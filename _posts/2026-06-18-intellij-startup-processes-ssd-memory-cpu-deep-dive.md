---
layout: post
title: "*IntelliJ IDEA 가 켜질 때 도대체 *무엇이 *실행되는가* — *SSD · 메모리 · CPU* 관점 의 *기동 해부*"
date: 2026-06-18 22:55:00 +0900
categories: [ide, jvm, performance, intellij]
tags: [intellij, jetbrains, jvm, jit, indexing, fsnotifier, mmap, ssd, gc, code-cache, metaspace, hotspot]
---

> *Dock 아이콘* 을 클릭한다. *스플래시* 가 뜬다. *Welcome 창* 이 나타나기까지 *3~10 초*. 그동안 *내 맥* 의 *CPU 팬* 이 잠깐 돌고, *SSD 활성 LED* 가 깜빡인다.
>
> *그 안에서 *무슨 일이 일어나는가*. *왜 그렇게 *오래* 걸리는가. *왜 *프로젝트 열고 30 초간* *CPU 4 코어가 100%* 인가. *왜 *idea.vmoptions* 의 *-Xmx* 를 키우면 *체감 속도* 가 빨라지는가.

이 글은 *IntelliJ IDEA* 의 *프로세스 구조* 와 *그 프로세스 들이 *SSD · RAM · CPU* 위에서 *정확히 어떻게* 동작* 하는지 추적한다.

*Java IDE* 가 *어떻게 *수백만 줄 의 코드* 를 *실시간 으로 분석* 하면서 *부드러운 키 입력* 을 유지하는지 — 그 *시스템 엔지니어링 의 깊이* 를 *기동 시점* 에서 풀어본다.

대상 : *macOS / Apple Silicon* 기준. *Linux / Windows* 도 *큰 그림은 동일*. 차이가 있는 곳은 따로 표시.

---

## TL;DR — *한 줄 결론*

> *IntelliJ* 는 *큰 JVM 하나 (idea) + 작은 네이티브 헬퍼 (fsnotifier) + 빌드 데몬 (Gradle/Maven)* 의 *3 층 구조*. *SSD* 는 *mmap 된 인덱스 + JAR 클래스 로딩* 에 쓰이고, *RAM* 은 *Heap + Metaspace + Code Cache + mmap* 로 *4 군데* 갈라지며, *CPU* 는 *인덱싱 워커 + JIT 컴파일러 + GC + Daemon analyzer* 가 *멀티코어로 동시에* 굴린다. *IDE 가 느린 원인의 90%* 는 *이 셋 중 어디 가 병목인가* 의 문제.

---

## 1. *기동 직후 — *내 맥 에 *떠 있는 프로세스* 들**

`Activity Monitor` 또는 `ps` 로 보면, *IntelliJ 한 번 켜면* 평균 *5~9 개 프로세스* 가 동시에 올라온다.

```sh
$ ps -ef | grep -iE "idea|intellij|fsnotifier|jetbrains" | grep -v grep
```

대표적 구성 :

| 프로세스 | 종류 | 역할 |
|---|---|---|
| `idea` (또는 `IntelliJ IDEA`) | *JVM* | *메인*. 에디터 / 인덱서 / UI / 거의 전부 |
| `fsnotifier` | *네이티브 (C)* | *파일시스템 변경 감지* — OS 의 *FSEvents/inotify* 를 IDE 에 푸시 |
| `Java Launcher` 또는 `java` | *JVM 프로세스* | *Gradle / Maven 데몬*. 빌드 중에만 |
| `KotlinCompileDaemon` | *JVM* | *Kotlin 컴파일러 데몬*. 한 번 띄워두고 재사용 |
| `JetBrains Toolbox Helper` | *Electron/JVM* | *업데이트·라이선스 헬퍼*. 옵셔널 |
| `Code With Me` / `Gateway` 서버 | *JVM* | *원격 협업 / Remote Dev*. 켜면 뜸 |
| `clangd` / `rust-analyzer` 등 *LSP* | *네이티브* | *플러그인이 외부 LS 를 띄울 때* |
| `Docker plugin` 의 *DB 드라이버* | *JVM 서브 프로세스* | *Database tool 창 의 *외부 query runner* |

