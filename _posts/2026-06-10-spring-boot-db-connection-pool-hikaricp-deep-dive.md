---
layout: post
title: "*백엔드 개발자가 알아야 할 *DB Connection Pool* — Spring Boot + HikariCP *11 가지 설정의 *진짜 의미*, *Pool sizing 계산 공식*, *Connection Leak 진단법*, 실전 *postmortem 4 건* 까지*"
date: 2026-06-10 18:00:00 +0900
categories: [backend, spring-boot, database, performance]
tags: [spring-boot, hikaricp, connection-pool, postgresql, jdbc, jpa, connection-leak, performance-tuning, postmortem, micrometer, grafana, transaction]
---

이 글은 *Spring Boot 백엔드 개발자* 가 *DB Connection Pool* 에 대해 *"옵션 이름은 들어봤지만 *진짜 의미는 모르겠다"* 단계 를 *벗어나기 위한 *현장 deep-dive*. *HikariCP 11 가지 설정* / *Pool sizing 계산 공식* / *Connection Leak 진단 절차* / *실제 production postmortem 4 건* 으로 구성.

전 글 (*[백엔드 TPS](/2026/06/10/backend-tps-throughput-realistic-cases-tools/)*) 의 *후속편*. *TPS 1K → 10K 의 *첫 번째 천장* 이 *DB connection pool* 이었던 이유 를 *진짜 *layer 별로 *파고든다*.

읽고 가셔도 좋은 분:
1. *Spring Boot 1-3 년차* — `maximum-pool-size: 10` 만 알고 *나머지는 *기본값 그대로* 쓰는 사람
2. *"connection pool 이 *왜 100 으로 *늘렸는데 *오히려 더 느려졌어?"* 의 *진짜 답* 이 궁금한 사람
3. *Connection Leak* 으로 *production 장애* 한 번 *겪어본 사람* — *재발 방지 진단법* 정리하고 싶은 사람

---

## TL;DR

> *HikariCP* 가 *Spring Boot 의 *기본 connection pool*. *Pool 의 본질은 *DB 와 *비싼 *TCP+TLS+인증* 을 *재사용* 하는 것*. *Pool size 가 무한대 *클수록 좋지 *않음* — *DB max_connections 의 *연산* 결과로 *정확히* 계산. *실전 *4 가지 사고 패턴* (pool 고갈 / connection leak / dead connection / DB restart 후 stale) 의 *진단 + 해결* 까지.

**한 표로**:

| 증상 | 원인 | HikariCP 설정 |
|------|------|------------|
| `Connection is not available, request timed out after 30000ms` | Pool 고갈 | `maximum-pool-size`, `connection-timeout` |
| Pool 갯수 증가, 회수 안 됨 | Connection Leak (트랜잭션 누락 / close 누락) | `leak-detection-threshold` |
| `Connection refused` 가 *간헐적* | Dead connection (DB 재시작 / NAT timeout) | `keepalive-time`, `validation-timeout` |
| DB CPU 80%+, app 멀쩡 | Pool 너무 큼 → DB 경합 | Pool size *감소* + read replica |

---

## 0. *왜 *Connection Pool* 인가 — *raw JDBC 의 *비용***

### 0.1 *DB 연결 1 회 의 *진짜 비용***

```
Client → DB 연결 한 번:
   1) TCP 3-way handshake             ~1ms
   2) TLS handshake (SSL 켜져있으면)   ~50-200ms
   3) DB 인증 (user + password 검증)   ~10-30ms
   4) 세션 초기화 (search_path, encoding) ~5ms
                                       ━━━━━━━━
                                       총 ~70-240ms
```

> 1 요청 1 연결 = *연결만 으로도 *latency p99 가 *200ms+ *. *비현실적*.

### 0.2 *Pool 의 효과 — *재사용***

