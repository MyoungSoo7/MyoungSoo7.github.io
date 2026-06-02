---
layout: post
title: "5노드 K3s 홈랩 *146 pod 분해* — 9개 카테고리·배포 방식·운영 흐름 분석"
date: 2026-06-02 21:45:00 +0900
categories: [infra, kubernetes, devops]
tags: [k3s, kubernetes, homelab, argocd, gitops, observability, elastic, kafka, prometheus, grafana, velero, pod-ecosystem]
---

5노드 K3s 클러스터 안에서 *146 개 pod* 가 동시에 굴러간다. *몇 개는 인프라*, *몇 개는 GitOps*, *몇 개는 관측성*, *몇 개는 실제 비즈니스 서비스*. 한 클러스터에 *너무 많은 종류* 가 섞여있어서 *전체 그림이 안 보일 때* 가 많다.

본 글은 *그 146 개 pod 를 *9 개 카테고리* 로 분해* 하고, *각 카테고리의 역할 / 배포 방식 / 노드별 분담 패턴* 을 정리한다. *홈랩을 처음 구축* 하려는 사람에게 *"이 정도 규모면 무엇이 필요한가"* 의 *참고 지도*.

> 본 글의 노드명·IP·도메인 등 *식별 정보는 모두 일반화*. *구조와 흐름* 만 다룬다.

---

## TL;DR

| 카테고리 | Pod 수 | 역할 | 배포 |
|---|---|---|---|
| 1. **코어 시스템** (kube-system) | 15 | DNS, 스토리지, 메트릭, 운영 cron | K3s 기본 + 추가 매니페스트 |
| 2. **GitOps** (ArgoCD) | 8 | 클러스터 전체 *형상 관리* | Bootstrap (Helm) + Self-managed |
| 3. **모니터링** | 11 | Prometheus, Grafana, node-exporter | ArgoCD app (kube-prometheus-stack) |
| 4. **로깅** | 14 | Elasticsearch (hot/warm/cold), Kibana, Logstash, Fluent-bit | ArgoCD app (eck-operator + 차트) |
| 5. **데이터** | ~15 | PostgreSQL (per-app), Redis, Kafka, MySQL | StatefulSet via ArgoCD |
| 6. **백업** (Velero) | 5 | S3 백업·복원 | ArgoCD app |
| 7. **운영 애플리케이션** (*-prod) | ~50 | 실제 비즈니스 서비스 (settlement, MSA 들) | ArgoCD + Image Updater |
| 8. **스테이징** (*-staging) | ~10 | 프로덕션 미리보기 환경 | ArgoCD + Image Updater |
| 9. **대시보드 / 기타** | ~5 | Kubernetes Dashboard 등 | ArgoCD app |

| 배포 방식 | 비율 | 비고 |
|---|---|---|
| **ArgoCD 자동 sync** (Git push → 적용) | ~95% | App-of-Apps 패턴 |
| **CronJob** (운영 자동화) | ~5% | etcd-leader-pin, secret-replicator 등 |
| **Manual kubectl** | ~0% | 비상 시에만 |

---

## 1. 5노드 토폴로지 — *역할 분담의 본질*

```
┌──────────────────────────────────────────────────────────────┐
│  Control Plane (etcd quorum 3/3)                              │
│                                                              │
│  Node-CP1  (cordoned, etcd 안정성 우선)                       │
│  Node-CP2  (control-plane + etcd + 일반 워크로드도)            │
│  Node-CP3  (control-plane + etcd + 데이터 워크로드 다수)        │
│                                                              │
│  Workers                                                     │
│  Node-W1   (일반 워크로드 + Cloudflare tunnel 트래픽 게이트웨이)  │
│  Node-W2   (백업·재해복구·대용량 디스크 풀)                       │
└──────────────────────────────────────────────────────────────┘
```

### 노드별 *명시적 역할 분담*

| 노드 | CPU/Mem | 주 역할 | 특이점 |
|---|---|---|---|
| CP1 | 4코어 / 31GB | etcd 안정화용 | cordon 처리 — 새 워크로드 안 받음 |
| CP2 | 8코어 / 15GB | 일반 워크로드 + 백엔드 트래픽 게이트웨이 | Cloudflare tunnel target |
| CP3 | 12코어 / 30GB | 데이터 워크로드 우선 | etcd leader pin 으로 raft 부하 집중 |
| W1 | 6코어 / 15GB | 일반 워크로드 | 작은 워크로드 다수 |
| W2 | 4코어 / 15GB | 백업·콜드 데이터 | 큰 디스크 (~700GB) |

