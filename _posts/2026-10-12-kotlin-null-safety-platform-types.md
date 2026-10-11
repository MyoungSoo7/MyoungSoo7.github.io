---
layout: post
title: "코틀린 널 안전 — ?, ?., ?:, !!, 스마트 캐스트, 그리고 자바 경계의 플랫폼 타입"
date: 2026-10-12 00:22:42 +0900
categories: [kotlin]
tags: [kotlin, null-safety, smart-cast, platform-types, jspecify, jsr-305, java-interop, spring]
---

자바·코틀린 20편 시리즈의 **코틀린 2편(K2)** 이다. [K1](https://myoungsoo7.github.io/2026/10/12/kotlin-essence-pragmatism-java-interop/) 에서 본 코틀린의 세 축 가운데 **안전성**의 중심, 널 안전을 다룬다. 연산자 문법보다 더 중요한 것은 두 가지다. (1) 스마트 캐스트가 *언제* 동작하고 언제 안 하는지, (2) 자바 코드가 넘겨주는 **플랫폼 타입**이 널 안전에 어떤 구멍을 내고, 그 구멍을 nullability 애노테이션으로 어떻게 메우는지.

자바 쪽 짝 글은 [J5 null 과 예외: Optional 의 올바른 용도](https://myoungsoo7.github.io/2026/10/12/java-null-optional-exceptions/) 다. 자바가 `Optional` 이라는 *라이브러리 타입*으로 푸는 문제를 코틀린은 *타입 시스템*으로 푼다.

---

## 1. 출발점: nullable 타입과 non-null 타입

### 1.1 무엇인가

코틀린의 모든 타입은 null 을 허용하는 쌍둥이를 가진다. `String` 에는 null 을 넣을 수 없고, `String?` 에는 넣을 수 있다. 공식 비교 문서가 "Java 에서 고친 것" 의 첫 항목으로 꼽는 것이 바로 "null 참조가 타입 시스템으로 통제된다" 이다 ([Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html)).

```kotlin
var a: String = "abc"
// a = null                 // 컴파일 에러

var b: String? = "abc"
b = null                    // OK

val l1 = a.length           // OK — a 는 절대 null 이 아니다
// val l2 = b.length        // 컴파일 에러 — b 는 null 일 수 있다
```

### 1.2 타입 계층으로 보면

| 타입 | 담을 수 있는 값 |
|---|---|
| `Any` | null 이 아닌 모든 객체 |
| `Any?` | 모든 값 + null |
| `String` | null 이 아닌 문자열 |
| `String?` | 문자열 또는 null |
| `Nothing?` | null 하나뿐 |

`String` 은 `String?` 의 하위 타입이다. 그래서 non-null 값을 nullable 변수에 넣는 건 언제나 되고, 반대는 검사(또는 단언)를 거쳐야 한다.

### 1.3 Optional 과 무엇이 다른가

| 관점 | 자바 `Optional<T>` | 코틀린 `T?` |
|---|---|---|
| 정체 | 래퍼 객체 | 타입 표기 (런타임 래퍼 없음) |
| 강제 수준 | 관례 (반환 타입에 쓰자는 권고) | 컴파일러가 모든 역참조를 검사 |
| 필드·파라미터 | 권장하지 않음 | 어디서나 사용 |
| 컬렉션 원소 | `List<Optional<T>>` 는 어색 | `List<T?>` 자연스러움 |

코틀린 코드에서 `Optional` 을 쓸 이유는 거의 없다. 자바 API 가 `Optional` 을 반환할 때만 경계에서 `.orElse(null)` 로 풀어 `T?` 로 바꾸면 된다.

```kotlin
// Spring Data 의 Optional 반환을 코틀린 nullable 로 변환
fun findUser(id: Long): User? = userRepository.findById(id).orElse(null)
```

---

## 2. 널 처리 연산자 다섯 개

### 2.1 안전 호출 `?.`

#### 무엇인가

수신 객체가 null 이면 호출을 건너뛰고 null 을 반환한다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)).

#### 코드 예제

```kotlin
val a: String? = "Kotlin"
val b: String? = null
println(a?.length)   // 6
println(b?.length)   // null

// 체인: 중간 하나라도 null 이면 전체가 null
val headName: String? = bob?.department?.head?.name

// 할당 왼쪽에도 쓸 수 있다: 수신 객체 중 하나라도 null 이면 대입 자체를 건너뛴다
person?.department?.head = managersPool.getManager()
```

