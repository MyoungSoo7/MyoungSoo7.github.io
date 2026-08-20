---
layout: post
title: "의존성 화살표가 안쪽으로 돌기까지 — 레이어드·헥사고날·클린 아키텍처 비교"
date: 2026-08-20 21:45:00 +0900
categories: [engineering, architecture]
tags: [Layered, Hexagonal, Clean, PortsAndAdapters, DDD, Testability, DependencyRule]
---

"레이어드·헥사고날·클린 아키텍처 차이가 뭔가요" 는 신입 인터뷰의 단골이다. 답변은 대부분 **그림의 차이** ("클린은 동심원, 헥사고날은 육각형…") 로 흐른다. 그러나 이 셋을 만든 저자들이 실제로 겨눈 건 그림이 아니라 **의존성이 어느 방향으로 흐르는가** 한 줄이다. 이 글은 그 한 줄을 시대순으로 따라간다.

미리 밝혀두면 **셋은 서로 대체 관계가 아니다.** 각자 앞선 것이 미처 다루지 못한 문제를 겨눈다. 헥사고날은 레이어드 위에, 클린은 헥사고날 위에 얹혀 있다. 이걸 "요즘은 클린이 정답" 으로 뭉개면, 자기 팀 코드가 왜 여전히 아픈지 설명할 수 없게 된다.

이 시리즈의 [이전 글: 스프링/스프링부트가 실제로 지운 것들](/2026/08/20/what-spring-and-spring-boot-solved/) 도 같은 관점을 썼다 — **결과** 가 아니라 **문제** 부터 나열한다.

---

## 1. 아키텍처 이전: 왜 코드가 아팠나

1980년대 후반까지의 전형적인 비즈니스 앱 코드는 한 함수 안에 UI, 비즈니스 규칙, DB 접근이 섞여 있었다. 예시 (VB6 시대의 이벤트 핸들러가 실제로 이랬다).

```
Sub BtnSave_Click()
    If txtAmount.Text = "" Then MsgBox "금액 입력": Exit Sub
    conn.Open "DSN=orders;UID=sa;PWD=..."
    sql = "INSERT INTO orders VALUES(" & txtAmount.Text & ")"
    conn.Execute sql
    conn.Close
    MsgBox "저장됨"
End Sub
```

이 22줄 안에 존재하는 문제:

- **DB 를 바꾸려면** 이벤트 핸들러를 뒤진다
- **검증 규칙만 테스트하려 해도** UI 폼과 DB 를 붙여야 한다
- **같은 규칙이 다른 화면에 반복** 되어도 재사용할 방법이 없다
- **UI 프레임워크가 바뀌면** (WinForms → WPF → Web) 규칙까지 다시 쓴다

이 다섯 개 통증이 이후 30년 동안 아키텍처 담론을 만들어 낸다.

---

## 2. Layered Architecture (1990s~): 수직으로 자르기

책으로 정착한 건 Buschmann 외의 *Pattern-Oriented Software Architecture* (1996)[^posa] 와 Fowler 의 *Patterns of Enterprise Application Architecture* (2002)[^peaa] 다. 아이디어는 단순하다 — **책임을 층으로 자르고, 위층은 아래층만 부른다.**

```
┌─────────────────────────┐
│ Presentation (UI/API)   │  ← 사용자 입력, 화면
├─────────────────────────┤
│ Business (Service)      │  ← 규칙, 워크플로우
├─────────────────────────┤
│ Data Access (Repository)│  ← SQL, ORM
├─────────────────────────┤
│ Database                │
└─────────────────────────┘
       ↓ 의존
```

같은 저장 로직이 이렇게 바뀐다.

```java
// Presentation
@Controller
class OrderController {
    private final OrderService svc;
    @PostMapping("/orders")
    ResponseEntity<?> create(@RequestBody OrderRequest req) {
        svc.create(req.amount()); return ResponseEntity.ok().build();
    }
}
// Business
@Service
class OrderService {
    private final OrderRepository repo;
    void create(BigDecimal amount) {
        if (amount.signum() <= 0) throw new IllegalArgumentException();
        repo.save(new OrderEntity(amount));
    }
}
// Data Access
interface OrderRepository extends JpaRepository<OrderEntity, Long> {}
```

