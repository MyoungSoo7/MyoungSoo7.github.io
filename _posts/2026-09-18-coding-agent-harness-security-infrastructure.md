---
layout: post
title: "코딩 에이전트 하네스의 보안과 인프라: Claude Code·Codex·오픈소스 하네스 운영 기준"
date: 2026-09-18 18:49:14 +0900
categories: [AI, Security, Infrastructure]
tags: [Coding Agent, Harness, Claude Code, Codex, MCP, Sandbox, Zero Trust, DevSecOps]
---

# 코딩 에이전트 하네스의 보안과 인프라

코딩 에이전트 하네스를 도입할 때 가장 먼저 물어야 할 질문은 “어떤 모델이 더 똑똑한가?”가 아니다.

```text
어떤 파일을 읽을 수 있는가
어떤 명령을 실행할 수 있는가
어떤 네트워크에 접근할 수 있는가
어떤 credential을 볼 수 있는가
누가 승인하는가
무엇을 증명해야 완료인가
```

Claude Code, Codex, Superpowers, gstack, oh-my-codex, Ouroboros 같은 도구는 개발 생산성을 높이지만 동시에 **코드·shell·네트워크·MCP·memory·CI·배포 권한을 연결하는 실행 계층**이 된다.

따라서 하네스는 생산성 도구이면서 다음과 같은 보안 경계다.

```text
사용자 / 저장소 / 외부 문서
          ↓ untrusted input
모델
          ↓ tool decision
하네스 정책 계층
          ↓ allow / ask / deny
sandbox·network·credential boundary
          ↓
개발 인프라·CI·artifact·운영 시스템
```

이 글은 특정 하네스를 순위 매기지 않는다. 보안과 인프라 관점에서 무엇을 통제해야 하는지, 어떤 배포 모델이 안전한지, 오픈소스 하네스를 운영할 때 어디를 검증해야 하는지 정리한다.

## 1. 위협 모델부터 정의하기

코딩 에이전트는 일반적인 IDE보다 더 많은 일을 할 수 있다.

- 저장소 전체 읽기
- 임의 파일 수정
- shell 명령 실행
- package 설치
- 웹 요청
- GitHub·cloud·Kubernetes API 호출
- MCP 서버 호출
- 테스트와 build 실행
- commit·PR·release 보조

OWASP는 agentic AI의 주요 위험으로 prompt injection, tool abuse와 privilege escalation, data exfiltration, memory poisoning, goal hijacking, excessive autonomy, high-impact action abuse, cascading failure, supply-chain attack을 제시한다.[4][5]

### 보호해야 할 자산

```text
소스 코드
CI/CD credential
cloud·Kubernetes token
SSH key
.env·private key
고객 데이터·개인정보
package registry credential
production endpoint
agent memory·event ledger
build artifact·signing key
```

### 신뢰 경계

하네스 운영에서는 다음을 서로 다른 신뢰 영역으로 분리해야 한다.

1. 사용자 입력
2. 저장소의 코드와 문서
3. 웹·이슈·PR·문서에서 가져온 외부 데이터
4. 모델의 계획과 tool call
5. 하네스 정책과 승인 계층
6. sandbox 내부 실행 환경
7. CI·registry·cloud·production

특히 저장소의 `CLAUDE.md`, `AGENTS.md`, skill, plugin, `.mcp.json`도 실행 동작에 영향을 줄 수 있다. 신뢰하지 않는 저장소를 바로 읽기·쓰기 권한으로 실행하면 저장소 자체가 하네스의 행동을 바꾸는 입력이 될 수 있다.

## 2. Claude Code의 보안·인프라 관점

Claude Code는 permission-based architecture를 사용하며, Manual mode에서는 읽기 전용 작업과 변경·shell·네트워크 작업의 승인 범위를 구분한다.[1]

### 제공되는 핵심 경계

- 세밀한 tool permission
- working directory boundary
- sandboxed Bash의 filesystem·network isolation
- ask·allow·deny rule
- MCP permission
- hook을 통한 tool call 검사
- project·user·managed settings
- 사용량·감사 관측 연계

