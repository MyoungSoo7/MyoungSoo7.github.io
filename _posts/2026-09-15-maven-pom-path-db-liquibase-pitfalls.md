---
layout: post
title: "pom.xml 경로·DB 설정과 Liquibase 조합에서 유의할 점 — 경로가 체인지셋의 '이름'이다"
date: 2026-09-15 22:25:00 +0900
categories: [Engineering, Backend]
tags: [Maven, pom.xml, Liquibase, changelog, resource-filtering, credentials]
---

Maven 프로젝트에 Liquibase 를 붙이는 방법은 두 갈래다 — `liquibase-maven-plugin` 으로 빌드/배포 단계에서 돌리거나, Spring Boot 라면 앱 기동 시 자동 실행에 맡기거나. 문제는 **두 경로를 같이 쓰는 순간**부터다. 같은 체인지로그인데 한쪽에서는 이미 실행된 걸로, 다른 쪽에서는 처음 보는 걸로 인식되는 사고가 난다. 원인은 늘 같다. **경로 문자열이 체인지셋 신원(identity)의 일부**이기 때문이다.

이 글은 pom.xml 관점에서 유의점을 세 덩어리로 정리한다: ① 경로 설정 ② 리소스 필터링 ③ DB 접속 정보.

## 1. 경로 — 체인지셋의 신원은 `id + author + 파일경로` 다

