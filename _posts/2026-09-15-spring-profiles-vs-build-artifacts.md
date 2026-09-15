---
layout: post
title: "프로파일은 늘리고 산출물은 늘리지 않는다 — 스프링 프로파일과 빌드 결과물의 분리 운영"
date: 2026-09-15 23:17:41 +0900
categories: [Engineering, Spring]
tags: [Spring Boot, 프로파일, Gradle, Maven, 빌드, 12factor, Kubernetes, CDS]
---

"환경이 늘었으니 프로파일을 늘린다" 까지는 대부분 같은 답을 낸다. 문제는 그다음이다 — **프로파일이 늘면 빌드 산출물도 같이 늘어나는가?**

여기서 갈린다. 그리고 갈리는 이유는 취향이 아니라, **"프로파일" 이라는 한 단어가 성격이 완전히 다른 두 개를 가리키기 때문**이다.

Maven 공식 문서는 자기 쪽 프로파일을 이렇게 정의한다.[^mvnprofile]

> They **modify the POM at build time**, and are meant to be used in complementary sets to give equivalent-but-different parameters for a set of target environments ... As such, **profiles can easily lead to differing build results from different members of your team.**

Spring Boot 공식 문서의 프로파일은 정의가 다르다.[^bootprofiles]

> Spring Profiles provide a way to segregate parts of your application configuration and make it be available only in certain environments.

앞의 것은 **빌드 시점에 결과물을 바꾸고**, 뒤의 것은 **런타임에 이미 만들어진 결과물의 일부를 켜고 끈다.** 이름이 같을 뿐 축이 다르다. 이 글은 그 두 축을 분리해 놓고, 각각을 어디까지 늘려야 하는지를 공식 문서만으로 정리한다.

> **범위와 버전.** Spring Boot 인용은 현행 레퍼런스 문서 기준이며, 설정 파일 처리 방식이 크게 바뀐 **2.4** 를 기준선으로 본다(그 이전 동작은 Config Data Migration Guide 로 별도 표기). Maven 인용은 Apache Maven 공식 프로파일 가이드, Gradle 쪽은 Spring Boot Gradle 플러그인 공식 문서다. 특정 버전 번호를 단정한 곳은 문서에 그 번호가 적혀 있는 경우뿐이다.

---

## 1. 산출물을 환경 수만큼 만들면 무엇이 무너지는가

서비스 $S$ 개, 환경 $E$ 개인 조직을 생각하자. 환경별로 굽는 전략과 한 번 굽고 주입하는 전략의 산출물 수는 이렇게 갈린다.

$$N_{\text{env-baked}} = S \times E \qquad\text{vs.}\qquad N_{\text{build-once}} = S$$

숫자만 보면 그냥 빌드 시간 얘기 같다. 실제로 무너지는 건 다른 것이다. **staging 에서 통과한 바이트와 prod 에 올라간 바이트가 서로 다른 파일이 된다.** 테스트가 증명한 대상이 배포 대상이 아니게 된다는 뜻이고, 이건 빌드 비용이 아니라 **검증의 유효성** 문제다.

12-Factor 는 같은 요구를 다른 말로 적는다.[^twelve]

> Apps sometimes store config as constants in the code. This is a violation of twelve-factor, which requires **strict separation of config from code**. Config varies substantially across deploys, code does not.

그리고 이 문서의 리트머스 시험지는 외울 만하다.

> A litmus test for whether an app has all config correctly factored out of the code is whether **the codebase could be made open source at any moment, without compromising any credentials.**

`application-prod.yml` 에 운영 DB 비밀번호를 적어 jar 안에 굽는 순간 이 시험지는 빨간불이다. 그 jar 를 받은 사람은 누구든 `unzip` 한 번으로 운영 크리덴셜을 본다.

Maven 문서는 자기 쪽 프로파일의 이 위험을 "portability" 라는 말로 훨씬 구체적으로 경고한다 — `settings.xml` 에 앱서버 경로를 둔 프로파일 예시를 들고, 동료가 같은 `settings.xml` 없이 빌드하면 **`${appserver.home}` 이 그대로 문자열로 들어가거나 빌드가 깨진다**고 적은 뒤 이렇게 끝맺는다.[^mvnprofile]

