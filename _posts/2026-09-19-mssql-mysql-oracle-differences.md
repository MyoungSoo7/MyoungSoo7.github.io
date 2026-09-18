---
layout: post
title: "MSSQL · MySQL · Oracle 은 무엇이 다른가 — 문법이 아니라 동시성 모델, DDL 트랜잭션, 기본 대소문자"
date: 2026-09-19 03:20:00 +0900
categories: [Engineering, Database]
tags: [MSSQL, SQL Server, MySQL, Oracle, Isolation Level, MVCC, DDL, Collation]
---

"MSSQL 과 MySQL 과 Oracle 의 차이" 를 물으면 대개 문법 이야기가 돌아온다. `TOP` 이냐 `LIMIT` 이냐, `NVL` 이냐 `ISNULL` 이냐. 그건 컴파일 에러로 드러나니 오히려 안전한 차이다. **진짜 물리는 지점은 문법이 같은데 동작이 다른 곳**이다. 똑같이 생긴 `SELECT` 가 어디선 멈추고 어디선 안 멈추며, 똑같은 `WHERE id = 'Kim'` 이 어디선 한 행을 어디선 두 행을 돌려준다.

세 엔진을 실제로 가르는 축 세 개 — **동시성 모델, DDL 의 트랜잭션성, 기본 대소문자** — 를 각 벤더의 1차 문서 기준으로 정리한다. Oracle·MySQL·MariaDB·Tibero 의 SQL 방언 차이(빈 문자열 = NULL, `||`, NULL 정렬 순서, `ROWNUM` 등)는 [이전 글]({% post_url 2026-08-12-oracle-mysql-mariadb-tibero-comparison %})에서 다뤘으니 여기서는 되풀이하지 않는다.

인용 기준 버전은 각 문서 URL 그대로다 — SQL Server `ver17` 문서, **MySQL 8.4 LTS** 레퍼런스 매뉴얼, **Oracle Database 26ai** 문서.

## 1. 축 ① — 읽기가 쓰기를 기다리는가

이게 셋 사이의 가장 큰 차이다. 그리고 문법에는 전혀 드러나지 않는다.

**Oracle 은 읽기와 쓰기가 서로를 막지 않는다.** Oracle 은 undo 데이터로 다중버전 읽기 일관성(multiversion read consistency)을 구현하며, 문서가 특성으로 못박는다 — "Nonblocking queries — Readers and writers of data do not block one another", 그리고 "Oracle AI Database never permits a dirty read"[^oracle-concepts]. 즉 `UPDATE` 가 걸려 있는 행을 다른 세션이 `SELECT` 해도, 그 세션은 기다리지 않고 변경 전 버전을 본다.

**SQL Server 의 기본값은 정반대에 가깝다.** 기본 격리 수준은 READ COMMITTED 로 같지만, 그 READ COMMITTED 를 *어떻게 구현하느냐* 가 데이터베이스 옵션 `READ_COMMITTED_SNAPSHOT` 에 달려 있다. 이 옵션이 **OFF 인 상태가 SQL Server 의 기본값**이고, 이때 엔진은 "uses shared locks to prevent other transactions from modifying rows while the current transaction is running a read operation. The shared locks also block the statement from reading rows modified by other transactions until the other transaction is completed" 라고 문서가 직접 기술한다[^mslearn-isolation]. 읽는 쪽이 쓰는 쪽을 막고, 쓰는 쪽이 읽는 쪽을 막는다.

여기서 자주 놓치는 함정이 하나 더 있다. **같은 제품군인데 기본값이 다르다.** 같은 문서가 `READ_COMMITTED_SNAPSHOT ON` 은 "the default on Azure SQL Database and SQL database in Microsoft Fabric" 이라고 명시한다[^mslearn-isolation]. 온프레미스 SQL Server 에서 멀쩡하던 코드가 Azure SQL 로 옮기면 블로킹 양상이 달라지고, 그 반대도 마찬가지다. 엔진 이름이 같다고 동시성 동작이 같지 않다.

