---
layout: post
title: "*3 형제 *마이크로서비스* — *OMS · WMS · LMS* 를 *헥사고날 + GitOps + Outbox 로 *2 일 만에 *0 → 운영*'까지'"
date: 2026-06-05 18:30:00 +0900
categories: [architecture, microservices, hexagonal, kubernetes, gitops]
tags: [oms, wms, lms, spring-boot, java-21, hexagonal, ddd, outbox, gitops, k3s, argocd, image-updater]
---

> *''*마이크로서비스를 *제대로 *해본 적이 *있는가?""*. *모든 *시니어 *백엔드가 *한 번쯤 *받는 *질문이다. 책으로 *읽은 *것과 *블로그에서 *본 *것을 *제외하면, *''*진짜로 *돌리고 *진짜로 *상태 추적하고 *진짜로 *서로 *호출 하는 *3 개 이상의 *서비스를 *처음부터 *끝까지 *내가 *세팅 해 본 *경험""* 이 *흔하지 *않다.
>
> 이 글은 *2 일 *동안 *0 에서 시작해 *3 개의 *물류 마이크로서비스 — **OMS** (Order Management System), **WMS** (Warehouse Management System), **LMS** (Logistics Management System) — 를 *Spring Boot 3.4 + Java 21 + 헥사고날 *아키텍처로 *각자 *별도 *리포에 *짓고, *각자 *전용 *PostgreSQL 을 *띄우고, *K3s 클러스터에 *GitOps 로 *자동 *배포하고, *3 서비스가 *내부 *DNS 로 *서로 *호출 하는 *e2e 시나리오 까지 *검증한 *전 과정*의 *기술 회고다.

대상은 *''*마이크로서비스를 *진짜 *돌려보고 싶은 *백엔드 *시니어""*, *''*헥사고날 / Outbox / GitOps 가 *실제로 *어떻게 *맞물려 *돌아가는지 *궁금한 *모든 *개발자""*, 그리고 *''*3 시스템이 *서로 *느슨하게 *결합 *한다는 게 *진짜 *어떤 *모양인가""* 가 *궁금한 *사람.

---

## 1. *왜 *이 3 시스템 인가*

물류 도메인의 *3 형제 *시스템은 *각자 *책임이 *명확히 *다르고 *서로 *의존하는 *전형적인 *마이크로서비스 *패턴이다.

```
[OMS] order-oms              [WMS] warehouse-wms          [LMS] logistic-lms
─────────────                ──────────────                ───────────
▶ 채널 주문 수령              ▶ PickOrder 생성              ▶ Shipment 생성
  (자사몰/쿠팡/네이버)          ▶ 피킹·패킹 워크플로우          ▶ 배차 (driver+vehicle)
▶ 재고 할당                   ▶ Stock 도메인                ▶ Driver App (라스트마일)
                                                              ▶ PoD (Proof of Delivery)
```

이 *3 개를 *고른 *이유:

1. **책임이 *완전히 *다름** — *각자 *별도 *DB 가 *자연스러움
2. **순서가 *명확** — *OMS → WMS → LMS 의 *단방향 흐름
3. **이벤트 *발행이 *자연스러움** — *각 *상태 *변경이 *다음 *시스템에 *알림 *필요
4. **모두 *실무에서 *수십억 *원 *돌리는 *진짜 도메인** — 학습 *예제가 *아님

---

## 2. *기술 *스택의 *일관성 — *3 서비스 *완전 동일*

3 서비스 *모두 *같은 *스택을 *썼다. *이게 *''*세 형제""* 라 부를 만한 *진짜 *이유다.

```
Spring Boot   3.4
Java          21 (Virtual Threads 활성)
ORM           JPA (Hibernate)
DB            PostgreSQL 17 (각자 전용)
Migration     Flyway V1__initial_schema.sql
패턴           헥사고날 (domain / application / adapter)
이벤트         Transactional Outbox + Polling Publisher
어댑터         Webhook / Kafka / Noop (ConditionalOnProperty 로 *교체)
인프라         K3s + ArgoCD + ghcr.io + Image Updater
검증           ArchUnit 5 룰 × 3 서비스 = 15 룰
```

**왜 *일관성이 *중요한가**:

- 다음 *서비스를 *복제할 때 *기존 *패턴 *그대로 *재사용 → *WMS 만드는 데 *LMS 의 *3 분의 1 시간
- 신규 입사자가 *한 서비스 *익히면 *나머지 *2 도 *즉시 *이해
- 운영 *대시보드·알람·로그가 *동일 *지표

> **격언**: *''*마이크로서비스의 *진짜 *비용은 *''*N 개의 *다른 스택""* 이지 *''*N 개의 *서비스""* 가 *아니다""*.

---

## 3. *헥사고날 *3 계층 — *세 서비스 *모두 *동일 *구조*

```
서비스/
├── domain/                      ← Spring·JPA 의존 0 (pure Java)
│   ├── Aggregate Root
│   ├── Value Objects (Money, Address, Sku, ...)
│   ├── FSM (Status enum + canTransitionTo)
│   └── event/ (DomainEvent 구현체)
├── application/
│   ├── port/in/  (UseCase 인터페이스)
│   ├── port/out/ (Repository 인터페이스)
│   └── service/  (@Service @Transactional)
└── adapter/
    ├── in/web/   (REST Controller + DTO)
    └── out/persistence/ (JPA Entity + Mapper)
```

**ArchUnit 5 룰 — *컴파일러처럼 *강제**:

```java
@ArchTest static final ArchRule domain_isFrameworkFree =
    noClasses().that().resideInAPackage("..domain..")
        .should().dependOnClassesThat().resideInAnyPackage(
            "org.springframework..", "jakarta.persistence..",
            "com.fasterxml.jackson..", "..adapter..", "..application..");

@ArchTest static final ArchRule layersFlowInward =
    layeredArchitecture().consideringOnlyDependenciesInLayers()
        .layer("Domain").definedBy("..domain..")
        .layer("Application").definedBy("..application..")
        .layer("Adapter").definedBy("..adapter..")
        .whereLayer("Adapter").mayNotBeAccessedByAnyLayer()
        .whereLayer("Application").mayOnlyBeAccessedByLayers("Adapter")
        .whereLayer("Domain").mayOnlyBeAccessedByLayers("Application", "Adapter");
```

**3 서비스 × 5 룰 = 15 ArchUnit 룰** 이 *CI 의 *모든 *PR 마다 *돌면서 *''*도메인이 *Spring 을 *모름""* 의 *원칙을 *지킨다.

---

## 4. *Aggregate 와 *FSM — *3 서비스의 *7 도메인 *Aggregate*

각 *서비스의 *Aggregate Root 와 *상태 *전이:

### OMS — *Order Aggregate*
```
RECEIVED → ALLOCATED → DISPATCHED → SHIPPED → DELIVERED
              ↓ CANCELED                    ↓ REFUNDED
```

### WMS — *PickOrder Aggregate + Stock Aggregate*
```
PickOrder: CREATED → PICKING → PICKED → PACKED → DISPATCHED → CANCELED
Stock:     onHand / reserved 분리. adjust 가 reservation invariant 깨면 거절.
```

### LMS — *Shipment + Driver + Vehicle + Delivery (4 Aggregate)*
```
Shipment:  RECEIVED → DISPATCHED → IN_TRANSIT → DELIVERED → FAILED → CANCELED
Delivery:  ASSIGNED → ACCEPTED → IN_PROGRESS → COMPLETED → FAILED → CANCELED
```

**FSM 의 *2 가지 *효용**:

1. **불법 *전이 *컴파일러처럼 *차단** — `if (!status.canTransitionTo(next)) throw`
2. **상태 변경의 *''*무엇""* 이 *코드 *한 곳에 *집중** — 흩어진 *if 문 *지옥 *방지

---

## 5. *Transactional Outbox — *3 서비스의 *공통 *심장*

가장 *복사 *많이 한 *코드는 *Outbox 패턴이다. **3 서비스가 *완전히 *같은 *14 개의 *클래스를 *공유** 한다 (패키지명만 *다름):

