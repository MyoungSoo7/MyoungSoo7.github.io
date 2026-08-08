---
layout: post
title: "고객의 상품 주문에서 결제·정산까지: Settlement order-service와 settlement-service 구조 분석"
date: 2026-08-09 10:10:00 +0900
categories: [Architecture, Backend, Finance]
tags: [Settlement, Order Service, Payment, Kafka, Outbox, CQRS, Reconciliation, Ledger]
---

# 고객의 상품 주문에서 결제·정산까지

## 이 글의 범위와 근거

이 글은 `MyoungSoo7/settlement` 저장소의 기준 커밋 `70d24bb`를 기준으로 `order-service`와 `settlement-service`의 소스코드·migration·설정·테스트를 읽어 고객의 상품 주문이 결제와 정산으로 이어지는 흐름을 설명한다.

```text
Repository: https://github.com/MyoungSoo7/settlement
Branch: feat/card-service-phase2-gowid
Commit: 70d24bb
Inspection: 2026-08-09
```

운영 DB, 실제 고객 정보, 실제 PG 거래를 조회한 분석이 아니다. 따라서 다음을 구분한다.

```text
관찰됨
= 소스·설정·테스트에서 직접 확인

설계 의도
= 주석·ADR·문서가 설명

추론
= 여러 코드 관계를 연결한 해석

미확인
= runtime trace·실제 Kafka·실제 PG로 확인해야 하는 부분
```

## 전체 흐름 한눈에 보기

고객 관점의 핵심 흐름은 다음과 같다.

```text
상품 탐색
  → 장바구니
  → 주문 생성
  → 결제 생성/승인
  → PG capture
  → 주문 PAID
  → PaymentCaptured Outbox
  → Kafka
  → settlement-service 소비
  → settlement 생성
  → 정산 프로젝션·원장·지급예정
  → reconciliation
```

중요한 설계 선택은 주문과 정산이 같은 DB 트랜잭션으로 묶이지 않는다는 점이다.

```text
order-service DB
  = 고객 주문·결제의 원천 상태

settlement-service DB
  = 정산·원장·지급·대사의 소유 상태

연결
  = Kafka 이벤트 + 로컬 프로젝션 + 내부 대사 API
```

이 경계는 장애 격리와 독립 배포에 유리하지만, 이벤트 유실·중복·지연·프로젝션 불일치를 별도의 운영 문제로 만든다.

## 1. 고객이 상품을 선택하는 단계

`order-service`에는 상품·카테고리·메뉴·쿠폰·장바구니 도메인이 존재한다. 장바구니는 영속 저장소와 Redis 어댑터를 함께 사용하도록 구성되어 있다.

```text
Product/Menu/Category
        ↓
Cart
 ├─ userId
 ├─ productId
 ├─ variantId
 └─ quantity
```

장바구니 체크아웃은 `CheckoutCartService`가 담당한다.

소스에서 확인되는 순서는 다음과 같다.

1. 사용자 장바구니 조회
2. 장바구니가 없거나 비어 있으면 실패
3. 각 `CartItem`을 주문 line으로 변환
4. `CreateMultiItemOrderUseCase` 호출
5. 주문 생성 성공 시 장바구니 비우기
6. 주문 생성 실패 시 트랜잭션 롤백으로 장바구니 유지

이 흐름은 사용자 경험 측면에서 중요하다. 주문 생성이 실패했는데 장바구니를 먼저 비우면 고객은 재시도할 상품 목록을 잃는다. 현재 코드의 주석과 `@Transactional` 경계는 이 상황에서 장바구니를 유지하려는 의도를 보여준다.

다만 `CreateMultiItemOrderUseCase` 내부에서 재고·주문·결제 준비가 어떤 원자성으로 처리되는지는 해당 구현과 통합 테스트를 추가로 확인해야 한다. 장바구니 트랜잭션과 외부 PG 호출은 동일한 원자성을 가질 수 없으므로, 실제 결제 시점에는 별도의 상태 머신이 필요하다.

## 2. 주문 생성: 고객 요청이 도메인 상태가 되는 지점