### 분담의 *원칙*
1. **CP 가 워크로드도 받음** — 홈랩이라 노드 수 제약. *소규모 운영자의 현실*
2. **CPU 큰 노드 (12코어)** 에 *데이터 워크로드 우선* — DB / ES / Kafka 가 CPU 많이 씀
3. **디스크 큰 노드** 에 *백업·콜드 스토리지* — Velero · Elasticsearch cold tier
4. **부하 흐름** 한 노드 (W1) 가 *외부 인입 트래픽 게이트웨이* — Cloudflare tunnel 라우팅 단일점

---

## 2. 카테고리 1 — *코어 시스템* (kube-system, 15 pods)

K3s 가 *자체적으로 깔아주는* + *수동으로 추가한* 인프라 pod 들.

### 주요 구성
```
coredns × 2              — 클러스터 내부 DNS (kubernetes.default.svc → IP)
node-local-dns × 5       — 각 노드에 가까운 DNS 캐시 (latency 절감)
metrics-server × 1       — kubectl top, HPA 용 메트릭 수집
local-path-provisioner × 1  — hostPath PVC (단일 노드 영구 저장)
elastic-secret-replicator (CronJob) × 3  — namespace 간 secret 동기화
etcd-leader-pin (CronJob) × 3            — etcd raft leader 강제 고정
```

### *왜 이게 필요한가*
- **coredns**: pod 가 *서비스 이름* 으로 통신 (예: `settlement.cluster.local`). *없으면 IP 직접* — 운영 불가
- **node-local-dns**: pod → coredns 매번 호출하면 *latency + load*. *각 노드 캐시* 로 90% 단축
- **etcd-leader-pin** (CronJob): etcd raft leader 가 *작은 노드* 에 가면 *load5 100%* 까지 튐. *큰 노드 에 고정* 으로 안정화

### 배포 방식
- K3s 기본 (coredns, local-path-provisioner, metrics-server)
- 추가 — *cluster-ops 매니페스트* (ArgoCD app `cluster-ops`)
  ```
  cluster-ops/
  ├── elastic-secret-replicator.yaml
  ├── etcd-leader-pin.yaml
  ├── elastic-system/
  └── pod-restart-alert-rule.yaml
  ```

---

## 3. 카테고리 2 — *GitOps* (ArgoCD, 8 pods)

클러스터 전체의 *형상 관리* 가 여기 다 모임. *git push → 적용* 의 핵심.

### 8개 pod
```
argocd-application-controller     — Application object 의 sync 처리 (StatefulSet)
argocd-server                     — 웹 UI + API (외부 노출 가능)
argocd-applicationset-controller  — ApplicationSet 매니저 (다중 환경)
argocd-image-updater              — 컨테이너 이미지 자동 업데이트
argocd-notifications-controller   — Slack/Telegram 알람
argocd-redis                      — sync 상태 캐시
argocd-repo-server                — Git/Helm 차트 fetch + manifest 렌더
argocd-dex-server                 — SSO 게이트웨이 (OIDC)
```

### *App-of-Apps* 패턴
```
root-app (Application)
   ↓ watch argocd-applications/ 디렉토리
   ├── academy-prod.yaml
   ├── settlement-prod.yaml
   ├── lemuel-xr-prod.yaml
   ├── sparta-prod.yaml
   ├── ... (총 30+개 Application)
   └── elk/
       ├── 01-elastic-operator.yaml
       ├── 02-elastic-cluster.yaml
       └── 03-fluent-bit.yaml
```

→ **새 서비스 추가 = `argocd-applications/<name>.yaml` 한 파일 commit**. ArgoCD root-app 이 자동으로 발견 + sync.

### Image Updater 의 마법
- ghcr.io / private registry 의 *새 이미지 push* 를 *자동 감지*
- ArgoCD 의 *Helm values* 또는 *Kustomize parameters* 자동 갱신
- *git commit 도 자동* — 운영자 개입 없이 *코드 배포 → 자동 운영 반영*

→ 결과: **새 commit push → 5분 안에 운영 반영**, *수동 작업 0*.

---

## 4. 카테고리 3 — *모니터링* (monitoring, 11 pods)

