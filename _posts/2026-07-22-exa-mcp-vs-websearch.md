---
layout: post
title: "Exa MCP vs 내장 WebSearch — 근거로 따져본 성능과 기대 효과"
date: 2026-07-22 23:15:00 +0900
categories: [AI, Tooling]
tags: [Exa, WebSearch, MCP, Anthropic, NeuralSearch, RAG, Benchmark, TokenEfficiency, HarnessEngineering]
---

# 왜 웹검색의 '주축'을 바꿨나

오늘 나는 두 하네스(Claude Code · Codex)의 전역 설정에서 **웹검색 1순위를 내장 WebSearch가 아니라 [Exa](https://exa.ai) MCP로 바꿨다.** 그런데 도구를 갈아 끼우는 건 쉽고, *왜* 갈아 끼웠는지를 근거로 대는 건 어렵다. 이 글은 마케팅 문구가 아니라 **1차 공식 자료만** 근거로, 두 도구가 실제로 무엇이 다르고 무엇을 기대할 수 있는지 따져본 기록이다.

먼저 결론부터: **두 도구는 애초에 같은 종류의 물건이 아니다.** 그래서 "누가 더 낫다"보다 "어느 상황의 주축으로 둘 것인가"가 옳은 질문이다.

---

## 1. 둘은 '같은 것'이 아니다 — 설계 목적이 다르다

| 구분 | Anthropic 내장 WebSearch | Exa (MCP) |
|---|---|---|
| 정체 | 모델 턴 안에서 도는 **관리형 server tool** | **뉴럴 검색 API**를 MCP로 연결 |
| 검색 방식 | 일반 웹 검색(검색엔진 백엔드) | 임베딩 기반 **의미(semantic) 검색** |
| 인용 | **항상 자동 인용**(cited_text 등) | 도구가 clean content·highlights 반환, 인용은 모델 몫 |
| 통합 | 모델에 내장, 별도 설정 불필요 | MCP 서버 등록으로 어떤 클라이언트든 연결 |
| 최적화 대상 | 일반 Q&A·실시간 정보 | 에이전트·RAG 파이프라인 |

Anthropic 공식 문서는 내장 WebSearch를 이렇게 규정한다. 모델이 검색 시점을 스스로 판단하고("Claude determines when to search based on the prompt"), API가 검색을 실행해 결과를 컨텍스트에 넣고, 턴 끝에 **인용이 달린 최종 답변**을 낸다. 인용은 항상 켜져 있다("Citations are always enabled for web search"). ([Anthropic 공식 문서](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool))

Exa는 반대로 **검색 자체가 제품**이다. MCP는 그 제품을 하네스에 꽂는 표준 커넥터일 뿐이다. MCP는 공식적으로 "AI 애플리케이션을 외부 시스템에 연결하는 오픈소스 표준"이자 "AI를 위한 USB-C 포트"로 정의된다. ([Model Context Protocol 공식](https://modelcontextprotocol.io/introduction))

즉 **WebSearch는 '모델에 붙은 편의 기능', Exa는 '검색 엔진 그 자체'**다. 이 차이가 아래 모든 항목의 뿌리다.

---

## 2. 작동 원리 — 키워드 웹검색 vs 뉴럴 검색

내장 WebSearch는 일반 웹 검색엔진 결과를 모델 컨텍스트로 가져온다. 문서의 예시 응답조차 Wikipedia 같은 표준 웹 결과(`url`·`title`·`page_age`)를 돌려준다. ([Anthropic 공식 문서](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)) 강점은 **범용성과 자동 인용**이고, 성격상 검색엔진의 랭킹을 그대로 물려받는다.

Exa는 접근이 다르다. Exa는 자사 블로그에서 "분산 크롤링/파싱 시스템, 자체 학습한 임베딩·리랭킹 모델, 새로 설계한 벡터 데이터베이스"를 직접 구축했다고 밝힌다. 그리고 "복잡한 질의는 의미 이해를 요구하며, 그 지점에서 우리 아키텍처가 강점을 낸다"고 주장한다. ([Exa 공식 블로그 — Evals at Exa](https://exa.ai/blog/evals-at-exa)) 핵심은 **표면 문자열 매칭이 아니라 의미로 랭킹**한다는 것이다. 키워드가 안 겹쳐도 뜻이 맞으면 찾아온다는 얘기다.

RAG·에이전트 관점에서 더 중요한 건 반환 형태다. Exa MCP는 `web_search_exa`(검색)와 함께 **정제된 본문과 highlights(문서 내 핵심 구절 추출)**를 준다. ([exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server)) 검색 결과를 통째로 컨텍스트에 붓는 대신 *답이 실제로 들어있는 구절만* 골라올 수 있다는 뜻이다.

---

## 3. 성능 — 벤치마크가 말하는 것, 그리고 말하지 않는 것

여기서부터는 **정직하게** 봐야 한다. 공개된 정량 비교는 대부분 **Exa 1차(vendor) 벤치마크**다. 다만 한 가지 완화 요인이 있다.

### Exa의 오픈 벤치마크 (재현 가능)

Exa는 벤치마크 코드·데이터셋·방법을 MIT 라이선스로 공개한다([exa-labs/benchmarks](https://github.com/exa-labs/benchmarks)). 벤더가 만든 것이지만 **재현 가능**하다는 점에서 순수 마케팅 수치보다는 검증 여지가 크다. 구성과 대표 수치:

| 트랙 | 규모 | 대표 결과(Exa) | 비교 대상 |
|---|---|---|---|
| People Search | 1,400 질의 | **R@1 72%** (Brave 44.4%) | Brave·Parallel·**Claude**·Perplexity·Tavily |
| Company Search | ~800 질의 | **RAG 정확도 79%** | 〃 |
| WebCode | ~840 질의 | Highlights **groundedness 94.8%** | 〃 |

지표는 R@1·R@10·Precision·Groundedness·Correctness·Completeness·Citation Precision·token efficiency 등을 쓴다. ([exa-labs/benchmarks](https://github.com/exa-labs/benchmarks)) 흥미로운 대목은 **비교 대상에 "Claude"가 포함**된다는 점이다 — 즉 Anthropic 계열 검색과의 대결 레인이 존재한다. (다만 Exa-vs-Claude의 정확한 격차 수치까지는 공개 텍스트로 확인하지 못했으므로 여기서 단정하지 않는다.)

### 공개 표준 벤치마크

Exa는 OpenAI의 **SimpleQA**(짧은 사실 질의로 환각을 유도해 정확도 측정)와 **MSMARCO**(1,000 질의를 GPT-4o가 1~5점 채점)에서 최상위 성능을 보고한다. 공정성을 위해 "경쟁사의 공개 수치와 우리 측정치 중 높은 값을 채택했다"고 밝혔다. ([Exa 공식 블로그 — API Evals](https://exa.ai/blog/api-evals)) 다만 정확한 점수는 차트 이미지로만 제시돼 있어, 이 글에서는 구체 수치를 인용하지 않는다.

### 벤치마크가 '말하지 않는' 것 (한계)

- 이 수치들은 전부 **Exa가 설계·실행한 평가**다. 재현 가능하다는 건 신뢰를 *높이지만* 중립성을 *보장하지는* 않는다.
- 내가 찾은 범위에서 **중립적 제3자가 Exa vs Anthropic WebSearch를 직접 맞붙인 헤드투헤드는 없다.**
- Anthropic은 공식 문서에서 **경쟁 정확도 수치를 아예 공표하지 않는다.** 문서는 "무엇을 할 수 있는가(capability)"를 규정할 뿐, "누구보다 정확한가"를 주장하지 않는다. ([Anthropic 공식 문서](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool))

그래서 정직한 결론은 이렇다. **"Exa가 의미 검색·RAG 지표에서 앞선다는 근거는 재현 가능한 형태로 존재하지만, Anthropic WebSearch를 같은 잣대로 맞붙인 중립 데이터는 부재하다."** 이 문장 이상으로 나가면 과장이다.

---

## 4. 기대 효과 — 내 하네스(에이전트/RAG) 관점

성능 수치보다 내 쓰임에 직접 걸리는 건 **토큰 효율과 반환 품질**이다.

**토큰 효율.** 내장 WebSearch도 이 문제를 안다. 기본 검색은 "모든 검색 결과를 컨텍스트에 싣고, 그중 상당수가 무관"한데, 최신 버전은 **dynamic filtering**으로 코드가 결과를 먼저 걸러 컨텍스트에 넣어 토큰을 줄인다. ([Anthropic 공식 문서](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)) Exa는 다른 각도로 같은 문제를 푼다 — **highlights로 답이 든 구절만** 뽑아온다. 두 도구 모두 "결과 전체를 붓지 말자"는 방향이지만, Exa는 그게 검색 엔진 층위에서 기본 제공된다.

**비용.** 공식 가격 기준으로 정리하면:

| 항목 | 가격(공식) |
|---|---|
| Anthropic WebSearch | **$10 / 1,000 검색** + 표준 토큰 비용 ([Anthropic](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)) |
| Exa Search (≤10 results) | **$7 / 1,000 요청** ([Exa Pricing](https://exa.ai/pricing)) |
| Exa Deep Search | $12 / 1,000 요청 ([Exa Pricing](https://exa.ai/pricing)) |
| Exa Contents(본문) | $1 / 1,000 pages ([Exa Pricing](https://exa.ai/pricing)) |

기본 검색은 Exa($7)가 WebSearch($10)보다 저렴하고, 대신 심층 검색·본문 회수는 별도 과금 구조다. **비용 우위는 "단순 검색"에서 뚜렷하고, 파이프라인을 어떻게 짜느냐에 따라 역전될 수 있다.**

**정리하면 내 기대 효과는** ─ ① 의미 검색으로 *놓치던 문서*를 잡고, ② highlights로 *컨텍스트를 덜 먹고*, ③ 단순 검색은 *더 싸게*. 다만 ④ 자동 인용·관리 편의·ZDR 같은 운영 특성은 내장 WebSearch가 그대로 강점이다.

---

## 5. 그래서 어떻게 두었나 — 주축은 Exa, 폴백은 WebSearch

나는 [며칠 전 하네스는 겹쳐 쓰는 게 아니라 주축을 고르는 것](/2026/07/22/ouroboros-harness-main-axis/)이라고 적었다. 웹검색도 같은 원리로 정리했다.

- **주축 = Exa MCP** (`web_search_exa` 1순위). 의미 검색·highlights·RAG 지향이 내 에이전트/연구 작업의 결과 맞다.
- **폴백 = 내장 WebSearch.** Exa가 실패·미가용일 때만. 자동 인용과 관리 편의가 필요한 범용 질의에는 여전히 훌륭하다.

이건 "WebSearch가 나쁘다"는 결론이 **아니다.** 오히려 문서를 읽을수록 내장 WebSearch는 *잘 설계된 범용 도구*였다. 내 선택은 **"내 워크로드(에이전트·RAG)의 설계 목적에 더 맞는 쪽을 1순위로"**일 뿐이다. 워크로드가 다르면 답도 달라진다.

---

## 마치며 — 근거의 등급을 구분하자

이 글을 쓰며 지킨 원칙 하나: **자료의 등급을 섞지 않기.**

- **1차·공식**(Anthropic 문서, MCP 사양, Exa 문서/가격) → 사실로 인용.
- **벤더 벤치마크(재현 가능)**(exa-labs/benchmarks) → "Exa 주장, 단 검증 여지 있음"으로 명시.
- **중립 제3자 헤드투헤드** → **부재**. 그래서 성능 우열을 단정하지 않음.

도구를 바꾸는 결정은 쉽다. 어려운 건 *바꿀 자격이 있는 근거인지*를 등급까지 나눠 정직하게 대는 일이다. Exa를 주축으로 둔 건 "더 빠르다·더 똑똑하다"는 광고 때문이 아니라, **내 워크로드의 설계 목적과 맞고, 그 근거가 재현 가능한 형태로 존재하기 때문**이다.

---

## 출처 (모두 1차·공식 자료)

- Anthropic, **Web search tool** (공식 문서) — 작동 방식·자동 인용·dynamic filtering·가격 $10/1,000: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool>
- Model Context Protocol, **What is MCP** (공식) — MCP 정의·아키텍처: <https://modelcontextprotocol.io/introduction>
- Exa, **Evals at Exa** (공식 블로그) — 뉴럴 검색 구조·평가 철학: <https://exa.ai/blog/evals-at-exa>
- Exa, **Web Search API Evals** (공식 블로그) — SimpleQA·MSMARCO 방법론: <https://exa.ai/blog/api-evals>
- exa-labs, **benchmarks** (오픈소스, MIT) — 재현 가능한 벤치마크 코드·데이터·수치: <https://github.com/exa-labs/benchmarks>
- exa-labs, **exa-mcp-server** (공식 저장소) — MCP 툴(`web_search_exa`·`web_fetch_exa`): <https://github.com/exa-labs/exa-mcp-server>
- Exa, **Pricing** (공식) — Search $7/1k·Deep $12/1k·Contents $1/1k pages: <https://exa.ai/pricing>

> 면책: 성능 관련 정량 수치는 Exa 1차 벤치마크에 근거하며, 재현 가능하나 중립 제3자 검증은 아니다. 중립적 Exa-vs-WebSearch 헤드투헤드는 확인되지 않았다.