```
Pool 시작 시:
  - 10 개 연결 미리 만듬 (각각 100ms × 10 = 1초 *애플리케이션 시작 시 *소비*)

요청 처리 시:
  1) Pool 에서 *이미 열린 연결 *빌림*     ~0.1ms
  2) 쿼리 실행
  3) Pool 로 *반납*                       ~0.1ms

→ 연결 cost = *완전 무료* 가까움 (사용자 입장에선)
```

> *Pool 의 본질* — *비싼 자원 (DB connection) 의 *생성 cost 를 *시작 시점에 *몰아서 *지불* 하고, *이후 무한히 *재사용*.

---

## 1. *HikariCP — *Spring Boot 의 *기본 선택***

### 1.1 *왜 HikariCP 가 *기본*

Spring Boot 2.x 부터 *HikariCP* 가 *default*. *Apache DBCP, c3p0* 등이 *과거 표준* 이었으나 *HikariCP 가 *3-10× 빠름*. 이유:

```
DBCP / c3p0:
  - Pool 관리 자체 가 *synchronized 블록* 으로 *경합*
  - Connection 객체 wrapping 이 *반사 (reflection)*

HikariCP:
  - Lock-free 자료구조 (FastList, ConcurrentBag)
  - Bytecode generation 으로 *wrapping 비용 최소*
  - JIT 친화 코드
```

### 1.2 *POM / Gradle 설정 — *자동 적용***

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    runtimeOnly("org.postgresql:postgresql")
}
```

→ *HikariCP 가 *spring-boot-starter-jdbc* 의 *transitive 의존성*. *별도 설정 불필요*.

---

## 2. *11 가지 핵심 설정 — *진짜 의미***

### 2.1 *application.yml 의 *전체 설정 예시***

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/lemuel
    username: lemuel
    password: ${DB_PASSWORD}
    hikari:
      # === Pool 크기 ===
      maximum-pool-size: 20            # 최대 connection 수
      minimum-idle: 10                 # 최소 idle connection

      # === Timeout ===
      connection-timeout: 3000         # connection 얻는 데 *최대 wait* (ms)
      validation-timeout: 5000         # validation query 실행 *최대 wait*
      idle-timeout: 600000             # idle 상태 *10 분* 지나면 닫음
      max-lifetime: 1800000            # connection 최대 *30 분* 생존
      keepalive-time: 30000            # 30 초마다 살아있는지 ping

      # === 진단 ===
      leak-detection-threshold: 60000  # 60 초 이상 borrow 상태면 *leak 의심*
      register-mbeans: true            # JMX 노출 (Actuator 통합)

      # === 이름 ===
      pool-name: lemuel-pool
```

### 2.2 *각 옵션의 *의미와 *현실적 *값***

#### `maximum-pool-size` (default: 10)

> Pool 의 *최대 connection 수*. 가장 자주 만지는 옵션.

**계산 공식 (Brett Wooldridge, HikariCP 저자)**:
```
connections = ((core_count × 2) + effective_spindle_count)

# 예: 4 코어 SSD 서버:
#   connections = (4 × 2) + 1 = 9
```

> *현실에서는 *훨씬 큰 값 (20-50)* 으로 설정. 이유:
> - Spring 의 *transaction 안 *외부 호출 (HTTP)* 가 *connection 점유 시간 늘림*
> - DB CPU 외 *I/O wait* 으로 *core × 2* 보다 더 활용 가능

**현실적 권장**:
```
TPS < 100  →  pool 10  (default)
TPS 100-1K →  pool 20-30
TPS 1K-5K  →  pool 30-50 (인스턴스당)
TPS > 5K   →  read replica + connection pool 분리
```

#### `minimum-idle` (default: maximum-pool-size)

> 항상 *준비된 idle connection 의 *최소 수*. *peak time 대비*.

```
요청 burst 직전:
  idle = 0, 새 request 100 개
  → connection 만들기 100 × 70ms = 7초 latency 폭발

vs

  minimum-idle = 10, 새 request 100 개
  → 10 개 즉시 사용 + 90 개 wait
  → 평균 *훨씬 빠름*
```

#### `connection-timeout` (default: 30000ms = 30 초)

