---
layout: post
title: "*8 가지 체크리스트* 로 *내 정산 시스템* 을 *자가 검수* 했다 — *동시성 / 트랜잭션 / 보안 / N+1 / 재처리 / 로그 / 예외 / 도메인 규칙*"
date: 2026-06-18 03:30:00 +0900
categories: [backend, architecture, code-review, settlement]
tags: [hexagonal, settlement, concurrency, transaction, security, n-plus-one, idempotency, observability, exception, domain-driven]
---

> *"운영해 본 적 없는 코드 는 *서비스 가 *아니다*."* 
>
> *주문·결제·정산* 처럼 *돈* 이 *흐르는 시스템* 은 *코드를 *짠 사람조차 *모르는 사이* *조용히 *깨진다*. *동시성 / 트랜잭션 / 보안 / N+1 / 재처리 / 로그 / 예외 / 도메인 규칙* — *8 가지 영역* 을 *체크리스트화* 하지 않으면 *모르는 사이 가다가 *터진다*.
>
> 이 글은 *내 settlement (이커머스 정산 MSA, Spring Boot 4 hexagonal)* 를 *그 8 가지 체크리스트* 로 *자가 감사* 한 *실제 결과* 다. *✅ 안전한 것* 도, *❌ 진짜 깨진 것* 도, *⚠️ 마지막 5%* 도 *솔직하게 *기록*.

---

## TL;DR

> *전반적으로 *견고* 했다 — *ArchUnit + Triple Idempotency + Outbox* 같은 *문서화된 약속* 이 *실제 코드에 *정확히 반영* 되어 있음. *그러나 *진짜 *critical* 두 가지: *(1) PaymentController 의 BOLA (Broken Object Level Authorization)* — *타인 결제 ID 로 *환불 가능*, *(2) Settlement / Order 의 public setStatus()* — *상태 머신 무력화 가능*. *나머지는 *N+1 2 건* / *settlement-service logback-spring.xml 누락* / *Outbox 지수 backoff 부재* 같은 *완성도 마지막 5%* 수준. *수정 PR* 을 *그 자체로 *포트폴리오 자산* 으로 *만들 수 있는 *수준의 *결함 분포*.

---

## 0. *왜 *8 가지 인가 — *체크리스트의 *철학*

### 0.1 *모든 *production 사고* 는 *이 8 개 *중 *한 곳* 에서 *튀어나온다*

수년간 *결제 / 정산 / 트랜잭션* 운영 코드를 *고치고 *대응하고 *postmortem* 을 쓴 경험을 *압축* 하면, *production 사고* 는 *결국* 이 *8 가지 영역 의 *조용한 누락* 에서 *나온다*.

| 영역 | 사고 시나리오 (실제 자주 보는 것) |
|---|---|
| *동시성* | 같은 결제건이 *동시에 2 번 capture* → 잔고 차감 2 번 |
| *트랜잭션 경계* | Kafka publish 성공 + DB rollback → *유령 이벤트* 발생 |
| *보안* | *타인 paymentId* 로 *환불 가능* (BOLA / IDOR) |
| *N+1* | 일일 정산 *10 만건* 에서 *raw query 10 만 번* → DB CPU 100% |
| *재처리* | Kafka consumer 실패 시 *DLT 없음* → *영원히 stuck* |
| *로그* | 사고 났는데 *traceId chain 끊김* → *근본 원인 30 분 *찾기* |
| *예외* | `catch (Exception e) { log.error(...); }` → *silent fail* |
| *도메인 규칙* | `payment.setStatus(REFUNDED)` 외부 호출 → *상태 머신 우회* |

→ *체크리스트 가 없으면 *모르는 사이* *이 중 *몇 개가 *깨져 있다*. *체크리스트 가 있으면 *깨진 것을 *발견하고 *고친다*.

### 0.2 *체크리스트 의 *3 가지 가치*

