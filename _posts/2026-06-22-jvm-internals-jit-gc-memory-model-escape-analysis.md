---
layout: post
title: "*JVM 의 *본질* — *JIT 컴파일*, *GC 알고리즘*, *메모리 모델*, *Escape Analysis* 까지"
date: 2026-06-22 18:40:00 +0900
categories: [java, jvm, fundamentals, performance]
tags: [jvm, jit, gc, garbage-collection, g1gc, zgc, memory-model, escape-analysis, c1, c2, fundamentals]
---

> *"java 명령어 가 *내 코드 를 *실행 한다"* — 이 문장 의 *9 단어* 안 에 *수십 가지 의 *내부 동작* 이 *숨어 있다*. *JVM 의 *bytecode 인터프리터*, *JIT 컴파일러 의 *C1 → C2 단계 적 최적화*, *GC 의 *generational hypothesis*, *Escape Analysis 의 *스택 할당*, *Memory Model 의 *happens-before*. 이 모든 것 이 *Spring Boot 앱 한 줄* 의 *뒤* 에서 *작동* 한다.
>
> ORM 위에서 일하는 백엔드 가 *DB 본질 을 알아야 하듯*, *Java 위에서 일하는 백엔드 는 *JVM 본질 을 알아야 한다*. *GC pause 가 *p99 latency 의 *큰 부분* 일 때, *JIT 가 *warm-up 안 끝났을 때*, *memory leak 이 *조용히 누적* 될 때 — *그 모든 순간 의 *원인 추론* 이 *JVM 내부 의 물리* 에 *뿌리* 박혀 있다.
>
> 이 글은 *기본기 시리즈 의 JVM 편* — *Class Loading*, *Bytecode 실행*, *JIT*, *GC (Serial → G1 → ZGC)*, *Memory Model*, *Escape Analysis*, *Modern features (Virtual Thread, AOT, GraalVM)* — 을 *백엔드 엔지니어 의 *깊이* 로 정리한다.

내 *기본기 시리즈* :
- [*DB 의 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html) — 첫 편
- [*오브젝트 (조영호) 서평*](/2026/06/22/object-book-review-cho-younghoo-object-oriented-design.html) — 객체지향 편
- [*Virtual Thread*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html) — 동시성 편

---

## TL;DR — *한 줄 결론*

> *JVM 은 *7 단계* : (1) *Class Loading* 의 *위임 모델*, (2) *Bytecode 의 *stack-based 실행*, (3) *JIT 의 *C1 (빠른) → C2 (최적) 단계 적 컴파일* + *tiered compilation*, (4) *Generational GC* 의 *young / old 분리*, (5) *G1 / ZGC 의 *region 기반 + concurrent*, (6) *Memory Model 의 *happens-before + volatile*, (7) *Escape Analysis 의 *스택 할당 / lock elision / scalar replacement*. *Virtual Thread (JEP 444)* 는 *Continuation 으로 *async 색칠 없이 *수십만 동시성*, *AOT (GraalVM)* 는 *시작 시간 ms 단위*. *Spring Boot 의 *모든 줄 의 *밑* 에 *이 7 단계 가 *함께 *돈다*. *p99 latency 의 *진짜 원인* 을 *추적 하려면 *JFR + async-profiler* 가 *눈*, *jstat + gclog* 가 *체*. *깊이 는 *코드 양 이 아니라 *어디 의 본질 이 깨졌는지* *측정 할 수 있는 능력* 이 만든다.

---

## 1. *JVM 의 *7 단계 — *전체 지도***

```text
[*.java]                                       ← 1. Source code
   ↓ javac
[*.class (bytecode)]                           ← 2. Compiled bytecode
   ↓ JVM 시작
[Class Loader]                                 ← 3. Class loading (Bootstrap → Platform → Application)
   ↓
[Bytecode Interpreter]                         ← 4. 인터프리트 실행 (느림)
   ↓ hot method 감지
[JIT C1 → C2]                                  ← 5. JIT 컴파일 (네이티브 머신 코드)
   ↓
[Native code execution]                        ← 6. 실행
   ↓ (메모리 할당 / 해제)
[Garbage Collector]                            ← 7. GC (Young/Old, Concurrent)
```

