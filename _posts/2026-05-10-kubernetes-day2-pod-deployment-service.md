---
layout: post
title: "쿠버네티스 2일차 — Pod / Deployment / Service / Ingress 4종 세트"
date: 2026-05-10 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k8s, pod, deployment, service, ingress, yaml, kubectl]
---

[1일차]({% post_url 2026-05-09-kubernetes-day1-architecture %}) 에서는 클러스터 안에 누가 사는지 봤습니다. 2일차는 그 클러스터 위에 **내 앱을 올리는 데 필요한 4가지 오브젝트** 를 직접 만들어보면서 익힙니다.

> 이 글에서 다루는 것
> - **Pod**: 컨테이너를 담는 가장 작은 그릇
> - **Deployment**: Pod 를 N 개로 굴리는 매니저
> - **Service**: Pod 를 외부/내부에 노출하는 네트워크 진입점
> - **Ingress**: HTTP 도메인 라우팅 (Service 의 상위 레이어)

각각이 왜 따로 존재하는지, yaml 한 통이 어떤 일을 하는지 손으로 따라가 봅니다.

---

## 1. Pod — 컨테이너를 담는 가장 작은 그릇

### "왜 컨테이너 직접 안 띄우고 Pod 라는 걸 거쳐?"

쿠버네티스는 컨테이너를 **직접** 다루지 않습니다. **Pod** 라는 한 겹을 거칩니다. 이유는 두 가지입니다.

1. **공동 운명** — Pod 안의 컨테이너들은 같은 노드에 같이 뜨고, 같이 죽습니다. (사이드카, 로그 수집 컨테이너처럼 본체와 운명을 함께 해야 하는 경우)
2. **공동 네트워크** — Pod 안의 컨테이너들은 `localhost` 로 서로를 부릅니다. 같은 IP 를 공유합니다.

대부분의 경우 **Pod 1개 = 컨테이너 1개** 입니다. 사이드카 패턴이 필요할 때만 여러 개를 묶어요.

### 가장 작은 Pod yaml

```yaml
# pod-nginx.yaml
apiVersion: v1
kind: Pod
metadata:
  name: hello-nginx
  labels:
    app: hello
spec:
  containers:
    - name: web
      image: nginx:1.27
      ports:
        - containerPort: 80
```

```bash
kubectl apply -f pod-nginx.yaml
kubectl get pods
# NAME          READY   STATUS    RESTARTS   AGE
# hello-nginx   1/1     Running   0          5s
```

이게 끝입니다. nginx 가 클러스터 안에서 돌고 있어요.

### 그런데 이대로는 운영에 못 씀

- Pod 가 죽으면 **자동으로 재생성되지 않습니다** (단발성).
- N개로 늘리려면 yaml 을 N개 만들어야 합니다.
- 새 버전 배포 시 무중단이 안 됩니다.

그래서 실무에선 Pod 를 **직접** 만들지 않고 **Deployment 가 대신 만들게** 합니다.

---

## 2. Deployment — Pod 를 N 개로 굴리는 매니저

### 핵심 발상: "선언" 만 하면 시스템이 맞춰준다

`Deployment` 는 이렇게 말합니다:

> "**hello-nginx Pod 를 항상 3개 띄워줘. 죽으면 알아서 살리고, 새 버전 나오면 무중단으로 갈아끼워줘.**"

쿠버네티스의 **선언적(declarative)** 철학이 가장 잘 드러나는 오브젝트입니다.

```yaml
# deploy-nginx.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-nginx
spec:
  replicas: 3                    # ← 3개 띄워
  selector:
    matchLabels: { app: hello }  # ← 이 라벨 가진 Pod 가 내 책임
  template:                      # ← Pod 의 청사진
    metadata:
      labels: { app: hello }
    spec:
      containers:
        - name: web
          image: nginx:1.27
          ports: [ { containerPort: 80 } ]
```

```bash
kubectl apply -f deploy-nginx.yaml
kubectl get deploy,pods
# NAME                   READY   UP-TO-DATE   AVAILABLE   AGE
# deployment/hello-nginx 3/3     3            3           10s
# NAME                          READY   STATUS    RESTARTS   AGE
# pod/hello-nginx-7dffb9-abc12  1/1     Running   0          10s
# pod/hello-nginx-7dffb9-def34  1/1     Running   0          10s
# pod/hello-nginx-7dffb9-ghi56  1/1     Running   0          10s
```

### 마법 같은 명령들

```bash
# 5개로 늘리기
kubectl scale deploy/hello-nginx --replicas=5

# 새 버전으로 무중단 업데이트
kubectl set image deploy/hello-nginx web=nginx:1.28

# 방금 한 거 되돌리기 (롤백)
kubectl rollout undo deploy/hello-nginx

# Pod 하나를 손으로 죽여보기 — Deployment 가 즉시 새로 띄움
kubectl delete pod hello-nginx-7dffb9-abc12
```

> Deployment 안에는 사실 **ReplicaSet** 이라는 한 겹이 더 있습니다. 무중단 배포 시 새 ReplicaSet 을 만들고 옛 것을 점차 줄이는 방식으로 전환합니다. 입문자는 일단 "Deployment = Pod N개 매니저" 로만 기억해도 충분합니다.

---

## 3. Service — Pod 의 안정된 주소를 만들어준다

### Pod IP 를 직접 쓰면 안 되는 이유

Pod 가 재생성되면 **IP 가 바뀝니다**. Pod 5개를 아무리 잘 굴려도, 그걸 부르는 클라이언트 입장에서는

- "지금 살아있는 Pod IP 가 뭐지?"
- "5개 중에 누구한테 트래픽 보내지?"

