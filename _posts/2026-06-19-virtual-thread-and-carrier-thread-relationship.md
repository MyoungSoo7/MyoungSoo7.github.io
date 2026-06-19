---
layout: post
title: "*Virtual Thread* 와 *Carrier Thread* 의 *관계* — *mount / unmount* 메커니즘 과 *pinning* 의 *물리*"
date: 2026-06-19 00:10:00 +0900
categories: [java, jvm, concurrency, performance]
tags: [virtual-thread, carrier-thread, project-loom, jdk21, jdk24, continuation, forkjoinpool, pinning, structured-concurrency, scoped-values, jep444]
---

> *"Virtual Thread* 는 *경량 스레드 다"* — *맞는 말 이지만* *반쪽 짜리 설명* 이다. *Virtual Thread 가 *경량 인 이유* 는 *그 자체로 *가벼워서 가 아니라* *실제로 *CPU 를 *돌리는 스레드 가 *따로 있기 때문* 이다.
>
> 그 *따로 있는 스레드* 가 *Carrier Thread* — *플랫폼 스레드* (전통적인 OS 스레드) 의 *작은 풀*. *수십만 개 의 Virtual Thread* 가 *수십 개 의 Carrier Thread* 위에서 *돌아 가며 *마운트 / 언마운트* 된다.
>
> 이 *마운트 / 언마운트 가 *어떻게 작동* 하는지 *모르면* — *`synchronized` 하나* 가 *전체 carrier pool* 을 *잠궈서* *Virtual Thread 의 *모든 이점이 *사라지는 *pinning* 의 *물리적 이유* 를 *이해 할 수 없다*.
>
> 이 글은 *JDK 21 (JEP 444 finalized) ~ JDK 24 (JEP 491)* 기준 으로 *Virtual Thread 와 *Carrier Thread* 의 *관계* — *Continuation primitive*, *mount/unmount 시점*, *pinning 의 *원인 과 *처방*, *carrier pool 크기*, *실전 안티 패턴* — 까지 *런타임 관점* 에서 *분해* 한다.

내 *이전 두 글* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) — *메모리 벽 의 자매편*.
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html) — *I/O 6 가지 패턴*.

이 글은 *I/O 병목 글 의 *"동기 직렬화 해결책"* 으로 *언급된 Virtual Thread* 의 *그 안쪽 메커니즘* 을 *파고든다*.

---

## TL;DR — *한 줄 결론*

> *Virtual Thread (VT)* 는 *Carrier Thread (CT)* 라는 *플랫폼 스레드 풀* 위에서 *마운트 / 언마운트* 되며 돈다. *VT 가 *blocking I/O* 를 만나면 *언마운트* 되어 *CT 를 *비워주고*, *I/O 완료* 시 *다시 마운트*. *수십만 VT 가 *수십 CT 로 *충분* 한 이유. 그런데 *`synchronized` 블록 안 *blocking* 은 *언마운트 가 *안 되는 pinning* 을 일으켜 *CT 를 *잡아둔다* → *전체 carrier pool 고갈* → *VT 의 *모든 이점 사라짐*. *JDK 24 (JEP 491)* 에서 *대부분 해결* 되었지만, *JNI / native frame* 은 *여전히 pinning*. *ReentrantLock / 가벼운 lock-free 구조* 가 *VT 시대 의 *기본 동시성 도구* 가 되어야 한다.

---

## 1. *Virtual Thread* 의 *정체* — *경량의 *이유*

### 1.1 *플랫폼 스레드* 의 *비용*

전통 *Java Thread* (= *Platform Thread*) 는 *OS 스레드 1:1 매핑* :

| 자원 | 비용 |
|---|---|
| 스택 메모리 (기본) | *1 MB* (`Xss` 기본) |
| 커널 메모리 (TCB, kernel stack) | *수십 KB* |
| 생성 비용 | *수십 ~ 수백 μs* (`clone()` 시스템 콜 + 스케줄러 등록) |
| 컨텍스트 스위치 | *1 ~ 10 μs* + *cache pollution* |
| OS 스레드 한도 | *수천 ~ 수만* (`/proc/sys/kernel/threads-max`, ulimit `nproc`) |

→ *수십만 동시 요청* 을 *각자 Thread 로 처리하려는 시도 의 *물리적 불가능*. 이게 *Servlet thread-per-request* 모델 의 *한계 의 원인*.

