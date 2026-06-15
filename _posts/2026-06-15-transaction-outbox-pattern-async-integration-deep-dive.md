---
layout: post
title: "*분산 시스템의 *트랜잭션 + Outbox 패턴 + 비동기 연동* 완전 가이드 — *Two-Phase Commit 의 함정 / Transactional Outbox 구현 / CDC vs Polling / Triple Idempotency Stack* 의 *실전 postmortem 4 건***"
date: 2026-06-15 15:00:00 +0900
categories: [backend, distributed-system, msa, transaction]
tags: [transaction, outbox, transactional-outbox, cdc, debezium, kafka, idempotency, triple-idempotency, distributed-system, msa, eventual-consistency, saga, two-phase-commit]
---

이 글은 *MSA / 분산 시스템* 에서 *DB 변경 + 외부 시스템 알림* 을 *원자적 + 신뢰성 있게* 처리하는 *Outbox 패턴* 과 *비동기 연동* 의 *진짜 구현* 을 *실전 postmortem 4 건* 으로 정리한다. *transactional 보장 / Two-Phase Commit 함정 / CDC vs Polling 비교 / Triple Idempotency Stack* 의 *4 layer* 까지.

전 글들 ([트래픽 폭증 대기열](/2026/06/10/spring-boot-traffic-surge-waiting-room-queue-pattern/) + [동기/비동기 연동](/2026/06/13/java-python-kotlin-sync-async-integration-comparison/)) 의 *후속편*. *고부하 / 비동기 / 신뢰성* 의 *3 축* 을 *완성* 하는 *마지막 layer*.

읽고 가셔도 좋은 분:
1. *MSA 마이그레이션* 중인 백엔드 — *DB 변경 후 Kafka 발행* 의 *원자성* 어떻게 보장 하는지 모르는 사람
2. *결제 / 정산 / 주문* 시스템 개발자 — *"이벤트 중복 발행" / "이벤트 누락"* 사고 경험 있는 사람
3. *Debezium / Outbox / Saga* 의 *차이가 *애매한* 사람

---

## TL;DR

> *DB 트랜잭션 + Kafka 발행* 을 *동시에 *원자적 처리* 하려는 *순진한 시도* 는 *반드시 깨짐* — *Dual Write Problem*. *Transactional Outbox* 가 *현실적 해법* — *outbox_events 테이블 INSERT* 가 *DB tx 안* 에서 *함께 commit*, *별도 poller / CDC* 가 *Kafka 발행*. *수신측 *idempotency* 까지 합치면 *Triple Idempotency Stack* — *Outbox event_id UNIQUE → processed_events PK → 비즈니스 키 UNIQUE* 의 *3 단 방어*.

**한 그림으로**:

```
[order-service]                              [settlement-service]
                                             
@Transactional                               
  payment.capture()                          
  outbox_events INSERT (PaymentCaptured)     
       ↓ (DB commit — 원자성 보장)            
       │                                     
       ▼                                     
[Poller (2초 주기)]                          
  status: PENDING → PUBLISHED                
       ↓                                     
       Kafka Topic: lemuel.payment.captured  
       ↓                                     
       ▼                                     
                                  [Consumer]
                                  processed_events (group_id, event_id) PK 검사
                                       ↓ 신규 이벤트만
                                  @Transactional
                                    settlement INSERT (payment_id UNIQUE)
                                    processed_events INSERT
```

---

## 0. *왜 *Dual Write 가 *반드시 깨지는가***

### 0.1 *순진한 시도*

```java
@Service
public class OrderService {
    
    @Transactional
    public Order createOrder(OrderRequest req) {
        Order order = new Order(req);
        orderRepository.save(order);                    // 1. DB
        kafkaTemplate.send("orders", order.toEvent());  // 2. Kafka
        return order;
    }
}
```

> 한 번 보면 *맞는 것 같다*. 그런데 *3 가지 시나리오 에서 *반드시 깨진다*.

### 0.2 *깨지는 시나리오 3 가지*

**시나리오 1 — *Kafka 발행 후 *DB commit 실패***

```
1. Kafka send 성공  → 이벤트 *외부로 나감*
2. DB tx rollback (예: deadlock, constraint violation)
3. → DB 에는 *order 없는데*, Kafka 에는 *주문 생성 이벤트*
4. → 정산 / 재고 / 알림 시스템이 *유령 주문* 처리
```

**시나리오 2 — *DB commit 후 *Kafka 발행 실패***

