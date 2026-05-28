---
layout: post
title: "Java · Spring · Hexagonal — *복잡 *도메인의 *정합성 + 확장성을 *책임지는 *팀 표준 *설계*"
date: 2026-05-29 03:40:00 +0900
categories: [architecture, ddd, java, spring]
tags: [hexagonal, ddd, spring-boot, spring-modulith, archunit, aggregate, domain-event, java, technical-standard, senior-engineer]
---

> *''*우리 팀의 *코드가 *3 년 후에도 *유지보수 가능 할까?''*''*. *시니어가 *팀 코드 *리뷰하다 *문득 *떠올리는 *이 *질문은 *''*기술 표준의 *부재''* 의 *증상* 이다. *3 명 *팀이 *각자 *''*자신의 *베스트 *프랙티스''* 로 *짜면 *결과는 *3 가지 *서로 *다른 *구조*. *6 개월 뒤 *합류한 *신입은 *''*어느 게 *맞는 거지?''* 라며 *또 *네 번째 *스타일을 *만든다*.
>
> *''*기술 표준''* 은 *''*독재''* 가 *아니다*. *''*팀이 *같은 *문제에 *같은 *답을 *낼 수 있게 *만드는 *집단적 *어휘''* 다. 이 글은 *Java + Spring + Hexagonal Architecture* 를 *기반으로*, *복잡 도메인의 *정합성과 *확장성을 *책임지는 *팀 표준* 을 *어떻게 *정의하고 *어떻게 *유지할 것인가* 를 *시니어 백엔드 *관점에서 *과거의 *교훈과 *미래의 *방향* 으로 본다.

대상은 *''*팀 표준을 *써야 할 *시니어 / 아키텍트''*, 그리고 *''*우리 팀의 *코드가 *왜 *복잡할까''* 를 *진지하게 *고민하는 *모든 미들 ~ 시니어 백엔드 개발자*.

---

## 1. *왜 *이 주제가 *시니어의 *책임인가*

### 1.1 *조직의 *기술 자산은 *''*표준 + 문화''* 의 *산물*

코드 자산은 *2 가지 *방식으로 *축적된다*:

```
[강한 표준 + 일관된 문화]
  ├─ 모든 신규 코드가 *같은 패턴*
  ├─ 신규 입사자도 *2 주 *내 적응
  └─ *기술 자산 = *증가*

[느슨한 표준 + 자유 문화]
  ├─ 각자 *자신의 *베스트 *추구*
  ├─ 6 개월 후 *''*Big Ball of Mud""*
  └─ *기술 자산 = *감소 (오히려 *부채)*
```

*표준이 *없으면 *''*개인 *생산성 ↑* but *조직 *생산성 ↓*''*. *시니어의 *책임* = *''*개인 생산성을 *조금 *희생해서 *조직 생산성을 *압도적으로 *올리는 *표준을 *만드는 것''*.

### 1.2 *''*복잡 도메인''* 의 *진짜 의미*

*복잡 도메인* 의 *정의*:

- *비즈니스 *규칙이 *수십 ~ 수백 *개*
- *규칙 *간 *연쇄 *효과 (조건 *A → 조건 *B 가 *영향)*
- *시간에 *따라 *변화 (예: *프로모션, 가격 정책 *분기별 변경)*
- *법적 / 회계적 *제약 *존재 (전자상거래법, *세금)*

이런 도메인에 *''*Spring 만 *잘 *알면 *된다''* 는 *''*몇 달 안에 *진흙공''* 으로 *직행*. *''*도메인 자체의 *구조가 *코드 구조에 *반영* 되어야 *유지보수 가능''*.

### 1.3 *''*정합성''* 과 *''*확장성''* 의 *동시 *추구*

대부분의 *기술 결정* 은 *둘 중 *하나에만 *집중*:

- *''*정합성 위주 — *엄격한 *제약, *유연성 부족''*
- *''*확장성 위주 — *느슨한 *경계, *데이터 *불일치 위험""*

진짜 시니어는 *''*둘을 *동시에''* 책임지는 *구조를 *설계할 수 있다*. 그게 *Hexagonal + DDD 의 *핵심 가치*.

---

