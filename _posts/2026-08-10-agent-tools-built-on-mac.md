---
layout: post
title: "Agent가 어려워하는 일을 자동화한 로컬 Script·Tool 지도"
date: 2026-08-10 14:28:00 +0900
categories: [ai-agent, engineering, automation]
tags: [Hermes, Claude, Codex, Ouroboros, harness, observability, memory, k3s]
---

LLM Agent는 코드를 쓰고 설명하는 일에는 강하지만, 반복적이고 상태가 많으며 실패를 정확히 분류해야 하는 작업에서는 쉽게 흔들린다. 현재 이 Mac에는 그런 한계를 보완하기 위해 Claude, Codex, Hermes를 사용하며 만든 Script·Tool·Hook가 쌓여 있다.

이 글은 “파일이 많다”는 목록이 아니라, **어떤 Agent 한계를 어떤 외부 실행 장치로 보완했는가**를 정리한 현재 시점의 지도다. 파일의 작성 주체는 커밋·경로로 확인되는 경우에만 표시하고, Claude/Codex/Hermes의 개별 저작자 attribution은 확인되지 않은 경우 “실행 환경에서 사용되는 도구”로 표현한다.

## 먼저 구분할 것

| 구분 | 역할 | 대표 위치 |
| --- | --- | --- |
| Hermes | 중앙 조정·cron·보고·memory·웹/터미널 실행 | `~/.hermes/` |
| Claude 봇 1~4 | Telegram을 통한 프로젝트별 실행자 | `~/.claude/channels/telegram-bot*` |
| Codex | 규칙·전문 reviewer·Ouroboros worker·hook | `~/.codex/` |
| Ouroboros | 실행·checkpoint·evaluate·evolve·receipt 하네스 | `~/ouroboros`, `~/ouroboros-mcp-venv` |
| Script/Tool | Agent가 반복해서 틀리는 부분을 결정적 코드로 고정 | `~/.hermes/scripts/` |
| Memory/Wiki | 현재 작업과 재사용 지식 분리 | `~/.hermes/memories`, `~/wiki` |

이 표의 핵심은 Agent가 모든 판단을 직접 수행하지 않는다는 점이다. **LLM은 해석하고, Script는 수집·계산·필터링하고, Harness는 완료 증거를 판정한다.**

## 1. 운영 인프라: K3s RCA와 관측

### `k8s-rca-collect.sh`

Kubernetes API에서 현재 Pod 후보와 최근 로그를 수집한다.

Agent가 어려워하는 일:

```text
최근 24시간 시간창 적용
현재 Pod와 오래된 Pod 구분
Running/Completed/Failed/Pending 분리
현재 재시작과 누적 restartCount 분리
현재 로그와 previous 로그 구분
활성 data stream 선택
```

수집 결과에는 `COLLECTED_AT_UTC`와 `LOOKBACK_SECONDS`를 남긴다. 이는 “로그에 있었다”와 “최근 장애였다”를 분리하기 위한 provenance다.

### `k8s-rca-analyze.py`

수집 corpus를 시간 범위에 맞춰 분석하고, 과거 사건을 현재 장애로 승격하지 않도록 한다. Gemini 404와 Elasticsearch mapping conflict처럼 같은 연쇄 사건을 묶고, 외부 API 종료와 마지막 성공·첫 실패를 비교하는 데 사용한다.

### `k8s-rca-daily.sh`

collector와 analyzer를 연결하는 매일 RCA 실행 진입점이다. 읽기 전용 수집 후 결과를 브리핑에 전달한다.

### `lemuel_pod_report.py`

Pod 상태를 직접 판정한다. `CrashLoopBackOff`, `ImagePullBackOff`, `ErrImagePull`, `Failed` 같은 현재 hard failure만 즉시 후보로 올리고, 높은 `restartCount`만으로 RestartLoop라고 말하지 않도록 한다.

### `lemuel_pod_logs.py`

특정 Pod와 컨테이너의 현재·이전 로그를 제한적으로 조회한다. “어떤 로그를 읽었는가”를 남기는 보조 도구다.

### 이 영역에서 얻은 중요한 교훈

```text
API endpoint 접근 실패 ≠ API Server 장애
HTTP 401 /version 응답 = 서버가 살아 있고 인증을 요구함
restartCount 누적값 ≠ 현재 CrashLoop
Completed Pod ≠ 장애 Pod
노드 reboot ≠ k3s service restart
```

