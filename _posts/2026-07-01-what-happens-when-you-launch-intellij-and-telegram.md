---
layout: post
title: "IntelliJ 실행 (데스크탑) 과 Telegram 실행 (모바일) — CPU / Memory / SSD / Ethernet 의 *실 과정 추적*"
date: 2026-07-01 15:30:00 +0900
categories: [systems, cpu, memory, storage, network]
tags: [intellij, telegram, jvm, android, art, ssd, nvme, lpddr5, ufs, tls, mtproto, zygote]
---

*"IntelliJ 를 더블 클릭 하면 *무엇 이 일어나는가?"* — 프론트/백엔드 개발자가 *매일 반복* 하지만 *실제 로 *무엇 이 벌어지는지* 는 잘 모름. 이 글은 *데스크탑 (IntelliJ) + 모바일 (Telegram)* 의 *실행 순간* 을 *하드웨어 (CPU / Memory / SSD / Wi-Fi/이더넷)* 관점 에서 *시간 축* 으로 *추적*.

두 시나리오 는 *같은 문제 (앱 실행)* 지만 *완전 히 다른 최적화 를 함*. *데스크탑 = 성능 우선*, *모바일 = 전력 + 냉각 우선*. 이 차이 가 *CPU 아키텍처 / 메모리 계층 / 저장 매체 / 네트워크* 의 *모든 결정* 에 반영.

---

## Part 1 — IntelliJ 실행 (데스크탑, macOS / Linux 기준)

### 시나리오
개발자 가 *Dock 의 IntelliJ 아이콘* 을 클릭. *0 초 부터 *스플래시 화면 사라지기* (약 5~10 초) 까지 의 *5 phase*.

---

### Phase 1 — *0 ~ 100 ms*: OS 의 *프로세스 생성*

**사용자 액션** → *WindowServer / Finder* 이 *`launch com.jetbrains.intellij`* 시스템 콜 발행 → *macOS 의 `launchd`* 가 *`posix_spawn()`* 호출 (Linux 면 `fork() + exec()`).

**CPU** — *커널 모드 (Ring 0)* 로 진입. *system call 처리*:
1. **process descriptor 생성** — `task_struct` (Linux) / `proc_struct` (macOS) 할당
2. **가상 메모리 공간 할당** — *48-bit 가상 주소 공간* 의 *새 매핑*. 실제 RAM 할당 은 *lazy* — page fault 시점.
3. **file descriptor 테이블 초기화** — stdin/stdout/stderr 만 열림 (0, 1, 2)
4. **kernel scheduler** 에 *new task 등록* → *runqueue 삽입*
5. *`execve()` 호출* — *ELF (Linux) / Mach-O (macOS)* 헤더 읽기

**SSD** — *0 접근*. 아직 파일 안 읽음.

**Memory** — *kernel 의 slab allocator* 에서 *수 KB 할당* (task_struct 등)

**Ethernet** — *0 접근*. 아직 네트워크 무관.

---

### Phase 2 — *100 ~ 800 ms*: JVM 부트스트랩 + IntelliJ launcher

**CPU 는 다시 *userland (Ring 3)*** 로 복귀. *`idea` shell script* 실행 → `/usr/bin/java` 실행 → *JVM 부팅*.

**SSD 의 *진짜 부하* 시작**:
- *JVM 실행 파일* (`java` 바이너리, ~15 MB) — **NVMe controller** 가 *PCIe 4.0 x4* 로 *~7 GB/s bandwidth* 사용 가능. 실 파일 은 *KB 단위 random read*.
- *libjvm.so* / *libjava.so* / *libjli.so* — *약 40 MB* 총 shared library
- *IntelliJ 의 *JAR 파일 수백 개* — `~/Applications/IntelliJ IDEA.app/Contents/lib/*.jar` — *약 500 MB, 200~300 파일*
- **NVMe 의 마법** — *SATA SSD 의 *550 MB/s* 대비 *~10 배*. *NVMe queue depth 64+ (SATA 는 32)* — *동시 다중 요청* 이 *실 속도 의 핵심*
- *Page cache 활용* — *이미 읽은 파일 은 *RAM 에 있음* → *2 번 째 실행 부터 는 *SSD 접근 안 함* (macOS 의 *Unified Buffer Cache*, Linux 의 *Page Cache*)

