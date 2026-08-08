---
layout: post
title: "Claude와 Codex를 운영하는 법: 세션별 Identity와 상황별 Persona의 분리"
date: 2026-08-09 01:00:00 +0900
categories: [AI, Engineering, Agent]
tags: [Claude Code, Codex, Identity, Persona, Session, Agent Orchestration, Harness Engineering]
---

# Claude와 Codex를 운영하는 법

## 핵심 결론

Claude와 Codex를 안정적으로 운영하려면 **Identity는 세션의 지속적인 책임과 권한으로 고정하고, Persona는 현재 작업·검증 단계·위험도에 따라 교체해야 한다.**

```text
Identity
= 누구이며 어떤 책임·권한·기억·작업영역을 갖는가

Persona
= 지금 어떤 관점·말투·판단 기준으로 일하는가

Task Context
= 이번 세션이 처리할 구체적인 문제

Policy/Harness
= 무엇을 할 수 있고 어디서 멈춰야 하는가
```

Persona를 Identity처럼 고정하면 Agent가 모든 작업에서 같은 태도를 유지하려 한다. 반대로 Identity까지 매번 바꾸면 책임·권한·추적성이 사라진다.

## 1. Claude와 Codex를 같은 Agent로 보면 안 되는 이유

Claude와 Codex는 모두 코드를 다룰 수 있지만 운영상 같은 역할로 취급하면 안 된다.

| 구분 | Claude | Codex |
|---|---|---|
| 주 역할 | 장시간 문맥 유지·설계·조정·대화 | 독립 구현·반대 검토·대안 탐색 |
| 강점 | 요구사항 종합·설명·문서·운영 맥락 | 제한된 작업의 코드 수정·테스트·비판 |
| 적합한 위치 | Orchestrator·상시 Worker·Reviewer | Builder·Counter-reviewer·Spare implementation |
| 세션 전략 | 지속 세션과 프로젝트 문맥 | 짧고 명확한 bounded session |
| 완료 기준 | 근거·상태·다음 단계 보고 | diff·test·artifact 제출 |

이 표는 모델의 절대적인 성능 순위가 아니라 **운영 역할을 분리하기 위한 설계 가설**이다. 실제 모델 동작은 버전·설정·도구·작업에 따라 달라지므로 Trace와 결과로 검증해야 한다.

## 2. Identity는 무엇으로 구성되는가

Identity는 단순한 이름이나 말투가 아니다.

```yaml
identity:
  id: settlement-bot-03
  owner: platform-engineering
  mission: settlement 코드의 안정적인 변경과 검증
  repository: /srv/repos/settlement
  worktree_policy: one-task-one-worktree
  default_role: builder
  allowed_data: source, tests, generated reports
  forbidden_data: secrets, production customer data
  delivery_owner: hermes
```

Identity가 유지해야 하는 것은 다음이다.

- 작업 주체 ID
- 책임 영역
- 기본 저장소와 worktree 정책
- 허용 도구와 금지 도구
- 기본 보안 경계
- 결과를 전달할 상위 오케스트레이터
- 세션·작업·commit의 추적 키

Identity는 세션이 바뀌어도 쉽게 바꾸지 않는다. `bot3`가 오전에는 구현하고 오후에는 리뷰를 하더라도, 누가 어떤 작업을 했는지 추적할 수 있어야 한다.

## 3. Persona는 교체 가능한 작업 모드다

Persona는 Identity 위에 임시로 얹는 작업 모드다.

```text
settlement-bot-03
  ├─ explorer persona
  ├─ builder persona
  ├─ adversarial reviewer persona
  ├─ test investigator persona
  └─ release reporter persona
```

같은 Identity가 여러 Persona를 적용할 수 있다.

### Explorer

```text
목표: 구조와 근거 파악
권한: read-only
출력: 파일·symbol·test·unknown 목록
금지: 코드 수정·push·배포
```

### Builder

```text
목표: 지정된 작은 변경 구현
권한: 격리 worktree write
출력: diff·test·변경 이유
금지: unrelated file 수정·운영 접근
```

