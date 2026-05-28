---
layout: post
title: "Lemuel K3s 의 ELK 운영 구조 — GitOps + ECK Operator + Fluent Bit→Logstash→ES 3-stage 파이프라인"
date: 2026-05-19 23:30:00 +0900
categories: [infra, observability]
tags: [k8s, k3s, elk, elasticsearch, kibana, logstash, fluent-bit, eck, argocd, gitops, helm, ilm, hot-warm-cold]
---

5월 19일 밤, 홈 K3s 클러스터(**Lemuel**)의 ELK 스택이 *실제로* 어떻게 굴러가는지 한 번 정리하고 싶었다. "fluent-bit 으로 로그 수집한다" 같은 한 줄 설명 말고, **무엇이 누구를 띄우고, 누가 누구한테 로그를 던지는지** 까지.

이 글은 그 한 시간 짜리 워크스루를 5가지 주제로 정리한 결과다.

> ⚠️ 보안 — 클러스터 내부 IP / 노드명 / 도메인은 모두 redacted. 구조와 패턴만 공유.

---

## TL;DR — 5가지 인사이트

| # | 주제 | 핵심 발견 | 왜 흥미로운가 |
|---|---|---|---|
| 1 | **3 개 ArgoCD App 분리** | `elk-cluster`, `elk-storage`, `fluent-bit` 가 각각 별 App. 스토리지/CR/수집기 라이프사이클이 독립. | 한 App 으로 묶으면 PV·StorageClass 가 ES CR 보다 늦게 sync 돼서 데이터 노드가 영원히 Pending. 분리는 *순서 보장* 의 답. |
| 2 | **ECK Operator + Helm CR-only** | Helm 차트는 `Elasticsearch` / `Kibana` / `Logstash` CR 만 적고, 실제 STS·Service 는 ECK Operator 가 만든다. | Helm 이 모든 K8s 리소스를 직접 갈아엎는 *낡은 패턴* 대신, *선언적 spec + operator 재구성* 모델. |
| 3 | **ES Hot / Warm / Cold 3-tier** | 단일 클러스터 안에 `master+data_hot` / `data_warm` / `data_cold` 3 nodeSet. ILM 정책으로 인덱스가 시간순 이동. | 1인 클러스터에서도 ILM 학습이 가능한 *최소 토폴로지*. |
| 4 | **Fluent Bit → Logstash → ES 3-stage** | fluent-bit 가 ES 로 직접 안 쏜다. 의도적으로 Logstash 를 거치도록 파이프라인을 끊어 놓음. | Fluent Bit 의 `record_modifier` 만으론 못 하는 *복잡 enrich/parse* 를 Logstash 에서 처리. 학습 목적도 있음. |
| 5 | **ECK Operator restart 사이클 vs ArgoCD drift** | operator pod 가 44h 동안 218 회 restart (exit 0). Argo App 은 OutOfSync. operator 가 spec 에 자기 필드를 덧붙여서 drift 발생. | Helm-managed CR 과 Operator 자가 패치의 *고전적 충돌*. 해법은 `ignoreDifferences` + lease tuning. |

기술 스택: **K3s 1.35.4 + ECK Operator + Elasticsearch 8.16.1 + Kibana 8.16.1 + Logstash 8.16.1 + Fluent Bit (Helm chart 0.57.5)** — ArgoCD 가 helm-deploy GitOps 레포의 master 브랜치를 폴링.

---

## 1. 왜 ArgoCD App 을 3 개로 쪼갰나

처음엔 모든 ELK 리소스를 `elk-cluster` 라는 App 하나에 몰아넣었다. 결과는 비참했다 — **Elasticsearch StatefulSet 이 영원히 Pending**.

원인은 sync 순서였다. ArgoCD 는 한 App 안의 리소스를 sync wave 로 정렬하지만, `StorageClass` 와 `PersistentVolume` 같은 클러스터 스코프 리소스는 ES `StatefulSet` 보다 빨리 적용되어도 *PV 실제 생성* 은 첫 PVC 요청 때 일어난다. 그리고 ES STS 가 PVC 를 만들 때 StorageClass 이름이 typo 한 글자만 있어도 영원히 Pending.

