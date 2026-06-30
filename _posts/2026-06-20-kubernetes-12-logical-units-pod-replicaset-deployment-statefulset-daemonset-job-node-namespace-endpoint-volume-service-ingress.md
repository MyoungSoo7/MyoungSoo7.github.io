---
layout: post
title: "*쿠버네티스의 *논리적 단위 12종 — *Pod / ReplicaSet / Deployment / StatefulSet / DaemonSet / Job / Node / Namespace / Endpoint / Volume / Service / Ingress* 를 *한 장의 *지도* 로 *연결* 한다"
date: 2026-06-20 23:15:00 +0900
categories: [infrastructure, kubernetes, devops]
tags: [k8s, kubernetes, pod, replicaset, deployment, statefulset, daemonset, job, node, namespace, endpoint, volume, service, ingress, logical-units]
---

![쿠버네티스 의 논리적 단위 — Pod / ReplicaSet / Deployment / StatefulSet / DaemonSet / Job / Node / Namespace / Endpoint / Volume / Service / Ingress](/assets/images/k8s-12-logical-units.jpg)
*쿠버네티스 의 *논리적 단위* — 좌측 *워크로드 계열 (Pod / ReplicaSet / Deployment / StatefulSet / DaemonSet / Job)*, 우측 *컨텍스트 계열 (Node / Namespace / Endpoint / Volume / Service / Ingress)*. 이 12 개 가 *어떻게 *서로 참조* 하고 *어느 축* 에 *속하는지* 를 *분해* 한다.*

> *"쿠버네티스 *오브젝트 *너무 *많다"* 라고 *말하는 사람과 *"12 개 *논리 단위 가 *각자 *맡은 책임* 이 있다"* 라고 *말하는 사람은 *kubectl get 결과* 를 *완전히 *다르게 *읽는다*.
>
> 쿠버네티스는 *YAML 한 장 만 *보면 *컨테이너 *오케스트레이션* 이지만, *그 한 장 이 *살아 있게 하는 *논리 단위* 를 *세어 보면 *12 개* 다. 이 12 개 가 *워크로드 / 노드 / 네트워크 / 스토리지 / 격리* 라는 *5 가지 *축* 으로 *나뉘어* 서로를 *참조* 한다.
>
> 이 글은 *Pod, ReplicaSet, Deployment, StatefulSet, DaemonSet, Job, Node, Namespace, Endpoint, Volume, Service, Ingress* 가 *각자 *무엇을 책임지는지* + *어느 단위가 *어느 단위를 *참조* 하는지* + *왜 *분리* 되어야 했는지* 를 *런타임 관점* 에서 *분해* 한다.

---

## TL;DR

> 쿠버네티스의 *논리 단위* 는 **5 개 축** 으로 *정렬* 된다.
>
> 1. **워크로드 (Workload)** — *Pod (실행 단위)* → *ReplicaSet (개수 보장)* → *Deployment / StatefulSet / DaemonSet / Job (배포 정책)*
> 2. **노드 (Node)** — *Pod 가 *어디서 도는지*. *물리/가상 머신* 의 *논리 단위*.
> 3. **네트워크 (Network)** — *Service (가상 IP + 로드밸런싱)* → *Endpoint (실제 Pod IP 리스트)* → *Ingress (L7 라우팅 + TLS)*
> 4. **스토리지 (Storage)** — *Volume (Pod 수명을 넘는 영속성)*
> 5. **격리 (Isolation)** — *Namespace (멀티테넌시 + RBAC 단위)*
>
> *Pod 가 *맨 *위* 가 *아니다*. *Pod 는 *ReplicaSet 의 *결과물*, *ReplicaSet 은 *Deployment 의 *결과물*, *Deployment 는 *사람이 *선언* 하는 *최상위 *루트*. 옆에서는 *Service 가 *Endpoint 를 *통해 *Pod 의 *실시간 IP* 를 *추적* 하고, *Volume 이 *Pod 의 *데이터 수명* 을 *분리* 한다. 12 개 가 *각자 *왜 *분리* 되어야 했는지* 를 *이해* 하면 *kubectl describe* 한 줄 의 *의미* 가 *완전히 *달라진다*.

---

## 0. *왜 *논리 단위 를 *분리* 해서 *봐야 *하나*

### 0.1 *"docker run + nginx" 의 *세계 가 *왜 *터졌나*

전통적인 *컨테이너 운영* 에서는 *모든 책임 이 *한 명령어 안* 에 *섞여 있다*.

```bash
docker run -d \
  --name myapp \
  --restart=always \
  -p 8080:80 \
  -e DB_HOST=postgres.internal \
  -v /data:/var/data \
  myapp:1.2.3
```

