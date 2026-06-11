---
layout: post
title: "*백엔드 개발자가 *진짜 *신경 써야 하는 *처리량 (TPS)* — *100 → 1K → 10K → 100K* 의 *단계별 병목 / 실전 사례 6 건 / 도구 (k6 + JMeter + Pinpoint + Grafana) 사용법* 의 *postmortem 압축***"
date: 2026-06-10 17:00:00 +0900
categories: [backend, performance, sre, kubernetes, msa]
tags: [tps, rps, throughput, performance, k6, jmeter, pinpoint, prometheus, grafana, jvm-tuning, hpa, db-connection-pool, redis, kafka, hexagonal, postmortem]
---

이 글은 *"우리 시스템 TPS 가 *얼마야?"* 라는 질문에 *백엔드 개발자가 *정확히 답할 수 있게* 하는 *현장 가이드* 다. *TPS 정의 → 단계별 병목 → 실전 사례 6 건 → 측정/부하 테스트 도구 사용법 → 함정과 학습 압축* 의 *5 layer* 로 정리.

읽고 가셔도 좋은 분:
1. *백엔드 1~3 년차* — *부하 테스트* 한 번도 안 해본 사람. *어디서부터 시작할지* 막막한 사람.
2. *백엔드 시니어* — *TPS 1K → 10K 의 *벽* 에 *부딪힌 사람*. *DB / 캐시 / Kafka 의 *각자의 한계 가 *어디서 휘는지* 가 궁금한 사람.
3. *SRE / 인프라* — *부하 테스트 도구 의 *선택 기준* (*JMeter vs k6 vs wrk vs vegeta*) 이 궁금한 사람.

---

## TL;DR

> *TPS 100 → 1K → 10K → 100K* 각 단계가 *완전히 다른 시스템* 을 요구. *DB pool / Redis / Kafka partition / JVM heap / HPA* 의 *5 layer 가 각자의 *천장* 에서 휜다. *측정 없이 추측하면 *반드시 틀린다* — *k6 (간단) + JMeter (정밀) + Pinpoint (call tree) + Grafana (시계열)* 의 *4 도구* 가 *현장의 표준*.

**한 표로**:

| 단계 | 대표 워크로드 | 1차 병목 | 해법 |
|------|------------|---------|------|
| **100 TPS** | 사내 admin, B2B API | *없음* — 기본 Spring Boot 로 충분 | tuning 불필요 |
| **1K TPS** | 중소 이커머스 | DB connection pool | HikariCP `maximum-pool-size` 튜닝 |
| **10K TPS** | 대형 이커머스 / 메신저 | DB write contention + Redis network | read replica + Redis pipeline + Kafka 비동기 |
| **100K TPS** | 결제 PG / 게임 인증 | Single DB 한계 | sharding + CQRS + read-only projection |
| **1M+ TPS** | 광고 트래픽 / IoT 시세 | Linux kernel / NIC / GC | DPDK / Reactive / 언어 변경 (Java → Rust / C++) |

---

## 0. *RPS / TPS / QPS — *용어 정리***

> 단어 *3 개가 *혼용* 되는데 *정확한 의미가 *서로 다르다*. *측정 전에 *기준을 합의* 안 하면 *팀 간 *수십 배 차이* 의 *해석 오류* 발생.

| 용어 | 단위 | 무엇을 세는가 | 예시 |
|------|------|---------|------|
| **RPS** (Requests / sec) | HTTP request | *클라이언트가 보낸 요청 수* | GET /products = RPS 1 |
| **TPS** (Transactions / sec) | *비즈니스 단위* 트랜잭션 | *완료된 비즈니스 작업 수* | 주문 1건 완료 = TPS 1 (5개 API 호출 = RPS 5) |
| **QPS** (Queries / sec) | DB query | *DB 가 처리한 쿼리 수* | 주문 1건 = QPS ~10-30 (multiple SELECT/INSERT) |

**예시**:
```
주문 트랜잭션 1건:
  - 1 TPS  (비즈니스)
  - 5 RPS  (5 API 호출 : 카트 조회 / 재고 확인 / 결제 / 주문 생성 / 알림)
  - 30 QPS (다수 SELECT + INSERT + UPDATE)
```

