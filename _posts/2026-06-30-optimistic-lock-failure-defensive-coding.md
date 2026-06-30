---
layout: post
title: "낙관적 락 실패 를 *어떻게 막을 것인가* — 14 개월 운영 으로 정리한 방어 코드"
date: 2026-06-30 15:30:00 +0900
categories: [backend, jpa, concurrency, spring]
tags: [optimistic-lock, jpa, hibernate, version, retry, resilience4j, idempotency, spring-retry, settlement]
---

낙관적 락 은 *충돌 이 드물 다* 는 *가정* 의 *동시성 전략*. 그러나 *production 의 *현실* — *동시 요청 의 *몇 % 가 *반드시 *충돌*. 그 때 *코드 가 어떻게 반응 하는지* 가 *시스템 의 *진짜 품질*. *기능 구현* 의 *반대 편* — *실패 의 *우아 한 처리*.

이 글은 *settlement 의 SKU (ProductVariant) 에 *@Version + 100 쓰레드 동시성 테스트* 의 *14 개월 운영* 경험 위에서 *방어 코드 의 *7 가지 패턴* 의 *현실 가이드*.

---

## 1. 낙관적 락 의 *진짜 작동*

```java
@Entity
class ProductVariant {
    @Id Long id;
    private Integer stock;

    @Version
    private Long version;
}
```

`@Version` 의 *진짜 의미* — *UPDATE 시 *WHERE 절 에 version 자동 추가*. Hibernate 의 *생성 SQL*:

```sql
UPDATE product_variant 
SET stock = ?, version = version + 1
WHERE id = ? AND version = ?
```

*동시 2 개 트랜잭션* 이 *같은 id* 를 *읽고 *수정 하면* — *둘 다 같은 version* 으로 *UPDATE 시도* → *먼저 commit 한 것 만 *성공*, *두 번 째 는 *affected_rows = 0* → Hibernate 가 `OptimisticLockException` 발생.

```
tx1: SELECT id=1, version=5
tx2: SELECT id=1, version=5
tx1: UPDATE ... WHERE id=1 AND version=5  → version=6, 성공
tx2: UPDATE ... WHERE id=1 AND version=5  → affected=0, 실패
```

→ *충돌 의 *자동 검출*. *DB lock 없음* + *동시성 처리량 *높음*. *대가* — *충돌 시 *어떻게 처리* 의 *책임 이 *애플리케이션 측*.

---

## 2. 실패 의 *3 가지 시그널*

JPA / Spring Data 의 *예외 위계*:

```
DataAccessException (Spring)
└── OptimisticLockingFailureException
    ├── ObjectOptimisticLockingFailureException (id + entity class)
    └── StaleObjectStateException (Hibernate)

PersistenceException (JPA)
└── OptimisticLockException (Jakarta)
```

```java
try {
    productVariantRepo.save(variant);
} catch (ObjectOptimisticLockingFailureException e) {
    // Spring의 wrapper — 가장 흔히 잡음
    log.warn("Optimistic lock conflict on {}", e.getIdentifier());
}
```

⚠️ **함정** — `OptimisticLockException` 은 *flush 시점 에 던져짐*. *@Transactional 메서드 *내부 에서 catch* 하면 *commit 이 일어나기 전 의 시점* — *flush 가 *transaction commit 시 발생* 하면 *catch 못 함*.

**해결** — `entityManager.flush()` 명시 호출 또는 *Outer transaction 에서 catch*.

---

## 3. 패턴 1 — *재시도 (Retry) 의 *4 가지 구현*

낙관적 락 의 *흔한 응답* — *재시도*. *낮은 충돌 률* 의 *가정 위* 에서 *재시도 1~3 회* 면 *대부분 성공*.

### (1) Spring Retry — *AOP 기반*
```xml
<!-- build.gradle -->
implementation 'org.springframework.retry:spring-retry'
implementation 'org.springframework:spring-aspects'
```