### 1.2 *Virtual Thread* 의 *비용*

| 자원 | 비용 |
|---|---|
| 스택 메모리 | *~ KB 단위* (heap 에 *연속 객체* 로 저장, 필요시 *resize*) |
| 커널 자원 | *0* (OS 가 모름) |
| 생성 비용 | *~ μs* (Java 객체 할당 수준) |
| 컨텍스트 스위치 | *~ ns* (mount/unmount, JVM 내부) |
| 동시 개수 한도 | *수백만 ~ 수천만* (heap 만 충분하면) |

→ *"한 요청 = 한 VT"* 가 *가능* 해진다. 이게 *Project Loom 의 *철학 의 핵심*.

### 1.3 *그런데 *Virtual Thread 는 *마법 이 *아니다*

> *VT 는 *OS 가 모르는 *Java 만의 *추상화*. *CPU 를 *돌리는 실제 주체* 는 *플랫폼 스레드* — 이게 *Carrier Thread*.

*100,000 VT* 가 *동시에 실행 중* 이라고 *CPU 가 100,000 개 가 *돌아가는 게 *아니다*. 실제로는 *N 개 (보통 = CPU 코어 수)* 의 *Carrier Thread* 가 *번갈아가며* *VT 의 *연속(continuation)* 을 *실행* 한다.

---

## 2. *Carrier Thread* — *진짜 일하는 자*

### 2.1 *Carrier Thread 의 *정체*

- *그냥 *플랫폼 스레드* — `Thread` 인스턴스, OS 스레드 1:1.
- *내부적 으론 *`ForkJoinPool` (`Thread.ofVirtual()` 전용 풀)* 의 *워커들*.
- *기본 크기* : `Runtime.getRuntime().availableProcessors()` (= CPU 코어 수).
- *조정* : `-Djdk.virtualThreadScheduler.parallelism=N` 시스템 프로퍼티.

```java
// 카리어 풀 크기 확인
System.out.println("Carrier pool size: " +
    Integer.getInteger("jdk.virtualThreadScheduler.parallelism",
        Runtime.getRuntime().availableProcessors()));
```

### 2.2 *2 종류 의 *내부 풀*

JDK 의 VT 스케줄러는 *2 개 의 ForkJoinPool* 을 *내부적으로 사용* :

1. *Main scheduler* — *대부분의 VT* 가 *여기서* 실행.
2. *Blocking ForkJoinPool* — *pinning 된 VT* 또는 *file system I/O* 등 *언마운트 불가 작업* 을 위한 *별도 풀*. 이 풀은 *동적으로 워커를 추가* (최대 256 개).

### 2.3 *왜 *ForkJoinPool 인가*

VT 스케줄러 의 *요구사항* :
- *work-stealing* — 한 CT 가 *놀고 있으면* 다른 CT 의 큐에서 *작업 훔쳐옴*.
- *낮은 오버헤드* — VT 의 *μs 단위 mount/unmount* 와 *맞물려야 함*.
- *수많은 task* — *수십만 VT 의 *continuation* 을 *효율적으로 큐잉*.

→ *Doug Lea 의 *ForkJoinPool* 이 *정확히 이 요구* 에 *맞춰 만들어진 자료구조*. *VT 가 *위에 얹히는 것* 은 *역사적으로 *자연스러운 *흐름*.

---

## 3. *Mount / Unmount* — *VT 와 CT 가 *만나는 *순간*

### 3.1 *Continuation 의 *원리*

> *VT 의 *핵심 primitive* 는 *Continuation* — *"실행 의 중간 상태 를 *객체로 *저장* 하고 *나중에 *재개 할 수 있는 능력"* .

```text
[VT 의 생명주기]

  생성 → READY → MOUNTED → (blocking 만남) → UNMOUNTED (heap 에 저장)
                    ↑                                ↓
                    └── (I/O 완료, 다시 스케줄링) ────┘
                                                     ↓
                                                  TERMINATED
```

**Mount** :
- *CT 가 *놀고 있을 때* *큐에서 VT 를 꺼냄*.
- *VT 의 *continuation (heap 에 저장된 스택)* 을 *CT 의 *네이티브 스택* 으로 *복사*.
- CT 는 *VT 의 코드* 를 *자기 일처럼* 실행.