### Adversarial Reviewer

```text
목표: 실패 가능성과 반례 찾기
권한: diff·source·test read
출력: severity·evidence·reproduction
금지: 검증 전 승인·근거 없는 칭찬
```

### Test Investigator

```text
목표: 실패를 재현하고 원인을 분리
권한: 테스트·로그·fixture
출력: 재현 명령·actual output·root cause 후보
금지: 실패를 임의 skip
```

### Release Reporter

```text
목표: 실제 전달 증거 정리
권한: commit·remote·CI·PR 조회
출력: SHA·URL·status·known limitation
금지: 실행하지 않은 성공 주장
```

## 4. 세션은 Persona를 안전하게 적용하는 경계다

Persona를 전역 파일 하나에 계속 덧붙이면 세션 간 오염이 생긴다.

```text
나쁜 방식:
전역 Claude 설정에 모든 역할 지시를 누적

좋은 방식:
Identity 고정
→ 세션 시작 시 Task Persona 선택
→ 세션 종료 시 evidence 저장
→ 다음 세션은 새 Persona로 초기화
```

세션 시작 기록의 예시는 다음과 같다.

```yaml
session_id: settlement-review-2026-08-09-01
identity_id: settlement-bot-03
persona: adversarial-reviewer
objective: PaymentCaptured 멱등성 경로 검토
repository_commit: 70d24bb
allowed_tools:
  - read_file
  - git_diff
  - run_tests
forbidden_tools:
  - kubectl_apply
  - production_db_write
  - git_push
success_evidence:
  - findings.md
  - reproduction-command.txt
stop_conditions:
  - missing_source_evidence
  - production_access_required
```

이 기록이 있으면 Persona가 바뀌어도 Identity·commit·권한·목표를 복원할 수 있다.

## 5. 상황별 Persona 전환 규칙

Persona를 마음대로 바꾸면 역할 회피가 발생한다. 전환 조건을 명시해야 한다.

```text
탐색 전:
explorer

계약과 테스트 계획 확정 후:
builder

코드 변경 완료 후:
adversarial-reviewer

테스트 실패 시:
test-investigator

CI·PR 전달 단계:
release-reporter
```

전환 시 반드시 기록한다.

```json
{
  "session_id": "settlement-review-2026-08-09-01",
  "identity_id": "settlement-bot-03",
  "from_persona": "builder",
  "to_persona": "adversarial-reviewer",
  "reason": "implementation slice passed unit tests",
  "evidence": ["test-output.txt", "git-diff.patch"]
}
```

## 6. Persona와 권한은 별개다

다음 문장은 안전장치가 아니다.

```text
너는 read-only reviewer다.
```

실제 shell과 credential이 그대로 있으면 Agent는 여전히 쓰기·삭제·배포를 시도할 수 있다.

실제 권한은 아래 계층에서 enforce해야 한다.

```text
OS account/group
→ filesystem permission
→ isolated worktree
→ container/sandbox
→ MCP allowlist
→ Git branch protection
→ CI/CD approval
```

Persona는 “어떻게 판단할 것인가”를 정하고, Policy는 “무엇을 실행할 수 있는가”를 정한다.

```text
Persona가 push를 원해도
Policy가 push 금지면 push하지 않는다.
```

## 7. Claude 세션 운영 모델

Claude는 긴 문맥과 조정이 필요한 세션에 적합한 운영 모델을 가질 수 있다.

```text
Claude Identity
  = 프로젝트 오너/오케스트레이터

세션 Persona
  = 설계자·운영자·리뷰어·문서 작성자 중 하나

세션 Artifact
  = plan·decision·trace·report
```

하지만 장시간 세션은 다음 위험이 있다.

- 이전 가정이 현재 사실처럼 남는다.
- 실패한 접근이 문맥에 누적된다.
- Persona 전환 후 이전 역할의 편향이 남는다.
- context 사용량이 늘어 핵심 근거가 묻힌다.

따라서 단계 전환 시 요약을 새 문서로 고정한다.

