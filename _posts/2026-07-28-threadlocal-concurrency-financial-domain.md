---
layout: post
title: "*금융 도메인의 ThreadLocal 과 동시성* — *필드 동기화* 로 푸는 것, *스레드 격리* 로만 풀리는 것, 그리고 *스레드풀 오염* 이라는 사고"
date: 2026-07-28 09:00:00 +0900
categories: [java, spring, concurrency]
tags: [ThreadLocal, Concurrency, Spring, JMM, happens-before, ScopedValue, VirtualThreads, MDC, TaskDecorator, Finance]
---

# 금융에서 동시성 버그는 "느려짐"이 아니라 "사고"다

일반적인 웹 서비스에서 동시성 버그의 최악은 대개 **화면이 잠깐 이상해지는 것**이다. 금융 도메인은 다르다. 같은 버그가

- 계좌 A 의 이체가 **고객 B 의 거래ID 로 감사로그에 남고**,
- 승인 응답 전문의 금액 문자열이 `1,00.00` 처럼 **깨진 채 가맹점에 나가고**,
- 요청 스레드가 재사용되면서 **직전 고객의 인증 컨텍스트가 다음 요청에 그대로 보이는**

형태로 나타난다. 마지막 것은 성능 문제가 아니라 **정보 유출 사고**다. 그리고 이 세 가지는 전부 *같은 뿌리* — **"어떤 상태를 공유하고, 어떤 상태를 격리할 것인가"를 명시적으로 결정하지 않은 코드** — 에서 나온다.

이 글은 그 결정을 두 축으로 정리한다.

- **축 A. 필드 동기화** — *공유해야 하는* 상태를 여러 스레드가 안전하게 보게 만드는 법 (`volatile` / `synchronized` / `Atomic*` / `LongAdder`)
- **축 B. ThreadLocal** — *공유하면 안 되는* 상태를 스레드 단위로 **격리**하는 법

그리고 금융 코드에서 실제로 사고를 만드는 **주의사항 6가지**와, JDK 25 에서 정식 API 가 된 **ScopedValue** 로의 이전까지 다룬다.

---

## 0. 먼저, 두 축을 가르는 한 장의 표

상태를 만났을 때 물어야 할 질문은 하나다. **"이 값은 요청들 사이에 공유되어야 하는가?"**

| 상태의 성격 | 예 (금융) | 올바른 처방 | 틀린 처방 |
|---|---|---|---|
| 요청마다 다르고, 공유되면 **안 되는** 것 | 거래ID·멱등키·채널·인증 주체 | **격리**: 메서드 파라미터 → 안 되면 `ThreadLocal` / `ScopedValue` | 싱글톤 빈의 필드 |
| 프로세스 전체가 공유하고, **읽기만** 하는 것 | 수수료 정책 테이블(부팅 시 로드) | 불변 객체 + `final` (안전 발행) | 아무 동기화 |
| 프로세스 전체가 공유하고, **쓰기도** 하는 것 | 승인 건수 카운터·서킷브레이커 상태 | `volatile` / `Atomic*` / `LongAdder` | 그냥 `long` 필드 |
| **여러 인스턴스**가 공유하는 것 | 계좌 잔액·한도·재고 | **DB** (비관/낙관 락) 또는 분산 락 | `synchronized` |
| 스레드마다 하나 있으면 되는 **비싼 도구** | `DecimalFormat`, `Mac`(전문 MAC) | 지역 변수 / 불변 대안 / (신중히) `ThreadLocal` | 싱글톤 빈의 필드 |

마지막 행 두 개가 특히 중요하다. **잔액을 `synchronized` 로 지키는 코드는 파드가 2개가 되는 순간 무너진다.** 이건 예전 글([낙관적 락 vs 분산 락]({% post_url 2026-06-05-optimistic-lock-vs-distributed-lock-when-which %}))에서 따로 다뤘으니, 이 글은 **단일 JVM 안의 문제**에 집중한다.

---

# Part 1. 축 A — 필드 동기화 (공유 상태)

## 1.1 Spring 싱글톤 빈의 필드는 사실상 전역 변수다

Spring 의 기본 스코프는 싱글톤이다. 공식 레퍼런스는 이 스코프를 "컨테이너당·빈당 하나의 인스턴스"로 정의하고, **"상태를 가지는 빈은 prototype, 무상태 빈은 singleton 을 쓰라"** 고 규칙으로 명시한다([Spring Framework Reference — Bean Scopes](https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html)).

바꿔 말하면 — **`@Service` 클래스에 인스턴스 필드를 하나 선언하는 순간, 그 필드는 톰캣 워커 스레드 200개가 동시에 만지는 전역 변수가 된다.**

금융 코드에서 가장 흔한 실제 사고 형태는 "잔액을 필드에 담는" 초보적 실수가 아니라, **포매터를 필드에 담는 것**이다.

```java
@Service
public class SettlementReportService {

    // ❌ 싱글톤 빈의 필드 = 모든 요청 스레드가 공유
    private final DecimalFormat amountFormat = new DecimalFormat("#,##0.00");

    public String renderAmount(BigDecimal amount) {
        return amountFormat.format(amount);
    }
}
```

