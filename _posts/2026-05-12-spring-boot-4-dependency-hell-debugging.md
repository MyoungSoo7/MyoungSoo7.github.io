---
layout: post
title: "Spring Boot 4 의존성 지옥 디버깅 후기 — Spring AI / SpringDoc / classpath leakage"
date: 2026-05-12 22:45:00 +0900
categories: [java, spring-boot, devops, debugging]
tags: [spring-boot-4, spring-ai, springdoc, gradle, classpath, postmortem]
---

K3s 이관 작업 중 Spring Boot 4.0.4 로 마이그레이션된 3 개 프로젝트 (sparta-msa, sns-portfolio, shopping-lowprice) 가 전부 다른 방식으로 실패하는 걸 디버깅한 기록입니다. **사진: 깨끗하게 잘 도는 SB 3 으로 다운그레이드가 정답이었다.**

> 이 글에서 다루는 것
> - SB 4 의 패키지 경로 대규모 재편 (어디가 바뀌었나)
> - 진짜 범인은 transitive deps (Springdoc, Spring AI BOM)
> - `gradle dependencyInsight` 로 transitive 추적
> - "Banner 만 출력 후 무한 hang" 의 진짜 원인 = logback profile mismatch
> - 다운그레이드 매트릭스 — SB 3.4 + Spring AI 1.0 + Spring Cloud 2024.0.0 + Java 21

---

## 1. 증상별 분류 — 3 가지 다른 실패 모드

| 프로젝트 | 빌드 | 런타임 | 진짜 원인 |
|---|---|---|---|
| **sparta-msa** | ✅ 성공 | `ClassNotFoundException: RestClientAutoConfiguration` | SpringDoc 3.0.3 이 SB 4 transitive 끌어들임 |
| **sns-portfolio** | ❌ 컴파일 실패 | - | 코드에 `boot.data.redis.autoconfigure` 직접 import |
| **shopping-lowprice** | ✅ 성공 | Banner 만 출력 후 hang, port bind 안 됨 | logback `<springProfile name="dev">` 만 정의, prod 프로파일이면 appender 0 개 |

## 2. SB 4 의 패키지 경로 재편

Spring Boot 4 는 모듈을 잘게 쪼개면서 패키지 경로가 대거 바뀜:

| SB 3.x 경로 | SB 4 경로 |
|---|---|
| `org.springframework.boot.autoconfigure.web.client.RestClientAutoConfiguration` | `org.springframework.boot.restclient.autoconfigure.RestClientAutoConfiguration` |
| `org.springframework.boot.autoconfigure.data.redis.RedisProperties` | `org.springframework.boot.data.redis.autoconfigure.DataRedisProperties` |
| `org.springframework.boot.autoconfigure.web.servlet.error.ErrorMvcAutoConfiguration` | `org.springframework.boot.webmvc.autoconfigure.error.ErrorMvcAutoConfiguration` |
| `org.springframework.boot.web.error.ErrorPageRegistrar` | (제거됨) |

영향:
- **사용자 코드**가 옛 경로 import 하면 컴파일 실패
- **third-party library** (SpringDoc 등) 가 옛 경로 의존하면 transitive 가 SB 3 jar 끌어옴
- 그 결과 **classpath 에 SB 3 + SB 4 두 버전 동시 존재** → 클래스 로딩 충돌

## 3. sparta-msa — SpringDoc 이 진짜 범인

### 증상
```
APPLICATION FAILED TO START
Caused by: java.lang.ClassNotFoundException:
  org.springframework.boot.autoconfigure.web.client.RestClientAutoConfiguration
  at sun.reflect.annotation.AnnotationParser.parseAnnotations...
  at spring-boot-autoconfigure-4.0.4.jar!/...
```

`(v3.5.5)` 배너인데 stack trace 에 `spring-boot-autoconfigure-4.0.4.jar` 등장. **classpath 에 두 버전 동시 존재.**