- *발견* — *모르는 결함* 을 *체계적으로 *찾는다*
- *증명* — *내 시스템 이 *어디까지 *견고한지* 를 *3 자에게 *제시* 할 수 있다
- *학습* — *각 항목 마다 *왜 그 항목 인지* 를 *공부하게 된다*

---

## 1. *영역 1 — *동시성 (Concurrency)*

### 1.1 *체크리스트*

- *결제 capture / 환불 / 정산 생성* 같은 *돈 다루는 흐름* 에 *비관락 (`@Lock(PESSIMISTIC_WRITE)`)* 또는 *낙관락 (`@Version`)* 있나?
- *재고 / 쿠폰 사용 / 시드 차감* 같은 *공유 자원 차감* 에 *동시성 보호* 있나?
- *Outbox poller* 의 *PENDING → PUBLISHED 전환* 에 *동시 실행 보호* (ShedLock / `FOR UPDATE SKIP LOCKED`) 있나?
- *Idempotency-Key* 가 *실제 컨트롤러 / 서비스 에 적용* 되어 있나?

### 1.2 *내 코드 검수 결과 — ✅ 전반 안전*

| 항목 | 결과 | 증거 |
|---|---|---|
| 비관락 (refund/settle/payout) | ✅ | `PaymentJpaRepository.java:32` `@Lock(PESSIMISTIC_WRITE)` + `SpringDataSettlementJpaRepository.java:25,41,56` 환불·확정·holdback release 전부 FOR UPDATE |
| 낙관락 `@Version` | ✅ | `SettlementJpaEntity.java:74`, `ReservationJpaEntity.java:104`, `ProductVariantJpaEntity.java:41`, `PayoutJpaEntity.java:17` |
| 재고 (`decreaseStockIfAvailable`) | ✅ | `SpringDataProductVariantRepository.java:39` 조건부 UPDATE → 영향행 0 분류 후 분기 |
| 쿠폰 | ✅ | `CouponPersistenceAdapter.java:47` `incrementUsedCountIfAvailable` + UNIQUE 제약 + `DataIntegrityViolationException` 폴백 |
| Outbox poller | ✅ | `SpringDataOutboxEventRepository.java:35` `FOR UPDATE SKIP LOCKED` + lease, `LedgerOutboxPoller.java:37` 는 `@SchedulerLock` |
| Idempotency-Key | ✅ (단, 환불만) | `PaymentController.java:105` 부분환불 키 필수 + `MissingIdempotencyKeyException` |

### 1.3 *발견된 결함 — ⚠️ 1 건*

> *`CapturePaymentUseCase.java:51` — `loadById` (락 없음).* 동시 capture 가 같은 paymentId 로 들어오면 *status 충돌 가능*.

→ Fix : `loadByIdForUpdate` 로 통일.

### 1.4 *왜 비관락 이 *돈 다루는 흐름에 *적절한가*

- *낙관락* — 충돌 시 *retry* 가 *비즈니스 적으로 *허용될 때*. *블로그 좋아요* 같은 *비-금전* 흐름
- *비관락* — *retry 가 *위험* 할 때. *환불 / capture* 는 *2 번 retry 가 *2 번 환불* 위험 → *애초에 *직렬화* 가 안전

→ *내 코드는 *금전 흐름 에 *비관락 *통일* — 옳은 선택.

---

## 2. *영역 2 — *트랜잭션 경계 (Transaction boundary)*

### 2.1 *체크리스트*

- `@Transactional` 이 *application 서비스 (UseCase)* 에 *제대로 붙어 있나*?
- *어댑터 (out/persistence)* 가 *자체 @Transactional* 을 가져서 *경계 부서지지 않나*?
- *Kafka publish + DB 쓰기* 가 *같은 트랜잭션* 안에 있나, 아니면 *Outbox 로 분리* 되어 있나?
- `REQUIRES_NEW` 가 *부적절한 곳* (예: 도메인 이벤트 처리 안) 에 쓰여 *부분 commit* 위험 없나?