```java
@EnableRetry
@Configuration
class RetryConfig {}

@Service
class StockService {

    @Retryable(
        retryFor = ObjectOptimisticLockingFailureException.class,
        maxAttempts = 3,
        backoff = @Backoff(delay = 50, multiplier = 2, random = true)
    )
    @Transactional
    public void decreaseStock(Long variantId, int quantity) {
        ProductVariant v = repo.findById(variantId).orElseThrow();
        v.decreaseStock(quantity);   // ← @Version 자동 증가
        repo.save(v);
    }

    @Recover
    public void recover(ObjectOptimisticLockingFailureException e, 
                        Long variantId, int quantity) {
        log.error("Stock decrease failed after 3 retries: {}", variantId);
        throw new StockUpdateFailedException(variantId);
    }
}
```

→ *깔끔 함*. *재시도 + backoff + recover 가 *애너테이션 만으로*.

**핵심** — `@Transactional` 이 *@Retryable 안쪽* 에 위치. *재시도 마다 *새 트랜잭션* 이 *새 SELECT + 새 version 읽기*.

### (2) Resilience4j — *코드 기반*
```java
@Service
@RequiredArgsConstructor
class StockService {
    private final Retry retry = Retry.of("stock-update",
        RetryConfig.<Void>custom()
            .maxAttempts(3)
            .waitDuration(Duration.ofMillis(50))
            .retryOnException(ObjectOptimisticLockingFailureException.class::isInstance)
            .build());

    public void decreaseStock(Long variantId, int quantity) {
        Retry.decorateRunnable(retry, () -> 
            doDecrease(variantId, quantity)
        ).run();
    }

    @Transactional
    protected void doDecrease(Long variantId, int quantity) {
        ProductVariant v = repo.findById(variantId).orElseThrow();
        v.decreaseStock(quantity);
        repo.save(v);
    }
}
```

→ *Spring Retry 와 동등*. *추가 의존성 없음* (이미 Circuit Breaker / Bulkhead 쓰는 프로젝트 면 *통합 자연*).

### (3) 수동 루프 — *명시 적 제어*
```java
public void decreaseStock(Long variantId, int quantity) {
    int attempt = 0;
    int maxAttempts = 3;

    while (true) {
        try {
            doDecreaseInNewTx(variantId, quantity);
            return;
        } catch (ObjectOptimisticLockingFailureException e) {
            if (++attempt >= maxAttempts) {
                throw new StockUpdateFailedException(variantId, e);
            }
            sleepWithJitter(50, attempt);
        }
    }
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
protected void doDecreaseInNewTx(Long variantId, int quantity) {
    ProductVariant v = repo.findById(variantId).orElseThrow();
    v.decreaseStock(quantity);
    repo.save(v);
}

private void sleepWithJitter(long baseMs, int attempt) {
    long jitter = ThreadLocalRandom.current().nextLong(baseMs);
    try {
        Thread.sleep(baseMs * (1L << (attempt - 1)) + jitter);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new RuntimeException(e);
    }
}
```

→ *프레임워크 없이 *완전 제어*. *디버깅 의 *투명 성*. *production 의 *fine-tuning 필요 한 hot path 에 적합*.

### (4) @Transactional 경계 — *흔한 함정*
```java
@Service
class StockService {
    
    @Retryable(...)          // ← AOP 1
    @Transactional           // ← AOP 2
    public void decreaseStock(...) {  // ← 같은 메서드
        ...
    }
}
```

⚠️ **순서 의 함정** — *Spring AOP 의 *애너테이션 처리 순서*. `@Transactional` 이 *바깥* 이면 *재시도 가 *같은 트랜잭션* 안에서 발생 → *항상 stale version 으로 *영원 실패*.

**해결** — *분리*:
```java
@Service
class StockService {
    @Autowired private TransactionalStockService txService;

    @Retryable(...)
    public void decreaseStock(...) {
        txService.doDecrease(...);   // ← 새 트랜잭션
    }
}

@Service
class TransactionalStockService {
    @Transactional
    public void doDecrease(...) { ... }
}
```

