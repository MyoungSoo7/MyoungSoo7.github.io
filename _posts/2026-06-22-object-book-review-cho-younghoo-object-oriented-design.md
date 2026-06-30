---
layout: post
title: "*서평* — *조영호* 의 *오브젝트* : *코드로 이해 하는 *객체지향 설계*"
date: 2026-06-22 18:30:00 +0900
categories: [book-review, object-oriented, software-engineering, design]
tags: [object-oriented, ood, design, cho-youngho, ddd, responsibility, role, collaboration, spring, refactoring, book-review]
---

> *"객체 가 *데이터 가 아니라 *역할 이라는 것* 을 *진심으로 *받아들이기 까지 *7년 이 걸렸다"* — 이게 *오브젝트* 를 *처음 읽은 *2020 년 의 *내 *마음 의 균열* 이었다.
>
> *조영호 (Cho Young-ho)* 의 *오브젝트: 코드로 이해 하는 객체지향 설계* (위키북스, 2019) 는 *한국 어로 쓰여진 *객체지향 설계 의 *가장 깊은 책* 중 하나 다. *교보문고 2019 올해 의 책*, *Java 진영 의 *진짜 명저*. 656 쪽 의 *밀도 가 높은 코드 + 일관 된 *영화 예매 시스템 예제* 가 *부실 한 코드 를 *점진 적으로 개선* 하는 *리팩토링 의 여정* 으로 *독자 를 끌고 간다*.
>
> 이 글은 *내가 *직접 *2 회 정독* 한 경험 + *국내 의 *여러 리뷰* — *Velog, Jinwoo's Blog, 위키북스 공식*, *Trevari 모임* 등 — 의 *공통 인상* 과 *상이 한 시각* 을 *교차 정리* 한 *서평* 이다.

내 *기본기 시리즈* 의 *객체지향 편* :
- [*DB 의 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html) — *기본기 시리즈 첫 편*
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
- [*AI 코드 PR 머지 7 질문*](/2026/06/21/ai-code-pr-merge-7-questions-checklist.html) — *시니어 의 시야*

---

## TL;DR — *한 줄 결론*

> *오브젝트* 는 *객체지향 의 *이론 가 아니라 *코드 의 *실전 변화* 를 *656 쪽 동안 *집요 하게 *추적* 하는 책. *전작 *객체지향 의 사실 과 오해* 가 *철학* 이었다면 이 책 은 *공장*. *역할 / 책임 / 협력* 의 *3 단어* 를 *영화 예매 시스템* 이라는 *한 도메인* 위에서 *데이터 중심 → 책임 중심 → 협력 중심* 으로 *3 차례 리팩토링* 하며 *왜* 가 아니라 *어떻게* 를 *체화* 시킨다. *강점* : *코드 의 정확함 + 한국어 의 정밀함 + 단계 적 개선 의 일관성*. *약점* : *객체지향 의 *기본 어휘* (캡슐화 / 상속 / 다형성) 를 *모르면 *진입 어려움* + *656 쪽 의 양 적 부담* + *영화 예매 도메인* 의 *반복 으로 *후반 피로감*. *대상* : *Spring Boot / JPA 로 *3년 이상 *비즈니스 코드 짠 적 있는 개발자*. *anemic domain model* 의 *답답함을 *느낀 적 있는 사람*.

---

## 1. *책 의 *정체 — *2019 년 의 위치***

### 1.1 *기본 정보*

| | |
|---|---|
| **저자** | 조영호 (Cho Young-ho) |
| **출판사** | 위키북스 (IT Leaders 시리즈 29) |
| **출간** | 2019 년 6 월 17 일 |
| **분량** | 656 쪽 |
| **정가** | 38,000 원 |
| **수상** | 교보문고 2019 *올해의 책* |
| **전작** | *객체지향 의 사실 과 오해* (위키북스, 2015) |

### 1.2 *저자 의 *위치*

조영호 는 *국내 의 *드문 객체지향 설계 전문가*. *우아한형제들* 등 의 *실무 코드 베이스* 에서 *Java 진영 의 *객체지향 적 코드* 를 *집요 하게 *추적* 해 온 *경험* 이 *책 의 *모든 예제 의 *밑* 에 *깔려 있다*.

> 전작 *객체지향 의 사실 과 오해* (2015) 는 *비교 적 얇은 (250 쪽)* *철학적 / 비유 적* 책. *오브젝트* 는 *그 철학 을 *실 코드 로 *증명* 하는 *656 쪽 의 *공장*.

