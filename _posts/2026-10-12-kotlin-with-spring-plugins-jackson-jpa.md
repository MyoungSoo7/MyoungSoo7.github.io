---
layout: post
title: "코틀린 × 스프링 — kotlin-spring(all-open)·kotlin-jpa(no-arg) 플러그인, 생성자 주입, Jackson 코틀린 모듈, JPA 엔티티 함정"
date: 2026-10-12 00:29:42 +0900
categories: [kotlin]
tags: [kotlin, spring, spring-boot, all-open, no-arg, kotlin-jpa, jackson-module-kotlin, jpa, hibernate, dependency-injection]
---

자바·코틀린 20편 시리즈의 **코틀린 9번째 글(K9)** 이다. 코틀린으로 스프링 애플리케이션을 만들 때 부딪히는 마찰 지점을 다섯 덩어리로 나눈다. (1) "기본 final" 과 프록시 — `kotlin-spring` 플러그인, (2) 의존성 주입과 설정 주입, (3) JSON — Jackson 코틀린 모듈과 kotlinx.serialization, (4) JPA — `kotlin-jpa` 플러그인과 엔티티 설계 함정, (5) 테스트. 각 항목은 "무엇인가 → 코드 → 실무 사용사례 → 함정" 순서다.

자바 쪽 짝 글은 스프링이 리플렉션·프록시를 쓰는 원리를 다룬 [J9 — 스프링이 자바를 쓰는 방식](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 과 [J10 — 스프링부트 × 자바 호환](https://myoungsoo7.github.io/2026/10/12/spring-boot-java-version-compatibility/) 이다. 코루틴·DSL·버전 호환은 다음 글 [K10 — 코틀린 × 스프링부트](https://myoungsoo7.github.io/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/) 에서 다룬다. 클래스 기본 final·data class 자체는 [K3 — 클래스](https://myoungsoo7.github.io/2026/10/12/kotlin-classes-data-sealed-object-value/) 를 참고. 프록시가 왜 상속을 필요로 하는지는 예전 글 [Reflection과 Proxy 심화](https://myoungsoo7.github.io/2026/07/14/spring-reflection-and-proxy-deep-dive/) 에도 있다.

---

## 0. 전제 — 스프링 프레임워크의 코틀린 요구사항

스프링 프레임워크 레퍼런스의 [Kotlin — Requirements](https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html) 기준:

| 항목 | Spring Framework 6.2 | Spring Framework 7.0 |
|---|---|---|
| 지원 코틀린 버전 | **Kotlin 1.7+** ([6.2 문서](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/requirements.html)) | **Kotlin 2.2+** ([현재 문서](https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html)) |
| 클래스패스 필수 | `kotlin-stdlib`, `kotlin-reflect` | `kotlin-stdlib`, `kotlin-reflect` |
| JSON (Jackson 사용 시) | `jackson-module-kotlin` — 클래스패스에 있으면 자동 등록 | 동일 |

[start.spring.io](https://start.spring.io/#!language=kotlin) 로 코틀린 프로젝트를 만들면 `kotlin-stdlib`·`kotlin-reflect` 가 기본 포함된다고 같은 문서에 적혀 있다. 스프링부트 버전별 정리는 K10 에서 한다.

---

## 1. 기본 final 과 프록시 — kotlin-spring (all-open)

### 1.1 무엇인가 — 문제

코틀린 클래스와 멤버 함수는 **기본이 `final`** 이다. 스프링 공식 문서([Spring Projects in Kotlin](https://docs.spring.io/spring-framework/reference/languages/kotlin/spring-projects-in.html)): 이 때문에 CGLIB 프록시가 `@Configuration` 클래스 같은 스프링 빈을 **상속할 수 없다.** `@Transactional`·`@Cacheable`·`@Async` 처럼 클래스 기반 프록시로 동작하는 기능이 전부 영향을 받는다.

### 1.2 해법 — all-open 과 그 스프링 프리셋

코틀린 공식 문서([All-open compiler plugin](https://kotlinlang.org/docs/all-open-plugin.html)): all-open 플러그인은 지정한 애노테이션이 붙은 클래스와 그 멤버를 `open` 키워드 없이 **open 으로 만든다.** `kotlin-spring` 은 all-open 위에 스프링 애노테이션을 미리 지정해 둔 래퍼다.

`kotlin-spring` 이 여는 애노테이션:

| 직접 지정 | 메타 애노테이션으로 함께 열리는 것 |
|---|---|
| `@Component`, `@Async`, `@Transactional`, `@Cacheable`, `@SpringBootTest` | `@Configuration`, `@Controller`, `@RestController`, `@Service`, `@Repository` (모두 `@Component` 로 메타 애노테이트됨) |

### 1.3 설정 코드

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "2.2.21"
    kotlin("plugin.spring") version "2.2.21"   // = id("org.jetbrains.kotlin.plugin.spring")
}
```

Maven 은 `kotlin-maven-plugin` 의 `<compilerPlugins>` 에 `<plugin>spring</plugin>` 을 넣고 `kotlin-maven-allopen` 의존성을 추가한다(공식 문서 예제).

```xml
<plugin>
    <groupId>org.jetbrains.kotlin</groupId>
    <artifactId>kotlin-maven-plugin</artifactId>
    <configuration>
        <compilerPlugins>
            <plugin>spring</plugin>
        </compilerPlugins>
    </configuration>
    <dependencies>
        <dependency>
            <groupId>org.jetbrains.kotlin</groupId>
            <artifactId>kotlin-maven-allopen</artifactId>
            <version>${kotlin.version}</version>
        </dependency>
    </dependencies>
</plugin>
```

start.spring.io 로 생성한 프로젝트에는 `kotlin-spring` 이 **기본으로 켜져 있다** (코틀린 문서와 스프링 문서 양쪽에 명시).

### 1.4 실무 사용사례 — 대안: proxyBeanMethods = false

스프링 문서는 `@Configuration` 에 한해 다른 길도 제시한다: CGLIB 프록시 자체를 끄는 것.

```kotlin
@Configuration(proxyBeanMethods = false)
class ClientConfig {
    @Bean
    fun httpClient(): java.net.http.HttpClient = java.net.http.HttpClient.newHttpClient()
}
```

이 경우 `@Bean` 메서드끼리 서로 호출해도 싱글턴 보장이 없으므로, 다른 빈이 필요하면 메서드 파라미터로 주입받는다.

### 1.5 함정

1. **플러그인 없이 `@Transactional` 을 붙이면?** 클래스가 final 이라 CGLIB 가 상속할 수 없다(스프링 문서). 프록시·AOP 가 이상하게 동작하면 빌드에 `kotlin-spring` 이 적용돼 있는지부터 본다.
2. **"클래스가 열렸다" 고 끝이 아니다.** 프록시 기반 AOP 의 원래 제약(같은 클래스 안의 self-invocation 은 프록시를 거치지 않음)은 코틀린에서도 똑같다. 원리는 J9 참고.
3. **`kotlin-spring` 은 스프링 애노테이션만 연다.** JPA 엔티티(`@Entity`) 는 대상이 아니다 → 4장.

---

## 2. 의존성 주입과 설정 주입

### 2.1 생성자 주입 — 기본값으로

스프링 문서: "생성자 주입을 우선하라. `val` 읽기 전용(가능하면 non-null) 프로퍼티로 받는다." 그리고 "생성자가 하나뿐인 클래스는 파라미터가 자동으로 autowire 되므로 `@Autowired constructor` 를 명시할 필요가 없다."

```kotlin
@Service
class OrderService(
    private val orderRepository: OrderRepository,
    private val paymentClient: PaymentClient,
) {
    fun place(cmd: PlaceOrder): Long { /* ... */ TODO() }
}
```

또한 [Classes and Interfaces](https://docs.spring.io/spring-framework/reference/languages/kotlin/classes-interfaces.html) 에 따르면 스프링은 코틀린 클래스를 **주 생성자(primary constructor)로 인스턴스화**할 수 있고, 파라미터 기본값(optional parameter)을 인식하며, 코틀린 파라미터 이름은 `KotlinReflectionParameterNameDiscoverer` 가 `-parameters` 플래그 없이 인식한다. 그래도 문서는 완전성을 위해 코틀린 컴파일러의 `-java-parameters` 플래그를 권장한다.

### 2.2 필드 주입이 꼭 필요하면 lateinit

```kotlin
@Component
class LegacyJob {
    @Autowired
    lateinit var mongoTemplate: MongoTemplate
}
```

**함정:** `lateinit` 프로퍼티를 초기화 전에 읽으면 `UninitializedPropertyAccessException` 이다. 생성자에서 이 필드를 쓰면 반드시 터진다. 테스트 편의를 이유로 필드 주입을 고르지 말 것 — 2.6 의 생성자 주입 테스트가 더 낫다.

### 2.3 internal 함수와 이름 맹글링

코틀린 `internal` 가시성은 바이트코드에서 함수 이름을 **맹글링**한다. 스프링 문서: 이름으로 주입할 때는 맹글링된 이름을 쓰거나 `@JvmName` 을 붙여라.

```kotlin
@Configuration
class SampleConfiguration {
    @Bean
    @JvmName("sampleBean")
    internal fun sampleBean() = SampleBean()
}
```

`@Bean` 메서드 이름이 곧 빈 이름이므로, `internal` 을 붙이는 순간 빈 이름이 바뀔 수 있다는 뜻이다. `@Qualifier("sampleBean")` 으로 찾던 코드가 갑자기 실패하면 여기를 의심한다.

### 2.4 `@Value` 와 `$` — 문자열 템플릿 충돌

코틀린에서 `$` 는 문자열 템플릿 기호다. 스프링 문서의 세 가지 해법:

```kotlin
// 1) 이스케이프
@Component
class Mailer(@Value("\${mail.from}") private val from: String)

// 2) (스프링부트 권장) @ConfigurationProperties
@ConfigurationProperties(prefix = "app")
data class AppProperties(val name: String = "")

// 3) 플레이스홀더 접두사 변경
@Bean
fun propertyConfigurer() = PropertySourcesPlaceholderConfigurer().apply {
    setPlaceholderPrefix("%{")
}
```

### 2.5 `@ConfigurationProperties` + data class (생성자 바인딩)

스프링부트 문서([Kotlin Support](https://docs.spring.io/spring-boot/reference/features/kotlin.html))는 불변 `val` 을 가진 data class 로 생성자 바인딩하는 예를 준다.

```kotlin
@ConfigurationProperties("example.kotlin")
data class KotlinExampleProperties(
    val name: String,
    val description: String,
    val myService: MyService,
) {
    data class MyService(
        val apiToken: String,
        val uri: java.net.URI,
    )
}
```

**함정:** 같은 문서가 **value class 는 지원이 제한적**이니 data class 를 쓰라고 적는다. `@JvmInline value class ApiToken(val raw: String)` 같은 걸 프로퍼티 타입으로 쓰고 싶어도 설정 바인딩에서는 피한다.

### 2.6 checked 예외와 `@Throws`

코틀린에는 checked 예외가 없다. 스프링 문서: 프록시된 객체(`@Transactional` 등)에서 checked 예외를 던지면 기본적으로 **`UndeclaredThrowableException` 으로 감싸진다.** 원래 예외를 그대로 받으려면 `@Throws` 를 붙인다.

```kotlin
@Service
class FileImportService {
    @Transactional
    @Throws(java.io.IOException::class)
    fun import(path: java.nio.file.Path) {
        java.nio.file.Files.readAllLines(path)   // IOException 가능
    }
}
```

**실무 영향:** `@Transactional(rollbackFor = [IOException::class])` 를 걸어 두고 예외 핸들러에서 `IOException` 을 잡도록 짰는데, 실제로는 `UndeclaredThrowableException` 이 올라와 핸들러가 놓치는 버그가 생길 수 있다. 자바 개발자가 코틀린으로 옮겨 올 때 자주 빠뜨리는 부분이다.

### 2.7 애노테이션 배열 속성

```kotlin
@RequestMapping("/toys", method = [RequestMethod.GET])
fun toys(): List<Toy> = TODO()

// 대부분은 단축 애노테이션이 더 낫다
@GetMapping("/toys")
fun toys2(): List<Toy> = TODO()
```

---

## 3. JSON — Jackson 코틀린 모듈과 kotlinx.serialization

### 3.1 무엇인가

Jackson 은 원래 자바 빈(기본 생성자 + setter)을 전제로 만들어졌다. 코틀린 data class 는 기본 생성자가 없고 프로퍼티가 `val` 이다. [jackson-module-kotlin](https://github.com/FasterXML/jackson-module-kotlin) 은 "코틀린 클래스와 data class 의 직렬화/역직렬화 지원" 을 추가해, 기본 생성자 없이도 주 생성자로 객체를 만든다.

스프링 프레임워크 문서: Jackson 으로 코틀린 클래스를 (역)직렬화하려면 이 모듈이 필요하고, **클래스패스에 있으면 자동 등록**된다. 스프링부트 문서도 같은 내용을 적는다.

### 3.2 좌표 — Jackson 2 와 Jackson 3

모듈 README 기준 좌표가 메이저 버전마다 다르다.

| Jackson | groupId | artifactId |
|---|---|---|
| 2.x | `com.fasterxml.jackson.module` | `jackson-module-kotlin` |
| 3.x | `tools.jackson.module` | `jackson-module-kotlin` |

배경: [Spring Framework 7.0 릴리스 노트](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes) 에서 **Jackson 3.x 지원이 기본**이 되고 Jackson 2.x 지원은 deprecated 됐다. 스프링부트 4.0 릴리스 노트도 Jackson 3.0 업그레이드와 "Jackson 2 지원은 deprecated 형태로 제공" 을 적는다. 즉 Boot 4 로 올리면서 Jackson 3 로 가면 코틀린 모듈 좌표도 함께 바꿔야 한다. (버전은 사용하는 BOM 이 관리하는지 확인하고, 아니면 Jackson 버전과 맞춰 명시한다.)

### 3.3 코드

```kotlin
data class OrderResponse(
    val id: Long,
    val status: String,
    val memo: String? = null,     // 응답 JSON 에 없으면 null
)

@RestController
class OrderController(private val service: OrderService) {
    @GetMapping("/orders/{id}")
    fun get(@PathVariable id: Long): OrderResponse = service.find(id)
}
```

### 3.4 함정

1. **모듈이 없으면** data class 역직렬화가 "기본 생성자 없음" 류 오류로 실패한다. 수동으로 `ObjectMapper` 를 만들 때 특히 빠뜨린다. 모듈 README 의 등록 방법: `jacksonObjectMapper()`, 기존 매퍼에 `registerKotlinModule()`, 빌더에서 `addModule(kotlinModule())`. 가능하면 스프링이 구성한 매퍼를 주입받아 쓴다.
2. **non-null 프로퍼티에 JSON `null`.** 코틀린 타입이 `String` 인데 JSON 이 `null` 을 보내면 역직렬화 단계에서 실패해야 맞다. 모듈은 `StrictNullChecks`, `NullIsSameAsDefault` 같은 설정 기능을 제공하므로, 팀에서 "null 을 기본값으로 볼지, 오류로 볼지" 를 정하고 설정으로 고정한다.
3. **kotlinx.serialization 과 섞어 쓰기.** 스프링 7.0 릴리스 노트: 두 JSON 라이브러리를 함께 쓸 때 버그 리포트가 많았기 때문에, Kotlin Serialization 컨버터/코덱이 `KotlinDetector#hasSerializableAnnotation` 으로 **`@Serializable` 이 붙은 타입만** 처리하도록 기본 동작이 바뀌었다. 스프링부트 4.0 은 `spring-boot-starter-kotlin-serialization` 스타터를 새로 제공하며, `Json` 빈을 등록하고 `spring.kotlinx.serialization.json.*` 프로퍼티로 설정한다(4.0 릴리스 노트). 어느 쪽을 주 JSON 엔진으로 쓸지 명시적으로 정해야 한다.

---

## 4. JPA — kotlin-jpa(no-arg) 와 엔티티 설계

### 4.1 무엇인가 — JPA·Hibernate 가 요구하는 것

[Hibernate ORM 6.6 User Guide](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html) 의 엔티티 요구사항 요지:

- 엔티티 클래스는 **public 또는 protected 의 인자 없는 생성자**를 가져야 한다 (Jakarta Persistence 요구).
- 엔티티 클래스는 **final 이면 안 되고**, 메서드나 영속 인스턴스 변수도 final 이면 안 된다 (Jakarta Persistence 규약).
- Hibernate 문서 "Prefer non-final classes": 지연 로딩은 **런타임 프록시**에 의존하며, 이는 엔티티가 non-final 이어야 가능하다. final 클래스도 저장은 되지만 **지연 연관에 프록시를 쓸 수 없어** 성능 튜닝 선택지가 줄어든다.

코틀린 클래스는 기본 final 이고, 주 생성자에 파라미터가 있으면 인자 없는 생성자가 없다. 두 요구를 모두 어긴다.

### 4.2 kotlin-jpa = no-arg + JPA 프리셋

코틀린 공식 문서([No-arg compiler plugin](https://kotlinlang.org/docs/no-arg-plugin.html)):

- no-arg 플러그인은 지정 애노테이션이 붙은 클래스에 **추가 인자 없는 생성자**를 만든다. 이 생성자는 **synthetic** 이라 자바·코틀린 코드에서 직접 호출할 수 없고 **리플렉션으로만** 호출된다. 이로써 JPA 가 인스턴스를 만들 수 있다.
- `kotlin-jpa` 는 no-arg 위에 **`@Entity`, `@Embeddable`, `@MappedSuperclass`** 를 자동 지정한 래퍼다.
- `invokeInitializers` 옵션을 켜면 synthetic 생성자가 초기화 로직을 실행한다. **기본은 꺼져 있다.**

```kotlin
plugins {
    kotlin("plugin.jpa") version "2.2.21"
}
```

### 4.3 open 문제 — 코틀린 2.3.20 전과 후

no-arg 는 생성자만 만든다. **final 문제는 별개**다.

- **Kotlin 2.3.20 이전**: `kotlin-spring` 은 `@Entity` 를 열지 않으므로, 엔티티를 열려면 all-open 을 직접 설정해야 했다.

```kotlin
plugins {
    kotlin("plugin.allopen") version "2.2.21"
}

allOpen {
    annotation("jakarta.persistence.Entity")
    annotation("jakarta.persistence.MappedSuperclass")
    annotation("jakarta.persistence.Embeddable")
}
```

- **Kotlin 2.3.20 부터** ([What's new in 2.3.20](https://kotlinlang.org/docs/whatsnew2320.html), 2026-03-16 릴리스): Gradle `org.jetbrains.kotlin.plugin.jpa` 플러그인이 **all-open 을 JPA 프리셋과 함께 자동 적용**한다. 프리셋 대상은 `javax.persistence` 와 `jakarta.persistence` 의 `Entity`·`Embeddable`·`MappedSuperclass` 다. 문서가 밝힌 이유: "지연 연관이 의도대로 동작하게 해서, 즉시 로딩과 추가 쿼리가 발생하지 않도록." Maven 의 `kotlin-maven-noarg` 도 이제 `kotlin-maven-allopen` 을 암묵적으로 포함한다.

**실무 판단:** 빌드의 코틀린 버전이 2.3.20 미만이면 위 `allOpen { }` 블록이 있는지 확인한다. 없다면 엔티티가 final 로 컴파일되고 있고, Hibernate 문서대로 지연 연관 프록시를 못 쓰고 있을 가능성이 있다. 2.3.20 이상으로 올리면 블록은 중복이 되지만 해롭지는 않다.

### 4.4 data class 를 엔티티로 쓰면 안 되는 이유

코틀린 공식 문서([Data classes](https://kotlinlang.org/docs/data-classes.html))의 사실 세 가지에서 바로 나온다.

1. **data class 는 `open` 일 수 없다** ("abstract, open, sealed, inner 불가"). 즉 all-open 이 적용될 수 있는 일반 클래스가 아니라, 프록시 상속을 원천적으로 상정하지 않은 타입이다.
2. **`equals()`/`hashCode()` 를 주 생성자의 모든 프로퍼티로 생성**한다. 생성되는 ID(`@GeneratedValue`)가 주 생성자에 있으면, 저장 전후로 `hashCode` 가 바뀐다.
3. **`toString()` 도 주 생성자의 모든 프로퍼티를 포함**한다. 연관 엔티티가 주 생성자에 있으면 로그 한 줄이 연관을 따라가며 읽는다.

2번의 결과는 Hibernate 문서가 정확히 설명한다. `Set` 의 계약은 "원소가 Set 안에 있는 동안 equals/hashCode 가 바뀌면 안 된다" 인데, **생성된 식별자** 기반 equals/hashCode 는 트랜잭션이 커밋돼 ID 가 채워지는 순간 값이 바뀐다. 그 결과 저장 전에 `Set` 에 넣은 엔티티를 저장 후 `contains` 로 찾지 못한다. 문서가 제시하는 대안은 **natural id(비즈니스 키)** 기반 equals/hashCode 이며, "모두에게 맞는 단일 해법은 없다" 고 덧붙인다.

### 4.5 권장 엔티티 모양

```kotlin
import jakarta.persistence.*

@Entity
@Table(name = "book")
class Book(
    @Column(nullable = false)
    var title: String,

    @org.hibernate.annotations.NaturalId
    @Column(nullable = false, unique = true, updatable = false)
    val isbn: String,

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "library_id")
    var library: Library? = null,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null
        protected set

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Book) return false
        return isbn == other.isbn
    }

    override fun hashCode(): Int = isbn.hashCode()

    override fun toString(): String = "Book(id=$id, isbn=$isbn)"   // 연관은 넣지 않는다
}
```

설계 포인트:

- **일반 `class`** (data 아님). `kotlin-jpa`(+ all-open JPA 프리셋 또는 수동 allOpen)로 no-arg 생성자와 open 이 붙는다.
- **ID 는 본문의 nullable `var`**, setter 는 `protected` 로 막는다. "저장 전에는 ID 가 없다" 는 사실을 타입(`Long?`)이 그대로 표현한다.
- **equals/hashCode 는 natural id 기반** (Hibernate 문서의 권장안). natural id 가 없는 엔티티라면 팀 규칙을 정해야 하며, 이것은 Hibernate 문서도 단일 정답을 주지 않는 영역이다.
- **toString 에서 연관 제외.**
- 비즈니스 메서드로 상태를 바꾸고, 외부에서 아무 `var` 나 바꾸지 못하게 setter 가시성을 좁힌다.

### 4.6 함정 모음

1. **`invokeInitializers` 를 모르고 본문 초기값에 기대기.** 이 옵션은 기본값이 꺼져 있으므로, synthetic 생성자로 만든 인스턴스에서는 클래스 본문의 초기화 로직이 실행되지 않는다(코틀린 no-arg 문서). DB 에서 채워지지 않는 필드(예: `@Transient` 필드)의 초기값에 기대는 코드가 있다면 옵션을 켜거나 그런 의존을 없앤다.
2. **non-null 타입인데 DB 에는 null.** JPA 가 리플렉션으로 필드에 값을 넣는 경로는 코틀린 생성자·세터를 거치지 않으므로, 컬럼이 nullable 이면 `var title: String` 필드에도 null 이 들어갈 수 있고 문제는 나중에 읽는 지점에서 드러난다. 스키마의 `NOT NULL` 과 코틀린 타입의 nullability 를 일치시킨다.
3. **`val` 영속 필드.** 리플렉션으로 값을 넣으므로 동작은 하지만 "불변" 이라는 코틀린 쪽 의도와 실제 동작이 어긋난다. 바뀌면 안 되는 컬럼은 `@Column(updatable = false)` 로 DB 계약도 같이 건다(위 `isbn`).

### 4.7 대안 — 불변 모델을 원한다면

스프링 문서는 영속 계층에서도 `val` 과 `data class` 를 쓰는 불변 모델을 "가장 코틀린다운" 방식으로 보고, JPA 는 `kotlin-jpa` 로 보완하라고 한다. 그리고 "Kay 릴리스 트레인부터 **Spring Data 는** `kotlin-noarg` 없이 코틀린 불변 클래스를 지원한다" 고 적는다. 실제로 spring.io 의 [Spring Boot + Kotlin 튜토리얼](https://spring.io/guides/tutorials/spring-boot-kotlin/) 은 현재 **Spring Data JDBC** 와 불변 data class 를 사용한다. 엔티티 생명주기·지연 로딩·더티 체킹이 필요 없는 도메인이라면 JPA 대신 Spring Data JDBC 를 고려할 만하다.

---

## 5. 테스트

스프링 문서([Spring Projects in Kotlin — Testing](https://docs.spring.io/spring-framework/reference/languages/kotlin/spring-projects-in.html))의 권장:

### 5.1 테스트 클래스 생성자 주입

```kotlin
@SpringJUnitConfig(TestConfig::class)
@TestConstructor(autowireMode = TestConstructor.AutowireMode.ALL)
class OrderServiceIntegrationTests(
    val orderService: OrderService,
    val customerService: CustomerService,
) {
    @Test
    fun `places an order`() { /* ... */ }
}
```

`junit-platform.properties` 에 `spring.test.constructor.autowire.mode = all` 을 두면 기본값으로 만들 수 있다. `lateinit var` 필드 주입 없이 `val` 로 받는다.

### 5.2 PER_CLASS 생명주기

`@TestInstance(TestInstance.Lifecycle.PER_CLASS)` 를 쓰면 `@BeforeAll`/`@AfterAll` 을 non-static 메서드에 붙일 수 있다. 코틀린에는 `static` 이 없으므로 `companion object` + `@JvmStatic` 보다 깔끔하다. `junit.jupiter.testinstance.lifecycle.default = per_class` 로 기본값 지정도 가능하다.

### 5.3 목킹

스프링부트 문서: 코틀린 클래스 목킹에는 **MockK** 를 권장하고, **SpringMockK** 가 `@MockkBean`·`@SpykBean` 을 제공한다(Mockito 의 `@MockitoBean`·`@MockitoSpyBean` 대응).

---

## 6. 빌드 설정 한눈에 (Spring Boot 4.x 기준 예)

```kotlin
// build.gradle.kts — 버전은 예시. Boot 4.x 는 Kotlin 2.2.x 이상을 요구한다 (K10 참고)
plugins {
    kotlin("jvm") version "2.2.21"
    kotlin("plugin.spring") version "2.2.21"
    kotlin("plugin.jpa") version "2.2.21"
    kotlin("plugin.allopen") version "2.2.21"   // allOpen { } 블록용
    id("org.springframework.boot") version "4.1.1"
}

// 2.3.20 미만이므로 엔티티 open 을 수동 지정
allOpen {
    annotation("jakarta.persistence.Entity")
    annotation("jakarta.persistence.MappedSuperclass")
    annotation("jakarta.persistence.Embeddable")
}

dependencies {
    implementation(platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES))
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("tools.jackson.module:jackson-module-kotlin")   // Jackson 3
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xannotation-default-target=param-property")
    }
}
```

- `allOpen { }` 블록은 all-open Gradle 플러그인의 설정이므로 `kotlin("plugin.allopen")` 을 명시했다. Kotlin 2.3.20 이상이면 `plugin.jpa` 가 JPA 프리셋으로 all-open 을 자동 적용하므로 이 블록과 플러그인 줄은 빼도 된다.
- `spring-boot-starter-web` 은 Boot 4 문서에서 **`spring-boot-starter-webmvc` 로 대체되며 deprecated** 로 표시돼 있다 ([Build Systems — Starters](https://docs.spring.io/spring-boot/reference/using/build-systems.html)).
- `-Xannotation-default-target=param-property` 는 Boot 4 문서가 Kotlin 2.2.x 의 새 애노테이션 기본 대상 규칙으로 인한 경고를 피하려고 권장하는 플래그다 (K10 에서 설명).

---

## 7. 체크리스트

- [ ] `kotlin("plugin.spring")` 이 적용돼 `@Service`/`@Configuration`/`@Transactional` 클래스가 열려 있는가
- [ ] 의존성은 생성자 `val` 로 받고, `@Autowired lateinit` 은 예외로만 쓰는가
- [ ] `@Value` 의 `$` 를 이스케이프했거나 `@ConfigurationProperties` data class 로 옮겼는가
- [ ] 프록시 대상 메서드가 checked 예외를 던지면 `@Throws` 를 붙였는가
- [ ] Jackson 메이저 버전에 맞는 `jackson-module-kotlin` 좌표를 쓰는가 (2.x: `com.fasterxml…`, 3.x: `tools.jackson…`)
- [ ] `kotlin("plugin.jpa")` 가 있고, Kotlin 2.3.20 미만이면 엔티티용 `allOpen { }` 도 있는가
- [ ] 엔티티가 data class 가 아니고, ID 기반 equals/hashCode 로 `Set` 문제를 만들지 않는가
- [ ] 엔티티 `toString` 이 지연 연관을 건드리지 않는가

---

## References

- Spring Framework Reference — [Kotlin: Requirements (7.0)](https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html), [Requirements (6.2)](https://docs.spring.io/spring-framework/reference/6.2/languages/kotlin/requirements.html)
- Spring Framework Reference — [Kotlin: Classes and Interfaces](https://docs.spring.io/spring-framework/reference/languages/kotlin/classes-interfaces.html)
- Spring Framework Reference — [Kotlin: Spring Projects in Kotlin](https://docs.spring.io/spring-framework/reference/languages/kotlin/spring-projects-in.html)
- Spring Framework — [7.0 Release Notes (wiki)](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes)
- Spring Boot Reference — [Kotlin Support](https://docs.spring.io/spring-boot/reference/features/kotlin.html)
- Spring Boot Reference — [Build Systems (Starters)](https://docs.spring.io/spring-boot/reference/using/build-systems.html)
- Spring Boot — [4.0 Release Notes (wiki)](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
- spring.io Guide — [Building web applications with Spring Boot and Kotlin](https://spring.io/guides/tutorials/spring-boot-kotlin/)
- Kotlin docs — [All-open compiler plugin](https://kotlinlang.org/docs/all-open-plugin.html)
- Kotlin docs — [No-arg compiler plugin](https://kotlinlang.org/docs/no-arg-plugin.html)
- Kotlin docs — [What's new in Kotlin 2.3.20](https://kotlinlang.org/docs/whatsnew2320.html)
- Kotlin docs — [Data classes](https://kotlinlang.org/docs/data-classes.html)
- FasterXML — [jackson-module-kotlin README](https://github.com/FasterXML/jackson-module-kotlin)
- Hibernate ORM 6.6 — [User Guide (Entity types, Implementing equals() and hashCode())](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html)

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
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) ← 지금 글
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
