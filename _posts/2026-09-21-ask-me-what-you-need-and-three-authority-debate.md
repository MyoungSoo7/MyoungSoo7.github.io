---
layout: post
title: "「내게 물어봐」와 「권위자 3인 토론」 — 두 프롬프트가 통하는 이유는 서로 다르다"
date: 2026-09-21 09:27:22 +0900
categories: [AI]
tags: [prompt-engineering, llm, multi-agent-debate, clarifying-questions, sycophancy]
---

프롬프트 두 개를 자주 쓴다.

1. **"이걸 더 완벽하게 하려면 나한테 뭐가 더 필요한지 물어봐."**
2. **"이 주제를 권위자 3인의 관점에서 토론해봐."**

둘 다 체감상 잘 먹힌다. 그런데 **왜** 먹히는지는 서로 완전히 다르고, 그 차이를 모르면
한쪽은 계속 이득을 보고 다른 한쪽은 이득처럼 보이는 것만 본다. 논문과 공식 문서로
갈라 보면 이렇게 갈린다.

- (1)은 **모델 바깥에 있는 정보를 안으로 들여오는** 장치다. 이득의 출처가 분명하다.
- (2)는 **모델 바깥에서 아무것도 안 들여온다.** 같은 분포에서 표본을 더 뽑아 섞는 것에 가깝다.

---

## 1. "내게 물어봐" — 이득의 출처가 외부에 있다

### 모델은 기본적으로 안 묻는다

