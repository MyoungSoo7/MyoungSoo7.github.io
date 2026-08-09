---
layout: post
title: "하네스로서의 Claude Code와 Codex: 모델 호출을 넘어 실행 시스템을 설계하는 법"
date: 2026-08-09 13:00:00 +0900
categories: [AI, Engineering, Agent]
tags: [Claude Code, Codex, Harness Engineering, Agent, TDD, MCP, Git Worktree]
---

# 하네스로서의 Claude Code와 Codex

## 결론부터

Claude Code와 Codex는 단순한 대화형 코딩 도구가 아니라, **모델·도구·파일시스템·실행 프로세스·검증·승인 흐름을 연결하는 Agent 하네스**로 이해해야 한다.

```text
LLM
  = 추론·생성 엔진

Claude Code / Codex
  = 모델을 실제 저장소·shell·테스트·Git·MCP와 연결하는 실행 하네스

Harness
  = Agent가 무엇을 보고, 무엇을 실행하고, 언제 멈추며,
    어떤 증거를 남길지 정의하는 운영 시스템
```

모델이 코드를 잘 생성하는 것만으로는 production-ready 결과가 나오지 않는다. 하네스가 범위를 제한하고, 실행 결과를 수집하며, 실패 시 중단하고, 검증된 산출물만 전달해야 한다.

## 1. 하네스란 무엇인가

하네스는 자동차를 움직이는 엔진 주변의 제어·연결 장치와 비슷하다. 모델은 엔진이지만, 실제 작업은 다음 요소가 함께 있어야 가능하다.

```text
사용자 목표
  ↓
작업 계약·계획
  ↓
Agent runtime
  ├─ 모델
  ├─ 파일 읽기/쓰기
  ├─ shell·test 실행
  ├─ Git/worktree
  ├─ MCP 도구
  ├─ context·session 관리
  └─ permission·approval
  ↓
검증·증거 저장
  ↓
PR·배포·사람 승인
```

좋은 하네스는 Agent의 자율성을 무제한으로 키우지 않는다.

```text
자율 실행 범위는 넓히되
권한·시간·비용·파일·branch·네트워크 경계는 좁힌다
```

## 2. Claude Code와 Codex를 하네스로 보는 관점

### Claude Code

Claude Code는 프로젝트 디렉터리를 읽고, shell을 실행하고, 파일을 수정하고, 테스트를 수행하며, Git 작업과 MCP 연결을 조합하는 장시간 작업형 Agent runtime으로 볼 수 있다.

```text
프로젝트 문맥
→ 계획
→ 파일 탐색
→ 수정
→ 테스트
→ 결과 설명
```

강점으로 활용할 수 있는 부분:

- 긴 프로젝트 문맥의 유지
- 요구사항·코드·문서의 종합
- 단계적 구현과 대화형 조정
- MCP·채널·shell을 통한 시스템 연결
- 세션 재개와 상태 관찰

하지만 긴 세션에는 위험도 있다.

- 과거 가정이 현재 사실처럼 남을 수 있음
- 실패한 접근이 context에 누적될 수 있음
- 작업 범위가 점점 넓어질 수 있음
- 이전 Persona와 현재 Persona가 충돌할 수 있음

따라서 Claude Code를 사용할 때는 세션의 길이보다 **세션의 경계와 증거 bundle**이 중요하다.

### Codex

Codex는 독립된 구현 slice, 테스트 작성, 대안 설계, 반대 검토에 투입할 수 있는 bounded Agent runtime으로 볼 수 있다.

```text
명확한 입력
→ 제한된 worktree
→ 작은 구현
→ 테스트
→ diff·artifact 제출
→ 세션 종료
```

Codex를 하네스로 사용할 때의 핵심은 작업을 작게 고정하는 것이다.

```text
나쁜 요청:
이 기능 전체를 완성하라

좋은 요청:
PaymentCaptured 중복 이벤트에 대한 실패 테스트 하나를 추가하고
해당 테스트만 통과시키는 최소 변경을 제출하라
```

Codex를 Claude의 하위 Agent로 생각하기보다, 독립적인 구현자·반대 검토자·재현 담당자로 배치하면 판단 편향을 줄일 수 있다.

## 3. 모델·하네스·프로젝트의 책임 분리

문제가 발생했을 때 모델 탓만 하면 개선이 어렵다. 세 계층을 나눠야 한다.

