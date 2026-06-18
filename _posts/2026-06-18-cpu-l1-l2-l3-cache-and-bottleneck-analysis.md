---
layout: post
title: "*CPU 의 *L1 / L2 / L3 캐시* — *메모리 벽* 과 *병목 구간* 에 대한 *고찰*"
date: 2026-06-18 22:00:00 +0900
categories: [computer-architecture, performance, low-level]
tags: [cpu, cache, l1-cache, l2-cache, l3-cache, memory-wall, false-sharing, cache-line, performance-tuning, perf, numa, prefetcher]
---

> *"CPU 가 빠르다"* 는 말 은 *반쪽 짜리 진실* 이다. *CPU 는 *빠르지만*, *그 CPU 가 *기다리는 시간* 의 대부분은 *메모리* 다. *현대 CPU 의 *코어 클럭* 은 *4~5 GHz* — 즉 *0.25 ns* 안에 *한 사이클* 을 돌린다. 그런데 *DRAM 접근* 은 *80~120 ns* — 그 사이 *CPU 는 *400 ~ 500 사이클* 을 *놀고 있다*.
>
> 이 격차를 *메모리 벽 (Memory Wall)* 이라고 부른다. *캐시 (L1 / L2 / L3)* 는 *그 벽 을 *조각조각 *허무는 *3 단계 *완충재* 다. *각각 *얼마나 *빠르고*, *얼마나 *크고*, *어떻게 *공유* 되고, *어디서 *병목* 이 *터지는지* — 그 *구조* 를 *모르면* *성능 튜닝* 은 *추측 게임* 이 된다.
>
> 이 글은 *L1 / L2 / L3 의 *물리적 / 논리적 차이*, *현대 워크로드 의 *6 가지 캐시 병목 패턴*, *측정 도구*, *완화 패턴* 을 *런타임 관점* 에서 정리한다.

---

## TL;DR — *한 줄 결론*

> *CPU 캐시 는 *3 단계* 다. *L1 (코어 전속, ~4 사이클, ~32KB)* / *L2 (코어 전속, ~12 사이클, ~1MB)* / *L3 (소켓 공유, ~40 사이클, ~수십 MB)*. *DRAM (~300 사이클)* 까지 떨어지면 *코어 가 *놀게 *된다*. *대부분의 성능 병목* 은 *알고리즘 의 *복잡도* 가 아니라 *메모리 접근 패턴 의 *캐시 친화성* 에서 *온다*. *AoS 를 *SoA 로 바꾼 *한 줄* 이 *10 배 빠르게 *만들 수 있고*, *padding 1 줄* 이 *false sharing 으로 죽던 *멀티스레드 코드* 를 *살린다*.

---

## 1. *왜 *캐시 가 *필요 한가* — *메모리 벽 의 *물리학*

### 1.1 *클럭 격차 의 *실제 숫자*

| 자원 | 접근 시간 | 4 GHz 기준 사이클 | L1 대비 배수 |
|---|---|---|---|
| L1 캐시 (D) | ~1 ns | ~4 사이클 | 1x |
| L2 캐시 | ~3 ns | ~12 사이클 | 3x |
| L3 캐시 | ~10 ns | ~40 사이클 | 10x |
| DRAM (로컬) | ~80 ns | ~320 사이클 | 80x |
| DRAM (NUMA 원격) | ~140 ns | ~560 사이클 | 140x |
| NVMe SSD | ~80 μs | ~320,000 사이클 | 80,000x |
| 회전 HDD | ~10 ms | ~40,000,000 사이클 | 10,000,000x |

> *L1 hit* 이 *DRAM access* 의 *1/80* 이라는 것 은 *"좀 더 빠르다"* 가 *아니라* *"완전히 다른 종류의 자원"* 이라는 *물리적 사실* 이다.

### 1.2 *왜 *3 단계 인가*

캐시 가 *한 층* 이라면 *간단* 했을 텐데, *왜 *3 단계 로 나눴나*.

