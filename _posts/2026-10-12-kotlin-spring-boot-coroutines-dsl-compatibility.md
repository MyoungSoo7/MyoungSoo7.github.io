---
layout: post
title: "코틀린 × 스프링부트 — 버전 호환표, 널 안전(JSR-305 → JSpecify), suspend 컨트롤러와 Flow, 라우터·빈 등록 DSL"
date: 2026-10-12 00:30:42 +0900
categories: [kotlin]
tags: [kotlin, spring-boot, spring-framework, coroutines, flow, webflux, spring-mvc, jspecify, null-safety, kotlin-dsl, bean-registrar]
---

자바·코틀린 20편 시리즈의 **코틀린 10번째 글(K10)**, 코틀린 편의 마지막이다. 스프링부트에서 코틀린을 쓸 때 "어느 버전에서 무엇이 되는가" 를 다섯 덩어리로 정리한다. (1) 버전 호환표 — Boot 3.x / 4.x 와 Spring Framework 6.2 / 7.0 의 코틀린 요구사항, (2) 널 안전 — JSR-305 에서 JSpecify 로, (3) 코루틴 — `suspend` 컨트롤러·`Flow` 반환·트랜잭션·컨텍스트 전파, (4) Kotlin DSL — 라우터 DSL, 빈 등록 DSL, MockMvc DSL, (5) 부트 고유 지원과 Boot 3 → 4 이행 체크리스트.

