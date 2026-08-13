---
layout: post
title: "카프카 구조는 설계도가 아니라 브로커에 남는다 — settlement 토픽 38개를 실측해 다시 그렸다"
date: 2026-08-13 17:20:00 +0900
categories: [backend, messaging, kafka]
tags: [kafka, strimzi, kraft, consumer-group, partition, outbox, dlt, settlement, observability]
---

> 설계 문서에는 "이벤트 기반 아키텍처"라고 적혀 있다.
> 그런데 브로커에 붙어서 `kafka-topics.sh --describe` 를 때려보면, 문서에 없는 토픽이 나오고, 문서에 있는 토픽에는 컨슈머가 없다.
> 이 글은 settlement 의 카프카를 **코드가 아니라 실행 중인 브로커에서** 읽어 구조를 다시 그린 기록이다.

## 측정 조건 (먼저 밝힌다)

- 대상: 자택 K3s 클러스터 1대(`ilwon` 노드)에 Strimzi 로 띄운 Kafka **4.2.0**, KRaft 모드, 브로커 **1대**.
- 시점: 2026-08-13. 모든 수치는 그날 `kubectl exec` 로 브로커에 직접 붙어 뽑은 값이다.
- **트래픽은 사실상 0이다.** 토픽별 log-end-offset 이 0~2 수준이고 `retention.ms=604800000`(7일)이라 과거 메시지는 이미 만료됐다. 그러니 이 글은 **처리량 벤치마크가 아니라 구조 관측**이다. 성능 주장은 하지 않는다.
- 단일 클러스터 1회 관측이므로 일반화하지 않는다. 재현 가능한 건 "명령어와 그 출력"까지다.

설계 의도 쪽 이야기 — Outbox 를 왜 쓰는지, Triple Idempotency 가 왜 3중인지 — 는 이미 따로 썼다. 겹치지 않게 그 글들을 전제로 깔고 간다.

- [정산 정합성의 진짜 어려움 — 배치 / Kafka / Outbox / Triple Idempotency]({% post_url 2026-06-13-settlement-consistency-batch-kafka-outbox %})
- [Kafka 운영 회고 — Outbox + Triple Idempotency + DLT]({% post_url 2026-06-17-kafka-in-production-settlement %})

---

## 1. 선언된 구조와 실행 중인 구조가 다르다

GitOps 로 관리되는 클러스터니까, 카프카 토픽도 당연히 선언돼 있을 거라 생각했다. 세어봤다.

```
$ kubectl -n kafka get kafkatopic
NAME                 PARTITIONS   REPLICATION FACTOR
notification-topic   3            1
```

**KafkaTopic CR: 1개.**

브로커에 직접 물어봤다.

```
$ kafka-topics.sh --bootstrap-server localhost:9092 --list | grep -v __consumer_offsets | wc -l
38
```

**실제 토픽: 38개.**

37개는 어디서 왔나. 애플리케이션이 만들었다. Spring Kafka 의 프로듀서가 존재하지 않는 토픽에 보내면 브로커의 `auto.create.topics.enable` 이 기본 파티션 수로 만들어버리고, 컨슈머 쪽 `NewTopic` 빈이 만들기도 한다. 어느 쪽이든 결과는 같다 — **토픽의 수명주기가 Git 밖에 있다.**

이게 왜 문제인가. 파티션 수와 복제 계수는 토픽을 만드는 순간 결정되고, 파티션은 늘릴 수는 있어도 줄일 수 없다. 즉 **되돌릴 수 없는 결정이 코드 배포 타이밍에 암묵적으로 내려지고 있다.** `notification-topic` 하나만 CR 로 선언돼 있다는 건, 이 원칙이 한 번 시도됐다가 확산되지 않았다는 뜻이다.

실측으로 확인한 파티션 분포:

| 파티션 수 | 토픽 수 | 해당 토픽 |
|---|---|---|
| 3 | 6 | `lemuel.payment.captured`, `lemuel.payment.refunded`, 그 둘의 `.DLT`, `notification-topic`, `order.created` |
| 1 | 32 | 나머지 전부 |

