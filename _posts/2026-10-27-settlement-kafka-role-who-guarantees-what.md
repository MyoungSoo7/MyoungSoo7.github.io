---
layout: post
title: "정산 서비스에서 카프카의 역할 — 카프카가 보장하는 것과, 카프카에게 맡기지 않은 것"
date: 2026-10-27 23:16:11 +0900
categories: [backend, kafka]
tags: [kafka, settlement, outbox, idempotency, dlt, spring-kafka, strimzi, event-driven]
---

정산 시스템에서 카프카가 무슨 일을 하는지 한 문장으로 줄이면 이렇다. **카프카는 정산의 장부가 아니라 배달부다.** 금액이 맞는지, 한 번만 반영됐는지, 사라진 사건은 없는지 — 이 질문들의 답은 카프카 안에 있지 않다. 카프카 앞뒤의 데이터베이스와 코드에 있다.

이 글은 settlement 리포의 `main` 코드와 오늘(2026-10-27 23시) 운영 브로커 실측을 같이 놓고, **누가 무엇을 보장하는지** 를 한 칸씩 나눠 본다. 토픽 구조를 처음 실측한 기록은 [8월의 토픽 38개 실측 글](/2026/08/13/settlement-kafka-runtime-structure-measured/), 실패가 조용히 사라지는 지점은 [여섯 가드포인트 글](/2026/08/28/kafka-loses-silently-six-guardpoints/)에 있다. 여기서는 그 뒤로 달라진 것과 "역할 분담" 자체에 집중한다.

## 0. 오늘 운영 브로커의 모습

| 항목 | 실측 값 |
| --- | --- |
| 브로커 | Strimzi 로 띄운 Kafka 4.2.0, **브로커 겸 컨트롤러 파드 1개** |
| 토픽 | 145개 (`lemuel.*` 142개, 그중 `.DLT` 67개) |
| 파티션 | 3개짜리 93개 · 1개짜리 51개 · (내부 오프셋 토픽 50개짜리 1개) |
| 복제 계수 | **전 토픽 1** |
| 컨슈머 그룹 | 15개, 파티션 106개, **총 lag 0** |
| DLT 에 쌓인 메시지 | **0건** |
| outbox 테이블 | 2개 DB 합쳐 88행, **전부 PUBLISHED** |

8월에 38개였던 토픽이 145개로 늘었다. 기능이 늘면서 사건 종류가 늘었고, 사건마다 DLT 짝이 생겼다. 반면 흐른 사건 수는 많지 않다(outbox 88행). 포트폴리오로 운영 중인 시스템이라, **이 글의 숫자는 처리량이 아니라 구조를 보여 준다.**

## 1. 카프카에 넣기 전 — "DB 커밋과 발행"을 한 몸으로 묶는 건 outbox 다

정산 서비스가 "정산 확정"을 처리하면 두 가지를 해야 한다. DB 에 확정 상태를 쓰고, 다른 서비스(원장·대출·투자)에 그 사실을 알린다. 문제는 DB 와 카프카가 한 트랜잭션에 묶이지 않는다는 점이다. 커밋 전에 보내면 롤백돼도 메시지는 나간다. 커밋 후에 보내면 그 사이에 죽으면 메시지가 사라진다.

Transactional Outbox 패턴의 답은 **메시지를 먼저 같은 DB 트랜잭션 안의 `outbox_events` 테이블에 쓰고, 별도 프로세스가 그걸 브로커로 옮기는 것** 이다. 이렇게 하면 "DB 트랜잭션이 커밋될 때, 그리고 그때만" 메시지가 발행된다([Chris Richardson — Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html), [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)).

settlement 의 옮기는 쪽(`OutboxPublisherScheduler`)은 이렇게 생겼다.

- `PENDING` 행을 `FOR UPDATE SKIP LOCKED` 로 100개씩 **claim** 한다. 여러 인스턴스가 동시에 폴링해도 서로 다른 행만 가져간다([PostgreSQL Docs — The Locking Clause](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)).
- claim 에 **1분짜리 리스**를 찍는다. 발행 도중 워커가 죽어도 리스가 끝나면 다른 워커가 회수한다.
- `outbox.pending.count`·`outbox.failed.count` 를 게이지로 내보낸다. FAILED 는 알람 대상이다.

여기서 카프카가 하는 일은 아직 없다. **"사건이 빠지지 않고 기록된다"는 보장은 전적으로 Postgres 트랜잭션의 몫이다.**

## 2. 카프카가 실제로 맡은 일 — 순서, 내구성, 팬아웃

발행기(`KafkaOutboxPublisher`)가 카프카에 넘기는 레코드에는 세 가지 결정이 들어 있다.

