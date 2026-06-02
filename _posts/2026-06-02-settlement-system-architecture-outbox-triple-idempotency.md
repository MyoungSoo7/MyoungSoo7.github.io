---
layout: post
title: "정산 시스템 *어떻게 동작하나* — 헥사고날 MSA + Outbox + Triple Idempotency + 분산 트레이싱"
date: 2026-06-02 17:15:00 +0900
categories: [architecture, reflection, software-engineering]
tags: [settlement, outbox, idempotency, kafka, hexagonal, msa, spring-boot, postgres, elasticsearch, distributed-tracing, dlq, reconciliation]
---

*결제 정산 시스템* 은 *돈을 다루는 흐름* 이라 "한 번 더 결제 / 한 번 덜 정산" 같은 *작은 실수가 큰 사고* 가 된다. *분산 시스템* 의 *고전적 어려움* 들 — *트랜잭션 경계*, *멱등성*, *재시도*, *DLQ*, *추적성* — 이 *전부 한 자리* 에 등장한다.

본 글은 *내가 만든 정산 시스템* 의 *핵심 동작 원리* 를 정리한다. *왜 그렇게 설계했는지* 의 *이유* 까지 함께. 특정 회사 구현이 아니라 *교과서적 설계 패턴이 실전 코드 안에서 어떻게 굴러가는지* 를 보여주는 *교육 목적*.

> 본 글의 구체적인 IP·도메인·내부 식별자는 *모두 제거됨*. *패턴과 흐름* 만 다룬다.

---

## TL;DR

| 핵심 | 내용 |
|---|---|
| **아키텍처** | 헥사고날 MSA (gateway / order / settlement) + 이벤트 드리븐 |
| **결제→정산 전파** | **Transactional Outbox** + Kafka — *DB 와 메시지의 원자성* |
| **멱등성** | **3중 방어** (UNIQUE outbox + Kafka idempotence + Consumer PK + 도메인 UNIQUE) |
| **실패 처리** | 10회 재시도 → **DLQ** → 운영자 콘솔 (`/admin/outbox/dlq`) |
| **추적성** | `traceparent` 헤더 *모든 경계* 전파 → Tempo/Grafana 단일 trace |
| **PG 대사** | 매일 PG CSV 받아 *5종 분류* (MATCHED / ROUNDING_DIFF / AMOUNT_MISMATCH / MISSING_*) |

---

## 1. 전체 구조 — *2개 Bounded Context + 1 Gateway*

```
┌─────────────┐
│   Client    │  (Web / Mobile)
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│  gateway-service         │ Spring Cloud Gateway
│  /api/* 라우팅            │
└──────┬───────────────────┘
       │
   ┌───┴────────────────┐
   ▼                    ▼
┌──────────────┐  ┌────────────────────┐
│ order-service│  │ settlement-service │
│              │  │                    │
│ - user       │  │ - settlement       │
│ - order      │  │ - reconciliation   │
│ - payment    │  │ - cashflow report  │
│ - product    │  │ - daily batch      │
│ - coupon     │  │ - ES indexing      │
└──────┬───────┘  └────────────────────┘
       │                ▲
       │ Outbox + Kafka │
       └────────────────┘
       │
       ▼
┌──────────────────────────┐
│   PostgreSQL 17          │ 공유 DB (스키마는 도메인 분리)
└──────────────────────────┘
              ▲
              │
┌──────────────────────────┐
│   Elasticsearch 8.17     │ 정산 검색 인덱스
└──────────────────────────┘
```

### 도메인 분리의 이유
- **Commerce** (주문/결제) 과 **Settlement** (정산) 은 *변경 주기* 가 다름
  - Commerce: *프로모션·UX 변경* 으로 *주마다* 배포
  - Settlement: *법규·회계 정책* 따라 *분기마다* 변경
- *서로 다른 SLA*: 결제는 *실시간*, 정산은 *분 단위 지연 OK*
- *팀이 분리* 될 가능성 (현재 1인이지만, 회사 환경 가정 시)

### 왜 Gateway 를 따로?
- *인증* 을 한 곳에 (JWT 검증)
- *Rate limiting* 한 곳에
- *서비스 추가* 시 *클라이언트 변경 없이* 라우팅만 추가

---

## 2. 핵심 흐름 — *결제 → 정산* (Transactional Outbox 패턴)

분산 시스템에서 가장 어려운 문제: *DB 트랜잭션 과 메시지 발행을 *동시에* 보장* 하는 것. 둘 다 동시에 성공·실패해야 *데이터 일관성* 이 유지된다.

