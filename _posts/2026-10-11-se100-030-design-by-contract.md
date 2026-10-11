---
layout: post
title: "[SE100 #030] 계약에 의한 설계 — 사전조건·사후조건·불변식"
date: 2026-10-11 16:58:14 +0900
categories: [software-engineering]
tags: [se100, software-architecture, design-by-contract, preconditions, invariants, liskov-substitution]
---

소프트웨어 공학 100 주제 시리즈의 30번째 글이다. (카테고리: 설계와 아키텍처)

## 한 줄 요약

계약에 의한 설계(Design by Contract, DbC)는 모듈 사이 관계를 **의무와 이익을 명시한 계약**으로 본다. 호출자는 사전조건(precondition)을 만족시킬 의무가 있고, 공급자는 그 대가로 사후조건(postcondition)을 보장하며, 클래스는 모든 공개 연산 전후에 불변식(invariant)을 유지한다. 위반이 나면 **누구의 버그인지가 정해진다.**

## 왜 필요한가

다음 함수의 문서가 "주어진 금액을 출금한다" 뿐이라고 하자.

```kotlin
fun withdraw(amount: Long)
```

음수를 넣으면? 잔액보다 크면? 호출 후 잔액은 정확히 얼마 줄어드는가? 정해진 것이 없으면 두 가지 나쁜 일이 동시에 생긴다.

- **방어적 코드의 중복.** 호출자도 검사하고, 함수도 검사하고, 그 안에서 부르는 함수도 또 검사한다. 같은 조건이 여러 층에 흩어지고, 층마다 처리 방식(예외, `null`, 무시)이 다르다.
- **책임의 공백.** 아무도 검사하지 않는 조건이 생긴다. 다들 "저쪽에서 하겠지" 라고 가정했기 때문이다.

DbC 는 검사의 위치를 계약으로 정해 이 둘을 동시에 없앤다. 사전조건은 호출자의 책임이므로 공급자는 그것을 믿고 본문을 단순하게 쓴다. 사후조건은 공급자의 책임이므로 호출자는 결과를 다시 검증하지 않는다.

## 핵심 개념

### 원전과 이론적 뿌리

