---
layout: post
title: "온톨로지의 표현수준 — 목적이 스펙트럼의 어디에 세울지를 정한다"
date: 2026-09-03 18:58:36 +0900
categories: [AI, 지식표현]
tags: [온톨로지, 온톨로지스펙트럼, SKOS, OWL, RDF, 지식표현]
---

"우리 온톨로지는 아직 부족하다"는 말을 자주 듣는다. 그런데 부족하다는 게 무슨 뜻이냐고
되물으면 대답이 갈린다. 어휘가 적다는 뜻인가, 계층이 얕다는 뜻인가, 아니면 기계가
모순을 스스로 못 잡아낸다는 뜻인가. 이 셋은 전혀 다른 결핍이고, 채우는 방법도 다르다.
**"제대로 된 온톨로지"라는 단일한 목표는 없다. 목적마다 필요한 표현수준이 다르고, 표현수준을
올릴수록 모델링 비용과 추론 비용이 같이 오른다.** 이 글은 그 스펙트럼이 어디서 왔고, 층위마다
무엇을 얻고 무엇을 지불하는지, 그래서 목적이 어떻게 층위를 결정하는지를 정리한다.

---

## 1. 스펙트럼은 패널 토론에서 나왔다

"온톨로지"라는 단어가 가리키는 대상이 사람마다 다르다는 문제는 학계에서도 오래된 불만이었다.
1999년 AAAI Ontologies 패널에서 Lehman, McGuinness, Uschold, Welty 네 명이 각자 경험한
"온톨로지"라 불리는 산출물이 서로 얼마나 다른지 비교하다가, 그 다양성을 하나의 축 위에
배열할 수 있다는 데 동의했다. 이게 **온톨로지 스펙트럼**의 출발점이다.

Lassila와 McGuinness는 이 아이디어를 2001년 기술보고서 *The Role of Frame-Based
Representation on the Semantic Web*에서 처음 활자화했고,[^lassila-mcguinness] McGuinness는
2003년 *Spinning the Semantic Web*의 챕터 "Ontologies Come of Age"에서 스펙트럼을 층위별로
정리해 확장했다.[^mcguinness2003] 스펙트럼이 늘어놓는 것은 어휘의 **크기**가 아니라
어휘가 지원하는 **추론의 종류**다. 낮은 층위에서 높은 층위로 갈수록, 같은 어휘로부터
기계가 자동으로 끌어낼 수 있는 것이 많아진다.

층위를 약한 의미론에서 강한 의미론 순으로 배열하면 대략 이렇다.

| 층위 | 예 | 기계가 이걸로 무엇을 할 수 있나 |
|---|---|---|
| 통제 어휘 (controlled vocabulary) | 카탈로그 태그 목록 | 정해진 용어로만 라벨을 붙였는지 검사 |
| 분류체계 (taxonomy) | 상품 카테고리 트리 | 상위/하위 카테고리 탐색 |
| 시소러스 (thesaurus) | broader/narrower/related 관계 | 동의어·연관어로 검색 확장 |
| 비형식 is-a | "고양이는 포유류다" (자연어 주석 수준) | 사람이 읽는 계층도 |
| 형식 is-a | RDFS `subClassOf` | 클래스 상속에 따른 자동 분류(subsumption) |
| 프레임 (속성) | 클래스마다 속성·값 타입 정의 | 속성 상속, 타입 검사 |
| 값 제약 (value restriction) | OWL `someValuesFrom` / cardinality | "이 속성의 값은 반드시 이 타입이어야 한다"는 제약 위반 탐지 |
| 일반 논리 제약 | OWL 공리, disjointness, 역관계 | 모순(비일관성) 자동 탐지, 미기술 사실의 함의(entailment) 도출 |

핵심은 이거다. **하위 층위에서 상위 층위로 올라가는 건 "더 정교하게 적는다"가 아니라
"기계에게 더 많은 권한을 준다"는 뜻이다.** 값 제약과 논리 제약부터는 사람이 안 적은 것도
기계가 참으로 추론하거나, 반대로 서로 모순되는 두 문장을 자동으로 잡아낼 수 있다. 그
권한은 공짜가 아니다.

---

## 2. 표준이 실제로 이 스펙트럼을 두 겹으로 나눠 놨다

이 스펙트럼이 이론에 머물지 않는 이유는, W3C가 스펙트럼의 서로 다른 지점을 서로 다른
표준으로 굳혀놨기 때문이다.

**낮은 층위 — SKOS.** Simple Knowledge Organization System은 시소러스·분류체계·통제
어휘를 RDF로 표현하기 위한 W3C 권고안이다. 개념(concept)에 URI를 부여하고, `broader`
/ `narrower` / `related`로 느슨한 계층과 연관을 표현하며, 여러 언어의 라벨을 붙일 수
있다.[^skos] SKOS는 의도적으로 **형식 논리를 강제하지 않는다.** "A가 B보다 broader다"는
관계일 뿐 상속 규칙이 아니고, 모순 검사도 없다. 도서관 분류표·전거 데이터·용어집처럼
애초에 "정확한 계층"보다 "사람이 합의한 대략의 구조"가 목적인 자료에 맞춘 설계다.

