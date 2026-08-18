---
layout: post
title: "힙은 19%인데 컨테이너는 59%다 — 1Gi 파드에서 JVM 메모리 예산 다시 세기"
date: 2026-08-18 01:55:00 +0900
last_modified_at: 2026-08-19 01:59:31 +0900
categories: [Kubernetes, JVM]
tags: [JVM, GC, Kubernetes, SpringBoot, Metaspace, Observability]
---

## 발단: 초록불이 켜졌는데 뒤가 켕겼다

운영 중인 정산 서비스(K3s, `settlement-prod`) 파드에 JVM 힙 점검을 돌렸다. 결과는 이랬다.

```
■ Heap 사용량 — settlement-prod
  settlement-app-...-qrhg8: heap 142MiB / max 742MiB (19%)
  settlement-app-...-sph5r: heap 108MiB / max 742MiB (15%)
  settlement-app-...-vb9c5: heap 136MiB / max 742MiB (18%)
  판정: ✅ 정상 (max 대비 여유)
```

같은 시각 `kubectl top` 은 이렇게 답했다.

```
NAME                             CPU(cores)   MEMORY(bytes)
settlement-app-7b6b7948b-qrhg8   6m           583Mi
settlement-app-7b6b7948b-sph5r   2m           582Mi
settlement-app-7b6b7948b-vb9c5   2m           572Mi
```

힙은 최대치의 19%다. 그런데 컨테이너는 1Gi 한도의 **57%**(`kubectl top` 의 working set 기준, cgroup 이 보고하는 `memory.current` 로는 **59%**)를 쓰고 있다. 두 숫자 사이의 440MiB 는 어디서 온 걸까. 그게 궁금해서 파드 안을 열어봤고, 예상과 다른 게 세 개 나왔다.

미리 밝혀두면 **이 글은 장애 리포트가 아니다.** 이 파드들은 지금 잘 돌고 있고, `settlement-prod` 네임스페이스에 `OOMKilled` 이력은 한 건도 없다. 아직 터지지 않은 여유(headroom)를 산수로 재본 기록이다.

> **같은 파드를 같은 시각에 다룬 글이 하나 더 있다.** [limits.memory 한 줄이 GC 알고리즘을 골랐다](/2026/08/18/one-line-memory-limit-chose-the-gc/) 는 같은 `settlement-prod` 파드에서 같은 Serial GC 사실을 독립적으로 발견했다. 겹치는 부분은 **발견 1**(Serial GC) 하나이고, 그 뒤로 갈라진다. 이 글은 **힙 밖의 440MiB 를 항목별로 나눠 예산을 다시 세우는 쪽** 이고, 그 글은 **왜 Serial 이 골라졌는지(1791/1792 MB 임계값)와 Full GC 1회의 범인(코드캐시)** 을 파는 쪽이다. GC 선택의 인과가 궁금하면 그쪽이, 1Gi 안에서 무엇이 얼마를 먹는지가 궁금하면 이쪽이 먼저다.

## 측정 조건

숫자는 전부 운영 파드에서 직접 읽었다. 컨테이너가 JRE 이미지라 `jstat`/`jcmd` 가 없어서, Spring Boot actuator 의 `/actuator/prometheus` 엔드포인트(Micrometer JVM 바인더[^micrometer])와 JVM 플래그 덤프를 썼다.

| 항목                     | 값                                                   |
| ------------------------ | ---------------------------------------------------- |
| JVM                      | Temurin 25.0.3+9 LTS (OpenJDK 25.0.3)                |
| `JAVA_OPTS`              | `-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0` |
| 컨테이너 limit / request | memory 1Gi / 768Mi, cpu 2 / 300m                     |
| QoS 클래스               | Burstable                                            |
| JVM 이 인식한 CPU        | 2 (`system_cpu_count`)                               |
| cgroup `memory.max`      | 1,073,741,824 B (1024 MiB)                           |
| cgroup `memory.current`  | 628,822,016 B (599.7 MiB, 한도의 58.6%)              |
| 프로세스 가동시간        | 172,979 s (약 48.0시간)                              |

