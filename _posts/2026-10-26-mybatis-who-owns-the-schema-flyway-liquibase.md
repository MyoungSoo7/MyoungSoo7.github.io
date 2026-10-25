---
layout: post
title: "MyBatis 는 스키마를 모른다 — 그 빈자리를 Flyway·Liquibase 가 메우는 방식과, 끝내 테스트에 남는 것"
date: 2026-10-26 02:11:27 +0900
categories: [Engineering, Database]
tags: [MyBatis, Flyway, Liquibase, 마이그레이션, SpringBoot, 테스트, Testcontainers]
---

> Liquibase 와 Flyway 를 서로 비교하는 글은 이미 여러 편 썼다([변경의 정체성](/2026/09/14/liquibase-vs-flyway-change-identity/), [개념 대응표](/2026/09/19/liquibase-for-flyway-users-concept-mapping/), [MSSQL·MySQL·Oracle](/2026/10/26/liquibase-vs-flyway-mssql-mysql-oracle/)). 이 글은 비교가 아니다. **MyBatis 와 함께 쓸 때** 세 도구 사이에 생기는 경계를 다룬다. 어디까지가 누구 책임이고, 그 경계 사이로 무엇이 새는지를 본다.

## 1. 출발점: MyBatis 에는 스키마 쪽 기능이 없다

