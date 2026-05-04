---
layout: post
title: "모놀리스에서 MSA로 — Settlement 정산 플랫폼 전환기"
date: 2026-05-04
categories: [architecture, msa]
tags: [spring-boot, kafka, hexagonal, outbox]
---

## 왜 MSA로 전환했는가

주문/결제와 정산은 Bounded Context가 다릅니다. 주문은 실시간 트랜잭션, 정산은 배치/비동기 처리 중심이라 배포 주기와 스케일링 요구가 달랐습니다.

## Read-only Projection 패턴

MSA 분리의 핵심은 **코드 의존성 0**입니다. settlement-service가 order-service의 테이블을 조회해야 하지만 코드를 import하면 안 됩니다.

`@Immutable` JPA Entity로 같은 테이블을 Read-only로 매핑하여:
- 코드 의존성 0
- 런타임 API 호출 0  
- Strong Consistency 확보

```java
// settlement-service에 정의된 Read-only Entity
@Entity
@Table(name = "payments")
@Immutable
public class SettlementPaymentReadModel {
    @Id private Long id;
    private Long orderId;
    private BigDecimal amount;
    private String status;
    // order-service의 Payment 테이블을 읽기 전용으로 매핑
}
```

## Outbox + Kafka 3단 멱등

결제 CAPTURED → 정산 생성 파이프라인에서 데이터 정합성을 보장하기 위해 3단 멱등 방어를 구현했습니다.

1. `outbox_events.event_id UUID UNIQUE` — 발행 측 중복 방지
2. `processed_events PK(group, event_id)` — 컨슈머 중복 수신 차단
3. `settlements.payment_id UNIQUE` — 비즈니스 레벨 중복 방지

## 프로젝트 규모

- 519개 소스 파일, 112개 테스트
- 16개 ADR (Architecture Decision Record)
- 83개 Flyway 마이그레이션
- 4개 Gradle 모듈 (order-service, settlement-service, gateway-service, shared-common)

**GitHub**: [MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement)  
**Live**: [jen.lemuel.co.kr](https://jen.lemuel.co.kr)