### 2.2 *내 코드 검수 결과 — ✅ 거의 완벽*

| 항목 | 결과 | 증거 |
|---|---|---|
| UseCase 에 @Transactional | ✅ | `CapturePaymentUseCase.java:26`, `RefundPaymentUseCase.java:28` (REPEATABLE_READ), `CreateSettlementFromPaymentService.java:27` |
| Kafka publish + DB | ✅ Outbox 분리 | `OutboxBackedEventPublisher.java:75-95` — 도메인 tx 안에서 outbox 테이블에만 INSERT, 실 발행은 비동기 poller |
| REQUIRES_NEW | ✅ 의도적 사용만 | `TenderRefundExecutor.java:64,99` (tender 별 격리), `AuditLogger.java:31` (감사 분리), `PayoutSingleExecutor.java:39` (payout 격리) |
| readOnly = true | ✅ 일관 | 조회 전용 서비스 (`SettlementQueryService.java:20`, `GenerateCashflowReportService.java:24`) 모두 적용 |

### 2.3 *발견된 결함 — ⚠️ 1 건*

> `PasswordResetTokenPersistenceAdapter.java:20,28,35,42` — *어댑터가 자체 @Transactional 보유.* *헥사고날 경계 위반*.

→ Fix : `@Transactional` 을 *application 서비스로 끌어올림*.

### 2.4 *Outbox 가 *왜 *트랜잭션 경계 의 *교과서 해법 인가*

```
[잘못된 패턴]
@Transactional
void capture() {
  paymentRepo.save(payment);       // DB tx 안
  kafkaTemplate.send("captured");  // ← Kafka publish 는 tx 밖
  // → DB rollback 되어도 Kafka 메시지 이미 나감 = 유령 이벤트
}

[Outbox 패턴]
@Transactional
void capture() {
  paymentRepo.save(payment);       // DB tx
  outboxRepo.save(new OutboxEvent("captured", payload));  // 같은 tx
  // → 둘 다 commit 또는 둘 다 rollback. 원자성 보장
}

// 별도 poller 가 2초 주기로 outbox 읽어서 Kafka 발행 (at-least-once)
```

→ *내 코드는 *이 패턴 *그대로 *적용* . `OutboxBackedEventPublisher` + `OutboxPublisherScheduler` 가 *교과서 그대로*.

---

## 3. *영역 3 — *보안 (Security)*

### 3.1 *체크리스트*

- *SQL Injection* — JPQL / native query 문자열 concat?
- *인증 우회 / 권한 누락* — `@PreAuthorize` 없는 민감 endpoint?
- *민감 정보 로깅* — `log.info` 가 카드번호 / JWT / 토스 secret key 그대로?
- *JWT 검증* — `verifyWith(secretKey)` 진짜로 호출?
- *BCrypt cost 12*, *CSRF / CORS*, *환불 동시성*, *Webhook 서명*, *Mass assignment*, *Rate limiting*

### 3.2 *내 코드 검수 결과 — ❌ *2 건 CRITICAL BOLA**

| 항목 | 결과 |
|---|---|
| SQL Injection | ✅ 전체 @Query 18개 named parameter 만 사용, native 0 |
| JWT 검증 | ✅ `JwtUtil.java:57-62` `Jwts.parser().verifyWith(secretKey).build().parseSignedClaims()` + 키 32 bytes 미만 시 IllegalState |
| BCrypt cost=12 | ✅ `SecurityConfig.java:37` `new BCryptPasswordEncoder(12)` |
| CSRF / CORS | ✅ JWT stateless 면 CSRF disable 정당, CORS 는 env var 화이트리스트 |
| 환불 동시성 | ✅ Pessimistic Lock + UNIQUE idempotencyKey |
| Mass assignment | ✅ DTO 가 화이트리스트 필드만 노출 |