```text
exploration.md
implementation-contract.md
review-findings.md
release-report.md
```

새 세션을 시작할 때는 전체 대화를 재주입하지 말고 이 evidence bundle을 읽힌다.

## 8. Codex 세션 운영 모델

Codex는 독립된 bounded task에 투입하는 것이 안전하다.

```text
Codex session
  입력: 파일·계약·실패 테스트·제약
  작업: 한 slice 구현 또는 반대 검토
  출력: diff·test·unknown
  종료: artifact 제출 후 세션 종료
```

Codex를 Claude와 같은 worktree에 동시에 두지 않는다.

```text
Claude worktree A
Codex worktree B
        ↓
Moderator가 diff와 test 비교
```

Codex를 반대 검토자로 사용할 때는 “무조건 결함을 찾아라”가 아니라 다음 형식이 좋다.

```text
주장:
근거:
반례:
재현 명령:
심각도:
확신도:
미확인:
```

이 형식은 토론을 감정적 찬반이 아니라 검증 가능한 주장으로 바꾼다.

## 9. Identity·Persona·Task Context의 3층 구조

세션을 다음 세 층으로 생각하면 충돌이 줄어든다.

```text
┌─────────────────────────┐
│ Identity                │ 고정: 주체·책임·기본권한
├─────────────────────────┤
│ Persona                 │ 교체: 관점·판단스타일·출력형식
├─────────────────────────┤
│ Task Context            │ 단기: 파일·이슈·테스트·목표
└─────────────────────────┘
```

예시:

```text
Identity:
  settlement-bot-03

Persona:
  adversarial-reviewer

Task:
  PaymentCaptured 중복 이벤트의 정산 중복 생성 방어 검토

Evidence:
  PaymentEventKafkaConsumer.java
  processed_events migration
  settlements.payment_id unique
```

이 구조에서 다음 작업은 Persona만 바꾼다.

```text
같은 Identity
→ test-investigator
→ 동일 repository boundary
→ 다른 실패 테스트와 출력 계약
```

## 10. 세션 간 기억과 격리

모든 것을 기억시키는 것이 좋은 Agent 운영은 아니다.

### Identity에 남길 것

```text
역할·소유 영역
기본 보안 경계
작업 방식
불변의 프로젝트 규칙
```

### Persona에 남길 것

```text
현재 판단 기준
출력 형식
검토 렌즈
이번 단계의 금지 행동
```

### Task Context에 남길 것

```text
현재 commit
현재 diff
실패 로그
테스트 명령
미해결 질문
```

완료된 임시 상태를 장기 기억에 넣지 않는다.

```text
PR 번호·임시 PID·일시적 오류
→ session artifact

사용자의 안정적 선호·프로젝트의 지속 규칙
→ memory/skill
```

## 11. Claude↔Codex 하브루타에서 Persona를 운용하는 법

권장 라운드는 다음과 같다.

```text
Round 0: 공동 문제·소스 commit 고정
Round 1: Claude Explorer 분석
Round 2: Codex Adversarial Reviewer 반론
Round 3: Claude Reconciler 근거 재검증
Round 4: Codex Test Investigator 재현 확인
Round 5: Moderator 최종 종합
```

각 라운드의 Identity는 유지하지만 Persona는 바뀔 수 있다.

```text
Claude Identity: architecture-orchestrator
  Explorer → Reconciler → Synthesizer

Codex Identity: independent-counterpart
  Reviewer → Test Investigator
```

중요한 것은 Claude와 Codex가 서로의 결론을 곧바로 사실로 채택하지 않는 것이다.

```text
결론
→ 근거
→ 독립 검증
→ 합의/미합의/미확인
```

## 12. 실패 패턴

### Persona를 Identity처럼 굳힌다

항상 “보수적인 리뷰어”인 Agent는 구현 단계에서도 과도하게 멈출 수 있다. 반대로 항상 “자율 구현자”인 Agent는 운영·리뷰 단계에서 범위를 넘을 수 있다.

### Identity를 작업마다 새로 만든다

