---
layout: post
title: "*GitOps(ArgoCD) 기반* *멀티 환경 배포 자동화* 와 *통합 관측 체계 구축* — *K3s 5 노드 HA* *47 개 ArgoCD App* *무중단 운영* 실전 정리"
date: 2026-06-17 01:30:00 +0900
categories: [infrastructure, devops, gitops, observability]
tags: [argocd, gitops, k3s, elk, prometheus, grafana, tempo, velero, sops, playwright, telegram, frp, helm]
---

> *"인프라가 무너지면 *비즈니스가 *무너진다*."* 
>
> *그러나 *무너지는 순간* 은 *코드가 *고장난 순간* 이 *아니다*. *대부분은 *배포 직후* 다. *그래서 *배포 파이프라인* 과 *관측 체계* 가 *같은 무게* 로 *설계* 되어야 한다.
>
> 이 글은 *온프레미스 K3s 5 노드 HA 클러스터* (control-plane × 3 + worker × 2) 위에서 *47 개 ArgoCD Application (prod + staging 합산)* 을 *GitOps 단일 소스* 로 *무중단 배포 / 관측 / 백업 / 게이트* 하는 *5 개 축* 의 *실제 운영 설계* 를 정리한다.

---

## TL;DR

> *GitOps(ArgoCD)* 는 *"클러스터 상태 = Git 상태"* 라는 *단 한 줄의 약속* 을 *컴파일러처럼 강제* 한다. 그 위에 *(1) 3 - pillar 관측 (ELK + Prometheus + Tempo)*, *(2) 이중 백업 (Velero + 14 개 pg_dump CronJob)*, *(3) 품질 게이트 (Playwright E2E + 외부 도메인 검증)*, *(4) 운영 관제 (Telegram 실시간 알림)*, *(5) 인프라 자가 운영 (K3s HA + NFS + Registry mirror + frp + SOPS)* 의 *5 개 축* 을 *얹어야* *진짜 무중단 운영* 이 *가능* 해진다. *코드 1 줄* 이 *production 까지 가는* *모든 좌석* 에 *안전벨트* 가 *있어야* 한다는 *철학* 이다.

---

## 0. *왜 *GitOps 인가* — *문제의식*

### 0.1 *"누가 *언제 *무엇을 *바꿨나"* 가 *추적되지 않는* 클러스터

전통적인 `kubectl apply` 운영은 *3 가지 문제* 가 *반복* 된다.

1. *Drift* — 실수로 `kubectl edit` 한 변경이 *Git 에 안 남는다*. 다음 사람이 *Git 만 보고* 클러스터를 *복원* 하면 *그 변경이 사라진다*.
2. *Audit gap* — *누가 / 언제 / 왜* 가 *git log 가 아니라 *kubectl history* 에 *흩어져 있다*.
3. *Rollback 불확실성* — 이전 manifest 가 *어디 있었는지* 가 *명확하지 않다*. *재배포가 *재현 가능* 하지 않다.

### 0.2 *GitOps 의 *단 한 줄 약속*

> *클러스터 상태 = `helm-deploy` 리포의 *master* 브랜치 상태*

이 약속 하나로 *위 3 가지 문제 가 동시에 해결* 된다.

- *변경은 *반드시 PR / commit 으로* — drift 0
- *git log* = *audit log* — *누가 / 언제 / 왜* 가 *영구 기록*
- *rollback* = *git revert* — *재현 가능*

---

## 1. *축 1 — 3-Pillar 통합 관측 (Logs + Metrics + Traces)*

### 1.1 *관측의 *3 기둥*

> *시스템의 *건강* 을 *말로* 만 *물으면 *시스템은 *대답하지 않는다*. *수치 / 흔적 / 진술* 로 *물어야* 한다.

| 기둥 | 질문 | 대표 도구 |
|---|---|---|
| *메트릭 (Metrics)* | *"얼마나 *어떻게 *돌고 있나?"* (CPU, QPS, latency) | Prometheus + Grafana |
| *로그 (Logs)* | *"무슨 일이 *언제 *일어났나?"* (텍스트 이벤트) | Fluent-bit + Elasticsearch + Kibana |
| *트레이스 (Traces)* | *"한 요청이 *어느 서비스를 *거쳐 *어디서 *느려졌나?"* (span chain) | Tempo |