해결: 라이프사이클을 강제로 분리.

```
[ArgoCD]
├── elk-storage   ← StorageClass + 정적 PV
├── elk-cluster   ← Elasticsearch / Kibana / Logstash CR + Jobs / CronJob
└── fluent-bit    ← 외부 차트 @0.57.5 (DaemonSet)
```

`elk-storage` 가 먼저 Healthy 되어야 `elk-cluster` 가 PV 를 안전하게 잡는다. 그리고 fluent-bit 은 ES 와 *완전히 다른 라이프사이클* — fluent-bit chart 만 업데이트해도 ES 가 흔들리면 안 된다.

> 💡 모놀리식 App 으로 묶이면 한 번의 sync 실패가 *전체 ELK* 를 OutOfSync 로 만든다. 작은 App 은 blast radius 가 작다.

---

## 2. ECK Operator + Helm 차트가 *CR만* 적는 이유

내 `elk-cluster` 차트의 templates 디렉토리:

```
templates/
├── elasticsearch.yaml         # Elasticsearch CR (spec.nodeSets, version, ...)
├── kibana.yaml                # Kibana CR
├── kibana-nodeport.yaml       # 외부 노출용 NodePort Service
├── logstash.yaml              # Logstash CR (pipelines.yml 포함)
├── advanced-es-setup.yaml     # 인덱스 템플릿/ILM 초기화 Job
├── dashboards-importer.yaml   # Kibana 대시보드 자동 import Job
└── error-alert-cronjob.yaml   # 5분마다 ERROR 로그 검사 CronJob
```

여기엔 StatefulSet 도, Service 도, ConfigMap 도 거의 없다. ES CR 하나만 적으면 **ECK Operator 가** 그걸 보고 STS / Headless Service / ConfigMap / Secret / NetworkPolicy 를 *자기 컨트롤러 루프 안에서* 만든다.

Helm 차트는 "이런 ES 클러스터를 원해" 라고 말만 하고, 실제 K8s 리소스 어셈블리는 Operator 가 한다. ES 노드 추가? `nodeSets[].count` 증가. 버전 업? `version` 한 줄 수정. 나머지는 Operator 가 rolling 으로 처리.

이 분업이 깨끗하게 굴러가려면 **Helm 이 CR 외 다른 걸 만들지 말아야** 한다. `kibana-nodeport.yaml` 처럼 *Operator 가 안 만드는* 외부 노출 Service 만 차트에 둔다.

---

## 3. Hot / Warm / Cold — 1 인 클러스터에서도 ILM 을 가르치는 토폴로지

ES CR 의 nodeSets:

```yaml
nodeSets:
  - name: hot
    count: 1
    config:
      node.roles: [master, data_hot, data_content, ingest, transform, remote_cluster_client]
  - name: warm
    count: 1
    config:
      node.roles: [data_warm, ingest, remote_cluster_client]
  - name: cold
    count: 1
    config:
      node.roles: [data_cold, remote_cluster_client]
```

각 nodeSet 이 별 StatefulSet 으로 분리되고, ECK 가 `node.roles` 를 jvm flag 와 함께 주입한다. 노드는 클러스터 안에서 `nodeSelector` 로 *storage 티어 노드* 에 핀.

ILM 정책 (별도 Job 으로 적용):
```
hot   (0d ~ 1d)  → 활발한 인덱싱
warm  (1d ~ 7d)  → 읽기 중심, 압축
cold  (7d ~ 30d) → 거의 안 읽힘, 최저가 저장
delete (30d~)    → 삭제
```

물리적으론 노드 3 개라 *복제 효과* 는 없지만, **인덱스 라이프사이클이 어떻게 동작하는지 학습하기엔 충분한 최소 토폴로지**다. cold 가 NotReady 면 cluster health 가 yellow — replica 가 cold tier 로 못 옮겨가서.

---

