---
layout: post
title: "[SE100 #050] 탐색적 테스팅과 테스트 오라클 문제"
date: 2026-10-11 17:01:50 +0900
categories: [software-engineering]
tags: [se100, software-testing, exploratory-testing, test-oracle, metamorphic-testing]
---

소프트웨어 공학 100 주제 시리즈의 50번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

모든 테스트에는 두 질문이 있다. **무엇을 시도할 것인가**(입력·시나리오)와 **결과가 맞는지 어떻게 아는가**(오라클). 탐색적 테스팅은 첫 질문을 실행 중에 배우면서 답하는 방식이고, 테스트 오라클 문제는 두 번째 질문이 생각보다 훨씬 어렵다는 사실이다. 자동화가 막히는 지점은 대개 입력 생성이 아니라 오라클이다.

## 왜 필요한가

이 카테고리의 앞선 글들은 대부분 "무엇을 시도할 것인가" 를 체계화했다. 동등 분할과 경계값(SE100 #042), 커버리지(SE100 #043), 속성 기반 생성(SE100 #046)이 그렇다. 그런데 두 장면에서 이 접근이 한계에 닿는다.

1. **명세가 빈약하거나 계속 바뀐다.** 미리 짠 스크립트는 작성자가 예상한 위험만 확인한다. 새 기능의 이상한 상호작용은 스크립트 바깥에 있다.
2. **정답을 계산할 방법이 없다.** 검색 결과의 "관련성", 추천의 "적절함", 수치 시뮬레이션의 결과, 기계 학습 모델의 출력은 기대값을 미리 적어 둘 수 없다.

첫째는 탐색적 테스팅이, 둘째는 오라클 기법들이 다룬다. 둘 다 **사람의 판단을 어떻게 구조화하고 어디까지 자동화하는가** 의 문제다.

## 핵심 개념

### 탐색적 테스팅의 정의와 기원

James Bach 는 자기 사이트의 [Exploratory Testing](https://www.satisfice.com/exploratory-testing) 페이지에서, 이 용어를 만든 사람은 자기가 아니라 1980년대의 Cem Kaner 이고, Kaner 는 John Tukey 가 만든 "탐색적 자료 분석" 에서 영감을 받았다고 적는다. Bach 는 80년대 말~90년대 초에 스크립트를 따르지 않는 테스터들이 버그를 더 잘 찾는다는 것을 관찰하고 그 이유를 연구했다고 한다.

ISTQB [Foundation Level 강의계획서 v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) 4.4.2절의 정의는 다음과 같다.

> 탐색적 테스팅에서는 테스터가 테스트 대상에 대해 배우는 동안 테스트를 **동시에 설계·실행·평가** 한다.

같은 절은 탐색적 테스팅이 명세가 적거나 부적절할 때, 테스트에 시간 압박이 클 때 유용하고, 더 형식적인 기법을 보완하는 데도 쓰이며, 테스터가 경험·도메인 지식·분석력·호기심·창의성을 갖출수록 효과적이라고 정리한다.

Bach 는 같은 페이지에서 더 근본적인 주장을 한다. 전문적인 테스팅은 **본질적으로 탐색적** 이어서 "탐색적 테스팅" 이라는 말은 상당 부분 중복이고, 실제 테스팅은 늘 탐색적인 쪽(비형식적, 테스터가 순간순간 결정)과 스크립트 쪽(형식적, 다른 사람이나 이전 시점에 결정)의 **혼합** 이라는 것이다.

```
  스크립트형 ◀──────────────────────────────▶ 탐색형
  절차를 미리 정함                         실행하며 다음 행동 결정
  재현성·감사 추적 강함                      학습·새 위험 발견 강함
  예: 회귀 체크리스트     예: 차터 기반 세션    예: 자유 탐색
```

### 세션 기반 테스트 관리(SBTM)

"자유롭게 탐색" 은 관리하기 어렵다. Bach 형제(James, Jon)는 Hewlett-Packard 에서 실천한 방식을 바탕으로 [Session-Based Test Management](https://www.satisfice.com/download/session-based-test-management) 를 썼고, 이를 산출물 중심 관리의 대안인 **활동 중심** 테스트 관리라고 설명한다. ISTQB 강의계획서는 세션 기반 접근을 이렇게 요약한다.

| 요소 | 내용 |
|---|---|
| 타임박스 | 정해진 시간 안에서 탐색 |
| 차터(charter) | 테스트 목표를 담아 세션을 이끄는 문서 |
| 세션 시트 | 수행한 단계와 발견을 기록 |
| 디브리핑 | 세션 후 테스터와 이해관계자가 결과를 논의 |

### 테스트 오라클 문제

**오라클** 은 주어진 입력에 대해 관찰된 동작이 올바른지 판정하는 수단이다.

Weyuker 의 [On Testing Non-Testable Programs](https://doi.org/10.1093/comjnl/25.4.465) (The Computer Journal, 1982) 는 테스트에서 흔히 깔려 있는 가정, 즉 테스터나 외부 장치가 출력이 올바른지 **정확히 판정할 수 있다** 는 가정을 검토했다. 오라클이 존재하지 않거나 출력이 맞는지 판정하는 데 비상하게 많은 시간이 드는 프로그램을 **테스트 불가능(non-testable)** 하다고 정의하고, 많은 경우 이 가정이 현실적이지 않다고 결론 내렸다.

Barr, Harman, McMinn, Shahbaz, Yoo 의 서베이 [The Oracle Problem in Software Testing: A Survey](https://doi.org/10.1109/TSE.2014.2372785) (IEEE TSE, 2015) 는 입력이 주어졌을 때 올바른 동작과 잠재적으로 틀린 동작을 구별하는 과제를 **테스트 오라클 문제** 라 부르고, 오라클 자동화가 더 넓은 테스트 자동화를 가로막는 **병목** 이라고 진단한다. 오라클 자동화 기법으로 모델링, 명세, 계약 기반 개발, 메타모픽 테스팅을 들고, 이들이 모두 부족할 때 최종 오라클은 비형식적 명세·기대·규범·도메인 지식을 가진 **사람** 이라고 정리한다.

| 오라클 종류 | 예 | 강점 | 한계 |
|---|---|---|---|
| 명세된 기대값 | `assertEquals(5000, price(12))` | 정확 | 미리 계산할 수 있어야 함 |
| 모델·참조 구현 | 느리지만 단순한 구현과 비교 | 입력을 대량 생성 가능 | 참조 구현도 틀릴 수 있음 |
| 계약·단언 | 사전/사후 조건, 불변식 | 운영 중에도 검사 | 부분적 정확성만 |
| 암묵적 오라클 | 크래시, 예외, 타임아웃, 메모리 누수 | 명세 없이 자동 | 기능 오류는 못 잡음 |
| 메타모픽 관계 | 입력 변환과 출력 관계 | 정답 없이 검사 | 관계를 찾아야 함 |
| 사람 | 탐색적 테스트, 리뷰 | 맥락 판단 | 비싸고 일관성 낮음 |

### 메타모픽 테스팅

Chen 외의 서베이 [Metamorphic Testing: A Review of Challenges and Opportunities](https://doi.org/10.1145/3143561) (ACM Computing Surveys, 2018) 는 메타모픽 테스팅을 테스트 케이스 생성과 결과 검증 **양쪽** 에 쓰는 접근으로 설명한다. 중심은 **메타모픽 관계**, 즉 여러 입력과 그 출력들 사이에 반드시 성립해야 하는 대상 함수의 성질이다. 개별 출력의 정답은 몰라도, 출력들 **사이의 관계** 는 알 수 있다는 점을 이용한다.

### 사람 오라클을 구조화하기: HICCUPPS

자동화할 수 없는 판단도 막연한 "감" 으로 둘 필요는 없다. Michael Bolton 의 [FEW HICCUPPS](https://www.developsense.com/blog/2012/07/few-hiccupps/) 는 문제를 알아채는 근거를 **일관성** 원칙으로 정리한다. 제품은 다음과 일관되어야 한다.

| 글자 | 일관성의 대상 |
|---|---|
| History | 같은 시스템의 과거 버전 |
| Image | 조직이 보여 주려는 이미지·브랜드·평판 |
| Comparable products | 비교할 만한 다른 제품·시스템·대안 알고리즘 |
| Claims | 명세, 설계 문서, 매뉴얼, 회의 발언 등 중요한 사람들의 주장 |
| Users' desires | 합리적인 사용자가 원할 만한 것 |
| Product | 같은 시스템 안의 비교 가능한 요소들 |
| Purpose | 사람들이 쓸 명시적·암묵적 용도 |
| Statutes | 관련 법규와 규제 |

Bolton 은 이것들이 모두 **휴리스틱** 이라고 강조한다. 틀릴 수 있고 맥락에 의존하며, 불일치가 곧 문제임을 보장하지 않는다. 판정은 결국 사람이 여러 원칙과 가치 판단을 함께 적용해 내린다.

## 실무 적용

### 1. 차터 템플릿

```markdown
## 차터: 쿠폰 + 부분 환불 상호작용 탐색
- 목표: 쿠폰 적용 주문의 부분 환불 시 금액·포인트·재고 정합성 위험 찾기
- 범위: 웹 결제, 관리자 환불 화면 / 제외: 정기결제
- 타임박스: 60분
- 오라클: 정산 규칙 문서(Claims), 이전 버전 동작(History), 관리자 화면과 사용자 화면 금액 일치(Product)
- 기록: 시도한 시나리오, 발견한 문제, 남은 질문, 다음 차터 후보
- 디브리핑: 결제팀 담당자와 15분
```

차터는 "무엇을 탐색하나" 와 함께 **"무엇으로 판정하나"(오라클)** 를 적게 하는 것이 핵심이다. 오라클이 없는 탐색은 "이상한데?" 에서 멈춘다.

### 2. 메타모픽 테스트로 정답 없는 출력 검사

```python
import math, random

def search(items, query, category=None):
    hits = [i for i in items if query in i["title"]]
    return [i for i in hits if category is None or i["cat"] == category]

items = [{"title": t, "cat": c} for t, c in
         [("red shoe", "shoes"), ("red hat", "hats"), ("blue shoe", "shoes")]]

# 관계 1: 필터를 추가한 결과는 필터 없는 결과의 부분집합이다
base = search(items, "red")
assert all(x in base for x in search(items, "red", category="shoes"))

# 관계 2: sin(π − x) = sin(x). 개별 sin(x) 의 정답값은 몰라도 된다
for _ in range(1000):
    x = random.uniform(-10, 10)
    assert math.isclose(math.sin(math.pi - x), math.sin(x), abs_tol=1e-9)
```

실제 검색 엔진에서는 "결과 순위가 정답인가" 를 판정할 수 없지만 "필터를 더하면 결과가 늘어나지 않는다", "같은 질의를 두 번 하면 같은 결과", "무관한 문서를 색인에 추가해도 상위 결과의 상대 순서는 유지" 같은 관계는 검사할 수 있다. 속성 기반 테스트(SE100 #046)와 결합하면 입력 생성과 판정이 모두 자동화된다.

### 3. 탐색에서 회귀로

탐색 세션에서 찾은 문제는 고친 뒤 **스크립트화된 회귀 테스트** 로 옮긴다. 탐색은 새 위험을 찾는 데, 자동화는 이미 아는 위험을 지키는 데 쓴다.

## 흔한 오해와 함정

- **탐색적 테스팅 = 계획 없는 테스트.** ISTQB 정의와 SBTM 모두 목표(차터), 시간 제한, 기록, 디브리핑을 둔다. 즉흥이 아니라 실행 중에 설계를 갱신하는 방식이다.
- **자동화가 탐색을 대체한다.** 자동화된 체크는 이미 적어 둔 오라클만 확인한다. 아무도 기대값을 적지 않은 문제는 사람이 탐색 중에 처음 발견한다.
- **오라클을 당연하게 여긴다.** "테스트 실패 = 버그" 가 아니다. 오라클(기대값, 참조 구현, 명세)도 틀릴 수 있다. 테스트가 실패하면 SUT 와 오라클을 모두 의심한다.
- **암묵적 오라클로 만족한다.** 크래시·예외가 없다는 것은 최소한의 확인일 뿐이다. 금액이 틀린 영수증은 아무 예외도 내지 않는다.

## 확인 문제

1. ISTQB 의 탐색적 테스팅 정의에서 "동시에" 가 강조하는 것은 무엇인가?
2. Weyuker 가 말한 "테스트 불가능한 프로그램" 의 두 조건은?
3. 머신 러닝 기반 추천 API 에 쓸 수 있는 오라클을 세 종류 이상 제시하라.
4. 메타모픽 테스팅이 오라클 문제를 완화하는 원리는?
5. 탐색 세션 후 디브리핑에서 무엇을 다뤄야 하는가?

### 풀이

1. 테스트 설계, 실행, 결과 평가가 별도 단계로 나뉘지 않고 한 흐름 안에서 이루어지며, 앞 단계의 결과로 배운 것이 즉시 다음 설계에 반영된다는 점이다.
2. 오라클이 존재하지 않거나, 출력이 올바른지 판정하는 데 비상하게 많은 시간이 드는 경우다.
3. 암묵적 오라클(오류·타임아웃 없음, 응답 스키마 준수), 계약·불변식(추천 항목은 재고가 있고 이미 구매한 상품은 제외), 메타모픽 관계(같은 사용자·같은 시점 요청은 같은 결과, 무관한 상품 추가가 상위 순서를 뒤집지 않음), 이전 버전과의 비교(History), 사람 판단(차터 기반 탐색 세션)
4. 개별 출력의 정답을 몰라도, 입력을 정해진 방식으로 바꿨을 때 출력들 사이에 반드시 성립해야 할 관계는 알 수 있다. 그 관계의 위반을 결함 신호로 삼는다.
5. 차터 목표 대비 무엇을 했는지, 발견한 문제와 그 판정 근거(오라클), 남은 질문과 위험, 다음 세션 차터 후보, 회귀 테스트로 옮길 항목이다.

## 더 읽을거리 (References)

- James Bach, [Exploratory Testing](https://www.satisfice.com/exploratory-testing), satisfice.com
- James Bach, Jon Bach, [Session-Based Test Management](https://www.satisfice.com/download/session-based-test-management)
- ISTQB, [Certified Tester Foundation Level Syllabus v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) (PDF), 4.4.2절
- E. J. Weyuker, [On Testing Non-Testable Programs](https://doi.org/10.1093/comjnl/25.4.465), The Computer Journal 25(4), 1982
- E. T. Barr, M. Harman, P. McMinn, M. Shahbaz, S. Yoo, [The Oracle Problem in Software Testing: A Survey](https://doi.org/10.1109/TSE.2014.2372785), IEEE TSE 41(5), 2015
- T. Y. Chen 외, [Metamorphic Testing: A Review of Challenges and Opportunities](https://doi.org/10.1145/3143561), ACM Computing Surveys 51(1), 2018
- Michael Bolton, [FEW HICCUPPS](https://www.developsense.com/blog/2012/07/few-hiccupps/), DevelopSense, 2012
- Elisabeth Hendrickson, *Explore It!: Reduce Risk and Increase Confidence with Exploratory Testing*, Pragmatic Bookshelf, 2013 (서지 정보)