**MySQL InnoDB 는 세 번째 자리에 있다.** "The default isolation level for `InnoDB` is `REPEATABLE READ`"[^mysql-isolation] — 셋 중 유일하게 기본이 READ COMMITTED 가 아니다. InnoDB 도 Oracle 과 마찬가지로 일관된 읽기(consistent read)에 스냅샷을 쓰지만, 스냅샷을 잡는 시점이 다르다. REPEATABLE READ 에서는 **같은 트랜잭션 안의 첫 읽기가 세운 스냅샷**을 이후 읽기가 계속 본다. 그래서 트랜잭션을 길게 열어 두면 나중에 읽어도 옛날 데이터가 나온다 — 버그가 아니라 정의된 동작이다.

| | SQL Server | MySQL (InnoDB) | Oracle |
|---|---|---|---|
| 기본 격리 수준 | READ COMMITTED | **REPEATABLE READ** | READ COMMITTED |
| 기본 구현 | **잠금 기반** (`READ_COMMITTED_SNAPSHOT` OFF) | 스냅샷(일관된 읽기) | undo 기반 다중버전 |
| 읽기가 쓰기에 막히는가 | **기본적으로 막힌다** | 아니오 | 아니오 |
| 스냅샷 방식 선택 | DB 옵션 ON/OFF + `SNAPSHOT` 격리 수준 | 격리 수준으로 | 항상 |
| 클라우드판 기본값 | Azure SQL 은 RCSI **ON** | — | — |

실무 함의는 단순하다. **Oracle 이나 MySQL 에서 개발해 SQL Server 로 옮기면, 아무것도 안 바꿨는데 조회가 멈추기 시작한다.** 반대로 SQL Server 에서 `WITH (NOLOCK)` 을 습관처럼 붙여 온 팀은, Oracle 로 가면 그 힌트가 필요 없어질 뿐 아니라 애초에 막을 게 없었다는 걸 알게 된다. `NOLOCK` 은 READ UNCOMMITTED 이고, 잠금 기반 기본값 때문에 생긴 회피책이다.

## 2. Oracle 에는 REPEATABLE READ 가 아예 없다

표준 SQL 이 정의하는 네 격리 수준 중 Oracle 이 제공하는 건 둘뿐이다. `SET TRANSACTION` 문법이 허용하는 값은 `READ ONLY`, `READ WRITE`, `ISOLATION LEVEL SERIALIZABLE`, `ISOLATION LEVEL READ COMMITTED` 이고, 문서는 "The `READ COMMITTED` setting is the default Oracle Database transaction behavior" 라고 적는다[^oracle-settx]. **READ UNCOMMITTED 도 REPEATABLE READ 도 문법에 없다.**

SQL Server 는 다섯을 제공한다 — READ UNCOMMITTED / READ COMMITTED / REPEATABLE READ / SNAPSHOT / SERIALIZABLE[^mslearn-isolation]. `SNAPSHOT` 은 표준에 없는 SQL Server 고유 수준이다.

그래서 "우리는 REPEATABLE READ 로 맞춰 쓴다" 는 합의는 **세 엔진 공통 정책이 될 수 없다.** MySQL 에선 기본값이고, SQL Server 에선 명시적으로 켤 수 있고, Oracle 에선 존재하지 않는다. Oracle 에서 같은 보장을 원하면 SERIALIZABLE 로 올라가거나 `SELECT ... FOR UPDATE` 로 직접 잠가야 한다 — 비용도 실패 양상도 다른 선택이다.

## 3. 축 ② — DDL 을 롤백할 수 있는가

마이그레이션 스크립트가 중간에 깨졌을 때 무엇이 남는가. 이 질문의 답이 셋 다 다르다.

**Oracle — 롤백 불가.** "Oracle Database implicitly commits the current transaction before and after executing a data definition language (DDL) statement"[^oracle-settx]. DDL 앞뒤로 커밋이 박히니 DDL 을 트랜잭션에 넣는다는 개념 자체가 성립하지 않는다.

