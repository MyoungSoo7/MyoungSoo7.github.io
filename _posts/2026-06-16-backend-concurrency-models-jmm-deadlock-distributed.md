---
layout: post
title: "백엔드 *동시성* — *5 가지 모델 (Thread+Lock · Async · Reactive · CSP · Actor)*, *Java Memory Model 의 happens-before*, *Deadlock·Race·Visibility 의 3 대 함정*, *분산 동시성* 까지의 *체계화*"
date: 2026-06-16 17:30:00 +0900
categories: [backend, concurrency, jvm]
tags: [concurrency, parallelism, java, jmm, happens-before, volatile, atomic, locks, synchronized, reentrantlock, executor, completablefuture, virtual-threads, reactive, csp, actor, goroutine, coroutine, deadlock, race-condition, distributed-lock, saga, cap]
---

*동시성 (concurrency)* 은 *대부분 의 *production 사고* 의 *마지막 한 줄*. *디버깅 가능 한 사고 의 *비율 이 *극도로 낮은 자리*. *경험 적으로 *5 년 차 백엔드 개발자 가 *마주칠 사고 의 *80% 가 *동시성 의 어떤 변형**. 그러나 *학교 와 교과서* 에서는 *동시성 의 *진짜 깊이 가 *충분히 다뤄지지 않음*. *Race condition*, *visibility*, *ordering*, *deadlock* — *4 가지 의 *각각 다른 메커니즘 의 *각각 다른 진단* 이 *서로 섞이면 *진짜 의 *현장 디버깅 의 *지옥**.

