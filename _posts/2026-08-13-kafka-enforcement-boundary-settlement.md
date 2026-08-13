---
layout: post
title: "컨슈머는 코드에 있는데 브로커엔 그룹이 없다 — settlement 카프카를 '강제 장치의 경계선'에서 읽었다"
date: 2026-08-13 17:30:00 +0900
categories: [backend, messaging, kafka]
tags:
  [
    kafka,
    strimzi,
    spring-kafka,
    outbox,
    idempotency,
    gitops,
    settlement,
    argocd,
  ]
---

> 같은 시스템의 카프카를 오늘 두 번 읽었다. 한 번은 **브로커가 무엇을 갖고 있나**를 보려고([카프카 구조는 설계도가 아니라 브로커에 남는다]({% post_url 2026-08-13-settlement-kafka-runtime-structure-measured %})), 이 글은 **무엇이 그 상태를 강제하고 있나**를 보려고 읽었다.
>
> 결론부터. settlement 는 정합성을 문서로 부탁하지 않고 **기계로 강제**한다 — 계약 테스트, 커밋 훅 린트, DB UNIQUE 3단. 그런데 오늘 실측으로 남아 있는 카프카 결함은 **하나도 빠짐없이 그 강제 장치가 닿지 않는 바깥쪽**에 있었다. Helm 환경변수 한 줄, 브로커 기본값, 3일 전까지 Git 에 없던 CR.

---

## 0. 측정 조건 (먼저 밝힌다)

- 대상: 자택 K3s 클러스터의 `kafka` 네임스페이스. Strimzi, Kafka **4.2.0**, KRaft, `KafkaNodePool` `dual-role` **replicas=1**, 파드는 `ilwon` 노드.
- 소비 측: `settlement-prod` 네임스페이스의 Spring Boot 서비스들 + Kotlin/Go 폴리글랏.
- 시점: **2026-08-13**. 모든 수치는 그날 `kubectl exec` 로 브로커에 붙거나 파드 안에서 직접 뽑았다.
- **트래픽은 사실상 0이다.** 토픽별 log-end-offset 이 0~3 수준이다. 그러니 이 글이 지적하는 것들은 **아직 사고를 낸 적이 없다.** 성능·장애 주장은 하지 않는다. 주장하는 건 "설계가 의도한 상태와 런타임의 실제 상태가 다르다"까지다.
- 설계 쪽 근거는 리포의 ADR 원문(`docs/adr/0003`, `0005`, `0017`, `0024`)과 `origin/develop` 의 소스다.

---

## 1. settlement 는 정합성을 기계로 강제한다

먼저 이 시스템이 무엇을 잘하고 있는지 정확히 말해야, 그 다음의 지적이 의미를 갖는다.

**Transactional Outbox.** 도메인 변경과 이벤트 적재를 한 커밋으로 묶는다. ADR 0003 의 문제 정의는 교과서적이다 — "DB 커밋은 성공했는데 Kafka 발행 직전 프로세스가 죽으면 이벤트 유실, Kafka 발행은 성공했는데 DB 커밋이 롤백되면 유령 이벤트." 두 저장소에 걸친 원자성을 2PC 없이 얻는 표준 해법이다.[^outbox] 폴러는 `FOR UPDATE SKIP LOCKED` 로 행을 claim 해서 ShedLock 없이 멀티 인스턴스로 돈다.

**3단 멱등.** at-least-once 를 전제하고 컨슈머를 멱등하게 만든다.

1. `outbox_events.event_id UUID UNIQUE` — 발행 측 중복 적재 차단
2. `processed_events` PK `(consumer_group, event_id)` — 소비 측 중복 처리 차단
3. 비즈니스 UNIQUE (`settlements.payment_id` 등) — 최후 방어선

**DLT 배선을 린트로 강제.** 여기가 인상적이다. ADR 0017 은 서비스마다 에러 핸들러 설정을 복붙하던 문화 때문에 **나중에 추가된 서비스에서 배선 자체가 누락**돼 Spring Kafka 기본 핸들러로 떨어졌다고 적는다. 기본 핸들러는 재시도를 소진한 뒤 메시지를 조용히 skip 하므로 사실상 유실이다. 배선을 `shared-common` 한 벌로 모으고, 누락을 `scripts/harness/guard.mjs` 의 `KAFKA-DLQ` 룰이 커밋 단계에서 막는다. 룰 메시지가 문제의 본질을 정확히 짚는다.

