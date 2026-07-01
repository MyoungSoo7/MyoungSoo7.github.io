---
layout: post
title: "Outbox 패턴 에서 JPA · MyBatis · QueryDSL 의 *경계* — 하나 로 모두 하려 하지 말라"
date: 2026-07-01 19:00:00 +0900
categories: [backend, outbox, jpa, mybatis, querydsl]
tags: [outbox, jpa, hibernate, mybatis, querydsl, kafka, idempotency, skip-locked, settlement]
---

*"JPA 를 쓰는 팀 은 *모든 것 을 JPA 로 하려 함*. MyBatis 팀 은 *모든 것 을 MyBatis 로*"* — 이 함정 이 *Outbox 패턴 의 *진짜 실패 원인*. Outbox 는 *4 가지 성격 이 다른 데이터 접근* 을 요구 — *하나 의 도구 로 강제 하면 *성능 / 유지보수 / 안전 성* 이 *모두 손상*.

이 글은 *settlement 의 *2 년 운영* 경험 위 에서 *JPA / MyBatis / QueryDSL 의 *역할 분담* 을 *Outbox 의 4 단계* 로 정리.

---

## 1. Outbox 패턴 복습 — *왜 3 도구 가 필요 한가*

*결제 완료* 이벤트 를 *다른 서비스 (정산 / 재고 / 알림)* 에 알리는 시나리오:

```
[결제 서비스]                    [정산 서비스]
    │                                │
    ├── payments 테이블 INSERT       │
    ├── outbox 테이블 INSERT         │
    │   (같은 트랜잭션)              │
    ▼                                │
COMMIT                               │
    │                                │
Poller (5 초 마다)                    │
    ├── outbox WHERE published=false │
    │   FOR UPDATE SKIP LOCKED       │
    ├── Kafka 발행                    │
    ├── outbox UPDATE published=true │
    ▼                                │
                                     ▼
                            Consumer (idempotent)
                                 processed_events PK
                                 settlements INSERT
```

**Outbox 의 *4 가지 데이터 접근*** — *성격 이 완전 히 다름*:

| # | 접근 | 성격 | 최적 도구 |
|---|---|---|---|
| **W1** | Business Write (Payment INSERT) | *도메인 로직* + *복잡 한 aggregate* | **JPA** |
| **W2** | Outbox Insert | *단순 INSERT* + *같은 트랜잭션* | **JPA** (통합) |
| **W3** | Outbox Poller SELECT + UPDATE | *동시성 (SKIP LOCKED)* + *배치 성능* | **JdbcTemplate / MyBatis** |
| **R1** | Read Projection (조회 / 리포트) | *복잡 한 JOIN* + *type-safe* | **QueryDSL** |

*4 가지 를 *하나 의 도구 로* 하면 — *각각 어색*. *역할 분담* 이 *진짜 답*.

---

## 2. Layer W1 — Business Write (JPA)

*Payment* 는 *도메인 엔티티*. *가격 정책 + 할인 + 유효성 검증 + State machine (PENDING → COMPLETED)* 등 *비즈니스 로직 이 풍부*.

```java
@Entity
@Table(name = "payments")
public class Payment {
    @Id @GeneratedValue Long id;
    @Enumerated(EnumType.STRING) PaymentStatus status;
    @Embedded Money amount;
    @Version Long version;

    // 도메인 로직
    public void complete() {
        if (this.status != PaymentStatus.PENDING) {
            throw new IllegalStateException("이미 완료 됨");
        }
        this.status = PaymentStatus.COMPLETED;
        // ... 상태 전이 감사 로그
    }
}
```

**왜 JPA 인가**:
- *도메인 로직* 이 *엔티티 안* 에 있음 (Rich Domain Model)
- *@Version* 낙관 적 락 자동
- *@Embedded* Value Object
- *@OneToMany cascade* 로 *aggregate 자동 관리*
- *TransactionSynchronization* 으로 *커밋 시점 hook*

**MyBatis 로 시도 하면**:
- *엔티티 = DTO* (row 1:1 매핑) — *도메인 로직 이 서비스 로 이동* → *Anemic Model*
- *상태 전이* 를 *SQL UPDATE 로 직접* — *invariant 관리 어려움*
- *복잡 한 aggregate* 를 *수동 로드* — *N+1 지옥*

