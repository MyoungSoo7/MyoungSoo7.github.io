---
layout: post
title: "이커머스 + 정산 MSA 를 *왜* / *어떻게* 분리했나 — Hexagonal · Outbox · Read-only Projection · K3s GitOps 까지 한 production 서비스의 *전 구조*"
date: 2026-06-07 00:50:00 +0900
categories: [architecture, msa, kubernetes, gitops]
tags: [hexagonal, msa, bounded-context, outbox, kafka, read-only-projection, archunit, spring-boot, gradle-multi-module, k3s, argocd, image-updater, cloudflare-tunnel, gitops]
---

운영 중인 *이커머스 + 정산 MSA 플랫폼* 한 개를 *전 layer 한 번에* 풀어 본다. 모놀리스에서 시작해 **Bounded Context 분리 → 이벤트 드리븐 → Read-only Projection** 으로 진화시킨 백엔드와, 그것이 *어떻게 K3s 위에서 GitOps 로 굴러가는지* 까지. 도메인 분할의 *근거*, 헥사고날의 *경계*, Outbox 의 *멱등*, 그리고 *production K3s* 의 ArgoCD/Image-updater/Cloudflare Tunnel 까지 — 하나의 그림 안에서 *왜 그 선택을 했는가* 를 정리한다.

이 글은 **(1) 왜 MSA 로 갔나** — *서비스 분리의 근거*, **(2) 기술 스택과 그 선택 이유**, **(3) Gradle 멀티 모듈 구조와 shared-common 의 역할**, **(4) 헥사고날 + ArchUnit 으로 *경계를 컴파일 타임에 강제* 하기**, **(5) Read-only Projection — MSA 의 *코드 의존성 0*** , **(6) Outbox + Kafka + 3 단 멱등 방어**, **(7) K3s production 배포 구조 — GitOps · ArgoCD · Image-updater · Cloudflare Tunnel**, **(8) 운영상 약점 5 가지와 개선 방향** 순으로 다룬다.

---

## TL;DR

**도메인.** Commerce (주문/결제/상품) + Settlement (정산/대사/리포트) 의 *SLA·장애 격리·배포 주기* 가 서로 달라서 *서비스 분리*. 즉 *우리는 MSA 를 원해서 한 게 아니라 두 컨텍스트가 같이 살기 어려워서 분리* 한 것.

**경계 강제.** Hexagonal (Ports & Adapters) + ArchUnit 으로 *컴파일 타임에* 의존 방향 검증. `domain → application → adapter` 외에는 못 가는 *물리적 잠금*.

**서비스 간 통신.** *코드 의존 0*. Settlement 가 Order 의 코드를 *import 하지 않고도* Order/Payment/User/Product 를 읽어야 해서, 두 가지로 분리: *조회* 는 **Read-only Projection** (`@Immutable JpaEntity` 로 같은 테이블 매핑), *변경 이벤트* 는 **Outbox + Kafka**. 결과: settlement-service 의 `build.gradle.kts` 에 `implementation(project(":order-service"))` 가 없다.

**멱등.** Outbox 의 *3 단 방어선*. `outbox_events.event_id UNIQUE` → `processed_events PK (group, event_id)` → 비즈니스 unique 제약 (`settlements.payment_id UNIQUE`). 어느 하나가 뚫려도 다음이 막는다.

**배포.** K3s + ArgoCD (GitOps) + argocd-image-updater (newest-build). 외부 노출은 *Cloudflare Tunnel* 로 — Ingress 안 쓰고 *NodePort + Tunnel 진입* 으로 단순화.

**약점.** prod replicaCount=1 (SPOF), Elasticsearch local-path (노드 종속), backend memory 1Gi (OOM 마진 좁음). 인지하고 단계적 개선 중.

---

## 1. 왜 MSA 로 갔나 — *서비스 분리의 근거*

> *"단순히 도메인이 두 개라서" 가 아니라 *동거할 수 없는 이유* 가 있어서.*

처음엔 *단일 모놀리스* 였다. user/order/payment/settlement/report 가 같은 jar 안에 있었고 배포도 같이 됐다. MSA 로 가른 이유는 다음 *4 차원의 차이* 가 동시에 누적됐기 때문이다.