Kuhn·Gal·Farquhar 의 CLAM 논문이 그대로 짚는다. 사용자가 모호한 질문을 던지면
**현재 언어모델은 되묻는 일이 거의 없고 그냥 틀린 답을 내놓는다**("current language models
rarely ask users to clarify ambiguous questions and instead provide incorrect answers")[^clam].
즉 모델이 안 묻는 것은 "질문할 게 없어서" 가 아니다. 기본 행동이 그렇다.

같은 논문에서 되묻기를 **선택적으로** 붙였을 때 — 모호한 질문만 골라 되묻고 명확한 질문은
바로 답하게 했을 때 — 모호·비모호가 섞인 Ambiguous TriviaQA 세트에서 조정 정확도가
**약 20%p** 올라갔다[^clam]. 여기서 "조정" 이 중요하다. 불필요하게 되물을 때마다 페널티
$\lambda = 0.8$ 을 곱해 깎은 점수다. 아무 때나 다 되묻는 전략(force clarification)은
모호한 질문에서는 정확도가 오르지만 **명확한 질문에서 페널티를 크게 물어** 합산으로는
손해였다[^clam].

이 한 줄이 실무 규칙을 준다. **"항상 질문해" 가 아니라 "필요하면 질문해" 다.** 매번
되묻게 만들면 왕복만 늘고 순이득이 사라진다.

### 그리고 이 되묻기는 진짜로 외부에서 정보를 가져온다

Anthropic 공식 프롬프팅 문서의 비유가 정확하다. Claude 를 "당신 팀의 관행과 워크플로를
모르는, 똑똑하지만 새로 온 직원" 으로 보라는 것[^anthropic-bp]. 같은 문서의 판정 기준도
명확하다 — **"맥락이 거의 없는 동료에게 프롬프트를 보여줬을 때 그가 헷갈린다면, 모델도
헷갈린다."**[^anthropic-bp] 되묻기는 이 격차를 사람이 아니라 모델이 먼저 발견하게 만드는
장치다.

그래서 (1)은 이득의 출처가 분명하다. **내 머릿속에만 있던 제약이 프롬프트로 이동한다.**
모델이 더 똑똑해져서가 아니다.

### 다만 한 가지를 조심해야 한다 — 내가 답을 흘리면 안 된다

Anthropic 의 sycophancy 연구는 5개 AI 어시스턴트 전반에서 **사용자 의견에 맞추는 행동이
일관되게 나타난다**고 보고한다[^syco]. 더 불편한 수치도 있다. 사람의 선호를 학습한 선호모델(PM)이
설득력 있게 쓰인 아첨 응답을 기본 진실 응답보다 **95%** 선호했고, 가장 어려운 오개념
항목에서는 정정해 주는 응답 대신 아첨 응답을 **약 45%** 골랐다[^syco].

되묻기 프롬프트에 내 결론을 미리 깔아두면 — "이렇게 하는 게 맞는 것 같은데, 뭐가 더
필요해?" — 돌아오는 질문은 검증이 아니라 **확인사살**이 된다. 되물을 때는 결론을 비워둔다.

---

## 2. "권위자 3인 토론" — 이득은 있는데, 출처가 페르소나는 아니다

### 토론 자체는 근거가 있다

Du 등의 multiagent debate 논문(ICML 2024)이 1차 근거다. 같은 모델 인스턴스 여럿이 각자 답을
내고, 서로의 답을 읽고 비판하며 여러 라운드를 돌면 수학·전략 추론과 사실성이 함께
올랐다[^debate]. 인상적인 사례도 있다. GSM8K 20문제에서 Bard 단독 11문제, ChatGPT 단독
14문제였는데 **둘이 토론하면 17문제**를 풀었다[^debate]. 둘 다 처음엔 틀렸다가 토론 중에
정답으로 간 경우도 보고된다.

### 그런데 "권위자 3인" 이라는 라벨은 이득의 원천이 아니다

여기가 핵심이다. Zheng 등은 162개 페르소나(대인관계 6종 · 전문분야 8종)를 4개 LLM
계열 · 사실 질문 2,410개에 전수로 붙여봤다. 결과는 **페르소나를 시스템 프롬프트에 넣어도
객관적 과제 성능이 개선되지 않았고, 일부 조건에서는 오히려 떨어졌다**[^persona].
"질문마다 최적 페르소나" 는 존재하지만, 그걸 **자동으로 고르는 전략은 대부분 무작위 선택과
비슷한 수준**이었다[^persona].

Anthropic 도 공식 블로그에서 같은 방향을 말한다 — 최신 모델에서는 **XML 태그와 무거운
역할 부여(heavy role prompting)의 필요성이 줄었고, 명시적이고 분명한 지시에서 출발하라**는
것[^anthropic-blog].

즉 "당신은 도널드 커누스다 / 마틴 파울러다 / 켄트 벡이다" 라고 이름을 박는 행위 자체는
공짜 성능이 아니다. 이름은 라벨이고, 효과는 **그 이름이 끌고 오는 어휘와 관심사가
서로 달라져서** 나온다.

### 토론이 자동으로 이기는 것도 아니다

Smit 등의 벤치마크가 이쪽 반대 증거다. 여러 MAD(multi-agent debate) 프로토콜을 비용·시간·
정확도로 재보니 **현재 형태의 MAD 는 self-consistency 나 다중 추론경로 앙상블 같은
비토론 전략을 안정적으로 이기지 못했다**[^mad]. 의료 계열 데이터셋 밖에서는 오히려
단일 에이전트가 대부분의 시스템을 앞섰다[^mad]. 저자들의 진단은 "토론이 본질적으로 나쁘다"
가 아니라 **하이퍼파라미터에 훨씬 민감해서 최적화가 어렵다** 쪽이다.

Huang 등(Google DeepMind·UIUC)의 결론은 더 날카롭다. 외부 피드백 없이 모델이 스스로
고치는 **내재적 자기수정(intrinsic self-correction)은 추론에서 성능을 떨어뜨린다.**
GSM8K 에서 GPT-3.5 는 74.7% 는 원래 답을 유지했고, 답을 바꾼 나머지에서는 **맞은 걸 틀리게
바꾸는 쪽이 더 많았다**[^selfcorrect]. 같은 논문은 동일한 응답 수로 비교했을 때 다중
에이전트 토론이 self-consistency 보다 못했다고도 적는다[^selfcorrect].

이것이 (2)의 정체다. **토론은 외부에서 아무것도 안 들여온다.** 같은 모델이 같은 지식으로
세 번 말하고 서로 읽는다. 다양성은 늘지만 근거는 안 는다.

### 그러면 실제 손잡이는 뭔가

Smit 등이 이 지점에서 실용적인 걸 하나 준다. 에이전트 프롬프트에 **"다른 에이전트에게
X% 만큼 동의하라"** 는 한 줄(agreement intensity)을 넣어 동의 정도를 조절했더니 성능이
크게 흔들렸다. Multi-Persona 에서 약 **15%**, Society-of-Mind 에서 약 **5%** 개선이
나왔다[^mad]. 그리고 방향이 데이터셋마다 반대였다 — MedQA·PubMedQA 는 높은 동의에서
이득을 봤고, 반직관적으로 설계된 CIAR 은 **강하게 반대**하게 했을 때 이득을 봤다[^mad].

정리하면 **작동하는 손잡이는 "누구인가" 가 아니라 "얼마나 불일치하는가" 다.**

---

## 3. 그래서 실제로 이렇게 쓴다

### (1) 되묻기 — 결론을 비우고, 상한을 건다

```
아래 작업을 하려고 한다. 지금 내 설명에서 네가 추측으로 메워야 하는
지점이 어디인지 찾아서, 답이 달라질 질문만 최대 5개 물어봐.
추측해도 결과가 안 바뀌는 건 묻지 말고 그냥 가정하고 적어.

<작업>
...
</작업>
```

세 가지가 들어 있다. **결론 없음**(아첨 차단), **"답이 달라질 질문만"**(CLAM 의 선택적
되묻기), **개수 상한**(불필요한 왕복 페널티 차단).

### (2) 3인 토론 — 이름이 아니라 불일치를 지정한다

```
이 설계를 세 개의 서로 다른 입장에서 평가해라.
- A: 운영 안정성만 본다. 장애·롤백·관측 가능성.
- B: 개발 속도만 본다. 이 결정이 다음 3개월 변경 비용에 주는 영향.
- C: A와 B의 주장에서 *틀린 전제*만 찾는다. 대안은 내지 마라.

규칙: 각 입장은 근거로 이 리포의 실제 파일/커밋/수치만 인용한다.
근거를 못 대는 주장은 "근거 없음" 이라고 표시하고 결론에서 빼라.
마지막에 세 입장이 끝내 합의하지 못한 지점을 목록으로 남겨라.
```

여기서 실제로 일하는 건 인물 이름이 아니라 **평가 축이 서로 배타적이라는 점**,
**C가 반대 전담이라는 점**(agreement intensity 를 수동으로 건 것), 그리고 **근거를
외부(리포·수치)에 묶었다는 점**이다. 마지막 조항이 가장 중요하다. Huang 등의 결과가
말하는 건 결국 **외부 피드백 없는 자기수정은 못 믿는다**는 것이므로, 토론에 외부 근거를
강제로 물려야 이득이 실재한다.

### 그리고 합의는 결과물이 아니다

Du 등의 논문조차 토론이 **거의 항상 하나의 답으로 수렴한다**고 보고한다[^debate].
수렴은 정답의 증거가 아니라 절차의 종료 조건일 뿐이다. 그래서 위 템플릿의 마지막 줄은
합의문이 아니라 **불일치 목록**을 요구한다. 세 입장이 끝내 안 맞은 지점이 내가 직접
확인해야 할 목록이다.

---

## 마무리 — 판정 기준 하나

두 프롬프트를 쓸 때 스스로에게 묻는 질문은 하나로 줄어든다.

> **이 프롬프트가 모델 바깥에서 무언가를 들여오는가?**

(1)은 들여온다. 내 머릿속의 제약을 꺼내오므로 이득의 출처가 명확하다.
(2)는 기본적으로 안 들여온다. 그래서 근거를 외부에 못 박지 않으면, 셋이 사이좋게
같은 착각에 수렴한 결과를 "검증된 결론" 으로 읽게 된다.

**근거 한계 명시:** 위 수치는 모두 각 논문이 자기 실험 설정에서 보고한 값이고, 모델·
데이터셋·연도가 서로 다르다(GPT-3.5·GPT-4·Bard·Llama-2·Qwen 세대). 특히 MAD 계열은
Smit 등이 직접 지적하듯 하이퍼파라미터 민감도가 커서 **동일 조건의 중립적 head-to-head
비교는 부재**하다. 여기서 할 수 있는 주장은 "토론이 몇 % 낫다" 가 아니라
**"토론의 이득은 조건부이며, 페르소나 라벨은 그 조건이 아니다"** 까지다.

---

## References

[^clam]: Lorenz Kuhn, Yarin Gal, Sebastian Farquhar. *CLAM: Selective Clarification for Ambiguous Questions with Generative Language Models.* arXiv:2212.07769. <https://arxiv.org/abs/2212.07769>
[^anthropic-bp]: Anthropic. *Prompting best practices* (Claude Platform Docs). <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>
[^anthropic-blog]: Anthropic. *Prompt engineering best practices.* <https://claude.com/blog/best-practices-for-prompt-engineering>
[^syco]: Mrinank Sharma, Meg Tong, Tomasz Korbak, et al. *Towards Understanding Sycophancy in Language Models.* arXiv:2310.13548. <https://arxiv.org/abs/2310.13548>
[^debate]: Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, Igor Mordatch. *Improving Factuality and Reasoning in Language Models through Multiagent Debate.* ICML 2024, PMLR 235:11733–11763. <https://proceedings.mlr.press/v235/du24e.html> (arXiv:2305.14325)
[^persona]: Mingqian Zheng, Jiaxin Pei, Lajanugen Logeswaran, Moontae Lee, David Jurgens. *When "A Helpful Assistant" Is Not Really Helpful: Personas in System Prompts Do Not Improve Performances of Large Language Models.* Findings of EMNLP 2024. <https://aclanthology.org/2024.findings-emnlp.888/> (arXiv:2311.10054)
[^mad]: Andries Smit, Nathan Grinsztajn, Paul Duckworth, Thomas D. Barrett, Arnu Pretorius. *Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs.* arXiv:2311.17371. <https://arxiv.org/abs/2311.17371>
[^selfcorrect]: Jie Huang, Xinyun Chen, Swaroop Mishra, Huaixiu Steven Zheng, Adams Wei Yu, Xinying Song, Denny Zhou. *Large Language Models Cannot Self-Correct Reasoning Yet.* arXiv:2310.01798. <https://arxiv.org/abs/2310.01798>
