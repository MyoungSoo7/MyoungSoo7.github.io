---
layout: post
title: "Spring Boot 안티패턴 *2종* — @Service 비대화 + @Transactional 경계 흐림 (실전 리팩토링)"
date: 2026-05-29 00:30:00 +0900
categories: [refactoring, spring-boot]
tags: [spring-boot, refactoring, clean-code, hexagonal, transactional, ddd, service-layer]
---

새 Spring Boot 프로젝트 시작할 때 누구나 *깔끔하게* 짠다. `OrderService` 가 200줄, `PaymentService` 가 150줄. 한 달 뒤 `OrderService` 는 1500줄, `@Transactional` 이 메서드마다 붙어있고, 어떤 메서드가 *진짜* 비즈니스 경계인지 모르겠다.

이건 *Spring Boot 가 너무 편해서* 생기는 안티패턴이다. 두 가지가 90% 다.

> 본 글의 코드 예시는 *교육용 축약본* 입니다. 실 코드와 표현이 다를 수 있어요.

---

## TL;DR

| # | 안티패턴 | 증상 | 해결 |
|---|---|---|---|
| 1 | `@Service` 가 비대화 | 한 클래스 1000줄+, *비즈니스 규칙 + 검증 + DB 조회 + 외부 호출* 다 섞임 | 비즈니스 규칙은 *도메인 객체로* 빼고, `@Service` 는 *오케스트레이션만* |
| 2 | `@Transactional` 경계가 흐림 | 모든 public 메서드에 `@Transactional`, 한 트랜잭션 안에 *외부 API 호출* + DB 작업 섞임 | 트랜잭션 경계 = *비즈니스 경계*. 외부 호출은 *트랜잭션 밖으로* (Outbox 패턴) |

---

## 안티패턴 1: @Service 비대화 — "편한 곳에 다 넣기"

### 증상 (1년 된 OrderService 의 단면)

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepo;
    private final UserRepository userRepo;
    private final InventoryClient inventoryClient;
    private final PaymentClient paymentClient;
    private final NotificationService notification;
    // ... 의존성 12개

    @Transactional
    public OrderResult placeOrder(OrderRequest req) {
        // 1. 검증 (50줄)
        if (req.getQuantity() <= 0) throw new InvalidOrderException(...);
        if (req.getQuantity() > 100) throw new InvalidOrderException(...);
        var user = userRepo.findById(req.getUserId())
            .orElseThrow(() -> new UserNotFoundException(...));
        if (user.getStatus() != UserStatus.ACTIVE) throw new ...;
        // ...

        // 2. 재고 확인 (외부 호출, 20줄)
        var stock = inventoryClient.check(req.getProductId());
        if (stock.getAvailable() < req.getQuantity()) throw new ...;

        // 3. 가격 계산 + 할인 (80줄)
        BigDecimal price = ...;
        if (user.getMembership() == GOLD) price = price.multiply(...);
        // ...

        // 4. 결제 (외부 호출, 30줄)
        var payment = paymentClient.charge(...);

        // 5. 저장
        var order = new Order(...);
        orderRepo.save(order);

        // 6. 알림 (40줄)
        notification.send(...);

        return new OrderResult(order);
    }

    // ... placeOrder 와 비슷한 패턴의 메서드 8개 더
}
```

문제:
- *비즈니스 규칙* (수량 한도, 회원 할인, 가격 계산) 이 `@Service` 에 hardcoding
- *주문이라는 도메인* 의 본질이 *코드 어디에도 없음* — 그냥 절차의 나열
- 테스트할 때 `@Service` 전체 mock 해야 함 → `InventoryClient`, `PaymentClient` 등 *외부 의존성 다 stub*
- 비즈니스 규칙 하나 바꾸면 *DB / 외부 API mock 까지 다 setup* 해야 테스트 가능

### 리팩토링: 도메인 객체로 *규칙* 빼기

```java
// === 도메인 객체 ===
public class Order {
    private final OrderId id;
    private final UserId userId;
    private final List<OrderLine> lines;
    private OrderStatus status;

    // 비즈니스 규칙: "주문은 1~100 사이 수량만"
    public static Order place(User user, Product product, int quantity, Pricing pricing) {
        if (quantity <= 0 || quantity > 100) {
            throw new InvalidOrderException(quantity);
        }
        if (!user.canOrder()) {
            throw new UserCannotOrderException(user.getId());
        }
        var price = pricing.calculate(product, quantity, user.getMembership());
        return new Order(OrderId.generate(), user.getId(), List.of(new OrderLine(product, quantity, price)));
    }

    public boolean isPayable() { return status == OrderStatus.PENDING; }
}

