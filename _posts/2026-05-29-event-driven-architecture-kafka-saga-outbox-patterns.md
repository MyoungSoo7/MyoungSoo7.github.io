---
layout: post
title: "이벤트 아키텍처 — *''호출하는 시스템''* 에서 *''반응하는 시스템''* 으로, 그리고 그 안의 *함정 7 개*"
date: 2026-05-29 00:50:00 +0900
categories: [architecture, event-driven, backend]
tags: [event-driven, kafka, rabbitmq, saga, outbox, cqrs, event-sourcing, idempotency, distributed-system]
---

> *''서비스 A 가 *서비스 B 를 호출* 한다''* 라는 한 문장은 분산 시스템의 *가장 흔한 결합* 이다. 호출하는 순간 *A 는 B 의 *주소·가용성·응답 시간* 을 모두 떠안는다*. *''서비스 A 가 *이벤트를 발행* 하고, *누구든 들으면 반응한다*''* 로 한 번 뒤집으면, *결합이 *시간·공간* 양쪽에서 *떨어진다***.

이 글은 *''이벤트 아키텍처는 왜 필요한가''* 를 시작으로, *4 가지 핵심 패턴* → *분산 트랜잭션의 진짜 문제* → *Outbox / Saga / Idempotency 의 삼각 방어* → *2026 권장 출발점* 으로 이어간다. 마지막은 *''이벤트 아키텍처가 만들어내는 7 가지 함정''* 으로 마무리한다 — *도구가 *해결하는* 문제만큼 *만드는* 문제도 있다*.

---

## 1. 왜 *이벤트* 로 뒤집는가 — *결합* 의 두 축

서비스 간 동기 호출 (synchronous call) 은 *두 가지 결합* 을 깐다.

| 결합 축 | 동기 호출의 가정 | 깨지는 순간 |
|---|---|---|
| **시간** (temporal) | B 가 *지금* 살아 있어야 한다 | B 가 *느려지면* A 도 느려짐 |
| **공간** (spatial) | A 가 B 의 *주소를 안다* | B 의 위치가 바뀌면 A 가 *수정* 필요 |

*''주문이 들어오면 결제하고, 결제하면 재고 잡고, 재고 잡으면 알람 보낸다''* 같은 *4 단 호출 체인* 은 *''마지막 단계가 죽으면 *앞단 3 개의 결과도 잃는다*''* 라는 *원자성 환상* 까지 만든다.

이벤트로 뒤집으면 — 

```
[주문 서비스] ─publish─▶ OrderPlaced(eventId=X, orderId=...) ─▶ [Kafka]
                                                                  │
                                          ┌───── 결제 서비스 ─────┘
                                          ├───── 재고 서비스 ─────┘
                                          └───── 알람 서비스 ─────┘
```

- 주문 서비스는 *''누가 듣는지 모른다''* — 새로운 구독자가 추가돼도 *주문 서비스 코드 0 줄 수정*
- 결제 서비스가 *5 분 뻗어도* 주문은 받아진다 — *복구되면 *밀린 이벤트* 부터 처리*
- *''누가 무엇을 하는지''* 가 *서비스 코드가 아니라 *토픽 구독 관계* 에 명시*

이 한 가지 *뒤집기* 가 *''100 개 서비스가 망 형태로 호출하는 카오스''* 를 *''100 개 서비스가 *공통 이벤트 버스* 에 매달리는 별 형태''* 로 바꾼다.

---

## 2. 4 가지 핵심 패턴 — Martin Fowler 가 정리한 *이벤트의 4 얼굴*

Martin Fowler 의 2017 년 글 **What do you mean by ''Event-Driven''?** 은 *이벤트* 라는 단어가 *적어도 4 가지 다른 것* 을 가리킨다고 정리했다.

### 2.1 *Event Notification* — *''뭔가 일어났다''* 만 알림

```json
// 가벼운 알림 — payload 최소
{
  "eventType": "OrderPlaced",
  "eventId": "evt-1",
  "orderId": "ord-42",
  "occurredAt": "2026-05-29T00:50:00Z"
}
```

- 들은 쪽이 *''그래서 뭐?''* 가 필요하면 *원본 서비스로 *다시 호출* 해서 조회*
- 가장 *느슨한* 결합 — 이벤트가 *진실* 을 들고 있지 않음
- *단점* — 구독자가 늘면 *원본 서비스로 *조회 폭주***

### 2.2 *Event-Carried State Transfer* — *''뭐가 어떻게 바뀌었는지''* 까지 실어 보냄

