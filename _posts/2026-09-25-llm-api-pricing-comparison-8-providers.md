---
layout: post
title: "LLM API 가격 비교 2026년 9월 — OpenAI·Gemini·Claude·Grok·DeepSeek·Kimi·Qwen·MiMo"
date: 2026-09-25 02:26:14 +0900
categories: [AI]
tags: [LLM, API, 가격비교, OpenAI, Gemini, Claude, Grok, DeepSeek, Kimi, Qwen, MiMo]
---

LLM API 가격은 몇 달, 빠르면 몇 주 만에 바뀐다. 그래서 이 글의 모든 숫자는 **2026-09-25 에 각 사 공식 가격 페이지에서 직접 확인한 값**이다. 확인하지 못한 값은 추정으로 채우지 않고 비워 두었다.

- 단위: **USD / 100만 토큰**, 표준(실시간) 요금 기준
- 긴 컨텍스트 할증이 있는 모델은 **짧은 컨텍스트 구간** 가격
- 쓰기 전에 반드시 공식 페이지를 다시 확인할 것 (링크는 각 절과 References 에 있다)

## 한 장 요약 — 등급별 대표 모델

| 회사 | 모델 | 입력 | 캐시 입력 | 출력 |
|---|---|---|---|---|
| **OpenAI** | gpt-6-astra | 10.00 | 1.00 | 50.00 |
| | gpt-6-sol | 2.00 | 0.20 | 10.00 |
| | gpt-6-luna | 0.10 | 0.01 | 0.50 |
| **Google** | gemini-3.1-pro-preview (≤200K) | 2.00 | 0.20 | 12.00 |
| | gemini-3.8-flash ※ | 0.75 | 0.075 | 3.75 |
| | gemini-3.1-flash-lite | 0.25 | 0.025 | 1.50 |
| **Anthropic** | Claude Fable 5.1 | 10.00 | 0.25 | 50.00 |
| | Claude Opus 5.5 | 4.00 | 0.20 | 20.00 |
| | Claude Sonnet 5 | 2.00 | 0.20 | 10.00 |
| | Claude Haiku 4.5 | 1.00 | 0.10 | 5.00 |
| **xAI** | grok-4.7 (<200K) | 2.00 | 0.50 | 6.00 |
| | grok-4.3 (<200K) | 1.25 | 0.20 | 2.50 |
| **DeepSeek** | deepseek-v4-pro (피크) | 1.32 | 0.044 | 3.96 |
| | deepseek-flash (피크) | 0.30 | 0.006 | 1.20 |
| **Moonshot** | kimi-k3 | 3.00 | 0.30 | 15.00 |
| | kimi-k2.6 | 0.95 | 0.16 | 4.00 |
| **Alibaba (Qwen)** | qwen3.8-max | 2.00 | 입력의 10% | 6.00 |
| | qwen3.7-plus (≤256K) | 0.40 | 입력의 10% | 1.60 |
| | qwen3.7-flash (≤32K) | 0.03 | 입력의 10% | 0.13 |
| **Xiaomi** | MiMo-V2.6-Pro / Flash | 확인 불가 | — | — |

※ gemini-3.8-flash 는 **2026-12-31 까지의 가격**이다. 2027-01-01 부터 입력 1.50 / 캐시 0.15 / 출력 7.50 으로 두 배가 된다고 공식 페이지에 적혀 있다.

## 회사별 세부 — 표에 안 들어간 조건들

같은 "100만 토큰당 가격" 이라도 **할인·할증 규칙**이 회사마다 달라서, 실제 청구액은 이 조건에서 크게 갈린다.

### OpenAI

출처: [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)

- **긴 컨텍스트:** 모델마다 "short / long context" 가격이 따로 있다. gpt-6-astra 의 긴 컨텍스트 가격은 입력 20 / 출력 75 다.
- **Batch:** 표준 가격의 정확히 절반이다(astra 기준 입력 5 / 출력 25). Flex 가격도 Batch 와 같다.
- **Fast mode:** 표준의 2배. 페이지에는 2026-07-30 에 Priority processing 이 Fast mode 로 이름을 바꿨다고 적혀 있다.
- **데이터 레지던시:** 2026-03-05 이후 출시된 대상 모델은 지역 엔드포인트를 쓰면 10% 가 붙는다.
- **캐시 쓰기:** 별도 과금한다(astra 12.50).

### Google Gemini

출처: [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)

