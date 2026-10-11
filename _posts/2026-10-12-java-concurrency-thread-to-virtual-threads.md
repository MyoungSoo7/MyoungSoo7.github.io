---
layout: post
title: "자바 동시성의 진화 — Thread → ExecutorService → CompletableFuture → 가상 스레드, 그리고 구조적 동시성"
date: 2026-10-12 00:17:42 +0900
categories: [java]
tags: [java, concurrency, thread, executorservice, completablefuture, virtual-threads, structured-concurrency, scoped-values, project-loom, jdk21, jdk24, jdk25, spring-boot]
---

자바·코틀린 20편 시리즈의 **자바 7번째 글(J7)** 입니다. 자바가 "동시에 여러 일을 한다" 를 표현해 온 방식을 세대별로 정리합니다. `Thread` 를 직접 만들던 시절부터 `ExecutorService` 스레드 풀, `CompletableFuture` 비동기 조합, JDK 21 의 **가상 스레드(virtual threads)**, JDK 24 의 pinning 개선, 그리고 JDK 26 기준으로도 아직 프리뷰인 **구조적 동시성(structured concurrency)** 과 JDK 25 에 정식이 된 **Scoped Values** 까지 다룹니다. 마지막에 스프링 부트에서 가상 스레드를 켜는 방법과 주의점을 봅니다.