**Unmount** :
- VT 가 *blocking 지점* (예 : `Socket.read()`, `Thread.sleep()`) 을 만남.
- *현재 스택 상태* 를 *heap 의 *continuation 객체* 로 *복사*.
- CT 는 *해방* 되어 *다른 VT 를 마운트 가능*.
- VT 는 *I/O 완료 콜백* 또는 *타이머* 가 *다시 깨울 때* 까지 *heap 에 잠들어 있음*.

### 3.2 *언마운트 가 *일어나는 시점 (= "VT 친화적" I/O)*

JDK 21+ 표준 라이브러리 의 *blocking 호출* 은 *대부분 VT 친화* :

- `java.io.InputStream.read()` / `OutputStream.write()` — VT 인 경우 *NIO 로 자동 재라우팅*.
- `java.net.Socket` / `ServerSocket` — *언마운트* OK.
- `Thread.sleep(...)` — *언마운트* OK.
- `LockSupport.park(...)` — *언마운트* OK.
- `BlockingQueue.take()`, `Object.wait()` — *언마운트* OK.
- `CompletableFuture.get()`, `Future.get()` — *언마운트* OK.
- *대부분의 `synchronized`* — *JDK 24 부터* *언마운트* OK (그 전엔 *pinning*).

### 3.3 *언마운트 가 *안 되는 시점 (= "Pinning")*

여전히 *carrier 를 잡아둠* :

- **JNI (native frame)** — JVM 이 *네이티브 코드 의 *스택을 *언마운트 할 수 없음*.
- **Class initializer (`<clinit>`)** — *JVM 자체 의 *동기적 락* 이 *연관* 됨.
- **`synchronized` (JDK 21~23)** — *모니터 객체 와 *carrier 가 *얽혀 있어서 *언마운트 불가*. *JDK 24 (JEP 491) 에서 *해결*.

→ *pinning 된 VT* 는 *blocking 동안 *CT 를 *놓아주지 않는다* — *CT 풀이 *고갈* 되면 *다른 VT 가 *못 돔* → *VT 의 *모든 이점이 *사라진다*.

---

## 4. *Pinning* — *Loom 의 *가장 큰 함정*

### 4.1 *전형적 *pinning 증상*

```java
// 안티 패턴 — JDK 21~23 에서 *치명적*
private final Object lock = new Object();

public void process(Request req) {
    synchronized (lock) {              // ← VT 가 *이 블록 안* 에 있으면
        restClient.get("/external");   // ← *blocking I/O* 가 *언마운트 안 됨*
    }                                  //    → CT 가 *잡혀 있는 동안 *다른 VT 도 *못 돔*
}
```

만약 *100 개의 VT 가 *동시에 *위 함수 호출* + *carrier 풀 = 16* 이라면 :

- *16 개 가 *carrier 에 *마운트* 됨.
- *각자 `synchronized` 블록* 에 진입.
- *external HTTP 호출 (50 ms)* 동안 *언마운트 안 됨* (`synchronized` pinning + 외부 I/O blocking).
- *나머지 84 VT 는 *carrier 가 *돌아올 때까지 *대기*.
- 결과: *VT 50,000 동시* 의 *이점 무력화*.

→ *"async 로 바꿨는데 *왜 안 빨라지지?"* 의 *흔한 원인*.

### 4.2 *Pinning 감지*

JDK 옵션 :
```bash
# JDK 21
-Djdk.tracePinnedThreads=full      # pinning 발생 시 *스택 트레이스* 출력
-Djdk.tracePinnedThreads=short     # 한 줄 요약

# JDK 24+
-XX:+UnlockExperimentalVMOptions -XX:+TrackVirtualThreadPinning
# JFR 이벤트 : jdk.VirtualThreadPinned
```

JFR 이벤트 분석 :
```bash
jfr print --events jdk.VirtualThreadPinned recording.jfr | head -50
```

→ *어느 코드 가 *얼마나 자주 pinning* 시키는지 *정량적으로* 확인 가능.

### 4.3 *처방*

**1. `synchronized` → `ReentrantLock` 으로 교체** (JDK 23 이하 필수, JDK 24 에선 선택):