**Memory 의 *3 계층*** 흐름:
```
SSD (NAND flash)  →  DRAM (page cache) →  L3 →  L2 →  L1 →  CPU register
   ~50 μs             ~100 ns             ~10 ns  ~3 ns  ~1 ns  <1 ns
```
- *IntelliJ 의 *JAR 파일 * 이 *page cache 에 로드* — *한 번 만* NAND 접근
- *CPU 가 *실제 처리 는 *L1/L2 캐시* 에서
- *처음 실행* — *cold cache* → *cache miss 폭증* → *느림*
- *2 번 째 실행* — *warm cache* → *훨씬 빠름* (macOS/Linux 의 *first launch vs subsequent launch* 의 *체감 차이*)

**CPU 의 *역할*** — JVM 부팅 시:
1. **Bootstrap ClassLoader** — *java.lang.\**, *java.util.\**, *java.io.\** 클래스 를 *rt.jar (Java 8) 또는 *jimage (Java 9+ modules)* 에서 로드
2. **JIT compiler 초기화** — *C1 (client compiler, 빠른 컴파일)* + *C2 (server compiler, 최적화 강함)* 준비. 아직 컴파일 안 함 — *메소드 호출 횟수 카운팅 만*
3. **Metaspace 초기화** — Java 8+ 의 *class metadata 영역* (PermGen 대체). *native memory* 에 위치
4. **Heap 초기화** — `-Xms2g` 옵션 이면 *가상 메모리 2GB reserve* + *처음 512MB 만 commit*

**Ethernet** — *아직 0*.

---

### Phase 3 — *800 ~ 2500 ms*: IntelliJ 의 *main() 실행 + UI init*

**CPU** — *`com.intellij.idea.Main.main()`* 실행 → *Swing UI thread (EDT)* 시작.

**Memory 의 *진짜 사용* 시작**:
- *IntelliJ platform 코드* — *약 3000 개 클래스* JIT interpret + class 별 몇 KB metadata 를 Metaspace 에
- *플러그인 로드* — *~200 개 플러그인* (Java, Kotlin, Git, Docker, DB Navigator...) 각각 *ClassLoader 격리*. 이게 *IntelliJ 의 *느린 이유* 의 하나.
- *IntelliJ 의 *캐시 파일* 로드 — `~/Library/Caches/JetBrains/IntelliJIdea2026.1/*` 에 *과거 프로젝트 index / recent files / plugin state* 저장. *~500 MB 급*.

**SSD** — *2 번 째 파도* — *cache 파일 + plugin JAR + font 리소스* 읽기.

**CPU 의 *멀티 코어 활용***:
- **UI thread (EDT)** — *Prime core (예: Apple M2 Pro 의 Performance core, ~3.5 GHz)* 에 스케줄
- **background 작업** (index worker, plugin init) — *Efficiency core* 에 분산
- **JIT compilation** — *별도 thread* 에서 *hot method 감지 시 background compile*
- **GC** — *G1GC 의 concurrent phase 는 백그라운드*, *STW phase 는 mutator 중단*

**JIT 의 *실 작동***:
1. *메소드 호출 횟수 감지* — *interpreter counter*
2. *임계 값* (default 10000) 도달 → *C1 compile* — *빠른 컴파일 + 중간 최적화*
3. *더 자주 호출* → *C2 compile* — *aggressive inlining + escape analysis + vectorization*
4. *컴파일 결과 는 *code cache* (JVM 내 별도 영역) 에 저장
5. *2 번 째 실행 부터 는 *AppCDS (Application Class-Data Sharing)* — *컴파일 된 클래스 를 *다음 실행 에 재사용* → *시작 시간 30~50% 단축*

**Ethernet** — *처음 신호*:
- *JetBrains 계정 서버* (`account.jetbrains.com`) 에 *라이센스 검증* GET 요청
- *플러그인 update check* (`plugins.jetbrains.com`) — *마지막 check 이후 24h 지났으면*
- **네트워크 스택 의 흐름**:
  ```
  App (Java Socket) → JVM Native → OS TCP/IP stack
     → NIC driver (e.g., Broadcom BCM4364)
     → Ethernet PHY (physical layer)
     → 케이블 / Wi-Fi radio
  ```