→ *Java 의 *"한 번 작성, 어디서든 실행"* 의 *진짜 비용* 은 *이 7 단계 의 *runtime 처리*. *그 대가* 가 *bytecode 의 portability + JIT 의 적응 적 최적화*.

---

## 2. *Class Loading — *위임 모델***

### 2.1 *3 단계 ClassLoader*

```text
Bootstrap ClassLoader   ← rt.jar / java.base 모듈 (Native 코드)
        ↓
Platform ClassLoader    ← java.* / javax.* 표준
        ↓
Application ClassLoader ← classpath 의 사용자 코드
        ↓
(사용자 정의 ClassLoader) ← Spring Boot, Tomcat, OSGi 등
```

**위임 (delegation)** : 클래스 로드 요청 시 *부모 ClassLoader 에 먼저 위임*. *부모 가 못 찾으면 *자식 이 시도*. 이게 *Java 의 *security 의 *물리적 토대* — *사용자 코드 가 *`java.lang.String` 같은 *시스템 클래스 를 *위조 못 함*.

### 2.2 *Loading → Linking → Initialization*

| 단계 | 의미 |
|---|---|
| **Loading** | .class 파일 → 메모리 의 *Class 객체* |
| **Verifying** | bytecode 유효성 검증 (stack overflow, type safety) |
| **Preparing** | static 필드 의 *기본값* 할당 (0, null) |
| **Resolving** | symbolic reference → direct reference |
| **Initializing** | *static 블록* 실행, static 필드 *명시 값* 할당 |

→ *`<clinit>`* 메서드 가 *Initialization 단계* 의 *진실*. *static 초기화 의 *순환 의존* 이 *교묘한 버그 의 원인*.

### 2.3 *Spring Boot 의 ClassLoader*

```text
Boot ClassLoader (rt.jar)
        ↓
Platform ClassLoader (jakarta.*, java.*)
        ↓
LaunchedURLClassLoader (Spring Boot fat-jar 의 BOOT-INF/lib/*.jar)
        ↓
RestartClassLoader (devtools — 핫리로드 시 클래스 만 재로드)
```

→ *Spring Boot devtools* 의 *hot reload* 가 *작동 하는 이유* — *별도 ClassLoader* 가 *사용자 클래스 만 재로드*. *라이브러리 클래스 (LaunchedURLClassLoader 의 것) 는 *유지*.

---

## 3. *Bytecode — *Stack-Based 실행***

### 3.1 *JVM 은 *Stack Machine***

x86 (register-based) :
```asm
mov eax, [a]    ; load a
add eax, [b]    ; eax = a + b
mov [c], eax    ; c = eax
```

JVM (stack-based) :
```text
iload a          ; push a → stack: [a]
iload b          ; push b → stack: [a, b]
iadd             ; pop two, push sum → stack: [a+b]
istore c         ; pop → c
```

→ *Stack 기반* 의 *장점* : *bytecode 가 *플랫폼 무관*. *register 수* 가 *CPU 마다 달라도 *bytecode 가 *동일*.

### 3.2 *bytecode 의 *7 가지 instruction 그룹*

| 그룹 | 예 |
|---|---|
| Load/Store | `iload`, `astore`, `aload` |
| Arithmetic | `iadd`, `isub`, `imul`, `dcmpl` |
| Control flow | `if_icmpeq`, `goto`, `tableswitch` |
| Object | `new`, `getfield`, `putfield`, `invokevirtual` |
| Method | `invokestatic`, `invokeinterface`, `invokespecial`, `invokedynamic` |
| Array | `anewarray`, `aaload`, `aastore` |
| Synchronization | `monitorenter`, `monitorexit` |

