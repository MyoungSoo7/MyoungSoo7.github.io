---
layout: post
title: "Spring Boot 4 MSA 1일차 — 모놀리스에서 마이크로서비스로"
date: 2026-05-09 14:00:00 +0900
categories: [backend, spring]
tags: [spring-boot, msa, microservices, kotlin, jpa, hexagonal]
---

> 이 시리즈는 르무엘 아카데미(`lemuel-academy`) 를 만들면서 정리한 노트입니다. 모놀리스 한 덩어리를 4개 마이크로서비스로 쪼갠 실 사례 중심.

오늘 1일차는 **왜 쪼개나** + **첫 서비스 부트스트랩** 까지.

> 이 글에서 다루는 것
> - 모놀리스 vs 마이크로서비스 — 언제 쪼개야 하나
> - lemuel-academy 의 4개 서비스 분해 사례
> - Spring Boot 4 + Kotlin 2.0 첫 프로젝트 5분 부트스트랩
> - Hexagonal architecture 디렉토리 구조

---

## 1. 언제 쪼개야 할까

### 단일 모놀리스가 좋은 경우

- 팀 5명 이하
- 트래픽 작음 (RPS < 100)
- 도메인 경계가 흐릿함
- 배포 사이클이 일주일 이상

이런 경우 모놀리스 한 통이 압도적으로 빠릅니다. 마이크로서비스의 인프라 비용을 감당할 가치가 없어요.

### 쪼개야 할 신호

- 한 도메인이 다른 도메인 배포 때문에 막힌다
- 한 팀이 다른 팀의 코드를 너무 많이 건드린다
- 트래픽 패턴이 도메인별로 크게 다르다 (예: 영상은 자주 / 결제는 드물게)
- 리소스 요구가 다르다 (예: 영상은 GPU, 결제는 메모리)

---

## 2. lemuel-academy 의 4개 서비스 분해

```
[학생/크리에이터/관리자]
        │
        ▼
   [api-gateway :8080]   ← Spring Cloud Gateway, JWT 인증
        │
   ┌────┼─────────────┐
   ▼    ▼             ▼
[user] [catalog]   [media]
:8081   :8082      :8083
        │            │
   ┌────┴────┐   ┌────┴────┐
   ▼    ▼    ▼   ▼    ▼    ▼
 회원  강의  진도 영상 R2  ffmpeg
                    upload  worker
```

| 서비스 | 책임 | 데이터 |
|---|---|---|
| **api-gateway** | JWT 검증, 라우팅, X-User-Id 주입 | 없음 |
| **user-service** | 회원, 진도, 즐겨찾기, OAuth | users 스키마 |
| **catalog-service** | 강의/챕터/레슨/리뷰 | catalog 스키마 |
| **media-service** | 업로드/HLS/R2 + ffmpeg-worker | media 스키마 |

핵심은 **데이터를 공유하지 않는 것** — 각 서비스가 자기 스키마만 만짐. 서비스 간 통신은 webhook 또는 메시지큐.

---

## 3. Spring Boot 4 + Kotlin 첫 프로젝트

### 5분 부트스트랩

```bash
# IntelliJ → New Project → Spring Initializr (또는 https://start.spring.io)
#  - Project: Gradle (Kotlin DSL)
#  - Language: Kotlin
#  - Spring Boot: 4.0.x
#  - Java: 21
#  - Group: co.lemuel.academy
#  - Artifact: user-service
#  - Dependencies: Web, Data JPA, Validation, Flyway, PostgreSQL, Lombok 빼고
```

### 필수 + 선택 의존성

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.flywaydb:flyway-database-postgresql")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    implementation("io.jsonwebtoken:jjwt-api:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.12.6")
    runtimeOnly("org.postgresql:postgresql")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```

### Hexagonal architecture 디렉토리

```
user-service/
└── src/main/kotlin/co/lemuel/academy/user/
    ├── UserServiceApplication.kt
    ├── domain/                  ← 도메인 모델 (순수, 의존성 없음)
    │   └── User.kt
    ├── application/
    │   ├── port/in/              ← UseCase 인터페이스 (Controller 가 호출)
    │   │   └── SignUpUseCase.kt
    │   ├── port/out/             ← Repository 인터페이스 (DB 가 구현)
    │   │   └── UserRepositoryPort.kt
    │   └── service/              ← UseCase 구현
    │       └── SignUpService.kt
    └── adapter/
        ├── in/web/               ← HTTP 컨트롤러
        │   └── UserController.kt
        └── out/persistence/      ← JPA 어댑터
            ├── UserJpaEntity.kt
            └── UserJpaRepository.kt
```

핵심: **domain 은 어떤 의존성도 없어야 함.** Spring annotation 도 X. 테스트가 매우 빨라집니다.

---

## 4. 첫 엔티티 + 컨트롤러 한 통

```kotlin
// domain/User.kt
data class User(
    val id: UUID? = null,
    val email: String,
    val nickname: String,
    val role: UserRole,
    val createdAt: LocalDateTime = LocalDateTime.now(),
)

enum class UserRole { STUDENT, CREATOR, ADMIN }
```

```kotlin
// application/port/in/SignUpUseCase.kt
interface SignUpUseCase {
    fun signUp(cmd: SignUpCommand): User
}
data class SignUpCommand(val email: String, val nickname: String, val password: String)
```

```kotlin
// adapter/in/web/UserController.kt
@RestController
@RequestMapping("/api/users")
class UserController(private val signUp: SignUpUseCase) {
    @PostMapping("/signup")
    fun signUp(@RequestBody @Valid req: SignUpRequest): UserDto {
        val user = signUp.signUp(SignUpCommand(req.email, req.nickname, req.password))
        return UserDto.from(user)
    }
}
```

```bash
./gradlew bootRun
curl -X POST http://localhost:8081/api/users/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","nickname":"alice","password":"qwerty1234"}'
```

---

## 다음 학습 (7일 코스)

| Day | 주제 |
|---|---|
| 1 | 모놀리스 → MSA 분해 + 첫 서비스 (오늘) |
| 2 | API Gateway + JWT 인증 |
| 3 | JPA + Flyway + Hexagonal |
| 4 | 서비스 간 통신 (REST / Webhook / Redis Streams) |
| 5 | Testcontainers 통합 테스트 |
| 6 | 관측성 (Micrometer + Prometheus) |
| 7 | 배포 (Docker Compose → K8s) |

---

> 시리즈를 따라가시려면 `lemuel-academy` 레포가 살아있는 표본입니다 — 코드를 보면서 따라오세요.
