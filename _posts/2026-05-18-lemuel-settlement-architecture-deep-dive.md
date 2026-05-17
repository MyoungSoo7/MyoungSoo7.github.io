---
layout: post
title: "Lemuel 정산 플랫폼 아키텍처 분석 — 모노-MSA 하이브리드, Outbox, 헥사고날, Triple Idempotency"
date: 2026-05-18 02:00:00 +0900
categories: [backend, architecture]
tags: [java, spring-boot, msa, hexagonal, outbox, kafka, archunit, dlq, idempotency, ci-cd, k8s]
---

5월 17일 새벽, 내 정산 프로젝트(코드명 **Lemuel**) 의 구조를 다시 들여다봤다. 헥사고날·이벤트 드리븐·MSA 같은 키워드를 *말로만* 쓰는 게 아니라 **실제로 어떻게 구현됐는지** 코드 단위로 검증하는 게 목적이었다.

이 글은 그 분석 결과를 5개 주제로 정리한다.

> ⚠️ 보안 — IP, 비밀번호, 토큰, 내부 도메인은 모두 redacted. 구조와 패턴만 공유.

---

## TL;DR — 5가지 인사이트

| # | 주제 | 핵심 발견 | 왜 흥미로운가 |
|---|---|---|---|
| 1 | **모노-MSA 하이브리드** | settlement-service 가 *library jar* 로 빌드돼 order-service 의 fat jar 에 번들. Application class 가 둘의 패키지를 모두 scan. | 진짜 MSA 분리 비용을 미루는 *Phase B* 전략. compile 시점엔 한 덩어리, deploy 시점도 한 덩어리 — 하지만 도메인 경계는 살아있음 |
| 2 | **Transactional Outbox** | PENDING → PUBLISHED 상태머신 + 배치 폴링 + Micrometer 4종 메트릭 + DLQ. shared-common 모듈에 격리. | 트랜잭션과 이벤트 발행의 *원자성* 을 보장하는 production-grade 구현. |
| 3 | **ArchUnit 헥사고날 강제** | 3가지 룰 + 명시적 예외 화이트리스트. 도메인은 Spring 의존 금지, application은 JPA 직접 금지, adapter는 cross-domain 의존 금지. | 룰을 "원칙" 으로만 두지 않고 *컴파일러처럼* 강제. 예외는 문서화. |
| 4 | **Triple Idempotency** | (1) outbox event_id unique → (2) processed_events PK → (3) DB UNIQUE 제약. 어느 하나 뚫려도 다음 레이어가 막음. | "at-least-once 메시징 + idempotent 수신" 표준 패턴의 교과서적 구현. |
| 5 | **CI/CD + K8s** | 멀티스테이지 Dockerfile + `--build-arg MODULE` 로 3 서비스 한 이미지 빌더, Gradle 캐시 마운트, ArgoCD GitOps. | 빌드 시간 최적화 + 단일 Dockerfile 로 다중 산출물. |

기술 스택: **Java 25 + Spring Boot 4.0.4 + PostgreSQL 17 + Elasticsearch 8.17 + Redpanda(Kafka) + Flyway V34**.

---

## 1. 모노-MSA 하이브리드 — *물리적으론 mono, 논리적으론 MSA*

### 1.1 발견의 출발 — order-service 가 settlement-service 에 compile 의존?

처음 `order-service/build.gradle.kts` 를 봤을 때 위화감을 느꼈다.

```kotlin
dependencies {
    implementation(project(":shared-common"))
    implementation(project(":settlement-service"))     // ← MSA 인데 컴파일 의존?
    ...
}
```

MSA 면 서비스간 통신은 HTTP/이벤트로 해야 하는데 왜 *compile-time* 의존이 있나? 순환 의존 함정?

### 1.2 진실 — settlement-service 는 library jar

`settlement-service/build.gradle.kts`:

```kotlin
// Library mode: settlement-service 는 order-service 의 fat jar 에 번들된다.
// MSA 분리 배포(원래 의도)는 Phase B 에서 helm/CI 분리와 함께 재도입 예정.
tasks.named<BootJar>("bootJar") {
    enabled = false                       // ← bootJar 비활성화
}
tasks.named<Jar>("jar") {
    enabled = true
    archiveClassifier.set("")             // ← plain jar 만 산출
}
```

