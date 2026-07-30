---
layout: post
title: "*초록불인데 프로덕션에선 한 번도 안 돌았다* — 계약 · 설정 · 관측, *조용히 실패하는 세 층* 과 그걸 드러내는 법"
date: 2026-07-31 07:00:00 +0900
categories: [operations, spring, kubernetes, observability]
tags:
  [
    Jackson,
    ContractTest,
    SpringBoot,
    RelaxedBinding,
    Kubernetes,
    Helm,
    Micrometer,
    Prometheus,
    ServiceMonitor,
    FailOpen,
    SilentFailure,
    MSA,
  ]
---

# 에러 로그 0건, 알림 0건, 그리고 한 번도 안 돌아간 코드

하루 사이에 자체 운영 중인 정산·대출 MSA 에서 세 건을 잡았다. 증상은 제각각인데 성질이 똑같았다.

- 담보평가 어댑터가 **응답을 파싱한 적이 없다** — 그런데 예외 0건
- 그 어댑터가 **애초에 상대 서비스에 닿은 적이 없다** — 그런데 예외 0건
- 정산 정합성 지표가 **Prometheus 에 들어온 적이 없다** — 그런데 알림 0건

셋 다 "고장났다"는 신호를 아무 데도 남기지 않았다. 테스트는 초록불이었고, 파드는 `Healthy` 였고, ArgoCD 는 `Synced` 였다. 대시보드상으로는 완벽하게 정상인 시스템이 **핵심 기능을 하나도 수행하지 않고 있었다.**

이 글은 그 세 건을 층으로 나눠 보고, "왜 조용했는가"의 공통 구조와 각 층에서 소리가 나게 만드는 방법을 정리한다.

---

# 1층 — 계약: 컨슈머가 프로듀서의 스키마를 지어냈다

## 무슨 일이 있었나

대출 서비스(`loan-service`)의 담보평가 어댑터는 주택 담보를 평가할 때 공공데이터 커넥터(`common-data-service`)의 실거래가를 조회한다. 컨슈머 쪽 DTO 는 이렇게 생겼었다.

```java
// BEFORE — 컨슈머(loan)가 "이렇게 생겼겠지" 하고 지어낸 스키마
private record RecordsDto(String code, List<RecordDto> records) { }

@JsonIgnoreProperties(ignoreUnknown = true)
private record RecordDto(String recordKey, LocalDateTime collectedAt, Map<String, Object> payload) { }
```

