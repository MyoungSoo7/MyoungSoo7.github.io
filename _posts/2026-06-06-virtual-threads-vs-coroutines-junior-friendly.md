---
layout: post
title: "주니어를 위한 Java Virtual Threads & Kotlin Coroutines 안내 — *왜* 두 개가 생겼고 *어떻게* 같은 문제를 *다른 길* 로 풀었는가"
date: 2026-06-06 02:00:00 +0900
categories: [java, kotlin, concurrency]
tags: [virtual-threads, project-loom, kotlin, coroutines, continuation, junior-friendly, async, structured-concurrency]
---

*"동기 코드가 그냥 빨라지면 안 되나요?"*

이 한 질문이 *언어 설계자들의 *지난 10 년 고민*** 이었고, 그 답이 **Virtual Threads (Java 21, 2023)** 와 **Coroutines (Kotlin, 2018)**. 둘은 *같은 질문* 에 *다른 답* 을 줬다.

이 글은 *시니어가 주니어 옆에 앉아* 천천히 설명하는 톤으로 — *왜* 두 기술이 생겼고, *어떻게* 같은 메커니즘 위에서 *다른 syntax* 로 풀었는지 정리한다. *책에는 안 나오는 *왜* 중심*.

---

## TL;DR — *주니어 가 알아야 할 한 줄*

> *동시성의 본질은 **"기다리는 시간에 다른 일* 하는 것**". *예전엔 OS thread 가 *기다림* 을 비싸게 처리* 했고, *지금은 *continuation* 으로 싸게 처리*. **Virtual Threads = Java 의 답, Coroutines = Kotlin 의 답.** *대부분의 *blocking 호출* 이 *내부적으로 non-blocking* 으로 처리됨* — 너 코드 변경 없이.

---

## 1. *왜* 동시성이 어려운가 — *비유* 부터

### 1.1 카페 알바 한 명

너가 카페 알바. 손님 *한 명* 받음:
1. 주문 받기 (5초)
2. 머신에서 *추출* 기다리기 (60초)
3. 손님에게 *건네기* (5초)

총 70초. 이 중 *60초 는 *기다리는 시간**. 너는 *추출 보는 중* 손가락 빨고 있음.

손님이 *5 명* 오면? *각자 70초씩 = 350초*.

### 1.2 *해결책 1 — 알바 더 고용 (Platform Thread)*

알바 5 명 고용. 각자 *한 손님 전담*. 총 *70초* 에 5 명 처리.

**문제:**
- 알바 1 명 *시급 12,000원*. 5 명 = *60,000원*.
- 알바가 *놀고 있는 60초* 도 *시급 지급*.

이게 *Java Platform Thread* 의 옛 모델. 1 thread = *1 OS thread* = *큰 비용 (RAM 1MB + OS context switch)*. 트래픽 폭증 시 *알바 1000 명* 고용 불가.

### 1.3 *해결책 2 — 알바 1 명 + *멀티태스킹**

알바 1 명. 60초 기다리는 동안 *다른 손님 주문* 받기:

```
시간:  0  5  10  15  20  ...  60  65  70
알바:  A  B  C   D   E   ...   (A 의 추출 끝, A 건네기)
```

이제 *1 명 알바 + 5 명 손님* = 약 *85초*.

**핵심:** *기다리는 시간을 *다른 일에 활용**.

이게 *Reactive Programming (RxJava, WebFlux)* 의 모델. *callback / Mono / Flux* 로 *기다림 사이 다른 일* 처리.

**문제:**
- 알바가 *각 손님 의 *진행 상태*** 를 *기억* 해야. *손님 A 의 9 단계 중 어디까지 왔지?* 메모.
- 코드도 *복잡* — `.then().flatMap().subscribe(...)` 의 *콜백 지옥*.

### 1.4 *해결책 3 — 같은 알바 1 명 + *알아서 멀티태스킹**

알바 1 명. 그런데 *알바가 알아서 *기다림 동안 다른 일* 함*. 너는 *코드 작성 시 "기다림"** 이 라고 적기만 하면 됨.