**MySQL — 역시 롤백 불가. 그런데 이름 때문에 오해하기 쉽다.** MySQL 8.0 부터 "atomic DDL" 이 들어왔고, 단일 DDL 문의 데이터 딕셔너리 갱신·스토리지 엔진 작업·바이너리 로그 기록이 하나의 원자적 연산으로 묶여 "서버가 중간에 죽어도" 커밋 아니면 롤백으로 끝난다[^mysql-atomic-ddl]. 하지만 같은 문서가 바로 못박는다 — **"Atomic DDL is not transactional DDL. DDL statements, atomic or otherwise, implicitly end any transaction that is active in the current session, as if you had done a COMMIT before executing the statement. This means that DDL statements cannot be performed within another transaction"**[^mysql-atomic-ddl]. 즉 *문 하나*는 원자적이지만, *여러 문*을 하나의 트랜잭션으로 묶을 수는 없다. 암묵적 커밋을 유발하는 문의 목록은 따로 문서화돼 있고, `CREATE`/`ALTER`/`DROP TABLE`, `CREATE INDEX`, `TRUNCATE TABLE`, `RENAME TABLE` 같은 DDL 뿐 아니라 `ALTER USER`·`GRANT`·`REVOKE`·`LOCK TABLES`·`ANALYZE TABLE`, 그리고 `BEGIN` 자체도 포함된다[^mysql-implicit-commit].

같은 문서의 `TEMPORARY` 테이블 단서는 더 고약하다 — 임시 테이블에 대한 DDL 은 암묵적 커밋을 일으키지 않지만 롤백도 되지 않아서, "the use of such statements causes transactional atomicity to be violated"[^mysql-implicit-commit]. 커밋도 롤백도 아닌 상태가 남는다는 뜻이다.

**SQL Server — 롤백 가능.** SQL Server 의 DDL 은 트랜잭션 안에서 돌고 되감을 수 있다. 문서가 드는 가장 직접적인 증거는 DDL 트리거 예제다. `ON DATABASE FOR DROP_TABLE, ALTER_TABLE` 로 걸린 트리거가 본문에서 그냥 `ROLLBACK;` 을 실행해 테이블 삭제·변경을 통째로 취소한다[^mslearn-ddl-trigger]. DDL 이 롤백 가능한 트랜잭션 컨텍스트 안에서 실행되지 않으면 성립할 수 없는 동작이다.

| | SQL Server | MySQL | Oracle |
|---|---|---|---|
| DDL 을 명시적 트랜잭션에 넣기 | 가능 | **불가** (암묵적 커밋) | **불가** (앞뒤 암묵적 커밋) |
| DDL 롤백 | 가능 | 문 단위 원자성만 | 불가 |
| 실패한 마이그레이션 후 상태 | 전부 되감김 | **일부 적용된 채 남음** | **일부 적용된 채 남음** |

이 차이는 Flyway·Liquibase 같은 도구를 쓸 때 그대로 나타난다. 같은 마이그레이션 도구, 같은 changelog 인데 **SQL Server 에서는 실패한 스크립트가 흔적 없이 되감기고, MySQL·Oracle 에서는 앞쪽 몇 문이 적용된 어중간한 스키마가 남는다.** 그래서 후자에서는 "마이그레이션 하나 = DDL 하나" 로 잘게 쪼개고 재실행 안전성(idempotency)을 스크립트 쪽에서 직접 확보해야 한다. 도구가 대신 해 주지 않는다. 엔진이 못 하는 일이기 때문이다.

## 4. 축 ③ — `WHERE name = 'KIM'` 이 'kim' 을 찾는가

문자열 비교의 기본 규칙이 셋 다 다르다. 그리고 이건 에러가 아니라 **조용히 다른 결과**로 나타난다.

**Oracle 은 기본이 대소문자 구분이다.** `NLS_SORT` 의 기본값은 `BINARY` 이고[^oracle-nls-sort], 실제로 어떤 연산이 `NLS_SORT` 를 따르는지 결정하는 `NLS_COMP` 도 기본이 `BINARY` 다 — "Most SQL operations compare character values using binary collation, regardless of the value set in `NLS_SORT`. This is the default setting"[^oracle-linguistic]. 바이트 값 그대로 비교하니 `'KIM' <> 'kim'` 이다.

**MySQL 은 기본이 대소문자·악센트 무시다.** `utf8mb4` 의 기본 collation 은 `utf8mb4_0900_ai_ci` 이고[^mysql-charset], 이름 그대로 accent-insensitive, case-insensitive 다. `'KIM' = 'kim'` 이 참이다.

