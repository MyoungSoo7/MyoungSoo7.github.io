---
layout: post
title: "CompletableFuture 를 본문 3개 파일에만 쓴 이유"
date: 2026-09-01 03:44:41 +0900
categories: [backend, java]
tags: [completablefuture, kafka, outbox, java, spring-boot, concurrency]
---

정산 시스템(`settlement`) 전체에서 `CompletableFuture` 를 `import` 하는 곳은 31군데다.
그중 테스트를 빼면 **본문은 3개 파일**뿐이고, 그 3개는 전부 같은 이음매에 붙어 있다 —
outbox 레코드를 Kafka 로 내보내는 발행 경로.

```
shared-common/.../outbox/application/port/out/PublishExternalEventPort.java
shared-common/.../outbox/adapter/out/event/KafkaOutboxPublisher.java
shared-common/.../outbox/application/service/OutboxBatchEventPublisher.java
```

컨트롤러에도, 도메인 서비스에도 없다. 비동기를 *스타일*로 쓴 게 아니라, 비동기가 아니면
설명이 안 되는 한 지점에만 썼기 때문이다. 이 글은 그 한 지점에서 무엇을 얻었고 무엇이
아직 안 풀렸는지에 대한 기록이다.

## 1. 바꾸기 전: `.get()` 이 프로듀서의 배칭을 껐다

원래 폴러는 한 주기에 claim 한 이벤트를 하나씩 동기 발행했다.

```java
SendResult<String, String> result = kafkaTemplate.send(buildRecord(event))
        .get(SEND_TIMEOUT_SEC, TimeUnit.SECONDS);
```

이 코드 자체는 지금도 `KafkaOutboxPublisher#publish` 에 남아 있다(동기 경로가 필요한
호출자를 위해). 문제는 이걸 100건에 대해 루프로 돌릴 때다. Kafka 프로듀서 문서는 `send()` 의
성질을 이렇게 못박는다 — 호출하면 레코드를 대기 버퍼에 넣고 **즉시 반환**하며, 그래야
프로듀서가 레코드들을 배치로 묶을 수 있다.[^kafkaproducer] 즉 `send()` 직후에 `.get()` 을
붙이면 다음 레코드가 버퍼에 들어오기도 전에 이번 레코드의 브로커 왕복이 끝나기를 기다린다.
묶일 것이 없으니 배칭이 성립하지 않는다. Kafka 4.0 은 `linger.ms` 기본값을 0 에서 5 로
올렸는데,[^linger] 건건이 블로킹하면 그 5ms 의 수확도 통째로 버리는 셈이다.

바뀐 구조는 단순하다. **전부 먼저 던지고, 그다음에 모아 기다린다.**

```java
// 1) 전부 비동기 dispatch — 프로듀서가 in-flight 로 묶어 보낸다.
Map<OutboxEvent, CompletableFuture<Void>> inflight = new LinkedHashMap<>();
for (OutboxEvent event : events) {
    try {
        inflight.put(event, publishExternalEventPort.publishAsync(event));
    } catch (RuntimeException e) {
        inflight.put(event, CompletableFuture.failedFuture(e));
    }
}
```

## 2. 포트의 `default` 메서드 — 실패도 같은 통로로 흐르게

`publishAsync` 는 어댑터가 아니라 **포트**에 기본 구현으로 있다.

```java
default CompletableFuture<Void> publishAsync(OutboxEvent event) {
    try {
        publish(event);
        return CompletableFuture.completedFuture(null);
    } catch (RuntimeException e) {
        return CompletableFuture.failedFuture(e);
    }
}
```

Kafka 어댑터만 진짜 비동기 send 를 돌려주고, 나머지 구현체(예: 로컬
`ApplicationEventPublisher`)는 동기 호출을 이미 완료된 future 로 감싼다. 덕분에 배치 루프에
`if (kafka)` 분기가 하나도 없다. `completedFuture` 는 Java 8, `failedFuture` 는 Java
9 부터의 API다.[^cf]

같은 발상이 위 dispatch 루프의 `catch` 에도 있다. `publishAsync` 가 future 를 돌려주기
*전에* 동기적으로 던지는 경우(직렬화 실패 등)가 있는데, 그걸 `failedFuture` 로 바꿔 넣으면
결과 수거 루프는 예외 채널을 하나만 다루면 된다. 이 동작에는 회귀 테스트가 붙어 있다 —
`"배치: publishAsync 가 동기적으로 던져도 실패로 집계, DLQ 발행 실패는 삼킨다"`.

## 3. `allOf` 를 쓰지 않은 이유: 필요한 건 "끝났다"가 아니라 "누가 실패했나"

