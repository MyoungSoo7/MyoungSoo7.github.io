---
layout: post
title: "자바 동시성 총정리 그리고 실전 — 재고 예약은 왜 synchronized로 풀지 않는가"
date: 2026-07-14 10:00:00 +0900
categories: [backend, java, concurrency]
tags: [java, concurrency, race-condition, synchronized, volatile, atomic, lock, executorservice, completablefuture, concurrenthashmap, deadlock, msa, saga]
---

동시성은 "여러 일이 동시에 일어난다"는 낭만이 아니라, **여러 스레드가 같은 자원을 건드릴 때 프로그램이 조용히 틀린 답을 낸다**는 현실이다. 이 글은 자바 동시성의 핵심 도구 10개를 문제 → 해결도구 → 실행 프레임워크 순으로 정리하고, 마지막에 실제 MSA 프로젝트(`inventory-msa`)의 **재고 예약** 코드로 "그래서 실무에선 어떤 도구를 고르는가"를 보여준다.

미리 결론 한 줄:

> 단일 서버에서는 `synchronized`가 정답이지만, 확장 가능한 서비스에서 재고 정합성의 최종 방어선은 **DB의 원자적 UPDATE**다. 락을 애플리케이션이 아니라 DB로 내리는 것 — 이게 이 글의 심장이다.

---

## 1. 문제 현상 — 왜 어려운가

### Race Condition (경쟁 상태)

여러 스레드가 공유 자원을 동시에 읽고 쓸 때, **실행 순서(interleaving)에 따라 결과가 달라지는** 버그다. 가장 흔한 함정은 `count++`가 원자적으로 보이지만 사실은 세 단계라는 점이다.

```
count++  ==  (1) count 읽기 → (2) +1 → (3) 다시 쓰기
```

두 스레드가 (1)에서 같은 값 `10`을 읽으면, 둘 다 `11`을 쓴다. `+1`이 두 번 일어났는데 결과는 `11`. 1000번 증가시켰는데 987이 나오는 그 현상이다.

### Deadlock (교착 상태)

두 스레드가 **서로가 쥐고 있는 락을 기다리며** 영원히 멈추는 상황.

```
스레드 A: lock1 획득 → lock2 대기
스레드 B: lock2 획득 → lock1 대기
→ 둘 다 영원히 대기
```

예방의 정석은 **락 획득 순서를 전역적으로 통일**하는 것(항상 lock1 → lock2 순서로만 잡기), 그리고 `tryLock(timeout)`으로 일정 시간 못 잡으면 포기하고 재시도하는 것이다.

---

## 2. 동기화 도구 — 가벼움에서 무거움 순으로

### volatile — 가시성(visibility)만

한 스레드가 바꾼 값을 다른 스레드가 **즉시 보게** 한다. 변수를 CPU 캐시가 아니라 메인 메모리에서 직접 읽고 쓰게 만들기 때문이다.

```java
private volatile boolean running = true;   // 다른 스레드가 false로 바꾸면 즉시 반영
```

**주의: 원자성은 보장하지 않는다.** `volatile int count; count++`는 여전히 깨진다(읽기-수정-쓰기 3단계가 쪼개지므로). `volatile`은 `running` 같은 **단순 상태 플래그**에만 적합하다.

### synchronized — 가시성 + 원자성

한 번에 **한 스레드만** 임계 영역에 진입하도록 상호 배제(mutual exclusion)한다. 가시성과 원자성을 동시에 보장한다.

```java
synchronized (lock) {
    count++;                // 이제 안전
}
```

간단하고 강력하지만, 블로킹 방식이라 **경합이 심하면 느리다**(대기 스레드가 쌓인다).

### Atomic 클래스 — 락 없는 원자 연산

`AtomicInteger`, `AtomicLong`, `AtomicReference`는 **CAS(Compare-And-Swap)** 라는 하드웨어 명령으로 락 없이 원자 연산을 한다. "예상값이 여전히 X면 Y로 바꾸고, 아니면 실패 후 재시도"를 CPU가 원자적으로 처리한다.

```java
AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet();               // 락 없이 안전한 ++
counter.compareAndSet(expect, update);   // CAS
```

경합이 아주 심하지 않은 카운터/누적기에서는 `synchronized`보다 빠르다(lock-free).

### Lock — 유연한 synchronized

`ReentrantLock`, `ReadWriteLock`은 `synchronized`가 못 하는 것을 준다: **타임아웃(`tryLock`), 인터럽트 가능 대기, 공정성(fairness), 조건 변수(`Condition`)**.

```java
lock.lock();
try {
    // 임계 영역
} finally {
    lock.unlock();          // 반드시 finally에서 해제
}
```