**높은 층위 — OWL 2.** Web Ontology Language는 클래스·프로퍼티·개체에 **형식
의미론**을 부여해서, 적혀 있지 않은 사실을 추론해내거나 모순을 검출할 수 있게
만든다.[^owl2] 그런데 OWL 2 안에서도 표현력은 또 갈린다. 전체 OWL 2 DL(SROIQ 기반)은
표현력이 가장 크지만 추론이 계산적으로 무겁다. 그래서 W3C는 표현력을 의도적으로 깎은
세 프로파일을 따로 권고했다.[^owl2profiles]

- **OWL 2 EL** — 모든 표준 추론이 다항 시간에 끝나도록 설계. 아주 큰 온톨로지에
  적합.
- **OWL 2 QL** — 개념 질의를 관계형 DB의 SQL로 그대로 풀어낼 수 있게 설계. 대량의
  개체를 다루는 데이터 접근에 적합.
- **OWL 2 RL** — 규칙 기반 추론으로 확장성과 표현력을 절충.

이 셋의 존재 자체가 스펙트럼의 요점을 증명한다. **"표현력을 최대로" 가 기본값이
아니다. 표준조차 표현력을 깎는 버전을 따로 만들어서, 목적에 맞게 고르라고 권고한다.**

---

## 3. 그래서 목적이 층위를 어떻게 결정하는가

표현수준을 올리는 데는 두 가지 청구서가 따라온다. 하나는 **모델링 비용** — 시소러스는
관계 세 종류만 정하면 되지만, OWL 온톨로지는 클래스마다 제약과 공리를 사람이 다
써야 한다. 다른 하나는 **추론 비용** — 표현력이 늘수록 "이게 모순인가"를 계산하는
난이도가 는다. OWL 2가 EL/QL/RL을 따로 둔 이유가 정확히 이 두 번째 청구서 때문이다.

이 청구서를 감당할 가치가 있는지는 순전히 목적에 달려 있다.

1. **탐색·브라우징이 목적인가?** → 통제 어휘·분류체계로 충분하다. 사용자가 카테고리를
   클릭해서 좁혀가는 데는 형식 논리가 필요 없다.
2. **검색어 확장·용어 매핑이 목적인가?** → 시소러스(SKOS) 층위. "정산"과
   "settlement"가 related라는 사실만 있으면 되지, 그게 논리적으로 동치라는 증명은
   필요 없다.
3. **데이터가 규격을 지켰는지 기계가 검사해야 하는가?** → 형식 is-a·프레임 층위.
   RDFS 상속과 타입 제약 정도면 스키마 검증에 충분하다.
4. **"이 두 사실이 동시에 참일 수 없다"를 기계가 스스로 잡아내야 하는가?** → 값
   제약·일반 논리 제약, 즉 OWL이 필요하다. 여기서부터는 사람이 일일이 모순을
   찾는 대신 추론기가 찾는다. 대신 그 추론기를 계산 가능한 범위로 유지하려면
   EL/QL/RL 같은 프로파일 선택이 따라붙는다.

거꾸로 말하면, 탐색이 목적인데 OWL 공리를 쌓는 건 낭비고, 모순 탐지가 목적인데
SKOS로 버티는 건 애초에 SKOS가 못 하는 일을 시키는 것이다. **표현수준을 목적보다
높게 잡는 것도, 낮게 잡는 것도 같은 종류의 실수다.**

---

## 4. LLM 시대에 이 축이 다시 중요해진 이유

두 가지 흐름이 이 스펙트럼을 다시 실무 전면으로 끌고 왔다.

**첫째, 구조화 출력·함수 호출 스키마가 사실상 낮은 층위의 온톨로지 역할을 한다.**
LLM에게 JSON 스키마로 함수 인자를 정의하는 일은, 타입과 필수 필드를 정하는
프레임 층위의 표현이다. 다만 이 스키마 대부분은 값 제약·논리 제약까지는 거의
안 간다 — 그럴 필요가 없기 때문이다. 목적이 "이 함수를 호출할 때 인자가 맞는
타입인가"에서 멈추면, 스펙트럼도 거기서 멈추는 게 맞다.