## 2. *과거 — *''*우리가 *어떻게 *여기까지 *왔는가''*

### 2.1 *2010 년대 초 — *''*Anemic Domain Model''* 의 *전성기*

```java
// 전형적 *2010 년대 패턴*

@Entity
public class Order {
    private Long id;
    private OrderStatus status;
    private BigDecimal amount;
    // getters / setters *만*
}

@Service
public class OrderService {
    @Autowired private OrderRepository orderRepo;

    public void cancel(Long orderId) {
        Order order = orderRepo.findById(orderId).orElseThrow();
        if (order.getStatus() == OrderStatus.PAID) {
            order.setStatus(OrderStatus.CANCELED);
            // *비즈니스 *로직이 *Service 에 *집중*
            // *Entity 는 *''*데이터 *컨테이너""*
        }
        orderRepo.save(order);
    }
}
```

Martin Fowler 의 *''*Anemic Domain Model''* (2003 글). *''*객체가 *행동 없이 *데이터만 *들고 있음''*. *DDD 의 *반대 패턴*.

#### *문제점*

- *비즈니스 *규칙이 *Service 에 *흩어져 *재사용 *어려움*
- *''*같은 *cancel 로직''* 이 *3 곳에 *복사*
- *''*Order 라는 *말이 *''*무엇을 *할 수 있는가""*가 *Order *클래스만 *봐서는 *모름""*

### 2.2 *2010 년대 중반 — *''*패키지 by Layer''* 의 *함정*

```
com.lemuel.shop/
  ├─ controller/
  │   ├─ OrderController
  │   ├─ PaymentController
  │   └─ InventoryController
  ├─ service/
  │   ├─ OrderService
  │   ├─ PaymentService
  │   └─ InventoryService
  ├─ repository/
  │   ├─ OrderRepository
  │   ├─ PaymentRepository
  │   └─ InventoryRepository
  └─ entity/
      ├─ Order
      ├─ Payment
      └─ Inventory
```

*''*기술 *역할별 *분류""*. *''*모든 *Controller 가 *한 폴더, *Service 가 *한 폴더""*.

#### *문제점*

- *''*Order 도메인의 *''*전체 *그림""*'' 을 *보려면 *4 폴더 *돌아다녀야 *함*
- *''*Order 만 *수정하는데 *Payment 도 *건드리고 싶은 *유혹""*
- *''*도메인 *경계 *= *없음""*

### 2.3 *2010 년대 후반 — *''*Microservices''* 의 *유행 *직격*

```
[유행 1] *''*우리도 *MSA 하자""* — *팀이 *5 명인데 *15 마이크로서비스*
[유행 2] *''*분산 트랜잭션 모름""* — *유령 *주문 *수십 건*
[유행 3] *''*Eventual consistency 모름""* — *고객 *민원 *폭증*
```

*''*도메인 *분리 *없이 *물리적 *분리""* 가 *재앙*. *''*MSA 이전에 *모듈러 *모놀리식 부터""* 의 *교훈이 *늦게 *옴*.

### 2.4 *2020 년대 — *''*Hexagonal + DDD + Spring Modulith''* 의 *부상*

```
[새로운 *합의]
- *Bounded Context *명확히
- *Port / Adapter *경계 *컴파일러처럼 강제 (ArchUnit)
- *Aggregate / Value Object / Domain Event *전술 패턴*
- *Modular Monolith 부터 *시작, *팀 분리 시 *서비스 추출*
- *Spring Modulith 의 *모듈 *경계 자동 검증*
```

이게 *2026 년 *시니어 *백엔드의 *현대적 표준*.

### 2.5 *과거 *3 시대의 *공통 *교훈*

1. **'기술이 *바뀌어도 *근본 *문제는 *같다*''** — *''*복잡한 *비즈니스를 *어떻게 *구조화""*
2. **''*유행 따라 *바꾸면 *손해*''** — *''*Anemic → MSA → Modular Monolith''* 의 *되돌이 *고통*
3. **''*도메인 이해 *없이 *기술만 *바꾸면 *같은 *진흙공''*** — *''*MSA 진흙공""*도 *진흙공*

---

## 3. *표준의 *3 가지 *축*