> *팀 회의에서 *"우리 TPS 5K 야"* 라는 말이 *RPS / QPS* 와 *혼동* 되면 *부하 계산이 *6 배 차이* 난다. *측정 시 *분명히 명시*.

---

## 1. *단계별 천장 — *100 → 1K → 10K → 100K***

### 1.1 *100 TPS — *튜닝 불필요***

- 기본 Spring Boot + Tomcat (default 200 worker thread) 가 *200 RPS 까지 *그냥 처리*.
- DB connection 도 *HikariCP default = 10* 이 *충분*.
- *측정 안 해도 됨*. *기능 구현이 *진짜 부담*.

**대표 사례 (내 settlement 프로젝트의 *settlement-service*)** — *월 정산 배치* 라 *peak 시간이 *24 시간 분산*. *평균 *50 TPS / peak *200 TPS*. *지금까지 *튜닝 0회*.

### 1.2 *1K TPS — *DB connection pool 가 *첫 천장***

이 단계에서 *대부분 첫 *부하 테스트* 한다. 알게 되는 진실:

> *HikariCP max pool = 10 인 상태에서 *200 동시 요청 / 평균 50ms DB call* → *10 pool 가 *50ms 마다 200 회 turnover 필요 → 한계*. *connection wait timeout 폭발*.

**해법 1 — Pool size 늘리기**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 50      # default 10 → 50
      minimum-idle: 20
      connection-timeout: 3000   # 3초 wait 후 fail-fast
```

> **함정** — pool size *너무 크게* (예: 200) 잡으면 *DB 측 *connection 수 천 *limit* 충돌. *DB 의 max_connections* 와 *애플리케이션 인스턴스 수* × *pool size* 가 *서로 맞아야 함*.

```
계산 공식:
  DB max_connections >= (instances × pool_size) + (DBA 관리용 여유 ~ 30)
  
예: 인스턴스 10 × pool 50 = 500
   → PostgreSQL max_connections >= 530
```

**해법 2 — 쿼리 자체 빠르게**
- 인덱스 누락 검사 — `EXPLAIN ANALYZE`
- N+1 잡기 — `@EntityGraph`, JPA fetch join
- *읽기 위주는 *read replica* 로 분리

**실전 사례 — *ssgb2e (신세계 B2E 이커머스) 정산 배치***:

```sql
-- 일일 정산 배치 — 1 분 1회, 5 만 건 처리
INSERT INTO tbl_order_detail_statistics (...) 
SELECT ... FROM tbl_orderplist OP
LEFT JOIN tbl_orderinfo OI ON OI.oikey = OP.oikey
WHERE OP.ord_date >= TRUNC(SYSDATE - 1)
```

→ *1 회 *insert ~ 5 만 row*. *bulk insert 라 평균 *10K TPS 효과*. 단, *동시 트랜잭션 *3 개 이상이면 *PK lock contention*. *시리얼 처리로 묶음*. (관련 글: [PR #1 멱등성](/2026/06/07/python-tutor-cli-web-shared-grader-builtins-trap/))

### 1.3 *10K TPS — *Redis / Kafka / read replica 의 *조합 필요***

*DB 1 노드의 *write 한계* 가 *통상 5-15K TPS*. 그 이상은 *다른 layer* 가 필요.

**Layer 1 — Redis 캐시**
```java
@Cacheable(value = "product", key = "#id", cacheManager = "redisCacheManager")
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

→ *Cache hit 률 90%* 면 *DB call 90% 감소 = 10× throughput*.

**Layer 2 — Kafka 비동기**
```
[사용자] → [API server] → [Kafka topic] → [Worker]
              ↓ (즉시 응답 — 200ms)
           "주문 접수 됨"
                          ↓ (비동기 처리 — 1-2s)
                     실제 결제 / 재고 차감 / 정산 적재
```

→ *사용자가 *기다리는 *동기 부분 *짧게*. *나머지는 *비동기 처리량* 으로 *세분화*.

**Layer 3 — Read replica 분리**
```yaml
spring:
  datasource:
    write:
      url: jdbc:postgresql://pg-master:5432/db
    read:
      url: jdbc:postgresql://pg-replica:5432/db
```

