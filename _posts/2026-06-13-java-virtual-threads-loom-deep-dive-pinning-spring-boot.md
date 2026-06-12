---
layout: post
title: "자바 *Virtual Thread* — *Project Loom 의 정답*: 왜 *Tomcat 의 200 스레드* 가 *백만 개* 가 되는가, *Pinning 의 함정*, *Spring Boot 3.2+ 의 채택*, *Coroutine / Reactor 와의 *진짜 비교**"
date: 2026-06-13 04:00:00 +0900
categories: [java, concurrency, performance, jvm]
tags: [java, virtual-threads, project-loom, java21, jdk21, lts, concurrency, threads, tomcat, spring-boot, jpa, jdbc, pinning, synchronized, threadlocal, kotlin-coroutine, reactor, webflux, structured-concurrency]
---

*Java 21 LTS* 가 *Virtual Thread (Project Loom)* 를 *공식 release* 한 *2023 년 9 월* 이후 — *백엔드 자바 의 풍경이 *조용히 바뀌고 있다*. *Reactor / RxJava / WebFlux 의 비동기 지옥* 을 우회하고 *원래 의 *sync-style 코드* 로 *수십~수백 배 의 동시성* 을 얻는 길. *Spring Boot 3.2+ 가 *한 줄 설정* 으로 *전 endpoint 를 *Virtual Thread 위에 올린다*. 그러나 *함정 도 명확* — `synchronized` 블록 의 *pinning*, `ThreadLocal` 의 *수백만 인스턴스*, *CPU 바운드 워크로드 의 *기댓값 0*.

