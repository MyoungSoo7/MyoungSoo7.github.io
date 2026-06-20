---
layout: post
title: "*쿠버네티스 의 작동 원리* — *kubectl 한 줄* 이 *컨테이너 가 뜨기 까지* 의 *8 단계* 와 *그 안 의 *분산 합의 의 우아함**"
date: 2026-06-20 23:30:00 +0900
categories: [kubernetes, distributed-systems, architecture, control-plane]
tags: [kubernetes, k8s, api-server, etcd, scheduler, kubelet, controller-manager, watch, informer, reconciliation, cri, declarative]
image: /assets/images/k8s-replicaset-sequence.jpg
---

![ReplicaSet 생성 → API Server → Controller → Scheduler → Kubelet → Docker 의 8 단계 시퀀스 다이어그램](/assets/images/k8s-replicaset-sequence.jpg)

> *kubectl create -f replicaset.yaml*. 엔터 키 한 번. 0.3 초 뒤 *Pod 가 떴습니다* 라는 응답. 5 초 뒤 *내 노드 어디 선가 컨테이너 가 *실제로 돌고* 있다*.
>
> *그 사이 0.3 ~ 5 초* 에 *무슨 일* 이 *내 클러스터 의 어느 프로세스 들* 사이 에서 *어떤 순서로* 일어 났는가. *왜 이 설계 가 *Google 의 Borg 가 *15 년* 굴린 끝에 *오픈소스로 풀어 놓은 *결정 답안* 인가*.

이 글은 *흔히 보는 *8 단계 시퀀스 도식* 을 *그대로 따라가면서* — *각 단계 의 *내부 메커니즘 / 데이터 / 실패 시나리오* 까지 *밀도 있게* 풀어 본다.

같이 보면 좋은 *자매편* :
- *[쿠버네티스 런타임 layered view](/2026/06/18/kubernetes-runtime-layered-view-deployment-replicaset-service-configmap-secret-volume.html)* — *떠 있는 상태* 의 *수직 적 층 구조* 시점
- *[쿠버네티스 의 유용성 — 온프레미스 와 클라우드 의 비대칭 비교](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)* — *왜 이 복잡함 을 *감수* 하는가*

이 글 은 *시간 의 시점* — *명령 이 떨어진 뒤 *흐름* 으로* k8s 를 본다. *층 구조* 와 *시간 흐름* 이 *직교 한 두 축* 으로 *같은 시스템 을 *입체 적* 으로 *완성*.

---

## TL;DR — *한 줄 결론*

> *쿠버네티스* 는 *분산 시스템 의 *모든 *조정 (coordination)* 을 *오로지 *etcd 에 쓰는 행위* * 로 *환원* 시킨다. *모든 컴포넌트 (Controller / Scheduler / Kubelet) 는 *서로 *직접 말하지 않고*, *오직 *API Server 를 *왓치 (watch)* 하면서 *각자 의 영역 의 *원하는 상태* 와 *현재 상태* 의 *차이* 를 *조용히 메우는 *컨트롤 루프* 만 돌린다*. *kubectl 한 줄* → *API Server 가 *etcd 에 한 줄 적음* → *세 명의 watcher 가 *순차적 으로 깨어남* → *컨테이너 가 뜸*. *이게 *전부*. 이 *놀라울 정도로 단순한 패턴* 이 *클러스터 의 *모든 자가 치유 / 자동 스케일 / 무중단 배포* 의 *근본*.

---

## 1. *등장 인물 *5 명* — *각자 의 역할 만 *고집스럽게* 한다**

도식 의 *5 개 박스* 를 *역할 단위* 로 정확히 정의 해 두자. *오해 하기 쉬운 지점 들* 까지.

### 1.1 *API Server* — *유일한 *진실 의 창구**

- *모든 클라이언트 의 *유일한 진입점*. *kubectl, 컨트롤러, 스케줄러, kubelet — 전부 *API Server 와 만 대화*.
- *etcd 를 *직접 접근 하는 유일한 컴포넌트*. *다른 누구도 *etcd 에 손 못 대게* 차단*. *데이터 일관성 의 *수문장*.
- *RESTful API + Watch 스트림* 을 제공. *Watch 는 *long-polling HTTP 또는 gRPC stream* 으로 *변경 이벤트 를 *실시간 푸시*.
- *Admission Controller / Authentication / Authorization* 까지 *이 안에서 *체인* 으로 처리.
- *상태 (state) 를 *직접 갖지 않는다*. *오직 *etcd 의 캐시 + 게이트키퍼*. *그래서 *수평 확장* (HA 모드 의 *3 노드 API Server*) 이 *자연 스럽다*.

