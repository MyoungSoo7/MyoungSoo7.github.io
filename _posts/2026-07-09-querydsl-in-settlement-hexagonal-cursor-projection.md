---
layout: post
title: "정산 시스템 에 적용한 QueryDSL — 헥사고날 · 커서 페이징 · 프로젝션 실전"
date: 2026-07-09 20:10:00 +0900
categories: [backend, jpa, querydsl, architecture]
tags: [querydsl, jpa, hexagonal, cursor-pagination, projection, n+1, settlement, spring-boot]
---

정산(settlement) 시스템 의 조회 계층 은 전부 **QueryDSL** 로 짰다. 단순 CRUD 면 Spring Data JPA 로 충분 하지만, 정산 은 *동적 검색 · 대용량 페이징 · 집계 · 대사(reconciliation)* 가 핵심 이라 — 문자열 JPQL 로는 감당 이 안 된다. 이 글 은 *실제 코드* 로 QueryDSL 을 어떻게 붙였는지 정리 한다.

---

## 1. 왜 QueryDSL 인가 — 3가지 이유

- **타입 안전** — 컬럼명 오타 가 *컴파일 에러*. 문자열 JPQL 은 런타임 에야 터진다.
- **동적 쿼리** — 검색 조건 이 8개 인데 다 optional. `if` 로 `where` 를 조립 해야 하는데, JPQL 문자열 concat 은 지옥 이다.
- **프로젝션** — 엔티티 를 통째 로 로딩 하지 않고 *필요한 컬럼만* DTO 로 바로 뽑는다. N+1 도, 불필요 로딩 도 없다.

## 2. 설정 — Gradle + Bean 하나

Spring Boot 3 / Jakarta 기준. QueryDSL 5.0.0 의 `jakarta` 분류자 를 써야 한다:

```kotlin
implementation("com.querydsl:querydsl-jpa:5.0.0:jakarta")
annotationProcessor("com.querydsl:querydsl-apt:5.0.0:jakarta")
annotationProcessor("jakarta.annotation:jakarta.annotation-api")
annotationProcessor("jakarta.persistence:jakarta.persistence-api")

// 생성 위치 를 build/generated/querydsl 로 고정 (clean 시 함께 삭제)
val querydslDir = layout.buildDirectory.dir("generated/querydsl")
tasks.withType<JavaCompile>().configureEach {
    options.generatedSourceOutputDirectory.set(querydslDir.get().asFile)
}
```

APT(Annotation Processor) 가 `@Entity` 마다 **Q타입** (`QSettlementJpaEntity`) 을 생성 한다. 이게 타입 안전 의 실체 — 컬럼 을 `settlement.settlementDate` 처럼 *필드 로* 접근 한다.

그리고 Bean 하나:

```java
@Configuration
public class QueryDslConfig {
    @PersistenceContext private EntityManager entityManager;

    @Bean
    public JPAQueryFactory jpaQueryFactory() {
        return new JPAQueryFactory(entityManager);
    }
}
```

## 3. 헥사고날 — QueryDSL 은 *어댑터* 다

여기 가 설계 포인트. 정산 은 헥사고날(ports & adapters) 이라, QueryDSL 코드 가 *애플리케이션 계층 에 새는 것* 을 막아야 한다.

```
application/port/out/QuerySettlementPort   ← 인터페이스 (도메인 언어)
        ▲ 구현
adapter/out/persistence/querydsl/
    SettlementQueryRepositoryImpl          ← QueryDSL 은 여기 갇힘
```

애플리케이션 서비스 는 `QuerySettlementPort` 만 안다. `JPAQueryFactory` · `Projections` · `BooleanBuilder` 같은 QueryDSL 타입 은 **어댑터 밖 으로 절대 안 나간다.** 나중 에 조회 를 네이티브 SQL 이나 다른 기술 로 갈아도 포트 시그니처 는 그대로 — 코어 는 무사 하다.

## 4. 프로젝션 — 엔티티 안 부르고 DTO 로 바로

