---
layout: post
title: "Spring Cloud Stream × Kafka — 함수 하나를 토픽에 묶는 추상화, 그리고 그 대가"
date: 2026-11-10 23:56:28 +0900
categories: [spring, kafka]
tags: [spring-cloud-stream, kafka, spring-cloud-function, binder, dlq, consumer-group, partitioning, eda]
---

이 글은 [MSA · EDA · CDC · CQRS 비교]({% post_url 2026-11-10-msa-eda-cdc-cqrs-comparison %}) → [멱등성과 멱등키]({% post_url 2026-11-10-idempotency-key-design %})에 이은 세 번째 글이다. 앞의 두 글이 "이벤트로 서비스를 잇는다면 무엇을 지켜야 하나"를 다뤘다면, 이번엔 스프링 진영에서 그걸 **코드로 옮길 때 가장 먼저 만나는 프레임워크** — Spring Cloud Stream(이하 SCS)과 그 Kafka 바인더를 1차 문서 기준으로 정리한다.

## 1. 한 줄 요약 — SCS는 "Kafka 클라이언트"가 아니라 "바인딩 추상화"다

Kafka를 스프링에서 쓰는 방법은 크게 둘이다.

| | Spring for Apache Kafka (`spring-kafka`) | Spring Cloud Stream + Kafka 바인더 |
|---|---|---|
| 개발자가 쓰는 것 | `KafkaTemplate`, `@KafkaListener` | `Supplier` / `Function` / `Consumer` 빈 |
| 토픽은 어디에 | 코드(애너테이션 속성 등) | **설정**(`bindings.<이름>.destination`) |
| 브로커 교체 | Kafka 전용 | 바인더 교체로 RabbitMQ 등 이식 가능 |
| 관계 | — | Kafka 바인더가 내부적으로 spring-kafka 리스너 컨테이너를 사용 |

SCS의 핵심 아이디어는 **비즈니스 로직을 메시징 미들웨어에서 떼어 내는 것**이다. 개발자는 `java.util.function` 타입의 빈만 만들고, 그 함수의 입력·출력을 어떤 토픽에 붙일지는 바인더와 설정이 정한다. 마지막 행은 이 글 뒤쪽에서 중요하다: Kafka 바인더의 재시도 기본값 일부는 **spring-kafka 컨테이너의 기본값**으로 떨어진다([SCS Kafka DLQ 문서][dlq]).

## 2. 프로그래밍 모델 — 함수 세 가지

SCS 레퍼런스는 메시지 핸들러를 함수 빈으로 작성하라고 권한다. v2.1부터 Spring Cloud Function 기반의 함수형 정의가 가능해졌고, 3.x부터는 함수형 구현을 권장한다([Producing and Consuming Messages][produce]).

```java
@Bean
public Supplier<Order> orderSource() { ... }          // 소스: 입력 없음, 출력 1

@Bean
public Function<Order, Invoice> billing() { ... }     // 프로세서: 입력 1, 출력 1

@Bean
public Consumer<Invoice> notifier() { ... }           // 싱크: 입력 1, 출력 없음
```

- `Function`과 `Consumer`는 바인딩된 목적지에 데이터가 들어오면 호출된다 — 전형적인 이벤트 드리븐 컴포넌트다.
- `Supplier`는 입력이 없으므로 누군가 불러 줘야 한다. 명령형 `Supplier`는 **기본 폴러가 1초마다** 호출해 메시지를 하나씩 만든다(`spring.integration.poller.fixed-delay` 등으로 조정). 반응형 `Supplier<Flux<T>>`는 한 번만 호출된다([Producing and Consuming Messages][produce]).
- 함수 빈이 여러 개면 `spring.cloud.function.definition`으로 어떤 것을 바인딩할지 지정한다. 하나뿐이면 자동 탐지되지만, 문서는 혼동을 피하려면 **명시하는 것이 모범 사례**라고 말한다. 메시징과 무관한 `Function` 빈 하나가 우연히 자동 바인딩될 수 있기 때문이다([같은 문서][produce]).

### "REST 요청이 들어왔을 때 이벤트 발행"은 StreamBridge

