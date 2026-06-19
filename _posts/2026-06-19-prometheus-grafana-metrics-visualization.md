---
layout: post
title: "*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다 — *서버 죽었나?* 5 가지 질문 의 *PromQL + 대시보드*"
date: 2026-06-19 02:30:00 +0900
categories: [observability, infrastructure, devops, monitoring]
tags: [prometheus, grafana, monitoring, promql, node-exporter, micrometer, kube-state-metrics, cadvisor, alerting, red-method, use-method, kube-prometheus-stack]
---

> *"지금 서버가 죽었나?"* — 새벽 3 시 에 *이 질문* 에 *5 초 안* 에 답할 수 있어야 *운영* 이다.
>
> *Prometheus* 와 *Grafana* 의 *짝* 은 *그 질문 의 표준 답* 이 되었다. 그런데 *둘이 어떻게 협업* 하는지 — *Prometheus 가 *무엇 을 *어떻게 수집* 하고, *Grafana 가 *그것 을 *어떻게 *질문 으로 변환* 하는지* — *를 *모르면* *대시보드 는 *예쁜 그래프 의 *모음* 일 뿐, *진짜 질문 에 *답하지 못한다*.
>
> 이 글은 *8 가지 핵심 메트릭* (CPU / Memory / Disk / HTTP 요청 수 / 에러율 / 응답 시간 / DB 커넥션 / 컨테이너 상태) 이 *Prometheus 로 *어떻게 수집* 되는지, 그리고 *Grafana 가 *5 가지 운영 질문* — *지금 서버가 죽었나? CPU 가 너무 높나? 응답이 느려졌나? 에러율이 올라갔나? 트래픽이 늘었나?* — 에 *어떻게 답하는지* 를 *PromQL 한 줄 한 줄* 까지 *분해* 한다.

내 *3 편 연작* 의 *후속편* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
- [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)

이 세 글이 *문제 진단* 의 *어휘 를 *제공* 했다면, *이 글* 은 *그 어휘 를 *대시보드 위에 *고정시켜* *프로덕션 운영* 의 *언어 로 *만든다*.

---

## TL;DR — *한 줄 결론*

> *Prometheus 는 *pull-based time-series DB* — *exporter 가 노출한 `/metrics` 엔드포인트* 를 *주기적으로 긁어 온다*. *node_exporter (CPU/Mem/Disk)* + *cAdvisor (컨테이너)* + *kube-state-metrics (K8s 객체)* + *Micrometer (앱 메트릭)* 4 종 으로 *대부분 커버*. *Grafana 는 *PromQL 로 *질문 을 던지고* *시계열 그래프* + *single stat* + *알람* 으로 *답을 시각화*. *5 가지 운영 질문* 은 모두 *PromQL 1~3 줄* 로 *압축* 된다 — *up == 0*, *rate(cpu)*, *histogram_quantile(0.99, ...)*, *5xx / total*, *rate(requests)*. *대시보드 가 *예쁘다 가 *목표 가 아니라* *5 초 안 에 *판단* 이 가능한가* 가 *목표*.

---

## 1. *Prometheus 의 *수집 모델* — *Pull, Not Push*

### 1.1 *Pull-based 의 *철학*

대부분의 *전통 모니터링* (StatsD, Graphite, CloudWatch Agent) 은 *push-based* : *agent 가 *중앙 서버 에 *데이터 보냄*.

Prometheus 는 *반대* : *Prometheus 서버 가 *각 대상 의 `/metrics` 엔드포인트 를 *주기적으로 긁는다*.

```text
[Prometheus Server]
       │
       ├─ scrape every 15s ─→ http://node1:9100/metrics      (node_exporter)
       ├─ scrape every 15s ─→ http://node2:9100/metrics
       ├─ scrape every 30s ─→ http://app:8080/actuator/prometheus  (Micrometer)
       ├─ scrape every 60s ─→ http://kube-state-metrics:8080/metrics
       └─ scrape every 15s ─→ http://cadvisor:8080/metrics
```

