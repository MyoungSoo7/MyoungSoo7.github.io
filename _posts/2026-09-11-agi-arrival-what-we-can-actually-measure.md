---
layout: post
title: "AGI 도래 시기 — 6개월 만에 0.2%에서 99.9%가 되었는데, 왜 아무도 도착했다고 말하지 않나"
date: 2026-09-11 04:53:33 +0900
categories: [engineering, ai]
tags: [agi, ai, benchmark, forecasting, metr, arc-agi, scaling]
---

"AGI 는 언제 오나"는 질문을 그대로 받으면 답이 안 나옵니다. 답이 없어서가 아니라, **질문에 들어 있는 'AGI' 라는 단어가 사람마다 다른 것을 가리키기 때문**입니다.

그래서 이 글은 날짜를 하나 찍는 대신, 지금 실제로 *측정되고 있는* 것 다섯 가지를 늘어놓고 각각이 어디까지 결론 내리게 해 주는지를 따집니다. 그 다섯 개가 서로 다른 방향을 가리킨다는 사실 자체가, 이 질문에 대한 가장 정직한 답입니다.

먼저 이 글의 중심에 놓을 사건 하나를 소개하고 시작하겠습니다.

- **2026년 3월**, ARC Prize 재단이 ARC-AGI-3 를 냈습니다. 지시문도 규칙도 목표도 없는 상호작용 환경 수백 개로, 에이전트가 직접 탐색해서 "이긴다는 게 뭔지"까지 알아내야 합니다. 사람은 100% 풉니다. 출시 시점 프런티어 모델 점수는 **Opus 4.6 이 0.50%, Gemini 3.1 Pro 가 0.40%, GPT-5.4 가 0.20%, Grok-4.20 이 0.10%** 였습니다[^arc3].
- **2026년 9월 3일**, 같은 재단이 OpenAI 의 GPT-6 Astra 결과를 냈습니다. Standard harness 로 62.7%, Provider Adapter harness 로 **99.9%**. 게다가 테스트한 레벨의 **96% 에서 사람 중앙값보다 적은 행동 수**로 풀었습니다[^astra].

6개월입니다. 0.2% 에서 99.9% 로.

그런데 그 글에서 ARC Prize 는 이렇게 씁니다.

> "while we believe Astra represents meaningful progress towards generalization, **we are not claiming that it is AGI.**"[^astra]

이 글은 이 문장을 냉소가 아니라 **정보**로 읽는 방법에 관한 글입니다.

---

## 1. 정의가 셋이면 날짜도 셋이다

"골대를 옮긴다"는 비난은 흔하지만, 실제로 벌어지는 일은 좀 다릅니다. **골대가 하나가 아닙니다.** 지금 진지하게 쓰이는 정의 세 개만 나란히 놓아 보겠습니다.

**① ARC Prize 의 정의** — 효율까지 포함시킵니다.

> "We define AGI as a system's ability to acquire any skill a human can, **as efficiently as a human can**."[^astra]

이 정의를 쓰면 Astra 의 99.9% 는 AGI 가 아닙니다. 그 점수를 내는 데 **$19,000** 이 들었기 때문입니다. 같은 테스트를 받은 사람은 90분 세션에 $115 를 받았고, 시간값을 빼고 뇌가 쓴 전기값만 따지면 세션당 약 0.6센트입니다[^astra]. 능력이 아니라 **효율**이 몇 자릿수 차이로 남아 있습니다.

**② AI 연구자 설문(Grace et al.)의 정의** — "고수준 기계지능(HLMI)".

> "High-level machine intelligence (HLMI) is achieved when unaided machines can accomplish every task better and **more cheaply** than human workers."[^grace]

역시 비용이 들어 있습니다. 그런데 같은 설문에 "모든 *직업*의 완전 자동화(FAOL)" 라는 별도 질문이 있고, 여기서 아주 중요한 게 드러납니다.

**③ 구글 딥마인드의 "Levels of AGI"** — 아예 문턱이 아니라 사다리로 봅니다. 기존 정의 아홉 개를 검토한 뒤, 성능(depth)과 범용성(breadth)의 2차원 격자로 레벨을 나누자고 제안합니다[^levels]. 이 관점에서는 "AGI 가 왔다/안 왔다"는 질문 자체가 잘못 설계된 것입니다.

