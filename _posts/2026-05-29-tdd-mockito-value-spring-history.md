---
layout: post
title: "TDD 와 Mockito — Kent Beck 의 *빨강·초록·리팩토링* 부터 Spring 단위 테스트의 현재까지"
date: 2026-05-29 00:10:00 +0900
categories: [java, spring, testing]
tags: [tdd, mockito, junit, spring-boot, unit-test, kent-beck, london-school, detroit-school]
---

> *''테스트를 먼저 쓴다''* 는 한 문장은, 2002 년 Kent Beck 이 출판한 **Test-Driven Development by Example** 의 표지 한 줄로 요약된다. 하지만 그 한 문장이 자바 진영에서 *진짜* 살아남은 이유는, *Mockito* 라는 작은 라이브러리가 *''의존성을 어떻게 끊을 것인가''* 라는 막막한 문제를 *대화체* 로 풀어냈기 때문이다.

이 글은 *''Mockito 가 왜 자바 TDD 의 표준이 되었나''* 를 **TDD 의 역사 흐름** 위에서 풀어본다. *EasyMock → JMock → Mockito* 로 이어진 mock 라이브러리의 진화, *London vs Detroit* 학파의 철학적 분기, 그리고 Spring Boot 3 에서 `@MockitoBean` 까지 — *기술* 보다는 *왜* 에 무게를 둔다.

---

## 1. TDD 의 출발 — *디자인 도구* 로서의 테스트

Kent Beck 은 1990 년대 후반 *eXtreme Programming (XP)* 의 핵심 실천법 중 하나로 *Test-First Development* 를 정리했다. 2002 년 **TDD by Example** 에서 정리한 사이클은 *세 단어* 로 끝난다:

> **Red → Green → Refactor**
>
> - *Red*: 실패하는 테스트를 먼저 쓴다
> - *Green*: 그 테스트를 통과시키는 *가장 단순한* 코드를 쓴다
> - *Refactor*: 테스트가 초록인 상태에서 구조를 개선한다

이 사이클의 *진짜 의미* 는 *''버그를 잡는 도구''* 가 아니라 *''설계를 강제하는 도구''* 라는 점이다. Kent Beck 본인이 *''TDD 는 분석 기법이 아니라 설계 기법이다''* 라고 못 박았다. *테스트하기 어렵다 → 결합도가 높다 → 설계가 나쁘다* 의 인과 관계가 *컴파일러처럼* 작용한다.

### 1.1 TDD 가 자바에서 *막힌* 지점

문제는, 자바 진영의 *현실 객체* 는 *대부분 협력자* 와 함께 산다는 것.

```java
@Service
public class OrderService {
    private final PaymentGateway gateway;        // ← 외부 결제 API
    private final InventoryRepository inventory;  // ← DB
    private final NotificationClient notifier;    // ← Slack/Email

    public OrderResult place(OrderCommand cmd) {
        inventory.reserve(cmd.items());
        var payment = gateway.charge(cmd.amount());
        notifier.notify(payment);
        return OrderResult.of(payment);
    }
}
```

이 `OrderService` 의 단위 테스트를 쓰려고 하면 *세 가지 외부 의존성* 이 즉시 발목을 잡는다. 진짜 결제 API 를 호출할 순 없고, DB 를 띄우면 *분 단위* 가 걸리고, Slack 으로 알람이 진짜 가면 동료가 화낸다.

*''그럼 가짜를 끼우자''* 가 자연스러운 해법인데, 이 *''가짜를 어떻게 만들 것인가''* 가 2000 년대 자바 진영의 *오랜 숙제* 였다.

---

## 2. Mock 라이브러리의 진화 — *EasyMock → JMock → Mockito*

### 2.1 EasyMock (2001, Tammo Freese) — *record/replay* 시대

처음 자바에서 mock 의 표준은 **EasyMock** 의 *record-replay* 패턴이었다.

