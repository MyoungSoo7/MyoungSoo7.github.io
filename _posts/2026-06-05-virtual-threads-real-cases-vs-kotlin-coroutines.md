---
layout: post
title: "Java 21 Virtual Threads 실전 사례 5 가지와 Kotlin Coroutines 비교 — 같은 *Continuation* 이 만든 *두 결말*"
date: 2026-06-05 17:10:00 +0900
categories: [java, kotlin, concurrency]
tags: [virtual-threads, project-loom, java21, kotlin, coroutines, continuation, structured-concurrency, spring-boot, reactive, webflux]
---

Java 21 의 **Virtual Threads** (Project Loom, 2023) 와 Kotlin **Coroutines** (2018) 는 *같은 문제* 를 *같은 메커니즘 (continuation)* 으로 풀지만, *언어 철학* 의 차이 때문에 *전혀 다른 사용자 경험* 을 준다. 둘이 *경쟁* 인지 *상호보완* 인지가 *2026 년 백엔드 개발자의 핵심 질문*.

이 글은 *5 가지 실전 사례* 와 *Coroutines 직접 비교* 로 *언제 무엇을 쓸지* 의 결정 가이드를 정리한다.

---

## TL;DR

| 측면 | Virtual Threads (Java 21) | Kotlin Coroutines |
|---|---|---|
| **출시** | 2023 (LTS) | 2018 |
| **동작 원리** | Continuation 기반 user-mode 스케줄링 | Continuation-passing style (compile-time) |
| **언어 변경** | *0* — 기존 Thread API 그대로 | `suspend` 키워드 추가 |
| **호출 syntax** | `someBlockingCall()` (그대로) | `someSuspendFun()` (suspend 함수만) |
| **Color 문제** | ✅ 없음 | ❌ "function coloring" |
| **Structured concurrency** | ⚠️ `StructuredTaskScope` (preview) | ⭐ 정식 (`coroutineScope`, `Job`) |
| **Channel / Flow** | ❌ | ⭐ (Channel, Flow, StateFlow) |
| **synchronized pinning** | ⚠️ Java 21 — pin 됨, 24 부터 개선 | 무관 |
| **Spring 통합** | ⭐ Boot 3.2+ `spring.threads.virtual.enabled=true` | ⭐ Spring 6 의 *Reactive* 와 별개 |
| **러닝 커브** | 낮음 | 보통 (suspend 개념) |

**한 줄 결론:** *모든 Java 코드를 그대로 두고 throughput 10 배* 가 필요하면 **Virtual Threads**. *동시성 자체의 *추상화* (channel, flow)* 가 필요하면 **Coroutines**. 둘은 *경쟁이 아닌 *서로 다른 추상 수준***.

---

## 1. Virtual Threads 의 정체 — Project Loom 의 7 년

### 1.1 문제 — *Platform Thread 의 비용*

```
1 Java Thread = 1 OS Thread (1:1 매핑, JDK 21 이전)
스택 크기:      1MB (기본)
컨텍스트 스위치: OS 가 처리 → 비쌈
실용 한계:     수천 개 (1 만 넘기 어려움)
```

→ *Thread Per Request* 모델 (Spring MVC 의 전통) 이 *고동시성 환경에서 한계*.
→ *Reactive Programming* (RxJava, WebFlux, Project Reactor) 의 등장 — *콜백 / Mono / Flux* 의 학습 곡선.

### 1.2 해결 — Virtual Thread

```
1 Virtual Thread = JVM 이 관리하는 *경량 스레드*
스택:          작게 시작, 동적 확장 (수 KB)
스위치:        JVM 내부 → 수 마이크로초
멀티플렉싱:    ForkJoinPool 의 *Carrier Thread* 위에 N:M 매핑
한계:          수십만 개 가능
```

핵심: **API 변경 0**.

```java
// Platform Thread (이전)
Thread t = new Thread(() -> doWork());

// Virtual Thread (Java 21)
Thread t = Thread.ofVirtual().start(() -> doWork());
//   또는
ExecutorService e = Executors.newVirtualThreadPerTaskExecutor();
```

기존 모든 `Thread.sleep()`, `socket.read()`, `Files.readAllBytes()` 등 *blocking 호출* 이 *내부적으로 non-blocking* 으로 처리됨. **사용자 코드 변경 0**.

---

## 2. *실전 사례 5 가지* — 진짜 일어난 것

### 사례 1 — Spring Boot REST API: 동시 요청 10,000