> *왜 *pull 인가* :
>
> 1. *Service discovery* — 누가 *살아 있는지* Prometheus *자동 감지* (K8s API / Consul / file_sd).
> 2. *Healthcheck 가 *공짜* — scrape 실패 == down. `up` 메트릭이 *자동* 으로 생성.
> 3. *Backpressure* — 대상이 *과부하* 일 때 *Prometheus 가 *간격을 늘리거나 *건너뛰기* 가능.
> 4. *대상 의 *상태 가 *외부에서 *명확* — 메트릭 형식 / 노출 시점 이 *대상 책임*.

### 1.2 *Exposition format — *텍스트 한 장*

`/metrics` 엔드포인트 는 *그냥 평문 텍스트* :

```text
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 132845.62
node_cpu_seconds_total{cpu="0",mode="user"} 3215.89
node_cpu_seconds_total{cpu="0",mode="system"} 521.30
node_cpu_seconds_total{cpu="1",mode="idle"} 132792.15
...

# HELP http_server_requests_seconds Duration of HTTP server request handling
# TYPE http_server_requests_seconds histogram
http_server_requests_seconds_bucket{method="GET",uri="/api/users",status="200",le="0.005"} 1284
http_server_requests_seconds_bucket{method="GET",uri="/api/users",status="200",le="0.01"} 2138
http_server_requests_seconds_bucket{method="GET",uri="/api/users",status="200",le="0.05"} 4892
http_server_requests_seconds_bucket{method="GET",uri="/api/users",status="200",le="+Inf"} 5000
http_server_requests_seconds_sum{method="GET",uri="/api/users",status="200"} 142.85
http_server_requests_seconds_count{method="GET",uri="/api/users",status="200"} 5000
```

`metric_name{label1="value1",label2="value2"} 숫자`. 끝.

이 *단순함* 이 *생태계 폭발* 의 *원인*. 어떤 언어 / 어떤 시스템 도 *몇 줄 코드* 로 *exporter 만들 수 있다*.

### 1.3 *4 가지 메트릭 타입*

| 타입 | 의미 | 예시 |
|---|---|---|
| **Counter** | 증가만, 단조 증가 (재시작 시 0 으로 리셋) | `http_requests_total`, `node_cpu_seconds_total` |
| **Gauge** | 증감 모두 가능, 순간값 | `memory_used_bytes`, `connection_pool_active` |
| **Histogram** | 버킷 별 누적 카운트 + sum + count | `http_server_requests_seconds`, `db_query_duration` |
| **Summary** | 클라이언트 측 quantile 계산 (집계 불가) | (deprecated, histogram 권장) |

> *Counter 는 *그대로 보면 *의미 없음* — 항상 *`rate()` 또는 `increase()`* 로 *변화량* 을 본다.
> *Histogram 은 *`histogram_quantile()`* 로 *p99 / p95 / p50* 같은 *quantile* 을 *서버 측에서 계산* — 강력함.

---

## 2. *수집 대상 — *Exporter 4 종 세트*

### 2.1 *node_exporter — 시스템 메트릭*

*각 노드 에 *DaemonSet 으로 배포*. `/proc`, `/sys` 를 읽어 *Prometheus 형식* 으로 노출.

**제공 메트릭 (300+)** — 핵심만 :

```text
# CPU
node_cpu_seconds_total{cpu, mode}                    # CPU 시간 (mode = user/system/idle/iowait/...)

# 메모리
node_memory_MemTotal_bytes
node_memory_MemAvailable_bytes
node_memory_Buffers_bytes
node_memory_Cached_bytes
node_memory_SwapTotal_bytes / SwapFree_bytes

# 디스크 (블록 디바이스)
node_disk_read_bytes_total{device}
node_disk_written_bytes_total{device}
node_disk_io_time_seconds_total{device}              # %util 계산용

# 파일시스템 (마운트 단위)
node_filesystem_size_bytes{mountpoint, fstype}
node_filesystem_avail_bytes{mountpoint, fstype}

# 네트워크
node_network_receive_bytes_total{device}
node_network_transmit_bytes_total{device}

# 로드 / uptime
node_load1 / node_load5 / node_load15
node_boot_time_seconds
```

### 2.2 *cAdvisor — 컨테이너 메트릭*

K8s 의 *kubelet* 에 *내장*. 컨테이너 cgroup 통계 를 노출.

```text
container_cpu_usage_seconds_total{pod, container, namespace}
container_memory_working_set_bytes{pod, container}      # 진짜 사용량 (RSS - inactive_file)
container_memory_rss
container_fs_usage_bytes{pod, device}
container_network_receive_bytes_total{pod, interface}
container_network_transmit_bytes_total{pod, interface}
```