플래그 덤프(`-XX:+PrintFlagsFinal`)의 핵심 네 줄:

```
size_t MaxHeapSize        = 805306368            {product} {ergonomic}
size_t MaxMetaspaceSize   = 18446744073709551615 {product} {default}
double MaxRAMPercentage   = 75.000000            {product} {command line}
  bool UseSerialGC        = true                 {product} {ergonomic}
  bool UseG1GC            = false                {product} {default}
```

## 발견 1: G1 이 아니라 Serial GC 로 돌고 있었다

`UseSerialGC = true {ergonomic}`. 아무도 지정하지 않았는데 JVM 이 스스로 골랐다는 뜻이다. GC 지표의 이름표도 그걸 뒷받침한다 — 힙 풀 이름이 `Eden Space` / `Survivor Space` / `Tenured Gen` 이고, GC 이름이 `Copy`(minor)와 `MarkSweepCompact`(major)다. G1 이었다면 `G1 Eden Space` / `G1 Old Gen` / `G1 Young Generation` 으로 찍힌다.

왜 Serial 인가. Oracle 의 JDK 25 GC 튜닝 가이드가 기준을 명시한다.

> Garbage-First (G1) Collector on server-class machines, Serial Collector otherwise.
> (…) The VM considers machines as server-class if the VM detects two or more processors and **physical memory larger than or equal to 1792 MB**.
> — _Oracle, HotSpot Virtual Machine Garbage Collection Tuning Guide (JDK 25), Ergonomics_[^ergonomics]

이 컨테이너는 CPU 2개는 채웠지만 메모리가 1024 MiB 다. 1792 MB 문턱을 못 넘는다. `-XX:+UseContainerSupport` 는 JVM 이 호스트 RAM 대신 cgroup 한도를 "물리 메모리"로 읽게 만드는 옵션이므로[^javadoc], 호스트가 아무리 큰 서버여도 JVM 은 이 파드를 **1GB짜리 비-서버급 머신**으로 판정한다. 그래서 Serial 이다.

즉 `-XX:MaxRAMPercentage=75` 를 붙여 힙을 키운 그 설정이, 컨테이너 한도를 1Gi 로 잡은 순간 **GC 종류까지 같이 결정하고 있었다.** 힙 크기 옵션 하나로 끝나는 문제가 아니다.

여기서 "그래서 Serial 이 나쁘다"로 넘어가고 싶은 유혹이 있는데, 이 데이터로는 그렇게 말할 수 없다. 실제 GC 성적은 이랬다.

| GC 지표 (48시간 누적)                 | 값                                              |
| ------------------------------------- | ----------------------------------------------- |
| Minor GC (`Copy`, Allocation Failure) | 1,362회 / 총 5.712초 (평균 4.2ms, 최대 4ms)     |
| Major GC (`MarkSweepCompact`)         | 1회 / 0.771초 — 원인은 `CodeCache GC Threshold` |
| `jvm_gc_overhead`                     | 0.00004 (0.004%)                                |
| 누적 할당량                           | 87,305,595,176 B ≈ 81.3 GiB (≈ 493 KiB/s)       |
| 누적 승격량(promoted)                 | 14,588,672 B ≈ 13.9 MiB                         |
| GC 후 live data size                  | 83,726,160 B ≈ 79.8 MiB                         |

48시간 동안 81.3 GiB 를 할당했는데 old 로 승격된 건 13.9 MiB — **할당량의 0.017%** 다. 객체가 거의 전부 young 에서 죽는다. 세대 가설이 교과서처럼 들어맞는 워크로드고, 이런 모양에서는 Serial 의 단순한 copy collector 가 4ms 짜리 멈춤으로 충분히 감당한다. G1 으로 바꿨을 때 더 나아진다는 근거는 이 글에 없다. 벤치마크를 안 돌렸기 때문이다. 여기서 확인된 사실은 하나뿐이다 — **선택한 적 없는 GC 가 돌고 있었다.**

