---
layout: post
title: "스프링부트 × 자바 버전 호환 — Boot 2/3/4 의 최소 자바, javax→jakarta, 가상 스레드, GraalVM 네이티브"
date: 2026-10-12 00:20:42 +0900
categories: [java]
tags: [java, spring-boot, spring-framework, compatibility, java17, java21, java25, jakarta-ee, javax, virtual-threads, graalvm, native-image, migration]
---

자바·코틀린 20편 시리즈의 **자바 마지막 글(J10)** 입니다. "스프링 부트 X 를 쓰려면 자바 몇이 필요한가", "자바 Y 로 올리면 부트는 어디까지 따라가나", "`javax` 가 `jakarta` 로 바뀐 건 어느 버전부터인가", "가상 스레드는 언제부터 켤 수 있나", "네이티브 이미지는 어떤 GraalVM 이 필요한가" 를 **공식 문서와 릴리스 노트로 확인한 사실만** 모아 정리합니다.

이 글의 모든 버전 수치는 docs.spring.io 의 System Requirements, spring-projects GitHub 위키의 릴리스 노트·마이그레이션 가이드, spring.io 공식 블로그 릴리스 공지에서 직접 확인했습니다. 코틀린 쪽 버전 호환은 짝이 되는 [K10 — 코틀린 × 스프링부트](https://myoungsoo7.github.io/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/) 에서 다룹니다.

---

## 1. 한눈에 보는 호환표

### 1.1 스프링 부트 세대별

| 스프링 부트 | GA | 최소 자바 | 스프링 프레임워크 | EE 네임스페이스 / 기준 | 서블릿 |
|---|---|---|---|---|---|
| **2.x** | 2.0: 2018-03-01 | **Java 8** | 5.x | `javax` / Java EE 7–8 (SF 5.3 기준) | 2.7: 3.1·4.0 컨테이너 |
| **3.x** | 3.0: 2022-11-24 | **Java 17** | 6.x | `jakarta` / **EE 9 기준, EE 10 호환** | 3.0: 5.0+ 컨테이너, 임베디드 6.0 |
| **4.x** | 4.0: 2025-11-20 | **Java 17** (Java 25 1급 지원) | 7.x | `jakarta` / **EE 11** | **6.1** |

근거:

- 2.0: "Spring Boot 2.0 requires Java 8 as a minimum version." / "builds on and requires Spring Framework 5" ([Spring Boot 2.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.0-Release-Notes)). GA 공지: "A Java 8 baseline, and Java 9 support" ([Spring Boot 2.0 goes GA](https://spring.io/blog/2018/03/01/spring-boot-2-0-goes-ga/))
- 3.0: "Spring Boot 3.0 requires Java 17 as a minimum version." / "builds on and requires Spring Framework 6" / "Wherever possible, Jakarta EE 10 compatible dependencies have been chosen." ([Spring Boot 3.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Release-Notes)). GA 공지는 "Java 17 baseline", "Jakarta EE 10 with an EE 9 baseline" 이라고 요약합니다 ([Spring Boot 3.0 Goes GA](https://spring.io/blog/2022/11/24/spring-boot-3-0-goes-ga/)).
- 4.0: "Spring Boot 4.0 requires Java 17 or later. Using the latest LTS release of Java is encouraged." / "Spring Boot 4 is based on Jakarta EE 11 and requires a Servlet 6.1 baseline." ([Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)). GA 공지: "First class support for Java 25 (whilst retaining Java 17 compatibility)" ([Spring Boot 4.0.0 available now](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)).

### 1.2 대표 패치 버전의 "최소 ~ 최대 호환 자바"

System Requirements 페이지는 "requires at least Java N and is compatible up to and including Java M" 형식으로 **상한**도 밝힙니다. 아래는 2026-10 현재 docs.spring.io 에 게시된 각 라인의 최신 문서 기준입니다.

| 문서 버전 | 최소 자바 | 최대 호환 자바 | 스프링 프레임워크 | 임베디드 컨테이너 | GraalVM (네이티브) |
|---|---|---|---|---|---|
| [2.7.18](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/getting-started.html) | 8 | 21 | 5.3.31+ | Tomcat 9.0, Jetty 9.4/10.0, Undertow 2.0 | — |
| [3.0.13](https://docs.spring.io/spring-boot/docs/3.0.x/reference/html/getting-started.html) | 17 | 21 | 6.0.14+ | Tomcat 10.1, Jetty 11.0, Undertow 2.3 | 22.3+ |
| [3.5.16](https://docs.spring.io/spring-boot/3.5/system-requirements.html) | 17 | 25 | 6.2.19+ | Tomcat 10.1(10.1.25+), Jetty 12.0, Undertow 2.3 | 22.3+ |
| [4.0.8](https://docs.spring.io/spring-boot/4.0/system-requirements.html) | 17 | 26 | 7.0.9+ | Tomcat 11.0, Jetty 12.1 | 25 |
| [4.1.1](https://docs.spring.io/spring-boot/system-requirements.html) | 17 | 26 | 7.0.9+ | Tomcat 11.0, Jetty 12.1 | 25 |

**읽는 법**:
- "최소 자바" 는 **실행·컴파일에 필요한 하한**입니다. 이 아래에서는 부트 자체의 클래스 파일을 읽지 못합니다.
- "최대 호환 자바" 는 **그 패치 버전이 검증된 상한**입니다. 같은 마이너 라인이라도 패치가 올라가며 상한이 늘어나는 경우가 있으므로(예: 3.0 라인의 최신 문서는 Java 21 까지), 새 JDK 로 올릴 때는 **사용 중인 패치 버전의 문서**를 확인하세요.

### 1.3 스프링 프레임워크 기준

스프링 프레임워크 위키의 버전표 ([Spring Framework Versions](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions)):

| 프레임워크 | JDK 범위 | Java/Jakarta EE | 비고 |
|---|---|---|---|
| 7.0.x | JDK 17–25+ | Jakarta EE 11–12 | 운영에는 JDK 25 이상 권장 |
| 6.2.x | JDK 17–25 | Jakarta EE 9–10 | OSS 지원 2026-06 종료 |
| 6.1.x | JDK 17–21 | Jakarta EE 9–10 | |
| 6.0.x | JDK 17–21 | Jakarta EE 9–10 | |
| 5.3.x | JDK 8–21 | Java EE 7–8 | OSS 지원 2024-08 종료 |

같은 문서는 스프링이 JDK 의 LTS 릴리스(현재 JDK 17, 21, 25)를 완전히 테스트·지원한다고 밝힙니다. 7.x 는 EE 11 기준(Servlet 6.1, JPA 3.2, Bean Validation 3.1)입니다.

**실무적 함의**: 스프링 부트 3.5 는 스프링 프레임워크 6.2 위에 있습니다. 위 표대로 6.2.x 의 OSS 지원이 2026-06 에 끝났으므로, 2026-10 현재 **오픈소스 지원을 받으며 운영하려면 부트 4.x(프레임워크 7.x) 로의 이전**을 계획해야 합니다. 부트 라인별 정확한 지원 종료일은 spring.io 의 프로젝트 지원 페이지에서 확인하세요(이 글에서는 프레임워크 위키에 명시된 날짜만 인용했습니다).

---

## 2. Boot 2 → 3: 자바 17 과 `javax` → `jakarta`

### 2.1 무엇이 바뀌었나

부트 3.0 은 2.0 이후 4.5 년 만의 메이저 개정이었습니다 ([Spring Boot 3.0 Goes GA](https://spring.io/blog/2022/11/24/spring-boot-3-0-goes-ga/)). 핵심은 두 가지입니다.

1. **Java 17 기준선** — Java 8/11 로는 부트 3 을 쓸 수 없습니다.
2. **Java EE → Jakarta EE** — 스프링 프레임워크 6.0 은 최소 요구사항을 "Java 17+ 와 Jakarta EE 9+" 로 올렸고, `javax` 대신 `jakarta` 네임스페이스를 씁니다 ([Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)).

### 2.2 코드 — import 가 바뀐다

```java
// Boot 2.x
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.servlet.http.HttpServletRequest;
import javax.validation.constraints.NotBlank;
import javax.annotation.PostConstruct;

// Boot 3.x / 4.x
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.constraints.NotBlank;
import jakarta.annotation.PostConstruct;
```

스프링 프레임워크 6.0 릴리스 노트는 JSR-330 `@Inject` 가 `jakarta.inject` 로, JSR-250 `@PostConstruct`/`@PreDestroy` 가 `jakarta.annotation` 으로 옮겨졌다고 명시합니다.

**바뀌지 않는 것**: `javax.sql`(예: `DataSource`), `javax.crypto` 는 JDK 자체의 패키지라 그대로입니다 ([Spring Boot 3.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide)). 일괄 치환(`sed s/javax/jakarta/`)을 하면 이것들까지 깨집니다.

### 2.3 공식 마이그레이션 절차

[Spring Boot 3.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide) 가 제시하는 순서:

1. **먼저 최신 2.7.x 로 올린다.** 2.7 은 Java 8 에서 21 까지 호환되므로([2.7.18 문서](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/getting-started.html)), **자바 17 업그레이드를 부트 2.7 위에서 먼저** 끝낼 수 있습니다. 런타임 문제와 프레임워크 문제를 분리하는 핵심 요령입니다.
2. **`javax` → `jakarta` 자동 변환 도구**: 가이드는 OpenRewrite 레시피, Spring Boot Migrator, IntelliJ IDEA 의 지원을 언급합니다.
3. **`spring-boot-properties-migrator`**: 시작 시 이름이 바뀌거나 제거된 설정 프로퍼티를 찾아 임시로 이전해 줍니다. 마이그레이션이 끝나면 제거합니다.
4. **동작 변경 확인**: 대표적으로 스프링 프레임워크 6.0 에서 **후행 슬래시 매칭이 기본 비활성화**되어 `/some/greeting/` 요청이 `/some/greeting` 엔드포인트에 더 이상 매칭되지 않습니다.
5. **의존성 메이저 업**: 부트 3.0 은 Hibernate 6.1, Flyway 9.0, Micrometer 1.10 을 포함하며 각자 마이그레이션 사항이 있습니다.

### 2.4 함정

1. **서드파티 라이브러리의 `javax` 의존**: 내 코드는 `jakarta` 로 바꿨는데, 사용하는 라이브러리가 여전히 `javax.servlet.Filter` 를 구현하고 있으면 런타임에 클래스를 찾지 못합니다. 라이브러리의 Jakarta 대응 버전(대개 별도 artifact 또는 메이저 버전)을 확인하세요.
2. **Hibernate 6 의 동작 변화**: 네임스페이스뿐 아니라 쿼리 해석·타입 매핑이 바뀝니다. 통합 테스트로 확인하세요.
3. **`-parameters`**: 스프링 6.0 에서 `LocalVariableTableParameterNameDiscoverer` 가 deprecated 되고 `-parameters` 컴파일이 권장됩니다(같은 릴리스 노트). 이름 생략한 `@PathVariable`/`@RequestParam` 이 깨질 수 있습니다. 원리는 [J9](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 참고.
4. **제거된 기능**: 프레임워크 6.0 에서 RPC 스타일 원격 호출(Hessian, HTTP Invoker, JMS Invoker, JAX-WS), EJB 접근, Joda-Time 지원, Ehcache 2.x 통합이 제거되었습니다.

---

## 3. Boot 3.x 안에서의 변화 — 가상 스레드는 3.2 부터

### 3.1 가상 스레드 지원의 시작

| 항목 | 버전 | 근거 |
|---|---|---|
| JDK 가상 스레드 정식 | JDK 21 | [JEP 444](https://openjdk.org/jeps/444) |
| 스프링 프레임워크 지원 (`VirtualThreadTaskExecutor`, `SimpleAsyncTaskExecutor` 가상 스레드 모드) | 6.1 | [Spring Framework 6.1 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes) |
| 스프링 부트 `spring.threads.virtual.enabled` | **3.2** (2023-11-23 GA) | [Spring Boot 3.2 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes), [3.2.0 공지](https://spring.io/blog/2023/11/23/spring-boot-3-2-0-available-now/) |

3.2 릴리스 노트: "가상 스레드를 쓰려면 Java 21 에서 실행하고 `spring.threads.virtual.enabled` 를 `true` 로 설정해야 한다."

```properties
# Spring Boot 3.2+ / Java 21+
spring.threads.virtual.enabled=true
# 가상 스레드는 데몬 스레드이므로, 스케줄러만으로 JVM 을 살려 두는 앱이라면
spring.main.keep-alive=true
```

켜면 톰캣·제티 요청 처리, `@Async`·MVC 비동기용 태스크 실행기(`SimpleAsyncTaskExecutor`), 스케줄러(`SimpleAsyncTaskScheduler`), RabbitMQ·Kafka 리스너 등이 가상 스레드를 씁니다(3.2 릴리스 노트).

### 3.2 현재 문서의 권장 — Java 24 이상

현재 스프링 부트 레퍼런스는 "가상 스레드는 Java 21 이상이 필요하다. **최상의 경험을 위해 Java 24 이상을 강력히 권장한다**" 고 적고 있습니다 ([Spring Boot — SpringApplication](https://docs.spring.io/spring-boot/reference/features/spring-application.html)). 이유는 JDK 24 의 [JEP 491](https://openjdk.org/jeps/491) 이 `synchronized` 로 인한 pinning 을 제거했기 때문입니다. 같은 문서는 가상 스레드를 켜면 **스레드 풀 설정 프로퍼티가 효과가 없어진다**는 점도 경고합니다.

LTS 기준으로 정리하면:

| 조합 | 가상 스레드 |
|---|---|
| Boot 3.0~3.1 + Java 21 | `spring.threads.virtual.enabled` 없음(3.2 에서 추가) — 직접 실행기 구성 필요 |
| Boot 3.2+ + Java 17 | 사용 불가 (JDK 에 없음) |
| Boot 3.2+ + Java 21 | 가능. `synchronized` pinning 주의 |
| Boot 3.2+/4.x + **Java 25** | 가능. pinning 문제 대부분 해소 — **권장 조합** |

자세한 동작과 함정은 [J7 — 자바 동시성의 진화](https://myoungsoo7.github.io/2026/10/12/java-concurrency-thread-to-virtual-threads/) 에서 다룹니다.

### 3.3 함께 들어온 것들 (3.2)

3.2 GA 공지가 밝힌 주요 기능: 가상 스레드, JVM Checkpoint Restore(Project CRaC) 초기 지원, SSL 번들 재로딩, `RestClient`, `JdbcClient`, Jetty 12, Spring for Apache Pulsar ([Spring Boot 3.2.0 available now](https://spring.io/blog/2023/11/23/spring-boot-3-2-0-available-now/)). `RestClient`·`JdbcClient` 는 스프링 프레임워크 6.1 의 기능입니다.

---

## 4. Boot 3 → 4: Jakarta EE 11, 모듈화, Jackson 3

### 4.1 무엇이 바뀌었나

[Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) 기준:

| 항목 | 내용 |
|---|---|
| 자바 | **17 이상** (최신 LTS 권장). 부트 3 과 하한이 같다 |
| Jakarta EE | **EE 11**, 서블릿 **6.1** 기준 |
| Undertow | **지원 중단** — 서블릿 6.1 과 아직 호환되지 않음 |
| Jackson | **Jackson 3 기본** (그룹 ID `tools.jackson`), Jackson 2 는 deprecated 형태로 제공 |
| 스타터 | 작고 집중된 모듈로 **모듈화**. 각 스타터에 테스트 스타터 짝이 있음 |
| 널 안전 | **JSpecify** 널 애노테이션 추가 — 널 체커나 코틀린을 쓰면 컴파일 실패가 생길 수 있음 |
| 코틀린 | 2.2 이상 |
| GraalVM | 네이티브 이미지는 **v25 이상** |

GA 공지가 꼽은 하이라이트는 코드베이스 완전 모듈화, JSpecify 기반 포트폴리오 전반의 널 안전 개선, Java 25 1급 지원(Java 17 호환 유지), API 버저닝과 HTTP Service Client 지원입니다 ([Spring Boot 4.0.0 available now](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)).

### 4.2 코드 — 무엇을 고치게 되나

**(1) Jackson 3 패키지**

```java
// Boot 3.x (Jackson 2)
import com.fasterxml.jackson.databind.ObjectMapper;

// Boot 4.x (Jackson 3)
import tools.jackson.databind.ObjectMapper;
```

마이그레이션 가이드는 그룹 ID 변경(`com.fasterxml.jackson` → `tools.jackson`)과 함께 부트 쪽 클래스 이름 변경도 명시합니다. `@JsonComponent` → `@JacksonComponent`, `JsonObjectSerializer` → `ObjectValueSerializer`.

> 주의: 위 import 경로는 그룹 ID 변경에 맞춘 예시입니다. Jackson 3 의 세부 API 변경(예외 타입, 빌더 등)은 Jackson 프로젝트의 3.0 릴리스 노트로 따로 확인하세요. 이 글에서는 부트 마이그레이션 가이드가 밝힌 내용만 다룹니다.

**(2) 스타터 모듈화** — 쓰는 기술의 스타터를 명시

```kotlin
// build.gradle.kts (Boot 4.x)
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-webmvc")   // 기존 spring-boot-starter-web 대체
    implementation("org.springframework.boot:spring-boot-starter-flyway")   // 가이드의 예: Flyway 전용 스타터
}
```

가이드 기준으로 `spring-boot-starter-web` 은 `spring-boot-starter-webmvc` 로 대체되었고, 여러 스타터 이름이 deprecated 되며 새 이름이 생겼습니다. "각 스타터에 테스트 스타터 짝이 있다" 고 하므로 테스트 쪽 스타터도 같은 규칙으로 맞춥니다. 한 번에 옮기기 어렵다면 모든 인프라 모듈을 포함하는 **`spring-boot-starter-classic`, `spring-boot-starter-test-classic`** 으로 먼저 올리고 점진적으로 모듈 단위 스타터로 옮기는 경로도 제공됩니다(가이드는 결국 모듈 방식으로 옮길 것을 권합니다). 정확한 이름 대응표는 마이그레이션 가이드의 표를 확인하세요.

**(3) JSpecify 널 애노테이션**

```java
// 액추에이터 엔드포인트 파라미터
import org.jspecify.annotations.Nullable;   // javax.annotation.Nonnull 지원은 제거됨
```

가이드는 액추에이터 엔드포인트 파라미터에서 `javax.annotations.NonNull` 지원이 제거되었고 `org.jspecify.annotations.Nullable` 을 쓰라고 안내합니다. 그리고 "빌드에서 널 체커를 쓰거나 코틀린을 쓰면 컴파일 실패가 생길 수 있다" 고 경고합니다. 코틀린 쪽 영향은 [K10](https://myoungsoo7.github.io/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/) 에서 다룹니다.

### 4.3 서블릿 컨테이너

| 부트 | 기본 제공 임베디드 컨테이너 (문서 기준) |
|---|---|
| 3.5.16 | Tomcat 10.1, Jetty 12.0, Undertow 2.3 (모두 Servlet 6.0) |
| 4.0.8 / 4.1.1 | Tomcat 11.0, Jetty 12.1 (모두 Servlet 6.1) |

Undertow 를 쓰던 서비스는 부트 4 로 가면서 **톰캣이나 제티로 바꿔야** 합니다.

### 4.4 함정

1. **"자바 하한이 같으니 쉬운 업그레이드" 가 아닙니다.** 자바는 17 그대로지만 EE 11, Jackson 3, 스타터 구조, 널 애노테이션이 동시에 바뀝니다. 부트 4.0 공지 자체가 "업그레이드가 평소보다 더 손이 갈 수 있다" 며 마이그레이션 가이드를 먼저 보라고 권합니다.
2. **Jackson 2 에 의존하는 서드파티**: 라이브러리가 `com.fasterxml.jackson` 의 `ObjectMapper` 를 주입받는다면, 부트가 구성한 Jackson 3 `ObjectMapper` 와 타입이 다릅니다.
3. **GraalVM 버전**: 부트 3.x 는 GraalVM 22.3 이상이면 됐지만, 4.x 는 **25 이상**입니다. 네이티브 빌드 CI 이미지를 같이 올려야 합니다.

부트 4 실전 업그레이드에서 만난 의존성 문제는 이전 글 [Spring Boot 4 의존성 지옥 디버깅](https://myoungsoo7.github.io/2026/05/12/spring-boot-4-dependency-hell-debugging/) 에도 정리해 두었습니다.

---

## 5. GraalVM 네이티브 이미지

### 5.1 버전별 요구사항

| 부트 | GraalVM | Native Build Tools | 근거 |
|---|---|---|---|
| 3.0 | 22.3 이상 | 0.9.17 이상 (3.0.0 시점) | [3.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Release-Notes) |
| 3.5.16 | 22.3 이상 | 0.10.6 | [3.5 System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html) |
| 4.0.8 | 25 | 0.11.5 | [4.0 System Requirements](https://docs.spring.io/spring-boot/4.0/system-requirements.html) |
| 4.1.1 | 25 이상 | 1.1.8 | [System Requirements](https://docs.spring.io/spring-boot/system-requirements.html) |

부트 3.0 GA 공지는 네이티브 이미지 지원이 실험적인 Spring Native 프로젝트를 대체한다고 밝힙니다 ([Spring Boot 3.0 Goes GA](https://spring.io/blog/2022/11/24/spring-boot-3-0-goes-ga/)). **부트 2.x 에는 공식 네이티브 이미지 지원이 없습니다.**

### 5.2 제약 — 닫힌 세계

부트 문서는 네이티브 이미지가 빌드 시점 정적 분석과 **닫힌 세계 가정** 위에서 동작하므로, 클래스패스가 빌드 시점에 고정되고, 빈 정의가 런타임에 바뀔 수 없으며(`@Profile`, `@ConditionalOnProperty` 제약), 리플렉션·리소스·직렬화·동적 프록시는 힌트가 필요하다고 설명합니다 ([Introducing GraalVM Native Images](https://docs.spring.io/spring-boot/reference/packaging/native-image/introducing-graalvm-native-images.html)). 스프링은 이를 위해 빌드 시점 AOT 처리로 빈 정의 코드와 힌트 파일을 생성합니다. 원리는 [J9 의 8장](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 참고.

### 5.3 언제 쓰나

- **쓸 만한 곳**: 시작 시간이 중요한 서버리스/스케일-투-제로, 메모리가 빡빡한 사이드카·CLI.
- **신중할 곳**: 리플렉션을 많이 쓰는 라이브러리, 프로퍼티로 빈 구성이 바뀌는 앱, 빌드 시간이 길어지는 것이 부담인 팀.

---

## 6. 자바 버전에서 출발하는 선택 가이드

### 6.1 "우리 런타임이 자바 N 이다"

| 런타임 자바 | 쓸 수 있는 부트 | 권장 |
|---|---|---|
| 8 / 11 | 2.x 만 | 2.7 로 올리고 자바 17 로 먼저 업그레이드 (2.7 은 21 까지 호환) |
| 17 | 3.x, 4.x | 4.x 이전 계획. 가상 스레드는 불가 |
| 21 | 3.x, 4.x | 3.2+ 에서 가상 스레드 가능 (pinning 주의) |
| 25 | 3.5(상한 25), 4.x | **4.x + 25 가 현재의 기본 조합.** 가상 스레드 권장 환경 |
| 26 | 4.x (4.0.8·4.1.1 문서 기준 상한 26) | 비-LTS(Oracle 로드맵의 LTS 는 8·11·17·21·25). 운영보다는 검증용 |

### 6.2 "부트 X 로 가고 싶다"

| 목표 | 선행 조건 |
|---|---|
| 2.7 → 3.x | 자바 17, `javax`→`jakarta`, 서드파티 Jakarta 대응, Hibernate 6 |
| 3.x → 4.x | Undertow 제거, Jackson 3, 스타터 정리, JSpecify 대응, (네이티브라면) GraalVM 25, (코틀린이라면) 2.2+ |
| 가상 스레드 | 부트 3.2+, 자바 21+ (권장 24+ → LTS 로는 25) |

---

## 7. 업그레이드 체크리스트

**자바 업그레이드 (부트는 그대로)**
- [ ] 현재 부트 패치 버전의 System Requirements 에서 "최대 호환 자바" 확인
- [ ] 빌드 도구(Gradle/Maven)와 플러그인, 바이트코드 조작 라이브러리가 새 JDK 를 지원하는지 확인
- [ ] JDK 17 이상: JEP 403 강한 캡슐화로 깨지는 라이브러리 확인 ([J8](https://myoungsoo7.github.io/2026/10/12/java-modern-syntax-by-version/))
- [ ] JDK 18 이상: 기본 문자셋 UTF-8 ([JEP 400](https://openjdk.org/jeps/400))

**부트 2 → 3**
- [ ] 2.7.x 최신으로 먼저
- [ ] 자바 17
- [ ] OpenRewrite 등으로 `javax`→`jakarta` (단, `javax.sql`·`javax.crypto` 제외)
- [ ] `spring-boot-properties-migrator` 로 설정 키 점검 후 제거
- [ ] 후행 슬래시 매칭, Hibernate 6.1 변경 확인
- [ ] `-parameters` 컴파일

**부트 3 → 4**
- [ ] 3.5.x 최신으로 먼저
- [ ] Undertow → Tomcat/Jetty
- [ ] Jackson 3 (`tools.jackson`), `@JsonComponent`→`@JacksonComponent`
- [ ] 모듈화된 스타터와 테스트 스타터 반영
- [ ] JSpecify 널 애노테이션으로 인한 컴파일 에러(특히 코틀린) 정리
- [ ] 네이티브 이미지 사용 시 GraalVM 25

---

## 8. 정리

- **최소 자바**: 부트 2.x = **8**, 부트 3.x = **17**, 부트 4.x = **17** (4.x 는 Java 25 1급 지원).
- **EE 네임스페이스**: 부트 2 = `javax`(Java EE), 부트 3 = `jakarta`(**EE 9 기준·EE 10 호환**), 부트 4 = `jakarta`(**EE 11**, 서블릿 6.1).
- **가상 스레드**: JDK 21 정식, 스프링 프레임워크 6.1, **스프링 부트 3.2** 의 `spring.threads.virtual.enabled`. 현재 문서는 Java 24+ 를 강력히 권장.
- **GraalVM 네이티브**: 부트 **3.0** 부터 공식 지원(GraalVM 22.3+), 부트 **4.x 는 GraalVM 25** 필요.
- **지원 수명**: 스프링 프레임워크 6.2(부트 3.5 의 기반)의 OSS 지원은 2026-06 에 끝났습니다. 4.x 이전을 계획할 시점입니다.

---

## References

- [Spring Boot 2.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.0-Release-Notes) — spring-projects wiki
- [Spring Boot 3.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Release-Notes) — spring-projects wiki
- [Spring Boot 3.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide) — spring-projects wiki
- [Spring Boot 3.2 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes) — spring-projects wiki
- [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes) — spring-projects wiki
- [Spring Boot 4.0 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) — spring-projects wiki
- [Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes) — spring-projects wiki
- [Spring Framework 6.1 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes) — spring-projects wiki
- [Spring Framework Versions](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions) — spring-projects wiki
- [Spring Boot 2.0 goes GA](https://spring.io/blog/2018/03/01/spring-boot-2-0-goes-ga/) — spring.io blog
- [Spring Boot 3.0 Goes GA](https://spring.io/blog/2022/11/24/spring-boot-3-0-goes-ga/) — spring.io blog
- [Spring Boot 3.2.0 available now](https://spring.io/blog/2023/11/23/spring-boot-3-2-0-available-now/) — spring.io blog
- [Spring Boot 4.0.0 available now](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/) — spring.io blog
- System Requirements: [2.7.x](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/getting-started.html), [3.0.x](https://docs.spring.io/spring-boot/docs/3.0.x/reference/html/getting-started.html), [3.5](https://docs.spring.io/spring-boot/3.5/system-requirements.html), [4.0](https://docs.spring.io/spring-boot/4.0/system-requirements.html), [current (4.1)](https://docs.spring.io/spring-boot/system-requirements.html) — docs.spring.io
- [Spring Boot Reference — SpringApplication (Virtual threads)](https://docs.spring.io/spring-boot/reference/features/spring-application.html) — docs.spring.io
- [Spring Boot Reference — Introducing GraalVM Native Images](https://docs.spring.io/spring-boot/reference/packaging/native-image/introducing-graalvm-native-images.html) — docs.spring.io
- [Oracle Java SE Support Roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html) — Oracle
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444), [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491), [JEP 400: UTF-8 by Default](https://openjdk.org/jeps/400) — OpenJDK

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/)
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/)
- J9. [스프링이 자바를 쓰는 방식 — 리플렉션·프록시·DI](/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/)
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/) ← 지금 글

**코틀린**

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/)
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