> *왜 *container_memory_working_set_bytes* 가 *진짜* 인가 :
>
> *`rss + cache - inactive_file`*. K8s OOMKiller 가 *이 값 기준* 으로 죽인다. *대시보드 에 *이걸 써야 함*.

### 2.3 *kube-state-metrics — K8s 객체 상태*

Pod / Deployment / Node / PVC 등 *K8s 객체 의 *상태 를 *메트릭화*.

```text
kube_pod_status_phase{pod, namespace, phase}            # Running/Pending/Failed/...
kube_pod_container_status_restarts_total
kube_pod_container_status_ready
kube_deployment_status_replicas / replicas_available / replicas_unavailable
kube_node_status_condition{node, condition, status}     # Ready/MemoryPressure/...
kube_persistentvolumeclaim_status_phase
```

> *cAdvisor 가 *런타임 메트릭 (얼마나 쓰고 있나)* 이라면, *kube-state-metrics 는 *선언적 상태 (몇 개 떠있어야 하나)*. 둘이 *상호 보완*.

### 2.4 *Micrometer (Spring Boot) — 애플리케이션 메트릭*

Spring Boot 3.x 에 *기본 내장*. `micrometer-registry-prometheus` 만 추가 :

```gradle
implementation 'io.micrometer:micrometer-registry-prometheus'
```

`/actuator/prometheus` 가 *자동 노출*.

**자동 제공 메트릭** :
```text
# HTTP (Servlet)
http_server_requests_seconds{method, uri, status, exception, outcome}
http_server_requests_active_seconds   # 현재 진행 중

# JVM
jvm_memory_used_bytes{area, id}        # area=heap/nonheap, id=Eden/Survivor/Old/...
jvm_gc_pause_seconds{action, cause}
jvm_threads_states_threads{state}      # state=runnable/waiting/timed_waiting/...

# Hikari 커넥션 풀
hikaricp_connections_active{pool}
hikaricp_connections_pending{pool}     # ← 풀 고갈 신호
hikaricp_connections_timeout_total

# Logback / Logging
logback_events_total{level}

# Tomcat
tomcat_sessions_active_current
tomcat_threads_busy{name}
```

**커스텀 메트릭** :
```java
@Component
public class OrderMetrics {
    private final Counter ordersCreated;
    private final Timer orderProcessing;

    public OrderMetrics(MeterRegistry registry) {
        this.ordersCreated = Counter.builder("orders.created")
            .tag("region", "kr")
            .register(registry);
        this.orderProcessing = Timer.builder("orders.processing")
            .publishPercentileHistogram()  // ← histogram 으로 노출 → p99 계산 가능
            .register(registry);
    }

    public void onOrderCreated() {
        ordersCreated.increment();
    }
}
```

---

## 3. *PromQL — *질문 의 *언어*

### 3.1 *기본 셀렉터*

```promql
# 메트릭 이름만
node_cpu_seconds_total

# 레이블 필터
node_cpu_seconds_total{mode="idle"}
node_cpu_seconds_total{mode!="idle"}
node_cpu_seconds_total{instance=~"node-.*"}     # 정규식

# 시간 범위 (range vector)
node_cpu_seconds_total[5m]
```

### 3.2 *핵심 함수 5 가지*

```promql
# 1. rate(counter[range]) — 초당 증가량
rate(http_requests_total[5m])
# = (5분 후 값 - 5분 전 값) / 300

# 2. increase(counter[range]) — 범위 동안 총 증가
increase(http_requests_total[1h])

# 3. histogram_quantile(quantile, sum by (le)) — quantile 계산
histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))

# 4. sum / avg / max / min by (label) — 집계
sum by (instance) (rate(http_requests_total[5m]))

# 5. predict_linear(gauge[range], seconds_into_future) — 선형 예측
predict_linear(node_filesystem_avail_bytes[1h], 4 * 3600) < 0   # 4시간 후 디스크 부족 예측
```

### 3.3 *Recording rule — *비싼 쿼리 *미리 계산*

복잡한 PromQL 을 *주기적으로 미리 계산* 해서 *별도 시계열* 로 저장. Grafana 가 *빠르게 조회*.

