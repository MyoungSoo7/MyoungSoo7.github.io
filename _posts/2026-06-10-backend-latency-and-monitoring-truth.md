---
layout: post
title: "백엔드 개발자가 알아야 할 *응답 시간의 진실* — *평균이 거짓말하는 이유* 와 *모니터링 시스템이 잡지 못하는 것*"
date: 2026-06-10 16:30:00 +0900
categories: [backend, sre, observability, performance]
tags: [latency, percentile, p99, slo, sli, error-budget, prometheus, grafana, tempo, loki, distributed-tracing, monitoring]
---

> 동료가 *대시보드* 를 보여줬다 :
>
> *"평균 응답시간 100ms 다. *잘 돌고 있어*."*
>
> 같은 시간 *고객 게시판* 에 *"결제가 *10 초씩 멈춰요*"* 가 *3 건* 올라와 있었다.
>
> *둘 다 *옳다*. 그리고 *둘 다 *틀렸다**.

이 글은 *백엔드 개발자가 *지금 알아야 할* 응답시간의 진실* — *평균이 *왜 거짓말* 인지*, *percentile 이 *왜 진실에 가까운지**, *그리고 *Prometheus + Grafana + Tempo + Loki* 같은 *모니터링 시스템* 이 *잡지 못하는 것* 은 무엇인지* 를 *실제 운영 사례* 와 *함께* 풀어본다.

---

## TL;DR

> *응답시간은 *평균* 으로 보는 게 *아니라 *분포* 로 봐야 한다*. *Long tail 의 *p99 / p999* 가 *진짜 사용자 경험*. *모니터링 시스템* 은 *p99* 를 잡는 도구지 *전부* 가 아니다. *sampling / cardinality / 측정의 비용* 이라는 *3 가지 함정* 이 있고, *그걸 알아야 *진짜 SRE 가 된다*.

---

## 1. *발단 — *평균 100ms* 가 *어떻게 *거짓말* 이 되나*

가장 흔한 *백엔드 응답시간 분포* :

```
빈도 ↑
   │  ████
   │  ████ ████
   │  ████ ████ ████
   │  ████ ████ ████ ███                 ─────── (긴 꼬리)
   │  ████ ████ ████ ███ ██ ██ █ █ █ █ █ █ █ █ █ █ █
   │  ────────────────────────────────────────────────→ 응답시간
   50ms 100ms 200ms 500ms 1s         5s            10s
       ↑                              ↑
      대부분                          0.5% 인데 *이게 *진짜 문제**
```

이게 *long-tail 분포 (heavy-tailed)*. 대부분의 요청은 빠르고 일부 요청은 매우 느리다. *평균* 을 내면 *100 ms* — 빠른 요청에 *희석* 된다. 그러나 *p99 (상위 1%)* 를 보면 *5 초* 다.

*5 초 안에 응답 못 받은 0.5% 사용자* 가 *게시판에 글 쓴다*. *평균 100ms 라는 대시보드의 통계가 진실의 0.5% 를 못 본다*.

---

## 2. *Percentile — *진짜 분포 의 *시야**

### 2.1 *각 percentile 의 의미*

| 지표 | 의미 | 예 (평균 100ms 시스템) |
|---|---|---|
| *p50 (median)* | *반의 요청은 이보다 빠르다* | *80 ms* |
| *p95* | *95% 의 요청은 이보다 빠르다* | *250 ms* |
| *p99* | *99% 의 요청은 이보다 빠르다* | *1.2 s* |
| *p999* | *99.9% 의 요청은 이보다 빠르다* | *5 s* |
| *max* | *가장 느린 요청* | *12 s* |

*평균 (mean)* 은 *어디에 있지도 않은 *상상의 점**. *median (p50)* 이 *실제 *중앙값*.

### 2.2 *왜 p99 가 *핵심* 인가*

*p99* 는 *상위 1% 사용자가 *겪는* 응답시간*. 1 % 같지만 *서비스 규모가 초당 1000 요청이면 초당 10 명이 느림을 겪는다*. 분당 600 명. 하루 86 만 명. 체감 사용자 비율이 *생각보다 훨씬 크다*.

*Amazon 의 경험적 법칙* :

> *응답시간 100 ms 증가 = 매출 1% 감소 (실증 데이터, 2006~2010)*

p99 를 200ms 에서 1.2 s 로 방치한다는 건 *상위 1% 사용자에게 6 배 더 불쾌한 경험을 준다는 의미*. 그게 전환율에 직접 반영.

### 2.3 *p999 까지 가는 이유*