```json
{
  "eventType": "OrderPlaced",
  "eventId": "evt-1",
  "order": {
    "id": "ord-42",
    "amount": 12000,
    "items": [{ "sku": "A1", "qty": 2 }],
    "customer": { "id": "cust-7", "email": "..." }
  }
}
```

- 구독자가 *원본을 다시 조회할 필요 없음* — *자기 DB 에 *복제본* 저장*
- *원본 서비스 장애와 무관* 하게 *읽기 가능*
- *단점* — *데이터 중복*, *eventual consistency*, *schema evolution 책임*

### 2.3 *Event Sourcing* — *''이벤트가 *진실* 이다''*

```
[Account 의 *진실*]
  ┌─ AccountOpened(id=ACC-1)
  ├─ MoneyDeposited(amount=1000)
  ├─ MoneyDeposited(amount=500)
  ├─ MoneyWithdrawn(amount=300)
  └─ MoneyDeposited(amount=200)

→ 현재 잔액 = 1000 + 500 - 300 + 200 = 1400 *(이벤트를 *재생* 해서 계산)*
```

- *상태가 아니라 *변화의 역사* 가 *원본***
- *''과거 어느 시점의 상태''* 를 *재생* 으로 얻을 수 있음 — *완벽한 audit log*
- 금융 / 회계 / 게임 등 *역사 추적이 필수* 인 도메인에서 *압도적*
- *단점* — *모든 이벤트를 *영원히* 저장*, *snapshot 전략 필요*, *학습 곡선 가파름*

### 2.4 *CQRS* — *''읽기와 쓰기를 *다른 모델* 로''*

```
[쓰기 모델]  Command ─▶ Aggregate ─▶ Event ─▶ EventStore
                                       │
                                       ▼
[읽기 모델 1] OrderSummaryView   ─◀── Projection (Materialized View)
[읽기 모델 2] AnalyticsCube      ─◀── Projection
[읽기 모델 3] SearchIndex        ─◀── Projection
```

- *Command* 는 *Aggregate (DDD)* 로 쏘고 → *Event* 만 영구 저장
- *읽기* 는 *전혀 다른 모델* 로 — *목적별* 로 *여러 개* 둘 수 있음
- Event Sourcing 과 *자주 같이* 가지만 *독립적으로도* 가능
- *단점* — *eventual consistency*, *읽기/쓰기 분리의 인지 비용*

---

## 3. 메시징 인프라 — *Kafka / RabbitMQ / SQS* 의 *서로 다른 약속*

이벤트 아키텍처의 *물리적 기반* 은 *메시지 브로커* 다. 흔한 3 개의 *진짜 차이* 를 정리하면:

| | **Kafka** | **RabbitMQ** | **AWS SQS** |
|---|---|---|---|
| 모델 | *로그* (append-only) | *큐 + 라우팅* | *큐* |
| 메시지 보존 | *시간/크기 정책* 까지 *영구* | *consumer 가 ack* 하면 삭제 |  *최대 14 일* |
| 순서 보장 | *파티션 단위* | *큐 단위* | FIFO 큐만 |
| 처리량 | *극단적으로 높음* (LinkedIn 1조/일) | *중상* | *높음* (AWS 가 알아서) |
| Replay | *쉬움* (offset 되돌리기) | *안 됨* (ack 하면 사라짐) | *안 됨* |
| 강점 | *event sourcing*, *대량 스트리밍* | *복잡한 라우팅*, *RPC-like* | *완전 관리형* |

**언제 무엇을 쓰나** —
- *이벤트가 *진실* 이고 *재생* 이 필요* → Kafka
- *작업 분배 / RPC 대체 / 복잡한 routing* → RabbitMQ
- *AWS 환경 + 단순 비동기 처리* → SQS

> **2026 년 합리적 디폴트**: *대부분의 도메인 이벤트 → Kafka*. *팀 내부 작업 큐 → RabbitMQ / SQS*. *둘 다 *과한 선택* 이라면 그냥 *PostgreSQL 의 LISTEN/NOTIFY* + cron* 도 한 옵션.

---

## 4. *진짜* 어려운 문제 — *분산 트랜잭션*

*''DB 에 주문 저장하고, Kafka 에 이벤트 발행''* 이라는 *2 줄짜리 코드* 가 *분산 시스템 전체 문제* 의 *원천* 이다.

```java
// 안티 패턴 — *원자성 깨짐*
@Transactional
public void placeOrder(OrderCommand cmd) {
    orderRepo.save(order);                                    // DB commit
    kafkaTemplate.send("orders", new OrderPlaced(order));     // Kafka publish
}
```

이 코드의 *4 가지 실패 경로*:

1. *DB commit 성공 → Kafka 발행 실패* — *이벤트 누락*. 구독자가 *''주문이 *있었나''* 모름
2. *DB commit 실패 → Kafka 발행 성공* — *유령 이벤트*. *없는 주문이 *처리됨*
3. *Kafka 발행 성공 → DB 트랜잭션 롤백* — *유령 이벤트*
4. *Kafka 발행 성공 → 구독자 처리 중 죽음* — *재시도 → 중복 처리*

이 *4 경로를 모두 막는 표준 답안* 이 **Outbox + Saga + Idempotent Consumer** 의 *3 단 방어* 다.

### 4.1 *Transactional Outbox* — *''같은 DB 트랜잭션''* 에 이벤트도 넣자

```java
@Transactional
public void placeOrder(OrderCommand cmd) {
    orderRepo.save(order);
    outboxRepo.save(new OutboxEvent(
        eventId = UUID.randomUUID(),
        topic   = "orders",
        payload = json(new OrderPlaced(order)),
        status  = PENDING
    ));
}

// 별도 배치 (Polling Publisher)
@Scheduled(fixedDelay = 1000)
public void publishOutbox() {
    var pending = outboxRepo.findByStatus(PENDING, limit = 100);
    pending.forEach(evt -> {
        kafkaTemplate.send(evt.topic(), evt.payload());
        evt.markPublished();
    });
}
```

- *주문 저장 + 이벤트 저장* 이 *동일 DB 트랜잭션*
- 별도 *publisher 가 outbox 를 *폴링* 해서 Kafka 로 발행*
- *Kafka 실패 → 재시도*. *DB 실패 → 둘 다 롤백*
- **at-least-once 보장** — *이벤트가 *없어지지는* 않는다*

### 4.2 *Idempotent Consumer* — *중복 수신* 을 *결과 동일* 로

at-least-once 의 *대가* 는 *중복*. 같은 이벤트가 *2 번 이상* 도착할 수 있다. 그래서 *수신측* 이 *멱등* 해야 한다.

```java
@Transactional
public void on(OrderPlaced evt) {
    if (processedEventRepo.existsByEventId(evt.eventId())) {
        return;   // 이미 처리됨 — *건너뜀*
    }

    paymentService.charge(evt.orderId(), evt.amount());
    processedEventRepo.save(new ProcessedEvent(evt.eventId()));
}
```

핵심은 *''같은 트랜잭션에 *처리됨 표시* 까지 저장''*. 그래야 *처리 중 죽으면 *둘 다 롤백* → *재시도 가능***.

### 4.3 *Triple Idempotency* — *3 단 방어* 의 *현장 패턴*

실제 production 에서는 *한 층의 방어* 만으로는 안 깨진다. *3 단* 으로 둔다.

```
L1) 발행측 — outbox.event_id UNIQUE 제약    (같은 이벤트 *두 번 발행 안 됨*)
L2) 수신측 — processed_events.event_id PK   (같은 이벤트 *두 번 처리 안 됨*)
L3) DB 자체 — 비즈니스 자연키 UNIQUE 제약    (어떤 경로로 와도 *DB 가 막음*)
```

L1 이 뚫려도 L2 가 막고, L2 가 뚫려도 L3 가 막는다. *''완벽한 분산 트랜잭션은 없으니, 어느 층도 절대 깨지지 않는다고 가정 안 함''* 의 사고방식.

### 4.4 *Saga 패턴* — *''여러 서비스를 거치는 비즈니스 트랜잭션''*

```
[주문 saga]
  1) 주문 생성 (Order)
  2) 결제 (Payment)
  3) 재고 차감 (Inventory)
  4) 배송 예약 (Shipment)

→ 어느 단계에서 실패하면 *역순으로 *보상 트랜잭션***
```

Saga 는 *2 가지 스타일* 이 있다.

**Orchestration** — *''중앙 지휘자''* 가 단계 순서를 안다
- Spring StateMachine, AWS Step Functions, Camunda
- *장점* — 흐름이 *한 곳에* 보인다. 디버깅 쉬움
- *단점* — *지휘자가 *결합점***

**Choreography** — *''각자 *내 차례면* 행동''*
- 이벤트만 보고 *''결제 성공 들으면 *재고 깐다*''*
- *장점* — *완전 분산*, *추가 단계 = 새 구독자*
- *단점* — *전체 흐름이 코드에 *흩어짐*. 디버깅 어려움

> **선택 기준**: *단계 4 개 이하 + 흐름이 *바뀔 일 적음** → choreography. *단계 5 개 이상 + 흐름이 *바뀜* + *재시도/보상 정책이 복잡** → orchestration.

---

## 5. 산업 사례 — *Kafka 가 *왜* LinkedIn 에서 태어났는가*

