---
layout: post
title: "[SE100 #079] 범위·일정·품질의 트레이드오프"
date: 2026-10-11 17:07:03 +0900
categories: [software-engineering]
tags: [se100, project-management, iron-triangle, scope-management, internal-quality]
---

소프트웨어 공학 100 주제 시리즈의 79번째 글이다. (카테고리: 프로젝트 관리와 추정)

## 한 줄 요약

일정이 빠듯할 때 조절할 수 있는 손잡이는 범위, 일정, 비용(인력), 품질이다. 이 가운데 **범위가 가장 싸고 안전한 손잡이**이고, **내부 품질은 손잡이가 아니다.** 내부 품질을 깎으면 몇 주 안에 속도로 되갚게 된다.

## 왜 필요한가

프로젝트가 늦어질 때 실제로 벌어지는 일은 대개 이렇다. 날짜는 이미 공지됐고, 범위는 영업이 약속했고, 인력은 당장 늘릴 수 없다. 그러면 남은 손잡이는 하나, 아무도 공식적으로 결정하지 않은 품질이다. 테스트가 빠지고, 리뷰가 형식이 되고, "일단 하드코딩" 이 늘어난다.

이 결정은 회의록 어디에도 남지 않는다. 그래서 그 비용, 즉 다음 분기의 느려진 속도와 늘어난 장애도 누구의 결정 결과로도 기록되지 않는다. 트레이드오프를 명시적으로 다루는 목적은 이 **암묵적 품질 할인**을 막는 데 있다.

## 핵심 개념

### 철의 삼각형과 그 한계