`ReadWriteLock`은 **읽기는 여러 스레드 동시 허용, 쓰기만 배타적**이라 읽기가 압도적으로 많은 자원에서 처리량이 좋다.

---

## 3. 동시성 컬렉션 — ConcurrentHashMap

멀티스레드에서 안전한 `HashMap`이다. 옛날 `Hashtable`이나 `Collections.synchronizedMap`은 맵 전체에 락을 걸어 느렸지만, `ConcurrentHashMap`은 **버킷(bin) 단위로만 잠금**(Java 8+에서는 CAS + 부분 `synchronized`)이라 동시성이 훨씬 높다.

```java
map.putIfAbsent(key, value);              // 원자적
map.compute(key, (k, v) -> (v == null ? 1 : v + 1));   // 원자적 갱신
```

`get(key) == null`을 확인하고 `put`하는 두 줄은 그 사이가 race condition이다. `putIfAbsent`/`compute` 같은 **원자적 복합 연산**을 써야 한다.

---

## 4. 스레드 실행 프레임워크

### Thread Pool — 스레드 재사용

요청마다 `new Thread()`를 만들면 (1) 생성/소멸 비용이 크고 (2) 무제한 생성으로 메모리가 터진다(OOM). 스레드 풀은 **미리 만든 스레드를 재사용**하고 개수를 제한해 자원을 보호한다.

### ExecutorService — 풀을 다루는 표준 API

```java
ExecutorService ex = Executors.newFixedThreadPool(10);
Future<Integer> f = ex.submit(() -> calc());
Integer result = f.get();     // 결과 대기(블로킹)
ex.shutdown();                // 정리
```

실무 팁: `Executors.newFixedThreadPool()`은 내부적으로 **무한 큐**를 써서 작업이 쌓이면 OOM이 날 수 있다. 프로덕션에서는 `ThreadPoolExecutor`를 직접 생성해 **큐 크기와 거부 정책(RejectedExecutionHandler)** 을 명시하는 것이 안전하다.

### CompletableFuture — 비동기 + 조합

`Future`는 `get()`이 블로킹이고 여러 개를 조합할 수 없다. `CompletableFuture`는 **콜백 체이닝과 조합**을 준다.

```java
CompletableFuture
    .supplyAsync(() -> fetchUser(id))      // 비동기 실행
    .thenApply(User::getName)               // 결과 변환
    .thenCompose(name -> fetchOrders(name)) // 다른 비동기 작업 연결
    .thenCombine(otherFuture, (a, b) -> merge(a, b))  // 두 결과 합치기
    .exceptionally(e -> fallback());        // 예외 처리
```

여러 외부 API를 병렬 호출하고 결과를 합쳐야 할 때 강력하다.

---

## 5. 실전 — 재고 예약은 왜 synchronized로 풀지 않는가

이제 실제 MSA 프로젝트의 `inventory-msa`(재고 서비스)를 보자. 주문이 들어오면 재고를 예약(차감)하는데, **재고 10개에 동시 주문 100개**가 몰리는 상황이 핵심이다.

### 순진한 코드의 함정

```java
int cur = repo.find(productId).getAvailable();  // (1) read
if (cur >= qty) {                                // (2) check
    repo.update(productId, cur - qty);           // (3) act
}
```

이 `check-then-act`는 교과서적인 race condition이다. 스레드 100개가 (1)에서 똑같이 `available = 10`을 읽으면 전부 (2)를 통과하고 전부 차감한다 → **오버셀(재고 -90)**.

`synchronized`나 `ReentrantLock`을 걸면 단일 서버에서는 막힌다. 하지만 여기엔 함정이 있다(뒤에서).

### 해법 — DB의 원자적 조건부 UPDATE

`inventory-msa`는 **애플리케이션 락을 전혀 쓰지 않는다.** 대신 조건을 `WHERE`에 넣은 단일 UPDATE로 read-check-write를 DB의 한 번의 원자 연산으로 합친다.

```java
// InventoryRepository.java
@Modifying
@Query("""
        UPDATE Inventory i
           SET i.available = i.available - :qty,
               i.reserved  = i.reserved  + :qty
         WHERE i.productId = :productId
           AND i.available >= :qty
        """)
int reserve(@Param("productId") Long productId, @Param("qty") int qty);
// 반환값: 1 = 예약 성공, 0 = 재고 부족
```

`AND i.available >= :qty` 이 한 줄이 전부다. 동시 요청 100개가 와도 DB가 행(row) 단위 잠금으로 UPDATE를 직렬화하고, `available >= qty` 조건 덕에 **정확히 재고만큼만 1행 영향(성공)** 을 받고 나머지는 **0행(부족)** 이 된다. 재고가 음수가 되는 것을 DB가 원천 차단한다.

