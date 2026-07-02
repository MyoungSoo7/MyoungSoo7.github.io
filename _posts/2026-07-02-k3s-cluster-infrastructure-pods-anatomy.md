---
layout: post
title: "K3s 클러스터 의 *시스템 pod 해부* — 6 노드 위 에 얹은 80 개 인프라 컴포넌트"
date: 2026-07-02 19:45:00 +0900
categories: [devops, kubernetes, k3s, observability, gitops]
tags: [k3s, kube-system, argocd, velero, prometheus, grafana, elk, fluent-bit, tempo, cert-manager]
---

내 6 노드 K3s 홈랩 클러스터 에는 *약 215 개 pod* 이 실행 중. 그 중 **80 여 개 가 *인프라 (system) pod***. *애플리케이션 이 아니라 *클러스터 자체 를 돌리는 pod*. 이 글 은 그 *64 개 핵심 인프라 pod* (kube-system + logging + monitoring + argocd + velero) 를 *하나씩 해부* 하고, *왜 이 구성 이 성숙 한 지* 정리.

---

## 1. 전체 인프라 pod 총 정리

| 카테고리 | Pod 수 | 성숙 도 |
|---|---|---|
| K8s 코어 (kube-system) | **23** | ⭐⭐⭐⭐⭐ |
| Observability — Logging (ELK) | **16** | ⭐⭐⭐⭐⭐ |
| Observability — Metrics (Prometheus 스택) | **12** | ⭐⭐⭐⭐⭐ |
| GitOps (ArgoCD) | **8** | ⭐⭐⭐⭐⭐ |
| Backup (Velero — 실 실행) | **5** | ⭐⭐⭐⭐ |
| 기타 인프라 (ECK, Kafka, cert-manager, SOPS 등) | ~15 | ⭐⭐⭐⭐ |
| **합계** | ~80 | 중견 SaaS 급 |

---

## 2. kube-system (23 pod) — *K8s 의 심장*

*Kubernetes 자체* 가 돌아가는 데 필요 한 컴포넌트. K3s 는 이 중 대부분 을 *자동 배포*.

### 필수 5 종

| Pod | 수 | 역할 |
|---|---|---|
| **coredns** | 2 | K8s 클러스터 내부 DNS (`{svc}.{ns}.svc.cluster.local` 해석) |
| **node-local-dns** | 6 | *각 노드 의 *DNS 캐시 daemon* — DNS 지연 μs 급 단축 |
| **metrics-server** | 1 | `kubectl top` 의 데이터 소스, HPA 의 기반 |
| **local-path-provisioner** | 1 | K3s 의 *기본 storage* (호스트 디스크 를 PVC 로) |
| **traefik** | 1 | K3s 기본 ingress controller |
| **svclb** | 5 | Traefik LoadBalancer 의 per-node service DaemonSet |

### 부가 컴포넌트

- **elastic-secret-replicator** (3) — CronJob 기반 secret 복제
- **etcd-leader-pin** (2 completed) — etcd leader 안정화 CronJob 완료 잔재
- **helm-install** (1 completed) — K3s 부팅 시 Helm 차트 설치 job

### 왜 이 구성 이 *잘 된 것* 인가

**node-local-dns 6 개** 는 *typical K8s 클러스터 에 잘 없는 컴포넌트*. 각 노드 에 *DNS 캐시* 를 두어:
- coredns 로 가는 traffic *90% 절감*
- DNS 지연 이 *ms → μs* 개선
- 클러스터 규모 확장 시 필수

*홈랩 이 이 정도 까지 구성* 됐다는 것 은 성숙도 표시.

---

## 3. logging (16 pod) — *완전 한 ELK 스택*

```
Application pod stdout
    ↓ (파일 로 기록)
/var/log/containers/*.log
    ↓
Fluent Bit DaemonSet (per node)
    ↓ (수집 + 필터 + 라우팅)
Logstash (grok 변환, enrichment)
    ↓
Elasticsearch 3-tier (Hot / Warm / Cold)
    ↓
Kibana (시각화)
```

### 구성

