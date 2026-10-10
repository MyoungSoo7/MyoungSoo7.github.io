---
layout: post
title: "[CS300 #188] 디자인 패턴 3 — 행위 패턴: 객체끼리 일을 나누고 말을 거는 방식"
date: 2026-10-10 21:08:00 +0900
categories: [cs]
tags: [cs300, software-engineering, design-patterns, strategy, observer]
---

컴퓨터공학 300 주제 시리즈의 188번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

행위 패턴(behavioral patterns)은 객체 사이의 **책임 분배와 통신 방식**을 다룬다. GoF 의 열한 가지 중 전략, 옵저버, 커맨드, 상태, 템플릿 메서드, 이터레이터, 책임 연쇄는 지금도 거의 모든 프레임워크 안에서 매일 쓰인다.

## 왜 필요한가

생성 패턴이 "누가 만드는가", 구조 패턴이 "어떻게 엮는가" 를 다뤘다면, 행위 패턴은 "**런타임에 누가 무엇을 결정하고 누구에게 알리는가**" 를 다룬다.

결제가 끝나면 메일을 보내고, 포인트를 쌓고, 재고를 줄이고, 정산 데이터를 남긴다. 이걸 결제 함수 하나에 다 적으면 결제 코드가 메일 서버와 포인트 정책과 정산 형식을 모두 알게 된다. 기능 하나를 추가할 때마다 결제 코드를 고쳐야 한다. 행위 패턴은 이런 "알아야 할 것" 을 줄이는 도구다.

## 핵심 개념

### 열한 가지 한눈에 보기

| 패턴 | 한 줄 설명 | 익숙한 예 |
|---|---|---|
| 전략(Strategy) | 알고리즘을 객체로 캡슐화해 갈아 끼운다 | `sorted(key=...)`, 할인 정책 |
| 옵저버(Observer) | 상태 변화를 구독자들에게 알린다 | 이벤트 리스너, 발행/구독 |
| 커맨드(Command) | 요청을 객체로 만든다(기록·취소·대기열) | 실행 취소, 작업 큐 |
| 상태(State) | 상태에 따라 행동이 바뀌는 것을 상태 객체에 위임 | 주문 상태, TCP 연결 상태 |
| 템플릿 메서드(Template Method) | 알고리즘 뼈대는 상위가, 세부 단계는 하위가 | 테스트 프레임워크의 `setUp`/`tearDown` |
| 이터레이터(Iterator) | 내부 구조를 드러내지 않고 차례로 순회 | 파이썬 `for` 문, 제너레이터 |
| 책임 연쇄(Chain of Responsibility) | 요청을 처리할 수 있는 객체가 나올 때까지 사슬을 따라 넘긴다 | 미들웨어, 예외 처리 |
| 중재자(Mediator) | 객체들이 서로 직접 말하지 않고 중재자를 거친다 | 채팅방, 폼 위젯 조율 |
| 메멘토(Memento) | 캡슐화를 깨지 않고 상태를 저장·복원한다 | 스냅숏, 되돌리기 |
| 방문자(Visitor) | 구조를 바꾸지 않고 새 연산을 추가한다 | 컴파일러의 AST 처리 |
| 인터프리터(Interpreter) | 간단한 언어의 문법을 클래스로 표현해 해석한다 | 규칙 엔진, 작은 DSL |

### 전략: 함수가 일급인 언어에서는 함수 하나

