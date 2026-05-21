---
layout: post
title: "ECK operator 가 42시간 동안 406번 재시작했다 — OOM 인 줄 알았는데 leader election lease 였다 + Spring·Python OpenTelemetry 풀체인"
date: 2026-05-21 22:10:00 +0900
categories: [infra, kubernetes, observability, postmortem]
tags: [eck-operator, elasticsearch, leader-election, opentelemetry, tempo, grafana, postmortem, lemuel-xr]
---

ECK operator 가 *8분당 1회* 재시작하고 있었다. 42시간에 **406회**. 첫 가설: OOM. 사실: 그렇지 않다. 진짜 원인은 *leader election lease renewal* 였고, *Exit 0 / Reason "Completed"* 라는 단서가 일찍부터 있었는데 못 봤다.

이 글은 그 디버깅 + 같이 끝낸 *OpenTelemetry traces 풀체인 도입* 두 가지를 묶는다.

> **공통 교훈**: *재시작 카운트가 높다* 와 *시스템이 망가졌다* 는 다른 명제. Exit 0 면 *코드가 자기 종료* 한 것이고, *왜 종료가 트리거됐는지* 가 진짜 질문이다.

---

## TL;DR

| 영역 | 가설 | 실제 | 수정 |
|---|---|---|---|
| ECK operator 406회 재시작 | OOM (heap 부족) | **leader election lease renewal 실패** (kube-apiserver connection reset) | `--leader-election-lease=30s` (default 15초 → 30초) + `--kube-client-timeout=5m` |
| elk-cluster ArgoCD OutOfSync 무한 | spec drift | ECK operator 가 *자기가 만든 CR.status* 를 매 reconcile 마다 patch | ArgoCD `ignoreDifferences` 로 `/status` 무시 |
| node-exporter david 738회 SIGTERM | 메모리 압박 | (메모리 24%, eviction 0건 — 원인 미상) | restart count cleanup CronJob 으로 *증상* 만 정리 |
| 알람 신호 대 잡음비 | 알람 도착이 *많다 = 활동 많다* | 알람의 99% 가 *같은 pod 의 같은 패턴 반복* | PrometheusRule 의 `for: 10m` 임계로 짧은 churn 무시 |
| 분산 traces | 로그만으로 충분 | classify 600ms 중 어디가 LLM API 인지 DB 인지 모름 | Spring + Python OTel → Tempo, logging pattern 에 `[traceId/spanId]` 박음 |

---

## 1. ECK operator — 1차 가설이 틀린 경우

### 1.1 증상

```
$ kubectl -n elastic-system get pods
elastic-operator-0   1/1   Running   406 (4m27s ago)   2d
```

Running 인데 restart count 406. 컨테이너 정상인데 *왜 자꾸 죽었다 살아나*? 운영 영향은 없는 것 같은데 매시간 알람이 6~7번씩 온다.

### 1.2 1차 가설 — OOM

JVM heap 부족이 *operator restart loop 의 전형 케이스* 라서 자연스럽게 가정. 정황도 맞아 보였다:
- ECK operator 는 Go 가 아니라 Java 라고 *잘못 알고 있었음* (실제로는 Go)
- `kubectl describe` 가 안 보고 바로 *heap 증액* 으로 갔다면 30분 낭비했을 것

### 1.3 진짜 단서 — Exit 0

```bash
$ kubectl -n elastic-system describe pod elastic-operator-0
...
Last State:     Terminated
  Reason:       Completed       ← 핵심
  Exit Code:    0               ← 핵심
  Started:      Thu, 21 May 2026 21:16:28 +0900
  Finished:     Thu, 21 May 2026 21:45:58 +0900
```

**Exit 0 + Reason "Completed" = OOM 절대 아님.** OOM 이면 Exit 137 / Reason "OOMKilled". *Completed* 는 컨테이너가 *자기가 main 함수 끝까지 갔다* 는 신호.

→ 가설 즉시 폐기. *왜 process 가 정상 종료까지 갔는가* 가 새 질문.

### 1.4 진짜 원인 — leader election

ECK operator 의 마지막 로그:

```json
E0521 12:49:05.646257 1 leaderelection.go:429] Failed to update lock optimitically:
  Put "https://10.43.0.1:443/apis/coordination.k8s.io/v1/namespaces/elastic-system/leases/elastic-operator-leader?timeout=3m0s":
  read tcp 10.42.2.218:57322->10.43.0.1:443: read: connection reset by peer,
  falling back to slow path
```