이 *한 줄* 이 *섞은 책임* :

- *실행 단위* (`myapp` 컨테이너) → *Pod 가 *대신* 책임진다.
- *재시작 / 개수 보장* (`--restart=always` + *수동 N 회 *실행*) → *ReplicaSet 이 *대신* 책임진다.
- *배포 / 롤백 정책* (수동 `docker pull && docker stop && docker run`) → *Deployment 가 *대신* 책임진다.
- *어느 머신 에서 도는가* (운영자가 *수동 으로 SSH*) → *Node + Scheduler 가 *대신* 책임진다.
- *네트워크 (포트 매핑)* → *Service 가 *대신* 책임진다.
- *환경변수 / 시크릿* → *ConfigMap / Secret 이 *대신* 책임진다.
- *영속 저장소* → *Volume 이 *대신* 책임진다.
- *외부 진입* → *Ingress 가 *대신* 책임진다.

`docker run` 한 줄 은 *책임이 분리되지 않은 monolithic API*. 쿠버네티스는 이 한 줄 을 *12 개 의 *논리 단위* 로 *수직 / 수평 *분해* 한 것 이다.

### 0.2 *왜 *분해* 가 *프로덕션 운영* 의 *전제* 인가

분해되지 않은 책임은 *변경 비용* 이 *지수적* 으로 증가한다.

- *이미지 버전* 만 *바꾸고 싶다* → `docker run` 은 *컨테이너 전체 재생성*. 쿠버네티스는 *Deployment 의 `spec.template.spec.containers[].image`* 한 줄.
- *복제본 3 → 10* → `docker run` 은 *수동 9 회*. 쿠버네티스는 *Deployment 의 `spec.replicas: 10`* 한 줄.
- *노드 장애* → `docker run` 은 *수동 복구*. 쿠버네티스는 *ReplicaSet 이 *desired = 3*, *current = 2* 를 감지하여 *다른 Node 에 *재스케줄링*.
- *Stateful 서비스* (PostgreSQL, Kafka) → `docker run` 은 *수동 hostname / 디스크 매핑*. 쿠버네티스는 *StatefulSet + PV* 가 *순서·이름·디스크* 를 *자동 보존*.

12 개 의 *논리 단위* 는 *"무엇을 바꿀 때 *무엇을 함께 *바꿔야 하는가"* 의 *경계선* 이다. 이 경계 가 *없으면 *변경* 은 *재구축* 이 *된다*.

---

## 1. *Pod — *실행 단위* 이자 *동일 IP / 동일 호스트* 의 *최소 묶음*

### 1.1 *정의

> *Pod* 는 *1 개 이상* 의 *컨테이너* 가 *동일한 *네트워크 네임스페이스 (= 같은 IP / 포트 공간)* 와 *동일한 *볼륨 마운트 포인트* 를 *공유* 하는 *최소 *실행 단위*.

쿠버네티스 가 *컨테이너 를 *직접 다루지 않고 *Pod 를 다루는 이유* 는 *"실행 단위* 와 *공유 컨텍스트 단위* 를 *동일* 시키기 위해서* 다.

### 1.2 *왜 *Pod 안에 *여러 컨테이너* 가 *들어갈 수 있나*

흔히 *Pod = 컨테이너 1 개* 라고 *오해* 하지만, *Pod* 는 *사이드카 패턴* 을 *위해 *설계* 되었다.

- **주 컨테이너**: 비즈니스 로직 (e.g. `myapp:1.2.3`)
- **로깅 사이드카**: `fluent-bit` 가 *주 컨테이너 의 *stdout 로그* 를 *동일 IP * 동일 디스크* 로 *수집*
- **프록시 사이드카**: `envoy` (Istio) 가 *주 컨테이너 의 *트래픽* 을 *가로채 *mTLS / 트레이싱*
- **init 컨테이너**: *주 컨테이너 시작 전 *DB 마이그레이션* 실행

이들은 *반드시 *같은 노드 / 같은 IP* 에 있어야 *동작 한다 → *Pod 가 *묶음 단위* 가 되어야 하는 *근거*.

### 1.3 *Pod 의 *수명 = "재시작 되면 *다른 Pod"

*Pod 가 *재시작* 되면 *IP 가 *바뀐다*. 그래서 *Pod 를 *직접 호출* 하면 *프로덕션 에서 *깨진다*. 이 *불안정성* 이 *Service / Endpoint / Deployment* 가 *존재하는 *직접적 이유*.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    image: myapp:1.2.3
    ports:
    - containerPort: 8080