→ *대부분 트래픽이 *read* 라 (보통 80-90%) *read replica 1-3 대로 *쉽게 5-10× scale*.

**실전 사례 — *Lemuel 이커머스 의 *주문 API***:

내 *settlement* 프로젝트는 *주문/결제* 가 *order-service*, *정산이 *settlement-service* 로 *MSA 분리*. *Outbox 패턴 으로 *write* 가 *DB tx + outbox INSERT* 후 *poller 가 *Kafka 발행*. *Triple Idempotency* 로 *settlement 의 *멱등 수신*. 결과:

```
order-service       동기 (HTTP 요청) — 응답 < 200ms
   ↓
outbox_events 적재 (같은 DB tx 안 — 원자성)
   ↓ (2초 poll)
Kafka payment.captured
   ↓
settlement-service  (Triple Idempotency 로 안전 처리)
```

→ *주문 자체는 *3K TPS 가능*. 정산 처리는 *Kafka backpressure 로 *자연 평탄화* (5K → 1K TPS 로 *큐가 분산*).

### 1.4 *100K TPS — *Single DB 의 *마지막 한계***

이 단계는 *진짜 *대형 서비스*. *PG 결제 회사 (Toss / KCP / NHN Pay)*, *대형 메신저*, *광고 트래픽 처리*.

**필수 패턴**:

1. **Sharding** — DB 를 *Key 단위로 *N 개 인스턴스*. *userId % N = shard*.
2. **CQRS** — Write / Read 모델 *완전 분리*.
3. **Read-only Projection** — *MSA 간 *데이터 공유 *DB 직 read* (내 settlement 의 패턴).
4. **Event Sourcing** — Mutable state 가 아니라 *event stream 의 *append-only*.

**실전 사례 — *lemuel-quant-core 의 *market-feed***:

암호화폐 시세 수집 모듈. *Binance / Upbit / Bithumb* 의 *WebSocket* 으로 *수 천 / 초* 의 *틱 데이터*. *C++ 로 작성* 한 이유:

```
Java + GC 모델:
  GC pause 50ms 동안 *시세 100 건 missing*
  
C++ + zero-allocation:
  GC pause = 0
  *모든 틱 데이터 *순차 처리 보장*
```

> *100K TPS 이상* 은 *언어 / runtime 자체가 *천장*. *Java / Python* 으로 *fundamental 한계*. *Rust / C++ / Go* 로 *언어 변경* 검토.

### 1.5 *1M+ TPS — *kernel / NIC 의 영역***

여기는 *애플리케이션 코드 한계* 가 아니라 *Linux kernel TCP stack* 의 한계. *DPDK / eBPF / Reactive* 같은 *시스템 프로그래밍* 영역. *광고 / 게임 / IoT* 정도.

대부분 *백엔드 개발자* 는 *100K TPS 까지만 *현실적 *고민 대상*. 이 글 의 *주된 *대상도 *그 범위*.

---

## 2. *실전 사례 6 건 — *내 프로젝트의 *진짜 *부하 패턴***

### Case 1 — *settlement 의 *주문 + 결제 + 정산* MSA*

| 항목 | 값 |
|------|----|
| 평균 TPS | ~500 |
| Peak TPS (블프, 명절) | ~3000 |
| 1차 병목 | DB connection pool (HikariCP) |
| 해법 | pool=50 + Outbox 비동기 분리 + read replica |
| 도구 | k6 + Prometheus + Grafana |

### Case 2 — *ASAT (eln.lemuel.co.kr) 청각 재활 훈련*

| 항목 | 값 |
|------|----|
| 평균 TPS | ~50 |
| Peak TPS | ~200 |
| 1차 병목 | *없음* — 학술용 |
| 해법 | tuning 0 |

→ *모든 백엔드가 *고부하 시스템이 아니다*. *측정해서 *진짜 필요한 만큼만 *최적화*.

### Case 3 — *ssgb2e (신세계 B2E) 정산 배치*