### 5.1 **LinkedIn** (2010) — Kafka 의 *출생 배경*

LinkedIn 은 *''누가 누구를 팔로우했나''*, *''누가 누구의 글에 좋아요 눌렀나''* 같은 *대량 활동 데이터* 를 *여러 시스템* 에 보내야 했다.

- 검색 인덱스, 추천 엔진, 분석 데이터웨어하우스, 보안 로그, ...
- *N 개 생산자 × M 개 소비자* — *N×M 의 connector 카오스*
- 기존 메시지 큐 (ActiveMQ 등) 는 *처리량 한계* + *영구 보존 어려움*

해법: **Kafka** — *''log 자체를 *분산 시스템* 으로 만들자''*.

> *결과*: Kafka 가 2011 년 오픈 소스화. 2014 년 Confluent 창업. 2024 년 기준 *Fortune 100 의 80%+* 가 Kafka 사용.

### 5.2 **Uber** — *Real-time pricing* 의 *이벤트 spine*

Uber 의 *실시간 가격 산정* 은 *극한의 이벤트 아키텍처*.

- *수백만 운전자의 *위치 업데이트* * → Kafka topic
- *수억 명 사용자의 *요청 이벤트* * → Kafka topic
- *Surge pricing 알고리즘* 이 *Kafka Streams* 로 *실시간 집계*
- *가격 변경 이벤트* → 앱에 푸시

*''함수 호출이 *불가능* 한 규모''* — 동기 호출로 했으면 *지구상 어떤 서버* 도 못 견딘다.

### 5.3 **Netflix Keystone** — *내부 telemetry 의 이벤트 파이프라인*

Netflix 의 *서버 로그 + 메트릭 + 트레이스* 를 통합 처리하는 *Keystone* 은 *Kafka 기반*.

- *일일 *수조 개의 이벤트* * 처리
- *Flink* 로 실시간 처리, *S3 로 영구 저장*
- *분석 / 알람 / 비즈니스 메트릭* 모두 *같은 spine* 위에서

*''로그는 *Kafka 가 진실의 원천*''* — Netflix 의 공식 입장.

---

## 6. *함정 7 개* — 이벤트 아키텍처가 *만드는* 문제들

이벤트가 *해결* 하는 문제만큼 *만드는* 문제도 있다.

### 6.1 *순서 보장의 환상*

Kafka 는 *파티션 내부* 순서만 보장한다. *여러 파티션 = 순서 없음*. *''사용자 단위 순서가 필요하면 *사용자 ID 로 파티셔닝* * 해야 한다.

### 6.2 *Exactly-once 의 환상*

Kafka 가 *exactly-once* 를 광고하지만 *조건이 *매우* 까다롭다*. 안전한 가정은 **at-least-once + idempotent consumer** *뿐*.

### 6.3 *Schema Evolution* — *''필드 하나 추가가 *4 개 서비스를 깬다*''*

이벤트 schema 가 *없으면* 구독자가 *말없이* 깨진다. **Confluent Schema Registry** + *Avro / Protobuf* 가 *현장 표준*. *backward / forward compatibility 검증* 까지 *CI 단계에서*.

### 6.4 *디버깅의 *역방향 추적**

*''왜 이 주문이 *2 번 결제* 됐지?''* 의 답을 찾으려면 *Kafka offset, consumer lag, processed_events, outbox status* 를 *시계열로 합쳐서* 봐야 한다. *분산 트레이싱 (OpenTelemetry) 필수*.

### 6.5 *Eventual Consistency 의 비즈니스 노출*

*''주문 *직후* 마이페이지에 *안 보임*''* — *eventually* 동기화되니까 정상. 하지만 *고객은 *bug 로 신고**. *UI 가 *낙관적 업데이트* + *서버 컨펌* 패턴으로 대응* 필요.

### 6.6 *이벤트 폭증의 비용*

*''모든 상태 변경을 이벤트로''* 하면 *Kafka 비용 폭증*. *''*비즈니스 의미가 있는 변화* 만 이벤트''* 라는 *원칙* 이 필요. *내부 상태 동기화* 는 *outbox* 가 아니라 *주기적 sync* 가 답일 수 있다.

### 6.7 *''누가 무엇을 듣는지''* 의 *지식 손실*

*''이 이벤트를 *누가* 구독하나''* 가 *코드 어디에도 없다*. *Kafka 토픽 ACL* + *서비스 카탈로그* + *AsyncAPI 문서* 로 *명시적 관리* 필요. *방치하면 *모르고 이벤트 변경 → 운영 사고**.

---

## 7. *2026 권장 출발점*

