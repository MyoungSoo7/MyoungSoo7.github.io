---
layout: post
title: "*APM* 과 *응답 시간 분포* — *백엔드 서버 개발자* 의 시각 에서 *왜 평균 이 거짓말 인가*"
date: 2026-06-21 19:30:00 +0900
categories: [observability, apm, backend, performance]
tags: [apm, latency, p99, percentile, hdr-histogram, t-digest, opentelemetry, micrometer, new-relic, datadog, pinpoint, scouter, elastic-apm, coordinated-omission, spring-boot]
---

> *"우리 평균 응답 200ms 인데요"*. *그런데 사용자 한 명* 이 *Slack* 으로 *"왜 *오늘 결제 가 *10 초씩 걸리냐"* 한다.
>
> *둘 다 사실*. *평균 이 200ms 라는 것* 이 *99 명 이 *50ms* 인데 *1 명 이 *15,000ms* 라는 *극단 적 분포* 와 *수학적 으로 동일* 할 수 있다.
>
> *백엔드 서버 개발자* 의 *책임* 은 *평균 을 보는 것* 이 *아니라 *분포* 를 보는 것*. 그리고 *그 분포 의 *long tail* 이 *왜 길어졌는지* 를 *추적 가능* 하게 만드는 것 — 그 도구 가 *APM*.

이 글은 *9 년차 백엔드 개발자* 의 시각 에서 *APM 의 역할*, *응답 시간 분포 의 수학*, *분위수 통계 의 함정*, *실전 도구 비교*, *Spring Boot 에 *바로 붙이는 코드*, *내 실전 사고 사례* 를 *밀도 있게* 정리한다.

함께 보면 좋은 *자매편* :
- *[Prometheus + Grafana — 메트릭 시각화](/2026/06/19/prometheus-grafana-metrics-visualization.html)* — *왜 이 4 가지 그래프 만 보면 *대부분 보이는지*
- *[Backend 의 *Latency 추적*](/2026/06/10/backend-latency-monitoring.html)* — *Hop 별 분해 의 첫걸음*
- *[비동기 연동 과 인프라](/2026/06/16/async-integration-and-infrastructure.html)* — *Outbox 의 *느린 꼬리* 의 원인*

이 글은 *그 위에 *분포 의 수학 + APM 의 도구 지형* 을 *덧 댄다*. *대시보드 위 의 *분위수 그래프* 가 *왜 그렇게 생겼는지* 를 *완전히 풀어 본다*.

---

## TL;DR — *한 줄 결론*

> *평균* 은 *백엔드 의 *진짜 SLA* 를 *체계적으로 가린다*. *p95 / p99 / p99.9* 만이 *사용자 가 체감하는 시간* 의 *정직한 표현*. *그 분포 를 *정확히 측정* 하려면 *HDR Histogram / t-digest* 같은 *분위수 자료 구조* 가 필요하고, *그 분포 를 *추적 가능* 하게 만들려면 *Trace ID + Span 의 *분산 트레이싱* (OpenTelemetry) 이 필요*. *Spring Boot + Micrometer + OTel agent + Prometheus + Grafana / Jaeger* 의 *오픈소스 스택* 이 *지금 의 표준 답안*. 상용 (Datadog/New Relic) 은 *비용 vs 통합 시야* 의 trade-off.

---

## 1. *왜 *평균* 이 *거짓말 의 표준 형태* 인가**

### 1.1 *평균 의 *수학적 정의 가 *백엔드 와 안 맞는다**

평균 = 모든 응답 시간 의 합 / 요청 수.

이 정의 의 *조용한 가정* — *모든 응답 시간 이 *대칭 적 정규 분포* 를 따른다*. 그래야 *평균 = 중앙값 = 최빈값*.

*현실 의 응답 시간* :
- *대다수 (95~99%)* — *수십 ms* 의 *좁고 빠른 봉우리*
- *나머지 (1~5%)* — *수백 ms ~ 수십 초* 의 *긴 꼬리*