### 3.3 *`invokedynamic` — *Lambda 의 비밀***

Java 7 (2011) 에 도입. *Java 8 람다* 의 *기반*.

```java
Runnable r = () -> System.out.println("hi");
```

→ bytecode 에 `invokedynamic` 한 줄. *최초 호출 시 *Bootstrap method* 가 *람다 의 *진짜 구현체* 를 *생성* 후 *기억* (CallSite). *그 이후 *직접 호출*.

→ *람다 가 *익명 클래스 보다 *빠른 이유*. *클래스 가 *런타임 동적 생성*.

---

## 4. *JIT 컴파일 — *적응 적 최적화***

### 4.1 *인터프리트 + JIT 의 *Hybrid***

```text
첫 실행 → 인터프리트 (느림)
       ↓ 호출 횟수 / 루프 카운트 임계치 초과
       ↓
[C1 컴파일] (Client) — 빠른 컴파일, 적당 한 최적화
       ↓ 더 많은 호출
       ↓
[C2 컴파일] (Server) — 느린 컴파일, *공격적* 최적화
       ↓
네이티브 코드 실행
```

이게 *tiered compilation* (Java 7+). *시작 빠름 (인터프리트)* + *steady-state 빠름 (C2)* 의 *둘 다 얻음*.

### 4.2 *C2 의 *7 가지 최적화*

1. **Inlining** — 짧은 메서드 *호출 → 본문 *복사*. *call overhead 제거*.
2. **Loop unrolling** — `for (i=0; i<4; i++) {...}` → 4 회 *직접 작성*.
3. **Escape Analysis** — *객체 가 *함수 밖 으로 *안 새면* *스택 할당* 또는 *scalar replacement*.
4. **Lock elision** — *thread-local 인 객체 의 *synchronized 제거*.
5. **Branch prediction** — *자주 가는 경로 의 *코드 를 *직선 화*.
6. **Dead code elimination** — *결과 가 *사용 안 되는 코드 *삭제*.
7. **Common subexpression elimination** — `x*y + x*y` → `tmp = x*y; tmp + tmp`.

### 4.3 *Warm-up 의 *진실***

> *Java 앱 이 *처음 *느린 이유* 는 *JIT 컴파일 안 됨* + *cache 도 cold*.

```text
[t=0]   첫 요청 — 인터프리트, ~100x 느림
[t=30s] hot method 가 C1 컴파일 — 10x 빨라짐
[t=2m]  C2 컴파일 — 추가 2x 빨라짐
[t=5m]  full warm-up — steady-state latency
```

→ *Spring Boot 의 *startup probe* 가 *길어야 하는 이유*. *load test 의 *첫 30 초* 결과 는 *무시* — *warm-up 후 측정* 이 *진짜*.

### 4.4 *Deoptimization — *최적화 의 *철회***

```java
class Animal { void sound() { } }
class Dog extends Animal { void sound() { ... } }

void process(Animal a) {
    a.sound();   // C2 가 *monomorphic* 으로 가정 → Dog.sound 인라인
}

// 한 참 후
process(new Cat());   // *Cat* 등장 → 가정 깨짐 → deoptimize → 인터프리트 로 fallback
```

→ JVM 이 *추측 으로 공격적 최적화* 하다가 *틀리면 *철회*. *덕분 에 *일반 적 으로 *작동* 한다는 *유연성*.

---

## 5. *Garbage Collection — *세대 가설***

### 5.1 *Generational Hypothesis*

> *"대부분 의 객체 는 *짧게 산다*. 오래 산 객체 는 *더 오래 살 가능성*". — 1980 년대 의 *경험 적 관찰*.

→ *짧은 객체 는 *모아서 *빠르게 청소*, *오래 산 객체 는 *드물게 청소*. 이게 *generational GC* 의 *철학*.

### 5.2 *Heap 의 *영역*