실무에서 가장 흔한 발행 지점은 폴러가 아니라 **컨트롤러나 서비스 메서드 안**이다. 이때는 `StreamBridge`를 주입해 바인딩 이름으로 보낸다. 레퍼런스는 REST 엔드포인트 같은 "바인더가 아닌 외부 소스"를 스트림에 잇는 수단으로 이걸 소개하며, 폴러 기반 `Supplier`는 스레드가 예측하기 어려워 ThreadLocal에 의존하는 트레이싱 등과 충돌할 수 있으니 그런 경우 `StreamBridge`를 쓰라고 안내한다([같은 문서][produce]).

```java
@RestController
@RequiredArgsConstructor
class OrderController {
    private final StreamBridge streamBridge;

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.ACCEPTED)
    void place(@RequestBody OrderRequest req) {
        streamBridge.send("orderPlaced-out-0", req.toEvent());
    }
}
```

> ⚠️ `StreamBridge.send()`를 DB 트랜잭션 안에서 부르면 [첫 글]({% post_url 2026-11-10-msa-eda-cdc-cqrs-comparison %})에서 다룬 **이중 쓰기(dual write)** 문제가 그대로 생긴다 — DB 커밋은 됐는데 발행은 실패하거나, 그 반대다. 발행 누락이 허용되지 않는 이벤트라면 SCS를 쓰더라도 Outbox(+CDC 또는 릴레이)를 앞에 둬야 한다. SCS는 발행을 *쉽게* 만들어 주지만 *원자적으로* 만들어 주지는 않는다.

### 애너테이션 모델은 사라졌다

`@EnableBinding`, `@StreamListener`, `@Input`, `@Output` 기반 코드는 3.x에서 공식 폐기(deprecated)됐고([GH-2026 커밋][deprecate]) **4.0에서 제거**됐다([4.0 Migration guide][mig40]). Spring Boot 3 계열과 함께 쓰는 SCS 4.x 이상에서는 함수형 모델만 남는다. 인터넷의 오래된 예제가 컴파일되지 않는 가장 흔한 이유다.

## 3. 바인딩 이름 규칙 — 설정 키의 뼈대

함수형 모델에서 바인딩 이름은 규칙으로 만들어진다([Producing and Consuming Messages][produce]).

```
<함수 빈 이름>-in-<인덱스>     입력
<함수 빈 이름>-out-<인덱스>    출력
```

단일 입력·출력 함수라면 인덱스는 항상 0이다. 그래서 `billing` 함수의 입출력을 토픽에 연결하는 설정은 이렇게 된다.

```yaml
spring:
  cloud:
    function:
      definition: billing;notifier
    stream:
      kafka:
        binder:
          brokers: kafka:9092
      bindings:
        billing-in-0:
          destination: order.placed
          group: billing          # ← 4장에서 왜 필수인지
        billing-out-0:
          destination: invoice.issued
        notifier-in-0:
          destination: invoice.issued
          group: notifier
```

이름이 도메인과 동떨어져 보이면 `spring.cloud.stream.function.bindings.billing-in-0=orders` 처럼 바꿀 수 있지만, 그 뒤로는 **바꾼 이름으로** 모든 바인딩 속성을 걸어야 한다. 문서는 대부분의 경우 기본 이름을 따르는 게 합리적이라고 말한다([Kafka Streams binder — ancillaries][names]).

## 4. 컨슈머 그룹 — `group`을 빼먹으면 생기는 일

Kafka 바인더는 목적지를 Kafka 토픽에, SCS 컨슈머 그룹을 **Kafka 컨슈머 그룹에 그대로** 매핑하고, 파티셔닝도 Kafka 파티션에 직접 매핑한다([Kafka Binder Reference][binderref]).

SCS 문서의 정의는 이렇다: 같은 목적지를 구독하는 **모든 그룹은 데이터 사본을 각각 받지만, 한 그룹 안에서는 한 멤버만** 그 메시지를 받는다. 그리고 그룹을 지정하지 않으면 SCS는 그 애플리케이션을 **익명의 단일 멤버 그룹**에 넣는다([Consumer Groups][groups]).

이게 실무에서 의미하는 바:

- `billing` 서비스를 3개 인스턴스로 늘렸는데 `group`을 안 줬다면, 각 인스턴스가 각자 익명 그룹이 되어 **같은 주문을 세 번 처리**한다. 스케일 아웃이 곧 중복 처리가 된다.
- 익명 그룹으로는 **DLQ를 켤 수 없다**. Kafka 바인더 문서는 DLQ를 쓰려면 `group`을 반드시 지정해야 한다고 명시한다([DLQ 문서][dlq]).

그러니 사실상 규칙은 하나다 — **입력 바인딩에는 항상 `group`을 준다.**