> 이 위반은 '잘못 쓴 줄'이 아니라 '없는 파일'이다.

**계약을 파일로 고정.** `shared-common` 의 testFixtures 에 토픽별 JSON Schema **37개** + 정본 샘플 37개를 두고, 프로듀서 테스트는 실제 outbox 페이로드를 캡처해 스키마로 검증한다(ADR 0024). 금액 필드가 JSON number 로 되돌아가는 것을 막는 전용 테스트까지 있다.

정리하면 — **리포 안쪽에서 일어날 수 있는 실수는 거의 다 기계가 잡는다.**

---

## 2. 그런데 오늘 브로커에는 `lemuel-company` 그룹이 없다

`company-service` 에는 컨슈머가 있다. 코드도, 그룹 이름도, 멱등 골격도 다 있다.

```java
@Component
@ConditionalOnProperty(name = "app.kafka.enabled", havingValue = "true")
public class UserRegisteredEventConsumer extends IdempotentEventConsumer {

    private static final String CONSUMER_GROUP = "lemuel-company";

    @KafkaListener(topics = "${app.kafka.topic.user-registered:lemuel.user.registered}",
                   groupId = CONSUMER_GROUP,
                   containerFactory = "kafkaListenerContainerFactory")
```

`guard.mjs` 의 KAFKA-DLQ 룰도 통과한다 — company 는 컴포넌트 스캔 범위를 좁혀놨기 때문에 공용 에러 핸들링이 자동으로 안 잡힌다는 걸 알고, 전용 `@Import` 클래스를 따로 만들어 뒀다. 그 클래스의 주석은 이렇게 시작한다.

> 명시 `@Import` 가 없으면 Spring Kafka 기본 핸들러로 조용히 떨어져 재시도 소진 메시지가 유실된다.

**설계도, 코드도, 린트도 통과했다. 브로커에는 그 그룹이 없다.**

```
$ kubectl exec -n kafka lemuel-dual-role-0 -- \
    bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list | sort
lemuel-account
lemuel-investment
lemuel-loan
lemuel-operation
lemuel-settlement
lemuel-settlement-payment-view
lemuel-settlement-recon-adjust
lemuel-settlement-refund-adjust
notification
notification-service
```

10개. `lemuel-company` 는 없다. 파드는 멀쩡히 떠 있다.

```
$ kubectl get deploy settlement-company -n settlement-prod
NAME                 READY
settlement-company   1/1
```

원인은 실행 중인 컨테이너 안에서 확인했다. 배포 매니페스트의 `env` 만 보면 `envFrom` 으로 주입되는 Secret 을 놓칠 수 있으니, **파드 내부의 실제 환경**을 봐야 한다.

```
$ kubectl exec -n settlement-prod settlement-company-5ccff4d5bd-jnxd7 -- sh -c 'env | grep -i kafka'
SPRING_KAFKA_BOOTSTRAP_SERVERS=lemuel-kafka-bootstrap.kafka.svc.cluster.local:9092
```

**한 줄뿐이다.** `APP_KAFKA_ENABLED` 가 없다. 그리고 `application.yml` 의 기본값은 이렇다.

```yaml
app:
  kafka:
    enabled: ${APP_KAFKA_ENABLED:false}
```

`false` 다. 그러면 `@ConditionalOnProperty(havingValue = "true")` 가 붙은 것들이 **전부** 안 만들어진다 — 컨슈머 빈도, 공용 에러 핸들링 설정도, `KafkaConfig` 도. 부팅 로그에 에러는 없다. 브로커 주소는 친절하게 주입돼 있어서 설정이 완결돼 보인다. 그런데 아무도 구독하지 않는다.

세 방향에서 같은 결론이 나왔다: (1) 파드 내부 환경변수, (2) 브로커의 그룹 목록, (3) `application.yml` 의 기본값. 서로 독립적인 관측이다.

**정직하게 덧붙인다.** `lemuel.user.registered` 의 log-end-offset 은 **0**이다. 아직 아무것도 못 받은 게 아니라, 애초에 발행된 게 없다. 그래서 오늘 기준 피해는 **0**이다. 이 글이 지적하는 건 손실이 아니라 **정상 신호가 켜진 채로 존재하는 공백**이다.