단일 상품 주문의 중심은 `CreateOrderService`다.

```text
CreateOrderRequest
  → CreateOrderService
  → 사용자 존재 확인
  → Order.create()
  → SaveOrderPort
  → OrderCreated Outbox
  → 주문 알림
```

소스에서 확인되는 구체적인 동작은 다음과 같다.

### 사용자 확인

`LoadUserForOrderPort.findEmailById()`로 사용자의 존재와 이메일을 확인한다. 사용자가 없으면 `UserNotExistsException`이 발생하고 주문을 만들지 않는다.

### 도메인 생성과 검증

`Order.create(userId, productId, amount)`가 주문 도메인을 생성한다. 세부 불변식은 `Order`와 `OrderInvariantViolationException`을 함께 읽어야 하며, 일반적으로 금액·상태·필수 식별자 검증은 도메인 경계에서 수행하는 것이 맞다.

### 저장

`SaveOrderPort`를 통해 order-service가 소유한 DB에 주문을 저장한다. settlement-service가 order DB를 직접 읽어 주문을 만들지 않는 이유는 서비스 경계를 보존하기 위해서다.

### 이벤트 기록

주문 저장 후 `PublishOrderEventPort.publishOrderCreated()`가 호출된다. 실제 어댑터는 `OutboxBackedOrderEventPublisher`다.

```java
publishOrderCreated(
    orderId,
    userId,
    productId,
    status,
    amount,
    createdAt
)
```

이 메서드는 곧바로 Kafka에 쓰는 것이 아니라 order-service DB의 `outbox_events`에 `OrderCreated` 이벤트를 저장한다. 주문 상태와 이벤트를 같은 DB 트랜잭션 안에서 커밋하려는 Transactional Outbox 패턴이다.

```text
orders INSERT
+ outbox_events INSERT
= 하나의 DB commit
```

그 후 별도의 Outbox publisher/scheduler가 pending 이벤트를 읽어 Kafka로 보낸다. 따라서 주문 API의 성공이 곧 Kafka 소비 완료를 뜻하지 않는다.

## 3. 결제 준비: READY에서 AUTHORIZED로

결제 도메인은 `PaymentDomain`과 결제 유스케이스로 분리되어 있다. 상태 흐름은 코드 주석과 도메인 타입에서 다음처럼 확인된다.

```text
READY
  → AUTHORIZED
  → CAPTURED

AUTHORIZED
  → CANCELED

CAPTURED
  → REFUNDED
```

`PaymentController`에는 결제 생성, 승인, capture, Toss 결제 확인 및 장바구니 결제 경로가 노출되어 있다.

일반적인 승인 흐름은:

```text
Payment 생성
  → READY
  → PG authorize
  → pgTransactionId 저장
  → AUTHORIZED
```

PG 호출은 `PgClientPort`/`PaymentGatewayAdapter` 경계를 통해 이뤄진다. 저장소에는 Toss, Nice, Inicis, KCP와 Mock 어댑터가 있고, `PgRouter`는 거래 식별자 prefix를 사용해 후속 capture/refund를 동일 PG로 라우팅하도록 설계되어 있다.

```text
TOSS:transaction-id
NICE:transaction-id
KCP:transaction-id
```

이 prefix가 중요한 이유는 승인 때 선택한 PG와 capture/refund 때 선택하는 PG가 달라지면 외부 결제 상태를 찾지 못할 수 있기 때문이다.

## 4. Toss 결제 확인과 capture

`TossPaymentService.confirmTossPayment()`의 소스 주석은 다음 순서를 설명한다.

```text
1. Toss 결제 확인 API 호출
2. READY 결제 생성
3. payment.authorize(paymentKey)
4. AUTHORIZED 저장
5. capturePayment()
6. CAPTURED 저장
7. 주문 PAID
8. PaymentCaptured Outbox 기록
```

Toss 확인 API 호출에는 다음 보호 장치가 있다.

```text
RestTemplate connect timeout: 3초
RestTemplate read timeout: 5초
Resilience4j Retry
Resilience4j CircuitBreaker
```

