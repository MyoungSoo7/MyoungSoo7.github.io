---
layout: post
title: "멀티에이전트 아키텍처 고르기 — LangChain의 4패턴과 실측 비용 비교"
date: 2026-07-24 06:25:00 +0900
categories: [AI, Architecture]
tags: [MultiAgent, LangChain, Subagents, Skills, Handoffs, Router, TokenCost, AgentArchitecture]
---

# 패턴은 4개, 질문은 하나 — "내 제약이 무엇인가"

LangChain이 발표한 [Choosing the Right Multi-Agent Architecture](https://www.langchain.com/blog/choosing-the-right-multi-agent-architecture)는 멀티에이전트를 4개의 아키텍처로 정리하고, **각각의 실측 비용(모델 호출·토큰)까지** 비교한다. 어제 정리한 [Anthropic의 조율 패턴 5가지](/2026/07/23/multi-agent-coordination-patterns/)와 나란히 놓으면, 같은 문제를 다른 렌즈로 보는 셈이다.

대전제는 동일하다 — **단일 에이전트 + 좋은 도구로 대부분 충분하다.** 다만 규모가 커지면 두 제약이 멀티에이전트를 부른다: ① **컨텍스트 관리**(전문 지식이 단일 프롬프트에 안 들어감), ② **분산 개발**(팀별 소유 경계가 필요함). (LangChain도 Anthropic의 그 수치 — 서브에이전트가 단일 Opus 4 대비 **90.2% 향상** — 를 인용한다.)

---

## 4가지 아키텍처

### 1. Subagents — 중앙 오케스트레이션
- **정의**: 슈퍼바이저 에이전트가 전문 서브에이전트를 *도구처럼 호출*해 조율. 서브에이전트는 **stateless**(과거 상호작용 미보유).
- **메커니즘**: 메인이 어떤 서브에이전트를 부를지 결정 → 입력 제공 → 결과 종합.
- **장점**: 중앙 통제, 병렬 실행, 강한 컨텍스트 격리
- **단점**: 상호작용마다 모델 호출 1회 추가(결과가 메인을 거쳐 흐름) → 지연·토큰 비용↑
- **적합**: 여러 구분된 도메인을 중앙에서 워크플로 통제 (예: 캘린더·이메일·CRM 조율 개인비서, 도메인 전문가 리서치)
- LangChain의 **Deep Agents**가 즉시 사용 구현 제공

### 2. Skills — 점진적 공개(Progressive Disclosure)
- **정의**: 단일 에이전트가 전문 프롬프트·지식을 **온디맨드로 동적 로딩**. 프롬프트 기반 특화로 *준(quasi)-멀티에이전트*.
- **메커니즘**: 처음엔 스킬 이름·설명만 알고, 관련될 때 전체 컨텍스트 로드, 필요 시 세부 추가 발견.
- **장점**: 단순함, 사용자와 직접 상호작용, 분산 팀 유지보수
- **단점**: 컨텍스트가 대화 기록에 누적 → 이후 호출에서 토큰 팽창
- **적합**: 많은 특화가 있지만 능력 간 제약이 없는 단일 에이전트 (예: 코딩 에이전트, 창작 어시스턴트)

### 3. Handoffs — 상태 기반 전환
- **정의**: 대화 맥락에 따라 *활성 에이전트가 동적으로 바뀜*. 에이전트가 도구 호출로 다른 에이전트에 넘김.
- **메커니즘**: handoff 도구가 상태를 갱신해 다음 활성 에이전트를 결정. 상태가 턴을 넘어 유지 → 순차 워크플로.
- **장점**: 유려한 멀티턴 대화, 단계 간 자연스러운 컨텍스트 이월
- **단점**: 더 stateful → 상태 관리를 세심히 해야 함
- **적합**: 전제조건이 있는 순차 워크플로 (예: 단계별로 정보 수집하는 고객 지원)

### 4. Router — 병렬 디스패치 & 종합
- **정의**: 라우팅 단계가 입력을 분류해 전문 에이전트로 보내고, **병렬 실행** 후 결과를 종합. 보통 stateless.
- **메커니즘**: 라우터가 질의를 분해 → 여러 전문 에이전트 동시 호출 → 일관된 응답으로 종합.
- **장점**: 구분된 수직 영역 병렬 실행, 요청당 일관된 성능
- **단점**: stateless라 대화 기록마다 라우팅 오버헤드 반복 (대화형 에이전트 안에 라우터를 도구로 감싸면 완화)
- **적합**: 구분된 지식 도메인을 동시 조회 (예: 기업 지식베이스, 멀티버티컬 고객 지원)

---

## 결정 프레임워크

| 내 요구사항 | 패턴 |
|---|---|
| 여러 구분 도메인(캘린더·이메일·CRM), 병렬 실행 필요 | **Subagents** |
| 많은 특화를 가진 단일 에이전트, 가벼운 조합 | **Skills** |
| 상태 전환이 있는 순차 워크플로, 에이전트가 내내 사용자와 대화 | **Handoffs** |
| 구분된 수직 영역을 병렬 조회 후 종합 | **Router** |

### 요구사항 비교 매트릭스 (별점은 원문 기준)

| 패턴 | 분산 개발 | 병렬화 | 멀티홉 | 직접 사용자 상호작용 |
|---|---|---|---|---|
| **Subagents** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Skills** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Handoffs** | — | — | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Router** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐ |

---

## 이 글의 백미 — 실측 비용 비교

패턴 설명은 흔하지만, 이 글은 **같은 작업을 4패턴으로 돌렸을 때의 호출·토큰 수**를 제시한다. 이게 진짜 의사결정 근거다.

**시나리오 1 — 원샷 요청("커피 사줘")**

| 패턴 | 모델 호출 |
|---|---|
| Subagents | 4 |
| Skills / Handoffs / Router | 3 |

→ 단발 요청은 Skills·Handoffs·Router가 효율적(3회). Subagents는 중앙 통제 대가로 1회 더.

**시나리오 2 — 반복 요청(같은 요청 2번)**

| 패턴 | 2턴째 호출 | 총 호출 | 절감 |
|---|---|---|---|
| Subagents | 4 | 8 | — |
| Skills | 2 | 5 | 40% |
| Handoffs | 2 | 5 | 40% |
| Router | 3 | 6 | 25% |

→ **stateful 패턴(Skills·Handoffs)이 반복에서 40% 절감** — 컨텍스트를 유지하니까. Subagents는 stateless라 요청당 비용이 일정.

**시나리오 3 — 멀티도메인 질의(Python·JS·Rust 비교, 도메인당 ~2000토큰)**

| 패턴 | 모델 호출 | 총 토큰 | 비고 |
|---|---|---|---|
| Subagents | 5 | ~9K | 서브에이전트 컨텍스트 격리 |
| Skills | 3 | ~15K | 컨텍스트 누적 |
| Handoffs | 7+ | ~14K+ | 순차 실행 강제 |
| Router | 5 | ~9K | 병렬 실행 |

→ **병렬 패턴(Subagents·Router)이 대용량 도메인에서 압도적** — Subagents가 컨텍스트 격리로 Skills 대비 **토큰 67% 절감**.

### 워크로드별 요약

| 패턴 | 단발 | 반복 | 병렬 | 대용량 컨텍스트 |
|---|---|---|---|---|
| **Subagents** | — | — | ✅ | ✅ |
| **Skills** | ✅ | ✅ | — | — |
| **Handoffs** | ✅ | ✅ | — | — |
| **Router** | ✅ | — | ✅ | ✅ |

핵심 트레이드오프가 선명하다: **stateful(Skills/Handoffs)은 반복·대화에 강하고, 병렬+격리(Subagents/Router)는 대용량·멀티도메인에 강하다.** 컨텍스트 격리는 토큰을 아끼지만(격리) 호출을 늘리고, 컨텍스트 누적은 호출을 아끼지만(재사용) 토큰을 늘린다.

---

## 두 렌즈 겹쳐 보기 — LangChain vs Anthropic

어제 본 [Anthropic의 조율 패턴](/2026/07/23/multi-agent-coordination-patterns/)과 비교하면 관점 차이가 드러난다:

- **공통**: 둘 다 "단일 에이전트부터, 한계가 드러날 때 진화"를 대원칙으로 둔다. Subagents(=Orchestrator-Subagent), Router(=Routing/Fan-out), Handoffs는 명칭까지 겹친다.
- **LangChain 고유**: **Skills를 '준-멀티에이전트'로 승격** — 프롬프트 점진 공개도 하나의 아키텍처로 본다. 그리고 **실측 토큰/호출 비교**가 강점.
- **Anthropic 고유**: **Message Bus / Shared-State** 같은 *탈중앙·이벤트 기반* 패턴, 그리고 **Generator-Verifier**(품질 게이트)를 조율 패턴에 포함.

즉 LangChain은 "요청 하나를 어떻게 처리하나(비용 관점)", Anthropic은 "에이전트 생태계를 어떻게 잇나(정보 흐름 관점)"에 무게가 있다. 둘을 합치면 [멀티에이전트 설계 원칙 13가지](/2026/07/23/multi-agent-system-design-principles/)의 4축(Context 분배·Workflow 제어·Latency 운영·품질 운영)이 채워진다.

---

## 구현 지침 — 사다리를 지켜라

LangChain의 마무리 권고는 시리즈 내내 반복된 그 원칙이다:

> **"단일 에이전트 + 좋은 프롬프트 엔지니어링부터 시작하라. 에이전트를 늘리기 전에 도구를 먼저 늘려라. 명확한 한계에 부딪혔을 때만 멀티에이전트로 올라가라."**

패턴은 뷔페가 아니라 사다리다. 그리고 이제 그 사다리를 올라갈 때, **각 칸의 실측 비용표**를 근거로 고를 수 있다.

---

## 출처

- 원문(첨부): LangChain, **Choosing the Right Multi-Agent Architecture** — 4패턴 정의·결정 프레임워크·실측 비용 시나리오: <https://www.langchain.com/blog/choosing-the-right-multi-agent-architecture>
- 관련(공식): Anthropic, [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)(90.2% 수치 원출처) · [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- 관련 본인 정리글: [Anthropic 조율 패턴 5가지](/2026/07/23/multi-agent-coordination-patterns/) · [멀티에이전트 설계 원칙 13가지](/2026/07/23/multi-agent-system-design-principles/) · [Explorer/Implementer/Verifier 역할 분리](/2026/07/23/agent-roles-explorer-implementer-verifier/)

> 참고: 패턴 정의·별점·비용 수치는 LangChain 공식 게시물 기준이며, 시나리오 토큰/호출 값은 원문의 예시 측정치다.
