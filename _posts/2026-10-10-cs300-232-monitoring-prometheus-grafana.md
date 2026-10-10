---
layout: post
title: "[CS300 #232] 모니터링 — Prometheus 와 Grafana, 숫자로 시스템을 읽는 법"
date: 2026-10-10 21:52:00 +0900
categories: [cs]
tags: [cs300, devops, prometheus, grafana, monitoring]
---

컴퓨터공학 300 주제 시리즈의 232번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

Prometheus 는 대상의 `/metrics` 를 주기적으로 긁어(pull) 레이블이 붙은 시계열로 저장하고 PromQL 로 질의·경보하는 시스템이며, Grafana 는 그 결과를 대시보드로 보여 주는 시각화 도구다.

## 왜 필요한가

로그는 "무슨 일이 있었나"를 자세히 말해 주지만, "지금 시스템이 건강한가"를 한눈에 말해 주지는 않는다. 초당 요청 수, 에러 비율, 응답 시간의 99번째 백분위수, 디스크 사용률 같은 **숫자의 추이**가 필요하다. 이 숫자들이 있어야 경보를 만들고, 용량을 계획하고, 배포 전후를 비교하고, SLO 를 계산할 수 있다(235번 주제).

## 핵심 개념

### 아키텍처

```
  [앱 /metrics] [node_exporter] [kube-state-metrics]
         ^             ^                 ^
         |   주기적 HTTP GET (scrape)     |
         +-------------+-----------------+
                       |
                 [Prometheus 서버] --규칙 평가--> [Alertmanager] -> 메일·메신저
                  (TSDB 저장, PromQL)                (묶기·억제·라우팅)
                       ^
                       | PromQL 질의
                  [Grafana 대시보드]
```

- **pull 모델**: Prometheus 가 대상에게 가서 가져온다. 대상이 응답하지 않으면 그 자체가 신호다(`up == 0`).
- **서비스 디스커버리**: 쿠버네티스 API 등에서 대상 목록을 자동으로 얻는다. 파드가 늘고 줄어도 설정을 고칠 필요가 없다.
- **exporter**: 자체적으로 메트릭을 내지 않는 시스템(리눅스 노드, DB 등)의 상태를 Prometheus 형식으로 바꿔 주는 프로그램.
- **Pushgateway**: 너무 짧게 살아서 긁을 수 없는 배치 잡이 결과를 밀어 넣는 중계소. 일반 서비스에는 쓰지 않는다.

### 데이터 모델

모든 시계열은 **메트릭 이름 + 레이블 집합**으로 식별된다.

```
http_requests_total{method="GET", path="/api/orders", status="200"}  1027
```

레이블 조합 하나하나가 별도 시계열이다. 그래서 사용자 ID, 요청 ID 처럼 값의 종류가 무한한 것을 레이블로 넣으면 시계열이 폭발한다(높은 카디널리티). 메모리와 디스크가 금방 바닥난다. 레이블은 값의 종류가 유한한 것만 쓴다.

### 메트릭 타입

| 타입 | 성질 | 예 |
|---|---|---|
| Counter | 단조 증가, 재시작 시 0으로 리셋 | 요청 수, 에러 수, 처리 바이트 |
| Gauge | 오르내림 | 메모리 사용량, 큐 길이, 온도 |
| Histogram | 관측값을 구간(bucket)별로 셈 + 합계·개수 | 응답 시간, 요청 크기 |
| Summary | 클라이언트에서 분위수를 계산 | 응답 시간(집계 불가) |

명명 관례도 있다. 카운터는 `_total` 로 끝내고, 단위는 기본 단위(초, 바이트)로 이름에 넣는다. 예: `http_request_duration_seconds`.

### PromQL 기초

```promql
# 최근 5분 동안의 초당 요청 수(카운터에는 항상 rate)
rate(http_requests_total[5m])

# 서비스별 에러 비율
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
  /
sum by (service) (rate(http_requests_total[5m]))

# 히스토그램에서 p99 응답 시간
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# 사용 가능한 메모리 비율이 10% 미만인 노드
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.1
```

