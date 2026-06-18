---
layout: post
title: "*쿠버네티스를 *바라보는 *방법* — *Pod 는 *Deployment / ReplicaSet / Service / ConfigMap / Secret / Volume* 위에서 *돈다*"
date: 2026-06-18 18:30:00 +0900
categories: [infrastructure, kubernetes, devops]
tags: [k8s, kubernetes, deployment, replicaset, service, configmap, secret, volume, pod, runtime-perspective]
---

> *"Pod 가 *그냥 *컨테이너 다"* 라고 *생각하는 사람과 *"Pod 가 *그 모든 것 위에서 *돈다"* 라고 *생각하는 사람은 *클러스터 를 *완전히 다르게 *본다*.
>
> 쿠버네티스는 *Pod 하나 만 *보면 *YAML 한 장* 이지만, *Pod 가 *살아 있게 하는 *모든 것* 을 *보면 *6 개 의 *서로 다른 *층* 이 있다. 그 6 개 가 *각자 *책임* 을 *나눠지고 *맞물려야* *Pod 가 *production 에서 돈다*.
>
> 이 글은 *Deployment / ReplicaSet / Service / ConfigMap / Secret / Volume* 이 *Pod 위 / 옆 / 아래* 에서 *각자 *무엇을 책임지는지* 를 *런타임 관점* 에서 *분해* 한다.

---

## TL;DR

> *Pod 는 *맨 *위* 가 *아니라* *맨 *밑* 이다. *Pod 가 *어떻게 도는지* 를 *선언* 하는 것은 *Deployment*, *몇 개를 유지* 하는지 보장하는 것은 *ReplicaSet*, *외부에서 접근* 하는 길은 *Service*, *환경 변수 / 설정* 을 *외부에서 주입* 하는 것은 *ConfigMap*, *비밀 정보* 는 *Secret*, *영속 저장소* 는 *Volume*. *Pod 자체는 *이 모든 것의 *결과물* 이고 *받는 쪽* 이다. *6 개 의 *층* 이 *왜 *분리* 되어야 했는지* 를 *이해하면* *YAML 한 장 으로 *production 운영* 이 *가능* 해진다.

---

## 0. *왜 *층을 분리해서 봐야 하나*

### 0.1 *"docker run" 의 *세계 가 *왜 *터졌나*

전통적인 *컨테이너 운영* 은 *한 명령어 안에 *모든 것* 이 *섞여 있다*.

```bash
docker run -d \
  --name myapp \
  --restart=always \                       # ← 재시작 정책
  -p 8080:80 \                              # ← 네트워크
  -e DATABASE_URL=$URL \                    # ← 환경변수
  -e DB_PASSWORD=$PWD \                     # ← 시크릿
  -v /data/myapp:/var/data \                # ← 볼륨
  myapp:1.2.3
```

이 한 줄이 *섞은 책임* :
1. *워크로드 선언* (`myapp:1.2.3`)
2. *몇 개 실행* (1 개)
3. *재시작 정책* (`--restart`)
4. *네트워크 노출* (`-p`)
5. *설정* (`-e DATABASE_URL`)
6. *시크릿* (`-e DB_PASSWORD`)
7. *볼륨* (`-v`)

→ *7 가지 책임이 *한 줄* 에 *섞이면* *바꾸기 위해 *전부 재실행*. *재현 / audit / 협업* 어려움.

### 0.2 *Kubernetes 가 *7 가지 책임을 *6 개 리소스 로 *분리*

- *어떻게 도는지* → **Deployment** (declarative spec)
- *몇 개 도는지* → **ReplicaSet** (count guarantee)
- *외부 진입로* → **Service** (network endpoint)
- *설정 주입* → **ConfigMap** (non-secret config)
- *시크릿 주입* → **Secret** (sensitive data)
- *영속 저장소* → **Volume** (storage abstraction)
- *결과로 *돌아가는 *프로세스* → **Pod**

→ *각 리소스가 *각자 *책임* 만 *지면* *바꾸기 / 재현 / 협업 / 추적* 이 *각각 가능*.

---

## 1. *층 1 — *Deployment : *"어떻게 *돌릴지* 를 *선언* 한다"*

### 1.1 *Deployment 의 *진짜 역할*