또는 *Spring Retry 의 *@Retryable 이 @Transactional 보다 *바깥 (높은 priority)* 가 *기본 동작* — *Spring Boot 의 *@EnableRetry 가 *적절 한 order 보장*.

---

## 4. 패턴 2 — *충돌 률 의 *모니터링*

재시도 의 *횟수 / 성공 률* 의 *추적 의무*. *Micrometer + Prometheus*:

```java
@Service
@RequiredArgsConstructor
class StockService {
    private final MeterRegistry registry;

    @Retryable(...)
    @Transactional
    public void decreaseStock(Long variantId, int quantity) {
        registry.counter("stock.decrease.attempt", 
                "variant", variantId.toString()).increment();
        ...
    }

    @Recover
    public void recover(ObjectOptimisticLockingFailureException e, 
                        Long variantId, int quantity) {
        registry.counter("stock.decrease.exhausted").increment();
        throw new StockUpdateFailedException(variantId);
    }
}
```

```promql
# Grafana — *충돌 률*
rate(stock_decrease_attempt_total[5m]) / 
  rate(stock_decrease_success_total[5m])
```

→ *충돌 률 이 *> 10% 지속* 이면 *Pessimistic 으로 전환 검토*. *내 클러스터 의 *settlement* — *< 1% 유지*.

---

## 5. 패턴 3 — *멱등성 (Idempotency)* 와 *결합*

재시도 의 *전제 조건* — *멱등성*. *같은 입력 의 *N 회 실행* 이 *같은 결과*.

### 위험 한 패턴
```java
@Retryable(...)
@Transactional
public void chargeAndDeduct(Long userId, Long productId, int qty) {
    paymentService.charge(userId, totalAmount);   // ← 외부 PG 호출
    stockService.decrease(productId, qty);         // ← @Version
}
```

⚠️ *재시도 시 *결제 가 *2 번 발생*. PG 의 *멱등성 키 없으면 *2 회 청구*.

### 안전 한 패턴
```java
@Retryable(...)
@Transactional
public void chargeAndDeduct(Long userId, Long productId, int qty, 
                             String idempotencyKey) {
    Payment p = paymentService.charge(userId, totalAmount, idempotencyKey);
    // ← PG 가 idempotencyKey 로 중복 청구 차단
    stockService.decrease(productId, qty);
}
```

settlement 의 *Refund 엔티티 의 `(payment_id, idempotency_key) UNIQUE 제약* 이 *같은 발상*.

### *Outbox 패턴 의 적용*
재시도 가 *DB 변경 + 외부 호출* 의 *조합* 이면 — *Outbox + Triple Idempotency*:

```java
@Transactional
public void chargeAndDeduct(...) {
    stockService.decrease(...);                   // ← DB only
    outboxRepo.save(new OutboxEvent(...));        // ← 같은 tx
    // 외부 호출 = 별도 polling worker
}
```

→ *DB 부분 만 재시도 안전*. *외부 호출 의 *별도 worker* 가 *멱등성 키 로 *중복 방지*.

---

## 6. 패턴 4 — *Atomic Update 의 *우회*

`@Version` 의 *대안* — *단순 한 카운터 / 잔액 / 재고* 은 *Atomic UPDATE* 가 *훨씬 단순*.

```java
// ❌ Optimistic Lock 의 *재시도 지옥*
@Transactional
public void decreaseStock(Long variantId, int qty) {
    ProductVariant v = repo.findById(variantId).orElseThrow();
    v.setStock(v.getStock() - qty);  // ← read-modify-write
    repo.save(v);
}

// ✅ Atomic UPDATE — 충돌 없음
@Modifying
@Query("UPDATE ProductVariant v " +
       "SET v.stock = v.stock - :qty " +
       "WHERE v.id = :id AND v.stock >= :qty")