```java
// Before — pinning 위험
private final Object lock = new Object();

public void process(Request req) {
    synchronized (lock) {
        restClient.get("/external");
    }
}

// After — VT 친화
private final ReentrantLock lock = new ReentrantLock();

public void process(Request req) {
    lock.lock();
    try {
        restClient.get("/external");
    } finally {
        lock.unlock();
    }
}
```

> *`ReentrantLock.lock()` 은 *언마운트 가능* — *VT 가 lock 대기* 중일 때 *CT 를 *놓아준다*.

**2. JDK 24+ 로 업그레이드** (JEP 491):

JDK 24 부터 *`synchronized` 도 *대부분의 경우 언마운트* 가능. *대부분의 코드 가 *수정 없이* 작동.

**3. critical section 안 *I/O 호출 제거*** (근본 처방):

```java
// 더 좋음 — lock 안에서 *I/O 호출 자체를 피함*
public void process(Request req) {
    SomeState state = fetchState(req);          // ← lock 밖에서 I/O
    lock.lock();
    try {
        updateInMemory(state);                  // ← lock 안엔 *순수 메모리 작업만*
    } finally {
        lock.unlock();
    }
}
```

→ *VT 와 무관하게* *동시성 설계 의 *기본 원칙*. *critical section 짧게*.

**4. *Lock-free 자료구조*** :
- `ConcurrentHashMap`, `AtomicReference`, `LongAdder` — 락 자체 가 없어 pinning 무관.
- 가능한 곳 에서 *우선 선택*.

---

## 5. *Carrier Pool Size* — *얼마나 *커야 하나*

### 5.1 *기본값 의 *논리*

기본값 = *CPU 코어 수* 인 이유 :

> *VT 가 *언마운트 된 동안* *CT 는 *다른 VT 를 처리* 할 수 있어서 *CPU 코어 수 만큼 의 CT* 면 *대부분 충분* 하다.

*수십만 VT 동시 실행 중* → *대부분 I/O 대기 중 (언마운트)* → *실제 CPU 점유 중인 VT* 는 *코어 수 정도*. *그래서 *CT = 코어 수* 가 *맞다*.

### 5.2 *언제 *늘려야 하나*

- *Pinning 이 *불가피한 워크로드* — JNI 호출 자주, 또는 *legacy 코드* 가 `synchronized` 가득.
- *Filesystem I/O 비중 큰 워크로드* — *file I/O 는 *언마운트 불가* (POSIX file I/O 의 *비동기 API 부재* 때문). 이 경우 *Blocking ForkJoinPool 이 동적으로 늘어남* (최대 256).

```bash
# 명시적 조정 (예 : 8 코어 → CT 32)
-Djdk.virtualThreadScheduler.parallelism=32
```

### 5.3 *언제 *건드리지 말아야 하나*

> *Pinning 을 *처방 하지 않고 *CT 풀만 늘리는 것* 은 *"버킷 이 새는데 *더 큰 버킷 으로 *바꾸는 것"*.

- *pinning 의 *근본 원인 (synchronized + blocking)* 을 *해결* 하지 않으면 *CT 32 도 100 도 *결국 *고갈*.
- *기본값 으로 시작* 해서 *pinning JFR 이벤트* 와 *carrier 사용률* 측정 후 *조정*.

---

## 6. *Continuation 의 *내부 구조* — *왜 가능한가*

### 6.1 *Stack 의 *2 가지 *형태*

전통 Java thread :
```text
[Native stack] (1MB, contiguous)
  ↑
  ├ frame 1
  ├ frame 2
  ├ frame 3
  └ ...
```

Virtual thread :
```text
[Native stack of carrier]      [Heap stack chunks of VT]
  (carrier 가 mount 중일 때만)     (unmount 시 여기로 복사)
       ↓
   [VT continuation]
     ├ frame chunk 1
     ├ frame chunk 2  ← lazy 분할 저장
     └ frame chunk N
```

VT 가 *unmount* 될 때 :
1. *현재 frame stack* 을 *heap 에 *chunk 단위로 *복사*.
2. *carrier 의 *네이티브 스택* 은 *비워짐* (다른 VT 사용 가능).

VT 가 *remount* 될 때 :
1. *heap 의 continuation* 에서 *frame chunk* 들을 *읽어서* *carrier 스택* 에 *재구성*.
2. *제어 가 *return address* 로 *점프*.