```

> *Pod* 단독 YAML 은 *프로덕션 에 *써서는 안 된다*. *재시작 정책 / 복제본 / 롤링 업데이트* 가 *전부 *없기 때문*.

---

## 2. *ReplicaSet — *Pod 개수 보장* 의 *상수 (constant)*

### 2.1 *정의

> *ReplicaSet* 은 *"이 라벨 셀렉터에 *매치되는 *Pod 가 *항상 *N 개* 살아 있어야 한다"* 를 *보장* 하는 *컨트롤러*.

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: myapp-rs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.2.3
```

### 2.2 *동작 원리 — *조정 루프 (Reconciliation Loop)*

ReplicaSet 컨트롤러는 *kube-apiserver 의 *Watch 스트림* 을 *지속적으로 구독* 하며 *다음 *조정 알고리즘* 을 *반복* 한다.

```
loop:
  desired = spec.replicas
  current = count(Pods matching spec.selector AND status.phase != Terminating)
  if current < desired:
    create (desired - current) Pods from spec.template
  elif current > desired:
    delete (current - desired) Pods (oldest first)
  else:
    no-op
```

> *Pod 가 *죽는 *원인* 과 *상관없이* (노드 장애, OOMKilled, 수동 삭제) *ReplicaSet 은 *desired 상태* 로 *수렴* 시킨다. 이게 *쿠버네티스 의 *self-healing* 본체*.

### 2.3 *왜 *직접 ReplicaSet 을 *쓰지 않나*

ReplicaSet 은 *롤링 업데이트* 를 *모른다*. *이미지 버전* 만 *바꾸려고 해도 ReplicaSet 은 *기존 Pod 를 *모두 죽이고 새 *Pod 를 *한꺼번에 생성* 한다 → *다운타임 발생*. 그래서 *현실 에서는 *Deployment 를 통해 *간접적으로 ReplicaSet 을 *제어* 한다.

---

## 3. *Deployment — *롤링 업데이트 + 롤백* 의 *선언적 *루트*

### 3.1 *정의

> *Deployment* 는 *"이 버전의 *Pod 가 *몇 개 *살아 있어야 한다"* 와 *"버전 변경 시 *어떻게 *교체* 할 것인가"* 를 *함께 선언* 하는 *최상위 *워크로드 오브젝트*.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1          # 동시에 1개 더 만들 수 있음 (3 → 최대 4)
      maxUnavailable: 0    # 절대 가용 Pod 수가 3 미만이 되면 안 됨
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.2.3
```

### 3.2 *Deployment → ReplicaSet → Pod 의 *3 단 계층*

```
Deployment (myapp)
├── ReplicaSet (myapp-7d4f8) ← old, image:1.2.2, replicas:0
└── ReplicaSet (myapp-9c5a1) ← new, image:1.2.3, replicas:3
                              ├── Pod myapp-9c5a1-abcde
                              ├── Pod myapp-9c5a1-fghij
                              └── Pod myapp-9c5a1-klmno
