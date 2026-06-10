---
layout: post
title: "백엔드 개발자가 알아야 할 *가비지 컬렉터와 메모리 사용* — JVM 중심으로"
date: 2026-06-10 17:30:00 +0900
categories: [backend, performance, jvm]
tags: [gc, garbage-collection, jvm, memory, heap, g1, zgc, performance, java]
---

> *백엔드가 *느려진다* 의 *체감 30%* 는 *GC pause* 다. 단 *원인을 잘못 짚으면 *반대 방향* 으로 튜닝* 한다.
> *큰 heap* 이 *항상 좋은 게 아니고*, *GC 가 *항상 나쁜 것* 도 *아니다*.
> *원리 + 측정 + 결정* — 이 세 가지가 *GC 와의 *건강한 관계*.

---

## TL;DR

| 항목 | *핵심* |
|------|--------|
| **GC 의 역할** | *수동 메모리 관리 비용 *0* 으로 만듦. 단 *지연 (pause) 비용* 으로 대체* |
| **Heap 크기** | *너무 작으면 *OOM*, 너무 크면 *GC pause 폭증* (32GB+ 면 신중) |
| **G1 vs ZGC** | *G1 = 안정적 default. ZGC = *큰 heap + 짧은 pause* 추구* |
| **메모리 누수** | *JVM 에선 *Reference 가 *잡고 안 놓는 경우*. ThreadLocal, Cache, Listener |
| **튜닝 우선순위** | *측정 → *Heap 크기 + GC 알고리즘* → 코드 변경* |
| **모니터링** | *Heap 사용량, GC 횟수/시간, allocation rate, promotion rate* |

---

## 1. *왜 GC 가 *중요* 한가*

C / C++ 의 *수동 메모리 관리* — *malloc / free* 의 *모든 책임* 이 개발자에게. *자유롭지만 *위험*. *메모리 누수 / use-after-free / double-free* — *전통적 *버그의 50%*.

GC 의 *발명* :

> *런타임이 *불필요해진 객체* 를 *자동 감지 + 회수**.

*Lisp* (1959) 가 *최초*. Java (1995) 가 *대중화*. *Go / Python / JS / C# / Kotlin* 모두 GC 언어.

GC 의 *대가* :

- *GC 실행 시점 = 응답 지연 (pause)*
- *GC 알고리즘에 따라 *짧은 pause + 자주 vs 긴 pause + 드물게*
- *CPU 의 *5~20% 가 GC 에* — *throughput 비용*

→ *GC 가 *느림의 원인* 인 경우 *많지만*, *없으면 *더 위험*. *균형* 의 문제.

---

## 2. **JVM 메모리 구조** — *Heap 만이 *전부* 가 아니다*

```
                    ┌─────────────────────────────────────┐
                    │ JVM Process Memory                  │
                    ├─────────────────────────────────────┤
                    │ ① Heap (객체 저장)                  │
                    │   ├─ Young Generation               │
                    │   │   ├─ Eden                       │
                    │   │   └─ Survivor 0 / 1             │
                    │   └─ Old Generation                 │
                    ├─────────────────────────────────────┤
                    │ ② Metaspace (클래스 메타데이터)     │
                    ├─────────────────────────────────────┤
                    │ ③ Stack (메서드 / local var, 스레드별) │
                    ├─────────────────────────────────────┤
                    │ ④ Direct Buffer (NIO / Netty)       │
                    ├─────────────────────────────────────┤
                    │ ⑤ Code Cache (JIT 컴파일 결과)      │
                    ├─────────────────────────────────────┤
                    │ ⑥ Native (JNI, OS libraries)        │
                    └─────────────────────────────────────┘
```

흔한 *오해* :

> *"Heap 만 신경쓰면 됨"*

→ *틀림*. *컨테이너 OOMKilled* 의 가장 흔한 원인은 *Metaspace / Direct Buffer / Native* 가 *예상 외 증가*. *Heap 은 *멀쩡* 한데도* OOM.

### 권장 *시작 비율* (총 컨테이너 RAM 기준)

```
Heap          : 50%   (대형)
Direct Buffer : 10%   (NIO / Netty 쓸 때)
Metaspace     : 5%    (작은 앱)
Stack 합계    : 5%
Code Cache    : 2%
여유 / OS     : 28%
```

