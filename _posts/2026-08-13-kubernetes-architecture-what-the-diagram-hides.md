---
layout: post
title: "쿠버네티스 구조는 배치도가 아니라 계약이다 — 6노드 클러스터를 해부해 다시 그렸다"
date: 2026-08-13 17:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k3s, architecture, control-plane, etcd, kubelet, cri, cni, reconciliation]
---

> 사설망 주소는 `<lan>` · `<mgmt>` 로 가렸다. 호스트 옥텟과 각 줄의 의미는 원본 실측 그대로다.

쿠버네티스 구조를 물으면 대부분 같은 그림을 그립니다. 왼쪽 박스에 API Server·Scheduler·Controller Manager·etcd, 오른쪽 박스에 kubelet·kube-proxy·컨테이너 런타임. 저도 그렇게 배웠고 [1일차 노트]({% post_url 2026-05-09-kubernetes-day1-architecture %})에 그렇게 적었습니다.

그런데 제가 2년째 돌리는 6노드 클러스터에서 그 박스들을 실제로 찾아보면, **그림대로 있는 게 하나도 없습니다.** 컨트롤 플레인 컴포넌트 파드는 0개이고, 7개로 나뉘어 있어야 할 컴포넌트가 프로세스 하나입니다.

이 글은 그 간극을 실측으로 확인하고, 그렇다면 "구조"라고 부를 수 있는 게 무엇인지 다시 정리한 기록입니다.

> **측정 환경 고지**
> 아래 수치는 2026-08-13 제 홈 클러스터(K3s v1.35.4+k3s1, 6노드, 45 네임스페이스 / 295 파드)에서 직접 측정한 값입니다. **K3s라는 특정 배포판의 단일 사례**이며, kubeadm이나 관리형 클러스터(EKS/GKE)는 배치가 다릅니다. 그 "다르다"는 사실 자체가 이 글의 주제입니다.

---

## 1. 공식 문서가 그림 밑에 붙여둔 단서

먼저 짚을 게 있습니다. 그 유명한 아키텍처 그림은 쿠버네티스 공식 문서에 실려 있지만, 공식 문서는 그 그림에 **스스로 면책을 붙여 놨습니다.**