| 차원 | Commerce | Settlement |
|---|---|---|
| **컨텍스트** | *거래* (Transactional) | *백오피스* (Back-Office) |
| **SLA** | 사용자 응답 latency 우선 — P99 < 300ms | *정합성·일관성* 우선 — 1초 늦어도 됨, *틀리면 안 됨* |
| **데이터 패턴** | 쓰기 중심 (CRUD) | 읽기·집계 중심 (Batch + Search) |
| **장애 격리** | settlement 다운돼도 결제는 계속돼야 함 | settlement 배치는 *언제든 비동기* — 즉시 처리 X |
| **배포 주기** | 잦음 (UI 변경 동행) | 드뭄 (회계 사이클 단위, 월 1~2 회) |

특히 *"settlement 가 멈춰도 결제는 계속돼야 한다"* 가 결정타. 모놀리스였을 때는 settlement 의 ES 색인 hang 하나로 결제 트랜잭션이 같이 줄을 섰다. *"우리는 MSA 를 원해서 한 게 아니라, 두 컨텍스트가 같이 살기 어려워서 분리한 것"* — *이 한 줄이 모든 결정의 출발점*.

---

## 2. 기술 스택과 그 선택 이유

| 분류 | 기술 | 채택 이유 |
|---|---|---|
| 언어 | Java 25 | LTS + Virtual Threads (Loom) 활용. JVM 익숙도 |
| 프레임워크 | Spring Boot 4.0.4 | 기본기 + 생태계. Boot 4 의 새 옵저버빌리티 |
| 빌드 | Gradle Multi-module (Kotlin DSL) | 4 모듈 의존 그래프를 *타입 안전* 하게 |
| API Gateway | Spring Cloud Gateway | 라우팅 + 인증 필터, *MSA 단일 진입점* |
| DB | PostgreSQL 17 | JSONB / partial index / partitioning / `gen_random_uuid()` |
| 검색 | Elasticsearch 8.17 | 정산 검색·집계 (월 단위 매출 / 셀러별 합계) |
| 메시지 | Kafka (Redpanda 호환) | Outbox 발행 채널. Redpanda 는 JVM-less 라 노드 가벼움 |
| PG 연동 | Toss Payments | 결제 PG (실서비스 동일) |
| 배치 | Spring Batch | 월간 정산 / PG 대사 |
| 캐시 | Caffeine | local in-memory, jvm bound. Redis 불필요한 수준 |
| PDF | iText 8 | 정산서 PDF |
| 모니터링 | Micrometer + Prometheus | metrics export 표준 |
| 마이그레이션 | Flyway (V1~V34) | 정수 번호 순차, 트레이서블 |
| 회복탄력성 | Resilience4j | Circuit Breaker / Retry / Timeout / Bulkhead |
| Rate Limiting | Bucket4j | Token bucket, JVM in-process |

**눈에 띄는 선택 두 가지.**

**Redpanda over Vanilla Kafka.** 가벼운 노드, JVM 없음, Kafka API 100% 호환. 자가 운영 클러스터에서 *Kafka 운영 부담* (Zookeeper / KRaft / partition rebalance 학습 곡선) 을 크게 줄임. Outbox 의 publish 채널로만 쓰니까 Redpanda 의 단순함이 더 잘 맞는다.

**Caffeine over Redis.** 사용자 50~100명 규모에서는 *프로세스 내부 캐시* 로 충분. Redis 띄우려면 별도 노드/HA/persistence 까지 다 따라온다. *우리가 풀어야 할 문제가 그만큼 크지 않다* 면 *덜 띄우는 게 정공*.

---

## 3. Gradle 멀티 모듈 구조와 shared-common 의 역할

```
project-root/                       # Gradle 멀티 모듈 루트
├── settings.gradle.kts             # 4 모듈 선언
├── build.gradle.kts                # 부모 빌드 (subprojects 공통 설정)
├── shared-common/                  # 📦 java-library: 양 서비스가 의존
│   └── io.example.app.common.{audit, config, exception, outbox, ratelimit, pdf}
├── order-service/                  # 🛒 Commerce 서비스 (port 8088)
│   └── io.example.app.{user, order, payment, product, category, coupon, review}
├── settlement-service/             # 💰 Settlement 서비스 (port 8082)
│   └── io.example.app.{settlement, report}
└── gateway-service/                # 🚪 API Gateway (port 8080)
```

**shared-common 에 무엇을 넣고 무엇을 안 넣는가** — 이게 가장 어려운 결정이다. 잘못하면 모놀리스로 회귀한다.

