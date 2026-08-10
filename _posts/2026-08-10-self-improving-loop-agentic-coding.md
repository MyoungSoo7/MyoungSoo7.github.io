---
layout: post
title: "Agentic Coding의 Self-Improving Loop: 모델이 아니라 Harness를 개선하는 방법"
date: 2026-08-10 17:20:00 +0900
categories: [ai-agent, software-engineering, harness]
tags: [Self-Improving Loop, Agentic Coding, Claude Code, Codex, Harness Engineering, Evals, Memory]
---

[Codex.epril의 원문](https://codex.epril.com/what-is-self-improving-loop-in-ai-agentic-coding)을 읽고, Agentic Coding에서 말하는 Self-Improving Loop의 의미와 현재 Hermes·Claude·Codex·Ouroboros 운영에 적용할 수 있는 원칙을 정리했다.

## 핵심 요약

> Self-Improving Loop는 모델의 weight가 실시간으로 바뀌는 것이 아니라, Agent의 실패와 검증 결과를 다음 작업의 테스트·규칙·문서·Skill·Tool·Workflow에 반영해 **작업 시스템 자체를 개선하는 루프**다.

따라서 더 정확한 표현은 다음에 가깝다.

```text
Self-Improving Model
보다
Self-Improving Harness
```

## 1. Agent Loop와 Self-Improving Loop는 다르다

Claude Code나 Codex가 다음 과정을 반복한다고 하자.

```text
Read
 ↓
Implement
 ↓
Test
 ↓
Failure
 ↓
Analyze
 ↓
Fix
 ↓
Test
```

이것은 현재 작업을 완료하기 위한 **Agent Loop**다. 테스트가 실패하면 코드를 수정하고, 다시 테스트해 통과시키는 과정이다.

하지만 내일 비슷한 작업에서 같은 실수를 반복한다면 작업은 개선됐어도 시스템은 개선되지 않은 것이다.

```text
현재 task의 수정:
  이번 결과만 좋아짐

Harness의 수정:
  다음 task의 시작 조건이 좋아짐
```

Self-Improving Loop는 두 번째를 목표로 한다.

## 2. Ralph Loop와도 다르다

Ralph Loop는 목표가 만족될 때까지 Agent를 반복 실행하는 구조다.

```text
작업
 ↓
완료 여부 확인
 ↓ No
다시 작업
 ↓
완료
```

현재 목표를 끝까지 달성하는 데 유용하지만, 100번 반복했다고 101번째 Agent가 자동으로 더 나은 환경에서 시작하는 것은 아니다.

```text
반복:
  같은 환경에서 다시 시도

개선:
  다음 실행 환경 자체를 변경
```

Self-Improving Loop에는 현재 작업을 고치는 **Inner Loop**와, 다음 작업을 위해 Harness를 고치는 **Outer Loop**가 모두 필요하다.

## 3. 무엇이 개선되는가

개선 대상은 모델 weight가 아니라 Agent가 일하는 환경이다.

```text
AGENTS.md / CLAUDE.md
architecture documentation
tests
lint·static analysis
Skills
Subagents
Hooks
Scripts·Tools
Memory
Evaluation
Workflow
```

Agent가 Controller에서 Repository를 직접 호출하는 실수를 했다고 하자. 가장 단순한 해결은 “Service를 통해 호출하도록 고쳐”라고 지시하는 것이다.

더 나은 해결은 실패의 원인을 찾아 다음과 같이 바꾸는 것이다.

```text
실패
 ↓
원인 분석
 ↓
Architecture 문서 보강
 ↓
AGENTS.md에서 문서 연결
 ↓
ArchUnit Rule 보강
 ↓
실패 메시지 개선
```

이제 다음 Agent는 같은 규칙을 발견하고, 위반하면 실행 가능한 테스트 결과를 받는다.

## 4. 비싼 실패를 버리지 않는다

Agent가 오랜 시간 잘못된 방향으로 작업했다면 단순히 최종 코드만 고치고 끝내지 않는다.

그 실패가 다음 형태로 남을 수 있는지 확인한다.

```text
Regression Test
Lint Rule
Architecture Rule
Documentation
Skill
Hook
Tool
```

중요한 것은 자연어 회고를 많이 쌓는 것이 아니다. 다음 실행의 행동을 실제로 바꾸는 **실행 가능한 artifact**를 남기는 것이다.

## 5. 모든 Lesson을 AGENTS.md에 넣으면 안 된다

실패할 때마다 전역 지침에 한 줄씩 추가하면 다음 문제가 생긴다.

```text
규칙이 너무 길어짐
오래된 규칙이 남음
서로 모순되는 규칙 발생
특정 사건에만 맞는 과도한 규칙 누적
Context Pollution
```

따라서 Lesson의 위치를 선택해야 한다.

| 문제 유형 | 적합한 저장 위치 |
| --- | --- |
| 특정 버그 | Regression Test |
| 반복 코드 실수 | Lint·ArchUnit·Static Rule |
| 프로젝트 전역 원칙 | AGENTS.md·CLAUDE.md |
| 상세 설계 지식 | `docs/architecture` |
| 반복 절차 | Skill |
| 전문 판단 | Subagent |
| 반드시 실행할 검사 | Hook |
| 결정적 반복 작업 | Script·Tool |
| 검증된 경험 | Curated Memory |

원칙은 단순하다.

> 자연어 지시를 실행 가능한 검증으로 승격할 수 있다면 그렇게 한다.

## 6. Evaluation이 Memory보다 먼저다

Self-Improvement라고 하면 Vector DB나 Memory부터 떠올리기 쉽다. 하지만 평가 없이 Memory를 만들면 Agent의 잘못된 판단까지 보존할 수 있다.

안전한 순서는 다음과 같다.

```text
Execution
 ↓
Evaluation
 ↓
Evidence
 ↓
Diagnosis
 ↓
Lesson
 ↓
Memory
```

Memory는 학습 그 자체가 아니라 **검증된 학습 결과를 보존하는 장치**다.

현재 운영 환경에 적용하면 다음과 같다.

```text
K3s RCA:
  현재 endpoint·Pod·log·시간창 검증 후 기록

Artifact Registry:
  owner·runtime·permission·verification 기록

Blog publishing:
  commit + Pages build + 실제 URL 확인

Kafka/업무 수집:
  API 성공과 source/upsert 성공 분리
```

## 7. 먼저 통합 Verify 명령을 만든다

거대한 Multi-Agent System보다 먼저 필요한 것은 하나의 명확한 검증 진입점이다.

```bash
./scripts/verify.sh
```

예를 들어 다음을 한 번에 실행한다.

```text
Compile
 ↓
Unit Test
 ↓
Integration Test
 ↓
Architecture Test
 ↓
Lint
 ↓
Static Analysis
```

Frontend라면 Type Check·E2E·Browser 검증을 추가한다. Agent에게 명확한 feedback channel이 있으면, 사람이 매번 다음 명령을 알려주지 않아도 된다.

## 8. Agent에게 관측 능력을 준다

테스트가 통과해도 실제 화면이 정상이라는 보장은 없다.

```text
버튼이 화면 밖에 있음
클릭해도 반응 없음
Console error 발생
API가 500 반환
```

Frontend Agent에는 다음 관측 수단이 필요하다.

```text
Browser
DOM
Screenshot
Console
Network
```

Backend Agent에는 다음이 필요하다.

```text
Integration Test
curl
Database Query
Application Log
Metric
Trace
Load Test
```

모델 성능만큼 중요한 것은 **Agent가 자신의 결과를 관찰할 수 있는가**다.

## 9. Inner Loop와 Outer Loop

### Inner Loop

현재 작업을 성공시키는 루프다.

```text
Implement
 ↓
Test
 ↓
Analyze
 ↓
Fix
 ↓
Test
```

Claude Code의 goal loop, Stop Hook, Ralph Loop가 주로 이 문제를 해결한다.

### Outer Loop

미래 작업을 더 잘하게 만드는 루프다.

```text
Task
 ↓
Failure
 ↓
Retrospective
 ↓
Harness Improvement
 ↓
Evaluation
 ↓
Next Task
```

Self-Improving Loop의 본질은 Outer Loop다. Inner Loop가 Agent를 끝까지 움직이게 한다면, Outer Loop는 Agent가 일하는 환경을 개선한다.

## 10. Harness 변경도 평가해야 한다

새 Skill·Rule·문서를 추가했다고 바로 전역 적용하면 안 된다. 특정 문제 하나만 해결하고 다른 작업을 망가뜨릴 수 있다.

```text
Candidate Harness
 ↓
Current Problem
 ↓
Representative Tasks
 ↓
Held-out Tasks
 ↓
Regression Check
 ↓
Promote or Reject
```

예를 들어 특정 장애를 막으려고 `Never use asynchronous processing`이라는 규칙을 추가하면, 이번 장애에는 도움이 되어도 전체 시스템의 처리량과 구조를 망칠 수 있다.

Harness도 코드처럼 regression test가 필요하다.

## 11. Generator와 Evaluator를 분리한다

하나의 Agent가 구현과 평가를 모두 수행하면 자기 결과를 관대하게 평가할 수 있다.

```text
Generator
 ↓
Implementation
 ↓
Evaluator
 ↓
Score + Critique
 ↓
Generator
```

Evaluator는 코드뿐 아니라 실제 동작을 확인해야 한다.

```text
Browser 화면
API 응답
Console·Network
DB 상태
Metric·Trace
```

다만 LLM evaluator만으로 충분하지 않다. 가능한 항목은 deterministic test·schema 검사·원문 대조·권한 검사로 고정해야 한다.

## 12. Budget과 Stop Condition

Self-Improving Loop를 무한 실행하면 비용과 상태가 통제되지 않는다.

```text
Maximum Iterations
Maximum Cost
같은 실패 반복 횟수
개선 없는 라운드 수
보안·운영 변경 시 Human Review
```

예시:

```text
최대 8회 반복
같은 실패 3회면 중단
2라운드 연속 개선 없음이면 중단
권한·DB·Kubernetes 변경은 승인 대기
```

빠른 반복보다 안전한 중단 조건이 중요하다.

## 13. Curated Memory와 Untrusted Experience

Issue·Log·Web·Agent 관찰은 모두 처음에는 `Untrusted Experience`로 보는 것이 안전하다.

```text
Issues / Logs / Web / Observations
 ↓
Candidate Lesson
 ↓
Validation / Evaluation
 ↓
Trusted Test·Rule·Skill·Tool
```

현재 이 환경에서도 다음과 같이 분리한다.

```text
Memory:
  안정적인 사실·사용자 선호

Wiki:
  출처가 있는 분석·설계·RCA

Skill:
  반복 가능한 절차

Trace:
  최종 사실
```

저자·소유권이 불명확한 Script·Skill은 `author: unknown`으로 남기고, owner·runtime·source·verification만 별도로 기록하는 것이 맞다.

## 14. 가장 현실적인 도입 순서

처음부터 L5 수준의 자동 자기진화 시스템을 만들 필요는 없다.

```text
1. 통합 verify 명령
2. 실패·수정·검증 Improvement Log
3. Curated Memory
4. 반복 실패를 Test·Rule·Skill·Tool로 승격
5. Harness 변경 regression test
6. Budget·Stop Condition
7. Candidate Harness promote/reject
```

현재 환경에 대응시키면:

```text
Hermes:
  cron·보고·memory·artifact audit

Claude bots:
  프로젝트별 실행·검증·feedback

Codex:
  전문 reviewer·hook·Ouroboros worker

Ouroboros:
  run/evaluate/evolve/checkpoint/receipt
```

## 결론

Self-Improving Loop는 “AI가 스스로 학습해 모델이 똑똑해진다”는 뜻이 아니다.

```text
실패
→ 평가
→ 원인 분석
→ 실행 가능한 개선
→ 회귀 검증
→ 다음 작업에 반영
```

을 통해 Agent가 일하는 Harness가 좋아지는 과정이다.

가장 짧은 정의는 다음과 같다.

> **Every expensive failure should leave the system better than it found it.**

따라서 Agentic Coding의 경쟁력은 모델 이름만으로 결정되지 않는다. 같은 Claude Code와 Codex를 사용해도 한쪽은 같은 실패를 반복하고, 다른 한쪽은 실패를 Test·Rule·Skill·Tool로 바꾼다.

## 원문 및 참고 자료

- [원문: AI Agentic Coding의 Self-Improving Loop란 무엇인가](https://codex.epril.com/what-is-self-improving-loop-in-ai-agentic-coding)
- [OpenAI — Harness engineering](https://openai.com/index/harness-engineering/)
- [OpenAI Codex — Iterate on difficult problems with evals](https://learn.chatgpt.com/codex/use-cases/iterate-on-difficult-problems)
- [OpenAI Codex — AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md)
- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Ouroboros](https://github.com/Q00/ouroboros)

*이 글은 원문을 요약·재구성하고 현재 Agent 운영 구조에 적용한 분석이다. 원문 전체를 복제하지 않았으며, 확인하지 못한 내용은 확정하지 않았다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*
