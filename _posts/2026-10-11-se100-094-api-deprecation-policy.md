---
layout: post
title: "[SE100 #094] API 폐기(deprecation) 정책"
date: 2026-10-11 17:10:44 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, api-deprecation, versioning, backward-compatibility]
---

소프트웨어 공학 100 주제 시리즈의 94번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

폐기(deprecation)는 "곧 지운다" 는 선언이고, 제거(removal)·종료(sunset)는 실제로 지우는 행위다. 좋은 폐기 정책은 그 사이의 **기간·신호·대안·측정** 을 미리 약속해, 소비자가 놀라지 않고 옮겨 갈 수 있게 한다.

## 왜 필요한가

API 를 공개하는 순간 그것은 내 코드가 아니라 **남의 코드의 일부** 가 된다. 바꾸고 싶은 이유는 많다. 설계 실수, 보안 문제, 유지 비용. 그러나 정책 없이 지우면 다음 일이 벌어진다.

- 어느 날 고객 연동이 깨지고, 고객은 공지를 본 적이 없다고 한다.
- 겁이 나서 아무것도 지우지 못한다. v1, v2, v3 엔드포인트가 모두 살아 있고, 각각에 보안 패치를 해야 한다.
- 문서에서 "deprecated" 라고 써 두었지만 아무도 읽지 않아, 제거 직전까지 트래픽이 줄지 않는다.