- **TCP handshake** — SYN → SYN-ACK → ACK (*~30ms if server nearby*)
- **TLS 1.3 handshake** — *0-RTT 가 가능 하면 *0 ms, 아니면 1-RTT (~30ms)*
- **HTTP/2 GET** — *response ~5 KB*

---

### Phase 4 — *2500 ~ 5000 ms*: 프로젝트 로드 + 인덱싱 시작

**사용자 액션** — 프로젝트 창 클릭 → IntelliJ 가 *`.idea/` 폴더* 읽기.

**SSD** — *3 번 째 파도* (가장 큼) — *소스 코드 파일 수천~수만 개*:
- *.java, .kt, .xml, .yml* 등 *실제 프로젝트 파일*
- *build/, target/* 의 *컴파일 산출물*
- *~/.gradle/caches/* 또는 *~/.m2/repository/* 의 *의존성 JAR 들* (수 GB)

**Memory** — *IntelliJ 의 *heap 급증*:
- *PSI Tree (Program Structure Interface)* — *모든 소스 파일 의 *AST* 를 heap 에
- *Symbol table* — *클래스 / 메소드 / 필드* 의 인덱스
- *File type detection* — *bytes 기반 heuristic*
- *heap 사용 량 이 *1~4 GB 급* 도달 가능 — *`-Xmx8g` 권장 이 여기 서 나옴*

**CPU** — *인덱서 가 *멀티 스레드* 로 *병렬 처리*:
- *하드웨어 스레드 수 만큼* worker
- *각 파일* 마다 *lexer → parser → PSI 생성 → 인덱스 항목 추가*
- *SSD IOPS 가 병목* 인 경우 흔함 (특히 *많은 작은 파일*)

**Ethernet** — *Maven Central / JetBrains repository / GitHub* 등 *의존성 resolve 시 활발*. 이미 있으면 skip.

---

### Phase 5 — *5000 ms +*: 정상 상태 (idle)

**IntelliJ 창 이 보임**. 사용자 가 코딩 시작 전.

**CPU** — *idle 근처*. *plugin 의 timer callback*, *auto-save timer*, *editor caret blink* 정도. *~1~3% 사용*.

**Memory** — *정착*. *3~6 GB 사용*. *GC 는 *가끔 minor GC*.

**SSD** — *idle*. *가끔 auto-save, indexing update*.

**Ethernet** — *idle*. *plugin update check 등 백그라운드 폴링만*.

### *요약 표*

| Phase | 시간 | CPU | Memory | SSD | Ethernet |
|---|---|---|---|---|---|
| 1. Process create | 0~100ms | Ring 0 syscall | 수 KB (kernel) | 0 | 0 |
| 2. JVM boot | 100~800ms | JVM init | ~500MB (heap+meta) | *500MB read* | 0 |
| 3. IntelliJ main | 800~2500ms | *4 core burst* | *1~2GB* | *cache/plugin* | *TLS handshake* |
| 4. Project index | 2500~5000ms | *8 core parallel* | *2~4GB PSI* | *수천 파일* | *deps* |
| 5. Idle | 5000ms+ | ~1~3% | 3~6GB 정착 | idle | polling |

---

## Part 2 — Telegram 앱 실행 (모바일, Android + iPhone 참고)

### 시나리오
사용자 가 *홈스크린 의 Telegram 아이콘 탭*. *0 초 부터 *채팅 목록 표시* (약 500 ms ~ 2 초) 까지.

**모바일 은 *데스크탑 과 완전 히 다른 최적화***:
- **CPU** — big.LITTLE (Prime + Performance + Efficient) 의 *비대칭 코어*
- **저장** — eMMC (구형) 또는 *UFS 3.1 / 4.0* (신형). *SSD 보다 훨씬 느림 (UFS 3.1 이 read ~2 GB/s)*
- **메모리** — *LPDDR5* — *데스크탑 DDR5 의 *저전력 버전*
- **네트워크** — Wi-Fi + LTE/5G *동시 전환*
- **프로세스 모델** — *Android 의 Zygote fork* — *데스크탑 의 fork+exec 와 다름*

---

### Phase 1 — *0 ~ 50 ms*: launcher → SystemServer 요청

**사용자 액션** → *Launcher 앱* 이 *`ActivityManagerService`* 에 *"Telegram 시작"* IPC.

**Android 만 의 *Zygote 마법*** — *데스크탑 의 fork+exec 와 다름*:

```
Android 부팅 시:
1. init 프로세스 시작 (PID 1)
2. Zygote 프로세스 시작 — Android Runtime (ART) + 모든 프레임워크 클래스 미리 로드
3. Zygote 가 *fork()* 대기

앱 실행 시:
1. ActivityManagerService → Zygote 에 fork 요청
2. Zygote 가 *fork()* → 자식 프로세스 = *새 앱*
3. 자식 은 *이미 ART + framework 클래스 를 상속* (COW — Copy On Write)
4. 자식 이 *`ActivityThread.main()`* 진입 → app 코드 실행
```

**이점** — *ART 초기화 + framework 클래스 로드 를 *한 번 만* 함. *데스크탑 의 *JVM 매번 부팅 하는 5 초* 를 *~50 ms 로 절감*. **모바일 이 *느린 하드웨어 로 빠른 이유*.

**CPU** — *커널 의 fork syscall*. *Prime core (예: Cortex-X4 3.4 GHz)* 에 스케줄.

**Memory** — *COW (Copy On Write) 페이지 매핑*. *실제 복사 는 write 시*.

**Storage** — *0 접근*. Zygote 가 이미 로드 됨.

**Wireless** — *0*.

---

### Phase 2 — *50 ~ 200 ms*: 앱 프로세스 초기화

**CPU** — Telegram 의 `Application.onCreate()` 호출:
1. *`Application` 서브클래스* 초기화 (`TelegramApplication`)
2. *SharedPreferences / SQLite DB* 열기 — *로컬 캐시된 채팅 목록*
3. *native libraries* (`libtmessages.so` — MTProto C 구현체) 로드 — `System.loadLibrary()`
4. *AndroidX / Retrofit / OkHttp / Coil* 등 *라이브러리* 클래스 로드

**Memory (LPDDR5)** — *~500 MB/s per channel × 4 channel = 2 GB/s* (데스크탑 DDR5 의 *1/5*):
- Telegram 앱 heap — *~100~300 MB*
- native memory (libtmessages) — *~50 MB*
- graphics memory (Vulkan / OpenGL) — *~100 MB*

**Storage (UFS)** — *DEX / DEX2OAT 컴파일 산출물* 읽기:
- *Android 는 *ART (Android Runtime)* — *AOT 컴파일 + JIT + interpreter 의 hybrid*
- *앱 설치 시* dex2oat 로 *ARM machine code 생성* → *.odex, .vdex* 파일 → *실행 시 그냥 로드*
- *데스크탑 의 *JVM JIT 대비* — *시작 즉시 컴파일 된 코드*
- **UFS 4.0** — 순차 read ~4 GB/s (여전히 NVMe 의 절반)

**Wireless** — *radio wake*:
- *Wi-Fi 는 *deep sleep* 에서 *active* 로 (~50~200 ms)
- *LTE/5G 는 *idle 상태 (RRC IDLE)* → *connected (RRC CONNECTED)* 로 전환

---

### Phase 3 — *200 ~ 500 ms*: UI thread 시작 + MTProto 서버 연결

**CPU** — *UI thread 가 `MainActivity.onCreate()` 실행*. *Compose / View* 트리 build.

**Wireless 의 *진짜 부하*** — Telegram 의 *MTProto 프로토콜*:
```
Telegram Client
   ↓ TLS 1.3 handshake (~1-RTT, ~50 ms Wi-Fi / ~100 ms 5G)
Telegram DC (Data Center, 5 개 지역 배치)
   ↓ MTProto authorization (AES-256, Diffie-Hellman)
   ↓ HTTP-like binary protocol
   ↓ 지속 연결 (long-poll + push)
```

- **DNS resolve** — `venus.web.telegram.org` 또는 direct IP (Telegram 은 *DC 별 hardcoded IP list* — DNS 검열 우회)
- **TLS 1.3** — 대부분 *0-RTT* 로 *즉시 데이터 전송* 가능 (재접속 시 캐시 된 session key 사용)
- **MTProto auth_key** — 이미 있으면 *즉시 재사용*, 없으면 *DH 교환 1 RTT*
- **최근 메시지 fetch** — `GetHistory` RPC

**Push notification 채널** — *별개 layer*:
- Android — **Firebase Cloud Messaging (FCM)** 이 이미 백그라운드 로 유지 (앱 안 켜져 있어도)
- iOS — **APNs (Apple Push Notification service)**
- Telegram 은 *알림 페이로드 최소화* — *"메시지 왔음"* 만 전송, *실제 내용 은 앱 이 켜지면 fetch*

---

### Phase 4 — *500 ~ 1500 ms*: 채팅 목록 렌더링

**CPU** — big.LITTLE 의 *분업*:
- **Prime core (Cortex-X4)** — UI thread + Compose render
- **Performance core (A720)** — 이미지 decode (WebP → RGB) — *NEON SIMD* 활용
- **Efficient core (A520)** — 백그라운드 sync, DB read

**GPU** — 채팅 리스트 스크롤 = *Adreno 750 / Mali G720* 가 *60 Hz ~ 120 Hz 렌더링*
- Frame 마다 *16.6 ms (60 Hz) / 8.3 ms (120 Hz)* 이내 완료 필수
- *dropped frame* = *jank 감지*

**Memory** — *채팅 목록 의 *thumbnail 이미지* 를 *메모리 캐시*. 
- *L1 cache — 최근 스크롤 된 이미지 즉시 접근*
- *disk cache — UFS 의 파일 로*

**Wireless** — *WebSocket 유지* — *지속 연결*. *긴 메시지 는 청크 단위*.

---

### Phase 5 — *1500 ms +*: 정상 상태 (idle)

**CPU** — *Efficient core 만 동작*. *Prime core sleep*.

**Radio** — *DTX (Discontinuous Transmission)* 모드 — *간헐 적 keep-alive ping 만*.

**Battery** — *~50~100 mW 사용* (전화 통화 대비 *1/10*).

### *요약 표*

| Phase | 시간 | CPU (big.LITTLE) | Memory (LPDDR5) | UFS Storage | Wireless |
|---|---|---|---|---|---|
| 1. Zygote fork | 0~50ms | Prime core (커널) | *COW 매핑 만* | 0 | 0 |
| 2. App init | 50~200ms | Prime + Performance | ~200MB | *.odex/.vdex read* | *radio wake* |
| 3. MTProto | 200~500ms | Prime (crypto) | ~300MB | 최근 채팅 DB | *TLS + auth* |
| 4. UI render | 500~1500ms | *3 코어 분업* | ~400MB | 이미지 캐시 | WebSocket |
| 5. Idle | 1500ms+ | Efficient core | 정착 | idle | DTX / keep-alive |

---

## Part 3 — *데스크탑 vs 모바일* 의 *3 축 차이*

### 축 1 — *전력 / 냉각*

| 측면 | 데스크탑 (IntelliJ) | 모바일 (Telegram) |
|---|---|---|
| CPU 소비 전력 | 45~125 W (i9 / Ryzen) | **5~15 W** (Snapdragon 8 Gen 3) |
| 냉각 | 팬 + 히트파이프 + 케이스 airflow | *수동 방열판 만*. thermal throttling *즉각* |
| 부하 시 동작 | 몇 시간 max 부하 유지 가능 | *~30 초* 만에 *core clock 강제 하락* |
| 배터리 | AC power 무제한 | *3000~5000 mAh* |

**함의**:
- 모바일 CPU 는 *"짧은 시간 만 빠르게 + 대부분 시간 은 절전"* 이 *제 1 원칙*
- IntelliJ 의 *5 초 부팅 + 지속 인덱싱* 은 *모바일 에서 불가능*
- Telegram 의 *Zygote pre-fork* 는 *전력 절감* 의 *핵심 전략*

### 축 2 — *네트워크*

| 측면 | 데스크탑 (IntelliJ) | 모바일 (Telegram) |
|---|---|---|
| 네트워크 | 유선 이더넷 or Wi-Fi (안정) | *Wi-Fi ↔ LTE ↔ 5G 전환* |
| latency | 안정 5~30 ms | *변동 큼 20~200 ms* |
| bandwidth | 100 Mbps ~ 10 Gbps | *가변 5~500 Mbps* |
| interruption | 드묾 | *지하철 터널 등 * 자주 * 끊김 |

**함의**:
- Telegram 은 *짧은 disconnect 를 *자동 recovery* — MTProto 의 *session key 유지 + reconnect 즉시*
- IntelliJ 는 *offline 도 대부분 작동* — 로컬 캐시 위주
- 모바일 앱 은 *offline-first 설계 의무*

### 축 3 — *프로세스 모델*

| 측면 | 데스크탑 (IntelliJ) | 모바일 (Telegram) |
|---|---|---|
| process 생성 | *fork + exec* (매번 JVM 로드) | *Zygote fork* (framework 상속) |
| 시작 시간 | *5~10 초* | *0.5~2 초* |
| 프로세스 수명 | 사용자 종료 시 까지 | *언제든 OS 가 kill 가능* |
| 상태 관리 | *메모리 에 유지* | *`onSaveInstanceState` 로 serialize 의무* |

**함의**:
- 모바일 앱 은 *언제든 kill / restart 될 준비* — *state 를 *디스크 에 자주 flush*
- 데스크탑 앱 은 *메모리 에 자유롭게 유지*
- *같은 "실행"* 이라도 *모바일 은 *더 복잡 한 라이프사이클*

---

## Part 4 — *공통 원리* — *4 계층 의 *같은 여정*

시간축 이 다르지만 *데이터 는 항상 같은 계층* 을 흐름:

```
Storage (SSD / UFS)
      ↓ page fault or explicit read
DRAM (Page Cache → Heap)
      ↓ virtual memory translation (TLB)
CPU Cache (L3 → L2 → L1)
      ↓ single cycle load
CPU Register
      ↓ ALU
계산 결과
      ↓
Network (Ethernet / Wi-Fi radio)
      ↓ NIC DMA
DRAM (Socket buffer)
      ↓ syscall
Application
```

**핵심 병목**:
- **Storage → DRAM** — *ms 급*. *cache 활용 도* 가 *체감 성능 의 90%*
- **DRAM → CPU Cache** — *ns 급*. *cache miss 최소화* 가 *hot path 의 승부처*
- **CPU Cache → Register** — *cycle 급*. *branch prediction / SIMD* 가 *마지막 최적화*
- **DRAM ↔ Network** — *μs 급 (라우팅 latency 는 별개)*. *DMA + Zero-Copy* 가 *throughput 의 결정*

---

## 마치며 — *실행 순간 의 *놀라움*

*"IntelliJ 실행"* 한 클릭 뒤 에 *5 phase, 4 계층, 수 백 만 개 의 syscall, 수십 GB 의 데이터 이동*. *"Telegram 실행"* 한 탭 뒤 에 *같은 원리 를 *다른 하드웨어 최적화* 로 *1/10 시간 에 달성*.

이 *실행 순간 의 이해* 가 *성능 튜닝 의 *직관 의 뿌리*. *"왜 첫 실행 이 느린가"* — *cold cache*. *"왜 2 번 째 는 빠른가"* — *warm page cache*. *"왜 모바일 이 데스크탑 만큼 반응 하는가"* — *Zygote + AOT*. *"왜 네트워크 가 종종 끊기는가"* — *RRC state 전환*.

*백엔드 개발자 도 *하드웨어 계층* 을 *이해 해야* 하는 이유. *DB 튜닝 / JVM GC / 캐시 정책 / 네트워크 buffer 크기* 의 *모든 결정 이 *같은 계층 의 *같은 원리*.

---

## 참고

- *Operating Systems: Three Easy Pieces* (Remzi Arpaci-Dusseau, *무료 online*)
- *Computer Systems: A Programmer's Perspective, 3rd Ed* (Randal Bryant, David O'Hallaron)
- *The Linux Programming Interface* (Michael Kerrisk)
- *Android Internals* (Jonathan Levin)
- *Modern Operating Systems, 5th Ed* (Andrew Tanenbaum)
- 자매편:
    - [CPU 의 L1, L2, L3 캐시 와 병목 구간 고찰](/2026/06/17/cpu-cache-hierarchy-l1-l2-l3-and-memory-bottleneck.html)
    - [JVM 의 본질 — Garbage Collection 부터 Virtual Thread 까지](/2026/06/22/jvm-internals-from-gc-to-virtual-thread.html)
    - [I/O 병목 어떻게 해결하지?](/2026/06/18/io-bottleneck-how-to-solve.html)
    - [Linux 커널 의 본질](/2026/06/22/linux-kernel-fundamentals.html)
