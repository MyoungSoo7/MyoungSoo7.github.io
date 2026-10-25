---
layout: post
title: "JPA 의 장점 — '편하다' 말고, 스펙이 '반드시 해야 한다'고 적은 것만 추려봤다"
date: 2026-10-26 01:37:12 +0900
categories: [backend]
tags: [jpa, jakarta-persistence, hibernate, orm, optimistic-lock, persistence-context, spring]
---

"JPA 의 장점" 을 검색하면 거의 같은 목록이 나온다. 생산성, 유지보수, 패러다임 불일치 해결, DB 독립성. 다 맞는 말이다. 하지만 그 대부분은 **잘 쓰면** 얻는 효과이지, 누가 보장해주는 것은 아니다.

이 글은 기준을 바꿔서 본다. **Jakarta Persistence 스펙과 API 문서가 구현체에게 *의무*로 지운 것**만 장점으로 센다. 의무라면 Hibernate 든 EclipseLink 든, 스펙을 지키는 구현체 위에서는 성립해야 한다. 기준 버전은 **Jakarta Persistence 3.2**(2024-04-10)다.[^spec32]

JPA 를 PSA(이식 가능한 서비스 추상화) 관점에서 층층이 뜯어본 글은 [이쪽]({% post_url 2026-07-08-jpa-through-the-lens-of-psa %}), MySQL·MSSQL·Oracle 을 동시에 쓸 때 JPA 가 무엇을 흡수하고 무엇을 못 하는지는 [이쪽]({% post_url 2026-09-14-three-dbms-at-once-what-jpa-absorbs %})에 있다. 여기서는 겹치지 않게 "보장" 에만 집중한다.

---

## 1. 같은 행은 한 트랜잭션 안에서 같은 객체다 — 동일성 보장

`EntityManager` API 문서는 영속성 컨텍스트를 이렇게 정의한다. *"주어진 영속 엔티티 식별자(엔티티 타입 + 기본키)마다 **엔티티 인스턴스가 최대 하나**인 엔티티 인스턴스들의 집합."*[^em]

```java
Order a = em.find(Order.class, 42L);
Order b = em.createQuery("select o from Order o where o.id = 42", Order.class)
            .getSingleResult();
assert a == b;   // equals 가 아니라 == 다
```

JDBC 나 SQL 매퍼로 같은 행을 두 번 읽으면 객체가 두 개 생긴다. 그러면 한쪽을 고친 뒤 다른 쪽을 저장해 변경을 덮어쓰는 버그가 생길 수 있다. JPA 에서는 같은 영속성 컨텍스트 안에서 이 일이 구조적으로 생기지 않는다. 같은 문서는 이것을 **1차 캐시(first-level cache)** 라고 부르고, 2차 캐시와의 상호작용도 API 로 제어하게 해 두었다(`setCacheRetrieveMode`, `setCacheStoreMode`).[^em]

## 2. 버전 컬럼 하나로 "잃어버린 갱신" 이 막힌다 — 낙관적 락이 의무다

내가 보기에 JPA 의 가장 과소평가된 장점이다. 3.2 API 문서는 `@Version` 을 *"낙관적 락 실패를 감지하는 데 쓰이는"* 필드로 정의하고, 읽은 뒤 갱신·삭제하기 전에 DB 의 버전이 바뀌었으면 실패로 본다.[^version] 스펙 원문 저장소의 3장은 이것을 **"must"** 로 더 분명하게 적는다(아래 인용은 차기 버전을 개발 중인 master 브랜치 문구다).

> 영속성 공급자는 버전이 있는 모든 엔티티에 대해 낙관적 락을 **자동으로 수행해야 한다**.[^spec-ch3]

충돌이 감지되면 공급자는 **`OptimisticLockException` 을 던지고 현재 트랜잭션을 롤백 대상으로 표시해야 한다.** 엔티티 상태를 DB 에 쓸 때마다 버전을 올려야 하고, 메모리의 버전과 DB 의 버전을 비교해야 한다. detach 됐다가 `merge` 되는 엔티티도 버전을 검사해야 한다.[^spec-ch3]

```java
@Entity
class Settlement {
    @Id Long id;
    BigDecimal amount;
    @Version Instant lastUpdated;   // 3.2 부터 Instant · LocalDateTime 도 허용
}
```

`@Version` 타입은 `int`·`long` 류, `Timestamp`, 그리고 3.2 에서 추가된 `Instant`·`LocalDateTime` 이다.[^version][^spec32] 스펙은 한 걸음 더 나아가 **동시에 접근될 수 있는 모든 엔티티에 낙관적 락을 켜라고 "강하게 권한다"**. 그렇지 않으면 잃어버린 갱신을 막을 책임이 애플리케이션으로 넘어간다고 적고 있다.[^spec-ch3]

