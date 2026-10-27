---
layout: post
title: "정산 플랫폼 order-service 해부 — 주문·결제 프로세스와 구조"
date: 2026-10-28 02:10:00 +0900
categories: [Architecture]
tags: [msa, hexagonal, payment, idempotency, transactional-outbox, kafka, spring, settlement]
---

Lemuel 정산 플랫폼의 Java 서비스는 다섯 개다 — **order · settlement · finance · operation · external-data**
(+ 라우팅 전용 gateway). 이 중 돈이 처음 생기는 곳이 `order-service` 다. 주문이 만들어지고, 결제가
확정되고, 그 사실이 이벤트로 정산 서비스에 넘어간다. 이 글은 그 경로를 **코드 기준으로** 따라간다.
(기준: 2026-10-27 커밋 `0194c94`. 리포는 비공개라 짧은 발췌만 싣는다.)

## 1. 다섯 서비스 중 order 의 자리

| 서비스 | 하는 일 |
|---|---|
| **order** | 커머스 코어 — user·order·payment·cart·shipping·product·coupon·review·sellertier, 조직(organization) |
| settlement | 정산 상태머신·복식부기 원장·payout, 예치금, AI 챗봇 |
| finance | 선정산·투자·계정계·법인카드·보험·기업평판 |
| operation | 운영관제·알림 팬아웃·게시판·교육 |
| external-data | DART·ECOS·KRX·공공데이터·기업 마스터 |

order 와 settlement 는 **DB 도 따로**다(DB-per-service). 그래서 order 는 settlement 코드를 컴파일
의존하지 않고, 둘 사이에는 Kafka 이벤트만 흐른다.

## 2. 패키지 구조 — 헥사고날

`order`, `payment` 둘 다 같은 모양이다.

```
order/
├── domain/                 Order, OrderItem, OrderStatus(상태머신), RefundPolicy
├── application/
│   ├── port/in/            CreateMultiItemOrderUseCase, CancelOrderItemsUseCase …
│   ├── port/out/           SaveOrderPort, PublishOrderEventPort, DistributedLockPort …
│   └── service/            CreateMultiItemOrderService, IdempotentMultiItemOrderService …
└── adapter/
    ├── in/web, in/scheduler
    └── out/persistence, out/lock(Redis/InMemory), out/event(Outbox), out/notification(Mail/Slack)

payment/
├── domain/                 PaymentDomain, PaymentStatus, PaymentTender, TenderType, Refund, CashReceipt
├── application/            TossPaymentService, Authorize/Capture/RefundPaymentUseCase, service/…
└── adapter/out/pg/         PgRouter + Toss/Nice/KCP/Inicis 어댑터, out/event(Outbox)
```

도메인은 프레임워크를 모르고, 바깥 세계(PG·Redis·Kafka·메일)는 전부 `port/out` 인터페이스 뒤에 있다.
의존 방향은 ArchUnit 테스트가 빌드 단계에서 강제한다. 예컨대 `PgRouter` 주석은 이렇게 말한다:
"라우팅은 도메인 로직이 아닌 인프라 결정이므로 아웃바운드 어댑터에 둔다. 도메인은 PG 가 무엇인지 모른다."

## 3. 주문 상태머신

전이 규칙은 `OrderStatus` enum 한 곳에 표로 박혀 있다.

```java
ALLOWED.put(CREATED,  EnumSet.of(PAID, CANCELED, CANCELLATION_REQUESTED));
ALLOWED.put(PAID,     EnumSet.of(SHIPPING_PENDING, REFUND_REQUESTED, REFUNDED, CANCELLATION_REQUESTED));
ALLOWED.put(SHIPPING_PENDING, EnumSet.of(IN_TRANSIT, REFUND_REQUESTED, REFUNDED));
ALLOWED.put(IN_TRANSIT, EnumSet.of(DELIVERED, REFUND_REQUESTED, REFUNDED));
ALLOWED.put(DELIVERED,  EnumSet.of(REFUND_REQUESTED, REFUNDED));
ALLOWED.put(REFUND_REQUESTED, EnumSet.of(REFUNDED));
// CANCELED, REFUNDED — 종단
```

```
CREATED ──결제──▶ PAID ─▶ SHIPPING_PENDING ─▶ IN_TRANSIT ─▶ DELIVERED
   │               │            │                 │             │
   ▼               └────────────┴──── REFUND_REQUESTED ─────────┴──▶ REFUNDED (종단)
CANCELED (종단)
```

눈여겨볼 점 두 가지.