→ *속도 와 *용량 의 *역상관* 때문 :

- *SRAM (캐시 의 재료) 는 *DRAM 보다 *약 *6 배 더 많은 트랜지스터* 를 *셀 당 사용* 한다 (6T vs 1T1C).
- *큰 SRAM* 은 *물리적으로 *멀어진다* → *전기 신호 가 *거기 도달하는데* *시간이 더 걸린다*.
- *크게 만들면 *느려지고*, *작게 만들면 *덜 담긴다*.

→ *그래서 *작고 빠른 L1* / *중간 L2* / *크고 느린 L3* 의 *3 단계 분할 이 *물리적 최적* 이 된다.

### 1.3 *캐시 라인 — *64 바이트 가 *모든 것의 *단위*

현대 x86 (Intel, AMD) 와 *대부분의 ARM64* 는 *64 바이트* 를 *캐시 라인 크기* 로 쓴다. 즉:

> *CPU 가 *바이트 1 개* 를 *읽어도* *항상 *64 바이트 한 줄* 이 *통째로* *L1 으로 올라온다*.

이 *64 바이트 단위* 가 *false sharing*, *struct padding*, *cache line bouncing* 같은 *모든 캐시 병목 의 *기본 단위* 가 된다.

---

## 2. *L1 캐시* — *코어 의 *손 끝* 에 *붙은 *지갑*

### 2.1 *물리 위치 와 *구조*

- *각 코어 마다 *전용* (per-core).
- *L1I (Instruction) + L1D (Data)* 로 *나뉜다* — *Harvard 구조 안쪽*.
- 크기 : 보통 *32 KB + 32 KB* (Intel Skylake ~ Raptor Lake). *Apple M3 P-core* 는 *L1D 64 KB*.
- 지연 : ~4 사이클.
- 연관도 (associativity) : 8-way 또는 12-way set associative.

### 2.2 *L1I 와 *L1D 가 *왜 분리 되었나*

> *명령어 와 *데이터* 는 *서로 다른 *접근 패턴* 을 갖는다.

- *명령어* 는 *순차적* (sequential, branch 외엔) — *prefetch 친화*.
- *데이터* 는 *불규칙* — *random access 흔함*.

→ *한 캐시에 *둘 다 담으면* *서로 *밀어낸다* (cache thrashing). *분리 하면 *각자 *자기 패턴 에 *최적화* 된다. *Harvard 구조* 가 *L1 단에서만* 살아남은 이유.

### 2.3 *L1 hit 의 *위력*

```text
L1 hit  : 4 cycles
L2 hit  : 12 cycles  → L1 의 3 배
L3 hit  : 40 cycles  → L1 의 10 배
DRAM    : 320 cycles → L1 의 80 배
```

> *"L1 안에 *유지 한다"* 는 것 은 *단순한 최적화 가 *아니라* *80 배 의 *체급 차이* 다.

*핫 루프 의 *작업 집합 (working set)* 이 *32 KB 안* 에 들어가면 *그 루프 는 *L1 에서 *코어 클럭* 으로 *달린다*. *32 KB 를 *조금 넘어가면* *L2 로 떨어지고*, *그 순간 *3 배 느려진다*.

---

## 3. *L2 캐시* — *코어 의 *중간 지대*

### 3.1 *위치 와 *크기*

- *대부분 *코어 전속* (Intel, AMD Zen).
  - *예외* : *ARM big.LITTLE cluster* 는 *L2 를 *클러스터 공유* 하는 경우도 있다.
- 크기 : *Intel Coffee Lake 256 KB* → *Raptor Lake P-core 2 MB*. *AMD Zen4 1 MB*. *Apple M3 P-core 16 MB* (Apple 은 *L2 가 비정상적으로 크다*).
- 지연 : ~10 ~ 15 사이클.
- *Inclusive* vs *Non-inclusive* — Intel 은 *non-inclusive (Skylake-X 이후)*, AMD Zen 은 *non-inclusive*.

