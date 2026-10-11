---
layout: post
title: "[SE100 #034] 방어적 프로그래밍과 에러 처리 전략"
date: 2026-10-11 16:59:58 +0900
categories: [software-engineering]
tags: [se100, code-quality, defensive-programming, error-handling, design-by-contract, fail-fast]
---

소프트웨어 공학 100 주제 시리즈의 34번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

방어적 프로그래밍의 핵심은 "모든 곳에서 모든 것을 의심하라" 가 아니라 **어디가 신뢰 경계인지 정하고, 경계에서는 검증하고, 안쪽에서는 계약을 믿되 위반되면 즉시 크게 실패하는 것**이다. 실제 대형 장애의 상당수는 에러를 못 잡아서가 아니라 **잡은 에러를 잘못 처리해서** 생긴다.

## 왜 필요한가

예외 문법과 checked/unchecked 구분은 [예외 처리와 에러 설계]({% post_url 2026-10-10-cs300-034-exception-handling-and-error-design %})에서 다뤘다. 이 글은 "어디서 무엇을 검사하고, 실패하면 어떻게 할 것인가" 라는 설계 판단을 다룬다.

두 가지 실패가 흔하다. **과잉 방어**는 모든 함수가 null 을 다시 검사하고 모든 호출을 `try/catch` 로 감싸 로그만 남긴다. **조용한 실패**는 예외를 삼키고 기본값을 돌려주어, 잘못된 상태가 원인과 무관한 곳에서 뒤늦게 터진다.

토론토 대학의 Yuan 등은 OSDI 2014 논문 [Simple Testing Can Prevent Most Critical Failures](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/yuan)([PDF](https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-yuan.pdf))에서 Cassandra, HBase, HDFS, Hadoop MapReduce, Redis 의 사용자 보고 장애 198건을 분석했다. 결과는 다음과 같다.

- 치명적(catastrophic) 장애의 **92%** 는 소프트웨어가 명시적으로 알린 **치명적이지 않은 에러를 잘못 처리**한 결과였다.
- 치명적 장애의 **58%** 는 에러 처리 코드를 간단히 테스트했다면 발견할 수 있었다.
- 치명적 장애의 **35%** 는 세 가지 사소한 패턴에서 나왔다. (i) 에러 핸들러가 비어 있거나 로그만 찍음, (ii) 지나치게 일반적인 예외를 잡아 클러스터 전체를 중단, (iii) 핸들러에 `FIXME`, `TODO` 주석이 있음.

에러 처리 코드는 마지막 방어선인데, 가장 덜 테스트되는 코드이기도 하다.

## 핵심 개념

### 계약에 의한 설계