> "The diagram in Figure 1 presents an **example reference architecture** for a Kubernetes cluster. The actual distribution of components **can vary** based on specific cluster setups and requirements."
> — [Kubernetes Documentation, *Cluster Architecture*](https://kubernetes.io/docs/concepts/architecture/)

즉 공식 문서는 그 그림을 *예시 참조 아키텍처*라고 부르지, 명세라고 부르지 않습니다. 같은 문서에서 kube-proxy 항목의 제목은 아예 **`kube-proxy (optional)`** 입니다. 네트워크 플러그인이 자체 프록시 구현을 제공하면 노드에 kube-proxy가 없어도 된다고 명시합니다.

컴포넌트가 합쳐질 수 있다는 것도 문서에 이미 나옵니다. kube-controller-manager 설명은 이렇습니다.

> "Logically, each controller is a separate process, but to reduce complexity, they are all **compiled into a single binary and run in a single process**."
> — 같은 문서

노드 컨트롤러·잡 컨트롤러·EndpointSlice 컨트롤러는 논리적으로 별개지만 실제로는 한 바이너리 한 프로세스입니다. **"논리적 분리 ≠ 물리적 분리"가 쿠버네티스 안에 이미 들어 있는 원칙**이라는 뜻입니다. 그렇다면 이 원칙을 더 밀어붙인 배포판이 있어도 이상하지 않습니다.

---

## 2. 실측 ① — 컨트롤 플레인 파드가 0개인 클러스터

kubeadm으로 만든 클러스터라면 `kube-system`에 `kube-apiserver-<node>`, `kube-scheduler-<node>`, `etcd-<node>` 같은 스태틱 파드가 보입니다. 제 클러스터에서 같은 걸 찾아봤습니다.

```
$ kubectl -n kube-system get pods --no-headers \
    | grep -E "kube-apiserver|kube-scheduler|kube-controller-manager|^etcd"
etcd-leader-observe-29776770-b8z4s   0/1  Completed
```

하나 걸린 `etcd-leader-observe`는 제가 만든 CronJob이지 etcd 본체가 아닙니다. **진짜 컨트롤 플레인 컴포넌트는 파드로 단 하나도 없습니다.**

`kube-system`에 실제로 도는 건 이게 전부입니다.

```
coredns × 2            local-path-provisioner × 1
node-local-dns × 6     metrics-server × 1
node-self-healer × 6   (+ 자체 CronJob들)
```

DNS, 스토리지 프로비저너, 메트릭 — 전부 **부가 기능**입니다. 클러스터를 클러스터이게 하는 핵심은 이 목록에 없습니다.

그럼 어디에 있을까요.

---

## 3. 실측 ② — "이 포트 누가 듣고 있냐"고 물으면 구조가 나온다

컴포넌트를 찾는 가장 정직한 방법은 이름으로 검색하는 게 아니라 **포트 소유자를 묻는 것**입니다. 각 컴포넌트는 고유 포트를 듣기 때문입니다.

```
$ sudo ss -lntp | grep -E ":(6443|2379|2380|10250|10256|10257|10259) "
127.0.0.1:2380         users:(("k3s-server",pid=735720,fd=9))
127.0.0.1:2379         users:(("k3s-server",pid=735720,fd=14))
<lan>.101:2380   users:(("k3s-server",pid=735720,fd=12))
<lan>.101:2379   users:(("k3s-server",pid=735720,fd=15))
127.0.0.1:10259        users:(("k3s-server",pid=735720,fd=220))
127.0.0.1:10256        users:(("k3s-server",pid=735720,fd=227))
127.0.0.1:10257        users:(("k3s-server",pid=735720,fd=176))
*:6443                 users:(("k3s-server",pid=735720,fd=4))
*:10250                users:(("k3s-server",pid=735720,fd=216))
```

포트 9개, **PID는 전부 735720 하나**입니다. 교과서라면 서로 다른 프로세스여야 할 것들이 한 프로세스의 파일 디스크립터로 나란히 붙어 있습니다.

| 포트 | 교과서상 주인 | 실제 주인 |
|---|---|---|
| 6443 | kube-apiserver | k3s server (pid 735720) |
| 2379 / 2380 | etcd (client/peer) | k3s server (pid 735720) |
| 10259 | kube-scheduler | k3s server (pid 735720) |
| 10257 | kube-controller-manager | k3s server (pid 735720) |
| 10250 | kubelet | k3s server (pid 735720) |
| 10256 | kube-proxy (healthz) | k3s server (pid 735720) |

프로세스 트리도 같은 얘기를 합니다.

```
$ ps -eo pid,ppid,comm,args
735720       1 k3s-server      /usr/local/bin/k3s server
736145  735720 containerd      containerd
```

컨테이너 런타임인 containerd조차 `k3s server`의 **자식 프로세스**입니다. 교과서 그림의 박스 7개가 여기서는 프로세스 1개 + 자식 1개입니다.

이건 K3s가 문서에 밝혀 둔 설계입니다. [K3s 공식 아키텍처 문서](https://docs.k3s.io/architecture)는 서버 노드를 "`k3s server` 명령을 실행하는 호스트로, 컨트롤 플레인과 데이터스토어 컴포넌트를 K3s가 관리한다"고 정의합니다. 제 클러스터는 서버 3대(lemuel·ilwon·solomon) + 에이전트 3대(david·louise·isagal) 구성이고, 노드 라벨로도 확인됩니다.

```
$ kubectl get nodes -o json | ... (role 라벨 추출)
lemuel    control-plane,etcd
ilwon     control-plane,etcd
solomon   control-plane,etcd
david     (none)
louise    (none)
isagal    (none)
```

**여기서 중요한 결론.** 만약 "쿠버네티스 구조 = 그 박스 배치"였다면, 제 클러스터는 쿠버네티스가 아니어야 합니다. 그런데 `kubectl`은 정상 동작하고 295개 파드가 돌고 CNCF 컨포먼스도 통과하는 배포판입니다. 배치도는 구조가 아니었던 겁니다.

---

## 4. 그렇다면 구조는 무엇인가 — 바뀌지 않는 계약 3가지

배치는 배포판 마음대로였습니다. 하지만 **바뀌지 않는 것**이 있습니다. 그게 진짜 구조입니다.

### 4.1 상태의 단일 출처 — etcd 하나, 관문 하나

컴포넌트가 몇 개로 쪼개지든, **클러스터의 상태는 etcd에만 있고 그 etcd를 만지는 문은 API Server 하나뿐**입니다. 공식 문서가 etcd를 "쿠버네티스의 모든 클러스터 데이터를 담는 백킹 스토어", API Server를 "컨트롤 플레인의 프런트엔드"라고 정의하는 이유입니다.

스케줄러도, 컨트롤러 매니저도, kubelet도 etcd에 직접 쓰지 않습니다. 전부 API Server를 통합니다. 이 hub-and-spoke가 깨지지 않기 때문에 컴포넌트를 한 프로세스에 몰아넣어도 동작이 같습니다. **합쳐도 되는 이유가 바로 이 계약**입니다.

### 4.2 나머지는 전부 조정 루프

API Server와 etcd를 뺀 모든 것은 같은 모양입니다. "원하는 상태(spec)를 보고, 현재 상태를 그쪽으로 밀고, 결과를 API Server에 보고한다."

> "In Kubernetes, controllers are control loops that watch the state of your cluster, then make or request changes where needed."
> — [Kubernetes Documentation, *Controllers*](https://kubernetes.io/docs/concepts/architecture/controller/)

같은 문서는 이렇게도 말합니다. "컨트롤러가 돌면서 유용한 변경을 만들 수 있는 한, 전체 상태가 안정적인지 아닌지는 중요하지 않다." 쿠버네티스는 **수렴하는 시스템이지 도달하는 시스템이 아닙니다.**

이 루프가 kubectl 한 줄에서 어떻게 도는지는 예전에 따로 파헤쳐 뒀습니다 → [kubectl run 한 줄의 뒷이야기]({% post_url 2026-06-20-kubernetes-control-loop-watch-reconcile-pattern-deep-dive %}).

### 4.3 노드 쪽은 통째로 갈아끼우게 설계돼 있다

노드 쪽 구조는 더 노골적입니다. kubelet은 컨테이너를 직접 만들지 않고 **CRI**로 런타임에 위임하고, 네트워크는 **CNI** 플러그인에, 스토리지는 **CSI** 드라이버에 위임합니다. 제 클러스터 실측입니다.

```
런타임(CRI):  containerd 2.2.3-k3s1
네트워크(CNI): /var/lib/rancher/k3s/agent/etc/cni/net.d/10-flannel.conflist
              플러그인 체인: flannel → portmap → bandwidth
              flannel 백엔드: vxlan
```

CNI는 플러그인 하나가 아니라 **체인**입니다. flannel이 파드에 IP를 붙이고, portmap이 hostPort를 처리하고, bandwidth가 대역 제한을 겁니다. 각각 독립 바이너리이고 순서대로 호출됩니다.

kube-proxy가 공식 문서에서 `(optional)`로 강등된 것도 같은 맥락입니다. Service 구현은 **결과가 계약이지 수단이 계약이 아니기 때문에**, eBPF 기반 구현으로 갈아끼워도 Service는 그대로 동작합니다.

---

## 5. 구조를 알면 미리 보이는 실패 3가지

여기까지가 이론이라면, 아래는 제가 실제로 맞은 것들입니다. 세 가지 다 **구조에서 예측 가능한 실패**였습니다.

### 5.1 상태가 하나라서 — 불변 필드에 선언을 밀어넣으면 무한 재시도

작년에 컨트롤 플레인 노드를 추가하며 옛 가이드를 따라 `/etc/rancher/k3s/config.yaml`에 `cluster-dns: 169.254.20.10`을 넣었습니다. 결과는 6시간짜리 장애였습니다.

원인은 구조 그대로입니다. 이 옵션은 결국 `kube-dns` Service의 clusterIP를 바꾸려는 시도가 되는데, clusterIP는 **API 스펙상 불변 필드**입니다.

```
$ kubectl explain service.spec.clusterIP
    ... This field may not be changed through updates unless the type field
    is also being changed to ExternalName ...
```

그리고 4.2에서 봤듯 컨트롤 루프는 **포기하지 않습니다.** 원하는 상태와 현재 상태가 영원히 안 맞으니 영원히 재시도합니다. "설정이 틀리면 에러 내고 멈춘다"는 명령형 시스템의 직관이 여기선 안 통합니다. **선언형 시스템에서 불가능한 선언은 조용한 무한 루프가 됩니다.**

### 5.2 조정 루프라서 — 선언을 지워도 실물은 안 죽는다

바로 오늘 겪은 일입니다. 은퇴시킬 앱 하나를 GitOps에서 제거하려고 ArgoCD Application을 지웠습니다. Application은 사라졌는데 **파드는 그대로 돌고 있었습니다.** 공개 URL도 200을 그대로 반환했습니다.

이것도 구조상 당연합니다. Application 리소스와 그 앱이 만든 워크로드 사이에 `ownerReferences`가 없으면, 가비지 컬렉터가 지울 근거가 없습니다. ArgoCD는 이 경우를 위해 `resources-finalizer.argocd.argoproj.io` 파이널라이저를 제공하는데, 그 Application에는 그게 없었습니다. 결국 네임스페이스를 직접 지워서 정리했습니다. 네임스페이스 삭제는 그 안의 리소스를 소유 관계로 확실히 정리해 주기 때문입니다.

**교훈:** "선언을 지웠다"와 "실물이 사라졌다"는 다른 사건입니다. 둘을 잇는 건 소유권(ownerReferences)과 파이널라이저이지, 선의가 아닙니다. 그리고 네임스페이스 삭제도 만능이 아닙니다 — PV, ClusterRole 같은 **클러스터 스코프 리소스는 남습니다.** 오늘 그것들까지 따로 확인하고서야 정리가 끝났습니다.

### 5.3 상태가 합의라서 — 서버는 왜 3대여야 하는가

etcd는 Raft 합의로 동작하므로 과반이 살아 있어야 씁니다. 3대면 1대까지, 5대면 2대까지 버팁니다. 2대는 1대보다 **나쁩니다** — 어느 한 대만 죽어도 과반(2/2)이 깨지기 때문입니다.

[K3s 문서](https://docs.k3s.io/architecture)가 HA 구성을 "3대 이상의 서버 노드 + 임베디드 etcd"로 규정하는 이유가 이것입니다. 제 클러스터에서 lemuel은 `SchedulingDisabled`로 워크로드를 안 받지만 여전히 서버로 둡니다. **일은 안 시켜도 표는 필요하기 때문입니다.**

---

## 6. 그래서 다시 그린 그림

```
             [ 사용자 / 컨트롤러 / kubelet ]
                          |
                    (유일한 관문)
                          v
                  +-----------------+
                  |   API Server    |  ← 인증·검증·버전변환
                  +-----------------+
                          |
                    (유일한 상태)
                          v
                  +-----------------+
                  |      etcd       |  ← Raft 과반 합의
                  +-----------------+

  이 두 개만 고정. 아래는 전부 "조정 루프"이고, 배치는 배포판 자유.

  scheduler / controller-manager / kubelet / kube-proxy(optional)
      = 각자 watch → 비교 → 밀기 → 보고

  그리고 노드 경계는 인터페이스로 뚫려 있다:
      kubelet --CRI--> containerd
             --CNI--> flannel → portmap → bandwidth
             --CSI--> 스토리지 드라이버
```

박스가 몇 개인지, 파드인지 프로세스인지는 배포판이 정합니다. **바뀌지 않는 건 화살표의 방향**입니다.

---

## 7. 한 줄 정리

**쿠버네티스의 구조는 컴포넌트 배치도가 아니라, "상태는 etcd 하나 · 문은 API Server 하나 · 나머지는 전부 수렴하는 루프 · 경계는 교체 가능한 인터페이스"라는 계약이다.**

배치도를 외우면 K3s 앞에서 무너지지만, 계약을 이해하면 프로세스가 1개든 7개든 같은 방식으로 디버깅할 수 있습니다. 오늘 제 클러스터에서 "이 포트 누가 듣고 있냐"는 질문 하나가 그림보다 정확했던 것처럼요.

---

## References

**1차·공식 출처**

- Kubernetes Documentation, *Cluster Architecture* — <https://kubernetes.io/docs/concepts/architecture/> (예시 참조 아키텍처 면책, kube-proxy optional, controller-manager 단일 바이너리 서술)
- Kubernetes Documentation, *Controllers* — <https://kubernetes.io/docs/concepts/architecture/controller/> (컨트롤 루프 정의, 원하는 상태 vs 현재 상태)
- K3s Documentation, *Architecture* — <https://docs.k3s.io/architecture> (서버/에이전트 정의, HA 3서버 + 임베디드 etcd)
- Kubernetes API 스펙 (`kubectl explain service.spec.clusterIP`) — clusterIP 불변성

**본문 측정치**

- 2026-08-13, 자체 운영 K3s v1.35.4+k3s1 6노드 클러스터에서 `kubectl` / `ss -lntp` / `ps` 로 직접 측정. 단일 클러스터·단일 배포판 사례이므로 kubeadm·관리형 클러스터에 그대로 일반화되지 않습니다.
- 5.1·5.2의 장애 사례는 같은 클러스터의 실제 운영 기록입니다.
