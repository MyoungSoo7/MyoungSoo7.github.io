---
layout: post
title: "서버 구조 설계 패턴 — 모놀리스 부터 헥사고날, CQRS, Saga, Service Mesh 까지"
date: 2026-06-24 01:30:00 +0900
categories: [architecture, backend, design-patterns]
tags: [architecture, monolith, microservices, hexagonal, ports-and-adapters, clean-architecture, cqrs, event-sourcing, saga, outbox, api-gateway, bff, sidecar, service-mesh, strangler-fig]
---

서버 코드 를 짜는 사람 이라면 한 번 쯤 마주치 는 질문 들이 있다. "왜 Service 클래스 가 1000 줄 이 되면 안 되나?", "Repository 는 왜 인터페이스 로 두나?", "왜 도메인 객체 가 JPA Entity 와 분리 되어야 하나?", "외부 결제 API 호출 을 어디 에 두나?" — 이 모든 질문 의 밑 에 *구조 설계 패턴* 이 있다.

이 글 은 백엔드 가 자주 마주치 는 8 가지 구조 패턴 — 모놀리스 / 헥사고날 / CQRS / Saga / Outbox / API Gateway / Service Mesh / Strangler Fig — 의 *왜*, *언제*, *어떻게* 를 정리한다. 책 의 인용 보다 *내 settlement / sparta MSA 의 실전 결정* 위주로.

---

## 1. 첫 갈림길 — 모놀리스 vs MSA vs 모듈러 모놀리스

### 모놀리스 (Monolith)
하나 의 코드베이스, 하나 의 배포 단위. 30 명 미만 의 팀 에서 *압도적 으로 합리적*. Spring Boot 의 기본 형 태.

장점:
- 트랜잭션 경계 가 단순 — `@Transactional` 한 줄
- 디버깅 / 로깅 / 배포 가 단일 시스템
- 초기 속도 빠름

단점:
- 코드 가 50K 줄 넘으면 *모듈 경계 흐려짐*
- 한 곳 의 문제 가 *전체 다운*
- 팀 N 명 이 *같은 코드 베이스* 에 PR 쌓이면 *충돌 폭주*

### 마이크로서비스 (MSA)
도메인 별 *독립 배포* + *독립 DB* + *독립 팀*. *Netflix, Amazon* 의 *2000 년대 선택*.

장점:
- 팀 별 자율성 (각자 언어 / 배포 주기 / scale)
- 서비스 단위 fault isolation (Order 서비스 죽어도 *User 서비스 살아 있음*)
- 수평 확장 의 *자연스러움*

단점 (현실):
- *분산 트랜잭션* 의 지옥 (Saga / Outbox / 2PC 필요)
- *네트워크 RTT* 추가 latency
- *운영 부담* — K8s, observability, 분산 추적 의무
- *작은 팀 (< 10 명) 에선 *유지 비용 > 효과*

### 모듈러 모놀리스 (Modular Monolith)
*최근 5 년 의 새 트렌드*. *Shopify, Spring Modulith* 의 *재발견*.

```
[하나의 배포 단위]
   ├ user 모듈 (별도 schema)
   ├ order 모듈 (별도 schema)
   ├ payment 모듈 (별도 schema)
   └ shared common
```

모듈 간 통신 은 *명시적 API* (이벤트 또는 인터페이스) 만 허용. *DB schema 도 모듈 별*. *나중 에 MSA 로 분리 시 비교적 쉬움*.

장점:
- 모놀리스 의 *운영 단순성* + MSA 의 *모듈 경계*
- *팀 50 ~ 100 명 까지 합리적*

→ 우리 settlement 도 *모듈러 모놀리스 → MSA 점진 진화*. settlement-service 가 *library jar* 로 빌드 돼서 order-service 의 fat jar 에 *번들 되는 하이브리드* 가 *그 흔적*.

### 선택 가이드
| 팀 규모 | 권장 |
|---|---|
| 1 ~ 5 명 | 모놀리스 |
| 5 ~ 30 명 | 모듈러 모놀리스 |
| 30 ~ 100 명 | 모듈러 모놀리스 → 점진 MSA |
| 100 명+ | MSA |