## 발견 2: 힙보다 큰 건 힙이 아니었다

400MiB 의 행방을 찾아, 같은 파드의 메모리 풀을 전부 펼쳤다.

**힙 (Serial GC, 3개 풀)**

| 풀             | used          | committed     | max           |
| -------------- | ------------- | ------------- | ------------- |
| Eden Space     | 27.1 MiB      | 72.6 MiB      | 204.9 MiB     |
| Survivor Space | 0.5 MiB       | 9.0 MiB       | 25.6 MiB      |
| Tenured Gen    | 80.1 MiB      | 181.0 MiB     | 512.0 MiB     |
| **합계**       | **107.7 MiB** | **262.6 MiB** | **742.4 MiB** |

`MaxHeapSize` 는 805,306,368 B = 정확히 768.0 MiB (1024 MiB × 75%)인데, 풀 max 합은 742.4 MiB 다. Serial GC 는 survivor 두 개 중 하나만 동시에 쓸 수 있어서 가용 힙이 예약치보다 작게 잡힌다. 앞의 점검 스크립트가 뱉은 "max 742MiB" 가 이 숫자다.

**비-힙 (5개 풀)**

| 풀                               | used          |
| -------------------------------- | ------------- |
| Metaspace                        | 143.6 MiB     |
| Compressed Class Space           | 19.5 MiB      |
| CodeHeap 'profiled nmethods'     | 30.9 MiB      |
| CodeHeap 'non-profiled nmethods' | 14.6 MiB      |
| CodeHeap 'non-nmethods'          | 1.6 MiB       |
| **합계 (보고값 기준)**           | **210.3 MiB** |

여기서 눈에 걸리는 건 **Metaspace 143.6 MiB** 다. GC 후 실제로 살아있는 객체(live data size)가 79.8 MiB 인데, **클래스 메타데이터가 그 1.8배**다. 세 파드 모두 143.6 / 143.8 / 143.8 MiB 로 거의 같은 값이라 특정 파드의 사고가 아니라 이 이미지의 상수에 가깝다. Spring Boot fat jar 에 여러 도메인 모듈이 번들된 구조라면 이 정도 클래스 수가 이상한 건 아니다. 다만 **"메모리를 제일 많이 먹는 게 힙"이라는 전제가 여기서는 틀렸다**는 게 요점이다.

(주의: HotSpot 은 `Metaspace` 와 `Compressed Class Space` 를 별도 MemoryPool 로 보고하기 때문에, 위 210.3 MiB 합계에 클래스 공간이 이중으로 잡혔을 가능성이 있다. 그래서 아래 산수에서는 이중계상 논란이 없는 항목만으로도 결론이 서는지 같이 확인한다.)

## 발견 3: 예산을 더해보면 이미 한도를 넘는다

지금 이 컨테이너가 실제로 쓰는 599.7 MiB 를 분해하면 이렇다.

```
힙 committed        262.6 MiB
비-힙 (보고값)      210.3 MiB
------------------------------
소계                472.9 MiB
cgroup memory.current 599.7 MiB
------------------------------
나머지              126.8 MiB   ← 스레드 스택(21개) + GC 자료구조 + 네이티브 할당 등
```

문제는 힙이 아직 **committed 262.6 MiB** 라는 데 있다. 힙은 필요하면 742.4 MiB 까지 자란다. 나머지 항목이 지금 수준을 유지한다고 가정하고 힙만 최대로 밀어보면,

```
힙 (가용 최대)      742.4 MiB
비-힙               210.3 MiB
기타(스택·네이티브)  126.8 MiB
------------------------------
합계              1,079.5 MiB
컨테이너 limit     1,024.0 MiB
------------------------------
초과                 55.5 MiB
```

**힙이 JVM 이 허용한 최대치까지 자라면 컨테이너 한도를 55 MiB 넘긴다.** 이중계상 논란이 있는 `Compressed Class Space` 19.5 MiB 를 통째로 빼도 여전히 36 MiB 초과다. 즉 결론은 계상 방식과 무관하다.

