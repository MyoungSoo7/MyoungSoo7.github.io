---
layout: post
title: "코딩 에이전트 하네스 비교: Claude Code·Codex와 Superpowers·gstack·oh-my-codex·Ouroboros"
date: 2026-09-17 21:36:57 +0900
categories: [AI, Software Engineering, Agent]
tags: [Claude Code, Codex, Harness, Superpowers, gstack, oh-my-codex, Ouroboros, Coding Agent]
---

# 코딩 에이전트 하네스 비교

AI 코딩에서 모델만 비교하면 실제 개발 생산성과 안정성을 설명하기 어렵다. 같은 모델이라도 어떤 도구를 호출할 수 있는지, 변경을 어떻게 승인하는지, 테스트와 리뷰를 어떻게 강제하는지, 실패 후 어떻게 복구하는지에 따라 결과가 크게 달라진다.

이 글에서 말하는 하네스는 단순한 프롬프트 모음이 아니다.

```text
모델
  + 도구 실행
  + 권한·샌드박스
  + 저장소 규칙
  + skills / plugins
  + hooks / policy
  + 테스트·리뷰·관측
  + 반복·복구 루프
= 코딩 에이전트 하네스
```

비교 대상은 두 계층으로 나눈다.

- **상용·주도형 코딩 에이전트**: Claude Code, OpenAI Codex
- **오픈소스 하네스·워크플로 계층**: Superpowers, gstack, oh-my-codex, Ouroboros

여기서 “상용”은 모델 또는 제품 생태계를 제공하는 주도형 도구라는 의미이고, Codex CLI처럼 코드가 공개된 구성요소도 있다. 반대로 오픈소스 하네스는 대개 모델 자체가 아니라 기존 코딩 에이전트 위에 workflow, skill, policy, memory, orchestration을 추가한다.

## 1. 먼저 구분해야 할 것: Agent와 Harness

### 코딩 에이전트

에이전트는 모델이 저장소를 읽고 다음 작업을 수행하는 실행 주체다.

- 파일 탐색
- 코드 수정
- 테스트 실행
- shell 명령 실행
- git diff 확인
- 오류 로그 분석
- commit·PR 보조

OpenAI는 Codex CLI를 로컬 컴퓨터 터미널에서 동작하는 coding agent로 소개한다.[3] Claude Code도 hooks, MCP, permissions, plugins를 확장 지점으로 제공한다.[1][2]

### 하네스

하네스는 에이전트가 **어떤 순서와 제약으로 일하는지**를 결정한다.

```text
요구사항
  ↓
탐색·질문
  ↓
계획
  ↓
구현
  ↓
테스트
  ↓
리뷰
  ↓
검증
  ↓
커밋·PR
```

좋은 하네스는 “더 많이 작성하라”고 독촉하는 것이 아니라, 다음을 시스템으로 만든다.

- 시작 전에 저장소 규칙 읽기
- 변경 범위 제한
- 위험한 명령 승인
- 테스트 실패 시 중단
- 결과물과 로그 보존
- 다음 반복에 필요한 상태 저장
- 성공 조건을 코드와 CI로 검증

OpenAI의 harness engineering 사례도 사람이 직접 코드를 쓰는 비중보다 저장소의 legibility, feedback loop, 도구와 환경을 설계하는 일이 중요해졌다고 설명한다.[4]

## 2. Claude Code

Claude Code는 터미널 중심의 코딩 에이전트이며, 하네스 확장 표면이 풍부한 것이 특징이다.

### 핵심 구조

```text
Claude Code
  ├─ repository instructions
  ├─ tools
  ├─ MCP
  ├─ skills / plugins
  ├─ permissions
  └─ hooks
```

Claude Code의 hooks는 lifecycle의 특정 시점에 shell command, HTTP endpoint, MCP tool call, prompt 또는 agent를 실행할 수 있다.[1] Agent SDK도 hooks, MCP, permissions, plugins를 공식 capability로 제시한다.[2]

