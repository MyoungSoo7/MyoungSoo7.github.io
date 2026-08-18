---
layout: post
title: "limits.memory 한 줄이 GC 알고리즘을 골랐다 — Full GC 1회에서 시작한 K3s 자원 한도 점검"
date: 2026-08-18 01:56:00 +0900
last_modified_at: 2026-08-19 01:59:31 +0900
categories: [kubernetes, jvm]
tags:
  [
    kubernetes,
    k3s,
    jvm,
    garbage-collection,
    serial-gc,
    g1gc,
    ergonomics,
    spring-boot,
    micrometer,
    actuator,
    resource-limits,
    codecache,
    homelab,
  ]
---

홈랩 K3s 에 `/풀지씨` 라는 진단 명령을 붙여뒀다. 운영 중인 Spring Boot 파드의 Full GC 횟수를 액추에이터 지표로 읽어오는 한 줄짜리 도구다. 오늘 새벽에 돌렸더니 파드 세 개가 나란히 이렇게 답했다.

```
■ Full GC 빈도 — settlement-prod
  settlement-app-...-qrhg8: majorGC(Full) 1회, minorGC 1362회, overhead 0.0% → ⚠️ Full GC 발생
  settlement-app-...-sph5r: majorGC(Full) 1회, minorGC 1367회, overhead 0.0% → ⚠️ Full GC 발생
  settlement-app-...-vb9c5: majorGC(Full) 1회, minorGC 1349회, overhead 0.0% → ⚠️ Full GC 발생
```

경고 표시가 세 번 떴지만 이건 경보가 아니다. Full GC 가 0이 아니면 무조건 `⚠️` 를 붙이도록 내가 짜놓은 판정식이 걸린 것뿐이다. 48시간 동안 딱 한 번, GC 오버헤드는 0에 수렴한다. 정상이다.

그런데 그 "정상" 을 확인하려고 원본 지표를 열었다가 예상 못 한 걸 봤다. **이 JVM 은 Serial GC 로 돌고 있었다.** 아무도 그렇게 설정한 적이 없는데.

이 글은 그 한 줄에서 시작해 파드의 자원 한도 설정을 되짚은 기록이다. 결론부터 쓰면 — `limits.memory: 1Gi` 라는 한 줄이 GC 알고리즘을 고른 것이었고, 진짜 손봐야 할 곳은 GC 가 아니라 **메모리 예산 배정**이었다.

> **이 글의 규칙 세 가지.** ① 숫자는 전부 2026-08-18 01:5x KST 에 실제 `settlement-prod` 파드에서 뽑은 것이다(K3s `v1.35.4+k3s1`, JVM `Eclipse Adoptium 25.0.3+9-LTS`). ② 동작의 근거는 벤더 공식 문서와 OpenJDK 소스에서만 가져온다. ③ 문서로 확인 안 되는 건 "판단" 이라고 표시한다. 사설 IP·DB 접속 문자열·시크릿 참조는 뺐다.

> **겹치는 글이 하나 있다.** [힙은 19%인데 컨테이너는 59%다](/2026/08/18/jvm-heap-budget-in-1gi-container/) 가 같은 파드를 거의 같은 시각에 재서, **Serial GC 로 돌고 있다는 사실을 독립적으로 발견했다.** 두 글이 겹치는 건 그 한 가지이고 나머지는 다르다. 그 글은 힙 밖 440MiB 의 **예산 배분** 을, 이 글은 **왜 Serial 이 골라졌는가(1791/1792 MB 임계값)와 Full GC 1회의 범인** 을 다룬다. 같은 관측을 두 사람이 따로 재서 같은 결론에 닿았다는 점은 그 자체로 재현성의 증거이므로, 하나를 지우는 대신 서로를 가리키게 두었다.

---

## 1. 측정 원본 — 48시간치

컨테이너가 JRE 이미지라 `jstat`·`jcmd` 가 없다. 그래서 `:8080/actuator/prometheus` 의 Micrometer 지표를 읽는다. 파드 하나(`qrhg8`, 노드 `isagal`)의 원본은 이랬다.

