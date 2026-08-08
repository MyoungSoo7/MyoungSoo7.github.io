---
layout: post
title: "기획 1~5시간을 투자하는 하네스: Loop Engineering과 TDD로 완성도를 만드는 법"
date: 2026-08-08 23:50:00 +0900
categories: [AI, Engineering, Software Development]
tags: [Harness Engineering, Loop Engineering, TDD, Planning, Agent, Claude Code, Codex]
---

# 기획 1~5시간을 투자하는 하네스

## 왜 구현보다 기획에 시간을 쓰는가

Agent에게 복잡한 작업을 바로 시키면 처음에는 빠르게 보인다.

```text
요청
→ Agent가 코드 작성
→ 테스트 일부 실행
→ PR 생성
```

하지만 범위가 커질수록 다음 비용이 발생한다.

- 요구사항 해석이 여러 파일에 흩어진다.
- 구현 중간에 설계가 바뀐다.
- 테스트가 무엇을 보장하는지 불명확하다.
- 여러 Agent가 같은 파일을 수정한다.
- 완료 메시지는 있지만 실행 증거가 없다.
- 작은 수정이 다른 도메인의 계약을 깨뜨린다.

따라서 복잡한 작업에서는 **기획에 1~5시간을 쓰는 것**이 구현을 늦추는 행위가 아니라 재작업을 줄이는 품질 투자다.

```text
기획 시간
= 목표·경계·근거·실패 조건·검증 계획을 고정하는 시간
```

## 1~5시간 기획 모델

작업 난이도에 따라 기획 시간을 계층화한다.

| 수준 | 기획 시간 | 적합한 작업 | 필수 산출물 |
|---|---:|---|---|
| S | 1시간 | 단일 함수·작은 버그 | 문제 정의·실패 테스트·완료 조건 |
| M | 2시간 | 모듈·API·단일 서비스 | 계약·영향 범위·테스트 계획 |
| L | 3시간 | 여러 모듈·DB·이벤트 | 데이터 흐름·migration·rollback |
| XL | 4시간 | 다중 서비스·Agent 병렬화 | worktree·역할·게이트·Trace |
| XXL | 5시간 | 금융·운영·보안·대규모 변경 | ADR·위험 분석·단계별 승인·복구 계획 |

시간을 채우기 위해 문서를 늘리는 것이 아니다. **구현자가 추측해야 하는 빈칸을 줄이는 것**이 목적이다.

## 기획 산출물 계약

기획이 끝났다고 판단하려면 다음 질문에 답할 수 있어야 한다.

```text
무엇을 바꾸는가?
무엇을 바꾸지 않는가?
어떤 입력을 받는가?
성공 결과는 무엇인가?
실패 결과는 무엇인가?
어떤 테스트가 먼저 실패해야 하는가?
어떤 로그·Trace가 최종 증거인가?
rollback은 어떻게 하는가?
```

권장 문서:

```text
00-problem.md       문제와 사용자 가치
01-scope.md         포함·제외 범위
02-contract.md      API·데이터·이벤트 계약
03-architecture.md  컴포넌트와 흐름
04-test-plan.md     RED-GREEN-REFACTOR 계획
05-risk.md          보안·운영·호환성 위험
06-delivery.md      commit·PR·배포·rollback
```

## Loop Engineering이란

여기서 Loop Engineering은 Agent를 한 번 호출하고 결과를 기다리는 방식이 아니다. 작은 루프를 만들고, 각 루프마다 실행 결과를 다음 루프의 입력으로 사용하는 방식이다.

```text
Plan
→ Implement
→ Test
→ Inspect
→ Correct
→ Re-test
→ Evidence
→ Next slice
```

각 루프는 짧고 관찰 가능해야 한다.

```text
한 루프의 입력
+ 실행 명령
+ 기대 결과
+ 실제 결과
+ 다음 판단
```

“계속 진행해”라는 모호한 지시보다 다음과 같은 루프가 안전하다.

```yaml
slice: customer-chat-citation
input: tests/test_customer_chat.py
command: python -m unittest tests.test_customer_chat
expected: citation_count >= 1
on_fail: inspect retrieval and citation guard
on_pass: open next slice
```

## TDD와 Loop Engineering의 결합

