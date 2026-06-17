---
layout: post
title: "*트랜잭션 경계* 의 설정 — *어디서 *시작 하고 *어디서 *끝나는가*"
data: 2026-06-11 19:15:00 +0900
date: 2026-06-11 19:15:00 +0900
categories: [backend, database, architecture]
tags: [transaction, acid, jpa, spring, saga, outbox, distributed, boundary]
---

> *트랜잭션 *은 *모든 백엔드 의 *기본 도구*. *모든 SQL *문 마다 자동 으로 따라온다*.
> 그런데 *경계 가 잘못* 그어지면 — *데드락 / 데이터 부정합 / 느린 응답 / 분산 시스템의 *지옥* 이 *함께 온다*.
> 이 글은 *그 경계를 *어디에 *어떻게 그릴지* 의 *7 년 회고*.

---

## TL;DR

| 함정 | 증상 | 해결 |
|------|------|------|
| **경계 *너무 넓음*** | DB 락 *길게 잡힘*, 데드락 빈발 | *반드시 *짧게 *. 외부 호출 *밖으로* |
| **경계 *너무 좁음*** | *연관 데이터 *부정합*, *부분 commit* | *비즈니스 단위 로 *atomic* |
| **외부 API 가 *트랜잭션 안*** | *3rd party 느림 = DB 연결 점유* | *비동기 / 큐 / Saga* |
| **읽기 만 인데 *쓰기 트랜잭션*** | *불필요한 락 / connection 점유* | *@Transactional(readOnly = true)* |
| **분산 트랜잭션** | *2PC 의 *복잡 + 느림* | *Saga / Outbox / eventual consistency* |

*핵심 한 줄* :

> *트랜잭션 경계는 *비즈니스 *단위* 의 *반영*. *기술 적 편의* 가 *아니라 *도메인 의 *원자성 *요구* 가 *기준*.

---

## 1. *왜 *경계 가 *중요* 한가*

*트랜잭션* 은 *DB 의 *원자성 보증*. 그러나 *공짜 가 *아니다*. *비용* :

- *DB 연결 (connection) 점유*
- *행 / 페이지 / 테이블 *락 (lock)*
- *MVCC 의 *snapshot 유지*
- *Undo 로그 / WAL*
- *Network round-trip*

이 비용 들 이 *경계 가 *길수록 *기하 급수로 증가*. *짧으면 *원자성 깨짐 위험*. **그 사이의 *적정선* 을 *찾는 것이 *경계 설계*.**

---

## 2. *ACID 복습 — *각 글자 의 *의미*

| 글자 | 의미 |
|------|------|
| **Atomicity** | *전부 or *전혀* — 부분 적용 *없음* |
| **Consistency** | 트랜잭션 전 후 *제약 조건 *유지* |
| **Isolation** | *동시 트랜잭션 들 의 *서로 안 보임* |
| **Durability** | *commit 후 *영구 *지속* (장애 시 도) |

경계 설계 에 *가장 직결* 되는 건 ***A (Atomicity)*** 와 ***I (Isolation)***. *atomic 단위 가 *경계의 *최소 *크기*. *isolation level 이 *경계의 *영향 범위*.

---

## 3. **흔한 함정 1 — *경계 가 *너무 *넓음**

### 예 — *최악 의 *코드*

```java
@Transactional
public void placeOrder(OrderRequest req) {
  Order order = orderRepo.save(...);

  // ❌ 외부 API 호출 — *수 초 까지 *느릴 수 있음*
  PaymentResult pay = paymentApi.charge(req.cardNo, req.amount);

  // ❌ 메일 발송 — *느림 + 실패 *가능*
  mailService.send(req.email, "주문 완료");

  // ❌ S3 업로드 — *수 백 ms*
  s3Client.upload(...);

  order.setStatus(PAID);
}
```

### *문제*