이 글은 *백엔드 동시성 의 *완결적 체계*. **(1) *동시성 ≠ 병렬성***, **(2) *5 가지 모델 (Thread+Lock · Async · Reactive · CSP · Actor)***, **(3) *Java Memory Model 의 *happens-before***, **(4) *3 대 함정 — Race / Visibility / Ordering***, **(5) *Deadlock 의 4 조건 과 *우회***, **(6) *실무 패턴 5 가지***, **(7) *분산 동시성* — *분산 락 / Saga / CAP***, **(8) *학습 로드맵***. 어제 [자바 Virtual Thread](https://myoungsoo7.github.io) / [Discord Go→Rust](https://myoungsoo7.github.io) 글 의 *상위 frame*.

---

## TL;DR

**핵심 통찰 3 가지**:

1. *동시성 ≠ 병렬성*. 동시성 = *여러 일 이 *교차 실행* 의 *구조*, 병렬성 = *물리 적 으로 *동시 실행*. *Go 의 Rob Pike*: *"Concurrency is about *dealing with* lots of things at once. Parallelism is about *doing* lots of things at once."*
2. *동시성 의 *함정 은 *3 종*: *race condition (atomicity)*, *visibility (한 thread 의 쓰기 가 다른 thread 에 *언제 보이는지*)*, *ordering (코드 순서 ≠ 실행 순서)*. *셋 이 *각각 다른 메커니즘*, *각각 다른 도구*.
3. *분산 동시성 도 *같은 함정 의 *분산 버전*. *분산 락 / Saga / Exactly-once 의 모든 어려움 의 *근원 이 *동시성 의 *분산 화*.

**5 가지 모델 의 한 줄 비교**:

| 모델 | 대표 | 비유 |
|---|---|---|
| Thread + Lock | Java 전통, C/C++ | *공유 화이트보드 에 *순서 대로 *쓰기* |
| Async / Callback | Node.js, JavaScript | *나중에 결과 가 *돌아온다* 약속* |
| Reactive Stream | Reactor, RxJava | *Pull 이 아닌 *Push* + 역압* |
| CSP (Channel) | Go goroutine | *공유 메모리 X — *메시지 로 통신** |
| Actor | Erlang, Akka | *독립 적 객체 가 *메시지 로 협력* |

**실무 함의**: *동시성 의 *고수 가 되는 길 은 *모델 1 개 깊이 + 다른 4 개 의 *얕은 어휘**. *Java 백엔드* 라면 *Thread + Lock + Async/CompletableFuture + Virtual Thread* 가 *깊이 자리*. *Reactive 와 Actor 는 *어휘 만**.

---

## 0. *동시성 ≠ 병렬성*

```
동시성 (Concurrency):
   Thread A: ━━━━━┓     ┏━━━━━━━┓     ┏━
   Thread B:      ┗━━━━━┛       ┗━━━━━┛
   ← *교차 실행*, *단일 CPU 코어 가능*

병렬성 (Parallelism):
   Core 1 (Thread A): ━━━━━━━━━━━━━
   Core 2 (Thread B): ━━━━━━━━━━━━━
   ← *진짜 동시 실행*, *다중 CPU 코어 필요*
```

*동시성 은 *구조*, 병렬성 은 *물리적 사실*. *동시성 을 *잘 설계 한 코드 는 *병렬성 의 이익 도 누릴 수 있다*. 반대 는 성립 안 한다 — *병렬 실행 만 으로 는 *race condition 안 풀린다*.

### 0-1. *Rob Pike 의 우아한 정의*

> *"Concurrency is about *dealing with* lots of things at once. Parallelism is about *doing* lots of things at once."*

*100 개 의 task 가 *서로 다른 진도 의 *어딘가에* 있다 → 동시성*. *100 개 의 task 가 *지금 이 순간 *모두 실행* → 병렬성*. *둘은 *다른 차원의 개념*.

---

## 1. *5 가지 동시성 모델*

### 1-1. *Thread + Lock — *전통적 *공유 메모리**

```java
class Counter {
    private int value;

    public synchronized void increment() {
        value++;   // *원자성 보호*
    }
}
```

*가장 오래된 모델*. *공유 메모리 의 *임계 영역* 을 *lock 으로 보호*. *직관 적 이지만 *deadlock·race 의 *원천*. *모든 다른 모델 의 *기준점*.

**장점**: 직관적, 모든 언어 지원
**단점**: *lock 의 사슬 이 길면 deadlock, *lock 의 사슬 이 짧으면 *race condition*

### 1-2. *Async / Callback / Promise — *완료 의 약속**

```javascript
// JavaScript / Node.js
fetch(url)
  .then(res => res.json())
  .then(data => process(data))
  .catch(err => log(err));
```

*결과 가 *나중에 *돌아온다 의 약속*. *callback hell* → *Promise 체이닝* → *async/await 의 진화*. *I/O 바운드 의 *대부분 의 시간 을 *대기 가 아닌 *다른 일 에 쓴다*.

**장점**: 단일 thread 로 *수만 동시 I/O*
**단점**: *코드 가 *non-linear*, *스택 추적 의 *맥락 손실*

### 1-3. *Reactive Stream — *Push + 역압**

```java
// Reactor (Spring WebFlux)
Mono.fromCallable(() -> fetchData(id))
    .flatMap(this::process)
    .timeout(Duration.ofSeconds(5))
    .onErrorReturn(Fallback.DEFAULT)
    .subscribe(this::handleResult);
```

*Stream 처럼 *데이터 가 흐른다* — *Pull (조회) 아닌 Push (구독)*. *역압 (Backpressure)* — *소비자 가 느리면 *생산자 가 *멈춤*. *분산 시스템 의 *큐 의 폭주 방지*.

**장점**: *역압 의 *언어 차원 표현*
**단점**: *복잡성 의 *학습 곡선 큼*

### 1-4. *CSP (Communicating Sequential Processes) — *Go 의 길**

```go
// Go goroutine + channel
ch := make(chan int)

go func() {
    ch <- compute()    // 송신
}()

result := <- ch          // 수신
```

*Tony Hoare 의 1978 년 모델*. *"공유 메모리 로 통신 하지 말고 *통신 으로 메모리 를 공유 하라"*. *공유 변수 X — *채널 의 메시지 만**.

**장점**: *간결한 표현력*, *race condition 자체 의 *근본 적 회피*
**단점**: *channel 의 *과다 사용 시 *디버깅 어려움*

### 1-5. *Actor — *독립 적 객체 의 *협력**

```scala
// Akka
class Counter extends Actor {
  var value = 0
  def receive = {
    case Increment => value += 1
    case Get => sender() ! value
  }
}
```

*Carl Hewitt 의 1973 년 모델*. *모든 단위 가 *Actor* — *자기 상태 + *메시지 큐* + *행동*. *공유 메모리 X — 메시지 만*. *분산 시스템 에 *자연 스럽게 확장*.

**장점**: *분산 의 *자연 스러운 확장* (Erlang 의 *전화 교환기*)
**단점**: *언어 / 프레임워크 의 *깊은 종속*

### 1-6. *M:N 경량 스레드 — *Virtual Thread / Coroutine / goroutine**

```java
// Java 21+
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 1_000_000)
        .forEach(i -> executor.submit(() -> handle(i)));
}
```

*Thread + Lock 의 *코드 모양 그대로* + *수백만 동시성*. *어제 [Virtual Thread 글](https://myoungsoo7.github.io) 의 본질*. *2026 의 *Java 백엔드 의 *기본 도구*.

**장점**: *sync 코드 + async 효과*
**단점**: *pinning 의 함정* (Java 24 이전)

---

## 2. *Java Memory Model (JMM) — *모든 함정 의 *공통 토대**

### 2-1. *3 대 함정*

| 함정 | 정의 | 대응 도구 |
|---|---|---|
| **Race Condition** | *원자 적 으로 보아야 할 동작 이 *분리 실행* | `synchronized`, `Atomic*`, `Lock` |
| **Visibility** | *한 thread 의 쓰기 가 *다른 thread 에 *언제 보이는지 *불명* | `volatile`, `synchronized` |
| **Ordering** | *코드 의 순서 ≠ *실제 실행 순서* (컴파일러 / CPU 최적화) | `volatile`, `synchronized`, *happens-before* |

*셋 이 *서로 다른 함정*. *셋 이 *서로 다른 도구*. *혼동 하면 *방어 가 *부분 적*.

### 2-2. *Visibility 의 충격적 예제*

```java
class Worker {
    private boolean running = true;    // ❌

    public void stop() { running = false; }

    public void run() {
        while (running) {
            doWork();
        }
    }
}
```

*"main 이 stop() 호출 → worker 가 종료" — *직관 적*. *그러나 *JMM 의 *시각* 에서 — *worker thread 가 *영원히 안 멈출 수 있다*.

이유: *worker thread 의 *컴파일러 가 *while 조건 의 *running 을 *레지스터 에 캐시* + *다른 thread 의 변경 을 *영원히 안 본다*. *JIT 최적화 의 정공*.

해결: `volatile boolean running = true;`. *모든 쓰기 가 *즉시 *모든 thread 에 가시화*.

### 2-3. *Happens-Before 관계*

JMM 의 *공식 규칙*:

- **Program order**: 같은 thread 의 *문장 의 순서*
- **Monitor lock**: `synchronized` 의 *unlock → 다음 lock 가 *해당 변화 를 본다*
- **Volatile**: `volatile` 의 *쓰기 → 다음 읽기 가 *해당 변화 를 본다*
- **Thread start/join**: `t.start()` 직전 의 모든 동작이 *t 의 모든 동작 보다 *먼저*. `t.join()` 직후 *t 의 모든 동작 이 *현 thread 보다 *먼저*.
- **Atomic operations**: `AtomicInteger.compareAndSet()` 등

*이 관계 가 *성립 안 하면 — *visibility / ordering 의 *함정 발생*. *동시성 코드 의 *모든 디버깅 의 출발*.

---

## 3. *Deadlock 의 *4 조건* 과 *우회*

### 3-1. *Coffman 의 *4 조건* (1971)*

deadlock 발생 의 *필요 조건* — 4 가지 모두 만족 시 발생 가능:

1. **Mutual Exclusion** — 자원 이 *공유 불가*
2. **Hold and Wait** — *자원 을 잡은 채 *다른 자원 을 기다림*
3. **No Preemption** — *자원 을 *강제 회수 못 함*
4. **Circular Wait** — *순환 의존성*

*하나 만이라도 깨면 *deadlock 불가능*. *대부분의 우회 가 *Circular Wait 제거*.

### 3-2. *대표 deadlock 의 코드*

```java
// Thread 1
synchronized(lockA) {
    synchronized(lockB) {           // ← lockB 대기
        ...
    }
}

// Thread 2
synchronized(lockB) {
    synchronized(lockA) {           // ← lockA 대기
        ...
    }
}

// 두 thread 가 *동시에 *첫 lock 까지 진입* → 영원히 대기
```

### 3-3. *Lock Ordering — *정공*

```java
// 모든 thread 가 *항상 *lockA → lockB 순* 으로 잡음
synchronized(lockA) {
    synchronized(lockB) {
        ...
    }
}
```

*Circular Wait 제거*. *간단 + 효과*.

### 3-4. *Try-Lock + Timeout — *실전 대안**

```java
if (lockA.tryLock(1, SECONDS)) {
    try {
        if (lockB.tryLock(1, SECONDS)) {
            try {
                // 안전한 작업
            } finally {
                lockB.unlock();
            }
        }
    } finally {
        lockA.unlock();
    }
}
```

*deadlock 의 *최대 *대기 시간 제한*. *No Preemption 조건 우회*.

---

## 4. *Java 의 *동시성 도구 함**

### 4-1. *낮은 수준 (Low Level)*

| 도구 | 용도 |
|---|---|
| `synchronized` | 임계 영역 보호 (monitor lock) |
| `volatile` | visibility + 부분 적 ordering |
| `ReentrantLock` | `synchronized` 의 *확장* (try, timeout, fair) |
| `ReadWriteLock` | *읽기 다수 / 쓰기 단일* |
| `StampedLock` | *optimistic read* |
| `AtomicInteger / AtomicLong / AtomicReference` | CAS 기반 *lock-free* |

### 4-2. *중간 수준*

| 도구 | 용도 |
|---|---|
| `ConcurrentHashMap` | thread-safe HashMap |
| `BlockingQueue` (`LinkedBlockingQueue`, `ArrayBlockingQueue`) | *Producer-Consumer 의 표준* |
| `Semaphore` | *동시 N 개* 제한 |
| `CountDownLatch` | *N 개 작업 완료 대기* |
| `CyclicBarrier` | *N 개 thread 의 *동기화 지점* |
| `Phaser` | 동적 N 개 thread *세대 별 동기화* |

### 4-3. *높은 수준*

| 도구 | 용도 |
|---|---|
| `ExecutorService` | *Thread 의 *생성 추상화* |
| `CompletableFuture` | *비동기 결과 합성* |
| `ForkJoinPool` | *재귀 분할 정복* |
| `Stream.parallel()` | *데이터 병렬* |
| `Virtual Thread` (Java 21+) | *경량 thread* |
| `StructuredTaskScope` (Java 25+) | *부모-자식 thread 의 생명주기 묶기* |

*대부분 의 실무 코드 는 *높은 수준 만* 만지면 *충분*. *낮은 수준 은 *디버깅 + 라이브러리 작성 의 영역*.

---

## 5. *실무 패턴 5 가지*

### 5-1. *Thread-Safe Singleton*

```java
public class Singleton {
    private static volatile Singleton instance;

    public static Singleton getInstance() {
        if (instance == null) {                      // 1st check (no lock)
            synchronized (Singleton.class) {
                if (instance == null) {              // 2nd check (with lock)
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}
```

*Double-Checked Locking*. *volatile 의 *역할 이 핵심* — *부분 초기화 된 객체* 가 *다른 thread 에 보이는 사고* 방지.

### 5-2. *Producer-Consumer*

```java
BlockingQueue<Task> queue = new LinkedBlockingQueue<>(1000);

// Producer
new Thread(() -> {
    while (true) {
        Task t = generateTask();
        queue.put(t);    // 가득 차면 블록
    }
}).start();

// Consumer
new Thread(() -> {
    while (true) {
        Task t = queue.take();    // 비면 블록
        process(t);
    }
}).start();
```

*가장 흔한 패턴*. *큐 의 크기 가 *역압 의 표현*.

### 5-3. *Fan-out / Fan-in*

```java
List<Long> ids = ...;
List<CompletableFuture<Result>> futures = ids.stream()
    .map(id -> CompletableFuture.supplyAsync(() -> fetch(id)))
    .toList();

List<Result> results = futures.stream()
    .map(CompletableFuture::join)
    .toList();
```

*N 개 작업 의 *병렬 실행* + *모두 완료 대기*. *외부 API N 개 호출* 의 표준.

### 5-4. *Rate Limiting (Semaphore)*

```java
Semaphore externalApi = new Semaphore(10);  // 동시 10 호출 제한

void call() {
    externalApi.acquire();
    try {
        externalApi.call();
    } finally {
        externalApi.release();
    }
}
```

*외부 API 의 rate limit 보호* + *우리 thread pool 의 고갈 방지*.

### 5-5. *Distributed Lock*

```java
// Redisson 의 분산 락
RLock lock = redisson.getLock("order:" + orderId);
lock.lock(10, TimeUnit.SECONDS);
try {
    processOrder(orderId);
} finally {
    lock.unlock();
}
```

*JVM 간* lock. *Redis, ZooKeeper, etcd* 기반. *분산 환경 의 *공유 자원 보호*.

**주의**: *분산 락 의 *neverending 정확성 문제 (lease 만료 vs 작업 시간) — *Martin Kleppmann 의 *Redlock 비판* 의 본질*. *진짜 정확성 이 필요 하면 *Outbox 패턴 + 멱등 처리* 가 정공.

---

## 6. *흔한 함정 5 가지*

### 6-1. *HashMap 의 thread-unsafe 사용*

*JDK 7 이전* 의 HashMap 에 *동시 put → 내부 리스트 의 순환 → 영원한 spin*. *jstack 의 CPU 100%*. JDK 8 이후 는 무한 루프 는 없지만 *데이터 손상* 은 여전. *ConcurrentHashMap* 이 정공.

### 6-2. *SimpleDateFormat — *thread-unsafe**

```java
// ❌
private static final SimpleDateFormat FMT = new SimpleDateFormat(...);

// ✅
private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern(...);
```

*Java 8 의 `DateTimeFormatter` 는 *불변 + thread-safe*. *예외 적 사고 의 *간접 원인*.

### 6-3. *Lock 의 *비공정성**

```java
ReentrantLock lock = new ReentrantLock();   // ❌ 기본 unfair
ReentrantLock lock = new ReentrantLock(true); // ✅ fair
```

*기본 lock 은 *비공정* — *어떤 thread 가 먼저 기다렸어도 *나중 thread 가 받을 수 있음*. *starvation 의 원인*.

### 6-4. *CompletableFuture 의 *예외 처리 누락**

```java
CompletableFuture.supplyAsync(() -> {
    throw new RuntimeException("boom");
});
// ↑ 예외 가 *영원히 *조용히 사라짐*. log 도 안 남음.
```

*반드시 `.exceptionally()` 또는 `.handle()` 으로 처리*. *누락 시 *고스트 버그*.

### 6-5. *ThreadLocal 의 *메모리 누수**

*Tomcat 의 *스레드 풀* + *ThreadLocal 의 *제거 누락* = *thread 재사용 시 *이전 요청 의 데이터 누수* + *메모리 누수*. *반드시 `try-finally` 의 `remove()`*.

---

## 7. *분산 동시성*

### 7-1. *같은 함정 의 *분산 버전**

- *Race condition* → *분산 작업 의 순서*
- *Visibility* → *복제 본 의 *시간 차*
- *Deadlock* → *분산 락 의 순환*
- *Atomicity* → *분산 트랜잭션*

### 7-2. *Distributed Transaction 의 *근본 한계**

*Two-Phase Commit (2PC)* — *coordinator + participants 의 prepare → commit*. *coordinator 다운 시 *모든 participant 가 *영원히 대기* (blocking).

*Three-Phase Commit (3PC)* — *blocking 일부 해결* 시도. *현실 적으로 *복잡 + 느림*.

*그래서 — Microservices 시대 의 *기본 정공* = *Saga 패턴*. *2PC 포기 + *보상 트랜잭션 (compensating transaction)*.

### 7-3. *Saga 패턴*

```
주문 ───→ 결제 ───→ 재고 ───→ 배송
                     ↓ 실패
                  *재고 보상* ← *결제 보상* ← *주문 보상*
```

*각 단계 의 *역방향 보상 함수* 정의*. *부분 실패 시 *역순 보상*. *최종 일관성 (eventual consistency)*.

### 7-4. *Exactly-Once 의 *환상**

*"메시지 가 *정확히 *한 번 처리"* — *분산 시스템 에서 *근본 적으로 *불가능*. 가능 한 보장:

- *At-most-once*: 0~1 회 (손실 가능)
- *At-least-once*: 1+ 회 (중복 가능)

*"Exactly-once" 는 *at-least-once + 멱등 (idempotent) 처리 의 *조합* 으로만 *시뮬레이션*. *결제, 송금 등 의 *진짜 한 번* 도 *Idempotency-Key + processed_events 의 *3 단 멱등*.

### 7-5. *CAP 정리 와 의 연결*

*분산 동시성 = CAP 의 *현실 적 표현*. *Consistency (강한 일관성) ↔ Availability ↔ Partition tolerance*. *셋 동시 만족 불가능*. *대부분 의 분산 DB 는 *AP (eventual consistency) + *Optional strong consistency*.

---

## 8. *학습 로드맵*

| 단계 | 집중 | 책 |
|---|---|---|
| 1 | *Thread + Lock 의 *기초* (Java) | *자바 병렬 프로그래밍* (Brian Goetz, 한국어 번역 *자바 컨커런시 인 프랙티스*) |
| 2 | *java.util.concurrent 의 *높은 수준 도구* | 위 책 + *모던 자바 인 액션* |
| 3 | *Virtual Thread 와 *Structured Concurrency* | JEP 444, 506 |
| 4 | *CompletableFuture 의 *합성* | *Java 8 in Action* |
| 5 | *Reactive Stream (Reactor)* — *어휘 적 이해* | *Hands-On Reactive Programming in Spring 5* |
| 6 | *CSP (Go) / Actor (Akka) — *모델 의 시각* | Rob Pike 의 *Concurrency is not Parallelism* 강연 |
| 7 | *분산 동시성 — Saga / 분산 락 / Outbox* | *Microservices Patterns* (Chris Richardson) |
| 8 | *깊이 1 + 다른 4 의 *얕은 어휘* | (개인 선택) |

### 8-1. *최소 어휘* 한 줄 정리

- *Race Condition* — *원자 적 으로 보아야 할 일 이 *분리 실행*
- *Visibility* — *한 thread 의 쓰기 가 *다른 thread 에 *언제 보이는지*
- *Happens-Before* — *JMM 의 *순서 보장 규칙*
- *Deadlock* — *Coffman 의 4 조건* 의 동시 발생
- *Lock Ordering* — *순환 의존성 제거 의 정공*
- *Producer-Consumer* — *BlockingQueue 의 표준 패턴*
- *Saga* — *분산 트랜잭션 의 *보상 트랜잭션* 우회
- *Exactly-once* — *환상*. *At-least-once + 멱등* 이 실현
- *Outbox 패턴* — *DB transaction 과 *메시지 발행* 의 원자성

---

## 9. *마무리* — *동시성 의 *겸손*

*"동시성 코드 를 *짤 줄 안다" 는 *경험 적으로 *진짜 시니어 의 *시그널* 중 하나*. *직관 이 *통하지 않는 자리*. *학습 + 실패 + 디버깅 의 *수년 적 축적*.

*Brian Goetz* (Java 의 동시성 거장):

> *"The only reliable way to know if your code is correct is to *prove* it. Testing is necessary, but not sufficient."*

*동시성 코드 는 *테스트 만 으로 정확성 보장 불가*. *JMM 의 happens-before 규칙 의 *논리적 검증* 까지 필요. *이게 *동시성 의 *진짜 어려움*. 그리고 그 어려움이 *동시성 의 *시니어 적 가치 의 *원천*.

기억 할 *세 줄*:

1. *동시성 의 *3 대 함정* — race, visibility, ordering — 은 *각각 다른 메커니즘 의 *각각 다른 도구*.
2. *Java 백엔드* 에서는 *높은 수준 도구* (ExecutorService, CompletableFuture, ConcurrentHashMap, Virtual Thread) 가 *95% 의 정공*. *낮은 수준 (synchronized, volatile) 은 *디버깅 의 영역*.
3. *분산 동시성 = 같은 함정 의 *분산 버전* + CAP 의 *피할 수 없는 trade-off*. *Saga + Outbox + 멱등 의 *세 패턴* 이 *현대 적 정공*.

*"동시성 의 *고수 가 되는 길 — *수많은 production 사고 의 *디버깅 의 *수년 적 *축적**. *수업 만 으로 도 다 가지 못한다*. *실패 와 함께 자란다*. 그래서 *동시성 의 *진짜 깊이 를 *아는 개발자 의 *시장 가치 가 *그토록 높은 것**." — *글 의 한 줄 결론*.