### 강점

- 도구·MCP·plugin·skill 확장성이 좋다.
- `PreToolUse` 같은 hook으로 위험한 도구 호출을 검사할 수 있다.[1]
- 저장소별 `CLAUDE.md`와 프로젝트 규칙을 결합하기 쉽다.
- 대화형 탐색과 장시간 작업에 적합하다.
- 외부 서비스와 브라우저·관측 도구를 연결하기 쉽다.

### 약점

- 확장 기능이 많을수록 어떤 hook·MCP·skill이 실제로 동작하는지 추적하기 어려워진다.
- 권한 설정이 느슨하면 에이전트의 접근 범위가 커진다.
- 모델의 자연어 판단을 hook만으로 완전히 대체할 수 없다.
- 팀마다 `CLAUDE.md`와 로컬 plugin이 달라지면 재현성이 떨어질 수 있다.
- 외부 MCP를 추가할수록 credential·네트워크·prompt injection 위험이 늘어난다.

### 적합한 사용사례

- 복잡한 레거시 저장소 탐색
- 브라우저·Kubernetes·GitHub·문서 시스템을 함께 다루는 작업
- 사용자가 대화로 방향을 조정하는 장기 작업
- hooks와 MCP를 이용한 조직 정책 enforcement

## 3. OpenAI Codex

Codex CLI는 터미널에서 실행되는 coding agent이며 오픈소스 저장소로 공개되어 있다.[3] Codex 생태계는 저장소 규칙, `AGENTS.md`, permissions, sandbox, review와 결합해 사용한다.

### 핵심 구조

```text
Codex CLI
  ├─ AGENTS.md
  ├─ local repository context
  ├─ sandbox / approval policy
  ├─ shell·file tools
  └─ review·test loop
```

### 강점

- 터미널과 Git workflow에 자연스럽게 연결된다.
- 저장소의 `AGENTS.md`로 작업 지침을 공유하기 쉽다.
- sandbox와 approval policy를 통해 실행 범위를 조절할 수 있다.
- 코드 수정·테스트·review를 하나의 작업 루프로 묶기 좋다.
- OpenAI가 공개한 harness engineering 사례처럼 repository를 system of record로 삼는 운영과 잘 맞는다.[4]

### 약점

- 좋은 결과를 내려면 저장소 문서와 검증 명령이 충분히 정리되어 있어야 한다.
- 긴 작업의 상태 관리·다중 에이전트 orchestration은 별도 하네스가 필요할 수 있다.
- approval과 sandbox 정책을 잘못 설정하면 속도와 안전성 사이의 균형이 무너진다.
- 에이전트가 테스트를 실행했다는 사실과 실제 업무 성공은 다르다.

### 적합한 사용사례

- 명확한 acceptance criteria가 있는 기능 작업
- 반복 가능한 test·lint·build pipeline
- Git worktree·PR 단위의 병렬 작업
- 저장소 규칙과 CI가 잘 정리된 팀

## 4. Superpowers

Superpowers는 특정 모델보다 software development methodology와 composable skills에 초점을 둔 오픈소스 framework다. 저장소는 이를 코딩 에이전트 위에서 사용하는 완성형 개발 방법론으로 설명하고, Claude Code·Codex 등 여러 host용 plugin 디렉터리를 제공한다.[5]

### 핵심 workflow

```text
brainstorming
  ↓
writing-plans
  ↓
executing-plans
  ↓
test-driven-development
  ↓
review
  ↓
verification
```

### 강점

- 구현 전에 요구사항과 계획을 구조화한다.
- TDD, debugging, review 같은 방법론을 재사용 가능한 skill로 만든다.
- 특정 모델보다 workflow discipline을 강화한다.
- 여러 coding agent에 이식할 수 있는 plugin 구조를 지향한다.[5]
- “먼저 구현하고 나중에 검증”하는 습관을 줄이는 데 효과적이다.