TDD는 각 기능의 품질 경계를 정한다. Loop Engineering은 그 TDD 사이클을 Agent 운영 단위로 만든다.

```text
RED:
  실패 테스트 작성

GREEN:
  최소 구현

REFACTOR:
  구조 개선

LOOP GATE:
  실제 명령·출력·diff 확인
```

예를 들어 RAG 고객 상담 기능은 다음과 같이 쪼갤 수 있다.

```text
Loop 1: 근거 없는 질문은 handoff
Loop 2: 근거 있는 질문은 citation 반환
Loop 3: product_model filter 적용
Loop 4: trace_id 저장
Loop 5: Flask API contract 통과
```

각 Loop마다 테스트를 먼저 작성하고 실패를 확인한다. 테스트가 처음부터 통과한다면 새 동작을 검증하지 못한 것일 수 있다.

## 완성된 Harness Architecture

하네스는 Prompt 모음이 아니다. Agent의 실행을 둘러싼 통제·관찰·검증 시스템이다.

```text
                         ┌──────────────┐
                         │ Human Policy │
                         └──────┬───────┘
                                │
┌────────────┐          ┌───────▼────────┐          ┌────────────┐
│ Task Queue │ ───────▶ │ Orchestrator   │ ───────▶ │ Agent Pool │
└────────────┘          └───────┬────────┘          └─────┬──────┘
                                │                         │
                         ┌──────▼──────┐          ┌─────▼──────┐
                         │ Worktree    │          │ MCP Tools  │
                         │ Allocator   │          │ Allowlist  │
                         └──────┬──────┘          └─────┬──────┘
                                │                         │
                         ┌──────▼────────────────────────▼──────┐
                         │ Loop Runner: Plan→Code→Test→Inspect  │
                         └──────┬────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Evidence & Gate Store │
                    └───────┬───────────────┘
                            │
             ┌──────────────▼──────────────┐
             │ Reviewer / Ouroboros / CI   │
             └──────────────┬──────────────┘
                            │
                    ┌───────▼────────┐
                    │ Human Delivery │
                    └────────────────┘
```

### 구성요소별 책임

```text
Task Queue
  작업 ID·우선순위·의존성·상태 관리

Orchestrator
  Agent 선택·라운드·timeout·재시도·비용 관리

Worktree Allocator
  작업별 branch·디렉터리 격리

MCP Allowlist
  Agent별 도구·경로·namespace·DB 권한 제한

Loop Runner
  한 번에 하나의 작은 검증 가능한 slice 실행

Evidence Store
  diff·test output·Trace·commit·artifact 보존

Reviewer/CI
  품질·보안·계약·rollback 게이트

Human Delivery
  push·merge·배포 승인
```

## Agent별 하네스 정책

모든 Agent에게 같은 권한을 주면 안 된다.

```yaml
scout:
  read: [source, docs, git, wiki]
  write: false
  network: web-readonly

builder:
  write: isolated-worktree
  test: allowed
  push: false
  production: false

reviewer:
  read: diff-tests-reports
  write: false
  approve: false

operator:
  push: approved-branch-only
  deploy: human-approval
  secrets: never-read
```

Persona는 이 정책을 설명하는 데 사용하고, 실제 통제는 OS·MCP·CI·GitHub 보호 규칙으로 구현한다.

## Loop의 종료 조건

무한 Agent 루프는 비용과 변경을 폭발시킨다. 각 루프에 종료 조건을 둔다.

```text
PASS:
  테스트·검증·artifact 모두 통과

FAIL:
  같은 오류 2회 반복 → 사람 검토

BLOCKED:
  권한·외부 시스템·불명확한 계약 → 중지

TIMEOUT:
  지정 시간 초과 → 결과 보존 후 종료

CONVERGED:
  새 검증 가능한 정보 없음 → 토론/분석 종료
```

“작업 완료”는 Agent의 문장이 아니라 다음 조합으로 판정한다.

```text
expected test result
+ actual command output
+ clean or explained diff
+ commit SHA
+ delivery handle
```

## 1~5시간 기획을 실제 작업에 적용하는 예

### 1시간: 단일 기능

```text
00:00~00:15 문제·완료조건
00:15~00:30 실패 테스트
00:30~00:45 최소 구현 계획
00:45~01:00 실행·검증 명령
```

### 3시간: API와 DB가 있는 기능