Claude Code 공식 문서는 permission rule이 모델의 지시문이 아니라 Claude Code 실행 계층에서 적용된다고 설명한다.[2] 즉 다음은 서로 다르다.

```text
CLAUDE.md에 “절대 kubectl delete 하지 마”라고 씀
  ≠ 실행 계층의 kubectl delete 차단
```

### 권장 운영 방식

```text
read-only 탐색
  ↓
계획·diff 생성
  ↓
단위 테스트·lint
  ↓
명시적 write 승인
  ↓
CI 검증
  ↓
canary·read-back
```

민감한 저장소에서는 project-specific permission, managed settings, dev container, sandbox를 함께 사용해야 한다. Claude Code도 사용자가 부여한 권한만 가진다는 점과 제안된 명령·변경을 검토해야 할 책임을 명시한다.[1]

### MCP의 위험

MCP는 외부 시스템을 도구로 연결하지만, 동시에 새로운 권한 경계다.

```text
MCP 서버
  ├─ 어떤 credential을 읽는가
  ├─ 어떤 API를 호출하는가
  ├─ read/write가 분리되어 있는가
  ├─ 입력을 검증하는가
  └─ 결과와 호출을 audit하는가
```

MCP를 “단순한 플러그인”으로 보면 안 된다. DB write, Kubernetes apply, GitHub merge, email send 같은 고위험 도구는 별도 승인·allowlist·감사 로그가 필요하다.

## 3. Codex의 보안·인프라 관점

OpenAI는 Codex를 안전하게 운영하기 위해 sandbox, approval, network policy, managed configuration, credential control과 agent-native telemetry를 함께 사용한다고 설명한다.[3]

### 핵심 경계

```text
sandbox
  → 파일시스템 write 범위
  → 네트워크 접근 범위
  → 보호 경로

approval policy
  → 언제 사용자·정책 승인 필요

network policy
  → 허용 domain·차단 domain·미등록 domain

telemetry
  → prompt·approval·tool result·MCP·network decision
```

OpenAI의 운영 사례는 Codex를 열린 outbound 네트워크에 두지 않고, 예상되는 destination을 allowlist하고 낯선 domain에는 승인을 요구하는 방향을 설명한다.[3]

### Codex 인프라에 필요한 것

- 저장소별 `AGENTS.md`와 정책 버전관리
- sandbox mode 고정
- writable root 최소화
- network proxy 또는 domain allowlist
- secret을 OS keyring·CI secret manager에 보관
- Kubernetes·cloud 명령은 read-only prefix와 write prefix 분리
- OpenTelemetry 또는 중앙 audit log
- task·approval·tool result correlation ID

Codex의 `AGENTS.md`는 작업 지침이지 filesystem·network 권한 자체가 아니다. 권한은 sandbox·approval·managed policy에서 별도로 enforce해야 한다.

## 4. 오픈소스 하네스의 추가 공급망 위험

Superpowers, gstack, oh-my-codex, Ouroboros 같은 오픈소스 하네스는 source를 볼 수 있고 수정할 수 있다는 장점이 있다. 하지만 “오픈소스이므로 안전하다”는 결론은 성립하지 않는다.

### 추가 공격면

```text
Git repository
  ├─ install script
  ├─ setup/update script
  ├─ skill markdown
  ├─ shell helper
  ├─ hook
  ├─ plugin manifest
  ├─ MCP server
  ├─ dependency
  └─ browser/runtime binary
```

점검해야 할 항목:

- 설치 script가 어떤 파일과 경로를 수정하는가
- update가 자동 실행되는가
- skill이 어떤 `allowed-tools`를 선언하는가
- hook이 어떤 shell을 실행하는가
- plugin이 어떤 MCP를 등록하는가
- 외부 binary와 npm·Python dependency가 고정돼 있는가
- 네트워크로 무엇을 전송하는가
- telemetry와 opt-out이 있는가
- 이전 설정과 skill을 덮어쓰는가
- uninstall·rollback이 가능한가

### 안전한 도입 순서

```text
소스·release·commit 고정
  ↓
isolated canary profile
  ↓
install/update script 정적 검토
  ↓
network·filesystem trace
  ↓
read-only smoke test
  ↓
비민감 test repository
  ↓
팀 배포
```

