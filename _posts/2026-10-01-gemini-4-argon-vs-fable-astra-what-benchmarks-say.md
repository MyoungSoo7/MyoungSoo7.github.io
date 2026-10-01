---
layout: post
title: "제미나이 4 아르곤이 Fable·Astra 보다 좋다? — 누가 쟀는지부터 갈라 보기"
date: 2026-10-01 21:02:15 +0900
categories: [ai, llm]
tags: [gemini, gemini-4-argon, gpt-6-astra, claude-fable, claude-opus, benchmark]
---

> **이해충돌 고지.** 이 글은 Anthropic 의 Claude(Opus 5.5)가 조사·초안을 쓰고 사람이 검토했다. 비교 대상에 Anthropic 모델(Fable 5.1, Opus 5.5)이 들어 있다. 그래서 수치는 전부 원문 링크를 달았고, 해석보다 "누가 잰 숫자인지"를 먼저 밝히는 방식으로 썼다.

9월 30일 구글이 **Gemini 4 Argon** 을 발표했다. 그 뒤로 "아르곤이 Fable·GPT Astra 보다 성능이 좋다"는 말이 돈다. 결론부터 말하면 **반은 맞고 반은 틀리다.** 어느 벤치마크를, 누가, 어떤 모델과 비교했는지에 따라 답이 갈린다.

## 1. 세 모델의 정체

| 모델 | 회사 | 공개일 | 지금 쓸 수 있나 | API 가격 (입력/출력, 100만 토큰당) |
| --- | --- | --- | --- | --- |
| **Gemini 4 Argon** | Google | 2026-09-30 | **아니오.** 사이버 방어자 대상 Fairwind 프로그램부터 단계적 출시 | 도입가 $2 / $10 → 이후 $4 / $20 |
| **GPT-6 Astra** | OpenAI | 2026-09-03 | 예. ChatGPT·API(`gpt-6-astra`) | $10 / $50 부터 |
| **Claude Fable 5.1** | Anthropic | 2026-09-01 | 예. API(`claude-fable-5-1`) | $10 / $50 |
| (참고) **Claude Opus 5.5** | Anthropic | 2026-09-22 | 예. API(`claude-opus-5-5`) | $4 / $20 |

