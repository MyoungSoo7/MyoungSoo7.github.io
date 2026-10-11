---
layout: post
title: "코틀린 클래스 — 기본 final, data·sealed·enum class, object·companion, value class"
date: 2026-10-12 00:23:42 +0900
categories: [kotlin]
tags: [kotlin, data-class, sealed-class, enum, object, companion-object, value-class, jvm-record, adt]
---

자바·코틀린 20편 시리즈의 **코틀린 3편(K3)** 이다. 코틀린 클래스 모델을 "어떤 문제를 풀려고 이 종류의 클래스가 있는가" 기준으로 분류한다. 일반 클래스의 **기본 final** 에서 시작해, 값을 담는 **data class**, 닫힌 계층을 만드는 **sealed**, 고정된 상수 집합 **enum**, 단 하나의 인스턴스 **object/companion**, 그리고 런타임 비용 없는 래퍼 **value class** 까지 간다.

자바 쪽 짝 글은 두 편이다. [J3 클래스 모델의 진화: default 메서드, record, sealed](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/) 와 [J6 패턴 매칭: switch 식, record 패턴](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/). 이전 글 [sealed 와 record 는 실무에서 무엇이 되는가](https://myoungsoo7.github.io/2026/09/13/java17-sealed-record-real-use-vs-kotlin/) 에서도 자바 17 ADT 를 코틀린과 비교한 적이 있다.

---

## 0. 한눈에 보는 분류

| 종류 | 푸는 문제 | 핵심 성질 | 자바 대응 |
|---|---|---|---|
| `class` | 일반 객체 | **기본 final** | `final class` |
| `open class` / `abstract class` | 상속 허용 | 명시적 opt-in | 기본 `class` / `abstract class` |
| `data class` | 값 운반 (DTO, 이벤트) | `equals`/`hashCode`/`toString`/`copy`/`componentN` 생성 | `record` |
| `sealed class` / `sealed interface` | 닫힌 계층 (ADT) | 직접 하위 타입이 컴파일 타임에 확정 | `sealed` + `permits` |
| `enum class` | 고정 상수 집합 | `entries`, 상수별 본문 | `enum` |
| `object` | 싱글턴 | 첫 접근 시 스레드 안전 초기화 | static holder 패턴 |
| `companion object` | 클래스 수준 멤버 | 실제로는 인스턴스 멤버 | `static` |
| `value class` | 타입 안전 래퍼 | 런타임엔 내부 값으로 표현 | (없음) |

---

## 1. 기본 final 과 `open`

### 1.1 무엇인가

코틀린 클래스와 그 멤버는 **기본적으로 final** 이다. 상속하려면 클래스에, 오버라이드하려면 멤버에 각각 `open` 을 붙여야 한다 ([Inheritance](https://kotlinlang.org/docs/inheritance.html)).

```kotlin
open class Shape {
    open fun draw() { /* ... */ }
    fun fill() { /* ... */ }          // final
}

class Circle : Shape() {
    override fun draw() { /* ... */ } // override 필수
    // fun fill() {}                  // 컴파일 에러: final 멤버와 같은 시그니처
}
```

규칙 정리 (공식 문서):
- `override` 수식어는 필수. 빠지면 컴파일 에러
- `open` 이 없는 함수와 같은 시그니처를 하위 클래스에 선언하는 것은 `override` 유무와 관계없이 금지
- final 클래스의 멤버에 `open` 을 붙여도 효과가 없다
- `abstract` 클래스와 멤버는 `open` 없이도 상속 가능하다 ([Classes](https://kotlinlang.org/docs/classes.html))

`override` 된 멤버는 그 자체로 open 이다. 더 이상 오버라이드를 막으려면 `final override` 를 쓴다.

```kotlin
open class Rectangle : Shape() {
    final override fun draw() { /* 하위 클래스에서 더 못 바꿈 */ }
}
```

### 1.2 왜 기본 final 인가

"상속을 위해 설계하고 문서화하라, 아니면 금지하라" 는 원칙을 언어 기본값으로 만든 것이다. 상위 클래스의 내부 구현 변경이 하위 클래스를 깨뜨리는 취약한 기반 클래스 문제를, 애초에 상속을 opt-in 으로 만들어 줄인다.

### 1.3 함정: 프록시 기반 프레임워크

스프링 AOP(CGLIB), JPA 지연 로딩 프록시, Mockito(인라인 모드가 아닌 경우)는 **하위 클래스를 만들어** 동작한다. 코틀린의 기본 final 은 이와 정면으로 충돌한다.

```kotlin
@Service
class OrderService {                 // final — CGLIB 가 하위 클래스를 못 만든다
    @Transactional
    fun place() { /* ... */ }        // final — 오버라이드 불가
}
```

해결책은 클래스마다 `open` 을 붙이는 게 아니라 `kotlin-spring`(all-open) 컴파일러 플러그인이다. 상세는 [K9 코틀린 × 스프링](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) 에서 다룬다.

---

## 2. 주 생성자, 프로퍼티, init 블록 — 짧게

### 2.1 무엇인가

```kotlin
class User(
    val id: Long,                 // 읽기 전용 프로퍼티
    var nickname: String,         // 가변 프로퍼티
    email: String,                // 프로퍼티 아님 — 생성자 파라미터일 뿐
) {
    val emailDomain: String = email.substringAfter('@')

    init {
        require(nickname.isNotBlank()) { "nickname 은 비어 있을 수 없습니다" }
    }
}
```

주 생성자는 클래스 헤더에, 보조 생성자는 본문에 선언한다. init 블록은 주 생성자가 실행될 때 함께 실행된다 ([Classes](https://kotlinlang.org/docs/classes.html)).

### 2.2 실무 사용사례: 불변식은 init 에서

도메인 객체의 불변식(invariant)을 `init` + `require` 로 두면, 어떤 경로로 생성되든 검사가 빠지지 않는다.

### 2.3 함정

- `val`/`var` 를 빼먹으면 생성자 파라미터가 **프로퍼티가 되지 않는다.** 위의 `email` 은 `user.email` 로 접근할 수 없다.
- `init` 에서 `open` 멤버를 호출하지 말 것. 하위 클래스 필드가 초기화되기 전에 호출된다([K2 6.1절](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/) 의 NPE 사례).

---

## 3. data class — 값을 담는 클래스

### 3.1 무엇인가

`data` 를 붙이면 컴파일러가 **주 생성자에 선언된 프로퍼티**를 기준으로 다음을 생성한다 ([Data classes](https://kotlinlang.org/docs/data-classes.html)).

- `equals()` / `hashCode()`
- `toString()` — `User(name=John, age=42)` 형태
- `componentN()` — 선언 순서대로 (구조 분해용)
- `copy()`

요구사항:
- 주 생성자에 파라미터가 최소 하나 있어야 하고, 모든 주 생성자 파라미터는 `val` 또는 `var`
- `abstract`, `open`, `sealed`, `inner` 일 수 없다

### 3.2 코드 예제

```kotlin
data class Money(val amount: Long, val currency: String)

val a = Money(1000, "KRW")
val b = Money(1000, "KRW")
println(a == b)                          // true — 구조적 동등성
println(a)                               // Money(amount=1000, currency=KRW)

val doubled = a.copy(amount = a.amount * 2)
val (amount, currency) = a               // 구조 분해
```

### 3.3 실무 사용사례

- API 요청/응답 DTO, 커맨드·이벤트 객체
- `Map` 의 키나 `Set` 원소로 쓰는 값 객체
- 테스트의 기대값 비교 (`assertEquals(expected, actual)` 가 필드 단위로 동작)
- `copy()` 로 불변 객체의 "일부만 바뀐 새 버전" 만들기

### 3.4 함정

**(1) 본문 프로퍼티는 생성 함수에서 제외된다**

```kotlin
data class Person(val name: String) {
    var age: Int = 0
}

val p1 = Person("John").apply { age = 10 }
val p2 = Person("John").apply { age = 20 }
println(p1 == p2)   // true — age 는 equals 에 포함되지 않는다
```

공식 문서의 예제 그대로다 ([Data classes](https://kotlinlang.org/docs/data-classes.html)). 의도적으로 제외하고 싶을 때 쓰는 기법이지만, 모르고 쓰면 버그다.

**(2) `copy()` 는 얕은 복사**

`copy()` 는 구성 요소를 재귀적으로 복사하지 않으므로 다른 객체에 대한 참조는 공유된다 ([Data classes](https://kotlinlang.org/docs/data-classes.html)).

```kotlin
data class Cart(val items: MutableList<String>)

val c1 = Cart(mutableListOf("a"))
val c2 = c1.copy()
c2.items.add("b")
println(c1.items)   // [a, b] — 같은 리스트를 공유
```

data class 의 프로퍼티는 불변 타입(`List`, 다른 data class)으로 두는 것이 원칙이다.

**(3) JPA 엔티티를 data class 로 만들지 마라**

엔티티는 **식별자 기반 동등성**이 필요하고, 지연 로딩 연관관계가 있다. data class 의 `equals`/`hashCode`/`toString` 은 모든 주 생성자 프로퍼티를 건드리므로, 양방향 연관관계에서 `toString` 무한 재귀나 의도치 않은 지연 로딩을 유발할 수 있다. 또한 data class 는 `open` 일 수 없어 프록시와도 맞지 않는다. 엔티티 설계는 K9 에서 다룬다.

### 3.5 `@JvmRecord` — 자바 record 로 컴파일하기

자바 코드가 진짜 `java.lang.Record` 를 기대할 때 data class 에 `@JvmRecord` 를 붙인다. Kotlin 1.5.0 에서 Stable 이 된 JVM record 지원이다 ([What's new in 1.5.0](https://kotlinlang.org/docs/whatsnew15.html)). 요구사항 ([Using Java records in Kotlin](https://kotlinlang.org/docs/jvm-records.html)):

- JVM 16 바이트코드를 타깃하는 모듈이어야 함
- 다른 클래스를 명시적으로 상속할 수 없음(`Any` 포함, 인터페이스 구현은 가능)
- 주 생성자 파라미터로 초기화되는 것 외에 backing field 있는 프로퍼티 불가
- 가변(backing field 있는 `var`) 프로퍼티 불가
- 지역 클래스 불가

```kotlin
@JvmRecord
data class Point(val x: Int, val y: Int)
```

### 3.6 data class vs 자바 record

| 항목 | 코틀린 `data class` | 자바 `record` |
|---|---|---|
| `var` 프로퍼티 | 가능 | 불가 (컴포넌트는 final) |
| `copy()` | 있음 | 없음 |
| 구조 분해 | `val (a, b) = x` | record 패턴 (`instanceof Point(int x, int y)`) |
| 상속 | 다른 클래스 상속 가능 (`open` 불가) | 상속 불가 (`Record` 고정) |

record 패턴 같은 자바 쪽 패턴 매칭은 [J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/) 참고.

---

## 4. sealed class / sealed interface — 닫힌 계층

### 4.1 무엇인가

sealed 클래스·인터페이스의 **직접 하위 클래스는 컴파일 타임에 모두 알려진다.** sealed 클래스가 정의된 모듈·패키지 밖에서는 새 직접 하위 클래스를 만들 수 없다 ([Sealed classes and interfaces](https://kotlinlang.org/docs/sealed-classes.html)).

규칙:
- 직접 하위 클래스는 **같은 패키지**에 있어야 한다. 최상위든 중첩이든 상관없다
- 이 제한은 **간접 하위 클래스에는 적용되지 않는다.** 직접 하위 클래스가 sealed 가 아니면 그 수식어가 허용하는 대로 확장 가능
- sealed 인터페이스는 **Kotlin 1.5.0** 에서 도입됐다. 한 클래스가 여러 sealed 인터페이스를 직접 구현할 수 있어 더 유연한 계층을 만든다 ([What's new in 1.5.0](https://kotlinlang.org/docs/whatsnew15.html))

### 4.2 코드 예제: 결과 타입

```kotlin
sealed interface PaymentResult {
    data class Approved(val txId: String, val amount: Long) : PaymentResult
    data class Declined(val reason: String) : PaymentResult
    data object Timeout : PaymentResult
}

fun toMessage(r: PaymentResult): String = when (r) {
    is PaymentResult.Approved -> "승인 ${r.txId} (${r.amount}원)"
    is PaymentResult.Declined -> "거절: ${r.reason}"
    PaymentResult.Timeout -> "시간 초과"
    // else 불필요 — 모든 경우를 다룸
}
```

`when` 이 sealed 타입을 다룰 때 컴파일러가 **완전성(exhaustiveness)** 을 검사하므로 `else` 가 필요 없다 ([Sealed classes](https://kotlinlang.org/docs/sealed-classes.html), [Control flow](https://kotlinlang.org/docs/control-flow.html)). 새 하위 타입 `Pending` 을 추가하면, `else` 없이 작성한 모든 `when` 식이 컴파일 에러를 낸다 — 이것이 sealed 의 핵심 가치다.

### 4.3 가드 조건 (Kotlin 2.2.0 Stable)

`when` 에 주체(subject)가 있으면 분기 조건 뒤에 `if` 로 추가 조건을 붙일 수 있다. 2.1.0 에서 프리뷰로 들어와 **2.2.0 에서 Stable** 이 됐다 ([What's new in 2.2.0](https://kotlinlang.org/docs/whatsnew22.html), [Control flow — Guard conditions](https://kotlinlang.org/docs/control-flow.html)).

```kotlin
fun route(r: PaymentResult): String = when (r) {
    is PaymentResult.Approved if r.amount >= 1_000_000 -> "고액 승인 검토 큐"
    is PaymentResult.Approved -> "일반 승인"
    is PaymentResult.Declined -> "거절 처리"
    PaymentResult.Timeout -> "재시도 큐"
}
```

규칙: 쉼표로 여러 조건을 묶은 분기에는 가드를 쓸 수 없다. `when` *식*에서 가드를 쓰면 여전히 모든 경우를 덮어야 한다 ([Control flow](https://kotlinlang.org/docs/control-flow.html)).

### 4.4 실무 사용사례

- **도메인 결과/에러 모델링**: 예외 대신 `sealed` 결과 타입을 반환해서 호출자가 모든 실패 케이스를 다루게 강제
- **상태 머신**: `sealed interface OrderState { Created, Paid, Shipped, Cancelled }` — 상태 전이 함수가 모든 상태를 처리하는지 컴파일러가 확인
- **API 라이브러리의 에러 계층**: 공식 문서의 예처럼, 라이브러리 사용자가 임의의 에러 타입을 끼워 넣지 못하게 한다 ([Sealed classes](https://kotlinlang.org/docs/sealed-classes.html))

### 4.5 함정

- **`else` 를 넣는 순간 완전성 검사의 이점이 사라진다.** "일단 컴파일되게" `else -> throw` 를 넣으면, 나중에 하위 타입이 추가돼도 컴파일러가 알려주지 않는다.
- `when` *문(statement)* 은 일반적으로 모든 경우를 다룰 필요가 없다 ([Control flow](https://kotlinlang.org/docs/control-flow.html)). 다만 주체가 enum·sealed·Boolean 이면 1.6.0 에서 경고, **1.7.0 부터 에러**로 완전성이 강제된다 ([Compatibility guide for Kotlin 1.7](https://kotlinlang.org/docs/compatibility-guide-17.html)). 문자열이나 일반 타입 주체라면 여전히 빠진 경우를 조용히 넘기므로, 결과를 반환하는 *식* 형태로 쓰는 습관이 안전하다.
- 멀티플랫폼의 expect sealed 클래스를 common 코드에서 `when` 으로 다룰 때는 `else` 가 여전히 필요하다 ([Sealed classes](https://kotlinlang.org/docs/sealed-classes.html)).

### 4.6 자바 sealed 와 비교

| 항목 | 코틀린 | 자바 (17+) |
|---|---|---|
| 하위 타입 나열 | 불필요 (같은 패키지·모듈이면 됨) | `permits` 로 나열 (하위 타입이 같은 소스 파일에 있으면 생략 가능) |
| 하위 타입 수식어 | 제약 없음 | `final`/`sealed`/`non-sealed` 중 정확히 하나 필수 |
| 완전성 검사 | `when` 식 | `switch` 식/패턴 |

자바 쪽 규칙은 [JEP 409](https://openjdk.org/jeps/409) 기준이다. 자바 쪽 상세는 [J3](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/), [J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/) 참고.

---

## 5. data object — sealed 계층의 단일 값

### 5.1 무엇인가

`data object` 는 Kotlin 1.8.20 에 도입되어 **1.9.0 에서 Stable** 이 됐다 ([What's new in 1.9.0](https://kotlinlang.org/docs/whatsnew19.html)). 일반 `object` 와 달리 `toString()`(객체 이름 반환), `equals()`, `hashCode()` 를 생성한다 ([Object declarations](https://kotlinlang.org/docs/object-declarations.html)).

```kotlin
sealed interface ReadResult
data class Number(val number: Int) : ReadResult
data class Text(val text: String) : ReadResult
data object EndOfFile : ReadResult

fun main() {
    println(Number(7))   // Number(number=7)
    println(EndOfFile)   // EndOfFile  (plain object 라면 EndOfFile@<hashcode> 형태)
}
```

### 5.2 data class 와의 차이

- `copy()` 없음 — 싱글턴이므로
- `componentN()` 없음 — 데이터 프로퍼티가 없으므로
- `equals`/`hashCode` 를 직접 구현할 수 없음

### 5.3 함정: `===` 로 비교하지 말 것

리플렉션이나 직렬화 라이브러리 때문에 런타임에 같은 타입 인스턴스가 하나 더 생길 수 있다. 공식 문서는 data object 를 **`==` 로만 비교하고 `===` 로는 비교하지 말라**고 명시한다 ([Object declarations](https://kotlinlang.org/docs/object-declarations.html)).

---

## 6. enum class

### 6.1 무엇인가와 기본 사용

```kotlin
enum class Color(val rgb: Int) {
    RED(0xFF0000),
    GREEN(0x00FF00),
    BLUE(0x0000FF);                 // 멤버가 있으면 세미콜론으로 구분

    fun hex(): String = "#%06X".format(rgb)
}

val red = Color.valueOf("RED")                      // 없으면 IllegalArgumentException
val byRgb = Color.entries.first { it.rgb == 0xFF0000 }
val byIndex = Color.entries.getOrNull(0)
```

enum 이 멤버를 정의하면 상수 목록과 멤버 정의를 세미콜론으로 구분해야 한다. `valueOf()` 는 이름이 정확히 일치하지 않으면 `IllegalArgumentException` 을 던진다. 코틀린은 `Int` 를 enum 상수로 직접 캐스트할 수 없고 `entries.getOrNull(index)` 를 쓴다 ([Enum classes](https://kotlinlang.org/docs/enum-classes.html)).

### 6.2 `entries` vs `values()`

`entries` 프로퍼티는 1.8.20 에서 실험 기능으로 들어와 **1.9.0 에서 Stable** 이 됐다. 공식 문서는 `values()` 의 "현대적이고 성능 좋은 대체재" 라며 `entries` 사용을 권장한다 ([What's new in 1.9.0](https://kotlinlang.org/docs/whatsnew19.html)). 도입 배경은 `values()` 가 **배열**을 반환해 코틀린·자바 양쪽에서 숨은 성능 문제를 일으킬 수 있고 대부분의 API 가 컬렉션을 쓰기 때문이며, `entries` 는 **미리 할당된 불변 리스트**를 반환한다 ([What's new in 1.8.20](https://kotlinlang.org/docs/whatsnew1820.html)).

제네릭 코드에서는 reified 헬퍼 `enumEntries<T>()`, `enumValueOf<T>()` 를 쓴다 ([Enum classes](https://kotlinlang.org/docs/enum-classes.html)).

```kotlin
inline fun <reified T : Enum<T>> findByName(name: String): T = enumValueOf<T>(name)
```

### 6.3 상수별 동작: 추상 메서드 + 익명 클래스

```kotlin
enum class FeePolicy {
    CARD {
        override fun fee(amount: Long) = amount * 3 / 100
    },
    TRANSFER {
        override fun fee(amount: Long) = 500L
    };

    abstract fun fee(amount: Long): Long
}
```

각 상수가 자기 익명 클래스 본문에서 추상 함수를 구현할 수 있다 ([Enum classes](https://kotlinlang.org/docs/enum-classes.html)).

### 6.4 enum 이냐 sealed 냐

| 기준 | enum | sealed |
|---|---|---|
| 각 케이스가 같은 모양의 데이터 | 적합 | 가능 |
| 케이스마다 다른 필드 | 부적합 | 적합 |
| 케이스당 인스턴스 | 하나 (싱글턴) | 여러 개 가능 (data class) |
| 이름으로 조회·직렬화 | `valueOf`, `entries` 기본 제공 | 직접 구현 |
| DB 컬럼 매핑 | `@Enumerated(EnumType.STRING)` 등 자연스러움 | 별도 변환 필요 |

### 6.5 함정

- JPA 에서 `EnumType.ORDINAL` 로 저장하면 상수 순서를 바꾸는 순간 데이터가 깨진다. 자바와 동일한 함정이다.
- 외부 입력을 `valueOf()` 로 바로 변환하면 잘못된 값에 `IllegalArgumentException` 이 난다. 경계에서는 `entries.firstOrNull { it.name == input }` 처럼 null 을 반환하는 조회를 쓰고 400 으로 매핑하는 편이 낫다.

---

## 7. object 와 companion object

### 7.1 object 선언 — 싱글턴

#### 무엇인가

`object` 선언은 클래스 정의와 단일 인스턴스 생성을 한 번에 한다. 공식 문서에 따르면 **초기화는 스레드 안전하며 첫 접근 시** 일어난다 ([Object declarations](https://kotlinlang.org/docs/object-declarations.html)).

```kotlin
object Clock {
    fun nowMillis(): Long = System.currentTimeMillis()
}

object DefaultListener : MouseAdapter() {
    override fun mouseClicked(e: MouseEvent) { /* ... */ }
}
```

#### 실무 사용사례

- 상태 없는 유틸리티, 상수 묶음
- `Comparator`, 전략 인터페이스의 상태 없는 구현
- sealed 계층의 단일 케이스 (`data object`)

#### 함정

- **가변 상태를 가진 object 는 전역 변수다.** 테스트 간 상태가 새고, 동시성 문제가 생긴다.
- 스프링 애플리케이션에서 의존성이 필요한 싱글턴은 `object` 가 아니라 **스프링 빈**으로 만들어라. `object` 는 DI 컨테이너 밖에 있어서 주입·교체·모킹이 어렵다.

### 7.2 companion object

#### 무엇인가

클래스 안의 `object` 에 `companion` 을 붙이면 클래스 이름으로 멤버를 부를 수 있다. 이름을 생략하면 `Companion` 이 된다 ([Object declarations](https://kotlinlang.org/docs/object-declarations.html)).

중요한 두 가지 사실:
- companion 멤버는 static 처럼 보이지만 **실제로는 companion 객체의 인스턴스 멤버**다. 그래서 companion 이 인터페이스를 구현할 수 있다
- companion object 는 **해당 클래스가 로드될 때 초기화**되며, 이는 자바 static 초기화 블록의 의미와 같다

```kotlin
interface Factory<T> { fun create(): T }

class Order private constructor(val id: String) {
    companion object : Factory<Order> {
        private const val PREFIX = "ORD-"
        override fun create(): Order = Order(PREFIX + System.nanoTime())

        @JvmStatic
        fun of(id: String): Order = Order(id)
    }
}

val o1 = Order.create()
val f: Factory<Order> = Order       // companion 자체를 값으로 전달
```

#### 실무 사용사례

- **정적 팩토리 메서드** + `private constructor` 로 생성 경로 통제
- 로거: `companion object { private val log = LoggerFactory.getLogger(Order::class.java) }`
- 상수: `const val` (기본 타입과 `String` 만 가능)

#### 함정

- 자바에서 부를 때 `@JvmStatic` 이 없으면 `Order.Companion.of(...)` 로 불러야 한다 ([Calling Kotlin from Java](https://kotlinlang.org/docs/java-to-kotlin-interop.html)).
- companion 은 클래스 로드 시 초기화되므로, companion 초기화에서 무거운 작업(네트워크, 파일 I/O)을 하면 클래스를 처음 건드리는 곳에서 예기치 않은 지연·예외가 난다. 이는 자바 static 초기화 블록과 같은 함정이다.

---

## 8. value class — 런타임 비용 없는 타입 래퍼

### 8.1 무엇인가

value class(인라인 클래스)는 **값만 담는 값 기반 클래스의 부분집합**으로, 식별성(identity)이 없다. 주 생성자에 **프로퍼티 하나**를 가져야 하고, 런타임에는 가능한 한 그 하나의 프로퍼티로 표현된다 ([Inline value classes](https://kotlinlang.org/docs/inline-classes.html)). JVM 백엔드에서는 `@JvmInline` 이 필요하다. Kotlin 1.5.0 에서 `value` 수식어로 Stable 이 됐다 ([What's new in 1.5.0](https://kotlinlang.org/docs/whatsnew15.html)).

```kotlin
@JvmInline
value class UserId(val value: Long)

@JvmInline
value class OrderId(val value: Long)

fun cancel(orderId: OrderId, by: UserId) { /* ... */ }

cancel(OrderId(10), UserId(1))       // OK
// cancel(UserId(1), OrderId(10))    // 컴파일 에러 — 인자 순서 실수를 타입이 막는다
```

value class 도 프로퍼티·함수·`init` 블록·보조 생성자를 가질 수 있다 ([Inline value classes](https://kotlinlang.org/docs/inline-classes.html)).

```kotlin
@JvmInline
value class Email(val value: String) {
    init {
        require('@' in value) { "올바르지 않은 이메일: $value" }
    }
    val domain: String get() = value.substringAfter('@')
}
```

### 8.2 typealias 와의 차이

`typealias NameAlias = String` 은 **같은 타입의 다른 이름**일 뿐이라 `String` 을 그대로 넘겨도 된다. value class 는 **다른 타입**이라 섞어 쓰면 컴파일 에러다 ([Inline value classes](https://kotlinlang.org/docs/inline-classes.html)). ID 혼동을 막는 목적이면 value class 여야 한다.

### 8.3 박싱 규칙 — "다른 타입으로 쓰일 때 박싱된다"

컴파일러는 가능하면 내부 타입을 쓰지만, 경험칙상 **value class 가 다른 타입으로 사용될 때 박싱된다** ([Inline value classes](https://kotlinlang.org/docs/inline-classes.html)).

```kotlin
interface I

@JvmInline
value class Foo(val i: Int) : I

fun asInline(f: Foo) {}
fun <T> asGeneric(x: T) {}
fun asInterface(i: I) {}
fun asNullable(i: Foo?) {}

fun main() {
    val f = Foo(42)
    asInline(f)     // 언박싱: Foo 그대로
    asGeneric(f)    // 박싱: 제네릭 T 로 사용
    asInterface(f)  // 박싱: 인터페이스 I 로 사용
    asNullable(f)   // 박싱: Foo? 는 Foo 와 다른 타입
}
```

**실무 의미**: `List<UserId>` 의 원소는 박싱된다. "value class 는 항상 공짜" 가 아니다.

### 8.4 함정

- **참조 동등성(`===`) 금지**: 내부 값으로도, 래퍼로도 표현될 수 있어 참조 비교가 무의미하므로 금지된다 ([Inline value classes](https://kotlinlang.org/docs/inline-classes.html)).
- **이름 맹글링과 자바 상호운용**: value class 를 받는 함수는 오버로드 충돌을 피하려고 이름에 해시가 붙는다. 예: `fun compute(x: UInt)` 는 `compute-<hashcode>(int x)` 로 컴파일된다. 자바에서 부르려면 `@JvmName` 으로 맹글링을 꺼야 한다 ([Inline value classes](https://kotlinlang.org/docs/inline-classes.html)).

```kotlin
@JvmInline
value class UInteger(val x: Int)

@JvmName("computeUInt")
fun compute(x: UInteger) { /* 자바에서 computeUInt(int) 로 호출 */ }
```

- **프레임워크 경계**: 리플렉션으로 생성자나 프로퍼티를 찾는 프레임워크(JPA, 일부 직렬화기)는 맹글링된 시그니처와 언박싱 표현 때문에 value class 를 곧바로 다루지 못할 수 있다. 엔티티 필드나 컨트롤러 파라미터에 쓰기 전에, 사용하는 라이브러리 버전의 지원 여부를 반드시 확인하라. 이 글에서는 특정 라이브러리 버전의 지원 여부를 단정하지 않는다.

---

## 9. 클래스 위임 `by` — 상속 대신 합성

### 9.1 무엇인가

공식 문서는 위임(Delegation) 패턴을 구현 상속의 좋은 대안이라 부르며, 코틀린은 이를 **보일러플레이트 없이** 네이티브로 지원한다고 설명한다 ([Delegation](https://kotlinlang.org/docs/delegation.html)).

```kotlin
interface OrderRepository {
    fun find(id: Long): Order?
    fun save(order: Order): Order
    fun delete(id: Long)
}

// 저장 시에만 메트릭을 찍는 데코레이터 — 나머지 메서드는 자동 위임
class MeteredOrderRepository(
    private val delegate: OrderRepository,
    private val meter: Meter,
) : OrderRepository by delegate {
    override fun save(order: Order): Order {
        meter.increment("order.save")
        return delegate.save(order)
    }
}
```

### 9.2 실무 사용사례

- 데코레이터(캐시, 메트릭, 로깅)를 인터페이스 메서드 수와 무관하게 짧게 작성
- 기본 final 인 클래스의 동작을 *상속 없이* 확장

### 9.3 함정

- 래퍼에서 오버라이드한 멤버는 **위임 대상 객체의 멤버 안에서는 호출되지 않는다.** 위임 대상은 자기 자신의 구현만 볼 수 있다 ([Delegation](https://kotlinlang.org/docs/delegation.html)). 예를 들어 `delegate.saveAll()` 이 내부에서 `save()` 를 부르더라도 래퍼의 메트릭 코드는 실행되지 않는다. 상속의 템플릿 메서드처럼 동작하리라 기대하면 안 된다.

---

## 10. 정리: 무엇을 고를까

| 표현하려는 것 | 선택 |
|---|---|
| 서비스·컴포넌트 | 일반 `class` (스프링이면 all-open 플러그인과 함께) |
| DTO, 이벤트, 값 객체 | `data class` (불변 프로퍼티) |
| 자바 코드가 record 를 기대 | `@JvmRecord data class` (JVM 16+) |
| 케이스마다 모양이 다른 결과·상태 | `sealed interface` + `data class`/`data object` |
| 이름으로 식별되는 고정 상수 | `enum class` + `entries` |
| 상태 없는 싱글턴 | `object` |
| 정적 팩토리·상수·로거 | `companion object` (+ `@JvmStatic`) |
| 원시값 ID 혼동 방지 | `@JvmInline value class` (프레임워크 경계 확인) |
| 상속 없이 동작 확장 | 클래스 위임 `by` |
| JPA 엔티티 | 일반 `class` — data class 아님 (K9) |

다음 글 [K4 함수](https://myoungsoo7.github.io/2026/10/12/kotlin-functions-extension-inline-reified/) 에서는 기본/이름 인자, 확장 함수, 고차 함수, inline/reified 를 다룬다.

---

## References

- Classes — https://kotlinlang.org/docs/classes.html
- Inheritance — https://kotlinlang.org/docs/inheritance.html
- Data classes — https://kotlinlang.org/docs/data-classes.html
- Using Java records in Kotlin (@JvmRecord) — https://kotlinlang.org/docs/jvm-records.html
- Sealed classes and interfaces — https://kotlinlang.org/docs/sealed-classes.html
- Control flow (when, exhaustiveness, guard conditions) — https://kotlinlang.org/docs/control-flow.html
- Enum classes — https://kotlinlang.org/docs/enum-classes.html
- Object declarations and expressions — https://kotlinlang.org/docs/object-declarations.html
- Inline value classes — https://kotlinlang.org/docs/inline-classes.html
- Delegation — https://kotlinlang.org/docs/delegation.html
- Calling Kotlin from Java — https://kotlinlang.org/docs/java-to-kotlin-interop.html
- What's new in Kotlin 1.5.0 (sealed interfaces, value classes, JVM records) — https://kotlinlang.org/docs/whatsnew15.html
- What's new in Kotlin 1.8.20 (entries 도입 배경) — https://kotlinlang.org/docs/whatsnew1820.html
- Compatibility guide for Kotlin 1.7 (exhaustive when statements) — https://kotlinlang.org/docs/compatibility-guide-17.html
- JEP 409: Sealed Classes — https://openjdk.org/jeps/409
- What's new in Kotlin 1.9.0 (enum entries, data objects stable) — https://kotlinlang.org/docs/whatsnew19.html
- What's new in Kotlin 2.2.0 (guard conditions stable) — https://kotlinlang.org/docs/whatsnew22.html

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
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/) ← 지금 글
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