#### ❌ *CRITICAL #1 — PaymentController BOLA*

```java
// PaymentController.java:73, 85, 99
@PatchMapping("/{id}/authorize")
public ResponseEntity<?> authorize(@PathVariable Long id, ...) { ... }

@PatchMapping("/{id}/capture")
public ResponseEntity<?> capture(@PathVariable Long id, ...) { ... }

@PatchMapping("/{id}/refund")
public ResponseEntity<?> refund(@PathVariable Long id, ...) { ... }
```

- *@PreAuthorize 없음*, *소유자 검증 없음*
- *Spring Security 의 `anyRequest().authenticated()`* 만 — *로그인만 했으면 누구나 호출 가능*
- *익스플로잇*: 사용자 A 가 `PATCH /payments/9999/refund?amount=100000` → *타인 결제 환불 가능*

→ Fix :

```java
AuthPrincipal principal = (AuthPrincipal) SecurityContextHolder.getContext()
    .getAuthentication().getPrincipal();
if (!principal.role().equals("ADMIN")) {
    PaymentDomain p = loadPaymentPort.findById(paymentId)
        .orElseThrow(() -> new PaymentNotFoundException(paymentId));
    if (!p.getOrderUserId().equals(principal.userId())) {
        throw new AccessDeniedException("본인의 결제만 가능");
    }
}
```

#### ❌ *CRITICAL #2 — RefundHistoryController BOLA*

```java
// RefundHistoryController.java:38
@GetMapping("/api/payments/{paymentId}/refunds")
public List<RefundItem> getRefunds(@PathVariable Long paymentId) { ... }
```

- *타인 paymentId 의 환불 이력 + *idempotencyKey 응답 노출*
- BOLA 가 *idempotencyKey 노출* 과 *결합* 되면 *재사용 공격* 가능

### 3.3 *발견된 결함 — ⚠️ HIGH 1 건*

> `TossPaymentService.java:176` — `log.error("... paymentKey={} ...", paymentKey, ...)` *paymentKey 전체값 출력*. PCI-DSS 상 *결제 자격증명* 에 준하는 민감값.

→ Fix : `paymentKey.substring(0, 8) + "****"` 마스킹.

### 3.4 *그 외 (낮은 우선)*

- *Toss webhook HMAC 검증 미구현* — 코드 주석 으로 *Phase 3 별도 보안 설계 필요* 명시. 의도적 미구현.
- *회원가입 / 비번재설정 rate limit 없음* — Bucket4j 가 login / payment 에만 적용. 토큰 열거 공격 위험.

---

## 4. *영역 4 — *N+1 query*

### 4.1 *체크리스트*

- `@OneToMany / @ManyToOne` fetch = LAZY 디폴트인데 *서비스에서 stream / map 하면서 getXxx()* 호출?
- `open-in-view` 가 false?
- `JOIN FETCH` / `@EntityGraph` 적절히 쓰였나?
- Spring Batch 가 *findAll() 후 stream* 같은 *메모리 폭발* 없나?
- `@Modifying clearAutomatically` 누락?

### 4.2 *내 코드 검수 결과 — ⚠️ 2 건 실제 N+1*

**구조적 결정** : 이 코드베이스는 *JPA 양방향 / 단방향 연관관계를 *일절 쓰지 않음*. `OrderJpaEntity.userId : Long` 같이 *"FK as Long"* 패턴. → *연관 traversal N+1 0 개*.

#### ❌ HIGH — `OrderPersistenceAdapter` 의 *수동 N+1*

```java
// OrderPersistenceAdapter.java:54-59
public List<Order> findAll() {
  return orderJpaRepository.findAll().stream()
      .map(this::toDomainWithItems)  // ← Order 1 건당
      .toList();
}

private Order toDomainWithItems(OrderJpaEntity entity) {
  List<OrderItem> items = orderItemRepository
      .findByOrderIdOrderByIdAsc(entity.getId());  // ← 추가 SELECT
  return ...;
}
```

