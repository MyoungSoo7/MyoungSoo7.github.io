---
layout: post
title: "[SE100 #035] 불변성과 부수효과 관리"
date: 2026-10-11 16:59:59 +0900
categories: [software-engineering]
tags: [se100, code-quality, immutability, side-effects, functional-core, value-object]
---

소프트웨어 공학 100 주제 시리즈의 35번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

불변성은 "아무것도 바꾸지 않는다" 가 아니라 **바뀌는 지점을 좁히고 눈에 보이게 하는 설계 전략**이다. 값은 불변으로, 부수효과는 시스템 가장자리로 모으면 코드는 추론하기 쉬워지고 동시성 버그가 들어설 자리가 줄어든다.

## 왜 필요한가

순수 함수와 불변성의 기초는 [함수형 프로그래밍 — 불변성과 순수 함수]({% post_url 2026-10-10-cs300-031-functional-programming-immutability-pure-functions %})에서 다뤘다. 이 글은 객체지향 코드베이스에서 그것을 **어디까지, 어떻게** 적용하는지를 다룬다.

가변 상태가 만드는 버그는 재현이 어렵다는 공통점이 있다.

- **별칭(aliasing)**: 두 객체가 같은 리스트를 참조하는데, 한쪽이 정렬하면 다른 쪽 화면 순서가 바뀐다.
- **해시 키 변형**: `HashSet` 에 넣은 객체의 필드를 바꾸면 그 객체를 다시 찾을 수 없다.
- **경쟁 조건**: 두 스레드가 같은 객체를 수정하면 결과가 실행 순서에 따라 달라진다.
- **숨은 부수효과**: 이름은 `getTotal()` 인데 내부에서 캐시와 로그 카운터를 바꾼다. 호출 순서를 바꾸는 리팩터링이 동작을 바꾼다.

## 핵심 개념

### 불변의 세 층위

| 층위 | 의미 | 예 |
|---|---|---|
| 참조 불변 | 변수가 다른 객체를 가리키지 못함 | Java `final`, Kotlin `val` |
| 얕은 불변 | 객체 자신의 필드는 못 바꿈, 필드가 가리키는 객체는 바뀔 수 있음 | Java record, JS `Object.freeze` |
| 깊은 불변 | 도달 가능한 모든 상태가 바뀌지 않음 | 불변 필드만으로 구성된 값 객체 |