이때 무슨 일이 일어나는지는 쿠버네티스 문서가 분명히 적어놓았다.

> `memory` limits are enforced by the kernel with out of memory (OOM) kills. When a container uses more than its `memory` limit, the kernel may terminate it.
> — _Kubernetes, Resource Management for Pods and Containers_[^k8s-resources]

> If a Container allocates more memory than its limit, the Container becomes a candidate for termination. (…) the kubelet restarts it, as with any other type of runtime failure.
> — _Kubernetes, Assign Memory Resources to Containers and Pods_[^k8s-memory]

여기서 중요한 건 **누가 먼저 죽이느냐**다. 힙이 `MaxHeapSize` 에 부딪히면 JVM 이 `OutOfMemoryError` 를 던지고, 스택 트레이스가 남고, 힙 덤프를 뜰 수 있다. 그런데 위 산수대로면 힙이 최대치에 닿기 **전에** 컨테이너 총량이 먼저 1Gi 를 넘는다. 그러면 커널 OOM killer 가 프로세스를 죽이고, 파드는 `OOMKilled` / exit code 137 로 재시작된다.[^k8s-memory] 자바 예외는 없다. 힙 대시보드는 마지막 스크레이프까지 초록색이다.

이게 이 글을 쓴 이유다. **"힙 19%, 정상"이라는 판정은 참이지만, 그 판정이 커버하는 범위가 컨테이너의 절반도 안 된다.**

## 왜 아직 안 터졌나 — 정직한 부분

지금까지 무사한 이유는 설정이 안전해서가 아니라 워크로드가 힙을 안 쓰기 때문이다.

- 할당률이 초당 493 KiB 다. 48시간에 81.3 GiB — 배치성 정산 워크로드치고 조용하다.
- live set 이 79.8 MiB 로 안정적이고, 48시간 승격량이 13.9 MiB 다. old 영역이 사실상 안 자란다.
- 그래서 힙 committed 가 262.6 MiB 에서 더 밀고 올라갈 압력이 없다.
- `settlement-prod` 의 `OOMKilled` 이력: 0건. (같은 네임스페이스의 `settlement-ai` 가 3회 재시작했지만 사유는 `Error`/exit 1 로 메모리와 무관하다.)

바꿔 말하면 **트래픽이나 배치 규모가 지금의 몇 배로 뛰는 날, 힙이 자라기 시작하는 그 지점이 위험 구간**이다. 그때 나타나는 증상은 "메모리 부족 에러"가 아니라 "이유 없는 파드 재시작"이라서, 원인을 찾는 데 시간이 더 걸린다.

## 조치 후보 (아직 적용하지 않음)

이 글 시점에 운영 설정은 그대로다. 검토 중인 선택지를 근거와 함께 적어둔다.

**1. `MaxRAMPercentage` 를 낮춘다.** 75% → 50% 면 힙 예약이 512 MiB 가 되고, 위 산수는 `512 + 210 + 127 = 849 MiB` 로 175 MiB 여유가 생긴다. 현재 live set 이 79.8 MiB 이므로 512 MiB 힙도 과할 만큼 넉넉하다. 코드 변경 없이 값 하나다. 가장 값싼 선택지.

**2. 컨테이너 limit 을 올린다.** 1Gi → 2Gi. 여유는 확보되지만 **부수효과가 하나 딸려 온다** — 2048 MB 는 1792 MB 문턱을 넘으므로 JVM 이 이 파드를 server-class 로 재분류하고 **GC 가 Serial 에서 G1 으로 자동 전환된다**.[^ergonomics] 지금 minor GC 평균 4.2ms / overhead 0.004% 인 워크로드에서 G1 이 더 나을지는 재봐야 안다. 검증 없이 넘어갈 변경이 아니다. GC 를 고정하고 싶으면 `-XX:+UseSerialGC` 를 명시해서 ergonomic 선택을 끄는 편이 낫다.