```python
# 알바가 알아서 처리
def serve_customer():
    order = take_order()       # 5초
    coffee = wait_for_brew()    # 60초 (이 동안 다른 손님 처리)
    deliver(coffee)             # 5초
```

코드는 *동기적* 으로 보이지만, *기다림 동안 알바 가 *알아서* 다른 일*. *알바의 *기억 부담* 도 *언어/런타임* 이 처리.

이게 **Virtual Threads** + **Coroutines** 의 모델.

---

## 2. *3 단계 진화* — 한 표로

| 모델 | 비유 | 코드 모양 | 단점 |
|---|---|---|---|
| **OS Thread** (Java < 21) | 알바 1000 명 | `Thread.sleep(60_000)` 그대로 | 자원 낭비, *동시 1000 한계* |
| **Reactive** (WebFlux 등) | 알바 1 + 명시적 콜백 | `.flatMap(x -> Mono.delay(...))` | 학습 곡선 ↑, 디버깅 어려움 |
| **Virtual Threads / Coroutines** | 알바 1 + 알아서 멀티 | `Thread.sleep(60_000)` *그대로* | (거의 없음, 일부 함정만) |

세 번째 모델 = **"코드는 옛 모양, 성능은 새 모양"**.

---

## 3. *Java 의 답* — Virtual Threads

### 3.1 *왜 *Project Loom*** 이라 불렀나

Java 의 *Virtual Threads* 는 **Project Loom** 의 결과 (2018 ~ 2023). 이름의 *Loom (직조기)* 비유:

```
Platform Thread (옛) : 굵은 실 1 개 = OS thread 1 개
Virtual Thread (새)  : 가는 실 N 개 = JVM 이 *몇 개 굵은 실* 에 *멀티플렉싱*
```

같은 *천 (애플리케이션 동시성)* 을 *적은 굵은 실 (OS thread)* 위에 *수많은 가는 실 (vthread)* 로 짜는 직조기.

### 3.2 *코드 — 이전 vs 이후*

**이전 (Platform Thread):**
```java
Thread t = new Thread(() -> {
    // ... 60 초 blocking IO
});
t.start();
```

**이후 (Virtual Thread, Java 21):**
```java
Thread t = Thread.ofVirtual().start(() -> {
    // ... 같은 60 초 blocking IO
});
```

**무엇이 바뀌었나?**
- 코드: `new Thread(...)` → `Thread.ofVirtual().start(...)` 한 줄
- 동작: blocking IO 동안 *carrier thread (OS thread) 를 떠남* → 다른 vthread 사용
- 한계: *동시 1000 → 10 만+*

### 3.3 *Spring Boot 사용자 의 *한 줄***

너가 Spring Boot 3.2+ 쓰는 중이면:

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

→ Tomcat 의 worker thread 가 *전부 Virtual Thread* 로 전환. *코드 0 변경*. 성능 *수배~수십배*.

### 3.4 *내부 동작* — *Continuation* 이라는 마법

```java
// 너 코드
Thread.sleep(60_000);
```

JDK 21 이 *이 한 줄을* 만났을 때:
1. *Continuation* (현재 stack 상태) 을 *저장*
2. *Carrier thread* (실제 OS thread) 를 *떠남*
3. 60 초 후 OS scheduler 가 깨움
4. 다시 *어떤 carrier thread* 에 *mount* → continuation *복원*
5. *마치 끊김 없이* 다음 줄 실행

**Continuation** = *"여기까지 했고, 다음에 여기서부터"* 의 *스냅샷*. *Java 21 의 *모든 blocking 호출* 이 이 메커니즘*.

### 3.5 *주니어 가 *바로 시도* 할 수 있는 한 줄*

```java
public static void main(String[] args) {
    var start = System.currentTimeMillis();
    try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
        for (int i = 0; i < 10_000; i++) {
            executor.submit(() -> {
                Thread.sleep(1000);   // 1 초 sleep
                return null;
            });
        }
    }
    var elapsed = System.currentTimeMillis() - start;
    System.out.println("10,000 vthread x 1s sleep: " + elapsed + "ms");
}
// 출력: 약 1100ms  ← 10,000 vthread 가 *동시에* 1 초 sleep
```

