---
layout: post
title: "*트랜잭션 롤백 전략* — *깔끔하게 *되돌리는 *7 가지 *길*"
date: 2026-06-13 04:00:00 +0900
categories: [backend, database, architecture]
tags: [transaction, rollback, spring, saga, compensation, idempotency, distributed]
---

> *commit 은 *쉽다*. *rollback 이 *어렵다*.
> *문제가 *생기면 *처음 으로 *되돌리는 *능력* — 그게 *시스템 의 *진짜 *완성도*.
> *Spring 의 *@Transactional 한 줄 *밑에 *7 가지 *롤백 전략* 이 *숨어 있다*. 이 글은 그 *전체 지도*.

---

## TL;DR

| 전략 | 적용 상황 |
|------|-----------|
| **자동 rollback** | *RuntimeException → 자동* — Spring 의 기본 |
| **rollbackFor** | *Checked exception 도 rollback 시킬 때* |
| **noRollbackFor** | *특정 예외 는 rollback 안 할 때* (예: 비즈니스 정상 흐름) |
| **setRollbackOnly()** | *코드 흐름 으로 *rollback 결정* — *예외 없이도* |
| **Savepoint** | *부분 rollback* — 일부만 되돌림 |
| **보상 트랜잭션 (Saga)** | *분산 시스템 의 *논리적 rollback* — 결제 환불 등 |
| **Outbox + 멱등성** | *재시도 + 부분 실패 시 *안전* — *최종 consistency* |

*핵심 한 줄* :

> *Rollback 은 *DB 의 *기능* 이 *아니라 *시스템 전체 의 *철학*. *각 layer 마다 *다른 전략* 이 *필요* 하다.

---

## 1. *Rollback 이 *왜 *어려운가*

### *Rollback 의 *목표*

> *시스템 의 *상태 를 *문제 *전 *시점 으로 *원복*.*

말은 단순하다. 어려움 :

1. ***이미 *발생한 *부수 효과*** — *메일 발송 / 결제 차감 / 외부 통지* 등 — 이미 *현실에 *흔적*. *DB rollback 만 으로 안 됨*.
2. ***멀티 시스템*** — *DB + Redis + Kafka + 외부 API* 의 *부분 성공 / 부분 실패*.
3. ***시간*** — *수 초 이상 지난 *작업의 *원복* — *사용자가 *이미 본 *결과 도 있다*.
4. ***멱등성 부재*** — *재시도 시 *중복 처리 위험*.

→ *Rollback 의 *어려움 이 *시스템 의 *복잡도 의 *원천*. 그래서 *전략* 의 *선택* 이 *결정 적*.

---

## 2. **자동 Rollback** — *Spring 의 *기본*

### 동작

```java
@Transactional
public void process() {
  repo.save(...);
  throw new RuntimeException("something wrong");
  // → 자동 rollback
}
```

Spring 의 *AOP proxy* 가 *메서드 종료 시점* 의 *예외 검사* :
- *RuntimeException + Error* → **rollback**
- *Checked Exception* → **commit (!)**

이 동작 의 *2 가지 *함정* :

1. *Checked Exception 도 *rollback 시키고 싶을 때* → 다음 섹션
2. *예외 잡으면 *rollback 안 됨* — try / catch 로 *swallow 하면 *commit*.

```java
@Transactional
public void process() {
  try {
    repo.save(...);
    throw new IOException("...");
  } catch (IOException e) {
    log.error(e);  // ❌ 예외 *덮음* → commit 됨
  }
}
```

---

## 3. **rollbackFor / noRollbackFor** — *미세 조정*

### rollbackFor — *Checked 도 rollback*

```java
@Transactional(rollbackFor = Exception.class)
public void process() throws IOException {
  repo.save(...);
  if (...) throw new IOException(...);  // rollback 됨
}
```

`rollbackFor = Exception.class` 또는 `rollbackFor = SomeCheckedException.class` 로 *명시*.

### noRollbackFor — *특정 예외 는 rollback 안 함*