> *이게 *Loom 의 *가장 똑똑한 부분* — *코틀린 코루틴* 처럼 *컴파일러 변환* 이 *아니라*, *JVM 런타임 의 *Continuation primitive (`jdk.internal.vm.Continuation`)* 가 *기존 Java 코드 를 *그대로 *멈출 수 있게* 한다. *async 키워드 색칠* 없이 *기존 라이브러리 가 *그대로* 사용 가능.

### 6.2 *왜 *대부분 코드 가 *수정 불필요*

*"Color of Functions"* 문제 :
- *JavaScript / Python* : *async 함수 와 *sync 함수* 가 *서로 *호환 안 됨*. *전체 callstack 이 *async 로 색칠* 되어야 함.
- *Kotlin* : *suspend* 키워드 가 *함수 시그니처* 에 *침입*. *재컴파일* 필요.
- *Java Virtual Thread* : *색칠 안 함*. *기존 동기 코드 가 *그대로* *VT 위에서 효율적*.

→ *Spring Boot 의 *Servlet 코드 가 *수정 없이* VT 친화*. `spring.threads.virtual.enabled=true` *한 줄* 로 *전체 컨트롤러 가 VT 위에서 돔*.

---

## 7. *실전 패턴 — *Spring Boot* 에서 *VT 활용*

### 7.1 *활성화*

```yaml
# Spring Boot 3.2+
spring:
  threads:
    virtual:
      enabled: true
```

→ Tomcat / Jetty 의 *worker thread* 가 *Virtual Thread* 로 *교체*. *모든 컨트롤러 요청* 이 *VT 위에서 처리*.

### 7.2 *parallelStream* 의 *함정*

```java
// JDK 21 까지 — parallelStream 은 *공통 ForkJoinPool* 사용 (CPU 코어 수)
// VT 와 *별개 풀* — VT 의 이점 *못 활용*
userIds.parallelStream()
    .map(id -> restClient.get("/users/" + id))
    .toList();

// 더 좋음 — VT 풀 명시적 사용
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<CompletableFuture<UserProfile>> futures = userIds.stream()
        .map(id -> CompletableFuture.supplyAsync(
            () -> restClient.get("/users/" + id), executor))
        .toList();
    List<UserProfile> profiles = futures.stream()
        .map(CompletableFuture::join).toList();
}
```

### 7.3 *Structured Concurrency* (JEP 480/499 preview)

```java
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Supplier<User> user = scope.fork(() -> fetchUser(id));
    Supplier<Order> order = scope.fork(() -> fetchOrder(id));
    Supplier<List<Item>> items = scope.fork(() -> fetchItems(id));

    scope.join();           // 모두 완료 대기
    scope.throwIfFailed();  // 하나라도 실패 시 모두 취소

    return new Dashboard(user.get(), order.get(), items.get());
}
```

→ *부모 와 *자식 의 *생명주기 가 *연결* 됨. *부모 가 *cancel* 되면 *모든 자식* 자동 cancel. *unstructured async* 의 *resource leak 문제 해결*.

### 7.4 *Thread-Local 의 *경고*

```java
// VT 에선 *Thread-Local 비용 이 *체감 됨*
private static final ThreadLocal<DateFormat> DATE_FORMAT =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

// 10,000 VT * ThreadLocal value = 메모리 비용 무시 못함
```

대안 — *Scoped Values* (JEP 506, JDK 25 finalized):
```java
private static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

ScopedValue.where(CURRENT_USER, user).run(() -> {
    // 이 안에서 CURRENT_USER.get() 으로 접근
    // VT 가 unmount 되어도 *공유 가능*, *immutable*, *비용 ~0*
});
```

---

## 8. *언제 *Virtual Thread 를 *쓰지 *말아야 하나*

> *모든 곳에 VT 가 *최선 은 아니다*.

### 8.1 *CPU-bound 작업*

- *수치 계산 / 영상 처리 / 압축 / 암호화* — *CPU 시간 의 99%* 를 *연산* 에 쓴다.
- VT 의 *이점 (언마운트 로 CT 양보)* 이 *발생 안 함*.
- *오히려 *VT 스케줄러 오버헤드* 가 *손해*.

→ *플랫폼 스레드* 또는 *전용 ForkJoinPool* 이 *더 적합*.

### 8.2 *Pinning 이 *피할 수 없는 코드*