> *Conway's Law*: "조직 의 의사소통 구조 가 시스템 구조 를 결정한다". 팀 1 개 면 *모놀리스 가 자연*, 팀 5 개 면 *서비스 5 개 가 자연*.

---

## 2. 계층 아키텍처 (Layered) — 가장 흔한 시작점

```
Controller    ← HTTP 입출력, 검증, DTO 변환
   ↓
Service       ← 비즈니스 로직, 트랜잭션 경계
   ↓
Repository    ← DB 접근, JPA
   ↓
Entity / DB
```

장점:
- 직관적, Spring Boot 의 기본
- 학습 곡선 낮음

함정:
- *Service 가 *모든 책임 * 자석* 됨 — 결국 1000 줄
- *Entity 가 *anemic* (데이터 만, 메서드 없음) — 객체 지향 의 손실
- *Service → Repository* 의존이 *고정 방향* — 테스트 시 *모킹 의 지옥*

→ 작은 프로젝트 에선 충분. *복잡 한 도메인* 에선 *헥사고날* 로 진화.

---

## 3. 헥사고날 (Ports & Adapters)

*Alistair Cockburn, 2005*. *도메인 을 중심에 두고 *외부 (DB, API, UI) 가 *어댑터 로 *플러그 인* 한다.

```
                    ┌─────────────────────────┐
   REST API   →     │                         │
                    │      Application        │
   Kafka      →     │      (use cases)        │     →   PostgreSQL
                    │           ↑              │
   gRPC       →     │           ↓              │     →   Redis
                    │         Domain           │
                    │      (entities,          │     →   External API
                    │       value objects)     │
                    │                         │
                    └─────────────────────────┘
```

핵심:
- *Domain* 은 *Spring, JPA, Kafka 의존 0* — 순수 Java
- *Application* (use case) 은 *port (interface)* 통해 외부 와 통신
- *Adapter* 가 *port 구현* — JPA Repository, Kafka Consumer, REST Controller

장점:
- *도메인 로직 의 *테스트 단순* — 외부 mock 만 끼우면 됨
- *기술 교체 의 자유* (MySQL → PostgreSQL, REST → gRPC) — *Domain 코드 변경 0*
- *DDD 와 자연스럽게 결합*

함정:
- *학습 곡선 가파름*
- *간단한 CRUD 에 적용 시 *과잉 설계*
- *주니어 가 *어디 에 코드 두는지* 자주 혼란

settlement 의 *모듈 구조*:
```
domain/         — Order, Payment, Money 같은 도메인 객체 (Spring 의존 0)
application/    — OrderUseCase, RefundUseCase (port 정의)
adapter/
   in/web/      — REST controller
   in/kafka/    — Kafka consumer
   out/persistence/  — JPA Repository
   out/payment/      — 외부 결제 API client
```

→ *ArchUnit 으로 *경계 강제* 검증* (도메인 이 Spring import 시 빌드 fail).

---

## 4. CQRS — 읽기 와 쓰기 의 분리

*Command Query Responsibility Segregation* — *명령 (write) 모델* 과 *조회 (read) 모델* 을 *분리*.

```
[Command path]
   POST /orders → CommandHandler → Domain → Write DB
                                                ↓ event
[Query path]                              [Event Bus]
   GET /orders → QueryHandler → Read Model ←
```

장점:
- *Write 의 *정합성* 과 *Read 의 *성능* 을 *각자 최적화*
- *읽기 전용 replica*, *분석 DB*, *검색 인덱스* 를 *Read 모델* 로 채울 수 있음
- *복잡 한 도메인* 에서 *Write 의 *invariant* 와 *Read 의 *유연성* 가 *서로 충돌 안 함*

함정:
- *Eventual consistency* — *방금 쓴 데이터* 가 *읽기 모델* 에 *수 ms ~ 수 분 지연*
- *복잡도 증가* — *두 모델 의 *동기화 메커니즘 의무*
- *작은 시스템 엔 과잉*