```

*이미지 가 *바뀌면 Deployment 는 *새 ReplicaSet 을 *만들고 *기존 ReplicaSet 의 *replicas 를 *점진적으로 *0* 으로 줄인다 → *maxSurge / maxUnavailable* 의 *제약* 아래에서 *무중단 롤링 업데이트*.

### 3.3 *롤백 가 *왜 *가능* 한가

`kubectl rollout undo deployment/myapp` 한 줄로 *이전 버전* 으로 *되돌릴 수 있다*. 이건 *Deployment 가 *과거 ReplicaSet 을 *replicas=0 으로 유지* 하기 때문 — *기록 보관* 의 *부산물*.

```bash
$ kubectl rollout history deployment/myapp
REVISION  CHANGE-CAUSE
1         kubectl apply --filename=v1.2.2.yaml
2         kubectl apply --filename=v1.2.3.yaml
3         kubectl apply --filename=v1.2.4.yaml
```

`spec.revisionHistoryLimit` (기본 10) 만큼 *과거 ReplicaSet 을 *보관* 한다. *과도하게 *늘리면 *etcd 부담* 이 *커진다*.

---

## 4. *StatefulSet — *Pod 에 *영구 이름 + 영구 디스크* 를 *부여*

### 4.1 *왜 *Deployment 로는 *부족 한가*

Deployment 가 *만드는 Pod 의 이름* 은 *랜덤 해시* (`myapp-9c5a1-abcde`). *재시작 되면 이름이 바뀌고*, *Pod 가 *어느 디스크에 연결* 되는지도 *고정되지 않는다*. 이게 *stateless 웹 서버* 에는 *문제없지만* *DB / Kafka / Zookeeper / Elasticsearch* 같은 *stateful* 워크로드 에는 *치명적*.

- *PostgreSQL primary 가 *재시작 되면 *같은 데이터 디렉토리* 에 *다시 붙어야 한다*.
- *Kafka broker-0* 은 *재시작 후에도 *broker-0* 이어야 *다른 broker 가 *알아본다*.

### 4.2 *StatefulSet 의 *3 가지 *보장*

1. **안정적인 *이름* (Stable Network Identity)**: `myapp-0`, `myapp-1`, `myapp-2` — *재시작 되어도 이름 유지*.
2. **안정적인 *디스크* (Stable Storage)**: 각 *Pod 가 *전용 PersistentVolumeClaim* 을 *가짐. *Pod 가 *다른 노드* 로 이동해도 *같은 PVC = 같은 데이터*.
3. **순차적 *생성 / 종료* (Ordered Deployment & Termination)**: `myapp-0` 이 *Ready* 되어야 `myapp-1` 시작. 종료는 *역순*.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres-headless    # Headless Service 필수 (DNS 등록용)
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

### 4.3 *DNS — *Pod 마다 *고유 도메인*

StatefulSet + Headless Service 의 조합은 *각 Pod 에 *고유 DNS 이름* 을 *부여* 한다.

- `postgres-0.postgres-headless.default.svc.cluster.local`
- `postgres-1.postgres-headless.default.svc.cluster.local`
- `postgres-2.postgres-headless.default.svc.cluster.local`

이게 *클러스터링 (replication, leader election)* 의 *전제*.

---

## 5. *DaemonSet — *모든 노드* 에 *Pod 를 *1 개씩*

### 5.1 *정의

> *DaemonSet* 은 *"이 라벨에 매칭되는 *모든 *Node 에 *이 Pod 가 *정확히 1 개씩* 떠 있어야 한다"* 를 *보장* 한다.

### 5.2 *현실 적 *사용처*

- **로그 수집**: `fluent-bit`, `filebeat`, `vector` — *각 노드 의 *컨테이너 stdout* 을 *수집*
- **노드 모니터링**: `node-exporter`, `cadvisor` — *각 노드 의 *CPU / 메모리 / 디스크* 메트릭 수집
- **네트워크 플러그인**: `cilium-agent`, `calico-node`, `flannel` — *각 노드 의 *CNI 데몬*
- **스토리지 플러그인**: `csi-node-driver` — *각 노드 에 *볼륨 마운트* 를 *위한 daemon*

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:3.0
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

### 5.3 *왜 *Deployment 로 못 *대체 하나*

Deployment 는 *"몇 개"* 를 지정한다. *DaemonSet 은 *"어디에 (어느 노드에)"* 를 지정한다. *노드가 *추가* 되면 *DaemonSet 은 *자동으로 *Pod 1 개* 를 *그 노드* 에 *생성* 한다 → *Deployment 의 *복제본 수* 로는 *표현 불가능* 한 *시맨틱*.

---

## 6. *Job / CronJob — *한 번 실행 / 주기적 실행*

### 6.1 *Job — *완료 보장*

> *Job* 은 *"이 Pod 가 *N 번 *성공적으로 완료 (exit 0)* 될 때까지 *재시도 한다"* 를 *보장* 한다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
spec:
  completions: 1
  backoffLimit: 4         # 4 회 실패하면 포기
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: myapp-migrator:1.2.3
        command: ["./migrate.sh"]
```

*핵심* : *Deployment 와 *반대*. Deployment 는 *Pod 가 *계속 살아 있게* 한다. Job 은 *Pod 가 *완료 되면 *종료 된 상태* 로 *남겨둔다* (재시작 X).

### 6.2 *사용처*

- *DB 마이그레이션* (Flyway, Liquibase)
- *배치 작업* (일일 리포트 생성)
- *ML 학습* (한 번 도는 학습 잡)
- *Helm chart 의 *post-install / post-upgrade hook*

### 6.3 *CronJob — *주기적 Job*

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-report
spec:
  schedule: "0 2 * * *"   # 매일 새벽 2 시
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: report
            image: report-generator:1.0
```

> *CronJob 은 *cron 표현식* 에 따라 *주기적으로 Job 을 *생성* 한다. *Linux cron* 의 *쿠버네티스 버전*.

---

## 7. *Node — *Pod 가 *실제로 도는 *물리/가상 머신*

### 7.1 *정의

> *Node* 는 *쿠버네티스 클러스터 의 *작업 머신* (물리 서버 또는 VM). *컨테이너 런타임 (containerd, CRI-O), kubelet, kube-proxy* 가 *떠 있다*.

### 7.2 *Node 가 *제공하는 *자원* 의 *논리 표현*

```bash
$ kubectl describe node worker-01
Capacity:
  cpu:                8
  ephemeral-storage:  200Gi
  memory:             32Gi
  pods:               110