- **긴 컨텍스트:** 3.1 Pro 는 프롬프트가 200K 를 넘으면 입력 4.00 / 출력 18.00 이다.
- **Batch:** "50% cost reduction" 이라고 명시돼 있다. Priority 는 표준의 1.8배다.
- **캐시 저장료:** 캐시 입력 단가와 **별도로** 저장 시간당 요금이 붙는다(3.1 Pro 는 100만 토큰·시간당 4.50).
- **무료 티어:** Flash·Flash-Lite 계열에는 있지만 3.1 Pro 에는 없다. 무료 티어 콘텐츠는 제품 개선에 쓰인다고 명시돼 있다.
- **확인하지 못한 것:** 이번에 확인한 범위에서 Pro 급 최신 모델은 3.1 Pro Preview 뿐이었다. 페이지 뒷부분은 원문을 확인하지 못해서, 더 새 Pro 모델이 있는지는 공식 페이지에서 직접 보길 권한다.

### Anthropic Claude

출처: [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)

- **캐시:** 캐시 쓰기는 5분 TTL 이 입력의 1.25배, 1시간 TTL 이 2배다. 캐시 읽기는 기본 0.1배이고, Fable 5.1 은 0.025배, Opus 5.5 는 0.05배로 더 싸다.
- **Batch:** 입력·출력 모두 50% 할인이고, 캐시 배율과 함께 적용된다.
- **긴 컨텍스트:** 4.6 이후 모델은 100만 토큰 컨텍스트 전체가 표준 가격이다. 긴 컨텍스트 할증이 없다.
- **Sonnet 5:** 2/10 이 "now the standard price" 이고, 9월 1일로 예정됐던 3/15 인상은 "will not occur" 라고 명시돼 있다.
- **Fast mode:** Opus 5.5 는 입력 8 / 출력 40 이다.
- **US 전용 추론:** `inference_geo: "us"` 를 쓰면 1.1배.

### xAI Grok

