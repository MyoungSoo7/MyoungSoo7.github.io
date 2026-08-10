---
layout: post
title: "Apache Kafka 정리: 핵심 개념부터 운영 전 체크리스트까지"
date: 2026-08-10 16:40:00 +0900
categories: [java, spring, kafka, distributed-systems]
tags: [Apache Kafka, event-driven, consumer-group, partition, idempotency, outbox, observability]
---

Apache Kafka를 “써봤다”고 말하는 것과 Kafka를 **설계·운영할 수 있다**는 것은 다르다. Greg Lee’s Lab의 세 글을 읽고, Kafka의 핵심 구조·실무 트레이드오프·면접 검증 질문을 하나의 학습 노트로 다시 정리했다.

- [“Kafka 써봤어요”라는 후보자에게 질문할 것들](https://medium.com/greglee-lab/kafka-%EC%8D%A8%EB%B4%A4%EC%96%B4%EC%9A%94-%EB%9D%BC%EB%8A%94-%ED%9B%84%EB%B3%B4%EC%9E%90%EC%97%90%EA%B2%8C-%EC%A7%88%EB%AC%B8%ED%95%A0-%EA%B2%83%EB%93%A4-913d7890eb28)
- [Apache Kafka Isn’t a Silver Bullet: 4 Things to Check Before You Ship](https://medium.com/greglee-lab/apache-kafka-isnt-a-silver-bullet-4-things-to-check-before-you-ship-28128627a32f)
- [The 8 Core Concepts That Make Up Apache Kafka](https://medium.com/greglee-lab/the-8-core-concepts-that-make-up-apache-kafka-adfe5c57fc0f)

두 번째·세 번째 글은 Medium 회원 전용으로 본문 일부가 제한되어 있어, 확인 가능한 원문 범위와 [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/)를 함께 기준으로 삼았다.

## 1. Kafka가 필요한 이유: M×N 연결을 줄이는 로그

시스템이 늘어날 때 서비스끼리 직접 연결하면 생산자와 소비자 사이의 연결 수가 빠르게 증가한다.

```text
Producer A → Consumer 1
Producer A → Consumer 2
Producer B → Consumer 1
Producer B → Consumer 2
...
```

Kafka는 메시지를 중앙 로그에 기록하고, 여러 소비자가 각자의 속도로 읽도록 만든다.

```text
Producer
   ↓
Topic / Partition / Disk Log
   ↓
Consumer Group A
Consumer Group B
Consumer Group C
```

Kafka의 핵심 가치는 단순한 “비동기 큐”가 아니다.

```text
기록을 보존한다
여러 Consumer Group이 같은 이벤트를 독립 소비한다
각 그룹이 자기 offset을 관리한다
처리량과 보존 기간을 조정할 수 있다
```

그러나 이 장점은 파티션·offset·중복·순서·운영 비용을 함께 이해할 때만 얻을 수 있다.

## 2. Kafka의 핵심 구성요소

### 2.1 Broker

Broker는 Kafka 서버 한 대다. Producer의 레코드를 받아 디스크에 기록하고, Consumer의 fetch 요청에 응답한다. 여러 Broker가 Cluster를 구성하며, 파티션 리더·팔로워를 분산해 처리량과 장애 대응을 확보한다.

### 2.2 Cluster와 Controller

Cluster는 Broker들의 집합이다. Controller 역할은 파티션 리더 배치와 Broker 상태 변화 같은 클러스터 메타데이터를 관리한다. 운영자는 Broker 수만 늘리는 것이 아니라 다음을 함께 확인해야 한다.

```text
Broker별 디스크 여유
partition leader 분포
replica 동기화 상태
controller·metadata 안정성
```

### 2.3 Topic

Topic은 이벤트를 분류하는 논리적 이름이다. 중요한 것은 Topic을 명령이 아니라 **발생한 사실** 중심으로 설계하는 것이다.

```text
나쁜 예:
  do_payment
  process_order

좋은 후보:
  payment_completed
  order_cancelled
```

다만 Topic을 이벤트 종류별로 무조건 잘게 나누면 서로 다른 Topic 사이의 순서를 보장하기 어려워진다. “이벤트 명명”과 “순서가 필요한 사건의 묶음 단위”는 별도로 설계해야 한다.

### 2.4 Partition

Partition은 Topic의 물리적 로그 단위다. Kafka에서 핵심적인 사실은 세 가지다.

```text
순서는 Partition 내부에서만 보장된다
Consumer Group의 병렬성 상한은 Partition 수다
Partition은 Broker에 분산되어 확장된다
```

따라서 Partition 수는 단순한 용량 숫자가 아니다.

```text
순서 범위
처리 병렬성
Consumer 수
Broker·디스크 부하
키 재분배
```

를 함께 결정한다.

### 2.5 Record·Offset

Record는 Kafka에 기록되는 메시지 단위이며, Offset은 Partition 안에서의 위치다. Offset은 전역 메시지 ID가 아니다.

```text
Topic A, Partition 0, Offset 100
Topic A, Partition 1, Offset 100
```

은 서로 다른 위치다. 따라서 중복 제거 키는 Offset만으로 설계하면 부족할 수 있다. 업무 이벤트에는 `event_id`, `aggregate_id`, `occurred_at`, `schema_version` 같은 envelope를 두는 편이 안전하다.

### 2.6 Producer

Producer는 Record를 Kafka로 발행한다. 같은 Aggregate의 순서를 유지하려면 보통 Aggregate ID를 key로 사용해 같은 Partition으로 보낸다.

```text
order-123 / payment_completed
order-123 / payment_cancelled
→ 같은 key
→ 같은 Partition
→ 해당 주문 내부 순서 유지
```

단, key 기반 순서는 “해당 key가 같은 Partition에 배치되는 동안”의 순서다. Partition 수 변경, 이벤트 설계, 재처리 정책까지 함께 검토해야 한다.

### 2.7 Consumer와 Consumer Group

Consumer Group은 Kafka를 이해하는 핵심 단위다.

```text
같은 group.id의 Consumer:
  Partition을 나눠 병렬 처리

다른 group.id의 Consumer:
  같은 Topic을 독립적으로 소비
  각자의 offset 보유
```

한 Group 안에서 하나의 Partition은 동시에 한 Consumer에게만 할당된다. Consumer 수가 Partition 수보다 많으면 일부 Consumer는 유휴 상태가 된다.

Kafka가 일반적인 경쟁 소비 큐와 다른 이유도 여기에 있다. 결제 서비스, 분석 서비스, 알림 서비스가 같은 이벤트를 각자의 목적과 속도로 읽을 수 있다.

### 2.8 Replication과 Retention

Partition은 replica로 복제될 수 있다. `replication.factor`, `acks=all`, `min.insync.replicas`는 내구성과 지연 사이의 선택을 만든다.

```text
replication.factor:
  몇 개의 replica를 둘 것인가

acks=all:
  ISR replica들의 확인을 기다릴 것인가

min.insync.replicas:
  최소 몇 개의 동기 replica가 있어야 쓰기를 허용할 것인가

retention:
  기록을 얼마 동안 보존할 것인가
```

Replication은 백업과 동일하지 않다. 논리 삭제, 잘못된 Producer, 잘못된 이벤트도 복제될 수 있으므로 장기 보존·백업·복구 전략은 별도로 필요하다.

## 3. Kafka의 진짜 장점과 대가

Kafka의 큰 장점은 **여러 Consumer Group이 같은 Topic을 독립적으로 읽을 수 있다는 것**이다. 하나의 이벤트를 정산·알림·검색·분석이 각각 소비할 수 있다.

그러나 다음 네 가지 비용을 반드시 계산해야 한다.

### 3.1 순서 비용

순서는 전체 Topic이 아니라 Partition 단위다.

주문 `order-123`에 대해 다음 순서가 중요하다고 하자.

```text
order_completed
order_cancelled
```

두 이벤트에 같은 주문 ID를 key로 사용해야 같은 Partition에 배치할 수 있다. 하지만 모든 주문의 전역 순서를 보장하려고 Partition을 하나로 만들면 확장성과 처리량을 잃는다.

좋은 설계는 보통 다음과 같다.

```text
전체 순서 보장: 포기
주문 단위 순서: 보장
```

### 3.2 중복 처리 비용

Kafka 소비는 일반적으로 at-least-once 의미론을 전제로 설계한다. Consumer가 메시지를 처리한 뒤 offset commit 전에 죽거나 리밸런싱이 발생하면, 마지막으로 commit된 위치부터 다시 읽을 수 있다.

따라서 Consumer는 중복을 견뎌야 한다.

```text
방법 1: 비즈니스 연산을 멱등하게 설계
방법 2: event_id를 저장하고 UNIQUE로 중복 차단
방법 3: 처리 기록과 비즈니스 변경을 같은 DB 트랜잭션으로 묶기
```

Kafka transaction과 exactly-once semantics가 Kafka 내부 처리에는 도움을 주지만, 외부 DB·HTTP API·결제사까지 자동으로 exactly-once가 되는 것은 아니다.

### 3.3 Rebalance 비용

Consumer가 배포·재시작되거나 Group membership이 바뀌면 Partition 재할당이 발생한다. 리밸런싱 중 소비가 멈추거나 처리량이 떨어질 수 있다.

확인할 것:

```text
배포 시 rebalance 시간
consumer lag 변화
assignment 방식
cooperative rebalancing 적용 여부
세션·poll timeout
```

“Consumer를 여러 개 띄우면 빨라진다”만 말하면 부족하다. 재배포와 장애 복구 때 생기는 stop-the-world 구간도 설명해야 한다.

### 3.4 운영 비용

Kafka는 Broker만 띄우면 끝나는 라이브러리가 아니다.

```text
Partition 수
Replica 배치
디스크·보존 정책
Consumer lag
ISR 축소
Broker 장애
인증·인가·TLS
Schema compatibility
```

를 운영해야 한다. 처리량이 높지 않고 단일 소비자·짧은 지연·간단한 재시도만 필요하다면 Kafka보다 RabbitMQ, SQS, Redis Streams 또는 DB Outbox가 더 단순한 선택일 수 있다.

## 4. DB와 Kafka의 이중 쓰기 문제

가장 위험한 흐름은 다음이다.

```text
1. DB transaction commit 성공
2. Kafka publish 실패
```

그러면 DB에는 주문·결제가 존재하지만 다른 서비스는 이벤트를 받지 못한다. 반대 순서도 문제가 된다.

### Outbox Pattern

```text
Business transaction:
  business table 변경
  OUTBOX table insert
  → 같은 DB transaction

Relay:
  OUTBOX를 읽어 Kafka publish
  성공 후 published 상태 기록
```

이 방식은 DB 변경과 “발행할 이벤트의 기록”을 원자적으로 묶는다. Relay가 중복 발행할 수 있으므로 Consumer 멱등성은 여전히 필요하다.

### CDC

CDC는 DB transaction log/binlog를 읽어 변경을 이벤트로 전달한다. 애플리케이션 코드의 발행 부담을 줄일 수 있지만 다음 비용이 있다.

```text
스키마 변경 관리
삭제·정정 의미 해석
Debezium/Connect 운영
원본 테이블과 이벤트 계약 분리
```

Outbox와 CDC 중 어느 것이 정답이 아니라, 팀의 운영 역량·스키마 복잡성·이벤트 의미론에 따라 선택해야 한다.

## 5. Topic과 Partition 설계 체크리스트

### Topic 이름

```text
사실 중심인가?
명령과 이벤트를 구분했는가?
도메인과 수명 주기가 비슷한가?
서로 다른 소비 요구를 억지로 한 Topic에 넣지 않았는가?
```

### Partition key

```text
순서를 보장할 Aggregate는 무엇인가?
key가 균등하게 분포하는가?
특정 key hot spot이 생기는가?
Partition 수를 나중에 늘릴 때 순서 정책이 어떻게 되는가?
```

### Partition 수

```text
예상 처리량
Consumer 병렬성
Broker별 disk/network
향후 증가량
리밸런싱 비용
```

을 기준으로 정한다. 나중에 늘릴 수는 있지만 줄이기는 어렵고, key-to-partition 매핑 변화가 순서 정책에 영향을 줄 수 있다.

### Replica와 내구성

```text
replication factor
acks
min.insync.replicas
unclean leader election
retention
```

을 하나의 내구성 정책으로 검토한다. “replica가 있으니 데이터가 안전하다”는 설명은 부족하다.

## 6. 운영 장애를 어떻게 관찰할 것인가

최소한 다음 지표가 필요하다.

| 영역 | 지표·Trace |
| --- | --- |
| Consumer | consumer lag, poll 지연, 처리 latency |
| Broker | request latency, disk usage, network, ISR |
| Partition | leader 분포, under-replicated partition |
| Producer | send error, retry, record error, batch 효율 |
| Consumer Group | rebalance 횟수·시간, assignment 변화 |
| 데이터 | 처리 건수, 성공·실패·중복·DLQ 건수 |
| 계약 | schema compatibility, serialization 오류 |

특히 업무 파이프라인에서는 다음을 분리해야 한다.

```text
Kafka publish 성공
≠ Consumer 처리 성공
Consumer 처리 성공
≠ DB upsert 성공
실패 카운터 0
≠ 데이터가 들어왔다는 증거
```

업무 데이터의 source count, consumed count, processed count, upsert count, last non-zero success를 함께 봐야 한다.

## 7. “Kafka 써봤어요” 면접 질문을 설계로 바꾸기

다음 질문은 용어 암기보다 설계 경험을 확인한다.

```text
토픽과 Partition의 관계는?
순서는 어느 범위에서 보장되는가?
Consumer Group의 병렬성 상한은?
같은 Topic을 여러 서비스가 읽는 방식은?
중복 소비는 왜 생기는가?
처리와 offset commit의 순서는?
DB commit 후 Kafka publish 실패는 어떻게 처리하는가?
Outbox와 CDC의 비용 차이는?
배포 시 rebalance와 lag는 어떻게 관찰했는가?
Partition 수와 replication factor를 어떻게 결정했는가?
```

좋은 답변은 다음 구조를 갖는다.

```text
상황
→ 선택
→ 보장하는 것
→ 포기하는 것
→ 장애 시나리오
→ 관찰 지표
→ 실제 검증 결과
```

“Kafka를 사용했다”보다 “주문 ID를 key로 선택해 주문 단위 순서를 보장했고, at-least-once 중복은 event_id UNIQUE와 트랜잭션으로 처리했으며, lag와 rebalance를 모니터링했다”가 훨씬 강한 답이다.

## 8. Settlement에 적용한다면

Settlement 도메인에 Kafka를 적용할 때 후보 이벤트는 다음과 같다.

```text
payment_captured
order_completed
refund_requested
settlement_requested
settlement_completed
payout_completed
```

설계 질문:

```text
정산 이벤트의 Aggregate key는 seller_id인가, order_id인가?
환불과 정산 완료의 순서는 어느 단위에서 필요한가?
중복 payout을 어떻게 막는가?
DB 변경과 이벤트 발행을 어떻게 원자화하는가?
재처리 시 금액이 중복 반영되지 않는가?
대사·재조정 이벤트를 어떻게 남기는가?
```

예를 들어 지급 결과를 중복 처리하지 않으려면 다음이 필요하다.

```text
payout_id 또는 event_id
UNIQUE constraint
처리 상태 전이
외부 결제사 reference
retry와 compensation 정책
감사 로그
```

Kafka를 도입하는 것보다 더 중요한 것은 **정산 금액의 불변성·멱등성·대사 가능성**이다.

## 9. Kafka를 쓰지 않아야 하는 경우

다음 조건이면 Kafka가 과할 수 있다.

```text
소비자가 하나뿐이다
메시지 보존·재생이 필요 없다
처리량이 작다
지연·재시도 요구가 단순하다
운영팀이 Broker·lag·replica를 관리할 여력이 없다
```

이 경우 다음 대안을 비교한다.

```text
DB Outbox + worker
RabbitMQ
SQS/Pub/Sub
Redis Streams
Spring Batch 또는 Scheduler
```

반대로 다음 조건이면 Kafka의 가치가 커진다.

```text
여러 독립 Consumer가 같은 이벤트를 읽는다
이벤트 재생과 장기 보존이 필요하다
처리량과 수평 확장이 중요하다
Consumer가 각자 다른 속도로 처리한다
분산 이벤트 backbone을 운영할 역량이 있다
```

## 결론

Kafka는 Broker·Topic·Partition·Offset·Producer·Consumer Group·Replication·Retention을 따로 외우는 기술이 아니다. 이 요소들이 다음 속성을 어떻게 만드는지 이해해야 한다.

```text
순서
병렬성
재생
중복
내구성
가용성
확장성
운영 비용
```

가장 중요한 판단은 다음이다.

> Kafka를 도입할 것인가가 아니라, 여러 소비자·재생·처리량·순서·중복·운영비용이라는 문제를 Kafka의 대가로 감당할 것인가를 먼저 결정해야 한다.

## References

- [Greg Lee’s Lab — “Kafka 써봤어요”라는 후보자에게 질문할 것들](https://medium.com/greglee-lab/kafka-%EC%8D%A8%EB%B4%A4%EC%96%B4%EC%9A%94-%EB%9D%BC%EB%8A%94-%ED%9B%84%EB%B3%B4%EC%9E%90%EC%97%90%EA%B2%8C-%EC%A7%88%EB%AC%B8%ED%95%A0-%EA%B2%83%EB%93%A4-913d7890eb28)
- [Greg Lee’s Lab — Apache Kafka Isn’t a Silver Bullet](https://medium.com/greglee-lab/apache-kafka-isnt-a-silver-bullet-4-things-to-check-before-you-ship-28128627a32f)
- [Greg Lee’s Lab — The 8 Core Concepts That Make Up Apache Kafka](https://medium.com/greglee-lab/the-8-core-concepts-that-make-up-apache-kafka-adfe5c57fc0f)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Kafka Design](https://kafka.apache.org/documentation/#design)
- [Apache Kafka Introduction](https://kafka.apache.org/intro)
- [Apache Kafka Exactly Once Semantics](https://kafka.apache.org/documentation/#semantics)
- [Debezium Documentation](https://debezium.io/documentation/)
- [Confluent — Event Streaming Platform](https://www.confluent.io/blog/event-streaming-platform-1/)

*이 글은 세 원문을 요약·재구성하고 Apache Kafka 공식 문서와 대조한 학습·설계 노트다. 원문 전체를 재게시하지 않으며, 회원 전용 본문은 확인 가능한 범위만 사용했다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*

*보정 메모: 세 번째 원문의 8개 개념 전체 본문은 Medium paywall로 제한되어 있어, 제목·공개된 개요와 Kafka 공식 문서를 기준으로 핵심 구성요소를 재구성했다.*

---

## Related posts

- [Java/Spring 확장성: 변하는 축·추상화·이름](https://myoungsoo7.github.io/2026/08/10/scalability-abstraction-interview/)
- [Agent가 어려워하는 일을 자동화한 로컬 Script·Tool 지도](https://myoungsoo7.github.io/2026/08/10/agent-tools-built-on-mac/)
- [Settlement Order·Payment·Settlement 흐름](https://myoungsoo7.github.io/2026/08/09/settlement-order-payment-flow/)

---

## End

> Kafka는 도구의 이름이 아니라, 메시지의 수명·순서·중복·소유권과 운영 비용을 결정하는 설계 선택이다.

---