| 항목 | 값 |
|------|----|
| 처리량 | 5 만 row / 분 (≈ 800 TPS bulk insert) |
| 1차 병목 | Oracle PK lock contention |
| 해법 | 시리얼 처리 + UNIQUE 멱등성 + NOT EXISTS |
| 도구 | Pinpoint + DB Monitor |

→ *PR #1 / #2 / #3* 시리즈 ([blog 참조](/2026/06/07/python-tutor-cli-web-shared-grader-builtins-trap/)).

### Case 4 — *market-feed (lemuel-quant-core)*

| 항목 | 값 |
|------|----|
| 입력 throughput | ~ 5K msg/sec (Binance + Upbit + Bithumb 합) |
| 1차 병목 | *Java GC pause* — Java로 했다면 |
| 해법 | C++ + zero allocation + Boost.Beast WS |
| 도구 | perf + flamegraph |

### Case 5 — *news-pipeline (NER + 감성 분석)*

| 항목 | 값 |
|------|----|
| 처리량 | ~ 200 article/sec |
| 1차 병목 | KR-FinBERT ONNX 추론 (CPU bound) |
| 해법 | 2 티어 폴백 (LexiconScorer + KR-FinBERT) + batching |
| 도구 | ONNX Profiler + Prometheus |

→ ([관련 글](/2026/06/09/news-pipeline-ai-data-refinement-korean-nlp-traps/))

### Case 6 — *fashion-design (modular monolith)*

| 항목 | 값 |
|------|----|
| 평균 TPS | ~100 |
| Peak TPS | ~500 |
| 1차 병목 | WebSocket session count (실시간 3자 채팅) |
| 해법 | Redis Pub/Sub 멀티 인스턴스 동기화 + STOMP |
| 도구 | k6 (WebSocket plugin) |

---

## 3. *도구 사용법 — *측정 + 부하 테스트***

### 3.1 *부하 생성기 4 종 비교*

| 도구 | 언어 | 강점 | 약점 | 추천 시나리오 |
|------|------|------|------|------------|
| **wrk** | C | *가장 빠름* (수 만 RPS 단일 머신) | *단순 시나리오만* | nginx 자체 부하 |
| **hey** | Go | *설치 1 줄, CLI* 매우 간단 | 시나리오 분기 X | 즉석 API 1 개 측정 |
| **k6** ★ | JS (스크립트) | *시나리오 풍부* + *Grafana 통합* + WebSocket | *Cloud 버전 유료* | **현장 표준** |
| **JMeter** | Java GUI | *복잡한 시나리오* + *기업 표준* + *원본 보고서* | *무겁고 *느림* | 기업 / 금융 정밀 부하 |
| **Vegeta** | Go | *constant rate* 정밀 | UI 없음 | SLA 측정 |
| **Locust** | Python | *Pythonic, 분산 부하* | 속도 낮음 | Python 팀 |

### 3.2 *k6 — *현장 표준* 예시*

```bash
# 설치 (mac)
brew install k6
```

```javascript
// orders.js — 주문 API 부하 테스트
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 100 },    // 30초간 100 VU로 증가
    { duration: '1m',  target: 500 },    // 1분간 500 VU 유지
    { duration: '30s', target: 0 },      // 30초간 0으로 감소
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],    // 95%가 500ms 이내
    http_req_failed:   ['rate<0.01'],    // 에러율 1% 미만
  },
};

export default function () {
  const res = http.post('https://api.lemuel.co.kr/orders', JSON.stringify({
    productId: 1, quantity: 1,
  }), { headers: { 'Content-Type': 'application/json' } });

  check(res, {
    'status 200': (r) => r.status === 200,
    'has orderId': (r) => r.json('orderId') !== undefined,
  });

  sleep(1);
}
```

```bash
k6 run orders.js
```

→ 결과 (실제 출력 예시):
```
http_req_duration..........: avg=247ms min=12ms med=189ms max=2.1s p(95)=489ms
http_req_failed............: 0.83%
http_reqs..................: 28572  (~ 476/s)
vus........................: 0    max=500
```

> *p(95)=489ms < 500ms* 만족 ✅, *failure rate 0.83% < 1%* 만족 ✅.

### 3.3 *JMeter — *복잡한 시나리오용**

