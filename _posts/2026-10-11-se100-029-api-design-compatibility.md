---
layout: post
title: "[SE100 #029] API 설계 — 리소스 모델·버전·하위 호환성"
date: 2026-10-11 16:58:13 +0900
categories: [software-engineering]
tags: [se100, software-architecture, api-design, backward-compatibility, versioning, deprecation]
---

소프트웨어 공학 100 주제 시리즈의 29번째 글이다. (카테고리: 설계와 아키텍처)

## 한 줄 요약

API 는 공개되는 순간 **계약**이 된다. 좋은 API 설계는 리소스(명사)와 소수의 표준 메서드(동사)로 표면을 작게 유지하고, 같은 메이저 버전 안에서는 **추가만 하고 제거·이름 변경·의미 변경을 하지 않으며**, 깨야 할 때는 새 메이저 버전과 공지된 폐기 기간으로 옮긴다.

## 왜 필요한가

내부 함수는 시그니처를 바꾸고 호출부를 한 번에 고치면 된다. API 는 다르다. 호출하는 코드가 다른 팀, 다른 회사, 이미 배포된 모바일 앱 안에 있다. Google 의 [AIP-180 Backwards compatibility](https://google.aip.dev/180)는 이렇게 시작한다.

> API 는 근본적으로 사용자와의 계약이다. 사용자는 API 를 대상으로 코드를 짜서 운영 서비스로 내보내고, 그것이 계속 동작하리라 기대한다.

여기에 Hyrum Wright 의 관찰이 겹친다. [Hyrum's Law](https://www.hyrumslaw.com):

> API 사용자가 충분히 많으면, 계약에 무엇을 약속했든 상관없이, 시스템의 관찰 가능한 모든 동작에 누군가는 의존하게 된다.

응답 필드 순서, 오류 메시지 문구, 정렬되지 않는다고 문서에 적은 목록의 실제 순서까지 누군가는 의존한다. 그래서 하위 호환성은 "문서에 적은 것만 지키면 된다" 로 끝나지 않는다. REST 의 기초는 CS300 [REST API 설계]({% post_url 2026-10-10-cs300-208-rest-api-design %})에서 다뤘으므로 여기서는 계약의 진화에 집중한다.

## 핵심 개념

### 리소스 지향 설계

[AIP-121 Resource-oriented design](https://google.aip.dev/121)의 원칙은 세 가지다.

1. API 의 기본 구성 요소는 **개별적으로 이름 붙은 리소스(명사)** 와 그 사이의 관계·계층이다.
2. **소수의 표준 메서드(동사)** 가 대부분의 연산 의미를 제공한다(Get, List, Create, Update, Delete). 맞지 않을 때만 커스텀 메서드를 쓴다.
3. **무상태 프로토콜**: 각 상호작용은 독립적이다.

설계 순서도 권한다. 리소스 → 리소스 간 관계와 계층 → 각 리소스의 스키마 → 각 리소스의 메서드. 그리고 중요한 경고가 있다. **API 를 DB 스키마와 똑같이 만드는 것은 안티패턴**이다. 표면을 내부 시스템에 강하게 결합시키기 때문이다. 이는 SE100 #021 의 정보 은닉을 API 경계에 적용한 것이다.

```
publishers/{publisher}/books/{book}

GET    /v1/publishers/p1/books          → List
GET    /v1/publishers/p1/books/b42      → Get
POST   /v1/publishers/p1/books          → Create
PATCH  /v1/publishers/p1/books/b42      → Update (부분 갱신)
DELETE /v1/publishers/p1/books/b42      → Delete
POST   /v1/publishers/p1/books/b42:archive → 커스텀 메서드
```

같은 리소스가 여러 메서드의 요청·응답에 등장한다면 **모든 메서드에서 스키마가 같아야 한다**(AIP-121).

### 세 종류의 호환성

AIP-180 은 호환성을 셋으로 나눈다.

| 종류 | 뜻 | 깨지는 예 |
|---|---|---|
| 소스 호환성 | 이전 버전 대상 코드가 새 클라이언트 라이브러리로 컴파일·실행됨 | 생성 코드의 타입·패키지 변경 |
| 와이어 호환성 | 이전 버전 대상 코드가 새 서버와 올바르게 통신. 직렬화 기대가 일치 | 필드 번호 재사용, 필드 타입 변경 |
| 의미 호환성 | 이전 코드가 합리적인 개발자가 기대할 결과를 계속 받음 | 기본 페이지 크기 축소, 값 형식 변경 |

의미 호환성이 가장 미묘하다. AIP-180 의 예: 처음에는 모든 항목을 반환하다가 나중에 페이지네이션을 추가하면서 기본 `page_size` 를 이전 반환량보다 작게 잡으면, 옛 클라이언트는 **모든 결과를 받았다고 잘못 가정**한다. IPv4 형식이던 `ip_address` 필드에 IPv6 값을 넣는 것도 형식 변경이라 깨지는 변경이다.

### 깨지는 변경 vs 안전한 변경

AIP-180 의 지침을 정리하면 다음과 같다(protobuf·JSON 전제, 망라 목록이 아니라 지표라고 문서가 밝힌다).

| 변경 | 같은 메이저 버전에서 |
|---|---|
| 새 리소스·메서드·메시지·필드·enum 값 추가 | 대체로 허용 |
| 기존 요청에 **새 필수 필드** 추가 | 금지 |
| 클라이언트가 채우는 새 필드의 기본 동작이 이전 동작과 다름 | 금지 |
| 서버가 채우던 필드를 더 이상 채우지 않음 | 금지 (중복이 생겨도 계속 채움) |
| 응답에 쓰이는 enum 에 값 추가 | 주의 — 클라이언트가 새 값을 처리 못 할 수 있음 |
| 요청에만 쓰이는 enum 에 값 추가 | 허용 |
| 컴포넌트 제거 | 금지 |
| 이름 변경 | 금지 — "제거 + 추가" 와 같다. 새 것을 추가하고 옛 것은 남김 |
| 필드 타입 변경 | 금지 — 와이어 호환이어도 생성 코드가 깨짐 |
| 리소스 이름 형식을 더 엄격하게/느슨하게 | 금지 — 저장·검증하는 사용자 코드가 깨짐 |
| 문자열 길이 상한 증가 | 비호환으로 취급 권장 |

Protobuf 를 쓴다면 공식 [proto3 가이드](https://protobuf.dev/programming-guides/proto3/)의 규칙도 함께 지킨다. 필드를 삭제할 때 번호를 그대로 두면 나중에 누군가 재사용해 심각한 문제가 생기므로 **`reserved` 로 번호(와 이름)를 막아 둔다.**

```protobuf
message Book {
  reserved 4, 7 to 9;          // 삭제한 필드 번호는 재사용 금지
  reserved "isbn10";           // JSON·텍스트 포맷 호환을 위해 이름도
  string name = 1;
  string title = 2;
  string isbn13 = 5;           // isbn10 을 "이름 변경" 하지 않고 새 필드로 추가
}
```

### 받는 쪽의 규율: 관대한 독자

호환성은 생산자만의 책임이 아니다. Fowler 의 [TolerantReader](https://martinfowler.com/bliki/TolerantReader.html)는 소비자가 **필요한 필드만 읽고 모르는 필드는 무시**하라고 권한다. 응답 전체를 엄격한 스키마로 역직렬화해 모르는 필드에 실패하는 클라이언트는, 서버가 허용된 "필드 추가" 를 하는 순간 깨진다.

```kotlin
// Jackson: 모르는 필드 무시 — 서버의 필드 추가에 견딘다
@JsonIgnoreProperties(ignoreUnknown = true)
data class BookView(val name: String, val title: String)

// 응답 enum 에 새 값이 와도 죽지 않게
enum class BookState { ACTIVE, ARCHIVED, UNKNOWN }
fun parseState(raw: String) = runCatching { BookState.valueOf(raw) }.getOrDefault(BookState.UNKNOWN)
```

### 버전 관리

[Semantic Versioning 2.0.0](https://semver.org)은 공개 API 를 선언한 뒤 MAJOR.MINOR.PATCH 로 변경 종류를 표현한다. 호환되지 않는 API 변경은 MAJOR, 하위 호환 기능 추가는 MINOR, 하위 호환 버그 수정은 PATCH. 0.y.z 는 초기 개발용으로 무엇이든 바뀔 수 있다.

웹 API 에서는 이것을 그대로 쓰지 않는 경우가 많다. [AIP-185 API Versioning](https://google.aip.dev/185)은 다음을 요구한다.

- 모든 API 인터페이스는 **메이저 버전**을 가지며, protobuf 패키지 끝과 REST URI 경로 첫 부분에 넣는다(`/v1/...`).
- semver 의 용어를 빌리지만 **마이너·패치 번호는 노출하지 않는다.** `v1` 이지 `v1.4.2` 가 아니다. 마이너·패치 수준 변경은 같은 메이저 안에서 제자리 갱신되고 사용자는 이전 없이 새 기능을 받는다.
- 새 메이저 버전은 이전 메이저 버전에 의존하면 안 된다.
- 한 클라이언트 안에서 두 버전이 **전환 기간 동안 동시에 동작**해야 하고, 옛 버전은 충분히 공지된 폐기 기간을 거쳐 종료한다.
- 알파·베타는 `v1alpha`, `v1beta` 처럼 채널을 붙인다. 베타 기능은 폐기 표시 후 충분한 기간이 지나면 제거할 수 있으며, 권장 기간은 180일이다.

### 폐기와 종료 신호: HTTP 헤더

| 헤더 | 표준 | 의미 |
|---|---|---|
| `Deprecation` | [RFC 9745](https://www.rfc-editor.org/rfc/rfc9745) (2025, Proposed Standard) | 이 리소스가 폐기될 예정이거나 폐기된 시점. 값은 구조화 필드 날짜(`@` + 유닉스 시간) |
| `Sunset` | [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594) (2019, Informational) | 리소스가 응답하지 않게 될 것으로 예상되는 시점 |
| `Link: rel="deprecation"` | RFC 9745 | 폐기 정책·이전 안내 문서 링크 |

```http
HTTP/1.1 200 OK
Deprecation: @1688169599
Sunset: Sun, 30 Jun 2024 23:59:59 UTC
Link: <https://developer.example.com/deprecation>; rel="deprecation"; type="text/html"
```

위 값은 RFC 9745 의 두 예시(폐기 링크 예, Sunset 병용 예)를 합친 것이다. RFC 9745 는 Sunset 시점이 Deprecation 시점보다 앞서면 안 된다(MUST NOT)고 정한다. 폐기(deprecation)는 "쓰지 말라" 는 권고이고, 종료(sunset)는 "응답하지 않게 된다" 는 예고다. 둘은 다른 시점이다.

## 실무 적용: API 변경 리뷰 체크리스트

- [ ] 이 변경은 추가인가? 제거·이름 변경·타입 변경·의미 변경이 섞였는가
- [ ] 새 필드가 요청에서 필수인가 (같은 메이저에서는 금지)
- [ ] 새 필드의 기본값이 이전 동작과 같은가
- [ ] 응답 enum 에 값을 추가했다면, 주요 소비자가 모르는 값을 견디는가
- [ ] 목록의 기본 페이지 크기·정렬·필터 기본값이 바뀌었는가 (의미 호환성)
- [ ] protobuf: 삭제한 필드 번호·이름을 `reserved` 했는가
- [ ] 깨지는 변경이라면: 새 메이저 버전, 두 버전 병행 기간, `Deprecation`·`Sunset` 헤더, 이전 가이드
- [ ] OpenAPI 명세 diff 를 CI 에서 돌려 깨지는 변경을 자동 탐지하는가

마지막 항목은 [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)처럼 기계가 읽는 계약이 있을 때 가능하다. 계약을 코드와 같은 저장소에 두고 PR 마다 이전 버전과 비교한다.

## 흔한 오해와 함정

- **"필드 이름만 바꿨으니 사소하다."** AIP-180 기준으로 이름 변경은 제거 + 추가다. 깨지는 변경이다.
- **"문서에 없는 동작은 바꿔도 된다."** Hyrum's Law. AIP-180 도 문서화되지 않은 동작에도 사용자 코드가 의존하므로, 합리적인 사용자 코드를 깨뜨릴 만한 동작·의미 변경을 하지 말라고 한다. 다만 이를 너무 넓게 읽어 어떤 변경도 못 하게 되는 것은 의도가 아니라고 덧붙인다.
- **"v2 를 내면 v1 은 바로 끄면 된다."** AIP-185 는 합리적인 전환 기간 동안 두 버전이 동시에 동작해야 한다고 요구한다.
- **"내부 API 라 상관없다."** AIP-180 은 호출자를 통제할 수 있는(같은 팀, 강제 업데이트) API 는 자체 호환성 요구를 따로 판단하라고 한다. 반대로, 배포 시점을 맞출 수 없는 내부 소비자가 있다면 외부 API 와 같은 규율이 필요하다.
- **"API 모델 = DB 테이블."** AIP-121 이 안티패턴으로 명시했다. 테이블 컬럼 하나 바꿀 때마다 API 계약이 흔들린다.

## 확인 문제

1. AIP-180 이 말하는 세 종류의 호환성은?
2. 기존 목록 API 에 페이지네이션을 추가하면서 기본 페이지 크기를 50 으로 정했다. 무엇이 문제일 수 있는가?
3. protobuf 에서 필드를 삭제할 때 `reserved` 를 쓰는 이유는?
4. AIP-185 가 `v1.4.2` 대신 `v1` 만 노출하라고 하는 이유는?
5. `Deprecation` 헤더와 `Sunset` 헤더는 각각 무엇을 알리는가?

### 풀이

1. 소스 호환성, 와이어 호환성, 의미 호환성.
2. 이전에는 모든 항목을 반환했으므로, 옛 클라이언트는 첫 응답이 전부라고 가정하고 나머지를 놓친다. 의미 호환성 위반이다.
3. 나중에 누군가 같은 번호를 다른 의미로 재사용하면, 옛 데이터·옛 클라이언트와 와이어 수준에서 잘못 해석되기 때문이다. 이름도 막아 JSON·텍스트 포맷 호환을 지킨다.
4. 마이너·패치 수준 변경은 같은 메이저 안에서 제자리 갱신되어 사용자가 이전 작업 없이 받으므로, 사용자에게 의미 있는 경계는 메이저 버전뿐이기 때문이다.
5. Deprecation 은 리소스가 폐기될 예정이거나 폐기된 시점(사용 중단 권고), Sunset 은 리소스가 응답하지 않게 될 것으로 예상되는 시점(종료 예고)이다.

## 더 읽을거리 (References)

- Google API Improvement Proposals: [AIP-121 Resource-oriented design](https://google.aip.dev/121), [AIP-180 Backwards compatibility](https://google.aip.dev/180), [AIP-185 API Versioning](https://google.aip.dev/185)
- Hyrum Wright, [Hyrum's Law](https://www.hyrumslaw.com)
- Martin Fowler, [TolerantReader](https://martinfowler.com/bliki/TolerantReader.html)
- [Semantic Versioning 2.0.0](https://semver.org)
- Protocol Buffers, [Language Guide (proto 3)](https://protobuf.dev/programming-guides/proto3/)
- E. Wilde, [RFC 8594: The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594), 2019
- S. Dalal, E. Wilde, [RFC 9745: The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745), 2025
- [OpenAPI Specification v3.1.0](https://spec.openapis.org/oas/v3.1.0)
- CS300: [REST API 설계]({% post_url 2026-10-10-cs300-208-rest-api-design %}), [HTTP/1.1]({% post_url 2026-10-10-cs300-152-http-1-1 %})
