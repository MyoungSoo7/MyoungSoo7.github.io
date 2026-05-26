---
layout: post
title: "Grafana 사용법 — *메트릭·트레이스·로그* 를 한 화면에서 가로지르는 방법 (4 datasource 통합 구성 + Explore + Alerting 실전)"
date: 2026-05-27 04:55:00 +0900
categories: [observability, grafana, infra]
tags: [grafana, prometheus, tempo, elasticsearch, alertmanager, observability, explore, k3s]
---

Grafana 를 *''대시보드 보는 곳''* 으로만 쓴다면 절반밖에 못 쓴 거다. 진짜 가치는 *Explore* 에 있다. 메트릭에서 이상 신호를 보고, *클릭 한 번* 으로 그 시점의 트레이스를 보고, *또 한 번* 으로 그 트레이스의 로그를 보는 흐름이 *5초 안에* 끝나야 한다. 이 글은 *그 흐름을 어떻게 구성하고 어떻게 활용하는가* 를, 실제 K3s 홈랩 + Spring Boot 4 워크로드 위에서 정리한 글이다.

---

## TL;DR

| 데이터 종류 | 도구 | Grafana 안에서 | 비결 |
|---|---|---|---|
| 메트릭 | Prometheus | Explore → Prometheus | promQL 쿼리 |
| 알람 | Alertmanager | Alerting 탭 | PrometheusRule + Slack/Telegram 라우팅 |
| 트레이스 | Tempo | Explore → Tempo | traceID 또는 service name |
| 로그 | Elasticsearch | Explore → Elasticsearch | Lucene 쿼리 |

**핵심 통합** — 4 개 datasource 를 *하나의 Grafana* 에 등록하면 *''trace 에서 로그로 1-click''*, *''alert 에서 metric panel 로 1-click''* 같은 *''가로지르기''* 가 가능해진다.

---

## 1. 첫 진입 — *4 데이터소스 한 번에 확인*

Grafana 에 로그인한 후 좌측 메뉴 **Connections** → **Data sources** 클릭. 정상 구성이면 4 개가 보인다:

```
✔ Prometheus       — 기본 (메트릭)
✔ Alertmanager     — 알람 라우팅
✔ Tempo            — 분산 트레이스 (uid=tempo)
✔ Elasticsearch    — 로그 (uid=elasticsearch)
```

각 항목 우측의 **Save & test** 버튼을 클릭하면 *연결 OK* 인지 즉시 확인 가능. *401 / connection refused* 가 뜨면 *비밀번호 secret 누락* 또는 *namespace 경계* 문제가 거의 다임.

> *팁*: ECK Elasticsearch 의 *self-signed cert* 때문에 ES datasource 는 `tlsSkipVerify: true` 필수. 그렇지 않으면 *certificate validation* 으로 막힘.

---

## 2. *Explore* — Grafana 의 *진짜 심장*

좌측의 **나침반 아이콘 (Explore)** 이 *''한 번도 안 눌러본 사람''* 이 보통 60% 다. 여기가 *원래 핵심*.

### 2.1 *메트릭 → 트레이스 → 로그* 의 한 줄 시연

#### Step 1 — Prometheus 로 *최근 5xx 증가* 잡기

상단 데이터소스 *Prometheus* 선택. 쿼리 입력:

```promql
sum by (uri) (rate(http_server_requests_seconds_count{status=~"5.."}[1m]))
```

→ 특정 endpoint 의 5xx 가 *지금* 증가 중인 그래프가 보임.

#### Step 2 — *그 시간의 trace* 보기

같은 시간대 막대에서 *''Show in Tempo''* 버튼이 보이면 클릭 (Grafana 가 *promQL 결과의 시간 범위 + label* 을 자동으로 Tempo 쿼리로 변환). 또는 *Split view* (오른쪽 위 아이콘) 로 패널을 분할하고 datasource 를 *Tempo* 로 바꾼 후, 같은 시간 범위에서 *''Search''* 탭:

```
Service Name: lemuel-xr-backend
Tags: error=true   (또는 http.status_code=500)
Min duration: 100ms
```

→ 그 시간대의 *느린/실패 trace 목록* 이 옴.

#### Step 3 — *그 trace 의 로그* 보기

trace 하나 클릭해서 열면 *Span Details* 옆에 **Logs** 버튼이 있다 (Tempo datasource 설정의 `tracesToLogsV2.datasourceUid: elasticsearch` 가 만들어준 기능). 클릭하면 자동으로 *Elasticsearch 탭으로 이동 + traceID 로 필터된 로그* 가 옴.

→ 5초 안에 *''5xx 가 뭐고''* → *''어떤 trace 였고''* → *''뭐가 찍혀있었는지''* 가 다 보인다.

> *이게 안 되는 환경* 에선 5xx 알람이 떴을 때 *Kibana 따로 열고 + Jaeger 따로 열고 + Grafana 따로 보면서* 5 분 동안 cross-reference 하는 것과 다를 게 없다. *통합* 의 가치가 *시간 ÷ 6* 정도.

### 2.2 *Prometheus 쿼리* 자주 쓰는 것

```promql
# 1. CPU 사용률 노드별
100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)

# 2. 메모리 사용률
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 3. Pod restart count (지난 1 시간)
increase(kube_pod_container_status_restarts_total[1h])

# 4. K8s scheduling fail (Pending pod)
sum by (namespace) (kube_pod_status_phase{phase="Pending"})

# 5. http p95 latency by uri (Spring Boot)
histogram_quantile(0.95, sum by (le, uri) (rate(http_server_requests_seconds_bucket[5m])))

# 6. JVM heap usage
(jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}) * 100
```

좋은 쿼리 하나가 *대시보드 1 개의 가치* 다.

### 2.3 *Elasticsearch 쿼리* 자주 쓰는 것

```
# 최근 ERROR 로그
level:error

# 특정 trace
trace.id:b0f3a51c8d4e2

# 특정 user
labels.user_id:42 AND level:error

# 정규식
message:/timeout.*postgres/

# 시간 범위는 우상단 시간 선택기로
```

> *함정*: `@timestamp` 가 *시간 필드* 로 인식되려면 datasource 의 `jsonData.timeField: '@timestamp'` 설정 필수. 누락 시 *모든 로그가 ''No data''* 로 보이는 버그.

---

## 3. *Dashboard* — *''저장된 Explore''* 라고 생각하기

Explore 에서 만든 좋은 쿼리는 *Dashboard 패널* 로 박아둔다. 두 가지 방식:

### 3.1 *수동 빌드* — 한 패널씩 추가

1. 좌측 *Dashboards* → *New* → *Add visualization*
2. Datasource 고르고 쿼리 입력
3. *Panel options* 에서 제목, *Visualization* 에서 차트 종류 (timeseries / stat / gauge / bar / table)
4. *Save dashboard* — JSON 으로 저장됨

### 3.2 *GitOps 방식* — *Helm chart 의 ConfigMap 으로*

운영 환경에선 *클릭 빌드* 가 *재현 불가능한 운영 아티팩트* 가 된다. 더 좋은 방식은 *dashboard JSON 을 git 에* 두는 것.

```yaml
# helm-deploy/charts/lemuel-xr/templates/grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lemuel-xr-backend-grafana-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"   # ← kube-prometheus-stack 의 sidecar 가 이 라벨 보고 자동 import
data:
  lemuel-xr.json: |-
    {{ .Files.Get "dashboards/lemuel-xr.json" | nindent 4 }}
```

`grafana_dashboard: "1"` 라벨이 핵심. kube-prometheus-stack 의 *sidecar 컨테이너* 가 *모든 namespace 의 이 라벨* configmap 을 watch 해서 *자동으로 Grafana 에 import*. 변경 → git push → ArgoCD → ConfigMap 갱신 → sidecar 가 5 분 안에 반영. 완전 자동.