이것은 외부 PG가 느리거나 일시적으로 실패할 때 Spring 요청 스레드가 무한정 붙잡히는 것을 막는 설계다. 다만 재시도 가능 여부는 결제 API의 멱등성 계약과 함께 판단해야 한다. 결제 확인 요청을 무조건 재시도하면 외부 PG에서 중복 처리 위험이 생길 수 있다.

`CapturePaymentUseCase`에서 확인되는 실제 순서는 다음과 같다.

```text
paymentId로 결제 조회
  → PG capture
  → PaymentDomain.capture()
  → payment 저장
  → order 상태 PAID
  → PaymentCaptured 이벤트 outbox 저장
```

여기서 외부 PG capture와 로컬 DB commit은 하나의 분산 트랜잭션이 아니다.

```text
PG capture 성공 + DB 저장 실패
PG capture 실패 + DB 상태 미변경
DB 성공 + 이벤트 발행 지연
```

각 경우를 복구할 수 있도록 PG 조회·reconcile·outbox 재발행·대사 API가 필요하다. 저장소에는 `recon`과 outbox 상태 조회 경로가 있어 이 문제를 운영적으로 보완하려는 방향이 보인다.

## 5. PaymentCaptured 이벤트의 봉투

`OutboxBackedEventPublisher.publishPaymentCaptured()`는 결제 완료 사실을 이벤트로 만든다. 이벤트에는 다음 정보가 포함된다.

```text
paymentId
orderId
amount
capturedAt
paymentMethod
pgTransactionId
sellerId
sellerTier
settlementCycle
traceParent
```

seller tier와 settlement cycle을 이벤트에 동봉하는 것은 Event-Carried State Transfer 전략이다.

```text
기존 방식:
settlement가 order DB를 조회해 seller 정보 조인

동봉 방식:
order가 결제 이벤트에 정산에 필요한 seller metadata 포함
```

장점은 settlement-service가 order DB에 직접 의존하지 않는다는 점이다. 단점은 이벤트 스키마가 변경될 때 producer·consumer 계약과 하위 호환성을 관리해야 한다는 점이다.

`capturedAt`은 특히 중요하다. settlement-service는 소비 시각이 아니라 결제가 발생한 날짜를 정산 기준일로 사용하려고 한다. 이벤트가 지연되거나 재처리되어도 같은 결제가 같은 정산일을 얻어야 하기 때문이다.

```text
정산 기준일 = PaymentCaptured.capturedAt의 날짜
```

capturedAt이 없는 레거시 이벤트는 KST 현재일로 fallback하도록 구현되어 있으므로, 구 이벤트·백필에서는 기준일이 흔들릴 수 있다는 운영상 주의가 필요하다.

## 6. Settlement가 이벤트를 소비하는 방법

`settlement-service`의 `PaymentEventKafkaConsumer`는 `PaymentCaptured` 이벤트를 소비한다.

```text
Kafka topic:
lemuel.payment.captured

consumer group:
lemuel-settlement
```

소비 과정은 `IdempotentEventConsumer` 기반이다.

```text
Kafka ConsumerRecord
  → event envelope/header 파싱
  → processed_events 멱등 체크
  → JSON payload 검증
  → 정산 생성
  → settlement_payment_view upsert
  → processed marker
  → ack
```

멱등성 방어는 세 층으로 설명된다.

```text
1. outbox event_id UUID unique
2. processed_events(consumer_group, event_id) PK
3. settlements.payment_id UNIQUE
```

이 구조의 의미는 이벤트가 중복 전달되어도 정산금이 두 번 생성되지 않도록 하는 것이다. 1번과 2번이 정상이어도 경쟁 조건이나 다른 event_id를 가진 동일 결제가 들어올 수 있으므로, 3번 DB unique가 최종 방어선이 된다.

독성 메시지와 일시적 오류도 구분한다.

```text
JSON/IllegalArgument 오류
  → 재시도보다 DLT

일시적 인프라 오류
  → exponential backoff 재시도
  → 계속 실패하면 DLT
```

이 구분이 없으면 잘못된 메시지 하나가 Kafka 파티션의 후속 정상 메시지를 계속 막을 수 있다.