→ sparta MSA 의 *AI 검색 (pgvector)* 이 *간단한 CQRS* — *product write 가 *PostgreSQL*, *read 는 *vector index 위 의 검색*. *write → read 동기화* 는 *Kafka 이벤트*.

---

## 5. Event Sourcing — 상태 가 아닌 *이벤트 의 적재*

*전통 DB*: 마지막 상태 만 저장. `users` 테이블 의 *현재 row*.
*Event Sourcing*: *모든 상태 변경 이벤트 의 *append-only log*. *현재 상태* 는 *이벤트 의 reduce*.

```
events:
  - UserCreated   { id: 1, name: "A" }
  - UserRenamed   { id: 1, newName: "B" }
  - UserDeleted   { id: 1 }

현재 상태 = reduce(events) → User { id: 1, name: "B", deleted: true }
```

장점:
- *완전한 audit trail* — 모든 변경 이 *영원히 기록*
- *시간 여행* — "3 일 전 의 상태 는?" → events 의 *그 시점 까지 reduce*
- *재구축 가능* — read model 망가 져도 *events 재 reduce*

함정:
- *snapshot 없으면 *수만 events reduce* — 느림
- *schema evolution* — *옛 event 형식* 과 *새 코드* 호환 의 *복잡성*
- *대부분 의 도메인 엔 *과잉*

→ *금융 / 감사 / 게임 (replay)* 같은 *특수 도메인* 에서 *진지한 선택*.

---

## 6. Event-Driven — Saga, Outbox, CDC

분산 시스템 의 *분산 트랜잭션 의 *현실 적 답* — *이벤트 기반*. 자세히는 [분산 시스템 의 본질](/2026/06/22/distributed-systems-cap-base-saga-2pc-cdc-consistency.html) 참조.

### Saga
*Long-running transaction* 을 *짧은 local 트랜잭션 의 sequence + 보상 트랜잭션* 으로 분해.

```
주문 처리:
  T1: Order 생성        — settlement-prod
  T2: 재고 감소         — inventory-prod
  T3: 결제 호출         — payment-prod
  T4: 주문 확정         — settlement-prod

실패 시 보상:
  T3 실패 → T2' (재고 복구) + T1' (Order 취소)
```

2 종류:
- **Orchestration** — 중앙 *Saga manager* 가 *모든 단계 결정*
- **Choreography** — 각 서비스 가 *이벤트 발행 / 구독* 으로 *분산 협력*

### Transactional Outbox
*Dual-write 문제* (DB 변경 + Kafka publish 사이 불일치) 를 해결.

```sql
BEGIN;
INSERT INTO orders (...) VALUES (...);
INSERT INTO outbox (event, payload, published) VALUES ('OrderCreated', ..., false);
COMMIT;
```

별도 *Outbox Relay* 가 *주기 적 으로*:
1. `SELECT * FROM outbox WHERE published = false`
2. Kafka publish
3. `UPDATE outbox SET published = true`

→ *at-least-once delivery* 보장. settlement 의 *핵심 자산*.

### CDC (Change Data Capture)
*DB 의 WAL / binlog 자체* 를 *이벤트 스트림 으로 변환*. Debezium 같은 도구.

장점: *애플리케이션 코드 변경 0*
단점: *schema evolution* / *DB replication slot 부담*

---

## 7. API Gateway / BFF / Sidecar

### API Gateway
*모든 외부 요청 의 *단일 진입점*. *라우팅 / 인증 / rate limit / WAF*.

```
[Client]
   ↓
[API Gateway]   ← Spring Cloud Gateway / Kong / Tyk / AWS ALB
   ├ /orders/*  → order-service
   ├ /users/*   → user-service
   └ /products/* → product-service
```

장점: *클라이언트 가 *백엔드 구조* 모름*, *공통 정책 한 곳*
함정: *Gateway 자체 가 *single point of failure* — *HA 의무*

→ sparta MSA 의 *Spring Cloud Gateway* 가 *chat.lemuel.co.kr 의 진입점*.