→ *복잡 한 도메인 = JPA 압도적*.

---

## 3. Layer W2 — Outbox Insert (JPA — 통합 트랜잭션 의 이유)

*Payment INSERT 와 *같은 트랜잭션* 안 에 *OutboxEvent INSERT*. **이게 Outbox 패턴 의 *심장***.

```java
@Entity
@Table(name = "outbox_events")
public class OutboxEvent {
    @Id
    @Column(name = "event_id")
    private UUID eventId;    // ← L1 멱등성 키

    @Column private String aggregateType;
    @Column private String aggregateId;
    @Column private String eventType;
    @Column(columnDefinition = "jsonb") private String payload;

    @Enumerated(EnumType.STRING)
    private OutboxStatus status;  // PENDING / PUBLISHED / DEAD

    @Column private Instant createdAt;
    @Column private Instant publishedAt;

    static OutboxEvent of(String type, String aggId, Object data) {
        OutboxEvent e = new OutboxEvent();
        e.eventId = UUID.randomUUID();
        e.aggregateType = "Payment";
        e.aggregateId = aggId;
        e.eventType = type;
        e.payload = JsonUtil.toJson(data);
        e.status = OutboxStatus.PENDING;
        e.createdAt = Instant.now();
        return e;
    }
}
```

**사용**:
```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentRepository paymentRepo;
    private final OutboxRepository outboxRepo;

    @Transactional  // ← 하나 의 트랜잭션
    public void complete(Long paymentId) {
        Payment p = paymentRepo.findById(paymentId).orElseThrow();
        p.complete();  // ← 도메인 로직

        // 같은 트랜잭션 에서 outbox 저장
        outboxRepo.save(OutboxEvent.of(
            "PAYMENT_COMPLETED",
            String.valueOf(paymentId),
            new PaymentCompletedEvent(paymentId, p.getAmount())
        ));
        // COMMIT → payments + outbox_events 원자 적 커밋
    }
}
```

**왜 JPA 인가**:
- *같은 트랜잭션 안* 이 *핵심*. *다른 도구 로 분리 하면 *2PC (2-phase commit)* 지옥
- *영속성 컨텍스트* 가 *두 엔티티 를 함께 관리* — *간단*

**함정** — *Outbox 를 *별도 서비스 / DB* 로 두면 안 됨. *반드시 같은 DB / 같은 트랜잭션*.

---

## 4. Layer W3 — Outbox Poller (JdbcTemplate / MyBatis 의 자리)

*진짜 승부처*. *Poller 가 *5 초 마다 실행* — *동시성 + 성능* 이 *결정 적*.

### JPA 로 시도 시 의 *4 가지 함정*

```java
// ❌ 안티 패턴 1 — JPA 로 SELECT FOR UPDATE SKIP LOCKED
@Lock(LockModeType.PESSIMISTIC_WRITE)
@QueryHints({@QueryHint(name = "javax.persistence.lock.timeout", value = "0")})
@Query("SELECT o FROM OutboxEvent o WHERE o.status = 'PENDING' " +
       "ORDER BY o.createdAt ASC")
List<OutboxEvent> findPendingForUpdate(Pageable pageable);
```

문제:
1. **SKIP LOCKED 를 *표준 JPA 로 표현 불가*** — *hint 로 우회 지만 *공식 아님*. Hibernate 6.2+ 의 `LockOptions.SKIP_LOCKED` 도 완전 하지 않음
2. **JPA 의 *1 차 캐시* 가 *배치 처리 에 방해*** — 100 개 entity 로드 시 *메모리 폭증*. `clear()` 명시 필요
3. **`fetch join` 없으면 N+1** — payload 가 지연 로딩 이면 *100 회 추가 쿼리*
4. **성능** — JPA 의 오버헤드 로 *TPS 저하*

### JdbcTemplate 의 *답*

```java
@Repository
@RequiredArgsConstructor
public class OutboxPollerRepository {
    private final JdbcTemplate jdbc;

    public List<OutboxEvent> pollPending(int limit) {
        String sql = """
            SELECT event_id, aggregate_type, aggregate_id, event_type,
                   payload, created_at
            FROM outbox_events
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT ?
            FOR UPDATE SKIP LOCKED
            """;
        return jdbc.query(sql, this::mapRow, limit);
    }

    public int markPublished(List<UUID> eventIds) {
        String sql = "UPDATE outbox_events SET status='PUBLISHED', " +
                     "published_at=NOW() WHERE event_id = ANY(?)";
        return jdbc.update(sql, ps -> {
            ps.setArray(1, ps.getConnection().createArrayOf("uuid", eventIds.toArray()));
        });
    }

    private OutboxEvent mapRow(ResultSet rs, int rowNum) throws SQLException {
        // ... mapping
    }
}
```