**지워진 것**: DB · UI · 규칙이 서로 다른 파일로 갈라졌다. 규칙만 단위 테스트하기 쉬워졌고, UI 프레임워크 교체도 상대적으로 국지화됐다.

**남은 문제**: `OrderService` 가 `OrderRepository` 를 부른다 — 즉 **비즈니스 계층이 데이터 계층에 의존한다.** 그리고 `OrderRepository` 는 JPA `JpaRepository` 를 상속한다. 결과적으로 비즈니스 계층은 **간접적으로 JPA에 묶인다.** DB 를 인메모리로 바꾸거나 이벤트 소싱으로 갈아엎으려 하면, 비즈니스 계층까지 흔들린다.

또 하나 — **JPA `@Entity` 가 그대로 비즈니스 객체로 쓰이면**, DB 스키마 변경이 비즈니스 규칙 코드를 건드리게 된다. 계층은 나뉘었지만, **의존성 화살표가 여전히 위에서 아래로만** 흐른다.

---

## 3. Hexagonal Architecture (2005): DB 는 그저 하나의 액터일 뿐이다

Alistair Cockburn 은 2005년 위키에, 2006년에 정식 아티클로 *The Pattern: Ports and Adapters* 를 발표했다.[^hex] 통칭 헥사고날 아키텍처. 그가 새로 도입한 문장은 이 한 줄이다:

> *"애플리케이션은 인간 사용자, 다른 프로그램, 자동 배치, 스크립트 등 어떤 액터든 대칭적으로 다뤄야 한다. 데이터베이스도 액터의 하나일 뿐이다."*

이 관점 전환의 코드 결과는 이렇다.

```java
// domain — 순수 자바, 프레임워크 무관
public class Order {
    private final BigDecimal amount;
    public Order(BigDecimal amount) {
        if (amount.signum() <= 0) throw new IllegalArgumentException();
        this.amount = amount;
    }
    public BigDecimal amount() { return amount; }
}

// port (inbound) — 애플리케이션이 정의한 계약
public interface CreateOrderUseCase {
    void create(BigDecimal amount);
}

// port (outbound) — 애플리케이션이 필요로 하는 것
public interface OrderRepository {
    void save(Order order);
}

// application service
public class CreateOrderService implements CreateOrderUseCase {
    private final OrderRepository repo;
    public CreateOrderService(OrderRepository repo) { this.repo = repo; }
    public void create(BigDecimal amount) { repo.save(new Order(amount)); }
}

// adapter (driving) — 프레임워크가 애플리케이션을 부르는 쪽
@RestController
class OrderRestAdapter {
    private final CreateOrderUseCase useCase;
    OrderRestAdapter(CreateOrderUseCase u) { this.useCase = u; }
    @PostMapping("/orders")
    void create(@RequestBody OrderRequest req) { useCase.create(req.amount()); }
}

// adapter (driven) — 애플리케이션이 프레임워크를 부르는 쪽
@Repository
class OrderJpaAdapter implements OrderRepository {
    private final OrderJpaRepository jpa;
    OrderJpaAdapter(OrderJpaRepository j) { this.jpa = j; }
    public void save(Order o) { jpa.save(OrderJpaEntity.from(o)); }
}
```

**핵심 변화**: `OrderRepository` 는 이제 **애플리케이션 계층에 정의된 인터페이스** 다. JPA 는 그것을 *구현* 하는 어댑터일 뿐이다. 화살표가 뒤집혔다 — 도메인이 DB 를 부르는 게 아니라, DB 어댑터가 도메인이 정의한 계약을 만족시킨다.

**지워진 것**: `Order` 도메인 클래스는 스프링·JPA·심지어 자바 웹 API 조차 모른다. 도메인만 단위 테스트하려면 `new CreateOrderService(new InMemoryOrderRepository())` 로 끝난다. DB 를 통째로 갈아엎어도 도메인 코드는 한 줄도 안 바뀐다.

**남은 문제**: 대칭이 우아하지만 **인터페이스가 많아진다.** 4줄짜리 CRUD API 를 위해 use case interface + service class + port + adapter 4~5개 파일을 만들어야 한다는 인상. 실제로 헥사고날을 "과잉 설계다" 라고 비판하는 시각의 근거가 여기다.