```
jvm_info{runtime="OpenJDK Runtime Environment",vendor="Eclipse Adoptium",version="25.0.3+9-LTS"} 1
process_uptime_seconds                                          173046.617
system_cpu_count                                                2.0

jvm_gc_pause_seconds_count{action="end of major GC",cause="CodeCache GC Threshold",gc="MarkSweepCompact"}  1
jvm_gc_pause_seconds_sum  {action="end of major GC",cause="CodeCache GC Threshold",gc="MarkSweepCompact"}  0.771
jvm_gc_pause_seconds_count{action="end of minor GC",cause="Allocation Failure",  gc="Copy"}            1363
jvm_gc_pause_seconds_sum  {action="end of minor GC",cause="Allocation Failure",  gc="Copy"}            5.715

jvm_gc_overhead                                                 3.3333333333333335E-5
jvm_gc_live_data_size_bytes                                     8.372616E7
jvm_gc_max_data_size_bytes                                      5.36870912E8
jvm_gc_memory_allocated_bytes_total                             8.7381682472E10
jvm_gc_memory_promoted_bytes_total                              1.4588672E7
```

풀어 쓰면 이렇다.

| 항목                | 값                                                         |
| ------------------- | ---------------------------------------------------------- |
| 가동 시간           | 173,047초 = **48.1시간**                                   |
| minor GC            | 1,363회 / 누적 5.715초 → 평균 **4.19ms**, 약 127초에 한 번 |
| major GC (Full)     | **1회** / **771ms**                                        |
| GC 총 정지시간 비율 | 6.486초 ÷ 173,047초 = **0.0037%**                          |
| 할당 총량           | 81.4 GiB (평균 **0.48 MiB/s**)                             |
| Old 승격 총량       | 13.9 MiB = 할당량의 **0.0167%**                            |
| GC 후 live set      | 79.8 MiB / Old 최대 512 MiB = **15.6%**                    |

승격률 0.0167% 는 대단히 낮다. 만들어진 객체가 거의 전부 Eden 에서 죽는다는 뜻이고, 세대별 GC 가 가장 잘 먹는 형태다. 여기까진 좋은 소식이다.

문제는 컬렉터 이름 두 개다. **`Copy`** 와 **`MarkSweepCompact`**.

---

## 2. 발견 1 — 아무도 고르지 않은 Serial GC

`Copy`(young) + `MarkSweepCompact`(old) 는 **Serial 컬렉터**의 MXBean 이름이다. 힙 풀 이름이 `Eden Space` / `Survivor Space` / `Tenured Gen` 인 것도 같은 얘기다. 같은 이미지를 메모리 한도만 바꿔 띄우고 `GarbageCollectorMXBean` 이름을 찍어보면 차이가 바로 보인다.

```
# --memory=1g            # --memory=2g
GC: Copy                 GC: G1 Young Generation
GC: MarkSweepCompact     GC: G1 Concurrent GC
                         GC: G1 Old Generation
POOL: Eden Space         POOL: G1 Eden Space
POOL: Survivor Space     POOL: G1 Survivor Space
POOL: Tenured Gen        POOL: G1 Old Gen
```

왼쪽이 운영 파드에서 나오는 이름이다.

그런데 배포 매니페스트에는 `-XX:+UseSerialGC` 가 없다. 컨테이너에 들어가는 JVM 옵션은 이게 전부다.

```yaml
env:
  - name: JAVA_OPTS
    value: "-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
resources:
  requests: { cpu: 300m, memory: 768Mi }
  limits: { cpu: 2, memory: 1Gi }
```

즉 컬렉터는 **JVM 이 알아서 골랐다**. 그 기준이 Oracle 의 HotSpot GC 튜닝 가이드에 그대로 적혀 있다.

> Garbage-First (G1) Collector on server-class machines, Serial Collector otherwise.
>
> The VM considers machines as server-class if the VM detects two or more processors and physical memory larger than or equal to **1792 MB**.
>
> — [HotSpot Virtual Machine Garbage Collection Tuning Guide, Java SE 25 — Ergonomics][ergo25]

조건은 둘 다 만족해야 한다.