*결제 시스템* 같은 *돈이 흐르는 곳* 은 *p999 (천 명 중 1 명)* 까지도 모니터링한다. *돈 결제 실패 한 건이 고객 신뢰의 전부일 수 있기 때문에*.

---

## 3. *Latency 측정의 *3 가지 함정**

### 3.1 *Coordinated Omission*

벤치마크 도구가 *서버 응답이 느려질 때 요청 보내기를 기다린다*. 그래서 *느린 시점의 요청 양 자체가 줄어든다*. *실제 분포보다 훨씬 좋게 보고된다*.

Gil Tene 의 *HdrHistogram* 같은 도구는 이 문제를 *수정* 한 측정을 한다. production benchmark 에서 반드시 확인해야 할 함정.

### 3.2 *Histogram bucket 의 정밀도*

Prometheus 의 *histogram* 은 *미리 정의된 bucket* 에 카운트 누적. *bucket 사이의 값은 보간 (interpolation)*. *p99 추정치의 오차가 bucket 분포에 크게 좌우*.

섬세한 bucket 을 쓰면 cardinality 증가 — 메모리·CPU 비용 ↑. trade-off.

### 3.3 *Aggregation 의 위험*

5 개 노드의 p99 를 *평균낸 전체 p99* — 이게 *수학적으로 틀렸다*. *p99 는 aggregable 하지 않다*. 정확한 전체 p99 를 알려면 *모든 raw sample 을 모아서 다시 계산* 해야 한다.

Prometheus 의 `histogram_quantile()` 은 bucket sum 으로 *근사하는 유사 정확*. 완벽하지 않다.

---

## 4. *RED + USE Method — *모니터링의 *두 표준 시야**

### 4.1 *RED Method* (요청 관점)

Tom Wilkie (Weaveworks) 의 *3 가지 황금 지표* :

- **R**ate : 초당 요청 수
- **E**rror : 에러 비율 (4xx + 5xx)
- **D**uration : 응답시간 *분포* (p50, p99 등)

*사용자가 보는 관점*. 결제 / 검색 / 주문 같은 *비즈니스 엔드포인트별* 측정.

### 4.2 *USE Method* (자원 관점)

Brendan Gregg 의 *시스템 자원 진단* :

- **U**tilization : 자원 사용률 (CPU, memory, disk I/O, network)
- **S**aturation : 큐에 대기 중인 작업량 (run queue, connection wait)
- **E**rrors : 자원의 에러 (disk read error, dropped packet)

*시스템 관점*. CPU / memory / disk / network 각각에 3 지표 측정.

### 4.3 *두 method 의 *상호 보완**

- *RED* 가 *Duration 이 길다* 고 알려줌
- *USE* 가 *CPU saturation 이 100%* 라고 알려줌
- 둘을 교차해서 *"긴 응답시간 = CPU 부족"* 결론 도출

한 method 만 있으면 *증상만 보임*. 원인 추적 못 함. 그래서 *RED + USE* 둘 다 필요.

---

## 5. *SLO + Error Budget — *목표 와 *허용량***

### 5.1 *SLI (Service Level Indicator)*

*측정하는 지표*. 예: p99 latency, 5xx 비율, availability.

### 5.2 *SLO (Service Level Objective)*

*우리가 목표하는 값* :

- `p99 latency < 200ms`
- `availability ≥ 99.9%`
- `5xx error rate < 0.1%`

### 5.3 *Error Budget*

SLO 가 99.9% 면 *허용 실패율 = 0.1%* = *한 달에 43 분*. 이게 *우리가 망쳐도 되는 시간*.

*Error budget burn* 이 평소보다 빠르면 알람. 내 다른 글 [*etcd HDD trap*](/2026/06/06/etcd-fsync-hdd-trap-kube-api-error-budget-burn.html) 에서 자세히 다뤘다. *KubeAPIErrorBudgetBurn* 알람 한 줄에서 *디스크 마이그레이션* 까지 가는 *수직 진단의 시작점*.

### 5.4 *Burn rate 와 *알람 디자인**

짧은 + 긴 window 의 *2 단계 burn rate* 가 signal-to-noise 좋은 알람 패턴 :

| Severity | 짧은 window | 긴 window | Burn rate |
|---|---|---|---|
| Critical | 5 분 | 1 시간 | 14.4 |
| Critical | 30 분 | 6 시간 | 6 |
| Warning | 2 시간 | 1 일 | 3 |
| Warning | 6 시간 | 3 일 | 1 |

*두 window 모두 임계 넘었을 때* 만 알람. flap 적고 반응 빠른 신호.

---

