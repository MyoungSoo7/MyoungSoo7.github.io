---
layout: post
title: "템플릿 메서드 vs 전략 패턴 — 스프링과 금융 정산 시스템에서 실제로 어디에 쓰이나"
date: 2026-07-28 00:05:00 +0900
categories: [Java, DesignPattern]
tags: [TemplateMethod, Strategy, GoF, Spring, SpringBatch, Settlement, Fintech, Java]
---

두 패턴은 사실 **같은 질문**에 대한 서로 다른 대답이다.

> "알고리즘 전체는 그대로 두고, 그중 일부만 바꿔 끼우려면 어떻게 해야 하나?"

템플릿 메서드는 **상속(inheritance)** 으로 답하고, 전략은 **합성(composition)** 으로 답한다. GoF 『Design Patterns』에서 둘은 5장 행위(behavioral) 패턴에 나란히 실려 있다 — Strategy가 p.315, Template Method가 p.325다.

이 글은 (1) 각 패턴의 원전 정의와 최소 예제, (2) JDK·스프링의 **공식 문서로 확인되는** 실제 사례, (3) 내가 운영 중인 정산(settlement) 시스템의 실제 코드, (4) 금융 도메인에서 이 둘이 특히 자주 나타나는 자리 — 순으로 정리한다.

---

# 1. 템플릿 메서드 패턴

## 정의 (원전)

GoF의 의도(Intent) 원문은 이렇다.

> "Define the skeleton of an algorithm in an operation, deferring some steps to subclasses. Template Method lets subclasses redefine certain steps of an algorithm without changing the algorithm's structure."
>
> — Gamma, Helm, Johnson, Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software* (Addison-Wesley, 1994), Template Method (p.325)

번역하면 **"알고리즘의 골격을 하나의 연산에 정의하고 일부 단계를 서브클래스로 미룬다. 템플릿 메서드는 서브클래스가 알고리즘의 구조를 바꾸지 않으면서 특정 단계만 재정의할 수 있게 한다."**