- **프로세서 2개 이상** → `system_cpu_count` 가 2다. CPU 한도가 `2` 이므로 통과.
- **물리 메모리 1792 MB 이상** → 여기서 걸린다. 컨테이너 인식이 켜져 있으면 JVM 이 보는 "물리 메모리" 는 노드 메모리가 아니라 **cgroup 한도**다. 파드 안에서 확인한 값이 정확히 그렇다.

```
$ cat /sys/fs/cgroup/memory.max     # = limits.memory
1073741824                          # 1 GiB = 1024 MB
$ cat /sys/fs/cgroup/cpu.max        # = limits.cpu
200000 100000                       # quota/period = 2 CPU
```

**1024 MB 는 1792 MB 의 57% 다.** 서버급 판정에서 탈락하고, 그래서 Serial 이 선택됐다.

컨테이너 인식이 기본값이라는 것도 벤더 문서에 명시돼 있다.

> `-XX:-UseContainerSupport` — Linux only: The VM now provides automatic container detection support, which allows the VM to determine the amount of memory and number of processors that are available to a Java process running in docker containers. It uses this information to allocate system resources. **The default for this flag is `true`**, and container support is enabled by default.
>
> — [`java` Tool Specification, JDK 25][javaman]

곁가지지만 여기서 하나 정리된다. `JAVA_OPTS` 의 `-XX:+UseContainerSupport` 는 **기본값을 다시 켜는 중복 옵션**이라 지워도 동작이 같다.

### 재현 — 1791 MB 와 1792 MB 사이

문서만 믿고 넘어가지 않고 경계를 직접 찍어봤다. 운영 파드를 건드리면 안 되니 같은 벤더의 공개 이미지(`eclipse-temurin:25-jre`)를 로컬 도커에서 메모리 한도만 바꿔가며 돌렸다.

```bash
for MEM in 512m 1g 1791m 1792m 2g 4g; do
  for CPUS in 1 2; do
    docker run --rm --memory=$MEM --cpus=$CPUS eclipse-temurin:25-jre \
      java -XX:+PrintFlagsFinal -version | grep -E ' UseSerialGC | UseG1GC '
  done
done
```

결과는 문서와 정확히 일치했다.

| 컨테이너 메모리 한도 | `--cpus=1` | `--cpus=2`                         |
| -------------------- | ---------- | ---------------------------------- |
| 512m                 | Serial     | **Serial**                         |
| 1g                   | Serial     | **Serial** ← 운영 파드와 같은 조건 |
| 1791m                | Serial     | **Serial**                         |
| 1792m                | Serial     | **G1**                             |
| 2g                   | Serial     | **G1**                             |
| 4g                   | Serial     | **G1**                             |

1791m 과 1792m 사이에서 컬렉터가 갈린다. CPU 가 1개면 메모리를 아무리 줘도 Serial 이다. 두 조건이 AND 라는 문서 설명 그대로다.

같은 조건으로 힙 크기까지 재현해보면 운영 파드와 완전히 포개진다.

```bash
$ docker run --rm --memory=1g --cpus=2 eclipse-temurin:25-jre \
    java -XX:MaxRAMPercentage=75.0 -XX:+PrintFlagsFinal -version | grep -E ' MaxHeapSize | NewRatio | UseSerialGC '
MaxHeapSize  = 805306368        # = 768 MiB
NewRatio     = 2
UseSerialGC  = true
```

운영 파드의 힙 풀 최댓값을 더하면 `Eden 204.9 MiB + Survivor×2 51.1 MiB + Tenured 512 MiB = 768 MiB`. 똑같다.

여기서 짚어둘 게 하나 더 있다. 이 파드가 올라간 노드 `isagal` 은 **CPU 40개**짜리다. 그런데 JVM 은 2개만 본다. 그리고 Serial GC 는 정의상 **GC 작업을 스레드 하나로** 처리한다([Tuning Guide, Serial Collector][gcserial]). 40코어 노드 위에서 GC 는 1스레드로 돈다 — 매니페스트 두 줄이 만든 결과다.

---

## 3. 발견 2 — Full GC 1회의 범인은 힙이 아니라 코드캐시였다

여기가 이번 점검에서 제일 재미있었던 대목이다. Full GC 지표에 `cause` 라벨이 붙어 있다.