**SQL Server 는 "설치할 때 결정된다" 가 정답이다.** 문서는 "During SQL Server setup, the default installation collation setting is determined by the operating system (OS) locale" 이라고 적고, 예로 English (United States) 로케일의 설치 기본값이 `SQL_Latin1_General_CP1_CI_AS` 임을 든다[^mslearn-collation]. 접미사 `_CI` 는 case-insensitive 를 뜻한다[^mslearn-collation]. 즉 흔한 en-US 설치에서는 대소문자를 구분하지 않지만, **"SQL Server 는 CI 다" 라고 외워 두면 틀릴 수 있다.** 서버 collation 은 설치 시 OS 로케일로 정해지고, 나중에 바꾸려면 모든 객체와 데이터를 내보낸 뒤 `master` 를 재구축하고 다시 넣어야 한다[^mslearn-collation]. 실제 값은 `SERVERPROPERTY('Collation')` 으로 확인하는 게 맞다.

| | SQL Server | MySQL | Oracle |
|---|---|---|---|
| 기본 문자열 비교 | 설치 로케일에 따름 (en-US → `SQL_Latin1_General_CP1_CI_AS`, 대소문자 무시) | `utf8mb4_0900_ai_ci` (대소문자·악센트 무시) | `BINARY` (**대소문자 구분**) |
| 결정 시점 | 설치 시 서버 단위 → DB → 컬럼 | 서버/DB/테이블/컬럼 | 세션 파라미터(`NLS_SORT`/`NLS_COMP`) + 선언된 collation |
| 열 단위 재정의 | `COLLATE` 절 | `COLLATE` 절 | 선언 collation / `NLSSORT()` |

가장 아픈 시나리오는 **아이디·이메일 중복 검사**다. MySQL 에서 `UNIQUE(email)` 이 `Kim@a.com` 과 `kim@a.com` 을 같은 값으로 보고 막아 주던 것이, Oracle 로 옮기면 둘 다 들어간다. 코드는 한 줄도 안 바뀌었고 에러도 안 난다. 반대로 Oracle 에서 대소문자 구분을 전제로 짠 조회가 SQL Server(CI) 에서는 의도보다 많은 행을 돌려준다. 이식할 때 **비교 규칙을 명시적으로 고정**(컬럼 `COLLATE` 선언, 또는 저장 시 정규화)하는 것 말고 안전한 길이 없다.

## 5. 덤 — SQL Server 의 `datetime` 은 문서가 쓰지 말라고 한다

세 엔진 비교와 별개로, SQL Server 쪽에서 레거시 코드를 물려받을 때 자주 만나는 지뢰다. Microsoft 문서가 페이지 상단에 직접 적는다 — "Avoid using datetime for new work. Instead, use the time, date, datetime2, and datetimeoffset data types"[^mslearn-datetime].

이유도 문서에 있다. `datetime` 의 정확도는 "Rounded to increments of `.000`, `.003`, or `.007` seconds" 다[^mslearn-datetime]. 밀리초를 저장한 것 같지만 실제로는 3.33ms 눈금에 반올림돼 들어간다. 범위 하한은 1753-01-01 이고, 타임존 개념이 없다[^mslearn-datetime]. 밀리초 단위로 이벤트 순서를 비교하는 코드가 SQL Server 에서만 이상하게 도는 이유가 대개 이것이다. 새로 만드는 컬럼은 `datetime2`, 타임존이 필요하면 `datetimeoffset` 이 정답이다.

## 6. 정리 — 셋을 고를 때 실제로 봐야 하는 것

| 질문 | SQL Server | MySQL | Oracle |
|---|---|---|---|
| 조회가 갱신에 막히나 | **기본적으로 막힘** (RCSI 로 끌 수 있음) | 아니오 | 아니오 |
| 기본 격리 수준 | READ COMMITTED | REPEATABLE READ | READ COMMITTED |
| REPEATABLE READ 존재 | 있음 | 기본값 | **없음** |
| DDL 롤백 | 됨 | 안 됨 | 안 됨 |
| 기본 문자열 비교 | 로케일 의존(보통 대소문자 무시) | 대소문자 무시 | **대소문자 구분** |

엔진 선택이나 이식을 앞뒀다면 순서는 이렇다.