*핵심 통찰* : *대부분 의 일* 은 *메인 idea JVM 1 개* 안에서 일어난다. *수천 개의 스레드* 가 *그 안에* 산다. *외부 프로세스* 는 *OS 와 의 *얇은 경계* * 또는 *분리하면 안정성 이 더 좋은 작업* (빌드 / 컴파일 / LSP) 으로 *국한* 된다.

이게 *Electron 기반 VSCode* 와 *결정적으로 다른 점*. *VSCode* 는 *renderer / extension host / language server / file watcher* 가 *모두 별 프로세스*. *IntelliJ* 는 *거대한 모놀리식 JVM* 에 *얇은 네이티브 helper* 만 두른다. *통신 비용 0 + GC 1 개로 관리 + 디버깅 의 단순함* 을 얻고, *대신 *프로세스 격리 의 안전망* 을 포기*.

---

## 2. *메인 JVM `idea` 의 *내부 *— *스레드 풀 의 *동물원***

`jstack <pid>` 한 번 떠보면 *놀란다*. *200~400 개 스레드* 가 *한 프로세스 안* 에 있다.

대표 그룹 :

### 2.1 *EDT — Event Dispatch Thread*

*Swing UI 의 *유일한 스레드*. *모든 *화면 그리기 / 이벤트 처리* 가 *이 한 스레드* 에서 일어난다. *EDT 가 막히면 = IDE 가 얼어붙는다*. *IntelliJ 의 *체감 부드러움* 은 *"EDT 를 절대 막지 않는다"* 의 *광적인 엔지니어링* 결과.

### 2.2 *Indexing Workers*

*프로젝트 열 때 *수십 초간 *CPU 100%* 가 되는 그것*. `IndexInfrastructureExtension` 이 *멀티스레드 풀로 *.java / .kt / .xml / .properties / JAR* 를 *모두 읽어 *역인덱스* 를 만든다*. *N=CPU 코어 수* 만큼 병렬.

### 2.3 *Daemon Code Analyzer*

*키 입력 후 *몇 백 ms 의 *디바운스 뒤* 에 *현재 열려있는 파일* 을 *백그라운드 분석*. *Inspection (potential NPE / Unused / SonarLint 등) + Highlight + Quick fix 후보 계산* 이 모두 여기서. *우선순위 낮은 *데몬 스레드* 풀로 돌아 *EDT 와 인덱싱 에 양보*.

### 2.4 *JIT Compiler Threads (C1 / C2)*

*JVM 내장*. *나의 코드 가 아닌, IDE *자신의 *바이트코드* 를 *런타임에 *기계어로 컴파일* 한다. *IntelliJ 가 *방금 켰을 때 와 *5 분 뒤* 의 *체감 속도가 다른 이유* 의 *반*. *warm-up 효과 = JIT 가 *핵심 메서드* 를 *C2 로 최적화 완료* 한 상태*.

### 2.5 *GC Threads*

*G1 / ZGC* 의 *백그라운드 스레드*. *Apple Silicon 의 P-core* 가 *4~6 개* 있으면 *GC 가 그 중 하나를 차지* 하면서 *나머지로 사용자 일* 을 처리.

### 2.6 *기타 풀*

- `Application Pool` — 임의의 *백그라운드 작업*
- `RefreshQueue` — *fsnotifier 가 던진 *파일 변경 이벤트* 를 *받아 *VFS 갱신*
- `Tracing / Memory Monitor` — IDE 자체의 *내부 관측*

*핵심* : *IntelliJ 는 *내부 마이크로커널 같은 *concurrent 시스템*. *프로세스 1 개 + 스레드 수백 개 + 우선순위 분리*. 그래서 *외부에서 보면 1 개 JVM 이지만 *내부는 작은 OS*.

---

## 3. *SSD 관점 — *IDE 가 *디스크 에 *무엇을 *어떻게* 쓰고 읽는가**

### 3.1 *시작 시 *SSD 가 읽는 것들**

*Dock 클릭 → Welcome 창* 사이에 *수백 MB 의 sequential read* 가 발생.

대상 :

