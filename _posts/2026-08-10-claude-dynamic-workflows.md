---
layout: post
title: "Claude의 Dynamic Workflow: 한 번의 프롬프트에서 오케스트레이션·실행·검증까지"
date: 2026-08-10 18:40:00 +0900
categories: [ai-agent, claude-code, software-engineering]
tags: [Claude Code, dynamic workflow, ultracode, subagents, hooks, skills, orchestration]
---

첨부 이미지는 다음 세 단계로 Claude에게 복잡한 작업을 맡기는 사용 패턴을 보여준다.

```text
① /model 설정
② /effort ultracode 설정
③ 프롬프트에 workflow 입력
```

이미지의 메시지는 간단하다.

> 복잡한 작업을 넘기면 Claude가 오케스트레이션을 설계하고, 실행 스크립트를 만들고, 서브 에이전트에 업무를 나누고, 결과를 검증한 뒤 최종 리포트까지 작성한다.

이 글은 이 흐름을 Claude Code의 공식 Dynamic Workflows·Subagents·Skills·Hooks 기능과 연결해 설명한다. 다만 이미지의 설정값은 Claude Code 버전·모델·계정·실행 환경에 따라 달라질 수 있으므로, “어떤 환경에서나 똑같이 동작한다”고 일반화하지 않는다.

![Claude Dynamic Workflow 사용법을 설명하는 이미지](/assets/images/claude-dynamic-workflow-instructions.jpg)

## 1. 기존 Agent Loop와 Dynamic Workflow의 차이

전통적인 Agent Loop는 한 Agent가 다음 과정을 반복하는 구조다.

```text
목표
 ↓
코드 작성
 ↓
테스트
 ↓
실패 분석
 ↓
수정
```

Dynamic Workflow는 작업을 먼저 여러 단계로 분해하고, 각 단계에 적합한 Agent나 도구를 배치한다.

```text
복잡한 목표
 ↓
오케스트레이션 설계
 ↓
작업 분해
 ↓
서브 에이전트 실행
 ↓
결과 수집
 ↓
통합 검증
 ↓
최종 보고
```

Claude Code 공식 문서는 Dynamic Workflows를 실질적인 작업에 대해 Claude가 워크플로를 계획하고 여러 작업을 오케스트레이션하는 기능으로 설명한다.[1]

## 2. 이미지의 세 설정을 어떻게 이해할 것인가

### ① `/model`

사용할 모델을 선택하는 단계다. 모델은 비용·속도·추론 능력·도구 사용 품질에 영향을 줄 수 있다. 모델을 높인다고 모든 작업이 자동으로 좋은 설계가 되는 것은 아니다.

```text
모델 선택:
  추론 능력과 비용의 선택

워크플로:
  작업 분해와 실행 구조의 선택

검증:
  결과를 통과시킬 증거의 선택
```

### ② `/effort ultracode`

현재 Claude Code 공식 문서에서 `ultracode`는 단순한 모델 이름이 아니라, 높은 추론 노력과 Dynamic Workflow 오케스트레이션을 결합한 Claude Code 설정으로 설명된다.[2] 공식 문서 기준으로는 Claude Code v2.1.203 이상이 필요하고, 세션 단위로 적용되며, 작업량·토큰·실행 시간이 증가할 수 있다.[1][2]

즉 다음처럼 이해하는 편이 정확하다.

```text
ultracode:
  모든 작업에 무조건 좋은 모드가 아님

복잡한 작업:
  분해·병렬화·검증 비용을 감당할 가치가 있음

간단한 작업:
  과도한 토큰·시간·서브 에이전트 생성 가능
```

### ③ 프롬프트의 `workflow`

현재 작업을 Dynamic Workflow로 처리하라는 의도를 전달하는 방식이다. 공식 문서는 프롬프트에 `ultracode` 키워드를 넣어 단일 작업을 워크플로로 실행할 수 있다고 설명한다.[1]

다만 “workflow”라는 단어 하나만으로 도메인 경계·완료 기준·권한 정책이 자동으로 정의되지는 않는다.

## 3. Claude가 동적으로 만들 수 있는 것

이미지에서 말하는 동적 실행은 다음 구성요소의 조합으로 볼 수 있다.

```text
오케스트레이션:
  작업 순서·병렬성·의존성 설계

실행 스크립트:
  반복 명령·검증·수집 자동화

서브 에이전트:
  전문 역할별 독립 작업

검증:
  테스트·정적 분석·원문 대조·실행 Trace

리포트:
  산출물·실패·미확인·다음 행동 요약
```

Claude Code의 Subagent는 특정 유형의 작업을 독립적으로 수행하고 결과를 반환하는 전문 Agent다.[3] Skills는 재사용 가능한 지침과 실행 명령을 제공하며, Hooks는 세션·도구·서브 에이전트 생명주기의 특정 시점에 명령을 실행할 수 있다.[4][5]

