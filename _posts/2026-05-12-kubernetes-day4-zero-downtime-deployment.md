---
layout: post
title: "쿠버네티스 4일차 — 무중단 배포 (RollingUpdate / Canary / Blue-Green)"
date: 2026-05-12 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, deployment, rollingupdate, canary, blue-green, rollback]
---

3일차까지 우리는 앱을 띄우고, 노출하고, 데이터까지 붙였습니다. 이제 진짜 운영 기술 — **새 버전을 어떻게 끊김 없이 갈아끼우나** — 를 봅니다.

> 이 글에서 다루는 것
> - **RollingUpdate**: Deployment 의 기본 무중단 전략
> - **maxSurge / maxUnavailable**: 갈아끼우는 속도 조절
> - **Canary**: 신버전을 일부 트래픽에만 흘리기
> - **Blue-Green**: 두 환경 운용 + 스위치
> - **Rollback**: 한 줄로 전 버전 되돌리기

---

## 1. RollingUpdate — Deployment 의 기본값

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%          # 동시에 추가로 띄울 수 있는 비율
      maxUnavailable: 25%    # 동시에 죽여도 되는 비율
```

10개 replicas 면 한 번에 최대 2-3개씩 갈아끼웁니다.

### 흐름

```
v1: [v1][v1][v1][v1][v1][v1][v1][v1][v1][v1]   ← 시작
    ↓ kubectl set image
    [v1][v1][v1][v1][v1][v1][v1][v1][v2][v2]   ← 2개 신규 (maxSurge=25%)
    [v1][v1][v1][v1][v1][v2][v2][v2][v2][v2]   ← 점진 교체
    ...
    [v2][v2][v2][v2][v2][v2][v2][v2][v2][v2]   ← 완료
```

### 명령어

```bash
kubectl set image deploy/web app=my-app:v2
kubectl rollout status deploy/web      # 진행 상황
kubectl rollout history deploy/web     # 배포 이력
kubectl rollout undo deploy/web        # 직전 버전으로 즉시 롤백
```

### 함정 — readinessProbe 가 없으면 의미 없음

```yaml
containers:
  - name: app
    readinessProbe:
      httpGet: { path: /health, port: 8080 }
      initialDelaySeconds: 5
      periodSeconds: 5
```

`readinessProbe` 가 없으면 **시작 중인 Pod 도 트래픽을 받습니다.** 502 폭탄 맞기 딱 좋아요.

---

## 2. Canary — 카나리아 배포

> "신버전을 5% 사용자한테만 보내서 에러율 보고, 괜찮으면 100% 로 늘리자."

기본 Deployment 만으로는 어렵습니다. 두 가지 패턴이 있어요.

### 방법 A: 두 Deployment + Service selector

```yaml
# stable: replicas=9
# canary: replicas=1
# 같은 label app=web → Service 가 둘 다 라우팅
# 비율 = replica 수로 조절 (9:1 = 90%:10%)
```

거칠지만 yaml 만으로 가능. 정확한 % 제어는 못합니다.

### 방법 B: Service Mesh (Istio / Linkerd)

```yaml
# Istio VirtualService 예
spec:
  http:
    - route:
        - destination: { host: web, subset: v1 }
          weight: 95
        - destination: { host: web, subset: v2 }
          weight: 5
```

5% 정확히 v2 로. 에러율 보고 단계적으로 늘릴 수 있습니다.

---

## 3. Blue-Green — 두 환경 + 스위치

> "신버전 환경(green) 을 통째로 띄워놓고, 트래픽 스위치 한 번에 전환. 문제 생기면 다시 스위치."

```
[Service: web]
      │
      ▼ selector: { color: blue }
   [Deployment blue v1]   ← 트래픽 100%
   [Deployment green v2]  ← 대기 (트래픽 0)
```

```bash
# 스위치
kubectl patch service web -p '{"spec":{"selector":{"color":"green"}}}'
```

### 장단점

| | RollingUpdate | Canary | Blue-Green |
|---|---|---|---|
| 인프라 비용 | 1배 | 1배 | **2배** (두 환경 다 띄움) |
| 롤백 속도 | 분 단위 | 초 단위 | **즉시** |
| 부분 검증 | X | **O** (5% 유저) | X (전부 or 전부) |
| 구현 난이도 | 쉬움 | 보통 (Mesh 권장) | 보통 |

운영 70% 는 RollingUpdate + readinessProbe 만으로 충분합니다. Canary/Blue-Green 은 트래픽이 큰 서비스나 결제처럼 위험한 변경에서.

---

## 4. Rollback — 가장 중요한 한 줄

```bash
kubectl rollout undo deploy/web
# Direct previous version

kubectl rollout undo deploy/web --to-revision=3
# 특정 리비전으로
```

`Deployment.spec.revisionHistoryLimit` (기본 10) 만큼의 버전을 클러스터가 기억합니다.

---

## 5. 무중단 배포의 진짜 적 — Graceful Shutdown

배포 시 502 가 가끔 나는 가장 흔한 이유는 **Pod 가 죽을 때 in-flight 요청을 끊어버리기 때문** 입니다.

```yaml
spec:
  containers:
    - name: app
      lifecycle:
        preStop:
          exec:
            command: ["sh", "-c", "sleep 10"]   # SIGTERM 10초 지연
  terminationGracePeriodSeconds: 30
```

그리고 앱 코드에서 SIGTERM 받으면:
1. health check `/health` 가 503 반환 시작 → kube-proxy 가 트래픽 끊음
2. 이미 받은 요청은 끝까지 처리
3. 그 후 종료

이 패턴 안 쓰면 RollingUpdate 든 뭐든 무중단이 아닙니다.

---

## 핵심 한 줄 정리

- **RollingUpdate** = Deployment 기본값. maxSurge / maxUnavailable + readinessProbe 필수
- **Canary** = 신버전 일부 트래픽. 정확하려면 Istio/Linkerd
- **Blue-Green** = 두 환경 + Service selector 스위치. 비싸지만 즉시 롤백
- **Rollback** = `kubectl rollout undo` 한 줄
- **무중단의 핵심은 graceful shutdown** — preStop sleep + readiness 503 패턴

5일차에서는 **모니터링 + 로깅** — Prometheus / Grafana / Loki 스택 — 으로 넘어갑니다.

---

> 이 글은 르무엘 사내 K8s 7일 입문 코스의 4일차 자료입니다. 시리즈 시작은 [1일차]({% post_url 2026-05-09-kubernetes-day1-architecture %}) 글입니다.