### 1.2 *Fluent-bit DaemonSet — *모든 노드의 *모든 컨테이너 stdout*

```yaml
# argocd-applications/elk/03-fluent-bit.yaml — 핵심만
kind: DaemonSet
spec:
  template:
    spec:
      containers:
        - name: fluent-bit
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
```

- *DaemonSet* — *모든 노드에 1 개씩* *자동 배포*. 새 노드 합류 시 *수동 작업 없음*
- *컨테이너 stdout/stderr* 를 *Kubernetes metadata (namespace, pod, labels)* 와 *함께* *ES 로 적재*
- *Kibana* 에서 *namespace = settlement-prod AND log ~ "ERROR"* 같은 *cross-pod 검색*

### 1.3 *Prometheus 32 개 PrometheusRule — *알림은 *코드처럼 *버전 관리*

`monitoring-prod` 의 *kube-prometheus-stack* 위에 *32 개의 PrometheusRule* 이 *Git 으로 관리* 된다.

```yaml
# cluster-ops/pod-restart-alert-rule.yaml — 패턴 예시
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
    - name: pod-restart
      rules:
        - alert: PodRestartingFrequently
          expr: increase(kube_pod_container_status_restarts_total[15m]) > 3
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Pod {{ $labels.pod }} restarted >3 times in 15m"
```

*규칙의 *3 가지 가치*:

1. *PR 리뷰 가능* — 알림이 *왜 이 임계치인지* 가 *commit message* 에 *남는다*
2. *환경별 분기* — staging 은 *완화*, prod 는 *엄격* 으로 *value override*
3. *재현 가능* — *클러스터 재구축* 시 *Git apply 한 번* 이면 *알림 체계 복원*

### 1.4 *Tempo — *MSA 의 *끊어진 호출 chain 잇기*

```
[Client] → gateway → order-service → payment-service → (Kafka) → settlement-service
            span A      span B           span C                       span D
                                                          ^ Kafka 가 끊는 듯 보이는데
                                                            traceparent header propagation 으로 connect
```

- *settlement-service* 같은 *이벤트 기반 MSA* 에서 *주문 → 결제 → 정산* 의 *전체 흐름* 을 *한 trace ID* 로 *추적*
- *어느 span 에서 *p99 가 *튀는지* 가 *Grafana Tempo* 의 *flame graph* 로 *즉시 보인다*

### 1.5 *3 기둥의 *cross-link*

Grafana 에서:

- *메트릭 그래프* 의 *튀는 지점* → *클릭* → *그 시간대의 로그* (ES) / *그 시간대의 trace* (Tempo)
- *Tempo span* 에서 *exception* 보임 → *클릭* → *그 pod 의 로그* (ES)

→ *한 사고가 *터지면* *3 도구 사이 점프 횟수 = 1 ~ 2 번* 으로 *근본 원인* 까지 *내려간다*.

---

## 2. *축 2 — 이중 백업 (Form × Medium × Restore unit)*

### 2.1 *왜 *이중* 인가 — *직교 설계의 *원칙*

> *단일 백업 은 *침해 / 부패 / 인적 실수* 중 *하나에만 *대응* 한다. *직교 한 두 가지* 를 *겹치면 *둘 다 *동시* 에 *터지지 않는 한* *복원 가능*.

내 클러스터는 *3 차원이 직교* 하도록 *이중화* 했다.

| 차원 | Velero 백업 | pg_dump CronJob |
|---|---|---|
| *형태 (Form)* | *물리* (PV 스냅샷, K8s 리소스 manifest) | *논리* (SQL dump) |
| *매체 (Medium)* | *오프사이트 R2* | *로컬 PVC + R2 sync* |
| *복원 단위 (Restore unit)* | *클러스터 / 네임스페이스* | *단일 DB / 테이블* |

→ *클러스터 전체 손실* — Velero 로 *namespace 채로 *복원*.
→ *단일 DB 의 *논리적 부패 (잘못된 UPDATE)* — pg_dump 로 *해당 DB 만 시점 복원*.
→ *서로의 *부재 시나리오* 를 *덮어준다*.

### 2.2 *Velero 일·시간 단위 오프사이트 백업*