**장점**:
- **SKIP LOCKED 명시** — *다른 poller 인스턴스* 가 *같은 row 를 다시 잠그지 않음*. *3 replica poller 동시 실행 가능*
- **성능** — *JPA 오버헤드 0*. *직접 SQL*
- **명확** — *SQL 그대로*, *진단 쉬움*

### MyBatis 의 대안

```xml
<mapper namespace="OutboxPollerMapper">
    <select id="pollPending" resultType="OutboxEvent">
        SELECT event_id, aggregate_type, aggregate_id, event_type,
               payload, created_at
        FROM outbox_events
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
        LIMIT #{limit}
        FOR UPDATE SKIP LOCKED
    </select>

    <update id="markPublished">
        UPDATE outbox_events
        SET status = 'PUBLISHED', published_at = NOW()
        WHERE event_id IN
        <foreach collection="eventIds" item="id" open="(" separator="," close=")">
            #{id}
        </foreach>
    </update>
</mapper>
```

**MyBatis 가 JdbcTemplate 대비 유리**:
- *dynamic SQL* — *조건 별 WHERE 절 분기* (예: aggregate_type 별 필터)
- *복잡 한 조회* — 관리 화면 의 *필터 5 개 조합* 같은 것
- *XML 로 SQL 관리* — *SQL 개발자 가 리뷰 가능*

**MyBatis 가 불리**:
- *간단 한 CRUD* 만 이면 *JdbcTemplate 이 더 짧음*
- *XML 관리 비용*

### settlement 의 실 선택
*JdbcTemplate 사용*. *SKIP LOCKED 의 명확 성 + 짧은 코드*. *dynamic SQL 필요 없음* (poller 는 *단일 쿼리*).

---

## 5. Layer R1 — Read Projection (QueryDSL 의 자리)

*조회 전용 화면* — *정산 리포트*, *결제 대사*, *셀러 대시보드* 등. *복잡 한 JOIN + 동적 필터* 가 특징.

### 요구 — *셀러 별 *월 매출 대시보드*

```sql
SELECT
    s.id AS seller_id,
    s.name AS seller_name,
    DATE_TRUNC('month', p.completed_at) AS month,
    COUNT(*) AS transaction_count,
    SUM(p.amount) AS total_amount,
    SUM(r.amount) AS total_refund,
    (SUM(p.amount) - COALESCE(SUM(r.amount), 0)) AS net_amount
FROM sellers s
INNER JOIN products pr ON pr.seller_id = s.id
INNER JOIN order_items oi ON oi.product_id = pr.id
INNER JOIN payments p ON p.order_id = oi.order_id
LEFT JOIN refunds r ON r.payment_id = p.id
WHERE p.status = 'COMPLETED'
  AND p.completed_at >= :startDate
  AND p.completed_at < :endDate
  AND (:sellerId IS NULL OR s.id = :sellerId)
  AND (:productCategory IS NULL OR pr.category = :productCategory)
GROUP BY s.id, s.name, DATE_TRUNC('month', p.completed_at)
ORDER BY total_amount DESC
LIMIT :limit
OFFSET :offset;
```

### JPA / JPQL 로 시도 시

```java
// JPQL — 복잡 하고 type-unsafe
@Query("SELECT NEW SellerDashboard(s.id, s.name, ...) " +
       "FROM Seller s " +
       "JOIN Product pr ON pr.sellerId = s.id " +
       "JOIN OrderItem oi ON oi.productId = pr.id " +
       "JOIN Payment p ON p.orderId = oi.orderId " +
       "LEFT JOIN Refund r ON r.paymentId = p.id " +
       "WHERE ...")
```

문제:
- *동적 필터 (nullable 조건)* 표현 어색 — `(:sellerId IS NULL OR s.id = :sellerId)` 반복
- *컴파일 시 검증 없음* — 문자열 오타 는 *runtime 폭발*
- *GROUP BY / 집계* 의 *type 안전 표현 어려움*