핵심 단어: **`leaderelection.go`** / **`read tcp ... read: connection reset by peer`**.

흐름:
1. K8s controller 표준 패턴 — *leader election lease* 를 유지하면서 reconcile 한다
2. Lease 는 default 15초마다 renewal — kube-apiserver 에 PATCH 요청
3. 르무엘 (control-plane) 의 WiFi 가 *간헐 끊김* — TCP connection reset 발생
4. Lease 갱신 실패 → operator 는 *나는 더 이상 leader 가 아니다* 라고 판단 → graceful shutdown
5. kubelet 이 *Running 상태로 돌려놓기 위해* StatefulSet pod 재시작
6. 새 operator 가 떠서 leader election 다시 → 8분 후 또 같은 일

→ **lease renewal 의 default 15초 시간이 르무엘 WiFi 의 끊김 윈도우보다 짧다**. 25분 사이클을 8분으로 만드는 주범.

### 1.5 수정

ECK operator chart 는 leader election args 를 values 로 노출 안 함. StatefulSet args 를 직접 patch 해야 함:

```yaml
# cluster-ops/elastic-system/eck-leader-elect-patch.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: eck-leader-elect-patch-v1
  namespace: elastic-system
  annotations:
    argocd.argoproj.io/hook: Sync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  template:
    spec:
      serviceAccountName: eck-leader-elect-patcher
      containers:
        - name: kubectl
          image: bitnami/kubectl:1.31
          command: [sh, -c]
          args:
            - |
              CURRENT=$(kubectl -n elastic-system get sts elastic-operator \
                -o jsonpath='{.spec.template.spec.containers[0].args}')
              if echo "$CURRENT" | grep -q 'leader-election-lease'; then
                echo "이미 패치됨 — 스킵"; exit 0
              fi
              kubectl -n elastic-system patch sts elastic-operator --type=json -p='[{
                "op": "replace",
                "path": "/spec/template/spec/containers/0/args",
                "value": [
                  "manager", "--config=/conf/eck.yaml",
                  "--kube-client-qps=200", "--kube-client-timeout=5m0s",
                  "--leader-election-lease=30s",
                  "--leader-election-renew-deadline=25s",
                  "--leader-election-retry-period=5s"
                ]
              }]'
              kubectl -n elastic-system rollout status sts elastic-operator --timeout=5m
```

**Idempotent** — 이미 패치돼 있으면 skip. **Hook BeforeHookCreation** — ArgoCD 가 매 sync 마다 새로 실행하지만 grep 으로 noop 보장.

그리고 ArgoCD 가 chart-default args 로 되돌리려 하지 않게:

```yaml
# argocd-applications/elk/01-eck-operator.yaml
ignoreDifferences:
  - group: apps
    kind: StatefulSet
    name: elastic-operator
    namespace: elastic-system
    jsonPointers:
      - /spec/template/spec/containers/0/args
```

### 1.6 검증 (적용 후)

```
Lease default 15s → 30s
renewDeadline default 10s → 25s
retryPeriod default 2s → 5s
kube-client-timeout default 3m → 5m
```

WiFi 끊김이 *5초 미만* 이면 lease 안에서 회복. 5~25초 끊김도 retryPeriod 5초 × 5 retry = 25초 안에 회복 시도 → renewDeadline 25초 안에 성공.

→ 8분당 1회 restart → 거의 0 예상.

---

## 2. elk-cluster ArgoCD 무한 OutOfSync — 누가 *.status* 를 patch 하는가

### 2.1 증상

```bash
$ kubectl -n argocd get app elk-cluster
NAME          SYNC STATUS   HEALTH STATUS
elk-cluster   OutOfSync     Progressing
```

5일째 OutOfSync. 클러스터는 멀쩡한데 ArgoCD 는 *뭔가 drift 가 있다* 고 주장.

### 2.2 어디가 drift 인가

```bash
$ kubectl -n argocd get app elk-cluster -o json | jq '.status.resources[] | select(.status=="OutOfSync")'
{
  "group": "logstash.k8s.elastic.co",
  "kind": "Logstash",
  "name": "logs",
  "status": "OutOfSync"
}
```

