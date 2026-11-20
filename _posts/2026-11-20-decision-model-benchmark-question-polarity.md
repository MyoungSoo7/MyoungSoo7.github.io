---
layout: post
title: "Decision Model 8종 비교 — 승자보다 '질문을 뒤집으면 뒤집히는 판정'이 핵심이다"
date: 2026-11-20 17:54:20 +0900
categories: [ai]
tags: [jev, typesafe, decision-models, llm-as-a-judge, evaluation, calibration, arize]
---

Arize Korea가 「Decision Model 8종 성능 비교: Jev, Kev, Liquid d1 중 무엇을 선택해야 할까?」를
올렸다([한국어판](https://www.arizekorea.com/insights/post/decision-model-benchmark-jev-kev-liquid-d1-2LXJin4juMAAhxr)).
이 글은 Arize 본사 블로그에 Jim Bennett이 2026-10-07에 쓴
[영문 원문](https://arize.com/blog/decision-model-benchmark/)을 옮긴 것이다. 아래 수치는 모두 영문 원문과
대조했다.

결론부터 적는다. 이 벤치마크에서 건질 것은 "어느 모델이 이겼나"가 아니다. **같은 뜻의 질문을 긍정형에서
부정형으로 바꾸기만 했는데, 8개 중 5개 모델의 판정 품질이 무너졌다**는 관찰이다. 그리고 이 측정은
Jev를 자사 제품에 내장한 벤더가 직접 돌린 것이다. 그 전제를 깔고 읽어야 한다.

## Decision Model이 뭔가

TypeSafe는 2026-09-15 Jev를 내놓으면서 이런 모델을 "System One Model"이라고 불렀다
([TypeSafe 발표](https://typesafe.ai/blog/introducing-system-one-models-and-jev)). 텍스트를 생성하지 않는다.
상태(state)와 질문, 그리고 미리 정한 답의 공간을 받아서 **타입이 정해진 답과 확률**을 돌려준다
([TypeSafe 문서 — System One](https://docs.typesafe.ai/concepts/system-one)). 호출은
`POST /v1/systemone` 하나이고, 가격은 입력 100만 토큰당 $0.042, 출력은 무료다
([TypeSafe 문서 — Models](https://docs.typesafe.ai/models)).

출력 토큰이 없으니 싸고 빠르다. Arize는 쓸모를 두 가지로 꼽는다
([원문](https://arize.com/blog/decision-model-benchmark/)).

- **에이전트 안의 단일 결정.** 어떤 도구나 스킬을 부를지, 멈출지 계속할지.
- **트레이스를 채점하는 judge.** LLM-as-a-Judge 자리를 대신한다.

원문에 따르면 Jev가 나오고 몇 주 만에 OpenAI·Liquid AI·Cloudflare·AWS·PostHog 등 약 10곳이 같은
방식의 모델을 냈다. 8개 중 7개가 Jev의 `/v1/systemone` 요청 형식을 받는다. LLM 업계에서 OpenAI API
형식이 사실상 표준이 된 것과 같은 흐름이다. 예외는 OpenAI Decisions 하나다.

## 무엇을 어떻게 쟀나

| 모델 | 만든 곳 | 형태 | 실행 위치 |
| --- | --- | --- | --- |
| Jev 1.13 | TypeSafe | 비공개, 호스팅 API | TypeSafe API |
| Liquid d1 | Liquid AI | 비공개 | Liquid API |
| OpenAI Decisions (gpt-6-luna) | OpenAI | 비공개, 공개 베타 | OpenAI API |
| Clef 27B | Cloudflare | 27B 오픈 웨이트, Apache 2.0 | Workers AI |
| Kev 9B | Jared Palmer | Jev를 재현한 오픈 모델 | 로컬 |
| Jeeves 9B | PostHog | 결정 전에 추론하는 오픈 모델 | 로컬 |
| Strands Decider 2B | AWS | 학습 레시피 공개 | 로컬 |
| Laya multilingual | Convai Innovations | 322M BERT 계열 인코더 | 로컬 |

로컬 모델은 MacBook Pro(M4 Max, 36GB) 한 대에서 돌렸다. 과제는 셋이다.

1. **환각 탐지.** RAGTruth 2,675행.
2. **평가기(judge) 과제.** Phoenix 평가기 스위트 13개, 레이블 달린 케이스 655건.
3. **에이전트 라우팅.** 도구·스킬 선택 52건.

방식은 토너먼트다. 정확도·지연 시간·1,000건당 비용 중 두 지표를 이기면 다음 판에 오른다.
**정확도는 95% 신뢰구간이 겹치지 않을 때만 승리로 쳤다.** 모델마다 예/아니오 임계값을 데이터 절반으로
맞추고, 나머지 절반으로 채점했다.

## 결과 요약 — 상위권은 정확도로 갈리지 않는다

원문의 전체 결과표다(균형 정확도, 홀드아웃 절반 기준).

| 모델 | 환각 (RAGTruth) | 평가기 (Phoenix) | 라우팅 | 보정 오차 | 지연 p50 | 1,000건당 비용 |
| --- | --- | --- | --- | --- | --- | --- |
| Jev 1.13 | 85.5% | 91.1% | 49/52 | 0.023 | 0.08초 | $0.045 |
| Clef 27B | 85.2% | 91.5% | 50/52 | 0.062 | 0.50초 | $0.223 |
| Liquid d1 | 84.8% | 87.6% | 48/52 | 0.051 | 0.20초 | $0.034 |
| OpenAI Decisions | 81.5% | 90.0% | 48/52 | 0.042 | 0.16초 | $0.090 |
| Jeeves 9B | 80.3% | 87.1% | 48/52 | 0.043 | 16.8초 | 로컬 |
| Kev 9B | 76.8% | 88.7% | 48/52 | 0.055 | 1.03초 | 로컬 |
| Strands Decider 2B | 69.0% | 76.7% | 45/52 | 0.065 | 0.34초 | 로컬 |
| Laya multilingual | 59.8% | 57.3% | 40/52 | 0.330 | 0.04초 | 로컬 |

로컬 지연은 노트북 한 대에서 잰 값이라 클라우드 수치와 직접 비교할 수 없다(원문 단서).

결승은 **무승부**로 끝났다. 라우팅에서 Jev 49건, Kev 48건이었다. 52건짜리 세트에서 한 문제는 약
2%p라서 차이로 볼 수 없다. 그래서 Arize의 권고는 정확도가 아니라 배포 방식이 기준이다. **API로 부를
거면 Jev, 직접 호스팅할 거면 Kev**다. 1라운드에서 떨어진 Clef 27B도 정확도는 Jev와 같은 수준이었다.
Liquid보다 느리고 비싸서 탈락했을 뿐이다.

LLM judge와 비교한 대목도 있다. Arize의 이전 벤치마크에서 Opus 5는 RAGTruth 균형 정확도 86.6%,
판정 1,000건당 $14.30이었다([Laurie Voss, Arize](https://arize.com/blog/jev-as-a-judge/)).
Jev·Liquid·Clef 27B는 그 오차 범위 안에 들었다. 비용은 Opus 5 대비 Jev 0.3%, Liquid 0.2%,
Clef 27B 1.6%다.

## 진짜 발견 — 질문의 극성을 뒤집으면

본 실험 전에 Arize는 환각 질문의 문구를 두 가지로 돌려 봤다.

- **A:** "모든 주장이 컨텍스트로 뒷받침되는가?"
- **B:** "뒷받침되지 않는 주장이 하나라도 있는가?"

뜻은 같고 극성만 반대다. 질문을 이해하는 모델이라면 B에서 확률을 뒤집어 읽었을 때 A와 같은 판별력이
나와야 한다. 같은 테스트 1,338행에서 잰 ROC AUC다. 0.5는 동전 던지기이고, 0.5 밑은 반대 질문에 답하고
있다는 뜻이다.

| 모델 | A: 모두 뒷받침되나 | B: 미지지 주장이 있나 |
| --- | --- | --- |
| Jev 1.13 | 0.93 | 0.93 |
| Clef 27B | 0.92 | 0.91 |
| OpenAI Decisions | 0.90 | 0.89 |
| Kev 9B | 0.85 | **0.54** |
| Laya multilingual | 0.64 | **0.36** |
| Strands Decider 2B | 0.75 | **0.26** |
| Jeeves 9B | 0.85 | **0.25** |
| Liquid d1 | 0.92 | **0.17** |

버틴 모델은 Jev·Clef 27B·OpenAI 셋뿐이다. Kev는 동전 던지기 수준으로 떨어졌다. Liquid d1·Jeeves·Strands는
B를 받고도 A에 답하듯 **확신을 갖고 반대로** 판정했다. Liquid d1은 0.92에서 0.17이 됐다. 토너먼트에서
1라운드에 떨어진 OpenAI가 여기서는 상위 셋에 든다.

Laya는 일상적인 문구에서도 같은 약점을 보였다. Phoenix에서 "유해한 내용이 **없는가**?"로 물으면 0.11,
"유해한 내용이 **있는가**?"로 물으면 0.87이었다. 원문에 따르면 Laya의 모델 카드에도 답이 질문보다 선택지
레이블을 따라갈 수 있다는 경고가 적혀 있다.

### 왜 이게 위험한가

정확도 표는 "판정 모델 교체"를 부품 교체처럼 보이게 만든다. 하지만 이 결과대로라면 **점수는 모델 혼자
내는 것이 아니라 모델과 질문 문구의 조합이 낸다.** 질문 문구는 그대로 두고 judge만 Liquid d1로 바꾸면, 조용히
평가 결과가 거꾸로 나올 수 있다. 대시보드에는 여전히 그럴듯한 숫자가 뜨니 사고가 드러나지 않는다.

Arize의 처방은 싸다. **새 모델을 들이기 전에 같은 질문을 긍정형·부정형 두 가지로 돌려 본다.**
레이블이 있는 셋만 있으면 된다. 대략 이런 모양이다.

```python
from sklearn.metrics import roc_auc_score

# y: 1 = 모든 주장이 뒷받침됨(정상), 0 = 환각 있음
# p_pos: "모든 주장이 뒷받침되는가?" 에 대한 yes 확률
# p_neg: "뒷받침되지 않는 주장이 있는가?" 에 대한 yes 확률
auc_pos = roc_auc_score(y, p_pos)
auc_neg = roc_auc_score(y, [1 - p for p in p_neg])  # 극성을 되돌려 같은 축에서 비교

if abs(auc_pos - auc_neg) > 0.05 or min(auc_pos, auc_neg) < 0.6:
    print("문구 민감 — 이 모델·질문 조합을 judge 로 쓰지 말 것")
```

임계값 0.05·0.6은 예시일 뿐이다. 원문이 정한 기준이 아니다. 중요한 건 **두 문구의 AUC가 같은 값 근처에
모이는지**다.

## 이 벤치마크를 읽을 때의 한계

출처 등급을 섞지 않기 위해 따로 적는다.

- **벤더 1차 벤치마크다.** Arize는 AX에 "Jev as a judge"를 내장해 팔고 있다(원문 마지막 절). 하네스
  코드와 일부 데이터 출처(Arize 벤치마크 코드, Phoenix 스위트)도 Arize 것이다. 결과가 Jev에 불리할
  유인은 적다. 원문 수치를 재현해 본 중립 제3자 결과는 이 글을 쓰는 시점에 찾지 못했다.
- **OpenAI 수치는 Arize가 정한 프롬프트 배치에 달려 있다.** OpenAI Decisions API만 입력 형식이 달라서
  Arize가 필드를 텍스트 섹션으로 펴서 넣었다. 원문 스스로 "다른 배치면 점수가 달라질 수 있다"고 적었다.
- **라우팅 52건은 작다.** 1건이 약 2%p라 결승 무승부도 "차이를 못 쟀다"는 뜻이지 "같다"는 뜻이 아니다.
- **극성 테스트는 RAGTruth 한 과제의 두 문구다.** 다른 과제·언어(예: 한국어 질문)에서도 같은
  모델이 같은 식으로 무너진다는 증거는 아니다. 거꾸로, Jev가 여기서 버텼다고 모든 문구에서 버틴다는
  보장도 아니다.
- **TypeSafe의 "환각할 수 없다"는 주장은 출력 형식에 대한 것이다.** 타입 밖의 답을 못 낸다는 뜻이지
  판정이 맞는다는 뜻이 아니다. 위 극성 표가 정확히 그 차이를 보여 준다. 형식은 지켰지만 확신에 찬 오답을 낸
  모델이 다섯이다.

## 정리

| 질문 | 답 |
| --- | --- |
| 상위권 중 뭘 고르나 | 정확도로는 안 갈린다. API면 Jev, 셀프 호스팅이면 Kev, 오픈 웨이트+호스팅 둘 다면 Clef 27B (Arize 권고) |
| LLM judge 대신 써도 되나 | RAGTruth에서는 Opus 5와 오차 범위 안, 비용은 0.2~1.6% (Arize 측정) |
| 도입 전에 꼭 할 것 | 같은 질문을 긍정·부정 두 문구로 돌려 AUC가 같은지 본다 |
| 믿어도 되나 | 벤더 1차 결과다. 재현한 중립 제3자 결과는 아직 없다 |

이 블로그에서 Jev를 다룬 이전 글들은 "Jev가 LLM보다 낫다"는 말의 분모를 따졌다. 이번 벤치마크는 그 질문을
한 단계 옮긴다. 이제 문제는 **어떤 모델이냐보다, 그 모델에 어떻게 묻느냐**다.

## References

1. Jim Bennett, 「Decision model benchmark: Jev, Kev, Liquid d1, and more」, Arize AI Blog, 2026-10-07 (벤더 1차 벤치마크). <https://arize.com/blog/decision-model-benchmark/>
2. Sean Lee 옮김, 「Decision Model 8종 성능 비교: Jev, Kev, Liquid d1 중 무엇을 선택해야 할까?」, Arize Korea, 2026-11-10 (1의 한국어판). <https://www.arizekorea.com/insights/post/decision-model-benchmark-jev-kev-liquid-d1-2LXJin4juMAAhxr>
3. Diogo Almeida, 「Introducing System One Models & Jev」, TypeSafe, 2026-09-15 (제조사 1차 발표). <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
4. TypeSafe Docs, 「System One」 (공식 문서). <https://docs.typesafe.ai/concepts/system-one>
5. TypeSafe Docs, 「Models」 — 가격·컨텍스트·`/v1/systemone` (공식 문서). <https://docs.typesafe.ai/models>
6. Laurie Voss, 「Jev vs LLM-as-a-Judge: Accuracy and Cost Benchmarks」, Arize AI Blog, 2026-09-23 (벤더 1차 벤치마크, Opus 5 기준치 출처). <https://arize.com/blog/jev-as-a-judge/>