Allocatable:
  cpu:                7800m       # 시스템 예약분 200m 차감
  memory:             30Gi        # 시스템 예약분 2Gi 차감
  pods:               110
```

*Scheduler 는 *Pod 의 *resources.requests* 를 *Allocatable* 과 *비교* 해서 *어느 Node 에 *Pod 를 *배치* 할지 *결정* 한다.

### 7.3 *Taint / Toleration — *노드 격리*

```bash
$ kubectl taint node gpu-node-01 nvidia.com/gpu=true:NoSchedule
```

이 한 줄 후 *gpu-node-01* 에는 *Toleration 이 *명시된 Pod 만 *떨어진다*. GPU 노드 / Spot 인스턴스 / 마스터 노드 분리 등에 사용.

### 7.4 *NodeSelector / Affinity — *선호 배치*

```yaml
spec:
  nodeSelector:
    disktype: ssd
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values: ["us-west-2a", "us-west-2b"]
```

> *Node* 는 *수동으로 *생성 되는 것* 이 *아니다*. *클러스터 에 *kubelet 이 *조인* 하면 *자동으로 Node 오브젝트 가 *생성* 된다. *Node 자체는 *쿠버네티스 의 *경계 바깥* 이고, *Node 오브젝트* 는 *그 머신 을 *클러스터 의 *논리 단위* 로 *추상화* 한 것.

---

## 8. *Namespace — *멀티테넌시 / RBAC / 자원 격리* 의 *경계*

### 8.1 *정의

> *Namespace* 는 *클러스터 내부 의 *가상 클러스터*. *이름 충돌 격리 + RBAC 적용 단위 + ResourceQuota 적용 단위*.

### 8.2 *기본 Namespace*

- `default`: *명시하지 않은 모든 오브젝트*
- `kube-system`: *coredns, kube-proxy, kubelet 등 *시스템 컴포넌트*
- `kube-public`: *모든 사용자 가 *읽을 수 있는* 공개 영역
- `kube-node-lease`: *Node lease 오브젝트* (kubelet heartbeat 최적화)

### 8.3 *실무 적 *사용처*

- **환경 격리**: `dev`, `staging`, `prod` Namespace 분리
- **팀 격리**: `team-payments`, `team-ml`, `team-platform`
- **자원 한도**: ResourceQuota 로 *Namespace 별 CPU / 메모리 / Pod 수* 제한

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-payments-quota
  namespace: team-payments
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "100"
```

### 8.4 *Namespace 가 *격리* 하지 *못하는 것*

- **Node**: Node 는 *전체 클러스터* 자원, *Namespace 에 속하지 않음*.
- **PersistentVolume**: PV 는 *클러스터 자원*. PVC 만 *Namespace 에 속한다*.
- **CustomResourceDefinition (CRD)**: CRD 자체는 *클러스터 자원*.
- **네트워크**: 기본 적으로 *모든 Namespace 의 Pod 가 *서로 통신 가능*. 격리 하려면 *NetworkPolicy* 별도 적용.

> 흔한 오해 : *Namespace = 보안 경계*. *아니다*. *Namespace 는 *조직적 경계 + RBAC 단위*. *진짜 보안 경계 (네트워크 / 노드)* 는 *별도 정책* 이 *필요* 하다.

---

## 9. *Service — *Pod 묶음에 *고정 IP / DNS 부여*

### 9.1 *왜 *Service 가 *필요 한가*

Pod IP 는 *재시작 마다 *바뀐다*. *클라이언트가 *Pod IP 를 *직접 호출 하면 *깨진다*. Service 는 *"이 라벨에 매칭되는 Pod 들 의 *가상 대표 IP / DNS"* 를 *제공* 한다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp           # 이 라벨을 가진 Pod 를 모두 대상
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

이 *YAML* 한 장 후 *클러스터 내부* 에서는 *DNS 로 `myapp.default.svc.cluster.local`* 을 *호출* 하면 *항상 *살아있는 Pod 중 하나* 로 *로드밸런싱* 된다.

### 9.2 *4 가지 *Service 타입*

| 타입 | 노출 범위 | 사용처 |
|---|---|---|
| **ClusterIP** | 클러스터 내부만 | 내부 마이크로서비스 간 통신 (기본값) |
| **NodePort** | 각 Node 의 *고정 포트* | 외부 노출 (개발용 / 임시) |
| **LoadBalancer** | 클라우드 LB (ELB, GCP LB) | 외부 노출 (프로덕션) |
| **ExternalName** | DNS CNAME | 외부 서비스를 *내부 이름* 으로 추상화 |

### 9.3 *kube-proxy 의 *역할 — iptables / IPVS 룰*

