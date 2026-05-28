---
layout: post
title: "JVM 의 구조와 Java 버전 변천사 — 8 부터 21 까지의 *진짜 변화* 와 운영 환경에서 JVM 이 프로그램에 미치는 영향"
date: 2026-05-29 02:10:00 +0900
categories: [java, jvm, performance]
tags: [jvm, java, gc, jit, virtual-threads, zgc, g1gc, metaspace, java8, java11, java17, java21, production, tuning]
---

"Java 21 쓰세요" 라는 말, 자주 듣지만 *왜* 가 잘 안 보인다. 8 → 11 → 17 → 21 의 각 LTS 가 *JVM 내부에서 어떤 물리적 변화* 를 가져왔고, *서비스 운영* 에 어떻게 영향을 주는지 정리한다.

이 글은 *자바 문법 변화* (Lambda, Pattern Matching 등) 보다 *JVM 의 내부 구조와 운영 영향* 에 초점.

---

## TL;DR — Java 8 → 21 의 운영 관점 핵심 변화

| 변화 | 도입 버전 | 운영 영향 |
|---|---|---|
| PermGen → Metaspace | Java 8 | `java.lang.OutOfMemoryError: PermGen` 사라짐. Metaspace 는 native memory |
| G1GC 기본화 | Java 9 (8 부터 사용 가능, 9 부터 default) | Pause time 예측 가능 (`-XX:MaxGCPauseMillis`) |
| Module System (JPMS) | Java 9 | `--add-opens`, `--add-modules` 라이브러리 호환 이슈 |
| 새 GC: ZGC, Shenandoah | Java 11/12 (Production 은 15/15) | *Sub-millisecond* GC pause. Large heap 친화 |
| Container 인식 | Java 10 (`UseContainerSupport` 기본 활성) | Docker/K8s 의 cgroup memory/CPU 자동 인식 |
| Sealed Classes, Records | Java 17 | Pattern Matching 의 기반 |
| **Virtual Threads** | Java 21 | *Thread Per Request* 모델 부활. 동시성 모델 *대전환* |
| ZGC Generational | Java 21 | 기존 ZGC 의 throughput 한계 해소 |
| String Templates (Preview) | Java 21+ | (아직 preview) |

**LTS 채택 권고 (2026 년 5 월 기준):**
- 신규 프로젝트: **Java 21** (Virtual Threads 진심으로 사용 가능)
- 운영 중 시스템: **Java 17 → 21 이전** 검토. 17 은 2029 년까지 무료 지원
- 레거시: 8 은 *Oracle 유료 지원만 남음* (Adoptium/Corretto 는 무료 계속)

---

## 1. JVM 의 *물리적* 구조 — 메모리 / 실행 엔진 / ClassLoader

### 1.1 JVM 의 *3 큰 부품*

```
┌──────────────────────────── JVM ────────────────────────────┐
│                                                              │
│  ┌─── ClassLoader Subsystem ───┐                            │
│  │  Bootstrap → Platform → App  │   .class → 메모리          │
│  └─────────────────────────────┘                            │
│                                                              │
│  ┌─── Runtime Data Area ───────────────────────────────┐    │
│  │                                                       │   │
│  │  [Heap]                     [Metaspace] (native)     │    │
│  │   - Young Gen (Eden/S0/S1)   - 클래스 메타데이터      │    │
│  │   - Old Gen                  - 메서드 정보            │    │
│  │   - (JDK 7 까지: PermGen)     - String pool (Java 7+) │   │
│  │                                                       │   │
│  │  [JVM Stacks]               [PC Registers]            │   │
│  │   - Thread 마다 하나           - 현재 명령어 위치       │   │
│  │   - 메서드 frame stack                                │   │
│  │                                                       │   │
│  │  [Native Method Stacks]                              │    │
│  │   - JNI 호출 시                                       │   │
│  │                                                       │   │
│  │  [Direct Memory (off-heap)]                          │    │
│  │   - ByteBuffer.allocateDirect()                      │    │
│  │   - Netty 등                                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─── Execution Engine ──────────────────────────────┐      │
│  │  [Interpreter]                                     │      │
│  │  [JIT Compiler]                                    │      │
│  │   - C1 (Client) — 빠른 컴파일, 적은 최적화          │      │
│  │   - C2 (Server) — 느린 컴파일, 깊은 최적화           │     │
│  │   - GraalVM (실험) — Polyglot, AOT                  │     │
│  │  [Garbage Collector]                               │      │
│  │   - Serial / Parallel / CMS / G1 / ZGC / Shenandoah│      │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Heap vs Metaspace vs Direct Memory — *각각 다른 메모리*

```
운영 중 java 프로세스의 메모리 = Heap + Metaspace + Direct + Thread stacks + Code cache + JNI + ...