**둘째, LLM으로 지식그래프를 자동 추출하는 접근(GraphRAG류)은 태생적으로 스펙트럼의
낮은 층위에서 시작한다.** 이전 글["AI 온톨로지 구축 — 그래프와 벡터DB, 두 관점이 각각
무엇을 포기하는가"](/2026/09/03/ontology-graph-vs-vector-db-two-lenses/)에서 다룬
`~/wiki` 사례가 정확히 이 문제였다. 엣지 108개가 전부 `references` 관계 하나였다는
건, 스펙트럼상 "비형식 is-a"에도 못 미치는 링크 목록 수준에 머물렀다는 뜻이다.
LLM이 원문에서 뽑아내는 엔티티·관계도 마찬가지로 대개 이 낮은 층위에서 시작하고,
값 제약이나 논리 제약까지 자동으로 채워주지 않는다. **표현력을 사람 대신 기계에게
맡긴다는 것과, 표현수준이 저절로 높아진다는 것은 다른 이야기다.** 어느 층위까지
자동 추출로 채우고 어디부터 사람이 검수할지를 정하는 것 자체가 목적에 달린 설계
결정이다.

같은 맥락에서 상태관리 쪽을 다룬 [이전
글](/2026/09/03/ai-ready-data-state-management/)의 `purpose-bound(P)` 개념도
이 축과 맞닿아 있다. 데이터가 목적 P에 대해 준비됐다는 판정과, 온톨로지가 목적
P에 필요한 표현수준을 갖췄다는 판정은 같은 질문의 두 얼굴이다 — **"이 자산이 지금
이 목적을 감당할 만큼 만들어져 있는가."**

---

## 5. 정리

스펙트럼의 요점은 "위로 올라갈수록 좋다"가 아니라 **"위로 올라갈수록 비싸고, 그
값을 목적이 요구할 때만 지불한다"**는 것이다. SKOS로 충분한 자리에 OWL을 앉히면
모델링 비용만 늘고 아무도 그 추론 기능을 쓰지 않는다. 반대로 모순 탐지가 필요한
자리에 통제 어휘만 있으면, 모순은 여전히 존재하고 그걸 찾는 일이 전부 사람에게
남는다.

그래서 온톨로지를 시작하기 전에 물어야 할 첫 질문은 "얼마나 정교하게 만들 것인가"가
아니라 **"이 어휘로 기계가 무엇을 자동으로 할 수 있어야 하는가"**다. 그 답이
스펙트럼에서의 위치를 정하고, 위치가 비용을 정한다.

---

## References

- Lassila, O., McGuinness, D. L. (2001). *The Role of Frame-Based Representation on
  the Semantic Web*. Technical Report KSL-01-02, Knowledge Systems Laboratory,
  Stanford University. Also published in *Electronic Transactions on Artificial
  Intelligence*, Vol. 6, No. 005 (2001).
  [Semantic Scholar](https://www.semanticscholar.org/paper/The-Role-of-Frame-Based-Representation-on-the-Web-Lassila-McGuinness/b06f1d74e3f02fa6694b9286427b7303fd4ffdfa)
- McGuinness, D. L. (2003). "Ontologies Come of Age." In D. Fensel, J. Hendler, H.
  Lieberman, W. Wahlster (eds.), *Spinning the Semantic Web: Bringing the World
  Wide Web to Its Full Potential*. MIT Press.
  [MIT Press](https://mitpress.mit.edu/9780262562126/spinning-the-semantic-web/)
- Gruber, T. R. (1993). "A Translation Approach to Portable Ontology
  Specifications." *Knowledge Acquisition*, 5(2), 199–220. (온톨로지를 "명시적
  개념화 명세"로 정의한 원 논문.) <https://tomgruber.org/writing/ontolingua-kaj-1993.pdf>
- W3C, *SKOS Simple Knowledge Organization System Reference*, W3C Recommendation,
  2009-08-18. <https://www.w3.org/TR/skos-reference/>
- W3C, *OWL 2 Web Ontology Language Document Overview (Second Edition)*, W3C
  Recommendation, 2012-12-11. <https://www.w3.org/TR/owl2-overview/>
- W3C, *OWL 2 Web Ontology Language Profiles (Second Edition)*, W3C Recommendation,
  2012-12-11. <https://www.w3.org/TR/owl2-profiles/>

**근거의 한계.** 스펙트럼 층위의 명칭과 순서는 Lassila–McGuinness(2001)와
McGuinness(2003)를 따랐다. 이후 여러 저자가 이 스펙트럼을 더 세분화한 버전을
제시했는데, 그런 확장판은 이 글에서 1차 검증하지 못해 인용하지 않았다. "표현수준을
올리면 추론 비용이 커진다"는 주장은 OWL 2 프로파일의 존재 자체로 뒷받침되지만, 이
글은 EL/QL/RL 각각의 정확한 계산 복잡도 클래스(예: PTime, LogSpace 등급의 세부
경계)를 검증된 1차 출처 없이 단정하지 않았다. 관련 선행 글: [AI 온톨로지 구축 —
그래프와 벡터DB, 두 관점이 각각 무엇을 포기하는가](/2026/09/03/ontology-graph-vs-vector-db-two-lenses/),
[AI ready data는 형용사가 아니다 — 목적성과 품질성으로 본 데이터
상태관리](/2026/09/03/ai-ready-data-state-management/)
