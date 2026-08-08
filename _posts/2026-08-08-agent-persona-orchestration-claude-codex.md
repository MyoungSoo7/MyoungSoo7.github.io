---
layout: post
title: "Claude·Codex Agent 군단과 봇 페르소나를 관리하는 법"
date: 2026-08-08 23:40:00 +0900
categories: [AI, Engineering, DevOps]
tags: [Claude Code, Codex, Agent, Persona, Harness Engineering, tmux, MCP, Ouroboros]
---

# Claude·Codex Agent 군단과 봇 페르소나를 관리하는 법

## 문제는 Agent 수가 아니라 역할 충돌이다

Claude Code, Codex, Gemini CLI, OpenCode 같은 Agent를 여러 개 실행하는 것은 어렵지 않다.

```text
tmux new-session
cmux workspace
subprocess
worktree
```

어려운 부분은 여러 Agent가 동시에 다음을 수행할 때 생긴다.

- 서로 다른 저장소를 수정한다.
- 같은 작업을 중복한다.
- 각자 다른 판단 기준을 사용한다.
- 하나의 Agent가 조사·구현·리뷰·배포를 모두 하려고 한다.
- 대화형 Persona가 실제 권한 정책처럼 오해된다.

따라서 Agent 운영은 “Claude를 몇 개 켜는가”가 아니라 다음 질문으로 설계해야 한다.

```text
누가 무엇을 판단하는가?
어떤 저장소를 읽고 쓰는가?
어떤 도구를 호출할 수 있는가?
어떤 조건에서 멈추는가?
결과를 누가 검증하는가?
```

## Persona와 정책을 분리한다

가장 중요한 원칙은 **Persona는 행동 스타일이고, 정책은 실행 경계**라는 점이다.

```text
Persona
= 어떤 관점과 말투로 생각하는가

Policy
= 무엇을 할 수 있고 무엇을 할 수 없는가

Harness
= 작업을 어떤 단계와 검증으로 실행하는가
```

예를 들어 “신중한 SRE 봇”이라고 Persona에 적었다고 해서 실제로 `kubectl delete`를 막을 수 있는 것은 아니다.

```text
Persona 문장
≠ 권한 통제
≠ Secret 차단
≠ Git push 승인
```

실행 권한은 다음 계층에서 제어해야 한다.

```text
OS user/group
→ filesystem permission
→ container/sandbox
→ MCP tool allowlist
→ repository branch protection
→ CI gate
→ human approval
```

## 추천 Agent 역할 모델

### 1. Scout — 조사자

```text
권한: read-only
도구: web, git log, grep, Graphify, Wiki
출력: 사실·출처·미확인 목록
```

Scout는 코드를 수정하지 않는다. 문제를 빠르게 이해하고 다음 Agent가 읽을 증거 묶음을 만든다.

### 2. Builder — 구현자

```text
권한: isolated worktree write
도구: 파일 편집, 테스트, 로컬 빌드
출력: diff, 테스트 결과, 변경 요약
```

Builder는 `main`이나 운영 worktree에서 직접 작업하지 않는다.

```bash
git worktree add /tmp/agent-issue-123 -b agent/issue-123 main
```

### 3. Reviewer — 반대 검토자

```text
권한: read-only 또는 별도 검토 worktree
도구: diff, 테스트, 보안 스캔, dependency 검사
출력: 승인·수정 요청·차단 사유
```

Reviewer는 Builder와 같은 Persona를 쓰면 안 된다. “완료시키고 싶은 마음”이 검토를 오염시킬 수 있기 때문이다.

### 4. Operator — 전달자

```text
권한: 승인된 branch push/PR
도구: GitHub API, CI 상태, release metadata
출력: commit SHA, PR URL, CI 결과
```

Operator는 코드를 새로 고치지 않고 검증된 산출물을 전달한다.

### 5. Moderator — 사회자

Claude와 Codex를 함께 쓰는 하브루타에서는 Moderator가 필요하다.

```text
공동 텍스트 고정
→ 주장 수집
→ 반대 논거 요청
→ 근거 검증
→ 합의·미합의 분리
→ 최종 종합
```

Moderator가 토론자의 발언을 그대로 사실로 채택하면 토론이 아니라 생성형 확증 루프가 된다.

## 우리 봇1~4 모델에 적용하기

현재 운영 구조를 역할로 표현하면 다음과 같다.

```text
봇1~4
= Claude 상시 워커

Codex
= 필요할 때만 생성하는 임시 반대 논객 또는 구현 보조자

Hermes
= 중앙 오케스트레이터·상태·근거·결과 관리

Ouroboros
= PR 검토·전달 게이트

Leopard/LION
= 라우팅·종합 평가
```

여기서 중요한 것은 봇1~4가 모두 같은 “만능 Persona”가 되지 않도록 하는 것이다.