```
jvm_gc_pause_seconds_count{action="end of major GC", cause="CodeCache GC Threshold", gc="MarkSweepCompact"} 1
```

`Allocation Failure` 가 아니다. **`CodeCache GC Threshold`** 다. 힙이 모자라서 난 Full GC 가 아니라는 뜻이다.

이 문자열은 OpenJDK 소스에서 바로 확인된다.

```cpp
// src/hotspot/share/gc/shared/gcCause.cpp
case _codecache_GC_threshold:
  return "CodeCache GC Threshold";
```

발생 지점도 찾을 수 있다. JIT 컴파일러가 만든 기계어(nmethod)를 담는 코드 캐시가 일정 비율 이상 늘어나면, **코드 캐시 쪽에서 힙 수집을 요청한다.** 안 쓰는 nmethod 를 언로드하려면 GC 를 한 번 돌려야 하기 때문이다.

```cpp
// src/hotspot/share/code/codeCache.cpp
double threshold = SweeperThreshold / 100.0;
...
if (allocated_since_last_ratio > threshold) {
  log_info(codecache)("Triggering threshold (%.3f%%) GC due to allocating %.3f%% since last unloading ...");
  Universe::heap()->collect(GCCause::_codecache_GC_threshold);   // ← 여기
}
```

— [openjdk/jdk, tag `jdk-25+36`][jdksrc]

숫자를 맞춰보면 앞뒤가 딱 맞는다. 같은 컨테이너 조건에서 코드 캐시 기본값은 이렇다.

```
ReservedCodeCacheSize    = 251662336     # 240 MiB
NonProfiledCodeHeapSize  = 122916864     # 117.2 MiB  ← 파드 지표의 max 와 동일
ProfiledCodeHeapSize     = 122916864     # 117.2 MiB  ← 동일
SweeperThreshold         = 15.0          # %
StartAggressiveSweepingAt= 10            # %
```

임계치는 240 MiB 의 15% = **36 MiB**. 그리고 운영 파드의 현재 코드 캐시 사용량은 47.1 MiB(19.6%)다. 부팅 직후 JIT 이 클래스 27,814개를 컴파일하며 코드 캐시를 채우는 동안 36 MiB 선을 **한 번** 넘었고, 그 시점에 Full GC 가 딱 한 번 발생한 것이다. 이후 48시간 동안은 추가 발생이 없다.

즉 이 Full GC 는 **워밍업의 부산물**이지 메모리 압박의 신호가 아니다. `/풀지씨` 가 붙인 `⚠️` 는 이 구분을 못 한 것이다.

다만 대가는 있었다. Serial 의 `MarkSweepCompact` 는 전체 힙을 **STW 로 표시-쓸기-압축**한다. 그래서 그 한 번의 정지가 **771ms** 였다. 지금은 live set 이 79.8 MiB 라 이 정도로 끝나지만, 이 정지시간은 힙과 live set 이 커지면 같이 커진다. G1 처럼 표시 단계를 애플리케이션과 동시에 돌리는 구조가 아니기 때문이다.

---

## 4. 발견 3 — 진짜 문제는 GC 가 아니라 메모리 예산이었다

GC 를 따라가다 보니 더 손봐야 할 게 나왔다. `MaxRAMPercentage=75.0` 이다.

> 같은 파드의 메모리 예산 자체는 [바로 앞 글](/2026/08/18/jvm-heap-budget-in-1gi-container/)에서 따로 다뤘다. 여기서는 GC 논의에 필요한 만큼만 요약한다.

이 옵션이 무엇의 75% 인지가 핵심이다. 벤더 문서는 이렇게 말한다.

> `-XX:MaxRAMPercentage=percent` — Sets the maximum amount of memory that the JVM may use **for the Java heap** before applying ergonomics heuristics as a percentage of the maximum amount determined as described in the `-XX:MaxRAM` option. The default value is **25 percent**.
>
> — [`java` Tool Specification, JDK 25][javaman]

**힙에 대한 비율이다.** 그런데 컨테이너가 죽고 사는 기준은 힙이 아니라 프로세스 전체의 RSS 다. 같은 파드의 힙 밖 메모리를 세어보면 이렇다.

