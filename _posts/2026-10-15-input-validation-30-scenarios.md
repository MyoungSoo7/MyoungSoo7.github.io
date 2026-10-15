---
layout: post
title: "유효성 검사(Validation) 실전 시나리오 30가지 — @NotNull 다음에 터지는 것들"
date: 2026-10-15 21:34:52 +0900
categories: [backend]
tags: [validation, input-validation, spring, bean-validation, owasp, security, api]
---

`@NotBlank` 하나 붙이고 끝내는 유효성 검사는 형식만 본다. 실제 장애·보안 사고는 그 _다음_ 층에서 난다. 길이를 무엇으로 세는지, 모르는 필드를 어떻게 처리하는지, 검사한 뒤 값이 바뀌지는 않는지 같은 것들이다.

이 글은 백엔드 API(주로 Spring + Jakarta Bean Validation) 기준으로 **테스트 케이스로 바로 옮길 수 있는 30가지 시나리오**를 6개 축으로 정리한다. 각 항목은 "무엇을 넣으면 → 무엇이 잘못되는지 → 기준"의 순서다.

뼈대는 OWASP의 정의를 따른다. 유효성 검사는 **문법(syntax)**, 즉 타입과 형식, 그리고 **의미(semantics)**, 즉 그 연산에서 값이 말이 되는지를 둘 다 본다. 그리고 거부 목록(denylist)이 아니라 **허용 목록(allowlist)** 으로 정의한다 ([OWASP Input Validation Cheat Sheet][owasp-iv]). 관련 약점 분류는 [CWE-20: Improper Input Validation][cwe20]이다.

> 전제 하나. 유효성 검사는 SQL 인젝션·XSS 방어를 **대신하지 않는다.** OWASP는 파라미터화 쿼리와 출력 인코딩을 별도 통제로 둔다. 인가(authorization)도 별개다 ([OWASP][owasp-iv]). 아래 21번이 그 얘기다.

---

## A. 경계와 타입 — "없음"과 "범위"

### 1. null · 빈 문자열 · 공백 문자열을 구분하는가
- **입력**: `null`, `""`, `"   "`
- **함정**: `@NotNull`은 `""`를 통과시키고, `@NotEmpty`는 `"   "`를 통과시킨다. 공백까지 막으려면 `@NotBlank`다.
- **기준**: 필드마다 "없음"이 무엇인지 먼저 정한다. 선택 필드에서 `null`(안 보냄)과 `""`(지움)가 다른 뜻이면 둘을 다르게 처리해야 한다.

### 2. `@Size`·`@Email`은 null을 통과시킨다
- **입력**: `{"nickname": null}` (필드에 `@Size(min=2, max=20)`만 있음)
- **함정**: Jakarta Bean Validation의 대부분 제약은 **"`null` elements are considered valid"** 다 ([`@Size` javadoc][jbv-size], [`@Email` javadoc][jbv-email]). 길이 검사를 붙였으니 필수라고 착각하기 쉽다.
- **기준**: 필수면 `@NotNull`/`@NotBlank`를 **별도로** 붙인다. 테스트에 null 케이스를 항상 넣는다.

### 3. 숫자는 타입이 아니라 범위가 핵심이다
- **입력**: `quantity: -1`, `0`, `2147483648`, `1e309`
- **함정**: 정수로 파싱됐다는 건 타입만 확인된 것이다. OWASP 표현으로 "Converting text to an integer only establishes a type: it does not establish an acceptable quantity" ([OWASP][owasp-iv]). 음수 수량은 환불 로직을 뒤집는다.
- **기준**: 모든 숫자에 `@Min`/`@Max`(또는 `@Positive`)로 업무상 최소·최대를 둔다.

### 4. 큰 정수 ID는 JSON 숫자로 주고받지 않는다
- **입력**: `{"orderId": 9007199254740993}`
- **함정**: I-JSON(RFC 7493)은 절댓값이 `(2**53)-1`을 넘는 정수를 수신 측이 정확한 값으로 다룬다고 기대할 수 없다고 명시한다. 더 큰 수는 **문자열로 인코딩하라고 권고**한다 ([RFC 7493 §2.2][rfc7493]). 64비트 Snowflake ID를 숫자로 내보내면 브라우저(JavaScript)에서 끝자리가 바뀐다.
- **기준**: 64비트 ID는 API 경계에서 문자열로 직렬화한다. 받을 때는 문자열 → `Long` 파싱 실패를 400으로 처리한다.

