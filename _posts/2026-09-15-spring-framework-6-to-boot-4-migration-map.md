---
layout: post
title: "스프링 6에서 스프링부트 4로 — 공식 문서로 그리는 마이그레이션 지도"
date: 2026-09-15 22:09:44 +0900
categories: [backend]
tags: [Spring, Spring-Boot-4, Spring-Framework-7, 마이그레이션, Jakarta-EE-11, Jackson3]
---

스프링부트 4.0 은 2025년 11월 20일 GA 됐다([공식 발표][ga-blog]). 스프링 프레임워크 6 위의 부트 3.x 에서 넘어가려는 팀이 이제 꽤 될 시점이라, 공식 마이그레이션 가이드와 릴리스 노트를 축으로 **무엇이 언제 터지는지** 순서대로 지도를 그려 본다.

이 블로그에는 이미 부트 4 실전 글이 두 편 있다 — [의존성 지옥 디버깅]({% post_url 2026-05-12-spring-boot-4-dependency-hell-debugging %})과 [멀티 프로바이더 AI 서비스 마이그레이션기]({% post_url 2026-05-21-spring-boot-4-migration-multi-provider-ai-sops-secrets %}). 둘 다 사고 현장 기록이었다면, 이 글은 그 사고들이 **어느 지형에서 나는지**를 공식 문서 기준으로 정리하는 쪽이다.

## 0. 출발점: 3.5.x 최신부터

공식 [마이그레이션 가이드][mig-guide]의 첫 문장이 이것이다: **부트 4 로 뛰기 전에 3.5.x 최신 버전으로 먼저 올려라.** 이유는 두 가지다.

- 3.x 에서 deprecated 였던 클래스·메서드·프로퍼티는 4.0 에서 **삭제**됐다. 3.5 최신에서 deprecation 경고를 전부 청소하는 것이 4.0 컴파일 에러를 미리 보는 가장 싼 방법이다.
- 3.5 의 의존성 관리 최신선과 4.0 의 그것을 비교해야 서드파티 영향 범위가 보인다.

3.5 미만(3.3, 3.4)에서 바로 뛰는 건 공식적으로도 비권장이다([Upgrading Spring Boot][upgrading] — 건너뛴 버전의 릴리스 노트도 전부 읽으라고 명시한다).

## 1. 바닥부터 확인: 베이스라인

부트 4 / 프레임워크 7 의 최소 요구사항([프레임워크 7.0 릴리스 노트][fw7-notes], [마이그레이션 가이드][mig-guide]):

| 항목 | 요구 |
| --- | --- |
| Java | **17 이상** (최신 LTS 권장 — 프레임워크는 JDK 25 를 권장 LTS 로 명시) |
| Jakarta EE | **11** — Servlet 6.1 (Tomcat 11 / Jetty 12.1), JPA 3.2 (Hibernate 7.1), Bean Validation 3.1 |
| Kotlin | 2.2 이상 |
| GraalVM native-image | 25 이상 |
| 테스트 | JUnit 6 |

Java 17 이 그대로 바닥이라는 게 눈에 띈다 — 부트 3 에서 이미 17 로 왔다면 JDK 는 안 건드려도 된다. 진짜 벽은 Java 가 아니라 **Servlet 6.1** 이다. 바로 다음 항목.

## 2. 사라진 것들 — Undertow 가 제일 아프다

[마이그레이션 가이드][mig-guide]의 제거 목록:

- **Undertow 임베디드 서버 전체** — Servlet 6.1 을 아직 지원하지 않아서다. Undertow 를 쓰던 앱은 Tomcat 11 이나 Jetty 12.1 로 갈아타는 것 자체가 마이그레이션의 첫 작업이 된다.
- **fully executable jar 런치 스크립트** — `java -jar` 는 그대로 되고, init.d 스타일 자기실행 jar 만 없어졌다.
- **Spring Session Hazelcast / MongoDB** — 부트에서 빠지고 각 벤더 팀 소관으로 이관.
- **Spock 통합** (Groovy 5 미지원), **Pulsar Reactive**.

## 3. 최대 구조 변화: 모듈 쪼개기와 스타터 재편

부트 4 는 큰 jar 몇 개 대신 **작은 모듈 다수**로 재설계됐다. 규약은 일관적이다: 모듈 `spring-boot-<tech>`, 루트 패키지 `org.springframework.boot.<tech>`, 스타터 `spring-boot-starter-<tech>`, 테스트 스타터 `spring-boot-starter-<tech>-test`.

실무에서 걸리는 지점 세 개([마이그레이션 가이드][mig-guide]가 명시하는 함정들):

1. **스타터 없이 서드파티 의존성만 넣어 쓰던 기술.** Flyway·Liquibase 가 대표다 — 이제 `spring-boot-starter-flyway` / `spring-boot-starter-liquibase` 로 바꿔야 한다. 라이브러리 좌표만 두면 자동구성이 안 붙는다.
2. **테스트 스타터 누락.** `spring-security-test` 의 `@WithMockUser` 가 이제 `spring-boot-starter-security-test` 없이는 제대로 동작하지 않는다. "본체는 되는데 테스트만 이상하게 깨진다" 류의 추적 어려운 증상이 여기서 나온다.
3. **웹 클라이언트 스타터 분리.** `RestClient`/`RestTemplate` 는 `spring-boot-starter-restclient`, `WebClient` 는 `spring-boot-starter-webclient` — 명시적으로 선언해야 한다.