> Congratulations, your project is now non-portable.

정리하면 이렇다. **Maven/Gradle 프로파일로 환경 설정을 굽는 것은 "환경마다 다른 산출물" 을 만드는 일이고, 그 순간 산출물의 재현성과 검증 유효성을 둘 다 내놓는다.** 늘려도 되는 건 Spring 프로파일 쪽이다.

---

## 2. 그렇다면 프로파일은 얼마나 늘려도 되는가 — 반론부터 읽자

여기서 "Spring 프로파일은 얼마든지 늘려도 된다" 로 가면 정직하지 않다. 12-Factor 는 **"환경" 이라는 이름의 묶음 자체**를 반대하기 때문이다.[^twelve]

> Sometimes apps batch config into named groups (often called "environments") ... This method does not scale cleanly: as more deploys of the app are created, new environment names are necessary, such as `staging` or `qa`. As the project grows further, developers may add their own special environments like `joes-staging`, resulting in a **combinatorial explosion of config** which makes managing deploys of the app very brittle.
>
> In a twelve-factor app, env vars are granular controls, **each fully orthogonal to other env vars. They are never grouped together as "environments"**

이건 Spring 프로파일을 정면으로 겨눈 비판으로 읽힌다. 실제로 `dev`/`qa`/`staging`/`prod` 에 `joes-local` 이 붙기 시작하는 프로젝트를 본 적이 있다면 이 문장이 무슨 말인지 안다.

Spring Boot 의 화해안은 **"둘 중 하나" 가 아니라 "계층"** 이다. 프로파일은 **구조와 기본값**을 담고, 배포마다 달라지는 **값**은 우선순위가 더 높은 환경변수가 덮어쓴다. 문서가 정의한 우선순위 사슬이 이 화해를 가능하게 한다.[^bootext]

> Spring Boot uses a very particular `PropertySource` order that is designed to allow sensible overriding of values. **Later property sources can override the values defined in earlier ones.**

실무에서 쓰이는 구간만 순서대로 추리면 이렇다.

| 순위 | 소스 |
|---|---|
| 낮음 | 3. Config data (`application.properties` / `.yaml`) |
| ↓ | 5. **OS 환경변수** |
| ↓ | 6. Java 시스템 프로퍼티 (`-D`) |
| ↓ | 10. `SPRING_APPLICATION_JSON` |
| 높음 | 11. **커맨드라인 인자** (`--server.port=9000`) |

그리고 config data 내부는 다시 4단계다.[^bootext]

> 1. Application properties packaged inside your jar
> 2. Profile-specific application properties packaged inside your jar
> 3. Application properties **outside** of your packaged jar
> 4. Profile-specific application properties **outside** of your packaged jar

이 네 줄이 곧 운영 설계도다. **jar 안에는 "어디서나 맞는 기본값" 만 넣고, 배포마다 달라지는 것은 jar 밖(또는 환경변수)에서 덮는다.** 프로파일은 축을 만들고, 값은 바깥에서 온다. 이러면 프로파일 개수가 늘어도 산출물은 하나로 남고, 12-Factor 가 경고한 조합 폭발은 프로파일이 아니라 **배포 단위의 환경변수**로 흡수된다.

참고로 이 "바깥이 이긴다" 는 **2.4 에서 바뀐 규칙**이다. 그전에는 jar 밖 `application.properties` 가 jar 안 `application-{profile}.properties` 를 못 이겼다.[^migration]

> In earlier versions of Spring Boot, an `application.properties` file outside of your jar would not override a `application-<profile>.properties` file inside your jar. **As of Spring Boot 2.4, external file always override packaged files (profile-specific or not).**

2.3 시절 배선을 그대로 들고 올라온 프로젝트라면, 바깥 파일이 갑자기 이기기 시작한 지점이 여기다.

---

## 3. 프로파일 설계 — 공식 문서가 정해 둔 세 가지 제약

### 3.1 축이 여러 개면 프로파일 그룹으로 접는다

문서가 드는 예가 정확히 이 상황이다.[^bootprofiles]

> For example, you might have `proddb` and `prodmq` profiles that you use to enable database and messaging features independently.

