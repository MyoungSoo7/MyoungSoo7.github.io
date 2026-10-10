---
layout: post
title: "[CS300 #029] 객체지향 1 — 캡슐화와 추상화"
date: 2026-10-10 18:29:00 +0900
categories: [cs]
tags: [cs300, programming, oop, encapsulation, abstraction]
---

컴퓨터공학 300 주제 시리즈의 029번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

캡슐화는 데이터와 그 데이터를 바꾸는 규칙을 한 곳에 묶고 내부를 숨기는 것이고, 추상화는 사용하는 쪽이 알아야 할 것만 남긴 인터페이스를 정하는 것이다. 둘 다 "변경이 퍼지는 범위를 좁힌다"는 같은 목적을 가진다.

## 왜 필요한가

잔액 필드가 공개되어 있는 은행 계좌 클래스를 생각해 보자. 코드 곳곳에서 `account.balance -= amount` 를 직접 한다. 어느 날 "잔액은 음수가 될 수 없다"는 규칙이 생긴다. 이 규칙을 지키려면 `balance` 를 건드리는 모든 곳을 찾아 고쳐야 한다. 한 곳이라도 놓치면 버그다.

캡슐화는 이 문제를 원천적으로 막는다. 잔액을 바꾸는 길을 `deposit`, `withdraw` 두 메서드로 좁혀 두면 규칙은 그 두 곳에만 넣으면 된다. 추상화는 한발 더 나아가 "저장소가 메모리인지 S3 인지"처럼 호출자가 몰라도 되는 것을 아예 감춘다.

## 핵심 개념

### 정보 은닉: 출발점

1972년 파르나스(Parnas)는 논문 "On the Criteria To Be Used in Decomposing Systems into Modules"에서 모듈을 나누는 기준을 처리 순서가 아니라 **바뀔 가능성이 큰 설계 결정**으로 삼아야 한다고 주장했다. 각 모듈은 하나의 설계 결정을 다른 모듈로부터 숨긴다. 이것이 **정보 은닉**이고, 객체지향의 캡슐화는 이 원칙을 언어 기능으로 지원한 것이다.

### 캡슐화

캡슐화의 두 요소:

1. **묶기**: 상태(필드)와 그 상태를 다루는 연산(메서드)을 한 단위(클래스)에 둔다.
2. **숨기기**: 외부에서 상태를 직접 건드리지 못하게 하고, 정해진 연산으로만 바꾸게 한다.

숨기기의 목적은 **불변식(invariant) 보호**다. "잔액 ≥ 0", "시작 시각 ≤ 종료 시각", "리스트는 항상 정렬되어 있다" 같은 규칙을 객체가 스스로 지킨다. 생성자에서 불변식을 세우고, 모든 공개 메서드가 불변식을 유지하면, 객체는 언제나 유효한 상태다.

언어마다 숨기는 강도가 다르다.

| 언어 | 수단 | 강제력 |
|---|---|---|
| Java, C++ | `private`, `protected`, `public` | 컴파일러가 강제 |
| Python | `_name` 관례, `__name` 이름 맹글링 | 관례. 맹글링은 이름을 `_클래스__name` 으로 바꿀 뿐 |
| JavaScript | `#field` 사설 필드 | 언어가 강제 |
| Go | 소문자 시작 식별자는 패키지 밖에서 안 보임 | 컴파일러가 강제 |