```text
[Young Generation]
   [Eden]            ← *모든 new 가 여기*
   [Survivor 0 (S0)] ← Eden minor GC 생존자
   [Survivor 1 (S1)] ← S0 → S1 (또는 반대) — copying

[Old Generation]    ← N 회 minor GC 생존 → 승격 (promotion)

[Metaspace]         ← 클래스 메타데이터 (Java 8+, PermGen 폐지)
```

### 5.3 *GC 알고리즘 의 *진화*

| GC | Java 도입 | 특징 |
|---|---|---|
| Serial GC | 1.3 | *single-thread*. 소규모. |
| Parallel GC | 1.5 | *multi-thread young*. throughput 우선. |
| CMS | 1.5 | *concurrent old*. *deprecated (9), removed (14)* |
| **G1** | **8 (default 9+)** | *region 기반*, *pause time goal* 설정 |
| **ZGC** | **15 (production)** | *sub-ms pause*, *concurrent everything*. *colored pointers* |
| Shenandoah | 12 (Red Hat) | ZGC 와 유사 |
| Epsilon | 11 | *no-op GC*. 벤치마크 / 단기 batch 용 |

### 5.4 *G1 GC — *현재 표준***

```text
[Heap = N regions (~1~32MB each)]
   ├ Eden region 들
   ├ Survivor region 들
   ├ Old region 들
   └ Humongous region (큰 객체 ≥ region 절반)

Young GC:
   - Eden + Survivor 의 *살아 있는 객체* 를 *새 Survivor* 또는 *Old* 로 *복사*
   - 빈 region 회수

Mixed GC:
   - Young + *garbage 가 많은 Old region 일부* 동시 청소

Concurrent marking:
   - app 실행 중 *백그라운드 에서 *살아있는 객체 마킹*
```

**튜닝**:
```bash
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200   # 목표 pause (best-effort)
-Xms4g -Xmx4g              # heap 고정 (resize 비용 회피)
```

### 5.5 *ZGC — *극저 latency***

> *ZGC* 는 *Java 11 실험* → *15 production*. *pause 가 *항상 sub-millisecond* (heap 크기 무관).

핵심 기법:
- **Colored pointers** — 64-bit 포인터 의 *상위 비트* 에 *meta 정보 (marked, remapped)* 인코딩.
- **Load barrier** — 모든 *객체 참조 읽기 시* *barrier 코드* 실행, *concurrent 이동 의 *원자적 안전*.
- **Region 기반** — G1 처럼 region 단위 청소.

```bash
-XX:+UseZGC
-XX:+ZGenerational   # JDK 21+ 의 generational ZGC (성능 ↑)
```

→ *대용량 heap (16GB+)* 의 *p99 latency 가 *핵심* 인 워크로드 (검색 / 게임 / 금융 거래소) 에서 *현재 최선*.

### 5.6 *Stop-The-World (STW) 의 *진실***

- *모든 GC* 는 *최소 한 번 의 STW* 필요 (Initial Marking, Final Remarking).
- *concurrent GC (G1, ZGC)* 는 *STW 시간 을 *최소화* — *수십 ms (G1)*, *수 ms (ZGC)*.
- *Serial GC 의 *STW* 는 *수 초 ~ 분* — *production 부적합*.

**GC 로그 분석**:
```bash
-Xlog:gc*=info:file=/var/log/gc.log:time,level,tags
```

→ `g1gc-analyzer`, `gceasy.io`, *Eclipse MAT* 로 시각화. *p99 spike 의 *직접 원인 식별*.

---

## 6. *Memory Model — *happens-before***

### 6.1 *왜 *Memory Model 인가*

> *멀티 코어 CPU + JIT 의 *재배치* + cache 의 *지연* 으로 *프로그램 순서 와 *실제 실행 순서* 가 *다를 수 있다*.

```java
// thread 1
x = 1;
ready = true;

// thread 2
if (ready) {
    print(x);    // *0 이 출력 될 수 있다*  ★
}
```