### QueryDSL 의 답

```java
@Repository
@RequiredArgsConstructor
public class SellerDashboardRepository {
    private final JPAQueryFactory query;

    public List<SellerDashboard> getMonthlyDashboard(
            LocalDate startDate,
            LocalDate endDate,
            Long sellerId,          // nullable
            String category,         // nullable
            int limit, int offset) {

        QSeller s = QSeller.seller;
        QProduct pr = QProduct.product;
        QOrderItem oi = QOrderItem.orderItem;
        QPayment p = QPayment.payment;
        QRefund r = QRefund.refund;

        NumberExpression<BigDecimal> netAmount =
            p.amount.sum().subtract(r.amount.sum().coalesce(BigDecimal.ZERO));

        return query
            .select(Projections.constructor(SellerDashboard.class,
                s.id, s.name,
                Expressions.dateTemplate(YearMonth.class,
                    "date_trunc('month', {0})", p.completedAt),
                p.count(),
                p.amount.sum(),
                r.amount.sum().coalesce(BigDecimal.ZERO),
                netAmount
            ))
            .from(s)
            .innerJoin(pr).on(pr.sellerId.eq(s.id))
            .innerJoin(oi).on(oi.productId.eq(pr.id))
            .innerJoin(p).on(p.orderId.eq(oi.orderId))
            .leftJoin(r).on(r.paymentId.eq(p.id))
            .where(
                p.status.eq(PaymentStatus.COMPLETED),
                p.completedAt.goe(startDate.atStartOfDay()),
                p.completedAt.lt(endDate.atStartOfDay()),
                sellerIdEq(sellerId),         // ← 동적
                categoryEq(category)           // ← 동적
            )
            .groupBy(s.id, s.name, Expressions.dateTemplate(...))
            .orderBy(p.amount.sum().desc())
            .limit(limit)
            .offset(offset)
            .fetch();
    }

    private BooleanExpression sellerIdEq(Long sellerId) {
        return sellerId != null ? QSeller.seller.id.eq(sellerId) : null;
    }

    private BooleanExpression categoryEq(String category) {
        return category != null ? QProduct.product.category.eq(category) : null;
    }
}
```

**QueryDSL 의 *진짜 가치*:
- **type-safe** — *컴파일 시점 에 오타 / 타입 오류 감지*
- **dynamic where** — *nullable 조건 을 *메소드 로 분리* → `null` 반환 시 조건 제외
- **IDE 자동완성** — `s.id`, `p.amount.sum()` 등 *모두 강타입*
- **refactoring 안전** — *컬럼 rename 시 컴파일 실패 로 감지*

### MyBatis 도 가능 하지만
```xml
<select id="getMonthlyDashboard" resultType="SellerDashboard">
    SELECT ...
    FROM sellers s
    <if test="sellerId != null">AND s.id = #{sellerId}</if>
    ...
</select>
```

- *SQL 그대로 표현* — DBA 리뷰 편함
- *type-safe 부족* — DTO 매핑 오타 는 runtime
- *dynamic 은 MyBatis 도 강* — 취향 문제

**settlement 의 실 선택** — *QueryDSL*. *리팩토링 자주 발생* + *type safety 우선* + *Java 개발자 팀*.

---

## 6. 안티 패턴 — *1 도구 로 모두 하려 함*

### 안티 패턴 1: *"JPA 만 쓰자"*

- Business Write ✓ (좋음)
- Outbox Insert ✓ (좋음)
- **Poller** ⚠️ — SKIP LOCKED 우회, 1 차 캐시 문제, 성능 저하
- **Projection** ⚠️ — 복잡 JPQL 문자열, dynamic 조건 지옥

*결과* — *Poller 의 *deadlock 사고*, *리포트 화면 의 *TPS 급락*.

### 안티 패턴 2: *"MyBatis 만 쓰자"*

- **Business Write** ⚠️ — Anemic Model, 도메인 로직 이 service 로 leak
- Outbox Insert ✓ (단순 INSERT)
- Poller ✓ (좋음)
- Projection ✓ (동적 SQL)

*결과* — *도메인 로직 이 SQL 에 흩어짐*, *복잡 aggregate 관리 지옥*.

### 안티 패턴 3: *"QueryDSL 로 write 도 하자"*