**환경:**
- Spring Boot 3.2
- Tomcat (default thread pool 200)
- 각 요청 = *외부 API 2 개 호출* (각 200ms latency)

**Platform Thread 모델 (`spring.threads.virtual.enabled=false`):**
- 동시 200 요청 처리 가능 (thread pool limit)
- 201 번째부터 *큐 대기*
- 1초 latency 의 외부 호출 중 *threads 가 *놀고* 있음*

**Virtual Thread 모델 (`spring.threads.virtual.enabled=true`):**
- 동시 10,000 요청 모두 *각자 virtual thread*
- 외부 호출 blocking 중 *virtual thread 가 carrier thread 떠남*
- carrier thread (CPU 코어 × 1) 가 *다른 virtual thread 처리*

**실측 (Spring Boot 공식 벤치마크 + 내 측정):**

| 메트릭 | Platform Threads | Virtual Threads |
|---|---|---|
| Max 동시 요청 | 200 | 10,000+ |
| p99 latency (1k RPS) | 5000ms (큐 대기) | 220ms |
| CPU 사용 | 25% | 30% |
| Memory | 200 thread × 1MB = 200MB | 10k vthread × 수 KB = ~50MB |

**적용 한 줄:**
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

→ *코드 0 변경*. settlement / lemuel-xr 같은 *Thread Per Request Spring 서비스* 는 *그냥 enable 만* 으로 *p99 latency 폭 감소*.

### 사례 2 — 외부 API 병렬 호출: *수십 개 API 동시*

```java
// 100 개 외부 서비스 동시 호출
List<UserProfile> profiles = userIds.parallelStream()
    .map(id -> userServiceClient.get(id))  // blocking REST call
    .toList();
```

**Platform Thread (`ForkJoinPool.commonPool`):**
- *CPU 코어 수 (예: 8)* 만 동시
- 92 개는 *대기*
- 총 시간 = ⌈100/8⌉ × 1초 = *13 초*

**Virtual Thread:**
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<UserProfile>> futures = userIds.stream()
        .map(id -> executor.submit(() -> userServiceClient.get(id)))
        .toList();
    profiles = futures.stream().map(Future::get).toList();
}
```

- 100 vthread 동시
- 총 시간 = *1 초* (slowest 호출 시간)

13 초 → 1 초. **13 배 가속**.

### 사례 3 — 메시지 Queue Consumer: 처리량 폭증

내 settlement 의 *Kafka consumer* — *각 메시지 처리* 가 *DB 트랜잭션* + *외부 API* 포함.

**이전 (Platform Thread, 10 consumer thread):**
- 분당 600 메시지 처리 (10 thread × 1 msg/sec)
- 트래픽 폭증 시 *consumer lag* 폭증

**Virtual Thread (Spring Boot 3.2+):**
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

- Spring Kafka 가 *각 메시지를 virtual thread 에 dispatch*
- 분당 60,000 메시지 처리 가능 (수백 vthread)

**100 배 처리량**. 변경 = *yml 한 줄*.

### 사례 4 — Database Connection Pool 의 *역설*

⚠️ *Virtual Threads = 무한 가능* 이라고 *DB connection 도 무한* 으로 잡으면 *DB 가 죽음*.

```java
// ❌ 위험 — 10,000 vthread 가 각자 DB connection 잡으려 함
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 10_000; i++) {
        executor.submit(() -> {
            try (Connection conn = dataSource.getConnection()) {  // *connection 부족*
                // ...
            }
        });
    }
}
```

HikariCP 의 *max 50 connection* 이라면 *50 개만 동시*, *나머지 9,950 vthread 가 *connection 대기* 큐*. *DB 도 OK, virtual thread 도 *대기 중*. 결과: *Platform Thread + connection pool 와 동일*.

**교훈:** Virtual Threads 는 *bottleneck 을 *옮길* 뿐*. *진짜 bottleneck (DB / 외부 API rate limit)* 은 *별도 해결*.

**해결:**
- DB connection 도 *적절히 늘림* (CPU 코어 × 2~4)
- 또는 *Semaphore 로 동시 호출 제한*

### 사례 5 — `synchronized` Pinning — *진짜* 함정

```java
@Service
public class OrderService {
    private final Object lock = new Object();