### 1.2 *etcd* — *도식엔 *없지만 *진짜 주인공**

도식 에 *명시 되지 않음*. 그러나 *모든 *진실* 이 여기 에 있다.

- *RAFT 합의 알고리즘* 으로 *3 / 5 / 7 노드* 에 *분산 복제*. *과반수 합의* 가 *작성 의 조건*.
- *모든 객체* (Pod / Service / ConfigMap / Node / ...) 가 *Key-Value 로 저장*.
- *모든 객체 에 *ResourceVersion (rv)* * 이라는 *전역 단조 증가 의 수* 가 부여 됨. *낙관적 동시성 (Optimistic Concurrency)* 의 *비교 기준*.
- *Watch 는 *etcd 의 *MVCC + revision 기반*. *클라이언트 가 *마지막 본 rv* 부터 *그 이후 의 변경 만* 받음.
- *etcd 가 *느리면 *전체 클러스터 가 느리다*. *Production 의 90% 의 *컨트롤 플레인 문제* 의 *진짜 원인* 이 *여기*.

### 1.3 *Controller Manager* — *원하는 상태 의 *조용한 감독자**

- *수십 개 의 *Controller 의 집합* — ReplicaSet / Deployment / Node / Endpoint / Job / ... 각자 *자기 종류 의 리소스* 만 감시.
- *각 Controller 는 *Watch + 캐시 (informer)* 로 *API Server 의 자기 영역 객체* 를 *지속 추적*.
- *비교 → 행동 의 *두 줄 무한 루프* (reconciliation loop)*. *desired ≠ current 면 *API Server 에 *부족분 만큼 *추가 객체 생성 요청**.
- *결정 적 으로 — *직접 Pod 를 만들지 않는다*. *Pod 의 *명세* 만 *API Server 에 등록*. *실제 배치* 는 *Scheduler 의 일*.
- *모든 컨트롤러 가 *idempotent + level-triggered*. *같은 명령 을 *여러 번 보내도 안전*, *놓친 이벤트 는 *다음 동기화 에서 *자동 복구*.

### 1.4 *Scheduler* — *Pod 의 *집 정해주기* 담당**

- *PodSpec 의 *NodeName 이 비어 있는* Pod 만 본다*. *그 외 는 *무시*.
- *모든 노드 의 *자원 상태 / Taint / Affinity / 리소스 요구* 를 *후보 평가*.
- *2 단계 의 *필터 + 점수*. *(1)* *불가능 한 노드 *전부 제외* (Filter / Predicate) → *(2)* *남은 노드 들 의 *점수 매김* (Score / Priority) → *최고점 노드* 선택.
- *결정 의 결과 만 *API Server 에 PUT* — *`spec.nodeName: <chosen>`* 으로 *Pod 객체 패치*.
- *실제 배치 는 *Scheduler 가 안 한다*. *그 노드 의 Kubelet 이 *알아서 잡아 챔*.

### 1.5 *Kubelet* — *각 노드 의 *현장 감독**

- *모든 워커 노드 에 *데몬* 으로 상주. *자기 노드 에 *지정된 Pod 만* 봄*.
- *PodSpec 을 *받아 *Container Runtime 에 *gRPC 호출*. *옛날 엔 *Docker daemon* 직접, *지금 은 *CRI (Container Runtime Interface)* 표준 으로 *containerd / CRI-O*.
- *볼륨 마운트 / 네트워크 설정 (CNI 호출) / 라이프사이클 훅 / livenessProbe / readinessProbe* — *전부 *Kubelet 의 일*.
- *주기 적 으로 *현재 상태 (PodStatus) 를 *API Server 로 보고*. *이게 *도식 의 *8 번 단계*.

### 1.6 *Container Runtime (도식 의 "Docker")*

- *도식 의 *Docker* 는 *2026 년 기준 *containerd 또는 CRI-O 로 *읽어야 함*. *Kubernetes 1.24 부터 dockershim 제거*.
- *역할* — *컨테이너 이미지 *pull / 압축 해제 / namespace + cgroup 격리 + 실행*.
- *Kubelet 과 *gRPC CRI* 로 통신. *runc → OCI 표준 의 *런타임 핵심*.

---

## 2. *도식 의 *8 단계* — *한 줄 씩 *해부**

도식 의 *번호* 를 그대로 따라간다. 각 단계 의 *외부 표현 (도식)* + *내부 메커니즘 (실제 일어나는 일)* 의 *2 단 분리*.

### 2.1 *① ReplicaSet 생성 — `kubectl ... → API Server`*