```yaml
spring:
  profiles:
    group:
      production:
        - "proddb"
        - "prodmq"
```

> Our application can now be started using `--spring.profiles.active=production` to activate the `production`, `proddb` and `prodmq` profiles in one hit.

핵심은 **직교하는 축(DB·메시징·캐시)을 프로파일 이름에 곱해 넣지 않는 것**이다. `prod-mysql-rabbit` 같은 이름이 생기기 시작하면 이미 곱셈을 하고 있는 것이고, 그룹이 그 곱셈을 덧셈으로 되돌린다.

### 3.2 `active` / `include` / `group` 은 프로파일 고유 문서에 쓸 수 없다

세 프로퍼티 모두 같은 제약을 받는다.[^bootprofiles]

> `spring.profiles.active` and `spring.profiles.default` **can only be used in non-profile-specific documents.** This means they cannot be included in profile specific files or documents activated by `spring.config.activate.on-profile`.

즉 아래는 **무효**다.

```yaml
# 유효
spring:
  profiles:
    active: "prod"
---
# 무효 — on-profile 문서 안에서 active 를 또 켠다
spring:
  config:
    activate:
      on-profile: "prod"
  profiles:
    active: "metrics"
```

왜 막았는지까지 마이그레이션 가이드에 적혀 있다.[^migration]

> The reason we have introduced this restriction is so that **`on-profile` conditions are only evaluated once.** Without this limitation, it would be possible for a `spring.config.activate.on-profile` expression to return a different result depending on when it was evaluated.

"프로파일이 프로파일을 켜는" 재귀를 끊어 평가 순서 의존성을 없앤 것이다. 2.3 이하에서 흔했던 `spring.profiles` + `spring.profiles.include` 조합이 바로 이 금지에 걸리고, 그 대체제가 3.1 의 프로파일 그룹이다.

### 3.3 last-wins — 그리고 `,` 와 `;` 는 다른 문자다

프로파일을 여러 개 켜면 뒤가 이긴다.[^bootext]

> If several profiles are specified, a **last-wins** strategy applies. For example, if profiles `prod,live` are specified by the `spring.profiles.active` property, values in `application-prod.properties` can be overridden by those in `application-live.properties`.

그런데 이 last-wins 는 **location group 단위**로 적용된다. 문서의 예시를 그대로 옮기면, 같은 파일 집합인데 구분자 하나로 결과가 바뀐다.

`spring.config.location=classpath:/cfg/,classpath:/ext/` (쉼표 — `/cfg` 를 전부 처리한 뒤 `/ext`):

1. `/cfg/application-live.properties`
2. `/ext/application-prod.properties`
3. `/ext/application-live.properties`

`spring.config.location=classpath:/cfg/;classpath:/ext/` (세미콜론 — 같은 레벨로 묶음):

1. `/ext/application-prod.properties`
2. `/cfg/application-live.properties`
3. `/ext/application-live.properties`

**최종 승자가 2번과 3번 사이에서 바뀐다.** 설정이 왜 그 값인지 안 맞을 때 이 구분자를 먼저 보는 게 빠르다. 그리고 문서는 진단 도구도 지정해 준다 — 액추에이터의 `env` 와 `configprops` 엔드포인트가 "왜 이 값인지" 를 보여준다.[^bootext] 추측하지 말고 이걸 켜는 편이 낫다.

---

## 4. 쿠버네티스에서는 프로파일보다 마운트가 먼저다

컨테이너 환경이면 "프로파일 파일" 보다 **플랫폼이 주는 값**을 읽는 배선이 먼저다. Spring Boot 는 이 경로를 공식적으로 갖고 있다.

**와일드카드 위치** — 문서가 든 예가 정확히 K8s 다.[^bootext]

> Wildcard locations are particularly useful in an environment such as Kubernetes when there are multiple sources of config properties. ... having a wildcard location of `config/*/`, will result in both files being processed.
>
> **By default, Spring Boot includes `config/*/` in the default search locations.**

즉 `/config/redis/application.properties` 와 `/config/mysql/application.properties` 를 서로 다른 ConfigMap 으로 따로 마운트해도 둘 다 읽힌다. 관심사별로 ConfigMap 을 쪼갤 수 있다는 뜻이다. 단, 제약이 둘 있다 — 와일드카드는 **외부 디렉터리에서만** 동작하고 `classpath:` 에는 못 쓰며, `*` 는 하나만 들어갈 수 있다.[^bootext]

