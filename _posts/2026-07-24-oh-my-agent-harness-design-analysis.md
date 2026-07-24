---
layout: post
title: "에이전트 하네스 설계 뜯어보기 — oh-my-agent의 로스터로 배우는 역할 분업"
date: 2026-07-24 11:20:00 +0900
categories: [AI, Architecture]
tags: [AgentHarness, oh-my-agent, Orchestrator, Subagent, SeparationOfConcerns, LeastPrivilege, ReviewGate, AgenticCoding]
---

# 잘 만든 하네스는 '에이전트 명단'에서 드러난다

에이전트 하네스가 잘 설계됐는지는, 그 하네스가 어떤 에이전트들을 *어떤 역할로* 두었는지를 보면 안다. 이 글은 **oh-my-agent(omo)** 의 에이전트 로스터를 *교육 목적*으로 뜯어본다 — 각 에이전트가 어떤 설계 원칙을 체화하고 있는지, 그리고 그게 일반적인 하네스 설계에 무엇을 가르치는지.

먼저 로스터 전체(두 장).

![oh-my-agent 에이전트 로스터 — Sisyphus/Prometheus/Oracle/Librarian/Atlas/Hephaestus/Explore/Metis/Momus/Multimodal-Looker 를 mode(primary/subagent)와 layer(실행/계획/워커) 2축으로 분류한 표](/assets/images/oh-my-agent-roster-main.jpg)

![oh-my-agent 로스터 추가 행 — Sisyphus-Junior, subagent/워커, category로 소환되는 실행 워커](/assets/images/oh-my-agent-roster-junior.png)

정리하면 이렇다(그림 기준):

| 에이전트 | mode | layer | 한 줄 역할 |
|---|---|---|---|
| **Sisyphus** | primary | 실행 | 기본 오케스트레이터 (계획·위임·검증·실행) |
| **Prometheus** | primary | 계획 | 인터뷰형 전략 기획자 — `.omo/*.md` **플랜만** 작성 |
| **Oracle** | subagent | 워커 | 읽기전용 고난도 추론 컨설턴트 |
| **Librarian** | subagent | 워커 | 외부 OSS·문서를 **GitHub permalink 근거로** 검색 |
| **Atlas** | primary | 실행 | 투두리스트 오케스트레이터(지휘자) |
| **Hephaestus** | primary | 실행 | 자율 심층 워커 |
| **Explore** | subagent | 워커 | 내부 코드베이스 contextual grep |
| **Metis** | subagent | 워커 | 계획 전 갭 분석 컨설턴트 |
| **Momus** | subagent | 워커 | 플랜 비평가 (리뷰 게이트) |
| **Multimodal-Looker** | subagent | 워커 | PDF/이미지 분석 |
| **Sisyphus-Junior** | subagent | 워커 | category로 소환되는 실행 워커 |

> 이 글의 분석은 위 로스터(사용자 제공 그림)에 나타난 구조를 근거로 한다. omo 내부 구현 세부는 그림에 없는 만큼 단정하지 않는다.

---

## 축이 두 개다 — mode × layer

먼저 눈에 띄는 건 에이전트를 **두 축**으로 분류했다는 점이다:

- **축 1 — mode**: `primary`(사용자와 직접 상호작용하며 세션을 주도) vs `subagent`(다른 에이전트가 도구처럼 소환)
- **축 2 — layer**: `실행` vs `계획` vs `워커`

이 2축 분류 자체가 설계다. mode는 [Anthropic의 orchestrator-worker](/2026/07/23/multi-agent-coordination-patterns/)와 정확히 대응하고 — primary=오케스트레이터, subagent=격리된 컨텍스트의 워커 — layer는 "무엇을 하는 층인가"(짜는가/시키는가/실행하는가)를 가른다. 에이전트를 **이름이 아니라 축으로** 관리하면, 새 에이전트를 추가할 때 "얘는 어느 칸인가"만 물으면 된다.

---

## 로스터가 가르치는 설계 원칙 7가지

이름은 신화에서 왔지만, 각 에이전트는 하나의 *원칙*을 구현한다.

### 1. 기획자는 짓지 않는다 — Prometheus (계획 전용)
Prometheus는 `.omo/*.md` **플랜만** 쓴다. 코드를 만들지 않는다. 이건 [SPEC/PLAN 분리](/2026/07/24/harness-spec-plan-done-criteria/)와 [Ouroboros의 Socratic Interviewer("절대 만들지 않는다")](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) 그대로다. *계획하는 주체와 실행하는 주체를 분리*하면, 계획이 구현 편의에 오염되지 않는다.

### 2. 지휘와 노동을 나눈다 — Sisyphus/Atlas(primary) vs 워커들
Sisyphus·Atlas는 계획·위임·검증을 하는 **오케스트레이터**고, 실제 노동은 subagent 워커가 한다. 오케스트레이터가 직접 다 하면 컨텍스트가 오염된다 — [탐색·구현을 메인 밖으로 빼는](/2026/07/23/agent-roles-explorer-implementer-verifier/) 이유다.