## 4. Dynamic Workflow의 내부 구조

복잡한 Spring 기능을 예로 들면 다음과 같이 분리할 수 있다.

```text
Planner:
  요구사항·영향 범위·작업 그래프 작성

Explorer:
  기존 코드·의존성·문서 조사

Backend Agent:
  도메인·서비스·API 구현

Test Agent:
  단위·통합·아키텍처 테스트 작성

Reviewer:
  경계·보안·예외·엣지케이스 검토

Verifier:
  실제 명령 실행·결과 판정

Reporter:
  commit·diff·테스트·미확인 범위 보고
```

중요한 것은 Agent가 많다는 사실이 아니라 **각 Agent의 책임·입력·출력·권한이 분리되어 있는가**다.

## 5. “서브 에이전트를 대량으로 시작”하는 것의 함정

서브 에이전트를 많이 시작하면 항상 빨라지는 것은 아니다.

```text
작업 중복
문맥 불일치
서로 다른 가정
충돌하는 파일 수정
검증 결과의 중복
토큰·비용 증가
```

병렬화 가능한 것은 다음과 같이 독립된 조사다.

```text
Agent A:
  코드 구조 조사

Agent B:
  테스트 현황 조사

Agent C:
  외부 문서·API 계약 조사
```

반면 같은 파일을 동시에 수정하거나, 선행 설계 없이 여러 Agent가 서로 다른 아키텍처를 구현하게 하는 것은 위험하다.

```text
읽기·조사:
  병렬화 가능

공유 파일 쓰기:
  소유권 분리 필요

통합·최종 결정:
  단일 coordinator 필요
```

## 6. 오케스트레이션과 권한은 분리해야 한다

Dynamic Workflow가 자동으로 생성되더라도 권한은 자동 확장되면 안 된다.

```text
Read-only 조사:
  자동화 허용 범위가 넓음

로컬 코드 수정:
  sandbox·diff 검토

Git commit:
  검증 후 허용

Push·배포·DB 변경·Kubernetes write:
  명시적 승인 또는 강한 gate
```

Claude Code Hooks는 파일 포맷, 명령 실행 차단, 알림, 세션·서브 에이전트 이벤트 등 자동화를 지원한다.[4][5] 따라서 Hook은 “무조건 자동 실행”이 아니라 다음 guardrail로 활용해야 한다.

```text
위험 명령 차단
테스트 미통과 시 종료 차단
credential 출력 탐지
diff·파일 범위 검사
서브 에이전트 종료 시 산출물 확인
```

## 7. 자동 검증은 어떻게 구성하는가

최종 보고를 생성하기 전에 deterministic verification을 먼저 실행해야 한다.

```text
1. 컴파일
2. 단위 테스트
3. 통합 테스트
4. 아키텍처 테스트
5. 정적 분석·lint
6. 보안 검사
7. diff·파일 범위 검사
8. 실제 endpoint·artifact 확인
```

검증 결과는 다음처럼 분리한다.

```text
PASS:
  명령과 실제 출력으로 확인

FAIL:
  실패한 명령·오류·영향 범위

UNKNOWN:
  실행하지 못했거나 증거가 부족함

INFERENCE:
  로그·코드에 기반한 추론
```

Agent가 “완료했다”고 말하는 것과 실제 테스트·배포·HTTP 응답이 성공한 것은 다르다.

## 8. Claude Dynamic Workflow와 Self-Improving Harness

Dynamic Workflow는 현재 작업의 실행 구조를 자동화한다. Self-Improving Harness는 그 실행 결과를 다음 작업 환경에 반영한다.

```text
Dynamic Workflow:
  이번 복잡한 작업을 어떻게 수행할 것인가?

Self-Improving Harness:
  이번 실패로 다음 작업 환경을 어떻게 개선할 것인가?
```

예를 들어 Agent가 Controller에서 Repository를 직접 호출했다면, 현재 코드만 고치는 데서 끝내지 않는다.

```text
실패
 ↓
ArchUnit 규칙 보강
 ↓
AGENTS.md·CLAUDE.md 문서 연결
 ↓
Skill 개선
 ↓
회귀 테스트
```

이렇게 해야 다음 워크플로가 같은 실패를 반복하지 않는다.

## 9. Claude·Codex·Ouroboros와의 역할 분리

현재 Agent 운영 구조에 적용하면 다음처럼 나눌 수 있다.

```text
Claude:
  동적 워크플로·대화형 오케스트레이션·서브 에이전트

Codex:
  코드 변경·전문 리뷰·Evals·실행 검증

MCP:
  외부 지식·문서·도구 연결

Ouroboros:
  실행·평가·진화·checkpoint·receipt

Hermes:
  정책·cron·중앙 보고·memory·안전 조정
```

