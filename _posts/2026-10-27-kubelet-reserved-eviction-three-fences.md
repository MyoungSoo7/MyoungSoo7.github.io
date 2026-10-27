---
layout: post
title: "kubelet 예약·축출 구조가 메모리 관리에 주는 이점 — 31.2Gi 노드에 친 울타리 세 겹"
date: 2026-10-27 23:24:12 +0900
categories: [devops, kubernetes]
tags: [kubernetes, kubelet, k3s, node-allocatable, eviction, cgroup-v2, memory, homelab]
---

홈랩 클러스터의 노드 상태를 보는 봇이 오늘 밤 이런 한 줄을 보냈다.

```text
🛡 예약 1Gi+1536Mi · 축출 1Gi 미만 (예고 2Gi 미만) · 파드몫 27.7/31.2Gi · 압박 없음
```

숫자 다섯 개가 한 줄에 들어 있다. 이 글은 그 다섯 개가 각각 무엇을 막는지, 그리고 이 구조가 "메모리를 관리할 때" 왜 유익한지를 실제 노드(`lemuel`, 4코어·31.2Gi 노트북, k3s 에이전트로 도는 워커)의 설정과 cgroup 값으로 확인한 기록이다. 같은 노드의 CPU 압박 이야기는 같은 날 쓰인 [CPU 포화와 메모리 포화 글](/2026/10/27/cpu-vs-memory-saturation-what-users-feel/)에 있다.

## 0. 실측 — kubelet 설정과 노드 수치

kubelet 의 실제 적용 설정은 `/api/v1/nodes/lemuel/proxy/configz` 로 읽었다(설정 파일이 아니라 *돌고 있는* 값).

| 설정 | 값 |
| --- | --- |
| `systemReserved` | cpu 500m, memory **1Gi** |
| `kubeReserved` | cpu 500m, memory **1536Mi** |
| `evictionHard` | memory.available **< 1Gi**, nodefs 10%, imagefs 15% |
| `evictionSoft` | memory.available **< 2Gi**, 유예 1분 |
| `enforceNodeAllocatable` | `[pods]` |
| cgroup | v2, systemd 드라이버 |

노드 쪽 숫자는 이렇다.

| 항목 | 값 |
| --- | --- |
| Capacity (memory) | 31.24Gi |
| Allocatable (memory) | **27.74Gi** |
| Allocatable (cpu) | **3** (4코어 중) |
| `kubepods.slice/memory.max` | **28.74Gi** |
| `kubepods.slice/memory.current` | 4.89Gi |
| `system.slice/memory.max` | `max` (상한 없음) |
| 파드 요청 합계 / 한도 합계 | 메모리 5933Mi(20%) / 13402Mi(47%) · CPU 1702m(56%) / 7980m(266%) |
| 메모리 PSI (avg300) | some 0.00 · full 0.00 |

## 1. 숫자가 맞아떨어지는 방식

공식 문서의 공식은 이렇다([Kubernetes Docs — Reserve Compute Resources for System Daemons](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)).

```text
Allocatable = Capacity − kube-reserved − system-reserved − eviction-hard
```

대입하면 31.24 − 1.5 − 1 − 1 = **27.74Gi**. 봇이 보여 준 "파드몫 27.7/31.2Gi" 가 정확히 이 값이다.

그런데 cgroup 상한은 27.74 가 아니라 **28.74Gi** 다. 이 1Gi 차이가 이 구조의 핵심이다. 커널이 막는 선(28.74)과 kubelet 이 축출을 시작하는 선은 다르다. **kubelet 이 커널보다 1Gi 먼저 움직이도록** 설계돼 있다. 아래 세 겹 울타리로 나눠 보면 이유가 보인다.

## 2. 울타리 ① — 스케줄러: 애초에 너무 많이 들이지 않는다

스케줄러는 Capacity 가 아니라 Allocatable 을 노드의 크기로 본다. 문서 표현으로는 "스케줄러는 Allocatable 을 넘겨 배치하지 않는다."

이점은 **계획 단계에서 막는다**는 것이다. 이 노드에서는 파드 말고도 k3s 에이전트(kubelet 내장)와 containerd, sshd, 커널이 메모리를 쓴다. 예약이 없으면 파드 요청이 31.2Gi 를 다 채울 수 있고, 그 순간 시스템 데몬이 쓸 자리가 계산상 0이 된다. 지금 요청 합계는 5.9Gi(Allocatable 의 20%)라 여유가 크지만, 그 여유를 *계산하는 기준선* 이 이미 2.5Gi + 1Gi 만큼 안쪽에 그어져 있다.

단, 이 울타리는 **요청(request)** 만 센다. 한도(limit) 합계는 이미 13.4Gi 이고, CPU 한도는 266% 로 과다 약정(overcommit) 상태다. 실제 사용이 요청을 넘는 순간부터는 스케줄러가 아니라 다음 울타리의 몫이다.

## 3. 울타리 ② — kubelet 축출: 커널보다 먼저, 고를 수 있을 때 고른다

kubelet 은 `memory.available` 을 주기적으로 보고 임계치를 넘으면 파드를 내보낸다([Kubernetes Docs — Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)). 이 노드에는 두 단계가 있다.

- **soft: 2Gi 미만이 1분 지속** → 유예를 두고 축출. 봇이 "예고 2Gi 미만" 이라고 부르는 선이다. 순간 스파이크에 파드를 죽이지 않는다.
- **hard: 1Gi 미만** → 유예 없이 즉시 축출. 문서상 hard 축출은 유예 0초이고 PodDisruptionBudget 도 보지 않는다.

