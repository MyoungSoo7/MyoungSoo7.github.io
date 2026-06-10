---
layout: post
title: "서버 성능 개선 *기초* — *DB 80% / 외부 API 15% / 서버 코드 5% 법칙* 으로 본 *측정 → 진단 → 처방* 의 일관 사이클"
date: 2026-06-10 17:00:00 +0900
categories: [performance, backend, sre]
tags: [performance, latency, throughput, db, jpa, n-plus-one, indexing, connection-pool, caching, circuit-breaker, resilience4j, async, batch, gc, observability, apm, spring-boot]
---

서버 성능 의 *체감 적 정공* 은 *세 줄 룰* 로 압축 된다 — *"측정 없이 최적화 하지 말 것, *DB 부터 의심* 할 것, *코드 최적화 는 *마지막*"*. 실무 에서 *느린 endpoint 의 *80%* 는 *DB*, *15%* 는 *외부 API 호출*, *나머지 5%* 만 *서버 코드 자체*. *우리 시간 의 80% 가 *DB 절* 에 가야 한다 — 그러나 실제로는 *코드 가독성 개선* 같은 *5% 쪽에서 시간 을 쓴다*. *비대칭 이 *서버 성능 개선 의 *가장 큰 함정*.

이 글은 *Spring Boot + JPA + REST API* 환경 기준 으로 *서버 성능 개선 의 *기초* 를 정리 한다. **(1) 측정 지표 — 무엇을 보는가**, **(2) 80/15/5 법칙 — 어디부터 의심하는가**, **(3) DB 성능 개선 — 인덱스·N+1·쿼리·풀·캐시**, **(4) 외부 API 연동 — timeout·retry·circuit breaker·bulkhead**, **(5) 서버 자체 — async·batch·thread pool·GC**, **(6) 관측성 — APM·tracing·메트릭**, **(7) 함정 5 가지**, **(8) 학습 로드맵**. 어제 *컴퓨터과학 7 분야* / *수학 8 분야* 글 의 *시리즈* 톤 — *기초의 *공통 어휘* 를 깔아 주는 글*.

---

## TL;DR

| 단계 | 도구 / 지표 | 우선 순위 |
|---|---|---|
| 0. *측정* | p50 / p95 / p99 latency, throughput (RPS), error rate, saturation | *항상 먼저* |
| 1. *DB 의심* | slow query log, EXPLAIN, N+1 탐지 | 80% 사례 |
| 2. *외부 API* | timeout, retry, circuit breaker, fallback | 15% 사례 |
| 3. *서버 코드* | async / batch / thread pool / GC | 5% 사례 |
| 4. *관측성* | APM (Datadog/Pinpoint/Scouter), distributed trace | *문화* |

**핵심 명언 셋**:

- *"Premature optimization is the root of all evil."* — Donald Knuth (코드 최적화 *전에* 측정)
- *"In God we trust. All others must bring data."* — W. Edwards Deming (직감 X, 측정 O)
- *"The fastest code is the code that doesn't run."* — Anonymous (호출 자체를 *없애는* 게 정공)

**실무 함의**: *p99 latency 가 5 초* 라 한다면 *5 초 의 *어디서* 시간이 갔는지를 *trace 로 찢어 봐야* 한다*. *DB query 4.7 초 / 외부 API 0.2 초 / 코드 0.1 초* 면 — *답은 명백히 DB 인덱스*. *모르고 *async 변환 / 코드 최적화* 부터 손대면 *시간만 버린다*. *측정 → 진단 → 처방* 의 *일관 사이클* 이 본질.

---

## 0. 들어가며 — *측정 없이 최적화 하지 말 것*

성능 개선 의 *가장 큰 적* 은 *직감*. *"이 코드 가 느릴 것 같아"* 라는 *육감* 으로 손대면 *대부분 *틀린 자리* 를 만진다*. Knuth 가 *1974 년* 에 쓴 명언:

> *"Premature optimization is the root of all evil (or at least most of it) in programming."*

원문은 *"대부분 의 최적화 는 *측정 없이 *섣불리 한다* 라서 잘못 된다"* 라는 의미. *측정 → 진단 → 처방 → 재측정* 의 *과학적 사이클* 만이 정공.

### 0-1. *측정 의 4 가지 황금 지표*

Google 의 *SRE 책* 이 정리 한 *Four Golden Signals*:

1. **Latency** — 한 요청 의 처리 시간. *p50 / p95 / p99* 의 *분포* 가 핵심
2. **Traffic** — 단위 시간 처리량 (RPS, QPS, TPS)
3. **Errors** — 5xx, 4xx, 도메인 에러 비율
4. **Saturation** — *자원 의 *얼마나 차 있는지* (CPU%, mem%, conn pool 사용률)

이 *4 개만 정확히 측정* 해도 *대부분의 성능 문제 가 보인다*. *p99 latency 가 갑자기 튀면 — *어느 자원 의 saturation* 이 *그 시간 에 *피크* 인지 보면 답 이 나온다.

### 0-2. *p99 = 진짜 사용자 경험*

순진한 측정: *"평균 응답시간 200ms"*. 그러나 *평균 의 함정* — *p99 가 5 초* 일 수 있다. *전체 사용자 의 *1% 가 *5 초 의 대기* 를 경험*. *서비스 의 *느림* 으로 인식 되는 건 *이 1%*. *평균 보다 *분위수 (percentile)* 가 정공*.

```
p50 (중간값):     200ms   ← 절반 의 요청 이 이 안에
p95:              800ms   ← 95% 의 요청 이 이 안에
p99:            5,000ms   ← 1% 가 *이만큼 느림*  ← 진짜 문제
p99.9:         15,000ms   ← 0.1% 의 *서비스 의 비명*
```

*p99 가 *5 초 이상 이면 — *서비스 의 *상위 사용자 경험* 이 *재앙 적*. *p50 만 보면서 안심 하면 *모르고 망한다*.

---

## 1. *80/15/5 법칙* — 어디부터 의심하는가

수많은 *production trace* 를 보다 보면 *느린 endpoint 의 원인 분포* 가 *대체로 같다*:

| 원인 | 비율 | 대표 증상 |
|---|---|---|
| **DB** | *~80%* | N+1, 인덱스 누락, 큰 결과 셋, 락 |
| **외부 API** | *~15%* | timeout, 응답 지연, retry storm |
| **서버 코드** | *~5%* | sync I/O, GC pause, JSON 직렬화 비용 |

이 *비율* 이 *시간 분배 의 정공*. *DB 한 분야 에 *시간 의 80% 를 쓰는 게 *기댓값 적으로 옳다*. 그런데 *우리 가 *코드 리팩토링 에 80%* 를 쓰면 — *5% 의 영역에 80% 의 노력*. *기댓값 적으로 *손해*.

### 1-1. *어디서 시간이 갔는지* 보는 *최소 도구*

1. **APM** (Datadog APM, Pinpoint, Scouter, New Relic) — *한 요청의 *flame graph*. 어느 함수 / 어느 쿼리 가 *몇 ms* 인지 *한 눈* 에. *없으면 *비행기 를 *눈 가리고 운전*.
2. **Slow query log** (MySQL `slow_query_log`, PostgreSQL `log_min_duration_statement`) — *DB 가 *직접 신고* 하는 느린 쿼리
3. **Spring Boot 의 *Actuator + Micrometer + Prometheus*** — *애플리케이션 메트릭* 의 표준
4. **OpenTelemetry / Zipkin / Jaeger** — *분산 트레이싱*. 한 요청 이 *여러 마이크로서비스 를 통과* 할 때 추적

이 셋 중 *하나 라도* 없으면 — *성능 개선 은 *맹목적 추측***.

---

## 2. *DB 성능 개선* — *80% 의 영역*

가장 자주 만나는 패턴 5 가지.

### 2-1. *N+1 쿼리 — JPA 의 *기본 함정**

```java
// ❌ N+1: 주문 N 개 → 각 주문 의 고객 조회 N 번 추가
List<Order> orders = orderRepository.findAll();     // 1
for (Order o : orders) {
    System.out.println(o.getCustomer().getName());   // N
}
// 총 1 + N 회 쿼리. 주문 1000 개 면 *1001 회 쿼리*.
```

```java
// ✅ Fetch join
@Query("SELECT o FROM Order o JOIN FETCH o.customer")
List<Order> findAllWithCustomer();
// 총 1 회 쿼리.
```

또는 `@EntityGraph`, `@BatchSize` 같은 *어노테이션 기반 우회*. 어떤 방식 이든 *N+1 을 *제거* 하는 게 *대부분 의 *느린 endpoint 의 진짜 원인*.

### 2-2. *인덱스 — *대수 십만 배* 의 차이*

