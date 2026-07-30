---
layout: post
title: "*Pact 없이 만드는 내부 REST 계약 테스트* — *정본 샘플 하나* 로 프로듀서·컨슈머 드리프트를 빌드 시점에 잡기"
date: 2026-07-31 07:00:00 +0900
categories: [java, spring, testing, architecture]
tags:
  [
    ContractTest,
    ConsumerDrivenContracts,
    Pact,
    Jackson,
    Gradle,
    TestFixtures,
    SpringBoot,
    MSA,
    RestClient,
  ]
---

# 목킹된 계약은 계약이 아니다

MSA 에서 서비스 A 가 서비스 B 의 REST API 를 호출한다. A 쪽 테스트는 어떻게 쓰는가? 대개 이렇다.

```java
// A 의 테스트 — B 의 응답을 목킹한다
mockServer.expect(requestTo("/api/b/resource"))
          .andRespond(withSuccess("""
              { "code": "X", "payload": { "amount": "1000" } }
              """, APPLICATION_JSON));
```

이 테스트는 통과한다. 영원히 통과한다. **B 가 무슨 응답을 주든 상관없이.**

목킹한 JSON 이 B 의 실제 응답과 같다는 보장이 어디에도 없기 때문이다. 그리고 그 JSON 을 쓴 사람은 대개 A 의 개발자다. 즉 **A 가 "B 는 이렇게 생겼을 것"이라고 상상한 내용을, A 가 검증한다.** Martin Fowler 가 [Integration Test](https://martinfowler.com/bliki/IntegrationTest.html) 에서 정확히 지적한 문제다:

> An obvious catch with integration testing against a double is whether that double is truly faithful. But we can test that separately using ContractTests.

나는 이 함정에 정확히 빠졌고, 그 결과를 프로덕션에서 확인했다. [별도의 글](/2026/07/31/silent-failure-three-layers/)에 사고 경위를 정리했으니 여기서는 요약만 한다.

- 컨슈머 DTO: `code` / `payload` / `LocalDateTime`
- 프로듀서 실제: `sourceCode` / `data` / `Instant`
- Spring Boot 의 Jackson 은 모르는 필드를 조용히 버린다 → **`payload` 는 항상 `null`**
- 담보 실거래가가 **한 번도 읽히지 않고** 매번 신청인 제시값으로 폴백
- 테스트는 컨슈머가 지어낸 스키마를 목킹해서 **계속 초록불**

이 글은 그 재발을 막기 위해 넣은 장치를 그대로 옮긴다. Pact 도 Spring Cloud Contract 도 쓰지 않는, **정본 샘플 JSON 한 개 + 양쪽에 테스트 한 개씩**의 소박한 버전이다.

---

# 설계 — 정본 샘플을 단일 출처로

핵심 아이디어는 한 문장이다.

> **프로듀서와 컨슈머가 같은 JSON 파일을, 각자의 record 로, 엄격 모드로 읽는다.**

세 조건이 다 필요하다.

1. **같은 파일** — 파일이 둘이면 다시 두 개의 상상이 된다
2. **각자의 record** — 양쪽이 자기 타입으로 읽어야 어느 쪽이 어긋났는지 드러난다
3. **엄격 모드** — 관대하면 어긋나도 통과한다 (뒤에서 자세히)

```
                shared-common/src/testFixtures/resources/
                  contracts/internal-rest/common-data/records.sample.json
                                    │
                 ┌──────────────────┴──────────────────┐
                 │            같은 파일                │
                 ▼                                     ▼
   common-data (프로듀서)                       loan (컨슈머)
   DataRecordsRestContractTest             CommonDataRecordsRestContractTest
   → RecordsResponse 로 읽는다              → RecordsDto 로 읽는다
```

어느 한쪽이 필드를 개명·제거하면 **반대편 빌드가 깨진다.** 그게 전부다.

이 방향성은 Ian Robinson 의 [Consumer-Driven Contracts](https://martinfowler.com/articles/consumerDrivenContracts.html) 가 제시한 것과 같다. 그 글은 계약을 표현하는 형식을 규정하지 않고, 오히려 이렇게 열어 둔다:

> Contracts may be expressed and structured in several ways. In their simplest form, consumer expectations can be captured in a spreadsheet or similar document... By going a little further and introducing unit tests that assert each expectation, we can ensure that contracts are described and enforced in a repeatable, automated fashion with each build.

여기서 하는 게 정확히 그 "a little further" 단계다.

---

# 구현 1 — 정본 샘플을 공유 모듈의 testFixtures 에 둔다

샘플 JSON 을 어디에 두느냐가 첫 결정이다. 프로듀서 리포에 두면 컨슈머가 못 읽고, 각자 복사하면 단일 출처가 깨진다.

Gradle 의 `java-test-fixtures` 플러그인이 이 문제를 위해 있다. [Gradle 사용자 매뉴얼](https://docs.gradle.org/current/userguide/java_testing.html)의 설명:

> Test fixtures are not limited to a single project. It is often the case that a dependent project tests also needs the test fixtures of the dependency. This can be achieved very easily using the `testFixtures` keyword.

공유 모듈에 플러그인을 적용하고,

```kotlin
// shared-common/build.gradle.kts
plugins {
    `java-library`
    `java-test-fixtures`   // 계약(contract-as-code) 스키마·검증기·정본 샘플 제공
    `maven-publish`
}
```

샘플을 그 소스셋의 리소스로 둔다.

```
shared-common/src/testFixtures/resources/contracts/internal-rest/
├── common-data/
│   └── records.sample.json
└── recon/
    ├── daily-totals.sample.json
    ├── captured-payments.sample.json
    └── ...
```

소비하는 쪽은 한 줄이다.

```kotlin
// common-data-service/build.gradle.kts, loan-service/build.gradle.kts 양쪽 모두
dependencies {
    // REST 계약 정본 샘플 — 컨슈머(loan)와 같은 샘플을 본다
    testImplementation(testFixtures("github.lms.lemuel:shared-common:1.0.0"))
}
```

`testFixtures(...)` 로 선언하면 그 모듈의 `testFixtures` 소스셋 산출물이 테스트 클래스패스에 올라온다. 프로덕션 클래스패스는 오염되지 않는다. 정본 샘플은 **테스트에서만 보이는 자산**이다.

> 참고: 이 프로젝트는 `maven-publish` 도 함께 쓴다. Gradle 문서가 적듯 test fixtures 는 `test-fixtures` classifier 로 발행되므로, 서비스들이 별도 빌드로 갈려도 좌표(`group:artifact:version`)로 같은 샘플을 참조할 수 있다.

## 샘플은 "예쁜 예시"가 아니라 정본이어야 한다

```json
{
  "sourceCode": "molit-apt-trade",
  "count": 2,
  "records": [
    {
      "recordKey": "11680-래미안-2026-05",
      "collectedAt": "2026-06-01T00:00:00Z",
      "data": {
        "dealAmount": "79,000",
        "aptNm": "래미안",
        "excluUseAr": "84.98"
      }
    },
    {
      "recordKey": "11680-래미안-2026-06",
      "collectedAt": "2026-07-01T00:00:00Z",
      "data": {
        "dealAmount": "84,000",
        "aptNm": "래미안",
        "excluUseAr": "84.98"
      }
    }
  ]
}
```

여기서 의도적으로 넣은 것들이 있다.

- **`"79,000"` — 콤마 박힌 문자열.** 국토부 실거래가 원문이 그렇다. 숫자로 예쁘게 적었으면 파싱 코드의 콤마 처리 경로가 검증되지 않는다.
- **`"...T00:00:00Z"` — `Z` 붙은 Instant 표기.** 이게 컨슈머의 `LocalDateTime` 을 깨뜨린 바로 그 지점이다. 타임존 표기를 뺀 샘플이었으면 이 버그는 안 잡혔다.
- **`data` 안의 잡다한 필드들(`aptNm`, `excluUseAr`).** 프로듀서가 실제로 흘려보내는 원문 구조. 컨슈머가 `dealAmount` 만 쓰더라도 샘플에는 있어야 한다.
- **레코드 2건.** "최신 것을 고른다"는 로직이 있으므로 1건이면 정렬 경로가 안 돈다.

> 샘플이 실제 응답보다 깨끗하면, 그 차이만큼 계약 테스트가 놓친다.
> **프로덕션 응답을 캡처해서 넣는 게 가장 안전하다.** Fowler 가 [Contract Test](https://martinfowler.com/bliki/ContractTest.html) 에서 언급한 `SelfInitializingFake` 접근과 같은 취지다 — "Often a stub will snapshot a response."

---

# 구현 2 — 양쪽에 테스트를 하나씩

## 컨슈머측

```java
@DisplayName("common-data /records REST 계약 — 컨슈머(담보평가 어댑터 record)측")
class CommonDataRecordsRestContractTest {

    private static final JsonMapper MAPPER = JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .build();

    private static SatelliteCollateralValuationAdapter.RecordsDto readSample() {
        try (InputStream in = CommonDataRecordsRestContractTest.class.getResourceAsStream(
                "/contracts/internal-rest/common-data/records.sample.json")) {
            assertThat(in).as("정본 샘플 존재").isNotNull();
            return MAPPER.readValue(in, SatelliteCollateralValuationAdapter.RecordsDto.class);
        } catch (IOException e) {
            throw new AssertionError("계약 샘플 역직렬화 실패", e);
        }
    }

    @Test
    @DisplayName("정본 샘플이 어댑터 record 로 읽히고 모든 필드가 채워진다")
    void canonicalSampleDeserializes() {
        var dto = readSample();

        assertThat(dto.sourceCode()).isEqualTo("molit-apt-trade");
        assertThat(dto.count()).isEqualTo(2);
        assertThat(dto.records()).hasSize(2);

        var first = dto.records().get(0);
        assertThat(first.recordKey()).isEqualTo("11680-래미안-2026-05");
        // collectedAt 이 Instant 여야 한다 — LocalDateTime 이면 'Z' 때문에 역직렬화 자체가 깨진다.
        assertThat(first.collectedAt()).isNotNull();
        // data(구 payload) 가 채워져야 실거래가가 실제로 쓰인다. null 이면 조용히 제시값 폴백이다.
        assertThat(first.data()).isInstanceOf(Map.class);
        assertThat(asMap(first.data())).containsEntry("dealAmount", "79,000");
    }
}
```

## 프로듀서측

```java
@DisplayName("/api/common-data/sources/{code}/records REST 계약 — 프로듀서측")
class DataRecordsRestContractTest {

    private static final JsonMapper MAPPER = JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .build();

    @Test
    @DisplayName("정본 샘플 ↔ RecordsResponse record 호환")
    void recordsSampleMatchesResponseRecord() {
        var v = read("records.sample.json", DataSourceController.RecordsResponse.class);

        assertThat(v.sourceCode()).isEqualTo("molit-apt-trade");
        assertThat(v.count()).isEqualTo(2);
        assertThat(v.records()).hasSize(2);
        // ...
    }
}
```

거의 같은 코드다. 그게 의도다. **양쪽이 같은 샘플을 각자의 타입으로 읽을 수 있는가** — 검증하는 명제가 그것뿐이기 때문이다.

## 컨슈머 record 의 가시성을 열어야 한다

작은 실무 포인트. 원래 어댑터의 DTO 는 `private record` 였다.

```java
private record RecordsDto(String code, List<RecordDto> records) { }
```

계약 테스트가 그 타입을 참조해야 하므로 패키지 프라이빗으로 열었다.

```java
record RecordsDto(String sourceCode, int count, List<RecordDto> records) { }
```

"테스트를 위해 가시성을 넓히는 건 나쁘다"는 반론이 가능한데, 여기서는 **계약이 캡슐화 대상이 아니다**. 이 record 의 모양은 어댑터의 내부 구현이 아니라 **두 서비스가 합의한 외부 계약**이고, 그 사실을 타입 시스템에도 드러내는 게 맞다. 같은 패키지 안으로만 열었으므로 노출 범위도 최소다.

---

# 핵심 — 매퍼를 Spring 에서 가져오면 안 된다

이 장치 전체가 **딱 한 줄**에 걸려 있다.

```java
private static final JsonMapper MAPPER = JsonMapper.builder()
        .addModule(new JavaTimeModule())
        .build();
```

`@Autowired ObjectMapper` 를 쓰고 싶어진다. "프로덕션과 같은 매퍼로 테스트해야 정확하지 않나?" 정반대다.

Jackson 자체의 기본값은 **엄격**하다. [`DeserializationFeature` javadoc](https://javadoc.io/static/com.fasterxml.jackson.core/jackson-databind/2.19.1/com/fasterxml/jackson/databind/DeserializationFeature.html):

> **`FAIL_ON_UNKNOWN_PROPERTIES`** — Feature is enabled by default (meaning that a `JsonMappingException` will be thrown if an unknown property is encountered).

그런데 Spring 이 만들어 주는 매퍼는 이걸 끈다. [`Jackson2ObjectMapperBuilder` javadoc](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/converter/json/Jackson2ObjectMapperBuilder.html) 의 커스터마이즈 목록:

> - `MapperFeature.DEFAULT_VIEW_INCLUSION` is disabled
> - `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` is disabled

Spring Boot 레퍼런스의 [Customize the Jackson ObjectMapper](https://docs.spring.io/spring-boot/3.3/how-to/spring-mvc.html) 에도 같은 목록이 있다.

그러니 Spring 의 매퍼로 계약 테스트를 쓰면, **샘플에 있고 record 에 없는 필드가 조용히 버려진다.** 정확히 우리를 물었던 그 동작이 테스트 안에서 재현되는 것이다. 계약 테스트가 계약 위반을 통과시킨다.

정리하면 **비대칭이 의도된 설계**다.

|               | 매퍼                   | `FAIL_ON_UNKNOWN_PROPERTIES` | 이유                                           |
| ------------- | ---------------------- | ---------------------------- | ---------------------------------------------- |
| 프로덕션 경로 | Spring 자동 구성       | 꺼짐 (관용)                  | 프로듀서가 필드를 **추가** 해도 안 깨져야 한다 |
| 계약 테스트   | 직접 만든 `JsonMapper` | 켜짐 (엄격)                  | 필드 **개명·제거** 를 빌드 시점에 잡아야 한다  |

`@JsonIgnoreProperties(ignoreUnknown = true)` 는 어떤가? 이건 애노테이션이라 매퍼 설정과 무관하게 따라온다 — [javadoc](https://fasterxml.github.io/jackson-annotations/javadoc/2.13/com/fasterxml/jackson/annotation/JsonIgnoreProperties.html) 이 "ignored **without warnings** ... without exception" 이라고 못박는다. 그래서 이 방식은 **"샘플에 있는 필드가 record 에 없을 때"** 를 잡는 데는 한계가 있다.

그럼 무엇을 잡는가? 실전에서 훨씬 자주 터지는 두 가지를 잡는다.

- **필드 개명·제거** — `assertThat(dto.sourceCode()).isEqualTo(...)` 가 `null` 로 깨진다
- **타입 불일치** — `Instant` ↔ `LocalDateTime` 처럼 파싱 자체가 예외로 터진다

우리 사고의 세 원인(`code`↔`sourceCode`, `payload`↔`data`, `LocalDateTime`↔`Instant`) 중 **셋 다** 이 단언들에 걸린다. 그래서 충분했다.

더 엄격하게 가려면 record 에서 `@JsonIgnoreProperties` 를 떼고 매퍼의 기본 엄격 모드에만 의존하면 된다. 다만 그러면 프로듀서의 **필드 추가** 마저 컨슈머 빌드를 깨뜨리므로, 관용성과 엄격성 사이에서 선택해야 한다. 우리는 관용 쪽을 택했다 — 내부 서비스라 필드 추가가 잦기 때문이다.

---

# 어디까지 이걸로 충분한가

정직하게 한계를 적는다.

**이 방식이 검증하지 않는 것:**

- **프로듀서가 정말 그 샘플대로 응답하는지** — 샘플 ↔ record 호환만 본다. 프로듀서 컨트롤러가 그 record 를 실제로 그 엔드포인트에서 반환하는지는 별도의 웹 계층 테스트 몫이다.
- **런타임 값의 의미** — `dealAmount` 가 만원 단위인지 원 단위인지는 스키마가 말해주지 않는다.
- **HTTP 계약** — 상태 코드, 헤더, 에러 응답 형식.
- **버저닝** — 프로듀서가 v2 를 내보내며 v1 을 유지하는 시나리오.

**Pact 로 올라가야 할 때:**

- 프로듀서·컨슈머가 **다른 팀·다른 리포·다른 릴리즈 사이클** 일 때. [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) 가 설명하듯 CDC 의 진짜 가치는 "컨슈머가 자기 기대를 publish 하고 프로듀서가 그걸 fetch 해서 자기 빌드에서 돌리는" 흐름에 있다. 한 리포 안이면 그 인프라가 필요 없다.
- 컨슈머가 **여럿** 일 때. 정본 샘플 하나로는 "누가 어떤 필드를 실제로 쓰는지" 를 표현할 수 없다.

우리 경우는 한 모노리포 안의 내부 서비스 간이라 이 정도가 비용 대비 맞았다. **Pact 를 도입할 시간이 없어서 아무것도 안 하는 것보다는, 30분짜리 정본 샘플 테스트가 낫다.** 실제로 이 장치는 같은 리포에서 이미 정산 대사(`/internal/recon`) 경계에 먼저 도입돼 있었고, 이번에 담보평가 경계로 확장한 것이다.

---

# 체크리스트

새 내부 REST 호출을 추가할 때 쓰는 목록으로 정리한다.

- [ ] 프로듀서의 **실제 응답을 캡처**해서 정본 샘플로 저장했는가 (예쁘게 다듬지 않았는가)
- [ ] 샘플이 공유 모듈 `testFixtures` 에 있고, **양쪽이 `testFixtures(...)` 로 같은 파일**을 보는가
- [ ] 계약 테스트가 **Spring 매퍼가 아닌 직접 만든 `JsonMapper`** 를 쓰는가
- [ ] 샘플에 **까다로운 실제값**이 들어 있는가 (콤마 문자열, 타임존 표기, 다건, 잡다한 부가 필드)
- [ ] 컨슈머 테스트가 필드 **존재** 뿐 아니라 **값**까지 단언하는가 (`isNotNull()` 만으로는 `payload` 가 `null` 이던 버그를 못 잡는다)
- [ ] 이 호출이 실패했을 때 **폴백하는가?** 그렇다면 그 폴백은 **계량되고 있는가**

마지막 항목이 가장 중요하다. 계약 테스트는 **빌드 시점** 의 방어선이고, 폴백 지표는 **런타임** 의 방어선이다. 둘은 대체재가 아니다. 계약 테스트가 있어도 설정이 틀려 상대에게 닿지 못하면 똑같이 조용히 폴백하는데, 그건 [다른 글](/2026/07/31/silent-failure-three-layers/)의 주제다.

---

## References

**계약 테스트 이론**

- Ian Robinson, [Consumer-Driven Contracts: A Service Evolution Pattern](https://martinfowler.com/articles/consumerDrivenContracts.html) (martinfowler.com, 2006)
- Martin Fowler, [Contract Test](https://martinfowler.com/bliki/ContractTest.html) (2011, 2018 개정)
- Martin Fowler, [Integration Test](https://martinfowler.com/bliki/IntegrationTest.html)
- Ham Vocke, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) (martinfowler.com, 2018) — Consumer / Provider 테스트 실전 예제

**Jackson**

- [`DeserializationFeature` javadoc (jackson-databind 2.19.1)](https://javadoc.io/static/com.fasterxml.jackson.core/jackson-databind/2.19.1/com/fasterxml/jackson/databind/DeserializationFeature.html)
- [`@JsonIgnoreProperties` javadoc (jackson-annotations 2.13)](https://fasterxml.github.io/jackson-annotations/javadoc/2.13/com/fasterxml/jackson/annotation/JsonIgnoreProperties.html)

**Spring**

- [Spring Boot — Customize the Jackson ObjectMapper](https://docs.spring.io/spring-boot/3.3/how-to/spring-mvc.html)
- [`Jackson2ObjectMapperBuilder` javadoc (Spring Framework)](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/converter/json/Jackson2ObjectMapperBuilder.html)

**Gradle**

- [Testing in Java & JVM projects — Using test fixtures](https://docs.gradle.org/current/userguide/java_testing.html)
- [`JavaTestFixturesPlugin` javadoc](https://docs.gradle.org/current/javadoc/org/gradle/api/plugins/JavaTestFixturesPlugin.html)

**면책**: 코드 예시는 필자가 운영하는 개인 프로젝트에서 발췌·축약한 것이다. 인용한 라이브러리 동작은 모두 공식 문서·javadoc 으로 확인 가능하나 특정 버전 기준이므로, 사용 중인 버전의 문서를 확인하기 바란다. Pact 등 CDC 도구와의 비교는 필자의 프로젝트 맥락(단일 모노리포·단일 개발자)에서의 판단이며 일반적 권고가 아니다.