> *Senior 시그널*: dashboard 도 *git-managed* 한다는 답변. *''운영용 대시보드는 클릭으로 만들지 않습니다''* 라고 한 줄 추가하면 점수.

---

## 4. *Alerting* — *''언제 신호인가''*

좌측 *Alerting* → *Alert rules*. 두 가지 출처:

1. **Prometheus rules** — PrometheusRule CR 로 etcd 에 박혀있는 것 (helm-deploy/cluster-ops/pod-restart-alert-rule.yaml 같은). Grafana 가 *읽기 전용* 으로 보여줌.
2. **Grafana-managed alerts** — Grafana UI 안에서 만든 것. 더 유연 (Loki/Tempo/SQL 등 다른 datasource 도 alert 조건으로 가능).

### 4.1 *좋은 알람의 3 가지*

알람을 만들기 *전에* 자문할 것:

1. **이 알람이 울리면 *지금* 나는 뭘 할 건가?** — 답이 *''음 봐야지''* 면 알람 아니라 *dashboard panel*. *''pod 재시작''* 같은 *행동 가능한* 신호여야 진짜 알람.
2. **얼마나 자주 울릴까?** — `for: 5m` 같은 *지속 임계* 가 *''잠시 튄 spike''* 를 걸러줌. 알람의 *signal-to-noise* 를 결정하는 게 `for:`.
3. **누구에게 가나?** — Alertmanager 의 라우팅. 야간엔 Telegram, 평일 9-18 엔 Slack 등.

### 4.2 운영 중인 알람 예 (helm-deploy)

```yaml
# helm-deploy/cluster-ops/pod-restart-alert-rule.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-restart
  namespace: monitoring
spec:
  groups:
    - name: pod-restart
      rules:
        - alert: PodRestartingFast
          expr: |
            increase(kube_pod_container_status_restarts_total[15m]) > 5
          for: 10m
          labels: { severity: critical }
          annotations:
            summary: "Pod {{ "{{ $labels.namespace }}" }}/{{ "{{ $labels.pod }}" }} 가 15 분 안에 5번 이상 재시작"
            runbook: "https://your-internal-wiki/pod-restart"
```

`for: 10m` 이 핵심. *튐* 은 무시, *지속* 만 잡음.

---

## 5. *traceId 가로지르기* — 시니어가 진짜 점수 따는 패턴

좋은 observability 가 *''4 도구가 다 있다''* 가 아니라 *''서로 연결되어 있다''* 인 이유.

### 5.1 Spring Boot 4 + OpenTelemetry 의 자동 traceId

Spring Boot 3.0+ 의 Micrometer Tracing + OpenTelemetry 도입 시 — *application.yml*:

```yaml
management:
  tracing:
    sampling:
      probability: 1.0   # staging: 100%, prod: 0.1 (10%) 권장
  endpoint:
    health:
      probes:
        enabled: true

# 로그 패턴에 traceId 박기
logging:
  pattern:
    level: "%5p [%X{traceId:-}/%X{spanId:-}]"
  level:
    org.springframework: INFO
```

이러면 모든 로그 라인 앞에 `[<traceId>/<spanId>]` 가 박힌다. Fluent-bit → Logstash → Elasticsearch 로 흘러갈 때 *traceId 가 ES 필드* 로 추출되어 *쿼리 가능* 해진다.

### 5.2 Tempo datasource 의 *''Logs 버튼''*

helm-deploy 의 monitoring values 에:

```yaml
- name: Tempo
  type: tempo
  url: http://tempo.monitoring:3100
  jsonData:
    tracesToLogsV2:
      datasourceUid: elasticsearch
      tags: [{ key: "service.name", value: "service" }]
      # 자동으로 ES 쿼리: "{service=...} | traceId=$__trace.traceId"
```

이게 *''Tempo span 에서 Logs 클릭''* 의 결과가 *ES Explore 에 traceId 필터된 채로* 자동 열리게 한다.

### 5.3 반대 방향 — *로그에서 trace 로 점프*

ES datasource 에:

```yaml
- name: Elasticsearch
  type: elasticsearch
  jsonData:
    dataLinks:
      - field: traceId
        url: "/explore?orgId=1&left={\"datasource\":\"tempo\",\"queries\":[{\"refId\":\"A\",\"queryType\":\"traceql\",\"query\":\"${__value.raw}\"}]}"
        urlDisplayLabel: "→ Tempo"
```

로그 라인에서 `traceId` 필드 클릭 → *Tempo 의 그 trace* 로 점프.

---

## 6. *''안 쓰는 게 더 자주 있는''* 패턴 — 정직한 노트

좋은 시니어는 *Grafana 안 쓰는 게 나을 때* 도 안다.

- **단일 메서드의 latency 디버깅** — `jconsole` / `VisualVM` 으로 *''지금 이 한 프로세스''* 보는 게 빠름. Grafana 는 *''장기 추세 + 다중 인스턴스''* 가 강점.
- **테스트 시 단발 query** — `curl` + `jq` 로 raw Prometheus API 두드리는 게 빠를 때 많음.
- **SLO 계산** — *''최근 24h 의 가용성 %''* 같은 건 Grafana 의 *Stat* 패널보다 *raw PromQL + spreadsheet* 가 더 잘 맞음.

도구는 *문제에 맞게* 선택. Grafana 가 *전부* 가 아님.

---

## 7. 운영 중 자주 만나는 함정

### 7.1 *''No data''* 의 5 가지 원인

```
1. datasource 의 URL 이 잘못됨 (cluster-internal DNS 가 다름)
2. label selector 가 안 맞음 (job 이름 변경 후 dashboard 갱신 안 됨)
3. 시간 범위가 *너무 짧음* (5m → 1h 로 늘리면 보임)
4. ES timeField 누락 (앞서 언급)
5. 권한 부족 (datasource 의 basic auth password 만료)
```

### 7.2 *대시보드 사라짐*

Grafana 의 *유저별 dashboard* 는 etcd 안에 있고 — *Grafana persistence 가 꺼져있으면* pod 재시작 시 *기억 잃음*. helm values 에 `persistence.enabled: true` + `size: 5Gi` 같은 PVC 필수. 우리 환경은:

```yaml
grafana:
  persistence:
    enabled: true
    storageClassName: local-path
    size: 5Gi
```

### 7.3 *''alert 안 옴''* 의 원인

```
1. PrometheusRule 의 namespace 가 Prometheus 의 ruleSelector 와 안 맞음
2. for: 가 너무 길어서 *짧은 spike* 를 못 잡음
3. Alertmanager 의 receiver 가 *test 만* 설정되어 있고 실제 channel 미연결
4. silences 로 누군가 묵음 처리해놨음
```

---

## 8. 마무리

*''Grafana 깔았으니 끝''* 이 아니라, *Grafana 안에서 4 종 데이터를 가로지르는 흐름* 을 *깔끔하게 정의해 두는 게* 운영의 8 할이다. 가장 큰 가치 시점:

- **새벽 3 시 알람** — 한 화면에서 *''뭐가 / 언제 / 왜 / 어떻게 보였는지''* 가 *5 클릭 안에* 보임
- **신규 입사자** — *Discover* 라는 추상이 아니라 *''Explore 가서 promQL 치고 Tempo 보고 ES 보면 됨''* 으로 한 번에 전달
- **장애 후 분석** — *trace 1 개* 가 *5 분의 회고록* 을 정확히 보여줌

이게 *integrated observability* 의 *operational payoff* 다. 도구의 *수* 가 아니라 *흐름의 매끄러움* 으로 운영 품질이 결정된다.

---

> 작성: 2026-05-27. 환경: K3s v1.35.4, kube-prometheus-stack 65.5.0 (Grafana 11.4), Tempo 2.6, Elasticsearch 8.16 (ECK), Spring Boot 4 + Micrometer Tracing + OpenTelemetry. 실제 *lemuel-xr* / *settlement* / *asat* 의 cross-cutting 추적 패턴을 그대로 정리.