```
1. DB commit 성공  → order 영구화
2. Kafka send 실패 (broker 다운 / 네트워크)
3. → DB 에는 *order 있는데*, Kafka 에는 *이벤트 없음*
4. → 후속 시스템이 *주문 모름 — 영원히 누락*
```

**시나리오 3 — *둘 다 성공 처럼 보이는데 *부분 실패***

```
1. DB commit 성공
2. Kafka send 의 *async ack 받기 전에 *JVM crash*
3. → DB 영구, 메시지는 *발행 됐는지 모름*
4. → 재시도 시 *중복 발행* 가능
```

### 0.3 *Two-Phase Commit (2PC) 의 *함정**

```
[Coordinator]
    ↓ phase 1 — prepare
[Resource 1 DB]   [Resource 2 Kafka]
    ↓ vote yes        ↓ vote yes
    ↓ phase 2 — commit
[Resource 1 commit]  [Resource 2 commit]
```

> 이론적으로 *가능*. 실제로:
> - Kafka 는 *XA 트랜잭션 미지원* (Kafka Transaction 은 *Kafka 안 만*)
> - 2PC 는 *coordinator 가 *single point of failure*
> - *Blocking* — coordinator 다운 시 *모두 *대기*
> - 마이크로서비스 시대에 *비실용적 *처치*

> *2PC 는 *2002 년 이후 *마이크로서비스 시대에 *거의 사라짐*. *Transactional Outbox* 가 *현대적 대체*.

---

## 1. *Transactional Outbox — *원리***

### 1.1 *핵심 아이디어*

> *DB 변경 + 이벤트 발행* 을 *2 개 트랜잭션 으로* 분리. *첫 트랜잭션 에서 *DB 변경 + outbox INSERT* 함께 commit (원자성). *두 번째 별도 프로세스* 가 *outbox → Kafka 발행*.

```sql
CREATE TABLE outbox_events (
    id              UUID PRIMARY KEY,
    event_id        VARCHAR(36) UNIQUE NOT NULL,    -- ★ UNIQUE 멱등성
    aggregate_type  VARCHAR(50)        NOT NULL,    -- 'Order', 'Payment' 등
    aggregate_id    VARCHAR(50)        NOT NULL,    -- '12345'
    event_type      VARCHAR(50)        NOT NULL,    -- 'PaymentCaptured'
    payload         JSONB              NOT NULL,
    status          VARCHAR(20)        NOT NULL DEFAULT 'PENDING',  -- PENDING / PUBLISHED / FAILED
    created_at      TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at    TIMESTAMP,
    
    INDEX idx_outbox_status_created (status, created_at)
);
```

### 1.2 *Producer 측 — *원자적 INSERT***

```java
@Service
public class PaymentService {
    
    @Transactional
    public Payment capturePayment(Long orderId) {
        Payment payment = paymentRepository.findByOrderId(orderId);
        payment.capture();
        paymentRepository.save(payment);
        
        // ★ 같은 트랜잭션 안에서 outbox INSERT
        OutboxEvent event = OutboxEvent.builder()
            .eventId(UUID.randomUUID().toString())
            .aggregateType("Payment")
            .aggregateId(payment.getId().toString())
            .eventType("PaymentCaptured")
            .payload(toJson(payment))
            .status(PENDING)
            .build();
        outboxRepository.save(event);
        
        return payment;
    }
}
```

> *DB 가 *둘 다 commit 또는 둘 다 rollback*. *원자성 100% 보장*.

### 1.3 *Poller — *별도 프로세스***

```java
@Component
@RequiredArgsConstructor
public class OutboxPoller {
    
    private final OutboxRepository outboxRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    
    /**
     * 2 초 주기로 PENDING 이벤트 조회 → Kafka 발행 → PUBLISHED 상태 갱신.
     * ShedLock 으로 *분산 환경 단일 실행* 보장 (HA).
     */
    @Scheduled(fixedDelay = 2000)
    @SchedulerLock(name = "outbox-poller", lockAtLeastFor = "PT2S")
    @Transactional
    public void publishPendingEvents() {
        List<OutboxEvent> pending = outboxRepository.findByStatusOrderByCreatedAt(
            PENDING, PageRequest.of(0, 100));
        
        for (OutboxEvent event : pending) {
            try {
                String topic = topicFor(event.getEventType());
                kafkaTemplate.send(topic, event.getAggregateId(), event.getPayload())
                    .get(5, TimeUnit.SECONDS);   // *동기 ack 대기*
                
                event.setStatus(PUBLISHED);
                event.setPublishedAt(Instant.now());
                outboxRepository.save(event);
                
                meterRegistry.counter("outbox.published",
                    "type", event.getEventType()).increment();
            } catch (Exception e) {
                log.error("Outbox 발행 실패: {}", event.getEventId(), e);
                meterRegistry.counter("outbox.failed",
                    "type", event.getEventType()).increment();
                // *PENDING 상태 그대로* — 다음 poll 에서 재시도
                // 5 회 실패 시 DLQ 또는 alert
            }
        }
    }
}
```