> *Pool 에서 connection 얻기 까지 *최대 *대기 시간*.

> ⚠️ **default 30 초는 *너무 김***. *production 에서는 *3-5 초* 권장. *그래야 *pool 고갈 시 *빠른 fail-fast → upstream 회복*.

#### `idle-timeout` (default: 600000ms = 10 분)

> idle 상태인 *connection 을 *닫는 *시간*. *minimum-idle 위* 만 적용.

> *10 분 권장*. *짧으면 *재생성 비용*, *길면 *DB 측 connection 늘어남*.

#### `max-lifetime` (default: 1800000ms = 30 분)

> Connection 의 *최대 생존 시간*. 이 시간 지나면 *closed + 재생성*.

> **중요**: DB / NAT / Firewall 의 *idle timeout 보다 *짧게* 설정. 예: AWS RDS 의 *기본 wait_timeout* 이 *8 시간* 이지만 *NAT gateway* 의 *idle timeout* 이 *5 분*. *max-lifetime 을 *4 분* 으로 둬야 *NAT 가 끊은 connection 사용 *방지*.

#### `keepalive-time` (HikariCP 4.0+)

> *Idle connection 에 *주기적 ping*. *dead connection 조기 발견*.

> *production 권장 30 초*. *없으면 *NAT timeout / 방화벽 RST 에 의한 *dead connection* 이 *다음 요청 때 *5xx*.

#### `leak-detection-threshold` (default: 0 = 비활성)

> *Borrow 후 *반납 안 한 *connection 의심* 시간. 초과 시 *warning log + stack trace*.

> *production 권장 60 초*. *60 초 이상 *connection 점유 = 거의 *bug*. *leak 진단의 *결정적 도구*.

```
[WARN] Connection leak detection triggered for connection
       org.postgresql.jdbc.PgConnection@1234abcd,
       stack trace follows
   at OrderService.processOrder(OrderService.java:42)
   at ...
```

→ *Stack trace 가 *정확히 *leak 코드 위치* 가리킴.

#### `validation-timeout` (default: 5000ms)

> Connection 유효성 검사 (`SELECT 1`) 의 *timeout*. *connection-timeout 보다 작아야 함*.

#### `register-mbeans` (default: false)

> *JMX 노출*. *Spring Boot Actuator + Micrometer* 가 *자동 metrics 발행* 하려면 *true*.

```
hikaricp_connections           # 총 connection 수
hikaricp_connections_active    # 사용 중
hikaricp_connections_idle      # idle 대기
hikaricp_connections_pending   # ★ 대기 중 (이게 > 0 이면 *pool 부족 신호*)
```

---

## 3. *Pool sizing — *DB max_connections* 와의 관계*

### 3.1 *위험한 함정 — *pool 크게 = 빠름 (오해)***

> *"pool 100 으로 늘렸는데 *응답이 *더 느려졌어?"* — *흔한 *오해*.

이유:
```
DB max_connections = 100
  
인스턴스 10 × pool 50 = 500 connection 요청
  → DB 가 *400 개 거부 (또는 *경합 폭발*)
  → 인스턴스 측에서 *connection 회수 + 재시도 폭주*
  → throughput 오히려 감소
```

### 3.2 *정확한 계산 공식*

```
DB max_connections >= (인스턴스 수 × pool size) 
                     + DBA / monitoring connection 여유 (~ 30)
                     + 마이그레이션 / 운영 도구 (~ 20)

예) PostgreSQL max_connections = 200
    인스턴스 10 개 → pool size = (200 - 50) / 10 = 15
```

### 3.3 *Replica 활용 — *write / read 분리***

```yaml
# 약 80% 트래픽이 read 인 경우
spring:
  datasource:
    write:
      jdbc-url: jdbc:postgresql://pg-master:5432/db
      maximum-pool-size: 20
    read:
      jdbc-url: jdbc:postgresql://pg-replica:5432/db
      maximum-pool-size: 30   # 더 큼 (read 가 80% 트래픽)
```

> 같은 *총 connection 수* 로 *2-5× throughput*.