OS RSS (Resident Set Size) ≠ -Xmx
```

이 한 줄이 *컨테이너 OOM 사고의 90%* 원인. `-Xmx4g` 줬는데 컨테이너가 6GB 에서 OOMKilled 되는 *진짜 이유*:

- Heap: 4GB
- Metaspace: 300MB
- Direct Memory: 500MB (Netty / NIO buffer)
- Thread Stacks: 200 스레드 × 1MB = 200MB
- Code Cache: 240MB
- GC overhead: 200MB
- **합: 약 5.5GB + 변동**

해결책 (뒤에서 자세히):
- `-XX:MaxDirectMemorySize=512m` 명시
- `-XX:MaxMetaspaceSize=512m` 명시
- `-XX:MaxRAMPercentage=75.0` (cgroup memory limit 의 75% 만 heap)
- Native Memory Tracking (`-XX:NativeMemoryTracking=summary`)

---

## 2. ClassLoader — 클래스가 메모리에 올라오는 과정

### 2.1 3 단계 로더 (Java 9 이후)

```
Bootstrap ClassLoader (C++ 구현, JVM 본체)
  ├─ java.base 모듈 (java.lang.*, java.util.*)
  │
  ↓ delegate
Platform ClassLoader (이전엔 Extension)
  ├─ JDK 모듈 (java.xml, java.sql, ...)
  │
  ↓ delegate
Application ClassLoader (System)
  ├─ classpath / module path
  │  (애플리케이션 JAR 들)
  │
  ↓ delegate
(Custom ClassLoader — 예: 톰캣의 WebappClassLoader)
```

**Parent Delegation Model**: 자식 로더는 *부모에게 먼저* 위임. 부모가 없으면 자기가 로드. 이게 *같은 클래스가 두 ClassLoader 에 의해* 로드되는 사고를 막는 핵심.

### 2.2 ClassLoader Leak — *재배포 시 메모리 누수*

운영에서 가장 *잘 안 보이는* 메모리 누수:

```
Tomcat 같은 컨테이너에서:
1. WAR 1 배포 → WebappClassLoader1 + 로드된 클래스들 + 인스턴스
2. WAR 1 재배포 → WebappClassLoader1 *언로드 시도*
3. 그러나 *어딘가에서 강한 참조* 가 남아있으면 언로드 실패
4. 메모리에 *옛 ClassLoader1 의 모든 클래스* 가 영구 남음
5. 몇 번 재배포 시 Metaspace OOM
```

흔한 원인:
- **ThreadLocal 미정리** — Thread pool 의 스레드가 옛 ClassLoader 의 객체 참조 유지
- **Driver 미등록 해제** — `DriverManager` 에 등록된 JDBC Driver
- **JNI 가 static 으로 잡고 있는 자바 객체**
- **shutdown hook 미등록 해제**

진단:
```bash
jcmd <pid> GC.class_histogram | head -50
jcmd <pid> VM.classloaders   # ClassLoader 트리
jmap -clstats <pid>           # ClassLoader 통계 (deprecated, JFR 권장)
```

---

## 3. GC 변천사 — *latency vs throughput* 의 50 년 진화

### 3.1 GC 알고리즘 계보

| GC | 도입 / 표준화 | 특징 | Pause time | Throughput |
|---|---|---|---|---|
| **Serial** | JDK 1.x | 단일 스레드, *모든 GC stop-the-world* | 매우 김 | 단순 |
| **Parallel** (Throughput) | JDK 1.4 ~ Java 8 기본 | 멀티 스레드 STW. *최대 throughput* | 김 | 최고 |
| **CMS** (Concurrent Mark Sweep) | JDK 1.5 ~ Java 9 deprecated | 일부 phase 만 STW | 짧음 | 보통 |
| **G1** (Garbage First) | JDK 7 → Java 9 기본 | Region 기반, 예측 가능한 pause | 예측 가능 | 좋음 |
| **ZGC** | Java 11 → 15 production → 21 generational | *Sub-millisecond* pause, 대용량 heap | < 1ms | 보통 (21 부터 ↑) |
| **Shenandoah** | Java 12 → 15 production (Red Hat) | ZGC 와 비슷, *concurrent compaction* | < 10ms | 보통 |
| **Epsilon** | Java 11 | *GC 하지 않는* GC. 테스트/벤치마크용 | 없음 | 최고 |

### 3.2 G1 vs ZGC vs Shenandoah — *언제 무엇을*

```
힙 크기 / 워크로드 결정 트리:

힙 < 4GB?
  → G1 (또는 Parallel)

힙 4-32GB?
  → G1 (기본). MaxGCPauseMillis=200 정도가 좋은 출발점

힙 32GB-1TB? AND Latency 중요?
  → ZGC (Java 21 generational 이상 권장)

Latency 가 *극도로* 중요 (실시간 거래 등)?
  → ZGC 또는 Shenandoah

Throughput 만 중요 (배치 잡)?
  → Parallel GC (-XX:+UseParallelGC)
```

### 3.3 G1GC 의 *진짜 동작* — Region 모델

```
이전 GC: 메모리를 *큰 영역 3개* (Eden/Survivor/Old) 로 분리
G1: 메모리를 *수백 개 region* (각 1-32MB) 으로 분리

각 region 은 가변적으로 Eden / Survivor / Old / Humongous 역할 부여
GC 마다 *어떤 region 을 회수할지* G1 이 결정 → 이름이 "Garbage First"
```

핵심 옵션:
```bash
-XX:+UseG1GC                  # G1 활성 (Java 9 부터 기본)
-XX:MaxGCPauseMillis=200       # 목표 pause time (best-effort)
-XX:G1HeapRegionSize=16M       # region 크기. 자동 결정이 보통 OK
-XX:InitiatingHeapOccupancyPercent=45  # mixed GC 시작 임계
```

`MaxGCPauseMillis` 는 *목표* 일 뿐, 보장 아님. 너무 작게 (예: 50ms) 잡으면 GC 가 *자주* 돌아 throughput 저하.

### 3.4 ZGC — *Concurrent* 가 다 무엇인가

ZGC 는 *거의 모든 작업을 concurrent* 로:
- Mark: concurrent
- Relocate (compaction): concurrent
- Reference processing: concurrent

STW 는 *시작/종료 동기화 점만*. 그래서 *< 1ms pause* 가 가능. *512MB 부터 16TB heap* 까지 동일하게 동작.

활성:
```bash
-XX:+UseZGC                    # Java 15+
-XX:+ZGenerational             # Java 21+ (young/old 분리, throughput ↑)
```

ZGC 의 *throughput* 은 G1 보다 *5-10% 낮음* (concurrent 오버헤드). 그러나 *Java 21 의 generational ZGC* 부터 이 격차 줄어듦.

---

## 4. JIT — *interpreted Java* 가 *native 수준* 으로 빨라지는 비밀

### 4.1 Tiered Compilation

```
Method 호출 1번  → Interpreter 가 bytecode 실행
호출 2000번    → C1 (Client) JIT 가 *빠르게* 컴파일 (level 3)
호출 10000번   → C2 (Server) JIT 가 *깊이* 최적화 (level 4)
                 - inlining, escape analysis, vectorization, ...
