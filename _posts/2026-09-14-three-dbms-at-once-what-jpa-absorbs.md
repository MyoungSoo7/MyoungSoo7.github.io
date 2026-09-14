---
layout: post
title: "MySQL · MSSQL · Oracle 을 동시에 이고 있다 — JPA 는 그중 무엇을 없애주고, 무엇이 끝까지 남는가"
date: 2026-09-14 22:53:52 +0900
categories: [backend]
tags: [jpa, hibernate, mysql, mssql, oracle, rdbms, transaction, isolation, spring]
---

JPA 이식성 논쟁은 대개 같은 결론에서 끝난다. **"DB 를 바꿀 일이 없으니 이식성은 이론적 장점"** 이라는 것.
나도 [예전 글]({% post_url 2026-05-29-jpa-vs-mybatis-ai-era-coding %})에서 그렇게 썼다. 그 결론은 *한 조직이 DBMS 하나를 쓴다*
는 전제 위에서만 맞다.

그런데 MySQL·MSSQL·Oracle 을 **동시에** 이고 있는 조직이 있다. 인수한 회사가 MSSQL 을 쓰고 있었거나, 기간계는 Oracle 인데
신규 서비스는 MySQL 로 깔았거나, 패키지 솔루션이 특정 DB 를 강제하거나. 여기서는 전제가 바뀐다.

> 이전(migration)은 안 한다. 그러나 **병존(coexistence)** 은 매일 한다.

이전은 언젠가 한 번이라 이식성의 값어치를 할인해도 된다. 병존은 매 커밋마다라 할인이 안 된다.
그래서 같은 질문이 전혀 다른 답을 갖는다. 이 글은 그 답을 **"JPA 가 흡수하는 층"** 과 **"끝까지 안 흡수되는 층"**
두 개로 갈라서 쓴 것이다.

---

## 1. 먼저 인정할 것 — 3배가 되는 것들의 대부분은 JPA 와 무관하다

JPA 도입 검토를 하면 논의가 애플리케이션 코드로 쏠린다. 그런데 3중 운영의 비용은 코드 밖에 훨씬 많다.

| 3배가 되는 것 | JPA 가 줄여주나 |
| --- | --- |
| 백업·복구 절차와 RPO/RTO 검증 | ❌ 전혀 |
| 스키마 변경 배포 파이프라인 | △ 일부 (DDL 생성·검증) |
| 모니터링 지표 이름과 임계치 | ❌ 전혀 |
| 드라이버·커넥션 풀 튜닝 | ❌ (풀은 HikariCP 로 통일돼도 DB별 타임아웃 의미가 다르다) |
| 계정·권한·감사 정책 | ❌ 전혀 |
| 장애 런북과 온콜 지식 | ❌ 전혀 |
| 버전 EOL 캘린더와 라이선스 | ❌ 전혀 |
| 옵티마이저 통계·실행계획 읽는 법 | ❌ 전혀 |

JPA 는 **애플리케이션 코드 층의 도구**다. 위 표에서 JPA 가 손대는 칸은 사실상 한 줄뿐이다.
"JPA 를 넣으면 3중 운영이 편해진다" 는 기대로 검토를 시작하면 검토는 실패한다.
정확한 질문은 이것이다 — **"코드 층에서 3벌이 되는 것 중 무엇이 1벌로 줄어드나?"**

---

## 2. JPA 가 실제로 흡수하는 층 — *문법*

Hibernate 의 Dialect 가 먹어주는 건 대체로 **SQL 문법의 차이**다. 이건 진짜로 먹어준다.

### 2-1. 페이지네이션

셋이 전부 다른 문법을 쓴다.

- MySQL — `LIMIT ... OFFSET ...`
- SQL Server — `ORDER BY ... OFFSET n ROWS FETCH NEXT m ROWS ONLY`. `<offset_fetch>` 는 `ORDER BY` 절 문법의
  일부로 정의돼 있다 (Microsoft, *SELECT - ORDER BY clause (Transact-SQL)*).
- Oracle — `SELECT` 문법 다이어그램에 `row_limiting_clause` 가 별도 절로 들어 있다 (Oracle, *SQL Language Reference — SELECT*).

애플리케이션에서는 `Pageable` 하나다. 이건 순수 이득이고, 3중 운영에서 특히 크다. 같은 목록 API 를 DB 별로 세 번 짜던
일이 없어진다.

### 2-2. 식별자 생성 전략