---

## 4. *실전 Postmortem 4 건*

### Case 1 — *Pool 고갈 + connection-timeout 30초 의 *재앙* 시너지**

**증상**:
```
[ERROR] HikariPool-1 - Connection is not available, request timed out 
        after 30000ms.
```
*peak hour 에 *모든 요청 30 초 지연*. *사용자 *대량 이탈*.

**진단**:
```bash
# Grafana 에서 확인
hikaricp_connections_pending  →  ~ 300  (★ pool 부족)
hikaricp_connections_active   →  20    (max-pool-size 도달)
```

**원인**:
- TPS 가 *예상 보다 *3 배 증가*
- `connection-timeout: 30000` (default) → *30 초 동안 wait* → *upstream 도 *대기 누적*
- *connection 빌리려는 *thread queue 폭발*

**해결**:
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 50          # 20 → 50 (DB max_connections 확인 후)
      minimum-idle: 20
      connection-timeout: 3000       # 30 초 → 3 초 (★ fail-fast)
```

**교훈**:
> *connection-timeout: 30 초* 가 *upstream 의 *fail-fast* 를 *막아서 *재앙 *시너지*. *반드시 *3-5 초* 로 *축소*. *그래야 *circuit breaker* 가 *작동*.

### Case 2 — *Connection Leak — *@Transactional 누락*

**증상**:
```
시간이 지날수록 hikaricp_connections_active 가 *천천히 증가*.
서버 시작 ~ 6 시간 후 pool 고갈.
```

**진단** — `leak-detection-threshold: 60000` 켰더니:
```
[WARN] Apparent connection leak detected: 
   at com.lemuel.order.service.OrderService.processOrder(OrderService.java:127)
```

**원인 코드**:
```java
public void processOrder(Long orderId) {
    Order order = orderRepository.findById(orderId).get();
    
    // 외부 HTTP call (PG 결제)
    paymentClient.charge(order);   // ★ 여기서 60+ 초 → leak 의심
    
    order.setStatus(PAID);
    orderRepository.save(order);
}
```

**원인**:
- `@Transactional` *누락*. 메서드 전체가 *non-tx*
- JPA 가 *implicit transaction* 으로 *connection 빌림*
- 외부 HTTP call 60 초 동안 *connection 점유*
- *high concurrency* 에 leak처럼 누적

**해결**:
```java
@Transactional
public void processOrder(Long orderId) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    
    // tx 안에서 외부 호출 → *위험 — 더 큰 안티패턴*
    paymentClient.charge(order);   // ★ 여기 30초 = tx 30초 점유
    
    order.setStatus(PAID);
}
```

> ⚠️ **이건 더 큰 안티패턴**. *transaction 안 에서 *외부 HTTP* 호출 = *DB connection 점유 *수 십 초*.

**진짜 해결 — *tx 분리***:
```java
public void processOrder(Long orderId) {
    Order order = loadOrder(orderId);            // tx 1 (read only)
    PaymentResult res = paymentClient.charge(order);  // *외부 호출 — tx 밖*
    completePayment(orderId, res);               // tx 2 (write)
}

@Transactional
public void completePayment(Long orderId, PaymentResult res) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    order.setStatus(res.isSuccess() ? PAID : FAILED);
}
```

**교훈**:
> *Transaction 안에 *외부 호출 (HTTP / Kafka send / 다른 DB call)* 절대 X*. *transaction 은 *짧을수록 좋음*.

### Case 3 — *Dead Connection — NAT timeout*

**증상**:
```
[ERROR] org.postgresql.util.PSQLException: An I/O error occurred while
        sending to the backend.
```
*간헐적* 으로 *발생*. *재시도 시 정상*.

**진단**:
- 인프라 팀에 *NAT gateway idle timeout 확인* → *350 초*
- HikariCP `max-lifetime: 1800000` (30 분) → NAT 보다 *큼*
- 결과: *5 분 30 초 동안 *idle connection* 이 *NAT 측에서 *RST*
- 다음 요청 시 *dead connection* 사용 → I/O error

**해결**:
```yaml
spring:
  datasource:
    hikari:
      max-lifetime: 240000     # 30 분 → 4 분 (NAT timeout 350 초보다 짧게)
      keepalive-time: 30000    # 30 초마다 ping