int decreaseStockAtomic(@Param("id") Long id, @Param("qty") int qty);

public void decreaseStock(Long variantId, int qty) {
    int affected = repo.decreaseStockAtomic(variantId, qty);
    if (affected == 0) {
        throw new InsufficientStockException(variantId);
    }
}
```

→ *DB 가 *원자 적 으로 처리*. *재시도 불필요*. *@Version 도 불필요*. *충돌 = 부족 한 재고* 의 *명확 한 차이*.

**언제 사용** — *단순 한 수치 변경* + *비즈니스 로직 이 거의 없음*. *복잡 한 도메인 로직 (예: 가격 정책 + 할인 + VIP 등급)* 은 *Optimistic Lock 의 표준 패턴 이 더 자연*.

---

## 7. 패턴 5 — *Pessimistic 으로 *전환* — *언제?*

충돌 률 이 *높으면 *Optimistic 의 *재시도 지옥*. *Pessimistic* 으로 전환:

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT v FROM ProductVariant v WHERE v.id = :id")
ProductVariant findByIdForUpdate(@Param("id") Long id);

@Transactional
public void decreaseStock(Long variantId, int qty) {
    ProductVariant v = repo.findByIdForUpdate(variantId);  // ← FOR UPDATE
    v.decreaseStock(qty);
    repo.save(v);
}
```

생성 SQL — `SELECT ... FOR UPDATE`. *다른 tx 의 *SELECT FOR UPDATE / UPDATE 가 *대기*. *충돌 없음*.

### *Pessimistic 의 *비용*
- *동시 처리량 ↓* (직렬화)
- *deadlock 위험 ↑* (락 순서)
- *long-running tx 의 *영향 ↑*

### *Optimistic 유지 vs Pessimistic 전환 의 *결정 기준*
| 상황 | 권장 |
|---|---|
| 충돌 률 < 5% | Optimistic + Retry |
| 충돌 률 5~20% | **Atomic UPDATE** (가능 하면) |
| 충돌 률 > 20% + 짧은 tx | Pessimistic |
| 충돌 률 > 20% + 긴 tx | *설계 재검토* (도메인 분할) |
| 분산 환경 + 비-DB 자원 | Distributed Lock (Redis / etcd) |

settlement 의 *경험* — *재고 (SKU)* 는 *Optimistic + Retry*. *금액 (정산 잔액)* 은 *Pessimistic*. *도메인 특성 의 차이* 의 *명시 적 선택*.

---

## 8. 패턴 6 — *사용자 응답 의 *우아 함*

재시도 *exhausted 후* 의 *사용자 응답* — *5xx 의 *지옥* 이 아니라 *비즈니스 의미*.

```java
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(StockUpdateFailedException.class)
    ResponseEntity<ApiError> handleStock(StockUpdateFailedException e) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
            .body(new ApiError(
                "STOCK_CONCURRENT_UPDATE",
                "다른 고객 이 동시에 주문 중 입니다. 잠시 후 다시 시도 해주세요.",
                Map.of("productId", e.getProductId())
            ));
    }

    @ExceptionHandler(InsufficientStockException.class)
    ResponseEntity<ApiError> handleInsufficient(InsufficientStockException e) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
            .body(new ApiError(
                "STOCK_INSUFFICIENT",
                "재고 가 부족 합니다.",
                Map.of("productId", e.getProductId(), 
                       "available", e.getAvailable())
            ));
    }
}
```

→ *HTTP 409 Conflict* vs *422 Unprocessable*. *전자 = 재시도 가능*, *후자 = 비즈니스 실패*. *클라이언트 의 *재시도 결정 의 명확 한 신호*.

### Frontend 의 *재시도*
```typescript
async function orderProduct(productId: number, qty: number) {
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            return await api.post('/orders', { productId, qty });
        } catch (err) {
            if (err.response?.status === 409 && attempt < 2) {
                await sleep(200 * Math.pow(2, attempt));
                continue;
            }
            throw err;
        }
    }
}
```

