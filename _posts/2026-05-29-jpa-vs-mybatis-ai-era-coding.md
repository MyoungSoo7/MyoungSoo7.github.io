---
layout: post
title: "JPA vs MyBatis — 2026 년 5 월 기준, 생성형 AI 시대에 어느 것이 더 유용한가? 그리고 둘 다 쓸 것인가 하나로 통일할 것인가"
date: 2026-05-29 03:00:00 +0900
categories: [java, spring, database, ai]
tags: [jpa, hibernate, mybatis, orm, sql-mapper, spring-data, ai-coding, generative-ai, claude-code, copilot, persistence]
---

JPA 와 MyBatis 의 *교체할 수 없는 차이* 는 두 줄로 요약된다:

> **JPA 는 *객체* 가 중심, MyBatis 는 *SQL* 이 중심.**
> 그래서 **JPA 는 *모델 변경* 에 빠르고, MyBatis 는 *쿼리 튜닝* 에 빠르다.**

이 *근본 차이* 가 2026 년 AI 시대에 *완전히 다른 양상* 으로 드러난다. 생성형 AI 가 SQL 보다 *객체 코드를 더 잘 만들고*, MyBatis 의 XML 보다 *Java/Kotlin 메서드 시그니처를 더 정확히* 추론하기 때문이다. 그러나 *복잡한 쿼리 튜닝* 에서는 *AI 가 만든 JPA 가 N+1 폭탄* 을 떨어뜨리고, *AI 가 만든 MyBatis 가 더 안정적* 인 경우도 많다.

이 글은 *기술 비교 → 강점/약점 → AI 시대의 새 변수 → 통일 vs 혼용 가이드* 4 단계로 정리한다.

---

## TL;DR

| 항목 | JPA (Hibernate) | MyBatis |
|---|---|---|
| **철학** | ORM — 객체가 1급 시민 | SQL Mapper — SQL 이 1급 시민 |
| **쿼리 작성** | 자동 생성 또는 JPQL/Criteria | 사람이 SQL 직접 작성 |
| **단순 CRUD** | ⭐ 매우 빠름 | 보통 |
| **복잡 쿼리** | 어려움 (Native query 또는 QueryDSL) | ⭐ 자연스러움 |
| **DB 종속성 회피** | ⭐ 좋음 (DB 바꿔도 코드 거의 그대로) | 약함 (DB 방언 SQL 자주) |
| **튜닝 가시성** | 약함 (생성된 SQL 추측) | ⭐ 명확 (SQL 그대로 보임) |
| **러닝 커브** | 가파름 (영속성 컨텍스트, 캐시, fetch 전략) | 완만 |
| **AI 코드 생성 품질** | ⭐ 더 정확 | 보통 (복잡 SQL 은 환각 위험) |
| **AI 디버깅 난이도** | 보통 (생성 SQL 추적 필요) | ⭐ 쉬움 (SQL 그대로) |

**2026 년 5 월 권장:**
- 신규 일반 프로젝트 → **JPA 우선, 복잡 쿼리만 MyBatis 또는 JdbcTemplate**
- 대규모 데이터 / 통계 / 배치 → MyBatis 또는 jOOQ
- 레거시 통합 / 복잡 stored procedure → MyBatis
- *둘 다 사용 OK* — 한 프로젝트에서 *역할 분리* 면 합리적

---

## 1. JPA 와 MyBatis 의 정체

### 1.1 JPA — *Java Persistence API*

- Sun Microsystems 의 **표준 스펙** (2006, JSR 220). EJB 3.0 의 부산물
- *구현체*: **Hibernate** (사실상 표준), EclipseLink, OpenJPA
- *Spring Data JPA*: JPA 위에 *repository 추상화* 를 더 얹은 Spring 프로젝트

```java
@Entity
@Table(name = "orders")
public class Order {
    @Id @GeneratedValue
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    private User user;

    @Column(name = "total_amount")
    private BigDecimal totalAmount;

    @CreationTimestamp
    private Instant createdAt;
}

public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByUserIdAndCreatedAtAfter(Long userId, Instant after);
}
```