### 5. 금액은 소수 자릿수까지 검사한다
- **입력**: `amount: 1000.005`, `amount: 1e2`
- **함정**: 원화에 소수점이 오거나, 통화가 허용하지 않는 자릿수가 들어온다.
- **기준**: `BigDecimal` + `@Digits(integer=…, fraction=…)` + `@DecimalMin`. 반올림은 검사를 통과한 **뒤** 업무 규칙으로 명시적으로 한다.

---

## B. 문자열과 인코딩 — "몇 글자"는 생각보다 어렵다

### 6. 길이를 무엇으로 세는가
- **입력**: `"👍👍👍"` (이모지 3개)
- **함정**: Java `String.length()`는 UTF-16 코드 유닛 수라서 이모지 하나가 2로 세어진다. `@Size(max=5)`가 이모지 3개를 거부한다. 반대로 NIST SP 800-63B는 비밀번호 길이를 셀 때 **"Each Unicode code point SHALL be counted as a single character"** 라고 정한다 ([NIST SP 800-63B-4 §3.1.1.2][nist]).
- **기준**: 필드마다 단위를 정한다. 사용자에게 보이는 글자(grapheme)인지, 코드 포인트(`codePointCount`)인지, 저장 바이트인지 정하고, 화면·API·DB가 같은 단위를 쓰는지 대조한다.