| 계층 | 책임 | 실패 예 |
| --- | --- | --- |
| 모델 | 추론·코드·설명 생성 | 잘못된 API 가정 |
| 하네스 | 도구·권한·context·실행·중단 | 운영 DB 접근 허용 |
| 프로젝트 | 계약·테스트·구조·배포 | 멱등성 테스트 부재 |

예를 들어 Agent가 운영 DB를 수정했다면:

```text
모델 판단 오류일 수 있음
+ 하네스 권한 경계 실패
+ 프로젝트 승인·배포 정책 부재
```

일 가능성이 있다. 하네스 설계는 모델 능력보다 시스템 경계를 먼저 다룬다.

## 4. 하네스의 핵심 구성요소

### 4.1 Task Contract

모든 Agent 작업은 다음 계약으로 시작한다.

```yaml
task_id: settlement-payment-idempotency
objective: PaymentCaptured 중복 소비의 최종 방어를 검증
scope:
  repository: settlement
  modules:
    - settlement-service
allowed:
  - read_source
  - edit_worktree
  - run_tests
forbidden:
  - production_db_write
  - secret_read
  - deploy
  - push_without_approval
success_evidence:
  - failing_test_before_change
  - passing_test_after_change
  - diff
  - test_output
stop_conditions:
  - unrelated_file_change
  - missing_contract
  - production_access_required
```

### 4.2 Worktree Isolation

여러 Agent가 같은 저장소를 동시에 수정하면 병렬화가 아니라 충돌 자동화가 된다.

```bash
git worktree add /tmp/agent-settlement-123 \
  -b agent/settlement-123 origin/main
```

권장 원칙:

```text
한 작업 = 한 worktree
한 worktree = 한 branch
한 branch = 명확한 delivery owner
```

Claude와 Codex가 같은 파일을 동시에 수정해야 한다면 각각 별도 worktree에서 수행하고, Moderator가 diff·테스트·설계를 비교한다.

### 4.3 Tool and MCP Boundary

모든 Agent에게 `run_shell(command)`를 주는 것은 하네스가 없는 것과 비슷하다.

```text
나쁜 도구:
run_shell(command)

좋은 도구:
get_pod_status(namespace)
read_schema(service)
run_test_suite(name)
get_ci_status(repo, branch)
```

MCP는 Agent의 도구 경계로 사용할 수 있다.

```text
Scout MCP
  read_wiki
  read_git_diff

Builder MCP
  read_fixture
  run_test

Reviewer MCP
  get_ci_status
  inspect_trace

Operator MCP
  create_pr_after_approval
```

도구 이름과 schema가 좁을수록 승인·감사·실패 처리가 쉬워진다.

### 4.4 Session and Context Control

세션 재개는 편리하지만 이전 대화가 무조건 좋은 context는 아니다.

```text
긴 세션
  → 가정·실패·오래된 지시가 누적

새 세션 + evidence bundle
  → 최신 계약·diff·테스트·미해결 항목만 전달
```

세션 사이에 다음 artifact를 남긴다.

```text
plan.md
contract.md
test-output.txt
findings.md
decision.md
handoff.md
```

`/clear`는 대화 문맥을 초기화하지만 Git branch·worktree·commit을 삭제하지 않는다. 세션을 초기화할 때도 작업 artifact를 먼저 저장해야 한다.

### 4.5 Permission and Approval

Persona에 “read-only reviewer”라고 적는 것만으로는 read-only가 되지 않는다.

실제 권한은 다음 계층에서 강제해야 한다.

```text
OS user/group
→ filesystem permission
→ container/sandbox
→ MCP allowlist
→ Git branch protection
→ CI gate
→ human approval
```

```text
reviewer:
  push 금지
  운영 DB 금지
  secret 금지

operator:
  승인된 branch만 push
  deploy는 사람 승인
```

## 5. TDD와 하네스

TDD는 Agent에게 테스트를 마지막에 만들라고 하는 규칙이 아니라, 하네스의 실행 단위를 정의하는 방법이다.

```text
RED
  실패하는 테스트 작성

GREEN
  최소 구현

REFACTOR
  구조 개선

GATE
  명령·출력·diff·artifact 검증
```

예를 들어 상담봇의 근거 검증은 다음 Loop로 나눈다.