| 영역                   | committed     | used          |
| ---------------------- | ------------- | ------------- |
| Metaspace              | 145.3 MiB     | 143.6 MiB     |
| Compressed Class Space | 20.3 MiB      | 19.5 MiB      |
| CodeHeap (3종 합)      | 48.3 MiB      | 47.1 MiB      |
| **힙 밖 합계**         | **213.9 MiB** | **210.3 MiB** |

여기에 스레드 스택(현재 live 21개), GC·JIT 내부 구조, malloc 아레나, 다이렉트 버퍼가 더 붙는다. 그래서 최악의 경우를 더하면 이렇게 된다.

```
힙 최대치            768 MiB
힙 밖 committed    + 214 MiB
--------------------------------
                     982 MiB
컨테이너 한도        1024 MiB
--------------------------------
남는 여유             42 MiB   ← 스레드 스택·네이티브 할당 전
```

**힙이 실제로 최대치까지 차면 컨테이너가 한도를 넘는다.** 그리고 넘으면 어떻게 되는지는 쿠버네티스 문서가 분명히 적어놨다.

> `memory` limits are enforced by the kernel with **out of memory (OOM) kills**. When a container uses more than its `memory` limit, the kernel may terminate it. (…) This means `memory` limits are enforced **reactively**.
>
> — [Kubernetes, Resource Management for Pods and Containers][k8sres]

지금까지 안 죽은 이유는 단순하다. 워크로드가 작아서 **힙이 최대치 근처에 가본 적이 없기** 때문이다.

```
힙 committed  263 MiB   (최대 768 MiB 중)
힙 used        95 MiB
memory.current 601 MiB  (한도의 59%)
```

live set 이 80 MiB 인 앱이라 힙이 커질 일이 없었을 뿐, 설정 자체는 초과 배정 상태다. **부하가 늘어 힙이 실제로 자라는 날, 이 파드는 GC 문제가 아니라 OOMKill 로 죽는다.** (판단)

참고로 이 파드는 requests(`768Mi`/`300m`)와 limits(`1Gi`/`2`)가 달라 QoS 는 `Burstable` 이다. 노드에 메모리 압박이 오면 `Guaranteed` 보다 먼저 축출 후보가 된다([Pod QoS Classes][k8sqos]).

---

## 5. 곁다리로 드러난 것 — 내 진단 스크립트의 판정식이 틀렸다

이번 점검에서 도구 쪽 버그도 두 개 나왔다.

**(1) `major > 0` 이면 경고, 는 틀린 기준이다.** `jvm_gc_pause_seconds_count` 는 **부팅 이후 누적**이다. 워밍업에 한 번 발생한 Full GC 는 영원히 카운트에 남고, 그래서 이 판정식은 파드가 살아있는 한 계속 `⚠️` 를 띄운다. 늑대가 온다고 매번 외치는 알람은 알람이 아니다.

봐야 할 건 세 가지다 — **증가율**(`rate()`), **누적 정지시간**(`_sum`), 그리고 **`cause` 라벨**. `CodeCache GC Threshold` 와 `Allocation Failure` 는 완전히 다른 사건인데 지금 스크립트는 둘을 구분하지 않는다.

**(2) `overhead 0.0%` 를 "GC 없음" 으로 읽으면 안 된다.** `jvm_gc_overhead` 는 누적값이 아니라 **롤링 윈도**다. Micrometer 구현이 그렇게 돼 있다.

```java
// JvmHeapPressureMetrics.java — 기본 생성자
this(emptyList(), Duration.ofMinutes(5), Duration.ofMinutes(1));   // lookback=5분, testEvery=1분

Gauge.builder("jvm.gc.overhead", gcPauseSum, pauseSum -> {
    double overIntervalMillis = Math.min(System.nanoTime() - startOfMonitoring, lookback.toNanos()) / 1e6;
    return gcPauseSum.poll() / overIntervalMillis;
})
.description("An approximation of the percent of CPU time used by GC activities over the last lookback period ...")
```

— [micrometer-metrics/micrometer, `JvmHeapPressureMetrics`][micro]