## 7. Settlement 생성 내부

`CreateSettlementFromPaymentService`는 결제 이벤트를 실제 정산 도메인으로 변환한다.

### 이미 존재하는 정산 확인

먼저 `paymentId`로 기존 정산을 조회한다.

```text
이미 존재
→ 기존 settlement 반환
```

없으면 seller tier·settlement cycle을 결정한다.

```text
이벤트 동봉값 우선
  → 없으면 order 관련 fallback port
  → 그래도 없으면 NORMAL/default cycle
```

### 정산금 계산

`Settlement.createFromPayment(paymentId, orderId, amount, settlementDate, tier.rate())`로 정산을 만든다. 이후 seller tier에 따른 holdback 정책을 적용한다.

```text
payment amount
  → commission
  → net amount
  → holdback
  → settlement date
```

코드에는 다음과 같은 핵심 불변식이 연결되어 있다.

```text
payment = net + commission
```

정산 원장으로 넘어가는 금액은 단순히 고객이 지불한 총액이 아니다. 수수료·환불·보류금·지급 예정일을 분리해야 한다.

### 동시 생성 경합

`findByPaymentId()` 후 `save()`는 전형적인 check-then-act 구조다. 두 consumer가 동시에 통과할 수 있으므로 DB의 `settlements.payment_id UNIQUE`가 필요하다.

코드는 `DataIntegrityViolationException`이 발생했을 때 기존 승자 정산을 다시 조회해 반환하는 경합 수렴 경로를 갖는다.

```text
동시 생성
  → 한 트랜잭션 INSERT 성공
  → 다른 트랜잭션 unique 충돌
  → 승자 행 재조회
  → 기존 정산 반환
```

금융 시스템에서 중요한 것은 “예외가 발생하지 않는 것”이 아니라 **경쟁 상황에서도 최종 금액이 한 번만 기록되는 것**이다.

## 8. Settlement order projection

`OrderCreated` 이벤트는 `settlement_order_view`에 적재된다.

```text
OrderCreated
  → OrderEventKafkaConsumer
  → settlement_order_view upsert
```

`PaymentCaptured` 이벤트는 `settlement_payment_view`에 적재된다.

```text
PaymentCaptured
  → PaymentEventKafkaConsumer
  → settlement_payment_view upsert
```

이것은 CQRS 형태의 로컬 읽기 모델이다.

```text
쓰기 원천:
order-service DB

읽기 모델:
settlement-service DB의 order/payment view
```

settlement-service가 order DB 테이블을 직접 `@Immutable` 매핑하는 대신 이벤트로 자체 view를 유지하면 서비스 간 DB coupling을 줄일 수 있다. 대신 다음을 운영해야 한다.

- consumer lag
- projection 상태
- missing event
- replay/backfill
- schema compatibility
- projection drift

## 9. 고객 주문에서 정산까지의 상세 시나리오

### 정상 케이스

```text
1. 고객이 상품을 장바구니에 담는다.
2. CheckoutCartService가 cart를 읽는다.
3. cart item을 order line으로 변환한다.
4. order-service가 사용자와 상품 정보를 검증한다.
5. Order가 생성·저장된다.
6. OrderCreated가 outbox에 기록된다.
7. outbox publisher가 Kafka에 발행한다.
8. 고객이 PG 결제를 확인한다.
9. payment가 READY→AUTHORIZED→CAPTURED로 이동한다.
10. order 상태가 PAID가 된다.
11. PaymentCaptured가 outbox에 기록된다.
12. Kafka가 settlement-service로 전달한다.
13. settlement consumer가 멱등 체크한다.
14. 결제일과 seller policy로 settlement date를 계산한다.
15. commission·net·holdback을 계산한다.
16. settlement를 저장한다.
17. settlement_payment_view를 갱신한다.
18. 원장·지급·대사 후속 흐름으로 연결된다.
```

### PG 승인 실패

```text
PG authorize 실패
→ payment AUTHORIZED 전환 안 됨
→ capture 실행 안 됨
→ PaymentCaptured 없음
→ settlement 생성 없음
→ 주문은 결제 실패/미완료 상태
```