```text
Loop 1: 근거 없는 질문은 handoff
Loop 2: 근거 있는 질문은 citation 반환
Loop 3: citation 없는 답변 차단
Loop 4: trace_id 반환
Loop 5: API contract 통과
```

각 Loop마다 하네스가 기록해야 한다.

```text
입력
명령
기대 결과
실제 결과
변경 파일
다음 판단
```

Agent가 “테스트 통과”라고 말하는 것보다 실제 명령 출력이 중요하다.

## 6. Claude와 Codex의 조합 패턴

### 패턴 A: Claude 설계 → Codex 구현 → Claude 리뷰

```text
Claude:
  요구사항·계약·테스트 계획

Codex:
  isolated worktree에서 구현

Claude:
  diff·테스트·설계 정합성 리뷰
```

복잡한 도메인과 작은 구현 slice에 적합하다.

### 패턴 B: Claude 구현 → Codex 반대 검토 → 사람 승인

```text
Claude:
  구현·테스트

Codex:
  반례·보안·멱등성·회귀 검토

Human:
  delivery 승인
```

금융·정산·운영 변경에 적합하다.

### 패턴 C: Codex 두 개의 독립 대안 비교

```text
Codex A:
  synchronous API 대안

Codex B:
  event-driven 대안

Moderator:
  비용·장애·대사·rollback 비교
```

모델 수를 늘리는 것보다 각 결과를 독립적인 evidence로 남기는 것이 중요하다.

## 7. 하네스에서 관찰성은 기능이다

Agent 작업도 운영 시스템처럼 관찰해야 한다.

```json
{
  "task_id": "settlement-payment-idempotency",
  "agent": "codex-reviewer-01",
  "runtime": "codex",
  "repository_commit": "70d24bb",
  "worktree": "/tmp/agent-settlement-123",
  "persona": "adversarial-reviewer",
  "tools": ["read_source", "run_tests"],
  "started_at": "...",
  "finished_at": "...",
  "test_status": "passed",
  "commit_sha": "...",
  "handoff": "..."
}
```

측정할 수 있는 지표:

```text
작업 완료율
테스트 통과율
rework rate
근거 coverage
blocked rate
unsafe action attempt
평균 context 사용량
작업당 비용
handoff 재개 성공률
```

코드 생성량이나 PR 개수만으로 Agent 생산성을 판단하면 안 된다.

```text
실질 생산성
= 사용자 가치 × 품질 × 재사용성
  / (실행 비용 + 리뷰 비용 + 재작업 비용 + 장애 비용)
```

## 8. 실패와 중단을 하네스에 포함한다

좋은 하네스는 성공 경로만 자동화하지 않는다.

```text
API timeout
→ 무조건 retry하지 않음

권한 부족
→ 다른 credential로 우회하지 않음

테스트 실패
→ 임의 skip하지 않음

계약 불명확
→ 구현보다 질문·blocked 보고

context 초과
→ 요약 artifact 저장 후 새 세션
```

종료 상태를 구조화한다.

```text
completed
failed
blocked
waiting-approval
timeout
converged
```

`completed`는 모델의 문장이 아니라 다음 증거 조합으로 판정한다.

```text
actual command output
+ expected test result
+ diff check
+ commit SHA
+ PR/CI handle
```

## 9. 우리 환경에 적용하는 구조

현재 운영 도구를 하네스 계층으로 배치하면 다음과 같다.

```text
Hermes
  작업 큐·정책·상태·사용자 승인

Claude 봇1~4
  지속적인 프로젝트 worker

Codex
  bounded 구현·반대 검토·재현 worker

tmux
  세션 지속성·원격 운영

cmux
  Mac의 workspace·알림·시각적 관찰

MCP
  도구·데이터 권한 경계

Git worktree
  변경 격리

TDD/CI
  실행 증거

Ouroboros/LION
  PR·코드·아키텍처·종합 검토

GitHub
  승인된 전달 결과
```

이 구조에서 Claude와 Codex를 단순히 여러 개 켜는 것보다 중요한 것은 다음이다.

```text
작업 ID
Identity
Persona
branch
worktree
허용 도구
완료 조건
evidence
```

## 10. web01 AI 포트폴리오 적용 예

삼성SDS형 상담·수리·보이스봇 작업을 하네스로 나누면:

```text
Scout:
  요구사항·fixture·기존 API 조사

Architect:
  RAG·CRM·voice flow 계약 정의

Builder:
  isolated worktree에서 API/UI 구현

Reviewer:
  citation·handoff·PII·접근성 검토

Evaluator:
  질문 세트·retrieval·groundedness 측정

Operator:
  PR·CI·demo URL 검증
```

각 Agent가 “AI 기능을 구현했다”고 보고하려면:

```text
API response
citation
handoff
trace_id
test output
evaluation result
```

이 있어야 한다. FakeLLM·Synthetic CRM·local Qdrant와 실제 Gemini·CRM·STT/TTS를 분리해 기록하는 것도 하네스의 책임이다.

## 11. Settlement 적용 예

Settlement의 주문·결제·정산·원장 변경에는 더 강한 하네스가 필요하다.

```text
계획:
  order → payment → settlement → ledger → payout → reconciliation

TDD:
  멱등성·금액 불변식·Outbox·재처리·rollback

Builder:
  별도 worktree

Reviewer:
  payment_id unique·processed_events·DLT·대사

Operator:
  CI·PR·승인 확인
```

금융 원장 변경에서 하네스가 허용하면 안 되는 것:

```text
운영 DB 직접 수정
원장 UPDATE
Secret 출력
검증 전 push
대사 실패를 성공으로 표시
```

## 12. Claude Code와 Codex를 비교하는 올바른 방식

절대적인 모델 순위를 정하기보다 작업 적합성과 하네스 품질을 비교한다.

| 항목 | Claude Code | Codex |
| --- | --- | --- |
| 적합한 역할 | 설계·종합·장기 조정 | bounded 구현·반대 검토 |
| 세션 방식 | 지속 세션·프로젝트 문맥 | 짧은 계약형 세션 |
| 좋은 입력 | 요구사항·architecture·운영 맥락 | 파일·실패 테스트·명확한 acceptance criteria |
| 좋은 출력 | decision·plan·review·handoff | diff·test·artifact |
| 주요 위험 | context 오염·범위 확장 | 입력 범위가 넓으면 임의 구현 |
| 보완 장치 | `/clear`, 요약 artifact, 단계 게이트 | 작은 task, worktree, hard timeout |

이 비교는 제품의 모든 버전과 작업에 대한 절대적 사실이 아니다. 실제 작업별 결과로 평가해야 한다.

## 13. 완성된 Agent Harness 체크리스트

```text
[ ] Task contract가 존재한다
[ ] Identity와 Persona가 분리돼 있다
[ ] worktree와 branch가 격리돼 있다
[ ] 허용·금지 도구가 명시돼 있다
[ ] 운영 DB·Secret·배포가 기본 차단돼 있다
[ ] TDD RED 단계가 기록돼 있다
[ ] Loop마다 기대/실제 결과가 있다
[ ] timeout·retry·cost limit가 있다
[ ] 실패·blocked·approval 상태가 있다
[ ] diff·test·Trace가 보존된다
[ ] Builder와 Reviewer가 분리된다
[ ] commit·PR·CI 결과가 검증된다
[ ] rollback 방법이 존재한다
[ ] 사람 승인 지점이 명확하다
```

## 결론

Claude Code와 Codex를 하네스로 사용한다는 것은 모델에게 더 많은 권한을 주는 것이 아니다. 모델의 능력을 실제 개발 흐름에 연결하되, **작업 계약·격리·도구 경계·TDD·관찰성·승인·rollback을 함께 설계하는 것**이다.

```text
Claude Code
  = 장기 문맥을 가진 설계·조정 하네스

Codex
  = 독립 작업과 반대 검토를 수행하는 bounded 하네스

Hermes
  = 여러 하네스의 작업·정책·증거 오케스트레이터
```

**한 문장 요약:** Claude Code와 Codex의 가치는 모델 호출 자체가 아니라, 모델을 저장소·도구·테스트·Git·MCP·승인 흐름에 안전하게 연결해 재현 가능한 개발 루프를 만드는 하네스 역할에 있다.

## 참고 자료

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [OpenAI Codex](https://github.com/openai/codex)
- [Model Context Protocol Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [tmux](https://github.com/tmux/tmux)
- [cmux](https://github.com/manaflow-ai/cmux)

> 이 글은 Claude Code·Codex·Hermes·MCP·tmux·worktree·TDD를 결합한 Agent 운영 설계에 대한 고찰이다. 특정 제품의 기능과 성능은 버전·설정·실제 실행 Trace로 다시 검증해야 한다.
