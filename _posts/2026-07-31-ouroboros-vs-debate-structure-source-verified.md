---
layout: post
title: "우로보로스는 해석과 적용을 분리하지 않는다 — 토론 구조로 읽은 에이전트 시스템, 소스로 검증"
date: 2026-07-31 06:40:00 +0900
categories: [AI, Engineering, Philosophy]
tags: [Ouroboros, AgentOS, Evaluation, SpecFirst, Debate]
---

# 우로보로스는 해석과 적용을 분리하지 않는다

지난 [7월 27일 글]({{ site.baseurl }}/2026/07/27/ouroboros-philosophy-and-mechanics/)에서 성숙한 토론의 구조와 [Ouroboros](https://github.com/Q00/ouroboros)의 실행 하네스를 나란히 놓아 봤습니다. 그때는 개념 수준의 매핑이었습니다. 이번에는 같은 질문을 들고 소스를 열었습니다.

결론부터 적습니다. 다섯 단계 중 넷은 놀랍도록 정확히 대응했고, **한 곳은 정반대로 설계돼 있었습니다.** 지난 글에서 "우로보로스는 해석과 적용을 엄격히 분리한다"고 썼는데, 코드를 읽어보니 그 반대입니다. 그 교정이 이 글의 본론입니다.

이 글의 모든 수치와 인용은 Ouroboros 최신 릴리스 **v0.50.6** 시점의 소스에서 직접 확인한 것이며, 각 항목에 파일·라인 링크를 답니다.

---

## 비교의 틀

비교 대상이 된 토론 구조는 두 축을 가집니다.

**매너(태도)** — 존중, 경청, 명철, 온유, 인내
**방법(절차)** — ① 쟁점 기준 유지 → ② 근거와 사실 파악 → ③ 해석과 적용 분리 → ④ 기준 검토 → ⑤ 결론과 실행

우로보로스 쪽은 인터뷰(Interview) → 씨앗(Seed) → 실행(Execute) → 평가(Evaluate) → 진화(Evolve)의 루프입니다. 이제 하나씩 대조합니다.

---

## 검증 1 — 쟁점 기준 유지: 이탈을 감정이 아니라 지표로 잰다

토론에서 "지금 그 얘기가 아니잖아요"는 대개 감각의 영역입니다. 우로보로스는 이걸 숫자로 만듭니다.

```python
GOAL_DRIFT_WEIGHT = 0.5
CONSTRAINT_DRIFT_WEIGHT = 0.3
ONTOLOGY_DRIFT_WEIGHT = 0.2

DRIFT_THRESHOLD = 0.3
```

<sub>— [`src/ouroboros/observability/drift.py#L51-L56`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/observability/drift.py#L51-L56)</sub>

목표에서 벗어난 정도에 50%, 제약 이탈에 30%, 온톨로지(용어 정의) 이탈에 20%를 가중해 합산하고, 0.3을 넘으면 그대로 진행하지 못합니다. 가중치 배분 자체가 하나의 주장입니다 — **쟁점 이탈의 절반은 "목표를 바꿔치기한 것"에서 온다**는.

토론에 옮기면 이렇습니다. 말이 새는 방식은 한 가지가 아닙니다. 목적이 바뀌는 것, 전제가 슬며시 넓어지는 것, 같은 단어를 서로 다른 뜻으로 쓰는 것. 우로보로스는 이 셋을 따로 재고, 그중 목적 이탈을 가장 무겁게 봅니다.

## 검증 2 — 근거와 사실 파악: 돈이 안 드는 검증을 먼저

평가는 3단계 누진 구조입니다. 기계적 검증(lint·build·test) → 의미 평가(LLM) → 다중 모델 합의. 앞 단계에서 걸리면 뒤로 안 갑니다.

의미 평가의 합격선은 이렇게 박혀 있습니다.

```python
satisfaction_threshold: float = 0.8
```

<sub>— [`src/ouroboros/evaluation/semantic.py#L84`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evaluation/semantic.py#L84)</sub>

순서가 중요합니다. 값싼 사실 확인을 다 끝내기 전에는 비싼 해석 논쟁을 시작하지 않습니다. 토론에서 "그 숫자 맞아요?"를 먼저 정리하지 않고 의미 싸움으로 들어가면 어떻게 되는지, 우리는 이미 압니다.

## 검증 3 — 해석과 적용 분리: 여기가 정반대였다

이 글을 쓰게 만든 지점입니다.

성숙한 토론의 규율은 이렇습니다. **적용이 실패해도 해석을 임의로 바꾸지 않는다.** 해석이 결과에 끌려다니기 시작하면, 우리는 진리를 찾는 게 아니라 결과를 정당화하는 중이기 때문입니다.

우로보로스의 Reflect 단계는 모듈 설명부터 이렇게 시작합니다.

> The Reflect phase examines execution results + current ontology + wonder output and produces refined ACs + **ontology mutations** for the next Seed.

<sub>— [`src/ouroboros/evolution/reflect.py#L4`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evolution/reflect.py#L4)</sub>

실행 결과를 받아서 **온톨로지 변형**을 만들어냅니다. 온톨로지는 "이게 정확히 무엇인가"에 대한 정의, 즉 해석입니다. 그러니까 적용의 결과가 해석을 고치는 구조입니다.

게다가 선택이 아니라 의무입니다. 프롬프트에 이렇게 적혀 있습니다.

> If Wonder questions exist, you **MUST** propose at least one `ontology_mutation` that addresses them

<sub>— [`src/ouroboros/evolution/reflect.py#L464`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evolution/reflect.py#L464)</sub>

토론 규율의 정확한 반대편입니다. 지난 글에서 제가 잘못 짚었던 부분이고, 그래서 여기 남깁니다.

**다만 방임은 아닙니다.** 해석 변경에는 상한이 두 겹 걸려 있습니다. 하나는 앞서 본 드리프트 0.3, 다른 하나는 온톨로지가 바뀔 때 발동하는 3모델 합의입니다.

```python
majority_threshold: float = 0.66  # 2/3 = 0.6666...
```

<sub>— [`src/ouroboros/evaluation/consensus.py#L140`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evaluation/consensus.py#L140)</sub>

즉 우로보로스의 설계는 "해석 변경 금지"가 아니라 **"해석 변경을 비싸게"** 입니다.

어느 쪽이 옳은가는 취향의 문제가 아니라 **기준이 어디 있느냐**의 문제입니다. 기준이 우리 밖에 있다면(경전, 법전, 계약서) 해석은 고정이 맞고 적용만 배웁니다. 기준이 우리가 만든 것이라면(제품 명세) 해석도 학습 대상이 됩니다. 우로보로스의 기준인 Seed는 인터뷰로 사람이 만든 것이니, 후자를 택한 것은 자기 전제에 충실한 선택입니다.

## 검증 4 — 매너 축: 경청은 더 낫고, 온유는 없다

존중·온유·인내는 상대가 인격일 때 필요한 덕입니다. 우로보로스의 상대는 인격이 아니어서, 이 축은 덕이 아니라 **역할 강제**로 치환돼 있습니다. Devil's Advocate가 아무리 날을 세워도 아무도 상처받지 않습니다.

그런데 한 가지는 인간 토론보다 낫습니다. **소수 의견이 지워지지 않습니다.**

```python
disagreements = tuple(v.reasoning for v in votes if v.approved != approved)
```

<sub>— [`src/ouroboros/evaluation/consensus.py#L508`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evaluation/consensus.py#L508)</sub>

투표에서 진 쪽의 **근거(reasoning)**를 따로 모아 결과에 실어 보냅니다. 이벤트 저장소는 append-only라 지워지지도 않습니다. 사람의 회의에서 소수 의견은 대개 회의실을 나가는 순간 증발합니다. 경청의 형식만 놓고 보면 기계 쪽이 앞섭니다.

반대로 비어 있는 자리는 **온유**입니다. 심판(Judge)은 `approved` / `rejected` / `conditional` 세 가지 판정을 낼 수 있는데, 문서는 이렇게 못박습니다.

> **`conditional` is treated as rejection** in the pipeline (`DeliberationResult.approved == False`).

<sub>— [`docs/guides/evaluation-pipeline.md#L426-L428`](https://github.com/Q00/ouroboros/blob/v0.50.6/docs/guides/evaluation-pipeline.md#L426-L428)</sub>

정확히 말하면 조건부 판정의 **조건 목록은 보존되고 사용자에게 노출됩니다.** 사라지는 건 정보가 아니라 권한입니다. 회색지대가 기록으로는 남지만 통과로는 이어지지 않습니다.

온유는 "이기려 하지 않는 태도"입니다. 승과 패만 있는 게이트에는 그 자리가 없습니다. 사람 사이의 토론에서 "조건부"는 관계를 살리는 자리인데, 여기서는 접힙니다.

---

## 숫자 하나 뜯어보기 — 왜 0.1이 아니라 0.2인가

우로보로스는 인터뷰에서 모호도가 0.2 이하로 떨어지기 전에는 코드를 한 줄도 만들지 않습니다.

```python
AMBIGUITY_THRESHOLD = 0.2
```

<sub>— [`src/ouroboros/bigbang/ambiguity.py#L36`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/ambiguity.py#L36)</sub>

왜 하필 0.2일까요. 코드 주석에는 `(NFR6)`이라는 요구사항 번호만 달려 있고, **그 NFR 문서 자체는 저장소에 없습니다.** 값은 최초 인프라 커밋에 들어온 뒤 지금까지 바뀌지 않았습니다. 근거를 문서에서 찾을 수는 없다는 뜻입니다.

대신 코드가 답을 줍니다. 점수 공식은 이렇습니다.

```python
# Ambiguity = 1 - clarity
return round(1.0 - weighted_clarity, 4)
```

<sub>— [`src/ouroboros/bigbang/ambiguity.py#L812`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/ambiguity.py#L812)</sub>

모호도 0.2는 곧 **평균 명료도 80%** 입니다. 그리고 0.8은 앞서 본 의미 평가의 합격선과 같은 숫자입니다. 0.2는 독립적으로 고른 값이 아니라 **시스템 전역 합격선 0.8의 뒷면**입니다.

여기에 축별 하한선이 따로 있습니다.

```python
GOAL_CLARITY_FLOOR = 0.75
CONSTRAINT_CLARITY_FLOOR = 0.65
SUCCESS_CRITERIA_CLARITY_FLOOR = 0.70
```

<sub>— [`src/ouroboros/bigbang/ambiguity.py#L41-L43`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/ambiguity.py#L41-L43)</sub>

가중치는 목표 0.40 / 제약 0.30 / 성공기준 0.30입니다([L47-L49](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/ambiguity.py#L47-L49)). 하한선을 **간신히 다 맞춘** 상태를 공식에 넣어보면:

```
0.75 × 0.40 + 0.65 × 0.30 + 0.70 × 0.30 = 0.705
모호도 = 1 − 0.705 = 0.295
```

0.295. 통과선 0.2에 한참 못 미칩니다. 즉 **하한선은 "어느 축도 무너지면 안 된다"는 조건이고, 0.2는 그 위에 따로 얹은 총합 요구**입니다. 평균으로 약한 축을 덮을 수 없게 두 겹으로 잠가 놓았습니다.

그리고 한 번 잘 나왔다고 끝나지 않습니다.

```python
AUTO_COMPLETE_STREAK_REQUIRED = 2
```

<sub>— [`src/ouroboros/bigbang/ambiguity.py#L38`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/ambiguity.py#L38)</sub>

인터뷰 프롬프트에도 같은 취지가 명시돼 있습니다 — _"Even when the score is seed-ready, do not end the interview on the first low-ambiguity turn."_([`interview.py#L1387`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/interview.py#L1387))

**여기서부터는 제 추론입니다.** 왜 90%가 아니라 80%로 멈췄는가에 대해 문서화된 근거는 없고, 아래는 설계 구조에서 끌어낸 해석입니다.

첫째, 뒤에 진화 루프가 있습니다. 남은 20%는 세대를 돌며 흡수하도록 설계돼 있는데, 앞단에서 90%를 요구하면 사실상 폭포수로 회귀합니다. 진화 루프를 가진 시스템이 앞단 완벽주의를 요구하면 구조가 스스로 모순됩니다.

둘째, 채점자가 LLM입니다. 재현성을 위해 온도를 낮췄어도 0.10과 0.15를 안정적으로 가르기는 어렵습니다. 임계를 0.1로 두면 판정이 노이즈에 지배됩니다.

셋째, 명료도는 질문 수에 대해 수확 체감입니다. 마지막 10%를 깎으려면 질문이 급증하고, 기계보다 사람이 먼저 지칩니다.

넷째, 대신 조건을 겹쳤습니다. 단일 임계를 조이는 대신 **총합 0.2 + 축별 하한 + 2연속 달성**의 3중 구조를 택했습니다. 하나를 세게 조이는 것보다 여러 개를 겹치는 쪽이 대체로 더 견고합니다.

토론으로 옮기면 이런 입장입니다. 합격선을 100%로 잡으면 영원히 결론에 못 가고(분석 마비), 0.3이면 쟁점이 흐린 채로 시작합니다. 80%는 **"충분히 또렷하면 시작하고 나머지는 하면서 배운다"**는 선택입니다.

---

## 검증하지 못한 것

- **NFR6 원문**: 0.2·0.3 임계의 근거 문서는 저장소에 없어 확인하지 못했습니다. 위 네 가지 이유는 제 추론이며 저자의 의도가 아닙니다.
- **실측 효과**: 0.2가 0.1이나 0.3보다 실제로 나은 결과를 낸다는 비교 데이터는 저장소에서 찾지 못했습니다. 이 글은 **설계 의도의 정합성**을 읽은 것이지 성능을 검증한 것이 아닙니다.
- **버전 고정**: 모든 인용은 v0.50.6 기준입니다. 이 프로젝트는 변경이 잦아 이후 값이 달라질 수 있습니다.
- **토론 구조 쪽**: 비교 대상이 된 토론 구조는 제 실천적 정리이지 특정 문헌의 인용이 아닙니다. 그쪽에는 이 글이 다는 것과 같은 급의 1차 출처가 없습니다.

## 남는 질문

우로보로스는 스스로를 이렇게 소개합니다 — _"Ouroboros는 기계가 아닌 인간을 바로잡습니다."_([README.ko.md](https://github.com/Q00/ouroboros/blob/v0.50.6/README.ko.md)) 최종 기준이 인터뷰에 응한 사람이라는 뜻입니다.

그래서 이 시스템은 **"잘 만들었는가"는 정밀하게 재지만 "옳은 것을 원했는가"는 재지 못합니다.** 모호도 0.2는 명료함의 지표이지 진실성의 지표가 아닙니다. 아주 또렷하게 잘못된 것을 원할 수도 있으니까요.

기준이 루프 안에 있는 시스템과 루프 밖에 있는 토론. 오늘 소스를 읽고 남은 것은 이 한 문장입니다.

---

## References

모든 링크는 Ouroboros v0.50.6 태그 기준입니다.

1. Ouroboros 저장소 — [Q00/ouroboros](https://github.com/Q00/ouroboros)
2. 모호도 임계·하한선·가중치·공식 — [`src/ouroboros/bigbang/ambiguity.py`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/ambiguity.py)
3. 인터뷰 종료 조건 — [`src/ouroboros/bigbang/interview.py`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/bigbang/interview.py)
4. 드리프트 가중치·임계 — [`src/ouroboros/observability/drift.py`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/observability/drift.py)
5. 온톨로지 변형 — [`src/ouroboros/evolution/reflect.py`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evolution/reflect.py)
6. 의미 평가 합격선 — [`src/ouroboros/evaluation/semantic.py`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evaluation/semantic.py)
7. 합의·소수의견 보존 — [`src/ouroboros/evaluation/consensus.py`](https://github.com/Q00/ouroboros/blob/v0.50.6/src/ouroboros/evaluation/consensus.py)
8. 평가 파이프라인 가이드 (`conditional` 처리 포함) — [`docs/guides/evaluation-pipeline.md`](https://github.com/Q00/ouroboros/blob/v0.50.6/docs/guides/evaluation-pipeline.md)
9. 이전 글 — [불변의 진실과 자율적 실행: Ouroboros 아키텍처와 에이전트 끝장 토론의 함의]({{ site.baseurl }}/2026/07/27/ouroboros-philosophy-and-mechanics/)
