---
layout: post
title: "Harness Engineering ② Test Harness — JUnit/Mockito/Testcontainers, 그리고 *통합 테스트가 단위 테스트만큼 빨라지는* 비밀"
date: 2026-05-29 01:20:00 +0900
categories: [testing, backend]
tags: [harness, junit, mockito, testcontainers, spring-boot, integration-test, slice-test, fixture, archunit]
---

> "Harness Engineering 의 4 가지 얼굴" 시리즈의 2 편. [① AI Agent Harness]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %}) / [③ Software Engineering Harness]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %}) / [④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})

*Test Harness* 는 *테스트가 실행되는 environment 와 그것을 둘러싼 인프라*. 단위 테스트의 fixture, 통합 테스트의 컨테이너, mocking 라이브러리, 데이터 셋업 / 정리 / 격리, 병렬 실행 — 이 모든 게 *test harness*.

> "Test harness 가 잘 설계됐는가" 가 *그 팀이 테스트를 진심으로 쓰는가* 를 결정한다.

이 글은 Spring Boot 백엔드 기준으로 *production-grade test harness* 의 구성 요소와 흔한 함정을 정리한다.

---

## TL;DR — Test Harness 의 7 가지 구성요소

| # | 요소 | 도구 / 패턴 |
|---|---|---|
| 1 | Test Runner | JUnit 5 (`@Test`, `@ParameterizedTest`, `@RepeatedTest`) |
| 2 | Mocking | Mockito (`@Mock`, `@Spy`, `@Captor`, `mockStatic`) |
| 3 | Assertion | AssertJ (`assertThat(...).is...`) |
| 4 | Fixture | 빌더 패턴, ObjectMother, Factory |
| 5 | Integration | Testcontainers (Postgres/Kafka/Redis 실제 컨테이너) |
| 6 | Slice Test | `@WebMvcTest`, `@DataJpaTest`, `@JsonTest` |
| 7 | Architecture Test | ArchUnit (의존 방향, layer 강제) |

---

## 0. *왜* Test Harness 가 중요한가

"테스트는 작성하는 것" 이 아니라 "*작성하고 *매일* 돌리는* 것". 문제는:

- **느리면** → 안 돌림 (CI 만 돌림, 로컬은 패스)
- **flaky 하면** (가끔 실패) → 신뢰 안 함 → 무시
- **셋업이 복잡하면** → 새 테스트 안 만듦
- **mocking 이 지나치면** → *진짜 시스템과 다른* 통과 (production 사고)

좋은 test harness 는 *위 4가지를 막는 인프라*.

---

## 1. JUnit 5 — Test Runner 가 표준화한 것

JUnit 4 → 5 의 *진짜 변화* 는 *확장성*. `@ExtendWith` 로 어떤 동작이든 *주입* 가능.

```java
@ExtendWith({
    MockitoExtension.class,        // @Mock 활성화
    SpringExtension.class,         // Spring Context 통합
    TestcontainersExtension.class  // @Testcontainers 활성화
})
class OrderServiceTest {
    @Mock OrderRepository repo;
    @Container static PostgreSQLContainer<?> db = new PostgreSQLContainer<>("postgres:16");
}
```

세 라이브러리가 *한 테스트 클래스에 공존*. JUnit 4 였으면 `@RunWith` 가 *하나뿐* 이라 불가.

### `@ParameterizedTest` — 동일 로직, 다른 입력

```java
@ParameterizedTest
@CsvSource({
    "100, 0.1, 10",      // 10% 할인
    "100, 0.0, 0",        // 무할인
    "0,   0.5, 0",        // 0원 주문
    "100, 1.0, 100"       // 100% 할인 (edge)
})
void discount(int amount, double rate, int expected) {
    assertThat(calculator.discount(amount, rate)).isEqualTo(expected);
}
```

테이블 형식으로 *4개 시나리오* 를 한 메서드로. boilerplate 4배 절약.

---

## 2. Mockito — Mocking 의 표준