| ✅ shared-common 안에 넣는다 | ❌ shared-common 에 *절대* 안 넣는다 |
|---|---|
| `BaseEntity` (id, createdAt, updatedAt, deletedAt) | 도메인 모델 (User, Order, Payment, Settlement) |
| `JpaConfig` (OSIV off, naming strategy) | 비즈니스 로직 |
| `GlobalExceptionHandler` (ErrorCode 표준) | DTO / Request / Response |
| `OutboxEntity` + 폴러 abstract | 도메인 이벤트 정의 (각 서비스 자체에) |
| JWT 검증 필터 | 인증 정책 (각 서비스가 자기 권한 매트릭스 보유) |
| Rate Limiter | 엔드포인트 정책 |
| PDF 렌더링 유틸 | 정산서 양식 (settlement-service 안에) |

원칙: *"여러 서비스가 동일하게 쓰는 *횡단 관심사*만 shared-common* — *도메인은 절대 공유 X"*. 이 원칙을 어기는 순간 *서비스를 분리한 의미가 사라진다*.

---

## 4. 헥사고날 + ArchUnit 으로 *경계를 컴파일 타임에 강제*

각 서비스 내부 구조:

```
{service}/src/main/java/io/example/app/{domain}/
├── domain/              # 도메인 모델 (POJO, *프레임워크 의존 0*)
├── application/
│   ├── port/in/         # 인바운드 포트 (UseCase 인터페이스)
│   ├── port/out/        # 아웃바운드 포트 (영속성/외부 서비스)
│   └── service/         # UseCase 구현
└── adapter/
    ├── in/web/          # REST 컨트롤러
    ├── in/kafka/        # Kafka 컨슈머 (settlement-service)
    ├── in/batch/        # Spring Batch (settlement-service)
    ├── out/persistence/ # JPA 리포지토리, 엔티티
    ├── out/external/    # PG 클라이언트 (Toss)
    ├── out/event/       # Outbox-backed Kafka publisher
    ├── out/readmodel/   # ★ Read-only projection (settlement-service 전용)
    ├── out/search/      # ES 색인
    └── out/pdf/         # iText PDF
```

이걸 *컨벤션 + 코드 리뷰* 로 지키는 건 한계가 있다. 한 PR 만 *피로* 해도 `domain` 이 Spring 을 import 하기 시작한다. 그래서 **ArchUnit** 으로 *컴파일·테스트 타임에* 강제한다:

```java
@AnalyzeClasses(
    packages = "io.example.app",
    importOptions = ImportOption.DoNotIncludeTests.class
)
class HexagonalArchitectureTest {

    @ArchTest
    static final ArchRule 도메인은_프레임워크를_의존하지_않는다 =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "org.springframework..",
                "jakarta.persistence..",
                "..adapter..",
                "..application.."
            );

    @ArchTest
    static final ArchRule application_은_JPA_엔티티를_직접_쓰지_않는다 =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat()
            .areAnnotatedWith(jakarta.persistence.Entity.class);

    @ArchTest
    static final ArchRule adapter_는_다른_도메인의_adapter_를_의존하지_않는다 =
        noClasses().that().resideInAPackage("..order.adapter..")
            .should().dependOnClassesThat().resideInAPackage("..settlement.adapter..");
}
```

이 테스트가 *CI 의 일부* 라 PR 에서 헥사고날 위반은 *merge 자체가 안 된다*. *코드 리뷰어가 사람일 때 놓치는 것을 컴파일러가 잡아준다* — 이게 *내가 ArchUnit 을 좋아하는 단 하나의 이유*.

---

## 5. Read-only Projection — *MSA 의 코드 의존성 0*

**문제.** Settlement 가 *정산서* 를 만들려면 Order/Payment 의 정보 + User/Product 의 이름이 필요하다. 가장 쉬운 길은 settlement-service 가 `implementation(project(":order-service"))` 를 추가하고 `OrderRepository` 를 직접 쓰는 것. 그런데 그 순간 *"MSA 라고 부르면서 두 서비스가 같은 모놀리스 안에 있는 것과 다를 게 없다"* 가 된다.

**해법.** *조회* 만 필요하니까 *Read-only Projection* — settlement-service 안에 *별도의 `@Immutable` JpaEntity* 를 정의하고 *같은 테이블에 매핑* 한다.