그리고 `order-service/LemuelApplication.java`:

```java
@SpringBootApplication(
    scanBasePackages = {
        "github.lms.lemuel.user",
        "github.lms.lemuel.order",
        "github.lms.lemuel.payment",
        // ...
        // settlement-service 모듈 (임시 번들). ledger 는 prod DB 에 테이블 미생성이라 제외.
        "github.lms.lemuel.settlement",
        "github.lms.lemuel.pgreconciliation",
        "github.lms.lemuel.payout",
        "github.lms.lemuel.chargeback",
    }
)
```

**한 JVM 이 두 서비스의 빈을 모두 로드**. 하지만 패키지 경계로 도메인은 분리된 채.

### 1.3 왜 이런 구조인가 — 전략적 점진 마이그레이션

> *"Phase B 에서 helm/CI 분리"* — 코멘트가 그대로 설계 의도를 드러낸다.

| Phase | 상태 | 트레이드오프 |
|---|---|---|
| **A (현재)** | 한 fat jar 에 두 서비스. compile 의존 OK. | 운영 단순, deploy 1 회. 진짜 MSA 격리 없음 |
| **B (계획)** | separate bootJar + helm chart + CI 분리. | 진짜 MSA. 운영 복잡도 ↑ |

핵심 인사이트: **MSA 는 단번에 가는 게 아니라 점진적이다.** 도메인 경계 (패키지/헥사고날) 부터 먼저 그어두고, 운영 비용을 감당할 준비가 되면 물리 분리 (배포 단위) 로 확장. 거꾸로 가면 monolith 의 entanglement 가 그대로 microservices 의 entanglement 로 옮겨감.

### 1.4 코드로 강제되는 도메인 경계

physical separation 이 없는 만큼 *logical* separation 을 더 엄격히 강제한다 — section 3 (ArchUnit) 에서 자세히.

### 1.5 보너스 — ledger 도메인의 흥미로운 처리

```java
@EntityScan(basePackages = {
    // ledger 패키지 entity 가 자동 스캔되지 않도록 명시 — ledger_entries 테이블이 prod 에 없어
    // Hibernate schema validation 실패. Phase B 에서 V47 마이그레이션 추가 후 복귀.
    "github.lms.lemuel.cart",
    "github.lms.lemuel.category",
    // ... (ledger 제외)
})
```

코드는 있는데 DB 스키마는 아직 — 의도적 *반쪽 배포* 상태. 다음 Flyway 마이그레이션 (V47) 에서 활성화 예정. 이런 *"코드 ready, 스키마 wait"* 패턴은 큰 조직에서 자주 보이는 점진적 롤아웃 기법이다.

---

## 2. Transactional Outbox 패턴 — Production-grade 구현

### 2.1 문제 정의 — *DB 커밋과 이벤트 발행의 원자성*

```java
@Transactional
void capturePayment(...) {
    paymentRepository.save(payment);       // DB 커밋
    kafkaPublisher.publish(paymentEvent);  // ← 여기서 죽으면? DB 는 살아남고 이벤트는 유실
}
```

이게 *Dual Write* 문제. 해법 — *같은 트랜잭션에 outbox row 쓰고, 별도 프로세스가 발행*.

### 2.2 shared-common 모듈에 격리

`shared-common/` 의 outbox 패키지 구조:

```
common/outbox/
├── domain/
│   ├── OutboxEvent.java
│   └── OutboxEventStatus.java     # PENDING | PUBLISHED | FAILED
├── application/
│   ├── port/in/  OutboxAdminUseCase.java
│   ├── port/out/
│   │   ├── LoadOutboxEventPort.java
│   │   ├── SaveOutboxEventPort.java
│   │   ├── PublishExternalEventPort.java
│   │   └── PublishDlqEventPort.java
│   └── service/
│       ├── OutboxPublisherScheduler.java    # 폴러
│       ├── OutboxAdminService.java
│       └── TraceContextCapture.java         # OTel context 보존
└── adapter/
    ├── in/
    │   ├── web/OutboxAdminController.java   # admin API
    │   └── kafka/ProcessedEventJpaEntity.java   # 멱등성 추적
    └── out/
        ├── persistence/OutboxEventPersistenceAdapter.java
        └── event/
            ├── KafkaOutboxPublisher.java        # 운영
            ├── ApplicationEventOutboxPublisher.java  # local dev
            ├── KafkaDlqPublisher.java
            └── NoOpDlqPublisher.java            # 비활성화 시
```