*수학적 으로 *log-normal 또는 Pareto 분포*. *오른쪽 으로 *심하게 치우친 (right-skewed) *비대칭*.

> 이런 분포 에서 *산술 평균* 은 *long tail 의 *극단 값* 에 *무방비 로 끌려간다*. 1 % 의 *15 초 요청* 이 *평균 을 *수백 ms 단위* 로 *왜곡*.

### 1.2 *백엔드 의 *long tail 의 *발생원* 6 가지**

내 *9 년* 의 경험 으로 *꼬리 를 길게 만드는 *주범* * :

1. **GC pause** — *Java 의 *Stop-The-World*. *G1 의 Mixed GC 가 *수십 ~ 수백 ms*. *ZGC 도 *드물게 *수 ms*.
2. **DB connection 대기** — *HikariCP 풀 고갈* 시 *대기 큐* — *밀린 요청 의 *합산 지연*.
3. **외부 API 호출** — *PG / 카카오톡 / SMS / OCR* 의 *간헐 적 *수 초 지연*. *circuit breaker 미적용 시 *전체 풀 점거*.
4. **N+1 쿼리** — *평소 1 쿼리 인데 *특정 데이터 의 *400 쿼리 폭발*.
5. **Cold start** — *JIT 미온, *클래스 로딩, *connection 풀 prewarm 안 됨*, *Caffeine miss*.
6. **Lock contention** — *DB 의 *row lock*, *Java 의 *synchronized*, *분산 락 의 *재시도*.

이 6 가지 중 *어느 것* 도 *평소 에는 *문제 없음*. *문제 가 생기는 순간* 의 *특정 요청* 만 *수십 배 의 지연*. *평균 으로 보면 *조용히 묻힘*.

### 1.3 *유명 한 *Amazon 의 *50ms 의 1 %*

*Amazon 의 *2007 년 *기록* (Greg Linden) — *추가 100ms 지연 마다 *매출 1% 감소*. *이 데이터 의 *원천* 은 *분위수 측정 도구* 였다. *평균 으로 봤다면 *그 인과 가 *영원히 안 보였다*.

*우리 의 백엔드* 도 같다. *p99 의 *200ms 차이* 가 *체감 만족 의 *결정 적 차이*. *평균 이 *말해주지 않는 진실*.

---

## 2. *분위수 (Percentile) — *분포 의 *정직한 언어**

### 2.1 *정의 와 *한 줄 의미**

| 분위수 | 의미 | 백엔드 적 해석 |
|---|---|---|
| **p50 (중앙값)** | *요청 의 절반 이 이 시간 안 에 응답* | *전형 적 사용자 의 체감* |
| **p95** | *95 % 의 요청 이 이 시간 안* | *조금 늦은 사용자 의 체감* |
| **p99** | *99 % 가 이 시간 안. 100 명 중 1 명* | *불만 게시판 의 체감* |
| **p99.9** | *1,000 명 중 1 명. *long tail 의 *심장*. | *서비스 의 *진짜 SLA 기준* |
| **p99.99** | *10,000 명 중 1 명. *극단 적 사용자*. | *고가용성 서비스 의 SRE 영역* |

### 2.2 *p99 가 *제일 정직한 *백엔드 SLA**

*9 년차 경험* 으로 — *모든 백엔드 SLA 는 *p99 기준* 으로 *작성 해야 한다*.

이유 :
- *p95* — *long tail 의 *너무 많이 숨김*. *5 % 의 *나쁜 경험* 이 *그대로 묻힘*.
- *p99* — *균형 점*. *99 % 가 행복 한 SLA = *대부분 사용자 행복*. *그 1 % 는 *내가 *식별 가능 / 사과 가능*.
- *p99.9* — *극단 적 정확성*. *측정 의 *통계 적 노이즈* 가 *크다*. *수십만 건 데이터* 필요.

> *내 settlement 의 *결제 API SLA = *p99 < 500ms*. *p95 가 아니라 *p99*. *p95 로 두면 *5 % 의 *느린 결제 가 *조용히 누적* 됨.

### 2.3 *분위수 의 *수학적 *조심 할 점**