- *JNI 호출이 *대부분* 인 라이브러리* (예 : 일부 native crypto, image processing).
- *legacy `synchronized` 가 *고치기 어려운 *외부 라이브러리*.
- *JDK 24 이전* + *수정 불가 코드*.

→ *해당 부분만 *별도 스레드 풀* 로 격리.

### 8.3 *ThreadLocal 을 *극도로 *많이 쓰는 코드*

- VT 의 개수가 *수십만* 이면 *ThreadLocal value × VT 수* 의 *메모리* 가 *문제*.
- *Scoped Values 로 *마이그레이션* 권장.

---

## 9. *Carrier Thread 의 *현황 점검 — *프로덕션 *모니터링*

### 9.1 *JFR 로 *실시간 가시화*

```java
// JFR 이벤트 활성화
-XX:StartFlightRecording=duration=60s,filename=vt.jfr,settings=profile

// 핵심 이벤트들:
// jdk.VirtualThreadStart / VirtualThreadEnd
// jdk.VirtualThreadPinned       (← pinning 발생!)
// jdk.VirtualThreadSubmitFailed (← carrier 풀 고갈?)
```

### 9.2 *Micrometer 메트릭 (Spring Boot)*

```yaml
management:
  metrics:
    enable:
      jvm.threads: true
```

핵심 지표 :
- `jvm.threads.daemon` — *플랫폼 스레드 수* (= carrier + 기타).
- *Custom metric* — VT 활성 개수, pinning 발생 횟수 (JFR consumer 로 수집).

### 9.3 *주의 지표*

- *Carrier pool 사용률 > 80% 지속* → pinning 의심.
- *VirtualThreadPinned 이벤트 가 *초당 수십+* → 코드 검토.
- *Heap 사용량 의 *지속적 상승* → ThreadLocal 누수 의심.

---

## 10. *결론 — *VT 는 *Carrier 위에서 *춤춘다*

> *Virtual Thread 의 *경량성 은 *Carrier Thread 와 의 *마운트/언마운트 메커니즘 이 *받쳐 주기에 *가능* 하다.

VT 를 *제대로 활용* 하려면 :

1. **`synchronized` + blocking I/O 의 *조합 을 *피하기*** — 또는 *JDK 24+ 로 업그레이드*.
2. **critical section 안 *I/O 호출 금지*** — VT 와 *무관하게 *기본 원칙*.
3. **CPU-bound 와 *I/O-bound 작업 *분리*** — VT 는 *후자만 위한 도구*.
4. **ThreadLocal → Scoped Values 마이그레이션** — VT 다중 환경의 *메모리 최적화*.
5. **Pinning JFR 이벤트 *모니터링*** — *조용한 회귀* 가 *흔하다*.

> *"async 코드 색칠 없이 *기존 Java 가 *효율적으로 도는"* 이 *Loom 의 *진짜 약속*. 그 약속은 *Carrier Thread 라는 *얇은 OS 스레드 풀* 위에서 *VT 가 *춤추듯 *교체* 되는 *물리 위에 *서 있다*.

*수십만 동시 요청 의 *Java 시대* 가 *진짜로 *왔는지* — 답은 *Virtual Thread 의 *마운트 / 언마운트 가 *내 코드 의 *blocking 지점* 마다 *정상 작동* 하느냐* 에 달려 있다. *측정 → pinning 진단 → ReentrantLock / lock-free 전환 → 재측정* 의 *루프* 를 *돌려야* 한다.

*Carrier Thread 가 *놀고 있을 때* — 그게 *VT 가 *제대로 일하고 있다는 *증거*.

---

## *참고*

- JEP 444 : *Virtual Threads* (JDK 21, finalized).
- JEP 491 : *Synchronize Virtual Threads without Pinning* (JDK 24, finalized).
- JEP 480 / 499 : *Structured Concurrency* (preview).
- JEP 506 : *Scoped Values* (JDK 25, finalized).
- Ron Pressler, *State of Loom* — Project Loom 의 *공식 디자인 문서*.
- Java Magazine, *Coming to Java 21: Virtual threads*.
- Inside Java 의 *Project Loom* 시리즈 — JDK 팀의 *직접 설명*.
- 이전 글 [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html) — *VT 가 *해결책 으로 *등장* 한 자매편.
- 이전 글 [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) — *메모리 벽* 의 자매편.