```java
package io.example.app.settlement.adapter.out.readmodel;

@Entity
@Immutable
@Table(name = "payments")  // ★ order-service 의 같은 테이블
public class SettlementPaymentReadModel {
    @Id private Long id;
    private Long orderId;
    private Long userId;
    private BigDecimal amount;
    private String status;       // CAPTURED, REFUNDED, ...
    private Instant capturedAt;

    // 기본 생성자만, setter 없음, 비즈니스 메서드 없음
}

public interface SettlementPaymentReadModelRepository
    extends Repository<SettlementPaymentReadModel, Long> {
    Optional<SettlementPaymentReadModel> findById(Long id);
    List<SettlementPaymentReadModel> findByCapturedAtBetween(Instant from, Instant to);
}
```

특징:

- `@Immutable` 이라 *변경 트래킹 안 함*. 1차 캐시·dirty checking 비용 0
- *setter 없음* — 변경 의도 자체가 없음을 명시
- *order-service 의 Payment 와 클래스 자체가 다름* — 이름/패키지 모두 분리
- settlement-service 의 `build.gradle.kts` 에 `implementation(project(":order-service"))` **여전히 없음**

**원리.** 두 서비스가 *같은 DB · 같은 테이블* 을 공유한다는 *물리* 사실은 그대로 두되, *코드 의존성* 만은 끊는다. 즉 *DB 가 통신 채널이 되는 게 아니라 Read-only projection 의 매핑 대상* 일 뿐. 변경은 절대 양쪽에서 일어나지 않는다 — *쓰기 권한은 order-service 만, settlement-service 는 영원히 read-only*.

**언제 안 맞나.** *서로 다른 DB* 가 되는 순간 이 패턴은 못 쓴다. 그땐 *이벤트 + materialized view* 가 정공. 하지만 단일 DB 모놀리스에서 MSA 로 *서서히 분리* 하는 중간 단계에서는 *압도적으로 가성비가 좋다*.

---

## 6. Outbox + Kafka + 3 단 멱등 방어

*조회* 는 Read-only Projection 으로 풀었다면, *상태 변화의 전파* 는 이벤트로 보낸다. *결제가 캡쳐* 되면 *정산이 생성* 돼야 한다. 이걸 *trustworthy* 하게 만드는 게 **Outbox 패턴 + 3 단 멱등 방어**.

### 6-1. Publish 측 — Transactional Outbox

```
[order-service] Payment.capture() (DB transaction)
    ├─ payments.status = CAPTURED
    └─ outbox_events INSERT (aggregateId, eventType, payload)
                       ↑ 같은 DB transaction 안. 둘 다 commit 아니면 둘 다 rollback.
                       ↓ (poller 2초 주기 별도 스레드)
                   PENDING → PUBLISHED 상태 머신
                       ↓
                   Kafka topic: example.payment.captured
```

*같은 트랜잭션 안에서* "비즈니스 변경" 과 "이벤트 발행 의도" 를 함께 적는다. *Kafka 가 죽어 있어도 일단 이벤트는 DB 에 남는다*. 별도 폴러가 PENDING 상태인 outbox row 를 발견하면 Kafka 로 발행하고 PUBLISHED 로 상태 전환. *at-least-once 보장*.

### 6-2. Consume 측 — 3 단 멱등 방어

```
[settlement-service] PaymentEventKafkaConsumer
    ├─ 1. outbox_events.event_id UUID UNIQUE   ← Publish 측 중복 방지
    ├─ 2. processed_events PK (consumer_group, event_id)  ← Consume 측 중복 방지
    └─ 3. settlements.payment_id UNIQUE         ← 비즈니스 unique 방어
```

**Layer 1.** *발행자 측 unique*. 같은 event_id 로 다시 INSERT 시도 시 DB 가 거부 → outbox 가 중복 발행하지 않는다.

**Layer 2.** *컨슈머 측 명시적 멱등*. 컨슈머가 처리할 때마다 `processed_events (group, event_id)` 에 *비즈니스 트랜잭션과 함께* INSERT. 같은 event 가 다시 들어와도 PK 위반으로 거부 → skip. *Kafka rebalance 로 같은 메시지가 두 번 들어와도 비즈니스는 한 번만 수행*.

**Layer 3.** *비즈니스 자연 unique*. `settlements.payment_id` 컬럼에 UNIQUE 제약. *코드/메시징 layer 가 모두 뚫려도* DB 자연키가 마지막으로 막는다.

*"3 단 방어선이 다 뚫리는 경우 = 우리가 정산 시스템의 DB 자연 키를 잘못 잡았다"* — 이는 *데이터 모델링 버그* 이지 *메시징 버그가 아니다*. 즉 *책임 layer 가 명확하게 분리* 된다.