```sh
$ kubectl apply -f replicaset.yaml
```

**도식 표현** — *kubectl 이 API Server 에 ReplicaSet 객체 를 *POST*.

**내부 메커니즘** :

1. *kubectl* 이 *YAML* 을 *읽어 *JSON 으로 변환*.
2. *`~/.kube/config`* 에서 *클러스터 주소 + TLS 인증서 + 사용자 인증 토큰* 을 꺼낸다.
3. *`POST /apis/apps/v1/namespaces/default/replicasets`* 으로 *API Server 에 보낸다*.
4. *API Server 의 *처리 체인* :
   - **Authentication** — *클라이언트 인증서 / 토큰 / OIDC* 검증.
   - **Authorization** — *RBAC* 으로 *이 사용자 가 *이 동작* 권한 보유 여부 확인*.
   - **Admission Controllers** — *PodSecurity / ResourceQuota / LimitRange / MutatingWebhook / ValidatingWebhook* 의 *순차 적용*.
   - **Schema Validation** — *OpenAPI 스키마* 로 *YAML 의 모양* 검증.
5. *통과 하면 — *etcd 에 *`/registry/replicasets/default/<name>`* 키 로 *저장*.
6. *etcd 가 *revision +1*. *그 새 revision 이 *ResourceVersion* 으로 객체 에 부여 됨.
7. *kubectl 에 *201 Created* 응답.

여기 까지 *수십 ms*. *이 시점* 에서 *Pod 는 아직 없다*. *ReplicaSet 의 *명세* 만 *적힘*.

### 2.2 *② 생성 요청 감시 — Controller 가 API Server 의 변경 을 받음*

**도식 표현** — *Controller 가 ReplicaSet 생성 이벤트 를 감지*.

**내부 메커니즘** — *Watch 의 마법*.

- *Controller Manager* 가 *기동 시 부터 *long-running watch* 를 *유지 중*. *대략* :
  ```
  GET /apis/apps/v1/replicasets?watch=true&resourceVersion=<last_seen>
  ```
- *이 요청 은 *닫히지 않는 HTTP 응답*. *서버 가 *변경 이 생기면 *그 시점 의 *이벤트 객체* 를 *바로 push*.
- *Controller 의 client-go 라이브러리 의 *Informer* 가 이 스트림 을 받아 *로컬 캐시 갱신*.
- *변경 이벤트 의 종류* — `ADDED`, `MODIFIED`, `DELETED`, `BOOKMARK`.
- *Informer 가 *EventHandler* 콜백 호출 — *"새 ReplicaSet 생겼다"* → *ReplicaSetController.syncHandler(key)* 트리거.
- *Controller* 의 *이번 일* — *ReplicaSet 의 *spec.replicas* 와 *현재 *그 라벨 셀렉터* 에 매칭 되는 Pod 수* 를 비교 → *부족분 계산*.

> *"왜 watch 가 *polling 이 아닌가"* 의 답 — *polling 은 *지연 + 부하 의 trade-off*. *watch (long-polling / streaming) 는 *수천 개 의 객체 변화* 를 *수 ms 지연* 으로 *수십 컴포넌트 에 *효율 적* 으로 전파. *분산 시스템 의 *진동 (jitter) 을 *최소화*.

### 2.3 *③ Pod 생성 요청 — Controller → API Server*

**도식 표현** — *Controller 가 API Server 에 Pod 객체 생성 요청*.

**내부 메커니즘** :

1. *부족분 계산* — *원하는 3 개 vs 현재 0 개 → 3 개 부족*.
2. *Controller 가 *PodTemplate 을 *복제* 해서 *Pod 객체* 3 개 생성. *각자 *OwnerReference* 로 *ReplicaSet 가리킴*.
3. *3 번* `POST /api/v1/namespaces/default/pods` 호출.
4. *API Server 가 *전과 같은 *Auth + Admission + 검증* 체인* 적용.
5. *etcd 에 *`/registry/pods/default/<podname>`* 키 로 *저장*.
6. *이 시점 의 *Pod.spec.nodeName* 은 *비어 있음*. *Pending phase*.
7. *etcd revision 다시 +1*.

**핵심 통찰** — *Controller 는 *idempotent + level-triggered*. *내일 다시 켜져도 *같은 결과*. *5 번 트리거 되어도 *3 개 만 만듦 (이미 있는 건 안 만듦)*. *이 단순함* 이 *클러스터 재시작 / 네트워크 분할 / 컨트롤러 죽음* 에서 *자가 회복* 의 근거.