`Service.spec.clusterIP` 는 *진짜 IP 가 아니다*. *kube-proxy* 가 *각 Node 의 *iptables (또는 IPVS) 룰* 에 *"이 가상 IP 로 가는 트래픽 을 *현재 살아있는 Pod IP 중 하나* 로 *DNAT"* 룰을 *주입* 한다. *Service 가 *마법* 처럼 *작동* 하는 *원리*.

### 9.4 *Headless Service — clusterIP: None*

```yaml
spec:
  clusterIP: None
  selector:
    app: postgres
```

*가상 IP 가 *없고* *DNS 가 *Pod IP 리스트* 를 *직접 반환* 한다. *StatefulSet* 과 함께 *각 Pod 의 *개별 DNS* 를 *부여* 할 때 *필수*.

---

## 10. *Endpoint / EndpointSlice — *Service 가 *추적하는 *실시간 Pod IP 리스트*

### 10.1 *Service 와 *Endpoint 의 *관계*

흔히 *Service 가 *Pod 를 *직접 *바라본다* 고 *오해* 하지만, *실제로는 *중간에 *Endpoint 오브젝트* 가 *있다*.

```
Service (myapp, selector: app=myapp)
  ↓ (controller 가 자동 생성)
Endpoint (myapp)
  - 10.244.1.5:8080
  - 10.244.2.7:8080
  - 10.244.3.2:8080
  ↑ (selector 매칭되는 Pod IP)
Pods (app=myapp)
```

*Endpoint Controller 는 *Pod 의 *상태 변화 를 *감지* 하여 *Endpoint 의 *IP 리스트 를 *갱신* 한다. *kube-proxy 는 *Service 가 *아닌 *Endpoint* 를 *Watch* 하여 *iptables 룰* 을 *동기화* 한다.

### 10.2 *왜 *분리* 되어 *있나*

- *Service 는 *불변* (가상 IP, 포트, 셀렉터). *재배포 해도 *바뀌지 않는다*.
- *Endpoint 는 *가변* (Pod 가 *추가 / 삭제 될 때마다 *갱신*).
- *분리하지 않으면 *Service 오브젝트 가 *고빈도로 *업데이트* 된다 → *etcd 부담 / Watch 비용 증가*.

### 10.3 *EndpointSlice — *대규모 클러스터* 의 *최적화*

기존 *Endpoint 는 *한 Service 에 *대응하는 모든 IP 를 *단일 오브젝트* 에 *담는다*. *수천 개 Pod* 가 *매칭* 되면 *Endpoint 오브젝트 가 *거대해지고 *Watch 트래픽 이 *폭발* 한다.

*EndpointSlice* (1.21+ stable) 는 *Endpoint 를 *100 개 단위* 로 *나눠* *부분 업데이트* 만 *전파* 한다. *현재 *Service 는 *EndpointSlice 를 *기본 으로 사용*, *Endpoint 는 *하위 호환용*.

### 10.4 *외부 서비스 를 *Service 처럼 *부르기 — *ExternalName + 수동 Endpoint*

```yaml
# Selector 가 없는 Service
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  ports:
  - port: 5432
---
# 수동 Endpoint 생성
apiVersion: v1
kind: Endpoints
metadata:
  name: external-db          # Service 와 이름 동일해야 함
subsets:
- addresses:
  - ip: 10.0.0.42
  ports:
  - port: 5432
```

*외부 DB* 를 *내부 Service 처럼 *부를 수 있게* 하는 *클래식 패턴*.

---

## 11. *Volume — *Pod 수명 을 *넘는 *스토리지 추상화*

### 11.1 *왜 *Volume 이 *필요 한가*

*컨테이너 내부 파일시스템* 은 *Pod 삭제 시 *소실*. *재시작 시 *초기 이미지 상태로 복원*. *DB / 파일 업로드 / 로그* 가 *유지* 되려면 *Pod 수명 외부* 의 *저장소* 가 *필요*.

### 11.2 *Volume 의 *3 단 계층*

```
PersistentVolume (PV)       ← 클러스터 자원 (관리자 또는 StorageClass 가 생성)
  ↑ binding
PersistentVolumeClaim (PVC) ← Namespace 자원 (개발자가 신청)
  ↑ mount
Pod                          ← PVC 를 마운트
```

> *PV / PVC 분리* 는 *"관리자 = 디스크 제공자, 개발자 = 디스크 요청자"* 라는 *역할 분리*.

