---
layout: post
title: "*정산 정합성* 의 *진짜 어려움* — 배치 / Kafka / Outbox / Triple Idempotency 가 *합쳐져야* 풀린다"
date: 2026-06-13 03:30:00 +0900
categories: [settlement, architecture, kafka, spring-boot, distributed-systems]
tags: [settlement, outbox-pattern, kafka, idempotency, transactional-outbox, batch, distributed-systems, eventual-consistency, dlq, flyway]
---

> *정산이 *한 건 *틀어졌습니다*.*
>
> 한 줄짜리 메시지가 *돈이 흐르는 시스템* 에서 의미하는 건 *간단하지 않다*. 다음 날 *고객 cs 가 *수십 건*, *세무사가 *전화* 하고, *은행 입출금이 *맞지 않는다*.
>
> *결제 1 건* 의 *정합성 깨짐* 이 *돈, 세무, 신뢰, 시간* 의 *4 가지 동시 사고* 를 만든다.

이 글은 *내가 1 년 가까이 운영해 온 *settlement (정산) 시스템* 의 *정합성 보장 패턴* — *배치 정산 / Kafka / Transactional Outbox / Triple Idempotency* 가 *왜 그렇게 결합 되어 있는지*, *어느 한 레이어 만 빠지면 *왜 무너지는지* 를 *실제 코드 + Flyway 마이그레이션 + 운영 메트릭* 과 함께 풀어본다.

---

## TL;DR — *한 줄 결론*

> *정산 정합성* 은 *단일 기술* 로 풀리지 않는다. *배치 (정기 집계)* + *Kafka (이벤트 전파)* + *Transactional Outbox (DB-Kafka 원자성)* + *Triple Idempotency (3 중 중복 차단)* 의 *4 layer 가 *합쳐져야* *at-least-once 메시징* 위에서 *정확히 한 번 처리* 의 *환상이 만들어진다*.

---

## 1. *왜 정산이 *어려운가**

### 1.1 *돈이 흐르는 *비대칭성**

일반 도메인은 *읽기 80% / 쓰기 20%*. *정산* 은 *반대* — *집계 + 분배 의 *write-heavy 한 사이클*. 그리고 *틀어지면 *돈* 이 흐른다*.

- *주문 1 건 → 매출 분배 (플랫폼 수수료 / 판매자 정산금 / 세금 / 환불 충당금)*
- *그 분배가 *틀어지면 *돈이 흐른 후 정정* 이 *비용 수십 배*
- *법적 / 회계적 *증빙 필요* — *모든 정산이 *audit log* 로 남아야 함*

### 1.2 *분산 시스템의 *본질적 한계**

분산 트랜잭션 (2PC) 는 :

- *성능 떨어짐* (모든 참여자가 prepare → commit 동기 대기)
- *coordinator 장애 시 *lock 영구 유지* 위험
- *Kafka / Redis 같은 *외부 시스템과 *함께 트랜잭션* 못 묶음*

그래서 *현대 시스템* 은 *2PC 를 피하고* *eventual consistency + idempotency* 로 *간다*. 정합성을 *시간 차원에서 *수렴* 시킨다*.

---

## 2. *Layer 1 — 배치 정산 의 *한계와 *왜 여전히 필요한가**

### 2.1 *옛 방식 — *일 1 회 *대량 배치**

```
매일 자정  →  전날 거래 SELECT  →  집계  →  정산 INSERT  →  은행 송금
```

장점 :
- *단순*. 한 트랜잭션 안에서 *원자성 보장*
- *실패 시 *재실행* 쉬움 (같은 일자 다시 돌리면 됨)

단점 :
- *latency* 가 *최대 24 시간*
- *피크 시간 (자정)* 의 *대량 트래픽 spike*
- *부분 실패 시 *복원 복잡* (어디까지 처리됐는지)

### 2.2 *왜 *여전히 배치가 필요한가**

실시간 정산 (Kafka 기반) 만 쓰면 :

- *집계가 *진행 중* 일 때 *snapshot* 이 *모호*
- *세무 신고* 같은 *기간 단위 집계* 는 *배치가 자연스러움*
- *최종 정합성 검증* (reconciliation) 은 *배치로 도는 게 *정확*