- *외부 호출 의 *지연 동안 *DB 락 / 연결 *계속 점유*
- *외부 호출 *실패 면 *DB rollback* — *결제 *완료된 *상태 가 *불일치*
- *외부 호출 *지연 시 *DB connection pool *고갈* → *서비스 다운*

### *해결*

```java
public void placeOrder(OrderRequest req) {
  // 1. *짧은 *트랜잭션 — *DB 변경 만*
  Order order = orderService.create(req);  // @Transactional 내부

  // 2. *밖에서 *외부 호출*
  PaymentResult pay = paymentApi.charge(...);

  // 3. *결과 반영 *다른 *짧은 트랜잭션*
  orderService.markPaid(order.getId(), pay);

  // 4. *부수 효과 *비동기*
  eventPublisher.publish(new OrderCompletedEvent(order));
}
```

**원칙** : *외부 호출 은 *트랜잭션 밖*. *DB 변경 만 *트랜잭션 안*.

---

## 4. **흔한 함정 2 — *경계 가 *너무 *좁음**

### 예 — *부정합 의 *원인*

```java
public void transferMoney(Long fromId, Long toId, BigDecimal amount) {
  // ❌ 두 호출 이 *각자 *트랜잭션*
  accountService.withdraw(fromId, amount);  // tx1 commit
  // *여기서 *서버 죽으면 *돈 사라짐*
  accountService.deposit(toId, amount);     // tx2
}
```

*withdraw 완료 → deposit 전 *서버 다운* — *돈 *공중분해*.

### *해결*

```java
@Transactional
public void transferMoney(Long fromId, Long toId, BigDecimal amount) {
  accountService.withdraw(fromId, amount);
  accountService.deposit(toId, amount);
  // *둘 다 *동일 트랜잭션* — *부분 commit 없음*
}
```

**원칙** : *비즈니스 의 *원자 단위* 가 *트랜잭션 의 *최소* 크기*.

---

## 5. *경계 설정 의 *3 가지 단계*

### 5.1. *비즈니스 *원자성 단위 *식별*

> *이 작업 의 *중간 상태 가 *나타날 수 없다* 라면 *그게 *원자 단위*.*

예 :
- 송금 — *출금 + 입금* 은 *원자*. 분리 불가.
- 주문 — *주문 생성 + 재고 차감* 은 *원자*.
- 결제 처리 — *결제 완료 + 주문 상태 변경* — *경우에 따라 *원자 / 비원자*.

### 5.2. *외부 *의존성 *분리*

> *DB 외 의 *모든 호출* 은 *트랜잭션 밖* 에 두기.*

- 외부 API
- 메일 / SMS / Push
- 파일 / S3 / 이미지 처리
- 다른 마이크로서비스

이 모든 게 *트랜잭션 안* 이면 *느림 + 부정합 위험*. *밖* 으로 빼고 *Outbox / Event 큐* 활용.

### 5.3. *읽기 / 쓰기 *분리*

> *읽기만 *하는 메서드 는 *@Transactional(readOnly = true)*.*

```java
@Transactional(readOnly = true)
public ProductView findProduct(Long id) { ... }
```

장점 :

- *Hibernate 가 *flush 안 함* — 성능 향상
- *Read replica 로 *라우팅 가능*
- *Lock 점유 *최소*

---

## 6. **Spring @Transactional 의 *주의점*

### 6.1. *Self-Invocation 의 함정*

```java
public class OrderService {
  public void process(OrderRequest req) {
    save(req);  // ❌ *@Transactional 안 먹음*
  }

  @Transactional
  public void save(OrderRequest req) { ... }
}
```

*같은 클래스 안 의 *메서드 호출* 은 *프록시 안 거침* → *@Transactional 무시*. *별도 클래스 분리* 또는 *@TransactionalEventListener* 등 *우회 패턴* 필요.

### 6.2. *Propagation*

