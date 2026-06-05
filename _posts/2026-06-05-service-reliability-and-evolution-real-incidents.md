---
layout: post
title: "서비스 안정성과 고도화 — *측정 → 자동화 → 회복 → 학습* 루프, 그리고 오늘 logistic-prod / fashion-prod / pg-backup 실전 사고 4 건의 진단 과정"
date: 2026-06-05 17:00:00 +0900
categories: [sre, reliability, kubernetes]
tags: [reliability, sre, slo, kubernetes, argocd, flyway, cdn-cache, shedlock, velero, image-updater, root-cause-analysis]
---

서비스 *안정성 (reliability)* 과 *고도화 (evolution)* 는 두 별개의 일처럼 보이지만 본질은 같다 — **반복 가능한 *측정·자동화·회복·학습* 루프** 이다. 안정성 없는 고도화는 *사상누각*, 고도화 없는 안정성은 *정체*. 오늘 내 K3s 클러스터에서 *4 개 사고* 가 동시 발생했고, 그 진단 흐름 자체가 *안정성·고도화 루프의 살아있는 교과서* 였다.

이 글은 **(1) 안정성의 5 단계 성숙도** + **(2) 오늘의 4 건 사고 + 진단** + **(3) 고도화의 4 단계 루프** + **(4) 흔한 안티패턴 5 가지** 로 구성된다. *시간이 늦었더라도 끝까지 작성하는 이유* — 같은 사고가 *다음에 더 빨리 복구* 되도록 *학습으로 압축* 하기 위해서.

---

## TL;DR

**서비스 안정성 = *예측 가능성*** (불확실성 적음).
**서비스 고도화 = *학습 압축률*** (같은 사고 다시 안 일어남).

| 안정성 단계 | 측정 가능? | 자동 회복? | 학습 압축? |
|---|---|---|---|
| L0 Reactive (수동) | ❌ | ❌ | ❌ |
| L1 Observed (모니터링) | ✅ | ❌ | ❌ |
| L2 Automated (자가 회복) | ✅ | ✅ (단순 케이스) | △ |
| L3 SLO-driven (예측) | ✅ + SLO | ✅ | ✅ |
| **L4 Anti-fragile (사고에서 *강해짐*)** | ✅ | ✅ + 점진 | ✅✅ |

내 클러스터는 *L2~L3 사이*. 오늘 4 건 모두 L3 의 *자동 신호* (kubectl, ArgoCD, GHCR, log) 로 *진단 가능* 했지만 *L4 (사고에서 *강해짐*)* 는 *blog 글로 압축* 함으로써만 도달.

---

## 1. 안정성의 5 단계 성숙도 모델

### L0 — Reactive (수동)

- 사고 발생 → 사용자가 *전화* / *카톡* 으로 알림
- 운영자가 *서버에 ssh* 들어가 *직접 진단*
- 복구 = *경험·운*

**전형 신호:** *"왜 안 돼?"* 가 *유저로부터* 시작.

### L1 — Observed (모니터링)

- Prometheus + Grafana + 알람
- *어디서 무엇이 깨졌는지* 알 수 있음
- 그러나 *수동 복구*

**전형 신호:** 알람 받고 *대시보드 열어 진단* 후 *kubectl 명령* 직접 실행.

### L2 — Automated (자가 회복)

- *흔한 사고* 는 *클러스터가 자동 처리*
- K8s liveness/readiness probe → 자동 재시작
- ArgoCD self-heal → drift 자동 동기화
- Velero schedule → 자동 백업
- CronJob → 정기 작업

**전형 신호:** 일부 사고는 *사용자가 모를 정도로* 자동 회복.

### L3 — SLO-driven (예측)

- *SLO (Service Level Objective)* 정의 — *예: 가용성 99.9%*
- *Error budget* 으로 *변경 속도 vs 안정성* 트레이드오프 측정
- *알람 임계*가 *SLO 위반 추세* 기반

**전형 신호:** *"이번 분기 error budget 50% 소진"* 같은 *예측적 대화*.

### L4 — Anti-fragile (사고에서 *강해짐*)

- 사고가 *시스템을 약화* 시키지 않고 *강화*
- *Postmortem* 이 *학습 자산* 으로 압축
- *카오스 엔지니어링* 으로 *사고 시뮬레이션*

**전형 신호:** 같은 사고가 *다시 발생 안 함*. 비슷한 사고가 *더 빨리 복구*.

---

## 2. 오늘의 실전 4 사고 — *동시 발생*, *각자 다른 layer*

### 사고 1 — logistic-prod *4 단계 캐스케이드*

**증상:** 새로 만든 logistic-robot 의 13 pod 중 *9 개 ImagePullBackOff*.

**진단 흐름 (각 단계 *별도 root cause*):**