*컨테이너 RAM 4GB* 면 *heap 2GB* 정도가 *시작점*. *전부 heap 에 박지 마라*.

---

## 3. **Generational GC** — *대부분 객체는 *빨리 죽는다**

GC 의 *대원칙* (weak generational hypothesis) :

> *대부분 객체는 *생성 직후 *짧은 수명* 으로 죽는다*.

JVM 의 heap *세대 분리* :

- **Young Generation** — *방금 만든 객체*. 90% 가 *몇 ms 안* 죽음.
- **Old Generation** — *살아남은 객체* (캐시, 세션, 풀 등)
- ***Survivor* 영역** — *Young 의 *임시 *살아남은 객체* 보관*

### 동작 흐름

```
1. new 객체 → Eden 에 할당
2. Eden 가득 차면 → *Minor GC* (Young 영역만 수집)
   - 살아있는 객체 → Survivor 로
   - 죽은 객체 → 즉시 회수
3. 여러 Minor GC 살아남으면 → *Old* 로 *promote*
4. Old 가득 차면 → *Major GC / Full GC* (전체 수집)
   - *Stop-the-world 가 *오래 걸림*
```

> ***Minor GC 는 *흔하고 빠름*** — 수십 ms 단위
> ***Major / Full GC 는 *드물고 *길다*** — 수백 ms ~ 수 초 (heap 크기 비례)

→ *튜닝의 핵심* : *Full GC 를 *최대한 안 일어나게*.

---

## 4. **GC 알고리즘** — *상황별 *선택*

### Serial GC

*단일 스레드 GC*. *작은 앱 / 임베디드*. *현대 백엔드 거의 *안 씀*.

### Parallel GC (Java 8 까지 default)

*다중 스레드 GC*. *throughput 최강*. 단 *pause 가 길음* (수백 ms ~ 수 초).

*batch job / 분석 작업* 처럼 *throughput 우선* 인 경우.

### G1 GC (Java 9~17 default)

*Heap 을 *region 단위로 분할*. *점진적 수집*. *예측 가능한 pause 목표*.

- *권장 heap 4 ~ 32GB*
- *기본 pause 목표 200ms*
- *현대 Spring Boot API 의 *기본 선택*

### **ZGC** (Java 15 production)

*초저지연 GC*. *대부분 작업 concurrent*. *pause < 10 ms* 목표.

- *권장 heap 8GB ~ TB*
- *pause 일정* (heap 크기에 *덜 영향*)
- *throughput 은 *G1 보다 *조금 낮음*
- *Java 21+ 에선 *production 기본 후보*

### Shenandoah (Red Hat)

*ZGC 와 *경쟁*. *concurrent 압축*. *OpenJDK 의 *대안*.

### *알고리즘 *선택 가이드*

```
일반 Spring Boot API (heap < 8GB)   → G1
대규모 캐시 / heap 16GB+              → ZGC
Batch / 분석 (pause 허용)             → Parallel
극저지연 (HFT 등)                     → ZGC + 코드 최적화
```

---

## 5. *GC pause* — *시스템 응답시간의 *변동성*

GC 의 *pause* 는 *Stop-the-world (STW)* — *모든 application thread 정지*. *그 동안 새 요청 못 받음*.

### Pause 의 *영향*

- *100ms pause* — *그 순간 *모든 요청 *100ms 지연*. *p99 / p999 의 *원인*.
- *수 초 pause* — *health check 실패* → *Kubernetes 가 *unhealthy 판정* → *재시작*. *장애 chain*.

### *Pause 추적 *지표*

```
- GC pause duration (P99, max)
- GC pause frequency
- *Allocation rate* (MB/s)
- *Promotion rate* (Young → Old)
- *Heap usage curve* (sawtooth pattern 정상)
```

JFR (Java Flight Recorder) / VisualVM / Prometheus JMX exporter 로 *모두 수집*.

---

## 6. *메모리 누수 (Memory Leak)* — *GC 가 *못 잡는 *객체*

GC 가 *수집 못하는 *이유* — *Reference 가 *어딘가 *남아있어서*. 흔한 패턴 :

### 6.1. *ThreadLocal* 미해제

```java
private static ThreadLocal<User> currentUser = new ThreadLocal<>();
// set 후 remove() 안 함 → thread pool 의 thread 살아있는 한 *영원히 참조*
```