### 11.3 *StorageClass — *동적 프로비저닝*

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
reclaimPolicy: Retain
```

*PVC 가 *StorageClass 를 *지정* 하면 *해당 클래스 의 *프로비저너* 가 *자동으로 PV 를 생성* 한다. AWS EBS, GCP PD, Ceph, NFS 등 다양한 백엔드 지원.

### 11.4 *AccessMode — *동시 접근 정책*

| Mode | 의미 |
|---|---|
| **ReadWriteOnce (RWO)** | *하나의 Node 에서 *RW 마운트*. 대부분의 블록 스토리지 (EBS) |
| **ReadOnlyMany (ROX)** | *여러 Node 에서 *RO 마운트*. 정적 콘텐츠 배포 |
| **ReadWriteMany (RWX)** | *여러 Node 에서 *RW 마운트*. NFS, EFS, CephFS |
| **ReadWriteOncePod (RWOP)** | *하나의 Pod 에서만 *RW*. 더 엄격한 격리 (1.22+) |

### 11.5 *임시 볼륨* — *emptyDir, hostPath*

- **emptyDir**: *Pod 수명 동안만 *존재*. *재시작 되면 *소실*. *컨테이너 간 데이터 공유* (사이드카) 용
- **hostPath**: *Node 의 *호스트 파일시스템* 을 *마운트*. *DaemonSet (로그 수집, 모니터링)* 에서 *주로 사용*. *프로덕션 워크로드 에서는 *기피* (Pod 이동 시 데이터 손실, 보안 위험)

---

## 12. *Ingress — *L7 라우팅 + TLS 종단* 의 *최외각*

### 12.1 *왜 *Service 만 으로는 *부족 한가*

*Service (LoadBalancer)* 는 *L4 (TCP/UDP) 로드밸런싱* 만 *제공* 한다. *현실 의 *웹 트래픽* 은 *L7 (HTTP/HTTPS)* 이고 *다음 *요구사항* 이 *추가* 된다.

- *호스트 기반 라우팅*: `api.example.com → api-service`, `app.example.com → app-service`
- *경로 기반 라우팅*: `/api → backend-service`, `/static → frontend-service`
- *TLS 종단*: HTTPS 인증서 를 *Ingress 에서 *terminate*
- *Service 별 *LoadBalancer 분산 방지*: 클라우드 LB 는 *비싸다* (월 $20+/개). *Ingress 1 개로 N 개 Service 통합*.

### 12.2 *Ingress 정의*

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: backend-v1
            port:
              number: 80
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: backend-v2
            port:
              number: 80
```

### 12.3 *Ingress vs Ingress Controller*

- **Ingress** (오브젝트): *라우팅 규칙* 의 *선언적 정의* (위 YAML)
- **Ingress Controller** (구현): *실제로 *트래픽 을 *처리* 하는 *프록시*. *nginx-ingress, Traefik, HAProxy, Istio Gateway, AWS ALB Controller, GCP GCLB Controller* 등.

*Ingress 오브젝트 만 *생성* 하고 *Controller* 가 *없으면 *아무 일도 일어나지 않는다*. *Controller 는 *클러스터 마다 *최소 1 개* 설치 필요.

### 12.4 *Gateway API — *Ingress 의 *후계자*

Ingress 는 *기능 부족* (TCP/UDP 지원 X, 동적 라우팅 제한, *주석 (annotation) 으로 *벤더 확장 의존*) 이 *비판* 받아 *Gateway API* 가 *2023 GA*. 표준 화 된 *HTTPRoute / TCPRoute / GRPCRoute* 등 *세분화된 *리소스* 제공. *신규 프로젝트* 는 *Gateway API* 검토 권장.

---

## 13. *전체 *그림 — *12 개 *논리 단위 의 *상호 참조*

```
                          ┌────────────────────────────────────┐
                          │  Namespace (격리 경계)              │
                          └────────────────────────────────────┘
                                          │
                                          │ scope
                                          ↓
   ┌─────────────────────────────────────────────────────────────┐
   │                       Workload 축                            │
   │                                                              │
   │  Deployment ──── manages ──→ ReplicaSet ──── manages ──→ Pod │
   │  StatefulSet ─── manages ──→ Pod (named, with PVC)           │
   │  DaemonSet ───── manages ──→ Pod (one per Node)              │
   │  Job / CronJob ─ manages ──→ Pod (run-to-completion)         │
   └─────────────────────────────────────────────────────────────┘
                                          │
                                          ↓
                                    runs on (스케줄링)
                                          │
                                          ↓
                          ┌────────────────────────────┐
                          │   Node 축 (물리/가상 머신)  │
                          └────────────────────────────┘
                                          │
                                          ↑ mount
                          ┌────────────────────────────┐
                          │   Storage 축 (Volume)       │
                          │   PV ← bind ─ PVC ← mount ─ Pod │
                          └────────────────────────────┘
                                          │
                                          ↓
                          ┌────────────────────────────────────┐
                          │   Network 축                        │
                          │                                     │
                          │   Ingress ── routes ──→ Service     │
                          │   Service ── tracks ──→ Endpoint    │
                          │   Endpoint ── points ──→ Pod IP     │
                          └────────────────────────────────────┘
```

