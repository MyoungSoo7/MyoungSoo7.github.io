---
layout: post
title: "헥사고날과 클린 아키텍처 — *''도메인이 *프레임워크* 를 모른다''* 라는 한 문장"
date: 2026-05-29 01:10:00 +0900
categories: [architecture, ddd, backend]
tags: [hexagonal, clean-architecture, ports-and-adapters, onion-architecture, ddd, dependency-inversion, spring-boot]
---

> *''내 도메인이 *Spring* 을 import 하고 있다''*. 이 한 줄에서 *''이 코드는 *프레임워크 종속* 이다''* 라는 진단이 시작된다. 5 년 뒤 *Spring 4 → Spring 7* 으로 이관하려고 보니 *모든 도메인 클래스가 *프레임워크 메이저 버전에 묶여 있는 것* 을 발견* — 이게 *''Big Ball of Mud''* 가 만들어지는 *전형적 시나리오* 다.
>
> Alistair Cockburn 의 **헥사고날 아키텍처** (2005) 와 Robert C. Martin 의 **클린 아키텍처** (2012) 는 같은 문제에 대한 *두 가지 표현* 이다. *''도메인은 *세상* 을 모른다. *세상* 이 도메인을 *입양* 한다''*.

이 글은 헥사고날과 클린 아키텍처의 *역사적 출발* → *공통 원칙* → *세 자매 (헥사고날 / 클린 / 어니언) 의 차이* → *Spring 진영의 실무 적용* → *흔히 빠지는 함정* 의 순서로 풀어본다.

---

## 1. *왜* 도메인을 *분리* 해야 했나 — *진흙공* 의 역사

1999 년 Brian Foote 와 Joseph Yoder 가 발표한 논문 **Big Ball of Mud** 는 *''대부분의 production 시스템이 *결국* 진흙공이 된다''* 는 *불편한 진실* 을 정리했다.

전형적 패턴:
1. *프로토타입* 으로 시작 — UI 가 직접 DB 쿼리
2. *비즈니스 로직* 이 *Controller 에 침투*
3. *프레임워크 클래스를 *직접 상속* — 갈아탈 수 없음
4. *''여기 한 줄 더''* 가 *5 년 누적* — *수정이 *어디로 튈지 모름**

이 진흙공의 *공통 원인* 한 줄: *''비즈니스 로직이 *주변 기술* 과 *물리적으로 섞여 있다''*.

해법의 *방향* 도 한 줄: *''비즈니스를 *가운데* 놓고, 주변 기술을 *교체 가능* 하게 만들자''*.

이 *한 방향* 을 *서로 다른 이름과 메타포* 로 표현한 게 헥사고날 / 클린 / 어니언 *3 자매* 다.

---

## 2. *Hexagonal Architecture* (Alistair Cockburn, 2005) — *Ports and Adapters*

Cockburn 이 원래 붙인 이름은 *''Ports and Adapters''* 였다. *''Hexagonal''* 은 *그림이 *6 각형* 으로 그려져서 붙은 별명* 인데 이게 더 유명해졌다.

```
                    ┌─────────────────────┐
                    │   primary adapter   │
                    │   (REST Controller) │
                    └──────────┬──────────┘
                               │
                ┌──────────────▼──────────────┐
                │      ┌───────────────┐      │
                │      │               │      │
   secondary   │      │    DOMAIN     │      │   secondary
   adapter ────┼──────┤  (Pure Java)  ├──────┼──── adapter
   (Email)     │      │               │      │   (PostgreSQL)
                │      └───────────────┘      │
                │                              │
                └──────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │   primary adapter     │
                │   (Kafka Listener)    │
                └───────────────────────┘
```

### 2.1 핵심 용어 *3 개*

- **Domain** — 비즈니스 규칙 *그 자체*. *어떤 프레임워크도 모름*. *Pure Java/Kotlin*.
- **Port** — 도메인이 *''내가 *바깥* 과 *이런 식* 으로 대화한다''* 를 선언하는 **인터페이스**.
- **Adapter** — Port 의 *구체적 구현*. *프레임워크/DB/HTTP* 등 *기술 결정* 이 *여기* 에만 들어감.

### 2.2 *Port 의 두 방향* — *primary* vs *secondary*

이게 헥사고날의 *진짜 통찰* 이다.

- **Primary Port (driving port)** — *바깥이 도메인을 *부른다***
  - 예: `PlaceOrderUseCase`, `GetOrderQuery`
  - Adapter 예: REST Controller, GraphQL resolver, Kafka Listener