| Pod | 수 | 역할 |
|---|---|---|
| **fluent-bit** | 5 | *DaemonSet* — 각 노드 의 로그 수집 (lemuel cordoned 이라 5, 정상 은 6) |
| **logstash** (`logs-ls-0`) | 1 | 중앙 변환 + Slack alerting 라우팅 |
| **Elasticsearch Hot** (`logs-es-hot-0`) | 1 | *NVMe SSD*, 최근 7 일 활발 read/write |
| **Elasticsearch Warm** (`logs-es-warm-0`) | 1 | *SATA SSD*, 7~30 일 read 위주 |
| **Elasticsearch Cold** (`logs-es-cold-0`) | 1 | *HDD*, 30 일+ 감사 보관 |
| **Kibana** (`logs-kb-*`) | 1 | 웹 UI + 대시보드 |
| **kb-dashboards** | 1 | 커스텀 대시보드 provisioner |
| **es-advanced** | 1 | ILM 정책 세팅 job |
| **log-error** | 3 | *별도 pipeline* — error 만 별도 라우팅 |

### 세부 특징

- **3-tier ILM**: Hot → Warm → Cold → Delete (90 일)
- **ECK Operator** 로 자동 인증서 / rolling upgrade
- **11 개 운영 대시보드** in Kibana (Cluster Overview, Pod CrashLoop, Slow Query, GC Pressure, ...)

이 스택 만 으로 *중견 회사 의 로그 관리 요구 전부 충족*. *자세한 원리 는 [Logstash 와 ES glob](/2026/06/29/logstash-and-elasticsearch-from-fluent-bit-to-ilm.html)* 참고.

---

## 4. monitoring (12 pod) — *kube-prometheus-stack + Tempo*

메트릭 + 알림 + 분산 추적 의 *3 축 완성*.

### 구성

| Pod | 수 | 역할 |
|---|---|---|
| **Prometheus** (`prometheus-kps-prometheus-0`) | 1 | 메트릭 수집·저장·쿼리 |
| **Alertmanager** (`alertmanager-kps-alertmanager-0`) | 1 | 알림 라우팅 (Slack, Telegram, email) |
| **Grafana + Operator** (`kps-*`) | 2 | 시각화 + Prometheus Operator |
| **node-exporter** DaemonSet | 6 | 각 노드 의 CPU/메모리/디스크 metric |
| **kube-state-metrics** | 1 | K8s 리소스 메트릭 (deployment, pod, node status) |
| **Tempo** (`tempo-0`) | 1 | *distributed tracing* — OpenTelemetry backend |

### 왜 성숙 한가

**Tempo 의 추가** — *3 종 observability (Metrics, Logs, Traces) 완성*:
- 로그 는 Kibana 로 어디 서 문제 났나 파악
- 메트릭 은 Grafana 로 언제 문제 났나 파악
- **Traces 는 왜 문제 났나** — request chain 을 *microservice 간 recursive 로 시각화*

내 sparta-msa 의 *Outbox → Kafka → Consumer* 흐름 을 *한 화면 에 trace* 가능. *별도 상용 도구 (Datadog $60/host/month)* 없이 *로컬 에서 무료 완성*.

---

## 5. argocd (8 pod) — *GitOps 의 얼굴*

| Pod | 수 | 역할 |
|---|---|---|
| **argocd-server** | 1 | 웹 UI + gRPC API |
| **argocd-application-controller-0** | 1 | *진짜 심장* — git ↔ cluster 비교 + reconcile |
| **argocd-repo-server** | 1 | git 리포 clone + Helm/Kustomize 렌더링 |
| **argocd-notifications-controller** | 1 | Slack / Telegram 알림 |
| **argocd-image-updater** | 1 | ghcr 새 이미지 감지 + git write-back |
| **argocd-dex-server** | 1 | SSO/OIDC (사용 안 하면 idle) |
| **argocd-applicationset-controller** | 1 | 여러 앱 을 template 로 자동 생성 |
| **argocd-redis** | 1 | 캐시 |

### 왜 이 8 개 가 필요 한가