```java
// EasyMock — 옛 방식
PaymentGateway gateway = createMock(PaymentGateway.class);
expect(gateway.charge(1000)).andReturn(PaymentResult.success("tx-1"));
replay(gateway);   // ← 여기서부터 ''진짜 모드''

orderService.place(cmd);

verify(gateway);   // ← 기대했던 호출이 다 일어났는지 검증
```

문제는 *기대치를 미리 다 기록* 해야 한다는 점. 테스트 하나에 *record / replay / verify* 가 다 들어가니 *읽기 어려웠고*, 기대치를 *하나만 빼먹어도* 깨졌다.

### 2.2 JMock (2003, Steve Freeman·Nat Pryce) — *기대치 DSL*

**JMock** 은 *London school* 의 진원지답게 *기대치를 DSL 로 명시* 하는 길로 갔다.

```java
context.checking(new Expectations() {{
    oneOf(gateway).charge(1000);
    will(returnValue(PaymentResult.success("tx-1")));
}});
```

표현력은 좋아졌지만 *익명 내부 클래스 + 이중 중괄호* 라는 *자바 8 이전의 한계* 때문에 *시각적 노이즈* 가 컸다. *''mock 이 좋긴 한데 코드가 안 예쁘다''* 가 당시의 합의였다.

### 2.3 Mockito (2007/2008, Szczepan Faber) — *그냥 호출하고, 그냥 검증한다*

**Mockito** 는 한 가지 *과감한 선택* 으로 판을 뒤집었다.

> *''기대치를 *미리* 기록할 필요가 없다. *호출이 끝난 뒤* 에 검증하면 된다.''*

```java
// Mockito — given/when/then
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock PaymentGateway gateway;
    @Mock InventoryRepository inventory;
    @Mock NotificationClient notifier;

    @InjectMocks OrderService orderService;

    @Test
    void 결제_성공_시_재고를_예약하고_알람을_보낸다() {
        // given — *대화체* 로 읽힘
        given(gateway.charge(1000)).willReturn(PaymentResult.success("tx-1"));

        // when
        var result = orderService.place(new OrderCommand(1000, items));

        // then
        then(inventory).should().reserve(items);
        then(notifier).should().notify(any(PaymentResult.class));
        assertThat(result.txId()).isEqualTo("tx-1");
    }
}
```

이 코드의 *가치* 는 *''어떻게 동작하는가''* 가 아니라 *''왜 받아들여졌는가''* 에 있다.

#### Mockito 가 *가치* 였던 이유 — 4 가지

1. **호출이 없어도 깨지지 않음** — `verify` 를 안 쓰면 그 호출은 검증되지 않는다. *''내가 검증하고 싶은 것만''* 검증할 수 있다.
2. **기대치 없이도 mock 이 동작** — 메서드 호출 시 `null` / `0` / `false` 를 자동 반환. *Stubbing 안 한 메서드를 호출해도 NPE 가 안 난다*. → 테스트가 *깨지기 어렵다*.
3. **자연어 같은 가독성** — `given() / when() / then()` 패턴. Behavior-Driven Development (BDD) 와 자연스럽게 맞물림.
4. **부분 mock (spy)** — *real object* 를 두고 *일부 메서드만* mock. *legacy 코드* 를 점진적으로 테스트로 덮을 수 있는 거의 유일한 길이었다.

이 네 가지가 *조용한 혁명* 이었다. *''mock 을 안 쓰는 게 답이다''* 라고 주장하던 진영조차도 *''쓸 거면 Mockito 가 낫다''* 로 돌아섰다.

---

## 3. London vs Detroit — Mockito 의 *철학적 위치*

TDD 진영은 **2000 년대 중반** 에 한 번 *학파로 갈렸다*.

| 학파 | 검증 대상 | 의존성 처리 | 대표자 |
|---|---|---|---|
| **London School** (Mockists) | *행위 (interaction)* | mock 으로 *전부 끊는다* | Steve Freeman, Nat Pryce |
| **Detroit School** (Classicists) | *상태 (state)* | 진짜 객체를 *최대한 쓴다* | Kent Beck, Martin Fowler |