- Oracle — 시퀀스 있음
- SQL Server — `CREATE SEQUENCE` 있음. 마이크로소프트 문서는 *"Sequences, unlike identity columns, aren't associated with
  specific tables"* 라고 명시한다.
- MySQL — 시퀀스 객체가 없다. `AUTO_INCREMENT` 로 간다.

`@GeneratedValue` 한 줄로 흡수된다 — **단, 성능까지 흡수되지는 않는다.** 이건 3-3 에서 다시 나온다.

### 2-3. 그 외

DDL 생성, 조인 문법, 일부 함수 매핑, 락 구문(`LockModeType` → 벤더별 구문), 그리고 벤더 예외의 중립 예외 번역.
예외 번역이 왜 이식성의 한 층인지는 [PSA 렌즈로 본 JPA]({% post_url 2026-07-08-jpa-through-the-lens-of-psa %}) 에 따로 썼다.

---

## 3. 끝까지 안 흡수되는 층 — *의미론*

여기가 이 글의 본론이다. 문법은 번역되지만 **같은 문장이 다른 뜻이 되는 것** 은 번역되지 않는다.
JPQL 을 한 글자도 안 고쳤는데 결과가 갈리는 지점들이다.

### 3-1. 빈 문자열이 NULL 인 DB 가 하나 섞여 있다

Oracle SQL Language Reference 의 *Nulls* 는 이렇게 쓰여 있다.

> "The database treats a character value with a length of zero as null."

그리고 바로 아래 Oracle 자신의 경고가 붙어 있다.

> "The database currently treats a character value with a length of zero as null. However, this may not continue to be
> true in future releases, and Oracle recommends that you do not treat empty strings the same as nulls."

즉 **지금은 그렇지만 앞으로도 그럴 거라고 믿지 말라** 는 것이다. 이것의 실전 효과:

```java
entity.setName("");
repo.save(entity);
// JPQL 은 동일
// select e from Entity e where e.name is null
```

MySQL·SQL Server 에서는 0건, Oracle 에서는 1건이 나온다. Dialect 가 고쳐줄 수 있는 종류의 차이가 아니다.
`""` 와 `null` 을 서로 다른 값으로 쓰고 있는 도메인이라면, 3중 운영에서는 **애플리케이션이 저장 전에 정규화** 하는 것 말고
방법이 없다. (그리고 그 정규화는 JPA 가 아니라 도메인 코드의 책임이다.)

### 3-2. 기본 격리 수준이 셋 다 다르고, 고를 수 있는 범위도 다르다

1차 문서 그대로:

| DBMS | 기본 격리 수준 | 비고 |
| --- | --- | --- |
| MySQL (InnoDB) | `REPEATABLE READ` | "The default isolation level for `InnoDB` is `REPEATABLE READ`." |
| SQL Server | `READ COMMITTED` | "This option is the SQL Server default." 그리고 `READ_COMMITTED_SNAPSHOT` 의 **기본값은 OFF** — 즉 기본 동작은 스냅샷이 아니라 **공유 락으로 블로킹** 한다 |
| Oracle | `READ COMMITTED` | 다중버전(MVCC) 기반 |

여기서 진짜 함정은 기본값이 다르다는 게 아니라 **선택지 자체가 다르다** 는 것이다.
Oracle 의 `SET TRANSACTION` 문법이 받는 격리 수준은 `SERIALIZABLE` 과 `READ COMMITTED` **둘뿐**이다
(Oracle, *SQL Language Reference — SET TRANSACTION*). MySQL InnoDB 는 SQL:1992 의 네 단계를 전부 제공하고
(MySQL 8.4 매뉴얼), SQL Server 는 거기에 `SNAPSHOT` 을 더해 다섯 개를 받는다 (Microsoft, *SET TRANSACTION ISOLATION LEVEL*).

그래서 이런 코드가 문제가 된다.

```java
@Transactional(isolation = Isolation.REPEATABLE_READ)
public void settle(Long id) { ... }
```

MySQL 에서는 기본값과 같아서 아무 일도 안 일어나고, SQL Server 에서는 잠금 범위가 넓어지고,
Oracle 에서는 **애초에 지정할 수 없는 수준**이다. 같은 애노테이션 한 줄이 세 군데서 세 가지로 해석된다.