작업마다 새로운 이름과 책임을 만들면 누가 어떤 변경을 했는지 추적하기 어렵다.

### System prompt에 권한을 적는다

권한은 prompt가 아니라 runtime과 infrastructure에서 enforcement해야 한다.

### 전역 Persona를 계속 누적한다

과거 작업의 규칙과 현재 작업의 규칙이 충돌한다. 세션별 Persona manifest를 사용한다.

### Model 특성을 사실처럼 일반화한다

“Claude는 항상 설계를 잘한다”, “Codex는 항상 구현을 잘한다”는 검증되지 않은 일반화다. 모델·버전·도구·작업 난이도별 평가 결과로 판단한다.

## 13. 실전 Persona manifest

```yaml
identity:
  id: settlement-bot-03
  runtime: claude-code
  mission: settlement 변경의 안전한 구현과 검증
  repository_boundary: /srv/repos/settlement
  default_worktree_policy: isolated

session:
  id: settlement-order-flow-review
  commit: 70d24bb
  persona: adversarial-reviewer
  objective: 주문→결제→정산 이벤트 경계의 실패 경로 검토

persona:
  stance: evidence-first and adversarial
  focus:
    - transactional outbox
    - PaymentCaptured idempotency
    - database uniqueness
    - reconciliation
  output:
    - claim
    - evidence
    - impact
    - reproduction
    - unknowns

policy:
  allow:
    - read_source
    - read_migration
    - run_tests
    - inspect_git_diff
  deny:
    - production_db_write
    - secret_read
    - deploy
    - push

completion:
  required:
    - findings.md
    - test-output.txt
    - evidence-paths
  stop_if:
    - source_commit_changed
    - runtime_trace_missing
    - production_access_required
```

## 14. 평가 지표

Persona를 유연하게 적용했는지 감으로 판단하지 않는다.

```text
role adherence
  지정된 역할 밖의 행동 비율

claim evidence coverage
  주장 중 파일·로그·테스트 근거가 있는 비율

rework rate
  후속 Agent가 되돌린 변경 비율

handoff completeness
  다음 세션이 artifact만으로 재개 가능한 비율

unsafe action attempts
  차단된 운영·보안 위반 시도 수

context contamination
  이전 Persona의 지시가 현재 결과에 남은 비율
```

이 지표를 측정하기 전에는 Persona 운영이 생산성을 높였다고 단정하지 않는다.

## 결론

Claude와 Codex를 잘 운영하는 핵심은 모델에게 더 강한 캐릭터를 부여하는 것이 아니다.

```text
Identity는 고정한다.
Persona는 상황에 맞게 교체한다.
Task Context는 짧게 유지한다.
Policy는 실제 runtime에서 강제한다.
Evidence는 세션 사이를 연결한다.
```

권장 구조는 다음과 같다.

```text
Hermes
  → Identity·Task·Persona manifest 관리

Claude
  → 긴 문맥의 설계·조정·종합 세션

Codex
  → 독립된 구현·반대 검토·재현 세션

MCP
  → 도구·데이터 권한 경계

tmux/cmux
  → 세션 지속성과 관찰

Git worktree
  → 변경 격리

CI/Ouroboros
  → 최종 검증 게이트
```

**한 문장 요약:** Identity는 “누가 책임지는가”를 고정하고, Persona는 “지금 어떤 관점으로 일하는가”만 바꾸며, 둘 사이를 Policy·Harness·Evidence로 연결해야 여러 Agent가 유연하면서도 추적 가능하게 협업한다.

## 참고 자료

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [OpenAI Codex](https://github.com/openai/codex)
- [Model Context Protocol Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [tmux](https://github.com/tmux/tmux)
- [cmux](https://github.com/manaflow-ai/cmux)
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)

> 이 글은 Claude·Codex·MCP·tmux·worktree를 결합한 Agent 운영 설계에 대한 고찰이다. 특정 모델의 성능·특성은 고정된 사실이 아니라 버전·도구·작업별 Trace와 평가 결과로 확인해야 한다.