1. **`IntelliJ IDEA.app/Contents/jbr/`** — *번들된 JBR (JetBrains Runtime, 커스텀 OpenJDK)*. *200~300 MB 의 *libjvm.dylib + 표준 라이브러리 *.jar*.
2. **`IntelliJ IDEA.app/Contents/lib/` + `plugins/`** — *IDE 자체 의 JAR 들*. *500 MB ~ 1 GB*. *플러그인 수* 에 비례.
3. **`~/Library/Caches/JetBrains/IntelliJIdea2026.x/`** — *영구 캐시*. *인덱스 / class 파일 / Maven 캐시 메타*.
4. **프로젝트의 `.idea/`** — *프로젝트 설정 / module 정의 / iml*.

*Apple Silicon 의 *내장 NVMe SSD* 는 *순차 읽기 5~7 GB/s*. *번들 JAR 들* 은 *대부분 이 시점에 *page cache 에 올라온다*. *재시작이 빠른 이유* — *OS 가 *최근 읽은 페이지* 를 *RAM 에 캐시* 해서 *2 번째 부팅* 은 *훨씬 빠르다*.

### 3.2 *인덱싱 시 *SSD 가 *쓰는 것들**

*프로젝트 첫 열기 / Gradle sync 후* 에 *대량 의 작은 *random write* 가 발생.

대상 — `~/Library/Caches/JetBrains/.../index/` :

- **stub indexes** — *Java / Kotlin 의 *파일 → 메서드/클래스 시그니처* 역매핑*
- **id-index / word-index** — *전 문장 검색용 *trigram 인덱스**
- **filename-index** — *파일명 → 위치*
- **shared indexes** — *Maven 의 *공용 JAR* 의 *인덱스 (재사용 가능)*

이 인덱스 들은 *PersistentMap / PersistentHashMap* 이라는 *IntelliJ 자체 의 *키-값 저장소* 로 *디스크에 쓰임*. *append-only 로그 + 압축* 의 *구조*. *대규모 프로젝트 (수만 파일)* 의 *인덱스 크기 는 *수 GB* 까지*.

*SSD 마모 관점* — *4K random write* 의 폭격. *예전 *eMMC / SATA SSD* 에서 *인덱싱 중 IDE 가 느렸던 이유* 가 이것. *NVMe* 는 *random IOPS 50 만 +* 이라 *체감 없음*. *Apple Silicon 의 *통합 SSD* 는 더 빠름.

### 3.3 *상시 *SSD 사용 패턴 — *mmap 의 마법**

*가장 흥미로운 부분* : *IntelliJ 는 *인덱스 파일 을 *그냥 mmap* 해서 *RAM 처럼* 쓴다.

```
[프로세스 가상 메모리]
    ↓ mmap()
[SSD 의 인덱스 파일]
    ↓ OS 가 자동 페이지 인 / 아웃
[RAM 의 page cache]
```

이게 무엇을 뜻하는가 :

1. *인덱스 가 *Heap 안* 에 *없다*. *Heap 사용량 통계* 에 *인덱스 가 포함 안 된다*.
2. *OS 가 *자동 관리*. *자주 쓰는 인덱스 부분 은 *RAM 에 잡혀 있고*, *덜 쓰는 건 *디스크에 남는다*.
3. *체감 메모리 사용량* 이 *Activity Monitor 의 "메모리" 컬럼 보다 *더 클 수 있다* — *page cache 가 *공유 메모리 로 잡혀 있어서*.

이 mmap 전략 이 *Heap 을 *과하게 키우지 않고도* *수 GB 의 인덱스 를 다루는* 비결.

*MacOS 의 Activity Monitor* 에서 *IntelliJ 메모리* 가 *2 GB 인데 *실제 RAM 압박* 이 *4 GB 처럼 보이는 이유* 가 이것 — *mmap 된 page cache* 가 *IntelliJ 의 *사용 메모리* 로 *부분 표시*.

### 3.4 *프로젝트 인덱스 위치 *바꾸기 — *NVMe 분산 의 *경험적 효과**

*macOS* — `idea.properties` 에 :

```
idea.system.path=/Volumes/FastNVMe/idea-system
idea.config.path=/Volumes/FastNVMe/idea-config
```