복잡 도메인을 *책임지는 *팀 표준* 의 *3 축*:

```
[축 1] 정합성 — *도메인 규칙이 *위반 *불가능한 *구조*
        ├─ Aggregate 경계
        ├─ Invariant 강제
        ├─ Domain Event
        └─ 트랜잭션 경계

[축 2] 확장성 — *변경 / 신기능이 *예측 가능한 *구조*
        ├─ Hexagonal Port / Adapter
        ├─ 패키지 구조 표준
        ├─ ArchUnit 자동 검증
        └─ Module 추출 가능성

[축 3] 일관성 — *팀 어휘와 *문화*
        ├─ 명명 컨벤션
        ├─ 코드 리뷰 가이드
        ├─ ADR (의사결정 기록)
        └─ 점진적 개선 패턴
```

---

## 4. *축 1 — *정합성을 *책임지는 *구조*

### 4.1 *Aggregate — *''*일관성의 *섬''*

```java
// 정합성 *책임을 *지는 *Order Aggregate*

public class Order {  // Aggregate Root
    private final OrderId id;
    private final List<OrderItem> items;
    private OrderStatus status;
    private Money totalAmount;

    // *생성자 *통제 — *불변식 *강제*
    public static Order place(OrderCommand cmd) {
        validateItems(cmd.items());      // *항상 *최소 1 개*
        var totalAmount = Money.sumOf(cmd.items());
        validateTotal(totalAmount);      // *항상 *양수*
        return new Order(...);
    }

    // *상태 *변경의 *유일한 *통로*
    public Order cancel(CancelReason reason) {
        if (status != OrderStatus.PAID && status != OrderStatus.READY) {
            throw new InvalidOrderStateException(
                "주문 상태 " + status + " 는 *취소 불가");
        }
        var events = List.of(new OrderCanceledEvent(id, reason));
        return new Order(id, items, OrderStatus.CANCELED, totalAmount, events);
    }

    // *비즈니스 *행동이 *Aggregate 안에*
    public Order applyDiscount(Discount discount) {
        if (status != OrderStatus.PENDING) {
            throw new InvalidOrderStateException("할인은 *결제 전에만");
        }
        // ...
    }
}
```

> **표준 규칙 1**: ***''*Aggregate 의 *상태 변경은 *Aggregate 의 *메서드를 *통해서만""***. *직접 *setter / setStatus()는 *''*표준 위반""*.

### 4.2 *Invariant — *''*절대 깨지지 *않는 규칙''*

도메인의 *불변식* 을 *''*문서로""* 가 *아니라 *''*코드로""* 강제한다.

```java
public class Money {
    private final BigDecimal amount;
    private final Currency currency;

    public Money(BigDecimal amount, Currency currency) {
        if (amount == null || currency == null)
            throw new IllegalArgumentException("amount/currency null *불가");
        if (amount.scale() > 2)
            throw new IllegalArgumentException("Money 는 *소수점 2 자리까지");
        this.amount = amount;
        this.currency = currency;
    }

    public Money add(Money other) {
        if (!currency.equals(other.currency))
            throw new IllegalArgumentException("통화 *다른 Money *더할 수 없음");
        return new Money(amount.add(other.amount), currency);
    }
    // ... immutable + invariant
}
```

> **표준 규칙 2**: ***''*Value Object 는 *생성자에서 *invariant 검증 + immutable""***.

### 4.3 *Domain Event — *''*상태 *변경을 *공식 *기록""*

```java
public sealed interface OrderEvent permits
    OrderPlacedEvent, OrderPaidEvent, OrderCanceledEvent, OrderShippedEvent {

    OrderId orderId();
    Instant occurredAt();
}

public record OrderPaidEvent(
    OrderId orderId,
    Money amount,
    Instant occurredAt
) implements OrderEvent {}
```

