---
layout: post
title: "쿠버네티스 7일차 — 종합 프로젝트: 작은 SaaS 운영"
date: 2026-05-15 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, helm, gitops, argocd, project, capstone]
---

드디어 **7일차**. 지금까지 배운 모든 것을 한 프로젝트로 묶습니다. **풀스택 SaaS 한 개를 쿠버네티스 위에 깔고, 무중단 배포 + 모니터링 + 보안까지** 한 흐름으로.

> 이 글에서 다루는 것
> - 프로젝트 개요 — 작은 todo SaaS
> - **Helm** 으로 yaml 묶음 패키징
> - **GitOps (ArgoCD)** 로 git push = 배포
> - 1일차 ~ 6일차 내용을 한 yaml 패키지로 통합
> - 다음 단계 학습 가이드

---

## 1. 프로젝트 개요 — Lemuel-Todo

작은 TODO SaaS 를 만든다고 가정합니다.

```
[Next.js 프론트] ─ /api ──► [Spring Boot 백엔드] ─► [Postgres]
      :3000                       :8080                :5432

(Ingress)             (ConfigMap+Secret+SA)        (PVC 20Gi)
```

지금까지 배운 모든 것을 다 씁니다:

| 주제 | 적용처 |
|---|---|
| Pod / Deployment | 3개 모두 (frontend, backend, postgres) |
| Service / Ingress | frontend ClusterIP + Ingress, backend ClusterIP, postgres ClusterIP |
| ConfigMap / Secret | backend 의 DB URL / JWT secret |
| PVC | postgres 데이터 디렉토리 (20Gi) |
| RollingUpdate | backend 배포 전략 + readinessProbe |
| Prometheus | backend Spring Boot Actuator → ServiceMonitor |
| Loki | 모든 Pod 로그 수집 |
| RBAC | backend 전용 ServiceAccount (Secret 1개만 read) |
| NetworkPolicy | postgres 는 backend 만 접근 가능 |
| SOPS | git 에 들어가는 Secret 모두 암호화 |

---

## 2. Helm — yaml 묶음 패키징

yaml 10개를 따로 관리하면 금방 망가집니다. **Helm** 은 yaml 들을 한 묶음(chart)으로 만들고 변수로 차이를 주는 도구입니다.

### Chart 구조

```
todo-saas/
├── Chart.yaml          # 메타 (name, version)
├── values.yaml         # 기본값
├── values-prod.yaml    # 환경별 오버라이드
├── values-staging.yaml
└── templates/
    ├── deployment-frontend.yaml
    ├── deployment-backend.yaml
    ├── statefulset-postgres.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secret.yaml
    ├── pvc.yaml
    ├── networkpolicy.yaml
    └── servicemonitor.yaml
```

### 템플릿 변수

```yaml
# templates/deployment-backend.yaml (요약)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-backend
spec:
  replicas: {{ .Values.backend.replicas }}
  template:
    spec:
      containers:
        - name: backend
          image: {{ .Values.backend.image }}:{{ .Values.backend.tag }}
          envFrom:
            - configMapRef: { name: {{ .Release.Name }}-config }
            - secretRef:    { name: {{ .Release.Name }}-secret }
          readinessProbe:
            httpGet: { path: /actuator/health, port: 8080 }
            initialDelaySeconds: 10
```

```yaml
# values.yaml
backend:
  replicas: 3
  image: ghcr.io/lemuel/todo-backend
  tag: 1.0.0

# values-prod.yaml
backend:
  replicas: 10                  # 프로덕션은 10개
  resources:
    requests: { cpu: 500m, memory: 1Gi }
    limits:   { cpu: 1500m, memory: 2Gi }
```

### 배포

```bash
# 스테이징
helm install todo ./todo-saas -f values-staging.yaml -n staging

# 프로덕션
helm install todo ./todo-saas -f values-prod.yaml -n prod

# 업그레이드
helm upgrade todo ./todo-saas -f values-prod.yaml -n prod
```

---

## 3. GitOps with ArgoCD — git push = 배포

수동 `helm upgrade` 도 잘 작동하지만, 누가 언제 뭘 배포했는지 추적이 어렵습니다. **GitOps** 는 git 저장소의 상태를 클러스터의 진실로 삼습니다.