전략 패턴은 "하는 일은 같고 방법만 다른 알고리즘" 을 인터페이스 뒤에 숨기고 런타임에 고른다. 자바처럼 함수를 값으로 넘기기 어려웠던 시절에는 `DiscountStrategy` 인터페이스와 구현 클래스가 필요했다. 파이썬에서는 함수가 일급 객체라 **함수를 넘기는 것 자체가 전략 패턴**이다. 내장 [`sorted`](https://docs.python.org/3/library/functions.html#sorted)의 `key` 인자가 그 예다.

### 옵저버: 발행자는 구독자를 모른다

```
           publish("order_paid")
 결제 ─────────────> EventBus ──> 메일 발송
                             ├──> 포인트 적립
                             └──> 재고 차감
```

결제 코드는 "결제됐다" 는 사실만 알린다. 누가 듣는지 모른다. 새 기능(정산 기록)을 추가할 때 결제 코드는 그대로 두고 구독자만 하나 더 붙인다.
대가도 있다. 흐름이 코드에 직접 드러나지 않아, "결제 후 무슨 일이 일어나는가" 를 알려면 구독 등록 지점을 전부 찾아야 한다. 구독자 하나의 예외가 나머지 구독자 실행을 막을 수 있다는 점도 설계 때 정해야 한다.

### 커맨드: 요청을 값으로

"텍스트를 추가하라" 는 요청을 메서드 호출이 아니라 **객체**로 만들면, 그 객체를 리스트에 쌓아 두었다가 되돌리거나(undo), 큐에 넣었다가 나중에 실행하거나, 로그로 남겼다가 재실행할 수 있다. 작업 큐 시스템의 "작업(job)" 메시지가 커맨드 객체다.

### 상태: 조건문 대신 상태 객체

주문 처리 코드 곳곳에 `if status == "PAID" and action == "cancel": ...` 이 흩어져 있으면, 새 상태를 하나 추가할 때 모든 분기를 찾아 고쳐야 한다. GoF 상태 패턴은 상태마다 클래스를 두고, 각 상태 클래스가 "이 상태에서 이 행동을 하면 무슨 일이 일어나는가" 를 안다.
상태와 전이가 단순하면 아래 예제처럼 **전이 표**를 데이터로 두는 상태 머신으로도 충분하다. 핵심은 허용되지 않은 전이를 한 곳에서 막는 것이다.

### 템플릿 메서드와 이터레이터

- **템플릿 메서드**: 상위 클래스가 `run()` 안에서 `setUp() → test() → tearDown()` 순서를 고정하고, 하위 클래스는 각 단계만 채운다. 파이썬 [`unittest.TestCase`](https://docs.python.org/3/library/unittest.html)가 정확히 이 구조다.
- **이터레이터**: 파이썬은 언어 차원에서 이 패턴을 내장했다. `__iter__()` 와 `__next__()` 를 구현하면 `for` 문이 동작하고, 더 꺼낼 것이 없으면 `StopIteration` 을 던진다([용어집: iterator](https://docs.python.org/3/glossary.html#term-iterator)).

## 직접 해 보기

전략, 옵저버, 커맨드, 표 기반 상태 머신을 한 파일에서 돌려 본다.

```python
from collections import defaultdict

# 1) 전략: 알고리즘을 갈아 끼운다. 파이썬에서는 함수 하나로 충분하다
def no_discount(total):      return total
def member_discount(total):  return int(total * 0.9)
def coupon_3000(total):      return max(total - 3000, 0)

def checkout(total, pricing=no_discount):
    return pricing(total)

for s in (no_discount, member_discount, coupon_3000):
    print(f"전략 {s.__name__:16s} -> {checkout(20000, s)}")

# 2) 옵저버: 발행자는 구독자가 누군지 모른다
class EventBus:
    def __init__(self): self._subs = defaultdict(list)
    def subscribe(self, topic, fn): self._subs[topic].append(fn)
    def publish(self, topic, **data):
        for fn in self._subs[topic]:
            fn(**data)

bus = EventBus()
bus.subscribe("order_paid", lambda order_id, **_: print(f"  메일 발송: 주문 {order_id}"))
bus.subscribe("order_paid", lambda order_id, amount: print(f"  포인트 적립: {amount // 100}점"))
bus.publish("order_paid", order_id=42, amount=20000)

# 3) 커맨드: 요청을 객체로 만들어 기록·취소할 수 있게 한다
class AddText:
    def __init__(self, doc, text): self.doc, self.text = doc, text
    def execute(self): self.doc.append(self.text)
    def undo(self):    self.doc.pop()

doc, history = [], []
for t in ("Hello", ", ", "World"):
    cmd = AddText(doc, t); cmd.execute(); history.append(cmd)
print("커맨드 실행 후:", "".join(doc))
history.pop().undo()
print("되돌리기 1회 :", "".join(doc))

# 4) 상태 머신(표 기반): 허용된 전이만 통과시킨다
class Order:
    def __init__(self): self.name = "CREATED"
    def go(self, nxt):
        if nxt not in TRANSITIONS[self.name]:
            raise ValueError(f"{self.name} -> {nxt} 전이는 허용되지 않는다")
        self.name = nxt

TRANSITIONS = {
    "CREATED":   {"PAID", "CANCELLED"},
    "PAID":      {"SHIPPED", "CANCELLED"},
    "SHIPPED":   {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}
o = Order()
for step in ("PAID", "SHIPPED", "CANCELLED"):
    try:
        o.go(step); print("상태:", o.name)
    except ValueError as e:
        print("상태 오류:", e)
```

실행 결과:

```
전략 no_discount      -> 20000
전략 member_discount  -> 18000
전략 coupon_3000      -> 17000
  메일 발송: 주문 42
  포인트 적립: 200점
커맨드 실행 후: Hello, World
되돌리기 1회 : Hello, 
상태: PAID
상태: SHIPPED
상태 오류: SHIPPED -> CANCELLED 전이는 허용되지 않는다
```

`checkout` 은 할인 방식이 몇 개든 바뀌지 않는다. `publish` 를 호출한 쪽은 메일과 포인트를 모른다. 배송이 시작된 주문을 취소하려는 시도는 상태 머신이 한 곳에서 거부한다. 같은 거부 로직이 화면, API, 배치 작업마다 따로 있다면 셋 중 하나는 언젠가 빠뜨린다.

## 현업에서는

- **옵저버는 메시지 브로커로 커진다.** 한 프로세스 안의 이벤트 버스가 서비스 경계를 넘으면 Kafka·RabbitMQ 같은 브로커를 둔 발행/구독이 된다. 쿠버네티스 컨트롤러가 API 서버의 리소스 변화를 "watch" 해서 반응하는 구조도 옵저버다.
- **상태 머신은 쿠버네티스 곳곳에 있다.** 파드의 `Pending → Running → Succeeded/Failed` 단계(phase)가 대표적이다. 홈랩에서 파드가 `Pending` 에 머물러 있으면 "다음 전이를 막는 조건(스케줄링, 이미지 풀)" 이 무엇인지 찾는 것이 진단의 시작이다.
- **책임 연쇄는 미들웨어 체인이다.** 인증 미들웨어가 토큰이 없으면 거기서 401 로 끝내고, 있으면 다음으로 넘긴다.
- **패턴 이름은 코드에 드러내도 좋다.** `PricingStrategy`, `OrderStateMachine` 처럼 패턴 이름이 들어간 이름은 읽는 사람에게 구조를 바로 알려 준다. 다만 패턴을 쓰기 위해 패턴을 쓰지는 말자. `if` 두 개로 충분한 곳에 상태 클래스 다섯 개는 과하다.

## 확인 문제

1. 파이썬에서 전략 패턴을 별도 클래스 없이 구현할 수 있는 이유는?
2. 옵저버 패턴의 장점 하나와 단점 하나를 들라.
3. 커맨드 패턴으로 "실행 취소" 를 구현할 수 있는 이유는?
4. 파이썬의 `for` 문이 동작하려면 객체가 어떤 메서드를 제공해야 하는가?
5. `unittest.TestCase` 는 어떤 행위 패턴의 예인가? 그 이유는?

### 풀이

1. 함수가 일급 객체라서, 알고리즘 하나를 함수로 만들어 인자로 넘기면 그대로 전략이 된다.
2. 장점: 발행자가 구독자를 몰라 기능 추가 시 발행 코드를 고치지 않는다. 단점: 실행 흐름이 코드에 직접 드러나지 않아 추적이 어렵고, 구독자 실패 처리 방식을 따로 정해야 한다.
3. 요청이 객체로 남아 있고, 각 객체가 자기 `execute` 의 반대 동작인 `undo` 를 알고 있기 때문이다. 실행 기록을 스택으로 쌓아 두고 역순으로 `undo` 한다.
4. `__iter__()` 가 이터레이터를 돌려주고, 이터레이터는 `__next__()` 로 다음 값을 주다가 끝나면 `StopIteration` 을 던져야 한다.
5. 템플릿 메서드. 실행 순서(`setUp` → 테스트 메서드 → `tearDown`)는 프레임워크가 고정하고, 각 단계의 내용만 하위 클래스가 채운다.

## 더 읽을거리 (References)

- Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, 1994 (서지 정보)
- Python 문서, [Glossary — iterator](https://docs.python.org/3/glossary.html#term-iterator)
- Python 문서, [Built-in Functions — sorted](https://docs.python.org/3/library/functions.html#sorted)
- Python 문서, [unittest — Unit testing framework](https://docs.python.org/3/library/unittest.html)