프로젝트 관리에는 비용·일정·품질(또는 범위)을 꼭짓점으로 하는 "철의 삼각형" 이라는 오래된 그림이 있다. 한 꼭짓점을 당기면 다른 꼭짓점이 움직인다는 뜻이다. Roger Atkinson 은 1999년 [International Journal of Project Management 논문](https://doi.org/10.1016/S0263-7863%2898%2900069-6)의 제목에서 비용·시간·품질을 "두 개의 최선의 추측과 하나의 현상" 이라 부르며 **다른 성공 기준을 받아들일 때** 라고 주장했다. 삼각형을 지켰다고 성공한 프로젝트는 아니라는 것이다.

Kent Beck 은 *Extreme Programming Explained*(Addison-Wesley, 1999)에서 이를 네 변수로 정리했다. **비용, 시간, 품질, 범위.** 외부에서 셋을 정하면 팀이 나머지 하나를 정한다. 그리고 XP 는 범위를 조절 변수로 삼는다.

### 품질은 두 종류다

Martin Fowler 는 [TradableQualityHypothesis](https://martinfowler.com/bliki/TradableQualityHypothesis.html)에서 Beck 을 따라 품질을 나눈다.

| 구분 | 무엇 | 사용자가 볼 수 있나 | 거래 대상인가 |
|---|---|---|---|
| 외부 품질 | UI 의 쾌적함, 결함 수 등 | 볼 수 있다 | **가능.** "A 를 더 쓰기 쉽게 할까, B 를 추가할까" 는 정당한 선택 |
| 내부 품질 | 코드 구조, 설계, 테스트 | 볼 수 없다 | 거래하면 곧 손해 |

Fowler 는 [Is High Quality Software Worth the Cost?](https://martinfowler.com/articles/is-quality-worth-cost.html)에서 근거를 이렇게 든다. 내부 품질이 높으면 다음 기능을 추가하는 비용이 낮아진다. 개발자들은 품질 낮은 코드가 **몇 주 안에** 자신을 크게 느리게 만든다고 느낀다. 그래서 내부 품질을 깎아 속도를 얻을 수 있는 구간은 아주 짧다. [DesignStaminaHypothesis](https://martinfowler.com/bliki/DesignStaminaHypothesis.html)에서도 같은 주장을 한다. 설계를 소홀히 해 얻는 이득이 사라지는 "설계 손익분기선" 은 대부분의 사람이 생각하는 것보다 훨씬 낮아서, 대개 몇 달이 아니라 **몇 주**라는 것이다.

이 점은 [기술 부채]({% post_url 2026-10-10-cs300-200-technical-debt %}) 글의 이자 모형과 같은 이야기다. 짧게 끝나는 일회성 작업이라면 품질을 거래할 수 있지만, 몇 주 넘게 이어질 제품이라면 거래가 아니라 손해다.

### 스크럼의 답: 품질은 고정, 범위는 협상

[스크럼 가이드 2020](https://scrumguides.org/scrum-guide.html)은 스프린트 중 규칙을 이렇게 적는다.

- 스프린트 목표를 위태롭게 하는 변경은 하지 않는다.
- **품질은 떨어뜨리지 않는다(Quality does not decrease).**
- 범위는 더 알게 되면서 제품 책임자와 명확히 하고 **다시 협상할 수 있다.**

완료의 정의(Definition of Done)를 충족하지 못한 항목은 릴리스는커녕 스프린트 리뷰에서 보여 줄 수도 없다. 품질 하한을 규칙으로 못 박아 두고, 압력은 범위가 받게 하는 구조다.

### 일정 고정, 범위 가변 — Shape Up

Basecamp 의 [Shape Up](https://basecamp.com/shapeup/1.2-chapter-03)은 이 원칙을 계획 단계로 끌어올린다. 먼저 이 문제에 얼마의 시간을 쓸 용의가 있는지, 즉 **식욕(appetite)** 을 정하고 그 안에 맞는 해법을 설계한다. 책은 이를 추정과 반대라고 설명한다. 추정은 설계에서 출발해 숫자로 끝나고, 식욕은 숫자에서 출발해 설계로 끝난다. 원칙의 이름은 **"고정된 시간, 가변 범위(fixed time, variable scope)"** 다. 저자는 책을 예로 든다. 마감 일주일 전이면 오타를 고칠지 새 절을 추가할지 골라야 하고, 오타 투성이 책을 내고 싶지 않으니 범위를 줄인다. 마감이 없으면 이 결정을 하지 않고, 범위가 고정이면 품질 문제를 고칠 시간이 없다.

### 일정 압축의 가격

범위를 지키고 날짜를 당기려면 사람을 늘려야 한다. 그 비용은 선형이 아니다. COCOMO II(SE100 #072)의 [모형 정의 매뉴얼](http://web.archive.org/web/20090206135819/http://sunset.usc.edu:80/csse/research/COCOMOII/cocomo2000.0/CII_modelman2000.0.pdf)에서 일정 승수 SCED 는 공칭 일정의 85% 로 당길 때 1.14, 75% 로 당길 때 **1.43** 이다. 공칭보다 늘린 일정(130%, 160%)은 1.00 으로 노력을 줄여 주지 않는다. Brooks 의 법칙(SE100 #003)은 이미 늦은 프로젝트에 인력을 넣으면 더 늦어진다고 경고한다.

```python
# 같은 범위, 일정만 압축할 때 (COCOMO II.2000 SCED 승수)
nominal_pm, nominal_months = 465.3, 25.9          # SE100 #072 예제의 100 KSLOC 프로젝트
for pct, em in ((100, 1.00), (85, 1.14), (75, 1.43)):
    pm, months = nominal_pm * em, nominal_months * pct / 100
    print(f"일정 {pct:3d}% → {months:4.1f}개월, 노력 {pm:5.0f} PM, 평균 {pm / months:4.1f}명")
```

```
일정 100% → 25.9개월, 노력   465 PM, 평균 18.0명
일정  85% → 22.0개월, 노력   530 PM, 평균 24.1명
일정  75% → 19.4개월, 노력   665 PM, 평균 34.3명
```

일정을 25% 당기면 평균 인원은 두 배 가까이 된다. 그만큼 사람을 바로 구할 수 있는 조직은 드물다.

### 속도와 안정성은 반대가 아니다

"빨리 하려면 품질을 희생해야 한다" 는 직관에 대해 [DORA](https://dora.dev/guides/dora-metrics-four-keys/)는 자신들의 연구가 **속도와 안정성이 트레이드오프가 아님**을 거듭 보여 줬다고 쓴다. 대부분의 팀에서 두 지표는 상관관계가 있고, 상위 팀은 다섯 지표 모두에서 잘하고 하위 팀은 모두에서 못한다. 같은 페이지는 Dave Farley 의 말을 인용한다. 장기적으로 진짜 트레이드오프는 "더 좋은 소프트웨어를 더 빨리" 와 "더 나쁜 소프트웨어를 더 느리게" 사이에 있다(SE100 #070 에서 다룬다).

## 실무 적용

### 트레이드오프 협상 순서

일정 압박이 오면 이 순서로 손잡이를 검토한다.

| 순서 | 손잡이 | 질문 | 비고 |
|---|---|---|---|
| 1 | 범위 | 무엇을 빼거나 나중으로 미룰 수 있나? 각 기능의 최소 버전은? | 가장 싸다. MoSCoW 우선순위(SE100 #017) |
| 2 | 출시 방식 | 일부 사용자에게 먼저 낼 수 있나? | 피처 플래그(SE100 #057) |
| 3 | 일정 | 날짜를 옮길 수 있나? 옮기면 무엇을 잃나? | 날짜의 진짜 근거를 확인 |
| 4 | 인력 | 지금 넣으면 언제부터 도움이 되나? | 늦은 투입은 역효과 |
| ✕ | 내부 품질 | — | 협상 대상에서 제외. 완료의 정의로 고정 |

### 범위를 "자르는" 방법

범위 축소는 기능을 통째로 빼는 것만이 아니다.

```
"주문 내역 조회" 기능을 줄이는 여러 방법
├─ 기간 축소     : 전체 기간 → 최근 3개월만
├─ 경로 축소     : 모든 결제 수단 → 카드만, 나머지는 다음 증분
├─ 자동화 축소   : 환불 자동 처리 → 1차 버전은 운영자가 관리 화면에서 처리
├─ 품질 속성 조정 : 실시간 반영 → 5분 지연 허용 (사용자 합의된 외부 품질)
└─ 플랫폼 축소   : 웹·앱 동시 → 웹 먼저
```

마지막에서 두 번째 줄을 보자. 외부 품질(지연 허용치)은 사용자와 합의하면 정당하게 조절할 수 있다. 조절할 수 없는 것은 그 기능을 만드는 코드의 테스트와 구조다.

### 결정을 기록한다

```
[트레이드오프 결정 기록] 2026-10-xx
상황: 85% 예측 완료일이 목표보다 2주 늦음 (SE100 #077 예측)
선택: 범위 축소 — 쿠폰 기능을 v1.1 로 이동
제외한 대안: 날짜 이동(행사일 고정), 인력 투입(온보딩 3주 필요)
영향: 쿠폰 사용 고객 약 X% 가 1차 출시에서 혜택 없음 → 고객센터 공지
결정자: 제품 책임자, 스폰서
```

아키텍처 결정 기록(SE100 #025)과 같은 형식이다. 반년 뒤 "왜 쿠폰이 빠졌냐" 는 질문에 답할 수 있다.

## 흔한 오해와 함정

- **"품질도 다른 것처럼 거래할 수 있다."** 외부 품질은 그렇다. 내부 품질은 몇 주 안에 속도로 청구된다.
- **"범위는 고정이고 협상할 수 없다."** 범위는 대개 기능 목록이 아니라 문제 해결의 한 방식이다. 같은 문제를 더 작은 해법으로 푸는 길이 거의 언제나 있다.
- **"일정을 늘리면 비용이 준다."** COCOMO 의 SCED 표에서 늘린 일정의 승수는 1.00 이다. 늘어진 일정은 관리 비용으로 상쇄된다.
- **"늦었으니 사람을 넣자."** 투입 효과가 나기까지 걸리는 시간과 의사소통 경로 증가(SE100 #078)를 먼저 계산한다.
- **"품질을 높이면 느려진다."** DORA 의 결과는 반대 방향을 가리킨다. 작은 배치, 자동화된 테스트, 빠른 피드백이 속도와 안정성을 함께 올린다.

## 확인 문제

1. Beck 의 네 변수는 무엇이며, XP 는 그중 무엇을 조절 변수로 쓰는가?
2. 외부 품질과 내부 품질 중 정당하게 거래할 수 있는 것은? 그 이유는?
3. 스크럼 가이드 2020 이 스프린트 중 고정하는 것과 협상 가능하다고 한 것은?
4. Shape Up 의 "식욕" 이 추정과 다른 점은?
5. COCOMO II 기준으로 일정을 공칭의 75% 로 당기면 노력은 몇 배가 되는가?

### 풀이

1. 비용, 시간, 품질, 범위. XP 는 범위를 조절 변수로 쓴다.
2. 외부 품질. 사용자가 직접 인식하는 속성이라 다른 기능과 비교해 우선순위를 정할 수 있다. 내부 품질은 다음 변경의 비용을 정하므로, 깎으면 몇 주 안에 속도 저하로 돌아온다.
3. 고정: 스프린트 목표를 위태롭게 하지 않음, 품질을 떨어뜨리지 않음. 협상 가능: 범위(제품 책임자와 명확히 하고 재협상).
4. 추정은 설계에서 출발해 숫자(기간)로 끝나고, 식욕은 숫자(쓸 시간)에서 출발해 그 안에 맞는 설계로 끝난다.
5. 1.43배.

## 더 읽을거리 (References)

- Roger Atkinson, [Project management: cost, time and quality, two best guesses and a phenomenon, its time to accept other success criteria](https://doi.org/10.1016/S0263-7863%2898%2900069-6), *International Journal of Project Management* 17(6), 1999
- Martin Fowler, [TradableQualityHypothesis](https://martinfowler.com/bliki/TradableQualityHypothesis.html), [DesignStaminaHypothesis](https://martinfowler.com/bliki/DesignStaminaHypothesis.html), [Is High Quality Software Worth the Cost?](https://martinfowler.com/articles/is-quality-worth-cost.html)
- Ryan Singer, [Shape Up — Set Boundaries](https://basecamp.com/shapeup/1.2-chapter-03), Basecamp
- Ken Schwaber, Jeff Sutherland, [The 2020 Scrum Guide](https://scrumguides.org/scrum-guide.html)
- DORA, [DORA's software delivery performance metrics](https://dora.dev/guides/dora-metrics-four-keys/)
- USC CSE, [COCOMO II Model Definition Manual v2.1](http://web.archive.org/web/20090206135819/http://sunset.usc.edu:80/csse/research/COCOMOII/cocomo2000.0/CII_modelman2000.0.pdf) (인터넷 아카이브 사본)
- Kent Beck, *Extreme Programming Explained: Embrace Change*, Addison-Wesley, 1999 (서지 정보)