> *Deployment 는 *컨테이너를 *돌리는 *명령어 가 *아니다*. *"이런 상태가 되도록 *유지해 줘"* 라는 *선언* 이다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 3                                    # ← 이 개수를 유지해 줘
  selector:
    matchLabels:
      app: order-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                                # ← 배포 시 한 번에 1 개 더
      maxUnavailable: 0                          # ← 한 개도 다운 안 됨
  template:                                       # ← Pod 의 spec (틀)
    metadata:
      labels:
        app: order-service
    spec:
      containers:
        - name: app
          image: ghcr.io/lms/order-service:v1.42.0
          ports:
            - containerPort: 8088
```

### 1.2 *선언적 (declarative) 의 *진짜 의미*

- *명령형 (imperative)* — *"이 명령을 실행해"* (`docker run ...`)
- *선언형 (declarative)* — *"이런 상태가 되도록 유지해"*

→ Deployment 가 *대단한 게 *아니다*. *Deployment 가 *대단한 것은 *Controller 가 *현재 상태를 *읽고 *원하는 상태와 *비교 하고 *조정* 하는 *reconciliation loop* 다.

```
[Desired state] replicas: 3
[Current state] running pods: 2   ← 1 개가 죽었음
       ↓
[Controller] 차이 = +1 → ReplicaSet 에게 Pod 1 개 추가 요청
       ↓
[After]     running pods: 3
```

→ *내가 *잘 시간에* *클러스터가 *알아서* *Pod 를 *살린다*. 이게 *선언적 운영* 의 *힘*.

### 1.3 *RollingUpdate 의 *진짜 가치*

```
[Before]  v1.0 × 3
[Step 1]  v1.0 × 3 + v1.1 × 1  (maxSurge 1)
[Step 2]  v1.0 × 2 + v1.1 × 1  (1 개 종료, maxUnavailable 0 보장)
[Step 3]  v1.0 × 2 + v1.1 × 2
[Step 4]  v1.0 × 1 + v1.1 × 2
[Step 5]  v1.0 × 1 + v1.1 × 3
[Step 6]  v1.1 × 3
```

→ *한 번도 *0 개로 *떨어진 적 *없음*. *무중단 배포* 가 *기본 동작*.

---

## 2. *층 2 — *ReplicaSet : *"몇 개 가 *돌고 있는지 *보장 한다"*

### 2.1 *Deployment 와 ReplicaSet 의 *진짜 관계*

> *Deployment 는 *직접 Pod 를 *만들지 *않는다*. *ReplicaSet 을 *만든다*. *ReplicaSet 이 *Pod 를 *만든다*.

```
Deployment  ─────[manages]─────►  ReplicaSet  ─────[manages]─────►  Pod × N
   (선언)                              (개수 보장)                       (실행)
```

### 2.2 *왜 *분리되어 있나 — *RollingUpdate 의 *비밀*

```bash
$ kubectl get rs
NAME                       DESIRED   CURRENT   READY   AGE
order-service-7f9d6b8c5    3         3         3       5m    # v1.1 (현재)
order-service-6c8b9d4f2    0         0         0       30m   # v1.0 (이전)
order-service-5a7c8e3d1    0         0         0       2h    # v0.9 (그 이전)
```

- *Deployment 가 *RollingUpdate 할 때 *새 ReplicaSet 을 *만들고 *카운트 를 *옮긴다*
- *옛 ReplicaSet 은 *카운트 0 으로 *남는다*
- → `kubectl rollout undo deployment/order-service` 시 *카운트 만 *역전* — *옛 ReplicaSet 으로 *즉시 롤백*

### 2.3 *ReplicaSet 이 *보장 하는 것 — *Single Source of Truth*

```
Desired replicas: 3
       │
       ▼
ReplicaSet Controller 가 watch:
  - Pod 1 죽음 → 자동 재생성
  - Pod 4 가 어디서 생김 (수동 kubectl run?) → 1 개 삭제
  - 노드 fail → Pod 다른 노드로 재스케줄
```

→ *"내가 *원하는 개수* 가 *유지된다"* 의 *유일한 책임자*.

---

## 3. *층 3 — *Service : *"Pod 에 *접근하는 *길* 이다"*

### 3.1 *Pod 의 *IP 가 *왜 *못 믿을 *주소 인가*

> Pod 는 *죽고 *살아나고 *옮겨 다닌다*. *Pod IP* 는 *그때마다 *바뀐다*. *Pod 끼리 *IP 로 *직접 통신* 하면 *깨진다*.

```
[10:00] order-service Pod    IP: 10.42.1.5   ← Pod 죽음
[10:01] order-service Pod    IP: 10.42.2.8   ← 다른 노드에 새로 생김
[10:02] order-service Pod    IP: 10.42.0.3   ← 또 옮김
```

→ payment-service 가 *10.42.1.5 로 직접 호출* 했으면 *3 초마다 *깨진다*.

### 3.2 *Service 는 *Pod 의 *안정적인 *얼굴 이다*

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  selector:
    app: order-service        # ← 이 라벨의 모든 Pod 에 부하분산
  ports:
    - port: 8088
      targetPort: 8088
  type: ClusterIP              # ← 클러스터 내부 안정 IP
```