### 6-3. Micrometer 4 종 메트릭

운영 가능한 시스템이 되려면 메트릭이 따라와야 한다. 우리는 outbox 에 *4 가지 메트릭* 을 단다:

- `outbox.pending.count` — *현재 PENDING 인 outbox row 수*. 늘어나면 Kafka 가 안 가고 있는 것.
- `outbox.publish.duration` — *DB 폴 → Kafka send → PUBLISHED 까지의 latency*. P99 가 늘어나면 백프레셔.
- `outbox.publish.failure` — *연속 발행 실패 카운터*. DLQ 도 따라옴.
- `outbox.dlq.count` — *3 회 재시도 실패 후 DLQ 에 던진 수*. 0 이 아니면 알람.

Grafana 에서 이 4 개만 봐도 *Outbox 가 건강한지* 한눈에 들어온다.

---

## 7. K3s production 배포 구조

GitHub 의 helm chart → ArgoCD → K3s 까지 *완전 자동* 의 GitOps 파이프라인이다.

### 7-1. 전체 그림

```
GitHub: helm-deploy 레포 (charts/<app>)
            ↓ 변경 push
        ArgoCD Application
        ├─ syncPolicy.automated: { prune: false, selfHeal: true }
        ├─ retry: 3 회 / 10s → 5m 백오프
        └─ destination.namespace: <app>-prod (CreateNamespace=true)
            ↓
K3s 클러스터 (자가 호스트)
        ↓                 ↑ image-updater (newest-build)
        ↓                 ↑   ghcr.io/<owner>/<app>:<tag>
   namespace: <app>-prod
        ├─ Deployment: backend (Spring Boot)
        ├─ Deployment: frontend
        ├─ StatefulSet: Elasticsearch
        ├─ Service NodePort: backend (30088), frontend (30087)
        └─ external PostgreSQL: <db>-postgres.<db>-prod.svc
            ↓
    Cloudflare Tunnel (cloudflared)
            ↓
    api.example.com (사용자)
```

### 7-2. 핵심 4 가지 결정

**(A) Ingress 안 쓴다 — Cloudflare Tunnel + NodePort.** K3s 의 ingress-nginx 를 굳이 운영하지 않는다. 이유:

- TLS 종료를 *Cloudflare 에서* 하기 때문에 ingress 의 cert-manager / Let's Encrypt 부담 0
- DDoS / WAF 도 Cloudflare 가 무료 layer 에서 처리
- 진입점 IP 가 *집 공인 IP 가 아니라 Cloudflare* — 노출 surface 최소화

대신 Service 가 *NodePort* 로 떠 있고, cloudflared 가 그 NodePort 로 forwarding 한다.

**(B) ArgoCD syncPolicy `prune: false`.** *helm chart 에서 리소스를 제거* 했을 때 *자동으로 클러스터에서 지우지 않는다*. 안전 마진. 대신 분기에 한 번씩 *수동 prune* 으로 garbage 정리.

**(C) argocd-image-updater `update-strategy: newest-build`.** GHCR 에 새 이미지가 올라오면 그중 *빌드 시각 최신* 을 골라 자동 sync. *지난 5월 한 번 두 PR 의 빌드 결과가 거의 동시에 push 되면서 *fix 가 묻혔던* 사고가 있었음. 이후 *외부 검증* (실제 외부 도메인에 served bytes 확인) 을 파이프라인에 추가했다.

**(D) PodAntiAffinity + PDB.** *preferredDuringSchedulingIgnoredDuringExecution* (강제 아닌 선호) 로 *같은 호스트에 같은 컴포넌트 2 개 안 뜨게*. 단, prod replicaCount=1 이라 *지금은 의미 없는 설정* (의도된 idempotent — 나중에 replica 늘리면 자동으로 활성).

---

## 8. 운영상 약점 5 가지와 개선 방향

운영하다 보면 *문서에 안 적힌 약점* 이 드러난다. 솔직하게 적어둔다.