- 100 건 → *101 round-trip*
- Fix : `findAllByOrderIdIn(orderIds)` 한 방 + `Map<Long, List<OrderItem>>` 그룹핑

#### ❌ MED — `IndexSettlementService` bulk indexing

```java
// IndexSettlementService.java:62-66
settlementIds.stream()
    .map(id -> findById(id))  // ← N 회 SELECT
    .forEach(es::index);
```

- 1 만 건 인덱싱 → *1 만 round-trip*
- Fix : `settlementJpaRepository.findAllById(ids)` 한 방

#### ⚠️ Spring Batch 메모리 폭발

```java
// CreateDailySettlementsService.java:32-43
List<Payment> all = findCapturedPaymentsByDate(date);  // 일자 전체 in-memory
return all.stream()
    .map(this::toSettlement)
    .toList();
// → 일일 결제 10 만 건 시 OOM
```

→ Fix : Chunk + `JdbcPagingItemReader(chunkSize=1000)` 또는 `flush()/clear()` 주기적.

### 4.3 *그 외*

- `open-in-view: false` ✅ 4 개 yml 모두 명시
- 인덱스 ✅ payment_id (V3 UNIQUE), order_id, user_id, status+date 등 거의 모든 핫 컬럼 커버
- ⚠️ `@Modifying` 에 `clearAutomatically=true` 누락 (coupon / productTag / ledgerOutbox)

---

## 5. *영역 5 — *재처리 (Resilience)*

### 5.1 *체크리스트*

- Outbox poller 가 publish 실패 시 *retry / backoff / DLQ* 가 *진짜* 구현?
- Kafka consumer 에 *retry topic / DLQ / DefaultErrorHandler* 있나?
- processed_events 가 *진짜로 매 consume 마다 check + insert*?
- Toss 호출 실패 시 *Resilience4j* 적용?
- Spring Batch 정산 잡 실패 시 *step restart*?
- *Triple Idempotency* (outbox UUID + processed_events PK + payment_id UNIQUE) 가 *실제 마이그레이션* 에 모두?

### 5.2 *내 코드 검수 결과 — ✅ 전반 잘됨*

| 항목 | 결과 | 증거 |
|---|---|---|
| Outbox retry → DLQ | ✅ | `OutboxBatchEventPublisher.java:101-108` markFailed → retryCount 누적, 10 회 도달 시 FAILED + 즉시 DLQ |
| Kafka DLT | ✅ | `KafkaErrorHandlerConfig.java:165-186` `DefaultErrorHandler` + `DeadLetterPublishingRecoverer` + non-retryable 분류 |
| processed_events | ✅ | `PaymentEventKafkaConsumer.java:73-80, 107-111` 비즈니스 처리 전 `existsById` + 후 `save`, 같은 tx |
| Triple Idempotency 마이그레이션 | ✅ | V3 (settlements.payment_id UNIQUE) + V28 (outbox event_id UNIQUE) + V29 (processed_events PK) 모두 존재 |
| Toss Resilience4j | ✅ | `TossPaymentService.java:131-180` `@CircuitBreaker(name=tossPg, fallbackMethod) @Retry(name=tossPg)`, PG 별 독립 CB, PgRouter 폴백 chain |
| Claim lease | ✅ | `OutboxPublisherScheduler.java:33-77` `FOR UPDATE SKIP LOCKED` + `claimed_at` 1 분, 워커 죽으면 회수 |

### 5.3 *발견된 결함 — ⚠️*