## 5. 파티셔닝 — 대부분은 Kafka에 맡긴다

"같은 고객의 이벤트는 같은 순서로" 같은 요구가 있으면 같은 키가 같은 파티션으로 가야 한다. 여기서 흔한 오해가 SCS의 `partitionKeyExpression` / `partitionCount`를 먼저 설정하는 것이다.

Kafka 바인더 문서는 분명히 말한다: Kafka는 파티셔닝을 네이티브로 지원하므로, **커스텀 파티션 키나 페이로드를 쓰는 표현식이 필요한 경우가 아니면 바인더 파티셔닝에 의존할 필요가 없다.** 바인더 파티셔닝은 원래 네이티브 파티셔닝이 없는 미들웨어를 위한 것이다. 레코드 키만 주면(`KafkaHeaders.KEY` 헤더) Kafka가 키 해시로 파티션을 고른다([Partitioning with the Kafka Binder][partitions]).

```java
streamBridge.send("orderPlaced-out-0",
    MessageBuilder.withPayload(event)
        .setHeader(KafkaHeaders.KEY, event.customerId())
        .build());
```

그리고 바인더 파티셔닝을 쓸 때의 함정도 같은 문서에 있다. 바인더 기본 전략(`key.hashCode() % partitionCount`)은 **독립 Kafka 프로듀서(예: Kafka Streams가 쓰는 것)의 기본 전략과 다르므로, 같은 키가 서로 다른 파티션으로 갈 수 있다**([같은 문서][partitions]). 한 토픽에 SCS 앱과 다른 클라이언트가 함께 쓴다면 키 순서 보장이 깨질 수 있다는 뜻이다.

소비 쪽은 Kafka가 그룹 멤버에게 파티션을 나눠 준다. 인스턴스 수(× `concurrency`)가 파티션 수보다 많으면 일부는 놀게 되므로, 문서는 파티션을 미리 **넉넉하게 프로비저닝**하라고 권한다([같은 문서][partitions]).

## 6. 에러 처리 — 기본값은 "로그 찍고 버림"

이 장이 이 글에서 가장 중요하다.

SCS 공통 문서에 따르면, 메시지 핸들러가 예외를 던지면 바인더가 `RetryTemplate`으로 같은 메시지를 **기본 3회** 시도한다(`maxAttempts`=3, 초기 간격 1000ms, 최대 10000ms, 배수 2.0). 그래도 실패하면? 별도 설정이 없으면 기본 에러 핸들러는 **에러를 로그로 남기고, 메시지는 버려진다(dropped).** 문서도 "대부분의 경우 이는 허용되지 않으며 메시지 유실을 피할 복구 메커니즘이 필요하다"고 적는다([Error Handling][errors]).

Kafka 바인더에서는 여기에 미묘한 차이가 하나 더 있다([DLQ 문서][dlq]).

| 설정 | 실제 재시도 동작 |
|---|---|
| DLQ 켬 (`enable-dlq: true`) | `max-attempts`(기본 3)를 따르고, 소진되면 DLQ 토픽으로 보냄 |
| DLQ 끔 (기본값) | `max-attempts`는 **영향이 없음**. spring-kafka 컨테이너 기본값(**10회**)으로 재시도 |
| DLQ 끔 + 재시도 완전히 끄고 싶음 | `max-attempts: 1`로는 **안 됨**. `ListenerContainerCustomizer`로 `DefaultErrorHandler`의 백오프를 0회로 바꿔야 함 |

즉 "`max-attempts: 1`로 재시도를 껐다"고 생각한 설정이 DLQ를 켜지 않은 상태에선 아무 효과가 없을 수 있다. 문서에 그대로 적힌 함정이다.

DLQ 설정은 이렇게 한다.

```yaml
spring:
  cloud:
    stream:
      bindings:
        billing-in-0:
          destination: order.placed
          group: billing                 # DLQ 의 전제 조건
          consumer:
            max-attempts: 3
      kafka:
        bindings:
          billing-in-0:
            consumer:
              enable-dlq: true
```

문서의 예제에서 원래 목적지 `so8400out`, 그룹 `so8400`의 DLQ 토픽은 `error.so8400out.so8400`이다 — 즉 `error.<destination>.<group>` 꼴이다([DLQ 문서][dlq]).

두 가지를 더 기억하자.