| # | 약점 | 영향 | 개선안 |
|---|---|---|---|
| 1 | prod replicaCount=*1* (backend/frontend) | SPOF — pod 1 개 죽으면 503 | 2 로 올리고 메모리 limit 1Gi → 1.5Gi |
| 2 | Elasticsearch local-path PVC | 노드 종속, 노드 사고 시 인덱스 영구 손실 | 분산 storage (longhorn / openebs) 또는 snapshot 정책 |
| 3 | backend memory limit 1Gi + JVM 75% heap | 트래픽 늘면 OOMKilled 마진 좁음 | 1.5Gi 또는 heap 60% 로 더 안전한 비율 |
| 4 | argocd image-updater `prune: false` 와 newest-build 조합 | helm 에서 지운 리소스가 클러스터에 남음 | 분기 수동 prune 또는 selective auto-prune |
| 5 | etcd quorum 노드 중 *2 대가 노트북* | sleep / WiFi 끊김 → raft 불안정 → control-plane CPU 폭증 | 데스크톱/iDRAC 서버로 master 재구성 (별도 글) |

특히 **#5 가 가장 큰 부채** 였고, *2026-06-06 의 CPU 부하 알림* 의 진짜 원인. K3s control-plane HA 를 *노트북 2 대 + 데스크톱 1 대* 로 구성했던 *초기 임시 설계* 가 누적 부채가 됐다. 데스크톱 3 대 또는 iDRAC 서버 추가로 재구성 예정.

---

## 9. 이 구조에서 얻은 *6 개의 교훈*

### 9-1. *"왜 MSA 인가" 는 도메인이 답한다, 트렌드가 아니다*

서비스가 두 개라서가 아니라 *두 컨텍스트가 같이 살 수 없는 4 가지 이유* (SLA / 데이터 패턴 / 장애 격리 / 배포 주기) 가 누적돼서다. 이 답이 안 나오면 MSA 안 가는 게 답.

### 9-2. *Hexagonal 은 컨벤션이 아니라 컴파일러로 강제하는 것*

ArchUnit 없이 헥사고날을 *지키는* 건 거의 불가능. *코드 리뷰어가 사람일 때 놓치는 것을 컴파일러가 잡는다*.

### 9-3. *Read-only Projection 은 MSA 의 *과도기* 정공*

*같은 DB 를 여전히 공유* 하는 단계에서 *코드 의존성 0* 을 만들어 주는 가성비 최고의 패턴. 별도 DB 로 가야 하는 시점이 되면 자연스럽게 *이벤트 + materialized view* 로 이행.

### 9-4. *Outbox 는 1 단으로 절대 부족하다*

3 단 (publish unique → consume PK → 비즈니스 unique) 으로 짠다. 어느 layer 만 보고 *"이거 멱등이에요"* 라 하면 *언젠가 중복* 이 발생. *Layer 가 책임을 나눠 갖는다*.

### 9-5. *작은 클러스터에서는 *덜 띄우는 게 정공**

Redis 안 띄우고 Caffeine. ingress-nginx 안 띄우고 Cloudflare Tunnel. *우리가 풀어야 할 문제가 그만큼 크지 않다* 면 *덜 띄우는 것이 정공*.

### 9-6. *production K3s 의 *물리* 가 가장 비싼 부채*

코드는 git revert 로 되돌릴 수 있지만 *master 노드가 노트북이라는 사실* 은 *Kubernetes 명령으로는 못 되돌린다*. *물리 결정* 은 *코드 결정* 보다 항상 더 비싸다는 걸 운영하면서 배웠다.

---

## 마무리

*이커머스 + 정산* 이라는 *흔한 도메인* 을 *어떻게 풀었는가* — *왜 MSA 인지부터 K3s 의 NodePort 까지* 한 줄로 이어 봤다. 흥미로운 건 *어디 한 layer 가 도드라지지 않는다* 는 점. 도메인 분할의 근거가 약하면 헥사고날도 의미 없고, ArchUnit 이 없으면 헥사고날은 무너지고, Outbox 의 3 단 멱등이 없으면 결제·정산이 어긋난다. *각 layer 의 결정이 직전 layer 의 결정을 정당화* 한다.

다음 글 후보 — *(a) K3s control-plane 을 노트북에서 데스크톱/iDRAC 서버로 옮기는 zero-downtime 이전기*, *(b) Outbox 의 3 단 멱등 방어 구현 디테일 + 운영 메트릭 4 종 코드 레벨*, *(c) Read-only Projection 으로 DB 를 분리할 때의 *마지막 단계* — 별도 DB + Debezium CDC* 중 하나.

*"우리가 짠 코드보다, 우리가 *왜 그 코드를 그렇게 짰는가* 가 더 오래 남는다"* — 이 글이 *6 개월 뒤의 나에게 *왜 그랬는지* 를 다시 설명* 해 줄 것이다. 가장 좋은 문서화는 *결정의 근거를 적는 것*.