카운터의 원시값은 의미가 거의 없다. 1027 이라는 숫자는 프로세스가 언제 시작했는지에 달렸다. `rate()` 는 구간 안의 증가율을 계산하면서 **카운터 리셋을 자동 보정**한다.

Histogram 과 Summary 의 차이는 집계 가능성이다. 히스토그램은 버킷 카운터라서 여러 파드의 값을 `sum` 한 뒤 분위수를 계산할 수 있다. Summary 의 분위수는 파드마다 계산된 값이라 평균을 내도 전체의 분위수가 되지 않는다.

### 경보 규칙

{% raw %}
```yaml
groups:
  - name: api
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m])) > 0.05
        for: 10m
        labels:
          severity: page
        annotations:
          summary: "API 5xx 비율 {{ $value | humanizePercentage }}"
```
{% endraw %}

`for: 10m` 은 조건이 10분 연속 참이어야 발화한다는 뜻이다. 순간 튀는 값으로 사람을 깨우지 않기 위해서다. 발화된 경보는 Alertmanager 로 가서 비슷한 것끼리 묶이고, 상위 경보가 있으면 하위 경보는 억제되고, 심각도에 따라 다른 채널로 간다.

### 무엇을 잴 것인가

출발점으로 쓰기 좋은 틀이 두 가지 있다.

- **요청 처리 서비스**: Rate(초당 요청), Errors(실패 비율), Duration(응답 시간 분포). 앞 글자를 따 RED 라고 부른다.
- **자원**: Utilization(사용률), Saturation(포화, 대기열), Errors. USE 라고 부른다.

Google SRE 책은 지연·트래픽·에러·포화를 "네 가지 황금 신호"로 제시한다.

### Grafana

Grafana 는 Prometheus 를 비롯한 여러 데이터 소스를 질의해 패널로 그린다. 대시보드는 JSON 으로 내보낼 수 있어 Git 으로 관리하기 좋다. 변수(템플릿 변수)를 쓰면 네임스페이스·서비스를 드롭다운으로 바꿔 가며 같은 대시보드를 재사용한다.

## 직접 해 보기

`rate()` 의 카운터 리셋 보정과 `histogram_quantile()` 의 선형 보간을 직접 구현해 보자. 실제 Prometheus 의 `rate` 는 구간 경계로의 외삽까지 하지만, 핵심은 아래와 같다.

```python
def simple_rate(samples):
    """samples: [(t_seconds, counter_value), ...] -> 초당 증가율(리셋 보정)"""
    increase = 0.0
    for (t0, v0), (t1, v1) in zip(samples, samples[1:]):
        increase += v1 - v0 if v1 >= v0 else v1   # 줄었으면 리셋: 새 값 전체가 증가분
    return increase / (samples[-1][0] - samples[0][0])

# 15초 간격 수집, 중간에 프로세스 재시작(1300 -> 40)
samples = [(0, 1000), (15, 1100), (30, 1200), (45, 1300), (60, 40), (75, 140)]
print(f"rate = {simple_rate(samples):.2f} req/s")

def histogram_quantile(q, buckets):
    """buckets: [(upper_bound_le, cumulative_count), ...], 마지막은 +Inf"""
    total = buckets[-1][1]
    rank = q * total
    prev_le, prev_c = 0.0, 0
    for le, c in buckets:
        if c >= rank:
            if le == float("inf"):
                return prev_le        # +Inf 버킷이면 직전 경계를 반환
            return prev_le + (le - prev_le) * (rank - prev_c) / (c - prev_c)
        prev_le, prev_c = le, c

# 5분간 응답 시간 버킷(누적 개수)
b = [(0.05, 600), (0.1, 850), (0.25, 960), (0.5, 990), (1.0, 998), (float("inf"), 1000)]
for q in (0.5, 0.9, 0.99, 0.995):
    print(f"p{q * 100:g} ~= {histogram_quantile(q, b) * 1000:.0f} ms")
```

결과는 다음과 같다.