### 1.3 *책 의 *시점 적 의의*

- *Java 진영 의 *Effective Java (3rd, 2017)* 와 *Clean Code (2008)* 는 *서양 표준*. *오브젝트* 는 *그 둘 의 *간극 — *객체지향 설계 의 *통합 적 시야* 를 *한국어 로 *처음 *체계화* 한 책.
- *DDD (Eric Evans, 2003)* 가 *전략 적 설계* 의 *철학* 이라면, *오브젝트* 는 *전술 적 패턴* 의 *코드 적 깊이*.
- *2026 년 의 *Spring Boot / JPA / Kotlin* 시대 에도 *여전히 유효* 한 *고전*. *AI 코딩 시대 의 *시니어 의 *남은 영역* 인 *도메인 설계* 의 *핵심 reference*.

---

## 2. *책 의 *구조 — *4 부 13 장***

### 2.1 *Part 1 — *객체지향 의 *기초***

| 장 | 주제 |
|---|---|
| 1. 객체, 설계 | *왜 우리는 객체지향 으로 가는가* — 절차 적 vs 객체지향 의 *영화 예매 시스템* 첫 비교 |
| 2. 객체지향 프로그래밍 | *역할 / 책임 / 협력* 의 *3 단어 의 *공식 도입* |

**핵심 메시지** :
> "*데이터 가 아니라 *역할* 에 집중 하라*". *클래스 가 가지는 *상태 / 데이터* 가 아니라 *그 클래스 가 *수행 하는 *책임 (메서드 의 의도)* 가 *설계 의 출발점*.

### 2.2 *Part 2 — *책임 의 *원리***

| 장 | 주제 |
|---|---|
| 3. 역할, 책임, 협력 | *책임 주도 설계 (Responsibility-Driven Design)* — Rebecca Wirfs-Brock 의 RDD |
| 4. 설계 품질 과 트레이드 오프 | *응집도 / 결합도* 의 *정량 적 측정* 방법 |
| 5. 책임 할당 하기 | *INFORMATION EXPERT*, *CREATOR*, *LOW COUPLING*, *HIGH COHESION* — *GRASP 패턴* 의 한국 어 적용 |
| 6. 메시지와 인터페이스 | *what 과 *how 의 *분리* — 인터페이스 의 *철학* |

**핵심 메시지** :
> "*객체 가 *무엇을 *알고 있느냐* 가 아니라 *무엇을 *할 수 있느냐* 가 *그 객체 의 정체성*".

### 2.3 *Part 3 — *추상화와 *다형성***

| 장 | 주제 |
|---|---|
| 7. 객체 분해 | *추상화* 의 *3 가지 방법* — *분류 / 일반화 / 합성* |
| 8. 의존성 관리 하기 | *컴파일 타임 vs 런타임 의존성*, *DIP, DI* |
| 9. 유연한 설계 | *추상 의존 의 *대가 와 *이득* |
| 10. 상속과 코드 재사용 | *상속 의 *함정 7 가지* + *합성 우선 의 원칙* |
| 11. 합성과 유연한 설계 | *Strategy / Template Method* 의 *재 분석* |
| 12. 다형성 | *추상 메서드 / 인터페이스 / 다형성 의 *기계 적 동작* |

**핵심 메시지** :
> "*상속 은 *위험 한 도구*. *재사용 의 *유혹* 에 *합성 의 *유연성* 을 *희생* 하지 말 것".

### 2.4 *Part 4 — *깊이 보기***

| 장 | 주제 |
|---|---|
| 13. 서브클래싱과 서브타이핑 | *Liskov 치환 원칙 (LSP)* 의 *코드 적 의미* |
| 14. 일관성 있는 협력 | *변화 의 *공통 패턴 식별* — *역할 의 *재 사용* |
| 15. 디자인 패턴과 프레임워크 | *GoF 패턴 의 *객체지향 적 재 해석* — *Strategy / Observer / Command / Composite 의 *진짜 의도* |

→ **656 쪽 의 *마지막 *3 부* 가 *깊이 의 *클라이맥스*. 패턴 책 (GoF) 의 *한국 어 적 *최선 의 *입문*.

---

## 3. *책 의 *핵심 메시지 — *5 가지***

### 3.1 *(1) 객체 는 *데이터 가 아니라 *역할***