### 3. 읽기 전용 자문역 — Oracle, Metis (최소 권한)
Oracle(고난도 추론)과 Metis(계획 전 갭 분석)는 **읽기전용 컨설턴트**다. 판단을 돕지만 상태를 바꾸지 않는다. [최소 권한](/2026/07/23/agent-roles-explorer-implementer-verifier/) — 자문에 편집 권한을 줄 이유가 없다. 권한을 좁히면 사고 반경이 좁아진다.

### 4. 계획에 리뷰 게이트를 세운다 — Momus (플랜 비평가)
Momus는 **플랜을 비평하는 전용 에이전트**다. 즉 계획(Prometheus)과 비평(Momus)이 다른 주체다 — [작성자≠검증자](/2026/07/24/agentic-feedback-eval-pipeline/)의 계획 단계 버전. 자기 계획을 자기가 통과시키지 못하게, *계획에도 배심원 독립성*을 건다.

### 5. 검색엔 근거를 강제한다 — Librarian (permalink 그라운딩)
Librarian은 외부 OSS·문서를 찾되 **GitHub permalink를 근거로** 가져온다. 출처 없는 "카더라"를 차단하는 구조 — [권위 있는 출처를 요구하는 규율](/2026/07/24/eval-harness-grader-types/)이 검색 에이전트에 박혀 있다. 근거를 *에이전트 계약*으로 만든 것.

### 6. 무거운 탐색은 격리한다 — Explore, Multimodal-Looker
Explore(코드베이스 grep)·Multimodal-Looker(PDF/이미지)는 **중간 결과가 폭발하는 작업**을 격리된 subagent 컨텍스트에서 처리하고 요약만 돌려준다. [Anthropic이 말하는 서브에이전트 컨텍스트 격리](/2026/07/24/choosing-multi-agent-architecture/) — 소음이 메인을 오염시키지 않게.

### 7. 워커는 동적으로 소환한다 — Sisyphus-Junior (category 소환)
Sisyphus-Junior는 **category로 소환되는 실행 워커**다. 오케스트레이터가 필요할 때 필요한 워커를 띄우는 구조 — 정적 배치가 아니라 [orchestrator가 하위작업을 동적 분해](/2026/07/23/multi-agent-coordination-patterns/)해 워커에 위임하는 패턴.

---

## 이 로스터가 하네스 설계에 주는 교훈

개별 에이전트를 넘어, 로스터 *전체*가 보여주는 설계 철학:

- **역할은 곧 권한이다.** 계획자는 못 짓고(Prometheus), 자문역은 읽기만(Oracle/Metis), 비평가는 통과만 판정(Momus). 각 에이전트의 이름이 곧 *할 수 있는 것의 경계*다.
- **분리가 기본, 통합이 예외.** 계획/실행/검증/탐색/검색이 다 다른 주체다. 하나가 다 하면 편하지만, 그 편함이 [계약 표류·자기 정당화·컨텍스트 오염](/2026/07/24/when-multi-agent-is-a-loss/)을 부른다.
- **2축으로 관리하면 확장이 싸다.** 새 능력이 필요하면 "primary/subagent × 실행/계획/워커" 중 어느 칸인지만 정하면 된다. 명단이 늘어도 정신 모델은 그대로다.
- **근거·리뷰가 에이전트에 *내장*된다.** Librarian의 permalink, Momus의 리뷰 게이트처럼 — 좋은 규율은 프롬프트로 부탁하는 게 아니라 [전용 역할로 구조화](/2026/07/23/ai-work-operating-rules/)한다.

주의할 균형점도 있다: 이렇게 잘게 나눈 로스터는 강력하지만, [MVP·저복잡도 작업엔 과한 세팅](/2026/07/24/when-multi-agent-is-a-loss/)일 수 있다. 로스터의 깊이는 *워크로드가 정당화할 때* 값을 한다.

---

## 한 줄 결론

oh-my-agent의 로스터가 가르치는 건 하나다 — **하네스 설계는 "얼마나 똑똑한 에이전트를 두느냐"가 아니라 "역할과 권한을 어떻게 쪼개느냐"의 문제**다. 계획·실행·검증·탐색·검색·비평을 다른 주체로 나누고, 각 주체의 이름이 곧 권한의 경계가 되게 하라. 그리고 그 명단을 2축으로 관리하면, 하네스는 커져도 이해 가능한 상태로 남는다.

---

## 출처

- 첨부 이미지 2장: 사용자 제공(oh-my-agent 에이전트 로스터). 본문 분석은 이 로스터에 나타난 구조를 근거로 하며, 그림에 없는 내부 구현은 단정하지 않았다.
- 설계 원칙의 근거(공식·본인 정리): Anthropic [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)·[Coordination Patterns](https://claude.com/blog/multi-agent-coordination-patterns) · [Ouroboros 3부작](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) · [Explorer/Implementer/Verifier](/2026/07/23/agent-roles-explorer-implementer-verifier/) · [하네스의 세 문서](/2026/07/24/harness-spec-plan-done-criteria/) · [멀티에이전트가 손해인 순간](/2026/07/24/when-multi-agent-is-a-loss/)

> 참고: "oh-my-agent"의 구조 해석은 사용자 제공 로스터 기준의 교육적 분석이며, 각 에이전트를 일반적 에이전트-아키텍처 원칙(오케스트레이터-워커·최소권한·리뷰 게이트·컨텍스트 격리)에 대응시켜 설명했다.
