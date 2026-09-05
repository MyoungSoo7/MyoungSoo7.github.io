---
layout: post
title: "프로메테우스와 그라파나 사용법: 메트릭을 운영 의사결정으로 바꾸기"
date: 2026-09-05 18:07:24 +0900
categories: [Observability]
tags: [Prometheus, Grafana, PromQL, Kubernetes, Monitoring, SRE]
---

# 프로메테우스와 그라파나 사용법

서비스 운영에서 로그는 “무슨 일이 있었는가”를 보여주고, 메트릭은 “얼마나 자주·얼마나 오래·어느 정도로 발생하는가”를 보여준다. Prometheus는 시계열 메트릭을 수집·저장·질의하고 알림 규칙을 실행하는 모니터링 도구이며, Grafana는 여러 데이터 소스를 조회해 대시보드와 시각화를 만드는 화면 계층이다.[1][4]

둘은 자주 함께 사용되지만 같은 제품은 아니다.

- **Prometheus**: 메트릭 수집, 시계열 저장, PromQL 질의, recording rule과 alert rule
- **Grafana**: 데이터 소스 연결, PromQL 편집, 패널·대시보드·변환·공유
- **Alertmanager**: Prometheus 알림을 그룹화하고 라우팅·억제·전달
- **Exporter**: 애플리케이션이나 OS의 상태를 Prometheus 형식으로 노출

## 1. 전체 구조

```text
애플리케이션 / Kubernetes / 노드 / DB
              │
              ▼
       /metrics endpoint
              │
              ▼
         Prometheus
   scrape → TSDB 저장 → PromQL
        ┌─────┴─────┐
        ▼           ▼
  Alert rules    Grafana
        │       Dashboard
        ▼           │
  Alertmanager     운영자
```

Prometheus는 대상의 HTTP metrics endpoint를 주기적으로 조회하는 pull 모델을 기본으로 한다. 서비스 디스커버리나 정적 설정으로 대상을 찾고, 수집한 샘플을 로컬에 저장하며, 규칙으로 집계 시계열이나 알림을 생성한다.[1]

Grafana는 Prometheus를 데이터 소스로 등록한 뒤 PromQL 결과를 패널로 표시한다. Grafana 패널은 데이터 소스 플러그인, 쿼리, 필요할 경우 변환을 거쳐 시각화된다.[5]

## 2. 무엇을 측정해야 하는가

### 애플리케이션 메트릭

- 초당 요청 수
- HTTP 4xx·5xx 오류율
- p50·p95·p99 응답시간
- 요청 처리 중인 작업 수
- 큐 길이와 처리 지연
- 외부 API timeout·실패 수

### 인프라 메트릭

- CPU·메모리·디스크 사용량
- 네트워크 송수신량
- 파일 디스크립터
- 노드 상태
- 컨테이너 재시작 횟수

### Kubernetes 메트릭

- 파드 Ready 상태
- Deployment desired/available replica
- 컨테이너 재시작
- CPU·메모리 requests/limits 대비 사용량
- Pending 파드와 스케줄링 실패
- API 서버·컨트롤러·노드 상태

메트릭 이름만 많이 만드는 것이 좋은 관측은 아니다. 운영자가 실제로 답해야 하는 질문—“오류율이 증가했는가?”, “어느 서비스인가?”, “사용자 영향이 있는가?”—에서 역산해 설계해야 한다.

## 3. Prometheus 설치 후 가장 먼저 확인할 것

Prometheus 설정은 명령줄 플래그와 YAML 설정 파일로 구성된다. 설정 파일에는 scrape job, 대상 인스턴스, rule 파일 등이 들어가며, 설정을 다시 읽어 런타임에 reload할 수도 있다.[3]

간단한 예시는 다음과 같다.

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: shop-api
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["shop-api:8080"]
        labels:
          environment: production
          team: commerce