Platform Thread 였으면 *동시 1000 한계* 이라 약 *10 초* 이상.

---

## 4. *Kotlin 의 답* — Coroutines

### 4.1 *2018 — Kotlin 1.3* 정식 출시

Kotlin Coroutines 는 *Java 보다 *5 년 빨리** 같은 문제 풀었음.

```kotlin
// suspend 키워드 — *기다림이 가능한* 함수
suspend fun fetchUser(id: Long): User {
    delay(1000)                      // 비동기 sleep
    return userRepository.find(id)   // 비동기 DB 호출
}

// 호출
runBlocking {
    val user = fetchUser(42L)
    println(user)
}
```

### 4.2 *suspend* 키워드 의 *진짜 의미*

```kotlin
suspend fun fetchUser(id: Long): User { ... }
```

`suspend` = *"이 함수는 *기다림이 들어갈 수 있다*"* 라고 *컴파일러에게* 알림.

컴파일러 가 *내부적으로* state machine 으로 변환:

```kotlin
// 컴파일 후 (개념적)
fun fetchUser(id: Long, continuation: Continuation<User>): Any {
    when (continuation.label) {
        0 -> {
            continuation.label = 1
            delay(1000, continuation)
            return COROUTINE_SUSPENDED
        }
        1 -> {
            return userRepository.find(id)
        }
    }
}
```

*각 `suspend` 호출 지점이 *분기 (label)*** 가 됨. *기다림* 후 *재진입* 가능.

### 4.3 *Virtual Threads 와 *같은* Continuation*

두 기술의 *공통 메커니즘*:

```
함수 실행 중 "기다림" 만남
   ↓
현재 상태 (stack, local var, label) 를 *Continuation* 으로 저장
   ↓
Thread (carrier) 떠남
   ↓
기다림 끝나면 *어떤 thread* 에서 *Continuation 복원* → 계속 실행
```

**차이점:**
- *Kotlin*: 컴파일 시점에 *state machine* 생성 (`suspend` 함수만)
- *Java*: 런타임에 *continuation capture* (모든 blocking 호출)

---

## 5. *둘의 차이* — 같은 메커니즘, 다른 *사용자 경험*

### 5.1 *함수 색상 (Function Coloring)* — Kotlin 의 *문제*

```kotlin
fun normal() = "OK"                  // 일반 함수
suspend fun colored() = delay(100)    // suspend 함수

fun main() {
    normal()                         // ✅
    colored()                        // ❌ 컴파일 에러
    runBlocking { colored() }         // ✅ scope 안에서
}
```

→ *함수가 *두 색* (normal vs suspend)*. *normal 에서 suspend 호출 불가*. *Coroutine scope 필요*.

이게 *Bob Nystrom 의 "What Color is Your Function?" (2015)* 비판의 핵심. 라이브러리가 *normal 버전 + suspend 버전* 둘 다 만들어야 함.

**Virtual Threads 는 이 문제 *0*** — 모든 함수가 *그대로* 호출 가능.

### 5.2 *Structured Concurrency* — Kotlin 의 *강점*

```kotlin
suspend fun loadUserDetail(id: Long): UserDetail = coroutineScope {
    val profile = async { profileApi.fetch(id) }
    val orders = async { orderApi.list(id) }
    val photos = async { photoApi.list(id) }
    UserDetail(profile.await(), orders.await(), photos.await())
}
```

`coroutineScope` 의 *Structured Concurrency*:
- 모든 자식 (async) 가 *부모와 생명주기 연결*
- 부모 *취소* → 자식 *전부 취소*
- 자식 하나 *실패* → 부모 *예외 던짐*

Java 의 *대응 API* = `StructuredTaskScope` (JDK 21 preview, JDK 24+ stable):

