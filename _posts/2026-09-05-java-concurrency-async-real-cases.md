---
layout: post
title: "Java 동시성과 비동기 프로그래밍의 실제 사례"
date: 2026-09-05 19:31:56 +0900
categories: [Java]
tags: [Java, 동시성, 비동기, CompletableFuture, ExecutorService, VirtualThreads, Spring]
---

# Java 동시성과 비동기 프로그래밍의 실제 사례

온라인 주문, 결제, 알림, 검색, 파일 처리, 외부 API 연동은 한 요청 안에서 여러 작업이 동시에 발생한다. 이때 “동시성(concurrency)”과 “비동기(asynchronous)”를 구분하지 않으면 스레드 풀 고갈, 중복 처리, race condition, timeout 전파 실패 같은 문제가 생긴다.

Java의 동시성은 단순히 스레드를 여러 개 만드는 기술이 아니다. 공유 상태를 안전하게 다루고, 작업의 실행 자원과 완료 시점을 설계하며, 실패·취소·종료까지 관리하는 애플리케이션 구조다. Oracle의 Java 동시성 튜토리얼은 스레드, 동기화, intrinsic lock, executor, thread pool, concurrent collection, atomic variable 등을 별도의 설계 주제로 다룬다.[1]

이 글은 Java 21 기준으로 다음 질문에 답한다.

- 동시성과 비동기는 어떻게 다른가?
- 어떤 실제 업무에 어떤 방식을 적용하는가?
- `synchronized`, `Lock`, `ExecutorService`, `CompletableFuture`, virtual thread를 언제 쓰는가?
- 비동기 코드는 어떻게 timeout·실패·중복·종료를 통제하는가?

## 1. 동시성과 비동기의 차이

### 동시성

동시성은 여러 작업이 겹치는 시간 구간에서 진행될 수 있도록 프로그램을 구성하는 방식이다. 실제로 CPU 코어에서 완전히 동시에 실행되는 병렬성(parallelism)과는 다르다. 한 코어에서도 여러 작업을 번갈아 진행하면 동시성이 만들어진다.

예를 들어 주문 요청 처리 중 재고 조회, 쿠폰 검증, 배송비 계산을 각각 독립적인 작업으로 나누는 것은 동시성 설계다.

### 비동기

비동기는 작업을 시작한 호출자가 결과를 기다리며 즉시 멈추지 않는 실행 모델이다. 작업의 완료 결과는 나중에 callback, `Future`, `CompletionStage`, 메시지 이벤트 등으로 전달된다.

즉, 동시성은 여러 작업을 다루는 구조이고, 비동기는 호출자와 완료 시점의 관계다. 비동기라고 해서 반드시 여러 스레드가 필요한 것은 아니며, 동시성을 사용한다고 해서 항상 비동기 API를 노출해야 하는 것도 아니다.

## 2. 공유 상태의 문제: 재고 차감 사례

다음 코드는 여러 요청이 동시에 실행될 때 문제가 생긴다.

```java
class Inventory {
    private int stock = 1;

    void decrease() {
        if (stock > 0) {
            stock--;
        }
    }
}
```

`stock > 0` 확인과 `stock--` 사이에 다른 스레드가 끼어들 수 있기 때문이다. 두 요청이 동시에 재고가 있다고 판단하면 초과 판매가 발생할 수 있다.

### synchronized로 보호하기

```java
class Inventory {
    private int stock = 1;

    synchronized boolean decrease() {
        if (stock == 0) {
            return false;
        }
        stock--;
        return true;
    }
}
```

`synchronized`는 객체의 intrinsic lock을 획득한 스레드만 보호 구역에 들어가도록 한다. lock을 해제한 뒤 같은 lock을 획득한 다른 스레드가 접근하면 happens-before 관계를 통해 가시성도 확보된다.[2]

다만 synchronized 구역 안에서 외부 API 호출이나 오래 걸리는 DB 작업을 실행하면 대기 스레드가 늘어난다. 보호해야 하는 메모리 상태의 변경만 짧게 잠그고, 외부 I/O는 lock 밖으로 분리하는 것이 기본 원칙이다.

### Atomic과 데이터베이스의 역할

단순한 카운터에는 `AtomicInteger`가 적합할 수 있다.

```java
private final AtomicInteger processed = new AtomicInteger();

void markProcessed() {
    processed.incrementAndGet();
}
```

