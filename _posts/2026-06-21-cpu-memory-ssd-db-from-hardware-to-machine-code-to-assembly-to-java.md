---
layout: post
title: "*CPU 와 *DB* 의 *관계* — *메모리 와 *SSD* 를 *포함* 해서 *하드웨어 → 기계어 → 어셈블리 → 자바* 4 단 으로 *내려간다*"
date: 2026-06-21 19:30:00 +0900
categories: [computer-science, database, jvm, performance]
tags: [cpu, memory, ssd, dram, nvme, cache, jdbc, jvm, buffer-pool, page-cache, assembly, syscall, java]
---

> *"DB 가 *느리다"* 라고 *말하는 사람과 *"이 SELECT 가 *L3 미스 → DRAM 1 회 + SSD random read 1 회 + JIT 컴파일 안 된 ResultSet 루프* 라서 *느리다"* 라고 *말하는 사람은 *프로파일러를 *완전히 다르게 *읽는다*.
>
> *DB 한 줄 의 *결과 가 *Java 의 *Long id* 에 들어오기까지 — *CPU → L1 → L2 → L3 → DRAM → NVMe SSD → 페이지 캐시 → DB 버퍼풀 → JDBC → JIT → JVM Heap* — *최소 8 개 의 *계층* 을 *통과* 한다. 각 계층 의 *지연 시간 (latency)* 은 *수십 배 / 수천 배 / 수십만 배* 로 *불연속* 적 으로 *튄다*.
>
> 이 글은 *그 한 줄* 이 *어떻게 *흐르는지* 를 *하드웨어 → 기계어 → 어셈블리 (x86-64) → 자바 (JDBC + JIT)* 의 *4 단 추상화* 로 *내려가 *분해* 한다. *4 단* 을 *동시에 *볼 수 있게 되면 *프로파일러의 *flame graph* 도, *DB 의 *EXPLAIN ANALYZE* 도, *GC 로그* 도 *같은 *언어* 로 *읽힌다*.

---

## TL;DR

> *CPU* 는 *DB* 에 *직접 *말하지 *않는다*. CPU 가 *직접 *접근* 할 수 있는 *유일한 *것* 은 *DRAM* (그리고 *MMIO 영역에 매핑된 *디바이스 레지스터*). *SSD* 는 *CPU 가 *직접 못 *읽는다*. *DMA 가 *대신* 한다.
>
> - **하드웨어 수준**: CPU ↔ L1 ↔ L2 ↔ L3 ↔ **메모리 컨트롤러** ↔ DRAM ↔ **PCIe 루트 컴플렉스** ↔ NVMe SSD. *CPU 가 *DB 파일* 의 *바이트 를 *읽는 *유일한 경로* 는 *NVMe SSD → DMA → DRAM → CPU 캐시* 다. CPU 가 *SSD 에 *직접 LOAD* 하지 *않는다*.
> - **기계어 수준**: CPU 명령어 (MOV, LOAD/STORE) 는 *가상 주소* 만 *알고* — *물리 주소* 변환은 *MMU + TLB + 페이지 테이블* 이 한다. *디스크 I/O 는 *기계어 1 개 가 *아니라 *시스템콜 (syscall) → 커널 → 블록 디바이스 드라이버 → NVMe 큐 제출 → DMA 완료 인터럽트* 의 *수천 사이클* 의 *시퀀스*.
> - **어셈블리 수준**: x86-64 의 `mov rax, [rbx]` 한 줄 은 *L1 히트* 면 *1 ns*, *L3 히트* 면 *10 ns*, *DRAM* 이면 *80 ns*, *페이지 폴트 (디스크 까지 내려가면) NVMe* 면 *50 µs*. *불연속* 이 *60,000 배*.
> - **고급언어 (Java) 수준**: `rs.getLong("id")` 한 줄 은 *JNI 안 한다 — JDBC 드라이버 (예: HikariCP + PostgreSQL JDBC) 가 *소켓 readWire 프로토콜 파싱 → byte[] 복사 → boxing → 메서드 디스패치*. JIT 가 *컴파일* 했다면 *대부분 인라인* 된다. *안 된 상태* 면 *인터프리터 + 가상 함수 호출* 로 *수십 배* 느리다.
>
> 4 단 추상화 를 *동시에 잡으면* — *"느린 쿼리"* 가 *DB 의 *문제* 인지, *JDBC 의 *문제* 인지, *JIT 워밍업 미달* 인지, *L3 미스* 인지, *NVMe 큐 깊이 포화* 인지 *분리* 할 수 있다.

---

## 0. *왜 *4 단 추상화* 로 *내려가야 *하나*

### 0.1 *"DB 가 느리다" 라는 *진단 명* 의 *치명적 *모호성*

다음 *4 가지 *상황* 은 *모두 *동일* 한 *"DB 쿼리 10 ms"* 처럼 *보이지만 *원인* 도 *해결책* 도 *완전히 다르다*.