---

## 3. `acks=all` 인데 복제본은 1개다

모든 서비스의 `application.yml` 이 같은 프로듀서 설정을 갖는다.

```yaml
spring:
  kafka:
    producer:
      acks: all
      retries: 5
      properties:
        enable.idempotence: true
        max.in.flight.requests.per.connection: 5
```

내구성에 진심인 설정이다. Kafka 4.2 공식 문서의 `acks` 항목은 이렇게 적는다.

> **acks=all** This means the leader will wait for the full set of in-sync replicas to acknowledge the record. This guarantees that the record will not be lost **as long as at least one in-sync replica remains alive.**[^kafka-acks]

핵심은 마지막 조건절이다. 보장의 강도는 `acks` 값이 아니라 **ISR(in-sync replica) 집합의 크기**에서 나온다. 그리고 이 클러스터의 브로커 설정은 이렇다.

```
$ kubectl exec -n kafka lemuel-dual-role-0 -- bin/kafka-configs.sh \
    --bootstrap-server localhost:9092 --entity-type brokers --entity-name 0 --describe --all
  default.replication.factor=1
  min.insync.replicas=1
  auto.create.topics.enable=true
  num.partitions=1
  log.retention.hours=168
  unclean.leader.election.enable=false
```

토픽 39개 전부 RF=1. `min.insync.replicas=1`. 즉 **ISR 의 크기가 항상 1**이고, `acks=all` 은 런타임에서 `acks=1` 과 동일하게 동작한다. 토픽 설정 문서가 권장하는 조합은 정반대다.

> A typical scenario would be to create a topic with a replication factor of 3, set `min.insync.replicas` to 2, and produce with acks of "all".[^kafka-misr]

`enable.idempotence: true` 도 마찬가지다. 이건 **프로듀서 재시도로 인한 중복 쓰기**를 막는 장치지, 브로커가 통째로 사라지는 것과는 무관하다.

직관용 모형으로 적으면, 복제본 $n$ 개가 독립적으로 각각 확률 $r$ 로 살아남을 때 데이터가 보존될 확률은

$$
D(n) = 1 - (1-r)^{\,n}
$$

이고, $n=1$ 이면 $D = r$ 이다. **복제는 이 식에서 유일하게 지수를 만드는 항인데, 그 지수가 1이다.** (실제 복제본은 독립이 아니므로 이 식은 크기 감각용이지 예측용이 아니다.)

그래서 이 파이프라인의 실제 내구성 경계는 애플리케이션이 아니라 **`ilwon` 노드에 고정된 5Gi 로컬 PV 하나**다. Outbox 가 살아 있으니 브로커를 복구하면 재발행은 가능하다 — 하지만 그건 "복구 가능"이지 "유실 없음"이 아니고, 무엇보다 **이 트레이드오프가 어디에도 결정으로 기록돼 있지 않다.** 코드 주석에는 있다.

```java
// 복제본 1 — 개발/데모용. 프로덕션은 최소 3 권장.
return TopicBuilder.name("lemuel.payment.captured")
        .partitions(partitions)
        .replicas(1)
```

주석은 "개발/데모용"이라고 말하는데, 이 값이 실제로 도는 곳은 `settlement-prod` 다. **주석이 틀린 게 아니라, 주석이 가리키던 환경이 그대로 프로덕션이 됐다.**

---

## 4. 컨슈머 51명, 파티션 17개

`concurrency` 설정이 실측에 어떻게 찍히는지 보자.

```java
factory.setConcurrency(concurrency);   // ${app.kafka.consumer.concurrency:3}
```

`settlement-prod` 어느 배포에도 `APP_KAFKA_CONSUMER_CONCURRENCY` 가 없으니 기본값 3이 적용된다. account-service 는 컨슈머 클래스가 17개다. 결과:

```
$ kafka-consumer-groups.sh --describe --group lemuel-account --state
GROUP           ...  STATE     #MEMBERS
lemuel-account  ...  Stable    51
```

**멤버 51명.** 그리고 이 그룹이 구독하는 17개 토픽은 **전부 파티션 1개**다. 총 파티션 17개.

```
$ kafka-consumer-groups.sh --describe --group lemuel-account | wc -l   # 17 rows
```

