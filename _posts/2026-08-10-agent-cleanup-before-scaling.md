---
layout: post
title: "확장하기 전에 정리 경로부터 설계하라: Agent 운영에 적용한 cleanup 원칙"
date: 2026-08-10 15:55:00 +0900
categories: [ai-agent, operations, harness]
tags: [agent-os, cleanup, provenance, parallelism, cost-model, observability]
---

[개발가재 블로그의 원문 Daily Reflection — 확장하기 전에 정리 경로부터 설계하라](https://blog.gaebal-gajae.dev/posts/2026-08-10-daily-reflection-design-the-cleanup-before-scaling.html)를 읽고, 현재 Mac의 Hermes·Claude 봇1~4·Codex·Ouroboros 운영에 적용할 수 있는 원칙으로 정리했다.

원문의 핵심 문장은 다음과 같다.

> 같은 문제가 다시 자라는 구조를 먼저 고치는 책임이, 문제가 생길 때마다 잘 치우는 능력보다 중요하다.

이 문장은 Agent를 많이 병렬 실행하는 것보다, **생성되는 상태·산출물·권한·비용·수명·소유권을 먼저 설계해야 한다**는 뜻으로 읽힌다.

## 1. 병렬성은 작업 수가 아니라 복제 상태의 총량이다

병렬 Agent는 처리량을 높인다. 그러나 각 Agent가 다음 상태를 별도로 만들면 전체 비용도 증가한다.

```text
대화 context
build artifact
cache
temporary worktree
background shell
MCP subprocess
logs
memory 후보
```

따라서 병렬성을 다음처럼 계산해야 한다.

$$
\text{Total State Cost}
= \text{Shared State}
+ \sum_{i=1}^{n} \text{Replicated State}_i
$$

작업 수를 4개에서 8개로 늘리는 결정은 단순히 Agent가 두 배가 되는 문제가 아니다.

```text
context가 몇 배가 되는가?
cache가 공유되는가?
artifact가 중복 생성되는가?
background process가 종료되는가?
실패한 worktree를 보존할 것인가?
```

현재 봇1~4를 운영할 때도 “세션이 살아 있다”만으로 정상이라고 판단할 수 없다. 세션 수와 함께 shell·MCP·worktree·토큰 사용량을 관찰해야 한다.

## 2. 생성 경로에는 반드시 정리 경로가 있어야 한다

원문은 정리 자체보다 **정리 경로의 사전 설계**를 강조한다. 이 원칙을 Agent artifact에 적용하면 모든 생성물에 다음 질문이 필요하다.

| 질문 | 운영 규칙 |
| --- | --- |
| 무엇이 생성되는가? | 파일·cache·worktree·log·MCP process를 명시 |
| 누가 소유하는가? | owner와 runtime을 분리 기록 |
| 언제까지 보존하는가? | TTL·보존 기간·실패 시 예외 정의 |
| 무엇이 재생성 가능한가? | source와 build 산출물을 구분 |
| 실패 시 무엇을 남기는가? | trace·receipt·로그만 보존하고 임시물은 정리 |
| 어떻게 되돌리는가? | rollback pointer 또는 backup 경로 기록 |

현재 이 원칙을 Script·Tool·Skill에 적용하기 위해 다음 Registry를 만들었다.

```text
/Users/lms/.hermes/scripts/agent-artifacts.yaml
```

각 artifact는 다음 메타데이터를 갖는다.

```yaml
owner:
runtime:
author:
source:
permissions:
side_effects:
status:
last_verified:
verification:
```

최초 작성자 근거가 없으면 `author: unknown`으로 남긴다. 이는 누군가의 기여를 지우는 것이 아니라, 추측을 provenance로 위장하지 않기 위한 규칙이다.

## 3. 긴급 청소가 반복되면 예방 계약을 만든다

같은 청소 작업이 반복되면 더 빠른 삭제가 답이 아니다.

```text
첫 번째 반복:
  원인과 산출물 종류 조사

두 번째 반복:
  owner·TTL·보존 경계 추가

세 번째 반복:
  자동 정리 또는 생성 전 차단 계약 도입
```

예를 들어 Agent가 임시 파일을 계속 만드는 경우:

```text
나쁜 방식:
  매번 /tmp를 전체 삭제

좋은 방식:
  작업별 namespace
  생성 시 owner/expiry 기록
  성공 시 자동 정리
  실패 시 trace만 보존
  active 작업은 삭제 금지
```

`harness_janitor.py` 같은 정리 도구도 이 정책 위에서만 사용해야 한다. 정리 도구가 소유권·작업 상태를 모르면 필요한 증거까지 지울 수 있다.

## 4. 구조화된 입력은 build 전에 검증한다

원문은 setup tip을 예로 들어, 구조화된 콘텐츠를 빌드 전에 검증해야 잘못된 입력이 후단으로 전파되지 않는다고 말한다.

Agent 시스템에서 입력은 단순한 JSON/YAML 형식이 아니다.

```text
source
authority
permission
cost
lifetime
side_effects
```

현재 적용 사례:

```text
Jekyll post:
  frontmatter·date·table·HTML 검증

K3s RCA:
  collected_at·lookback·현재 endpoint 검증

Artifact Registry:
  owner·runtime·permissions·verification 검증

Ouroboros:
  checkpoint·receipt·evaluate 검증
```

형식이 맞아도 권한과 원본이 틀리면 완료가 아니다. 예를 들어 K3s API에 연결되지 않았는데 API Server 장애라고 보고한 것은 네트워크 입력과 판정 권한을 분리하지 못한 사례다.

## 5. green signal은 올바른 입력 위에서만 완료다

이번 Agent 운영에서 특히 중요한 규칙이다.

```text
HTTP 200
≠ 업무 데이터 성공

실패 카운터 0
≠ 데이터 수집 성공

Git push 성공
≠ 블로그 게시 성공

MCP connected
≠ 업무 도구 검증 완료

Pod Running
≠ 애플리케이션 업무 정상
```

그래서 각 영역에 별도 완료 조건을 둔다.

| 영역 | 실제 완료 조건 |
| --- | --- |
| Blog | Git push + Pages build/deploy success + 실제 URL HTTP 200 |
| K3s RCA | 현재 API/Pod/log/업무 trace가 모두 시간창 안에 있음 |
| KRX 수집 | 거래일 source count·upsert count가 기대치와 일치 |
| MCP | 연결 + tool discovery + read-only 호출 성공 |
| Artifact | 파일 존재 + 권한·owner + verification evidence |
| Ouroboros | 실행 결과 + checkpoint + evaluate/receipt |

## 6. no-op은 실패가 아니라 정직한 결과다

원문은 근거가 없는 칸을 억지로 채우지 않는 “조용한 no-op”을 운영 품질로 본다.

이 원칙은 Agent에게 특히 중요하다.

```text
새 이슈를 만들 근거가 없음
→ 만들지 않음

현재 장애 증거가 없음
→ 정상 또는 미확정으로 보고

최초 작성자를 증명할 수 없음
→ unknown으로 기록

클러스터 endpoint에 접근할 수 없음
→ 관측 지점 접근 실패로 보고

사용하지 않는 zeude reference
→ 장애가 아닌 정리 후보
```

빈칸을 채우려는 Agent의 습관은 보고서를 길게 만들지만 시스템을 더 정확하게 만들지는 않는다.

## 7. 현재 운영 구조에 적용한 설계

### Hermes

```text
중앙 cron·보고·memory·정책
```

Hermes는 다른 Agent의 결과를 종합하지만, 원본 Trace가 없으면 결론을 만들지 않아야 한다.

### Claude 봇1~4

```text
봇1: 범용·인프라
봇2: Settlement
봇3: MSA·P8
봇4: inter-asat·RAHAB
```

각 봇의 worktree·memory·background shell은 소유권을 명확히 하고, 작업 종료 후 정리 경로를 둔다.

### Codex

전문 reviewer·hook·Ouroboros worker Skill을 담당한다. 전문 Agent가 늘어날수록 reviewer 자체의 artifact와 provenance도 Registry에 등록한다.

### Ouroboros

```text
run → evaluate → evolve → checkpoint → receipt
```

긴 실행의 상태·재개·검증을 구조화한다. 병렬 generation을 늘리기 전에 artifact 상한과 lease·checkpoint의 수명을 정해야 한다.

## 8. 다음에 도입할 예방 계약

현재 `agent_artifact_audit.py`를 만들고 다음을 자동화했다.

```text
Registry와 실제 path 대조
신규 Script/Skill 탐색
owner/runtime/source 확인
SHA-256 계산
PASS/WARN/FAIL 판정
Registry additive 등록
Wiki log append
```

앞으로의 최소 계약은 다음이다.

```text
새 artifact 생성 시 Registry entry 필수
author는 근거 없으면 unknown
owner와 runtime은 반드시 명시
permissions와 side_effects 기록
검증 command와 결과 기록
Wiki에는 요약 log만 append
기존 artifact 자동 overwrite 금지
```

## 9. 함께 읽으면 좋은 원문과 연결 글

- [원문: Daily Reflection — 확장하기 전에 정리 경로부터 설계하라](https://blog.gaebal-gajae.dev/posts/2026-08-10-daily-reflection-design-the-cleanup-before-scaling.html)
- [이 Mac의 Agent Skill 생태계 지도: Hermes·Claude·Codex·Leopard](https://myoungsoo7.github.io/2026/08/10/agent-skills-inventory/)
- [Agent가 어려워하는 일을 자동화한 로컬 Script·Tool 지도](https://myoungsoo7.github.io/2026/08/10/agent-tools-built-on-mac/)
- [이 Mac의 Agent Artifact Provenance 설계](https://myoungsoo7.github.io/2026/08/10/agent-tools-built-on-mac/)

## 결론

확장은 더 많은 Agent를 띄우는 일이 아니다. 무엇이 복제되고, 어디에 쌓이며, 누가 소유하고, 언제 사라지는지 설명할 수 있게 만드는 일이다.

```text
생성 비용
+ 소유권
+ 검증 경계
+ 보존 범위
+ 정리 경로
+ rollback
```

이 다섯 가지가 설계되지 않은 병렬성은 처리량처럼 보이는 부채다.

> **같은 문제가 세 번째로 발생하기 전에, 더 빠르게 치우는 방법이 아니라 다시 자라지 않는 구조를 만들어야 한다.**

## References

- [원문: 개발가재 블로그, Daily Reflection — 확장하기 전에 정리 경로부터 설계하라](https://blog.gaebal-gajae.dev/posts/2026-08-10-daily-reflection-design-the-cleanup-before-scaling.html)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Ouroboros](https://github.com/Q00/ouroboros)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

*이 글은 원문을 요약·재해석한 글이며, 원문의 문장을 그대로 재게시하지 않고 현재 Agent 운영 구조에 적용한 관점으로 작성했다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*
}myzyň#+#+#+#+json go? 