```java
@Transactional(noRollbackFor = NotFoundException.class)
public Order findOrCreate(Long id) {
  Order existing = repo.find(id);
  if (existing == null) throw new NotFoundException();  // 비즈니스 흐름
  return existing;
}
```

*비즈니스 흐름 의 일부 인 예외* 는 *rollback 안 시킴*. 이미 *부분 commit 된 데이터* 보존.

### *경험적 *권장*

```java
@Transactional(rollbackFor = Exception.class)
```

*모든 *서비스 메서드 의 *기본*. *Checked exception 누락* 의 *함정* 차단.

---

## 4. **setRollbackOnly()** — *예외 없이 *rollback*

### 코드 흐름 으로 *rollback 결정*

```java
@Transactional
public void process() {
  if (invalidCondition()) {
    TransactionAspectSupport.currentTransactionStatus()
                             .setRollbackOnly();
    return;  // 예외 없이 *조용히 rollback*
  }
  repo.save(...);
}
```

또는 *PlatformTransactionManager 직접 사용* :

```java
@Autowired TransactionTemplate txTemplate;

public void process() {
  txTemplate.execute(status -> {
    if (invalidCondition()) {
      status.setRollbackOnly();
      return null;
    }
    repo.save(...);
    return null;
  });
}
```

### *언제 *유용한가*

- *예외 throwing 이 *과한 *비즈니스 흐름*
- *복잡한 *조건 로직 *기반 *결정*
- *로깅 / 분석 후 *조용한 rollback*

→ *흐름 의 *명확함* 이 강점. 단 *프로그램 흐름 의 *명시* 가 *필수* — *모르고 *지나가면 *디버깅 *지옥*.

---

## 5. **Savepoint** — *부분 Rollback*

### 동작

```java
@Transactional
public void process() {
  repo.saveOrder();           // [1] 저장

  Object savepoint = null;
  try {
    txManager.createSavepoint();
    repo.savePayment();        // [2] 시도
  } catch (Exception e) {
    txManager.rollbackToSavepoint(savepoint);
    // [2] 만 rollback, [1] 은 *유지*
  }

  repo.markComplete();         // [3] 진행
}
```

### Spring 의 @Transactional(propagation = NESTED)

```java
@Transactional(propagation = REQUIRED)
public void parent() {
  service.savePart1();        // 부모 tx
  try {
    service.tryPart2();        // 자식 = savepoint
  } catch (Exception e) {
    log.warn("Part 2 실패, 무시");
    // 부모 tx 는 *살아있음*
  }
}

@Transactional(propagation = NESTED)
public void tryPart2() { ... }
```

### *주의 — *현실의 *제약*

- *NESTED 는 *JDBC Savepoint 지원 DB 만* — Postgres / Oracle / MS-SQL OK. *MySQL InnoDB 는 *조건부*.
- *JPA / Hibernate 와 *호환성* 문제 가 *자주 발생*.
- *디버깅 *어려움*.

→ *NESTED 는 *현장에서 *최후 의 선택*. *대부분 *Saga 로 *해결*.

---

## 6. **분산 시스템의 *Rollback** — *Saga 와 *보상 트랜잭션*

### *DB rollback 의 *한계*

```
주문 생성 (DB1)     ← commit
결제 처리 (DB2)     ← commit
재고 차감 (DB3)     ← 실패!
```

DB3 만 *기술적 rollback*. 그러나 *DB1, DB2 는 *이미 commit*. *논리적 부정합*.

### Saga 패턴

```
주문 생성 (DB1)  ↔ 보상: 주문 취소
결제 처리 (DB2)  ↔ 보상: 결제 환불
재고 차감 (DB3)  ↔ 보상: 재고 복원
```

*각 단계 가 *독립 commit*. 실패 시 *역순으로 *보상 트랜잭션* 실행.

### *보상 트랜잭션 의 *원칙*

1. ***멱등성 (Idempotency)*** — *여러 번 실행해도 *같은 결과*
2. ***즉시 실행*** — *지연 불가* — *바로 보상* 시도
3. ***실패 시 재시도 + 알림*** — *최후 의 수동 처리* 까지 고려
4. ***감사 (audit) 기록*** — *언제 *왜 *어떻게 보상 했는지*