Python 공식 튜토리얼은 객체 내부에서만 접근할 수 있는 "private" 변수는 Python 에 존재하지 않으며, 밑줄 접두사는 API 가 아닌 부분이라는 관례라고 설명한다. `__spam` 형태는 서브클래스와의 이름 충돌을 피하려는 이름 맹글링이다([Classes — Private Variables](https://docs.python.org/3/tutorial/classes.html#private-variables)).

### 게터·세터가 캡슐화는 아니다

모든 필드에 `getX()`, `setX()` 를 기계적으로 붙이면 필드를 공개한 것과 다를 바 없다. 캡슐화된 클래스는 "데이터를 꺼내 밖에서 계산하라"가 아니라 "객체에게 일을 시키라"는 방향으로 설계된다. `account.setBalance(account.getBalance() - 100)` 대신 `account.withdraw(100)` 이다. 이를 흔히 "묻지 말고 시켜라(Tell, Don't Ask)"라고 부른다.

Python 의 `property` 는 필드 접근 문법을 유지하면서 뒤에 메서드를 끼워 넣는다. 처음엔 공개 속성으로 시작했다가 나중에 검증이 필요해지면 호출 코드를 바꾸지 않고 `property` 로 감쌀 수 있다. 이 메커니즘은 디스크립터 프로토콜 위에 구현되어 있다([Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html)).

### 추상화

추상화는 복잡한 것을 **무엇을 하는가**로만 표현하고 **어떻게 하는가**는 감추는 것이다. 객체지향에서는 주로 인터페이스와 추상 클래스로 나타난다.

```
        호출자 코드
            │  save(key, data) / load(key)  ← 이것만 안다
            ▼
     ┌──────────────┐
     │  Storage     │  (추상: 계약)
     └──────────────┘
       ▲        ▲        ▲
  MemoryStorage  FileStorage  S3Storage   (구체: 구현)
```

호출자는 `Storage` 계약에만 의존한다. 테스트에서는 `MemoryStorage` 를, 운영에서는 `S3Storage` 를 끼운다. 구현을 바꿔도 호출자는 손대지 않는다.

Python 은 `abc` 모듈로 추상 기반 클래스를 정의한다. `@abstractmethod` 로 표시한 메서드를 모두 구현하지 않은 클래스는 인스턴스를 만들 수 없다([abc](https://docs.python.org/3/library/abc.html)). Java 는 `interface` 와 `abstract class` 로 같은 일을 한다.

### 캡슐화와 추상화의 관계

둘은 자주 섞여 쓰이지만 초점이 다르다.

- **추상화**: 바깥에서 본 모습. "무엇을 보여 줄까"를 정한다.
- **캡슐화**: 안쪽의 보호. "무엇을 숨기고 어떻게 지킬까"를 정한다.

좋은 추상화는 캡슐화가 있어야 유지된다. 내부가 새어 나가면 호출자가 내부에 의존하게 되고, 추상화의 경계가 무너진다. 흔히 "새는 추상화(leaky abstraction)"라고 부르는 현상, 예를 들어 ORM 을 썼는데 결국 SQL 성능을 알아야 하는 상황도 이 경계의 한계를 보여 준다.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
from abc import ABC, abstractmethod

class Account:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self._balance = 0
        self.deposit(balance)          # 생성자도 같은 규칙을 거친다

    @property
    def balance(self):                 # 읽기 전용 공개
        return self._balance

    def deposit(self, amount):
        if amount < 0:
            raise ValueError("음수 입금 불가")
        self._balance += amount

    def withdraw(self, amount):
        if amount > self._balance:     # 불변식: 잔액 >= 0
            raise ValueError("잔액 부족")
        self._balance -= amount

acc = Account("kim", 100)
acc.withdraw(30)
print(acc.balance)                     # 70
acc.balance = 1_000_000
# AttributeError: property 'balance' of 'Account' object has no setter
acc.withdraw(500)
# ValueError: 잔액 부족

class Secret:
    def __init__(self):
        self.__token = "abc"
s = Secret()
print(hasattr(s, "__token"), s._Secret__token)   # False abc  맹글링일 뿐 숨김이 아니다

class Storage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...
    @abstractmethod
    def load(self, key: str) -> bytes: ...

class MemoryStorage(Storage):
    def __init__(self):
        self._d = {}
    def save(self, key, data):
        self._d[key] = data
    def load(self, key):
        return self._d[key]

Storage()
# TypeError: Can't instantiate abstract class Storage without an implementation
#            for abstract methods 'load', 'save'
st: Storage = MemoryStorage()
st.save("a", b"hi"); print(st.load("a"))   # b'hi'
```

## 현업에서는

- **도메인 모델**: 주문, 결제, 정산 같은 도메인 객체는 상태 전이 규칙("결제 완료된 주문만 배송 가능")을 메서드 안에 가둔다. 상태 필드를 서비스 계층 여기저기서 직접 바꾸면 규칙 위반이 쌓인다.
- **포트와 어댑터**: 외부 시스템(DB, 메시지 큐, 결제 대행)을 인터페이스 뒤에 숨기면 테스트에서 가짜 구현을 끼우기 쉽고, 공급자를 바꿀 때 영향이 어댑터 하나로 끝난다.
- **공개 API 의 범위**: 라이브러리에서 한번 공개한 필드·메서드는 사용자가 의존하므로 쉽게 못 지운다. 공개 범위는 최소로 시작한다. Python 패키지에서 `_` 로 시작하는 모듈·함수를 내부용으로 구분하는 관례가 이 역할을 한다.
- **쿠버네티스의 추상화**: 서비스(Service)는 파드 집합 앞에 고정된 이름과 주소를 두고, 파드가 어느 노드에 몇 개 떠 있는지는 숨긴다. 호출자는 서비스 이름만 안다. 객체지향 밖에서도 같은 원리가 쓰인다.

## 확인 문제

1. 파르나스가 제안한 모듈 분해 기준은 무엇인가?
2. 모든 필드에 게터와 세터를 붙인 클래스가 캡슐화되었다고 보기 어려운 이유는?
3. Python 의 `self.__token` 은 외부 접근을 완전히 막는가?
4. 추상 기반 클래스에서 추상 메서드 하나를 구현하지 않은 서브클래스를 인스턴스화하면 어떻게 되는가?
5. 캡슐화와 추상화의 차이를 한 문장씩으로 설명하라.

### 풀이

1. 바뀔 가능성이 큰 설계 결정을 하나씩 숨기도록 모듈을 나눈다(정보 은닉).
2. 외부가 여전히 임의의 값을 넣고 꺼내 바깥에서 규칙을 처리하므로 불변식을 객체가 지키지 못한다.
3. 막지 않는다. 이름이 `_Secret__token` 으로 바뀔 뿐이며 그 이름으로 접근할 수 있다. 목적은 서브클래스와의 이름 충돌 방지다.
4. `TypeError` 가 나며 인스턴스가 만들어지지 않는다.
5. 추상화는 바깥에 무엇을 할 수 있는지만 보여 주는 것, 캡슐화는 안쪽 상태를 숨기고 정해진 연산으로만 바꾸게 해 불변식을 지키는 것이다.

## 더 읽을거리 (References)

- D. L. Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules", CACM 15(12), 1972
- Python Tutorial, [Classes](https://docs.python.org/3/tutorial/classes.html)
- Python Docs, [abc — Abstract Base Classes](https://docs.python.org/3/library/abc.html)
- Python Docs, [Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html) — `property` 의 동작 원리