위 한 인터페이스 메서드만으로 *SQL 자동 생성*:
```sql
SELECT * FROM orders WHERE user_id = ? AND created_at > ?
```

JPA 의 *마법*. 단 이 마법이 *후에 비싼 대가* 를 부를 수 있음 — *N+1 query*, *lazy loading 함정*.

### 1.2 MyBatis — *SQL Mapper*

- 원래 *iBATIS* (2002) → 2010 년 Google 이 Apache 에서 MyBatis 로 fork
- 한국/중국/일본에서 *압도적 시장 점유* — 특히 금융권/공공기관
- 철학: *SQL 은 개발자가 관리한다*. 자동 생성 안 함

```java
@Mapper
public interface OrderMapper {
    @Select("SELECT id, user_id, total_amount, created_at " +
            "FROM orders WHERE user_id = #{userId} AND created_at > #{after}")
    List<Order> findByUserIdAndCreatedAtAfter(Long userId, Instant after);
}
```

또는 XML:
```xml
<mapper namespace="OrderMapper">
  <select id="findByUserIdAndCreatedAtAfter" resultType="Order">
    SELECT id, user_id, total_amount, created_at
    FROM orders
    WHERE user_id = #{userId}
      AND created_at > #{after}
  </select>
</mapper>
```

JPA 의 *Repository 메서드 자동 SQL 생성* 같은 마법은 *없음*. *SQL 을 직접 적는* 게 핵심.

---

## 2. 7 가지 핵심 차이

### 2.1 추상화 수준 — *객체 vs 행*

- **JPA**: *객체 그래프* 가 중심. `Order.getUser().getName()` 같은 *객체 탐색*
- **MyBatis**: *행 (row)* 이 중심. SQL 결과를 *객체로 매핑* 하는 정도

JPA 는 *Domain-Driven Design* 의 *Aggregate* 와 잘 어울림 — 객체 중심 모델링.
MyBatis 는 *Transaction Script* 또는 *Active Record* 와 잘 어울림 — 절차 중심.

### 2.2 영속성 컨텍스트 (Persistence Context) — JPA 만 있는 것

JPA 의 *가장 강력한 (그리고 위험한)* 기능:

```java
@Transactional
public void updateOrder(Long orderId) {
    Order order = orderRepo.findById(orderId).get();  // SELECT
    order.setStatus("APPROVED");                       // 변경
    // save() 안 불러도 트랜잭션 끝날 때 UPDATE 자동 발행!
}
```

영속성 컨텍스트가 *변경 추적* (dirty checking). *명시 save 불필요*. 그러나:

- *언제 SQL 이 실제로 나가는지* 직관 어려움 (`flush` 시점)
- `EntityManager.clear()` 또는 트랜잭션 분리 시 *동작 다름*

MyBatis 엔 이 개념 *없음*. `update` 메서드를 *명시 호출* 해야 SQL 실행.

### 2.3 N+1 Query — JPA 의 *원초적 함정*

```java
@Entity
public class User {
    @OneToMany(mappedBy = "user", fetch = FetchType.LAZY)
    private List<Order> orders;
}

// 코드
List<User> users = userRepo.findAll();          // 1 query (users)
for (User u : users) {
    System.out.println(u.getOrders().size());   // N queries (each user's orders)
}
// → 총 1 + N 쿼리 발행. user 가 1000명이면 1001 쿼리.
```

해결: `@EntityGraph`, `JOIN FETCH`, `BatchSize` 등. *MyBatis 엔 이 함정 자체가 없음* (사람이 SQL 직접 짜기에).

### 2.4 캐시

- **JPA**: *1차 캐시* (영속성 컨텍스트 = 트랜잭션 내), *2차 캐시* (선택, EhCache 같은 거)
- **MyBatis**: *LocalCache* (세션 내), *2nd-level cache* (Mapper namespace 별)

JPA 의 1차 캐시는 *자동* — 같은 트랜잭션에서 같은 ID 조회 시 DB 안 감.
MyBatis 의 LocalCache 는 *제한적* — 같은 Mapper 의 같은 메서드 + 같은 파라미터.