Martin Fowler 의 2007 년 글 **Mocks Aren't Stubs** 는 이 두 학파의 *''싸움이 아닌 차이''* 를 정리한 고전이다.

- *London* 은 *''객체끼리 어떻게 *대화* 하는가''* 를 검증한다 — interface 설계가 정교해진다
- *Detroit* 는 *''최종 상태가 맞는가''* 를 검증한다 — refactor 에 *덜 깨진다*

**Mockito 는 *London 의 도구* 지만 *비명령적* 으로 쓸 수 있다.** `verify` 를 안 쓰고 `given … willReturn` 만 쓰면 사실상 *stub* 으로 동작한다. 이 *''원하는 만큼만 mockist 가 될 수 있다''* 가 Mockito 가 *양 진영 모두에게* 받아들여진 이유다.

### 3.1 Spring 환경의 *현실적 답*

Spring 진영의 일반적인 *합의* 는:

- *단위 테스트* — Mockito 로 의존성 전부 끊고 *순수 자바* 처럼 실행 (millisecond 단위)
- *슬라이스 테스트* — `@WebMvcTest`, `@DataJpaTest` 로 *부분 컨텍스트* 만 띄우고 나머지는 `@MockitoBean` 으로 채움 (second 단위)
- *통합 테스트* — `@SpringBootTest` + Testcontainers 로 *진짜 DB / 진짜 Kafka* 띄움 (10s+)

이 *피라미드* 의 *바닥* 을 Mockito 가 담당한다. *바닥이 빠르고 안정적이어야 위층이 의미를 가진다*.

---

## 4. Spring Boot 의 Mockito — `@MockBean` 에서 `@MockitoBean` 까지

Spring Boot 1.4 (2016) 에서 도입된 `@MockBean` 은 *Spring 진영의 Mockito 수용* 을 공식화한 어노테이션이었다.

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired MockMvc mvc;

    @MockBean OrderService orderService;   // ← Spring Boot 1.4 ~ 3.3

    @Test
    void 결제_API_200() throws Exception {
        given(orderService.place(any())).willReturn(OrderResult.success("tx-1"));

        mvc.perform(post("/orders").contentType(JSON).content("{...}"))
           .andExpect(status().isOk())
           .andExpect(jsonPath("$.txId").value("tx-1"));
    }
}
```

이게 의미하는 바는 *''Mockito 가 *Spring 의 표준 의존성* 으로 편입됐다''* 는 것. `spring-boot-starter-test` 에 *자동으로* 들어간다.

### 4.1 Spring Boot 3.4 (2024) — `@MockitoBean` 으로 *공식 위임*

Spring Boot 3.4 부터는 `@MockBean` 이 **deprecated** 되고 **`@MockitoBean`** 으로 바뀌었다. 이름이 *명확해진 것* 도 있지만 더 중요한 메시지는:

> *''Spring Framework 자체가 Mockito 통합을 *직접* 책임진다''*

기존 `@MockBean` 은 Spring Boot 모듈에 있었고 *Spring Framework 의 의존성* 이 아니었다. 3.4 부터는 Spring Framework 6.2 가 `org.springframework.test.context.bean.override.mockito.MockitoBean` 으로 *프레임워크 코어* 에 가져왔다. *Mockito 가 Spring 의 일급 시민이 된 셈* 이다.

```java
// Spring Boot 3.4+
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @MockitoBean OrderService orderService;   // ← 새로운 표준
    // @MockBean 도 한동안 동작하지만 deprecated
}
```

---

## 5. *과용* 의 함정 — Mockito 메인테이너도 경고하는 것들

Mockito 가 *너무 편하다* 보니 *과용* 의 함정에 빠지기 쉽다. 메인테이너 Szczepan Faber 본인도 *''Mockito 가 적게 쓰일수록 좋은 코드''* 라고 자주 말했다.

### 5.1 흉터 #1 — *남의 객체를 mock 하지 마라* (Don't mock what you don't own)

```java
// 안티 패턴 — Spring 의 ResponseEntity 를 mock
@Test
void 컨트롤러_응답_검증() {
    ResponseEntity<String> mockEntity = mock(ResponseEntity.class);
    given(mockEntity.getStatusCode()).willReturn(HttpStatus.OK);
    given(mockEntity.getBody()).willReturn("ok");
    // ...
}
```

이건 *두 가지* 가 문제다.

1. **Spring 이 ResponseEntity 의 동작을 바꾸면 *우리 테스트는 거짓 통과* 한다** — mock 이 실제 동작과 분기됨
2. **`ResponseEntity` 같은 *데이터 객체* 는 그냥 *진짜로* 만들어 쓰는 게 *훨씬 간결* 함**

> **원칙**: *우리가 인터페이스를 *소유* 한 것* 만 mock 한다. 외부 라이브러리의 클래스는 *진짜로 만들고*, 외부 *서비스* (HTTP, DB) 는 *Adapter 인터페이스* 를 우리가 만들어서 *그 인터페이스* 를 mock 한다.

### 5.2 흉터 #2 — *구현 세부* 를 검증하면 *refactor 가 깨진다*

```java
// 안티 패턴 — 호출 순서까지 검증
@Test
void 결제_플로우() {
    orderService.place(cmd);

    InOrder inOrder = inOrder(inventory, gateway, notifier);
    inOrder.verify(inventory).reserve(items);
    inOrder.verify(gateway).charge(1000);
    inOrder.verify(notifier).notify(any());
}
```

이런 테스트는 *''로직이 맞다''* 가 아니라 *''내가 *지금* 짠 순서대로 호출됐다''* 를 검증한다. 내일 *''결제를 먼저 하고 재고를 잡자''* 로 순서를 바꾸면 *비즈니스적으로 옳은 변경이 테스트를 깬다*.

> **원칙**: *검증해야 할 것은 *비즈니스 약속*, 검증하면 안 되는 것은 *구현 순서*. `InOrder` 가 필요한 경우는 *순서 자체가 비즈니스 요구* 일 때 (예: *반드시 결제 *전* 에 재고 잡기*) 뿐.

### 5.3 흉터 #3 — *Mock 의 늪에 빠진 단위 테스트*

가장 흔한 패턴:

```java
// 의존성이 7 개라서 mock 도 7 개...
@Mock A a; @Mock B b; @Mock C c; @Mock D d;
@Mock E e; @Mock F f; @Mock G g;