- **Secondary Port (driven port)** — *도메인이 *바깥을* 부른다***
  - 예: `OrderRepository`, `PaymentGateway`, `NotificationSender`
  - Adapter 예: JPA Repository, Stripe HTTP client, AWS SES client

이 *''방향성''* 덕분에 *''도메인은 *바깥의 *구현* 을 모름*''* 이 성립한다. *Port 만 알고*, *adapter 는 *DI 로 *주입* 됨**.

### 2.3 *왜 Cockburn 이 이 그림을 그렸나*

Cockburn 의 2005 년 원문은 *''Allow an application to equally be driven by users, programs, automated tests or batch scripts, and to be developed and tested in isolation from its eventual run-time devices and databases''* 로 시작한다.

핵심은 ***''같은 도메인 코드가 *4 가지 진입점* 으로 *동등하게 *호출될 수 있어야 한다''*** — REST, CLI, 테스트, 배치. 이 *''4 동등''* 이 *''포트와 어댑터''* 의 *진짜 의미* 다.

---

## 3. *Clean Architecture* (Robert C. Martin, 2012) — *동심원의 *4 계층*

Uncle Bob 의 클린 아키텍처는 2012 년 블로그 글로 처음 그려졌고, 2017 년 책 **Clean Architecture** 에서 정리됐다.

```
        ╭─────────────────────────────────────────╮
        │  Frameworks & Drivers                   │ ← Spring, JPA, AWS SDK
        │   ╭─────────────────────────────────╮   │
        │   │  Interface Adapters             │   │ ← Controller, Repository 구현
        │   │   ╭─────────────────────────╮   │   │
        │   │   │  Application Business   │   │   │ ← Use Cases (시나리오)
        │   │   │   ╭─────────────────╮   │   │   │
        │   │   │   │   Enterprise    │   │   │   │ ← Entities (핵심 비즈니스 규칙)
        │   │   │   │   Business      │   │   │   │
        │   │   │   ╰─────────────────╯   │   │   │
        │   │   ╰─────────────────────────╯   │   │
        │   ╰─────────────────────────────────╯   │
        ╰─────────────────────────────────────────╯

        의존성 방향: 바깥 → 안쪽 (한 방향)
```

### 3.1 *4 계층* 의 의미

- **Entities** — *기업 전체* 에 공통되는 *핵심 비즈니스 규칙*. *DB 가 없어도, UI 가 없어도, 살아 있는 규칙*.
- **Use Cases** — *''이 *애플리케이션* 에서 *어떻게* 쓰이는가''*. *시나리오*. 예: *''주문을 받아 결제하고 재고를 잡는다''*.
- **Interface Adapters** — *Use Cases 가 정의한 *port* 의 구현*. Controller, Repository 구현체, Presenter.
- **Frameworks & Drivers** — Spring, JPA, AWS SDK, Web Server — *''교체 가능한 인프라''*.

### 3.2 **Dependency Rule** — *''의존성은 *안쪽으로만*''*

> *''소스 코드 의존성은 *반드시* 안쪽 — 더 높은 수준의 정책 — 으로 향해야 한다.''*

이 한 줄이 클린 아키텍처의 *전부* 다. *Entities 는 *아무것도* 의존하지 않는다*. *Use Cases 는 Entities 만 의존*. *Adapters 는 Use Cases + Entities 만 의존*. *Frameworks 는 *전부* 의존하지만 *역방향은 없음*.

### 3.3 *''어떻게 *바깥 → 안* 의존성을 *뒤집을 것인가''*

도메인이 DB 를 호출해야 하는데, *''도메인이 *Repository 인터페이스* 를 *자기 영역* 에 정의''* 한다.

```java
// 안쪽 영역 — domain/use-case
package com.lemuel.order.application;

public interface OrderRepository {           // ← *Use Case 가 *정의*
    Optional<Order> findById(OrderId id);
    void save(Order order);
}

// 바깥 영역 — infrastructure/adapter
package com.lemuel.order.infrastructure.persistence;

@Repository
public class JpaOrderRepository implements OrderRepository {  // ← *바깥이 *구현*
    private final JpaOrderEntityRepository jpa;

    @Override
    public Optional<Order> findById(OrderId id) {
        return jpa.findById(id.value()).map(this::toDomain);
    }
}
```

*''인터페이스는 안쪽, 구현은 바깥쪽''* — 이게 **Dependency Inversion Principle (DIP)** 의 *실전 적용*. *''도메인이 *JPA* 를 import 하지 않는다''* 가 성립한다.

---

## 4. *3 자매의 차이* — 헥사고날 / 클린 / 어니언