복제 계수는 **38개 전부 1**이다. 브로커가 1대니 당연한 결과지만, 뒤에서 다시 짚는다.

---

## 2. 토픽 이름이 곧 계약이다

토픽 이름은 손으로 짓지 않는다. 발행 코드가 규칙으로 만든다. `shared-common` 의 `KafkaOutboxPublisher` 를 보면 이렇다.

```java
// "Payment" + "PaymentCaptured" -> "lemuel.payment.captured"
private static String resolveTopic(OutboxEvent event) {
    String aggregate = event.getAggregateType().toLowerCase(Locale.ROOT);
    String eventType = event.getEventType();
    if (eventType.startsWith(event.getAggregateType()))
        eventType = eventType.substring(event.getAggregateType().length());
    return "lemuel." + aggregate + "." + camelToSnake(eventType);
}
```

`lemuel.<애그리거트>.<이벤트>`. 실측한 38개 중 **36개가 이 규칙을 따른다.** 도메인별로 갈라보면 구조가 그대로 보인다.

```
lemuel.payment.*      created / authorized / captured / confirmed / refunded  (+ .DLT 2개)
lemuel.settlement.*   created / confirmed / canceled / adjusted
                      holdback_released / holdback_consumed / withholding_accrued
lemuel.loan.*         disbursement_requested / corporate_loan_disbursed
                      secured_loan_disbursed / secured_loan_repaid
                      secured_loan_principal_repaid / repayment_applied
lemuel.ops.*          order.failed / payment.failed / settlement.failed
                      shipping.delayed / stock.depleted / stock.reclaim_delayed
lemuel.order.created  lemuel.payout.completed  lemuel.user.registered
lemuel.product.changed  lemuel.seller.tier_changed  lemuel.company.reputation_changed
lemuel.investment.executed  lemuel.pgreconciliation.discrepancy_approved
lemuel.seller_recovery.opened  lemuel.seller_recovery.offset
```

규칙을 안 따르는 2개가 남는다. `notification-topic` 과 — **`order.created`**. 접두사 없는 `order.created` 가 `lemuel.order.created` 와 나란히 존재한다. 이름 규칙을 도입하기 전 세대의 잔재다. 파티션 3개까지 잡고 살아 있다.

`lemuel.ops.*` 는 규칙에서 한 칸 더 들어간다. `ops` 는 애그리거트가 아니라 **운영 알림 채널**이다. 도메인 이벤트와 운영 이벤트가 같은 네임스페이스 규칙을 공유하되 두 번째 세그먼트로 갈라진다.

---

## 3. 파이프라인이 아니라 메시다

여기가 이 글의 핵심이다. 아키텍처 다이어그램은 보통 왼쪽에서 오른쪽으로 흐르는 화살표로 그려진다. 결제 → 정산 → 대출. 실제 컨슈머 그룹을 전부 describe 해서 토픽-구독 매트릭스를 만들어보니 그림이 달랐다.

컨슈머 그룹 **10개**, 구독 관계 실측:

| 컨슈머 그룹 | 구독 토픽 수 | 주요 구독 |
|---|---|---|
| `lemuel-account` | 17 | settlement.* 전부, loan.* 전부, investment.executed, payout.completed |
| `lemuel-operation` | 9 | ops.* 6개, order.created, payment.captured, settlement.created |
| `lemuel-settlement` | 6 | order.created, payment.captured, loan.repayment_applied, user.registered, product.changed, seller.tier_changed |
| `notification-service` | 5 | payment.captured/confirmed/refunded, settlement.confirmed, investment.executed |
| `lemuel-loan` | 3 | settlement.created, settlement.confirmed, company.reputation_changed |
| `lemuel-investment` | 1 | settlement.confirmed |
| `lemuel-settlement-refund-adjust` | 1 | payment.refunded |
| `lemuel-settlement-payment-view` | 1 | payment.refunded |
| `lemuel-settlement-recon-adjust` | 1 | pgreconciliation.discrepancy_approved |
| `notification` | 1 | notification-topic |