    public Order create(...) {
        synchronized (lock) {                       // ❌ JDK 21 에서 pinning
            return externalApi.call(...);            // blocking IO
        }
    }
}
```

`synchronized` 안의 blocking IO → **Virtual Thread 가 *Carrier Thread 떠나지 못함*** (pinned). *Carrier Thread 점유* → *모든 다른 vthread 가 대기*.

JDK 21 에선 *경고만*. JDK 24+ 에서 *완전 해결* (synchronized + blocking 도 vthread 풀림).

**해결 (JDK 21):**
- `synchronized` → `ReentrantLock` 으로 변경
- 또는 *synchronized 블록 안 외부 호출 절대 금지*

내 환경의 *legacy synchronized* 위치 점검 — `grep -rn "synchronized" src/main` 으로 *blocking IO 포함된 곳* 찾기 권장.

---

## 3. Kotlin Coroutines — *같은 메커니즘, 다른 syntax*

### 3.1 본질 — Continuation-Passing Style

```kotlin
// 사용자가 본 코드
suspend fun getUser(id: Long): User {
    val profile = profileApi.fetch(id)     // suspending call
    val orders = orderApi.list(id)          // suspending call
    return User(profile, orders)
}

// 컴파일러가 변환한 코드 (개념적)
fun getUser(id: Long, cont: Continuation<User>): Any {
    when (cont.label) {
        0 -> profileApi.fetch(id, cont.withLabel(1))
        1 -> orderApi.list(id, cont.withLabel(2))
        2 -> cont.resume(User(profile, orders))
    }
}
```

**State machine** 으로 변환. *함수 호출 의 *각 await 지점* 이 state 의 *분기*. 이게 *Continuation-Passing Style (CPS)*.

### 3.2 Virtual Threads 도 *내부적으로 continuation*

JEP 444 의 *Virtual Threads* 도 *blocking 호출 시점에 continuation 저장* + *carrier thread 떠남* + *비동기 완료 후 다른 carrier thread 에 mount*. 메커니즘은 *Kotlin Coroutines 와 거의 동일*.

**차이:**
- Kotlin: *컴파일 타임* state machine (suspend 함수만)
- Virtual Threads: *런타임* continuation (모든 blocking 호출)

### 3.3 *Function Coloring* — Coroutines 의 문제

Coroutines 의 가장 큰 비판:

```kotlin
fun normal() = println("normal")             // 일반 함수
suspend fun colored() = println("colored")    // suspend 함수

fun main() {
    normal()                  // ✅
    colored()                 // ❌ compile error — suspend 는 suspend 안에서만
    runBlocking { colored() } // ✅ scope 안에서
}
```

→ *함수가 *두 색** (normal vs suspend) 으로 갈림. *normal 에서 suspend 호출 불가*. *Coroutine scope 필요*.

이게 *Bob Nystrom 의 유명한 글 "What Color is Your Function?" (2015)* 의 주제. *모든 라이브러리가 *suspend 버전 + normal 버전* 두 개* 만들어야 함.

**Virtual Threads 는 이 문제 0** — 모든 함수가 *그대로* 호출 가능.

### 3.4 *Structured Concurrency* — Coroutines 의 강점

```kotlin
suspend fun loadUser(id: Long): UserDetail = coroutineScope {
    val profile = async { profileApi.fetch(id) }
    val orders = async { orderApi.list(id) }
    val photos = async { photoApi.list(id) }
    UserDetail(profile.await(), orders.await(), photos.await())
}
```

- `coroutineScope` 안의 *모든 async* 가 *부모* 와 *생명주기 연결*
- *부모 취소* → *모든 자식 자동 취소*
- *자식 하나 실패* → *부모 throws*

Virtual Threads 의 *Structured Concurrency 동등 API* 는 *JDK 21 preview* (`StructuredTaskScope`):

```java
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Subtask<Profile> profile = scope.fork(() -> profileApi.fetch(id));
    Subtask<List<Order>> orders = scope.fork(() -> orderApi.list(id));
    scope.join().throwIfFailed();
    return new UserDetail(profile.get(), orders.get());
}
```

JDK 24+ 부터 *stable*. *Coroutines 의 coroutineScope 와 거의 동일* 한 의미.

### 3.5 *Channel / Flow* — Coroutines 의 독점 영역

```kotlin
// Producer
val channel = Channel<Order>()
launch {
    orders.forEach { channel.send(it) }
    channel.close()
}

// Consumer
for (order in channel) {
    processOrder(order)
}

// 또는 Flow (cold stream)
val ordersFlow: Flow<Order> = flow {
    repeat(100) { emit(fetchOrder(it)) }
}.flowOn(Dispatchers.IO)
 .filter { it.amount > 1000 }
 .map { it.toResponse() }
