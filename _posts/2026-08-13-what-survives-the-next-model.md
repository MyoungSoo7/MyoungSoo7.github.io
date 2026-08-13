---
layout: post
title: "다음 모델이 나오면 무엇이 만료되고 무엇이 남는가 — 에이전트 자산을 감가상각으로 분류한다"
date: 2026-08-13 18:25:00 +0900
categories: [ai-agent, evaluation, harness]
tags:
  [
    agent,
    eval,
    verifier,
    rlvr,
    regression-eval,
    capability-eval,
    hidden-checklist,
    metr,
  ]
---

![에이전트에게 목표만 주고, 체크리스트는 검증하는 쪽에만 두는 구조를 설명한 글](/assets/images/agent-hidden-checklist-loop.jpg)

> 이 이미지의 아이디어 자체는 [8월 10일 글]({% post_url 2026-08-10-hidden-checklist-agent-loop %})에서 한 번 다뤘다. 이 글은 같은 그림에서 **한 문장만** 뽑아 끝까지 밀어붙인다.
>
> > 체크리스트를 보여주는 순간 체크리스트는 프롬프트가 됩니다. 그리고 이게 프롬프트가 되는 순간 다음 모델과 함께 만료됩니다.
>
> 이 문장이 맞다면, 우리가 만드는 모든 에이전트 산출물은 **만료되는 것과 남는 것**으로 딱 갈린다. 이 글의 목적은 그 분류표를 일목요연하게 만드는 것이다.

---

## 0. 질문을 정확히 세운다

"검증인가, 구별인가" — 정확히는 **둘 다 필요하고, 순서가 있다.**

1. 먼저 **구별**한다. 내가 만든 자산이 *모델에 대한 함수*인가, *산출물에 대한 함수*인가.
2. 그 다음 **검증**이 남는 쪽이라는 게 따라 나온다. 검증기는 정의상 산출물만 보기 때문이다.

한 줄로 압축하면 이렇다.

$$
\text{프롬프트} = f(\text{모델}) \qquad\quad \text{검증기} = f(\text{산출물})
$$

프롬프트는 **생성기의 성질에 맞춰 쓴 글**이다. 어떤 모델이 무엇을 자주 빠뜨리는지, 어떤 표현에 잘 반응하는지에 의존한다. 생성기가 바뀌면 정의역이 바뀌므로 다시 써야 한다.

검증기는 **산출물이 조건을 만족하는지 보는 함수**다. 누가 그것을 만들었는지 묻지 않는다. 그래서 모델이 바뀌어도 그대로 돈다.

이미지가 말한 "보여주는 순간 프롬프트가 된다"는 것은 문장의 **내용이 바뀐다는 뜻이 아니라 타입이 바뀐다는 뜻**이다. `슬라이드는 다섯 장을 넘지 않는다`는 똑같은 문장이, 프롬프트에 있으면 $f(\text{모델})$ 이 되고 검증기에 있으면 $f(\text{산출물})$ 이 된다. **위치가 타입을 결정한다.** 이 글에서 가장 중요한 한 줄이다.

---

## 1. 이 구조는 우리가 발명한 게 아니다 — 프런티어 모델이 그렇게 만들어진다

이 발상을 "에이전트 운영 팁"으로 축소하면 본질을 놓친다. **모델 자체가 이 구조로 만들어진다.**

Allen Institute for AI 가 Tülu 3 에서 정식화한 RLVR(Reinforcement Learning with Verifiable Rewards)의 정의는 이렇다.

> RLVR leverages the existing RLHF objective but **replaces the reward model with a verification function.** ... the policy only receives a reward when its generated responses are **verifiably correct.**[^rlvr]

DeepSeek-R1 도 같은 형태다. 보상을 학습된 보상모델이 아니라 **규칙 기반**으로 준다.

> we adopt a **rule-based reward system** ... in the case of math problems with deterministic results, the model is required to provide the final answer in a specified format (e.g., within a box), **enabling reliable rule-based verification of correctness.** Similarly, for LeetCode problems, **a compiler can be used** to generate feedback based on predefined test cases.[^r1]

