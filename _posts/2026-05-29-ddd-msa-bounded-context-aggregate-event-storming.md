---
layout: post
title: "DDD 와 MSA 의 상관관계 — Bounded Context 가 곧 서비스 경계인 이유, 그리고 DDD 없이 MSA 가면 만나는 Distributed Monolith"
date: 2026-05-29 00:45:00 +0900
categories: [architecture, backend]
tags: [ddd, msa, microservices, bounded-context, aggregate, event-storming, hexagonal, outbox, distributed-monolith, archunit]
---

"MSA 갈 거면 DDD 부터 배워라" 라는 말, 매우 자주 듣는데 *왜* 가 잘 안 드러난다. DDD 는 2003 년 (Eric Evans), MSA 는 2014 년 (Lewis & Fowler). *서로를 위해 태어난 게 아닌* 두 개념이 결과적으로 *떨어질 수 없는 한 쌍* 이 된 데에는 분명한 구조적 이유가 있다.

이 글은 두 개념이 *어떤 컨셉 단위에서 1:1 매핑* 되는지, *DDD 없이 MSA 가면 어떤 모양의 시스템이 나오는지*, 그리고 내 실제 settlement / lemuel-xr 운영에서 어떻게 적용하고 있는지 — 세 가지 축으로 정리한다.

> 본 글의 예시는 *내가 운영 중인 모노레포 (settlement, sparta-msa, lemuel-xr)* 의 실제 패턴을 인용한다. 코드 일부는 추상화 / 단순화돼있다.

---

## TL;DR — DDD 컨셉과 MSA 컨셉의 매핑표

| DDD 컨셉 | MSA 컨셉 | 1:1 인가 |
|---|---|---|
| **Bounded Context** | **Microservice** (또는 그 묶음) | *대체로* 1:1, 큰 Context 는 여러 서비스로 분할 가능 |
| **Aggregate** | *서비스 내부의 트랜잭션 단위* | *반드시* 한 서비스 안. 절대 분리 X |
| **Ubiquitous Language** | API / 이벤트 contract (OpenAPI, AsyncAPI, schema registry) | *동의어 사전 = 스키마* |
| **Domain Event** | Integration Event (Kafka topic / RabbitMQ exchange) | Outbox 로 두 세계 연결 |
| **Context Map (9가지 패턴)** | 서비스 간 관계 (sync vs async, partnership vs customer-supplier) | *패턴 그대로 매핑* |
| **Anti-Corruption Layer (ACL)** | API Gateway / Adapter / BFF | 외부 모델로부터 도메인 보호 |
| **Repository** | 서비스 내부의 DB 접근 추상 (Spring Data JPA, MongoTemplate 등) | 1:1 |
| **Hexagonal Architecture (Ports & Adapters)** | 서비스 내부의 레이어 격리 | *내부* 패턴, MSA 가 아니라도 가치 |
| **Saga** | *여러 서비스를 가로지르는* 비즈니스 트랜잭션 | DDD 도 Saga 개념 정의함 (Vernon) |

---

## 0. 역사적 만남 — 왜 두 개념이 한 쌍이 됐나

### DDD (2003)
- Eric Evans, *Domain-Driven Design: Tackling Complexity in the Heart of Software*
- *복잡한 도메인을 어떻게 모델링할 것인가* 가 본질
- 당시 주적: Monolith 내부의 *Big Ball of Mud* — 도메인 로직이 여기저기 흩어져 유지보수 불가
- 처방: **모델 = 코드** 일치, **Bounded Context** 로 *의미가 달라지는 경계* 명시