### BFF (Backend for Frontend)
*프론트 별* 별도 *백엔드 집계 층*. *모바일 / 웹 / 외부 파트너* 가 *각자 다른 BFF*.

```
[Mobile App]  → [Mobile BFF]   → user-service, order-service, ...
[Web App]     → [Web BFF]      → user-service, order-service, ...
[Partner API] → [Partner BFF]  → user-service, ...
```

각 BFF 는 *자기 클라이언트* 의 *최적 응답 만들기* 책임. *N+1 fan-out* 을 *server-side aggregation* 으로 흡수.

### Sidecar
*pod 안 의 *보조 컨테이너*. *주 컨테이너* 와 *생명 주기 / 자원 공유*.

흔한 sidecar:
- *Envoy / Istio proxy* — Service Mesh 의 *traffic 정책*
- *fluent-bit / filebeat* — 로그 수집
- *cloud SQL proxy* — DB 인증 처리

---

## 8. Service Mesh — Istio, Linkerd, Cilium

*sidecar 가 *모든 pod 에 *주입* 되어 *서비스 간 통신* 을 *가로채기*.

```
[Pod A]                    [Pod B]
  ├ App container            ├ App container
  └ Envoy sidecar ←──mTLS──→ └ Envoy sidecar
```

Envoy 가 *mTLS / retry / circuit breaker / observability* 를 *코드 변경 없이* 적용. *Zero Trust 의 *물리 적 실현*.

장점:
- *애플리케이션 코드 의 *cross-cutting 보안 / 관측 의무* 제거
- *정교한 traffic 정책* (canary, A/B, fault injection)
- *mTLS 자동* (cert 발급 / 갱신)

함정:
- *각 pod 에 sidecar = RAM 50MB+ 추가*
- *latency 0.5~1 ms 추가 per hop*
- *복잡도 증가* — *수십 ~ 수백 서비스* 가 *되어야 비용 정당화*

→ 우리 6 노드 클러스터 에선 *과잉*. *Cloudflare Tunnel + Cloudflare Access* 로 *외부 보안* 흡수.

자세히는 [K8s 로드밸런서](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html).

---

## 9. Strangler Fig — 레거시 마이그레이션

*Martin Fowler 의 2004 명명*. *옛 시스템 을 *한 번에 갈아 엎지 않고*, *새 시스템 이 *천천히 *옛 시스템 을 *감싸* 며 *기능을 흡수*.

```
초기:
[Client] → [Legacy Monolith]

전환 1:
[Client] → [API Gateway]
              ├ /users/* → [Legacy Monolith]
              └ /orders/* → [New Order Service]   ← 새 서비스 신설

전환 2 (몇 달 후):
[Client] → [API Gateway]
              ├ /users/* → [New User Service]    ← 옛 monolith 의 users 부분 이전
              └ /orders/* → [New Order Service]

최종:
[Client] → [API Gateway]
              ├ /users/* → [New User Service]
              ├ /orders/* → [New Order Service]
              └ /products/* → [New Product Service]
              # Legacy Monolith 사라짐
```

장점:
- *production down time 0*
- *각 단계 별 *위험 작음*
- *옛 시스템 의 *고객 영향 0*

함정:
- *오래 걸림* — 보통 *6 개월 ~ 2 년*
- *옛 + 새 *동시 유지 비용*
- *경계 결정 의 *지속적 의사결정*

---

## 10. 우리 settlement MSA — 실전 적용

```
[Internet]
   ↓
[Cloudflare Tunnel + Access]   ← Zero Trust 보안
   ↓
[ingress-nginx]                 ← L7 라우팅
   ↓
[order-service]                 ← 모듈러 모놀리스 (fat jar 안에 settlement-service 번들)
   ├ Module: order              ← 헥사고날, ArchUnit 강제
   │   ├ domain/                ← Spring 의존 0
   │   ├ application/           ← use case
   │   └ adapter/
   ├ Module: settlement         ← library jar (분리 준비)
   ├ Module: shared-common      ← Outbox infra (재사용)
   ↓
[PostgreSQL (ilwon)]            ← schema 별 모듈 격리
[Kafka]                         ← Outbox → Kafka publish
   ↓
[downstream consumers]
   ├ Search indexer (sparta)
   ├ Notification service
   └ Analytics
```