출처: [Google 블로그](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/), [OpenAI Astra 발표](https://openai.com/index/gpt-6-astra/)·[가격](https://openai.com/index/gpt-6-astra-next-generation-work/), [Anthropic Fable 5.1 문서](https://platform.claude.com/docs/en/models/fable-5-1/overview), [Opus 5.5 문서](https://platform.claude.com/docs/en/models/opus-5-5/overview).

먼저 짚을 사실이 하나 있다. **아르곤은 아직 일반에 풀리지 않았다.** 구글은 미국 정부의 자발적 사전 접근 절차에 참여 중이며 "가능한 한 빨리" 개발자·기업·소비자에게 넓히겠다고만 밝혔다 ([Google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/)). 아래의 성능 비교는 대부분 **우리가 직접 돌려 볼 수 없는 모델**에 대한 것이다.

## 2. 구글이 고른 비교 상대는 Fable 이 아니었다

"아르곤 > Fable" 이라는 말의 출처를 따라가 보면 묘한 점이 있다. **구글의 발표 비교표에 Fable 5.1 은 거의 나오지 않는다.** 구글이 맞붙인 상대는 **GPT-6 Astra 와 Claude Opus 5.5** 다 ([VentureBeat](https://venturebeat.com/technology/google-unveils-gemini-4-argon-retaking-benchmark-lead-over-openai-and-anthropic-but-in-limited-release); [Reuters via CNBC-TV18](https://www.cnbctv18.com/technology/gemini-argon-google-announces-flagship-ai-model-after-months-of-delays-20002577.htm)). Fable 5.1 은 프롬프트 인젝션 표에만 등장한다.

Opus 5.5 는 Anthropic 스스로 "대부분의 작업에서 Fable 5.1 수준"이라고 소개한 모델이다 ([Anthropic](https://www.anthropic.com/claude-opus-5-5)). 그러니 "Opus 5.5 를 이겼다 ≈ Fable 을 이겼다"고 읽고 싶어진다. 하지만 이것은 **벤더 주장 두 개를 이어 붙인 추론**이다. 그 자체로 측정된 결과는 아니다.

## 3. 구글 자체 수치 — 18개 중 12개 1위, 그러나 "완승"은 아님

> ⚠️ 아래 표는 **벤더(구글)가 직접 잰 수치**다. 하네스·설정이 공개되지 않아 재현 가능 여부는 확인되지 않았다. 경쟁 모델 수치는 구글 비교표를 본 VentureBeat 보도에서 옮겼다. 구글 블로그 본문 텍스트로 확인되는 수치는 DeepSWE 77.9%·AutomationBench 51.3%·LVBench 91.7%·CWE-bench 68% 이다.

VentureBeat 의 집계로는 구글이 공개한 벤치마크 18개 중 **아르곤 단독 1위 12개, 공동 1위 1개, Astra 단독 1위 3개, Opus 5.5 단독 1위 2개**다 ([VentureBeat](https://venturebeat.com/technology/google-unveils-gemini-4-argon-retaking-benchmark-lead-over-openai-and-anthropic-but-in-limited-release)).

| 벤치마크 (구글 표) | Argon | GPT-6 Astra | Opus 5.5 | 앞선 쪽 |
| --- | --- | --- | --- | --- |
| DeepSWE v1.1 (장기 SW 엔지니어링) | **77.9%** | 74.1% | 74.2% | Argon |
| AutomationBench (업무 자동화) | **51.3%** | 41.4% | 42.5% | Argon |
| Harvey Legal Agent (법률) | **19.6%** | 5.4% | 3.8% | Argon |
| Vals Finance Agent v2 (금융) | **65.4%** | 53.5% | 58.6% | Argon |
| LVBench (장시간 영상) | **91.7%** | 87.5% | 83.7% | Argon |
| CWE-bench v1 (취약점 수정) | 68% | 68% | 67% | 동률 |
| FrontierSWE v2 | 55.0% | **65.5%** | — | Astra |
| Terminal-Bench Science 0.1 | 57.6% | **68.1%** | — | Astra |
| Terminal-bench 4.0 | 57.4% | — | **66.4%** | Opus 5.5 |
| PostTrainBench | 45.3% | — | **49.3%** | Opus 5.5 |

로이터도 같은 점을 짚었다. 아르곤은 여러 벤치마크에서 앞섰지만 **구글이 넣은 코딩 벤치마크 4개 중 2개에서는 뒤졌다** ([Reuters via CNBC-TV18](https://www.cnbctv18.com/technology/gemini-argon-google-announces-flagship-ai-model-after-months-of-delays-20002577.htm)). 구글의 강점은 **법률·금융·업무 자동화·장문맥·영상**이다. 반대로 **터미널 에이전트·과학 터미널 작업**은 Astra 와 Opus 쪽이 강하다.

## 4. 제3자 측정 — 두 독립 평가기관의 답이 다르다

벤더 표보다 무게를 둬야 할 건 **중립 제3자 측정**이다. 이번에는 두 곳이 발표 당일 수치를 냈다. 그런데 **둘의 결론이 다르다.**

### Artificial Analysis — "Astra 와 동률, Opus 5.5 보다 아래"

Artificial Analysis 는 10개 평가를 묶은 Intelligence Index v4.3 을 쓴다. 이 지수에서 아르곤(high)은 **53점으로 GPT-6 Astra(max) 53점과 같았다** ([Artificial Analysis](https://www.linkedin.com/pulse/googles-new-gemini-4-argon-equals-gpt-6-astra-artificial-ijumc)). 같은 기관은 현재 이 지수 1위를 **Claude Opus 5.5(58점)** 로 표시한다 ([AA Intelligence Index](https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index)). 이 지수만 보면 "아르곤이 Astra 보다 좋다"는 말은 성립하지 않는다.

같은 측정의 세부:

- **환각률**은 아르곤이 압도적으로 낮다. AA-Omniscience 환각률 **15% vs Astra 51%** 다. 모르면 모른다고 답하는 쪽이다. 다만 정답률 자체는 **50% vs Astra 63%** 로 낮아서 종합 점수(42 vs 43)는 비슷하다.
- **AutomationBench-AA 1위(78%)**. 업무 자동화 강점이 독립 측정에서도 재현됐다.
- **Terminal-Bench 4.0 은 57%** 로 Sonnet 5.5(64%)·Opus 5.5(60%)·Astra(59%)보다 낮다. 구글 표의 약점과 방향이 같다.
- **과제당 비용**은 도입가 기준 **$1.99** 로 Astra($3.26)의 60% 다. 하지만 이건 **토큰 단가가 싸서**지 토큰을 덜 써서가 아니다. 과제당 출력 토큰은 아르곤이 약 6.2만, Astra 가 약 2.7만이다. 정가($4/$20)로 돌아가면 **$3.98 로 Astra 보다 비싸진다.**

### Vals AI — "Fable 5.1 보다 근소하게 위"

Vals Index 는 금융·코딩·법률 과제를 미국 GDP 비중으로 가중한 지수다. 여기서는 아르곤이 **68.90% (±0.97)** 로 1위다 ([Vals: Gemini 4 Argon](https://www.vals.ai/models/google_gemini-4-argon)). 같은 지수에서 Fable 5.1 은 **67.87% (±1.10)** 다 ([Vals: Claude Fable 5.1](https://www.vals.ai/models/anthropic_claude-fable-5-1)). 사용자 질문의 "Fable 보다 좋다"에 가장 직접 답하는 독립 수치가 이것이다.

다만 차이는 **약 1%p** 이고, 두 오차범위(68.90±0.97 → 67.93~69.87, 67.87±1.10 → 66.77~68.97)가 **겹친다.** "앞선다"보다는 **"통계적으로 거의 같은 수준"** 이라고 읽는 게 정직하다. 이 지수는 가중치의 절반 이상이 금융이다. 아르곤이 가장 강한 영역이 크게 반영되는 구조라는 점도 감안해야 한다.

### 같은 벤치마크, 다른 숫자

Terminal-Bench 4.0 하나만 놓고 봐도 측정 주체마다 숫자가 다르다.

| 측정 주체 | Argon | Opus 5.5 | Astra | Fable 5.1 |
| --- | --- | --- | --- | --- |
| 구글 (자체 표, VentureBeat 보도) | 57.4% | 66.4% | — | — |
| Artificial Analysis | 57% | 60% | 59% | — |
| Vals AI | 57.58% | — | — | — |
| Anthropic (자체, 9/1) | — | — | — | 55.8% |

아르곤 쪽은 세 곳에서 57% 안팎으로 거의 같다. 그런데 Opus 5.5 는 구글 표(66.4%)와 Artificial Analysis(60%)가 6%p 넘게 차이 난다. **하네스·노력 수준·재시도 설정이 다르면 같은 이름의 벤치마크도 다른 시험이 된다.** 서로 다른 출처의 숫자를 한 표에 섞어 순위를 매기면 안 되는 이유다. Fable 5.1 의 55.8% 는 Anthropic 이 안전장치(세이프가드)를 켠 상태로 잰 값이고, 개입된 과제는 0점 처리됐다고 스스로 밝혔다 ([Anthropic](https://www.anthropic.com/claude-fable-and-mythos-5-1)).

## 5. 그래서 "아르곤이 더 좋다"는 맞는 말인가

| 주장 | 근거 수준 | 판정 |
| --- | --- | --- |
| 아르곤이 구글 표 18개 중 가장 많이 1위 | 벤더 자체 측정 | **벤더 주장으로는 맞음** (재현 미확인) |
| 아르곤이 Astra 보다 똑똑하다 | 제3자(AA) | **아님 — 동률(53 vs 53)** |
| 아르곤이 Fable 5.1 보다 좋다 | 제3자(Vals) | **근소 우위, 오차범위 겹침** |
| 아르곤이 Opus 5.5 보다 좋다 | 제3자(AA) | **AA 종합 기준 아님 (53 vs 58)** |
| 아르곤이 환각이 적다 | 제3자(AA) | **맞음 (15% vs Astra 51%)** |
| 아르곤이 싸다 | 공식 가격 + AA | **도입가 동안만.** 정가에선 과제당 Astra 보다 비쌈 |
| 업무 자동화·법률·금융에 강하다 | 벤더 + 제3자 | **맞음** (AutomationBench-AA 1위, Finance Agent v2 1위) |
| 터미널 코딩 에이전트에 강하다 | 벤더 + 제3자 | **아님** (세 곳 모두 57% 안팎, 경쟁작보다 낮음) |

한 줄로 줄이면: **"아르곤이 전부 앞선다"는 틀렸다. "경쟁 모델들과 같은 최상위 그룹에 들어왔다. 강점은 업무 자동화·법률·금융·저환각이고 약점은 터미널 코딩이다"가 증거에 맞는 문장이다.** 구글 대변인도 "Astra·Opus 에 *필적*한다(comparable)"고 표현했다 ([Reuters via CNBC-TV18](https://www.cnbctv18.com/technology/gemini-argon-google-announces-flagship-ai-model-after-months-of-delays-20002577.htm)). 언론 제목의 "압도"보다 회사 대변인의 말이 더 조심스럽다.

## 6. 실무자는 어떻게 고르나

1. **아직 못 쓴다.** 일반 공개 전이다. 지금 계약·설계를 바꿀 근거로 쓰기엔 이르다.
2. **작업별로 고른다.** 계약서·재무 리서치·SaaS 업무 자동화가 주력이면 아르곤 공개 후 우선 시험할 가치가 있다. 터미널에서 오래 도는 코딩 에이전트가 주력이면 현재 증거로는 Opus 5.5·Astra·Sonnet 5.5 쪽이 앞선다.
3. **"싸다"는 날짜를 확인한다.** 50% 도입 할인의 종료일을 구글이 아직 밝히지 않았다 ([AA](https://www.linkedin.com/pulse/googles-new-gemini-4-argon-equals-gpt-6-astra-artificial-ijumc)). 할인이 끝나면 과제당 비용이 두 배가 된다. 출력 토큰을 많이 쓰는 모델이라 토큰 단가보다 **과제당 비용**으로 비교해야 한다.
4. **결국 자기 과제로 잰다.** 같은 Terminal-Bench 에서도 측정 주체마다 6%p씩 갈렸다. 공개 벤치마크는 후보를 3개로 줄이는 데까지 쓰고, 최종 선택은 **우리 데이터·우리 하네스로 돌린 20~50건 평가셋**으로 한다.

## 이 글의 한계

- **중립 헤드투헤드는 두 곳(Artificial Analysis, Vals AI)뿐**이다. 발표 하루 만의 측정이고, 그 둘의 결론도 다르다.
- 구글 비교표의 경쟁 모델 수치는 **표 이미지를 본 VentureBeat 보도**를 통해 옮겼다. 구글 블로그 본문 텍스트에서 직접 확인한 수치는 아르곤 자신의 4개뿐이다.
- Artificial Analysis 의 **v4.3 지수에서 Fable 5.1 점수**는 공개 페이지에서 확인하지 못했다. Fable 5.1 모델 페이지의 66점은 **구버전 v4.1.1** 기준이라 아르곤의 53점(v4.3)과 직접 비교할 수 없다.
- 아르곤이 일반 공개되면 설정·안전장치가 달라질 수 있다. 그러면 수치도 바뀔 수 있다.
- 필자는 비교 대상 회사(Anthropic)의 모델이다. 위 고지를 참고해 원문 링크로 직접 확인하길 권한다.

이전 글: [Claude Opus 5.5 vs Fable 5.1 — 벤치마크·비용·안전장치]({% post_url 2026-09-23-claude-opus-5-5-vs-fable-5-1-benchmarks-cost-safeguards %}), [GPT-6 Astra Codex 컴퓨터 사용]({% post_url 2026-09-17-gpt-6-astra-codex-computer-use %}), [Fable 5 벤치마크의 사각지대와 하네스]({% post_url 2026-07-11-fable5-benchmark-blind-spots-and-harness %}).

## References

**1차·공식 (벤더)**
1. Kavukcuoglu, K. (Google), "[Gemini 4 Argon: our next era of frontier intelligence](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/)," 2026-09-30.
2. OpenAI, "[GPT-6 Astra: A new generation of intelligence](https://openai.com/index/gpt-6-astra/)"; "[GPT-6 Astra: The next generation in intelligence for work](https://openai.com/index/gpt-6-astra-next-generation-work/)"; "[GPT-6 Astra System Card](https://deploymentsafety.openai.com/gpt-6-astra/model-safety)," 2026-09-03.
3. Anthropic, "[Introducing Claude Fable 5.1 and Claude Mythos 5.1](https://www.anthropic.com/claude-fable-and-mythos-5-1)"; [Claude Fable 5.1 model docs](https://platform.claude.com/docs/en/models/fable-5-1/overview), 2026-09-01.
4. Anthropic, "[Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)"; [Claude Opus 5.5 model docs](https://platform.claude.com/docs/en/models/opus-5-5/overview), 2026-09-22.

**중립 제3자 측정**
5. Artificial Analysis, "[Google's new Gemini 4 Argon equals GPT-6 Astra on the Artificial Analysis Intelligence Index](https://www.linkedin.com/pulse/googles-new-gemini-4-argon-equals-gpt-6-astra-artificial-ijumc)," 2026-09-30; [Intelligence Index v4.3](https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index); [v4.3 방법론](https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v4-3).
6. Vals AI, [Gemini 4 Argon](https://www.vals.ai/models/google_gemini-4-argon); [Claude Fable 5.1](https://www.vals.ai/models/anthropic_claude-fable-5-1); [Vals Index 방법론](https://www.vals.ai/benchmarks/vals_index).

**보도**
7. Franzen, C., "[Google unveils Gemini 4 Argon, retaking benchmark lead…](https://venturebeat.com/technology/google-unveils-gemini-4-argon-retaking-benchmark-lead-over-openai-and-anthropic-but-in-limited-release)," VentureBeat, 2026-09-30.
8. Reuters, "[Gemini Argon: Google announces flagship AI model after months of delays](https://www.cnbctv18.com/technology/gemini-argon-google-announces-flagship-ai-model-after-months-of-delays-20002577.htm)" (CNBC-TV18 전재), 2026-10-01.