### 2.4 *④ Pod 생성 요청 감시 — Scheduler 가 새 Pod 를 발견*

**도식 표현** — *Scheduler 가 새 Pod 알아챔*.

**내부 메커니즘** — *Controller 와 동일한 *Watch 패턴*. 차이 는 :

- *Scheduler 는 *Pod 만 본다*. *그 중 `spec.nodeName` 이 *빈 Pod 만 큐 에 넣음*.
- *내부 의 *PriorityQueue* 가 *대기 Pod 들* 을 우선순위 별 로 정렬.
- *루프* — *큐 에서 *하나 꺼냄* → *스케줄링 알고리즘 적용* → *결과 를 *API Server 에 PUT*.

### 2.5 *⑤ 노드에 Pod 할당 — Scheduler → API Server*

**도식 표현** — *Scheduler 가 Pod 에 노드 를 결정 해 *API Server 에 통보*.

**내부 메커니즘** — *2 단계 점수 매김*.

#### Filter (Predicate) 단계

*불가능 한 노드 *전부 제외*. 대표적 필터 :

- **PodFitsResources** — *CPU / Memory request 가 *남은 자원* 에 맞나*
- **PodMatchNodeSelector** — *PodSpec 의 nodeSelector / nodeAffinity 와 *노드 라벨* 매칭*
- **PodToleratesNodeTaints** — *노드 의 Taint 를 *Pod 의 Toleration 이 *허용 하는가*
- **NoVolumeZoneConflict** — *PV 의 가용 영역 (zone) 과 *Pod 가 갈 노드 의 zone* 호환*
- **PodAntiAffinity** — *"같은 라벨 의 Pod 와 *같은 노드 에 안 가게"* 같은 제약*

#### Score (Priority) 단계

*남은 후보 들 의 *0 ~ 100 점*. 대표 :

- **LeastRequestedPriority** — *남은 자원 많을수록 *고득점* (균등 분산)*
- **BalancedResourceAllocation** — *CPU / Memory 사용 비율* 의 *균형*
- **NodeAffinity** — *preferred (weight) 의 가산*
- **ImageLocalityPriority** — *이미지 가 이미 노드 에 있으면 *고득점* (pull 시간 절약)*
- **InterPodAffinity** — *친 한 Pod 와 가까이 *가점*

**결과** — `PATCH /api/v1/namespaces/default/pods/<name>` 으로 *`spec.nodeName = <best>`* 채움.

**중요한 한 가지** — *Scheduler 는 *그 노드 에 *직접 명령 하지 않는다*. *그저 *Pod 의 nodeName 을 *적기만* 한다. *그 노드 의 Kubelet 이 *알아서 잡으러 옴*. *분산 시스템 의 *모든 조정 을 *etcd 의 한 줄 갱신* 으로 환원* 의 가장 노골 적 인 예.

### 2.6 *⑥ Pod 할당 감시 — Kubelet 이 자기 노드 의 Pod 를 발견*

**도식 표현** — *Kubelet 이 자기 노드 의 새 Pod 를 인지*.

**내부 메커니즘** :

- *각 노드 의 Kubelet 이 *기동 시 부터* `GET /api/v1/pods?fieldSelector=spec.nodeName=<thisNode>&watch=true`* 의 *Watch 유지 중*.
- *새 Pod 가 *자기 nodeName 으로 *지정 되면 *Watch 가 그 이벤트 즉시 push*.
- *Kubelet 의 *PodWorker 가 *그 Pod 를 *Sync 큐 에 넣음*.
- *Sync 루프* — *이 Pod 의 *원하는 상태 (PodSpec)* 와 *현재 상태 (이미 떠 있는 컨테이너 들)* 를 비교 → *차이 만큼 *액션*.

### 2.7 *⑦ 컨테이너 생성 — Kubelet → Container Runtime*

**도식 표현** — *Kubelet 이 *Docker (containerd / CRI-O)* 에 컨테이너 생성 요청*.

**내부 메커니즘** — *여기 가 *실제 OS 가 일하는 *유일한 순간*.

1. **Sandbox 생성** — *Pod 의 *네트워크 네임스페이스 + cgroup 컨테이너* 를 *먼저* 만든다. (pause 컨테이너 + Linux namespace).
2. **CNI 호출** — *`/opt/cni/bin/<plugin>` 실행*. *IP 할당, veth pair 생성, 라우팅 추가, NetworkPolicy 적용*. (Flannel / Calico / Cilium 의 *바이너리*).
3. **Volume Mount** — *PVC → PV → 노드 의 *실제 디스크 경로* mount*. CSI 드라이버 호출.
4. **이미지 Pull** — *컨테이너 이미지 가 노드 에 없으면 *registry 에서 *pull*. *layered FS (overlayfs) 로 *공유*.
5. **컨테이너 Start** — *각 컨테이너 별 로 *runc 호출 → 새 프로세스 (PID 1) → Pod 의 네트워크 / cgroup 안* 으로 *진입*.
6. **probe 시작** — *readinessProbe / livenessProbe* 를 *주기 적으로 호출*.