#### *분위수 는 *평균낼 수 없다*

```
서비스 A 의 p99 = 200ms
서비스 B 의 p99 = 300ms
→ A+B 합쳐서 p99 = ???  ← 250ms 아님!!!
```

분위수 *합산 의 진실* — *원본 분포 가 필요*. *합쳐서 *p99 가 *200~500ms 사이 어디 든 가능*. *Grafana 의 *평균 패널* 이 *p99 를 평균* 내면 *통계적 으로 의미 없음*. *반드시 *HDR Histogram 의 *원본 버킷 합* 으로 재계산*.

#### *분위수 는 *시간 별로 *나눌 수 없다*

```
1 분간 p99 = 200ms
2 분간 p99 = 300ms
→ 2 분 합쳐서 p99 = ???  ← 250ms 아님!!!
```

*같은 이유*. *반드시 *히스토그램 의 합산* 후 재계산*.

이게 *Prometheus 의 `histogram_quantile()` 함수* 의 *진짜 의미*. *분위수 자체 가 아니라 *히스토그램 버킷* 을 저장하고 *조회 시 점에 *분위수 계산*. *이렇게 해야 *합산 / 시간 윈도우 가능*.

### 2.4 *Coordinated Omission — *측정 의 *조용한 거짓말**

*Gil Tene* 이 명명한 *분위수 측정 의 *치명 적 함정*.

전형 적 시나리오 :
- *부하 테스트 가 *RPS 100 *유지 시도*.
- *서버 가 *느려져서 *응답 이 *10 초 늦어짐*.
- *부하 테스트 클라이언트 는 *그 10 초 동안 *새 요청 을 *덜 보냄* (왜냐하면 *바쁨*).
- *결과 — *측정 안 된 *수백 개 의 *늦은 요청* 이 *통계 에서 누락*.

*해결* — *시작 시간 (intended start time) 을 *기준* 으로 측정. *기다린 시간 까지 포함*. *이게 *wrk2 / HdrHistogram / Gatling 의 *지원 이유*.

> *JMeter 의 *기본 측정 이 *coordinated omission* 에 *취약*. *p99 가 *실제보다 *극단 적으로 낙관 적*. *부하 테스트 결과 신뢰 할 때 *반드시 확인*.

---

## 3. *분포 를 *제대로 저장 하는* 자료 구조*

*"매 요청 의 응답 시간 을 다 저장"* — *디스크 폭발*. *수십억 건 요청 의 *수십 GB 데이터*.

*그래서 *근사 압축 자료 구조* 가 필요하다. 4 가지 후보 :

### 3.1 *naive 평균 + 표준편차 — *제일 흔하고 *제일 쓸모 없는**

장점 : 메모리 *상수*.
단점 : *분위수 추론 불가*. *분포 모양 모름*. *대부분 의 *Prometheus 기본 메트릭* 이 이렇게 *잘못 됐다*.

### 3.2 *Histogram (고정 버킷)*

```
[0~10ms]   [10~50ms]   [50~100ms]   ...   [10s~]
   count       count       count               count
```

장점 :
- *합산 가능* (버킷 단위 더하기).
- *시간 윈도우 합산 가능*.
- *Prometheus 의 `histogram_quantile()` 가 *이걸 가정*.

단점 :
- *버킷 경계 가 *고정* — *p99 의 정확도 가 *낮음*. *적은 버킷 = 큰 오차*.
- *너무 많은 버킷 = 메모리 폭발*.

### 3.3 *HDR Histogram (High Dynamic Range)*

*Gil Tene 의 *고급 자료 구조*. *지수 적 버킷 + 정밀도 보장*.

```
1 µs ~ 1 분 의 *7 자릿수 범위* 에서 *0.1 % 의 *상대 오차 보장*.
메모리 = 수십 KB.
```

장점 :
- *극단 적 정확*.
- *합산 가능*.
- *Java 에 *공식 라이브러리*. *Micrometer 도 *옵션 적 지원*.