`ready = true` 가 *thread 2 에 *먼저 보이고* `x = 1` 이 *나중에 보일 수 있음* — *JIT 재배치 + cache 지연*.

### 6.2 *happens-before 관계*

JMM (Java Memory Model) 이 *명시*:
- 같은 thread 의 *프로그램 순서*
- `synchronized` 의 *release → acquire*
- `volatile` 의 *write → read*
- `Thread.start()` → 새 thread 의 *모든 동작*
- `Thread.join()` 전 의 *모든 동작 의 *완료*
- `Atomic` / `final` 의 *publication*

→ *happens-before 가 *보장 되는 두 동작 사이*만 *순서 가 *관찰 가능*.

### 6.3 *volatile 의 *진짜 의미***

```java
private volatile boolean ready;

// thread 1
data = produce();
ready = true;          // volatile write

// thread 2
while (!ready) {}      // volatile read
consume(data);          // ★ data 가 *반드시 *initialized*
```

`volatile` 의 *2 가지 효과*:
1. **Visibility** — 다른 thread 가 *최신 값 봄*.
2. **Ordering** — *volatile write 전 의 *모든 write* 가 *완료 후 보임*. *volatile read 후 의 *모든 read* 가 *그 시점 이후 발생*.

→ *volatile* 만 으론 *atomicity 보장 안 됨*. 카운터 증가 같은 *read-modify-write* 는 *AtomicInteger* 또는 *synchronized*.

### 6.4 *Final 의 *Safe Publication***

```java
class Config {
    private final String url;
    public Config(String url) { this.url = url; }
}

// thread 1
Config c = new Config("https://...");
sharedRef = c;

// thread 2
Config local = sharedRef;
if (local != null) {
    System.out.println(local.url);   // *반드시 *완전히 초기화* — volatile 없어도 OK
}
```

→ *final 필드* 는 *생성자 종료 시점 의 *값 이 *모든 thread 에 *원자적 으로 보임*. *immutable 객체 의 *공유 의 *안전성*.

---

## 7. *Escape Analysis — *조용한 최적화***

### 7.1 *원리*

> *객체 가 *함수 밖으로 *escape 안 하면* (스택 외 노출 안 됨) *heap 할당 불필요*.

```java
void process() {
    Point p = new Point(1, 2);   // ★ p 가 *밖으로 안 나감*
    System.out.println(p.x + p.y);
}
```

C2 가 *p 의 escape 분석* → *escape 안 함* 발견 → *3 가지 최적화 가능*:

### 7.2 *3 가지 결과*

1. **Stack allocation** — heap 대신 *스택 에 할당*. *GC 부담 0*.
2. **Scalar replacement** — *Point p* 를 *int x, int y* 두 변수 로 *분해*. *객체 자체 가 *사라짐*.
3. **Lock elision** — *escape 안 하는 객체 의 *synchronized 제거*. *thread-local 이라 lock 의미 없음*.

### 7.3 *Escape 의 *3 단계*

- **NoEscape** — 메서드 안 에서만 사용. *최대 최적화*.
- **ArgEscape** — 다른 메서드 의 *인자 로 전달*. *부분 최적화*.
- **GlobalEscape** — *필드, return, exception* 등 으로 *밖 으로 나감*. *최적화 불가*.

```java
// NoEscape — 최적화 가능
void noEscape() {
    StringBuilder sb = new StringBuilder();
    sb.append("hi");
    System.out.println(sb.toString());
}

// GlobalEscape — heap 필수
StringBuilder field;
void escape() {
    field = new StringBuilder();  // ★ 필드 로 escape
}
```

→ *JIT 의 *조용한 위력*. 우리 코드 의 *수많은 short-lived 객체* 가 *실제로는 heap 안 가는* 비밀.

---

## 8. *Modern Features — *2026 년의 *JVM***

### 8.1 *Virtual Thread (JEP 444, JDK 21)*

