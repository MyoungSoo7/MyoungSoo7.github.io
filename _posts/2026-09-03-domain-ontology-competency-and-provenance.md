---
layout: post
title: "도메인 온톨로지는 언제 '쓸만해지는가' — 정의·문제·가치·이력, 그리고 한 줄의 판정"
date: 2026-09-03 19:05:26 +0900
categories: [data]
tags: [ontology, competency-questions, provenance, prov-o, gene-ontology, fair, skos]
---

앞 글에서 데이터의 준비도를 `ready(D, P, t)` 라는 술어로 적었다. 데이터셋 $$D$$ 가
목적 $$P$$ 에 대해 시점 $$t$$ 에 승인된 상태인가. 온톨로지도 정확히 같은 꼴을 갖는다.

> 온톨로지의 쓸만함은 $$\mathrm{good}(O)$$ 가 아니라 $$\mathrm{competent}(O, Q, t)$$ 다 —
> 온톨로지 $$O$$ 가 역량질문 집합 $$Q$$ 를 시점 $$t$$ 에 답해내는가.
> 인자 $$Q$$ 를 빼면 "좋은 온톨로지" 는 감상이지 판정이 아니다.

이 글은 도메인 온톨로지를 다섯 축 — **정의 → 푸는 문제 → 만드는 가치 → 쌓인 이력 →
한마디로 얼마나 쓸만한가** — 으로 따라가면서, 그 마지막 한마디가 왜 반드시
인자를 받는 술어여야 하는지를 1차 자료로 정리한다.

## 1. 정의 — 목적은 정의 안에 이미 들어 있다

가장 많이 인용되는 정의는 Gruber 의 것이다.