코틀린 코루틴과의 비교는 짝이 되는 [K7 — 코틀린 코루틴과 Flow](https://myoungsoo7.github.io/2026/10/12/kotlin-coroutines-and-flow/) 에서 다룹니다. 가상 스레드 내부 구조를 더 깊게 보고 싶다면 이전 글 [가상 스레드와 캐리어 스레드의 관계](https://myoungsoo7.github.io/2026/06/19/virtual-thread-and-carrier-thread-relationship/) 도 참고하세요.

---

## 1. 세대별 지도

| 세대 | 핵심 API | 도입 | 해결한 문제 | 남은 문제 |
|---|---|---|---|---|
| 1 | `Thread`, `Runnable` | JDK 1.0 | 동시 실행 자체 | 생성 비용, 수명 관리, 결과 반환 |
| 2 | `ExecutorService`, `Future` | JDK 1.5 | 스레드 재사용(풀), 작업/실행 분리 | `Future.get()` 블로킹, 조합 불가 |
| 3 | `ForkJoinPool` | JDK 1.7 | 분할 정복 병렬 처리, work-stealing | CPU 작업 전용 |
| 4 | `CompletableFuture` | JDK 1.8 | 비동기 결과의 조합·체이닝 | 콜백 스타일, 디버깅 난이도, 스택 트레이스 단절 |
| 5 | 가상 스레드 | JDK 21 | 블로킹 코드 그대로 높은 동시성 | pinning(JDK 24 에서 대부분 해소) |
| 6 | 구조적 동시성 | 프리뷰(JDK 21~26) | 하위 작업 수명을 코드 블록에 묶기 | 아직 프리뷰 |

`Since` 버전은 각 클래스의 JDK 21 Javadoc 에서 확인했습니다: [Thread](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html)(1.0), [ExecutorService](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html)(1.5), [ForkJoinPool](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html)(1.7), [CompletableFuture](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html)(1.8). 가상 스레드는 [JEP 444](https://openjdk.org/jeps/444) 로 JDK 21 에 정식 도입되었습니다.

---

## 2. 1세대 — `Thread` 직접 다루기

### 2.1 무엇인가

`java.lang.Thread` 는 자바의 실행 단위입니다. JDK 21 이전에는 자바 `Thread` 하나가 OS 스레드 하나에 대응하는 **플랫폼 스레드** 뿐이었습니다.

### 2.2 코드

```java
Thread t = new Thread(() -> {
    System.out.println("작업 스레드: " + Thread.currentThread().getName());
});
t.start();
t.join();   // 끝날 때까지 대기
```

JDK 21 부터는 빌더로 플랫폼/가상 스레드를 명시적으로 고를 수 있습니다(`Thread.ofPlatform()`, `Thread.ofVirtual()` 모두 Since 21).

```java
Thread platform = Thread.ofPlatform().name("worker-", 0).start(task);
Thread virtual  = Thread.ofVirtual().name("vt-", 0).start(task);
```

### 2.3 실무 사용사례

- 애플리케이션 코드에서 `new Thread()` 를 직접 쓸 일은 거의 없습니다. 예외는 **수명이 애플리케이션 전체와 같은 전용 스레드**(예: 소켓 accept 루프, 아주 단순한 백그라운드 데몬) 정도입니다.

### 2.4 함정

- **요청마다 `new Thread()`**: 플랫폼 스레드는 생성 비용이 크고 OS 자원을 씁니다. 트래픽이 몰리면 스레드 수가 무한히 늘어 OOM 이나 OS 한도에 걸립니다.
- **예외 유실**: `run()` 에서 던진 예외는 호출자에게 전달되지 않습니다. `UncaughtExceptionHandler` 를 설정하지 않으면 로그 한 줄 남기고 사라집니다.
- **`ThreadLocal` 누수**: 스레드가 오래 살면 `ThreadLocal` 값도 오래 삽니다. 풀에서 재사용될 때 이전 요청의 값이 남아 있는 사고가 흔합니다.

---

## 3. 2세대 — `ExecutorService` 와 `Future`

### 3.1 무엇인가

"무엇을 실행할지(작업)" 와 "어떻게 실행할지(스레드 관리)" 를 분리합니다. 스레드 풀이 스레드를 재사용하므로 생성 비용이 사라지고, 풀 크기로 동시성 상한을 정합니다.

### 3.2 코드

```java
ExecutorService pool = Executors.newFixedThreadPool(16);
try {
    Future<User> userF   = pool.submit(() -> userClient.find(id));
    Future<List<Order>> ordersF = pool.submit(() -> orderClient.findByUser(id));

    User user = userF.get(2, TimeUnit.SECONDS);       // 블로킹
    List<Order> orders = ordersF.get(2, TimeUnit.SECONDS);
} finally {
    pool.shutdown();
}
```

JDK 19 부터 `ExecutorService` 는 `AutoCloseable` 이라 try-with-resources 로 쓸 수 있습니다. `close()` 는 새 작업을 받지 않고, **이미 제출된 작업이 모두 끝날 때까지 기다립니다**. 기다리는 중 인터럽트되면 `shutdownNow()` 를 호출합니다 ([ExecutorService Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html)).

```java
try (ExecutorService pool = Executors.newFixedThreadPool(16)) {
    pool.submit(task1);
    pool.submit(task2);
}   // 여기서 두 작업이 끝날 때까지 대기
```

### 3.3 실무 사용사례

- **외부 API 병렬 호출**: 위 예제처럼 서로 독립적인 호출을 동시에 보내고 결과를 모읍니다.
- **배치 작업 분할**: 대량 데이터를 청크로 나눠 풀에 제출.
- **동시성 상한 강제**: 풀 크기 = 하위 시스템(DB, 외부 API)이 견딜 수 있는 동시 요청 수.

### 3.4 함정

1. **`Executors.newCachedThreadPool()` 은 상한이 없습니다.** 부하가 몰리면 스레드가 무제한으로 생깁니다.
2. **`newFixedThreadPool` 의 큐는 무제한입니다.** 작업이 처리 속도보다 빨리 들어오면 큐에 쌓여 메모리를 먹습니다. 운영 코드에서는 `ThreadPoolExecutor` 를 직접 만들어 큐 크기와 거부 정책을 명시하는 편이 안전합니다.
3. **`shutdown()` 누락**: 비데몬 스레드가 남아 JVM 이 종료되지 않습니다.
4. **풀 안에서 같은 풀의 결과를 `get()`**: 풀의 모든 스레드가 서로의 결과를 기다리면 교착(thread starvation deadlock)이 납니다.
5. **`Future.get()` 은 결국 블로킹**입니다. 결과들을 조합하려면 `get()` 을 여러 번 부르며 스레드를 묶어 두게 됩니다. 이게 3세대가 나온 이유입니다.

---

## 4. 3세대 — `ForkJoinPool` (짧게)

`ForkJoinPool`(JDK 1.7)은 큰 작업을 작게 쪼개고, 놀고 있는 워커가 다른 워커의 작업을 훔쳐 오는(work-stealing) 풀입니다. 병렬 스트림과 `CompletableFuture` 의 기본 실행기가 이 풀의 공용 인스턴스(`ForkJoinPool.commonPool()`)를 씁니다. 그리고 JDK 21 가상 스레드의 스케줄러 역시 **FIFO 모드로 동작하는 work-stealing `ForkJoinPool`** 입니다 ([JEP 444](https://openjdk.org/jeps/444)).

**함정**: 공용 풀에서 블로킹 I/O 를 하면 같은 풀을 쓰는 병렬 스트림과 `CompletableFuture` 작업 전체가 느려집니다. 공용 풀은 CPU 작업 용도로 남겨 두세요.

---

## 5. 4세대 — `CompletableFuture`

### 5.1 무엇인가

JDK 8 의 `CompletableFuture` 는 "나중에 완료될 값" 을 **블로킹 없이 조합**합니다. 각 단계가 끝나면 다음 단계가 콜백으로 이어집니다.

기본 실행기 규칙이 중요합니다. Javadoc 에 따르면, `Executor` 인자 없는 모든 *async* 메서드는 `ForkJoinPool.commonPool()` 에서 실행되며, 공용 풀의 병렬도가 2 미만이면 작업마다 새 스레드를 만듭니다 ([CompletableFuture Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html)).

### 5.2 코드 — 조합

```java
ExecutorService io = Executors.newFixedThreadPool(32);

CompletableFuture<User> userF =
        CompletableFuture.supplyAsync(() -> userClient.find(id), io);
CompletableFuture<List<Order>> ordersF =
        CompletableFuture.supplyAsync(() -> orderClient.findByUser(id), io);

CompletableFuture<Profile> profileF = userF
        .thenCombine(ordersF, Profile::new)                    // 두 결과 합치기
        .thenApply(p -> p.withGrade(gradePolicy.of(p)))        // 변환
        .orTimeout(2, TimeUnit.SECONDS)                         // 타임아웃 (JDK 9)
        .exceptionally(ex -> Profile.fallback(id));            // 실패 시 대체값

Profile profile = profileF.join();
```

`orTimeout`, `completeOnTimeout`, `delayedExecutor` 는 JDK 9 의 [JEP 266](https://openjdk.org/jeps/266) 으로 추가되었습니다.

여러 개를 기다릴 때는 `allOf` 를 씁니다.

```java
List<CompletableFuture<Price>> futures = skus.stream()
        .map(sku -> CompletableFuture.supplyAsync(() -> priceClient.get(sku), io))
        .toList();

CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new)).join();

List<Price> prices = futures.stream()
        .map(CompletableFuture::join)
        .toList();
```

### 5.3 실무 사용사례

- **팬아웃-팬인**: 여러 하위 서비스 호출을 동시에 보내고 합치기(BFF, 상품 상세 페이지 조립).
- **타임아웃·대체값**: 추천 API 가 느리면 기본 추천으로 대체.
- **스프링 `@Async` 반환 타입**: `@Async` 메서드는 `void`, `Future`, `CompletableFuture` 를 반환할 수 있습니다. 기본 모드가 프록시라 **같은 클래스 안의 호출(self-invocation)은 비동기로 실행되지 않는다** 는 점도 함께 기억하세요 ([Spring Framework — Task Execution and Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)).

### 5.4 함정

1. **실행기를 지정하지 않으면 공용 풀**입니다. `supplyAsync(() -> blockingHttpCall())` 처럼 블로킹 I/O 를 공용 풀에 올리면 애플리케이션 전체의 병렬 작업이 막힙니다. I/O 는 **항상 전용 `Executor` 를 넘기세요.**
2. **`thenApply` vs `thenApplyAsync`**: `thenApply` 는 이전 단계를 완료시킨 스레드(또는 호출 스레드)에서 실행될 수 있습니다. 어느 스레드에서 실행될지 가정하지 마세요.
3. **예외가 `CompletionException` 으로 감싸짐**: `join()` 은 원인 예외를 `CompletionException` 으로 감쌉니다. `exceptionally` 안에서 `ex.getCause()` 를 확인해야 할 때가 많습니다.
4. **`orTimeout` 은 원래 작업을 멈추지 않습니다.** 결과 future 를 타임아웃 예외로 완료시킬 뿐, 이미 실행 중인 HTTP 호출은 계속 돕니다. 하위 클라이언트 자체에도 타임아웃을 걸어야 합니다.
5. **`ThreadLocal`(MDC, 트랜잭션, 보안 컨텍스트)이 전파되지 않습니다.** 다른 스레드에서 실행되기 때문입니다. 로그 추적 ID 가 비동기 구간에서 사라지는 원인입니다.

---

## 6. 5세대 — 가상 스레드 (JDK 21)

### 6.1 무엇인가

가상 스레드는 JDK 가 관리하는 경량 스레드입니다. [JEP 444](https://openjdk.org/jeps/444) 기준 주요 사실은 다음과 같습니다.

- 프리뷰 이력: JEP 425(JDK 19), JEP 436(JDK 20) → **JDK 21 정식**.
- **M:N 스케줄링**: 많은 가상 스레드를 적은 수의 플랫폼 스레드(캐리어) 위에서 돌립니다. 스케줄러는 FIFO 모드의 work-stealing `ForkJoinPool` 이고, 기본 병렬도는 사용 가능한 프로세서 수입니다.
- 블로킹 I/O 를 만나면 가상 스레드가 캐리어에서 **내려오고(unmount)**, 캐리어는 다른 가상 스레드를 실행합니다.
- `ThreadLocal`, `InheritableThreadLocal` 을 지원해 기존 라이브러리를 그대로 쓸 수 있습니다.

가장 중요한 문장은 비목표(non-goal) 쪽에 있습니다. JEP 444 는 가상 스레드가 **"더 빠른 스레드가 아니다"** 라고 못 박습니다. 코드를 더 빨리 실행하지 않으며, **지연 시간(latency)이 아니라 처리량(throughput), 즉 규모(scale)를 위한 것**입니다 ([JEP 444](https://openjdk.org/jeps/444)).

### 6.2 코드

```java
// 1) 작업마다 가상 스레드 하나
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<Price>> futures = skus.stream()
            .map(sku -> executor.submit(() -> priceClient.get(sku)))   // 블로킹 호출 그대로
            .toList();
    for (Future<Price> f : futures) {
        prices.add(f.get());
    }
}

// 2) 단발성
Thread.startVirtualThread(() -> audit.write(event));

// 3) 빌더
Thread vt = Thread.ofVirtual().name("import-", 0).unstarted(task);
vt.start();
```

`CompletableFuture` 체인으로 쓰던 팬아웃 코드가, **평범한 블로킹 코드 + 작업당 가상 스레드**로 바뀝니다. 스택 트레이스도 평범한 동기 코드처럼 이어집니다.

### 6.3 공식 가이드의 사용 원칙

Oracle 의 JDK 21 가상 스레드 가이드는 다음을 권합니다 ([Oracle Virtual Threads 가이드](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)).

1. **가상 스레드를 풀링하지 말 것.** "모든 동시 작업을 가상 스레드로 표현하고, 가상 스레드를 풀링하지 말라." 가상 스레드 수는 동시 작업 수와 같아야 합니다. JEP 444 도 같은 말을 합니다.
2. **동시성 제한은 `Semaphore` 로.** 외부 서비스 동시 호출 수를 제한하고 싶으면 스레드 풀 크기 대신 세마포어를 씁니다.

   ```java
   private final Semaphore paymentGatewayLimit = new Semaphore(10);

   PaymentResponse call(PaymentRequest req) throws InterruptedException {
       paymentGatewayLimit.acquire();
       try {
           return gateway.send(req);
       } finally {
           paymentGatewayLimit.release();
       }
   }
   ```

3. **비싼 객체를 `ThreadLocal` 에 캐시하지 말 것.** 가상 스레드는 작업 하나만 실행하고 사라지므로 캐시가 재사용되지 않습니다. `SimpleDateFormat` 을 `ThreadLocal` 에 넣던 패턴 대신 불변·스레드 안전한 `DateTimeFormatter` 를 씁니다.
4. **단순한 동기 블로킹 코드를 쓸 것.** 가상 스레드에서 블로킹은 싸고 권장됩니다.

### 6.4 Pinning — JDK 21 과 JDK 24 의 차이

가상 스레드가 블로킹되어도 캐리어에서 내려오지 못하고 캐리어를 붙잡는 상태를 **pinning** 이라고 합니다.

- **JDK 21 (JEP 444)**: `synchronized` 블록/메서드 안에서, 또는 네이티브 메서드·외부 함수(foreign function) 실행 중에 블로킹하면 pinning 이 발생합니다. 진단용으로 `jdk.tracePinnedThreads` 시스템 프로퍼티가 있었습니다.
- **JDK 24 (JEP 491)**: `synchronized` 구현이 바뀌어 가상 스레드가 캐리어와 독립적으로 모니터를 획득·보유·해제할 수 있게 되었습니다. 즉 **`synchronized` 로 인한 pinning 이 사라졌습니다.** 남은 pinning 사례로 JEP 491 은 클래스 로딩, 클래스 초기화(static initializer) 중 블로킹, 다른 스레드의 클래스 초기화 대기를 들며 "드물게만 문제가 된다" 고 설명합니다. 그리고 `jdk.tracePinnedThreads` 는 **제거되었고**, 설정해도 효과가 없습니다 ([JEP 491](https://openjdk.org/jeps/491)).

진단은 JFR 로 합니다. Oracle 가이드에 따르면 JFR 은 pinning 상태에서 블로킹이 일어나면 `jdk.VirtualThreadPinned` 이벤트를 내고, 기본값으로는 20ms 이상 걸린 경우에 활성화됩니다 ([Oracle Virtual Threads 가이드](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)).

**실무 결론**: JDK 21 에서 가상 스레드를 쓰면, 오래·자주 블로킹하는 `synchronized` 구간(예: 오래된 JDBC 드라이버나 커넥션 풀 내부)을 `ReentrantLock` 으로 바꾸라는 조언이 많았습니다. **JDK 24 이상**에서는 이 문제가 대부분 사라졌으므로, 가상 스레드를 진지하게 도입한다면 런타임을 JDK 25 LTS 로 맞추는 것이 가장 간단한 해법입니다. 스프링 부트 문서도 같은 취지로 "Java 24 이상을 강력히 권장" 합니다(7장).

### 6.5 실무 사용사례

- **thread-per-request 서버**: 톰캣 같은 서블릿 컨테이너의 요청 처리 스레드를 가상 스레드로. 대부분 시간을 DB·외부 API 응답을 기다리는 데 쓰는 전형적인 백엔드에 맞습니다.
- **팬아웃 호출**: `CompletableFuture` 체인 대신 블로킹 호출 + 작업당 가상 스레드.
- **대량 I/O 배치**: 수천 개 파일/HTTP 호출을 동시에. 단, 하위 시스템 보호를 위해 세마포어로 상한.

### 6.6 함정

1. **CPU 바운드 작업에는 이득이 없습니다.** 가상 스레드는 기다리는 시간을 재활용할 뿐, 계산을 빠르게 하지 않습니다(JEP 444 의 "not faster threads").
2. **하위 자원이 병목이 됩니다.** 스레드 수 제한이 풀리면 DB 커넥션 풀이 새 병목이 됩니다. 요청 1만 개가 동시에 커넥션 30개를 기다리게 될 수 있습니다. 커넥션 풀 크기·타임아웃을 함께 봐야 합니다. (관련: [HikariCP 커넥션 풀 대기 시간](https://myoungsoo7.github.io/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time/))
3. **풀링하지 말 것.** `Executors.newFixedThreadPool(100, Thread.ofVirtual().factory())` 처럼 가상 스레드를 풀에 넣으면 장점이 사라집니다. 동시성 제한이 목적이면 세마포어.
4. **`ThreadLocal` 남용**: 가상 스레드는 수가 많으므로 무거운 값을 `ThreadLocal` 에 두면 메모리가 늘어납니다. 대안은 다음 장의 Scoped Values.
5. **데몬 스레드**: 가상 스레드는 데몬 스레드입니다. 모든 스레드가 데몬이면 JVM 이 종료됩니다(스프링 부트 문서의 경고, 7장).

---

## 7. 스프링 부트에서 가상 스레드 켜기

### 7.1 설정

스프링 부트 **3.2** 부터 다음 한 줄로 켭니다. Java 21 에서 실행해야 합니다 ([Spring Boot 3.2 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes)).

```properties
spring.threads.virtual.enabled=true
```

3.2 릴리스 노트가 밝힌 적용 범위는 다음과 같습니다.

| 영역 | 동작 |
|---|---|
| 웹 서버 | 톰캣과 제티가 요청 처리에 가상 스레드 사용 |
| 태스크 실행 | 애플리케이션 태스크 실행기가 가상 스레드를 쓰는 `SimpleAsyncTaskExecutor` 로 (`@Async`, Spring MVC 비동기 처리에 영향) |
| 스케줄링 | 태스크 스케줄러가 가상 스레드를 쓰는 `SimpleAsyncTaskScheduler` 로 |
| 메시징 | RabbitMQ·Kafka 리스너용 가상 스레드 실행기 자동 구성, Pulsar 는 `VirtualThreadTaskExecutor` |
| WebFlux | 블로킹 실행이 애플리케이션 태스크 실행기를 사용 |

그 바탕에는 스프링 프레임워크 **6.1** 의 `VirtualThreadTaskExecutor` 와 `SimpleAsyncTaskExecutor` 의 가상 스레드 모드가 있습니다 ([Spring Framework 6.1 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes)).

### 7.2 현재 문서의 주의사항

스프링 부트 레퍼런스의 "Virtual threads" 절은 다음을 명시합니다 ([Spring Boot — SpringApplication](https://docs.spring.io/spring-boot/reference/features/spring-application.html)).

- 가상 스레드는 Java 21 이상이 필요하고, **최상의 경험을 위해 Java 24 이상을 강력히 권장**한다.
- 경우에 따라 "Pinned Virtual Threads" 때문에 처리량이 오히려 떨어질 수 있다.
- 가상 스레드가 켜지면 **스레드 풀 설정 프로퍼티는 더 이상 효과가 없다.** 가상 스레드는 JVM 전역 플랫폼 스레드 풀에서 스케줄되기 때문이다.
- 가상 스레드는 데몬 스레드라, `@Scheduled` 빈에만 의존해 애플리케이션을 살려 두던 경우 JVM 이 종료될 수 있다. **`spring.main.keep-alive=true`** 를 권장한다.

태스크 실행 문서도 같은 내용을 확인해 줍니다. 가상 스레드가 켜지면 `SimpleAsyncTaskScheduler` 는 **풀 관련 프로퍼티를 무시**합니다 ([Spring Boot — Task Execution and Scheduling](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html)).

```properties
spring.threads.virtual.enabled=true
spring.main.keep-alive=true
```

### 7.3 스프링에서의 함정

1. **`server.tomcat.threads.max` 로 부하를 제어하던 방식이 사라집니다.** 이 값이 사실상 "동시에 DB 를 두드리는 요청 수 상한" 역할을 하고 있었다면, 켜는 순간 그 보호막이 없어집니다. HikariCP `maximum-pool-size`·`connection-timeout`, 외부 호출용 세마포어/레이트 리미터를 다시 설계하세요.
2. **`@Async` 의 풀 크기 설정이 무시됩니다.** `spring.task.execution.pool.*` 로 동시성을 제한하던 코드가 있다면 다른 수단이 필요합니다.
3. **MDC·트랜잭션 등 `ThreadLocal` 기반 컨텍스트**는 가상 스레드에서도 동작하지만, `@Async` 경계를 넘으면 여전히 전파되지 않습니다. 이건 가상 스레드와 무관한 기존 성질입니다.
4. **JDK 21 + `synchronized` 많은 라이브러리**: JDK 21 에 머물러야 한다면 JFR 로 `jdk.VirtualThreadPinned` 를 먼저 측정하세요.

---

## 8. 6세대 — 구조적 동시성 (프리뷰)

### 8.1 무엇인가

구조적 동시성은 "하위 작업(subtask)의 수명을 그것을 시작한 코드 블록 안에 가둔다" 는 원칙입니다. 하나가 실패하면 나머지를 자동으로 취소하고, 블록을 빠져나갈 때 모든 하위 작업이 끝나 있음을 보장합니다.

**상태(2026-10 기준)**: 아직 **프리뷰**입니다 ([JEP 505](https://openjdk.org/jeps/505), [JEP 525](https://openjdk.org/jeps/525)).

| JDK | JEP | 단계 |
|---|---|---|
| 19, 20 | JEP 428, 437 | 인큐베이터 |
| 21 | JEP 453 | 1차 프리뷰 |
| 22, 23, 24 | JEP 462, 480, 499 | 2~4차 프리뷰 |
| 25 | JEP 505 | 5차 프리뷰 — `StructuredTaskScope.open()` + `Joiner` 형태로 API 개편 |
| 26 | JEP 525 | 6차 프리뷰 — `Joiner.onTimeout()` 추가, `allSuccessfulOrThrow()` 가 결과 리스트 반환, `anySuccessfulResultOrThrow()` → `anySuccessfulOrThrow()` 이름 변경 등 |

### 8.2 코드 (프리뷰, JDK 25 — `--enable-preview` 필요)

JEP 505 의 예제입니다.

```java
Response handle() throws InterruptedException {
    try (var scope = StructuredTaskScope.open()) {
        Subtask<String> user = scope.fork(() -> findUser());
        Subtask<Integer> order = scope.fork(() -> fetchOrder());
        scope.join();
        return new Response(user.get(), order.get());
    }
}
```

`ExecutorService` + `Future` 로 쓴 같은 코드와 비교하면 차이는 이렇습니다.

| | `ExecutorService` + `Future` | `StructuredTaskScope` |
|---|---|---|
| 하나가 실패하면 | 나머지는 계속 돈다(직접 `cancel` 해야 함) | 나머지를 취소 |
| 호출자가 인터럽트되면 | 하위 작업은 계속 돈다 | 함께 취소 |
| 스레드 덤프 | 작업 간 부모-자식 관계가 안 보임 | 스코프 계층이 드러남 |
| 수명 | 실행기 수명에 묶임 | `try` 블록에 묶임 |

### 8.3 함정

- **프리뷰 API 는 릴리스마다 바뀝니다.** JDK 21 프리뷰([JEP 453](https://openjdk.org/jeps/453))의 `ShutdownOnFailure`/`ShutdownOnSuccess` 서브클래스 방식은 JDK 25 에서 `open()` + `Joiner` 로 바뀌었고, JDK 26 에서 또 메서드 이름이 바뀌었습니다. 운영 코드에 쓰면 JDK 업그레이드마다 수정해야 합니다.
- 운영 코드에서는 당분간 `newVirtualThreadPerTaskExecutor()` + try-with-resources 로 비슷한 효과(블록 종료 시 대기)를 얻고, 실패 시 취소는 직접 처리하는 편이 현실적입니다.

---

## 9. Scoped Values (JDK 25 정식)

### 9.1 무엇인가

`ScopedValue` 는 **불변 값을 정해진 실행 범위 동안 공유**하는 수단입니다. JDK 20 인큐베이터(JEP 429), JDK 21~24 프리뷰(JEP 446, 464, 481, 487)를 거쳐 **JDK 25 에서 정식**이 되었습니다 ([JEP 506](https://openjdk.org/jeps/506)).

| | `ThreadLocal` | `ScopedValue` |
|---|---|---|
| 변경 | `set()` 으로 언제든 변경 | 불변, `set` 없음 |
| 수명 | 스레드 수명(직접 `remove()` 해야 함) | `run`/`call` 범위로 한정 |
| 자식 스레드 상속 | `InheritableThreadLocal` 은 복사 비용 | 자식과 효율적으로 공유 |

### 9.2 코드

```java
public final class RequestContext {
    public static final ScopedValue<String> TRACE_ID = ScopedValue.newInstance();
}

// 경계(필터, 메시지 리스너 진입점)에서 바인딩
ScopedValue.where(RequestContext.TRACE_ID, traceId)
           .run(() -> handler.handle(request));

// 깊은 곳에서 읽기
String traceId = RequestContext.TRACE_ID.get();
```

`run` 블록이 끝나면 바인딩이 사라지므로 `ThreadLocal.remove()` 를 잊어 생기는 누수가 원천적으로 없습니다.

### 9.3 함정

- **값을 바꿀 수 없습니다.** 요청 처리 도중 값을 갱신하는 설계(예: 처리 단계 기록)에는 맞지 않습니다. 필요하면 바깥 범위에서 새 값으로 다시 `where(...).run(...)` 합니다.
- **기존 생태계는 여전히 `ThreadLocal` 기반**입니다. SLF4J MDC, 스프링의 트랜잭션 동기화, 보안 컨텍스트가 모두 그렇습니다. 애플리케이션 자체 컨텍스트부터 `ScopedValue` 로 옮기는 정도가 현실적인 시작점입니다.
- JDK 25 에서 마지막으로 바뀐 점: `ScopedValue.orElse` 가 더 이상 `null` 인자를 받지 않습니다 ([JEP 506](https://openjdk.org/jeps/506)).

---

## 10. 선택 가이드

| 상황 | 권장 |
|---|---|
| 일반적인 블로킹 I/O 백엔드, JDK 21+ | 가상 스레드 (가능하면 JDK 24+, 즉 25 LTS) |
| CPU 집약 계산 | 코어 수 기반 고정 풀, `ForkJoinPool`, 병렬 스트림 |
| 여러 비동기 결과의 복잡한 조합, JDK 17 | `CompletableFuture` + 전용 I/O 실행기 |
| 하위 시스템 동시 호출 상한 | `Semaphore` (가상 스레드), 풀 크기 (플랫폼 스레드) |
| 요청 범위 불변 컨텍스트, JDK 25+ | `ScopedValue` |
| 하위 작업 수명 묶기 | 구조적 동시성(프리뷰) — 운영에는 아직 신중히 |
| 스트리밍·백프레셔가 본질인 문제 | 리액티브(Reactor) 또는 코틀린 Flow |

코틀린 코루틴은 언어·라이브러리 수준에서 구조적 동시성을 이미 정식으로 제공합니다. 같은 문제를 코틀린이 어떻게 푸는지는 [K7](https://myoungsoo7.github.io/2026/10/12/kotlin-coroutines-and-flow/) 에서 비교합니다.

---

## 11. 정리

- `Thread` → `ExecutorService` → `CompletableFuture` 는 "스레드가 비싸다" 는 전제 위에서 **스레드를 아끼는 방법**의 진화였습니다.
- 가상 스레드는 그 전제를 바꿔, **블로킹 코드를 그대로 두고 동시성을 늘리는** 방향으로 돌아왔습니다. 단, 더 빠른 스레드가 아니라 더 많은 스레드입니다.
- JDK 21 의 `synchronized` pinning 은 JDK 24 에서 해소되었습니다. 스프링 부트도 Java 24 이상을 강력히 권장합니다.
- 스프링 부트 3.2+ 에서 `spring.threads.virtual.enabled=true` 한 줄로 켜지만, **풀 크기라는 보호막이 사라진다**는 점을 반드시 설계에 반영해야 합니다.
- 구조적 동시성은 JDK 26 기준으로도 프리뷰, Scoped Values 는 JDK 25 에서 정식입니다.

---

## References

- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444) — OpenJDK
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491) — OpenJDK
- [JEP 505: Structured Concurrency (Fifth Preview)](https://openjdk.org/jeps/505) — OpenJDK
- [JEP 525: Structured Concurrency (Sixth Preview)](https://openjdk.org/jeps/525) — OpenJDK
- [JEP 506: Scoped Values](https://openjdk.org/jeps/506) — OpenJDK
- [JEP 453: Structured Concurrency (Preview)](https://openjdk.org/jeps/453) — OpenJDK
- [JEP 266: More Concurrency Updates](https://openjdk.org/jeps/266) — OpenJDK
- [Virtual Threads — Java SE 21 Core Libraries](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html) — Oracle
- Javadoc (JDK 21): [Thread](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html), [ExecutorService](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html), [ForkJoinPool](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html), [CompletableFuture](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html) — Oracle
- [JDK 25](https://openjdk.org/projects/jdk/25/), [JDK 26](https://openjdk.org/projects/jdk/26/) 프로젝트 페이지 — OpenJDK
- [Spring Boot 3.2 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes) — spring-projects wiki
- [Spring Framework 6.1 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes) — spring-projects wiki
- [Spring Boot Reference — SpringApplication (Virtual threads)](https://docs.spring.io/spring-boot/reference/features/spring-application.html) — docs.spring.io
- [Spring Boot Reference — Task Execution and Scheduling](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html) — docs.spring.io
- [Spring Framework Reference — Task Execution and Scheduling (@Async)](https://docs.spring.io/spring-framework/reference/integration/scheduling.html) — docs.spring.io

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/) ← 지금 글
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