이 과정 의 *전체 가 *수 초 ~ 수십 초*. *이미지 pull 이 *가장 큰 변수*.

### 2.8 *⑧ Pod 상태 업데이트 — Kubelet → API Server*

**도식 표현** — *Kubelet 이 *API Server 에 *현재 상태* 보고*.

**내부 메커니즘** :

- *Kubelet 이 *주기 적으로* 또는 *상태 변화 시 즉시* `PATCH /api/v1/namespaces/.../pods/<name>/status` 호출*.
- *전송 내용* — *각 컨테이너 의 *Running / Waiting / Terminated 상태*, *Pod IP*, *startTime*, *conditions (Ready/PodScheduled/...)*.
- *etcd 에 *status 부분 만 갱신*.
- *API Server 가 *Watch 스트림 으로 *이 변경 을 *모든 관련 watcher 에 전파* — *Controller / Scheduler / kubectl get pods -w / Service Endpoints Controller / ...*.
- *Endpoints Controller* 가 *Pod 의 Ready=True* 를 보고 → *대응 Service 의 Endpoints 객체 에 *그 Pod IP 추가* → *kube-proxy 가 *iptables / IPVS 규칙 갱신* → *클라이언트 요청 이 *이 Pod 로 라우팅 시작*.

> *"Ready 되기 전 까지 *Service 가 안 보냄"* 의 *전체 chain* 이 *방금 8 줄* 안에 있음.

---

## 3. *8 단계 가 *드러내는 *6 가지 본질**

도식 만 보면 *그냥 흐름* 같지만, 자세히 보면 *분산 시스템 의 *모든 패턴* 이 들어 있다.

### 3.1 *Hub-and-Spoke* — *모두 가 *API Server 만 본다**

*Controller ↔ Scheduler ↔ Kubelet 사이 *직접 통신 이 *0*. *모두 *API Server 를 거친다*.

장점 :
- *컴포넌트 추가 의 *0 비용* — 새 Controller 가 와도 *기존 Watch 가 *그대로 동작*.
- *디버깅 의 *단일 지점* — *API Server 의 audit log* 가 *모든 행위 의 기록*.
- *권한 의 *단일 지점* — *RBAC* 가 *API Server* 에 만 있으면 됨.

단점 :
- *API Server 가 *병목*. *수만 개 객체 클러스터* 에서 *etcd 와 API Server 의 *수평 확장 + 성능 튜닝* 이 *생사*.
- *모든 변경 이 *왓치 스트림 으로 *모든 watcher 에 전파* → *대규모 클러스터* 에서 *네트워크 트래픽 부담*.

### 3.2 *Declarative + Reconciliation* — *명령 이 아닌 *상태**

*kubectl 이 *"Pod 를 만들어 라"* 가 아니라 *"이 ReplicaSet 이 *원하는 상태* 다"* 를 *선언*.

*Controller* 가 *desired vs current 의 *차이* 를 *지속 적으로 메움*.

이게 *왜 *우월한가* :
- *명령 형 (imperative)* 은 *놓치면 끝*. *"create 3 pods"* 명령 후 노드 하나 죽으면 *2 개 만 남고 *영구 적*.
- *선언 형 (declarative)* 은 *놓쳐도 *다음 reconcile 에서 *알아서 보충*. *자가 치유 의 기반*.
- *재시도 / 분산 / 부분 실패* 의 *모든 어려운 부분* 이 *"비교 후 *부족 분 만 만들기"* 로 *환원*.

### 3.3 *Level-Triggered + Idempotent* — *놓침 에 강한 설계**

*Edge-triggered (이벤트 변화) 가 아닌 *Level-triggered (현재 상태 비교)*.

- *Watch 가 *이벤트* 를 *주긴 함*. 하지만 *그 이벤트 는 *큐 의 트리거* 일 뿐.
- *실제 *동작 의 기준* 은 *현재 상태 의 *전체 스냅샷*.
- *그래서 *이벤트 *놓치면 *동기화 가 *늦어질 뿐 *틀어지지 않음*.
- *Controller 가 *같은 함수 *여러 번 호출 받아도 *결과 동일*.