```bash
# 매일 03:00 KST 풀 백업, 매시간 incremental
velero schedule create daily-full \
  --schedule="0 3 * * *" \
  --include-namespaces='*-prod' \
  --ttl 720h0m0s   # 30 일 보존

velero schedule create hourly-pv \
  --schedule="0 * * * *" \
  --include-resources=pvc,pv \
  --ttl 168h0m0s   # 7 일 보존
```

- *03:00* — *클러스터 전체 *조용한 시간*
- *오프사이트 R2* — *온프레미스 NAS 만 *터지는 *지역 사고* 에서도 *복원 가능*

### 2.3 *14 개 pg_dump CronJob — *namespace 별 *논리 백업*

```yaml
# charts/pg-backup/values.yaml
schedule: "0 2 * * *"     # 매일 02:00 KST (Velero 03:00 보다 1 시간 앞)
timezone: "Asia/Seoul"
retention:
  days: 30                 # local PVC 30 일 보존
```

*핵심 설계 결정*:

- *namespace 별 1 개* CronJob — *14 개 namespace × 1 = 14 개*. *blast radius 격리*
- *Velero (03:00) 보다 1 시간 앞* — *pg_dump 의 *결과물 .sql* 이 *Velero PV 스냅샷에 포함* 되도록
- *retention 30 일* — *지난 한 달 안 *언제든 *시점 복원*
- *LimitRange 호환* — *memory request==limit*, *cpu ratio ≤ 4* — *crypto-prod 같은 *제한 namespace* 에서도 *반려 없이 *돌도록* *튜닝*

### 2.4 *백업의 *복원 시간 (RTO) 검증*

> *백업 은 *복원 해 본 적 없 으면 *백업 이 아니다*.

분기별 1 회 *staging 클러스터에 Velero restore + pg_dump 적용* 을 *수동 테스트*. *RTO 측정* 해서 *Grafana 에 *수치로 기록*.

---

## 3. *축 3 — 품질·안정성 게이트 (Pre + Post deploy)*

### 3.1 *배포 *직후* 에 *터지는 사고* 가 *가장 많다*

> *CI 의 *단위테스트* 가 *통과해도* *frontend 가 *production CDN* 에서 *깨질 수 있다*. *프론트 빌드 시점에 *NEXT_PUBLIC_API_URL* 이 *틀려서* `https://localhost:8080` 로 *번들* 되는 사고 같은 것들.

→ *배포 후 *실제 사용자가 *보는 도메인* 을 *외부에서 *검증* 해야 한다.

### 3.2 *Playwright E2E — *배포 전 *유저 시나리오 자동화*

```typescript
// settlement/frontend/playwright.config.ts 패턴
export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 14'] } },
  ],
});
```

- *PR 게이트* — main merge 전 *주요 user flow (로그인 → 주문 → 결제 → 정산 조회)* *자동 실행*
- *Trace 자동 캡쳐* — 실패 시 *영상 + DOM snapshot* 이 *Actions artifact* 로 *남는다*

### 3.3 *배포 *후* 외부 도메인 가용성 검증*

```yaml
# uptime-kuma-prod.yaml 로 배포한 Uptime Kuma 의 모니터
- type: http
  name: settlement-frontend
  url: https://settlement.example.com
  interval: 60  # 1 분 주기
  acceptedStatusCodes: ['200-299']
  expectedKeyword: '정산 대시보드'   # 빌드 산출물 마커
```

- *acceptedStatusCodes* 만 보지 *않고* *body keyword* 까지 *검증* — *200 이지만 *빈 화면* 인 사고 차단
- *frp tunnel* 을 거쳐 *외부 인터넷* 에서 *진짜 사용자 시점* 으로 *fetch*

### 3.4 *왜 *내부 신호 (API 200, Argo Healthy)* 만으로는 *부족* 한가

ArgoCD 가 *Healthy = Synced* 라고 *말해도*:

- *외부 CDN 캐시* 가 *옛 버전* 일 수 있다
- *frontend 빌드 ARG* 가 *틀려* *번들이 *깨졌어도* *서버 응답은 *200*
- *Kafka 가 *백로그 *쌓고 있어* *DB 쓰기 가 *오래된 데이터*