정산 상세 는 settlement · payment · order · user · product **5개** 를 조인 한다. 엔티티 로 로딩 하면 N+1 지옥 이다. QueryDSL 은 `Projections.constructor` 로 *단일 쿼리 + DTO 직행*:

```java
List<SettlementDetailDto> items = queryFactory
    .select(Projections.constructor(SettlementDetailDto.class,
            settlement.id,
            settlement.paymentAmount,
            settlement.netAmount,
            settlement.status,
            settlement.settlementDate,
            order.orderId,
            payment.paymentMethod,
            user.email,
            product.name.coalesce("")
    ))
    .from(settlement)
    .join(payment).on(settlement.paymentId.eq(payment.paymentId))
    .join(order).on(settlement.orderId.eq(order.orderId))
    .join(user).on(order.userId.eq(user.userId))
    .leftJoin(product).on(order.productId.eq(product.productId))
    .where(where)
    .orderBy(buildOrderSpecifier(condition))
    .limit(fetchSize + 1)
    .fetch();
```

5개 테이블 을 **쿼리 한 방** 에 조인 해서 필요한 필드만 DTO 로 채운다. 엔티티 그래프 를 안 만드니 지연로딩 도, N+1 도 원천 봉쇄.

## 5. 동적 검색 — BooleanBuilder

검색 조건 8개 가 전부 optional. `BooleanBuilder` 로 *있는 조건만* `and` 로 쌓는다:

```java
private BooleanBuilder buildSearchWhere(SettlementSearchCondition c) {
    BooleanBuilder b = new BooleanBuilder();

    if (hasText(c.getStatus()))     b.and(settlement.status.eq(c.getStatus()));
    if (c.getStartDate() != null)   b.and(settlement.settlementDate.goe(c.getStartDate()));
    if (c.getEndDate() != null)     b.and(settlement.settlementDate.loe(c.getEndDate()));
    if (c.getUserId() != null)      b.and(order.userId.eq(c.getUserId()));
    if (hasText(c.getProductName()))b.and(product.name.containsIgnoreCase(c.getProductName()));
    if (Boolean.TRUE.equals(c.getIsRefunded()))
        b.and(settlement.refundedAmount.gt(BigDecimal.ZERO));

    return b;
}
```

`null` 이면 조건 이 안 붙는다. 이걸 JPQL 문자열 로 짜면 — `WHERE 1=1` 뒤 에 조건 을 concat 하는, 그 악명 높은 코드 가 된다. QueryDSL 은 이 문제 를 우아하게 없앤다.

## 6. 커서 페이징 — OFFSET 을 버린 이유

정산 목록 은 수백만 건. `OFFSET 100000 LIMIT 20` 은 **뒤로 갈수록 느려진다** — DB 가 앞 10만 건 을 세고 버리기 때문. 그래서 **커서 기반** 으로 갔다. 복합 커서 `(settlementDate, id)`:

```java
private BooleanExpression cursorCondition(LocalDate cursorDate, Long cursorId, boolean isDesc) {
    if (isDesc) {
        return settlement.settlementDate.lt(cursorDate)
                .or(settlement.settlementDate.eq(cursorDate)
                        .and(settlement.id.lt(cursorId)));   // 날짜 같으면 id 로 tie-break
    }
    return settlement.settlementDate.gt(cursorDate)
            .or(settlement.settlementDate.eq(cursorDate)
                    .and(settlement.id.gt(cursorId)));
}
```

날짜 로 자르고, *날짜 가 같은 경계* 는 id 로 끊는다. 인덱스 `(settlement_date, id)` 를 그대로 타서 **O(log n)** — 100만 번째 페이지 도 첫 페이지 와 같은 속도. `limit(fetchSize + 1)` 로 **1건 더 뽑아** `hasNext` 를 판정 하고, 마지막 행 의 `(date, id)` 를 다음 커서 로 반환 한다.

## 7. 집계 — CASE WHEN · coalesce · date_trunc