→ *큰 객체 ThreadLocal + thread pool* = *메모리 누수 *상위 1 위*.

### 6.2. *static Collection* 무한 누적

```java
private static List<Object> cache = new ArrayList<>();
public void add(Object o) { cache.add(o); }  // remove 없음
```

→ *영원히 자라는 List*. *재시작 전엔 *해제 안 됨*.

### 6.3. *Listener / Observer* 등록 후 해제 안 함

*이벤트 리스너* 가 *대상 객체* 참조. *대상이 *논리적으로 *끝나도* 리스너가 *살아있어 GC 못 함*.

### 6.4. *내부 클래스 의 *외부 참조*

```java
class Outer {
  class Inner { ... }  // *implicit Outer reference*
}
```

*Inner 객체* 가 *오래 살면* *Outer 도 *못 죽음*. *static class* 권장.

### 6.5. *캐시 + TTL 없음*

```java
private Map<String, Object> cache = new HashMap<>();
// TTL / size limit 없음 → 무한 증가
```

→ *Caffeine 같은 *bounded cache* 권장.

---

## 7. *Heap 크기 결정* — *너무 크면 *또한 *문제*

흔한 *오해* :

> *"RAM 많으면 *heap 크게 잡으면 *좋다*"*

→ *틀림*. *큰 heap = *긴 Full GC pause*.

### *작은 heap (~4GB)*

- *Minor GC 잦음* — 매 초 가능
- *Full GC 짧음* — *수십 ms*
- *pause 변동성 *적음*

### *큰 heap (32GB+)*

- *Minor GC 느림* — *Young 영역도 *큼*
- *Full GC 길음* — *수 초 가능* (G1 도)
- *ZGC 가 *해법* — pause heap 크기에 *덜 의존*

### *권장 *시작점*

```
Spring Boot API (트래픽 보통)  : -Xmx2g
대규모 캐시 (in-process)        : -Xmx8g
Elasticsearch / Kafka            : -Xmx16g ~ 32g
ML inference / 큰 데이터 처리   : -Xmx32g+ (ZGC)
```

*경험상 *heap 8GB 가 *분기점*. *그 이상* 이면 *G1 → ZGC 전환 검토*.

---

## 8. *튜닝의 *우선순위*

> *코드 변경 *전에* 측정* — 절대 원칙.

순서 :

1. **측정** — 현재 GC pause / heap usage / allocation rate
2. **heap 크기 조정** — 너무 작으면 키우고 / 너무 크면 줄임
3. **GC 알고리즘 변경** — G1 → ZGC 등
4. **GC 옵션 튜닝** — `-XX:MaxGCPauseMillis`, `-XX:G1HeapRegionSize` 등
5. *마지막에 *코드 변경** — *불필요한 객체 생성 줄이기*

대부분 시스템은 *1~3 만으로 *충분*. *4~5 는 *최후의 *카드*.

### *흔히 효과 있는 *옵션*

```
-Xmx<크기>                       # Heap 최대
-Xms<크기>                       # Heap 초기 (Xmx 와 동일 권장 — 변동 줄임)
-XX:MaxGCPauseMillis=200         # G1 pause 목표
-XX:+UseG1GC                     # G1 사용
-XX:+UseZGC                      # ZGC 사용
-XX:+UnlockExperimentalVMOptions # 일부 실험 옵션
-XX:MaxRAMPercentage=75.0        # 컨테이너 RAM 의 75% 까지 heap
```

컨테이너 환경에선 *`-Xmx` 대신 *`-XX:MaxRAMPercentage`*** 권장 — *컨테이너 RAM 변경 시 *자동 반영*.

---

## 9. *Allocation Rate* — *GC 의 *진짜 원인*

*초당 *몇 MB 객체* 를 *만드는가* — *Allocation Rate*. *높을수록 *Minor GC 잦음 + Old 로 promote 많음*.

### *높은 allocation rate 의 *원인*

- *불필요한 String concatenation* (Java 8 이전, builder 사용 안 함)
- *과한 *JSON 직렬화* (큰 객체)
- *Stream 의 *남용* — *각 단계마다 *intermediate 객체*
- *Logging 의 *과한 detail*
- *Reflection / proxy 의 *과한 사용*

### *측정*