README의 설치 명령을 그대로 production workstation에서 실행하지 않는다. 특히 `curl | sh`, 자동 update, broad home-directory write, wildcard tool permission은 먼저 차단·검토해야 한다.

## 5. 하네스별 보안 책임의 차이

| 대상 | 기본 역할 | 보안 책임의 중심 | 인프라 위험 |
|---|---|---|---|
| Claude Code | 확장 가능한 coding agent | permission·sandbox·MCP·hooks | MCP와 project settings 확장 |
| Codex | sandbox·approval 기반 coding agent | sandbox·network·managed policy·telemetry | shell·CI·repo 권한 결합 |
| Superpowers | 계획·TDD·review skill | host permission에 의존 | 절차는 권한을 대체하지 않음 |
| gstack | role-based workflow | host + skill + browser 경계 | QA·browser·ship 자동화 범위 |
| oh-my-codex | Codex hooks·team·HUD | Codex policy와 plugin 검증 | hook·team·plugin 호환성 |
| Ouroboros | long-running Agent OS | runtime·MCP·ledger·event policy | durable state·worker cascade |

핵심은 오픈소스 workflow 계층이 자체적으로 OS sandbox를 제공하지 않을 수 있다는 점이다. Superpowers나 gstack을 설치했다고 shell·network·Kubernetes 권한이 안전해지는 것이 아니다. 실제 권한은 Claude Code·Codex·OS·container·cloud IAM에서 enforce해야 한다.

## 6. 인프라 배포 모델

### 6.1 로컬 workstation

```text
개발자 Mac/Linux
  └─ Claude Code 또는 Codex
      └─ local repository
      └─ local sandbox
      └─ limited MCP
```

장점:

- 빠른 interactive 개발
- local IDE·terminal·Docker 활용
- 사람이 즉시 승인 가능

위험:

- SSH key와 cloud credential이 같은 환경에 존재
- home directory 과도한 접근
- 개인별 설정 차이
- 로컬 agent가 production endpoint에 도달할 가능성

권장:

- 별도 OS user 또는 dev container
- project별 credential
- production credential 부재
- read-only cloud·Kubernetes context 기본값
- `~/.ssh`, `.env`, key 파일 deny
- write는 branch·worktree 내부로 제한

### 6.2 개발 container·VM

```text
Host
  └─ VM / dev container
      └─ agent
          └─ repository mount
          └─ test-only credential
          └─ restricted network
```

민감한 저장소나 untrusted contribution에는 local host보다 강한 경계를 제공한다. 다만 container 안에 Docker socket을 mount하면 사실상 host control 권한이 커질 수 있으므로 주의해야 한다.

```text
/var/run/docker.sock mount
  → container가 host Docker daemon을 제어할 가능성
```

### 6.3 CI runner

Self-hosted runner에서 agent를 실행할 때는 runner를 일반 build runner보다 높은 위험 등급으로 취급해야 한다.

- ephemeral runner
- job별 workspace 폐기
- secret 최소 주입
- fork PR과 production credential 분리
- outbound domain allowlist
- privileged Docker·hostPath 최소화
- artifact·log secret scanning
- runner group과 repository allowlist
- job timeout·cost limit

### 6.4 중앙 Agent OS·Orchestrator

Ouroboros처럼 중앙 runtime이 여러 worker를 지휘하면 다음이 중요하다.

```text
Conductor
  ├─ worker identity
  ├─ task scope
  ├─ credential scope
  ├─ event trace
  ├─ retry budget
  ├─ cancellation
  └─ result verification
```

여러 agent가 하나의 credential이나 broad MCP를 공유하면 한 worker의 prompt injection이 전체 worker로 전파될 수 있다. worker마다 identity·token·worktree·network·memory를 분리하고, inter-agent message도 검증해야 한다.

## 7. 보안 통제 7계층

### 1. Identity

- 사람·agent·worker·MCP server별 identity 분리
- short-lived token
- OS keyring·secret manager 사용
- static PAT·공용 SSH key 최소화
- service account를 개인 계정과 분리

### 2. Authorization

- read·write·delete·deploy 권한 분리
- repository·branch·namespace별 scope
- Kubernetes RBAC
- cloud IAM least privilege
- deny가 allow보다 우선하는 정책