하지만 재고·잔액·중복 결제처럼 여러 데이터의 일관성이 필요한 업무는 JVM 내부 lock만으로 충분하지 않다. 여러 애플리케이션 인스턴스가 동시에 실행되기 때문이다. 이런 경우 DB의 조건부 UPDATE, unique constraint, optimistic/pessimistic lock, idempotency key를 함께 설계해야 한다.

## 3. ExecutorService: 작업 실행을 통제하기

직접 `new Thread()`를 반복해서 만드는 대신 `ExecutorService`로 작업 실행 자원을 관리한다. `ExecutorService`는 작업을 제출하고 `Future`로 진행 상황과 결과를 추적할 수 있으며, `shutdown()`과 `shutdownNow()`로 종료를 관리한다.[5]

```java
try (ExecutorService pool = Executors.newFixedThreadPool(8)) {
    Future<Price> future = pool.submit(() -> pricingClient.calculate(order));
    Price price = future.get(500, TimeUnit.MILLISECONDS);
}
```

실제 사례는 다음과 같다.

- 이미지 썸네일 생성
- 대량 CSV 행 처리
- 상품 검색 색인 생성
- 외부 배송비 API 호출
- 이메일 발송 작업
- 독립적인 보고서 계산

### CPU 작업과 I/O 작업을 분리한다

CPU를 많이 사용하는 이미지 변환이나 암호화는 CPU 코어 수에 가까운 bounded pool이 적절하다. 반면 외부 HTTP·DB 응답을 기다리는 I/O 작업은 대기 시간이 길어 더 많은 동시 작업을 처리할 수 있지만, 외부 시스템의 connection pool과 rate limit을 함께 고려해야 한다.

스레드 수를 무작정 늘리면 처리량이 늘지 않는다. DB connection pool이 20개인데 애플리케이션 스레드만 200개로 늘리면 결국 대기열과 timeout만 커질 수 있다.

## 4. CompletableFuture: 여러 외부 작업 조합하기

`CompletableFuture`는 완료에 따라 후속 함수와 작업을 연결할 수 있는 `Future`이자 `CompletionStage` 구현이다. 비동기 stage를 조합하고 성공·예외·timeout 흐름을 표현할 수 있다.[4]

### 상품 상세 화면 사례

상품 페이지를 열 때 상품 정보, 재고, 추천 상품을 모두 조회한다고 가정한다.

```java
Executor ioPool = Executors.newFixedThreadPool(32);

CompletableFuture<Product> product =
    CompletableFuture.supplyAsync(() -> productClient.get(id), ioPool);

CompletableFuture<Stock> stock =
    CompletableFuture.supplyAsync(() -> inventoryClient.get(id), ioPool);

CompletableFuture<List<Product>> recommendations =
    CompletableFuture.supplyAsync(() -> recommendationClient.get(id), ioPool);

CompletableFuture<ProductPage> page =
    product.thenCombine(stock, ProductPage::withStock)
           .thenCombine(recommendations, ProductPage::withRecommendations)
           .orTimeout(800, TimeUnit.MILLISECONDS);
```

세 조회가 서로 독립적이면 순차 실행보다 전체 대기시간을 줄일 가능성이 있다. 그러나 외부 서비스 세 개가 모두 정상이어야 화면이 완성되는지, 추천이 실패해도 상품 화면을 보여줄 것인지에 따라 조합 방식이 달라진다.

### 부분 실패를 허용하기

```java
CompletableFuture<List<Product>> safeRecommendations =
    recommendations.exceptionally(error -> List.of());
```

추천 목록은 부가 기능이므로 실패하면 빈 목록으로 대체할 수 있다. 반대로 결제 승인이나 재고 확정처럼 핵심 업무는 조용히 기본값으로 대체하면 안 된다. 실패를 사용자에게 반환하거나 재시도·보상 처리 대상으로 보내야 한다.

### 기본 executor의 함정

명시적인 Executor를 전달하지 않는 async 메서드는 기본적으로 `ForkJoinPool.commonPool()`을 사용한다. Oracle API 문서도 이 정책을 명시한다.[4] 블로킹 HTTP나 JDBC 호출을 common pool에 섞으면 다른 작업의 실행을 방해할 수 있으므로, I/O 전용 executor를 명시하는 편이 안전하다.

## 5. 비동기 메시지 처리: 주문과 알림 분리

