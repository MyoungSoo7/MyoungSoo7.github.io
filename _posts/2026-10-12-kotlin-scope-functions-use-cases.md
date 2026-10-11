---
layout: post
title: "코틀린 스코프 함수 let·run·with·apply·also — 언제 무엇을 쓰나, 그리고 남용의 함정"
date: 2026-10-12 00:25:42 +0900
categories: [kotlin]
tags: [kotlin, scope-functions, let, run, with, apply, also, takeIf, readability, code-review]
---

자바·코틀린 20편 시리즈의 **코틀린 5편(K5)** 이다. 코틀린 코드 리뷰에서 가장 자주 의견이 갈리는 주제가 스코프 함수다. 다섯 개가 기술적으로 거의 같은 일을 하기 때문에 "아무거나 써도 된다" 와 "아무것도 쓰지 마라" 사이에서 팀마다 기준이 흔들린다. 이 글은 공식 문서의 기준을 뼈대로 삼아 (1) 다섯 함수를 **두 개의 축**으로 분류하고, (2) 각각의 정석 사용사례를 보여준 뒤, (3) 실무에서 반복해서 보이는 **남용 패턴**을 카탈로그로 정리한다.

스코프 함수는 [K4](https://myoungsoo7.github.io/2026/10/12/kotlin-functions-extension-inline-reified/) 에서 다룬 **inline 함수 + 수신 객체 지정 람다**의 조합이고, `?.let` 은 [K2 널 안전](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/) 의 핵심 관용구다. 자바에는 직접 대응하는 문법이 없다. 굳이 비교하자면 `Optional.map`/`ifPresent`([J5](https://myoungsoo7.github.io/2026/10/12/java-null-optional-exceptions/)) 와 빌더 패턴이 일부 역할을 나눠 갖는다.

---

## 1. 스코프 함수란 무엇인가

### 1.1 공식 정의

표준 라이브러리에는 **객체의 문맥 안에서 코드 블록을 실행하는 것이 유일한 목적인** 함수들이 있다. 람다와 함께 호출하면 임시 스코프가 생기고, 그 안에서 객체를 이름 없이 접근한다. 이것을 스코프 함수라 부르며 `let`, `run`, `with`, `apply`, `also` 다섯 개다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

공식 문서가 강조하는 문장 하나:

> 스코프 함수는 새로운 기술적 능력을 도입하지 않는다. 다만 코드를 더 간결하고 읽기 쉽게 만들 수 있다. ([Scope functions](https://kotlinlang.org/docs/scope-functions.html))

즉 스코프 함수를 쓸지 말지는 **오로지 가독성의 문제**다. 가독성을 해친다면 쓰지 않는 것이 정답이다.

### 1.2 실제 시그니처

표준 라이브러리 소스 [Standard.kt](https://github.com/JetBrains/kotlin/blob/master/libraries/stdlib/src/kotlin/util/Standard.kt) 에서 그대로 가져온 선언이다(본문 생략).

```kotlin
public inline fun <R> run(block: () -> R): R
public inline fun <T, R> T.run(block: T.() -> R): R
public inline fun <T, R> with(receiver: T, block: T.() -> R): R
public inline fun <T> T.apply(block: T.() -> Unit): T
public inline fun <T> T.also(block: (T) -> Unit): T
public inline fun <T, R> T.let(block: (T) -> R): R
public inline fun <T> T.takeIf(predicate: (T) -> Boolean): T?
public inline fun <T> T.takeUnless(predicate: (T) -> Boolean): T?
```

시그니처만 보면 차이가 전부 드러난다.

- 람다 타입이 `T.() -> ...` 이면 객체가 **`this`(수신 객체)**, `(T) -> ...` 이면 **`it`(인자)**
- 반환 타입이 `R` 이면 **람다 결과**, `T` 면 **객체 자신**
- 모두 `inline` 이므로 람다 객체 할당이 없다 (K4 5.1절)

또한 모든 함수가 본문에서 `contract { callsInPlace(block, InvocationKind.EXACTLY_ONCE) }` 를 선언한다 ([Standard.kt](https://github.com/JetBrains/kotlin/blob/master/libraries/stdlib/src/kotlin/util/Standard.kt)). 컴파일러에게 "이 람다는 그 자리에서 정확히 한 번 호출된다" 고 알려주는 계약으로, 람다 안팎의 초기화·스마트 캐스트 분석이 일반 람다보다 정확해진다.

---

## 2. 두 개의 축으로 분류하기

### 2.1 분류표

공식 문서의 선택 표를 옮긴다 ([Scope functions — Function selection](https://kotlinlang.org/docs/scope-functions.html)).

| 함수 | 객체 참조 | 반환값 | 확장 함수인가 |
|---|---|---|---|
| `let` | `it` | 람다 결과 | 예 |
| `run` | `this` | 람다 결과 | 예 |
| `run` (비확장) | — | 람다 결과 | 아니오: 문맥 객체 없이 호출 |
| `with` | `this` | 람다 결과 | 아니오: 문맥 객체를 인자로 받음 |
| `apply` | `this` | 문맥 객체 | 예 |
| `also` | `it` | 문맥 객체 | 예 |

2×2 로 접으면 이렇게 기억할 수 있다.

|  | 람다 결과 반환 | 객체 자신 반환 |
|---|---|---|
| **`this`** | `run`, `with` | `apply` |
| **`it`** | `let` | `also` |

### 2.2 축 1: `this` 냐 `it` 이냐

공식 문서의 기준 ([Scope functions — Context object: this or it](https://kotlinlang.org/docs/scope-functions.html)):

- **`this`(run, with, apply)**: 대부분 `this` 를 생략할 수 있어 짧아진다. 하지만 생략하면 수신 객체의 멤버와 바깥 객체·함수를 구분하기 어려워진다. 그래서 **객체의 멤버를 주로 호출하거나 프로퍼티에 값을 대입하는** 람다에 권장된다.
- **`it`(let, also)**: 객체를 **다른 함수의 인자로 주로 넘길 때** 낫다. 블록 안에서 여러 변수를 쓸 때도 낫다. 필요하면 `it` 대신 이름을 줄 수 있다.

```kotlin
// this — 객체 자신의 멤버를 설정
val adam = Person("Adam").apply {
    age = 20
    city = "London"
}

// it — 객체를 다른 함수의 인자로
fun getRandomInt(): Int =
    Random.nextInt(100).also { value ->
        writeToLog("getRandomInt() generated value $value")
    }
```

### 2.3 축 2: 무엇을 반환하나

공식 문서 ([Scope functions — Return value](https://kotlinlang.org/docs/scope-functions.html)):

- **`apply`, `also`** 는 문맥 객체를 반환한다 → 같은 객체에 대한 호출 체인 중간에 "곁가지 단계" 로 끼울 수 있고, 문맥 객체를 반환하는 함수의 `return` 문에 쓸 수 있다.
- **`let`, `run`, `with`** 는 람다 결과를 반환한다 → 결과를 변수에 대입하거나 결과에 대해 체인을 이어갈 때 쓴다. 반환값을 무시하고 지역 변수의 임시 스코프를 만드는 데 쓸 수도 있다.

---

## 3. 함수별 정석 사용법

### 3.1 `let` — non-null 일 때 실행 / 결과 변환 / 지역 스코프

#### 무엇인가

객체를 `it` 으로 받고 람다 결과를 반환한다.

#### 정석 사용사례 (공식 문서 기준)

**(1) null 이 아닐 때만 실행 — `?.let`**

```kotlin
val length = str?.let {
    println("let() called on $it")
    processNonNullString(it)    // 블록 안에서 it 은 non-null
    it.length
}
```

**(2) 호출 체인 결과에 한 번 더 작업**

```kotlin
numbers.map { it.length }.filter { it > 3 }.let(::println)
```

람다가 `it` 을 인자로 받는 함수 하나만 호출하면 메서드 참조(`::`)로 바꿀 수 있다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

**(3) 범위가 제한된 지역 변수 도입**

```kotlin
val modifiedFirstItem = numbers.first().let { firstItem ->
    if (firstItem.length >= 5) firstItem else "!$firstItem!"
}.uppercase()
```

#### 함정

- `x?.let { foo(it) }` 은 좋지만 `x.let { foo(it) }` (non-null 인데 let) 은 그냥 `foo(x)` 다. **null 처리도, 스코프 제한도 아닌 let 은 소음이다.**
- 중첩 `let` 에서 `it` 이 여러 개 겹치면 어느 `it` 인지 알 수 없다. 바깥은 반드시 이름을 줘라(아래 5.2절).

### 3.2 `with` — 반환값이 필요 없는 그룹 호출

#### 무엇인가

확장 함수가 아니다. 문맥 객체를 인자로 넘기고, 람다 안에서는 `this` 로 접근한다. 람다 결과를 반환한다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

#### 정석 사용사례

공식 문서는 **반환 결과가 필요 없을 때 문맥 객체의 함수들을 호출**하는 데 `with` 를 권한다. "이 객체를 가지고, 다음을 하라" 로 읽힌다. 또한 값을 계산하는 데 쓰이는 **헬퍼 객체**를 도입하는 데도 쓴다.

```kotlin
with(numbers) {
    println("'with' is called with argument $this")
    println("It contains $size elements")
}

val firstAndLast = with(numbers) {
    "The first element is ${first()}, the last element is ${last()}"
}
```

실무 예: 렌더러·매퍼처럼 여러 멤버를 연달아 쓰는 코드.

```kotlin
fun render(report: Report): String = with(StringBuilder()) {
    appendLine("# ${report.title}")
    report.rows.forEach { appendLine("- ${it.name}: ${it.value}") }
    toString()
}
```

#### 함정

- `with` 는 확장 함수가 아니라 **nullable 객체에 안전 호출을 할 수 없다.** `with(user) { ... }` 에서 `user` 가 `User?` 면 블록 안 모든 접근에 `?.` 가 필요해진다. 이 경우는 `user?.run { ... }` 이 맞다.

### 3.3 `run` — 초기화 + 결과 계산 / 식이 필요한 곳의 블록

#### 무엇인가

확장 `run` 은 `with` 와 같은 일을 하되 확장 함수라 `.` 으로 호출하고 `?.run` 도 된다. 비확장 `run` 은 문맥 객체 없이 블록을 실행하고 결과를 반환한다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

#### 정석 사용사례

**(1) 객체를 설정하면서 결과를 계산 (확장 run)** — 공식 문서: "람다가 객체를 초기화하면서 반환값도 계산할 때 유용"

```kotlin
val result = service.run {
    port = 8080
    query(prepareRequest() + " to port $port")
}
```

**(2) 식이 필요한 자리에서 여러 문장 실행 (비확장 run)**

```kotlin
val hexNumberRegex = run {
    val digits = "0-9"
    val hexDigits = "A-Fa-f"
    val sign = "+-"
    Regex("[$sign]?[$digits$hexDigits]+")
}
```

**(3) 엘비스 오른쪽의 여러 문장**

```kotlin
val user = repository.findByIdOrNull(id) ?: run {
    log.warn("user not found: $id")
    return ResponseEntity.notFound().build()
}
```

#### 함정

- 확장 `run` 과 비확장 `run` 이 이름이 같아, 수신 객체를 빠뜨린 실수가 컴파일 에러 없이 다른 의미가 된다. `foo.run { }` 과 `run { }` 은 전혀 다르다.
- `?.let { ... } ?: run { ... }` 를 if-else 대용으로 쓰는 함정은 5.3절에서 다룬다.

### 3.4 `apply` — 객체 설정

#### 무엇인가

`this` 로 받고 **객체 자신**을 반환한다. 공식 문서는 값을 반환하지 않고 **주로 수신 객체의 멤버를 다루는** 블록에 `apply` 를 권하며, 가장 흔한 용도가 **객체 설정(configuration)** 이라고 설명한다. "다음 대입들을 이 객체에 적용하라" 로 읽힌다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

#### 정석 사용사례

```kotlin
// 자바 빈 스타일 객체 설정 — setter 연쇄를 대체
val dataSource = HikariDataSource().apply {
    jdbcUrl = props.url
    username = props.username
    password = props.password
    maximumPoolSize = 20
}

// 테스트 픽스처
val request = MockHttpServletRequest().apply {
    method = "POST"
    requestURI = "/orders"
    addHeader("X-Request-Id", "abc")
}
```

#### 함정

- **`apply` 블록의 마지막 식은 버려진다.** `val x = builder.apply { build() }` 는 빌드 결과가 아니라 **빌더 자신**을 반환한다. 결과가 필요하면 `run` 이다.

```kotlin
val wrong = StringBuilder().apply { append("a"); toString() }   // StringBuilder
val right = StringBuilder().run { append("a"); toString() }     // String
```

- **`this` 가림(shadowing)**: 클래스 메서드 안에서 `apply` 를 쓰면 `this` 가 바깥 클래스가 아니라 문맥 객체가 된다. 바깥 클래스와 문맥 객체에 같은 이름의 프로퍼티가 있으면 **문맥 객체 쪽이 이긴다.**

```kotlin
class OrderFactory(private val name: String) {
    fun create(): Order = Order().apply {
        // Order 에 name 프로퍼티가 있다면, 아래 name 은 Order.name 이다
        // OrderFactory.name 을 의도했다면 this@OrderFactory.name 이 필요
        memo = "created by $name"
    }
}
```

### 3.5 `also` — 부수 효과 끼워 넣기

#### 무엇인가

`it` 으로 받고 **객체 자신**을 반환한다. 공식 문서: 객체의 프로퍼티·함수보다 **객체에 대한 참조 자체가 필요한 동작**, 또는 **바깥 스코프의 `this` 를 가리고 싶지 않을 때** 쓴다. "그리고 또한 다음을 하라" 로 읽힌다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

#### 정석 사용사례

```kotlin
// 로깅·메트릭을 체인 중간에
val saved = orderRepository.save(order)
    .also { log.info("order saved id={}", it.id) }

// 반환 직전 부수 효과
fun nextId(): Long = idGenerator.next().also { metrics.increment("id.issued") }

// 체인 중간의 디버깅
numbers
    .also { println("before sort: $it") }
    .sorted()
```

#### 함정

- **`also` 안에서 객체를 변경하지 마라.** `also` 는 "곁가지 부수 효과" 를 암시하므로, 그 안에서 상태를 바꾸면 리뷰어가 놓친다. 상태 변경은 `apply` 나 명시적 문장으로.
- `also` 는 `this` 를 가리지 않는다는 점이 장점이다. 클래스 메서드 안에서 바깥 `this` 를 계속 써야 하면 `apply` 대신 `also` 가 낫다.

### 3.6 `takeIf` / `takeUnless`

스코프 함수는 아니지만 짝으로 쓰인다. `takeIf` 는 조건을 만족하면 객체를, 아니면 null 을 반환한다 — "단일 객체에 대한 filter". `takeUnless` 는 반대다. 람다 안에서 객체는 `it` 이다 ([Scope functions — takeIf and takeUnless](https://kotlinlang.org/docs/scope-functions.html)).

```kotlin
val evenOrNull = number.takeIf { it % 2 == 0 }

val port = System.getenv("PORT")?.toIntOrNull()?.takeIf { it in 1..65535 } ?: 8080

fun displaySubstringPosition(input: String, sub: String) {
    input.indexOf(sub).takeIf { it >= 0 }?.let {
        println("The substring $sub is found in $input.")
        println("Its start position is $it.")
    }
}
```

**함정**: `takeIf` 뒤에는 거의 항상 `?.` 가 필요하다. 반환 타입이 `T?` 이기 때문이다. `takeIf { ... }.let { }` 처럼 `?.` 를 빠뜨리면 `it` 이 nullable 인 채로 블록이 실행된다.

---

## 4. 의도별 선택 가이드

공식 문서의 "의도에 따른 선택" 목록 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)) 에 실무 예를 붙인다.

| 의도 | 함수 | 실무 예 |
|---|---|---|
| non-null 객체에 람다 실행 | `let` | `email?.let { mailer.send(it) }` |
| 식을 지역 변수로 도입 | `let` | `parse(x).let { r -> if (r.ok) r.value else 0 }` |
| 객체 설정 | `apply` | `HikariDataSource().apply { ... }` |
| 객체 설정 + 결과 계산 | `run` | `client.run { timeout = 3; get(url) }` |
| 식이 필요한 곳에서 문장 실행 | 비확장 `run` | `?: run { log(); return }` |
| 부수 효과 추가 | `also` | `.also { log.info(...) }` |
| 객체에 대한 호출 묶기 | `with` | `with(sb) { append(); append() }` |

공식 문서는 사용사례가 겹치므로 **프로젝트·팀의 컨벤션에 따라 선택**할 수 있다고 덧붙인다. 즉 이 표는 정답표가 아니라 *기본값*이다.

---

## 5. 남용 패턴 카탈로그

공식 문서는 분명히 경고한다: 스코프 함수는 코드를 간결하게 만들 수 있지만 **남용하면 읽기 어렵고 오류를 유발한다.** 또한 **스코프 함수를 중첩하지 말고, 체인으로 이을 때는 주의하라.** 현재 문맥 객체와 `this`/`it` 의 값이 헷갈리기 쉽기 때문이다 ([Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

아래는 실무 코드 리뷰에서 반복해서 만나는 형태다.

### 5.1 안티패턴 1: 이유 없는 스코프 함수

```kotlin
// Bad
user.let { userRepository.save(it) }
order.run { validate() }

// Good
userRepository.save(user)
order.validate()
```

null 처리도, 스코프 제한도, 체인도 아니면 스코프 함수는 **간접 단계 하나를 더할 뿐**이다.

### 5.2 안티패턴 2: 중첩

```kotlin
// Bad — it 이 무엇인지, this 가 무엇인지 추적 불가
order?.let {
    it.customer?.let {
        it.address?.apply {
            notify(it, this)       // 컴파일 에러거나, 의도와 다른 객체
        }
    }
}

// Good — 엘비스 가드 + 지역 val
val customer = order?.customer ?: return
val address = customer.address ?: return
notify(customer, address)
```

중첩이 두 단계를 넘으면 **가드 절로 펴는 것**이 거의 항상 낫다. 어쩔 수 없이 중첩하면 모든 람다 파라미터에 이름을 준다.

### 5.3 안티패턴 3: `?.let { } ?: run { }` 을 if-else 로

```kotlin
// Bad
cache[key]?.let { render(it) } ?: run { loadAndRender(key) }
```

`render(it)` 이 **null 을 반환할 수 있으면** 캐시 적중인데도 `loadAndRender` 가 실행된다. 엘비스는 왼쪽 *식 전체*의 결과가 null 인지를 보기 때문이다.

```kotlin
// Good
val cached = cache[key]
if (cached != null) render(cached) else loadAndRender(key)
```

if-else 의도에는 if-else 를 쓴다. 스마트 캐스트 덕분에 `cached` 는 블록 안에서 non-null 이다([K2 3절](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/)).

### 5.4 안티패턴 4: 긴 체인 속 문맥 전환

```kotlin
// Bad — 각 단계가 무엇을 반환하는지 머릿속으로 추적해야 한다
val result = request
    .also { validate(it) }
    .let { toCommand(it) }
    .apply { requestedAt = now() }
    .run { service.handle(this) }
    .also { audit(it) }
    .let { toResponse(it) }
```

```kotlin
// Good — 이름 있는 중간 값
validate(request)
val command = toCommand(request).apply { requestedAt = now() }
val outcome = service.handle(command)
audit(outcome)
return toResponse(outcome)
```

중간 값에 이름을 주는 것은 **문서화**다. 디버거 브레이크포인트를 걸 자리도 생긴다.

### 5.5 안티패턴 5: `apply` 안의 비즈니스 로직

```kotlin
// Bad — "설정" 처럼 보이지만 실제로는 도메인 규칙과 I/O
val order = Order(id).apply {
    status = if (paymentClient.isPaid(id)) PAID else PENDING   // 외부 호출
    if (status == PAID) inventory.reserve(items)                // 부수 효과
}
```

`apply` 는 독자에게 "속성 대입" 을 약속한다. 외부 호출·분기·부수 효과가 들어가면 그 약속이 깨진다. 이런 로직은 도메인 메서드나 서비스 메서드로 옮긴다.

### 5.6 안티패턴 6: JPA 엔티티에 `apply` 로 setter 남발

```kotlin
// Bad — 엔티티의 불변식을 우회
member.apply {
    grade = Grade.VIP
    point = 0
    updatedAt = now()
}
```

엔티티가 `var` 프로퍼티를 열어 두고 바깥에서 `apply` 로 바꾸게 하면, 엔티티가 스스로 지켜야 할 규칙("VIP 승급 시 포인트 초기화")이 호출부로 흩어진다. 상태 변경은 `member.promoteToVip(now)` 같은 **의도가 드러나는 메서드**로 만들고, 프로퍼티는 `private set` 으로 닫는다. 엔티티 설계는 [K9](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) 에서 다룬다.

### 5.7 안티패턴 7: `takeIf` 로 복잡한 조건

```kotlin
// Bad
val target = user.takeIf { it.active && !it.locked && it.plan != Plan.FREE && it.region in allowed }

// Good — 조건에 이름을 준다
fun User.isEligibleForPromotion() = active && !locked && plan != Plan.FREE && region in allowed
val target = user.takeIf { it.isEligibleForPromotion() }
```

---

## 6. 스프링 코드에서 자주 쓰는 정석 패턴

```kotlin
@RestController
class OrderController(private val orderService: OrderService) {

    @GetMapping("/orders/{id}")
    fun get(@PathVariable id: Long): ResponseEntity<OrderResponse> =
        orderService.find(id)
            ?.let { ResponseEntity.ok(it.toResponse()) }      // let: 있으면 변환
            ?: ResponseEntity.notFound().build()

    @PostMapping("/orders")
    fun create(@RequestBody req: CreateOrderRequest): ResponseEntity<OrderResponse> {
        val created = orderService.create(req.toCommand())
            .also { log.info("order created id={}", it.id) }   // also: 로깅
        return ResponseEntity
            .created(URI.create("/orders/${created.id}"))
            .body(created.toResponse())
    }

    companion object {
        private val log = LoggerFactory.getLogger(OrderController::class.java)
    }
}

@Configuration
class HttpClientConfig {
    @Bean
    fun restTemplate(): RestTemplate =
        RestTemplate().apply {                                  // apply: 설정
            interceptors.add(LoggingInterceptor())
        }
}
```

`?.let { ... } ?: ...` 가 첫 번째 메서드에서는 안전하다. `ResponseEntity.ok(...)` 는 null 을 반환하지 않으므로 5.3절의 함정이 생기지 않는다. **오른쪽 분기로 새는지 여부는 왼쪽 람다의 반환 타입이 non-null 인지로 판단**하면 된다.

---

## 7. 팀 컨벤션 예시

공식 문서가 "팀 컨벤션에 따라 선택하라" 고 하므로, 컨벤션을 명시해 두는 것이 리뷰 비용을 줄인다. 아래는 이 글의 근거를 바탕으로 한 예시다.

1. `let` 은 **`?.let` 과 체인 끝 변환**에만 쓴다. non-null 수신 객체에 `let` 을 쓰지 않는다.
2. `apply` 는 **속성 대입만** 있는 객체 설정에 쓴다. 외부 호출·분기를 넣지 않는다.
3. `also` 는 **로깅·메트릭·검증 같은 부수 효과**에만 쓴다. 객체 상태를 바꾸지 않는다.
4. `run`/`with` 는 **같은 객체 멤버를 3회 이상 연달아** 쓸 때만 쓴다.
5. **중첩 금지.** 두 단계가 필요하면 가드 절과 지역 `val` 로 편다.
6. 체인 안의 스코프 함수는 **두 개까지.** 넘으면 중간 값에 이름을 준다.
7. if-else 의도에는 `?.let {} ?: run {}` 이 아니라 `if` 를 쓴다.
8. 람다 파라미터가 다른 람다 안에 있으면 `it` 대신 **이름**을 준다.

---

## 8. 정리

| 함수 | 한 줄 요약 | 대표 함정 |
|---|---|---|
| `let` | `?.let` 과 결과 변환 | non-null 에 쓰는 소음, 중첩 `it` |
| `with` | 반환값 없는 그룹 호출 | nullable 에 못 씀 → `?.run` |
| `run` | 설정 + 결과 / 식 자리의 블록 | 확장·비확장 혼동 |
| `apply` | 객체 설정, 자신 반환 | 마지막 식 버려짐, `this` 가림 |
| `also` | 부수 효과, 자신 반환 | 안에서 상태 변경 |
| `takeIf` | 단일 객체 필터 | 뒤에 `?.` 누락 |

스코프 함수는 "새 능력" 이 아니라 "표현 수단" 이다. 그래서 판단 기준도 단 하나, **읽는 사람이 더 빨리 이해하는가** 다.

다음 글 [K6 컬렉션과 시퀀스](https://myoungsoo7.github.io/2026/10/12/kotlin-collections-and-sequences/) 에서는 읽기 전용/가변 컬렉션과 `Sequence` 지연 평가를 자바 Stream 과 비교한다.

---

## References

- Scope functions — https://kotlinlang.org/docs/scope-functions.html
- Kotlin stdlib source, Standard.kt (let/run/with/apply/also/takeIf 선언과 contract) — https://github.com/JetBrains/kotlin/blob/master/libraries/stdlib/src/kotlin/util/Standard.kt
- Inline functions — https://kotlinlang.org/docs/inline-functions.html
- Higher-order functions and lambdas (function types with receiver) — https://kotlinlang.org/docs/lambdas.html
- Null safety — https://kotlinlang.org/docs/null-safety.html
- Spring Data Commons, CrudRepositoryExtensions.kt (findByIdOrNull) — https://github.com/spring-projects/spring-data-commons/blob/main/src/main/kotlin/org/springframework/data/repository/CrudRepositoryExtensions.kt

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
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/) ← 지금 글
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