@Test
void 테스트() {
    given(a.do1()).willReturn(...);
    given(b.do2()).willReturn(...);
    given(c.do3()).willReturn(...);
    given(d.do4()).willReturn(...);
    // ... 30 줄의 given() ...

    sut.run();   // ← 한 줄

    // ... 30 줄의 verify() ...
}
```

이 *''mock 30 줄, 검증 30 줄, 실제 호출 한 줄''* 패턴이 보이면 *그건 단위 테스트의 문제가 아니라 *설계의 문제*. *의존성 7 개* 자체가 단일 책임 원칙 (SRP) 위반의 신호다.

> **원칙**: *Mock 이 많다는 건 *책임이 많다* 는 신호*. 테스트가 못생기면 *프로덕션 코드를 의심* 해라. TDD 의 *원래 목적* 으로 돌아오게 되는 지점.

---

## 6. *2026 년 현재* — 표준 스택과 권장 패턴

지금 자바 진영에서 *모범 답안* 으로 통하는 스택은:

```
JUnit 5         + AssertJ          + Mockito 5    + Spring Boot 3.4+
  ↓                ↓                  ↓               ↓
선언적 lifecycle   대화체 assertion    @MockitoBean    슬라이스 테스트
```

### 6.1 추천 *조합 패턴*

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock PaymentGateway gateway;
    @Mock InventoryRepository inventory;
    @InjectMocks OrderService sut;       // System Under Test

    @Test
    @DisplayName("재고가 부족하면 결제 호출 없이 OUT_OF_STOCK 을 반환한다")
    void 재고_부족_시_결제_안_함() {
        // given
        given(inventory.tryReserve(items))
            .willReturn(ReservationResult.outOfStock());

        // when
        var result = sut.place(new OrderCommand(1000, items));

        // then — *상태* 검증 (Detroit)
        assertThat(result.status()).isEqualTo(OUT_OF_STOCK);

        // and — *행위* 검증 (London) — *결제 호출이 *없었음* *
        then(gateway).should(never()).charge(anyLong());
    }
}
```