```sql
-- 인덱스 없음
SELECT * FROM orders WHERE customer_id = 12345;
-- 풀스캔. O(n) — 1,000 만 row 면 ~수 초

-- 인덱스
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
-- B-tree lookup. O(log n) — 같은 row 수 에 *~수 ms*
```

*어제 컴퓨터과학 글 의 *B-tree* 가 *현실에서 *수십만 배* 의 차이를 만든다*. 다만 *모든 컬럼에 인덱스 가 능사 가 아님*:

- INSERT / UPDATE *비용 증가* (인덱스 도 유지)
- 디스크 *공간 증가*
- *과도 한 인덱스* — 옵티마이저 가 *잘못 된 인덱스 를 선택* 해 *오히려 느려짐*

*EXPLAIN* 으로 *실제 사용 인덱스* 확인 이 정공:

```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 12345;
-- Index Scan using idx_orders_customer_id ...  ← 인덱스 사용 OK
-- Seq Scan on orders ...                       ← 풀스캔. 인덱스 누락 또는 부적합
```

### 2-3. *복합 인덱스 의 *순서**

```sql
-- WHERE customer_id = ? AND status = 'PAID' ORDER BY created_at DESC
-- 자주 쓰는 쿼리. 복합 인덱스 의 *컬럼 순서* 가 중요.

-- ✅ 정공
CREATE INDEX idx ON orders(customer_id, status, created_at DESC);
-- *equality (=) 먼저, range / sort 나중*

-- ❌ 비효율
CREATE INDEX idx ON orders(created_at, customer_id, status);
-- equality 컬럼 (customer_id, status) 가 인덱스 *뒤 쪽* → 활용 안 됨
```

*"Equality → Range → Sort"* 의 순서. *복합 인덱스 의 *황금 룰*. 이 룰 만 알아도 *느린 쿼리 의 절반 은 *해결*.

### 2-4. *Connection Pool — *적정 크기* 의 함정*

```yaml
# 흔히 보는 *틀린* 설정
spring:
  datasource:
    hikari:
      maximum-pool-size: 100  # ❌ 너무 큼
```

*"풀이 클수록 빠를 것"* — 직관 적이지만 *틀림*. DB 의 *동시 연결 처리 능력* 이 *코어 수 의 *몇 배* 가 한계*. *PostgreSQL 의 권장: *(코어 수 × 2) + 디스크 스핀들 수***. *수십 정도*.

```yaml
# ✅ 보통 정공
maximum-pool-size: 20
minimum-idle: 10
connection-timeout: 3000
idle-timeout: 600000
max-lifetime: 1800000   # 30분. DB 의 wait_timeout 보다 짧게
```

*풀 이 *너무 크면*: connection 자체 의 메모리·DB 부하 가 *오히려 느려짐*. *너무 작으면*: 요청들 이 *connection 대기* 로 줄을 섬. *Saturation 메트릭 (`hikaricp.connections.active / max`)* 으로 *튜닝*.

### 2-5. *캐싱 — *호출 자체를 *없애는* 정공*

> *"The fastest code is the code that doesn't run."*

같은 쿼리 가 *자주 반복* 된다면 *결과 를 메모리 에 캐싱* 하는 게 *어떤 인덱스 최적화 보다 효과*. Spring 의 *@Cacheable*:

```java
@Service
public class ProductService {

    @Cacheable(value = "products", key = "#id")
    public Product findById(Long id) {
        return productRepository.findById(id).orElseThrow();
    }

    @CacheEvict(value = "products", key = "#product.id")
    public void update(Product product) {
        productRepository.save(product);
    }
}
```

*Caffeine* (in-memory) 또는 *Redis* (분산) 가 두 대표 백엔드. *TTL + max size* 정책 으로 *메모리 폭주 방지*. *Cache hit ratio* 메트릭 으로 *정책 의 효과 측정*.

> ⚠️ *캐시 의 함정*: *stale data*. 캐시 가 *오래된 데이터 를 반환* 하면 *비즈니스 정합성 깨짐*. *변경 이벤트 와 *evict* 가 *짝* 이어야 안전.

---

## 3. *외부 API 연동* — *15% 의 영역*

외부 PG, 메시징, 다른 마이크로서비스. *우리 통제 밖* 이라 *안전망 5 종 세트* 가 필수.

### 3-1. *Timeout — *0순위 필수**

```java
// ❌ 기본 RestTemplate — timeout 무한대
RestTemplate rt = new RestTemplate();

// ✅ 명시적 timeout
SimpleClientHttpRequestFactory f = new SimpleClientHttpRequestFactory();
f.setConnectTimeout(3000);   // 3초
f.setReadTimeout(5000);      // 5초
RestTemplate rt = new RestTemplate(f);
```

