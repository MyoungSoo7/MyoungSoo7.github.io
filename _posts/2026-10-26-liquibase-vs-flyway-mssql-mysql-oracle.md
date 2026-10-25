---
layout: post
title: "MSSQL · MySQL · Oracle 셋을 같이 쓸 때 — Liquibase 와 Flyway 는 저장소 모양과 '실패한 뒤의 상태'에서 갈린다"
date: 2026-10-26 01:37:12 +0900
categories: [Engineering, Database]
tags: [Liquibase, Flyway, MSSQL, MySQL, Oracle, 마이그레이션, 멀티DB, SpringBoot]
---

두 도구의 일반적인 차이는 앞선 글에서 다뤘다. [변경의 정체성을 무엇으로 잡느냐]({% post_url 2026-09-14-liquibase-vs-flyway-change-identity %})(버전 번호 vs `id`+`author`+파일 경로)와, [Flyway 개념을 Liquibase 로 옮긴 대응표]({% post_url 2026-09-19-liquibase-for-flyway-users-concept-mapping %})다. 이 글은 범위를 좁힌다. **한 제품의 스키마를 MSSQL·MySQL·Oracle 세 곳에 동시에 내보내야 할 때** 무엇이 달라지는가.

결론을 먼저 적는다. 셋을 동시에 지원하면 비교표에서 두 항목만 무거워진다.

1. **저장소의 모양** — 변경 하나를 *한 번* 쓰는가, *세 번* 쓰는가.
2. **실패한 뒤의 상태** — 이건 도구가 아니라 DB 가 정한다. 그래서 어느 도구를 고르든 셋 중 둘에서는 같은 문제를 겪는다.

사실 주장은 각 벤더의 공식 문서로 확인했고, 확인 시점은 2026-10-26 이다. 성능 비교는 하지 않는다. 세 DB 를 같은 조건에 놓고 두 도구를 비교한 중립 측정을 찾지 못했다.

---

## 1. 저장소 모양 — Liquibase 는 "한 번 쓰고 갈래를 친다"

Liquibase 의 모델형 changelog(XML·YAML·JSON)는 SQL 이 아니라 **변경을 기술**한다. `createTable` 같은 Change Type 을 적으면 Liquibase 가 접속한 DB 에 맞는 SQL 을 만든다. 어느 DB 인지는 `dbms` 속성 값이 아니라 **접속 URL 로 판별한다**고 문서에 적혀 있다.[^lb-dbms]

세 DB 에서 문법이 갈리는 지점에만 `dbms` 로 갈래를 친다. 단축명은 `mssql`, `mysql`, `oracle` 이고, `!` 을 붙이면 "그 DB 만 빼고" 라는 뜻이다.[^lb-dbms]

```yaml
databaseChangeLog:
  # 공통 — 한 번만 쓴다. SQL 은 DB 마다 Liquibase 가 생성
  - changeSet:
      id: 2026-10-26-01
      author: lms
      changes:
        - createTable:
            tableName: settlement
            columns:
              - column: { name: id,     type: bigint, constraints: { primaryKey: true } }
              - column: { name: amount, type: decimal(19,2) }

  # 문법이 갈리는 곳만 DB 별로
  - changeSet:
      id: 2026-10-26-02-oracle
      author: lms
      dbms: oracle
      changes:
        - sql:
            sql: CREATE INDEX ix_settlement_amt ON settlement(amount) ONLINE
  - changeSet:
      id: 2026-10-26-02-others
      author: lms
      dbms: "!oracle"
      changes:
        - createIndex:
            tableName: settlement
            indexName: ix_settlement_amt
            columns: [ { column: { name: amount } } ]
```

`CREATE TABLE` 끝에 `ENGINE=InnoDB` 같은 벤더 절만 덧붙이고 싶을 때는 `modifySql` 을 `dbms` 와 같이 쓴다. 다만 `modifySql` 은 XML·YAML·JSON 에서만 된다.[^lb-modifysql]

함정이 하나 있다. **`dbms` *전제조건(precondition)* 은 formatted SQL changelog 에서 쓸 수 없다.**[^lb-precond] 팀이 "SQL 이 편하니 `.sql` changelog 로 가자" 고 정하는 순간, 모델형이 주던 "한 번 쓰기" 이점이 대부분 사라진다. 셋을 동시에 지원할 거라면 Liquibase 의 장점은 모델형 포맷을 쓸 때만 성립한다.

## 2. 저장소 모양 — Flyway 는 "SQL 을 벤더별로 둔다"

