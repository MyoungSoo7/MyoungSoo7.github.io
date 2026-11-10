---
layout: post
title: "QueryDSL 사용사례와 성능 최적화 — 동적 쿼리부터 No-Offset·count 분리까지, 100만 건 실측"
date: 2026-11-10 23:47:52 +0900
categories: [backend, jpa]
tags: [querydsl, jpa, hibernate, performance, pagination, no-offset, spring-data]
---

QueryDSL은 JPQL(과 SQL, MongoDB 등)을 **문자열 대신 자바 코드로, 컴파일 타임 타입 체크를 받으며** 조립하게 해 주는 라이브러리입니다. 이 글은 두 가지를 다룹니다. 하나는 *어디에 쓰면 이득인가*(사용사례), 다른 하나는 *QueryDSL로 쓴 쿼리를 어떻게 빠르게 만드나*(성능)입니다. 성능 쪽은 주장만 하지 않고 직접 100만 건을 넣어 쟀습니다.

> 짝꿍 글: JPA·JPQL 자체(영속성 컨텍스트, N+1, fetch join, 벌크 연산 등)는 [JPA와 JPQL 사용사례와 성능 최적화](/2026/11/10/jpa-jpql-use-cases-performance-measured/)에서 다룹니다. 이 글은 QueryDSL 고유의 지점에 집중합니다.

## 0. 먼저 알아야 할 것 — 원본 프로젝트는 멈췄고, 포크가 이어받았다

