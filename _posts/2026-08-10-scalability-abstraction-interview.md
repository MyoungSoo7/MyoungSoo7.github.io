---
layout: post
title: "면접에서 확장성을 말할 때 확인해야 할 것: 변하는 축·추상화·이름"
date: 2026-08-10 16:05:00 +0900
categories: [java, spring, architecture, career]
tags: [OCP, abstraction, composition, inheritance, interview, Kotlin, Spring]
---

[Greg Lee’s Lab의 원문](https://medium.com/greglee-lab/%EB%A9%B4%EC%A0%91%EC%97%90%EC%84%9C-%ED%99%95%EC%9E%A5%EC%84%B1-%EC%9D%84-%EB%A7%90%ED%95%98%EB%8A%94-%EC%88%9C%EA%B0%84-%EB%A9%B4%EC%A0%91%EA%B4%80%EC%9D%80-%EC%9D%B4%EA%B2%83%EB%B6%80%ED%84%B0-%ED%99%95%EC%9D%B8%ED%95%9C%EB%8B%A4-77383ee3fb25)을 읽고, Java·Spring 면접과 현재 Settlement 설계에 적용할 수 있는 내용으로 요약했다.

원문의 핵심은 간단하다.

> 확장성은 “많이 붙일 수 있음”이 아니라, 새 요구가 와도 기존 코드를 최소한만 고치고 추가 구현으로 대응할 수 있는 능력이다.

화려한 MSA 다이어그램이나 캐시·메시지큐의 개수가 확장성을 증명하지 않는다. 면접관은 먼저 **변하는 축을 식별했는지, 그 축을 추상화했는지, 추상화의 이름이 구현체에 오염되지 않았는지**를 확인한다.

## 1. 확장성은 OCP를 실제 코드로 설명하는가

새 요구가 들어올 때 기존 서비스의 `if/else`를 계속 수정한다면 확장에 열려 있다고 보기 어렵다.

결제 생성 과정에 다음 검증 규칙이 계속 추가된다고 하자.

```text
MID 소유권 확인
orderNo 중복 확인
1회 결제 한도 확인
특정 상품·거래 유형 제한
```

검증 로직을 서비스에 직접 누적하면 요구사항이 추가될 때마다 결제 서비스가 변경된다. 원문은 이때 변하는 축인 “검증 규칙”을 별도 계약으로 뽑고, 구현체 목록을 주입하는 방향을 설명한다.

```kotlin
fun interface Validator<in T> {
    fun validate(target: T)
}

@Service
class PaymentService(
    private val validators: List<Validator<CreatePaymentCommand>>
) {
    @Transactional
    fun create(command: CreatePaymentCommand): PaymentInfo {
        validators.forEach { it.validate(command) }
        return createPayment(command)
    }
}
```

새 검증 규칙은 `Validator<CreatePaymentCommand>` 구현체를 추가하면 된다. 결제 서비스는 개별 규칙을 알지 않는다.

단, 이것이 항상 좋은 것은 아니다. 규칙 순서, 실패 메시지, 트랜잭션 경계, 중복 실행 여부를 테스트해야 한다. 인터페이스를 만들었다는 사실만으로 설계가 확장 가능한 것은 아니며, 계약과 실행 의미론까지 명확해야 한다.

## 2. 변하는 축을 먼저 찾아라

추상화의 시작은 “인터페이스를 하나 만들자”가 아니다.

```text
무엇이 자주 변하는가?
무엇이 외부 시스템에 의해 달라지는가?
무엇이 정책이고 무엇이 흐름인가?
무엇을 추가할 때 기존 코드를 건드리고 있는가?
```

예를 들어 Settlement에서 변하는 축은 다음처럼 나눌 수 있다.

| 변하는 축 | 적합한 추상화 후보 |
| --- | --- |
| 지급 방식 | `PayoutProcessor` |
| 수수료 정책 | `FeePolicy` |
| 정산 대상 선정 | `SettlementEligibility` |
| 외부 결제사 | `PaymentGateway` |
| 재처리 정책 | `RetryPolicy` |
| 사기·위험 판정 | `RiskRule` |

반대로 단순히 클래스 수를 늘리기 위해 모든 것을 인터페이스로 만들면 추상화가 아니라 간접참조가 된다. 변하지 않는 축까지 추상화하면 읽기 어려움과 설정 복잡성만 커진다.

## 3. Validator 목록과 Template Method는 같은 OCP라도 다르다

원문은 Validator 방식과 Template Method 패턴의 차이를 비교한다.

### Validator·Strategy·Composition

```text
검증 규칙을 병렬로 추가
구현체를 주입
구성으로 조합
```

이 방식은 각 규칙이 독립적일 때 적합하다.

### Template Method·Inheritance

```text
알고리즘의 전체 골격을 부모가 고정
특정 훅을 자식이 구현
```

쿠폰 적용 흐름이 다음처럼 고정된다고 하자.

```text
쿠폰 검증
→ 할인액 계산
→ 결제 반영
```

할인액 계산만 달라진다면 Template Method로 표현할 수 있다. 하지만 부모 클래스의 상태·생명주기·변경에 모든 자식이 결합된다.

변하는 단계가 독립적이라면 다음과 같은 Strategy/Composition이 더 유연할 수 있다.

```kotlin
fun interface DiscountPolicy {
    fun calculate(command: UseCouponCommand): Money
}

@Service
class CouponService(
    private val policies: Map<CouponType, DiscountPolicy>
) {
    fun use(command: UseCouponCommand): PaymentDiscount {
        validate(command)
        val amount = policies.getValue(command.type).calculate(command)
        return apply(command, amount)
    }
}
```

### 면접에서 설명할 기준

```text
변하는 훅이 여러 단계에 걸쳐 부모 상태를 공유하는가?
알고리즘 골격이 강하게 고정되어야 하는가?
구현을 조합·교체·mock하기 쉬워야 하는가?
상속 슬롯과 부모 변경의 비용을 감당할 수 있는가?
```

“상속은 나쁘고 조합은 항상 좋다”가 아니라, **결합 비용을 계산해 선택하는가**가 핵심이다.

## 4. 인터페이스 이름에 구현체 용어가 새지 않는가

추상화의 품질은 이름에서 드러난다.

OAuth 로그인 제공자가 여러 개라면 다음과 같은 모델은 확장에 취약하다.

```kotlin
data class SocialUser(
    val googleSub: String?,
    val kakaoId: Long?
)
```

Provider가 늘어날 때마다 필드가 추가되고, 호출부는 nullable 필드와 Provider별 분기를 떠안게 된다.

중립적인 도메인 언어로 바꾸면 경계가 선명해진다.

```kotlin
data class OAuthPrincipal(
    val provider: OAuthProvider,
    val providerUserId: String,
    val email: String?
)
```

`providerUserId`는 Google의 `sub`, Kakao의 `id`를 내부 도메인 개념으로 변환한 값이다. 외부 API의 필드명을 그대로 도메인 모델에 들여오지 않는 것이 중요하다.

이 원칙은 결제·배송·CRM 연동에도 같다.

```text
googleSub / kakaoId
→ providerUserId

stripePaymentId / tossPaymentKey
→ externalPaymentReference

coupangOrder / vendorOrder
→ externalOrderReference
```

단, 이름을 중립화했다고 끝나지 않는다. 원본 Provider, 식별자 안정성, 재사용·재할당 정책, 정규화 실패를 함께 정의해야 한다.

## 5. 현재 프로젝트에 적용하는 방법

Settlement에서 “확장 가능한 결제·정산”을 말하려면 다음처럼 설명하는 편이 구체적이다.

### 구현 수준

```text
현재 구현된 것:
  실제 코드·테스트·런타임 Trace로 확인된 범위만 implemented

설계 제안:
  아직 코드가 없으면 designed/proposed

외부 연동 경계:
  adapter/interface만 있으면 boundary only
```

### 설계 질문

```text
새 PG를 추가할 때 기존 결제 서비스가 바뀌는가?
정산 정책을 추가할 때 핵심 흐름이 바뀌는가?
외부 식별자와 내부 식별자가 분리되어 있는가?
실패·재시도·멱등성이 계약에 포함되는가?
각 정책 구현을 독립적으로 테스트할 수 있는가?
```

### 면접 답변 구조

```text
1. 변하는 축을 식별했습니다.
2. 해당 축을 도메인 계약으로 분리했습니다.
3. 구현체는 DI/Composition으로 연결했습니다.
4. 새 구현체를 추가해도 핵심 서비스는 수정하지 않습니다.
5. 실패·멱등성·순서·트랜잭션 경계를 테스트했습니다.
6. 실제 적용 범위와 아직 설계인 범위를 구분합니다.
```

마지막 문장이 중요하다. “확장성을 고려했다”는 말보다 **어떤 변경을 하지 않아도 되는지**를 말해야 한다.

## 6. 확장성 면접 체크리스트

| 질문 | 확인하려는 역량 |
| --- | --- |
| 무엇이 변하는 축인가? | 문제 분해·도메인 이해 |
| 인터페이스는 어떤 계약을 표현하는가? | 추상화 설계 |
| 구현체가 몇 개이고 어떻게 선택되는가? | DI·Composition |
| 상속 대신 조합을 선택한 이유는? | 결합도·테스트성 판단 |
| 인터페이스 이름에 외부 업체 용어가 들어가는가? | 경계 설계 |
| 새 요구가 오면 기존 코드를 고치는가? | OCP의 실질적 적용 |
| 실패·재시도·멱등성은 어디에 있는가? | 운영 가능한 설계 |
| 실제로 구현·테스트했는가? | 주장과 Evidence 구분 |

## 결론

확장성은 패턴 이름을 많이 아는 것보다 다음 네 가지에서 드러난다.

```text
변하는 축을 식별한다
구체 구현과 무관한 계약을 만든다
상속과 조합의 결합 비용을 비교한다
도메인 언어로 중립적인 이름을 붙인다
```

좋은 확장성은 새 기능을 쉽게 붙이는 기술만이 아니다. **기존 코드를 왜 건드리지 않아도 되는지 설명할 수 있는 설계**다.

## 원문 및 관련 글

- [원문: Greg Lee’s Lab — 면접에서 “확장성”을 말하는 순간, 면접관은 이것부터 확인한다](https://medium.com/greglee-lab/%EB%A9%B4%EC%A0%91%EC%97%90%EC%84%9C-%ED%99%95%EC%9E%A5%EC%84%B1-%EC%9D%84-%EB%A7%90%ED%95%98%EB%8A%94-%EC%88%9C%EA%B0%84-%EB%A9%B4%EC%A0%91%EA%B4%80%EC%9D%80-%EC%9D%B4%EA%B2%83%EB%B6%80%ED%84%B0-%ED%99%95%EC%9D%B8%ED%95%9C%EB%8B%A4-77383ee3fb25)
- [Agent가 어려워하는 일을 자동화한 로컬 Script·Tool 지도](https://myoungsoo7.github.io/2026/08/10/agent-tools-built-on-mac/)
- [이 Mac의 Agent Skill 생태계 지도](https://myoungsoo7.github.io/2026/08/10/agent-skills-inventory/)
- [Settlement Order·Payment·Settlement 흐름 분석](https://myoungsoo7.github.io/2026/08/09/settlement-order-payment-flow/)

*이 글은 원문을 요약·재구성하고 현재 Java/Spring·Settlement 설계 관점의 해석을 덧붙인 글이다. 원문 전체를 재게시하지 않는다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*

## References

- [Greg Lee’s Lab 원문](https://medium.com/greglee-lab/%EB%A9%B4%EC%A0%91%EC%97%90%EC%84%9C-%ED%99%95%EC%9E%A5%EC%84%B1-%EC%9D%84-%EB%A7%90%ED%95%98%EB%8A%94-%EC%88%9C%EA%B0%84-%EB%A9%B4%EC%A0%91%EA%B4%80%EC%9D%80-%EC%9D%B4%EA%B2%83%EB%B6%80%ED%84%B0-%ED%99%95%EC%9E%A5%ED%95%9C%EB%8B%A4-77383ee3fb25)
- [Spring Framework Documentation](https://docs.spring.io/spring-framework/reference/)
- [Kotlin Documentation — Interfaces](https://kotlinlang.org/docs/interfaces.html)
- [Martin Fowler — Inversion of Control](https://martinfowler.com/articles/injection.html)
- [Object-oriented design principles — Open/Closed Principle](https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle)