1. **동시성 모델부터 본다.** 잠금 기반 기본값(SQL Server) 위에서 짠 코드와 다중버전 위에서 짠 코드는 구조가 다르다. 나중에 힌트로 때울 수 있는 층위가 아니다.
2. **마이그레이션 전략을 DDL 트랜잭션성에 맞춘다.** MySQL·Oracle 로 간다면 "실패하면 되감긴다" 를 가정에서 지운다.
3. **비교 규칙을 스키마에 명시한다.** 기본값에 기대면 엔진을 옮기는 순간 데이터 무결성이 조용히 달라진다.
4. 문법 차이(`LIMIT`/`ROWNUM`/`TOP`, NULL 정렬, 빈 문자열)는 마지막에 본다. 컴파일 에러로 드러나므로 가장 덜 위험하다 — [이전 글]({% post_url 2026-08-12-oracle-mysql-mariadb-tibero-comparison %}) 참고.

## 근거의 한계

- **이 글에는 성능 수치가 없다.** 세 엔진의 중립적 head-to-head 벤치마크는 공개돼 있지 않고, Oracle 의 라이선스는 사용자가 벤치마크 결과를 공개하는 것을 제한한다(이른바 DeWitt 조항). 따라서 "어느 게 빠르다" 는 주장은 하지 않는다. 위 표는 전부 **동작(behavior) 차이**이고 각 항목은 해당 벤더의 1차 문서로 확인 가능하다.
- **인용 기준 버전**은 SQL Server `ver17` 문서, MySQL 8.4 LTS 매뉴얼, Oracle Database 26ai 문서다. 기본값은 버전과 배포 형태(온프레미스/클라우드)에 따라 바뀐다 — 특히 `READ_COMMITTED_SNAPSHOT` 은 같은 SQL Server 계열 안에서도 다르다는 점을 본문에 적은 이유다.
- 각 엔진의 기본값은 **설치·구성으로 바뀔 수 있다.** 운영 환경에서는 문서 대신 실제 값을 조회해 확인하는 게 맞다 — SQL Server `SERVERPROPERTY('Collation')` / `sys.databases.is_read_committed_snapshot_on`, MySQL `SELECT @@transaction_isolation`, Oracle `NLS_SESSION_PARAMETERS`.

## References

[^mslearn-isolation]: Microsoft Learn, *SET TRANSACTION ISOLATION LEVEL (Transact-SQL)*. <https://learn.microsoft.com/en-us/sql/t-sql/statements/set-transaction-isolation-level-transact-sql?view=sql-server-ver17>
[^mslearn-collation]: Microsoft Learn, *Collation and Unicode support*. <https://learn.microsoft.com/en-us/sql/relational-databases/collations/collation-and-unicode-support?view=sql-server-ver17>
[^mslearn-datetime]: Microsoft Learn, *datetime (Transact-SQL)*. <https://learn.microsoft.com/en-us/sql/t-sql/data-types/datetime-transact-sql?view=sql-server-ver17>
[^mslearn-ddl-trigger]: Microsoft Learn, *DDL triggers*. <https://learn.microsoft.com/en-us/sql/relational-databases/triggers/ddl-triggers?view=sql-server-ver17>
[^mysql-isolation]: MySQL 8.4 Reference Manual, §17.7.2.1 *Transaction Isolation Levels*. <https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html>
[^mysql-atomic-ddl]: MySQL 8.4 Reference Manual, §15.1.1 *Atomic Data Definition Statement Support*. <https://dev.mysql.com/doc/refman/8.4/en/atomic-ddl.html>
[^mysql-implicit-commit]: MySQL 8.4 Reference Manual, §15.3.3 *Statements That Cause an Implicit Commit*. <https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html>
[^mysql-charset]: MySQL 8.4 Reference Manual, §12.2 *Character Sets and Collations in MySQL*. <https://dev.mysql.com/doc/refman/8.4/en/charset-mysql.html>
[^oracle-concepts]: Oracle Database 26ai, *Database Concepts*, ch.12 *Data Concurrency and Consistency*. <https://docs.oracle.com/en/database/oracle/oracle-database/26/cncpt/data-concurrency-and-consistency.html>
[^oracle-settx]: Oracle Database 26ai, *SQL Language Reference*, `SET TRANSACTION`. <https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/SET-TRANSACTION.html>
[^oracle-nls-sort]: Oracle Database 26ai, *Database Reference*, `NLS_SORT`. <https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/NLS_SORT.html>
[^oracle-linguistic]: Oracle Database 26ai, *Globalization Support Guide*, *Linguistic Sorting and Matching*. <https://docs.oracle.com/en/database/oracle/oracle-database/26/nlspg/linguistic-sorting-and-matching.html>