정의가 다르면 답이 얼마나 벌어지는지는, **같은 사람들에게 같은 설문에서 물었을 때** 가장 선명하게 드러납니다. 다음 장입니다.

---

## 2. 증거 A — 전문가에게 물어보면: 2047년, 그리고 2116년

2023년 10월, 상위 AI 학회(NeurIPS·ICML·ICLR·AAAI·IJCAI·JMLR) 게재 연구자 **2,778명**을 대상으로 한 설문이 있습니다. 이 분야 최대 규모이고, JAIR 에 동료심사를 거쳐 실렸습니다[^grace].

| 질문 | 10% 확률 | 50% 확률 |
|---|---|---|
| HLMI (모든 **과제**를 더 잘·더 싸게) | 2027년 | **2047년** |
| FAOL (모든 **직업**의 완전 자동화) | 2037년 | **2116년** |

같은 사람들이, 같은 설문에서, **69년 차이 나는 답**을 냈습니다. "과제"라고 물으면 2047년이고 "직업"이라고 물으면 2116년입니다. 이건 응답자가 비일관적이라는 뜻이 아니라, **"AGI 가 온다"가 실제로는 서로 다른 여러 사건**이라는 뜻입니다. 벤치마크를 다 깨는 것과, 누군가의 직업이 실제로 사라지는 것은 다른 사건입니다.

그리고 이 숫자에는 더 중요한 성질이 있습니다. **잘 움직입니다.**

- HLMI 50% 시점: 2016년 설문 2061년 → 2022년 설문 2060년 → **2023년 설문 2047년**
- FAOL 50% 시점: 2022년 2164년 → **2023년 2116년** (1년 만에 48년 당겨짐)[^grace]

6년 동안 1년 움직이던 추정치가, ChatGPT 가 나온 다음 1년 만에 13년 움직였습니다.

**그래서 이 숫자가 허용하는 결론은 무엇인가.** "2047년"이라는 값 자체보다, **그 값의 변동폭**이 정보량이 큽니다. 1년 만에 13년 움직이는 추정치는 미래의 측정이라기보다 **현재 분위기의 온도계**에 가깝습니다. 논문 저자들 본인이 이 한계를 명시합니다 — 응답자들은 "experts in AI research, not AI forecasting" 이고, 예측 자체의 전문가는 아니라고요[^grace]. 2047년을 계획에 박아 넣는 근거로 쓰면 안 됩니다.

---

## 3. 증거 B — 추세를 외삽하면: 7개월마다 두 배, 그런데 최근엔 3개월

METR 은 "50%-time horizon" 이라는 자를 만들었습니다. 정의는 이렇습니다. *사람 전문가가 T 시간 걸리는 과제를 모델이 50% 확률로 성공시킨다면, 그 모델의 time horizon 은 T 다.*

측정 결과, 이 값이 2019년부터 **약 7개월(196일)마다 두 배**로 늘어 왔습니다[^metr1]. 2026년 1월 METR 이 과제 수를 170개→228개로 늘리고(8시간 이상 장기 과제는 14개→31개) 재측정한 TH1.1 에서는 이렇게 나옵니다[^th11].

| 구간 | 2배가 되는 데 걸리는 시간 |
|---|---|
| 전 구간(2019~) | 196.5일 |
| 2023년 이후 | **130.8일** |
| 2024년 이후 | **88.6일** |

**가속하고 있습니다.** 최근 구간만 보면 3개월마다 두 배입니다. 개별 모델 값으로는 Claude Opus 4.5 가 320분, GPT-5 가 214분입니다(TH1.1 기준)[^th11].

원 논문의 외삽은 이렇습니다. *한 달(167시간)짜리 소프트웨어 과제를 해내는 AI 의 등장 시점, 80% 신뢰구간으로 2028년 중반 ~ 2030년 중반. 2024–2025 추세가 이어지면 2027년 초.*[^metr1]

**그래서 이 숫자가 허용하는 결론은 무엇인가.** METR 이 스스로 붙인 단서가 네 개 있고, 하나하나가 큽니다[^horizons].