Logstash CR 이 drift. 그런데 sync result 를 보면:
```json
{
  "kind": "Logstash",
  "message": "logstash.logstash.k8s.elastic.co/logs serverside-applied",
  "status": "Synced"
}
```

→ sync 는 성공. 즉시 그 다음 reconcile 에서 OutOfSync 로 또 바뀜.

### 2.3 원인 — operator 가 *.status* 를 patch

ECK operator 는 Logstash/Elasticsearch/Kibana CR 의 **`.status`** 필드를 *자기가 관리하면서* reconcile 마다 갱신:
```yaml
status:
  observedGeneration: 42
  expectedNodes: 3
  availableNodes: 3
  health: green
  ...
```

ArgoCD 의 desired state 에는 `.status` 가 없으니 차이 발생 → OutOfSync 무한.

### 2.4 수정

ArgoCD Application 에 `ignoreDifferences` — *operator 가 관리하는 필드 무시*:

```yaml
# argocd-applications/elk/02-elk-cluster.yaml
ignoreDifferences:
  - group: logstash.k8s.elastic.co
    kind: Logstash
    jsonPointers:
      - /status
      - /metadata/labels   # operator 가 label 도 추가
  - group: elasticsearch.k8s.elastic.co
    kind: Elasticsearch
    jsonPointers:
      - /status
      - /metadata/labels
      - /spec/nodeSets     # controller-revision-hash 등도 operator 관리
  - group: kibana.k8s.elastic.co
    kind: Kibana
    jsonPointers:
      - /status
      - /metadata/labels
```

→ ArgoCD 는 *내가 신경 쓰는 spec* 만 비교. OutOfSync 해소.

이건 **모든 operator-managed CRD 의 GitOps 표준 패턴**. ECK 외에도 Strimzi(Kafka), Crossplane, Argo Rollouts 등 다 동일.

---

## 3. 자동복구 CronJob — 증상은 정리, 원인은 보존

### 3.1 절충

ECK 같은 *진짜 원인 해결* 가능한 case 는 위처럼 처리.
하지만 node-exporter rnk6q (738회 SIGTERM) 같이 *원인 미상* 인 케이스도 있다 (메모리 24%, eviction 0건). 진짜 원인 찾기 전까지 알람이 매시간 도착하는 게 더 큰 문제 — *알람 신호 대 잡음비* 가 떨어진다.

### 3.2 패턴 — restart count > 200 이고 Ready 인 pod 만 delete

```yaml
# cluster-ops/pod-restart-cleanup.yaml
apiVersion: batch/v1
kind: CronJob
spec:
  schedule: "17 * * * *"   # 매시간 17분
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: pod-restart-cleaner
          containers:
            - name: kubectl
              image: bitnami/kubectl:1.31
              command: [sh, -c]
              args:
                - |
                  kubectl get pods -A -o json | python3 -c "
                  import json, sys
                  THRESHOLD = 200
                  EXCLUDE_NS = {'kube-system'}
                  EXCLUDE_NAME_PREFIX = ('kube-proxy', 'coredns', 'etcd-')
                  data = json.load(sys.stdin)
                  for p in data['items']:
                      ns = p['metadata']['namespace']
                      name = p['metadata']['name']
                      if ns in EXCLUDE_NS and any(name.startswith(pre) for pre in EXCLUDE_NAME_PREFIX):
                          continue
                      max_rc = max((c.get('restartCount', 0) for c in p['status'].get('containerStatuses', [])), default=0)
                      if max_rc > THRESHOLD:
                          ready = all(c.get('ready', False) for c in p['status']['containerStatuses'])
                          if ready:
                              print(f'{ns}/{name}')
                  " | xargs -I{} sh -c 'ns_name="{}"; ns="${ns_name%%/*}"; name="${ns_name##*/}"; kubectl -n "$ns" delete pod "$name" --grace-period=30'
```

### 3.3 핵심 원칙 3가지

1. **Ready 인 것만 delete** — 진짜 깨진 pod 은 그대로 둠 (delete 하면 같은 문제 재발 + 알람만 더 시끄러움)
2. **kube-system 의 핵심 (kube-proxy/coredns/etcd) 은 제외** — 데이터 plane 안전
3. **count reset 효과 외 다른 영향 X** — pod 이 새로 떠서 Running 상태 회복, 알람 잠잠해짐