## 6. *모니터링 스택의 *3 pillars** — Metric / Log / Trace

### 6.1 *Metric (Prometheus + Grafana)*

*수치 시계열*. 집계 + 시각화의 핵심. *cardinality 제한* (label 조합) 이 비용 결정. *RED + USE method* 의 실질적 구현.

### 6.2 *Log (Loki + Elasticsearch)*

*세부 이벤트의 원시 기록*. grep 가능한 서사적 진단. *cardinality 무한* (모든 행이 unique 가능) 이라 저장 비용 ↑. retention 정책으로 시간 절단.

### 6.3 *Trace (Tempo + Jaeger)*

*분산 시스템의 한 요청의 전 여정*. Service A → B → C → DB 의 각 단계 latency 를 *한 그림에 본다*. Spring Cloud Sleuth / OpenTelemetry / gRPC interceptor 가 자동 instrumentation.

### 6.4 *셋의 *상호 보완**

- *Metric 의 알람* 이 *"p99 가 튀었다"*
- → *Trace 가 *"그 시점 결제 endpoint 가 5 초였다"*
- → *Log 가 *"DB connection pool 고갈 직전에 5 건의 slow query"*

*셋이 교차해야 root cause 가 나타난다*.

내 인프라의 stack :
- *Prometheus + kube-prometheus-stack + Grafana* (metric)
- *Loki + Fluent Bit* (log, K8s 워크로드)
- *Elastic Stack (ECK)* (log, 도메인 워크로드 + 시계열 분석)
- *Tempo* (distributed trace — 부분 적용 중)

---

## 7. *모니터링 시스템의 *3 가지 진짜 함정** — 잘 안 말하는 것들*

### 7.1 *Cardinality explosion*

Prometheus metric 의 *label 조합 수* 가 *cardinality*. 예 :

```
http_request_duration_seconds{method="GET", path="/api/products", status="200"}
```

path 가 */api/products/{id}* 같은 *동적 ID* 면 *백만 개 id × 10 method × 5 status = 5천만 개 시계열*. Prometheus 메모리 *수십 GB*. 서비스 망.

해결 : *path 를 route 패턴 (/api/products/{id}) 으로 집계*. id 별 metric 은 *trace* 로.

### 7.2 *Sampling의 함정*

Trace 가 *모든 요청을 기록하면 너무 비쌈*. 보통 *1% 샘플링*. 그러면 :

- *드물게 일어나는 p999 의 원인을 놓친다*
- 우연히 잡힌 느린 trace 가 *대표성 있나 의심*
- *tail-based sampling* (지연 보고 후 느린 것만 저장) 으로 완화 가능, 다만 메모리·복잡도 ↑

### 7.3 *측정의 *비용***

*Observability 가 공짜가 아니다*. 각 metric / log / trace 는 *수집 + 전송 + 저장 + 인덱싱* 의 비용. 서비스의 *5~10% CPU* 가 observability 자체에 들 수 있다.

*과한 측정 = 측정이 측정 대상을 방해*. *Heisenberg 의 관측자 효과* 의 분산 시스템 버전.

해결 : 비싼 측정 (trace, 동적 cardinality) 은 *샘플링 + dynamic enable*. 기본은 *metric + log* 의 저비용 조합.

---

## 8. *내 인프라의 *실제 사례 3 건**

### Case 1 — *Velero CPU throttling 99.54%*

- *Metric* (`container_cpu_throttled_seconds_total`) 가 *99.54%* 로 알람
- *USE method* 의 *Saturation*
- Trace / Log 없이도 *cgroup 의 cpu.max 가 진짜 원인* 임이 *수치만으로 도출*
- 조치 : limit 1 → 2

### Case 2 — [*etcd HDD trap*](/2026/06/06/etcd-fsync-hdd-trap-kube-api-error-budget-burn.html)

- *Metric* (`KubeAPIErrorBudgetBurn`) 의 burn rate 알람 한 줄
- *Trace 없음* (etcd 내부 추적은 비공개)
- *Log* (`fdatasync took XYZ ms`) 가 *디스크 fsync 가 원인* 임을 명시
- 조치 : etcd 를 SSD 로 마이그레이션. *GET p99 8.75s → 715ms (12 배 개선)*

### Case 3 — *Frontend 9 일 묻힌 사고* ([velero kopia 글의 별편](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug.html))

- *Metric* 은 정상 (CPU 안 튐, 응답시간 안 튐)
- *Log* 도 조용함
- *사용자 게시판* 에 "빈 화면" — *Synthetic monitoring (외부 도메인 served bytes 검증)* 이 모니터링의 *최후 보루*
- *Layer 0 (CI/CD) 의 race* 가 진짜 원인 — Metric / Log / Trace *모두* 잡지 못함