### 2.5 마이그레이션 / 스키마 진화

- **JPA**: `@Column` 변경하면 *Hibernate ddl-auto* 가 자동 (`update` / `create` — production 절대 금지). Flyway / Liquibase 로 *명시 마이그레이션* 권장
- **MyBatis**: SQL 마이그레이션은 *전적으로* Flyway / Liquibase. SQL 자체가 *수동* 이므로 일관성 ↑

### 2.6 DB 종속성

- **JPA**: HQL → 각 DB 의 SQL 로 *자동 변환*. Postgres → Oracle 이전 시 *코드 거의 안 바뀜*
- **MyBatis**: SQL 이 *직접* 적혀있어 DB 종속. 이전 시 *모든 Mapper 수정*

이건 *서비스 운영의 현실* 과 비교:
- *진짜로 DB 바꿔본 적 있는가?* 대부분 회사 *없음*
- *JPA 의 DB 독립성* 은 *이론적 장점*, *실전에선 거의 안 쓰임*

### 2.7 동적 쿼리

```java
// JPA — QueryDSL 또는 Specification 필요
QOrder o = QOrder.order;
JPQLQuery<Order> query = jpaFactory.selectFrom(o);
if (status != null) query.where(o.status.eq(status));
if (userId != null) query.where(o.user.id.eq(userId));
```

```xml
<!-- MyBatis 동적 SQL — XML 의 강점 -->
<select id="searchOrders" resultType="Order">
  SELECT * FROM orders
  <where>
    <if test="status != null">AND status = #{status}</if>
    <if test="userId != null">AND user_id = #{userId}</if>
    <if test="minAmount != null">AND total_amount >= #{minAmount}</if>
  </where>
  <if test="orderBy != null">ORDER BY ${orderBy}</if>
</select>
```

MyBatis 의 *동적 SQL* (`<if>`, `<choose>`, `<foreach>`) 이 *복잡한 검색 조건* 표현에 *훨씬 자연스러움*.

---

## 3. 각자의 *진짜 강점*

### JPA 의 강점

1. **단순 CRUD 의 *생산성*** — Repository 메서드 시그니처만으로 SQL 생성. *80% 의 비즈니스 로직* 에 충분
2. **객체 모델링** — DDD 의 Aggregate 와 자연스러운 매핑
3. **변경 추적 자동화** — dirty checking
4. **타입 안전성** — Criteria API, QueryDSL 로 *컴파일 타임* 쿼리 검증
5. **Spring Data 의 *추상화*** — `findBy...`, `Page`, `Sort` 등 풍부한 추상

### MyBatis 의 강점

1. **SQL 의 *명확성*** — 코드만 보면 *어떤 SQL 이 발행될지* 명확
2. **복잡 쿼리** — `WITH RECURSIVE`, `WINDOW FUNCTION`, *DB 별 특화 기능* 자유롭게
3. **튜닝 용이성** — DBA 가 *그대로 검토 가능*
4. **러닝 커브 완만** — SQL 만 알면 *바로 사용*
5. **stored procedure 통합** — 레거시 시스템에 *완벽*
6. **Bulk operation** — `INSERT INTO ... SELECT ...` 같은 *세트 처리* 자연스러움

---

## 4. AI 시대 (2026 년 5 월) — *새 변수*

### 4.1 AI 가 *JPA 를 더 잘 쓰는 이유*

생성형 AI (Claude, GPT, Gemini) 가 JPA 코드를 *MyBatis 보다 정확히* 만드는 경향. 이유 5 가지:

**1. 메서드 시그니처 = 명세**
```java
List<Order> findByUserIdAndStatusOrderByCreatedAtDesc(Long userId, String status);
```
이름 자체가 *완전한 명세*. AI 가 *추론할 여지가 적음*. 헛소리할 공간이 없음.

**2. 어노테이션 기반 모델**
`@Entity`, `@OneToMany`, `@JoinColumn` 같은 어노테이션은 *학습 데이터에 풍부*. AI 가 *익숙*.