→ *외부 도메인 의 *real bytes* 까지 *검증* 해야 *진짜 배포 성공*.

---

## 4. *축 4 — 운영 관제 (Telegram 실시간 알림 파이프라인)*

### 4.1 *알림의 *3 채널 분리*

| 채널 | 용도 | 임계 |
|---|---|---|
| *#infra-critical* | *PV / etcd / NFS / 노드 down* | *즉시 호출* |
| *#deploy* | *ArgoCD sync, Image Updater 이벤트* | *알리지만 *호출 X* |
| *#cronjob-fail* | *14 개 pg_dump + 기타 CronJob 실패* | *오늘 안에 *대응* |

→ *모든 알림이 *한 채널에 *섞이면* *진짜 critical 이 *묻힌다*. *분리 가 *운영자 의 *정신 건강* 을 *지킨다*.

### 4.2 *Alertmanager → Telegram webhook 흐름*

```yaml
# monitoring-prod 의 alertmanager values
receivers:
  - name: telegram-infra-critical
    webhook_configs:
      - url: 'https://api.telegram.org/bot{{ token }}/sendMessage'
        send_resolved: true
route:
  receiver: telegram-deploy
  routes:
    - matchers: ['severity="critical"']
      receiver: telegram-infra-critical
```

- *severity 라벨* 로 *PrometheusRule 정의 시점에 *분기*
- *send_resolved: true* — *복구 메시지도 *수신*. *"끝났는지" 가 *명확*

### 4.3 *CronJob 실패 전용 룰 — *왜 *별도* 인가

```yaml
# cluster-ops/cronjob-failed-alert-rule.yaml
- alert: CronJobFailed
  expr: kube_job_failed{job_name=~".+-pg-backup-.+"} > 0
  for: 1m
  annotations:
    summary: "Backup job {{ $labels.job_name }} failed"
```

- *백업 실패 는 *오늘 안에 *발견* 해야 한다. *내일 *터지면 *어제 백업이 없다*
- *CronJob 은 *재시도가 *기본* 이라 *사람이 *모르고 *지나갈 수 있는* *유일한 알림*

### 4.4 *알림의 *피드백 루프*

> *알림이 *너무 *시끄러우면* *운영자가 *읽지 않는다*. *너무 *조용하면* *진짜 사고 가 *묻힌다*.

분기별 *알림 통계 리뷰* — *false positive 비율 > 30%* 인 룰은 *임계치 조정* 또는 *삭제*. *Git 으로 관리* 되므로 *PR 으로 검토 가능*.

---

## 5. *축 5 — 인프라 자가 운영 (K3s HA + 4 가지 핵심 인프라)*

### 5.1 *K3s HA (etcd 3 voter) — *control-plane 1 대 죽어도 *클러스터 살아 있음*

*실제 5 노드 토폴로지 (2026-06 시점)*:

| 노드 | 역할 | IP | 비고 |
|---|---|---|---|
| *lemuel* | control-plane + etcd | 192.168.219.101 | 메인 마스터, SSH 2652 |
| *ilwon* | control-plane + etcd | 192.168.219.110 | NVMe 1TB + 4TB HDD (storage tier) |
| *solomon* | control-plane + etcd | 192.168.219.108 | Floating VIP (3-NIC failover), 백업 전용 |
| *louise* | worker | 192.168.219.111 | 일반 워크로드 |
| *david* | worker | 192.168.219.107 | 모니터링 전용 (Prometheus / Grafana / Loki) |

- *etcd 3 voter quorum* — *2 대만 *살아 있으면* *클러스터 의사 결정 *계속 가능*
- *Floating VIP* — solomon 의 *3-NIC failover* 로 *NIC 1 개 *죽어도 *VIP 유지*
- *워크로드 분리* — david 는 *monitoring 전용 tier* 로 *labeled*, 운영 부하가 *관측 시스템 을 *압살하지 않도록*
- *역사* — K3s v1.35.4+k3s1 / *SQLite → embedded etcd 마이그레이션 완료 (2026-05-12)*. SQLite 단일 마스터에서 *진짜 HA* 로 *전환한 큰 변곡점*
- *마스터 추가 시 *반드시 동기화* — `/etc/rancher/k3s/config.yaml` 의 *top-level `cluster-dns`* 와 *`kubelet-arg.cluster-dns`* *둘 다 *같은 값 (169.254.20.10)*. 한쪽만 두면 *DNS 어긋남*