이 테스트는 *London 과 Detroit 를 모두* 활용한다.

- `assertThat(result.status())` 로 *최종 상태* 를 본다 (Classicist)
- `then(gateway).should(never())` 로 *행위가 없었음* 을 본다 (Mockist)

*''결제 안 한다''* 라는 비즈니스 약속은 *상태로는 표현 불가능* 하다 (결제가 실패해도, 결제 안 해도 상태는 같을 수 있다). 그래서 *행위 검증이 비즈니스적으로 필요한 지점* 에만 mock verify 를 쓴다.

### 6.2 *언제 Mockito 를 쓰지 말 것인가*

- **값 객체 (Value Object)** — `Money`, `OrderId` 같은 객체는 진짜로 만들어라. *new Money(1000)* 이 한 줄이다.
- **컬렉션** — `List`, `Map` 은 절대 mock 하지 마라. `List.of(...)` / `Map.of(...)` 가 훨씬 깔끔하다.
- **외부 HTTP 호출** — Mockito 대신 *WireMock* 이 답. *진짜 HTTP 통신* 을 *가짜 서버* 로 받는다. *직렬화/역직렬화 버그* 까지 잡힌다.
- **DB 호출** — *@DataJpaTest* + H2 또는 Testcontainers + 진짜 PostgreSQL. *쿼리 정확성* 은 mock 으로 잡을 수 없다.

> **2026 년의 공식** = **Mockito 는 *우리가 정의한 *Adapter 인터페이스*** 만 mock 한다. 그 너머의 *외부 시스템* 은 *진짜 흉내* 를 내는 도구로 넘긴다.

---

## 7. 정리 — *왜 Mockito 가 살아남았는가*

TDD 진영에서 *''mock 은 위험하다''* 는 비판은 *지금도 유효* 하다. 그럼에도 Mockito 가 자바 TDD 의 *표준* 으로 자리 잡은 이유는:

1. **사용하지 않아도 되는 자유** — `verify` 를 안 쓰면 stub 으로 동작. *London 강요가 없다*
2. **대화체 가독성** — `given / when / then` 이 *비즈니스 문장* 처럼 읽힌다
3. **legacy 와의 화해** — `spy` 로 *진짜 객체 + 일부 mock*. 한 번에 다 못 바꾸는 코드를 점진적으로 덮을 수 있다
4. **Spring 의 일급 통합** — `spring-boot-starter-test` 에 *자동 포함*, `@MockitoBean` 으로 *프레임워크 핵심* 진입

> *''Kent Beck 이 *빨강·초록·리팩토링* 으로 TDD 의 *방법론* 을 줬다면, Mockito 는 자바 진영의 *실행 가능성* 을 줬다.''*

*''테스트 먼저 쓰자''* 라는 한 문장이 2002 년에 출판되고 *24 년이 지난 지금* 도 살아 있는 건, 그 사이에 *''의존성을 어떻게 끊을 것인가''* 라는 *현실 문제* 를 풀어준 라이브러리들이 있었기 때문이다. Mockito 는 그 흐름의 *결정적 매듭* 이었다.

---

## 더 읽으면 좋은 글

- Kent Beck, **Test-Driven Development by Example** (2002) — *원전*
- Martin Fowler, **Mocks Aren't Stubs** (2007) — London/Detroit 의 *정리된 차이*
- Steve Freeman·Nat Pryce, **Growing Object-Oriented Software, Guided by Tests** (2009) — London school 의 *교과서*
- Mockito 공식 문서, **MockitoUsage** — *3 분 가이드*
- Spring Framework 6.2 Reference, **Bean Overriding for Tests** — `@MockitoBean` 의 *공식 위치*