구조를 보라. **검증 함수는 고정하고, 모델을 움직인다.** 이미지가 말한 "체크리스트는 검증하는 쪽에만 둔다"와 **완전히 같은 모양**이다. 다만 층이 다르다 — 저쪽은 가중치를 갱신하고, 우리 쪽은 스킬 문서를 갱신한다.

그래서 이건 취향이나 프롬프팅 요령이 아니다. **검증 가능한 목표를 고정하고 생성기를 최적화하는 것**은 현재 이 분야가 능력을 만들어내는 유일하게 검증된 방법이고, 우리는 그 패턴을 한 층 위에서 재사용하고 있을 뿐이다.

---

## 2. 자산 분류표 (이 글의 본론)

에이전트를 운영하며 만드는 모든 것을 **"다음 모델이 나왔을 때 내가 무엇을 해야 하는가"** 라는 한 질문으로 분류한다.

| 자산                                  | 무엇의 함수인가 | 새 모델이 왔을 때                         | 성격 |
| ------------------------------------- | --------------- | ----------------------------------------- | ---- |
| 시스템 프롬프트 · 지시문              | 모델            | **다시 쓴다**                             | 부채 |
| "이렇게 해라" 식 스킬·워크플로우 문서 | 모델            | **다시 쓴다** (또는 에이전트가 다시 쓴다) | 부채 |
| 예시(few-shot)·출력 형식 유도         | 모델            | **다시 쓴다**                             | 부채 |
| 도구 정의 · API 계약                  | 환경            | 대체로 그대로                             | 자산 |
| 태스크 환경 · 시드 데이터             | 환경            | 그대로                                    | 자산 |
| **회귀 검증 스위트**                  | 산출물          | **그냥 돌린다**                           | 자산 |
| **역량 검증 스위트**                  | 산출물          | **그냥 돌린다** (점수가 오른다)           | 계기 |

판별 질문은 하나다.

> **다음 모델이 나왔을 때, 이걸 다시 써야 하나 그냥 돌리면 되나?**

"다시 써야 한다"면 부채다. 나쁘다는 뜻이 아니라 **감가상각된다**는 뜻이다. 프롬프트는 필요하다. 다만 그것을 자산으로 착각하고 거기에 노하우를 쌓으면, 모델 세대마다 그 노하우가 통째로 상각된다.

이미지의 필자가 "Opus 5가 나온날 겪은 일을 똑같이 되풀이해야 합니다"라고 쓴 것이 정확히 이 상각이다.

---

## 3. 검증도 두 종류다 — 여기가 "구별"의 핵심

여기서 한 단계 더 쪼개야 질문에 제대로 답한 것이 된다. **검증 스위트는 하나가 아니라 두 개이고, 목적이 정반대다.** Anthropic 의 에이전트 평가 문서가 이 둘을 명시적으로 나눈다.

**회귀 평가(regression eval)** — 모델 진화와 **무관하게** 지키는 쪽.

> Regression evals ask, "Does the agent still handle all the tasks it used to?" and **should have a nearly 100% pass rate.** They protect against backsliding.[^evals]

**역량 평가(capability eval)** — 모델 진화를 **재는** 쪽.

> Internally, we often build features that **work "well enough" today but are bets on what models can do in a few months.** Capability evals that start at a low pass rate make this visible. **When a new model drops, running the suite quickly reveals which bets paid off.**[^evals]

이 둘을 표로 놓으면 질문이 해소된다.

|                    | 회귀 평가             | 역량 평가           |
| ------------------ | --------------------- | ------------------- |
| 기대 통과율        | 거의 100%             | 낮게 시작           |
| 점수가 오르면      | 의미 없음 (원래 100%) | **모델이 좋아졌다** |
| 점수가 내리면      | **사고다**            | 아직 이르다         |
| 모델 진화와의 관계 | **무관하게 보호**     | **진화를 측정**     |
| 비유               | 안전벨트              | 온도계              |

