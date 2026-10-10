---
layout: post
title: "[CS300 #198] 도메인 주도 설계 — 업무의 언어로 모델을 만들고 경계를 긋기"
date: 2026-10-10 21:18:00 +0900
categories: [cs]
tags: [cs300, software-engineering, ddd, bounded-context, aggregate]
---

컴퓨터공학 300 주제 시리즈의 198번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

도메인 주도 설계(DDD, Domain-Driven Design)는 소프트웨어의 중심에 **업무 영역(도메인)의 모델**을 두고, 개발자와 도메인 전문가가 같은 언어로 그 모델을 함께 다듬어 가는 설계 접근이다. 큰 그림에서는 모델이 통하는 **경계(바운디드 컨텍스트)**를 긋고, 코드 수준에서는 엔티티·값 객체·애그리거트로 규칙을 지킨다.

## 왜 필요한가

복잡한 업무 소프트웨어에서 어려운 부분은 대개 기술이 아니라 **업무 규칙**이다. 보험 약관, 정산 규칙, 물류 예외 처리 같은 것들이다. 이런 규칙이 컨트롤러, SQL, 배치 스크립트에 흩어져 있으면 아무도 전체를 모르고, 규칙 하나가 바뀔 때마다 어디를 고쳐야 할지 찾는 데 시간이 든다.

또 하나의 문제는 말이다. 영업팀의 "고객" 은 계약한 회사이고, 고객지원팀의 "고객" 은 전화를 건 개인이고, 결제 시스템의 "고객" 은 카드 소유자다. 이 셋을 `Customer` 클래스 하나로 만들면 필드가 50개인 괴물이 되고, 한 팀의 요구로 고친 필드가 다른 팀 기능을 깨뜨린다.

DDD 는 이 두 문제, 즉 **규칙이 흩어지는 문제와 같은 말이 다른 뜻을 갖는 문제**를 정면으로 다룬다. Eric Evans 가 2003년 같은 이름의 책에서 체계화했고, Martin Fowler 는 [Domain Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)에서 이를 도메인 모델을 중심으로 소프트웨어를 개발하는 접근이라고 요약한다.

## 핵심 개념

DDD 는 크게 두 층으로 나뉜다. 시스템을 어떻게 나눌지 정하는 **전략적 설계**와, 나눈 안쪽을 어떻게 짤지 정하는 **전술적 설계**다.

### 전략적 설계 1: 보편 언어(Ubiquitous Language)

개발자와 도메인 전문가가 **같은 단어를 같은 뜻으로** 쓰는 공용어를 만들고, 그 단어를 회의, 문서, 코드의 클래스·메서드 이름에 그대로 쓴다.

```
도메인 전문가: "주문이 확정되면 재고를 할당하고, 할당에 실패하면 주문을 보류한다."

나쁜 코드:  process(o) → update_tbl(o.id, 2) → if err: set_flag(o, 7)
좋은 코드:  order.place() → inventory.allocate(order) → order.hold(reason)
```

코드를 도메인 전문가가 읽고 "맞다, 틀리다" 를 말할 수 있으면 보편 언어가 살아 있는 것이다. 용어가 바뀌면 코드 이름도 바꾼다.

### 전략적 설계 2: 바운디드 컨텍스트(Bounded Context)

