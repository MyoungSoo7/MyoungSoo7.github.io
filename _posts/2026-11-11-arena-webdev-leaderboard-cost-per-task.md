---
layout: post
title: "Arena 리더보드에 '작업당 비용'이 붙었다 — WebDev 순위와 Cost/Task 를 1차 데이터로 다시 읽기"
date: 2026-11-11 16:35:33 +0900
categories: [AI, LLM]
tags: [Arena, LMArena, WebDev, Cost per Task, 벤치마크, Claude, Gemini, GPT, AI 코딩]
---

"Arena.ai WebDev 리더보드에 Cost/Task(작업당 비용)가 추가됐다"는 요약이 텔레그램 채널에 돌았다. 요지는 맞다. 모델을 고를 때 점수만이 아니라 **한 작업을 끝내는 데 드는 돈**도 같이 봐야 한다는 것이다.

다만 그 요약에 실린 숫자를 1차 데이터와 맞춰 보니 맞지 않는 곳이 몇 군데 있었다. 이 글은 Arena 가 직접 공개한 두 가지만 근거로 다시 정리한다.

- 리더보드 페이지
- Hugging Face 공개 데이터셋 `lmarena-ai/leaderboard-dataset` (CC BY 4.0)

---

## 1. 무엇이 바뀌었나