OutboxPublisherScheduler 핵심 로직:

```java
@Component
public class OutboxPublisherScheduler {
    private static final int BATCH_SIZE = 100;

    @Scheduled(fixedDelay = ...)
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    void publishBatch() {
        List<OutboxEvent> pending = loadOutboxEventPort.findPending(BATCH_SIZE);
        for (OutboxEvent event : pending) {
            try {
                publishExternalEventPort.publish(event);   // Kafka 발행
                event.markPublished();
                saveOutboxEventPort.save(event);
            } catch (Exception e) {
                if (event.exceededRetryLimit()) {
                    publishDlqEventPort.publish(event);    // DLQ
                    dlqCounter.increment();
                }
                event.markFailed(e);
                saveOutboxEventPort.save(event);
            }
        }
    }
}
```

### 2.3 Micrometer 메트릭 4종

```java
@PostConstruct
void registerMetrics() {
    Gauge.builder("outbox.pending.count", pendingGauge, AtomicLong::get)
            .description("outbox_events 테이블의 PENDING 건수")
            .register(meterRegistry);
    Gauge.builder("outbox.failed.count", failedGauge, AtomicLong::get)
            .description("outbox_events 테이블의 FAILED 건수 (DLQ 알람 대상)")
            .register(meterRegistry);
    publishTimer = Timer.builder("outbox.publish.duration")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(meterRegistry);
    dlqCounter = Counter.builder("outbox.dlq.published")
            .description("DLQ 로 발행된 누적 이벤트 수 (재시도 한계 초과)")
            .register(meterRegistry);
}
```

이 4개로 운영 대시보드/알람 만들기 충분:

- `outbox.pending.count` 가 계속 증가 → 폴러가 못 따라감 → 알람
- `outbox.failed.count > 0` → DLQ 적재됨 → 즉시 조사
- `outbox.publish.duration{quantile="0.99"}` → 외부 시스템 latency 추적
- `outbox.dlq.published_total` → DLQ 누적량 → SLO 계산

### 2.4 인사이트 — Outbox 는 "패턴" 이 아니라 "인프라"

shared-common 에 추출해서 양 서비스가 의존. 새 도메인 추가될 때 *"outbox 도 신경써야 하나?"* 가 사라짐 — domain event 만 publish 하면 인프라가 알아서.

---

## 3. ArchUnit 으로 헥사고날 강제 — 룰 + 화이트리스트

### 3.1 헥사고날 패키지 구조 (모든 도메인 동일)

```
<domain>/
├── adapter/
│   ├── in/web/        REST Controller + request/response DTO
│   └── out/persistence/  JPA Entity + Repository + Adapter
├── application/
│   ├── port/in/       UseCase 인터페이스 (driver port)
│   ├── port/out/      External 의존 인터페이스 (driven port)
│   └── service/       UseCase 구현 (Application Service)
└── domain/            순수 비즈니스 로직 (POJO)
```

### 3.2 룰 3가지

`HexagonalArchitectureTest.java`:

```java
@Test
void domainShouldNotDependOnSpringOrJpa() {
    noClasses().that().resideInAPackage("..domain..")
        .and().resideOutsideOfPackage("..adapter..")
        .and().resideOutsideOfPackage("..application..")
        .should().dependOnClassesThat().resideInAnyPackage(
            "org.springframework..",
            "jakarta.persistence..",
            "javax.persistence..")
        .because("도메인 레이어는 프레임워크에 의존하지 않는 순수 POJO 여야 한다")
        .check(mainClasses);
}

@Test
void applicationServiceShouldNotUseJpaRepositoryDirectly() {
    noClasses().that().resideInAPackage("..application.service..")
        .should().dependOnClassesThat().resideInAPackage("..adapter.out.persistence..")
        .because("애플리케이션 서비스는 어댑터(JPA)에 직접 의존하지 않고 포트를 사용해야 한다")
        .check(mainClasses);
}

@Test
void adaptersShouldNotDirectlyReferenceOtherDomainsPersistence() {
    noClasses().that().resideInAPackage("..adapter..")
        .and().doNotHaveSimpleName("SettlementSearchDocumentMapper")
        .and().doNotHaveSimpleName("SettlementQueryRepositoryImpl")
        .and().doNotHaveSimpleName("CapturedPaymentsAdapter")
        .should(dependOnClassesThat(crossDomainPersistence()))
        .because("어댑터는 타 도메인의 JPA 엔티티/리포지토리를 직접 import 하지 않는다. "
                + "CQRS 읽기/집계 전용 클래스는 명시적 허용 목록으로 관리")
        .check(mainClasses);
}
```