```
[git repo: helm-deploy/]
        │
        ▼ ArgoCD watches
[ArgoCD Controller]
        │
        ▼ syncs to cluster
[Kubernetes cluster]
```

### ArgoCD Application 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: todo-prod, namespace: argocd }
spec:
  project: default
  source:
    repoURL: https://github.com/lemuel/helm-deploy
    targetRevision: main
    path: charts/todo-saas
    helm:
      valueFiles: ["values-prod.yaml"]
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated:
      prune: true            # git 에서 지운 리소스는 클러스터에서도 삭제
      selfHeal: true         # 누가 손으로 바꿔도 git 상태로 복원
```

### 효과

- **PR 머지 = 자동 배포** (별도 CD 파이프라인 X)
- **모든 변경 git 히스토리 추적** ("누가 언제 뭘 배포")
- **`git revert` = 즉시 롤백**

---

## 4. 한 페이지 통합 다이어그램

```
                ┌──────────────────────────┐
                │ Internet / 사용자        │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │ Ingress  (todo.lemuel.co)│  ← 6일차: TLS, NetworkPolicy
                └─────┬────────────────┬───┘
                      │                │
                  /                  /api
                      │                │
                      ▼                ▼
           ┌──────────────┐   ┌──────────────┐
           │ frontend SVC │   │ backend SVC  │
           │ + Deployment │   │ + Deployment │
           │  (3 replicas)│   │  (3 replicas)│   ← 4일차: RollingUpdate
           └──────────────┘   └──────┬───────┘
                                     │
                                     ▼
                          ┌────────────────────┐
                          │ postgres SVC       │
                          │ + StatefulSet      │   ← 3일차: PVC 20Gi
                          │ + PVC ReadWriteOnce│
                          └────────────────────┘
                                     │
                ┌────────────────────┴────────┐
                │ NetworkPolicy: backend only │   ← 6일차
                └─────────────────────────────┘

  [관측: Prometheus + Grafana + Loki]   ← 5일차
  [GitOps: ArgoCD watches helm-deploy/] ← 7일차
  [보안: SA + RBAC + SOPS Secret + restricted PSA] ← 6일차
```

---

## 5. 7일이 끝났습니다 — 그 다음은?

### 1주일 안에 시도해볼 것

- [ ] Helm chart 직접 만들고 PR 한 번 머지해보기
- [ ] Grafana 알람 4개 (CrashLoop / 메모리 / 5xx / 배포 후) 설정
- [ ] NetworkPolicy default-deny 적용 후 깨진 곳 고치기
- [ ] Pod Security Admission `baseline` → `restricted` 단계 올리기

### 2~4주 안에 더 깊이

- [ ] Service Mesh — Istio / Linkerd (Canary 정확히 % 배포)
- [ ] **Tracing** — OpenTelemetry + Tempo / Jaeger (3 기둥 마지막)
- [ ] HPA (Horizontal Pod Autoscaler) — CPU 기반 자동 확장
- [ ] Cluster Autoscaler — 노드 자동 추가/축소
- [ ] Backup — Velero 로 클러스터 + PV 통째로 백업

### 자격증/책 (선택)

- [Kubernetes 공식 문서](https://kubernetes.io/docs/) — 가장 정확한 레퍼런스
- 책: *Kubernetes in Action* (Marko Lukša) — 입문 정석
- 자격증: CKAD (개발자) → CKA (관리자) — 손에 익는 가장 빠른 길

---

## 핵심 한 줄 정리

- **Helm** = yaml 묶음 패키지 + 환경별 values 오버라이드
- **GitOps (ArgoCD)** = git push 가 곧 배포. 추적 + 자동 복원
- 1일차 ~ 6일차의 모든 개념이 한 chart 안에 통합된다
- 7일이 끝나면 — 진짜 운영자의 입구에 선다
- **다음은 service mesh, autoscaling, backup, 그리고 자격증**

수고하셨습니다! 7일 코스가 끝났습니다. 이제 여러분의 가장 가까운 작은 프로젝트를 클러스터에 직접 올려보세요. 거기서 진짜 학습이 시작됩니다.

---

> 시리즈 처음부터 다시 보고 싶다면 → [1일차 — 클러스터 아키텍처]({% post_url 2026-05-09-kubernetes-day1-architecture %})