### 구성 (kube-prometheus-stack 기반)
```
kps-prometheus-0              — 메트릭 시계열 저장 (StatefulSet)
kps-grafana                   — 대시보드 + Alerting UI
kps-alertmanager-0            — 알람 라우팅 (Slack/Telegram/Email)
kps-prometheus-node-exporter × 5  — 각 노드의 시스템 메트릭 (CPU/메모리/디스크)
kps-kube-state-metrics        — K8s 리소스 상태 메트릭 (pod 개수, restart 등)
kps-operator                  — Prometheus/Alertmanager CRD 매니저
```

### 데이터 흐름
```
[ pod 의 /metrics 엔드포인트 ]
        ↓ scrape (15s 간격)
[ Prometheus ]
        ↓ alert rules 평가
        ↓ ────────────→ [ Alertmanager ] → Slack / Telegram
        ↓
[ Grafana ]  ←── query  
        ↓
[ 사용자 ]
```

### 자체 만든 *알람 룰*
- `pod_restart_loop` — 분당 1회 이상 재시작 시 Telegram
- `node_cpu_high` — CPU > 90% 10분 지속 시 warning
- 등등

---

## 5. 카테고리 4 — *로깅* (logging, 14 pods)

가장 *복잡한* 카테고리. *ECK Operator + 3-tier ES + Fluent-bit + Logstash + Kibana*.

```
elastic-operator-0           — ECK Operator (Elasticsearch CRD 매니저)
logs-es-hot-0                — Elasticsearch hot tier (최근 7일, NVMe)
logs-es-warm-0               — Elasticsearch warm tier (7~30일)
logs-es-cold-0               — Elasticsearch cold tier (30일+ / 대용량 디스크)
logs-kb-...                  — Kibana
logs-ls-0                    — Logstash (Fluent-bit → Logstash → ES, 변환)
fluent-bit × 4 (DaemonSet)   — 각 노드의 컨테이너 로그 수집
kb-dashboards-import         — Kibana 대시보드 자동 import (Job)
log-error-alerter (CronJob)  — ES 에 ERROR 누적 시 알람
```

### *3-tier ES* 의 효과
- *hot* (NVMe) — 실시간 검색·indexing 빠름
- *warm* (SSD) — 검색은 가능, indexing 안 함
- *cold* (HDD) — 압축·archived. 검색 가능 (느림)
- **자동 lifecycle 으로 이동** — ILM 정책

### 흐름
```
[ Pod stdout ] → /var/log/containers/*.log
                        ↓
                  [ fluent-bit DaemonSet (각 노드) ]
                        ↓ HTTP POST
                  [ Logstash ] (grok/dissect 변환)
                        ↓
                  [ Elasticsearch hot tier ]
                        ↓ 7일 후 자동
                  [ warm tier ]
                        ↓ 30일 후 자동
                  [ cold tier ]
                        ↓ 90일 후
                  [ 삭제 ]
```

### 비용 관리
- ES 가 *디스크 비용 폭발* 원인 1위
- ILM 으로 *자동 이동* + *삭제* 안 하면 *6개월 후 디스크 가득*
- fluent-bit 에서 *kube-system 로그 제외* 등 *필터링* 도 중요

---

## 6. 카테고리 5 — *데이터* (DB / Kafka, ~15 pods)

### 각 *애플리케이션* 별 *전용 DB*
```
academy-postgres-0           — academy 서비스 전용
academy-staging-postgres-0   — staging
settlement-prod 도 PostgreSQL 사용 (공유 또는 별도)
asat-postgres-0
cost-postgres-0
crypto-postgres-0
dart-postgres-0
database-mysql-0             — 다목적 MySQL
```

### *DB-per-Service* vs *Shared DB*
- 본 클러스터는 *DB-per-Service* 채택
- 장점: *서비스 독립성* (한 DB 죽어도 다른 서비스 영향 0)
- 단점: *DB 인스턴스 수 ↑* → 운영 부담
- 트레이드오프: *홈랩 규모* 라 *서비스 독립성 우선*

### Kafka (Redpanda)
- `kafka` 네임스페이스, 3 pods
- Outbox 패턴의 *메시지 백본*
- 결제 → 정산, 주문 → 알림 등 비동기 흐름

### Redis
- 서비스마다 *전용 Redis* (academy-redis, asat-redis, ...)
- 세션 / 캐시 / Rate limiting 용도

---

## 7. 카테고리 6 — *백업* (Velero, 5 pods)

```
velero-server         — 백업 컨트롤러
velero-restic × 5     — 각 노드의 PV 스냅샷 데몬 (DaemonSet)
```

### 백업 정책
- *일별*: 모든 PV → S3 (또는 NFS) 스냅샷
- *주별*: 클러스터 전체 매니페스트 + PV
- *보관*: 일별 30일, 주별 12주

