---
layout: post
title: "Hibernate 와 HikariCP — 커넥션을 언제 빌리고 언제 돌려주는지가 성능의 절반이다"
date: 2026-09-15 22:15:00 +0900
categories: [Engineering, Backend]
tags: [Hibernate, HikariCP, JPA, Connection Pool, Spring Boot, autoCommit, OSIV]
---

스프링 부트에서 JPA 를 쓰면 Hibernate 와 HikariCP 는 자동으로 한 몸이 된다 — [부트는 HikariCP 가 클래스패스에 있으면 무조건 그걸 선택한다](https://docs.spring.io/spring-boot/reference/data/sql.html). 그래서 대부분 둘의 경계를 의식할 일이 없다. 그런데 성능 문제(풀 고갈, 불필요한 왕복, 커넥션을 오래 무는 트랜잭션)는 거의 전부 **이 경계에서** 생긴다. 핵심 질문은 하나다: **Hibernate 는 Hikari 풀에서 커넥션을 언제 빌리고, 언제 돌려주는가.**

이 블로그에 HikariCP 자체를 뜯은 글([풀 내부 구조](/2026/06/10/spring-boot-db-connection-pool-hikaricp-deep-dive/), [대기 시간 분석](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time/))은 이미 있으니, 오늘은 그 반대편 — Hibernate 쪽에서 풀을 어떻게 대하는지만 본다.

## 1. 빌리는 시점 — 트랜잭션 시작이 아니라 "첫 SQL 직전"

[Hibernate 공식 사용자 가이드](https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html)의 connection handling 모드 중, 풀을 쓸 때의 기본값은 `DELAYED_ACQUISITION_AND_RELEASE_AFTER_TRANSACTION` 이다. 이름 그대로 두 가지를 약속한다.

- **DELAYED_ACQUISITION**: `@Transactional` 메서드에 들어와도 커넥션을 바로 빌리지 않는다. 실제 JDBC 작업이 필요한 순간(첫 쿼리/플러시)까지 미룬다.
- **RELEASE_AFTER_TRANSACTION**: 한번 빌리면 트랜잭션이 끝날 때 돌려준다.

이게 왜 중요한가. `@Transactional` 메서드 앞부분에서 외부 API 호출·파일 처리 같은 DB 무관 작업을 한다면, 그 시간 동안 커넥션은 (지연 획득 덕에) 아직 풀에 있다. 하지만 **첫 쿼리를 날린 뒤에 느린 작업을 하면** 커넥션은 트랜잭션 끝까지 잡혀 있다. 즉:

```java
@Transactional
public void bad() {
    repo.findById(id);        // 여기서 커넥션 획득
    slowExternalApiCall();    // 커넥션을 문 채 3초 대기 ← 풀 고갈의 주범
    repo.save(entity);
}
```

풀 크기를 늘리기 전에 **트랜잭션 안에서 커넥션을 문 채 보내는 시간부터 줄이는 것**이 순서다. HikariCP 위키의 [풀 사이징 문서](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)도 같은 방향을 가리킨다 — 풀은 생각보다 훨씬 작아도 되고, 문제는 대개 커넥션을 오래 물고 있는 쪽이다.

## 2. autoCommit — 둘 다 처리하려다 왕복이 두 배가 된다

경계에서 가장 자주 어긋나는 설정이다.

- HikariCP 의 `autoCommit` 기본값은 `true` 다 ([공식 README](https://github.com/brettwooldridge/HikariCP)).
- Hibernate 는 트랜잭션을 시작할 때 auto-commit 을 꺼야 하므로, 커넥션을 빌릴 때마다 `setAutoCommit(false)` → 끝나면 `setAutoCommit(true)` 복원을 반복한다. 드라이버에 따라 이건 DB 왕복이다.

그래서 Hibernate 는 [`hibernate.connection.provider_disables_autocommit`](https://docs.jboss.org/hibernate/orm/6.6/javadocs/org/hibernate/cfg/AvailableSettings.html) 이라는 설정을 제공한다(공식 사용자 가이드에도 명시). 의미는 "풀이 이미 auto-commit 을 꺼서 커넥션을 준다고 **약속**하니, Hibernate 너는 확인하지 마라" 다. 짝은 이렇게 맞춘다:

```properties
# HikariCP: auto-commit 끈 커넥션을 내놓는다
spring.datasource.hikari.auto-commit=false
# Hibernate: 그 약속을 믿고 확인 왕복을 생략한다
spring.jpa.properties.hibernate.connection.provider_disables_autocommit=true
```

⚠️ **반드시 세트로.** Hikari 쪽을 안 바꾸고 Hibernate 쪽만 켜면, auto-commit 이 켜진 커넥션을 Hibernate 가 "꺼져 있겠지" 하고 그대로 쓴다 — 트랜잭션 경계가 조용히 무너진다. 거꾸로 Hikari 만 끄고 Hibernate 설정을 안 켜면 동작은 정확하지만 최적화만 못 받는다. 후자는 손해, 전자는 사고다.

## 3. OSIV — "커넥션 반납"을 뷰 렌더링까지 미루는 함정

스프링 부트의 `spring.jpa.open-in-view` 는 기본 `true` 고, 부트는 기동 로그에 이 사실을 경고로 알려줄 정도로 [공식 문서가 명시적으로 언급하는](https://docs.spring.io/spring-boot/reference/data/sql.html) 설정이다. OSIV 가 켜져 있으면 영속성 컨텍스트가 HTTP 요청 끝까지 살아 있고, 컨트롤러·뷰에서 지연 로딩이 터지면 **트랜잭션 밖에서 커넥션을 다시 빌린다.**

1번의 지연 획득 덕에 "요청 내내 커넥션을 문다" 는 건 아니지만, 응답 직렬화 중에 N+1 지연 로딩이 발생하면 그 각각이 풀에서 커넥션을 꺼내 쓴다. 트래픽이 몰리면 서비스 계층은 멀쩡한데 직렬화 단계에서 풀이 마르는, 원인 찾기 고약한 고갈이 된다. API 서버라면 `spring.jpa.open-in-view=false` 로 끄고, 필요한 데이터는 서비스 계층 안에서 fetch join/DTO 로 완결하는 쪽이 경계가 깨끗하다.

## 4. 풀 고갈 데드락 — 한 스레드가 커넥션 두 개를 원할 때

마지막 함정은 Hibernate 설정이 아니라 코드 패턴이다. 한 요청 스레드가 커넥션을 이미 문 상태에서 **두 번째 커넥션이 필요한 작업**(REQUIRES_NEW 트랜잭션, 별도 데이터소스, 트랜잭션 안에서 ID 채번용 별도 커넥션)을 시작하면, 부하 상황에서 전원이 첫 커넥션을 문 채 두 번째를 기다리는 교착이 된다. HikariCP 의 [풀 사이징 문서](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)는 이 경우의 최소 풀 크기 공식(`pool size = Tn × (Cm − 1) + 1`)까지 제시한다 — 스레드 수 × (스레드당 동시 필요 커넥션 − 1) + 1. 이 공식이 필요해졌다는 것 자체가 설계를 다시 볼 신호이기도 하다.

## 체크리스트

| 점검 | 기대값 |
| --- | --- |
| 트랜잭션 안에서 외부 호출이 첫 쿼리 **뒤에** 오는가 | 순서를 바꾸거나 트랜잭션에서 분리 |
| `hikari.auto-commit=false` 와 `provider_disables_autocommit=true` | 반드시 세트, 한쪽만은 금지 |
| `spring.jpa.open-in-view` | API 서버면 `false` |
| REQUIRES_NEW·다중 데이터소스가 한 스레드에 겹치는가 | 겹치면 사이징 공식 적용 또는 구조 분리 |

Hibernate 와 HikariCP 는 각자 훌륭하다. 문제는 언제나 **둘 사이의 약속** — 누가 auto-commit 을 끄는지, 커넥션을 언제 돌려주는지 — 를 한쪽만 알고 있을 때 생긴다.

## References

- Hibernate ORM 6.6 — [User Guide (connection handling, `provider_disables_autocommit`)](https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html) · [AvailableSettings javadoc](https://docs.jboss.org/hibernate/orm/6.6/javadocs/org/hibernate/cfg/AvailableSettings.html)
- HikariCP — [README (구성 기본값)](https://github.com/brettwooldridge/HikariCP) · [About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)
- Spring Boot — [SQL Databases reference (커넥션 풀 선택, open-in-view)](https://docs.spring.io/spring-boot/reference/data/sql.html)