| 상황 | 진짜 병목 | 해결책 |
|---|---|---|
| ① 디스크 (NVMe) 에서 *콜드 페이지 100 회 random read* | SSD I/O | 인덱스 추가, 버퍼풀 확대 |
| ② 모든 페이지 *DB 버퍼풀 적중* 하지만 *CPU 캐시 미스* 가 많음 | L3 미스 (캐시 비친화 자료구조) | 로우 압축, 컬럼나 (parquet), 페이지 순회 패턴 변경 |
| ③ JDBC 드라이버 의 *문자열 변환 + boxing* | JVM / JIT 워밍업 미달 | -XX:+PrintCompilation 으로 hot path 확인, 더 오래 워밍업 |
| ④ DB 는 *1 ms* 인데 *애플리케이션 측 N+1 쿼리 100 회 → 네트워크 RTT* | 네트워크 / 클라이언트 직렬화 | JPA fetch join, 배치 fetch, native query |

*"DB 느리다"* 가 *DB 안 (스토리지/버퍼풀/플래너)* 인지 *DB 밖 (클라이언트/JIT/캐시/네트워크)* 인지 *분리* 못 하면 *몇 일 *허공* 에 *날린다*. *4 단 추상화* 가 *그 분리 의 *공통 언어* 다.

### 0.2 *지연 시간 의 *대수 *척도* — *Latency Numbers Every Programmer Should Know*

Jeff Dean 의 *유명한 표* (2010, 갱신값):

| 작업 | 지연 (ns) | DRAM 1 회 대비 |
|---|---|---|
| L1 캐시 히트 | ~1 ns | 0.013 배 |
| 분기 예측 실패 | ~3 ns | 0.04 배 |
| L2 캐시 히트 | ~4 ns | 0.05 배 |
| L3 캐시 히트 | ~10 ns | 0.13 배 |
| **DRAM 접근** | **~80 ns** | **1 배 (기준)** |
| 같은 데이터센터 내 네트워크 RTT (왕복) | ~500,000 ns (500 µs) | 6,250 배 |
| **NVMe SSD random read** | **~50,000~100,000 ns (50~100 µs)** | **600~1,250 배** |
| SATA SSD random read | ~150,000 ns (150 µs) | 1,875 배 |
| HDD random seek | ~10,000,000 ns (10 ms) | 125,000 배 |
| 다른 대륙 네트워크 RTT | ~150,000,000 ns (150 ms) | 1,875,000 배 |

> *NVMe SSD 가 *DRAM 보다 *600~1,250 배 *느리다*. *HDD 시대* (DRAM 대비 *125,000 배*) 보다는 *100 배 좋아졌지만 *여전히 *불연속*. *DB 의 *버퍼풀* 이 *왜 *존재* 하는지* 의 *직접적 *수치 적 *근거*.

### 0.3 *이 글 이 *내려가는 *4 단 *지도*

```
┌─────────────────────────────────────────────┐
│  4. 고급언어 (Java + JDBC + JVM)             │  ← rs.getLong("id")
└─────────────────────────────────────────────┘
                    ↓ JIT 컴파일
┌─────────────────────────────────────────────┐
│  3. 어셈블리 (x86-64)                        │  ← mov rax, [rbx + 8]
└─────────────────────────────────────────────┘
                    ↓ 인스트럭션 디코드
┌─────────────────────────────────────────────┐
│  2. 기계어 + OS (syscall / MMU)              │  ← LOAD / STORE / read(2)
└─────────────────────────────────────────────┘
                    ↓ 마이크로아키텍처
┌─────────────────────────────────────────────┐
│  1. 하드웨어 (CPU / 캐시 / DRAM / SSD)       │  ← L1↔L2↔L3↔메모리컨트롤러↔DRAM↔PCIe↔NVMe
└─────────────────────────────────────────────┘
```

각 *층* 은 *아래 층* 의 *세부 사항* 을 *추상화* 해서 *덮는다*. 추상화 의 *비용* 이 *각 층* 에 *얼마* 인지 — *그게 *프로파일링* 의 *진짜 *질문*.

---

## 1. *하드웨어 수준* — *CPU 가 *DB 파일 의 *바이트 까지 닿는 *물리 경로*

### 1.1 *CPU 의 *물리 구조 — *코어 / 캐시 / 메모리 컨트롤러 / I/O 다이*

현대 x86-64 CPU (Intel Xeon, AMD EPYC, Apple Silicon) 의 *내부 *물리 *블록*:

```
┌──────────────────────────────────────────────────────────┐
│                     CPU 패키지 (소켓)                      │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐         │
│  │ Core 0 │  │ Core 1 │  │ Core 2 │  │ Core 3 │  ...    │
│  │ ┌────┐ │  │ ┌────┐ │  │ ┌────┐ │  │ ┌────┐ │         │
│  │ │L1 i│ │  │ │L1 i│ │  │ │L1 i│ │  │ │L1 i│ │         │
│  │ │L1 d│ │  │ │L1 d│ │  │ │L1 d│ │  │ │L1 d│ │         │
│  │ │L2  │ │  │ │L2  │ │  │ │L2  │ │  │ │L2  │ │         │
│  │ └────┘ │  │ └────┘ │  │ └────┘ │  │ └────┘ │         │
│  └────────┘  └────────┘  └────────┘  └────────┘         │
│  ┌──────────────────────────────────────────────────┐    │
│  │              L3 캐시 (모든 코어 공유)              │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ 메모리       │  │ PCIe 루트    │  │ 캐시 일관성  │   │
│  │ 컨트롤러     │  │ 컴플렉스     │  │ 디렉터리     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────┘
       ↓                    ↓
   ┌────────┐         ┌──────────┐
   │ DRAM   │         │ NVMe SSD │
   │ (DIMM) │         │ (M.2/U.2)│
   └────────┘         └──────────┘
```

핵심:
- **L1 캐시**: *코어 *전용*, *명령어 (i) + 데이터 (d) 분리*, *32~64 KB*, *3~4 사이클* (~1 ns @ 3 GHz)
- **L2 캐시**: *코어 *전용*, *256 KB ~ 1 MB*, *12~15 사이클* (~4 ns)
- **L3 캐시**: *모든 코어 공유*, *수 MB ~ 100 MB*, *30~70 사이클* (~10 ns)
- **DRAM**: *수십 ~ 수 TB*, *80~100 ns*
- **NVMe SSD**: *수백 GB ~ 수 TB*, *50~100 µs*

> *"코어 가 *L3* 를 *공유 한다"* 는 사실 이 *멀티스레드 DB 의 *진짜 *난점*. 두 코어 가 *같은 캐시 라인* 을 *동시에 *수정* 하면 *MESI 프로토콜* 의 *coherence traffic* 으로 *L3 → 다른 코어 L1* 의 *invalidation 폭주* — 흔히 말하는 *false sharing*.

### 1.2 *메모리 컨트롤러 ↔ DRAM — *CPU 가 *직접 *접근하는 *유일한 *것*

DRAM 은 *CPU 패키지 안 의 *메모리 컨트롤러* 가 *직접 *제어* 한다. *DDR4 / DDR5* 채널, *DIMM 슬롯* 단위.

- CPU 가 `mov rax, [0x7fff_1234_5678]` 명령을 실행 → MMU 가 *가상 주소* `0x7fff_1234_5678` 을 *물리 주소* `0x0001_2345` 로 변환 → L1/L2/L3 검사 → 모두 미스 → 메모리 컨트롤러 가 *DRAM 의 *Bank/Row/Column* 를 *활성화* → *64 바이트 캐시 라인* 을 *L3 → L2 → L1 → 레지스터* 로 *끌어올림*

> *DRAM 에서 *읽혀 *오는 *최소 단위 가 *64 바이트* (캐시 라인). *8 바이트 만 *필요해도 *64 바이트 가 *함께 *올라온다*. 이게 *공간 지역성 (spatial locality)* 의 *물리 적 *근거*.

### 1.3 *SSD — *CPU 가 *직접 못 *읽는다 (DMA 가 *대신* 한다)

SSD 는 *DRAM 처럼 *CPU 의 *주소 공간* 에 *직접 매핑* 되지 *않는다*. *PCIe 버스* 너머 의 *블록 디바이스*.

CPU 가 *SSD 의 *바이트 를 *읽는 *과정*:

```
1. CPU: "이 LBA 범위 의 데이터 를 DRAM 의 이 주소 로 복사 해" 라는 명령 (NVMe Submission Queue 에 쓰기)
        ↓ (MMIO — Memory-Mapped I/O, NVMe 컨트롤러 의 BAR 영역에 기록)
2. NVMe 컨트롤러: SQ doorbell 감지, 명령 디큐
        ↓
3. NVMe 컨트롤러: NAND 플래시 에서 4 KB 페이지 읽기 (실제 latency 의 *대부분* 이 여기)
        ↓
4. NVMe 컨트롤러: PCIe 의 DMA 로 *직접 DRAM 에 64 KB 쓰기* (CPU 우회)
        ↓
5. NVMe 컨트롤러: Completion Queue 에 결과 쓰기 → MSI-X 인터럽트 발생
        ↓
6. CPU: 인터럽트 핸들러 실행 → 커널 의 페이지 캐시 / 사용자 버퍼 에 데이터 위치 알림
        ↓
7. (커널 이 깨운 프로세스가 다시 스케줄링 되어 실행 되면)
   CPU: 그 DRAM 영역 을 LOAD 로 읽음 → 캐시 히트 / 미스 의 일반 경로
```