```
shared/outbox/
├── DomainEvent              (interface — Aggregate 가 발행)
├── OutboxEntry              (record — DB row 표현)
├── OutboxStatus             (PENDING / PUBLISHED / FAILED)
├── OutboxRepository         (interface)
├── OutboxJpaEntity          (JPA)
├── OutboxSpringDataRepository
├── JpaOutboxRepository      (implementation)
├── EventSerializer          (interface)
├── JacksonEventSerializer   (impl)
├── EventPublisherPort       (interface ← *교체 지점)
├── OutboxPublisher          (@Scheduled 1초 폴링)
├── WebhookEventPublisher    (@ConditionalOnProperty webhook)
├── KafkaEventPublisher      (@ConditionalOnProperty kafka)
└── NoopEventPublisher       (@ConditionalOnExpression 둘 다 비활성)
```

**EventPublisherPort 의 *진짜 *효용**:

```yaml
# Webhook 모드
webhook.enabled: true
kafka.enabled: false

# Kafka 모드 — 도메인 코드 0 줄 수정
webhook.enabled: false
kafka.enabled: true

# Noop fallback — 둘 다 비활성
webhook.enabled: false
kafka.enabled: false
```

**3 서비스가 *각자 *독립적으로 *전송 *방식 *결정**. *OMS 는 *Webhook, *WMS 는 *Kafka, *LMS 는 *둘 다 — 같은 *클러스터에서 *공존 가능.

---

## 6. *Triple Idempotency — *cross-service 멱등성의 *3 층*

at-least-once 메시징의 *피할 수 *없는 *''*중복 *발행""* 을 *3 층 *방어선 으로 *막는다.

| Layer | 위치 | 동작 |
|---|---|---|
| **L1** | `outbox_events.event_id UNIQUE` | 같은 이벤트 *두 번 *발행 X (발행측 책임) |
| **L2** | 수신측 `processed_events PK` | 수신측이 *두 번 *처리 X |
| **L3** | 비즈니스 자연키 UNIQUE | 어떤 *경로로 *와도 *DB 가 *차단 |

3 서비스의 *L3 자연키:

- **OMS**: `(channel, channel_order_ref)` UNIQUE — 쿠팡 *주문이 *두 번 *수령 X
- **WMS**: `external_reference` UNIQUE — OMS 의 *같은 *order id 를 *두 번 *PickOrder 화 X
- **LMS**: `external_reference` UNIQUE — *''*OMS-{id}""* 또는 *''*WMS-{id}""* 가 *두 번 *Shipment 화 X

**핵심 *발견**: WMS 가 *LMS 에 *호출할 때 `externalReference="WMS-{poId}"` 로 *prefix 함. 만약 *OMS 가 *직접 LMS 호출 한다면 `externalReference="OMS-{id}"`. *Prefix 가 *다르므로 *L3 UNIQUE 가 *충돌 *없음.

---

## 7. *3 서비스 *연동 — *''*OMS → WMS → LMS""* 의 *진짜 *순서*

### 7.1 *초기 *시도 — *OMS 가 *LMS 직결*

처음엔 *''*OMS allocate → LMS shipment 생성""* 으로 *시작했다. 빠르고 *단순한 *통합. 그러나 *진짜 *현실은 *''*WMS 가 *피킹 / 패킹 / 출고 워크플로우를 *처리한 *다음에야 *LMS 호출""* 이 *맞다.

### 7.2 *현재의 *흐름 — *진짜 *3 단 *체인*

```
1. OMS POST /api/v1/orders                    (채널이 push)
   ↓ Order RECEIVED + 저장
2. OMS POST /api/v1/orders/{id}/allocate      (분배 API)
   ↓ greedy single-warehouse 알고리즘
   ↓ WarehouseWmsAdapter.dispatch()
3. WMS POST /api/v1/pick-orders              (WMS 에 PickOrder 생성)
   ↓ PickOrder CREATED + 저장
4. WMS POST /pick-orders/{id}/start-picking
   ↓ PickOrder PICKING
5. WMS POST /pick-orders/{id}/pick (× N)
   ↓ 라인별 binCode 기록
6. WMS POST /pick-orders/{id}/complete-picking
   ↓ PickOrder PICKED
7. WMS POST /pick-orders/{id}/complete-packing
   ↓ PickOrder PACKED
8. WMS POST /pick-orders/{id}/dispatch
   ↓ LogisticLmsShipmentAdapter.dispatch()
9. LMS POST /api/v1/shipments                 (LMS 에 Shipment 생성)
   ↓ Shipment RECEIVED + 저장
```