```java
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Subtask<Profile> profile = scope.fork(() -> profileApi.fetch(id));
    Subtask<List<Order>> orders = scope.fork(() -> orderApi.list(id));
    scope.join().throwIfFailed();
    return new UserDetail(profile.get(), orders.get());
}
```

비슷한 의미, 다른 *syntax*. *try-with-resources* 가 *coroutineScope* 의 역할.

### 5.3 *Channel / Flow* — Kotlin 의 *독점 영역*

```kotlin
// Channel — producer-consumer
val channel = Channel<Order>()
launch {
    orders.forEach { channel.send(it) }
}
for (order in channel) {
    processOrder(order)
}

// Flow — cold stream
val ordersFlow: Flow<Order> = flow {
    repeat(100) { emit(fetchOrder(it)) }
}.flowOn(Dispatchers.IO)
 .filter { it.amount > 1000 }
 .map { it.toResponse() }
```

**Virtual Threads 는 이 추상화 없음**. *BlockingQueue + Virtual Thread* 조합으로 흉내내지만 *Coroutines 의 *backpressure / select* 같은 고급 기능* 은 *없음*.

---

## 6. *직접 비교* — 100 개 외부 호출

### Kotlin Coroutines
```kotlin
suspend fun aggregate(ids: List<Long>): List<Result> = coroutineScope {
    ids.map { async { externalApi.fetch(it) } }.awaitAll()
}
```
*5 줄.* 구조화된 동시성, 예외 자동 전파.

### Java Virtual Threads
```java
List<Result> aggregate(List<Long> ids) throws Exception {
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        List<Subtask<Result>> tasks = ids.stream()
            .map(id -> scope.fork(() -> externalApi.fetch(id)))
            .toList();
        scope.join().throwIfFailed();
        return tasks.stream().map(Subtask::get).toList();
    }
}
```
*8 줄.* 같은 의미, 약간 더 명시적.

둘 다 *Reactive (WebFlux) 의 콜백 체인* 보다 *훨씬 직관*. 비교용:

```java
// Reactive (WebFlux) — *예전 모양*
Flux<Result> aggregate(List<Long> ids) {
    return Flux.fromIterable(ids)
        .flatMap(id -> externalApi.fetch(id))
        .collectList()
        .flatMapMany(Flux::fromIterable);
}
```

*Reactive 코드 의 *학습 곡선*** 이 *Virtual Threads + Coroutines* 의 *진짜 가치*.

---

## 7. *주니어 가 *바로 시도* 할 수 있는 한 가지*

### Java (Spring Boot 3.2+)

`application.yml` 한 줄:

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

이게 다. Tomcat 의 worker thread 가 *전부 Virtual Thread* 로 전환. *외부 API 호출, DB query 같은 blocking 작업* 동안 *carrier thread 양보* → *동시 처리량 폭증*.

### Kotlin (Spring + Coroutines)

```kotlin
@RestController
class UserController(val service: UserService) {

    @GetMapping("/users/{id}")
    suspend fun getUser(@PathVariable id: Long): User {
        return service.findUser(id)
    }
}

class UserService {
    suspend fun findUser(id: Long): User = coroutineScope {
        val profile = async(Dispatchers.IO) { profileApi.fetch(id) }
        val orders = async(Dispatchers.IO) { orderApi.list(id) }
        User(profile.await(), orders.await())
    }
}
```

Spring 5+ 가 *Coroutine 직접 지원* — `suspend fun` controller method 그대로 가능.

---

## 8. *주니어 의 *흔한 5 질문***

### Q1. *Virtual Threads = Reactive 와 같은 거?*

**A: 아니다, 다른 추상화 수준이다.**
- *Reactive* = *명시적 콜백 / 스트림*. 학습 곡선 큼. *코드 모양이 완전 다름*.
- *Virtual Threads* = *blocking 코드 그대로*. 학습 곡선 작음. *코드 모양은 동기*.

목표는 같음 (*기다림 동안 다른 일*), 방법이 다름.

### Q2. *Coroutines = Thread 와 같은 거?*