```
rate = 5.87 req/s
p50 ~= 42 ms
p90 ~= 168 ms
p99 ~= 500 ms
p99.5 ~= 812 ms
```

구간 동안의 실제 증가분은 100+100+100+40+100 = 440 이고, 75초로 나누면 5.87 이다. 리셋을 보정하지 않고 끝값에서 첫값을 빼면 `(140 - 1000) / 75` 로 음수가 나온다. 그리고 p99.5 의 812ms 는 실제 측정값이 아니라 0.5~1.0초 버킷 안에서 선형으로 **추정**한 값이다. 그 버킷에 든 요청 8개가 실제로 몇 ms 였는지는 알 수 없다. 버킷 경계를 SLO 기준값(예: 300ms) 근처에 촘촘히 두어야 정확도가 올라간다.

## 현업에서는

- **카디널리티 사고.** 누군가 URL 전체(쿼리 문자열 포함)나 사용자 ID 를 레이블로 넣으면 시계열 수가 급증해 Prometheus 가 메모리 부족으로 죽는다. `prometheus_tsdb_head_series` 를 감시하고, 경로는 라우트 템플릿(`/orders/:id`)으로 정규화한다.
- **경보 피로.** CPU 80% 같은 원인 기반 경보를 잔뜩 걸면 아무도 경보를 보지 않게 된다. 사람을 깨우는 경보는 사용자가 느끼는 증상(에러율, 지연)에 걸고, 원인 지표는 대시보드에서 진단용으로 쓴다.
- **쿠버네티스 스택.** 클러스터에서는 Prometheus Operator 가 포함된 헬름 차트(kube-prometheus-stack 등)로 Prometheus, Alertmanager, Grafana, node_exporter, kube-state-metrics 를 한 번에 설치하는 경우가 많다. 대상은 `ServiceMonitor`·`PodMonitor` 커스텀 리소스로 선언한다.
- **재시작 경보를 읽는 법.** 여러 파드가 같은 시각에 재시작했다면 파드별 원인보다 그 시각의 공통 원인(노드 압박, API 서버 블립)을 먼저 찾는다. 같은 대시보드에 컨트롤 플레인 지표를 함께 두면 상관관계가 바로 보인다.
- **보존 기간.** Prometheus 로컬 저장소는 장기 보존용이 아니다. 몇 주 이상 보관하려면 원격 저장(remote write)으로 Thanos, Mimir 같은 장기 저장소에 보낸다.

## 확인 문제

1. Prometheus 가 pull 모델을 쓸 때 얻는 장점 하나는?
2. 카운터 원시값 대신 `rate()` 를 써야 하는 이유 두 가지는?
3. 응답 시간을 Summary 가 아니라 Histogram 으로 수집해야 하는 상황은?
4. 레이블에 사용자 ID 를 넣으면 생기는 문제는?
5. 경보 규칙의 `for: 10m` 은 무엇을 뜻하며 왜 쓰는가?

### 풀이

1. 대상이 응답하지 않는 것 자체를 감지할 수 있다(`up == 0`). 대상 목록을 서버가 통제한다.
2. 원시값은 프로세스 시작 시점에 좌우되어 의미가 없고, 재시작 시 리셋되기 때문이다. `rate()` 는 증가율을 주고 리셋을 보정한다.
3. 여러 인스턴스의 분포를 합쳐 전체 분위수를 계산해야 할 때. Summary 분위수는 집계할 수 없다.
4. 시계열 수가 사용자 수만큼 늘어나는 카디널리티 폭발로 메모리·디스크가 고갈된다.
5. 조건이 10분 연속 참일 때만 발화한다. 일시적 튐으로 인한 오경보를 줄인다.

## 더 읽을거리 (References)

- Prometheus Docs, [Overview](https://prometheus.io/docs/introduction/overview/)
- Prometheus Docs, [Metric types](https://prometheus.io/docs/concepts/metric_types/)
- Prometheus Docs, [Querying basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- Google SRE Book, [Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) (Ch. 6)