- *Service 의 IP / DNS (order-service.default.svc.cluster.local)* 는 *Pod 가 *바뀌어도 *동일*
- 내부적으로 *iptables / IPVS / eBPF* 가 *실시간 부하분산*
- *Pod 가 *죽으면 *그 Pod 는 *endpoint 에서 *제거* + *새 Pod 가 *생기면 *추가*

### 3.3 *Service 의 *3 가지 type*

| Type | 용도 | 비유 |
|---|---|---|
| *ClusterIP* | 클러스터 내부 통신 | 사내 내선 번호 |
| *NodePort* | 노드 IP : 고정 포트 | 사내 회의실 외부 직통 번호 |
| *LoadBalancer* | 외부 IP 할당 | 회사 대표 번호 |

→ MSA 끼리는 *대부분 ClusterIP*. *외부 노출 은 *Ingress (별도 리소스) + ClusterIP* 가 *현대적 패턴*.

### 3.4 *Service Discovery 의 *우아함*

```java
// Spring Boot 코드 — Service 만 알면 됨
@Value("${ORDER_SERVICE_URL:http://order-service:8088}")
private String orderServiceUrl;

// Pod IP 가 매 분 바뀌어도 코드는 영원히 그대로
```

→ *애플리케이션 코드 가 *Pod 의 *생사 를 *알 필요 없다*. *Service 가 *그 추상화 를 *대신* 한다.

---

## 4. *층 4 — *ConfigMap : *"설정을 *외부에서 *주입* 한다"*

### 4.1 *왜 *환경별 *설정 을 *코드에 *못 박으면 *안 되나*

```java
// 안티패턴 — 환경별로 빌드해야 함
@Value("${database.url:jdbc:postgresql://prod-db:5432/orders}")  // ← 코드에 박힘
```

- *staging 에서 *돌리려면* *다시 빌드*
- *DB 호스트 가 *바뀌면* *다시 빌드*
- *image tag 가 *환경마다 *달라짐* → *재현 불가능*

### 4.2 *ConfigMap : *image 는 *하나, *설정 만 *다르게*

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: order-service-config
data:
  application.yml: |
    spring:
      datasource:
        url: jdbc:postgresql://postgres:5432/orders
      kafka:
        bootstrap-servers: redpanda:9092
    settlement:
      commission-rate: 0.03
```

→ Pod 에 *주입* 하는 *3 가지 방식* :

```yaml
# 1. 환경변수
env:
  - name: DATABASE_URL
    valueFrom:
      configMapKeyRef:
        name: order-service-config
        key: database.url

# 2. 파일 마운트 (Spring Boot 가 application.yml 자동 인식)
volumeMounts:
  - name: config
    mountPath: /config
volumes:
  - name: config
    configMap:
      name: order-service-config

# 3. envFrom 전체 주입
envFrom:
  - configMapRef:
      name: order-service-config
```

### 4.3 *ConfigMap 의 *진짜 가치*

- *image 는 *production 전용 *1 개* — 빌드 *1 번* 으로 *모든 환경 배포*
- *설정 만 *환경별로 *다른 ConfigMap*
- *설정 변경 = *Pod 재시작 만* (이미지 빌드 X)

```
[Build]   image v1.42.0   (한 번 빌드)
   ↓
[Dev]     image v1.42.0 + dev-config        → Pod
[Staging] image v1.42.0 + staging-config    → Pod
[Prod]    image v1.42.0 + prod-config       → Pod
```

→ *같은 image* 가 *환경마다 *다른 옷* 을 *입고 돈다*. *재현 가능* 의 *핵심*.

---

## 5. *층 5 — *Secret : *"비밀번호 / 키 / 토큰 을 *분리* 한다"*

### 5.1 *Secret = *ConfigMap 의 *민감 버전*

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: order-service-secrets
type: Opaque
data:
  POSTGRES_PASSWORD: c3VwZXItc2VjcmV0LXBhc3N3b3Jk     # base64
  JWT_SECRET: aHMyNTYtMzItYnl0ZS1taW5pbXVtLXNlY3JldA==
  TOSS_SECRET_KEY: dGVzdF9zay4uLg==
```