```java
// Aggregate 가 *Event 발생을 *기록*
public class Order {
    private final List<DomainEvent> uncommittedEvents = new ArrayList<>();

    public Order pay(Payment payment) {
        // ... 비즈니스 로직
        uncommittedEvents.add(new OrderPaidEvent(...));
        return this;
    }
}

// Application Service 가 *Event 발행*
@Service
public class PayOrderService {
    @Transactional
    public void pay(OrderId id, PaymentCommand cmd) {
        var order = repo.findById(id).orElseThrow();
        order.pay(cmd);
        repo.save(order);

        // *Spring Application Event (모듈러 모놀리식)
        order.getUncommittedEvents().forEach(eventPublisher::publishEvent);

        // *또는 *Outbox (MSA / 다른 서비스 동기화)
        order.getUncommittedEvents().forEach(outboxRepo::save);
    }
}
```

> **표준 규칙 3**: ***''*Aggregate 의 *상태 변경 = *Domain Event 발행""***. *''*조용한 변경""* 금지.

### 4.4 *트랜잭션 *경계의 *원칙*

```java
// ✅ 표준 — *Aggregate 1 개 = *트랜잭션 1 개*
@Transactional
public void cancel(OrderId id) {
    var order = orderRepo.findById(id).orElseThrow();
    order.cancel();
    orderRepo.save(order);
}

// ❌ 안티 — *여러 Aggregate 한 *트랜잭션*
@Transactional
public void payAndReserveInventory(OrderId orderId) {
    var order = orderRepo.findById(orderId);
    order.pay();
    orderRepo.save(order);

    var inventory = inventoryRepo.findFor(order);   // ← *다른 Aggregate*
    inventory.reserve(order);
    inventoryRepo.save(inventory);
    // *Lock 광범위, *경합 ↑, *확장성 ↓*
}

// ✅ 표준 — *각 Aggregate *별 *트랜잭션 + *Event*
@Transactional
public void pay(OrderId orderId) {
    var order = orderRepo.findById(orderId);
    order.pay();
    orderRepo.save(order);
    // OrderPaidEvent 발행 → Inventory 모듈이 *별도 트랜잭션에서 *처리*
}
```

> **표준 규칙 4**: ***''*1 트랜잭션 = *1 Aggregate. *여러 Aggregate 동기화는 *Event 로""***.

### 4.5 *''*정합성 표준""* 의 *체크리스트*

- [ ] *Aggregate Root 가 *명확히 *식별 됨*
- [ ] *상태 변경이 *항상 *Aggregate 메서드 *통과*
- [ ] *Invariant 가 *생성자 / setter 에서 *강제*
- [ ] *Value Object 가 *Immutable*
- [ ] *Domain Event 가 *모든 *비즈니스 *상태 변경에 *발행*
- [ ] *1 트랜잭션 = *1 Aggregate*

---

## 5. *축 2 — *확장성을 *책임지는 *구조*

### 5.1 *Hexagonal *패키지 *표준*

```
com.lemuel.shop.order/                        ← Module
  │
  ├─ domain/                                  ← *가장 *안쪽*
  │   ├─ Order.java                           (Aggregate Root)
  │   ├─ OrderId.java                         (Value Object)
  │   ├─ OrderItem.java
  │   ├─ OrderStatus.java                     (Enum)
  │   ├─ Money.java                           (Value Object)
  │   └─ event/
  │       ├─ OrderPlacedEvent.java
  │       ├─ OrderPaidEvent.java
  │       └─ OrderCanceledEvent.java
  │
  ├─ application/                             ← Use Case
  │   ├─ port/
  │   │   ├─ in/                              ← *Primary Port*
  │   │   │   ├─ PlaceOrderUseCase.java
  │   │   │   ├─ CancelOrderUseCase.java
  │   │   │   └─ GetOrderQuery.java
  │   │   └─ out/                             ← *Secondary Port*
  │   │       ├─ OrderRepository.java
  │   │       ├─ PaymentGateway.java
  │   │       └─ NotificationSender.java
  │   └─ service/                             ← Use Case 구현
  │       ├─ PlaceOrderService.java
  │       ├─ CancelOrderService.java
  │       └─ GetOrderQueryService.java
  │
  └─ adapter/                                 ← *가장 *바깥쪽*
      ├─ in/
      │   ├─ web/
      │   │   ├─ OrderController.java
      │   │   └─ dto/
      │   │       ├─ PlaceOrderRequest.java
      │   │       └─ OrderResponse.java
      │   └─ messaging/
      │       └─ OrderEventListener.java
      └─ out/
          ├─ persistence/
          │   ├─ JpaOrderRepository.java      (implements OrderRepository)
          │   ├─ OrderJpaEntity.java
          │   └─ OrderPersistenceMapper.java
          ├─ payment/
          │   └─ StripePaymentGateway.java
          └─ notification/
              └─ SesNotificationSender.java
```