> 3중 운영에서 `isolation` 속성은 "조직 전체가 합의한 기본값 하나" 로 고정하고, 그걸 벗어나야 하는 트랜잭션은
> **DB 를 명시한 주석과 함께** 예외로 관리하는 편이 낫다. 코드만 보고는 어느 DB 에서 뭐가 되는지 알 수 없기 때문이다.

### 3-3. 같은 코드가 MySQL 에서만 배치 insert 를 못 한다

Hibernate 의 *Batching* 문서는 이렇게 못박는다.

> "Hibernate disables insert batching at the JDBC level transparently if you use an identity identifier generator."

그리고 Best Practices 부록은 이렇게 이어진다.

> "Only if the relational database does not support sequences (e.g. MySQL 5.7), you should use the `IDENTITY`
> generators. However, you should keep in mind that the `IDENTITY` generators disables JDBC batching for `INSERT`
> statements."

두 문장을 겹쳐 놓으면 3중 운영에서의 결론이 나온다.

- Oracle·SQL Server — 시퀀스가 있으니 `SEQUENCE` 전략 → 배치 가능
- MySQL — 시퀀스가 없으니 `IDENTITY` 로 몰림 → **배치 비활성화**

즉 **엔티티 코드는 한 벌인데 대량 적재 성능만 DB 하나에서 무너진다.** 그리고 이건 로그에 에러로 안 찍힌다.
조용히 느릴 뿐이다.

⚠️ 위 인용은 Hibernate 5.2 User Guide 기준이다. Hibernate 6 이후로는 IDENTITY 값 회수를
`Statement.getGeneratedKeys()` 위임 구조(`IdentityColumnSupport`)로 바꾸는 작업이 들어가 있어서 **dialect 마다 사정이
다를 수 있다.** 나는 "6.x 에서는 배치가 된다/안 된다" 를 자기 버전 문서 문장으로 확인하지 못했으므로 단정하지 않는다.
도입 검토라면 이건 문서로 믿을 게 아니라 **자기 버전·자기 dialect 로 실측할 항목**이다 (측정법은 6절).

### 3-4. 타입 매핑 — boolean 하나가 셋 다 다르다

- MySQL — `BOOLEAN` 은 `TINYINT(1)` 의 별칭
- SQL Server — `BIT`
- Oracle — 오랫동안 SQL 레벨에 boolean 이 없어 `NUMBER(1)`·`CHAR(1)` 로 흉내 냈다. Oracle Database **23ai** 에서
  ISO SQL 표준 `BOOLEAN` 데이터 타입이 들어왔다 (Oracle, *23c New Features Guide* — "SQL BOOLEAN Data Type").

`@Column boolean` 한 줄은 Hibernate 가 매핑해 준다. 그러나 **그 테이블을 JPA 가 아닌 경로로 읽는 순간** — 배치 SQL,
리포팅 도구, 다른 언어로 짠 연계 프로그램 — 셋의 저장 표현이 다르다는 사실이 그대로 튀어나온다.
3중 운영의 함정은 대부분 이 지점, **"JPA 를 안 거치는 두 번째 경로"** 에서 터진다.

---

## 4. 결정적인 한 줄 — 트랜잭션은 3개를 못 묶는다

Spring Framework 레퍼런스의 서술이 이 문제의 정확한 요약이다.

> "Local transactions are resource-specific, such as a transaction associated with a JDBC connection. Local transactions
> may be easier to use but have a significant disadvantage: **They cannot work across multiple transactional resources.**"

`@Transactional` 하나로 MySQL 과 Oracle 을 원자적으로 묶는 건 로컬 트랜잭션으로는 **불가능**하다. 방법은 두 갈래뿐이다.

1. **JTA/XA 로 간다.** Spring Boot 는 이 경로를 지원한다 — *"Spring Boot supports distributed JTA transactions across
   multiple XA resources by using a transaction manager retrieved from JNDI."* 대신 그 순간 이건 JPA 도입 검토가 아니라
   **아키텍처 결정**이 된다. XA 드라이버, 2PC 지연, 미결 트랜잭션(in-doubt) 복구 절차가 3개 DB 몫으로 붙는다.
2. **묶지 않는다.** DB 당 트랜잭션으로 쪼개고 경계는 아웃박스·보상 트랜잭션으로 잇는다.
   ([아웃박스 패턴의 경계]({% post_url 2026-07-01-outbox-pattern-boundaries-of-jpa-mybatis-querydsl %}))