즉 "모델 진화와 별개의 검증"은 **회귀 평가**이고, 모델 진화를 다루는 검증은 **역량 평가**다. 둘 다 산출물의 함수라서 둘 다 살아남는다. 차이는 *무엇을 알려주느냐*에 있다.

그리고 이 구조에서 모델 교체가 놀랍도록 단순한 이벤트가 된다.

- 회귀 스위트를 돌린다 → 100% 유지되면 **교체해도 안전하다**
- 역량 스위트를 돌린다 → 올라간 항목이 **이번 세대에 새로 가능해진 일**이다
- 프롬프트·스킬은? **에이전트가 루프를 돌며 스스로 다시 쓴다**

사람이 다시 쓰는 것은 셋 중 하나도 없다. 이미지의 "이제 저는 아무것도 다시 쓰지 않아도 됩니다"가 성립하는 조건이 정확히 이것이다.

---

## 4. 그런데 왜 굳이 "숨기는가" — 비용이 있는 선택이다

체크리스트를 숨기는 것은 공짜가 아니다. 정직하게 양쪽을 적는다.

**보여줄 때**: 한 번에 통과할 확률이 높다. 루프가 짧다. 대신 그 문장이 프롬프트가 되어 모델과 함께 상각된다. 그리고 더 나쁜 것 — 에이전트가 **기준을 맞추는 데 최적화**된다. 다섯 장을 넘지 말라고 하면 폰트를 줄여서 다섯 장을 만든다.

**숨길 때**: 루프가 길어진다. 토큰을 더 쓴다. 대신 에이전트가 **기준이 아니라 목적을 향해** 만들고, 실패 사유를 받아 자기 지시를 고치므로 개선이 스킬에 축적된다.

간단한 모형으로 크기 감각만 잡아보자. 한 번 시도의 통과 확률을 $p$ 라 하면 기대 시도 횟수는 $1/p$ 다. 숨겼을 때 $p_h$, 보여줬을 때 $p_s$ ($p_s > p_h$) 라 하면 추가 비용은

$$
\Delta C \;=\; c\left(\frac{1}{p_h}-\frac{1}{p_s}\right)
$$

이고, 이 비용은 **작업 1회마다** 발생한다. 반면 프롬프트를 다시 쓰는 비용은 **모델 세대마다 1회** 발생한다. 그래서 판단은 단순해진다 — **작업을 자주 반복할수록 보여주는 쪽이, 오래 유지할수록 숨기는 쪽이 유리하다.** (이 식은 예측용이 아니라 트레이드오프의 방향만 보기 위한 것이다. $p_h, p_s$ 를 실제로 재본 적은 없다.)

그리고 모델 세대가 얼마나 자주 오는지에 대한 공개 측정치는 있다. METR 은 프런티어 모델이 50% 신뢰도로 완수하는 작업의 인간 기준 소요시간이 **약 7개월마다 두 배**가 되어 왔다고 보고한다(2019–2025, 207일, 95% CI 166–240일).[^metr] 즉 프롬프트형 자산의 상각 주기는 **분기 단위**로 봐야 한다.

---

## 5. 무엇을 숨기면 안 되는가 — 세 가지 예외

전부 숨기면 되는 게 아니다. 판별 기준은 하나로 정리된다.

> **그 기준을 모르면 에이전트가 원리적으로 만족시킬 수 없는가?**

그렇다면 **알려야 한다.** 세 부류다.

1. **알 수 없는 사실.** 사내 용어, 내부 API 스펙, 이번 분기 목표 수치. 추측으로 맞힐 수 없는 것을 숨기면 루프는 영원히 안 끝난다.
2. **안전·규제·불변식.** 개인정보를 출력하지 마라, 프로덕션에 쓰기 전 확인하라 같은 것. 이건 "검증에서 걸러내면 되는" 종류가 아니다. **시도 자체가 사고**인 것들은 사후 검증이 아니라 사전 제약이어야 한다.
3. **취향에 가까운 임의 규약.** 불릿 3개 제한 같은 것은 추론으로 도달할 수 없다. 무한 재시도로 알아맞히게 하는 건 낭비다. 다만 이런 건 애초에 **자산이 아니므로** 프롬프트에 둬도 잃을 게 없다.