### 3.2 *L2 의 *진짜 역할*

> *L1 이 *놓치면 *우선 *여기서 *받아준다*. *DRAM 까지 가지 않게 *막는 *보험*.

L1 (32KB) 은 *너무 작아서 *조금만 *큰 데이터* 를 다루면 *바로 *터진다*. L2 (1MB) 가 그 *완충* 을 *맡는다*.

```text
L1 miss → L2 hit  : 추가 ~8 cycles → 총 ~12 cycles
L1 miss → L3 hit  : 추가 ~36 cycles → 총 ~40 cycles
L1 miss → DRAM    : 추가 ~316 cycles → 총 ~320 cycles
```

→ *L2 가 *받아주면 *3 배 느린 정도* 로 끝나지만, *L2 도 *놓치면 *40 배 까지 *밀려난다*. *L2 hit rate* 가 *조용한 1 등 지표* 인 이유.

### 3.3 *현대 워크로드 의 *L2 압박*

- *Spring Boot 서비스* 의 *전형적인 hot working set* : 직렬화 buffer, JIT 코드, GC card table, 도메인 객체 그래프 — *수 MB 단위*. *L1 안에 들어갈 수 없고, *L2 가 *살리느냐 *죽이느냐* 가 *latency p99* 를 *흔든다*.
- *JIT compiled code* 가 *L1I 를 *압박* → *L2I 까지 떨어지면 *분기 예측 실패 비용 이 *눈에 보일 정도로 늘어난다*.

---

## 4. *L3 캐시 (LLC)* — *소켓 의 *공유 자원*

### 4.1 *위치 와 *크기*

- *소켓 안 모든 코어 가 *공유* (Intel monolithic) 또는 *CCX (chiplet) 단위 로 공유* (AMD Zen2+).
- 크기 : *Intel i9-14900K 36 MB*, *AMD 7950X 64 MB*, *EPYC 9684X 1152 MB (3D V-Cache)*.
- 지연 : *Intel ~40 사이클*, *AMD ~50 사이클*, *V-Cache stack 추가시 +4 사이클*.

### 4.2 *L3 의 *2 가지 책임*

1. *DRAM 으로 떨어지기 전 *마지막 완충*.
2. *코어 간 *공유 메모리 의 *합류 지점* — *MESI / MOESI 캐시 코히어런시 트래픽* 이 *여기서 처리* 된다.

### 4.3 *L3 가 *공유 이기에 *생기는 문제*

> *코어 가 *많을수록* *L3 한 줄을 *놓고 *N 코어가 *경쟁* 한다.

*16 코어 32 스레드* 가 *36 MB L3* 를 나눠 쓰면 *코어 당 평균 2.25 MB* 다. *하지만 한 워크로드 가 *공격적* 이면 *다른 코어 의 *L3 가 *evict* 된다 → *그 코어의 *DRAM 접근 이 늘어남* → *latency 상승*.

→ *클라우드 multi-tenant* 환경에서 *noisy neighbor* 문제 의 *물리적 근원*.

### 4.4 *V-Cache 같은 *3D 적층*

AMD 가 *Ryzen X3D / EPYC X* 에 *L3 위에 *추가 SRAM 다이 를 적층* (96MB ~ 1152MB). *게이밍 워크로드* 의 *working set 이 *대부분 *L3 압박 형* 이라 *그 한 단계 차이* 가 *FPS 10~30% 향상* 으로 *측정 된다*.

→ *L3 hit rate* 가 *그만큼 *중요한 *현실의 지표* 라는 *반증*.

---

## 5. *DRAM 너머* — *NUMA 와 *원격 메모리*

### 5.1 *NUMA 토폴로지*

서버 급 시스템 (2 소켓 이상) 은 *각 소켓 이 *자기 *DRAM 채널* 을 갖는다. *내 소켓 의 DRAM* 은 *80 ns*, *옆 소켓 의 DRAM* 은 *140 ns* — *2 배 느림*.