- ⚠️ *Outbox backoff 가 fixed 2 s* — 지수 backoff 없음. Kafka broker 다운 시 매 2 초 재시도로 broker 회복 방해 가능
- ⚠️ *Kafka consumer 가 코드는 `FixedBackOff(2 s × 3)` 인데 *주석은 ExponentialBackOff* — 코드/문서 불일치
- ⚠️ *Spring Batch step 에 `faultTolerant()` 없음* — 1 건 실패가 *일일 정산 job 전체 fail*. 부분 격리 불가

### 5.4 *Triple Idempotency 의 *3 단 방어*

```
[L1] outbox_events.event_id UUID UNIQUE
     → producer side 중복 발행 차단
[L2] processed_events (consumer_group, event_id) PK
     → consumer side 중복 처리 차단
[L3] settlements.payment_id UNIQUE
     → 비즈니스 레벨 (1 결제 = 1 정산) 차단

→ 어느 한 layer 가 뚫려도 다음 layer 가 막는다.
   at-least-once 메시징 + idempotent 수신 의 교과서 패턴.
```

---

## 6. *영역 6 — *로그 / 모니터링 (Observability)*

### 6.1 *체크리스트*

- Micrometer 메트릭 이 *비즈니스 지표* 로 *진짜* emit?
- *구조화 로그 (JSON / MDC traceId)*?
- Actuator endpoint 가 *민감한 env / configprops* 차단?
- traceparent (W3C trace context) propagation 이 *Kafka 메시지 header* 로 전달?

### 6.2 *내 코드 검수 결과 — ⚠️ 한 개 큰 누락*

| 항목 | 결과 |
|---|---|
| Micrometer 광범위 | ✅ outbox/chargeback/refund/payout/holdback/pg_routing 등 dedicated counter / gauge / timer |
| order-service JSON 로그 | ✅ LogstashEncoder + traceId/userId/orderId/paymentId/settlementId/refundId MDC |
| Actuator | ✅ `include: health,info,metrics,prometheus` — env/configprops/beans 차단 |
| traceparent Kafka header | ✅ V40 outbox_traceparent 컬럼 + `KafkaOutboxPublisher.java:94-97` 헤더 주입 + DLQ replay 도 보존 → Tempo chain 완결 |

#### ❌ *큰 누락 — settlement-service 에 logback-spring.xml 없음*

- `order-service/src/main/resources/logback-spring.xml` 만 존재
- *settlement-service 는 운영 JSON 로깅 / PII 마스킹 / MDC 가 *적용 안 됨*
- *정산 사고* 시 *traceId chain 끊김* — Tempo / Kibana 에서 *order → settlement 흐름 추적 불가*

→ Fix : *shared-common 에 logback-spring.xml 을 둬서 *양 서비스 가 *공유* 하는 게 *깔끔*.

#### ⚠️ Kafka consumer-lag 메트릭 명시 바인딩 없음

- `outbox.pending.count` 는 *producer side* 만
- Spring Boot autoconfigure 가 일부 잡지만 *명시적 KafkaClientMetrics 등록* 권장
- 컨슈머 backlog 폭증 시 *알람 없음*

---

## 7. *영역 7 — *예외 처리 (Exception handling)*

### 7.1 *체크리스트*

- `@RestControllerAdvice` 글로벌 핸들러 있나?
- *광범위 swallow* (`catch (Exception e) { log; }`) 없나?
- *checked → unchecked* wrap 시 *cause chain* 살리나?
- *외부 API (Toss) 의 4xx / 5xx* 를 *도메인 예외로 변환*?
- *비즈니스 예외* vs *시스템 예외* 구분?

### 7.2 *내 코드 검수 결과 — ✅ 잘됨*