Hyrum Wright 의 관찰로 알려진 [Hyrum's Law](https://www.hyrumslaw.com/) 가 이 문제의 바닥을 보여 준다.

> API 사용자가 충분히 많으면, 계약에 무엇을 약속했는지는 중요하지 않다. 시스템의 관찰 가능한 모든 동작에 누군가는 의존하게 된다.

즉 문서화된 필드만 바꾸지 않는다고 안전한 것이 아니다. 응답 순서, 오류 메시지 문구, 응답 시간까지 누군가의 코드가 의존한다. 폐기 정책은 이 현실을 전제로 한 변경 관리다.

## 핵심 개념

### 용어 정리

| 용어 | 의미 | 이 시점의 API |
|---|---|---|
| 폐기(deprecated) | 더 이상 권장하지 않음, 대안 존재, 제거 예정일 수 있음 | **동작한다** |
| 종료(sunset) | 응답하지 않게 될 예정 시점 | 그 시점 이후 동작 보장 없음 |
| 제거(removed) | 실제로 사라짐 | 오류(예: 404, 410) |

### 시맨틱 버저닝의 규칙

[Semantic Versioning 2.0.0](https://semver.org/) 은 하위 호환되지 않는 변경은 MAJOR 를 올리고, 공개 API 기능을 폐기로 표시하면 MINOR 를 올려야 한다고 규정한다. FAQ 는 절차까지 제시한다. 문서를 갱신하고, 폐기를 담은 MINOR 릴리스를 내고, **완전히 제거하는 MAJOR 릴리스 전에 폐기가 포함된 MINOR 릴리스가 최소 하나 있어야** 사용자가 부드럽게 옮겨 갈 수 있다.

### 성숙도별 보장 기간: Kubernetes 와 Google AIP

폐기 정책을 가장 정량적으로 문서화한 사례가 [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/) 다.

| 규칙 | 내용 |
|---|---|
| Rule #1 | API 요소는 API 그룹의 버전을 올려야만 제거할 수 있다 |
| Rule #2 | 한 릴리스 안에서 API 객체는 버전 간 왕복 변환해도 정보가 손실되지 않아야 한다 |
| Rule #3 | 어떤 API 버전을 **덜 안정적인** 버전으로 대체하며 폐기할 수 없다 (GA 를 beta 로 대체 불가) |
| Rule #4a (GA) | 폐기 표시는 가능하지만 Kubernetes 메이저 버전 안에서는 제거하면 안 된다 |
| Rule #4a (Beta) | 도입 후 9개월 또는 3개 마이너 릴리스 안에 폐기되고, 폐기 후 9개월 또는 3개 마이너 릴리스가 지나면 서비스 중단 (둘 중 긴 쪽) |
| Rule #4a (Alpha) | 사전 폐기 공지 없이 어느 릴리스에서든 제거 가능 |

CLI 와 동작(behavior)에도 기간이 있다. 예컨대 kubectl 같은 사용자용 컴포넌트의 GA CLI 요소는 폐기 공지 후 **12개월 또는 2개 릴리스** 이상 동작해야 하고(Rule #5a), 폐기된 동작은 공지 후 **최소 1년** 동작해야 하며(Rule #7), 폐기된 CLI 요소는 사용 시 경고를 내야 한다(Rule #6).

Google 의 API 설계 지침 [AIP-181 Stability levels](https://google.aip.dev/181) 도 같은 구조다. alpha 는 하위 호환 깨짐이 허용되고 기대되며, beta 의 호환 불가 변경에는 폐기 기간이 필요하고 그 "경험칙" 으로 **90일** 을 든다. stable 은 메이저 버전 수명 동안 깨는 변경이 없어야 하며, 메이저 버전을 내릴 때의 공식 절차를 stable 로 표시할 때 미리 정해 두어야 한다.

공통 원리는 하나다. **안정성 약속이 클수록 폐기 기간이 길다.** 그리고 그 약속을 출시 시점에 이름(alpha/beta/GA)으로 붙여 둔다.

### 날짜 기반 버전 고정: Stripe

Stripe 는 [API 버전](https://docs.stripe.com/api/versioning)을 날짜(+릴리스 이름)로 붙이고, 계정마다 기본 버전을 고정하며, 요청별로 `Stripe-Version` 헤더로 바꿀 수 있게 한다. 2024-09-30.acacia 부터는 매달 깨는 변경 없는 버전을 내고, 1년에 두 번 깨는 변경을 담은 메이저 릴리스를 낸다고 문서에 적혀 있다. 강타입 SDK(Java, Go, .NET)는 SDK 버전이 API 버전을 고정한다. 소비자가 **스스로 업그레이드 시점을 고르는** 모델이다.

### 프로토콜 수준 신호: Deprecation·Sunset 헤더

HTTP 에는 폐기와 종료를 기계가 읽을 수 있게 알리는 표준 헤더가 있다.

- [RFC 9745 The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745.html) (2025-03, Standards Track): 값은 구조화 필드 Date 형식(`@` + 유닉스 시각)이다. 문서 위치는 `rel="deprecation"` 링크로 알린다.
- [RFC 8594 The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594.html) (2019-05, Informational): 값은 HTTP-date. 클라이언트는 이를 **힌트** 로 다뤄야 하며, 그때까지 반드시 동작한다는 보장도, 그 이후 반드시 사라진다는 보장도 아니다.
- RFC 9745 는 Sunset 시각이 Deprecation 시각보다 **이르면 안 된다** 고 규정한다.

```http
HTTP/1.1 200 OK
Deprecation: @1688169599
Sunset: Sun, 30 Jun 2024 23:59:59 GMT
Link: <https://developer.example.com/deprecation>; rel="deprecation"; type="text/html"
```

(RFC 9745 본문 예시를 바탕으로 했다. 2023-06-30 폐기, 2024-06-30 종료를 뜻한다. RFC 본문 예시는 Sunset 값 끝을 `UTC` 로 적었지만, RFC 8594 가 정한 HTTP-date 문법에 맞춰 `GMT` 로 썼다.)

### 언어 수준 신호: Java @Deprecated(forRemoval)

Java 9 의 [JEP 277 Enhanced Deprecation](https://openjdk.org/jeps/277) 은 `@Deprecated` 에 `since` 와 `forRemoval` 을 더했다. `forRemoval=true` 는 **최종 폐기(terminal deprecation)** 로, 사용처에서 일반 폐기 경고와 다른 **제거 경고** 가 난다. `@SuppressWarnings("deprecation")` 으로는 제거 경고가 꺼지지 않아, 일반 폐기였던 API 가 나중에 제거 예정으로 바뀌면 이미 경고를 꺼 둔 코드에서도 다시 경고가 뜬다. `jdeprscan` 도구는 jar 를 훑어 폐기 API 사용을 찾는다.

```java
/** @deprecated 2.4부터. {@link #findByEmail(String)} 를 쓰라. 3.0에서 제거. */
@Deprecated(since = "2.4", forRemoval = true)
public User findByLogin(String login) {
    return findByEmail(loginToEmail(login));   // 폐기 기간 동안은 위임으로 동작 유지
}
```

## 실무 적용

### 폐기 정책 템플릿

```yaml
api_deprecation_policy:
  stability_levels:
    alpha:  { notice: none,      breaking_changes: allowed }
    beta:   { notice: 90d,       breaking_changes: with_notice }
    ga:     { notice: 12 months, breaking_changes: new_major_only }
  announce:
    - changelog + 문서 상단 배너
    - 응답 헤더: Deprecation, Sunset, Link rel=deprecation
    - SDK: 컴파일 경고(@Deprecated forRemoval) / 런타임 경고 로그
    - 최근 N일 호출한 API 키 소유자에게 직접 메일
  migrate:
    - 대체 API 와 1:1 매핑 표, 예제 코드
    - 가능하면 옛 API 를 새 API 위임으로 구현 (동작 일치)
  measure:
    - 폐기 엔드포인트별 호출 수, 호출 고객 수 (주간)
    - 0 이 되지 않으면 상위 고객에 개별 연락
  remove:
    - 종료 전 '브라운아웃'(짧은 계획 중단)으로 숨은 소비자 발견
    - 제거 후 410 Gone + 문서 링크
```

수치(90일, 12개월)는 예시다. 우리 소비자가 배포 주기상 얼마나 걸리는지를 기준으로 정하고, **한 번 공표한 기간은 줄이지 않는다.**

### 측정 없는 폐기는 희망 사항이다

폐기 엔드포인트에 사용량 지표를 붙이는 것이 가장 중요한 작업이다.

```python
def deprecated(endpoint_id: str, sunset_http_date: str, deprecated_epoch: int, doc: str):
    def wrap(handler):
        def inner(request, *a, **kw):
            metrics.counter("api.deprecated.calls",
                            tags={"endpoint": endpoint_id, "client": request.api_key_owner}).inc()
            resp = handler(request, *a, **kw)
            resp.headers["Deprecation"] = f"@{deprecated_epoch}"
            resp.headers["Sunset"] = sunset_http_date
            resp.headers["Link"] = f'<{doc}>; rel="deprecation"; type="text/html"'
            return resp
        return inner
    return wrap
```

## 흔한 오해와 함정

- **"문서에 deprecated 라고 썼으니 됐다."** 문서는 사람이 읽을 때만 효과가 있다. 헤더·컴파일 경고·직접 연락 같은 **여러 경로** 가 필요하고, 결국 호출 지표가 줄어드는지로 판단한다.
- **"폐기 = 즉시 사용 금지."** 폐기된 API 는 여전히 동작해야 한다. 폐기 기간 동안 버그·보안 수정도 계속 해야 한다.
- **덜 안정적인 대안으로 갈아타라고 한다.** Kubernetes Rule #3 이 금지하는 것이다. GA 를 beta 로 대체하면 소비자는 더 불안정한 곳으로 이사하는 셈이다.
- **Sunset 날짜를 절대적 약속처럼 쓴다.** RFC 8594 는 이를 힌트로 규정한다. 소비자 쪽에서는 날짜 전에도 사라질 수 있다고 가정하고, 공급자 쪽에서는 날짜 이후에도 숨은 소비자가 있다고 가정한다.
- **관찰 가능한 동작 변경을 "비호환 아님" 으로 분류한다.** 정렬 순서, 기본 페이지 크기, 오류 문구도 Hyrum's Law 의 대상이다. 의미 있는 동작 변경은 폐기 절차를 밟거나 최소한 변경 공지에 넣는다.

## 확인 문제

1. 폐기, 종료, 제거의 차이를 "그 시점에 API 가 동작하는가" 로 설명하라.
2. SemVer 에서 폐기 표시는 어느 버전 자리를 올리며, 제거 전에 어떤 조건이 필요한가?
3. Kubernetes 에서 beta API 가 지켜야 하는 폐기·종료 기간은?
4. RFC 9745 와 RFC 8594 의 헤더 값 형식은 각각 무엇이고, 둘 사이의 시간 제약은?
5. JEP 277 의 `forRemoval=true` 가 `@SuppressWarnings("deprecation")` 으로 경고를 꺼 둔 코드에 대해 갖는 효과는?

### 풀이

1. 폐기는 아직 동작하지만 권장되지 않고 대안이 있는 상태, 종료(sunset)는 응답하지 않게 될 예정 시점, 제거는 실제로 사라져 동작하지 않는 상태다.
2. MINOR 를 올린다. 완전 제거하는 MAJOR 릴리스 전에 폐기가 포함된 MINOR 릴리스가 최소 하나 있어야 한다.
3. 도입 후 9개월 또는 3개 마이너 릴리스 안에 폐기되고, 폐기 후 9개월 또는 3개 마이너 릴리스(둘 중 긴 쪽)가 지나야 서비스가 중단된다.
4. Deprecation 은 구조화 필드 Date(`@` 유닉스 시각), Sunset 은 HTTP-date 다. Sunset 시각은 Deprecation 시각보다 이르면 안 된다.
5. 제거 경고는 "deprecation" 억제로 꺼지지 않으므로, 일반 폐기였던 API 가 제거 예정으로 바뀌면 그 코드에서도 경고가 다시 나타난다. 조용히 깨지는 것을 막는다.

## 더 읽을거리 (References)

- [Semantic Versioning 2.0.0](https://semver.org/)
- Kubernetes, [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- Google, [AIP-181 Stability levels](https://google.aip.dev/181) / [AIP-185 API Versioning](https://google.aip.dev/185)
- S. Dalal, E. Wilde, [RFC 9745: The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745.html), 2025
- E. Wilde, [RFC 8594: The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594.html), 2019
- OpenJDK, [JEP 277: Enhanced Deprecation](https://openjdk.org/jeps/277)
- Stripe, [Versioning](https://docs.stripe.com/api/versioning)
- [Hyrum's Law](https://www.hyrumslaw.com/)
- [REST API 설계]({% post_url 2026-10-10-cs300-208-rest-api-design %}) (CS300 #208)
