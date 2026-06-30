---
layout: post
title: "*AI 코드 PR* 머지 전, *7 가지 질문* — *vibe coding 의 *마지막 게이트***"
date: 2026-06-21 00:50:00 +0900
categories: [ai, code-review, software-engineering, senior-engineer]
tags: [ai-coding, code-review, pr-review, vibe-coding, defensive-programming, senior-engineer, claude-code, copilot, secure-coding]
---

![AI 코드 PR 머지하기 전, 7 가지 질문](/assets/images/ai-pr-7-questions.jpg)
*AI 가 만든 코드의 PR 머지 전 던져야 할 7 가지 질문 — 신뢰할 수 없는 입력 / 동시 요청 / 경계값 / 외부 의존 다운 / 100만 건 데이터 / 도메인 규칙 / 로그·알람. **Rule of thumb**: "이게 운영에서 죽을 수 있는 5 가지 시나리오는?" — 머지 전 항상.*

> *"AI 가 *이 코드 짜 줬어요. *돌아가는 것 같아요. *머지 해도 될까요?"* — 2026 년 *팀 PR 의 가장 흔한 대화*.
>
> *돌아가는 것 같음* 과 *production 에서 *살아남음* 사이 의 *거리* 는 *AI 가 *알려주지 않는다*. *AI 는 *기쁜 경로 (happy path)* 의 *코드 를 *기쁘게 *생성* 하고 — *경계값 / 동시성 / 외부 의존 / 도메인 규칙 / 관측성* 의 *어두운 골목* 은 *명시적 으로 묻지 않으면* *대부분 *비어 있다*.
>
> 이 글은 *AI 가 생성한 코드 의 *PR 머지 전* *반드시 던져야 할 *7 가지 질문* — *vibe coding 시대 의 *마지막 게이트* — 을 *각자 *왜 *필요* 하고 *어디서 무너지는지 *Spring Boot 코드 *예시* 와 함께 *분해* 한다.
>
> 이 7 가지 가 *코드 리뷰 의 *전부* 가 아니라, *AI 가 *체계적 으로 *놓치는 영역* 의 *집중 점검*. *나머지 (네이밍, 아키텍처, 추상화 수준)* 는 *팀 의 *공통 어휘* 에서 다룬다.

내 *9 편 인프라 / 관측 / 보안 연작* 의 *후속 / 마무리* :
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *시큐어 코딩 섹션* 과 *직접 연결*
- [*K8s 의 유용성 — 온프레미스 vs 클라우드*](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)
- [*Prometheus + Grafana*](/2026/06/19/prometheus-grafana-metrics-visualization.html) — *질문 7 (로그/알람)* 의 *도구*
- [*I/O 병목*](/2026/06/18/io-bottleneck-how-to-solve.html) — *질문 5 (대용량 데이터)* 의 *물리*

이전 글 [*바이브 코딩 과 시니어 개발자 의 *7 가지 기준*](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html) 이 *직무 정의 의 거시 적 7 가지* 였다면, *이 글* 은 *코드 리뷰 시점 의 *미시 적 7 가지*. *짝* 의 글.

---

## TL;DR — *한 줄 결론*

> AI 가 *돌아가는 코드* 를 만든 후 *PR 에 올렸을 때*, *머지 전 7 가지 질문 을 *기계 적 으로 *던져라* :
> 1. *신뢰할 수 없는 입력* 이 *어디서 들어오나?*
> 2. *두 요청 이 *동시에 *오면* 어떻게 되나?*
> 3. *입력 이 *비거나 / null / 음수* 면 어떻게 되나?*
> 4. *외부 의존* 이 *죽으면* 우리 시스템 은?*
> 5. *데이터 가 *100만 건* 이 되면 어떻게 되나?*
> 6. *우리 도메인 규칙* 이 *명시되어 있나?*
> 7. *실패했을 때 *로그 / 알람* 으로 *알 수 있나?*
>
> 7 가지 모두 *AI 가 *명시적 으로 묻지 않으면* *대부분 *비어 있는 영역*. *PR 의 *vibe coding* 이 *production 에서 *살아남는 *유일한 길* 은 *이 7 가지 게이트 를 *기계 적 으로 *통과* 시키는 것*.
>
> **Rule of thumb** : *"이게 *운영 에서 죽을 수 있는 *5 가지 시나리오* 는?"* — 머지 전 *항상 *묻기*.