내 권고는 2번이다. 3중 운영을 하는 조직은 이미 DB 별로 팀·배포·장애 경계가 갈려 있는 경우가 많다.
그 경계를 XA 로 억지로 지우면, 장애가 났을 때 **세 DB 가 한꺼번에 멈춘다.**

---

## 5. 그래서 JPA 를 도입할 것인가 — 판단 기준 네 가지

전면 도입/전면 거부의 이분법이 아니라, 아래 네 개로 **경계마다 따로** 답하는 게 맞다.

**기준 1 — 3개 DB 가 같은 도메인을 쪼개 갖는가, 각자 다른 도메인인가.**
각자 다른 도메인이면 (예: 회원=MySQL, 기간계=Oracle, 레거시 사내시스템=MSSQL) JPA 이득이 크다.
모듈별로 `DataSource`·`EntityManagerFactory`·`TransactionManager` 를 따로 두면 되고, 4절의 문제가 애초에 안 생긴다.
같은 도메인을 쪼개 갖고 있으면 JPA 가 아니라 **데이터 소유권 설계**부터 다시 해야 한다.

**기준 2 — 레거시 스키마를 그대로 써야 하는가.**
복합키, 트리거, 스토어드 프로시저 중심, 컬럼명이 `COL_001` 인 테이블 — 이런 스키마에서 JPA 의 이득은 급감한다.
이 경계는 SQL 매퍼로 두는 게 낫다. ([JPA 와 MyBatis 는 JDBC 의 무엇을 지웠나]({% post_url 2026-08-20-jpa-vs-mybatis-two-branches-from-jdbc %}))

**기준 3 — 배치·대량 DML 비중.**
3-3 의 이유로, 대량 적재가 핵심이면 JPA 를 그 경로에 넣는 결정 자체를 재고해야 한다.

**기준 4 — 팀이 생성된 SQL 을 읽을 수 있는가.**
3중 운영에서 JPA 는 *SQL 을 안 봐도 되게* 해주는 도구가 아니라 *SQL 세 벌을 안 짜도 되게* 해주는 도구다.
읽기는 여전히 해야 한다. 세 DB 의 실행계획 읽는 법을 아무도 모르는 팀이 JPA 를 넣으면, 느려졌을 때 볼 곳이 하나 더 늘 뿐이다.

---

## 6. 도입한다면 — 첫 2주에 검증할 순서

검토 단계에서 문서로 결론 내지 말고, 아래를 **세 DB 전부에 대해 같은 테스트로** 돌린다.

1. **같은 통합테스트를 세 번 돌린다.** Testcontainers 로 MySQL·SQL Server·Oracle 컨테이너를 각각 띄우고
   동일 테스트 스위트를 프로파일만 바꿔 실행. 3중 운영에서 이건 선택이 아니라 **최소 조건**이다.
2. **`ddl-auto` 는 `validate` 로 고정한다.** 스키마를 애플리케이션이 만들게 두면 세 DB 의 DDL 이 조용히 갈라진다.
   3중 환경에서 의미 있는 값은 `validate` 하나뿐이다. 스키마 자체는 형상관리 도구로 간다
   ([Liquibase vs Flyway]({% post_url 2026-09-14-liquibase-vs-flyway-change-identity %})).
3. **Dialect 를 명시적으로 고정한다.** 자동 감지에 맡기면 드라이버·버전이 바뀔 때 생성 SQL 이 조용히 바뀐다.
4. **의미론 3종을 먼저 회귀 테스트로 박는다** — ① 빈 문자열/NULL, ② 날짜·타임존, ③ boolean.
   3절에서 본 것들이고, 전부 "테스트 없으면 운영에서 처음 발견되는" 종류다.
5. **배치 insert 를 실측한다.** `hibernate.jdbc.batch_size` 를 켜고 1만 건 적재의 SQL 실행 횟수를 센다
   (`hibernate.generate_statistics` 또는 드라이버 로그). 3-3 이 자기 버전에서 참인지는 이걸로만 알 수 있다.
6. **`@Transactional` 로 두 DB 를 건드리는 코드가 있는지 정적으로 뒤진다.** 있으면 그건 버그다 — 4절이 이유다.

---

## 7. 함정 모음