---

## 4. Clean Architecture (2012): 규칙을 규칙으로 못박다

Uncle Bob (Robert C. Martin) 은 2012년 블로그 *The Clean Architecture* 에서, 2017년 동명의 책에서 이 그림을 대중화했다.[^clean]

```
       ┌───────────────────────────┐
       │  Frameworks & Drivers     │  ← Web, DB, UI
       │  ┌───────────────────────┐│
       │  │ Interface Adapters    ││  ← Controllers, Presenters, Gateways
       │  │  ┌───────────────────┐││
       │  │  │  Application     │││  ← Use Cases
       │  │  │  Business Rules  │││
       │  │  │ ┌───────────────┐│││
       │  │  │ │  Enterprise   ││││  ← Entities
       │  │  │ │ Business Rules││││
       │  │  │ └───────────────┘│││
       │  │  └───────────────────┘││
       │  └───────────────────────┘│
       └───────────────────────────┘
        의존성은 **오직 안쪽으로만** 향한다
```

Uncle Bob 이 이 그림에서 새로 만든 것은 **없다**. 그는 자기 글에서 이렇게 인정한다 — 이 그림은 헥사고날(Cockburn, 2005), 오니언(Palermo, 2008)[^onion], BCE(Jacobson, 1992), DCI(Reenskaug/Coplien, 2009) 를 **하나의 그림으로 합친 것** 이라고. 새로운 건 하나뿐이다 — **의존성 규칙 (Dependency Rule)** 을 아키텍처의 최상위 불변식으로 격상시켰다.

> *"소스 코드 의존성은 오직 안쪽만 향할 수 있다. 안쪽 원은 바깥쪽 원에 대해 아무것도 알아서는 안 된다."*

**같은 CRUD 를 클린으로 쓰면 헥사고날과 코드가 매우 비슷하다.** 다른 점은 이름 짓기와 계층 개수 (엔티티/유스케이스 분리 강조) 정도다. 실제로 많은 실무 팀이 "우리는 헥사고날+클린" 이라는 표현을 쓴다 — 둘의 경계가 흐리기 때문이다.

**지워진 것**: 신입이 리팩터링할 때 "이거 어느 계층에 놔야 하나요" 물으면, **의존성 화살표만 그려보고 답이 나온다.** 이 규칙이 코드 리뷰의 객관적 기준을 만들어 준다.

**남은 문제 (여전히)**: 계층 간 데이터를 옮기려고 **DTO 매핑 코드가 폭증** 한다. MapStruct 같은 도구가 그걸 완화하지만, 도메인 → 애플리케이션 → 어댑터 사이에서 DTO 3~4개를 유지하는 팀 피로가 실재한다.

---

## 5. 세 아키텍처 나란히 놓기

| 항목                     | Layered (1990s~)              | Hexagonal (2005)                | Clean (2012)                         |
| ------------------------ | ----------------------------- | ------------------------------- | ------------------------------------ |
| 의존성 방향              | 위 → 아래 (단방향)            | 어댑터 → 애플리케이션 (안쪽으로) | 바깥 원 → 안쪽 원 (안쪽으로)         |
| 도메인이 아는 것         | 데이터 계층 인터페이스        | 자기 자신만                     | 자기 자신만                          |
| 프레임워크 위치          | 위·아래 모두                  | 어댑터 안                       | 최외곽 원                            |
| 인터페이스(포트) 위치    | 없거나 데이터 계층에          | 애플리케이션 안에서 정의        | 유스케이스 계층에서 정의             |
| DB 교체 시 도메인 영향   | 있음 (특히 `@Entity` 재사용)  | 없음                            | 없음                                 |
| 파일 수 (CRUD 한 건)     | 3~4                           | 5~7                             | 5~8                                  |
| 학습 곡선                | 완만                          | 중간                            | 중~높음                              |
| 어울리는 규모            | 소규모 CRUD, 프로토타입       | 중대형 도메인, 오래 유지        | 대형·장기, 팀 규모 있을 때           |

**한 문장으로 요약하면**: 레이어드는 **책임을 잘랐고**, 헥사고날은 **화살표를 뒤집었으며**, 클린은 **그 화살표를 법으로 만들었다.**