### PG capture 성공 뒤 DB 오류

```text
PG capture 성공
→ 로컬 DB 저장 실패
→ 고객·PG에는 결제 성공
→ order-service에는 상태 미반영 가능
→ PaymentCaptured 없음 가능
→ 대사·PG 조회·복구 작업 필요
```

### 이벤트 발행 지연

```text
payment CAPTURED
→ outbox PENDING
→ Kafka 발행 지연
→ settlement 미생성
→ order 원천 합계 > settlement 합계
```

이 경우 settlement를 즉시 “금액 오류”로 판단하면 안 된다. 먼저 order outbox 상태와 Kafka lag를 확인해야 한다.

### 이벤트 중복

```text
동일 PaymentCaptured 재전달
→ processed_events 확인
→ 이미 처리됐으면 종료/ack
```

다른 event_id로 같은 payment가 전달되는 비정상 상황은 `settlements.payment_id UNIQUE`와 예외 수렴 로직이 차단한다.

### 환불

환불은 원 결제를 삭제하거나 금액을 조용히 덮는 방식이 아니라 `PaymentRefunded`와 adjustment/reversal 경로로 이어져야 한다.

```text
CAPTURED
  → refund 요청
  → PG 환불
  → PaymentRefunded Outbox
  → settlement adjustment
  → ledger reversal/조정
  → reconciliation
```

실제 환불 전체의 소비·조정·원장 연결은 별도 source와 테스트를 함께 확인해야 하며, 이 글의 주문→최초 결제 흐름과 분리해 운영해야 한다.

## 10. 왜 order와 settlement를 직접 연결하지 않는가

두 서비스가 같은 DB를 조회하면 처음에는 간단해 보인다.

```text
settlement → order.orders SELECT
settlement → order.payments SELECT
```

하지만 다음 문제가 생긴다.

- DB schema 변경이 양쪽 배포를 묶는다.
- 장애 시 settlement가 order DB에 연쇄 의존한다.
- 권한 경계가 약해진다.
- 읽기 부하가 원천 서비스로 전파된다.
- 서비스 ownership이 흐려진다.

현재 설계는 이를 줄이기 위해:

```text
Kafka event
+ local projection
+ internal recon API
```

를 사용한다. `settlement-service` 설정과 `AGENTS.md`에는 settlement와 order 사이의 직접 DB 의존을 피하고, 이벤트 프로젝션과 내부 대사 API를 사용한다는 경계가 기록되어 있다.

내부 대사 API는 정산 생성의 원천 흐름이 아니라 **정합성 확인·보완 경로**다.

```text
정상 생성:
PaymentCaptured event

검증:
order internal recon API

불일치 조사:
projection status → outbox status → ledger/reconciliation
```

## 11. 대사(Reconciliation)가 필요한 이유

이벤트 기반 시스템은 각 서비스의 로컬 성공이 전체 플로우 성공과 같지 않다.

```text
order 결제 합계
vs
settlement 생성 합계
vs
ledger posting 합계
vs
payout 합계
```

대사는 다음 차이를 찾는다.

| 불일치 | 가능한 원인 |
|---|---|
| settlement < order | outbox pending, Kafka lag, consumer 실패, DLT |
| settlement > order | 중복 소비, 멱등 방어 실패, 잘못된 재처리 |
| ledger < settlement | ledger outbox 지연, 원장 posting 실패 |
| payout < ledger | 지급 배치 지연, holdback, 은행 오류 |
| 환불만 불일치 | PaymentRefunded 지연, adjustment 미생성, 날짜 기준 차이 |

정산 리포트의 합계는 날짜 기준도 중요하다.

```text
order captured_at 기준
settlement created_at 기준
settlement_date 기준
payout_date 기준
```

서로 다른 날짜 축을 비교하면 시스템이 정상이어도 불일치처럼 보인다. 따라서 대사는 캡처 축·환불 축·정산일 축을 명시해야 한다.

## 12. 이 구조의 강점과 한계

### 강점