### 잘못된 방식 ❌
```java
@Transactional
public void capturePayment(...) {
    paymentRepo.save(payment);              // DB 저장 OK
    kafkaTemplate.send("payment", event);   // ← Kafka 실패하면?
    // 트랜잭션 롤백되지만 *Kafka 는 이미 발행됨* (또는 그 반대)
}
```
*DB 와 Kafka 는 서로 다른 시스템* — *2PC (Two-Phase Commit)* 없이는 원자적 보장 불가. 그리고 *2PC 는 운영 부담이 큰* 안티패턴.

### Transactional Outbox 패턴 ✅
```
1. 비즈니스 트랜잭션 안에서:
   - 도메인 변경 (UPDATE payments)
   - outbox_events 테이블에 INSERT (이벤트 임시 저장)
   ↓ 한 번에 커밋 — DB 만 신경 쓰면 됨
   
2. 별도 워커 (OutboxPublisher) 가 *주기적으로 (2초)*:
   - SELECT pending outbox_events
   - Kafka 에 publish
   - 성공 시 outbox_events 상태 = PUBLISHED
```

핵심: **DB 트랜잭션 만으로 원자성 보장**. Kafka 는 *나중에 발행* 되지만 *반드시 발행됨* (at-least-once).

### 시퀀스 (가독성 정리)

```
[ User ]
   │ POST /payments/{id}/capture
   ▼
[ PaymentController ]
   │
   ▼
[ CapturePaymentUseCase ]
   │ ① PgRouter.capture(...) → 외부 PG 호출
   │ ② 트랜잭션 시작
   │   UPDATE payments SET status=CAPTURED
   │   INSERT outbox_events (traceparent 함께)
   │ ③ 커밋
   ▼
[ User ] ← 200 OK   (사용자 응답 끝)
═══════════════════════════════ 비동기 경계 ═══════════════════════════════
[ OutboxPublisher (2초 폴링) ]
   │ ④ SELECT pending outbox_events
   │ ⑤ Kafka topic 'payment.captured' 에 publish (traceparent header 복원)
   │ ⑥ UPDATE outbox_events SET status=PUBLISHED
   ▼
[ PaymentEventKafkaConsumer (settlement-service) ]
   │ ⑦ 멱등 체크 (processed_events PK)
   │ ⑧ createSettlementFromPayment(...)
   │ ⑨ INSERT settlements (commission_rate 스냅샷)
```

### 결과
- 사용자는 *2초 안에* 응답 받음 (Kafka 발행 대기 X)
- 정산 INSERT 는 *별도 워커* 가 처리
- *결제 성공했는데 정산 누락* → 절대 없음 (outbox 가 보장)
- *Kafka 일시 다운* → outbox 가 *재시도*

---

## 3. Triple Idempotency — *3중 멱등성 방어*

분산 시스템의 *현실*: 메시지는 *중복 전달될 수 있다*. 네트워크 재시도, Consumer 재기동, Kafka rebalance 등 *수많은 시나리오* 에서.

같은 결제에 *2번 정산 INSERT* 가 들어가면 *돈이 두 배* 가 된다. 절대 안 됨.

### 4단 방어 체계

| 단계 | 위치 | 메커니즘 | 실패 시 동작 |
|---|---|---|---|
| **L1** | Producer | `outbox_events.event_id UUID UNIQUE` | DB 제약 위반 → 비즈니스 트랜잭션 롤백 |
| **L2** | Kafka | Producer `enable.idempotence=true` | Kafka 내부 sequence number 로 *중복 record 방지* |
| **L3** | Consumer | `processed_events(consumer_group, event_id) PK` | 같은 이벤트 재배달 시 *즉시 ACK + 본문 처리 스킵* |
| **L4** | Domain | `settlements.payment_id UNIQUE` | 위 3단 다 뚫어도 *스키마가 최종 방어* |

### 왜 4중인가 — 한 단으론 부족?

각 단의 *실패 시나리오*:
- L1 만 있으면 → outbox 는 한 번이지만 *Publisher 가 2번 publish* 가능
- L2 만 있으면 → *다른 Producer 인스턴스* 가 같은 메시지 발행 가능
- L3 만 있으면 → *Consumer 가 처리 중 죽음* + 다시 살아남 → 중복 처리 가능
- *각 단이 *서로 다른 종류의 실패* 를 막음*

> **결론: 한 단이 뚫려도 다음 단이 막는다. 4단 다 뚫리려면 *4가지 동시 실패* — 사실상 불가능.**

이게 *defense in depth* 의 교과서.

---

## 4. DLQ — *실패한 메시지의 종착역*

Outbox 발행이 *10번 재시도해도 실패* 하면? 영원히 재시도 루프에 빠지면 *시스템 자원 고갈*.

### DLQ (Dead Letter Queue) 분기