### 3. Execution sandbox

- working directory 제한
- filesystem deny list
- network namespace·egress allowlist
- non-root
- privileged·hostPath·Docker socket 차단
- resource·time·process limit

### 4. Input·context security

- 외부 문서·Issue·PR·웹 페이지는 untrusted data로 취급
- instruction과 data delimiter 분리
- retrieved content에서 tool call 지시 제거
- memory 저장 전 sanitize·redact
- session·user·project memory 격리

OWASP도 외부 입력을 신뢰하지 말고, memory를 검증·격리하며, prompt injection 방어와 입력 경계를 적용하라고 권고한다.[4]

### 5. Human approval

다음은 기본적으로 승인 대상이어야 한다.

- production deploy
- DB write·migration
- Kubernetes apply/delete/scale
- cloud IAM 변경
- secret·credential 접근
- email·외부 게시
- merge·release·tag
- 대량 파일 삭제

승인 UI만으로 충분하지 않다. 승인 대상·요청 payload·승인자·시각·결과를 audit해야 한다.

### 6. Observability

최소한 다음 이벤트를 남긴다.

```text
session_id
agent_id / worker_id
user_id
repository·commit·worktree
prompt hash 또는 분류 정보
selected tool
sanitized arguments
approval decision
sandbox·network decision
exit code
artifact·test result
```

단, prompt·tool argument에 secret과 개인정보를 평문으로 남기지 않는다.

### 7. Recovery

- 작업 취소
- timeout
- retry budget
- circuit breaker
- worktree 폐기
- credential revoke
- token rotation
- artifact quarantine
- rollback commit/image
- memory·event correction

“에이전트가 알아서 고친다”는 recovery 전략이 아니다. 실패 상태를 사람이 재현할 수 있어야 한다.

## 8. DevSecOps 파이프라인에 하네스 연결

```text
Plan
  ↓
static policy check
  ↓
agent implementation
  ↓
unit/integration test
  ↓
SAST·dependency scan·secret scan
  ↓
container build·SBOM·image scan
  ↓
review / approval
  ↓
canary
  ↓
runtime smoke·read-back
  ↓
release
```

### 예시 정책

```text
개발 agent:
  repo read/write
  test container network
  no production credential

CI agent:
  ephemeral workspace
  artifact upload
  read-only issue/PR
  deploy only after approval

운영 agent:
  default read-only
  explicit command allowlist
  separate break-glass path
  every action audited
```

에이전트가 테스트를 통과했다는 것은 코드 검증의 한 단계일 뿐이다. 이미지 push, Git push, Kubernetes apply, 외부 URL 200은 각각 별도의 성공 조건과 read-back이 필요하다.

## 9. 실패 패턴

### “읽기 전용이라고 문서에 적었으니 안전하다”

문서의 의도는 실행 권한이 아니다. tool policy, OS sandbox, RBAC와 network policy가 실제로 막아야 한다.

### “MCP 서버는 데이터만 제공한다”

MCP tool이 write endpoint와 credential을 가지고 있다면 실제 외부 side effect를 만들 수 있다.

### “self-hosted runner에서만 실행하면 안전하다”

runner가 repository code와 secret을 함께 실행하면 공격면이 커진다. ephemeral·isolated runner와 secret scope가 필요하다.

### “자동 승인으로 생산성을 높인다”

자동 승인은 저위험 작업에만 적용해야 한다. 네트워크·삭제·deploy·credential 접근은 별도 승인 또는 deny가 필요하다.

### “오픈소스 skill은 markdown일 뿐이다”

skill이 shell, hook, MCP, plugin을 호출하거나 allowed tool을 선언하면 실행 정책의 일부다. commit 고정과 코드 review가 필요하다.

### “로그를 많이 남기면 감사 가능하다”

secret과 개인정보를 로그에 남기면 observability가 데이터 유출 경로가 된다. 구조화된 metadata와 redaction이 필요하다.

## 10. 도입 체크리스트

### 사전 조사