같은 매트릭스를 토픽 기준으로 뒤집으면 팬아웃이 드러난다.

| 토픽 | 이 토픽을 읽는 컨슈머 그룹 |
|---|---|
| `lemuel.settlement.confirmed` | **4개** — account, investment, loan, notification-service |
| `lemuel.payment.captured` | **3개** — settlement, operation, notification-service |
| `lemuel.settlement.created` | **3개** — account, loan, operation |
| `lemuel.payment.refunded` | **3개** — settlement-payment-view, settlement-refund-adjust, notification-service |

카프카 공식 문서는 이 성질을 이렇게 설명한다. "In Kafka, producers and consumers are fully decoupled and agnostic of each other, which is a key design element to achieve the high scalability that Kafka is known for."[^kafka-intro] 정산 서비스는 `settlement.confirmed` 를 발행할 때 그걸 누가 읽는지 모른다. 실제로 네 곳이 읽는다. 대출은 담보 회수를 위해, 투자는 수익 배분을 위해, 계정은 원장 기표를 위해, 알림은 사용자 통지를 위해.

그리고 방향이 한쪽이 아니다.

- `settlement` → `lemuel.settlement.confirmed` → `loan`
- `loan` → `lemuel.loan.repayment_applied` → `settlement` **그리고** `account`

**정산과 대출은 서로를 구독한다.** 순환이다. 이건 카프카에서는 자연스럽다 — 동기 호출의 순환 의존과 달리 데드락이 나지 않으니까. 하지만 대가가 있다: 어느 이벤트가 어느 이벤트를 유발했는지 코드만 읽어서는 절대 못 그린다. 그래서 `traceparent` 헤더가 필요하다(§5).

또 하나. `lemuel-settlement*` 로 시작하는 그룹이 **4개**다. 하나의 서비스가 컨슈머 그룹을 여러 개로 쪼갰다. `payment.refunded` 하나를 `settlement-payment-view`(조회 모델 갱신)와 `settlement-refund-adjust`(정산 조정)가 **각각의 그룹으로** 읽는다. 같은 그룹이었다면 둘 중 하나만 받는다. 그룹을 나눴다는 건 **"이 두 처리는 서로 독립적으로 실패하고 독립적으로 재처리돼야 한다"** 는 선언이다. 조회 모델 갱신이 터졌다고 정산 조정까지 멈추면 안 되니까.

---

## 4. 파티션 3개는 순서 보장 3묶음이자 스레드 3개다

`lemuel.payment.captured` 만 파티션 3개인 이유가 실측에 그대로 찍힌다.

```
GROUP             TOPIC                    PARTITION  OFFSET  LAG  CLIENT-ID
lemuel-settlement lemuel.payment.captured  0          -       -    consumer-lemuel-settlement-10
lemuel-settlement lemuel.payment.captured  1          2       0    consumer-lemuel-settlement-11
lemuel-settlement lemuel.payment.captured  2          -       -    consumer-lemuel-settlement-12
```

세 파티션에 세 개의 client-id 가 붙어 있고, HOST 는 **셋 다 `10.42.7.61` 로 같다.** 파드 하나 안의 스레드 3개다. Spring Kafka 의 `concurrency` 설정이 그대로 관측된 것이다.

```java
@Value("${app.kafka.consumer.concurrency:3}")
private int concurrency;
```

여기서 파티션 키가 중요해진다. 발행 코드는 파티션을 직접 고르지 않는다.

```java
ProducerRecord<String, String> record = new ProducerRecord<>(
        topic,
        null,                      // 파티션 — 키 해시로 자동 할당
        event.getAggregateId(),    // 키
        event.getPayload());
```

키가 `aggregateId` 다. 카프카 공식 문서: "Events with the same event key (e.g., a customer or vehicle ID) are written to the same partition, and Kafka guarantees that any consumer of a given topic-partition will always read that partition's events in exactly the same order as they were written."[^kafka-intro]