> *"객체 의 *내부 상태* 가 *외부 에서 *보이지 않게* 하라 — 그것 이 *캡슐화 의 *진짜 의미*".

```java
// 안티 (anemic domain model)
class Order {
    private List<OrderItem> items;
    public List<OrderItem> getItems() { return items; }
}

class OrderService {
    public BigDecimal calculateTotal(Order o) {
        return o.getItems().stream()
            .map(i -> i.getPrice().multiply(BigDecimal.valueOf(i.getQuantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
```

이 코드 의 *문제* :
- *Order 는 *데이터 보관 자* — *역할 (책임) 없음*.
- *OrderService 가 *Order 의 *내부 (items) 를 *알아야 함*. *캡슐화 깨짐*.

```java
// 책임 주도 설계 후
class Order {
    private List<OrderItem> items;
    public BigDecimal calculateTotal() {       // ← 책임 이 *내부* 로
        return items.stream()
            .map(OrderItem::subtotal)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}

class OrderItem {
    public BigDecimal subtotal() {              // ← *자기 책임*
        return price.multiply(BigDecimal.valueOf(quantity));
    }
}
```

→ *Order, OrderItem 둘 다 *역할 을 가짐*. *내부 데이터 노출 없음*. *변경 의 영향 범위 가 *작음*.

### 3.2 *(2) Tell, Don't Ask*

> *"객체 에 *질문 (getter) 하지 말고 *명령 (메서드) 하라*".

```java
// 안티 — Ask
if (account.getBalance().compareTo(amount) >= 0) {
    account.setBalance(account.getBalance().subtract(amount));
}

// Tell
account.withdraw(amount);   // ← 책임 이 *Account 안*
```

→ *조건 검증 / 상태 변경 의 *짝* 이 *외부* 에 *흩어 지면* *동일한 조건 을 *여러 곳 에서 *반복* — *불일치 의 진원지*. *내부 메서드* 가 *원자 적 보장*.

### 3.3 *(3) 응집도 와 결합도 의 *정량 적 측정***

> *응집도 = *변화 의 *이유* 가 *얼마나 *같은가*". *결합도 = *내가 *얼마나 *남을 *알아야 *동작* 하는가*".

| 응집도 (높을수록 좋음) | 결합도 (낮을수록 좋음) |
|---|---|
| *함께 변하는 코드 가 *같은 클래스 에* | *나의 변경 이 *남을 *얼마나 자주 *건드리는가* |

조영호 의 *결합도 측정* :
- *내가 *남 의 *어떤 것* 을 *알고 있는가* — *클래스 자체 / 메서드 / 시그너처 / 내부 구현* 순으로 *결합도 강해짐*
- *내가 *남 의 *내부 구현* 을 *안다 → *그 내부 변경 시 *나도 깨짐*

### 3.4 *(4) 상속 보다 합성*

> *"상속 은 *컴파일 타임 의 *강한 결합*. *합성 은 *런타임 의 *느슨한 결합*".

상속 의 *7 가지 함정* (책 10 장):
1. *부모 의 *내부 변경* 이 *자식 을 깨뜨림*
2. *오버라이드 의 *순서 가 *불확실* — fragile base class
3. *다중 상속 의 *복잡성* (Java 는 다중 상속 금지 가 *이유*)
4. *Liskov 위반* — 자식 이 *부모 의 약속 깨면 *런타임 에러*
5. *코드 재사용 만 위한 *상속 = *잘못된 동기*
6. *deep hierarchy 의 *추적 어려움*
7. *Composition over inheritance* — GoF 의 *최우선 원칙*

```java
// 안티 — 단순 코드 재사용 위한 상속
class Stack<T> extends ArrayList<T> {
    public void push(T x) { add(x); }
    public T pop() { return remove(size() - 1); }
}
// 문제: ArrayList 의 add(0, x), removeAll() 등 *Stack 의도 깨는 메서드* 가 *외부 에 노출*

// 합성
class Stack<T> {
    private final ArrayList<T> list = new ArrayList<>();
    public void push(T x) { list.add(x); }
    public T pop() { return list.remove(list.size() - 1); }
    // ArrayList 의 *원치 않는 메서드 는 *밖 으로 안 보임* ★
}
```

→ *Effective Java Item 18 (Favor composition over inheritance)* 의 *한국어 적 깊이*.

### 3.5 *(5) 인터페이스 vs 구현 의 *분리***

