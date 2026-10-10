---
layout: post
title: "[CS300 #185] SOLID 원칙 — 바뀌는 곳과 안 바뀌는 곳을 떼어 놓는 다섯 가지 규칙"
date: 2026-10-10 21:05:00 +0900
categories: [cs]
tags: [cs300, software-engineering, solid, object-oriented-design, liskov-substitution]
---

컴퓨터공학 300 주제 시리즈의 185번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

SOLID 는 객체지향 설계의 다섯 원칙(단일 책임, 개방-폐쇄, 리스코프 치환, 인터페이스 분리, 의존성 역전)의 머리글자다. 공통 목표는 하나다. **변경이 생겼을 때 고쳐야 하는 곳을 좁게 만드는 것.**

## 왜 필요한가

처음 짠 코드는 대개 잘 돌아간다. 문제는 두 번째, 세 번째 요구사항이 들어올 때 생긴다. 결제 수단 하나를 추가하는데 파일 일곱 개를 고쳐야 하고, 이메일 문구를 바꿨더니 정산 테스트가 깨진다.

이런 일은 코드가 "함께 바뀌어야 할 것" 과 "따로 바뀌어야 할 것" 을 구분하지 않고 엉켜 있을 때 생긴다. SOLID 는 그 엉킴을 풀 때 쓰는 체크리스트다. 원칙들은 Robert C. Martin 이 여러 글과 책에서 정리했고, Michael Feathers 가 다섯 개의 머리글자를 묶어 SOLID 라는 이름을 붙였다.

## 핵심 개념

### S — 단일 책임 원칙 (Single Responsibility)

> 모듈은 하나의, 오직 하나의 액터(actor)에 대해서만 책임져야 한다.

"한 가지 일만 하라" 로 흔히 요약되지만, Martin 이 *Clean Architecture* 에서 다시 정리한 표현은 **변경을 요구하는 주체**에 초점을 둔다.

```
class Employee:
    calculate_pay()    ← 회계팀이 바꿔 달라고 함
    report_hours()     ← 인사팀이 바꿔 달라고 함
    save()             ← DBA 가 바꿔 달라고 함
```

세 부서의 요구가 한 클래스에서 부딪친다. 회계팀 요청으로 공통 헬퍼를 고쳤는데 인사팀 보고서 숫자가 바뀌는 사고가 여기서 나온다. 액터별로 클래스를 나누면 한 부서의 변경이 다른 부서 코드에 닿지 않는다.

### O — 개방-폐쇄 원칙 (Open-Closed)

> 소프트웨어 개체는 확장에는 열려 있고, 수정에는 닫혀 있어야 한다.

Bertrand Meyer 가 1988년 *Object-Oriented Software Construction* 에서 제시했다. 새 기능을 넣을 때 기존 코드를 고치지 않고 **새 코드를 추가**해서 해결할 수 있어야 한다는 뜻이다.

```python
# 닫혀 있지 않은 코드: 결제 수단이 늘 때마다 이 함수를 고친다
def pay(method, amount):
    if method == "card":
        ...
    elif method == "bank":
        ...
    elif method == "point":   # 새로 추가할 때마다 여기를 수정
        ...
```

결제 수단을 공통 인터페이스 뒤에 두고, 새 수단은 새 클래스로 추가하면 `pay` 를 쓰는 쪽은 바뀌지 않는다. 다음 글들에서 볼 전략 패턴이 이 원칙의 대표 구현이다.

### L — 리스코프 치환 원칙 (Liskov Substitution)

> 상위 타입의 객체를 하위 타입의 객체로 바꿔도 프로그램의 올바름이 깨지지 않아야 한다.

Barbara Liskov 가 1987년 기조연설에서 제시하고, Liskov 와 Jeannette Wing 이 1994년 논문 "A Behavioral Notion of Subtyping" 에서 형식화했다. 핵심은 **문법이 아니라 행위(계약)의 호환성**이다. 하위 타입은

- 사전조건을 더 강하게 만들면 안 되고(더 까다로운 입력을 요구하지 않는다),
- 사후조건을 더 약하게 만들면 안 되며(약속한 결과를 덜 보장하지 않는다),
- 상위 타입의 불변식을 유지해야 한다.

상속 문법이 허락한다고 해서 치환이 안전한 것은 아니다. 아래 "직접 해 보기" 의 정사각형 예가 고전적인 반례다.

