---
layout: post
title: "자바 클래스 모델의 진화 — 인터페이스 default/static/private 메서드, record, sealed"
date: 2026-10-12 00:13:42 +0900
categories: [java]
tags: [java, interface, default-method, record, sealed, algebraic-data-type, jpa, spring-boot]
---

자바·코틀린 20편 시리즈의 **자바 3편(J3)** 이다. 자바의 "타입을 선언하는 방법" 은 Java 8 이후 크게 세 번 바뀌었다.

| 단계 | 기능 | 도입 | 바꾼 것 |
|---|---|---|---|
| 1 | 인터페이스 default·static 메서드 | Java 8 | 인터페이스가 구현을 가질 수 있게 됨 |
| 1' | 인터페이스 private 메서드 | Java 9 | default 메서드 간 코드 공유 |
| 2 | record | Java 16 | "데이터 운반자" 를 한 줄로 |
| 3 | sealed 클래스·인터페이스 | Java 17 | 상속 가능한 하위 타입을 닫음 |

이 글은 각 기능을 (1) 무엇인가 (2) 코드 (3) 실무 사용사례 (4) 함정 순으로 정리한다. sealed + record 를 switch 로 분해하는 **패턴 매칭** 쪽은 [J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/) 에서 이어서 다룬다. 같은 문제를 코틀린이 어떻게 풀었는지(`data class`, `sealed class`, 기본 `final`)는 [K3](https://myoungsoo7.github.io/2026/10/12/kotlin-classes-data-sealed-object-value/) 를 같이 보면 좋다.

---

## 1. 인터페이스의 진화

### 1.1 Java 7 까지의 인터페이스

Java 7 의 인터페이스는 추상 메서드와 상수만 가질 수 있었다. 그래서 "인터페이스 + 그걸 돕는 유틸 클래스" 쌍이 관용구였다(`Collection` / `Collections`, `Path` / `Paths`).

문제는 **진화**였다. 람다와 스트림을 넣으려면 `Collection` 에 `stream()`, `Iterable` 에 `forEach()` 를 추가해야 했는데, 추상 메서드를 추가하면 세상의 모든 구현체가 깨진다. Java 8 람다 JEP 은 이를 위해 "virtual extension methods will allow interfaces to be evolved in a source and binary compatible fashion" 이라고 밝혔다([JEP 126](https://openjdk.org/jeps/126)). 호환성 관점은 [J1](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/) 참고.

### 1.2 default 메서드 (Java 8)

**무엇인가.** JLS 정의: "A default method is a method that is declared in an interface with the `default` modifier; its body is always represented by a block."([JLS SE 8 §9.4](https://docs.oracle.com/javase/specs/jls/se8/html/jls-9.html))

```java
public interface DiscountPolicy {
    long discount(long price);

    // 구현을 가진 인스턴스 메서드. 구현 클래스는 그대로 상속하거나 재정의한다
    default long apply(long price) {
        long d = discount(price);
        return Math.max(0, price - d);
    }
}

public class FixedDiscount implements DiscountPolicy {
    private final long amount;
    public FixedDiscount(long amount) { this.amount = amount; }
    @Override public long discount(long price) { return amount; }
    // apply() 는 상속
}
```

**실무 사용사례.**

1. **기존 인터페이스에 기능 추가** — 사내 공통 모듈의 인터페이스에 새 메서드를 넣을 때, default 로 넣으면 모든 구현 팀이 즉시 재컴파일하지 않아도 된다.
2. **템플릿 메서드 대체** — 추상 클래스 없이 "골격 + 확장 지점" 을 표현.
3. **스프링 설정 콜백** — `WebMvcConfigurer` 같은 스프링 인터페이스는 메서드가 default 로 비어 있어, 필요한 것만 재정의한다.

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {   // 필요한 것만 재정의
        registry.addMapping("/api/**").allowedOrigins("https://example.com");
    }
}
```

**함정 1 — 다이아몬드 충돌.** 두 상위 인터페이스가 같은 시그니처의 default 메서드를 주면 컴파일 에러다. JLS: "If an interface I inherits a `default` method whose signature is override-equivalent with another method inherited by I, then a compile-time error occurs."([JLS §9.4.1.3](https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html)) 해결은 직접 재정의하고, 필요하면 `X.super.m()` 으로 특정 부모를 고른다.

```java
interface Audited  { default String label() { return "audited"; } }
interface Cached   { default String label() { return "cached"; } }

class Repo implements Audited, Cached {
    @Override
    public String label() {
        return Audited.super.label() + "+" + Cached.super.label();
    }
}
```

**함정 2 — `Object` 메서드는 default 로 못 만든다.** JLS 는 default 메서드가 `Object` 의 public 메서드를 재정의하는 것을 금지한다([JLS §9.4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html)). `default boolean equals(Object o)` 는 컴파일 에러다. 인터페이스로 equals 계약을 강제할 수는 없다.

**함정 3 — 상태가 없다.** 인터페이스는 인스턴스 필드를 가질 수 없다. default 메서드가 상태를 필요로 하기 시작하면 추상 클래스나 합성(composition)으로 가는 것이 맞다. default 메서드를 "다중 상속 도구" 로 남용하면 어디서 동작이 오는지 추적하기 어려워진다.

**함정 4 — 호환성은 "대부분" 이다.** default 메서드 추가는 바이너리 호환이지만 "may cause an `IncompatibleClassChangeError` if a pre-existing binary attempts to invoke the method" 라는 단서가 붙는다([JLS §13.5.7](https://docs.oracle.com/javase/specs/jls/se21/html/jls-13.html)). 위 다이아몬드 상황이 재컴파일 없이 런타임에 생기는 경우다.

### 1.3 static 메서드 (Java 8)

**무엇인가.** 인터페이스에 정적 메서드를 선언할 수 있다. JLS SE 8: "An interface can declare `static` methods, which are invoked without reference to a particular object." 그리고 "An interface does not inherit `static` methods from its superinterfaces."([JLS SE 8 §9.4](https://docs.oracle.com/javase/specs/jls/se8/html/jls-9.html))

```java
public interface Money {
    long amount();
    String currency();

    static Money krw(long amount) {             // 팩토리를 인터페이스에 둔다
        return new SimpleMoney(amount, "KRW");
    }
}

record SimpleMoney(long amount, String currency) implements Money {}

Money m = Money.krw(1000);
// SimpleMoney.krw(1000);   // 컴파일 에러: 구현 클래스에 상속되지 않는다
```

**실무 사용사례.** JDK 자체가 이 패턴을 쓴다: `List.of(...)`(Java 9), `Comparator.comparing(...)`. 별도의 `Xxxs` 유틸 클래스 없이 인터페이스 이름으로 팩토리를 찾을 수 있다.

**함정.** 정적 메서드는 상속되지 않으므로 하위 인터페이스 이름으로 호출할 수 없다. 클래스의 static 메서드와 직관이 다르니 주의한다.

### 1.4 private 메서드 (Java 9)

**무엇인가.** default/static 메서드끼리 공통 코드를 공유하기 위한 private 메서드. Java 8 에서 미뤄졌다가 Java 9 의 [JEP 213](https://openjdk.org/jeps/213) 으로 들어왔다. private 메서드는 `abstract` 나 `default` 와 함께 쓸 수 없고 `static` 은 가능하다([JLS §9.4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html)).

```java
public interface Retryable {
    <T> T call(Supplier<T> action);

    default <T> T callWithRetry(Supplier<T> action, int max) {
        return loop(action, max, 0L);
    }

    default <T> T callWithBackoff(Supplier<T> action, int max, long backoffMs) {
        return loop(action, max, backoffMs);
    }

    private <T> T loop(Supplier<T> action, int max, long backoffMs) {  // 공유 로직
        RuntimeException last = null;
        for (int i = 0; i < max; i++) {
            try {
                return call(action);
            } catch (RuntimeException e) {
                last = e;
                sleepQuietly(backoffMs);
            }
        }
        throw last;
    }

    private static void sleepQuietly(long ms) {
        if (ms <= 0) return;
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

**함정.** `max` 가 0 이면 `last` 가 null 인 채로 `throw last;` 에서 NPE 가 난다 — 위 코드는 설명용이고, 실제로는 `max >= 1` 검증을 넣는다. 그리고 private 메서드가 많아지면 인터페이스가 사실상 추상 클래스가 되고 있다는 신호다.

### 1.5 인터페이스 메서드 종류 요약

| 종류 | 키워드 | 구현 | 상속 | 도입 |
|---|---|---|---|---|
| 추상 | (생략 가능 `abstract`) | 없음 | O | 1.0 |
| default | `default` | 있음 | O | 8 |
| static | `static` | 있음 | X (인터페이스 이름으로만 호출) | 8 |
| private (인스턴스/정적) | `private` | 있음 | X | 9 |

JLS 는 `abstract`, `default`, `static` 중 둘 이상을 같이 쓰면 컴파일 에러라고 정한다([JLS §9.4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html)).

---

## 2. record (Java 16)

### 2.1 무엇인가

[JEP 395](https://openjdk.org/jeps/395) 로 Java 16 에 정식 도입됐다. `java.lang.Record` Javadoc 은 record 를 "shallowly immutable, transparent carrier for a fixed set of values, called the record components" 라고 설명한다([Record](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Record.html)).

```java
public record Point(int x, int y) {}
```

이 한 줄로 컴파일러가 만들어 주는 것:

- `private final int x, y;` 필드
- 모든 컴포넌트를 받는 **정규(canonical) 생성자**
- 접근자 `x()`, `y()` — `getX()` 가 **아니다**
- 컴포넌트 기반 `equals`, `hashCode`, `toString`

`equals` 는 같은 record 클래스이고 모든 컴포넌트가 같을 때 `true` 다. 참조 타입 컴포넌트는 `Objects.equals`, 원시 타입 컴포넌트는 해당 래퍼의 `compare` 로 비교한다([Record.equals](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Record.html)). `toString` 의 정확한 형식은 바뀔 수 있으니 파싱하지 말라고 Javadoc 이 경고한다.

### 2.2 JEP 395 가 정한 제약

| 제약 | 이유 |
|---|---|
| 암묵적으로 `final`, `abstract` 불가 | 상속으로 "투명성" 이 깨지는 것을 막음 |
| 다른 클래스를 `extends` 불가 (부모는 항상 `java.lang.Record`) | 상태가 컴포넌트로만 정의되도록 |
| 컴포넌트 필드는 `final` | 얕은 불변 |
| 추가 **인스턴스 필드**·인스턴스 초기화 블록 불가 | 상태 = 컴포넌트 |
| 인터페이스 구현 가능, static 필드·메서드 가능 | 행위와 팩토리는 허용 |

JEP 395 는 같이 들어온 변화로 **로컬 record**(메서드 안 선언, 암묵적 static 이라 바깥 지역 변수를 캡처하지 않음)와, **내부(inner) 클래스가 static 멤버를 선언할 수 있게** 한 완화도 명시한다.

### 2.3 컴팩트 생성자 — 검증과 정규화

```java
public record Email(String value) {
    public Email {                                   // 파라미터 목록 없는 컴팩트 생성자
        Objects.requireNonNull(value, "email");
        value = value.trim().toLowerCase();          // 파라미터 재할당 → 필드에 반영
        if (!value.contains("@")) throw new IllegalArgumentException("invalid: " + value);
    }                                                // 필드 대입은 컴파일러가 마지막에 넣는다
}
```

```java
public record Range(int from, int to) {
    public Range {
        if (from > to) throw new IllegalArgumentException(from + " > " + to);
    }
    public static Range of(int from, int to) { return new Range(from, to); }  // static 팩토리
    public int length() { return to - from; }                                  // 파생 값 메서드
    public Range shift(int d) { return new Range(from + d, to + d); }          // "withers" 는 새 객체
}
```

### 2.4 실무 사용사례

**① DTO / API 요청·응답**

```java
public record CreateOrderRequest(
        @NotNull Long productId,
        @Positive int quantity,
        @NotBlank String address) {}

@PostMapping("/orders")
public OrderResponse create(@Valid @RequestBody CreateOrderRequest req) { ... }
```

**② 스프링부트 `@ConfigurationProperties`** — 스프링부트 레퍼런스는 "Constructor binding can be used with records" 이고 "Unless your record has multiple constructors, there is no need to use `@ConstructorBinding`" 이라고 안내한다. 기본값은 `@DefaultValue` 를 record 컴포넌트에 붙인다([Spring Boot Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html)).

```java
@ConfigurationProperties("payment.pg")
public record PgProperties(
        String baseUrl,
        @DefaultValue("3s") Duration timeout,
        @DefaultValue("3") int maxRetries) {}

@SpringBootApplication
@ConfigurationPropertiesScan
public class App { ... }
```

레퍼런스는 생성자 바인딩 클래스가 `@EnableConfigurationProperties` 나 프로퍼티 스캔으로 활성화돼야 하며, `@Component` 나 `@Bean` 으로 만든 빈에는 생성자 바인딩을 쓸 수 없다고 명시한다.

**③ 메서드 내부의 중간 결과 — 로컬 record**

```java
List<String> topSellers(List<Order> orders) {
    record Sales(String seller, long total) {}               // 로컬 record
    return orders.stream()
            .collect(Collectors.groupingBy(Order::seller, Collectors.summingLong(Order::amount)))
            .entrySet().stream()
            .map(e -> new Sales(e.getKey(), e.getValue()))
            .sorted(Comparator.comparingLong(Sales::total).reversed())
            .limit(10)
            .map(Sales::seller)
            .toList();
}
```

`Map.Entry<String, Long>` 를 이리저리 넘기는 대신 의미 있는 이름이 생긴다.

**④ 복합 키** — `equals/hashCode` 가 자동이므로 `Map` 키로 안전하다.

```java
record CacheKey(String tenant, long userId) {}
Map<CacheKey, Profile> cache = new ConcurrentHashMap<>();
```

### 2.5 함정

**함정 1 — "얕은" 불변이다.**

```java
record Team(String name, List<String> members) {}

var list = new ArrayList<>(List.of("a"));
var t = new Team("x", list);
list.add("b");                    // t.members() 도 바뀐다
t.members().add("c");             // 이것도 된다
```

방어적 복사를 컴팩트 생성자에서 한다.

```java
record Team(String name, List<String> members) {
    Team { members = List.copyOf(members); }   // 불변 복사본 (null 요소는 NPE)
}
```

`List.copyOf` 는 Java 10, 결과는 수정 불가이고 null 요소를 허용하지 않는다([List](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html)).

**함정 2 — 배열 컴포넌트.** `record Blob(byte[] data)` 의 `equals` 는 배열을 `Objects.equals` 로, 즉 **참조**로 비교한다. 내용이 같은 두 Blob 이 다르다고 나온다. 배열 대신 `List` 나 별도 값 타입을 쓰거나 `equals/hashCode` 를 직접 재정의한다.

**함정 3 — JPA 엔티티로 쓸 수 없다.** Jakarta Persistence 명세는 엔티티 클래스에 "must have a no-arg constructor", "must not be final. No methods or persistent instance variables of the entity class may be final" 을 요구한다([Jakarta Persistence 3.1 §2.1](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html)). record 는 final 이고 필드도 final 이라 정면으로 충돌한다. 3.2 명세는 아예 "An enum, record, or interface may not be designated as an entity" 라고 적는다. 대신 3.2 부터는 **record 를 embeddable 클래스와 기본 키 클래스로 쓸 수 있게** 됐다([Jakarta Persistence 3.2](https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html)).

| 용도 | record 사용 |
|---|---|
| `@Entity` | 불가 |
| `@Embeddable` | Jakarta Persistence 3.2 부터 가능 |
| `@IdClass`/`@EmbeddedId` 기본 키 클래스 | 3.2 부터 record 가능 |
| 조회 전용 DTO 프로젝션 | 가능 (JPQL 생성자 표현식 등) |

**함정 4 — 접근자 이름.** `x()` 이지 `getX()` 가 아니다. JavaBeans 규약(getter)을 가정하는 오래된 라이브러리·템플릿 엔진은 record 를 못 읽을 수 있다. 쓰는 라이브러리의 record 지원 여부를 확인한다.

**함정 5 — 도메인 엔티티를 record 로 만들지 않는다.** record 는 "값" 이다. 식별자가 있고 상태가 바뀌는 엔티티(주문, 계좌)는 일반 클래스가 맞다. record 는 값 객체(Money, Email), DTO, 이벤트, 키에 쓴다.

---

## 3. sealed 클래스·인터페이스 (Java 17)

### 3.1 무엇인가

[JEP 409](https://openjdk.org/jeps/409) 로 Java 17 에 정식 도입됐다. 클래스·인터페이스 작성자가 **누가 자신을 상속/구현할 수 있는지** 명시한다.

```java
public sealed interface PaymentResult
        permits PaymentResult.Approved, PaymentResult.Declined, PaymentResult.Pending {

    record Approved(String txId, long amount) implements PaymentResult {}
    record Declined(String code, String reason) implements PaymentResult {}
    record Pending(String txId) implements PaymentResult {}
}
```

### 3.2 규칙

JEP 409 가 정한 규칙:

1. **위치** — 허용된 하위 클래스는 sealed 클래스와 같은 모듈에 있어야 하고, 이름 없는 모듈(일반적인 클래스패스 앱)이면 **같은 패키지**에 있어야 한다.
2. **수식어** — 허용된 하위 클래스는 `final`, `sealed`, `non-sealed` 중 **정확히 하나**를 선언해야 한다. record 는 암묵적 final 이라 그대로 쓸 수 있다.
3. **`permits` 생략** — sealed 클래스와 하위 클래스들이 같은 소스 파일에 있으면 `permits` 를 생략할 수 있고 컴파일러가 추론한다.
4. **이름 필요** — `permits` 대상은 정규 이름(canonical name)이 있어야 하므로 익명·로컬 클래스는 안 된다.
5. **리플렉션** — `Class.isSealed()`, `Class.getPermittedSubclasses()` 가 추가됐다.

```java
public sealed abstract class Shape permits Circle, Polygon, Freeform {}

public final class Circle extends Shape { ... }                 // 더 이상 확장 불가

public sealed class Polygon extends Shape permits Triangle, Rect {}  // 다시 봉인
public final class Triangle extends Polygon { ... }
public final class Rect extends Polygon { ... }

public non-sealed class Freeform extends Shape { ... }          // 여기서부터 다시 열림
```

### 3.3 왜 필요한가 — 합 타입

JEP 409 는 record 와 sealed 의 조합을 대수적 데이터 타입(ADT)으로 설명한다. record 는 **곱 타입**(필드들의 조합), sealed 는 **합 타입**(여러 경우 중 하나)이다.

이전에는 "결과는 성공/실패/보류 중 하나" 를 표현할 방법이 enum(데이터를 못 실음)이나 열린 상속(누가 하위 타입을 추가할지 모름)뿐이었다. sealed 는 그 중간 — **경우의 수는 닫혀 있고, 각 경우는 서로 다른 데이터를 가진다** — 를 표현한다.

### 3.4 실무 사용사례

**① 외부 연동 결과 모델링**

```java
public PaymentResult pay(PaymentRequest req) {
    PgResponse res = pgClient.call(req);
    return switch (res.status()) {
        case "0000" -> new PaymentResult.Approved(res.txId(), req.amount());
        case "9999" -> new PaymentResult.Pending(res.txId());
        default     -> new PaymentResult.Declined(res.status(), res.message());
    };
}
```

호출하는 쪽은 Java 21 의 switch 패턴 매칭([JEP 441](https://openjdk.org/jeps/441))과 record 패턴([JEP 440](https://openjdk.org/jeps/440))으로 처리한다.

```java
String toMessage(PaymentResult r) {
    return switch (r) {                                   // default 없음
        case PaymentResult.Approved(var txId, var amount) -> "승인 " + txId + " / " + amount;
        case PaymentResult.Declined(var code, var reason) -> "거절 [" + code + "] " + reason;
        case PaymentResult.Pending(var txId)              -> "처리 중 " + txId;
    };
}
```

여기서 sealed 의 진가가 나온다. 나중에 `Canceled` 를 `permits` 에 추가하면 **`default` 없는 모든 switch 가 컴파일 에러** 가 난다. "새 상태를 추가했는데 한 군데 처리를 빠뜨렸다" 는 운영 사고를 컴파일러가 막는다. 패턴 매칭의 망라성(exhaustiveness) 규칙은 [J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/) 에서 자세히 본다.

**② 도메인 이벤트**

```java
public sealed interface OrderEvent permits OrderPlaced, OrderPaid, OrderShipped, OrderCanceled {
    String orderId();
}
public record OrderPlaced(String orderId, List<Line> lines) implements OrderEvent {}
public record OrderPaid(String orderId, String txId) implements OrderEvent {}
public record OrderShipped(String orderId, String trackingNo) implements OrderEvent {}
public record OrderCanceled(String orderId, String reason) implements OrderEvent {}
```

**③ 라이브러리 API 의 확장 통제** — 공개 인터페이스를 사용자가 구현하지 못하게 하고 싶을 때(구현을 추가하면 호환성 책임이 생기므로). 예전엔 "package-private 생성자를 가진 추상 클래스" 같은 우회를 썼다.

### 3.5 함정

**함정 1 — 패키지 제약.** 이름 없는 모듈에서는 하위 클래스가 같은 패키지여야 한다. "도메인 패키지별로 이벤트를 나눴더니 sealed 가 안 된다" 는 흔한 첫 충돌이다. 같은 패키지로 모으거나 JPMS 모듈을 쓴다.

**함정 2 — `default` 로 망라성을 버리지 않는다.**

```java
// 나쁜 예: default 가 있으면 새 케이스 추가 시 컴파일러가 아무 말도 안 한다
return switch (r) {
    case PaymentResult.Approved a -> "승인";
    default -> "기타";
};
```

sealed 계층을 switch 할 때는 `default` 를 쓰지 않는 것이 원칙이다.

**함정 3 — `non-sealed` 는 구멍이다.** `non-sealed` 하위 타입 아래로는 누구나 확장할 수 있다. switch 는 여전히 망라적이지만(그 타입으로 한 번에 받으므로) 그 안쪽은 모른다. 의도적으로 열어둘 확장 지점에만 쓴다.

**함정 4 — JSON 다형성 역직렬화.** sealed 인터페이스로 받는 API 요청은 Jackson 에서 `@JsonTypeInfo`/`@JsonSubTypes` 같은 타입 판별 정보를 따로 설정해야 한다. sealed 선언만으로 역직렬화 대상 타입이 정해지지는 않는다고 생각하고 설정을 명시한다.

**함정 5 — 프록시와 final.** 스프링 AOP(CGLIB)는 하위 클래스를 만들어 프록시를 거는데, record 와 final 클래스는 상속할 수 없다. sealed 계층의 record 는 **값**으로 쓰고 빈(bean)으로 등록하지 않는다. 프록시 원리는 [J9](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 참고. 코틀린이 기본 final 이라 생기는 같은 문제는 [K9](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) 에서 다룬다.

---

## 4. 무엇을 언제 쓰나 — 선택 가이드

| 상황 | 선택 |
|---|---|
| 여러 구현이 공유할 계약 + 일부 공통 동작 | 인터페이스 + default 메서드 |
| 공통 동작이 **상태**를 필요로 함 | 추상 클래스 또는 합성 |
| 인터페이스 관련 팩토리 | 인터페이스 static 메서드 |
| 불변 값·DTO·이벤트·키 | record |
| 식별자 있고 상태가 변하는 엔티티 / JPA `@Entity` | 일반 클래스 |
| 경우의 수가 닫힌 결과·상태·이벤트 | sealed + record |
| 경우는 닫혀 있고 데이터가 없음 | enum |
| 사용자 확장을 허용해야 하는 플러그인 지점 | 일반 인터페이스 (또는 `non-sealed`) |

### 자바와 코틀린 대응표

| 자바 | 코틀린 | 차이 |
|---|---|---|
| `record Point(int x, int y)` | `data class Point(val x: Int, val y: Int)` | 코틀린은 `copy()`·`componentN()` 제공, 상속(open 부모)도 가능 |
| `sealed interface ... permits` | `sealed interface` / `sealed class` | 코틀린은 `permits` 절 없이 하위 타입 위치 규칙으로 닫는다 |
| 클래스 기본 open, `final` 명시 | 기본 final, `open` 명시 | 스프링 프록시 이슈의 근원 |
| default 메서드 | 인터페이스 메서드 본문 | 자바에서 호출될 때의 바이트코드 형태는 코틀린 버전·컴파일 옵션에 따라 다르다 (K3 참고) |

코틀린 쪽 세부와 버전별 차이는 [K3](https://myoungsoo7.github.io/2026/10/12/kotlin-classes-data-sealed-object-value/) 에서 공식 문서 기준으로 정리한다.

---

## References

- JEP 126: Lambda Expressions & Virtual Extension Methods — https://openjdk.org/jeps/126
- JEP 213: Milling Project Coin — https://openjdk.org/jeps/213
- JEP 395: Records — https://openjdk.org/jeps/395
- JEP 409: Sealed Classes — https://openjdk.org/jeps/409
- JEP 440: Record Patterns — https://openjdk.org/jeps/440
- JEP 441: Pattern Matching for switch — https://openjdk.org/jeps/441
- JLS SE 8, Chapter 9 Interfaces — https://docs.oracle.com/javase/specs/jls/se8/html/jls-9.html
- JLS SE 21, Chapter 9 Interfaces (§9.4, §9.4.1.3) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html
- JLS SE 21, Chapter 13 Binary Compatibility (§13.5.7) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-13.html
- `java.lang.Record` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Record.html
- `java.util.List` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html
- Spring Boot Reference, Externalized Configuration — https://docs.spring.io/spring-boot/reference/features/external-config.html
- Jakarta Persistence 3.1 Specification — https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html
- Jakarta Persistence 3.2 Specification — https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/) ← 지금 글
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
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