Spring for Apache Kafka 공식 문서는 이 상황을 명시한다.

> if you have three topics with five partitions each and you want to use `concurrency=15`, you see only five active consumers, each assigned one partition from each topic, **with the other 10 consumers being idle.** This is because the default Kafka `ConsumerPartitionAssignor` is the `RangeAssignor`[^spring-concurrency]

같은 계산을 적용하면 51명 중 **최대 17명만 파티션을 할당받고 나머지 34명은 영구 유휴**다. `lemuel-settlement` 도 같다 — 멤버 18명, 파티션 8개(그중 `payment.captured` 만 3개).

이건 버그는 아니다. 다만 공짜도 아니다. 유휴 컨슈머도 브로커 연결을 잡고, 폴 루프를 돌고, 힙을 쓰고, 리밸런스에 참여한다. **브로커 1대 위에서 처리량 이득 0으로 51개의 소비 스레드가 도는 상태**다.

원인은 3장과 같은 뿌리다. 파티션 수를 정하는 `NewTopic` 선언은 리포에 **4개**뿐이고(`payment.captured`, `payment.refunded`, 그리고 둘의 `.DLT`), 나머지 토픽은 브로커의 `auto.create.topics.enable=true` + `num.partitions=1` 로 태어났다. **선언된 것만 파티션 3개, 나머지는 1개.** 파티션 수는 코드가 아니라 "누가 먼저 만들었나"의 화석이다.

Strimzi 는 이 조합을 명시적으로 권장하지 않는다. Unidirectional Topic Operator 를 쓸 때는 `auto.create.topics.enable` 을 꺼두라는 것이 프로젝트의 공식 권고다.

> The recommendation when using the UTO is to configure the Kafka cluster with `auto.create.topics.enable: false` in order to reduce the likelihood of hitting this problem.[^strimzi-uto]

그리고 이 클러스터의 Entity Operator 에는 Topic Operator 가 켜져 있다(`entityOperator.topicOperator: {}`). 켜져 있지만 관리 대상은 `KafkaTopic` CR 이 있는 토픽뿐이다. Strimzi 문서의 표현:

> If a topic is created, deleted, or modified directly within the Kafka cluster, without the presence of a corresponding `KafkaTopic` resource, **the Topic Operator does not manage that topic.**[^strimzi-to]

CR 은 `notification-topic` 하나뿐이고, 그 토픽의 오프셋은 **0**이다. **유일하게 선언으로 관리되는 토픽이 유일하게 아무 데이터도 흐르지 않는 토픽**이다.

---

## 5. 같은 실패가 층을 갈아타며 세 번 나타났다

지금까지 본 것들은 서로 다른 문제가 아니다. **같은 실패 양식이 층을 바꿔 가며 반복된 것**이다. 공통 성질은 하나 — _정상 신호가 계속 켜져 있다._

### 5.1. 코드 층 (해결됨)

Spring Kafka 기본 에러 핸들러가 재시도 소진 후 메시지를 조용히 skip. 서비스가 늘어나며 복붙된 설정이 누락돼 발생. → `shared-common` 단일화 + `guard.mjs` KAFKA-DLQ 룰로 **커밋 단계에서 기계 차단**.

### 5.2. 인프라 CR 층 (2026-08-10 해결)

`helm-deploy/infra-ssd/kafka-cluster.yaml` 파일 머리말에 사고 기록이 그대로 남아 있다.

> (2026-08-10) GitOps 편입. 이전엔 이 두 CR 이 git 에 없었고 kubectl apply 로만 존재했다(managedFields 소유자 = kubectl-client-side-apply). 그 결과: nodepool 은 `class: local-path` 를 선언 → 실제 PVC 는 `ssd-local` … 둘이 어긋나 Strimzi 가 매 2분 PVC 를 local-path 로 되돌리려다 422 immutable 로 실패 → **Kafka NotReady 가 52일간 지속됐다. 브로커는 정상 동작했으므로 조용한 실패였다.**

52일이다. 그리고 **Kafka CR 자체가 Git 에 들어온 게 3일 전**이다. 앞선 글이 "토픽이 Git 밖에 있다"고 지적했는데, 사흘 전까지는 **클러스터 정의 자체가 Git 밖에 있었다.**

### 5.3. 배포 설정 층 (현존)