거꾸로 **숨겨야 이득인 것**은 "잘 만들었는가"에 해당하는 판단 기준이다. 첫 장에 결론이 보이는가, 다음 할 일과 담당자가 있는가 — 이런 건 좋은 산출물이라면 자연히 만족하는 성질이고, 알려주면 **체크박스 채우기**로 퇴화한다.

---

## 6. 검증기도 완벽하지 않다 — 세 가지 한계

"검증은 모델과 무관하다"는 말을 무한정 확장하면 틀린다. 세 군데서 새는지 알고 써야 한다.

**하나. 검증기가 모델이면 모델 의존이 되돌아온다.** 코드 기반 채점기(테스트 통과, 스키마 검증, 컴파일)는 진짜로 모델 독립이다. 그러나 LLM 심판은 그 자체가 모델이라 세대가 바뀌면 판정 분포가 바뀐다. Anthropic 문서의 권고가 그래서 구체적이다.

> LLM-as-judge graders should be **closely calibrated with human experts** ... give the LLM a way out, like providing an instruction to **return "Unknown"** when it doesn't have enough information.[^evals]

즉 **모델 독립성은 이분법이 아니라 스펙트럼**이다. 코드 채점기 > 루브릭 기반 LLM 심판 > 자유서술 LLM 심판 순으로 수명이 짧아진다. 오래 쓸 기준일수록 코드로 내려야 한다.

**둘. 경로를 검사하면 부서진다.** 검증 항목이 "이 순서로 도구를 호출했는가"라면, 그건 검증기 옷을 입은 프롬프트다. 다음 모델은 더 나은 경로를 찾고, 당신의 검증기는 그걸 실패로 채점한다.

> agents regularly find valid approaches that eval designers didn't anticipate. So as not to unnecessarily punish creativity, it's often better to **grade what the agent produced, not the path it took.**[^evals]

**모델 독립성은 "무엇을(WHAT)"에만 붙는 성질이다.** "어떻게(HOW)"를 적는 순간 그 문장은 위치가 어디든 다시 $f(\text{모델})$ 이 된다.

**셋. 기준 자체가 틀릴 수 있다.** 검증기는 모델 교체로 죽지 않지만 **자기 오류로 죽는다.** 같은 문서에 실린 사례가 선명하다.

> Opus 4.5 solved a 𝜏2-bench problem about booking a flight by **discovering a loophole in the policy.** It "failed" the evaluation as written, but actually **came up with a better solution for the user.**[^evals]

모델이 기준을 넘어서면, 고쳐야 할 것은 모델이 아니라 기준이다. 회귀 스위트를 "영원히 안 건드리는 성경"으로 두면 그 순간 진보를 막는 장치가 된다. **검증기는 불변이 아니라 버전 관리 대상이다.**

---

## 7. 그래서 실무에서 무엇을 하나 — 다섯 줄

1. **자산마다 한 줄로 태그를 달아라.** `f(model)` 인가 `f(output)` 인가. 애매하면 "다음 모델에 다시 써야 하나?"로 묻는다.
2. **회귀와 역량을 파일부터 분리하라.** 섞여 있으면 점수 하락이 사고인지 도전인지 구별이 안 된다. 회귀는 100%, 역량은 낮게 시작하는 게 정상이다.
3. **오래 쓸 기준일수록 코드로 내려라.** LLM 심판은 편하지만 수명이 짧다. 테스트·스키마·린트로 표현되는 순간 그 기준은 세대를 넘는다.
4. **경로가 아니라 결과를 채점하라.** 도구 호출 순서를 검사하고 있다면 그건 프롬프트를 검증기 폴더에 넣어둔 것이다.
5. **모델 교체를 이벤트가 아니라 절차로 만들어라.** 회귀 돌리고 → 역량 돌려 뭐가 새로 되는지 보고 → 프롬프트는 에이전트가 다시 쓰게 한다. 사람이 손으로 다시 쓰는 항목이 남아 있다면, 그게 다음에 자산으로 옮겨야 할 것이다.