```java
@ExtendWith(MockitoExtension.class)
class PaymentServiceTest {
    @Mock PaymentGateway gateway;
    @InjectMocks PaymentService service;

    @Test
    void approves_payment_via_gateway() {
        // given
        given(gateway.charge(any())).willReturn(new ChargeResult("OK", "tx-123"));

        // when
        var result = service.pay(new PaymentRequest(10000, "card-1"));

        // then
        assertThat(result.status()).isEqualTo("APPROVED");
        verify(gateway).charge(argThat(req -> req.amount() == 10000));
    }
}
```

### `ArgumentCaptor` — 호출 인자 검증

```java
@Captor ArgumentCaptor<ChargeRequest> requestCaptor;

@Test
void captures_request() {
    service.pay(new PaymentRequest(10000, "card-1"));

    verify(gateway).charge(requestCaptor.capture());
    var captured = requestCaptor.getValue();
    assertThat(captured.amount()).isEqualTo(10000);
    assertThat(captured.cardId()).isEqualTo("card-1");
}
```

`verify(...argThat(...))` 보다 *복잡한 검증* 에 유용.

### `mockStatic` — 정적 메서드도 mocking

```java
@Test
void mocks_static_clock() {
    try (var mock = mockStatic(Clock.class)) {
        mock.when(Clock::systemUTC).thenReturn(Clock.fixed(Instant.parse("2026-05-29T00:00:00Z"), UTC));

        // 테스트
    }
}
```

`Clock.systemUTC()` 같은 *static method* 도 mocking. 단 *남용 위험* — 정적 의존이 많을수록 *테스트 가능성* 이 떨어진다는 신호.

### 흔한 함정: *과도한 mocking*

```java
// ❌ 안티패턴: 모든 의존 mocking
@Mock A a;
@Mock B b;
@Mock C c;
@Mock D d;
@Mock E e;  // 의존 5개 mocking → 진짜 코드 vs 테스트의 *2배 분량*
```

5개 이상 mocking 하면 *통합 테스트로 가야 할 신호*. Mock 은 *외부 시스템 (DB, HTTP, MQ)* 에만 쓰고, *내부 의존* 은 real object 로 가는 게 일반론.

---

## 3. AssertJ — Fluent Assertion

JUnit 의 `assertEquals(expected, actual)` 보다 *읽기 쉬움*:

```java
// 기본
assertThat(result).isEqualTo(expected);

// Collection
assertThat(orders)
    .hasSize(3)
    .extracting(Order::status)
    .containsExactly(APPROVED, APPROVED, FAILED);

// Optional
assertThat(repo.findById(1L))
    .isPresent()
    .get()
    .extracting(User::email)
    .isEqualTo("test@example.com");

// Exception
assertThatThrownBy(() -> service.pay(invalidRequest))
    .isInstanceOf(PaymentException.class)
    .hasMessageContaining("card expired");
```

`isInstanceOf` + `hasMessageContaining` 조합이 *exception 시나리오* 의 표준.

---

## 4. Fixture — 데이터 셋업의 *재사용성* 이 모든 것

같은 테스트 데이터를 *매 테스트마다* 새로 만들면 *지옥*. 표준 패턴 3가지:

### Builder

```java
public class OrderBuilder {
    private Long id = 1L;
    private String status = "PENDING";
    private BigDecimal amount = BigDecimal.valueOf(10000);

    public OrderBuilder id(Long id) { this.id = id; return this; }
    public OrderBuilder status(String s) { this.status = s; return this; }
    public OrderBuilder amount(BigDecimal a) { this.amount = a; return this; }

    public Order build() {
        return new Order(id, status, amount, Instant.now());
    }
}

// 테스트
var order = new OrderBuilder()
    .status("APPROVED")
    .amount(BigDecimal.valueOf(50000))
    .build();
```

*디폴트 + 부분 오버라이드*. 가장 일반적.

### Object Mother

```java
public class OrderMother {
    public static Order pending(BigDecimal amount) {
        return new Order(null, "PENDING", amount, Instant.now());
    }
    public static Order approvedFor(User user) {
        return new Order(null, "APPROVED", BigDecimal.valueOf(10000), Instant.now(), user.id());
    }
}

// 테스트
var order = OrderMother.approvedFor(testUser);
```