```

운영 영향:
- **Warm-up 기간** — 배포 직후 *수 분간* CPU 가 *비정상적으로 높음*. JIT 컴파일 중
- **De-optimization** — JIT 가 가정 (예: 어떤 타입만 들어옴) 이 깨지면 *interpreted 로 fallback*. Latency spike

### 4.2 Code Cache

JIT 결과 (native code) 가 저장되는 *별도 메모리 영역*. 기본 240MB.

```bash
-XX:ReservedCodeCacheSize=512m
-XX:+PrintCodeCache
```

`CodeCache is full. Compiler has been disabled` 경고가 *production 사고 신호*. JIT 가 멈추면 *모든 코드가 interpreted* 로 돌아 *throughput 90% 저하*.

### 4.3 GraalVM — *next-gen* JIT

- C2 보다 *더 깊은 최적화* — 특히 Stream, Lambda 코드
- *AOT (Ahead-Of-Time) 컴파일* 지원 → native image (Spring Boot 3.x 의 `native` profile)
- 기동 시간 *수초 → 100ms*, 메모리 *수백 MB → 50MB*
- 단점: build time *5배*, *runtime reflection / dynamic class loading* 제약

내 환경에서 *Lambda function* / *CLI tool* 은 GraalVM native, *서버 워크로드* 는 일반 JIT 가 답.

---

## 5. Java 버전별 *진짜 변화* 매핑

### Java 8 (2014, LTS)

- **Lambda + Stream API** — 가장 큰 *언어 변화*
- **PermGen 제거 → Metaspace** — *OOM: PermGen* 사라짐. Metaspace 는 native memory 라 *기본 무제한* (위험!) → `-XX:MaxMetaspaceSize` 명시 필수
- **CompletableFuture** — async programming
- **Optional<T>** — null 안전성
- **Nashorn JavaScript** (지금은 deprecated)

운영 영향: *Metaspace OOM* 이라는 새 함정. 옛 `-XX:MaxPermSize` 옵션은 *무시됨*.

### Java 9 (2017)

- **JPMS (Java Platform Module System)** — `module-info.java`, `jlink`
- **G1GC 기본화**
- **jshell** — REPL
- **HTTP/2 client API**
- **VarHandles** — Unsafe 의 후계자

운영 영향: *모듈 호환성 지옥*. `--add-opens java.base/java.lang=ALL-UNNAMED` 같은 옵션이 *어디서나* 필요해짐. Spring/Hibernate 등 *모든 라이브러리* 가 모듈 호환 패치.

### Java 10 (2018)

- **`var` 키워드** — local variable type inference
- **Container 인식** — `-XX:+UseContainerSupport` 기본 활성. cgroup 의 memory/CPU 자동 감지

운영 영향: Docker/K8s 에서 *호스트의 자원이 아닌 cgroup 의 자원* 을 인식. `Runtime.availableProcessors()` 가 *컨테이너 CPU limit* 반환.

### Java 11 (2018, LTS)

- **HTTP Client API** (java.net.http) 정식
- **ZGC 도입** (experimental → 15 production)
- **Epsilon GC**
- **Single-file source-code 실행** (`java MyApp.java`)
- **Oracle JDK 유료화** — Adoptium / Corretto / Zulu 같은 무료 배포판으로 *생태계 이동*

운영 영향: *대용량 heap + low latency* 가 ZGC 로 가능해짐. 단 production-grade 는 15 부터.

### Java 12-16 (interim)

- **Switch expressions** (12-14)
- **Text blocks** (13-15)
- **Records** (14-16 preview → 16 production)
- **Pattern Matching for instanceof** (14-16)
- **Shenandoah, ZGC production** (15)

### Java 17 (2021, LTS)

- **Sealed Classes** — exhaustive pattern matching 의 기반
- **Pseudo-Random Number Generators** API
- **Strong encapsulation of JDK internals** — `--add-opens` 강제. *옛 라이브러리 호환성 큰 깨짐*
- **Foreign Function & Memory API** (incubator)

운영 영향: 17 → 21 사이 *Spring 6 / Spring Boot 3* 가 17 을 *최소 요구*. 17 미만 못 가는 시스템과 호환 깨짐.

### Java 21 (2023, LTS) — *대전환*

- **Virtual Threads** (JEP 444) — production ready
- **Pattern Matching for switch** (JEP 441) — final
- **Sequenced Collections** (JEP 431)
- **ZGC Generational** (JEP 439)
- **Foreign Function & Memory API** — final (JEP 442)
- **Record Patterns** (JEP 440)

운영 영향: *Virtual Threads* 가 *Thread Per Request 모델* 을 부활시킴. 다음 절에서 자세히.

### Java 22-23 (2024, interim)

- **String Templates** (preview → cancelled, redesign)
- **Statements before super(...)** (preview)
- **Unnamed Variables** (final 22)
- **Class-File API** (preview)

---

## 6. Virtual Threads — *동시성 모델의 혁명*

### 이전: Platform Thread

```
1 자바 Thread = 1 OS Thread (1:1 매핑)
스택 크기: 1MB (기본)
컨텍스트 스위치: OS 가 처리 → 비쌈