```
REQUIRED    : 기존 tx 있으면 *참여*, 없으면 *새로*   (default)
REQUIRES_NEW: *항상 새 *tx*  — 기존 tx 일시 정지
NESTED      : *savepoint 로 *중첩*  (rollback 부분 가능)
MANDATORY   : *반드시 기존 *tx 있어야 함*
NOT_SUPPORTED: *tx 없이 실행*
NEVER       : tx 있으면 *예외*
SUPPORTS    : *있으면 참여, 없으면 그냥*
```

대부분 *REQUIRED 가 *정답*. *REQUIRES_NEW* 는 *외부 로깅 / 이벤트 발행* 같은 *부수 효과 가 *부모 rollback 에 *영향 받으면 안 될 때*.

### 6.3. *RuntimeException 만 *rollback*

```java
@Transactional
public void save() {
  try {
    repo.save(...);
  } catch (IOException e) {  // ❌ checked exception — *rollback 안 됨*
    log.error(e);
  }
}
```

기본 동작 : *RuntimeException + Error 만 rollback*. *Checked exception 은 *rollback 안 함*. *@Transactional(rollbackFor = Exception.class)* 로 변경 가능.

---

## 7. *분산 트랜잭션 의 *복잡성*

### *2PC (2-Phase Commit) 의 *옛 *시대*

```
Coordinator → 모든 노드 :  "준비 됐어?"
            ← prepare OK / NO
Coordinator → 모든 노드 :  "Commit!"  또는  "Rollback!"
```

*ACID 보증* — 단 *심각한 단점* :

- *모든 노드 가 *동시에 *살아 있어야* — *partition 위약*
- *Coordinator 다운 = *모든 노드 *blocking*
- *느림* — *네트워크 round-trip *수회*
- *2025 년 *현실에선 *거의 안 쓴다*

### *Saga 패턴 — *현대 의 *답*

> *각 단계 가 *독립 적 *트랜잭션*. *실패 시 *보상 트랜잭션* (compensation)* 실행.

```
주문 생성 (성공)
  → 결제 (성공)
    → 재고 차감 (실패!)
      → 결제 *환불* (보상)
      → 주문 *취소* (보상)
```

### Saga 의 *2 구현 패턴*

1. **Choreography** — *각 서비스 가 *이벤트 발행 / 구독*. 중앙 *조정자 없음*.
2. **Orchestration** — *중앙 *오케스트레이터 (Workflow Engine)* 가 *순서 *결정*. Camunda, Temporal, AWS Step Functions.

### *Outbox 패턴 — *DB + 이벤트 *원자성*

```
1 트랜잭션 :
  - 주문 저장
  - *outbox 테이블에 *이벤트 *insert*

별도 publisher :
  - outbox 의 미발행 이벤트 *읽음*
  - Kafka / RabbitMQ 에 *발행*
  - 발행 성공 시 outbox 표시
```

→ *DB 와 *메시지 의 *원자성 *보장*. *eventual consistency*. *현대 *마이크로서비스 *표준*.

---

## 8. *Read 시 *주의 — *Lock 의 *세부*

### *Pessimistic Lock* vs *Optimistic Lock*

**Pessimistic** :
```sql
SELECT * FROM account WHERE id = 1 FOR UPDATE;
```
*행 *잠금*. *동시 변경 *완전 차단*. *데드락 위험*.

**Optimistic** :
```java
@Version
private Long version;
```
*충돌 시 *예외*. *재시도 로 해결*. *데드락 없음*.

### *어느 걸 쓸지*

```
충돌 가능성 *높음* + 충돌 시 *치명적* → Pessimistic
충돌 가능성 *낮음* + 재시도 *쉽다*    → Optimistic
대부분 시스템                          → Optimistic 우선
```

---

## 9. *실 현장 *경험* — *7 년의 *5 가지 *오답*

### 9.1. *결제 API 가 *@Transactional 안*

*결제 API 가 *3 초 지연* → DB connection pool 30 개 모두 점유 → *전 서비스 다운 *5 분*. **외부 호출 *밖으로* 뺀 후 *해결*.