- **환불 종단은 `REFUNDED` 하나.** 예전 `REFUND_COMPLETED` 는 `@Deprecated` 로 남겨 두되 신규 전이는 없다.
  과거 DB 행을 읽을 수 있게 enum 값만 보존한 것이다.
- **입력 파싱을 두 개로 나눴다.** DB 복원용 `fromString` 은 모르는 값을 `CREATED` 로 눕히지만, 사용자
  입력용 `parse` 는 거부한다. 주석이 이유를 댄다 — 관대한 파서를 조회 필터에 쓰면 오타 하나가
  "CREATED 주문 목록"으로 바뀌고, 승인 큐라면 운영자가 "대기 0건"으로 읽고 넘어간다.

## 4. 주문 생성 — 한 트랜잭션, 두 겹의 중복 방어

### 4-1. 생성 본체 (`CreateMultiItemOrderService`)

1. 사용자 존재 확인
2. 라인별 상품/SKU 조회 → 단가·이름 **스냅샷**
3. 재고 차감 (SKU 는 낙관적 락 재시도, 단일 상품은 조건부 `UPDATE`)
4. 쿠폰 검증 → 할인 반영 → `Order.createMultiItem` 이 합계 계산
5. 저장 → 쿠폰 사용 기록 → `OrderCreated` Outbox 기록 → 확인 메일

**전부 하나의 `@Transactional`** 이다. 쿠폰 한도 초과로 사용 기록이 실패하면 주문 INSERT·재고 차감·
Outbox 까지 함께 롤백된다. "쿠폰은 못 썼는데 주문만 생성됨" 같은 반쪽 상태가 생기지 않는다.

### 4-2. 멱등 래퍼 (`IdempotentMultiItemOrderService`)

더블클릭·클라이언트 재시도로 같은 주문이 두 번 오는 걸 막는다. 클라이언트가 `Idempotency-Key`
헤더를 보내면([IETF 초안](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)과 같은 발상):

```java
return lockPort.executeWithLock("order:create:" + key, WAIT_3s, LEASE_10s, () ->
    transactionTemplate.execute(tx -> {
        var existing = idempotencyPort.findOrderId(key);
        if (existing.isPresent()) return loadOrderPort.findById(existing.get())...; // replay
        Order created = delegate.create(userId, lines, couponCode);
        idempotencyPort.save(key, created.getId());   // 중복 키면 PK 위반 → 통째 롤백
        return created;
    }));
```

- **1겹 — 분산 락(`RedisDistributedLockAdapter`, 로컬은 인메모리 대체):** 같은 키의 동시 요청을 줄 세워, 두 번째 요청이 재고를 또 깎는 낭비를 막는다.
  락은 트랜잭션 **바깥**에서 잡아 보유 시간을 짧게 한다.
- **2겹 — DB UNIQUE:** 락이 만료돼 둘이 빠져나가도 멱등 레코드의 PK 위반이 늦은 쪽 트랜잭션을 통째로
  롤백한다. 잡힌 `DataIntegrityViolationException` 은 승자의 주문을 다시 읽어 그대로 돌려준다.

락은 최적화이고 정합성은 DB 제약이 지킨다 — 이 역할 분담이 핵심이다.

## 5. 결제 — Toss 승인 흐름 (`TossPaymentService`)

```
멱등 replay 확인 → 주문 대조(소유권·금액) → Toss confirm API → READY 생성 → AUTHORIZED → CAPTURED
```

### PG 를 부르기 전에 끝내야 하는 검증 두 가지

코드 주석이 가장 길게 설명하는 부분이다.

1. **소유권** — 요청 본문의 주문 ID 를 믿으면 남의 주문번호만 알아도 그 주문을 결제 완료로 만들 수 있다.
   주문 소유자는 DB 에서 읽어 JWT 주체와 대조한다.