### 13.1 *변경 시 *어떤 단위 가 *어떤 단위 를 *건드리는가*

| 변경 액션 | 직접 변경 단위 | 간접 영향 단위 |
|---|---|---|
| 이미지 버전 업 (`v1.2 → v1.3`) | Deployment | ReplicaSet (새 RS 생성) → Pod (새 Pod 생성) |
| 복제본 수 (3 → 5) | Deployment.replicas | ReplicaSet.replicas → Pod (+2 생성) → Endpoint (+2 IP) |
| Pod 라벨 추가 | Deployment.template.labels | Service.selector 매칭 변화 → Endpoint 갱신 |
| Service 포트 변경 | Service.spec.ports | kube-proxy iptables 룰 갱신 → 모든 Node |
| 새 Node 조인 | (자동) Node 오브젝트 생성 | DaemonSet (자동 Pod 생성), Scheduler (배치 후보 확장) |
| PVC 추가 | PVC | StorageClass → PV 동적 생성 → Pod 마운트 가능 |
| Namespace ResourceQuota 변경 | ResourceQuota | 향후 Pod 생성 시 제한 적용 (기존 Pod 영향 X) |
| Ingress 호스트 추가 | Ingress.spec.rules | Ingress Controller 의 nginx.conf 재로드 |

> 한 단위 가 *바뀌면 *어떤 단위 가 *연쇄적으로 갱신* 되는지* 를 *예측 할 수 있어야 *프로덕션 변경 의 *위험 평가* 가 *가능* 하다. 이게 *12 개 *논리 단위 를 *외워야 하는 *진짜 이유*.

---

## 14. *정리

### 14.1 *5 축 *재배열*

| 축 | 단위 | 한 줄 책임 |
|---|---|---|
| **Workload** | Pod | 동일 IP / 공유 컨텍스트 의 *최소 실행 묶음* |
| Workload | ReplicaSet | *Pod 개수 보장* (self-healing 의 본체) |
| Workload | Deployment | *롤링 업데이트 / 롤백* 의 *선언적 루트* |
| Workload | StatefulSet | *Pod 이름 + 디스크 + 순서* 보장 (stateful) |
| Workload | DaemonSet | *모든 Node 에 *1 개씩* 보장 |
| Workload | Job / CronJob | *완료 보장 / 주기 실행* |
| **Node** | Node | *물리/가상 머신* 의 *논리 표현* |
| **Network** | Service | *Pod 묶음 의 *가상 IP + DNS* |
| Network | Endpoint(Slice) | *Service 의 *실시간 Pod IP 리스트* |
| Network | Ingress | *L7 라우팅 + TLS* 의 *최외각* |
| **Storage** | Volume (PV/PVC) | *Pod 수명 외부* 의 *영속 저장소* |
| **Isolation** | Namespace | *멀티테넌시 / RBAC / 자원 격리* 의 *경계* |

### 14.2 *시니어가 *kubectl get* 을 *읽는 *방식*

```bash
$ kubectl get deploy,rs,po,svc,ep,ing -n team-payments
```

*초보* : 결과 가 *너무 많다* 고 *느낀다*.
*시니어* : *Deployment* 가 *루트*, *ReplicaSet* 이 *중간*, *Pod* 가 *말단*, *Service* 가 *옆에서 *Pod 를 *바라보고*, *Endpoint* 가 *Service 의 *실시간 매핑*, *Ingress* 가 *Service 의 *외부 진입점* — *5 줄 의 *논리 흐름* 을 *바로 본다*.

### 14.3 *마지막 한 마디

> 쿠버네티스를 *"오브젝트 종류가 많아 어렵다"* 고 *느낀다면 *시각 의 *문제* 가 *아니라 *분류* 의 *문제* 다. *12 개 의 *논리 단위* 가 *5 개 의 *축* 에 *어떻게 *흩어져* 있고 *서로 *어떻게 *참조* 하는지* 를 *한 장* 에 *그릴 수 있게 되면 *kubectl 명령어* 도, *YAML 한 장* 도, *프로덕션 장애* 도 *완전히 *다른 의미* 로 *읽힌다*.
>
> *Pod 가 *맨 위가 아니라 *맨 *밑* 에 있고, *Deployment 가 *맨 *위*, *Service 가 *옆에서 *Endpoint 를 *통해 *Pod 를 *바라보고*, *Volume 이 *아래에서 *Pod 의 *데이터 수명 을 *분리* 한다는 *그림* — *이게 *쿠버네티스 의 *논리적 단위* 다.