```

**교훈**:
> *AWS RDS Default wait_timeout = 28800 (8 시간)* 와 *NAT idle timeout (보통 5 분)* 의 *gap*. *HikariCP 의 *max-lifetime 은 *모든 중간 layer 의 *timeout 보다 *짧아야 함*.

### Case 4 — *DB Restart 후 *모든 connection stale***

**증상**: DB *재시작 직후 *수 분간 *전 인스턴스 5xx*.

**원인**:
- DB restart → 모든 *기존 connection 끊김*
- HikariCP 가 *connection 사용 시점에 *발견*
- *예외 → 인스턴스가 *재연결 시도*
- *DB 재시작 직후 *부하 폭주* → *재연결 실패*

**해결 — *Connection validation*:
```yaml
spring:
  datasource:
    hikari:
      keepalive-time: 30000              # 30 초 마다 ping
      validation-timeout: 5000
      # 연결 빌릴 때마다 validation 안 함 (HikariCP 는 자동)
```

또는 *Spring Boot 의 *retry*:
```java
@Retryable(value = SQLException.class, maxAttempts = 3,
           backoff = @Backoff(delay = 1000, multiplier = 2))
public List<Order> findOrders() {
    return orderRepository.findAll();
}
```

---

## 5. *모니터링 — *Actuator + Micrometer + Grafana***

### 5.1 *Actuator 활성화*

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, metrics, hikaricp
  metrics:
    distribution:
      percentiles-histogram:
        "[hikaricp.connections.acquire]": true
```

### 5.2 *PromQL 쿼리 — Grafana dashboard*

```promql
# Active connection (현재 사용 중)
hikaricp_connections_active{pool="lemuel-pool"}

# Pending (대기 중 — *이게 > 0 이면 *위험 신호*)
hikaricp_connections_pending{pool="lemuel-pool"}

# Connection 획득 latency p95
histogram_quantile(0.95, 
  rate(hikaricp_connections_acquire_seconds_bucket[5m]))

# Pool 사용률
hikaricp_connections_active / hikaricp_connections_max
```

### 5.3 *알람 설정 — 운영 정착*

```yaml
# Prometheus alert rule
groups:
- name: hikaricp
  rules:
  - alert: HikariCPPoolNearExhaustion
    expr: hikaricp_connections_pending > 0
    for: 1m
    annotations:
      summary: "DB pool 대기 큐 1분 이상 — pool 부족 의심"
  
  - alert: HikariCPPoolHighUtilization
    expr: (hikaricp_connections_active / hikaricp_connections_max) > 0.8
    for: 5m
    annotations:
      summary: "DB pool 사용률 80%+ 5분 — *증설 검토*"
```

---

## 6. *Connection Leak 진단 — *체계적 *5 단계***

### Step 1 — `leak-detection-threshold` *켜기*

```yaml
hikari:
  leak-detection-threshold: 60000   # 60 초
```

→ *Production 도 *늘 켜둘 것*. *overhead 0.1% 미만*.

### Step 2 — *Log 에 *stack trace 확인*

```
[WARN] HikariPool-1 - Apparent connection leak detected
       stack trace:
   at com.lemuel.order.OrderService.processOrder(OrderService.java:42)
   at com.lemuel.order.OrderController.create(OrderController.java:18)
   ...
```

### Step 3 — *해당 코드 패턴 분석*

- `@Transactional` 누락?
- Transaction 안 외부 호출?
- `EntityManager` 직접 사용 후 `close()` 누락?
- *Spring AOP proxy 우회* (self-invocation `this.method()`)?

### Step 4 — *재현 + 수정*

```java
@Test
void leak_when_self_invocation() {
    // this.processOrder(1L);  ← @Transactional 적용 안 됨
}
```