### 3.3 인사이트 — "예외 0 개" 가 목표가 아니다

룰 정의에 **명시적 예외 화이트리스트**:

| 클래스 | 이유 |
|---|---|
| `EcommerceCategoryService`, `ProductImageService` | application.service 인데 JPA 직접 의존 — *리팩터 TODO* |
| `SettlementSearchDocumentMapper` | Elasticsearch 인덱싱용 read-model — CQRS 의 read side |
| `SettlementQueryRepositoryImpl` | QueryDSL 크로스 엔티티 조인 — 성능 지향 |
| `CapturedPaymentsAdapter` | 정산 생성 시 결제 데이터 읽기 — read-only projection |

이게 *현실적인 ArchUnit 운영*. "예외 0" 은 이상이지만 *현실엔 의도된 예외* 가 있다 (CQRS 읽기 모델, 성능 최적화). 예외를 *허용하되 코드로 명시* 해야 사람이 까먹지 않고 새 예외가 무지성으로 추가되는 걸 막을 수 있음.

### 3.4 한 단계 더 — 매 PR 마다 자동 실행

```kotlin
// build.gradle.kts
testImplementation("com.tngtech.archunit:archunit-junit5:1.3.0")

tasks.test {
    useJUnitPlatform()
    // ArchUnit 위반은 빌드 실패로 처리
}
```

CI 가 `./gradlew test` 돌면 ArchUnit 도 실행 → 위반 시 PR 머지 차단. **룰이 코드가 되고, 코드가 게이트가 된다.**

---

## 4. Event Flow End-to-End + Triple Idempotency

### 4.1 결제 → 정산 흐름

```
[1] order-service (REST API)
       │
       │ POST /api/payments (Toss Webhook)
       ▼
   PaymentService.capture()
       │
       │ @Transactional
       ├──► payments 테이블 INSERT
       └──► outbox_events INSERT (event_type=PAYMENT_CAPTURED)
                                    └─ event_id: UUID (unique)
                                       payload: JSON

[2] OutboxPublisherScheduler (shared-common)
       │
       │ 매 N초 마다 PENDING 조회
       ▼
   KafkaOutboxPublisher.publish()
       │
       │ Kafka topic: payment-captured
       ▼

[3] settlement-service (Kafka Consumer)
       │
       │ @KafkaListener(topics="${app.kafka.topic.payment-captured}")
       ▼
   PaymentEventKafkaConsumer.consume()
       │
       │ @Transactional
       ├──► processed_events 조회 (idempotency check)
       │      └─ 이미 처리됐으면 ack & return
       ├──► CreateSettlementFromPaymentUseCase.execute()
       │      └──► settlements INSERT (payment_id UNIQUE)
       ├──► processed_events INSERT (consumer_group + event_id)
       └──► Kafka ack
```

### 4.2 Triple Idempotency — 3중 방어

```java
/**
 * 멱등성 3 단 방어:
 *   1. outbox event_id UUID unique — 프로듀서 측 중복 발행 방지
 *   2. processed_events(consumer_group, event_id) PK — 컨슈머 측 재수신 방지
 *   3. settlements.payment_id UNIQUE (V3) — 스키마 수준 최종 방어
 */
```