SQL 을 직접 쓰는 방식이라면 같은 보호를 얻기 위해 모든 `UPDATE` 에 `WHERE version = ?` 를 붙이고, 영향받은 행 수를 확인하고, 0 이면 예외를 던지는 코드를 **매번** 써야 한다. JPA 에서는 애노테이션 하나다. 재시도 설계까지 포함한 실전 이야기는 [예전 글]({% post_url 2026-06-29-db-optimizer-and-jpa-optimistic-lock-retry-defense %})에 있다.

## 3. 비관적 락도 DB 문법 없이 의도만 적는다

`LockModeType` 은 락의 *의미*를 정의한다. `PESSIMISTIC_READ` 와 `PESSIMISTIC_WRITE` 를 요청하면 공급자는 **dirty read 와 non-repeatable read 가 일어나지 않도록 보장해야 하고**, 버전이 없는 엔티티에도 이 두 락을 지원해야 한다. 락 획득에 실패했을 때 던질 예외도 상황별로 정해져 있다. 트랜잭션 단위 롤백이면 `PessimisticLockException`, 문장 단위 롤백이면 `LockTimeoutException`(이 경우 트랜잭션을 롤백 대상으로 표시하면 *안 된다*)이다.[^lockmode]

```java
em.find(Account.class, id, LockModeType.PESSIMISTIC_WRITE);
```

이 한 줄이 DB 마다 어떤 SQL 이 되는지는 구현체의 **Dialect** 가 맡는다. Hibernate 문서는 Dialect 를 *"특정 DB 와 통신하는 방식의 모든 차이 — 시퀀스 값을 얻는 법, SELECT 를 구성하는 법 등 — 를 캡슐화한 것"* 이라고 설명한다.[^hb-port] (Dialect 는 Hibernate 의 장치이지 스펙의 의무는 아니다. 스펙이 보장하는 것은 *의미*이고, 문법 변환은 구현체가 한다.)

## 4. 예외가 벤더 중립적이다

위의 `OptimisticLockException`, `PessimisticLockException`, `LockTimeoutException` 은 모두 `jakarta.persistence` 패키지의 타입이다.[^lockmode][^spec-ch3] 그래서 재시도 로직이 "Oracle 에서는 ORA-xxxxx, MySQL 에서는 에러코드 1213" 같은 벤더 코드 분기를 몰라도 된다. Spring 을 쓰면 이것이 한 번 더 `DataAccessException` 계층으로 번역되는데, 그 층은 [PSA 글]({% post_url 2026-07-08-jpa-through-the-lens-of-psa %})에서 다뤘다.

## 5. 쿼리 언어가 계속 표준으로 확장된다

JPQL 과 Criteria API 는 엔티티 모델을 대상으로 쿼리한다. 3.2 에서 표준에 들어온 것만 봐도 "표준이라 표현력이 부족하다" 는 비판의 범위가 계속 줄고 있다.[^spec32]

- JPQL·Criteria 에 `union`·`intersect`·`except`, `cast`, `left`·`right`·`replace`, `||` 연결 연산자
- `ORDER BY` 의 null 우선순위 지정
- `getSingleResultOrNull()`: 결과 없음이 예외가 아니라 `null`
- Java `record` 를 embeddable 로 사용
- 스키마를 프로그래밍 방식으로 다루는 `SchemaManager` API
- `EntityManagerFactory.runInTransaction()` / `callInTransaction()`

전부 *스펙*에 들어갔으므로 특정 구현체의 확장 문법(HQL 전용 기능 등)에 묶이지 않는다.

## 6. 식별자 생성의 이식성 — 단, 대가를 알고 쓸 때

DB 마다 키 생성 방식(시퀀스 vs IDENTITY)이 다르다. Hibernate 의 enhanced 생성기 `SequenceStyleGenerator` 는 시퀀스가 없는 DB 에서 **테이블로 시퀀스를 흉내 내어** 의미를 맞춘다.[^hb-port]

다만 같은 문서 계열의 성능 가이드는 대가도 분명히 적는다. **`IDENTITY` 생성기는 INSERT 의 JDBC 배치를 끈다.** 그리고 `TABLE` 생성기는 이식성 문제는 해결하지만 별도 트랜잭션과 행 락으로 시퀀스를 흉내 내기 때문에 성능이 나쁘다.[^hb-bp] 장점을 "DB 를 바꿔도 코드가 그대로" 까지만 믿고, 성능까지 같다고 믿으면 안 된다는 뜻이다.