*시나리오 이름* (approvedFor, pending) 으로 *의도 명확*.

### Factory (DB 셋업)

```java
@Component
public class TestDataFactory {
    @Autowired UserRepository userRepo;
    @Autowired OrderRepository orderRepo;

    @Transactional
    public Order anApprovedOrder(BigDecimal amount) {
        var user = userRepo.save(UserMother.standard());
        return orderRepo.save(OrderMother.approvedFor(user, amount));
    }
}

// 통합 테스트
@Test
void test(@Autowired TestDataFactory factory) {
    var order = factory.anApprovedOrder(BigDecimal.valueOf(10000));
    // ...
}
```

DB 까지 채워서 *통합 테스트의 fixture* 로 사용.

---

## 5. Testcontainers — *진짜* 인프라로 통합 테스트

Mocking 의 *진짜 위험*: production 의 실제 DB / Kafka / Redis 와 *행동이 다름*. 통합 테스트는 *진짜 컨테이너* 로 해야 한다.

```java
@Testcontainers
@SpringBootTest
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> db = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("test")
        .withReuse(true);  // 컨테이너 재사용 → 속도 ↑

    @Container
    static KafkaContainer kafka = new KafkaContainer(
        DockerImageName.parse("confluentinc/cp-kafka:7.6.0"));

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", db::getJdbcUrl);
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
    }

    @Test
    void publishes_outbox_event_after_commit() {
        // 진짜 Postgres + Kafka 사용
    }
}
```

### `withReuse(true)` — 속도의 비밀

기본은 *매 테스트 클래스마다 새 컨테이너*. `withReuse(true)` + `~/.testcontainers.properties` 에 `testcontainers.reuse.enable=true` 설정 시:

- 첫 실행 시 컨테이너 띄움
- 두 번째부터 *기존 컨테이너 재사용*
- 컨테이너 시작 비용 (5~15초) 절약

*"통합 테스트가 단위 테스트만큼 빠르다"* 의 비밀이 이것.

### 컨테이너 데이터 격리

```java
@BeforeEach
void cleanDb(@Autowired JdbcTemplate jdbc) {
    jdbc.execute("TRUNCATE TABLE orders, payments, outbox CASCADE");
}
```

또는 `@Sql("/cleanup.sql")` 으로. *각 테스트 독립성* 유지.

---

## 6. Slice Test — *필요한 부분만* 띄우기

`@SpringBootTest` 는 *모든 빈* 로딩 → 느림. *부분 슬라이스* 만 띄우는 것이 빠름.

| 어노테이션 | 띄우는 것 | 용도 |
|---|---|---|
| `@WebMvcTest` | Controller + filter | Controller 단독 테스트 |
| `@DataJpaTest` | JPA Repository + H2 / Testcontainer | Repository 쿼리 테스트 |
| `@JsonTest` | Jackson configuration | DTO 직렬화 테스트 |
| `@RestClientTest` | RestTemplate / WebClient | 외부 HTTP 클라이언트 |

### 예시: `@WebMvcTest`

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvc mvc;
    @MockBean OrderService service;  // 외부 의존은 mock

    @Test
    void returns_200_on_valid_request() throws Exception {
        given(service.create(any())).willReturn(new OrderResponse(1L, "OK"));

        mvc.perform(post("/api/orders")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"amount": 10000, "userId": 1}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(1));
    }
}
```

전체 Spring context 안 띄움 → *대략 100ms* 내 시작 (`@SpringBootTest` 는 5~15초).

---

## 7. ArchUnit — 아키텍처 *컴파일러*

위에서 (DDD 글) 다룬 ArchUnit 의 이중 역할. *Test harness* 의 가장 *underrated* 한 구성요소.

```java
@AnalyzeClasses(packages = "com.lemuel.settlement")
class HexagonalArchitectureTest {

    @ArchTest
    static final ArchRule domain_no_spring =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAPackage("org.springframework..");

    @ArchTest
    static final ArchRule application_no_jpa =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAPackage("jakarta.persistence..");