2. **금액** — Toss [결제위젯 연동 가이드](https://docs.tosspayments.com/guides/v2/payment-widget/integration)는
   성공 리다이렉트의 `amount` 쿼리 파라미터가 결제 요청 때 설정한 금액과 같은지 반드시 확인하라고 한다 —
   "클라이언트에서 결제 금액을 조작하는 행위를 방지"하기 위해서다. 그런데 결제창 금액 자체도 브라우저가
   정하므로, 서버가 **주문 금액**과 이어주지 않으면 저가 결제창으로 고가 주문을
   결제 처리할 수 있다. 주문 금액을 아는 주체는 우리뿐이다.

둘 다 돈이 움직이기 **전에** 판정해야 의미가 있어 confirm 호출 앞에 둔다.

### 멱등 키 — 헤더가 없어도 보호된다

승인은 POST 라 재시도가 같은 승인을 두 번 부를 수 있다. 예전엔 하류 UNIQUE 제약만 있어 이중 결제행은
막혔지만 사용자에겐 500 이 나갔다. 지금은 `payment_idempotency` 테이블이 최초 결과를 replay 한다.
키는 `Idempotency-Key` 헤더, 없으면 결제창이 발급한 `paymentKey` 를 쓴다 — 구 클라이언트도 보호된다.

### 복원력 — 별도 빈이어야 AOP 가 걸린다

Toss 호출은 `TossConfirmApiClient` 라는 **별도 빈**이 [Resilience4j](https://resilience4j.readme.io/docs/getting-started-3)
CircuitBreaker + Retry 로 감싼다. 4xx(비즈니스 오류)는 재시도·서킷 판정에서 뺀다.
별도 빈인 이유: Spring AOP 는 프록시 기반이라 **같은 클래스 안의 자기 호출에는 어드바이스가 걸리지 않는다**
([Spring 공식 문서 — Understanding AOP Proxies](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html#aop-understanding-aop-proxies)).
예전 구조에선 재시도·서킷이 조용히 무력화돼 있었고, 지금은 이 회귀를 하네스 테스트가 막는다.

### 결제 상태머신

```
READY ─▶ AUTHORIZED ─▶ CAPTURED ─▶ REFUNDED
  └─▶ EXPIRED      └─▶ CANCELED (승인취소)
```

`EXPIRED` 는 **READY 에서만** 도달한다. 가상계좌·무통장의 입금 기한이 지난 경우다. 승인 이후엔 자금이
잡혀 있으므로 만료가 아니라 취소·환불 경로를 탄다. 미입금 만료는 매일 03:20(KST) 스케줄러가 집되,
**건별 독립 트랜잭션 + 비관적 락으로 재조회**한다 — 스캔과 처리 사이에 입금이 도착했을 수 있어서다.

## 6. 텐더 분할결제 — 수단은 두 축으로 갈린다

`TenderType` 은 결제 수단을 두 개의 독립 축으로 분류한다.

| 수단 | 외부 PG 호출 | 입금 대기 |
|---|---|---|
| CARD, KAKAO_PAY, NAVER_PAY, PAYCO, SAMSUNG_PAY | O | X |
| BANK_TRANSFER, VIRTUAL_ACCOUNT | O | **O** |
| POINT, GIFT_CARD | X (내부 잔액) | X |

"포인트 3천 + 카드 나머지" 같은 결제는 tender 별로 독립 PG 거래가 된다. 재밌는 규칙이 하나 있다.
**입금 대기 수단이 하나라도 섞이면 카드 텐더도 승인까지만 하고 캡처하지 않는다.** 가상계좌 입금이
끝내 안 오면 주문이 취소될 텐데, 카드만 먼저 매입해 뒀다면 그때 환불로 되돌려야 하기 때문이다.
같은 이유로 포인트도 "차감"이 아니라 "선점"하고, 입금 확인 시 확정·기한 경과 시 해제한다.

PG 선택은 `PgRouter` 가 한다 — 고액 거래 우선 PG → 수단별 1순위 → fallback 체인 순으로 고르고,
unhealthy 한 PG 는 건너뛴다. 이후 capture·refund 는 **거래 ID prefix** 로 원래 PG 를 찾아간다
(DB 컬럼 추가 없이 이력 보존). 코드 주석은 중간 실패 시 이미 처리된 외부 PG 거래의 보상(Saga)을
"단순화" 했다고 **스스로 밝혀 두었다** — 남은 숙제다.

## 7. 결제 확정 → 정산: Transactional Outbox

```
[order-service 트랜잭션]
  payments UPDATE (CAPTURED)
  outbox_events INSERT (PaymentCaptured)  ← 같은 커밋
            │
   OutboxPublisherScheduler (폴링)
            ▼
   Kafka  lemuel.payment.captured
            ▼
[settlement-service]  PaymentEventKafkaConsumer → CreateSettlementFromPaymentService
```

`CapturePaymentUseCase` 는 정산을 **직접 부르지 않는다.** 결제 상태 변경과 이벤트 레코드를 같은 DB
트랜잭션에 쓰고, 별도 퍼블리셔가 Kafka 로 내보낸다
([Transactional Outbox 패턴](https://microservices.io/patterns/data/transactional-outbox.html)).
그래서 결제 트랜잭션의 성공 여부가 정산 서비스·Kafka 가용성과 분리된다. 이벤트에는 `capturedAt` 이
실려 정산 기준일이 되고, 없으면 settlement 가 KST 현재일로 폴백하며 경고를 남긴다.
Outbox 레코드에는 W3C `traceparent` 도 함께 담아([W3C Trace Context](https://www.w3.org/TR/trace-context/))
비동기 경계를 건너도 트레이스가 이어진다.

order 가 내보내는 이벤트는 `OrderCreated`, `PaymentCreated`, `PaymentAuthorized`, `PaymentCaptured`,
`PaymentRefunded` 다.

## 8. 환불 — 실패 이력은 롤백되면 안 된다

환불은 `approveRefund`(order) → `refundPayment`(payment) 로 이어지고 기본 전파(REQUIRED)라 한 물리
트랜잭션을 공유한다. PG 호출이 실패하면 그 트랜잭션은 통째로 롤백되는데, **"실패했다"는 이력까지
사라지면 재시도·대사의 근거가 없어진다.** 그래서 `RefundLifecycle` 이 환불 시도 행의 상태 전이를
`REQUIRES_NEW` 독립 트랜잭션으로 즉시 커밋한다
([Spring 트랜잭션 전파](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html)).

여기서 교착이 하나 숨어 있었다. PostgreSQL 에서 자식 행 INSERT 는 FK 검사 때문에 부모 행에
`FOR KEY SHARE` 를 잡고, 이는 환불이 payment 를 잠글 때 쓰는 `FOR UPDATE` 와 충돌한다
([PostgreSQL 공식 문서 — Row-Level Locks](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS)).
바깥 트랜잭션이 payment 를 `FOR UPDATE` 로 쥔 채 안쪽 `REQUIRES_NEW` 가 refunds 를 INSERT 하면 서로를 기다린다.

해법은 순서다.

1. **락을 잡기 전에** `REQUESTED` 행을 INSERT·커밋 (같은 `(paymentId, idempotencyKey)` 가 있으면 재사용)
2. 그다음 payment `FOR UPDATE` → PG 환불
3. 성공/실패는 전부 **UPDATE** — FK 재검사가 없어 부모 락을 안 잡는다 → 교착 없음

실패 건은 `FAILED` + 재시도 횟수 + 다음 재시도 시각이 남고, `RefundRetryScheduler` 가 다시 집는다.

## 9. 정리

| 문제 | order-service 의 답 |
|---|---|
| 임의 상태 전이 | enum 한 곳의 전이표 + 도메인 가드 |
| 반쪽 주문(재고·쿠폰·주문 불일치) | 생성 전 과정을 단일 트랜잭션으로 |
| 중복 제출 | 분산 락(낭비 방지) + DB UNIQUE(정합성) |
| 결제 위변조 | PG 호출 **전** 소유권·금액 서버 대조 |
| PG 장애 | 별도 빈 + CircuitBreaker/Retry, 다중 PG 라우팅 |
| 입금 대기 수단 혼합 | 승인만 하고 캡처 보류, 포인트는 선점 |
| 결제↔정산 결합 | Transactional Outbox → Kafka |
| 환불 실패 이력 유실·교착 | REQUIRES_NEW + "INSERT 먼저, 락은 나중" |

공통된 태도가 보인다 — **락·재시도 같은 장치는 최적화로 두고, 최종 정합성은 DB 제약과 트랜잭션
경계에 맡긴다.** 그리고 아직 안 한 것(분할결제 Saga 보상)은 숨기지 않고 주석에 적어 둔다.

## References

- Toss Payments, 결제위젯 연동 가이드 — <https://docs.tosspayments.com/guides/v2/payment-widget/integration>
- IETF, The Idempotency-Key HTTP Header Field (Internet-Draft) — <https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/>
- Spring Framework Reference, Understanding AOP Proxies — <https://docs.spring.io/spring-framework/reference/core/aop/proxying.html>
- Spring Framework Reference, Transaction Propagation — <https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html>
- Resilience4j Documentation — <https://resilience4j.readme.io/docs/getting-started-3>
- PostgreSQL Documentation, Explicit Locking (Row-Level Locks) — <https://www.postgresql.org/docs/current/explicit-locking.html>
- Chris Richardson, Pattern: Transactional Outbox — <https://microservices.io/patterns/data/transactional-outbox.html>
- W3C, Trace Context — <https://www.w3.org/TR/trace-context/>