Liquibase 는 실행한 체인지셋을 [추적 테이블(DATABASECHANGELOG)](https://docs.liquibase.com/concepts/tracking-tables/tracking-tables.html)에 기록하는데, [체인지셋의 고유 식별자는 `id`·`author`·**체인지로그 파일 경로**의 조합](https://docs.liquibase.com/concepts/changelogs/changeset.html)이다. 여기서 함정: 같은 파일이라도 **부르는 경로가 다르면 다른 체인지셋**이다.

- Maven 플러그인에서 `<changeLogFile>src/main/resources/db/changelog/db.changelog-master.xml</changeLogFile>` 로 실행 → FILENAME 이 `src/main/resources/db/...` 로 기록
- Spring Boot 기동 시 `classpath:db/changelog/db.changelog-master.xml` 로 실행 → FILENAME 이 `db/changelog/...` 로 기록

DB 입장에서 이 둘은 남남이다. 결과는 **같은 DDL 의 이중 실행 시도** — 운 좋으면 "table already exists" 로 배포가 깨지고, 운 나쁘면(멱등한 변경이면) 조용히 두 번 적용된다.

### 대책 둘 중 하나를 처음부터

1. **실행 주체를 하나로 통일한다.** 마이그레이션은 부트 자동 실행에만 맡기고, Maven 플러그인은 `status`·`rollbackSQL` 생성 같은 조회용으로만 쓴다 (반대도 가능 — 플러그인만 쓰고 부트 자동 실행은 끈다).
2. **경로를 신원에서 분리한다.** 체인지로그에 [`logicalFilePath`](https://docs.liquibase.com/concepts/changelogs/attributes/logicalfilepath.html) 를 명시하면 물리 경로가 어떻든 기록되는 이름을 고정할 수 있다. 새 프로젝트라면 처음부터 붙여두는 편이 이식성에서 남는다.

이미 사고가 난 뒤라면(FILENAME 이 두 갈래로 쌓인 상태) — 추적 테이블의 FILENAME 을 한쪽으로 정리하는 수술이 필요해진다. 예방이 압도적으로 싸다.

## 2. 리소스 필터링 — 체인지로그를 필터에 넣지 말 것

pom.xml 에서 `${...}` 치환을 위해 리소스 필터링을 켜는 일은 흔하다:

```xml
<resources>
  <resource>
    <directory>src/main/resources</directory>
    <filtering>true</filtering>  <!-- 여기에 체인지로그가 같이 걸리면 -->
  </resource>
</resources>
```

[Maven 공식 문서의 필터링](https://maven.apache.org/plugins/maven-resources-plugin/examples/filter.html)은 리소스 안의 `${...}` 를 빌드 시점 값으로 치환한다. 체인지로그가 이 대상에 포함되면 두 가지가 어긋난다.

- Liquibase 자체의 [changelog property `${...}` 문법](https://docs.liquibase.com/concepts/changelogs/property-substitution.html)과 충돌한다 — Liquibase 가 런타임에 치환해야 할 자리를 Maven 이 빌드 때 먼저 먹어버리거나, 정의 안 된 프로퍼티라며 이상한 값이 박힌다
- 환경마다 빌드된 체인지로그 내용이 달라지면 **체크섬이 환경마다 달라진다** — "dev 에서는 되는데 prod 에서 checksum 에러" 의 전형적 출처다

대책은 단순하다. **체인지로그 디렉터리를 필터링에서 제외**한다:

```xml
<resource>
  <directory>src/main/resources</directory>
  <filtering>true</filtering>
  <excludes><exclude>db/changelog/**</exclude></excludes>
</resource>
<resource>
  <directory>src/main/resources</directory>
  <filtering>false</filtering>
  <includes><include>db/changelog/**</include></includes>
</resource>
```

## 3. DB 접속 정보 — pom.xml 에 비밀번호를 적는 순간 그건 git 히스토리다

Maven 플러그인은 실행에 url·username·password 가 필요하다. [Liquibase 공식 Maven 문서](https://docs.liquibase.com/tools-integrations/maven/home.html)는 이 값을 pom 의 `<configuration>` 또는 별도 `liquibase.properties` 로 줄 수 있다고 안내한다. 유의점 두 가지.

**첫째, 크리덴셜을 pom.xml 에 평문으로 두지 않는다.** pom 은 커밋되는 파일이고, 한 번 커밋된 비밀번호는 지워도 git 히스토리에 남는다. 선택지는 위에서부터 권장 순:

1. 환경변수/CI 시크릿으로 주입 (`-Dliquibase.password=...` 를 CI 가 공급)
2. `liquibase.properties` 를 환경별 파일로 두고 **`.gitignore`**
3. Maven 자체의 [settings.xml 암호화](https://maven.apache.org/guides/mini/guide-encryption.html) — 단 이건 마스터 키가 같은 머신에 있으므로 "커밋 방지" 용이지 강한 암호화가 아니라는 점을 공식 문서도 전제한다

**둘째, 플러그인의 DB 설정과 애플리케이션의 DB 설정은 별개다.** `spring.datasource.*` 를 바꿔도 플러그인 쪽 `liquibase.properties` 는 옛 DB 를 보고 있을 수 있다 — "마이그레이션은 성공했다는데 앱이 붙는 DB 엔 테이블이 없는" 상황의 정체다. 접속 정보의 **원천을 하나**(예: 환경변수)로 두고 양쪽이 같은 원천을 읽게 만들면 표류가 구조적으로 안 생긴다.

## 체크리스트

| 항목 | 확인 |
| --- | --- |
| 마이그레이션 실행 주체 | 플러그인·부트 중 **하나만** (또는 logicalFilePath 고정) |
| 체인지로그 경로 표기 | 모든 실행 경로에서 동일 문자열인가 |
| 리소스 필터링 | `db/changelog/**` 제외됐는가 |
| 크리덴셜 | pom.xml 평문 금지, 환경변수/시크릿 주입 |
| 플러그인 DB ↔ 앱 DB | 같은 원천에서 읽는가 |

요약하면 이렇다. Liquibase 는 "무엇을 실행했는가" 를 **문자열로** 기억한다. Maven 은 경로·내용·접속 정보를 **빌드 시점에** 주무를 수 있는 도구다. 이 둘을 겹쳐 쓸 때의 유의점은 전부 한 문장으로 줄어든다 — **Maven 이 바꿀 수 있는 것(경로 표기, 파일 내용, 접속 대상)을 Liquibase 의 기억과 어긋나지 않게 고정하라.**

## References

- Liquibase — [Maven integration](https://docs.liquibase.com/tools-integrations/maven/home.html) · [changeset (신원 구성)](https://docs.liquibase.com/concepts/changelogs/changeset.html) · [Tracking tables](https://docs.liquibase.com/concepts/tracking-tables/tracking-tables.html) · [logicalFilePath](https://docs.liquibase.com/concepts/changelogs/attributes/logicalfilepath.html) · [Property substitution](https://docs.liquibase.com/concepts/changelogs/property-substitution.html)
- Maven — [Resource filtering](https://maven.apache.org/plugins/maven-resources-plugin/examples/filter.html) · [Password encryption](https://maven.apache.org/guides/mini/guide-encryption.html)
- Spring Boot — [Data initialization (Liquibase 자동 실행)](https://docs.spring.io/spring-boot/how-to/data-initialization.html)