```yaml
groups:
  - name: app.rules
    interval: 30s
    rules:
      - record: app:http_request_rate_5m
        expr: sum by (service) (rate(http_server_requests_seconds_count[5m]))
      - record: app:http_error_rate_5m
        expr: |
          sum by (service) (rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
          /
          sum by (service) (rate(http_server_requests_seconds_count[5m]))
```

→ Grafana 에서 `app:http_error_rate_5m` 만 select 하면 됨.

---

## 4. *8 가지 메트릭 — *각각 *PromQL 한 줄 정리*

### 4.1 *CPU 사용률*

> *"전체 CPU 의 *몇 % 가 *놀고 있지 않은가"* — `100 - idle%`.

```promql
# 노드 별 CPU 사용률 (%)
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 모드 별 breakdown (user vs system vs iowait)
sum by (mode) (rate(node_cpu_seconds_total[5m])) * 100

# 컨테이너 별 CPU (vCPU 단위)
sum by (pod) (rate(container_cpu_usage_seconds_total{pod!=""}[5m]))

# 컨테이너 의 *requests 대비 사용률*
sum by (pod) (rate(container_cpu_usage_seconds_total{pod!=""}[5m]))
/
sum by (pod) (kube_pod_container_resource_requests{resource="cpu"})
```

### 4.2 *메모리 사용량*

```promql
# 노드 메모리 사용률 (%)
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 컨테이너 working set (OOMKiller 기준)
container_memory_working_set_bytes{pod!=""}

# 컨테이너 의 *limit 대비 사용률* (OOMKill 위험도)
container_memory_working_set_bytes{pod!=""}
/
on(pod, container) kube_pod_container_resource_limits{resource="memory"}

# JVM heap 사용률
sum by (instance) (jvm_memory_used_bytes{area="heap"})
/
sum by (instance) (jvm_memory_max_bytes{area="heap"})
```

### 4.3 *디스크 사용량*

```promql
# 파일시스템 사용률 (%)
(1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
    / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}) * 100

# 디스크 I/O 사용률 (%util — iostat -x 의 그것)
rate(node_disk_io_time_seconds_total[5m]) * 100

# 디스크 IOPS
rate(node_disk_reads_completed_total[5m]) + rate(node_disk_writes_completed_total[5m])

# 디스크 처리량 (MB/s)
(rate(node_disk_read_bytes_total[5m]) + rate(node_disk_written_bytes_total[5m])) / 1024 / 1024

# 디스크 가 *N 시간 후 *꽉 찰까* 예측
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 4*3600) < 0
```

### 4.4 *HTTP 요청 수 (Throughput)*

```promql
# RPS (초당 요청)
sum by (service) (rate(http_server_requests_seconds_count[5m]))

# 엔드포인트 별
sum by (uri) (rate(http_server_requests_seconds_count[5m]))

# 상태 코드 별
sum by (status) (rate(http_server_requests_seconds_count[5m]))
```

### 4.5 *에러율*

```promql
# 5xx 비율 (%)
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
/
sum(rate(http_server_requests_seconds_count[5m]))
* 100

# 4xx + 5xx
sum(rate(http_server_requests_seconds_count{status=~"4..|5.."}[5m]))
/
sum(rate(http_server_requests_seconds_count[5m]))

# Exception 발생률 (Micrometer 의 exception 레이블)
sum by (exception) (rate(http_server_requests_seconds_count{exception!="None"}[5m]))
```

### 4.6 *응답 시간 (Latency)*

```promql
# p50 / p95 / p99 (5분 window)
histogram_quantile(0.50, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))
histogram_quantile(0.95, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))

# 엔드포인트 별 p99
histogram_quantile(0.99,
  sum by (uri, le) (rate(http_server_requests_seconds_bucket[5m]))
)

# 평균 응답 시간 (덜 유용함, p99 권장)
rate(http_server_requests_seconds_sum[5m]) / rate(http_server_requests_seconds_count[5m])
```

> *왜 *avg 가 아니라 *quantile* 인가 :
>
> *100 요청 중 99 개가 *10 ms*, 1 개가 *10 초* 라면 *avg = 109 ms* — 평탄해 보임.
> *quantile* 은 *p99 = 10 초* — *그 1 명 사용자 의 *고통* 이 *보임*. *avg 는 *사용자 가 아닌 *서버 의 관점*.

