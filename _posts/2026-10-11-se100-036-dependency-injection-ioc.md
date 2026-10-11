---
layout: post
title: "[SE100 #036] 의존성 주입과 제어의 역전"
date: 2026-10-11 17:00:00 +0900
categories: [software-engineering]
tags: [se100, code-quality, dependency-injection, inversion-of-control, composition-root]
---

소프트웨어 공학 100 주제 시리즈의 36번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

제어의 역전(IoC)은 "프레임워크가 내 코드를 부른다" 는 넓은 개념이고, 의존성 주입(DI)은 그중 **객체가 협력자를 스스로 찾지 않고 바깥에서 받는다**는 좁은 패턴이다. DI 의 본질은 컨테이너가 아니라 생성자 인자이며, 조립은 애플리케이션 진입점 한곳(Composition Root)에서 한다.

## 왜 필요한가

```kotlin
class OrderService {
    private val repo = JdbcOrderRepository(DataSourceFactory.get())   // 직접 생성
    private val clock = Clock.systemUTC()                              // 전역 접근
    fun place(order: Order) { ... }
}
```

이 클래스를 테스트하려면 실제 DB 가 필요하고, "자정 직전 주문" 같은 시간 경계를 재현할 방법이 없다. 결제 모듈을 바꾸려면 `OrderService` 코드를 고쳐야 한다. 협력자를 **누가 고르는가**라는 결정이 사용하는 쪽 안에 박혀 있기 때문이다.

DI 는 이 결정을 바깥으로 빼낸다. 그 결과 테스트에서는 가짜를, 운영에서는 진짜를 넣을 수 있고, 클래스의 의존성이 생성자 시그니처에 정직하게 드러난다.

## 핵심 개념

### 세 용어를 구분한다

| 용어 | 무엇 | 층위 |
|---|---|---|
| 의존성 역전 원칙(DIP) | 상위 정책이 하위 세부에 의존하지 않고 둘 다 추상에 의존 | 설계 원칙 ([SOLID]({% post_url 2026-10-10-cs300-185-solid-principles %})의 D) |
| 제어의 역전(IoC) | 흐름 제어를 프레임워크가 쥐고 사용자 코드를 호출 | 프레임워크의 일반 성질 |
| 의존성 주입(DI) | 객체의 협력자를 외부에서 넣어 줌 | 구체적 패턴 |

DIP 없이 DI 를 할 수도 있고(구체 클래스를 주입), DI 없이 DIP 를 지킬 수도 있다(팩토리). 셋은 자주 함께 쓰이지만 같은 말이 아니다.

### IoC: 할리우드 원칙