단점 :
- *합산 시 *값 범위 가 다르면 *주의*.
- *시각화 도구 의 *직접 지원 적음* (보통 *분위수로 변환 후 송신*).

### 3.4 *t-digest*

*Ted Dunning 의 *분위수 추정 알고리즘*.

장점 :
- *극단 분위수 (p99.9, p99.99) 의 *상대 적 정확도 *매우 높음*.
- *합산 가능*.
- *Datadog / Elasticsearch / Cassandra* 등 다수 채택.

단점 :
- *알고리즘 의 *수학적 복잡도*.
- *Java 의 *공식 라이브러리 가 *상대 적으로 적음*.

### 3.5 *선택 지침*

| 상황 | 권장 |
|---|---|
| Prometheus + Grafana 기본 | *Histogram* (`Timer`, `histogram_quantile`) |
| 정밀한 *p99.9* 가 *비즈니스 SLA* | *HDR Histogram* |
| Datadog / Elastic APM | *t-digest* (도구 가 자동) |
| 그냥 *대시보드 의 *p99 라인* 만 | *Histogram* 충분 |

---

## 4. *APM 의 *3 가지 축* — *Metric / Trace / Log**

APM 은 *추적 가능 한 관측* 의 *우산 용어*. *3 가지 *데이터 형 의 통합* :

### 4.1 *Metric — *집계 된 *시계열**

- *수십억 요청* 을 *수치 합산* 으로 *압축*. *분위수 / 처리량 / 에러율 / GC time*.
- *시각화 — *Grafana, Datadog 대시보드*.
- *질문 — *"지난 1 시간 의 p99 가 어땠지?"*

### 4.2 *Trace — *한 요청 의 *Hop 별 *시간 분해**

- *HTTP 요청 1 건* 이 *내부 5 개 마이크로서비스 + 3 개 DB + 2 개 외부 API* 를 *돌아 다닐 때*, *각 Hop 의 시간* 을 *한 묶음* 으로 추적.
- *시각화 — *Jaeger UI 의 *waterfall*, *Datadog APM 의 *flame graph*.
- *질문 — *"이 요청 이 *왜 *3 초 걸렸나?"*

### 4.3 *Log — *문맥 적 *정확한 사건**

- *비즈니스 로직 의 *흔적*. *예외 의 *스택 트레이스*.
- *시각화 — *Kibana / Loki / Splunk*.
- *질문 — *"왜 *이 사용자 의 *이 요청 이 *실패 했나?"*

> *3 가지 의 *통합 의 핵심* — *Trace ID 의 일관성*. *Metric 의 *p99 가 튄 시점* 에서 *그 시간대 의 *느린 trace 한 건* 을 찾고, *그 trace 의 *각 span* 의 *로그 를 *문맥 적으로 추적*.

이게 *Datadog / New Relic 의 *비싼 값* 의 *진짜 정체* — *셋 의 *자동 연결*.

---

## 5. *APM 도구 지형 — *6 가지 옵션 비교**

### 5.1 *국내 산 — *Pinpoint / Scouter**

| | Pinpoint | Scouter |
|---|---|---|
| 출신 | Naver (오픈소스) | LG CNS → 오픈소스 |
| 데이터 저장 | HBase | 자체 file storage |
| 강점 | *호출 흐름 의 *깊은 시각화*, *대용량 분산* | *경량, 빠른 셋업, JVM 지표 풍부* |
| 약점 | *셋업 복잡 (HBase + Zookeeper)* | *시각화 노후* |
| 적합 | 대형 SI 의 *수십 ~ 수백 인스턴스* | *중소 규모 의 *빠른 도입* |

### 5.2 *글로벌 상용 — *New Relic / Datadog / Dynatrace**

| | New Relic | Datadog | Dynatrace |
|---|---|---|---|
| 가격 | *호스트 / 사용량 기반* | *호스트 + 데이터 양* (악명 ↑) | *프리미엄 (가장 비쌈)* |
| 강점 | *통합 UX, 분산 트레이싱 의 *원조* | *클라우드 통합, 알림 의 풍부함* | *AI 자동 인사이트 (Davis)* |
| Spring Boot 통합 | *에이전트 첨부 → 즉시* | *에이전트 + Micrometer 변환* | *OneAgent 자동 계측* |