**3. `MaxMetaspaceSize` 를 명시한다.** 지금은 기본값, 즉 **무제한**이다(`18446744073709551615`). 클래스로더 누수가 생기면 메타스페이스가 상한 없이 자라고, 힙은 멀쩡한 채로 컨테이너가 OOMKill 된다 — 위에서 말한 "가장 찾기 어려운 증상"의 전형이다. 현재 143.6 MiB 이므로 여유를 둔 상한(예: 256m)을 걸어두면, 같은 사고가 커널 OOMKill 대신 JVM 의 `OutOfMemoryError: Metaspace` 로 터진다. 죽는 건 같지만 **원인이 로그에 남는다.**

**4. QoS 를 결정한다.** 현재 request 768Mi ≠ limit 1Gi 라 Burstable 이다. 노드 메모리 압박 시 Guaranteed 파드보다 먼저 축출 후보가 된다.[^k8s-qos] 정산 서비스에 그 리스크를 감수할지는 용량 계획의 문제라 별도 판단이 필요하다.

순서를 정한다면 **3번 → 1번**이다. 3번은 관측 가능성을 되찾는 변경이라 실패해도 손해가 없고, 1번은 실제 여유를 만드는 변경이다. 2번은 GC 전환을 동반하므로 벤치가 먼저다.

## 남는 교훈

세 줄로 줄이면 이렇다.

1. **컨테이너에서 `-XX:MaxRAMPercentage` 는 힙 크기만 정하지 않는다.** cgroup 한도가 1792 MB 문턱 아래면 GC 종류까지 따라 바뀐다. 힙 옵션을 만질 때 GC 가 뭐로 돌고 있는지 `PrintFlagsFinal` 로 한 번 확인할 값어치가 있다.
2. **비-힙을 안 세면 예산 계산이 안 맞는다.** 이 파드에서는 메타스페이스 하나가 live set 의 1.8배였다. `힙 최대치 + 비-힙 + 스택·네이티브 ≤ 컨테이너 limit` 이 성립하는지 더해봐야 한다. 안 성립하면, 힙이 다 차는 날 자바 예외가 아니라 exit 137 이 나온다.
3. **"힙 정상"과 "컨테이너 정상"은 다른 문장이다.** 힙 대시보드가 초록색인 상태로 OOMKill 이 나는 경로가 실재하고, 그게 제일 오래 헤매게 되는 종류다. 두 지표를 나란히 보게 만들어 두는 게 낫다.

측정은 다 끝냈고, 설정 변경은 아직 하지 않았다. 3번과 1번을 적용한 뒤의 숫자는 다음 글에서 다시 재보겠다.

---

## References

[^ergonomics]: Oracle, _HotSpot Virtual Machine Garbage Collection Tuning Guide, Release 25 — 2 Ergonomics_. <https://docs.oracle.com/en/java/javase/25/gctuning/ergonomics.html> (server-class 판정 기준 및 기본 GC 선택)

[^javadoc]: Oracle, _The java Command (JDK 25)_. <https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html> (`-XX:+UseContainerSupport`, `-XX:MaxRAMPercentage`)

[^k8s-resources]: Kubernetes, _Resource Management for Pods and Containers_. <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>

[^k8s-memory]: Kubernetes, _Assign Memory Resources to Containers and Pods_. <https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/>

[^k8s-qos]: Kubernetes, _Pod Quality of Service Classes_. <https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/>

[^micrometer]: Micrometer, _JVM Metrics_. <https://docs.micrometer.io/micrometer/reference/reference/jvm.html> (`JvmMemoryMetrics`, `JvmGcMetrics` 가 노출하는 지표 정의)

본문의 모든 수치는 2026-08-18 01:4x KST 에 운영 중인 `settlement-prod` 파드에서 `/actuator/prometheus`, `-XX:+PrintFlagsFinal`, `cat /sys/fs/cgroup/memory.max`, `kubectl top pod` 로 직접 읽은 값이다. GC 성능 비교(Serial vs G1)는 벤치마크를 수행하지 않았으므로 이 글은 우열을 주장하지 않는다.