특히 사설 LAN endpoint에 접근하지 못한 `curl rc=7`을 클러스터 CRITICAL로 승격했던 사례는, **관측 지점과 대상 시스템을 분리하지 않은 Agent 판정의 전형적인 실패**였다. 이후에는 SSH tunnel 경로, 직접 `/version` probe, 현재 Node/Pod 상태를 함께 확인해야 한다.

## 2. 업무 데이터 성공을 검증하는 도구

### `export_investment_recommendations.py`

외부 투자 서비스의 결과를 평탄화하고 민감정보를 제거한 snapshot으로 만든다.

### `test_investment_export.py`

외부 결과가 비어 있거나 schema가 바뀌었을 때 조용히 성공하지 않는지 확인한다.

이 계열에서 가장 중요한 미완성 과제는 KRX 결손에서 드러났다.

```text
실패 카운터 0 ≠ 업무 성공
HTTP 200 ≠ 데이터 수집 성공
Job completed ≠ source data non-empty
```

업무 수집기는 앞으로 다음 invariant를 확인해야 한다.

```text
거래일이면 기대 데이터가 존재해야 한다
source response count > 0
upsert count > 0
마지막 non-zero 성공 시각이 존재한다
전일 대비 0건이면 경고한다
```

이것은 일반적인 LLM 추론이 아니라 결정적 검증기여야 한다.

## 3. 뉴스·RSS·블로그 자동화

### `daily_news_poster.py`

RSS/공개 페이지를 수집해 AI·K8s·보안·금융·Java/Spring 기술 브리핑과 Jekyll 포스트를 생성한다.

현재 등록된 Java/Spring 관련 소스:

```text
Toss Tech — https://toss.tech/rss.xml
Woowahan Tech — https://techblog.woowahan.com/feed/
NHN Cloud Meetup — https://meetup.nhncloud.com/rss
NAVER D2 — https://d2.naver.com/ 또는 공식 Atom fallback
```

스크립트가 담당하는 것은:

```text
RSS 수집
피드별 실패 격리
중복 제거
48/168시간 필터링
Java/Spring/Kotlin/JPA/Kafka 등 keyword 우선순위
원문 링크 보존
Jekyll frontmatter 생성
```

관련 테스트:

```text
test_daily_news_poster.py
test_daily_news_poster_rss.py
test_daily_news_poster_markets.py
test_daily_news_poster_projects.py
test_investment_export.py
```

피드 하나가 깨져도 전체 결과를 버리지 않고 `성공 소스`와 `실패 소스`를 구분하는 것이 핵심이다.

## 4. 코드 영향 분석과 구조 그래프

### `code-impact-analyze.py`

변경 파일의 영향을 추적하는 분석기다. Agent가 한두 파일만 보고 “영향 없음”이라고 결론내리는 것을 줄인다.

### `build_local_code_graph.py`

로컬 프로젝트의 코드 관계를 그래프로 만든다.

### `build_settlement_code_graph.py`

Settlement의 order/payment/settlement/account 흐름과 서비스 관계를 구조적으로 확인한다.

Agent가 어려워하는 일:

```text
호출자·피호출자 추적
서비스 경계 확인
설정·Dockerfile·Gateway route 누락 확인
변경 파일의 운영 영향 추정
```

코드 그래프는 답을 대신하지 않지만, **읽어야 할 범위를 결정하는 검색 장치**다.

## 5. Memory·Wiki·검색 도구

### `agent_memory.py`

기억과 실행 환경을 연결하는 보조 도구다. 단, Memory는 Trace의 대체재가 아니다.

### `wiki_master.py`

LLM Wiki에 분석 결과를 정리하는 진입점이다. 공개 블로그와 내부 지식베이스를 분리한다.

### `wiki_graph_engine.py`

문서와 개념 간 연결을 그래프로 만든다. Agent가 매번 처음부터 읽지 않고 관련 개념을 따라갈 수 있게 한다.

### `viking_neural_search.py`

OpenViking 기반 검색을 시도하는 도구다. 실제 backend 상태와 검색 성공 여부를 구분해 보고해야 한다.

지식의 저장 규칙은 다음이다.