### 3.4 *Optimistic Concurrency* — *락 없는 조정**

*etcd 의 *ResourceVersion* 으로 *낙관적 동시성 제어*.

- *컨트롤러 가 *Pod 업데이트* 할 때 *PATCH with resourceVersion=X*.
- *그 사이 *누가 먼저 수정* 해서 *현재 rv 가 X+1* 이면 *컨플릭트 (409)* 반환.
- *컨트롤러 가 *다시 읽고 *재시도*. *락 안 잡고도 *일관성 유지*.
- *수십 컴포넌트 가 *동시에 안전 하게 작업* 가능.

### 3.5 *Watch 의 *효율 적 전파* — *informer 의 *공유 캐시**

*수십 개 의 컨트롤러 가 *각자 *수만 개 객체* 를 watch 하면 *부하 폭발*.

해결 :
- *client-go 의 *SharedInformerFactory* — *같은 종류 의 객체 는 *한 번 watch 해서 *모든 컨트롤러 와 공유*.
- *로컬 캐시 (DeltaFIFO + ThreadSafeStore)* — *API Server 호출 없이 *바로 lookup*.
- *Resync* — *주기 적으로 *전체 상태 재 동기화* 로 *놓침 보정*.

### 3.6 *Asynchronous 의 *연쇄**

*8 단계* 가 *그 어디 에서도 *동기 적 RPC* 가 아니다*.

- *kubectl 응답* 은 *Pod 생성 응답* 이 아닌 *ReplicaSet 객체 저장 응답*.
- *Pod 가 *실제 떠 있는 지* 알려면 *별도 watch 또는 *poll*.
- *각 단계 의 시간 *완전 독립*. *Scheduler 가 *0.1 초 만에 결정* 해도 *Kubelet 의 이미지 pull* 이 *30 초 걸리면 *Pod 가 30 초 뒤 뜸*.

이 *비동기* 덕분 에 *클러스터 의 *수십만 객체* 가 *각자 의 속도 로 *흘러가도 *전체 가 일관 됨*.

---

## 4. *실패 시나리오 — *각 단계 가 *깨지면 *어떻게 되는가**

설계 의 우아함 은 *실패 모드* 에서 드러난다.

| 무엇이 죽으면 | 즉시 영향 | 자가 회복 메커니즘 |
|---|---|---|
| *kubectl* | *그 명령 만 실패* | *재실행 = 같은 결과* |
| *API Server* | *모든 조정 멈춤. 기존 Pod 는 살아 있음.* | *재기동 시 *etcd 에서 *상태 그대로 읽음*. *수십 ms 만에 *resume* |
| *etcd* | *진짜 큰 문제. 클러스터 *읽기 / 쓰기 불능*. 기존 Pod 는 *유일하게 *Kubelet 의 *마지막 본 상태로 *계속 돔*.* | *RAFT 의 *과반수 합의* 가 *2/3 살아 있으면 *복구*. 1/3 만 살면 *읽기 전용* |
| *Controller Manager* | *새 Pod 생성 안 됨. 기존 Pod 는 영향 없음.* | *Leader Election. 다른 *대기 인스턴스 가 *즉시 인계* |
| *Scheduler* | *Pending Pod 가 *영원히 Pending*. 기존 Pod 는 무관* | *Leader Election + *재기동 시 *기존 Pending 큐 다시 채움* |
| *Kubelet (특정 노드)* | *그 노드 의 *Pod 상태 보고 끊김*. *NodeCondition 의 *Ready=Unknown* 후 *NodeLease 만료* 시 *Pod 가 *다른 노드 로 *재 스케줄* | *Node 가 *돌아오면 *Watch 재연결 → *현재 상태 그대로 *resync* |
| *Container Runtime* | *그 노드 의 *컨테이너 안 뜸*. Kubelet 이 *반복 시도* | *재기동 시 *Kubelet 이 *desired 상태 로 *재실행* |

*핵심 통찰* — *어떤 단일 컴포넌트 가 죽어도 *데이터 손실 없음*. *최악 의 경우 *복구 시 까지 *지연 만* 발생. *이게 *Kubernetes 가 *production 의 *기본 인프라* 가 된 *결정 적 이유*.

---

## 5. *시간 척도 — *각 단계 가 *얼마나 걸리는가**

*"왜 그렇게 *Pod 생성 이 *느린가"* 의 *분해*. 일반 적 인 사례 기준.