- 구조는 *ConfigMap 과 동일*
- *base64 인코딩* (암호화 X — *식별 안 되도록* 만)
- *etcd 에는 *암호화 저장 (`--encryption-provider-config`)
- *RBAC* 으로 *읽기 권한 제한*

### 5.2 *Secret 만 *별도 type 으로 *나눈 *3 가지 이유*

1. *RBAC 분리* — *Secret read 권한* 은 *고 권한 운영자만*
2. *Audit 추적* — *Secret 접근은 *별도 로그*
3. *etcd 암호화 대상* — *ConfigMap 은 *plain* 으로 두지만 *Secret 은 암호화*

### 5.3 *Secret 의 *진짜 문제 — *Git 에 *못 넣음*

> *Secret YAML 을 *그대로 git 에 *commit 하면* *base64 디코딩* 만으로 *시크릿 노출*.

→ *해법 1*: *외부 KMS* (AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager)
→ *해법 2*: *SOPS + age* — *암호화된 채로 *Git 에 *commit*, *클러스터 의 *Operator 가 *런타임에 *복호화*

```yaml
# secrets/order-service.sops.yaml — Git 에 이렇게 들어감
apiVersion: v1
kind: Secret
metadata:
    name: order-service-secrets
data:
    POSTGRES_PASSWORD: ENC[AES256_GCM,data:5x9f...,iv:abc...,tag:...,type:str]
sops:
    age:
      - recipient: age1qzx...
```

→ *Git audit trail 유지* + *복호화 키 없는 사람은 못 읽음* + *클러스터의 SOPS-Operator 만 복호화 가능*.

---

## 6. *층 6 — *Volume : *"영속 저장소 와 *Pod 의 *수명을 *분리* 한다"*

### 6.1 *Pod 는 *기본적으로 *상태가 *없다*

> Pod 가 *재시작 되면 *컨테이너 안의 파일 시스템* 은 *모두 *날아간다*. 그래서 *DB / 업로드 파일 / 캐시* 는 *Pod 밖* 에 *두어야 한다*.

### 6.2 *Volume 의 *3 단 추상화*

```
[Pod]
  └─ VolumeMount     "내 컨테이너 의 /var/data 에 *뭔가* 를 *마운트* 해 줘"
              │
              ▼
[PersistentVolumeClaim (PVC)]   "10Gi SSD 가 *필요* 해"
              │
              ▼
[PersistentVolume (PV)]         "여기 *진짜 *디스크 가 *있어"
              │
              ▼
[StorageClass]                  "이 디스크 는 *NFS / local-path / Ceph / EBS 중 *어떤 *것인지*"
```

### 6.3 *왜 *3 단 으로 분리되어 있나*

- *PVC* — *애플리케이션 측 요구* (몇 GB, 어떤 access mode)
- *PV* — *인프라 측 공급* (어떤 디스크, 어디 위치)
- *StorageClass* — *동적 provisioning 정책* (요청 오면 *알아서 PV 생성*)

```yaml
# 애플리케이션 개발자 — PVC 만 작성
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: order-service-uploads
spec:
  storageClassName: ssd-local            # ← StorageClass 이름만
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          volumeMounts:
            - name: uploads
              mountPath: /var/uploads     # ← Pod 안의 경로
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: order-service-uploads
```

→ *개발자는 *"10Gi SSD 줘"* 만 *말하면 된다*. *어떤 디스크 인지* 는 *클러스터 운영자 의 *책임*.

### 6.4 *Pod 가 *옮겨도 *데이터는 *살아 남는다*

```
[09:00] Pod 가 노드 A 에서 시작 → /var/uploads 에 파일 100 개 적재
[10:00] 노드 A 다운 → Pod 가 노드 B 로 재스케줄
[10:01] 새 Pod 가 /var/uploads 마운트 → 같은 파일 100 개 그대로 보임
```

→ *Pod 의 수명* 과 *데이터의 수명* 이 *분리* 된다. *이게 *상태 없는 컨테이너* 위에서 *상태 있는 서비스* 를 *돌리는 *비밀* .

---

## 7. *6 개 층 의 *조화 — *어떻게 *맞물려 *돌아가나*

### 7.1 *한 Pod 가 *생기는 *과정*

