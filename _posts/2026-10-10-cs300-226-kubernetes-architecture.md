---
layout: post
title: "[CS300 #226] 쿠버네티스 아키텍처 — API 서버, etcd, 그리고 조정 루프"
date: 2026-10-10 21:46:00 +0900
categories: [cs]
tags: [cs300, devops, kubernetes, control-plane, etcd]
---

컴퓨터공학 300 주제 시리즈의 226번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

쿠버네티스는 "원하는 상태"를 API 서버를 거쳐 etcd 에 저장하고, 여러 컨트롤러가 각자 현재 상태를 원하는 상태로 끌어당기는 조정 루프(reconciliation loop)를 끝없이 도는 시스템이다.

## 왜 필요한가

컨테이너 하나는 `docker run` 으로 띄우면 된다. 수백 개를 여러 서버에 나눠 띄우고, 서버가 죽으면 다른 곳에 다시 띄우고, 버전을 하나씩 바꾸고, 트래픽을 살아 있는 것에만 보내는 일은 사람이 할 수 없다. 쿠버네티스는 이 일을 "명령"이 아니라 "선언"으로 해결한다. 사용자는 "이 이미지로 3개"라고 적을 뿐이고, 3개를 유지하는 방법은 시스템이 알아서 찾는다.

이 구조를 이해하면 장애를 읽을 수 있다. 파드가 Pending 에 머문다면 스케줄러 단계에서 막힌 것이고, 노드가 NotReady 면 kubelet 의 보고가 끊긴 것이다.

## 핵심 개념

### 전체 그림

```
              kubectl / CI / 컨트롤러
                       |
                       v
+-------------------- 컨트롤 플레인 ---------------------+
|  kube-apiserver  <---->  etcd (클러스터 상태 저장소)    |
|     ^      ^                                           |
|     |      +---- kube-scheduler (파드 -> 노드 배정)     |
|     +----------- kube-controller-manager (각종 컨트롤러)|
|     +----------- cloud-controller-manager (선택)       |
+-------------------------------------------------------+
          ^  watch / 상태 보고          ^
          |                            |
+---- 노드 1 -------+        +---- 노드 2 -------+
| kubelet           |        | kubelet           |
| 컨테이너 런타임    |        | 컨테이너 런타임    |
| kube-proxy(선택)  |        | kube-proxy(선택)  |
+-------------------+        +-------------------+
```

### 컨트롤 플레인 구성 요소

| 구성 요소 | 하는 일 |
|---|---|
| kube-apiserver | 쿠버네티스 API 를 제공하는 프런트엔드. 인증·인가·검증 후 etcd 에 읽고 쓴다. 다른 모든 구성 요소는 API 서버하고만 대화한다 |
| etcd | 일관성 있고 가용성 높은 키-값 저장소. 클러스터의 모든 데이터가 여기 있다 |
| kube-scheduler | 노드가 정해지지 않은 새 파드를 감시하다가, 자원 요청·제약 조건·친화성 등을 고려해 노드를 골라 준다 |
| kube-controller-manager | 노드 컨트롤러, 잡 컨트롤러, 엔드포인트 슬라이스 컨트롤러 등 여러 컨트롤러를 한 프로세스로 실행한다 |
| cloud-controller-manager | 클라우드 사업자 API 와 연동(로드밸런서, 노드 수명 등). 온프레미스에서는 없을 수 있다 |

핵심은 **API 서버가 유일한 관문**이라는 점이다. 스케줄러도 kubelet 도 etcd 에 직접 쓰지 않는다. 덕분에 인증·감사·검증이 한곳에서 일어난다.

### 노드 구성 요소

| 구성 요소 | 하는 일 |
|---|---|
| kubelet | 각 노드의 에이전트. 자기 노드에 배정된 파드 명세를 받아 컨테이너 런타임에 실행을 지시하고, 상태를 API 서버에 보고한다 |
| 컨테이너 런타임 | containerd, CRI-O 같은 CRI 구현체. 실제로 컨테이너를 띄운다 |
| kube-proxy | 서비스(Service) 의 가상 IP 로 오는 트래픽을 파드로 보내는 네트워크 규칙을 노드에 만든다. 같은 일을 하는 네트워크 플러그인을 쓰면 없을 수도 있다 |