---

## 장점이 아닌 것 — 같은 출처들이 경고하는 것

공정하게 하려면 같은 1차 출처들이 적은 한계도 같이 봐야 한다.

- **너무 많이 가져오는 것이 대부분 JPA 앱의 1번 성능 문제다.** Hibernate 성능 가이드의 표현이다. 엔티티 쿼리는 *가져온 엔티티를 수정할 때*, 곧 자동 변경 감지(dirty checking)의 이득을 볼 때만 유용하다. 읽기 전용이면 **DTO 프로젝션**을 쓰라고 권한다.[^hb-bp] 위의 1~2장(동일성·변경 감지·버전)은 *관리되는 엔티티*에만 붙는 장점이라서, 조회 전용 화면에서는 오히려 비용이 된다.
- **버전이 없는 엔티티는 보호받지 못한다.** 버전 있는 엔티티와 없는 엔티티가 섞여 merge 되면, 공급자는 버전 있는 쪽만 검사하면 되고 **객체 그래프 전체의 일관성은 보장되지 않는다**고 스펙에 적혀 있다.[^spec-ch3]
- **트랜잭션 의미론 차이는 흡수하지 못한다.** 격리 수준 기본값, 빈 문자열과 NULL 처리 같은 것들은 Dialect 아래로 그대로 새어 나온다. 세 DB 사례는 [앞의 글]({% post_url 2026-09-14-three-dbms-at-once-what-jpa-absorbs %})에 정리했다.

## 요약

| 장점 | 보장 근거 | 성립 조건 |
|---|---|---|
| 같은 행 = 같은 객체 | `EntityManager` 의 영속성 컨텍스트 정의[^em] | 같은 영속성 컨텍스트 안 |
| 잃어버린 갱신 방지 | 스펙 3장: 공급자가 자동 낙관적 락을 **수행해야 함**[^spec-ch3] | `@Version` 이 있을 때만 |
| DB 문법 없는 비관적 락 | `LockModeType` 의미 정의[^lockmode] | 문법 변환은 구현체 Dialect |
| 벤더 중립 예외 | `jakarta.persistence` 예외 타입 | — |
| 표준 쿼리 표현력 확장 | Jakarta Persistence 3.2 변경 목록[^spec32] | 3.2 구현체 |
| 키 생성 이식성 | Hibernate enhanced 생성기[^hb-port] | 성능은 DB 마다 다름[^hb-bp] |

"JPA 가 편하다" 는 주관이다. 반면 **"버전 컬럼 하나면 구현체가 잃어버린 갱신을 막아야 한다"** 는 스펙에 적힌 의무다. 도입을 설득할 때는 후자로 말하는 편이 반박하기 어렵다.

---

## References

[^spec32]: Eclipse Foundation, *Jakarta Persistence 3.2* — 릴리스 변경 목록(2024-04-10). <https://jakarta.ee/specifications/persistence/3.2/> · 스펙 PDF: <https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.pdf>
[^em]: Jakarta Persistence 3.2 API, *EntityManager* — 영속성 컨텍스트 정의, flush, 1차·2차 캐시 상호작용. <https://jakarta.ee/specifications/persistence/3.2/apidocs/jakarta.persistence/jakarta/persistence/entitymanager>
[^spec-ch3]: Jakarta Persistence 스펙 원문 저장소(master, 차기 버전 개발 중), Chapter 3 *Entity Operations* — Optimistic Locking / Entity Versions. 3.2 릴리스 문구와 다를 수 있다. <https://github.com/jakartaee/persistence/blob/master/spec/src/main/asciidoc/ch03-entity-operations.adoc>
[^version]: Jakarta Persistence 3.2 API, *Version*. <https://jakarta.ee/specifications/persistence/3.2/apidocs/jakarta.persistence/jakarta/persistence/version>
[^lockmode]: Jakarta Persistence 3.2 API, *LockModeType*. <https://jakarta.ee/specifications/persistence/3.2/apidocs/jakarta.persistence/jakarta/persistence/lockmodetype>
[^hb-port]: Hibernate ORM User Guide, *Database Portability Considerations* — Dialect, 식별자 생성. <https://docs.hibernate.org/orm/5.2/userguide/html_single/chapters/portability/Portability.html> (최신판 목차: <https://docs.hibernate.org/stable/orm/userguide/html_single/>)
[^hb-bp]: Hibernate ORM User Guide, *Performance Tuning and Best Practices* — IDENTITY 와 배치, TABLE 생성기, fetching, DTO 프로젝션. <https://docs.hibernate.org/orm/5.2/userguide/html_single/appendices/BestPractices.html>
