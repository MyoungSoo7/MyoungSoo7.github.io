---
layout: post
title: "[SE100 #045] 테스트 더블 — 목·스텁·페이크·스파이"
date: 2026-10-11 17:01:44 +0900
categories: [software-engineering]
tags: [se100, software-testing, test-double, mock-objects, xunit-patterns]
---

소프트웨어 공학 100 주제 시리즈의 45번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

**테스트 더블** 은 테스트를 위해 실제 객체 대신 끼워 넣는 모든 대역의 총칭이고(Gerard Meszaros), 쓰임에 따라 더미·스텁·스파이·목·페이크로 나뉜다. 구분의 핵심은 "대역이 **간접 입력을 공급**하는가, **간접 출력을 관찰**하는가, 아니면 **진짜처럼 동작**하는가" 다. 어떤 대역을 쓰느냐는 결국 상태를 검증할지 행위를 검증할지의 선택이다.

## 왜 필요한가

테스트 대상(SUT, system under test)이 결제 게이트웨이, 메일 서버, 현재 시각, 난수에 의존하면 테스트는 느려지고(네트워크), 비결정적이 되고(시각·난수), 위험해진다(진짜 결제). 그래서 의존 대상(DOC, depended-on component)을 대역으로 바꾼다.

그런데 팀마다 이 대역을 다 "목" 이라고 부르면 대화가 어긋난다.

- A: "목으로 바꿨어요." (고정 응답만 돌려주는 객체를 뜻함)
- B: "그럼 호출 횟수 검증도 넣었죠?" (기대 호출을 검증하는 객체를 떠올림)

두 사람은 전혀 다른 테스트를 상상하고 있다. 이름이 다르면 검증하는 것이 다르고, 깨지는 이유도 다르다.

## 핵심 개념

### Meszaros 의 다섯 가지