| | **Hexagonal** (Cockburn, 2005) | **Onion** (Palermo, 2008) | **Clean** (Martin, 2012) |
|---|---|---|---|
| 주된 메타포 | 6 각형 + Port/Adapter | 양파 (껍질) | 동심원 4 겹 |
| 강조점 | *port 의 *방향성** (primary/secondary) | *infra → 도메인* 일방향 | *4 계층 명시* + Dependency Rule |
| 계층 수 | *''경계 하나''* 만 강조 | *''껍질 여러 겹''* (수 명시 안 함) | *''4 겹''* 명시 |
| 정신적 친척 | DDD, Ports & Adapters | DIP 의 *조직 패턴* | SOLID 의 *아키텍처화* |

**한 줄로**: *셋 다 같은 것을 말한다*. *''도메인을 중심에 놓고, 의존성을 *안쪽으로* 향하게 한다''*. *차이는 메타포와 계층 명시 방식뿐*.

### 4.1 *그래서 *어느 이름* 을 쓰나*

실무에서는 **''헥사고날 아키텍처''** 가 *가장 자주 쓰이는 이름* 이다. 이유:

1. *Port / Adapter 라는 *구체적 용어** 가 *코드 패키지명* 으로 *그대로* 쓸 수 있다 (`application/port/in`, `application/port/out`, `adapter/in/web`, `adapter/out/persistence`)
2. *클린 아키텍처는 *4 계층* 이 *너무 정형화* 돼서 *작은 프로젝트* 엔 *과함*
3. *어니언은 *그림은 예쁘지만* *port 의 방향성을 *명시* 안 함*

> *2026 년 자바/스프링 진영의 *기본값** 은 *''Hexagonal + DDD 의 *전술 패턴* (Aggregate, Value Object, Domain Event)''* 의 조합.

---

## 5. *Spring Boot 에서의 *실전 적용**

### 5.1 *패키지 구조 — *6 면체* 의 *물리적 표현**

```
com.lemuel.order
├── domain/                          ← 가장 안쪽 (pure Java)
│   ├── Order.java                   ← Aggregate Root
│   ├── OrderId.java                 ← Value Object
│   ├── OrderItem.java
│   └── OrderStatus.java
│
├── application/                     ← Use Case 계층
│   ├── port/
│   │   ├── in/                      ← *Primary Port*
│   │   │   ├── PlaceOrderUseCase.java
│   │   │   └── GetOrderQuery.java
│   │   └── out/                     ← *Secondary Port*
│   │       ├── OrderRepository.java
│   │       ├── PaymentGateway.java
│   │       └── NotificationSender.java
│   └── service/                     ← Use Case 구현
│       └── OrderService.java         (implements PlaceOrderUseCase)
│
└── adapter/                         ← 가장 바깥쪽 (프레임워크)
    ├── in/
    │   ├── web/
    │   │   └── OrderController.java  (uses PlaceOrderUseCase)
    │   └── messaging/
    │       └── OrderEventListener.java
    └── out/
        ├── persistence/
        │   ├── JpaOrderRepository.java   (implements OrderRepository)
        │   └── OrderJpaEntity.java       ← JPA 전용 — 도메인 ≠ 이거
        ├── payment/
        │   └── StripePaymentGateway.java (implements PaymentGateway)
        └── notification/
            └── SesNotificationSender.java
```

### 5.2 *의존성 방향 — *ArchUnit* 으로 *컴파일러처럼* 강제*

*''좋은 의도''* 만으로는 시간이 지나면 *반드시 깨진다*. **ArchUnit** 으로 *테스트 단계에서 차단*.

```java
@AnalyzeClasses(packages = "com.lemuel.order")
class HexagonalArchitectureTest {

    @ArchTest
    static final ArchRule 도메인은_Spring_을_모른다 =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "org.springframework..",
                "jakarta.persistence..",
                "..adapter.."
            );

    @ArchTest
    static final ArchRule application_은_adapter_를_모른다 =
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
}
```

*''리뷰가 놓쳐도 *CI 가 빨강* ''*. *시간의 진흙공화* 를 *물리적으로* 막는다.

### 5.3 *Domain Entity vs JPA Entity — *분리* 인가 *통합* 인가*

가장 자주 나오는 논쟁:

**Option A — *완전 분리***
```java
// domain/Order.java — pure Java
public class Order {
    private final OrderId id;
    private final List<OrderItem> items;
    public void cancel() { ... }   // 비즈니스 행동
}

// adapter/out/persistence/OrderJpaEntity.java
@Entity
@Table(name = "orders")
public class OrderJpaEntity {
    @Id private String id;
    // ... JPA 어노테이션 *전용*
}

// Mapper
class OrderPersistenceMapper {
    Order toDomain(OrderJpaEntity entity) { ... }
    OrderJpaEntity toEntity(Order domain) { ... }
}
```