### 약점

- 절차가 많아 단순한 한 줄 수정에는 무겁다.
- skill 간 순서와 적용 범위를 팀이 이해해야 한다.
- 모델이 skill을 읽었다고 해서 실제로 모든 검증을 수행한 것은 아니다.
- 동일한 repository에 다른 skill pack을 여러 개 얹으면 충돌과 중복이 생길 수 있다.

### 적합한 사용사례

- 중대형 기능 개발
- 요구사항 누락이 잦은 팀
- TDD·review·plan을 표준화하려는 조직
- agent가 자의적으로 범위를 넓히는 문제가 있는 저장소

## 5. gstack

gstack은 하나의 에이전트를 CEO, designer, engineering manager, release manager, documentation engineer, QA 역할로 나누는 opinionated skill stack이다. 공식 저장소는 23개 도구와 slash-command 기반 역할 구성을 설명한다.[6]

### 핵심 workflow

```text
/plan-ceo-review
      ↓
/plan-eng-review
      ↓
/design-review
      ↓
/qa
      ↓
/ship
      ↓
/retro
```

### 강점

- 제품·설계·구현·QA·출시를 역할별로 분리한다.
- 코드만이 아니라 제품 요구사항과 UX까지 검토 범위에 넣는다.
- slash command로 진입점이 명확하다.
- ship, QA, browser, review 같은 실무 workflow가 구체적이다.
- 팀에 “누가 어떤 관점에서 검토했는가”를 남기기 좋다.

### 약점

- 제품 역할이 필요 없는 라이브러리·단순 backend 작업에는 과하다.
- opinionated workflow를 그대로 적용하면 팀의 기존 프로세스와 충돌할 수 있다.
- 설치와 업데이트가 사용자 skill을 덮어쓰지 않도록 관리되어야 한다.[6]
- 역할 수가 많아지면 실제 책임자와 모델 역할을 혼동할 수 있다.

### 적합한 사용사례

- 제품 기능 개발
- UI·UX와 backend를 함께 검토하는 서비스
- 출시 전 QA와 release checklist가 중요한 팀
- 한 에이전트를 가상 engineering team처럼 운용하려는 경우

## 6. oh-my-codex

oh-my-codex는 Codex를 혼자 두지 않고 hooks, agent teams, HUD, workflow 기능을 추가하는 Codex 중심 오픈소스 하네스다.[7]

### 강점

- Codex의 CLI 경험을 확장하는 데 초점을 둔다.
- hook·team·HUD를 통해 실행 상태를 보이게 한다.
- Codex 사용자에게 별도의 Claude Code 중심 workflow를 강제하지 않는다.
- 반복 작업과 병렬 agent 운영의 진입점을 제공한다.

### 약점

- Codex의 버전·plugin API 변화에 영향을 받는다.
- hook과 team이 많아질수록 실행 주체와 권한을 추적해야 한다.
- HUD는 관측을 돕지만 검증 자체를 대신하지 않는다.
- 오픈소스 프로젝트의 release 안정성·호환성은 직접 확인해야 한다.

### 적합한 사용사례

- Codex CLI를 주력으로 사용하는 개인·팀
- 병렬 agent와 상태 HUD가 필요한 작업
- Codex 기본 workflow에 organization-specific guard를 추가하는 경우

## 7. Ouroboros

이 글에서 Ouroboros는 `Q00/ouroboros` Agent OS를 의미한다. 동명이인 프로젝트가 있으므로 repository identity를 먼저 확인해야 한다. Q00 프로젝트는 local-first runtime, Seed·Ledger·MCP·Runtime으로 구성된 specification-first Agent OS를 지향한다고 설명한다.[8]

### 핵심 구조

```text
Seed
  ↓
Plan / Stage / Step
  ↓
Runtime + MCP
  ↓
Ledger / EventStore
  ↓
Evaluation / Evolution
```