예시:

```text
봇1: Settlement 금융 불변식·원장·대사 검토
봇2: 정합성·Watermark·하브루타 분석
봇3: 코드 구현·테스트·PR 준비
봇4: 보안·운영·배포 검증
```

역할을 나누더라도 저장소·branch·작업 ID를 명시해야 한다.

```json
{
  "agent": "bot3",
  "task_id": "settlement-card-phase2",
  "role": "builder",
  "repo": "settlement",
  "worktree": "/Users/lms/settlement-wt-card",
  "branch": "feature/card-phase2",
  "allowed_actions": ["read", "edit-worktree", "test"],
  "push": false,
  "state": "busy"
}
```

## Persona 파일은 짧고 검증 가능하게 만든다

좋은 Persona에는 다음이 들어간다.

```text
역할
목표
읽을 수 있는 근거
허용 도구
금지 행동
완료 조건
보고 형식
```

예시:

```markdown
# Settlement Reviewer

역할: 금융 정산 변경의 반대 검토자

목표:
- 원장 불변식과 대사 경로의 깨짐 여부 확인
- Outbox/Kafka 멱등성·재처리 경로 확인

허용:
- 소스·테스트·migration·diff 읽기
- read-only 테스트 실행

금지:
- 운영 DB 쓰기
- Secret 출력
- main push
- 배포·rollout

완료 조건:
- 주장별 파일/라인/테스트 근거
- 심각도와 미확인 사항
- rollback 영향
```

반대로 다음과 같은 Persona는 너무 추상적이다.

```text
너는 최고의 시니어 엔지니어다.
모든 문제를 자율적으로 해결하라.
```

이 문장은 책임·범위·종료 조건을 정의하지 않는다.

## Persona 상속과 충돌을 관리한다

여러 계층의 지시가 합쳐지면 충돌이 생긴다.

```text
Global policy
→ Project AGENTS/CLAUDE.md
→ Skill
→ Task prompt
→ Runtime user message
```

권장 우선순위는 다음과 같이 문서화한다.

```text
보안·권한·사용자 명시 지시
→ 프로젝트 계약
→ 작업 역할
→ 스타일 Persona
```

예를 들어 Persona가 “자동 push”라고 해도 프로젝트 규칙이 “승인 전 push 금지”라면 push하지 않는다. Persona는 정책을 덮어쓸 수 없다.

## Agent 상태를 명시적으로 관리한다

화면을 읽어 “뭔가 하는 것 같다”고 판단하면 안 된다. 상태는 구조화된 파일·이벤트·프로세스로 관리한다.

```json
{
  "agent": "bot2",
  "state": "blocked",
  "task_id": "reconciliation-review",
  "stage": "evidence-validation",
  "context_usage": "unknown",
  "last_evidence": "tests/contract-report.json",
  "updated_at": "2026-08-08T23:00:00+09:00"
}
```

가능한 상태:

```text
idle
ready
busy
blocked
waiting-approval
failed
completed
```

`context_usage`는 공식 조회 경로가 없으면 `unknown`으로 둔다. 화면에 보이는 숫자를 임의로 API 수준의 정확한 수치처럼 보고하지 않는다.

## Claude와 Codex를 함께 쓸 때

### 같은 작업에서 경쟁시키지 않는다

나쁜 구조:

```text
Claude와 Codex가 같은 worktree를 동시에 수정
```

좋은 구조:

```text
Claude worktree A: 구현
Codex worktree B: 독립 대안 또는 반대 검토
Moderator: diff·테스트·근거 비교
```

### 하브루타 단계

```text
1. 공동 텍스트와 질문 고정
2. Claude 주장 생성
3. Codex 반대 주장 생성
4. 각 주장에 source/file/test 근거 부착
5. Moderator가 근거 검증
6. 합의·미합의·미확인 분리
7. 최종 보고서 작성
8. 임시 Codex 종료
```

토론 횟수보다 종료 조건이 중요하다.

```text
새로운 검증 가능한 논거가 없음
반대 논거가 반복됨
남은 쟁점이 미확인 자료에 의존
```

## 100개 Agent를 관리하려면

앞서 살펴본 대량 Agent 사례처럼 작업 슬롯을 많이 만들려면 Persona만 늘려서는 안 된다.

```text
Task queue
→ scheduler
→ concurrency limit
→ worktree allocator
→ Agent
→ test gate
→ reviewer
→ delivery queue
```

필수 제어:

- 저장소·branch·worktree 격리
- 동시 실행 수 제한
- API rate limit
- 중복 작업 fingerprint
- 비용 예산
- 최대 라운드·timeout
- 실패 후 재시도 횟수
- PR 생성 전 승인
- 결과 artifact 보존

실제 운영에서는 100개를 모두 동시에 실행하기보다:

```text
대기 슬롯 100개
실행 슬롯 4~16개
검토 슬롯 2~4개
전달 슬롯 1개
```

처럼 분리하는 것이 안전하다.

## MCP는 Persona의 도구 경계다

MCP를 쓰면 Persona 파일보다 더 명확하게 권한을 나눌 수 있다.

```text
Scout MCP
  search_wiki
  read_git_diff

Reviewer MCP
  read_test_report
  run_readonly_scan

Operator MCP
  get_ci_status
  create_pr_after_approval
```

나쁜 방식:

```text
모든 Agent에게 run_shell(command)를 제공
```

좋은 방식:

```text
get_pod_status(namespace)
read_schema(service)
run_test_suite(name)
get_ci_status(repo, branch)
```

도구가 작을수록 감사·권한·실패 처리가 쉬워진다.

## 완료를 판단하는 증거 계약

Agent가 “완료했다”고 말하는 것만으로 완료 처리하면 안 된다.

```text
구현 완료:
  diff + test output

PR 완료:
  commit SHA + remote branch + PR URL

배포 완료:
  CI success + rollout status + endpoint health

하브루타 완료:
  라운드 기록 + 근거 검증 + Codex 종료

블로그 게시 완료:
  commit + Pages build + 실제 URL HTTP 200
```

이 계약이 있어야 Persona가 바뀌어도 시스템의 품질 기준은 유지된다.

## 흔한 실패 패턴

### 1. 모두가 PM이다

모든 Agent가 계획·구현·리뷰·배포를 하면 아무도 책임지지 않는다.

### 2. Persona를 권한으로 착각한다

“read-only reviewer”라고 적어도 실제 shell·credential 권한이 그대로면 read-only가 아니다.

### 3. 화면 캡처를 Trace로 착각한다

TUI에는 상태바와 토큰 정보가 섞인다. 구조화된 결과 파일과 명령 출력을 우선한다.

### 4. 완료 메시지를 성공으로 착각한다

실제 커밋 SHA·PR·CI·URL이 없으면 완료가 아니다.

### 5. 대량 병렬화를 품질로 착각한다

Agent 수와 PR 수가 늘어도 중복·되돌림·보안 결함이 함께 늘 수 있다.

## 운영 템플릿

하나의 Agent 작업은 다음 계약으로 시작하는 것이 좋다.

```yaml
agent: bot3
role: builder
task_id: settlement-reconciliation-042
objective: Watermark 대사 실패 원인 재현 테스트 추가
repo: /srv/repos/settlement
worktree: /srv/worktrees/settlement-reconciliation-042
branch: agent/settlement-reconciliation-042
allowed_tools:
  - read_file
  - git_diff
  - run_tests
forbidden:
  - production_db_write
  - secret_read
  - deploy
  - push_without_approval
success_evidence:
  - test_output
  - diff_stat
  - commit_sha
stop_conditions:
  - unrelated_file_change
  - missing_fixture
  - production_access_required
```

## 결론

Claude·Codex Agent 운영에서 Persona는 장식적인 말투 설정이 아니다. 역할·근거·도구·금지행동·완료조건을 정리하는 **작업 계약의 일부**다.

```text
Persona = 관점
Policy = 권한
Harness = 실행 절차
MCP = 도구 경계
Worktree = 코드 격리
Reviewer = 품질 게이트
Trace = 진실
```

우리 환경에서 권장하는 형태는 다음과 같다.

```text
Hermes
  → 작업 큐·상태·근거 관리

Claude 봇1~4
  → 역할이 고정된 상시 워커

Codex
  → 필요할 때 생성하는 임시 논객·대안 구현자

Ouroboros/LION
  → 리뷰·종합·검증

GitHub
  → 승인된 commit·PR만 전달
```

결국 좋은 Agent 군단은 가장 많은 Agent를 켜는 시스템이 아니다. **각 Agent가 자신의 역할을 넘지 않고, 다음 Agent가 검증할 수 있는 증거를 남기며, 사람이 승인할 지점에서 멈추는 시스템**이다.

## 참고 자료

- [Model Context Protocol Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [MCP Official Servers](https://github.com/modelcontextprotocol/servers)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [OpenAI Codex](https://github.com/openai/codex)
- [Ouroboros](https://github.com/Q00/ouroboros)
- [cmux](https://github.com/manaflow-ai/cmux)
- [tmux](https://github.com/tmux/tmux)
- [기존 블로그: Linux에서 오픈소스 MCP를 쓰는 법](/2026/08/09/linux-open-source-mcp-analysis-guide/)

> 이 글은 우리 Hermes·Claude 봇·Codex·MCP·tmux 운영 경험을 일반화한 설계 고찰이다. 특정 Agent의 상용 기능·내부 구현·공식 지원 여부는 각 제품의 최신 문서를 다시 확인해야 한다.