### 5.2 *ArchUnit — *''*표준을 *컴파일러처럼 *강제""*

```java
@AnalyzeClasses(packages = "com.lemuel.shop")
class ArchitectureTest {

    @ArchTest
    static final ArchRule domain_은_프레임워크_모름 =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "org.springframework..",
                "jakarta.persistence..",
                "..adapter..",
                "..application.."
            );

    @ArchTest
    static final ArchRule application_은_adapter_모름 =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAPackage("..adapter..");

    @ArchTest
    static final ArchRule 의존성은_안쪽으로만 =
        layeredArchitecture().consideringAllDependencies()
            .layer("Domain").definedBy("..domain..")
            .layer("Application").definedBy("..application..")
            .layer("Adapter").definedBy("..adapter..")
            .whereLayer("Domain").mayNotAccessAnyLayer()
            .whereLayer("Application").mayOnlyAccessLayers("Domain")
            .whereLayer("Adapter").mayOnlyAccessLayers("Application", "Domain");

    @ArchTest
    static final ArchRule UseCase_는_인터페이스 =
        classes().that().haveSimpleNameEndingWith("UseCase")
            .should().beInterfaces()
            .andShould().resideInAPackage("..application.port.in..");

    @ArchTest
    static final ArchRule Adapter_는_Port_구현 =
        classes().that().resideInAPackage("..adapter.out.persistence..")
            .and().areAnnotatedWith(Repository.class)
            .should().implement(JavaClass.Predicates.resideInAPackage("..application.port.out.."));
}
```

> **표준 규칙 5**: ***''*ArchUnit 룰을 *CI 에 *통합 — *위반 PR 거절""***.

### 5.3 *''*모듈 간 *통신은 *Application Event 또는 *Port""*

```java
// ✅ 표준 — *Application Event 로 *모듈 간 *느슨한 *결합*
@Component
public class OrderEventHandler {

    @ApplicationModuleListener  // Spring Modulith
    public void on(OrderPaidEvent event) {
        // *inventory 모듈이 *order 모듈을 *직접 *호출하지 *않음*
        // *event 만 *듣고 *반응*
    }
}

// ❌ 안티 — *직접 *다른 모듈 *서비스 *호출*
@Service
public class PayOrderService {
    private final InventoryService inventoryService;  // ← *모듈 *경계 *위반*

    @Transactional
    public void pay(OrderId id) {
        // ...
        inventoryService.reserve(...);  // ← *결합 *재앙*
    }
}
```

### 5.4 *Spring Modulith — *''*모듈러 *모놀리식의 *표준""*

```java
// src/main/java/com/lemuel/shop/order/package-info.java
@ApplicationModule(
    displayName = "Order",
    allowedDependencies = {"shared::events", "user"}  // 명시적 의존
)
package com.lemuel.shop.order;

import org.springframework.modulith.ApplicationModule;
```

Spring Modulith 가 *''*다른 모듈 *직접 호출 = *테스트 *실패""* 로 *강제*. *''*신입이 *모듈 경계 *깨려 하면 *PR 못 *통과""*.

### 5.5 *''*확장성 표준""* 의 *체크리스트*

- [ ] *패키지 구조 *3 계층 (domain / application / adapter)*
- [ ] *Port 가 *인터페이스, *Adapter 가 *구현*
- [ ] *ArchUnit 룰 *최소 *5 개 *적용*
- [ ] *모듈 간 *통신 = *Event 또는 *명시적 *Port*
- [ ] *Spring Modulith 또는 *동급 *모듈 검증*

---

## 6. *축 3 — *팀의 *일관된 *어휘와 *문화*

### 6.1 *명명 표준*