- **DLQ에 들어간 메시지를 어떻게 처리할지는 프레임워크가 정하지 않는다.** 원인이 일시적이면 원래 토픽으로 되돌려 보낼 수 있지만, 영구적 문제면 무한 루프가 된다. 문서의 예제는 재시도 횟수를 헤더에 세다가 3회를 넘으면 별도의 "parking lot" 토픽으로 옮긴다([DLQ 문서][dlq]).
- **커스텀 에러 핸들러는 DLQ와 배타적이다.** `error-handler-definition`으로 `Consumer<ErrorMessage>`를 지정하면, DLQ가 설정돼 있어도 DLQ로 보내지지 않는다([Error Handling][errors]).
- 반응형 함수(`Function<Flux<T>, …>`)는 메시지 핸들러가 아니므로 위의 `RetryTemplate`·DLQ 설명이 **적용되지 않는다**. Reactor의 `retryWhen` 같은 연산자로 직접 처리해야 한다([Error Handling][errors]).

## 7. 재시도는 중복을 만든다 — 멱등 소비자로 돌아가서

6장의 재시도·DLQ 재처리·리밸런스 후 재전달은 모두 **같은 메시지가 두 번 이상 핸들러에 들어오는 경로**다. 오프셋 커밋 시점도 영향을 준다. Kafka 바인더의 `ackEachRecord` 설명은, 기본적으로 오프셋은 `poll()`이 반환한 배치 전체가 처리된 뒤 커밋되며 레코드마다 커밋하면 성능은 떨어지지만 실패 시 재전달 가능성을 줄인다고 적는다(이 속성은 3.1부터 `ackMode`로 대체)([Kafka Binder 설정][config]). "줄인다"이지 "없앤다"가 아니다.

그러니 SCS의 `Consumer` / `Function` 안쪽은 [멱등성과 멱등키]({% post_url 2026-11-10-idempotency-key-design %}) 7장의 **멱등 소비자**여야 한다 — 처리한 메시지 ID를 비즈니스 변경과 같은 트랜잭션에 기록하고, 이미 있으면 건너뛴다. 프레임워크는 at-least-once까지 데려다주고, 마지막 한 걸음은 핸들러 코드의 몫이다.

```java
@Bean
public Consumer<Message<OrderPlaced>> billing(BillingService service) {
    return msg -> service.handleOnce(
        msg.getHeaders().get("eventId", String.class),   // 발행 측이 넣은 이벤트 ID
        msg.getPayload());                                // 내부에서 processed_events INSERT + 처리, 한 트랜잭션
}
```

(Kafka 바인더는 `transaction.transactionIdPrefix`로 Kafka 트랜잭션도 켤 수 있다([Kafka Binder 설정][config]). 이는 *Kafka 안에서의* 읽기-처리-쓰기 원자성에 관한 것이고, 핸들러가 외부 DB에 쓰는 부작용까지 한 트랜잭션으로 묶어 주지는 않는다는 점에서 멱등 소비자를 대체하지 않는다.)

## 8. 언제 SCS를 쓰고, 언제 spring-kafka를 직접 쓸까

중립적인 비교 벤치마크나 연구는 찾지 못했다. 아래는 두 프로젝트의 공식 문서가 밝힌 설계 의도에서 끌어낸 **판단 기준**이다.

**SCS가 잘 맞는 경우**
- 핸들러가 "하나 받아 변환해 하나 보낸다"는 모양으로 깔끔하게 떨어지는 파이프라인.
- 토픽·그룹·재시도·DLQ를 코드가 아닌 **설정으로** 환경마다 바꾸고 싶을 때.
- Kafka와 RabbitMQ를 함께 쓰거나 바꿀 가능성이 있을 때(바인더 교체).

**spring-kafka를 직접 쓰는 편이 나은 경우**
- 리스너 컨테이너·에러 핸들러·오프셋 커밋을 세밀하게 제어해야 할 때. 6장에서 보듯 SCS를 써도 결국 `ListenerContainerCustomizer`로 spring-kafka 레벨에 내려가야 하는 순간이 온다.
- Kafka 고유 기능(트랜잭션·헤더·시킹 등)을 깊게 쓰고, 브로커 이식성은 필요 없을 때.

추상화는 공짜가 아니다. SCS의 "함수 하나 + 설정 몇 줄"은 **기본값이 무엇인지 알 때만** 안전하다 — 특히 "실패한 메시지는 기본적으로 버려진다"는 것과 "`group`이 없으면 인스턴스마다 다 받는다"는 두 가지.