| 레이어 | 막는 것 | 어떻게 |
|---|---|---|
| 1. Producer | 중복 outbox row | `event_id UUID UNIQUE` 제약 |
| 2. Consumer | Kafka 의 at-least-once 재전송 | `processed_events(group_id, event_id) PRIMARY KEY` 사전 조회 |
| 3. Schema | 위 둘 다 뚫린 race condition | `settlements.payment_id UNIQUE` insert 거부 |

**왜 3겹인가?** Kafka 의 at-least-once 보장 + 분산 컨슈머 + retry/replay 가능성 → 단일 방어선은 race condition 에 뚫림. 깊이 방어 (defense in depth) 가 분산 시스템의 정수.

### 4.3 DLT (Dead Letter Topic) 분리 — 일시적 vs 독성

```java
@KafkaListener(
    topics = "${app.kafka.topic.payment-captured}",
    groupId = "lemuel-settlement",
    // ...
)
public void consume(ConsumerRecord<String, byte[]> record, Acknowledgment ack) {
    // 처리 로직
    // - 일시적 예외 → throw → ExponentialBackOff(2s ×2, 3회) → DLT
    // - JsonProcessingException / IllegalArgumentException / IllegalStateException
    //   → 재시도 없이 즉시 DLT — 같은 파티션의 후속 메시지 stall 방지
}
```

**핵심 운영 통찰**: 모든 예외를 같이 처리하면 *독성 메시지 1개* 가 *수천 메시지* 의 처리를 막을 수 있음 (Kafka 파티션 순서 보장 때문에). 예외 종류별로 *재시도 vs 즉시 DLT* 분리가 필수.

`KafkaErrorHandlerConfig` 에서 `DefaultErrorHandler` + classifier 로 구현.

### 4.4 DLQ Replay

`DlqReplayService` 가 있음 — DLT 토픽의 메시지를 admin 액션으로 *재처리*. 운영 중에 일시적 외부 의존성 (PG 사 점검) 으로 누적된 DLT 를 복구 시점에 한 번에 흘려보내기.

---

## 5. CI/CD + K8s 배포

### 5.1 단일 Dockerfile, 3 서비스 빌드

```dockerfile
# Stage 1: Build (parameterized)
#   docker build --build-arg MODULE=order-service .
#   docker build --build-arg MODULE=settlement-service .
#   docker build --build-arg MODULE=gateway-service .
FROM gradle:9.1.0-jdk25 AS builder
ARG MODULE
WORKDIR /workspace

# 의존성 캐싱: 변경 적은 파일 먼저
COPY settings.gradle.kts build.gradle.kts ./
COPY gradle ./gradle
COPY shared-common/build.gradle.kts ./shared-common/
COPY order-service/build.gradle.kts ./order-service/
COPY settlement-service/build.gradle.kts ./settlement-service/
COPY gateway-service/build.gradle.kts ./gateway-service/

RUN --mount=type=cache,target=/home/gradle/.gradle \
    gradle --no-daemon :${MODULE}:dependencies || true

# 전체 소스 복사
COPY shared-common ./shared-common
COPY order-service ./order-service
COPY settlement-service ./settlement-service
COPY gateway-service ./gateway-service

RUN --mount=type=cache,target=/home/gradle/.gradle \
    gradle --no-daemon :${MODULE}:bootJar -x test

RUN find /workspace/${MODULE}/build/libs -maxdepth 1 -name '*.jar' \
    ! -name '*-plain.jar' -exec cp {} /workspace/app.jar \;

# Stage 2: Runtime
FROM eclipse-temurin:25-jre-alpine
RUN apk add --no-cache curl tini ghostscript
RUN addgroup -S spring && adduser -S spring -G spring
...
```

**좋은 점**:

1. **단일 Dockerfile 로 3 산출물** — `--build-arg MODULE=` 로 분기. 유지보수 1곳.
2. **레이어 캐싱 최적화** — build.gradle.kts 먼저 복사 → dependencies 캐시. 소스만 바뀐 빌드는 deps 다운로드 skip.
3. **BuildKit cache mount** — `--mount=type=cache,target=/home/gradle/.gradle` 로 Gradle 캐시 컨테이너 간 공유. CI 재빌드 5분 → 30초.
4. **runtime 분리** — JDK 빌더 (큰 이미지) 와 JRE Alpine (작은 이미지) 분리. 최종 이미지 200MB 대.
5. **non-root user** — `spring` 사용자로 실행, security best practice.
6. **tini PID 1** — graceful shutdown 지원, zombie process 회수.
7. **ghostscript** — iText PDF 가 PostScript 폰트 처리 시 필요.

