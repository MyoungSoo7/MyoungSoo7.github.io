---
layout: post
title: "[SE100 #039] 주석과 API 문서 — 무엇을 왜 남기는가"
date: 2026-10-11 17:00:03 +0900
categories: [software-engineering]
tags: [se100, code-quality, documentation, comments, api-docs, adr]
---

소프트웨어 공학 100 주제 시리즈의 39번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

코드는 **무엇을, 어떻게** 하는지 말할 수 있지만 **왜** 그렇게 했는지와 **무엇을 약속하는지**는 말하지 못한다. 주석은 "왜" 를, API 문서는 "계약" 을, 결정 기록은 "그때의 맥락" 을 맡는다. 코드가 말할 수 있는 것을 주석으로 반복하면 그 주석은 곧 거짓말이 된다.

## 왜 필요한가

두 극단이 모두 흔하다. 한쪽은 `i++ // i 를 1 증가` 같은 주석으로 가득한 코드다. 이런 주석은 정보가 없고, 코드가 바뀔 때 갱신되지 않아 결국 코드와 어긋난다. 다른 쪽은 "좋은 코드는 주석이 필요 없다" 를 문자 그대로 믿는 팀이다. 이 팀의 코드에는 왜 재시도를 정확히 3번 하는지, 왜 이 정렬은 안정 정렬이어야 하는지, 왜 이 외부 API 호출 앞에 200ms 를 기다리는지가 어디에도 없다. 그 이유를 아는 사람이 떠나면 다음 사람은 "불필요해 보이는" 코드를 지우고 과거의 장애를 다시 겪는다.

이 글의 질문은 "주석을 쓸까 말까" 가 아니라 **어떤 정보를 어느 그릇에 담을까**다.

## 핵심 개념

### 문서의 그릇은 넷이다

| 그릇 | 담는 것 | 독자 | 수명 |
|---|---|---|---|
| 이름과 구조(코드 자체) | 무엇을, 어떻게 | 코드를 읽는 사람 | 코드와 같음 |
| 구현 주석 | 왜 이렇게 했는가, 숨은 제약, 경고 | 유지보수자 | 해당 코드와 같음 |
| API 문서(docstring, Javadoc, OpenAPI) | 계약: 입력, 출력, 예외, 부수효과, 스레드 안전성 | 호출자(구현을 안 보는 사람) | 공개 인터페이스와 같음 |
| 결정 기록(ADR), 변경 이력 | 그때의 맥락, 대안, 결과 | 미래의 팀 | 영구 |

정보를 잘못된 그릇에 담는 것이 대부분의 문서 문제다. 계약을 구현 주석에 쓰면 호출자가 못 보고, 결정의 맥락을 코드 주석에 쓰면 코드가 바뀔 때 사라진다.

### 원칙 1: 코드가 말할 수 있으면 코드로

