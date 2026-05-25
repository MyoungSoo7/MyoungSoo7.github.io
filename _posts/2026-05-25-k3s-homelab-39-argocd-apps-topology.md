---
layout: post
title: "운영 K3s 홈랩 한 장 — 39 ArgoCD App · 5 노드 · 영어 용어 사전 포함"
date: 2026-05-25 11:55:00 +0900
categories: [infra, kubernetes, gitops]
tags: [k3s, argocd, image-updater, etcd, traefik, helm, sops, observability, homelab]
---

홈랩 K3s 클러스터에 39개 ArgoCD 애플리케이션이 돌고 있다. 어느 날 누가 *"이거 한 장으로 보여줘"* 라고 하면 그릴 수 있는 그림 — 그리고 *그 그림에 박힌 영어 용어들* 을 같이 풀어쓴 글.

> 영어 용어는 **굵게 + (한글 풀이)** 로 첫 등장에 표기. 끝에 [§9 용어 사전](#9-용어-사전-사전순) 도 따로.

---

## 1. 노드 토폴로지 — 5 노드 중 실제 작동 4

```text
┌────────────────────────────────────────────────────────────────┐
│  K3s Cluster  (v1.35.4+k3s1, Ubuntu 24.04 / 26.04 혼합)         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   lemuel     │  │    ilwon     │  │       solomon        │  │
│  │ 219.101      │  │ 219.110      │  │ 219.108              │  │
│  │ control+etcd │  │ control+etcd │  │ control+etcd         │  │
│  │ ⚠ Sched X   │  │ ✅ Ready     │  │ ✅ Ready              │  │
│  │ (etcd only)  │  │              │  │ taint=storage        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│        │                  │                    │                │
│        └──────────────── etcd quorum (3/3) ────┘                │
│                                                                 │
│  ┌──────────────┐                                               │
│  │   louise     │       ┌──────────────────┐                    │
│  │ 219.109      │       │  david           │  ❌ NotReady (17h) │
│  │ worker only  │       │  219.107         │     유선 시도 실패  │
│  │ ✅ tier=worker│      │  (배제)          │     helm refs 4곳 │
│  └──────────────┘       └──────────────────┘     임시 비활성화   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 용어

- **Control plane (제어 평면)** — Kubernetes 의 *결정 두뇌*. API 요청 받고 *클러스터 상태* 를 etcd 에 저장, 어느 워크로드를 어느 노드에 띄울지 결정.
- **etcd quorum (이트시디 합의)** — 분산 키-값 저장소의 *다수결*. 3 노드면 2 이상 살아 있어야 쓰기 가능. 1 노드 죽어도 OK, 2 죽으면 클러스터 마비.
- **SchedulingDisabled (스케줄링 차단)** — 노드를 *드레인(drain)* 한 상태. 새 Pod 안 받음. 보통 점검·드레이닝 시. 이 클러스터의 `lemuel` 은 *control-plane + etcd 만 책임지고 워크로드는 안 받음* 으로 의도적 cordon.
- **Taint / Toleration (테인트 / 톨러레이션)** — 노드에 *얼룩(taint)* 을 묻혀 두면 그 얼룩을 *참아낼(tolerate)* 수 있는 Pod 만 들어옴. `solomon` 의 `dedicated=storage:PreferNoSchedule` 은 *스토리지 워크로드 우선* 의도.
- **NotReady (준비 안 됨)** — 노드의 kubelet 이 API server 에 *하트비트(heartbeat)* 를 못 보내는 상태. 5분 이상 지속 시 컨트롤매니저가 그 노드의 Pod 들을 다른 노드로 옮김.

### 실효 운영 능력

- **etcd quorum**: 3/3 (정상). lemuel SchedulingDisabled 여도 etcd 는 살아 있음.
- **워커 노드**: louise(전용) + ilwon/solomon(겸직) = **실효 워커 3**. david 빠진 후도 운영 OK.
- **사고 한 건**: `david` 가 어제(2026-05-23) NotReady → 유선 연결 시도했지만 결국 안 됨 → 일단 배제. helm-deploy 의 david 참조 4곳에 *"노드 복구 전까지 nodeSelector 제거"* 임시 주석.

---

## 2. GitOps 흐름 — `main` push 한 번이면 끝

```text
┌─────────┐
│ 개발자  │  git push main
└────┬────┘
     │
     ▼
┌──────────────────────┐
│  App Repo            │  GitHub Actions:  build + test
│  (lemuel-xr,         │  → docker build
│   sparta-msa,        │  → push to GHCR
│   settlement, ...)   │     image:latest + image:{sha}-build-{N}
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  GHCR                │   ← (1) container image registry
│  (컨테이너 이미지)    │
└──────┬───────────────┘
       │ 60s polling
       ▼
┌──────────────────────┐
│  ArgoCD              │   GHCR 의 newest-build tag 추적
│  Image Updater       │   → helm-deploy 의 values.yaml 자동 commit
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  helm-deploy Repo    │   ← (2) GitOps source-of-truth
│  (charts + values    │
│   + argocd-apps)     │
└──────┬───────────────┘
       │ 3min reconcile
       ▼
┌──────────────────────┐
│  ArgoCD              │   git fetch → drift 감지 → helm apply
│  Application         │
│  Controller          │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  K3s Cluster         │   rolling update (ReplicaSet 신규 생성)
│                      │   Pod 1/1 Ready 까지 90s + probe period
└──────────────────────┘
```

### 용어

- **GitOps (깃옵스)** — *원하는 클러스터 상태(desired state)* 를 git 에 선언적(declarative)으로 두고, 컨트롤러가 *실제 상태(actual state)* 를 git 에 맞춰 끌어당기는 운영 방식.
- **GHCR (GitHub Container Registry)** — GitHub 가 제공하는 컨테이너 이미지 저장소. `ghcr.io/{owner}/{image}:{tag}` 형식.
- **ArgoCD (아르고씨디)** — Kubernetes 용 GitOps 컨트롤러. *git 의 manifest* 와 *클러스터 실제 상태* 를 비교해서 drift (차이) 를 자동 sync.
- **Image Updater** — ArgoCD 의 *플러그인*. 컨테이너 레지스트리의 새 태그를 polling 해서, 자동으로 helm-deploy 의 `image.tag` 값을 갱신·commit. 개발자가 helm-deploy push 안 해도 됨.
- **Rolling update (롤링 업데이트)** — 새 ReplicaSet(레플리카셋) 의 Pod 들이 *준비될 때까지* 기다린 후 옛 Pod 들을 점진적으로 종료. 다운타임 0.
- **Reconcile (재조정)** — *목표 상태와 현재 상태를 일치시키는 루프*. ArgoCD 는 3분마다 자동 reconcile.
- **Drift (드리프트)** — git 선언과 클러스터 실제 상태의 *차이*. 누가 손으로 kubectl edit 하면 drift 가 생기고, ArgoCD 가 다음 reconcile 에서 되돌림.

---

## 3. 워크로드 분류 — 39 ArgoCD 애플리케이션

```text
🏛️ Lemuel 자체 서비스 (6)
├── lemuel-xr-prod         영적 단련 교육 (XR + AR)
├── sparta-prod            이커머스 MSA (Lemuel Mall)
├── settlement-prod        주문·결제·정산 시스템
├── landing-prod           홈 페이지
├── pilgrim-prod           순례자 트래커
└── asat-prod              asat 서비스

🎓 학습/포트폴리오 (20)
├── academy · ghost · jen · grid
├── fashion · goods · livecommerce · lowshopping · pharmacy
├── crypto · trading · jabis · dart · media-search · report · data
└── serverless · codingtest · sns

📊 관측·인프라 (10)
├── elk-cluster + elk-storage + eck-operator + eck-patches  ─ 로그
├── monitoring-prod (kube-prometheus-stack)                 ─ 메트릭
├── tempo                                                    ─ 트레이싱
├── fluent-bit                                              ─ 로그 수집 DaemonSet
├── uptime-kuma-prod                                        ─ 외형 헬스체크
└── cluster-ops + infra-ssd + database-prod                 ─ 기반

🔐 GitOps 자체 (2)
├── root-app  (app-of-apps 패턴)
└── argocd  (image-updater 포함)

총 39 ArgoCD applications
```

현재 OutOfSync 4건 (`elk-cluster`, `elk-storage`, `lemuel-xr-prod`, `tempo`) — *진행 중인 변경* 또는 manual override 대기.

### 용어

- **Namespace (네임스페이스)** — Kubernetes 의 *논리적 폴더*. 같은 클러스터 안에서 리소스를 격리하는 단위. `cost-prod`, `lemuel-xr-prod` 처럼 `-prod` suffix 로 환경 표시.
- **app-of-apps 패턴** — `root-app` 이라는 하나의 ArgoCD Application 이 *다른 ArgoCD Application 들의 정의 자체* 를 관리. 새 서비스 추가 시 manifest 만 git push 하면 자동 등록.
- **OutOfSync / Healthy / Progressing** — ArgoCD 의 두 가지 직교 차원:
  - *Sync status* — git 과 클러스터의 일치 (Synced / OutOfSync)
  - *Health status* — 워크로드 자체의 상태 (Healthy / Progressing / Degraded)
- **MSA (Microservice Architecture, 마이크로서비스 구조)** — 하나의 큰 모놀리식 앱이 아니라 *작고 독립 배포 가능한 서비스* 들의 집합. sparta-prod 는 user/order/product 등 ~10개 서비스.

---

## 4. 관측 stack — *어디가 아픈지* 알려주는 3 축

```text
┌──────────────────────────────────────────────────────────┐
│  각 노드 (DaemonSet — 모든 노드에 1개씩)                  │
│  ├── fluent-bit          로그 수집 (각 Pod 의 stdout)     │
│  ├── node-exporter       호스트 메트릭 (CPU/mem/disk/net) │
│  └── node-local-dns      DNS 캐시 (CoreDNS 부담 ↓)       │
└──────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼

  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  ELK Stack   │  │  Prometheus  │  │   Tempo      │
  │              │  │              │  │              │
  │  Logstash    │  │  scrape:     │  │  분산 트레이싱│
  │  → ES (3 tier│  │   - node-exp │  │  (OpenTelem) │
  │     hot/warm │  │   - kube-state│ │              │
  │     /cold)   │  │   - app /metrics│              │
  │  → Kibana    │  │  →  Grafana  │  │  →  Grafana  │
  └──────────────┘  └──────────────┘  └──────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Uptime Kuma     │
                  │  외형 헬스 28 URL │
                  │  (alert → 카톡)  │
                  └──────────────────┘
```

### 용어

- **DaemonSet (데몬셋)** — *모든 노드에 1개씩* 자동으로 Pod 를 띄우는 Kubernetes 컨트롤러. 노드 추가되면 그 노드에도 자동 생성. 로그 수집·메트릭 수집 같은 *노드 단위 책임* 에 적합.
- **fluent-bit** — *경량 로그 수집기*. 각 Pod 의 표준 출력(stdout) 을 캡처해서 Logstash/Elasticsearch 로 전달. CPU·메모리 소모 적음.
- **ELK Stack** — Elasticsearch + Logstash + Kibana. *로그* 영역의 사실상 표준. ECK = ElasticSearch on Kubernetes operator.
- **Prometheus (프로메테우스)** — *메트릭(metric, 시간에 따른 숫자)* 수집의 사실상 표준. 각 앱에 `/metrics` HTTP 엔드포인트만 노출하면 자동 scrape.
- **Grafana (그라파나)** — Prometheus/Tempo/Loki 데이터를 *그래프·대시보드* 로 보여주는 UI.
- **Tempo (템포)** — *분산 트레이싱(distributed tracing)* — 한 요청이 여러 마이크로서비스를 거치는 흐름을 *한 줄의 trace* 로 시각화. settlement 처럼 N개 서비스 거치는 흐름에서 *어디가 느린지* 한 눈에.
- **OpenTelemetry (오픈텔레메트리)** — *벤더 중립* 의 관측 데이터 표준 (trace + metric + log). Tempo / Prometheus / Loki 모두 이걸 받음.
- **Uptime Kuma (업타임 쿠마)** — *외형 헬스체크*. 사용자가 보는 URL 을 *외부에서* 호출해서 5xx 떴는지 / 응답 느려졌는지 측정. 내부에서 *Healthy* 라고 해도 외부에서 안 보이면 의미 없음 ([어제 글의 핵심](/2026/05/20/production-agent-goal-completed-external-verification/)).

---

## 5. 외부 진입 — 도메인 → 서비스

```text
USER (https)
   │
   ▼
┌─────────────────────┐
│  Traefik            │   K3s 기본 ingress controller
│  (ingress-class:    │   :80 → :443 자동 리다이렉트
│   traefik)          │   ACME Let's Encrypt 자동 갱신
└────────┬────────────┘
         │
         ├──→ xr.lemuel.co.kr            → lemuel-xr-prod
         ├──→ chat.lemuel.co.kr          → sparta-prod (Lemuel Mall)
         ├──→ lemuel.co.kr               → landing-prod
         ├──→ settlement.lemuel.co.kr    → settlement-prod
         ├──→ argocd.lemuel.co.kr        → argocd
         ├──→ grafana.lemuel.co.kr       → grafana
         ├──→ kibana.lemuel.co.kr        → kibana
         └──→ kuma.lemuel.co.kr          → uptime-kuma
```

### 용어

- **Ingress (인그레스)** — 클러스터 *바깥의 HTTP 트래픽* 을 *안쪽 Service* 로 라우팅하는 Kubernetes 리소스. *Ingress Controller* 가 실제 라우팅 담당.
- **Traefik (트래픽)** — K3s 가 *기본 내장* 한 Ingress Controller. nginx-ingress 대비 *동적 설정* 강함 (Ingress 리소스 추가 즉시 반영).
- **ACME / Let's Encrypt** — *무료 TLS 인증서* 자동 발급·갱신 프로토콜. Traefik 가 ACME challenge 처리.
- **Service (서비스)** — Pod 의 *안정적 네트워크 식별자*. Pod 이 죽고 새로 떠도 Service IP 는 그대로.

---

## 6. 안전선·운영 정책 — 한 줄씩

- **etcd quorum 보호**: 3 control-plane 노드 중 *2 이상 항상 Ready*. lemuel SchedulingDisabled 여도 etcd 는 살아 있음.
- **PriorityClass `lemuel-production`**: Lemuel 자체 6개 서비스에 부여 → *자원 부족 시* 이 Pod 들이 우선 스케줄, 다른 Pod 가 evict.
- **LimitRange (네임스페이스 한도)**: 각 namespace 에 `burstRatio.memory=2` 등 강제. 임의 Pod 가 노드 메모리 다 먹는 사고 방지.
- **PDB (PodDisruptionBudget)**: 주요 StatefulSet (postgres / ECK) 에 *최소 1개 보장* — 노드 드레인 시 한 번에 다 죽지 않도록.
- **SOPS + age**: 시크릿 (DB 비번 / API 키) 은 git 에 *암호화된 형태로* 저장. age 키 가진 사람만 복호화 가능.
- **Image Updater 듀얼 태그 정책**: `:latest` (인간 가독) + `:{sha}-build-{N}` (불변 식별자). Image Updater 는 `*-build-*` 만 추적해서 *동시 빌드 충돌* 회피.
- **사고 메모**:
  - 2026-05-17 `chat.lemuel.co.kr/products` 빈 화면 — same-origin proxy 누락 → [관련 글](/2026/05/17/settlement-empty-admin-page-4-layer-debug/)
  - 2026-05-23 `david` NotReady — helm refs 4곳 임시 비활성화
  - 2026-05-24 `cost-app` 8일째 CrashLoopBackOff ×91 — probe `timeoutSeconds` 미지정 (Kubernetes default 1s) 으로 8080 응답 1s 안에 못 받아 죽임. `timeoutSeconds: 5` + memory 1Gi → 1.5Gi 로 fix.

### 용어

- **PriorityClass (우선순위 클래스)** — Pod 에 *상대 우선순위* 부여. 자원 부족 시 *낮은 우선순위 Pod* 가 먼저 evict (강퇴).
- **LimitRange** — namespace 안의 모든 Pod 에 *기본 자원 한도* 강제. *cpu/memory 비율* 도 제한 가능 (memory limit ≤ request × 2 같은 식).
- **PDB (PodDisruptionBudget, 파드 중단 예산)** — *자발적 중단* (노드 드레인 같은) 시 *동시에 죽을 수 있는 Pod 개수 상한*. 5 replica StatefulSet 에 PDB `maxUnavailable=1` 이면 한 번에 1개씩만 종료 허용.
- **StatefulSet (스테이트풀셋)** — *상태 가진* Pod 묶음. 각 Pod 가 *고정 이름* (pg-0, pg-1) + *고정 PVC* (persistent volume claim) 보유. DB 같은 상태 워크로드에 적합.
- **SOPS** — Mozilla 의 *시크릿 암호화 도구*. YAML/JSON 의 *값 부분만* 암호화하고 키는 그대로 둠 (diff 가능). age 키 + GPG 키 + AWS KMS 등 다양한 백엔드.
- **drain / cordon** — `cordon` = 노드에 새 Pod 못 들어오게 차단 (SchedulingDisabled), `drain` = cordon + 기존 Pod evict.
- **evict (이빅트, 강퇴)** — Pod 를 *우아하게 종료* 하고 다른 노드로 옮김. SIGTERM → terminationGracePeriod → SIGKILL.

---

## 7. 이 그림이 닿지 않는 곳

- **DB 시드/마이그레이션** — 각 앱 레포의 `db/migration/` Flyway 가 deploy 시 자동 실행. 본 글은 *클러스터 자원만* 다룸.
- **외부 API 의존** — Gemini / Anthropic API / TTS 사이드카. 앱 코드 안에 있음.
- **사용자 데이터 정책** — lemuel-xr 의 PHI 비수집 (emotion_logs.raw_text 영속화 X) 같은 *개인정보 정책* 은 [별도 자살예방 mission 글](/2026/05/21/lemuel-xr-governance-content-quarantine-e2e/) 참고.

---

## 8. 왜 이 그림을 그렸나

ArgoCD 화면 들어가서 39 app 보고 있으면 *어디부터 봐야 할지* 모른다. 노드 4개 + 39 app + 관측 stack 까지 *한 장* 으로 가지고 있으면, 사고 났을 때 *어디부터 의심할지* 한 박자 빨리 찾는다. 그리고 *영어 용어가 자연스러워질 때* 다른 사람한테 설명할 수 있다.

토폴로지 그림 자체는 mermaid 버전이 helm-deploy 레포의 `docs/CLUSTER-TOPOLOGY.md` 에 있다 — GitHub 가 mermaid 를 자동 렌더해주니 더 깔끔하게 본다.

---

## 9. 용어 사전 (사전순)

| 영어 | 한글 | 한 줄 요약 |
|---|---|---|
| ACME | 자동 인증서 | TLS 인증서 자동 발급·갱신 프로토콜 |
| ArgoCD | 아르고씨디 | Kubernetes GitOps 컨트롤러 |
| app-of-apps | 앱 오브 앱스 | 하나의 ArgoCD app 이 다른 app 정의를 관리하는 패턴 |
| cordon | 코든 | 노드에 새 Pod 못 들어오게 차단 |
| Control plane | 제어 평면 | Kubernetes 의 결정 두뇌 (API server + scheduler + controller) |
| DaemonSet | 데몬셋 | 모든 노드에 1개씩 Pod 자동 생성 |
| drain | 드레인 | cordon + 기존 Pod evict |
| Drift | 드리프트 | git 선언과 클러스터 실제 상태의 차이 |
| ELK | - | Elasticsearch + Logstash + Kibana 로그 stack |
| etcd | 이트시디 | Kubernetes 의 분산 KV store |
| evict | 이빅트, 강퇴 | Pod 를 우아하게 종료 |
| fluent-bit | - | 경량 로그 수집기 |
| GHCR | - | GitHub Container Registry |
| GitOps | 깃옵스 | git 을 원하는 상태의 단일 source 로 |
| Grafana | 그라파나 | 메트릭·로그·트레이스 대시보드 UI |
| Image Updater | - | ArgoCD 의 컨테이너 이미지 자동 갱신 plugin |
| Ingress | 인그레스 | 클러스터 바깥 HTTP 트래픽 라우팅 |
| LimitRange | - | namespace 별 자원 한도 강제 |
| MSA | - | Microservice Architecture |
| Namespace | 네임스페이스 | 클러스터 안의 논리적 폴더 |
| NotReady | 준비 안 됨 | kubelet 이 API server 와 hearbeat 끊긴 상태 |
| OpenTelemetry | 오픈텔레메트리 | 벤더 중립 관측 데이터 표준 |
| OutOfSync | - | git 과 클러스터 상태가 다름 |
| PDB | 파드 중단 예산 | 자발적 중단 시 동시 죽을 Pod 개수 상한 |
| PriorityClass | 우선순위 클래스 | Pod 에 상대 우선순위 부여 |
| Prometheus | 프로메테우스 | 메트릭 수집의 사실상 표준 |
| Quorum | 합의 | 분산 시스템의 다수결 (etcd 3 노드 → 2 살아야 OK) |
| Reconcile | 재조정 | 목표 상태와 현재 상태 일치 루프 |
| Rolling update | 롤링 업데이트 | 다운타임 0 으로 점진 교체 |
| Service | 서비스 | Pod 의 안정적 네트워크 식별자 |
| SOPS | - | Mozilla 의 시크릿 암호화 도구 |
| StatefulSet | 스테이트풀셋 | 상태 가진 Pod 묶음 (고정 이름 + PVC) |
| Taint / Toleration | 테인트 / 톨러레이션 | 노드 얼룩 + Pod 의 얼룩 참기 |
| Tempo | 템포 | 분산 트레이싱 저장소 |
| Traefik | 트래픽 | K3s 기본 Ingress Controller |
| Uptime Kuma | 업타임 쿠마 | 외형 헬스체크 |

---

*이 글은 2026-05-25 운영 스냅샷 기준. 노드/앱 추가·삭제 시 갱신. mermaid 버전은 [helm-deploy/docs/CLUSTER-TOPOLOGY.md](https://github.com/MyoungSoo7/helm-deploy/blob/master/docs/CLUSTER-TOPOLOGY.md).*
