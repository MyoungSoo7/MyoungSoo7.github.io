---
layout: post
title: "\"Jev 가 LLM 보다 낫다\" 에는 분모가 없다 — 주장을 출처별로 갈라 읽기"
date: 2026-09-22 22:16:57 +0900
categories: [ai]
tags: [jev, typesafe, system-one-models, benchmarks, calibration, evaluation]
---

Jev 가 나온 지 일주일 됐고, "요즘 LLM 보다 낫다더라" 라는 말이 돌기 시작했다. 이 글은 그 말의
출처를 하나씩 되짚는다. 결론부터 적으면 **화제성은 사실이고, "낫다" 는 TypeSafe 자신도 하지
않은 주장**이다.

## 1. 화제성은 진짜다

2026-09-15 공개, 창업자 Diogo Almeida 는 전 OpenAI 로 ChatGPT 뒤의 지시따르기 연구를 한
사람이다. 본인이 런치 포스트에 그렇게 적었다.[^1] 일반 하드웨어 매체까지 제목을 뽑았고,
Tom's Hardware 는 그 제목에 **193x faster, 445x cheaper** 를 그대로 실었다.[^2]

그러니까 "핫하다" 는 물음에는 그렇다고 답해야 맞다. 문제는 그 다음 문장이다.

## 2. 벤더 자신은 "더 똑똑하다" 고 쓰지 않았다

런치 포스트의 핵심 문장은 이거다.

> "Jev achieves **similar levels of intelligence** on System One tasks compared to existing
> LLMs, while being two orders of magnitude faster and more efficient."
> — Introducing System One Models and Jev, TypeSafe AI[^1]

지능은 **비슷**, 싸고 빠르다. 이 문장은 비교급이 아니라 동급이다. 마케팅 문구가 아니라
자기네 발표문 본문에 있는 문장이라 이걸 넘어서는 주장은 전부 독자가 덧붙인 것이다.

## 3. 그러면 193.6x·444.6x 는 무엇과 비교한 숫자인가

배수는 분자가 아니라 **분모가 정한다.** 이 숫자의 출처도 같은 포스트의 각주다.

> "This is where the claims of 193.6x faster, 444.6x cheaper on our home page comes from,
> and we expect that these are on **the higher end of real world gains**."[^1]

벤더가 직접 "현실 이득의 상단" 이라고 적어 놨다. 분모는 비싼 프런티어 추론 모델이다.
같은 일을 하는 **싼 대안**과 붙이면 배수는 훨씬 작아진다. 공개된 외부 테스트 둘을 보면,
Every 의 12개 지문 결함 검출에서 Jev 는 지문당 중앙값 0.35초 대 Claude Fable 5.1 의 8.83초로
약 25배 빠르고 비용은 대략 1/580 이었는데, **심어둔 결함 7개 중 6개를 잡았고 Fable 은 7개를
다 잡았다.**[^5] 영국 이벤트 사이트 NearHere 의 리스팅 판정에서는 Jev 96% 대
Gemini Flash-Lite 86% 로 정확도까지 Jev 가 이겼다(건당 58배 저렴).[^6]

즉 외부 숫자는 **작업에 따라 갈린다.** 한쪽에서는 정확도로도 이기고, 한쪽에서는 프런티어에
한 건 진다. 어느 쪽도 193배·445배의 재현은 아니다.

## 4. eval 사이트의 진짜 주장은 "제일 정확" 이 아니라 파레토다

TypeSafe 는 워크플로 eval 을 따로 사이트로 공개했다. 그 페이지에 적힌 주장 문구가 정확히
이렇다.

> "frontier: **nothing is both cheaper and more accurate**"
> — Workflow evals, TypeSafe AI[^3]

"제일 정확하다" 가 아니라 "나보다 싸면서 동시에 더 정확한 건 없다" 다. 이건 파레토 프런티어
주장이지 우열 주장이 아니다. 같은 페이지가 레퍼런스 정답의 정체도 밝혀 놨다.