### 1.4 *멱등성 — *event_id UNIQUE***

```sql
-- DB 가 *발행자 중복 발행* 차단
INSERT INTO outbox_events (event_id, ...) VALUES (?, ...);
-- 동일 event_id 두 번째 INSERT 시 *UNIQUE constraint violation*
```

> *Producer 측 의 *재시도 안전성* 보장.

---

## 2. *Consumer 측 — *Inbox 패턴***

### 2.1 *processed_events 테이블*

```sql
CREATE TABLE processed_events (
    consumer_group  VARCHAR(100) NOT NULL,
    event_id        VARCHAR(36)  NOT NULL,
    processed_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (consumer_group, event_id)
);
```

### 2.2 *Consumer 코드*

```java
@KafkaListener(topics = "lemuel.payment.captured", groupId = "settlement-service")
public void handlePaymentCaptured(ConsumerRecord<String, String> record) {
    String eventId = extractEventId(record.value());
    
    // ★ 같은 트랜잭션 안에서 *중복 검사 + 비즈니스 처리 + processed_events INSERT*
    settlementService.processPaymentCaptured(eventId, record.value());
}

@Service
public class SettlementService {
    
    @Transactional
    public void processPaymentCaptured(String eventId, String payload) {
        // 1. 중복 검사
        if (processedEventsRepository.exists("settlement-service", eventId)) {
            log.info("이미 처리된 이벤트: {}", eventId);
            return;   // *멱등 — 그냥 무시*
        }
        
        // 2. 비즈니스 처리
        PaymentCaptured event = parsePayload(payload);
        Settlement settlement = Settlement.fromPayment(event);
        settlementRepository.save(settlement);
        
        // 3. processed_events INSERT — *같은 tx*
        processedEventsRepository.save(
            new ProcessedEvent("settlement-service", eventId, Instant.now()));
    }
}
```

> *Consumer 측 의 *중복 처리 차단*. *at-least-once 메시징* 을 *exactly-once 효과* 로 변환.

---

## 3. *Triple Idempotency Stack — *3 단 방어***

> *Producer + Consumer 의 *각자의 멱등성* 만으로 *부족할 수 있음*. *비즈니스 키 UNIQUE* 가 *마지막 layer*.

### 3.1 *3 layer 설명*

```
[L1] outbox_events.event_id UNIQUE
     ↓ 발행자 단계 중복 차단
     ↓ Producer 재시도 안전
     
[L2] processed_events (consumer_group, event_id) PK
     ↓ 수신자 단계 중복 차단
     ↓ Consumer 재실행 안전
     
[L3] settlements.payment_id UNIQUE  (비즈니스 키)
     ↓ 비즈니스 무결성 강제
     ↓ 운영 미스 / 마이그레이션 사고 마지막 안전망
```

### 3.2 *왜 *3 layer 필요한가*

> *각 layer 가 *서로 다른 *실패 모드* 를 막는다*.
> - L1 — *발행자의 *중복 발행 (재시도 / 네트워크 timeout)*
> - L2 — *수신자의 *중복 처리 (Consumer rebalance / replay)*
> - L3 — *비즈니스 키 *오염 (수동 보정 / 마이그레이션 실수 / 다른 service 의 잘못된 호출)*

*하나가 뚫려도 *다음 layer 가 막음*. *과잉 엔지니어링 아님* — *각자의 root cause 가 다름*.

---

## 4. *CDC (Change Data Capture) — *Polling 의 대안***

### 4.1 *CDC 의 *원리***

```
[Source DB — PostgreSQL]
    ↓ WAL (Write-Ahead Log)
[Debezium Connector]
    ↓ logical replication
[Kafka Topic — db_changes.public.orders]
    ↓
[Consumer]
```

> *DB 의 *변경 로그 (WAL / binlog) 를 *직접 읽음*. *애플리케이션 코드 변경 X*.

### 4.2 *Outbox + CDC 조합 (★ 권장)*