### 선언과 조정 루프

쿠버네티스의 모든 컨트롤러는 같은 패턴을 따른다.

```
loop:
    desired = API 서버에서 원하는 상태(spec) 읽기
    actual  = 현재 상태 관찰
    if desired != actual:
        차이를 줄이는 행동 하나
    상태(status) 갱신
```

이 루프는 **수준 기반(level-triggered)** 이다. "무슨 이벤트가 있었나"가 아니라 "지금 차이가 얼마인가"를 본다. 그래서 이벤트를 하나 놓쳐도 다음 루프에서 결국 맞춰진다. 이것이 쿠버네티스가 부분 장애에 강한 이유다.

### 디플로이먼트를 만들 때 일어나는 일

`replicas: 3` 인 디플로이먼트를 적용하면 순서는 이렇다.

1. kubectl 이 API 서버에 디플로이먼트 객체를 보낸다. API 서버가 검증 후 etcd 에 저장한다.
2. 디플로이먼트 컨트롤러가 이를 감지하고 레플리카셋을 만든다.
3. 레플리카셋 컨트롤러가 파드가 0개임을 보고 파드 3개를 만든다(아직 노드 미정).
4. 스케줄러가 노드 없는 파드를 감지하고 각각 노드를 정해 기록한다(binding).
5. 해당 노드의 kubelet 이 자기에게 배정된 파드를 보고 런타임에 컨테이너 실행을 지시한다.
6. kubelet 이 파드 상태를 API 서버에 보고한다.

아무도 다른 구성 요소를 직접 호출하지 않는다. 모두 API 서버의 객체를 **watch** 하고 자기 몫을 할 뿐이다.

### 고가용성

컨트롤 플레인이 죽어도 이미 떠 있는 파드는 계속 돈다. kubelet 이 이미 받은 명세대로 컨테이너를 유지하기 때문이다. 다만 새 배포, 재스케줄, 오토스케일은 멈춘다. 운영 환경은 API 서버를 여러 대 두고, etcd 는 홀수 개(보통 3 또는 5) 멤버로 구성한다. etcd 는 Raft 합의를 쓰므로 과반이 살아 있어야 쓰기가 가능하다. 3대면 1대, 5대면 2대 장애를 견딘다.

## 직접 해 보기

조정 루프와 수준 기반 동작을 시뮬레이션해 보자. 노드 장애로 파드가 사라지고, 중간에 이벤트 하나를 놓쳐도 결국 원하는 수로 돌아오는지 본다.

```python
import random
random.seed(7)

desired = {"web": 3}
actual = {"web": ["web-1", "web-2", "web-3"]}
next_id = 4

def reconcile(name):
    global next_id
    have, want = len(actual[name]), desired[name]
    if have < want:
        pod = f"{name}-{next_id}"; next_id += 1
        actual[name].append(pod)
        return f"create {pod}"
    if have > want:
        return f"delete {actual[name].pop()}"
    return "in sync"

timeline = {
    2: ("node-fail", 2),   # 노드 장애로 파드 2개 소멸
    5: ("scale", 5),       # 사용자가 replicas 를 5로
    9: ("scale", 2),       # 다시 2로
}
for t in range(18):
    if t in timeline:
        kind, n = timeline[t]
        if kind == "node-fail":
            for _ in range(n):
                actual["web"].remove(random.choice(actual["web"]))
        else:
            desired["web"] = n
        print(f"t={t:2} EVENT {kind} {n}")
    # 30% 확률로 이번 루프를 놓친다(컨트롤러 재시작, 네트워크 지연 등)
    if random.random() < 0.3:
        print(f"t={t:2} (loop skipped)")
        continue
    have = len(actual["web"])
    print(f"t={t:2} want={desired['web']} have={have} -> {reconcile('web')}")
```

출력은 이렇다(시드를 고정했으므로 매번 같다).