→ *서버 + 클라이언트* 의 *2 단 재시도*. *대부분 의 *transient 충돌 의 *흡수*.

---

## 9. 패턴 7 — *테스트 의 *진짜 검증*

재시도 코드 가 *진짜 작동 하는지* 의 *증명* — *100 쓰레드 동시성 테스트*. settlement 의 *실제 테스트*:

```java
@SpringBootTest
class StockConcurrencyTest {

    @Autowired StockService stockService;
    @Autowired ProductVariantRepository repo;

    @Test
    void concurrent_100_threads_no_oversell() throws Exception {
        // Given: 재고 100 개 SKU
        ProductVariant v = repo.save(new ProductVariant("SKU-001", 100));

        // When: 100 쓰레드 가 동시 에 1 개 씩 차감
        int threads = 100;
        CountDownLatch ready = new CountDownLatch(threads);
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch done = new CountDownLatch(threads);
        AtomicInteger success = new AtomicInteger();
        AtomicInteger conflict = new AtomicInteger();

        ExecutorService pool = Executors.newFixedThreadPool(threads);
        for (int i = 0; i < threads; i++) {
            pool.submit(() -> {
                try {
                    ready.countDown();
                    start.await();
                    stockService.decreaseStock(v.getId(), 1);
                    success.incrementAndGet();
                } catch (StockUpdateFailedException e) {
                    conflict.incrementAndGet();
                } catch (Exception e) {
                    log.error("Unexpected", e);
                } finally {
                    done.countDown();
                }
            });
        }
        ready.await();
        start.countDown();   // ← 동시 시작
        done.await(30, TimeUnit.SECONDS);

        // Then: 정확 히 100 개 차감 + oversell 없음
        ProductVariant final_ = repo.findById(v.getId()).orElseThrow();
        assertThat(final_.getStock()).isEqualTo(0);
        assertThat(success.get() + conflict.get()).isEqualTo(threads);
        log.info("Success: {}, Conflict (retry exhausted): {}", 
                 success.get(), conflict.get());
    }
}
```

→ *진짜 동시성* 의 *검증*. *unit test 가 *못 잡는 *race condition 의 *유일한 진단 도구*.

내 settlement 의 *경험* — *100 쓰레드 + Retry 3 회* → *대부분 success 100 / conflict 0*. *재시도 backoff 가 *충분 한 분산*.

---

## 10. 분산 환경 의 *Optimistic Lock*

JPA 의 `@Version` 은 *DB 단 의 *낙관 적 락*. *비-DB 자원* (Redis cache / 외부 API state) 의 *동시성* 은 *별도 패턴*.

### Redis SETNX + CAS
```java
public boolean updateRedisCounter(String key, int delta) {
    while (true) {
        String current = redis.get(key);
        long curVal = Long.parseLong(current);
        long newVal = curVal + delta;
        
        // CAS — WATCH + MULTI/EXEC
        Boolean ok = redis.executePipelined(...).contains(true);
        if (ok) return true;
        // retry
    }
}
```

### etcd / ZooKeeper — *revision 기반*
```java
// etcd v3 API
TxnResponse resp = etcd.txn()
    .If(Cmp.create(KEY, Cmp.Op.EQUAL, expectedRevision))
    .Then(Op.put(KEY, newValue, PutOption.DEFAULT))
    .commit().get();
if (!resp.isSucceeded()) {
    // CAS 실패 — 재시도
}
```

핵심 — *모든 *낙관 적 락* 의 *공통 패턴* = **CAS (Compare-And-Swap)**. *JPA, Redis, etcd, ZooKeeper, Kafka* 모두 *같은 발상*.

---

## 11. 운영 함정 — *내 14 개월*