### 5.3 *오픈소스 — *OpenTelemetry 기반**

*2026 년 의 *대세*. *벤더 락인 탈피 + 표준 SDK*.

```
Spring Boot 앱
  ↓ (Micrometer / OTel SDK)
OTel Collector  ← 통합 변환 / 샘플링 / 라우팅
  ↓
+----------------+------------------+-------------+
|                |                  |             |
Prometheus     Tempo / Jaeger     Loki         (선택적으로 Datadog 등)
(메트릭)         (트레이스)         (로그)
  ↓                ↓                ↓
              Grafana — 통합 시각화
```

*장점* — *Prometheus + Grafana + Loki + Tempo* 의 *Grafana 스택* 으로 *3 종 통합*. *벤더 락인 없음*.

*단점* — *셋업 의 부하 (특히 *retention / 샘플링 / *알람 의 *직접 구성*)*. *Datadog 의 *바로 됨* 에 비하면 *학습 곡선*.

> *내 K3s 홈랩 패턴* — *Prometheus + Grafana + Loki + Tempo + OTel Collector*. *완전 무료 *셀프 호스팅*. *셋업 *수십 시간* 이지만 *연 *수백만 원 절약*.

### 5.4 *Elastic APM*

ELK 스택 의 일부. *Elasticsearch 가 이미 있다면 *합리적*. *고유 한 *trace + log 의 *동일 데이터 베이스* 결합 이 *강점*.

---

## 6. *Spring Boot 에 *APM 붙이기 — *실제 코드**

### 6.1 *Micrometer 의 *Timer*

```java
@RestController
@RequiredArgsConstructor
class PaymentController {
    private final MeterRegistry meterRegistry;
    private final PaymentService paymentService;
    private final Timer paymentTimer;

    public PaymentController(MeterRegistry registry, PaymentService svc) {
        this.meterRegistry = registry;
        this.paymentService = svc;
        this.paymentTimer = Timer.builder("payment.request")
            .description("Payment API latency")
            .publishPercentiles(0.5, 0.95, 0.99, 0.999)   // ← 분위수 명시
            .publishPercentileHistogram()                   // ← Prometheus 용 버킷
            .serviceLevelObjectives(
                Duration.ofMillis(100),
                Duration.ofMillis(500),
                Duration.ofMillis(1000)
            )                                               // ← SLO 추적
            .register(registry);
    }

    @PostMapping("/pay")
    public PaymentResult pay(@RequestBody PaymentRequest req) {
        return paymentTimer.record(() -> paymentService.execute(req));
    }
}
```

핵심 :
- `publishPercentiles` — *Micrometer 내장 *분위수 계산*.
- `publishPercentileHistogram` — *Prometheus 호환 *히스토그램 버킷* 생성 (`histogram_quantile()` 사용 가능).
- `serviceLevelObjectives` — *SLO 추적 용 *boolean 카운터*. *Prometheus 알람 의 *기반*.

### 6.2 *`application.yml` 의 *전역 설정**

```yaml
management:
  endpoints:
    web:
      exposure:
        include: prometheus,health,metrics
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
      percentiles:
        http.server.requests: 0.5,0.95,0.99,0.999
      slo:
        http.server.requests: 100ms,500ms,1s
    tags:
      application: ${spring.application.name}
      env: ${ENV:dev}
```

이 한 블록 으로 *모든 컨트롤러 메서드 의 *분위수 + 히스토그램 + SLO* 자동 생성.

### 6.3 *OpenTelemetry Java Agent — *코드 0 줄 의 *분산 트레이싱**

```sh
# 다운로드
$ curl -L -o opentelemetry-javaagent.jar \
  https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar

# 실행
$ java -javaagent:./opentelemetry-javaagent.jar \
       -Dotel.service.name=payment-service \
       -Dotel.exporter.otlp.endpoint=http://otel-collector:4317 \
       -jar payment.jar
```