### 5.2 *NFS Storage — *공유 PV 의 *단순한 진리*

- `nfs-server` 차트 — *한 노드에 NFS 서버* + *모든 노드에 mount*
- *Velero 백업 본 / 빌드 artifact / 공유 정적 자산* 의 *common bucket*
- *CSI driver 같은 *복잡함 없이* *단일 마운트 포인트* 로 *대부분의 *공유 스토리지 요구* 해결

### 5.3 *Private Registry Mirror — *DockerHub rate-limit / 외부 의존 차단*

```yaml
# K3s registries.yaml
mirrors:
  docker.io:
    endpoint:
      - "https://registry.internal:5000"
  ghcr.io:
    endpoint:
      - "https://registry.internal:5000"
```

- *DockerHub anonymous rate-limit (100 pulls / 6h)* 를 *영구 회피*
- *외부 registry 장애 시에도 *내부 이미지 *재배포 가능*
- *이미지 가 *내부에 *캐시* — *pull 속도 *상승*

### 5.4 *frp Tunnel — *외부에서 내부 서비스로의 *안전한 통로*

```
[Public DDNS / SaaS]  →  [frp server (외부 VPS)]  →  [frp client (내부 K3s)]  →  [Service]
```

- *내부 서비스 (Kibana, Grafana, ArgoCD UI)* 를 *NAT 뒤에 두면서도* *외부 합법 접근 만 *허용*
- *공유기 포트 포워딩 / 고정 IP 없이도* *production 도메인 운영*

### 5.5 *SOPS-Operator — *암호화된 시크릿을 *Git 에 둔다*

```yaml
# secrets/settlement-postgres.sops.yaml — 일부 (암호화된 상태로 commit)
apiVersion: v1
kind: Secret
data:
  password: ENC[AES256_GCM,data:...]
sops:
  age:
    - recipient: age1...
```

- *Git 에 *암호화된 상태로 *commit* — *audit trail 보존* + *복호화 키 없는 사람은 못 읽음*
- *클러스터 의 *SOPS-Operator* 가 *런타임에 *복호화* → *일반 Secret 으로 *변환*
- *복호화 키 (age private key)* 는 *클러스터에만 *존재*, *Git 에는 *없음*

### 5.6 *5 가지 인프라의 *공통 철학*

> *외부 SaaS 의 *editable knob* 을 *최소화* 하고, *Git 으로 *재현 가능* 한 *self-managed* 인프라로 *집중*.

- *외부 의존 ↓* — DockerHub / SaaS 가 *터져도 *우리는 *살아 있다*
- *Git 단일 소스* — *재구축 가능*, *audit 가능*
- *복잡함 ↓* — *NFS / etcd / frp / SOPS — 각각 *단순하고 *오래된 *기술*

---

## 6. *운영 플레이북 — *내가 *매일 *클러스터 를 *움직이는 방법*

### 6.1 *진입점 — *root-app 의 *App-of-Apps 패턴*

```yaml
# root-app.yaml — 클러스터의 *유일한 *수동 apply 대상*
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
spec:
  source:
    repoURL: https://github.com/MyoungSoo7/helm-deploy
    targetRevision: master
    path: argocd-applications
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

- *root-app 자체 만* `kubectl apply -f root-app.yaml` *수동 1 회*
- 그 후로는 *root-app 이 *argocd-applications/ 디렉터리 의 *모든 Application CR* 을 *자동 sync*
- *prune: true* — Git 에서 *파일을 *지우면 *클러스터에서도 *제거*
- *selfHeal: true* — *수동 `kubectl edit` drift* 가 *발생하면 *Git 상태로 *되돌림*

### 6.2 *새 앱 추가 — *4 단계 *고정 절차*

```bash
# 1. 차트 작성
mkdir -p charts/myapp/templates
$EDITOR charts/myapp/Chart.yaml charts/myapp/values.yaml charts/myapp/values-prod.yaml

# 2. Application CR 추가 (기존 academy-prod.yaml 패턴 복사)
cp argocd-applications/academy-prod.yaml argocd-applications/myapp-prod.yaml
$EDITOR argocd-applications/myapp-prod.yaml   # path, namespace 만 바꿈