### *Saga 의 *2 구현*

**Choreography** :
```
이벤트 1 → 이벤트 2 → ...
실패 → 보상 이벤트 발행 → 이전 이벤트 들 *각자 *보상*
```

**Orchestration** :
```
Workflow Engine 이 *순서 제어*
실패 → 엔진 이 *순차적 *보상 호출*
```

Camunda / Temporal / AWS Step Functions 가 *대표 도구*.

---

## 7. **Outbox 패턴 과 *Rollback**

### Outbox 의 *역할*

```
1 트랜잭션 :
  - 주문 저장
  - *outbox 테이블 에 *이벤트 *insert*

별도 *publisher* :
  - outbox 의 미발행 이벤트 *읽음*
  - Kafka 에 *발행*
  - 성공 시 outbox 표시
```

### *Rollback 시 *동작*

- *주문 *실패* → *outbox event 도 *함께 rollback* (*같은 트랜잭션*)
- *Kafka 발행 *실패* → *재시도 *반복*. *outbox 의 미발행 상태* 유지
- *DB ↔ Kafka 간 *원자성 *보장*

> Outbox 는 *최종 일관성 (eventual consistency)* 의 *표준 패턴*. *분산 시스템 의 *대표 도구*.

---

## 8. **외부 호출 의 *Rollback** — *결제 환불 패턴*

### *외부 호출 의 *진짜 어려움*

```java
@Transactional
public void completeOrder() {
  orderRepo.save(...);
  paymentApi.charge(amount);      // ❌ 외부 호출 — 트랜잭션 *밖에 영향*
  emailService.send(...);          // ❌ 더 큰 영향
}
```

*DB rollback 후* :
- 결제 *완료* 그대로 — *환불 필요*
- 메일 *이미 발송* — *되돌릴 수 없음*

### *해결 — 트랜잭션 *밖* + 보상*

```java
public void completeOrder() {
  // 1. *짧은 트랜잭션* — DB만
  Order order = orderService.create(...);

  try {
    // 2. *밖* — 외부 호출
    PaymentResult pay = paymentApi.charge(amount);

    // 3. *짧은 트랜잭션* — DB 갱신
    orderService.markPaid(order.getId(), pay);
  } catch (Exception e) {
    // 4. *보상* — 주문 취소
    orderService.cancel(order.getId());
    // 5. *결제 *환불* (있었으면)
    paymentApi.refundIfPossible(order.getId());
    throw e;
  }
}
```

### *원칙*

1. **외부 호출 *전* — *DB 변경 *짧게 commit*
2. **외부 호출 *밖에 두기*
3. **실패 시 *보상* — *대칭 호출*
4. **보상 도 실패 가능 — *알림 + 수동 처리 큐* 포함

---

## 9. **멱등성 (Idempotency)** — *Rollback 의 *안전망*

### *멱등성 의 *정의*

> *같은 *요청 을 *N 번 보내도 *결과 가 *1 번 보낸 것과 *동일*.*

### *Rollback 과의 *연결*

Saga / 보상 / 재시도 — *모두 *재실행 가능성* 가짐. *멱등성 없으면 *중복 처리*.

```java
// ❌ 비-멱등 — 재시도 마다 *증가*
public void incrementCounter(Long id) {
  counter.increment(id);
}

// ✅ 멱등 — *idempotency key 검증*
public void process(String requestId, Long amount) {
  if (processedRequests.contains(requestId)) {
    return;  // *이미 처리*
  }
  process(...);
  processedRequests.add(requestId);
}
```

### *멱등성 구현 패턴*

1. **Idempotency Key** — *요청 마다 *고유 key + DB UNIQUE 제약*
2. **상태 머신** — *PENDING → PAID 만 허용*, *PAID → PAID 무시*
3. **Versioning** — *낙관적 락 의 응용*
4. **Set / Map 저장** — *처리한 요청 *기록*

→ *멱등성 의 *유무* 가 *재시도 가능 시스템 의 *결정* 적 *조건*.