- [ ] agent·harness·model·MCP의 책임 경계 작성
- [ ] source repository와 license 확인
- [ ] release·commit·dependency lock
- [ ] 설치·update·uninstall script 검토
- [ ] telemetry·외부 network 확인
- [ ] prompt·memory·event 저장 위치 확인

### 권한

- [ ] repository·branch·worktree 범위
- [ ] read/write/delete 분리
- [ ] production credential 미주입
- [ ] Kubernetes RBAC와 cloud IAM 최소화
- [ ] MCP server allowlist
- [ ] shell command deny/ask/allow 정책

### 격리

- [ ] dev container 또는 VM
- [ ] non-root
- [ ] Docker socket·privileged 차단
- [ ] egress domain allowlist
- [ ] secret 파일 접근 차단
- [ ] resource·timeout·retry limit

### 검증

- [ ] prompt injection red-team
- [ ] tool abuse test
- [ ] secret exfiltration test
- [ ] unauthorized path write test
- [ ] production command denial test
- [ ] memory poisoning test
- [ ] multi-agent cascade test
- [ ] cost·loop·DoW limit test

OWASP는 production agent에 대해 agent version, model provider, tool policy, retrieval configuration, abuse case, approval·denial·timeout·circuit-breaker 결과와 잔여 위험을 보존하라고 권고한다.[4]

## 결론

코딩 에이전트 하네스의 보안은 모델 선택만으로 해결되지 않는다.

```text
안전한 하네스
=
최소 권한
+ 실행 sandbox
+ 제한된 네트워크
+ credential 분리
+ untrusted input 격리
+ 고위험 승인
+ 구조화된 telemetry
+ 검증 가능한 recovery
```

Claude Code는 permission, sandbox, working-directory boundary, MCP 통제와 hooks를 중심으로 운영할 수 있다.[1][2] Codex는 sandbox·approval·network policy·managed configuration·agent-native telemetry를 함께 구성하는 방향을 제시한다.[3] Superpowers와 gstack 같은 workflow 하네스는 계획·TDD·QA를 강화하지만, OS 권한이나 네트워크 경계를 자동으로 보장하지 않는다. Ouroboros 같은 Agent OS는 durable execution과 중앙 orchestration을 제공할 수 있지만, worker identity·event trace·memory·credential 격리가 필수다.

가장 현실적인 도입 순서는 다음과 같다.

```text
read-only 조사
  ↓
격리된 test repository
  ↓
승인된 개발 workspace
  ↓
CI ephemeral runner
  ↓
canary
  ↓
승인된 운영 경로
```

하네스의 완료 조건도 “코드를 작성했다”가 아니라 다음이어야 한다.

```text
변경 범위 확인
+ 테스트·빌드·보안 게이트 통과
+ artifact 검증
+ 배포 read-back
+ runtime smoke
+ audit trace
```

AI 코딩의 핵심 인프라는 더 강한 모델이 아니라 **행동 범위를 제한하면서도 필요한 피드백을 제공하는 실행 환경**이다. 보안과 인프라가 설계되지 않은 자율성은 생산성이 아니라 통제되지 않은 변경 속도에 불과하다.

## 참고 자료

[1] Claude Code Security — permission architecture, sandbox, prompt injection, MCP와 운영 보안  
[2] Claude Code Permissions — allow·ask·deny, project settings, tool permission enforcement  
[3] Running Codex safely at OpenAI — sandbox, approvals, network policy, credential과 telemetry  
[4] OWASP AI Agent Security Cheat Sheet — agent threat model, least privilege, memory·tool·input 보안  
[5] OWASP Top 10 for Agentic Applications 2026 — agentic AI 위험 프레임워크

## 출처

- Claude Code Security: https://code.claude.com/docs/en/security
- Claude Code Permissions: https://code.claude.com/docs/en/permissions
- Running Codex safely: https://openai.com/index/running-codex-safely/
- OWASP AI Agent Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html
- OWASP Top 10 for Agentic Applications 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

## Sources

[1] https://code.claude.com/docs/en/security — Claude Code Security
[2] https://code.claude.com/docs/en/permissions — Claude Code Permissions
[3] https://openai.com/index/running-codex-safely — Running Codex Safely
[4] https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html — OWASP AI Agent Security
[5] https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026 — OWASP Top 10 Agentic Applications