*"외부 API 가 영원히 응답 안 한다" 면 *우리 의 thread pool 이 점유* 되고 *전체 서비스 가 hang*. *timeout 은 옵션 이 아니라 *필수*.

### 3-2. *Retry — 멱등 조건 일 때만*

```java
@Retryable(
    value = {SocketTimeoutException.class, IOException.class},
    maxAttempts = 3,
    backoff = @Backoff(delay = 1000, multiplier = 2)  // 1s, 2s, 4s
)
public Response callExternal() {
    return restTemplate.getForObject(url, Response.class);
}
```

*주의*: *POST / 결제 / 송금* 같은 *부수 효과* 가 있는 호출 의 retry 는 *멱등 보장* 이 필수. *Idempotency-Key 헤더* 같은 표준 패턴 이 정공. *아무 retry 가 *중복 결제* 를 만들 수 있다*.

### 3-3. *Circuit Breaker — 외부 가 죽으면 *우리도 같이 죽지 않게**

```java
@CircuitBreaker(name = "paymentApi", fallbackMethod = "fallback")
public Payment charge(Order o) {
    return paymentClient.charge(o);
}

public Payment fallback(Order o, Throwable t) {
    log.warn("payment fallback for {}", o.getId(), t);
    return Payment.pending(o);   // pending 으로 표시, 비동기 재시도
}
```

*Resilience4j 의 CircuitBreaker* — 외부 API 의 *연속 실패 가 임계치 넘으면* *일정 시간 차단* + *fallback 호출*. 외부 가 *천천히 회복 하는 사이* 에 *우리 의 thread 가 쌓이는 사고* 방지.

### 3-4. *Bulkhead — *외부 가 *우리 thread 를 다 잡지 않게**

```java
@Bulkhead(name = "paymentApi", type = Bulkhead.Type.SEMAPHORE, maxConcurrentCalls = 10)
public Payment charge(Order o) { ... }
```

*"외부 API 호출 에 *동시 10 thread 까지만 쓰겠다"*. 나머지 thread 는 *다른 일* (다른 API, 다른 endpoint) 을 한다. *한 외부 의 hang 이 *전체 서비스 의 hang* 으로 *번지지 않게*. *어제 컴퓨터과학 글 의 *netflix Hystrix 의 정신*.

### 3-5. *Fan-out — N 개 호출 의 병렬화*

```java
// ❌ Sequential: 5 외부 API × 200ms = 1000ms
Result a = apiA();
Result b = apiB();
Result c = apiC();
Result d = apiD();
Result e = apiE();

// ✅ Parallel: max(...) = 200ms
CompletableFuture<Result> fa = CompletableFuture.supplyAsync(this::apiA);
CompletableFuture<Result> fb = CompletableFuture.supplyAsync(this::apiB);
// ... 등
CompletableFuture.allOf(fa, fb, ...).join();
```

*N 개 호출 이 *서로 독립* 이라면 *반드시 *병렬*. 그러나 *부주의 한 parallel* 은 *외부 의 *rate limit 폭발* 또는 *thread pool 고갈*. *bulkhead + circuit* 과 *세트로 사용*.

---

## 4. *서버 자체* — *5% 의 영역*

DB 와 외부 API 가 *깨끗* 한데도 느리다면 — 그 때 *서버 코드* 차례.

### 4-1. *Async — sync I/O 의 *thread 낭비**

```java
// ❌ Tomcat 의 한 thread 가 *5초 동안 *외부 API 응답 대기*
@GetMapping("/order")
public Order getOrder(Long id) {
    Order o = orderService.find(id);    // 200ms
    Customer c = customerApi.get(o);    // 5000ms ← thread 점유
    return o.withCustomer(c);
}

// ✅ 비동기 — thread 는 다른 요청 처리
@GetMapping("/order")
public CompletableFuture<Order> getOrder(Long id) {
    return CompletableFuture
        .supplyAsync(() -> orderService.find(id))
        .thenCombine(
            CompletableFuture.supplyAsync(() -> customerApi.get(id)),
            Order::withCustomer
        );
}
```

또는 *Virtual Thread* (Java 21+) 로 *훨씬 가벼운 동시성* — *Tomcat 의 thread 수 가 *수십 → 수만* 으로 가능*. *Spring Boot 3.2+ 의 *virtual thread 지원* 으로 *대부분의 sync 코드 가 그대로 *고동시성*.