## 9. 체크리스트

- [ ] `spring.cloud.function.definition`을 **명시**했는가? (우연한 자동 바인딩 방지)
- [ ] 모든 입력 바인딩에 `group`이 있는가? (스케일 아웃 시 중복 처리, DLQ 불가)
- [ ] `enable-dlq`를 켰는가? 안 켰다면 실패 메시지가 **로그만 남고 버려진다**는 걸 알고 있는가?
- [ ] DLQ 토픽(`error.<destination>.<group>`)을 **누가, 어떻게** 재처리하는지 정했는가? 무한 루프 방지(parking lot)는?
- [ ] 커스텀 `error-handler-definition`을 쓰고 있다면 DLQ가 꺼진다는 걸 알고 있는가?
- [ ] 순서가 필요한 이벤트에 **레코드 키**(`KafkaHeaders.KEY`)를 넣는가? 같은 토픽을 쓰는 다른 클라이언트와 파티셔너가 일치하는가?
- [ ] 핸들러가 **멱등**한가? (재시도·리밸런스·DLQ 재처리 모두 중복 경로)
- [ ] DB 커밋과 발행이 함께 일어나야 한다면 `StreamBridge` 직접 호출이 아니라 **Outbox**를 쓰는가?
- [ ] 옛 예제의 `@EnableBinding` / `@StreamListener`를 쓰고 있지 않은가? (4.0에서 제거)

## References

1. Spring Cloud Stream Reference, "[Producing and Consuming Messages][produce]" — 함수형 모델, `spring.cloud.function.definition`, 바인딩 이름 규칙, 폴러, `StreamBridge`.
2. Spring Cloud Stream Reference, "[Consumer Groups][groups]".
3. Spring Cloud Stream Reference, "[Error Handling][errors]" — `RetryTemplate` 기본값, drop, 커스텀 에러 핸들러, 반응형 함수 예외.
4. Spring Cloud Stream Reference, "[Dead-Letter Topic Processing (Kafka binder)][dlq]".
5. Spring Cloud Stream Reference, "[Partitioning with the Kafka Binder][partitions]".
6. Spring Cloud Stream Reference, "[Configuration Options (Kafka binder)][config]" — `ackEachRecord`/`ackMode`, `transaction.transactionIdPrefix`.
7. Spring Cloud Stream Kafka Binder Reference Guide, "[Usage / Overview][binderref]" — 목적지·그룹·파티션의 Kafka 매핑.
8. Spring Cloud Stream Reference, "[Overriding the default binding names (Kafka Streams binder)][names]".
9. spring-cloud/spring-cloud-stream, "[4.0 Migration guide][mig40]" (GitHub Wiki) — 애너테이션 모델 제거.
10. spring-cloud/spring-cloud-stream, "[GH-2026 Formally deprecate annotation-based programming model][deprecate]" (commit e3faae2, 2020-10-06).
11. 앞 글: [MSA · EDA · CDC · CQRS 비교]({% post_url 2026-11-10-msa-eda-cdc-cqrs-comparison %}), [멱등성과 멱등키]({% post_url 2026-11-10-idempotency-key-design %})

[produce]: https://docs.spring.io/spring-cloud-stream/reference/spring-cloud-stream/producing-and-consuming-messages.html
[groups]: https://docs.spring.io/spring-cloud-stream/reference/spring-cloud-stream/consumer-groups.html
[errors]: https://docs.spring.io/spring-cloud-stream/reference/spring-cloud-stream/overview-error-handling.html
[dlq]: https://docs.spring.io/spring-cloud-stream/reference/kafka/kafka-binder/dlq.html
[partitions]: https://docs.spring.io/spring-cloud-stream/reference/kafka/kafka-binder/partitions.html
[config]: https://docs.spring.io/spring-cloud-stream/reference/kafka/kafka-binder/config-options.html
[binderref]: https://docs.spring.io/spring-cloud-stream/docs/current/reference/html/spring-cloud-stream-binder-kafka.html
[names]: https://docs.spring.io/spring-cloud-stream/reference/kafka/kafka-streams-binder/ancillaries-to-the-programming-model.html
[mig40]: https://github.com/spring-cloud/spring-cloud-stream/wiki/4.0-Migration-guide
[deprecate]: https://github.com/spring-cloud/spring-cloud-stream/commit/e3faae2091330a521f48b7df628acbc2597b41f4