Flyway 의 기본 단위는 **DB 에 그대로 실행되는 SQL 파일**이다. 도구가 SQL 을 생성하지 않는다(자동 생성은 Enterprise 기능이다).[^fw-features] 그래서 문법이 다른 변경은 사람이 DB 마다 따로 쓴다.

Flyway FAQ 가 직접 권하는 구성은 공통 위치와 DB 별 위치를 `locations` 로 함께 지정하는 방식이다.[^fw-faq]

```
db/migration/common/V1__create_settlement.sql      ← 세 DB 공통 문법만
db/migration/sqlserver/V2__index_settlement.sql
db/migration/mysql/V2__index_settlement.sql
db/migration/oracle/V2__index_settlement.sql
```

Spring Boot 를 쓰면 이 구성을 설정 한 줄로 만들 수 있다. `spring.flyway.locations` 에 `{vendor}` 자리표시자를 넣으면 접속한 DB 종류의 디렉터리로 치환된다.[^boot-vendor]

```properties
spring.flyway.locations=classpath:db/migration/common,classpath:db/migration/{vendor}
```

치환되는 값은 Spring Boot `DatabaseDriver` enum 이름을 소문자로 바꾼 것이다.[^boot-driver] 그래서 SQL Server 의 디렉터리 이름은 **`sqlserver`** 다. Liquibase 단축명 `mssql` 과 다르다. 두 도구를 오가는 팀이 디렉터리를 `mssql/` 로 만들면 SQL Server 마이그레이션이 **조용히 하나도 안 잡힌다.**

### 세 벌 복사가 실제로 치르는 비용

- **버전 번호를 세 폴더가 공유한다.** `V2` 가 `oracle/` 에만 있고 `mysql/` 에 없으면, MySQL 의 스키마 이력에는 V2 가 영영 비어 있다. Flyway 는 그게 의도인지 누락인지 모른다.
- **세 파일이 같은 의미인지는 사람이 보증한다.** 리뷰어는 diff 세 개를 나란히 놓고 대조해야 한다.
- 대신 **실행되는 SQL 이 눈에 보이는 그대로다.** DBA 가 리뷰하는 대상과 실제 실행되는 문장이 같다. Liquibase 모델형은 실제 SQL 을 보려면 `update-sql` 같은 미리보기를 한 번 더 돌려야 한다.

정리하면, Liquibase 는 *일관성*을 도구가 맡고 *투명성*은 미리보기로 확보한다. Flyway 는 *투명성*이 기본이고 *일관성*은 사람과 리뷰가 맡는다.

## 3. 실패한 뒤의 상태 — 도구가 아니라 DB 가 정한다

세 DB 를 같이 쓸 때 가장 자주 놓치는 지점이다. 마이그레이션이 중간에 실패하면 무엇이 남는가.

| DB | DDL 이 트랜잭션 안에서 롤백되나 | 근거 |
|---|---|---|
| SQL Server | **어느 정도 된다** | Flyway FAQ[^fw-faq] |
| MySQL | **안 된다** — DDL 앞뒤로 암묵 커밋 | MySQL 매뉴얼[^mysql-ic] |
| Oracle | **안 된다** — DDL 앞뒤로 암묵 커밋 | Oracle SQL Reference[^ora-commit][^ora-ddl] |

Oracle 문서의 표현은 이렇다. 암묵 커밋은 DDL *앞*에서 일어나며, **"그 문장이 오류로 끝나더라도"** 일어난다.[^ora-commit] MySQL 도 DDL 이 실행 전에 현재 트랜잭션을 끝낸다고 적고 있다.[^mysql-ic]

Flyway 문서는 이 경우의 결과를 그대로 적는다. DDL 트랜잭션을 깨끗하게 지원하지 않는 DB 에서는 실패 시 깨끗하게 롤백할 수 없으므로 마이그레이션을 *failed* 로 표시하고, **수동 정리가 필요할 수 있으며 `repair` 로 실패 기록을 지워야 할 수도 있다.**[^fw-tx] 같은 문서는 `mixed` 설정이 이 문제와 다른 문제라는 점도 밝힌다. `mixed` 는 "트랜잭션 안에서 아예 실행이 안 되는 문장"을 위한 설정이고, MySQL·Oracle 의 암묵 커밋을 해결해주지 않는다.[^fw-mixed]