각 pod 이 *하나의 책임 만*:
- **server** — UI/CLI 만 응답
- **controller** — 상태 조정 만
- **repo-server** — Helm render 만
- **image-updater** — image tag 관리 만

*마이크로서비스 원칙 을 *ArgoCD 자체 에 적용*. 확장 시 각 컴포넌트 독립 스케일 가능.

*자세한 사용법 은 [ArgoCD 실전 사용 가이드](/2026/07/02/argocd-hands-on-usage-guide.html)* 참고.

---

## 6. velero (47 pod, 실 실행 5) — *backup 의 함정*

### 실 pod 만 보면 5 개

| Pod | 수 | 역할 |
|---|---|---|
| **velero-server** | 1 | 백업 orchestrator |
| **node-agent** DaemonSet | 4 | 각 worker 노드 의 file-system backup (kopia uploader) |

### 나머지 42 개 는 *completed backup job*

Velero 는 *`Schedule` CRD* 로 *매시간 kopia maintenance job* 자동 실행. 각 backup repo (namespace 별) 마다 1 개 씩:
- academy-prod, argocd, asat-prod, codingtest-prod, ...
- 총 ~15 개 repo × 시간당 1 = 매시간 15 개 새 Job
- Job 은 완료 되어도 *자동 삭제 안 됨* → 축적

### 정리 방법

**수동 정리**:
```bash
kubectl delete jobs -n velero --field-selector status.successful=1
```

**자동 정리** (권장):
- Kubernetes `Job.spec.ttlSecondsAfterFinished: 86400` (24h)
- 그러나 Velero 가 생성 하는 Job 은 *velero 소스 에서 설정 안 함* → CronJob 으로 우회

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: velero-job-cleanup
  namespace: velero
spec:
  schedule: "0 3 * * *"  # 매일 03:00
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: velero
          containers:
          - name: cleanup
            image: bitnami/kubectl
            command:
            - sh
            - -c
            - kubectl delete jobs -n velero --field-selector status.successful=1
          restartPolicy: OnFailure