→ 결론 : *실시간 + 배치 *동시 사용*. *실시간은 *주문 단위 즉시 처리*, *배치는 *일/월 단위 *검증 + 보정**.

내 [settlement-service](https://github.com/MyoungSoo7/sparta-msa-project) 의 구조 :

```
주문 발생 (실시간)
  → Outbox INSERT + DB commit (원자적)
  → Kafka publish (별도 worker)
  → Consumer 가 정산 INSERT (idempotent)

일 1 회 배치 (새벽 04:00)
  → 어제 주문 전체 SELECT
  → 정산 테이블과 *대조 검증*
  → 차이 발견 시 *보정 + 알람*
```

*실시간 = 빠른 처리*, *배치 = 안전망*. *둘 다 필요*.

---

## 3. *Layer 2 — Kafka 의 *역할 — 이벤트 전파와 *replay**

### 3.1 *왜 Kafka 인가 (Redis Streams / RabbitMQ 가 아닌)*

| 항목 | Kafka | Redis Streams | RabbitMQ |
|---|---|---|---|
| Persistence | *디스크 저장 (replicated)* | *RAM 기반 (AOF)* | *디스크 저장* |
| Replay | *offset 기반 *과거 재처리* 강력* | *XREAD 가능 (제한적)* | *재처리 어려움* |
| Throughput | *수십만 RPS* | *수만 RPS* | *수천~수만 RPS* |
| Partition / 순서 보장 | *partition 별 *순서 보장* | *stream 별 순서* | *queue 별 순서* |
| 운영 부담 | *높음 (broker / ZooKeeper)* | *낮음* | *중간* |

정산의 핵심 요구 :

- *부분 시스템 장애 시 *replay 로 복구* 가능 → Kafka offset 기반
- *주문 ID 별 순서 보장* → Kafka partition key = orderId
- *Throughput 수십만 events/min* — Kafka 의 *기본 영역*

### 3.2 *Topic 설계 — *키와 partition*

```kotlin
// settlement-service / Kafka publish
kafkaTemplate.send(
    ProducerRecord(
        "order.settlement.requested",
        orderId.toString(),    // key = partition 결정
        JSON.stringify(event)
    )
)
```

- *Topic* : `order.settlement.requested` (도메인 동사 + past tense)
- *Key* : `orderId` — 같은 주문은 *같은 partition* → *순서 보장*
- *Partition 수* : 노드 수 × 2 ~ × 4 (consumer 병렬 throughput)

### 3.3 *Consumer group 의 *acknowledgement 모드*

```yaml
spring:
  kafka:
    consumer:
      enable-auto-commit: false   # 수동 commit
    listener:
      ack-mode: manual_immediate   # 처리 *완료 후 *수동 ack*
```

*at-least-once* — *처리 완료 후 commit*. *실패 시 *재처리*. *처리 도중 죽으면 *같은 메시지 다시 받음*. *그래서 *idempotency 가 필수*.

---

## 4. *Layer 3 — *Transactional Outbox* 패턴 — *DB-Kafka 원자성**

### 4.1 *문제 — *Dual Write*

가장 흔한 *초보 코드* :

```kotlin
@Transactional
fun completeOrder(orderId: OrderId) {
    orderRepository.markCompleted(orderId)      // DB 쓰기
    kafkaTemplate.send("order.completed", ...)  // Kafka publish
}
```

*문제* :

- *DB 쓰기 성공 + Kafka publish 실패* → *주문은 완료, 정산은 안 됨* (돈 안 흐름)
- *DB 쓰기 실패 + Kafka publish 성공 (재시도 직전)* → *정산은 됐는데 주문 미완료* (이중 정산)

DB tx 와 Kafka publish 는 *원자적으로 묶을 수 없다* (2PC 안 됨, 그리고 안 쓴다).

### 4.2 *Outbox 패턴*

해결 : *Kafka publish 대신 *outbox 테이블 INSERT* 만 같은 DB tx 안에서*.

```kotlin
@Transactional
fun completeOrder(orderId: OrderId) {
    orderRepository.markCompleted(orderId)

    // Kafka publish 대신 outbox 테이블에 INSERT
    outboxRepository.save(
        OutboxEvent(
            eventId = UUID.randomUUID(),
            topic = "order.completed",
            payload = JSON.stringify(orderCompletedEvent(orderId)),
            status = PENDING
        )
    )
}
```

*같은 DB tx 안에 두 INSERT — 원자적*. Kafka 는 *나중에 별도 worker* 가 *outbox 를 polling 해서 publish*.

```kotlin
@Scheduled(fixedDelay = 1000)  // 1초마다
fun publishPendingEvents() {
    val pending = outboxRepository.findByStatusOrderById(PENDING, limit = 100)
    pending.forEach { event ->
        try {
            kafkaTemplate.send(event.topic, event.eventId, event.payload).get()
            event.status = PUBLISHED
            outboxRepository.save(event)
        } catch (e: Exception) {
            event.attempts += 1
            if (event.attempts >= 10) event.status = DEAD_LETTER
            outboxRepository.save(event)
        }
    }
}
```

### 4.3 *settlement 의 outbox 스키마* (Flyway V12)

```sql
CREATE TABLE outbox (
    id              BIGSERIAL PRIMARY KEY,
    event_id        UUID NOT NULL UNIQUE,        -- L1 idempotency
    topic           VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL,
    status          VARCHAR(20) NOT NULL,         -- PENDING / PUBLISHED / DEAD_LETTER
    attempts        INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at    TIMESTAMPTZ,
    CONSTRAINT chk_outbox_status CHECK (status IN ('PENDING','PUBLISHED','DEAD_LETTER'))
);

CREATE INDEX idx_outbox_status_id ON outbox (status, id) WHERE status = 'PENDING';
```

핵심 :

- `event_id UNIQUE` — *같은 비즈니스 이벤트가 *중복 INSERT* 못 되게 차단* (Layer 1 of Triple Idempotency)
- `idx_outbox_status_id ... WHERE status='PENDING'` — *partial index*. *PENDING 인 것만 polling 비용 ↓*
- *상태 머신* : `PENDING → PUBLISHED` 또는 `PENDING → DEAD_LETTER`

---

## 5. *Layer 4 — Triple Idempotency — *3 중 중복 차단**

*at-least-once 메시징* 위에서 *정확히 한 번 처리* 의 환상을 만드는 *3 중 안전망*.

### 5.1 *L1 — Outbox 의 event_id UNIQUE*

```sql
event_id UUID NOT NULL UNIQUE
```

같은 *비즈니스 이벤트 (예: order 123 의 정산 요청)* 가 *2 번 outbox INSERT 시도* 시 *DB UNIQUE 제약 위반 → 두번째 실패 → 첫번째 만 살아남음*.

*producer 측 *재시도* 가 *원천 차단*.

### 5.2 *L2 — Consumer 측 processed_events 테이블*

```sql
CREATE TABLE processed_events (
    event_id       UUID PRIMARY KEY,             -- L2 idempotency
    consumer_name  VARCHAR(100) NOT NULL,
    processed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Consumer 가 메시지 받으면 :

```kotlin
@Transactional
fun handleOrderCompleted(event: OrderCompletedEvent) {
    try {
        // L2 — 같은 event_id 가 이미 처리됐으면 INSERT 실패
        processedEventsRepository.save(
            ProcessedEvent(event.eventId, "settlement-consumer")
        )
    } catch (e: DataIntegrityViolationException) {
        return  // 이미 처리됨. 조용히 skip.
    }
    
    // 비즈니스 로직
    settlementService.create(event)
}
```

*Kafka 의 *at-least-once 재배달* 시* L2 의 PK 충돌이 *중복 처리 차단*.

### 5.3 *L3 — 비즈니스 테이블의 *자연키 UNIQUE**

```sql
CREATE TABLE settlement (
    id              BIGSERIAL PRIMARY KEY,
    order_id        BIGINT NOT NULL,
    settlement_date DATE NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    -- L3 — 같은 주문은 정산 1 회만
    CONSTRAINT uk_settlement_order UNIQUE (order_id, settlement_date)
);
```

*L1, L2 가 다 뚫린 만에 하나의 경우* — *DB 의 *최종 진실의 출처* 인 *자연키 UNIQUE 제약* 이 *마지막 방어*.

### 5.4 *왜 3 중인가*

각 layer 의 *책임 분리* :

- L1 : *producer 재시도 사이클* 의 중복 차단 (Outbox polling 의 lost-update)
- L2 : *Kafka rebalance / consumer crash* 시 메시지 재배달 차단
- L3 : *L1/L2 가 다 새는 *예외적 buy 상황* 에서 *데이터 무결성 마지막 보호*

*한 layer 만 있으면 *불완전*. 셋 모두 있으면 *진짜 at-least-once + idempotent receiver 의 *교과서 패턴**.

---

## 6. *상태 머신 — Outbox 의 *PENDING → PUBLISHED**

### 6.1 *상태 전이*

```
[INSERT] → PENDING
              │
              ├─ publish 성공 → PUBLISHED
              │
              ├─ publish 실패 (재시도) → PENDING (attempts++)
              │
              └─ 10 회 실패 → DEAD_LETTER (수동 개입 알람)
```

### 6.2 *DLQ (Dead Letter Queue)*

DEAD_LETTER 상태가 *N 개 누적* 되면 *알람*. 운영자가 :

1. *원인 파악* (스키마 변경? 외부 API down?)
2. *수정 후 *수동 재시도* (status=PENDING 으로 update)
3. *불가능한 경우* *영구 폐기 + 회계 보정*

### 6.3 *Micrometer 메트릭 (settlement 의 4 종)*

```kotlin
@Component
class OutboxMetrics(meterRegistry: MeterRegistry) {
    val pending = Gauge.builder("outbox_pending_count", outboxRepo) { it.countByStatus(PENDING).toDouble() }
        .register(meterRegistry)
    val published = Counter.builder("outbox_published_total").register(meterRegistry)
    val deadLetter = Gauge.builder("outbox_dead_letter_count", outboxRepo) { it.countByStatus(DEAD_LETTER).toDouble() }
        .register(meterRegistry)
    val publishDuration = Timer.builder("outbox_publish_duration").register(meterRegistry)
}
```

*Prometheus + Grafana* :

- *pending* 증가 — *publish worker 가 *못 따라가는 중* 또는 Kafka 다운
- *dead_letter* 증가 — *재시도 한계 초과* 한 이벤트
- *publishDuration p99* 증가 — *Kafka latency 증가 또는 DB 부하*

자세한 응답시간 모니터링 관점은 [별편 글](/2026/06/10/backend-latency-and-monitoring-truth.html) 참고.

---

## 7. *흔한 함정 5 가지*

### 7.1 *@Transactional 안에서 *Kafka publish**

```kotlin
@Transactional
fun bad(orderId: OrderId) {
    orderRepository.save(...)
    kafkaTemplate.send(...).get()  // ← 5초 걸리면 *5초간 DB 락*
}
```

*Connection pool 점유 + DB lock 유지*. [HikariCP 글](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) 의 *@Transactional 안 외부 호출 함정*. 해결 : *outbox 패턴*.

### 7.2 *Outbox 가 *polling 만* 으로 부족*

Polling 간격이 1 초여도 *p99 latency* 가 *1 초 추가*. 해결 :

- *DB 트리거 → NOTIFY → 즉시 publish*
- *Debezium 같은 *CDC tool* — DB binlog 직접 읽음

### 7.3 *Consumer 가 *처리 도중 *부분 commit**

```kotlin
@KafkaListener
fun handle(event: Event) {
    settlementService.create(event)  // 성공
    notifyService.send(event)         // 실패 → 예외 → rollback?
}
```

*트랜잭션 경계* 가 *부정확하면* L2 processed_events 가 *INSERT 됐는데 비즈니스 *rollback* — *영원히 처리 안 됨* 패턴. *명확한 *트랜잭션 경계 *반드시* 명시*.

### 7.4 *Producer 와 Consumer 의 *스키마 *깨짐**

Producer 가 새 필드 추가 → Consumer 가 옛 버전 → *역직렬화 실패 → 무한 재시도*.

해결 : *schema registry (Confluent / Apicurio)* + *backward-compatible 변경만 허용*.

### 7.5 *DLQ 모니터링 안 함*

DLQ 가 *조용히 쌓이는 게 가장 위험*. *주간 / 일간 *DLQ count* 알람 + *Grafana 패널 *반드시* 노출*.

내 [Velero kopia 좀비 잡 사고](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug.html) 처럼 *stale 메시지 한 달간 누적* 사고는 *outbox 의 *DLQ 무관심* 으로 *얼마든지 재현 가능*.

---

## 8. *ArchUnit 으로 *경계 강제**

settlement 의 *core constraint* :

```kotlin
@ArchTest
val `application layer 는 JPA 를 *직접* 못 쓴다` = noClasses()
    .that().resideInAPackage("..application..")
    .should().dependOnClassesThat().resideInAPackage("jakarta.persistence..")

@ArchTest
val `domain 은 Spring 의존 없음` = noClasses()
    .that().resideInAPackage("..domain..")
    .should().dependOnClassesThat().resideInAPackage("org.springframework..")
```

[헥사고날 아키텍처](https://blog.lemuel.co.kr/) 의 *컴파일러 수준 강제*. *Outbox + Idempotency 같은 인프라 *세부사항이 *domain 로 새지 않도록**.

---

## 9. *전체 흐름 — *한 그림에*

```
사용자  →  주문 완료 API
              │
              ▼
       ┌──────────────────────────┐
       │  @Transactional          │
       │   - order UPDATE         │
       │   - outbox INSERT        │  ← L1 (event_id UNIQUE)
       │   - commit               │
       └──────────────────────────┘
              │
              ▼
       Outbox Worker (polling 1s)
              │  PENDING → PUBLISHED
              ▼
       ┌──────────────────────────┐
       │  Kafka                   │
       │   topic: order.completed │
       │   key: orderId           │
       └──────────────────────────┘
              │  at-least-once
              ▼
       ┌──────────────────────────┐
       │  Settlement Consumer     │
       │   @Transactional         │
       │    - processed_events    │ ← L2 (event_id PK)
       │       INSERT             │
       │    - settlement INSERT   │ ← L3 (order_id+date UK)
       │    - commit + ack        │
       └──────────────────────────┘
              │
              ▼
       매일 04:00 배치 — 재집계 + 정합성 검증
```

*각 layer 가 *자기 책임* 을 갖는다*. *한 layer 가 *조용히 *깨져도 다음 layer 가 *받아준다*. 그게 *defense-in-depth* 의 *정합성 버전*.

---

## 10. *교훈*

> *"정산 정합성은 *단일 *마법* 이 *없다*. *배치 / Kafka / Outbox / Triple Idempotency 의 *4 layer 가 *합쳐져야 만이 *at-least-once 위에서 *정확히 한 번* 의 환상이 만들어진다*. *어느 하나가 빠지면 *어딘가에서 새는* 시스템이 *조용히 *돈을 흘린다*."*

분산 시스템의 *정확히 한 번 처리* 는 *실재하지 않는다*. *우리가 만들 수 있는 건 *at-least-once 메시징 + idempotent receiver* 의 *결합으로 *재구성된 *정확히 한 번 의 *환상**. 그 환상이 *비즈니스 입장에서 *진짜 한 번* 으로 느껴지려면 *Outbox + Triple Idempotency + DLQ 모니터링* 의 *4 가지가 *함께* 살아 있어야 한다*.

*다음에 *정산 시스템* 을 설계할 때 — *Kafka 한 줄 도입* 만으로 *해결됐다* 고 *생각하지 말고 *4 layer 전체를 *그림으로* 그려보자**. 그게 *돈을 안전하게 흐르게 *하는 시야* 다.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [R 은 클러스터에 *없다*](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · [HikariCP 의 5 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) · [백엔드 응답시간 + 모니터링](/2026/06/10/backend-latency-and-monitoring-truth.html) · [Python vs Java 알고리즘](/2026/06/11/python-vs-java-algorithms-comparison.html) · *정산 정합성 (현재 글)*

*이 글은 [settlement-service](https://github.com/MyoungSoo7/settlement) 의 *실제 운영 코드* + Flyway V37 시리즈 마이그레이션 + Micrometer 4 종 메트릭 + ArchUnit 3 가지 핵심 룰 + outbox PENDING/PUBLISHED 상태 머신 운영 경험을 기반으로 작성.*