### 강점

- 단일 coding session보다 장기 실행과 durable history를 강조한다.
- 요구사항을 Seed나 specification으로 고정하려는 방향이 강하다.
- MCP와 runtime을 중심으로 여러 agent를 orchestration할 수 있다.
- 실행 이벤트·평가·진화 루프를 별도 객체로 다루기 좋다.
- coding agent를 조직 운영 시스템의 worker로 배치할 수 있다.

### 약점

- Claude Code나 Codex보다 도입할 개념과 운영 컴포넌트가 많다.
- EventStore·runtime·MCP·plugin health를 별도로 운영해야 한다.
- 단순 기능 하나를 빨리 수정하는 데는 과한 구조다.
- 장기 실행의 state가 정확히 저장되고 재생되는지 검증해야 한다.
- 하네스가 복잡해질수록 장애 원인과 책임 경계도 복잡해진다.

### 적합한 사용사례

- 장기 프로젝트와 반복 가능한 agent execution
- 여러 worker를 지휘하는 중앙 orchestrator
- 실행 기록·평가·진화가 중요한 연구·운영 시스템
- 단순 prompt가 아니라 durable workflow를 구축하려는 조직

## 8. 다각도 비교

| 관점 | Claude Code | Codex | Superpowers | gstack | oh-my-codex | Ouroboros |
|---|---|---|---|---|---|---|
| 분류 | coding agent·platform | coding agent·CLI | methodology·skills | role-based skills | Codex extension harness | Agent OS·orchestrator |
| 중심 가치 | 확장성·도구 연결 | repo 실행·검증 | 계획·TDD·규율 | 역할별 review·ship | Codex team·HUD·hooks | durable execution·ledger |
| 주 입력 | prompt·repo·MCP | prompt·repo·AGENTS | task·plan·skills | slash commands | Codex task·hooks | Seed·spec·events |
| 가장 강한 영역 | 복잡한 탐색·통합 | 명확한 coding task | 구현 품질 절차 | 제품·QA·출시 | Codex 병렬 workflow | 장기 orchestration |
| 도입 난도 | 중 | 중 | 중 | 중~상 | 중~상 | 상 |
| 정책·권한 | permissions·hooks | sandbox·approval | host에 의존 | host와 skill에 의존 | host·hook에 의존 | runtime·MCP·policy 필요 |
| 주요 리스크 | MCP·권한 복잡성 | 검증 부족 | 절차 과잉 | 역할 과잉 | plugin 호환성 | 운영 복잡성 |
| 추천 단위 | session·repo | task·PR | feature·plan | product change | Codex workspace | program·long-running run |

이 표는 각 프로젝트의 공식 문서가 설명하는 기능과 workflow를 기준으로 한 구조적 비교이며, 처리량·품질·비용의 독립적인 head-to-head 벤치마크 결과는 아니다.

## 9. 가장 중요한 비교축: 통제력

### 9.1 결정론적 통제

다음은 모델의 기억에 맡기지 말고 코드로 강제해야 한다.

- 금지된 경로 수정 차단
- production 명령 차단
- secret 출력 차단
- 테스트 실패 시 merge 차단
- diff scope 제한
- dependency·image 보안 검사
- commit 전 lint·build·test

Claude Code에서는 hooks와 permissions가 이 계층을 구성한다.[1][2] Codex에서는 sandbox·approval과 repository instructions를 조합한다.[3] 오픈소스 하네스는 결국 host가 제공하는 이 enforcement surface를 얼마나 안전하게 활용하는지가 핵심이다.

### 9.2 절차적 통제

Superpowers와 gstack은 “무엇을 어떤 순서로 검토할지”를 구조화한다. 이 계층은 모델의 reasoning 품질과 누락을 줄이는 데 유용하지만, 절차 문서 자체가 실행됐다는 증거는 아니다.