**3. 표준 스펙**
JPA 는 *Java EE 표준* 이라 *학습 데이터의 일관성 ↑*. MyBatis 는 *XML 작성 스타일이 회사마다 다름* → AI 가 *어느 스타일* 을 선택할지 헷갈림.

**4. 컴파일러 피드백**
JPA 는 *대부분 Java 코드* → 컴파일러가 잡음. AI 가 틀려도 *즉시 수정 가능*.
MyBatis 는 *XML + SQL 문자열* → 컴파일러 패스, *런타임 에러* 가 흔함.

**5. Repository 인터페이스**
AI 가 *인터페이스 시그니처 한 줄* 만 보고 *모든 SQL 작성 위임*. 가장 *추상화된* 코드 = 가장 *AI 가 잘 만드는* 코드.

### 4.2 AI 가 *MyBatis 에 약한 이유*

**1. SQL 의 *비결정성***
같은 비즈니스 요구도 *수십 가지 SQL* 로 표현 가능. AI 가 *그 회사의 스타일* 을 모르면 *어색한 SQL* 생성.

**2. DB 방언**
Postgres 의 `JSONB`, MySQL 의 `JSON_TABLE`, Oracle 의 `CONNECT BY` 같은 *DB 별 특화 기능*. AI 가 *우리 DB 가 무엇* 인지 명시 없으면 헛소리.

**3. 도메인 컨텍스트 부족**
AI 가 *settlements 테이블의 transaction_type = 'REFUND'* 이 *어떤 의미* 인지 모름. JPA 의 `@Enumerated` + Java enum 으로 표현하면 *AI 도 이해*.

**4. XML 의 *시각적 복잡성***
긴 `<choose>`, `<foreach>` 가 *AI 의 token window* 압박. *작은 변경* 도 *전체 SQL 재생성* 위험.

**5. 테스트 어려움**
AI 가 *MyBatis SQL 의 테스트 데이터* 생성 어려움. JPA 는 *Repository 모킹* 으로 단위 테스트 쉬움.

### 4.3 그러나 *AI 가 JPA 에서 더 잘 *틀리는** 영역도 있다

**1. N+1 Query 함정**
AI 가 *코드 생산* 은 잘 하는데 *생성된 코드의 *성능* 을 평가* 못 함. *Lazy loading* 의 함정에 *AI 가 만든 코드* 가 *자주 빠짐*.

```java
// AI 가 만든 코드 (얼핏 자연스러움)
List<User> users = userRepo.findAll();
return users.stream()
    .map(u -> new UserDto(u.getName(), u.getOrders().size()))  // ❌ N+1!
    .toList();
```

해결책: `@EntityGraph` 또는 `JOIN FETCH`. AI 에게 *"N+1 발생 안 하게"* 명시 요청 필요.

**2. 복잡 join + projection**
AI 가 *3 개 이상 join* + *DTO projection* 작성 시 *어색한 JPQL*. MyBatis 가 더 직관적.

**3. Batch update / bulk delete**
JPA 의 `@Modifying` 쿼리는 *영속성 컨텍스트 무시*. AI 가 *주의사항* 자주 누락.

### 4.4 *AI 디버깅 난이도*

- **JPA**: 문제 = SQL 추측 → Hibernate 로그 (`show_sql=true`) → 실제 SQL 보고 진단. *추가 단계 필요*
- **MyBatis**: 문제 = *그 SQL 그대로*. *진단 1 단계 단축*

production 사고 시 *MyBatis 가 디버깅 빠름* (특히 AI 에게 SQL 분석 시킬 때).

---

## 5. *실측 비교* — Claude Code 와 GitHub Copilot 으로 실험

### 5.1 실험 1: "주문 조회 API" 생성

**프롬프트**: "사용자 ID 와 기간으로 주문 목록을 조회. 페이징 지원. 사용자 정보 같이 반환."

**JPA 결과 (Claude Code)**:
```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    @EntityGraph(attributePaths = {"user"})
    Page<Order> findByUserIdAndCreatedAtBetween(
        Long userId, Instant from, Instant to, Pageable pageable);
}
```
*완벽*. `@EntityGraph` 까지 자동 — N+1 회피.