```text
Socket 0  ─────── (UPI / Infinity Fabric) ─────── Socket 1
   │                                                  │
  로컬 DRAM (80ns)                              원격 DRAM (140ns)
```

> *NUMA 미친 짓* 은 *스레드 가 *소켓 0 에 있는데 *그 스레드 의 데이터 가 *소켓 1 에 있을 때* 다. *모든 메모리 접근 이 *2 배 + 코히어런시 트래픽* 으로 *팽창*.

### 5.2 *해결* : *thread + memory affinity*

- Linux : `numactl --cpunodebind=0 --membind=0` 로 *바인딩*.
- JVM : `-XX:+UseNUMA` (G1, Parallel GC), `-XX:+UseNUMAInterleaving`.
- *Kubernetes 환경* : *topology manager* + *CPU manager* 정책 (`single-numa-node`).

---

## 6. *6 가지 *캐시 병목 패턴* — *현장 의 *고질병*

### 6.1 *Cache Miss 의 *3 종류 (3 C's)*

전통 *3 C model* (Mark Hill, 1989) :

1. *Compulsory miss (cold)* — *처음 *접근* — 캐시 가 *알 길 없음* — *prefetch 외엔 해결 불가*.
2. *Capacity miss* — *작업 집합 > 캐시 크기* — *알고리즘 / 데이터 구조 *재설계* 로만 해결.
3. *Conflict miss* — *associativity 한계* 로 *같은 set 에 충돌* — *데이터 정렬 / 패딩* 으로 해결.

여기에 *멀티코어 시대* 의 *4 번째* :

4. *Coherence miss* — *다른 코어 가 *내 캐시 라인을 *invalidate* — *false sharing / true sharing* 의 *세계*.

### 6.2 *병목 패턴 1 — False Sharing*

> *두 스레드 가 *서로 다른 변수 를 *바꾸는데*, *그 두 변수 가 *같은 64 바이트 캐시 라인* 안에 있다.

```java
class Counter {
    long a;   // Thread 1 이 ++a
    long b;   // Thread 2 가 ++b
}            // a 와 b 는 16 바이트 안에 — 같은 cache line
```

*Thread 1 이 `a++` 하는 순간 *그 cache line 의 *Modified 권한 을 가져온다* → *Thread 2 의 *그 line 은 *Invalid* 가 된다 → *Thread 2 가 `b++` 하려면 *그 line 을 *다시 가져와야 함* → *MESI 핑퐁*.

→ *논리적으로 *완전 무관한 *두 변수* 가 *물리적 인접성* 만으로 *서로 의 성능을 *죽인다*. *최대 100 배 까지 느려지는 사례 흔함*.

*해결* : *패딩*.

```java
class Counter {
    long a;
    long[] pad1 = new long[7];  // 56 byte → a 가 한 line 독차지
    long b;
}
// 또는 JDK 8+ : @Contended (jdk.internal.vm.annotation.Contended)
```

### 6.3 *병목 패턴 2 — True Sharing / Cache Line Bouncing*

> *진짜로 *공유 되는 변수* 를 *N 코어 가 *동시에 *쓴다*.

*공유 카운터*, *공유 큐 의 tail pointer*, *atomic flag* 등. *논리적으로 정당* 하지만 *물리적으로는 *한 line 이 *N 코어 사이 *왔다갔다*.

→ *atomic increment* 가 *single thread 1 ns* → *16 thread 동시* 일 때 *200 ns+* 로 *터지는 이유*.

*해결* :
- *thread-local accumulator* + *주기적 merge* (Java 의 `LongAdder` 가 *이 패턴*).
- *Reservation pattern* — 일정 범위를 *코어 별로 *예약 / 분배*.
- *Lock-free 자료구조 의 *근본 한계* 가 *여기서 *온다*.

### 6.4 *병목 패턴 3 — Working Set > L3*

> *알고리즘 은 *맞는데*, *데이터 가 *너무 커서 *L3 도 못 받아준다*.