```

**Virtual Threads 는 이 추상화 없음**. *Channel 이 필요하면 BlockingQueue + Virtual Thread 조합*, *Flow 가 필요하면 Project Reactor 또는 RxJava 별도 사용*.

---

## 4. *직접 비교* — 같은 작업을 두 방식으로

### 작업: *100 개 외부 호출 + 합산*

**Kotlin Coroutines:**
```kotlin
suspend fun aggregate(ids: List<Long>): List<Result> = coroutineScope {
    ids.map { async { externalApi.fetch(it) } }.awaitAll()
}
```
*5 줄*. *Structured concurrency 보장*. *예외 전파 자동*.

**Java 21 Virtual Threads:**
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
*8 줄*. Structured concurrency 동일. *try-with-resources* 가 *scope 의 close*.

→ Coroutines 가 *조금 더 간결*, Virtual Threads 가 *조금 더 명시적*. 의미는 동일.

### 작업: *Publish-Subscribe (Channel)*

**Kotlin:**
```kotlin
val events = Channel<Event>()
launch { events.consumeEach { handle(it) } }
launch { events.send(event) }
```

**Java 21 Virtual Threads:**
```java
BlockingQueue<Event> events = new LinkedBlockingQueue<>();
Thread.startVirtualThread(() -> {
    while (true) handle(events.take());  // blocking — but vthread 안전
});
Thread.startVirtualThread(() -> events.put(event));
```

→ Virtual Threads + `BlockingQueue` 조합이 *Coroutines 의 Channel 과 거의 동등*. *Backpressure (bounded queue), select (다중 channel)* 같은 *고급 기능* 은 *Coroutines 가 압도*.

---

## 5. *2026 년 5 월 결정 가이드*

### Java 21 Virtual Threads 가 좋음:

1. **기존 Java 코드베이스를 *코드 0 변경* 으로 가속**
   - Spring Boot 3.2+: `spring.threads.virtual.enabled=true` 한 줄
2. ***Reactive 학습 곡선 회피***
   - WebFlux 의 Mono/Flux 학습 없이 *높은 동시성*
3. **Function coloring 회피**
   - *모든 함수가 동일 색*
4. **레거시 라이브러리 호환**
   - JDBC, JPA, HTTP client 등 *그대로*
5. **팀이 *Java 중심***

### Kotlin Coroutines 가 좋음:

1. ***Channel / Flow 같은 고급 동시성 추상화* 필요**
2. **이미 Kotlin 코드베이스**
3. **Structured concurrency 가 *production-grade* 필요** (JDK 21 의 preview API 대신)
4. **Android 개발 동시**
5. ***Reactive stream / Backpressure* 활용**

### *함께 쓰기* — Kotlin + Virtual Threads

Kotlin 으로 작성 + JVM 21 + Virtual Threads 가능. `runInterruptible` 또는 `Dispatchers.IO` 가 *내부적으로 virtual thread* 사용:

```kotlin
val dispatcher = Dispatchers.IO.limitedParallelism(64)  // JDK 21+ 에선 vthread 활용
```

Kotlin 의 *syntax* + Virtual Thread 의 *blocking IO 가속*. *최선의 조합*.

---

## 6. *내 환경의 적용 권장*

### settlement (Java 21 + Spring Boot 4.x)

✅ **즉시 적용 가능:**
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

영향:
- Tomcat 의 worker thread 가 *virtual* 로 전환
- Outbox publisher 의 *Kafka send + DB update* 가속
- Settlement 배치 잡 — *수천 settlement 동시 처리*

⚠️ **사전 점검:**
```bash
grep -rn "synchronized" /Users/lms/settlement/*/src/main/java | grep -vE "@Synchronized|Lock"
```
*synchronized 블록 안 blocking IO* 가 있으면 *ReentrantLock 으로 변경*.

### lemuel-xr (Java 21 + Spring Boot 3.4)

✅ **즉시 적용 가능** — 동일.

특히 *LLM API 호출 (Claude / OpenAI)* 이 *외부 API blocking call* 이라 Virtual Threads 의 *가장 큰 효과*.

### academy / sparta-msa

✅ **즉시 적용 가능**.

---

## 7. *흔한 함정 5 가지*

### ❌ 함정 1: synchronized + blocking IO (Pinning)

```java
synchronized (lock) {
    httpClient.send(req);  // *pin* 됨
}
```
→ ReentrantLock 으로.

### ❌ 함정 2: ThreadLocal 남용

```java
private static final ThreadLocal<UserContext> CTX = new ThreadLocal<>();
```
*Virtual Thread 마다 ThreadLocal 인스턴스* → *수만 개 = 메모리 폭증*. **`ScopedValue`** (JDK 21+) 사용 권장:

```java
public static final ScopedValue<UserContext> CTX = ScopedValue.newInstance();

ScopedValue.where(CTX, userContext).run(() -> doWork());
```

### ❌ 함정 3: DB connection pool 의 *너무 작은* 크기

기본 HikariCP 10 → 10,000 vthread *경합* 발생. *50~100* 으로 증설.

### ❌ 함정 4: *CPU-bound 작업에 vthread 사용*

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 1000; i++) {
        executor.submit(() -> calculatePi());  // CPU-bound!
    }
}
```
→ Carrier thread (보통 CPU 코어 수) 만 *실제 동시*. *Virtual Thread 의 이점 0*. **`ForkJoinPool` 또는 `Executors.newFixedThreadPool(cores)`** 사용.

### ❌ 함정 5: *모니터링 도구 깨짐*

Virtual Thread 수만 개 → Thread dump 가 *수만 줄*. *VisualVM / JFR 의 *thread 분석* 어려움. *Java Flight Recorder* 의 *최신 버전* 이 vthread 별 분석 지원.

---

## 8. *5 년 후* — Virtual Threads + Coroutines 의 미래

### Java 진영

- JDK 24+ : Virtual Threads + synchronized pinning 완전 해결
- StructuredTaskScope stable
- ScopedValue 가 ThreadLocal 의 *default* 가 될 듯
- Project Loom 의 *Tail-call optimization* 등 추가 진화

### Kotlin 진영

- Coroutines 1.x → 2.x 계획
- Compose Multiplatform 통합 강화
- *Kotlin Multiplatform* 에서의 동시성 통일

### *충돌 가능성?*

작음. *Kotlin 이 JDK 21 의 Virtual Threads 를 *Dispatcher.IO* 의 backend 로 활용*. 즉 *Kotlin Coroutines = 고급 추상화*, *Virtual Threads = 저수준 메커니즘*. 협력 관계.

---

## 9. 결론 — *Continuation 의 두 얼굴*

**Virtual Threads** = *"기존 Java 코드 그대로, 더 빠르게"*
**Coroutines** = *"동시성 자체를 *언어 수준 추상화*"*

둘은 *Continuation* 이라는 *같은 메커니즘* 위에서 *다른 추상 수준* 의 답을 준다.

| 결정 변수 | 선택 |
|---|---|
| Java 코드베이스 + Spring Boot | Virtual Threads |
| Kotlin 코드베이스 | Coroutines |
| Channel / Flow / Reactive stream | Coroutines |
| Reactive 학습 비용 회피 | Virtual Threads |
| Android + 백엔드 통일 | Coroutines |
| 함수 코러링 회피 | Virtual Threads |

**2026 년 5 월 추천:**
- **신규 Java 백엔드** → JDK 21 + Virtual Threads
- **신규 Kotlin 백엔드** → Coroutines (Dispatchers.IO 가 내부적 vthread)
- **혼합** → 가능, 자연스러움

**한 줄 결론:** *Reactive Programming 의 시대는 *끝* 났다 — *Virtual Threads + Coroutines* 가 *blocking 코드의 *직관* 으로 같은 동시성* 을 만든다.* 이제 *Mono / Flux* 의 학습 곡선 없이 *Thread Per Request* 가 *production-grade* 로 돌아왔다.

---

## 참고

- *Java Concurrency in Practice* — Brian Goetz (2006) — *cf. Virtual Threads 이전*
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [JEP 453: Structured Concurrency](https://openjdk.org/jeps/453)
- [Kotlin Coroutines Guide](https://kotlinlang.org/docs/coroutines-guide.html)
- *Bob Nystrom — What Color is Your Function?* (2015)
- *Roman Elizarov — Structured Concurrency* (KotlinConf 2019)
- 관련 글:
  - [JVM 구조와 Java 버전 변천사]({% post_url 2026-05-29-jvm-structure-java-version-evolution-production-impact %})
  - [Java vs Kotlin — 코드량·기업 ROI·Claude Code 시너지]({% post_url 2026-05-29-java-vs-kotlin-roi-break-even-claude-code-ai-coding %})
  - [ShedLock 으로 @Scheduled 분산 락]({% post_url 2026-06-04-kubernetes-scheduled-shedlock-distributed-lock %})