기업에서 *정밀 보고서* 가 필요할 때 사용. *Thread Group + HTTP Request + Listener* 의 *GUI 조립*. 

장점: *Cookie / OAuth / DB 직접 / CSV 데이터 셋* 같은 *enterprise 기능 풍부*.
단점: *JVM 위에서 동작 → 단일 머신 *5K RPS 한계*. *대량 부하* 시 *분산 모드 필요*.

### 3.4 *Pinpoint (or Scouter / NewRelic / Datadog) — *call tree 분석***

*"왜 *우리 API 가 *느리지?"* 라는 *진단* 에는 *부하 테스트 외에 *APM* 도 필요. *Pinpoint* (오픈소스, NHN 개발) 가 *국내 표준*:

```
사용자 요청 → /orders POST
   ├─ AuthFilter            2ms
   ├─ ProductService         15ms  (Redis hit)
   ├─ InventoryService       82ms  ⚠️ 느림
   │    └─ DB query: SELECT * FROM stock WHERE...  78ms
   │         → *index 누락* 의심
   ├─ PaymentService         245ms ⚠️⚠️ 매우 느림
   │    └─ 외부 PG (Toss) call: 240ms
   │         → 정상 (외부 의존)
   └─ OrderRepository        18ms
                       총: 362ms
```

→ *call tree 시각화* 로 *어디서 느린지* 즉시 발견. *내장 어디서 *얼마나 *DB / Redis / 외부 API* 사용했는지* 까지.

**설치 — Java agent 추가**:
```bash
java -javaagent:/path/to/pinpoint-bootstrap-2.5.x.jar \
     -Dpinpoint.agentId=order-service-1 \
     -Dpinpoint.applicationName=order-service \
     -jar order-service.jar
```

### 3.5 *Prometheus + Grafana — *시계열 모니터링***

부하 테스트 *외에 *상시 모니터링*. *Micrometer* 가 Spring Boot 의 *기본 metrics 발행*:

```java
// 자동 노출되는 metrics
http_server_requests_seconds_count
http_server_requests_seconds_sum   
jvm_memory_used_bytes
hikaricp_connections_active
hikaricp_connections_pending       ← *이게 증가하면 *pool 부족 신호*
```

Grafana dashboard:
```promql
# 실시간 TPS
rate(http_server_requests_seconds_count[1m])

# p95 latency
histogram_quantile(0.95, rate(http_server_requests_seconds_bucket[5m]))

# DB pool waiting
hikaricp_connections_pending
```

→ *peak hour 직전 *pool 증가 신호* 잡아서 *AutoScale*.

---

## 4. *부하 테스트 시 *주의해야 할 *함정 5 가지***

### 4.1 *Warm-up 안 했다*

JVM 의 *JIT compilation* 이 *초기 1-2 분* 동안 *코드 최적화*. *시작 직후 측정* 하면 *실제 production 보다 *2-3 배 느린 결과*.

→ k6 의 *처음 30 초는 *warm-up* 으로 *결과 무시*.

### 4.2 *Cache 가 hit 률 100% 인 상황만 측정*

같은 데이터를 *반복 요청* 하면 *Redis hit 률 100%* → *비현실적 TPS*. 

→ *시나리오에 *데이터 다양성 *주입*. *productId 를 *1~1만 사이 random*.

### 4.3 *클라이언트 측 병목*

부하 생성기가 *돌리는 머신의 *CPU / 네트워크* 가 *천장* 인데 *서버가 느린 줄 *오인*.

→ *부하 생성기 *별도 머신* (또는 클러스터) 에서 실행. *클라이언트 CPU 사용률 *< 70% 유지*.

### 4.4 *외부 의존성 무시*

PG / SMS / 이메일 외부 API 의 *rate limit 무시* 하고 부하 주면 *외부 API 에서 *차단 / 추가 요금*.

→ 부하 테스트 환경의 *외부 의존은 *mock 처리*. 또는 *staging PG* 사용.

### 4.5 *측정 단위 혼동 — RPS vs TPS*

| *우리 시스템 *5K TPS 가능* | 진실 |
|------------------------|------|
| 만약 *RPS* 의미였다면 | 실제 *TPS 1K* (1 트랜잭션 = 5 API) — *5 배 과대 광고* |
| 만약 *QPS* 의미였다면 | 실제 *TPS 200* (1 트랜잭션 = 25 query) — *25 배 과대* |