### 추적

```bash
$ ./gradlew :product-service:dependencyInsight \
    --dependency org.springframework.boot:spring-boot-autoconfigure \
    --configuration runtimeClasspath
```

핵심 발견:
```
+--- org.springdoc:springdoc-openapi-starter-common:3.0.3 (requested org.springframework.boot:spring-boot-starter:4.0.5)
     \--- org.springdoc:springdoc-openapi-starter-webmvc-api:3.0.3
          \--- org.springdoc:springdoc-openapi-starter-webmvc-ui:3.0.3
               \--- runtimeClasspath
```

**SpringDoc 3.0.3 이 SB 4.0.5 를 transitive 로 요구.** Gradle 이 BOM 으로 다운 리졸브하긴 했지만, fat jar 안에는 SB 4 jar 와 함께 들어있던 클래스가 남음.

### SpringDoc 버전 매트릭스

| SpringDoc | Spring Boot |
|---|---|
| 2.5.x | 3.2-3.3 |
| 2.6.x ~ 2.7.x | 3.3-3.4 |
| **2.8.x** | **3.4-3.5** ← SB 3.x 에 맞는 마지막 |
| 3.0.x | **4.0 전용** |

### 해결

```diff
- implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:3.0.3'
+ implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:2.8.9'
```

배포 성공.

## 4. sns-portfolio — 사용자 코드가 SB 4 import 직접 참조

### 증상

```
/app/src/main/java/lms/snsportfolio/configuration/RedisConfiguration.java:6:
  error: package org.springframework.boot.data.redis.autoconfigure does not exist
```

사용자 코드가 SB 4 의 새 패키지 경로 `boot.data.redis.autoconfigure` 를 import. SB 3 으로 다운그레이드하니 클래스 없음.

### 코드

```java
// SB 4 시절 코드
import org.springframework.boot.data.redis.autoconfigure.DataRedisProperties;

@Configuration
public class RedisConfiguration {
    private final DataRedisProperties redisProperties;

    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        String url = redisProperties.getUrl();   // SB 4 의 새 API
        // ...
    }
}
```

### 해결

`getUrl()` 메서드 자체가 SB 4 에서 추가됐기 때문에 단순 import 만 바꾸면 안 됨. SB 3 의 `RedisProperties` 는 `getHost()`, `getPort()` 등 분리된 API.

```diff
- import org.springframework.boot.data.redis.autoconfigure.DataRedisProperties;
+ import org.springframework.boot.autoconfigure.data.redis.RedisProperties;
+ import org.springframework.data.redis.connection.RedisStandaloneConfiguration;

  @Configuration
  public class RedisConfiguration {
-     private final DataRedisProperties redisProperties;
+     private final RedisProperties redisProperties;

      @Bean
      public RedisConnectionFactory redisConnectionFactory() {
-         RedisURI uri = RedisURI.create(redisProperties.getUrl());
-         RedisConfiguration config = LettuceConnectionFactory.createRedisConfiguration(uri);
+         RedisStandaloneConfiguration config = new RedisStandaloneConfiguration(
+             redisProperties.getHost(), redisProperties.getPort());
+         if (redisProperties.getPassword() != null)
+             config.setPassword(redisProperties.getPassword());
          return new LettuceConnectionFactory(config);
      }
  }
```

## 5. shopping-lowprice — "조용한 hang" 의 진짜 원인

### 증상

```
$ kubectl logs pod
Picked up JAVA_TOOL_OPTIONS: -XX:MaxRAMPercentage=75.0

  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/

 :: Spring Boot ::                (v3.4.5)

10:48:57,265 |-WARN in Logger... - No appenders present in context [default]
                                  for logger [...SpringcoreApplication]

<<< 이후 아무 로그도 안 나옴, port 8080 bind 안 됨 >>>
```

### 진짜 원인 — logback profile mismatch