이건 Liquibase 를 써도 똑같다. 같은 DB 엔진 위에서 돌기 때문이다. 그래서 세 DB 를 동시에 지원하는 저장소에서는 **같은 마이그레이션 파일이 SQL Server 에서는 깨끗하게 롤백되고, MySQL·Oracle 에서는 절반만 적용된 채로 남는다.** 테스트를 SQL Server 에서만 돌렸다면 이 차이는 운영에서 처음 보게 된다.

실무 대응은 두 가지다.

- **마이그레이션 하나에 DDL 하나.** Flyway FAQ 가 직접 제시하는 우회책이고, 번거롭다는 단점도 같이 적혀 있다.[^fw-faq] Liquibase 라면 체인지셋 하나에 Change Type 하나다.
- **CI 에서 세 DB 를 모두 띄워 돌린다.** 실패 경로까지 보려면 "일부러 실패하는 마이그레이션" 을 하나 넣어서 각 DB 에 무엇이 남는지 확인하는 테스트가 유용하다.

## 4. 되돌리기 — 세 DB 에서는 "몇 벌을 써야 하나" 의 문제가 된다

- **Liquibase**: 모델형 changelog 에서는 `createTable`·`addColumn`·`renameColumn` 같은 Change Type 의 역연산을 **자동 생성**한다. `dropTable`·`insert` 처럼 역연산이 정의되지 않는 것은 직접 써야 하고, **formatted SQL changelog 는 자동 롤백을 전혀 지원하지 않는다.**[^lb-rollback][^lb-autorb] 즉 모델형 + 자동 롤백 대상 Change Type 조합이면 *롤백 정의 하나로 세 DB 가 해결된다.*
- **Flyway**: `undo` 는 **Teams 이상** 기능이고, 반복 마이그레이션(`R__`)에는 undo 가 없다.[^fw-undo][^fw-features] undo 스크립트도 SQL 이므로, 2장의 벤더별 폴더 구성이라면 **undo 도 세 벌**이 된다.

그리고 3장 때문에 MySQL·Oracle 에서는 롤백이 필요한 바로 그 순간, 곧 *중간에 실패했을 때* 상태가 반쯤 적용돼 있다. 어느 도구의 롤백이든 "깨끗한 이전 상태" 를 전제로 만들어진다는 점을 기억해야 한다. 이미지만 되돌린다고 스키마가 되돌아가지 않는 문제는 [예전 글]({% post_url 2026-09-24-flyway-image-rollback-is-not-schema-rollback %})에서 다뤘다.

## 5. 지원 범위와 라이선스

- **지원 범위.** 세 DB 모두 양쪽에서 지원된다. Flyway 는 공식 표에 SQL Server 2008~2025, MySQL 5.6~9.4, Oracle 19c·21c·23ai 를 올려두고 있다. Oracle 18c 이하는 부분 지원으로 표시돼 있고, Oracle 11g 지원은 다음 메이저 릴리스에서 빠진다고 공지돼 있다.[^fw-dbs] Liquibase 의 `dbms` 단축명 목록에도 `mssql`·`mysql`·`oracle` 이 있다.[^lb-dbms]
- **라이선스.** Liquibase Community 는 **5.0 부터 FSL-1.1-ALv2** 다. 운영 사용과 수정은 자유롭다. 다만 경쟁하는 상업적 사용(예: 매니지드 서비스로 재판매)은 막히고, 각 릴리스는 2년 뒤 Apache 2.0 으로 전환된다. 벤더 스스로 **OSI 기준의 오픈소스는 아니다**라고 밝히고 있다.[^lb-fsl][^lb-50] Flyway 는 Community / Teams / Enterprise 로 기능이 나뉜다. undo 는 Teams 이상이고, 마이그레이션 자동 생성은 Enterprise 기능이다.[^fw-features]

## 6. 그래서 어느 쪽인가 — 세 DB 기준의 판단표

| 상황 | 기울어지는 쪽 | 이유 |
|---|---|---|
| 변경 대부분이 테이블·컬럼·인덱스 같은 표준 DDL | **Liquibase (모델형)** | 한 번 쓰면 세 DB 용 SQL 이 생성되고, 자동 롤백도 한 벌로 끝난다 |
| 저장 프로시저·패키지·벤더 힌트처럼 벤더 SQL 이 많음 | **Flyway** | 어차피 세 벌을 써야 한다면 실행 SQL 이 그대로 보이는 쪽이 리뷰가 쉽다 |
| DBA 가 실행 SQL 원문을 승인해야 함 | **Flyway** (또는 Liquibase `update-sql` 산출물로 승인) | 승인 대상과 실행 대상이 같아야 한다 |
| 팀이 `.sql` changelog 를 고집함 | **Flyway** | Liquibase formatted SQL 에서는 `dbms` 전제조건도, 자동 롤백도 없다[^lb-precond][^lb-autorb] |
| 매니지드 서비스로 도구를 재판매하는 사업 | 라이선스 검토 먼저 | Liquibase 5.0+ 의 FSL 경쟁 사용 제한[^lb-fsl] |