*외장 NVMe (Thunderbolt)* 에 옮기면 *내장 SSD 마모 분산* + *대형 프로젝트 빌드 시 *내장 디스크 와 *경합 회피* 효과. 다만 *Apple Silicon 내장 SSD 의 *내구도 통계* 가 이미 *충분히 길어서* *일반 사용* 에선 *불필요*.

---

## 4. *메모리 관점 — *JVM 의 *4 가지 *메모리 영역**

`-Xmx4096m` 만 본다면 *전체 의 *4 분의 1* 만 보는 것*.

### 4.1 *Java Heap*

*객체 가 들어가는 곳*. `-Xmx` 가 *상한*. *IntelliJ 기본* `2048m`. *대규모 프로젝트* 는 *4096~8192m* 권장.

여기에 들어가는 것 :

- *열린 파일 의 *PSI 트리* (Project Structure Interface — *AST + 의존 그래프*)
- *인덱싱 중 의 *중간 자료구조*
- *키 입력 마다 *임시 객체*
- *플러그인 의 *모든 객체*

*Heap 부족 → OOM → IDE 죽음*. 또는 *GC 가 광적으로 돌면서 *모든 키 입력 마다 *200ms 지연**. *체감 신호* — *Heap 우측 하단 표시* 가 *빨개지고 GC 가 자주* 돈다면 *Xmx 부족*.

### 4.2 *Metaspace*

*클래스 메타데이터*. *얼마나 많은 클래스 가 *JVM 에 로드됐는지*. *IntelliJ + 모든 플러그인 + 프로젝트의 *수만 JAR 의 클래스* 를 *모두 메모리에 적재*. *기본 *제한 없음*. 보통 *500 MB ~ 1.5 GB*.

*Heap 과 다른 영역*. *Xmx 와 무관*. *Metaspace OOM* 은 *별도 에러*.

### 4.3 *Code Cache*

*JIT 가 *컴파일한 기계어* 가 들어가는 곳*. *기본 `240MB`*. *JBR 은 더 크게 잡아둠 (`512MB` 정도)*.

*Code Cache 가 차면* → *JIT 가 *새 컴파일* 못 함 → *interpreter 모드로 돌아간다* → *IDE 가 *천천히 느려진다*. *IntelliJ 가 *오래 켜둘수록 느려진 적이 있다면* 이 원인 의심.

해결 : `-XX:ReservedCodeCacheSize=512m` (또는 더 크게).

### 4.4 *Off-heap / Direct Memory + mmap*

- **NIO Direct Buffer** — *파일 I/O / 네트워크 의 *제로카피*.
- **mmap 된 인덱스** — *위 3.3* 에서 설명. *수 GB 까지*.
- *기타 *native allocator* 가 잡은 메모리.

*"IntelliJ 가 메모리 8 GB 먹는다"* 는 사용자 경험 의 *대부분* — *Heap 4 GB + Metaspace 1 GB + Code Cache 0.5 GB + mmap 인덱스 2 GB + 기타*.

### 4.5 *체감 튜닝 *— *idea.vmoptions* *의 핵심 7 줄**

```sh
# macOS : ~/Library/Application Support/JetBrains/IntelliJIdea2026.x/idea.vmoptions
-Xms2048m
-Xmx8192m
-XX:ReservedCodeCacheSize=512m
-XX:+UseG1GC                       # 또는 -XX:+UseZGC (Java 21+, 더 작은 pause)
-XX:+UseStringDeduplication        # G1 에서 동일 문자열 풀링
-XX:SoftRefLRUPolicyMSPerMB=50     # SoftRef 가 메모리 압박 시 빠르게 해제
-XX:CICompilerCount=4              # JIT 컴파일러 스레드 (코어 ÷ 2 권장)
```

*"메모리 32 GB 인데 IntelliJ 가 4 GB 만 써서 답답하다"* → *`-Xmx` 가 *기본값 2048m* 에 묶여서 그렇다*. *키워라*.

---

## 5. *CPU 관점 — *멀티코어 가 *동시에 *무엇을 하는가**

*Apple M3 Pro* 기준 — *P-core 6 + E-core 6 = 12 코어*. *IntelliJ 가 *동시에 굴리는 것* 들 :