### 4-2. *Batch — *N 회 호출 → 1 회 호출**

```java
// ❌ 개별 호출 N 회 — 1000 row 면 1000 회 INSERT
for (Order o : orders) {
    orderRepository.save(o);
}

// ✅ batch INSERT
spring.jpa.properties.hibernate.jdbc.batch_size: 50

orderRepository.saveAll(orders);   // 50 row 씩 묶어 *20 회 INSERT*
```

*N+1 의 반대 — *1+N → 1***. *INSERT*, *UPDATE*, *외부 API 호출* 모두 *batch 가능 여부* 를 점검.

### 4-3. *Thread Pool — *적정 크기**

```yaml
# Tomcat
server:
  tomcat:
    threads:
      max: 200
      min-spare: 20
```

*"max 가 클수록 좋을까?"* 아니다. *CPU 코어 의 *몇 배* 가 한계*. 그 이상은 *context switch* 비용 이 *처리량 을 떨어뜨림*. *I/O 바운드* 면 *큰 수*, *CPU 바운드* 면 *코어 수 ±*.

### 4-4. *GC Pause — *조용 한 살인자**

```bash
# JVM 옵션 — G1GC 권장 (Java 17+)
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:+UnlockExperimentalVMOptions
-XX:+UseZGC      # 또는 ZGC. *pause < 10ms 보장*
```

*p99 latency 가 *튀는 원인* 의 큰 부분 이 *GC pause*. *Young GC* 는 *수십 ms*, *Full GC* 는 *수 초*. *모니터링: `jstat -gc`*. *Heap 너무 작으면 *Full GC 빈도*, 너무 크면 *Pause 길어짐*.

*ZGC* (Java 17+) 또는 *Shenandoah* — *pause 가 10ms 미만 보장*. *최신 GC 로 *대부분의 GC 고민 이 사라진다*.

---

## 5. *관측성 — *모르면 못 고친다**

성능 개선 은 *반복적*. *재측정 → 진단 → 처방 → 재측정*. *측정 인프라 가 없으면 *반복 의 사이클 이 *돌아가지 않는다*.

### 5-1. *최소 관측성 스택*

| layer | 도구 |
|---|---|
| 메트릭 | Micrometer + Prometheus + Grafana |
| 로그 | Loki, ELK |
| 트레이스 | OpenTelemetry + Tempo, Jaeger, Zipkin |
| APM | Datadog, Pinpoint, Scouter (한국 기업), Skywalking |

*Spring Boot* 에 *3 줄* 만 추가 하면 Prometheus endpoint 가 열린다:

```gradle
implementation 'org.springframework.boot:spring-boot-starter-actuator'
implementation 'io.micrometer:micrometer-registry-prometheus'
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
```

이 한 번 의 설정 으로 *수십 가지 메트릭* 이 자동 수집:

- `http_server_requests_seconds` — endpoint 별 latency
- `hikaricp_connections_active` — connection pool 활용
- `jvm_gc_pause_seconds` — GC pause
- `jvm_memory_used_bytes` — heap 사용량

### 5-2. *Distributed Trace — 마이크로서비스 의 *X-ray**

한 사용자 요청 이 *Order → Payment → Settlement* 의 *3 마이크로서비스 를 통과*. *어디서 시간이 갔는지* 는 *trace 가 없으면 *찾지 못함*.

```
[Order]    ─10ms→  [Payment]  ─4500ms→  [PG API]
                                          ↑
                                  ← 여기서 4.5초
```

*OpenTelemetry* 의 *trace ID* 가 *모든 요청 로그에 자동 부착*. *Grafana Tempo + Loki* 조합 으로 *trace 보면서 그 시점의 로그* 까지 *한 화면*. *MSA 의 *디버깅 능력 의 본질*.

---

## 6. *함정 5 가지* — 빠지면 *오히려 느려지는*

### 6-1. *N+1 을 풀려고 *cartesian product*

```java
@Query("SELECT o FROM Order o JOIN FETCH o.lineItems JOIN FETCH o.payments")
```

*다중 JOIN FETCH* — *order 1 개 × line 5 개 × payment 3 개 = 15 row*. Hibernate 가 *DB 의 *카르테시안 곱* 결과 를 *중복 제거* 하느라 *오히려 더 느림*. *MultipleBagFetchException* 도 자주. *@EntityGraph + @BatchSize* 가 정공.

### 6-2. *인덱스 *너무 많이* 만들기*

