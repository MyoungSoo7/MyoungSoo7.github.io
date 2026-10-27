---
layout: post
title: "CPU 가 차면 느려지고, 메모리가 차면 죽는다 — 사용자와 클라이언트가 겪는 일의 차이"
date: 2026-10-27 22:59:08 +0900
categories: [devops, linux]
tags: [cpu, memory, psi, cgroup, oom, kubernetes, throttling, swap, use-method]
---

CPU 사용률 90% 와 메모리 사용률 90% 는 대시보드에서 같은 빨간색으로 보인다. 그런데 그 서버를 쓰는 사람이 겪는 일은 전혀 다르다. 이 글은 두 경우를 나란히 놓고 비교한다. 비교 대상은 셋이다.

- 컴퓨터 앞에 앉은 사용자
- 서버에 요청을 보내는 클라이언트
- 쿠버네티스 위의 컨테이너

글 중간에 오늘(2026-10-27 22:58) 홈랩 노드 세 대에서 잰 실측값을 예시로 붙였다.

## 결론부터

| | CPU 가 찼을 때 | 메모리가 찼을 때 |
|---|---|---|
| 자원의 성격 | **나눠 쓸 수 있다** (시간을 쪼갠다) | **나눠 쓸 수 없다** (자리를 차지한다) |
| 첫 증상 | 모두가 **조금씩 느려진다** | 처음엔 **아무 일도 없다** |
| 악화되면 | 응답 지연이 줄을 선 만큼 길어진다 | 회수 → 스왑 → 쓰래싱 → **프로세스 강제 종료** |
| 사용자 체감 | 커서·타이핑이 굼뜨다, 팬이 돈다 | 앱 전환할 때 멈칫, 디스크 소리, 어느 순간 창이 꺼진다 |
| 클라이언트 체감 | 지연(p99)이 늘고, 심하면 타임아웃 | 정상 응답 → 갑자기 연결 끊김·5xx·재시작 |
| 컨테이너 limit 초과 시 | **스로틀링** (멈췄다 재개) | **OOMKill** (재시작) |
| 되돌릴 수 있나 | 부하가 빠지면 즉시 회복 | 죽은 프로세스의 상태는 사라진다 |

