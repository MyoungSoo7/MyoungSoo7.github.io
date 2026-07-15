---
layout: post
title: "무엇에도 종속되지 않기 — 이식 가능한 에이전트 하네스의 두 결합 끊기"
date: 2026-07-15 21:00:00 +0900
categories: [AI, Agents, architecture]
tags: [agent, harness, mcp, stateless, runtime, adapter, tool-catalog, capability, portability, task-harness]
---

에이전트 시스템을 오래 굴리다 보면 한 가지 두려움이 생긴다. **종속.** 특정 벤더의 런타임에 묶이고, 특정 세션 상태에 묶이면, 그 위에 쌓은 모든 게 그 결정과 함께 죽는다. 모델은 6개월마다 갈리고, CLI는 이름을 바꾸고, 가격 정책은 하루아침에 뒤집힌다.

그래서 내 에이전트 하네스(harness)의 설계는 두 개의 **결합 끊기(decoupling)** 위에 서 있다. 하나는 *세션*으로부터, 다른 하나는 *런타임*으로부터. 아래 세 장의 카드가 그 두 원칙과, 그 원칙이 사는 **3계층 분리 모델**을 한 줄씩으로 압축한다.

---

## 1. 세션으로부터의 결합 끊기 — stateless와 capability

![stateless가 강제하는 건 결국 "이 도구가 무엇을 할 수 있나"를 매번 분명히 알리는 일이다. WHY 세션 없음→ 매 호출 독립→ capability가 호출 단위→ 도구 카탈로그가 자산](/assets/images/posts/agent-harness-stateless-oneliner.jpg)

> **"stateless가 강제하는 건 결국 '이 도구가 무엇을 할 수 있나'를 매번 분명히 알리는 일이다."**

처음엔 stateless가 제약처럼 느껴진다. 세션에 상태를 못 들고 있으니 매 호출이 맨바닥에서 시작한다. 그런데 이 제약이 사실은 **더 나은 설계를 강제**한다. 카드의 WHY 사슬을 따라가 보자.

```
세션 없음  →  매 호출 독립  →  capability가 호출 단위  →  도구 카탈로그가 자산
```

- **세션 없음** — 호출과 호출 사이에 숨은 상태가 없다. "아까 그거"에 기대지 못한다.
- **매 호출 독립** — 그러니 매 호출은 자기가 필요한 걸 스스로 다 들고 와야 한다. 재현 가능하고, 재시도 가능하고, 병렬화 가능하다.
- **capability가 호출 단위** — 그 결과, 시스템의 최소 단위가 "세션"이 아니라 **"이 도구가 무엇을 할 수 있는가(capability)"** 가 된다. 각 도구는 매번 자기 능력을 명시적으로 선언한다.
- **도구 카탈로그가 자산** — 능력이 호출 단위로 명시되면, **도구들의 카탈로그 자체가 시스템의 핵심 자산**이 된다. 무엇을 할 수 있는지가 코드에 흩어져 숨지 않고, 조회 가능한 목록으로 드러난다.

이것이 MCP(Model Context Protocol)류 설계의 핵심이기도 하다. 도구를 stateless·capability 단위로 두면, 에이전트는 "지금 필요한 능력"을 카탈로그에서 골라 조립한다. 상태는 도구가 아니라 **바깥(스토리지·파일·DB)** 에 있고, 도구는 순수 함수에 가까워진다. 테스트하기 쉽고, 갈아끼우기 쉽고, 다른 에이전트가 그대로 재사용한다.

> 역설: 상태를 *못* 갖게 강제하니, 오히려 능력이 *명확히* 드러난다. 제약이 명료함을 낳는다.

---

## 2. 런타임으로부터의 결합 끊기 — 어댑터와 팩토리

![런타임은 이미 6개 + 추가 adapter다. 하나에 종속되면 안 된다 — Claude Code / Codex CLI / OpenCode / Hermes / Kiro CLI / Copilot CLI + 추가 adapter + 커스텀 런타임](/assets/images/posts/agent-harness-runtime-adapters.jpg)

> **"런타임은 이미 6개 + 추가 adapter다. 하나에 종속되면 안 된다."**

두 번째 카드는 에이전트를 *실행하는* 런타임들의 지도다. 하나가 아니라 여섯 + α다.

| # | 런타임 | 성격 |
|---|---|---|
| 01 | **Claude Code** | Claude(Anthropic) · Max Plan · 기본 파일·Bash 도구 |
| 02 | **Codex CLI** | GPT 계열 · OpenAI API key · per-token 과금 |
| 03 | **OpenCode** | provider 의존(교체형) · 기본 파일·Bash 도구 |
| 04 | **Hermes** | NousResearch · 로컬 실행 · MCP 기반 custom skills |
| 05 | **Kiro CLI** | Claude(AWS) · Kiro AWS sign-in |
| 06 | **Copilot CLI** | live-discovered 모델 · Copilot 구독 |
| + | **추가 adapter** | `providers/` 의 Gemini · Goose · LiteLLM · Anthropic SDK |
| ∞ | **커스텀 런타임** | `AgentRuntime` 구현 → `runtime_factory.py` 등록 |

이 표를 관통하는 설계 원칙은 하나다 — **런타임은 교체 가능한 부품이어야 한다.** 그래서 하네스는 특정 CLI의 API를 직접 부르지 않는다. 대신:

- 각 런타임을 **어댑터**로 감싼다. 과금 모델(Max Plan / per-token / 구독), 인증 방식(API key / AWS sign-in / 로컬), 모델 소스가 제각각이어도, 하네스는 동일한 인터페이스로만 대화한다.
- 새 런타임은 **`AgentRuntime` 인터페이스를 구현하고 `runtime_factory.py`에 등록**하면 끝(∞ 칸). 팩토리 패턴이 "어떤 런타임을 쓸지"의 결정을 한 곳으로 모은다.
- `providers/`(Gemini · Goose · LiteLLM · Anthropic SDK)는 그 어댑터 계층이 이미 다중 공급자로 열려 있음을 보여준다.

효과는 실전에서 드러난다. 어떤 작업은 Max Plan의 Claude Code로 싸게 돌리고, 토큰 민감한 대량 작업은 per-token Codex로, 로컬·오프라인이 필요하면 Hermes로, 조직 정책이 AWS면 Kiro로 — **같은 하네스, 같은 도구 카탈로그, 다른 런타임.** 벤더가 가격을 올리거나 모델을 내려도, 어댑터 하나 바꾸면 그만이다.

---

## 3. 두 결합 끊기가 사는 곳 — 3계층 분리 모델

그럼 이 두 번의 결합 끊기는 아키텍처의 *어디에* 자리 잡을까. 세 번째 카드가 그 지도를 그린다 — 하네스를 세 층으로 가르고, 각 층이 런타임을 바꿔도 **같은지 다른지**를 못 박는다.

![3계층 분리 — Workflow Layer(identical, 어디서나 같음): Seed·AC tree·event store·평가 게이트·checkpoint / Runtime Layer(differs, 런타임마다 다름): 모델·인증·도구 surface·권한·비용 / Integration Surface(UX differs, 런타임마다 다름): UI·호출 방법·MCP 통합·세션 보존](/assets/images/posts/agent-harness-three-layers.jpg)

| 층 | 런타임 바꾸면? | 내용물 |
|---|---|---|
| **Workflow Layer** | **어디서나 같음** (identical) | Seed · AC tree · event store · 평가 게이트 · checkpoint |
| **Runtime Layer** | 런타임마다 다름 (differs) | 모델 · 인증 · 도구 surface · 권한 · 비용 |
| **Integration Surface** | 런타임마다 다름 (UX differs) | UI · 호출 방법 · MCP 통합 · 세션 보존 |

이 표가 앞의 두 카드가 *왜 필요한지*를 설명한다.

- **맨 위 Workflow Layer는 어디서나 동일하다.** 작업의 씨앗(Seed), 결정 트리(AC tree), 사건 로그(event store), 평가 게이트, 체크포인트 — 이 **결정론적 오케스트레이션**은 런타임이 무엇이든 똑같이 돌아야 한다. 이게 자산의 본체다.
- **가운데 Runtime Layer는 런타임마다 다르다.** 모델·인증·도구 surface·권한·비용. 바로 **카드 2**가 어댑터로 감싼 그 계층이다. 다양성을 여기에 *가둔다.*
- **맨 아래 Integration Surface도 다르다.** UI, 호출 방법, MCP 통합, 세션 보존 방식 — 런타임마다 UX가 다르다.

핵심은 이것이다: **Workflow Layer가 "어디서나 같음"을 유지할 수 있는 이유가 바로 앞의 두 결합 끊기다.**

- 도구를 stateless·capability로 두었기에(카드 1), 워크플로가 세션 상태에 안 묶여 어느 런타임에서도 같은 순서로 재현된다.
- 런타임을 어댑터로 가두었기에(카드 2), 모델·인증·비용의 차이가 Runtime Layer 안에 격리되어 Workflow Layer로 새지 않는다.

즉 **변하는 것(런타임·통합 UX)을 아래 두 층에 격리했기 때문에, 변하면 안 되는 것(워크플로)이 맨 위에서 불변으로 남는다.** 소프트웨어 설계의 오래된 지혜 — "변하는 것과 변하지 않는 것을 분리하라" — 를 에이전트 하네스에 적용한 형태다.

이 이식성(portability)이 실제로 얼마나 중요한지는, 나 자신이 이 하네스를 텔레그램에서 매일 굴리며 체감한다. 오늘은 이 런타임, 내일은 저 런타임으로 같은 작업 파이프라인(코드→CI→PR→배포→관측)을 돌린다. **Workflow Layer는 그대로고, 아래 두 층만 바뀐다.** 지금 이 글을 쓰는 에이전트도 그 하네스 위에서 돈다.

---

## 4. 한 줄 요약

| 카드 | 무엇으로부터 | 어떻게 | 결과 |
|---|---|---|---|
| ① stateless | 세션 결합 | capability를 호출 단위로 | 도구 카탈로그가 자산 |
| ② 런타임 6+α | 벤더 결합 | 어댑터 + factory 등록 | 런타임을 부품처럼 교체 |

빠르게 움직이는 판에서 오래 살아남는 시스템의 공통점은, 무엇을 잘 붙였느냐가 아니라 **무엇에 안 묶였느냐**다. 세션에도, 런타임에도 종속되지 않는 것 — 그 두 번의 결합 끊기가, 다음 모델이 나오고 다음 CLI가 등장해도 흔들리지 않는 에이전트 하네스의 뼈대다.