`final` 이니까 안전해 보이지만 아니다. `final` 은 **참조**가 안 바뀐다는 뜻일 뿐, **객체 내부 상태**는 `format()` 호출 중에 계속 변한다. `DecimalFormat` 의 javadoc 은 이 점을 못 박아둔다.

> Decimal formats are generally **not synchronized**. It is recommended to create separate format instances for each thread. If multiple threads access a format concurrently, it must be synchronized externally.
> — [DecimalFormat (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/text/DecimalFormat.html)

`SimpleDateFormat` 도 동일하며, javadoc 은 아예 **불변·스레드안전한 `DateTimeFormatter` 를 쓰라고 권고**한다([SimpleDateFormat](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/text/SimpleDateFormat.html)).

동시 호출이 겹치면 결과 문자열이 **조용히 깨진다.** 예외가 안 난다는 게 최악이다 — `1,234.00` 이 나와야 할 자리에 `1,21,34.00` 같은 값이 나오고, 그게 정산 파일이나 승인 응답 전문으로 나간 뒤 **대사(對査) 단계에서야** 발견된다.

**처방은 세 가지 중 하나다.**

```java
// ① 지역 변수 — 가장 단순하고, 대부분의 경우 정답
public String renderAmount(BigDecimal amount) {
    return new DecimalFormat("#,##0.00").format(amount);
}

// ② 불변·스레드안전 대안으로 교체
private static final DateTimeFormatter TS =
        DateTimeFormatter.ofPattern("yyyyMMddHHmmss").withZone(ZoneId.of("Asia/Seoul"));

// ③ 정말 생성 비용이 문제일 때만 — 스레드당 하나 (단, 가상 스레드에서는 재검토: 4.5 절)
private static final ThreadLocal<DecimalFormat> AMOUNT_FORMAT =
        ThreadLocal.withInitial(() -> new DecimalFormat("#,##0.00"));
```

③은 "필드 동기화 문제를 ThreadLocal 로 푸는" 대표적 패턴이다. 다만 **가상 스레드 시대에는 이 패턴이 역효과**가 되는데, 이건 뒤(4.5)에서 따로 본다. 순서를 바꿔 말하면 — **①로 되면 ①로 끝내라.**

## 1.2 가시성 — `volatile` 이 실제로 보장하는 것

동시성의 두 얼굴 중 하나는 **원자성**, 다른 하나는 **가시성**이다. 후자는 직관을 배신한다.

```java
@Component
public class SettlementWindow {

    private boolean closed = false;   // ❌ 가시성 보장 없음

    public void close() { this.closed = true; }          // 마감 배치 스레드
    public boolean isClosed() { return this.closed; }     // 승인 처리 스레드들
}
```

마감 배치가 `close()` 를 호출해도, **승인 처리 스레드가 `true` 를 영영 못 볼 수 있다.** 버그가 아니라 **명세상 허용된 동작**이다. Java 언어 명세 17장(Threads and Locks)은 "동기화되지 않은 프로그램의 동작은 혼란스럽고 반직관적일 수 있다"고 전제한 뒤, 어떤 읽기가 어떤 쓰기를 볼 수 있는지를 **happens-before** 관계로 규정한다. 그 규칙 목록에 이런 항목이 있다.

> A write to a `volatile` field happens-before every subsequent read of that field.
> An unlock on a monitor happens-before every subsequent lock on that monitor.
> — [JLS §17.4.5 Happens-before Order](https://docs.oracle.com/javase/specs/jls/se23/html/jls-17.html)

즉 **`volatile` 을 붙이는 행위는 "캐시를 끄는 것"이 아니라 "happens-before 간선을 하나 만드는 것"** 이다. 같은 간선을 `synchronized`(unlock→lock), `Thread.start()`, `Thread.join()`, 그리고 `java.util.concurrent` 클래스들이 만들어준다.

```java
private volatile boolean closed = false;   // ✅ 쓰기가 이후의 모든 읽기에 보인다
```

**주의**: `volatile` 은 **가시성만** 준다. **원자성은 안 준다.** `volatile long count; count++;` 는 여전히 깨진다(읽기-증가-쓰기 3단계).

## 1.3 원자성 — 금융 카운터에는 `LongAdder`

승인 건수·거절 건수처럼 **"많이 쓰고 가끔 읽는"** 통계 값에는 `AtomicLong` 보다 `LongAdder` 가 낫다. javadoc 이 용도를 직접 구분해준다.

> This class is usually preferable to `AtomicLong` when multiple threads update a common sum that is used for purposes such as **collecting statistics, not for fine-grained synchronization control**. Under low update contention, the two classes have similar characteristics. But **under high contention, expected throughput of this class is significantly higher**, at the expense of higher space consumption.
> — [LongAdder (Java SE 25/26)](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/util/concurrent/atomic/LongAdder.html)

```java
@Component
public class ApprovalMetrics {

    private final LongAdder approved = new LongAdder();   // 통계 → LongAdder
    private final LongAdder declined = new LongAdder();

    public void recordApproved() { approved.increment(); }
    public long approvedCount()  { return approved.sum(); }
}
```

반대로 **"이 값으로 분기 판단을 해야 하는"** 경우 — 예: 한도 소진 여부를 CAS 로 판정 — 는 `AtomicLong.compareAndSet` 이 맞다. `LongAdder.sum()` 은 순간 스냅샷이지 원자적 판정 근거가 아니기 때문이다.

## 1.4 그래도 잔액은 필드로 풀지 않는다

여기서 선을 하나 그어야 한다. **JVM 안의 락은 JVM 안에서만 유효하다.**

```java
// ❌ 파드 1개일 때만 "맞아 보이는" 코드
public synchronized void withdraw(String accountId, BigDecimal amount) { ... }
```

K8s 에서 레플리카가 2로 늘어나는 순간 이 락은 아무것도 지키지 않는다. 계좌 잔액·한도·좌석 같은 **여러 인스턴스가 공유하는 자원**의 정합성은 반드시 **DB 제약 + 락(비관/낙관)**, 또는 분산 락으로 내려가야 한다.

이 글의 나머지는 **한 JVM·한 요청 안에서의 문제**로 좁힌다.

---

# Part 2. 축 B — ThreadLocal (요청별 격리)

## 2.1 정의 — 그리고 javadoc 이 든 예시가 하필 금융이다

`ThreadLocal` 은 **같은 변수인데 스레드마다 다른 값을 갖는** 컨테이너다. javadoc 은 전형적 용도를 이렇게 든다.

> `ThreadLocal` instances are typically private static fields in classes that wish to associate state with a thread (e.g., **a user ID or Transaction ID**).
> — [ThreadLocal (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ThreadLocal.html)

user ID 와 transaction ID — **금융 백엔드가 매 요청 들고 다녀야 하는 바로 그 두 개**다.

## 2.2 Spring 은 이미 이 위에 서 있다

직접 쓰기 전에, **이미 쓰고 있다**는 사실부터 알아야 한다.

| Spring 구성요소 | 스레드에 묶어두는 것 | 공식 근거 |
|---|---|---|
| `TransactionSynchronizationManager` | JDBC Connection·Hibernate Session 등 **트랜잭션 리소스** | "Central delegate that manages **resources and transaction synchronizations per thread**" ([javadoc](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/support/TransactionSynchronizationManager.html)) |
| `SecurityContextHolder` | 인증 주체(`Authentication`) | 전략 미지정 시 **기본값이 `MODE_THREADLOCAL`** ([javadoc](https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/core/context/SecurityContextHolder.html)) |
| `RequestContextHolder` | 현재 `HttpServletRequest` | `@RequestScope` 빈이 이 위에서 동작 |
| SLF4J/Logback `MDC` | 로그 태깅용 key-value | "MDC manages contextual information **on a per thread basis**" ([Logback Ch.8](https://logback.qos.ch/manual/mdc.html)) |

**`@Transactional` 이 동작하는 원리 자체가 ThreadLocal 이다.** 트랜잭션 매니저가 커넥션을 *현재 스레드에* 바인딩하고, 같은 스레드에서 실행되는 리포지토리가 `DataSourceUtils.getConnection()` 으로 *그 커넥션을* 찾아 쓴다([DataSourceUtils javadoc](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/jdbc/datasource/DataSourceUtils.html)).

이 사실에서 **금융 코드에서 가장 자주 밟는 지뢰** 하나가 바로 유도된다.

```java
@Transactional
public void transfer(TransferCommand cmd) {
    ledgerRepository.debit(cmd.from(), cmd.amount());
    // ❌ 다른 스레드로 넘어가는 순간 "이 트랜잭션"은 따라가지 않는다
    CompletableFuture.runAsync(() -> ledgerRepository.credit(cmd.to(), cmd.amount()));
}
```

`runAsync` 안의 코드는 **다른 스레드**에서 돈다. 그 스레드에는 커넥션이 바인딩돼 있지 않다. 즉 **차변과 대변이 서로 다른 트랜잭션**이 되고, 롤백은 절반만 일어난다. 복식부기가 깨지는 코드다.

## 2.3 금융 예제 — 거래 컨텍스트(TxContext)

금융 요청 하나에는 비즈니스 파라미터와 **별개로** 따라다녀야 하는 메타데이터가 있다.

- `traceId` — 대외기관·내부 로그 상관관계
- `idempotencyKey` — 재전송 방어(승인 중복 방지)
- `channel` / `terminalId` — 채널(ATM·인터넷뱅킹·가맹점 단말)
- `principalId` — 조작 주체 (감사 요건)
- `requestedAt` — 원 요청 시각

이걸 **모든 메서드 시그니처에 끼워 넣는 것**은 현실적으로 불가능하다(컨트롤러→서비스→도메인→리포지토리→외부 어댑터 전 구간). 그래서 컨텍스트를 스레드에 붙인다.

```java
public record TxContext(
        String traceId,
        String idempotencyKey,
        String channel,
        String principalId,
        Instant requestedAt
) {}
```

```java
public final class TxContextHolder {

    private static final ThreadLocal<TxContext> CONTEXT = new ThreadLocal<>();

    private TxContextHolder() {}

    public static void set(TxContext ctx) {
        CONTEXT.set(Objects.requireNonNull(ctx));
    }

    /** 컨텍스트가 없으면 *조용히 넘어가지 않고* 즉시 실패한다. */
    public static TxContext require() {
        TxContext ctx = CONTEXT.get();
        if (ctx == null) {
            throw new IllegalStateException("거래 컨텍스트가 없다 — 진입점 필터를 거치지 않은 호출");
        }
        return ctx;
    }

    public static Optional<TxContext> find() {
        return Optional.ofNullable(CONTEXT.get());
    }

    public static void clear() {
        CONTEXT.remove();   // ← 이 한 줄이 사고를 막는다
    }
}
```

**설계 판단 하나를 짚고 간다.** 여기서 `ThreadLocal.withInitial(...)` 로 "기본 컨텍스트"를 만들어 주지 않았다. javadoc 상 `withInitial` 은 값이 없을 때 초기값을 만들어주는 편의 기능이지만, 금융에서는 **"컨텍스트를 못 찾았으니 빈 값으로 진행"이 곧 감사 추적 유실**이다. **조용한 기본값보다 즉시 실패가 안전하다.**

진입점에서 채우고, **반드시 `finally` 에서 비운다.**

```java
@Component
public class TxContextFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {

        TxContext ctx = new TxContext(
                Optional.ofNullable(req.getHeader("X-Trace-Id")).orElseGet(() -> UUID.randomUUID().toString()),
                req.getHeader("Idempotency-Key"),
                Optional.ofNullable(req.getHeader("X-Channel")).orElse("UNKNOWN"),
                currentPrincipalId(),
                Instant.now()
        );

        TxContextHolder.set(ctx);
        MDC.put("traceId", ctx.traceId());
        MDC.put("channel", ctx.channel());
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.clear();
            TxContextHolder.clear();   // ✅ 예외가 나도, 타임아웃이 나도 반드시
        }
    }
}
```

그러면 저 아래 어댑터에서 파라미터 없이 꺼내 쓸 수 있다.

```java
@Aspect
@Component
public class AuditTrailAspect {

    private final AuditLogPort auditLogPort;

    @AfterReturning(pointcut = "@annotation(Audited)", returning = "result")
    public void record(JoinPoint jp, Object result) {
        TxContext ctx = TxContextHolder.require();
        auditLogPort.append(new AuditRecord(
                ctx.traceId(), ctx.principalId(), ctx.channel(),
                jp.getSignature().toShortString(), ctx.requestedAt(), Instant.now()
        ));
    }
}
```

## 2.4 그런데 — 이걸 어디까지 퍼뜨릴 것인가

`ThreadLocal` 은 **"선언되지 않은 숨은 파라미터"** 다. 편한 만큼 대가가 있다.

- **테스트**: 도메인 단위테스트가 갑자기 필터·컨텍스트 셋업을 요구한다.
- **추적**: 누가 값을 넣었는지 코드에서 안 보인다. javadoc 이 `ScopedValue` 를 소개하며 지적하는 첫 번째 문제도 이것이다 — **"`ThreadLocal` does not prevent code in a faraway callee from setting a new value"**([ScopedValue javadoc](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ScopedValue.html)).
- **재사용**: 배치·컨슈머에서 같은 서비스를 부르면 컨텍스트가 없다.

그래서 실무 규칙은 이렇게 잡는다.

> **횡단 관심사(로깅·감사·추적·인증)는 ThreadLocal 로, 비즈니스 입력은 파라미터로.**
> 거래금액·계좌번호가 ThreadLocal 에서 나오기 시작하면 그 코드는 이미 잘못됐다.

헥사고날 구조를 쓴다면 — **어댑터·인프라 계층에서만 읽고, 도메인 계층은 순수하게 유지**한다.

---

# Part 3. 주의사항 6가지 (금융 관점)

## 3.1 ① `remove()` 누락 = 스레드풀 오염 = **정보 유출**

가장 중요한 항목이라 맨 앞에 둔다.

서블릿 컨테이너는 스레드를 **재사용**한다. 톰캣 기본 워커 200개가 요청 수만 건을 돌려 처리한다. 그래서 이런 일이 생긴다.

```
 [worker-7]  요청 A (고객 1234, traceId=aaa)
             TxContextHolder.set(...)   → worker-7 에 컨텍스트 부착
             ... 처리 ...
             clear() 없이 종료            ← 사고 지점
             ↓ 스레드 반납
 [worker-7]  요청 B (고객 9999, 컨텍스트 헤더 없음)
             TxContextHolder.require()  → 고객 1234 의 컨텍스트를 반환!
             감사로그: "고객 1234 가 조회함"     ← 오기록
             화면/응답: 직전 고객 정보 노출 가능    ← 유출
```

일반 서비스라면 "로그가 좀 이상함"이지만, 금융에서는 **감사 부적합 + 개인정보 유출**이다. 그래서 규칙은 타협 없이 하나다.

> **`set` 이 있는 모든 지점에는 `finally { remove(); }` 가 짝으로 있어야 한다.**

- 필터라면 `finally` 블록
- 인터셉터라면 `preHandle` ↔ `afterCompletion` (`postHandle` 은 예외 시 안 불린다)
- 배치/컨슈머라면 메시지 처리 루프의 `finally`
- 테스트라면 `@AfterEach`

## 3.2 ② 메모리 누수 — key 는 약참조인데 **value 는 강참조**다

`ThreadLocal` 의 실제 저장소는 각 `Thread` 안의 `ThreadLocalMap` 이고, 그 엔트리의 **key 는 `ThreadLocal` 인스턴스에 대한 약한 참조(weak reference)** 다. Tomcat 프로젝트 위키가 이 구조를 정확히 설명한다.

> The key is a **weak reference** to the `ThreadLocal` instance … `ThreadLocalMap` entries whose key is GCed are **not immediately removed** … it's only during subsequent uses of `ThreadLocal` features that each Thread removes the abandoned entries.
> — [Apache Tomcat Wiki — MemoryLeakProtection](https://cwiki.apache.org/confluence/display/TOMCAT/MemoryLeakProtection)

**value 는 강참조**다. 그래서 `remove()` 를 빼먹으면 값 객체가 **스레드 수명만큼** 살아남는다. 스레드는 풀에서 몇 달을 산다. 커다란 응답 DTO·리스트를 컨텍스트에 담아뒀다면 그대로 누수다.

WAS 재배포 시나리오에서는 더 나빠져서 **클래스로더 누수**가 된다. Tomcat 은 이걸 감지해 로그를 남긴다.

```
SEVERE: A web application created a ThreadLocal with key of type [...] and a value of type [...]
        but failed to remove it when the web application was stopped.
        To prevent a memory leak, the ThreadLocal has been forcibly removed.
```

Tomcat 7.0.6 이후의 정식 대응은 **풀 스레드 자체를 갱신**하는 것이고, 이를 담당하는 게 `ThreadLocalLeakPreventionListener` 다 — "triggers the **renewal of threads in Executor pools** when a Context is being stopped to avoid thread-local related memory leaks"([Tomcat Listeners 문서](https://tomcat.apache.org/tomcat-8.5-doc/config/listeners.html)).

**단, 이건 컨테이너의 안전망이지 면허가 아니다.** 애플리케이션이 `remove()` 를 하는 게 1차 방어다.

## 3.3 ③ 전파되지 않는다 — `@Async`·`CompletableFuture`·`parallelStream`

`ThreadLocal` 은 **스레드 경계를 넘지 않는다.** 금융 코드에서 흔한 형태는 이렇다.

```java
@Async
public CompletableFuture<Void> notifyCore(TransferCommand cmd) {
    // ❌ traceId 없음, 인증 컨텍스트 없음 → 대외 전문 상관관계 추적 불가
    log.info("코어뱅킹 전송");
    ...
}
```

Logback 문서도 같은 지점을 경고한다. **"a child thread does not automatically inherit a copy of the mapped diagnostic context of its parent"**, 그리고 Executor 를 쓰는 경우 **원 스레드에서 `MDC.getCopyOfContextMap()` 을 떠서 작업 첫머리에 `MDC.setContextMap()` 하라**고 명시한다([Logback Ch.8 — MDC and Managed Threads](https://logback.qos.ch/manual/mdc.html)).

Spring 의 정석 해법은 `TaskDecorator` 다. javadoc 이 밝히는 주 용도가 정확히 이것이다 — **"to set some execution context around the task's invocation"**([TaskDecorator javadoc](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/core/task/TaskDecorator.html)).

```java
public class TxContextTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // ── 여기는 아직 "제출한 스레드" (예: 톰캣 워커) ──
        TxContext ctx = TxContextHolder.find().orElse(null);
        Map<String, String> mdc = MDC.getCopyOfContextMap();

        return () -> {
            // ── 여기는 "실행 스레드" (예: async-1) ──
            if (ctx != null) TxContextHolder.set(ctx);
            if (mdc != null) MDC.setContextMap(mdc);
            try {
                runnable.run();
            } finally {
                MDC.clear();
                TxContextHolder.clear();   // 여기서도 반드시
            }
        };
    }
}
```

```java
@Bean
ThreadPoolTaskExecutor auditTaskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setTaskDecorator(new TxContextTaskDecorator());
    executor.initialize();
    return executor;
}
```

**직접 만들기 전에 표준부터 본다.** Spring Framework 는 `ContextPropagatingTaskDecorator` 를 제공하고, 이건 Micrometer 의 [context-propagation](https://docs.micrometer.io/context-propagation/reference/) 라이브러리 위에서 동작한다. 그 라이브러리에 `ThreadLocalAccessor` 를 등록해두면 `ContextSnapshot` 이 **등록된 모든 ThreadLocal 을 한 번에** 떠서 복원한다 — MDC·Observation·Security·내 `TxContext` 까지 일관되게. 관측(Observability) 스택을 이미 쓰고 있다면 이 경로가 정답이다.

한 가지 더: **`parallelStream()` 은 공용 ForkJoinPool 에서 돈다.** 데코레이터를 끼울 자리조차 없다. 금융 처리 루프에서 `parallelStream` 을 쓰면 컨텍스트·트랜잭션이 통째로 사라진다고 보면 된다.

## 3.4 ④ `InheritableThreadLocal` 은 해결책이 아니다 (특히 풀에서)

"자식 스레드가 상속하게 하면 되잖아?" 라는 유혹이 있다. `InheritableThreadLocal` 은 **스레드 생성 시점에 부모 값을 복사**한다. 문제는 **스레드풀에서 생성은 딱 한 번 일어난다**는 것이다.

```
 풀 스레드 async-1 이 "요청 A 처리 중"에 최초 생성됨
   → 요청 A 의 컨텍스트를 상속받아 고정
 이후 요청 B, C, D … 가 async-1 을 재사용
   → 계속 "요청 A" 의 컨텍스트로 로그·감사 기록
```

`remove()` 누락보다 더 고약하다. **틀린 값이 안정적으로 재현**되기 때문에 오히려 "정상 동작"으로 보인다.

Spring Security 의 `SecurityContextHolder` 도 `MODE_INHERITABLETHREADLOCAL` 을 제공하지만, 기본값은 `MODE_THREADLOCAL` 이며 javadoc 은 이 기본이 **"서버에 적합(appropriate on servers)"** 하다고 명시한다([javadoc](https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/core/context/SecurityContextHolder.html)). 인증 주체가 풀 스레드에 고착되는 것은 금융에서는 **권한 오적용**이다. 기본값을 바꾸지 마라. 전파가 필요하면 **작업 단위로 명시 복사(③의 데코레이터)** 가 옳다.

## 3.5 ⑤ 가상 스레드 — "비싼 객체 캐싱" 용도는 정반대가 된다

Spring Boot 는 `spring.threads.virtual.enabled=true` 한 줄로 가상 스레드를 켠다([Spring Boot Reference](https://docs.spring.io/spring-boot/reference/features/spring-application.html)). 이때 **ThreadLocal 의 두 용도가 정반대 운명**을 맞는다.

**(a) 컨텍스트 전달 용도 — 괜찮다.** Oracle 공식 가이드는 "현재 트랜잭션/사용자 ID 같은 컨텍스트 정보를 결부시키는 용도는 가상 스레드에서도 **완벽히 합당(perfectly reasonable)**" 하다고 적는다.

**(b) 비싼 객체 캐싱 용도 — 무너진다.** 앞의 1.1 ③ 패턴(`ThreadLocal<DecimalFormat>`)이 여기 해당한다.

> virtual threads are **never pooled and never reused** by unrelated tasks. Because every task has its own virtual threads, every call to `foo` from a different task would trigger the instantiation of a new `SimpleDateFormat` … These outcomes are **the very opposite of what caching in thread locals intends to achieve**.
> — [Oracle, Virtual Threads (Java 21 core docs)](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)

JEP 444 도 같은 경고를 표준 문서 레벨로 못 박는다 — **"do not use thread locals to pool costly resources among multiple tasks sharing the same thread in a thread pool"**, 그리고 JDK 자신도 가상 스레드 대비로 `java.base` 안의 ThreadLocal 사용처를 대거 제거했다고 밝힌다([JEP 444](https://openjdk.org/jeps/444)).

**진단 도구도 표준으로 있다.** JEP 444 는 시스템 프로퍼티 `jdk.traceVirtualThreadLocals=true` 를 켜면 **가상 스레드가 ThreadLocal 에 값을 set 할 때 스택트레이스를 찍어준다**고 명시한다. 마이그레이션 시 첫 번째로 켜볼 스위치다.

```bash
java -Djdk.traceVirtualThreadLocals=true -jar settlement.jar
```

## 3.6 ⑥ 트랜잭션 경계와 컨텍스트 경계를 헷갈리지 않기

마지막은 개념 정리다. **둘 다 ThreadLocal 위에 있지만 생애주기가 다르다.**

```
 HTTP 요청 ┌──────────────────────────────────────────────┐  ← TxContext (필터가 열고 닫음)
           │   ┌──────────────┐      ┌──────────────┐     │
           │   │ @Transactional│      │ @Transactional│    │  ← 커넥션 바인딩 (트랜잭션 매니저가 열고 닫음)
           │   └──────────────┘      └──────────────┘     │
           └──────────────────────────────────────────────┘
```

- **거래 컨텍스트**는 요청 전체 — 트랜잭션 밖(응답 직렬화·에러 핸들러)에서도 살아 있어야 한다.
- **트랜잭션 리소스**는 `@Transactional` 범위 — Spring 이 자동으로 정리한다. **직접 `TransactionSynchronizationManager` 에 바인딩하지 마라.** javadoc 이 "**to be used by resource management code but not by typical application code**" 라고 명시한다.

---

# Part 4. 다음 단계 — ScopedValue (JDK 25 정식)

JDK 25 에서 `ScopedValue` 가 **preview 를 벗고 정식 API 가 됐다**(JEP 506, Status: Closed/Delivered, Release 25). 목표는 명확하다.

> Introduce scoped values, which enable a method to share **immutable** data both with its callees within a thread, and with child threads. Scoped values are **easier to reason about** than thread-local variables. They also have **lower space and time costs**, especially when used together with virtual threads.
> — [JEP 506: Scoped Values](https://openjdk.org/jeps/506)

javadoc 은 `ThreadLocal` 의 문제를 세 가지로 정리한다.

1. 멀리 있는 callee 가 **새 값을 set 하는 걸 막지 못한다**
2. **수명이 무제한** — 명시적으로 remove 하지 않으면 메서드가 끝나도 값이 남는다
3. **상속 비용이 크다** — 자식 스레드 생성 시 맵을 복사해야 한다

셋 다 앞에서 본 사고의 원인 그 자체다. 앞의 `TxContext` 를 옮기면 이렇게 된다.

```java
public final class TxScope {

    private static final ScopedValue<TxContext> CONTEXT = ScopedValue.newInstance();

    private TxScope() {}

    /** 바인딩은 *구조적*이다 — body 가 끝나면 자동으로 unbound. remove() 가 필요 없다. */
    public static void runWith(TxContext ctx, Runnable body) {
        ScopedValue.where(CONTEXT, ctx).run(body);
    }

    public static TxContext require() {
        if (!CONTEXT.isBound()) {
            throw new IllegalStateException("거래 컨텍스트가 없다 — 진입점 스코프 밖의 호출");
        }
        return CONTEXT.get();
    }
}
```

```java
// 필터
TxScope.runWith(ctx, () -> {
    try { chain.doFilter(req, res); }
    catch (IOException | ServletException e) { throw new UncheckedFilterException(e); }
});
// ← 여기서 자동으로 unbound. "remove() 를 잊어서" 생기는 사고가 구조적으로 불가능해진다.
```

**금융 관점에서 중요한 성질 두 가지.**

- **값이 불변이고 재바인딩만 가능하다.** 깊은 계층의 코드가 거래ID 를 몰래 바꿔치기할 수 없다. 감사 추적의 신뢰성이 **언어 수준에서** 보장된다.
- **자식 스레드 상속이 구조적이다.** `StructuredTaskScope` 로 fork 한 자식은 바인딩을 그대로 본다 — 맵 복사 없이. `@Async` 처럼 "언제 끝날지 모르는" 스레드로 새는 경로가 아니다.

**단, 오늘 당장 전면 이관하라는 뜻은 아니다.** JEP 506 스스로 **"It is not a goal to require migration away from thread-local variables"** 라고 못 박고, 이관이 맞는 경우를 한정한다 — **"one-way transmission of unchanging data"** 일 때. 반대로 **깊은 callee 가 값을 써서 위로 올려보내는 양방향 사용**은 이관 대상이 아니다. 또한 Spring Security·MDC 등 프레임워크 상당수가 여전히 `ThreadLocal` 기반이므로, 현실적 순서는 이렇다.

1. 지금: **`remove()` 규율 + `TaskDecorator` 전파**를 먼저 정확히 한다
2. 가상 스레드 도입 시: `jdk.traceVirtualThreadLocals` 로 **캐싱 용도 ThreadLocal 을 색출**해 제거
3. 신규 코드부터: **단방향 컨텍스트는 `ScopedValue`** 로

---

# Part 5. 체크리스트

프로덕션 금융 코드에 넣기 전에 확인할 항목들이다.

**축 A — 공유 상태**

- [ ] `@Service`/`@Component` 클래스에 **가변 인스턴스 필드**가 있는가? (있다면 그게 스레드 안전한 타입인지 확인)
- [ ] `SimpleDateFormat`·`DecimalFormat`·`Matcher` 를 필드로 들고 있지 않은가? → 지역 변수 또는 `DateTimeFormatter`
- [ ] 스레드 간에 읽는 플래그에 `volatile` 이 있는가?
- [ ] 통계 카운터는 `LongAdder`, 판정용 값은 `AtomicX`(CAS) 인가?
- [ ] **여러 인스턴스가 공유하는 자원**(잔액·한도)을 `synchronized` 로 지키고 있지 않은가? → DB 락으로

**축 B — 격리 상태**

- [ ] 모든 `ThreadLocal.set` 에 대응하는 `finally { remove(); }` 가 있는가?
- [ ] 인터셉터라면 `postHandle` 이 아니라 `afterCompletion` 에서 정리하는가?
- [ ] `@Async`·`CompletableFuture`·`@Scheduled` 로 넘어가는 경로에 `TaskDecorator`(또는 `ContextPropagatingTaskDecorator`)가 걸려 있는가?
- [ ] `parallelStream()` 을 컨텍스트/트랜잭션이 필요한 구간에서 쓰고 있지 않은가?
- [ ] `InheritableThreadLocal` 을 스레드풀과 함께 쓰고 있지 않은가?
- [ ] 컨텍스트에서 꺼내 쓰는 값이 **횡단 관심사**뿐인가? (거래금액·계좌번호가 나오면 설계 오류)
- [ ] 컨텍스트 부재 시 **빈 값으로 진행**하지 않고 **즉시 실패**하는가?
- [ ] 가상 스레드를 켰다면 `jdk.traceVirtualThreadLocals` 로 캐싱 용도를 점검했는가?

---

## 닫으며

동시성 코드를 볼 때 나는 이제 두 질문만 한다.

**"이 상태는 공유돼야 하나, 격리돼야 하나?"**
**"격리돼야 한다면, 그 격리는 언제 끝나나?"**

첫 질문에 답하면 `volatile`·`Atomic`·`ThreadLocal` 중 무엇을 쓸지가 정해지고, 두 번째 질문에 답하면 `finally { remove(); }` 를 어디 둘지가 정해진다. 금융 도메인에서 두 번째 질문의 답이 "잘 모르겠다"이면, 그건 **아직 배포하면 안 되는 코드**다.

그리고 JDK 25 의 `ScopedValue` 는 두 번째 질문을 **개발자에게 묻지 않는** 방향으로 언어가 움직이고 있다는 신호다. 바인딩의 끝을 문법이 정해주면, 잊어버릴 수가 없다.

---

## References

- Oracle. *ThreadLocal (Java SE 25 & JDK 25 API)* — 공식 javadoc (용도 예시: user ID / Transaction ID, `remove()`, `withInitial`). [docs.oracle.com/en/java/javase/25/…/ThreadLocal.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ThreadLocal.html)
- Oracle. *ScopedValue (Java SE 25 & JDK 25 API)* — 공식 javadoc (`ThreadLocal` 의 3가지 문제, `where().run()`, 구조적 상속). [docs.oracle.com/en/java/javase/25/…/ScopedValue.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ScopedValue.html)
- Oracle. *The Java Language Specification — Chapter 17. Threads and Locks (§17.4 Memory Model, §17.4.5 Happens-before Order)* — 1차 언어 명세. [docs.oracle.com/javase/specs/jls/se23/html/jls-17.html](https://docs.oracle.com/javase/specs/jls/se23/html/jls-17.html)
- OpenJDK. *JEP 444: Virtual Threads* — 스레드로컬 사용 지침, `jdk.traceVirtualThreadLocals`, "do not pool virtual threads". [openjdk.org/jeps/444](https://openjdk.org/jeps/444)
- OpenJDK. *JEP 506: Scoped Values* — JDK 25 정식화(Closed/Delivered), 이관 권고 범위. [openjdk.org/jeps/506](https://openjdk.org/jeps/506)
- Oracle. *Virtual Threads (Java SE 21 Core Libraries Guide)* — "Don't Cache Expensive Reusable Objects in Thread-Local Variables". [docs.oracle.com/en/java/javase/21/core/virtual-threads.html](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)
- Oracle. *DecimalFormat / SimpleDateFormat API* — "not synchronized … must be synchronized externally", `DateTimeFormatter` 권고. [DecimalFormat](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/text/DecimalFormat.html) · [SimpleDateFormat](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/text/SimpleDateFormat.html)
- Oracle. *LongAdder API* — 통계 집계 시 `AtomicLong` 대비 고경합 처리량 우위. [docs.oracle.com/en/java/javase/26/…/LongAdder.html](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/util/concurrent/atomic/LongAdder.html)
- Spring. *Spring Framework Reference — Bean Scopes* — "prototype scope for all stateful beans, singleton scope for stateless beans". [docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html](https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html)
- Spring. *TransactionSynchronizationManager / DataSourceUtils javadoc* — "manages resources and transaction synchronizations **per thread**". [TransactionSynchronizationManager](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/support/TransactionSynchronizationManager.html) · [DataSourceUtils](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/jdbc/datasource/DataSourceUtils.html)
- Spring. *TaskDecorator / ContextPropagatingTaskDecorator javadoc, Task Execution and Scheduling* — 실행 컨텍스트 전파. [TaskDecorator](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/core/task/TaskDecorator.html) · [ContextPropagatingTaskDecorator](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/core/task/support/ContextPropagatingTaskDecorator.html) · [Reference](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)
- Spring Security. *SecurityContextHolder javadoc* — 기본 전략 `MODE_THREADLOCAL`, 서버 환경 적합성. [docs.spring.io/spring-security/…/SecurityContextHolder.html](https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/core/context/SecurityContextHolder.html)
- Spring Boot. *SpringApplication — Virtual threads* (`spring.threads.virtual.enabled`, pinning 주의). [docs.spring.io/spring-boot/reference/features/spring-application.html](https://docs.spring.io/spring-boot/reference/features/spring-application.html)
- Micrometer. *Context Propagation — Purpose / Usage* (`ThreadLocalAccessor`, `ContextSnapshot`). [docs.micrometer.io/context-propagation/reference/](https://docs.micrometer.io/context-propagation/reference/)
- QOS.ch. *Logback Manual, Chapter 8: Mapped Diagnostic Context* — per-thread 관리, 자식 스레드 미상속, Executor 사용 시 `getCopyOfContextMap`/`setContextMap` 권고. [logback.qos.ch/manual/mdc.html](https://logback.qos.ch/manual/mdc.html) · [SLF4J Manual](https://www.slf4j.org/manual.html)
- Apache Tomcat. *MemoryLeakProtection (프로젝트 위키)* 및 *Listeners — ThreadLocal Leak Prevention Listener* — `ThreadLocalMap` 약참조 key/강참조 value, 풀 스레드 갱신 대응. [cwiki.apache.org/…/MemoryLeakProtection](https://cwiki.apache.org/confluence/display/TOMCAT/MemoryLeakProtection) · [Listeners](https://tomcat.apache.org/tomcat-8.5-doc/config/listeners.html)

*출처 등급: 언어 동작(메모리 모델·ThreadLocal·ScopedValue·가상 스레드)은 JLS·JEP·Oracle javadoc 등 1차 명세를, 프레임워크 동작은 Spring/Tomcat/Logback/Micrometer 공식 문서를 인용했다. 본문의 코드는 설명용 예제이며 특정 금융기관의 실제 코드가 아니다. "성능이 얼마나 좋아진다" 류의 수치 주장은 중립 벤치마크가 없어 의도적으로 넣지 않았다 — `LongAdder`·`ScopedValue` 의 우위는 각 공식 문서의 서술을 그대로 인용한 범위까지만이며, 실제 효과는 경합 수준·워크로드에 따라 달라지므로 도입 전 자체 측정이 필요하다.*