자바 쪽 짝 글은 [J10 — 스프링부트 × 자바 호환](https://myoungsoo7.github.io/2026/10/12/spring-boot-java-version-compatibility/) 과 [J9 — 스프링이 자바를 쓰는 방식](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 이다. 플러그인·Jackson·JPA 는 직전 글 [K9 — 코틀린 × 스프링](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/), 코루틴 자체는 [K7 — 코루틴과 Flow](https://myoungsoo7.github.io/2026/10/12/kotlin-coroutines-and-flow/) 에 있다.

> 이 글의 "현재" 는 2026-10-12 기준 docs.spring.io 의 최신 안정 문서다 (Spring Framework 7.0.9, Spring Boot 4.1.1). 이전 세대는 Spring Framework 6.2 / Spring Boot 3.5 문서를 인용한다.

---

## 1. 버전 호환표

### 1.1 표

| | Spring Boot 3.5 | Spring Boot 4.x |
|---|---|---|
| 요구 코틀린 | **최소 Kotlin 1.7.x** ([Boot 3.5 Kotlin](https://docs.spring.io/spring-boot/3.5/reference/features/kotlin.html)) | **최소 Kotlin 2.2.x** ([Boot Kotlin](https://docs.spring.io/spring-boot/reference/features/kotlin.html)) |
| 기반 Spring Framework | 6.2.19 이상 (3.5.16 기준, [시스템 요구사항](https://docs.spring.io/spring-boot/3.5/system-requirements.html)) | 7.0.9 이상 (4.1.1 기준, [시스템 요구사항](https://docs.spring.io/spring-boot/system-requirements.html)) |
| Spring Framework 의 코틀린 지원 | Kotlin 1.7+ ([SF 6.2](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/requirements.html)) | Kotlin 2.2+ ([SF 7.0](https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html)) |
| 자바 | 17 ~ 25 | 17 ~ 26 (4.1.1 기준) |
| 널 안전 애노테이션 | JSR-305 (`-Xjsr305` 플래그) | JSpecify |
| 기본 JSON | Jackson 2 | Jackson 3 (Jackson 2 지원은 deprecated) |
| 기본 테스트 | JUnit 5 | JUnit 6 |
| 함수형 빈 등록 DSL | `beans { }` (`BeanDefinitionDsl`) | `BeanRegistrarDsl` (`beans { }` 는 deprecated) |

보충 근거:

- Spring Framework 7.0 릴리스 노트의 "Baseline Upgrades": JDK 17 기준선 유지(JDK 25 권장), Jakarta EE 11, **Kotlin 2.2**, GraalVM 25, **JUnit 6** ([SF 7.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes)).
- Spring Boot 4.0 릴리스 노트의 의존성 업그레이드 목록에 **Kotlin 2.2.20**, Kotlin Serialization 1.9, Jackson 3.0 이 있다 ([Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)).
- Spring Boot 4.0.0 GA 는 **2025-11-20** 에 발표됐다 ([spring.io 블로그](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)). 발표문 하이라이트: 코드베이스 전면 모듈화, JSpecify 기반 포트폴리오 전반 널 안전 개선, Java 25 1급 지원(Java 17 호환 유지), API 버저닝과 HTTP Service Client.
- 코틀린 쪽 날짜 참고: Kotlin 2.2.0 은 2025-06-23, 2.2.20 은 2025-09-10 릴리스 ([Kotlin releases](https://kotlinlang.org/docs/releases.html)).

### 1.2 실무 해석

- **Boot 3 → 4 이행은 코틀린 2.x 이행을 강제한다.** Boot 3.5 는 1.7.x 이상이면 됐지만 Boot 4 는 2.2.x 이상이다. 아직 1.9 를 쓰는 서비스라면 K2 컴파일러 전환 검증을 Boot 업그레이드와 같은 마일스톤에 넣어야 한다.
- **코틀린 버전은 부트가 관리한다.** 스프링부트 문서: 부트는 **Kotlin BOM** 을 임포트하고, Maven 은 `kotlin.version` 프로퍼티로 바꾸며, Gradle 은 부트 플러그인이 `kotlin.version` 을 **코틀린 플러그인 버전에 자동으로 맞춘다.** 코루틴은 Kotlin Coroutines BOM 으로 관리되고 `kotlin-coroutines.version` 프로퍼티로 바꾼다.
- 자바 버전 요구는 J10 에서 상세히 다룬다.

### 1.3 함정

- **Gradle 에서 코틀린 플러그인 버전만 올리고 끝내기.** 부트가 `kotlin.version` 을 플러그인 버전에 맞추므로 stdlib 은 따라오지만, 그 버전이 해당 Boot 의 "요구 최소 버전" 이상인지는 따로 확인해야 한다.
- **`kotlin-reflect` 누락.** 두 세대 모두 클래스패스 필수다. 생성자 바인딩·파라미터 이름 탐색이 이것에 기대고 있다(K9).

---

## 2. 널 안전 — JSR-305 에서 JSpecify 로

### 2.1 Spring Framework 6.x / Boot 3.x — JSR-305

[SF 6.2 Null-safety](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/null-safety.html) 와 [Boot 3.5 Kotlin](https://docs.spring.io/spring-boot/3.5/reference/features/kotlin.html) 요지:

- 스프링 API 는 `org.springframework.lang` 패키지의 JSR-305 기반 애노테이션으로 nullability 를 표시하고, 코틀린은 이것을 읽어 자바 API 를 플랫폼 타입이 아닌 nullable/non-null 타입으로 본다.
- 컴파일러 플래그 `-Xjsr305={strict|warn|ignore}`. 기본값은 `warn`, 스프링 API 에 완전한 널 안전을 원하면 **`strict` 권장** — 단 Boot 문서는 "스프링 API 의 nullability 선언이 마이너 릴리스 사이에도 바뀔 수 있다" 는 점을 감수하라고 적는다.
- **제네릭 타입 인자, varargs, 배열 원소의 nullability 는 아직 지원하지 않음.**

```kotlin
// Boot 3.x build.gradle.kts
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xjsr305=strict")
    }
}
```

### 2.2 Spring Framework 7.0 / Boot 4.x — JSpecify

[SF 7.0 Null-safety (Kotlin)](https://docs.spring.io/spring-framework/reference/languages/kotlin/null-safety.html) 와 7.0 릴리스 노트 요지:

- 스프링 프레임워크 API 전체의 널 안전을 **[JSpecify](https://jspecify.dev/) 애노테이션**으로 제공한다.
- **"Kotlin 2.1 부터 코틀린은 `org.jspecify.annotations` 패키지의 nullability 애노테이션을 엄격하게 처리한다."** 즉 `-Xjsr305` 같은 플래그 없이도 엄격 모드다.
- 릴리스 노트: JSpecify 는 JSR-305 대비 명확한 명세, split-package 문제가 없는 정식 의존성, 더 나은 툴링과 **코틀린 통합**, 그리고 **제네릭 타입·배열·vararg 원소의 nullness 지정**이 가능하다. 스프링 기반 애플리케이션에도 JSpecify 사용을 권장한다.

### 2.3 함정 — 업그레이드하면 컴파일이 깨질 수 있다

SF 7.0 릴리스 노트가 직접 경고한다: 스프링 프레임워크 코틀린 API 의 nullability 가 바뀌어 **코틀린 프로젝트에 코드 수정이 필요할 수 있다.** 이유는 두 가지다.

1. JSR-305 와 JSpecify 를 코틀린이 해석하는 방식의 차이
2. 코틀린 확장 함수의 nullability 를 자바 API 에 더 가깝게 맞춘 정비 — 예로 `JdbcOperations`, `RestOperations` 확장이 언급된다. `JdbcOperations.queryForObject(sql, args: Array<out Any>)`·`queryForList(sql, args: Array<out Any>)` 확장은 **배열 파라미터 대신 vararg 버전으로 교체**됐다.

**대응:** 업그레이드 후 이런 확장 호출부에서 컴파일 오류가 나면, 확장 대신 `JdbcTemplate` 의 자바 API 를 직접 쓰는 것도 방법이다. 자바 API 시그니처는 확장 정비의 영향을 받지 않는다.

```kotlin
val names: List<String> =
    jdbc.queryForList("select name from users where team = ?", String::class.java, teamId)
```

### 2.4 `-Xannotation-default-target=param-property`

Boot 4 코틀린 문서는 **Kotlin 2.2.x 의 새 애노테이션 기본 대상(defaulting) 규칙으로 인한 경고를 피하려면** 이 컴파일러 플래그를 설정하라고 권장한다.

```kotlin
// Boot 4.x build.gradle.kts
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xannotation-default-target=param-property")
    }
}
```

생성자 프로퍼티(`class A(@NotBlank val name: String)` 처럼 대상을 명시하지 않은 자리)에 붙은 애노테이션이 파라미터·프로퍼티·필드 중 어디로 가는지에 관한 규칙이므로, Bean Validation 애노테이션을 생성자 프로퍼티에 다는 DTO 가 많다면 업그레이드 후 경고를 꼭 확인한다.

---

## 3. 코루틴 — suspend 컨트롤러와 Flow

### 3.1 무엇인가 — 지원 범위

[SF Coroutines](https://docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html) 이 나열하는 지원 범위 (6.2 문서도 동일 목록):

- Spring MVC·WebFlux 의 `@Controller` 에서 **`Deferred`·`Flow` 반환값**
- Spring MVC·WebFlux 의 `@Controller` 에서 **suspend 함수**
- WebFlux 클라이언트·서버 함수형 API 확장
- WebFlux.fn **`coRouter { }`** DSL
- WebFlux **`CoWebFilter`**
- RSocket `@MessageMapping` 의 suspend·`Flow`, `RSocketRequester` 확장
- Spring AOP

**의존성:** `kotlinx-coroutines-core` 와 `kotlinx-coroutines-reactor` 가 클래스패스에 있으면 활성화되며, **1.4.0 이상**을 지원한다. 스프링부트 문서: 리액티브 프로젝트에는 `kotlinx-coroutines-reactor` 가 기본 제공된다. Spring MVC 프로젝트에서 suspend 컨트롤러를 쓰려면 두 의존성을 직접 추가한다.

```kotlin
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")
}
```

(버전은 부트의 Kotlin Coroutines BOM 이 관리한다.)

### 3.2 리액티브 타입 ↔ 코루틴 번역 규칙

공식 문서의 대응:

| 리액티브 | 코루틴 |
|---|---|
| `fun handler(): Mono<Void>` | `suspend fun handler()` |
| `fun handler(): Mono<T>` | `suspend fun handler(): T` 또는 `T?` (Mono 가 비어 있을 수 있으면) |
| `fun handler(): Flux<T>` | `fun handler(): Flow<T>` |
| 파라미터 `Mono<T>` (지연 불필요) | `fun handler(value: T)` |
| 파라미터 `Mono<T>` (지연 필요) | `fun handler(supplier: suspend () -> T)` |

`Mono<T>` → `T?` 구분은 문서가 말하듯 "더 정적으로 타입화된다" 는 이점이 있다. 빈 결과 가능성이 시그니처에 드러난다.

### 3.3 코드 — 컨트롤러

```kotlin
@RestController
class BannerController(private val client: WebClient, private val banner: Banner) {

    @GetMapping("/suspend")
    suspend fun one(): Banner {
        delay(10)
        return banner
    }

    @GetMapping("/flow")
    fun many(): Flow<Banner> = flow {
        emit(banner)
        delay(10)
        emit(banner)
    }

    @GetMapping("/parallel")
    suspend fun parallel(): List<Banner> = coroutineScope {
        val a = async { client.get().uri("/suspend").retrieve().awaitBody<Banner>() }
        val b = async { client.get().uri("/suspend").retrieve().awaitBody<Banner>() }
        listOf(a.await(), b.await())
    }
}

data class Banner(val title: String, val message: String)
```

공식 예제는 `awaitExchange()` 뒤에 `awaitBody<Banner>()` 를 잇는 형태도 보여 준다. 문서는 `@Controller` 에서 suspend 함수로 **뷰 렌더링**(`suspend fun render(model: Model): String`)도 지원한다고 적는다.

### 3.4 실무 사용사례

1. **팬아웃 집계 API** — 위 `parallel()` 처럼 `coroutineScope` + `async`. 하나가 실패하면 나머지가 취소되는 구조적 동시성을 컨트롤러에서 그대로 얻는다(K7 2장).
2. **스트리밍 응답** — `Flow<T>` 반환. 문서에 따르면 `Flow` 는 코루틴 세계의 `Flux` 대응물로, hot/cold·유한/무한 스트림에 모두 쓸 수 있다.
3. **Spring MVC 서비스의 점진적 도입** — 기존 MVC 앱에서 일부 엔드포인트만 `suspend` 로 바꿔 외부 호출을 동시에 하는 식. 두 코루틴 의존성만 추가하면 된다.

### 3.5 트랜잭션

공식 문서: "코루틴의 트랜잭션은 리액티브 트랜잭션 관리의 **프로그래밍 방식 변형**으로 지원된다."

```kotlin
import org.springframework.transaction.reactive.TransactionalOperator
import org.springframework.transaction.reactive.executeAndAwait
import org.springframework.transaction.reactive.transactional

class PersonRepository(private val operator: TransactionalOperator) {

    suspend fun initDatabase() = operator.executeAndAwait {
        insertPerson1()
        insertPerson2()
    }

    fun updatePeople(): Flow<Person> =
        findPeople().map(::updatePerson).transactional(operator)

    private suspend fun insertPerson1() { /* INSERT */ }
    private suspend fun insertPerson2() { /* INSERT */ }
    private fun findPeople(): Flow<Person> = TODO("SELECT")
    private suspend fun updatePerson(p: Person): Person = TODO("UPDATE")
}

data class Person(val id: Long, val name: String)
```

그리고 선언적 트랜잭션 쪽 문서([Understanding the Spring Framework's Declarative Transaction Implementation](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-decl-explained.html)): `TransactionInterceptor` 는 **메서드 반환 타입**으로 방식을 고른다. `Publisher` 나 **Kotlin `Flow`** 를 반환하는 메서드는 **리액티브 트랜잭션 관리** 대상이고, 그 외(`void` 포함)는 명령형 경로다. 명령형은 `PlatformTransactionManager`, 리액티브는 `ReactiveTransactionManager` 구현이 필요하다.

**함정 — JPA/JDBC 와 섞기.** 리액티브 트랜잭션은 `ReactiveTransactionManager`(예: R2DBC) 를 전제로 한다. 블로킹 JPA 리포지토리를 `suspend` 함수 안에서 부르면서 위 `TransactionalOperator` 를 쓰는 조합은 성립하지 않는다. Spring MVC + JPA 앱에 suspend 를 도입할 때는 트랜잭션 경계를 블로킹 서비스 메서드(`@Transactional`, 명령형)에 두고, 그 호출을 `withContext(Dispatchers.IO)` 로 감싸는 식으로 경계를 분명히 나누는 편이 안전하다.

### 3.6 컨텍스트 전파 (Spring Framework 7.0)

SF 7.0 릴리스 노트: 블로킹·리액티브에서는 잘 되던 트레이스 컨텍스트 전파가 코루틴 실행 중에는 보이지 않는다는 피드백에 따라, **`PropagationContextElement`** 로 코루틴의 자동 컨텍스트 전파를 도입했다.

공식 문서 요지: 트레이싱의 현재 observation 은 블로킹 코드에선 `ThreadLocal`, 리액티브 파이프라인에선 Reactor `Context` 로 전파되지만, suspend 함수 실행 컨텍스트에도 있어야 "traceId" 가 로그에 붙는다. `io.micrometer:context-propagation` 의존성이 필요하고(`kotlinx-coroutines-reactor` 는 선택), 스프링이 코루틴을 Reactor 로 적응시키는 경로(`CoroutinesUtils#invokeSuspendingFunction`)의 자동 전파는 `Hooks.enableAutomaticContextPropagation()` 으로 켠다. 직접 쓸 때는:

```kotlin
fun main() {
    runBlocking(Dispatchers.IO + PropagationContextElement()) {
        waitAndLog()
    }
}

suspend fun waitAndLog() {
    delay(10)
    logger.info("Suspending function with traceId")
}
```

**실무:** Boot 3 에서 코루틴 컨트롤러 로그에 traceId 가 빠지던 문제를 겪었다면, Boot 4(SF 7.0) 로 올린 뒤 이 메커니즘으로 정리할 수 있다.

### 3.7 함정 모음

1. **컨트롤러에서 `runBlocking`.** suspend 컨트롤러가 지원되므로 필요 없다. 요청 스레드를 블록할 뿐이다(K7 1.4).
2. **`catch (e: Exception)` 으로 취소 삼키기.** 클라이언트 연결이 끊겨 요청 코루틴이 취소될 때 `CancellationException` 을 일반 오류로 처리해 500 로그를 쏟아내는 경우가 있다. 공식 예제에도 `CancellationException` 을 던지는 `/cancel` 엔드포인트가 따로 있다.
3. **WebFlux 에서 블로킹 호출.** `suspend` 라고 블로킹 JDBC 가 논블로킹이 되지는 않는다.

---

## 4. Kotlin DSL

### 4.1 라우터 DSL

[SF Kotlin Web](https://docs.spring.io/spring-framework/reference/languages/kotlin/web.html): 라우터 DSL 은 세 가지다.

| DSL | 대상 |
|---|---|
| `router { }` | WebMvc.fn |
| `router { }` | WebFlux.fn (Reactive) |
| `coRouter { }` | WebFlux.fn (Coroutines) |

```kotlin
@Configuration
class RouterConfiguration {

    @Bean
    fun mainRouter(userHandler: UserHandler) = router {
        accept(TEXT_HTML).nest {
            GET("/") { ok().render("index") }
            GET("/users", userHandler::findAllView)
        }
        "/api".nest {
            accept(APPLICATION_JSON).nest {
                GET("/users", userHandler::findAll)
            }
        }
        resources("/**", ClassPathResource("static/"))
    }
}
```

```kotlin
@Bean
fun apiRouter(handler: UserCoHandler) = coRouter {
    GET("/api/user", handler::listApi)
}

class UserCoHandler(builder: WebClient.Builder) {
    private val client = builder.baseUrl("http://users").build()

    suspend fun listApi(request: ServerRequest): ServerResponse =
        ServerResponse.ok().contentType(MediaType.APPLICATION_JSON)
            .bodyAndAwait(client.get().uri("/").retrieve().bodyToFlow<User>())
}
```

**사용사례:** 문서가 강조하는 장점은 DSL 이 **프로그래밍 방식**이라 `if`·`for` 같은 코틀린 구문으로 라우트를 동적으로 등록할 수 있다는 점이다. 기능 플래그·테넌트 설정에 따라 라우트를 켜고 끄는 경우에 맞다.

**함정:** `router { }` 는 MVC 용과 WebFlux 용이 **이름이 같다**. import 경로(`org.springframework.web.servlet.function.router` vs `org.springframework.web.reactive.function.server.router`)를 IDE 가 잘못 고르면 엉뚱한 스택의 `RouterFunction` 이 만들어진다.

### 4.2 빈 등록 DSL — `beans { }` 에서 `BeanRegistrarDsl` 로

**SF 6.2 까지: `beans { }`** ([6.2 Bean Definition DSL](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/bean-definition-dsl.html))

```kotlin
val myBeans = beans {
    bean<Foo>()
    bean<Bar>()
    bean("bazBean") {
        Baz().apply { message = "Hello world" }
    }
    profile("foobar") {
        bean { FooBar(ref("bazBean")) }
    }
    bean(::myRouter)
}
```

`beans()` 는 `ApplicationContextInitializer` 를 반환한다. 6.2 문서는 "**스프링부트는 아직 함수형 빈 정의를 위한 전용 지원을 제공하지 않는다**" 고 적고, 부트의 `ApplicationContextInitializer` 지원으로 실험적으로 쓸 수 있다고 안내한다.

**SF 7.0 부터: `BeanRegistrar` / `BeanRegistrarDsl`** ([Programmatic Bean Registration](https://docs.spring.io/spring-framework/reference/core/beans/java/programmatic-bean-registration.html))

- "Spring Framework 7 부터 `BeanRegistrar` 인터페이스로 프로그래밍 방식 빈 등록을 1급 지원한다."
- 보통 `@Configuration` 클래스에 `@Import` 로 가져온다.
- 타입 수준 `@Conditional` 계열로 조건부 임포트 가능.
- **AOT 최적화 지원** — JVM 과 GraalVM 네이티브 이미지 모두, instance supplier 를 써도.
- 7.0.9 KDoc 에서 `BeanDefinitionDsl` 은 **Deprecated, "Use BeanRegistrarDsl instead"** 로 표시돼 있다 ([KDoc](https://docs.spring.io/spring-framework/docs/current/kdoc-api/spring-context/org.springframework.context.support/-bean-definition-dsl/index.html)).

```kotlin
class MyBeanRegistrar : BeanRegistrarDsl({
    registerBean<Foo>()
    registerBean(
        name = "bar",
        prototype = true,
        lazyInit = true,
        description = "Custom description",
    ) {
        Bar(bean<Foo>())
    }
    profile("baz") {
        registerBean { Baz("Hello World!") }
    }
    registerBean<MyRepository>()
    registerBean {
        myRouter(bean<MyRepository>())
    }
})

@Configuration
@Import(MyBeanRegistrar::class)
class MyConfiguration
```

**실무 판단:**

- 애노테이션 스캔 대신 **명시적 등록**이 필요한 곳(조건이 복잡한 인프라 빈, 플러그인형 모듈)에서 쓴다.
- Boot 3 시절 `beans { }` + `ApplicationContextInitializer` 로 짠 코드가 있다면, Boot 4 이행 때 `BeanRegistrarDsl` + `@Import` 로 옮기는 것이 deprecated 경고를 없애고 AOT 지원도 받는 길이다.

### 4.3 MockMvc DSL

```kotlin
mockMvc.get("/person/{name}", "Lee") {
    secure = true
    accept = APPLICATION_JSON
    headers { contentLanguage = Locale.FRANCE }
}.andExpect {
    status { isOk }
    content { contentType(APPLICATION_JSON) }
    jsonPath("$.name") { value("Lee") }
}.andDo {
    print()
}
```

([SF Kotlin Web — MockMvc DSL](https://docs.spring.io/spring-framework/reference/languages/kotlin/web.html)) `"$.name"` 의 `$` 뒤에 식별자 문자가 아닌 `.` 이 오므로 코틀린 문자열 템플릿으로 해석되지 않는다. 다만 `"$name"` 형태의 JSONPath 를 쓰면 템플릿으로 해석되니 `"\$name"` 으로 이스케이프한다(K9 2.4 와 같은 원리).

### 4.4 Kotlin 확장 — reified 와 import

[SF Kotlin Extensions](https://docs.spring.io/spring-framework/reference/languages/kotlin/extensions.html): `RestTemplate`, `WebClient`, `GenericApplicationContext.registerBean` 등에 reified 타입 파라미터를 쓰는 확장이 있고, 확장은 **import 해야** 쓸 수 있다 (예: `import org.springframework.context.support.registerBean`).

```kotlin
val users: Flux<User> = client.get().retrieve().bodyToFlux()
```

**참고:** SF 7.0 릴리스 노트에 따르면 `RestTemplate` 은 7.0 에서 레퍼런스 문서상 deprecated 가 됐고 **7.1 에서 공식 `@Deprecated`** 가 될 예정이다. 새 코드에서 `RestTemplate` 의 코틀린 확장에 의존하는 것은 피한다.

---

## 5. 부트 고유 지원

### 5.1 runApplication

```kotlin
@SpringBootApplication
class MyApplication

fun main(args: Array<String>) {
    runApplication<MyApplication>(*args) {
        setBannerMode(Banner.Mode.OFF)
    }
}
```

([Boot Kotlin](https://docs.spring.io/spring-boot/reference/features/kotlin.html)) `SpringApplication.run(MyApplication::class.java, *args)` 의 코틀린다운 대안이며, 람다로 `SpringApplication` 을 커스터마이즈한다.

### 5.2 설정 메타데이터

`@ConfigurationProperties` 메타데이터 생성에는 `kapt` 로 `spring-boot-configuration-processor` 를 돌린다. 부트 문서는 kapt 모델의 한계로 기본값·deprecated 항목 감지 같은 일부 기능이 제한된다고 적는다.

### 5.3 Kotlin Serialization 스타터 (Boot 4.0)

Boot 4.0 릴리스 노트: 새 모듈 `spring-boot-kotlinx-serialization-json` 과 스타터 `spring-boot-starter-kotlin-serialization` 이 추가됐고, `Json` 빈을 등록해 `spring.kotlinx.serialization.json.*` 프로퍼티로 구성한다. SF 7.0 은 Jackson 과 섞어 쓸 때 충돌을 줄이기 위해 Kotlin Serialization 컨버터가 `@Serializable` 타입만 처리하도록 기본 동작을 바꿨다(K9 3.4).

### 5.4 테스트

- Boot 3.5: JUnit 5 가 기본이며 권장.
- Boot 4.x: **JUnit 6 가 기본**이며 코틀린 호환성 측면에서 권장. 테스트 클래스 인스턴스 재사용과 non-static `@BeforeAll`/`@AfterAll` 을 언급한다.
- 두 세대 모두 MockK, SpringMockK(`@MockkBean`, `@SpykBean`) 를 권장한다.

---

## 6. Boot 3 → 4 이행 체크리스트 (코틀린 관점)

| # | 항목 | 근거 |
|---|---|---|
| 1 | Kotlin 2.2.x 이상으로 올렸는가 | Boot 4 Kotlin 문서 "at least Kotlin 2.2.x" |
| 2 | `-Xjsr305=strict` 대신 JSpecify 기반 엄격 처리로 바뀐 것을 반영했는가 (컴파일 오류 수정) | SF 7.0 Null-safety, 릴리스 노트 |
| 3 | `-Xannotation-default-target=param-property` 를 추가했는가 | Boot 4 Kotlin 문서 |
| 4 | `JdbcOperations`·`RestOperations` 코틀린 확장의 시그니처·nullability 변경을 확인했는가 | SF 7.0 릴리스 노트 |
| 5 | `jackson-module-kotlin` 을 Jackson 3 좌표(`tools.jackson.module`)로 바꿨는가 | SF 7.0 / Boot 4.0 릴리스 노트, 모듈 README |
| 6 | `beans { }` 를 `BeanRegistrarDsl` + `@Import` 로 옮겼는가 | SF 7.0 KDoc deprecated 표시 |
| 7 | `spring-boot-starter-web` 을 `spring-boot-starter-webmvc` 로 바꿨는가 | Boot 4 Starters 표 (web 은 deprecated) |
| 8 | 코루틴 traceId 전파를 `PropagationContextElement` 로 정리했는가 | SF 7.0 릴리스 노트 |
| 9 | 테스트가 JUnit 6 에서 도는가 | SF 7.0 baseline, Boot 4 Kotlin 문서 |
| 10 | Kotlin 스크립트 템플릿(JSR 223)을 쓰고 있다면 대안을 찾았는가 | SF 7.0: 코틀린 팀의 JSR 223 제거 계획에 따라 deprecated |

```kotlin
// Boot 4.x 기준 build.gradle.kts 핵심부 (버전은 예시)
plugins {
    kotlin("jvm") version "2.2.21"
    kotlin("plugin.spring") version "2.2.21"
    id("org.springframework.boot") version "4.1.1"
}

dependencies {
    implementation(platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES))
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    implementation("tools.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xannotation-default-target=param-property")
    }
}
```

---

## References

- Spring Framework Reference (7.0) — [Kotlin: Requirements](https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html), [Null-safety](https://docs.spring.io/spring-framework/reference/languages/kotlin/null-safety.html), [Coroutines](https://docs.spring.io/spring-framework/reference/languages/kotlin/coroutines.html), [Web](https://docs.spring.io/spring-framework/reference/languages/kotlin/web.html), [Extensions](https://docs.spring.io/spring-framework/reference/languages/kotlin/extensions.html)
- Spring Framework Reference (7.0) — [Programmatic Bean Registration](https://docs.spring.io/spring-framework/reference/core/beans/java/programmatic-bean-registration.html)
- Spring Framework Reference (7.0) — [Declarative Transaction Implementation](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-decl-explained.html)
- Spring Framework KDoc (7.0.9) — [BeanDefinitionDsl](https://docs.spring.io/spring-framework/docs/current/kdoc-api/spring-context/org.springframework.context.support/-bean-definition-dsl/index.html)
- Spring Framework Reference (6.2) — [Kotlin: Requirements](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/requirements.html), [Null-safety](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/null-safety.html), [Bean Definition DSL](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/bean-definition-dsl.html), [Coroutines](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/coroutines.html)
- Spring Framework — [7.0 Release Notes (wiki)](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes)
- Spring Boot Reference (4.x) — [Kotlin Support](https://docs.spring.io/spring-boot/reference/features/kotlin.html), [System Requirements](https://docs.spring.io/spring-boot/system-requirements.html), [Build Systems (Starters)](https://docs.spring.io/spring-boot/reference/using/build-systems.html)
- Spring Boot Reference (3.5) — [Kotlin Support](https://docs.spring.io/spring-boot/3.5/reference/features/kotlin.html), [System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html)
- Spring Boot — [4.0 Release Notes (wiki)](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
- spring.io blog — [Spring Boot 4.0.0 available now (2025-11-20)](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)
- Kotlin docs — [Kotlin releases](https://kotlinlang.org/docs/releases.html)
- FasterXML — [jackson-module-kotlin README](https://github.com/FasterXML/jackson-module-kotlin)

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
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/)

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
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/) ← 지금 글