여러 future 를 기다린다고 하면 `CompletableFuture.allOf` 가 먼저 떠오른다. 여기서는 못
쓴다. `allOf` 가 돌려주는 future 는 하나라도 예외로 끝나면 그 하나의 예외를
`CompletionException` 에 담아 예외 완료된다.[^allof] "배치가 실패했다"는 알 수 있지만
**100건 중 어느 것이 실패했는지**는 알 수 없다.

정산 outbox 는 정확히 그 정보로 굴러간다. 실패한 이벤트만 `markFailed` 로 `retryCount` 를
올리고, 한계(10회)를 넘겨 `FAILED` 로 전이되는 순간에만 DLQ 로 한 번 보내고, 아직 재시도
여지가 있는 행은 claim 리스를 풀어 다음 주기에 곧바로 다시 잡히게 한다. 그래서 자료구조가
`Map<OutboxEvent, CompletableFuture<Void>>` 다 — 이벤트와 future 의 1:1 대응을 끝까지
들고 간다. `LinkedHashMap` 인 것도 우연이 아니고, claim 순서대로 수거해야 로그와 DB 반영
순서가 읽히기 때문이다.

수거 쪽에서 예외를 푸는 코드는 이렇게 생겼다.

```java
private String awaitError(CompletableFuture<Void> future) {
    try {
        future.get(AWAIT_TIMEOUT_SEC, TimeUnit.SECONDS);
        return null;
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        return "publish interrupted";
    } catch (ExecutionException e) {
        Throwable cause = e.getCause() != null ? e.getCause() : e;
        return cause.getMessage() != null ? cause.getMessage() : cause.toString();
    } catch (TimeoutException e) {
        return "publish timeout after " + AWAIT_TIMEOUT_SEC + "s";
    }
}
```

`getCause()` 로 한 겹 벗기는 건 취향이 아니라 규약이다. `CompletableFuture` 가 예외
완료됐을 때 `get()` 은 `CompletionException` 이 품고 있던 원인을 그대로 담은
`ExecutionException` 을 던진다.[^cf] 벗기지 않으면 `outbox_events.last_error` 에
`java.util.concurrent.ExecutionException` 만 쌓이고 정작 브로커가 뭐라 했는지는 사라진다.
`InterruptedException` 에서 인터럽트 플래그를 복원하는 것도 같은 부류의 규약이다.

## 4. 순서를 지키는 건 `CompletableFuture` 가 아니다

100건을 한꺼번에 in-flight 로 띄우면 자연스럽게 나오는 걱정이 있다. 같은 결제 건의
이벤트 순서가 뒤집히지 않나?

여기서 `CompletableFuture` 는 아무 역할도 하지 않는다. 순서는 **프로듀서 설정**이 지킨다.
`aggregateId`(예: `payment_id`)를 레코드 키로 써서 같은 집합이 같은 파티션에 가게 하고,
그 위에 이 설정이 깔려 있다.

```yaml
producer:
  acks: all
  retries: 5
  properties:
    enable.idempotence: true
    max.in.flight.requests.per.connection: 5
```

Kafka 의 `retries` 설정 문서는 이 조합의 위험을 직접 서술한다 — `enable.idempotence` 가
`false` 인 채로 재시도를 허용하고 `max.in.flight.requests.per.connection` 이 1 보다 크면,
한 파티션으로 보낸 두 배치 중 앞의 것이 실패해 재시도되고 뒤의 것이 성공하면 **뒤의 레코드가
먼저 나타날 수 있다**.[^retries] 멱등 프로듀서를 켜야 그 재정렬이 막힌다. 즉 배치 발행으로
얻은 처리량은 `enable.idempotence: true` 라는 전제 위에서만 안전하다. 코드 리뷰에서
`OutboxBatchEventPublisher` 만 보면 이 전제가 보이지 않는다는 게 이 구조의 함정이다.

## 5. 아직 안 풀린 것 셋

**① 30초 타임아웃은 send 를 취소하지 않는다.** `awaitError` 의 `TimeoutException` 분기는
"기다리다 지쳤다"는 뜻이지 "발행이 취소됐다"는 뜻이 아니다. 프로듀서 쪽 상한인
`delivery.timeout.ms` 의 기본값은 120초로,[^delivery] 우리 30초보다 훨씬 길다. 그 사이
브로커가 늦게 ack 하면 레코드는 결국 전달되는데, 배치는 이미 그 이벤트를 실패로 적고
다음 주기에 다시 보낸다. 결과는 **중복 발행**이다. 이건 버그가 아니라 at-least-once 의
정상 동작이고, 그래서 소비자 쪽 멱등 레이어(`processed_events` 의 `event_id` 기록)가
최종 방어선이다. 발행자만 보고 "중복 없음"을 주장할 수 없다는 뜻이기도 하다.