```
[Primary Port]
  - *UseCase / Query 로 *끝남*
  - 예: PlaceOrderUseCase, GetOrderQuery

[Secondary Port]
  - *Repository / Gateway / Sender / Client 로 *끝남*
  - 예: OrderRepository, PaymentGateway

[Adapter]
  - *기술 + 역할 *명명*
  - 예: JpaOrderRepository, StripePaymentGateway, RestUserClient

[Domain Entity]
  - *비즈니스 명사*
  - 예: Order, Customer, Product

[Value Object]
  - *비즈니스 명사*
  - 예: Money, Address, OrderId

[Domain Event]
  - *과거 시제*
  - 예: OrderPlacedEvent, PaymentCompletedEvent
```

> **표준 규칙 6**: ***''*명명 표준은 *컨벤션 *문서 + IDE 템플릿 + 코드 리뷰로 *유지""***.

### 6.2 *코드 리뷰 *가이드*

표준에 *기반한 *체크리스트* 가 *리뷰어 / 작성자 *모두에게 *기준 제공*:

```markdown
## 표준 준수 체크리스트

### Domain
- [ ] Aggregate Root 가 *명확*
- [ ] 상태 변경이 *Aggregate 메서드 *통과
- [ ] Domain Event 가 *상태 변경에 *발행
- [ ] Value Object 가 *Immutable + Invariant

### Application
- [ ] UseCase 인터페이스가 *Primary Port 에 *위치
- [ ] @Transactional 이 *Application Service 에 *위치 (Domain 에 X)
- [ ] 외부 시스템 호출이 *Secondary Port 통해서

### Adapter
- [ ] Controller 가 *얇은 변환 + UseCase 호출 만
- [ ] JPA Entity 와 Domain Entity 분리
- [ ] HTTP 응답 DTO 가 *Domain 노출 X

### 표준 어휘
- [ ] 명명이 *컨벤션 준수
- [ ] 패키지 *위치가 *정확

### Test
- [ ] Domain 단위 테스트 (Spring 없이)
- [ ] UseCase 단위 테스트 (Port mock)
- [ ] Adapter 통합 테스트 (Testcontainers)
```

### 6.3 *ADR (Architecture Decision Record) — *''*결정의 *역사""*

```markdown
# ADR-007: Order Aggregate 의 *재고 처리 *분리

## 일자
2026-05-29

## 컨텍스트
초기 *Order Aggregate 안에 *재고 차감 *로직 *포함.
*문제:
- 재고 부족 시 *주문 자체 *생성 실패 → *비즈니스 요구 (주문은 *생성, *재고 부족 *시 *대기) 위반
- Order 와 Inventory 가 *같은 *트랜잭션 → *Lock 광범위

## 결정
- Order Aggregate 는 *주문 의도만 표현
- 재고 차감은 *Inventory Aggregate 의 *책임
- OrderPlacedEvent 듣고 *Inventory 가 *처리
- 재고 부족 시 *InventoryReservationFailedEvent → Order 가 *상태 *전환

## 결과
- 트랜잭션 *경계 *명확
- 두 Aggregate *독립 *확장 가능
- 재시도 / 보상 로직이 *Event 흐름 *위에서

## 회고
- Eventual consistency *도입 *결정의 *시작
- UI / 고객 응대 팀에 *''*주문 *완료 ≠ *재고 확보""* 교육 필요
```

> **표준 규칙 7**: ***''*중요한 *기술 결정 = *ADR. *6 개월 후 *''*왜 이렇게 됐지""* 의 *답이 *존재""***.

### 6.4 *점진적 *개선 *패턴*

표준은 *''*처음부터 *완벽""* 일 수 *없다*. *진화*:

```
[Phase 1] 핵심 표준 *3 ~ 5 개 *정의 + ArchUnit *룰 *2 개*
[Phase 2] *6 개월 *적용 후 *효과 측정*
[Phase 3] *주니어 의견 *수렴 + 표준 *조정*
[Phase 4] *추가 규칙 *5 개 + ArchUnit *룰 *5 개*
[Phase 5] *연 1 회 *표준 *리뷰 + 개정*
```

*''*완벽한 표준 *처음부터 *시도""* = *''*아무도 *읽지 않는 *200 페이지 *문서""*.