### 복구 시나리오
- *PV 손상* → Velero 로 *전 단계 스냅샷* 복원 (15분)
- *클러스터 전체 재구축* → Velero 의 *매니페스트 + 데이터* 로 *2~3시간 안에* 복구

### 왜 *별도 백업* 인가
- ArgoCD 는 *매니페스트 만* 형상 관리 — *PV 안의 데이터는 안 함*
- DB / Kafka / ES 데이터는 *Velero* 가 담당
- *둘이 함께* 있어야 *완전한 복구 가능*

---

## 8. 카테고리 7 — *운영 애플리케이션* (~50 pods)

실제 *비즈니스 서비스* 들. 각 네임스페이스가 *하나의 마이크로서비스 묶음*.

### 네임스페이스 분포 예시
```
academy-prod          — 9 pods (frontend + 5 backend MSA + redis + postgres)
sparta-prod           — 6 pods (msa 묶음)
fashion-prod          — 5 pods (이커머스)
asat-prod             — 5 pods
lemuel-xr-prod        — 4 pods (XR 콘텐츠)
goods-prod, sns-prod, jabis-prod, ... — 각 3~4 pods
settlement-prod       — 3 pods (gateway + order + settlement)
... (총 15+개 prod 네임스페이스)
```

### 공통 패턴 (헥사고날 + MSA)
- **Frontend** (Next.js / React) — Nginx 로 정적 서빙
- **API Gateway** (Spring Cloud Gateway) — 인증 + 라우팅
- **Backend MSA** — 도메인별 Spring Boot
- **DB**: 서비스 전용 (StatefulSet)
- **Redis**: 세션·캐시
- **Kafka producer/consumer**: 비동기 이벤트

### 배포 흐름 (settlement 예시)
```
[ 개발자 git push to settlement repo ]
        ↓
[ GitHub Actions CI ]
        ↓ build image
[ ghcr.io / private registry ]
        ↓
[ ArgoCD Image Updater 감지 ]
        ↓ helm-deploy 의 values 자동 갱신 commit
[ ArgoCD root-app sync ]
        ↓
[ K3s 에 새 이미지 rollout ]
        ↓
[ 운영 반영 (5분) ]
```

→ *git push → 운영 반영* *완전 자동화*. 사람 개입 0.

---

## 9. 카테고리 8 — *스테이징* (~10 pods)

```
academy-staging       — 8 pods (prod 미러)
settlement-staging    — 2 pods
```

### 스테이징의 의미
- *프로덕션 환경 미리보기* — 새 기능 / 마이그레이션 / 부하 테스트
- *같은 이미지·매니페스트, 다른 데이터*
- *develop 브랜치 CI 통과 → 스테이징 자동 배포*
- 사람이 확인 후 *develop → main PR* → *prod 배포*

---

## 10. 카테고리 9 — *대시보드 / 기타* (~5 pods)

```
kubernetes-dashboard          — K8s 리소스 GUI (kubectl 대체)
homelab-dashboard             — 자체 만든 통합 대시보드
display-order                 — QR 코드 라벨 시스템 (작은 SPA)
```

---

## 11. *왜 이렇게 많은가* — 홈랩의 *현실적 트레이드오프*

### *146 pod 가 *너무 많아 보일 수 있다*
- 운영자 1명에 *146 pod* — 일반적이지 않음
- 그러나 *각 카테고리가 다른 학습 목적*
- *모니터링·로깅·백업* 같은 *프로덕션 운영* 의 *기본 구성요소* 가 *그 자체로 50%* 차지
- 실제 *비즈니스 서비스* 는 *50 개 정도* — *normal* 한 규모

### 왜 *MSA 가 그렇게 많은가*
- *포트폴리오 + 학습* — 다양한 도메인 (academy, settlement, fashion, ...) *학습 목적*
- *대기업 가정* 시 *현실적인 클러스터 규모* — 100~200 pod 흔함
- *복잡성 학습* — *단일 모놀리스* 만 만들면 *분산 시스템의 진짜 어려움* 못 만남

### *5노드면 충분한가*
- *충분* — *146 pod / 5 노드 = 노드당 ~30 pod*. K8s 권장 ≤ 110 per node
- 단 *한 노드 죽으면* *그 위 pod 들 다른 노드로 재스케줄* → 다른 노드 부하 ↑
- *etcd quorum 3* 이 *최소* — 2/3 도 OK 지만 *한 번 더 죽으면 split brain*

---

## 12. 배포 흐름 종합 — *한 그림으로*