### 4.7 *DB 커넥션 수*

```promql
# HikariCP 활성 / 대기 / 총 풀 크기
hikaricp_connections_active{pool="HikariPool-1"}
hikaricp_connections_pending{pool="HikariPool-1"}    # ← 폴 고갈 신호!
hikaricp_connections_max{pool="HikariPool-1"}

# 풀 사용률 (%)
hikaricp_connections_active / hikaricp_connections_max * 100

# 커넥션 타임아웃 발생률
rate(hikaricp_connections_timeout_total[5m])

# PostgreSQL (postgres_exporter)
pg_stat_database_numbackends{datname="myapp"}
pg_settings_max_connections
```

### 4.8 *컨테이너 상태*

```promql
# Pod 상태별 카운트
sum by (namespace, phase) (kube_pod_status_phase)

# 재시작 횟수 (CrashLoopBackOff 감지)
rate(kube_pod_container_status_restarts_total[15m]) > 0

# 미준비 Pod (Ready != 1)
sum by (namespace) (kube_pod_status_ready{condition="false"})

# Deployment 가 *원하는 만큼 안 떠 있음*
kube_deployment_status_replicas_available < kube_deployment_spec_replicas

# Node 가 NotReady
kube_node_status_condition{condition="Ready", status="false"} == 1

# 노드 / 서비스 가 *Prometheus 자체 가 못 긁고 있음*
up == 0
```

> *`up`* 은 *Prometheus 가 *자동 생성* 하는 *메타 메트릭* — *scrape 성공 = 1, 실패 = 0*. *서버 죽음* 의 *가장 단순한 신호*.

---

## 5. *5 가지 운영 질문 → *PromQL 답*

### 5.1 *"지금 서버가 죽었나?"*

가장 *기본* 의 질문. *3 단계 답*:

```promql
# 1. Prometheus 가 *scrape 자체 를 못 함*
up{job="my-app"} == 0
# → 알람 'AppDown', for: 1m

# 2. 노드 가 *NotReady*
kube_node_status_condition{condition="Ready", status="false"} == 1

# 3. Deployment 가 *원하는 만큼 *안 떠 있음*
kube_deployment_status_replicas_available < kube_deployment_spec_replicas
```

**Grafana 패널** :
- *Stat panel* (single number) — *down 개수 카운트*.
- *Threshold* — green (0) / red (>=1).
- *Alert rule* — `up == 0` for 1m → Alertmanager → Telegram / Slack.

```yaml
# Alert rule
- alert: ServiceDown
  expr: up == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "{{ $labels.job }} on {{ $labels.instance }} is down"
```

### 5.2 *"CPU 가 너무 높나?"*

```promql
# 노드 CPU 사용률
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# load average vs CPU 수
node_load5 / count without (cpu, mode) (node_cpu_seconds_total{mode="idle"}) > 1
# load5 > CPU 수 → 처리 못하고 *큐 쌓이는 중*

# iowait 가 *비정상적* 으로 높은가 (디스크 병목 신호)
avg by (instance) (rate(node_cpu_seconds_total{mode="iowait"}[5m])) * 100 > 20
```

**Grafana 패널** :
- *Time series* — 노드 별 CPU 사용률 라인.
- *Stacked* (user / system / iowait / steal) — *왜 높은가* 까지 보이게.
- *Threshold line* — 80% (warning), 95% (critical).

**알람** :
```yaml
- alert: HighCpuUsage
  expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
  for: 10m  # 10분 지속 시
  labels:
    severity: warning
```

### 5.3 *"응답 시간이 느려졌나?"*

```promql
# 현재 p99
histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))

# 1시간 전 p99 과 비교 (편차)
histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))
/
histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m] offset 1h)))
# > 2 면 *2 배 느려짐*

# SLO 위반 (p99 > 500ms 가 *5분 이상*)
histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket[5m]))) > 0.5
```

**Grafana 패널** :
- *Time series* — p50 / p95 / p99 *3 라인 동시*.
- *Heatmap* — *latency 분포 의 *시간별 변화* (가장 강력한 시각화 중 하나).