---

## 7. *''*표준 *위반 *시 *어떻게 *대응 할 것인가""*

표준이 *있어도 *어겨질 *수 있다*. *시니어의 *대응 *3 가지*:

### 7.1 *컴파일 / 테스트 *단계 *차단*

- **ArchUnit** — 의존성 *방향 위반*
- **Spring Modulith** — 모듈 *경계 위반*
- **Checkstyle / SpotBugs** — *명명, 코드 스타일*

*''*PR 이 *CI 통과 못 함 → *자동 *차단""*. *''*리뷰어가 *놓쳐도 *시스템이 *막음""*.

### 7.2 *PR 리뷰 *단계 *교정*

- *체크리스트 *기반 *리뷰*
- *''*왜 표준이 *이렇게 되었는가""* 를 *설명* (단순 *지적 X)
- *대안 *제시*

### 7.3 *지속적 *교육*

- *신입 *온보딩 *시 *표준 *세션*
- *분기 *1 회 *''*표준 *리뷰 *회의""*
- *''*표준 위반 *예시와 *수정""* 의 *내부 *위키*

---

## 8. *미래 — *''*2026 ~ 2030 의 *표준 *진화""*

### 8.1 *Spring Modulith 의 *전사 *표준화*

```
[현재] *Modular Monolith 의 *옵션*
[2027] *대부분의 *신규 *Spring Boot *프로젝트의 *기본*
[2030] *''*Modulith 모르면 *Spring 모름""*
```

### 8.2 *Virtual Thread 의 *전면 *적용*

- *''*기존 *동기 코드 *= *고성능""*
- *''*Reactive 의 *학습 비용 *피하면서 *성능 *확보""*
- *''*표준에 *Virtual Thread 적용 *전제""*

### 8.3 *Spring AI 의 *Domain 통합*

```java
@Service
public class OrderRecommendationService {
    private final ChatClient chatClient;
    private final OrderRepository orderRepo;

    public Recommendation recommend(CustomerId id) {
        var history = orderRepo.findHistory(id);
        return chatClient.prompt()
            .system("이커머스 추천 *AI. *제공된 *주문 *내역에 *없는 *상품 *추천 *금지""")
            .user("내역: {history}")
            .call()
            .entity(Recommendation.class);
    }
}
```

*''*AI 호출이 *Use Case 의 *일부 — *Port / Adapter 패턴으로 *추상화""*. *''*Domain 은 *AI 모름, *Application 만 *알게""*.

### 8.4 *데이터 *주권과 *Sovereign AI*

- *''*특정 *데이터는 *해외 *AI 서비스 *전송 *불가""* (GDPR, 국내 *공공)
- *''*Adapter 패턴으로 *AI 호출 *분리 → *''*해외 vs 국내 *서비스 *교체""*

### 8.5 *''*Code as *Documentation""* 의 *진화*

```
[전통] *별도 *문서 (Confluence, Notion)
[현재] *Javadoc + ADR + README
[미래] *AI 가 *코드 자체에서 *''*도메인 모델""* 을 *추출 / 시각화*
```

### 8.6 *표준의 *글로벌 *수렴*

- *''*한국의 *Spring + 헥사고날 *팀이 *전 세계 *수많은 *팀과 *같은 *패턴""*
- *''*GitHub 의 *공개 코드가 *그대로 *학습 자료*''
- *''*문서가 *영어 *기본""* — *2026 ~ 글로벌 *통합 가속*

---

## 9. *시니어가 *써내야 할 *''*표준 문서""* 의 *목차*