> *CPU 는 *SSD 의 *바이트 를 *직접 *읽지 *않는다*. *DMA* 가 *DRAM 까지 *옮긴 *후* *CPU 가 *DRAM 을 *읽는다*. 그래서 "SSD 데이터를 CPU 가 보는 latency = NVMe 동작 + DRAM 1 회". *NVMe random read 50 µs 의 *대부분 (~95%)* 은 *NAND 플래시 액세스 + ECC + 컨트롤러 오버헤드*. *PCIe 전송* 자체는 *수 µs*.

### 1.4 *DB 파일 의 *물리적 *경로*

PostgreSQL `SELECT * FROM users WHERE id = 42` 한 줄 이 *디스크 까지 *닿는 경우*:

```
1. 클라이언트 → libpq (소켓) → postgres backend 프로세스 (Linux 의 user-space 프로세스)
2. backend: planner → executor → heap_getnext()
3. heap_getnext() → page id 계산 (id=42 가 들어있는 8 KB 페이지)
4. shared_buffers (PostgreSQL 자체 버퍼풀, DRAM 안) 에서 찾음
   ├── 히트: 그 DRAM 영역 LOAD → 끝 (수십 ns ~ 수 µs)
   └── 미스: 아래로 진행
5. 페이지 캐시 (Linux 커널 의 페이지 캐시, DRAM 의 또 다른 영역) 에서 찾음
   ├── 히트: 커널 → 사용자 공간 복사 (CPU 가 memcpy, ~수 µs)
   └── 미스: 아래로 진행
6. read(2) syscall → ext4/xfs → 블록 레이어 → NVMe 큐 제출 → DMA 완료 인터럽트
7. 페이지 캐시 채워짐 → 사용자 공간 복사 → shared_buffers 채워짐 → executor 계속
```

**핵심 통찰**: DB 가 *디스크에 *닿는다* 는 의미는 *DRAM 두 개 영역* (shared_buffers + 페이지 캐시) 를 *모두 미스* 한 *최악의 경우*. 그래서 *DB 튜닝 의 *제 1 원칙* 은 *"메모리에 데이터가 머물게 한다"*.

### 1.5 *왜 *DB 가 *자체 버퍼풀* 을 *가지는가 — *OS 페이지 캐시* 와 *중복* 인데*

PostgreSQL `shared_buffers`, MySQL InnoDB `innodb_buffer_pool_size`, Oracle SGA 의 buffer cache 는 *전부 *DB 가 *직접 관리* 하는 *DRAM 캐시*. *OS 가 이미 *페이지 캐시* 를 *제공 함에도* 왜?

- **세밀한 교체 정책**: DB 는 *워크로드 특성 (sequential scan vs random index probe)* 을 *안다*. OS 의 LRU 는 그걸 모른다. PostgreSQL 은 *clock-sweep + ring buffer*, MySQL 은 *midpoint LRU* — DB 워크로드 에 *최적화* 된 교체.
- **트랜잭션 일관성**: WAL 의 *fsync 시점* 을 *DB 가 직접* 제어해야 한다. OS 의 *writeback delay* 에 맡기면 *crash safety* 가 *깨진다*.
- **lock 단위**: 페이지/로우 단위 잠금 을 *DB 자체 버퍼* 안에서 *해야 효율적*.

> Oracle / SQL Server 는 한 단계 더 가서 *direct I/O* (`O_DIRECT`) 로 *OS 페이지 캐시 를 우회*. 페이지 캐시 와 buffer pool 의 *이중 복사 낭비* 를 피하기 위함. PostgreSQL 은 *OS 페이지 캐시 를 신뢰* 하는 설계 (단순함을 택함).

---

## 2. *기계어 + OS 수준* — *CPU 명령어 가 *DB 페이지 에 *닿는 *논리 경로*

### 2.1 *CPU 가 *직접 *수행 하는 *3 가지 *접근*

CPU 의 *기계어 (ISA) 가 *알고 있는 *세계* 는 다음 *3 가지* 뿐:

1. **레지스터** (`rax`, `rbx`, ...): 코어 내부, 0 사이클
2. **메모리** (`[address]` 피연산자): 캐시 → DRAM 의 *가상 주소 공간*
3. **포트 I/O / MMIO**: 디바이스 레지스터. NVMe / GPU / NIC 의 *명령 큐* 가 *MMIO 영역에 매핑*.

*디스크 의 *바이트* 는 *이 3 가지 에 *들어 있지 *않다*. CPU 는 *디스크 라는 *주소 공간* 을 *모른다*. *블록 디바이스 라는 추상화 는 *OS 의 *소프트웨어 발명품*.

### 2.2 *시스템콜 — *기계어 1 개 가 *아니라 *모드 전환*

`read(fd, buf, 4096)` 의 *기계어 *시퀀스* (Linux x86-64):