**확장자 없는 파일** — 볼륨 마운트된 파일에 확장자를 못 붙이는 플랫폼을 위해 힌트 문법이 있다.[^bootext]

```properties
spring.config.import=file:/etc/config/myconfig[.yaml]
```

**환경변수 안의 설정 뭉치** — 여러 줄짜리 환경변수 전체를 프로퍼티로 읽는다.[^bootext]

```properties
spring.config.import=env:MY_CONFIGURATION
```

여기에 우선순위 5번(OS 환경변수)과 10번(`SPRING_APPLICATION_JSON`)을 더하면, **jar 를 다시 굽지 않고 배포 단위의 값만 바꾸는 경로가 이미 네 개**다. 환경마다 jar 를 굽는 선택지는 이 중 아무것도 쓰지 않았을 때만 불가피해 보인다.

---

## 5. 그럼 산출물은 왜 여러 개인가 — 축이 다르다

여기까지가 "환경별로 굽지 마라" 였다. 그런데 실제 운영에서 산출물은 하나가 아니다. 다만 그 다양성의 축은 **환경이 아니라 실행 형태**다. 같은 코드에서 나오는 다른 포장이지, 다른 설정이 아니다.

**① 레이어드 jar (기본값).** `bootJar` 가 기본으로 레이어 인덱스를 넣는다.[^gradlepkg]

> By default, the following layers are defined: `dependencies` ... `spring-boot-loader` ... `snapshot-dependencies` ... `application`

왜 이 순서인지도 문서가 밝힌다.[^effimg]

> This layering is designed to separate code based on **how likely it is to change between application builds.** Library code is less likely to change between builds, so it is placed in its own layers to allow tooling to re-use the layers from cache.

즉 **레이어 분리는 설정 분리가 아니라 캐시 히트율 설계**다. 애플리케이션 클래스만 바뀌면 Docker 가 맨 아래 레이어만 새로 쓴다.

**② 추출 실행.** uber jar 를 그대로 돌리는 건 중첩 jar 로딩 비용이 있다.[^efficient]

> loading the classes from nested jars has a small startup cost. Depending on the size of the jar, **running the application from an exploded structure is faster and recommended in production.**

```shell
$ java -Djarmode=tools -jar my-app.jar extract
$ java -jar my-app/my-app.jar
```

다만 문서는 시작 이후에 대해 못박는다 — "**After startup, you should not expect any differences in execution time**". 빨라지는 건 기동이지 처리량이 아니다.

**③ CDS / AOT 캐시.** 기동 시간과 메모리를 더 줄이는 경로다. 문서의 안내는 명확하다.[^cds]

> In Java 24, CDS is succeeded by the AOT Cache via JEP 483. Spring Boot supports both CDS and AOT cache, and it is **recommended that you use the latter if it is available in the JVM version you are using (Java 24+).**

여기엔 운영상 중요한 단서가 붙는다 — 만들어진 아카이브는 "**as long as the application is not updated**" 동안만 유효하다. **캐시 파일과 애플리케이션 아티팩트는 한 몸으로 묶어 배포해야 한다.** 이미지 태그는 새것인데 캐시는 옛날 것인 조합이 가능하고, 그건 이득이 사라지거나 더 나빠지는 쪽이다.

**④ 실행형 war.** 외부 컨테이너 배포와 `java -jar` 를 동시에 지원해야 할 때다.[^gradlepkg]

```groovy
dependencies {
    implementation('org.springframework.boot:spring-boot-starter-webmvc')
    providedRuntime('org.springframework.boot:spring-boot-starter-tomcat-runtime')
}
```

> This ensures that the runtime jars are packaged in the war file's `WEB-INF/lib-provided` directory from where **they will not conflict with the external container's own classes.**

문서는 `compileOnly` 를 쓰지 말라고 이유까지 적는다 — "compileOnly dependencies are not on the test classpath so any **web-based integration tests will fail**".

이 네 가지는 전부 **같은 설정, 다른 포장**이다. 환경 수가 아니라 실행 형태 수만큼만 늘어나고, 대개 그 수는 1 또는 2다.