우리 집에서 이 지형을 미리 밟은 게 dependabot 사건이었다. 부트 4 의존성에 부트 3용 스타터가 섞인 조합을 dependabot 이 "업그레이드"라고 올렸고, CI 는 통과했는데 조합 자체가 성립 불가였다. 메이저 전환기의 버전 매트릭스는 봇이 아니라 **사람이 dependency management BOM 기준으로** 검산해야 한다.

## 4. 속성 이관은 도구에 맡긴다

이름이 바뀌거나 사라진 설정 프로퍼티는 `spring-boot-properties-migrator` 를 runtime 의존성으로 넣으면 기동 시점에 진단을 찍어 주고, 임시로 옛 키를 새 키로 번역까지 해 준다([마이그레이션 가이드][mig-guide]). **이관이 끝나면 반드시 빼라**는 주의까지가 공식 절차다. 전체 변경 목록은 [설정 변경 로그][config-changelog]에 있다.

## 5. 갈아끼워지는 큰 부품들

[릴리스 노트][boot4-notes]의 의존성 상향 중 앱 코드에 직접 닿는 것들:

- **Jackson 3.0** — 메이저 교체. 직렬화 커스터마이징(모듈 등록, `ObjectMapper` 빈 조작)이 있다면 이 항목만 따로 검토가 필요하다.
- **Hibernate 7.1 / JPA 3.2**, **HikariCP 7.0**, **Liquibase 5.0**, **Flyway 11.11**, **Kafka 4.1**, **Testcontainers 2.0** — 각각 자체 브레이킹 체인지를 가진 메이저·마이너 점프다. 공식 가이드가 "다른 프로젝트의 릴리스 노트도 읽어라"고 별도 절을 둔 이유다.
- 스프링 포트폴리오 전체가 같이 뛴다: Security 7, Data 2025.1, Batch 6, Integration 7, Kafka 4.0, Session 4.0…

## 6. 넘어가면 얻는 것

마이그레이션 비용의 반대편([릴리스 노트][boot4-notes], [프레임워크 7.0 릴리스 노트][fw7-notes]):

- **JSpecify 널 안전성** — 프레임워크 코드베이스 전체가 JSpecify 로 이관됐고, 옛 JSR-305 계열 스프링 널 어노테이션은 deprecated. IDE·컴파일러가 널 계약을 더 정확히 본다.
- **HTTP Service Client 자동구성** — `@HttpExchange` 인터페이스만 선언하면 구현체가 자동으로 생긴다. Feign 류를 스프링 자체 기능으로 대체하는 길.
- **API 버저닝 자동구성** — `spring.mvc.apiversion.*` 프로퍼티로 MVC/WebFlux 버전 협상이 내장됐다.
- **OpenTelemetry 스타터**(`spring-boot-starter-opentelemetry`), **RestTestClient**, virtual thread 통합 개선 등.

## 순서 요약

1. 3.5.x 최신으로 → deprecation 경고 0 만들기
2. 베이스라인 점검: Servlet 6.1 컨테이너(Undertow 면 교체 계획부터), Java 17+, Kotlin 2.2+
3. 부트 4 로 올리고 스타터 재편 반영 — 특히 Flyway/Liquibase 스타터, 테스트 스타터 동반 추가
4. `spring-boot-properties-migrator` 로 속성 이관 → 끝나면 제거
5. Jackson 3·Hibernate 7 등 큰 부품의 자체 마이그레이션 노트 검토
6. 그 다음에야 신기능(JSpecify·HTTP Service Client·API 버저닝) 도입

정직하게 덧붙이면: 이 글은 공식 문서의 지형도이고, 실제로 밟으면 어떤 소리가 나는지는 5월의 [의존성 지옥 글]({% post_url 2026-05-12-spring-boot-4-dependency-hell-debugging %})이 더 생생하다. 지도와 답사기는 같이 봐야 길을 안 잃는다.

---

## References

- Spring 공식 위키 — [Spring Boot 4.0 Migration Guide][mig-guide]
- Spring 공식 위키 — [Spring Boot 4.0 Release Notes][boot4-notes]
- Spring 공식 위키 — [Spring Framework 7.0 Release Notes][fw7-notes]
- Spring 공식 위키 — [Spring Boot 4.0 Configuration Changelog][config-changelog]
- spring.io 공식 블로그 — [Spring Boot 4.0.0 available now][ga-blog] (2025-11-20)
- Spring 공식 문서 — [Upgrading Spring Boot][upgrading]

[mig-guide]: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
[boot4-notes]: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes
[fw7-notes]: https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes
[config-changelog]: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Configuration-Changelog
[ga-blog]: https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/
[upgrading]: https://docs.spring.io/spring-boot/upgrading.html
