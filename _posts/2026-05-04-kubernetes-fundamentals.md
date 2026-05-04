---
layout: post
title: "Kubernetes 핵심 개념 완전 정리 — Pod부터 Ingress까지 실전 가이드"
date: 2026-05-04 00:30:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k3s, docker, devops, container]
---
{% raw %}

> 이 글은 K3s 클러스터로 ASAT(청각 재활 훈련 시스템)를 이중화 운영한 실제 경험을 바탕으로 작성했습니다.

## 목차

1. [Kubernetes 기본 개념](#1-kubernetes-기본-개념)
2. [Pod의 생명주기 관리](#2-pod의-생명주기-관리)
3. [Deployment 사용 및 관리](#3-deployment-사용-및-관리)
4. [Service와 Ingress로 네트워킹 구성](#4-service와-ingress로-네트워킹-구성)
5. [지속적인 스토리지 관리](#5-지속적인-스토리지-관리)
6. [실전 사례: K3s로 ASAT 이중화 운영](#6-실전-사례-k3s로-asat-이중화-운영)

---

## 1. Kubernetes 기본 개념

### 왜 Kubernetes가 필요한가?

Docker로 컨테이너를 띄우는 건 쉽습니다. 하지만 **10개 이상의 서비스를 운영**하면 이런 문제가 생깁니다:

- 컨테이너가 죽으면 누가 다시 띄우나?
- 트래픽이 늘면 어떻게 스케일 아웃?
- 여러 서버에 컨테이너를 어떻게 분배?
- 무중단 배포는?

Kubernetes는 이 모든 걸 **선언적으로** 해결합니다.

### 핵심 아키텍처

```
┌─────────────────────────────────────────────┐
│                Control Plane                │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ API      │ │ Scheduler│ │ Controller  │ │
│  │ Server   │ │          │ │ Manager     │ │
│  └──────────┘ └──────────┘ └─────────────┘ │
│  ┌──────────────────────────────────────┐   │
│  │              etcd                     │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         ↕                    ↕
┌────────────────┐  ┌────────────────┐
│   Worker Node  │  │   Worker Node  │
│  ┌──────────┐  │  │  ┌──────────┐  │
│  │ kubelet  │  │  │  │ kubelet  │  │
│  │ kube-    │  │  │  │ kube-    │  │
│  │ proxy    │  │  │  │ proxy    │  │
│  ├──────────┤  │  │  ├──────────┤  │
│  │ Pod  Pod │  │  │  │ Pod  Pod │  │
│  └──────────┘  │  │  └──────────┘  │
└────────────────┘  └────────────────┘
```

### 구성 요소 역할

| 구성 요소 | 역할 | 비유 |
|----------|------|------|
| **API Server** | 모든 요청의 진입점 | 회사의 접수 데스크 |
| **etcd** | 클러스터 상태 저장소 | 회사의 데이터베이스 |
| **Scheduler** | Pod를 어떤 노드에 배치할지 결정 | 인사 배치 담당자 |
| **Controller Manager** | 원하는 상태(desired state)를 유지 | 현장 관리자 |
| **kubelet** | 각 노드에서 Pod를 실행/관리 | 현장 작업자 |
| **kube-proxy** | 네트워크 규칙 관리, 서비스 라우팅 | 네트워크 관리자 |

### Docker Compose vs Kubernetes

| | Docker Compose | Kubernetes |
|---|---|---|
| 범위 | 단일 서버 | 다중 서버 클러스터 |
| 자가 복구 | restart 정책만 | Pod 자동 재시작 + 자동 스케줄링 |
| 스케일링 | 수동 | `kubectl scale` 한 줄 |
| 무중단 배포 | 직접 구현 | Rolling Update 기본 제공 |
| 서비스 디스커버리 | Docker DNS | Service + DNS 자동 등록 |

---

## 2. Pod의 생명주기 관리

### Pod란?

Kubernetes의 **최소 배포 단위**입니다. 하나 이상의 컨테이너를 묶어서 같은 네트워크/스토리지를 공유합니다.

```yaml
# 가장 단순한 Pod 정의
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  containers:
    - name: app
      image: my-app:1.0
      ports:
        - containerPort: 8080
      resources:
        requests:
          memory: "256Mi"
          cpu: "250m"
        limits:
          memory: "512Mi"
          cpu: "500m"
```

### Pod 생명주기

```
Pending → Running → Succeeded/Failed
             ↓
         CrashLoopBackOff (반복 실패 시)
```

| 상태 | 의미 |
|------|------|
| **Pending** | 노드 배정 대기 또는 이미지 다운로드 중 |
| **Running** | 최소 1개 컨테이너 실행 중 |
| **Succeeded** | 모든 컨테이너 정상 종료 (Job 등) |
| **Failed** | 컨테이너가 비정상 종료 |
| **CrashLoopBackOff** | 반복 실패 → 재시작 간격 증가 |

### Health Check (프로브)

```yaml
spec:
  containers:
    - name: app
      livenessProbe:         # 살아있는지 확인 → 실패하면 재시작
        httpGet:
          path: /actuator/health
          port: 8080
        initialDelaySeconds: 30
        periodSeconds: 10
      readinessProbe:        # 트래픽 받을 준비 됐는지 → 실패하면 Service에서 제외
        httpGet:
          path: /actuator/health/readiness
          port: 8080
        initialDelaySeconds: 10
        periodSeconds: 5
      startupProbe:          # 시작 완료 확인 → 실패하면 liveness/readiness 시작 안 함
        httpGet:
          path: /actuator/health
          port: 8080
        failureThreshold: 30
        periodSeconds: 10
```

**실전 팁**: Spring Boot 앱은 시작이 느리므로 `startupProbe`를 꼭 설정하세요. 없으면 `livenessProbe`가 앱 시작 전에 실패 판정 → 무한 재시작.

### Multi-Container Pod 패턴

```yaml
# Sidecar 패턴: 메인 앱 + 로그 수집기
spec:
  containers:
    - name: app
      image: my-app:1.0
    - name: log-collector    # Sidecar
      image: fluentd:latest
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/app
```

| 패턴 | 용도 | 예시 |
|------|------|------|
| **Sidecar** | 보조 기능 추가 | 로그 수집, 프록시 |
| **Ambassador** | 외부 통신 프록시 | DB 연결 풀 |
| **Init Container** | 초기화 작업 | DB 마이그레이션, 설정 다운로드 |

---

## 3. Deployment 사용 및 관리

### Deployment란?

Pod의 **선언적 관리자**입니다. "이 앱을 3개 실행해라"라고 선언하면 Kubernetes가 알아서 유지합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asat-backend
  namespace: asat
spec:
  replicas: 2                    # Pod 2개 유지
  selector:
    matchLabels:
      app: asat-backend
  strategy:
    type: RollingUpdate          # 무중단 배포 전략
    rollingUpdate:
      maxSurge: 1                # 최대 1개 추가 Pod 허용
      maxUnavailable: 0          # 기존 Pod 0개 이하로 내려가지 않음
  template:
    metadata:
      labels:
        app: asat-backend
    spec:
      containers:
        - name: backend
          image: asat-backend:latest
          ports:
            - containerPort: 8080
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: "prod"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
```

### 배포 전략

#### Rolling Update (기본값)

```
v1 v1 v1     ← 기존 3개
v1 v1 v1 v2  ← 새 Pod 1개 추가
v1 v1 v2     ← 기존 1개 제거
v1 v2 v2     ← 반복
v2 v2 v2     ← 완료
```

- **장점**: 무중단, 점진적 전환
- **단점**: 잠시 동안 v1과 v2가 공존

#### Recreate

```
v1 v1 v1     ← 전부 종료
(다운타임)
v2 v2 v2     ← 전부 시작
```

- **장점**: 버전 혼재 없음
- **단점**: 다운타임 발생

### 롤백

```bash
# 배포 히스토리 확인
kubectl rollout history deployment/asat-backend

# 이전 버전으로 롤백
kubectl rollout undo deployment/asat-backend

# 특정 버전으로 롤백
kubectl rollout undo deployment/asat-backend --to-revision=3

# 배포 상태 확인
kubectl rollout status deployment/asat-backend
```

### HPA (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: asat-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: asat-backend
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70    # CPU 70% 넘으면 스케일 아웃
```

---

## 4. Service와 Ingress로 네트워킹 구성

### Service란?

Pod는 생성/삭제될 때마다 IP가 바뀝니다. Service는 **고정된 엔드포인트**를 제공하여 Pod 집합에 접근합니다.

### Service 유형

#### ClusterIP (기본값)

클러스터 **내부**에서만 접근 가능:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: asat-backend-svc
spec:
  type: ClusterIP
  selector:
    app: asat-backend      # 이 라벨의 Pod로 트래픽 전달
  ports:
    - port: 80             # Service 포트
      targetPort: 8080     # Pod 포트
```

```
다른 Pod → asat-backend-svc:80 → Pod(8080)
```

#### NodePort

모든 노드의 특정 포트로 외부 노출:

```yaml
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080      # 모든 노드의 30080 포트로 접근
```

```
외부 → <노드IP>:30080 → Service → Pod
```

#### LoadBalancer

클라우드 환경에서 외부 로드밸런서 자동 생성:

```yaml
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
```

### Ingress

**L7(HTTP) 레벨** 라우팅. 도메인/경로 기반으로 여러 Service에 분배:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: asat-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: asat.lemuel.co.kr
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: asat-frontend-svc
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: asat-backend-svc
                port:
                  number: 80
```

```
asat.lemuel.co.kr/      → frontend Service → frontend Pod
asat.lemuel.co.kr/api   → backend Service  → backend Pod
```

### Service vs Ingress 비교

| | Service (NodePort) | Ingress |
|---|---|---|
| 레이어 | L4 (TCP/UDP) | L7 (HTTP) |
| 도메인 라우팅 | 불가 | 가능 |
| SSL 종료 | 별도 구현 | 지원 |
| 경로 기반 분배 | 불가 | 가능 |
| 포트 | 노드당 1개 | 80/443 공유 |

---

## 5. 지속적인 스토리지 관리

### 문제: Pod는 일시적이다

Pod가 재시작되면 컨테이너 내부 파일이 **전부 사라집니다**. DB 데이터, 업로드 파일 등을 유지하려면 외부 스토리지가 필요합니다.

### PV (Persistent Volume)

클러스터 관리자가 생성하는 **스토리지 리소스**:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgres-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce          # 하나의 노드에서만 읽기/쓰기
  hostPath:
    path: /data/postgres     # 노드의 로컬 경로 (개발용)
  persistentVolumeReclaimPolicy: Retain   # PVC 삭제 후에도 데이터 보존
```

### PVC (Persistent Volume Claim)

사용자(개발자)가 요청하는 **스토리지 신청서**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi           # 5GB 요청 → 10GB PV에 바인딩
```

### Pod에서 사용

```yaml
spec:
  containers:
    - name: postgres
      image: postgres:17
      volumeMounts:
        - name: db-storage
          mountPath: /var/lib/postgresql/data
  volumes:
    - name: db-storage
      persistentVolumeClaim:
        claimName: postgres-pvc
```

### Access Modes

| 모드 | 의미 | 약자 |
|------|------|------|
| ReadWriteOnce | 하나의 노드에서 읽기/쓰기 | RWO |
| ReadOnlyMany | 여러 노드에서 읽기 전용 | ROX |
| ReadWriteMany | 여러 노드에서 읽기/쓰기 | RWX |

### StorageClass (동적 프로비저닝)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: rancher.io/local-path   # K3s 기본 provisioner
reclaimPolicy: Retain
```

PVC가 생성되면 **자동으로 PV를 생성**합니다. 매번 수동으로 PV를 만들 필요가 없습니다.

---

## 6. 실전 사례: K3s로 ASAT 이중화 운영

### 환경

- **마스터**: 르무엘 (i7-6500U, 32GB)
- **워커**: 루이스 (i7-8565U, 16GB)
- **서비스**: ASAT 청각 재활 훈련 시스템

### K3s 설치

```bash
# 마스터 노드 (르무엘)
curl -sfL https://get.k3s.io | sh -

# 워커 노드 (루이스) — 토큰으로 마스터에 연결
curl -sfL https://get.k3s.io | K3S_URL=https://[LAN노드]:6443 \
  K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token) sh -
```

### Deployment 구성

```yaml
# backend 2개, frontend 2개 — 양쪽 노드에 분배
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asat-backend
  namespace: asat
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: backend
          image: asat-backend:latest
          ports:
            - containerPort: 8080
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 60
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
      affinity:
        podAntiAffinity:           # 같은 노드에 배치하지 않음 → 이중화
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: asat-backend
                topologyKey: kubernetes.io/hostname
```

### 트래픽 흐름

```
인터넷 → Cloudflare Tunnel → nginx (르무엘 호스트)
    → upstream (Pod IP 직접 지정)
        → 르무엘 Pod (192.168.x.x:8080)
        → 루이스 Pod (192.168.y.y:8080)
```

NodePort 대신 **nginx upstream + Pod IP 직접 지정** 방식을 사용합니다. K3s kube-proxy의 iptables 라우팅이 홈서버 환경에서 불안정했기 때문입니다.

### Pod IP 자동 갱신 스크립트

Pod가 재시작되면 IP가 바뀌므로 nginx upstream을 자동 갱신합니다:

```bash
#!/bin/bash
# /opt/scripts/update-k8s-nginx.sh (cron 1분마다)
NEW_IPS=$(kubectl get pods -n asat -l app=asat-backend \
  -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}')

# nginx upstream 업데이트
# ... IP 변경 감지 시 nginx reload
```

### 운영 현황

```bash
$ kubectl get pods -n asat -o wide
NAME                        READY   NODE     IP
asat-backend-xxx-abc        1/1     lemuel   10.42.0.15
asat-backend-xxx-def        1/1     louise   10.42.1.8
asat-frontend-xxx-ghi       1/1     lemuel   10.42.0.16
asat-frontend-xxx-jkl       1/1     louise   10.42.1.9
```

- Backend 2개: 르무엘 1, 루이스 1
- Frontend 2개: 르무엘 1, 루이스 1
- 한쪽 서버가 죽어도 나머지에서 서비스 유지

### 교훈

1. **K3s는 경량 Kubernetes** — 홈서버에서도 충분히 운영 가능
2. **NodePort보다 nginx upstream** — 홈서버 환경에서 더 안정적
3. **podAntiAffinity** — 이중화의 핵심, 같은 노드에 배치 방지
4. **startupProbe 필수** — Spring Boot 앱은 시작이 느려서 livenessProbe가 먼저 실패할 수 있음
5. **실무에서는 Ingress Controller** — nginx Ingress Controller가 표준, 홈서버에서는 호스트 nginx로 대체

{% endraw %}