> "An ontology is an explicit specification of a conceptualization."
> — [Gruber, *A Translation Approach to Portable Ontology Specifications*, Knowledge Acquisition 5(2), 1993](https://tomgruber.org/writing/ontolingua-kaj-1993.pdf)

여기서 자주 흘려 읽히는 대목은 **conceptualization 의 정의 쪽**이다. 같은 논문은
conceptualization 을 "우리가 **어떤 목적을 위해** 표현하고 싶은, 세계에 대한
추상적이고 단순화된 관점" 으로 정의한다. 즉 목적은 온톨로지의 *부가 요구사항*이
아니라 **정의를 구성하는 성분**이다. 같은 논문이 설계 기준을 논하면서
"자연스러움이나 진리에 대한 선험적 관념이 아니라 **결과물의 목적에 근거한**
객관적 기준이 필요하다" 고 못박은 것도 같은 이유다. 그가 제시한 다섯 기준 중
하나인 *minimal ontological commitment* — 의도한 지식 공유 활동을 지탱하는 데
필요한 최소한의 존재론적 개입만 하라 — 도 "목적 밖의 주장은 하지 말라" 는
요구다.

널리 쓰이는 다른 정의는 형용사가 넷이다.

> "an ontology is a formal, explicit specification of a shared conceptualization"
> — Studer, Benjamins & Fensel, *Knowledge Engineering: Principles and Methods*, Data & Knowledge Engineering 25(1–2), 1998, p.184

네 형용사는 장식이 아니라 각각 다른 검사를 요구한다.

| 형용사 | 요구하는 것 | 없으면 생기는 일 |
|---|---|---|
| formal | 기계가 해석 가능한 형식 semantics | "우리 팀은 이렇게 이해한다" 가 시스템 간에 안 넘어간다 |
| explicit | 개념·관계·제약이 문서가 아니라 **공리로** 적혀 있음 | 암묵적 합의가 사람이 바뀌면 사라진다 |
| shared | 한 사람이 아니라 공동체의 합의 | 부서마다 다른 온톨로지가 생겨 통합 대상이 하나 더 늘어난다 |
| conceptualization | 표현 대상이 되는 **목적 붙은** 세계관 | 무엇을 넣고 뺄지 판단할 기준이 없다 |

### 분류체계를 가졌다고 온톨로지를 가진 게 아니다

이 경계를 표준 자신이 명시적으로 긋는다. W3C SKOS Reference 는 시소러스·분류체계·
주제명표목 같은 지식조직체계(KOS)를 기계가 읽을 수 있게 만드는 데이터 모델인데,
스스로에 대해 이렇게 쓴다.

> "However, SKOS is not a formal knowledge representation language."
> — [SKOS Simple Knowledge Organization System Reference, W3C Recommendation, 2009](https://www.w3.org/TR/skos-reference/)

이유도 같은 문서가 설명한다. 형식 온톨로지에서 "지식" 은 **공리와 사실의 집합**으로
표현되지만, 시소러스나 분류체계는 어떤 공리도 사실도 주장하지 않는다. 그 계층
구조에는 형식 semantics 가 없고, 세계에 대한 공리나 사실로 신뢰성 있게 해석될 수
없으며, **애초에 그렇게 의도된 적도 없다**. 그것들은 어떤 주제 영역의 편리하고
직관적인 지도일 뿐이다.

그래서 SKOS 문서는 재공학(re-engineering)의 비용을 경고한다. 시소러스를 형식
온톨로지로 바꾸려면 사람이 그 구조와 내용을 공리와 사실로 변환해야 하고, 이 일은
지적으로 까다롭고 시간이 들며 따라서 비싸다. 더 날카로운 경고는 그다음 문장이다 —
어떤 KOS 는 **설계상 자기 도메인의 논리적 관점을 표현하려는 의도가 아예 없고**,
그런 것을 논리 기반 표현으로 바꾸면 실무에서는 **원래 의도한 목적에 더는 맞지 않는
표현**이 되어 버릴 수 있다.

즉 "형식화 수준을 올리는 것" 자체가 개선이 아니다. 개선인지 아닌지는 목적이 정한다.
이 글의 나머지는 그 목적을 **검사 가능한 형태로 고정하는 장치**에 관한 것이다.

## 2. 문제 — 온톨로지가 실제로 푸는 문제

Gruber 논문의 제목에 답이 있다. *portable* ontology specifications — 서로 다른
표현 언어와 시스템을 쓰는 당사자들이 **같은 용어를 같은 뜻으로** 쓰게 만드는
문제다. 데이터 쪽 말로 바꾸면 이렇다.

- 같은 단어가 부서마다 다른 뜻이라 조인이 조용히 틀린다.
- 다른 단어가 같은 뜻이라 조인이 아예 안 된다.
- 어느 쪽인지 확인할 방법이 코드 리뷰밖에 없다.

그런데 "용어를 통일하자" 는 구호로는 어디까지 통일해야 하는지, 통일이 끝났는지를
판정할 수 없다. Grüninger 와 Fox 의 1995년 방법론이 도입한 것이 바로 그
**판정 장치**다.

> "Every proposal for a new or extended ontology must be accompanied by a set of
> formal competency questions. It is only in this way that we can evaluate the
> ontology and claim that it is adequate."
> — [Grüninger & Fox, *Methodology for the Design and Evaluation of Ontologies*, IJCAI-95 Workshop on Basic Ontological Issues in Knowledge Sharing](http://stl-fs.mie.utoronto.ca/publications/gruninger-ijcai95.pdf)

절차는 다음과 같다. 먼저 **motivating scenario** — 온톨로지가 없어서 곤란한 실제
상황 — 를 적는다. 거기서 온톨로지가 반드시 답해야 할 질문들, 즉 **informal
competency question** 을 뽑는다. 그다음 그 질문을 표현하는 데 필요한 용어만 골라
1차 술어논리로 terminology 를 정의하고, 질문을 형식적으로 다시 쓴다. 형식 역량질문은
$$T_{\mathrm{ontology}}$$ 를 온톨로지의 공리 집합, $$T_{\mathrm{ground}}$$ 를 인스턴스
집합, $$Q$$ 를 질문이라 할 때 다음 두 형태 중 하나의 문제가 된다.

$$T_{\mathrm{ontology}} \cup T_{\mathrm{ground}} \;\models\; Q
\qquad\text{또는}\qquad
T_{\mathrm{ontology}} \cup T_{\mathrm{ground}} \cup Q \;\text{가 consistent}$$

여기서 방향이 뒤집힌다. 보통은 모델을 먼저 그리고 나중에 "이걸로 뭘 할 수 있나" 를
묻는데, 이 방법론은 **질문이 용어의 존재 근거**가 되게 만든다. 같은 논문의 표현으로,
제안된 온톨로지의 모든 객체·속성·관계·공리에 대해 **그것을 직관적으로 요구하는
informal competency question 이 먼저 있어야 한다.**

그리고 이 방법론에는 실무에서 제일 자주 무시되는 한 줄이 있다.

> "It is not a well-designed ontology if all competency questions have the form of
> simple lookup queries; there should be questions that use the solutions to such
> simple queries."

역량질문이 전부 단순 조회면 통과율 100% 를 받아도 그 온톨로지는 잘 설계된 게 아니다.
낮은 질문의 답을 재료로 쓰는 상위 질문이 있어야 한다. 뒤에서 볼
$$\mathrm{coverage}$$ 지표가 왜 혼자서는 못 미더운지의 근거가 여기 있다.

또 하나. 같은 논문은 역량질문이 **존재론적 개입을 만들어내지 않는다**고 분명히 한다.
역량질문은 이미 내려진 개입을 *평가하는* 도구다. 요구사항 문서가 아니라 테스트라는
뜻이다.

## 3. 가치 — 무엇이 실제로 만들어지는가

추상적으로 말하면 "상호운용성" 이지만, 그것이 실제로 얼마짜리인지는 오래 굴러간
1차 사례를 봐야 한다. 유전자 온톨로지(GO)가 가장 잘 문서화된 사례다.

[The Gene Ontology knowledgebase in 2023 (GENETICS 224(1):iyad031)](https://doi.org/10.1093/genetics/iyad031)
에 따르면 GO 지식베이스는 세 부분으로 되어 있다.

1. **온톨로지** — 유전자 산물의 기능적 특성을 서술하는 항(term)들이 관계로 이어진
   **레이블 붙은 유향 비순환 그래프(DAG)**. 계층 구조와 비슷하지만 **다중 부모를
   허용**한다.
2. **어노테이션** — "이 유전자 산물이 이 기능적 특성을 갖는다" 는, **증거로 뒷받침된**
   문장.
3. **GO-CAM** — 여러 어노테이션을 정의된 관계로 이어 만든 분자 경로의 기계적 모델.

규모는 같은 논문이 보고한 수치로 basic edition 기준 **43,303 개 항**과 **88,099 개
관계**이고, 외부 온톨로지의 항까지 포함하면 **121,698 개 관계**다. (이 수치는 해당
릴리스 시점의 컨소시엄 자체 보고다 — §7 의 근거 한계를 참고.)

여기서 만들어지는 가치의 정체는 "용어집이 크다" 가 아니다. **종(species)을 넘어
비교가 되는 것**이다. 초파리에서 밝혀진 기능과 사람에서 밝혀진 기능을 같은 항으로
쓸 수 있으면, 각각의 실험 결과가 서로의 검색 대상이 된다. 다중 부모를 허용하는 DAG
구조는 하나의 기능이 여러 상위 범주에 동시에 속하는 생물학의 실제를 잃지 않고
표현하기 위한 선택이다.

기계 쪽 가치는 FAIR 원칙이 명시적으로 말한다. FAIR 는 사람 독자만이 아니라
**기계가 자동으로 찾아 쓰는 능력**을 강조하는 원칙 집합이고, 상호운용성 항목은
이렇게 적혀 있다.

> I1. (meta)data use a formal, accessible, shared, and broadly applicable language
> for knowledge representation.
> I2. (meta)data use vocabularies that follow FAIR principles.
> I3. (meta)data include qualified references to other (meta)data.
> — [Wilkinson et al., *The FAIR Guiding Principles*, Scientific Data 3:160018, 2016](https://doi.org/10.1038/sdata.2016.18)

I1 은 사실상 "형식 지식표현 언어를 쓰라" 는 요구이고, I2 는 "그 어휘 자체도 FAIR
해야 한다" 는 재귀 조건이다. 온톨로지가 만드는 가치는 이 두 줄이 충족될 때
**기계가 사람의 중재 없이 두 데이터셋을 잇는 것**으로 현금화된다.

## 4. 이력 — 두 겹으로 쌓인다

"어떤 이력으로 데이터를 쌓았나" 라는 질문은 사실 **두 개의 다른 질문**이다.
하나는 사실 한 줄의 출처, 다른 하나는 온톨로지 자신의 판(version) 이력이다.
둘을 섞으면 둘 다 못 쓴다.

### (a) 사실 한 줄마다 — 증거

GO 어노테이션은 각각 **증거 코드(evidence code)와 참조 문헌**을 달고 다닌다.
증거 코드는 그 문장이 실험으로 뒷받침되는지, 계통 추론인지, 저자 진술인지, 큐레이터
추론인지를 구분한다. 사용자는 **증거 유형과 검토 수준을 둘 다** 고려해야 한다고
논문이 명시한다.

이 원칙이 통계에까지 반영된 대목이 인상적이다. GO 2023 논문의 기여자 통계표는
`protein binding` 에 직접 붙은 어노테이션을 **따로 뺀 열로** 집계한다. 이유는
상호작용 상대에 대한 정보 없이는 그 항 자체가 거의 모든 단백질이 갖는 활성을
가리켜서 **정보량이 별로 없기 때문**이다. 이력이 부실한 사실은 지우는 게 아니라
**세는 방식을 달리한다** — 실무에 그대로 옮길 만한 태도다.

### (b) 온톨로지 자신 — 폐기하되 지우지 않는다

GO 는 항을 **삭제하지 않고** obsolete 시키거나 다른 항으로 merge 한다. 릴리스마다
추가·폐기·병합된 항의 수를 웹사이트에 보고하고, 논문은 2년치 변화를 축(molecular
function / cellular component / biological process)별로 표로 싣는다. 그 기간에
biological process 축에서는 **800 개가 넘는 항이 순감**했는데, 상당수가 용법의
불일치를 정리하는 전면 재검토의 결과다.

여기가 핵심이다. **삭제였다면 그 항을 참조하던 과거 어노테이션이 전부 고아가 된다.**
폐기 표시는 "이 항은 더는 쓰지 말라" 는 신호를 남기면서 과거 데이터의 해석 가능성을
보존한다. 온톨로지의 상태 전이에 되돌릴 수 없는 파괴가 없어야 하는 이유다.

### (c) 그 이력을 적는 표준 어휘

출처를 표현하는 W3C 표준은 PROV 계열이다. PROV-DM 은 서두에서 provenance 를
이렇게 정의한다.

> "Provenance is information about entities, activities, and people involved in
> producing a piece of data or thing, which can be used to form assessments about
> its quality, reliability or trustworthiness."
> — [PROV-DM: The PROV Data Model, W3C Recommendation, 2013](https://www.w3.org/TR/2013/REC-prov-dm-20130430/Overview.html)

[PROV-O](https://www.w3.org/TR/prov-o/) 는 이 모델을 OWL2 로 인코딩한 것으로, 출발점은
세 클래스(`prov:Entity`, `prov:Activity`, `prov:Agent`)와
`prov:wasGeneratedBy` · `prov:used` · `prov:wasDerivedFrom` · `prov:wasAttributedTo`
같은 관계들이다. 실무에서 특히 쓸모 있는 두 가지가 있다.

- **qualified 패턴** — `prov:qualifiedAssociation` 으로 관계 자체를 객체화해서
  `prov:hadPlan`(어떤 계획으로) 과 `prov:hadRole`(무슨 역할로) 을 붙일 수 있다.
  "누가 만들었나" 를 넘어 "무슨 절차로 만들었나" 가 기록된다.
- **bundle** — PROV-DM 의 6개 컴포넌트 중 4번은 bundle, 곧 **출처의 출처**를
  다루기 위한 장치다. 출처 기록 자체가 언제 누구에 의해 쓰였는지를 적을 수 있다.

FAIR 도 같은 것을 재사용성의 조건으로 못박는다 — **R1.2. (meta)data are associated
with detailed provenance.** 이력은 있으면 좋은 게 아니라 재사용의 전제다.

## 5. 한마디로 얼마나 쓸만한가 — 판정식

앞의 네 축을 하나의 술어로 접으면 이렇게 된다. $$T_O(t)$$ 를 시점 $$t$$ 의 온톨로지
공리 집합, $$Q$$ 를 역량질문 집합이라 하자.

$$\mathrm{coverage}(O, Q, t) \;=\;
\frac{\bigl|\{\, q \in Q \;:\; T_O(t) \cup T_{\mathrm{ground}}(t) \models q \,\}\bigr|}{|Q|}$$

**한 단어로 답하면 온톨로지의 쓸만함은 "역량(competency)" 이다.** 크기도, 항의 수도,
형식화 수준도 아니다. 다만 이 지표를 쓸 때 반드시 함께 적어야 할 단서가 셋 있다.

1. **분모가 거짓말을 할 수 있다.** $$Q$$ 가 빈약하면 통과율은 쉽게 100% 가 된다.
   Grüninger–Fox 가 역량질문을 **계층화**하라고 한 이유이고, 단순 조회만으로 이루어진
   $$Q$$ 를 잘 설계된 온톨로지의 증거로 인정하지 않은 이유다. 지표를 보고할 때는
   $$Q$$ 의 구성과 출처를 같이 보고해야 한다.
2. **완전성은 조건부다.** 같은 논문은 역량질문의 답이 완전해지는 조건 $$\Phi$$ 를
   명시한 **completeness theorem** 을 요구한다. "답이 나온다" 와 "답이 전부다" 는
   다른 주장이다.
3. **$$t$$ 인자를 지우지 말 것.** $$O$$ 도 바뀌고 $$Q$$ 도 바뀐다. 작년의 통과율은
   올해의 승인 근거가 아니다.

## 6. 상태기계 — 목적과 품질이 맞기까지

앞 글에서 데이터 상태를 `raw → conformed → purpose-bound(P) → serving-approved(P)`
로 적었다. 온톨로지도 같은 모양의 상태를 갖는데, **인자가 $$Q$$ 로 바뀐다.**

| 상태 | 뜻 | 다음 상태로 가는 게이트 |
|---|---|---|
| `draft` | 용어가 모이는 중, 근거 없음 | motivating scenario 와 informal $$Q$$ 가 문서로 존재 |
| `cq-bound(Q)` | 모든 용어가 $$Q$$ 의 어느 질문에 대응됨 | 형식 $$Q$$ 가 entailment/consistency 문제로 적힘 |
| `released(v, Q)` | 판이 고정되고 $$\mathrm{coverage}$$ 가 측정됨 | 완전성 조건 $$\Phi$$ 가 명시됨 |
| `deprecated(term)` | 쓰지 말 것, 다만 해석은 가능 | 대체 항이 지정됨 (merge 대상) |
| `retired(v)` | 그 판으로는 더 서비스하지 않음 | 옛 판이 조회 가능하게 보존됨 |

핵심은 `released` 가 **인자를 두 개 받는다**는 점이다. 같은 온톨로지가 $$Q_1$$
(예: 정산 대사 질문 집합)에 대해서는 competent 이고 $$Q_2$$ (예: 이상거래 탐지 질문
집합)에 대해서는 incompetent 일 수 있다. 앞 글의 스냅샷 하나가
`purpose-bound(사기탐지)` 이면서 동시에 `quarantined(신용평가)` 일 수 있던 것과 정확히
같은 구조다. 그리고 `deprecated` 가 `deleted` 가 아니라는 점이 GO 가 30년 가까이
축적을 잃지 않은 이유다.

## 7. 실무에서 반복되는 네 가지 안티패턴

1. **역량질문 없이 만든 온톨로지.** 리뷰가 취향 논쟁이 된다. 어떤 항을 넣자/빼자는
   주장을 기각할 근거가 없어서 온톨로지는 단조 증가만 한다.
2. **분류체계를 온톨로지라 부르기.** SKOS 문서가 짚듯 시소러스는 공리도 사실도
   주장하지 않는다. 이름만 바꾸면 형식 semantics 를 기대하는 다운스트림이 조용히
   틀린 추론을 한다.
3. **항을 삭제하기.** 폐기·병합이 아니라 삭제하면 그 항을 참조하던 과거 사실이
   해석 불가능해진다. 되돌릴 수 없는 유일한 전이를 기본값으로 두는 셈이다.
4. **근거 없는 어노테이션.** 증거 코드와 참조가 없으면 그 문장은 나중에 검증할
   수도, 철회할 수도 없다. GO 가 정보량 낮은 어노테이션을 통계에서 분리해 세는
   태도가 최소한의 대안이다.

## 정리

- ❌ "우리는 도메인 온톨로지를 구축했다."
- ✅ "우리는 역량질문 $$Q$$ 를 정의했고, 현재 판 $$v$$ 의 $$\mathrm{coverage}(O, Q, t)$$ 는
  이 값이며, 완전성 조건 $$\Phi$$ 는 이렇고, 모든 사실은 증거 코드를 달고 있으며,
  폐기된 항은 삭제하지 않았다."

앞 문장은 반증할 수 없고 뒤 문장은 반증할 수 있다. 온톨로지의 상태가 목적과 품질에
맞았는지는, 그 문장이 반증 가능해지는 시점에 비로소 물어볼 수 있는 질문이다.

## References

**1차·공식 (표준·사양)**

- [SKOS Simple Knowledge Organization System Reference, W3C Recommendation, 18 August 2009](https://www.w3.org/TR/skos-reference/)
- [PROV-O: The PROV Ontology, W3C Recommendation, 30 April 2013](https://www.w3.org/TR/prov-o/)
- [PROV-DM: The PROV Data Model, W3C Recommendation, 30 April 2013](https://www.w3.org/TR/2013/REC-prov-dm-20130430/Overview.html)

**동료심사·학술 1차 문헌**

- [Gruber, T. R. *A Translation Approach to Portable Ontology Specifications.* Knowledge Acquisition 5(2):199–220, 1993](https://tomgruber.org/writing/ontolingua-kaj-1993.pdf)
- Studer, R., Benjamins, V. R. & Fensel, D. *Knowledge Engineering: Principles and Methods.* Data & Knowledge Engineering 25(1–2):161–197, 1998. [DOI: 10.1016/S0169-023X(97)00056-6](https://doi.org/10.1016/S0169-023X(97)00056-6)
- [Grüninger, M. & Fox, M. S. *Methodology for the Design and Evaluation of Ontologies.* IJCAI-95 Workshop on Basic Ontological Issues in Knowledge Sharing, Montreal, 1995](http://stl-fs.mie.utoronto.ca/publications/gruninger-ijcai95.pdf)
- [Wilkinson, M. D. et al. *The FAIR Guiding Principles for scientific data management and stewardship.* Scientific Data 3:160018, 2016](https://doi.org/10.1038/sdata.2016.18)

**컨소시엄 자체 보고 (수치의 출처)**

- [The Gene Ontology Consortium. *The Gene Ontology knowledgebase in 2023.* GENETICS 224(1):iyad031, 2023](https://doi.org/10.1093/genetics/iyad031)

### 근거의 한계

- §3 의 GO 규모 수치(43,303 항 / 88,099 관계 / 외부 포함 121,698 관계)와 §4 의
  "biological process 축 800 개 이상 순감" 은 **컨소시엄이 자기 릴리스에 대해 보고한
  값**이다. 동료심사 저널에 실린 논문이지만 제3자가 독립적으로 재집계한 수치는 아니다.
  GO 는 릴리스 통계를 공개하므로 시점을 고정하면 재현 가능하다.
- 이 글은 "온톨로지 기반 통합이 다른 통합 방식보다 낫다" 는 **성능 우열을 주장하지
  않는다.** 그런 주장을 뒷받침할 중립적인 헤드투헤드 비교 근거를 찾지 못했고,
  §5 의 $$\mathrm{coverage}$$ 도 서로 다른 온톨로지를 비교하는 지표가 아니라 **하나의
  온톨로지를 자신이 선언한 $$Q$$ 에 대해 판정하는** 지표다.
- $$\mathrm{competent}(O, Q, t)$$ 와 §6 의 상태표는 위 1차 자료들을 필자가 하나의
  틀로 정리한 것이지, 표준이나 논문에 그 형태로 규정된 표기가 아니다.
