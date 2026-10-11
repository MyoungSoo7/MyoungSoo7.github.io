---
layout: post
title: "현대 자바 문법 총정리 — 8 → 11 → 17 → 21 → 25 LTS 별로 무엇이 바뀌었나"
date: 2026-10-12 00:18:42 +0900
categories: [java]
tags: [java, java8, java11, java17, java21, java25, lts, var, text-blocks, records, sealed, switch-expression, pattern-matching, jep, migration]
---

자바·코틀린 20편 시리즈의 **자바 8번째 글(J8)** 입니다. "우리 서비스는 자바 17 인데, 21 이나 25 로 올리면 **코드에서** 무엇을 쓸 수 있게 되나?" 라는 질문에 답하려고 쓴 글입니다. JVM·GC 같은 런타임 변화보다는 **개발자가 매일 쓰는 언어 문법과 표준 라이브러리 API** 에 집중합니다. LTS 구간(8, 11, 17, 21, 25)별로 묶고, 각 기능은 **무엇인가 → 코드 → 실무 사용사례 → 함정** 순서로 짧게 봅니다.

JVM 구조와 런타임 쪽 변화는 이전 글 [JVM 의 구조와 Java 버전 변천사](https://myoungsoo7.github.io/2026/05/29/jvm-structure-java-version-evolution-production-impact/) 에서 다뤘습니다. 버전별로 **스프링 부트가 요구하는 자바 버전**은 [J10 — 스프링부트 × 자바 호환](https://myoungsoo7.github.io/2026/10/12/spring-boot-java-version-compatibility/) 에서 정리합니다.

---

## 0. LTS 지도와 이 글을 읽는 법

Oracle 의 Java SE 지원 로드맵은 **Java SE 8, 11, 17, 21, 25 를 LTS 릴리스**로 명시하고, 앞으로 LTS 를 2년마다 내겠다고 밝힙니다 ([Oracle Java SE Support Roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html)). OpenJDK 프로젝트 페이지의 GA 날짜는 다음과 같습니다.

| 버전 | GA | 근거 |
|---|---|---|
| JDK 8 | 2014-03-18 | [JDK 8](https://openjdk.org/projects/jdk8/) |
| JDK 11 | 2018-09-25 | [JDK 11](https://openjdk.org/projects/jdk/11/) |
| JDK 17 | 2021-09-14 | [JDK 17](https://openjdk.org/projects/jdk/17/) |
| JDK 21 | 2023-09-19 | [JDK 21](https://openjdk.org/projects/jdk/21/) |
| JDK 25 | 2025-09-16 | [JDK 25](https://openjdk.org/projects/jdk/25/) |

JDK 10 에 시간 기반 릴리스 버전 체계([JEP 322: Time-Based Release Versioning](https://openjdk.org/jeps/322))가 들어왔고, 위 표처럼 GA 가 3월·9월에 반복됩니다. 그래서 LTS 사이의 비-LTS 릴리스에서 프리뷰를 거쳐 다음 LTS 에서 정식이 되는 흐름이 반복됩니다. 아래에서 "도입" 은 **정식(final) 도입 버전**을 뜻하고, 프리뷰 버전은 따로 표기합니다.

---

## 1. Java 8 (2014) — 함수형의 시작

JDK 8 의 중심은 Project Lambda 였습니다 ([JDK 8](https://openjdk.org/projects/jdk8/)). 언어·라이브러리 JEP 는 [JDK 8 Features](https://openjdk.org/projects/jdk8/features) 에서 확인했습니다.

| 기능 | JEP |
|---|---|
| 람다 식 & 인터페이스 default 메서드 | [JEP 126](https://openjdk.org/jeps/126) |
| 컬렉션 벌크 연산(Stream) | [JEP 107](https://openjdk.org/jeps/107) |
| Date & Time API (`java.time`) | [JEP 150](https://openjdk.org/jeps/150) |
| 타입 애노테이션 | [JEP 104](https://openjdk.org/jeps/104) |
| 반복 애노테이션 | [JEP 120](https://openjdk.org/jeps/120) |
| 런타임 파라미터 이름 접근 | [JEP 118](https://openjdk.org/jeps/118) |
| Base64 | [JEP 135](https://openjdk.org/jeps/135) |

### 1.1 람다·메서드 참조·Stream

```java
List<String> activeEmails = users.stream()
        .filter(User::isActive)
        .map(User::email)
        .sorted()
        .collect(Collectors.toList());
```

- **사용사례**: 컬렉션 변환·필터링, 콜백(`Comparator`, `Runnable`), 스프링의 `JdbcTemplate` 의 `RowMapper` 같은 함수형 인터페이스 자리.
- **함정**: 람다 안의 checked 예외 처리, 스트림 안의 부수효과, 디버깅 어려움. 자세한 내용은 [J4 — 람다·함수형 인터페이스·Stream](https://myoungsoo7.github.io/2026/10/12/java-lambda-functional-interface-stream/).

### 1.2 `java.time`

```java
LocalDate due = LocalDate.of(2026, 10, 31);
ZonedDateTime seoulNow = ZonedDateTime.now(ZoneId.of("Asia/Seoul"));
Duration timeout = Duration.ofSeconds(3);
```

- **사용사례**: `Date`/`Calendar` 대체. 불변이고 스레드 안전합니다.
- **함정**: DB·JSON 경계에서 `LocalDateTime`(시간대 없음)과 `Instant`/`OffsetDateTime`(시점)을 혼동하는 것. "언제 일어났나(시점)" 는 `Instant`, "달력상 날짜" 는 `LocalDate` 로 구분하세요.

### 1.3 파라미터 이름(JEP 118) — 스프링과의 연결

JEP 118 은 `javac -parameters` 로 컴파일하면 런타임에 리플렉션으로 메서드 파라미터 이름을 읽을 수 있게 했습니다. 스프링 프레임워크 6.0 은 이 표준 방식을 쓰라고 권하며, 바이트코드 디버그 정보를 읽던 `LocalVariableTableParameterNameDiscoverer` 를 deprecated 처리했습니다 ([Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)). `@PathVariable Long id` 처럼 이름을 생략한 코드가 6.x 로 올리며 깨지는 원인이 이것입니다. 자세한 내용은 [J9](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/).

---

## 2. Java 9 ~ 11 — 다듬기와 `var`

### 2.1 Java 9: 모듈, 컬렉션 팩토리, Project Coin 마무리

JDK 9(2017-09-21 GA)의 개발자 관련 JEP ([JDK 9](https://openjdk.org/projects/jdk9/)):

- [JEP 261](https://openjdk.org/jeps/261) 모듈 시스템
- [JEP 269](https://openjdk.org/jeps/269) 컬렉션 팩토리 메서드
- [JEP 213](https://openjdk.org/jeps/213) Milling Project Coin
- [JEP 222](https://openjdk.org/jeps/222) jshell
- [JEP 266](https://openjdk.org/jeps/266) `CompletableFuture` 타임아웃 등 동시성 보강

**컬렉션 팩토리(JEP 269)**

```java
List<String> roles = List.of("ADMIN", "USER");
Set<Integer> ports = Set.of(80, 443);
Map<String, Integer> limits = Map.of("free", 10, "pro", 1000);
```

- **무엇**: 수정 불가(unmodifiable) 컬렉션을 만드는 정적 팩토리.
- **함정 1 — `null` 불가**: JEP 269 는 "null 원소·키·값을 허용하지 않는다" 고 명시합니다. `List.of(a, null)` 은 `NullPointerException`.
- **함정 2 — 순서 보장 없음**: `Set.of`, `Map.of` 의 반복 순서는 보장되지 않습니다. 순서에 의존하는 테스트가 간헐적으로 깨지는 원인입니다.
- **함정 3 — 수정 시 예외**: `add`/`put` 하면 `UnsupportedOperationException`. `Arrays.asList` 와 달리 `set` 도 안 됩니다.

**Project Coin 마무리(JEP 213)** — 다섯 가지 작은 변경:

1. `private` 인스턴스 메서드에 `@SafeVarargs`
2. try-with-resources 에서 **effectively final 변수** 사용
3. 익명 클래스에 다이아몬드 `<>` 사용
4. `_` 를 식별자로 쓰면 에러
5. **인터페이스 `private` 메서드**

```java
// 2) 이미 선언된 리소스를 그대로
BufferedReader reader = Files.newBufferedReader(path);
try (reader) {
    return reader.readLine();
}

// 5) 인터페이스 private 메서드 — default 메서드 간 공통 로직
public interface Discount {
    long apply(long price);

    default long applyTwice(long price) { return clamp(apply(apply(price))); }
    default long applyOnce(long price)  { return clamp(apply(price)); }

    private long clamp(long v) { return Math.max(0, v); }
}
```

**API 추가(Since 9)**: `Stream.takeWhile/dropWhile`, `Optional.ifPresentOrElse/or/stream` (JDK 21 Javadoc 의 Since 표기로 확인).

**모듈(JEP 261) 의 함정**: 대부분의 스프링 애플리케이션은 클래스패스(이름 없는 모듈)에서 돌기 때문에 `module-info.java` 를 쓰지 않습니다. 실무 영향은 모듈을 직접 쓰는 것보다, 뒤에 나올 **JDK 내부 캡슐화(JEP 403)** 쪽이 훨씬 큽니다.

### 2.2 Java 10: `var`

JDK 10(2018-03-20 GA)의 [JEP 286](https://openjdk.org/jeps/286) 이 지역 변수 타입 추론을 도입했습니다.

```java
var list = new ArrayList<String>();          // ArrayList<String> 으로 추론
var byStatus = orders.stream()
        .collect(Collectors.groupingBy(Order::status));   // Map<Status, List<Order>>

for (var entry : byStatus.entrySet()) {
    System.out.println(entry.getKey() + " " + entry.getValue().size());
}
```

| 허용 | 불허 |
|---|---|
| 초기화식이 있는 지역 변수 | 필드, 메서드 파라미터, 반환 타입 |
| 향상된 `for` 의 변수 | `catch` 파라미터 |
| 전통적 `for` 의 인덱스 변수 | 초기화식 없는 변수, `null` 초기화 |
| | 타깃 타입 없는 람다·배열 초기화식 |

- **`var` 는 키워드가 아니라 "예약된 타입 이름(reserved type name)"** 입니다. 변수명·메서드명으로 `var` 를 쓴 기존 코드는 그대로 컴파일됩니다([JEP 286](https://openjdk.org/jeps/286)).
- **사용사례**: 오른쪽에 타입이 이미 드러나는 경우(`new`, 팩토리 메서드), 긴 제네릭 타입.
- **함정 1 — 의도치 않은 구체 타입**: `var list = new ArrayList<String>();` 은 `List` 가 아니라 `ArrayList` 입니다. 인터페이스 타입으로 다루고 싶으면 명시하세요.
- **함정 2 — 다이아몬드와의 조합**: `var list = new ArrayList<>();` 는 `ArrayList<Object>` 로 추론됩니다.
- **함정 3 — 가독성**: `var result = service.process(x);` 처럼 타입이 안 보이는 곳에서는 오히려 읽기 어렵습니다.

**API 추가(Since 10)**: `List.copyOf`, `Collectors.toUnmodifiableList`, 인자 없는 `Optional.orElseThrow()`.

### 2.3 Java 11 (LTS)

JDK 11(2018-09-25 GA)의 주요 JEP ([JDK 11](https://openjdk.org/projects/jdk/11/)):

- [JEP 323](https://openjdk.org/jeps/323) 람다 파라미터에 `var`
- [JEP 321](https://openjdk.org/jeps/321) HTTP Client 표준화
- [JEP 330](https://openjdk.org/jeps/330) 단일 소스 파일 실행
- [JEP 320](https://openjdk.org/jeps/320) **Java EE 와 CORBA 모듈 제거**

**람다 파라미터의 `var` (JEP 323)** — 애노테이션을 붙이기 위한 문법입니다.

```java
BiFunction<String, String, String> join =
        (@NonNull var a, @NonNull var b) -> a + b;
```

함정: 모든 파라미터에 `var` 를 쓰거나 아무 데도 안 써야 합니다. `(var x, y)`, `(var x, int y)` 처럼 섞을 수 없습니다([JEP 323](https://openjdk.org/jeps/323)).

**단일 파일 실행 (JEP 330)**

```bash
java Hello.java     # 메모리에서 컴파일 후 실행
```

운영 스크립트나 일회성 도구에 유용합니다. JDK 22 의 [JEP 458](https://openjdk.org/jeps/458) 은 이를 여러 소스 파일로 확장했습니다.

**`String`·`Files` API (Since 11)**: `String.isBlank/strip/lines/repeat`, `Files.readString/writeString`, `Optional.isEmpty`.

```java
String body = Files.readString(Path.of("payload.json"));
if (body.isBlank()) { ... }
String divider = "-".repeat(40);
```

`strip()` 은 유니코드 공백 기준이라 전각 공백 등도 제거합니다(`trim()` 은 코드 포인트 `U+0020` 이하만 제거). 사용자 입력 정리에는 `strip()` 이 맞습니다.

**함정 — JEP 320**: JDK 11 에서 `java.xml.bind`(JAXB), `java.xml.ws`(JAX-WS), `java.activation`, `java.xml.ws.annotation`(Common Annotations), `java.transaction`(JTA), `java.corba` 등이 JDK 에서 빠졌고, 대신 Maven Central 의 독립 artifact 로 쓰게 되었습니다 ([JEP 320](https://openjdk.org/jeps/320)). 8 → 11 업그레이드 시 `javax.xml.bind` 를 쓰던 코드는 별도 의존성을 추가해야 합니다. 이 흐름이 결국 스프링 부트 3 의 `javax` → `jakarta` 전환으로 이어집니다(J10).

---

## 3. Java 12 ~ 17 — 데이터 지향 문법의 등장

| 기능 | 프리뷰 | 정식 | JEP |
|---|---|---|---|
| `switch` 식 | 12, 13 | **14** | [JEP 361](https://openjdk.org/jeps/361) |
| Helpful NPE 메시지 | — | **14**(기본 꺼짐) → 15 기본 켜짐 | [JEP 358](https://openjdk.org/jeps/358), [JDK-8233014](https://bugs.openjdk.org/browse/JDK-8233014) |
| 텍스트 블록 | 13, 14 | **15** | [JEP 378](https://openjdk.org/jeps/378) |
| record | 14, 15 | **16** | [JEP 395](https://openjdk.org/jeps/395) |
| `instanceof` 패턴 | 14, 15 | **16** | [JEP 394](https://openjdk.org/jeps/394) |
| sealed 클래스 | 15, 16 | **17** | [JEP 409](https://openjdk.org/jeps/409) |
| JDK 내부 강한 캡슐화 | — | **17** | [JEP 403](https://openjdk.org/jeps/403) |

### 3.1 텍스트 블록 (15)

```java
String sql = """
        SELECT o.id, o.amount
          FROM orders o
         WHERE o.user_id = :userId
           AND o.status = 'PAID'
        """;

String json = """
        {"name": "%s", "age": %d}
        """.formatted(name, age);
```

JEP 378 의 규칙:

- 여는 `"""` 뒤에는 **반드시 줄바꿈**이 와야 합니다(`"""SELECT` 는 에러).
- 컴파일 시 줄 끝을 LF 로 정규화 → **부수적 들여쓰기(incidental whitespace) 제거** → 이스케이프 해석 순서로 처리.
- 새 이스케이프 `\<줄바꿈>`(줄 이어 붙이기), `\s`(공백 한 칸, 줄 끝 공백 제거를 막는 울타리).
- `String.stripIndent()`, `translateEscapes()`, `formatted()` 추가(Javadoc 상 Since 15).

**사용사례**: 네이티브 SQL, JSON 테스트 픽스처, HTML 템플릿 조각.
**함정**: 닫는 `"""` 의 위치가 들여쓰기 기준선이 됩니다. 닫는 따옴표를 내용보다 왼쪽에 두면 그만큼 공백이 남습니다. 그리고 텍스트 블록은 **문자열 보간이 아닙니다**. 사용자 입력을 `formatted()` 로 SQL 에 넣으면 그대로 SQL 인젝션입니다. 바인딩 파라미터를 쓰세요.

### 3.2 Helpful NullPointerExceptions (14, 15)

```text
Cannot invoke "String.length()" because "user.address().city()" is null
```

JEP 358 은 JDK 14 에 들어왔지만 처음에는 기본값이 꺼져 있었고, JDK 15 에서 기본으로 켜졌습니다([JEP 358](https://openjdk.org/jeps/358), [JDK-8233014](https://bugs.openjdk.org/browse/JDK-8233014)). 17 이상이면 별도 설정 없이 이 메시지를 봅니다. 코드 변화는 없지만 체이닝 코드 디버깅 시간이 크게 줄어듭니다.

### 3.3 record (16)

```java
public record Money(long amount, String currency) {
    public Money {                       // compact 생성자 — 검증·정규화
        if (amount < 0) throw new IllegalArgumentException("음수 금액");
        currency = currency.toUpperCase();
    }

    public Money plus(Money other) {
        if (!currency.equals(other.currency)) throw new IllegalArgumentException();
        return new Money(amount + other.amount, currency);
    }
}
```

JEP 395 기준 규칙: 암묵적 `final`, 다른 클래스 상속 불가(상위 클래스는 항상 `java.lang.Record`), 필드는 `private final`, **인스턴스 필드 추가 선언 불가**, 인터페이스 구현 가능, 지역 record 가능. compact 생성자에서는 필드 대입이 끝에서 자동으로 일어납니다.

- **사용사례**: DTO, 값 객체, 메서드 내부 중간 결과(지역 record), 패턴 매칭 대상(J6).
- **함정**: JPA 엔티티로는 맞지 않습니다(불변, `final`, 기본 생성자 없음). 그리고 배열·가변 리스트를 구성요소로 넣으면 겉만 불변입니다. compact 생성자에서 `List.copyOf` 로 방어 복사하세요.

상세는 [J3 — 클래스 모델의 진화](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/).

### 3.4 sealed 와 패턴 매칭

```java
public sealed interface Shape permits Circle, Square, Rect {}
public record Circle(double r) implements Shape {}
public record Square(double side) implements Shape {}
public non-sealed class Rect implements Shape { /* 확장 열어 둠 */ }
```

허가된 하위 타입은 `final`, `sealed`, `non-sealed` 중 **정확히 하나**를 선언해야 합니다([JEP 409](https://openjdk.org/jeps/409)). record 는 암묵적 `final` 이라 따로 붙이지 않습니다. 패턴 매칭과의 조합은 [J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/) 에서 자세히 다룹니다.

### 3.5 Since 12~16 API

- `String.indent`(12), `Collectors.teeing`(12)
- `Stream.toList()`(16) — 수정 불가 리스트를 돌려주는 단축 메서드. `Stream.mapMulti`(16).

```java
// 12: 두 컬렉터 결과를 합치기
var stats = orders.stream().collect(Collectors.teeing(
        Collectors.counting(),
        Collectors.summingLong(Order::amount),
        (count, sum) -> new OrderStats(count, sum)));

// 16
List<String> names = users.stream().map(User::name).toList();
```

**함정**: `stream().toList()` 의 결과는 수정 불가입니다. `collect(Collectors.toList())` 를 기계적으로 `toList()` 로 바꾸면, 결과에 `add` 하던 코드가 런타임에 `UnsupportedOperationException` 을 냅니다.

### 3.6 JEP 403 — 리플렉션 프레임워크에 대한 영향 (17)

JDK 17 은 `--illegal-access` 옵션을 제거해 JDK 내부의 강한 캡슐화를 영구 기본값으로 만들었습니다. 리플렉션으로 JDK 내부 비공개 멤버에 접근하던 코드는 `InaccessibleObjectException` 으로 실패하고, 필요하면 `--add-opens` 로 패키지를 개별적으로 열어야 합니다. `sun.misc.Unsafe` 같은 핵심 내부 API 는 `jdk.unsupported` 모듈로 계속 접근 가능합니다 ([JEP 403](https://openjdk.org/jeps/403)). 11 → 17 업그레이드 때 오래된 라이브러리가 깨지는 가장 흔한 원인입니다.

---

## 4. Java 18 ~ 21 — 패턴 매칭 완성과 가상 스레드

| 기능 | 정식 | JEP |
|---|---|---|
| 기본 문자셋 UTF-8 | 18 | [JEP 400](https://openjdk.org/jeps/400) |
| Sequenced Collections | 21 | [JEP 431](https://openjdk.org/jeps/431) |
| record 패턴 | 21 | [JEP 440](https://openjdk.org/jeps/440) |
| `switch` 패턴 매칭 | 21 | [JEP 441](https://openjdk.org/jeps/441) |
| 가상 스레드 | 21 | [JEP 444](https://openjdk.org/jeps/444) |

JDK 21(2023-09-19 GA)에는 이 밖에도 String Templates(JEP 430), unnamed 패턴(JEP 443), unnamed class(JEP 445), Scoped Values(JEP 446), 구조적 동시성(JEP 453)이 **프리뷰**로 들어 있었습니다 ([JDK 21](https://openjdk.org/projects/jdk/21/)). 프리뷰는 `--enable-preview` 없이는 쓸 수 없습니다.

### 4.1 UTF-8 기본 (18)

JDK 18 부터 `Charset.defaultCharset()` 이 OS·로케일과 무관하게 UTF-8 입니다. 이전 동작이 필요하면 `-Dfile.encoding=COMPAT` 으로 되돌릴 수 있습니다 ([JEP 400](https://openjdk.org/jeps/400)).

**함정**: 윈도우 서버에서 기본 문자셋(MS949 등)에 의존해 파일을 읽던 코드가 17 → 21 업그레이드 후 한글이 깨질 수 있습니다. 경계에서는 항상 문자셋을 명시하세요(`Files.readString(path, StandardCharsets.UTF_8)`).

### 4.2 Sequenced Collections (21)

```java
List<Event> events = loadEvents();
Event first = events.getFirst();      // 이전: events.get(0)
Event last  = events.getLast();       // 이전: events.get(events.size() - 1)

LinkedHashMap<String, Integer> ranking = new LinkedHashMap<>();
ranking.putFirst("vip", 1);
var newestFirst = ranking.reversed();
```

JEP 431 은 `SequencedCollection`, `SequencedSet`, `SequencedMap` 세 인터페이스를 추가하고, `getFirst/getLast/addFirst/addLast/removeFirst/removeLast/reversed` 와 `firstEntry/lastEntry/pollFirstEntry/pollLastEntry/putFirst/putLast` 를 제공합니다 ([JEP 431](https://openjdk.org/jeps/431)).

**함정**: 기존 컬렉션 인터페이스(`List`, `Deque`, `LinkedHashSet`, `LinkedHashMap` 등)가 새 상위 인터페이스를 갖게 되면서 메서드가 추가되었습니다. 같은 이름(`getFirst()`, `reversed()` 등)인데 반환 타입이나 의미가 다른 메서드를 가진 **자체 컬렉션 구현체**는 21 로 올릴 때 컴파일 에러나 의도치 않은 오버라이드가 생길 수 있습니다.

### 4.3 패턴 매칭 & 가상 스레드

- `switch` 패턴 매칭·record 패턴: [J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/)
- 가상 스레드: [J7](https://myoungsoo7.github.io/2026/10/12/java-concurrency-thread-to-virtual-threads/)

---

## 5. Java 22 ~ 25 — 문턱 낮추기와 마무리

| 기능 | 프리뷰 | 정식 | JEP |
|---|---|---|---|
| unnamed 변수·패턴 `_` | 21 | **22** | [JEP 456](https://openjdk.org/jeps/456) |
| 여러 소스 파일 실행 | — | **22** | [JEP 458](https://openjdk.org/jeps/458) |
| FFM API (JNI 대체) | — | **22** | [JEP 454](https://openjdk.org/jeps/454) |
| Stream Gatherers | 22, 23 | **24** | [JEP 485](https://openjdk.org/jeps/485) |
| `synchronized` 가상 스레드 pinning 해소 | — | **24** | [JEP 491](https://openjdk.org/jeps/491) |
| 모듈 import 선언 | 23, 24 | **25** | [JEP 511](https://openjdk.org/jeps/511) |
| Compact 소스 파일 & 인스턴스 `main` | 21~24 | **25** | [JEP 512](https://openjdk.org/jeps/512) |
| 유연한 생성자 본문 | 22~24 | **25** | [JEP 513](https://openjdk.org/jeps/513) |
| Scoped Values | 21~24 | **25** | [JEP 506](https://openjdk.org/jeps/506) |

### 5.1 `_` (22)

```java
try { Integer.parseInt(s); } catch (NumberFormatException _) { return false; }
map.forEach((_, v) -> sum.add(v));
```

자세한 패턴 쪽 쓰임은 J6 참고.

### 5.2 Stream Gatherers (24)

`Stream::gather(Gatherer)` 는 JEP 485 의 표현대로 "중간 연산에 대해, `Stream::collect(Collector)` 가 종단 연산에 대해 하는 역할" 을 합니다. 내장 `Gatherers` 로 `fold`, `scan`, `windowFixed`, `windowSliding`, `mapConcurrent` 가 있습니다.

```java
// JEP 485 예제: 연속된 두 측정값 비교
List<List<Reading>> findSuspicious(Stream<Reading> source) {
    return source.gather(Gatherers.windowSliding(2))
                 .filter(window -> window.size() == 2
                    && isSuspicious(window.get(0), window.get(1)))
                 .toList();
}

// 1000건씩 끊어 배치 저장
orders.stream()
      .gather(Gatherers.windowFixed(1000))
      .forEach(orderRepository::saveAll);
```

- **사용사례**: 배치 청크 분할, 이동 평균, 연속 이벤트 비교. 예전에는 스트림 밖에서 인덱스를 돌려야 했던 일들입니다.
- **함정**: 21 LTS 에는 없습니다(22, 23 프리뷰). LTS 기준으로는 **25 부터** 씁니다.

### 5.3 유연한 생성자 본문 (25)

`super(...)`/`this(...)` 호출 **앞에** 문장을 쓸 수 있습니다. 이 구간(prologue)에서는 `this` 를 참조할 수 없고, 예외로 **초기화식이 없는 자기 클래스 필드에 대한 단순 대입**만 허용됩니다 ([JEP 513](https://openjdk.org/jeps/513)).

```java
class Employee extends Person {
    String officeID;

    Employee(int age, String officeID) {
        if (age < 18 || age > 67)
            throw new IllegalArgumentException();  // super 전에 빠른 실패
        this.officeID = officeID;                  // 초기화식 없는 필드 대입은 허용
        super(age);
    }
}
```

- **사용사례**: 상위 생성자 호출 전 인자 검증·변환. 이전에는 `static` 헬퍼 메서드를 만들어 `super(validate(age))` 처럼 우회했습니다.
- **함정**: prologue 에서 `this.age` 읽기, 메서드 호출, 초기화식이 있는 필드 대입은 모두 컴파일 에러입니다.

### 5.4 Compact 소스 파일 & 인스턴스 `main` (25)

```java
// Hello.java — 클래스 선언 없음
void main() {
    IO.println("Hello, World!");
}
```

JEP 512 기준: 클래스 선언을 생략하면 컴파일러가 이름 없는 패키지의 `final` 최상위 클래스를 암묵적으로 만들고, `java.base` 모듈의 공개 클래스들을 자동 import 하며, 새 `java.lang.IO` 클래스(`print`, `println`, `readln`)를 제공합니다. `main` 은 `static` 일 필요도, `String[]` 파라미터를 가질 필요도 없습니다.

- **사용사례**: 교육, 스크립트, 사내 도구. `java Hello.java`(JEP 330)와 같이 쓰면 셸 스크립트 대용이 됩니다.
- **함정**: 서비스 코드에서 쓸 기능이 아닙니다. 그리고 compact 소스 파일 안의 클래스는 이름으로 참조할 수 없으니 다른 코드가 의존할 대상이 아닙니다.

### 5.5 모듈 import (25)

```java
import module java.base;   // java.base 가 export 하는 모든 패키지의 공개 타입
```

- **함정**: 여러 모듈을 import 하면 같은 단순 이름이 충돌할 수 있습니다(`java.util.List` vs `java.awt.List`). 이때는 `import java.util.List;` 같은 단일 타입 import 가 우선해 충돌을 해결합니다 ([JEP 511](https://openjdk.org/jeps/511)).

### 5.6 JDK 25 에서도 여전히 프리뷰인 것

JDK 25(2025-09-16 GA)의 JEP 목록 기준 ([JDK 25](https://openjdk.org/projects/jdk/25/)):

- 구조적 동시성(5차 프리뷰, JEP 505) — JDK 26 에서 6차 프리뷰(JEP 525)
- 원시 타입 패턴(3차 프리뷰, JEP 507) — JDK 26 에서 4차 프리뷰(JEP 530)
- Stable Values(프리뷰, JEP 502) — JDK 26 에서 Lazy Constants(2차 프리뷰, JEP 526)로 이어짐 ([JDK 26](https://openjdk.org/projects/jdk/26/))

**String Templates** 는 JDK 21(JEP 430), 22(JEP 459)에서 프리뷰였지만, 이후 JDK 24·25·26 의 JEP 목록에는 없습니다. 오래된 글의 `STR."..."` 예제는 현재 JDK 에서 컴파일되지 않습니다.

---

## 6. 업그레이드 경로별 "코드에서 달라지는 것"

### 6.1 8 → 11

| 할 수 있게 되는 것 | 깨질 수 있는 것 |
|---|---|
| `var`, `List.of`, `String.isBlank/strip/repeat`, `Files.readString`, HTTP Client | JAXB·JAX-WS 등 Java EE 모듈 제거(JEP 320) → 의존성 추가 필요 |

### 6.2 11 → 17

| 할 수 있게 되는 것 | 깨질 수 있는 것 |
|---|---|
| `switch` 식, 텍스트 블록, record, `instanceof` 패턴, sealed, `Stream.toList()`, 친절한 NPE | JEP 403 강한 캡슐화 → 딥 리플렉션 쓰는 오래된 라이브러리 실패 |

스프링 부트 3.x 이상은 **Java 17 이 최소** 이므로, 사실상 모든 스프링 팀이 지나야 하는 구간입니다(J10).

### 6.3 17 → 21

| 할 수 있게 되는 것 | 깨질 수 있는 것 |
|---|---|
| `switch` 패턴 매칭, record 패턴, Sequenced Collections, 가상 스레드 | UTF-8 기본(JEP 400, 18)으로 플랫폼 기본 문자셋 의존 코드, `getFirst()` 등 이름 충돌 |

### 6.4 21 → 25

| 할 수 있게 되는 것 | 깨질 수 있는 것 |
|---|---|
| `_`, Stream Gatherers, 유연한 생성자 본문, 모듈 import, compact 소스 파일, Scoped Values, `synchronized` pinning 해소 | 32비트 x86 포트 제거(JEP 503) 등 플랫폼 정리. 빌드 도구·바이트코드 조작 라이브러리(ASM, ByteBuddy, Lombok 등)의 25 지원 버전 확인 필요 |

마지막 줄의 "라이브러리 지원 버전 확인" 은 일반적인 원칙입니다. 새 클래스 파일 버전을 읽어야 하는 바이트코드 도구는 JDK 업그레이드 때마다 먼저 올려야 합니다. 구체적인 지원 버전은 각 라이브러리의 릴리스 노트로 확인하세요.

---

## 7. 팀 컨벤션 제안

1. **`var`**: 오른쪽에 타입이 보일 때만. 공개 API 경계(반환값을 받는 곳)에서는 명시 타입.
2. **record**: DTO·값 객체의 기본값. 엔티티는 일반 클래스.
3. **텍스트 블록**: SQL·JSON 리터럴은 무조건. 단 값 삽입은 바인딩으로.
4. **`switch`**: 새 코드는 화살표 형식만. enum/sealed 대상은 `default` 금지(완전성 검사 유지).
5. **`toList()`**: 결과를 수정하지 않을 때만. 수정하면 `collect(Collectors.toCollection(ArrayList::new))`.
6. **프리뷰 기능**: 운영 코드 금지. 실험 모듈에서만.

---

## 8. 정리

- **8**: 람다·Stream·`java.time` — 함수형과 현대 날짜 API의 출발점.
- **11**: `var`, 컬렉션 팩토리, `String`/`Files` 편의 API, HTTP Client. Java EE 모듈 제거.
- **17**: `switch` 식, 텍스트 블록, record, `instanceof` 패턴, sealed — 데이터 지향 문법. 강한 캡슐화.
- **21**: 패턴 매칭 완성(record 패턴, `switch` 패턴), Sequenced Collections, 가상 스레드.
- **25**: `_`, Gatherers, 유연한 생성자, compact 소스 파일, Scoped Values, 그리고 가상 스레드 pinning 해소(24).
- 구조적 동시성, 원시 타입 패턴은 JDK 26 기준 아직 프리뷰. String Templates 는 정식 기능이 아닙니다.

---

## References

- [Oracle Java SE Support Roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html) — Oracle
- OpenJDK 프로젝트 페이지: [JDK 8](https://openjdk.org/projects/jdk8/), [JDK 8 Features](https://openjdk.org/projects/jdk8/features), [JDK 9](https://openjdk.org/projects/jdk9/), [JDK 10](https://openjdk.org/projects/jdk/10/), [JDK 11](https://openjdk.org/projects/jdk/11/), [JDK 14](https://openjdk.org/projects/jdk/14/), [JDK 15](https://openjdk.org/projects/jdk/15/), [JDK 16](https://openjdk.org/projects/jdk/16/), [JDK 17](https://openjdk.org/projects/jdk/17/), [JDK 21](https://openjdk.org/projects/jdk/21/), [JDK 22](https://openjdk.org/projects/jdk/22/), [JDK 24](https://openjdk.org/projects/jdk/24/), [JDK 25](https://openjdk.org/projects/jdk/25/), [JDK 26](https://openjdk.org/projects/jdk/26/)
- JEP: [126](https://openjdk.org/jeps/126), [213](https://openjdk.org/jeps/213), [261](https://openjdk.org/jeps/261), [266](https://openjdk.org/jeps/266), [269](https://openjdk.org/jeps/269), [286](https://openjdk.org/jeps/286), [320](https://openjdk.org/jeps/320), [322](https://openjdk.org/jeps/322), [323](https://openjdk.org/jeps/323), [330](https://openjdk.org/jeps/330), [358](https://openjdk.org/jeps/358), [361](https://openjdk.org/jeps/361), [378](https://openjdk.org/jeps/378), [394](https://openjdk.org/jeps/394), [395](https://openjdk.org/jeps/395), [400](https://openjdk.org/jeps/400), [403](https://openjdk.org/jeps/403), [409](https://openjdk.org/jeps/409), [431](https://openjdk.org/jeps/431), [440](https://openjdk.org/jeps/440), [441](https://openjdk.org/jeps/441), [444](https://openjdk.org/jeps/444), [454](https://openjdk.org/jeps/454), [456](https://openjdk.org/jeps/456), [458](https://openjdk.org/jeps/458), [485](https://openjdk.org/jeps/485), [491](https://openjdk.org/jeps/491), [506](https://openjdk.org/jeps/506), [511](https://openjdk.org/jeps/511), [512](https://openjdk.org/jeps/512), [513](https://openjdk.org/jeps/513)
- [JDK-8233014: Enable ShowCodeDetailsInExceptionMessages by default](https://bugs.openjdk.org/browse/JDK-8233014) — OpenJDK JBS
- JDK 21 Javadoc (Since 표기): [String](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/String.html), [Stream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html), [Optional](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html), [Files](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html), [List](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html), [Collectors](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html) — Oracle
- [Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes) — spring-projects wiki

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
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/) ← 지금 글
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