그런데 프로듀서가 실제로 내려주는 것은 이랬다.

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
    }
  ]
}
```

세 군데가 어긋나 있다.

| 프로듀서                    | 컨슈머가 기대한 것 | 결과            |
| --------------------------- | ------------------ | --------------- |
| `sourceCode`                | `code`             | 무시됨          |
| `data`                      | `payload`          | **항상 `null`** |
| `Instant` (`...T00:00:00Z`) | `LocalDateTime`    | 역직렬화 파괴   |

`payload` 가 항상 `null` 이니 거래금액을 뽑는 코드는 매번 `null` 을 받고, 어댑터는 "데이터 없음"으로 판단해 **신청인이 제시한 담보가액을 그대로 인정**했다. 담보 대출에서 이건 단순 버그가 아니라 **과소평가된 담보로 승인이 나가는 리스크**다.

## 왜 예외가 안 났나 — Jackson 기본값과 Spring Boot 기본값이 반대다

여기가 핵심이다. Jackson 자체의 기본값은 **모르는 필드를 만나면 예외를 던지는 것**이다. `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` 의 javadoc 은 명시한다 — ["Feature is enabled by default (meaning that a `JsonMappingException` will be thrown if an unknown property is encountered)."](https://javadoc.io/static/com.fasterxml.jackson.core/jackson-databind/2.19.1/com/fasterxml/jackson/databind/DeserializationFeature.html)

그런데 Spring 이 만들어 주는 매퍼는 그 기본값을 **뒤집는다.** `Jackson2ObjectMapperBuilder` 의 javadoc 은 커스터마이즈 목록을 이렇게 적어 둔다 — ["`MapperFeature.DEFAULT_VIEW_INCLUSION` is disabled / `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` is disabled"](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/converter/json/Jackson2ObjectMapperBuilder.html). Spring Boot 레퍼런스의 [Customize the Jackson ObjectMapper](https://docs.spring.io/spring-boot/3.3/how-to/spring-mvc.html) 절에도 같은 목록이 있다.

즉 **Spring Boot 위에서 REST 클라이언트를 쓰는 순간, "모르는 필드는 조용히 버린다"가 기본 동작이다.** 여기에 컨슈머가 `@JsonIgnoreProperties(ignoreUnknown = true)` 까지 붙였으니 — 이 애노테이션의 javadoc 표현대로 ["all properties that are unrecognized ... are ignored **without warnings** ... without exception"](https://fasterxml.github.io/jackson-annotations/javadoc/2.13/com/fasterxml/jackson/annotation/JsonIgnoreProperties.html) — 이중으로 침묵한다.

`ignoreUnknown = true` 는 원래 **관용(tolerant reader)** 을 위한 장치다. 프로듀서가 필드를 _추가_ 해도 컨슈머가 안 깨지게 하는 것. Ian Robinson 은 [Consumer-Driven Contracts](https://martinfowler.com/articles/consumerDrivenContracts.html) 에서 이 전략을 "just enough" validation 이라 부르며, 프로듀서 계약 변경으로부터 컨슈머를 보호하는 두 전략 중 하나로 소개한다. 문제는 같은 글이 지적하는 바로 그 한계다 — 이런 완충 장치는 **컨슈머를 보호하지만, 어느 쪽에도 "지금 무엇이 실제로 쓰이고 있는지"를 알려주지 않는다.**

필드 _추가_ 에 관용적인 설정은, 필드 _이름이 다른_ 상황에서도 똑같이 관용적이다. 그리고 후자는 관용이 아니라 **데이터 유실**이다.

## 테스트는 왜 못 잡았나

기존 테스트는 있었고 통과했다. 무엇을 목킹했는지가 문제였다.

```java
// 기존 테스트가 목킹한 JSON — 컨슈머가 지어낸 스키마 그대로
{ "code": "...", "records": [ { "payload": { "dealAmount": "79,000" } } ] }
```

**어댑터가 지어낸 스키마를 그대로 목킹했다.** 그러니 어댑터는 자기 상상 속 세계에서는 완벽하게 동작했고, 테스트는 그 상상을 검증했다. Martin Fowler 가 [Contract Test](https://martinfowler.com/bliki/ContractTest.html) 에서 지적하는 함정이 정확히 이것이다 — 테스트 더블을 상대로 한 테스트는 "그 더블이 진짜 서비스와 같은가"를 검증하지 못한다. 그가 [Integration Test](https://martinfowler.com/bliki/IntegrationTest.html) 에서 쓴 표현대로, "An obvious catch with integration testing against a double is whether that double is truly faithful. But we can test that separately using ContractTests."

## 어떻게 고쳤나 — 양측이 같은 정본 샘플을 읽게 한다

DTO 를 실제 계약에 맞춘 것은 당연한 수정이고, 재발 방지 장치가 본론이다.

**정본 샘플 하나**를 공유 모듈의 testFixtures 에 둔다.

```
shared-common/src/testFixtures/resources/contracts/internal-rest/common-data/records.sample.json
```

그리고 **프로듀서와 컨슈머가 각자의 record 로 그 같은 파일을 읽는 테스트**를 양쪽에 둔다.

```java
// 컨슈머(loan)측
private static final JsonMapper MAPPER = JsonMapper.builder()
        .addModule(new JavaTimeModule())
        .build();   // ← Spring 의 매퍼가 아니다. FAIL_ON_UNKNOWN_PROPERTIES 가 켜져 있다.

SatelliteCollateralValuationAdapter.RecordsDto dto =
        MAPPER.readValue(in, SatelliteCollateralValuationAdapter.RecordsDto.class);