---

## 6. 실제로 밟는 함정

**`-plain.jar` 가 같이 나온다.** Gradle 플러그인의 기본 동작이다.[^gradlepkg]

> By default, when the `bootJar` or `bootWar` tasks are configured, the `jar` or `war` tasks are configured to use `plain` as the convention for their archive classifier. This ensures that `bootJar` and `jar` ... have different output locations, **allowing both the executable archive and the plain archive to be built at the same time.**

즉 `build/libs/` 에 파일이 **두 개** 있다. Dockerfile 에 `COPY build/libs/*.jar app.jar` 라고 쓰면 두 개가 걸리거나 `-plain.jar` 가 잡히고, 그러면 컨테이너가 매니페스트 문제로 뜨지 않는다. 안 만들려면 문서대로 `jar` 태스크를 끈다.

```groovy
tasks.named("jar") { enabled = false }
```

단 문서의 단서도 같이 지킨다 — "**Do not disable the `jar` task when creating native images.**"

**멀티 문서 YAML 의 순서 규칙이 2.4 에 바뀌었다.**[^migration]

> property sources are now added **in the order that documents are declared.** With Spring Boot 2.3 and earlier, the order that the individual documents were added was based on profile activation order.

`---` 로 나눈 문서 안에서 서로 덮어쓰는 값이 있다면, **이기고 싶은 쪽이 파일에서 아래에 있어야 한다.** 2.3 에서 올라오며 조용히 값이 바뀌는 대표적인 자리다.

**`@Profile` 의 등록 방식 의존.** 문서의 단서가 미묘하다.[^bootprofiles]

> If `@ConfigurationProperties` beans are registered through `@EnableConfigurationProperties` instead of automatic scanning, **the `@Profile` annotation needs to be specified on the `@Configuration` class** that has the `@EnableConfigurationProperties` annotation.

같은 `@Profile` 을 같은 클래스에 붙여도 등록 경로에 따라 먹고 안 먹는다. 스캔이면 클래스에, `@EnableConfigurationProperties` 면 그 설정 클래스에.

**프로파일 이름 규칙.** 문자·숫자와 `-`, `_`, `.`, `+`, `@` 만 되고 시작·끝은 문자나 숫자여야 한다. `spring.profiles.validate=false` 로 풀 수 있지만, 문서가 밝힌 대로 이 제약은 "prevent common parsing issues" 용이다 — 끄는 쪽이 이득인 경우는 드물다.[^bootprofiles]

**없는 위치를 가리키면 뜨지 않는다.**[^bootext]

> By default, when a specified config data location does not exist, Spring Boot will **throw a `ConfigDataLocationNotFoundException` and your application will not start.**

컨테이너에서 ConfigMap 마운트가 조건부라면 `optional:` 접두어를 붙인다. 붙이지 않으면 "설정이 없어서 기본값으로 뜨는" 대신 **아예 안 뜬다.** 이게 더 안전한 기본값이라는 데는 동의하지만, 모르고 만나면 원인을 엉뚱한 데서 찾는다.

---

## 7. 결정표

| 결정할 것 | 답 | 근거 |
|---|---|---|
| 환경별로 jar 를 따로 굽는다? | **아니오** | 테스트한 바이트 ≠ 배포한 바이트가 된다 |
| 환경별 값은 어디에? | jar **밖** 파일 · 환경변수 · 커맨드라인 | 우선순위 3 < 5 < 11 |
| jar **안**에 넣을 것은? | 어디서나 맞는 기본값, 구조적 설정 | 12-Factor 가 말하는 "내부 설정" |
| 크리덴셜을 프로파일 파일에? | **아니오** | 오픈소스 리트머스 시험지 |
| 프로파일이 축마다 늘어난다 | `spring.profiles.group` 으로 접는다 | 곱셈을 덧셈으로 |
| `active`/`include` 를 on-profile 문서 안에 | **불가** | on-profile 은 한 번만 평가 |
| Maven/Gradle 프로파일로 환경 설정 필터링 | 가급적 금지 | "your project is now non-portable" |
| Maven 프로파일을 언제 쓰나 | 빌드 환경 차이(JDK·OS·통합테스트 on/off) | POM 을 바꾸는 게 목적일 때만 |
| 컨테이너 산출물 | 레이어드 jar(기본) + 추출 실행 | 캐시 히트율 + 기동 시간 |
| Java 24+ 기동 최적화 | CDS 대신 AOT 캐시 | 공식 권고 |
| 캐시 파일 배포 | 아티팩트와 한 몸으로 | "as long as the application is not updated" |