| 단계 | 일반 시간 | 변동 요인 |
|---|---|---|
| ① kubectl → API Server | *10 ~ 50 ms* | *TLS 핸드셰이크, 네트워크 RTT* |
| ① 내부 — Auth + Admission + etcd write | *5 ~ 30 ms* | *Webhook 의 *외부 호출 지연 (악명 높음)* |
| ② Watch 이벤트 전파 | *수 ms* | *Informer 의 *resync 주기* |
| ③ Pod 객체 *N 개 생성 | *N × 10 ms* | *N 의 크기, etcd 쓰기 처리량* |
| ④ Scheduler watch 인지 | *수 ms* | *informer cache* |
| ⑤ 노드 선택 알고리즘 | *수 ms ~ 수십 ms* | *노드 수, 필터 / 점수 함수 수* |
| ⑥ Kubelet watch 인지 | *수 ms* | *informer cache* |
| ⑦-a Image pull | **수 초 ~ 수십 초** | *이미지 크기, 네트워크, registry 위치, 캐시* |
| ⑦-b Sandbox + CNI + Volume | *0.5 ~ 5 초* | *CNI 의 IP 할당, PV 의 형상* |
| ⑦-c 컨테이너 start + readinessProbe 통과 | *수 초 ~ 수 분* | *애플리케이션 의 *초기화 시간 (JVM 워밍업!)* |
| ⑧ status 업데이트 | *수 ms* | — |

> *전체 의 *80 ~ 95% 의 시간* 이 *⑦ 단계 (이미지 pull + 컨테이너 기동)*. *제어 평면 자체 는 *50 ms 이내 끝남*.

이게 *"제어 평면 의 부담 최소화"* 의 *결과*. *대부분 의 시간* 이 *애플리케이션 / 컨테이너 / 네트워크* 라는 *제거 불가능 한 *물리 작업* 에 쓰임. *Kubernetes 의 부하 는 *그 사이 의 *얇은 조정*.

---

## 6. *간과 하기 쉬운 *5 가지 진실**

### 6.1 *Deployment 가 *시퀀스 의 *맨 앞* 에 *하나 더 *있다**

*실제 운영* 에선 *kubectl 이 *Deployment 를 만든다*. *Deployment Controller* 가 *ReplicaSet 을 만든다*. *그 다음 부터 도식*.

```
Deployment → ReplicaSet → Pod → 컨테이너
```

*각 레이어 가 *자신 의 *Controller* 를 가진다*. *그래서 *롤링 업데이트 / 롤백 / 일시 정지* 가 *모두 *Deployment 객체 의 *spec 변경* 으로 환원*.

### 6.2 *Service / Endpoints 는 *별도 컨트롤러**

*Pod 가 떴다고 *바로 트래픽* 안 들어옴*. *Endpoints Controller* 가 *Service 의 셀렉터* 에 매칭 되는 *Ready=True Pod 의 IP* 를 *Endpoints 객체 에 등록* 해야 *kube-proxy 가 *iptables 갱신*.

*그래서 *Pod Running 뜨고도 *몇 초 동안 *503*. *readinessProbe 가 *그 사이* 의 *완충*.

### 6.3 *etcd 의 *크기 제한* — *암묵 적 인 *클러스터 상한**

*etcd 의 *권장 DB 크기* 8 GB*. *수만 객체 * 시작하면 *위험 영역*.

*Tip* — *ConfigMap / Secret 의 *과도한 분량* 이 *주범*. *큰 데이터 는 *PV / 외부 저장소*.

### 6.4 *Webhook 이 *제어 평면 의 *암살자**

*MutatingWebhook / ValidatingWebhook* 이 *모든 객체 생성 시 호출*. *Webhook 서버 가 *5 초 안 응답하면 *API Server 가 *전체 차단* 가능.

*고치는 방법* — *failurePolicy: Ignore* 또는 *timeoutSeconds: 짧게*. *우리 가 *6 월 8 일 settlement 사고* 에서 학습.

### 6.5 *Kubelet 이 *직접 etcd 접근 안 함**

*보안 / 분산 의 핵심*. *수천 개 노드 의 *Kubelet* 이 *모두 *etcd 에 직접* 하면 *etcd 가 죽음*.

*그래서 *API Server 가 *유일한 *etcd 게이트* + *수평 확장 의 단위*.

---

## 7. *이 설계 의 *철학 적 *기원**

### 7.1 *Borg / Omega 의 *15 년 학습**

*Google 의 Borg (2003~)* → *Omega (2013)* → *Kubernetes (2014)*.

*세 시스템 의 *공통 패턴* :
- *모든 조정 을 *중앙 저장소 (Borg-master 의 BorgFile)* 에 *환원*.
- *Watch + reconcile 의 *Control loop*.
- *Declarative spec*.