```
┌─────────────────────────────────────────────────────────────────┐
│  개발자 / 운영자                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 1. git push (app repo or helm-deploy)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  GitHub                                                         │
│  - 코드 리포 (settlement, academy, ...)                          │
│  - helm-deploy 리포 (매니페스트 + values)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 2. GitHub Actions CI
                           │    - 빌드
                           │    - 테스트
                           │    - 이미지 push to ghcr.io
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ghcr.io (Container Registry)                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 3. ArgoCD Image Updater 가 감지
                           │    helm-deploy 의 values 자동 갱신 commit
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ArgoCD (cluster 내부)                                          │
│  - root-app: argocd-applications/ 디렉토리 watch                  │
│  - 각 Application: helm-deploy 의 한 yaml 감지                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 4. sync — 매니페스트 적용
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  K3s (5 nodes)                                                  │
│  - rolling update                                               │
│  - readiness probe 통과 후 트래픽 전환                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 5. 외부 노출
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Cloudflare Tunnel                                              │
│  - hostname per service                                         │
│  - SSL 자동 (Cloudflare 가 termination)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                  [ 외부 사용자 ]
```

---

## 13. *흥미로운 관찰* 5가지

### 1. *코어 운영 인프라가 *비즈니스 보다 비싼* 경우*
모니터링 (11 pod) + 로깅 (14 pod) + 백업 (5 pod) = **30 pod** 가 *순수 인프라*. 
실제 비즈니스 (settlement-prod = 3 pod) 보다 **10배**. *홈랩의 함정* — 인프라 학습이 *목표 자체* 가 되기 쉬움.

### 2. *DB 인스턴스가 인스턴스 폭발*
서비스 10개 → DB 인스턴스 10개. *작은 단위로 분리* 의 비용. 대규모에선 *managed DB* (RDS, Cloud SQL) 가 답이지만 *홈랩에선 self-host*.

### 3. *cron 잡이 *조용한 영웅**
- `etcd-leader-pin`: 매일 raft leader 강제 고정 — *load5 100% 사고 예방*
- `elastic-secret-replicator`: namespace 간 secret 동기화
- *cron 없이는 운영자가 *수동으로 매일 같은 작업*. 자동화의 ROI 가 가장 큰 영역.

### 4. *GitOps 가 *형식이 아니라 실체**
- 새 서비스 추가 = yaml 한 파일 commit
- 운영 반영 = 자동 5분
- 롤백 = git revert + push
- *이게 *제대로* 동작하면 운영 부담 80% 감소*

### 5. *5노드 중 1 노드가 *외부 트래픽 단일점**
Cloudflare tunnel 라우팅이 *한 노드 IP* 를 가리키고 있음. *그 노드 죽으면* 외부 접근 *전부 다운*. *단일점 (SPOF)*. 개선 옵션: *NodePort 가 모든 노드에 열려있으니 다른 노드 IP 로 라우트 변경* (수동).

---

## 14. 결론 — *홈랩 = 작은 회사*

### *5노드 K3s 의 *진짜 가치**
- *프로덕션 운영* 의 *기본 구성요소* 를 *한 개인이 다 배움*
- ArgoCD / Prometheus / ELK / Velero — *대기업에서도 같은 도구*
- *처음부터 끝까지 *내가 만든 시스템*

### 학습 우선순위 추천 (홈랩 입문자에게)
1. K3s 설치 + 노드 1개 (1주차)
2. ArgoCD + root-app + 첫 서비스 배포 (2주차)
3. Prometheus + Grafana + 알람 (3주차)
4. ELK + Fluent-bit (4주차)
5. Velero 백업 (5주차)
6. *그 다음* 비즈니스 서비스 본격화

이 순서로 가면 *모니터링·로깅 없이 비즈니스 먼저 시작* 했을 때의 *2개월 후 후회* 를 피한다.

### *마지막* — *146 pod 의 의미*
숫자 자체는 *과시* 가 아니라 *현대 운영의 현실*. 단일 모놀리스 시대엔 *프로세스 5개* 면 충분했지만, *MSA + 옵저버빌리티 + GitOps* 의 결합은 *자연스럽게 100+ pod*. *각 pod 가 *왜* 있는지* 명확히 알면 *복잡함이 *질서가 된다*.

다음 글에선 *ArgoCD App-of-Apps 패턴* 의 *실전 구성* — 30+ Application 을 *한 root-app* 으로 관리하는 *디렉토리 구조 + sync wave* 를 정리할 예정.