- 원본 `com.querydsl` 의 마지막 릴리스는 **5.0.0(2021-07-22)** 입니다([릴리스 노트](https://github.com/querydsl/querydsl/releases/tag/QUERYDSL_5_0_0)). 5.0 릴리스 노트도 "2년 넘게 대체로 유지보수되지 않았다"고 스스로 적고 있습니다.
- 2023년 10월 OpenFeign 조직 아래 포크가 생겼습니다([OpenFeign/querydsl](https://github.com/OpenFeign/querydsl)). groupId는 `io.github.openfeign.querydsl` 이고, **자바 패키지(`com.querydsl.*`)와 API는 그대로**입니다. 그래서 의존성 좌표만 바꾸면 됩니다([마이그레이션 가이드](https://github.com/openfeign/querydsl/blob/master/docs/migration.md)). 6.0부터 Jakarta EE와 Java 17 이상을 요구하며, 이 글을 쓰는 시점(2026-11)의 Maven Central 최신 버전은 **7.7** 입니다.
- **Spring Data 공식 문서**도 이 포크를 언급합니다. "Querydsl 유지보수가 둔화되어 커뮤니티가 OpenFeign 아래로 포크했고, Spring Data는 이 포크를 best-effort로 지원한다"([Spring Data Commons — Querydsl Extension](https://docs.spring.io/spring-data/commons/reference/repositories/core-extensions.html)).

```groovy
// Gradle (Spring Boot 3+/Hibernate 6+)
implementation "io.github.openfeign.querydsl:querydsl-jpa:7.7"
annotationProcessor "io.github.openfeign.querydsl:querydsl-apt:7.7:jpa"
annotationProcessor "jakarta.persistence:jakarta.persistence-api"
```

### CVE-2024-49203 — `orderBy` 에 사용자 입력을 그대로 넣지 마라

- 내용: `PathBuilder.get(사용자입력)` 으로 정렬 경로를 만들면 HQL 인젝션이 됩니다([GHSA-6q3q-6v5j-h6vg](https://github.com/OpenFeign/querydsl/security/advisories/GHSA-6q3q-6v5j-h6vg)).
- 포크의 조치: 5.6.1 / 6.10.1 / 7.0 에서 **공백이 들어간 프로퍼티 이름을 거부**하도록 패치했습니다([PR #743](https://github.com/OpenFeign/querydsl/pull/743)).
- 원본 쪽: 원본 `com.querydsl` 은 패치가 나오지 않았습니다.
- 다툼이 있는 점: NVD 항목은 이 CVE를 **"disputed"** 로 표시합니다. 이유는 "신뢰할 수 없는 입력을 쿼리 구성에 직접 쓰는 개발자를 막는 것은 라이브러리의 책임이 아니다"라는 반론입니다([NVD CVE-2024-49203](https://nvd.nist.gov/vuln/detail/CVE-2024-49203)).

어느 쪽이 맞든 실무 결론은 같습니다. **정렬 키는 화이트리스트로 매핑합니다.**

```java
private static final Map<String, ComparableExpressionBase<?>> SORTABLE = Map.of(
        "id", order.id,
        "amount", order.amount,
        "createdAt", order.createdAt);

OrderSpecifier<?> toOrder(String key, boolean asc) {
    var path = SORTABLE.get(key);
    if (path == null) throw new IllegalArgumentException("unsupported sort: " + key);
    return asc ? path.asc() : path.desc();
}
```

## 1. 사용사례 — QueryDSL이 값을 하는 곳

### 1-1. 조건이 붙었다 떨어지는 검색 화면 (동적 쿼리)

관리자 검색처럼 "입력한 조건만 WHERE에 붙인다" 는 화면이 QueryDSL의 본업입니다. 조건마다 `BooleanExpression` 을 돌려주는 메서드를 만들고, **null을 반환하면 `where()` 가 그 조건을 무시**하는 성질을 이용합니다.

```java
public List<OrderDto> search(OrderSearch c) {
    return query
        .select(Projections.constructor(OrderDto.class, order.id, order.status, order.amount))
        .from(order)
        .where(statusEq(c.status()), amountGoe(c.minAmount()), memberIdEq(c.memberId()))
        .orderBy(order.id.desc())
        .limit(c.size())
        .fetch();
}

private BooleanExpression statusEq(String s)   { return s == null ? null : order.status.eq(s); }
private BooleanExpression amountGoe(Long min)  { return min == null ? null : order.amount.goe(min); }
private BooleanExpression memberIdEq(Long id)  { return id == null ? null : order.memberId.eq(id); }
```

`BooleanBuilder` 로도 같은 일을 할 수 있습니다. 하지만 조건을 **이름 있는 메서드**로 쪼개면 재사용(`statusEq(..).and(amountGoe(..))`)과 테스트가 쉬워집니다.

### 1-2. 화면용 DTO를 바로 뽑기 (Projection)

- `Projections.constructor(...)`: 생성자 순서로 매핑합니다. record와 잘 맞습니다.
- `Projections.fields(...)` / `Projections.bean(...)`: 필드나 setter 이름으로 매핑합니다. 별칭이 다르면 `.as("name")` 를 붙입니다.
- `@QueryProjection`: DTO 생성자에 붙이면 `QOrderDto` 가 생성되어 **컴파일 타임에** 인자 타입과 개수를 검사합니다. 대신 DTO가 QueryDSL에 의존하게 됩니다.

### 1-3. Spring Data와 붙이는 세 가지 방법

| 방법 | 언제 |
|---|---|
| `QuerydslPredicateExecutor<T>` 상속 | 단순 조건 조회. `findAll(Predicate, Pageable)` 이 바로 생김. 조인·프로젝션은 한계 |
| 커스텀 리포지토리(`XxxRepositoryCustom` + `Impl`)에서 `JPAQueryFactory` 사용 | 실무 대부분. 조인·DTO·서브쿼리 자유 |
| 별도 `@Repository` 쿼리 클래스 | 조회 전용 쿼리가 많을 때 CQRS식으로 분리 |

`QuerydslPredicateExecutor` 의 시그니처는 [Spring Data 공식 문서](https://docs.spring.io/spring-data/commons/reference/repositories/core-extensions.html)에 있습니다.

### 1-4. QueryDSL이 *안* 맞는 곳

- **JPQL의 한계는 그대로 물려받습니다.** FROM 절 서브쿼리, 윈도 함수, `UNION` 같은 것은 `querydsl-jpa` 로는 표현이 안 되거나 제한적입니다. 이런 통계성 쿼리는 `querydsl-sql`, jOOQ, 네이티브 쿼리가 맞습니다.
- `fetchCount()` 와 `fetchResults()` 가 deprecated된 이유도 같은 데서 나옵니다(아래 3장).

## 2. 실험 환경

| 항목 | 값 |
|---|---|
| 라이브러리 | OpenFeign QueryDSL 7.7, Hibernate ORM 7.4.15.Final, PostgreSQL JDBC 42.7.14 |
| DB | PostgreSQL 17.10 (로컬, 기본 설정, `ANALYZE` 후 측정) |
| JVM | OpenJDK 26, `-Xmx4g`, macOS(Apple Silicon 맥북 1대) |
| 데이터 | `orders` 1,000,000 건. status = PAID 60% / CANCELED 20% / SHIPPED 20%, `memo` 300자, 인덱스 `(status, id)` |
| 측정 | 각 항목 워밍업 2회 버린 뒤 5~7회 측정, **중앙값(ms)**. 매 회 새 EntityManager·트랜잭션. 전체를 2회 돌려 둘 다 표기 |
| 코드 | 본문 말미 "재현" 절 참고 |

DB와 앱이 **같은 맥북에 있어서** 네트워크 왕복이 거의 없습니다. 데이터도 대부분 메모리(버퍼 캐시)에 올라가 있습니다. 2회차가 1회차보다 전반적으로 1.5배쯤 느린 것은 같은 맥에서 다른 작업이 돌았기 때문으로 보입니다. 절대값이 아니라 **같은 회차 안에서의 상대 비교**로 읽어 주세요.

## 3. 성능 ① — 깊은 페이지: offset vs No-Offset

**문제.** `offset(n).limit(100)` 은 앞의 n행을 **읽은 뒤 버립니다.** 페이지가 뒤로 갈수록 버리는 양이 커집니다.

```java
// offset 방식
query.select(dto).from(order)
     .where(order.status.eq("PAID"))
     .orderBy(order.id.asc())
     .offset(offset).limit(100)
     .fetch();

// No-Offset(키셋) 방식 — 직전 페이지의 마지막 id 를 받는다
query.select(dto).from(order)
     .where(order.status.eq("PAID"), order.id.gt(lastId))
     .orderBy(order.id.asc())
     .limit(100)
     .fetch();
```

**실측 (중앙값, ms — 1회차 / 2회차)**

| 페이지 | offset | offset 방식 | No-Offset |
|---:|---:|---:|---:|
| 1 | 0 | 3.7 / 5.1 | 3.6 / 6.8 |
| 100 | 9,900 | 11.4 / 15.9 | 3.7 / 4.6 |
| 1,000 | 99,900 | 59.7 / 100.1 | 2.5 / 4.4 |
| 5,000 | 499,900 | **448.6 / 729.7** | **1.9 / 4.1** |

첫 페이지에서는 차이가 없습니다. 5,000번째 페이지에서는 **100~180배** 차이가 납니다. `EXPLAIN ANALYZE` 를 보면 이유가 드러납니다.

```
-- offset 499,900
Limit (actual rows=100)
  -> Index Scan using orders_pkey (actual rows=500000)
       Filter: status = 'PAID'   Rows Removed by Filter: 333332
Execution Time: 706 ms

-- No-Offset (id > 833167)
Limit (actual rows=100)
  -> Index Scan using orders_pkey (actual rows=100)
       Index Cond: (id > 833167)   Rows Removed by Filter: 68
Execution Time: 0.32 ms
```

offset 방식은 100행을 주려고 **약 83만 행을 훑습니다.** No-Offset은 168행만 봅니다.

**대가.** No-Offset으로는 "37페이지로 바로 이동" 같은 임의 점프를 할 수 없습니다. 그래서 **무한 스크롤, 더보기, 배치 처리**에 맞습니다. 정렬 키는 유일해야 하고, 유일하지 않으면 `(createdAt, id)` 처럼 동률을 깨는 키를 붙여야 합니다.

## 4. 성능 ② — count는 생각보다 비싸다: `fetchResults()` 를 버리는 이유

QueryDSL 5.0부터 JPA 모듈의 `fetchResults()` 와 `fetchCount()` 는 **deprecated** 입니다. Javadoc의 설명은 다음과 같습니다([AbstractJPAQuery](https://github.com/OpenFeign/querydsl/blob/master/querydsl-libraries/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/AbstractJPAQuery.java)).

- JPQL은 FROM 절 서브쿼리를 허용하지 않아서 `SELECT COUNT(*) FROM (원쿼리)` 를 만들 수 없습니다.
- 그래서 group by가 여러 개이거나 having이 있으면 **`fetch()` 로 전부 가져와 메모리에서 셉니다.** 큰 결과셋에서는 심각한 성능 저하가 생긴다고 경고합니다.

대안은 **본문 쿼리와 count 쿼리를 분리**하고, Spring Data의 `PageableExecutionUtils.getPage` 로 count를 *필요할 때만* 실행하는 것입니다. Javadoc 그대로 옮기면 "결과 크기와 `Pageable` 로 total을 알 수 있으면 count 쿼리를 생략"합니다. 예를 들어 첫 페이지인데 결과가 페이지 크기보다 작거나, 마지막 페이지인 경우입니다([PageableExecutionUtils](https://docs.spring.io/spring-data/commons/docs/current/api/org/springframework/data/support/PageableExecutionUtils.html)).

```java
public Page<OrderDto> search(OrderSearch c, Pageable pageable) {
    List<OrderDto> content = query
        .select(Projections.constructor(OrderDto.class, order.id, order.status, order.amount))
        .from(order)
        .where(statusEq(c.status()))
        .orderBy(order.id.desc())
        .offset(pageable.getOffset())
        .limit(pageable.getPageSize())
        .fetch();

    JPAQuery<Long> countQuery = query
        .select(order.count())     // 조인·정렬·프로젝션 없이 최소한으로
        .from(order)
        .where(statusEq(c.status()));

    return PageableExecutionUtils.getPage(content, pageable, countQuery::fetchOne);
}
```

**실측 (ms — 1회차 / 2회차)**

| 쿼리 | 시간 |
|---|---:|
| 첫 페이지 20건 조회 | 1.8 / 3.9 |
| 같은 조건의 count (60만 건 해당) | **115.7 / 250.4** |

count 하나가 페이지 조회보다 **60배 이상** 비쌉니다. 실행 계획은 `Parallel Seq Scan` 으로 테이블 전체를 훑습니다. 그러니 "전체 몇 건"이 정말 필요한 화면인지부터 다시 묻는 것이 가장 큰 최적화입니다. 무한 스크롤이면 `Slice` 처럼 `limit(size + 1)` 로 "다음이 있는가"만 판단하면 됩니다.

## 5. 성능 ③ — 존재 확인은 count가 아니라 `fetchFirst()`

```java
// 나쁨: 전부 센다
boolean exists = query.select(order.count()).from(order).where(cond).fetchOne() > 0;

// 좋음: 하나 찾으면 멈춘다 (LIMIT 1)
boolean exists = query.selectOne().from(order).where(cond).fetchFirst() != null;
```

| 방법 | 시간 (ms, 1회차 / 2회차) |
|---|---:|
| `count() > 0` | 134.2 / 235.4 |
| `selectOne().fetchFirst()` | **2.1 / 3.2** |

`fetchFirst()` 는 `limit(1).fetchOne()` 이라 SQL에 `LIMIT 1` 이 붙습니다. 실행 계획상 1행을 찾는 즉시 끝납니다(0.13 ms). JPQL에는 `select exists(...)` 형태가 없기 때문에 이 패턴이 사실상의 exists입니다.

## 6. 성능 ④ — 필요한 컬럼만: DTO Projection / ⑤ 대량 수정은 벌크로

**DTO Projection.** 엔티티를 조회하면 모든 컬럼(예제에서는 300자 `memo` 포함)을 읽습니다. 그리고 영속성 컨텍스트가 각 엔티티의 **스냅샷**을 보관해 더티 체킹에 씁니다. 읽기 전용 목록에는 둘 다 낭비입니다.

| 5만 건 조회 | 시간 (ms, 1회차 / 2회차) |
|---|---:|
| `selectFrom(order)` 엔티티 | 197.5 / 299.5 |
| `Projections.constructor(OrderDto, id, status, amount)` | **53.0 / 79.8** |

약 **3.7배** 빠릅니다. 엔티티로 받아야 하는데 읽기 전용이라면 하이버네이트 read-only 힌트로 스냅샷 비용만 줄이는 방법도 있습니다.

**벌크 update.** 엔티티를 조회해서 필드를 바꾸면, 하이버네이트는 엔티티마다 UPDATE를 하나씩 만듭니다(`jdbc.batch_size` 로 묶어 보내더라도 문장 수는 같습니다). 같은 값으로 일괄 수정한다면 QueryDSL 벌크 연산 한 줄이면 됩니다.

```java
long updated = query.update(order)
        .set(order.amount, newAmount)
        .where(order.id.loe(10_000L))
        .execute();
em.clear();   // 벌크 연산은 영속성 컨텍스트를 우회한다 — 이후 조회 전 반드시 비울 것
```

| 1만 건 수정 | 시간 (ms, 1회차 / 2회차) |
|---|---:|
| 조회 후 더티 체킹 (`batch_size=1000`) | 584.6 / 878.4 |
| `update().set().where().execute()` | **316.5 / 435.0** |

약 **2배** 빠릅니다. 대신 벌크 연산은 **영속성 컨텍스트와 2차 캐시를 거치지 않습니다.** 같은 트랜잭션에서 이미 읽어 둔 엔티티는 옛 값을 들고 있게 됩니다. 그래서 `em.clear()`(Spring Data라면 `@Modifying(clearAutomatically = true)`)가 짝으로 따라와야 합니다([Hibernate User Guide — Batching](https://docs.jboss.org/hibernate/orm/7.0/userguide/html_single/Hibernate_User_Guide.html#batch)).

### 재현

측정 코드의 뼈대입니다. 워밍업 2회를 버리고 5~7회 측정해 중앙값을 냅니다. 매 측정마다 새 `EntityManager` 와 트랜잭션을 씁니다.

```java
static double median(int runs, Supplier<?> s) {
    for (int i = 0; i < 2; i++) s.get();          // warm-up
    double[] t = new double[runs];
    for (int i = 0; i < runs; i++) {
        long st = System.nanoTime();
        s.get();
        t[i] = (System.nanoTime() - st) / 1e6;
    }
    Arrays.sort(t);
    return t[runs / 2];
}
```

> **측정하다 밟은 함정.** 처음에는 H2 in-memory로 쟀습니다. 그러자 count 60만 건이 2 ms, 깊은 offset도 3 ms로 나왔습니다. H2가 **같은 SQL의 결과를 캐시**(`QUERY_CACHE_SIZE`, 기본 8)해서 반복 측정이 전부 캐시 히트였기 때문입니다. 캐시를 끄자 이번에는 `ORDER BY id` 를 인덱스로 풀지 못하고 60만 건을 정렬해서, 첫 페이지조차 600 ms가 걸렸습니다. **H2 수치로는 결론을 낼 수 없어서** 로컬 PostgreSQL 17로 다시 쟀습니다. 이 글의 표는 전부 PostgreSQL 수치입니다.


## 7. 정리 — 체크리스트

1. 의존성은 **`io.github.openfeign.querydsl`** 로 옮깁니다. API와 패키지가 같아 좌표만 바꾸면 됩니다.
2. 정렬과 필드 선택에 **사용자 입력을 `PathBuilder` 로 바로 넘기지 않습니다.** 화이트리스트로 매핑합니다.
3. 동적 조건은 **null을 반환하는 `BooleanExpression` 메서드**로 쪼갭니다.
4. 목록 화면은 **DTO Projection** 으로 필요한 컬럼만 가져옵니다.
5. 깊은 페이지가 생기는 목록(무한 스크롤, 배치)은 **No-Offset(`id < lastId`)** 으로 바꿉니다.
6. `fetchResults()` 대신 **`fetch()` + 별도 count 쿼리 + `PageableExecutionUtils.getPage`** 를 씁니다. count가 정말 필요한 화면인지부터 다시 묻습니다.
7. 존재 여부는 **`selectOne()...fetchFirst() != null`** 로 확인합니다.
8. 대량 수정은 **벌크 update**로 하고, 직후에 영속성 컨텍스트를 비웁니다.

## 근거의 한계

- **성능 수치는 이 글 작성자가 맥북 1대(로컬 PostgreSQL 17, 기본 설정)에서 잰 단일 환경 측정**입니다. 운영 DB에서는 디스크·버퍼 풀·네트워크·동시 부하·옵티마이저 차이로 배수가 달라집니다. MySQL(InnoDB)은 count와 offset의 내부 동작이 달라 배수도 다를 수 있습니다. 특히 count 비용과 커버링 인덱스 효과는 DB 엔진에 크게 좌우됩니다. 중립 제3자가 QueryDSL 버전별로 비교한 벤치마크는 찾지 못했습니다.
- QueryDSL 자체가 쿼리를 빠르게 만들지는 않습니다. QueryDSL은 JPQL을 **조립**할 뿐이고, 실행 계획은 DB가 정합니다. 위 차이는 모두 **어떤 쿼리를 조립했느냐**의 차이입니다.
- 포크의 유지보수 지속성은 README가 밝히듯 **사실상 한 명의 메인테이너**에게 크게 의존합니다. Spring Data의 지원도 "best-effort" 입니다. 장기 의존성 리스크로 계산에 넣어야 합니다.
- CVE-2024-49203은 NVD에서 "disputed" 상태입니다. 심각도 평가는 자료마다 다를 수 있습니다.

## References

1. Querydsl 5.0.0 Release Notes — <https://github.com/querydsl/querydsl/releases/tag/QUERYDSL_5_0_0>
2. OpenFeign/querydsl README — <https://github.com/OpenFeign/querydsl>
3. OpenFeign/querydsl Migration Guide — <https://github.com/openfeign/querydsl/blob/master/docs/migration.md>
4. Spring Data Commons Reference — Querydsl Extension — <https://docs.spring.io/spring-data/commons/reference/repositories/core-extensions.html>
5. Spring Data `PageableExecutionUtils` Javadoc — <https://docs.spring.io/spring-data/commons/docs/current/api/org/springframework/data/support/PageableExecutionUtils.html>
6. `AbstractJPAQuery#fetchCount` / `#fetchResults` deprecation Javadoc — <https://github.com/OpenFeign/querydsl/blob/master/querydsl-libraries/querydsl-jpa/src/main/java/com/querydsl/jpa/impl/AbstractJPAQuery.java>
7. GHSA-6q3q-6v5j-h6vg (CVE-2024-49203) — <https://github.com/OpenFeign/querydsl/security/advisories/GHSA-6q3q-6v5j-h6vg>
8. OpenFeign/querydsl PR #743 (Fix for CVE-2024-49203) — <https://github.com/OpenFeign/querydsl/pull/743>
9. NVD CVE-2024-49203 — <https://nvd.nist.gov/vuln/detail/CVE-2024-49203>
10. Hibernate ORM User Guide — Batch / Bulk operations — <https://docs.jboss.org/hibernate/orm/7.0/userguide/html_single/Hibernate_User_Guide.html#batch>