*Kubernetes 가 *처음 시도* 한 것 *없음*. *Borg 의 *오픈소스 화*.

### 7.2 *Unix 철학 의 *분산 시스템 판본**

*"do one thing well + compose"* 가 *컨트롤러 의 정신* :
- *각 컨트롤러 가 *한 자원 종류* 만 본다.
- *상호 통신 없음, *공유 저장소 통한 *데이터 흐름 만*.
- *조합 = 새 컨트롤러 추가 = 무한 확장*.

### 7.3 *CAP 의 *선택**

*Consistency vs Availability* — *Kubernetes 는 *CP* 선택.

*etcd 의 *RAFT 가 *과반수 합의 안 되면 *쓰기 거절*. *AP 였다면 *분할 시 데이터 분기*, *복구 시 *충돌 해결* 의 지옥.

*결과* — *제어 평면 의 *드물게 가용 불가능* 한 *대신* *상태 의 *항상 일관*.

---

## 8. *왜 이렇게 *복잡 한 것 을 *우리가 받아 들이는가**

*도식 의 *5 개 박스* — *처음 보면 *과도해 보임*.

*하지만 *이 5 개 의 분리* 가 *없으면* :

- *kubectl* 이 *직접 노드 에 SSH 해서 *컨테이너 띄움* — *권한 / 인증 / 일관성 / 재시도* 의 지옥.
- *Controller 가 직접 Scheduler 와 통신* — *둘 의 *생사 의존 + 진동*.
- *Scheduler 가 *Kubelet 에 *직접 명령* — *수천 노드 의 *N x M 망 구조*.

*하나 하나 의 분리 가 *15 년 운영 의 *피 의 결과*. *모두 가 *간단한 단일 책임 + 단일 게이트* 의 *우아함* 으로 *수렴*.

> *"왜 *간단한 컨테이너 띄우는 데 *이렇게 많은 부품* 인가"* 의 답 — *간단한 컨테이너 띄우기 가 *목표 가 아니다*. *수천 노드 의 *수만 컨테이너* 를 *수십 명 의 개발자 가 *동시에 안전 하게 운영 하는 것* 이 *목표*. *그 규모* 가 *이 분리 의 *비용 을 *완전히 회수*.

---

## 9. *결론 — *도식 한 장 이 *말하는 것**

처음 *8 단계 도식* 을 다시 본다.

- *왼쪽 의 *Master* — *원하는 상태 의 *수호자*. *etcd 의 진실, API Server 의 게이트, Controller 의 조정, Scheduler 의 결정*.
- *오른쪽 의 *Node* — *현재 상태 의 *실행 자*. *Kubelet 의 감독, Container Runtime 의 실행*.
- *둘 사이 의 *모든 통신* 이 *API Server 통과*. *직접 RPC 없음*.

*이 도식 의 *얇은 화살표 8 개* 가 *현대 클라우드 인프라 의 *근본*. *AWS EKS / Google GKE / Azure AKS / 내 K3s 홈랩* — *모두 *이 8 단계 의 변주*.

> *"Kubernetes 를 *공부 한다"* 는 것은 *YAML 의 100 가지 필드 를 외우는 것* 이 아니라 *이 8 단계 의 *각 화살표 가 *왜 그렇게 그어졌는지* 를 *깊이 이해 하는 것*.

*그러면 *kubectl 한 줄* 에 *내가 *무엇 을 부탁 하고 있는지*, *그 부탁이 *어떻게 *전 클러스터 에 *조용히 흘러가 *결국 컨테이너 가 뜨는지* 가 *눈 에 보인다*. *그 시야 가 *production 의 모든 디버깅 의 *시작점*.

---

## 다음 으로 *권 하는 읽기**

- *원작 의 *원작* — *Borg 논문 (2015 EuroSys)*. *"Large-scale cluster management at Google with Borg"*.
- *Kubernetes 의 *왜 그렇게 설계 했는지* — *Brendan Burns 의 *"Designing Distributed Systems"*.
- *내부 의 *진짜 코드* — *kubernetes/kubernetes 의 *`pkg/controller/` *디렉토리. *각 컨트롤러 가 *200 ~ 500 줄 의 *놀라운 단순함*.
- *Custom Controller 작성* — *Operator SDK / Kubebuilder*. *이 8 단계 패턴 의 *내 도메인 적용*.

*다음 글* — *이 8 단계 가 *수십 개 의 *real-world 에서 *어떻게 깨지고 *어떻게 디버깅 했는지* 의 *5 가지 사고 사례* — 곧.