번역하면 — **같은 결제 건의 이벤트는 항상 같은 파티션에 들어가고, 발행 순서대로 읽힌다.** 병렬성 3배를 얻으면서 건별 순서는 잃지 않는다. 파티션을 3개로 늘린 대가로 포기한 건 **토픽 전체의 전역 순서**뿐이고, 정산에서 그건 애초에 필요 없다. 결제 A 와 결제 B 사이의 순서는 의미가 없으니까.

반대로 파티션 1개짜리 32개 토픽은 이 선택을 안 한 것이다. 전역 순서를 얻고 병렬성을 0으로 뒀다. 트래픽이 지금 수준이면 합리적이고, 늘어나면 하나씩 올려야 한다 — 그리고 그 시점에 §1 의 "토픽이 Git 밖에 있다" 가 청구서로 돌아온다.

---

## 5. 페이로드가 아니라 봉투를 본다

발행 코드가 헤더에 붙이는 것들:

```java
record.headers().add(new RecordHeader("event_id", ...));
record.headers().add(new RecordHeader("event_type", ...));
record.headers().add(new RecordHeader("aggregate_type", ...));
record.headers().add(new RecordHeader("occurred_at", ...));
record.headers().add(new RecordHeader("event_version", ...));
// producer, traceparent (비어 있지 않을 때만)
```

카프카에서 이벤트는 "key, value, timestamp, and optional metadata headers" 로 구성된다.[^kafka-intro] 여기서 헤더는 옵션이 아니라 **운영의 뼈대**다. 셋만 짚는다.

**`event_id`** — 컨슈머는 이걸로 중복을 막는다. `processed_events` 테이블의 PK 로 들어가고, 두 번째 도착한 같은 `event_id` 는 조용히 버려진다. at-least-once 전달을 멱등 수신으로 상쇄하는 표준형이다.

```java
public class SettlementConfirmedConsumer extends IdempotentEventConsumer {
    private static final String CONSUMER_GROUP = "lemuel-loan";
    @KafkaListener(topics = "${app.kafka.topic.settlement-confirmed}", groupId = CONSUMER_GROUP)
    @Transactional
    public void onSettlementConfirmed(ConsumerRecord<String,String> r, Acknowledgment ack) {
        consume(r, ack);
    }
}
```

**`event_version`** — 스키마 레지스트리가 없다. 이 클러스터에 Schema Registry 는 안 떠 있다(ns `kafka` 의 파드는 브로커, entity-operator, cluster-operator 셋뿐이다). 대신 헤더의 버전 필드로 호환성을 수동 관리한다. 레지스트리 없이 사는 대가는 **깨진 페이로드가 배포 시점이 아니라 소비 시점에 발견된다**는 것이다. 그 순간을 처리하는 게 다음 절의 DLT다.

**`traceparent`** — §3 에서 본 순환 구조에서 인과를 복원하는 유일한 수단이다. W3C Trace Context 형식이고, DLT 로 넘어갈 때도 보존된다.

---

## 6. 실측이 드러낸 구멍 세 개

### 6.1. 복제 계수 1 — 브로커가 죽으면 전부 멈춘다

```
$ kubectl -n kafka get kafkanodepool
NAME        REPLICAS   ROLES
dual-role   1          [controller broker]
```

노드풀 1개, 레플리카 1개, 컨트롤러와 브로커 역할을 한 파드가 겸한다. 토픽 38개 전부 RF=1. 카프카 공식 문서는 "A common production setting is a replication factor of 3"[^kafka-intro] 라고 명시한다.

여기서 정직해야 한다. **이건 버그가 아니라 자원 제약이다.** 노드 6대짜리 홈랩에서 브로커 3대를 띄우면 PVC 3개와 JVM 3개가 더 필요하다. 문제는 선택 자체가 아니라, 이 선택이 **어디에도 적혀 있지 않다**는 점이다. Outbox 와 Triple Idempotency 로 애플리케이션 계층의 정합성은 3중으로 막아놨는데, 그 아래 저장 계층은 단일 장애점이다. 파드가 있는 `ilwon` 노드가 내려가면 38개 토픽이 동시에 사라진다 — 정확히는 PVC 가 로컬이면 데이터까지.