### 3.4 알람 룰 — 임계 *시간* 으로 노이즈 차단

```yaml
# cluster-ops/pod-restart-alert-rule.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
    - name: pod-restart-loop
      rules:
        - alert: PodRestartingTooOften
          expr: rate(kube_pod_container_status_restarts_total[5m]) > 0.5
          for: 10m   # ← 핵심: 10분 지속돼야 알람 (cleanup 후 자연 해소되면 알람 안 옴)
          labels: { severity: warning, channel: telegram }
        - alert: PodRestartCountVeryHigh
          expr: max by (namespace, pod) (kube_pod_container_status_restarts_total) > 1000
          for: 30m   # cleanup 으로 1시간마다 reset 되므로 정상이면 < 200
          labels: { severity: critical }
```

**`for: 10m`** 가 진짜 가치. 5분짜리 spike 는 알람 안 옴 (cleanup 후 회복). 30분 이상 1000회 누적이면 *cleanup 무용* = 진짜 사고.

---

## 4. OpenTelemetry traces — 같이 끝낸 두 번째 영역

ECK 디버깅과 별개로, 같은 날 *traces 0* 문제도 해결했다. 로그·메트릭은 있는데 traces 가 없어서 *어디서 느린지* 추적이 안 됐다.

### 4.1 무엇이 부족했나

```
classify 600ms 평균 — 그 안에서:
  ㄴ Spring controller : 5ms?
  ㄴ AI 사이드카 HTTP  : 580ms?
  ㄴ Postgres INSERT   : 15ms?
```

답을 모름. 로그를 grep 해도 끽해야 *총 wall time* 만 보임. p99 spike 의 원인을 *trace 한 줄* 로 보고 싶었다.

### 4.2 Spring backend — Micrometer Tracing + OTLP

```kotlin
// build.gradle.kts
implementation("io.micrometer:micrometer-tracing-bridge-otel")
implementation("io.opentelemetry:opentelemetry-exporter-otlp")
```

```yaml
# application.yml
management:
  tracing:
    sampling.probability: ${TRACING_SAMPLING:0.1}   # prod 10%, dev 1.0
    propagation.type: w3c                            # traceparent header
  otlp:
    tracing:
      endpoint: ${OTLP_ENDPOINT:http://tempo.monitoring.svc:4318/v1/traces}
      compression: gzip
      timeout: 10s
```

Spring Boot 3.2+ 의 Micrometer Tracing 은 *@WebClient / RestClient / JPA / @Async* 자동 instrumentation. 추가 코드 0줄.

### 4.3 *진짜 가치* — log↔trace correlation

```yaml
# application.yml
logging:
  pattern:
    console: "%d{...} [%thread] [%X{traceId:-}/%X{spanId:-}] %-5level %logger{36} - %msg%n"
```

`%X{traceId}` 가 Micrometer Tracing MDC. 매 로그 줄에 `[a3f0.../e8c2...]` 가 박힘.

→ Grafana 에서:
1. ELK 에서 *오늘 5xx 어디서?* 찾아 → 해당 로그 줄의 traceId 추출
2. Tempo datasource 클릭 → 같은 traceId 의 *모든 span* 그래프로
3. 어느 span 이 580ms 잡아먹었는지 즉시 보임

이 *log → trace jump* 가 OTel 도입의 가장 큰 ROI. 메트릭만 보면 *전체 latency p99 가 1.8s* 인데 *왜* 인지 모름. trace 한 번 보면 즉시 답.

### 4.4 Python AI 사이드카 — 같은 trace_id 로 잇기

```python
# ai/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup(app):
    resource = Resource.create({
        "service.name": "lemuel-xr-ai",
        "service.version": "0.1.0"
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=OTLP_ENDPOINT, timeout=10)
    ))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
```

W3C `traceparent` 헤더가 Spring → Python 으로 전달돼서 *같은 trace_id* 로 span 이 이어진다.

### 4.5 Tempo Helm Application

```yaml
# argocd-applications/tempo.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: tempo }
spec:
  source:
    repoURL: https://grafana.github.io/helm-charts
    chart: tempo
    targetRevision: 1.18.2
    helm:
      values: |
        tempo:
          receivers:
            otlp:
              protocols:
                http: { endpoint: 0.0.0.0:4318 }
                grpc: { endpoint: 0.0.0.0:4317 }
          storage:
            trace:
              backend: local
              local: { path: /var/tempo/traces }
        persistence: { enabled: true, size: 10Gi, storageClassName: local-path }
        nodeSelector: { monitoring: "true" }
```