```markdown
# [회사명] 백엔드 *표준 *가이드 v1.0

## 1. 철학
   - 도메인 우선
   - 정합성과 확장성의 균형
   - 점진적 진화

## 2. 패키지 구조
   - 헥사고날 *3 계층*
   - 모듈 *분리 기준*

## 3. Domain Layer 표준
   - Aggregate 정의 기준
   - Value Object 사용 시점
   - Domain Event 발행 규칙
   - Invariant 강제 패턴

## 4. Application Layer 표준
   - Use Case 명명과 시그니처
   - @Transactional 사용 규칙
   - Port 정의 가이드

## 5. Adapter Layer 표준
   - JPA / Repository 패턴
   - HTTP Controller 패턴
   - Messaging Listener 패턴
   - 외부 시스템 통신 표준

## 6. 모듈 간 통신
   - Spring Modulith 활용
   - Application Event 패턴
   - MSA 추출 시 Outbox 패턴

## 7. 명명 컨벤션
   - 도메인 / 패키지 / 클래스 / 메서드 / 변수

## 8. 테스트 전략
   - Domain unit test (no Spring)
   - Use Case unit test (Mockito)
   - Adapter integration test (Testcontainers)
   - End-to-end test 기준

## 9. ArchUnit 룰
   - 적용된 룰 *전체 *목록 + 이유

## 10. 의사결정 기록 (ADR)
   - 누적된 ADR 의 *인덱스*

## 11. 점진적 개선
   - 표준 *위반 발견 시 *프로세스*
   - 표준 *제안 / 변경 *프로세스*

## 12. FAQ
   - 자주 묻는 *경계 케이스*
```

이 *12 절짜리 *문서* 가 *''*조직의 *기술 자산""*. *시니어가 *떠나도 *남는 *영구 자원*.

---

## 10. 정리 — *''*표준의 *3 가지 *진실""*

### 10.1 *3 가지 *진실*

> 1. ***''*표준 *없으면 *기술 자산이 *축적되지 *않고 *부채만 *축적 된다.*''*
> 2. ***''*표준은 *''*독재""* 가 *아니라 *''*집단 어휘""*. *팀이 *같은 문제에 *같은 답을 *내는 *공통 *언어.*'''*
> 3. ***''*컴파일러처럼 *강제하는 표준만 *지켜진다. *문서로만 *있는 *표준은 *읽히지 않는다.*'''*

### 10.2 *시니어의 *5 가지 *책임*

1. **표준 *정의*** — Hexagonal + Spring + DDD 의 *현장 적용 표준*
2. **자동 *강제*** — ArchUnit / Spring Modulith / CI
3. **교육과 *문화*** — 신입 *온보딩, 코드 리뷰, ADR
4. **점진적 *진화*** — 분기별 *리뷰, 표준 *개정
5. **미래 *준비*** — Virtual Thread, Spring AI, 데이터 주권

### 10.3 *과거 *교훈 + 미래 *방향* 의 *통합*

```
[과거] Anemic → MSA 광기 → Modular Monolith *재발견
[현재] Hexagonal + DDD + Spring Modulith *표준화
[미래] Virtual Thread + Spring AI + Sovereign AI 의 *추가 표준
```

**한 줄로**: *''*표준은 *우리 *팀의 *''*5 년 후 *코드 *품질""* 의 *유일한 *예측 변수*''.

> **마지막 한 문장**:
>
> *''*Spring 이 *바뀌고, *프레임워크가 *진화하고, *AI 가 *코드 짜는 *시대가 *와도, *''*복잡 *도메인을 *어떻게 *구조화 할 것인가""* 의 *질문은 *남는다. *그 답을 *팀의 *표준으로 *써내고 *유지하는 *것이 *시니어의 *진짜 자산이고, *그 *자산은 *어떤 *기술 변화에도 *살아남는다''*.

---

## 더 읽으면 좋은 자료

- *Eric Evans*, **Domain-Driven Design** (2003) — *원전*
- *Vaughn Vernon*, **Implementing Domain-Driven Design** (2013) — *실무 교과서*
- *Vlad Khononov*, **Learning Domain-Driven Design** (2021) — *현대적 정리*
- *Tom Hombergs*, **Get Your Hands Dirty on Clean Architecture** (2019) — *Spring 적용*
- *Alistair Cockburn*, **Hexagonal architecture** (2005 글)
- *Robert C. Martin*, **Clean Architecture** (2017)
- *Spring Modulith 공식 문서*
- *ArchUnit 공식 문서* + *Practical examples*
- *Martin Fowler*, **Anemic Domain Model** (2003)
- *Will Larson*, **Staff Engineer** + **Elegant Puzzle**
- *네이버 D2, 카카오 Tech, 우아한기술블로그* — *국내 *표준화 사례*