// === Service 는 *오케스트레이션만* ===
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepo;
    private final UserRepository userRepo;
    private final ProductCatalog productCatalog;
    private final Pricing pricing;

    @Transactional
    public OrderId placeOrder(OrderRequest req) {
        var user = userRepo.findById(req.getUserId()).orElseThrow();
        var product = productCatalog.findById(req.getProductId()).orElseThrow();
        var order = Order.place(user, product, req.getQuantity(), pricing);   // ← 비즈니스 규칙은 *여기*
        orderRepo.save(order);
        return order.getId();
    }
}
```

효과:
- `Order.place(...)` 는 *순수 도메인 테스트* 가능 — Spring context 필요 없음, DB mock 필요 없음
- `@Service` 는 *3줄 짜리 오케스트레이션* — 의존성 4개로 줄어듦
- 새 비즈니스 규칙 추가는 *도메인 객체에만* — 다른 코드 영향 없음
- *재고 확인 / 결제 / 알림* 같은 외부 부수효과는 *다른 곳으로* (안티패턴 2 에서 다룸)

---

## 안티패턴 2: @Transactional 경계 흐림 — "일단 다 묶기"

### 증상

```java
@Service
public class OrderService {

    @Transactional        // ← 한 트랜잭션 안에 *모든 것*
    public OrderResult placeOrder(OrderRequest req) {
        var order = Order.place(...);
        orderRepo.save(order);

        var payment = paymentClient.charge(...);  // ← ⚠️ 외부 HTTP 호출
        notification.sendEmail(...);              // ← ⚠️ 외부 SMTP
        return new OrderResult(order);
    }
}
```

문제:
- `@Transactional` 이 PG 외부 호출까지 *물고 있음* → PG 응답 5초 동안 *DB 커넥션 점유*
- PG 가 timeout → *DB 트랜잭션 롤백* → 그런데 PG 측에선 이미 *결제 성공* 상태
- 이메일 발송 실패 → 주문 자체가 롤백 → *주문은 됐어야 했는데* 사라짐
- 트랜잭션 안에서 *시간이 오래 걸리는 작업* 이 있으면 → 데드락·DB 풀 고갈

### 리팩토링: 트랜잭션 *안* 과 *밖* 분리 + Outbox 패턴

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepo;
    private final OutboxRepository outbox;

    @Transactional      // ← *DB 작업만* (수 ms)
    public OrderId placeOrder(OrderRequest req) {
        var order = Order.place(...);
        orderRepo.save(order);
        outbox.save(new OrderPlacedEvent(order.getId()));   // ← 같은 트랜잭션에 *이벤트 저장*
        return order.getId();
    }
}

// === 외부 호출은 *트랜잭션 밖*, 별도 워커 ===
@Component
@RequiredArgsConstructor
public class OutboxPublisher {
    private final OutboxRepository outbox;
    private final PaymentClient paymentClient;

    @Scheduled(fixedDelay = 1000)
    public void publish() {
        var events = outbox.findUnpublished(100);
        for (var event : events) {
            try {
                paymentClient.charge(event);     // ← 외부 호출, *트랜잭션 없음*
                outbox.markPublished(event.getId());
            } catch (Exception e) {
                // 재시도, DLQ, 메트릭...
            }
        }
    }
}
```

효과:
- `@Transactional` 메서드는 *수 ms* 안에 끝남 (DB INSERT + outbox INSERT 만)
- 외부 PG 호출은 *별개 워커* 에서 — 실패해도 재시도 가능, DB 트랜잭션 영향 없음
- *at-least-once 메시징 + idempotent 수신* 으로 안전 (PG 측 idempotency key 필요)
- DB 커넥션 풀이 *외부 응답 시간에 종속되지 않음* → 대량 트래픽도 안정

이게 *Outbox 패턴* — settlement / payment 도메인의 *교과서 패턴*. Spring Boot 에선 `@TransactionalEventListener(phase = AFTER_COMMIT)` 또는 별도 워커로 구현.

---

## 정리

| 안티패턴 | 답 한 줄 |
|---|---|
| @Service 비대화 | 비즈니스 규칙은 *도메인 객체로*, @Service 는 *오케스트레이션만* |
| @Transactional 경계 흐림 | 트랜잭션 안엔 *DB 작업만*, 외부 호출은 *밖으로* (Outbox) |

둘 다 *Spring Boot 가 너무 편해서* 생긴다 — `@Service` 에 다 넣어도 동작하고, `@Transactional` 도 일단 붙이면 동작하니까. 그 *동작* 이 *작동* 으로 충분한 단계엔 문제 없지만, 트래픽 / 규칙 / 외부 의존성이 늘어나면 *작은 단위로 갈라놓지 않은 비용* 이 한꺼번에 청구된다.

리팩토링의 핵심은 *"한 번에 다 갈아엎지 마라"* — 하나의 `@Service` 메서드부터 *도메인 객체로 비즈니스 규칙 빼기* 시작하면 된다. 30분이면 그 메서드의 *테스트* 가 Spring context 없이 돌아간다 — 그것 하나만으로도 가치는 충분하다.