### MSA (2014)
- James Lewis, Martin Fowler, [Microservices](https://martinfowler.com/articles/microservices.html)
- *시스템을 어떻게 *물리적으로* 나눌 것인가* 가 본질
- 당시 주적: Monolith 의 *배포 단위 거대화* — 한 줄 고치려 전체 빌드/배포
- 처방: **독립 배포 가능한 작은 서비스들**, 각자의 DB, 가벼운 통신

### 만남 (2015~)
두 개념은 *같은 문제의 다른 측면* 을 다루고 있었다:
- DDD: *의미적 경계*
- MSA: *물리적 경계*

MSA 가 부상하면서 *"그래서 어디서 잘라야 하는데?"* 라는 질문에 직면. DDD 가 *이미* 답을 가지고 있었다 — **Bounded Context 경계가 곧 의미적 단위**. 그걸 *물리적으로 분리* 하면 자연스럽게 MSA.

Vaughn Vernon (DDD 거장) 의 *Implementing Domain-Driven Design* (2013) 이후의 DDD 서적들은 *전부* MSA 매핑을 전제로 쓰여진다. 두 개념은 *동의어* 가 아니지만, *현대 시스템 설계의 표준 쌍* 이 됐다.

---

## 1. Bounded Context = Microservice 경계

가장 중요한 한 줄:

> **"서비스 하나는 Bounded Context 하나, 또는 그 일부 또는 묶음."**

### Bounded Context 의 정의

같은 단어가 *문맥에 따라 다른 의미* 를 가지는 경계. 예:

| Context | "Order" 의 의미 |
|---|---|
| Sales (영업) | 고객이 *지금 카트에 담은 것* |
| Fulfillment (배송) | 물류 시스템이 *집어야 할 박스* |
| Billing (결제) | *결제가 완료된* 거래 단위 |
| Accounting (회계) | *수익으로 인식된* 항목 |

같은 "Order" 라는 단어를 *한 클래스* 로 만들면 어느 Context 에서도 진심으로 어울리지 않는 *Frankenstein* 이 된다. DDD 의 답: **각 Context 마다 자기만의 Order 모델**.

### MSA 로 옮기면

```
sales-service       → SalesOrder (cart_id, items, customer_id, ...)
fulfillment-service → ShipmentOrder (warehouse_id, packed_at, courier_id, ...)
billing-service     → PaymentOrder (amount, payment_method, paid_at, ...)
accounting-service  → RevenueEntry (recognized_at, account_code, ...)
```

각 서비스가 *자기 모델만* 책임. 다른 서비스의 모델은 *이벤트 페이로드* 또는 *API 응답 DTO* 로만 알게 됨.

### 1:1 매핑이 아닌 경우

| 상황 | 패턴 |
|---|---|
| Bounded Context 가 너무 큼 | 여러 서비스로 분할 (예: `sales-cart`, `sales-order`, `sales-pricing`) |
| Bounded Context 가 너무 작음 | 여러 Context 를 한 서비스 안에 — 단 *별도 모듈* 로 격리 |
| 빠른 변경이 필요 | 시작은 *Modular Monolith* — Bounded Context 만 분리, 배포는 일체 |

**내 settlement 의 실제 구조**:
- settlement 는 *논리적으론* 한 Bounded Context (정산)
- 하지만 *물리적으론* `settlement-service` 가 library jar 로 빌드돼 `order-service` 의 fat jar 에 번들됨
- 즉 *모노-MSA 하이브리드* — Modular Monolith 와 MSA 사이
- 왜? 정산 로직과 주문 로직이 *항상 함께 배포돼야* 일관성 보장 + 운영 단순화

DDD 가 *"꼭 물리적으로 나눠라"* 라고 안 했다. 그게 핵심. 경계는 *의미* 가 우선, 물리는 *상황에 맞춰*.

---

## 2. Aggregate = Transactional Boundary

DDD 의 *Aggregate* 는 *함께 일관성을 유지해야 하는 객체들의 클러스터*. Aggregate Root 가 외부에서 접근할 수 있는 유일한 entrypoint.

### 핵심 규칙 (Vaughn Vernon 이 강조)

1. *한 트랜잭션 = 한 Aggregate 만 수정*
2. Aggregate 간엔 *Eventual Consistency*
3. Aggregate 끼리는 *ID 로만 참조* (객체 참조 금지)

### MSA 와 곧장 매핑

| Aggregate 규칙 | MSA 에서의 의미 |
|---|---|
| 한 트랜잭션 = 한 Aggregate | 한 트랜잭션이 *한 서비스 안* 에서 끝남 |
| Aggregate 간 Eventual Consistency | 서비스 간 Eventual Consistency (Saga, Outbox) |
| ID 로만 참조 | 서비스 간 *외부 키로만* 참조 (FK 없음) |

이게 *왜 중요한가*: MSA 에서 *분산 트랜잭션 (XA, 2PC)* 을 피하는 이유가 여기 있다. Aggregate 가 트랜잭션 경계라면, *Aggregate 가 한 서비스 안에 있는 한* 분산 트랜잭션이 필요 없다.

### 흔한 함정

```java
// ❌ 안티패턴: 한 트랜잭션에 두 Aggregate 수정
@Transactional
public void transferMoney(Long fromId, Long toId, BigDecimal amount) {
    Account from = accountRepo.findById(fromId);  // Aggregate 1
    Account to = accountRepo.findById(toId);      // Aggregate 2
    from.withdraw(amount);
    to.deposit(amount);
    accountRepo.save(from);
    accountRepo.save(to);
}
```

이 코드는 *돌긴 도는데*, Aggregate 경계를 침범했다. 두 계좌가 다른 서비스로 분리될 때 *분산 트랜잭션* 외엔 답이 없어진다.

```java
// ✅ DDD 권장: 도메인 이벤트로 Eventual Consistency
@Transactional
public void requestTransfer(Long fromId, Long toId, BigDecimal amount) {
    Account from = accountRepo.findById(fromId);
    from.requestWithdraw(amount);  // status=PENDING_TRANSFER
    accountRepo.save(from);
    outbox.append(new MoneyWithdrawn(fromId, toId, amount));  // event
}

@EventListener
public void on(MoneyWithdrawn event) {  // 다른 트랜잭션
    Account to = accountRepo.findById(event.toId);
    to.deposit(event.amount);
    accountRepo.save(to);
    outbox.append(new MoneyDeposited(...));
}
```

각 step 이 *한 Aggregate 만* 수정. 일관성은 *이벤트 체인* 으로. 이걸 *Saga* 라 부른다.

---

## 3. Domain Event → Outbox Pattern — DDD 와 MSA 의 진짜 만남

DDD 의 *Domain Event* 는 "도메인에서 *일어난 사건*" 을 표현. 처음엔 *프로세스 내* 통신 수단 (Spring `ApplicationEventPublisher`) 으로 출발.

MSA 에선 이 이벤트가 *서비스 경계를 넘어야* 한다. 그런데 *DB 트랜잭션* 과 *메시지 발행* 이 두 시스템이라 *원자적이지 않다*:

```java
// ❌ 함정: DB commit 후 Kafka 발행
@Transactional
public void placeOrder(Order order) {
    orderRepo.save(order);          // DB commit OK
    kafka.send("order.created", e); // 여기서 네트워크 실패하면?
}
// 결과: DB 에 주문 있는데 다른 서비스는 모름 → 데이터 불일치
```

해결책: **Outbox Pattern**.

### Outbox Pattern (settlement 의 실제 구현)

```sql
-- 같은 DB 트랜잭션 안에서
INSERT INTO orders (id, ...) VALUES (?, ...);
INSERT INTO outbox (event_id, type, payload, status, created_at)
  VALUES (?, 'OrderCreated', ?, 'PENDING', NOW());
COMMIT;

-- 별도 폴러 (Scheduled Job) 가:
SELECT * FROM outbox WHERE status='PENDING' LIMIT 100;
-- Kafka 발행 후
UPDATE outbox SET status='PUBLISHED', published_at=NOW() WHERE event_id=?;
```

핵심: *DB 트랜잭션 = 비즈니스 변경 + 이벤트 기록* 을 *원자적으로* 묶음. 메시지 발행은 그 다음 *eventual* 로.

### Triple Idempotency (settlement 의 at-least-once 처리)

at-least-once 메시징은 *같은 이벤트가 두 번 도착할 수 있음*. 이걸 receiver 쪽에서 막아야 한다.

```
L1: Outbox 의 event_id UNIQUE 제약
    → 같은 이벤트가 두 번 outbox 에 들어가는 것 방지

L2: Consumer 쪽의 processed_events 테이블 PK
    → 이미 처리한 event_id 면 즉시 skip

L3: 비즈니스 자연키 UNIQUE 제약 (예: payment_request_id UNIQUE)
    → L1/L2 가 뚫려도 DB 가 마지막 방패
```

이 3중 방어가 *at-least-once 메시징을 idempotent receiver* 로 흡수하는 표준 패턴.

DDD 책엔 이 디테일이 잘 안 나온다. 하지만 *DDD 의 Domain Event 를 MSA 에 옮기려면* 이 패턴이 *사실상 강제*. settlement 운영 18개월간 *L3 가 L1/L2 의 버그를 두 번 잡아준 사례* 가 있다 — 그 둘 중 어느 하나만 있었으면 데이터 불일치 사고였다.

---

## 4. Context Map 9 가지 패턴 — 서비스 간 관계의 카탈로그

DDD 가 *Context 간 관계* 를 9가지 패턴으로 정리했다. MSA 의 서비스 간 관계와 *완벽히 매핑* 된다.

| 패턴 | 의미 | MSA 예시 |
|---|---|---|
| **Partnership** | 두 팀이 *함께 성공/실패* | 같은 회사의 두 마이크로서비스 (운영 책임 공유) |
| **Customer-Supplier** | 상류가 *명시적* 으로 하류를 지원 | API 제공 팀 (상류) + 사용 팀 (하류) |
| **Conformist** | 하류가 상류 모델을 *그대로 받아씀* | 외부 SaaS API 를 우리 모델에 맞춰 변환 안 함 |
| **Anti-Corruption Layer (ACL)** | 상류 모델을 *번역하는 레이어* | 결제 PG 의 응답을 우리 도메인으로 변환 |
| **Open Host Service (OHS)** | *공개 API* 로 여러 하류 지원 | 인증 서비스가 명세된 OAuth/OIDC 제공 |
| **Published Language (PL)** | 공개 *스키마* (이벤트, schema registry) | Avro/Protobuf 스키마 registry |
| **Shared Kernel (SK)** | 두 Context 가 *공유 코드* | shared-common 모듈 (with 엄격한 변경 룰) |
| **Big Ball of Mud** | 경계가 없는 카오스 | 흔한 레거시 모노리스 |
| **Separate Ways** | 통합 *안 함* | 두 서비스가 *서로 모름* (가능한 경우) |

### 실전 예시 — 내 sparta-msa 의 Context Map

```
[user-service] ──── OHS ────→ [order-service] ──── ACL ────→ [pg-gateway-service]
       │                              │                            │
       │ shared-common (SK)           │ outbox events (PL)          │
       │                              ↓                            │
       └──────────────────────→ [product-service]                  │
                                      ↑                            │
                                      └─── Conformist ─── external-product-feed
                                                                   │
[notification-service] ←──── PL (events) ────────────────────────┘
```

이런 *Context Map* 을 *그리고 나서야* 어떤 서비스끼리 sync 통신, 어떤 끼리 event 통신, 어디에 ACL 이 필요한지 결정 가능.

---

## 5. DDD 없이 MSA 가면 — Distributed Monolith 의 출현

MSA 만 흉내내고 DDD 없이 가면 *최악의 패턴* 이 만들어진다 — **Distributed Monolith**.

### 증상

| 증상 | 원인 |
|---|---|
| 한 기능 추가에 3~4 개 서비스 *동시 배포* 필요 | 서비스 경계가 *기술적* 이지 *의미적* 이 아님 |
| 서비스 간 *동기 REST 콜이 5단계 이상* 체인 | Aggregate 분리 잘못 → 한 트랜잭션이 여러 서비스 거침 |
| 서비스 다운 시 *연쇄 장애* | 의존 그래프가 *cycle* 포함 |
| 같은 DB 스키마를 *여러 서비스가 공유* | "data-service" 같은 안티패턴 — 데이터 따로 두지 않음 |
| API 변경 시 *모든 consumer 동시 deploy* | Conformist 만 있고 ACL 없음 |
| 운영 복잡도가 *모노리스보다 높음* | 분리의 *이득* 은 없고 *비용* 만 |

### 왜 일어나나

DDD 없이 *코드 라인 수* 또는 *팀 구조* 또는 *기술 스택* 으로 서비스를 나누면 이런 결과가 나온다. 흔한 케이스:

```
잘못된 분리:
  - user-controller-service  (Controller 만 따로)
  - user-business-service    (Service 만 따로)
  - user-data-service        (Repository 만 따로)

→ 한 user 등록 기능에 3 서비스 호출 체인
→ 한 서비스만 죽어도 user 등록 불가
→ 트랜잭션 분산 불가
```

올바른 분리 (DDD 적용):

```
Bounded Context 기반:
  - identity-service          (인증/인가)
  - profile-service           (사용자 프로필)
  - notification-service      (사용자 알림)

→ 각자 controller + service + repository 풀스택
→ 각자 자기 DB
→ 한 서비스 죽어도 다른 서비스 살아있음
```

### 진단 체크리스트

내 시스템이 Distributed Monolith 인지 확인:

- [ ] 새 기능 추가 시 *2 개 이상* 서비스 배포가 *반드시* 필요한가?
- [ ] 서비스 간 *동기 호출 체인이 3 단계 이상* 인가?
- [ ] 한 서비스의 DB 스키마를 *다른 서비스가 직접 조회* 하는가?
- [ ] 서비스 다운 시 *연쇄 장애* 가 발생한 적 있는가?

하나라도 ✅ 면 *Distributed Monolith 의심*. DDD 의 *Context Map* 부터 다시 그려야 한다.

---

## 6. Hexagonal Architecture — 서비스 *내부* 의 DDD

MSA 의 *밖* 은 Context Map 으로, *안* 은 Hexagonal Architecture 로 정리.

```
┌──────────────────── Adapter (Inbound) ────────────────────┐
│  REST Controller / Kafka Consumer / Scheduled Job         │
└────────────────────────────┬──────────────────────────────┘
                             │
                             ↓
                  ┌──────── Port (Inbound) ────────┐
                  │  UseCase / ApplicationService  │
                  └────────────┬───────────────────┘
                               │
                               ↓
                    ┌──────── Domain ────────┐
                    │  Aggregate / Entity    │
                    │  Domain Service        │
                    │  Domain Event          │
                    └────────────┬───────────┘
                                 │
                                 ↓
                       ┌─── Port (Outbound) ───┐
                       │  Repository / Gateway │
                       └───────────┬───────────┘
                                   │
                                   ↓
                  ┌──── Adapter (Outbound) ────┐
                  │  JPA Repository / HTTP     │
                  │  Client / Kafka Producer   │
                  └────────────────────────────┘
```

핵심 규칙:
- *Domain* 은 *Spring, JPA, Kafka 의존 없음* — 순수 비즈니스 로직
- *Application* 은 *Domain + Port* 만 알고, 구체 Adapter 모름
- *Adapter* 가 외부 기술 (DB, HTTP, MQ) 을 *Port 인터페이스* 에 맞춤
- 의존 방향: *Adapter → Application → Domain* (역방향 절대 X)

### ArchUnit 으로 강제

위 의존 규칙을 *문서* 가 아닌 *컴파일러 같은 게이트* 로 강제하려면:

```java
@AnalyzeClasses(packages = "com.lemuel.settlement")
public class HexagonalArchitectureTest {

    @ArchTest
    static final ArchRule domain_should_not_depend_on_spring =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAPackage("org.springframework..");

    @ArchTest
    static final ArchRule application_should_not_use_jpa_directly =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAPackage("jakarta.persistence..");

    @ArchTest
    static final ArchRule adapter_should_not_cross_domain =
        noClasses().that().resideInAPackage("..adapter.in.web..")
            .should().dependOnClassesThat().resideInAPackage("..adapter.out.persistence..");
}
```

settlement 는 ArchUnit 3 가지 핵심 룰로 *PR 단위로* 헥사고날 위반을 reject 한다. *코드 리뷰가 사람이 아닌 컴파일러가* 1차 검토.

이 패턴은 *MSA 의 안* 이지만 *모노리스에도 동일하게* 적용 가능. DDD 는 MSA 의 전제 조건이 *아니지만*, *함께 가면 시너지* 가 가장 크다.

---

## 7. 흔한 오해 3가지

### 오해 1: "DDD = 마이크로서비스다"

❌. DDD 는 *Modular Monolith* 에도, *Serverless* 에도, *단일 람다* 에도 적용 가능. *모델링 방법론* 이지 아키텍처가 아니다.

내 settlement 는 *모노-MSA 하이브리드* (library jar + fat jar). DDD 패턴을 *전부* 적용하면서도 *물리적 분리는 적용 안 함*. 이게 가능한 이유는 DDD 와 MSA 가 *독립적 개념* 이기 때문.

### 오해 2: "Bounded Context = Service 는 무조건 1:1"

❌. 1:N 또는 N:1 도 가능. 결정 기준은:

- 변경 주기 (같이 변하면 한 서비스로)
- 운영 책임 (한 팀이면 한 서비스)
- 트래픽 패턴 (다른 스케일링 필요하면 분리)
- 데이터 크기 (한 DB 로 감당 안 되면 분리)

### 오해 3: "이벤트 기반이면 자동으로 좋은 MSA"

❌. *이벤트 토픽 수십 개에 모두가 publish/subscribe* 하면 *Event Spaghetti* — 또 다른 Distributed Monolith. 이벤트도 *Context Map* 의 *Published Language* 패턴으로 *명시적으로 설계* 해야 한다.

내 환경 *AsyncAPI* 스펙으로 이벤트 스키마 관리, schema registry 로 *호환성 정책* 강제 (Backward / Forward / Full).

---

## 8. Event Storming — DDD/MSA 설계의 출발점

코드 한 줄 짜기 *전에* 도메인 모델을 *시각적으로* 발견하는 워크샵. Alberto Brandolini (2013) 제안.

### 흐름

```
[관계자 모두 모임 (개발 + PO + 도메인 전문가)]
                ↓
[Domain Event 부터 포스트잇으로 시간순 나열]
   주황색: 비즈니스에서 *과거형* 사건 (OrderPlaced, PaymentApproved, ...)
                ↓
[각 Event 의 Command 와 Actor 식별]
   파란색: 명령 (PlaceOrder, ApprovePayment, ...)
   노란색: Actor / Role
                ↓
[Aggregate 와 Bounded Context 발견]
   분홍색: Aggregate
   굵은 선: Bounded Context 경계
                ↓
[Policy / Read Model / External System 식별]
                ↓
[자연스럽게 *서비스 경계* 가 보이기 시작]
```

이게 *왜 효과적인가*: 코드 시작 전 *도메인 전문가의 머릿속 모델* 을 시각화한다. 개발팀이 도메인을 *오해한 채* 코드 짜는 사고를 막는다.

내 lemuel-xr 의 *Scene 분기 구조* 를 설계할 때 Event Storming 을 2회 진행. 첫 회의 결과로 *Track A (성경 스토리)* vs *Track B (인물 미션)* 을 *별도 Aggregate* 로 분리. 이게 두 트랙이 *독립적으로 변경 가능* 하게 만든 기반.

---

## 9. 실전 적용 — 내 settlement / lemuel-xr 의 DDD/MSA

### settlement

| DDD 컨셉 | 구현 |
|---|---|
| Bounded Context | Settlement (정산) |
| Aggregate | `SettlementBatch`, `PaymentRequest`, `RefundCase` |
| Hexagonal | domain / application / adapter 3 레이어 분리 (ArchUnit 강제) |
| Domain Event | `SettlementCompleted`, `RefundRequested` |
| Outbox | PENDING → PUBLISHED 상태머신, 배치 폴링 |
| Triple Idempotency | L1 outbox event_id UNIQUE / L2 processed_events PK / L3 자연키 UNIQUE |
| Context Map (with order-service) | Partnership (같이 배포되는 library jar) |
| Anti-Corruption Layer | PG (결제대행사) 응답 → 우리 도메인 변환 |
| Shared Kernel | `shared-common` 모듈 (변경 시 양쪽 빌드 강제) |

운영 18개월 동안 Triple Idempotency 의 *L3 가 L1/L2 의 버그를 2 회 잡아준* 사고가 있었다. *DDD 의 Eventual Consistency 모델 + at-least-once 메시징* 을 *idempotent receiver* 로 흡수하는 패턴은 *프로덕션에서 필요* 한 이유가 명확하다.

### lemuel-xr

| DDD 컨셉 | 구현 |
|---|---|
| Bounded Context | XR Experience, AI Generation, User Reflection (3개) |
| Aggregate | `Scene`, `Meditation`, `UserSession` |
| Hexagonal | enforcer agent 가 자동 검토 |
| Domain Event | `SceneCompleted`, `MeditationGenerated` |
| Anti-Corruption Layer | LLM (OpenAI/Claude) 응답 → 우리 도메인 변환 + theology gate |
| Context Map (with academy) | Customer-Supplier (academy 가 lemuel-xr 의 컨텐츠 사용) |

---

## 10. 결론 — 의미적 경계가 먼저, 물리적 경계가 다음

| 질문 | DDD | MSA |
|---|---|---|
| *왜* 나누는가? | 의미가 달라지는 곳 | 변경 / 배포 / 운영의 독립성 |
| *어디서* 나누는가? | Bounded Context | Bounded Context 의 물리적 표현 |
| *어떻게* 나누는가? | 모델링 | API + DB 분리 + 독립 배포 |
| *언제* 나누는가? | *항상* (모노리스에도) | *변경 비용이 분리 비용을 넘는 순간* |

MSA 에서 *경계를 어디에 그을 것인가* 는 결국 DDD 가 답한다. DDD 없이 MSA 만 가면 *경계가 자의적* 이 되고, 그 결과가 Distributed Monolith.

반대로 DDD 만 잘 해도 *MSA 가 아니어도* 가치 충분 — Modular Monolith 라는 매우 합리적 선택지가 존재한다 (Shopify, Stack Overflow, GitHub 모두 이 길).

**한 줄로:** *DDD 는 "왜·어디서 나눠야 하는가" 의 답이고, MSA 는 "그 답을 어떻게 물리적으로 실현하는가" 의 한 가지 선택지.*

내 다음 시스템을 설계한다면 *Event Storming 1주 → Bounded Context 도출 → Modular Monolith 로 시작 → 변경 비용이 분리 비용을 넘기 시작하는 Context 만 점진적 MSA 분리* 순서로 가겠다. *처음부터 MSA* 는 거의 항상 *조기 최적화*.

---

## 참고

- Eric Evans, *Domain-Driven Design: Tackling Complexity in the Heart of Software* (2003)
- Vaughn Vernon, *Implementing Domain-Driven Design* (2013)
- Vaughn Vernon, *Domain-Driven Design Distilled* (2016) — DDD 와 MSA 매핑 명시
- Alberto Brandolini, *Introducing EventStorming* (2017)
- Sam Newman, *Building Microservices* (2nd ed, 2021) — DDD 기반 MSA 설계
- Martin Fowler, [Microservices](https://martinfowler.com/articles/microservices.html) (2014)
- Chris Richardson, [microservices.io](https://microservices.io/) — 패턴 카탈로그 (Outbox, Saga, ACL 등)
- 관련 글: [홈랩 K3s 5노드의 CPU 가 모자랄 때 — 데이터센터의 Capacity Planning 흉내내기]({% post_url 2026-05-29-homelab-capacity-planning-datacenter-style %})