| 항목 | 결과 |
|---|---|
| @RestControllerAdvice | ✅ shared-common GlobalExceptionHandler (LOWEST precedence 폴백) + 도메인별 6 개 (HIGHEST) — `SettlementExceptionHandler / OrderExceptionHandler / PaymentExceptionHandler / UserExceptionHandler / ProductExceptionHandler / ReservationExceptionHandler` |
| Cause chain | ✅ `KafkaOutboxPublisher.java:58/60` `new RuntimeException("...", e)`, `TossPaymentService.java:161` `new IllegalStateException("...", e)` |
| Toss 4xx → 도메인 | ✅ `HttpClientErrorException` → `IllegalStateException` + Resilience4j ignore 처리, 5xx 는 retry 대상 |
| 비즈니스 vs 시스템 | ✅ `KafkaErrorHandlerConfig.java:169-173` `addNotRetryableExceptions(JsonProcessingException, IllegalArgumentException, IllegalStateException)` — 비즈니스 즉시 DLT, 시스템 (DB lock, IO) 만 재시도 |

### 7.3 *발견된 결함 — ⚠️ 1 건*

> `JwtAuthenticationFilter.java:57` — `catch (Exception ignored)` 의도적이지만 *최소한 debug 로그* 권장.

---

## 8. *영역 8 — *도메인 규칙 (Anemic check)*

### 8.1 *체크리스트*

- 도메인 모델이 *POJO 인데 *비즈니스 규칙이 *서비스에 흩어져* 있지 않나? (anemic)
- *상태 전이 (READY → AUTHORIZED → CAPTURED → REFUNDED)* 가 *도메인 메서드에서 enforce*?
- *수수료 / 정산 금액 계산* 같은 *불변식* 이 *도메인 안에*?
- *팩토리* 가 *불완전 객체 생성 차단*?

### 8.2 *내 코드 검수 결과 — ⚠️ Setter 무력화 위험*

| 항목 | 결과 |
|---|---|
| Settlement 도메인 행위 | ✅ `Settlement.java:137-217` 상태 전이 (`startProcessing/complete/fail/retry/confirm/cancel`), `:225-260` `adjustForRefund` + DONE 불변, `:339-392` holdback 정책 |
| Payment 도메인 행위 | ✅ `capture()/refund()/authorize()/planRefundFromTenders()` |
| 수수료 / 정산 금액 | ✅ `Settlement.java:105-111` `calculateCommissionAndNetAmount`, `Money` 값 객체 round HALF_UP 통일, `COMMISSION_RATE`/`SellerTier.rate()` 도메인 안 |
| 팩토리 | ✅ `Settlement.createFromPayment`, `Order.create/createMultiItem`, `PaymentDomain.createSplit` |

#### ❌ *심각 — public setStatus()* 가 *상태 머신 무력화*

```java
// Settlement.java:311
public void setStatus(SettlementStatus status) { this.status = status; }

// Refund.java:74
public void setStatus(Status status) { this.status = status; }

// → ChangeOrderStatusService.java:82,93
order.setStatus(target);  // ← 도메인 메서드 우회, 검증 없음
```

- *상태 전이 검증 (DONE → CANCELED 금지 등) 우회* 가능
- *anemic domain anti-pattern* 의 *전형*

→ Fix : 
- `setStatus` 를 *패키지 가시성 (package-private)* 로 낮추거나 *제거*
- `Order` 에 `requestCancellation()`, `approveRefund()` 같은 *의미 있는 도메인 메서드 추가*

#### ⚠️ 기본 생성자 + public setter

- `Settlement.java:51` 기본 생성자 public + 모든 필드 public setter → `new Settlement() + setPaymentAmount(0)` 가능
- → Fix : 기본 생성자 *protected (JPA 매퍼용)*, setter 최소화

---

## 9. *종합 — *발견된 결함 의 *우선순위*

### 9.1 *Critical (배포 / 공개 전 *반드시* 수정)*

| # | 영역 | 위치 | 내용 |
|---|---|---|---|
| 1 | 보안 (BOLA) | `PaymentController.java:73,85,99` | authorize/capture/refund 소유자 검증 없음 — *타인 결제 환불 가능* |
| 2 | 보안 (BOLA) | `RefundHistoryController.java:38` | 환불 이력 + idempotencyKey 노출 |
| 3 | 도메인 | `Settlement.java:311`, `Refund.java:74`, `Order.setStatus` | 상태 머신 무력화 가능 |