```
[ OutboxPublisher 폴링 ]
   │
   ▼
[ Kafka publish 시도 (실패) ]
   │
   ├─ retryCount < 10 → 다음 폴링에 재시도
   │
   └─ retryCount = 10 →
        ┌─ Kafka DLQ topic 으로 publish (with lastError header)
        ├─ UPDATE outbox_events SET status=FAILED
        └─ 운영자 알람 (Slack/Telegram)
   
[ 운영자 ]
   │ GET /admin/outbox/dlq
   ▼
[ failed events list 조회 ]
   │
   ├─ POST /dlq/{id}/retry   → 다시 발행 시도
   └─ POST /dlq/{id}/skip    → 영구 스킵 (수동 보정 결정)
```

### 핵심 — *DLQ 가 *운영의 안전판**
- 자동 시스템은 *언제든 실패할 수 있다* — 외부 PG 다운, Kafka 다운, 네트워크 단절
- DLQ 없으면 *실패가 누적되어 어디론가 사라짐*
- DLQ 있으면 *운영자가 명시적으로 결정* (재시도 vs 스킵)

---

## 5. 분산 트레이싱 — *경계 너머로 trace 가 따라간다*

비동기 시스템의 *디버깅 지옥*: "사용자 결제 요청이 *어디서* 멈춘 거지?"

### 해답: `traceparent` 전파

W3C TraceContext 표준의 `traceparent` 헤더가 *모든 경계* 를 통과:

```
[ HTTP request ]      traceparent: 00-abc123...-span1-01
       │ ← span 시작
       ▼
[ Spring MVC ]         traceparent: 00-abc123...-span2-01  (자식 span)
       │
       ▼
[ DB INSERT outbox ]   traceparent 컬럼에 *값 저장* (DB 안에 trace 정보 보존)
       │
═══ 비동기 경계 ═══
       │
       ▼
[ OutboxPublisher ]    DB 에서 *traceparent 복원* → Kafka header 에 첨부
       │
       ▼
[ Kafka deliver ]      header: traceparent: 00-abc123...-span3-01
       │
       ▼
[ Consumer ]           spring-kafka 자동 instrumentation → trace 합류
       │
       ▼
[ Settlement INSERT ]  traceparent: 00-abc123...-span4-01
```

### 결과 — Grafana Tempo 에서
**한 결제 요청** 의 *시작부터 정산 INSERT* 까지가 *단일 trace* 로 보임.
- 어느 span 이 *얼마나 오래* 걸렸나
- 어느 경계에서 *에러 발생* 했나
- 평균 *얼마나 지연* 되나 (E2E latency)

비동기 시스템의 *디버깅 지옥* 이 *클릭 두 번* 으로 해결.

---

## 6. PG 정산파일 대사 (Reconciliation)

매일 PG 사가 *정산 CSV 파일* 을 보내준다. 우리가 *내부에 기록한 결제 내역* 과 *PG 가 알고 있는 내역* 이 *일치하는지* 확인해야 한다.

차이 나는 케이스 — 자주 발생:
- 우리 DB 에서 결제 성공 처리 직전 *네트워크 단절* → PG 는 성공, 우리는 실패 기록
- *Rounding 처리 차이* (소수점)
- *동일 거래 중복 발생*

### 5종 분류 자동화

```
[ POST /admin/pg-reconciliation/files (CSV 업로드) ]
   │
   ▼
[ ReconcilePgFileService ]
   │ ① CsvPgFileParser → List<PgTransactionRow>
   │ ② InternalPaymentsJdbcAdapter → List<InternalPaymentRow>
   │ ③ PgReconciliationMatcher.match(pgRows, internalRows)
   │      ↓
   │   ┌──────────────────────────────────────────────────┐
   │   │  5종 분류 (도메인 순수 로직)                       │
   │   ├──────────────────────────────────────────────────┤
   │   │ MATCHED          — 양쪽 동일                        │
   │   │ ROUNDING_DIFF    — 차이 < 1원, *자동 보정*          │
   │   │ AMOUNT_MISMATCH  — 차이 ≥ 1원, *검토 필요*           │
   │   │ MISSING_INTERNAL — PG 에만 있음 ⚠️ 위험             │
   │   │ MISSING_PG       — 내부에만 있음                    │
   │   │ DUPLICATE        — PG 에 중복 발생                   │
   │   └──────────────────────────────────────────────────┘
   ▼
[ pg_reconciliation_runs / discrepancies 테이블 INSERT ]
   │
   ▼
[ 운영자 대시보드 — 차이만 검토 ]
```

### 설계 핵심
- *Matcher* 는 *Spring 의존성 0* — *순수 도메인 로직*, *DB / 외부 mock 없이 단위 테스트* 가능
- *자동 보정* 은 *작은 차이 (1원 미만)* 만 — *큰 차이* 는 *운영자 검토*
- *MISSING_INTERNAL* 은 *위험 신호* — *PG 는 결제 알고 있는데 우리는 모름* = *돈 받았다가 사용자에게 안 줌* 위험

