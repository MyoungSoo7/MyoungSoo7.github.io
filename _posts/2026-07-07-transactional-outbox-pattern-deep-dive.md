---
layout: post
title: "Transactional Outbox 패턴 — *DB 커밋 과 메시지 발행* 을 하나 로 묶는 법"
date: 2026-07-07 10:15:00 +0900
categories: [backend, architecture, messaging]
tags: [outbox, transactional-outbox, kafka, eventual-consistency, idempotency, dual-write, msa, cdc]
---

이벤트 기반 시스템 에는 *조용한 함정* 이 하나 있다. **"DB 에 저장 하고, 메시지 를 발행 한다"** 는 이 두 줄 이, 사실 원자적 이지 않다는 것. 이 글 은 그 함정(dual write problem) 과, 그걸 푸는 **Transactional Outbox** 패턴 을 내 정산 시스템 구현 과 함께 정리 한다.

---

## 1. 문제 — *이중 쓰기(dual write)*

결제 가 완료 되면 두 가지 를 해야 한다:

```java
paymentRepository.save(payment);      // ① DB 커밋
kafkaTemplate.send("payment.done", e); // ② 메시지 발행
```

*둘 을 다 성공* 하면 좋다. 하지만 사이 에서 죽으면?

- ① 성공 → ② 실패: **결제 는 됐는데 정산 이벤트 가 안 감.** 돈 은 빠졌는데 정산 은 영영 안 됨.
- ② 성공 → ① 롤백: **이벤트 는 갔는데 결제 는 없음.** 유령 정산.

DB 트랜잭션 과 메시지 브로커 는 *서로 다른 시스템* 이라 하나 의 트랜잭션 으로 묶을 수 없다(분산 트랜잭션·2PC 는 무겁고 취약). 이게 이중 쓰기 문제 다.

---

## 2. 아이디어 — *같은 DB 트랜잭션 에 "발행할 메시지" 도 저장*

Outbox 의 통찰 은 단순 하다: **메시지 를 브로커 대신 *같은 DB* 의 outbox 테이블 에 쓴다.** 그럼 비즈니스 데이터 와 이벤트 가 *하나 의 트랜잭션* 으로 묶인다.

```java
@Transactional
void completePayment(...) {
    paymentRepository.save(payment);        // 비즈니스
    outboxRepository.save(new OutboxEvent(  // 이벤트 (같은 트랜잭션!)
        eventId, "payment.done", payload, PENDING));
}
```

이 트랜잭션 이 커밋 되면 *결제 와 이벤트 가 함께* 남고, 롤백 되면 *둘 다* 사라진다. **DB 커밋 = 이벤트 보장.** 이제 발행 은 *나중에* 별도 프로세스 가 맡는다.

---

## 3. 흐름 — *상태 머신 (PENDING → PUBLISHED)*

```
[결제 트랜잭션]
   payment 저장 + outbox(PENDING) 저장  ── 한 커밋

[Outbox 폴러 — 2초 주기]
   PENDING 조회 → Kafka 발행 → PUBLISHED 로 전환
                          ↘ 실패 시 재시도 (다음 폴링에서 다시 PENDING)
```

- 결제 는 outbox 에 `PENDING` 으로 이벤트 를 남기고 *즉시 응답*. 사용자 는 Kafka 를 기다리지 않는다.
- 별도 폴러(2 초 주기) 가 `PENDING` 을 긁어 Kafka 로 발행 하고 `PUBLISHED` 로 바꾼다.
- 발행 실패? 상태 가 `PENDING` 그대로 남으니 *다음 폴링 에서 재시도*. 브로커 가 잠깐 죽어도 유실 되지 않는다.

이게 Outbox 를 **최종 일관성(eventual consistency)** 의 안전한 다리 로 만든다.

---

## 4. 전달 보장 — *at-least-once, 그래서 수신 은 멱등 해야*

여기 가 핵심 이자 함정 이다. Outbox 는 **at-least-once** 를 보장 한다 — *최소 한 번* 은 간다(유실 X). 하지만 *정확히 한 번* 은 아니다:

- 폴러 가 Kafka 발행 에 **성공** 했는데, `PUBLISHED` 로 바꾸기 *전에* 죽으면? → 다음 폴러 가 같은 이벤트 를 *또* 발행 한다. **중복.**

즉 Outbox 는 유실 을 없애는 대신 *중복* 을 만든다. 그래서 **수신 측 이 반드시 멱등(idempotent)** 해야 완성 된다. 나 는 정산 에서 이걸 3 겹 으로 막는다:

```
L1  outbox event_id UNIQUE      — 같은 이벤트 두 번 발행 방지 (발행측)
L2  processed_events PK         — 같은 이벤트 두 번 처리 방지 (수신측)
L3  settlements.payment_id UNIQUE — 최종 저장 단계 중복 차단 (DB)
```

**Outbox(유실 방지) + 멱등 수신(중복 방지)** 이 세트 로 가야 "정확히 한 번 처럼" 동작 한다. 하나 만 하면 반쪽. (→ [정산 시스템 을 KPI 로]({% post_url 2026-07-03-settlement-system-kpi %}))

---

## 5. 실전 구현 디테일 (settlement)

교과서 와 운영 사이 의 간극 을 메우는 것 들:

- **event_id UNIQUE 제약** — outbox 에 비즈니스 키 기반 event_id 를 UNIQUE 로. 같은 결제 로 이벤트 가 두 번 생기는 것 자체 를 DB 가 막는다(L1).
- **배치 폴링** — 매 폴링 마다 `PENDING` 을 *N 건 씩* 묶어 처리. 한 건씩 하면 처리량 이 안 나온다.
- **메트릭(Micrometer)** — outbox 발행 성공/실패/지연/대기건수 를 메트릭 으로. "PENDING 이 쌓이고 있다" 를 알아야 폴러 장애 를 잡는다.
- **DLQ(Dead Letter Queue)** — N 회 재시도 후 도 실패 하는 이벤트 는 버리지 않고 격리 → 사람 이 조사·재처리.
- **trace_id 전파** — 결제 트랜잭션 의 trace_id 를 outbox → Kafka 경계 너머 로 전파. 분산 추적 이 끊기지 않게.
- **outbox 정리** — `PUBLISHED` 된 오래된 행 은 주기적 으로 아카이브/삭제. 안 그러면 테이블 이 무한 증식.

---

## 6. 대안 과 비교 — *폴링 Outbox vs CDC*

Outbox 를 발행 하는 방식 은 두 갈래 다:

| 방식 | 원리 | 장 | 단 |
|---|---|---|---|
| **폴링 Outbox** | 폴러 가 테이블 을 주기 조회 | 단순·인프라 최소 | 폴링 지연·DB 부하 |
| **CDC (Debezium)** | DB WAL/binlog 를 tailing | 지연 낮음·DB 부하 적음 | Debezium/Connect 운영 부담 |

나 는 폴링 을 택했다 — *2 초 지연 은 정산 에 충분* 하고, Debezium 운영 세금 을 지지 않아도 되니까. [설계 세 축]({% post_url 2026-07-07-backend-design-three-axes %}) 의 *"의심 되면 단순 쪽"* 그대로. 트래픽 이 커지면 CDC 로 진화 시킬 여지 는 열어둔다.

---

## 7. 흔한 함정

- **폴링만 하고 멱등 은 안 함** → at-least-once 의 중복 이 그대로 정합성 사고 로. *수신 멱등 은 옵션 이 아니다.*
- **outbox 를 안 지움** → 테이블 폭증, 폴링 쿼리 느려짐. `PUBLISHED` 는 인덱스 + 정리 배치 필수.
- **순서 가정** → 폴링/파티션 에 따라 이벤트 순서 가 뒤집힐 수 있다. 순서 가 중요 하면 파티션 키·시퀀스 를 설계.
- **동기 호출 로 "빠르게"** → Outbox 를 쓸 자리 에 동기 REST 를 박으면 [분산 모놀리스]({% post_url 2026-07-07-six-designs-that-hurt-in-operation %}) 가 된다.

---

## 결론

Transactional Outbox 는 *화려한 패턴 이 아니라, 조용한 안전장치* 다:

- **DB 커밋 = 이벤트 보장** — 같은 트랜잭션 에 이벤트 를 박제 해 이중 쓰기 를 없앤다.
- **at-least-once** — 유실 은 없앤다. 대신 *중복* 을 만들고, 그건 *수신 멱등* 이 받는다.
- **Outbox + 멱등 수신 = 세트** — 둘 이 함께 가야 "정확히 한 번 처럼" 이 완성 된다.

돈 을 다루는 이벤트 라면, "발행 하고 잘 됐겠지" 가 아니라 **"DB 가 커밋 됐으면 이벤트 는 반드시 간다"** 를 구조 로 보장 해야 한다. Outbox 는 그 보장 을, *분산 트랜잭션 없이* 가장 단순하게 얻는 방법이다.