## 4. Fluent Bit → Logstash → ES — *3-stage 의 의도*

가장 흔한 패턴은 `Fluent Bit → Elasticsearch` 직결이다. CPU 도 적게 먹고 hop 도 짧다. 그런데 내 클러스터는:

```
[모든 노드] fluent-bit DaemonSet (5/5)
        │  tail kube logs → kubernetes filter → record_modifier
        ▼ HTTP 8080
[logging] Logstash (filter / enrich / route)
        ▼ HTTPS 9200
[logging] Elasticsearch (hot → warm → cold via ILM)
        ▼
[logging] Kibana
```

fluent-bit `OUTPUT` 설정:
```ini
[OUTPUT]
    Name   http
    Match  kube.*
    Host   logs-ls-api.logging.svc.cluster.local
    Port   8080
```

왜 굳이 Logstash 를 끼웠나 — 두 가지 이유.

1. **복잡 변환은 Logstash 가 강함.** Fluent Bit 의 `record_modifier` 는 단순 필드 추가/제거에 좋지만, *Java 스택트레이스 multi-line 머지* 나 *정규식 기반 메시지 파싱* 은 Logstash filter chain 이 훨씬 표현력 있다.
2. **라우팅 분기점이 한 군데.** 나중에 "에러 로그만 별도 인덱스 / DLQ 토픽" 으로 보내려면 Logstash 한 곳에서 if 분기로 끝난다. Fluent Bit 에 모든 라우팅 룰을 박으면 노드별로 복제되고, 룰 한 줄 바꾸려면 DaemonSet rolling restart 가 필요하다.

대가는 명확하다 — **hop 한 단계 증가, Logstash 가 SPOF**. 그래서 1 인 클러스터에서도 Logstash 컨테이너는 input/filter/output **3 개로 분리된 사이드카 패턴**으로 떠 있다 (logs-ls-0 3/3 Running).

---

## 5. Helm 이 자동으로 굴리는 보조 잡 3 개

ES 클러스터 띄우는 것만으로는 *볼 수 있는 게 없다*. 인덱스 템플릿이 없으면 매핑이 dynamic 으로 폭발하고, 대시보드가 없으면 Kibana 가 빈 화면이다. 그래서 차트에 자동화 Job 3 개를 넣었다.

### 5.1 `advanced-es-setup` Job

ES 가 Ready 되자마자 한 번 실행. ILM 정책, 인덱스 템플릿(`logs-*` 매핑), composable template 을 PUT 한다. 멱등하게 작성 — 이미 있으면 skip.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: es-advanced-setup-{{ .Values.elasticsearch.versionHash }}
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: setup
          image: curlimages/curl:8.10.1
          command: ["sh", "-c"]
          args:
            - |
              # ILM 정책 + 인덱스 템플릿 PUT
              curl -ksS -X PUT "https://logs-es-http:9200/_ilm/policy/logs-policy" ...
              curl -ksS -X PUT "https://logs-es-http:9200/_index_template/logs" ...