    @ArchTest
    static final ArchRule adapter_no_cross_domain =
        noClasses().that().resideInAPackage("..adapter.out.persistence..")
            .should().dependOnClassesThat().resideInAPackage("..adapter.in..");
}
```

*Code review 가 아닌 컴파일러가* 헥사고날 위반을 reject. PR 시점에 *자동 차단*. settlement 가 이 패턴으로 *18개월 무사고* 유지.

---

## 8. 흔한 함정 5가지

### ❌ 함정 1: `@SpringBootTest` 남발

*모든 테스트* 를 `@SpringBootTest` 로 쓰면 *5초 × 1000 테스트 = 1.5 시간*. CI 가 멈춤. Slice test 로 분리.

### ❌ 함정 2: 테스트 간 *상태 공유*

```java
static List<Order> orders;  // ❌ 테스트 간 누수

@Test void a() { orders.add(...); }
@Test void b() { /* a 의 데이터 보임 */ }
```

테스트는 *완전 독립* 이어야. `@BeforeEach` 로 reset.

### ❌ 함정 3: Mock 으로 *DB 행동* 시뮬

```java
// ❌ Mock 으로 unique constraint 흉내
given(repo.save(any())).willThrow(DataIntegrityViolationException.class);
```

진짜 DB 의 *unique constraint 위반* 은 *Testcontainers* 로만 정확히 재현. Mock 으로 흉내 내면 *실제 행동과 다름*.

### ❌ 함정 4: *시간 의존* 테스트

```java
@Test void expires_after_24h() {
    var order = createOrder();
    Thread.sleep(86_400_000);  // ❌ 24시간 대기
    assertThat(service.isExpired(order)).isTrue();
}
```

`Clock` 을 주입 가능하게 만들어 *fake clock* 사용. `mockStatic(Clock.class)` 또는 `Clock` Bean.

### ❌ 함정 5: *flaky 테스트* 방치

가끔 실패하는 테스트는 *즉시 수정* 또는 *삭제*. 방치하면:
- 팀이 *재실행* 으로 우회
- *진짜 실패* 도 무시
- *테스트 신뢰* 가 무너짐

---

## 9. 내 settlement / lemuel-xr 의 test harness

| 영역 | 도구 / 패턴 |
|---|---|
| Unit test | JUnit 5 + Mockito + AssertJ |
| Integration test | Testcontainers (Postgres 16, Kafka) + `withReuse(true)` |
| Fixture | TestDataFactory (Spring Bean) + ObjectMother (static) |
| Slice test | `@DataJpaTest` (repository) + `@WebMvcTest` (controller) |
| Architecture test | ArchUnit (3 rules: domain/application/adapter) |
| Coverage | JaCoCo, line ≥ 80%, branch ≥ 70% gate |
| CI | GitHub Actions, 병렬 4 worker, *5분 내 전체 테스트 + ArchUnit + ECR 푸시* |

이 셋업이 *production-grade test harness 의 한 표준*. 어느 회사 가도 *비슷한 패턴* 으로 만나게 된다.

---

## 결론 — Test Harness 는 *문화*

좋은 test harness 가 있으면:
- *새 테스트 작성 비용* 이 낮음 → 자연스럽게 많이 짬
- *테스트 실행 비용* 이 낮음 → 매번 돌림
- *테스트 신뢰* 가 높음 → 통과하면 진심으로 안심
- *production 사고* 가 줄어듦

이게 *팀이 테스트를 진심으로 쓰는 회사 vs 그냥 흉내내는 회사* 의 차이. Junior 가 들어와서 *3 분 안에* 새 테스트 짤 수 있는 환경이 *진짜 test harness 가 잘 된 환경*.

다음 편: [③ Software Engineering Harness — 개발자 toolchain]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %})

---

## 참고

- *Growing Object-Oriented Software, Guided by Tests* — Freeman & Pryce (2009)
- [Testcontainers 공식 문서](https://testcontainers.com/)
- [Spring Boot Testing 가이드](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing)
- [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html)
- 시리즈 다른 편:
  - [① AI Agent Harness]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %})
  - [③ Software Engineering Harness]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %})
  - [④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