```promql
# Heatmap 용 (Grafana 가 자동 처리)
sum by (le) (rate(http_server_requests_seconds_bucket[1m]))
```

### 5.4 *"에러율이 올라갔나?"*

```promql
# 5xx 비율
(sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
/
sum(rate(http_server_requests_seconds_count[5m]))) * 100

# 1시간 전 대비 *5 배 이상* 증가
(sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) + 0.01)
/
(sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m] offset 1h)) + 0.01)
> 5

# Spring Exception 별 카운트
sum by (exception) (rate(http_server_requests_seconds_count{exception!="None"}[5m]))
```

**Grafana 패널** :
- *Time series* — 에러율 (%) + *threshold 1%*.
- *Bar chart* — *exception 별 top 10*.
- *Logs panel (Loki 연동)* — 알람 발생 시 *동시간대 로그* 자동 표시.

### 5.5 *"트래픽이 갑자기 늘었나?"*

```promql
# RPS
sum(rate(http_server_requests_seconds_count[5m]))

# 5분 전 대비 변동
sum(rate(http_server_requests_seconds_count[5m]))
/
sum(rate(http_server_requests_seconds_count[5m] offset 5m))
# > 2 → 5분 만에 *2 배*

# 엔드포인트 별 — *어디로 *몰리고 있나*
topk(10, sum by (uri) (rate(http_server_requests_seconds_count[5m])))

# IP 별 (gateway 가 client_ip 레이블 노출 시)
topk(10, sum by (client_ip) (rate(http_server_requests_seconds_count[5m])))
# → DDoS / scraping 봇 감지
```

**Grafana 패널** :
- *Time series* — 전체 RPS + *엔드포인트 별 stacked area*.
- *Single stat* — 현재 RPS, 1시간 전 대비 변동 (%).
- *Table* — *top 10 엔드포인트 / 클라이언트 IP*.

---

## 6. *RED 방법론 vs USE 방법론*

> *어떤 메트릭 을 *우선 봐야 하나* 라는 질문에 *체계적인 답*.

### 6.1 *RED — *서비스 (요청 처리) 관점*

Tom Wilkie (Weaveworks) 제안. *모든 서비스* 에 *3 가지 만 측정*:

| | 의미 | PromQL |
|---|---|---|
| **R** ate | 초당 요청 수 | `rate(http_requests_total[5m])` |
| **E** rrors | 실패 요청 수 (또는 비율) | `rate(http_requests_total{status=~"5.."}[5m])` |
| **D** uration | 응답 시간 분포 | `histogram_quantile(0.99, ...)` |

→ *5 가지 운영 질문 중 *3 가지* 가 *RED* 로 즉시 답 가능.

### 6.2 *USE — *리소스 관점*

Brendan Gregg 제안. *모든 자원* 에 *3 가지 만 측정*:

| | 의미 | 예시 |
|---|---|---|
| **U** tilization | 자원이 *얼마나 사용* 중 | CPU 사용률 %, 디스크 %util, 메모리 % |
| **S** aturation | 자원이 *얼마나 *과부하* (대기열 깊이) | CPU run-queue, 디스크 await, 메모리 swap, HikariCP pending |
| **E** rrors | 자원의 *오류 카운트* | 디스크 errors, NIC drops, OOMKilled |

→ *5 가지 중 *서버/CPU/메모리/디스크 질문* 이 *USE* 로 답.

### 6.3 *두 방법론 의 *결합*

| 질문 | 도구 |
|---|---|
| 서비스 가 사용자에게 *어떻게 보이나*? | **RED** |
| 인프라 자원이 *어떻게 *돌고 있나*? | **USE** |

> *RED 와 *USE 가 *서로 *상관* 되는 지점 — 예: *p99 latency 가 오르고 *디스크 saturation* 도 오른다 → *디스크 가 *latency 의 원인*.

---

## 7. *Grafana 대시보드 설계 — *5 초 안 에 *판단 가능* 한가*

### 7.1 *Golden signals 4 가지 의 *Layout*

화면 *상단* 에 *5 초 안에 판단 가능한 *Single stat 4 개*:

```text
┌──────────────────────────────────────────────────┐
│  [RPS]      [Error %]   [p99 (ms)]   [Healthy]  │
│   1,247       0.02         142         12/12    │
└──────────────────────────────────────────────────┘
  ↓ (스크롤 하면) — 시계열 그래프
  ↓ (더 스크롤) — 호스트/Pod 별 상세
```

