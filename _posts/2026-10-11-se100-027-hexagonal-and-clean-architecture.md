---
layout: post
title: "[SE100 #027] 헥사고날·클린 아키텍처 — 포트와 어댑터"
date: 2026-10-11 16:58:11 +0900
categories: [software-engineering]
tags: [se100, software-architecture, hexagonal-architecture, clean-architecture, ports-and-adapters, dependency-rule]
---

소프트웨어 공학 100 주제 시리즈의 27번째 글이다. (카테고리: 설계와 아키텍처)

## 한 줄 요약

헥사고날(포트와 어댑터), 어니언, 클린 아키텍처는 이름과 그림이 다르지만 같은 규칙 하나를 공유한다. **업무 규칙은 바깥(UI, DB, 프레임워크, 외부 API)을 모르고, 소스 코드 의존은 항상 안쪽을 향한다.** 바깥과의 대화는 안쪽이 정의한 포트(인터페이스)를 통해서만, 기술별 어댑터가 맡는다.

## 왜 필요한가

전통적인 레이어드 아키텍처([레이어드 아키텍처]({% post_url 2026-10-10-cs300-197-layered-architecture %}))는 표현 → 비즈니스 → 데이터 접근 순으로 아래를 향해 의존한다. Jeffrey Palermo 는 [The Onion Architecture](https://jeffreypalermo.com/2008/07/the-onion-architecture-part-1/) (2008) 에서 이 구조의 가장 흔한 문제를 지적한다. **UI 와 업무 로직이 데이터 접근에 결합된다.** 이행적 의존도 의존이다. 업무 로직은 데이터 접근 없이는 동작하지 않고, UI 는 업무 로직 없이는 동작하지 않는다.

결과는 이렇다.

- 업무 규칙을 테스트하려면 DB 가 떠 있어야 한다.
- ORM 을 바꾸거나 DB 를 옮기면 업무 로직 클래스가 줄줄이 바뀐다.
- 같은 업무 기능을 REST, 배치, 메시지 소비자에서 호출하려면 각 입구마다 로직이 복제된다.

Alistair Cockburn 은 [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) 원문에서 이 문제를 "업무 로직이 사용자 인터페이스 코드에 스며들고, 외부 DB 나 서비스에 묶이는 것" 으로 요약하고, 그 결과 자동 회귀 테스트도, 사람 대신 프로그램이 시스템을 구동하는 것도 어려워진다고 말한다.

## 핵심 개념

### 헥사고날: 포트와 어댑터 (Cockburn, 2005)

원문에 표기된 날짜는 2005-09-04 이고, 패턴 이름은 "Ports and Adapters", 별칭이 "Hexagonal" 이다. 의도(Intent)는 이렇다.

> 애플리케이션이 사용자, 프로그램, 자동 테스트, 배치 스크립트에 의해 똑같이 구동될 수 있게 하고, 최종 런타임 장치와 데이터베이스로부터 격리된 채 개발·테스트될 수 있게 한다.

| 용어 | 뜻 |
|---|---|
| 포트(port) | "목적 있는 대화" 하나. 애플리케이션 경계에 있는 인터페이스 |
| 어댑터(adapter) | 특정 기술(HTTP, GUI, 테스트 하네스, SQL, 메시지 큐)을 포트에 맞게 변환. 포트 하나에 어댑터 여럿 |
| 주(primary) / 구동(driving) | 애플리케이션을 구동하는 쪽. 유스케이스의 주 행위자. 예: UI, REST, 테스트 하네스 |
| 부(secondary) / 피구동(driven) | 애플리케이션이 구동하는 쪽. 부 행위자. 예: DB, 메일, 외부 API |

육각형이라는 모양에 대해 Cockburn 은 분명히 말한다. **6이라는 숫자가 중요한 게 아니다.** 1차원적인 레이어 그림에 묶이지 않고 필요한 만큼 포트와 어댑터를 그려 넣을 공간을 주려는 것이고, 경험상 포트는 2~4개 정도였다고 적었다. 또 구동 쪽 테스트 대체물로는 스크립트를 읽어 애플리케이션을 구동하는 FIT 같은 하네스가, 피구동 쪽 대체물로는 질의에 답하는 목(mock) DB 가 자연스럽다는 "좌우 비대칭" 을 설명한다.

```
           구동(primary) 쪽                       피구동(secondary) 쪽
  [REST 컨트롤러] ─┐                        ┌─▶ [JPA 어댑터] ──▶ PostgreSQL
  [배치 잡]       ─┼─▶ (입력 포트) ┌────────┐ (출력 포트) ─┼─▶ [PG 클라이언트] ──▶ 결제사
  [테스트 하네스] ─┘               │ 애플리케이션 │            └─▶ [인메모리 가짜] (테스트)
                                  └────────┘
```

### 어니언 (Palermo, 2008)

Palermo 의 근본 규칙: **모든 코드는 더 중심에 있는 레이어에만 의존할 수 있고, 바깥 레이어에는 의존할 수 없다. 모든 결합은 중심을 향한다.** 중심은 도메인 모델이고, 그 바로 바깥에 저장소 인터페이스 같은 것이 있으며, 그 구현은 DB 에 결합되므로 애플리케이션 코어 밖에 둔다. 가장 바깥에는 UI, 인프라, 테스트가 있다. 그는 "데이터베이스는 중심이 아니다, 외부다" 라고 쓰고, 이 아키텍처가 작은 웹사이트에는 맞지 않으며 복잡한 동작을 가진 오래 사는 업무 애플리케이션에 맞는다고 범위를 밝힌다. 헥사고날과의 공통 전제도 명시한다. 인프라를 외부화하고 어댑터 코드를 써서 인프라와 강하게 결합되지 않게 한다는 것이다.

### 클린 아키텍처 (Martin, 2012)

Robert C. Martin 의 [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) (2012) 는 헥사고날·어니언 등 여러 아키텍처를 하나의 그림으로 묶으며 목표를 이렇게 나열한다. 프레임워크로부터 독립, 테스트 가능, UI 로부터 독립, DB 로부터 독립, 외부 기관으로부터 독립.

그리고 이 모든 것을 가능하게 하는 규칙을 **의존 규칙(The Dependency Rule)** 이라 부른다.

> 소스 코드 의존성은 안쪽으로만 향할 수 있다. 안쪽 원의 어떤 것도 바깥 원의 어떤 것에 대해서도 알 수 없다. 특히 바깥 원에서 선언된 것의 이름(함수, 클래스, 변수 등)을 안쪽 원의 코드가 언급해서는 안 된다.

| 원 (안→밖) | 내용 |
|---|---|
| 엔터티(Entities) | 전사적 업무 규칙. 외부 변화에 가장 덜 영향받음 |
| 유스케이스(Use Cases) | 애플리케이션 고유 업무 규칙. 엔터티를 지휘해 유스케이스 목표 달성 |
| 인터페이스 어댑터 | 유스케이스·엔터티에 편한 형식 ↔ DB·웹에 편한 형식 변환. MVC, 프레젠터, SQL 은 여기까지 |
| 프레임워크와 드라이버 | DB, 웹 프레임워크 등 세부 사항 |

원이 꼭 네 개일 필요는 없다고 Martin 은 덧붙인다. **원의 개수는 도식일 뿐이고, 의존 규칙은 언제나 적용된다.** 안으로 갈수록 추상 수준이 높아진다.

제어 흐름과 의존 방향이 다를 때의 처리도 설명한다. 유스케이스가 프레젠터를 호출해야 하면, 유스케이스는 안쪽 원에 정의된 **출력 포트 인터페이스**를 호출하고 바깥의 프레젠터가 그것을 구현한다. 의존성 역전 원칙(DIP)으로 경계를 넘는 것이다([SOLID 원칙]({% post_url 2026-10-10-cs300-185-solid-principles %})).

### 셋의 관계

| | 헥사고날 | 어니언 | 클린 |
|---|---|---|---|
| 강조점 | 입출력 포트의 대칭, 테스트 대체성 | 도메인 모델 중심, DB 외부화 | 의존 규칙, 원별 책임 |
| 그림 | 육각형 + 어댑터 | 동심원 | 동심원 4개 |
| 공통 | 업무 규칙이 인프라를 모름, 인터페이스는 안쪽이 소유, 구현은 바깥 | ← | ← |

## 예제: Kotlin + Spring 구조와 규칙 강제

```
order/
├── domain/                     # 엔터티, 값 객체 — 프레임워크 import 없음
│   ├── Order.kt
│   └── Money.kt
├── application/
│   ├── port/in/PlaceOrderUseCase.kt      # 입력 포트
│   ├── port/out/LoadStockPort.kt         # 출력 포트 (안쪽이 정의)
│   ├── port/out/SaveOrderPort.kt
│   └── PlaceOrderService.kt              # 유스케이스 구현
└── adapter/
    ├── in/web/OrderController.kt         # 구동 어댑터
    └── out/persistence/OrderJpaAdapter.kt # 피구동 어댑터 (포트 구현)
```

```kotlin
// application/port/out/SaveOrderPort.kt — 안쪽이 필요한 것만 정의
interface SaveOrderPort { fun save(order: Order): OrderId }

// application/PlaceOrderService.kt — JPA 도, Spring MVC 도 모른다
class PlaceOrderService(
    private val stock: LoadStockPort,
    private val orders: SaveOrderPort,
) : PlaceOrderUseCase {
    override fun place(cmd: PlaceOrderCommand): OrderId {
        val available = stock.available(cmd.sku)
        val order = Order.place(cmd.sku, cmd.quantity, available)  // 규칙은 도메인에
        return orders.save(order)
    }
}

// adapter/out/persistence/OrderJpaAdapter.kt — 바깥이 안쪽 포트를 구현
@Component
class OrderJpaAdapter(private val repo: OrderJpaRepository) : SaveOrderPort {
    override fun save(order: Order) = repo.save(OrderEntity.from(order)).toId()
}
```

테스트에서는 `SaveOrderPort` 의 인메모리 구현을 넣어 DB 없이 `PlaceOrderService` 를 검증한다. Cockburn 이 의도한 "런타임 장치와 DB 로부터 격리된 개발·테스트" 다.

규칙은 문서가 아니라 테스트로 지킨다. [ArchUnit](https://www.archunit.org/userguide/html/000_Index.html)은 Palermo 의 정의를 따르는 `onionArchitecture()` 규칙을 제공한다.

```java
@ArchTest
static final ArchRule onion = onionArchitecture()
        .domainModels("com.shop.order.domain..")
        .domainServices("com.shop.order.domain.service..")
        .applicationServices("com.shop.order.application..")
        .adapter("web", "com.shop.order.adapter.in.web..")
        .adapter("persistence", "com.shop.order.adapter.out.persistence..");

@ArchTest
static final ArchRule domainIsFrameworkFree = noClasses()
        .that().resideInAPackage("..domain..")
        .should().dependOnClassesThat()
        .resideInAnyPackage("org.springframework..", "jakarta.persistence..");
```

## 흔한 오해와 함정

- **"폴더를 domain/application/adapter 로 나누면 클린 아키텍처다."** 의존 규칙을 검증하지 않으면 폴더 이름만 바뀐다. 도메인 클래스에 `@Entity` 가 붙어 있다면 이미 규칙이 깨졌다.
- **"모든 것에 포트를 만든다."** 외부 세계와의 경계에만 필요하다. 도메인 내부 클래스마다 인터페이스를 만들면 간접화만 늘어난다. Palermo 도 작은 웹사이트에는 맞지 않는다고 했다.
- **"육각형이니까 포트가 6개."** Cockburn 이 직접 부정했다. 그리기 공간의 문제다.
- **"매핑 코드가 너무 많다."** 도메인 모델과 JPA 엔터티, 요청 DTO 를 분리하면 변환 코드가 생긴다. 이것이 이 아키텍처의 실제 비용이다. 도메인 규칙이 빈약한 CRUD 서비스라면 레이어드로 충분할 수 있다.
- **"출력 포트는 인프라 쪽에 둔다."** 그러면 애플리케이션이 인프라를 import 해야 하므로 의존 방향이 다시 바깥을 향한다. 포트는 쓰는 쪽(안쪽)이 소유한다.

## 확인 문제

1. Cockburn 이 말한 구동(primary) 어댑터와 피구동(secondary) 어댑터의 차이는? 각각 테스트에서 무엇으로 대체하기 자연스러운가?
2. 클린 아키텍처의 의존 규칙을 한 문장으로 말하라.
3. 유스케이스가 결과를 화면에 보여 줘야 하는데 화면은 바깥 원에 있다. 의존 규칙을 어기지 않으려면?
4. 도메인 엔터티 클래스에 JPA `@Entity` 를 직접 붙이면 어떤 규칙을 어기는가? 그 대가와 이익은?
5. 세 아키텍처의 공통 전제를 Palermo 의 표현으로 말하라.

### 풀이

1. 구동 어댑터는 애플리케이션을 구동하는 쪽(UI, REST, 테스트 하네스), 피구동 어댑터는 애플리케이션이 구동하는 쪽(DB, 외부 서비스)이다. 전자는 스크립트로 애플리케이션을 구동하는 테스트 하네스(FIT 등)로, 후자는 목·인메모리 구현으로 대체하기 자연스럽다.
2. 소스 코드 의존성은 안쪽으로만 향하며, 안쪽 코드는 바깥에서 선언된 이름을 언급하지 않는다.
3. 유스케이스 원에 출력 포트 인터페이스를 정의하고 유스케이스는 그것만 호출한다. 바깥의 프레젠터가 그 인터페이스를 구현한다(의존성 역전).
4. 도메인(안쪽)이 영속성 프레임워크(바깥)의 이름을 언급하므로 의존 규칙 위반이다. 대가는 도메인이 ORM 변경과 그 제약(기본 생성자, 지연 로딩 등)에 묶이는 것이고, 이익은 매핑 코드가 줄어드는 것이다. 팀이 의식적으로 택할 수 있는 트레이드오프이며, 택했다면 ADR 로 남긴다.
5. 인프라를 외부화하고 어댑터 코드를 작성해 인프라가 강하게 결합되지 않게 한다.

## 더 읽을거리 (References)

- Alistair Cockburn, [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/), 2005
- Jeffrey Palermo, [The Onion Architecture: part 1](https://jeffreypalermo.com/2008/07/the-onion-architecture-part-1/), 2008
- Robert C. Martin, [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html), 2012
- ArchUnit, [User Guide](https://www.archunit.org/userguide/html/000_Index.html)
- CS300: [레이어드 아키텍처]({% post_url 2026-10-10-cs300-197-layered-architecture %}), [도메인 주도 설계]({% post_url 2026-10-10-cs300-198-domain-driven-design %}), [SOLID 원칙]({% post_url 2026-10-10-cs300-185-solid-principles %})