### 7. 유니코드 정규화를 같은 시점에 한 번 한다
- **입력**: 같은 "한글"을 NFC(완성형)와 NFD(자모 분리)로 각각 보냄. macOS에서 올린 파일명이 대표적이다.
- **함정**: 눈에는 같은데 `equals`가 false라서 중복 검사·금칙어 검사가 뚫린다.
- **기준**: OWASP는 정규화가 필요한 필드라면 **검사·저장·비교 전에 같은 정책을** 적용하라고 한다. 또한 호환 정규화(NFKC/NFKD)는 의미 있는 구분을 지울 수 있다고 경고한다 ([OWASP][owasp-iv], [UAX #15][uax15]). 비밀번호에 대해 NIST는 해싱 전 NFC를 권고한다 ([NIST][nist]).

### 8. 앞뒤 공백과 보이지 않는 문자
- **입력**: `"admin "`, `"ad​min"`(zero-width space), 줄바꿈이 섞인 이름
- **함정**: `trim()`은 일부 유니코드 공백을 못 지운다(`strip()`과 다르다). 보이지 않는 문자로 "admin"과 똑같아 보이는 다른 아이디를 만들 수 있다.
- **기준**: 식별자 필드는 허용 문자 집합(allowlist)을 정규식 **전체 일치**로 강제한다. 표시용 자유 텍스트는 막지 말고 길이만 제한한다. OWASP도 자유 텍스트는 넓은 유니코드를 허용하되 길이를 제한하라고 한다 ([OWASP][owasp-iv]).

### 9. 정규식은 전체 일치 + 길이 먼저 + 백트래킹 주의
- **입력**: `"aaaaaaaaaaaaaaaaaaaaaaaaaaaa!"`를 `^(a+)+$` 류 패턴에 넣음
- **함정**: ① `find()`로 부분 일치만 보면 `"abc<script>"`가 통과한다. ② 중첩 수량자는 거의 일치하는(near-match) 입력에서 지수 시간이 걸린다. 이게 ReDoS([CWE-1333][cwe1333])다.
- **기준**: OWASP 권고 그대로다. 매칭 **전에** 길이를 제한하고, 전체 일치 API를 쓰고, 과도한 백트래킹 패턴을 피하고, 가능하면 비백트래킹 엔진이나 타임아웃을 쓰고, **타임아웃은 검증 실패로 처리**한다 ([OWASP][owasp-iv]).

### 10. 이메일 — 형식 통과 ≠ 주인 확인
- **입력**: 255자 주소, `"a@b"`, 국제화 도메인
- **함정**: `@Email`의 정확한 규칙은 **"left to Jakarta Bean Validation providers"**, 즉 구현체마다 다르다 ([`@Email` javadoc][jbv-email]). 길이는 RFC 5321 기준 local-part 64옥텟·도메인 255옥텟·경로 256옥텟이다 ([RFC 5321 §4.5.3.1][rfc5321]). 실사용 주소 상한은 RFC 3696 정오표에서 **254자**로 정리된다 ([RFC Errata 1690][errata1690]).
- **기준**: 형식은 유지보수되는 라이브러리로 느슨하게 보고, 길이는 254로 자른다. 실제 소유는 **확인 메일로** 증명한다. OWASP도 "Format validation does not prove mailbox access"라고 쓴다 ([OWASP][owasp-iv]).

---

## C. 구조 — 객체·배열·파서

### 11. 모르는 필드는 조용히 버려진다 (그리고 위험하다)
- **입력**: `{"name":"kim", "role":"ADMIN", "isVerified":true}`
- **함정**: Spring의 `Jackson2ObjectMapperBuilder`는 **`FAIL_ON_UNKNOWN_PROPERTIES`를 끈 상태가 기본**이다 ([Spring javadoc][spring-jackson]). 오타 난 필드는 에러 없이 무시된다. 엔티티를 그대로 바인딩하면 `role`이 실제로 들어간다. 이게 Mass Assignment다 ([OWASP Mass Assignment][owasp-ma]).
- **기준**: 요청마다 전용 DTO(필요한 필드만)를 둔다. 엔티티를 직접 바인딩하지 않는다. 공개 API라면 엄격 모드(모르는 필드 → 400)를 검토한다.

### 12. 중첩 객체는 `@Valid`가 없으면 검사되지 않는다
- **입력**: `{"shipping": {"zip": ""}}` (`Address.zip`에 `@NotBlank`)
- **함정**: 바깥 DTO의 `shipping` 필드에 `@Valid`가 없으면 안쪽 제약은 **아예 실행되지 않는다.** 테스트는 바깥만 보니 초록불이 뜬다.
- **기준**: 중첩 필드에 `@Valid`를 붙인다. 컬렉션은 `List<@Valid Item>`처럼 컨테이너 요소 제약으로 건다. Bean Validation 2.0부터 `Map<@Valid K, @Valid V>`까지 지원된다 ([Jakarta Bean Validation 3.0 spec][jbv-spec]).

### 13. 배열은 개수 상한과 원소 하나하나를 본다
- **입력**: `items: []`, `items: [ …10만 개… ]`, 원소 하나만 잘못된 배열
- **함정**: 빈 배열 주문, 거대한 배열로 인한 메모리 고갈, 첫 원소만 검사하는 코드.
- **기준**: OWASP 표대로 배열은 **최소·최대 개수와 모든 원소(중첩 포함)** 를 검사한다 ([OWASP][owasp-iv]). `@Size(min=1, max=100) List<@Valid Item>`.

### 14. 중복 키 JSON
- **입력**: `{"amount": 100, "amount": 1000000}`
- **함정**: RFC 8259는 객체 안의 이름이 유일**해야 한다(SHOULD)** 고만 하고, 중복 시 동작은 구현마다 다르다 ([RFC 8259 §4][rfc8259]). 게이트웨이(앞쪽 키)와 백엔드(뒤쪽 키)가 서로 다른 값을 읽으면 검사를 우회한다.
- **기준**: 서명·금액이 걸린 API는 파서의 중복 키 탐지(Jackson이면 `JsonParser.Feature.STRICT_DUPLICATE_DETECTION`)를 켜고 400으로 거부한다.

### 15. 크기·깊이 제한은 파싱 **전에**
- **입력**: 50MB 바디, `[[[[[…]]]]]` 1만 단계 중첩
- **함정**: 스키마 검사는 파싱이 끝난 뒤에 돈다. OWASP 표현으로 "A schema check after parsing cannot protect a parser that has already exhausted resources" ([OWASP][owasp-iv]). RFC 8259도 구현이 크기·중첩 깊이·숫자 범위에 제한을 둘 수 있다고 명시한다 ([RFC 8259 §9][rfc8259]).
- **기준**: 리버스 프록시·서블릿 컨테이너에서 바디 크기를 먼저 자르고, 파서의 깊이·문자열 길이 제한을 설정한다.

---

## D. 의미와 교차 필드 — 각각은 맞는데 같이 보면 틀림

### 16. 시작일 < 종료일
- **입력**: `start=2026-10-20, end=2026-10-01`
- **함정**: 필드 단위 제약으로는 못 잡는다. OWASP가 예로 드는 바로 그 경우다(예약의 종료일은 시작일 뒤) ([OWASP][owasp-iv]).
- **기준**: 클래스 수준 커스텀 제약(`@ValidPeriod`)이나 서비스 계층에서 검사하고, 에러는 **필드가 아니라 객체** 단위로 돌려준다.

### 17. 존재하지 않는 날짜가 조용히 고쳐진다
- **입력**: `"2026-02-30"`, `"2025-02-29"`
- **함정**: `DateTimeFormatter.ofPattern("yyyy-MM-dd")`의 기본 해석 방식은 `ResolverStyle.SMART`다. 이 방식은 2월 30일을 **2월 말일로 바꿔 통과시킨다** ([Java `ResolverStyle` javadoc][java-resolver]). 사용자는 30일을 넣었는데 28일로 예약된다.
- **기준**: `ISO_LOCAL_DATE`(STRICT)를 쓰거나, `.withResolverStyle(ResolverStyle.STRICT)`를 쓴다(STRICT에서는 연도 패턴을 `uuuu`로). 2월 29일·말일·윤년을 테스트 케이스에 넣는다.

### 18. 시간대 없는 시각
- **입력**: `"2026-10-15T09:00:00"` (오프셋 없음)
- **함정**: 서버 기본 시간대로 해석된다. 컨테이너는 대개 UTC라 9시간이 밀린다.
- **기준**: 시각은 RFC 3339처럼 **오프셋을 필수로** 받는다(`2026-10-15T09:00:00+09:00`) ([RFC 3339][rfc3339]). 오프셋 없는 값은 400.

### 19. 상태 전이는 허용 목록으로
- **입력**: `PATCH /orders/1 {"status":"SHIPPED"}` (현재 `CANCELLED`)
- **함정**: enum 값으로는 맞지만, 취소된 주문을 배송으로 바꾸는 건 말이 안 된다.
- **기준**: `현재상태 → 허용되는 다음상태` 표를 도메인에 두고 검사한다. 위반은 400이 아니라 **409 Conflict** 성격으로 구분해 응답하면 클라이언트가 처리하기 쉽다.

### 20. 클라이언트가 보낸 가격·합계는 믿지 않는다
- **입력**: `{"items":[{"sku":"A","price":1}], "total":1}`
- **함정**: 항목별 가격과 합계가 서로 맞기만 하면 통과시키는 코드. 둘 다 조작된 값이다.
- **기준**: 가격·할인·합계는 **서버가 재계산**한다. 클라이언트 값은 "화면에서 본 금액"과 비교해 불일치를 알리는 용도로만 쓴다.

---

## E. 보안 경계 — 유효성 검사가 아닌 것과 섞이지 않게

### 21. 형식이 맞다 ≠ 접근해도 된다
- **입력**: 남의 계좌 ID (형식은 완벽)
- **함정**: 유효성 검사를 통과했으니 조회를 허용한다. 전형적인 IDOR다.
- **기준**: OWASP 그대로다. "a valid account identifier does not mean the caller may access that account". 인가는 **별도로** 검사한다 ([OWASP][owasp-iv]).

### 22. 클라이언트 검사만 있는 필드
- **입력**: 브라우저를 거치지 않고 `curl`로 직접 전송
- **함정**: 프론트에 `maxlength`·`required`만 있고 서버에는 검사가 없다.
- **기준**: 클라이언트 검사는 즉시 피드백용일 뿐 우회 가능하다. 서버가 **같은 규칙을 다시** 검사한다 ([OWASP Common Pitfalls][owasp-iv]). 규칙을 한 곳(스키마)에서 생성해 양쪽에 배포하면 어긋나지 않는다.

### 23. 파일 업로드 — 확장자·Content-Type은 사용자가 정한 값
- **입력**: `photo.jpg`라는 이름의 HTML, `../../etc/passwd`, 0바이트, 3GB
- **함정**: 파일명과 `Content-Type`을 믿는다. OWASP는 이 둘을 **신뢰할 수 없는 메타데이터**로 다루라고 한다 ([OWASP][owasp-iv], [File Upload Cheat Sheet][owasp-fu]). 참고로 Spring Boot의 멀티파트 기본 상한은 파일당 `1MB`, 요청당 `10MB`다 ([Spring Boot properties][boot-props]). 운영에서 이 값을 키우면서 업로드 경로의 다른 검사를 같이 점검하지 않는 경우가 많다.
- **기준**: 크기 상한, 내용 기반 형식 판별(매직 바이트), 서버가 생성한 파일명으로 저장, 웹 루트 밖에 저장, 내려줄 때 `Content-Disposition: attachment`.

### 24. 비밀번호 규칙 — 복잡도 규칙은 이제 금지다
- **입력**: `"Password1!"`, 공백 포함 문장형 비밀번호, 100자 비밀번호
- **함정**: "대문자·숫자·특수문자 각 1개 이상" 규칙. NIST SP 800-63B(rev.4)는 다음을 명시한다 ([NIST §3.1.1.2][nist]).
  - 단일 인증 수단 비밀번호는 **최소 15자**, MFA의 일부로만 쓰면 최소 8자 (SHALL)
  - 최대 길이는 **64자 이상 허용** (SHOULD)
  - 문자 종류 조합 같은 **다른 구성 규칙을 강제하지 않음** (SHALL NOT)
  - **주기적 변경 강제 금지** (SHALL NOT). 단 유출 증거가 있으면 강제 변경
  - 흔한·유출된 비밀번호 **차단 목록** 대조, **잘라서 검증하지 않음**
- **추가 함정**: bcrypt는 입력의 **72바이트**까지만 쓴다 ([OWASP Password Storage][owasp-pw]). "64자 이상 허용"과 한글(UTF-8 3바이트)이 만나면 앞부분만 같은 다른 비밀번호가 통과한다.
- **기준**: 길이 + 차단 목록만 검사한다. bcrypt를 쓴다면 72바이트 초과를 거부하거나 Argon2id 등으로 옮긴다.

### 25. 거부된 입력을 그대로 로그에 남기기
- **입력**: `"kim\n2026-10-15 INFO login success user=admin"`
- **함정**: 검증 실패 메시지에 원문을 넣으면 로그 줄이 위조된다(log injection). 비밀번호 필드의 실패 원문이 로그에 남는다.
- **기준**: OWASP 권고대로 실패 사실과 메타데이터(필드명·제약 이름·길이)만 남기고, 원문은 비밀값과 전체 바디를 빼고 로그 형식에 맞게 이스케이프한다 ([OWASP][owasp-iv]).

---

## F. 시스템 경계와 동시성 — 검사한 순간과 쓰는 순간

### 26. 내부에서 온 데이터도 경계를 넘으면 검사한다
- **입력**: Kafka 메시지, 파트너 배치 파일, 다른 마이크로서비스 응답, DB에서 읽은 옛날 레코드
- **함정**: "우리 시스템이 보낸 거니까"라고 믿는다. 스키마가 바뀐 구버전 프로듀서, 마이그레이션 전 데이터가 들어온다.
- **기준**: OWASP는 내부 API·파트너 피드·큐·저장된 레코드도 **신뢰 경계를 넘을 때 다시 검사**하라고 한다 ([OWASP Common Pitfalls][owasp-iv]). 컨슈머 쪽에 같은 DTO 검사를 두고, 실패한 메시지는 DLQ로 보낸다.

### 27. 중복 검사 후 저장 — TOCTOU
- **입력**: 같은 이메일로 가입 요청 2건을 동시에 보냄
- **함정**: `existsByEmail()` → false → `save()`. 두 요청이 모두 존재하지 않음을 확인한 뒤 둘 다 저장한다. 검사 시점과 사용 시점의 경쟁이다 ([CWE-367][cwe367]).
- **기준**: 애플리케이션 검사는 **친절한 에러 메시지용**이고, 최종 보증은 **DB UNIQUE 제약**이다. 제약 위반 예외를 409로 바꿔 응답한다.

### 28. 같은 요청이 두 번 온다
- **입력**: 결제 버튼 더블클릭, 타임아웃 후 클라이언트 재시도
- **함정**: 각 요청은 단독으로 완벽히 유효하다. 문제는 둘이 합쳐졌을 때다.
- **기준**: 상태를 바꾸는 요청은 **멱등성 키**(클라이언트가 생성한 요청 ID)를 받아 처리 결과와 함께 저장하고, 같은 키의 재요청에는 저장된 결과를 돌려준다. 이것도 결국 DB UNIQUE로 보증한다(27번과 같은 원리).

### 29. 생성과 수정의 규칙이 다르다 — 그리고 PATCH의 null
- **입력**: `POST`에는 `id`가 없어야 하고 `PUT`에는 있어야 함. `PATCH {"nickname": null}`
- **함정**: DTO 하나에 제약을 몰아 두면 한쪽이 깨진다. PATCH에서 `null`이 "안 바꿈"인지 "지움"인지가 모호하다.
- **기준**: Bean Validation **그룹**(`groups = OnCreate.class`)이나 그룹 시퀀스로 시나리오별 규칙을 나누거나 ([Jakarta spec §5.4][jbv-spec]), 아예 생성·수정 DTO를 분리한다. PATCH는 "필드가 왔는가"를 `null`과 구분할 수 있는 표현(JSON Merge Patch 의미론 또는 `Optional`/명시적 존재 플래그)으로 받는다.

### 30. 검증 실패 응답을 일관되게 — Spring의 두 가지 예외
- **입력**: `@RequestBody @Valid` DTO 실패, `@RequestParam @Min(1) int page` 실패
- **함정**: 둘이 **다른 예외**로 나온다. 필드 단위 검사는 `MethodArgumentNotValidException`이고, 메서드 파라미터에 제약을 직접 걸면 메서드 검증이 적용되어 `HandlerMethodValidationException`이다. Spring 문서는 메서드 시그니처에 따라 어느 쪽이든 날 수 있으니 **둘 다 처리하라**고 명시한다 ([Spring MVC Validation][spring-val]). 하나만 핸들링하면 다른 하나는 기본 500 처리나 형식이 다른 응답으로 새어 나간다.
- **기준**: 두 예외를 모두 `@RestControllerAdvice`에서 잡아 같은 형식(RFC 9457 Problem Details, [RFC 9457][rfc9457])으로 변환한다. 필드명·제약 이름·거부 사유를 담되 **원문 값은 담지 않는다**(25번).

---

## 체크리스트로 줄이면

| 축 | 한 줄 질문 |
| --- | --- |
| A 경계·타입 | null/빈값/공백, 범위, 큰 수, 소수 자릿수를 각각 정했나 |
| B 문자열 | 길이 단위·정규화·보이지 않는 문자·정규식 전체일치·ReDoS |
| C 구조 | 모르는 필드, 중첩 `@Valid`, 배열 상한, 중복 키, 파싱 전 크기 제한 |
| D 의미 | 교차 필드, 존재하지 않는 날짜, 시간대, 상태 전이, 서버 재계산 |
| E 보안 경계 | 인가는 별개, 서버 재검사, 업로드 메타데이터 불신, NIST 비밀번호, 로그 |
| F 시스템 | 내부 데이터도 재검사, DB 제약으로 최종 보증, 멱등성, 그룹, 일관된 에러 |

이 30개를 그대로 테스트 이름으로 쓰면 된다. 특히 2·12·17·27·30번은 "테스트는 초록불인데 운영에서 터지는" 유형이라 우선순위를 높게 둔다.

### 근거의 한계

- 이 글의 규칙은 표준·공식 문서(OWASP, NIST, IETF RFC, Jakarta, Spring, Java 문서)에서 가져왔다. **어떤 시나리오가 실제로 얼마나 자주 사고를 내는지에 대한 통계는 제시하지 않는다.** 그런 중립적 데이터를 찾지 못했다.
- 우선순위(2·12·17·27·30)는 필자의 판단이다.
- Spring·Jackson의 기본값은 버전에 따라 바뀔 수 있다. 본문은 글 작성일(2026-10-15) 기준 공개 문서를 따랐다.

---

## References

1. OWASP, *Input Validation Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html>
2. MITRE, *CWE-20: Improper Input Validation*. <https://cwe.mitre.org/data/definitions/20.html>
3. MITRE, *CWE-1333: Inefficient Regular Expression Complexity*. <https://cwe.mitre.org/data/definitions/1333.html>
4. MITRE, *CWE-367: Time-of-check Time-of-use (TOCTOU) Race Condition*. <https://cwe.mitre.org/data/definitions/367.html>
5. NIST, *SP 800-63B-4 Digital Identity Guidelines: Authentication and Authenticator Management* (2025), §3.1.1. <https://pages.nist.gov/800-63-4/sp800-63b.html>
6. Eclipse Foundation, *Jakarta Bean Validation 3.0 Specification*. <https://jakarta.ee/specifications/bean-validation/3.0/jakarta-bean-validation-spec-3.0.html>
7. Jakarta Bean Validation API 3.0, `@Size` / `@Email` javadoc. <https://jakarta.ee/specifications/bean-validation/3.0/apidocs/jakarta/validation/constraints/size> · <https://jakarta.ee/specifications/bean-validation/3.0/apidocs/jakarta/validation/constraints/email>
8. IETF, *RFC 5321 — Simple Mail Transfer Protocol*, §4.5.3.1. <https://www.rfc-editor.org/rfc/rfc5321.html>
9. RFC Editor, *Errata ID 1690 (RFC 3696)* — 이메일 주소 실사용 상한 254자. <https://www.rfc-editor.org/errata/eid1690>
10. IETF, *RFC 8259 — The JavaScript Object Notation (JSON) Data Interchange Format*. <https://www.rfc-editor.org/rfc/rfc8259.html>
11. IETF, *RFC 7493 — The I-JSON Message Format*. <https://www.rfc-editor.org/rfc/rfc7493.html>
12. IETF, *RFC 3339 — Date and Time on the Internet: Timestamps*. <https://www.rfc-editor.org/rfc/rfc3339.html>
13. IETF, *RFC 9457 — Problem Details for HTTP APIs*. <https://www.rfc-editor.org/rfc/rfc9457.html>
14. Unicode, *UAX #15 — Unicode Normalization Forms*. <https://unicode.org/reports/tr15/>
15. OWASP, *Mass Assignment Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html>
16. OWASP, *File Upload Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html>
17. OWASP, *Password Storage Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html>
18. Spring Framework Reference, *Validation (Spring MVC)*. <https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-validation.html>
19. Spring Framework API, `Jackson2ObjectMapperBuilder`. <https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/converter/json/Jackson2ObjectMapperBuilder.html>
20. Spring Boot Reference, *Common Application Properties*. <https://docs.spring.io/spring-boot/appendix/application-properties/index.html>
21. Oracle, Java SE API, `java.time.format.ResolverStyle`. <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/format/ResolverStyle.html>

[owasp-iv]: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
[cwe20]: https://cwe.mitre.org/data/definitions/20.html
[cwe1333]: https://cwe.mitre.org/data/definitions/1333.html
[cwe367]: https://cwe.mitre.org/data/definitions/367.html
[nist]: https://pages.nist.gov/800-63-4/sp800-63b.html
[jbv-spec]: https://jakarta.ee/specifications/bean-validation/3.0/jakarta-bean-validation-spec-3.0.html
[jbv-size]: https://jakarta.ee/specifications/bean-validation/3.0/apidocs/jakarta/validation/constraints/size
[jbv-email]: https://jakarta.ee/specifications/bean-validation/3.0/apidocs/jakarta/validation/constraints/email
[rfc5321]: https://www.rfc-editor.org/rfc/rfc5321.html
[errata1690]: https://www.rfc-editor.org/errata/eid1690
[rfc8259]: https://www.rfc-editor.org/rfc/rfc8259.html
[rfc7493]: https://www.rfc-editor.org/rfc/rfc7493.html
[rfc3339]: https://www.rfc-editor.org/rfc/rfc3339.html
[rfc9457]: https://www.rfc-editor.org/rfc/rfc9457.html
[uax15]: https://unicode.org/reports/tr15/
[owasp-ma]: https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
[owasp-fu]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
[owasp-pw]: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
[spring-val]: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-validation.html
[spring-jackson]: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/http/converter/json/Jackson2ObjectMapperBuilder.html
[boot-props]: https://docs.spring.io/spring-boot/appendix/application-properties/index.html
[java-resolver]: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/format/ResolverStyle.html