**MyBatis 결과**:
```xml
<select id="findOrders" resultMap="OrderWithUserResultMap">
  SELECT o.*, u.id as user_id, u.name, u.email
  FROM orders o
  LEFT JOIN users u ON o.user_id = u.id
  WHERE o.user_id = #{userId}
    AND o.created_at BETWEEN #{from} AND #{to}
  ORDER BY o.created_at DESC
  LIMIT #{limit} OFFSET #{offset}
</select>
<!-- resultMap 별도 정의 필요 -->
```
*동작하지만* — `resultMap` 별도 생성, 페이징은 *수동* (limit/offset), `Page` 객체 추상화 없음. *작성량 2 배*.

→ **단순 CRUD: JPA + AI 가 압도적 효율**

### 5.2 실험 2: "월별 매출 통계 (윈도우 함수)"

**프롬프트**: "최근 12 개월 매출 합계 + 전월 대비 증감률. 매출 0 인 달도 포함."

**JPA 결과**:
```java
// AI 가 시도하지만...
@Query(value = """
    SELECT date_trunc('month', created_at), SUM(total_amount),
           LAG(SUM(total_amount)) OVER (ORDER BY date_trunc('month', created_at))
    FROM orders
    WHERE created_at >= :from
    GROUP BY 1
    """, nativeQuery = true)
List<Object[]> monthlySalesWithPrev(@Param("from") Instant from);
```
*Native query* 로 떨어짐. 결과는 `Object[]` — 타입 안전성 잃음. *JPA 의 장점 상실*.

**MyBatis 결과**:
```xml
<select id="monthlySales" resultType="MonthlySalesDto">
  WITH months AS (
    SELECT generate_series(
      date_trunc('month', NOW()) - INTERVAL '11 months',
      date_trunc('month', NOW()),
      '1 month'
    ) AS month
  ),
  sales AS (
    SELECT date_trunc('month', created_at) AS month,
           SUM(total_amount) AS total
    FROM orders
    WHERE created_at >= NOW() - INTERVAL '12 months'
    GROUP BY 1
  )
  SELECT m.month,
         COALESCE(s.total, 0) AS total,
         LAG(COALESCE(s.total, 0)) OVER (ORDER BY m.month) AS prev_total
  FROM months m
  LEFT JOIN sales s ON m.month = s.month
  ORDER BY m.month
</select>
```
*자연스러움*. PostgreSQL 의 `generate_series`, `WITH`, `LAG` 모두 활용. `MonthlySalesDto` 타입 안전.

→ **복잡 쿼리: MyBatis + AI 가 자연스러움**

### 5.3 실험 결과 매트릭스

| 시나리오 | JPA + AI | MyBatis + AI |
|---|---|---|
| 단순 CRUD | ⭐⭐⭐ | ⭐⭐ |
| Paging, Sorting | ⭐⭐⭐ (Spring Data) | ⭐⭐ (수동) |
| 동적 검색 | ⭐⭐ (QueryDSL 권장) | ⭐⭐⭐ |
| 통계 / 윈도우 함수 | ⭐ (native query 강제) | ⭐⭐⭐ |
| Bulk update | ⭐⭐ (`@Modifying` 주의) | ⭐⭐⭐ |
| Stored procedure | ⭐ | ⭐⭐⭐ |
| 도메인 모델링 | ⭐⭐⭐ (DDD 친화) | ⭐ (행 중심) |
| 테스트 작성 | ⭐⭐⭐ | ⭐⭐ |
| AI 가 첫 시도에 *맞는 코드* 생성 | ⭐⭐⭐ | ⭐⭐ |
| 실패 시 *AI 가 진단* | ⭐⭐ (SQL 추적 필요) | ⭐⭐⭐ |

---

## 6. 통일 vs 혼용 — 어떤 방향이 옳은가

### 6.1 *통일* 의 매력

- *단일 패턴* — 코드 리뷰 / 학습 곡선 / 인력 채용 단순
- *도구 일관성* — 마이그레이션, 테스트, 모니터링 통일
- *AI 의 컨텍스트 명확* — 한 가지 패턴만 알면 됨