WebDev 리더보드 페이지([arena.ai/leaderboard/code/webdev](https://arena.ai/leaderboard/code/webdev))의 표에는 현재 다음 열이 있다.

> Rank · Rank Spread · Model · Score · Votes · **Cost/Task (P50)** · Price $/M · Context

비용 열의 이름은 **P50**, 즉 작업당 비용의 *중앙값*이다. 같은 페이지 기준 집계는 2026-11-10, 투표 995,980건, 모델 157개다.

이 "작업당 비용" 개념은 사실 WebDev 에서 처음 나온 게 아니다. Arena 는 2026-08-14 블로그 글에서 **Agent Arena** 에 먼저 이 지표를 도입하면서 측정법을 설명했다 ([Arena, *Agent Leaderboard Improvements: Categories & Task Cost*](https://arena.ai/blog/agent-categories-and-cost)).

- **단위는 "작업(task)"이다.** 에이전트 세션을 작업 경계로 잘라서 작업 하나마다 비용을 계산한다. 블로그의 예로, 바이올린용 악보 편곡을 네 턴 주고받아 끝냈다면 그게 작업 하나다.
- **세션당 처음 3개 작업까지만 센다.** 세션이 길어지면 앞의 맥락이 매 턴 다시 처리돼서(context carry-over) 뒤쪽 작업일수록 비싸진다. 사용자가 오래 붙잡고 쓰는 *좋은* 모델일수록 세션이 길어지니 비용이 부풀려진다. 그 왜곡을 막는 장치다.
- **실제 사용자 세션에서 잰다.** 블로그 표현으로 "통제된 정적 벤치마크가 아니라 실제 작업을 하는 모델을 현장에서 잰 값"이다.
- 그 결과로 성능 대비 비용의 **파레토 프런티어** 뷰를 제공하고, p25·p50·p95 별로 볼 수 있다.

---

## 2. WebDev 점수 — 1차 데이터 기준

아래 값은 Hugging Face 데이터셋의 `webdev` 서브셋(`latest`, 게시일 2026-11-10, `category=overall`)에서 직접 읽었다. 리더보드 페이지의 표와도 일치한다.

| 순위 | 모델 | 점수 | 신뢰구간 | 투표 수 | 가격 $/M (입력/출력) |
| --- | --- | --- | --- | --- | --- |
| 1 | Claude Fable 5.2 (xHigh) | 1835.8 | ±22 | 994 | $8 / $40 |
| 2 | Claude Opus 5.5 (Max) | 1814.3 | ±12 | 4,187 | $4 / $20 |
| 3 | Claude Sonnet 5.5 (xHigh) | 1772.5 | ±10 | 5,818 | $2 / $10 |
| 4 | Gemini 4 Carbon (High) *Preliminary* | 1768.2 | ±15 | 2,120 | $2 / $10 |
| 5 | GPT-6 Astra (Max) | 1764.4 | ±9 | 8,425 | $10 / $50 |
| 6 | GPT-6.1 Sol (Max) | 1743.0 | ±10 | 5,539 | $2 / $10 |
| 7 | Claude Fable 5.1 (Max) | 1742.1 | ±8 | 9,756 | $10 / $50 |

신뢰구간과 가격은 리더보드 페이지 표에서 가져왔다.

### 돌던 요약과 다른 점

| 항목 | 돌던 요약 | 1차 데이터 |
| --- | --- | --- |
| Fable 5.2 | "AutoEval 단계, 정식 순위 미포함" | 정식 **1위**. 2026-11-09 리더보드 편입이 [변경 로그](https://arena.ai/company/leaderboard-changelog)에 기록돼 있다 |
| Opus 5.5 | 1813 | 1814.3 |
| Sonnet 5.5 (xHigh) | 1772 | 1772.5 |
| GPT-6 Astra | 1765 | 1764.4 |

점수 1점 차이는 반올림이나 갱신 시점 차이로 보인다. 결론을 바꾸지는 않는다. 다만 Fable 5.2 를 "순위 밖"이라고 한 것은 1차 데이터와 반대다.

### 점수를 읽는 법

- **"ELO"는 정확히는 Bradley–Terry 점수다.** 두 모델이 같은 프롬프트로 웹앱을 만들고 사람이 더 나은 쪽에 투표한다. 그 승패로 각 모델의 강도를 추정한다. Arena 는 이를 체스 Elo 와 비슷하다고 설명하지만 모델은 시간에 따라 변하지 않는다는 점이 다르다고 밝힌다 ([Arena, *WebDev Arena*, 2025](https://arena.ai/blog/webdev-arena)).
- **1위와 2위는 통계적으로 갈리지 않는다.** 페이지의 Rank Spread 가 두 모델 모두 "1–2"다. Fable 5.2 는 투표가 994건뿐이라 신뢰구간이 ±22 로 넓다. 3~5위(Sonnet 5.5·Gemini 4 Carbon·GPT-6 Astra)도 4점 안에 몰려 있고 구간이 겹친다.
- **Preliminary 는 아직 표본이 적다는 뜻이다.** Gemini 4 Carbon 은 이 표시가 붙어 있다.

---

## 3. 작업당 비용 — 검증 가능한 숫자만

### WebDev 의 Cost/Task 값은 확인하지 못했다

돌던 요약은 작업당 비용을 이렇게 적었다: Opus 5.5 $5.80, Gemini 4 Carbon $1.46, GPT-6.1 Sol $1.04. 이 값은 검증하지 못했다.

- WebDev 페이지에 열은 있지만, 텍스트로 받아 본 표에서는 값이 비어 있었다(차트·동적 렌더링으로 보인다).
- 공개 데이터셋의 `webdev` 서브셋에는 비용 열 자체가 없다.
- Arena 이용약관은 사이트 자동 수집을 허용하지 않는다고 알려져 있다. 그래서 페이지를 긁어 확인하는 방법은 쓰지 않았다.

그래서 이 글에서는 위 세 값을 **쓰지 않는다**.

### 대신: Agent Arena 의 작업당 비용(공개 데이터)

같은 지표가 Agent Arena 에는 공개 데이터로 나와 있다. 공개 데이터셋 `agent` 서브셋(게시일 2026-11-08)에 `cost_per_task_p50` 과 `output_tokens_per_task_p50` 열이 있다. 이 열은 한 사용자 요청으로 추가됐다는 Arena 팀의 답변이 데이터셋 토론에 남아 있다 ([HF discussion #7](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/discussions/7)).

**주의: 이건 WebDev 가 아니라 Agent Arena 의 수치다.** 점수 척도도 다르다. Agent 는 *net improvement* 점수라 0.x 단위로 나온다.

| Agent 순위 | 모델 | Agent 점수 | 작업당 비용 P50 | 작업당 출력 토큰 P50 |
| --- | --- | --- | --- | --- |
| 1 | Claude Opus 5.5 (Max) | 0.200 | **$6.31** | 120,135 |
| 2 | Gemini 4 Carbon (High) | 0.166 | **$1.54** | 50,900 |
| 3 | Claude Sonnet 5.5 (Max) | 0.160 | $3.42 | 149,861 |
| 4 | Claude Fable 5.1 (Max) | 0.143 | $6.87 | 56,226 |
| 5 | GPT-6 Astra (Max) | 0.142 | $7.04 | 43,780 |
| 6 | GPT-6.1 Sol (Max) | 0.125 | **$0.98** | 35,187 |
| 7 | GPT-6.1 Terra (Max) | 0.121 | $0.80 | 43,743 |
| 8 | Gemini 4 Argon (High) | 0.108 | $0.82 | 28,823 |

돌던 요약의 $5.80·$1.46·$1.04 는 이 Agent 값($6.31·$1.54·$0.98)과 크기가 비슷하다. **순서도 같다**(Opus ≫ Carbon > Sol). 그래서 "Opus 5.5 가 작업당 4~6배 비싸다"는 큰 그림은 두 출처가 같은 방향을 가리킨다. 정확한 값은 어느 리더보드·어느 시점이냐에 따라 다르다.

### 비싼 이유는 단가만이 아니다

이 표에서 내가 계산한 것 하나를 덧붙인다. 공식 지표가 아니라 *대략적인 산수*다.

- **단가 차이.** 출력 단가는 Opus 5.5 $20/M, Gemini 4 Carbon·GPT-6.1 Sol $10/M 이다. 2배 차이다.
- **토큰 차이.** 작업당 출력 토큰은 120k : 51k : 35k 다. 2.4~3.4배 차이다.
- **출력 토큰만으로 계산한 비용.** 출력 토큰 × 출력 단가로 따지면 Opus $2.40, Carbon $0.51, Sol $0.35 다. 셋 다 실제 작업당 비용 P50 의 **3분의 1 수준**이다.
- 나머지는 대부분 **입력(맥락) 토큰**으로 보인다. 에이전트는 매 턴 파일과 도구 결과를 다시 읽기 때문이다. 캐시 할인 여부는 공개 데이터로 알 수 없다.

모델 선택이 "단가가 싼 모델"의 문제만이 아니라는 뜻이다. **같은 일을 몇 토큰으로 끝내느냐**와 **맥락을 얼마나 끌고 다니느냐**가 함께 들어간다. 단가표만 보고 하는 비교가 빗나가는 이유이고, Arena 가 작업 단위로 재기로 한 이유이기도 하다.

### 위 8개만 놓고 본 성능-비용 경계

Arena 공식 파레토 뷰가 아니라 위 표 8개 모델만으로 그어 본 것이다.

- **경계 위에 있는 모델.** GPT-6.1 Terra($0.80) → GPT-6.1 Sol($0.98) → Gemini 4 Carbon($1.54) → Claude Opus 5.5($6.31) 순으로, 돈을 더 내면 점수도 오른다.
- **경계 밖에 있는 모델.** Fable 5.1 과 GPT-6 Astra 는 Opus 5.5 보다 비싼데 점수는 낮다. Sonnet 5.5 (Max) 는 Carbon 보다 비싼데 점수가 약간 낮다. 다만 신뢰구간이 겹치므로 단정할 수는 없다.

---

## 4. 그래서 어떻게 쓰나

1. **"가장 좋은 모델"보다 "이 일에 충분한 가장 싼 모델".** 1~5위는 통계적으로 촘촘하다. 반면 비용은 몇 배씩 벌어진다. 대량·반복 작업이면 경계 위의 싼 모델부터 시도하는 게 합리적이다.
2. **최상위 모델은 실패 비용이 큰 일에.** 한 번 틀리면 사람이 다시 손봐야 하는 일이라면, 작업당 $5 차이는 사람 시간에 비해 작을 수 있다. 이건 Arena 데이터가 아니라 각자의 계산이다.
3. **내 작업으로 다시 잰다.** Arena 의 작업은 Arena 사용자가 실제로 맡긴 일들의 분포다. 내 리포·내 프롬프트에서 작업당 토큰과 비용을 직접 재는 게 최종 판단 기준이다.
4. **표 위의 숫자는 시점값이다.** 점수는 매일 바뀐다. 이 글의 숫자도 2026-11-08(Agent)과 2026-11-10(WebDev) 게시분이다.

---

## 근거의 한계

- **WebDev Cost/Task 실값 미확인.** 페이지에 열이 있다는 것까지만 확인했다. 값은 텍스트로 확인되지 않아 쓰지 않았다(검증 불가 수치 배제 원칙). 위 비용 수치는 모두 **Agent Arena** 공개 데이터다.
- **Arena 는 중립 제3자지만 이용자 선호 기반이다.** 점수는 "어느 결과물이 더 좋아 보이나"에 대한 사람들의 투표다. 코드 정확성을 테스트로 채점한 값이 아니다. 투표자 분포와 프롬프트 분포가 내 업무와 같다는 보장도 없다.
- **작업당 비용은 Arena 환경의 측정값이다.** 공급자 가격, 캐시, 하네스, 세션 앞 3개 작업 제한이 모두 반영된 값이다. 내 환경에서 같은 값이 나온다는 보장은 없다.
- **이해충돌 고지.** 이 블로그는 Claude 기반 도구로 작성·운영된다. 수치는 해석 없이 1차 데이터 그대로 옮기려 했다.
- 돌던 요약의 원 출처(텔레그램 채널)는 인용하지 않았다. 1차 출처가 아니기 때문이다.

---

## References

1. Arena. *Code Arena — WebDev leaderboard.* 2026-11-10 집계. <https://arena.ai/leaderboard/code/webdev>
2. Arena. *Leaderboard Changelog.* (2026-11-09 Claude Fable 5.2 (xHigh) WebDev 편입) <https://arena.ai/company/leaderboard-changelog>
3. Arena. *Agent Leaderboard Improvements: Categories & Task Cost.* 2026-08-14 (2026-08-19 갱신). <https://arena.ai/blog/agent-categories-and-cost>
4. Arena. *WebDev Arena: A Live LLM Leaderboard for Web App Development.* 2025-03-10. <https://arena.ai/blog/webdev-arena>
5. lmarena-ai. *leaderboard-dataset* (Hugging Face, CC BY 4.0) — `webdev` 서브셋(2026-11-10), `agent` 서브셋(2026-11-08). <https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset>
6. lmarena-ai/leaderboard-dataset Discussion #7 — `cost_per_task_p50`, `output_tokens_per_task_p50` 열 추가. <https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/discussions/7>