가장 흔한 착각은 첫 층위를 셋째로 오해하는 것이다. [Kotlin 공식 문서](https://kotlinlang.org/docs/collections-overview.html)는 가변 컬렉션을 `val` 에 담아도 쓰기 연산은 여전히 가능하며, `val` 이 보호하는 것은 **참조**라고 명시한다. 같은 문서는 `List` 를 "읽기 전용(read-only)" 인터페이스라 부르는데, 읽기 전용 **뷰**를 통해서만 못 바꿀 뿐 같은 객체를 `MutableList` 로 가진 쪽은 바꿀 수 있다. MDN 은 [`Object.freeze`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/freeze)가 얕다(shallow)고 적는다.

Java 의 [`List.of` / `List.copyOf`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html)는 요소를 추가·삭제·교체할 수 없는 리스트를 만든다. 하지만 같은 문서가 경고하듯 **요소 자체가 가변이면** 리스트 내용이 바뀌어 보일 수 있다.

### 언어가 주는 도구

| 언어 | 도구 | 주의점 |
|---|---|---|
| Java 16+ | `record` ([JEP 395](https://openjdk.org/jeps/395)): "불변 데이터를 투명하게 운반하는" 클래스, 필드는 `private final` | 컴포넌트가 가변 컬렉션이면 방어적 복사 필요 |
| Kotlin | `val`, `data class` + `copy()`, 읽기 전용 컬렉션 인터페이스 | 읽기 전용 ≠ 불변 |
| Python | `@dataclass(frozen=True)`: 필드 대입 시 [`FrozenInstanceError`](https://docs.python.org/3/library/dataclasses.html) | 필드가 `list` 면 내부는 바뀜, `tuple`/`frozenset` 사용 |
| Rust | 기본이 불변, `mut` 은 명시. 한 시점에 [가변 참조 하나 또는 불변 참조 여러 개](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html) | 가변성을 금지하지 않고 **통제**한다 |

Joshua Bloch 의 *Effective Java* 3판(Addison-Wesley, 2018) 아이템 17 "변경 가능성을 최소화하라" 는 불변 클래스의 다섯 규칙을 제시한다. 상태를 바꾸는 메서드를 두지 않는다, 클래스를 확장할 수 없게 한다, 모든 필드를 `final` 로, 모든 필드를 `private` 으로, 가변 컴포넌트에 대한 접근을 독점한다(방어적 복사).

### 불변과 동시성

Java 언어 명세 [17.5절 final 필드 의미론](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.5)은 `final` 필드가 동기화 없이도 스레드 안전한 불변 객체를 구현하게 해 준다고 쓴다. 생성자가 끝난 뒤에야 참조를 볼 수 있는 스레드는 `final` 필드의 올바르게 초기화된 값을 보도록 보장된다. 단, 생성자 안에서 `this` 를 외부로 흘리면 이 보장이 깨진다. 불변 객체는 잠금 없이 공유할 수 있으므로 동시성 설계에서 가장 싼 안전장치다.

### 부수효과를 분리한다: 명령-질의 분리

Fowler 의 [CommandQuerySeparation](https://martinfowler.com/bliki/CommandQuerySeparation.html)은 Bertrand Meyer 가 만든 원칙을 소개한다. 메서드는 상태를 바꾸는 **명령**이거나 값을 돌려주는 **질의**여야 하며, 질의는 관찰 가능한 상태를 바꾸지 않아야 한다. 같은 글은 스택의 `pop` 처럼 둘을 겸하는 편이 편한 예외도 인정한다. 원칙의 효과는 "값을 돌려주는 메서드는 몇 번 불러도 안전하다" 는 믿음을 코드 전체에 심는 데 있다.

### 함수형 코어, 명령형 셸

Gary Bernhardt 는 SCNA 2012 강연 [Boundaries](https://www.destroyallsoftware.com/talks/boundaries)에서 단순한 값을 컴포넌트 간 경계로 쓰는 설계를 이야기하고, 이를 [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell)로 이어 간다.

```
 ┌──────────────── 명령형 셸 (얇게) ────────────────┐
 │  DB 읽기 → 값 생성   시계·난수 읽기   HTTP 호출    │
 │        │                                ▲          │
 │        ▼                                │          │
 │  ┌──────── 함수형 코어 (두껍게) ────────┐│          │
 │  │ 값 → 값. I/O 없음, 시간 없음, 난수 없음 ││          │
 │  │ 결정(무엇을 할지)만 계산해 값으로 반환 │┘          │
 │  └───────────────────────────────────────┘          │
 │  결정 값을 받아 DB 쓰기 / 메시지 발행               │
 └──────────────────────────────────────────────────────┘
```

코어는 목(mock) 없이 입력과 출력만으로 테스트되고, 셸은 분기가 거의 없어 통합 테스트 몇 개로 충분하다.

### 시스템 수준의 불변성

Pat Helland 의 [Immutability Changes Everything](https://www.cidrdb.org/cidr2015/Papers/CIDR15_Paper16.pdf)(CIDR 2015)은 "멀리 떨어진 곳끼리 조율하려면 불변성이 필요하고, 저장 공간이 싸지면서 불변성을 감당할 수 있게 되었다" 고 말한다. 추가만 하는 로그, [이벤트 소싱](https://martinfowler.com/eaaDev/EventSourcing.html), 스냅숏 같은 기법은 같은 생각을 데이터 계층에 적용한 것이다. 언어 차원에서 이를 기본으로 삼은 예가 [Clojure](https://clojure.org/reference/data_structures)로, 기본 컬렉션이 모두 불변이다.

## 예제

### Java record 에 방어적 복사

```java
public record Order(String id, List<OrderLine> lines) {
    public Order {                       // compact constructor
        Objects.requireNonNull(id);
        lines = List.copyOf(lines);      // 호출자의 리스트와 연결을 끊는다
    }
    public Order addLine(OrderLine line) {   // 변경 대신 새 값을 돌려준다
        var next = new ArrayList<>(lines);
        next.add(line);
        return new Order(id, next);
    }
}
```

`List.copyOf` 가 없으면 호출자가 넘긴 `ArrayList` 를 나중에 수정할 때 `Order` 내용도 바뀐다. `OrderLine` 도 불변이어야 깊은 불변이 완성된다.

### Python: 함수형 코어 + 셸

```python
from dataclasses import dataclass, replace
from datetime import datetime

@dataclass(frozen=True)
class Subscription:
    plan: str
    expires_at: datetime
    reminded: bool = False

# 코어: 순수 함수. 현재 시각도 인자로 받는다.
def decide_reminder(sub: Subscription, now: datetime) -> tuple[Subscription, bool]:
    days_left = (sub.expires_at - now).days
    if days_left <= 3 and not sub.reminded:
        return replace(sub, reminded=True), True
    return sub, False

# 셸: I/O 만 담당. 분기 거의 없음.
def run(repo, mailer, clock):
    for sub in repo.expiring_soon():
        updated, should_send = decide_reminder(sub, clock.now())
        if should_send:
            mailer.send_reminder(updated)
            repo.save(updated)
```

`decide_reminder` 는 `now` 를 바꿔 가며 경계값(3일, 이미 알림 보냄)을 목 없이 테스트할 수 있다.

## 흔한 오해와 함정

- **"`val`/`final` 이면 불변이다."** 참조만 고정된다. 필드가 가리키는 컬렉션과 객체까지 불변인지 확인한다.
- **"읽기 전용 뷰를 반환했으니 안전하다."** `Collections.unmodifiableList` 같은 뷰는 원본이 바뀌면 같이 바뀐다. 소유권을 넘길 때는 복사한다.
- **"불변 객체는 너무 느리다."** 복사 비용은 실재하지만 측정 없이 단정하지 말 것. 대부분의 업무 객체는 작고, 공유·캐시·스레드 안전성에서 얻는 이득이 크다. 큰 컬렉션을 자주 바꾸는 핫패스라면 구조 공유 자료구조나 지역적 가변성을 쓴다.
- **모든 것을 불변으로 만들려는 강박.** 함수 안의 지역 변수나 빌더처럼 바깥으로 새지 않는 가변성은 문제가 아니다. 통제해야 할 것은 **공유되는** 가변 상태다.
- **getter 의 숨은 부수효과.** 지연 초기화, 카운터 증가 같은 일을 질의 메서드에 넣으면 CQS 의 믿음이 깨진다.

## 확인 문제

1. 참조 불변, 얕은 불변, 깊은 불변을 각각 예로 구분하라.
2. Java record 의 필드가 모두 `final` 인데도 객체 상태가 바뀔 수 있는 경우는? 어떻게 막는가?
3. JLS 17.5 가 `final` 필드에 주는 보장은 무엇이며, 그것이 깨지는 대표적 실수는?
4. 함수형 코어, 명령형 셸 구조에서 "현재 시각" 을 코어 함수의 인자로 받는 이유는?

### 풀이

1. 참조 불변: Kotlin `val list = mutableListOf()` (재대입 불가, 내용 변경 가능). 얕은 불변: `Object.freeze` 한 객체의 중첩 객체는 변경 가능. 깊은 불변: 모든 필드가 불변 타입인 값 객체.
2. 컴포넌트가 가변 객체(예: `ArrayList`)를 가리키면 호출자나 외부가 그 객체를 수정할 수 있다. compact constructor 에서 `List.copyOf` 같은 방어적 복사를 하고, 요소 타입도 불변으로 만든다.
3. 생성자가 끝난 뒤 참조를 얻은 스레드는 동기화 없이도 `final` 필드의 올바르게 초기화된 값을 본다. 생성자 실행 중에 `this` 를 다른 스레드가 볼 수 있게 흘리면 깨진다.
4. 시계 읽기는 부수효과(비결정적 입력)이므로 셸이 담당해야 한다. 인자로 받으면 코어는 순수 함수가 되어 경계 시각을 자유롭게 넣어 테스트할 수 있다.

## 더 읽을거리 (References)

- Gary Bernhardt, [Boundaries](https://www.destroyallsoftware.com/talks/boundaries), SCNA 2012
- Martin Fowler, [CommandQuerySeparation](https://martinfowler.com/bliki/CommandQuerySeparation.html)
- Pat Helland, [Immutability Changes Everything](https://www.cidrdb.org/cidr2015/Papers/CIDR15_Paper16.pdf), CIDR 2015
- [JEP 395: Records](https://openjdk.org/jeps/395), [JLS §17.5 final Field Semantics](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.5)
- [Kotlin Collections overview](https://kotlinlang.org/docs/collections-overview.html), [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
- Joshua Bloch, *Effective Java*, 3rd ed., Addison-Wesley, 2018 (서지 정보)