### 6.2 *혼용* 의 매력

- *각자의 강점* 활용 — 80% JPA + 20% MyBatis 가 *생산성 최대*
- *현실의 다양성* 대응 — 복잡 쿼리는 어쩔 수 없이 native 가 필요한 순간 있음

### 6.3 *2026 년 5 월 권장 방향*

#### 권장 1: **새 프로젝트 → JPA + Spring Data 가 default, MyBatis 는 *복잡 영역만***

이유:
- AI 가 *JPA + Spring Data* 코드를 *가장 정확히* 생성
- 단순 CRUD 가 80% — JPA 가 *생산성 최대*
- 통계/배치/복잡 검색은 *별도 Module* 로 분리 → 거기만 MyBatis (또는 jOOQ)

구조 예시:
```
project/
  domain-core/         (JPA — Aggregate, Repository)
  query-side/          (MyBatis — 통계, 검색, 리포팅)
  batch/               (Spring Batch + JdbcTemplate)
```

CQRS (Command Query Responsibility Segregation) 자연스러움 — *Write 는 JPA*, *Read 는 MyBatis*.

#### 권장 2: **레거시 / 금융권 → MyBatis 유지, 신규 모듈만 JPA**

이유:
- 한국 금융권 / 공공기관 코드베이스 대부분 MyBatis
- 갑자기 JPA 로 *전환* 은 비현실적
- *새 모듈* 부터 JPA, *옛 모듈* 은 그대로

#### 권장 3: **둘 *완전 통일* 강요는 비추**

내 환경 (settlement, lemuel-xr, academy) 도 *둘 다* 사용. JPA 가 90%, MyBatis 가 10%. 잘 동작.

*혼용의 함정* 한 가지: *같은 Aggregate 를 JPA 와 MyBatis 가 동시에* 건드리면 *영속성 컨텍스트 + 캐시 동기화* 문제. 해결책 — *명확히 경계 분리*. *Write 는 한 가지로 통일*, *Read 는 자유*.

### 6.4 *통일* 이 정답인 경우

- *팀이 5 명 이하* 의 작은 회사 — 모두가 *한 가지* 만 마스터하는 게 빠름
- *MVP / 프로토타입* — 단순함이 우선
- *주니어 비중 높은 팀* — 두 가지는 학습 부담 ↑

### 6.5 *혼용* 이 정답인 경우

- *팀이 10 명 이상* + *영역별 책임 분리 가능*
- *Domain 복잡 + 통계 / 리포팅 많음*
- *시니어 비중 충분*

---

## 7. AI 활용 *실전 패턴*

### 7.1 JPA 코드 AI 에게 시킬 때

✅ **좋은 프롬프트:**
- "주문 조회 — userId 와 status 로 필터, 사용자 정보 같이, 페이징, N+1 회피, Spring Data JPA"

❌ **나쁜 프롬프트:**
- "주문 조회 SQL 짜줘" — AI 가 *MyBatis 인지 JPA 인지* 헷갈림

### 7.2 MyBatis 코드 AI 에게 시킬 때

✅ **좋은 프롬프트:**
- "PostgreSQL 16 기준, 최근 12개월 매출 통계, generate_series + LAG, 매출 0 인 달 포함, MyBatis XML"

❌ **나쁜 프롬프트:**
- "월별 매출 SQL" — DB 종류, NULL 처리 모호. AI 가 *환각*.

### 7.3 *AI 에게 항상 추가해야 할 컨텍스트*

```
- Spring Boot 3.4, Java 21
- DB: PostgreSQL 16 (또는 MySQL 8 / Oracle 19)
- JPA / MyBatis / 혼용 어느 것?
- 도메인 모델 (Entity 들 첨부)
- Convention: snake_case 컬럼명, UUID PK, soft delete 사용 등
```

이 컨텍스트 없으면 AI 가 *어색한* 코드 생성.

---

## 8. *5 년 후* — JPA / MyBatis 의 미래

### 8.1 JPA 의 미래