# 3. 시크릿 (필요 시)
$EDITOR /tmp/myapp-secret.yaml                 # 평문 작성
sops --encrypt --in-place /tmp/myapp-secret.yaml
mv /tmp/myapp-secret.yaml secrets/myapp-secret.sops.yaml

# 4. push — ArgoCD 가 알아서 sync
git add . && git commit -m "feat(myapp): add app" && git push
```

→ *수동으로 `kubectl apply` 하는 일이 *없다*. 모든 *클러스터 변경 = git push*.

### 6.3 *앱 폐기 — *git rm 한 줄*

```bash
git rm argocd-applications/myapp-prod.yaml
git commit -m "chore(myapp): retire" && git push
# root-app 의 prune: true 가 cascade 로 namespace · PVC · Service 모두 정리
```

### 6.4 *시크릿 수정 — *SOPS 의 마법*

```bash
sops secrets/settlement-postgres.sops.yaml
# → 에디터 가 *평문으로 *열리고*
# → 저장 시 *자동으로 *다시 *암호화*
git add -u && git commit -m "chore(secrets): rotate settlement-postgres" && git push
```

- *Git 에는 *항상 *암호화된 상태 만 *commit*
- *복호화 키 (age private key)* 는 *클러스터 의 *SOPS-Operator 만 *보유* — *Git 에는 *없음*

### 6.5 *수동 디버깅 — *마스터에서 `sudo kubectl`*

```bash
# lemuel 마스터에 SSH
ssh -p 2652 lemuel
sudo kubectl get pods -A | grep -v Running
sudo kubectl logs -n settlement-prod deploy/order-service --tail=200
sudo kubectl describe pod -n settlement-prod order-service-xxx
```

- `/etc/rancher/k3s/k3s.yaml` 권한 때문에 *`sudo` 필수*
- *수동 변경은 *금지* — `selfHeal: true` 가 *Git 으로 되돌림*

### 6.6 *ArgoCD UI — *육안 모니터링*

- `argocd.example.com` — *외부 frp 로 노출*
- *47 개 Application 의 *Health × Sync* 매트릭스 *한 화면*
- *Out-of-sync 노랑 / Degraded 빨강* 이 *알람보다 *먼저 *보일 때가 많다*

### 6.7 *내 *하루 *운영 패턴*

| 시간 | 행동 |
|---|---|
| 아침 | ArgoCD UI / Grafana 대시보드 / Telegram 알림 history *5 분 스캔* |
| 작업 시 | helm-deploy 의 *PR 로 변경* (직접 push 도 가능 하지만 *PR 권장*) |
| 알림 시 | Telegram → Kibana / Grafana 점프 → *근본 원인 까지 *5 분 내 도달* 목표 |
| 주간 | *false positive 알림 통계* 리뷰 → 룰 조정 PR |
| 분기 | *Velero restore + pg_dump 복원* *staging 검증* |

→ *"하지 않는 일"* 이 *명확*: *kubectl apply 수동 / kubectl edit 직접 변경 / 평문 시크릿 commit / 클러스터에서 *수동 helm install*.

---

## 7. *통합 아키텍처 — *5 개 축이 *어떻게 *겹치나*

```
[Developer commits code]
    ↓
[GitHub Actions]  → 이미지 빌드 + ghcr push  ← Playwright E2E 게이트 (축 3)
    ↓
[ArgoCD Image Updater]  → helm-deploy 자동 commit (축 1)
    ↓
[ArgoCD] watches helm-deploy → cluster sync  ← Self-heal + Prune (축 1)
    ↓
[K3s 6 node HA]                              ← etcd quorum (축 5)
  ├ Pod scheduling
  ├ NFS / Registry / frp                     ← 인프라 자가 운영 (축 5)
  └ Pod start
    ↓
[Fluent-bit DaemonSet]    → ES               ← 로그 (축 1)
[Prometheus + Tempo]      → Grafana           ← 메트릭 / 트레이스 (축 1)
    ↓
[Alertmanager]            → Telegram          ← 운영 관제 (축 4)
    ↓
[Uptime Kuma]             → 외부 도메인 검증   ← 배포 후 게이트 (축 3)
    ↓