```
[Producer 서비스]
  @Transactional
    DB 변경
    outbox_events INSERT
       ↓ commit
[PostgreSQL WAL]
       ↓
[Debezium]   ← *poller 대신* WAL 직접 읽음
       ↓
[Kafka Topic]
```

**장점**:
- Poller 없어도 됨 (DB → Debezium 직접)
- *수 ms latency* (poll 2초 vs WAL 즉시)
- *DB 부하 적음* (poll 의 *주기 SELECT* 없음)

**단점**:
- Debezium 운영 부담 (Kafka Connect cluster)
- 운영 복잡도 증가

### 4.3 *Polling vs CDC 선택*

| 조건 | 권장 |
|------|------|
| 단순 시스템, 팀 작음 | **Polling (Outbox + Scheduled)** |
| 대용량, latency 민감 | **CDC (Debezium)** |
| 운영 인력 적음 | **Polling** |
| Kafka Connect 운영 가능 | **CDC** |
| MSA 10+ 서비스 | **CDC** (재사용) |

---

## 5. *실전 Postmortem 4 건*

### Case 1 — *Outbox 도입 전의 *Dual Write 사고*

**증상**: *주문 1만 건 / 일* 중 *3-5 건* 이 *Kafka 누락* — *후속 시스템 동기화 실패*.

**원인**:
```java
@Transactional
public void createOrder(...) {
    orderRepo.save(order);            // DB 성공
    kafkaTemplate.send(...);          // ★ 가끔 실패 (broker timeout)
    // → DB 에 주문 있는데, Kafka 에 없음
}
```

**해결**: Transactional Outbox 도입. *이후 *6 개월 *누락 0*.

### Case 2 — *Poller 중복 실행 — *분산 환경***

**증상**: 같은 이벤트가 *Kafka 에 *2 번 발행*.

**원인**: *Poller 가 *2 인스턴스 *동시 실행*. *PENDING 이벤트를 *둘 다 가져옴*.

**해결**: *ShedLock 으로 *분산 단일 실행* 보장*.

```java
@Scheduled(fixedDelay = 2000)
@SchedulerLock(name = "outbox-poller", lockAtLeastFor = "PT2S")
public void publishPendingEvents() { ... }
```

또는 *DB SELECT FOR UPDATE SKIP LOCKED* 패턴:

```sql
SELECT * FROM outbox_events 
WHERE status = 'PENDING'
ORDER BY created_at
LIMIT 100
FOR UPDATE SKIP LOCKED;  -- ★ 다른 트랜잭션이 잠근 row 는 *건너 뜀*
```

### Case 3 — *Consumer 중복 처리 — *Rebalance***

**증상**: *Kafka Consumer rebalance 후* 같은 이벤트 *2 번 처리*. *settlement *중복 row*.

**원인**: *processed_events 검사 누락 / commit 타이밍 문제*.

**해결**: 
1. *processed_events PK 검사* 추가
2. *L3 (settlements.payment_id UNIQUE)* 제약 추가
3. *Triple Idempotency Stack* 완성

### Case 4 — *Outbox 테이블 *수억 건 적체* — *DB 성능 저하***

**증상**: *6 개월 후* outbox_events 테이블 *수억 건*. *INSERT 성능 저하*.

**원인**: PUBLISHED 이벤트 *정리 X*. 무한 증가.

**해결**:
```sql
-- *7 일 지난 *PUBLISHED 이벤트 정리*
DELETE FROM outbox_events 
WHERE status = 'PUBLISHED' 
  AND published_at < NOW() - INTERVAL '7 days';
```

```java
@Scheduled(cron = "0 0 3 * * *")   // 매일 새벽 3시
public void cleanupOldEvents() {
    outboxRepository.deleteOldPublishedEvents(Instant.now().minus(7, ChronoUnit.DAYS));
}
```

---

## 6. *고급 — *Saga 패턴***

> *MSA 의 *여러 서비스에 걸친 트랜잭션* — *Outbox 만으로 부족*. *Saga 패턴* 이 *분산 트랜잭션 의 *현실적 해법*.

### 6.1 *Choreography Saga — *이벤트 기반***

```
[Order Service]
  OrderCreated 이벤트 발행 (Outbox)
       ↓
[Payment Service]
  PaymentRequested → Payment 처리
  PaymentCaptured / PaymentFailed 발행
       ↓
[Inventory Service]
  StockReserved / StockReservationFailed
       ↓
[Order Service]
  OrderConfirmed / OrderCancelled (보상)
```

### 6.2 *Orchestration Saga — *코디네이터***