- Hibernate 7 (2024) 이후 *조금 더 직관적* — `org.hibernate.query.sqm` 같은 모던 API
- **Reactive JPA** (R2DBC) — 아직 *애매한 상태*
- **GraalVM Native Image** 호환성 개선 진행 중
- AI 코딩 도구와의 *시너지가 더 커질 전망*

### 8.2 MyBatis 의 미래

- Mybatis-Plus 같은 *JPA-like 추상화 레이어* 가 인기 (특히 중국)
- *XML 떠나기* 트렌드 — annotation-only 또는 *MyBatis Dynamic SQL* (Java DSL)
- 한국 시장 *영향력 유지*. 금융권 표준

### 8.3 *대안 — jOOQ*

- Type-safe SQL builder. JPA 의 안전성 + MyBatis 의 SQL 명확성
- 한국에서 *드물게 쓰이지만* 유럽/북미에선 인기
- AI 와의 시너지 *매우 좋음* (모든 게 type-safe)
- 단점: *유료 라이센스* (상용 DB 사용 시)

### 8.4 *Native + AOT* 시대의 ORM

GraalVM Native Image 가 Spring Boot 3 부터 정식 지원. 그러나:
- JPA: *Reflection 의존성* 으로 *AOT 설정 복잡*
- MyBatis: 더 직관적

*Native* 가 표준 될수록 MyBatis 의 상대 가치 *살짝 ↑*.

---

## 9. 결론 — *둘 다 살아남는다, 단 각자의 자리에서*

> **JPA 는 *객체 모델* 의 1 등 시민. MyBatis 는 *SQL* 의 1 등 시민.**
> 비즈니스 코드의 80% 는 *객체 모델* 이고, 20% 는 *SQL 자체* 가 본질이다.
> **그래서 80% JPA + 20% MyBatis 가 *2026 년 5 월의 sweet spot*.**

생성형 AI 의 영향:
- *코드 작성 능력* 의 commodity 화 → *어느 도구 쓸 것인가* 자체의 결정 비용 ↓
- *JPA 의 학습 곡선* 이 *AI 의 도움* 으로 *낮아짐*
- *MyBatis 의 SQL 작성* 도 *AI 의 도움* 으로 *빨라짐*
- 결국 *둘 다 더 쉽게* 쓸 수 있게 됨 → *원리* 만 알면 *어느 쪽도 OK*

리드의 결정:
- *팀 컨벤션* 명확히 — JPA 기본 / MyBatis 예외, 또는 그 반대
- *경계* 명확히 — *같은 Aggregate 를 두 도구가 동시 수정* 금지
- *AI 에게 컨텍스트 충분히* — 어떤 도구 / 어떤 DB / 어떤 컨벤션
- *N+1, 영속성 컨텍스트 함정* 은 *팀 트레이닝* 필수 — AI 가 *자주 빠뜨림*

내 환경에선 *JPA + Spring Data 가 default*, *복잡 통계는 MyBatis*. *AI 도구* 와 가장 잘 호환되는 조합. 2026 년 5 월 기준 *권장 패턴*.

---

## 참고

- [Spring Data JPA Reference](https://docs.spring.io/spring-data/jpa/reference/)
- [MyBatis 3 Reference](https://mybatis.org/mybatis-3/)
- [jOOQ Manual](https://www.jooq.org/learn/)
- *Java Persistence with Hibernate* — Bauer, King, Gregory (2015)
- *Effective Java 3rd Ed* — Joshua Bloch
- 관련 글:
  - [Spring Filter vs Interceptor — 네트워크 관점]({% post_url 2026-05-29-spring-filter-vs-interceptor-network-perspective %})
  - [JVM 구조와 Java 버전 변천사]({% post_url 2026-05-29-jvm-structure-java-version-evolution-production-impact %})
  - [DDD ↔ MSA]({% post_url 2026-05-29-ddd-msa-bounded-context-aggregate-event-storming %})
  - [개발 리드 30 년 변천사 + AI 시대]({% post_url 2026-05-29-engineering-leadership-evolution-overengineering-ai-era %})