```

차트 버전을 올릴 때마다 Job 이름이 바뀌어 *새로 한 번 더 돈다*. ILM 정책 업데이트도 같은 메커니즘으로 흘러간다.

### 5.2 `dashboards-importer` Job

`dashboards/k8s-logs-overview.ndjson` 을 Kibana saved-objects API 로 POST. 차트 안에 ndjson 을 동봉했기 때문에 **클러스터 새로 깔아도 5 분 안에 동일한 대시보드** 가 뜬다.

### 5.3 `error-alert-cronjob` CronJob (*/5 \* \* \* \*)

5 분마다 ES 에 `level: ERROR` 쿼리를 날리고, hits.total 이 임계 넘으면 알림. 이미지는 `curlimages/curl:8.10.1` — 가장 가벼운 옵션. 알림 채널은 Slack/텔레그램.

세 잡 다 Helm 차트 안에 **선언적으로** 들어있어서, 새 클러스터에 elk-cluster 차트만 sync 하면 *바로 운영 가능한 상태* 가 만들어진다.

---

## 6. 실제 운영에서 만난 두 가지 흔적

### 6.1 ECK Operator restart 사이클

```
$ kubectl get pod -n elastic-system
NAME                 READY   STATUS        RESTARTS        AGE
elastic-operator-0   1/1     Terminating   218 (19h ago)   44h
```

44 시간에 218 회. 처음 보면 *crashloop 인가?* 싶지만 `Last State: Terminated (Reason: Completed, Exit Code: 0)`. panic 이 아니라 **leader election lease 만료로 정상 종료** 사이클이었다.

ECK Operator 는 active-active 가 아니라 leader 단일. lease 가 너무 짧으면 짧은 GC pause 에도 lease 를 놓치고 재시작. 해법은 lease 를 늘리는 것:

```yaml
- --enable-leader-election=true
- --leader-election-lease-duration=60s
- --leader-election-renew-deadline=40s
- --leader-election-retry-period=15s
```

(기본은 15s/10s/2s — 가정용 클러스터엔 너무 빡빡.)

### 6.2 ArgoCD OutOfSync — Operator 가 spec 에 자기 필드를 덧붙임

```
elk-cluster   OutOfSync   Progressing
elk-storage   OutOfSync   Healthy
```

ECK Operator 는 사용자가 적은 `Elasticsearch` CR 의 spec 에 자기 필요한 필드(예: `spec.transport.tls.selfSignedCertificate.subjectAltNames`)를 *자동으로 채워 넣는다*. ArgoCD 입장에선 git 의 desired state 와 live state 가 달라지니 OutOfSync.

해결은 두 가지.

1. `argocd.argoproj.io/sync-options: ServerSideApply=true` — server-side apply 로 컨트롤러가 덧붙인 필드는 무시.
2. `ignoreDifferences` 로 특정 path 만 제외.

```yaml
spec:
  ignoreDifferences:
    - group: elasticsearch.k8s.elastic.co
      kind: Elasticsearch
      jsonPointers:
        - /spec/transport/tls/selfSignedCertificate
```

helm-deploy 마지막 두 커밋이 정확히 이 두 줄을 추가한 것:

```
fix(elk): ArgoCD ignoreDifferences for ECK operator args (manual leader-elect patch)
fix(elk): ECK operator leader election lease 늘려 crash loop 해결
```

이걸 한 줄로 정리하면 — **Helm-managed CR 과 Operator 자가 패치의 충돌은 ELK 만의 문제가 아니다.** cert-manager, Istio, Prometheus Operator 다 같은 패턴. ignoreDifferences 화이트리스트는 어느 클러스터에서도 결국 필요해진다.

---

## 마무리 — 정리해두니까 정리되는 것들

이번에 정리하면서 알게 된 것:

1. **3 개 App 분리** 가 단순 취향이 아니라 *PV→CR sync 순서* 라는 실제 문제의 답이었다는 것.
2. **Helm + Operator + GitOps** 조합에서 Helm 의 역할은 *CR 선언* 까지로 좁히는 게 깨끗하다는 것.
3. 1 인 클러스터에 Hot/Warm/Cold 를 깔아두면 *복제 효과 없이도 ILM 학습 plate* 가 된다는 것.
4. Fluent Bit 직결이 정답인 줄 알았는데, **Logstash 를 끼우는 게 라우팅 분기점 측면에서 운영 단순화** 가 된다는 것.
5. Operator restart 가 *crashloop 처럼 보이지만 leader election lease* 인 경우가 많다는 것 — exit code 부터 확인.

다음으로는 ES cold tier 가 NotReady 인 이유(PV mount 실패 가능성) 와 logstash pipeline 의 `if` 라우팅 추가 두 가지를 다뤄볼 예정. ELK 시리즈로 묶일 것 같다.

---

### 참고

- ECK Operator docs — leader election flags
- Argo CD docs — `ignoreDifferences`, ServerSideApply
- Elasticsearch ILM, data tier (hot/warm/cold/frozen)
- Fluent Bit `http` output plugin