선택 의 근거:
- *Modular Monolith*: 1 명 운영 — 운영 부담 최소화
- *Hexagonal*: 도메인 안정성 — 변경 비용 줄임
- *Outbox*: dual-write 사고 영원 차단
- *Saga*: 결제 / 정산 의 *분산 트랜잭션* 안전
- *No Service Mesh*: 6 노드 규모 — 과잉

자세히 [Outbox 패턴](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html), [settlement 8 가지 체크리스트](/2026/06/18/eight-checklist-self-audit-of-my-settlement-system.html) 참조.

---

## 11. 패턴 선택 의 가이드

| 상황 | 선택 |
|---|---|
| 팀 < 5 명, 시작 단계 | Monolith + Layered |
| 팀 5 ~ 30, 도메인 커짐 | Modular Monolith + Hexagonal |
| 팀 30+, 명확한 도메인 경계 | MSA + Hexagonal + Outbox |
| 복잡한 비즈니스 규칙 | + CQRS 검토 |
| 금융 / 감사 / 시간 여행 | + Event Sourcing |
| 분산 트랜잭션 필요 | Saga (Orchestration 또는 Choreography) |
| Legacy 마이그레이션 | Strangler Fig |
| 수십 ~ 수백 서비스 | + Service Mesh |
| 외부 API 단일 진입점 | API Gateway |
| 클라이언트 별 응답 다름 | + BFF |

> 패턴 은 *목적 자체 가 아니라 *문제 해결의 도구*. *문제 없는데 패턴 도입* 은 *복잡도 만 추가*. *문제 가 명확 할 때* *적합한 패턴 을 선택* 하는 *판단력* 이 *시니어 의 일*.

---

## 12. 마치며

서버 구조 설계 의 *진실* 은 *trade-off*. *어떤 패턴 도 *공짜 가 아님*. *Modular Monolith 의 단순성* 을 *Microservice 의 자율성* 과 *교환* 한다. *Hexagonal 의 *테스트 단순성* 을 *학습 곡선* 과 *교환* 한다. *Service Mesh 의 *보안 / 관측 의 강력함* 을 *복잡도* 와 *교환* 한다.

*그 trade-off 의 *밑* 에 *팀 / 워크로드 / 시점 / 비용* 의 *맥락* 이 있다. 같은 패턴 이 *6 명 팀 에선 *과잉*, *50 명 팀 에선 *필수* 다. *맥락 모르면 패턴 도 의미 없음*.

내가 *3 년 settlement MSA + sparta MSA 운영* 하면서 *체화 한 한 가지* — *처음 부터 정답 인 구조* 는 *없다*. *문제 가 *생기면 *그 문제 해결 의 적합 한 패턴* 을 *도입*, *해결 후 *경계 다시 그리기*. *진화* 가 *유일한 길*.

---

## 참고

- *Domain-Driven Design* (Eric Evans, 2003)
- *Implementing Domain-Driven Design* (Vaughn Vernon, 2013)
- *Hexagonal Architecture* (Alistair Cockburn, 2005, 원전 논문)
- *Building Microservices* (Sam Newman, 2nd ed., 2021)
- *Monolith to Microservices* (Sam Newman, 2020) — Strangler Fig 의 깊이
- *Microservices Patterns* (Chris Richardson, 2018) — Saga, Outbox, CDC 의 표준 reference
- 자매편:
  - [분산 시스템 의 본질](/2026/06/22/distributed-systems-cap-base-saga-2pc-cdc-consistency.html)
  - [Outbox 패턴](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)
  - [객체 지향 의 4 층 분해](/2026/06/22/object-oriented-4-layers-decomposition-architecture-solid-dip-di.html)
  - [K8s 로드밸런서](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html)