### (1) Cascade 의 *@Version*
`@OneToMany cascade = ALL` 의 *parent 만 *@Version*. *child 추가 / 삭제* 가 *parent version 증가 X* (Hibernate 기본 동작).

해결 — `@OptimisticLock(excluded = false)` 또는 *parent.lastModified 명시 적 변경*.

### (2) *부분 update 의 *함정*
```java
// ❌ @DynamicUpdate 없으면 *모든 컬럼 update*
@Entity class ProductVariant { @Version Long version; ... }

// 두 tx 가 *다른 컬럼* 변경 해도 *@Version 충돌*
```

해결 — `@DynamicUpdate` + *부분 update* (그러나 *동일 column 충돌 의 *위험 은 *남음*).

### (3) *@Lock(OPTIMISTIC_FORCE_INCREMENT)*
*read 만 하는 tx 도 *version 증가*. *조회 가 *관련 도메인 의 *일관성 보장 의무* 가 있을 때.
```java
@Lock(LockModeType.OPTIMISTIC_FORCE_INCREMENT)
ProductVariant findById(Long id);
```

### (4) *long-running tx 의 *재앙*
@Transactional 메서드 가 *수초~수분* 걸리면 — *그 동안 의 *모든 동시 요청* 이 *충돌*. *@Transactional 안 외부 호출 금지* 의 *진짜 의미*.

### (5) *Hibernate 의 *flush 시점*
*같은 트랜잭션 의 *2 번 째 SELECT* — *1 차 캐시 의 *옛 version 반환*. 변경 사항 보려면 `entityManager.refresh(entity)` 명시.

---

## 12. 마치며 — *작은 결론*

낙관 적 락 의 *진짜 가치* — *낮은 충돌 률 + 높은 처리 량* 의 *최적 조합*. *DB lock 의 *직렬화 비용 없음* + *충돌 시 *재시도 의 *작은 비용*.

낙관 적 락 의 *진짜 책임* — *충돌 시 *어떻게 처리* 가 *애플리케이션 측 의 *명시 적 결정*. *Pessimistic 의 *자동 대기* 와 다르게 *코드 가 *7 가지 패턴* (Retry / Atomic UPDATE / Pessimistic 전환 / 멱등성 / 사용자 응답 / 모니터링 / 동시성 테스트) 을 *명시 적 으로 *조합*.

settlement 의 *14 개월 운영* — *재고 (SKU)* 는 *Optimistic + Retry + Atomic Stock UPDATE 의 *3 단*, *금액 (정산 잔액)* 은 *Pessimistic*. *도메인 특성 별 *명시 적 선택* 이 *production 의 *결함 0 회* 의 *근거*.

핵심 메시지: *"낙관 적 락 은 *옵션 이 아니라 *완전 한 패턴 의 *조합*. *@Version 한 줄* 의 *겉모습 뒤* 의 *7 가지 책임* 의 *체화* 가 *진짜 의 quality*"*

---

## 참고

- *Java Persistence with Hibernate, 2nd Ed* (Christian Bauer)
- *Vlad Mihalcea — Optimistic Locking* — [vladmihalcea.com/optimistic-locking-version-property-jpa-hibernate](https://vladmihalcea.com/optimistic-locking-version-property-jpa-hibernate/)
- *Spring Retry Reference* — [docs.spring.io/spring-retry](https://docs.spring.io/spring-retry/docs/api/current/)
- *Resilience4j* — [resilience4j.readme.io](https://resilience4j.readme.io)
- 자매편:
    - [DB 옵티마이저 와 JPA 낙관 적 락 의 실패 방어](/2026/06/29/db-optimizer-and-jpa-optimistic-lock-retry-defense.html)
    - [데이터베이스 의 본질 — B+Tree 부터 MVCC, Replication 까지](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
    - [DB 설계 와 쿼리 — 14 개월 운영 경험](/2026/06/29/db-design-and-query-practical-guide.html)
    - [Transactional Outbox 패턴](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)