> "the reference labels are generated via an average of the responses of GPT-6 Astra and
> Claude Fable 5.1, both at high thinking"[^3]

사람이 라벨링한 정답이 아니라 **다른 두 모델의 평균**이다. 그래서 여기 나오는 수치는
"정확도" 가 아니라 "그 레퍼런스와의 일치율" 로 읽어야 한다. 벤더도 각주에서 그 편향을
자인한다 — "biases answers towards OpenAI and Anthropic's models".[^1]

네 워크플로를 평균한 집계표는 그 사이트에서 **차트로만** 그려져 텍스트로 긁히지 않는다.
같은 표를 옮긴 복수의 2차 자료가 숫자를 일치시켜 보도하고 있어 그대로 적되, **이건 1차가
아니라 2차 인용**이다.[^4][^7]

| 모델 | 레퍼런스 일치율 | 건당 비용 | 지연 |
| --- | --- | --- | --- |
| GPT-5.6 Sol | 74.1% | $0.0836 | 23.3s |
| Claude Opus 5 | 73.1% | $0.1761 | 37.8s |
| GPT-5.6 Terra | 67.9% | $0.0304 | 10.1s |
| **Jev** | **67.8%** | **$0.0004** | **0.4s** |
| Claude Sonnet 5 | 67.8% | $0.1174 | 78.1s |

정확도 열에서 Jev 는 중위권과 동률이고 상위권에 진다. 차이는
$$74.1 - 67.8 = 6.3$$ 퍼센트포인트, 비용 차이는 Opus 5 기준
$$0.1761 \div 0.0004 \approx 440$$ 배다. **이 표를 근거로 "LLM 보다 낫다" 고 말하려면
6.3 포인트를 440배로 산 거라고 말해야 한다.** 그건 대부분의 자동화에서 좋은 거래지만,
"더 똑똑하다" 와는 다른 문장이다.

## 5. "환각을 못 한다" 의 0% 는 측정치가 아니다

이 슬로건이 오해를 제일 많이 만든다. 벤더 각주는 이렇게 적혀 있다.

> "Our number is not empirical. Schema matching is guaranteed, thus we can confidently add
> 0% into the plots."[^1]

즉 차트의 0% 는 **재서 나온 값이 아니라 구조상 그렇다고 단정한 값**이다. 그리고 그 보장의
범위는 **모양**이다. 스키마 밖 값을 못 뱉는 건 진짜지만, 스키마 **안의 틀린 값**을 자신 있게
고르는 건 그대로 가능하다. 청구 문의를 기술팀으로 보내는 라우팅 오류는 완벽하게 타입 안전한
채로 틀린다.

## 6. 정작 제일 중요한 주장은 아직 검증이 없다

Jev 의 진짜 상품은 속도가 아니라 **캘리브레이션**이다. 확신도 0.9 라고 답한 1,000건 중
900건쯤이 실제로 맞아야 임계값을 걸고 자동화할 수 있다. 훈련 방법 이름부터가
Reinforcement Learning for Calibrated Decisions 다.[^1]

그런데 **런치 포스트에는 캘리브레이션 수치가 한 줄도 없다.** 직접 전문을 받아 확인했다 —
신뢰도 곡선도, ECE 도, Brier 스코어도, RLCD 를 재현할 수 있는 수준의 기술 서술도 없다.
표준 지표이고 재기도 쉬운데 없다. 확신도를 팔면서 확신도 그림을 안 낸 셈이라,
그 값을 그대로 임계값에 꽂기 전에 **자기 데이터로 직접 재는 것 말고는 방법이 없다.**
그 재는 절차는 전에 따로 썼다 —
[모르겠다고 말할 수 있는 모델]({% post_url 2026-09-20-jev-confidence-gate-korean-guide %}).

## 7. 그래서 답