```
Step 1: ImagePullBackOff
  → GitHub Actions CI 실패 검사
  → 에러: "repository name must be lowercase"
  → 원인: ${{ github.repository_owner }} 가 MyoungSoo7 (대문자)
  → FIX: .github/workflows/ci.yml 에 tr '[:upper:]' '[:lower:]' 변환
  → push → CI 7/7 success → GHCR 이미지 push

Step 2: secret "postgres-credentials" not found
  → 진단: kubectl describe pod
  → 원인: helm chart 가 require 하는 secret 자동 생성 안 함
  → FIX: kubectl create secret generic postgres-credentials --from-literal=...

Step 3: postgres-0 Pending — node affinity 안 맞음
  → 원인: PV 가 david 노드에 bind, david 가 NotReady
  → FIX (사용자): david 물리 전원 cycle

Step 4: Flyway checksum mismatch
  → 원인: 여러 service 가 같은 DB 에 자기 V1__init.sql 적용 → 충돌
  → FIX: SPRING_FLYWAY_ENABLED=false + SPRING_JPA_HIBERNATE_DDL_AUTO=update
       (정통 fix 는 각 service 별 schema 분리 — 후속 작업)
```

**총 시간:** 약 4 시간 (대부분 *대기*, 실제 진단·fix 는 30 분).

**Layer 마다 *root cause* 다름:**
- CI 설정 (GHCR lowercase 룰)
- K8s 권한 (secret 자동 생성 미설계)
- 물리 인프라 (노드 다운)
- 애플리케이션 아키텍처 (같은 DB 공유 시 Flyway 충돌)

이게 *분산 시스템의 *현실*** — 사고는 *한 가지 원인* 이 아닌 *여러 layer 의 동시 실패*.

### 사고 2 — fashion.lemuel.co.kr 의 *3 단계 cache 함정*

**증상:** 외부 도메인이 *Next.js create-next-app starter* 그대로 표시. *몇 주째*.

**진단 흐름:**

```
Layer 1: Deployment image = :latest (5/11 빌드, 한 달 전)
  → ArgoCD Image Updater 가 spec.helm.parameters 에 frontend.image.tag=latest 박아둠
  → values.yaml 의 SHA pinning (e6e24b5) 을 override
  → :latest + IfNotPresent = 노드 cache 의 옛 이미지 영원
  → FIX: kubectl patch app fashion-prod parameters 직접 SHA 로

Layer 2: 새 SHA 이미지에도 starter HTML
  → Docker build cache 가 *stale .next/* 디렉토리 포함
  → 5/26 .dockerignore 추가 commit 후에도 *그 빌드 시점에 이미 stale .next/ 박힘*
  → FIX: rm -rf frontend/.next + empty commit + push → clean rebuild

Layer 3: 새 이미지 적용 후에도 *여전히 starter*
  → x-nextjs-cache: HIT + s-maxage=31536000 (1년)
  → Cloudflare CDN edge 가 *5/11 starter HTML* 을 1년 동안 cache
  → FIX (사용자): Cloudflare dashboard → Purge cache
```

**핵심 교훈:** *cache 는 *4 layer* 에 있다* — Deployment / Container Registry / Docker build / CDN. 한 layer fix 가 다른 layer 의 cache 를 invalidate 못 함.

### 사고 3 — solomon 노드 NotReady (kubelet 응답 정지)

**증상:** `kubectl get nodes` 에 *solomon NotReady*, *Kubelet stopped posting status*.

**진단:**
- ping 응답 (5~295ms 출렁) → *네트워크 부분 도달*
- SSH key 없어 직접 진단 불가
- 30 분 후 *자동 회복* (kubelet 재기동 자동)

**Lesson:** *solomon = 2014 Mac Mini*. 메모리 부족 + 노후 하드웨어로 *간헐 kubelet 멈춤*. *재발 가능성 100%*. 장기적으로 *교체 또는 워크로드 이관* 필요.

### 사고 4 — sns-app 26 시간 Pending

**증상:** *sns-prod/sns-app* 이 *26 시간째 schedule 안 됨*.

**진단:**

```
FailedScheduling: 0/5 nodes are available:
  1 Insufficient memory       ← louise (99% 점유)
  1 had untolerated taint     ← lemuel cordon
  2 didn't match nodeSelector ← ilwon=management, solomon=storage
  1 unschedulable             ← lemuel
```

**원인:** `nodeSelector: tier=worker` + *louise 만 worker label* + *louise 메모리 99%*. david 도 *worker 가능한데* `tier` label 안 박혀있음.

**Fix 1 줄:**
```
kubectl label node david tier=worker
```

30 초 만에 sns-app Running.

---

## 3. 4 가지 사고의 *공통 패턴*