```

내 클러스터 는 아직 자동 정리 미구축 — TODO.

---

## 7. 기타 인프라 (약 15 pod)

이 표 에 없지만 실행 중 인 *숨은 인프라*:

| namespace | Pod | 용도 |
|---|---|---|
| **elastic-system** | 1 | ECK Operator — Elasticsearch 자동 관리 |
| **kafka** | 3 | Kafka broker + zookeeper (Outbox 이벤트 발행) |
| **kubernetes-dashboard** | 3 | Web UI (k8s.lemuel.co.kr) |
| **cert-manager** | 1 | Let's Encrypt 자동 갱신 (Cloudflare Tunnel 사용 시 idle) |
| **ingress-nginx** | 1 | Nginx ingress (Traefik 병행) |
| **sops-operator** | 1 | SopsSecret CRD reconciler |
| **registry-mirror** | 1 | Docker Hub / ghcr mirror |
| **nfs-server** | 1 | 공유 스토리지 (일부 앱 이 참조) |
| **frp-prod** | 2 | 원격 접근 tunnel |
| **echo-webhook** | 1 | Webhook 테스트 유틸 |
| **homelab-dashboard** | 1 | 홈랩 서비스 tile 대시보드 |

*이 중 몇 개 는 실 사용 여부 재검토 대상* (예: `frp-prod` 이 실제 로 traffic 받고 있는지, `echo-webhook` 이 필요한지).

---

## 8. 성숙 도 매트릭스 — *홈랩 vs 프로덕션*

| 항목 | 내 클러스터 | 홈랩 평균 | 중견 SaaS |
|---|---|---|---|
| K8s 코어 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **node-local-dns** | ✓ | ✗ | ✓ |
| Metrics + Alerts | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Distributed Tracing** | ✓ | ✗ | ✓ |
| **Log Aggregation** (ELK) | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| **3-tier ILM** | ✓ | ✗ | 부분 |
| GitOps | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Image Updater** | ✓ | ✗ | 부분 |
| Backup (Velero) | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Secret Management (SOPS) | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ (Vault) |
| **총점** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**결론**: *중견 SaaS 회사 의 K8s 관리 수준*. *홈랩 관점 에서 는 *과잉 을 넘어 학습·포트폴리오 최고 급*.

---

## 9. 개선 여지 5 가지

### (1) Velero completed job 자동 정리
- CronJob 으로 매일 03:00 삭제
- 미구축 → *매 시간 15 개 accumulate*

### (2) Ingress 이중화
- Traefik (K3s default) + ingress-nginx *둘 다 실행*
- 하나 만 남기고 정리 필요 (트래픽 routing 검증 후)

### (3) cert-manager 실 사용 검토
- Cloudflare Tunnel 이 TLS 처리 → cert-manager 미사용 가능성
- 사용 안 하면 삭제

### (4) Descheduler 도입 검토
- 노드 부하 불균형 시 pod 자동 재배치
- ilwon (81% mem) vs solomon (36% mem) 균형 조정

### (5) etcd backup 자동화
- Velero 는 PVC / K8s 리소스 백업
- etcd 는 별도 — K3s 의 `etcd-snapshot` 자동 (per node local)
- *R2 로 외부 백업* 추가 권장

---

## 10. 마치며 — *"홈랩 이 아니라 mini-Prod"*

이 80 개 인프라 pod 의 조합 은 *typical 홈랩 을 훨씬 초과*. *중견 SaaS 회사 의 SRE 팀 이 관리 하는 스택* 과 유사.

**핵심 강점**:
- **완전 한 observability 3층** (Metrics + Logs + Traces)
- **GitOps 완성** (ArgoCD + Image Updater + SOPS)
- **자동화** (backup, Let's Encrypt, node-local-dns)
- **재해 복구** (Velero + Kopia + R2)

**핵심 학습**:
- *애플리케이션 pod (~135)* 보다 *인프라 pod (~80)* 가 *더 많은 시간* 을 잡아먹는 게 정상
- *운영 시간 의 대부분 은 인프라 유지 보수* — 이걸 이해 하는 것 이 *DevOps / SRE 의 시작*
- *pod 수 자체 는 의미 없음* — *어떤 pod 이 *왜 있는지* 이해* 가 중요

내 클러스터 의 *14 개월 운영 경험* — 인프라 pod 을 *처음 부터 완비* 하려 하지 말고, *필요할 때 마다 하나 씩 추가*. 그러다 보면 어느 순간 *중견 SaaS 급 클러스터* 가 완성. 이게 *GitOps + 관측 성 + 백업* 3 축 이 만드는 *지속 가능 한 운영*.

**핵심 메시지**: *"인프라 pod 80 개 는 *과잉 이 아니라 *필수*. *하나 씩 이해 하는 순간* K8s 는 *마법 이 아니라 *합리적 시스템* 이 됨"*

---

## 참고

- **K3s 공식** — [k3s.io/docs](https://docs.k3s.io/)
- **kube-prometheus-stack** — [github.com/prometheus-community/helm-charts](https://github.com/prometheus-community/helm-charts)
- **ECK (Elastic Cloud on Kubernetes)** — [elastic.co/guide/en/cloud-on-k8s](https://www.elastic.co/guide/en/cloud-on-k8s/current/)
- **Argo CD 공식** — [argo-cd.readthedocs.io](https://argo-cd.readthedocs.io/)
- **Velero 공식** — [velero.io/docs](https://velero.io/docs/)
- **Grafana Tempo** — [grafana.com/oss/tempo](https://grafana.com/oss/tempo/)
- **node-local-dns 원리** — [Kubernetes NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)
- 자매편:
  - [ArgoCD 실전 사용 가이드](/2026/07/02/argocd-hands-on-usage-guide.html)
  - [K3s vs K8s 현실 비교](/2026/06/24/k3s-vs-k8s-realistic-comparison.html)
  - [Prometheus 가 어떻게 메트릭 을 수집 하고 Grafana 에 시각화 하는가](/2026/06/19/prometheus-metrics-collection-and-grafana-visualization.html)
  - [Logstash 와 Elasticsearch — Fluent Bit 파이프라인 부터 ILM 까지](/2026/06/29/logstash-and-elasticsearch-from-fluent-bit-to-ilm.html)