### 5.2 K8s 배포 — ArgoCD GitOps

```
k8s/
├── argocd/           ArgoCD Application 매니페스트
├── base/             공통 Kustomize base (Deployment, Service, ConfigMap)
├── ingress/          Ingress 라우팅 (gateway 외부 노출)
├── security/         NetworkPolicy, RBAC
└── storage/          PVC (PostgreSQL, ES 데이터)
```

- ArgoCD App-of-Apps 패턴 (별도 [helm-deploy 레포](https://github.com/MyoungSoo7/helm-deploy) 에서 관리)
- Kustomize overlays 로 prod/staging 분리
- 별도 frontend 디렉토리 — nginx 컨테이너로 SPA 호스팅

### 5.3 CI 워크플로우 (2개)

| 파일 | 역할 |
|---|---|
| `.github/workflows/ci.yml` | main push → 빌드 + 테스트 (ArchUnit 포함) + GHCR 푸시 + ArgoCD Image Updater 가 감지해 자동 rollout |
| `.github/workflows/pr-review.yml` | PR open → Claude AI 코드 리뷰 |

`ci.yml` 에 `paths-filter` 가 있어 frontend 만 변경되면 백엔드 빌드 skip — *변경 영역만 빌드* 패턴.

---

## 마무리 — 이 프로젝트에서 배울 점 5가지

### 1. **MSA 는 진화 단계의 산물**

"우린 MSA 야" 보다 "**우린 지금 Phase A 의 모노-MSA 하이브리드고, Phase B 에서 물리 분리할 예정이야**" 가 훨씬 솔직하고 운영 가능한 설명. *진짜 MSA 비용* 을 감당할 준비 (CI 분리, helm chart 분리, 분산 트랜잭션 처리) 가 되기 전엔 *논리 분리* 만 먼저 강제.

### 2. **인프라성 패턴은 shared 모듈에**

Outbox 를 매 도메인마다 구현하면 *지옥*. shared-common 에 격리 → 새 도메인은 `domain event publish` 만 하면 끝.

### 3. **ArchUnit 화이트리스트 = 정직한 운영**

"룰 0 예외" 는 이상이고 *현실엔 의도된 예외* 가 있다 (CQRS, 성능). 이상을 추구하되 *예외를 코드로 명시* 해야 사람이 까먹지 않음.

### 4. **분산 시스템엔 깊이 방어**

at-least-once 메시징 + 분산 컨슈머 = *반드시* 중복 처리 가능성. 단일 방어선은 race condition 에 뚫림. *3겹 멱등성* (producer + consumer + schema) 이 표준.

### 5. **빌드 최적화는 캐시 게임**

레이어 캐싱 (build.gradle.kts 먼저) + BuildKit cache mount + 멀티스테이지 + non-root + tini PID1 — 이 5가지가 *production-grade* Dockerfile 의 기본기. 5분 빌드를 30초로.

---

> **TL;DR** — 이 프로젝트의 진짜 가치는 *"MSA 라고 부르기"* 가 아니라 *"왜, 어디까지, 어떻게 MSA 화 할지 의식적으로 결정한 흔적"* 이 코드에 남아있다는 것. Phase A → Phase B 라는 명시적 로드맵, ArchUnit 예외 화이트리스트, Outbox 의 shared 모듈화 — 모두 *지금 완벽하지 않다는 걸 인정하고 다음 단계를 준비한* 결과물. 그게 포트폴리오의 진솔함이다.

---

### 부록 — 분석에 쓴 명령

```bash
# 모노-MSA 하이브리드 확인
grep -r "github.lms.lemuel.settlement" --include="*.java" order-service/

# ArchUnit 룰
cat order-service/src/test/java/.../HexagonalArchitectureTest.java

# Outbox 구조
find shared-common/src/main/java -path "*outbox*"

# Kafka 컨슈머
cat settlement-service/src/main/java/.../PaymentEventKafkaConsumer.java

# Dockerfile 분석
cat Dockerfile
```