```
1. 사용자가 Deployment 의 image tag 를 v1.42 → v1.43 으로 변경
   → git push → ArgoCD 가 cluster 에 apply
   
2. Deployment Controller 가 ReplicaSet (v1.43) 생성
   → ReplicaSet Controller 가 Pod 3 개 만들라고 명령
   
3. Scheduler 가 Pod 3 개를 *어느 노드 에 둘지* 결정
   → 노드의 CPU / 메모리 / nodeSelector / podAntiAffinity 평가
   
4. kubelet 이 노드에서 Pod 를 *진짜 *생성
   → image pull (private registry mirror)
   → ConfigMap / Secret 을 환경변수 / 파일로 주입
   → PVC → PV 로 binding → /var/uploads 마운트
   → 컨테이너 start

5. Readiness probe 통과 → Service 의 endpoint 에 추가
   → 외부 트래픽 받기 시작

6. 옛 ReplicaSet (v1.42) 의 Pod 1 개 종료
   → Service 의 endpoint 에서 제거
   → SIGTERM → graceful shutdown → 종료

→ 한 번에 하나씩 반복 (RollingUpdate)
```

### 7.2 *6 개 층 의 *책임 분담 표*

| 층 | 책임 | 한 줄 |
|---|---|---|
| Deployment | *원하는 상태 선언* | "이런 상태 유지해 줘" |
| ReplicaSet | *개수 보장* | "3 개 가 항상 살아 있어야 해" |
| Service | *접근 길* | "어떤 Pod 든 이 주소로 가면 됨" |
| ConfigMap | *설정 주입* | "환경마다 다른 옷을 입혀 줘" |
| Secret | *시크릿 주입* | "민감한 옷은 분리해서 줘" |
| Volume | *영속 저장소* | "Pod 가 죽어도 데이터는 살아" |
| *Pod* | *결과 — 진짜 도는 *프로세스* | "위 모든 것의 결정체" |

---

## 8. *운영 관점에서 *왜 이 *층 분리 가 *결정적 인가*

### 8.1 *각 층 이 *독립적으로 *변경 가능*

- *image 만 *바꿈* — *ConfigMap / Secret / Volume / Service 그대로*
- *설정 만 *바꿈* — *image / Secret / Volume / Service 그대로*
- *시크릿 만 *바꿈* — *image / ConfigMap / Volume / Service 그대로*
- *replica 수 만 *바꿈* — *나머지 모두 그대로*

→ *변경의 *영향 범위 가 *최소화* 된다.

### 8.2 *각 층 이 *독립적으로 *추적 가능*

- *Deployment 변경* — `kubectl rollout history`
- *ConfigMap 변경* — Git commit 추적
- *Secret 변경* — RBAC audit 로그
- *PV 변경* — 별도 audit (스토리지 변경은 *드물게* 일어남)

### 8.3 *각 층 이 *독립적으로 *권한 분리 가능 (RBAC)*

- *개발자* — Deployment, ConfigMap *읽기/쓰기*
- *보안팀* — Secret *읽기/쓰기*
- *인프라팀* — PV, StorageClass *읽기/쓰기*
- *운영자* — *전부 읽기*

→ *책임 분리 + 권한 분리 가 *자연스럽게 *맞아 떨어진다*.

### 8.4 *각 층 이 *독립적으로 *GitOps 관리 가능*

```
helm-deploy/                       # GitOps 단일 소스
├── charts/
│   └── order-service/
│       ├── templates/
│       │   ├── deployment.yaml    # ← Deployment 정의
│       │   ├── service.yaml       # ← Service 정의
│       │   ├── configmap.yaml     # ← ConfigMap 정의
│       │   └── pvc.yaml           # ← PVC 정의
│       └── values-prod.yaml       # ← 환경별 값
└── secrets/
    └── order-service.sops.yaml    # ← Secret (SOPS 암호화)
```

→ *6 개 층 이 *각자 파일 / 차트* 로 *분리* 되어 *PR 리뷰 / audit / rollback* 가능.

---

## 9. *흔한 오해 3 가지*

### 9.1 *"Pod 가 *주인공이다"*

→ *Pod 는 *결과물* 이다. *Pod 를 *직접 *만드는 것은 *anti-pattern*. *Deployment 를 *통해서만 *만들어야* *재시작 / 롤백 / 스케일* 이 *작동* 한다.

### 9.2 *"Service 가 *로드밸런서 다"*