2장의 `APP_KAFKA_ENABLED`. 코드 린트가 닿지 않고, CR GitOps 도 닿지 않는다 — 이건 Helm values 의 환경변수 목록이기 때문이다. 파드는 `1/1 Running`, ArgoCD 는 `Synced/Healthy`, 브로커 주소는 주입돼 있다. **모든 신호가 초록인데 구독이 없다.**

세 사건의 공통점을 한 문장으로 줄이면 이렇다.

> **강제 장치는 자기가 사는 층까지만 강제한다. 실패는 그 위층으로 이사한다.**

`guard.mjs` 는 Gradle 모듈 안을 본다. ArgoCD 는 Git 에 있는 매니페스트를 본다. Kafka 는 브로커 설정을 본다. 이 셋 사이의 **틈**(Helm 환경변수, 선언되지 않은 토픽, CR 밖의 dynamic config)에는 강제자가 없다. 그리고 정확히 그 틈에서만 오늘의 결함이 나왔다.

ArgoCD 의 `Synced/Healthy` 를 건강 신호로 읽으면 안 되는 이유도 같다. 그건 "Git 과 클러스터가 일치한다"는 뜻이지 "의도한 대로 동작한다"는 뜻이 아니다. **Git 이 모르는 것에 대해서는 영원히 Synced 다.**

---

## 6. 무엇부터 고칠 것인가

비용 대비 효과 순으로.

**1) `APP_KAFKA_ENABLED` 를 company 배포에 추가 (수 분).** 지금은 피해가 0이지만, `lemuel.user.registered` 에 첫 메시지가 흐르는 날 조용히 놓친다. 더 중요한 건 재발 방지다 — _`@KafkaListener` 를 가진 서비스의 배포는 `APP_KAFKA_ENABLED=true` 를 반드시 갖는다_ 를 차트 렌더 단계에서 검사할 수 있다. `guard.mjs` 가 리포 안에서 한 일을 helm-deploy 에서 한 번 더 하는 것이다.

**2) 부팅 시 자기 배선을 스스로 신고하게 만들기 (수십 분).** 리포에는 이미 `KafkaConsumptionStartupNotice` 라는 클래스가 있다. 컨슈머를 가진 서비스가 기동 시 "나는 이 그룹으로 이 토픽들을 구독한다"를 로그/지표로 뱉게 하고, 아무것도 구독하지 않으면 WARN 을 남기게 하면 2장의 공백이 **런타임에 스스로 드러난다.** 외부 감시자를 늘리는 것보다 값싸다.

**3) 토픽을 `KafkaTopic` CR 로 끌어오고 `auto.create.topics.enable=false` (반나절).** Strimzi 공식 권고이자, 파티션 수·보존 기간이 Git 밖에서 결정되는 문제의 근본 해결이다. 단 순서가 중요하다 — 자동 생성을 먼저 끄면 CR 없는 토픽에 발행하는 서비스가 깨진다. **CR 먼저, 스위치는 나중.**

**4) 복제 계수 (자원 필요).** 브로커 3대는 홈랩에서 PVC 3개와 JVM 3개를 더 쓴다. 당장 못 한다면 **최소한 기록은 해야 한다.** ADR 한 장이면 된다 — "RF=1 은 자원 제약에 의한 의식적 선택이며, 그 대가는 브로커 노드 손실 시 미소비 이벤트의 유실이고, Outbox 보존 기간이 그 복구 창이다." 3장의 코드 주석("개발/데모용")이 프로덕션에 붙어 있는 상태보다는 훨씬 낫다.

---

## 7. 한 줄

**정합성을 기계로 강제하기 시작하면, 남은 결함은 전부 그 기계의 사정거리 밖으로 이사한다.**

settlement 는 리포 안쪽을 아주 잘 막아놨다. 계약 테스트 37개, 커밋 훅 린트, 3단 멱등. 그래서 오늘 남은 카프카 결함은 코드에 하나도 없었고 — Helm 환경변수 한 줄, 브로커 기본값 두 개, 사흘 전에야 Git 에 들어온 CR 하나였다.

다음에 강제 장치를 하나 더 만든다면, 코드 안쪽이 아니라 **층과 층 사이**에 놓는 게 맞다.

---

## References

**1차·공식 출처**