```text
skill을 읽음
≠
명령 실행
≠
테스트 성공
≠
운영 반영
```

### 9.3 감사·복구 통제

Ouroboros 같은 Agent OS는 실행을 event·ledger·evaluation 관점에서 다루려 한다. 장기 실행에서는 이 계층이 중요하지만, EventStore에 기록됐다는 사실도 artifact와 실제 시스템 상태를 대신하지 않는다.

## 10. 어떤 조합이 좋은가

### 개인 개발자

```text
Codex 또는 Claude Code
+ 최소한의 repository instructions
+ test·lint·build hook
```

먼저 기본 agent를 안정화하고, 필요한 workflow만 추가하는 편이 좋다.

### 품질 중심 팀

```text
Claude Code 또는 Codex
+ Superpowers
+ CI security/test gate
```

계획·TDD·review를 표준화하고, 성공 조건은 CI가 판정하게 한다.

### 제품 출시 중심 팀

```text
Claude Code
+ gstack
+ browser/QA trace
+ release checklist
```

제품 요구사항·UX·QA·출시 검토가 중요한 경우에 적합하다.

### Codex 중심 병렬 실행 팀

```text
Codex
+ oh-my-codex
+ worktree·CI·review gate
```

다만 병렬 작업 수보다 branch isolation, merge 검증과 context 보존이 먼저다.

### 중앙 오케스트레이션 조직

```text
Claude Code·Codex worker
+ Ouroboros
+ EventStore·MCP·evaluation
```

여러 worker의 실행 상태와 결과를 중앙에서 관리해야 할 때 검토할 수 있다. 단순 기능 개발에는 도입 비용이 과하다.

## 11. 흔한 실패 패턴

### 하네스 여러 개를 동시에 무작정 설치

Superpowers, gstack, oh-my-codex를 모두 활성화하면 command·skill·hook 이름이 충돌할 수 있다. 한 프로젝트에서 workflow owner를 하나 정하고 나머지는 필요한 기능만 선별하는 편이 안전하다.

### 별 개수로 품질을 단정

GitHub stars는 관심도와 확산의 신호이지 production correctness, security, 유지보수 품질의 증거가 아니다. 이 글의 비교도 기능과 구조 비교이지 품질 순위가 아니다.

### 모델 변경으로 모든 문제를 해결하려 함

테스트가 없고 실행 환경이 불명확하면 더 강한 모델도 성공을 보장하지 않는다. 먼저 repository map, fixtures, test command, observability, CI gate를 만든다.

### “완료”를 agent의 문장으로만 판단

다음 증거가 필요하다.

```text
변경 diff
+ 실행한 명령
+ 실제 exit code
+ 테스트 결과
+ build artifact
+ 배포·외부 상태 read-back
```

### production 권한을 처음부터 부여

agent에게 broad shell·cluster·cloud 권한을 주면 편해 보이지만, 실패 반경과 credential 노출 반경이 커진다. read-only → test environment → canary → 승인된 production 순서가 안전하다.

## 12. 평가 프레임워크

하네스를 도입할 때 stars나 데모 대신 다음을 측정한다.

### 작업 품질

- acceptance criteria 충족률
- defect escape rate
- 회귀 테스트 통과율
- mutation 또는 negative test coverage
- review에서 발견된 결함 수

### 실행 효율

- 첫 성공까지의 시간
- human intervention 횟수
- context reset 횟수
- failed tool call 비율
- token·API 비용
- 병렬 작업의 실제 merge 성공률

### 안전성

- unauthorized command 차단률
- secret exposure zero 여부
- production 접근 실패가 fail-closed인지
- sandbox escape·unexpected network access 여부
- dependency·image security gate 통과율

### 유지보수성

- skill·plugin 충돌 수
- version upgrade rollback 가능 여부
- 실행 trace 재현성
- 새로운 개발자의 onboarding 시간
- repository 규칙과 실제 runtime enforcement의 일치도