출처: [xAI Models and Pricing](https://docs.x.ai/docs/models), [xAI Pricing](https://docs.x.ai/developers/pricing)

- **긴 컨텍스트:** 프롬프트가 200K 에 도달하면 **요청 전체**가 두 배 가격으로 청구된다(grok-4.7: 입력 4 / 출력 12).
- **Batch:** grok-4.3 과 grok-4.20 계열만 20% 할인되고, 4.7·4.6·4.5 는 할인이 없다.
- **Priority:** 2배. US 리전 엔드포인트: 1.1배.
- **캐시:** 캐시 입력 단가만 있고 캐시 쓰기 요금은 표시돼 있지 않다.

### DeepSeek

출처: [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)

- **시간대 요금:** *"Off-peak rates are half of the peak rates."*
  - 피크는 평일 UTC 01:00–04:00, 06:00–10:00 이다(한국 시간으로 10:00–13:00, 15:00–19:00).
  - 그 밖의 시간, 주말, 중국 공휴일은 오프피크다.
  - 즉 **한국 업무시간의 상당 부분이 피크**다. 야간 배치라면 표의 절반 가격이다.
- **캐시 히트가 매우 싸다:** deepseek-flash 는 0.006(오프피크 0.003)이다. 같은 프롬프트 앞부분을 반복하는 워크로드에 유리하다.
- **이전 모델명:** `deepseek-v4-flash` 는 여전히 호출되지만 V4.1-Flash 로 처리되고 Flash 가격이 청구된다.

### Moonshot (Kimi)

출처: [Kimi API Pricing](https://platform.kimi.ai/docs/pricing/chat) (예전 platform.moonshot.ai 주소는 여기로 리다이렉트된다)

- **캐시 쓰기:** kimi-k3 만 TTL 별로 과금한다(5분 3.00, 1시간 6.00).
- 가격은 세금 별도다.
- 코딩 특화 `kimi-k2.7-code`(입력 0.95 / 출력 4.00)와 고속 버전(1.90 / 8.00)이 따로 있다.

### Alibaba Cloud (Qwen)

출처: [Model Studio Model Pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) (싱가포르 리전 기준)

- **구간 요금:** 요청 하나의 입력 토큰 수로 구간이 정해지고, **요청 전체가 그 구간 가격**으로 청구된다.
  - qwen3.7-flash: ≤32K 에서 0.03 / 0.13, 256K–1M 에서 0.20 / 0.80.
- **리전별 가격 차이:** 같은 모델도 리전마다 가격이 다르다. 예를 들어 qwen3-max 는 일부 리전의 Global 범위 가격이 싱가포르보다 낮게 표시된다.
- **캐시·Batch:** 컨텍스트 캐시 히트는 입력의 10%, 명시적 캐시 생성은 125%, Batch 는 50% 다. **캐시 할인과 Batch 할인은 중복 적용되지 않는다.**
- **할인·무료:** qwen3.7-plus 는 한시적 20% 할인 중이다(표는 정가). 싱가포르에서는 모델별로 90일간 100만 토큰 무료 할당이 있다.

### Xiaomi (MiMo)

공식 API 플랫폼([platform.xiaomimimo.com](https://platform.xiaomimimo.com/))의 가격 페이지는 **자바스크립트로 값을 불러오는 구조**라, 이번 확인에서는 가격 숫자를 읽지 못했다. 사이트 코드에서 **MiMo-V2.6-Pro, MiMo-V2.6-Flash** 모델과 "cache hit / cache miss / output" 3단 가격 구조는 확인했지만, 값은 확인하지 못했다. 원칙대로 비워 둔다.

## 예시 계산 — 월 입력 1,000만 + 출력 200만 토큰

캐시·Batch 없이 표준 가격으로 계산하면 이렇다(짧은 컨텍스트 구간 기준).

| 모델 | 월 비용(USD) |
|---|---|
| gpt-6-astra, Claude Fable 5.1 | 200 |
| Claude Opus 5.5 | 80 |
| kimi-k3 | 60 |
| gemini-3.1-pro-preview | 44 |
| gpt-6-sol, Claude Sonnet 5 | 40 |
| grok-4.7, qwen3.8-max | 32 |
| deepseek-v4-pro (피크 / 오프피크) | 21.12 / 10.56 |
| Claude Haiku 4.5 | 20 |
| grok-4.3, kimi-k2.6 | 17.5 |
| gemini-3.8-flash (2026년 가격 / 2027년 가격) | 15 / 30 |
| qwen3.7-plus | 7.2 |
| gemini-3.1-flash-lite | 5.5 |
| deepseek-flash (피크 / 오프피크) | 5.4 / 2.7 |
| gpt-6-luna | 2 |
| qwen3.7-flash | 0.56 |

같은 등급 안에서도 서너 배, 최상위와 최하위 사이는 수백 배 차이가 난다.

## 가격표만 보고 고르면 틀리는 이유

1. **토큰은 회사마다 단위가 다르다.** 토크나이저가 달라서 같은 한국어 문장도 회사마다 토큰 수가 다르게 나온다. "100만 토큰당 가격" 을 그대로 비교하면 실제 비용과 어긋난다. 정확히 비교하려면 **자기 데이터로 각 API 의 usage 필드를 직접 찍어 봐야** 한다.
2. **추론(thinking) 토큰은 출력으로 과금된다.** 추론 모델은 답보다 긴 사고 과정을 출력 토큰으로 청구하는 경우가 많다. 출력 단가가 높은 모델일수록 이 영향이 크다.
3. **할인 규칙이 단가보다 클 수 있다.**
   - 캐시 히트는 입력의 1/10 ~ 1/50 수준이다.
   - Batch 는 대개 절반이다(Grok 일부는 20%, 일부는 할인 없음).
   - DeepSeek 은 시간대, Qwen 은 리전과 입력 구간에 따라 가격이 바뀐다.
   - 반복 프롬프트나 야간 배치 워크로드는 표의 단가와 전혀 다른 비용이 나온다.
4. **긴 컨텍스트 할증의 방식이 다르다.** 200K 를 넘으면 요청 **전체**가 비싸지는 곳(Grok, Gemini Pro)이 있고, 100만 토큰까지 할증이 없는 곳(Claude 4.6+)이 있다. RAG 로 긴 문서를 넣는 서비스라면 이게 단가보다 중요하다.
5. **프로모션은 끝난다.** Gemini 3.8 Flash 는 2027년에 두 배가 되고, Qwen 3.7 Plus 의 할인도 한시적이다. 장기 비용을 추정할 때는 정가로 계산한다.
6. **가격은 품질을 말하지 않는다.** 이 글은 가격만 비교했다. 벤더가 발표한 벤치마크는 벤더 주장이다. 자기 작업으로 평가셋을 만들어 **"같은 품질을 내는 가장 싼 모델"** 을 찾는 것이 결국 유일하게 정확한 비교다.

## References

모든 페이지는 2026-09-25 에 확인했다.

- OpenAI — [API Pricing](https://developers.openai.com/api/docs/pricing)
- Google — [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Anthropic — [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- xAI — [Models](https://docs.x.ai/docs/models) · [Pricing](https://docs.x.ai/developers/pricing)
- DeepSeek — [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)
- Moonshot AI — [Kimi API Pricing](https://platform.kimi.ai/docs/pricing/chat)
- Alibaba Cloud — [Model Studio Model Pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- Xiaomi — [MiMo API Open Platform](https://platform.xiaomimimo.com/) (가격 미확인)