---

## 7. 설계 결정 — *왜 이렇게 했나*

### 7.1 *왜 Kafka 인가 Application Event 안 쓰고?*
Spring 의 `ApplicationEvent` 는 *같은 프로세스 내* 에서만 동작. *서비스 분리* 의미 무색.
Kafka 는 *서비스 경계 너머* 까지 전달 + *재처리·DLQ·trace* 까지 가능.

### 7.2 *왜 Hexagonal Architecture 인가?*
- 외부 PG (TOSS, KCP, NICE, INICIS) 가 *바뀌어도 도메인 영향 없음*
- 테스트 시 *Port 만 mock* — Spring context 불필요
- *settlement-service 가 order-service 코드 import 없이* JDBC 로 *읽기 전용* payments 조회 → *모듈 경계 보존*

### 7.3 *왜 PostgreSQL 17 공유 DB 인가?*
- 운영 단순성: *2개 DB 인스턴스 관리 vs 1개*
- *스키마 분리* (commerce_*, settlement_*) 로 *논리적 격리*
- *cross-domain JOIN 절대 금지* (ArchUnit 으로 강제)
- 장기 확장 시 *물리 분리 가능* (event sourcing 또는 CDC 로)

### 7.4 *왜 Elasticsearch 별도?*
- *정산 검색* 은 *복합 조건* (날짜 + 가맹점 + 금액 범위 + 상태) — PostgreSQL 인덱스로는 *cardinality 폭발*
- ES 는 *역색인 + 점수* — *수억 row* 도 *밀리초 검색*
- 일별 배치로 *동기화* — 실시간 필요성 낮음

---

## 8. 운영 패턴 — *Triple Idempotency 가 일상에서 동작*

실제 운영에서 *이런 시나리오 들* 이 *자주* 발생:

| 시나리오 | 어느 단이 막는가 |
|---|---|
| 사용자가 결제 버튼 *2번 클릭* | L1 (outbox UNIQUE) — 비즈니스 트랜잭션 롤백 |
| Kafka producer 가 *네트워크 timeout 후 재시도* | L2 (idempotence) — Kafka 가 중복 record 거절 |
| Consumer 가 *처리 중 OOM kill* → restart | L3 (processed_events PK) — 같은 이벤트 무시 |
| L1·L2·L3 모두 *코드 버그* | L4 (settlements.payment_id UNIQUE) — DB 가 INSERT 거절 |

→ *매주 모니터링 대시보드* 에서 *각 단에서 막힌 횟수* 를 추적. 한 단이 *비정상적으로* 자주 발동하면 *상위 단 문제 진단 신호*.

---

## 9. 결론 — *이 시스템에서 배운 5가지*

### 1. **분산 시스템에서 *DB 트랜잭션은 신* 이다**
Outbox 가 *DB 트랜잭션만으로* Kafka 발행을 *원자화*. *2PC 같은 복잡한 것* 필요 없음.

### 2. **멱등성은 *한 단으론 부족* 하다**
3~4중 방어가 *교과서적 권장*. 한 단만 있다면 *언젠가 사고* 난다.

### 3. **DLQ 없는 시스템은 *모래 위 성**
자동 시스템은 *반드시 실패* 한다. DLQ + 운영자 콘솔이 *유일한 안전판*.

### 4. **분산 트레이싱은 *후행 투자가 아니라 *선행 투자**
처음부터 *traceparent 전파* 안 해두면 *나중에 retrofit* 비용 *10배*.

### 5. **도메인 순수성은 *테스트 속도* 와 직결**
`PgReconciliationMatcher` 같은 *Spring 없는 순수 도메인* 은 *밀리초 단위 단위 테스트* + *수백 개 시나리오*. 이게 *진짜 자신감 있는 리팩토링* 의 기반.

---

## 마무리 — *교과서가 *살아있는* 시스템*

GoF·DDD·헥사고날·Outbox·CQRS — *책에서 본 패턴들* 이 *결제 정산 한 도메인 안에서 다 같이 굴러갈 수 있다*. 그리고 그렇게 *제대로 굴러가게* 만드는 게 *시니어 백엔드 엔지니어의 일*.

다음 글에선 *Outbox 패턴 의 *깊은 함정* — at-least-once vs exactly-once 의 *현실적 비용*, 그리고 *실제 코드에서 그 비용을 어떻게 줄였는지* 를 정리할 예정.

> *분산 시스템 디버깅 의 마지막 답: traceparent + outbox + DLQ + idempotency. 이 4가지 없이는 *어떤 시스템도* 운영할 수 없다.*