### 5.1 *기동 시 *— *코어 다 쓰지 못함**

*Welcome 창* 띄우기 까지 *큰 부분* 은 *클래스 로딩 + 일부 초기화* 가 *순차적*. *멀티 코어 가 *대부분 쉬는 시간*. 그래서 *기동 시간 단축 은 *주로 *SSD 속도* 와 *JBR 의 *AOT 캐시* * 에 의존.

*JBR (JetBrains Runtime)* 은 *최근 *Class Data Sharing (CDS) + AppCDS* 를 활용해서 *대부분 의 *공용 클래스* 를 *공유 메모리 영역* 에서 로드. 그래서 *재시작 이 빠르다*.

### 5.2 *프로젝트 인덱싱 시 *— *코어 다 씀**

`Indexing...` 진행 바 가 보이는 시점 — *N 개 의 워커 스레드* 가 *N 개 의 *.java / .kt / .xml 파일* 을 *병렬* 로 *파싱 + 인덱스 생성*. *CPU 100% × 코어 수*. *팬 풀가동*.

이 시점 의 *병목 은 *CPU* 가 아니라 *SSD 의 *small file 읽기 IOPS* 인 경우 도 많다. *NVMe 는 *문제 없음*, *느린 디스크* 면 *CPU 가 *읽기 대기* 로 *50% 만 활용*.

### 5.3 *상시 *— *부드러운 코어 분담**

| 코어 / 스레드 | 일 |
|---|---|
| *EDT (1 스레드)* | *UI 그리기 + 키 입력 처리*. *반드시 빨라야 함*. |
| *Daemon Code Analyzer (백그라운드 풀)* | *현재 파일 의 *Inspection / Highlight* |
| *Indexing (백그라운드 풀)* | *VFS 변경 감지 시 *부분 재인덱스* |
| *JIT C2 (1~4 스레드)* | *IDE 자체 의 *hot path* 를 *기계어로 컴파일* |
| *GC (1~4 스레드)* | *G1 의 *동시 마킹 / 짧은 STW*. *ZGC 면 *거의 STW 없음* |
| *Gradle 데몬 (다른 JVM)* | *빌드 / 의존성 해석* |

*Apple Silicon 의 *P-core / E-core* 분리* — *macOS QoS API* 가 *IntelliJ 에 *영향*. *낮은 우선순위 풀* 은 *E-core 에 배치 되어 *고성능 작업 의 P-core 양보*. *이게 *키 입력 부드러움* 의 *현대적 기반*.

### 5.4 *JIT — *워밍업 의 *진짜 의미**

JIT 의 두 단계 :

1. **C1 — *클라이언트 컴파일러*** — *빠르게 *덜 최적화된* 기계어 생성*. *시작 후 *몇 초 안에*.
2. **C2 — *서버 컴파일러*** — *충분히 호출된 메서드 (호출 ≥ 10,000 ish)* 를 *공격적 최적화*. *시작 후 *몇 분 ~ 몇 십 분 뒤* 까지 계속.

*"오래 켜둔 IntelliJ 가 *빠르다"* 의 *기술적 정체* — *C2 가 *수천 메서드 를 *기계어로 최적화 완료*. *재시작 = warm-up 의 *리셋*. 그래서 *상시 켜둔다* 가 *생산성 의 합리적 선택*.

다만 *C2 가 *과하게 메모리 를 쓰면* (위 *Code Cache* 부족) *역효과*. *균형* 의 문제.

### 5.5 *GC — *조용한 백그라운드 청소부**

*G1 GC* — *기본*. *Heap 을 *Region 단위* 로 나누고 *동시 마킹 + 짧은 STW 로 compaction*. *수십 ms 의 pause*.

*ZGC* — *Java 21+*. *최대 pause 1 ms 미만*. *대용량 Heap (8 GB +)* 에서 *극적 효과*. *대규모 IntelliJ 프로젝트* 에서 권장.

GC 의 *체감 영향* :

- *키 입력 직후 *400 ms 정지* 가 가끔 → *Full GC* 의심
- *Heap 이 항상 95% 이상* 으로 차 있다 → *Xmx 부족*
- *CPU 의 *항상 일정 비율* (20%) 이 *백그라운드 GC* → *Heap 이 작거나 *GC 알고리즘 미스 매치*