> *수십만 동시성 + 기존 동기 코드 그대로*.

내 [*Virtual Thread 글*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html) 참조. *Continuation primitive* + *carrier thread pool* 의 *마운트/언마운트*.

### 8.2 *AOT + GraalVM Native Image*

```bash
# bytecode → 네이티브 binary (시작 시간 ms)
native-image -jar myapp.jar
./myapp
# ↑ 시작 ~50ms (JVM 시작 ~2초 의 1/40)
```

장점:
- *시작 시간 ms* — *serverless / CLI* 에 강력
- *메모리 적음* (JIT 없음)
- *throughput*: *steady-state 는 C2 가 더 빠를 수 있음* (warm-up 후)

단점:
- *reflection / dynamic class loading 어려움* — 설정 필요
- *compile time 길어짐*

→ *Spring Boot 3+ Native* 의 *gradlew nativeCompile* 이 *GraalVM 기반*.

### 8.3 *JEP 신기능 들*

- **JEP 458 (JDK 22)**: Launch Multi-File Source-Code Programs — `java *.java` 한 줄
- **JEP 461 (JDK 22)**: Stream Gatherers — 사용자 정의 stream operator
- **JEP 467 (JDK 23)**: Markdown Documentation Comments
- **JEP 491 (JDK 24)**: Synchronize Virtual Threads without Pinning — *VT pinning 해결*
- **JEP 506 (JDK 25)**: Scoped Values — ThreadLocal 의 대안

→ *Java 가 *7 년 동안 *2 ~ 3 배 변했다*. *2018 년 Java 11 이 *마지막 LTS 였다고 *생각하면 *큰 손실*.

---

## 9. *진단 도구 — *4 종 세트***

### 9.1 *async-profiler — *가장 강력***

```bash
# CPU profile
asprof -e cpu -d 30 -f cpu.html <pid>

# Wall-clock profile (I/O 대기 보임)
asprof -e wall -d 30 -f wall.html <pid>

# Allocation profile (GC 부담 추적)
asprof -e alloc -d 30 -f alloc.html <pid>

# Lock contention
asprof -e lock -d 30 -f lock.html <pid>
```

→ **flame graph** 로 시각화. *어느 메서드 가 *CPU / I/O / GC / lock* 에 *시간 쓰는지* *한 눈*.

### 9.2 *JFR (Java Flight Recorder) — *내장 도구***

```bash
# 60 초 녹화
java -XX:StartFlightRecording=duration=60s,filename=flight.jfr -jar app.jar

# JDK 17+ — 항상 켤 수 있을 만큼 가벼움
java -XX:+FlightRecorder -XX:StartFlightRecording=settings=profile -jar app.jar
```

분석 :
- *JDK Mission Control (JMC)* — 무료 GUI
- *jfr print --events <event-type>* — CLI

핵심 이벤트:
- `jdk.GCPhasePause` — STW pause
- `jdk.AllocationRequiringGC` — large allocation
- `jdk.ObjectAllocationInNewTLAB` — TLAB allocation
- `jdk.VirtualThreadPinned` — VT pinning

### 9.3 *jstat — *실시간 GC 통계***

```bash
jstat -gcutil <pid> 1000   # 1초 간격
#   S0      S1      E      O      M     CCS    YGC   YGCT    FGC   FGCT     GCT
#   0.00    7.21   55.40  35.20  98.34  96.20   123    1.234     2    0.567   1.801
```

- *S0/S1*: Survivor 사용률 (%)
- *E*: Eden 사용률
- *O*: Old 사용률
- *YGC / YGCT*: Young GC 횟수 / 누적 시간
- *FGC / FGCT*: Full GC 횟수 / 시간

→ *Full GC 빈도 폭증* 또는 *O 가 90%+* 면 *memory leak 의심*.

### 9.4 *heap dump + Eclipse MAT*

```bash
# heap dump
jmap -dump:format=b,file=heap.hprof <pid>

# 또는 OutOfMemoryError 자동
java -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heap.hprof -jar app.jar
```