이 구조의 목적은 Agent 수를 늘리는 것이 아니라:

```text
작업 분해
권한 분리
검증 독립성
Trace 보존
실패 재사용
```

을 확보하는 것이다.

## 10. Dynamic Workflow를 사용할 때의 체크리스트

### 작업 시작 전

```text
[ ] 목표와 범위가 명확한가?
[ ] 읽기·쓰기·배포 권한이 구분되어 있는가?
[ ] 작업을 병렬화할 수 있는가?
[ ] 공유 파일 소유권이 정해졌는가?
[ ] 완료 조건과 실패 조건이 있는가?
```

### 실행 중

```text
[ ] 서브 에이전트가 중복 작업하지 않는가?
[ ] 모든 결과에 출처·파일·명령이 있는가?
[ ] 위험한 write가 자동으로 실행되지 않는가?
[ ] 실패를 성공으로 포장하지 않는가?
[ ] 비용·반복 횟수·context를 감시하는가?
```

### 완료 전

```text
[ ] 테스트와 검증 명령을 실제 실행했는가?
[ ] diff·commit·push 상태를 분리했는가?
[ ] 운영 배포와 로컬 검증을 구분했는가?
[ ] 미확인·추론·다음 조치를 보고했는가?
[ ] 결과를 다음 Skill·Rule·Test로 승격할 가치가 있는가?
```

## 결론

첨부 이미지의 사용법은 Claude를 단순한 답변 Agent가 아니라 **동적으로 팀을 구성하는 Workflow Engine**처럼 사용하는 방법을 보여준다.

Claude Code의 Dynamic Workflows는 복잡한 작업을 분해하고, Subagents는 전문 역할을 나누며, Skills와 Hooks는 반복 절차와 검증을 자동화한다.[1][3][4][5]

하지만 Dynamic Workflow가 곧 자율적인 성공을 뜻하지는 않는다.

```text
서브 에이전트가 많음
≠ 작업이 정확함

workflow가 생성됨
≠ 경계가 올바름

테스트 통과
≠ 업무 정합성 보장

최종 리포트 생성
≠ 실제 완료 증명
```

가장 중요한 것은 오케스트레이션의 화려함이 아니라 다음 네 가지다.

```text
작업 경계
권한 경계
검증 기준
Trace 증거
```

> **Claude가 팀을 구성하고 지휘·실행·검증할 수 있는 시대일수록, 사람은 무엇을 자동화할지보다 무엇을 자동화하지 않을지를 먼저 결정해야 한다.**

## Sources

1. [Claude Code — Dynamic Workflows](https://code.claude.com/docs/en/workflows)
2. [Claude Code — Model configuration and ultracode](https://code.claude.com/docs/en/model-config)
3. [Claude Code — Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
4. [Claude Code — Hooks guide](https://docs.anthropic.com/en/docs/claude-code/hooks-guide)
5. [Claude Code — Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
6. [Claude Code — Common workflows](https://docs.anthropic.com/en/docs/claude-code/common-workflows)

*첨부 이미지는 사용자가 제공한 이미지이며, 이미지의 문구를 요약·재구성했다. Claude Code의 기능·버전·가용 모델은 공식 문서와 실행 환경에 따라 달라질 수 있다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*

## Related posts

- [Agentic Coding의 Self-Improving Loop](https://myoungsoo7.github.io/2026/08/10/self-improving-loop-agentic-coding/)
- [Hidden Checklist와 자기개선 루프](https://myoungsoo7.github.io/2026/08/10/hidden-checklist-agent-loop/)
- [바이브 코딩의 다음 경계: MCP와 아키텍처](https://myoungsoo7.github.io/2026/08/10/vibe-coding-boundaries-mcp-architecture/)
- [Agent Skill 생태계 지도](https://myoungsoo7.github.io/2026/08/10/agent-skills-inventory/)

*이 글은 Claude Code 공식 문서를 기준으로 첨부 이미지의 사용 패턴을 분석한 글이며, 특정 설정 조합의 결과를 모든 환경에서 보장하지 않는다.*

---

## Appendix: 역할별 산출물 예시

| 역할 | 입력 | 산출물 | 검증 |
|---|---|---|---|
| Planner | 목표·제약 | 작업 그래프 | 의존성·범위 |
| Explorer | 저장소·문서 | 구조·영향 분석 | 파일·출처 |
| Implementer | 승인된 계획 | 코드·테스트 | 컴파일·단위 테스트 |
| Reviewer | diff·계약 | 리뷰 결과 | 규칙·엣지케이스 |
| Verifier | 전체 artifact | PASS/FAIL/UNKNOWN | 실제 실행 Trace |
| Reporter | 모든 결과 | 최종 보고서 | 근거·미확인 분리 |

---

*2026-08-10 작성*

---

