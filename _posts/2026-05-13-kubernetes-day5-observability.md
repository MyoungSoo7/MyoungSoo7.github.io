---
layout: post
title: "쿠버네티스 5일차 — 모니터링 + 로깅 (Prometheus / Grafana / Loki)"
date: 2026-05-13 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, prometheus, grafana, loki, observability, monitoring]
---

운영하다 보면 깨닫는 진실 하나:

> "장애가 났는지 모르는 게 가장 무섭다."

5일차는 클러스터의 눈과 귀를 다는 시간입니다. **메트릭** (Prometheus) + **시각화** (Grafana) + **로그** (Loki) 3종 세트로 운영의 절반을 자동화합니다.

> 이 글에서 다루는 것
> - **Observability 3 기둥**: metrics / logs / traces
> - **Prometheus**: 메트릭 수집의 표준
> - **Grafana**: 메트릭/로그 시각화
> - **Loki**: 로그 집계 (가벼운 ELK 대안)
> - kube-prometheus-stack 으로 한 번에 깔기

---

## 1. Observability 3 기둥

| 기둥 | 무엇 | 도구 (선택) |
|---|---|---|
| **Metrics** | 시간별 수치 (CPU, 요청수, 에러율) | Prometheus, OpenTelemetry |
| **Logs** | 텍스트 이벤트 (에러 스택, 접근 기록) | Loki, ELK, CloudWatch |
| **Traces** | 한 요청이 거친 경로 (분산 추적) | Tempo, Jaeger, OpenTelemetry |

5일차는 처음 둘 — Metrics + Logs 까지만. Traces 는 마이크로서비스가 정착된 후.

---

## 2. Prometheus — 메트릭 수집의 표준

### Pull 방식

```
[Pod 의 /metrics 엔드포인트]   ← 노출 (앱이 한 줄 노출만 하면 됨)
        ▲
        │ HTTP GET 15s 마다
[Prometheus]   ← scrape
```

각 앱이 `/metrics` 에 자기 상태를 텍스트로 노출하면 Prometheus 가 주기적으로 긁어옵니다. **Push 가 아니라 Pull** 인 점이 중요해요.

### Spring Boot 예시

```kotlin
// build.gradle.kts
implementation("io.micrometer:micrometer-registry-prometheus")
```

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: ["health", "metrics", "prometheus"]
```

이러면 `http://app:8080/actuator/prometheus` 에 메트릭 자동 노출.

### 쿠버네티스에 알려주기 (ServiceMonitor)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata: { name: my-app }
spec:
  selector: { matchLabels: { app: my-app } }
  endpoints:
    - port: http
      path: /actuator/prometheus
      interval: 15s
```

Prometheus Operator 가 이 객체를 보고 자동으로 scrape 설정을 만듭니다.

### PromQL 한 손에

```promql
# 최근 5분 평균 CPU
rate(container_cpu_usage_seconds_total[5m])

# 5xx 에러율
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))

# 메모리 90% 넘는 Pod
container_memory_usage_bytes
  / container_spec_memory_limit_bytes > 0.9
```

---

## 3. Grafana — 메트릭/로그 시각화

대시보드 + 알림. Prometheus / Loki 를 데이터 소스로 등록만 하면 됩니다.

### 추천 대시보드 ID (Grafana.com)

- `15760` — Kubernetes / Views / Global
- `15757` — Kubernetes / Views / Pods
- `15759` — Kubernetes / Views / Nodes
- `12740` — Spring Boot 2.x System Monitor

대시보드 import 한 줄로 끝납니다.

### Alert

```yaml
# 알림 룰 (Prometheus rule)
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m]))
      / sum(rate(http_requests_total[5m])) > 0.05
  for: 5m
  labels: { severity: warning }
  annotations:
    summary: "5xx 에러율 5% 초과 (5분 지속)"
```

Grafana 에서 Slack / Telegram / 이메일로 발송.

---

## 4. Loki — 로그 집계

ELK (Elasticsearch+Logstash+Kibana) 가 강력하지만 무겁습니다. **Loki** 는 "로그를 위한 Prometheus" 컨셉으로 가볍습니다.

### 핵심 차이

| | ELK | Loki |
|---|---|---|
| 인덱스 | 로그 본문 풀 인덱싱 | **레이블만 인덱싱** (본문은 청크 저장) |
| 비용 | 디스크 ↑↑↑ | 디스크 ↓ |
| 검색 속도 | 매우 빠름 | 보통 (대부분 OK) |
| 학습 | Lucene 쿼리 | LogQL (PromQL 닮음) |

### LogQL

```logql
# 특정 앱의 최근 로그
{app="lemuel-jen", namespace="prod"}

# ERROR 만
{app="lemuel-jen"} |= "ERROR"

# 에러 발생 횟수 시계열로
sum by (app) (rate({namespace="prod"} |= "ERROR" [5m]))
```

Grafana 에서 Prometheus 메트릭과 같은 화면에 로그를 띄울 수 있습니다 — 알람 클릭 → 그 시점의 로그 즉시 확인.

---

## 5. 한 번에 깔기 — kube-prometheus-stack

Helm chart 하나로 Prometheus + Grafana + Alertmanager + ServiceMonitor 가 통째로 설치됩니다.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword='S3cret!@#'

# Grafana 접근
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
# http://localhost:3000  (admin / S3cret!@#)
```

Loki 는 별도:

```bash
helm install loki grafana/loki-stack \
  --namespace monitoring --set promtail.enabled=true
```

`promtail` 이 모든 노드에서 Pod 로그를 자동 수집합니다.

---

## 6. 가장 먼저 만들어야 할 4가지 알람

1. **Pod CrashLoopBackOff** — 죽었다 살았다 반복
2. **노드 메모리/디스크 90% 초과** — 곧 터질 신호
3. **5xx 에러율 5% 초과** — 사용자가 느끼기 시작하는 임계
4. **배포 후 30분 내 ErrorRate 급증** — 자동 롤백 트리거 (있으면)

이 4개만 자기 손으로 짜놓아도 새벽에 깨어날 일이 절반은 줄어듭니다.

---

## 핵심 한 줄 정리

- **Observability = metrics + logs + traces** (오늘은 앞 둘만)
- **Prometheus**: Pull 방식 메트릭 수집. ServiceMonitor 로 자동 등록
- **Grafana**: 시각화 + 알람. 추천 대시보드 ID 그대로 import
- **Loki**: 가벼운 로그 집계. 레이블만 인덱싱
- **kube-prometheus-stack** Helm 차트로 한 줄 설치

6일차에서는 **보안** — RBAC / NetworkPolicy / ServiceAccount — 으로 넘어갑니다.

---

> 시리즈 [1일차]({% post_url 2026-05-09-kubernetes-day1-architecture %}) 부터 차근차근 보시면 좋습니다.