assertThat(dto.sourceCode()).isEqualTo("molit-apt-trade");
// data(구 payload) 가 채워져야 실거래가가 실제로 쓰인다. null 이면 조용히 제시값 폴백이다.
assertThat(first.data()).isInstanceOf(Map.class);
assertThat(asMap(first.data())).containsEntry("dealAmount", "79,000");
```

포인트는 **`JsonMapper.builder()` 로 맨 매퍼를 쓴다**는 것이다. Spring 이 주는 매퍼를 쓰면 `FAIL_ON_UNKNOWN_PROPERTIES` 가 꺼져 있어 드리프트를 다시 놓친다. 프로덕션 경로는 관용적이되, **계약 테스트만은 엄격해야 한다.** 어느 한쪽이 필드를 개명·제거하면 반대편 빌드가 깨진다.

이건 Pact 같은 도구 없이 만든 소박한 버전이다. 한 리포 안의 내부 서비스 간에는 이 정도로 충분했다. 팀·리포가 갈리면 [Consumer-Driven Contract 도구](https://martinfowler.com/articles/practical-test-pyramid.html)로 올라가는 게 맞다.

## 그리고 폴백을 계량한다

가장 중요한 교훈. 이 어댑터의 폴백은 **의도된 설계**였다. 평가 조달 실패가 대출 신청 자체를 막으면 안 되니까(가용성 우선). 그 판단 자체는 옳다. 틀린 건 **그 폴백이 조용했다는 것**이다.

```java
private BigDecimal fallback(ValuationClaim claim, String reason) {
    meterRegistry.counter("loan.collateral.valuation.fallback",
            "type", claim.type().name(), "reason", reason).increment();
    return claim.declaredValue();
}
```

`reason` 은 `no_market_ref`, `no_quote`, `fetch_failed`, `no_records`, `no_match`, `source_not_configured` 로 나뉜다. Micrometer 문서가 [메터의 식별](https://docs.micrometer.io/micrometer/reference/concepts/meters.html)에 대해 쓰듯 "A meter is uniquely identified by its name and dimensions" — 태그를 나눠 둬야 `no_match` 가 계속 오르는지(계약 드리프트) `fetch_failed` 가 오르는지(네트워크·설정)를 사후에 구분할 수 있다.

한 가지 주의. `registry.counter(...).increment()` 는 **첫 증가 시점에 등록**된다. 즉 **폴백이 한 번도 안 일어나면 `/actuator/prometheus` 에 그 지표 라인 자체가 없다.** "지표가 안 보인다"를 "배포가 안 됐다"로 오독하기 쉬운 지점이라, 배포 검증은 지표 존재가 아니라 이미지 digest 교체로 해야 한다.

### 코드리뷰가 잡아준 것 — 관측 장치가 스스로 오탐 소스가 될 뻔했다

첫 구현은 `marketRef`(조회 키) 부재 가드를 타입 분기보다 **앞에** 뒀다.

```java
// 처음 쓴 것 — 틀렸다
if (claim.marketRef() == null || claim.marketRef().isBlank()) {
    return fallback(claim, "no_market_ref");   // ← 예금·채권·보증서까지 여기로 들어온다
}
return switch (claim.type()) { ... };
```

예금·채권·보증서는 **서류값이 정본**이라 `marketRef` 가 없는 게 정상이다. 이 순서면 정상 트래픽이 전부 폴백 카운터를 올려, 방금 만든 관측 장치가 그 자체로 오탐 소스가 된다. 타입 분기를 먼저 하고, 조회 키 부재는 **외부 평가가 실제로 필요한 유형 안에서만** 계량하도록 고쳤다.

> 폴백을 계량하기로 했다면 "무엇이 폴백이 아닌지"를 먼저 정의해야 한다. 정상 경로가 섞여 들어간 지표는 없느니만 못하다 — 노이즈 때문에 아무도 안 보게 되니까.

---

# 2층 — 설정: 코드를 고쳐도 그 코드에 도달하지 못한다

## 배포는 됐는데

위 수정을 머지하고, 이미지 빌드가 끝난 걸 확인하고, 파드를 재기동했다. digest 도 바뀌었다. 기동 로그도 깨끗했다.

그리고 확인 삼아 파드 안에서 실제 호출 경로를 찔러 봤다.

```
$ kubectl -n settlement-prod exec $POD -- \
    curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 http://localhost:8094/actuator/health