```asm
mov rdi, 3            ; fd = 3 (DB 파일)
mov rsi, buf_addr     ; buffer 주소
mov rdx, 4096         ; 길이
mov rax, 0            ; syscall 번호 (0 = read)
syscall               ; ← 여기서 CPU 가 ring 3 → ring 0 으로 전환
```

`syscall` 명령은 *기계어 1 개* 지만, 그 *효과* 는:

1. CPU 의 *권한 레벨 (CPL)* 을 *3 → 0* 으로 *변경*
2. `rcx` 에 *복귀 주소*, `r11` 에 *기존 RFLAGS* 저장
3. *MSR (LSTAR)* 에 미리 등록된 *커널 진입점* 으로 `rip` 점프
4. 이제 부터 *커널 코드* 실행 — 페이지 캐시 검색 → 미스 → 블록 디바이스 드라이버 → NVMe SQ 에 명령 제출 → 프로세스 *수면 (D-state)* → 다른 프로세스 스케줄링
5. *수십 µs 후* DMA 완료 인터럽트 → 페이지 캐시 채워짐 → 프로세스 *깨움*
6. *사용자 공간 buf 에 *memcpy* → `sysret` 로 *권한 3 으로 복귀*

> *`read` 한 줄 이 *최소 *4 번 의 *주소 공간 전환* 을 *유발* 한다. 그래서 *io_uring* 같은 *syscall 배칭 + 비동기 완료* 인터페이스 가 *Linux 5.1+* 에 도입 되어 *DB 의 *I/O 효율* 을 *수 배 끌어올린다*.

### 2.3 *MMU + TLB + 페이지 테이블 — *가상 주소 의 *번역*

CPU 가 `mov rax, [0x7fff_1234_5678]` 을 실행 할 때, *0x7fff...* 는 *가상 주소*. *물리 주소* 로 *번역* 되어야 *DRAM 에 닿는다*.

```
가상 주소 (48 bit, x86-64 standard mode)
   PML4 (9 bit) → PDPT (9 bit) → PD (9 bit) → PT (9 bit) → offset (12 bit)
        ↓
        ↓ 페이지 테이블 4 단 워크 (최대 4 회 DRAM 액세스)
        ↓
물리 주소 (52 bit) → DRAM
```

**최적화**: *TLB (Translation Lookaside Buffer)* 가 *최근 번역 결과* 를 *수십 ~ 수백 엔트리 *캐시*. *TLB 히트* 면 *0 사이클*, *미스* 면 *페이지 테이블 워크 50~100 ns* 추가.

> *DB 의 *대용량 버퍼풀* 을 *작은 페이지 (4 KB)* 로 다루면 *TLB 미스 폭주*. 그래서 *Linux Huge Pages (2 MB / 1 GB)* 가 *대형 DB 의 *튜닝 포인트*. *Oracle / MySQL / PostgreSQL* 모두 *Huge Pages 지원*.

### 2.4 *페이지 폴트 — *DRAM 미스 의 *가짜 명령*

`mov rax, [addr]` 의 *주소 가 *디스크에 *스왑* 되어 있거나 *mmap 된 파일* 의 *아직 로드 안 된 페이지* 라면, MMU 가 *Present 비트 = 0* 을 감지 → *Page Fault 예외* 발생 → 커널 진입 → 디스크 에서 페이지 로드 → 페이지 테이블 갱신 → 사용자 명령 *재실행*.

*"기계어 1 개 가 *50 µs* 걸린 셈".* 프로파일러 에서는 *그 한 명령* 이 *50,000 사이클* 처럼 *보인다*. *NVMe random read 의 *진짜 정체*.

---

## 3. *어셈블리 수준* — *x86-64 가 *DB 데이터 를 *실제로 *집어드는 *방식*

### 3.1 *예제: *PostgreSQL JDBC 가 *읽은 *Long id* 를 *Java 에서 *사용*

```java
ResultSet rs = stmt.executeQuery("SELECT id FROM users WHERE email = 'foo'");
rs.next();
long id = rs.getLong("id");  // ← 이 한 줄
```

JIT 컴파일 된 후 (HotSpot C2) *x86-64 어셈블리 의 *대략적인 *모습*:

```asm
; rs.getLong("id") 의 hot path (JIT C2 컴파일 결과 의 간략화)

; 1. ResultSet 객체 참조 가 rsi 에 들어 있음
mov     rdi, [rsi + 0x28]      ; this.fields (Field[] 배열) 로딩
mov     edx, [rsi + 0x10]      ; this.columnIndex (이미 캐시된 인덱스)
mov     rdi, [rdi + rdx*8 + 0x10]  ; fields[columnIndex] (Object[] 인덱싱)

; 2. Field 객체 안의 byte[] data 참조
mov     rax, [rdi + 0x18]      ; field.data (byte[]) 로딩
mov     ecx, [rdi + 0x20]      ; field.offset

; 3. 8 바이트 big-endian Long 디코딩
mov     rax, [rax + rcx + 0x10] ; byte[] 의 raw 데이터 8 바이트 LOAD
bswap   rax                     ; big-endian → little-endian 변환

; 4. 결과 를 호출자 의 long 변수 슬롯에 저장
mov     [rsp + 0x8], rax        ; 스택 의 id 변수 슬롯
```