→ *모니터링은 코드 실행 stack 만 본다*. *Layer 0 (배포 파이프라인)* 은 *별도 synthetic check* 가 필요.

---

## 9. *백엔드 개발자가 *코드 단에서* 신경 써야 할 것*

### 9.1 *Histogram metric 을 *기본으로* 깔기*

Spring Boot Micrometer :

```kotlin
@Configuration
class MetricsConfig {
    @Bean
    fun timerCustomizer() = MeterFilter.replaceConfigsAccept { config ->
        config?.merge(DistributionStatisticConfig.builder()
            .percentilesHistogram(true)
            .percentiles(0.5, 0.95, 0.99, 0.999)
            .build()) ?: DistributionStatisticConfig.NONE
    }
}
```

*모든 endpoint 에 p50/p95/p99/p999 histogram 자동 생성*. cost 는 낮음.

### 9.2 *Trace context propagation*

HTTP 헤더의 *traceparent / baggage* 가 *서비스 간 전파* 돼야 분산 trace 가 작동한다. Spring Cloud Sleuth + Brave 또는 OpenTelemetry Java agent 가 자동 처리.

*직접 외부 HTTP client (OkHttp 등) 호출 시 header 전파가 수동 필요* — 흔한 깜빡 실수.

### 9.3 *Slow query log 켜기*

PostgreSQL :

```
log_min_duration_statement = 1000  # 1초 넘는 쿼리 로그
```

Spring Boot + HikariCP :

```yaml
spring.jpa.properties.hibernate.session.events.log.LOG_QUERIES_SLOWER_THAN_MS: 1000
```

*p99 응답시간이 튀면 80% 는 DB 쿼리가 원인*. *slow query log 가 진단의 첫 화면*. 자세한 HikariCP 시간 설정은 [별편 글](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) 참고.

### 9.4 *Endpoint 별 Bulkhead (thread pool 분리)*

[이커머스 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) 글에서 다룬 패턴. 결제 vs 검색 vs 통계의 thread pool 을 분리해 *한쪽 saturation 이 다른쪽 p99 를 못 망치게*.

### 9.5 *Timeout 명시 (cascading default)*

모든 HTTP client / DB / Redis 호출에 *명시적 timeout*. 안 걸면 기본 *수십 초 ~ 무한*. *cascading failure* 의 주범.

---

## 10. *모니터링 시스템의 *한계 — 못 보는 것**

마지막으로 모니터링이 *정의상 못 보는* 것들 :

- **사용자의 주관적 만족도** — 200 ms 도 *느림* 으로 느끼는 사람이 있다
- ***경쟁 서비스의 응답시간*** — 우리 200ms 가 경쟁이 100ms 면 이미 패배
- **클라이언트 시점의 전체 latency** — 서버 응답 50ms 후 *프론트 렌더 5 초* 면 서버 모니터링은 거짓말
- ***아직 안 일어난 사고*** — Predictive monitoring 은 한계. *capacity planning* 의 영역

이게 *모니터링의 철학적 한계*. *진짜 사용자 경험* 은 *browser-side RUM (Real User Monitoring) + Synthetic check + 고객 게시판 + 백엔드 metric* 의 *총합* 이지 백엔드 metric 단독이 아니다.

---

## 11. *교훈*

> *"백엔드 응답시간은 숫자가 아니라 분포다. 분포의 진짜 형태를 보는 시야가 모니터링 시스템의 진짜 가치. 그리고 그 시스템이 *못 보는 것* 을 항상 기억하는 백엔드 개발자가 진짜 SRE 가 된다."*

평균이 조용히 거짓말한다. *p99 가 진실에 가깝다*. *p999 는 돈이 흐르는 곳에서 필수*. 그리고 *모든 측정은 비용과 함정을 갖는다*.

다음 대시보드를 볼 때 — *평균만 보지 말고 분포의 꼬리를 반드시 함께 보자*. 그 꼬리에 *진짜 사용자의 진짜 경험* 이 살고 있다.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [R 은 클러스터에 *없다*](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · [HikariCP 의 5 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) · *백엔드 응답시간 + 모니터링 (현재 글)*

*이 글은 sparta-msa-project / settlement / helm-deploy 의 운영 경험과 [etcd HDD trap](/2026/06/06/etcd-fsync-hdd-trap-kube-api-error-budget-burn.html), [velero kopia 좀비 잡](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug.html), [이커머스 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) 글들의 *관측 가능성 관점* 을 종합.*