```text
1시간: API·DB 계약·영향 범위
1시간: TDD 시나리오·migration·rollback
1시간: Agent 역할·Loop·검증 artifact
```

### 5시간: 금융·운영·멀티 Agent 변경

```text
1시간: 공동 텍스트·요구사항·금지 범위
1시간: 데이터·이벤트·backward compatibility
1시간: 보안·운영·장애·rollback
1시간: TDD·통합·계약 테스트
1시간: worktree·Agent·PR·배포 게이트
```

이 계획은 시간을 낭비하는 문서화가 아니라, 실행 중 판단을 줄이는 사전 컴파일 단계다.

## 우리 운영 구조와 연결

우리 환경의 도구를 이 아키텍처에 배치하면 다음과 같다.

```text
Hermes
  = Orchestrator·대화·작업 상태

Leopard
  = 라우팅·스킬 선택

LION
  = 15개 CS 렌즈 종합 평가

Graphify/code graph
  = 관계·영향도 탐색

Claude 봇1~4
  = 상시 worker

Codex
  = 제한된 임시 논객·대안 구현자

MCP
  = 내부 도구 경계

tmux/cmux
  = 세션·관찰·작업공간

Ouroboros
  = PR·diff·품질 전달 검토

LLM Wiki
  = 결정·근거·결과 저장
```

## 실패하는 하네스

### 계획은 긴데 계약이 없다

문서가 50페이지여도 입력·출력·실패 조건이 없으면 Agent는 추측한다.

### Agent가 바로 main을 수정한다

격리되지 않은 작업은 병렬화가 아니라 충돌 자동화다.

### 테스트를 마지막에 만든다

TDD를 지키지 않으면 Loop가 검증 루프가 아니라 생성 루프가 된다.

### 모든 실패를 재시도한다

권한 부족·계약 불명확·잘못된 요구사항은 재시도로 해결되지 않는다.

### 로그를 보존하지 않는다

나중에 “왜 그렇게 판단했는가”를 재구성할 수 없다.

## 완성도 판단 체크리스트

```text
[ ] 문제·범위·제외 범위가 문서화됨
[ ] 작업별 worktree·branch가 격리됨
[ ] Agent별 권한과 Persona가 분리됨
[ ] 각 기능의 실패 테스트가 먼저 존재함
[ ] RED→GREEN→REFACTOR 기록이 있음
[ ] Loop마다 기대 결과와 실제 결과가 있음
[ ] MCP 도구가 allowlist로 제한됨
[ ] Secret·운영 DB·운영 배포가 기본 차단됨
[ ] diff·test·Trace·artifact가 보존됨
[ ] Reviewer와 Builder가 분리됨
[ ] commit·PR·CI 결과가 확인됨
[ ] timeout·재시도·비용 상한이 있음
[ ] rollback 방법이 존재함
[ ] 사람이 승인할 지점이 명확함
```

## 결론

기획에 1~5시간을 쓰는 이유는 Agent에게 더 많은 설명을 하기 위해서가 아니다. **작업을 작고 검증 가능한 Loop로 분해하고, 하네스가 각 Loop의 경계를 지키게 만들기 위해서**다.

```text
기획
→ 계약
→ TDD RED
→ 최소 구현
→ Loop 검증
→ Review Gate
→ 승인된 전달
```

좋은 하네스는 Agent를 더 자율적으로 만드는 동시에, 언제 멈춰야 하는지도 명확하게 만든다.

```text
속도는 Agent가 만든다.
완성도는 TDD가 측정한다.
안전은 Policy와 MCP가 지킨다.
재현성은 Loop와 Trace가 만든다.
최종 책임은 사람이 가진다.
```

## 참고 자료

- [Model Context Protocol Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [MCP Official Servers](https://github.com/modelcontextprotocol/servers)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
- [tmux](https://github.com/tmux/tmux)
- [cmux](https://github.com/manaflow-ai/cmux)
- [Ouroboros](https://github.com/Q00/ouroboros)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [OpenAI Codex](https://github.com/openai/codex)

> 이 글은 Agent 운영·TDD·MCP·worktree·검증 게이트를 결합한 설계 고찰이다. 특정 도구의 최신 기능이나 성능은 공식 문서와 실제 실행 Trace로 다시 검증해야 한다.