이 글은 *Virtual Thread 의 *진짜 깊이*. **(1) *왜 OS 스레드 가 비싼가***, **(2) *Virtual Thread 의 *내부 — carrier thread + park/unpark***, **(3) *Spring Boot 3.2+ 채택 의 *한 줄 설정***, **(4) *Pinning 의 함정* — synchronized 와 native call**, **(5) *Coroutine / Reactor 와의 *진짜 비교***, **(6) *실측 마이그레이션 가이드***, **(7) *함정 5 가지***, **(8) *학습 로드맵***. 어제 [서버 성능 기초](https://myoungsoo7.github.io) / [캐시 적중률](https://myoungsoo7.github.io) / [Discord Go→Rust](https://myoungsoo7.github.io) 글 의 *심화 시리즈*.

---

## TL;DR

| 차원 | Platform Thread (기존) | Virtual Thread (Loom) |
|---|---|---|
| 1 스레드 메모리 | *~1 MB* (스택) | *~수 KB* (동적 확장) |
| 동시 스레드 수 | *수 천* 가 한계 | *수 백만* 가능 |
| Block 시 동작 | *OS 스레드 점유* (낭비) | *carrier 해제 → 재사용* |
| 컨텍스트 스위치 비용 | *OS 의 syscall* (수 μs) | *JVM 내부 park* (수 십 ns) |
| 동작 모델 | *thread-per-request 가 *한계* | *thread-per-request 가 *정공* 회복 |
| 코드 변화 | — | *거의 0*. sync 코드 그대로 |
| CPU 바운드 워크로드 | 동등 | *이득 0* (~약간 손해) |
| I/O 바운드 워크로드 | 한계 명확 | *수십 배 동시성* |

**핵심 메시지**:

- *Virtual Thread = *JVM 이 *OS 스레드 의 *역할 을 *내부 에서 *재구현* 한 것*. *코드는 *블로킹 sync* 그대로, 내부는 *async* 동작*.
- *Spring Boot 3.2+ 의 *`spring.threads.virtual.enabled=true`* 한 줄* 로 *전 endpoint 가 *Virtual Thread 위에 올라간다*.
- *Pinning* = `synchronized` 블록 안에서 *block I/O* 발생 시 *Virtual Thread 가 carrier 를 점유* 해 *동시성 이익 상실*. *Java 24 에서 *해결 완료*.
- *Reactive (WebFlux) 의 가치* 가 *축소* 됨. *Virtual Thread 가 *더 단순 + 비슷한 성능*.
- *Kotlin Coroutine 의 *철학적 자리* — *그래도 *유효*. *구조화 동시성 의 표현력* 은 *Coroutine 이 더 명확*.

**실무 함의**: *지금 Tomcat 의 *200 스레드 한계 가 *bottleneck 인 endpoint* 가 있다면 — *코드 변경 거의 없이 *수십 배 동시성*. *그러나 *Reactive 코드 를 *전부 Virtual Thread 로 바꾸는 *대대적 리팩토링 은 *대부분 *과잉**. *새 프로젝트 는 Virtual Thread, 기존 Reactive 는 그대로* 가 정공.

---

## 0. *왜 OS 스레드 가 비싼가*

### 0-1. *Thread = 스택 + OS 레지스트리*

OS 의 *thread 1 개 = *기본 1 MB 의 스택* + *커널 의 *task_struct 등록*. *1 만 스레드 = *10 GB 메모리*. *물리 적으로 가능하지 않음*.

```
Tomcat 의 기본:
  max-threads: 200    ← 그 이상은 *현실적으로 *어렵다*

JVM 의 기본 스택:
  -Xss1m   ← 1 MB
  10,000 스레드 = 10 GB heap-off-heap
```

*이 한계 가 *모든 thread-per-request 모델 의 *천장**. *동시 사용자 200 명 이상은 *큐* 대기 또는 *비동기 패러다임*.

### 0-2. *Context Switch — 또 다른 비용*

OS 의 *thread 전환 = *kernel mode 전환 + register 저장/복원 + cache miss*. *수 μs ~ 수십 μs*. *수만 스레드 동시 실행 시 *대부분 시간을 *전환 에 소모*.

### 0-3. *해결책 의 *두 갈래**

| 접근 | 대표 | 특징 |
|---|---|---|
| *Async / Reactive* | Node.js, WebFlux, Reactor, RxJava | *코드 는 비동기 (callback, Promise, Mono)* 로 다 바뀜. *효율 적이지만 *복잡* |
| *Lightweight Thread (M:N)* | Erlang, Go (goroutine), Kotlin Coroutine, *Java Virtual Thread* | *코드 는 sync 그대로*. *런타임 이 알아서 *경량 스레드 ↔ OS 스레드 매핑* |

*Virtual Thread = 두 번째 길 의 *Java 의 도착*. *Java 가 *15 년 늦었지만 *결국 왔다*.

---

## 1. *Virtual Thread 의 *내부 원리*

### 1-1. *Carrier Thread + Virtual Thread*

```
[수천만 개 의 Virtual Thread]
       ↓ 일부 만 *지금 실행 중*
[수십 개 의 Carrier Thread]   ← 실제 *OS 스레드*
       ↓
   [CPU 코어]
```

- *Virtual Thread* — JVM 의 *Continuation* 객체. 메모리 만 차지 (~수 KB)
- *Carrier Thread* — *실제 OS 스레드*. *기본 *CPU 코어 수 정도*
- *Virtual 이 *block 가능 한 I/O 호출* (예: `socket.read()`) 를 만나면 — *carrier 에서 *unmount* → *다른 virtual 이 carrier 위에 *mount*

### 1-2. *Block 의 *마법**

```java
// 일반 적인 sync 코드
String response = httpClient.get(url);   // ← 여기서 *block*
process(response);
```

*Platform Thread* — *block 의 *수 초 동안 OS 스레드 점유*. 다른 요청 대기.

*Virtual Thread* — *block 의 *순간 carrier 해제 → 다른 virtual thread 가 *그 carrier 위에서 동작*. *I/O 응답 이 오면 *어느 carrier 든 잡아 *재개*.

*동일 한 sync 코드 가 *async 의 효과*. *코드 의 동시성 표현 은 그대로 + 런타임 의 효율 은 비약 적*.

### 1-3. *Continuation 의 진짜*

내부 적으로 — *Virtual Thread 의 *모든 상태 (스택 + 로컬 변수)* 가 *Continuation 객체 로 *heap 에 저장*. *block 시 *Continuation 만 남기고 *carrier 는 *다른 일*. *재개 시 *Continuation 복원*.

*Stack-on-heap* 의 본질. *Kotlin coroutine 의 *suspending function 과 *같은 원리*. *Java 가 *바이트 코드 수준 에서 *지원 도입*.

---

## 2. *Spring Boot 3.2+ 의 *한 줄 설정**

### 2-1. *전 endpoint 를 Virtual Thread 로*

```yaml
# application.yaml
spring:
  threads:
    virtual:
      enabled: true   # ← 이 한 줄
```

이 *한 줄* 로:
- *Tomcat 의 worker thread 가 *모두 Virtual Thread*
- *@Async 의 *기본 executor 도 Virtual Thread*
- *@Scheduled 도 Virtual Thread*

*기존 코드 한 줄 안 바꾸고* *Tomcat 의 *200 동시 요청 한계 가 사실상 *사라진다*.

### 2-2. *DB Connection Pool 은 여전히 *유한 한 자원**

```
Tomcat thread: 무한 (Virtual)
↓ 모두 *DB 호출* 시도
HikariCP pool: max 20

→ 20 개 만 DB, 나머지 99,980 은 *대기*
```

*Virtual Thread 가 *동시성 의 *천장 을 *DB 풀로 *이동 시킬 뿐*. *DB 풀 의 *적정 크기 가 *새 병목*. *pool size 도 같이 검토* 필요.

### 2-3. *명시적 Virtual Thread Executor*

```java
// Java 21 API
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<String> f1 = executor.submit(() -> callApi1());
    Future<String> f2 = executor.submit(() -> callApi2());
    Future<String> f3 = executor.submit(() -> callApi3());

    return combine(f1.get(), f2.get(), f3.get());
}
```

*N 개 외부 API 의 *병렬 호출* — *thread pool 의 *크기 고민 없음*. *각 호출 마다 Virtual Thread 1 개*. *I/O 대기 시간 동안 *다른 호출 의 carrier 가 *재활용*.

---

## 3. *Pinning 의 함정*

Virtual Thread 의 *가장 큰 함정*. *synchronized 블록 안에서 *block 발생* 시 — *Virtual Thread 가 carrier 를 *놓지 못한다*.

### 3-1. *Pinning 의 예제*

```java
// ❌ Pinning 발생
synchronized (lock) {
    String data = httpClient.get(url);   // block I/O
    process(data);
}
```

*synchronized 블록 안에서 *block I/O* 가 일어나면 — *Java 의 *모니터 락 (synchronized) 의 구현 한계* 로 *carrier 가 *해제 되지 않음*. *동시성 이익 0*. *Platform Thread 와 동등*.

### 3-2. *해결책 — ReentrantLock 사용*

```java
// ✅ ReentrantLock 은 pinning 없음
ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    String data = httpClient.get(url);   // block OK
    process(data);
} finally {
    lock.unlock();
}
```

*`java.util.concurrent.locks.ReentrantLock` 은 *Virtual Thread 친화 적*. *carrier 정상 해제*.

### 3-3. *Java 24 의 *해결**

*2025 년 의 Java 24* 에서 *synchronized 의 pinning 이 *내부 적으로 해결*. *바이트 코드 호환 그대로 *carrier 가 정상 해제*. *기존 코드 의 *대부분 pinning 이 *자동 사라짐*.

*Java 21 LTS 사용 시* — *ReentrantLock 권장*. *Java 24+* — *synchronized 그대로 OK*.

### 3-4. *Pinning 진단*

```bash
# JVM 옵션
-Djdk.tracePinnedThreads=full       # 또는 short
```

*Pinning 발생 시 *stack trace 출력*. *production 에서 일정 기간 켜서 *pinning 점검*.

---

## 4. *ThreadLocal 의 함정*

```java
private static final ThreadLocal<Connection> CONN = new ThreadLocal<>();
```

Platform Thread 200 개 면 *최대 200 개 의 ThreadLocal 인스턴스*. *Virtual Thread 100 만 개 면 *최대 100 만 인스턴스*. *메모리 폭발*.

### 4-1. *해결책 — *ScopedValue* (Java 21 preview, Java 25 정식)*

```java
private static final ScopedValue<Connection> CONN = ScopedValue.newInstance();

ScopedValue.where(CONN, conn).run(() -> {
    // CONN.get() 접근 가능
    process();
});
// 블록 종료 시 자동 정리
```

*Virtual Thread 의 *경량 ThreadLocal*. *불변 + 범위 한정*. *memory 폭발 없음*.

기존 ThreadLocal 도 *동작은 하지만 *권장 패턴 은 ScopedValue*. *기존 코드 의 ThreadLocal 사용 빈도 가 *많지 않다면* 큰 문제 아님.

---

## 5. *Coroutine / Reactor 와 비교*

### 5-1. *Reactor / WebFlux — *그래서 의미 잃었나?*

| 영역 | WebFlux (Reactor) | Virtual Thread |
|---|---|---|
| *코드 단순함* | 복잡 (Mono, Flux 체이닝) | *극도로 단순* (sync 그대로) |
| *디버깅* | 어려움 (stack trace 가 다름) | *직관 적* (일반 stack trace) |
| *I/O 성능* | 매우 우수 | 매우 우수 |
| *CPU 성능* | 비슷 | 비슷 |
| *역압 (backpressure)* | *명시 제어 가능* | *언어 차원 X* (별도 라이브러리) |
| *기존 sync 라이브러리* | *non-blocking 으로 *전면 교체 필요* | *그대로 사용* |

*Virtual Thread 도입 후 *WebFlux 의 *대부분 영역 의 우위 가 사라짐*. *남는 우위 는 *역압 제어 + 스트리밍*. *그 외 영역 에서는 *Virtual Thread 가 *더 단순 한 정공*.

### 5-2. *Kotlin Coroutine — *그래도 유효*

| 영역 | Coroutine | Virtual Thread |
|---|---|---|
| *코드 단순함* | 매우 우수 (suspend) | 매우 우수 (sync) |
| *구조화 동시성* | *언어 차원 지원* (CoroutineScope) | *Java 21 preview, 25 정식* |
| *cancellation* | *명시 적 일급* | *Thread.interrupt()* (덜 우아) |
| *언어 통합* | *깊음* (suspending fun, flow) | *라이브러리 수준* |
| *생태계* | Kotlin only | Java/Kotlin 모두 |

*Kotlin 프로젝트* 에서는 *Coroutine 이 여전히 정공*. *구조화 동시성 의 *언어 표현력* 이 *Virtual Thread 보다 명확*. *Java 프로젝트* 에서는 *Virtual Thread 가 정공*.

### 5-3. *Go goroutine — *근본 적으로 같은 아이디어**

| 영역 | Go goroutine | Java Virtual Thread |
|---|---|---|
| 본질 | M:N 경량 스레드 | 동일 |
| 런타임 | Go runtime | JVM |
| 동시성 통신 | *Channel* (CSP 모델) | *전통 적 lock / queue* |
| 학습 곡선 | 매우 낮음 | 낮음 |

*철학 적 자리는 *동일*. *Go 가 *2009 년 부터 한 일 을 *Java 가 *2023 년 따라잡았다*. *Discord 가 *Go → Rust 한 *수년 후* — *Java 도 *그 자리 에 *복귀**.

---

## 6. *실측 마이그레이션 가이드*

### 6-1. *I/O 바운드 endpoint 만 *우선 적용**

```java
// CPU 바운드 (이미지 처리 등) 은 *이득 0 ~ 손해*
@PostMapping("/image/resize")
public Image resize(...) { ... }   // ← Virtual Thread 효과 X

// I/O 바운드 (외부 API, DB) 은 *이득 큼*
@GetMapping("/order/{id}")
public Order get(@PathVariable Long id) {
    return externalApi.fetch(id);   // ← Virtual Thread 효과 압도적
}
```

*전 endpoint 일괄 적용 안 해도 됨*. *I/O 비중 높은 것 부터*.

### 6-2. *Connection Pool 함께 재검토*

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 50   # Virtual Thread 와 함께 *증가 필요*
                              # 단, DB 의 max_connections 와 맞춤
```

*Virtual Thread 의 동시성 증가 가 *DB pool 의 *새 천장 을 만든다*. *DB 측 max_connections 가 함께 올라야 함*.

### 6-3. *Pinning 모니터링*

```bash
-Djdk.tracePinnedThreads=short    # production. full 은 비용 큼
```

*로그에 pinning 발생 stack trace*. *상위 N 개 위치 식별 → ReentrantLock 또는 *Java 24 업그레이드*.

### 6-4. *부하 테스트 의 정공 순서*

1. *Virtual Thread off* — baseline
2. *Virtual Thread on* — 동일 부하 + 적용 후 차이 측정
3. *부하 증가* — 처리량 증가 한계 측정
4. *DB pool 증가* — Virtual Thread 의 효과 가 *DB pool 의 천장 에 막히는지* 확인

---

## 7. *함정 5 가지*

### 7-1. *CPU 바운드 워크로드 에 적용 → 이득 0*

이미지 처리, 압축, ML 추론. *CPU 사용량 자체 가 *한계*. Virtual Thread 가 *carrier 를 더 많이 만들지 않음 (default = 코어 수)*. *동시성 이 *오히려 미세 손해*. *적용 X*.

### 7-2. *synchronized 의 pinning 무시*

*Java 21 LTS* 에서 *기존 코드 의 synchronized 가 *Virtual Thread 이익 을 망친다*. *진단 + ReentrantLock 으로 전환* 또는 *Java 24+ 로 업그레이드*.

### 7-3. *ThreadLocal 의 *메모리 폭발**

Connection, MDC (logging), SecurityContext 등 *흔히 사용*. *수만 ~ 수십만 Virtual Thread 에서 *기존 ThreadLocal 그대로* 사용 가능 하지만 *메모리 footprint 검토* 필요.

### 7-4. *Native call / FFI 의 Pinning*

JNI 호출, native lock 등 *carrier 해제 불가능*. *Virtual Thread 에서도 *carrier 그대로 점유*. *Java 21 의 *남은 한계*.

### 7-5. *"Virtual Thread = 무한 동시성"* 이라는 *낙관*

*Tomcat 의 천장 이 사라져도 *DB 풀, 외부 API rate limit, 네트워크 대역폭, GC* 등 *다른 천장 이 *기다림*. *Virtual Thread 가 *천장 의 위치를 *옮길 뿐*. *Holistic 한 *시스템 측정* 이 정공.

---

## 8. *학습 로드맵*

| 단계 | 집중 | 자료 |
|---|---|---|
| 1 | *Virtual Thread 의 *기본 API* (`Thread.ofVirtual()`, `newVirtualThreadPerTaskExecutor()`) | Java 21 docs |
| 2 | *Spring Boot 3.2+ 의 *config 와 효과* | Spring Boot 공식 release notes |
| 3 | *Pinning 의 진단 + ReentrantLock 전환* | JEP 444 (Virtual Threads) |
| 4 | *ScopedValue (Java 25)* | JEP 506 |
| 5 | *Structured Concurrency (Java 25 정식)* | JEP 505 |
| 6 | *Coroutine / Reactor 비교* | Inside Java podcast, JetBrains talks |
| 7 | *실 production 마이그레이션 사례* | 한국 사례 (e.g., 카카오 / 우아한형제들 블로그) |

### 8-1. *최소 어휘* 한 줄 정리

- *Virtual Thread* — JVM 의 *M:N 경량 스레드*. *수백만 가능*
- *Carrier Thread* — *실제 OS 스레드*. 코어 수 만큼만
- *Continuation* — *스택 의 heap 저장*. block 시 *carrier 분리*
- *Pinning* — *synchronized 블록 의 *carrier 점유*. Java 24+ 해결
- *ScopedValue* — *경량 ThreadLocal*. Virtual Thread 의 *짝*
- *Structured Concurrency* — *부모-자식 스레드 의 *생명주기 묶기*
- *thread-per-request* — *옛 패러다임 의 *부활*. Virtual Thread 의 *정공*

---

## 9. *마무리* — *비동기 의 *되감기**

*"비동기 가 정공" 의 시대 (2010 년대 — Node.js, Reactive)* — *코드 의 단순함 을 *희생 하고 *성능 을 얻었다*. *callback hell, Promise 체이닝, Mono / Flux 의 *학습 비용*. *오랜 자바 백엔드 의 *Reactor 와 *씨름 한 *고통 의 시간*.

*Virtual Thread 는 그 *희생 의 *되감기*. *코드 의 단순함 + 성능* 의 *두 마리 토끼*. *2026 년 의 *자바 백엔드 의 *정공 적 출발점*. *새 프로젝트* 에서는 *기본 으로 Virtual Thread*, *기존 Reactive 는 그대로* 가 정공.

기억 할 *세 줄*:

1. *Virtual Thread = *JVM 이 *OS 스레드 의 역할 을 *내부 에서 재구현* 한 것. *sync 코드 그대로 + 수십 배 동시성*.
2. *Spring Boot 3.2+ 의 *한 줄* 설정 + *I/O 바운드 endpoint 의 *수십 배 동시성*. *기존 코드 변경 거의 없음*.
3. *함정 — `synchronized` 의 pinning, ThreadLocal 의 메모리, CPU 바운드 의 *이득 0*. *Java 24+ 가 *대부분 해결*.

*"Go goroutine 의 시대 가 *15 년 후 *Java 에도 왔다"* — 우리는 이제 *Java 로도 *Go 처럼 쓴다*. *Reactive 의 학습 비용 을 *낼 이유 가 사라졌다*. *그 자리 의 *새 의식 은 — *측정 → DB 풀 / 외부 API rate limit / GC 등 *다음 천장 의 분석**.

*"가장 빠른 코드 는 *sync 처럼 보이는 코드*. Virtual Thread 가 그것 을 *진짜 빠르게 만든다*."* — *글 의 한 줄 결론*.
