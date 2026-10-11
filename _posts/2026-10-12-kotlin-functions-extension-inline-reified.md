---
layout: post
title: "코틀린 함수 — 기본·이름 인자, 확장 함수, 고차 함수, 수신 객체 지정 람다, inline·reified"
date: 2026-10-12 00:24:42 +0900
categories: [kotlin]
tags: [kotlin, functions, extension-functions, lambda, higher-order-functions, dsl, inline, reified, context-parameters]
---

자바·코틀린 20편 시리즈의 **코틀린 4편(K4)** 이다. 코틀린 함수 문법을 다섯 묶음으로 나눈다. **(1) 선언과 호출**(기본·이름 인자, 단일 식, infix), **(2) 확장 함수**, **(3) 함수 타입과 람다**(고차 함수, SAM), **(4) 수신 객체 지정 람다와 DSL**, **(5) inline·reified**. 마지막에 2.4.0 에서 Stable 이 된 **컨텍스트 파라미터**를 짧게 붙인다.

자바 쪽 짝 글은 [J4 람다·메서드 참조·함수형 인터페이스·Stream API](https://myoungsoo7.github.io/2026/10/12/java-lambda-functional-interface-stream/) 다. 자바가 함수형 인터페이스(SAM)로 함수를 *흉내* 내는 반면, 코틀린은 함수 타입을 언어에 직접 가진다 — 공식 비교 문서가 "자바에서 고친 것" 으로 꼽는 항목이다 ([Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html)).

---

## 1. 선언과 호출

### 1.1 기본값 있는 파라미터

#### 무엇인가

파라미터에 `=` 로 기본값을 주면 호출 시 생략할 수 있다. 기본값은 상수가 아니어도 되고, **앞선 파라미터를 참조**할 수도 있다. 기본값 식은 해당 인자가 생략됐을 때만 평가된다 ([Functions](https://kotlinlang.org/docs/functions.html)).

```kotlin
fun read(
    b: ByteArray,
    off: Int = 0,
    len: Int = b.size - off,      // 앞선 파라미터 참조
) { /* ... */ }

read(bytes)            // off = 0, len = bytes.size
read(bytes, 10)        // len = bytes.size - 10
```

#### 실무 사용사례: 오버로드 폭발 제거

자바에서 `connect(host)`, `connect(host, port)`, `connect(host, port, timeout)` 처럼 텔레스코핑 오버로드를 만들던 것을 하나로 줄인다.

```kotlin
fun connect(
    host: String,
    port: Int = 5432,
    timeout: Duration = Duration.ofSeconds(3),
    ssl: Boolean = true,
): Connection = TODO()
```

#### 함정

**(1) 오버라이드는 기본값을 바꿀 수 없다.** 오버라이드하는 메서드는 항상 상위 메서드의 기본값을 쓰며, 시그니처에서 기본값을 생략해야 한다 ([Functions](https://kotlinlang.org/docs/functions.html)).

```kotlin
open class A {
    open fun foo(i: Int = 10) { /* ... */ }
}

class B : A() {
    override fun foo(i: Int) { /* ... */ }   // 기본값 지정 불가, A 의 10 이 쓰인다
}
```

**(2) 자바에서는 기본값이 안 보인다.** 자바 호출자를 위해 오버로드가 필요하면 `@JvmOverloads` 를 붙인다. 기본값 있는 파라미터마다 오버로드가 하나씩 생성된다. 단 추상 메서드·인터페이스 메서드에는 쓸 수 없다 ([Calling Kotlin from Java](https://kotlinlang.org/docs/java-to-kotlin-interop.html)).

**(3) 기본값 식의 부작용.** 기본값에 `Clock.now()` 같은 식을 쓰면 "호출 시점마다 평가" 된다는 점이 호출부에서 보이지 않는다. 테스트에서 시간을 고정하기 어려워지므로, 시간·랜덤·ID 생성은 기본값보다 주입이 낫다.

### 1.2 이름 있는 인자

#### 무엇인가

호출 시 `name = value` 로 인자를 넘기면 순서를 바꿀 수 있고, 기본값 있는 인자를 골라서 건너뛸 수 있다. 첫 번째로 건너뛴 인자 이후로는 모두 이름을 붙여야 한다 ([Functions](https://kotlinlang.org/docs/functions.html)). Kotlin 1.4.0 부터는 **위치 인자 사이에 이름 있는 인자를 섞을 수 있다**(순서가 맞는 한) ([What's new in 1.4.0](https://kotlinlang.org/docs/whatsnew14.html)).

```kotlin
fun reformat(
    str: String,
    normalizeCase: Boolean = true,
    upperCaseFirstLetter: Boolean = true,
    divideByCamelHumps: Boolean = false,
    wordSeparator: Char = ' ',
) { /* ... */ }

reformat("This is a long String!")
reformat("text", upperCaseFirstLetter = false, wordSeparator = '_')
reformat("text", true, upperCaseFirstLetter = false, false, '_')   // 1.4+ 혼합
```

`vararg` 를 이름으로 넘길 때는 스프레드 연산자 `*` 를 쓴다.

```kotlin
fun mergeStrings(vararg strings: String) { /* ... */ }
mergeStrings(strings = arrayOf("a", "b", "c"))
mergeStrings(*arrayOf("a", "b"), "c")
```

#### 실무 사용사례

- **boolean·null 인자에 이름 붙이기**: `createUser(name, true, false, null)` 는 리뷰 불가능한 코드다. `createUser(name, verified = true, admin = false, referrer = null)` 로 쓴다. 1.4.0 이 혼합을 허용한 이유로 공식 문서가 든 것이 바로 이 경우다 ([What's new in 1.4.0](https://kotlinlang.org/docs/whatsnew14.html)).
- **테스트 픽스처 빌더**: 기본값 + 이름 인자 조합이 별도 빌더 클래스를 대체한다.

```kotlin
fun anOrder(
    id: Long = 1L,
    status: OrderStatus = OrderStatus.CREATED,
    amount: Long = 10_000L,
) = Order(id, status, amount)

val paid = anOrder(status = OrderStatus.PAID)
```

#### 함정

- 이름 있는 인자는 **파라미터 이름이 공개 API 가 된다**는 뜻이다. 라이브러리에서 파라미터 이름을 바꾸면 호출부 소스가 깨진다.
- JVM 에서 **자바 함수를 호출할 때는 이름 있는 인자 문법을 쓸 수 없다.** 자바 바이트코드가 파라미터 이름을 항상 보존하지는 않기 때문이다 ([Functions](https://kotlinlang.org/docs/functions.html)).

### 1.3 단일 식 함수와 반환 타입

블록 본문 함수는 `Unit` 이 아닌 한 반환 타입을 명시해야 한다. 단일 식 함수는 반환 타입을 추론할 수 있다 ([Functions](https://kotlinlang.org/docs/functions.html)).

```kotlin
fun double(x: Int): Int = x * 2
fun triple(x: Int) = x * 3                  // Int 로 추론

fun log(msg: String) { println(msg) }       // Unit 생략 가능
```

**함정**: public API 에서 단일 식 함수의 반환 타입을 생략하면, 구현 식이 바뀔 때 반환 타입이 *조용히* 바뀐다(예: `List` → `MutableList`). 라이브러리·모듈 경계 함수는 반환 타입을 명시하라.

### 1.4 infix 함수

`infix` 를 붙이면 점과 괄호 없이 호출할 수 있다. 조건은 (1) 멤버 함수이거나 확장 함수, (2) 파라미터가 정확히 하나, (3) 그 파라미터가 vararg 가 아니고 기본값이 없을 것 ([Functions](https://kotlinlang.org/docs/functions.html)).

```kotlin
infix fun Money.plusMoney(other: Money): Money {
    require(currency == other.currency)
    return Money(amount + other.amount, currency)
}

val total = a plusMoney b
val pair = "key" to "value"      // 표준 라이브러리의 infix fun to
```

**함정**: 도메인 연산을 전부 infix 로 만들면 연산자 우선순위가 직관과 어긋나고 읽기 어려워진다. `to`, 테스트 매처처럼 **영어 문장처럼 읽히는 경우**로 한정하라.

---

## 2. 확장 함수와 확장 프로퍼티

### 2.1 무엇인가

기존 클래스를 수정하거나 상속하지 않고 그 클래스에 "메서드처럼 보이는" 함수를 추가한다.

```kotlin
fun String.isValidEmail(): Boolean = contains('@') && substringAfter('@').contains('.')

"a@b.com".isValidEmail()   // true
```

### 2.2 핵심 규칙 1: 정적으로 디스패치된다

확장 함수는 **정적으로 디스패치**된다. 컴파일러는 *런타임 실제 타입*이 아니라 **선언된 타입**을 보고 어떤 확장을 부를지 정한다 ([Extensions](https://kotlinlang.org/docs/extensions.html)).

```kotlin
open class Shape
class Rectangle : Shape()

fun Shape.getName() = "Shape"
fun Rectangle.getName() = "Rectangle"

fun printClassName(s: Shape) {
    println(s.getName())
}

printClassName(Rectangle())   // "Shape" — 선언 타입 Shape 기준
```

**함정**: 확장 함수로 다형성을 흉내내지 마라. 하위 타입별로 동작이 달라야 하면 멤버 함수(오버라이드)나 sealed + `when` 을 써라.

### 2.3 핵심 규칙 2: 멤버가 이긴다

같은 수신 타입, 같은 이름, 호환되는 인자의 멤버 함수가 있으면 **멤버 함수가 우선**한다 ([Extensions](https://kotlinlang.org/docs/extensions.html)).

```kotlin
class Example {
    fun printFunctionType() { println("Member function") }
}

fun Example.printFunctionType() { println("Extension function") }

Example().printFunctionType()   // "Member function"
```

**함정**: 라이브러리 클래스에 확장 함수를 만들었는데, 라이브러리가 업그레이드되며 같은 시그니처의 멤버를 추가하면 **호출이 조용히 멤버로 바뀐다.** 범용적인 이름(`toDto`, `validate`)보다 도메인 특화된 이름을 쓰는 것이 방어가 된다.

### 2.4 nullable 수신 객체

수신 타입을 nullable 로 선언하면 null 인 변수에도 호출할 수 있다. 본문에서 `this` 는 null 일 수 있다 ([Extensions](https://kotlinlang.org/docs/extensions.html)).

```kotlin
fun String?.orDash(): String = if (this.isNullOrBlank()) "-" else this

val nick: String? = null
println(nick.orDash())   // "-" — ?. 없이 호출
```

표준 라이브러리의 `isNullOrBlank()`, `orEmpty()` 가 이 방식이다.

### 2.5 확장 프로퍼티

확장은 실제로 클래스에 멤버를 추가하지 않으므로 **backing field 를 가질 수 없고, 초기화식도 쓸 수 없다.** getter/setter 로만 정의한다 ([Extensions](https://kotlinlang.org/docs/extensions.html)).

```kotlin
val <T> List<T>.lastIndexOrNull: Int?
    get() = if (isEmpty()) null else size - 1

// val House.number = 1   // 에러: 확장 프로퍼티에는 초기화식을 쓸 수 없다
```

### 2.6 실무 사용사례

```kotlin
// (1) 매핑 — 도메인 ↔ DTO 변환을 도메인 클래스 밖에 둔다
fun Order.toResponse(): OrderResponse =
    OrderResponse(id = id, status = status.name, amount = amount)

// (2) 자바 라이브러리 API 를 코틀린답게
fun ResultSet.getLongOrNull(column: String): Long? =
    getLong(column).takeUnless { wasNull() }

// (3) 테스트 가독성
fun Order.shouldBePaid() = check(status == OrderStatus.PAID) { "expected PAID but was $status" }
```

**왜 (1)이 좋은가**: 도메인 클래스가 웹 계층 DTO 를 알 필요가 없다. 의존 방향(웹 → 도메인)을 지키면서 `order.toResponse()` 라는 자연스러운 호출을 얻는다.

### 2.7 함정 정리

| 함정 | 설명 |
|---|---|
| 정적 디스패치 | 다형성이 필요하면 확장이 아니다 |
| 멤버 우선 | 라이브러리 업그레이드로 동작이 바뀔 수 있다 |
| private 접근 불가 | 확장은 클래스 밖 함수라 private 멤버에 접근하지 못한다 |
| 전역 오염 | `String`, `Any` 에 확장을 남발하면 IDE 자동완성이 오염된다. 패키지·가시성(`private`, `internal`)으로 범위를 좁혀라 |

---

## 3. 함수 타입, 람다, 고차 함수

### 3.1 함수 타입

`(A, B) -> C` 는 A, B 를 받아 C 를 반환하는 함수 타입이다. 수신 객체가 있는 함수 타입은 `A.(B) -> C` 로 쓴다 ([Higher-order functions and lambdas](https://kotlinlang.org/docs/lambdas.html)).

```kotlin
val add: (Int, Int) -> Int = { a, b -> a + b }
val isEven: (Int) -> Boolean = { it % 2 == 0 }
val handler: ((String) -> Unit)? = null          // nullable 함수 타입
```

### 3.2 고차 함수

함수를 인자로 받거나 반환하는 함수다. 공식 문서의 `fold` 예를 단순화하면:

```kotlin
fun <T, R> Collection<T>.fold(
    initial: R,
    combine: (acc: R, nextElement: T) -> R,
): R {
    var accumulator: R = initial
    for (element: T in this) {
        accumulator = combine(accumulator, element)
    }
    return accumulator
}

val sum = listOf(1, 2, 3).fold(0) { acc, x -> acc + x }
```

### 3.3 람다 문법 규칙

| 규칙 | 예 | 출처 |
|---|---|---|
| 마지막 파라미터가 함수면 괄호 밖으로 (trailing lambda) | `items.forEach { println(it) }` | [lambdas](https://kotlinlang.org/docs/lambdas.html) |
| 파라미터가 하나면 암묵적 이름 `it` | `ints.filter { it > 0 }` | 〃 |
| 마지막 식이 반환값 | `{ x -> val y = x * 2; y + 1 }` | 〃 |
| 람다에서 명시적 반환은 레이블 | `return@filter shouldFilter` | 〃 |
| 반환 타입을 명시하려면 익명 함수 | `fun(s: String): Int { return s.length }` | 〃 |

```kotlin
ints.filter {
    val shouldFilter = it > 0
    return@filter shouldFilter
}
```

### 3.4 람다 안의 `return` — 가장 자주 틀리는 부분

일반(비 inline) 함수에 넘긴 람다 안에서는 **레이블 없는 `return` 이 금지**된다. 람다가 바깥 함수를 반환시킬 수 없기 때문이다. 하지만 **inline 함수**에 넘긴 람다에서는 허용되고, 이것은 바깥 함수를 반환시킨다 — 이를 **non-local return** 이라 한다 ([Inline functions](https://kotlinlang.org/docs/inline-functions.html)).

```kotlin
fun hasZero(list: List<Int>): Boolean {
    list.forEach {
        if (it == 0) return true     // forEach 는 inline → hasZero 자체가 true 반환
    }
    return false
}

fun printUntilZero(list: List<Int>) {
    list.forEach {
        if (it == 0) return@forEach  // 이번 원소만 건너뜀 (continue 처럼)
        println(it)
    }
}
```

**함정**: `return@forEach` 는 `break` 가 아니라 `continue` 처럼 동작한다. 루프를 중단하려면 일반 `for` 루프를 쓰거나, 아래의 non-local `break` 를 쓴다.

**non-local `break`/`continue`**: inline 함수에 넘긴 람다 안에서 바깥 루프에 대한 `break`/`continue` 를 쓰는 기능이 2.1.0 프리뷰를 거쳐 **2.2.0 에서 Stable** 이 됐다 ([What's new in 2.2.0](https://kotlinlang.org/docs/whatsnew22.html), [Inline functions](https://kotlinlang.org/docs/inline-functions.html)).

```kotlin
// 공식 문서 예제를 단순화
fun processList(elements: List<Element>): Boolean {
    for (element in elements) {
        val variable = element.nullableMethod() ?: run {
            log.warn("Element is null or invalid, continuing...")
            continue                       // run 은 inline → 바깥 for 의 다음 반복으로 (2.2.0+)
        }
        if (variable == 0) return true
    }
    return false
}
```

### 3.5 SAM 변환과 `fun interface`

자바의 단일 추상 메서드(SAM) 인터페이스에는 람다를 그대로 넘길 수 있다. **코틀린 인터페이스**에 SAM 변환을 쓰려면 `fun interface` 로 선언해야 하며, 이 기능은 **Kotlin 1.4.0** 에서 도입됐다 ([What's new in 1.4.0](https://kotlinlang.org/docs/whatsnew14.html), [Functional (SAM) interfaces](https://kotlinlang.org/docs/fun-interfaces.html)).

```kotlin
fun interface IntPredicate {
    fun accept(i: Int): Boolean
}

val isEven = IntPredicate { it % 2 == 0 }

// 자바 SAM 은 원래 가능
val r = Runnable { println("run") }
executor.execute { println("in pool") }
```

SAM 변환은 인터페이스에만 동작하고 추상 클래스에는 동작하지 않는다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

#### 함수 타입이냐 `fun interface` 냐

| 상황 | 선택 |
|---|---|
| 코틀린 내부에서만 쓰는 콜백 | 함수 타입 `(T) -> R` (+ 필요하면 `typealias`) |
| 자바에서도 구현·호출할 API | `fun interface` (자바 쪽에서 이름 있는 인터페이스로 보임) |
| 메서드 이름 자체가 의미를 가질 때 | `fun interface` |

---

## 4. 수신 객체 지정 람다와 DSL

### 4.1 무엇인가

`A.(B) -> C` 타입의 람다 안에서는 수신 객체 `A` 가 `this` 가 된다. 확장 함수의 람다 버전이다 ([Higher-order functions and lambdas](https://kotlinlang.org/docs/lambdas.html)).

```kotlin
val sum: Int.(Int) -> Int = { other -> this + other }
println(2.sum(3))      // 5
println(sum(2, 3))     // 5 — 수신 객체를 첫 인자로 넘길 수도 있다
```

### 4.2 코드 예제: 직접 만드는 빌더

```kotlin
class HttpRequestSpec {
    var method: String = "GET"
    var url: String = ""
    private val headers = mutableMapOf<String, String>()
    fun header(name: String, value: String) { headers[name] = value }
    fun build(): HttpRequest = HttpRequest(method, url, headers.toMap())
}

fun request(block: HttpRequestSpec.() -> Unit): HttpRequest =
    HttpRequestSpec().apply(block).build()

val req = request {
    method = "POST"
    url = "https://api.example.com/orders"
    header("Content-Type", "application/json")
}
```

`apply` 자체가 `T.() -> Unit` 을 받는 수신 객체 지정 람다의 대표 예다(K5).

### 4.3 실무 사용사례

- Gradle Kotlin DSL (`build.gradle.kts`) 의 `dependencies { ... }`
- 스프링의 코틀린 DSL — `router { }`, `beans { }`, MockMvc DSL (K10 에서 다룬다)
- 테스트 데이터 빌더, HTML/SQL 빌더

### 4.4 함정과 `@DslMarker`

중첩된 수신 객체 지정 람다에서는 **바깥 수신 객체의 멤버도 암묵적으로 보인다.** 그래서 `table { tr { tr { } } }` 처럼 안쪽에서 바깥 빌더의 함수를 실수로 호출할 수 있다. `@DslMarker` 로 표시한 애노테이션을 빌더 클래스에 붙이면 같은 DSL 의 바깥 암묵적 수신 객체 접근이 막힌다 ([Type-safe builders](https://kotlinlang.org/docs/type-safe-builders.html)).

```kotlin
@DslMarker
annotation class HtmlTagMarker

@HtmlTagMarker
abstract class Tag(val name: String) { /* ... */ }

// 이제 tr { tr { } } 는 컴파일 에러 — 바깥 수신 객체는 this@table 처럼 명시해야 한다
```

---

## 5. inline 함수

### 5.1 무엇인가 — 왜 필요한가

고차 함수에는 런타임 비용이 있다. 함수 하나하나가 객체이고 클로저를 캡처하며, 함수 객체·클래스의 메모리 할당과 가상 호출이 오버헤드가 된다. `inline` 을 붙이면 컴파일러가 함수 본문과 넘겨진 람다를 **호출 지점에 복사**해 이 비용을 없앤다 ([Inline functions](https://kotlinlang.org/docs/inline-functions.html)).

```kotlin
inline fun <T> lockAndRun(lock: java.util.concurrent.locks.Lock, body: () -> T): T {
    lock.lock()
    try {
        return body()
    } finally {
        lock.unlock()
    }
}

// 호출부는 사실상 lock(); try { foo() } finally { unlock() } 로 펼쳐진다
lockAndRun(l) { foo() }
```

표준 라이브러리의 `let`, `run`, `apply`, `also`, `with`, `takeIf` 가 모두 `public inline fun` 이다 ([Standard.kt 소스](https://github.com/JetBrains/kotlin/blob/master/libraries/stdlib/src/kotlin/util/Standard.kt)). 그래서 스코프 함수는 람다 객체 할당 없이 쓸 수 있다.

### 5.2 `noinline` 과 `crossinline`

| 수식어 | 의미 | 쓰는 경우 |
|---|---|---|
| (기본) | 람다도 인라인. non-local return 허용 | 대부분 |
| `noinline` | 이 람다는 인라인하지 않음. 저장·전달 가능 | 람다를 필드에 저장하거나 다른 비 inline 함수에 넘길 때 |
| `crossinline` | 인라인은 하되 non-local return 금지 | 람다를 다른 실행 컨텍스트(지역 객체, 중첩 함수)에서 호출할 때 |

출처: [Inline functions](https://kotlinlang.org/docs/inline-functions.html)

```kotlin
inline fun <T> measured(
    name: String,
    noinline onSlow: (Long) -> Unit,      // 비 inline 함수에 넘겨야 하므로 noinline
    block: () -> T,                       // 이 람다는 인라인됨
): T {
    val start = System.nanoTime()
    val result = block()
    reportIfSlow(name, System.nanoTime() - start, onSlow)
    return result
}

fun reportIfSlow(name: String, elapsed: Long, onSlow: (Long) -> Unit) {
    if (elapsed > 1_000_000_000L) onSlow(elapsed)
}

inline fun runLater(crossinline body: () -> Unit) {
    val task = Runnable { body() }        // 다른 컨텍스트에서 호출 → crossinline 필요
    executor.execute(task)
}
```

### 5.3 함정

**(1) 람다 파라미터가 없으면 inline 은 의미가 없다.** inline 할 함수 파라미터도 reified 타입 파라미터도 없으면 컴파일러가 경고한다 ([Inline functions](https://kotlinlang.org/docs/inline-functions.html)).

**(2) 큰 함수를 inline 하면 코드가 커진다.** 공식 문서도 인라인은 생성 코드를 키울 수 있으니 큰 함수의 인라인을 피하라고 한다 ([Inline functions](https://kotlinlang.org/docs/inline-functions.html)).

**(3) public inline 함수는 비공개 선언을 쓸 수 없다.** public/protected inline 함수는 다른 모듈의 호출 지점에 본문이 복사되므로 모듈의 공개 API 로 취급된다. 그래서 `private`/`internal` 선언을 본문에서 쓸 수 없다. `internal` 선언에 `@PublishedApi` 를 붙이면 허용된다 ([Inline functions](https://kotlinlang.org/docs/inline-functions.html)).

```kotlin
@PublishedApi
internal fun logInternal(msg: String) { /* ... */ }

inline fun <T> traced(name: String, block: () -> T): T {
    logInternal("start $name")       // @PublishedApi 덕분에 OK
    return block().also { logInternal("end $name") }
}
```

**(4) 라이브러리 inline 함수의 수정은 재컴파일 전까지 반영되지 않는다.** 본문이 호출 측 바이트코드에 복사되기 때문이다. 공식 문서가 public inline 함수의 제약을 둔 이유도 이 바이너리 호환 문제다.

---

## 6. reified 타입 파라미터

### 6.1 무엇인가

코틀린 제네릭도 자바처럼 런타임에 타입 인자가 소거된다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)). 그래서 일반 제네릭 함수 안에서는 `x is T` 나 `T::class` 를 쓸 수 없다. **inline 함수**는 호출 지점에 복사되므로, 타입 파라미터에 `reified` 를 붙이면 실제 타입이 그 자리에 박혀 `is`, `as`, `T::class` 를 쓸 수 있다 ([Inline functions — Reified type parameters](https://kotlinlang.org/docs/inline-functions.html)).

```kotlin
// reified 없이: Class 객체를 직접 넘겨야 한다
fun <T> TreeNode.findParentOfType(clazz: Class<T>): T? {
    var p = parent
    while (p != null && !clazz.isInstance(p)) {
        p = p.parent
    }
    @Suppress("UNCHECKED_CAST")
    return p as T?
}

// reified: 타입 인자만으로
inline fun <reified T> TreeNode.findParentOfType(): T? {
    var p = parent
    while (p != null && p !is T) {
        p = p.parent
    }
    return p as T?
}

val owner = node.findParentOfType<MyTreeNodeType>()
```

### 6.2 실무 사용사례

```kotlin
// (1) 역직렬화 헬퍼 — Class/TypeReference 인자 제거
inline fun <reified T> ObjectMapper.readAs(json: String): T =
    readValue(json, object : com.fasterxml.jackson.core.type.TypeReference<T>() {})

val orders: List<OrderDto> = mapper.readAs(json)

// (2) 타입별 필터
inline fun <reified T> List<Any>.only(): List<T> = filterIsInstance<T>()

// (3) 로거
inline fun <reified T : Any> loggerFor(): org.slf4j.Logger =
    org.slf4j.LoggerFactory.getLogger(T::class.java)
```

(1) 에서 `TypeReference<T>` 를 익명 객체로 만들 때 `T` 가 reified 이므로 `List<OrderDto>` 라는 **완전한 제네릭 타입**이 익명 클래스의 상위 타입 정보에 기록된다. 자바에서 `new TypeReference<List<OrderDto>>() {}` 를 매번 쓰던 것을 호출부에서 없앤다.

### 6.3 함정

- **비 inline 함수는 reified 를 가질 수 없다.** 또 런타임 표현이 없는 타입(비 reified 타입 파라미터, `Nothing` 같은 가상 타입)은 reified 타입 인자로 쓸 수 없다 ([Inline functions](https://kotlinlang.org/docs/inline-functions.html)). 즉 reified 함수를 *다른 제네릭 함수 안에서* `T` 로 부르면 컴파일 에러다 — 그 바깥 함수도 inline + reified 여야 한다.
- reified 는 "리플렉션이 필요 없어진다" 는 뜻이지만, `T::class.members` 처럼 리플렉션을 같이 쓸 수도 있다.
- reified 함수는 자바에서 호출할 수 없다(자바 컴파일러는 인라인을 하지 못한다). 자바 사용자가 있는 API 라면 `Class<T>` 를 받는 비 inline 오버로드를 함께 제공하라.

제네릭 변성(in/out)과 reified 의 관계는 [K8](https://myoungsoo7.github.io/2026/10/12/kotlin-generics-variance-in-out/), 자바의 타입 소거는 [J2](https://myoungsoo7.github.io/2026/10/12/java-type-system-generics-erasure-pecs/) 에서 다룬다.

---

## 7. 컨텍스트 파라미터 (2.4.0 Stable)

### 7.1 무엇인가

함수·프로퍼티가 **주변 컨텍스트에서 암묵적으로 제공되는 의존성**을 선언하는 기능이다. 여러 호출에 걸쳐 거의 바뀌지 않는 서비스·의존성을 매번 인자로 넘기지 않아도 된다 ([Context parameters](https://kotlinlang.org/docs/context-parameters.html)).

- 2.2.0 에서 프리뷰로 도입, 기존 실험 기능 **컨텍스트 리시버(context receivers)를 대체** ([What's new in 2.2.0](https://kotlinlang.org/docs/whatsnew22.html))
- **2.4.0 에서 Stable** — 단, 컨텍스트 인자(context arguments)와 callable reference 는 제외 ([What's new in 2.4.0](https://kotlinlang.org/docs/whatsnew24.html))
- 컨텍스트 리시버와의 핵심 차이: 컨텍스트 파라미터는 함수 본문에서 수신 객체로 들어오지 않으므로 **이름으로 멤버에 접근**해야 한다 ([What's new in 2.2.0](https://kotlinlang.org/docs/whatsnew22.html))

### 7.2 코드 예제

```kotlin
interface UserService {
    fun log(message: String)
    fun findUserById(id: Int): String
}

context(users: UserService)
fun outputMessage(message: String) {
    users.log("Log: $message")
}

context(users: UserService)
val firstUser: String
    get() = users.findUserById(1)
```

호출은 해당 타입의 컨텍스트가 있는 스코프에서 한다. 공식 문서는 `context()` 함수 같은 방법을 안내한다 ([Context parameters](https://kotlinlang.org/docs/context-parameters.html)).

### 7.3 실무 판단

- **스프링 애플리케이션의 서비스 의존성**은 여전히 생성자 주입이 기본이다. 컨텍스트 파라미터는 DI 컨테이너의 대체재가 아니라, 로깅·트랜잭션 스코프·DSL 처럼 **호출 체인 전체에 흐르는 문맥**을 표현하는 도구로 보는 것이 맞다.
- 명시적 컨텍스트 인자(`-Xexplicit-context-arguments`)는 2.4.0 기준 아직 Experimental 이다 ([Context parameters](https://kotlinlang.org/docs/context-parameters.html)). 공용 라이브러리 API 에는 Stable 범위만 쓰라.

---

## 8. 정리

| 문법 | 한 줄 요약 | 대표 함정 |
|---|---|---|
| 기본값 인자 | 오버로드 대체 | 오버라이드는 기본값 못 바꿈, 자바엔 `@JvmOverloads` |
| 이름 있는 인자 | boolean/null 인자에 이름 | 파라미터 이름이 API 가 됨 |
| 확장 함수 | 클래스 밖에서 메서드처럼 | 정적 디스패치, 멤버 우선 |
| 함수 타입·람다 | 진짜 함수 타입 | 람다 안 `return` 규칙 |
| `fun interface` | 코틀린 SAM (1.4+) | 추상 클래스는 SAM 불가 |
| 수신 객체 지정 람다 | DSL 의 기반 | 바깥 수신 객체 누출 → `@DslMarker` |
| `inline` | 람다 할당 제거, non-local return | 코드 크기, public API 제약 |
| `reified` | 소거 우회 | inline 전용, 자바에서 호출 불가 |
| 컨텍스트 파라미터 | 암묵적 의존성 (2.4 Stable) | 일부 기능은 아직 Experimental |

다음 글 [K5 스코프 함수](https://myoungsoo7.github.io/2026/10/12/kotlin-scope-functions-use-cases/) 에서는 이 글의 inline + 수신 객체 지정 람다가 결합된 `let`/`run`/`with`/`apply`/`also` 를 다룬다.

---

## References

- Functions — https://kotlinlang.org/docs/functions.html
- Extensions — https://kotlinlang.org/docs/extensions.html
- Higher-order functions and lambdas — https://kotlinlang.org/docs/lambdas.html
- Functional (SAM) interfaces — https://kotlinlang.org/docs/fun-interfaces.html
- Inline functions (noinline, crossinline, non-local returns, reified, @PublishedApi) — https://kotlinlang.org/docs/inline-functions.html
- Type-safe builders (@DslMarker) — https://kotlinlang.org/docs/type-safe-builders.html
- Context parameters — https://kotlinlang.org/docs/context-parameters.html
- Calling Java from Kotlin — https://kotlinlang.org/docs/java-interop.html
- Calling Kotlin from Java (@JvmOverloads) — https://kotlinlang.org/docs/java-to-kotlin-interop.html
- Comparison to Java — https://kotlinlang.org/docs/comparison-to-java.html
- Kotlin stdlib source, Standard.kt — https://github.com/JetBrains/kotlin/blob/master/libraries/stdlib/src/kotlin/util/Standard.kt
- What's new in Kotlin 1.4.0 (fun interface, mixing named and positional arguments) — https://kotlinlang.org/docs/whatsnew14.html
- What's new in Kotlin 2.2.0 (non-local break/continue stable, context parameters preview) — https://kotlinlang.org/docs/whatsnew22.html
- What's new in Kotlin 2.4.0 (context parameters stable) — https://kotlinlang.org/docs/whatsnew24.html

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
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/) ← 지금 글
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