→ *대시보드 의 *상단 4 개 숫자* 만 *5 초 보고* *정상 / 비정상* 판단 가능.

### 7.2 *Threshold + Color*

```yaml
# Grafana stat panel — error rate
thresholds:
  - color: green
    value: 0
  - color: yellow
    value: 0.5    # 0.5% 부터 노란색
  - color: red
    value: 2      # 2% 부터 빨간색
```

→ *숫자 만 보면 직관 부족* — *색깔* 이 *5 초 판단* 의 *촉매*.

### 7.3 *Variables — *대시보드 *1 개 로 *전체 서비스* 커버*

```text
[namespace ▼: settlement]  [service ▼: order-service]  [pod ▼: all]
```

→ *모든 패널 의 PromQL* 이 *변수 를 *주입* 받아 *재사용*. *서비스 별 대시보드 N 개 만들 필요 없음*.

```promql
# 변수 사용 예
sum by (instance) (rate(http_server_requests_seconds_count{
  namespace="$namespace",
  service="$service",
  pod=~"$pod"
}[5m]))
```

### 7.4 *Drill-down*

Grafana 의 *링크 기능* 으로 *상위 대시보드 → 하위 대시보드* 자동 점프. 예 :

- *클러스터 overview* 에서 *문제 Pod* 클릭 → *Pod 상세 대시보드* + *동시간대 Loki 로그*.

→ *알람 → 5초 판단 → drill-down → 30초 원인 식별* 의 *flow* 가 *대시보드 의 진짜 목적*.

---

## 8. *알람 (Alertmanager) — *예방* 의 *마지막 층*

### 8.1 *알람 의 *3 가지 기본 형태*

```yaml
groups:
  - name: critical.rules
    rules:
      # 1. 서비스 down — 1분 지속
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "{{ $labels.job }} ({{ $labels.instance }}) is DOWN"

      # 2. 에러율 1% 초과 — 5분 지속
      - alert: HighErrorRate
        expr: |
          sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
          / sum(rate(http_server_requests_seconds_count[5m])) > 0.01
        for: 5m
        labels: { severity: warning }

      # 3. SLO 위반 (p99 latency > 500ms)
      - alert: P99LatencyHigh
        expr: |
          histogram_quantile(0.99,
            sum by (le) (rate(http_server_requests_seconds_bucket[5m]))
          ) > 0.5
        for: 10m
        labels: { severity: warning }
```

### 8.2 *알람 *피로 (Alert Fatigue)* 방지*

- *`for:` 조건* — *순간 spike 무시*. 5 분 지속 시에만 알람.
- *Severity 분리* — `critical` (즉시 깨움) vs `warning` (업무 시간 처리).
- *Routing 분리* — `critical` → 전화 + SMS, `warning` → Telegram, `info` → 로그만.
- *Inhibition* — *상위 알람* 이 *발생* 하면 *하위 알람 *suppress*. 예: 노드 down → 그 노드의 모든 pod 알람 무시.
- *Silence* — *유지보수 시간 *명시적 silence*.

```yaml
# alertmanager.yml — Telegram 라우팅 예
route:
  receiver: telegram-default
  routes:
    - match: { severity: critical }
      receiver: telegram-critical
      group_wait: 0s        # 즉시
    - match: { severity: warning }
      receiver: telegram-warnings
      group_wait: 30s       # 30초 모아서 발송
      group_interval: 5m
```

---

## 9. *kube-prometheus-stack — *조립품* 의 *현실*

대부분 *처음부터 *구성하지 않는다*. *Helm chart `kube-prometheus-stack`* 이 *Prometheus + Grafana + Alertmanager + node-exporter + kube-state-metrics + 사전 정의 알람 규칙 + 사전 정의 Grafana 대시보드* 를 *한 번에 설치*.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prom prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

설치 후 *기본 제공 대시보드* :
- *Kubernetes / Compute Resources / Cluster / Namespace / Pod*
- *Node Exporter / Nodes*
- *Kubernetes / Networking / Cluster*
- *Prometheus / Overview*
- *Alertmanager / Overview*