서비스 계층은 영향받은 행 수만 보면 된다:

```java
// InventoryService.java
@Transactional
public void reserveForOrder(OrderCreatedEvent event) {
    // ... 멱등성 체크 ...
    for (OrderCreatedEvent.Item item : event.items()) {
        int affected = inventoryRepository.reserve(item.productId(), item.quantity());
        if (affected == 0) {
            // 한 라인이라도 부족 → 예외 → 트랜잭션 전체 롤백(이미 예약한 라인도 원복)
            throw new InsufficientStockException(event.orderId(), item.productId(), item.quantity());
        }
        reservationRepository.save(
                StockReservation.reserved(event.orderId(), item.productId(), item.quantity()));
    }
    kafkaTemplate.send(KafkaTopics.STOCK_RESERVED, ...);
}
```

### 왜 synchronized/Lock이 아니라 DB인가 — MSA의 핵심 인사이트

`synchronized`, `ReentrantLock`, `AtomicInteger`는 모두 **단일 JVM 안에서만** 유효하다. `inventory-msa` 파드가 부하 때문에 3개로 스케일아웃되면, 각 JVM의 락은 서로를 못 본다. 파드 A의 락과 파드 B의 락은 무관하므로 **오버셀이 다시 발생**한다.

```
[Pod A JVM] synchronized ─┐
                          ├─ 서로 못 봄 → 오버셀
[Pod B JVM] synchronized ─┘
[Pod C JVM] synchronized ─┘
                    ▼
              모두가 공유하는 단 하나의 지점
                    = Database
              → 정합성의 최종 방어선은 여기
```

분산 환경에서 정합성의 최종 방어선은 **모든 인스턴스가 공유하는 단일 지점(DB)** 이다. 그래서 동시성 제어를 애플리케이션에서 DB로 내린다. 이것이 로컬 멀티스레딩과 분산 시스템의 결정적 차이다.

> 단일 서버 = `synchronized`/비관적 락으로 충분.
> 수평 확장 가능한 서비스 = DB 레벨 원자성(조건부 UPDATE, 또는 비관적/낙관적 락)이 정답.

### 위에 겹쳐진 방어막

DB 원자성은 오버셀을 막지만, 분산 메시징 환경에는 다른 위협도 있다. `inventory-msa`는 이를 계층으로 방어한다.

- **멱등성(idempotency)** — Kafka는 at-least-once라 같은 이벤트가 재전송될 수 있다. `idempotencyChecker.tryMark(eventId)`로 이미 처리한 이벤트는 skip해 **중복 예약을 방지**한다.
- **원자적 다중 라인(all-or-nothing)** — 주문에 상품이 여러 개일 때, 한 라인이라도 부족하면 `@Transactional`이 롤백해 이미 예약한 라인까지 원복한다.
- **Saga 보상 트랜잭션** — 결제가 실패하면 `release`로 재고를 되돌린다. 이때 `StockReservation`의 상태를 `RESERVED → RELEASED`로 전이시켜 **재고 이중 복원을 방지**한다.

```java
@Transactional
public void releaseForOrder(PaymentFailedEvent event) {
    // ... 멱등성 체크 ...
    for (StockReservation r : reservationRepository.findAllByOrderId(event.orderId())) {
        if (r.release()) {                       // RESERVED → RELEASED (딱 한 번만 true)
            inventoryRepository.release(r.getProductId(), r.getQuantity());
        }
    }
}
```

---

## 6. 한눈 요약 — 언제 무엇을

| 상황 | 도구 |
|---|---|
| 단순 상태 플래그(가시성만) | `volatile` |
| 카운터/숫자 누적 | `AtomicInteger` (CAS) |
| 복합 임계 영역 | `synchronized` / `Lock` |
| 타임아웃·조건변수 등 세밀한 제어 | `ReentrantLock` |
| 읽기 多 쓰기 少 | `ReadWriteLock` |
| 공유 맵 | `ConcurrentHashMap` |
| 작업 실행/재사용 | `ExecutorService` (스레드 풀) |
| 비동기 조합 | `CompletableFuture` |
| Deadlock 예방 | 락 순서 통일 + `tryLock` 타임아웃 |
| **분산 환경 재고/잔액 정합성** | **DB 원자적 UPDATE / 비관적·낙관적 락** |

동시성 도구를 아는 것과 **어디에 무엇을 쓸지 아는 것**은 다르다. `synchronized`를 배우면 모든 걸 `synchronized`로 풀고 싶지만, 수평 확장되는 서비스에서 재고 정합성은 결국 DB로 내려간다. 도구의 유효 범위(단일 JVM vs 분산)를 먼저 묻는 습관 — 그것이 동시성 설계의 시작이다.