홈랩 single-binary mode. PVC 10Gi, retention 24h. 사용자 1k 이하면 충분. distributed 모드 (ingester/distributor/querier 분리) 는 1만+ 일 때 검토.

### 4.6 풀체인

```
Unity (XR client)
    │ X-Trace-ID 자동 생성
    ▼
Spring backend (자동 instrumented)
    ├ DB span (Postgres)
    ├ HTTP span → AI 사이드카
    │   ├ FastAPI 자동 span
    │   ├ HTTPX → OpenAI/Anthropic/Gemini
    │   └ (같은 trace_id)
    └ HTTP span → TTS 사이드카
    │
    │ BatchSpanProcessor → OTLP gzip
    ▼
Tempo (monitoring ns, david 노드)
    │ local PVC
    ▼
Grafana (Tempo datasource)
    └─ traceID 검색 → 모든 span flame graph
```

---

## 5. 같은 날 한꺼번에 끝낸 이유 — 인프라 투자의 복리

오늘 *ECK 디버깅* 과 *OTel 도입* 이 같이 끝난 건 우연이 아니다. 두 작업의 공통점:

| 영역 | 어디서 도움? |
|---|---|
| ArgoCD GitOps | 두 작업 모두 git push 만으로 자동 배포. helm chart + Application yaml |
| SOPS-operator | (이번엔 안 썼지만) 새 secret 추가가 5분 |
| kube-prometheus-stack | PrometheusRule 추가가 ConfigMap 같은 단순한 작업 |
| 일관된 컨벤션 | `argocd-applications/`, `cluster-ops/`, `helm-deploy/charts/` 의 분담이 굳어진 상태 |
| 사용 가능한 패턴 (이전 글에서 정착) | App-of-Apps, `ignoreDifferences`, Hook BeforeHookCreation 등 |

만약 이게 *첫 ArgoCD 도입 하루* 였다면 ECK 디버깅 + Tempo 도입은 1주는 걸렸을 것. *인프라 자산이 복리로 쌓이면 한 시간이 모이는 일이 한 사건이 된다*.

---

## 6. 다음 검증 — 24시간 후

```bash
# 1) ECK operator restart count 안정화
kubectl -n elastic-system get pod elastic-operator-0 \
  -o jsonpath='{.status.containerStatuses[0].restartCount}'
# 목표: 24h 안에 +5 미만 (현재 8분당 1회 = 24h +180회)

# 2) ArgoCD elk-cluster Synced
kubectl -n argocd get app elk-cluster
# 목표: SYNC STATUS = Synced

# 3) Tempo traces 수신
kubectl -n monitoring exec deploy/tempo -- wget -qO- http://localhost:3200/api/echo
# Grafana Tempo datasource 추가 후 traceID 검색

# 4) AlertManager 알람 도달 빈도
# 어제: 매시간 6~7 알람 (operator restart)
# 목표: 24h 동안 < 5
```

내일 결과 보고 *진짜 leader election lease 가 답이었는지* / *Tempo 가 운영 데이터 패턴 보여주는지* 회고 글로 후속.

---

## 참고

- [Spring Boot 4 위에 lemuel-xr 백엔드 구축]({% post_url 2026-05-21-spring-boot-4-migration-multi-provider-ai-sops-secrets %}) — 오늘 같은 날 끝낸 12 작업의 다른 한 축
- [K3s 홈랩 하루치 운영기 — Logstash·etcd·ECK]({% post_url 2026-05-17-elk-modernization-etcd-stability-eck-crashloop-deepdive %}) — 이번 ECK 디버깅의 토대
- [GitOps 전문가의 시야 — 36개 Application 운영]({% post_url 2026-05-19-gitops-expert-7-patterns-and-pitfalls %}) — `ignoreDifferences` / App-of-Apps / Hook 패턴이 모두 다뤄짐
- [Kubernetes leader election](https://kubernetes.io/docs/concepts/architecture/leases/) — 공식 lease 메커니즘
- [Grafana Tempo](https://grafana.com/docs/tempo/) / [Micrometer Tracing](https://docs.micrometer.io/tracing/reference/)