기본 창은 **5분**이다. 측정값 `3.3333e-5` 를 되짚으면 지난 5분간 GC 정지 합계가 **10ms** 라는 뜻이지, "GC 가 없었다" 가 아니다. 오히려 이 지표는 창이 짧아서 **알람에 쓰기 좋다** — 다만 무엇을 재는지 알고 써야 한다.

---

## 6. 그래서 뭘 바꿀 것인가

여기서부터는 문서가 답을 주지 않는 영역이라 **판단**으로 표시한다.

먼저 반직관적인 결론 하나. **이 워크로드에서 Serial GC 는 나쁜 선택이 아니다.** 오히려 Oracle 가이드의 권고와 맞아떨어진다.

> The serial collector uses a single thread to perform all garbage collection work (…). It's best-suited to single processor machines because it can't take advantage of multiprocessor hardware, although it can be useful on multiprocessors for applications with **small data sets (up to approximately 100 MB)**.
>
> — [HotSpot GC Tuning Guide, Java SE 25 — Available Collectors][gcserial]

live set 79.8 MiB, 승격률 0.0167%, GC 정지 비율 0.0037%. 문서가 말하는 "약 100MB 이하 데이터셋" 에 정확히 들어간다. 성능 지표만 보면 지금 이 조합은 잘 돌고 있다.

문제는 **성능이 아니라 통제**다. 지금 상태는 이렇게 요약된다.

- 컬렉터를 **고른 사람이 없다.** 매니페스트의 `1Gi` 가 부수효과로 골랐다.
- 그래서 누군가 `limits.memory` 를 `2Gi` 로 올리는 순간, **의도치 않게 G1 으로 바뀐다.** 메모리만 늘렸다고 생각한 변경이 GC 알고리즘 교체를 동반한다.
- 반대로 앱이 자라 live set 이 300 MiB 쯤 되면, Serial 의 Full GC 정지는 지금의 771ms 에서 **초 단위로 늘어난다.** JVM 은 이때 알아서 G1 으로 갈아타지 않는다.

그래서 손볼 순서는 이렇다. (판단)

**① 컬렉터를 명시한다.** 지금 잘 돌고 있으니 당장은 Serial 을 유지하되, `-XX:+UseSerialGC` 를 명시적으로 적는다. 그러면 메모리 한도를 조정해도 GC 가 따라 바뀌지 않는다. **암묵적 기본값을 명시적 선택으로 바꾸는 것**이 이 변경의 전부이자 핵심이다.

**② 메모리 예산을 다시 짠다.** 이게 더 급하다. `MaxRAMPercentage=75` 는 힙 밖 214 MiB 를 계산에 넣지 않은 값이다. 힙 밖이 이미 한도의 21% 를 쓰고 있으니 75% 는 남는 게 없다. 한도 `1Gi` 를 유지한다면 **50~55%** 가 현실적이다(힙 512~~563 MiB + 힙 밖 214 MiB ≈ 726~~777 MiB, 여유 250 MiB 이상). live set 이 80 MiB 이므로 힙 512 MiB 도 여전히 6배 여유다.

**③ 한도를 올릴 거면 1792 MB 경계를 의식한다.** `2Gi` 로 올리면 서버급 판정을 통과해 G1 이 기본으로 붙는다. 그걸 원해서 올리는 건 합리적이지만, **모르고 넘는 것**과 **알고 넘는 것**은 다르다. ①을 먼저 해두면 이 경계를 밟아도 놀랄 일이 없다.

**④ 진단 스크립트의 판정식을 고친다.** `major > 0` → `rate(major) > 0 또는 cause != CodeCache`, 그리고 `overhead` 는 5분 창이라는 걸 출력에 적는다.

---

## 마무리

`/풀지씨` 는 "Full GC 1회, 정상" 이라고 답하면 되는 일이었다. 실제로도 정상이었다. 48시간 동안 GC 가 애플리케이션을 세운 시간은 전부 합쳐 6.5초, 가동시간의 0.0037% 다.

그런데 그 한 줄을 확인하러 원본 지표를 열었더니 **아무도 내린 적 없는 결정**이 두 개 나왔다. 컬렉터는 매니페스트의 메모리 한도가 골랐고, 힙 최대치는 컨테이너 한도를 넘기 직전까지 배정돼 있었다. 둘 다 지금은 문제를 일으키지 않는다. 워크로드가 작아서다.

