---
layout: post
title: "코틀린 컬렉션과 Sequence — 읽기 전용 vs 가변, 컬렉션 연산, 지연 평가, 그리고 자바 Stream 과의 대응"
date: 2026-10-12 00:26:42 +0900
categories: [kotlin]
tags: [kotlin, collections, sequence, lazy-evaluation, java-stream, interop, read-only, covariance]
---

자바·코틀린 20편 시리즈의 **코틀린 6번째 글(K6)** 이다. 이번 글은 코틀린 컬렉션을 네 덩어리로 나눠 정리한다. (1) 타입 계층: 읽기 전용 인터페이스와 가변 인터페이스의 분리, (2) 컬렉션 연산: 변환·필터·그룹핑·집계, (3) `Sequence` 와 지연 평가, (4) 자바 `Stream`·자바 컬렉션과의 상호운용. 각 항목은 "무엇인가 → 코드 → 실무 사용사례 → 함정" 순서로 쓴다.

자바 쪽 짝 글은 람다·Stream 을 다룬 [J4 — 람다·메서드 참조·함수형 인터페이스·Stream API](https://myoungsoo7.github.io/2026/10/12/java-lambda-functional-interface-stream/) 다. 읽기 전용 컬렉션이 왜 공변(covariant)인지는 [K8 — 제네릭 변성](https://myoungsoo7.github.io/2026/10/12/kotlin-generics-variance-in-out/) 에서 타입 이론 쪽으로 더 깊게 들어간다.

---

## 1. 타입 계층 — "읽기 전용" 과 "가변" 을 타입으로 가른다

### 1.1 무엇인가

코틀린은 컬렉션 종류마다 인터페이스를 **두 개** 둔다. 공식 문서 표현 그대로 옮기면 다음과 같다 ([Collections overview](https://kotlinlang.org/docs/collections-overview.html)).

- 원소에 **접근하는 연산만** 제공하는 읽기 전용(read-only) 인터페이스
- 읽기 전용 인터페이스를 상속해 **추가·삭제·갱신** 연산을 더한 가변(mutable) 인터페이스

| 읽기 전용 | 가변 | 가변 기본 구현 (문서 기준) |
|---|---|---|
| `List<T>` | `MutableList<T>` | `ArrayList` |
| `Set<T>` | `MutableSet<T>` | `LinkedHashSet` (삽입 순서 유지) |
| `Map<K, V>` | `MutableMap<K, V>` | `LinkedHashMap` (반복 시 삽입 순서 유지) |

`HashSet`·`HashMap` 은 순서를 보장하지 않는 대신 메모리를 덜 쓴다는 것도 같은 문서에 적혀 있다.

### 1.2 코드

```kotlin
val readOnly: List<String> = listOf("one", "two")
// readOnly.add("three")      // 컴파일 오류: List 에는 add 가 없다

val mutable: MutableList<String> = mutableListOf("one", "two")
mutable.add("three")          // OK — val 이어도 내용 변경은 가능

// mutable = mutableListOf()  // 컴파일 오류: val 은 재할당 불가
```

`val`/`var` 는 **변수의 재할당** 여부이고, `List`/`MutableList` 는 **컬렉션 내용의 변경** 여부다. 둘은 독립적인 축이다. 공식 문서도 "가변 컬렉션을 `var` 에 담을 필요는 없다, `val` 이어도 쓰기 연산은 가능하다" 고 명시한다.

### 1.3 읽기 전용 ≠ 불변(immutable)

읽기 전용 타입은 "이 참조로는 못 바꾼다" 는 뜻이지, "아무도 못 바꾼다" 는 뜻이 아니다. 공식 문서의 [Constructing collections](https://kotlinlang.org/docs/constructing-collections.html) 에 정확히 이 예제가 있다.

```kotlin
val sourceList = mutableListOf(1, 2, 3)
val referenceList: List<Int> = sourceList   // 같은 객체를 읽기 전용 타입으로 본다
sourceList.add(4)
println(referenceList)                      // [1, 2, 3, 4] — 변경이 보인다
```

반대로 `toList()` 는 그 시점의 **얕은 복사본(snapshot)** 을 만든다. 원본에 원소를 추가해도 복사본은 변하지 않는다. 다만 얕은 복사이므로 원소 객체 자체가 가변이면 그 내부 변경은 공유된다.

```kotlin
val source = mutableListOf(1, 2, 3)
val snapshot = source.toList()
source.add(4)
println(snapshot)   // [1, 2, 3]
```

### 1.4 실무 사용사례

- **도메인 객체가 외부에 컬렉션을 노출할 때**: 내부는 `MutableList`, 공개 프로퍼티는 `List` 로 노출한다.

```kotlin
class Order(val id: Long) {
    private val _lines = mutableListOf<OrderLine>()
    val lines: List<OrderLine> get() = _lines

    fun addLine(line: OrderLine) {
        require(line.quantity > 0) { "quantity must be positive" }
        _lines += line
    }
}

data class OrderLine(val sku: String, val quantity: Int)
```

- 외부 코드는 `order.lines.add(...)` 를 컴파일 단계에서 못 한다. 불변식(invariant) 검사는 `addLine` 한 곳에 모인다.
- 단, 1.3 에서 봤듯 `lines` 는 **뷰** 다. 호출자가 반환값을 오래 들고 있다가 나중에 읽으면 그 사이 변경이 보인다. 시점 고정이 필요하면 `get() = _lines.toList()` 로 복사해서 준다(복사 비용을 감수).

### 1.5 함정

1. **캐스팅으로 뚫린다.** `(order.lines as MutableList).add(...)` 는 런타임에 실제 객체가 `ArrayList` 이므로 성공한다. 읽기 전용은 컴파일 타임 계약이지 런타임 보호막이 아니다.
2. **자바로 넘기면 계약이 사라진다.** 자바에는 읽기 전용 인터페이스가 없다(4장 참고). 자바 메서드가 받은 `java.util.List` 에 `add` 를 호출할 수 있다.
3. **"불변" 이라고 문서·리뷰에 쓰지 말 것.** 코틀린 공식 문서 용어는 read-only 다. 진짜 불변이 필요하면 방어적 복사를 하거나 별도 불변 컬렉션 라이브러리를 쓴다.

### 1.6 공변성 — 읽기 전용만 공변이다

공식 문서: "읽기 전용 컬렉션 타입은 공변이다. `Rectangle` 이 `Shape` 를 상속하면 `List<Shape>` 가 필요한 곳에 `List<Rectangle>` 을 쓸 수 있다." 반면 "가변 컬렉션은 공변이 아니다. 그랬다면 런타임 실패가 생긴다" ([Collections overview](https://kotlinlang.org/docs/collections-overview.html)).

```kotlin
open class Shape
class Rectangle : Shape()
class Circle : Shape()

fun area(shapes: List<Shape>) = shapes.size

val rects: List<Rectangle> = listOf(Rectangle())
area(rects)                       // OK — List<out E> 이므로

val mrects: MutableList<Rectangle> = mutableListOf(Rectangle())
// val mshapes: MutableList<Shape> = mrects   // 컴파일 오류
// 만약 허용됐다면 mshapes.add(Circle()) 로 Rectangle 리스트에 Circle 이 들어간다
```

자바에서는 같은 효과를 얻으려면 `List<? extends Shape>` 와일드카드를 써야 한다. 이 차이는 공식 [Java 와 Kotlin 컬렉션 비교 가이드](https://kotlinlang.org/docs/java-to-kotlin-collections-guide.html) 에도 나란히 나온다. 원리는 K8 에서 다룬다.

---

## 2. 컬렉션 생성 — 팩토리와 빌더

### 2.1 무엇인가

| 용도 | 함수 |
|---|---|
| 읽기 전용 생성 | `listOf`, `setOf`, `mapOf`, `emptyList()` 등 |
| 가변 생성 | `mutableListOf`, `mutableSetOf`, `mutableMapOf` |
| 빌더 (안에서는 가변, 결과는 읽기 전용) | `buildList`, `buildSet`, `buildMap` |
| 복사 | `toList()`, `toMutableList()`, `toSet()` … |

### 2.2 코드

```kotlin
val statusMap = mapOf("A" to 1, "B" to 2)

val traceId: String? = currentTraceIdOrNull()

val headers = buildMap {
    put("Content-Type", "application/json")
    if (traceId != null) put("X-Trace-Id", traceId)
}

val empty = emptyList<String>()   // 빈 컬렉션은 타입을 명시
```

### 2.3 실무 사용사례

- 조건부로 원소가 붙는 컬렉션은 `buildList`/`buildMap` 이 깔끔하다. "가변으로 만들고 → 읽기 전용으로 반환" 패턴을 한 블록에 가둔다.
- 테스트 픽스처·상수 테이블은 `listOf`/`mapOf`.

### 2.4 함정 — `to` 는 공짜가 아니다

공식 문서는 `to` 표기가 **수명이 짧은 `Pair` 객체를 만든다** 고 지적하고, 성능이 중요한 곳에서는 `mutableMapOf<...>().apply { this["k"] = v }` 같은 대안을 제시한다 ([Constructing collections](https://kotlinlang.org/docs/constructing-collections.html)). 수백만 건 루프 안에서 `mapOf(a to b)` 를 반복 생성하는 코드는 리뷰에서 걸러야 한다. 반면 설정·상수처럼 한 번 만드는 맵에서는 신경 쓸 필요 없다.

---

## 3. 컬렉션 연산 — 범주별 정리

### 3.0 전제: 연산은 원본을 바꾸지 않는다

공식 문서는 연산을 8개 범주로 나눈다: 변환, 필터, plus/minus 연산자, 그룹핑, 부분 추출, 단일 원소 추출, 정렬, 집계 ([Collection operations overview](https://kotlinlang.org/docs/collection-operations.html)). `isEmpty()`·`get()` 같은 필수 연산은 **멤버 함수**이고, 필터·변환·정렬 같은 처리 함수는 **확장 함수**로 선언돼 있다.

그리고 핵심 규칙: 이 연산들은 **원본을 바꾸지 않고 새 컬렉션을 반환**한다. 그래서 다음 코드는 아무 일도 하지 않는다.

```kotlin
val numbers = listOf("one", "two", "three", "four")
numbers.filter { it.length > 3 }                 // 결과가 버려진다
val longerThan3 = numbers.filter { it.length > 3 } // 이렇게 받아야 한다
```

결과를 기존 가변 컬렉션에 쌓고 싶으면 `To` 접미사 함수(`filterTo`, `associateTo`, `mapTo` …)를 쓴다. 대상 컬렉션을 인자로 받고, 그것을 그대로 반환한다.

```kotlin
val bucket = mutableListOf<String>()
numbers.filterTo(bucket) { it.length > 3 }
```

### 3.1 변환 (map 계열)

([Collection transformations](https://kotlinlang.org/docs/collection-transformations.html))

```kotlin
val ids = users.map { it.id }
val withIndex = items.mapIndexed { i, item -> "$i:${item.name}" }
val parsed = rawLines.mapNotNull { it.toIntOrNull() }   // null 결과는 버린다

val prices = mapOf("apple" to 1000, "pear" to 2000)
val upperKeys = prices.mapKeys { it.key.uppercase() }
val withVat = prices.mapValues { it.value * 110 / 100 }
```

**실무:** `mapNotNull` 은 "파싱 실패는 조용히 버린다" 를 한 줄로 표현한다. 단, 실패를 **조용히** 버린다는 점이 함정이다. 입력 검증이 필요한 곳(정산·결제 데이터)에서는 실패 건수를 따로 세거나 `partition` 으로 분리해 로그를 남긴다.

### 3.2 연관(associate) — 리스트를 맵으로

```kotlin
val byId: Map<Long, User> = users.associateBy { it.id }
val lengthOf: Map<String, Int> = words.associateWith { it.length }
val nameToEmail: Map<String, String> = users.associate { it.name to it.email }
```

**함정 1 — 키 충돌은 마지막 값이 이긴다.** `associateBy` 에서 같은 키가 두 번 나오면 뒤의 원소가 앞을 덮는다. 중복 가능성이 있는 키(이름, 이메일)라면 `groupBy` 를 써야 데이터가 사라지지 않는다.

**함정 2 — `associate` 는 `Pair` 를 만든다.** 공식 문서가 직접 "수명이 짧은 `Pair` 객체를 만들어 성능에 영향을 줄 수 있다" 고 경고한다. 키나 값 중 하나가 원소 자체라면 `associateBy`/`associateWith` 가 낫다.

### 3.3 그룹핑

([Grouping](https://kotlinlang.org/docs/collection-grouping.html))

```kotlin
val numbers = listOf("one", "two", "three", "four", "five")

numbers.groupBy { it.first().uppercase() }
// {O=[one], T=[two, three], F=[four, five]}

numbers.groupBy(keySelector = { it.first() }, valueTransform = { it.uppercase() })
// {o=[ONE], t=[TWO, THREE], f=[FOUR, FIVE]}

numbers.groupingBy { it.first() }.eachCount()
// {o=1, t=2, f=2}
```

`groupingBy` 는 `Grouping` 객체를 돌려주고, `eachCount`·`fold`·`reduce`·`aggregate` 같은 연산을 실행하기 **직전에** 그룹을 만든다. "그룹별 개수" 만 필요할 때 `groupBy { }.mapValues { it.value.size }` 처럼 중간 리스트 맵을 다 만들 필요가 없다.

**실무 예 — 상태별 주문 수 집계:**

```kotlin
enum class Status { PAID, SHIPPED, CANCELED }
data class OrderSummary(val id: Long, val status: Status, val amount: Long)

fun countByStatus(orders: List<OrderSummary>): Map<Status, Int> =
    orders.groupingBy { it.status }.eachCount()

fun sumByStatus(orders: List<OrderSummary>): Map<Status, Long> =
    orders.groupingBy { it.status }.fold(0L) { acc, o -> acc + o.amount }
```

### 3.4 필터와 분할

```kotlin
val active = users.filter { it.active }
val inactive = users.filterNot { it.active }
val (ok, failed) = results.partition { it.isSuccess }   // Pair<List, List>
val admins = principals.filterIsInstance<Admin>()       // 타입으로 거르고 스마트 캐스트된 리스트
```

`partition` 은 "성공/실패를 나눠 각각 처리" 하는 배치 코드에서 `filter` 두 번보다 의도가 분명하다.

### 3.5 정렬

```kotlin
val sorted = users.sortedBy { it.createdAt }
val desc = users.sortedByDescending { it.score }
val multi = users.sortedWith(compareBy<User>({ it.lastName }, { it.firstName }))
```

**함정:** `sorted*` 는 새 리스트를 반환하고, `MutableList.sort*` 는 제자리 정렬이다. 이름이 비슷해서 `list.sortBy { }` 의 반환값(Unit)을 받으려다 컴파일 오류를 만나는 일이 흔하다.

### 3.6 집계

```kotlin
val total = orders.sumOf { it.amount }
val max = orders.maxByOrNull { it.amount }
val joined = tags.joinToString(separator = ", ", prefix = "[", postfix = "]")
val product = (1..5).fold(1L) { acc, n -> acc * n }
```

`joinToString` 은 `limit`·`truncated` 인자도 받는다. 로그에 수천 개 ID 를 찍는 사고를 막을 때 유용하다.

```kotlin
log.info("ids={}", ids.joinToString(limit = 20, truncated = "...(${ids.size} total)"))
```

### 3.7 평탄화와 짝맞추기

```kotlin
val allTags = posts.flatMap { it.tags }
val flat = listOf(setOf(1, 2), setOf(3)).flatten()

val pairs = names zip scores               // List<Pair<String, Int>>
val lines = names.zip(scores) { n, s -> "$n=$s" }
val (left, right) = pairs.unzip()
```

`zip` 은 짧은 쪽 길이에 맞춰 잘린다. 두 리스트 길이가 같아야 하는 데이터(헤더-값 매핑 등)라면 `require(a.size == b.size)` 를 먼저 둬야 조용한 유실을 막는다.

### 3.8 연산 범주 요약표

| 범주 | 대표 함수 | 자바 Stream 대응 |
|---|---|---|
| 변환 | `map`, `mapNotNull`, `flatMap`, `associateBy` | `map`, `flatMap`, `Collectors.toMap` |
| 필터 | `filter`, `filterNot`, `partition`, `filterIsInstance` | `filter`, `Collectors.partitioningBy` |
| 그룹 | `groupBy`, `groupingBy{}.eachCount()` | `Collectors.groupingBy`, `counting()` |
| 정렬 | `sortedBy`, `sortedWith` | `sorted(Comparator)` |
| 집계 | `sumOf`, `fold`, `reduce`, `maxByOrNull` | `reduce`, `max`, `mapToLong().sum()` |
| 문자열화 | `joinToString` | `Collectors.joining` |

(오른쪽 열은 기능상 대응이며 동작·반환 타입이 1:1 로 같지는 않다.)

---

## 4. Sequence — 지연 평가

### 4.1 무엇인가

공식 문서의 정의를 요약하면 ([Sequences](https://kotlinlang.org/docs/sequences.html)):

- `Iterable`(일반 컬렉션) 의 다단계 처리는 **즉시(eager)** 실행된다. 각 단계가 끝날 때마다 **중간 컬렉션**을 반환한다.
- `Sequence` 의 다단계 처리는 가능한 한 **지연(lazy)** 실행된다. 전체 체인의 결과를 요청할 때 비로소 계산한다.
- 처리 순서도 다르다. `Iterable` 은 한 단계를 **컬렉션 전체에** 끝내고 다음 단계로 간다. `Sequence` 는 **원소 하나씩** 모든 단계를 통과시킨다.

### 4.2 코드 — 공식 문서 예제

```kotlin
val words = "The quick brown fox jumps over the lazy dog".split(" ")

// Iterable: filter 를 9개 단어 전부에, map 을 통과한 전부에 실행한 뒤 take(4)
val lengthsList = words
    .filter { println("filter: $it"); it.length > 3 }
    .map { println("length: ${it.length}"); it.length }
    .take(4)

// Sequence: 원소 단위로 filter→map 을 거치다가 4개가 모이면 멈춘다
val lengthsSequence = words.asSequence()
    .filter { println("filter: $it"); it.length > 3 }
    .map { println("length: ${it.length}"); it.length }
    .take(4)

println("Lengths of first 4 words longer than 3 chars")
println(lengthsSequence.toList())   // 이 terminal 연산에서야 filter/map 이 실행된다
```

Sequence 버전은 `toList()` 호출 전까지 아무 출력도 없고, 4개를 찾으면 나머지 단어에는 `filter` 조차 호출하지 않는다.

### 4.3 중간 연산과 최종 연산, stateless 와 stateful

공식 문서의 분류:

| 축 | 구분 | 예 |
|---|---|---|
| 반환 타입 | **중간(intermediate)**: 다른 Sequence 를 지연 반환 | `map`, `filter`, `take` |
| | **최종(terminal)**: 그 외. 원소는 최종 연산으로만 꺼낼 수 있다 | `toList()`, `sum()`, `first()` |
| 상태 | **stateless**: 원소를 독립 처리 (`take`/`drop` 처럼 작은 상수 상태 포함) | `map`, `filter`, `take` |
| | **stateful**: 원소 수에 비례하는 상태 필요 | 예: 전체를 봐야 하는 정렬 |

정렬처럼 전체 원소를 봐야 하는 stateful 연산은 결국 원소를 다 모아야 다음 단계로 넘길 수 있으므로, 체인 중간에 끼면 지연 평가의 이점이 그 지점에서 끊긴다.

### 4.4 Sequence 만들기

```kotlin
val s1 = sequenceOf("a", "b", "c")
val s2 = listOf(1, 2, 3).asSequence()

// 무한 시퀀스 — 반드시 take 등으로 끊어야 한다
val odds = generateSequence(1) { it + 2 }
println(odds.take(5).toList())     // [1, 3, 5, 7, 9]

// null 을 반환하면 끝난다
val oddsBelow10 = generateSequence(1) { if (it < 8) it + 2 else null }
println(oddsBelow10.count())       // 5

// sequence 빌더 — yield / yieldAll
val custom = sequence {
    yield(1)
    yieldAll(listOf(3, 5))
    yieldAll(generateSequence(7) { it + 2 })
}
println(custom.take(5).toList())   // [1, 3, 5, 7, 9]
```

### 4.5 실무 사용사례

1. **"앞에서 N 개만"** 이 필요한 큰 컬렉션 처리. `first { }`, `take(n)` 이 체인 끝에 있으면 Sequence 가 불필요한 계산을 건너뛴다.
2. **페이지네이션 API 를 하나의 스트림처럼** 다룰 때. 다음 페이지 토큰이 없으면 끝나는 구조는 `generateSequence`/`sequence { }` 와 잘 맞는다.

```kotlin
data class Page(val items: List<String>, val nextToken: String?)

fun fetchPage(token: String?): Page = TODO("HTTP 호출")

fun allItems(): Sequence<String> = sequence {
    var token: String? = null
    do {
        val page = fetchPage(token)
        yieldAll(page.items)
        token = page.nextToken
    } while (token != null)
}

// 조건을 만족하는 첫 항목을 찾으면 그 뒤 페이지는 요청하지 않는다
val firstMatch = allItems().firstOrNull { it.startsWith("ERR") }
```

3. **중간 결과가 큰 다단계 변환.** `map → filter → map` 체인에서 중간 리스트가 원본만큼 크면, Sequence 로 중간 리스트 할당을 없앨 수 있다.

### 4.6 함정

1. **작은 컬렉션에 습관적으로 `asSequence()` 를 붙이지 말 것.** 공식 문서: "Sequence 의 지연 특성은 오버헤드를 더하며, 작은 컬렉션이나 단순한 계산에서는 그 오버헤드가 클 수 있다. `Sequence` 와 `Iterable` 을 모두 고려해 결정하라." 어느 쪽이 빠른지는 측정해서 정한다.
2. **최종 연산을 잊으면 아무 일도 안 일어난다.** `seq.map { save(it) }` 는 `Sequence` 를 반환할 뿐 `save` 를 한 번도 호출하지 않는다. 부수효과가 목적이면 `forEach` 같은 최종 연산이 필요하다.
3. **여러 번 순회 가능 여부는 구현마다 다르다.** 공식 문서: "Sequence 는 여러 번 순회할 수 있다. 다만 일부 구현은 한 번만 순회되도록 제한할 수 있고, 그 경우 해당 문서에 명시된다." 4.5 의 `allItems()` 를 두 번 순회하면 HTTP 호출이 두 번 일어난다. 재사용할 결과라면 `toList()` 로 한 번 구체화한다.
4. **무한 시퀀스에 `toList()`/`sorted()`.** 끝나지 않는다. `take`/`takeWhile` 로 먼저 자른다.

---

## 5. 자바 Stream 과의 비교

### 5.1 개념 대응

공식 가이드 [Collections in Java and Kotlin](https://kotlinlang.org/docs/java-to-kotlin-collections-guide.html) 의 요지:

- 자바 Stream API 는 중간 연산과 최종 연산을 가진다. `filter()` 는 Stream 을 반환하는 중간 연산이고, 컬렉션을 받으려면 `collect()` 같은 최종 연산이 필요하다.
- 코틀린은 필터링이 컬렉션에 내장돼 있고, `filter()` 는 필터링한 컬렉션과 같은 타입을 반환한다(즉시 평가).
- **자바 Stream 의 지연 평가에 대응하는 것은 코틀린 `Sequence`** 다.

```java
// Java
List<String> result = names.stream()
        .filter(n -> n.length() > 3)
        .map(String::toUpperCase)
        .toList();          // JDK 16+, 수정 불가 List
```

```kotlin
// Kotlin — 즉시 평가 (중간 리스트 생성)
val result = names.filter { it.length > 3 }.map { it.uppercase() }

// Kotlin — 지연 평가 (Stream 과 같은 모양)
val result2 = names.asSequence().filter { it.length > 3 }.map { it.uppercase() }.toList()
```

### 5.2 차이점 표

| 항목 | 자바 Stream | 코틀린 컬렉션 연산 | 코틀린 Sequence |
|---|---|---|---|
| 평가 | 지연 | 즉시 | 지연 |
| 재사용 | **한 번만** 조작해야 함 | 원본은 그대로, 여러 번 가능 | 대개 여러 번 가능, 구현별 제한 가능 |
| 병렬 | `parallelStream()`/`parallel()` 지원 | 없음 | 없음 |
| 결과 수집 | `collect`/`toList()` 필요 | 바로 `List` | 최종 연산 필요 |
| 가변성 표현 | 타입으로 표현 불가 (`toList()` 결과는 수정 시 예외) | `List`/`MutableList` 로 구분 | — |

근거:
- 자바 `Stream` Javadoc: "스트림은 (중간·최종 연산 호출로) **한 번만** 조작해야 한다. 같은 소스가 둘 이상의 파이프라인에 공급되는 '분기' 스트림이나 같은 스트림의 다중 순회는 배제된다." 재사용이 감지되면 `IllegalStateException` 을 던질 수 있다 ([Stream (Java SE 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html)).
- 같은 Javadoc: `Stream.toList()` 는 **JDK 16** 에 추가됐고, 반환 리스트는 수정 불가이며 변경 메서드는 항상 `UnsupportedOperationException` 을 던진다. 병렬 스트림은 `Collection.parallelStream()` 또는 `BaseStream.parallel()` 로 만든다.
- 코틀린 가이드: 자바에서는 "타입만 보고 컬렉션이 가변인지 알 수 없고", `Collections.unmodifiableList(...)` 에 `add` 하는 코드는 **컴파일되고 런타임에 실패** 한다. 코틀린은 읽기 전용 컬렉션 수정 시도가 **컴파일 오류** 다.

### 5.3 실무 판단 기준

- **기본값은 컬렉션 연산.** 원소 수가 작거나 단계가 1~2개면 가독성과 단순성이 이긴다.
- **Sequence 로 바꿀 때:** 원소가 많고 단계가 많아 중간 컬렉션이 부담일 때, 또는 `first`/`take` 로 일찍 끝낼 수 있을 때.
- **자바 Stream 을 코틀린에서 그대로 쓸 일:** 자바 라이브러리가 `Stream` 을 반환하거나 병렬 스트림이 꼭 필요할 때. 코틀린 표준 라이브러리 `kotlin.streams` 패키지에 `Stream<T>.asSequence()`, `Sequence<T>.asStream()`, `Stream<T>.toList()` 가 있다(모두 Kotlin 1.2 부터, [kotlin.streams API](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.streams/)). `asStream()` 은 **순차(sequential)** Stream 을 만든다.

```kotlin
import kotlin.streams.asSequence

fun activeIds(repo: JavaRepository): List<Long> =
    repo.streamAll()              // Java 가 Stream<Entity> 를 반환
        .asSequence()
        .filter { it.isActive }
        .map { it.id }
        .toList()
```

**함정:** JPA 리포지토리의 `Stream` 반환 메서드처럼 리소스를 잡는 Stream 은 닫아야 한다. `asSequence()` 로 감싸도 닫는 책임은 그대로이므로 `stream.use { it.asSequence()... }` 형태로 감싼다(`Stream` 은 `AutoCloseable` 이다).

---

## 6. 자바 컬렉션 상호운용 — 플랫폼 타입 `(Mutable)List<T>!`

### 6.1 무엇인가

자바 컬렉션 타입은 코틀린에서 매핑된다. 공식 표 일부 ([Calling Java from Kotlin — Mapped types](https://kotlinlang.org/docs/java-interop.html)):

| 자바 | 코틀린 읽기 전용 | 코틀린 가변 | 자바에서 로드될 때 |
|---|---|---|---|
| `Iterable<T>` | `Iterable<T>` | `MutableIterable<T>` | `(Mutable)Iterable<T>!` |
| `Collection<T>` | `Collection<T>` | `MutableCollection<T>` | `(Mutable)Collection<T>!` |
| `List<T>` | `List<T>` | `MutableList<T>` | `(Mutable)List<T>!` |
| `Set<T>` | `Set<T>` | `MutableSet<T>` | `(Mutable)Set<T>!` |
| `Map<K, V>` | `Map<K, V>` | `MutableMap<K, V>` | `(Mutable)Map<K, V>!` |

`(Mutable)List<T>!` 는 "가변일 수도 아닐 수도, null 일 수도 아닐 수도 있는 T 의 자바 리스트" 라는 뜻이다. `!` 는 플랫폼 타입 표기다([K2 — 널 안전과 플랫폼 타입](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/)).

### 6.2 코드와 사용사례

```kotlin
// Java: public List<String> legacyNames() { ... }
val a: List<String> = javaService.legacyNames()          // 읽기 전용으로 받겠다고 선언
val b: MutableList<String> = javaService.legacyNames()   // 가변으로 받는 것도 컴파일된다
val c: List<String>? = javaService.legacyNames()         // null 가능성도 내가 결정
```

**실무 규칙:** 자바 API 경계에서는 반환값을 받자마자 **명시적 타입**을 붙인다. 추론에 맡기면 플랫폼 타입이 코드 안으로 번진다. 자바 쪽에 nullability 애노테이션이 붙어 있으면 코틀린이 그 정보를 쓴다(K2 참고).

### 6.3 함정

1. **`List<String>` 으로 받았다고 실제로 수정 불가인 건 아니다.** 반대로 `MutableList` 로 받았는데 실제 객체가 `List.of(...)` 나 `Collections.unmodifiableList(...)` 면 `add` 시 런타임 `UnsupportedOperationException` 이다. 자바 쪽 계약(Javadoc)을 확인해야 한다.
2. **코틀린 `List` 를 자바에 넘기면** 자바는 그것을 그냥 `java.util.List` 로 본다. 코틀린 쪽의 읽기 전용 의도는 전달되지 않는다.

---

## 7. 체크리스트

- [ ] 공개 API 는 `List`/`Set`/`Map`, 내부 구현은 `Mutable*` 로 노출 범위를 좁혔는가
- [ ] "읽기 전용" 을 "불변" 으로 오해하는 문서·주석이 없는가
- [ ] `associateBy` 키 충돌로 데이터가 사라질 가능성은 없는가 (`groupBy` 고려)
- [ ] 핫 루프의 `to`·`associate` 가 `Pair` 를 대량 생성하지 않는가
- [ ] `asSequence()` 는 측정 근거나 조기 종료 이점이 있을 때만 썼는가
- [ ] Sequence 체인 끝에 최종 연산이 있는가, 두 번 순회해도 되는 소스인가
- [ ] 자바 경계의 반환값에 명시적 코틀린 타입을 붙였는가
- [ ] 리소스를 잡는 자바 `Stream` 을 닫고 있는가

---

## References

- Kotlin docs — [Collections overview](https://kotlinlang.org/docs/collections-overview.html)
- Kotlin docs — [Constructing collections](https://kotlinlang.org/docs/constructing-collections.html)
- Kotlin docs — [Collection operations overview](https://kotlinlang.org/docs/collection-operations.html)
- Kotlin docs — [Collection transformation operations](https://kotlinlang.org/docs/collection-transformations.html)
- Kotlin docs — [Grouping](https://kotlinlang.org/docs/collection-grouping.html)
- Kotlin docs — [Sequences](https://kotlinlang.org/docs/sequences.html)
- Kotlin docs — [Collections in Java and Kotlin](https://kotlinlang.org/docs/java-to-kotlin-collections-guide.html)
- Kotlin docs — [Calling Java from Kotlin (Mapped types)](https://kotlinlang.org/docs/java-interop.html)
- Kotlin API — [kotlin.streams](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.streams/)
- Java SE 21 API — [java.util.stream.Stream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html)

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/)
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/)
- J9. [스프링이 자바를 쓰는 방식 — 리플렉션·프록시·DI](/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/)
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/)

**코틀린**

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/)
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/) ← 지금 글
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