이 *6 줄* 이 *L1 히트* 면 *수 ns* 안에 끝난다. *L3 미스* 면 *80 ns*. *페이지 폴트* 면 *50 µs* (60,000 배).

### 3.2 *분기 예측 (Branch Predictor)*

`rs.next()` 의 *if (cursor < rowCount)* 검사 같은 *분기*. CPU 의 *분기 예측기* 가 *맞으면 *0 사이클*, *틀리면 *파이프라인 플러시 ~15 사이클* 손실.

> *DB 에서 *조건 분기 가 *50/50 으로 *예측 불가* 한 *지점* (예: `WHERE x > ?` 의 *비균등 분포*) 이 *모던 DB 의 *SIMD 화* 와 *branchless 코드* 의 *동기*. *DuckDB / Velox* 같은 *컬럼나 엔진* 이 *전부 branchless + SIMD*.

### 3.3 *캐시 라인 정렬 (Cache Line Alignment)*

64 바이트 캐시 라인 *경계* 에 *걸친 *데이터 *접근 은 *2 회 캐시 로드*. PostgreSQL 의 *Tuple 헤더* 가 *24 바이트* + *NULL bitmap* 등 으로 *비정렬*. *그래서 *컬럼나 DBMS* 가 *행 단위 DBMS 보다 *분석 쿼리* 에서 *10~100 배* 빠르다 — *캐시 라인 효율*.

---

## 4. *고급언어 (Java) 수준* — *JDBC + JIT + JVM* 의 *실제 동작*

### 4.1 *JDBC 의 *진짜 *계층*

```
┌─────────────────────────────────────────────┐
│  Spring Data JPA / MyBatis 등 (선택적)       │
└─────────────────────────────────────────────┘
                    ↓ JDBC API
┌─────────────────────────────────────────────┐
│  HikariCP (커넥션 풀)                        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  PostgreSQL JDBC Driver (pgjdbc)             │
│  - protocol parser (V3)                      │
│  - byte[] ↔ Object 변환                      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  java.net.Socket (TCP)                       │
└─────────────────────────────────────────────┘
                    ↓ syscall
┌─────────────────────────────────────────────┐
│  Linux 커널 (TCP stack, ext4, NVMe)          │
└─────────────────────────────────────────────┘
```

### 4.2 *PostgreSQL Wire Protocol — *바이트 가 *Java 에 *들어오는 *형태*

PostgreSQL 서버는 *FE/BE Protocol V3* 로 *응답*. `SELECT id FROM users` 의 *한 행* 의 *Wire 형식*:

```
DataRow (1 byte 'D')   - 메시지 타입
Length (4 byte)        - 메시지 길이
FieldCount (2 byte)    - 컬럼 수
[FieldLength (4 byte) + FieldData (N byte)] × FieldCount
```

PostgreSQL JDBC Driver 는:

1. *TCP 소켓 에서 `InputStream.read(byte[])`* → 커널 버퍼 → 사용자 버퍼 (memcpy 1 회)
2. `byte[]` 안에서 *'D'* 메시지 파싱 → `byte[]` 슬라이스
3. `getLong("id")` 호출 시 *그 슬라이스 를 *big-endian Long* 으로 *디코딩*

> *"DB 의 한 행이 *Java Long 으로 *변환* 되는 *오버헤드 가 *얼마인가"* 의 *답* 은 *대체로 *Long 1 개 당 *수십 ns + 일부 GC 압박*. *대량 *SELECT (수십만 행)* 에서는 이게 *prepared statement 자체 시간* 을 *능가* 한다.

### 4.3 *Heap / Direct ByteBuffer — *DB 데이터 가 *JVM 에 *머무는 *형태*

`byte[]` 가 *JVM Heap 안* 에 있으면 *GC 의 대상*. 큰 *ResultSet 을 *전부 *Heap 에 적재* 하면 *Young GC 폭주*.

대안:
- **Direct ByteBuffer** (`ByteBuffer.allocateDirect`): *Heap 외부 (OS 가 관리하는 native 메모리)*, *GC 영향 X*, 하지만 *Heap ↔ Direct 복사 1 회 필요*.
- **MappedByteBuffer** (`FileChannel.map`): *파일을 *직접 가상 메모리 매핑* → *페이지 폴트 가 *알아서 디스크 로드*. *임베디드 DB (RocksDB, LMDB)* 의 *기본 전략*.

> *대용량 결과 셋 *처리* 는 *Heap 우회* 가 *필수*. JDBC 의 `setFetchSize()` 로 *서버 측 커서* 를 사용하면 *전체 결과 를 한 번에 로드하지 않고* *N 행 씩 가져옴*.