000
command terminated with exit code 7        # curl(7) = Failed to connect
```

`localhost:8094`. 어댑터의 `@Value` 기본값이었다.

```java
@Value("${app.loan.market.base-url:http://localhost:8094}") String marketBaseUrl,
@Value("${app.loan.commondata.base-url:http://localhost:8098}") String commonDataBaseUrl,
```

`application.yml` 에는 `${APP_LOAN_MARKET_BASE_URL:http://localhost:8094}` 형태로 환경변수 자리가 **제대로 뚫려 있었다.** 그런데 Helm 차트의 loan 서비스 `extraEnv` 에는 그 변수가 **하나도 없었다.**

```
$ kubectl -n settlement-prod exec $POD -- env | grep -E 'APP_LOAN|BASE_URL'
(출력 없음)
```

로컬 개발 편의를 위한 기본값이 프로덕션에서 그대로 살아 있었다. 파드가 **자기 자신의 8094 포트**를 찔렀고, 아무도 안 듣고 있었고, 어댑터는 `RestClientException` 을 삼키고 폴백했다.

위성 서비스들은 멀쩡히 살아 있었다. loan 이 주소를 몰랐을 뿐이다.

```
$ kubectl -n settlement-prod exec $POD -- \
    curl -s --max-time 8 "http://settlement-market:8094/api/market/stocks/005930/latest"
{"stockCode":"005930","name":"삼성전자","market":"KOSPI",
 "latest":{"baseDate":"2026-07-28","closePrice":220000.00, ...}}
```

**주식 담보가 프로덕션에서 단 한 번도 시가로 평가된 적이 없었다.** 1층을 고쳐도 소용없었다 — 그 코드에 닿기 전에 여기서 끊긴다.

## 하나 더 있었다 — 그리고 이쪽이 더 아팠다

첫 수정에서 세 개(`market`·`commondata`·`financial`)를 채웠는데, 검증하다 **네 번째**를 발견했다.

```yaml
economics:
  base-url: ${APP_LOAN_ECONOMICS_BASE_URL:http://localhost:8087}
```

`economics-service` 는 한국은행 기준금리를 제공하고, loan 은 그걸로 담보·개인신용 대출 **금리**를 산정한다. 못 읽으면? 역시 조용히 설정 기본값으로 폴백한다.

```
$ kubectl -n settlement-prod exec $POD -- \
    curl -s "http://settlement-economics:8087/api/economics/indicators/BASE_RATE/latest"
{"code":"BASE_RATE","name":"한국은행 기준금리","unit":"%",
 "latest":{"observedDate":"2026-07-27","value":2.7500}, ...}
```

실제 기준금리 **2.75%** 대신 폴백 **3.5%** 로 심사해 왔다. **금리가 0.75%p 높게 산정된 채로.** 1층이 담보 _평가액_ 이었다면 이건 _금리_ 다. 둘 다 로그 한 줄 없이 조용했다.

## 왜 아무도 몰랐나

같은 차트 안에서 `investment` 서비스는 이미 같은 위성들을 정확히 주입하고 있었다.

```yaml
- name: investment
  extraEnv:
    FINANCIAL_BASE_URL: http://settlement-financial:8086
    MARKET_BASE_URL: http://settlement-market:8094
    ECONOMICS_BASE_URL: http://settlement-economics:8087
- name: loan
  extraEnv:
    APP_KAFKA_ENABLED: "true" # ← 이게 전부였다
```

`loan` 만 빠져 있었다. 그리고 **빠져 있어도 아무 일도 일어나지 않았다.** 기본값이 있었으니까.

여기서 얻은 규칙:

> **`@Value("${x:localhost:PORT}")` 형태의 기본값은 K8s 에서 항상 틀린 값이다.**
> 로컬 편의를 위한 기본값은 프로덕션에서 "설정 누락"을 "정상 기동"으로 위장한다.
> 새 외부 호출 소비자를 추가하면 Helm values 의 `extraEnv` 도 **같은 PR 에서** 채운다.

그리고 검증 방법:

> **파드 `env` 를 직접 찍어 본다.** `kubectl exec <pod> -- env | grep BASE_URL` 이 0줄이면 전부 기본값이다.
> 차트 파일을 읽는 것으로 대신하지 말 것 — "채웠다고 생각한 것"과 "파드에 들어간 것"은 다른 사실이다.

## 곁가지 — 환경변수 이름 규칙에 기대지 말 것

이 수정을 하면서 `APP_LOAN_MARKET_BASE_URL` 이라는 이름이 정말 `app.loan.market.base-url` 에 바인딩되는지 확인해야 했다. Spring 의 규칙은 두 갈래고, **서로 다르다.**

- `@Value` 는 `PropertySourcesPlaceholderConfigurer` 를 거쳐 `SystemEnvironmentPropertySource` 로 간다. 그 javadoc 은 `getProperty("foo.bar")` 가 [`foo.bar` → `foo_bar` → `FOO.BAR` → `FOO_BAR` 순으로 시도하며 "Any hyphen variant of the above would work as well"](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/core/env/SystemEnvironmentPropertySource.html) 이라고 명시한다.
- `@ConfigurationProperties` 의 relaxed binding 은 [Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html) 이 정의하는 **정규형(canonical form)** 을 쓴다: "Replace dots (`.`) with underscores (`_`). **Remove any dashes (`-`).** Convert to uppercase." 이 규칙대로면 `base-url` 은 `BASEURL` 이 된다.

즉 같은 프로퍼티라도 `@Value` 냐 `@ConfigurationProperties` 냐에 따라 먹히는 환경변수 이름이 다를 수 있다. 실제로 Spring Boot 3.5 에서 이 두 경로가 갈라지며 [회귀 이슈(#45741)](https://github.com/spring-projects/spring-boot/issues/45741)가 보고됐고, 스레드에서 "`@Value("${test.value-name}")` works fine. (It is handled by `PropertySourcesPlaceholderConfigurer`.)" 라고 정리됐다.

결론은 단순하다. **이름 변환 규칙에 기대지 말고 `application.yml` 에 `${ENV_NAME:기본값}` 으로 환경변수 이름을 리터럴로 적어라.** 규칙 의존이 사라지고, 무엇보다 **"이 서비스가 뭘 주입받아야 하는지"를 `grep` 으로 찾을 수 있게 된다.** 이번 건의 진짜 원인은 그게 안 보였다는 것이었다.

---

# 3층 — 관측: 지표는 있는데 아무도 안 가져갔다

세 번째는 더 근본적이다. 정산 정합성 검사가 "감시되지 않는" 것처럼 보였다. 일일 정합성 검사 6종, 3축 대조, outbox/DLQ, 원장 outbox, 정산 지급, PG 대사 — 로직은 전부 있었다. 알림이 안 왔다.

알림이 없으면 알림 규칙부터 쓰고 싶어진다. 그게 함정이었다. **지표가 Prometheus 에 들어오고 있는지부터** 봤어야 했다.

원인은 두 가지였다.

**(a) 차트 주석이 사실이 아니었다.** `values.yaml` 의 정산 코어 서비스에 `noMetrics: true` 와 "actuator/prometheus 미노출" 이라는 주석이 붙어 있었다. 실측해 보니 그 엔드포인트는 **656줄을 정상 노출**하고 있었다. 언젠가 사실이었을 주석이 화석이 되어, `ServiceMonitor` 가 그 서비스를 통째로 건너뛰게 만들었다.

**(b) 지목할 라벨이 없었다.** 모놀리스 쪽 `Service` 에는 라벨이 아예 없어서 `ServiceMonitor` 가 셀렉터로 잡을 대상 자체가 없었다.

결과: 스케줄 태스크 **ERROR 46건이 이틀 동안 무알림**으로 지나갔다.

이번에도 파드는 `Healthy` 였다. 헬스체크는 "프로세스가 살아 있는가"를 볼 뿐, "이 프로세스가 만들어 내는 신호를 누가 가져가고 있는가"는 보지 않는다.

> **`up{namespace="..."}` 로 타깃 목록을 먼저 본다.**
> 알림이 안 오는 문제의 최단 경로는 규칙 점검이 아니라 스크레이프 확인이다.
> 그리고 **값 파일의 "미노출/미지원" 류 주석은 믿지 말고 파드에서 직접 실측한다** — `curl localhost:<healthPort>/actuator/prometheus | wc -l`.

---

# 세 층을 관통하는 것

| 층   | 무엇이 조용했나            | 왜 조용했나                                                         | 소리 나게 하는 법                                        |
| ---- | -------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------- |
| 계약 | 응답 파싱이 항상 `null`    | `ignoreUnknown` + Spring Boot 가 `FAIL_ON_UNKNOWN_PROPERTIES` 를 끔 | 양측이 같은 정본 샘플을 **엄격 매퍼**로 읽는 계약 테스트 |
| 설정 | 상대 서비스에 닿은 적 없음 | `@Value` 의 `localhost` 기본값이 누락을 위장                        | 파드 `env` 실측 + `${ENV:기본값}` 리터럴로 grep 가능하게 |
| 관측 | 지표가 수집된 적 없음      | 화석 주석 · 셀렉터 라벨 부재                                        | `up{}` 타깃 수 확인 + 파드에서 엔드포인트 직접 실측      |

공통 구조는 하나다. **셋 다 "실패했을 때 계속 진행한다(fail-open)"는 의도적 설계 위에서 벌어졌다.**

그 설계 자체는 옳았다. 시세 조회가 안 된다고 대출 신청을 막을 수는 없다. 문제는 fail-open 을 선택하면서 **"폴백했다는 사실"을 아무 데도 안 남긴 것**이다.

> **Fail-open 은 선택이지만, silent 는 선택이 아니다.**
> 무언가를 삼키기로 했다면 삼켰다는 사실은 반드시 내보내야 한다.
> 로그는 부족하다 — 아무도 안 읽는다. **지표로 만들어야 누적되고, 누적돼야 알림을 걸 수 있다.**

그리고 검증에 대해:

> **"머지했다"는 "동작한다"가 아니다.**
> 이번 건은 코드 머지 → 이미지 빌드 → digest 교체 → **설정 주입** → 실제 호출 성공까지 다섯 단계였고, 넷째 단계에서 끊겨 있었다. 내부 신호(테스트 초록불, 파드 `Healthy`, ArgoCD `Synced`)는 그 어느 것도 이걸 알려주지 않았다.
> 마지막 확인은 **실제 경로를 직접 찔러 보는 것**이어야 한다.

---

# 남은 것

정직하게 적어 둔다. 주택 실거래가 경로는 여전히 안 돈다. `common-data` 에 등록된 수집 소스가 공휴일 정보 하나뿐이라 **실거래가 수집원 자체가 없다.** 그래서 소스 코드 설정은 일부러 비워 뒀다 — 값을 지어 넣으면 `no_match` 폴백이 되어 `source_not_configured` 보다 원인이 흐려진다.

이건 이 글의 결론을 스스로에게 적용한 결과다. **작동하지 않는 것을 작동하는 것처럼 보이게 만드는 설정은, 아무것도 안 하느니 나쁘다.** 지금은 지표가 `reason="source_not_configured"` 로 정직하게 말하고 있고, 수집원이 생기면 그때 채운다.

---

## References

**Jackson**

- [`DeserializationFeature` javadoc (jackson-databind 2.19.1)](https://javadoc.io/static/com.fasterxml.jackson.core/jackson-databind/2.19.1/com/fasterxml/jackson/databind/DeserializationFeature.html) — `FAIL_ON_UNKNOWN_PROPERTIES` 는 Jackson 기본 **활성**
- [`@JsonIgnoreProperties` javadoc (jackson-annotations 2.13)](https://fasterxml.github.io/jackson-annotations/javadoc/2.13/com/fasterxml/jackson/annotation/JsonIgnoreProperties.html) — `ignoreUnknown=true` 는 "without warnings ... without exception"

**Spring**

- [Spring Boot — Customize the Jackson ObjectMapper](https://docs.spring.io/spring-boot/3.3/how-to/spring-mvc.html) — Boot 가 `FAIL_ON_UNKNOWN_PROPERTIES` 를 **비활성**으로 뒤집는다
- [`Jackson2ObjectMapperBuilder` javadoc (Spring Framework)](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/converter/json/Jackson2ObjectMapperBuilder.html) — 같은 목록
- [Spring Boot — Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html) — relaxed binding · Binding From Environment Variables 정규형 규칙
- [`SystemEnvironmentPropertySource` javadoc (Spring Framework 6.2.x)](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/core/env/SystemEnvironmentPropertySource.html) — `foo.bar` → `foo_bar` → `FOO.BAR` → `FOO_BAR` 탐색 순서
- [spring-boot issue #45741](https://github.com/spring-projects/spring-boot/issues/45741) — 3.5 에서 `@Value` 경로와 `@ConfigurationProperties` 경로가 갈라진 사례

**계약 테스트**

- Ian Robinson, [Consumer-Driven Contracts: A Service Evolution Pattern](https://martinfowler.com/articles/consumerDrivenContracts.html) (2006) — "just enough" validation 의 한계와 CDC 패턴
- Martin Fowler, [Contract Test](https://martinfowler.com/bliki/ContractTest.html) (2011, 2018 개정)
- Martin Fowler, [Integration Test](https://martinfowler.com/bliki/IntegrationTest.html) — 테스트 더블의 충실성 문제
- Ham Vocke, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) (2018) — CDC 테스트 실전

**Micrometer**

- [Micrometer — Meters](https://docs.micrometer.io/micrometer/reference/concepts/meters.html) — "A meter is uniquely identified by its name and dimensions"
- [Micrometer — Counters](https://docs.micrometer.io/micrometer/reference/concepts/counters.html)
- [Micrometer — Registry](https://docs.micrometer.io/micrometer/reference/concepts/registry.html)

**면책**: 이 글의 실측 수치(파드명·digest·응답 본문·`curl` 종료 코드)는 필자가 직접 운영하는 K3s 홈랩 클러스터에서 2026-07-30~31 KST 에 관측한 것이며, 제3자가 재현할 수 있는 환경이 아니다. 인용한 라이브러리 동작은 모두 공식 문서·javadoc 으로 확인 가능하지만, 특정 버전에서의 동작이므로 사용 중인 버전의 문서를 확인하기 바란다.