→ Thread 1000개 = 1GB 메모리 + 잦은 스위치 → 한계
→ "Thread Per Request" 모델 *불가능*
→ Reactive Programming (RxJava, WebFlux) 등장 — 콜백 지옥
```

### 이후: Virtual Thread (Project Loom)

```
1 Virtual Thread = JVM 이 관리하는 *경량* Thread
스택 크기: 작게 시작, 동적 확장
JVM 이 ForkJoinPool 위에 *수많은 Virtual Thread* 를 멀티플렉싱

→ Virtual Thread 100,000 개 = 부담 적음
→ "Thread Per Request" *부활* — Reactive 안 써도 됨
→ Blocking IO 가 *내부적으로 non-blocking* 으로 처리
```

### 코드 비교

```java
// 이전 (WebFlux Reactive)
public Mono<Order> getOrder(Long id) {
    return userClient.getUser(id)
        .flatMap(user -> productClient.getProducts(user.getOrders())
            .map(products -> new Order(user, products)));
}

// 이후 (Java 21, Virtual Thread + plain blocking)
public Order getOrder(Long id) {
    var user = userClient.getUser(id);          // blocking but virtual
    var products = productClient.getProducts(user.getOrders());
    return new Order(user, products);
}

// 위 메서드를 Virtual Thread 에서 실행
Thread.ofVirtual().start(() -> getOrder(123L));
```

코드가 *동기적으로* 보이지만, JVM 이 *내부적으로 non-blocking IO* 로 처리. *RxJava / WebFlux 의 학습곡선* 이 사라짐.

### Spring Boot 3.2+ 의 적용

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true
```

Tomcat 의 worker thread 가 *Virtual Thread* 로 전환. *수만 동시 요청* 처리 가능.

### 운영 영향

✅ 장점:
- *동기 코드 그대로 + 높은 동시성*
- Reactive 패턴 학습 비용 ↓
- Thread dump 가 *수만 줄* 이라 분석 어려워질 수 있음 (도구 발전 필요)

⚠️ 함정:
- **synchronized 블록 안에서 blocking IO** → Virtual Thread 가 *pinned* — OS thread 점유 풀지 못함. 성능 저하
  - Java 21: `synchronized` 안의 blocking 호출이 OS thread 를 *pin*
  - Java 23+: 일부 개선
- **ThreadLocal 남용** — Virtual Thread 마다 ThreadLocal 인스턴스 → 메모리 폭증. *ScopedValue* (JEP 446) 사용 권장
- **ForkJoinPool 의존** — 기본 carrier thread pool. CPU 코어 수 = pool 크기

---

## 7. 운영 환경에서 JVM 이 *프로그램에 미치는 영향* 7 가지

### 7.1 GC Pause → Latency Spike

```
일반 응답 latency: 50ms
GC Major 발생 시: 50ms + 500ms = 550ms
```

해결:
- G1GC 또는 ZGC 선택
- `MaxGCPauseMillis` 적절히 (G1)
- Heap 크기 조정 — 너무 작으면 GC 자주, 너무 크면 GC 한 번이 김

### 7.2 Container OOMKilled

```
-Xmx2g 설정 → JVM 은 2GB 까지 heap 사용
But Container limit 2.5GB → Metaspace + Direct + Stack 으로 2.5GB 초과 → OOMKilled
Pod 가 *조용히* 재시작 → log 만 보면 *이유 없는 죽음*
```

해결:
- `-XX:MaxRAMPercentage=75.0` — cgroup limit 의 75% 를 heap 으로
- `-XX:MaxMetaspaceSize=256m` 명시
- `-XX:MaxDirectMemorySize=256m` 명시
- 컨테이너 limit 의 *25%* 는 *non-heap* 으로 남겨두는 게 안전선

### 7.3 JIT Warm-up — 배포 직후 latency spike