**9 단계가 *모두 *내부 *DNS 로 *cross-namespace HTTP**:

```
order-oms-prod-app.order-oms-prod.svc.cluster.local
warehouse-wms-prod-app.warehouse-wms-prod.svc.cluster.local
logistic-lms-prod-app.logistic-lms-prod.svc.cluster.local
```

---

## 8. *GitOps — *3 서비스 *3 리포 + 1 인프라 *리포*

마이크로서비스의 *''*리포 폭증""* 함정은 *유명하다. 우리의 *해법은 *명확한 *분리:

```
서비스 *리포 3 개:
- github.com/MyoungSoo7/order-oms
- github.com/MyoungSoo7/warehouse-wms
- github.com/MyoungSoo7/logistic-lms

인프라 *리포 1 개:
- github.com/MyoungSoo7/helm-deploy
  ├── charts/order-oms/         (Helm chart)
  ├── charts/warehouse-wms/
  ├── charts/logistic-lms/
  └── argocd-applications/
      ├── order-oms-prod.yaml
      ├── warehouse-wms-prod.yaml
      └── logistic-lms-prod.yaml
```

**완전 *자동화된 *파이프라인**:

```
개발자 push  → github.com/MyoungSoo7/order-oms (main)
                  ↓
GitHub Actions     test + bootJar + Docker build
                  ↓
ghcr.io/myoungsoo7/order-oms:sha-{short}
                  ↓
ArgoCD Image Updater  (newest-build 전략)
                  ↓
helm-deploy 의 *app.image.tag *자동 *업데이트
                  ↓
ArgoCD            Diff 감지 → sync → Pod rolling update
                  ↓
새 버전 *자동 *배포 (사람 *개입 0)
```

**3 서비스 *동시에 *같은 *파이프라인** — *''*복제 *비용 *0""* 의 *진짜 *의미.

---

## 9. *실제 *검증 — *e2e 시나리오*

다음 *시나리오를 *cluster 내부에서 *돌렸다:

```bash
# STEP 1: OMS 에 *주문 *수령
curl -X POST http://order-oms.../orders -d '{
  "channel":"COUPANG",
  "channelOrderRef":"CP-INTEG-001",
  "items":[
    {"sku":"SKU-A","quantity":2,"unitPrice":20000},
    {"sku":"SKU-B","quantity":1,"unitPrice":35000}
  ],
  ...
}'
→ 201 Created, id=1e6fb4ed-..., status=RECEIVED, totalAmount=75000

# STEP 2: OMS 분배 (WMS 호출)
curl -X POST http://order-oms.../orders/1e6fb4ed-.../allocate
→ {"warehouseId":"WH-DEFAULT","success":true,"reason":"ok pickOrder=a4e688e0-..."}

# STEP 3: WMS 워크플로우
curl -X POST http://warehouse-wms.../pick-orders/a4e688e0-.../start-picking
curl -X POST http://warehouse-wms.../pick-orders/a4e688e0-.../pick -d '{"sku":"SKU-A","binCode":"A-01-01-01","quantity":2}'
curl -X POST http://warehouse-wms.../pick-orders/a4e688e0-.../pick -d '{"sku":"SKU-B","binCode":"A-01-01-02","quantity":1}'
curl -X POST http://warehouse-wms.../pick-orders/a4e688e0-.../complete-picking
curl -X POST http://warehouse-wms.../pick-orders/a4e688e0-.../complete-packing

# STEP 4: WMS → LMS dispatch
curl -X POST http://warehouse-wms.../pick-orders/a4e688e0-.../dispatch
→ {"downstreamShipmentId":"71dbb28d-..."}  ← LMS 의 진짜 shipment ID

# STEP 5: LMS 확인
curl http://logistic-lms.../shipments/71dbb28d-...
→ externalReference: "WMS-a4e688e0-..."   ← WMS-prefix 확인
   status: RECEIVED
```

**핵심 *발견**:

1. *9 단계 *모두 *200 / 201 응답* — 한 번에 *통과
2. **3 PG 에 *각자 *기록* — Order / PickOrder / Shipment 가 *자기 DB 에
3. **L3 UNIQUE 가 *멱등성 *보장** — 같은 *주문 *재요청 시 *기존 ID 반환

---

## 10. *Outbox 활성화 — *Noop 에서 *Webhook 으로 *전환*

초기에는 *3 서비스의 *outbox 가 *모두 *FAILED 상태로 *쌓였다 (NoopEventPublisher 가 *명시적으로 *throw, 5 회 *재시도 후 *FAILED).

```sql
-- outbox_events 테이블
event_type       | status | attempt_count
-----------------+--------+--------------
order.received   | FAILED |      5
order.allocated  | FAILED |      5
```

**Webhook 활성화 — env var 만 *변경**:

```yaml
WEBHOOK_ENABLED: "true"
WEBHOOK_URL: "https://httpbin.org/post"
WEBHOOK_SECRET: "demo-secret"
```

helm-deploy push → ArgoCD sync → rolling restart → 다음 *outbox 이벤트부터 *PUBLISHED.

**도메인 *코드 *0 줄 *수정** — 헥사고날 + EventPublisherPort 추상화의 *진짜 *효용. *Kafka 로 *바꾸는 *것도 *동일한 *방식.

---

## 11. *PostgreSQL 인 *이유 (MySQL 이 *아닌)*

3 서비스 *모두 *PostgreSQL 을 *선택한 *이유:

- **jsonb 우수** — 도메인 *직렬화 라인을 *TEXT 가 *아닌 jsonb 로 *확장 가능
- **Flyway *트랜잭션 *DDL** — 마이그레이션 *실패 시 *완벽 *롤백
- **pgvector** — *향후 *주문 *추천 / 유사 *주문 *검색 *대비
- **Range 타입** — *재고 *유효기간, 가격 *유효기간 *자연 *표현
- **SQL 표준 *준수** — *''*편의 위해 *표준 *어김""* 케이스 *적음

> **현장 *발견**: 2026 년 기준 *Stack Overflow *조사에서 *PostgreSQL 이 *MySQL 을 *역전 (51% vs 41%). *신규 *프로젝트의 *기본값이 *바뀌고 *있다.

---

## 12. *3 시스템 *총 *통계*

| 항목 | 수치 |
|---|---|
| 마이크로서비스 | 3 (OMS / WMS / LMS) |
| GitHub 리포 (서비스) | 3 |
| GitHub 리포 (인프라) | 1 (helm-deploy) |
| Helm 차트 | 3 |
| ArgoCD Application | 3 (Image Updater 자동 sync) |
| K3s 네임스페이스 | 3 (-prod 접미사) |
| PostgreSQL 인스턴스 | 3 (각자 5Gi PVC) |
| 동시 운영 *Pod | 6 (3 app + 3 db) |
| Aggregate Root | 7 (Order / PickOrder / Stock / Shipment / Driver / Vehicle / Delivery) |
| Domain Event 종류 | 12+ |
| ArchUnit 룰 | 15 (5 × 3 서비스) |
| 도메인 *테스트 *케이스 | ~25 |
| 총 *작업 *시간 | 약 *2 일 |

---

## 13. *''*마이크로서비스를 *진짜 *해봤다""* 의 *5 가지 *진실*

이 *2 일 동안 *몸으로 *배운 *것:

### 1. *''*동일 *스택의 *복제""* 가 *가장 *비싼 *자산*
3 서비스가 *같은 *Spring + Java + PG + Outbox 라서 *''*다음 서비스 *만들기""* 가 *극단적으로 *빨랐다. *''*N 개의 *다른 *스택""* 은 *''*N 개의 *재앙""*.

### 2. *''*같은 패턴의 *Outbox""* 가 *사실상 *내부 *프레임워크*
14 개 클래스의 *Outbox 패턴이 *3 서비스에 *복사 — *''*공통 *라이브러리로 *추출 *해야 *하나?""* 가 *다음 *주제. *지금은 *복사가 *복잡도 *↓.

### 3. *''*L3 자연키 UNIQUE 가 *분산 트랜잭션을 *대체""*
*Saga 같은 *복잡한 *패턴 *없이도 *''*DB 의 *자연키 UNIQUE""* 한 줄이 *''*같은 *주문이 *두 *번 *처리 X""* 를 *보장. *마법 *아님.