---

## 10. *현장 *경험* — *7 가지 *오답*

### 10.1. *Checked exception 무시*

`IOException` 던졌는데 *rollback 안 됨*. *부분 commit + 로그 만*. **`rollbackFor = Exception.class`** 로 해결.

### 10.2. *try / catch 로 *swallow*

```java
@Transactional
public void p() {
  try { ... } catch (Exception e) { log.error(e); }
  // *예외 *덮임* → commit
}
```

해결 — *예외 *re-throw* 또는 *setRollbackOnly()*.

### 10.3. *NESTED 의 *Hibernate 호환 문제*

```java
@Transactional(propagation = NESTED)  // Hibernate + MySQL 환경
```

*flush 시점 의 *예외 가 *Savepoint 못 잡음*. **Saga 로 *재 작성*** 후 *해결*.

### 10.4. *결제 API 가 *트랜잭션 안*

*결제 *완료 후 DB 저장 *실패* → *환불 *못 함*. **외부 호출 *밖* + 보상 트랜잭션** 으로 해결.

### 10.5. *Outbox 없는 *이벤트 발행*

*DB commit + Kafka publish 가 *별 도*. *publish 실패 시 *DB 와 *이벤트 불일치*. **Outbox + 재시도 publisher 로 *원자성**.

### 10.6. *멱등성 없는 *재시도*

*Saga 의 *보상 트랜잭션* 이 *재시도 중* — *2 번 *환불*. **Idempotency key 추가** 로 해결.

### 10.7. *부분 *rollback 의 *흔적 안 남김*

*rollback 후 *왜 *되었는지 *추적 불가*. **감사 (audit) 테이블 + 알림** 추가.

---

## 11. **흔한 함정 7 개**

1. ***Checked exception 의 *기본 commit 동작 *모름***.
2. ***try / catch 로 *예외 swallow***.
3. ***Service 안의 *자기 호출 (self-invocation)*** — @Transactional 적용 안 됨.
4. ***외부 호출 트랜잭션 *안*** — 환불 불가능.
5. ***Saga 보상 의 *멱등성 부재*** — 중복 처리.
6. ***NESTED 의 *DB / ORM 호환 부족***.
7. ***Rollback 후 *알림 / 감사 없음*** — 디버깅 지옥.

---

## 12. *결정 가이드*

```
□ 단일 DB / 단일 서비스    → @Transactional + rollbackFor
□ 일부 commit 보존        → setRollbackOnly() / noRollbackFor
□ 부분 rollback           → Savepoint / NESTED (제약 주의)
□ 외부 호출 동반          → 트랜잭션 *밖* + 보상
□ 분산 시스템              → Saga (Choreography or Orchestration)
□ DB + 이벤트 원자성       → Outbox 패턴
□ 재시도 가능 시스템        → Idempotency 필수
```

이 *7 결정* 으로 *대부분 시나리오 *커버*.

---

## 13. 마치며

> *Rollback 의 *깊이 = *시스템 의 *완성도*. *문제 시 *조용히 *원복 되는 시스템* 이 *진짜 *신뢰 받는 시스템*.

3 줄 요약 :

1. **단일 DB 는 *@Transactional + rollbackFor***. 거의 *상수*.
2. **외부 호출 / 분산 시스템 은 *Saga + 보상 + 멱등성***. *DB rollback 으로는 불가능*.
3. ***Outbox 패턴 으로 *DB ↔ 메시지 *원자성*** — *eventual consistency 의 *표준*.

9년 차 회고 :

> *"commit 코드 는 *모두가 *짠다*. Rollback 코드 가 *시니어 의 *서명*."*

다음 글 — *Saga 의 *깊이* — Choreography / Orchestration / Workflow Engine 의 *실제 구현 패턴*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *9년차 백엔드 운영 회고*. *Spring / JPA 중심* 이지만 *원칙* 은 *언어 / 프레임워크 *무관*. *분산 시스템 의 *rollback* 은 *완벽한 답 이 *없는 영역* — *trade-off 의 *지속 적 *결정*.