분석:
- **Eclipse MAT** — 무료, 강력
- *Dominator Tree* — 큰 객체 의 *retained heap*
- *Leak Suspects* — 자동 *leak 후보 식별*

→ *OOM 사고 의 *root cause* 식별 의 *결정 적 도구*.

---

## 10. *체크리스트 — *JVM 본질 의 실전***

내가 *production Java 앱* 운영 시 *반드시 확인* 하는 *12 가지*:

**힙 / GC**:
1. *`-Xms`* 와 *`-Xmx`* 가 *같은가* (resize 비용 회피)
2. *G1 또는 ZGC* 사용 중인가 (production 기본)
3. *`-XX:MaxGCPauseMillis`* 적절한가
4. *`-Xlog:gc*` 가 *파일 로깅* 되어 있는가
5. *Full GC 빈도* 가 *분당 1 회 미만* 인가
6. *jstat -gcutil* 또는 *Grafana 의 *JVM dashboard* 모니터링 하는가

**진단**:
7. *async-profiler* 가 *production 에 설치* 되어 있는가 (사고 시 즉시 사용)
8. *JFR* 또는 *프로파일링* 이 *상시 켜져* 있는가 (낮은 overhead)
9. *Heap dump on OOM* (`-XX:+HeapDumpOnOutOfMemoryError`) 활성화 됐는가

**튜닝**:
10. *`-XX:+TieredCompilation`* (default) — *startup latency*
11. *`-XX:+UseStringDeduplication` (G1)* — String 중복 제거, memory 절감
12. *Container 환경* 에서 *`-XX:MaxRAMPercentage=75`* (k8s memory limit 의 *비율*)

---

## 11. *결론 — *추상화 의 *3 단 깊이***

> Java 코드 의 *한 줄* 의 *밑* 에 *3 단 의 추상화* 가 있다 — *Bytecode 의 *플랫폼 무관*, *JIT 의 *적응 적 최적화*, *GC 의 *자동 메모리 관리*. *각 단 의 본질* 을 *알아야 *그 추상화 가 *어디서 깨지는지* 알 수 있다.

오늘 정리한 *JVM 의 7 본질* :
1. **Class Loading** — 위임 모델 + 보안 토대
2. **Bytecode** — Stack machine + invokedynamic
3. **JIT** — Tiered + Inlining + Deoptimization
4. **GC** — Generational + G1 + ZGC + STW
5. **Memory Model** — happens-before + volatile + final
6. **Escape Analysis** — Stack allocation + Lock elision
7. **Modern** — Virtual Thread + AOT + Native Image

> *Spring Boot 의 *모든 줄 의 *밑* 에 *이 7 가지 가 *함께 *돈다*. *p99 latency 의 *spike* 가 *GC pause 인지 *JIT warm-up 인지 *lock contention 인지* — *그 식별 의 능력* 이 *시니어 Java 의 *진짜 깊이*.

*2026 년 의 Java 는 *7 년 전 의 Java 가 아니다*. *Virtual Thread, ZGC, GraalVM Native, Pattern Matching, Records, Sealed* — *모두 production-ready*. *그 변화 의 *흐름 을 *놓치지 않는 것* 이 *시니어 의 *기본기*.

---

## *참고*

- *Java Performance — The Definitive Guide* (Scott Oaks).
- *The Garbage Collection Handbook* (Jones, Hosking, Moss).
- *Java Concurrency in Practice* (Brian Goetz).
- *JEP Index* — [openjdk.org/jeps](https://openjdk.org/jeps/0).
- *async-profiler* — [github.com/async-profiler/async-profiler](https://github.com/async-profiler/async-profiler).
- 자매편:
  - [*DB 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
  - [*Virtual Thread*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
  - [*오브젝트 서평*](/2026/06/22/object-book-review-cho-younghoo-object-oriented-design.html)
