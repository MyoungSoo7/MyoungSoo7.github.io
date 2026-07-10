---
layout: post
title: "6 기둥 으로 다시 읽는 superpowers — *SKILL.md* 는 어떻게 규칙 을 강제 하는가"
date: 2026-07-10 12:20:00 +0900
categories: [ai, harness, skills]
tags: [superpowers, skill-md, ai-agent, harness-engineering, prompt-engineering, hooks, claude-code, obra]
---

Jesse Vincent 의 [obra/superpowers](https://github.com/obra/superpowers) 는 **문서형 하네스 를 실제 로 운영 중 인 보기 드문 오픈소스 사례** 다. 마크다운(`SKILL.md`) 로 에이전트 의 행동 규칙 을 정의 하고, 그걸 훅 으로 강제 한다. 이 글 은 그 SKILL.md 들 을 **6 기둥 — ROLE · GOAL · FORBID · OUTPUT · EXAMPLE · CHECK** 에 매핑 해 읽고, 마크다운 밖 의 `hooks/` 가 어떻게 한 겹 더 잠그는지 를 본다.

![6기둥으로 다시 읽는 superpowers — SKILL.md 를 ROLE·GOAL·FORBID·OUTPUT·EXAMPLE·CHECK 로](/assets/images/skills/superpowers-6-pillars.jpg)

> 참고: 이 글 은 그 스킬 시스템 을 *실제 로 돌려보며* 썼다. 아래 분석 은 문서 요약 이 아니라 *동작 관찰* 이다.

---

## 0. 왜 "6 기둥" 인가

좋은 프롬프트 = *역할·입력·제약·형식* 이라고 [전에]({% post_url 2026-07-02-ai-in-practice-8-self-assessment %}) 썼다. **SKILL.md 는 그 프롬프트 를 *재사용 가능한 규칙서* 로 굳힌 것** 이다. 그리고 잘 쓰인 스킬 을 뜯어보면 여섯 개 기둥 이 반복 된다:

| 기둥 | 질문 | 없으면 |
|---|---|---|
| **ROLE** | 이 스킬 은 *언제/누구* 를 위한 것인가 | 아무 때나 발동 or 영영 안 발동 |
| **GOAL** | *무엇 을 달성* 하나 | 방향 없이 표류 |
| **FORBID** | *하지 말아야 할 것* 은 | 그럴듯한 함정 에 빠짐 |
| **OUTPUT** | *결과 물 의 형태* 는 | 매번 다른 모양 |
| **EXAMPLE** | *구체 사례* 는 | 추상론 으로 오해 |
| **CHECK** | *어떻게 검증* 하나 | "됐다" 는 착각 |

이 여섯 칸 을 표 로 두면, **내 규칙서 를 짤 때 *어느 칸 을 비워두고 있는지* 가 한눈에** 보인다. superpowers 는 이 여섯 을 어떻게 채웠나.

---

## 1. FORBID 를 *일급 시민* 으로 — `using-superpowers`

가장 인상적 인 건 superpowers 가 **FORBID 를 표 로 못 박는다** 는 점이다. `using-superpowers` 스킬 에는 *"이 생각 이 들면 STOP — 당신 은 합리화 중"* 이라는 **레드 플래그 테이블** 이 있다:

- "이건 그냥 간단한 질문이야" → *질문 도 작업 이다. 스킬 을 확인 하라.*
- "먼저 코드 부터 둘러보자" → *스킬 이 어떻게 둘러볼지 를 알려준다. 먼저 확인.*
- "이 스킬 은 과하다" → *간단한 게 복잡 해진다. 써라.*

대부분 의 프롬프트 는 *하라(GOAL)* 만 쓰고 *하지 마라(FORBID)* 를 비워둔다. 그런데 AI 가 실수 하는 지점 은 대개 *그럴듯한 합리화* 다 — "이 정도 는 괜찮겠지". FORBID 를 *예상 되는 변명 과 함께* 명시 하면, 그 합리화 를 미리 차단 한다. **금지 를 구체적 으로 쓰는 게, 목표 를 쓰는 것 만큼 중요** 하다.

---

## 2. CHECK 를 *행동* 으로 — `verification-before-completion`

superpowers 의 또 다른 축 은 **CHECK 를 말 이 아니라 강제 절차 로** 만든 것이다:

- `using-superpowers`: 스킬 발동 시 *"Using [스킬] to [목적]"* 을 선언 하고, 체크리스트 항목 마다 *todo 를 하나씩* 만들라 — CHECK 를 *가시화*.
- `verification-before-completion`: *"됐다/고쳤다/통과 한다" 를 주장 하기 전 에 검증 명령 을 실제 로 돌리고 출력 을 확인 하라. 증거 가 주장 보다 먼저.*

이건 내가 [운영 회고]({% post_url 2026-07-09-a-day-of-k8s-java-ops-senior-retrospective %}) 에서 반복 한 원칙 과 똑같다 — *"됐어" 말고 "뭘 검증 안 했어?"*. 스킬 이 CHECK 기둥 을 *비워두면* AI 는 "아마 될 거예요" 를 남발 한다. superpowers 는 그걸 절차 로 막는다.

---

## 3. GOAL · ROLE · EXAMPLE — 나머지 세 기둥

- **ROLE(언제 발동)** — 각 스킬 의 frontmatter `description` 이 *트리거 조건* 이다. "X 를 할 때 사용" 형태 로, *언제 이 규칙 이 켜지는지* 를 못 박는다. `brainstorming` 은 "창의 작업 전 에", `systematic-debugging` 은 "버그·실패 를 만나면".
- **GOAL(무엇)** — `brainstorming` 은 *구현 전 에 의도·요구 를 탐색*, `test-driven-development` 는 *구현 전 에 테스트 부터*. 각 스킬 이 *한 문장 의 목표* 로 수렴 한다.
- **EXAMPLE** — 레드 플래그 표, 실패/성공 대비, 잘못된 예 vs 올바른 예. *추상 규칙 을 구체 로* 내려앉힌다.

여섯 기둥 이 다 채워진 스킬 은 *혼자 서도 작동* 한다 — 언제 켜지고(ROLE), 뭘 하고(GOAL), 뭘 피하고(FORBID), 어떤 형태 로 내놓고(OUTPUT), 어떻게 생겼고(EXAMPLE), 어떻게 확인 하는지(CHECK) 가 다 있으니.

---

## 4. 마크다운 밖 의 잠금 — `hooks/`

여기 가 superpowers 가 *영리한* 지점 이다. **SKILL.md 는 결국 "권고" 다.** AI 가 무시 할 수 있다. 그래서 이 레포 는 마크다운 밖 에 한 겹 을 더 둔다 — `hooks/`.

- 세션 시작 시 훅 이 `using-superpowers` 스킬 을 *컨텍스트 에 강제 주입* 한다. "스킬 을 쓰라" 는 규칙 이, 안 읽힐 수 없게 *시스템 레벨 에서* 들어온다.
- 즉 **문서 층(권고) + 시스템 층(강제)** 두 겹.

이 구조 가 낯익지 않은가. 내가 계속 말한 것 과 똑같다 — **"경계 는 문서 가 아니라 빌드 에서 강제 될 때 만 지켜진다."** ArchUnit 이 아키텍처 규칙 을 *테스트* 로, coordinator hook 이 세션 충돌 을 *훅* 으로 막듯이. superpowers 는 *스킬 규칙 을 훅* 으로 강제 한다.

> 소프트 게이트(마크다운) 는 방향 을 주고, 하드 게이트(훅) 는 이탈 을 막는다. 둘 다 있어야 규칙 이 *실제 로* 작동 한다.

---

## 5. 그래서 — 내 규칙서 를 어떻게 짜야 하나

superpowers 를 6 기둥 으로 읽고 나면, 내 스킬/프롬프트 를 점검 하는 체크리스트 가 생긴다:

1. **ROLE** — 이 규칙 이 *언제 켜지는지* 한 문장 으로 썼나? (안 쓰면 발동 자체 가 안 됨)
2. **GOAL** — 목표 가 *하나* 로 수렴 하나?
3. **FORBID** — *예상 되는 변명 과 함께* 금지 를 명시 했나? (가장 자주 비는 칸)
4. **OUTPUT** — 결과 형태 를 고정 했나?
5. **EXAMPLE** — 추상 을 구체 로 내렸나?
6. **CHECK** — 검증 을 *절차* 로 강제 했나? (두 번째 로 자주 비는 칸)
7. **(밖)** — 마크다운 이 무시 될 때 *하드 게이트(훅)* 가 있나?

경험상 사람들 이 가장 자주 비우는 건 **FORBID 와 CHECK** 다 — 하라 는 쓰는데, *하지 마라* 와 *확인 하라* 를 안 쓴다. superpowers 의 핵심 기여 는 그 두 칸 을 *일급 시민* 으로 끌어올린 것이다.

---

## 맺으며

`SKILL.md` 는 작아 보이는 마크다운 파일 이다. 하지만 잘 쓰인 스킬 은 **재사용 가능한 하네스 부품** 이다 — 여섯 기둥 이 채워지고, 훅 으로 잠기면, *한 번 잘 정의한 규칙 이 매번 자동 으로 작동* 한다. [하네스 엔지니어링]({% post_url 2026-07-10-harness-engineering-weekly-app-cycle %}) 의 "스킬" 이 바로 이거다.

superpowers 가 보여주는 건 결국 이 블로그 의 반복 주제 다 — **좋은 시스템 은 하라 만 이 아니라, 하지 마라·확인 하라 를 *구조 로 강제* 한다.** 문서 로 방향 을 주고, 훅 으로 이탈 을 막고. 백엔드 의 ArchUnit 이든 에이전트 의 SKILL.md 든, 신뢰 는 *강제 된 규칙* 에서 나온다.

*규칙 은 적는 것 이 아니라 강제 하는 것 이다 — 그리고 그 강제 를 어디에 두느냐 가 설계다.*
