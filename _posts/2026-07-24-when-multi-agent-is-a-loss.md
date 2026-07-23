---
layout: post
title: "멀티에이전트가 '손해'인 순간 — 복잡함이 곧 멀티에이전트는 아니다"
date: 2026-07-24 06:35:00 +0900
categories: [AI, Architecture]
tags: [MultiAgent, AntiPatterns, SingleAgent, CoordinationCost, TokenCost, ClaudeCode, AgentArchitecture]
---

# 멀티에이전트를 안 쓰는 것이 정답일 때

지난 며칠 멀티에이전트 아키텍처를 여러 각도로 정리했다. 이제 정반대편에서 봐야 균형이 맞는다 — **멀티에이전트가 오히려 손해인 순간.** 핵심 명제부터: **복잡한 문제라고 해서 곧바로 Multi-Agent가 필요한 것은 아니다.** LangChain도, Anthropic도 같은 말을 한다 — 복잡한 작업이라도 *단일 에이전트 + 동적 도구 + 좋은 프롬프트*만으로 충분한 경우가 많다.

아래 표가 "멀티에이전트가 손해가 되는 8가지 경우"와 그 처방이다.

![멀티에이전트가 손해인 경우 8가지 — 문제가 되는 경우 · 왜 문제가 되는가 · 해결 방향](/assets/images/when-multi-agent-is-a-loss.jpg)

| 문제가 되는 경우 | 왜 손해인가 | 해결 방향 |
|---|---|---|
| 단일 LLM 호출로 충분한 작업 | 조정 비용이 품질 이득보다 큼 | 단일 에이전트 + 좋은 프롬프트 + RAG + few-shot |
| 컨텍스트를 나누기 어려운 작업 | 에이전트 간 정보 전달에서 손실 발생 | 하나의 에이전트가 전체 문맥 유지 |
| 강한 순차 의존성 작업 | 병렬화해도 대기 안 줄고 조정 비용만 증가 | Prompt chaining / 명시적 state machine |
| 저가치·저위험·저복잡도 작업 | 토큰·시간·디버깅 비용 과도 | 단순 workflow |
| 도구가 많아 헷갈리는 문제 | 전문화보다 *tool selection* 이 핵심 | Tool search·routing·MCP registry 로 도구 노출 최소화 |
| 평가 기준이 모호한 반복 루프 | Generator-Verifier 무한 반복 or 조기 성공 선언 | 명확한 acceptance criteria·negative test·최대 반복 수 |
| 공유 파일·상태 동시 수정 | 충돌·중복·모순 변경 | worktree 분리·lock·merge gate·integration test |
| 운영 관측성 낮은 시스템 | 실패 원인 추적 불가 | trace·checkpoint·durable state·end-state 평가 |

---

## 손해의 정체 — 멀티에이전트가 물리는 세금

8가지를 관통하는 원리는 하나다. **멀티에이전트는 공짜가 아니라 세금을 문다.** 그 이득이 세금보다 클 때만 흑자다.

### 세금 1 — 조정 비용(coordination cost)
1·3·4행이 여기 걸린다. 에이전트를 늘리면 "누가 무엇을 언제"를 조율하는 비용이 생긴다. 단일 LLM 호출로 끝날 일, 순차 의존이 강한 일, 애초에 저가치인 일에 이 비용을 물면 **품질 이득 < 조정 비용**이 되어 순손실이다. Anthropic도 못 박는다 — 에이전틱 시스템은 *더 나은 성능을 위해 지연과 비용을 희생하는 교환*이고, 그 교환은 특정 경우에만 정당하다. 처방은 단순하다: **단일 에이전트 + 좋은 프롬프트 + RAG + few-shot.**

### 세금 2 — 토큰 증식
4·2행. 멀티에이전트는 토큰을 곱한다. Anthropic 실측: 에이전트는 챗의 **~4배**, 멀티에이전트는 **~15배** 토큰을 쓰고, 성능 평가 분산의 **80%가 토큰 사용량만으로 설명**된다. 즉 이득의 상당 부분이 *더 태운 토큰*의 결과다. 저위험·저복잡도 작업에 15배를 물 이유가 없다.

### 세금 3 — 정보 손실(handoff loss)
2·3행. 컨텍스트를 여러 에이전트로 쪼개면 그 경계마다 정보가 샌다. Anthropic이 "모든 에이전트가 *같은 컨텍스트를 공유해야 하는* 작업엔 멀티에이전트가 부적합"이라 한 이유다. 문맥이 나뉘면 안 되는 일은 **하나의 에이전트가 전체를 쥐는 것**이 맞다.