쿠버네티스 설계 문서는 이 차이를 처음부터 **compressible(압축 가능) 자원 대 incompressible(압축 불가) 자원**으로 나눴다. CPU 는 limit 을 넘으면 "스로틀"되고, 메모리는 limit 을 넘으면 "죽을 수 있다"고 적었다 ([Kubernetes design proposal — Resource QoS](https://github.com/kubernetes/design-proposals-archive/blob/main/node/resource-qos.md)).

## 1. CPU 가 높아질 때 — "줄이 길어진다"

CPU 는 시간을 쪼개 나눠 주는 자원이다. 일이 코어 수보다 많아지면 운영체제는 아무것도 버리지 않는다. 대신 **차례를 기다리게 한다.** 그래서 증상은 늘 같다. 같은 일이 조금 더 늦게 끝난다.

중요한 건 사용률보다 **대기열**이다. Brendan Gregg 의 USE 방법론은 자원마다 세 가지를 따로 보라고 한다 ([Brendan Gregg — The USE Method](https://www.brendangregg.com/usemethod.html)).

- **사용률**(utilization): 바쁜 시간의 비율
- **포화도**(saturation): 처리하지 못하고 대기열에 쌓인 일의 양
- **에러**

같은 글에는 5분 평균 CPU 가 80% 를 넘은 적이 없는데 몇 초씩 100% 를 찍어 지연 문제가 났던 사례도 나온다. 사용률 숫자 하나로는 사용자가 기다렸는지 알 수 없다.

리눅스는 그 "기다림"을 직접 재는 지표를 제공한다. **PSI**(Pressure Stall Information)다. `/proc/pressure/cpu` 의 `some` 은 "적어도 일부 태스크가 CPU 를 기다리며 멈춰 있던 시간의 비율"이다 ([Linux kernel docs — PSI](https://docs.kernel.org/accounting/psi.html)).

오늘 밤 홈랩 노드에서 잰 값은 이렇다.

| 노드 (코어) | load avg 1분 | `cpu some` avg300 |
|---|---|---|
| ilwon (12) | 0.77 | 1.31% |
| louise (8) | 7.25 | 19.17% |
| lemuel (4) | 7.08 | **47.21%** |

lemuel 은 코어 4개에 실행 대기 7개 꼴이었다. 최근 5분 동안 절반 가까운 시간에 누군가가 CPU 차례를 기다리고 있었다는 뜻이다. 이 노드에서 도는 정산 API 를 부르는 클라이언트 입장에서는 이렇게 보인다.

- 요청은 **실패하지 않는다.**
- 응답이 **들쭉날쭉 늦다.** 평균은 조금 늘고 꼬리 지연(p99)은 많이 는다.
- 클라이언트 타임아웃보다 길어지면 그제야 타임아웃 에러가 된다. 클라이언트가 재시도하면 서버에 일이 더 쌓여 악순환이 된다.

컴퓨터 앞의 사용자에게는 마우스 커서가 끊기고, 글자가 한 박자 늦게 찍히고, 팬 소리가 커지는 것으로 나타난다. 무거운 작업을 끄면 **바로** 원래대로 돌아온다. CPU 포화는 "느림"이지 "손실"이 아니다.

### 컨테이너라면: 스로틀링

쿠버네티스에서 CPU limit 을 건 컨테이너는 한도에 닿으면 커널이 **CPU 접근 자체를 제한한다** ([Kubernetes — Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)). cgroup v2 의 `cpu.max` 는 "주기(period)마다 최대 얼마(max)까지 쓸 수 있다"는 대역폭 제한이다 ([Linux kernel docs — Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)). 그 주기 안에 할당량을 다 쓴 컨테이너는 다음 주기가 올 때까지 실행되지 않는다.

그래서 노드 전체 CPU 가 한가해도 그 컨테이너의 응답만 느려질 수 있다. 대시보드 CPU 그래프에는 안 보이고 `cpu.stat` 의 `nr_throttled` 에만 보이는 지연이다. 죽지는 않는다.

## 2. 메모리가 높아질 때 — "자리가 없어진다"

메모리는 쪼개서 나중에 줄 수 없다. 프로세스가 들고 있는 데이터는 그 자리에 있어야 한다. 그래서 메모리 문제는 CPU 와 순서가 반대로 진행된다.

### 1단계 — 높은 사용률은 대개 정상이다

리눅스는 남는 메모리를 디스크 캐시(page cache)로 채운다. 이 캐시는 필요하면 바로 비울 수 있다. 오늘 lemuel 의 `free` 를 보면 이렇다.

- 전체 32GB
- `buff/cache` 21.9GB
- `available` 23.6GB

"사용 중"으로 잡히는 숫자는 커도 실제로 새로 쓸 수 있는 메모리는 넉넉하다.

ilwon 은 Elasticsearch·Logstash 때문에 앱이 실제로 18.4GB 를 쥐고 있다. 그래도 `/proc/pressure/memory` 는 avg10·avg60·avg300 이 모두 0.00 이다. 메모리를 기다린 태스크가 없다는 뜻이다. **메모리 사용률 65% 와 메모리 압박 0% 는 동시에 참일 수 있다.** 이 단계에서 사용자와 클라이언트는 아무것도 느끼지 못한다.

### 2단계 — 회수와 스왑

`available` 이 바닥나기 시작하면 커널은 캐시를 버리고, 그다음에는 오래 안 쓴 페이지를 스왑으로 내린다. 이때부터 증상이 생기는데, CPU 포화와는 모양이 다르다.

- **방금 쓰던 앱**은 빠르다.
- **한동안 안 쓴 앱**으로 전환하면 멈칫한다. 디스크에서 페이지를 다시 읽어 와야 하기 때문이다.
- 서버라면 **가끔 오는 요청**이나 **오래된 데이터를 건드리는 요청**만 유독 느려진다.

오늘 louise 는 스왑 4GB 중 981MB 를, lemuel 은 8GB 중 102MB 를 쓰고 있었다. 부팅 이후 누적 스왑 아웃 페이지는 각각 676,396개와 488,887개였다(`/proc/vmstat` 의 `pswpout`). 지금 PSI 메모리 압박이 0 이니 현재는 문제없지만, 과거 어느 시점에는 이 단계까지 갔다는 흔적이다.

### 3단계 — 쓰래싱

모든 프로세스가 서로의 페이지를 밀어내며 스왑을 오가면, CPU 는 놀고 있는데 아무 일도 진척되지 않는다. PSI 문서는 `full` 줄, 즉 "모든 비유휴 태스크가 동시에 멈춘 시간"이 길게 이어지는 상태를 **쓰래싱**이라 부르고, 성능에 심각한 영향을 준다고 적는다 ([Linux kernel docs — PSI](https://docs.kernel.org/accounting/psi.html)).

사용자는 이 단계를 "컴퓨터가 얼었다"로 겪는다. 마우스는 움직이는데 클릭이 먹지 않고, 디스크 표시등만 깜빡인다. 클라이언트 입장에서는 서버가 연결은 받지만 응답을 안 주는 상태다. CPU 포화의 "느림"과 달리 **거의 무한한 느림**이다.

### 4단계 — 누군가 죽는다

더 회수할 게 없으면 커널의 OOM killer 가 프로세스 하나를 골라 강제 종료한다. cgroup v2 문서에 따르면 `memory.max` 에 닿았는데 사용량을 줄일 수 없으면 그 cgroup 안에서 OOM killer 가 호출된다 ([Linux kernel docs — Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)).

이때 사용자와 클라이언트가 겪는 일은 CPU 포화와 질적으로 다르다.

- 사용자: 작업하던 창이 **경고 없이 사라진다.** 저장 안 한 내용은 없어진다.
- 클라이언트: 진행 중이던 요청이 **연결 리셋**이나 502/503 으로 끝난다. 응답이 늦는 게 아니라 아예 오지 않는다.
- 서버: 메모리 안의 상태(세션, 캐시, 처리 중이던 트랜잭션)가 **통째로 사라진다.** 재시작한 프로세스는 캐시가 빈 상태라 한동안 오히려 더 느리다.

### 컨테이너라면: OOMKill, 그리고 노드 단위 축출

쿠버네티스 문서는 메모리 limit 을 OOM kill 로 강제하고, 그 집행이 **사후적**(reactive)이라고 설명한다. 커널이 메모리 압박을 감지했을 때만 죽이므로 limit 을 넘고도 한동안 살아 있을 수 있다는 것이다 ([Kubernetes — Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)).

컨테이너 limit 말고 **노드 전체** 메모리가 모자라면 kubelet 이 파드를 먼저 내보낸다(eviction). 이때 kubelet 은 PodDisruptionBudget 을 존중하지 않고, hard 임계치에서는 유예 시간 0초로 종료한다 ([Kubernetes — Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)). 같은 문서의 축출 신호 목록에는 `memory.available` 과 디스크·inode·PID 는 있지만 **CPU 는 없다.** CPU 가 모자란 노드는 느려질 뿐이고, 메모리가 모자란 노드는 파드를 잃는다. 쿠버네티스도 두 자원을 이렇게 다르게 다룬다.

## 3. 그래서 무엇을 봐야 하나

| 질문 | CPU | 메모리 |
|---|---|---|
| 사용자가 지금 기다리고 있나? | PSI `cpu some`, run queue(load / 코어 수) | PSI `memory some`·`full` |
| 사용률이 높은 게 문제인가? | 대기가 같이 늘면 문제 | `available` 이 줄 때만 문제 (캐시는 정상) |
| 컨테이너 단위로는? | `nr_throttled` 증가 = 스로틀 지연 | `OOMKilled` 종료 사유, 재시작 횟수 |
| 경보 기준은? | 지연(p99)과 대기 시간 | 남은 여유분(`available`), 스왑 유입(`pswpin`) 추세 |

한 문장으로 줄이면 이렇다. **CPU 경보는 "느려지고 있다"는 뜻이라 지켜볼 시간이 있고, 메모리 경보는 "곧 무언가 사라진다"는 뜻이라 그 전에 움직여야 한다.** 반대로 메모리 사용률이 높다는 것만으로 놀랄 필요는 없다. 대부분은 캐시이고, 진짜 신호는 `available` 과 PSI 다.

## References

- Kubernetes Documentation — [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) (CPU limit=스로틀링, memory limit=사후적 OOM kill)
- Kubernetes Documentation — [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/) (축출 신호에 CPU 없음, PDB 미존중)
- Kubernetes design proposals — [Resource Quality of Service](https://github.com/kubernetes/design-proposals-archive/blob/main/node/resource-qos.md) (compressible vs incompressible)
- Linux Kernel Documentation — [PSI: Pressure Stall Information](https://docs.kernel.org/accounting/psi.html) (Johannes Weiner)
- Linux Kernel Documentation — [Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html) (`cpu.max`, `memory.max`, Tejun Heo)
- Brendan Gregg — [The USE Method](https://www.brendangregg.com/usemethod.html) (사용률·포화도·에러)