Fowler 는 [FunctionLength](https://martinfowler.com/bliki/FunctionLength.html)에서 함수 길이의 기준을 줄 수가 아니라 **의도와 구현의 분리**로 본다. 코드 조각이 무엇을 하는지 알아내려고 애써야 한다면, 그 조각을 함수로 추출하고 "무엇" 을 이름으로 붙이라는 것이다. 주석으로 설명하려던 블록은 대개 추출할 함수 후보다.

```java
// Before: 주석이 코드의 '무엇'을 반복한다
// 활성 상태이고 30일 이내에 로그인한 사용자인지 확인
if (u.status == 1 && u.lastLogin.isAfter(now.minusDays(30))) { ... }

// After: 이름이 '무엇'을 말한다
if (u.isRecentlyActive(now)) { ... }
```

### 원칙 2: 주석은 "왜" 를 말한다

Google 의 코드 리뷰 가이드 [What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html)는 주석이 대개 코드가 **무엇을 하는지가 아니라 왜 존재하는지**를 설명할 때 유용하며, 주석은 주로 코드 자체가 담을 수 없는 정보를 위한 것이라고 쓴다. 정규식이나 복잡한 알고리즘처럼 무엇을 하는지 설명이 도움이 되는 예외도 함께 인정한다.

```kotlin
// 결제사 API 는 같은 idempotency key 를 24시간만 기억한다(결제사 연동 문서 3.2절).
// 그보다 오래된 재시도는 새 키로 보내면 이중 결제가 되므로 여기서 실패로 끊는다.
if (Duration.between(firstAttempt, now) > Duration.ofHours(24)) return RetryDecision.GiveUp
```

좋은 "왜" 주석의 유형은 다음과 같다.

- **외부 제약**: 프로토콜, 결제사·규제 요구, 하위 호환
- **비자명한 선택**: 더 단순해 보이는 대안을 **안 쓴** 이유
- **경고**: 이 순서를 바꾸면 교착이 생긴다, 이 함수는 스레드 안전하지 않다
- **출처**: 알고리즘의 논문, 버그 이슈 번호, 스펙 절 번호
- **TODO**: 반드시 이슈 번호와 함께(번호 없는 TODO 는 영원히 남는다)

### 원칙 3: API 문서는 계약이다

공개 API 의 독자는 구현을 보지 않는다. 그래서 API 문서는 Design by Contract 의 사전조건, 사후조건, 예외를 사람의 말로 쓴 것이어야 한다(SE100 #034 에서 다룬다).

언어별 공식 관례는 첫 문장을 특별하게 다룬다.

| 언어 | 관례 |
|---|---|
| Java | Oracle 의 [How to Write Doc Comments](https://www.oracle.com/technical-resources/articles/java/javadoc-tool.html): 첫 문장은 요약으로 메서드 요약 표에 그대로 들어간다. `@param`, `@return`, `@throws` 블록 태그 |
| Python | [PEP 257](https://peps.python.org/pep-0257/): 항상 `"""삼중 큰따옴표"""`, 한 줄 docstring 은 마침표로 끝나는 명령형 구문("Return the pathname …"), 설명형("Returns …")이 아님 |
| Go | [Go Doc Comments](https://go.dev/doc/comment): 완전한 문장, 선언된 이름으로 시작 |
| Kotlin | [KDoc](https://kotlinlang.org/docs/kotlin-doc.html), [Dokka](https://kotlinlang.org/docs/dokka-introduction.html)로 생성 |
| HTTP API | [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)(현재 3.2.x) |

API 문서에 꼭 들어가야 하지만 자주 빠지는 것: **null/빈 값의 의미, 단위(ms 인가 s 인가), 예외 조건, 멱등성, 스레드 안전성, 성능 특성(O(n) 인가), 부수효과**. 요구 수준을 명확히 하려면 [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)의 MUST/SHOULD/MAY 를 차용하는 것도 방법이다.

### 원칙 4: 실행되는 문서는 거짓말을 못 한다

문서가 코드와 어긋나는 문제의 가장 확실한 해법은 문서를 **실행**하는 것이다.

- Python [doctest](https://docs.python.org/3/library/doctest.html)는 docstring 안의 대화형 예제를 찾아 실행하고 결과를 비교한다.
- Rust 의 [문서 테스트](https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html)는 문서 주석의 코드 예제를 추출해 테스트로 실행한다.
- OpenAPI 명세를 먼저 쓰고 서버 스텁과 계약 테스트를 생성하면(contract-first), 명세와 구현이 어긋날 때 빌드가 깨진다. 코드에서 명세를 생성하는 쪽(code-first)이라면 [springdoc](https://springdoc.org/) 같은 도구가 있다.

### 원칙 5: 결정은 따로 남긴다

Michael Nygard 는 2011년 글 [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)에서, 새로 온 사람이 과거 결정의 이유를 모르면 **맹목적으로 따르거나 맹목적으로 뒤집는** 두 가지 선택밖에 없다고 지적하며 짧은 결정 기록(ADR)을 제안했다. 형식은 Title, Context, Decision, Status, Consequences 다섯 부분이다. Status 는 proposed, accepted, 그리고 나중 결정이 대체하면 deprecated 나 superseded 가 된다. Consequences 에는 긍정적인 것만이 아니라 모든 결과를 적는다.

사용자용 변경 이력은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)의 원칙대로 "기계가 아니라 사람을 위한 것" 으로, Added, Changed, Deprecated, Removed, Fixed, Security 로 묶는다. 커밋 로그 diff 를 그대로 변경 이력으로 쓰는 것은 잡음이 많아 나쁜 방법이라고 같은 문서가 명시한다.

### 문서 전체의 지도: Diátaxis

[Diátaxis](https://diataxis.fr/)는 기술 문서를 네 종류로 나눈다. **튜토리얼**(배우게 하는 수업), **방법 안내(how-to)**(목표 달성 절차), **참조(reference)**(API 문서처럼 정확한 기술 정보), **설명(explanation)**(배경과 이유). API 문서는 참조이고, ADR 은 설명에 가깝다. 한 문서에 넷을 섞으면 어느 독자에게도 맞지 않는다.

Knuth 는 1984년 *The Computer Journal* 에 [Literate Programming](https://doi.org/10.1093/comjnl/27.2.97)을 발표했다. 그의 [소개 페이지](https://www-cs-faculty.stanford.edu/~knuth/lp.html)는 핵심 생각을 "프로그램을 컴퓨터가 아니라 **사람에게 보내는 문학 작품**으로 다루는 것" 이라고 요약한다. 오늘날 문서 도구 대부분이 이 생각의 일부를 물려받았다.

## 예제

### 계약을 담은 Javadoc

```java
/**
 * 주문을 취소하고 결제를 환불한다.
 *
 * <p>멱등하다: 이미 취소된 주문에 대해 다시 호출하면 아무 일도 하지 않고 같은 결과를 반환한다.
 * 이 메서드는 스레드 안전하며, 같은 주문에 대한 동시 호출은 주문 단위 잠금으로 직렬화된다.
 *
 * @param orderId 취소할 주문 ID. null 이면 안 된다.
 * @param reason  사용자에게 표시될 사유. 최대 200자.
 * @return 환불 결과. 결제 전 주문이면 {@code RefundResult.NONE}.
 * @throws OrderNotFoundException 주문이 없을 때
 * @throws IllegalStateException  이미 배송이 시작된 주문일 때
 */
public RefundResult cancel(OrderId orderId, String reason) { ... }
```

### ADR 템플릿

```markdown
# ADR 7: 주문 이벤트를 Kafka 대신 DB outbox 테이블로 발행한다

## Status
Accepted (2026-10-11). ADR 3 을 대체한다.

## Context
주문 저장과 이벤트 발행이 원자적이지 않아 이벤트 유실이 발생했다. …

## Decision
주문과 같은 트랜잭션에서 outbox 테이블에 이벤트를 쓰고, 별도 릴레이가 발행한다. …

## Consequences
+ 저장과 발행의 원자성 확보
- 발행 지연이 릴레이 주기만큼 늘어남, outbox 정리 작업 필요
```

## 흔한 오해와 함정

- **"좋은 코드는 주석이 필요 없다."** 좋은 코드는 "무엇" 에 대한 주석이 필요 없다. "왜" 는 코드가 말할 수 없다.
- **주석 처리된 코드 남기기.** 버전 관리가 기억한다. 남겨야 할 이유가 있다면 그 이유를 쓰고 코드는 지운다.
- **변경 이력을 주석에.** "2023-03 김OO 수정" 같은 주석은 `git log` 와 `git blame` 의 일이다.
- **docstring 이 시그니처 반복.** `@param name the name` 은 정보가 없다. 단위, 범위, null 의미를 쓴다.
- **문서를 리뷰하지 않기.** 코드 리뷰에서 바뀐 동작에 맞게 주석과 문서가 바뀌었는지도 본다. 어긋난 주석은 없는 주석보다 해롭다.

## 확인 문제

1. 다음 각각을 어느 그릇에 담아야 하는가? (a) 이 메서드가 null 을 반환할 수 있다는 사실 (b) 정렬을 직접 구현한 이유 (c) 메시지 큐 대신 outbox 를 택한 이유와 대안
2. PEP 257 이 한 줄 docstring 에 요구하는 문장 형태는?
3. Nygard 가 ADR 이 없을 때 새 팀원이 처한다고 본 두 가지 선택은?
4. 문서와 코드가 어긋나는 문제를 구조적으로 막는 방법 두 가지를 들라.

### 풀이

1. (a) API 문서(계약), (b) 구현 주석(왜), (c) ADR(결정 맥락, 대안, 결과).
2. 마침표로 끝나는 구문으로, 함수의 효과를 명령형으로 기술한다("Return …"). "Returns …" 같은 설명형이 아니다.
3. 이유를 모른 채 결정을 맹목적으로 받아들이거나, 맹목적으로 뒤집는 것.
4. 문서 안의 예제를 테스트로 실행한다(doctest, Rust 문서 테스트). API 명세를 먼저 쓰고 스텁·계약 테스트를 생성해 명세와 구현이 어긋나면 빌드가 실패하게 한다.

## 더 읽을거리 (References)

- Google Engineering Practices, [What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Martin Fowler, [FunctionLength](https://martinfowler.com/bliki/FunctionLength.html)
- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), 2011
- D. E. Knuth, "Literate Programming", *The Computer Journal* 27(2), 1984, [DOI](https://doi.org/10.1093/comjnl/27.2.97)
- [PEP 257](https://peps.python.org/pep-0257/), [How to Write Doc Comments for the Javadoc Tool](https://www.oracle.com/technical-resources/articles/java/javadoc-tool.html), [Go Doc Comments](https://go.dev/doc/comment)
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html), [Diátaxis](https://diataxis.fr/), [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