### I — 인터페이스 분리 원칙 (Interface Segregation)

> 클라이언트는 자신이 쓰지 않는 메서드에 의존하도록 강요받아서는 안 된다.

`Printer` 인터페이스에 `print`, `scan`, `fax` 가 다 들어 있으면, 인쇄만 하는 단순 프린터도 `scan` 과 `fax` 를 "지원 안 함" 예외로 구현해야 한다. 그리고 `fax` 시그니처가 바뀌면 팩스를 안 쓰는 클라이언트까지 다시 빌드·배포해야 한다. 역할별로 작은 인터페이스(`Printable`, `Scannable`)로 나누는 것이 해법이다.

### D — 의존성 역전 원칙 (Dependency Inversion)

> 상위 수준 모듈은 하위 수준 모듈에 의존해서는 안 된다. 둘 다 추상에 의존해야 한다.

```
역전 전:  SignupService ──────────────> EmailNotifier (구체)

역전 후:  SignupService ──> Notifier (추상) <── EmailNotifier
                                         <── SmsNotifier
                                         <── FakeNotifier (테스트)
```

"가입시키고 알린다" 는 비즈니스 정책이 "SMTP 로 보낸다" 는 세부 구현을 모르게 된다. 화살표(의존 방향)가 세부 구현 쪽에서 추상 쪽을 향하도록 **뒤집혔기** 때문에 역전이라 부른다. 실제 객체를 바깥에서 넣어 주는 의존성 주입(DI)이 이 원칙을 실현하는 흔한 방법이다.

### 한눈에 보기

| 원칙 | 질문 | 위반 신호 |
|---|---|---|
| SRP | 이 모듈을 바꿔 달라고 하는 사람이 여럿인가? | 서로 다른 이유로 같은 파일이 자주 수정된다 |
| OCP | 새 종류를 추가할 때 기존 코드를 고치는가? | 타입별 `if/elif` 가 여러 곳에 흩어져 있다 |
| LSP | 하위 타입을 넣어도 호출자가 놀라지 않는가? | `isinstance` 로 하위 타입을 따로 처리한다 |
| ISP | 쓰지 않는 메서드까지 구현·의존하는가? | "지원하지 않음" 예외를 던지는 메서드가 있다 |
| DIP | 정책 코드가 구체 구현을 직접 생성하는가? | 단위 테스트에 실제 DB·메일 서버가 필요하다 |

## 직접 해 보기

