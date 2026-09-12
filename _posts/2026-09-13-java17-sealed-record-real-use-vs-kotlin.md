---
layout: post
title: "sealed 와 record 는 실무에서 무엇이 되는가 — 자바 17의 ADT, 코틀린과 나란히 놓고 보기"
date: 2026-09-13 03:29:19 +0900
categories: [java, kotlin]
tags: [java17, sealed-classes, records, kotlin, data-class, pattern-matching, adt]
---

자바 17의 sealed class([JEP 409](https://openjdk.org/jeps/409))와 자바 16의 record([JEP 395](https://openjdk.org/jeps/395))는 따로 보면 각각 "상속 제한 문법"과 "보일러플레이트 절감 문법"처럼 보인다. 하지만 실무에서 이 둘은 거의 항상 **한 세트**로 쓰인다. 둘을 합치면 함수형 언어들이 대수적 데이터 타입(ADT)이라 부르던 것 — "이 타입의 값은 정확히 이 몇 가지 모양 중 하나다"라는 선언 — 이 자바에 들어오기 때문이다. 코틀린은 같은 자리를 sealed class + data class 로 먼저 채웠다. 이 글은 실제 운영 코드에서 두 기능이 어떤 모습으로 쓰이는지 정리하고, 코틀린과 어디가 같고 어디가 다른지 비교한다.

## record 의 실제 사용처

내가 운영하는 정산 시스템(Java, Spring Boot 멀티모듈)에서 `record` 선언을 세어 보니 **680개**였다. 클래스 문법 중 가장 많이 쓰는 축에 든다. 용도는 대부분 다음 네 가지로 수렴한다.

**① API 요청/응답 DTO.** 컨트롤러 경계를 넘는 데이터는 거의 전부 record 다. 생성자·접근자·`equals`/`hashCode`/`toString` 이 언어 차원에서 보장되므로, Lombok `@Value` 로 하던 일이 표준 문법이 됐다.

```java
public record ReviewRequest(@NotNull Boolean matched, String note) { }
```

**② 설정 바인딩.** Spring Boot 의 `@ConfigurationProperties` 는 record 의 생성자 바인딩을 공식 지원한다([Spring Boot 공식 문서](https://docs.spring.io/spring-boot/reference/features/external-config.html)). 설정값은 기동 후 바뀌면 안 되는 값이므로 불변 record 가 정확히 맞는 그릇이다.

```java
public record CollateralOcrProperties(String apiKey, String model, String baseUrl) { }
```

**③ 값 객체(Value Object)와 복합 키.** 금액+통화, 계좌+일자 같은 "동등성이 곧 정체성"인 값들. record 의 `equals` 는 전 컴포넌트 비교라 Map 키로 바로 안전하다.

**④ 검증이 딸린 값.** record 의 compact constructor 는 "생성 시점 검증"을 강제하는 좋은 자리다. [JEP 395](https://openjdk.org/jeps/395)가 명시하는 설계 의도 자체가 "데이터를 데이터로 모델링"이다.

반대로 **JPA 엔티티로는 못 쓴다.** Jakarta Persistence 명세는 엔티티에 인자 없는 생성자와 프록시 가능한(비-final) 구조를 요구하는데 record 는 둘 다 위반한다. 그래서 실무 구도는 "엔티티는 클래스, 경계를 넘는 모든 데이터는 record"로 자연스럽게 갈라진다.

## sealed 의 실제 사용처

record 보다 훨씬 적게, 그러나 훨씬 전략적인 자리에 쓰인다. 같은 코드베이스에서 sealed 는 두 곳뿐이었는데, 그 두 곳이 전형적인 실전 용례다.

**① 결과(Result) 타입.** 알림 채널 하나의 전달 결과를 이렇게 모델링했다:

```java
/**
 * 채널 1건의 전달 결과. sealed 라 호출자가 성공/실패를 전수 처리해야 한다
 * (새 결과 종류가 생기면 switch 가 컴파일 에러로 알려준다).
 */
public sealed interface ChannelResult permits ChannelResult.Success, ChannelResult.Failure {
    String channel();
    int attempts();

    record Success(String channel, int attempts) implements ChannelResult { }
    record Failure(String channel, int attempts, String error) implements ChannelResult { }
}
```

sealed interface + record 구현체 — 이것이 자바식 ADT 의 표준형이다. 예외를 던지는 대신 실패를 값으로 돌려주면, 호출자는 실패 처리를 "잊을 수" 없다.

**② 프로토콜/스펙 모델링.** 금융 FEP 전문(電文)의 요소 타입처럼 "종류가 닫혀 있는 문법"을 표현할 때다. 전문 요소는 고정 필드·반복부·가변 반복부 중 하나이지 그 외의 것일 수 없고, sealed 가 그 사실을 컴파일러에 알린다. 상태 기계의 상태, 도메인 이벤트 계층, API 에러 분류도 같은 패턴이다.

여기서 정직해야 할 부분: **sealed 의 최대 수혜인 "빠짐없는(exhaustive) switch"는 자바 17 기준으로는 미완성이었다.** 17에서 switch 패턴 매칭은 preview([JEP 406](https://openjdk.org/jeps/406))였고, 정식 기능이 된 것은 자바 21의 [JEP 441](https://openjdk.org/jeps/441)(pattern matching for switch)과 [JEP 440](https://openjdk.org/jeps/440)(record patterns)부터다. [JEP 409](https://openjdk.org/jeps/409) 스스로도 sealed 의 "significant benefit"이 switch 패턴 매칭에서 실현된다고 적고 있다. 즉 자바 17에서 sealed 는 "설계 의도의 문서화 + 무단 상속 차단"이고, 21에 와서야 컴파일러가 case 누락을 잡아주는 완전체가 된다.

```java
// 자바 21+: Failure 케이스를 지우면 컴파일 에러
String line = switch (result) {
    case ChannelResult.Success s -> s.channel() + " ok";
    case ChannelResult.Failure f -> f.channel() + " failed: " + f.error();
};
```

## 코틀린과 나란히 놓고 보기

코틀린으로 같은 것을 쓰면 이렇게 된다:

```kotlin
sealed interface ChannelResult {
    val channel: String
    val attempts: Int

    data class Success(override val channel: String, override val attempts: Int) : ChannelResult
    data class Failure(override val channel: String, override val attempts: Int,
                       val error: String) : ChannelResult
}
```

겉모양은 거의 같지만 결이 다른 지점들이 실무에서 체감된다.

**봉인 방식 — 명시 vs 암묵.** 자바는 `permits` 로 허용 목록을 선언한다(같은 소스 파일에 자식이 있으면 생략 가능, [JEP 409](https://openjdk.org/jeps/409)). 허용 자식은 `final`/`sealed`/`non-sealed` 중 하나를 반드시 골라야 하고, `non-sealed` 라는 공식 탈출구가 있다. 코틀린은 `permits` 가 없다 — [공식 문서](https://kotlinlang.org/docs/sealed-classes.html)의 규칙대로 **같은 모듈·같은 패키지 안의 직접 자식만** 허용되며, 직접 자식이 `open` 이면 그 아래로는 자유롭게 열린다. 자바 쪽이 더 장황하지만 계층의 의도가 코드에 남고, 코틀린 쪽이 더 간결하지만 "어디까지 닫혀 있나"를 알려면 규칙을 알아야 한다.

**전수 검사의 연차.** 코틀린의 `when` 은 sealed 타입에 대한 빠짐없음 검사를 언어 명세 차원에서 오래전부터 지원해 왔다([Kotlin 언어 명세](https://kotlinlang.org/spec/pdf/sections/inheritance.pdf) 5.1.2). 자바는 위에서 본 대로 21까지 기다려야 했다. "sealed 를 왜 쓰는데?"에 대한 체감 답이 코틀린 개발자에게 훨씬 일찍 왔던 이유다.

**record vs data class — 불변의 강도와 copy().** record 의 컴포넌트는 언어가 final 로 못 박는다(얕은 불변). data class 는 `var` 프로퍼티를 허용하므로 불변은 관례이지 강제가 아니다. 대신 data class 는 [`copy()` 를 자동 생성](https://kotlinlang.org/docs/data-classes.html)해 "일부만 바꾼 새 값"을 한 줄로 만든다 — 불변 모델링에서 가장 자주 쓰는 동작이다. record 에는 이것이 없어서 전 컴포넌트를 나열한 생성자 호출을 손으로 써야 하고, OpenJDK 도 이 불편을 인지해 파생 레코드 생성([JEP 468](https://openjdk.org/jeps/468))을 논의해 왔다. 반대로 코틀린의 `copy()` 는 얕은 복사이고 생성자 검증을 우회할 수 있다는 점이 종종 함정으로 지적된다.

**분해(destructuring).** 코틀린은 `componentN()` 기반 구조 분해(`val (ch, n) = success`)를 처음부터 제공했다. 자바는 21의 record pattern 으로 `case Success(String ch, int n)` 처럼 **패턴 매칭 안에서의** 분해가 생겼다 — 위치가 다를 뿐 지향점은 같다.

**교차 제약.** 코틀린 data class 는 `sealed`/`open`/`abstract` 가 될 수 없다(잎 노드 전용) — 자바 record 가 암묵적으로 final 인 것과 정확히 대응한다. 두 언어 모두 "합(sum) 타입은 sealed 로, 곱(product) 타입은 record/data class 로, 잎은 닫는다"는 같은 문법 구조에 도달했다.

## 정리

- **record 의 실사용**은 DTO·설정 바인딩·값 객체·검증 딸린 값 — "경계를 넘는 모든 데이터"다. 내 코드베이스 기준 680곳. JPA 엔티티만 예외.
- **sealed 의 실사용**은 결과 타입과 닫힌 스펙 모델링 — 수는 적지만 설계의 급소에 놓인다. 완전한 보상(전수 switch)은 자바 21부터.
- **코틀린과의 차이**는 봉인의 명시성(permits vs 모듈·패키지 규칙), 전수 검사 도입 시기, `copy()` 유무, 불변 강제 수준으로 요약된다. 문법은 달라도 두 언어는 같은 결론 — sealed 로 합 타입, record/data class 로 곱 타입 — 에 수렴했다.

자바 17에서 이 둘을 "편의 문법"으로만 쓰고 있다면, 결과 타입 하나를 sealed interface + record 로 바꿔 보는 것을 권한다. 컴파일러가 도메인의 빈틈을 대신 세어 주기 시작하는 경험은 되돌리기 어렵다.

## References

- OpenJDK, [JEP 395: Records](https://openjdk.org/jeps/395) (JDK 16 정식)
- OpenJDK, [JEP 409: Sealed Classes](https://openjdk.org/jeps/409) (JDK 17 정식)
- OpenJDK, [JEP 406: Pattern Matching for switch (Preview)](https://openjdk.org/jeps/406) (JDK 17 preview)
- OpenJDK, [JEP 440: Record Patterns](https://openjdk.org/jeps/440) / [JEP 441: Pattern Matching for switch](https://openjdk.org/jeps/441) (JDK 21 정식)
- OpenJDK, [JEP 468: Derived Record Creation (Preview)](https://openjdk.org/jeps/468)
- Oracle, [Sealed Classes and Interfaces — Java SE 17 Language Updates](https://docs.oracle.com/en/java/javase/17/language/sealed-classes-and-interfaces.html)
- Kotlin 공식 문서, [Sealed classes and interfaces](https://kotlinlang.org/docs/sealed-classes.html)
- Kotlin 공식 문서, [Data classes](https://kotlinlang.org/docs/data-classes.html)
- Kotlin 언어 명세, [Inheritance — Sealed classes and interfaces](https://kotlinlang.org/spec/pdf/sections/inheritance.pdf)
- Spring Boot 공식 문서, [Externalized Configuration — Constructor binding](https://docs.spring.io/spring-boot/reference/features/external-config.html)

*본문의 record 개수(680)와 코드 예시는 필자가 운영하는 정산 시스템 코드베이스에서 직접 집계·발췌한 것이다.*