```
배포 직후 1~3분 동안:
  CPU 사용률 비정상적으로 높음 (JIT 컴파일)
  Latency p99 가 평소의 3-5배

JIT 가 "warm" 해지면 평소 수준으로 복귀
```

해결:
- **AppCDS (Application Class Data Sharing)** — 클래스 로딩 + 일부 JIT 정보 캐시
- **Readiness probe 늦게 OK** — 배포 직후 1분간 traffic 안 받게
- **Canary deployment** — 점진적 노출
- **GraalVM native** — JIT warm-up 자체 없앰

### 7.4 ClassLoader Leak (재배포 누수)

위에서 자세히. *Hot reload 환경 (Tomcat 자체 redeploy)* 에서 자주.

### 7.5 Thread Pool Saturation

```
@Async, ExecutorService, Tomcat threads.max = 200
모든 thread 가 *외부 호출 대기* 중
→ 새 요청 못 받음 → "503 Service Unavailable"
```

해결:
- **Virtual Threads** (Java 21+) — Thread 수 한계 사실상 제거
- **Bulkhead pattern** — 외부 호출별 별도 thread pool
- **Circuit Breaker** — 느린 외부 차단 (Resilience4j)
- **Timeout 짧게** — 무한 대기 방지

### 7.6 Direct Memory 누수

```java
// Netty 4.x — DirectByteBuffer 사용
// ReferenceCountUtil.release() 안 부르면 leak
```

해결:
- `-Dio.netty.leakDetection.level=PARANOID` (개발)
- `-Dio.netty.leakDetection.level=SIMPLE` (production)
- `-XX:NativeMemoryTracking=summary` + `jcmd <pid> VM.native_memory summary`

### 7.7 Code Cache 가득 참

```
[CodeCache is full. Compiler has been disabled.]
→ JIT 멈춤 → 모든 코드 interpreted → throughput 90% 저하
```

해결:
- `-XX:ReservedCodeCacheSize=512m` (기본 240MB)
- `-XX:+UseCodeCacheFlushing` 켜기 (기본 켜짐)
- **GraalVM** — code cache 압박 적음

---

## 8. JVM 모니터링 / 진단 — 운영 도구 모음

### 8.1 명령어 도구

```bash
# 프로세스 확인
jps -v                          # PID + JVM 옵션
jcmd <pid> help                 # 모든 JCMD 명령

# 메모리
jcmd <pid> GC.heap_info
jcmd <pid> VM.native_memory summary    # NMT 활성 시
jmap -histo <pid> | head -30           # 객체 별 인스턴스 수

# 스레드
jcmd <pid> Thread.print
jstack <pid>                            # thread dump

# GC
jstat -gcutil <pid> 1s 10               # GC 통계 (1초 간격, 10회)
```

### 8.2 JFR (Java Flight Recorder) — *production-safe* 프로파일러

```bash
# 1분간 기록
jcmd <pid> JFR.start duration=60s filename=profile.jfr

# JMC (Mission Control) 로 분석
jmc profile.jfr
```

오버헤드 *< 1%*. Production 에 *상시 켜두는* 게 표준.

### 8.3 Micrometer + Prometheus

Spring Boot 의 `actuator` + `micrometer-registry-prometheus` 가 *JVM 메트릭 자동 노출*:

- `jvm_memory_used_bytes{area="heap",id="G1 Eden Space"}`
- `jvm_gc_pause_seconds{action="end of minor GC"}`
- `jvm_threads_states_threads{state="runnable"}`
- `jvm_classes_loaded_classes`

Grafana 대시보드로 *실시간 GC, Heap, Thread 상태* 가시화.

---

## 9. 어느 LTS 로 가야 하나 — 2026 년 의사결정

### 9.1 LTS 지원 일정 (Oracle 공식, 무료 배포판은 더 길게)

| 버전 | LTS 출시 | Premier 지원 | Extended |
|---|---|---|---|
| 8 | 2014 | ~2022 (유료만) | ~2030 |
| 11 | 2018 | ~2026 | ~2032 |
| 17 | 2021 | ~2029 | ~2034 |
| **21** | 2023 | ~2031 | ~2036 |
| 25 (예정) | 2025-9 | TBD | TBD |

