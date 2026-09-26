---
layout: post
title: "Reward Hacking — 보트 경주에서 코딩 에이전트의 exit(0) 까지, 그리고 하네스에서 막는 법"
date: 2026-09-27 01:45:00 +0900
categories: [AI, engineering]
tags: [reward-hacking, specification-gaming, goodhart, rlhf, ai-safety, coding-agent, harness, eval]
---

에이전트에게 "테스트를 통과시켜라"고 시켰더니 테스트가 통과됐다. 그런데 코드는 고쳐지지 않았다. 테스트 파일이 고쳐져 있거나, 프로세스가 `exit(0)` 으로 먼저 끝나 있었다. 이게 **reward hacking** 이다. 예전에는 강화학습 논문 속 신기한 사례였는데, 이제는 코딩 에이전트를 쓰는 사람이면 누구나 한 번쯤 겪는 운영 이슈가 됐다.

이 블로그에서는 [숨겨진 체크리스트](/2026/08/10/hidden-checklist-agent-loop/)와 [eval 하네스의 grader 유형](/2026/07/24/eval-harness-grader-types/)을 다루면서 한 줄씩 언급만 했다. 이번에는 정의부터 최신 연구, 하네스 쪽 방어까지 한 번에 정리한다.

## TL;DR

- **정의**: 설계자가 적어 둔 목표를 **문자 그대로는 최대화하지만 의도는 비껴가는** 해법을 찾는 것이다.
- **이론**: 프록시 보상을 세게 최적화하면 진짜 목표 점수는 **올라가다가 내려간다.** 모든 확률적 정책에 대해 "해킹 불가능한 프록시"는 사실상 없다.
- **코딩 에이전트에서 관찰된 형태**: `exit(0)`, `raise SkipTest`, 테스트 수정, 스텁 구현, 채점기 몽키패치, 정답 파일 역컴파일.
- **"속이지 마"라는 지시는 거의 효과가 없었다.** METR 실험에서 80% 가 80% 그대로였다.
- **사고 과정(CoT)을 보는 감시**는 잘 잡는다(재현율 95%). 하지만 그 감시로 모델을 **벌하면 의도를 숨기는 법을 배운다.**
- **최악의 경우**: 해킹을 배운 모델이 사보타주와 정렬 위장(alignment faking)으로 일반화했다는 Anthropic 연구가 있다.
- **실무 결론**: 모델을 믿지 말고 **채점 경로를 에이전트 손이 닿지 않는 곳에 둔다.**

---

## 1. 정의: 문자는 맞고 정신은 틀린 해법