*hash join*, *Spark shuffle*, *대규모 in-memory 인덱스* 의 *전형*. *모든 접근 이 *DRAM 으로 떨어지면* *코어 활용률 이 *20% 도 안 된다* (대부분 *stall*).

*해결* :
- *Loop tiling / blocking* — *데이터를 *L2 또는 *L3 크기 의 *블록* 으로 *쪼개* 처리.
- *Cache-oblivious algorithms* (Frigo et al., 1999) — 재귀적으로 자연스럽게 *모든 캐시 레벨 적합*.
- *Streaming algorithms* — *한 번 만 *훑고* *cache 에 *남기지 않음* (`_mm_stream_*` 같은 NT store).

### 6.5 *병목 패턴 4 — Pointer Chasing 이 *Prefetcher 를 *무력화* 한다*

HW prefetcher 는 *연속적 / 스트라이드 패턴* 을 인식해 *미리 가져온다*. *링크드 리스트* 는 *다음 노드 주소 가 *현재 노드 안 에 있다* → *prefetcher 가 *예측 불가* → *모든 노드 가 *cold miss*.

→ *LinkedList traversal* 이 *ArrayList traversal* 보다 *10 배 느린 *물리적 이유*.

*해결* :
- *배열 기반 구조* (ArrayList, ArrayDeque, open-addressing hash table).
- *Software prefetch* : `__builtin_prefetch(next->next, 0, 0)` — *다음 노드 의 다음* 을 *미리 요청*.
- *데이터 컴팩션* — 노드 안 *큰 payload* 를 *바깥으로 빼고* 노드 자체는 *작게 (cache line 1~2 줄)*.

### 6.6 *병목 패턴 5 — AoS vs SoA*

> *Array of Structs (AoS)* : `Particle[] {x, y, z, mass, color, ...}` — *모든 필드 가 *함께 묶여서 *한 캐시 라인*.
> *Struct of Arrays (SoA)* : `float[] x, float[] y, float[] z, ...` — *같은 필드 끼리 *연속 메모리*.

만약 *수백만 particle 의 *x 좌표만 *업데이트* 한다면 :

- *AoS* — *y, z, mass, color 도 *같이 캐시에 끌려 옴* → *cache line 사용률 ~12.5%* (4 byte / 32 byte struct).
- *SoA* — *x 만 *연속해서 *읽음* → *cache line 100% 활용* → *SIMD 도 자연스럽게 적용*.

→ *게임 엔진 / 시뮬레이션 / ML* 이 *SoA 로 *기울어지는 *물리적 이유*. *Data-Oriented Design (DOD)* 의 *근본*.

### 6.7 *병목 패턴 6 — TLB Miss (자주 *잊혀지는 *7번째 캐시)*

CPU 는 *가상 주소 → 물리 주소* 변환을 위해 *TLB (Translation Lookaside Buffer)* 를 쓴다 — *MMU 의 캐시*.

- L1 TLB : ~64 entries (4KB 페이지 기준 256KB 커버)
- L2 TLB : ~1500 entries (4KB 페이지 기준 6MB 커버)
- *TLB miss* → *page table walk* → *최대 4 단계 메모리 접근* → *수백 사이클*.

→ *큰 데이터셋* 을 *random 하게* 접근하면 *cache miss + TLB miss* 가 *동시에 터진다* — *체감 latency 가 *예상치의 *2 배* 가 나오는 흔한 원인.

*해결* : *Huge pages (2MB / 1GB)*. Linux `transparent_hugepage=always` 또는 `madvise`. JVM `-XX:+UseLargePages`.

---

## 7. *측정* — *추측 대신 *숫자*

### 7.1 *Linux `perf` 한 줄*

```bash
perf stat -e \
  cycles,instructions,\
  L1-dcache-loads,L1-dcache-load-misses,\
  LLC-loads,LLC-load-misses,\
  dTLB-loads,dTLB-load-misses \
  ./my-binary
```

읽는 법 :