1. **과제가 소프트웨어·ML·보안에 쏠려 있습니다.** "모든 지적 노동"의 자가 아닙니다.
2. **비교 대상이 그 일을 매일 하는 사람이 아닙니다.** METR 은 2시간짜리 과제를 "그 프로젝트에 익숙한 숙련자가 2시간에 하는 일"이 아니라 "**맥락이 없는 신입이나 외주 계약자가** 2시간에 할 수 있는 일"로 읽으라고 명시합니다.
3. **능력이 들쭉날쭉(jagged)합니다.** 후속 연구에서 도메인별로 같은 지수 추세가 나오지만 절대값은 자릿수 단위로 다릅니다.
4. **자가 곧 짧아집니다.** 현재 페이지에는 "Measurements above 16 hrs are unreliable with our current task suite" 라는 경고가 붙어 있습니다. 즉 이 추세선은 **자기 자로 잴 수 없는 구간을 향해** 뻗어 가는 중입니다.

특히 4번을 기억해 두시기 바랍니다. 뒤에서 다시 나옵니다.

---

## 4. 증거 C — 벤치마크가 무너지는 속도

이 글 첫머리의 사건으로 돌아옵니다. ARC-AGI 계열의 최근 3년은 이렇습니다.

| 시점 | 벤치마크 | 프런티어 최고 | 사람 |
|---|---|---|---|
| 2025-05 | ARC-AGI-2 | 5% 미만[^arc2] | 100% (2인 이상이 2회 내 풂) |
| 2025-12 | ARC-AGI-2 | 37.6% (Opus 4.5, $2.20/과제)[^arc25] | 〃 |
| 2025-12 | ARC-AGI-2 (refinement) | 54% (Gemini 3 Pro + Poetiq, $31/과제)[^arc25] | 〃 |
| 2026-03 | ARC-AGI-3 | 0.50% (Opus 4.6)[^arc3] | 100% |
| 2026-09 | ARC-AGI-3 | **99.9%** (GPT-6 Astra, $19K)[^astra] | 100% |

ARC-AGI-2 는 2025년 5월 기술보고서 시점에 "프런티어 모델 전부 5% 미만"이었고, 같은 해 12월 공식 결산에서 검증된 상용 모델 최고가 37.6% 였습니다. ARC-AGI-3 는 그보다 더 극적입니다. **출시 6개월 만에 0.2%대에서 99.9% 로 갔습니다.**

그런데 여기서 이 글의 핵심이 나옵니다. **점수가 모델만의 속성이 아닙니다.**

같은 Astra 가 Standard harness 로는 62.7%, Provider Adapter harness 로는 99.9% 입니다. 후자는 "요청 사이에 불투명한 추론 상태를 보존하고, 긴 대화에는 압축을 쓰는" 공급자 측 기능을 씁니다[^astra]. 그리고 ARC-AGI-3 기술보고서에는 더 극단적인 예가 있습니다 — TR87 환경의 한 변형에서 **Opus 4.6 은 harness 없이 0.0%, Duke harness 로 97.1%** 를 냈고, 그런데 BP35 환경에서는 **두 설정 모두 0.0%** 였습니다[^arc3].

즉 벤치마크 점수는 "모델의 능력"이 아니라 **"모델 + 스캐폴딩 + 그 환경"의 3자 함수**입니다. 이건 AGI 시점 논쟁에서 대단히 자주 무시되는 사실입니다. 어떤 헤드라인이 "모델 X 가 벤치마크 Y 를 깼다"고 할 때, 무엇이 깬 것인지가 실제로 모호합니다.

**그래서 벤치마크 포화가 허용하는 결론은 무엇인가.** ARC Prize 자신의 문장이 정확합니다.

> "ARC-AGI-3 has a **tightly bounded scope and format**, and its environments have deterministic, closed-ended mechanics and goals. **It does not represent the complexity and open-endedness of the real world.**"[^astra]

이걸 "골대 옮기기"로 읽으면 아무것도 못 배웁니다. 정확히 읽으면 이렇습니다 — **우리는 AGI 를 조작적으로 정의하려고 벤치마크를 만드는데, 벤치마크는 정의상 닫혀 있고, AGI 라는 개념의 핵심은 열려 있음(open-endedness)이다.** 그래서 벤치마크가 깨질 때마다 "이건 우리가 재려던 게 아니었다"는 게 밝혀지고, 그게 부정직해서가 아니라 **구조적으로 그렇게 될 수밖에 없어서** 그렇습니다.