**A: 아니다, *더 가볍다*.**
- *Thread* = OS thread (1 개 ~ 1MB RAM)
- *Coroutine* = *언어 추상화* (1 개 ~ 수 KB)

CoroutineScope 안의 *수십만 coroutine* 가능. Thread 는 *수천* 한계.

### Q3. *언제 *suspend* 키워드를 붙이나?*

**A: *기다림이 있는* 함수 만.**
```kotlin
suspend fun fetchUser(id: Long): User {     // ← 안에 delay/network call
    return apiClient.fetch(id)
}

fun computePi(n: Int): Double {              // ← 순수 CPU, suspend 불필요
    var pi = 0.0
    for (i in 0 until n) pi += 4.0 / (2*i+1)
    return pi
}
```

*CPU bound* 작업은 *suspend 불필요*. *IO bound* 만 suspend.

### Q4. *Spring 에서 *진짜로 *Virtual Threads 가 동작* 하는지 확인?*

**A:** Controller 에서 출력:
```java
System.out.println(Thread.currentThread());
// VirtualThread[#42]/...
// 또는
// Thread[platform-thread-N, ...]
```

`VirtualThread[#XX]` 가 *진짜 vthread*. Tomcat 의 *worker* 이름이 `tomcat-handler-XX` 면 *옛 모델*.

### Q5. *Coroutines + Virtual Threads 같이 쓰면?*

**A: 가능, 자연.**

Kotlin 1.7+ 의 `Dispatchers.IO.limitedParallelism(...)` 가 *Java 21 의 Virtual Thread carrier* 활용 가능. *Kotlin syntax + Virtual Thread* = 최선의 조합.

---

## 9. *함정 5 가지 — 시니어 가 자주 잡는 것*

### ❌ 함정 1: *synchronized + blocking IO (Pinning)*

```java
synchronized (lock) {
    httpClient.send(req);   // ❌ Virtual Thread *pin* — carrier 떠나지 못함
}
```

`synchronized` 블록 안의 *blocking IO* → Virtual Thread *carrier 점유 영원*. 다른 vthread 못 돔.

**JDK 21 의 한계**. JDK 24+ 에서 *완전 해결*. 지금은 `ReentrantLock` 으로:

```java
lock.lock();
try {
    httpClient.send(req);
} finally {
    lock.unlock();
}
```

### ❌ 함정 2: *ThreadLocal 남용*

```java
private static final ThreadLocal<UserContext> CTX = new ThreadLocal<>();
```

*Virtual Thread 마다 ThreadLocal 인스턴스* → *10 만 vthread = 10 만 인스턴스* → 메모리 폭증.

**해결:** `ScopedValue` (JDK 21+) — *immutable 한 scoped binding*:

```java
public static final ScopedValue<UserContext> CTX = ScopedValue.newInstance();

ScopedValue.where(CTX, userContext).run(() -> doWork());
```

### ❌ 함정 3: *DB Connection Pool 의 *역설**

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 10_000; i++) {
        executor.submit(() -> {
            try (Connection conn = dataSource.getConnection()) {  // ❌
                // ...
            }
        });
    }
}
```

vthread 10,000 개 → 모두 *DB connection 잡으려*. HikariCP *max 50* 이면 *9,950 vthread 가 *connection 대기**. *Virtual Thread 의 이점 상쇄*.

**해결:** DB connection pool 도 *적절히 늘림* (CPU × 2-4). 또는 *Semaphore 로 동시 호출 제한*.

### ❌ 함정 4: *CPU-bound 작업 에 vthread 사용*

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 1000; i++) {
        executor.submit(() -> calculatePi());   // ❌ CPU-bound
    }
}
```

CPU-bound 작업은 *carrier thread (CPU 코어 수)* 만 동시 실행 → *Virtual Thread 의 이점 0*.

**해결:** `Executors.newFixedThreadPool(CPU_CORES)` 사용. *Virtual Thread 는 IO-bound 만*.