### 4.4 *JIT 컴파일 — *워밍업 의 *진짜 의미*

HotSpot JVM 은 *처음 *수천 회* 까지는 *인터프리터 (template interpreter)* 로 *실행*. *Hot method* 로 판정 (보통 `-XX:CompileThreshold=10000`) 되면 *C1 컴파일러* → 더 뜨거우면 *C2 컴파일러*.

`rs.getLong("id")` 한 줄 의 *비용*:

| 상태 | 비용 (CPU 사이클) | 비고 |
|---|---|---|
| 인터프리터 | ~500~1000 사이클 | 가상 함수 디스패치 + 바이트코드 해석 |
| C1 컴파일 | ~50~100 사이클 | 단순 컴파일 |
| C2 컴파일 + 인라인 | ~10~30 사이클 | escape analysis, loop unrolling, dead code 제거 |

> *벤치마크 워밍업 의 *진짜 동기* — *처음 10,000 회 의 *측정값* 은 *인터프리터 비용 이 *섞여* 있어 *프로덕션 의 *진짜 hot path 성능* 을 *반영 못 한다*. JMH 의 `@Warmup` 어노테이션 이 *그 이유*.

### 4.5 *GC 와 *쿼리 지연*

`SELECT * FROM users` 가 *수만 행* 을 *Object[] 배열* 로 받아 오면:

- Object 헤더 16 바이트 × N
- Field 객체 N 개 × 컬럼 수
- byte[] 인스턴스 N 개

*수십 MB ~ 수백 MB 의 *Young 영역 객체*. *Young GC 발생* → *Stop-the-world 5~50 ms* → *쿼리 100 ms 인데 GC 가 30 ms 차지* 같은 *패턴*.

> *그래서 *Streaming ResultSet* + *MyBatis ResultHandler* + *JDBC setFetchSize()* 가 *대용량 결과 처리* 의 *표준 패턴*. *전체 결과 셋 을 한 번에 List<User> 에 담는 *나쁜 패턴* 은 *프로파일러 에서 *GC pause 폭주* 로 *나타난다*.

---

## 5. *전체 *그림* — *한 쿼리 가 *닿는 *길*

```
Java 애플리케이션
   ↓ stmt.executeQuery("SELECT id FROM users WHERE email = 'foo'")
HikariCP (커넥션 풀 — 미리 만들어 둔 Socket 재사용)
   ↓
pgjdbc (Wire Protocol V3 직렬화: 'Q' message + SQL bytes)
   ↓
java.net.Socket.getOutputStream().write(byte[])
   ↓ syscall write(2)
Linux 커널 TCP stack → NIC → 네트워크 → DB 서버

[DB 서버 측]
   PostgreSQL backend 프로세스 (사용자가 만든 SELECT 하나당 1 프로세스)
   ↓
   Parser → Planner → Executor
   ↓ heap_getnext()
   shared_buffers (DRAM, PostgreSQL 자체 버퍼풀) 검색
   ├── 히트: 그대로 진행 (수 µs)
   └── 미스:
       └── Linux 페이지 캐시 (DRAM, 커널 영역) 검색
           ├── 히트: 사용자 공간 복사 (수 µs)
           └── 미스: read(2) syscall
               └── NVMe SQ 에 명령 제출 → DMA → 50 µs 후 깨움
   ↓
   결과 행 → Wire Protocol 'D' message 직렬화 → 소켓 write

[애플리케이션 측]
   소켓 read → byte[] 채워짐
   ↓
   pgjdbc 파싱 → Field[] 생성
   ↓
   rs.next() → 행 인덱스 +1
   ↓
   rs.getLong("id") → byte[] 슬라이스 → big-endian Long 변환
       ↓ (JIT C2 컴파일 후) — L1 히트 면 수 ns, 미스면 수십~수백 ns
   ↓
   호출자 의 long id 변수 에 저장
```

### 5.1 *어디서 *얼마 *걸리는가 — *전형적인 *분포*

`SELECT id FROM users WHERE email = ?` *한 줄* 의 *지연 시간 분해* (인덱스 있음, warm cache 가정):

| 단계 | 일반적 비용 | DB 가 핫인 경우 | DB 가 콜드인 경우 |
|---|---|---|---|
| Java → JDBC 직렬화 | ~10 µs | ~10 µs | ~10 µs |
| 네트워크 RTT (같은 데이터센터) | ~200 µs | ~200 µs | ~200 µs |
| DB 파싱 + 플래닝 (prepared statement 면 ~10 µs) | ~50 µs | ~10 µs | ~10 µs |
| DB 실행 + 페이지 접근 | ~5 µs | ~5 µs (메모리 히트) | ~100 µs (디스크 미스) |
| 응답 직렬화 | ~10 µs | ~10 µs | ~10 µs |
| JDBC 역직렬화 + JIT 핫 패스 | ~10 µs | ~10 µs | ~10 µs |
| **합계** | **~285 µs** | **~245 µs** | **~340 µs** |

