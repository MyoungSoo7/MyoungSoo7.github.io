---
layout: post
title: "코틀린 제네릭과 변성 — 선언 지점 변성 in/out, 타입 프로젝션, 스타 프로젝션, reified, 그리고 자바 와일드카드와의 대응"
date: 2026-10-12 00:28:42 +0900
categories: [kotlin]
tags: [kotlin, generics, variance, covariance, contravariance, star-projection, reified, java-interop, wildcard]
---

자바·코틀린 20편 시리즈의 **코틀린 8번째 글(K8)** 이다. 제네릭 변성을 다섯 덩어리로 나눈다. (1) 왜 변성이 필요한가 — 자바 와일드카드의 동기, (2) 선언 지점 변성 `out`/`in`, (3) 사용 지점 변성(타입 프로젝션), (4) 스타 프로젝션과 타입 소거, (5) 제약(upper bound)·`reified`·자바 상호운용. 각 문법은 "무엇인가 → 코드 → 사용사례 → 함정" 순으로 쓴다.

자바 쪽 짝 글은 [J2 — 타입 시스템: 제네릭과 타입 소거, 와일드카드와 PECS](https://myoungsoo7.github.io/2026/10/12/java-type-system-generics-erasure-pecs/) 다. `inline`/`reified` 의 함수 측면은 [K4 — 함수: 확장·고차·inline/reified](https://myoungsoo7.github.io/2026/10/12/kotlin-functions-extension-inline-reified/), 읽기 전용 컬렉션이 공변인 실무 효과는 [K6 — 컬렉션과 Sequence](https://myoungsoo7.github.io/2026/10/12/kotlin-collections-and-sequences/) 에 있다. 제네릭 일반론은 [CS300 #033 제네릭과 타입 매개변수](https://myoungsoo7.github.io/2026/10/10/cs300-033-generics-and-type-parameters/) 를 참고.

---

## 1. 출발점 — 자바 제네릭은 불변(invariant)이다

### 1.1 무엇인가

코틀린 공식 문서는 변성 장을 이렇게 연다: "자바 타입 시스템에서 가장 까다로운 부분 중 하나가 와일드카드 타입이다. **코틀린에는 와일드카드가 없다.** 대신 **선언 지점 변성(declaration-site variance)** 과 **타입 프로젝션(type projections)** 이 있다." ([Generics: in, out, where](https://kotlinlang.org/docs/generics.html))

그리고 문제의 뿌리: "자바의 제네릭 타입은 **불변**이다. 즉 `List<String>` 은 `List<Object>` 의 하위 타입이 아니다." 만약 공변이었다면 자바 배열처럼 런타임에 깨진다.

```java
// Java — 만약 List 가 공변이었다면
List<String> strs = new ArrayList<>();
List<Object> objs = strs;   // 실제로는 컴파일 오류
objs.add(1);                // 정수를 문자열 리스트에 넣음
String s = strs.get(0);     // ClassCastException
```

### 1.2 자바의 해법 — 사용 지점 와일드카드

자바는 메서드를 쓸 때마다 `? extends`/`? super` 를 붙여 해결한다. 코틀린 문서도 Joshua Bloch 의 원칙 **PECS — Producer-Extends, Consumer-Super** 를 인용한다: "최대 유연성을 위해 생산자·소비자를 나타내는 입력 파라미터에 와일드카드를 써라."

```java
// Java
void addAll(Collection<? extends E> items);         // E 를 꺼내기만 하는 생산자
void sort(List<T> list, Comparator<? super T> c);    // T 를 받기만 하는 소비자
```

문제는 **매번** 써야 한다는 것이다. `Source<T>` 처럼 애초에 T 를 반환만 하는 타입이라도, 자바는 그 사실을 선언에 적을 방법이 없어서 사용하는 모든 곳에 `Source<? extends T>` 를 반복한다. 코틀린은 이 사실을 **선언에 한 번** 적게 했다.

---

## 2. 선언 지점 변성 — `out` 과 `in`

### 2.1 `out` — 공변(covariance), 생산자

공식 문서: "클래스 `C` 의 타입 파라미터 `T` 가 `out` 으로 선언되면, `T` 는 `C` 멤버에서 **out 위치(반환)에만** 나올 수 있다. 대신 `C<Base>` 가 `C<Derived>` 의 상위 타입이 될 수 있다."

```kotlin
interface Source<out T> {
    fun nextT(): T
}

fun demo(strs: Source<String>) {
    val objects: Source<Any> = strs   // OK — T 가 out 이므로
}
```

자바라면 `Source<? extends Object>` 로 써야 할 것을 코틀린은 `Source<Any>` 로 그냥 쓴다.

### 2.2 `in` — 반공변(contravariance), 소비자

공식 문서: "`in` 은 타입 파라미터를 반공변으로 만든다. **소비만 되고 생산되지 않는다.**" 대표 예가 `Comparable` 이다.

```kotlin
interface Comparable<in T> {
    operator fun compareTo(other: T): Int
}

fun demo(x: Comparable<Number>) {
    x.compareTo(1.0)                 // Double 은 Number 의 하위 타입
    val y: Comparable<Double> = x    // OK — Number 를 비교할 수 있으면 Double 도 비교할 수 있다
}
```

문서가 제시하는 기억법: **"Consumer in, Producer out!"**

### 2.3 표준 라이브러리의 실제 선언

| 타입 | 변성 | 이유 |
|---|---|---|
| `List<out E>` (읽기 전용) | 공변 | E 를 꺼내기만 함 |
| `MutableList<E>` | 불변 | E 를 넣기도 함 |
| `Comparable<in T>` | 반공변 | T 를 받기만 함 |
| 함수 타입 `(P) -> R` | P 는 in, R 은 out | 인자는 소비, 반환은 생산 |
| `Array<T>` | **불변** | 읽기·쓰기 모두 |

`List`/`MutableList` 의 공변·불변 구분은 [Collections overview](https://kotlinlang.org/docs/collections-overview.html) 에 명시돼 있다. `Array<T>` 가 불변인 점은 [Generics 문서](https://kotlinlang.org/docs/generics.html) 의 타입 프로젝션 절에 나온다 — 자바 배열이 공변이라 `ArrayStoreException` 이 런타임에 터지는 것과 대조된다.

### 2.4 실무 사용사례 — 이벤트 핸들러와 결과 타입

```kotlin
// 생산자: 이벤트를 꺼내기만 한다
interface EventSource<out E> {
    fun poll(): E?
}

// 소비자: 이벤트를 받기만 한다
interface EventHandler<in E> {
    fun handle(event: E)
}

sealed interface DomainEvent
data class OrderPlaced(val orderId: Long) : DomainEvent
data class OrderCanceled(val orderId: Long) : DomainEvent

class AuditLogger : EventHandler<DomainEvent> {
    override fun handle(event: DomainEvent) = println("audit: $event")
}

fun wire(placed: EventSource<OrderPlaced>, handler: EventHandler<OrderPlaced>) {
    generateSequence { placed.poll() }.forEach(handler::handle)
}

fun main() {
    val source = object : EventSource<OrderPlaced> {
        private val q = ArrayDeque(listOf(OrderPlaced(1), OrderPlaced(2)))
        override fun poll(): OrderPlaced? = q.removeFirstOrNull()
    }
    wire(source, AuditLogger())   // EventHandler<DomainEvent> 가 EventHandler<OrderPlaced> 자리에 들어간다 (in)
}
```

모든 도메인 이벤트를 받는 범용 핸들러(`AuditLogger`)를 특정 이벤트 핸들러가 필요한 자리에 꽂을 수 있다. 자바라면 `wire` 시그니처에 `EventHandler<? super OrderPlaced>` 를 써야 하는 부분이다.

### 2.5 함정 — 위치 규칙

1. **`out T` 를 공개 메서드 파라미터에 쓰면 컴파일 오류.** `interface Source<out T> { fun push(t: T) }` 는 안 된다. "읽기만 한다" 는 약속을 컴파일러가 강제한다. `in T` 를 반환 타입에 쓰는 것도 마찬가지다.
2. **"일단 `out` 붙이고 보자" 는 안 된다.** 나중에 T 를 받는 메서드가 필요해지면 선언을 바꿔야 하고, 그 순간 기존 호출부의 서브타이핑이 깨진다. 변성은 공개 API 계약이므로 처음부터 "이 타입은 정말 생산만 하는가" 를 따져서 붙인다.

---

## 3. 사용 지점 변성 — 타입 프로젝션

### 3.1 무엇인가

공식 문서: "타입 파라미터를 `out` 으로 선언하면 편하지만, **어떤 클래스는 실제로 T 를 반환만 하도록 제한할 수 없다.** 좋은 예가 `Array` 다." 이때는 **쓰는 쪽에서** 변성을 지정한다. 이것이 타입 프로젝션이고, 자바 와일드카드와 같은 개념이다.

### 3.2 코드

```kotlin
fun copy(from: Array<out Any>, to: Array<Any>) {
    require(from.size == to.size)
    for (i in from.indices) to[i] = from[i]
    // from[0] = "x"   // 컴파일 오류 — out 프로젝션은 쓰기를 막는다
}

fun fill(dest: Array<in String>, value: String) {
    for (i in dest.indices) dest[i] = value
}

fun main() {
    val ints: Array<Int> = arrayOf(1, 2, 3)
    val any = Array<Any>(3) { "" }
    copy(ints, any)                         // Array<Int> → Array<out Any>

    val objs: Array<Any> = arrayOf(1, 2)
    fill(objs, "x")                         // Array<Any> → Array<in String>
}
```

공식 문서: "`Array<in String>` 은 자바의 `Array<? super String>` 에 해당한다. 즉 `String`, `CharSequence`, `Object` 배열을 `fill()` 에 넘길 수 있다." `Array<out Any>` 는 `? extends Object` 에 해당한다.

### 3.3 대응표

| 코틀린 | 자바 | 의미 |
|---|---|---|
| 선언 `class Box<out T>` | 대응 없음 (사용처마다 `? extends`) | 이 타입은 항상 T 의 생산자 |
| 선언 `class Sink<in T>` | 대응 없음 (사용처마다 `? super`) | 이 타입은 항상 T 의 소비자 |
| 사용 `Array<out T>` | `T[]`… 제네릭이면 `Foo<? extends T>` | 이 자리에서는 읽기만 |
| 사용 `MutableList<in T>` | `List<? super T>` | 이 자리에서는 쓰기만(읽으면 `Any?`) |
| `Foo<*>` | `Foo<?>` | 타입 인자를 모름 (4장) |

### 3.4 실무 사용사례

`MutableList` 처럼 불변으로 선언된 타입을 받는 유틸 함수를 유연하게 만들 때 쓴다.

```kotlin
fun <T> drainTo(source: MutableList<out T>, sink: MutableList<in T>) {
    sink.addAll(source)
    // source.clear() 는 가능하다 — clear 는 T 를 받지 않으므로 out 프로젝션에서도 호출된다
}

val numbers: MutableList<Int> = mutableListOf(1, 2)
val anything: MutableList<Any> = mutableListOf()
drainTo(numbers, anything)
```

### 3.5 함정

- **`MutableList<out T>` 에서 꺼낸 값은 T, 넣는 메서드는 사실상 막힌다.** `add(element: E)` 의 E 가 `Nothing` 처럼 취급되기 때문이다. "왜 add 가 안 보이지?" 의 원인이 대개 이것이다.
- 선언 지점에서 이미 `out` 인 타입(`List<out E>`)에 또 `List<out Foo>` 를 쓰는 것은 의미상 중복이다.

---

## 4. 스타 프로젝션과 타입 소거

### 4.1 스타 프로젝션 `*`

공식 문서: "타입 인자에 대해 아무것도 모르지만 안전하게 쓰고 싶을 때가 있다." 규칙은 다음과 같다.

| 선언 | `Foo<*>` 의 의미 | 결과 |
|---|---|---|
| `Foo<out T : TUpper>` | `Foo<out TUpper>` | `TUpper` 로 **읽기** 안전 |
| `Foo<in T>` | `Foo<in Nothing>` | 안전하게 **쓸 수 있는 것이 없음** |
| `Foo<T : TUpper>` (불변) | 읽기는 `Foo<out TUpper>`, 쓰기는 `Foo<in Nothing>` | 읽기만 가능 |

함수 타입 예 (`interface Function<in T, out U>`):

- `Function<*, String>` = `Function<in Nothing, String>`
- `Function<Int, *>` = `Function<Int, out Any?>`
- `Function<*, *>` = `Function<in Nothing, out Any?>`

### 4.2 타입 소거와 `is` 검사

공식 문서: "타입 정보는 소거된다. 예를 들어 `Foo<Bar>` 와 `Foo<Baz?>` 인스턴스는 모두 `Foo<*>` 로 소거된다." 그래서 "런타임에 제네릭 인스턴스가 어떤 타입 인자로 만들어졌는지 확인하는 일반적 방법은 없고, 컴파일러는 `ints is List<Int>` 나 `list is T` 같은 검사를 **금지**한다." 대신 스타 프로젝션 타입에는 검사할 수 있다.

```kotlin
fun describe(x: Any) = when (x) {
    is List<*> -> "list of ${x.size}"       // OK
    // is List<String> -> ...               // 컴파일 오류
    else -> "other"
}
```

캐스트도 마찬가지다. `foo as List<String>` 은 런타임에 검사할 수 없어 **unchecked cast 경고**가 나고, 필요하면 `@Suppress("UNCHECKED_CAST")` 로 의도를 표시한다.

### 4.3 실무 사용사례 — 이질적 핸들러 레지스트리

```kotlin
interface Handler<in E> { fun handle(e: E) }

class Registry {
    private val handlers = mutableMapOf<Class<*>, Handler<*>>()

    fun <E : Any> register(type: Class<E>, h: Handler<E>) {
        handlers[type] = h
    }

    fun dispatch(event: Any) {
        @Suppress("UNCHECKED_CAST")
        val h = handlers[event.javaClass] as Handler<Any>?   // 등록 시점에 타입을 맞췄으므로 안전
        h?.handle(event)
    }
}
```

맵 값 타입이 `Handler<*>` 인 이유는 서로 다른 E 를 한 맵에 담기 위해서다. 꺼낼 때의 unchecked cast 는 `register` 가 키·값 타입을 일치시킨다는 **불변식**에 기대고 있다. 이 불변식을 깨는 다른 쓰기 경로가 생기지 않도록 맵을 `private` 으로 막는 것이 핵심이다.

### 4.4 함정

- `Handler<*>` 에 `handle(...)` 을 직접 부를 수 없다(`in Nothing`). 이를 우회하려고 여기저기 캐스트를 뿌리면 소거 때문에 **잘못된 타입이 한참 뒤에 터진다**. 캐스트는 한 곳에 모은다.
- 자바의 raw type(`List`) 과 `List<*>` 는 다르다. raw type 은 검사를 꺼 버리지만, 스타 프로젝션은 읽기만 허용하는 **안전한** 타입이다.

---

## 5. 제약, reified, 그리고 자바 상호운용

### 5.1 상한 제약과 where 절

공식 문서: "가장 흔한 제약은 상한(upper bound)이며 자바의 `extends` 에 해당한다." 꺾쇠 안에는 상한을 하나만 쓸 수 있고, 여러 개가 필요하면 `where` 절을 쓴다.

```kotlin
fun <T : Comparable<T>> maxOf3(a: T, b: T, c: T): T = maxOf(a, maxOf(b, c))

fun <T> copyWhenGreater(list: List<T>, threshold: T): List<String>
        where T : CharSequence, T : Comparable<T> =
    list.filter { it > threshold }.map { it.toString() }
```

공식 문서: "상한을 지정하지 않으면 기본 상한은 `Any?` 다." 즉 `fun <T> f(x: T)` 의 T 는 nullable 일 수 있다. null 을 허용하지 않으려면 `<T : Any>` 로 쓴다.

### 5.2 확실히 non-null 인 타입 `T & Any`

자바 제네릭을 상속할 때, 자바 쪽 시그니처가 "이 파라미터만은 non-null" 인 경우가 있다. 코틀린은 `T & Any` 로 이를 표현한다. 공식 문서: "제네릭 타입 `T` 를 확실히 non-nullable 로 선언하려면 `& Any` 를 붙인다. 이 타입은 nullable 상한을 가져야 한다." [Kotlin 1.7.0 에서 Stable](https://kotlinlang.org/docs/whatsnew17.html) 이 됐다.

```kotlin
fun <T> elvisLike(x: T, y: T & Any): T & Any = x ?: y
```

```kotlin
// Java: interface Game<T> { T save(T x); @NotNull T load(@NotNull T x); }
interface ArcadeGame<T1> : Game<T1> {
    override fun save(x: T1): T1
    override fun load(x: T1 & Any): T1 & Any
}
```

같은 1.7.0 에서 타입 인자 추론용 **언더스코어 연산자 `_`** 도 도입됐다 — `Runner.run<SomeImplementation, _>()` 처럼 일부 타입 인자만 명시하고 나머지는 추론하게 한다.

### 5.3 reified — 소거를 피해 가는 inline

공식 문서([Inline functions](https://kotlinlang.org/docs/inline-functions.html)): "inline 이 아닌 일반 함수는 reified 파라미터를 가질 수 없다." reified 타입 파라미터는 함수 안에서 "거의 일반 클래스처럼" 쓸 수 있다 — `is T`, `T::class` 가 된다.

```kotlin
inline fun <reified T> Any.findParentOfType(parentOf: (Any) -> Any?): T? {
    var p = parentOf(this)
    while (p != null && p !is T) p = parentOf(p)
    return p as T?
}

inline fun <reified T> membersOf() = T::class.members
```

제약: "런타임 표현이 없는 타입(reified 가 아닌 타입 파라미터, `Nothing` 같은 가상 타입)은 reified 타입 인자로 쓸 수 없다."

**실무 — 스프링의 reified 확장.** 스프링 공식 문서는 reified 를 이용해 JVM 타입 소거를 우회하는 확장을 제공한다고 설명한다 ([Spring Framework — Kotlin Extensions](https://docs.spring.io/spring-framework/reference/languages/kotlin/extensions.html)).

```kotlin
// Java:  Flux<User> users = client.get().retrieve().bodyToFlux(User.class);
val users = client.get().retrieve().bodyToFlux<User>()
// 또는
val users2: Flux<User> = client.get().retrieve().bodyToFlux()
```

이 확장은 import 해야 쓸 수 있다는 점도 문서에 명시돼 있다(IDE 가 보통 제안한다).

**함정:** reified 는 호출 지점에 함수 본문이 인라인될 때 **호출 지점의 구체 타입**이 들어가는 것이다. `List<User>` 처럼 제네릭 타입을 넘기면 `T::class` 는 `List::class` 일 뿐 `User` 정보는 없다. 중첩 제네릭 역직렬화는 라이브러리의 타입 토큰 API 를 써야 한다.

### 5.4 자바에서 보는 코틀린 변성 — 와일드카드 자동 생성

코틀린 선언 지점 변성은 자바에서 어떻게 보일까. 공식 문서([Calling Kotlin from Java — Variant generics](https://kotlinlang.org/docs/java-to-kotlin-interop.html)):

```kotlin
class Box<out T>(val value: T)
interface Base
class Derived : Base

fun boxDerived(value: Derived): Box<Derived> = Box(value)
fun unboxBase(box: Box<Base>): Base = box.value
```

```java
// 자바에서 보이는 시그니처
Box<Derived> boxDerived(Derived value) { ... }         // 반환 타입: 와일드카드 없음
Base unboxBase(Box<? extends Base> box) { ... }        // 파라미터: 와일드카드 생성
```

규칙:

- **파라미터** 위치에서는 와일드카드를 생성한다.
- **반환 타입**에는 생성하지 않는다. 문서 이유: "자바 코딩 스타일에 반하고" 자바 호출자를 번거롭게 하므로.
- 타입 인자가 `String` 같은 **final** 타입이면 와일드카드를 만들지 않는다 (`Box<String>` 그대로).
- 기본 동작을 바꾸려면 `@JvmWildcard`(강제 생성) 또는 `@JvmSuppressWildcards`(생성 억제)를 쓴다. 후자는 함수·클래스 전체에도 붙일 수 있다.
- `Nothing` 은 자바에 대응이 없어, 타입 인자로 쓰이면 **raw type** 으로 번역된다 (`List<Nothing>` → `List`).

```kotlin
fun unboxStrict(box: Box<@JvmSuppressWildcards Base>): Base = box.value
// Java: Base unboxStrict(Box<Base> box)
```

**사용사례:** 자바 프레임워크가 리플렉션으로 제네릭 시그니처를 읽어 "정확히 `List<Foo>` 인 파라미터" 를 찾는 경우, 코틀린이 만든 `List<? extends Foo>` 때문에 매칭이 실패할 수 있다. 이런 경계에서 `@JvmSuppressWildcards` 를 쓴다.

### 5.5 스프링에서의 변성 — 공식 문서 예

스프링 프레임워크의 [Spring Projects in Kotlin](https://docs.spring.io/spring-framework/reference/languages/kotlin/spring-projects-in.html) 문서는 타입 컨버터를 쓸 때 코틀린의 `out` 이 선언 지점 변성이라는 점(자바는 사용 지점)을 상기시키며 이런 예를 든다.

```kotlin
class ListOfFooConverter : Converter<List<Foo>, CustomJavaList<out Foo>> {
    // ...
}

class ListOfAnyConverter : Converter<List<*>, CustomJavaList<*>> {
    // ...
}
```

`List<Foo>` 는 코틀린에서 이미 `List<out Foo>` 이므로 따로 쓸 필요가 없지만, 자바 타입인 `CustomJavaList` 는 불변이므로 사용 지점에서 `out Foo` 를 붙여야 자바의 `CustomJavaList<? extends Foo>` 와 같은 의미가 된다.

---

## 6. 자바 ↔ 코틀린 제네릭 대응 요약

| 개념 | 자바 | 코틀린 |
|---|---|---|
| 기본 변성 | 불변 | 불변 (선언에 `out`/`in` 을 붙이면 변경) |
| 공변 | 사용처 `? extends T` | 선언 `out T` 또는 사용처 `out T` |
| 반공변 | 사용처 `? super T` | 선언 `in T` 또는 사용처 `in T` |
| 알 수 없는 타입 인자 | `?` | `*` |
| raw type | 존재 (`List`) | 없음 (`Nothing` 인자만 자바에서 raw 로 보임) |
| 배열 | 공변 (런타임 `ArrayStoreException`) | `Array<T>` 불변 |
| 상한 | `T extends A & B` | `T : A` + `where T : A, T : B` |
| non-null 강제 | 애노테이션 | `T : Any`, `T & Any` (1.7.0 Stable) |
| 런타임 타입 인자 | `Class<T>` 토큰 전달 | `inline` + `reified` |

---

## 7. 체크리스트

- [ ] T 를 반환만 하는 인터페이스에 `out`, 받기만 하는 인터페이스에 `in` 을 선언했는가
- [ ] 가변 컬렉션을 받는 유틸은 `MutableList<out T>`/`MutableList<in T>` 로 유연하게 했는가
- [ ] `is List<String>` 같은 소거된 타입 검사를 시도하지 않는가 (`List<*>` 사용)
- [ ] unchecked cast 는 불변식이 보장되는 한 곳에 모았는가
- [ ] 자바 프레임워크가 제네릭 시그니처를 정확히 읽어야 하는 경계에서 와일드카드 생성을 확인했는가 (`@JvmSuppressWildcards`)
- [ ] reified 로 중첩 제네릭(`List<User>`)의 원소 타입까지 얻을 수 있다고 착각하지 않았는가

---

## References

- Kotlin docs — [Generics: in, out, where](https://kotlinlang.org/docs/generics.html)
- Kotlin docs — [Inline functions (reified type parameters)](https://kotlinlang.org/docs/inline-functions.html)
- Kotlin docs — [Calling Kotlin from Java (Variant generics)](https://kotlinlang.org/docs/java-to-kotlin-interop.html)
- Kotlin docs — [Collections overview](https://kotlinlang.org/docs/collections-overview.html)
- Kotlin docs — [What's new in Kotlin 1.7.0](https://kotlinlang.org/docs/whatsnew17.html)
- Spring Framework Reference — [Kotlin: Extensions](https://docs.spring.io/spring-framework/reference/languages/kotlin/extensions.html)
- Spring Framework Reference — [Kotlin: Spring Projects in Kotlin](https://docs.spring.io/spring-framework/reference/languages/kotlin/spring-projects-in.html)

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
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/) ← 지금 글
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