주문 API가 결제 완료 후 이메일, SMS, 배송 시스템 호출까지 모두 기다리면 사용자의 응답시간이 길어진다. 업무 경계를 분리하면 다음 구조가 가능하다.

```text
주문 API
  ├─ 주문 저장
  ├─ Outbox 이벤트 저장
  └─ 사용자에게 주문 접수 응답
          │
          ▼
     메시지 브로커
       ├─ 이메일 consumer
       ├─ SMS consumer
       └─ 배송 consumer
```

이 방식은 단순한 `CompletableFuture.runAsync()`보다 내구성이 높다. 프로세스가 종료되어도 이벤트가 저장되고, consumer 재처리·acknowledgement·dead-letter queue를 적용할 수 있기 때문이다.

실제 운영에서 확인할 항목:

- 이벤트에 고유 ID를 둔다.
- consumer는 같은 이벤트를 두 번 받아도 안전하게 만든다.
- 처리 성공 전에 ack하지 않는다.
- 실패 횟수와 재시도 간격을 제한한다.
- 영구 실패 이벤트는 DLQ로 보낸다.
- 주문 상태 전이와 외부 부작용의 순서를 명시한다.

## 6. Java 21 virtual thread의 실제 적용

Virtual thread는 OS thread에 직접 묶이지 않는 가벼운 Java thread다. blocking I/O에서 virtual thread가 대기하면 carrier OS thread가 다른 virtual thread 작업에 사용될 수 있다. 따라서 많은 요청이 외부 I/O를 기다리는 고처리량 서버에 적합하다.[3]

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<String> result = executor.submit(() -> httpClient.fetch(url));
    System.out.println(result.get());
}
```

적용하기 좋은 사례:

- 요청마다 하나의 blocking HTTP 호출이 있는 API
- JDBC 호출이 포함된 전통적인 thread-per-request 서비스
- 다수의 독립적인 파일·네트워크 작업
- 코드 구조는 동기식으로 유지하면서 동시 처리량을 높이고 싶은 서버

Virtual thread는 더 빠른 CPU thread가 아니다. Oracle 문서도 속도(latency)가 아니라 규모·처리량(throughput)을 위한 기능이라고 설명한다.[3] CPU 집약 작업을 무한히 virtual thread로 감싸면 CPU 병목이 해결되지 않는다.

또한 synchronized 구역 안에서 오래 걸리는 blocking I/O를 실행하면 pinning이 발생할 수 있다. 짧은 메모리 보호 구역은 괜찮지만, 빈번하고 긴 I/O가 lock 안에 있으면 구조를 바꾸거나 `ReentrantLock`을 검토해야 한다.[3]

## 7. 실제 사례별 선택 기준

### 사례 A: 동시 재고 차감

- 문제: 여러 요청이 같은 재고를 읽고 차감
- 1차 해결: 원자적 DB 조건부 UPDATE 또는 낙관적 락
- 보조 해결: JVM 내부의 짧은 critical section
- 필수 검증: 초과 판매가 없는지 동시성 테스트

### 사례 B: 상품 상세 조회

- 문제: 독립된 여러 외부 API를 순차 호출
- 선택: `CompletableFuture`로 병렬 시작·결과 조합
- 필수: 명시적 I/O executor, timeout, 부분 실패 정책

### 사례 C: 주문 후 알림

- 문제: 메일·SMS 때문에 주문 API가 느려짐
- 선택: Outbox + 메시지 consumer
- 필수: idempotency, 재시도, DLQ, 처리 상태

### 사례 D: 대량 파일 처리

- 문제: 파일 하나가 전체 요청 스레드를 점유
- 선택: bounded executor 또는 작업 큐
- 필수: backpressure, 진행 상태, 취소, 재시작 지점

### 사례 E: 고동시성 I/O 서버

- 문제: 많은 요청이 blocking I/O를 기다림
- 선택: Java 21 virtual thread 또는 비동기 HTTP client
- 필수: DB·외부 API connection limit, timeout, pinning 관측

## 8. 흔한 실패 패턴

### 비동기인데 바로 join하는 코드

```java
var future = CompletableFuture.supplyAsync(this::load);
return future.join();
```

호출자가 즉시 `join()`하면 외부 계약상 동기 호출과 다르지 않다. 내부 병렬 조합이 필요하지 않은데 비동기를 도입하면 복잡성만 늘어난다.

### 공용 풀에 모든 작업을 넣기

CPU 작업, blocking I/O, 긴 배치 작업을 하나의 pool에 섞으면 서로 영향을 준다. 작업 특성별 executor를 분리하고 queue와 rejection 정책을 정해야 한다.

### 예외를 무시하는 fire-and-forget

```java
CompletableFuture.runAsync(() -> sendEmail());
return "OK";
```

이메일이 실패했는데 API가 성공을 반환하고, 예외도 관측되지 않을 수 있다. 반드시 예외 로깅·메트릭·재시도 또는 메시지 기반 처리를 연결해야 한다.

### timeout은 하나만 설정

HTTP client timeout, future timeout, DB query timeout, 메시지 처리 timeout이 서로 다르면 한 계층은 이미 포기했는데 다른 계층은 계속 작업할 수 있다. 전체 deadline을 전파하고, 취소가 실제 downstream 호출까지 전달되는지 확인해야 한다.

### 공유 mutable state를 편리하게 사용

`HashMap`, `ArrayList`, 임의의 singleton cache를 여러 스레드가 수정하면 race condition이 발생한다. 불변 객체, concurrent collection, actor/message passing, DB 원자 연산 등 소유권을 명확히 해야 한다.

## 9. 테스트와 관측

동시성 코드는 정상 테스트 한 번으로 검증되지 않는다.

- 여러 스레드가 같은 상태를 갱신하는 테스트
- barrier로 동일 시점 실행을 유도하는 테스트
- timeout·interrupt·cancel 테스트
- executor queue 포화 테스트
- 외부 API 지연·실패 주입 테스트
- 중복 메시지 재처리 테스트
- 애플리케이션 메트릭과 thread dump 확인
- Java Flight Recorder와 virtual thread pinned event 확인

성공률만 보지 말고 다음 지표를 수집한다.

- active task 수
- queue depth
- task wait time
- task execution time
- rejection count
- timeout·cancel·retry count
- 외부 호출별 latency
- 중복 처리와 DLQ count

## 결론

Java 동시성과 비동기는 “스레드를 많이 쓰는 방법”이 아니다. 핵심은 작업의 독립성, 공유 상태의 소유권, 실행 자원, 완료·실패·취소·재시작의 경계를 명확히 하는 것이다.

- 짧은 공유 상태 보호에는 `synchronized`, atomic, lock을 사용한다.
- 작업 실행량은 `ExecutorService`와 bounded resource로 통제한다.
- 독립적인 외부 호출 조합에는 `CompletableFuture`를 사용한다.
- 내구성이 필요한 후속 작업은 메시지·Outbox로 분리한다.
- blocking I/O가 많은 고동시성 서버에는 virtual thread를 검토한다.
- CPU 작업, DB 연결 수, 외부 rate limit을 무시한 동시성은 성능 개선이 아니라 장애 증폭기가 된다.

좋은 동시성 설계는 빠르게 보이는 코드가 아니라, 부하·실패·중복·종료 상황에서도 결과를 예측할 수 있는 코드다.

## 참고 자료

[1] Oracle Java Concurrency Tutorial — 스레드, 동기화, executor, concurrent API  
[2] Oracle Intrinsic Locks and Synchronization — monitor lock과 happens-before  
[3] Oracle Java 21 Virtual Threads — virtual thread의 구조, 적용 범위, pinning  
[4] Java SE 21 CompletableFuture API — CompletionStage, 비동기 executor, 예외 완료  
[5] Java SE 21 ExecutorService API — 작업 제출, Future, shutdown과 executor lifecycle

## 출처

- Oracle Java Concurrency Tutorial: https://docs.oracle.com/javase/tutorial/essential/concurrency/
- Intrinsic Locks and Synchronization: https://docs.oracle.com/javase/tutorial/essential/concurrency/locksync.html
- Java 21 Virtual Threads: https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html
- CompletableFuture API: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html
- ExecutorService API: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html

## Sources

[1] https://docs.oracle.com/javase/tutorial/essential/concurrency — Oracle Java Concurrency Tutorial
[2] https://docs.oracle.com/javase/tutorial/essential/concurrency/locksync.html — Intrinsic Locks and Synchronization
[3] https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html — Java 21 Virtual Threads
[4] https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html — CompletableFuture Java SE 21
[5] https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html — ExecutorService Java SE 21