### ❌ 함정 5: *blocking 코드 안의 *function coloring* 혼란 (Kotlin)*

```kotlin
// 일반 함수 안에서 suspend 호출
fun normal() {
    fetchUser(42L)   // ❌ Cannot invoke suspending function
}
```

해결: *runBlocking* 으로 *bridge*:
```kotlin
fun normal() {
    runBlocking {
        fetchUser(42L)   // ✅
    }
}
```

또는 *모든 함수 chain 을 suspend* 로:
```kotlin
suspend fun normal() {
    fetchUser(42L)   // ✅
}
```

---

## 10. *시니어 가 보는 *5 년 후***

### 10.1 Reactive Programming 의 *황혼*

WebFlux / RxJava 의 *학습 곡선 + 디버깅 어려움* 이 *Virtual Threads / Coroutines* 등장 후 *상대 가치 하락*. 신규 프로젝트의 *Reactive 채택 감소*. 단:
- *backpressure* 가 *진짜 critical* 한 영역 (스트리밍 데이터, 메시지 broker) 은 *여전히 Reactive*

### 10.2 *Java + Kotlin 의 *수렴**

- Java 21 의 *Virtual Threads* + *StructuredTaskScope* + *ScopedValue* = *Kotlin Coroutines 의 대부분 기능* 흡수
- Kotlin 의 *Dispatchers.IO* 가 *Java Virtual Threads* 의 backend 가능

**합쳐 쓰는 게 *최선*** — Kotlin syntax + JVM 21+ Virtual Threads.

### 10.3 *함정 의 *해결**

- JDK 24+ 에 *synchronized pinning* 완전 해결 예정
- Kotlin 의 *Channel / Flow* 같은 추상화 가 *Java 에도* 진입 (java.util.concurrent.Flow 등)

---

## 11. *주니어 에게 *마지막 한 마디**

10 년 전 *Reactive Programming* 의 시대를 *건너뛰고* 바로 *Virtual Threads / Coroutines* 시대에 진입한 너희는 *행운*. *콜백 지옥* 의 트라우마 없이 *동기 코드 의 직관* 으로 *높은 동시성* 가능.

**기억할 3 줄:**

1. **동시성 의 본질 = 기다림 동안 *다른 일*** — *기다림* 을 *싸게* 처리 하는 게 진화
2. **Continuation 메커니즘** — Java *Virtual Threads* + Kotlin *Coroutines* 가 *같은 마법*
3. **Spring Boot 사용자는 `spring.threads.virtual.enabled=true` 한 줄** — 그게 다.

추가 학습:
- *synchronized pinning 함정* — JDK 24 까지 *주의*
- *ThreadLocal → ScopedValue* 전환
- *Coroutines 의 Channel / Flow* — 본격 분산 시스템에 *유용*

이게 너의 *동시성 학습 첫 단원*. 다음 단원 = *backpressure, debouncing, retry strategy* 등 *고급 패턴*. 천천히 가자.

---

## 참고

- *Java Concurrency in Practice* — Brian Goetz (2006) — *Virtual Threads 이전 시대*
- *Kotlin Coroutines Deep Dive* — Marcin Moskała (2022)
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [Kotlin Coroutines Guide](https://kotlinlang.org/docs/coroutines-guide.html)
- *Bob Nystrom — What Color is Your Function?* (2015)
- *Roman Elizarov — Structured Concurrency* (KotlinConf 2019)
- 관련 글:
  - [Java 21 Virtual Threads 실전 사례 5가지 vs Coroutines]({% post_url 2026-06-05-virtual-threads-real-cases-vs-kotlin-coroutines %})
  - [JVM 구조와 Java 버전 변천사]({% post_url 2026-05-29-jvm-structure-java-version-evolution-production-impact %})
  - [Java vs Kotlin ROI]({% post_url 2026-05-29-java-vs-kotlin-roi-break-even-claude-code-ai-coding %})
  - [프록시 패턴 시니어→주니어]({% post_url 2026-06-06-proxy-pattern-dynamic-proxy-spring-aop-explained %})