```text
Memory = 안정적인 사실·선호·운영 규칙
Skill = 반복 가능한 절차
Wiki = 출처가 있는 분석·RCA·설계
Session = 임시 진행 상태
Trace = 최종 진실
```

## 6. Harness와 Agent 자기 개선

### `harness_stats.py`

실행 횟수, 성공·실패·검증 누락 같은 Harness 지표를 수집한다.

### `harness_distiller.py`

반복된 실행 기록에서 재사용 가능한 규칙과 실패 패턴을 추출한다.

### `harness_janitor.py`

오래된 임시 산출물과 실행 흔적을 정리하는 도구다.

### `autofix_harness.py`

반복 실패를 바탕으로 Harness 보정 후보를 만든다. 자동 수정은 반드시 diff와 테스트를 통과한 뒤 채택해야 한다.

### `tool_maker.py`

Agent가 계속 반복하는 수동 절차를 Script·Tool 후보로 만드는 실험 도구다.

개선 루프는 다음과 같다.

```text
Agent 실행
→ Trace 수집
→ 실패 패턴 계량
→ 결정적 Script/Tool 생성
→ 테스트·승인
→ 다음 실행에 적용
```

중요한 것은 “Agent가 스스로 똑똑해졌다”가 아니라, **실패를 재현 가능한 외부 장치로 옮겼다**는 점이다.

## 7. Multi-agent와 Telegram 제어

### `tmux_tg_bridge.py`

Telegram과 tmux Claude 세션 사이의 상태·메시지 연결을 보조한다.

현재 역할 분리:

```text
봇1 = 범용·인프라
봇2 = Settlement
봇3 = MSA·P8
봇4 = inter-asat·RAHAB
```

병렬 Agent의 장점은 독립 작업이지만, 다음 race가 생긴다.

```text
같은 노드에 중복 SSH
같은 Git worktree 동시 수정
같은 Kubernetes 변경 중복 실행
같은 issue/PR 상태를 서로 다르게 관찰
```

그래서 Claude hook의 coordinator, worktree 규칙, 봇별 CLAUDE.md가 필요하다. 봇의 Memory도 공유하지 않고 역할별로 분리한다.

## 8. Debate·Consensus 실험 도구

현재 스크립트 저장소에는 다음 실험군이 있다.

```text
consensus_engine.py
consensus_engine_symposium.py
debate_A*.py
debate_B*.py
debate_C*.py
debate_orchestrator.py
debate_headless.py
vibe_debate.py
vibe_debate_v2.py
```

목적은 단일 Agent의 첫 답을 바로 채택하지 않는 것이다.

```text
주장
→ 반론
→ 재검토
→ 근거 대조
→ 합의 또는 미확정
```

하지만 이 파일들은 운영 표준 제품이 아니라 실험·중간 버전이 섞인 영역이다. 앞으로는 canonical entrypoint, 입력 schema, output receipt, 회귀 테스트를 정해야 한다.

## 9. Codex와 Ouroboros가 제공하는 별도 Harness

### Codex

`~/.codex/`에는 전문 reviewer Agent와 Hook가 있다.

```text
agents/
  jpa-optimizer
  settlement-archunit-enforcer
  settlement-idempotency-checker
  security-auditor
  test-coverage-fixer
  lemuel-cluster-toolbox

hooks/
  bash-danger-check.sh
  inject-datetime.sh
  prettier-format.sh

rules/
  ouroboros.md
```

Codex의 강점은 전문 관점과 사전·사후 Hook를 분리하는 것이다. 예를 들어 JPA 최적화, 멱등성, ArchUnit, 보안, 테스트 커버리지를 일반 Agent에게 매번 설명하지 않고 역할별 reviewer로 고정한다.

### Ouroboros

`~/ouroboros`는 실행을 다음 단위로 구조화한다.

```text
run
→ evaluate
→ evolve
→ checkpoint
→ receipt
→ convergence
```

현재 Mac의 전용 MCP 환경은:

```text
/Users/lms/ouroboros-mcp-venv
Ouroboros v0.51.0
MCP discovery: 35 tools
EventStore: /Users/lms/.ouroboros/ouroboros.db
```

이는 Agent의 긴 실행을 단순 채팅 기록이 아니라 checkpoint·artifact·평가 결과로 남기는 장치다.