| # | Layer | Root Cause 종류 |
|---|---|---|
| logistic-prod | CI / K8s / 인프라 / App | *연쇄 4 layer 의 동시 실패* |
| fashion CDN | 빌드 / 레지스트리 / CDN | *4 layer cache 의 invalidation 부재* |
| solomon | 물리 인프라 | *하드웨어 노후* |
| sns-app | K8s 스케줄 | *label 매칭 부재* |

**공통 결론:**
1. **단일 root cause 는 *거의 없다*** — 분산 시스템엔 *layer 마다 다른 원인*
2. **모든 layer 의 *상태* 가 가시화되지 않으면 진단 어려움** — *L1 (observed)* 의 한계
3. **자동 회복은 *흔한 사고* 만 처리** — 노드 다운, CDN cache 같은 *교차 layer 사고* 는 사람 개입

---

## 4. 고도화의 4 단계 루프 — *측정 → 자동화 → 회복 → 학습*

### 4.1 측정 (Observe)

```
prometheus → kubectl metrics → grafana
GH Actions → CI status
ArgoCD → Application status
Cloudflare → CDN cache stats
```

*무엇을 측정하지 않으면 그것이 깨져도 모른다*.

### 4.2 자동화 (Automate)

```
- K8s liveness probe → pod 자동 재시작
- ArgoCD selfHeal → drift 자동 sync
- Velero schedule → 매일 백업
- pg-backup CronJob → 14 namespace logical dump
- ShedLock → @Scheduled 분산 락 (HA 대비)
- Image Updater → 새 이미지 자동 적용
```

*반복 작업* 의 자동화는 *시간 절약 + 휴먼 에러 차단*.

### 4.3 회복 (Recover)

```
- 다중 백업 (Velero + pg_dump 별도 = idempotent receiver 의 L1/L2 비유)
- ArgoCD self-heal
- liveness probe 재시작
- Triple Idempotency (settlement) — 발행측 + 수신측 양방향 보호
- Outbox Pattern — 메시지 발행 원자성
```

*회복 메커니즘이 *layer 마다* 있어야 한다*.

### 4.4 학습 (Learn)

```
- Postmortem → blog post (이 글 자체)
- ADR (Architecture Decision Record)
- Runbook 업데이트
- 새 alert rule 추가
```

이 글이 *L4 Anti-fragile* 의 핵심 — *사고를 학습으로 압축*.

---

## 5. 안정성을 *방해하는* 흔한 안티패턴 5 가지

### ❌ 안티패턴 1: *Latest 태그* 의존

```yaml
image: ghcr.io/myorg/app:latest
imagePullPolicy: IfNotPresent
```

= *옛 이미지 cache 영원*. *변경 후에도 갱신 안 됨*. fashion CDN 사고의 *Layer 1*.

**해결:** SHA 또는 *immutable tag* 사용.

### ❌ 안티패턴 2: *단일 root cause* 가정

진단 시 *첫 발견한 원인에서 멈춤*. logistic-prod 같이 *4 layer 동시 실패* 면 *layer 별 fix 후 다음 layer 진단* 필요.

**해결:** *모든 *증상이 다 사라질 때까지* 진단 계속*.

### ❌ 안티패턴 3: *cache invalidation 누락*

새 코드 배포 → *어딘가 cache 가 옛 거*. fashion-prod 의 *Docker build cache → 새 commit 시점에 stale 박힘*.

**해결:** *모든 cache layer* (Docker / CDN / Browser / Redis) 의 *invalidation 전략* 명시.

### ❌ 안티패턴 4: *secret 자동 생성 미설계*

helm chart 가 `existingSecret: postgres-credentials` *require* 하지만 *자동 생성 안 함*. 첫 배포 시 *CreateContainerConfigError*. logistic-prod 사고의 *Step 2*.

**해결:** 
- Chart 에 `secrets.autoCreate=true` 옵션 + `randomly generate password` 헬퍼
- 또는 *SOPS 또는 sealed-secrets 로 secret git-managed*

### ❌ 안티패턴 5: *label 일관성 부재*

`nodeSelector: tier=worker` 인데 *worker 라벨 가진 노드 1 개만*. sns-app 26 시간 Pending.

**해결:** *클러스터 토폴로지 *문서화* + *label 일관성 enforcement** (ArchUnit 같은 정책 검증을 K8s 에도).

---

## 6. *지금 너 환경의* 안정성 점검 (체크리스트)

오늘 발견한 *너 K3s 클러스터의 안정성 신호*:

**✅ 잘 됨:**
- pg-backup 14/14 매일 02:00~03:05 KST 자동 (시간 분산 적용)
- Velero hourly + daily 백업 정상
- ShedLock 7 scheduler 분산 락 PR 머지 대기
- ArgoCD ApplicationSet 으로 *fleet 단위 일괄 배포*