```

실제 적용 전에는 설정 문법을 검증한다.

```bash
promtool check config prometheus.yml
promtool check rules rules/*.yml
```

설정이 정상이라도 target이 실제로 수집되는지는 별도로 확인해야 한다. Prometheus UI의 **Status → Targets**에서 `UP` 여부, 마지막 scrape 시각, 오류 메시지를 확인한다. 설정 성공과 업무 데이터 수집 성공은 같은 의미가 아니다.

## 4. 메트릭을 애플리케이션에 추가하기

애플리케이션은 Prometheus client library 또는 프레임워크 integration으로 `/metrics` endpoint를 노출한다. HTTP 서버라면 최소한 요청 수와 응답시간을 측정하는 것이 좋다.

개념적인 메트릭 예시는 다음과 같다.

```text
http_requests_total{
  service="shop-api",
  method="GET",
  route="/orders",
  status="200"
} 18420

http_request_duration_seconds_bucket{
  service="shop-api",
  route="/orders",
  le="0.5"
} 17300
```

카운터에는 보통 `_total`, 시간 분포에는 histogram의 `_bucket`, `_sum`, `_count`가 사용된다. 레이블은 검색과 집계를 가능하게 하지만, 사용자 ID·요청 ID·무제한 URL 같은 고카디널리티 값을 넣으면 시계열 수가 폭증할 수 있다.

좋은 레이블:

- `service`
- `environment`
- `method`
- 제한된 `route`
- 제한된 `status`

주의할 레이블:

- `user_id`
- UUID 기반 `request_id`
- 원본 query string
- 무제한 상품명·파일명

## 5. PromQL 기초

PromQL은 Prometheus의 시계열 선택·집계 언어다. instant query는 특정 시점의 결과를, range query는 시간 범위의 결과를 반환한다.[2]

### 현재 메트릭 조회

```promql
up
```

```promql
up{job="shop-api", environment="production"}
```

### 요청량

```promql
sum(rate(http_requests_total[5m])) by (service)
```

`rate()`는 counter가 최근 5분 동안 초당 얼마나 증가했는지 계산한다. Counter의 원시 값 자체보다 `rate()`나 `increase()`를 사용해야 시간에 따른 요청량을 해석하기 쉽다.

### 오류율

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
```

서비스별 오류율은 다음과 같이 계산할 수 있다.

```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/
sum(rate(http_requests_total[5m])) by (service)
```

### p95 응답시간

Histogram을 사용한다면 다음과 같이 계산한다.

```promql
histogram_quantile(
  0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)
```

### 메모리와 CPU

```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

```promql
sum(rate(container_cpu_usage_seconds_total[5m])) by (pod)
```

쿼리의 결과를 그대로 운영 판단으로 사용하기 전에 단위, 라벨 범위, 시간 창, scrape 누락 여부를 확인해야 한다.

## 6. Recording rule로 자주 쓰는 계산을 저장하기

복잡한 쿼리를 모든 대시보드에서 반복 실행하면 비용과 응답시간이 커질 수 있다. Recording rule은 자주 사용하는 계산 결과를 새 시계열로 미리 기록한다.

```yaml
groups:
  - name: shop-recording-rules
    interval: 30s
    rules:
      - record: service:http_requests_per_second:rate5m
        expr: sum(rate(http_requests_total[5m])) by (service)

      - record: service:http_5xx_ratio:rate5m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
          /
          sum(rate(http_requests_total[5m])) by (service)
```

Recording rule은 대시보드 쿼리를 단순화하고, 동일한 계산을 여러 소비자가 사용할 때 유용하다. 단, 규칙 이름과 의미를 문서화하고 원본 메트릭과 단위가 무엇인지 함께 관리해야 한다.

## 7. Alert rule과 Alertmanager

알림은 “메트릭이 임계값을 넘었다”보다 “운영자가 대응해야 하는 상태가 되었다”를 표현해야 한다.

```yaml
groups:
  - name: shop-alerts
    rules:
      - alert: ShopApiHighErrorRate
        expr: service:http_5xx_ratio:rate5m > 0.05
        for: 10m
        labels:
          severity: critical
          team: commerce
        annotations:
          summary: "Shop API 5xx 비율이 높습니다"
          description: "{{ $labels.service }}의 5xx 비율이 10분 이상 5%를 초과했습니다."
```

`for`를 사용하면 순간적인 스파이크를 바로 장애로 오인하는 것을 줄일 수 있다. Alertmanager에서는 팀·서비스·severity 기준으로 알림을 그룹화하고, 중복을 억제하며, Slack·메일·PagerDuty 등으로 라우팅한다.

알림 설계 원칙:

- 증상과 원인을 구분한다.
- 사용자 영향이 없는 경고는 낮은 severity로 분리한다.
- 같은 원인의 알림을 그룹화한다.
- runbook 링크를 annotation에 포함한다.
- 알림이 실제로 전달되는지 테스트한다.
- 업무시간 외에도 대응할 알림인지 합의한다.

## 8. Grafana 사용법

### 8.1 Prometheus를 데이터 소스로 등록

Grafana에서 **Connections → Data sources → Add data source → Prometheus**로 이동해 Prometheus URL을 등록한다. 저장 후 **Save & test**에서 연결 성공을 확인한다. Grafana 공식 문서는 Prometheus를 포함한 여러 데이터 소스를 연결하고 첫 대시보드를 구성하는 흐름을 제공한다.[4]

### 8.2 첫 패널 만들기

1. 새 Dashboard를 만든다.
2. Add visualization을 선택한다.
3. 데이터 소스로 Prometheus를 선택한다.
4. PromQL을 입력한다.
5. 시간 범위와 refresh interval을 설정한다.
6. 단위·범례·threshold를 지정한다.
7. 패널 제목과 설명을 추가한다.
8. 저장하고 권한·공유 범위를 확인한다.

Grafana 대시보드는 패널들의 묶음이다. 각 패널은 쿼리 결과를 시간 그래프, Stat, Gauge, Table, Heatmap 등으로 표현한다. 필요하면 transformation으로 결과 필드를 합치거나 필터링할 수 있다.[5]

### 8.3 운영 대시보드 구성

첫 화면에는 다음 네 가지 질문이 보여야 한다.

- 지금 서비스가 살아 있는가?
- 사용자가 실패를 겪고 있는가?
- 느려지고 있는가?
- 어느 서비스·노드·버전이 문제인가?

추천 패널:

- 전체 요청량
- 성공률과 5xx 비율
- p50/p95/p99 latency
- 활성 파드·Ready 파드 수
- CPU·메모리 사용률
- 재시작 수
- 활성 알림
- 최근 배포 버전

대시보드는 지표를 많이 넣는 화면이 아니라, 장애 발생 시 판단 시간을 줄이는 화면이어야 한다.

## 9. 실전 사용사례

### 사례 1: API 장애

5xx 비율 패널에서 급증이 보이면 서비스별 오류율, endpoint별 latency, 파드 Ready 상태를 drill-down한다. Prometheus는 증상과 규모를 보여주고, 상세 원인은 로그와 trace에서 확인한다. 메트릭만으로 원인을 확정하지 않고 배포 이벤트·로그·트레이스와 시간축을 맞춰야 한다.

### 사례 2: Kubernetes 배포 후 성능 저하

배포 전후의 p95 응답시간, CPU throttling, 메모리 사용량, 재시작 수를 비교한다. 새 이미지 버전 label을 모든 애플리케이션 메트릭에 넣으면 버전별 비교가 가능하다. 다만 이미지 태그가 무제한으로 생성되거나 pod name을 과도하게 집계하면 카디널리티와 쿼리 비용이 커질 수 있다.

### 사례 3: 용량 계획

요청량과 CPU·메모리 사용량의 관계를 시간 범위로 비교해 scale-out 기준을 찾는다. 단순히 CPU 80%라는 하나의 숫자만 보지 말고, latency·error rate·queue depth·replica 수를 함께 봐야 한다.

### 사례 4: SLO와 에러 버짓

가용성 SLI를 성공 요청 비율로 정의하고, 목표 SLO와 실제 값을 비교한다. 예를 들어 5xx 비율, latency threshold 초과율, availability를 recording rule로 만들고 주간·월간 추세를 대시보드화한다. SLO를 만들 때는 측정 가능한 지표, 사용자 영향, 시간 창, 제외 조건을 먼저 문서화해야 한다.

### 사례 5: 데이터 파이프라인과 배치 작업

짧게 실행되는 배치 작업은 일반 scrape만으로 놓칠 수 있다. Prometheus 공식 개요는 이런 경우 Pushgateway 같은 중간 구성요소를 언급하지만, 모든 작업을 무조건 push 방식으로 바꾸기보다 작업의 수명과 운영 모델에 맞춰 선택해야 한다.[1]

## 10. Prometheus와 Grafana의 한계

Prometheus는 숫자 시계열 모니터링에 강하지만, per-request billing처럼 100% 정확한 거래 원장으로 쓰기에는 적합하지 않다. 공식 문서도 정확성이 절대적으로 필요한 경우에는 다른 시스템을 사용하라고 설명한다.[1]

따라서 다음을 분리해야 한다.

- 메트릭: 상태·추세·알림·SLO
- 로그: 상세 이벤트와 오류 메시지
- 트레이스: 요청이 여러 서비스를 거친 경로
- DB·원장: 정산과 정확한 업무 사실

또한 Prometheus 단일 서버의 보존기간, 디스크, 고가용성, 장기 보관 요구가 커지면 remote write·장기 저장소·Thanos·Cortex·Mimir 같은 별도 아키텍처를 검토해야 한다. 실제 선택은 규모·RPO/RTO·비용·운영 역량에 따라 결정한다.

## 11. 도입 순서

1. 핵심 서비스 하나를 선택한다.
2. 요청 수·오류율·응답시간·가용성부터 계측한다.
3. `/metrics` endpoint와 scrape target을 검증한다.
4. PromQL로 장애 질문에 답하는 쿼리를 만든다.
5. Grafana에 네 개의 핵심 패널을 만든다.
6. recording rule로 반복 쿼리를 정리한다.
7. Alertmanager와 runbook을 연결한다.
8. 배포 전후 비교와 SLO 대시보드를 추가한다.
9. label cardinality·보존기간·쿼리 비용을 정기적으로 점검한다.

## 결론

Prometheus와 Grafana의 조합은 “예쁜 그래프”를 만드는 도구가 아니다. Prometheus가 운영 상태를 수치와 시계열로 수집하고, PromQL이 질문을 계산하며, Grafana가 그 결과를 사람이 판단할 수 있는 화면으로 만든다.

가장 좋은 시작점은 다음 세 가지다.

- 사용자가 겪는 실패를 측정한다.
- 장애 때 필요한 질문을 PromQL로 만든다.
- 대시보드와 알림을 실제 runbook과 연결한다.

메트릭·로그·트레이스·업무 원장을 각각의 역할에 맞게 분리하면, 관측 시스템이 단순 모니터링을 넘어 운영 의사결정의 근거가 된다.

## 참고 자료

[1] Prometheus Overview — 기능, pull 모델, 구성요소, 적용 범위  
[2] PromQL Querying Basics — instant/range query와 표현식  
[3] Prometheus Configuration — scrape job과 rule 설정  
[4] Grafana Getting Started — 데이터 소스와 첫 대시보드  
[5] Grafana Dashboards Overview — 데이터 소스·쿼리·변환·패널 구조

## 출처

- Prometheus Overview: https://prometheus.io/docs/introduction/overview/
- PromQL Querying Basics: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Prometheus Configuration: https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- Grafana Getting Started: https://grafana.com/docs/grafana/latest/fundamentals/getting-started/
- Grafana Dashboards Overview: https://grafana.com/docs/grafana/latest/fundamentals/dashboards-overview/

## Sources

[1] https://prometheus.io/docs/introduction/overview — Prometheus Overview
[2] https://prometheus.io/docs/prometheus/latest/querying/basics — PromQL Querying Basics
[3] https://prometheus.io/docs/prometheus/latest/configuration/configuration — Prometheus Configuration
[4] https://grafana.com/docs/grafana/latest/fundamentals/getting-started — Grafana Getting Started
[5] https://grafana.com/docs/grafana/latest/fundamentals/dashboards-overview — Grafana Dashboards Overview
