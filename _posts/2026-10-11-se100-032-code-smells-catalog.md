---
layout: post
title: "[SE100 #032] 코드 스멜 카탈로그 — 무엇이 냄새인가"
date: 2026-10-11 16:59:56 +0900
categories: [software-engineering]
tags: [se100, code-quality, code-smells, refactoring, maintainability]
---

소프트웨어 공학 100 주제 시리즈의 32번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

코드 스멜은 "버그" 도 "규칙 위반" 도 아니고, **더 깊은 설계 문제가 있을지 모른다는 표면 신호**다. 카탈로그의 가치는 이름을 붙여 팀이 같은 말을 쓰게 하고, 각 냄새에서 어떤 리팩터링으로 가는지 길을 알려 주는 데 있다.

## 왜 필요한가

리팩터링의 기법은 [클린 코드와 리팩터링]({% post_url 2026-10-10-cs300-189-clean-code-and-refactoring %})에서 다뤘다. 남는 질문은 **언제, 어디를** 고치느냐다. "이 코드 좀 이상한데" 라는 감각만으로는 리뷰에서 설득이 안 되고, 우선순위도 정할 수 없다.

스멜 카탈로그는 이 감각에 이름을 준다. "이 클래스는 Divergent Change 냄새가 난다" 라고 말하면 상대는 "변경 이유가 여러 개라 쪼개야 할 수도 있다" 는 맥락까지 함께 받는다. 동시에 카탈로그는 위험하기도 하다. 냄새를 규칙으로 오해하면 도구가 낸 숫자에 맞춰 멀쩡한 코드를 뜯어고치게 된다.

## 핵심 개념

### 원전의 정의

