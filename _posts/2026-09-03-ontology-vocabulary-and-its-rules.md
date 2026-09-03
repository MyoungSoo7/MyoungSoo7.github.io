---
layout: post
title: "온톨로지 구축, 어휘와 그 어휘가 지켜야 할 규칙으로 나눠보면"
date: 2026-09-03 18:56:00 +0900
categories: [AI, 지식표현]
tags: [온톨로지, RDFS, OWL, SHACL, SWRL, 지식그래프]
---

온톨로지를 "지식을 표현하는 체계"라고 정의하면 구축 방법이 안 보인다. 뭘 먼저 만들어야 하는지, 뭐가 끝났다는 신호인지 이 정의에서는 아무것도 안 나온다.

그런데 W3C가 실제로 나눠 쓰는 표준들을 따라가 보면 구분선이 하나 뚜렷하게 보인다. **어휘(vocabulary)** — 무엇을 말할 수 있는가 — 와 **그 어휘가 지켜야 할 규칙** — 그 말이 언제 참이거나 유효한가 — 이 서로 다른 명세, 다른 언어, 다른 표준화 트랙으로 나뉘어 있다는 것이다. 이 둘을 하나로 뭉쳐서 생각하면 온톨로지 구축이 막연해지고, 갈라서 보면 각 단계가 무엇을 해야 하는지가 구체적으로 잡힌다.

## 1. 어휘 층위 — RDFS는 "서술하는 자원"만 준다

RDF Schema(RDFS)는 클래스와 프로퍼티를 정의하는 가장 기본적인 층위다. W3C 명세는 RDFS를 이렇게 규정한다.

> "The language defined in this specification consists of a collection of RDF resources that can be used to describe other RDF resources."[^rdfs]

핵심은 그다음이다. `rdfs:domain`과 `rdfs:range`로 프로퍼티의 정의역·치역을 적어놔도, 명세는 그걸 애플리케이션이 어떻게 써야 하는지 정하지 않는다.

> "RDF Schema provides a mechanism for describing this information, but does not say whether or how an application should use it."[^rdfs]

즉 어휘 층위가 주는 건 **서술 수단**이지 **강제 수단**이 아니다. `범주:주문`이라는 클래스와 `취소함`이라는 프로퍼티를 선언할 수는 있지만, 그 선언 자체는 "취소함의 domain이 범주:주문이 아닌 데이터가 들어오면 무슨 일이 일어나야 하는가"에 대해 아무 답도 주지 않는다.

## 2. 규칙 층위는 사실 두 갈래로 갈린다

여기서부터가 온톨로지 구축에서 제일 자주 헷갈리는 지점이다. "어휘에 규칙을 씌운다"는 한 문장처럼 보이지만, 실제로는 목적이 정반대인 두 갈래 표준으로 나뉘어 있다.

### (a) 추론 규칙 — 새 사실을 이끌어낸다

OWL 2는 클래스·프로퍼티·개체·데이터값 위에 공리(axiom)를 얹는 언어다.

> "OWL 2 ontologies provide classes, properties, individuals, and data values"[^owl2]

OWL과 그 확장인 SWRL(Semantic Web Rule Language)의 규칙은 **열린 세계 가정** 아래에서 동작한다. SWRL은 스스로를 이렇게 규정한다.

> "The proposal extends the set of OWL axioms to include Horn-like rules."[^swrl]

규칙의 의미는 조건부 함의다.

> "whenever the conditions specified in the antecedent hold, then the conditions specified in the consequent must also hold"[^swrl]

이건 검증이 아니라 **도출**이다. 전건이 참이면 후건도 참이어야 한다고 선언할 뿐, 데이터에 후건이 빠져 있다고 해서 에러가 나지 않는다. 추론기는 빠진 사실을 채워 넣거나(entailment), 모순이 없으면 그냥 넘어간다. "적혀 있지 않다"와 "거짓이다"는 OWL/SWRL 세계에서 다른 말이다.

### (b) 검증 규칙 — 데이터가 어휘를 지켰는지 확인한다

바로 이 지점 때문에 W3C는 2017년에 완전히 별도의 권고안을 냈다. SHACL이다.

> "a language for validating RDF graphs against a set of conditions"[^shacl]

SHACL은 검증 규칙(shapes graph)과 검증 대상(data graph)을 구조적으로 분리한다.

> "Validation takes a data graph and a shapes graph as input and produces a validation report"[^shacl]

그리고 SHACL은 OWL/RDFS의 추론 의미론을 전제하지 않는다.

> "SHACL uses the RDF and RDFS vocabularies, but full RDFS inferencing is not required"[^shacl]

