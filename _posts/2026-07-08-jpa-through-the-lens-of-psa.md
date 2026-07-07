---
layout: post
title: "PSA 렌즈 로 본 JPA — *표준 하나 아래, 겹겹 이 쌓인 이식성*"
date: 2026-07-08 05:05:00 +0900
categories: [backend, spring, jpa]
tags: [jpa, psa, spring-data-jpa, hibernate, transaction, exception-translation, abstraction, orm]
---

Spring 의 삼대 요소 는 **IoC/DI · AOP · PSA** 다. 이 중 PSA(Portable Service Abstraction, 이식 가능한 서비스 추상화) 는 *가장 조용히 일 하는* 요소다. 그리고 우리 가 매일 쓰는 **JPA** 야말로, PSA 가 *어떻게 겹겹이 작동 하는지* 를 보여주는 최고 의 교재다.

이 글 은 JPA 를 *PSA 렌즈* 로 층층이 뜯어본다. (PSA 일반 은 → [스프링 이 파는 건 이식성]({% post_url 2026-07-07-spring-service-abstraction-psa %}), 이 글 은 JPA 특화.)

---

## 0. PSA 란 — *구현 을 감춘, 일관된 인터페이스*

PSA 는 한 마디 로 **"기술 을 바꿔도 내 코드 는 안 바뀌게"** 하는 추상화다. 특정 벤더·기술 에 *직접* 의존 하는 대신, 스프링 이 씌운 *일관된 껍데기* 에 의존 한다. 그럼 아래 구현 을 갈아끼워도 위 코드 는 그대로.

JPA 를 보면, 이 PSA 가 **한 겹 이 아니라 네 겹** 으로 쌓여 있다.

---

## 1. Layer 0 — *JPA 자체 가 이미 PSA 다*

가장 먼저, **JPA 그 자체 가 PSA** 다. JPA(Jakarta Persistence) 는 *구현 이 아니라 표준(스펙)* 이다.

- **표준(인터페이스)**: `EntityManager`, `@Entity`, `@Id`, JPQL — Jakarta Persistence 명세.
- **구현(provider)**: **Hibernate**, EclipseLink, DataNucleus…

```java
@PersistenceContext
EntityManager em;              // 표준 인터페이스에만 의존
em.persist(order);             // 실제 구현은 Hibernate가
```

내 코드 는 `EntityManager`·JPA 어노테이션 에만 의존 한다. 그래서 **Hibernate 를 EclipseLink 로 갈아도 도메인 코드 는 안 바뀐다.** 이게 PSA 의 원형 — *스펙 에 의존, 구현 은 교체 가능*. (나 는 provider 로 Hibernate 를 쓴다.)

> 즉 "JPA 를 쓴다" 는 건 이미 *ORM 벤더 에 대한 이식성* 을 확보 한 것. 순수 JDBC/Hibernate API 를 직접 쓰면 이 이식성 이 사라진다.

---

## 2. Layer 1 — `@Transactional` : *트랜잭션 기술 의 PSA*

JPA 위 에 스프링 이 **트랜잭션 PSA** 를 한 겹 더 씌운다. `@Transactional` 하나 가, 밑 의 트랜잭션 매니저 를 *추상* 한다:

| 데이터 기술 | 실제 TransactionManager |
|---|---|
| JPA | `JpaTransactionManager` |
| JDBC/MyBatis | `DataSourceTransactionManager` |
| JTA(분산) | `JtaTransactionManager` |

```java
@Transactional
public void completePayment(...) {   // JPA든 JDBC든 코드는 동일
    paymentRepository.save(payment);
    outboxRepository.save(event);
}
```

정산 에서 결제+Outbox 를 *한 트랜잭션* 으로 묶는 [Outbox 패턴]({% post_url 2026-07-07-transactional-outbox-pattern-deep-dive %}) 도, 이 `@Transactional` PSA 위 에 선다. JPA 를 JDBC 로 바꿔도 트랜잭션 경계 선언 은 그대로 — *커밋/롤백 을 누가 처리 하는지* 를 스프링 이 감춘다.

---

## 3. Layer 2 — *예외 번역* : 벤더 예외 를 중립 으로

이게 JPA + 스프링 PSA 의 *가장 안 보이지만 중요한* 층이다. JPA/Hibernate 는 벤더·기술 별 로 제각각 예외 를 던진다 — `PersistenceException`, `ConstraintViolationException`, 그 아래 `SQLException`(벤더별 에러 코드).

스프링 은 이걸 **`DataAccessException` 계층(런타임·기술 중립)** 으로 *번역* 한다:

```
Hibernate ConstraintViolationException
  → org.springframework.dao.DataIntegrityViolationException
JPA OptimisticLockException
  → org.springframework.dao.OptimisticLockingFailureException
```