어느 쪽을 고르든 3장의 문제는 남는다. 세 DB 를 지원한다면 *도구 선택*보다 **세 DB 모두에서 CI 를 돌리는 것**, 그리고 **마이그레이션 하나에 DDL 하나**라는 규율이 더 큰 차이를 만든다.

---

## References

[^lb-dbms]: Liquibase, *dbms* (changelog attribute) — 유효한 단축명 목록, `!` 부정, 접속 URL 로 DB 판별. <https://docs.liquibase.com/secure/reference-guide-6-0/changelog-attributes/dbms>
[^lb-modifysql]: Liquibase, *modifySql* — 벤더 절 추가, XML·YAML·JSON 에서만 가능. <https://www.liquibase.org/documentation/modify_sql.html>
[^lb-precond]: Liquibase, *What are preconditions?* — `dbms` 전제조건은 formatted SQL 에서 불가, `onFail` 값. <https://docs.liquibase.com/community/user-guide-5-0/what-are-preconditions>
[^lb-rollback]: Liquibase, *rollback* command — formatted SQL 은 롤백을 수동 정의해야 함. <https://docs.liquibase.com/secure/reference-guide-6-0/rollback>
[^lb-autorb]: Liquibase, *What automatic rollbacks does Liquibase support?* — 자동 롤백 Change Type 표. <https://docs.liquibase.com/secure/set-up-secure-automation-6-0/what-automatic-rollbacks-does-liquibase-support>
[^lb-fsl]: Liquibase, *Strengthening Liquibase Community for the Future* (2025-09-30) — FSL 전환, 2년 후 Apache 2.0, OSI 오픈소스 아님. <https://www.liquibase.com/blog/liquibase-community-for-the-future-fsl>
[^lb-50]: Liquibase Community 5.0 release notes. <https://docs.liquibase.com/community/release-notes/5-0>
[^fw-faq]: Redgate Flyway, *Frequently Asked Questions* — DDL 트랜잭션 지원 DB, 마이그레이션당 DDL 1개 우회책, DB 별 `locations` 구성. <https://documentation.red-gate.com/flyway/reference/usage/frequently-asked-questions>
[^fw-tx]: Redgate Flyway, *Migration transaction handling* — 실패 시 failed 표시, 수동 정리와 `repair`. <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/migration-transaction-handling>
[^fw-mixed]: Redgate Flyway, *Flyway Mixed Setting* — MySQL·Oracle 의 암묵 커밋과는 별개. <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-mixed-setting>
[^fw-undo]: Redgate Flyway, *Undo* (Flyway Teams). <https://documentation.red-gate.com/flyway/reference/commands/undo>
[^fw-features]: Redgate Flyway, *Feature Summary* — 에디션별 기능표. <https://documentation.red-gate.com/flyway/learn-more-about-flyway/feature-summary>
[^fw-dbs]: Redgate Flyway, *Supported databases and versions*. <https://documentation.red-gate.com/flyway/getting-started-with-flyway/system-requirements/supported-databases-and-versions>
[^boot-vendor]: Spring Boot, *Database Initialization* — `spring.flyway.locations` 의 `{vendor}` 자리표시자. <https://docs.spring.io/spring-boot/how-to/data-initialization.html>
[^boot-driver]: Spring Boot 소스, `DatabaseDriver.getId()` = `name().toLowerCase()` (`SQLSERVER` → `sqlserver`). <https://github.com/spring-projects/spring-boot/blob/main/module/spring-boot-jdbc/src/main/java/org/springframework/boot/jdbc/DatabaseDriver.java>
[^mysql-ic]: MySQL 9.7 Reference Manual, *15.3.3 Statements That Cause an Implicit Commit*. <https://dev.mysql.com/doc/refman/9.7/en/implicit-commit.html>
[^ora-commit]: Oracle Database 19c SQL Language Reference, *COMMIT* — DDL 전후 암묵 커밋, 오류가 나도 앞의 커밋은 발생. <https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/COMMIT.html>
[^ora-ddl]: Oracle SQL Language Reference, *Types of SQL Statements*. <https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/Types-of-SQL-Statements.html>