**⚠️ 개선 여지:**
- root-app sync 5/30 부터 깨짐 (`--force` + `--server-side` 충돌)
- secret 수동 생성 — `postgres-credentials`, `jwt-secret` 매번 직접
- Image Updater 가 `latest` 박는 패턴 → 모든 fashion-style 사고 위험
- *모든 prod 가 replicas: 1* — HA 없음, *pod 죽으면 다운*

**🚨 즉시 action 추천:**
1. *cluster-wide allow-tags regex* 강제 — `latest` 금지
2. *helm chart 에 secret auto-gen* 패턴 — `lookup` 함수 활용
3. *node label 일관성 정책* — `tier=worker` 가 *모든 worker 에* 있게

---

## 7. 도구 매핑 — 어느 layer 에 무엇이

```
┌─ 측정 ───────────────────────────────────┐
│  Prometheus + Grafana + Loki + Tempo   │
│  kubectl / k9s                          │
│  GitHub Actions / ArgoCD               │
└──────────────────┬──────────────────────┘
                   ↓
┌─ 자동화 ───────────────────────────────┐
│  K8s liveness/readiness probe         │
│  ArgoCD selfHeal + Image Updater      │
│  Velero schedule + pg-backup CronJob  │
│  ShedLock (HA scheduler)              │
└──────────────────┬─────────────────────┘
                   ↓
┌─ 회복 ────────────────────────────────┐
│  PV backup (Velero) + pg_dump (SQL)  │
│  Outbox Pattern + Triple Idempotency │
│  Multi-replica (HA, 미적용)            │
└──────────────────┬────────────────────┘
                   ↓
┌─ 학습 ────────────────────────────────┐
│  Blog posts (이 글 같은 것)            │
│  ADR (architecture decision records) │
│  Postmortem template                 │
│  Runbook 업데이트                      │
└────────────────────────────────────────┘
```

---

## 8. *고도화* — 다음 6 개월 로드맵

1. **HA 도입** — *Critical service* (settlement, lemuel-xr) 부터 replicas 2 + ShedLock
2. **secret 관리 통일** — SOPS 또는 *External Secrets Operator*
3. **Image policy enforcement** — `latest` 금지, SHA 또는 semver 만
4. **runbook 자동화** — ChatOps + Slack/Telegram bot 으로 *수동 명령* 줄임
5. **카오스 엔지니어링 도입** — *주 1 회* 노드 강제 종료 / network partition 테스트
6. **SLO 정의** — *가용성 99.9%* 같은 *측정 가능 목표*

---

## 9. 결론 — *안정성은 정직, 고도화는 학습*

서비스 안정성은 *완벽함이 아니라 *정직함**.

- *언제 어떻게 깨지는지* 솔직히 측정
- *대부분의 사고* 가 *layer 마다 다른 원인* 인 것 인정
- *완벽한 자동 회복은 불가능* — *사람 개입 지점* 명확히 설계
- *사고가 *학습 자산* 으로 압축* 될 때 시스템은 *강해짐*

고도화는 *최신 기술 도입* 이 아니라 *루프 압축률* 향상:

```
Reactive  →  Observed  →  Automated  →  SLO-driven  →  Anti-fragile
   L0           L1            L2            L3              L4
```

오늘 *4 건 사고를 4 시간에 해결* 한 것은 *천재성 때문이 아니라 그 layer 별 도구 + 진단 패턴이 *축적* 되어 있었기에*. 내일 사고는 *오늘보다 더 빨리* 복구될 것이다 — *이 글이 학습 자산* 으로 압축됐기에.

**한 줄 결론:** *안정성과 고도화는 *동시* 가 가능한 일* — *측정·자동화·회복·학습 루프* 가 둘 다 만든다.

---

## 참고

- *Site Reliability Engineering* — Google (2016)
- *The Site Reliability Workbook* — Google (2018)
- *Accelerate* — Forsgren, Humble, Kim (2018) — DORA metrics
- *Implementing Service Level Objectives* — Alex Hidalgo (2020)
- Brendan Gregg, [The USE Method](https://www.brendangregg.com/usemethod.html)
- 관련 글:
  - [Harness Engineering ④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
  - [홈랩 K3s Capacity Planning]({% post_url 2026-05-29-homelab-capacity-planning-datacenter-style %})
  - [K3s 의 한계]({% post_url 2026-05-29-k3s-limitations-real-world-homelab-experience %})
  - [ShedLock 으로 @Scheduled 분산 락]({% post_url 2026-06-04-kubernetes-scheduled-shedlock-distributed-lock %})
  - [DDD ↔ MSA — Bounded Context]({% post_url 2026-05-29-ddd-msa-bounded-context-aggregate-event-storming %})