"요즘 LLM 보다 낫다" 는 카테고리를 건너뛴 문장이다. Jev 는 글을 못 쓰고, 이유를 설명하지
못하고, 스키마에 "모르겠음" 을 직접 넣어주지 않으면 기권도 못 한다. 대체재가 아니라
**if 문 자리에 꽂는 부품**이다. 그 자리에서는 실제로 더 나을 수 있고, 그 밖에서는 비교 대상이
아니다. 이 구도 자체는 앞선 글에 적었다 —
[Jev — 텍스트를 포기한 프런티어 모델]({% post_url 2026-09-19-jev-system-one-vs-llm-era %}).

그리고 판단 방법은 지난 글과 같다. 남의 배수를 인용하지 말고 **내 워크로드에서 내가 재는
것.** 내가 쓸 분모는 프런티어 추론 모델이 아니라 지금 그 자리에 실제로 돌고 있는 싼 모델일
가능성이 높고, 그 분모에서는 배수가 두 자리로 떨어진다.[^5][^6] 스킬 선택 사례에서도 결론은
같았다 —
[지연 로딩은 이미 하고 있다]({% post_url 2026-09-22-skill-listing-is-the-real-cost-jev-skill-suggestion %}).

## 근거의 한계

- 속도·가격·일치율 수치는 **거의 전부 벤더 1차 벤치마크**다. 워크플로도 레퍼런스 정답도
  TypeSafe 가 만들었고, 본인들이 "made by individuals on our model capabilities team, so some
  bias could exist" 라고 적었다.[^1]
- 4절의 집계표는 **1차 사이트에서 차트로만 제공돼 내가 텍스트로 확인하지 못했다.** 복수의
  2차 자료가 같은 숫자를 싣고 있어 옮겼을 뿐이고, 1차 확인이 된 수치가 아니다.
- 외부 테스트는 12지문·50건 규모의 단발이고, 상당수가 벤더가 앞당겨 준 얼리액세스로 돌렸다.
  중립 제3자의 대규모 독립 재현은 **찾지 못했다.**
- RLCD 는 이름만 공개돼 있어 알고리즘으로서 평가할 수 없다. 모델 구조·파라미터 수·가중치도
  공개되지 않았다.
- 가격 지속성도 미지수다. 벤더 본인 문장 — "We can't prove it isn't subsidized".[^1]

## References

[^1]: "Introducing System One Models and Jev", Diogo Almeida (founder, TypeSafe AI), 2026-09. <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
[^2]: Bruno Ferreira, "TypeSafe AI's Jev offers an alternative to LLMs that claims to be 193x faster and 445x cheaper", Tom's Hardware, 2026-09-21. <https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making>
[^3]: "Workflow evals", TypeSafe AI. <https://evals.typesafe.ai/>
[^4]: Laurie Voss, "TypeSafe Jev: Can Decision Models Replace LLM Judges?", Arize AI, 2026-09-18. <https://arize.com/blog/typesafe-jev-llm-judge/> — 2차. 같은 대시보드를 68% / $0.0004 / 0.4s 로 요약.
[^5]: "Jev: TypeSafe's Decision Model, Speed and Cost Explained", OrcaRouter, 2026-09-16. <https://www.orcarouter.ai/blog/jev-typesafe-system-one-what-we-know> — 2차. Every 의 12지문 테스트(0.35s 대 8.83s, 결함 6/7 대 7/7) 인용.
[^6]: NearHere 의 리스팅 판정 결과(Jev 96% 대 Gemini Flash-Lite 86%, 건당 58배 저렴)는 위 Arize 글에 보고된 수치다 — 2차. <https://arize.com/blog/typesafe-jev-llm-judge/>
[^7]: "The Jev model writes no text and TypeSafe won't say how", Botmonster Tech, 2026-09-20. <https://botmonster.com/ai/the-jev-model-writes-no-text-and-typesafe-wont-say-how/> — 2차. 4절 표와 같은 집계를 모델별로 게재.