## 10. Claude·Codex·Hermes attribution의 한계

현재 확인된 로컬 저장소는 “누가 최초로 작성했는가”를 항상 기록하지 않는다. 일부는 Hermes 스크립트 저장소에 추적되지만, Claude 봇이나 Codex가 실행 중 생성·수정한 파일의 저작자를 파일만으로 확정할 수 없는 경우가 있다.

따라서 다음처럼 표시하는 것이 정직하다.

```text
확정 가능:
  Git author/commit으로 확인된 작성자
  도구가 현재 어느 Agent 환경에서 사용되는지

확정 불가:
  대화 중 최초 아이디어를 낸 모델
  여러 Agent가 수정한 최종 파일의 단일 저자
  설치된 외부 plugin의 원저자와 로컬 수정자 구분
```

“Claude가 만들었다”, “Codex가 만들었다”, “Hermes가 만들었다”는 주장은 Git trace나 파일 provenance가 있을 때만 사용해야 한다.

## 11. 현재 도구의 상태 분류

| 상태 | 예시 | 관리 원칙 |
| --- | --- | --- |
| 운영 사용 | K3s RCA, daily news, memory/wiki, tmux bridge | 입력·출력·검증 유지 |
| 검토 후 사용 | harness stats/distiller, code graph, dynamic mapper | 실행 전 diff·trace 확인 |
| 실험 | debate/vibe/consensus 변형 | canonical 버전과 폐기 기준 필요 |
| 외부 도구 | Claude plugin, Codex skill, Ouroboros | 버전·출처·권한 확인 |

현재 `~/.hermes/scripts`에는 Python·Shell 파일 약 50개가 있고, 그중 운영 스크립트와 실험 파일이 함께 존재한다. 이 자체가 다음 리팩터링 과제다.

## 12. 다음에 필요한 Tool Registry

도구가 많아질수록 목록만으로는 부족하다. 다음 registry를 두는 것이 좋다.

```yaml
name: k8s-rca-collect
owner: Hermes
purpose: 최근 24시간 read-only K3s Trace 수집
inputs:
  - kubeconfig
  - lookback_seconds
outputs:
  - timestamped corpus
side_effects: read-only
success:
  - exit 0
  - collected_at present
  - credentials excluded
failure:
  - endpoint unreachable
  - malformed JSON
related_policy: homelab-k3s-ops
```

최소 필드는 다음과 같다.

```text
owner
purpose
input/output
side effects
required permissions
success condition
failure condition
rollback
last verified
```

## 결론

이 Mac의 Script·Tool 생태계는 Agent를 대체하기 위해 만들어진 것이 아니다. Agent가 잘하지 못하는 다음 영역을 외부에서 고정하기 위해 만들어졌다.

```text
현재 상태 판정
반복 수집
수치 계산
업무 invariant 검증
코드 영향 범위 파악
동시 실행 충돌 방지
Memory 정리
긴 실행 checkpoint
완료 증거 생성
```

가장 중요한 운영 원칙은 이것이다.

> **LLM은 해석을 담당하고, Script는 반복을 담당하며, Harness는 완료를 증명한다.**

그리고 도구가 많아질수록 새 도구를 만드는 것보다 먼저 해야 할 일은 다음이다.

```text
운영 도구와 실험 도구 분리
owner와 provenance 기록
입력·출력 schema 고정
Trace와 receipt 저장
중복·폐기 기준 마련
```

Agent 시스템의 신뢰성은 모델의 말솜씨보다, **모델이 틀리기 쉬운 부분을 얼마나 결정적이고 검증 가능한 장치로 옮겼는가**에 달려 있다.

## References

- [Hermes Agent](https://hermes-agent.nousresearch.com/docs)
- [Ouroboros](https://github.com/Q00/ouroboros)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Project source: local Hermes scripts](/Users/lms/.hermes/scripts)

*이 글의 로컬 파일·경로·도구 수는 2026-08-10 KST 현재 Mac 환경을 기준으로 한 inventory이며, 외부 plugin·캐시·개별 project worktree 전체를 완전한 단일 목록으로 주장하지 않는다.*

*주의: 공개 블로그에는 credential, token, private IP, 내부 endpoint와 같은 민감정보를 포함하지 않았다.*