## 결론

Claude Code와 Codex는 작업을 실행하는 **주도형 coding agent**이고, Superpowers·gstack·oh-my-codex·Ouroboros는 그 agent를 더 규율 있고 반복 가능하게 만드는 **workflow·skill·orchestration 계층**이다.

```text
Claude Code:
  확장 가능한 도구·MCP·hook 플랫폼

Codex:
  터미널·저장소·sandbox·검증 중심 coding agent

Superpowers:
  계획·TDD·debugging·review 방법론

gstack:
  제품·설계·QA·출시 역할 분해

oh-my-codex:
  Codex 중심 hooks·team·HUD 확장

Ouroboros:
  Seed·Ledger·MCP·Runtime 기반 장기 Agent OS
```

가장 좋은 하네스는 기능이 가장 많은 하네스가 아니다. 프로젝트의 위험도와 팀의 검증 능력에 맞게 다음을 명확히 하는 하네스다.

```text
누가 계획하는가
누가 실행하는가
무엇을 자동 승인하는가
어디서 중단하는가
무엇으로 성공을 증명하는가
실패 후 어떻게 복구하는가
```

실무 추천은 다음과 같다.

1. Claude Code 또는 Codex 하나를 주 agent로 정한다.
2. 저장소 규칙을 `CLAUDE.md` 또는 `AGENTS.md`로 명시한다.
3. Superpowers 또는 gstack 중 하나만 workflow owner로 선택한다.
4. Codex 중심이면 oh-my-codex를 별도 검토한다.
5. 여러 worker와 durable execution이 필요할 때만 Ouroboros를 추가한다.
6. 모든 write·deploy 결과는 agent의 말이 아니라 실제 trace와 read-back으로 검증한다.

하네스 engineering의 본질은 AI에게 코드를 더 많이 쓰게 하는 것이 아니다. **의도를 명확하게 만들고, 실행 범위를 제한하고, 실패를 빨리 드러내고, 결과를 재현 가능하게 증명하는 시스템을 만드는 것**이다.

## 참고 자료

[1] Claude Code Hooks — lifecycle hook과 tool 호출 제어  
[2] Claude Agent SDK — hooks, MCP, permissions, plugins  
[3] OpenAI Codex — 터미널에서 실행되는 open-source coding agent  
[4] OpenAI Harness Engineering — repository legibility, feedback loop, agent-first 개발 운영  
[5] Superpowers — composable skills와 software development methodology  
[6] gstack — 역할 기반 slash-command와 QA·ship workflow  
[7] oh-my-codex — Codex hooks, agent teams, HUD 확장  
[8] Ouroboros — Seed·Ledger·MCP·Runtime 기반 Agent OS

## 출처

- Claude Code Hooks: https://code.claude.com/docs/en/hooks
- Claude Agent SDK: https://code.claude.com/docs/en/agent-sdk/overview
- OpenAI Codex: https://github.com/openai/codex
- OpenAI Harness Engineering: https://openai.com/index/harness-engineering/
- Superpowers: https://github.com/obra/superpowers
- gstack: https://github.com/garrytan/gstack
- oh-my-codex: https://github.com/Yeachan-Heo/oh-my-codex
- Ouroboros: https://github.com/Q00/ouroboros

## Sources

[1] https://code.claude.com/docs/en/hooks — Claude Code Hooks
[2] https://code.claude.com/docs/en/agent-sdk/overview — Claude Agent SDK
[3] https://github.com/openai/codex — OpenAI Codex CLI
[4] https://openai.com/index/harness-engineering — OpenAI Harness Engineering
[5] https://github.com/obra/superpowers — Superpowers
[6] https://github.com/garrytan/gstack — gstack
[7] https://github.com/Yeachan-Heo/oh-my-codex — oh-my-codex
[8] https://github.com/Q00/ouroboros — Ouroboros Agent OS