```
[Order Saga Orchestrator]
  1. Payment Service 호출
     ↓ 실패 시 ↓
  2. Inventory Service 호출
     ↓ 실패 시 ↓
  3. Shipping Service 호출
     ↓ 실패 시 ↓
  4. 완료
  
  각 단계 실패 시 *역방향 보상 (compensation)*
```

| 항목 | Choreography | Orchestration |
|------|-------------|---------------|
| 결합도 | 낮음 (이벤트만) | 중 (orchestrator 의존) |
| 디버깅 | 어려움 (분산) | 쉬움 (중앙) |
| 추가 인프라 | 없음 | orchestrator 서비스 |
| 복잡한 흐름 | *어려움* | *쉬움* |

### 6.3 *Outbox + Saga 조합*

```kotlin
@Service
class OrderSagaOrchestrator(
    private val outbox: OutboxRepository
) {
    
    @Transactional
    fun startOrderSaga(order: Order) {
        // 1. Saga 상태 DB 저장
        val sagaState = SagaState(order.id, STARTED)
        sagaRepo.save(sagaState)
        
        // 2. 첫 단계 명령 — Outbox 로 발행
        outbox.save(OutboxEvent(
            eventType = "PaymentRequested",
            payload = toJson(PaymentCommand(order.id, order.amount))
        ))
    }
    
    @KafkaListener(topics = ["payment.captured"])
    @Transactional
    fun onPaymentCaptured(event: PaymentCaptured) {
        val saga = sagaRepo.findByOrderId(event.orderId)
        saga.advance(PAYMENT_COMPLETED)
        
        // 다음 단계 명령
        outbox.save(OutboxEvent(
            eventType = "StockReservationRequested",
            payload = toJson(StockReservationCommand(event.orderId))
        ))
    }
}
```

---

## 7. *모니터링 — *Outbox 의 *4 가지 메트릭***

```java
// Micrometer 메트릭
Counter outboxPublished = meterRegistry.counter("outbox.published");
Counter outboxFailed = meterRegistry.counter("outbox.failed");
Gauge outboxPending = meterRegistry.gauge("outbox.pending", 
    Tags.empty(), outboxRepository, r -> r.countByStatus(PENDING));
Timer outboxPublishDuration = meterRegistry.timer("outbox.publish.duration");
```

**Grafana 대시보드 query**:

```promql
# 발행 성공률
rate(outbox_published_total[5m]) / 
  (rate(outbox_published_total[5m]) + rate(outbox_failed_total[5m]))

# PENDING 적체 (*이게 증가하면 위험 신호*)
outbox_pending

# 발행 평균 latency
histogram_quantile(0.95, rate(outbox_publish_duration_bucket[5m]))
```

**알람**:
```yaml
- alert: OutboxPendingHigh
  expr: outbox_pending > 1000
  for: 5m
  annotations:
    summary: "Outbox PENDING 적체 — Poller 정지 또는 Kafka 다운 의심"
```

---

## 8. *함정 6 가지 — *Postmortem 압축***

### 8.1 *Outbox INSERT 누락*

```java
// ❌ — 비즈니스 로직 후 Outbox 안 함
@Transactional
public void capturePayment(...) {
    payment.capture();
    paymentRepo.save(payment);
    // outbox INSERT 빠짐 → 후속 시스템 알림 X
}
```

→ *코드 리뷰 + 단위 테스트 *필수*.

### 8.2 *Outbox 와 *비즈니스 로직 *다른 트랜잭션***

```java
// ❌ — 두 개 다른 트랜잭션
@Transactional
public void capturePayment(...) {
    payment.capture();
    paymentRepo.save(payment);
}

// 호출 분리
public void publishEvent(...) {
    outboxRepository.save(...);   // ★ 다른 tx — 원자성 깨짐
}
```

→ *반드시 같은 메서드 + 같은 tx*.

### 8.3 *Poller 가 *너무 자주 실행 — *DB 부하***

```java
@Scheduled(fixedDelay = 100)   // ❌ 100ms 마다 — DB 부하 폭주
```

→ *2-5 초 권장*. *latency 가 *민감* 하면 *CDC (Debezium)*.

### 8.4 *Outbox 발행 *순서 보장 누락*

```java
// ❌ — created_at 순서 미보장
outboxRepository.findByStatus(PENDING);  // 순서 없음

// ✅
outboxRepository.findByStatusOrderByCreatedAt(PENDING, ...);
```

> *이벤트 순서* 가 *중요한 비즈니스 (정산, 거래)* 에서 *치명적*.

