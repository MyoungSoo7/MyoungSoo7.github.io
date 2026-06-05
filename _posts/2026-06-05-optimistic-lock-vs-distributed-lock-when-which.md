---
layout: post
title: "낙관적 락 vs 분산 락 — *언제 어느 것* 을 써야 하나 (Spring + JPA + Redis 실전)"
date: 2026-06-05 16:50:00 +0900
categories: [reflection, concurrency, software-engineering]
tags: [optimistic-lock, distributed-lock, jpa, redis, redisson, concurrency, race-condition, spring-boot, mvcc]
---

"동시성 문제 어떻게 막아요?" 의 첫 답은 거의 항상 *"락 걸어요"*. 그런데 *어떤 락* 이냐가 *그 시스템의 성능 / 안정성 / 비용 을 좌우* 한다.

**낙관적 락 (Optimistic Lock)** 과 **분산 락 (Distributed Lock)** 은 자주 혼동되지만 *완전히 다른 도구*. 같은 *"동시성 제어"* 라는 우산 아래 있지만 *적용 시점·비용·실패 모드* 가 다르다.

본 글은 *두 락의 본질적 차이* 를 정리하고, *Spring + JPA + Redis* 환경에서의 *실전 코드* 와 *언제 어느 것을 써야 하는지* 를 다룬다.

---

## TL;DR

| 차원 | 낙관적 락 | 분산 락 |
|---|---|---|
| **방식** | "충돌 안 일어날 거다 → 일어났으면 retry" | "임계 영역 시작 전에 *진짜* 락 획득" |
| **메커니즘** | 버전 컬럼 (`@Version`) — DB UPDATE 시 검사 | 외부 시스템 (Redis SETNX, Zookeeper, etcd) |
| **충돌 시점** | 트랜잭션 *커밋 직전* (UPDATE) | 임계 영역 *진입 전* |
| **실패 모드** | `OptimisticLockException` → retry | timeout / 다른 인스턴스 보유 → wait or fail |
| **비용** | 낮음 (DB 한 컬럼) | 높음 (외부 시스템 호출 + 네트워크) |
| **적합 상황** | *충돌 빈도 낮음*, 단일 row 갱신 | *충돌 빈도 높음*, *프로세스 간 상호 배제* |
| **부적합 상황** | *충돌 빈도 매우 높음* — retry 폭주 | *단일 인스턴스에서 충분* — 오버킬 |

---

## 0. 같은 문제를 *다른 각도* 에서 보기

### 시나리오: 한정판 상품 *재고 1개* 를 100명이 동시에 주문

```
[ User A ] ─┐
[ User B ] ─┤
[ User C ] ─┼─→ 동시에 → POST /orders { sku: "limited", qty: 1 }
[ ...     ] ─┤
[ User Z ] ─┘
                                ↓
                         재고 1개에 100명 → 누가 살 수 있나?
```

순진한 코드:
```java
public void placeOrder(Order order) {
    Product p = productRepo.findById(order.sku());     // 재고 = 1
    if (p.getStock() < order.qty()) throw new SoldOut();
    p.decreaseStock(order.qty());                       // 재고 = 0
    productRepo.save(p);
    orderRepo.save(order);
}
```

문제: *100 개 트랜잭션이 동시에 `findById`* → 다 *재고 = 1* 로 봄 → 다 통과 → *실제론 100 개 팔림*. 재고 -99. *과매도 사고*.

해결책의 *두 갈래*:
- **낙관적 락** — *"동시 변경이 드물 거다"* 가정. 실제 충돌 발생하면 *retry*
- **분산 락** — *"동시 변경이 잦다"* 가정. *임계 영역을 직렬화*

---

## 1. 낙관적 락 (Optimistic Lock)

### 메커니즘 — *Version 컬럼*

```
orders 테이블
┌──────┬─────────┬────────┬─────────┐
│ id   │ status  │ amount │ version │
├──────┼─────────┼────────┼─────────┤
│ ORD1 │ PENDING │ 10000  │    3    │
└──────┴─────────┴────────┴─────────┘

[ Tx A ]                            [ Tx B ]
SELECT * WHERE id=ORD1              SELECT * WHERE id=ORD1
→ version=3                          → version=3
UPDATE ... WHERE id=ORD1            UPDATE ... WHERE id=ORD1
        AND version=3                       AND version=3
→ 1 row updated, version → 4         → 0 rows updated ❌
                                     → OptimisticLockException
                                     → retry (다시 SELECT, version=4)
```