> *네트워크 RTT 가 *대부분*. 그래서 *PgBouncer / 같은 서버 콜로케이션 / Unix socket* 같은 *RTT 감소 기법* 의 *효과 가 크다*. *NVMe 시대* 의 *DB 튜닝* 은 *디스크 가 *아니라 *네트워크 + 클라이언트* 가 *주 무대*.

### 5.2 *4 단 추상화 의 *교차 지점 — *프로파일링 의 *진짜 *언어*

| 증상 | 4 단 중 어디 | 원인 후보 |
|---|---|---|
| 모든 쿼리가 갑자기 100 µs → 1 ms | 하드웨어 | NVMe 큐 깊이 포화 (`iostat -x` 의 *avgqu-sz*), DRAM ECC 오류 |
| 특정 컬럼 SELECT 만 느림 | 어셈블리 / 하드웨어 | TOAST out-of-line 저장 → 추가 페이지 fetch |
| 워밍업 후 5 분 동안 만 느림 | Java 고급 | JIT 컴파일 진행 중 (-XX:+PrintCompilation 으로 확인) |
| 50 ms 마다 100 ms 의 latency spike | Java 고급 | Young GC, *jstat -gcutil* 로 확인 |
| 50 µs 마다 5 µs spike | 기계어 / 하드웨어 | TLB miss, perf c2c 로 false sharing 확인 |
| EXPLAIN ANALYZE 는 빠른데 클라이언트 는 느림 | 네트워크 / Java | RTT, JDBC fetchSize 미설정 |

---

## 6. *정리

### 6.1 *4 단 의 *역할 분리*

| 추상화 층 | 보는 것 | 도구 |
|---|---|---|
| **하드웨어** | 캐시 미스, DRAM 대역폭, NVMe 큐 | `perf stat`, `iostat -x`, `dstat`, `intel-pmu-tools` |
| **기계어 + OS** | syscall 빈도, 페이지 폴트, TLB 미스 | `strace -c`, `perf trace`, `/proc/<pid>/status`, `bpftrace` |
| **어셈블리** | hot loop 의 명령어 분포, 분기 예측 실패 | `perf record + perf annotate`, JITWatch (JVM), `objdump` |
| **고급언어 (Java)** | JIT 진행, GC pause, JDBC 호출 분포 | JFR, async-profiler, JMC, `-XX:+PrintCompilation`, p6spy/datasource-proxy |

### 6.2 *시니어 가 *EXPLAIN ANALYZE* 를 *읽는 *방식*

```
Index Scan using users_email_idx on users  (cost=0.42..8.45 rows=1 width=8)
  (actual time=0.025..0.026 rows=1 loops=1)
  Index Cond: (email = 'foo'::text)
  Buffers: shared hit=4
Planning Time: 0.123 ms
Execution Time: 0.045 ms
```

*초보* : `Execution Time: 0.045 ms` 만 본다.
*시니어* : `Buffers: shared hit=4` 를 본다 → "4 페이지 × 8 KB = 32 KB, 전부 DRAM 안 의 shared_buffers 에 있었음. 디스크 0 회. 그런데 클라이언트 측 latency 는 5 ms" → "네트워크 + JDBC 가 100 배" → 클라이언트 측 프로파일러 켠다.

### 6.3 *마지막 *한 마디

> *DB 가 *느리다* 는 *진단명* 은 *4 단 추상화* 중 *어디서 느린지* 를 *말하지 *못한다*. *CPU 가 *DB 의 *바이트 에 *닿는 *물리 경로* 가 *L1 → L2 → L3 → DRAM (shared_buffers / 페이지 캐시) → DMA → NVMe → NAND* 의 *7 단 메모리 계층* 이고, 그 위를 *기계어 (LOAD/STORE/syscall) → 어셈블리 (분기 예측 / 캐시 라인) → 자바 (JIT / GC / JDBC 직렬화)* 가 *덮고 있다* 는 *그림* 을 *동시에 *볼 수 있을 때 — *프로파일러 의 *flame graph* 와 *EXPLAIN ANALYZE* 와 *jstat -gcutil* 이 *같은 *언어* 로 *읽힌다*.
>
> *CPU 는 *SSD 에 *직접 *말하지 *못한다*. *DRAM 만 *직접 안다*. *그 사이* 의 *모든 추상화 — *버퍼풀 / 페이지 캐시 / DMA / NVMe 큐 / TCP / JDBC / JIT — 가 *DB 라는 *경험* 을 *만든다*. *어느 하나 가 *깨지면 *전체 가 *느리다*. *어디서 깨졌는지* 를 *읽을 수 있게 되는 것* 이 *진짜 의 *DB 튜닝 능력*.