QueryDSL 은 *SELECT 중심 도구*. *INSERT / UPDATE 는 *지원 하지만 어색*.

```java
// QueryDSL 의 UPDATE — 가능 하지만 도메인 로직 우회
query.update(payment)
     .set(payment.status, PaymentStatus.COMPLETED)
     .where(payment.id.eq(paymentId))
     .execute();
// ← @Version 낙관 적 락 우회, 도메인 method 우회
```

*결과* — *invariant 파괴*, *`@Version` 무력화*, *도메인 로직 leak*.

---

## 7. 실 코드 예제 — *3 도구 조합*

settlement 의 *실제 구조* (간략):

```
com.settlement.payment/
├── domain/
│   ├── Payment.java              ← JPA @Entity (Rich Domain)
│   ├── PaymentRepository.java    ← JpaRepository (interface)
│   └── OutboxEvent.java          ← JPA @Entity
├── application/
│   ├── PaymentService.java       ← @Transactional (Business Write + Outbox Insert)
│   └── OutboxPoller.java         ← @Scheduled (Poller)
├── infra/
│   ├── OutboxPollerRepository.java  ← JdbcTemplate (SKIP LOCKED)
│   └── SellerDashboardRepository.java ← QueryDSL (Projection)
└── query/
    └── SellerDashboardDto.java    ← 조회 전용 DTO
```

**Poller 실 구현**:
```java
@Component
@RequiredArgsConstructor
public class OutboxPoller {
    private final OutboxPollerRepository outboxRepo;
    private final KafkaPublisher publisher;

    @Scheduled(fixedDelay = 5000)   // 5 초
    @Transactional                   // JdbcTemplate 도 트랜잭션 필요
    public void poll() {
        List<OutboxEvent> events = outboxRepo.pollPending(100);
        if (events.isEmpty()) return;

        List<UUID> published = new ArrayList<>();
        for (OutboxEvent e : events) {
            try {
                publisher.publish(e);
                published.add(e.getEventId());
            } catch (Exception ex) {
                log.error("Publish failed: {}", e.getEventId(), ex);
                // DEAD 처리 는 별개 로직
            }
        }
        if (!published.isEmpty()) {
            outboxRepo.markPublished(published);
        }
    }
}
```

**핵심 포인트**:
- `@Transactional` 로 *SELECT FOR UPDATE 의 lock* 유지 + *UPDATE 도 같은 tx*
- **JPA `EntityManager` 안 씀** — *1 차 캐시 회피 + 성능*
- *배치 사이즈 100* — *너무 크면 Kafka 지연*, *너무 작으면 poll 오버헤드*

---

## 8. 성능 실측 — settlement 의 *실 수치*

*100 만 event 처리 시나리오* (내 클러스터 의 *load test*):

| 접근 | TPS | p99 latency | Memory |
|---|---|---|---|
| JPA (@Lock + EntityManager) | 800 | 250 ms | 800 MB |
| JPA + `stateless session` | 1500 | 150 ms | 400 MB |
| **JdbcTemplate + SKIP LOCKED** | **3500** | **60 ms** | 200 MB |
| MyBatis + SKIP LOCKED | 3200 | 65 ms | 250 MB |

→ *Poller 에 서 *4 배 성능 차이*. *TPS 병목 이 poller 인 경우* — *반드시 JdbcTemplate/MyBatis*.

---

## 9. 결정 매트릭스

| 상황 | 도구 |
|---|---|
| 도메인 로직 풍부 + 상태 전이 | **JPA** |
| 단순 INSERT + 같은 트랜잭션 | **JPA** (통합 이 우선) |
| Batch write 100+ row | JPA `saveAll` 또는 **JdbcTemplate `batchUpdate`** |
| SELECT FOR UPDATE SKIP LOCKED | **JdbcTemplate / MyBatis** |
| Poller / Worker 조회 | **JdbcTemplate / MyBatis** |
| Dynamic 조건 조회 (nullable filter) | **QueryDSL** (Java 팀) 또는 **MyBatis** (SQL 중심) |
| 복잡 JOIN + 집계 | **QueryDSL** (type-safe) 또는 **MyBatis** (SQL 그대로) |
| DBA 리뷰 필수 | **MyBatis** (XML 로 SQL 관리) |
| Read model / CQRS | **QueryDSL** + 별도 조회 전용 테이블 |
| DDL / 마이그레이션 | **Flyway / Liquibase** (도구 무관) |