**② 대기의 최악 경계는 1배가 아니다.** 코드 주석은 "모든 send 가 in-flight 라 N배가 아닌
1배 수준의 벽시계 시간"이라고 적고 있고, 정상 경로에서는 맞다. 다만 `get(30s)` 는 future
*하나마다* 걸리는 타임아웃이고 수거는 순차적이라, 이론적 상한은 여전히 N×30초다. 앞의
future 가 29초를 쓰고 완료되면 다음 future 의 시계는 그때부터 다시 30초다. 실측한 적은
없고 정상 부하에서 관측된 적도 없지만, "1배"는 관측이지 보장이 아니다.

**③ `thenAccept` 는 완료 스레드에서 돈다.** `KafkaOutboxPublisher#publishAsync` 는
send future 에 `thenAccept` 로 로깅을 붙인다. `CompletableFuture` 문서는 비-async
메서드의 의존 동작이 "그 future 를 완료시키는 스레드에서 수행될 수 있다"고 명시한다.[^cf]
Kafka 에서 그 스레드는 프로듀서의 네트워크 I/O 스레드다. 지금은 `log.debug` 한 줄이라
문제가 없지만, 여기에 DB 쓰기나 원격 호출을 넣는 순간 전체 프로듀서의 전송이 그만큼
밀린다. 이 파일에는 그걸 막는 테스트가 없다 — 주석뿐이다.

## 덧: Java 25 인데 왜 여전히 블로킹하나

이 리포는 Java 25 / Spring Boot 4 다. 가상 스레드가 있는데 왜 `get()` 으로 막고 있냐고
물을 수 있다. 답은 **이 개선의 출처가 스레드 비용이 아니었기 때문**이다. 폴러 스레드는
어차피 한 개고, 그게 30초를 자든 말든 시스템 처리량과 무관하다. 느렸던 이유는 스레드가
비싸서가 아니라 `.get()` 이 프로듀서의 배칭 기회를 없앴기 때문이고, 그건 dispatch 와 await
를 분리하는 것만으로 해결됐다. 가상 스레드로 바꿔도 이 코드는 더 빨라지지 않는다.

비동기를 도입할 때 얻는 게 "스레드를 안 막는 것"인지 "아래 계층이 묶어 보낼 기회를 주는
것"인지 구분하지 않으면, 코드만 복잡해지고 숫자는 그대로인 리팩터링이 된다.

## References

- Apache Kafka, [`KafkaProducer` (Kafka 4.0 API)](https://kafka.apache.org/40/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html) — `send()` 의 비동기·배칭 성질, 멱등 프로듀서
- Apache Kafka, [Producer Configs (4.0)](https://kafka.apache.org/40/generated/producer_config.html) — `retries`, `linger.ms`, `delivery.timeout.ms`
- Oracle, [`CompletableFuture` (Java SE 25 API)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/CompletableFuture.html) — `completedFuture`/`failedFuture`, `allOf`, 예외 전파 규약, 의존 동작의 실행 스레드
- Spring, [Sending Messages :: Spring for Apache Kafka](https://docs.spring.io/spring-kafka/reference/kafka/sending-messages.html) — `KafkaTemplate.send(...)` 가 `CompletableFuture<SendResult<K,V>>` 를 반환
- 코드 원본: [MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement) `shared-common/src/main/java/github/lms/lemuel/common/outbox/`

[^kafkaproducer]: "The `send()` method is asynchronous. When called, it adds the record to a buffer of pending record sends and immediately returns. This allows the producer to batch together individual records for efficiency." — `KafkaProducer` javadoc, Apache Kafka 4.0.
[^linger]: `linger.ms` 기본값은 Apache Kafka 4.0 에서 0 → 5 로 변경됐다. Producer Configs, Apache Kafka 4.0.
[^cf]: `CompletableFuture`, Java SE 25 API 문서. `completedFuture` 는 Java 8, `failedFuture` 는 Java 9 부터.
[^allof]: `CompletableFuture.allOf` — 주어진 future 중 하나라도 예외로 완료되면 반환된 future 도 그 예외를 원인으로 하는 `CompletionException` 으로 예외 완료된다. Java SE 25 API 문서.
[^retries]: `retries` 설정 설명, Producer Configs, Apache Kafka 4.0.
[^delivery]: `delivery.timeout.ms` 기본값 120000ms(2분). Producer Configs, Apache Kafka 4.0.
