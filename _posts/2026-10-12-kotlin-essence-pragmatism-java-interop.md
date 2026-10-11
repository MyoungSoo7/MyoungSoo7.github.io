---
layout: post
title: "코틀린의 본질 — 실용주의, 자바 상호운용, 간결성과 안전성이라는 설계 목표"
date: 2026-10-12 00:21:42 +0900
categories: [kotlin]
tags: [kotlin, jvm, java-interop, null-safety, language-design, k2-compiler, spring]
---

자바·코틀린 20편 시리즈의 **코틀린 1편(K1)** 이다. 문법 하나하나로 들어가기 전에, 코틀린이 *무엇을 위해* 만들어졌고 그 목표가 문법 곳곳에 어떻게 새겨져 있는지를 먼저 정리한다. 이후 K2(널 안전)~K10(스프링부트 호환) 에서 다루는 거의 모든 규칙은 이 글의 세 가지 축 — **실용주의(pragmatism)**, **자바 상호운용(interoperability)**, **간결성·안전성(conciseness & safety)** — 으로 설명된다.

자바 쪽 짝 글은 [J1 자바의 본질: JVM·바이트코드·하위 호환성](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/) 이다. 같이 읽으면 "자바가 지키려는 것"과 "코틀린이 고치려는 것"이 대칭으로 보인다. 역사적 맥락은 이전 글 [Java 는 C++ 의 무엇을 지웠고, Kotlin 은 Java 의 무엇을 지웠나](https://myoungsoo7.github.io/2026/08/20/why-java-then-why-kotlin/) 에서 다룬 적이 있다.

---

## 1. 코틀린은 무엇인가 — 사실관계부터

### 1.1 공식 정의

코틀린 공식 FAQ 는 코틀린을 이렇게 정의한다 ([Kotlin FAQ](https://kotlinlang.org/docs/faq.html)).

- JVM, Android, JavaScript, Wasm, Native 를 타깃으로 하는 **오픈소스 정적 타입 언어**
- **JetBrains** 가 개발. 프로젝트는 2010년에 시작했고 **1.0 정식 릴리스는 2016년 2월**
- **Apache 2.0** 라이선스, 무료
- JVM 타깃일 때 **기본으로 Java 8 호환 바이트코드**를 만들고, 더 높은 자바 버전을 명시적으로 타깃할 수 있다

즉 코틀린은 "새 런타임"이 아니라 **기존 JVM 위에 얹는 새 언어**다. 이 한 문장이 상호운용 설계의 출발점이다. 자바와 같은 바이트코드, 같은 클래스 파일, 같은 런타임을 쓰기 때문에, 자바 라이브러리를 그대로 쓰고 자바 코드에서 코틀린 클래스를 그대로 부를 수 있다.

### 1.2 릴리스 체계

2.0.0 부터 코틀린은 릴리스를 세 종류로 나눈다 ([Kotlin release process](https://kotlinlang.org/docs/releases.html)).

| 종류 | 형태 | 주기 |
|---|---|---|
| 언어 릴리스 | 2.x.0 | 6개월마다 |
| 툴링 릴리스 | 2.x.20 | 언어 릴리스 3개월 뒤 |
| 버그픽스 릴리스 | 2.x.yz | 일정 없음 |

이 글을 쓰는 2026-10-12 기준 최신은 **2.4.21(2026-10-08)** 이고, 언어 릴리스 2.4.0 은 2026-06-03 에 나왔다 ([Kotlin releases](https://kotlinlang.org/docs/releases.html)). 실무에서는 "언어 기능이 바뀌는 건 x.0, 빌드 도구·성능은 x.20" 으로 기억하면 업그레이드 계획을 세우기 쉽다.

### 1.3 K2 컴파일러

**Kotlin 2.0.0(2024-05-21)** 에서 새 프런트엔드인 **K2 컴파일러가 Stable** 이 되었고 JVM·Native·Wasm·JS 모든 타깃의 기본 컴파일러가 되었다 ([What's new in Kotlin 2.0.0](https://kotlinlang.org/docs/whatsnew20.html)). 스마트 캐스트 개선 같은 언어 체감 변화도 이때 들어왔다(K2 편에서 자세히).

---

## 2. 첫 번째 축: 실용주의 (Pragmatism)

### 2.1 무엇인가

코틀린 팀은 언어 진화 원칙을 "실용적 진화(pragmatic evolution)" 라고 부르고, 세 가지를 든다 ([Kotlin evolution principles](https://kotlinlang.org/docs/kotlin-evolution-principles.html)).

1. 언어를 시간이 지나도 현대적으로 유지한다
2. 사용자와의 지속적인 피드백 루프를 유지한다
3. 새 버전으로의 업데이트를 쉽고 편하게 만든다

같은 문서는 기능 성숙도를 **Exploration and design → KEEP discussion → In preview(Experimental/Beta) → Stable** 단계로 관리하고, Stable 이 되어야 하위 호환 보장을 준다고 설명한다. 새 기능은 opt-in 프리뷰로 먼저 풀고 실사용 피드백을 받은 뒤 굳힌다.

### 2.2 실제 예: 프리뷰 → Stable 사이클

이 사이클이 실제로 어떻게 돌아가는지 최근 사례 두 개를 보자.

| 기능 | 프리뷰 | Stable | 출처 |
|---|---|---|---|
| `when` 가드 조건, non-local `break`/`continue`, 멀티 달러 문자열 보간 | 2.1.0 | 2.2.0 | [2.1.0](https://kotlinlang.org/docs/whatsnew21.html), [2.2.0](https://kotlinlang.org/docs/whatsnew22.html) |
| 컨텍스트 파라미터(context parameters) | 2.2.0 | 2.4.0 (컨텍스트 인자·callable reference 제외) | [2.2.0](https://kotlinlang.org/docs/whatsnew22.html), [2.4.0](https://kotlinlang.org/docs/whatsnew24.html) |

컨텍스트 파라미터는 원래 "컨텍스트 리시버(context receivers)" 라는 실험 기능이었는데, 피드백을 받아 설계를 바꿔 **대체**한 것이다 ([Context parameters](https://kotlinlang.org/docs/context-parameters.html)). "한 번 낸 실험 기능도 틀렸으면 버린다" 가 실용적 진화의 실제 모습이다.

### 2.3 실용주의가 문법에 남긴 흔적

실용주의는 "이론적으로 가장 우아한 것" 보다 "현업에서 매일 부딪히는 문제를 줄이는 것" 을 고른다는 뜻이다. 공식 FAQ 도 코틀린이 객체지향과 함수형을 섞는다고 설명한다 ([FAQ](https://kotlinlang.org/docs/faq.html)).

```kotlin
// 1) if / when / try 가 모두 식(expression) — 삼항 연산자가 따로 필요 없다
val grade = if (score >= 90) "A" else "B"

val label = when (status) {
    Status.ACTIVE -> "활성"
    Status.SUSPENDED -> "정지"
    Status.DELETED -> "삭제"
}

val port = try { env.toInt() } catch (e: NumberFormatException) { 8080 }

// 2) 최상위 함수 — 'Utils' 클래스를 억지로 만들지 않는다
fun slugify(s: String): String = s.lowercase().replace(' ', '-')

// 3) 문자열 템플릿
println("user=$userId, items=${cart.items.size}")
```

자바의 삼항 연산자 `a ? b : c` 는 코틀린에 없고 `if` 식으로 대체된다는 점은 공식 비교 문서에 명시돼 있다 ([Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html)).

### 2.4 함정: "실용적" ≠ "아무렇게나"

- 실용주의 문법(스코프 함수, 확장 함수, 연산자 오버로딩)은 **남용하면 읽기 어려워진다.** 공식 문서도 스코프 함수 남용과 중첩을 피하라고 명시한다(K5 편).
- Experimental 기능을 프로덕션 공용 라이브러리에 쓰면, Stable 이 될 때 시그니처가 바뀔 수 있다. 공식 원칙상 Stable 전에는 하위 호환 보장이 없다 ([evolution principles](https://kotlinlang.org/docs/kotlin-evolution-principles.html)).

---

## 3. 두 번째 축: 자바 상호운용 (Interoperability)

코틀린을 "자바 대체재"가 아닌 "자바와 섞어 쓰는 언어" 로 만드는 핵심이다. FAQ 는 코틀린이 자바와 **100% 상호운용**된다고 밝힌다 ([FAQ](https://kotlinlang.org/docs/faq.html)).

### 3.1 코틀린에서 자바 부르기

#### 무엇인가

자바 클래스는 import 해서 그냥 쓴다. 여기에 몇 가지 "번역 규칙" 이 붙는다 ([Calling Java from Kotlin](https://kotlinlang.org/docs/java-interop.html)).

| 자바 쪽 | 코틀린에서 보이는 모습 |
|---|---|
| `getX()` / `setX(v)` | 프로퍼티 `x` (합성 프로퍼티) |
| `isX()` (boolean) | 프로퍼티 `isX` |
| `void` 반환 | `Unit` 반환 |
| `java.lang.Object` | `Any` (`toString`/`hashCode`/`equals` 만 노출) |
| `int` / `java.lang.Integer` | `Int` / `Int?` |
| `List<T>` | `(Mutable)List<T>!` (플랫폼 타입) |
| `Foo<? extends Bar>` | `Foo<out Bar!>!` |
| raw `List` | `List<*>!` |
| checked exception | 강제되지 않음 (모든 예외가 unchecked) |

#### 코드 예제

```kotlin
import java.util.Calendar

fun configure(calendar: Calendar) {
    // setFirstDayOfWeek(...) 호출
    calendar.firstDayOfWeek = Calendar.MONDAY
    // isLenient() 호출
    if (!calendar.isLenient) {
        calendar.isLenient = true
    }
}

// 자바 식별자가 코틀린 키워드(in, object, is 등)일 때는 백틱으로 이스케이프
// 예: 자바 클래스 Foo 에 is(Object) 메서드가 있다면
fun matches(foo: Foo, bar: Any): Boolean = foo.`is`(bar)
```

자바 쪽에 setter 만 있고 getter 가 없으면 코틀린 프로퍼티로 보이지 않는다. 코틀린이 set-only 프로퍼티를 지원하지 않기 때문이다 ([java-interop](https://kotlinlang.org/docs/java-interop.html)).

#### 실무 사용사례

- 스프링·JPA·Jackson·Apache Commons 같은 자바 생태계 라이브러리를 **래퍼 없이** 그대로 사용
- 레거시 자바 서비스에 **새 모듈만 코틀린으로** 추가하는 점진 도입
- 테스트만 코틀린으로 먼저 쓰기 (Mockito 의 `` `when` `` 처럼 키워드 충돌은 백틱)

#### 함정

- **플랫폼 타입(`T!`)**: 자바가 넘긴 값은 nullable 인지 아닌지 컴파일러가 모른다. 코틀린 쪽에서 `String` 으로 받으면 할당 시점에 런타임 단언이 들어가고, null 이면 그 자리에서 NPE 가 난다 ([java-interop](https://kotlinlang.org/docs/java-interop.html)). K2 편에서 자세히 다룬다.
- `Any` 에는 `wait()`/`notify()` 가 없다. 공식 문서도 `java.util.concurrent` 사용을 권한다 ([java-interop](https://kotlinlang.org/docs/java-interop.html)).

### 3.2 자바에서 코틀린 부르기

#### 무엇인가

반대 방향은 코틀린이 **자바가 이해하는 모양**으로 컴파일되도록 애노테이션으로 조정한다 ([Calling Kotlin from Java](https://kotlinlang.org/docs/java-to-kotlin-interop.html)).

| 코틀린 선언 | 기본 컴파일 결과 | 조정 애노테이션 |
|---|---|---|
| `app.kt` 의 최상위 함수 | `AppKt` 클래스의 static 메서드 | `@file:JvmName("AppUtils")` |
| `companion object` 의 함수 | `Companion` 인스턴스 메서드 | `@JvmStatic` |
| 프로퍼티 | getter/setter | `@JvmField` (필드로 노출) |
| 기본값 있는 파라미터 | 전체 파라미터 1개 시그니처 | `@JvmOverloads` |
| 예외 던지는 함수 | `throws` 없음 | `@Throws(IOException::class)` |
| 소거 후 시그니처 충돌 | 컴파일 에러 | `@JvmName("...")` |

#### 코드 예제

```kotlin
@file:JvmName("Slugs")
package com.example.text

fun slugify(s: String): String = s.lowercase().replace(' ', '-')

class Money private constructor(val amount: Long, val currency: String) {
    companion object {
        @JvmStatic
        fun of(amount: Long, currency: String = "KRW"): Money = Money(amount, currency)
    }
}

class Circle @JvmOverloads constructor(
    val x: Int,
    val y: Int,
    val radius: Double = 1.0,
)

@Throws(java.io.IOException::class)
fun writeReport(path: String) {
    java.io.File(path).writeText("ok")
}
```

```java
// 자바 쪽
String s = Slugs.slugify("Hello World");     // @file:JvmName
Money m = Money.of(1000L, "KRW");            // @JvmStatic (기본값은 자바에 안 보임)
Circle c = new Circle(0, 0);                 // @JvmOverloads 가 만든 생성자
try {
    WriterKt.writeReport("/tmp/r.txt");      // 파일명이 writer.kt 라고 가정
} catch (java.io.IOException e) { /* @Throws 덕분에 catch 가능 */ }
```

#### 실무 사용사례

- 코틀린으로 만든 **공용 라이브러리**를 자바 팀이 쓰는 경우 — `@JvmStatic`, `@JvmOverloads` 가 없으면 자바 쪽 호출 코드가 `Money.Companion.of(...)` 처럼 어색해진다.
- 자바 코드가 checked exception 으로 흐름을 제어하는 레거시 — `@Throws` 없이는 자바 컴파일러가 `catch (IOException e)` 를 "던지지 않는 예외를 잡는다" 며 거부한다.

#### 함정

- `@JvmOverloads` 는 **추상 메서드·인터페이스 메서드에 못 붙인다** ([java-to-kotlin-interop](https://kotlinlang.org/docs/java-to-kotlin-interop.html)).
- `@JvmField` 는 private·open·override·const 프로퍼티나 위임 프로퍼티에는 못 붙인다.
- 코틀린 public 함수는 non-null 파라미터에 대해 **런타임 null 체크**를 생성한다. 자바에서 null 을 넘기면 자바 쪽에서 즉시 NPE 가 난다 ([java-to-kotlin-interop](https://kotlinlang.org/docs/java-to-kotlin-interop.html)). Kotlin 1.4.0 부터 이 런타임 null 체크들은 모두 `java.lang.NullPointerException` 으로 통일됐다 ([What's new in 1.4.0](https://kotlinlang.org/docs/whatsnew14.html)).

### 3.3 상호운용이 설계에 강요한 타협

상호운용을 위해 코틀린이 *일부러* 자바와 같게 남긴 것도 있다.

- **제네릭은 소거된다.** 코틀린 제네릭도 자바처럼 런타임에 타입 인자를 유지하지 않는다 ([java-interop](https://kotlinlang.org/docs/java-interop.html)). 그래서 `reified` 같은 우회로가 생겼다(K4, K8 편).
- **원시 타입은 문법에 없지만 바이트코드엔 있다.** 공식 비교 문서는 "바이트코드는 가능한 한 원시 타입을 쓰지만 명시적으로 노출되지는 않는다" 고 설명한다 ([Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html)). `Int` 는 상황에 따라 `int` 로, `Int?` 는 `Integer` 로 컴파일된다.

---

## 4. 세 번째 축: 간결성과 안전성

### 4.1 공식 문서가 꼽는 "자바에서 고친 것"

[Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html) 문서의 "Some Java issues addressed in Kotlin" 목록을 그대로 옮기면 이렇다.

1. null 참조가 타입 시스템으로 통제된다
2. raw 타입이 없다
3. 배열이 불변(invariant)이다
4. SAM 변환이 아닌 진짜 함수 타입이 있다
5. 와일드카드 없는 사용 지점 변성
6. checked exception 이 없다
7. 읽기 전용 컬렉션과 가변 컬렉션 인터페이스가 분리돼 있다

각 항목이 이 시리즈의 어느 글로 이어지는지 정리하면:

| 고친 것 | 다루는 글 |
|---|---|
| null 통제 | K2 널 안전 |
| 함수 타입 | K4 함수 |
| 사용 지점 변성·배열 불변 | K8 제네릭 변성 |
| checked exception 제거 | 이 글 3.2, J5 와 비교 |
| 읽기 전용/가변 컬렉션 | K6 컬렉션 |

### 4.2 간결성 — 보일러플레이트를 언어로 흡수

#### 코드 예제: 자바 엔티티 vs 코틀린

```java
// Java (record 없이 쓰던 전통적 DTO)
public final class UserDto {
    private final String name;
    private final int age;

    public UserDto(String name, int age) {
        this.name = name;
        this.age = age;
    }
    public String getName() { return name; }
    public int getAge() { return age; }

    @Override public boolean equals(Object o) { /* ... */ }
    @Override public int hashCode() { /* ... */ }
    @Override public String toString() { /* ... */ }
}
```

```kotlin
// Kotlin
data class UserDto(val name: String, val age: Int)
```

`data class` 는 `equals()`/`hashCode()`, `toString()`, `componentN()`, `copy()` 를 생성한다 ([Data classes](https://kotlinlang.org/docs/data-classes.html)). 자바 16 의 record 와 겹치는 영역이지만 `copy()` 와 구조 분해는 data class 쪽에만 있다. 자세한 비교는 K3 편.

공식 FAQ 는 자바 대비 코드 라인 수가 대략 40% 줄어든다고 *주장* 한다 ([FAQ](https://kotlinlang.org/docs/faq.html)). 이 수치는 JetBrains 자체 추정이며 독립 측정이 아니라는 점을 감안해서 읽어야 한다.

#### 간결성 문법 한눈에

[Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html) 의 "What Kotlin has that Java does not" 목록 중 실무 체감이 큰 것만 골랐다.

| 기능 | 한 줄 예 | 다루는 글 |
|---|---|---|
| 프로퍼티 | `var name: String = ""` | K3 |
| 주 생성자 | `class A(val x: Int)` | K3 |
| 타입 추론 | `val list = mutableListOf<String>()` | — |
| 기본값·이름 있는 인자 | `connect(timeout = 3)` | K4 |
| 확장 함수 | `fun String.isEmail(): Boolean` | K4 |
| 싱글턴 | `object Registry` | K3 |
| 위임 | `class A(b: B) : I by b` | K3 |
| 코루틴 | `suspend fun load()` | K7 |

### 4.3 안전성 — 실수를 타입으로 막는다

#### 무엇인가

안전성의 핵심은 **NPE 를 컴파일 타임 문제로 끌어올리는 것**이다. 공식 문서는 코틀린에서 NPE 가 날 수 있는 원인을 다음으로 한정한다 ([Null safety](https://kotlinlang.org/docs/null-safety.html)).

- 명시적인 `throw NullPointerException()`
- `!!` 연산자
- 초기화 중 데이터 불일치 (생성자에서 `this` 누출, 상위 클래스 생성자가 open 멤버 호출)
- 자바 상호운용 (플랫폼 타입, 제네릭 nullability 등)

#### 코드 예제

```kotlin
fun greet(name: String?) {
    // println(name.length)        // 컴파일 에러: nullable 수신 객체
    println(name?.length ?: 0)     // 안전 호출 + 엘비스
    if (name != null) {
        println(name.length)       // 스마트 캐스트: 여기선 String
    }
}
```

안전성은 null 만이 아니다.

- **기본 final**: 코틀린 클래스와 멤버는 기본이 final 이고, 상속을 허용하려면 `open` 을 붙여야 한다 ([Inheritance](https://kotlinlang.org/docs/inheritance.html)). "상속을 위한 설계가 아니면 상속을 막아라" 를 기본값으로 만든 것이다. 이 결정이 스프링 프록시와 충돌해서 `kotlin-spring` 플러그인이 생겼다(K9).
- **`val` 우선**: 재할당 불가 참조를 기본 선택지로 둔다.
- **`when` 의 완전성 검사**: sealed/enum 을 `when` 식으로 다루면 모든 경우를 다뤘는지 컴파일러가 확인한다 ([Control flow](https://kotlinlang.org/docs/control-flow.html)).

#### 함정

- `!!` 는 "여기서 NPE 가 나도 좋다" 는 선언이다. 코드 리뷰에서 `!!` 개수를 세는 팀이 있는 이유다.
- 안전성은 **코틀린 경계 안**에서만 완전하다. 자바 라이브러리 반환값(플랫폼 타입), 리플렉션으로 채워지는 필드(JPA, Jackson)는 컴파일러가 보장하지 못한다. 이 구멍을 메우는 것이 K2(애노테이션), K9(JPA·Jackson 플러그인) 의 주제다.

---

## 5. 자바가 가졌지만 코틀린이 *일부러* 뺀 것

공식 비교 문서의 "What Java has that Kotlin does not" 목록 ([Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html)) 과, 각 항목의 코틀린 대안이다.

| 자바에 있는 것 | 코틀린 대안 |
|---|---|
| checked exception | 없음. 자바와 맞출 땐 `@Throws` |
| 클래스가 아닌 원시 타입 | `Int`, `Long` 등. 바이트코드에선 원시 타입 사용 |
| static 멤버 | companion object, 최상위 함수, 확장 함수, `@JvmStatic` |
| 와일드카드 타입 | 선언 지점 변성 + 타입 프로젝션 (K8) |
| 삼항 연산자 | `if` 식 |
| record | `data class` (+ `@JvmRecord`) |
| package-private | 없음. `internal`(모듈 단위) |

### 5.1 package-private 이 없다는 것의 의미

코틀린의 가시성 수식어는 `private`, `protected`, `internal`, `public` 네 개이고 기본은 `public` 이다. `internal` 은 **같은 모듈** 안에서 보인다 ([Visibility modifiers](https://kotlinlang.org/docs/visibility-modifiers.html)).

```kotlin
// 모듈 내부 구현 — 다른 Gradle 모듈에서는 안 보인다
internal class OrderNumberGenerator {
    fun next(): String = "ORD-" + System.nanoTime()
}
```

#### 함정

- 자바 개발자는 "아무것도 안 쓰면 패키지 전용" 이라는 감각이 있는데, 코틀린은 **아무것도 안 쓰면 public** 이다. 라이브러리 모듈이라면 Explicit API mode([Kotlin 1.4.0](https://kotlinlang.org/docs/whatsnew14.html) 에서 도입)로 가시성 명시를 강제하는 것을 고려한다.
- `internal` 선언은 **자바에서는 public 이 된다.** 컴파일러가 internal *멤버* 이름을 바이트코드에서 맹글링하긴 하지만, internal *클래스*의 public 멤버 이름은 맹글링되지 않아 자바에서 그대로 호출할 수 있다 ([Calling Kotlin from Java](https://kotlinlang.org/docs/java-to-kotlin-interop.html)). 자바 코드가 섞인 모듈에서 `internal` 을 캡슐화 장치로 믿지 말 것.

### 5.2 checked exception 이 없다는 것의 의미

```kotlin
fun render(list: List<*>, to: Appendable) {
    for (item in list) {
        to.append(item.toString())  // 자바라면 IOException 처리 강제
    }
}
```

공식 문서의 예제 그대로다 ([java-interop](https://kotlinlang.org/docs/java-interop.html)). 코틀린 컴파일러는 자바 메서드의 checked exception 처리를 강제하지 않는다.

- **사용사례**: 람다 안에서 checked exception 을 감싸던 보일러플레이트(`try { ... } catch (IOException e) { throw new UncheckedIOException(e); }`)가 사라진다.
- **함정**: 강제가 없다는 건 *잊어도 된다* 는 뜻이 아니다. 스프링 `@Transactional` 의 기본 롤백 규칙은 런타임(unchecked) 예외 기준이고 checked exception 은 기본적으로 롤백하지 않는데 ([Spring Framework: Rolling Back](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html)), 코틀린에서 checked exception 을 던지면 자바와 똑같이 롤백 대상이 아니다. 예외 정책은 언어가 아니라 팀이 정해야 한다. 자바 쪽 예외 설계는 [J5](https://myoungsoo7.github.io/2026/10/12/java-null-optional-exceptions/) 참고.

---

## 6. 본질을 한 장으로: 코틀린을 쓸 때의 판단 기준

| 질문 | 코틀린의 기본 답 | 근거 |
|---|---|---|
| 이 값은 null 일 수 있나? | 타입에 적는다 (`T` vs `T?`) | [Null safety](https://kotlinlang.org/docs/null-safety.html) |
| 이 클래스를 상속해도 되나? | 기본 금지 (`open` 필요) | [Inheritance](https://kotlinlang.org/docs/inheritance.html) |
| 이 값을 바꿔도 되나? | `val` 기본, 컬렉션은 읽기 전용 기본 | [Comparison to Java](https://kotlinlang.org/docs/comparison-to-java.html) |
| 자바와 같이 쓰나? | 쓴다. 경계엔 애노테이션과 플랫폼 타입 주의 | [java-interop](https://kotlinlang.org/docs/java-interop.html) |
| 새 기능 써도 되나? | Stable 이면. 프리뷰는 opt-in 이고 바뀔 수 있다 | [evolution principles](https://kotlinlang.org/docs/kotlin-evolution-principles.html) |

### 6.1 안티패턴: "자바를 코틀린 문법으로 쓰기"

```kotlin
// 자바식 코틀린 — 컴파일은 되지만 코틀린의 이점을 다 버린 코드
class UserService {
    var repository: UserRepository? = null            // 주입을 nullable 로 받음

    fun find(id: Long): User? {
        val user = repository!!.findById(id)          // !! 남발
        if (user == null) {
            return null
        } else {
            return user
        }
    }
}
```

```kotlin
// 코틀린다운 코드
class UserService(private val repository: UserRepository) {  // 생성자 주입, non-null
    fun find(id: Long): User? = repository.findById(id)
}
```

차이는 문법이 아니라 **설계 목표를 받아들였는가** 다. 생성자 주입 + non-null 타입이 스프링에서 어떻게 맞물리는지는 [K9 코틀린 × 스프링](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) 에서 다룬다.

### 6.2 언제 코틀린의 이점이 줄어드는가

- **리플렉션 중심 프레임워크와의 경계**: JPA 엔티티, Jackson 역직렬화처럼 프레임워크가 기본 생성자로 객체를 만들고 필드를 채우는 곳에서는 null 안전과 final 기본값이 오히려 마찰을 만든다. 그래서 컴파일러 플러그인(all-open, no-arg)이 필요하다 (K9).
- **자바 비중이 큰 코드베이스**: 플랫폼 타입이 경계마다 생기므로, 자바 쪽에 nullability 애노테이션이 없으면 코틀린의 안전성이 크게 희석된다 (K2).

---

## 7. 정리

- 코틀린은 **JVM 위의 정적 타입 언어**로, 자바와 같은 바이트코드를 만들며 100% 상호운용을 목표로 한다.
- 설계의 세 축은 **실용주의**(프리뷰→Stable 의 점진적 진화, 식 중심 문법), **상호운용**(합성 프로퍼티, 플랫폼 타입, `@Jvm*` 애노테이션), **간결성·안전성**(data class, null 타입, 기본 final) 이다.
- 상호운용을 위해 남긴 타협(타입 소거, 플랫폼 타입)과 안전성을 위해 바꾼 기본값(final, public, unchecked)이 이후 모든 글의 "함정" 섹션의 근원이다.

다음 글 [K2 널 안전](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/) 에서는 안전성 축의 중심인 null 처리와 자바 경계의 플랫폼 타입을 깊게 다룬다.

---

## References

- Kotlin FAQ — https://kotlinlang.org/docs/faq.html
- Comparison to Java — https://kotlinlang.org/docs/comparison-to-java.html
- Kotlin evolution principles — https://kotlinlang.org/docs/kotlin-evolution-principles.html
- Kotlin release process / releases — https://kotlinlang.org/docs/releases.html
- Calling Java from Kotlin — https://kotlinlang.org/docs/java-interop.html
- Calling Kotlin from Java — https://kotlinlang.org/docs/java-to-kotlin-interop.html
- Null safety — https://kotlinlang.org/docs/null-safety.html
- Inheritance — https://kotlinlang.org/docs/inheritance.html
- Visibility modifiers — https://kotlinlang.org/docs/visibility-modifiers.html
- Data classes — https://kotlinlang.org/docs/data-classes.html
- Control flow (when, guard conditions) — https://kotlinlang.org/docs/control-flow.html
- Context parameters — https://kotlinlang.org/docs/context-parameters.html
- What's new in Kotlin 1.4.0 — https://kotlinlang.org/docs/whatsnew14.html
- What's new in Kotlin 2.0.0 — https://kotlinlang.org/docs/whatsnew20.html
- What's new in Kotlin 2.1.0 — https://kotlinlang.org/docs/whatsnew21.html
- What's new in Kotlin 2.2.0 — https://kotlinlang.org/docs/whatsnew22.html
- What's new in Kotlin 2.4.0 — https://kotlinlang.org/docs/whatsnew24.html
- Spring Framework Reference, Rolling Back a Declarative Transaction — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html

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

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/) ← 지금 글
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
