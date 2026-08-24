---
layout: post
title: "클린 아키텍처는 묶음 상품이다 — 한 코드베이스에서 얻는 것과 치르는 값을 따로 매겨봤다"
date: 2026-08-25 00:47:19 +0900
categories: [architecture]
tags: [clean-architecture, dependency-rule, jpa, kotlin, archunit, anemic-domain-model]
---

아키텍처 정리를 단계로 쪼개 놓고 Phase 1까지 끝낸 뒤, 다음 질문을 받았다.

> "Phase 2~3 하면 뭐가 좋지?"
> "그거 클린 아키텍처에 필요한 거야?"

두 번째 질문의 답은 짧다. **필요하다.** 그런데 그 답만 가지고 다음 단계를 시작하면 곤란해진다. "필요하다"는 규칙을 만족시키는지에 대한 답이고, 지금 물어야 하는 건 **이 코드베이스에서 그 규칙이 값을 하느냐**이기 때문이다. 이 글은 그 둘을 갈라놓고, 얻는 것과 치르는 값을 항목별로 따로 매겨본 기록이다. 대상은 공개 저장소 [MyoungSoo7/inter-asat](https://github.com/MyoungSoo7/inter-asat) — Kotlin + Spring Boot + JPA로 된 청각 훈련 백엔드다.

## 규칙 자체는 한 줄이다

Robert C. Martin이 2012년에 쓴 글에서 Dependency Rule은 이렇게 정의된다.

> "source code dependencies can only point inwards. Nothing in an inner circle can know anything at all about something in an outer circle."
> — Robert C. Martin, [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)[^1]

`domain/model` 밑의 클래스가 `jakarta.persistence.Entity`를 import하고 있으면 이 규칙 위반이다. 논쟁의 여지가 없다. 그리고 이 저장소는 그 위반을 이미 **스스로 장부에 적어두고 있다.** ArchUnit 규칙 `innerRingsMustNotDependOnJpa`의 도메인 쪽 검사가 위반자 집합이 정확히 19개 이름과 같은지를 단언한다.

```kotlin
private val DOMAIN_JPA_ALLOWANCE = arrayOf(
    "AdaptiveAlgorithmState", "AdminNotification", "AlgorithmConfigSnapshot",
    "AuditLog", "BaseEntity", /* ... 19개 ... */ "User",
)
```

이 목록은 `containsOnly` 방식이라 **새 위반이 생겨도 빨간불이고, 목록에 있는 이름이 사라져도 빨간불이다.** 줄어들 때만 손으로 지울 수 있게 만든 장부다. ArchUnit이 제공하는 `FreezingArchRule`이 위반을 파일에 기록해두고 새 위반만 보고하는 것과 목적이 같다 — 다만 프리즈는 해소되면 자동으로 줄어드는 데 반해[^2], 이쪽은 사람이 목록을 직접 지워야 해서 지운 사실이 커밋에 남는다.

중요한 건 이거다. **저 19개가 이 저장소에 남은 유일한 위반이다.** 나머지 7개 ArchUnit 규칙의 위반자 집합은 전부 `emptySet()`이다. 그러니까 "아키텍처 점수를 더 올린다"는 목표에서 손댈 수 있는 건 저것뿐이고, 그 말은 Phase 2~3이 **점수를 올리는 유일한 길**이라는 뜻이기도 하다.

## 그런데 규칙이 파는 건 묶음 상품이다

같은 글에서 Martin은 이 아키텍처가 만들어내는 속성을 다섯 개로 나열한다: **Independent of Frameworks / Testable / Independent of UI / Independent of Database / Independent of any external agency**[^1].

Phase 2~3은 이 다섯 개를 한 봉지에 담아 판다. 그래서 "필요하냐"가 아니라 **"봉지 안의 것들이 여기서 각각 얼마짜리냐"**를 물어야 한다. 하나씩 값을 매겨봤다.

### ① Independent of Database — 이 코드베이스에서는 0원

DB 교체 가능성은 봉지에서 가장 비싸 보이는 물건이다. 그런데 여기서는 이미 값이 0이다. Flyway 마이그레이션 37개 중 **12개가 PostgreSQL 전용 문법**을 쓴다 — `jsonb`, `ON CONFLICT`, `gen_random_uuid()`, `::` 캐스트, `CREATE EXTENSION`. 기준을 `TIMESTAMPTZ`까지 넓히면 15개다.

도메인 모델에서 JPA를 걷어내도 저 12개 파일은 그대로다. **DB를 못 바꾸는 이유가 도메인 모델이 아니라 스키마 자체에 박혀 있기 때문**이다. 봉지 값의 상당 부분을 차지하는 물건인데, 여기서는 이미 팔 수 없는 물건이다.

이건 추측이 아니라 최근에 직접 확인한 사실이다. 통합 테스트에 H2 폴백 분기가 있었는데, Docker 없이 돌려보니 그 경로는 **처음부터 성립할 수 없었다.** 마이그레이션을 못 돌리니 스키마를 엔티티에서 만들었고, 그러면 시드 데이터가 없어서 픽스처가 `HALLYM_RI seed missing`으로 죽었다. 실패 메시지가 원인(도커가 없다)이 아니라 증상(시드가 없다)을 가리키고 있었다. 죽은 분기를 지우고 원인을 그대로 말하고 멈추게 바꿨다.

### ② Testable — 이미 82%가 무료다

이 항목은 봉지에서 두 번째로 비싸 보인다. 실제로 재봤다. 테스트 총 321개 중 Spring 컨텍스트나 DB가 필요한 건 **7개 클래스, 58개**뿐이다.

| 구분 | 테스트 수 | 비중 |
|---|---:|---:|
| DB·Spring 없이 도는 것 | 263 | 81.9% |
| DB 또는 Spring 컨텍스트 필요 | 58 | 18.1% |

도메인 모델을 분리하면 저 58개 중 일부가 순수 단위 테스트로 내려온다. 그런데 저 58개는 컨트롤러 통합 테스트(RestAssured로 HTTP를 때리는 것)와 시나리오 테스트가 대부분이라, **도메인을 분리해도 여전히 DB가 필요하다.** 도메인 모델 자체를 검증하는 테스트는 이미 263개 쪽에 들어 있다. 이 항목도 대부분 이미 지불이 끝났다.

### ③ 복잡한 로직을 OO로 조직하기 — 조직할 로직이 없다

Martin Fowler는 빈혈 도메인 모델(Anemic Domain Model)을 두고, 그게 **"도메인 모델의 비용은 전부 치르면서 이득은 하나도 못 얻는"** 상태라고 썼다. 그 비용의 핵심으로 지목한 게 O/R 매핑 계층이고, 그 값을 치를 만한 경우는 **복잡한 로직을 OO 기법으로 조직할 때뿐**이라고 못 박았다[^3].

그래서 이 저장소의 도메인이 빈혈인지 재봤다.

| 위치 | 파일 | 줄 | 메서드 |
|---|---:|---:|---:|
| `domain/model` | 36 | 1,933 | **32** |
| `application/service` | 45 | 6,591 | — |

1,933줄에 메서드가 32개다. 나머지는 프로퍼티 선언이다. 그리고 로직의 무게중심은 서비스 쪽에 있다.

$$
\frac{\text{application/service 줄 수}}{\text{domain/model 줄 수}} = \frac{6591}{1933} \approx 3.4
$$

Fowler의 기준으로 보면 이 도메인은 빈혈이다. **분리해서 조직할 "복잡한 로직"이 도메인 안에 아직 없다.** 그러니 지금 분리하면 얻는 건 순수한 경계선이고, 남는 건 엔티티 19개 + 매퍼 19개다.

### ④ Independent of Frameworks — 여기는 값이 있다

봉지에서 유일하게 제값을 하는 물건이다. 다만 지금 아픈 방식이 좀 다르다.

## 진짜 아픈 곳은 규칙 위반이 아니었다

`main` 소스에 `!!`(Kotlin의 non-null 단언, 실패하면 NPE)가 **137개** 있다. 그중 **91개가 `id!!`** 다. 파일 하나(`ExportService.kt`)에만 38개다.

뿌리는 `BaseEntity`에 있다.

```kotlin
@MappedSuperclass
abstract class BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    var id: UUID? = null
        private set
    // ...
}
```

JPA가 id를 채워주기 전 상태를 표현해야 해서 nullable이다. 그래서 이 엔티티를 쓰는 쪽은 전부 `id!!`를 붙인다. 저장소의 CLAUDE.md에는 "NullAway를 걷어내고 Kotlin의 null 안전성에 맡긴다"고 적혀 있는데, 실제로는 **그 null 안전성을 137번 손으로 끄고 있는** 셈이다.

이게 프레임워크 의존의 진짜 비용이다. 도메인 모델이 JPA를 import하는 것 자체보다, **JPA의 생명주기가 도메인 모델의 타입을 nullable로 만들어버린 것**이 아프다.

그리고 이건 도메인을 분리하지 않고도 고칠 수 있다. Spring Data JPA 공식 문서는 이 문제를 정면으로 다룬다. `save()`는 엔티티가 새것이면 `persist()`, 아니면 `merge()`를 호출하는데, 기본 판별 전략은 **식별자 프로퍼티가 null인지를 본다.** 그래서 id를 생성자에서 직접 채우면 항상 "새것이 아님"으로 판정돼 INSERT 전에 SELECT가 한 번 나간다. 공식 처방은 `Persistable<ID>`를 구현하고 `@Transient` 플래그를 `@PostPersist`/`@PostLoad`로 뒤집는 것이다[^4].

```kotlin
@MappedSuperclass
abstract class BaseEntity(
    @Id val id: UUID = UUID.randomUUID(),
) : Persistable<UUID> {
    @Transient
    private var _isNew = true
    override fun getId() = id
    override fun isNew() = _isNew

    @PostPersist
    @PostLoad
    fun markNotNew() { _isNew = false }
}
```

이걸 하면 `id!!` 91개가 사라진다. 그리고 **이건 클린 아키텍처를 만족시키지 않는다.** `jakarta.persistence`는 여전히 도메인에 남는다. ArchUnit 허용 목록도 그대로 19개다.

## 그래서 두 개를 갈라놓아야 한다

| | 아픈 데를 고치기<br>(id non-null) | 규칙을 만족시키기<br>(Phase 2~3) |
|---|---|---|
| **얻는 것** | `!!` 137개 → 46개, `save()`의 불필요한 SELECT 제거 | Dependency Rule 준수, 허용 목록 19 → 0 |
| **비용** | `BaseEntity` + 엔티티 19개 생성자 수정 | 도메인 클래스 19 + 매퍼 19 신설, 서비스 전면 수정 |
| **DB 교체 가능성** | 변화 없음 | 변화 없음 (마이그레이션 12개가 PG 전용) |
| **테스트 개선** | 없음 | 58개 중 일부 (263개는 이미 무료) |
| **아키텍처 점수** | 오르지 않음 | 오름 (유일한 경로) |

두 열은 서로를 대체하지 않는다. 왼쪽은 규칙을 하나도 만족시키지 못하고, 오른쪽은 `id!!`를 하나도 없애지 못한다. 분리된 도메인 모델도 여전히 id를 어딘가에서 받아야 하기 때문이다.

## 순서는 정해져 있다

그런데 **어느 걸 먼저 하느냐는 정해져 있다.** id 먼저다.

분리된 도메인 모델은 어차피 id를 생성자에서 받는 형태가 된다. Phase 2~3을 먼저 하면 매퍼를 만들면서 nullable id를 그대로 들고 건너간 다음, 나중에 같은 자리를 또 고쳐야 한다. **같은 곳을 두 번 편집하게 된다.** 반대로 id를 먼저 정리해두면, 나중에 도메인을 분리할 때 그 생성자를 그대로 옮기면 된다.

## 정리

규칙은 묶음으로 팔린다. 그 묶음이 좋은 물건인 건 맞지만, **각 물건의 값은 코드베이스마다 다르다.** 이 저장소에서는

- DB 독립성은 스키마가 이미 PostgreSQL에 묶여 있어서 **0원**,
- 테스트 용이성은 이미 **82%가 지불 완료**,
- 복잡한 로직 조직화는 도메인이 빈혈이라 **조직할 로직이 아직 없고**,
- 프레임워크 독립성만 값을 하는데, 그마저도 **아픈 지점이 import가 아니라 nullable id**였다.

그래서 답은 "Phase 2~3은 클린 아키텍처에 필요하다. 다만 지금 사면 봉지 안의 넷 중 하나만 쓴다"이다. 그리고 그 하나는 훨씬 싼 값에 따로 살 수 있다.

아키텍처 규칙을 따를지 말지가 아니라, **규칙이 파는 물건을 하나씩 내 가격표에 붙여보는 것.** 재보기 전까지는 "필요하다"와 "값을 한다"가 같은 말처럼 들린다.

---

## References

[^1]: Robert C. Martin, "The Clean Architecture", *The Clean Code Blog*, 2012-08-13. <https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html>
[^2]: ArchUnit User Guide, "Freezing Arch Rules". <https://www.archunit.org/userguide/html/000_Index.html>
[^3]: Martin Fowler, "AnemicDomainModel", 2003-11-25. <https://martinfowler.com/bliki/AnemicDomainModel.html>
[^4]: Spring Data JPA Reference Documentation, "Persisting Entities" 및 Spring Data Commons, "Entity State Detection Strategies". <https://docs.spring.io/spring-data/jpa/reference/jpa/entity-persistence.html> · <https://docs.spring.io/spring-data/commons/reference/is-new-state-detection.html>

본문의 수치(테스트 321/58, `!!` 137/91, 마이그레이션 37/12, 도메인 36파일 1,933줄 32메서드 대 서비스 45파일 6,591줄)는 2026-08-25 기준 [inter-asat](https://github.com/MyoungSoo7/inter-asat) `main`에서 직접 세어 얻은 값이다. 마이그레이션의 "PostgreSQL 전용" 판정은 `jsonb` · `ON CONFLICT` · `gen_random_uuid` · `::` 캐스트 · `CREATE EXTENSION` 출현을 기준으로 했고, 기준에 따라 숫자가 달라질 수 있어 본문에 넓힌 경우(15개)도 함께 적었다.