- **"이전 계획이 없으니 이식성은 무의미하다"** — 병존 조직에는 안 맞는 말이다. 이식성의 값이 "한 번"에서 "매 커밋"으로 바뀐다.
- **Oracle 의 빈 문자열** — 지금은 NULL 이지만 Oracle 스스로 "그렇게 취급하지 말라"고 문서에 적어 뒀다. 의존하면 안 된다.
- **`isolation` 속성** — 세 DB 가 받는 값의 집합이 다르다. Oracle 은 두 개뿐이다.
- **SQL Server 의 `READ COMMITTED`** — 기본값이 스냅샷이 아니다. `READ_COMMITTED_SNAPSHOT` 은 SQL Server 에서 기본 OFF 이고,
  Azure SQL Database 에서는 기본 ON 이다. **같은 T-SQL 인데 온프렘과 클라우드의 동작이 다르다.**
- **IDENTITY 와 배치** — 조용히 느려진다. 에러가 안 난다.
- **JPA 를 안 거치는 두 번째 경로** — 리포팅·연계 프로그램이 같은 테이블을 읽는 순간 타입 매핑 차이가 드러난다.
- **XA 로 묶기** — 원자성을 얻는 대신 가용성을 셋이 공유하게 된다.
- **모니터링 지표 이름** — 세 DB 의 "대기(wait)" 가 같은 뜻이 아니다. 통합 대시보드를 만들 때 같은 칸에 놓으면 오독한다.
- **버전 EOL** — 3중 운영에서 가장 먼저 사고 나는 건 기술이 아니라 **캘린더**다. 셋의 지원 종료일이 다르다.

---

## 마무리

한 줄로 줄이면 이렇다.

> **JPA 는 세 DB 의 *문법* 을 한 벌로 줄여준다. *의미론* 과 *운영* 은 여전히 세 벌이다.**

그래서 3중 운영 조직의 JPA 도입 검토는 "JPA 가 좋냐 나쁘냐" 가 아니라 **"우리가 세 벌로 갖고 있는 것 중 어느 칸이
문법이고 어느 칸이 의미론인가"** 를 먼저 표로 그리는 일이어야 한다. 1절의 표에서 ❌ 가 대부분이라는 걸 인정하고 시작하면,
JPA 는 과대평가되지도 과소평가되지도 않은 채로 제자리에 놓인다 — **코드 층의, 문법 층의, 꽤 좋은 도구.**

---

## References

- Oracle, *Oracle Database SQL Language Reference — Nulls*. <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Nulls.html>
- Oracle, *Oracle Database SQL Language Reference — SET TRANSACTION*. <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SET-TRANSACTION.html>
- Oracle, *Oracle Database SQL Language Reference — SELECT* (`row_limiting_clause`). <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SELECT.html>
- Oracle, *Oracle Database 23ai New Features Guide* (SQL BOOLEAN Data Type). <https://docs.oracle.com/cd/G11854_01/nfcoa/oracle-database-23c-new-features-guide.pdf>
- Oracle, *Oracle Database Concepts — Data Concurrency and Consistency*. <https://docs.oracle.com/en/database/oracle/oracle-database/23/cncpt/data-concurrency-and-consistency.html>
- MySQL, *MySQL 8.4 Reference Manual — 17.7.2.1 Transaction Isolation Levels*. <https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html>
- Microsoft, *SET TRANSACTION ISOLATION LEVEL (Transact-SQL)*. <https://learn.microsoft.com/en-us/sql/t-sql/statements/set-transaction-isolation-level-transact-sql>
- Microsoft, *SELECT - ORDER BY clause (Transact-SQL)*. <https://learn.microsoft.com/en-us/sql/t-sql/queries/select-order-by-clause-transact-sql>
- Microsoft, *CREATE SEQUENCE (Transact-SQL)*. <https://learn.microsoft.com/en-us/sql/t-sql/statements/create-sequence-transact-sql>
- Hibernate ORM, *User Guide — Batching* (5.2). <https://docs.hibernate.org/orm/5.2/userguide/html_single/chapters/batch/Batching.html>
- Hibernate ORM, *User Guide — Performance Tuning and Best Practices* (5.2). <https://docs.hibernate.org/orm/5.2/userguide/html_single/appendices/BestPractices.html>
- Hibernate ORM, *Javadoc — `IdentityColumnSupport`* (6.6). <https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/dialect/identity/IdentityColumnSupport.html>
- Spring, *Spring Framework Reference — Data Access / Transaction Management*. <https://docs.spring.io/spring-framework/reference/data-access/transaction.html>
- Spring, *Spring Boot Reference — Distributed Transactions With JTA*. <https://docs.spring.io/spring-boot/reference/io/jta.html>