→ *기본 70% 가 *바로* 작동. *나머지 30%* 가 *내 애플리케이션 의 Micrometer 메트릭 을 *얹는 것*. 우리 K3s 클러스터 도 *kube-prometheus-stack + Loki* 조합 으로 *데이비드 노드* 에서 *운영* 중.

---

## 10. *실전 체크리스트 — *프로덕션 도입* 시*

내가 *팀 에 *Prometheus + Grafana* 를 *도입 할 때 *순서대로 체크* 하는 *10 가지*:

1. *kube-prometheus-stack* 설치 → *기본 인프라 메트릭* 확보.
2. *Micrometer* 추가 → *각 앱 마다 `/actuator/prometheus`*.
3. *ServiceMonitor* 또는 *PodMonitor* CRD 작성 → Prometheus 가 *자동 발견*.
4. *Histogram (publishPercentileHistogram = true)* 활성화 → *p99 계산 가능* 한 데이터 확보.
5. *Recording rule* 작성 — *비싼 PromQL* 미리 계산.
6. *대시보드* 작성 — *상단 4 개 single stat (RPS / Error % / p99 / Healthy)* 부터.
7. *Alert rule* 작성 — `ServiceDown`, `HighErrorRate`, `P99LatencyHigh` 3 개 필수.
8. *Alertmanager Routing* — severity 별 채널 분리.
9. *Loki* 연동 → 알람 시 *동시간대 로그* drill-down.
10. *Runbook 링크* — 알람 annotation 에 *처리 매뉴얼 URL* 첨부.

---

## 11. *결론 — *대시보드 는 *질문 에 답* 해야 한다*

> *예쁜 그래프 는 *대시보드 의 *목적 이 아니다*. *"지금 서버가 죽었나?"* 라는 *질문 에 *5 초 안 에 *답 하는 것* 이 *목적*.

*Prometheus* 는 *pull-based scrape* 로 *4 종 exporter 의 메트릭* 을 *통일된 텍스트 포맷* 으로 *수집*. *Grafana* 는 *PromQL 한 줄* 을 *시각적 패널* 로 *번역*. *그 짝 의 *철학 적 강점* 은 *단순함* — *각 부품이 *작고 명확*, *상호 결합 이 *느슨*.

> *5 가지 운영 질문* 에 대한 *답* 은 *모두 *PromQL 1~3 줄* 로 *압축* 된다.
>
> - 서버 죽음 → `up == 0`
> - CPU 높음 → `100 - rate(node_cpu_seconds_total{mode="idle"}[5m])`
> - 응답 느림 → `histogram_quantile(0.99, ...)`
> - 에러 증가 → `rate(...status=~"5..") / rate(...)`
> - 트래픽 spike → `rate(...) / rate(... offset 5m)`

*그 다섯 줄* 을 *대시보드 상단* 에 *single stat 으로 *고정* 해두면 — *새벽 3 시 의 *알람* 이 *진짜 사건* 인지 *오탐* 인지 *5 초 안* 에 *판단* 할 수 있다. *그게 *Observability 가 *Operations 에 *주는 가장 큰 선물*.

*수십 개 의 *예쁜 그래프 보다 *질문 에 답하는 *4 개 의 숫자* 가 *프로덕션* 에선 *훨씬 가치 있다*. *그게 *Prometheus 와 *Grafana 가 *짝 으로 살아남은 *진짜 이유*.

---

## *참고*

- *Prometheus 공식 문서* — [prometheus.io/docs](https://prometheus.io/docs).
- *Grafana 공식 PromQL guide* — [grafana.com/docs/grafana/latest/datasources/prometheus](https://grafana.com/docs/grafana/latest/datasources/prometheus).
- *Brendan Gregg, *USE Method* — [brendangregg.com/usemethod.html](https://www.brendangregg.com/usemethod.html).
- *Tom Wilkie, *Monitoring Microservices: The Three Pillars (RED Method)*.
- *Google SRE Book* — *Chapter 6: Monitoring Distributed Systems*.
- *Inside the JVM by Bill Venners* — JFR / Micrometer 의 *내부 동작*.
- 우리 K3s 클러스터 의 *kube-prometheus-stack* 운영 경험 — 데이비드 노드 의 *Prometheus + Loki + Grafana* 조합.
- 자매편 :
  - [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
  - [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
  - [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