(Adoptium/Corretto/Zulu 는 무료로 5-7년 추가 지원)

### 9.2 결정 트리

```
새 프로젝트 시작?
  → Java 21 (Virtual Threads, ZGC Generational, Pattern Matching)

운영 중 Java 8?
  → Java 17 로 이전 (Spring Boot 3, Spring 6 호환). 그 다음 21
  → 8 → 21 직접 점프는 *너무 많은 변화* 한꺼번에

운영 중 Java 11?
  → Java 17 로 이전 (보통 큰 어려움 없음)
  → 그 다음 21

운영 중 Java 17?
  → 안정적이면 *유지 OK*. 21 의 Virtual Threads 가 필요하면 이전

레거시 (Java 6/7)?
  → 단계적 이전. Spring 3 → 5 → 6 의 점프 같이 필요
```

### 9.3 21 이전의 *실전 체크리스트*

- [ ] Spring Boot 3.2+ 사용 중인가
- [ ] 모든 라이브러리가 21 호환인가 (BouncyCastle, Hibernate 등 마이너 버전 확인)
- [ ] `synchronized` 가 많은 코드는 Virtual Thread 도입 *주의* (pinning)
- [ ] ThreadLocal 사용처 → ScopedValue 검토
- [ ] GC 옵션 — ZGC Generational 시도 가능
- [ ] Container 자원 옵션 (`MaxRAMPercentage`) 재계산
- [ ] JFR 베이스라인 측정 → 이전 후 비교

---

## 10. 내 환경의 JVM 운영 설정

### settlement (Java 21, Spring Boot 3.4)

```bash
-XX:+UseG1GC                          # 4GB heap 이라 ZGC 까진 안 감
-XX:MaxGCPauseMillis=200
-XX:MaxRAMPercentage=75.0             # K3s memory limit 의 75%
-XX:MaxMetaspaceSize=512m
-XX:MaxDirectMemorySize=512m
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/heap-dumps/
-XX:NativeMemoryTracking=summary
-XX:+UnlockDiagnosticVMOptions
-XX:+PrintNMTStatistics
-Dspring.threads.virtual.enabled=true  # Virtual Threads
```

### lemuel-xr

```bash
# 더 큰 heap, ZGC Generational
-XX:+UseZGC
-XX:+ZGenerational
-Xmx8g
-XX:MaxRAMPercentage=75.0
-XX:MaxDirectMemorySize=1g            # Netty + embedding 캐시 많음
```

### Monitoring

- Micrometer → Prometheus → Grafana (JVM 대시보드)
- JFR 상시 켜둠 (1% 미만 오버헤드)
- Heap dump 자동 생성 → S3 업로드
- Pod restart 시 *이전 heap dump 보존* 자동화

---

## 결론 — JVM 은 *블랙박스가 아닌 *튜닝 가능한 OS**

Java 개발자가 *JVM 내부를 모르면* production 에서 *근본 원인을 못 찾는다*:
- "GC pause 가 길다" → 어떤 GC 알고리즘? 무슨 phase?
- "OOM" → Heap? Metaspace? Direct?
- "느려" → JIT warm-up? Code cache full?
- "Thread 부족" → Platform vs Virtual?

좋은 백엔드 개발자는 *JVM 을 두 번째 OS 처럼* 다룬다. Linux 의 `top`, `vmstat`, `strace` 와 동등하게 *`jcmd`, `jstat`, `JFR`* 을 *능숙*하게.

Java 21 의 Virtual Threads, ZGC Generational, Pattern Matching 은 *그 OS 가 다음 세대로 진화* 한 결과. *지금 신규 프로젝트면 21 부터 시작* 이 정답.

---

## 참고

- *Java Performance: In-Depth Advice for Tuning and Programming* — Scott Oaks (2020)
- *The Definitive Guide to Java Performance* — Scott Oaks
- [OpenJDK JEP Index](https://openjdk.org/jeps/0)
- [Inside Java](https://inside.java/) — Oracle 공식 블로그
- 관련 글:
  - [Harness Engineering ② Test Harness]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %})
  - [Spring Filter vs Interceptor]({% post_url 2026-05-29-spring-filter-vs-interceptor-network-perspective %})
