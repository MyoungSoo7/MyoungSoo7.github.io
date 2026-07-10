---
layout: post
title: "Claude Code 플러그인 *Superpowers* 의 구조 — 규율 을 하네스 로 굳히다"
date: 2026-07-10 13:10:00 +0900
categories: [ai, engineering, agentic-coding]
tags: [superpowers, claude-code, plugin, skill, hook, subagent, harness-engineering, tdd]
---

![Superpowers 플러그인 구조 — Using Superpower·Iron Law·Red Flag·Planning·Verifying·hook·SubAgent](/assets/images/superpowers-plugin-structure.jpg)

앞 글 [하네스 엔지니어링 해부]({% post_url 2026-07-10-harness-engineering-anatomy-from-a-diagram %}) 에서 하네스 의 부품(Skill·Hook·Tool·SubAgent) 을 봤다. 이번 엔 그 부품 들 로 *실제 로 조립 된 하네스* 하나 — Claude Code 플러그인 **Superpowers** — 의 구조 를 그림 대로 뜯는다.

한 줄 로: **Superpowers 는 "시니어 엔지니어 의 규율" 을 스킬·훅·서브에이전트 로 굳혀서, 모델 이 *건너뛰고 싶어 하는 과정* 을 강제 하는 하네스** 다.

---

## 1. 왜 필요 한가 — 모델 은 과정 을 건너뛴다

LLM 은 똑똑 하지만 *성급* 하다. 계획 없이 코딩 하고, 테스트 없이 "됐다" 하고, 검증 없이 완료 를 선언 한다. 사람 주니어 와 똑같다. Superpowers 는 이 성급함 을 막는 **과정 강제 장치** 다 — 그림 의 부품 들 이 전부 "먼저 이걸 해라" 를 박아 넣는다.

---

## 2. Using Superpower — *진입 스킬* 과 두 개 의 못

그림 맨 위 노란 박스 `Using Superpower`. 이게 시작점 이다. 모든 대화 초입 에 *"스킬 을 어떻게 찾고 쓸지"* 를 세우는 메타 스킬. 그 안 에 두 개 의 못 이 박혀 있다:

- **Iron Law(철칙)** — *"스킬 이 적용 될 가능성 이 1% 라도 있으면, 반드시 그 스킬 을 불러라."* 선택 이 아니라 의무. 모델 이 "이 정도 는 그냥 하지" 하고 넘어가는 걸 막는 못.
- **Red Flag(적신호)** — 합리화 를 잡는 표. *"이건 그냥 간단한 질문 이야", "일단 이것 부터 하고", "코드 부터 빨리 보자"* — 이런 생각 이 들면 **멈추라** 는 신호. 스스로 를 속이는 순간 을 이름 붙여 차단.

이 둘 이 핵심 이다. **규율 은 착함 이 아니라 강제 다.** 지키고 싶을 때 지키는 건 규율 이 아니니까.

---

## 3. 왼쪽 열 = *과정* 스킬 들 (하나의 세션 안 에서)

`chat session` 안 에 순서 대로 박힌 과정:

- **Systematic Debugging** — 버그 를 만나면 *추측 으로 고치지 말고* 체계적 으로. 증상 → 재현 → 가설 → 검증 의 루프. ([에러 를 묻기 전]({% post_url 2026-07-07-before-asking-about-error-logs-10-checks %}) 의 그 태도 를 스킬 로)
- **Planning, Developing** — 코드 부터 치지 말고 *브레인스토밍 → 계획 → 구현*. 특히 TDD(테스트 를 먼저) 를 과정 으로 강제.
- **User Input → Result** — 사용자 입력 이 곧장 결과 로 가는 게 아니라, 위 아래 의 과정 을 *통과* 해서 나온다는 표시.
- **Verifying** — "됐다" 고 말하기 전 에 *실제 로 돌려보고 확인*. 검증 없는 완료 선언 을 금지. (내 가 [배포 후 외부 E2E]({% post_url 2026-07-05-backend-and-devops-in-ax-era %}) 를 중시 하는 것 과 같은 철학)

즉 왼쪽 열 은 **"성급 하게 건너뛰기 쉬운 단계 들" 을 명시적 스킬 로 세워 둔 것.**

---

## 4. hook — *결정론* 으로 과정 을 지킨다

오른쪽 위 `hook`. 앞 글 에서 말했듯 훅 은 *모델 의 판단 이 아니라 하네스 가 확정적 으로* 실행 한다. Superpowers 에서 훅 은 "대화 시작 시 using-superpowers 규칙 을 무조건 주입", "특정 시점 에 검증 요구" 처럼 **규율 이 잊히지 않게 못 박는** 자리 다. 모델 이 깜빡 해도 훅 은 안 깜빡 한다.

## 5. SubAgent × 2 — *분업 과 격리*

오른쪽 `SubAgent` 두 개. 큰 일 은 서브에이전트 에게 위임 한다 — 병렬 탐색, 또는 *구현 은 A 가 · 검증 은 B 가* 처럼 [maker/checker 분리]({% post_url 2026-07-09-what-is-multi-agent %}). 메인 세션 은 컨텍스트 를 깨끗 하게 유지 하고, 서브 는 자기 일 만 본다. Superpowers 의 "dispatching parallel agents", "subagent-driven development" 가 이 자리.

---

## 6. 전체 를 관통 하는 설계 철학

부품 을 다 모으면 하나 의 문장 이 된다:

> **Superpowers = (Iron Law 로 강제 된) 스킬 + (잊지 않게) 훅 + (분업 하는) 서브에이전트 로, *과정 을 건너뛸 수 없게* 만든 하네스.**

이건 새 능력 을 주는 게 아니다. 모델 은 이미 계획 도 · 테스트 도 · 검증 도 할 줄 안다. Superpowers 가 하는 일 은 **"할 줄 아는 걸 실제 로 하게" 만드는 것** — 규율 의 자동화. 시니어 가 주니어 에게 "계획 부터 세워", "테스트 먼저", "됐다고 하기 전에 돌려봐" 라고 잔소리 하던 걸, 하네스 에 박아 넣은 셈 이다.

---

## 마무리 — 능력 이 아니라 *규율* 을 엔지니어링 한다

[하네스 엔지니어링]({% post_url 2026-07-10-harness-engineering-anatomy-from-a-diagram %}) · [멀티 에이전트]({% post_url 2026-07-09-what-is-multi-agent %}) · [loop engineering]({% post_url 2026-07-09-loop-engineering-overview-july-2026 %}) 이 *구조·공간·시간* 의 설계 였다면, Superpowers 는 그 위 에 **규율(discipline)** 을 얹은 구체 사례 다.

> AX 시대 에 좋은 결과 를 내는 건 *더 똑똑한 모델* 이 아니라, **똑똑한 모델 이 성급 하지 않게 만드는 하네스** 다. Superpowers 는 그 하네스 를 "엔지니어링 규율" 이라는 이름 으로 패키징 한 것.

재미 있는 건 — 이 글 을 쓰는 지금 도 그 하네스 안 에서 돌고 있다는 것. 규율 을 스킬 로 굳히면, 잔소리 하는 시니어 가 항상 옆 에 앉아 있는 셈 이다.