방어 계층을 쌓을 때 **가장 얕은 층의 깊이가 전체의 깊이**다. Outbox 가 살아 있으니 브로커 복구 후 재발행은 되겠지만, 그건 "유실 안 됨"이지 "가용함"이 아니다.

### 6.2. 컨슈머가 하나도 없는 토픽 5개

38개 토픽과 10개 그룹의 구독 집합을 차집합으로 돌렸다.

```
$ comm -23 topics.txt consumed.txt
lemuel.payment.authorized
lemuel.payment.captured.DLT
lemuel.payment.created
lemuel.payment.refunded.DLT
order.created
```

성격이 셋으로 갈린다.

- **`.DLT` 2개 — 의도된 무구독.** Spring Kafka 의 `DeadLetterPublishingRecoverer` 는 재시도(2초 간격 3회)를 소진한 레코드를 `<원본토픽>.DLT` 로 보낸다.[^spring-dlt] 여기 쌓이는 건 자동으로 다시 처리되면 안 되는 것들이다 — 사람이 원인을 보고 수동으로 replay 하는 게 설계다. 컨슈머가 없는 게 정상이다. 다만 **컨슈머가 없다는 건 알림도 없다는 뜻**이므로, DLT 적재량을 감시하는 별도 지표(`loan.kafka.dlt.published`)가 반드시 살아 있어야 한다. 지표가 죽으면 DLT 는 조용한 무덤이 된다.
- **`payment.created` / `payment.authorized` — 발행만 되고 아무도 안 듣는다.** 결제 생명주기를 이벤트로 다 뱉어놨는데 소비처는 `captured` 이후부터 붙었다. 나쁜 상태는 아니다. 나중에 붙일 소비자를 위한 여지고, 카프카는 소비자 없는 토픽을 벌하지 않는다. 다만 "발행 중인데 아무도 안 듣는 이벤트"는 **스키마가 검증된 적 없는 이벤트**이기도 하다. 첫 소비자가 붙는 날 §5 의 대가를 치른다.
- **`order.created` — 유령.** 접두사 규칙 이전 세대의 토픽이고, 지금은 `lemuel.order.created` 가 그 자리를 대신한다. 발행자도 소비자도 없이 파티션 3개를 잡고 남아 있다. §1 의 직접적 결과다 — **Git 이 토픽을 소유하지 않으면 토픽은 지워지지도 않는다.** 코드에서 문자열을 지우는 것은 브로커에서 토픽을 지우는 것이 아니다.

### 6.3. 토픽 설정이 동적으로만 존재한다

```
$ kafka-configs.sh --entity-type topics --entity-name lemuel.payment.captured --describe
Dynamic configs for topic lemuel.payment.captured are:
  retention.ms=604800000 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.ms=604800000}
```

보존 기간 7일이 **동적 설정으로만** 잡혀 있다. Git 에 없다. 토픽을 실수로 지웠다가 다시 만들면 이 값은 브로커 기본값으로 돌아가고, 아무도 모른다. 6.1~6.3 은 전부 같은 뿌리에서 나온다 — §1.

---

## 7. 다시 그린 구조

측정 결과로 그리면 이렇게 된다. 화살표는 실제 구독 관계다.