DbC 는 Bertrand Meyer 가 Eiffel 언어와 함께 정립했다. 대표 논문은 ["Applying 'design by contract'"](https://doi.org/10.1109/2.161279) (IEEE Computer 25(10), 1992). Eiffel 공식 문서의 [Design by Contract, Assertions and Exceptions](https://www.eiffel.org/doc/eiffel/ET-_Design_by_Contract_%28tm%29%2C_Assertions_and_Exceptions) 장이 개념과 문법을 직접 설명한다.

이론적 뿌리는 C. A. R. Hoare 의 ["An axiomatic basis for computer programming"](https://doi.org/10.1145/363235.363259) (CACM 12(10), 1969) 이다. 호어 삼중쌍 `{P} S {Q}` — 전제 P 가 참인 상태에서 S 를 실행하면 종료 후 Q 가 참 — 이 사전조건·사후조건의 형식적 원형이다.

### 의무와 이익

Eiffel 문서는 계약을 의무(obligation)와 이익(benefit)의 표로 설명하고, **한쪽의 의무는 다른 쪽의 이익으로 대응한다**고 말한다. 계좌 출금에 적용하면 이렇다.

|  | 의무 | 이익 |
|---|---|---|
| 호출자(client) | 0 < 금액 ≤ 잔액 인 상태에서만 호출 (사전조건) | 잔액이 정확히 금액만큼 줄었음을 보장받음 (사후조건) |
| 공급자(supplier) | 잔액을 정확히 금액만큼 줄임 (사후조건) | 금액이 유효하다고 가정하고 구현 가능 (사전조건) |

| 구성 요소 | Eiffel 키워드 | 누가 보장하나 | 언제 참이어야 하나 |
|---|---|---|---|
| 사전조건 | `require` | 호출자 | 루틴 진입 시 |
| 사후조건 | `ensure` | 공급자(루틴) | 루틴 종료 시 |
| 클래스 불변식 | `invariant` | 클래스 | 생성 완료 후, 그리고 모든 공개 루틴의 진입·종료 시 |

Eiffel 문서는 불변식이 **모든 공개 루틴의 사전조건과 사후조건에 암묵적으로 더해진다**고 설명한다. 구현자에게는 객체가 항상 안정 상태에서 시작한다는 좋은 소식이자, 루틴마다 종료 시 불변식을 복구해야 한다는 나쁜 소식이다. 사후조건에서는 `old` 로 진입 시점의 값을 참조할 수 있다.

```eiffel
deposit (sum: INTEGER)
    require
        non_negative: sum >= 0
    do
        add (sum)
    ensure
        one_more_deposit: deposit_count = old deposit_count + 1
        updated: balance = old balance + sum
    end
```

### 위반은 누구의 버그인가

Eiffel 문서의 가장 실용적인 두 문장이다.

- **사전조건 위반은 호출자의 버그**다. 호출자가 계약의 자기 몫을 지키지 않았다.
- **사후조건(또는 불변식) 위반은 공급자의 버그**다. 루틴이 자기 일을 하지 않았다.

그래서 어떤 계약이 깨졌는지만 보면 고칠 쪽이 정해진다. 또한 계약 위반은 사용자 입력 오류 같은 **예상된 실패가 아니라 프로그램 오류**라는 점이 중요하다. 외부 입력 검증은 계약 이전, 시스템 경계에서 별도로 해야 한다.

Eiffel 문서는 예외도 계약으로 설명한다. 루틴은 계약을 이행(성공)하거나 호출자에게 예외를 일으켜야(실패) 하며, 이행하지 못했는데 정상처럼 반환하는 것이 "최악의 방법" 이다.

### 상속과 계약: 하위 계약(subcontracting)

다형성으로 하위 클래스가 상위 클래스 대신 호출될 때, 호출자는 상위 클래스의 계약만 보고 코드를 짰다. Eiffel 문서의 [상속 장](https://www.eiffel.org/doc/eiffel/ET-_Inheritance)은 이를 **하위 계약**이라 부르고 규칙을 이렇게 정한다.

> 재정의가 올바르려면 새 사전조건은 원래 사전조건보다 **약하거나 같고**, 새 사후조건은 원래 사후조건보다 **강하거나 같아야** 한다.

Eiffel 은 이를 문법으로 강제한다. 재정의한 루틴에서는 `require`·`ensure` 를 쓸 수 없고, 대신 `require else`(원래 사전조건과 OR → 약해지기만 함)와 `ensure then`(원래 사후조건과 AND → 강해지기만 함)만 쓸 수 있다.

```
상위:   require P          ensure Q
하위:   require else P'    ensure then Q'
실효:   P or P'  (약화)     Q and Q'  (강화)
```

이것은 Barbara Liskov 와 Jeannette Wing 의 ["A behavioral notion of subtyping"](https://doi.org/10.1145/197320.197383) (ACM TOPLAS 16(6), 1994) 이 형식화한 행위적 하위 타입 개념, 즉 SOLID 의 리스코프 치환 원칙과 같은 방향의 규칙이다([SOLID 원칙]({% post_url 2026-10-10-cs300-185-solid-principles %})).

## 예제: 주류 언어에서 계약 쓰기

대부분의 언어에는 Eiffel 만큼의 계약 문법이 없으므로, 관례와 라이브러리로 흉내 낸다.

### Kotlin

Kotlin 표준 라이브러리의 [`require`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/require.html)는 조건이 거짓이면 `IllegalArgumentException` 을, [`check`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/check.html)는 `IllegalStateException` 을 던진다. 인자에 대한 사전조건에는 `require`, 객체 상태에 대한 조건(불변식, 사후조건)에는 `check` 를 쓰는 관례가 계약의 책임 구분과 맞는다.

```kotlin
class Account(initial: Long) {
    var balance: Long = initial
        private set
    private var withdrawCount = 0

    init { checkInvariant() }

    fun withdraw(amount: Long) {
        require(amount > 0) { "금액은 양수여야 한다: $amount" }              // 사전조건(호출자 책임)
        require(amount <= balance) { "잔액 초과: $amount > $balance" }
        val oldBalance = balance; val oldCount = withdrawCount              // Eiffel 의 old 흉내

        balance -= amount
        withdrawCount++

        check(balance == oldBalance - amount) { "사후조건 위반: 잔액" }       // 사후조건(공급자 책임)
        check(withdrawCount == oldCount + 1) { "사후조건 위반: 횟수" }
        checkInvariant()
    }

    private fun checkInvariant() = check(balance >= 0) { "불변식 위반: 음수 잔액 $balance" }
}
```

### Java

Java 의 `assert` 는 [공식 가이드](https://docs.oracle.com/javase/8/docs/technotes/guides/language/assert.html)에 따르면 **기본으로 꺼져 있고** `-ea`(`-enableassertions`)로 켠다. 같은 가이드는 **공개 메서드의 인자 검사에 assert 를 쓰지 말라**고 한다. 인자 검사는 메서드의 공개 명세(계약)의 일부라서 assert 를 켜든 끄든 지켜져야 하기 때문이다. 또 assert 식에는 부수 효과가 없어야 한다. 정리하면 공개 메서드의 사전조건은 `IllegalArgumentException` 등 명시적 예외로, 내부 사후조건·불변식은 `assert` 로 쓰는 것이 가이드의 방향이다.

```java
public void withdraw(long amount) {
    if (amount <= 0 || amount > balance)                    // 공개 사전조건: 항상 검사
        throw new IllegalArgumentException("invalid amount: " + amount);
    long old = balance;
    balance -= amount;
    assert balance == old - amount : "postcondition";       // 내부 사후조건: -ea 일 때만
    assert balance >= 0 : "invariant";
}
```

### Python

[icontract](https://github.com/Parquery/icontract) 라이브러리는 데코레이터로 사전·사후조건과 불변식을 선언한다. README 는 하위 클래스에서 사전조건의 약화와 사후조건·불변식의 강화를 지원한다고 밝히고, [사용 문서](https://icontract.readthedocs.io/en/latest/usage.html)는 `snapshot` 데코레이터로 호출 전 값을 떠 두었다가 사후조건에서 `OLD` 로 참조하는 방법(Eiffel 의 `old`)을 설명한다.

```python
import icontract

@icontract.invariant(lambda self: self.balance >= 0)
class Account:
    def __init__(self, balance: int) -> None:
        self.balance = balance

    @icontract.require(lambda self, amount: 0 < amount <= self.balance)
    @icontract.snapshot(lambda self: self.balance, name="balance")
    @icontract.ensure(lambda self, amount, OLD: self.balance == OLD.balance - amount)
    def withdraw(self, amount: int) -> None:
        self.balance -= amount
```

## 흔한 오해와 함정

- **"계약 = 입력 검증."** 사용자 입력, 외부 API 응답처럼 틀릴 수 있는 데이터의 검증은 계약이 아니라 정상 업무 흐름이다. 계약 위반은 프로그램 버그다. 둘을 섞으면 "잘못된 입력" 을 500 오류로 내거나, 버그를 400 으로 숨기게 된다.
- **"사전조건은 공급자가 방어적으로 다시 검사해야 안전하다."** DbC 의 요점은 반대다. 책임을 한쪽에 두고, 다른 쪽은 믿는다. 다만 공개 API 경계에서는 Java 가이드처럼 항상 켜진 명시적 검사로 계약을 강제하는 것이 실용적이다.
- **"하위 클래스가 더 엄격한 입력 조건을 가져도 된다."** 사전조건 강화는 상위 타입을 믿고 짠 호출자를 깨뜨린다. 하위 계약 규칙과 리스코프 치환 원칙 위반이다.
- **"테스트가 있으면 계약은 필요 없다."** 테스트는 고른 입력에서 확인하고, 계약은 실행되는 모든 호출에서 확인한다. 둘은 보완 관계다. 계약은 테스트에서 오라클 역할도 한다([테스트 주도 개발]({% post_url 2026-10-10-cs300-193-test-driven-development %})).

## 확인 문제

1. 사전조건 위반과 사후조건 위반은 각각 누구의 버그인가?
2. 클래스 불변식은 언제 참이어야 하는가?
3. 하위 클래스가 메서드를 재정의할 때 사전조건과 사후조건은 각각 어떻게 바뀔 수 있는가? Eiffel 은 이를 어떻게 강제하는가?
4. Java 공식 가이드가 공개 메서드의 인자 검사에 `assert` 를 쓰지 말라는 이유는?
5. 사용자가 폼에 음수 금액을 입력한 경우와, 내부 코드가 `withdraw(-1)` 을 호출한 경우는 어떻게 다르게 다뤄야 하는가?

### 풀이

1. 사전조건 위반은 호출자(client)의 버그, 사후조건·불변식 위반은 공급자(루틴)의 버그다.
2. 생성이 끝난 뒤, 그리고 모든 공개 루틴의 진입과 종료 시점. 공개 루틴 실행 도중에는 일시적으로 깨질 수 있다.
3. 사전조건은 같거나 약해질 수만 있고, 사후조건은 같거나 강해질 수만 있다. Eiffel 은 재정의 루틴에서 `require else`(OR)와 `ensure then`(AND)만 허용해 이를 문법으로 보장한다.
4. assert 는 기본으로 꺼져 있어 검사가 사라질 수 있는데, 인자 검사는 메서드의 공개 명세(계약)의 일부이므로 assert 활성화 여부와 무관하게 항상 지켜져야 하기 때문이다.
5. 폼 입력은 예상 가능한 외부 데이터 오류이므로 경계에서 검증해 사용자에게 알려 주는 정상 흐름이다. 내부 호출의 `withdraw(-1)` 은 호출자가 사전조건을 어긴 프로그램 버그이므로 즉시 실패시키고 호출자 코드를 고쳐야 한다.

## 더 읽을거리 (References)

- Bertrand Meyer, ["Applying 'design by contract'"](https://doi.org/10.1109/2.161279), IEEE Computer 25(10), 40–51, 1992
- Eiffel 문서, [Design by Contract, Assertions and Exceptions](https://www.eiffel.org/doc/eiffel/ET-_Design_by_Contract_%28tm%29%2C_Assertions_and_Exceptions), [Inheritance](https://www.eiffel.org/doc/eiffel/ET-_Inheritance)
- C. A. R. Hoare, ["An axiomatic basis for computer programming"](https://doi.org/10.1145/363235.363259), Communications of the ACM 12(10), 1969
- B. Liskov, J. Wing, ["A behavioral notion of subtyping"](https://doi.org/10.1145/197320.197383), ACM TOPLAS 16(6), 1994
- Oracle, [Programming With Assertions](https://docs.oracle.com/javase/8/docs/technotes/guides/language/assert.html)
- Kotlin, [require](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/require.html), [check](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/check.html)
- [icontract](https://github.com/Parquery/icontract), [Usage](https://icontract.readthedocs.io/en/latest/usage.html)
- CS300: [SOLID 원칙]({% post_url 2026-10-10-cs300-185-solid-principles %}), [테스트 주도 개발]({% post_url 2026-10-10-cs300-193-test-driven-development %})