---

## 6. *부 프로세스 들 — *Gradle / Maven / LSP* 의 *분리 이유**

### 6.1 *Gradle Daemon*

*Gradle 은 *항상 *데몬 모드*. *한 번 띄워두고 *재사용*. *왜 IDE 와 분리* 하는가 :

- *Gradle 의 *클래스로더 가 *복잡* 하고 *전역 상태가 많아* IDE 와 *섞으면 안정성 떨어짐*
- *빌드 중 *OOM 나도 *IDE 는 멀쩡* — *분리 의 안전망*
- *빌드 결과 의 *VM 캐시* (warm-up) 를 *유지하기 위해* *수십 분간 idle 로 살려둠*

`./gradlew --status` 로 *몇 개의 데몬* 이 *어느 JVM 버전* 으로 떠 있는지 확인 가능. *데몬 4~5 개 가 *조용히 *RAM 1~2 GB 씩* 잡고 있는 경우 있음*. `--stop` 으로 정리.

### 6.2 *KotlinCompileDaemon*

*같은 이유 + 같은 패턴*. *Kotlin 컴파일러 의 *클래스 로딩 비용* 이 *매우 커서* (수 초) *데몬 으로 항상 살려둠*.

### 6.3 *fsnotifier (네이티브)*

*macOS 의 FSEvents* 또는 *Linux 의 inotify* 를 *Java 프로세스 에 *전달*. *왜 분리* — *JVM 의 *FileWatcher API* 가 *대규모 디렉터리 에서 *비효율* 이라 *작은 C 프로그램* 으로 *전용 구현*. *몇 KB 의 메모리 + 사실상 0% CPU*. *놀라울 정도 로 효율적*.

---

## 7. *체감 신호 *↔* 원인 매핑 *— *문제 가 *어디인지* 보는 법**

| 증상 | 의심 영역 | 진단 |
|---|---|---|
| *기동 이 *10 초 이상* | *SSD 느림 / page cache 미스* | *재시작 후 *2 번째* 가 빠르면 SSD 또는 *AV 스캔 의심* |
| *프로젝트 열고 30~120 초간 *CPU 100%* | *인덱싱* — *정상*. 대형 프로젝트 면 *그냥 기다림* | *Help → Diagnostic Tools → Activity Monitor* |
| *키 입력 후 *1~2 초간 *얼어붙음* | *EDT 가 막힘 / GC pause* | *Help → CPU and Memory profiler* |
| *오래 켜둘수록 *느려짐* | *Code Cache 차거나 / Metaspace 누수 (플러그인)* | *idea.vmoptions* 의 *Code Cache 증가* |
| *Gradle sync 가 영원* | *Gradle 데몬 의 *Heap 부족* | *gradle.properties* 의 *`org.gradle.jvmargs=-Xmx4g`* |
| *Heap 표시 가 *항상 95%+* | *Xmx 부족* | *Xmx 키워라 — 8192m 이상* |
| *Apple Silicon 인데 *팬 풀가동* | *백그라운드 인덱싱 또는 *플러그인 의 무한 분석* | *Help → Diagnostic Tools → Activity Monitor* |

---

## 8. *한 사이클 *— *Dock 클릭 → 첫 키 입력* *까지의 *타임라인***

내가 *맥 에서 *맥주 한 모금 마시는 동안* 일어나는 일 *순서* :