### 8.5 *Kafka 발행 후 *outbox 상태 갱신 실패***

```java
// 시나리오:
// 1. Kafka send 성공
// 2. outbox.setStatus(PUBLISHED)
// 3. JVM crash
// → 다음 poll 에서 *재발행* (중복!)
```

→ *Consumer 측 *processed_events 검사* 가 *방어선*. *L2 멱등성의 *진짜 가치*.

### 8.6 *Schema 진화 — *오래된 이벤트 형식***

```
서비스 v1.0 — payload v1 발행
서비스 v2.0 — payload v2 로 변경
        ↓
Consumer v1.0 — v2 payload 파싱 실패 ★
```

→ *event_version 필드 명시*. *backward compatible 변경만 허용*. *breaking change 시 *새 topic*.

---

## 9. *마무리 — *Outbox 의 *진짜 의미***

### 9.1 *Outbox 는 *MSA 의 *기본 인프라***

> *Outbox 패턴 없이 *DB + Kafka 같이 쓰는 MSA = *반드시 사고 *언젠가 발생*. *Outbox 가 *MSA 의 *교통 신호등* — *없으면 *교차로 *충돌 *불가피*.

### 9.2 *Triple Idempotency 의 *각자의 책임***

> *L1 / L2 / L3 가 *서로 다른 *실패 모드* 를 담당*. *각자가 *독립적인 보안 layer* — *과잉 아닌 *정확한 분업*. *settlement 시스템 의 *실 운영 6 개월 0 사고* 의 *진짜 비결*.

### 9.3 *CDC 의 *2026 년 위치***

> *Debezium / Maxwell* 의 *CDC 가 *대규모 MSA 표준* 으로 자리잡음. *애플리케이션 코드 변경 없이 *DB 변경을 *Kafka 로 자동 발행*. *Outbox poller 의 *DB 부하 부담 회피*. *팀 규모 + 운영 역량* 에 따라 선택.

### 9.4 *이력서 변환 hook*

> *"분산 트랜잭션 / Outbox / 비동기 연동 경험"* 한 줄에:
> - Dual Write Problem 의 *3 가지 깨지는 시나리오*
> - Transactional Outbox 의 *원자성 보장* 메커니즘
> - Polling vs CDC (Debezium) 의 *trade-off*
> - Triple Idempotency Stack (L1/L2/L3) 의 *각자의 책임*
> - Saga (Choreography vs Orchestration) 의 *현실적 선택*
> - 실전 postmortem 4 건 의 *진단 + 해결*
> - 함정 6 가지 *Postmortem*
> 
> *4 단 깊이 면접 답변* 모두 준비.

---

## 부록 — *Spring Boot + Outbox *최소 셋업***

```kotlin
// 1. 의존성
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("net.javacrumbs.shedlock:shedlock-spring:6.0.0")
}

// 2. OutboxEvent 엔티티
@Entity
@Table(name = "outbox_events")
data class OutboxEvent(
    @Id @GeneratedValue val id: UUID = UUID.randomUUID(),
    @Column(unique = true) val eventId: String = UUID.randomUUID().toString(),
    val aggregateType: String,
    val aggregateId: String,
    val eventType: String,
    @Column(columnDefinition = "jsonb") val payload: String,
    @Enumerated(EnumType.STRING) var status: Status = PENDING,
    val createdAt: Instant = Instant.now(),
    var publishedAt: Instant? = null,
)

// 3. Poller
@Component
class OutboxPoller(
    private val outboxRepo: OutboxEventRepository,
    private val kafkaTemplate: KafkaTemplate<String, String>,
) {
    @Scheduled(fixedDelay = 2000)
    @SchedulerLock(name = "outbox-poller", lockAtLeastFor = "PT2S")
    @Transactional
    fun publish() {
        outboxRepo.findByStatusOrderByCreatedAt(PENDING, PageRequest.of(0, 100))
            .forEach { event ->
                runCatching {
                    kafkaTemplate.send(event.eventType, event.aggregateId, event.payload)
                        .get(5, TimeUnit.SECONDS)
                    event.status = PUBLISHED
                    event.publishedAt = Instant.now()
                }.onFailure {
                    log.error("Failed to publish ${event.eventId}", it)
                }
            }
    }
}
```

---

*다음 글:* *Saga 패턴의 *실전 구현 — *Choreography vs Orchestration* 의 *각자의 *디버깅 / 운영 / 보상 트랜잭션* 의 *실제 코드 비교*.