JPA(Hibernate)를 쓰면 엔티티에서 스키마를 만들거나(`create`), 엔티티와 실제 테이블이 맞는지 기동할 때 검사할 수 있다(`validate`). Spring Boot 문서는 `spring.jpa.hibernate.ddl-auto` 값으로 `none`, `validate`, `update`, `create`, `create-drop` 을 나열한다([Spring Boot — Database Initialization](https://docs.spring.io/spring-boot/how-to/data-initialization.html)).

MyBatis 에는 이에 해당하는 기능이 없다. MyBatis 는 직접 쓴 SQL 을 객체에 매핑하는 프레임워크이고([MyBatis 3 소개](https://mybatis.org/mybatis-3/)), 매퍼 XML 이나 `@Select` 안의 컬럼 이름은 **그냥 문자열**이다. 그래서 두 가지가 따라온다.

- **스키마를 만드는 주체가 MyBatis 바깥에 따로 있어야 한다.**
- **스키마와 SQL 이 어긋나도 기동 시점엔 아무도 모른다.** 컬럼 이름을 바꾸는 마이그레이션이 들어가도 앱은 정상적으로 뜬다. 깨지는 건 그 매퍼 문장이 처음 실행되는 순간이다.

이 글의 나머지는 이 두 가지를 각각 어떻게 메우는지에 관한 것이다.

## 2. 스키마의 주인 후보는 셋이다 — MyBatis 에도 자체 도구가 있다

잘 알려져 있지 않지만 MyBatis 프로젝트에는 자체 마이그레이션 도구 **MyBatis Migrations** 가 있다. 공식 소개는 Rails Migrations 와 dbdeploy 에서 영향을 받았다고 밝히고, 목표로 "앞으로도 뒤로도 마이그레이션(evolve, devolve)"과 "DB 현재 상태를 쉽게 파악"을 든다([MyBatis Migrations — Introduction](https://mybatis.org/migrations/)).

공식 문서에서 확인한 형태는 이렇다.

- `migrate new "create blog table"` 을 실행하면 `20090807221754_create_blog_table.sql` 같은 파일이 생긴다. 앞의 숫자는 식별자이자 타임스탬프이고, 정렬 순서이기도 하다. 3.2.1 부터는 `--idpattern=000` 으로 `003_…` 같은 일련번호도 쓸 수 있다([new 명령](https://mybatis.org/migrations/new.html)).
- **적용 SQL 과 되돌림 SQL 을 한 파일에 둔다.** `-- //@UNDO` 줄 위가 올릴 때, 아래가 내릴 때 실행된다(같은 문서).
- 적용 이력은 DB 의 changelog 테이블에 남고, `migrate status` 로 미적용(`...pending...`) 항목까지 볼 수 있다([status 명령](https://mybatis.org/migrations/status.html)).

| | MyBatis Migrations | Flyway | Liquibase |
|---|---|---|---|
| 변경 단위 | 타임스탬프(또는 일련번호) `.sql` | `V<버전>__<설명>.sql` / Java | changelog(XML·YAML·JSON·SQL)의 changeset |
| 되돌림 | 같은 파일 `-- //@UNDO` 구역 | 에디션에 따라 다름 — [대응표 글](/2026/09/19/liquibase-for-flyway-users-concept-mapping/) 참고 | changeset 단위 rollback |
| Spring Boot 기동 시 자동 실행 | **없음** | 있음 | 있음 |

마지막 줄이 실무에서는 가장 크게 작용한다. Spring Boot 문서는 "Spring Boot 는 두 개의 상위 마이그레이션 도구, Flyway 와 Liquibase 를 지원한다"고 적는다([Spring Boot — Database Initialization](https://docs.spring.io/spring-boot/how-to/data-initialization.html)). MyBatis Migrations 는 이 자동설정 목록에 없다. 쓰려면 앱 기동과 별개의 단계(CLI 등)로 돌려야 하고, 3절에서 다룰 **기동 순서 보장도 받지 못한다.** 같은 이름 아래 있다고 MyBatis 와 가장 잘 맞는 선택이 되는 건 아니다.

같은 문서는 하나 더 경고한다. Flyway·Liquibase 를 쓰면 스키마는 그 도구 **하나로만** 만들라고 하고, `schema.sql`/`data.sql` 을 함께 쓰는 방식은 권장하지 않으며 **향후 지원이 제거될 예정**이라고 적었다. MyBatis 프로젝트에 남아 있는 `schema.sql` 은 정리 대상이다.

## 3. 기동 순서 — 매퍼가 마이그레이션보다 먼저 DB 를 만지면

빈 DB 에서 앱을 띄울 때, 마이그레이션이 끝나기 전에 MyBatis 가 쿼리를 날리면 "테이블 없음"으로 기동이 실패한다. 실제로 이 문제가 MyBatis Spring Boot Starter 이슈로 보고됐다. 보고자는 SqlSessionFactory·SqlSessionTemplate 이 Liquibase/Flyway 초기화가 끝나기 전에 쓰일 수 있다고 했고, Flyway/Liquibase 자동설정이 순서를 보장해 주는 대상은 JdbcTemplate·EntityManager 같은 표준 빈뿐이라고 지적했다([mybatis/spring-boot-starter #537](https://github.com/mybatis/spring-boot-starter/issues/537)).

메인테이너는 **2.3.0 에서 해결했고 Spring Boot 2.5 이상이 필요하다**고 답했다(같은 이슈). 해결 방법은 Spring Boot 의 `DependsOnDatabaseInitializationDetector` 확장점이다. 스타터가 등록하는 감지기의 실제 소스는 이렇다([MybatisDependsOnDatabaseInitializationDetector](https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/xref/org/mybatis/spring/boot/autoconfigure/MybatisDependsOnDatabaseInitializationDetector.html)).

```java
class MybatisDependsOnDatabaseInitializationDetector
    extends AbstractBeansOfTypeDependsOnDatabaseInitializationDetector {
  @Override
  protected Set<Class<?>> getDependsOnDatabaseInitializationBeanTypes() {
    return Collections.singleton(SqlSessionTemplate.class);
  }
}
```

스타터의 테스트도 같은 계약을 고정해 둔다. Flyway 가 있으면 `sqlSessionTemplate` 빈 정의의 depends-on 이 `flywayInitializer`·`flyway` 이고, Liquibase 가 있으면 `liquibase` 다([MybatisAutoConfigurationTest](https://github.com/mybatis/spring-boot-starter/blob/master/mybatis-spring-boot-autoconfigure/src/test/java/org/mybatis/spring/boot/autoconfigure/MybatisAutoConfigurationTest.java)).

소스를 읽으면 경계가 정확히 보인다. **순서가 보장되는 건 `SqlSessionTemplate` 타입 빈뿐이다.**

- 평범한 구성, 즉 스타터 자동설정에 `@Mapper`/`@MapperScan` 을 쓰는 경우는 매퍼가 이 템플릿을 거치므로 안전하다.
- `SqlSessionFactory` 를 주입받아 직접 `openSession()` 을 여는 초기화 코드(`@PostConstruct` 등)는 이 depends-on 밖에 있다. *추론:* 그런 코드가 빈 생성 시점에 DB 를 건드리면 마이그레이션보다 먼저 실행될 수 있다. DB 를 건드리는 기동 로직은 컨텍스트가 다 뜬 뒤에 도는 `ApplicationRunner` 로 옮기는 편이 경계가 분명하다.
- **DataSource 가 둘 이상인 경우.** Flyway 는 기본적으로 `@Primary` DataSource 로 마이그레이션한다. 다른 DataSource 를 쓰려면 `@FlywayDataSource` 를 붙이거나 `spring.flyway.url`/`user` 를 따로 지정해야 한다([Spring Boot — Database Initialization](https://docs.spring.io/spring-boot/how-to/data-initialization.html)). 따라서 두 번째 DB 용 매퍼를 위해 SqlSessionTemplate 을 하나 더 만들어도 그 **DB 의 스키마는 아무도 올려 주지 않는다.** 순서 보장은 "누군가 마이그레이션을 한다"는 전제 위에서만 의미가 있다.

## 4. 매퍼와 스키마의 어긋남 — 결국 테스트가 잡는다

1절의 두 번째 문제, 즉 "스키마는 바뀌었는데 매퍼 SQL 은 그대로"인 상황은 Flyway 도 Liquibase 도 잡지 못한다. 두 도구는 *마이그레이션 파일*의 체크섬과 적용 이력을 검증할 뿐, 애플리케이션 SQL 은 보지 않는다. 그리고 MyBatis 에는 JPA 의 `validate` 같은 기능이 없다. 남는 곳은 테스트뿐이다.

다행히 `@MybatisTest` 가 이 경로를 이미 깔아 둔다. 테스트 자동설정이 불러오는 목록(`AutoConfigureMybatis.imports`)을 직접 보면 MyBatis 자동설정 옆에 이런 줄이 있다([소스](https://github.com/mybatis/spring-boot-starter/blob/master/mybatis-spring-boot-test-autoconfigure/src/main/resources/META-INF/spring/org.mybatis.spring.boot.test.autoconfigure.AutoConfigureMybatis.imports)).

```
optional:org.springframework.boot.flyway.autoconfigure.FlywayAutoConfiguration
optional:org.springframework.boot.liquibase.autoconfigure.LiquibaseAutoConfiguration
optional:org.springframework.boot.testcontainers.service.connection.ServiceConnectionAutoConfiguration
```

즉 클래스패스에 Flyway 나 Liquibase 가 있으면 **`@MybatisTest` 는 마이그레이션을 먼저 적용한 스키마 위에서 매퍼를 실행한다.** 마이그레이션 파일이 스키마의 유일한 원천이 되고, 매퍼 테스트가 그 원천과 SQL 을 대조하는 장치가 된다.

함정은 기본값에 있다. 공식 문서에 따르면 `@MybatisTest` 는 기본적으로 **인메모리 임베디드 DB 를 구성한다**([MyBatis-Spring-Boot-Starter-Test](https://mybatis.org/spring-boot-starter/mybatis-spring-boot-test-autoconfigure/)). MyBatis 를 쓰는 이유 자체가 벤더 SQL(힌트, `MERGE`, `ON CONFLICT`, 윈도 함수 등)을 그대로 쓰기 위해서인 경우가 많은데, 그러면 두 갈래로 실패한다.

- 벤더 문법으로 쓴 마이그레이션이 H2 에서 **아예 안 돌거나**,
- H2 에서는 통과했는데 **운영 DB 에서 깨진다.**

같은 문서가 실제 DB 를 쓰는 방법도 알려 준다. `@AutoConfigureTestDatabase(replace = Replace.NONE)` 다. 위 목록에 `ServiceConnectionAutoConfiguration` 이 들어 있으니 Testcontainers 컨테이너를 `@ServiceConnection` 으로 붙일 수 있다.

```java
@MybatisTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class CityMapperTest {

  @Container
  @ServiceConnection
  static PostgreSQLContainer<?> db = new PostgreSQLContainer<>("postgres:17");

  @Autowired CityMapper cityMapper;

  @Test
  void 마이그레이션된_스키마와_매퍼가_맞는다() {
    // db/migration 의 V*.sql 이 먼저 적용된 뒤 실행된다
    assertThat(cityMapper.findByState("CA")).isNotNull();
  }
}
```

*추론:* 이 테스트는 **해당 매퍼 문장을 실제로 실행했을 때만** 어긋남을 잡는다. 테스트가 없는 매퍼 문장은 여전히 운영에서 처음 터진다. "매퍼 문장 하나당 최소 한 번은 실행"을 커버리지 기준으로 두는 이유가 여기에 있다.

## 5. 그럼 Flyway 와 Liquibase 중 무엇을 — MyBatis 쪽에서 보는 기준 하나

두 도구의 일반적인 비교는 위에 링크한 글들로 넘긴다. MyBatis 관점에서 더할 기준은 하나다. **매퍼와 마이그레이션을 같은 언어로 쓰는가.**

- MyBatis 를 고른 팀은 이미 SQL 을 직접 쓴다. Flyway 의 기본 형태는 `V1__…sql` 같은 순수 SQL 파일이라([Spring Boot 문서](https://docs.spring.io/spring-boot/how-to/data-initialization.html)), 매퍼에서 쓰는 방언과 마이그레이션에서 쓰는 방언이 **한 벌**이다. 리뷰어가 두 파일을 같은 눈으로 읽는다.
- Liquibase 는 변경을 changeset 으로 기술하고 DB 별 SQL 을 도구가 만들어 낸다. 대상 DB 가 여럿일 때 이 추상화가 이점이 된다([멀티DB 글](/2026/10/26/liquibase-vs-flyway-mssql-mysql-oracle/)). *추론:* 하지만 매퍼 SQL 은 여전히 DB 별로 직접 써야 하므로, MyBatis 에서는 이 이점이 **스키마 쪽에서만** 생긴다. 매퍼는 MyBatis 의 `databaseId` 로 따로 갈라야 한다.

어느 쪽을 고르든 Spring Boot 문서의 원칙은 같다. **스키마를 만드는 메커니즘은 하나만.**

## 6. 요약

| 빈자리 | 누가 메우나 | 그래도 새는 곳 |
|---|---|---|
| 스키마를 만드는 주체 | Flyway 또는 Liquibase (Boot 자동 실행). MyBatis Migrations 는 별도 단계 | 두 번째 DataSource — `@Primary` 만 기본 대상 |
| 기동 순서 | 스타터 2.3.0+ 감지기가 `SqlSessionTemplate` 을 마이그레이션 뒤로 | `SqlSessionFactory` 로 직접 세션을 여는 초기화 코드 |
| 매퍼 ↔ 스키마 일치 | `@MybatisTest` + 마이그레이션 자동 적용 | 기본 인메모리 DB(→ `replace = NONE` + Testcontainers), 실행되지 않은 매퍼 문장 |

MyBatis 가 스키마를 모른다는 건 단점이라기보다 **역할 분담**이다. 대신 그 분담의 이음새, 즉 기동 순서와 테스트 DB 와 DataSource 개수를 사람이 알고 있어야 한다.

## References

- Spring Boot, *How-to: Database Initialization* — `ddl-auto` 값, Flyway·Liquibase 두 도구 지원, 단일 메커니즘 권고, `schema.sql` 병용 지원 제거 예정, `@Primary`/`@FlywayDataSource` — <https://docs.spring.io/spring-boot/how-to/data-initialization.html>
- MyBatis, *MyBatis 3 Introduction* — <https://mybatis.org/mybatis-3/>
- MyBatis, *MyBatis Migrations — Introduction* — <https://mybatis.org/migrations/>
- MyBatis, *Migrations: the 'new' command* (`-- //@UNDO`, `--idpattern` 3.2.1+) — <https://mybatis.org/migrations/new.html>
- MyBatis, *Migrations: the 'status' command* — <https://mybatis.org/migrations/status.html>
- mybatis/spring-boot-starter, Issue #537 *Liquibase/Flyway autoconfiguration order* (2.3.0 에서 해결, Boot 2.5+) — <https://github.com/mybatis/spring-boot-starter/issues/537>
- mybatis/spring-boot-starter, `MybatisDependsOnDatabaseInitializationDetector` 소스 — <https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/xref/org/mybatis/spring/boot/autoconfigure/MybatisDependsOnDatabaseInitializationDetector.html>
- mybatis/spring-boot-starter, `MybatisAutoConfigurationTest` (depends-on 계약 테스트) — <https://github.com/mybatis/spring-boot-starter/blob/master/mybatis-spring-boot-autoconfigure/src/test/java/org/mybatis/spring/boot/autoconfigure/MybatisAutoConfigurationTest.java>
- mybatis/spring-boot-starter, `AutoConfigureMybatis.imports` — <https://github.com/mybatis/spring-boot-starter/blob/master/mybatis-spring-boot-test-autoconfigure/src/main/resources/META-INF/spring/org.mybatis.spring.boot.test.autoconfigure.AutoConfigureMybatis.imports>
- MyBatis, *MyBatis-Spring-Boot-Starter-Test* (`@MybatisTest` 기본 인메모리 DB, `replace = NONE`) — <https://mybatis.org/spring-boot-starter/mybatis-spring-boot-test-autoconfigure/>