### Step 5 — *Prometheus 알람 추가*

```promql
# leak 발견 시 즉시 알람
rate(hikaricp_connections_leakdetected_total[5m]) > 0
```

---

## 7. *학습 압축 — *현장 *체크리스트***

### 7.1 *production deployment 전 *반드시 확인***

- [ ] `connection-timeout: 3000` 이하 (default 30000 X)
- [ ] `max-lifetime` < NAT idle timeout
- [ ] `keepalive-time: 30000` 설정
- [ ] `leak-detection-threshold: 60000` 활성
- [ ] DB `max_connections >= 인스턴스 수 × pool size + 50 여유`
- [ ] Actuator + Micrometer + Prometheus 노출
- [ ] Grafana dashboard 의 `hikaricp_connections_pending` 알람

### 7.2 *부하 테스트 시 *반드시 확인***

- [ ] *5 분 부하 후 *pool active 가 *안정* 상태인가?
- [ ] `pending` 이 *> 0* 발생 시점 의 *TPS 가 *기준*?
- [ ] *connection 획득 p95* 가 *목표 latency 의 *10% 이하*?

### 7.3 *흔한 안티 패턴 5 종*

| 패턴 | 왜 잘못 |
|------|--------|
| `maximum-pool-size: 200` | DB max_connections 초과 → 경합 폭발 |
| `connection-timeout: 30000` | fail-fast 불가, upstream 누적 |
| Transaction 안 외부 HTTP 호출 | connection 수 십 초 점유 |
| `@Transactional` 누락 | implicit tx → connection leak |
| Self-invocation `this.tx_method()` | Spring AOP 우회 → tx 안 걸림 |

---

## 8. *마무리 — *Pool 의 *진짜 의미***

### 8.1 *Pool 은 *시스템 health 의 *심장박동***

> *DB Connection Pool 은 *백엔드의 *심장박동*. *pending 이 0 이면 건강*, *> 0 이면 *질병의 *조기 신호*. *Grafana 의 *3 개 metric* (`active / idle / pending`) 만 *상시 본다면 *80% 의 *장애 사전 발견*.

### 8.2 *모든 옵션 의 *왜* 를 이해할 것*

> *옵션을 *값 그대로 *복사 X*. *내 시스템의 *TPS / DB 사양 / 네트워크 topology* 를 *고려해서 *각자의 *왜* 를 답할 수 있어야 함. *blindly 따라가는 설정 = 다음 사고 까지의 *시간 문제*.

### 8.3 *이력서 변환 hook*

> *"DB Connection Pool tuning 경험"* 한 줄에:
> - HikariCP 11 옵션 의 *왜*
> - Pool sizing 공식 (Brett Wooldridge + DB max_connections)
> - Leak detection 절차 5 단계
> - NAT timeout / DB restart / Transaction misuse 의 *4 가지 사고 패턴*
> - Actuator + Micrometer + Prometheus + Grafana 모니터링
> 
> *4 단 깊이 면접 답변 hook* 모두 준비.

---

## 부록 — *5 분 안에 *셋팅 하는 *현실적 *application.yml**

```yaml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST}:5432/${DB_NAME}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    hikari:
      pool-name: ${SPRING_APPLICATION_NAME:app}-pool
      maximum-pool-size: 30
      minimum-idle: 10
      connection-timeout: 3000
      validation-timeout: 3000
      idle-timeout: 600000
      max-lifetime: 240000          # NAT timeout 보다 짧게
      keepalive-time: 30000
      leak-detection-threshold: 60000
      register-mbeans: true
      
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, hikaricp
  metrics:
    distribution:
      percentiles-histogram:
        "[hikaricp.connections.acquire]": true
```

→ *5 분 안에 *production-grade *Pool 설정 완료*.

---

*다음 글:* *JPA 의 *flush 시점 + lazy loading + N+1 문제* — *Connection Pool 위에서 *얼마나 *추가 *latency 가 *발생하는가*, *Profile 로 *진짜 *진단법*.