Fowler 의 [InversionOfControl](https://martinfowler.com/bliki/InversionOfControl.html)은 명령줄 프로그램과 GUI 프로그램을 비교한다. 명령줄에서는 내가 언제 무엇을 부를지 정하지만, GUI 에서는 이벤트 루프에 제어를 넘기고 프레임워크가 내 핸들러를 부른다. 이것이 "Don't call us, we'll call you" 로 알려진 할리우드 원칙이다. 같은 글은 이 역전이 프레임워크를 "확장 가능한 골격" 으로 만든다는 Ralph Johnson 과 Brian Foote 의 말을 인용하고, IoC 가 **라이브러리와 프레임워크를 가르는 핵심**이라고 덧붙인다.

### DI 라는 이름의 탄생 (2004)

Fowler 는 2004년 1월 23일 글 [Inversion of Control Containers and the Dependency Injection pattern](https://martinfowler.com/articles/injection.html)에서 당시 PicoContainer, Spring 같은 "경량 컨테이너" 가 하는 일을 IoC 라고 부르는 것은 너무 포괄적이라며 **"Dependency Injection" 이라는 더 구체적인 이름**을 제안했다. 이 글은 주입 방식을 세 가지로 정리한다.

| 방식 | 형태 | 오늘날의 평가 |
|---|---|---|
| 생성자 주입 | `OrderService(repo, clock)` | 기본값으로 권장 |
| 세터 주입 | `setRepo(repo)` | 선택적 의존성에 한정 |
| 인터페이스 주입 | 주입용 인터페이스를 구현 | 거의 쓰지 않음 |

같은 글은 대안인 **서비스 로케이터**(객체가 레지스트리에 협력자를 요청)도 비교한다.

Spring 공식 문서는 [생성자 주입을 일반적으로 권장](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html)하며 이유를 셋 든다. 컴포넌트를 불변 객체로 만들 수 있고, 필수 의존성이 null 이 아님을 보장하며, 항상 완전히 초기화된 상태로 반환된다. 덧붙여 생성자 인자가 많다는 것은 클래스의 책임이 너무 많다는 **나쁜 냄새**라고 적는다. 세터 주입은 합리적 기본값이 있는 선택적 의존성에만 쓰라고 한다.

### 서비스 로케이터는 왜 문제인가

Mark Seemann 은 [Service Locator is an Anti-Pattern](https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/)(2010)에서 서비스 로케이터가 **클래스의 의존성을 숨긴다**고 지적한다. 생성자만 봐서는 무엇이 필요한지 알 수 없고, 등록을 빠뜨리면 컴파일 시점이 아니라 **런타임**에 실패하며, 어떤 변경이 호환성을 깨는지 판단하기 어려워진다.

```java
// 숨은 의존성: 시그니처는 깨끗하지만 거짓말이다
class ReportJob {
    void run() {
        var repo = ServiceLocator.get(SalesRepository.class);   // 등록 안 됐으면 런타임 실패
        var mailer = ServiceLocator.get(Mailer.class);
        ...
    }
}
// 정직한 의존성: 필요한 것이 시그니처에 보인다
class ReportJob {
    ReportJob(SalesRepository repo, Mailer mailer) { ... }
}
```

### Composition Root

Seemann 의 [Composition Root](https://blog.ploeh.dk/2011/07/28/CompositionRoot/)(2011)는 모듈들을 조립하는 (가급적) **유일한 장소**를 애플리케이션 진입점에 최대한 가깝게 두라고 한다. 나머지 코드는 생성자 주입으로 필요한 것을 받기만 하고, 객체 그래프를 직접 조립하지 않는다. 컨테이너를 쓴다면 컨테이너를 만지는 코드도 이곳에만 있어야 한다.

```
main() ── Composition Root ──────────────────────────────┐
  val ds    = HikariDataSource(config)                    │  여기서만
  val repo  = JdbcOrderRepository(ds)                     │  구체 클래스를
  val clock = Clock.systemUTC()                           │  고르고 조립한다
  val svc   = OrderService(repo, clock)                   │
  HttpServer(OrderController(svc)).start()                │
─────────────────────────────────────────────────────────┘
  OrderService, OrderController … : 받기만 한다. new 하지 않는다.
```

### 컨테이너는 선택이다

| 접근 | 조립 시점 | 예 |
|---|---|---|
| 순수 DI (수동 조립) | 코드 그대로 | `main` 함수 |
| 런타임 컨테이너 | 실행 시 리플렉션·설정 | Spring, [Guice](https://github.com/google/guice) |
| 컴파일 타임 생성 | 빌드 시 코드 생성 | [Dagger](https://dagger.dev/)("완전히 정적인 컴파일 타임 DI 프레임워크") |
| 언어·프레임워크 내장 | 함수 인자 해석 | [FastAPI `Depends`](https://fastapi.tiangolo.com/tutorial/dependencies/), [pytest fixture](https://docs.pytest.org/en/stable/how-to/fixtures.html) |

Java 생태계는 2009년 확정된 [JSR 330](https://jcp.org/en/jsr/detail?id=330)으로 `@Inject` 같은 주입 지점 주석을 표준화해, 컨테이너가 달라도 주입받는 쪽 코드는 같은 주석을 쓸 수 있게 했다.

## 실무 적용

### Kotlin: 순수 DI 와 테스트

```kotlin
interface OrderRepository { fun save(order: Order) }
fun interface PaymentGateway { fun charge(orderId: String, amount: Long): Boolean }

class OrderService(
    private val repo: OrderRepository,
    private val payments: PaymentGateway,
    private val clock: Clock,
) {
    fun place(order: Order): Result<Order> {
        val stamped = order.copy(placedAt = clock.instant())
        if (!payments.charge(stamped.id, stamped.total)) return Result.failure(PaymentDeclined())
        repo.save(stamped)
        return Result.success(stamped)
    }
}

// 테스트: 가짜를 손으로 만든다. 프레임워크도, 목 라이브러리도 필요 없다.
class InMemoryRepo : OrderRepository {
    val saved = mutableListOf<Order>()
    override fun save(order: Order) { saved += order }
}

@Test fun `결제가 거절되면 저장하지 않는다`() {
    val repo = InMemoryRepo()
    val svc = OrderService(repo, { _, _ -> false },
                           Clock.fixed(Instant.parse("2026-10-11T23:59:59Z"), ZoneOffset.UTC))
    assertTrue(svc.place(sampleOrder()).isFailure)
    assertTrue(repo.saved.isEmpty())
}
```

`PaymentGateway` 를 `fun interface` 로 선언했기 때문에 테스트에서 람다로 넘길 수 있다. 테스트 대역의 종류(fake, stub, mock)는 Fowler 의 [TestDouble](https://martinfowler.com/bliki/TestDouble.html)이 정리한다.

### Python: FastAPI 의존성 교체

FastAPI 는 `Depends` 로 선언한 의존성을 테스트에서 [`app.dependency_overrides`](https://fastapi.tiangolo.com/advanced/testing-dependencies/)로 바꿔 끼울 수 있다.

```python
def get_repo() -> OrderRepository:
    return SqlOrderRepository(engine)

@app.post("/orders")
def place(req: OrderIn, repo: OrderRepository = Depends(get_repo)):
    ...

# test
app.dependency_overrides[get_repo] = lambda: InMemoryOrderRepository()
```

### 점검표

- [ ] 도메인·서비스 클래스 안에 `new`/생성자 호출로 만드는 **인프라 객체**가 없다(값 객체 생성은 괜찮다)
- [ ] 시계, 난수, 환경 변수 같은 숨은 입력도 주입받는다
- [ ] 생성자 인자가 대여섯 개를 넘으면 책임 분리를 먼저 검토한다
- [ ] 컨테이너 API(`getBean`, `ApplicationContext`)는 Composition Root 와 프레임워크 접점에만 있다
- [ ] 필드 주입 대신 생성자 주입을 쓴다

## 흔한 오해와 함정

- **"DI = Spring(컨테이너)."** DI 는 생성자 인자일 뿐이다. 작은 서비스는 `main` 에서 손으로 조립하는 편이 더 읽기 쉬울 때가 많다.
- **"모든 클래스에 인터페이스를 만든다."** 구현이 하나뿐이고 교체할 이유가 없는 클래스에까지 인터페이스를 두면 탐색만 어려워진다. 경계(DB, 외부 API, 시계)에만 추상을 둔다.
- **필드 주입.** 테스트에서 리플렉션 없이는 의존성을 넣을 수 없고, 의존성이 시그니처에서 사라진다.
- **컨테이너를 주입받기.** `ApplicationContext` 를 받아 `getBean` 을 부르면 이름만 DI 인 서비스 로케이터다.
- **순환 의존.** 컨테이너는 생성자 주입 순환을 실행 시 감지해 실패시킨다(Spring 은 `BeanCurrentlyInCreationException`). 세터 주입으로 우회하지 말고 책임을 다시 나눈다.

## 확인 문제

1. DIP, IoC, DI 를 한 문장씩으로 구분하라.
2. Fowler 가 2004년에 "Dependency Injection" 이라는 새 이름을 제안한 이유는?
3. 서비스 로케이터가 생성자 주입보다 나쁜 이유 두 가지를 Seemann 의 논지로 설명하라.
4. Spring 문서가 생성자 주입을 권장하는 세 가지 이유와, 생성자 인자가 많을 때의 해석은?

### 풀이

1. DIP: 상위·하위 모듈 모두 추상에 의존하라는 설계 원칙. IoC: 흐름 제어를 프레임워크가 쥐고 사용자 코드를 호출하는 일반 성질. DI: 객체의 협력자를 외부에서 넣어 주는 구체 패턴.
2. 경량 컨테이너들이 하는 일을 IoC 라 부르기엔 그 용어가 너무 포괄적이어서, 협력자를 주입한다는 구체적 행위를 가리키는 이름이 필요했다.
3. 의존성이 시그니처에서 숨겨져 무엇이 필요한지 알 수 없고, 등록 누락이 컴파일이 아닌 런타임 오류로 드러난다.
4. 불변 객체로 만들 수 있고, 필수 의존성이 null 이 아님을 보장하며, 완전히 초기화된 상태로 반환된다. 인자가 많으면 클래스 책임이 과다하다는 냄새로 보고 분리를 검토한다.

## 더 읽을거리 (References)

- Martin Fowler, [Inversion of Control Containers and the Dependency Injection pattern](https://martinfowler.com/articles/injection.html), 2004
- Martin Fowler, [InversionOfControl](https://martinfowler.com/bliki/InversionOfControl.html)
- Mark Seemann, [Service Locator is an Anti-Pattern](https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/), 2010 / [Composition Root](https://blog.ploeh.dk/2011/07/28/CompositionRoot/), 2011
- Spring Framework, [Dependency Injection](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html)
- [JSR 330: Dependency Injection for Java](https://jcp.org/en/jsr/detail?id=330), [Dagger](https://dagger.dev/), [Guice](https://github.com/google/guice)
- FastAPI, [Testing Dependencies with Overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