---

## 1. *왜 *이 질문 들이 *AI 시대 에 *더 중요* 한가*

### 1.1 *AI 의 *기쁜 경로 편향*

> *AI 는 *기쁜 경로* (happy path) 의 *코드 를 *압도 적으로 잘 짠다*. *그러나 *어두운 골목* 은 *명시적 으로 묻지 않으면 *대부분 비어 있다*.

```text
[Prompt] : "사용자 ID 로 주문 목록 조회 endpoint 만들어줘"
[AI 의 응답]:
  GET /orders?userId=42
  → DB 쿼리 → JSON 반환 ✓

[비어 있는 영역]:
  - userId 가 0 / -1 / null / 음수면? ✗
  - 동시에 100명이 호출하면? ✗
  - 주문이 100만 건이면? ✗
  - 다른 사용자 의 ID 넣으면 IDOR? ✗
  - DB 가 timeout 되면? ✗
  - 실패 로그 + 알람? ✗
```

→ *AI 는 *질문 받지 않은 영역* 의 *코드 를 *생성 하지 않는다*. *그 질문 을 *던지는 것 이 *시니어 의 일*.

### 1.2 *Junior 의 *3 종 함정*

| 함정 | 증상 |
|---|---|
| *"AI 가 만들었으니 검토할 필요 없겠지"* | *경계값 미체크, 보안 미체크, 관측성 부재* 의 PR 머지 |
| *"테스트 통과하면 OK"* | *AI 가 *자기 가 작성한 코드 의 *기쁜 경로 만 테스트*. 경계 / 동시성 안 테스트 |
| *"리뷰어 도 AI 한테 던지면 되겠지"* | *AI vs AI 의 *의미 없는 ping-pong*. *책임 의 *부재* |

→ *이 글 의 *7 가지 질문* 은 *AI 의 *기쁜 경로 편향* 의 *체계 적 대응*.

---

## 2. *질문 1 — *신뢰할 수 없는 입력 이 *어디서 들어오나?*

> *모든 입력 은 *적대적* 이라고 가정.

### 2.1 *AI 가 *자주 놓치는 패턴*

```java
// AI 가 자주 생성하는 안티 패턴
@PostMapping("/users")
public User create(@RequestBody UserRequest req) {
    User u = new User(req.getName(), req.getEmail());
    return userRepo.save(u);
}
// 문제 : *어떤 입력 검증 도 없음*. name 1MB, email 1KB, SQL injection 시도 다 통과
```

### 2.2 *3 가지 입력 경계*

| 경계 | 검증 도구 |
|---|---|
| *HTTP request body / query / path* | *Bean Validation (`@Valid`, `@NotBlank`, `@Email`, `@Size`)* |
| *외부 API 응답* | *DTO 검증 + 응답 schema 검증* |
| *파일 업로드* | *MIME type 화이트리스트 + magic number 검증, 크기 제한, virus scan* |

### 2.3 *최소 패턴*

```java
public record UserCreateRequest(
    @NotBlank @Size(min = 3, max = 50)
    @Pattern(regexp = "^[a-zA-Z0-9_가-힣 ]+$")  // 화이트리스트
    String name,

    @NotBlank @Email @Size(max = 254)
    String email,

    @Min(0) @Max(150)
    int age
) {}

@PostMapping("/users")
public User create(@Valid @RequestBody UserCreateRequest req) {
    return userService.create(req);
}
```

**핵심** :
- *화이트리스트* (`Pattern` 으로 허용 문자 만) — *블랙리스트 보다 안전*.
- *길이 / 범위 의 *상하한 모두 명시*.
- *Bean Validation 의 *자동 검증* — 실패 시 *400 응답*.

### 2.4 *외부 API 응답 도 입력*

```java
// 외부 API 응답 도 *신뢰 X*
public PaymentResponse callPaymentApi(PaymentRequest req) {
    PaymentResponse res = restClient.post()
        .body(req)
        .retrieve()
        .body(PaymentResponse.class);

    // ★ 추가 검증 필수
    if (res == null) throw new PaymentException("null response");
    if (res.getStatus() == null || !VALID_STATUSES.contains(res.getStatus()))
        throw new PaymentException("invalid status: " + res.getStatus());
    if (res.getAmount() < 0) throw new PaymentException("negative amount");
    return res;
}
```