### 4. *''*ArgoCD Image Updater + GHA""* 의 *조합이 *진짜 *GitOps*
*코드 push → 자동 *이미지 *빌드 → 자동 *배포까지 *사람 *개입 *0. *''*Push 만 *하면 *production 에 *반영""* 의 *진짜 *모양.

### 5. *''*헥사고날의 *진짜 *효용은 *Adapter 교체에서 *드러난다""*
*Noop → Webhook → Kafka 의 *전환을 *코드 *0 줄 *수정 으로 *해 봐야 *''*아 *이게 *헥사고날이구나""* 가 *몸으로 *느껴진다.

---

## 14. *남은 *과제*

- **Cloudflare Tunnel *hostname 등록** — `oms.lemuel.co.kr`, `wms.lemuel.co.kr`, `lms.lemuel.co.kr` 외부 노출
- **Kafka 통합** — 모든 3 서비스를 *Webhook → Kafka 로 *전환 검증
- **Real Inventory** — *WMS 의 *Stock Aggregate 를 *진짜 *영속화하고 *OMS 가 *조회
- **분할 출고** — 한 *주문이 *여러 창고로 *분배되는 *케이스
- **채널 *어댑터** — 쿠팡 / 네이버 *스마트스토어 *주문 *폴링
- **모니터링** — Prometheus + Grafana 로 *3 서비스 *지표 *통합

---

## 15. *결론 — *''*N 개의 *서비스""* 가 *아니라 *''*N 개의 *경계""*

마이크로서비스의 *''*진짜""* 는 *''*많은 *서비스""* 가 *아니라 *''*잘 *나뉜 *경계""* 다.

3 형제 시스템은 *각자의 *책임이 *명확 — *OMS 는 *주문, *WMS 는 *창고, *LMS 는 *배차. *각자의 *DB 가 *완전히 *분리. *각자의 *코드 *리포가 *분리. *각자의 *배포 *주기가 *독립.

그러나 *동시에 *서로를 *모른다 — *OMS 는 *WMS 의 *내부를 *모르고, *WMS 는 *LMS 의 *내부를 *모른다. *오직 *''*어떤 *REST API 로 *호출 하는가""* 와 *''*어떤 *이벤트를 *발행 하는가""* 만 *공유. 이게 *''*느슨한 *결합""* 의 *진짜 *모양이다.

> **마지막 *한 *문장**:
>
> *''*마이크로서비스는 *''*N 개를 *돌리는 *법""* 이 *아니라 *''*N 개가 *서로를 *모르게 *돌리는 *법""* 이다. 그리고 *''*N 개가 *서로를 *모르려면""* *모두가 *같은 *언어 — 헥사고날 + Outbox + GitOps — 를 *써야 한다. *그게 *''*세 형제""* 라 *부를 만한 *진짜 *이유다.*''*

---

## 코드 / 리포

- **OMS**: https://github.com/MyoungSoo7/order-oms
- **WMS**: https://github.com/MyoungSoo7/warehouse-wms
- **LMS**: https://github.com/MyoungSoo7/logistic-lms
- **인프라 (helm-deploy)**: https://github.com/MyoungSoo7/helm-deploy

## 더 *읽으면 *좋은 *자료*

- 본 블로그의 [헥사고날·클린 *아키텍처](/2026/05/29/hexagonal-clean-architecture-ports-adapters-domain/)
- 본 블로그의 [이벤트 *아키텍처 *7 함정](/2026/05/29/event-driven-architecture-kafka-saga-outbox-patterns/)
- 본 블로그의 [Java/Spring/Hexagonal 팀 *표준](/2026/05/29/java-spring-hexagonal-domain-integrity-extensibility-team-standard/)
- Chris Richardson, **Microservices Patterns** (2018) — Saga / Outbox 의 *교과서
- Vlad Khononov, **Learning Domain-Driven Design** (2021)
- Tom Hombergs, **Get Your Hands Dirty on Clean Architecture** (2019)
- Spring Modulith 공식 *문서
- ArgoCD Image Updater 공식 *문서