> *"클라이언트 가 *알아야 하는 것 은 *what 이지 *how 가 아니다*".

```java
// 안티 — 클라이언트 가 *구체 클래스* 에 결합
class OrderService {
    private final ArrayList<Order> orders = new ArrayList<>();  // ArrayList!
    public void add(Order o) { orders.add(o); }
}

// 좋음 — 인터페이스 에 결합
class OrderService {
    private final List<Order> orders;                            // List!
    public OrderService(List<Order> orders) { this.orders = orders; }
}
```

→ *List 의 *어떤 구현* (ArrayList / LinkedList / CopyOnWriteArrayList) 로 *교체 가능*. *Dependency Inversion* 의 *기계 적 적용*.

---

## 4. *여러 리뷰 의 *공통 인상 — *3 가지***

(*Velog, Jinwoo's Blog, 트레바리 모임 등 의 *15+ 리뷰* 의 *공통점*)

### 4.1 *모두 가 *인상 깊다 고 한 부분 — *영화 예매 시스템 예제***

- *책 전체 가 *한 도메인 의 *반복 적 리팩토링*. 데이터 중심 → 책임 중심 → 협력 중심 → 패턴 적 변형.
- *대부분 의 리뷰* : *"같은 예제 가 *4 번 다른 방식 으로 *변하는 게 *교과서 와 *완전 히 다름*"*.
- *비교* : *Clean Code (Bob Martin)* 의 *예제 가 *각 장 마다 *다른 도메인* — *학습 부담 분산 됨*. *오브젝트* 는 *반대 — *한 도메인 의 깊이*.

### 4.2 *모두 가 *어렵 다 고 한 부분 — *6-7 장 (책임 할당, 메시지)***

- *책임 의 *논리 적 추적* 이 *추상적*. *코드 만 따라 가면 *어디 서 어떤 책임* 이 *어디 로 *옮겨 갔는지* *놓치기 쉬움*.
- *Velog 의 한 리뷰* : *"6 장 부터 *책 의 *밀도 가 *2 배* 가 됨. *1~5 장 의 5 배 시간* 으로 *6~10 장* 을 *겨우 따라감"*.
- *대부분 의 권장* : *6-7 장 은 *두 번 읽기*. *코드 직접 *타이핑 하면서 따라 가기*.

### 4.3 *대부분 이 *느낀 한계 — *현장 적용 의 거리***

- *Spring Boot / JPA 위에서 *책 의 *원칙 을 *그대로 적용 어려운* 경우 가 *많다*. *Entity 가 *anemic 으로 *유지* 되는 *전통 적 패턴* 과 *충돌*.
- *책 자체 가 *Java 만 다룸*. *Kotlin / Scala / TypeScript 같은 *다른 언어 의 *번역* 은 *독자 의 일*.
- *656 쪽 의 *분량* — *처음 부터 끝* 까지 *완독 의 부담 큼*.

---

## 5. *내가 *직접 *얻은 5 가지 — *읽은 후 *3 년 *적용 경험***

### 5.1 *(1) `@Transactional` 의 *경계 가 *책임 의 경계***

```java
// 안티 — Service 에 모든 책임
@Service
class OrderService {
    @Transactional
    public Order createOrder(OrderRequest req) {
        // 1. 재고 검증
        // 2. 가격 계산
        // 3. 할인 적용
        // 4. 결제 호출
        // 5. 주문 저장
        // 6. 알림 발송
        // ... 200 줄
    }
}

// 책임 분리
@Service
class OrderService {
    @Transactional
    public Order createOrder(OrderRequest req) {
        Cart cart = cartRepo.findById(req.cartId);
        cart.validateStock();                       // ← Cart 의 책임
        Order order = cart.checkout(req.paymentInfo);  // ← Cart 가 *Order 생성*
        return orderRepo.save(order);
    }
}
```

→ *Service 가 *지휘 자* 일 뿐, *비즈니스 로직 은 *도메인 객체 에*. *settlement / sparta MSA 의 *현재 구조*.

### 5.2 *(2) Repository 의 *findById 만 으로 충분 한 경우 가 *적다***

```java
// 안티
@Service
class OrderService {
    public void cancel(Long orderId) {
        Order o = orderRepo.findById(orderId).orElseThrow();
        if (o.getStatus() != Status.PAID) throw new ...;
        if (o.getCreatedAt().isBefore(LocalDate.now().minusDays(7))) throw new ...;
        // ... 더 많은 검증
        o.setStatus(Status.CANCELLED);
        o.setCancelledAt(LocalDateTime.now());
        // ...
    }
}

// 좋음 — Order 가 *자기 cancel 책임***
public void cancel(Long orderId, CancelReason reason) {
    Order o = orderRepo.findById(orderId).orElseThrow();
    o.cancel(reason);                                   // ← 도메인 메서드
    // 검증 / 상태 변경 / 시점 기록 모두 *Order 안*
}
```

→ *Order.cancel(CancelReason)* 이 *모든 cancel 시나리오 의 *single point of truth*.

### 5.3 *(3) Value Object 의 *실 효 능***

```java
// 안티 — primitive 가 의미 잃음
class Order {
    private long amount;        // *원? 천원? 페이? — 모름*
    private String currency;
    
    public boolean isExpensive() {
        return amount > 1_000_000;   // *어떤 통화 의 100만? 의미 불확실*
    }
}

// Value Object
class Money {
    private final BigDecimal amount;
    private final Currency currency;
    
    public Money add(Money other) {
        if (!currency.equals(other.currency)) throw new ...;  // ← *타입 적 안전*
        return new Money(amount.add(other.amount), currency);
    }
    public boolean isGreaterThan(Money other) { ... }
}

class Order {
    private Money total;
    public boolean isExpensive() {
        return total.isGreaterThan(Money.krw(1_000_000));   // ← *의미 명확*
    }
}
```

→ *원자 적 단위 의 *비즈니스 의미* 를 *타입 으로 *표현*. *typo 사고 영원 차단*.

### 5.4 *(4) Anemic Domain Model 의 *진실***

> *"Spring + JPA 의 *기본 패턴* 이 *anemic 으로 가게* 만든다. *그 흐름 을 *의식 적 으로 거슬러 가야* *오브젝트 의 *철학 이 살아남는다"*.

원인:
- *@Entity 가 *기본 으로 *getter/setter 생성* (lombok @Data)
- *Service 가 *오케스트레이션 의 *유일한 layer* 로 *가르쳐 짐*
- *MyBatis / SQL Mapper 의 *영향* — *DTO ↔ Entity 가 *데이터 보관* 으로 사용

→ *오브젝트* 를 읽으면 *그 흐름 의 *부자연 스러움 이 *보임*. *역행* 하는 의지 가 *시니어 의 *작은 차이*.

### 5.5 *(5) DDD 와 의 *관계 — *작은 책 + 큰 책***

| | 오브젝트 (조영호) | DDD (Eric Evans) |
|---|---|---|
| 범위 | *코드 단위 의 *전술* | *시스템 단위 의 *전략* |
| 분량 | 656 쪽 | 580 쪽 (English) |
| 시점 | *지금 의 *내 코드* | *컨텍스트 의 *분리* |
| 추상화 | *클래스 / 메서드 의 *책임 | *Aggregate / Bounded Context* |
| 적합 | Spring Boot 진영 의 *코드 리뷰* | MSA 의 *경계 설계* |

→ **상호 보완**. *오브젝트* 의 *전술 적 깊이* + *DDD* 의 *전략 적 시야* — *둘 다 읽으면 *각각 의 부족함 이 *보완 됨*.

---

## 6. *책 의 *약점 — *5 가지***

(*공정 한 시각 의 *균형*)

### 6.1 *(1) Java 만 다룸*

- Kotlin / Scala / TypeScript / Python 의 *번역 은 *독자 의 일*.
- *Kotlin 의 *data class*, *Scala 의 *case class*, *Python 의 *dataclass* 가 *어떻게 책 의 원칙 과 *충돌 / 호환 하는지* 의 *논의 없음*.

### 6.2 *(2) 함수형 패러다임 의 *연관 부재***

- *Java 8 의 *람다* 가 *2014 년 출시 — 책 의 *2019 년 시점 엔 *5 년 후*. *그러나 *책 의 코드 가 *함수형 적 시야 없음*.
- *Map / filter / reduce* 의 *immutable 변환* 이 *책임 분리 의 *또 다른 방법* 인데, *언급 적음*.

### 6.3 *(3) 동시성 / 분산 의 *부재***

- *책 의 *모든 예제 가 *단일 스레드 + 단일 프로세스*. *@Transactional* 의 *isolation, locking* 같은 *현장 적 복잡성* 은 *책 의 범위 외*.
- MSA / Saga / Outbox 같은 *분산 패턴* — *DDD 책 의 영역*.

### 6.4 *(4) 656 쪽 의 *분량*

- *완독 의 *심리 적 부담*.
- *대부분 의 리뷰* : *"6 개월 ~ 1 년* 에 걸쳐 *읽었다"*. *주말 한 두 번* 으로는 *불가능*.

### 6.5 *(5) 영화 예매 도메인 의 *반복 피로감*

- *후반 부 (10-12 장)* 에서 *같은 도메인* 의 *변주* 가 *지루 함* 호소 리뷰 흔함.
- *대부분 의 권장* : *후반 부 는 *Skim* 또는 *코드 만 빠르게*.

---

## 7. *누구 에게 *추천 하는가***

### 7.1 *✅ 강력 추천 — *3 그룹***

1. **Spring Boot / JPA 로 *3 년 이상* 비즈니스 코드 짠 사람** — *anemic 의 *답답함* 을 *느낀 적* 있는 사람.
2. **DDD 책 (Evans) 을 *읽다가 *추상 적 으로 *느껴진 사람*** — *오브젝트* 가 *전술 적 디테일* 보충.
3. **시니어 가 *주니어 에게 *객체지향 적 사고* 를 *전파 하고 싶을 때 의 *교재***.

### 7.2 *🟡 조건 부 추천 — *3 그룹***

1. **신입 / 주니어 개발자** — *기본 개념 (캡슐화 / 상속 / 다형성) 먼저 학습 후 의 *후속 읽기*. *Effective Java* 또는 *Head First Object-Oriented* 가 *선* 행 권장.
2. **함수형 진영 (Scala / Clojure)** — *책 의 *Java 의존* 이 *진영 적 차이* 와 *충돌 가능*.
3. **MSA 운영 의 *시스템 경계 설계* 에 *집중 한 사람*** — *DDD (Evans / Vernon) 가 *더 적합*.

### 7.3 *❌ 비 추천 — *2 그룹***

1. **알고리즘 / 시스템 프로그래밍 진영** — 이 책 의 *범위 외*.
2. **빠른 답 / 한 줄 결론* 만 원하는 사람** — *656 쪽 의 *깊이* 의 *적이 다*.

---

## 8. *효율 적 인 *읽기 가이드*

### 8.1 *3 단계 읽기*

**1 단계 — *2 ~ 3 시간** : *서문 + 1, 2 장* (개요 + 핵심 메시지)
→ *책 의 *전체 방향* 만 잡기. *남은 책 의 *읽을 가치* 결정.

**2 단계 — *2 주** : *3 ~ 9 장* (책임 / 의존성 / 유연한 설계)
→ *책 의 *심장*. *코드 직접 *타이핑 하면서* 따라가기. *6 장 (메시지)* 은 *두 번 읽기 권장*.

**3 단계 — *1 주** : *10 ~ 15 장* (상속 / 합성 / 다형성 / 패턴)
→ *알려진 패턴 의 *재 해석*. *GoF 책 의 *입문* 역할.

### 8.2 *읽기 *동반 자료*

- *책 의 *GitHub 예제 코드* — [https://github.com/eternity-oop/object](https://github.com/eternity-oop/object)
- *조영호 의 *블로그* — *aeternum.egloos.com*
- *Effective Java 3 판* — *Java 적 *기술 적 보완*
- *DDD Distilled* (Vernon) — *DDD 의 *짧은 입문*

---

## 9. *2026 년 의 *관점 — *AI 시대 의 *오브젝트***

### 9.1 *AI 가 *대체 못 하는 영역*

내 글 [*AI 코드 PR 머지 7 질문*](/2026/06/21/ai-code-pr-merge-7-questions-checklist.html) 에서 *AI 가 못 하는 영역* :
- *우리 도메인 규칙 의 *명시화*
- *비즈니스 의 *진짜 invariant 식별*
- *역할 / 책임 의 *근거 있는 분배*

→ *오브젝트* 의 *모든 메시지 가 *바로 그 영역*. *AI 가 *junior 코드 자동화* 한 시대 에 *senior 의 *남은 가치 가 *책임 의 정확한 분배*.

### 9.2 *2026 년 의 *유효 성*

> *Spring Boot 4*, *Kotlin 2.0*, *Java 25 LTS*, *Virtual Thread* — 도구 는 *7 년 동안 변했다*. *책 의 *원칙 은 변하지 않았다*.

*Virtual Thread* 위에서 *비즈니스 코드 가 *수십만 동시성* 으로 도는 시대 에도 *그 비즈니스 의 *invariant 는 *결국 *Order, Account, Payment 같은 *객체 의 *책임 의 명확성*. *오브젝트 가 *2026 년 에도 *현역* 이다*.

---

## 10. *결론 — *밀도 의 책***

> *오브젝트* 는 *읽기 쉬운 책 이 아니다*. *656 쪽 의 *밀도 가 *높음*. *코드 가 *대부분 의 페이지*. *그러나 *그 656 쪽 을 *3 ~ 6 개월 에 걸쳐 *천천히 *완독* 하면 *내 코드 의 *모든 줄 의 *시야 가 *바뀐다*.

오늘 정리한 *내 인상* :
1. **장점**: 코드 의 정확함 + 한국어 의 정밀함 + 책임 중심 의 일관성 + 영화 예매 의 단계 적 변화
2. **단점**: Java 만 + 함수형 미언급 + 분산 외 + 656 쪽 분량 + 후반 부 피로감
3. **여러 리뷰 공통**: *6-7 장 의 *어려움*, *영화 예매 의 *영혼 있는 반복*, *현장 적용 의 *추가 학습 필요*
4. **2026 년 의 유효성**: *AI 시대 의 *senior 의 *남은 영역* — *책임 의 명확한 분배* — 의 *교과서*

> *책 읽기 의 *목적* 이 *추상 적 인 *교양* 이 아니라 *내 다음 PR 의 *작은 책임 분배 의 *근거 있는 결정* 이라면 — *오브젝트* 는 *그 결정 을 *656 쪽 동안 *체화* 시키는 *공장*.

*Spring Boot 의 *Service 클래스* 가 *수백 줄 의 *지휘 자* 로 *부풀어 갈 때*, *오브젝트* 의 *책임 중심 의 시야* 가 *그 부풀음 을 *Order, Cart, Payment 의 *각 객체 의 *작은 메서드* 로 *분해* 해 준다. *그 분해 의 능력 — *2026 년 의 *시니어 백엔드 의 *진짜 의무*.

내 글 의 *모든 인프라 / 보안 / 관측성* 의 *위* 에 *결국 *비즈니스 코드* 가 *있다*. *그 코드 의 *작은 책임* 이 *7 년 후* 의 *유지보수 가능 한 *시스템 의 *진짜 토대*. *오브젝트* 는 *그 토대 의 *건축 학*.

---

## *참고 (Sources)*

- [[리뷰] 오브젝트 독후감 | Jinwoo's Blog](https://bugoverdose.github.io/essay/object-book-review/)
- [review - 오브젝트: 코드로 이해하는 객체지향 설계 (Velog)](https://velog.io/@dvmflstm/review-%EC%98%A4%EB%B8%8C%EC%A0%9D%ED%8A%B8-%EC%BD%94%EB%93%9C%EB%A1%9C-%EC%9D%B4%ED%95%B4%ED%95%98%EB%8A%94-%EA%B0%9D%EC%B2%B4%EC%A7%80%ED%96%A5-%EC%84%A4%EA%B3%84)
- [오브젝트 | 위키북스 공식](https://wikibook.co.kr/object/)
- [오브젝트(조영호) 느낀점 정리 (Velog)](https://velog.io/@xogml951/%EC%98%A4%EB%B8%8C%EC%A0%9D%ED%8A%B8%EC%A1%B0%EC%98%81%ED%98%B8-%EC%9A%94%EC%95%BD-%EC%A0%95%EB%A6%AC)
- [BookReview [오브젝트: 지은이의 글] - Blue log](https://fkdl0048.github.io/bookreview/bookreview_objects/)
- [[책] "오브젝트" 후기 (Velog)](https://velog.io/@joon6093/%EC%B1%85-%EC%98%A4%EB%B8%8C%EC%A0%9D%ED%8A%B8-%ED%9B%84%EA%B8%B0)
- [오브젝트 | 교보문고](https://product.kyobobook.co.kr/detail/S000001766367)
- [오브젝트 | 알라딘 (위키북스 IT Leaders 시리즈 29)](https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=193681076)
- 자매편 :
  - [*DB 의 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
  - [*AI 코드 PR 머지 7 질문*](/2026/06/21/ai-code-pr-merge-7-questions-checklist.html)
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