INSERT 가 빈번한 테이블에 *컬럼 마다 인덱스* — *INSERT 마다 *N 개 인덱스 갱신*. *쓰기 부하 가 *수 배*. *읽기 쿼리 패턴 분석 후 *필수 인덱스만**.

### 6-3. *@Async — 메서드 호출 무작정 비동기화*

```java
@Async
public void heavyTask() { ... }
```

*같은 클래스 내부 호출 (self-invocation)* 시 *Spring proxy 우회* → *비동기 동작 안 함*. *별도 서비스 로 분리* 또는 *AspectJ 모드*. 또한 *thread pool 의 *기본 크기* 가 너무 작아 *비동기 가 안 되는 경우* 도 많음.

### 6-4. *Retry 의 *무한 retry storm**

외부 API 가 *전체 다운* 일 때 *retry 가 *부하 를 *몇 배로 증폭*. *circuit breaker 가 *없이* retry 만 있으면 — *외부 의 회복 을 *방해*. *Retry + Circuit + Bulkhead = 세트*.

### 6-5. *측정 없이 *경험적 최적화**

*"우리 팀 이 *작년에 *@Transactional(readOnly=true) 로 효과 봤어"* — *그건 *그 코드 에서* 의 이야기*. *우리 endpoint 가 *진짜 *느린 자리* 는 다를 수 있음*. *경험 ≠ 데이터*. *Deming 의 룰*: *"In God we trust. All others must bring data."*

---

## 7. *학습 로드맵*

| 단계 | 집중 | 책 |
|---|---|---|
| 1 | *측정 의 4 골든 시그널* + Prometheus + Grafana | *Site Reliability Engineering* (Google, 무료 온라인) |
| 2 | *DB 의 *EXPLAIN + 인덱스 + Connection pool** | *Real MySQL 8.0* (한국어, 백은빈/이성욱) |
| 3 | *JPA 의 *N+1 + Fetch + Batch** | *자바 ORM 표준 JPA 프로그래밍* (김영한) |
| 4 | *Resilience 패턴* | Resilience4j 공식 docs + Michael Nygard *Release It!* |
| 5 | *비동기 / Virtual Thread / GC* | *Java Performance* (Scott Oaks) |
| 6 | *Observability 문화* | *Observability Engineering* (Charity Majors et al.) |

### 7-1. *최소 어휘* 한 줄 정리

- *p99* 가 들리면 → *진짜 사용자 의 *상위 1% 경험*
- *N+1* 가 들리면 → *JPA 가 *N 번 더 쿼리* 의 신호
- *EXPLAIN* 이 들리면 → *DB 의 *실제 실행 계획* 보는 도구
- *HikariCP* 가 들리면 → *connection pool 의 사실상 표준*
- *circuit breaker* 가 들리면 → *외부 가 죽어도 *우리는 산다*
- *bulkhead* 가 들리면 → *한 외부 가 *우리 thread 전체를 못 잡게*
- *trace ID* 가 들리면 → *마이크로서비스 의 *X-ray*

이 어휘 만으로 *대부분의 성능 회의 에 *공통 어휘* 로 참여 가능*.

---

## 마무리 — *성능 개선 의 *직업 적 자부심**

*"느린 시스템 을 *빠르게 만든다"* 는 *엔지니어 의 가장 *원초적 즐거움*. *p99 가 5 초 에서 *500ms* 로 떨어 지는 순간* — *그 *수치* 의 *변화 가 *사용자 수만 명 의 *체감 적 행복* 으로 환산* 된다. *측정 가능 한 영향*. *우리가 *이 직업 을 하는 이유* 중 하나*.

기억 할 *세 줄*:

1. *측정 하지 않은 채 최적화 하지 말 것* — Knuth
2. *DB 부터 의심* — *80% 가 거기*
3. *외부 API 는 *불확실성* + *우리 thread 를 점유* — *timeout / circuit / bulkhead 세트* 필수

성능 개선 의 *반복 의 사이클* — *측정 → 진단 → 처방 → 재측정* — 이 *돌아가는 팀 에서만* *시스템 이 *시간 과 함께 *느려지지 않는다*. *대부분의 팀 에서 *기능 추가 = 성능 저하* 는 *불가피*. *측정 인프라 가 있어야 *그 저하 를 *되돌릴 수 있다*.

*"빠른 시스템 은 *성능 좋은 코드 의 결과 가 *아니라 *측정 의 문화 의 결과* 다."* — 이 글 의 *한 줄 결론*.