```
t=0.0s   Dock 클릭. dyld 가 IntelliJ IDEA.app 의 launcher 를 로드
t=0.1s   launcher → JBR 의 java 실행 → JVM 부팅 (libjvm.dylib 로드)
t=0.3s   JBR 의 Class Data Sharing (CDS) — 공유 메모리 의 클래스 메타 매핑
t=0.5s   IntelliJ 의 main class — PluginManager → 모든 *.jar 클래스로더에 등록
t=1.0s   fsnotifier 자식 프로세스 spawn → 파일 변경 감지 시작
t=1.2s   Swing EDT 시작 → 스플래시 화면 표시
t=1.5s   인덱스 디렉터리 mmap → page cache 로 매핑 시작
t=2.0s   Welcome 창 표시
t=2.5s   사용자 가 *프로젝트 선택*
t=3.0s   .idea/ 읽기 + 프로젝트 모델 구성
t=3.5s   에디터 창 표시 — UI 측면 에서는 *준비 완료*
t=4.0s   백그라운드 — Indexing 워커 시작. *CPU 다코어 동작 시작*
t=5.0s   Gradle 데몬 부팅 시작 (별도 JVM)
t=10s    인덱싱 진행 — *체감 *키 입력 약간 끊김*
t=30~60s 인덱싱 완료. *Daemon code analyzer* 가 *현재 파일 만 분석*
t=60s~   *완전 한 부드러움*. JIT C2 가 *조용히 hot path 최적화*
```

*"체감 *시작 시간*"* 의 정의가 *t=3.5s (에디터 표시)* 인지 *t=30s (인덱싱 완료)* 인지 에 따라 *"IntelliJ 느림"* 의 *의미가 달라진다*. *둘 다 알아두면 *튜닝 방향이 달라진다*.

---

## 9. *맺음 — *왜 이 깊이 까지 *들어가야 하나***

매일 *8~12 시간* 쓰는 *내 가장 강력한 도구*. *느려지면 *생산성 직타*. *그런데 *대부분 의 개발자* 는 *Xmx 가 *2048m 기본 그대로* 인 채로* *4 년째 *느린 IDE 와 싸운다*.

이 글의 *진짜 효용* 두 가지 :

1. **튜닝 의 *방향* 을 안다** — *느릴 때 *어디를 의심 할지*. *SSD 인지 / Heap 인지 / Metaspace 인지 / GC 인지 / 플러그인 인지*. *각각 의 *해결책 이 *완전히 다르다*.
2. **JVM 의 *현대 엔지니어링* 을 *눈으로 본다*** — *JIT / GC / mmap / off-heap / Class Data Sharing*. *IntelliJ 가 *수십 년 의 JVM 진화* 의 *집약 결과*. *내가 만드는 *Spring Boot 서비스* 도 *같은 원리 위* 에 있다.

내가 *오늘 *블로그 글 을 *쓰면서* 도, *IntelliJ 의 *백그라운드 데몬 코드 분석* 이 *내 마크다운 의 문법 오류* 를 *실시간 으로 표시* 한다. *그 부드러움 의 비밀* 이 위 *모든 레이어* 의 *조용한 협업*.

내일 *내 IDE 가 *얼면* — *이 글 의 *체감 신호 표* 로 돌아온다.

---

## 부록 — *체크리스트*

내 *맥 의 *IntelliJ 한 번 점검*. *오늘 바로 할 수 있는 *7 가지* :

- [ ] `idea.vmoptions` *열어보기* — *Help → Edit Custom VM Options*
- [ ] *`-Xmx` 가 *2048m 이면 *4096~8192m 으로 키우기*
- [ ] *`-XX:ReservedCodeCacheSize=512m` 추가*
- [ ] *`Help → Change Memory Settings` 도 같이 확인*
- [ ] *`Activity Monitor` 에서 *idea 의 *메모리 / CPU* 한 번 보기*
- [ ] *`~/Library/Caches/JetBrains/` 크기 확인 — *수 GB 면 정상*
- [ ] *`./gradlew --status` 로 *불필요 한 Gradle 데몬* 정리*

작은 변화 의 *체감 차이* 가 *놀랍게 *크다*. *4 년 의 *느린 IDE 와 의 싸움* 이 *3 분 의 *vmoptions 수정* 으로 끝나는* 케이스 가 *생각보다 흔하다*.

---

*관련 글*

- [*CPU 의 *L1/L2/L3 캐시*. 그리고 *내 코드 의 *병목* 분석법*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) — *CPU 캐시 가 *JIT 컴파일된 hot path* 와 *어떻게 만나는지*
- [*Kafka 의 운영 — *settlement 의 *실전 패턴*](/2026/06/17/kafka-in-production-settlement.html) — *JVM 의 *off-heap mmap* 이 *Kafka client 에서도 *동일 한 핵심 패턴*