즉 SHACL은 **닫힌 세계**에 가깝게 동작한다 — "이 데이터그래프에 실제로 존재하는 것"만 놓고 "취소함의 domain이 범주:주문인데 이 인스턴스는 아니다"를 즉시 위반으로 보고한다. OWL 추론기라면 그냥 새로운 사실로 흡수하고 넘어갔을 상황이다.

## 3. 왜 이 구분이 실무에서 중요한가

어휘(RDFS/OWL 클래스·프로퍼티)만 정의하고 검증 규칙(SHACL)을 따로 두지 않으면, "규칙을 어겼다"는 신호 자체가 생기지 않는다. OWL의 domain/range 공리는 위반을 보고하는 장치가 아니라 추론을 위한 전제다. 열린 세계 가정 위에서는 모순되지 않는 한 뭐든 받아들여지기 때문에, 온톨로지 저작 도구나 데이터 파이프라인이 "이 값이 스키마를 어겼다"고 사람에게 알려주려면 별도의 검증 계층이 필요하다 — 그게 SHACL이 별도 표준으로 나온 이유다.

거꾸로 검증 규칙만 촘촘히 짜고 어휘를 안 정리하면, 규칙이 무엇을 규제하는지조차 이름 붙일 수 없다. `범주:주문`이 뭘 가리키는지 클래스로 먼저 고정돼 있어야 그 위에 SHACL shape을 얹을 대상이 생긴다.

## 4. 구축 순서 — 어휘는 질문에서 나온다

그럼 어휘를 어떻게 정할 것인가. Grüninger와 Fox의 1995년 온톨로지 설계·평가 방법론은 **competency question**(역량 질문)이라는 개념을 도입했다 — 온톨로지가 반드시 답할 수 있어야 하는 질문들을 형식논리로 먼저 적어두고, 그 질문에 답하는 데 필요한 용어만 어휘로 채택한 뒤, 그 어휘가 실제로 질문에 답할 수 있는지로 온톨로지를 평가하는 절차다.[^gruninger]

Stanford의 "Ontology Development 101" 가이드도 같은 순서를 실무 절차로 제시한다 — 도메인과 범위를 정하고, 온톨로지가 답해야 할 전형적인 질문 목록을 만들고, 그다음에야 클래스와 프로퍼티를 정의한다.[^ontology101]

규칙을 먼저 설계하고 어휘를 거기 끼워 맞추는 순서로는 이 절차가 성립하지 않는다. 질문 → 어휘 → (추론 규칙과 검증 규칙) 순서가 뒤집히면, 나중에 "이 프로퍼티가 왜 있어야 하는지" 되짚을 근거가 없어진다.

## 5. 정리

온톨로지 구축을 "지식표현"이라는 한 덩어리로 보면 다음에 뭘 해야 할지 알 수 없다. 두 층위, 그리고 규칙 안의 두 갈래로 쪼개면 각 단계가 무엇을 산출해야 하는지가 분명해진다.

1. **어휘** — RDFS/OWL 클래스·프로퍼티. "무엇을 말할 수 있는가." 강제력 없음.
2. **추론 규칙** — OWL 공리·SWRL. 열린 세계 가정. "무엇을 새로 도출할 수 있는가."
3. **검증 규칙** — SHACL. 데이터그래프 대 shapes 그래프. "실제 데이터가 어휘를 지켰는가."

그리고 이 세 가지를 채우는 순서는, 표준 자체가 아니라 방법론 쪽 문헌이 답을 준다 — 규칙보다 어휘가 먼저고, 어휘보다 "무엇을 답할 수 있어야 하는가"라는 질문이 먼저다.

---

### References

[^rdfs]: [RDF Schema 1.1 — W3C Recommendation](https://www.w3.org/TR/rdf-schema/)
[^owl2]: [OWL 2 Web Ontology Language Document Overview — W3C Recommendation](https://www.w3.org/TR/owl2-overview/)
[^swrl]: [SWRL: A Semantic Web Rule Language Combining OWL and RuleML — W3C Member Submission](https://www.w3.org/Submission/SWRL/)
[^shacl]: [Shapes Constraint Language (SHACL) — W3C Recommendation](https://www.w3.org/TR/shacl/)
[^gruninger]: Grüninger, M., Fox, M.S. (1995). *Methodology for the Design and Evaluation of Ontologies*. IJCAI'95 Workshop on Basic Ontological Issues in Knowledge Sharing. [Semantic Scholar](https://www.semanticscholar.org/paper/Methodology-for-the-Design-and-Evaluation-of-Gruninger/497abc0ddace6a7772a5f5a3edb3d7b751476755)
[^ontology101]: Noy, N.F., McGuinness, D.L. *Ontology Development 101: A Guide to Creating Your First Ontology*. Stanford University. [PDF](https://protege.stanford.edu/publications/ontology_development/ontology101.pdf)