- 주문·결제·정산 서비스의 DB ownership 분리
- Transactional Outbox로 로컬 변경과 이벤트 기록 원자화
- Kafka를 통한 비동기 장애 격리
- 로컬 read projection으로 cross-DB coupling 감소
- processed_events와 unique constraint의 중복 방어
- DLT·retry·quarantine 기반 독성 메시지 격리
- capturedAt 기준 정산일 결정으로 재처리 안정성 향상
- 내부 recon API로 원천과 결과를 비교 가능

### 한계

- 고객 결제 성공과 정산 생성 사이에 지연 구간이 존재
- Kafka·outbox·consumer·DB 각각의 장애를 운영해야 함
- 이벤트 schema 변경 호환성 관리 필요
- PG capture와 로컬 DB commit 사이에는 분산 트랜잭션 공백 존재
- legacy 이벤트에 capturedAt이 없으면 정산일 fallback 위험
- 실제 end-to-end PG·Kafka·운영 DB trace 없이는 production 성공률을 확정할 수 없음

## 13. 운영자가 장애를 조사하는 순서

결제 완료 후 정산이 보이지 않을 때 바로 settlement DB를 수정하지 않는다.

```text
1. order-service에서 payment 상태 확인
2. captured_at·amount·order_id 확인
3. outbox에서 PaymentCaptured 상태 확인
4. Kafka topic·consumer lag 확인
5. settlement processed_events 확인
6. settlement_payment_view 확인
7. settlements.payment_id 존재 여부 확인
8. DLT/quarantine 확인
9. ledger outbox와 posting 상태 확인
10. order recon API와 기간 기준을 맞춰 대사
```

각 단계는 다음 질문에 답해야 한다.

```text
원천 결제가 실제 CAPTURED인가?
이벤트가 기록됐는가?
발행됐는가?
소비됐는가?
멱등 체크에서 제외됐는가?
정산 저장이 성공했는가?
원장으로 넘어갔는가?
```

이 순서를 지키면 “정산이 없다”는 현상을 발행 지연·소비 실패·중복 차단·날짜 기준 오류로 분해할 수 있다.

## 결론

이 저장소에서 고객의 상품 주문과 결제는 하나의 거대한 트랜잭션으로 끝나지 않는다.

```text
주문 생성
  = order-service의 원천 상태

결제 capture
  = PG와 order-service payment 상태의 확정

PaymentCaptured
  = 결제 완료를 전달하는 이벤트 계약

Settlement
  = settlement-service가 정책·수수료·보류·정산일을 적용한 회계 후보

Ledger/Payout/Reconciliation
  = 돈의 이동과 정합성을 끝까지 확인하는 후속 계층
```

핵심은 **결제 성공을 정산 성공으로 착각하지 않는 것**이다. 결제 성공 뒤에는 outbox·Kafka·consumer·projection·idempotency·settlement·ledger·payout이라는 여러 경계가 있다.

```text
order-service
  → PaymentCaptured Outbox
  → Kafka
  → settlement-service
  → Settlement
  → Ledger
  → Payout
  → Reconciliation
```

이 플로우가 금융 시스템으로서 신뢰받으려면 코드만으로 충분하지 않다. 각 단계의 상태·이벤트·재시도·멱등성·DLT·대사·rollback을 관측하고, 실제 Trace로 성공을 증명해야 한다.

## 참고 자료

- [Settlement repository](https://github.com/MyoungSoo7/settlement)
- [Order service source](https://github.com/MyoungSoo7/settlement/tree/feat/card-service-phase2-gowid/order-service)
- [Settlement service source](https://github.com/MyoungSoo7/settlement/tree/feat/card-service-phase2-gowid/settlement-service)
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Spring Kafka Reference](https://docs.spring.io/spring-kafka/reference/)

> 이 글은 Settlement 저장소의 정적 소스·설정·문서·테스트를 기반으로 작성했다. 실제 PG 승인, Kafka 전달 지연, 운영 DB 정합성, 원장·지급 성공률은 runtime Trace와 운영 데이터로 별도 검증해야 한다.

> 기준 commit: `70d24bb` · 운영 DB·실제 고객정보 접근 없음 · 실제 PG 거래 실행 없음 · 클러스터 변경 없음