하나의 모델이 일관되게 통하는 **경계**다. Fowler 는 [BoundedContext](https://martinfowler.com/bliki/BoundedContext.html)에서 DDD 가 큰 모델을 여러 바운디드 컨텍스트로 나누고 그 사이의 관계를 명시적으로 다룬다고 설명한다.

```
┌──── 영업 컨텍스트 ────┐   ┌──── 배송 컨텍스트 ────┐   ┌──── 결제 컨텍스트 ────┐
│ Customer             │   │ Recipient            │   │ Payer                │
│  - 계약 등급          │   │  - 배송지            │   │  - 결제 수단          │
│  - 담당 영업          │   │  - 연락처            │   │  - 청구지            │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
        같은 "사람" 이지만 컨텍스트마다 다른 모델. 연결은 ID 로만.
```

같은 현실의 대상이라도 컨텍스트마다 필요한 속성과 규칙이 다르므로 **따로 모델링**한다. 컨텍스트 사이의 관계(누가 상류이고 누가 하류인지, 번역 계층을 둘지)를 그린 것을 컨텍스트 맵이라고 한다. 앞의 구조 패턴 글에서 본 안티부패 계층(어댑터)이 컨텍스트 경계의 번역기로 쓰인다.

### 전술적 설계: 모델의 구성 요소

| 구성 요소 | 정의 | 예 |
|---|---|---|
| 엔티티(Entity) | 식별자로 구별된다. 속성이 바뀌어도 같은 것 | 주문(주문번호), 회원(회원 ID) |
| 값 객체(Value Object) | 식별자가 없고 값이 같으면 같다. 불변으로 만든다 | 금액, 주소, 기간 |
| 애그리거트(Aggregate) | 함께 일관성을 지켜야 하는 객체 묶음. 루트를 통해서만 접근 | 주문 + 주문 항목 |
| 도메인 이벤트 | 도메인에서 일어난 의미 있는 사건 | 주문이 확정됨 |
| 리포지터리 | 애그리거트를 저장·조회하는 컬렉션 같은 인터페이스 | `OrderRepository` |
| 도메인 서비스 | 특정 엔티티에 자연스럽게 속하지 않는 도메인 로직 | 환율 적용 송금 계산 |

### 애그리거트: 불변식의 경계

Fowler 의 [DDD_Aggregate](https://martinfowler.com/bliki/DDD_Aggregate.html) 설명대로, 애그리거트는 하나의 단위로 다룰 수 있는 도메인 객체 묶음이고, **바깥에서의 참조는 애그리거트 루트로만** 향해야 한다. 그래야 루트가 묶음 전체의 일관성을 지킬 수 있다.

실무에서 자주 쓰는 규칙은 다음과 같다(Vaughn Vernon 이 *Implementing Domain-Driven Design* 에서 정리한 원칙에 기반).

- 애그리거트는 **작게** 만든다. 진짜 함께 지켜야 하는 불변식만 묶는다.
- 다른 애그리거트는 객체가 아니라 **ID 로** 참조한다.
- 한 트랜잭션에서는 **애그리거트 하나만** 수정한다. 여러 애그리거트에 걸친 일은 도메인 이벤트로 이어 붙여 결과적 일관성으로 처리한다.

## 직접 해 보기

값 객체 `Money`, 애그리거트 루트 `Order`, 도메인 이벤트 `OrderPlaced` 를 만들어 불변식이 지켜지는지 확인한다. 금액에는 부동소수점 오차가 없는 [`decimal.Decimal`](https://docs.python.org/3/library/decimal.html)을 쓴다.

```python
from dataclasses import dataclass, field
from decimal import Decimal

# ----- 값 객체: 식별자가 없고, 값이 같으면 같은 것. 불변 -----
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "KRW"
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("금액은 음수일 수 없다")
    def __add__(self, other):
        if self.currency != other.currency:
            raise ValueError("통화가 다르면 더할 수 없다")
        return Money(self.amount + other.amount, self.currency)
    def times(self, n):
        return Money(self.amount * n, self.currency)

# ----- 도메인 이벤트 -----
@dataclass(frozen=True)
class OrderPlaced:
    order_id: str
    total: Money

# ----- 애그리거트 루트: 불변식을 지키는 유일한 입구 -----
@dataclass
class OrderLine:
    sku: str
    unit_price: Money
    qty: int

class Order:
    MAX_LINES = 3

    def __init__(self, order_id):
        self.id = order_id                 # 엔티티: 식별자로 구별
        self._lines: list[OrderLine] = []
        self.status = "DRAFT"
        self.events: list = []

    def add_line(self, sku, unit_price, qty):
        if self.status != "DRAFT":
            raise ValueError("주문 확정 후에는 항목을 바꿀 수 없다")
        if len(self._lines) >= self.MAX_LINES:
            raise ValueError(f"주문 항목은 최대 {self.MAX_LINES}개")
        self._lines.append(OrderLine(sku, unit_price, qty))

    def total(self):
        t = Money(Decimal(0))
        for l in self._lines:
            t = t + l.unit_price.times(l.qty)
        return t

    def place(self):
        if not self._lines:
            raise ValueError("빈 주문은 확정할 수 없다")
        self.status = "PLACED"
        self.events.append(OrderPlaced(self.id, self.total()))

# ----- 사용 -----
print("값 객체 동등성:", Money(Decimal(1000)) == Money(Decimal(1000)))
o = Order("ORD-1")
o.add_line("BOOK", Money(Decimal(15000)), 2)
o.add_line("PEN",  Money(Decimal(1200)), 3)
o.place()
print("합계:", o.total().amount, o.total().currency, "| 상태:", o.status)
print("발행된 이벤트:", o.events)

for attempt in (lambda: o.add_line("CUP", Money(Decimal(5000)), 1),
                lambda: Money(Decimal(-1)),
                lambda: Money(Decimal(1)) + Money(Decimal(1), "USD")):
    try:
        attempt()
    except ValueError as e:
        print("거부:", e)
```

실행 결과:

```
값 객체 동등성: True
합계: 33600 KRW | 상태: PLACED
발행된 이벤트: [OrderPlaced(order_id='ORD-1', total=Money(amount=Decimal('33600'), currency='KRW'))]
거부: 주문 확정 후에는 항목을 바꿀 수 없다
거부: 금액은 음수일 수 없다
거부: 통화가 다르면 더할 수 없다
```

규칙이 **모델 안에** 있다는 점이 핵심이다. "확정된 주문은 바꿀 수 없다" 는 규칙이 컨트롤러나 SQL 이 아니라 `Order.add_line` 안에 있으므로, 웹 API 든 관리자 화면이든 배치 작업이든 이 규칙을 우회할 길이 없다. 음수 금액이나 통화 혼합은 `Money` 를 만드는 순간 거부되므로, 시스템 어디에도 "잘못된 금액" 이 존재할 수 없다.

`OrderPlaced` 이벤트는 재고 할당, 알림 발송 같은 **다른 애그리거트나 컨텍스트**의 일을 시작하는 신호가 된다. 주문 애그리거트는 재고를 직접 건드리지 않는다. 한 트랜잭션에 애그리거트 하나라는 규칙을 이렇게 지킨다.

## 현업에서는

- **이벤트 스토밍으로 시작한다.** 도메인 전문가와 개발자가 벽에 "주문이 확정됨", "결제가 실패함" 같은 도메인 이벤트를 포스트잇으로 시간순으로 붙여 가며 업무 흐름을 그리는 워크숍이 DDD 의 흔한 출발점이다. 용어 충돌과 컨텍스트 경계가 이 과정에서 드러난다.
- **모든 곳에 DDD 를 하지 않는다.** Evans 는 사업의 차별점이 되는 **핵심 도메인**에 모델링 노력을 집중하라고 한다. 게시판, 회원 가입 같은 일반 기능은 단순한 CRUD 로 충분하다. 애그리거트와 이벤트를 곳곳에 두르면 오히려 복잡해진다.
- **바운디드 컨텍스트는 마이크로서비스 경계의 후보가 된다.** 다음 글에서 다룰 마이크로서비스를 나눌 때, 기술 계층(프론트·백·DB)이 아니라 바운디드 컨텍스트를 기준으로 나누는 것이 일반적인 권고다.
- **운영에서도 언어가 중요하다.** 홈랩 클러스터의 대시보드와 알림 이름을 "파드 재시작 증가" 처럼 운영자가 실제로 쓰는 말로 지으면, 알림을 받은 사람이 바로 상황을 이해한다. 작은 보편 언어다.

## 확인 문제

1. 보편 언어가 코드에 반영되어 있는지 확인하는 간단한 방법은?
2. 바운디드 컨텍스트가 필요한 이유를 "고객" 예시로 설명하라.
3. 엔티티와 값 객체의 차이는?
4. 애그리거트 바깥에서 내부 객체(주문 항목)를 직접 수정하지 못하게 하는 이유는?
5. 주문 확정 후 재고를 줄여야 한다. 주문 애그리거트가 재고 애그리거트를 직접 수정하지 않고 처리하는 방법은?

### 풀이

1. 도메인 전문가가 클래스·메서드 이름을 읽고 업무 규칙과 맞는지 판단할 수 있는지 본다. 회의에서 쓰는 용어와 코드의 이름이 같은지 확인한다.
2. 영업·고객지원·결제에서 "고객" 이 가리키는 대상과 필요한 속성·규칙이 다르다. 하나의 모델로 합치면 비대해지고 서로의 변경이 충돌하므로, 컨텍스트마다 별도 모델을 두고 경계에서 번역한다.
3. 엔티티는 식별자로 구별되어 속성이 바뀌어도 같은 대상이고, 값 객체는 식별자 없이 값으로만 비교되며 불변으로 다룬다.
4. 애그리거트 루트가 묶음 전체의 불변식(최대 항목 수, 확정 후 변경 금지 등)을 지키는 유일한 입구여야 하기 때문이다. 내부를 직접 고치면 루트의 검사를 우회한다.
5. 주문 애그리거트가 `OrderPlaced` 도메인 이벤트를 발행하고, 재고 쪽이 이를 받아 별도 트랜잭션에서 재고 애그리거트를 수정한다(결과적 일관성).

## 더 읽을거리 (References)

- Martin Fowler, [Domain Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- Martin Fowler, [BoundedContext](https://martinfowler.com/bliki/BoundedContext.html)
- Martin Fowler, [DDD_Aggregate](https://martinfowler.com/bliki/DDD_Aggregate.html)
- Eric Evans, [DDD Reference](https://www.domainlanguage.com/ddd/reference/), Domain Language
- Eric Evans, *Domain-Driven Design: Tackling Complexity in the Heart of Software*, Addison-Wesley, 2003 (서지 정보)