### 세금 4 — 무한 루프와 게이밍
6행. 평가 기준이 모호한 채 Generator-Verifier를 돌리면, verifier가 무한 반복하거나 조기에 "성공" 선언한다. Anthropic도 경고한다 — "검증이 무엇인지 정의하지 않은 채 루프만 돌리면 실체 없는 *품질 통제의 환상*이 생긴다." 처방은 [Ouroboros가 코드로 강제한 것](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)과 같다: **명확한 acceptance criteria·negative test·최대 반복 수.** 관문 없는 루프는 토큰 소각로다.

### 세금 5 — 공유 상태 충돌
7행. 여러 에이전트가 공유 파일·상태를 동시에 만지면 충돌·중복·모순이 터진다. [Anthropic 조율 패턴](/2026/07/23/multi-agent-coordination-patterns/)이 Shared-State의 약점으로 꼽은 바로 그것. 처방은 [Explorer/Implementer/Verifier 역할 분리](/2026/07/23/agent-roles-explorer-implementer-verifier/)와 통한다: **worktree 분리·lock·merge gate·integration test** 로 동시 쓰기를 구조적으로 차단.

### 세금 6 — 디버깅 불투명
8행. 에이전트가 많아질수록 "왜 실패했나"를 추적하기 어렵다. Anthropic도 "전체 프로덕션 트레이싱을 붙이자 에이전트가 왜 실패했는지 진단하고 체계적으로 고칠 수 있었다"고 했다. 관측성 없는 멀티에이전트는 켜기 전에 **trace·checkpoint·durable state·end-state 평가**부터 깔아야 한다. ([관측 도구는 여기 정리](/2026/07/23/llm-observability-langfuse-langsmith-arize/).)

---

## 반직관적인 한 줄 — "도구 문제를 에이전트로 풀지 마라"

표에서 가장 통찰적인 행은 5번이다. **도구가 많아 헷갈리는 문제를, 에이전트를 늘려서 풀려는 함정.** 진짜 문제는 *전문화 부족*이 아니라 *tool selection*(어떤 도구를 쓸지 고르는 것)일 때가 많다. 이럴 땐 에이전트를 쪼갤 게 아니라 **도구 노출을 줄여야** 한다 — tool search, tool routing, MCP tool registry로 "지금 필요한 도구만" 보이게. 에이전트 수가 아니라 *도구 표면적*이 병목이었던 것이다.

이건 내가 실제로 쓰는 방식이기도 하다 — 도구가 수십 개여도 deferred tool + 검색으로 필요할 때만 로드하면, 에이전트 하나가 충분히 다룬다.

---

## 결정 규칙 — 언제 흑자인가

복잡함은 멀티에이전트의 조건이 아니다. 멀티에이전트가 흑자인 건 **오직** 이럴 때다(Anthropic 기준):

- **병렬화가 크고**, **정보가 단일 컨텍스트 창을 넘고**, **복잡한 도구가 많은** 고가치 작업

반대로 위 8가지 중 하나라도 해당하면, 멀티에이전트는 *비용만 늘리고 품질은 안 늘리는* 순손실이다. 그래서 사다리를 지켜야 한다:

> **단일 에이전트 + 좋은 프롬프트부터. 에이전트를 늘리기 전에 도구를 먼저. 명확한 한계에 부딪혔을 때만 멀티에이전트로.**

멀티에이전트는 능력의 증거가 아니라 *특정 제약에 대한 값비싼 처방*이다. 그 제약이 없다면, 안 쓰는 것이 실력이다.

---

## 출처

- 첨부 이미지: 사용자 제공(멀티에이전트가 손해인 8가지 경우). 표 상단 인용은 LangChain Docs 기준.
- Anthropic, [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — "가장 단순한 해법부터", 에이전틱은 지연·비용 교환
- Anthropic, [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system) — ~15배 토큰·분산 80% 설명·"공유 컨텍스트 필요 작업엔 부적합"·프로덕션 트레이싱
- Anthropic, [Multi-Agent Coordination Patterns](https://claude.com/blog/multi-agent-coordination-patterns) — Generator-Verifier "품질 통제의 환상", Shared-State 충돌
- 관련 본인 정리글: [LangChain 4패턴](/2026/07/24/choosing-multi-agent-architecture/) · [Ouroboros 3부작](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) · [Explorer/Implementer/Verifier](/2026/07/23/agent-roles-explorer-implementer-verifier/)

> 참고: 8가지 경우·처방은 이미지(LangChain Docs 인용) 기준이며, 본문은 각 항목의 "왜/처방"을 Anthropic·LangChain 공식 자료로 근거 대는 방식으로 정리했다. 정량 수치(15배·80%)는 Anthropic 공식 게시물 기준이다.