```
                      [ Strimzi Cluster Operator ]
                                  |
                                  v
        ns kafka  /  Kafka CR "lemuel" 4.2.0  (KRaft, node-pools)
        +--------------------------------------------------+
        |  lemuel-dual-role-0   @node ilwon                 |
        |  roles=[controller, broker]  replicas=1  PVC 5Gi  |
        |  38 topics · RF=1 · 32×part1 + 6×part3            |
        +--------------------------------------------------+
                  ^                            |
     produce      |                            |  consume (10 groups)
     (Outbox 폴러) |                            v

  [payment]--payment.captured(p3,key=aggregateId)--+--> lemuel-settlement
                                                   +--> lemuel-operation
                                                   +--> notification-service
                     (재시도 3회 실패시) ---------------> payment.captured.DLT  (구독자 없음)

  [settlement]--settlement.confirmed---------------+--> lemuel-account
                                                   +--> lemuel-loan --------+
                                                   +--> lemuel-investment   |
                                                   +--> notification-service|
                                                                            |
  [loan]--loan.repayment_applied--> lemuel-settlement <---------------------+
                              \---> lemuel-account          (역방향 = 메시)

  [*]--ops.{order,payment,settlement}.failed ------> lemuel-operation
       ops.{shipping.delayed, stock.depleted, ...}

  고아: order.created(p3, 발행X 소비X) · payment.created · payment.authorized
```

왼쪽에서 오른쪽으로 흐르는 선이 아니다. 중앙에 브로커 하나가 있고, 그 주위에 **서로를 모르는 10개의 구독 집단**이 붙어 있다. 결제는 정산이 자기를 듣는 줄 모르고, 정산은 대출·투자·계정·알림 넷이 자기를 듣는 줄 모른다.

---

## 8. 한 줄

**카프카 구조를 알고 싶으면 코드가 아니라 브로커에 물어봐야 한다.** 코드는 의도를 말하고, `--describe` 는 결과를 말한다. settlement 의 경우 그 둘의 차이는 토픽 37개, 고아 5개, 그리고 Git 이 모르는 보존 기간 하나였다.

가장 먼저 고칠 것 하나만 고르라면 §1 이다. 토픽을 KafkaTopic CR 로 끌어오면 6.2 의 고아도, 6.3 의 유령 설정도 구조적으로 못 생긴다. 복제 계수 1(6.1)은 자원이 필요한 문제라 다음이다 — 대신 **적어두기라도 해야 한다.** 문서에 없는 단일 장애점이 가장 나쁜 종류의 단일 장애점이다.

---

## References

**1차·공식 출처**

- Apache Kafka, [Introduction — Main Concepts and Terminology](https://kafka.apache.org/documentation/#intro) : 이벤트의 구성(key/value/timestamp/optional metadata headers), 프로듀서-컨슈머 분리, 키 기반 파티션 할당과 파티션 내 순서 보장, 일반적 운영 복제 계수 3.
- Spring for Apache Kafka, [Handling Exceptions — Publishing Dead-letter Records](https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html) : `CommonErrorHandler`, `DeadLetterPublishingRecoverer` 의 `<topic>.DLT` 라우팅 동작.
- Strimzi, [Documentation](https://strimzi.io/documentation/) : `Kafka` / `KafkaNodePool` / `KafkaTopic` 커스텀 리소스와 KRaft 모드 운영.

**본인 실측 (재현 가능한 명령까지만 주장)**

- 2026-08-13, 단일 K3s 클러스터의 `kafka` 네임스페이스에서 `kubectl exec` 로 실행한 `kafka-topics.sh --describe`, `kafka-consumer-groups.sh --describe`, `kafka-configs.sh --describe`, `kubectl get kafka/kafkanodepool/kafkatopic` 출력. 트래픽이 거의 없는 포트폴리오 환경이므로 **성능·처리량에 대한 주장은 하지 않는다.**

**같은 시스템의 설계 관점 글**

- [정산 정합성의 진짜 어려움 — 배치 / Kafka / Outbox / Triple Idempotency]({% post_url 2026-06-13-settlement-consistency-batch-kafka-outbox %})
- [Kafka 운영 회고 — Outbox + Triple Idempotency + DLT]({% post_url 2026-06-17-kafka-in-production-settlement %})

[^kafka-intro]: Apache Kafka, "Introduction — Main Concepts and Terminology", <https://kafka.apache.org/documentation/#intro>
[^spring-dlt]: Spring for Apache Kafka Reference, "Handling Exceptions", <https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html>