[Velero + 14 pg_dump CronJob]                ← 이중 백업 (축 2)
```

*핵심 통찰*:

- *5 개 축은 *독립* 이 *아니라* *직교* 한다. *각자 다른 차원* 의 *위험* 을 *덮는다*.
- *코드 1 줄* 이 *production* 까지 가는 *모든 좌석* 에 *안전벨트* 가 *있어야* 한다.

---

## 8. *운영 경험에서 얻은 *3 가지 교훈*

### 8.1 *"Healthy 가 *Healthy 가 *아니다"*

> *ArgoCD 가 *Healthy* 라고 말해도 *외부 사용자 가 *못 보면* *그것은 *Unhealthy* 다.

- *내부 신호* (`kube_pod_status_ready`, `argocd app health`) 와 *외부 신호* (Uptime Kuma 의 *body keyword*) 를 *둘 다 *측정*
- *둘이 *동시에 *green 일 때만 *진짜 *healthy*

### 8.2 *"백업은 *복원해 본 적 없으면 *백업이 아니다"*

- 분기별 *staging 클러스터에 *Velero restore + pg_dump 복원* *수동 검증*
- *RTO 측정 결과* 를 *Grafana 에 *수치로 *남긴다* — *팀이 *기대치를 *공유*

### 8.3 *"알림은 *시끄러우면 *읽히지 않는다"*

- *severity 별 채널 분리* — *infra-critical / deploy / cronjob-fail*
- *분기별 *false positive 비율 리뷰* — *> 30% 룰은 *조정 또는 *삭제*
- *알림 룰도 *Git 으로 *PR 리뷰*

---

## 9. *결론 — *GitOps + 통합 관측 의 *진짜 가치*

> *코드를 짜는 것은 *쉽다*. *그 코드 가 *production 에서 *영원히 *돌게 하는 것* 이 *어렵다*.

GitOps 와 통합 관측 체계는 *그 어려움* 을 *5 개 축* 으로 *나눠 *분담* 시킨다.

| 축 | 무엇을 *없애 주는가* |
|---|---|
| *1. 3-pillar 관측* | *"어디서 무엇이 *왜 *느린지 모름"* 의 *불안* |
| *2. 이중 백업* | *"되돌릴 수 없음"* 의 *공포* |
| *3. 품질 게이트* | *"내가 *모르는 *사이 *깨졌나"* 의 *의심* |
| *4. 운영 관제* | *"뭔가 *터졌는데 *나만 *모르나"* 의 *고립감* |
| *5. 인프라 자가 운영* | *"외부 SaaS 가 *우리 운명* 을 *쥐고 있다"* 의 *통제 불능* |

→ 이 5 가지 가 *동시에 충족* 되어야 *운영자가 *밤에 *잠을 잘 수 있다*. 그리고 *그것이 *production 운영 의 *진짜 KPI* 다.

---

## 부록 — 사용 기술 한 줄 요약

| 분류 | 도구 |
|---|---|
| *GitOps* | ArgoCD (App-of-Apps), ArgoCD Image Updater |
| *Cluster* | K3s v1.35+, embedded etcd, 6 노드 |
| *Manifest* | Helm 3, Kustomize 패치 |
| *Logs* | Fluent-bit (DaemonSet), Elasticsearch (ECK), Kibana |
| *Metrics* | kube-prometheus-stack, 32 PrometheusRule, Grafana |
| *Traces* | Grafana Tempo |
| *Backup* | Velero (off-site R2), pg_dump CronJob × 14 |
| *Quality gate* | Playwright E2E, Uptime Kuma (외부 도메인 검증) |
| *Alerting* | Alertmanager → Telegram (3 채널 분리) |
| *Self-managed infra* | NFS Server, Private Registry Mirror, frp Tunnel, SOPS-Operator |
| *Secrets* | SOPS + age, Git 에 *암호화 상태로 *commit* |

> *"운영의 *모든 변경* 은 *Git 으로 *간다*. *모든 *수치* 는 *대시보드로 *간다*. *모든 *사고* 는 *Telegram 으로 *간다*. *모든 *상태* 는 *복원 가능* 하다."* — 이것이 *5 개 축이 *그리는 *세계* 다.
