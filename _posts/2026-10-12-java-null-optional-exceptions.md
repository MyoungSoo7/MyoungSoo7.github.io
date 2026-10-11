---
layout: post
title: "자바의 null 과 예외 — Optional 의 올바른 용도, checked/unchecked 예외, try-with-resources"
date: 2026-10-12 00:15:42 +0900
categories: [java]
tags: [java, null, optional, exception, checked-exception, try-with-resources, spring-transaction, npe]
---

자바·코틀린 20편 시리즈의 **자바 5편(J5)** 이다. "값이 없을 때" 와 "일이 잘못됐을 때" 를 자바가 어떻게 표현하는지 다룬다.

1. **null** — 자바 타입 시스템의 가장 큰 구멍과 방어 기법
2. **Optional** — 무엇을 위해 만들어졌고, 무엇에 쓰면 안 되는가
3. **예외 계층** — checked vs unchecked, 설계 의도와 실무 선택
4. **try-with-resources** — 자원 해제와 억제된 예외
5. **스프링과 예외** — `@Transactional` 롤백 규칙과 예외 변환

짝이 되는 코틀린 글은 [K2 널 안전: ?, ?:, !!, 플랫폼 타입](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/) 이다. 코틀린이 null 을 타입으로, 예외를 "전부 unchecked" 로 다룬 이유를 이 글과 비교해서 보면 자바의 선택이 더 선명해진다.

---

## 1. null

### 1.1 무엇인가

자바의 모든 참조 타입 변수는 `null` 을 가질 수 있고, 타입 시스템은 "null 일 수 있는 `String`" 과 "null 일 수 없는 `String`" 을 구분하지 않는다. 그래서 null 관련 오류는 전부 **런타임** `NullPointerException` 으로 나타난다([J1 §6.2](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/)).

null 이 숨어 들어오는 대표 경로:

| 경로 | 예 |
|---|---|
| 조회 결과 없음 | `Map.get`, JPA `find`, 외부 API 응답 필드 |
| 초기화 안 된 필드 | 기본 생성자 + setter 로 만든 객체 |
| 언박싱 | `int n = map.get(k);` ([J2 §1.4](https://myoungsoo7.github.io/2026/10/12/java-type-system-generics-erasure-pecs/)) |
| 체이닝 | `order.getUser().getAddress().getZip()` |

### 1.2 Helpful NullPointerException

JDK 14 의 [JEP 358](https://openjdk.org/jeps/358) 은 NPE 메시지에 **무엇이 null 이었는지** 를 넣는다. JEP 의 예시로, `a.b.c.i = 99;` 에서 `a.b` 가 null 이면:

```text
Cannot read field "c" because "a.b" is null
```

JDK 14 에서는 `-XX:+ShowCodeDetailsInExceptionMessages` 를 켜야 했고, JDK 15 에서 기본값이 켜짐으로 바뀌었다([JDK-8233014](https://bugs.openjdk.org/browse/JDK-8233014)). JDK 17·21 서비스라면 별도 설정 없이 이 메시지를 받는다.

**실무 사용사례**: 체이닝 한 줄(`order.getUser().getAddress().getZip()`)에서 NPE 가 났을 때, 예전엔 줄 번호만으로는 어느 단계가 null 인지 몰랐다. 이제 메시지의 `because ...` 부분이 null 을 만든 식을 소스 형태로 재구성해 보여준다. JEP 358 의 예로, 메서드 호출 결과를 거친 경우 `Cannot store to int array because "Test.a().b[i]" is null` 처럼 어느 호출의 결과가 null 이었는지가 드러난다. 로그 수집 시 **예외 메시지를 자르지 말 것** — 핵심 정보가 메시지에 있다.

### 1.3 방어 기법

```java
// 1) 생성 시점에 막는다 (fail-fast)
public Order(String id, User user) {
    this.id = Objects.requireNonNull(id, "id");
    this.user = Objects.requireNonNull(user, "user");
}

// record 라면 컴팩트 생성자에서
public record Address(String zip, String line1) {
    public Address {
        Objects.requireNonNull(zip, "zip");
        Objects.requireNonNull(line1, "line1");
    }
}

// 2) 기본값 — requireNonNullElse 는 Java 9
String nickname = Objects.requireNonNullElse(user.nickname(), "anonymous");

// 3) 빈 컬렉션을 반환한다 — null 컬렉션을 반환하지 않는다
public List<Coupon> coupons() {
    return coupons == null ? List.of() : List.copyOf(coupons);
}

// 4) 문자열 비교는 상수 쪽에서
if ("PAID".equals(status)) { ... }         // status 가 null 이어도 안전
```

`Objects.requireNonNullElse` 는 Java 9 에 추가됐다([Objects](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Objects.html)).

### 1.4 함정

- **`List.of`/`Map.of` 는 null 을 거부한다.** 요소가 null 이면 `NullPointerException` 이다([List](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html)). `Arrays.asList` 나 `new ArrayList<>()` 에서 바꿀 때 주의.
- **애노테이션은 강제력이 없다.** `@Nullable`/`@NonNull` 은 정적 분석 도구·IDE·코틀린 컴파일러가 읽는 **힌트**다. javac 는 이를 근거로 컴파일을 막지 않는다. 다만 코틀린에서 자바 API 를 부를 때 이 애노테이션이 플랫폼 타입을 `String?`/`String` 으로 바꿔주므로, 코틀린과 섞어 쓰는 프로젝트에서는 실질적 효과가 크다([K2](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/)).

---

## 2. Optional

### 2.1 무엇인가 — 공식 용도

`java.util.Optional` 은 Java 8 에 추가됐다. Javadoc 의 API Note 가 용도를 명확히 제한한다.

> "`Optional` is primarily intended for use as a method return type where there is a clear need to represent "no result," and where using `null` is likely to cause errors. A variable whose type is `Optional` should never itself be `null`; it should always point to an `Optional` instance."
> — [Optional Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html)

즉 **"결과가 없을 수 있는 메서드의 반환 타입"** 이 주 용도다. 필드·파라미터·컬렉션 원소는 원래 의도가 아니다.

### 2.2 API 와 도입 버전

| 메서드 | 버전 | 용도 |
|---|---|---|
| `of`, `ofNullable`, `empty` | 8 | 생성 |
| `map`, `flatMap`, `filter` | 8 | 변환 |
| `orElse`, `orElseGet`, `orElseThrow(Supplier)` | 8 | 꺼내기 |
| `isPresent`, `ifPresent`, `get` | 8 | 검사·소비 |
| `ifPresentOrElse`, `or`, `stream` | 9 | |
| `orElseThrow()` (인자 없음) | 10 | `get()` 의 명시적 대체 |
| `isEmpty` | 11 | |

(출처: [Optional Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html) 의 `@since`)

### 2.3 코드 예제 — 좋은 사용

```java
public interface UserRepository {
    Optional<User> findByEmail(String email);     // 반환 타입으로 "없을 수 있음" 을 알린다
}

// 1) 없으면 예외 — 서비스 계층의 가장 흔한 패턴
User user = userRepository.findByEmail(email)
        .orElseThrow(() -> new UserNotFoundException(email));

// 2) 변환 체인
String city = userRepository.findByEmail(email)
        .map(User::address)                 // Address 가 null 이면 empty 로
        .map(Address::city)
        .orElse("UNKNOWN");

// 3) 대체 조회 — or (Java 9)
Optional<Price> price = cache.find(sku).or(() -> db.findPrice(sku));

// 4) 있을 때/없을 때 분기 — ifPresentOrElse (Java 9)
userRepository.findByEmail(email).ifPresentOrElse(
        u -> mailer.sendWelcomeBack(u),
        () -> mailer.sendSignupInvite(email));

// 5) Optional 들의 스트림에서 값만 — stream (Java 9)
List<User> found = emails.stream()
        .map(userRepository::findByEmail)
        .flatMap(Optional::stream)
        .toList();
```

**실무 사용사례 — 스프링 데이터.** 스프링 데이터 레퍼런스는 "Repository CRUD methods that return an individual aggregate instances can use `Optional` to indicate the potential absence of a value" 라고 하고, 쿼리 메서드는 래퍼 없이 `null` 로 부재를 표현할 수도 있다고 한다. 또한 컬렉션·스트림을 반환하는 저장소 메서드는 null 이 아니라 빈 결과를 돌려준다고 보장한다([Spring Data — Null Handling](https://docs.spring.io/spring-data/commons/reference/repositories/null-handling.html)). `CrudRepository.findById` 가 `Optional<T>` 를 반환하는 것이 그 예다.

### 2.4 함정과 안티패턴

**① `orElse` 는 항상 평가된다.**

```java
// 나쁜 예: 값이 있어도 createDefault() 가 실행된다 (DB insert 라면 사고)
User u = repo.findById(id).orElse(createDefaultUser());

// 좋은 예: 없을 때만 실행
User u2 = repo.findById(id).orElseGet(this::createDefaultUser);
```

`orElse(x)` 의 `x` 는 메서드 인자이므로 호출 전에 평가된다. 비싼 계산·부수효과가 있으면 `orElseGet` 을 쓴다.

**② `isPresent()` + `get()` 은 null 체크를 Optional 로 옮긴 것뿐이다.**

```java
// 나쁜 예
Optional<User> opt = repo.findById(id);
if (opt.isPresent()) { return opt.get().name(); } else { return "?"; }

// 좋은 예
return repo.findById(id).map(User::name).orElse("?");
```

값을 반드시 꺼내야 한다면 `get()` 보다 의도가 드러나는 `orElseThrow()`(Java 10)를 쓴다.

**③ Optional 을 반환하는 메서드가 null 을 반환한다.** Javadoc 이 "should never itself be `null`" 이라고 못 박은 바로 그 경우다. 호출자는 Optional 이니 안심하고 `.map` 을 부르다 NPE 를 맞는다.

```java
public Optional<Coupon> findCoupon(String code) {
    if (code == null) return null;          // 절대 금지
    return Optional.empty();                // 이렇게
}
```

**④ 필드·파라미터에 Optional.**

```java
// 나쁜 예
public class Member { private Optional<String> nickname; }          // 필드
public void update(Optional<String> nickname) { ... }               // 파라미터
```

- 필드: Javadoc 이 말하는 "주 용도" 밖이고, `Optional` 클래스 선언에는 `Serializable` 이 없다. JPA 엔티티 필드나 직렬화 대상 객체에 넣으면 매핑·직렬화가 꼬인다. 필드는 nullable 로 두고 **getter 가 Optional 을 반환**하게 한다.
- 파라미터: 호출자가 `Optional.empty()`, `Optional.of(x)`, 심지어 `null` 까지 넘길 수 있어 경우의 수가 늘어난다. 오버로드나 nullable 파라미터 + 문서화가 낫다.

```java
public class Member {
    private String nickname;                                         // nullable 필드
    public Optional<String> nickname() { return Optional.ofNullable(nickname); }
}
```

**⑤ 컬렉션을 Optional 로 감싸지 않는다.** `Optional<List<X>>` 대신 빈 리스트를 반환한다. "없음" 과 "비어 있음" 을 구분할 업무적 이유가 없다면 둘을 나누는 것은 복잡도만 늘린다.

**⑥ 동일성 비교·동기화 금지.** Javadoc 은 Optional 이 **value-based class** 이므로 "should not use instances for synchronization" 이라고 경고한다. `==` 비교, `synchronized(optional)` 을 하지 않는다.

**⑦ 성능 민감 루프에서의 남용.** Optional 은 객체다. 초당 수백만 번 도는 내부 루프에서 "깔끔해 보여서" 매번 `Optional.ofNullable(x).map(...)` 을 만들 필요는 없다. 경계(공개 API 반환)에서 쓰고 내부는 평범한 null 체크로 충분하다.

### 2.5 원시 특화 Optional

`OptionalInt`, `OptionalLong`, `OptionalDouble` 은 박싱 없이 원시 값을 담는다. `IntStream.max()` 등의 반환 타입이다. `map`/`flatMap` 이 없으니 체이닝이 필요하면 `boxed()` 스트림을 쓰거나 `orElse` 로 바로 꺼낸다.

---

## 3. 예외 계층 — checked vs unchecked

### 3.1 무엇인가

```text
Throwable
├── Error                      (unchecked) — OutOfMemoryError, StackOverflowError …
└── Exception                  (checked)   — IOException, SQLException …
    └── RuntimeException       (unchecked) — NullPointerException, IllegalArgumentException …
```

JLS 정의: unchecked 예외 클래스는 `RuntimeException` 과 그 하위 클래스, `Error` 와 그 하위 클래스다. 나머지 `Throwable` 하위 클래스는 모두 checked 다([JLS §11.1.1](https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html)). checked 예외는 메서드 `throws` 에 선언하거나 잡아야 컴파일된다.

### 3.2 설계 의도 — JLS 가 직접 밝힌 이유

JLS 11.2 는 두 종류를 검사에서 뺀 이유를 적는다.

- **Error**: "they can occur at many points in the program and recovery from them is difficult or impossible."
- **RuntimeException**: 선언하게 해봐야 "would not aid significantly in establishing the correctness of programs." 컴파일러가 가진 정보로는 그런 런타임 예외가 안 난다는 것을 증명하기 어려워서, 선언을 강제하면 "simply be an irritation to programmers" 라고 한다.

([JLS §11.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html))

이 설명에서 실무 기준이 나온다.

| 구분 | 의미 | 예 | 호출자에게 기대하는 것 |
|---|---|---|---|
| checked | 정상 프로그램에서도 **일어날 수 있고, 호출자가 복구할 수 있는** 외부 상황 | 파일 없음, 네트워크 끊김 | 재시도, 대체 경로, 사용자 안내 |
| unchecked (`RuntimeException`) | **프로그래밍 오류** 또는 호출자가 할 수 있는 게 없는 상황 | null 인자, 잘못된 상태, 범위 초과 | 고치기 (코드 수정) |
| `Error` | JVM 수준 문제 | OOM | 잡지 않는다 |

### 3.3 현실 — 왜 많은 프레임워크가 unchecked 로 기울었나

checked 예외는 **모든 중간 계층의 시그니처에 전파**된다. 저장소 구현을 JDBC → JPA 로 바꾸면 `throws SQLException` 이 서비스·컨트롤러 시그니처까지 바뀌어야 한다. 그리고 [J4 §3.4](https://myoungsoo7.github.io/2026/10/12/java-lambda-functional-interface-stream/) 에서 봤듯 `java.util.function` 인터페이스는 checked 예외를 던질 수 없어 람다·스트림과 궁합이 나쁘다.

그래서 스프링은 `SQLException` 같은 기술별 예외를 `DataAccessException` 을 루트로 하는 자체 예외 계층으로 변환한다. 레퍼런스는 이 예외들이 "wrap the original exception so that there is never any risk that you might lose any information" 이라고 설명한다([Spring — DAO Support](https://docs.spring.io/spring-framework/reference/data-access/dao.html)). 코틀린은 아예 checked 예외 개념을 두지 않았다([K1](https://myoungsoo7.github.io/2026/10/12/kotlin-essence-pragmatism-java-interop/)).

### 3.4 실무 가이드

```java
// 1) 도메인 예외는 RuntimeException 을 상속한 계층으로
public abstract class BusinessException extends RuntimeException {
    private final ErrorCode code;
    protected BusinessException(ErrorCode code, String message) {
        super(message);
        this.code = code;
    }
    public ErrorCode code() { return code; }
}
public class InsufficientStockException extends BusinessException {
    public InsufficientStockException(String sku, int requested, int available) {
        super(ErrorCode.OUT_OF_STOCK,
              "sku=%s requested=%d available=%d".formatted(sku, requested, available));
    }
}

// 2) checked 예외를 감쌀 때는 원인(cause)을 반드시 넘긴다
try {
    return Files.readString(path);
} catch (IOException e) {
    throw new UncheckedIOException("failed to read " + path, e);   // e 를 넘긴다
}
```

```java
// 3) 웹 계층에서 한 곳에 모아 변환 (스프링 MVC)
@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorBody> business(BusinessException e) {
        return ResponseEntity.status(e.code().status()).body(new ErrorBody(e.code(), e.getMessage()));
    }
}
```

### 3.5 함정

**① 예외 삼키기**

```java
try { send(); } catch (Exception e) { }                   // 최악: 흔적 없음
try { send(); } catch (Exception e) { e.printStackTrace(); } // 로그 시스템 밖으로 샌다
try { send(); } catch (Exception e) { log.error("send failed", e); throw e; } // 로그+재던지기 중복
```

원칙: **처리할 수 있는 곳에서 잡고, 아니면 던진다.** 로그는 최종 처리 지점 한 곳에서. 잡아서 다른 예외로 바꾸면 cause 를 넘긴다.

**② `catch (Exception e)` 의 범위** — `RuntimeException` 까지 다 잡아 프로그래밍 오류를 숨긴다. 필요한 예외 타입만 잡는다. 여러 타입을 같은 방식으로 처리하려면 multi-catch.

```java
try {
    client.call();
} catch (SocketTimeoutException | ConnectException e) {   // multi-catch (Java 7)
    retry();
}
```

multi-catch 의 catch 파라미터는 암묵적으로 `final` 이다([JLS §14.20](https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html)).

**③ `InterruptedException` 을 삼키지 않는다.** 잡았다면 인터럽트 상태를 복원한다. 스레드 풀 종료·가상 스레드 취소가 이 플래그에 의존한다([J7](https://myoungsoo7.github.io/2026/10/12/java-concurrency-thread-to-virtual-threads/)).

```java
try {
    Thread.sleep(100);
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();   // 상태 복원
    throw new IllegalStateException("interrupted", e);
}
```

**④ 예외로 흐름 제어** — "없으면 예외" 를 일상적인 분기에 쓰지 않는다. 예외 객체는 스택트레이스를 채우는 비용이 있다. 정상적인 "없음" 은 Optional 이나 결과 타입(sealed `Result`, [J3](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/))으로 표현한다.

**⑤ `finally` 에서 return 하지 않는다.** `finally` 의 `return` 은 `try` 에서 던진 예외를 조용히 없앤다.

---

## 4. try-with-resources

### 4.1 무엇인가

Java 7 에 도입된 문법으로(`AutoCloseable` @since 1.7, [AutoCloseable](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/AutoCloseable.html)), `AutoCloseable` 자원을 블록이 끝날 때 자동으로 닫는다. JLS 규칙([JLS §14.20.3](https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html)):

- 자원 타입은 `AutoCloseable` 의 하위 타입이어야 한다.
- 자원 변수는 암묵적으로 `final` 이다.
- 자원은 **초기화의 역순**으로 닫힌다.

```java
try (Connection con = dataSource.getConnection();
     PreparedStatement ps = con.prepareStatement("select name from users where id = ?")) {
    ps.setLong(1, id);
    try (ResultSet rs = ps.executeQuery()) {
        return rs.next() ? rs.getString(1) : null;
    }
}   // rs → ps → con 순으로 닫힌다
```

### 4.2 억제된 예외 (suppressed)

본문에서 예외가 나고 `close()` 에서도 예외가 나면? 본문 예외가 전파되고, `close()` 예외는 **억제(suppressed)** 되어 본문 예외에 붙는다. `Throwable.addSuppressed` Javadoc: "typically called (automatically and implicitly) by the `try`-with-resources statement"([Throwable](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Throwable.html)). `addSuppressed`/`getSuppressed` 는 Java 7 에 추가됐다.

```java
try (var res = new FlakyResource()) {
    throw new IllegalStateException("body failed");
} catch (IllegalStateException e) {
    for (Throwable s : e.getSuppressed()) {
        log.warn("suppressed during close", s);    // close() 에서 난 예외
    }
    throw e;
}
```

**왜 중요한가.** 예전의 `try/finally` 수동 close 에서는 `finally` 의 `close()` 예외가 본문 예외를 **덮어써서** 진짜 원인이 사라지곤 했다.

```java
// Java 6 스타일 — 원인 예외가 사라질 수 있다
InputStream in = open();
try {
    process(in);          // 여기서 예외 A
} finally {
    in.close();           // 여기서 예외 B → A 는 사라지고 B 만 전파
}
```

### 4.3 Java 9 개선 — effectively final 변수를 자원으로

[JEP 213](https://openjdk.org/jeps/213)(Java 9)은 "effectively-final variables to be used as resources" 를 허용했다.

```java
// 생성은 밖에서(예: 팩토리, 조건 분기), 닫기는 try-with-resources 로
BufferedReader reader = Files.newBufferedReader(path);
try (reader) {                         // Java 9+
    return reader.readLine();
}
```

### 4.4 실무 사용사례

```java
// 1) 파일 스트림 — Files.lines 는 반드시 닫는다
try (Stream<String> lines = Files.lines(path)) {
    return lines.filter(l -> !l.isBlank()).count();
}

// 2) 스프링 데이터 JPA 의 Stream 쿼리 — 레퍼런스가 닫으라고 명시
@Transactional(readOnly = true)
public void exportAll(Writer out) {
    try (Stream<User> users = userRepository.streamAllBy()) {
        users.forEach(u -> write(out, u));
    }
}

// 3) 사용자 정의 자원 — 락, MDC, 타이머 등 "범위가 있는 상태"
public final class MdcScope implements AutoCloseable {
    private final String key;
    public MdcScope(String key, String value) { this.key = key; MDC.put(key, value); }
    @Override public void close() { MDC.remove(key); }    // checked 예외를 던지지 않게 좁힘
}

try (var _ = new MdcScope("orderId", orderId)) {          // `_` 는 Java 22+ (JEP 456)
    process(order);
}
```

`Files.lines` 의 API Note 는 "must be used within a try-with-resources statement or similar control structure" 라고 명시하고([Files](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html)), 스프링 데이터 JPA 레퍼런스도 Stream 결과는 "must be closed after usage to avoid resource leaks" 라고 한다([Spring Data JPA Query Methods](https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html)). 사용하지 않는 자원 변수를 `_` 로 둘 수 있는 것은 Java 22 의 [JEP 456](https://openjdk.org/jeps/456) 이다. 그 이전 버전에서는 `var ignored = ...` 처럼 이름을 붙인다.

### 4.5 함정

- **`close()` 시그니처를 좁힌다.** `AutoCloseable.close()` 는 `throws Exception` 이다. 직접 만든 자원은 `close()` 를 재정의할 때 `throws` 를 없애거나 구체 타입으로 좁혀야 사용하는 쪽이 불필요한 catch 를 안 쓴다.
- **래퍼 생성자에서 예외가 나면** 안쪽 자원이 닫히지 않을 수 있다. `try (var r = new BufferedReader(new FileReader(f)))` 에서 바깥 생성자가 실패하면 `FileReader` 는 자원으로 등록되지 않았다. 각 자원을 별도 선언으로 나누면 안전하다.

```java
try (var fr = new FileReader(file);
     var br = new BufferedReader(fr)) {      // 둘 다 자원으로 등록
    ...
}
```

- **자원을 바깥으로 반환하지 않는다.** try 블록이 끝나면 닫히므로, 열린 `InputStream` 을 반환하려 했다면 설계를 바꿔야 한다(콜백으로 처리하게 하거나 호출자가 닫게 한다).

---

## 5. 스프링과 예외 — `@Transactional` 롤백 규칙

### 5.1 기본 규칙

스프링 레퍼런스: "In its default configuration, the Spring Framework's transaction infrastructure code marks a transaction for rollback only in the case of runtime, unchecked exceptions. That is, when the thrown exception is an instance or subclass of `RuntimeException`. (`Error` instances also, by default, result in a rollback)."([Spring — Rolling Back a Declarative Transaction](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html))

즉 **checked 예외는 기본적으로 롤백하지 않는다.**

```java
@Transactional
public void transfer(long from, long to, long amount) throws InsufficientFundsException {
    accountRepository.withdraw(from, amount);
    if (balanceOf(from) < 0) {
        throw new InsufficientFundsException();   // checked 라면 기본 설정에서 커밋된다!
    }
    accountRepository.deposit(to, amount);
}
```

### 5.2 대응

```java
// (1) 도메인 예외를 RuntimeException 계열로 만든다 — 권장 (§3.4)
public class InsufficientFundsException extends BusinessException { ... }

// (2) checked 예외를 유지해야 한다면 롤백 규칙을 명시한다
@Transactional(rollbackFor = InsufficientFundsException.class)
public void transfer(...) throws InsufficientFundsException { ... }
```

### 5.3 함정: 예외를 잡아버리면 롤백되지 않는다

```java
@Transactional
public void placeOrder(Order o) {
    orderRepository.save(o);
    try {
        pointService.use(o.userId(), o.points());
    } catch (RuntimeException e) {
        log.warn("point failed", e);   // 예외가 프록시 밖으로 안 나간다 → 커밋
    }
}
```

트랜잭션 인터셉터는 **메서드 밖으로 나온 예외**를 보고 결정한다. 이 메서드 안에서 잡아 삼키면 주문은 커밋된다. 의도한 것인지 반드시 확인한다. 반대로 `pointService.use` 가 자신의 `@Transactional`(같은 트랜잭션 참여)에서 런타임 예외를 던지고 그것을 바깥에서 잡으면, 내부 참여 트랜잭션이 이미 rollback-only 로 표시해 둔 상태라 바깥 커밋 시점에 `UnexpectedRollbackException` 이 난다. 스프링 레퍼런스는 `PROPAGATION_REQUIRED` 에서 내부 범위가 rollback-only 를 설정하면 바깥 트랜잭션 입장에서 그 롤백은 "unexpected" 이고 이때 `UnexpectedRollbackException` 이 던져진다고 설명한다([Spring — Transaction Propagation](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html)). 프록시·AOP 원리는 [J9](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 에서 다룬다.

---

## 6. 자바 vs 코틀린 요약

| 주제 | 자바 | 코틀린 |
|---|---|---|
| null 가능성 표현 | 타입에 없음 (애노테이션 힌트) | 타입에 있음 (`String` vs `String?`) |
| 부재 표현 | `Optional<T>` (반환 타입) | `T?` + `?.`, `?:` |
| NPE 진단 | Helpful NPE (JDK 15+ 기본) | 컴파일 타임에 대부분 차단, `!!` 에서만 |
| checked 예외 | 있음 | 없음 |
| 자원 해제 | try-with-resources | `use { }` 확장 함수 |

코틀린 쪽 상세와 공식 근거는 [K2](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/) 를 보자.

---

## 7. 체크리스트

- 공개 메서드가 "없을 수 있는 단일 값" 을 반환하면 `Optional<T>`. 컬렉션은 빈 컬렉션.
- Optional 은 반환 타입에만. 필드·파라미터·컬렉션 원소에 쓰지 않는다. Optional 변수에 null 금지.
- `orElse(비싼 것)` 대신 `orElseGet`. `get()` 대신 `orElseThrow()`.
- 도메인 예외는 unchecked 계층으로, 감쌀 때는 cause 를 넘긴다.
- `InterruptedException` 은 인터럽트 상태 복원.
- `AutoCloseable` 은 무조건 try-with-resources. `Files.lines`, 스프링 데이터 `Stream` 포함.
- `@Transactional` 은 checked 예외에 기본 롤백하지 않는다. 메서드 안에서 삼킨 예외도 롤백을 일으키지 않는다.

---

## References

- JLS SE 21, Chapter 11 Exceptions (§11.1.1, §11.2) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html
- JLS SE 21, Chapter 14 (§14.20 try, §14.20.3 try-with-resources) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html
- JLS SE 7, Chapter 14 — https://docs.oracle.com/javase/specs/jls/se7/html/jls-14.html
- `java.util.Optional` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html
- `java.util.Objects` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Objects.html
- `java.util.List` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html
- `java.lang.Throwable` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Throwable.html
- `java.lang.AutoCloseable` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/AutoCloseable.html
- `java.nio.file.Files` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html
- JEP 213: Milling Project Coin — https://openjdk.org/jeps/213
- JEP 358: Helpful NullPointerExceptions — https://openjdk.org/jeps/358
- JDK-8233014: Enable ShowCodeDetailsInExceptionMessages by default — https://bugs.openjdk.org/browse/JDK-8233014
- JEP 456: Unnamed Variables & Patterns — https://openjdk.org/jeps/456
- Spring Framework Reference, Rolling Back a Declarative Transaction — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html
- Spring Framework Reference, Transaction Propagation — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html
- Spring Framework Reference, DAO Support — https://docs.spring.io/spring-framework/reference/data-access/dao.html
- Spring Data Commons Reference, Null Handling of Repository Methods — https://docs.spring.io/spring-data/commons/reference/repositories/null-handling.html
- Spring Data JPA Reference, Query Methods — https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/) ← 지금 글
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
