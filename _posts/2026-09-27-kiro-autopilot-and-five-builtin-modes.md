---
layout: post
title: "Kiro 의 Autopilot 과 Built-in 5개 모드 — Default·Spec·Quick Spec·Bug Fix·Plan 을 언제 쓰나"
date: 2026-09-27 02:37:48 +0900
categories: [AI, Tools]
tags: [Kiro, AWS, AI에이전트, 스펙주도개발, EARS, Autopilot, 코딩에이전트]
---

![Kiro 채팅 입력창의 에이전트 선택 드롭다운. BUILT-IN: Default(General coding assistance), Spec(Structured feature development), Quick Spec(Fast spec workflow), Bug Fix(Structured bug-fix workflow), Plan(Plan-only mode). 아래에 "Default" 선택과 Autopilot 토글(켜짐)](/assets/images/kiro-builtin-modes-autopilot.jpg)

Kiro 채팅창 하단에는 작은 드롭다운과 토글이 하나씩 있다. 둘은 서로 다른 질문에 답한다.

- **드롭다운(모드 = 에이전트):** *무엇을, 어떤 절차로* 할 것인가
- **Autopilot 토글:** 하는 동안 *사람에게 묻고 할 것인가*

이 글은 [Kiro 공식 문서](https://kiro.dev/docs/ide/chat/)를 근거로 두 가지를 정리한다(2026-09-27 확인). Autopilot 을 포함한 Kiro 설정 화면 전체는 [먼저 올라간 글](/2026/09/27/kiro-settings-autonomy-ignore-portal/)에서 다뤘으니, 여기서는 **다섯 개 모드와 Autopilot 의 조합**에 집중한다.

## 1. 드롭다운의 정체 — "모드" 는 사실 에이전트다

드롭다운 제목이 **BUILT-IN** 인 데는 이유가 있다. [Chat 문서](https://kiro.dev/docs/ide/chat/)에 따르면 이 목록은 출처별로 묶인다.

| 그룹 | 위치 |
|---|---|
| **Built-in** | Default, Spec, Quick Spec, Bug Fix, Plan |
| User | `~/.kiro/agents/` |
| Workspace | `.kiro/agents/` |

즉 다섯 모드는 Kiro 가 기본으로 주는 **에이전트**이고, 직접 만든 [커스텀 에이전트](https://kiro.dev/docs/custom-agents/)(JSON 이나 Markdown 파일)도 같은 드롭다운에 나타난다. 이름이 겹치면 워크스페이스 쪽이 이긴다. 모드를 바꿔도 **대화 기록은 유지**되므로, 대화 도중에 모드를 전환해도 된다.

## 2. 다섯 개 모드

### ① Default — 대화형 코딩 (vibe)

드롭다운 설명은 "General coding assistance" 다. 문서는 이를 **vibe mode** 라고 부른다. 산출물 문서 없이 대화로 바로 코드를 다룬다. 워크플로를 따로 고르지 않으면 이 모드다.

**언제:** 작은 수정, 질문, 탐색, 한두 파일짜리 작업.

### ② Spec — 구조화된 기능 개발

Kiro 를 대표하는 모드다. [Specs 문서](https://kiro.dev/docs/specs/)에 따르면 `.kiro/specs/` 아래에 세 문서를 만든다.

| 파일 | 내용 |
|---|---|
| `requirements.md` | 요구사항. **EARS**(Easy Approach to Requirements Syntax) 형식: `WHEN [조건/이벤트] THE SYSTEM SHALL [기대 동작]` |
| `design.md` | 설계 |
| `tasks.md` | 구현 작업 목록 |

- 요구사항부터 시작할 수도 있고(Requirements-First), 설계부터 시작할 수도 있다(Design-First).
- 단계 사이에 **승인 관문**이 있다. 요구사항을 사람이 승인해야 설계로 넘어간다([Feature specs](https://kiro.dev/docs/specs/feature-specs/)).
- 작업은 의존 관계에 따라 병렬 "웨이브" 로 실행될 수 있다.

**언제:** 여러 파일에 걸친 새 기능, 팀과 공유해야 하는 기능. 스펙 파일이 곧 리뷰 대상이자 문서가 된다.

### ③ Quick Spec — 빠른 스펙

[Quick Spec 문서](https://kiro.dev/docs/specs/quick-spec/): *"auto-generates requirements, design, and tasks in a single pass."* 처음에 **명확화 질문에만** 답하면, 세 문서를 한 번에 만든다. 요구사항은 역시 EARS 형식이다. [Built-in agents 표](https://kiro.dev/docs/custom-agents/built-in/)는 차이를 한 줄로 적는다. *"auto-generates all phases without approval gates"*.

**Spec 과의 차이:** 산출물은 같고, **단계별 승인 관문이 없다.**

**언제:** 요구사항이 머릿속에 분명하고, 문서는 남기고 싶지만 단계마다 멈추기는 번거로울 때.

### ④ Bug Fix — 구조화된 버그 수정

[Bugfix specs 문서](https://kiro.dev/docs/specs/bugfix-specs/)에 따르면 `requirements.md` 대신 **`bugfix.md`** 를 만든다. 구성이 흥미롭다.

| 섹션 | 형식 |
|---|---|
| Current Behavior(현재 동작) | `WHEN [조건] THEN the system [잘못된 동작]` |
| Expected Behavior(기대 동작) | `WHEN [조건] THEN the system SHALL [올바른 동작]` |
| **Unchanged Behavior(바뀌면 안 되는 동작)** | `WHEN [조건] THEN the system SHALL CONTINUE TO [기존 동작]` |

이어서 `design.md` 에 **근본 원인 분석**을 쓰고, `tasks.md` 에는 **속성 기반 테스트(property-based tests)** 가 포함된다.

세 번째 섹션이 핵심이다. 버그 수정의 흔한 사고는 버그는 고쳤는데 **다른 것이 깨지는 것**이다. "바뀌면 안 되는 동작" 을 명시적으로 적게 하는 건 회귀를 요구사항 수준에서 막겠다는 설계다.

**언제:** 재현 조건이 있는 버그, 특히 고치다가 다른 곳을 깨뜨릴 위험이 큰 버그.

### ⑤ Plan — 계획만, 변경은 없음

[Plan 문서](https://kiro.dev/docs/specs/plan/): *"Plan mode intentionally cannot modify your project."*

- 파일 읽기, 검색, 웹 검색은 된다.
- **파일 쓰기, 명령 실행, MCP 도구는 안 된다.**
- 정식 requirements/design/tasks 문서를 만들지 않는다. 계획은 **대화 안에만** 있다.
- 계획을 승인하면 *"execution begins automatically"*, 즉 바로 실행 단계로 넘어간다.

**언제:** 아이디어를 쪼개 보고 싶을 때, 코드베이스를 처음 볼 때, 작업 범위를 가늠할 때. **읽기 전용이라 안전**하므로, 처음 보는 저장소에서 가장 먼저 쓰기 좋은 모드다.

### 한눈에

| 모드 | 파일 수정 | 산출 문서 | 승인 관문 | 한 줄 용도 |
|---|---|---|---|---|
| Default | ✅ | 없음 | — | 빠른 대화형 코딩 |
| Spec | ✅ | requirements·design·tasks | 단계마다 | 제대로 된 새 기능 |
| Quick Spec | ✅ | requirements·design·tasks | 없음(처음 질문만) | 빠르게 문서화된 기능 |
| Bug Fix | ✅ | bugfix·design·tasks | 스펙 흐름 | 회귀 없는 버그 수정 |
| Plan | ❌ | 없음(대화 안) | 계획 승인 후 실행 | 안전한 탐색·계획 |

## 3. Autopilot — 모드와 곱해지는 두 번째 축

화면 오른쪽 아래 토글이 **Autopilot** 이다. [Autopilot 문서](https://kiro.dev/docs/ide/chat/autopilot/)에 따르면 이게 **기본값**이다.

| | Autopilot (기본) | Supervised |
|---|---|---|
| 동작 | 단계마다 승인 없이 파일 생성·수정, 명령 실행, 구조적 결정 | 파일 수정이 있는 턴마다 멈추고 승인 대기 |
| 검토 방식 | 사후에 보고 되돌림 | hunk 단위 Accept / Reject, 또는 Accept All / Reject All |

Supervised 는 vibe 와 spec 세션 모두에 적용된다. 설정 키는 `kiroAgent.agentAutonomy` 다.

### 모드 × Autopilot 조합에서 알아둘 것

- **Plan 은 Autopilot 과 상관없이 안전하다.** 애초에 쓰기와 실행 도구가 없다. 다만 계획을 승인한 뒤 넘어가는 실행 단계는 Autopilot 설정의 영향을 받는다.
- **Spec 의 승인 관문과 Autopilot 은 다른 층이다.** Spec 은 *문서 단계*(요구사항 → 설계 → 작업)에서 멈춘다. Autopilot 은 *코드 변경*에서 멈출지를 정한다. 그래서 "Spec + Autopilot" 은 문서는 사람이 승인하고 구현은 알아서 하는 조합이다. 실무에서 가장 균형 잡힌 조합이다.
- **Quick Spec + Autopilot** 은 처음 질문에 답한 뒤로 사람이 멈춰 설 지점이 거의 없다. 가장 빠르지만 가장 덜 통제된다.
- **명령 실행은 모드와 별개다.** [보안 문서](https://kiro.dev/docs/privacy-and-security/)에 따르면 셸 명령은 *"a separate approval path"* 를 따른다. 신뢰 목록(Trusted Commands)에 없는 명령은 **두 모드 모두에서** 승인을 요구한다. 같은 문서는 이렇게도 경고한다. *"Supervised mode is a code review workflow, not a security control."*
- **되돌리기에는 한계가 있다.** 프롬프트마다 [체크포인트](https://kiro.dev/docs/checkpoints/)가 생겨 코드와 컨텍스트를 함께 되돌릴 수 있다. 하지만 *"does not track file changes made by MCP tools or bash commands"*, 즉 명령으로 바뀐 파일은 추적하지 않는다. Autopilot 에서 "나중에 되돌리면 되지" 가 항상 통하지는 않는다.

## 정리 — 추천 흐름

1. 처음 보는 저장소나 큰 아이디어 → **Plan** 으로 범위부터 본다(변경 없음).
2. 새 기능 → **Spec**(팀 공유·리뷰) 또는 **Quick Spec**(혼자, 빠르게).
3. 버그 → **Bug Fix**. "바뀌면 안 되는 동작" 칸을 꼭 채운다.
4. 자잘한 작업 → **Default**.
5. Autopilot 은 켜 두되, 위험한 명령은 신뢰 목록에 넣지 않는다. 모드가 **절차**를 정하고, 권한 규칙이 **안전**을 정한다.

## References

모두 2026-09-27 에 확인했다.

- Kiro Docs — [Chat (에이전트 선택)](https://kiro.dev/docs/ide/chat/) · [Built-in agents](https://kiro.dev/docs/custom-agents/built-in/) · [Custom agents](https://kiro.dev/docs/custom-agents/)
- Kiro Docs — [Specs](https://kiro.dev/docs/specs/) · [Feature specs](https://kiro.dev/docs/specs/feature-specs/) · [Quick Spec](https://kiro.dev/docs/specs/quick-spec/) · [Bugfix specs](https://kiro.dev/docs/specs/bugfix-specs/) · [Plan](https://kiro.dev/docs/specs/plan/)
- Kiro Docs — [Autopilot / Supervised](https://kiro.dev/docs/ide/chat/autopilot/) · [Privacy and security](https://kiro.dev/docs/privacy-and-security/) · [Checkpoints](https://kiro.dev/docs/checkpoints/)