### 7.1 *Spring Boot + Kafka* 의 *모범 답안 스택*

```
[발행측]
  - Outbox table (PostgreSQL)
  - @Transactional 로 비즈니스 + outbox 같이 commit
  - Polling Publisher (1초 주기 배치) → Kafka
  - Micrometer 메트릭 4종 (pending / publish_rate / failure / lag)

[수신측]
  - Spring Kafka Listener
  - processed_events table (PK = event_id)
  - @Transactional 로 비즈니스 + processed_events 같이 commit
  - DLQ (Dead Letter Queue) 로 *재시도 실패* 격리

[스키마]
  - Avro + Confluent Schema Registry
  - CI 에서 backward compatibility 검증

[트레이싱]
  - OpenTelemetry — Kafka header 로 trace_id 전파
  - Tempo / Jaeger 에서 *서비스 간 흐름 가시화*
```

### 7.2 *이벤트 아키텍처 도입 *3 단계 점검**

**Q1. 진짜 이벤트가 필요한가?**
- 동기 호출 *체인이 3 단계 이상* + *각 단계 *느림/장애* 가 *전체를 막음* → *이벤트로 풀어라*
- *2 서비스 간의 *단순 호출** 이면 *과한 선택*

**Q2. 운영 도구가 준비됐는가?**
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Centralized logging (event_id 로 *추적 가능*)
- [ ] Kafka 운영 인력 (또는 *MSK / Confluent Cloud*)
- [ ] Schema registry
- [ ] DLQ 모니터링

**Q3. 도메인이 *eventually consistent 를 *허용* 하는가?**
- *''주문 완료 직후 *즉시* 회계 장부에 반영''* 같은 *강한 일관성 요구* → *모놀리식 + DB 트랜잭션* 이 답
- *''대부분의 비즈니스 흐름은 *몇 초 지연* 허용''* → *이벤트 OK*

---

## 8. 정리 — *호출* 에서 *반응* 으로

> *''동기 호출은 *내가 *너* 를 부른다*''*. *''이벤트는 *내가 일어났음* 을 외친다, *듣는 자가 결정한다*''*.

이 한 줄의 *철학적 차이* 가 *시스템 전체의 *결합 구조* 를 바꾼다*. 발행자는 *''누가 듣는지''* 를 모르고, 구독자는 *''누가 외쳤는지''* 만 알면 된다.

하지만 *공짜는 아니다*. 동기 호출의 *원자성* 은 *분산 트랜잭션* 으로, 단순한 *''호출하면 답 온다''* 는 *''이벤트 보내면 *어디선가 *언젠가* 처리됨*''* 으로 바뀐다. 이 *교환* 을 *조직과 도메인이 *받아들일 준비* 가 되었을 때* 만 *이벤트 아키텍처가 *진짜* 가치를 낸다*.

> **요약**:
>
> 1. *호출 체인 ≥ 3 단계* + *운영 도구 갖춤* + *eventual consistency 허용* → *이벤트로 풀어라*
> 2. *Outbox + Idempotent Consumer + Triple Idempotency* — *분산 트랜잭션의 *3 단 방어*
> 3. *Schema Registry + OpenTelemetry + DLQ* — *운영 가시화의 *3 단 필수*
> 4. *''모든 걸 이벤트로''* 가 아니라 *''*비즈니스 의미 있는 변화* 만 이벤트로''*

이벤트 아키텍처는 *분산 시스템의 *극한의 도구* 가 아니라, *''잘 정의된 *경계* 와 *충분한 운영 성숙도* 가 만나는 지점''* 에서만 *진짜 답* 이 된다.

---

## 더 읽으면 좋은 자료

- Martin Fowler, **What do you mean by ''Event-Driven''?** (2017) — *4 패턴 정리의 원전*
- Chris Richardson, **Microservices Patterns** (2018) — *Outbox / Saga 의 교과서*
- Confluent, **Designing Event-Driven Systems** (Ben Stopford, 2018) — *무료 PDF*
- LinkedIn Engineering, **The Log: What every software engineer should know about real-time data's unifying abstraction** (Jay Kreps, 2013) — *Kafka 출생 배경*
- Uber Engineering, **Building Reliable Reprocessing and Dead Letter Queues with Apache Kafka**
- Sam Newman, **Building Microservices** (2 판, 2021) — *이벤트 경계 설계*
- Vlad Khononov, **Learning Domain-Driven Design** (2021) — *Domain Event* 와 *Integration Event* 의 차이
- Spring Modulith 공식 문서 — *application event* 로 시작해서 *Kafka 로 *추출* 가능* 한 *점진적 진화 경로*