→ *측정 시 *비즈니스 트랜잭션* 단위로 *정확히 명시*.

---

## 5. *현장에서의 *학습 압축***

### 5.1 *측정 없이 추측 X*

> *내가 *어디서 *느리지?"* 의 *답을 *추측으로 *내는 순간 *반드시 틀린다*. *Pinpoint / Prometheus / k6* 로 *수치 먼저 확인*. *직감 vs 측정 = 측정 승*.

### 5.2 *단계별 천장의 *언어*

> *TPS 100 → 1K → 10K → 100K* 각 단계가 *다른 시스템* 을 요구한다. *지금 우리 단계가 어디인지* 알면 *튜닝 우선순위* 명확. *10K 가 안 필요한 *학술 시스템* 에 *Kafka 도입 = 오버 엔지니어링*.

### 5.3 *부하 테스트는 *주기적*

> *코드 변경마다 *TPS 가 *바뀐다*. *CI 파이프라인에 *k6 자동 부하 테스트* 통합. *직전 commit 대비 *p95 가 *20% 떨어졌으면 *PR 차단*.

```yaml
# .github/workflows/loadtest.yml
- name: k6 load test
  uses: grafana/k6-action@v0.3.1
  with:
    filename: tests/orders.js
    flags: --vus 100 --duration 1m
```

### 5.4 *언어 / runtime 한계 인식*

> *Java GC pause* 가 *50ms* 라면 *latency p99 < 50ms* 절대 불가. *Java 의 *기본적 *천장*. *Rust / Go / C++* 으로 *언어 변경* 이 *답일 때* 가 있다. *내 lemuel-quant-core 의 *market-feed 가 *C++* 인 이유*.

---

## 6. *마무리 — *TPS 의 본질***

### 6.1 *TPS 는 *시스템의 *건강 상태***

> *TPS 측정 안 하는 백엔드 = *컴파일은 통과 했지만 *runtime 에서 *어떻게 *깨질지 모르는* 시스템*. *측정이 *건강 검진*. *부하 테스트가 *예방 접종*.

### 6.2 *내 시스템의 *7 단계 *현실적 *튜닝 우선순위***

```
1. 측정 도구 도입 (Prometheus + Grafana + Pinpoint)        ← 가장 중요
2. p95 latency 기준선 합의 (예: < 500ms)
3. k6 부하 테스트 시나리오 작성 + 정기 실행
4. DB connection pool 튜닝 (HikariCP)
5. 인덱스 / N+1 점검 (EXPLAIN ANALYZE)
6. Redis 캐시 (90% hit 률 목표)
7. Kafka 비동기 분리 (필요 시)
```

### 6.3 *이력서 변환 hook*

> *"백엔드 TPS 튜닝 경험"* 한 줄에:
> - 100 → 1K → 10K → 100K 의 *단계별 천장* 이해
> - HikariCP pool sizing *계산 공식*
> - Read replica / CQRS / Outbox / Triple Idempotency 의 *MSA 패턴*
> - k6 / JMeter / Pinpoint / Grafana *4 도구 차이*
> - GC pause / NIC / kernel 의 *언어 / runtime 한계*
> 
> *4 단 깊이 면접 답변 hook* 모두 준비.

---

## 부록 — *간단한 k6 *시작 키트*

```bash
# 1. k6 설치
brew install k6   # mac
docker run -i grafana/k6 run -   # docker

# 2. 가장 간단한 테스트
cat > simple.js <<'EOF'
import http from 'k6/http';
export const options = { vus: 50, duration: '30s' };
export default () => http.get('https://your-api.com/health');
EOF

# 3. 실행
k6 run simple.js
```

→ *5 분 안에 *첫 부하 테스트 결과*. *이게 *시작점*.

---

*다음 글:* *Reactive (Spring WebFlux / Project Reactor)* 가 *진짜 *TPS 천장을 *얼마나 올리는가* — *Tomcat vs Netty / Blocking IO vs Non-blocking IO / 실제 측정 비교*.