> *외부 의존* 이 *bug 를 갖거나*, *해킹 당하거나*, *프로토콜 이 *변경 되면* — *우리 시스템 의 *신뢰 의 *가장 약한 고리*. *response schema 검증 의무*.

→ 더 깊이는 [*보안 의 7 기둥 — 시큐어 코딩 섹션*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html#82-injection--가장-흔한-단일-사고-원인) 참조.

---

## 3. *질문 2 — *두 요청이 동시에 오면 어떻게 되나?*

> *상태 를 *바꾸는 코드* 는 *모두 동시성 체크 대상*.

### 3.1 *AI 가 *자주 만드는 race condition*

```java
// AI 가 자주 생성하는 안티 패턴 — *카운트 증가*
@Transactional
public void increment(Long itemId) {
    Item item = itemRepo.findById(itemId).orElseThrow();
    item.setCount(item.getCount() + 1);   // ★ 동시 호출 시 *마지막 쓰기만 살아남음 (lost update)*
    itemRepo.save(item);
}

// 100 명이 동시에 호출 → 100 증가 기대 → 실제로는 *1~5 증가*
```

### 3.2 *3 가지 동시성 해결책*

#### **(1) DB-level — *낙관적 락 (Optimistic Lock)***

```java
@Entity
public class Item {
    @Id Long id;
    int count;

    @Version
    long version;   // JPA 가 자동 관리
}

// 동시 update 시 *version mismatch → ObjectOptimisticLockingFailureException*
// → 캐치 후 retry
@Retryable(ObjectOptimisticLockingFailureException.class)
@Transactional
public void increment(Long itemId) {
    Item item = itemRepo.findById(itemId).orElseThrow();
    item.setCount(item.getCount() + 1);
    itemRepo.save(item);
}
```

#### **(2) DB-level — *비관적 락 (Pessimistic Lock)***

```java
@Query("SELECT i FROM Item i WHERE i.id = :id")
@Lock(LockModeType.PESSIMISTIC_WRITE)   // SELECT ... FOR UPDATE
Item findByIdForUpdate(@Param("id") Long id);

@Transactional
public void increment(Long itemId) {
    Item item = itemRepo.findByIdForUpdate(itemId);  // row 잠금
    item.setCount(item.getCount() + 1);
    itemRepo.save(item);  // commit 시 잠금 해제
}
```

→ *잔액 / 재고 *같은 *돈 / 수량 의 *strict* 케이스 에서 *기본*.

#### **(3) Atomic 연산 — *DB 단 한 번 의 update***

```sql
UPDATE items SET count = count + 1 WHERE id = ?
```

```java
@Modifying
@Query("UPDATE Item i SET i.count = i.count + 1 WHERE i.id = :id")
int incrementById(@Param("id") Long id);
```

→ *DB 자체 가 *원자성 보장*. *가장 단순* 하고 *가장 빠름*. 가능 한 곳 에서 *최우선 선택*.

### 3.3 *체크리스트 — *상태 변경 코드* 인가?*

- 카운트 / 재고 / 잔액 / 점수 / 좌석 수 / 쿠폰 잔량
- 상태 전이 (PENDING → APPROVED)
- 비밀번호 / 토큰 변경
- 권한 / role 변경

→ **위 중 하나 라도 해당 하면 *반드시 동시성 검증***.

---

## 4. *질문 3 — *입력 이 *비거나 / null / 음수* 면?*

> *"정상" 입력 외 *경계 값* 을 *의식 적으로 *한 번 씩 *통과 시켜 봐라*.

### 4.1 *AI 가 *자주 놓치는 경계값*

```java
// AI 가 자주 생성하는 안티 패턴
public BigDecimal averagePrice(List<Order> orders) {
    BigDecimal sum = orders.stream()
        .map(Order::getPrice)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
    return sum.divide(BigDecimal.valueOf(orders.size()));  // ★ orders.size() == 0 이면 ArithmeticException
}
```

### 4.2 *6 가지 경계 — *항상 체크*

| 경계 | 예 |
|---|---|
| **빈 컬렉션** | `[]`, `Map{}`, `Set{}` |
| **null** | `null` 자체 + 컬렉션 안 의 *element 가 null* |
| **음수 / 0** | `-1`, `0` — *signed* 가 *unsigned 가정* 위반 |
| **최대값 overflow** | `Integer.MAX_VALUE + 1` → 음수 (silent wrap-around) |
| **이상한 문자열** | 빈 문자열, 공백 만, *유니코드 정규화* 이슈, *control char* |
| **이상한 날짜** | 윤년 2월 29일, *DST 변경 일*, *epoch 0*, *연 9999* |

### 4.3 *방어 코드*

```java
public BigDecimal averagePrice(List<Order> orders) {
    if (orders == null || orders.isEmpty()) {
        return BigDecimal.ZERO;   // 명시 적 의미 결정
    }
    BigDecimal sum = orders.stream()
        .map(Order::getPrice)
        .filter(Objects::nonNull)   // null element 도 방어
        .reduce(BigDecimal.ZERO, BigDecimal::add);
    return sum.divide(
        BigDecimal.valueOf(orders.size()),
        2, RoundingMode.HALF_UP    // ★ 반올림 모드 명시 — 안 하면 0.333... 시 ArithmeticException
    );
}
```

### 4.4 *Test 의 *경계값 의무*

```java
@Test
void averagePrice_빈_리스트_0() {
    assertThat(svc.averagePrice(List.of())).isEqualByComparingTo("0");
}

@Test
void averagePrice_null_원소_무시() {
    List<Order> orders = Arrays.asList(
        new Order("100"), null, new Order("200")
    );
    assertThat(svc.averagePrice(orders)).isEqualByComparingTo("150");
}

@Test
void averagePrice_음수_가격_인정_여부_명시() {
    // ★ 도메인 규칙: 음수 가격 허용? 또는 throw?
}
```

→ *AI 의 *unit test* 가 *기쁜 경로 만* 가지면 *반드시 *경계값 테스트 *추가 요청*.

---

## 5. *질문 4 — *외부 의존 이 *죽으면* 우리 시스템 은?*

> *결제, 메일, 외부 API* — *그들이 *죽으면* *우리 가 *함께 죽지 *말아야 한다*.

### 5.1 *AI 가 *자주 만드는 *무방어 호출*

```java
// AI 가 자주 생성하는 안티 패턴
public Order createOrder(OrderRequest req) {
    Order order = orderRepo.save(new Order(req));
    paymentClient.charge(req.getPaymentInfo());      // ★ timeout 없음, 재시도 없음
    emailClient.sendConfirmation(req.getEmail());    // ★ 같은 문제
    smsClient.sendCode(req.getPhone());              // ★ 같은 문제
    return order;
}
// 문제: paymentClient 가 30초 hang → 모든 요청 thread 가 30초 잠김 → thread pool 고갈
//       emailClient 가 down → 주문 자체 실패 (상관 없는 두 일이 묶임)
```

### 5.2 *4 가지 방어 도구 (Resilience4j 기반)*

#### **(1) Timeout**

```yaml
resilience4j.timelimiter:
  instances:
    paymentClient:
      timeoutDuration: 3s   # 3초 안 응답 → TimeoutException
      cancelRunningFuture: true
```

```java
@TimeLimiter(name = "paymentClient")
public CompletableFuture<PaymentResult> charge(PaymentInfo info) {
    return CompletableFuture.supplyAsync(() -> paymentClient.charge(info));
}
```

#### **(2) Retry — *with backoff***

```yaml
resilience4j.retry:
  instances:
    paymentClient:
      maxAttempts: 3
      waitDuration: 500ms
      enableExponentialBackoff: true
      exponentialBackoffMultiplier: 2
      retryExceptions:
        - java.net.SocketTimeoutException
        - org.springframework.web.client.ResourceAccessException
```

> **함정** : *멱등 (idempotent) 보장 없이 retry 하면 *중복 결제*. *retry 전 *Idempotency-Key 헤더* 의무.

#### **(3) Circuit Breaker — *상대 가 *죽었으면 *시도 중단*

```yaml
resilience4j.circuitbreaker:
  instances:
    paymentClient:
      slidingWindowSize: 10
      failureRateThreshold: 50    # 50% 실패 시 OPEN
      waitDurationInOpenState: 30s
      permittedNumberOfCallsInHalfOpenState: 3
```

→ *상대 가 죽었으면 *내가 *추가 부하 안 줌* + *내 thread pool 보호*.

#### **(4) Bulkhead — *자원 격리***

```yaml
resilience4j.bulkhead:
  instances:
    paymentClient:
      maxConcurrentCalls: 10   # 동시 최대 10 호출
```

→ *external call 의 *thread 폭증* 이 *다른 처리* 를 *죽이지 않게*.

### 5.3 *Async 분리 — *주문 과 *알림 분리*

```java
public Order createOrder(OrderRequest req) {
    Order order = orderRepo.save(new Order(req));

    // 결제 — 동기 (필수)
    paymentService.charge(order);

    // 알림 — *비동기* (실패 해도 주문 은 살아있음)
    notificationOutbox.publishOrderCreated(order);  // outbox pattern

    return order;
}
```

→ [*Transactional Outbox 패턴*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) 으로 *외부 호출 의 *실패 가 *비즈니스 트랜잭션 을 *오염 시키지 않게*.

---

## 6. *질문 5 — *데이터 가 *100만 건 이 되면 어떻게 되나?*

> *현재 의 *행복한 N=10* 이 *1년 후 N=1M* 될 때 *터지지 않는가*.

### 6.1 *AI 가 *자주 만드는 N+1 / 메모리 폭탄*

```java
// 안티 — N+1 쿼리
public List<UserSummary> getAllUsers() {
    return userRepo.findAll().stream()
        .map(u -> new UserSummary(
            u.getName(),
            u.getOrders().size(),    // ★ lazy load → 각 user 마다 *별도 쿼리*
            u.getReviews().size()    // ★ 또 별도 쿼리
        ))
        .toList();
}
// 100만 user → 300만 쿼리 → 응답 5분
```

```java
// 안티 — 메모리 폭탄
public BigDecimal totalRevenue() {
    return orderRepo.findAll().stream()  // ★ 100만 row 메모리 로드
        .map(Order::getAmount)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
}
```

### 6.2 *4 가지 해결책*

#### **(1) JOIN FETCH / @EntityGraph**

```java
@EntityGraph(attributePaths = {"orders", "reviews"})
List<User> findAll();
// 1 쿼리 로 모두 가져옴
```

→ 더 깊이는 [*I/O 병목 — 패턴 2 N+1 쿼리*](/2026/06/18/io-bottleneck-how-to-solve.html#4-패턴-2--n1-쿼리-orm-의-가장-흔한-함정) 참조.

#### **(2) Pagination**

```java
@GetMapping("/users")
public Page<User> list(Pageable pageable) {
    return userRepo.findAll(pageable);   // *기본 size 20, max 100 강제*
}
```

#### **(3) Aggregation — *DB 에 위임***

```sql
-- 안티: 100만 row 가져와서 Java 에서 sum
-- 좋음: DB 가 sum
SELECT SUM(amount) FROM orders WHERE created_at >= ?
```

#### **(4) Streaming / Cursor**

```java
@Query("SELECT o FROM Order o ORDER BY o.id")
Stream<Order> streamAll();   // *전체 메모리 로드 안 함*

@Transactional(readOnly = true)
public BigDecimal totalRevenue() {
    try (Stream<Order> stream = orderRepo.streamAll()) {
        return stream
            .map(Order::getAmount)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
```

### 6.3 *루프 안 의 *await / DB 호출* 의무 체크*

```java
// 안티
for (Long userId : userIds) {  // 1000 명
    User u = userRepo.findById(userId);     // ★ DB 1000 회
    u.setStatus("ACTIVE");
    userRepo.save(u);                        // ★ DB 1000 회
}

// 좋음
List<User> users = userRepo.findAllById(userIds);  // 1 회
users.forEach(u -> u.setStatus("ACTIVE"));
userRepo.saveAll(users);                            // batch
```

→ **루프 안 의 *I/O 는 *적색 신호*. *batch 또는 *async parallel* 로 변환 의무*.

---

## 7. *질문 6 — *우리 도메인 규칙* 이 *명시되어 있나?*

> *"환불", "할인", "인증" 같은 *단어* 는 *회사 마다 *정의 가 다르다*. *AI 는 *일반 적인 의미* 로 *코드 짠다*.

### 7.1 *대표 함정 — *환불 의 의미*

```text
[당신 회사 의 환불 규칙]
- 결제 후 7 일 이내 — 전액 환불
- 7~30 일 — 90% 환불 (10% 결제 수수료)
- 30 일 이후 — 환불 불가
- 단, *프리미엄 회원* 은 *60 일 까지 전액*
- 단, *promotion 으로 *구매* 한 상품 은 *환불 불가*

[AI 가 짠 코드]
public void refund(Order o) {
    paymentService.refundFull(o);    // ★ 모든 케이스 전액 환불
}
```

→ *AI 는 *환불 = 전액 환불* 이라는 *일반 적 가정* 으로 코드 짠다. *당신 회사 의 *세밀한 규칙* 은 *직접 명시 안 하면 안 들어감*.

### 7.2 *도메인 규칙 의 *명시화 의무*

PR 리뷰 체크 :

1. *주석 또는 javadoc* 으로 *비즈니스 규칙 명시* 되어 있나?
2. *테스트 가 *비즈니스 케이스 별 *분리* 되어 있나?
3. *enum / value object* 가 *규칙 의 *의미* 를 *코드 로 *말하고 있나?

```java
public enum RefundPolicy {
    FULL_REFUND_WITHIN_7DAYS(7, BigDecimal.ONE),
    PARTIAL_REFUND_WITHIN_30DAYS(30, new BigDecimal("0.90")),
    NO_REFUND_AFTER_30DAYS(30, BigDecimal.ZERO);

    private final int dayLimit;
    private final BigDecimal refundRate;

    public BigDecimal calculate(Order order, MemberTier tier) {
        if (order.isPromotional()) return BigDecimal.ZERO;
        int daysSincePurchase = order.daysSincePurchase();

        // 프리미엄 회원 60일 까지 전액
        if (tier == MemberTier.PREMIUM && daysSincePurchase <= 60) {
            return order.getAmount();
        }
        // 일반 정책
        ...
    }
}
```

→ *enum / value object* 가 *비즈니스 규칙 의 *살아있는 문서*. *코드 자체 가 *spec*.

### 7.3 *DDD 의 *Ubiquitous Language*

> *Eric Evans 의 *Domain-Driven Design* 의 *핵심 메시지* — *"개발자 와 도메인 전문가 가 *같은 단어 를 *같은 의미 로 *써야 한다"*.

- *주문* — *결제 완료* 인가, *carting* 인가, *fulfillment* 인가?
- *고객* — *user* 와 *customer* 의 차이는?
- *완료* — *결제 완료* / *배송 완료* / *리뷰 완료* 의 *어느 것*?

→ *코드 의 *클래스 / 메서드 명* 이 *도메인 어휘* 와 *일치* 해야. *AI 는 *영어 일반 명칭* 으로 *대충 명명* 함. *PR 시 *우리 도메인 어휘* 로 *수정 의무*.

---

## 8. *질문 7 — *실패 했을 때 *로그 / 알람* 으로 알 수 있나?*

> *silent fail 이 *가장 위험 하다*. *에러 를 *살리지 않고 *보이게 *하라*.

### 8.1 *AI 가 *자주 만드는 *silent fail*

```java
// 안티 — exception 잡고 swallow
public void sendNotification(User u) {
    try {
        emailClient.send(u.getEmail(), "Welcome");
    } catch (Exception e) {
        // ★ 아무것도 안 함 — 영원 히 모름
    }
}

// 안티 — 로깅 만 하고 *알람 없음*
public void process(Event e) {
    try {
        ...
    } catch (Exception ex) {
        log.error("failed: {}", ex.getMessage());   // ★ 메시지만, *stack trace 없음*
        // *알람 도 없음* — 새벽에 100 회 실패 해도 *아무도 모름*
    }
}
```

### 8.2 *4 가지 좋은 패턴*

#### **(1) Structured Logging — *기계 읽기 가능***

```java
log.error("notification send failed",
    kv("user_id", u.getId()),
    kv("email", maskEmail(u.getEmail())),
    kv("attempt", attempt),
    kv("exception", ex.getClass().getSimpleName()),
    ex);   // ★ stack trace 전체
```

→ *JSON 으로 출력* → Loki / ELK 에서 *user_id 별 검색 가능*.

#### **(2) Metric 등록 — *알람 발사*

```java
@Component
public class NotificationMetrics {
    private final Counter failures;

    public NotificationMetrics(MeterRegistry registry) {
        this.failures = Counter.builder("notification.failures")
            .tag("type", "email")
            .register(registry);
    }

    public void onFailure() { failures.increment(); }
}

// alert rule
- alert: HighNotificationFailureRate
  expr: rate(notification_failures_total[5m]) > 1
  for: 5m
```

→ [*Prometheus + Grafana — 알림 패턴*](/2026/06/19/prometheus-grafana-metrics-visualization.html#8-알람-alertmanager--예방-의-마지막-층) 참조.

#### **(3) Re-throw 또는 *명시적 fallback***

```java
public void sendNotification(User u) {
    try {
        emailClient.send(u.getEmail(), "Welcome");
    } catch (TransientException e) {
        // *재시도 큐* 에 넣어 비동기 재처리
        retryQueue.enqueue(u);
        log.warn("notification deferred", kv("user_id", u.getId()));
    } catch (PermanentException e) {
        // *실패 알림* — 운영자 가 봐야 함
        log.error("notification permanent failure",
            kv("user_id", u.getId()), e);
        failureMetrics.increment();
    }
}
```

→ *어떤 실패는 *재시도*, *어떤 실패는 *영구 (포기)*. 그러나 *둘 다 *명시적 로깅 + 알람*.

#### **(4) Outbox 패턴 — *영구 손실 방지*

[*Transactional Outbox*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) 로 *알림 / 외부 호출 의 *at-least-once* 보장 + 실패 시 *DLQ (Dead Letter Queue)*. *조용히 사라지는 메시지 0*.

### 8.3 *Silent fail 의 *식별*

PR 리뷰 시 *식별 기준* :

- `catch (Exception e) {}` 또는 `catch (Throwable t) {}` 의 *빈 블록*.
- `e.printStackTrace()` 만 있고 *log 없음* (production 에서 *어디로 출력 됐는지 *모름*).
- *exception 잡고 *return null* / *return false* — 호출자 가 *왜 실패 했는지 모름*.
- *로깅 만 하고 *return* — 상위 호출자 가 *성공 으로 인식*.

→ **catch 블록 마다 *반드시 *log + (재시도 or 알람 or rethrow)*** 3 중 하나.

---

## 9. *Rule of Thumb — *5 가지 *운영 죽을 시나리오*

> *머지 전 *항상 묻기* : *"이 코드 가 *운영 에서 죽을 수 있는 *5 가지 시나리오 는?"*

### 9.1 *5 가지 *상상 시나리오*

1. **트래픽 spike** — 평소 의 *10x 트래픽* 이 *오면? rate limit? circuit breaker? autoscale?*
2. **DB 다운** — *DB 가 *10 초 hang* 또는 *완전 down* 되면? *connection pool 고갈, 어떻게 회복?*
3. **외부 의존 변경** — *외부 API 가 *response schema 변경* 했다면? *명시적 검증 으로 *알 수 있나?*
4. **악의적 사용자** — *공격자 가 *SQL injection, XSS, IDOR, brute force 시도* 하면 *어디서 잡히나?*
5. **데이터 증가** — *1년 후 데이터 가 *100배 면 *어디서 *처음 *터지나?*

> *이 5 가지 를 *명시적 으로 *답할 수 없으면* *PR 머지 *보류*.

### 9.2 *5 가지 의 *체크 위치*

| 시나리오 | 1차 방어 | 2차 방어 |
|---|---|---|
| 트래픽 spike | rate limit (Resilience4j) | autoscale (K8s HPA) |
| DB 다운 | connection timeout + circuit breaker | read replica fallback |
| 외부 변경 | response schema 검증 | contract testing (Pact) |
| 악의적 사용자 | input validation + RBAC | WAF, audit log |
| 데이터 증가 | pagination + index | DB partition / sharding |

---

## 10. *통합 — *PR 머지 체크리스트* — *15 가지*

내가 *AI 가 생성한 PR* 머지 전 *기계적 으로 *확인* 하는 *15 가지* :

**입력 / 검증**:
1. *모든 controller endpoint 에 `@Valid` + Bean Validation* 있는가
2. *외부 API 응답 의 *schema 검증* 있는가
3. *파일 업로드 의 *MIME / 크기 / magic number 검증* 있는가

**동시성**:
4. *상태 변경 코드 에 *동시성 제어 (낙관/비관/atomic update)* 있는가
5. *retry 가 *멱등성 보장* 되는가

**경계값**:
6. *빈 컬렉션 / null / 음수 / 0 / overflow* 케이스 *test 있는가*

**외부 의존**:
7. *외부 호출 에 *timeout + retry + circuit breaker* 있는가
8. *bulkhead 로 *thread pool 격리* 되었는가
9. *외부 실패 가 *비즈니스 트랜잭션 을 *오염 안 시키는가* (outbox)

**데이터 증가**:
10. *루프 안 *I/O / DB 호출 없는가*
11. *N+1 쿼리 없는가 (테스트 검증)*
12. *대용량 listing 에 *pagination* 있는가

**도메인**:
13. *비즈니스 규칙 이 *enum / value object* 로 *명시* 되는가
14. *PR description 에 *도메인 규칙* 의 *링크 / 인용* 있는가

**관측성**:
15. *catch 블록 마다 *log + metric / re-throw / 재시도* 의 *명시적 분기* 있는가

---

## 11. *결론 — *AI 코드 의 *기쁜 경로 편향* 의 *체계적 대응*

> *AI 가 *돌아가는 코드* 를 만든다*. *그 코드 가 *production 에서 *살아남는지* 는 *우리 가 *7 가지 질문* 으로 *검증 했는지* 에 달려있다.

오늘 정리한 *7 가지 질문* :
1. *신뢰할 수 없는 입력* 이 어디서 들어오나?
2. *동시 요청* 이 *오면* 어떻게?
3. *경계값* (빈/null/음수/overflow)?
4. *외부 의존* 이 죽으면?
5. *데이터 가 *100만 건* 이 되면?
6. *도메인 규칙* 이 *명시* 되어 있나?
7. *실패 가 *로그 / 알람* 으로 보이나?

> *7 가지 모두 *AI 의 *명시 적 질문 없이* *비어있는 영역*. *PR 리뷰어 의 *시니어 가치* 는 *그 *비어있는 영역* 을 *기계적 으로 *체크* 하는 *책임*.

*AI 가 *junior 수준 코드 의 *생산* 을 *자동화* 한 시대 에는, *senior 의 *상대적 가치* 가 *7 가지 게이트 의 *책임* 으로 *집약*. *그게 *vibe coding 시대 의 *시니어 개발자 의 *코드 리뷰 의 *진짜 일*.

*매일 매 PR 마다 *7 가지* 를 *기계 적 으로 묻는 것* — *그 *훈련* 이 *팀 의 *production 사고 비율* 을 *체감 적으로 낮춘다*. *그리고 *그 훈련* 이 *주니어 도 *AI 도 *시간 이 지나면서 *내재화* 한다*.

*"이 코드 가 *운영 에서 죽을 수 있는 *5 가지 시나리오 는?"* — *PR 머지 직전 *마지막 한 줄* 의 질문. *그 한 줄* 이 *팀 의 *cultural anchor*. *AI 가 *어떤 코드 를 *짜더라도* *그 한 줄 이 *남아 있는 한* *production 은 *살아남는다*.

---

## *참고*

- *Eric Evans*, *Domain-Driven Design: Tackling Complexity in the Heart of Software*.
- *Michael Nygard*, *Release It!: Design and Deploy Production-Ready Software*, 2nd ed. — *5 가지 시나리오 사고 의 *원전*.
- *OWASP Top 10 — 2021*, [owasp.org/Top10/](https://owasp.org/Top10/) — *질문 1, 2, 7 의 근거*.
- *Resilience4j 공식 문서* — *질문 4 의 도구*.
- *Spring Boot Testing Reference* — *경계값 test*.
- 자매편 :
  - [*바이브 코딩 과 시니어 개발자 의 7 가지 기준*](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html) — *직무 정의 의 *거시 적 짝*
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *질문 1, 2 의 *보안 적 깊이*
  - [*I/O 병목*](/2026/06/18/io-bottleneck-how-to-solve.html) — *질문 5 의 *물리적 근거*
  - [*Prometheus + Grafana*](/2026/06/19/prometheus-grafana-metrics-visualization.html) — *질문 7 의 *알람 도구*
  - [*Transactional Outbox*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) — *질문 4 의 *비동기 안전성*