---

## 6. 그럼 클린이면 끝인가

아니다. 세 층으로 겨눈 문제 뒤에 **여전히 남은 것** 이 있다.

- **DTO 매핑 피로**: 도메인 객체 → 유스케이스 입력 DTO → 어댑터 응답 DTO. 값 3개짜리 API 를 위해 클래스 6개. MapStruct/Lombok 이 완화하지만 근본적으로는 인접 계층 간의 impedance mismatch 다.
- **검증은 어느 계층인가**: 형식 검증(이메일 정규식)은 어댑터, 비즈니스 검증(재고 부족)은 도메인 — 문서로는 명확하지만 실무에서는 자주 뒤섞인다.
- **CQRS 를 얹으면 자연스럽지 않다**: 쓰기는 유스케이스로 잘 들어맞지만, 대시보드 조회 같은 read-heavy 는 원 밖에서 SQL 직행이 훨씬 빠르다. 클린은 이걸 "쿼리 유스케이스" 로 억지로 감싸려다 복잡도가 튄다.[^cqrs]
- **모듈 경계 ≠ 아키텍처 경계**: 마이크로서비스로 쪼갤 때 "이 도메인은 어디까지가 한 서비스" 를 결정해 주는 건 이 세 아키텍처 어느 것도 아니다. 그건 DDD 의 Bounded Context 몫이다.

즉 이 세 층은 **한 서비스 안의 의존성 방향** 을 다룬다. 서비스 간 경계와 데이터 흐름은 그 위층에서 별도로 답해야 한다.

---

## 7. 요약

1980년대의 코드는 UI·규칙·DB 가 한 함수에 뭉쳐 있어서 **하나를 바꾸면 나머지가 무너졌다.** 레이어드는 이걸 수직으로 잘라 규칙을 UI 와 DB 에서 떼어냈다 — 그러나 여전히 규칙이 DB 라이브러리를 알고 있었다. 헥사고날은 그 화살표를 뒤집어 **DB 를 애플리케이션의 계약을 만족시키는 어댑터** 로 격하시켰다. 클린은 그 뒤집힌 화살표를 이름 붙이고 규칙으로 못박아, 팀이 "어느 계층에 놓을지" 의견 다툼을 하지 않게 했다.

셋 다 지금도 유효하다. 프로토타입 하나 하루에 만드는 팀에게 클린을 강요하면 파일 5개짜리 CRUD 가 15개가 된다. 반대로 20년 유지할 정산 시스템에 레이어드만 쓰면, 5년 뒤 JPA 를 뜯어내려 할 때 도메인까지 갈아엎어야 한다. **선택 기준은 "얼마나 오래 살아남을 코드인가" 다.**

[^posa]: Buschmann, Meunier, Rohnert, Sommerlad, Stal, *Pattern-Oriented Software Architecture Volume 1: A System of Patterns*, Wiley, 1996. Layers 패턴이 처음 형식적으로 정의된 저작.
[^peaa]: Martin Fowler, *Patterns of Enterprise Application Architecture*, Addison-Wesley, 2002. Domain Layer, Data Source Layer, Presentation Layer 라는 명명이 이 책에서 자리 잡았다.
[^hex]: Alistair Cockburn, *Hexagonal architecture* (wiki 2005), *The Pattern: Ports and Adapters* (article 2006). 원문은 alistaircockburn.com 및 저자 후속 블로그에서 참고 가능.
[^onion]: Jeffrey Palermo, "The Onion Architecture" 시리즈, 2008. 도메인 모델을 중앙에 두고 인프라를 외곽 링으로 두는 개념. 클린의 직접적 전신 중 하나.
[^clean]: Robert C. Martin, "The Clean Architecture", 2012 블로그 (blog.cleancoder.com), *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Prentice Hall, 2017. Uncle Bob 자신이 헥사고날·오니언·BCE·DCI 의 통합임을 명시.
[^cqrs]: Greg Young 의 CQRS 정리(2010)와 클린 아키텍처의 접점은 지금도 논쟁적이다. Uncle Bob 은 CQRS 를 "유스케이스의 두 종류" 로 흡수 가능하다고 주장하지만, 실무에서는 read side 를 원 밖으로 빼는 팀이 더 많다.