```
t= 0 want=3 have=3 -> in sync
t= 1 (loop skipped)
t= 2 EVENT node-fail 2
t= 2 (loop skipped)
t= 3 want=3 have=1 -> create web-4
t= 4 want=3 have=2 -> create web-5
t= 5 EVENT scale 5
t= 5 (loop skipped)
t= 6 want=5 have=3 -> create web-6
t= 7 (loop skipped)
t= 8 want=5 have=4 -> create web-7
t= 9 EVENT scale 2
t= 9 (loop skipped)
t=10 (loop skipped)
t=11 want=2 have=5 -> delete web-7
t=12 want=2 have=4 -> delete web-6
t=13 (loop skipped)
t=14 (loop skipped)
t=15 want=2 have=3 -> delete web-5
t=16 want=2 have=2 -> in sync
t=17 want=2 have=2 -> in sync
```

눈여겨볼 곳은 t=9 이후다. 원하는 수가 2로 바뀐 순간과 그다음 루프가 두 번 건너뛰어졌다. 컨트롤러는 "scale 이벤트가 왔었다"는 사실을 기억하지 않는다. t=11 에 그냥 지금의 차이(5 대 2)를 보고 지우기 시작한다. 루프를 여러 번 건너뛰어도 결국 `in sync` 에 도달한다. 컨트롤러는 "무엇이 일어났는지"를 기억할 필요가 없다. 매번 차이만 보면 된다.

## 현업에서는

- **파드가 Pending 에 머문다.** 스케줄러가 노드를 못 찾은 것이다. `kubectl describe pod` 의 Events 에 "Insufficient memory", "node(s) had untolerated taint" 같은 이유가 남는다. 자원 요청을 줄이거나 노드를 늘리거나 제약을 고친다.
- **노드가 NotReady 가 된다.** kubelet 의 상태 보고가 끊긴 것이다. 노드의 kubelet 프로세스(systemd 유닛), 컨테이너 런타임, 디스크·메모리 압박을 본다. 일정 시간이 지나면 그 노드의 파드는 다른 노드로 옮겨진다.
- **etcd 가 심장이다.** etcd 의 디스크 쓰기 지연이 길어지면 API 서버 전체가 느려진다. 그래서 etcd 노드에는 빠른 디스크를 쓰고, 정기 스냅샷 백업을 한다(237번 주제). 홈랩 규모에서도 경량 배포판(k3s 등)이 내장 etcd 로 여러 서버 노드를 묶어 같은 원리로 고가용성을 만든다.
- **컨트롤 플레인 블립.** API 서버가 잠깐 응답하지 않으면, API 를 watch 하던 컨트롤러·오퍼레이터들이 한꺼번에 재시작하거나 에러를 쏟아낼 수 있다. 여러 파드의 재시작이 같은 시각에 몰려 있다면 각 파드가 아니라 그 시각의 컨트롤 플레인 이벤트를 먼저 찾는다.

## 확인 문제

1. 클러스터의 모든 상태가 저장되는 곳은? 그곳에 직접 쓰는 구성 요소는?
2. 새로 만든 파드에 노드를 배정하는 구성 요소는? 실제 컨테이너를 띄우라고 지시하는 구성 요소는?
3. "수준 기반" 조정이 "이벤트 기반" 처리보다 장애에 강한 이유는?
4. 컨트롤 플레인 전체가 10분간 내려갔다. 이미 떠 있던 파드는 어떻게 되는가? 무엇이 안 되는가?
5. etcd 멤버가 5개일 때 쓰기를 유지하면서 견딜 수 있는 장애 수는?

### 풀이

1. etcd. 직접 쓰는 것은 kube-apiserver 뿐이다.
2. kube-scheduler 가 배정하고, 해당 노드의 kubelet 이 컨테이너 런타임에 실행을 지시한다.
3. 매번 현재 차이를 보고 행동하므로, 이벤트를 놓치거나 컨트롤러가 재시작해도 다음 루프에서 결국 원하는 상태로 수렴한다.
4. 계속 돈다. kubelet 이 이미 받은 명세로 유지한다. 새 배포, 스케일, 장애 노드의 파드 재스케줄은 안 된다.
5. 2개. 과반(3) 이 살아 있어야 한다.

## 더 읽을거리 (References)

- Kubernetes Docs, [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/)
- Kubernetes Docs, [Cluster Architecture](https://kubernetes.io/docs/concepts/architecture/)
- Kubernetes Docs, [Controllers](https://kubernetes.io/docs/concepts/architecture/controller/)
- D. Ongaro, J. Ousterhout, "In Search of an Understandable Consensus Algorithm", USENIX ATC 2014. (Raft)