- Apache Kafka 4.2, [Producer Configs — `acks`](https://kafka.apache.org/42/generated/producer_config.html) : `acks=all` 의 보장 범위와 "at least one in-sync replica remains alive" 조건.
- Apache Kafka 4.2, [Topic Configs — `min.insync.replicas`](https://kafka.apache.org/42/generated/topic_config.html) : ISR 크기와 `acks=all` 의 관계, RF=3 / min.insync=2 권장 시나리오.
- Spring for Apache Kafka, [Message Listener Containers](https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/message-listener-container.html) : `concurrency` 가 파티션 수를 넘을 때 잉여 컨슈머가 유휴가 되는 이유(`RangeAssignor`).
- Spring for Apache Kafka, [Handling Exceptions](https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html) : `CommonErrorHandler` / `DeadLetterPublishingRecoverer`.
- Strimzi, [Introducing the Unidirectional Topic Operator](https://strimzi.io/blog/2023/11/02/unidirectional-topic-operator/) (2023-11-02, Federico Valeri) : UTO 사용 시 `auto.create.topics.enable: false` 권고.
- Strimzi, [Topic Operator reference](https://github.com/strimzi/strimzi-kafka-operator/blob/main/documentation/modules/operators/ref-operator-topic.adoc) : `KafkaTopic` CR 없이 브로커에 직접 만들어진 토픽은 Topic Operator 의 관리 대상이 아님.
- Chris Richardson, [Pattern: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html) : dual-write 문제와 outbox 해법의 정본 정의.

**본인 실측 / 리포 원문 (재현 가능한 명령·경로까지만 주장)**

- 2026-08-13, `kubectl exec -n kafka lemuel-dual-role-0 -- bin/kafka-consumer-groups.sh --list|--describe`, `bin/kafka-configs.sh --entity-type brokers --describe --all`, `bin/kafka-get-offsets.sh`, `kubectl exec -n settlement-prod <pod> -- env | grep -i kafka`, `kubectl get kafkatopic -A`.
- settlement 리포 `origin/develop` — `docs/adr/0003-transactional-outbox-pattern.md`, `0005-kafka-vs-application-events.md`, `0017-kafka-consumer-dlt-and-replay.md`, `0024-event-contract-as-code.md`, `shared-common/.../config/kafka/KafkaConfig.java`, `company-service/.../UserRegisteredEventConsumer.java`, `scripts/harness/guard.mjs`.
- helm-deploy 리포 `origin/master` — `infra-ssd/kafka-cluster.yaml`(파일 머리말의 52일 NotReady 사고 기록), `infra-ssd/kafka-broker.yaml`.
- **트래픽이 거의 없는 포트폴리오 환경이므로 성능·장애에 대한 주장은 하지 않는다.** 지적한 항목 중 실제 사고로 이어진 것은 5.2 하나뿐이며, 나머지는 "아직 발현되지 않은 상태 불일치"다.

**같은 시스템, 다른 시선**

- [카프카 구조는 설계도가 아니라 브로커에 남는다 — settlement 토픽 38개를 실측해 다시 그렸다]({% post_url 2026-08-13-settlement-kafka-runtime-structure-measured %}) — 이 글이 "무엇이 강제하나"를 봤다면, 그 글은 "브로커에 무엇이 남아 있나"를 본다.

[^outbox]: Chris Richardson, "Pattern: Transactional outbox", <https://microservices.io/patterns/data/transactional-outbox.html>

[^kafka-acks]: Apache Kafka 4.2 Documentation, "Producer Configs — acks", <https://kafka.apache.org/42/generated/producer_config.html>

[^kafka-misr]: Apache Kafka 4.2 Documentation, "Topic Configs — min.insync.replicas", <https://kafka.apache.org/42/generated/topic_config.html>

[^spring-concurrency]: Spring for Apache Kafka Reference, "Message Listener Containers", <https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/message-listener-container.html>

[^strimzi-uto]: Federico Valeri, "Introducing the Unidirectional Topic Operator", Strimzi Blog, 2023-11-02, <https://strimzi.io/blog/2023/11/02/unidirectional-topic-operator/>

[^strimzi-to]: Strimzi, "Topic Operator" reference documentation, <https://github.com/strimzi/strimzi-kafka-operator/blob/main/documentation/modules/operators/ref-operator-topic.adoc>