UPDATE 의 WHERE 절에 *version 조건* 을 넣음. 다른 Tx 가 먼저 커밋했으면 *version 이 바뀌어서 0 rows* → JPA 가 예외 던짐.

### JPA 예시

```java
@Entity
@Table(name = "products")
public class Product {

    @Id
    private String sku;

    private int stock;

    @Version              // ← JPA 가 알아서 version 컬럼 관리
    private Long version;

    public void decreaseStock(int qty) {
        if (this.stock < qty) {
            throw new OutOfStockException(sku);
        }
        this.stock -= qty;
    }
}
```

서비스 코드 (with retry):
```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final ProductRepository productRepo;
    private final OrderRepository orderRepo;

    @Retryable(
        retryFor = ObjectOptimisticLockingFailureException.class,
        maxAttempts = 5,
        backoff = @Backoff(delay = 50, multiplier = 1.5)
    )
    @Transactional
    public OrderId placeOrder(PlaceOrderCommand cmd) {
        var product = productRepo.findById(cmd.sku())
            .orElseThrow(() -> new ProductNotFoundException(cmd.sku()));

        product.decreaseStock(cmd.qty());
        // productRepo.save(product); ← JPA dirty-checking 으로 자동 UPDATE

        var order = Order.place(cmd.userId(), cmd.sku(), cmd.qty());
        return orderRepo.save(order).getId();
    }
}
```

Spring 의 `@Retryable` 이 *예외 발생 시 자동 재시도*. 5회까지, 50ms → 75ms → 112ms 지수 backoff.

### 언제 *적합* 한가
- *충돌 빈도가 낮음* — 100 개 동시 트랜잭션 중 *충돌 1~2개* 정도면 retry 비용 < 락 획득 비용
- *한 row 갱신* 위주 — 다중 row 분산 락 필요시 복잡
- *읽기가 압도적으로 많은* 워크로드 — 쓰기 시 충돌 거의 없음
- *MVCC* 가 잘 굴러가는 DB (PostgreSQL, MySQL InnoDB)

### 언제 *부적합* 한가
- *충돌 빈도 매우 높음* — 한정판 1개에 100명 → *retry 100번 폭주 → DB 부하 폭증*
- *짧은 임계 영역이라도 *반드시* 한 번만 실행* 되어야 하는 케이스 (예: 결제 차감)
- *프로세스 외부 자원* 락 — DB row 가 아닌 *파일·외부 API 호출 빈도 제한* 등

### 실패 시 동작
```
OptimisticLockException → @Retryable retry
                       → 5회 후에도 실패 → @Recover 핸들러
                       → 비즈니스 에러 응답 (429 / 503)
                       → 사용자 재시도
```

---

## 2. 분산 락 (Distributed Lock)

### 메커니즘 — *외부 시스템에서 토큰 발급*

```
[ Pod A ]                  [ Redis ]                  [ Pod B ]
   │                          │                          │
   ├─ SET lock:product:LIM-1 ─→│                          │
   │      uuid-A EX 10 NX     │                          │
   │←──── OK (취득) ──────────┤                          │
   │                          │                          │
   │  (임계 영역 작업)         │                          │
   │  - 재고 차감              │                          │
   │  - 주문 생성              │                          │
   │                          │←─ SET lock:product:LIM-1 ┤
   │                          │      uuid-B EX 10 NX     │
   │                          ├──── nil (실패) ─────────→│
   │                          │                          │  ← 대기 / retry
   ├─ DEL lock:product:LIM-1 ─→│                          │
   │      (uuid-A 확인)        │                          │
   │←──── OK ────────────────┤                          │
                              │                          │
                              │←─ SET lock:product:LIM-1 ┤  (재시도)
                              │←─── OK ──────────────────│
```

핵심:
- `SET ... NX` (Not Exists) — 키 없을 때만 SET → *원자적 락 획득*
- `EX 10` — 10초 후 자동 만료 → *holder 가 죽어도 deadlock 안 됨*
- `uuid-A` — *내가 건 락만 내가 풀 수 있게* 토큰 검증

### Redisson 예시