할당 왼쪽에서의 `?.` 동작(수신 객체가 null 이면 대입을 건너뜀)은 공식 문서에 예제로 나온다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)).

#### 실무 사용사례

- 선택적 연관 객체 탐색: `order.coupon?.discountRate`
- 로그·메트릭에서 "있으면 기록" : `span?.setAttribute("userId", id)`

#### 함정

- 체인이 길어지면 **어디서 null 이 됐는지 알 수 없다.** 도메인적으로 "없으면 안 되는" 값이라면 `?.` 로 조용히 흘리지 말고 엘비스 + 예외로 끊어라.
- 할당 왼쪽 `?.` 는 "대입이 안 일어날 수 있음" 을 숨긴다. 리뷰어가 놓치기 쉬우니 중요한 상태 변경에는 쓰지 않는 편이 낫다.

### 2.2 엘비스 `?:`

#### 무엇인가

왼쪽이 null 이면 오른쪽을 쓴다. 오른쪽은 왼쪽이 null 일 때만 평가된다. `throw` 와 `return` 도 식이므로 오른쪽에 올 수 있다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)).

#### 코드 예제

```kotlin
val len: Int = b?.length ?: 0

fun parentName(node: Node): String? {
    val parent = node.getParent() ?: return null
    val name = node.getName() ?: throw IllegalArgumentException("name expected")
    return "${parent.id}/$name"
}
```

#### 실무 사용사례: 가드 절(early return)

```kotlin
@Transactional
fun cancel(orderId: Long, userId: Long) {
    val order = orderRepository.findByIdOrNull(orderId)
        ?: throw OrderNotFoundException(orderId)
    val user = userRepository.findByIdOrNull(userId)
        ?: throw UserNotFoundException(userId)
    order.cancelBy(user)
}
```