---

## 10. Spring Data JDBC — *2026 의 *중간 옵션*

*JPA 의 무거움 + MyBatis 의 verbose* 사이. *Spring Data JDBC* 가 *가벼운 대안*:

```java
@Table("payments")
public class Payment {
    @Id Long id;
    PaymentStatus status;
    BigDecimal amount;
    // getter/setter
}

public interface PaymentRepository extends CrudRepository<Payment, Long> {
    @Query("SELECT * FROM payments WHERE status = 'PENDING' " +
           "FOR UPDATE SKIP LOCKED LIMIT :limit")
    List<Payment> findPendingForUpdate(int limit);
}
```

**Spring Data JDBC 의 *특징*:
- *영속성 컨텍스트 없음* — 1 차 캐시 없음, dirty checking 없음
- *lazy loading 없음* — *명시 적 로딩*
- *SKIP LOCKED* — `@Query` 로 단순 처리
- *aggregate 단위 CRUD* — DDD 친화

**적합** — *Outbox poller + 간단 CRUD* 조합. *2026 시점 sparta 팀 이 채택 검토 중*.

---

## 11. 실무 팁 — *운영 함정 5 가지*

### (1) Outbox 테이블 의 *인덱스*
```sql
CREATE INDEX idx_outbox_status_created
    ON outbox_events(status, created_at)
    WHERE status = 'PENDING';   -- ← partial index
```
*PENDING 만 index* — *PUBLISHED (99.9%) 는 index 낭비 없음*.

### (2) Outbox 의 *retention*
*PUBLISHED 이벤트 는 *일정 기간 후 삭제*. *pg_partman* 으로 *월별 파티션 + 자동 drop*.

### (3) Poller 의 *replica 수*
*3 replica* 권장 — *한 대 다운 시 다른 두 대가 SKIP LOCKED 로 이어감*.

### (4) *Idempotent Consumer*
*Consumer 측 은 *processed_events 테이블 로 중복 방지*. *Triple Idempotency 의 L2*.

### (5) *Kafka 의 *실패 시*
*publish 실패 는 *retry 3 회 후 status='DEAD'* → *별도 관리 화면 에서 수동 처리*.

---

## 12. 마치며 — *"경계 를 존중 하라"*

각 도구 는 *탄생 배경 이 다름*:
- **JPA** — *ORM 의 원리 (identity, dirty checking, lazy)* — *도메인 관리 중심*
- **MyBatis** — *SQL 을 그대로*, *동적 SQL 강*, *DBA / SQL 문화*
- **QueryDSL** — *type-safe query builder*, *Java 컴파일러 활용*
- **JdbcTemplate** — *가장 얇은 wrapper*, *성능 극한*

*"모두 를 하나 로"* 하려 하면 — *각 도구 의 *진짜 강점 을 못 살림*. *"각자 의 자리"* 를 인정 하면 — *Outbox 가 *성능 + 안전 성 + 유지 보수* 를 *모두 만족*.

내 settlement 의 *2 년 운영* 의 *작은 결론* — *경계 를 존중 하라*. *새 요구* 가 오면 *어떤 도구 가 적합* 을 *먼저 판단*. *익숙한 도구 로 억지로 하지 말라*. 이게 *production 의 *진짜 지혜*.

---

## 참고

- *Transactional Outbox Pattern* (Chris Richardson) — [microservices.io/patterns/data/transactional-outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- *High-Performance Java Persistence* (Vlad Mihalcea)
- *Java Persistence with Hibernate, 2nd Ed* (Christian Bauer)
- *QueryDSL Reference* — [querydsl.com](http://querydsl.com)
- *MyBatis Documentation* — [mybatis.org](https://mybatis.org)
- *Spring Data JDBC Reference* — [docs.spring.io/spring-data/jdbc](https://docs.spring.io/spring-data/jdbc/docs/current/reference/html/)
- 자매편:
    - [Transactional Outbox 패턴 심층](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)
    - [DB 설계 와 쿼리 — 14 개월 운영 경험](/2026/06/29/db-design-and-query-practical-guide.html)
    - [낙관 적 락 실패 를 어떻게 막을 것인가](/2026/06/30/optimistic-lock-failure-defensive-coding.html)