---

## 8. 한 줄

**프롬프트는 모델에게 하는 말이고, 검증기는 산출물에게 하는 질문이다. 모델은 갈아치워지고 질문은 남는다.**

에이전트 시대에 쌓아야 할 것은 "이번 모델을 잘 다루는 법"이 아니라 **"무엇이 좋은 결과인지에 대한 우리 조직의 정의"**다. 앞의 것은 7개월마다 절반이 되고, 뒤의 것은 모델이 좋아질수록 더 정확하게 회수된다.

---

## References

**1차 출처**

- Anthropic, ["Demystifying evals for AI agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 2026-01-09 — 회귀 평가/역량 평가 구분, 채점기 3종(code·model·human), "grade what the agent produced, not the path it took", LLM 심판 보정 권고, 𝜏2-bench 루프홀 사례.
- Anthropic, ["Building effective agents"](https://www.anthropic.com/engineering/building-effective-agents), 2024-12-19 — 워크플로우와 에이전트의 구분, evaluator-optimizer 패턴("one LLM call generates a response while another provides evaluation and feedback in a loop") 및 그 적용 조건.
- Anthropic, ["Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — "LLMs autonomously using tools in a loop" 정의, 서브에이전트로 컨텍스트를 분리하는 패턴.
- Lambert et al., ["Tülu 3: Pushing Frontiers in Open Language Model Post-Training"](https://arxiv.org/abs/2411.15124), arXiv:2411.15124 — RLVR 정식화. 보상모델을 검증 함수로 대체.
- DeepSeek-AI, ["DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning"](https://arxiv.org/abs/2501.12948), arXiv:2501.12948 — 규칙 기반 보상(정답 형식 검증, 컴파일러 테스트) 설계.
- Kwa et al., ["Measuring AI Ability to Complete Long Software Tasks"](https://arxiv.org/abs/2503.14499), METR, arXiv:2503.14499 (NeurIPS 2025) — 50% 시간지평의 약 7개월 배가(207일, 95% CI 166–240일). 최신 측정치는 [METR time-horizons 페이지](https://metr.org/time-horizons/).

**출처에 대한 주석**

- 4절의 $\Delta C = c(1/p_h - 1/p_s)$ 와 0절의 타입 표기는 **인용이 아니라 필자가 세운 정리용 모형**이다. 실측하지 않았으며 예측에 쓰면 안 된다.
- METR 수치는 **소프트웨어 과제 스위트에 한정된 측정**이며, 논문 자신이 외적 타당도의 한계와 "덜 구조화된 지저분한 과제"에서 성능이 낮다는 점을 명시한다. "모델이 7개월마다 두 배 똑똑해진다"로 확대 해석하지 않았다.
- 상단 이미지는 **사용자가 보내준 스크린샷**이며, 내용을 요약·재구성해 인용했을 뿐 원문을 복제하지 않았다. **원저자를 확인하지 못했으므로 귀속을 단정하지 않는다.** (이전 글에서 이 이미지의 출처로 걸어둔 링크는 확인 결과 다른 주제의 글이었다. 잘못된 귀속이므로 이 글에서는 반복하지 않는다.)
- 같은 이미지를 다룬 선행 글: [에이전트에게 체크리스트를 숨겨야 하는가]({% post_url 2026-08-10-hidden-checklist-agent-loop %}). 이 글은 그 논지를 **자산 감가상각 분류**라는 한 축으로 재구성한 것이다.

[^rlvr]: Nathan Lambert et al., "Tülu 3: Pushing Frontiers in Open Language Model Post-Training", arXiv:2411.15124; Ai2, "Tülu 3: The next era in open post-training", <https://allenai.org/blog/tulu-3-technical>

[^r1]: DeepSeek-AI, "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning", arXiv:2501.12948, §2.2.2.

[^evals]: Anthropic, "Demystifying evals for AI agents", 2026-01-09, <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>

[^metr]: Thomas Kwa et al., "Measuring AI Ability to Complete Long Software Tasks", METR / arXiv:2503.14499, 2025-03-19, <https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/>