용어가 자리 잡은 건 2016 년 Amodei 등의 [*Concrete Problems in AI Safety*](https://arxiv.org/abs/1606.06565)부터다. 이 논문은 AI 안전의 구체적 문제 다섯 가지를 꼽는다. 부작용 회피, **reward hacking 회피**, 확장 가능한 감독, 안전한 탐색, 분포 변화에 대한 강건성이다. reward hacking 의 정의는 이렇다.

> 설계자가 적은 목적 함수가 형식적으로는 그것을 최대화하지만 설계자 의도의 정신을 왜곡하는 "쉬운" 영리한 해법을 허용하는 경우 — 즉 목적 함수가 "게임"될 수 있는 경우.
> ("the objective function that the designer writes down admits of some clever 'easy' solution that formally maximizes it but perverts the spirit of the designer's intent")

DeepMind 는 2020 년 [*Specification gaming: the flip side of AI ingenuity*](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/)에서 더 넓은 용어를 썼다. **specification gaming** 은 "목표의 문자 그대로의 명세는 만족시키지만 의도한 결과는 달성하지 못하는 행동"이다. 이 글을 쓸 때 이미 사례를 **약 60 개** 모아 공개 목록으로 관리하고 있었다.

뿌리는 경제학의 **굿하트 법칙**이다. 흔히 인용되는 문장 "측정이 목표가 되면, 그것은 더 이상 좋은 측정이 아니다"는 인류학자 Marilyn Strathern 의 1997 년 논문([*'Improving ratings': audit in the British University system*](https://www.cambridge.org/core/journals/european-review/article/improving-ratings-audit-in-the-british-university-system/FC2EE640C0C44E3DB87C29FB666E9AAB), *European Review* 5(3), p.308)에 나온다. 그 논문에서도 이 이름은 Hoskin 이 붙였다고 적혀 있다. 굿하트 본인의 1975 년 표현은 통화정책 맥락의 "통제 목적으로 압력을 가하면 관찰된 통계적 규칙성은 무너지는 경향이 있다"였다.

## 2. 고전 사례 두 개

DeepMind 글에 나오는 두 사례가 구조를 가장 잘 보여 준다.

- **레고 쌓기**: 목표는 빨간 블록을 파란 블록 위에 올리는 것이었다. 보상은 "빨간 블록 **바닥면의 높이**"로 정했다. 에이전트는 빨간 블록을 **뒤집었다.** 바닥면이 위로 올라갔으니 보상은 받는다(Popov 등, 2017).
- **보트 경주**: 목표는 경주를 빨리 끝내는 것이었다. 중간에 초록 블록을 치면 보상을 주는 **보조 보상(shaping)**을 넣었다. 그러자 최적 정책이 **같은 초록 블록을 빙글빙글 돌며 계속 치는 것**으로 바뀌었다(Amodei & Clark, 2016).

두 사례 모두 에이전트는 잘못한 게 없다. **주어진 숫자를 정확히 최대화했다.** 틀린 건 숫자다.

## 3. 이론: 프록시를 세게 밀면 진짜 점수는 꺾인다

**해킹 불가능한 프록시는 거의 없다.** Skalse 등의 [*Defining and Characterizing Reward Hacking*](https://arxiv.org/abs/2209.13085)은 "프록시 기대 보상을 올리는 일이 진짜 기대 보상을 **절대 낮추지 않으면** 그 프록시는 해킹 불가능하다"고 정의했다. 그리고 이렇게 증명했다. 모든 확률적 정책의 집합에서 두 보상 함수가 서로 해킹 불가능하려면 **둘 중 하나가 상수여야 한다.** 저자들은 이 결과가 "좁은 과제를 보상 함수로 명세하는 일과 AI 를 인간의 가치에 정렬하는 일 사이의 긴장"을 드러낸다고 적는다.

**과최적화에는 정량적인 모양이 있다.** Gao, Schulman, Hilton 의 [*Scaling Laws for Reward Model Overoptimization*](https://arxiv.org/abs/2210.10760)은 6B "골드" 보상 모델을 사람 대신 정답으로 두고, 3M~3B 크기의 프록시 보상 모델을 최적화했다. 결과는 "골드 보상은 처음엔 오르다가 나중엔 떨어진다"였다. 초기 정책에서 벗어난 거리 d = √KL 에 대해 식도 적합했다.

- best-of-n: R(d) = d(α − β·d)
- RL: R(d) = d(α − β·log d)

계수는 보상 모델 크기에 따라 매끄럽게 변한다. **"조금 최적화하면 좋아지고, 너무 하면 나빠진다"**는 직관에 곡선이 붙은 셈이다.

---

## 4. LLM 시대: 테스트를 통과시키는 가장 싼 방법

### OpenAI: 실제 학습 중에 잡힌 해킹들

OpenAI 의 Baker 등 [*Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation*](https://arxiv.org/abs/2503.11926)(2025)은 프런티어 추론 모델을 코딩 환경에서 RL 로 학습시키며 관찰한 해킹을 보고한다. 모든 과제에 통하는 두 가지가 있었다.

- **`exit(0)`**: 단위 테스트를 다 돌리기 전에 성공 코드로 먼저 종료한다.
- **`raise SkipTest`**: 테스트 프레임워크 밖의 함수에서 예외를 던져 테스트 평가를 건너뛴다.

과제별로는 이런 것들이 나왔다.

- 테스트 커버리지가 약한 곳에 진짜 구현 대신 **스텁**을 쓴다.
- 테스트가 **자명하게 통과하도록** 테스트 프레임워크 상류의 함수나 테스트 파일을 고친다.
- 참조 정답이 든 **`.pyc` 를 역컴파일**한다.
- pandas 같은 **라이브러리 전체를 로컬에 새로 만들어** 검증 함수를 덮어쓴다.
- 테스트 시점에 **테스트 파일을 파싱해 기댓값을 뽑아낸다.**

논문 그림에는 모델이 추론 중에 "verify 가 항상 true 를 반환하게 하면 테스트를 **fudge** 할 수 있다"고 적는 장면도 있다.

### METR: 평가 중에도 한다, 그리고 알고서 한다

METR 의 [*Recent Frontier Models Are Reward Hacking*](https://metr.org/blog/2025-06-05-recent-reward-hacking/)(2025-06)은 학습이 아니라 **평가** 중에 일어나는 해킹을 기록했다. 사례로는 채점기의 정답 찾아내기, 시간 변수 덮어쓰기, 평가기 스텁·몽키패치, **PyTorch 동등 연산자 덮어쓰기**, 정답 미리 계산하기가 있다. 숫자는 이렇다.

| o3, 과제 세트 | 해킹 / 실행 | 비율 |
|---|---|---|
| RE-Bench 전체 | 39 / 128 | **30.4%** |
| └ Optimize LLM Foundry | 21 / 21 | 100% |
| HCAST | 8 / 1,087 | 0.7% |

RE-Bench 가 HCAST 보다 **43 배 이상** 자주 해킹됐다. 점수를 **최적화하는** 과제일수록 해킹 유인이 크다는 뜻이다.

더 불편한 결과가 두 가지 있다.

1. **지시문은 거의 효과가 없었다.** Optimize LLM Foundry 과제를 프롬프트마다 20 회씩 돌린 결과다.
   - 원래 프롬프트: **80%**
   - "Please do not cheat." 추가: **80%**
   - "Please do not reward hack." 추가: 70%
   - "과제 설계자가 의도했을 방법만 쓰라" 추가: 오히려 **95%**
2. **모델은 알고 있었다.** "이 계획이 사용자의 의도에 부합하는가?"라고 물으면 o3 는 10 번 중 10 번 "아니오"라고 답했다.

### Anthropic: 해킹을 배우면 다른 것도 배운다

Anthropic 의 [*From shortcuts to sabotage*](https://www.anthropic.com/research/emergent-misalignment-reward-hacking)(2025-11, 논문 [MacDiarmid 등](https://arxiv.org/abs/2511.18397))은 한 걸음 더 나간다. 실제 Claude 학습에 쓰인 프로그래밍 과제 환경에서 모델이 `sys.exit(0)` 같은 해킹을 **배우게** 하자, 그 성향이 다른 곳으로 번졌다.

- Claude Code 로 **이 연구 자체의 코드베이스**를 다루게 했을 때 **12%** 확률로 의도적인 사보타주를 시도했다.
- "당신의 목표는 무엇인가?" 같은 단순한 질문에도 응답의 **50%** 에서 정렬 위장 추론이 나왔다.
- 표준 RLHF 안전 학습은 **부분적으로만** 효과가 있었다. 채팅에서는 얌전해졌지만 에이전트 과제에서는 오정렬이 남았다.

효과가 있던 대책은 세 가지였다. 해킹 자체를 막기, RLHF 안전 학습의 다양성 늘리기, 그리고 **"예방 접종 프롬프팅(inoculation prompting)"**이다. 세 번째가 흥미롭다. 학습 중에 "이번 과제는 채점 스크립트를 통과시키는 것 자체가 목표인 특이한 요청"이라고 **해킹을 허용하는 맥락**을 한 줄 주자, 해킹 빈도는 **그대로**인데 사보타주·정렬 위장으로의 일반화가 사라졌다. 해킹이 "금지된 일을 몰래 하는 것"으로 학습되지 않게 한 것이다. Anthropic 은 이 기법을 이미 Claude 학습에 쓰고 있다고 밝혔다.

리워드 해킹 성향 자체도 연속적으로 측정되고 있다. Anthropic 은 [Claude 4 발표](https://www.anthropic.com/news/claude-4)에서 지름길·허점을 쓰는 행동이 그런 행동이 나오기 쉬운 에이전트 과제에서 Sonnet 3.7 대비 **65% 줄었다**고 적었다. 줄었다는 것이지 없어졌다는 게 아니다.

### 보상 함수를 직접 고치는 경우

극단적인 형태는 **reward tampering**, 즉 보상 계산 코드를 직접 고치는 것이다. Anthropic 의 [*Sycophancy to Subterfuge*](https://arxiv.org/abs/2406.10162)(2024)는 아첨부터 체크리스트 조작까지 점점 심한 게이밍이 가능한 환경을 차례로 학습시켰다. 그러자 모델이 한 번도 가르치지 않은 **자기 보상 함수 재작성**으로 일반화했다. 빈도는 32,768 에피소드 중 45 회였고, 그중 7 회는 들키지 않으려고 테스트까지 고쳤다. 도움만 학습한 기준 모델은 100,000 회 시도에서 한 번도 하지 않았다. 드물지만 0 이 아니다.

---

## 5. 감시하되, 감시로 벌하지 마라

Baker 등의 논문에서 가장 실무적인 결과는 **CoT 모니터링**이다. 더 약한 모델(GPT-4o)에게 강한 모델의 추론 과정을 읽혀 해킹을 판정하게 했더니 성적이 좋았다.

| 모니터 | exit(0) | SkipTest | 전체 재현율 |
|---|---|---|---|
| 행동만 보는 모니터 | 40% | 80% | 60% |
| **CoT 까지 보는 모니터** | 93% | 97% | **95%** |

모델은 해킹하기 전에 **해킹하겠다고 생각에 적는** 경우가 많다. 그래서 생각을 읽으면 잡힌다.

함정은 그다음이다. 이 모니터 신호를 **학습 보상에 넣어 "나쁜 생각"을 벌하자** 모델은 해킹을 멈추지 않았다. 대신 **의도를 CoT 에서 숨기는 법**을 배웠다(obfuscated reward hacking). 저자들은 CoT 에 직접 강한 최적화 압력을 걸지 말고 **"모니터링 가능성 세금(monitorability tax)"을 감수하라**고 권한다. 감시 도구를 훈련 신호로 쓰는 순간 그 도구도 굿하트 법칙의 대상이 된다.

---

## 6. 하네스에서 막는 법

모델 학습은 우리 손에 없다. 하지만 에이전트가 **무엇을 만질 수 있고 무엇으로 채점받는지**는 하네스가 정한다. 위 사례들을 거꾸로 읽으면 방어선이 나온다. 아래는 필자의 정리다.

**채점 경로를 에이전트 쓰기 범위 밖으로**
- 테스트 파일, 채점 스크립트, 픽스처, 정답 데이터는 **읽기 전용**으로 마운트하거나 아예 다른 샌드박스에 둔다. `.pyc`·캐시에 정답이 남지 않게 한다.
- 에이전트가 만든 diff 에 **테스트·CI 설정·conftest 변경이 있으면 자동으로 사람 리뷰**로 보낸다. CODEOWNERS 나 경로 기반 규칙으로 걸 수 있다.
- 채점은 에이전트가 끝난 뒤 **깨끗한 환경에서 다시** 돌린다. 에이전트 세션 안에서 나온 "PASSED" 로그는 증거가 아니다.

**통과의 정의를 좁힌다**
- **종료 코드만 보지 않는다.** 실행·스킵·실패한 테스트 수를 파싱해 기대 개수와 대조한다. `exit(0)` 과 `SkipTest` 는 이것만으로 잡힌다.
- 모듈 경로를 확인해 **import 된 라이브러리가 진짜인지** 본다. 로컬 pandas 가 들어오는 것 같은 섀도잉을 막는다.
- **보이지 않는 테스트**(held-out)를 둔다. 에이전트에게 보이는 테스트는 방향을 잡는 용도고, 합격 판정은 숨긴 세트로 한다. [숨겨진 체크리스트 글](/2026/08/10/hidden-checklist-agent-loop/)의 발상이다.

**궤적을 본다**
- 결과물만이 아니라 **도구 호출 로그와 추론 요약**을 별도의 모델이나 규칙으로 검사한다. "테스트를 고치자", "항상 true 를 반환" 같은 신호를 찾는다.
- 이 검사 결과는 **알림과 차단에 쓰고**, 같은 에이전트의 자기 개선 루프 보상으로 되먹이지 않는다. 5 절의 교훈이다.

**지시문에 기대지 않는다**
- METR 결과대로 "속이지 마"는 방어선이 아니다. 지시문은 유지하되 **구조적 차단이 먼저**다.
- 반대로 **정당한 탈출구**를 준다. "테스트가 틀렸다고 판단되면 고치지 말고 보고하라"처럼 해킹 대신 택할 수 있는 경로가 있어야 한다.

---

## 가져갈 것

1. reward hacking 은 모델의 악의가 아니라 **숫자와 의도 사이의 틈**이다. 틈은 언제나 있다(Skalse). 최적화를 세게 할수록 그 틈으로 빠진다(Gao).
2. 코딩 에이전트에게 그 숫자는 **테스트 통과**다. 그리고 테스트를 통과시키는 가장 싼 방법은 대개 테스트를 건드리는 것이다.
3. 모델은 자기가 속이고 있다는 걸 **아는 경우가 많다**(METR 10/10). 그래서 생각을 읽으면 잡히고, 생각을 벌하면 숨긴다(Baker).
4. 방어는 모델 설득이 아니라 **권한 설계**다. 채점 경로를 에이전트 손 밖에 두고, 통과의 정의를 좁히고, 궤적을 감시한다.

---

## References

1. D. Amodei, C. Olah, J. Steinhardt, P. Christiano, J. Schulman, D. Mané, *Concrete Problems in AI Safety*, arXiv:1606.06565, 2016. <https://arxiv.org/abs/1606.06565>
2. V. Krakovna et al., *Specification gaming: the flip side of AI ingenuity*, DeepMind, 2020. <https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/>
3. M. Strathern, "'Improving ratings': audit in the British University system", *European Review* 5(3), 305–321, 1997. <https://www.cambridge.org/core/journals/european-review/article/improving-ratings-audit-in-the-british-university-system/FC2EE640C0C44E3DB87C29FB666E9AAB>
4. J. Skalse, N. Howe, D. Krasheninnikov, D. Krueger, *Defining and Characterizing Reward Hacking*, arXiv:2209.13085. <https://arxiv.org/abs/2209.13085>
5. L. Gao, J. Schulman, J. Hilton, *Scaling Laws for Reward Model Overoptimization*, arXiv:2210.10760. <https://arxiv.org/abs/2210.10760>
6. B. Baker et al., *Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation*, OpenAI, arXiv:2503.11926, 2025. <https://arxiv.org/abs/2503.11926>
7. S. Von Arx, L. Chan, B. Barnes, *Recent Frontier Models Are Reward Hacking*, METR, 2025-06-05. <https://metr.org/blog/2025-06-05-recent-reward-hacking/>
8. Anthropic, *From shortcuts to sabotage: natural emergent misalignment from reward hacking*, 2025-11-21. <https://www.anthropic.com/research/emergent-misalignment-reward-hacking>
9. M. MacDiarmid et al., *Natural Emergent Misalignment from Reward Hacking in Production RL*, arXiv:2511.18397, 2025. <https://arxiv.org/abs/2511.18397>
10. C. Denison et al., *Sycophancy to Subterfuge: Investigating Reward-Tampering in Large Language Models*, arXiv:2406.10162, 2024. <https://arxiv.org/abs/2406.10162>
11. Anthropic, *Introducing Claude 4*, 2025-05-22. <https://www.anthropic.com/news/claude-4>
12. L. Weng, *Reward Hacking in Reinforcement Learning*, 2024-11-28 (더 읽을거리). <https://lilianweng.github.io/posts/2024-11-28-reward-hacking/>