- *장점* — 도메인 *완전 pure*. ORM 교체 가능
- *단점* — *mapping 코드 폭증*

**Option B — *통합 (한 클래스가 둘 다)***
```java
@Entity
public class Order {
    @Id private String id;
    // JPA + 비즈니스 행동이 *같은 클래스*
    public void cancel() { ... }
}
```

- *장점* — *간결*
- *단점* — *도메인이 JPA 종속*. *진짜 헥사고날 아님*

> **현장의 합의** — *''작은 프로젝트는 통합, 큰 프로젝트는 분리''*. *''엔티티가 *복잡한 비즈니스 행동을 갖는 시점* 부터 분리''*. 즉 *처음부터 분리할 필요 없음*, *진짜 필요해질 때 *추출* 가능*.

---

## 6. *흔히 빠지는 함정 *5 개**

### 6.1 *''너무 많은 mapping''* — *3 단 변환 지옥*

```
[Request DTO] → [Command] → [Domain] → [JPA Entity] → [DB]
[DB] → [JPA Entity] → [Domain] → [Response DTO]
```

이 *4 단 변환* 이 *매 endpoint 마다* 반복되면 *''Mapper 가 비즈니스 로직보다 많은 코드''* 가 된다. 해법:

- **MapStruct** — *컴파일 타임 코드 생성* 으로 *손코딩 제로*
- *''DTO ↔ Domain''* 만 명시적, *''Domain ↔ JPA''* 는 *Option B (통합)* 고려

### 6.2 *''Anemic Domain Model''* — *도메인이 *데이터만 들고* 행동이 없음*

```java
// 안티 패턴 — 도메인이 *getter / setter 만*
public class Order {
    private OrderStatus status;
    public OrderStatus getStatus() { return status; }
    public void setStatus(OrderStatus s) { this.status = s; }
}

// 비즈니스 로직이 *Service 에 다 있음*
@Service
class OrderService {
    public void cancel(OrderId id) {
        var order = repo.findById(id);
        if (order.getStatus() == PAID) {
            order.setStatus(REFUNDED);    // ← *도메인 규칙이 *서비스에 침투*
        }
    }
}
```

Martin Fowler 가 *''Anemic Domain Model''* 이라고 부르며 *''DDD 의 안티 패턴''* 으로 명시.

**해법** — *도메인이 *자기 규칙* 을 *자기가 안다***:
```java
public class Order {
    public Order cancel() {
        if (status != PAID) throw new InvalidOrderStateException();
        return new Order(..., REFUNDED);
    }
}
```

### 6.3 *''작은 프로젝트에 *과한 적용*''*

CRUD 5 개짜리 *프로토타입* 에 *Port 4 개 + Adapter 4 개 + Mapper 8 개* 를 만들면 *''아키텍처 자위''*. *''*복잡도가 *비즈니스 규칙에서 *나오기* 시작할 때* 만 적용''* 이 *진짜 답*.

### 6.4 *''Port 가 *너무 많아짐*''*

매 외부 호출마다 *Port 인터페이스 하나* 가 *기계적으로* 생기면 *인터페이스 폭발*. *''*하나의 *비즈니스 의미* 단위로 묶기''*:

```java
// ❌ Port 가 *너무 잘게*
interface CreateOrderPort { ... }
interface UpdateOrderPort { ... }
interface DeleteOrderPort { ... }
interface FindOrderPort { ... }

// ✅ *비즈니스 의미* 로 묶기
interface OrderRepository {
    void save(Order order);
    Optional<Order> findById(OrderId id);
    // ...
}
```

### 6.5 *''의존성 방향을 *런타임 DI* 만으로 *해결한 줄 안다*''*

*''Spring 이 *알아서 주입* 하니까 헥사고날이지 뭐''* — *틀린 가정*. *Spring 의 DI* 는 *''런타임 객체 그래프''* 만 풀어준다. *''컴파일 타임 의존성 (`import` 라인)''* 은 *직접 강제* 해야 한다 — **ArchUnit 이 그래서 필수**.

---

## 7. *실전 — Spring Boot 헥사고날 *최소 구성 예시**

*''책 보기 싫고 *돌아가는 게 보고 싶다*''* 라면:

```java
// 1) Domain (pure Java)
package com.lemuel.order.domain;

public record Order(OrderId id, Money amount, OrderStatus status) {
    public Order cancel() {
        if (status != OrderStatus.PAID)
            throw new IllegalStateException("not paid");
        return new Order(id, amount, OrderStatus.CANCELED);
    }
}

// 2) Primary Port
package com.lemuel.order.application.port.in;

public interface CancelOrderUseCase {
    void cancel(OrderId id);
}

// 3) Secondary Port
package com.lemuel.order.application.port.out;

public interface OrderRepository {
    Optional<Order> findById(OrderId id);
    void save(Order order);
}

// 4) Use Case 구현
package com.lemuel.order.application.service;

@Service
@RequiredArgsConstructor
public class CancelOrderService implements CancelOrderUseCase {
    private final OrderRepository repository;

    @Transactional
    public void cancel(OrderId id) {
        var order = repository.findById(id)
            .orElseThrow(() -> new OrderNotFoundException(id));
        repository.save(order.cancel());
    }
}

// 5) Primary Adapter (Web)
package com.lemuel.order.adapter.in.web;

@RestController
@RequestMapping("/orders")
@RequiredArgsConstructor
public class OrderController {
    private final CancelOrderUseCase cancelOrderUseCase;

    @PostMapping("/{id}/cancel")
    public ResponseEntity<Void> cancel(@PathVariable String id) {
        cancelOrderUseCase.cancel(OrderId.of(id));
        return ResponseEntity.noContent().build();
    }
}

// 6) Secondary Adapter (JPA)
package com.lemuel.order.adapter.out.persistence;

@Repository
@RequiredArgsConstructor
class JpaOrderRepository implements OrderRepository {
    private final OrderJpaEntityRepository jpa;
    private final OrderPersistenceMapper mapper;

    public Optional<Order> findById(OrderId id) {
        return jpa.findById(id.value()).map(mapper::toDomain);
    }
    public void save(Order order) {
        jpa.save(mapper.toEntity(order));
    }
}
```

이 *6 개 클래스* 가 헥사고날의 *''기본 한 사이클''*. 새 기능 추가 = *같은 6 개 클래스 패턴 반복*.

---

## 8. 정리 — *''도메인이 *프레임워크* 를 모른다''*

12 ~ 20 년 된 *3 자매의 한 줄 약속*:

> ***''비즈니스 규칙은 *세상* 을 모르고, *세상* 이 비즈니스를 *입양* 한다''***

이 약속이 지켜지면:
- **Spring 4 → 7 마이그레이션** 시 *도메인 코드 0 줄 변경*
- **PostgreSQL → DynamoDB 변경** 시 *adapter 만 교체*
- **REST → gRPC 추가** 시 *primary adapter 하나 추가*
- **단위 테스트** 시 *Spring context 안 띄움* — *millisecond 단위*

깨지면:
- *프레임워크 메이저 업그레이드 = *수개월*
- *''도메인 규칙이 *어디 있는지* 모름''* — *Controller, Service, Entity 에 *흩어짐**
- *테스트가 *느림* + *깨지기 쉬움**

> **2026 년 자바/스프링 진영의 *권장 출발점***:
>
> 1. **헥사고날** 패키지 구조 (domain / application / adapter)
> 2. **ArchUnit** 으로 의존성 방향 *컴파일러처럼* 강제
> 3. **DDD 전술 패턴** (Aggregate / Value Object / Domain Event) 함께
> 4. **작게 시작** — *복잡도가 *비즈니스에서* 나오기 시작할 때만* 분리 강화

*''완벽한 아키텍처''* 는 없다. *''오래 살아남는 아키텍처''* 는 *''비즈니스가 *주인공* 인 아키텍처''* 다. 헥사고날과 클린은 *그 한 가지 진실* 을 *서로 다른 그림* 으로 그린 것일 뿐이다.

---

## 더 읽으면 좋은 자료

- Alistair Cockburn, **Hexagonal architecture** (2005) — *원전*
- Robert C. Martin, **Clean Architecture** (2017) — *책 형태로 정리*
- Jeffrey Palermo, **The Onion Architecture** (2008 블로그) — *세 번째 자매*
- Vaughn Vernon, **Implementing Domain-Driven Design** (2013) — *DDD 의 실무 교과서*
- Tom Hombergs, **Get Your Hands Dirty on Clean Architecture** (2019) — *Spring Boot 로 *그대로* 따라 할 수 있는 유일한 책*
- Eric Evans, **Domain-Driven Design** (2003) — *모든 시작*
- Martin Fowler, **Anemic Domain Model** (2003) — *짧은 글이지만 *고전*
- ArchUnit 공식 문서 — *''Layered Architecture Rules''* 절
- Spring Modulith — *''*모듈형 모놀리식* 에서 헥사고날 *경계 강제*''*