*결과* — *Spring MVC / WebClient / JDBC / Redis / Kafka 의 *호출* 이 *전부 자동 으로 *span 으로 캡처*. *코드 한 줄 안 바꿈*. *마법 의 이름 은 *bytecode 변환*.

### 6.4 *Prometheus 쿼리 — *p99 의 *시각화**

```promql
# HTTP 요청 의 p99 (5 분 윈도우)
histogram_quantile(0.99,
  sum by (le, uri) (
    rate(http_server_requests_seconds_bucket{
      application="payment-service",
      uri!~".*/actuator.*"
    }[5m])
  )
)

# SLO 위반율 — 500ms 초과 비율
1 - (
  sum(rate(http_server_requests_seconds_bucket{le="0.5"}[5m]))
  /
  sum(rate(http_server_requests_seconds_count[5m]))
)
```

이 두 쿼리 만으로 *Grafana 의 *핵심 두 패널* — *p99 라인* + *SLO 위반율* — 완성.

---

## 7. *내 *9 년 경험* 의 *분포 가 *진짜 사고 를 잡은* 5 가지 사례*

### 7.1 *settlement 의 *p99 가 *야간 에 만 *3 초**

평균 응답 *180ms 평소*. *야간 (02~04 시)* 의 *p99 만 *3 초로 *튐*.

*평균 만 봤다면* — *전혀 안 보였다*. *p99 차트 가 *시간대 별 패턴* 을 *드러냄*.

원인 — *야간 의 *배치 잡 의 *DB 락 점유*. *결제 트랜잭션 이 *밀려서 *대기*. *batch 의 *작은 트랜잭션 단위 화* 로 해결.

### 7.2 *sparta-msa 의 *p99.9 만 *튀는 GC 사고**

p50 *15ms*, p95 *40ms*, p99 *80ms* — *건강 해 보임*.
p99.9 *2,300ms* — *수상*.

*GC 로그 와 시간 대 일치*. *G1 의 *Mixed GC 가 *주기 적 2 초 pause*.

해결 — *ZGC 로 변경 + Heap 크기 조정*. *p99.9 가 *200ms 이하 로 *극적 감소*.

> *p99 까지 만 봤다면 *영원히 못 잡았던* 사고. *p99.9 의 가치*.

### 7.3 *외부 PG API 의 *간헐 적 *10 초 지연**

p99 *400ms*. p99.9 *11,000ms*.

*trace 추적 — *대부분 의 *long tail 이 *PG 의 *카드 인증 API 응답 대기*.

해결 — *circuit breaker (Resilience4j) + fallback*. *10 초 이상 시 *바로 *retry-later 응답*.

### 7.4 *N+1 의 *p99 폭주**

*신규 정산 화면* 의 *p99 가 *주말 에 만 *15 초*.

*trace 본 결과* — *한 요청 이 *DB 470 회 호출*. *전형 적 N+1*.

해결 — *JPA fetch join + DTO projection*. *p99 가 *200ms 로 떨어짐*.

> *trace 의 *flame graph 가 *없었다면 *코드 어디서 N+1 인지* *영원히 추측*. *APM 의 *진짜 가치 는 *이 시각화*.

### 7.5 *cold start 의 *startup probe 실패**

배포 직후 *5 분 동안 *p99 가 *4 초*. *5 분 뒤 *정상*.

원인 — *JIT 미 워밍업 + connection 풀 init + Caffeine miss*.

해결 :
- *Spring Boot 의 *@WarmUp 작업*. *application context init 시 *주요 쿼리 *프리 콜*.
- *Kubernetes 의 *startupProbe* + *readinessProbe 의 *충분한 *initialDelaySeconds*.
- *AOT 컴파일 (GraalVM)* 검토.

p99 의 *시간 패턴 (배포 직후 만 튐)* 이 *원인 진단 의 *결정 적 단서*.

---

## 8. *알람 의 *철학 — *분포 기반 의 *5 가지 규칙**

평균 기반 알람 의 *3 가지 흔한 오류* :