- `@Repository` 를 붙이면 `PersistenceExceptionTranslationPostProcessor` 가 이 번역 을 자동 으로.
- 덕분 에 **서비스 계층 이 Hibernate/JDBC 예외 를 import 하지 않는다.** DB 벤더 를 MySQL→PostgreSQL 로 바꿔도, 유니크 위반 은 똑같이 `DataIntegrityViolationException`.

이건 [헥사고날]({% post_url 2026-07-07-object-oriented-design-from-a-diagram %}) 과도 맞물린다 — 도메인 이 *인프라 예외* 에 오염 되지 않게 하는 경계. 정산 의 멱등성(유니크 제약 위반 을 잡아 처리) 도, 벤더 중립 예외 위 에서 안전 하게 돈다.

---

## 4. Layer 3 — *Spring Data JPA* : 구현 없는 Repository

맨 위 층. Spring Data JPA 는 **인터페이스 만 선언 하면 구현 을 생성** 하는 PSA 다.

```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    Optional<Order> findByPaymentId(String paymentId);  // 구현 0줄
}
```

- `findByPaymentId` 는 *메서드 이름 을 파싱* 해 쿼리 를 자동 생성. 구현체 를 스프링 이 런타임 에 만든다.
- 그리고 이 `Repository` 추상 은 저장소 기술 을 넘어 이식 된다 — `JpaRepository` ↔ `MongoRepository` ↔ `ElasticsearchRepository` 가 *같은 프로그래밍 모델*.

즉 "Repository 인터페이스 에 의존" 하는 순간, 나 는 *JPA 구현 세부* 로부터 한 겹 더 멀어진다. 정산 의 Read-only Projection 도 이 위 에서 `@Immutable` 엔티티 를 Repository 로 조회 한다.

---

## 5. 네 겹 을 한 장 으로

```
[내 서비스 코드]
   ↑ 의존
Layer 3  Spring Data JPA Repository   (구현 없는 인터페이스)
Layer 2  예외 번역 (@Repository)       (DataAccessException 중립)
Layer 1  @Transactional               (트랜잭션 매니저 추상)
Layer 0  JPA 표준 (EntityManager)     (Hibernate/EclipseLink 교체)
   ↓ 실제
[Hibernate → JDBC → MySQL/PostgreSQL]
```

각 층 이 *아래 를 감춘다*. 그래서 provider 교체(Layer 0), 트랜잭션 기술 교체(Layer 1), DB 벤더 교체(Layer 2), 저장소 종류 교체(Layer 3) 가 *위 코드 를 건드리지 않고* 가능해진다. **이게 스프링 이 파는 "이식성" 의 실체다.**

---

## 6. 공짜 는 아니다 — 새는 추상화

PSA 가 완벽한 격리 는 아니다. **추상화 는 샌다(leaky abstraction).**

- **N+1 쿼리** — Repository 가 SQL 을 감춰서, *무심코* 지연 로딩 을 돌면 쿼리 가 폭증. 추상 아래 의 *실제 SQL* 을 봐야 한다.
- **벤더 특화 기능** — Hibernate 전용 힌트, PostgreSQL JSONB 같은 건 PSA 를 뚫고 벤더 에 의존 하게 된다.
- **성능 튜닝** — 결국 `EXPLAIN`·인덱스·fetch 전략 은 *추상 아래* 의 일. PSA 는 이식성 을 주지만 *성능 을 대신 짜주진 않는다*.

그래서 JPA 를 잘 쓴다는 건, *PSA 를 신뢰 하되 그 아래 SQL 을 볼 줄 아는 것*. 추상화 를 쓰는 것 과 추상화 에 갇히는 것 은 다르다. (→ [CS 기초 는 왜 중요한가]({% post_url 2026-07-06-why-cs-fundamentals-matter-for-backend %}))

---

## 마무리

JPA 를 PSA 렌즈 로 보면, 그건 단순한 ORM 이 아니라 **이식성 의 네 겹 탑** 이다:

- **Layer 0**: JPA 표준 → ORM 벤더 교체 가능
- **Layer 1**: `@Transactional` → 트랜잭션 기술 교체 가능
- **Layer 2**: 예외 번역 → DB 벤더 교체 가능
- **Layer 3**: Spring Data → 저장소 종류 교체 가능

스프링 이 JPA 로 파는 건 "편하게 CRUD" 가 아니다. **"아래 기술 을 바꿔도 위 코드 는 안 바뀐다" 는 이식성** 이다. 그리고 그 이식성 은, 우리 가 벤더 API 대신 *스프링 이 씌운 일관된 인터페이스* 에 의존 하기로 한 대가 로 얻는 것이다.

*좋은 추상화 는 선택지 를 없애지 않는다 — 나중 을 위해 열어둔다.*