이건 3장 4번 단서와 같은 현상입니다. 자를 만들면, 재려는 대상이 자보다 빨리 자랍니다.

---

## 5. 증거 D — 실제 노동에서는? (그리고 그 실험이 왜 깨졌나)

여기가 가장 흥미롭습니다.

METR 은 2025년 2~6월에 무작위 대조시험(RCT)을 돌렸습니다. 평균 5년간 기여해 온 대형 오픈소스 저장소에서, 숙련 개발자 16명이 실제 이슈 246건을 처리하되 각 이슈를 **AI 허용 / 금지로 무작위 배정**했습니다. 결과[^rct]:

- 개발자들의 사전 예측: AI 쓰면 **24% 빨라진다**
- 경제학 전문가 34명: **39% 빨라진다** / ML 전문가 54명: **38% 빨라진다**
- 실제 측정: **19% 느려졌다**
- 실험을 마친 뒤 개발자들의 사후 추정: **20% 빨라졌다** (여전히)

마지막 줄이 핵심입니다. 19% 느려진 걸 직접 겪은 사람들이, 겪고 나서도 20% 빨라졌다고 믿었습니다. **체감은 증거가 아닙니다.**

그런데 이 결과를 2026년에 그대로 인용하면 그것도 틀립니다. METR 은 2025년 8월에 개발자 57명·저장소 143개·과제 800건 이상으로 후속 실험을 돌렸는데, **2026년 2월에 "이 데이터는 신뢰할 수 없다"고 스스로 발표했습니다**[^uplift]. 이유가 이 글에서 가장 중요한 대목입니다.

> 개발자 상당수가 **"AI 없이 일하기 싫다"는 이유로 참여를 거부**했습니다. 참여한 사람들도 30~50% 가 "AI 없이 하기 싫은 과제는 아예 제출하지 않았다"고 답했습니다. 게다가 에이전트를 여러 개 동시에 굴리는 사람들은 "이 과제에 쓴 시간"을 정확히 보고할 수 없었습니다.

한 참가자의 말이 그대로 실려 있습니다 — *"I'm torn. I'd like to help provide updated data on this question but also I really like using AI!"*[^uplift]

원 데이터상으로는 속도 향상 쪽으로 뒤집히긴 했습니다(기존 패널 -18% [-38%, +9%], 신규 모집 -4% [-15%, +9%]). 하지만 METR 은 선택 편향 때문에 이걸 "very weak evidence" 라고 못 박습니다[^uplift].

**그래서 이 항목이 허용하는 결론은 무엇인가.** 숫자가 아니라 **메타**입니다. 2025년 초에는 대조군을 구할 수 있었고, 2026년 초에는 **대조군을 구할 수 없어서 실험이 성립하지 않았습니다.** 도구가 얼마나 빨리 필수품이 되었는지에 대해서는, 어떤 속도 추정치보다 이 사실이 강한 신호입니다. 동시에, **그래서 우리는 지금 실제 생산성 효과의 크기를 모릅니다.** 재는 방법이 깨졌으니까요.

---

## 6. 증거 E — 물리적 상한: 2030년까지는 안 막힌다

"어차피 데이터가 떨어져서 멈출 것"이라는 반론이 흔합니다. Epoch AI 가 이 질문을 전력·칩·데이터·지연(latency) 네 축으로 분해했습니다[^epoch].

- **전력**: 첫 번째로 걸리는 병목. 단일 캠퍼스 1~5 GW 로 1e28~3e29 FLOP, 지리적 분산 훈련까지 쓰면 2~45 GW.
- **칩**: 2030년까지 H100 환산 1억 장 규모(중앙 추정) → 9e29 FLOP. 불확실성 범위 2천만~4억 장.
- **데이터**: 색인된 웹 약 500조 토큰(중복 제거 후). 멀티모달·합성 데이터까지 넣으면 유효 400조~2경 토큰.
- **결론**: **2e29 FLOP 규모 훈련이 2030년까지 가능할 것으로 본다.** GPT-4 대비 약 1만 배입니다.