일/월별 요약 은 순수 집계. QueryDSL 로 조건부 카운트 와 합계 를:

```java
// 상태별 건수 = SUM(CASE WHEN status = ? THEN 1 ELSE 0)
private NumberExpression<Long> statusCount(String status) {
    return Expressions.cases()
            .when(settlement.status.eq(status)).then(1L)
            .otherwise(0L)
            .sum();
}

// 합계는 NULL 방어까지 — SUM(...) 이 null 이면 0
settlement.paymentAmount.sum().coalesce(BigDecimal.ZERO)
```

월별 그룹핑 은 PostgreSQL 의 `date_trunc` 가 필요 한데, QueryDSL 기본 에 없다. `dateTemplate` 으로 SQL 함수 를 직접 끼운다:

```java
var monthExpr = Expressions.dateTemplate(LocalDate.class,
        "CAST(date_trunc('month', {0}) AS date)", settlement.settlementDate);
// 이후 select · groupBy · orderBy 에 monthExpr 재사용
```

DSL 이 못 감싸는 DB 고유 함수 도 이렇게 *탈출구* 가 있다. 완전히 갇히지 않는다는 게 실무 에서 중요.

## 8. 정산 다운 활용 — 대사(Reconciliation)

QueryDSL 이 진짜 로 빛나는 정산 특유 의 쿼리 — **불일치 탐지**. `payments.amount ≠ settlements.payment_amount` 면 정산 생성 버그, 환불액 이 어긋나면 반영 누락:

```java
.where(
    settlement.settlementDate.goe(startDate),
    settlement.settlementDate.loe(endDate),
    payment.amount.ne(settlement.paymentAmount)
        .or(payment.refundedAmount.ne(settlement.refundedAmount))
)
```

두 테이블 의 값 을 **컬럼 대 컬럼 으로 비교** 하는 조건 을 타입 안전 하게 표현 한다. 이런 대사 쿼리 를 문자열 로 관리 하면 유지보수 가 불가능 하다.

## 9. 동적 정렬 — switch 로 OrderSpecifier

정렬 기준 도 런타임 파라미터. `OrderSpecifier[]` 를 스위치 로 만든다 (2차 정렬 로 항상 id 를 붙여 **정렬 안정성** 확보):

```java
return switch (sortBy) {
    case "amount" -> desc
        ? new OrderSpecifier[]{settlement.paymentAmount.desc(), settlement.id.desc()}
        : new OrderSpecifier[]{settlement.paymentAmount.asc(), settlement.id.asc()};
    default -> desc
        ? new OrderSpecifier[]{settlement.settlementDate.desc(), settlement.id.desc()}
        : new OrderSpecifier[]{settlement.settlementDate.asc(), settlement.id.asc()};
};
```

---

## 정리 — QueryDSL 이 정산 에 준 것

| 요구 | QueryDSL 해법 |
|---|---|
| 컬럼 오타 방지 | Q타입 → 컴파일 타임 검증 |
| optional 8조건 검색 | `BooleanBuilder` 동적 `and` |
| 수백만 건 페이징 | 복합 커서 `(date, id)` → O(log n) |
| 5테이블 조회 N+1 | `Projections.constructor` 단일 쿼리 DTO |
| 상태별 집계 | `Expressions.cases()` + `coalesce` |
| DB 고유 함수 | `dateTemplate` 탈출구 |
| 대사 불일치 | 컬럼 대 컬럼 `ne().or()` |

그리고 이 모든 것 을 **헥사고날 어댑터 안 에 가둬서** — 애플리케이션 코어 는 QueryDSL 을 모른다. 조회 기술 은 언제든 갈 수 있고, 도메인 은 그대로 남는다. *타입 안전 · 동적 · 프로젝션* 이 세 가지 가, 문자열 JPQL 로는 못 짤 조회 계층 을 가능 하게 했다.

---

_관련: [백엔드 설계 의 세 축]({% post_url 2026-07-07-backend-design-three-axes %})_