한 줄로 줄이면 이렇다. **늘려야 하는 건 프로파일이라는 "축" 이고, 늘리면 안 되는 건 빌드 산출물이라는 "바이트" 다.** 두 축을 섞는 순간 환경 수만큼 검증해야 할 대상이 늘고, 늘어난 만큼은 아무도 검증하지 않는다.

---

## 근거의 한계

- **성능 수치를 인용하지 않았다.** 레이어드 이미지의 빌드·풀 시간 단축, CDS/AOT 캐시의 기동 시간 감소 폭은 애플리케이션 규모와 인프라에 따라 달라지고, 재현 가능한 중립 측정치를 확인하지 못했다. 문서가 말한 **방향**(빨라진다, 캐시가 재사용된다)만 옮겼고 배수는 쓰지 않았다.
- **12-Factor 와 Spring 프로파일의 화해안은 해석이다.** 두 문서 모두 1차 출처지만, "프로파일은 구조를, 환경변수는 값을" 이라는 계층 구분은 어느 한쪽 문서가 그렇게 적어 둔 문장이 아니라 우선순위 규칙에서 내가 끌어낸 설계다. 12-Factor 의 "환경 묶음 반대" 는 여전히 Spring 프로파일과 긴장 관계에 있고, 그걸 숨기지 않으려고 §2 에 원문 그대로 실었다.
- **`-plain.jar` 로 컨테이너가 뜨지 않는 증상은 추론이다.** 기본 classifier 동작은 공식 문서지만, 그 결과로 어떤 에러가 뜨는지는 Dockerfile 작성 방식에 달려 있다. 자기 빌드 산출물 목록을 직접 확인하는 게 맞다.
- **Maven/Gradle 프로파일을 전면 금지하지는 않았다.** JDK 버전·OS·통합테스트 토글처럼 **빌드 자체가 달라져야 하는** 경우는 정당한 용도다. 이 글이 반대한 것은 그것으로 **애플리케이션 설정값을 산출물에 굽는 것** 하나다.
- **Spring Cloud Config / Vault 등 외부 설정 저장소는 다루지 않았다.** 이 글의 범위는 Spring Boot 본체가 기본으로 제공하는 경로까지다.

---

## References

[^bootprofiles]: Spring 공식 문서 — [Profiles :: Spring Boot](https://docs.spring.io/spring-boot/reference/features/profiles.html)
[^bootext]: Spring 공식 문서 — [Externalized Configuration :: Spring Boot](https://docs.spring.io/spring-boot/reference/features/external-config.html)
[^migration]: Spring Boot 공식 위키 — [Spring Boot Config Data Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-Config-Data-Migration-Guide)
[^mvnprofile]: Apache Maven 공식 문서 — [Introduction to Build Profiles](https://maven.apache.org/guides/introduction/introduction-to-profiles.html)
[^twelve]: Adam Wiggins — [The Twelve-Factor App: III. Config](https://12factor.net/config)
[^gradlepkg]: Spring 공식 문서 — [Packaging Executable Archives :: Spring Boot Gradle Plugin](https://docs.spring.io/spring-boot/gradle-plugin/packaging.html)
[^effimg]: Spring 공식 문서 — [Efficient Container Images :: Spring Boot](https://docs.spring.io/spring-boot/reference/packaging/container-images/efficient-images.html)
[^efficient]: Spring 공식 문서 — [Efficient Deployments :: Spring Boot](https://docs.spring.io/spring-boot/reference/packaging/efficient.html)
[^cds]: Spring 공식 문서 — [Class Data Sharing :: Spring Boot](https://docs.spring.io/spring-boot/reference/packaging/class-data-sharing.html) (JEP 483 — [Ahead-of-Time Class Loading & Linking](https://openjdk.org/jeps/483))