Redisson 라이브러리가 *Lua 스크립트* 로 위 모든 걸 캡슐화:

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final RedissonClient redisson;
    private final ProductRepository productRepo;
    private final OrderRepository orderRepo;

    @Transactional
    public OrderId placeOrder(PlaceOrderCommand cmd) {
        RLock lock = redisson.getLock("product:" + cmd.sku());

        boolean acquired;
        try {
            acquired = lock.tryLock(3, 10, TimeUnit.SECONDS);
            // 3초 안에 락 획득 시도, 획득 후 10초 후 자동 해제
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ConcurrencyException("Interrupted waiting for lock", e);
        }

        if (!acquired) {
            throw new ConcurrencyException("Failed to acquire lock for " + cmd.sku());
        }

        try {
            var product = productRepo.findById(cmd.sku())
                .orElseThrow(() -> new ProductNotFoundException(cmd.sku()));

            product.decreaseStock(cmd.qty());

            var order = Order.place(cmd.userId(), cmd.sku(), cmd.qty());
            return orderRepo.save(order).getId();
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

### 언제 *적합* 한가
- *충돌 빈도 매우 높음* — 한정판 / 핫이슈 상품
- *여러 인스턴스 (Pod)* 가 동시에 같은 자원 건드림
- *DB 외부 자원* — 외부 API 호출 rate limit, 파일 쓰기, 큐 처리
- *반드시 한 번만 실행* 보장이 필요

### 언제 *부적합* 한가
- *충돌 빈도 낮음* — 락 획득·해제 비용이 *대부분 낭비*
- *짧은 임계 영역* — 락 비용 (네트워크 RTT ~1ms) > 작업 비용
- *Redis 가용성이 시스템 SLA 보다 낮음* — 락 시스템이 *주 시스템보다 자주 죽음* 안 됨

### 실패 시 동작
```
tryLock(3, 10) 3초 후 timeout
    → 다른 holder 가 *오래 점유* 중
    → 비즈니스 에러 (HTTP 503 Service Unavailable)
    → 사용자 재시도 또는 큐잉

락 holder 가 *작업 중 죽음*
    → 10초 후 키 자동 만료
    → 다음 요청이 락 획득 가능 (단, *작업이 부분만 완료* 됐을 위험)
```

### Redisson 의 *추가 기능*
- **Watchdog**: 자동 락 연장 (작업이 expire 시간보다 오래 걸려도 안전)
- **Fair lock**: FIFO 순서 보장
- **Read/Write lock**: 다중 reader 허용
- **Semaphore**: N개 동시 점유 허용 (rate limit)
- **CountDownLatch**: 분산 동기화

---

## 3. *그 외* 분산 락 옵션

### 3.1 Zookeeper (Curator)
- *강한 일관성* 보장 (ZAB consensus)
- *세션 기반* — Pod 죽으면 세션 끊기고 락 자동 해제
- Watcher 로 *대기 줄 알림*
- 단점: *운영 부담* 큼 (Zookeeper 클러스터 별도)

### 3.2 etcd
- Kubernetes 가 *내부적으로* 쓰는 강한 일관성 KV
- Lease 기반 (TTL + renew)
- 적합: K8s 환경에서 *추가 인프라 없이* 쓸 수 있음

### 3.3 PostgreSQL Advisory Lock
- DB *함수 호출* 로 락 획득 — `pg_try_advisory_lock(key)`
- 별도 인프라 없음, *DB 트랜잭션과 자연 통합*
- 단점: *DB 부하* — 락 풀 고갈 위험
- 적합: *DB 이미 있고* 추가 인프라 안 늘리고 싶을 때

```sql
SELECT pg_try_advisory_xact_lock(hashtext('product:LIM-1'));
-- ↑ 트랜잭션 종료 시 자동 해제
```

### 3.4 데이터베이스 *비관적 락 (Pessimistic Lock)*
- `SELECT ... FOR UPDATE` — 행 직접 잠금
- JPA: `@Lock(LockModeType.PESSIMISTIC_WRITE)`
- *DB 안에서만* 보장 → 다른 시스템이 같은 row 건드리면 의미 없음

```java
@Repository
public interface ProductRepository extends JpaRepository<Product, String> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT p FROM Product p WHERE p.sku = :sku")
    Optional<Product> findByIdForUpdate(String sku);
}
```

비관적 락은 *DB 안에서의 분산 락* 이라고 볼 수 있음 — 같은 DB 를 쓰는 모든 Pod 에 효과.

---

## 4. *언제 어느 것* — 결정 가이드

```
시작
   │
   ├── 동시 충돌이 *드문* 가? (월 1~10건 미만)
   │      → ✅ 낙관적 락 (@Version + @Retryable)
   │
   ├── 같은 DB row 만 잠그면 되나?
   │      ├── 충돌 빈도 *중간* (분당 5~50 건)
   │      │      → ✅ 비관적 락 (SELECT FOR UPDATE)
   │      │
   │      └── 충돌 빈도 *높음* (초당 100+ 건)
   │              → ✅ 분산 락 (Redisson)
   │
   ├── DB 외부 자원 (API rate limit / 파일 / 큐) 잠가야 하나?
   │      → ✅ 분산 락 (Redisson / Zookeeper)
   │
   └── K8s 환경 + 추가 인프라 없이?
          → ✅ etcd 또는 PostgreSQL Advisory Lock
```

### 정량 가이드
| 충돌 빈도 (분당) | 권장 |
|---|---|
| < 1 | @Version (낙관적) — retry 거의 없음 |
| 1 ~ 10 | @Version + retry (5회) |
| 10 ~ 100 | 비관적 락 (SELECT FOR UPDATE) |
| 100 ~ 1000 | 분산 락 (Redisson) |
| > 1000 | *큐잉으로 직렬화* (Kafka topic + 단일 consumer) |

---

## 5. 실전 — *결제 정산* 도메인 예시

settlement 시스템에서 *PG 응답 colback 동시 처리* 문제:

### 시나리오
- 결제 PG 가 *callback 을 2번* 보냄 (네트워크 retry)
- 동시에 2개 Pod 가 callback 수신
- 같은 결제건의 *정산 INSERT* 가 *2번* 실행될 위험

### Layer 1: 분산 락 (Redisson)
*프로세스 간 진입 제어*:
```java
@Transactional
public void handlePaymentCallback(PaymentCallback cb) {
    RLock lock = redisson.getLock("settlement:" + cb.paymentId());
    if (!lock.tryLock(2, 30, TimeUnit.SECONDS)) {
        throw new ConcurrentCallbackException(cb.paymentId());
    }
    try {
        // 정산 로직
        settlementService.createFromCallback(cb);
    } finally {
        lock.unlock();
    }
}
```

### Layer 2: 도메인 UNIQUE 제약 (최종 방어)
```sql
ALTER TABLE settlements ADD CONSTRAINT uk_settlements_payment_id UNIQUE (payment_id);
```
Layer 1 락이 *어떤 이유로* 뚫려도 DB 가 *INSERT 거절*.

### Layer 3: 낙관적 락 (@Version) on Payment
*결제 상태 전이* 자체:
```java
@Entity
public class Payment {
    @Id private String id;
    private PaymentStatus status;
    @Version private Long version;
}
```
같은 결제건의 *상태를 동시에* 바꾸려는 시도 — DB 가 거절.

**3중 방어**:
- 분산 락 = *프로세스 진입* 제어
- @Version = *동일 row 동시 갱신* 차단
- UNIQUE = *최종 데이터 무결성*

각각 *다른 종류의 실패* 를 막음.

---

## 6. *흔한 함정* 6종

### 6.1 *분산 락 안에서 외부 호출*
```java
lock.tryLock(...);
try {
    callExternalPayment(...);  // ← 5초 걸리는 외부 API
} finally { lock.unlock(); }
```
*락을 5초 동안 잡고 있음*. 다른 요청들 *전부 대기*. → 락 *바깥에서* 외부 호출하고, *짧은 DB 작업만* 락 안에서.

### 6.2 *낙관적 락 retry 무한*
```java
@Retryable(maxAttempts = Integer.MAX_VALUE)  // ❌
```
충돌 폭주 시 *영원히 retry* → CPU 100%. *반드시 max + recovery* 핸들러.

### 6.3 *분산 락 timeout 안 줌*
```java
lock.lock();  // ❌ 무한 대기
```
다른 holder 가 죽으면 *영원히 멈춤*. 항상 `tryLock(timeout, ...)`.

### 6.4 *expire 없는 분산 락*
```redis
SET lock:x token  # ❌ EX 없음
```
holder 가 *kill -9* → 영원히 키 남음 → *deadlock*. *반드시 EX*.

### 6.5 *남의 락 풀기*
```java
redis.del("lock:x");  // ❌ 내가 안 잡은 락도 풀림
```
*Lua 스크립트* 로 *토큰 검증 후 DEL*:
```lua
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```
Redisson 은 *내부적으로 이 패턴 사용*.

### 6.6 *낙관적 락에서 retry 시 *조건 재평가 안 함**
```java
@Retryable
@Transactional
public void apply() {
    var p = productRepo.findById(id);
    if (p.getStock() < 1) throw new SoldOut();  // 첫 호출에선 통과
    p.decreaseStock(1);  // 충돌 → retry
    // ← retry 시에도 *반드시 findById 다시* — 새 트랜잭션이라 자동 됨, 하지만 *if 검사도 재실행*
}
```
@Transactional + @Retryable 조합에서 *조건 검사 빼먹지 말 것*. retry 마다 *새 트랜잭션* 이므로 조건이 다시 검사돼야 함.

---

## 7. 성능 비교 (대략)

| 락 | RTT | TPS (단일 키) | 비고 |
|---|---|---|---|
| 낙관적 (@Version) | 0 (DB 한 번) | 수천 | 충돌 0 가정 |
| 낙관적 (충돌 50%) | DB 2번 (retry) | 수백 | retry 비용 |
| 비관적 (FOR UPDATE) | DB 한 번 (락 + UPDATE) | 수백 | DB 락 직렬화 |
| Redisson (단일 노드) | ~1ms | 수만 | 메모리 빠름 |
| Redisson (sentinel) | ~2ms | 수만 | 약간 느림 |
| Zookeeper | ~5ms | 수천 | 강한 일관성 비용 |
| etcd | ~3ms | 수천 | RAFT 비용 |
| PG Advisory | 0 (DB 한 번) | 수천 | DB 부하 |

> **숫자는 워크로드/장비/네트워크에 따라 크게 다름. 본인 환경에서 *측정* 필수.**

---

## 8. 결론 — *5가지 원칙*

### 1. 두 락은 *완전히 다른 도구*
- 낙관적 = *충돌 드물다 가정 + retry*
- 분산 = *임계 영역 직렬화 + 진입 제어*
- *섞어 쓰는 게 정답일 때가 많음* (위 6번 settlement 예시)

### 2. *측정 후 결정*
충돌 빈도를 *모르고* 락 종류 결정 → 거의 항상 *과공학 또는 과소공학*. *프로덕션 메트릭* 으로 측정 (분당 OptimisticLockException 개수 등).

### 3. *가장 가벼운 도구* 부터
- @Version 으로 충분하면 거기서 멈춤
- 충돌 폭주 시 → 비관적 락 또는 분산 락 도입
- *처음부터 Redisson 도입* 하지 말 것 — 운영 비용 추가

### 4. *분산 락의 진짜 비용은 *Redis 의존성**
- Redis 다운 = 비즈니스 전체 정지
- *Redis HA 설계* 까지 *함께* 와야 함
- 못 할 거면 DB Advisory Lock 이 *현실적 대안*

### 5. *Defense in depth*
중요 비즈니스 (결제·정산·재고) 는 *반드시* 다중 방어:
- 분산 락 (프로세스)
- @Version (동시 갱신)
- DB UNIQUE 제약 (최종)

한 단이 뚫려도 다음 단이 막음. settlement 도메인의 *교과서 패턴*.

---

## 마무리 — *"락 걸어요" 의 진짜 의미*

신입 시절엔 *"동시성 = synchronized"*. 시니어가 되면 *"동시성 = 시스템의 어느 *경계* 에서 직렬화할 것인가"* 의 *설계 문제*. JVM 안인지 (`synchronized`), DB 안인지 (`@Version` / `FOR UPDATE`), 클러스터 전체인지 (Redisson) — *경계의 크기 가 비용을 결정* 한다.

작게 시작해서 *필요할 때만* 큰 도구로. 그게 *돈과 시간을 아끼는 분산 시스템 설계의 본질*.

다음 글에선 *Redis 분산 락 의 *5가지 알려진 함정* — Martin Kleppmann 의 *Redlock 비판* 부터 *fencing token* 까지 — 을 정리할 예정.