1. *평균 응답 > 500ms 알람* — *long tail 이 *평균 을 *왜곡*. *오발 + 누락 양쪽*.
2. *에러율 > 1 % 알람* — *백 엔드 의 *5xx 만 봄*. *4xx 의 사용자 불만 + 200 OK 의 *느린 응답* 누락*.
3. *동시 접속 > N 알람* — *부하 의 *상한 만 봄*. *분포 의 *나쁜 꼬리 가 *원인 일 때 *무관*.

대신 *분포 기반 *5 가지 규칙* :

1. **SLO 위반율 > 0.5 %** — *p99 SLO (예: 500ms) 초과 비율 의 *long-window burn rate*. *Google SRE 의 *공식 패턴*.
2. **p99.9 의 *급격한 변화*** — *전 주 동일 시간 대비 *2 배 이상 튐* → 알람. *베이스라인 비교*.
3. **에러율 의 *복합 정의*** — *5xx + 4xx 의 일부 (예: 429, 408) + 200 의 *임계 초과 응답** 의 합 = *체감 에러*.
4. **분위수 간 갭 의 갑작스러운 확장** — *p50 은 정상 인데 *p99 가 튀면 *분포 가 *비대칭 화*. *long tail 의 *새 원인 발생*.
5. **trace 의 *느린 span 의 *원인 분포*** — *지난 1 시간 의 *p99 trace 들 의 *공통 원인 (DB / 외부 API / GC)*. *주범 의 변화 감지*.

이 5 가지 가 *분포 기반 SRE 의 *근간*.

---

## 9. *결론 — *백엔드 개발자 의 *3 가지 의식 변화**

### 9.1 *"평균 응답"* 이라는 단어 를 *입에서 지우자*

매주 보고 / Slack / 회의 — *"평균 응답 200ms 입니다"* 라는 말 자체 를 *p99 응답 200ms 입니다* 로 바꾸자.

*조직 의 *언어 가 바뀌면 *사고 의 *기준* 이 바뀐다*. *기준 이 바뀌면 *알람 / 대시보드 / SLO* 가 *전부 따라 옴*.

### 9.2 *대시보드 의 *기본 그래프 4 개**

내 *Grafana 첫 페이지* 의 *고정 패널*:

1. *RPS (요청 률)* — *처리량 의 베이스*
2. *p50 / p95 / p99 라인 (한 차트 에 3 줄)* — *분포 의 변화*
3. *에러율 (5xx + 임계 초과)* — *사용자 의 *진짜 *실패 율*
4. *SLO 위반율 의 *burn rate** — *알람 의 기반*

이 4 개 만 *벽 에 띄워 두면 *서비스 의 *건강 의 *80 %* 가 보임.

### 9.3 *trace 의 *습관 화**

*p99 튀면 *바로 *그 시간대 의 *느린 trace 한 건* 을 *Jaeger 에서 열어 *flame graph 를 본다*.

*5 분 의 *습관* 이 *디버깅 시간 의 *수 시간 단축*. *trace 가 *추측 을 *증거 로 바꾼다*.

---

## 다음 으로 *권 하는 읽기**

- *Google SRE Book — *Chapter 4 (Service Level Objectives)*. *분포 기반 SLO 의 *교과서*.
- *Gil Tene 의 *"How NOT to Measure Latency"* 강의*. *Coordinated Omission 의 *진수*.
- *OpenTelemetry 공식 문서* — *Java 의 *자동 + 수동 계측 의 *모든 패턴*.
- *Brendan Gregg 의 *"Systems Performance"* 2 nd ed.*. *USE / RED 의 *원작자*.
- 자매편 — *내 이전 글 [Prometheus + Grafana 메트릭 시각화](/2026/06/19/prometheus-grafana-metrics-visualization.html)* 와 *[Backend Latency 추적](/2026/06/10/backend-latency-monitoring.html)*.

*다음 글* — *분산 트레이싱 의 *내부 — *Trace ID 의 전파 / 샘플링 의 수학 / OpenTelemetry Collector 의 라우팅* 의 *3 부 시리즈* — 곧.