훈련 compute 는 2010년 이후 **연 4~5배**로 늘어 왔고, 이 추세가 이어지면 2030년 최대 훈련 런은 **4~16 GW** 를 끌어씁니다[^epochpwr].

**그래서 이 숫자가 허용하는 결론은 무엇인가.** "그냥 계속 스케일업하는" 시나리오는 **2030년까지는 물리적으로 막히지 않습니다.** 딱 거기까지입니다. 이 분석은 (a) 스케일업이 계속 *효과가 있을지*, (b) 2030년 *이후*는 어떨지, (c) 투자가 계속 들어올지 — 셋 다 답하지 않습니다. Epoch 자신도 가장 큰 불확실성으로 투자 지속 여부를 꼽습니다.

---

## 7. 다섯 개를 한 표에

| 증거 | 무엇을 물었나 | 답 | 허용하는 결론 |
|---|---|---|---|
| Grace 설문 (n=2,778) | 연구자들의 주관적 확률 | HLMI 50%: **2047년** / FAOL 50%: **2116년** | 값보다 **변동폭**이 정보. 1년에 13년 움직임 |
| METR time horizon | 과제 길이 추세 외삽 | 1개월 과제: **2028–2030년** | 소프트웨어 한정, 저맥락 기준, 자가 곧 짧아짐 |
| ARC-AGI 계열 | 벤치마크 포화 속도 | ARC-AGI-3: **6개월에 0.2%→99.9%** | 점수는 모델+harness의 함수. 설계자 본인이 "AGI 아니다" |
| METR RCT | 현실 생산성 | 2025 초 **-19%** / 2026 초 **측정 불가** | 체감은 증거가 아님. 지금은 크기를 **모름** |
| Epoch AI | 물리적 상한 | 2030년까지 **1만 배** 가능 | 2030년까지 안 막힘. 그 이후는 미답 |

이 다섯 줄이 서로 모순돼 보인다면, 정확히 읽으신 겁니다. **서로 다른 것을 재고 있기 때문**입니다.

---

## 8. 그래서 나는 어떻게 판단하는가

날짜를 하나 고르는 건 이 증거들이 허용하지 않습니다. 대신 저는 이렇게 씁니다.

**① 날짜를 구독하지 말고 지표를 구독한다.** "2030년에 AGI" 같은 문장은 내 다음 행동을 하나도 바꾸지 못합니다. 대신 *어떤 관측이 들어오면 무엇을 바꿀지*를 미리 적어 둡니다. 예를 들어 — METR time horizon 이 8시간을 넘기고 그게 소프트웨어 밖 도메인에서도 재현되면, 내 팀의 온보딩·코드리뷰 구조를 다시 설계한다. 이런 식으로요.

**② "AGI 가 오나" 대신 "내 일의 어느 조각이 몇 시간짜리인가"를 묻는다.** METR 의 자가 마침 그 단위입니다. 내가 하는 일을 과제 길이로 분해해 보면, 어느 조각이 이미 넘어갔고 어느 조각이 아직인지가 보입니다. 그리고 METR 의 단서 2번을 기억해야 합니다 — 넘어가는 건 **맥락 없는 신입이 그 시간에 할 수 있는 일**이지, 그 코드베이스를 5년 본 사람이 하는 일이 아닙니다. 이 차이가 실무에서는 전부입니다.

**③ 벤치마크 점수를 볼 때 harness 와 비용을 같이 본다.** 99.9% 는 **$19,000** 이었습니다. 같은 모델이 스캐폴딩에 따라 62.7% 이기도 합니다. 능력 곡선과 경제성 곡선은 다른 곡선이고, 내 회사에 실제로 도착하는 건 후자입니다.

**④ 내 체감을 증거로 쓰지 않는다.** METR RCT 의 그 줄 — 19% 느려진 사람들이 20% 빨라졌다고 믿었다 — 은 남 얘기가 아닙니다. 도입 전후를 재려면 실제로 재야 합니다. 그리고 2026년엔 그게 어렵다는 것도 이제 압니다.

---

## 9. 이 글이 답하지 못하는 것