→ *Service 는 *iptables / IPVS 룰* 일 뿐. *L4 부하분산* 만. *L7 (HTTP 헤더 기반 라우팅)* 은 *Ingress / Gateway API* 필요.

### 9.3 *"ConfigMap 에 *비밀번호 *넣으면 *편하지"*

→ *Secret 과 *ConfigMap 의 *분리 는 *기술적 차이 가 *아니라* *audit / RBAC / 보안* 정책 분리. *섞으면 *팀 전체 가 *시크릿 을 *볼 수 있다*.

---

## 10. *내 클러스터에서 *6 개 층 이 *실제로 *어떻게 *돌고 있나*

| 층 | 내 구현 |
|---|---|
| Deployment | `charts/order-service/templates/deployment.yaml` — replicas 3 + RollingUpdate (maxSurge 1, maxUnavailable 0) + podAntiAffinity preferred (3 노드 spread) |
| ReplicaSet | Deployment 가 자동 관리 — `kubectl get rs -n settlement-prod` 로 *3 세대 history* 보존 |
| Service | `ClusterIP` (내부 통신) + Cloudflare Tunnel → 외부 도메인 (`jen.lemuel.co.kr`) |
| ConfigMap | Helm `values-prod.yaml` 이 *환경별 ConfigMap 으로 변환* — Spring `application.yml` 도 ConfigMap 으로 마운트 |
| Secret | *SOPS + age* 로 *암호화된 채로 *Git commit*. *클러스터 의 *SOPS-Operator 가 *런타임 복호화* |
| Volume | *NFS Server* (공유) + *local-path* (단일노드) + *ssd-local* (일원 NVMe 전용) — *StorageClass 분리* |

→ *6 개 층 이 *각자 *역할* 을 *온전히 *분담* 하기 때문에 *47 → 65+ 개 ArgoCD App* 이 *동시에 무중단 운영* 된다.

---

## 11. *결론 — *층을 *분리해서 *볼 수 있어야 *운영 이 *가능 하다*

> *Pod 만 보는 사람은 *Pod 가 *터지면 *왜 *터졌는지 *모른다*.
>
> *6 개 층 을 *분리해서 보는 사람은 *Pod 가 *터져도 *어느 층 에서 *왜* 가 *바로 보인다*.

| 증상 | 어느 층 의 문제인가 |
|---|---|
| Pod 가 *반복 재시작* | Deployment (resource limit) 또는 *Liveness probe* |
| Pod 는 *살았는데 *외부 접근 안 됨* | Service (endpoint 미연결) 또는 *Readiness probe* |
| *환경마다 *동작 다름* | ConfigMap (환경별 값) |
| *Secret 빠짐 / 권한 부족* | Secret (RBAC) 또는 *SOPS 복호화 실패* |
| *Pod 재시작 시 *데이터 사라짐* | Volume (PVC 미설정 또는 *emptyDir 사용*) |
| *원하는 개수 안 유지됨* | ReplicaSet (controller 오류) 또는 *resource 부족* |

→ *Pod 위 / 옆 / 아래* 의 *6 개 층* 을 *독립된 책임* 으로 *볼 수 있어야* 비로소 *진짜 K8s 운영자* 다. *YAML 한 장 을 *읽는 것* 이 *아니라* *6 개 층 의 *대화* 를 *읽는 것*. 그게 *production 운영 의 *진짜 시각* 이다.

---

## 부록 — *6 개 층 의 *진짜 API*

```bash
# Deployment 의 history / rollback
kubectl rollout history deployment/order-service
kubectl rollout undo deployment/order-service --to-revision=2

# ReplicaSet 직접 보기
kubectl get rs -l app=order-service
kubectl scale rs/order-service-7f9d6b8c5 --replicas=5  # (보통 안 함, Deployment 통해서)

# Service endpoint 실제로 누가 받고 있는지
kubectl get endpoints order-service
kubectl describe service order-service

# ConfigMap 실시간 변경 (단, Pod 재시작 필요 — Spring Boot 는 reload 안 함)
kubectl edit configmap order-service-config

# Secret 디코딩 (RBAC 통과한 경우)
kubectl get secret order-service-secrets -o jsonpath='{.data.JWT_SECRET}' | base64 -d

# Volume 의 실제 PV
kubectl get pvc order-service-uploads
kubectl describe pv pvc-abc-123
```

→ *각 명령어 가 *어느 층 에 *말하고 있는지* 가 *분명* 해야 한다. *그게 *층 분리 의 *진짜 가치* 다.