Meszaros 는 *xUnit Test Patterns* 에서 영화의 스턴트 대역(stunt double)에서 따온 **Test Double** 을 총칭으로 쓰고, 이미 널리 쓰이던 이름과 겹치지 않게 하려 했다. Martin Fowler 의 [TestDouble](https://martinfowler.com/bliki/TestDouble.html) (2006) 이 요약한 정의는 다음과 같다.

| 종류 | 정의(요약) | 검증 대상 |
|---|---|---|
| 더미(Dummy) | 전달은 되지만 실제로 쓰이지 않음. 주로 파라미터 목록을 채우는 용도 | 없음 |
| 페이크(Fake) | 실제로 동작하는 구현이지만 운영에는 맞지 않는 지름길을 씀. 예: 인메모리 DB | SUT 의 최종 상태 |
| 스텁(Stub) | 테스트 중 호출에 미리 준비한 응답을 돌려줌 | SUT 의 상태(스텁은 입력 공급) |
| 스파이(Spy) | 스텁이면서 어떻게 호출됐는지를 기록. 예: 보낸 메일 수를 기록하는 메일 서비스 | 기록된 호출(사후 단언) |
| 목(Mock) | 받을 호출에 대한 **기대** 를 미리 프로그래밍. 예상 밖 호출에 예외를 던질 수 있고, 검증 단계에서 기대한 호출을 모두 받았는지 확인 | 호출 자체(행위) |

[xunitpatterns.com 의 Test Double 항목](http://xunitpatterns.com/Test%20Double.html) 은 이 차이를 **간접 입력(indirect input)** 과 **간접 출력(indirect output)** 으로 설명한다.

```
          직접 입력 ─▶ ┌───────┐ ─▶ 직접 출력 (반환값)
                      │  SUT  │
   간접 입력 ◀── 스텁 ─┤       ├─▶ 간접 출력 ──▶ 스파이 / 목
   (DOC 가 SUT 에 주는 값)    (SUT 가 DOC 에 하는 호출)
```

- 스텁은 SUT 가 DOC 에서 **받는** 값을 통제한다. "재고 조회가 0 을 돌려주면?"
- 스파이와 목은 SUT 가 DOC 에 **보내는** 것을 관찰한다. "주문 실패 시 알림을 보냈는가?"
- 페이크는 둘 다 아니다. 같은 기능을 더 단순하게 구현해, 검증과 무관한 이유(속도, 설치 부담)로 실물을 대체한다.

스파이와 목의 차이는 **검증 시점과 위치** 다. 스파이는 기록만 하고 테스트가 끝에 단언한다. 목은 기대를 먼저 선언하고 목 스스로(또는 프레임워크가) 검증한다.

### 상태 검증 대 행위 검증

Fowler 의 [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html) (2007년 판) 는 두 가지 차이를 구분한다.

1. **검증 방식**: 실행 후 SUT·협력 객체의 상태를 보는 **상태 검증** 대, SUT 가 협력 객체를 올바르게 호출했는지 보는 **행위 검증**.
2. **TDD 스타일**: 가능하면 실제 객체를 쓰고 불편할 때만 대역을 쓰는 **고전파(classical)** 대, 흥미로운 행위가 있는 객체는 항상 목으로 바꾸는 **목 지향파(mockist)**.

Fowler 의 예에서 고전파는 창고(warehouse)는 진짜를, 메일 서비스는 대역을 쓴다. 목 지향파는 둘 다 목으로 쓴다.

### 목은 설계 도구라는 관점

Freeman, Mackinnon, Pryce, Walnes 의 [Mock Roles, not Objects](https://doi.org/10.1145/1028664.1028765) (OOPSLA 2004 Companion, [PDF](https://www.jmock.org/oopsla2004.pdf)) 는 초록에서 목 객체가 테스트 격리 기법이 아니라 **코드베이스 안에서 일관된 타입 체계를 발견하도록 이끄는** TDD 의 확장이라고 주장하고, 서드파티 라이브러리로부터 테스트를 격리하는 기법으로서는 흔히 생각하는 것보다 덜 흥미롭다고 쓴다. 논문이 정리한 실천 중 몇 가지:

| 절 | 지침 |
|---|---|
| 4.3 | 일어나면 **안 되는** 일은 명시하라 |
| 4.4 | 테스트에서는 **가능한 한 적게** 명세하라 — 구현의 부산물까지 검사하면 테스트가 깨지기 쉬워진다 |
| 4.5 | 다른 객체와 관계가 없는 경계 객체(값, 계산)에는 목을 쓰지 마라 |
| 4.6 | 목에 행위를 더하지 마라 |
| 4.7 | 직접 이웃만 목으로 만들어라 |
| 4.8 | 목이 너무 많으면 책임 배치나 객체 크기를 의심하라 |

## 실무 적용

### 같은 테스트, 다른 대역

```python
from unittest.mock import create_autospec
from datetime import datetime

class Clock:               # DOC
    def now(self) -> datetime: ...
class Mailer:              # DOC
    def send(self, to: str, body: str) -> None: ...

class FakeMailer(Mailer):  # 페이크 겸 스파이: 보낸 메일을 리스트에 저장
    def __init__(self): self.sent = []
    def send(self, to, body): self.sent.append((to, body))

def test_overdue_notice_with_stub_and_spy():
    clock = create_autospec(Clock, instance=True)        # 스텁: 간접 입력 통제
    clock.now.return_value = datetime(2026, 3, 2)
    mailer = FakeMailer()                                 # 스파이: 간접 출력 기록
    LibraryService(clock, mailer).send_overdue_notices()
    assert mailer.sent == [("kim@example.com", "반납 기한이 지났습니다")]

def test_overdue_notice_with_mock():
    clock = create_autospec(Clock, instance=True)
    clock.now.return_value = datetime(2026, 3, 2)
    mailer = create_autospec(Mailer, instance=True)      # 목: 호출 기대 검증
    LibraryService(clock, mailer).send_overdue_notices()
    mailer.send.assert_called_once_with("kim@example.com", "반납 기한이 지났습니다")
```

`create_autospec` 은 [unittest.mock](https://docs.python.org/3/library/unittest.mock.html) 의 기능으로, 실제 클래스의 시그니처를 따르는 목을 만든다. 실제에 없는 메서드를 부르거나 인자 수가 틀리면 바로 실패하므로, "목은 통과하는데 실물과 안 맞는" 사고를 줄인다. 맨 `Mock()` 은 어떤 속성 접근도 받아 주므로 오타가 그대로 통과할 수 있다.

### 고르는 기준

| 상황 | 추천 |
|---|---|
| 시각·난수·설정값처럼 값만 필요 | 스텁 |
| "보냈는가" 가 결과이고 외부로 나가는 부수효과 | 스파이 또는 목 |
| 저장소·캐시처럼 여러 호출이 상태로 얽힘 | 페이크(인메모리 구현) |
| 값 객체, 순수 계산 | 대역 쓰지 말고 진짜 |
| 서드파티 SDK | 직접 목으로 만들기보다 **우리 쪽 인터페이스(어댑터)** 를 두고 그것을 대역으로 |

### 페이크가 실물과 멀어지지 않게

페이크와 스텁은 실물과 어긋날 수 있다. Fowler 의 [ContractTest](https://martinfowler.com/bliki/ContractTest.html) 는 외부 서비스를 대역으로 테스트하되, 대역이 실제 서비스와 같은 결과를 내는지 확인하는 **계약 테스트** 를 따로, 외부 서비스의 변경 주기에 맞춰 돌리라고 권한다. 저장소 페이크라면 같은 테스트 묶음을 페이크와 실제 DB(테스트 컨테이너)에 모두 돌리는 추상 테스트 클래스가 실용적이다.

```kotlin
abstract class OrderRepositoryContract {
    abstract fun repo(): OrderRepository
    @Test fun `저장한 주문을 ID 로 다시 찾는다`() { /* ... */ }
    @Test fun `없는 ID 는 null 을 돌려준다`() { /* ... */ }
}
class InMemoryOrderRepositoryTest : OrderRepositoryContract() { override fun repo() = InMemoryOrderRepository() }
class JdbcOrderRepositoryTest : OrderRepositoryContract() { override fun repo() = JdbcOrderRepository(testDataSource) }
```

## 흔한 오해와 함정

- **"목" 을 모든 대역의 이름으로 쓴다.** Mockito 의 `mock()` 이나 `unittest.mock.Mock` 으로 만든 객체도 쓰는 방식에 따라 스텁일 수도 스파이일 수도 목일 수도 있다. 라이브러리 이름이 아니라 **테스트에서 맡은 역할** 로 부른다.
- **모든 호출을 검증한다.** 구현 세부 호출까지 `verify` 하면 동작은 그대로인데 리팩터링만 해도 테스트가 깨진다. Freeman 외의 "가능한 한 적게 명세하라" 와 Fowler 가 지적한 목 지향 테스트의 구현 결합 문제가 같은 이야기다.
- **목이 목을 돌려주는 연쇄.** `a.getB().getC().doIt()` 을 테스트하려고 목 세 개를 엮는다면 테스트가 아니라 설계(디미터 법칙 위반)가 문제다.
- **스텁에서 단언하기.** 스텁은 입력을 공급하는 역할이다. 스텁 호출 여부까지 검사하기 시작하면 목이 된 것이고, 그만큼 테스트가 구현에 묶인다.
- **페이크를 검증 없이 방치한다.** 인메모리 저장소가 실제 DB 의 유일 제약·트랜잭션·정렬을 흉내 내지 않으면 테스트는 통과하고 운영은 깨진다.

## 확인 문제

1. 스텁과 목의 차이를 간접 입력·간접 출력으로 설명하라.
2. 스파이와 목은 둘 다 SUT 의 호출을 관찰한다. 무엇이 다른가?
3. 고전파와 목 지향파는 "창고에서 재고를 빼고 메일을 보내는 주문 처리" 를 각각 어떻게 테스트하는가?
4. `Mock()` 대신 `create_autospec` 을 쓰는 이유는?
5. 인메모리 페이크 저장소를 쓰는 테스트가 통과했는데 운영에서 중복 키 오류가 났다. 무엇을 추가해야 하는가?

### 풀이

1. 스텁은 SUT 가 의존 대상에서 받는 값(간접 입력)을 테스트가 통제하게 해 준다. 목은 SUT 가 의존 대상에 하는 호출(간접 출력)에 대한 기대를 미리 정해 두고 그 호출이 일어났는지 검증한다.
2. 스파이는 호출을 기록만 하고 테스트가 끝난 뒤 그 기록에 단언한다. 목은 기대를 먼저 선언하고, 목이나 프레임워크가 예상 밖 호출이나 누락된 호출을 검증한다.
3. 고전파는 실제 창고 객체를 쓰고 메일 서비스만 대역으로 바꾼 뒤 창고의 재고 상태를 검증한다. 목 지향파는 창고와 메일 서비스를 모두 목으로 만들고 각각에 대한 호출을 검증한다.
4. 실제 클래스의 시그니처를 따르므로 없는 메서드 호출이나 잘못된 인자 수가 즉시 실패한다. 맨 `Mock()` 은 아무 속성이나 받아들여 오타와 인터페이스 불일치를 숨긴다.
5. 같은 계약 테스트 묶음을 실제 DB 구현에도 돌려, 페이크가 유일 제약 같은 실물의 동작을 따르는지 확인한다. 어긋나면 페이크를 고친다.

## 더 읽을거리 (References)

- Gerard Meszaros, [Test Double](http://xunitpatterns.com/Test%20Double.html), xunitpatterns.com / *xUnit Test Patterns: Refactoring Test Code*, Addison-Wesley, 2007 (서지 정보)
- Martin Fowler, [TestDouble](https://martinfowler.com/bliki/TestDouble.html), 2006
- Martin Fowler, [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html), 2007
- S. Freeman, T. Mackinnon, N. Pryce, J. Walnes, [Mock Roles, not Objects](https://doi.org/10.1145/1028664.1028765), OOPSLA 2004 Companion
- Martin Fowler, [ContractTest](https://martinfowler.com/bliki/ContractTest.html)
- Python 문서, [unittest.mock — mock object library](https://docs.python.org/3/library/unittest.mock.html)
- Mockito, [Mockito Javadoc](https://javadoc.io/doc/org.mockito/mockito-core/latest/org/mockito/Mockito.html)
- Steve Freeman, Nat Pryce, *Growing Object-Oriented Software, Guided by Tests*, Addison-Wesley, 2009 (서지 정보)