### 9.2. *Self-Invocation 으로 *트랜잭션 무시*

*동일 클래스 안 *메서드 호출* — *@Transactional 적용 안 됨*. *6 개월 만 에 *데이터 부정합 발견*. **서비스 분리 + Spring 의 *self-reference proxy** 로 해결.

### 9.3. *readOnly 누락*

*조회 메서드 *전부* 가 *write tx*. *Read replica 활용 못 함*. *@Transactional(readOnly = true) *대량 추가* 후 *p99 -40%*.

### 9.4. *NESTED *남용*

*복잡 한 *중첩 트랜잭션* — *savepoint 로 *부분 rollback 시도*. *디버깅 *지옥*. *결국 *Saga 로 *재 작성*.

### 9.5. *대량 처리 의 *단일 트랜잭션*

*100 만 행 처리 가 *1 개 트랜잭션* — *Undo 로그 폭발* + *락 점유*. **배치 분할 (chunk 1000)** 로 해결.

---

## 10. *흔한 안티 패턴* 5 개

1. ***Service 메서드 가 *@Transactional 하나 도 없음** — 데이터 변경 *원자성 없음*.
2. ***Service 메서드 가 *전부 @Transactional** — *읽기 까지 *불필요한 락*.
3. ***Controller 에 *@Transactional*** — *너무 *위 *경계*. *예외 처리 / 응답 변환 도 *트랜잭션 안*.
4. ***외부 API 호출 이 *트랜잭션 안*** — *흔한 *비밀의 *지옥*.
5. ***@Transactional + @Async 함께*** — *프록시 적용 안 되거나 *예측 안 되는 동작*.

---

## 11. *경계 설계 *체크리스트*

코드 작성 시 *체크* :

```
□ 이 메서드 의 *atomic 단위* 가 *명확* 한가?
□ *외부 호출 (HTTP / 메일 / S3 등)* 이 *트랜잭션 밖* 인가?
□ *readOnly = true* 를 활용 했는가?
□ Self-invocation 으로 *@Transactional 우회* 하고 있지 않은가?
□ *rollback 조건* (checked vs unchecked) 이 *명확* 한가?
□ *분산 서비스 간* *eventual consistency* 가 *허용 되는가? Saga 가 *필요한가*?
□ *Outbox 패턴* 으로 *DB + 이벤트 *원자성* 인가?
□ *대량 처리* 는 *배치 분할* 되었는가?
□ *@Async 와 *@Transactional 의 *상호작용* 을 *검토 했는가?
```

이 9 개 만 *매 PR 마다 *체크* 해도 — *대부분 *트랜잭션 사고 *예방*.

---

## 12. *세 줄 *정리*

> *트랜잭션 경계는 *비즈니스 의 *원자성 단위* 의 *반영*. *기술 적 편의* 가 *아닌* *도메인 의 *요구 가 *기준*.

1. ***좁게 *시작*** — *외부 호출 *밖으로*, *읽기 readOnly*, *비즈니스 단위 만 atomic*.
2. ***분산 시점에 *Saga / Outbox 로 *교체*** — *2PC 의 *옛 시대* 끝.
3. ***체크리스트* 로 *습관화*** — *코드 리뷰 시 *9 개 *체크*.

9 년차 회고 :

> *"@Transactional 한 줄 의 *위치 가 *시스템 *수명 을 *결정 한다*."*

다음 글 — *Saga 의 *깊이* — Choreography / Orchestration / 보상 트랜잭션 의 *실제 구현 패턴*. 시리즈 로 이어 집니다.

---

> 본 글은 *9년차 백엔드 운영 회고*. *Spring / JPA 중심* 이지만 *원칙* 은 *모든 ORM / 언어* 에 적용. *트랜잭션 의 *본질* 은 *DB 만큼이나 *비즈니스 분석 능력* — *원자성 단위 *식별* 이 *진짜 의 *경계 설정*.
