---
layout: post
title: "스프링 의 서비스 추상화(PSA) — 기술 을 바꿔도 *코드* 는 그대로"
date: 2026-07-07 11:20:00 +0900
categories: [backend, spring, architecture]
tags: [spring, psa, transaction, cache, exception-translation, abstraction, jpa, backend]
---

스프링 을 "DI 컨테이너" 로만 아는 사람 이 많다. 하지만 스프링 을 스프링 답게 만드는 세 다리 는 **IoC/DI · AOP · PSA** 다. 이 중 가장 덜 조명 되지만, 실무 에서 매일 덕 보는 게 세 번째 — **PSA(Portable Service Abstraction, 이식 가능한 서비스 추상화)** 다.

한 줄 로 요약 하면 : **"기술(JDBC·JPA·Redis·Kafka…) 을 바꿔도, 비즈니스 코드 는 안 바뀌게 하는 추상화."** `@Transactional` 이 JDBC 든 JPA 든 똑같이 동작 하는 그 마법 이 바로 PSA 다. 이 글 은 PSA 가 *무엇 을*, *어떻게*, 그리고 *어떤 대가 로* 해주는지 를 정리한다.

---

## 1. PSA 란 — *일관된 프로그래밍 모델* 을 씌운다

엔터프라이즈 기능(트랜잭션·캐시·메시징·메일) 은 벤더 마다 API 가 다르다. JDBC 트랜잭션 과 JTA 트랜잭션 은 코드 가 완전히 다르고, Redis 와 Caffeine 도 마찬가지 다.

PSA 는 그 위 에 **스프링 이 정의 한 일관된 인터페이스** 를 씌운다. 개발자 는 그 인터페이스 로만 코딩 하고, *실제 구현* 은 설정(빈 교체) 으로 갈아 끼운다.

> PSA = **일관된 API(변하지 않음)** + **교체 가능한 구현(설정 으로 주입)**. 구현 을 DI 로 주입 하고, 대개 AOP 로 부가기능 을 얹는다 — 그래서 PSA 는 DI·AOP 위 에 선다.

핵심 효과 는 셋 이다 — **① 기술 결합 제거**, **② 테스트 용이(구현 을 목 으로)**, **③ 교체 비용 하락**. 특히 ③ 은 [기술 도입비용]({% post_url 2026-07-07-tech-adoption-cost-5-questions-async-infra %}) 관점 에서 크다 — 추상화 가 *잠금(lock-in)* 을 낮춘다.

---

## 2. 트랜잭션 추상화 — `@Transactional` 하나 로 JDBC·JPA·JTA

가장 널리 쓰는 PSA. 비즈니스 코드 는 이게 전부 다:

```java
@Transactional
public void transfer(Long from, Long to, long amount) {
    accountRepository.withdraw(from, amount);
    accountRepository.deposit(to, amount);
}   // 정상 종료 → commit, 언체크 예외 → rollback
```

이 코드 는 밑 이 **JDBC 든, JPA 든, 여러 리소스 를 묶는 JTA 든** 한 글자 도 안 바뀐다. 비밀 은 `PlatformTransactionManager` 라는 추상화 다:

```java
public interface PlatformTransactionManager {
    TransactionStatus getTransaction(TransactionDefinition def);
    void commit(TransactionStatus status);
    void rollback(TransactionStatus status);
}
```

구현체 만 갈아 끼우면 된다 — `DataSourceTransactionManager`(JDBC), `JpaTransactionManager`(JPA), `JtaTransactionManager`(분산). `@Transactional` 은 AOP 프록시 로 이 매니저 를 호출 할 뿐 이다. **기술 을 바꾸는 건 빈 하나 교체, 코드 는 불변.**

---

## 3. 데이터 접근 예외 추상화 — `SQLException` 을 *벤더 중립* 으로

이건 티 안 나게 매일 구해주는 PSA 다. JDBC 의 `SQLException` 은 **체크 예외** 인 데다, 에러 코드 가 *DB 벤더 마다 다르다*. 그대로 쓰면 서비스 코드 가 MySQL 에러코드 `1062` 같은 것 에 묶인다.

스프링 은 이걸 **`DataAccessException` 계층(언체크 · 벤더 중립)** 으로 번역 한다:

```java
try {
    userRepository.save(user);
} catch (DuplicateKeyException e) {      // ← DB 무관, 스프링 공통 타입
    throw new AlreadyRegisteredException(user.email());
}
```