### 9.2 *High (이번 분기 안에 처리)*

| # | 영역 | 위치 | 내용 |
|---|---|---|---|
| 4 | N+1 | `OrderPersistenceAdapter.java:54-98` | 100 건 → 101 라운드트립 |
| 5 | 관측 | `settlement-service/.../logback-spring.xml` | 파일 부재 — JSON 로그/MDC 누락 |
| 6 | 보안 | `TossPaymentService.java:176` | paymentKey 전체값 로그 |
| 7 | 성능 | `CreateDailySettlementsService` | Spring Batch 메모리 폭발 위험 |

### 9.3 *Medium (개선 가치)*

- Outbox 지수 backoff 도입
- Kafka consumer FixedBackOff → ExponentialBackOff (주석/코드 동기화)
- `@Modifying` 에 `clearAutomatically=true` 추가
- 회원가입 / 비번재설정 rate limit 추가

---

## 10. *체크리스트의 *진짜 가치 — *내가 *얻은 것*

### 10.1 *발견 — *내가 *모르던 *3 가지 구멍*

- *BOLA* — *내가 *권한 모델 을 *너무 *낙관적으로* *생각* 했다는 것을 *발견*
- *setStatus* — *anemic 의 *유혹* 이 *Lombok @Setter 처럼 *조용히 *들어왔다는 것을 *발견*
- *settlement-service logback 누락* — *order-service 만 *세팅* 하고 *settlement-service 는 *복사 안 한 채 *지나간* 것을 *발견*

### 10.2 *증명 — *문서가 *실제* 코드와 *일치* 함*

- CLAUDE.md 의 *Triple Idempotency / Pessimistic Lock + Idempotency-Key / Outbox / ArchUnit / Read-only Projection* — *모두 *코드에 *그대로 *반영* 됨
- *"설계 자산이 *실제로 *작동한다"* 는 것을 *체크리스트 가 *증명*

### 10.3 *학습 — *각 항목 의 *왜* 를 *글로 정리할 수 있게 됨*

- *비관락 이 *왜 *돈 흐름 에 *적절한가* — *retry 의 *위험성*
- *Outbox 가 *왜 *교과서 인가* — *Kafka + DB 의 *원자성* 분리
- *Triple Idempotency 가 *왜 *3 단인가* — *layer 직교*
- *BOLA 가 *왜 *흔한가* — *Spring Security 가 *방어해 주지 않음* (URL 매칭 만)

→ *이 체크리스트는 *내 시스템 의 *진짜 약점* 을 *발견* 한 *지도* 다. 그리고 *내 시스템 의 *진짜 강점* 을 *증명* 한 *문서* 다.

---

## 11. *결론*

> *체크리스트 없이 *짠 코드 는 *체크리스트 없이 *터진다*.
>
> *체크리스트 와 함께 *짠 코드 는 *체크리스트 와 함께 *고친다*.

*8 가지 영역* — *동시성 / 트랜잭션 / 보안 / N+1 / 재처리 / 로그 / 예외 / 도메인 규칙*. 이 8 가지는 *production 사고 의 *85%* 가 *나오는 영역* 이다. *나머지 15%* 는 *예측 불가능* 하지만 *85%* 는 *체크리스트로 *예방* 할 수 있다.

*내 settlement* 는 *85% 영역 의 *대부분 *합격* 이었다. *나머지 *깨진 부분* 은 *수정 PR* 로 *오히려 *내 *엔지니어링 의 *깊이* 를 *증명* 하는 *자산* 이 된다.

> *"운영해 본 적 없는 코드 는 *서비스 가 *아니다"* — *그리고 *체크리스트 없이 *검수해 본 적 없는 코드 는 *production 이 *아니다*.