1. **토픽 = 사건 종류.** `lemuel.<집합>.<사건>` 규칙이다. 예를 들어 `Payment` 의 `PaymentCaptured` 는 `lemuel.payment.captured` 로 간다.
2. **키 = 집합 ID.** 같은 결제, 같은 정산의 사건은 같은 키를 갖는다. 카프카는 같은 키를 같은 파티션에 쓰고, 한 파티션 안의 순서는 소비자에게 그대로 보장한다([Apache Kafka — Introduction](https://kafka.apache.org/intro)). "같은 정산의 생성 → 확정 → 조정"이 뒤집혀 도착하지 않는 근거가 이것이다.
3. **봉투는 헤더에.** `event_id`·`event_type`·`occurred_at`·`event_version`·`producer`·W3C `traceparent` 를 페이로드가 아니라 헤더에 싣는다. 도메인 본문과 전송 메타를 분리한 결정이다. `traceparent` 덕분에 결제 요청에서 시작한 트레이스가 원장 소비자까지 한 줄로 이어진다.

그리고 카프카가 가장 잘하는 일, **팬아웃**이다. `lemuel.settlement.confirmed` 하나를 원장(account)·대출(loan)·투자(investment)·입금(deposit)·알림(notification) 소비자 다섯이 각자 그룹으로 읽는다(오늘 실측). 정산 서비스는 누가 이 사건을 듣는지 모른다. 오늘 실측한 컨슈머 그룹이 15개인데, 그 15개가 늘어날 때마다 정산 서비스 코드는 한 줄도 바뀌지 않았다. **결합을 끊는 것** — 이게 정산 시스템에서 카프카에게 준 핵심 역할이다.

## 3. 카프카에게 맡기지 않은 것 — "정확히 한 번"

카프카 프로듀서는 3.0 부터 기본으로 idempotent 다. 브로커 장애로 프로듀서가 내부 재시도를 해도 중복이 생기지 않는다. 하지만 공식 문서가 분명히 선을 긋는다. **애플리케이션 수준의 재전송은 중복 제거 대상이 아니다**([KafkaProducer Javadoc](https://kafka.apache.org/42/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)).

outbox 릴레이가 바로 그 "애플리케이션 수준 재전송"을 한다. 발행은 성공했는데 PUBLISHED 표시를 쓰기 전에 죽으면, 리스가 끝난 뒤 다른 워커가 같은 행을 다시 보낸다. Richardson 의 패턴 설명도 같은 말을 한다. 릴레이는 같은 메시지를 두 번 이상 보낼 수 있으니 **소비자가 멱등해야 한다**.

그래서 정산은 "정확히 한 번"을 카프카에게 맡기지 않고 세 겹으로 직접 막는다.

| 층 | 어디서 | 무엇을 막나 |
| --- | --- | --- |
| L1 | outbox `event_id` UNIQUE | 발행 쪽에서 같은 사건이 두 번 기록되는 것 |
| L2 | `processed_events (consumer_group, event_id)` PK | 같은 사건을 같은 소비자가 두 번 처리하는 것 |
| L3 | 도메인 테이블 자연키 UNIQUE | 앞 두 겹을 우회한 중복이 장부에 남는 것 |

L2 는 코드로 강제된다. 모든 소비자의 공통 골격 `IdempotentEventConsumer` 가 "`event_id` 헤더 추출 → `processed_events` 확인 → JSON 파싱 → 도메인 처리 → 마커 저장 → ack" 순서를 고정한다(Template Method). 새 소비자를 만드는 사람은 `consumerGroup()`·`eventType()`·`handle()` 세 개만 채운다. 멱등 체크를 빼먹을 자리가 없다.

여기에 하나가 더 있다. 멱등은 "같은 사건의 재처리"만 막고, **"오래된 사건의 늦은 도착"** 은 막지 못한다. DLT 에서 재처리하거나 백필로 재발행하면 오래된 사건이 새 사건 뒤에 도착할 수 있다. 그래서 프로젝션 소비자는 옵트인으로 `occurred_at` 헤더를 보고, 이미 반영한 것보다 오래된 사건은 적용하지 않는다.

## 4. 실패를 시끄럽게 만드는 것 — 공용 에러 핸들러

Spring Kafka 의 기본 에러 핸들러는 재시도를 다 쓰면 그 레코드를 건너뛴다. 결제·정산 사건에서 건너뛰기는 곧 장부 결손이다.

settlement 는 이 배선을 원래 서비스마다 180줄씩 복사해 두었다. 그 결과 나중에 생긴 서비스(card·insurance·operation)에서는 배선 자체가 빠져 있었다. 지금은 `shared-common` 의 `KafkaConsumerErrorHandlingConfig` 한 벌로 모았다.

- 일시적 예외(락 타임아웃, IO) → 2초 간격 3회 재시도
- 독성 메시지(파싱 실패, 검증 실패, 상태 위반) → 재시도 없이 즉시 `<토픽>.DLT`
- 재시도 소진 → DLT 로 복사한 뒤 ack. 같은 파티션의 다음 메시지는 정상 처리된다.

`DeadLetterPublishingRecoverer` 는 원본 헤더를 그대로 넘기고 원래 토픽·파티션·오프셋·예외 정보를 헤더로 덧붙인다([Spring for Apache Kafka — Handling Exceptions](https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html)). 원본 `event_id` 가 살아 있으니, DLT 에서 다시 꺼내 재처리해도 L2 멱등이 그대로 작동한다. 배선 누락은 리포의 하네스 가드 규칙이 기계적으로 막는다.

오늘 DLT 67개 토픽에 쌓인 메시지는 0건이다. 다만 사건 자체가 88건뿐이라 "실패가 없다"는 증거로 보기엔 표본이 작다.

## 5. 정리 — 역할표

| 질문 | 답하는 곳 | 카프카? |
| --- | --- | --- |
| 사건이 빠지지 않고 기록되나 | Postgres 트랜잭션 + outbox | ✗ |
| 기록된 사건이 브로커까지 가나 | SKIP LOCKED 폴러 + 리스 회수 | ✗ |
| 같은 정산의 사건이 순서대로 오나 | 키 = 집합 ID → 파티션 내 순서 | **✓** |
| 여러 서비스에 동시에 알리나 | 토픽 + 컨슈머 그룹 팬아웃 | **✓** |
| 브로커 재시작에도 메시지가 남나 | 로그 보존(7일) | **✓** (단, 아래 6절) |
| 한 번만 반영되나 | L1·L2·L3 멱등 | ✗ |
| 늦게 온 옛 사건을 막나 | `occurred_at` 순서 가드 | ✗ |
| 실패가 사라지지 않나 | 공용 에러 핸들러 → DLT | 반반(저장은 카프카, 판단은 코드) |

카프카가 ✓ 인 칸은 셋 반이다. 정산의 정합성을 지키는 칸은 대부분 ✗ 다. 이건 카프카를 낮춰 보는 게 아니다. 카프카의 보장 범위를 정확히 알고, **그 바깥을 코드와 DB 로 메운 설계** 라는 뜻이다.

## 6. 아직 안 풀린 것

- **복제 계수 1, 브로커 1대.** 전 토픽이 `ReplicationFactor: 1` 이다. 프로듀서가 `acks=all` 이어도 in-sync 레플리카가 리더 하나뿐이라, 디스크를 잃으면 보존 중이던 메시지도 같이 잃는다([Apache Kafka — Producer Configs, acks](https://kafka.apache.org/42/configuration/producer-configs/)). 위 표의 "브로커 재시작에도 남나"는 *재시작* 까지만 ✓ 다. 노드 소실은 outbox 테이블(이미 PUBLISHED)에서 다시 발행해야 하는데, 그 경로는 아직 수동이다.
- **브로커와 정산 DB 가 같은 노드에 있다.** 둘 다 같은 노드의 로컬 디스크에 묶여 있어, 그 노드를 잃으면 사건의 원본(outbox)과 사본(로그)을 동시에 잃는다. 게다가 정산 DB 의 자동 백업은 오늘부터 꺼져 있다.
- **파티션 1개짜리 토픽 51개.** 공용 설정은 컨슈머 스레드 3개를 띄운다(`concurrency=3`). 파티션이 하나면 나머지 두 스레드는 놀고 있다. 지금 처리량에선 문제가 아니지만, "파티션 간 병렬 소비" 라는 설정 주석의 전제가 절반의 토픽에서는 성립하지 않는다.
- 이 글의 "lag 0, DLT 0" 은 **부하가 거의 없는 상태의 스냅숏** 이다. 부하 상태의 동작은 이 수치로 말할 수 없다.

## References

- Chris Richardson — [Pattern: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- AWS Prescriptive Guidance — [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- Apache Kafka — [Introduction (keys, partitions, ordering)](https://kafka.apache.org/intro)
- Apache Kafka — [KafkaProducer Javadoc 4.2 (idempotent producer)](https://kafka.apache.org/42/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)
- Apache Kafka — [Producer Configs 4.2 (acks, enable.idempotence)](https://kafka.apache.org/42/configuration/producer-configs/)
- Spring for Apache Kafka — [Handling Exceptions (DefaultErrorHandler, DeadLetterPublishingRecoverer)](https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html)
- PostgreSQL — [SELECT: The Locking Clause (SKIP LOCKED)](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