Bertrand Meyer 는 [Applying "Design by Contract"](https://doi.org/10.1109/2.161279)(IEEE Computer, 1992)에서 루틴과 호출자의 관계를 계약으로 본다.

| 요소 | 누구의 의무 | 예 |
|---|---|---|
| 사전조건(precondition) | 호출자 | `amount > 0` |
| 사후조건(postcondition) | 루틴 | 반환 후 `balance == old balance - amount` |
| 불변식(invariant) | 클래스(모든 공개 연산 전후) | `balance >= 0` |

계약의 요점은 **책임의 위치를 정하는 것**이다. 사전조건을 호출자 의무로 정하면 루틴 안에서 같은 조건을 다시 방어할 필요가 없다. 그 대신 사전조건 위반은 호출자의 버그이므로 조용히 넘기지 않고 즉시 실패시킨다.

### 신뢰 경계: 검증과 단언을 구분한다

```
  외부 세계 (사용자 입력, HTTP, 파일, 큐, 외부 API)
  ─────────────── 신뢰 경계 ───────────────
  [검증 validation]  형식·범위·권한 확인. 실패는 "예상된 일" → 사용자에게 설명 가능한 에러
          │
          ▼  여기부터는 타입과 값 객체가 보장
  [도메인 내부]       단언 assertion / 계약 검사. 실패는 "버그" → 즉시 크게 실패
```

| | 검증(validation) | 단언(assertion) |
|---|---|---|
| 대상 | 신뢰할 수 없는 외부 입력 | 내부 코드가 지켜야 할 가정 |
| 실패의 의미 | 정상적으로 일어날 수 있는 일 | 프로그래머의 버그 |
| 처리 | 에러 응답, 재입력 요청 | 예외로 중단, 경보 |
| 끌 수 있나 | 절대 안 됨 | 언어에 따라 런타임 옵션(Java `assert` 는 [기본 비활성](https://docs.oracle.com/javase/8/docs/technotes/guides/language/assert.html)) |

Java `assert` 가 기본으로 꺼져 있다는 사실은 중요하다. 외부 입력 검증을 `assert` 로 하면 운영 환경에서 검증이 사라진다. Kotlin 은 의도를 함수 이름으로 구분한다. [`require`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/require.html)는 인자 조건(실패 시 `IllegalArgumentException`), `check` 는 상태 조건(실패 시 `IllegalStateException`)이다.

### 빨리, 크게 실패하라

Jim Shore 는 IEEE Software 2004년 칼럼 [Fail Fast](https://martinfowler.com/ieeeSoftware/failFast.pdf)에서 문제가 생기면 "즉시, 눈에 띄게(immediately and visibly)" 실패하는 소프트웨어가 오히려 더 견고해진다고 주장한다. 잘못된 값을 기본값으로 덮고 계속 가면, 실패는 결국 일어나되 원인에서 멀리 떨어진 곳에서 일어나 디버깅 비용이 커진다.

Erlang 은 이를 시스템 설계 원칙으로 끌어올렸다. Joe Armstrong 의 박사 논문 [Making reliable distributed systems in the presence of software errors](https://erlang.org/download/armstrong_thesis_2003.pdf)(2003) 4.3절은 Erlang 의 에러 처리 철학을 이렇게 요약한다. "다른 프로세스가 복구하게 하라", "원하는 일을 할 수 없으면 죽어라", "죽게 둬라(Let it crash)", "방어적으로 프로그래밍하지 마라". 개별 프로세스는 방어 코드 없이 실패하고, 감독(supervisor) 프로세스가 재시작한다. 방어를 **없앤** 것이 아니라 **다른 층으로 옮긴** 것이다.

### 에러의 종류를 나눈다

| 종류 | 예 | 적절한 처리 |
|---|---|---|
| 예상된 업무 실패 | 잔액 부족, 중복 가입 | 반환 타입으로 표현(Result, sealed class) 또는 checked 예외 |
| 일시적 인프라 실패 | 타임아웃, 503 | 멱등한 연산만 제한된 횟수로 재시도, 백오프 |
| 프로그래머 오류 | null 역참조, 계약 위반 | 잡지 않는다. 상위에서 요청 단위로 실패 처리 후 경보 |
| 복구 불가 | 메모리 부족, 설정 누락 | 프로세스 종료, 재시작은 바깥(오케스트레이터) 몫 |

언어마다 이 구분을 표현하는 장치가 다르다. Oracle Java 튜토리얼의 [기준](https://docs.oracle.com/javase/tutorial/essential/exceptions/runtime.html)은 "클라이언트가 합리적으로 복구할 수 있으면 checked, 아니면 unchecked" 다. [Rust](https://doc.rust-lang.org/book/ch09-00-error-handling.html)는 복구 가능한 에러를 `Result<T, E>` 로, 복구 불가능한 에러를 `panic!` 으로 나눈다. [Go](https://go.dev/blog/error-handling-and-go)는 에러를 `error` 인터페이스 값으로 반환한다.

Python 은 관용구로 [EAFP 와 LBYL](https://docs.python.org/3/glossary.html)을 구분한다. 미리 검사하는 LBYL(Look Before You Leap)은 멀티스레드 환경에서 검사와 사용 사이에 상태가 바뀌는 경쟁 조건을 만들 수 있고, 일단 시도하고 예외를 처리하는 EAFP 는 이를 피한다. 파일 존재를 검사하고 여는 대신 열고 `FileNotFoundError` 를 처리하는 식이다.

### null 은 타입으로 막는다

Tony Hoare 는 QCon London 2009 강연 [Null References: The Billion Dollar Mistake](https://www.infoq.com/presentations/Null-References-The-Billion-Dollar-Mistake-Tony-Hoare/)에서 1965년 ALGOL W 에 null 참조를 넣은 것이 "구현하기 너무 쉬워서" 였다며 이를 "10억 달러짜리 실수" 라고 불렀다. 현대적 처방은 런타임 방어가 아니라 타입 시스템이다. [Kotlin](https://kotlinlang.org/docs/null-safety.html)은 nullable 타입을 구분하고, Java 에서는 [JSpecify](https://jspecify.dev/) 주석과 [NullAway](https://github.com/uber/NullAway) 같은 검사기로 같은 효과를 낸다. 함수마다 `if (x == null)` 을 반복하는 것보다 경계에서 한 번 막고 안쪽 타입을 non-null 로 만드는 편이 낫다.

## 실무 적용

### 경계에서 검증, 안쪽은 계약

```kotlin
// 경계: 외부 입력 → 실패는 예상된 일, 모든 오류를 모아 돌려준다
data class TransferRequest(val from: String?, val to: String?, val amount: Long?)

sealed interface Validated<out T> {
    data class Ok<T>(val value: T) : Validated<T>
    data class Invalid(val errors: List<String>) : Validated<Nothing>
}

fun TransferRequest.validate(): Validated<Transfer> {
    val errors = buildList {
        if (from.isNullOrBlank()) add("from is required")
        if (to.isNullOrBlank()) add("to is required")
        if (amount == null || amount <= 0) add("amount must be positive")
        if (from != null && from == to) add("from and to must differ")
    }
    return if (errors.isEmpty())
        Validated.Ok(Transfer(AccountId(from!!), AccountId(to!!), Money(amount!!)))
    else Validated.Invalid(errors)
}

// 안쪽: 타입이 보장한다. 남은 가정은 계약으로 단언한다.
class Account(val id: AccountId, balance: Money) {
    var balance = balance; private set
    fun withdraw(amount: Money) {
        require(amount.value > 0) { "precondition: amount > 0" }   // 호출자 버그
        check(balance.value >= amount.value) { "invariant would break" }
        balance = Money(balance.value - amount.value)
    }
}
```

경계에서 첫 오류에서 멈추지 않고 오류를 **모아서** 돌려주는 방식은 Fowler 의 [Replacing Throwing Exceptions with Notification in Validations](https://martinfowler.com/articles/replaceThrowWithNotification.html)이 설명하는 패턴이다. HTTP API 라면 오류 응답 형식을 [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)(Problem Details for HTTP APIs, RFC 7807 대체)의 `application/problem+json` 으로 통일한다.

### catch 블록 점검표 (Yuan 등의 세 패턴에서)

- [ ] 비어 있거나 로그만 찍는 `catch` 가 없는가? 로그만 찍을 거면 왜 계속 진행해도 안전한지 주석으로 설명했는가
- [ ] `catch (Exception e)` / `except Exception:` 처럼 넓게 잡아 프로세스나 클러스터 전체를 멈추지 않는가
- [ ] `TODO`, `FIXME` 가 남은 에러 핸들러가 없는가(정적 검사로 막을 수 있다)
- [ ] 에러 경로에 대한 테스트가 있는가(의존성 실패를 주입하는 테스트)
- [ ] 재시도하는 연산은 멱등한가, 재시도 횟수와 전체 시간 상한이 있는가

## 흔한 오해와 함정

- **"방어 코드는 많을수록 안전하다."** 같은 검사를 층마다 반복하면 책임이 흐려지고, 각 층이 서로 다른 기본값으로 "복구" 하면서 상태가 어긋난다. 검증은 경계에서 한 번, 안쪽은 계약.
- **"예외를 잡아서 로그를 남겼으니 처리했다."** Yuan 등의 첫 번째 사소한 패턴 그대로다. 로그는 처리가 아니다.
- **"Let it crash 는 에러 처리를 안 해도 된다는 뜻."** 감독 트리와 재시작 전략이라는 **다른 층의 처리**가 전제다. 그것 없이 크래시만 하면 그냥 장애다.
- **외부 입력 검증에 `assert` 사용.** 운영에서 꺼질 수 있다.
- **모든 실패를 재시도.** 프로그래머 오류나 업무 실패를 재시도하면 같은 실패를 반복하며 부하만 키운다. 재시도는 일시적 실패 + 멱등 연산에만.

## 확인 문제

1. Yuan 등(OSDI 2014)이 치명적 장애의 92% 에 대해 밝힌 원인은 무엇인가?
2. 검증과 단언의 차이를 "실패의 의미" 관점에서 설명하라. 외부 입력을 Java `assert` 로 검사하면 왜 위험한가?
3. Design by Contract 에서 사전조건을 호출자 의무로 정하면 루틴 내부 코드는 어떻게 달라지는가?
4. Erlang 의 "방어적으로 프로그래밍하지 마라" 는 방어적 프로그래밍과 모순되는가?

### 풀이

1. 소프트웨어가 명시적으로 알린, 치명적이지 않은 에러를 잘못 처리한 것.
2. 검증 실패는 외부 입력 때문에 정상적으로 일어날 수 있는 일이고, 단언 실패는 내부 가정이 깨진 버그다. Java `assert` 는 기본으로 비활성이라 운영 환경에서 검사 자체가 사라질 수 있다.
3. 루틴은 사전조건을 다시 방어하거나 기본값으로 복구하지 않고, 위반 시 즉시 실패시킨다. 검사 중복이 사라지고 책임 소재가 분명해진다.
4. 모순이 아니다. 개별 프로세스 안의 방어 코드를 없애는 대신, 실패를 감지하고 재시작하는 책임을 감독 프로세스라는 다른 층으로 옮긴 것이다. 신뢰 경계와 책임 위치를 정한다는 원리는 같다.

## 더 읽을거리 (References)

- D. Yuan et al., [Simple Testing Can Prevent Most Critical Failures](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/yuan), OSDI 2014
- B. Meyer, "Applying 'Design by Contract'", *IEEE Computer* 25(10), 1992, [DOI](https://doi.org/10.1109/2.161279)
- J. Shore, [Fail Fast](https://martinfowler.com/ieeeSoftware/failFast.pdf), *IEEE Software*, 2004
- J. Armstrong, [Making reliable distributed systems in the presence of software errors](https://erlang.org/download/armstrong_thesis_2003.pdf), PhD thesis, 2003
- T. Hoare, [Null References: The Billion Dollar Mistake](https://www.infoq.com/presentations/Null-References-The-Billion-Dollar-Mistake-Tony-Hoare/), QCon London 2009
- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)
- Martin Fowler, [Replacing Throwing Exceptions with Notification in Validations](https://martinfowler.com/articles/replaceThrowWithNotification.html)