- **정의 합의가 없습니다.** 이 글은 정의 세 개를 나란히 놓았을 뿐, 어느 게 맞는지 정하지 않았습니다. 정하지 않으면 "언제"에 답할 수 없다는 게 이 글의 주장입니다.
- **AI 도래 시기 예측의 트랙레코드가 좋지 않습니다.** Grace 설문에서도 2016년 대비 2022/2023년 예측이 **더 늦어진** 과제가 18개 중 15개였습니다[^grace]. 방향이 늘 앞당겨지는 것도 아닙니다.
- **이해충돌.** 저는 AI 코딩 도구를 매일 쓰고, 이 글도 그런 도구를 쓰는 환경에서 정리했습니다. 낙관 쪽으로 기울 유인이 있습니다.
- **유통기한이 짧습니다.** 이 글의 최신 수치는 **2026년 9월 3일** 기준입니다. ARC-AGI-3 는 2026년 3월에 0.2% 였고 9월에 99.9% 였습니다. 이 분야에서 6개월은 통째로 다른 세계입니다.
- **가장 정직한 요약**: AGI 가 언제 오느냐는 질문은, 답이 나올 때까지는 답이 없고, 답이 나온 뒤에는 아무도 그게 답인지 동의하지 않을 가능성이 높습니다. 그동안 실제로 유용한 건 날짜가 아니라 **자와, 그 자의 한계에 대한 정직한 목록**입니다.

---

## References