이점은 **누가 죽을지를 kubelet 이 고른다**는 것이다. kubelet 은 ① 요청보다 더 쓰고 있는가 ② 파드 우선순위 ③ 요청 대비 초과량 순으로 고른다. 그래서 요청을 정직하게 적은 파드(Guaranteed, 혹은 요청 이내로 쓰는 Burstable)는 뒤로 밀린다([Kubernetes Docs — Pod Quality of Service Classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)). 축출된 파드는 Deployment 가 다른 노드에 다시 띄울 수 있고, 이벤트에 `Evicted` 사유가 남는다. **원인이 기록되는 죽음** 이다.

## 4. 울타리 ③ — cgroup 상한: 그래도 넘치면 커널이 파드 안에서 끝낸다

kubelet 은 폴링 기반이라 메모리가 몇 초 만에 치솟으면 놓칠 수 있다. 그래서 마지막 선이 커널에 있다. `enforceNodeAllocatable: [pods]` 이면 kubelet 은 모든 파드의 부모 cgroup(`kubepods.slice`)에 `memory.max` 를 건다. 이 노드에서는 **28.74Gi** 다(= Capacity − 두 예약). eviction-hard 1Gi 는 이 상한에 포함되지 않는다. 그 1Gi 가 바로 "kubelet 이 먼저 움직일 시간" 이다.

cgroup v2 에서 `memory.max` 를 넘기면 그 cgroup 안에서 회수를 시도하고, 안 되면 **그 cgroup 안의 프로세스만** OOM killer 대상이 된다([Linux Kernel Docs — Control Group v2, memory.max](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)). 파드들이 함께 폭주해도 k3s 에이전트나 sshd 가 아니라 파드 쪽에서 희생자가 나온다.

이게 중요한 이유는 **노드를 지키는 프로세스가 죽으면 그 노드의 파드 전체가 고아가 되기 때문**이다. 노드 전체 OOM 으로 k3s 에이전트(kubelet)가 죽으면 노드가 NotReady 가 되고, 그 위 파드 30개가 한꺼번에 상태 보고를 잃는다. 예약은 "파드 하나 대신 노드 하나를 잃는" 최악의 교환을 막는다.

## 5. 정리 — 세 겹이 각자 다른 실패를 막는다

| 울타리 | 기준선 | 막는 것 | 작동 시점 |
| --- | --- | --- | --- |
| ① 스케줄러 | Allocatable 27.74Gi | 처음부터 과다 배치 | 파드 배치 전 |
| ② kubelet 축출 | available < 2Gi(1분) / < 1Gi(즉시) | 요청을 넘겨 쓰는 파드의 누적 | 실행 중, 수초~1분 |
| ③ cgroup `memory.max` | kubepods 28.74Gi | ②가 놓친 급격한 폭주 | 즉시(커널) |

메모리 관리 관점의 이점을 한 줄씩 줄이면 이렇다.

1. **시스템 데몬의 자리가 숫자로 존재한다.** "남는 걸 쓰겠지"가 아니라 2.5Gi 가 장부에 잡혀 있다.
2. **희생자를 고른다.** 노드 전체 OOM 은 커널이 점수로 아무나 고르지만, 축출은 요청을 어긴 순서로 고른다.
3. **죽음이 설명된다.** `Evicted` 이벤트와 `MemoryPressure` 조건이 남아서, 사후 분석이 "왜 갑자기 재시작했지"에서 시작하지 않는다.
4. **경고 구간이 있다.** soft 2Gi 와 hard 1Gi 사이가 사람이나 알림이 개입할 수 있는 창이다. 서버체크봇의 "예고" 표시는 이 창을 화면에 그대로 옮긴 것이다.
5. **CPU 는 따로 논다.** CPU 예약 1코어는 Allocatable 을 3으로 만들지만 CPU 는 축출 신호가 아니다. CPU 가 모자라면 죽이지 않고 느려진다(봇이 보여 준 "CPU대기 27%"가 그 상태). 메모리와 CPU 를 같은 언어로 다루면 안 되는 이유다.

## 6. 아직 안 풀린 것

- **예약은 회계일 뿐, 시스템 데몬을 가두지 않는다.** `enforceNodeAllocatable` 이 `[pods]` 뿐이라 `system.slice` 의 `memory.max` 는 `max` 다. 문서에 따르면 `system-reserved`·`kube-reserved` 까지 강제하려면 해당 cgroup 을 지정하고 목록에 추가해야 한다. 지금은 k3s 에이전트가 1.5Gi 를 넘겨 써도 아무도 막지 않는다. 다만 강제하면 예약을 *과소* 추정했을 때 k3s 자체가 OOM 으로 죽으므로, 문서도 이 강제는 신중하게 하라고 권한다.
- **예약값이 실측에서 나온 게 아니다.** 1Gi·1536Mi 는 경험치다. k3s 에이전트와 containerd 의 실제 RSS 를 일정 기간 재서 맞춘 값이 아니다.
- **스왑이 켜져 있다.** `failSwapOn: false` 이고 스왑 8Gi 중 102Mi 를 쓰고 있다. 스왑이 있으면 `memory.available` 이 떨어지기 전에 페이지가 스왑으로 빠져, 축출보다 *느려짐* 이 먼저 올 수 있다. 오늘 메모리 PSI 는 0이라 실제 문제는 없지만, 축출 임계치가 의도대로 작동하는지는 스왑까지 넣어서 검증한 적이 없다.
- 이 글의 수치는 **압박이 없는 상태의 스냅숏** 이다. 실제로 soft·hard 축출이 발동한 사례는 이 노드에서 관측하지 않았다.

## References

- Kubernetes Docs — [Reserve Compute Resources for System Daemons (Node Allocatable)](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- Kubernetes Docs — [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- Kubernetes Docs — [Pod Quality of Service Classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)
- Linux Kernel Docs — [Control Group v2 (memory.max, OOM)](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)
- Linux Kernel Docs — [PSI — Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