`JdbcTemplate` 은 자동 으로 번역 하고, JPA/Hibernate 를 쓸 땐 `@Repository` + `PersistenceExceptionTranslationPostProcessor` 가 처리 한다. 덕분 에 **DB 를 MySQL → PostgreSQL 로 바꿔도 예외 처리 코드 가 안 깨진다.** 벤더 잠금 을 예외 레벨 에서 끊는 것.

---

## 4. 캐시 추상화 — `@Cacheable` + `CacheManager`

캐시 구현(Redis · Caffeine · EhCache) 을 비즈니스 코드 에서 지운다:

```java
@Cacheable(value = "products", key = "#id")
public Product findProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

이 메서드 는 *캐시 가 Redis 인지 Caffeine 인지* 를 모른다. 알 필요 도 없다. 교체 는 설정 뿐 :

```java
// 로컬 → 분산 전환도 이 빈 하나
@Bean CacheManager cacheManager(RedisConnectionFactory cf) {
    return RedisCacheManager.builder(cf).build();
}
```

개발 은 Caffeine(인메모리) 으로, 운영 은 Redis(분산) 로 — **애노테이션 은 그대로, `CacheManager` 만 교체.** `@CacheEvict`·`@CachePut` 까지 같은 방식.

---

## 5. 나머지 — 템플릿 으로 통일 된 세계

PSA 는 *템플릿 패턴* 으로 반복 된다. 이름 만 봐도 형제 인 게 보인다:

| 영역 | 추상화 | 구현 교체 |
|---|---|---|
| 메시징 | `JmsTemplate` · `RabbitTemplate` · `KafkaTemplate` | 브로커 |
| 메일 | `JavaMailSender` | SMTP 구현 |
| 리소스 | `Resource` | classpath · file · URL · S3 |
| 트랜잭션(반응형) | `ReactiveTransactionManager` | R2DBC 등 |

전부 같은 철학 이다 — *반복 되는 자원 관리(연결·해제·예외변환) 는 템플릿 이 처리* 하고, 개발자 는 *비즈니스 콜백* 만 넘긴다.

---

## 6. 공짜 는 아니다 — 추상화 의 *비용 과 한계*

PSA 를 만능 으로 믿으면 다친다. 대가 도 분명 하다:

- **새는 추상화(leaky abstraction).** JPA 의 `flush` 타이밍, 트랜잭션 `propagation`·`isolation`, 프록시 self-invocation(같은 클래스 내부 호출 시 `@Transactional` 무효) — 밑 기술 을 모르면 *추상화 가 새는 순간* 손 쓸 수 없다.
- **최소 공통분모 문제.** 추상화 는 *공통* 만 노출 한다. 특정 DB·브로커 의 강력 한 고유 기능 은 추상화 밖 이라, 결국 벤더 API 로 내려가야 할 때 가 있다.
- **추상화 자체 의 학습비용.** "교체 가 쉽다" 는 *실제 로 교체 할 때* 만 값어치 다. 평생 MySQL 만 쓸 서비스 에 과한 추상 레이어 를 또 얹는 건 [도입비용]({% post_url 2026-07-07-tech-adoption-cost-5-questions-async-infra %}) 만 늘린다.

즉 PSA 는 **잠금(lock-in) 을 낮추는 대신, 밑 기술 을 *더 잘 알아야* 안전하게 쓴다.** 추상화 를 쓰되, 그 아래 를 모르면 안 된다.

---

## 마무리 — 스프링 이 파는 건 "편의" 가 아니라 "이식성"

정리 하면 :

- PSA 는 IoC/DI · AOP 와 함께 스프링 의 세 다리 중 하나 다.
- **일관된 API + 교체 가능한 구현** 으로, 기술 을 바꿔도 비즈니스 코드 를 지킨다.
- 트랜잭션(`PlatformTransactionManager`) · 예외(`DataAccessException`) · 캐시(`CacheManager`) · 메시징(`*Template`) 이 대표 사례.
- 단, *새는 추상화* 와 *최소 공통분모* 라는 대가 가 있으니, 밑 기술 을 아는 채 로 써야 한다.

`@Transactional` 한 줄 뒤 에 숨은 이 설계 를 이해 하면, 스프링 코드 가 *왜 이렇게 갈아 끼우기 쉬운지* 가 보인다. 스프링 이 파는 건 결국 **편의 가 아니라 이식성(portability)** 이다 — 기술 은 변해도, 당신 의 도메인 코드 는 살아남게 하는 것.