- *IPC (instructions/cycles)* < 1.0 → *memory-bound 의심*.
- *L1 miss rate* > 5% → *작업 집합* 이 *L1 보다 큼*.
- *LLC miss rate* > 30% → *DRAM 바운드* (working set > LLC).
- *dTLB miss rate* > 1% → *huge pages 도입 검토*.

### 7.2 *Intel VTune / AMD μProf*

GUI / TUI 로 *hot function* 별 *cache miss breakdown* 까지 보여줌. *Top-Down Microarchitecture Analysis (TMA)* 메서드 를 *자동 적용* 해서 *"Frontend bound / Backend bound (memory / core) / Retiring / Bad speculation"* 4 분류 로 *bottleneck category* 를 알려줌.

### 7.3 *cachegrind (valgrind)*

```bash
valgrind --tool=cachegrind ./my-binary
cg_annotate cachegrind.out.<pid>
```

*시뮬레이션* 기반 (실제 HW counter 가 *아님*) 이라 *느리지만 *반복 가능*. *L1/LL miss 가 라인 단위로 표시*.

### 7.4 *JVM 의 *JFR (Java Flight Recorder)*

JVM 워크로드는 *순수 perf* 만 으론 *함수 매핑 이 어렵다* (JIT 코드). *JFR + async-profiler `--event=cache-misses`* 가 *Java 메서드 단위로 *cache miss 를 매핑*.

---

## 8. *완화 패턴 — *알고리즘 이 아니라 *데이터 배치*

> *"같은 알고리즘 인데 *10 배 빠르다"* — *대부분 *데이터 배치* 의 차이.

### 8.1 *Hot / Cold field separation*

```c
// Before — 자주 쓰는 state 와 가끔 쓰는 metadata 가 섞임
struct Session {
    long lastAccessNs;     // 매 요청마다 갱신 (hot)
    char username[64];     // 거의 안 읽음 (cold)
    char userAgent[256];   // 거의 안 읽음 (cold)
    int requestCount;      // 매 요청마다 갱신 (hot)
};

// After — hot 만 한 라인에 모음
struct SessionHot {
    long lastAccessNs;
    int requestCount;
    // 56 byte 안에 다 들어감
};
struct SessionCold {
    char username[64];
    char userAgent[256];
};
```

→ *hot path 의 *cache line 효율* 이 *3~5 배* 좋아진다.

### 8.2 *Padding for false sharing*

```c
struct PerCoreCounter {
    alignas(64) long count;   // 한 코어 전속 line
    char pad[64 - sizeof(long)];
};
PerCoreCounter counters[N_CORES];  // 코어 별 분리
```

### 8.3 *Loop tiling / blocking — *행렬 곱셈 예*

```c
// Before — N*N 행렬 곱셈 (cache 무관심)
for (i = 0; i < N; i++)
    for (j = 0; j < N; j++)
        for (k = 0; k < N; k++)
            C[i][j] += A[i][k] * B[k][j];   // B 가 column-major access → cache miss

// After — 32x32 블록 단위 처리 → 한 블록이 L1 에 들어감
for (ii = 0; ii < N; ii += 32)
    for (jj = 0; jj < N; jj += 32)
        for (kk = 0; kk < N; kk += 32)
            for (i = ii; i < ii+32; i++)
                for (j = jj; j < jj+32; j++)
                    for (k = kk; k < kk+32; k++)
                        C[i][j] += A[i][k] * B[k][j];
```

→ *N = 1024 일 때* *naive 대비 *5~10 배 빠름*.

### 8.4 *Software prefetch*

```c
for (Node* n = head; n; n = n->next) {
    __builtin_prefetch(n->next, 0, 0);   // 다음 노드 미리 가져옴
    process(n->data);
}
```

*pointer chasing* 도 *작업 (process) 이 *충분히 크다면* *prefetch 가 latency 를 *숨겨준다*.

### 8.5 *Huge pages 적용*