```xml
<!-- logback-spring.xml -->
<configuration>
    <springProfile name="dev">         ← 여기 dev 만!
        <appender name="CONSOLE">...</appender>
        <appender name="FILE">...</appender>
        <root level="INFO">
            <appender-ref ref="CONSOLE" />
            <appender-ref ref="FILE" />
        </root>
    </springProfile>
</configuration>
```

K3s 차트에서 `SPRING_PROFILES_ACTIVE=prod` 로 띄움 → `<springProfile name="dev">` 매치 안 됨 → **appender 0 개** → 로그가 어디로 안 감 → 그리고 앱 자체는 멀쩡히 떴는데 우리가 못 봤음.

근데 왜 hang 했나? 사실 hang 이 아니었음. 8083 으로 떠 있었음 (chart 가 8080 으로 probe 한 게 문제).

### 해결

```diff
  <configuration>
-     <springProfile name="dev">
          <appender name="CONSOLE">...</appender>
          <root level="INFO">
              <appender-ref ref="CONSOLE" />
          </root>
-     </springProfile>
  </configuration>
```

그리고 chart 의 containerPort `8080 → 8083` (실제 앱이 바인드하는 포트).

### 부수 발견 — FILE 어펜더는 항상 제거

```xml
<appender name="FILE">
    <file>logs/app.log</file>
</appender>
```

K8s 의 보안 컨텍스트 `runAsNonRoot: true, runAsUser: 1000` 환경에서 `/app/logs/` 디렉토리 쓰기 권한 없음 → logback 자체 실패. **K8s 에선 stdout 으로만 로그 보내고 `kubectl logs` 로 보는 게 표준.**

## 6. 호환 매트릭스 (실전 검증)

3 프로젝트 모두 같은 다운그레이드로 통일:

```gradle
plugins {
    id 'org.springframework.boot' version '3.4.5'
    id 'io.spring.dependency-management' version '1.1.7'
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)   // SB 3 LTS
    }
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.cloud:spring-cloud-dependencies:2024.0.0"
        mavenBom "org.springframework.ai:spring-ai-bom:1.0.0"
    }
}

dependencies {
    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:2.8.9'
    // ...
}
```

| 컴포넌트 | 안전한 버전 |
|---|---|
| Spring Boot | 3.4.5 (Spring Cloud 2024.0.0 매칭) |
| Spring AI | 1.0.0 (SB 3.3-3.5 호환) |
| Spring Cloud | 2024.0.0 (Moorgate, SB 3.4 매칭) |
| SpringDoc | 2.8.9 (SB 3.x 마지막) |
| Java | 21 LTS |

## 7. 정리 — Spring Boot 4 시기상조

| Spring Boot 4 의 약속 | 현실 |
|---|---|
| 패키지 모듈화로 깔끔한 구조 | transitive 의존성이 SB 3 jar 끌어들이면 진단 어려움 |
| Java 25 LTS | ecosystem (Spring AI, Spring Cloud, SpringDoc, ...) 아직 따라잡지 못함 |
| 더 빠른 시작 | 다운그레이드 후에도 마이그 비용 vs 이득 불균형 |

**조언**: 2026 중반까지 SB 3.4 + Java 21 로 머무는 게 안전. SB 4 는 ecosystem 정착 후 (2027?) 고려.

특히 Spring AI 사용 프로젝트는 SB 4 절대 금지 — Spring AI 1.x 가 SB 3 전용입니다.

---

## 8. 디버깅 흐름 정리

1. **빌드 실패** → 사용자 코드의 import 경로 확인
2. **빌드 성공 + 런타임 `ClassNotFoundException`** → `gradle dependencyInsight` 로 transitive 추적
3. **배너만 나오고 hang** → logback profile 또는 권한 (file write)
4. **포트 안 됨** → chart 의 containerPort 가 실제 앱 포트와 일치하나

이 4 단계만 체크하면 SB 마이그 trouble 의 90% 는 잡힙니다.