LSP 위반과 DIP 적용을 한 파일에서 확인한다. 파이썬은 [`typing.Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) 로 상속 없이 구조적 인터페이스를 정의할 수 있다. 명시적 상속을 강제하고 싶으면 [`abc` 모듈](https://docs.python.org/3/library/abc.html)의 추상 기반 클래스를 쓴다.

```python
from typing import Protocol

# --- LSP 위반: 정사각형은 직사각형인가? ---
class Rectangle:
    def __init__(self, w, h):
        self._w, self._h = w, h
    def set_width(self, w):  self._w = w
    def set_height(self, h): self._h = h
    def area(self): return self._w * self._h

class Square(Rectangle):
    def __init__(self, side):
        super().__init__(side, side)
    def set_width(self, w):  self._w = self._h = w   # 정사각형을 유지하려고
    def set_height(self, h): self._w = self._h = h

def stretch(r: Rectangle):
    """직사각형 계약: 너비만 바꾸면 높이는 그대로다."""
    r.set_width(5)
    r.set_height(4)
    return r.area()          # 계약상 항상 20

for shape in (Rectangle(2, 3), Square(3)):
    print(f"{type(shape).__name__:9s} area={stretch(shape)} (기대 20)")

# --- DIP: 상위 정책이 하위 구현이 아니라 추상에 의존 ---
class Notifier(Protocol):
    def send(self, to: str, msg: str) -> None: ...

class EmailNotifier:
    def send(self, to, msg): print(f"  [email] {to}: {msg}")

class FakeNotifier:                # 테스트용. 상속 없이 Protocol 만족
    def __init__(self): self.sent = []
    def send(self, to, msg): self.sent.append((to, msg))

class SignupService:
    def __init__(self, notifier: Notifier):   # 구체 클래스를 모른다
        self.notifier = notifier
    def signup(self, email):
        self.notifier.send(email, "가입을 환영합니다")

SignupService(EmailNotifier()).signup("a@example.com")
fake = FakeNotifier()
SignupService(fake).signup("b@example.com")
print("  fake 기록:", fake.sent)
```

실행 결과:

```
Rectangle area=20 (기대 20)
Square    area=16 (기대 20)
  [email] a@example.com: 가입을 환영합니다
  fake 기록: [('b@example.com', '가입을 환영합니다')]
```

`Square` 는 문법적으로 완벽한 하위 클래스지만 "너비를 바꿔도 높이는 그대로" 라는 직사각형의 사후조건을 약하게 만들었다. 수학에서 정사각형이 직사각형의 일종이라는 사실이, **변경 가능한 객체**에서 치환 가능성을 보장하지 않는다. 해법은 상속을 끊거나, 객체를 불변으로 만들어 `set_width` 자체를 없애는 것이다.

DIP 쪽은 `SignupService` 코드를 한 줄도 바꾸지 않고 실제 메일 발송과 테스트용 가짜를 갈아 끼웠다. 단위 테스트 글에서 다룰 테스트 더블이 바로 이 구조 위에서 동작한다.

## 현업에서는

- **원칙은 리뷰 어휘다.** "이 클래스가 결제와 알림을 둘 다 아는 게 SRP 측면에서 괜찮을까요?" 처럼 원칙 이름을 쓰면 리뷰 의견이 취향 싸움이 아니라 설계 근거가 된다.
- **과하게 적용하면 오히려 해롭다.** 구현이 하나뿐이고 바뀔 계획도 없는 곳에 인터페이스·팩토리·DI 설정을 겹겹이 쌓으면 읽기만 어려워진다. 두 번째 구현이 실제로 필요해질 때 추상을 꺼내도 늦지 않다.
- **DIP 는 테스트 용이성으로 드러난다.** 단위 테스트를 돌리는 데 데이터베이스 컨테이너가 꼭 떠 있어야 한다면, 정책 코드가 구체 구현에 직접 의존하고 있다는 신호다.
- **쿠버네티스도 같은 생각을 한다.** 쿠버네티스는 컨테이너 런타임(CRI), 스토리지(CSI), 네트워크(CNI)를 인터페이스로 분리해 두었다. 홈랩 k3s 가 containerd 위에서 돌아가도, 상위의 kubelet 은 런타임 구현이 아니라 CRI 라는 추상에 의존한다.

## 확인 문제

1. SRP 를 "변경의 이유" 또는 "액터" 라는 말로 설명하라.
2. 타입별 `if/elif` 분기가 코드 곳곳에 퍼져 있다면 어떤 원칙을 위반한 신호인가?
3. LSP 관점에서 하위 타입이 지켜야 할 사전조건·사후조건 규칙을 쓰라.
4. 위 예제에서 `Square` 를 LSP 를 지키도록 고치는 방법 두 가지를 들라.
5. DIP 에서 "역전" 되는 것은 정확히 무엇인가?

### 풀이

1. 한 모듈은 하나의 액터(변경을 요구하는 주체)의 요구로만 바뀌어야 한다. 바뀔 이유가 둘 이상이면 나눈다.
2. 개방-폐쇄 원칙(OCP). 새 종류를 추가할 때마다 기존 분기를 수정해야 한다.
3. 사전조건을 강화하지 않고, 사후조건을 약화하지 않으며, 상위 타입의 불변식을 유지한다.
4. (1) `Square` 를 `Rectangle` 의 하위 클래스로 두지 않고 별도 타입 또는 공통 `Shape` 의 형제로 둔다. (2) 도형을 불변 객체로 만들어 크기 변경 메서드를 없앤다.
5. 소스 코드 의존 방향. 상위 정책이 하위 구현을 향하던 의존이, 하위 구현이 상위가 정의한 추상을 향하도록 뒤집힌다.

## 더 읽을거리 (References)

- Python 문서, [typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)
- Python 문서, [abc — Abstract Base Classes](https://docs.python.org/3/library/abc.html)
- Barbara H. Liskov, Jeannette M. Wing, "A Behavioral Notion of Subtyping", *ACM Transactions on Programming Languages and Systems*, 16(6), 1994 (서지 정보)
- Bertrand Meyer, *Object-Oriented Software Construction*, Prentice Hall, 1988 (서지 정보)
- Robert C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Prentice Hall, 2017 (서지 정보)