`findByIdOrNull` 은 Spring Data Commons 가 코틀린용으로 제공하는 확장 함수로, 구현은 `findById(id).orElse(null)` 한 줄이다 ([CrudRepositoryExtensions.kt](https://github.com/spring-projects/spring-data-commons/blob/main/src/main/kotlin/org/springframework/data/repository/CrudRepositoryExtensions.kt)). 이 패턴 하나로 자바의 `orElseThrow(() -> new ...)` 를 대체한다.

#### 함정

- `a ?: b ?: c ?: d` 처럼 길게 이으면 우선순위 의도가 흐려진다. 3단 이상이면 `when` 으로 풀어 써라.
- 오른쪽에 **부작용 있는 식**을 넣으면 "null 일 때만" 실행된다는 점이 드러나지 않는다. `x ?: saveDefault()` 는 리뷰에서 자주 오해된다.

### 2.3 non-null 단언 `!!`

#### 무엇인가

어떤 값이든 non-null 타입으로 바꾸고, null 이면 NPE 를 던진다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)). Kotlin 1.4.0 부터 `!!` 를 포함한 런타임 null 체크는 모두 `java.lang.NullPointerException` 을 던지도록 통일됐다 ([What's new in 1.4.0](https://kotlinlang.org/docs/whatsnew14.html)).

#### 코드 예제

```kotlin
val c: String? = null
val l = c!!.length   // NullPointerException
```

#### 실무 사용사례 (드물다)

- 테스트 코드에서 "여기서 null 이면 테스트 실패가 맞다" 를 표현할 때
- 프레임워크가 초기화를 보장하지만 컴파일러가 모르는 아주 좁은 경우 — 다만 이마저도 `lateinit` 이나 `requireNotNull` 이 더 낫다

#### 함정과 대안

`!!` 는 실패 메시지가 없다. 같은 의도를 더 잘 표현하는 표준 라이브러리 함수가 있다.

```kotlin
// 인자 검증 — IllegalArgumentException
val id = requireNotNull(request.id) { "id 는 필수입니다" }

// 상태 검증 — IllegalStateException
val token = checkNotNull(session.token) { "세션 토큰이 없습니다: ${session.id}" }

// 도달하면 안 되는 분기
val v = map[key] ?: error("설정 누락: $key")
```

1.4.0 의 예외 통일은 `requireNotNull`/`checkNotNull` 같은 **명시적 라이브러리 함수 호출에는 적용되지 않는다** ([What's new in 1.4.0](https://kotlinlang.org/docs/whatsnew14.html)). 즉 이 함수들은 여전히 각각 `IllegalArgumentException`/`IllegalStateException` 을 던진다. 웹 계층에서 이 둘을 400/500 으로 다르게 매핑하면 의도가 응답 코드까지 전달된다.

### 2.4 안전한 캐스트 `as?`

#### 무엇인가

캐스트가 실패하면 `ClassCastException` 대신 null 을 반환한다 ([Type checks and casts](https://kotlinlang.org/docs/typecasts.html)).

```kotlin
val raw: Any = "user-1234"
val s: String? = raw as? String   // "user-1234"
val n: Int? = raw as? Int         // null — 예외 없음
```

#### 실무 사용사례

```kotlin
// 이벤트 핸들러에서 관심 있는 타입만 처리
fun onEvent(event: Any) {
    val paid = event as? PaymentCompleted ?: return
    settle(paid.orderId, paid.amount)
}
```

#### 함정

- `as?` + `?: return` 은 "다른 타입이 들어오면 조용히 무시" 다. 그게 의도가 아니면 sealed 계층 + `when` 으로 바꿔 컴파일러가 누락을 잡게 하라(K3).

### 2.5 `?.let { }`

#### 무엇인가

null 이 아닐 때만 블록을 실행한다. 블록 안의 `it` 은 non-null 타입이다 ([Null safety](https://kotlinlang.org/docs/null-safety.html), [Scope functions](https://kotlinlang.org/docs/scope-functions.html)).

```kotlin
email?.let { sendWelcomeMail(it) }

val listWithNulls: List<String?> = listOf("Kotlin", null)
for (item in listWithNulls) {
    item?.let { println(it) }   // "Kotlin" 만 출력
}
```

#### 함정

`?.let { } ?: run { }` 으로 if-else 를 흉내내는 코드는 **블록이 null 을 반환하면 else 쪽도 실행된다.**

```kotlin
// 의도: user 가 있으면 A, 없으면 B
user?.let { updateCache(it) } ?: run { log.warn("no user") }
// updateCache 가 null 을 반환하는 함수라면 user 가 있어도 warn 이 찍힌다
```

if-else 의도라면 그냥 `if (user != null) ... else ...` 를 쓴다. 스코프 함수 선택 기준은 [K5](https://myoungsoo7.github.io/2026/10/12/kotlin-scope-functions-use-cases/) 에서 정리한다.

---

## 3. 스마트 캐스트 — 언제 되고 언제 안 되나

### 3.1 무엇인가

`is` 검사나 null 검사 뒤에는 컴파일러가 변수를 자동으로 좁힌 타입으로 취급한다.

```kotlin
fun describe(x: Any) {
    if (x is String) {
        println(x.length)          // x 는 String 으로 스마트 캐스트
    }
}

val b: String? = "Kotlin"
if (b != null && b.length > 0) {   // && 오른쪽에서 이미 String
    println("length ${b.length}")
}
```

### 3.2 규칙 — "검사와 사용 사이에 값이 바뀔 수 없음을 컴파일러가 증명할 수 있을 때만"

공식 문서의 규칙을 표로 옮긴다 ([Type checks and casts](https://kotlinlang.org/docs/typecasts.html)).

| 대상 | 스마트 캐스트 |
|---|---|
| `val` 지역 변수 | 항상 (지역 위임 프로퍼티 제외) |
| `val` 프로퍼티 | `private`/`internal` 이거나 같은 모듈에서 검사할 때. **`open` 프로퍼티나 커스텀 getter 가 있으면 불가** |
| `var` 지역 변수 | 검사와 사용 사이에 수정되지 않고, 수정하는 람다에 캡처되지 않고, 지역 위임 프로퍼티가 아닐 때 |
| `var` 프로퍼티 | **절대 불가** — 다른 코드가 언제든 바꿀 수 있으므로 |

### 3.3 실무에서 가장 자주 만나는 에러: `var` 프로퍼티

```kotlin
class OrderView {
    var coupon: Coupon? = null

    fun discount(): Int {
        if (coupon != null) {
            // return coupon.rate   // 컴파일 에러: Smart cast to 'Coupon' is impossible,
            //                      // because 'coupon' is a mutable property
        }
        // 해결 1: 지역 val 로 복사
        val c = coupon ?: return 0
        return c.rate
    }

    // 해결 2: ?.let
    fun discount2(): Int = coupon?.let { it.rate } ?: 0
}
```

**왜 이것이 옳은가**: `var` 프로퍼티는 다른 스레드나 호출된 메서드가 검사 직후 null 로 바꿀 수 있다. 컴파일러의 거부는 실제 경쟁 조건을 막는 것이다. 지역 `val` 로 복사하는 것은 "이 시점의 스냅샷으로 작업한다" 는 명시적 선언이다.

### 3.4 다른 모듈의 `val` 프로퍼티

```kotlin
// 모듈 A
class Config(val endpoint: String?)

// 모듈 B
fun call(config: Config) {
    if (config.endpoint != null) {
        // config.endpoint.length  // 다른 모듈의 public val 은 스마트 캐스트 불가
    }
    val ep = config.endpoint ?: return
    println(ep.length)
}
```

위 표의 "같은 모듈" 조건이 이것이다. 공식 문서가 이유를 따로 적지는 않지만, 다른 모듈의 public 프로퍼티는 그 모듈이 나중에 커스텀 getter 로 구현을 바꿔 재배포할 수 있으므로 호출하는 쪽 컴파일러가 "두 번 읽어도 같은 값" 을 보장할 수 없다고 이해하면 된다.

### 3.5 Kotlin 2.0(K2) 에서 늘어난 스마트 캐스트

Kotlin 2.0.0 의 K2 컴파일러는 스마트 캐스트 범위를 여섯 영역에서 넓혔다: 지역 변수와 그 이후 스코프, `||` 로 묶은 타입 검사, 인라인 함수, 함수 타입 프로퍼티, 예외 처리, 증감 연산자 ([What's new in Kotlin 2.0.0](https://kotlinlang.org/docs/whatsnew20.html)). 실무에서 체감이 큰 두 가지만 본다.

```kotlin
// (1) 조건을 변수로 뽑아도 스마트 캐스트 유지 (1.9.20 에선 에러)
fun petAnimal(animal: Any) {
    val isCat = animal is Cat
    if (isCat) {
        animal.purr()
    }
}

// (2) || 로 묶으면 가장 가까운 공통 상위 타입으로 캐스트 (이전엔 Any)
interface Status { fun signal() {} }
interface Postponed : Status
interface Declined : Status

fun signalCheck(s: Any) {
    if (s is Postponed || s is Declined) {
        s.signal()   // Status 로 스마트 캐스트
    }
}
```

인라인 함수에 대해서는, K2 가 인라인 함수에 전달된 람다를 암묵적 `callsInPlace` 계약을 가진 것으로 취급해 캡처된 지역 `var` 도 안전하면 스마트 캐스트한다 ([What's new in Kotlin 2.0.0](https://kotlinlang.org/docs/whatsnew20.html)). `?.let { }` 이나 `apply { }` 같은 스코프 함수 안에서 지역 변수를 다룰 때 `?.` 가 줄어드는 이유다.

### 3.6 함정: 예외 블록에서의 스마트 캐스트

2.0.0 에서 `catch`/`finally` 블록으로 스마트 캐스트 정보가 *올바르게* 전달되도록 고쳐졌다. 1.9.20 에서는 `try` 안에서 null 로 바꾼 변수를 `catch` 에서 non-null 로 잘못 취급하는 경우가 있었다 ([What's new in Kotlin 2.0.0](https://kotlinlang.org/docs/whatsnew20.html)). 컴파일러 업그레이드 후 "safe call 이 불필요하다" 경고가 사라지거나 생기는 위치가 바뀔 수 있으니, 경고 diff 를 확인하라.

---

## 4. nullable 과 컬렉션

### 4.1 `List<String?>` 와 `List<String>?` 는 다르다

| 타입 | 의미 |
|---|---|
| `List<String>` | 리스트도 원소도 null 아님 |
| `List<String?>` | 리스트는 있음, 원소가 null 일 수 있음 |
| `List<String>?` | 리스트 자체가 없을 수 있음, 있으면 원소는 non-null |
| `List<String?>?` | 둘 다 null 가능 |

### 4.2 `filterNotNull`, `mapNotNull`

```kotlin
val nullable: List<Int?> = listOf(1, 2, null, 4)
val ints: List<Int> = nullable.filterNotNull()     // [1, 2, 4]

val ids: List<Long> = rawIds.mapNotNull { it.toLongOrNull() }
```

`filterNotNull()` 은 공식 문서의 예제다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)). 타입까지 `List<Int>` 로 좁혀진다는 점이 `filter { it != null }` 과 다르다.

### 4.3 함정: "빈 리스트" 와 "null 리스트" 를 둘 다 허용하지 마라

API 응답 DTO 에 `val tags: List<String>?` 를 두면 호출자는 `null` 과 `emptyList()` 를 모두 처리해야 한다. 의미 차이가 없다면 `val tags: List<String> = emptyList()` 로 기본값을 주는 편이 단순하다.

---

## 5. 초기화를 미루는 non-null: `lateinit` 과 `lazy`

### 5.1 `lateinit`

#### 무엇인가

생성자에서 초기화할 수 없지만 *사용 전에는 반드시 초기화되는* non-null `var` 에 쓴다 ([Properties](https://kotlinlang.org/docs/properties.html)).

제약:
- `var` 에만, non-null 이어야 하고 **원시 타입(Int 등) 불가**
- 클래스 프로퍼티라면 주 생성자에 선언 불가, 커스텀 getter/setter 불가
- 초기화 전 접근하면 `UninitializedPropertyAccessException`
- `::prop.isInitialized` 로 초기화 여부 확인 가능

#### 코드 예제와 사용사례: 테스트 픽스처

```kotlin
class OrderServiceTest {
    private lateinit var service: OrderService

    @BeforeEach
    fun setUp() {
        service = OrderService(FakeOrderRepository())
    }

    @Test
    fun `주문 취소`() {
        service.cancel(1L)
    }
}
```

#### 함정

- 프로덕션 스프링 빈에서 `@Autowired lateinit var` 필드 주입은 동작하지만, **생성자 주입이 정답**이다. `lateinit` 은 "초기화를 컴파일러가 아닌 사람이 보장" 한다는 뜻이라 널 안전을 반쯤 포기하는 것이다(K9).
- `isInitialized` 로 분기하는 코드가 늘어난다면 그건 사실 nullable 이다. `T?` 로 바꿔라.

### 5.2 `by lazy`

```kotlin
class ReportService(private val repo: ReportRepository) {
    private val template: String by lazy { loadTemplate("report.html") }
}
```

`lazy` 의 기본 동작은 **동기화**되어 한 스레드에서만 계산되고 모든 스레드가 같은 값을 본다. 동기화가 필요 없으면 `LazyThreadSafetyMode.PUBLICATION` 이나 `NONE` 을 줄 수 있다 ([Delegated properties](https://kotlinlang.org/docs/delegated-properties.html)).

---

## 6. 코틀린에서 NPE 가 나는 경우 — 공식 목록

공식 문서는 코틀린에서 NPE 가 날 수 있는 원인을 다음으로 한정한다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)).

1. 명시적 `throw NullPointerException()`
2. `!!` 연산자
3. 초기화 중 데이터 불일치
   - 생성자에서 초기화되지 않은 `this` 가 밖으로 새는 경우("leaking this")
   - 상위 클래스 생성자가 open 멤버를 호출하고, 하위 클래스 구현이 아직 초기화되지 않은 상태를 쓰는 경우
4. 자바 상호운용
   - 플랫폼 타입의 null 참조 멤버 접근
   - 제네릭 타입의 nullability 문제
   - 외부 자바 코드가 일으키는 기타 문제

### 6.1 3번의 실제 모습: 상위 생성자의 open 멤버 호출

```kotlin
open class Base {
    init {
        println(describe().length)   // 하위 클래스의 describe() 가 호출된다
    }
    open fun describe(): String = "base"
}

class Derived(private val name: String) : Base() {
    // Base 의 init 이 실행되는 시점에 name 은 아직 할당 전 (null)
    override fun describe(): String = name
}

fun main() {
    Derived("x")   // NullPointerException — 타입은 non-null String 인데도
}
```

`name` 은 `String` 이지만, `Base` 생성자가 먼저 실행되는 시점엔 필드가 아직 기본값(null) 이다. 그래서 **생성자/`init` 에서 open 멤버를 호출하지 말 것** 이 코틀린에서도 유효한 규칙이다. 타입 시스템은 "초기화 순서" 까지는 추적하지 않는다.

---

## 7. 자바 경계: 플랫폼 타입

### 7.1 무엇인가

자바 코드에서 온 값은 nullability 정보가 없다. 코틀린은 이를 **플랫폼 타입**으로 취급하고, null 검사를 *완화*한다. 코드에 직접 쓸 수는 없지만 에러 메시지와 IDE 툴팁에 다음 표기로 나온다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

| 표기 | 의미 |
|---|---|
| `T!` | `T` 또는 `T?` |
| `(Mutable)Collection<T>!` | 가변일 수도 아닐 수도, null 일 수도 아닐 수도 있는 자바 컬렉션 |
| `Array<(out) T>!` | `T`(또는 하위 타입)의 자바 배열, null 가능 여부 모름 |

### 7.2 코드 예제

```java
// Java
public class LegacyUserDao {
    public String findNickname(long id) { /* 없으면 null 반환 */ }
}
```

```kotlin
val dao = LegacyUserDao()

val n1 = dao.findNickname(1L)          // 타입: String! — 컴파일러는 아무것도 강제하지 않음
println(n1.length)                     // 컴파일 OK, null 이면 런타임 NPE

val n2: String? = dao.findNickname(1L) // 안전: nullable 로 받기
println(n2?.length ?: 0)

val n3: String = dao.findNickname(1L)  // non-null 로 받으면 할당 시점에 단언 삽입
                                       // null 이면 바로 여기서 예외
```

공식 문서에 따르면 non-null 타입으로 받으면 컴파일러가 **할당 시점에 단언을 넣고**, 플랫폼 값을 non-null 을 기대하는 코틀린 함수에 넘길 때도 단언이 들어간다. 다만 제네릭 때문에 완전히 막을 수는 없다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

### 7.3 실무 규칙: 경계에서 즉시 타입을 확정하라

```kotlin
// 자바 DAO 를 감싸는 어댑터 — 플랫폼 타입이 도메인 안으로 새지 않게 한다
class UserNicknameAdapter(private val dao: LegacyUserDao) {
    fun nickname(id: Long): String? = dao.findNickname(id)   // 반환 타입을 명시
}
```

**왜**: `val x = javaCall()` 처럼 타입을 추론에 맡기면 `T!` 가 지역 변수, 반환값, 다른 함수로 *전파*된다. NPE 가 나는 위치가 자바 호출 지점에서 멀어질수록 디버깅이 어렵다. 공식 문서도 이 표기를 보면 명시적 타입을 붙여 null 검사를 복원하라고 안내한다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

### 7.4 함정: 자바 컬렉션의 원소

```kotlin
val names: List<String> = javaApi.names()   // 리스트 자체는 단언되지만…
names.forEach { println(it.length) }        // 원소 중 null 이 있으면 여기서 NPE
```

리스트 참조에 대한 단언이 *원소* 의 null 까지 검사하지는 않는다. 공식 목록의 "제네릭 타입의 nullability 문제" 가 이것이다. 원소 null 가능성이 있으면 `List<String?>` 로 받고 `filterNotNull()` 로 정리하라.

또한 박싱 타입이 타입 인자로 쓰이면 플랫폼 타입이 된다: `List<java.lang.Integer>` 는 코틀린에서 `List<Int!>` 다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

---

## 8. 플랫폼 타입을 없애는 법: nullability 애노테이션

### 8.1 무엇인가

자바 선언에 nullability 애노테이션이 붙어 있으면, 코틀린은 그 타입을 플랫폼 타입이 아니라 **진짜 nullable/non-null 코틀린 타입**으로 읽는다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

지원하는 애노테이션 계열 (공식 문서 목록):

| 계열 | 패키지 |
|---|---|
| JetBrains | `org.jetbrains.annotations` (`@Nullable`, `@NotNull`) |
| JSpecify | `org.jspecify.annotations` |
| Android | `com.android.annotations`, `android.support.annotations` |
| JSR-305 | `javax.annotation` |
| FindBugs | `edu.umd.cs.findbugs.annotations` |
| Eclipse | `org.eclipse.jdt.annotation` |
| Lombok | `lombok.NonNull` |
| RxJava 3 | `io.reactivex.rxjava3.annotations` |
| Vert.x | `io.vertx.codegen.annotations` |

### 8.2 JSpecify — 현재의 표준 방향

JSpecify 는 자바 nullability 를 위한 통합 애노테이션 세트이고, 코틀린은 다음 네 가지를 지원한다 ([Calling Java from Kotlin — JSpecify support](https://kotlinlang.org/docs/java-interop.html#jspecify-support)).

- `@Nullable` / `@NonNull`
- `@NullMarked` — 클래스·패키지 등 스코프 안의 타입을 기본 non-null 로. 단, 지역 변수와 타입 변수(제네릭)에는 적용되지 않는다
- `@NullUnmarked` — `@NullMarked` 효과를 되돌려 다시 플랫폼 타입으로

```java
// package-info.java
@NullMarked
package com.example.legacy;

import org.jspecify.annotations.NullMarked;
```

```java
// com/example/legacy/UserDao.java
package com.example.legacy;

import org.jspecify.annotations.Nullable;

public class UserDao {
    public String name(long id) { ... }                 // 코틀린에서 String
    public @Nullable String nickname(long id) { ... }   // 코틀린에서 String?
}
```

```kotlin
val dao = UserDao()
val name: String = dao.name(1L)          // OK
// val nick: String = dao.nickname(1L)   // 컴파일 에러 — String? 를 String 에 할당
```

**심각도**: Kotlin 2.1.0 부터 JSpecify nullability 불일치는 **기본적으로 경고가 아니라 에러**다 ([What's new in Kotlin 2.1.0](https://kotlinlang.org/docs/whatsnew21.html)). 현재 문서도 JSpecify 가 기본 `strict` 를 쓰는 유일한 계열이라고 명시한다. 조정이 필요하면 `-Xjspecify-annotations=strict|warn|ignore` 를 쓴다 ([java-interop](https://kotlinlang.org/docs/java-interop.html)).

### 8.3 스프링과의 관계

Spring Framework 7 은 코드베이스에 **JSpecify 애노테이션**을 달아 API 의 nullability 를 선언하고, 기존 `org.springframework.lang` 의 `@Nullable`/`@NonNull`/`@NonNullApi`/`@NonNullFields` 는 **Spring Framework 7 부터 deprecated** 다. 공식 문서는 "코틀린에서 JSpecify 애노테이션은 코틀린의 널 안전으로 자동 번역된다" 고 설명한다 ([Spring Framework: Null-safety](https://docs.spring.io/spring-framework/reference/core/null-safety.html)).

즉 Spring Framework 7 기반 프로젝트에서는 스프링 API 반환값 상당수가 플랫폼 타입이 아니라 정확한 코틀린 타입으로 보인다. 버전별 상세(Boot 4 와의 관계 등)는 [K10](https://myoungsoo7.github.io/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/) 에서 다룬다.

### 8.4 JSR-305 와 `-Xjsr305`

JSR-305 의 `@Nonnull(when = ...)` 과, `@TypeQualifierNickname`/`@TypeQualifierDefault` 로 만든 커스텀 애노테이션도 지원된다. 컴파일러 옵션 ([java-interop — JSR-305 support](https://kotlinlang.org/docs/java-interop.html#jsr-305-support)):

```text
-Xjsr305={strict|warn|ignore}               # @UnderMigration 이 아닌 애노테이션
-Xjsr305=under-migration:{strict|warn|ignore}
-Xjsr305=@<fq.name>:{strict|warn|ignore}     # 특정 애노테이션만
```

- **기본값은 `-Xjsr305=warn`** 과 같다
- `strict` 만이 코틀린에서 보이는 타입 자체에 영향을 준다. 공식 문서는 `strict` 를 아직 실험적이라고 표현한다(검사가 추가될 수 있음)
- 내장 JSR-305 애노테이션 `@Nonnull`, `@Nullable`, `@CheckForNull` 은 플래그와 무관하게 항상 적용된다

```kotlin
// build.gradle.kts
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xjsr305=strict")
    }
}
```

#### 함정

- `warn` (기본) 에서는 JSR-305 *커스텀* 애노테이션 기반 불일치가 경고로만 나오고 타입은 여전히 플랫폼 타입이다. 경고를 무시하는 팀이라면 사실상 보호가 없다.
- `strict` 로 올리면 기존 코드에 컴파일 에러가 대량으로 날 수 있다. 라이브러리별로 `-Xjsr305=@<fq.name>:strict` 로 점진 적용하는 방법이 있다.

---

## 9. 제네릭과 nullability

### 9.1 타입 파라미터의 기본 상한은 `Any?`

타입 파라미터에 상한을 지정하지 않으면 기본 상한은 `Any?` 다 ([Generics](https://kotlinlang.org/docs/generics.html)). 즉 `T` 자체가 nullable 일 수 있다.

```kotlin
fun <T> firstOrDefault(list: List<T>, default: T): T = list.firstOrNull() ?: default
// T = String? 로 호출하면 결과도 String?

fun <T : Any> requireFirst(list: List<T>): T = list.first()
// T 는 non-null 만 허용
```

### 9.2 확정적 non-null 타입 `T & Any`

자바 제네릭 인터페이스를 구현할 때 "이 위치만큼은 non-null" 을 표현하려고 `T & Any` 문법이 있다. **Kotlin 1.7.0 에서 Stable** 이 되었다 ([What's new in 1.7.0](https://kotlinlang.org/docs/whatsnew17.html), [Generics](https://kotlinlang.org/docs/generics.html)).

```java
// Java
import org.jetbrains.annotations.NotNull;

public interface Game<T> {
    T save(T x);
    @NotNull T load(@NotNull T x);
}
```

```kotlin
interface ArcadeGame<T1> : Game<T1> {
    override fun save(x: T1): T1
    // T1 은 nullable 일 수 있지만, load 의 파라미터·반환은 확정적 non-null
    override fun load(x: T1 & Any): T1 & Any
}
```

변성(in/out)과 제네릭 전반은 [K8](https://myoungsoo7.github.io/2026/10/12/kotlin-generics-variance-in-out/) 에서 다룬다.

---

## 10. 자바에서 코틀린을 부를 때의 null

반대 방향도 있다. 코틀린 public 함수는 non-null 파라미터에 **런타임 null 체크**를 생성하므로, 자바가 null 을 넘기면 자바 호출 지점에서 즉시 NPE 가 난다 ([Calling Kotlin from Java](https://kotlinlang.org/docs/java-to-kotlin-interop.html)).

```kotlin
class Greeter {
    fun greet(name: String) = "Hello, $name"
}
```

```java
new Greeter().greet(null);   // NullPointerException — 코틀린 함수 본문에 들어가기 전에
```

**실무 의미**: 코틀린 모듈을 자바 팀에 라이브러리로 제공한다면, 시그니처의 `String` 과 `String?` 이 곧 계약서다. 계약 위반은 컴파일 타임이 아니라 *호출 즉시* 런타임에 드러난다는 점을 자바 쪽 사용자에게 문서로 알려 두는 것이 좋다.

---

## 11. 정리: 널 안전 체크리스트

| 상황 | 권장 |
|---|---|
| 없을 수 있는 값 | `T?` + `?.` / `?:` |
| 없으면 안 되는 값 (인자) | `requireNotNull(x) { "msg" }` |
| 없으면 안 되는 값 (상태) | `checkNotNull(x) { "msg" }` / `?: error("msg")` |
| 조회 후 없으면 예외 | `findByIdOrNull(id) ?: throw NotFound(id)` |
| `var` 프로퍼티 스마트 캐스트 실패 | 지역 `val` 로 복사 |
| 자바 반환값 | 받는 즉시 타입 명시 (`T` 또는 `T?`) |
| 우리 팀 자바 코드 | `@NullMarked` (JSpecify) 로 패키지 단위 non-null 기본값 |
| 나중에 초기화 | 테스트는 `lateinit`, 프로덕션 빈은 생성자 주입 |
| `!!` | 테스트 외에는 쓰지 않는 것을 기본으로 |

다음 글 [K3 클래스](https://myoungsoo7.github.io/2026/10/12/kotlin-classes-data-sealed-object-value/) 에서는 기본 final, data/sealed/enum class, object, value class 를 다룬다.

---

## References

- Null safety — https://kotlinlang.org/docs/null-safety.html
- Type checks and casts — https://kotlinlang.org/docs/typecasts.html
- Calling Java from Kotlin (platform types, nullability annotations, JSpecify, JSR-305) — https://kotlinlang.org/docs/java-interop.html
- Calling Kotlin from Java (runtime null checks) — https://kotlinlang.org/docs/java-to-kotlin-interop.html
- Properties (lateinit) — https://kotlinlang.org/docs/properties.html
- Delegated properties (lazy) — https://kotlinlang.org/docs/delegated-properties.html
- Generics (default upper bound, definitely non-nullable types) — https://kotlinlang.org/docs/generics.html
- Scope functions — https://kotlinlang.org/docs/scope-functions.html
- Comparison to Java — https://kotlinlang.org/docs/comparison-to-java.html
- What's new in Kotlin 1.4.0 (unified NPE for null checks) — https://kotlinlang.org/docs/whatsnew14.html
- What's new in Kotlin 1.7.0 (definitely non-nullable types stable) — https://kotlinlang.org/docs/whatsnew17.html
- What's new in Kotlin 2.0.0 (K2 smart cast improvements) — https://kotlinlang.org/docs/whatsnew20.html
- What's new in Kotlin 2.1.0 (JSpecify strict by default) — https://kotlinlang.org/docs/whatsnew21.html
- Spring Framework Reference, Null-safety — https://docs.spring.io/spring-framework/reference/core/null-safety.html
- Spring Data Commons, CrudRepositoryExtensions.kt — https://github.com/spring-projects/spring-data-commons/blob/main/src/main/kotlin/org/springframework/data/repository/CrudRepositoryExtensions.kt

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
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/) ← 지금 글
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