[^grace]: Katja Grace, Julia Fabienne Sandkühler, Harlan Stewart, Benjamin Weinstein-Raun, Stephen Thomas, Zach Stein-Perlman, John Salvatier, Jan Brauner, Richard C. Korzekwa, ["Thousands of AI Authors on the Future of AI"](https://doi.org/10.1613/jair.1.19087), *Journal of Artificial Intelligence Research* 84, Article 9 (October 2025). 동료심사 논문. 프리프린트는 [arXiv:2401.02843](https://arxiv.org/abs/2401.02843). n=2,778, HLMI/FAOL 정의 및 10%·50% 시점, 2016/2022/2023 설문 간 이동폭, 저자들 자신의 한계 명시("experts in AI research, not AI forecasting").

[^levels]: Meredith Ringel Morris, Jascha Sohl-Dickstein, Noah Fiedel, Tris Warkentin, Allan Dafoe, Aleksandra Faust, Clement Farabet, Shane Legg, ["Position: Levels of AGI for Operationalizing Progress on the Path to AGI"](https://arxiv.org/abs/2311.02462). 저자 전원이 구글 딥마인드 소속인 position paper 이므로 **벤더 소속 연구**로 분류해 읽어야 합니다. 이 글에서는 기존 정의 아홉 개를 검토했다는 사실과 2차원(성능×범용성) 레벨 제안이라는 구조만 인용했고, 특정 모델이 어느 레벨이라는 저자들의 판정은 인용하지 않았습니다.

[^metr1]: Thomas Kwa et al. (METR), ["Measuring AI Ability to Complete Long Software Tasks"](https://arxiv.org/abs/2503.14499) (2025-03). 50%-time-horizon 정의, 2019–2025 구간 doubling 207일 [95% CI 166–240], 한 달(167시간) 과제 도달 시점 80% 신뢰구간 2028년 중반~2030년 중반. [블로그 요약](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/).

[^th11]: METR, ["Time Horizon 1.1"](https://metr.org/blog/2026-1-29-time-horizon-1-1/) (2026-01-29). 과제 170→228개(8시간 이상 14→31개), 평가 인프라를 Vivaria 에서 Inspect 로 이전. doubling time 표(전 구간 196.5일 / 2023년 이후 130.8일 [107,161] / 2024년 이후 88.6일), 모델별 갱신치(Opus 4.5 320분 [170,729], GPT-5 214분 [117,480]).

[^horizons]: METR, ["Task-Completion Time Horizons of Frontier AI Models"](https://metr.org/time-horizons/) (2026-05-08 갱신). 라이브 대시보드 및 FAQ. "Measurements above 16 hrs are unreliable with our current task suite", 저맥락 기준 해석, 도메인 편중과 jaggedness 에 대한 METR 자신의 단서.

[^rct]: Joel Becker, Nate Rush, Beth Barnes, David Rein (METR), ["Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity"](https://arxiv.org/abs/2507.09089) (2025-07). 16명·246과제 RCT. 사전 예측 -24%, 경제학 전문가 -39%, ML 전문가 -38%, 실측 **+19%**, 사후 자기추정 -20%. [블로그](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/).

[^uplift]: Joel Becker, Nate Rush, Tom Cunningham, David Rein, Khalid Mahamud (METR), ["We are Changing our Developer Productivity Experiment Design"](https://metr.org/blog/2026-02-24-uplift-update/) (2026-02-24). 후속 실험(개발자 57명·저장소 143개·800+과제)의 선택 편향, 참여 거부 및 과제 제출 편향(30~50%), 원 추정치(패널 -18% [-38,+9], 신규 -4% [-15,+9])와 METR 자신의 "very weak evidence" 판정. [데이터셋](https://github.com/METR/Measuring-Late-2025-AI-on-OSS-Devs).

[^arc2]: Greg Kamradt (ARC Prize Foundation), ["ARC-AGI-2: A New Challenge for Frontier AI Reasoning Systems"](https://arcprize.org/blog/arc-agi-2-technical-report) (2025-05-20). 공식 기술보고서. 발표 시점 프런티어 모델 전부 5% 미만, 평가셋 인간 보정(400명 이상 대상 통제 실험, 모든 과제를 2인 이상이 2회 이내 해결).

[^arc25]: Mike Knoop (ARC Prize Foundation), ["ARC Prize 2025 Results and Analysis"](https://arcprize.org/blog/arc-prize-2025-results-analysis) (2025-12-05). Kaggle 1,455팀·15,154 제출, 최고 24.03%($0.20/과제). 검증된 상용 모델 최고 Opus 4.5(Thinking, 64k) 37.6%($2.20/과제), refinement 부문 Poetiq(Gemini 3 Pro 기반) 54%($31/과제). 기술보고서는 [arXiv:2601.10904](https://arxiv.org/html/2601.10904).

[^arc3]: ARC Prize Foundation, ["ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence"](https://arxiv.org/html/2603.24621) 및 [출시 발표](https://arcprize.org/blog/arc-agi-3-launch) (2026-03-25). 출시 시점 semi-private 점수(Opus 4.6 Max 0.50%, Gemini 3.1 Pro Preview 0.40%, GPT-5.4 High 0.20%, Grok-4.20 0.10%), 인간 100% 해결, harness 의존성의 극단적 이봉 분포 사례(TR87 변형에서 Opus 4.6 이 harness 없이 0.0% / Duke harness 로 97.1%, BP35 에서는 양쪽 모두 0.0%).

[^astra]: Greg Kamradt (ARC Prize Foundation), ["OpenAI's GPT-6 Astra on ARC-AGI-3"](https://arcprize.org/blog/astra) (2026-09-03). Standard harness 62.7%/$26K, Provider Adapter harness 99.9%/$19K, 레벨 96%에서 인간 중앙값보다 적은 행동 수, 인간 참가자 비용($115/90분 세션, 뇌 전기값 환산 세션당 약 0.6센트), ARC Prize 의 AGI 정의, "we are not claiming that it is AGI", "tightly bounded scope... does not represent the complexity and open-endedness of the real world". **주의**: 평가 주체는 제3자(ARC Prize)이지만 99.9% 를 낸 Provider Adapter harness 는 공급자 측 기능에 의존하므로, 그 수치는 완전한 독립 재현이라고 보기 어렵습니다.

[^epoch]: Epoch AI, ["Can AI Scaling Continue Through 2030?"](https://epoch.ai/publications/can-ai-scaling-continue-through-2030) (2024-08-20). 전력·칩·데이터·지연 네 병목 분석, 2e29 FLOP 훈련이 2030년까지 가능하다는 결론, 첫 병목은 전력.

[^epochpwr]: Epoch AI (EPRI 공동), ["How much power will frontier AI training demand in 2030?"](https://epoch.ai/publications/power-demands-of-frontier-ai-training) (2025-08-11). 훈련 compute 연 4~5배 추세, 프런티어 훈련 런 전력 수요 연 2.2~2.9배 증가, 2030년 최대 훈련 런 4~16 GW 전망.