쿠버네티스에서 `resources.limits` 는 스케줄러와 커널에만 전달되는 값처럼 보이지만, 실제로는 **그 안에서 도는 런타임의 자기 튜닝 입력**이기도 하다. JVM 만의 얘기도 아니다 — 쿠버네티스 문서는 Node.js 도 cgroup v2 메모리 한도를 제대로 못 읽는 버전이 있어 힙이 잘못 잡히고 OOM 으로 이어질 수 있다고 같은 맥락의 경고를 해둔다([About cgroup v2][k8scgroup]).

한 줄을 바꿀 때 그 줄이 컨테이너 밖에서만 의미를 갖는다고 가정하지 않는 것 — 이번에 얻은 건 그거다.

---

## References

- [HotSpot Virtual Machine Garbage Collection Tuning Guide, Java SE 25 — Ergonomics][ergo25] (Oracle 공식 문서) — 서버급 머신 판정 기준(프로세서 2개 이상 + 물리 메모리 1792 MB 이상)과 기본 컬렉터 선택 규칙
- [HotSpot Virtual Machine Garbage Collection Tuning Guide, Java SE 25 — Available Collectors][gcserial] (Oracle 공식 문서) — Serial 컬렉터의 단일 스레드 동작과 "약 100 MB 이하 데이터셋" 서술
- [`java` Tool Specification, JDK 25][javaman] (Oracle 공식 문서) — `-XX:-UseContainerSupport` 기본값, `-XX:MaxRAMPercentage` 정의(기본 25%, 힙 대상)
- [openjdk/jdk, tag `jdk-25+36` — `gcCause.cpp`, `codeCache.cpp`][jdksrc] (OpenJDK 1차 소스) — `CodeCache GC Threshold` 원인 문자열과 `SweeperThreshold` 기반 힙 수집 요청 지점
- [micrometer-metrics/micrometer — `JvmHeapPressureMetrics`][micro] (Micrometer 1차 소스) — `jvm.gc.overhead` 가 5분 롤링 윈도라는 구현 사실
- [micrometer-metrics/micrometer — `JvmGcMetrics`][microgc] (Micrometer 1차 소스) — `jvm.gc.live.data.size` / `jvm.gc.max.data.size` 정의
- [Kubernetes — Resource Management for Pods and Containers][k8sres] (공식 문서) — 메모리 한도의 cgroup·OOM kill 방식 강제, 반응적(reactive) 집행
- [Kubernetes — Pod Quality of Service Classes][k8sqos] (공식 문서) — Burstable 분류 기준과 축출 순서
- [Kubernetes — About cgroup v2][k8scgroup] (공식 문서) — 컨테이너 메모리 한도를 런타임이 잘못 읽을 때의 OOM 위험(Node.js 사례)

**측정 조건 명시.** 본문 수치는 홈랩 K3s 단일 클러스터의 파드 3개에서 2026-08-18 새벽 한 시점에 관측한 값이다. 벤치마크가 아니고, 다른 워크로드·JDK 배포판·커널에서 같은 값이 나온다는 보장은 없다. 다만 §2 의 컬렉터 선택 경계(1791m/1792m)와 §3 의 코드 캐시 기본값은 위 명령어로 누구나 재현할 수 있고, 판정 근거는 전부 위 1차 출처에 있다.

[ergo25]: https://docs.oracle.com/en/java/javase/25/gctuning/ergonomics.html
[gcserial]: https://docs.oracle.com/en/java/javase/25/gctuning/available-collectors.html
[javaman]: https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html
[jdksrc]: https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/hotspot/share/code/codeCache.cpp
[micro]: https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-core/src/main/java/io/micrometer/core/instrument/binder/jvm/JvmHeapPressureMetrics.java
[microgc]: https://github.com/micrometer-metrics/micrometer/blob/main/micrometer-core/src/main/java/io/micrometer/core/instrument/binder/jvm/JvmGcMetrics.java
[k8sres]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
[k8sqos]: https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/
[k8scgroup]: https://kubernetes.io/docs/concepts/architecture/cgroups/