```bash
# Linux 시스템 전체
echo always > /sys/kernel/mm/transparent_hugepage/enabled

# JVM
-XX:+UseLargePages -XX:LargePageSizeInBytes=2m

# PostgreSQL
huge_pages = try
```

워크로드 메모리 > 수 GB 일 때 *TLB miss 가 *p99 latency 의 *큰 부분* 이라면 *체감 효과 즉시*.

### 8.6 *NUMA awareness*

```bash
# 컨테이너 / VM 을 *한 NUMA 노드 안에 고정*
numactl --cpunodebind=0 --membind=0 ./service

# Kubernetes
spec:
  containers:
  - name: app
    resources:
      requests:
        cpu: "8"
        memory: "16Gi"
# kubelet 설정
--cpu-manager-policy=static
--topology-manager-policy=single-numa-node
```

---

## 9. *백엔드 개발자 의 *체크리스트*

내가 *백엔드 / 데이터 엔지니어* 라면 *낮은 레벨 까지 가지 않아도* *알고 있으면 *유용한 *체크* :

1. *Hot loop 의 *작업 집합 이 *몇 KB 인가* — L1 (32KB) / L2 (1MB) / L3 (수십 MB) 의 *어느 단계* 인가.
2. *멀티스레드 카운터 / 통계* 는 *false sharing 안전 한가* — `@Contended` / `LongAdder` / `AtomicLongArray` 패딩 확인.
3. *대용량 컬렉션 traversal* 은 *array 기반 인가 *linked 기반 인가*.
4. *DTO 의 *필드 순서* 가 *hot/cold 분리 되어 있나*.
5. *NUMA 환경* 에서 *thread 와 memory 가 *같은 노드 인가*.
6. *컨테이너 limit* 이 *논리 CPU 단위 인지 *NUMA 노드 단위 인지*.
7. *p99 latency spike* 가 *GC pause 인지* *cache miss spike 인지* 구분 가능한가.

---

## 10. *결론 — *메모리 가 *연산보다 *비싸다*

> *Moore's Law 가 *연산을 *기하급수적으로 *싸게 *만들었지만*, *DRAM latency 는 *지난 20 년 *거의 그대로* 다.

*1995 년 DRAM ~100 ns*. *2026 년 DRAM ~80 ns*. *그 사이 CPU 클럭은 *100 MHz → 5 GHz* 로 *50 배* 빨라졌다.

→ *코어 사이클 비용 으로 환산하면* *DRAM 접근 은 *그 사이 *50 배 더 비싸 졌다*. *이게 *메모리 벽 의 *진짜 정체*.

> *현대 성능 튜닝 의 90% 는 *알고리즘 의 *복잡도가 *아니라* *메모리 접근 패턴 의 *캐시 친화성* 이다.

L1 / L2 / L3 의 *3 단계 완충재* 가 *왜 그렇게 생겼는지*, *어디서 *터지는지*, *어떻게 *측정 하는지* — *이 한 페이지 의 *지도 를 *머릿속에 두면*, *"왜 이 코드가 *느리지?"* 라는 질문 앞에서 *추측 대신 *측정* 으로 시작할 수 있다.

*수십 줄의 데이터 구조 재배치* 가 *수천 줄의 알고리즘 재작성* 보다 *효과적인 경우* — *그게 *물리* 다.

---

## *참고*

- John L. Hennessy, David A. Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed.
- Ulrich Drepper, *What Every Programmer Should Know About Memory* (2007) — *지금도 유효*.
- Intel® 64 and IA-32 Architectures Optimization Reference Manual.
- AMD64 Software Optimization Guide for AMD Family 19h Processors.
- Mark D. Hill, *Aspects of Cache Memory and Instruction Buffer Performance*, PhD thesis, 1987.
- Matteo Frigo et al., *Cache-Oblivious Algorithms*, FOCS 1999.
- Daniel Lemire 의 블로그 — *데이터 구조 / SIMD / cache 실험* 의 *현대적 reference*.