Martin Fowler 의 [CodeSmell](https://martinfowler.com/bliki/CodeSmell.html)(2006)은 이렇게 정의한다.

> 코드 스멜은 대개 시스템의 더 깊은 문제에 대응하는 표면적 징후다. 이 용어는 Kent Beck 이 내 Refactoring 책을 도우면서 처음 만들었다.

같은 글은 두 가지 미묘한 점을 짚는다.

1. 냄새는 정의상 **빨리 알아챌 수 있어야** 한다. 긴 메서드처럼 훑어보기만 해도 보이는 것.
2. 냄새가 **항상 문제를 뜻하지는 않는다.** 어떤 긴 메서드는 그냥 괜찮다. 냄새는 문제 자체가 아니라 더 들여다보라는 지표다.

그리고 좋은 냄새의 예로 Data Class(데이터만 있고 행위가 없는 클래스)를 든다. "이 클래스에 어떤 행위가 있어야 하지?" 를 묻게 만들기 때문이다.

### 카탈로그: Refactoring 2판의 이름들

Fowler 의 *Refactoring: Improving the Design of Existing Code* 2판(Addison-Wesley, 2018) 3장은 Kent Beck 과 함께 쓴 냄새 목록이다. 1판(1999)에 비해 Mysterious Name, Global Data, Mutable Data, Loops, Repeated Switches, Insider Trading 등이 새로 들어오거나 이름이 바뀌었다. 2판의 이름을 성격별로 묶으면 다음과 같다(묶음은 이 글의 정리다).

| 묶음 | 냄새 |
|---|---|
| 이해를 막는 것 | Mysterious Name, Comments(탈취제로 쓰인 주석), Long Function |
| 커지는 것 | Large Class, Long Parameter List, Data Clumps, Primitive Obsession |
| 변경을 막는 것 | Divergent Change, Shotgun Surgery, Global Data, Mutable Data |
| 결합이 지나친 것 | Feature Envy, Message Chains, Middle Man, Insider Trading |
| 불필요한 것 | Duplicated Code, Lazy Element, Speculative Generality, Temporary Field, Data Class |
| 구조를 잘못 쓴 것 | Repeated Switches, Loops, Refused Bequest, Alternative Classes with Different Interfaces |

### 학계의 분류: Mäntylä 의 다섯 무리

평평한 목록은 관계가 안 보인다. Mika Mäntylä 등은 2003년 ICSM 에서 [냄새 분류 체계와 초기 실증 연구](https://doi.org/10.1109/ICSM.2003.1235447)를 발표했고, 저자가 공개한 [분류 페이지](https://mmantyla.github.io/BadCodeSmellsTaxonomy)는 1판 목록을 다섯 무리로 나눈다.

| 무리 | 공통점 | 예 |
|---|---|---|
| Bloaters | 조금씩 자라서 다룰 수 없이 커짐 | Long Method, Large Class, Primitive Obsession, Long Parameter List, Data Clumps |
| Object-Orientation Abusers | 객체지향 설계를 제대로 활용하지 못함 | Switch Statements, Temporary Field, Refused Bequest |
| Change Preventers | 변경과 클래스의 1:1 관계가 깨짐 | Divergent Change, Shotgun Surgery, Parallel Inheritance Hierarchies |
| Dispensables | 없어도 되는 것 | Lazy Class, Data Class, Duplicate Code, Dead Code, Speculative Generality |
| Couplers | 결합도 관련 | Feature Envy, Inappropriate Intimacy, Message Chains, Middle Man |

이 분류의 실용적 의미는 **처방의 방향**이 무리마다 같다는 점이다. Bloater 는 쪼개고, Dispensable 은 지우고, Coupler 는 책임을 옮기고, Change Preventer 는 변경 축에 맞춰 경계를 다시 긋는다.

### 짝으로 이해해야 하는 냄새

```
Divergent Change                     Shotgun Surgery
  한 모듈 ← 여러 종류의 변경             한 종류의 변경 → 여러 모듈
  ┌──────────────┐                     ┌────┐ ┌────┐ ┌────┐
  │ OrderService │ ← DB 바뀜           │ A  │ │ B  │ │ C  │ ← 세율 바뀜
  │              │ ← 세율 바뀜          └────┘ └────┘ └────┘
  │              │ ← 알림 채널 바뀜
  └──────────────┘
  처방: 변경 이유별로 쪼갠다              처방: 흩어진 것을 한곳에 모은다
```

Feature Envy 와 Middle Man 도 짝이다. 남의 데이터를 너무 많이 만지면 행위를 옮기고(Move Function), 옮기다 보면 위임만 하는 중간자가 생기는데 그때는 중간자를 없앤다(Remove Middle Man). 한쪽을 고치다 반대쪽 냄새를 만들 수 있으므로 "적당한 지점" 을 찾는 것이 핵심이다.

### 냄새에서 리팩터링으로

[refactoring.com 카탈로그](https://refactoring.com/catalog/)의 이름으로 대표적인 경로를 정리한다.

| 냄새 | 우선 시도할 리팩터링 |
|---|---|
| Long Function | Extract Function, Split Phase, Replace Loop with Pipeline |
| Long Parameter List / Data Clumps | Introduce Parameter Object, Preserve Whole Object |
| Primitive Obsession | Replace Primitive with Object |
| Feature Envy | Move Function |
| Shotgun Surgery | Move Function, Combine Functions into Class, Inline Class |
| Repeated Switches | Replace Conditional with Polymorphism |
| Message Chains | Hide Delegate |
| Middle Man | Remove Middle Man |
| Mutable Data / Global Data | Encapsulate Variable, Encapsulate Collection |

### 냄새는 언제 생기는가

흔한 믿음은 "처음엔 깨끗했는데 유지보수하면서 점점 썩는다" 이다. Tufano 등의 [When and Why Your Code Starts to Smell Bad](https://doi.org/10.1109/ICSE.2015.59)(ICSE 2015)는 여러 생태계의 오픈소스 프로젝트 200개의 변경 이력(커밋 50만 건 이상)을 분석하고 냄새를 들여온 커밋 9,164건을 수작업으로 살폈다. 초록은 그 결과가 "냄새는 진화 작업 중에 들어온다" 는 통념과 **대체로 반대**라고 요약한다. 즉 처음 작성할 때부터 냄새를 품고 태어나는 코드가 많다는 뜻이고, 리뷰의 가장 싼 개입 시점이 **새 코드가 들어올 때**라는 근거가 된다.

## 예제

### Data Clumps + Primitive Obsession

Fowler 는 [DataClump](https://martinfowler.com/bliki/DataClump.html)에서 `start` 와 `end` 가 늘 같이 다니면 범위(range) 객체가 되고 싶어 하는 것이라고 말한다.

```kotlin
// Before: 같은 세 값이 늘 함께 다니고, 검증은 호출부마다 흩어져 있다
fun reserve(roomId: String, startDate: LocalDate, endDate: LocalDate, guests: Int) { ... }
fun quote(roomId: String, startDate: LocalDate, endDate: LocalDate): Long { ... }
fun overlaps(aStart: LocalDate, aEnd: LocalDate, bStart: LocalDate, bEnd: LocalDate) =
    aStart < bEnd && bStart < aEnd
```

```kotlin
// After: Introduce Parameter Object → 행위를 객체로 옮긴다
data class StayPeriod(val start: LocalDate, val end: LocalDate) {
    init { require(start < end) { "start must be before end" } }
    val nights: Long get() = ChronoUnit.DAYS.between(start, end)
    fun overlaps(other: StayPeriod) = start < other.end && other.start < end
}

fun reserve(roomId: RoomId, period: StayPeriod, guests: Int) { ... }
fun quote(roomId: RoomId, period: StayPeriod): Long { ... }
```

`overlaps` 와 `nights` 가 자연스럽게 새 객체로 이동했다. Fowler 가 말한 "흥미로운 일은 새 객체로 옮길 행위를 찾기 시작할 때 일어난다" 가 바로 이 지점이다.

### 리뷰용 냄새 점검표

리뷰에서 냄새를 지적할 때는 **냄새 이름 + 관찰 + 질문** 형식이 방어적 반응을 줄인다.

```
[Shotgun Surgery?] 이번 PR 에서 배송비 정책을 바꾸려고 파일 5개를 고쳤습니다.
다음에 정책이 또 바뀌면 같은 5곳을 고쳐야 할까요? 정책 계산을 한곳에 모으면 어떨까요?
```

### 도구로 찾기

PMD 의 [Design 규칙 묶음](https://docs.pmd-code.org/latest/pmd_rules_java_design.html)에는 `GodClass`, `DataClass`, `ExcessiveParameterList`, `LawOfDemeter` 같은 냄새 대응 규칙이 있다. 이런 규칙의 임계값은 관례일 뿐이므로, 차단보다는 **후보 목록**으로 쓰고 사람이 판정하는 편이 맞다.

## 흔한 오해와 함정

- **"냄새 = 고쳐야 할 것."** 원전 정의부터 "항상 문제는 아니다" 를 포함한다. 냄새는 조사의 출발점이다.
- **"Comments 는 냄새니까 주석을 지우자."** 원래 뜻은 나쁜 코드를 덮는 **탈취제로서의** 주석이다. 왜(why)를 설명하는 주석은 냄새가 아니다(SE100 #039 에서 다룬다).
- **도구 경고 수를 KPI 로 삼기.** 숫자를 줄이려고 메서드를 기계적으로 쪼개면 이름만 늘고 이해는 어려워진다. 측정과 목표의 함정은 SE100 #033 에서 다룬다.
- **아무도 건드리지 않는 코드의 냄새 청소.** 변경되지 않는 코드의 냄새는 이자가 거의 없다([기술 부채]({% post_url 2026-10-10-cs300-200-technical-debt %}) 참고). 자주 바뀌는 곳부터 고친다.
- **반대 냄새로 넘어가기.** Feature Envy 를 없애다 Middle Man 을, Large Class 를 쪼개다 Shotgun Surgery 를 만든다. 고친 뒤 짝 냄새를 확인한다.

## 확인 문제

1. Fowler 의 정의에서 냄새가 "빨리 알아챌 수 있어야 한다" 와 "항상 문제는 아니다" 를 동시에 강조하는 이유는?
2. Divergent Change 와 Shotgun Surgery 의 차이를 "변경" 과 "모듈" 의 대응 관계로 설명하라.
3. Mäntylä 의 다섯 무리 중 Change Preventers 가 깨뜨리는 원칙은 무엇인가?
4. Tufano 등의 연구 결과가 코드 리뷰 전략에 주는 함의는?

### 풀이

1. 빨리 보여야 누구나(초심자도) 후보를 찾을 수 있고, 항상 문제가 아니기 때문에 찾은 뒤에는 더 깊이 들여다보는 판단이 필요하다. 탐지는 싸게, 판정은 신중하게 하라는 뜻이다.
2. Divergent Change 는 한 모듈이 여러 종류의 변경 때문에 계속 바뀌는 것(1 모듈 : N 변경 이유), Shotgun Surgery 는 한 종류의 변경이 여러 모듈을 동시에 고치게 하는 것(1 변경 : N 모듈)이다.
3. 클래스와 가능한 변경이 1:1 대응해야 한다는 원칙. 한 종류의 변경은 한 클래스에만 영향을 줘야 한다.
4. 냄새의 상당수가 진화 과정이 아니라 처음 작성 시점에 들어온다면, 새 코드가 들어오는 리뷰 시점이 가장 싸고 효과적인 개입 지점이다.

## 더 읽을거리 (References)

- Martin Fowler, [CodeSmell](https://martinfowler.com/bliki/CodeSmell.html), 2006
- Martin Fowler, [DataClump](https://martinfowler.com/bliki/DataClump.html), 2006
- Martin Fowler, *Refactoring: Improving the Design of Existing Code*, 2nd ed., Addison-Wesley, 2018 (서지 정보)
- [Refactoring Catalog](https://refactoring.com/catalog/), refactoring.com
- M. V. Mäntylä, J. Vanhanen, C. Lassenius, "A taxonomy and an initial empirical study of bad smells in code", ICSM 2003, [DOI](https://doi.org/10.1109/ICSM.2003.1235447)
- M. V. Mäntylä, [A Taxonomy for "Bad Code Smells"](https://mmantyla.github.io/BadCodeSmellsTaxonomy) (저자 페이지)
- M. Tufano et al., "When and Why Your Code Starts to Smell Bad", ICSE 2015, [DOI](https://doi.org/10.1109/ICSE.2015.59)
- PMD, [Java Design rules](https://docs.pmd-code.org/latest/pmd_rules_java_design.html)