가 항상 문제입니다. **Service** 가 이 둘을 한 번에 해결합니다.

### ClusterIP — 클러스터 내부에서 부르는 안정된 이름

```yaml
# svc-nginx.yaml
apiVersion: v1
kind: Service
metadata:
  name: hello
spec:
  selector: { app: hello }   # ← 이 라벨 가진 Pod 들이 백엔드
  ports:
    - port: 80               # ← 서비스 포트
      targetPort: 80         # ← Pod 컨테이너 포트
  type: ClusterIP            # ← 기본값. 클러스터 안에서만 보임
```

```bash
kubectl apply -f svc-nginx.yaml
kubectl get svc
# NAME    TYPE        CLUSTER-IP      PORT(S)
# hello   ClusterIP   10.96.142.18    80/TCP
```

이제 클러스터 안의 다른 Pod 가 `http://hello` 만 호출하면 됩니다 (DNS 자동 등록). 백엔드 Pod 가 5개든 100개든 트래픽이 자동 분산됩니다.

### Service 종류 4가지 — 언제 뭘 쓰나

| 타입 | 보이는 범위 | 언제 |
|---|---|---|
| **ClusterIP** (기본) | 클러스터 내부만 | 마이크로서비스끼리 부를 때 |
| **NodePort** | 모든 노드의 특정 포트 | 빠른 데모, 로컬 minikube 노출 |
| **LoadBalancer** | 클라우드 LB 로 외부 노출 | 운영 — AWS ELB, GCP LB 자동 생성 |
| **ExternalName** | DNS CNAME 으로 외부 서비스 매핑 | 외부 DB 를 클러스터 이름처럼 쓰기 |

운영에서 거의 다 ClusterIP + Ingress 조합이고, LoadBalancer 는 Ingress Controller 자체를 노출할 때만 씁니다.

---

## 4. Ingress — HTTP 도메인 + 경로 라우팅

### "근데 Service 가 외부 노출도 되잖아? 왜 또?"

LoadBalancer Service 는 1개당 클라우드 LB 1개입니다. 마이크로서비스 10개면 LB 10개? 비싸고 관리도 어렵습니다.

`Ingress` 는 **HTTP 7계층 라우터** 입니다. 도메인/경로별로 어느 Service 에 보낼지 한 곳에서 정합니다.

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lemuel-routes
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: academy.lemuel.co.kr
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: learner, port: { number: 3001 } }
          - path: /studio
            pathType: Prefix
            backend:
              service: { name: creator-studio, port: { number: 3002 } }
          - path: /api
            pathType: Prefix
            backend:
              service: { name: api-gateway, port: { number: 8080 } }
```

도메인 1개 + 경로 3개 + Service 3개 → **LB 1개** 로 충분합니다.

### Ingress Controller 가 따로 필요합니다

`Ingress` 오브젝트는 단순 **선언** 일 뿐, 실제 트래픽을 처리하는 건 **Ingress Controller** (보통 nginx, traefik, istio gateway 같은 것). minikube 에서는 한 줄로 켜집니다:

```bash
minikube addons enable ingress
```

---

## 5. 4종 세트가 함께 그리는 그림

```
        🌐 외부 트래픽
             │
             ▼
       [LoadBalancer]
             │
             ▼
     ┌────────────────┐
     │    Ingress     │  ← /api → api-gateway, /studio → studio
     └────────────────┘
        │           │
        ▼           ▼
   [Service A]  [Service B]   ← ClusterIP, 안정된 이름
        │           │
   ┌────┴────┐  ┌──┴──┐
   ▼    ▼    ▼  ▼    ▼
  [Pod][Pod][Pod] [Pod][Pod]   ← 실제 컨테이너, 죽으면 재생성
   ▲                ▲
   └─ Deployment ───┘            ← N개 유지, 무중단 배포
```

---

## 6. 실습 — 5분 안에 nginx 노출하기

`minikube start` 가 끝났다면:

```bash
# 1. Deployment 생성 (Pod 3개)
kubectl create deployment hello --image=nginx:1.27 --replicas=3

# 2. Service 로 노출 (NodePort)
kubectl expose deployment hello --type=NodePort --port=80

# 3. 브라우저에서 열기
minikube service hello
# → 자동으로 http://192.168.49.2:30xxx 가 열림
```

여기까지 약 30초.

```bash
# 죽여봐도 다시 살아남
kubectl delete pod -l app=hello
kubectl get pods -w
# 새 Pod 가 즉시 생성되는 걸 watch 로 관찰

# 새 버전으로 갈아끼우기
kubectl set image deployment/hello nginx=nginx:1.28
kubectl rollout status deployment/hello
```

---

## 핵심 한 줄 정리

- **Pod**: 컨테이너를 담는 가장 작은 그릇 (직접 만들 일은 거의 없다)
- **Deployment**: "이 Pod 를 N개 항상 굴려줘" 선언. 무중단 배포 + 자동 복구
- **Service**: Pod 들에게 안정된 이름과 로드밸런싱을 부여
- **Ingress**: 외부 도메인 → 내부 Service 라우팅 (HTTP 7 계층)

3일차에서는 **ConfigMap / Secret / Volume / PVC** — 즉 **앱 설정과 데이터** 다루는 4종 세트로 넘어갑니다.

---

> 이 글은 르무엘 사내 K8s 7일 입문 코스의 2일차 자료입니다. [1일차 — 클러스터 아키텍처]({% post_url 2026-05-09-kubernetes-day1-architecture %}) 글을 먼저 읽고 오시면 흐름이 매끄럽습니다.