핵심 단어는 **골격(skeleton)** 과 **구조를 바꾸지 않으면서(without changing the algorithm's structure)** 다. 즉 템플릿 메서드가 통제하는 것은 **순서**다. 무엇을 하느냐는 서브클래스가 채우지만, **어떤 순서로 하느냐는 상위 클래스가 잠근다.**

## 구조

```
AbstractClass
 ├─ templateMethod()      ← final. 순서를 고정한다.
 │     step1();           ← 공통 구현 (상위가 직접)
 │     doStep2();         ← abstract. 서브클래스 필수 구현
 │     hookStep3();       ← hook. 기본 no-op, 선택적 override
 └─ ...
ConcreteClassA / ConcreteClassB  ← doStep2()만 다르게
```

세 종류의 메서드를 구분하는 게 중요하다.

| 종류 | 접근 제어 | 역할 |
|---|---|---|
| **템플릿 메서드** | `public final` / `protected final` | 순서 고정. **반드시 `final`** — 오버라이드되면 패턴이 무너진다 |
| **추상 훅(primitive operation)** | `protected abstract` | 서브클래스가 **반드시** 채워야 하는 구멍 |
| **선택 훅(hook)** | `protected` + 빈 구현 | 필요할 때만 override. 기본은 no-op |

## 최소 예제

```java
public abstract class ReportGenerator {

    /** 순서를 고정한다. final 이 이 패턴의 계약이다. */
    public final Report generate(ReportRequest request) {
        validate(request);                       // 공통
        RawData raw = fetch(request);            // ← 다름
        Report report = transform(raw);          // ← 다름
        afterGenerated(report);                  // ← 선택 훅
        return report;
    }

    private void validate(ReportRequest request) {
        if (request.from().isAfter(request.to())) {
            throw new IllegalArgumentException("조회 시작일이 종료일보다 늦습니다");
        }
    }

    protected abstract RawData fetch(ReportRequest request);

    protected abstract Report transform(RawData raw);

    /** 기본 no-op — 필요한 서브클래스만 채운다. */
    protected void afterGenerated(Report report) {
    }
}
```

`generate()`가 `final`이 아니면 서브클래스가 검증을 통째로 건너뛸 수 있다. 금융 도메인에서는 이 `final` 하나가 감사(audit) 요건이 되기도 한다.

## JDK 안의 템플릿 메서드

먼저 정직하게 밝힐 사실이 하나 있다. **JDK 공식 자바독은 이 패턴을 "template method"라는 이름으로 부르지 않는다.** JDK 21 소스 전체를 검색해도 GoF 의미의 "template method"라는 표현이 공개 API 문서에 등장하는 곳은 없다. 대신 JDK는 이 패턴을 **행위로 서술**한다 — "skeletal implementation(골격 구현)", "the programmer needs only to provide implementations for X", "There's no need to override this method". 아래 인용이 그 근거다.

**`java.util.AbstractList`** — "골격 구현"이라는 표현을 직접 쓴다.

> "This class provides a **skeletal implementation** of the List interface… To implement an unmodifiable list, the programmer needs only to extend this class and provide implementations for the `get(int)` and `size()` methods."
>
> — [Java SE 21 API, `java.util.AbstractList`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/AbstractList.html)

`get(int)`와 `size()` 두 개만 구현하면 `iterator()`·`indexOf()`·`equals()`가 전부 따라온다. 뒤집어 말하면 그 연산들의 **순서와 의미가 상위에 잠겨 있는** 것이다.

**`java.io.InputStream`** — 서브클래스가 채워야 할 원시 연산이 딱 하나다.

> "Applications that need to define a subclass of `InputStream` **must always provide a method that returns the next byte of input.**"
>
> — [Java SE 21 API, `java.io.InputStream`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/InputStream.html)

**`jakarta.servlet.http.HttpServlet`** — 가장 교과서적인 사례다. 골격은 오버라이드하지 말라고 **명시**되어 있다.

> "There's almost no reason to override the `service` method. `service` handles standard HTTP requests by dispatching them to the handler methods for each HTTP request type (the `do`XXX methods listed above)." … (protected `service`에 대해) "Receives standard HTTP requests from the public `service` method and dispatches them to the `do`XXX methods defined in this class. … **There's no need to override this method.**"
>
> — [Jakarta Servlet 6.1 API, `HttpServlet`](https://jakarta.ee/specifications/servlet/6.1/apidocs/jakarta.servlet/jakarta/servlet/http/httpservlet)

골격은 고정, `doGet`/`doPost`는 미뤄진 단계. 정확히 GoF의 정의 그대로다.

## 스프링 안의 템플릿 메서드

스프링은 JDK와 달리 **자바독에서 패턴 이름을 직접 부른다.**

**`AbstractPlatformTransactionManager`** — 스프링에서 이 패턴을 가장 크게 쓴 곳이다.

> "Subclasses have to implement specific **template methods** for specific states of a transaction, for example: begin, suspend, resume, commit, rollback. The most important of them are abstract and must be provided by a concrete implementation; for the rest, defaults are provided, so overriding is optional."
>
> — [Spring Framework 7.0.x Javadoc, `AbstractPlatformTransactionManager`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/support/AbstractPlatformTransactionManager.html)

`protected abstract`로 선언된 원시 연산은 `doGetTransaction()`, `doBegin()`, `doCommit()`, `doRollback()` 네 개. `doSuspend`·`doResume`·`doCleanupAfterCompletion`은 기본 구현이 있는 선택 훅이다. **트랜잭션 전파(propagation) 처리와 동기화라는 거대한 골격은 상위에 있고**, `JpaTransactionManager`와 `DataSourceTransactionManager`는 저 구멍만 채운다. 두 구현체가 전파 규칙에 대해 서로 다르게 굴 수 없는 이유가 이것이다.

**`AbstractController`** — 스프링 자바독 중 GoF 패턴 이름을 가장 직설적으로 부르는 곳이다.

> "Convenient superclass for controller implementations, using the **Template Method design pattern**." … (`handleRequestInternal`에 대해) "**Template method.** Subclasses must implement this."
>
> — [Spring Framework 7.0.x Javadoc, `AbstractController`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/servlet/mvc/AbstractController.html)

**`JdbcTemplate`** — 이름이 `~Template`으로 끝나는 스프링 클래스는 대개 **템플릿 메서드 + 콜백(callback)** 의 조합이다. 순수 GoF가 변하는 부분을 서브클래스로 미룬다면, 스프링은 그것을 **콜백 객체/람다**로 바꿔 상속 없이 같은 효과를 낸다.

> "`JdbcTemplate` is the central class in the JDBC core package. **It handles the creation and release of resources**, which helps you avoid common errors, such as forgetting to close the connection. It performs the basic tasks of the core JDBC workflow (such as statement creation and execution), **leaving application code to provide SQL and extract results.**"
>
> — [Spring Framework Reference, Using `JdbcTemplate`](https://docs.spring.io/spring-framework/reference/data-access/jdbc/core.html)

우리가 채우는 건 SQL과 `RowMapper` 뿐이고, **자원 해제와 예외 변환**은 골격이 강제한다. (참고로 "변하는 부분/변하지 않는 부분"이라는 표현은 내 프레이밍이지 스프링 문서의 용어는 아니다. 스프링 문서는 위처럼 "core JDBC workflow를 수행하고 SQL과 결과 추출만 애플리케이션에 남긴다"고 서술한다.)

**`TransactionTemplate`** 도 같은 계열이다.

> "The `TransactionTemplate` adopts the same approach as other Spring templates, such as the `JdbcTemplate`. It uses a callback approach (to free application code from having to do the boilerplate acquisition and release transactional resources) and results in code that is intention driven."
>
> — [Spring Framework Reference, Programmatic Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction/programmatic.html)

---

# 2. 전략 패턴

## 정의 (원전)

> "Define a family of algorithms, encapsulate each one, and make them interchangeable. Strategy lets the algorithm vary independently from clients that use it."
>
> — Gamma, Helm, Johnson, Vlissides, *Design Patterns* (1994), Strategy (p.315). 별칭(Also Known As)은 **Policy**.

**"알고리즘군을 정의하고 각각을 캡슐화해 서로 교체 가능하게 만든다. 전략 패턴은 알고리즘을 그것을 사용하는 클라이언트와 독립적으로 변화시킨다."**

핵심은 마지막 문장 — **독립적으로 변화(vary independently)** 다. 클라이언트 코드를 건드리지 않고 알고리즘을 늘리거나 바꿀 수 있어야 전략이다. `if/else`로 분기해 놓고 "전략 패턴"이라 부르는 코드는 알고리즘을 늘릴 때마다 클라이언트가 바뀌므로 전략이 아니다.

또 하나, 별칭이 **Policy** 라는 점을 기억해두면 좋다. 금융 코드에서 `~Policy`라는 이름을 만나면 십중팔구 전략 패턴이다.

## 구조

```
Context ──has-a──▶ Strategy(interface)
                      ├─ ConcreteStrategyA
                      ├─ ConcreteStrategyB
                      └─ ConcreteStrategyC
```

상속이 아니라 **필드**다. 이 차이가 실질적인 결과를 만든다 — 전략은 **런타임에 갈아끼울 수 있다.**

## 최소 예제

```java
public interface FeePolicy {
    Money calculate(Money amount);
}

public record RateFeePolicy(BigDecimal rate) implements FeePolicy {
    @Override public Money calculate(Money amount) {
        return amount.multiply(rate);
    }
}

public record FlatFeePolicy(Money flat) implements FeePolicy {
    @Override public Money calculate(Money amount) {
        return flat;
    }
}

/** 정률 + 정액 중 큰 쪽 — 전략은 조합해서 또 하나의 전략이 된다. */
public record MaxOfFeePolicy(FeePolicy a, FeePolicy b) implements FeePolicy {
    @Override public Money calculate(Money amount) {
        Money x = a.calculate(amount), y = b.calculate(amount);
        return x.compareTo(y) >= 0 ? x : y;
    }
}
```

마지막 `MaxOfFeePolicy`가 전략 패턴의 진짜 힘이다. 인터페이스가 얇으면 **전략끼리 조합해 새 전략을 만들 수 있다.** 상속 기반 템플릿 메서드로는 이게 안 된다.

## JDK 안의 전략

템플릿 메서드와 달리, **JDK는 전략 패턴만큼은 자바독에서 이름을 직접 부른다.** `java.time.temporal` 패키지가 그 사례다.

> "**Strategy for adjusting a temporal object.** Adjusters are a key tool for modifying temporal objects. They exist to externalize the process of adjustment, permitting different approaches, **as per the strategy design pattern.**"
>
> — [Java SE 21 API, `java.time.temporal.TemporalAdjuster`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/temporal/TemporalAdjuster.html) (같은 문장이 `TemporalQuery`, `TemporalAdjusters`, `TemporalQueries`, `TemporalAccessor.query()`에도 있다)

`TemporalAdjusters.next(DayOfWeek.MONDAY)`, `lastDayOfMonth()` 같은 것들이 전부 교체 가능한 전략 객체다. 뒤에 나올 정산 주기 코드에서 이걸 그대로 쓴다.

**`java.util.Comparator`** — 가장 유명한 사례. 정렬 알고리즘은 고정, 비교 규칙만 갈아끼운다.

> "A comparison function, which imposes a total ordering on some collection of objects. Comparators can be passed to a sort method (such as `Collections.sort` or `Arrays.sort`) **to allow precise control over the sort order.**"
>
> — [Java SE 21 API, `java.util.Comparator`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Comparator.html)

**`RejectedExecutionHandler`** — 스레드풀 포화 시 거절 정책. 자바독이 GoF의 별칭인 **"policies"** 라는 단어를 쓴다.

> "…the `execute` method invokes the `RejectedExecutionHandler.rejectedExecution` method of its `RejectedExecutionHandler`. **Four predefined handler policies are provided:** 1. In the default `AbortPolicy`, the handler throws a runtime `RejectedExecutionException` upon rejection. 2. In `CallerRunsPolicy`, the thread that invokes `execute` itself runs the task…"
>
> — [Java SE 21 API, `ThreadPoolExecutor`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html)

덧붙여 `ThreadPoolExecutor`는 **두 패턴이 한 클래스에 공존하는** 좋은 예다. 같은 문서에 "Hook methods" 절이 따로 있고, `beforeExecute`/`afterExecute`/`terminated`를 오버라이드하라고 안내한다. 실행 골격은 템플릿 메서드, 거절 정책·스레드 팩토리는 주입되는 전략이다.

## 스프링 안의 전략

스프링은 아예 **자바독 첫 줄을 "Strategy interface for …"로 시작하는 관례**가 있다. 스프링 코드베이스를 읽을 때 이 문구를 grep하면 확장 지점이 그대로 나온다. 실제로 확인한 것들만 옮기면:

| 타입 | 자바독 첫 줄 |
|---|---|
| `org.springframework.util.PathMatcher` | "**Strategy interface for** `String`-based path matching." |
| `beans.factory.support.BeanNameGenerator` | "**Strategy interface for** generating bean names for bean definitions." |
| `core.io.support.PropertySourceFactory` | "**Strategy interface for** creating resource-based PropertySource wrappers." |
| `web.multipart.MultipartResolver` | "**A strategy interface for** multipart file upload resolution in accordance with RFC 1867." |
| `batch.item.ItemReader` | "**Strategy interface for** providing the data." |
| `retry.backoff.BackOffPolicy` | "**Strategy interface** to control back off between attempts in a single retry operation." |

반대로 **흔히 "전략 패턴"이라고 소개되지만 자바독에 그 표현이 없는** 것들도 있다. 정확히 하자면 이렇다.

- `PlatformTransactionManager` — 첫 줄은 아니지만 본문에 "A classic implementation of **this strategy interface** is `JtaTransactionManager`" 가 있다. 전략이 맞다.
- `TaskExecutor` — "Implementations can use all sorts of different execution **strategies**, such as: synchronous, asynchronous, using a thread pool" — 역할은 전략이지만 "Strategy interface"라고 선언하진 않는다.
- `InstantiationStrategy` — "This is **pulled out into a strategy** as various approaches are possible, including using CGLIB…" — 이름부터 전략이다.
- `HandlerMapping`, `ViewResolver`, `SkipPolicy`, `ItemProcessor`, `ItemWriter` — 설계상 전략이지만 자바독은 그냥 "Interface to be implemented by…" 식으로만 쓴다. 남의 글에서 "스프링 공식 문서가 전략 패턴이라고 부른다"고 하면 한 번쯤 확인해볼 만하다.

**`PasswordEncoder` / `DelegatingPasswordEncoder`** 는 별도로 짚을 가치가 있다. (`PasswordEncoder` 자바독은 "Service interface for encoding passwords"라고만 쓴다 — "Strategy interface"가 아니다. 그래도 동작은 전형적인 전략이다.)

> "A password encoder that **delegates to another `PasswordEncoder` based upon a prefixed identifier**." … "The general format for a password is: `{id}encodedPassword` … `id` is an identifier that is used to look up which `PasswordEncoder` should be used."
>
> — [Spring Security 7.0 Javadoc, `DelegatingPasswordEncoder`](https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/crypto/password/DelegatingPasswordEncoder.html) / [Reference, Password Storage](https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html)

저장된 해시에 알고리즘 식별자가 박혀 있으니, `{bcrypt}` → `{argon2}` 로 정책을 바꿔도 옛 비밀번호가 그대로 검증된다. 전략 패턴이 **무중단 마이그레이션 도구**로 쓰이는 좋은 예다. 금융에서 암호화·해시 알고리즘 교체는 규정 변경으로 주기적으로 발생하는 일이라, 이 구조를 직접 흉내 낼 일이 생각보다 많다.

## 두 패턴이 한 API에 같이 있는 경우

실무에서 더 흔한 건 순수한 단일 패턴이 아니라 **골격은 템플릿 메서드, 구멍은 전략**인 조합이다. 스프링 자바독에 그게 한 문장으로 드러난 곳이 있다.

> "This template uses a `SimpleDestinationResolver` and a `SimpleMessageConverter` **as default strategies** for resolving a destination name or converting a message, respectively. **These defaults can be overridden** through the "destinationResolver" and "messageConverter" bean properties."
>
> — [Spring Framework 7.0.x Javadoc, `JmsTemplate`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/jms/core/JmsTemplate.html)

Spring Retry의 `RetryTemplate`도 같다 — 재시도 루프라는 골격은 템플릿이 쥐고, `RetryPolicy`와 `BackOffPolicy`를 세터로 갈아끼운다.

---

# 3. 실제 코드 — 금융 정산 시스템에서

여기부터는 내가 운영 중인 정산(settlement) 시스템의 **실제 코드**다. 개념 예제가 아니라, 왜 그렇게 짰는지의 기록이다.

## 3-1. 템플릿 메서드 — 멱등 이벤트 컨슈머

정산 시스템의 Kafka 컨슈머는 전부 다음 순서를 지켜야 한다.

```
event_id 헤더 추출 → processed_events 멱등 체크 → JSON 파싱(실패 시 DLT)
  → 도메인 처리 → 멱등 마커 저장 → ack
```

문제는 컨슈머가 늘어날 때마다 이 preamble을 복붙한다는 것이었다. **한 번이라도 멱등 체크를 빠뜨리면 정산이 이중 생성된다.** 그래서 골격을 상위로 올렸다.

```java
public abstract class IdempotentEventConsumer {

    /** 서브클래스가 채우는 구멍은 세 개뿐. */
    protected abstract String consumerGroup();
    protected abstract String eventType();
    protected abstract void handle(JsonNode payload, UUID eventId);

    /** 기본 no-op 선택 훅 — 프로젝션 지연 메트릭 같은 부수효과용. */
    protected void afterProcessed(ConsumerRecord<String, String> record) {
    }

    /** 공통 멱등 처리 골격. final 이라 서브클래스가 순서를 못 바꾼다. */
    protected final void consume(ConsumerRecord<String, String> record, Acknowledgment ack) {
        ExtractedEventId extracted = extractEventId(record);
        if (extracted.eventId() == null) { /* 격리 기록 후 ack */ }

        UUID eventId = extracted.eventId();
        var key = new ProcessedEventJpaEntity.ProcessedEventId(consumerGroup(), eventId);
        if (processedEventRepository.existsById(key)) {
            log.info("이미 처리된 이벤트 스킵. group={}, eventId={}", consumerGroup(), eventId);
            ack.acknowledge();
            return;                                   // ← 멱등 방어 2단계
        }

        JsonNode payload;
        try {
            payload = objectMapper.readTree(record.value());
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Invalid JSON payload, eventId=" + eventId, e);
        }

        handle(payload, eventId);                     // ← 서브클래스 몫
        // ... 멱등 마커 저장 → afterProcessed → ack
    }
}
```

여기서 얻는 것은 코드 재사용이 아니라 **불변식의 구조적 강제**다. 새 컨슈머를 추가하는 개발자는 멱등 체크를 "잊을 수" 없다. 잊을 자리가 없기 때문이다.

주석에 **비대상(non-goal)** 을 명시해둔 것도 의도적이다.

> "practice-delay 토글·순서역전 처리 등 컨슈머 고유 로직이 큰 경우는 `handle` 안에서 처리하거나 이 골격을 상속하지 않는다(억지로 끼워 맞추지 않는다)."

템플릿 메서드가 실패하는 가장 흔한 경로가 **"골격에 안 맞는 케이스를 훅을 늘려 우겨넣는 것"** 이다. 훅이 늘수록 골격은 골격이 아니게 된다.

## 3-2. 템플릿 메서드 — 재고 차감의 동시성 골격

일반 상품과 옵션(SKU)은 대상 테이블만 다를 뿐, **초과판매를 막는 순서**는 완전히 같다.

```java
public abstract class AbstractDecreaseStockService<T> {

    protected abstract int decreaseStockIfAvailable(Long id, int quantity); // 원자적 조건부 UPDATE
    protected abstract Optional<T> reload(Long id);
    protected abstract RuntimeException notFound(Long id);
    protected abstract RuntimeException classifyPresent(T current, Long id, int quantity);

    protected final T doDecrease(Long id, int quantity) {
        if (quantity <= 0) throw new ProductInvariantViolationException("차감 수량은 양수여야 합니다");

        T result = transactionTemplate.execute(status -> {
            int affected = decreaseStockIfAvailable(id, quantity);
            if (affected == 0) throw classifyFailure(id, quantity);   // 재고부족/단종 분류
            return reload(id).orElseThrow(() -> new IllegalStateException("재고 차감 후 대상 사라짐"));
        });
        successCounter.increment();
        return result;
    }

    private RuntimeException classifyFailure(Long id, int quantity) {
        rejectedCounter.increment();
        T current = reload(id).orElse(null);
        return current == null ? notFound(id) : classifyPresent(current, id, quantity);
    }
}
```

주목할 점: 골격 안에 **`TransactionTemplate`** 과 **Micrometer 카운터**가 들어 있다. 즉 이 템플릿 메서드가 고정하는 건 비즈니스 순서만이 아니라 **트랜잭션 경계와 관측(observability) 지점**이기도 하다. 두 서비스의 성공/거절 카운터가 서로 다른 시점에 증가하는 사고가 구조적으로 불가능해진다.

## 3-3. 전략 — 정산 주기 (enum 전략)

정산 주기는 셀러 등급마다 다르다. 매일 / 매주 월요일 / 매월 말일 / T+1 / T+3 / T+7 영업일.

`if (cycle.equals("T_PLUS_1")) ... else if ...` 로 짜면 주기를 추가할 때마다 호출부가 전부 바뀐다. 그래서 **enum 상수별 메서드 구현(constant-specific method implementation)** 으로 전략을 넣었다. 앞서 본 `TemporalAdjusters`(JDK가 스스로 "strategy design pattern"이라 부르는 것)를 그대로 쓴다.

```java
public enum SettlementCycle {
    DAILY {
        @Override public LocalDate resolveSettlementDate(LocalDate paymentDate) {
            return paymentDate.plusDays(1);
        }
    },
    WEEKLY_MON {
        @Override public LocalDate resolveSettlementDate(LocalDate paymentDate) {
            return paymentDate.with(TemporalAdjusters.next(DayOfWeek.MONDAY));
        }
    },
    MONTHLY_LAST {
        @Override public LocalDate resolveSettlementDate(LocalDate paymentDate) {
            return paymentDate.with(TemporalAdjusters.lastDayOfMonth());
        }
    },
    T_PLUS_1 {
        @Override public LocalDate resolveSettlementDate(LocalDate paymentDate) {
            return BusinessDayCalculator.addBusinessDays(paymentDate, 1);   // 주말·공휴일 skip
        }
    },
    T_PLUS_3 { /* ... 3 영업일 ... */ },
    T_PLUS_7 { /* ... 7 영업일 ... */ };

    public abstract LocalDate resolveSettlementDate(LocalDate paymentDate);
}
```

호출부는 이 한 줄로 끝난다.

```java
LocalDate settlementDate = cycle.resolveSettlementDate(payment.paidAt().toLocalDate());
```

새 주기(예: `T_PLUS_2`)를 추가해도 **호출부는 한 글자도 바뀌지 않는다.** 이것이 GoF가 말한 "독립적으로 변화"다.

**enum 전략의 장단점**은 분명하다.

| | enum 전략 | 인터페이스 + 스프링 빈 전략 |
|---|---|---|
| 전략 집합 | **닫혀 있음**(컴파일 타임 고정) | 열려 있음 |
| 의존성 주입 | 어려움 (static 접근) | 자연스러움 |
| 직렬화·DB 저장 | 이름 그대로 저장 가능 | 별도 매핑 필요 |
| `switch` 완전성 검사 | 컴파일러가 도와줌 | 없음 |

정산 주기는 **금융 규정상 임의로 늘어나지 않고**, DB 컬럼(`users.settlement_cycle`)에 문자열로 저장되며, 외부 의존성이 없다. 이 세 조건이 맞으면 enum 전략이 인터페이스보다 낫다. 반대로 외부 API를 호출해야 하는 전략(환율 조회, 심사 엔진)은 반드시 인터페이스 + 스프링 빈으로 가야 한다.

## 3-4. 전략을 데이터로 — 등급이 정책의 단일 출처

한 걸음 더 나아가, 등급(`SellerTier`)이 **수수료율·정산주기·홀드백을 한꺼번에 들고 있게** 했다.

```java
public enum SellerTier {
    /** 기본 등급 — 3.5% 수수료, T+7 영업일 정산, 30% 30일 홀드백. */
    NORMAL   ("0.0350", SettlementCycle.T_PLUS_7, "0.30", 30),
    /** VIP — 2.5% 수수료, T+3 영업일 정산. */
    VIP      ("0.0250", SettlementCycle.T_PLUS_3, "0.10", 14),
    /** STRATEGIC — 2.0% 수수료, T+1 영업일 정산, 홀드백 없음. */
    STRATEGIC("0.0200", SettlementCycle.T_PLUS_1, "0",    0);
    // ...
}
```

전략을 **선택하는 규칙**까지 한 곳에 모은 셈이다. "VIP는 수수료 몇 %였지?"를 코드베이스 세 군데에서 찾아야 하는 상황이 사라진다.

---

# 4. 금융 도메인에서 이 둘이 자주 나타나는 자리

금융 백엔드(정산·결제·여신·자산관리)에서 두 패턴이 반복적으로 나타나는 자리를 정리하면 이렇다. 요약하면 — **템플릿 메서드는 "절차"를, 전략은 "요율·규칙"을 담당한다.**

## 템플릿 메서드가 쓰이는 자리 = 절차가 규정된 곳

| 자리 | 왜 템플릿 메서드인가 |
|---|---|
| **일 마감 배치 (EOD)** | 대사(reconciliation) → 확정 → 전표 생성 → 리포트. 순서를 바꾸면 회계가 틀어진다 |
| **원장 전기(posting)** | 차변/대변 균형 검증 → 기표 → 잔액 갱신 → 감사로그. 검증 없는 기표 경로가 존재하면 안 됨 |
| **이벤트 컨슈머 멱등 처리** | 위 3-1. 멱등 체크를 "빠뜨릴 자리"를 없앤다 |
| **외부 기관 연동 (PG·은행)** | 전문 조립 → 서명/암호화 → 전송 → 응답 검증 → 감사 기록. 서명 단계 생략 불가 |
| **승인/취소 트랜잭션 흐름** | 한도 체크 → 예약 → 승인 요청 → 확정/보상. 보상 트랜잭션 누락 방지 |

공통점은 **"이 순서를 지키지 않으면 돈이 틀어지는" 절차**라는 것이다. 금융에서 `final` 템플릿 메서드는 방어적 프로그래밍이 아니라 **통제(control)** 다. 감사 대응 시 "이 검증을 우회하는 코드 경로가 존재하지 않음"을 타입 수준에서 보일 수 있다.

Spring Batch가 금융권에서 압도적으로 쓰이는 이유도 같은 맥락이다. chunk-oriented step은 read → process → write → commit 이라는 골격을 **프레임워크가 잠가버린** 템플릿 메서드다. 공식 문서의 서술은 이렇다.

> "Chunk oriented processing refers to reading the data one at a time and creating 'chunks' that are written out within a transaction boundary. **Once the number of items read equals the commit interval, the entire chunk is written out by the `ItemWriter`, and then the transaction is committed.**"
>
> — [Spring Batch Reference, Chunk-oriented Processing](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html)

같은 문서가 그 골격의 의사코드까지 공개한다. 즉 **루프의 형태 자체가 프레임워크의 계약**이다.

```java
List items = new Arraylist();
for (int i = 0; i < commitInterval; i++) {
    Object item = itemReader.read();
    if (item != null) { items.add(item); }
}
itemWriter.write(items);
```

실제 정산 확정 잡도 이 구조다.

```java
@Bean
public Step confirmSettlementStep(JobRepository jobRepository,
                                  PlatformTransactionManager transactionManager,
                                  SettlementConfirmItemReader reader,
                                  SettlementConfirmProcessor processor,
                                  SettlementConfirmItemWriter writer,
                                  @Value("${app.settlement.confirm.chunk-size:100}") int chunkSize) {
    return new StepBuilder(STEP_NAME, jobRepository)
            .<Settlement, Settlement>chunk(chunkSize)
            .transactionManager(transactionManager)
            .reader(reader)          // ← 전략 ("Strategy interface for providing the data")
            .processor(processor)    // ← 전략
            .writer(writer)          // ← 전략
            .build();
}
```

과거엔 하루치를 단일 Tasklet 트랜잭션으로 처리했는데, 청크로 바꾸면서 **롱 트랜잭션과 비관적 락 보유 시간이 chunk 단위로 제한**됐다. 한 청크가 실패해도 이전 청크 커밋은 살아남고 Job은 FAILED로 남아 재시작된다. 골격을 프레임워크가 쥐고 있으니 얻는 이득이다.

> **한 코드에 두 패턴이 동시에 있는 전형이다.** Step의 실행 골격은 템플릿 메서드, `reader`/`processor`/`writer`는 주입되는 전략. 실무에서는 이 조합이 순수한 단일 패턴보다 훨씬 흔하다.
>
> (버전 주의: `StepBuilder.chunk(int, PlatformTransactionManager)` 오버로드는 Spring Batch 6.0에서 `@Deprecated(forRemoval=true)`로 표시됐다. 위 코드는 `.chunk(n).transactionManager(tx)` 형태의 5.x 스타일이다.)

## 전략이 쓰이는 자리 = 요율·규칙이 바뀌는 곳

| 자리 | 전략으로 뽑는 것 |
|---|---|
| **수수료 계산** | 정률/정액/구간별/최소·최대 캡. 가맹점·상품·채널별로 다름 |
| **정산 주기** | 위 3-3. T+1 / T+3 / 월말 |
| **이자 계산** | 단리/복리, 일할/월할, 일수 계산 관행(30/360, ACT/365, ACT/ACT) |
| **라운딩** | 통화별·산출물별. 부가세는 원단위 절사, 통화 환산은 다른 규칙 |
| **세금·원천징수** | 사업자 유형·거주자 여부·조세조약별 |
| **결제수단별 처리** | 카드/계좌이체/간편결제/포인트 — 취소·부분취소 규칙이 전부 다름 |
| **한도·리스크 정책** | 등급별 일일한도·건당한도·홀드백 |
| **FDS 룰** | 룰 하나하나가 교체·조합 가능한 전략 |
| **재시도·백오프** | 일시적 오류 vs 독성 메시지 |
| **환율 적용** | 매매기준율/전신환/고시시점 |
| **비밀번호·민감정보 해시** | 알고리즘 교체 시 `DelegatingPasswordEncoder` 방식 |

여기서 **라운딩**은 특히 금융다운 사례다. 정산 시스템에서 세무 금액은 공용 `Money` VO의 통화 라운딩(scale 2, `HALF_UP`)과 **의도적으로 분리**했다.

```java
/**
 * 세무 전용 라운딩 정책 — 원단위 절사(1원 미만 버림).
 * 공용 Money 의 scale 2 HALF_UP 을 통과시키면 반올림이 먼저 개입해
 * 세무 절사 의미가 손상되므로, 곱셈 원값에 이 정책을 직접 적용한다.
 */
public final class TaxRounding {
    public static BigDecimal floorToWon(BigDecimal amount) {
        // ... null·음수 검증 ...
        return amount.setScale(0, RoundingMode.DOWN);
    }
}
```

**라운딩을 "전략"으로 인식하지 못하면 1원 오차가 쌓여 대사(reconciliation)가 안 맞는다.** 금융 코드에서 `RoundingMode`가 암묵적 기본값으로 결정되고 있다면 그건 대개 버그다.

재시도도 전략이다. 정산 서비스의 Kafka 에러 핸들러는 예외 종류에 따라 다른 전략을 태운다.

```java
// 일시적 예외(DB lock timeout, IO) → FixedBackOff 로 재시도
// 독성 메시지(JSON 파싱 실패)      → 재시도 없이 즉시 DLT
DefaultErrorHandler handler = new DefaultErrorHandler(recoverer, new FixedBackOff(2_000L, 3L));
handler.addNotRetryableExceptions(JsonProcessingException.class, IllegalArgumentException.class);
```

Spring Kafka의 `DefaultErrorHandler` 기본값은 즉시 9회 재시도 후 recoverer로 넘기는 것이라, recoverer를 지정하지 않으면 사실상 조용히 로그만 남기고 넘어간다. 정산에서는 이게 메시지 유실이다. 백오프 전략과 "재시도 대상 아님" 분류, 그리고 DLT 발행 recoverer를 명시적으로 갈아끼운 이유다.

## 금융에서 특히 중요한 것 — 전략의 "스냅샷"

전략 패턴을 금융에 쓸 때 가장 자주 틀리는 지점이 있다. 디자인 패턴 책에는 안 나오는 이야기다.

> **계산 시점의 전략(요율)을 저장하지 않으면, 나중에 재계산했을 때 값이 달라진다.**

수수료율을 매번 `SellerTier.NORMAL.rate()`로 조회하면, 등급 정책이 3.0% → 3.5%로 바뀌는 순간 **과거 정산의 재계산 결과가 바뀐다.** 회계·감사에서 치명적이다.

그래서 정산 테이블에는 `commission_rate` 컬럼이 있다. 정산 생성 시점의 요율을 **스냅샷으로 박아둔다.** 전략은 "이번에 어떤 값을 쓸지"를 정할 뿐이고, 그 결과는 불변 레코드로 남아야 한다.

같은 원리가 정산 주기·홀드백·세율에도 적용된다. **금융에서 전략 패턴은 "현재 정책"을 계산하는 데 쓰고, 계산 결과는 반드시 시점 고정해 저장한다.**

---

# 5. 언제 무엇을 쓰나

| | 템플릿 메서드 | 전략 |
|---|---|---|
| 확장 수단 | 상속 (is-a) | 합성 (has-a) |
| 바꾸는 것 | 알고리즘의 **일부 단계** | 알고리즘 **전체** |
| 교체 시점 | **컴파일 타임** (클래스 고정) | **런타임** 교체 가능 |
| 조합 | 불가 (단일 상속) | 가능 (전략끼리 조합·데코레이트) |
| 결합도 | 높음 (상위 클래스 변경이 전파) | 낮음 |
| 테스트 | 서브클래스를 만들어야 함 | 가짜 전략 주입으로 끝 |
| GoF 분류 | 클래스 패턴 (상속) | 객체 패턴 (합성) |

**판단 기준을 한 줄로:**

- **순서가 핵심이고, 바뀌는 건 몇 단계뿐** → 템플릿 메서드
- **한 단계가 통째로 여러 버전이고, 늘어날 예정** → 전략

**전략 쪽으로 기울여야 하는 신호**
- 서브클래스가 5개를 넘어가기 시작한다
- 훅이 계속 늘어난다 (골격이 골격이 아니게 되는 중)
- 조합이 필요하다 (A 방식 + B 방식)
- 런타임 설정으로 바꿔야 한다
- 단위 테스트에서 서브클래스를 계속 만들고 있다

**템플릿 메서드를 유지해야 하는 신호**
- 순서 자체가 요구사항이다 (감사·규정)
- 변형이 2~3개로 닫혀 있다
- 훅이 서로 **의존적**이다 (앞 단계 결과를 뒤 단계가 쓴다)

## 주의할 점

**템플릿 메서드의 함정**

1. **`final`을 안 붙인 템플릿 메서드** — 오버라이드되는 순간 통제가 사라진다.
2. **훅 폭발** — 훅이 7~8개가 되면 이미 전략으로 갈아탈 시점을 놓친 것이다.
3. **깊은 상속** — 3단계 이상 상속하면 "어디서 뭘 하는지"를 아무도 모른다. "상속보다 합성"은 여기에도 적용된다.
4. **`protected` 남발** — 훅은 계약이다. `protected`로 노출한 순간 서브클래스가 의존하는 API가 되고 함부로 못 바꾼다.

**전략의 함정**

1. **전략이 하나뿐인데 인터페이스부터 만드는 것** — YAGNI. 두 번째가 나타날 때 뽑아도 늦지 않다.
2. **인터페이스가 두꺼운 것** — 메서드가 5개면 조합도 대체도 안 된다. 전략 인터페이스는 얇을수록 강하다.
3. **전략 선택 로직이 흩어지는 것** — 전략을 고르는 `if`가 여러 곳에 생기면 원래 문제로 돌아온 것이다. 팩토리나 `Map<Key, Strategy>` 한 곳으로 모은다. (스프링이라면 `Map<String, FeePolicy>` 주입으로 빈 이름 기반 조회가 깔끔하다.)
4. **상태를 가진 전략** — 전략은 가급적 무상태·불변으로. 싱글턴 빈으로 공유될 때 스레드 안전 문제가 생긴다. 스프링 문서가 `TransactionTemplate`에 대해 "instances do not maintain any conversational state"라고 굳이 명시하는 이유다.

---

# 6. 닫으며

두 패턴을 외워야 할 이유는 사실 없다. 실무에서 중요한 건 그 아래에 있는 **하나의 원칙**이다.

> **변하는 것과 변하지 않는 것을 분리하고, 변하지 않는 쪽이 변하는 쪽을 통제하게 한다.**

금융 백엔드에서 이 원칙은 특히 구체적인 형태를 띤다.

- **변하지 않는 것 = 절차** → 템플릿 메서드로 잠근다. 규정 준수의 문제다.
- **변하는 것 = 요율과 규칙** → 전략으로 뽑는다. 비즈니스 변경 속도의 문제다.
- 그리고 **계산에 쓴 정책은 결과와 함께 시점 고정해 저장한다.** 감사 가능성의 문제다.

세 번째는 GoF 책에 안 나오지만, 금융 도메인에서는 앞의 둘만큼 중요하다.

---

## References

**패턴 원전**

- Gamma, E., Helm, R., Johnson, R., Vlissides, J. *Design Patterns: Elements of Reusable Object-Oriented Software.* Addison-Wesley, 1994 — Strategy(p.315) / Template Method(p.325) 의도(Intent) 원문. 인용문은 서로 독립적인 4개 재수록본(대학 호스팅 원문 사본 2건, Addison-Wesley 『Design Patterns Smalltalk Companion』(1998), 학술 강의자료 1건)에서 문자 단위로 일치함을 확인했다. **단, 원서 실물이나 출판사 페이지로는 대조하지 못했다.**

**JDK 공식 자바독 (Java SE 21)**

- [`java.util.AbstractList`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/AbstractList.html) — "skeletal implementation"
- [`java.io.InputStream`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/InputStream.html)
- [`java.util.Comparator`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Comparator.html)
- [`java.util.concurrent.ThreadPoolExecutor`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html) — "Four predefined handler policies" / "Hook methods"
- [`java.time.temporal.TemporalAdjuster`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/temporal/TemporalAdjuster.html) — "as per the strategy design pattern"
- [Jakarta Servlet 6.1 `HttpServlet`](https://jakarta.ee/specifications/servlet/6.1/apidocs/jakarta.servlet/jakarta/servlet/http/httpservlet)

**스프링 공식 문서·자바독**

- [Spring Framework Reference — Using `JdbcTemplate`](https://docs.spring.io/spring-framework/reference/data-access/jdbc/core.html)
- [Spring Framework Reference — Programmatic Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction/programmatic.html)
- [Javadoc `AbstractPlatformTransactionManager`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/support/AbstractPlatformTransactionManager.html) — "Subclasses have to implement specific template methods"
- [Javadoc `AbstractController`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/servlet/mvc/AbstractController.html) — "using the Template Method design pattern"
- [Javadoc `PathMatcher`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/util/PathMatcher.html) · [`MultipartResolver`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/multipart/MultipartResolver.html) · [`JmsTemplate`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/jms/core/JmsTemplate.html)
- [Spring Batch Reference — Chunk-oriented Processing](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html) · [Commit Interval](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/commit-interval.html)
- [Spring Security Reference — Password Storage](https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html) · [Javadoc `DelegatingPasswordEncoder`](https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/crypto/password/DelegatingPasswordEncoder.html)
- [Spring Retry Javadoc — `BackOffPolicy`](https://docs.spring.io/spring-retry/docs/current/apidocs/spring.retry/org/springframework/retry/backoff/BackOffPolicy.html) — "Strategy interface to control back off"

*출처 등급과 한계: 패턴 정의는 GoF 원전(1994)의 의도 원문을, JDK·스프링 사례는 전부 공식 자바독 또는 공식 레퍼런스 문서를 직접 인용했다. 인용문은 확인 시점 기준이며, 스프링의 `docs.spring.io/.../current/` 경로는 버전 고정 URL이 아니라 시간이 지나면 내용이 바뀔 수 있다(확인 시점: Spring Framework 7.0.x / Spring Batch 5.2·6.0 / Spring Security 7.0 / Spring Retry 2.0.x). "JDK 자바독에 GoF 의미의 'template method'라는 표현이 없다"는 것은 JDK 21 소스 전수 검색 결과이며, 스프링 **레퍼런스 매뉴얼** 전체에 해당 표현이 있는지는 전수 확인하지 못했다(자바독에서는 확인됨). 3장·4장의 코드와 설계 판단(정산 주기·홀드백·라운딩·스냅샷)은 본인이 운영 중인 정산 시스템의 실제 소스이며, 특정 금융기관의 표준이나 업계 일반 관행을 대표한다고 주장하지 않는다. 이자 일수 계산 관행(30/360 등)·세무 절사 규칙은 국가·상품별로 다르므로 실제 적용 시 해당 규정을 확인해야 한다. 성능 벤치마크 주장은 이 글에 포함하지 않았다.*
