---
layout: post
title: "Docker → K8s 마이그레이션 1일차 — 왜, 언제, 어떻게 옮길까"
date: 2026-05-09 14:30:00 +0900
categories: [infra, kubernetes]
tags: [docker, kubernetes, migration, docker-compose, helm]
---

> 이 시리즈는 르무엘이 docker compose 환경 → 쿠버네티스 K3s 클러스터로 옮긴 실 사례입니다.

도커 컴포즈가 잘 동작하는데 굳이 쿠버네티스로 옮길 필요가 있을까요? 7일에 걸쳐 답해봅니다.

> 이 글에서 다루는 것
> - 도커 컴포즈로 충분한 경우 / 옮겨야 할 신호
> - 마이그레이션 전 체크리스트 5가지
> - 1일차 작업: docker-compose.yml → k8s yaml 자동 변환 (kompose)
> - 자동 변환의 한계 + 손으로 다듬어야 할 4가지

---

## 1. 옮길까 말까 — 5가지 신호

### 도커 컴포즈가 충분한 경우

- 서버 1~2 대 / 컨테이너 10개 이하
- 다운타임 5분 허용 (배포 중 재시작 OK)
- 팀 1~2명
- 트래픽 < 100 RPS

### 옮겨야 할 신호

| 신호 | 컴포즈의 한계 | K8s 의 답 |
|---|---|---|
| 서버 한 대로는 못 버틸 트래픽 | 멀티 호스트 미지원 (swarm 별도) | 워커 노드 자유롭게 추가 |
| 무중단 배포 필수 | `restart` 시 다운타임 | RollingUpdate + readinessProbe |
| 새벽 자동 복구 필요 | restart=always 만, 노드 단위 페일오버 X | 자동 재스케줄 |
| 배포 환경 분리 | env file 노가다 | namespace + values 분리 |
| 모니터링 통합 | 손으로 깔아야 | Prometheus Operator 표준 |

3개 이상 해당하면 옮길 가치 있음.

---

## 2. 마이그레이션 전 체크리스트

- [ ] 컴포즈에서 정적 IP / 호스트포트 의존이 있는가? → Service / Ingress 로 추상화
- [ ] 데이터 볼륨이 어떤 종류? → bind mount = hostPath 위험, named volume = PVC
- [ ] 컨테이너가 root 로 실행되는가? → securityContext 필요
- [ ] 환경변수에 비밀번호 평문? → Secret 으로 옮겨야
- [ ] init script 가 있는가? → InitContainer 로

---

## 3. kompose — docker-compose.yml 자동 변환

```bash
brew install kompose

# 변환
kompose convert -f docker-compose.yml -o k8s/

# 결과
ls k8s/
# postgres-deployment.yaml
# postgres-service.yaml
# academy-deployment.yaml
# academy-service.yaml
# ...
```

각 service 가 Deployment + Service 로 변환됩니다.

### kompose 의 한계

자동 변환의 결과는 **시작점일 뿐**, 그대로 운영에 못 씁니다.

| 컴포즈 | 자동 변환 결과 | 운영에 필요한 것 |
|---|---|---|
| `volumes: db:/var/lib/postgresql` | emptyDir 또는 hostPath | **PVC + StorageClass** |
| `restart: always` | `restartPolicy: Always` | + readiness/liveness probe |
| `environment: PASSWORD=xxx` | Deployment env 평문 | **Secret 으로 분리** |
| `ports: 8080:8080` | NodePort Service | **ClusterIP + Ingress** |
| 단일 replicas | `replicas: 1` | 무중단 위해 ≥ 2 + RollingUpdate |

---

## 4. 손으로 다듬어야 할 4가지

### A) Volume → PVC

```yaml
# Before (kompose 결과)
volumes:
  - name: db-data
    hostPath: { path: /home/iamipro/data }   # 노드 의존

# After
volumes:
  - name: db-data
    persistentVolumeClaim: { claimName: db-data }
```

### B) ConfigMap + Secret 분리

```yaml
# Before
env:
  - name: DATABASE_URL
    value: postgres://lemuel:S3cret@db:5432/lemuel

# After: ConfigMap 에 URL, Secret 에 비밀번호
envFrom:
  - configMapRef: { name: app-config }
  - secretRef: { name: db-cred }
```

### C) probe 추가

```yaml
readinessProbe:
  httpGet: { path: /actuator/health, port: 8080 }
  initialDelaySeconds: 10
livenessProbe:
  httpGet: { path: /actuator/health, port: 8080 }
  initialDelaySeconds: 30
  periodSeconds: 30
```

### D) Ingress 도입

```yaml
# 외부 접근은 NodePort 가 아니라 Ingress 로
apiVersion: networking.k8s.io/v1
kind: Ingress
spec:
  rules:
    - host: academy.lemuel.co.kr
      http:
        paths:
          - { path: /, backend: { service: { name: academy, port: { number: 80 } } } }
```

---

## 5. 르무엘의 실제 마이그레이션 순서

저는 다음 순서로 작은 서비스부터 옮겼습니다.

1. **Day 1** (오늘) — docker-compose 분석 + kompose 자동 변환
2. **Day 2** — 가장 stateless 한 서비스 1개 K3s 에 올림 (위험 적음)
3. **Day 3** — DB 같은 stateful → StatefulSet + PVC
4. **Day 4** — Ingress + Cloudflare Tunnel 통합
5. **Day 5** — Helm 차트로 묶기 + 환경별 values
6. **Day 6** — Prometheus + Grafana 모니터링
7. **Day 7** — GitOps (ArgoCD) 로 전 서비스 자동 배포

7일 후엔 docker-compose.yml 은 history 가 됩니다.

---

> 이 시리즈와 [Kubernetes 입문 7일 시리즈]({% post_url 2026-05-09-kubernetes-day1-architecture %}) 를 함께 보면 흐름이 매끄럽습니다.