```
jcmd <pid> GC.heap_info
async-profiler --alloc <pid>
JFR 의 *Allocation events*
```

500 MB/s 가 *경고선*. 1 GB/s 이상이면 *코드 수정 필요*.

---

## 10. *모니터링* — *반드시* 봐야 할 *지표*

```
필수 :
- Heap used / committed / max
- GC count (Minor / Major)
- GC time (P99, sum/sec)
- *Allocation rate* (bytes/sec)
- *Promotion rate* (Young → Old)
- Metaspace used
- Direct Buffer used
- Thread count
```

도구 :

- **Micrometer + Prometheus** — Spring Boot 표준
- **JFR (Java Flight Recorder)** — 내장, 저비용
- **async-profiler** — 깊은 분석 (allocation, lock contention)
- **VisualVM / JProfiler** — 시각화 / interactive

> *모니터링 *없이 튜닝* 하지 마라*. *짐작 으로 *바꾼 옵션* 이 *상황 더 악화* 시키는 경우가 *상시*.

---

## 11. *내 *7년* 경험* — *흔한 *패턴 4 가지*

### 11.1. *Spring Boot API — heap 2GB, G1*

대부분 *충분*. *추가 튜닝 안 함*. *기본값이 *생각보다 *훌륭함*.

### 11.2. *Elasticsearch — heap 16~32GB, G1 → ZGC*

*JVM 권장 max 32GB* (compressed oops). *그 이상은 *오히려 *역효과*. 최근 *ZGC 로 *전환* 하니 *full GC pause 가 *10초 → 200ms* 로 *극적 개선*.

### 11.3. *Kafka — heap 6GB, G1*

*대부분 메모리는 *OS page cache 에* — *heap 작게 *유지*. *6GB 가 *충분*.

### 11.4. *Spring Batch — heap 8GB, Parallel*

*batch 작업* 은 *pause 허용*. *throughput 우선* 으로 *Parallel GC* 선택.

---

## 12. *흔한 함정 7가지*

1. ***heap 무조건 *크게 잡기*** — *비용 + Full GC pause* 증가.
2. ***기본 GC 가 *항상 *적정* 이라 *생각*** — *워크로드별 *알고리즘 다름*.
3. ***메모리 누수 = OutOfMemory 만*** — *Slow leak* 은 *몇 주에 *한 번 *재시작* 으로 *덮인다*.
4. ***`System.gc()` 호출*** — *Full GC 강제 trigger*. *거의 *항상 *해롭다*. *부르지 마라*.
5. ***Direct Buffer 누수*** — *Netty / NIO 환경에서 *큰 buffer 안 해제 → *컨테이너 OOM*.
6. ***Metaspace 누수*** — *동적 클래스 로딩 (Groovy / 동적 proxy) 의 *지속 적인 *클래스 생성*. *Metaspace 무한 증가*.
7. ***ThreadLocal *해제 안 함*** — *thread pool 환경 의 *영원한 메모리 *점유*.

---

## 13. 마치며

> *GC 는 *고급 *시니어 영역* 이 *아니다*. *모든 백엔드 개발자 의 *기본 교양*. 단 *깊이는 *연차에 따라*.

핵심 3 줄 :

1. **측정 *없이* 튜닝 *없다*** — 모든 결정은 *데이터 기반*.
2. **heap 크기 + GC 알고리즘 *2 개* 만 잘 잡아도 *80% 해결*** — 미시 옵션 *대부분 불필요*.
3. **메모리 누수의 *상위 패턴 5* 만 *체크 list* 로 *항상 점검*** — ThreadLocal / static Collection / Listener / Inner class / unbounded cache.

이 *3 줄* 을 *7년차 *까지 따라가면* — *GC 가 *시스템 운영의 *친구* 가 *된다*. *적이 아니다*.

다음 글 — *Direct Buffer 와 Off-Heap Memory* — Netty / Kafka 등 *큰 시스템 의 *숨겨진 *메모리 *함정*. 시리즈로 이어집니다.

---

> 본 글은 *7년차 백엔드 운영 회고*. *JVM 중심* 이지만 *Go / Node.js / Python* 의 GC 도 *원리 유사*. *세대 가설 + STW + Allocation rate* 의 *3 가지 개념* 만 *몸에 익히면* 다른 언어도 *빠르게 *적응*.
