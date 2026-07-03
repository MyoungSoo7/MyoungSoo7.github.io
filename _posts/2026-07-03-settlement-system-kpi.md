---
layout: post
title: "정산 시스템 을 *KPI* 로 말하기 — 돈 을 다루는 코드 의 4 가지 지표"
date: 2026-07-03 21:00:00 +0900
categories: [backend, architecture, settlement]
tags: [settlement, hexagonal, outbox, idempotency, archunit, ddd, kafka, kpi]
---

정산(settlement) 은 **돈 을 다룬다.** 그래서 "동작 한다" 로는 부족 하다 — *한 번 도 틀리면 안 되고, 틀렸을 때 추적 가능 해야* 한다. 이 글 은 내 정산 시스템 을 **4 개 KPI** 로 나눠, 각각 을 *어떤 패턴 으로 보장 했는지* 정리한다.

| KPI | 위협 | 방어 패턴 |
|---|---|---|
| 정합성 | 중복 결제·이중 정산 | Triple Idempotency |
| 감사 추적성 | "왜 이렇게 됐지?" 못 답함 | Transactional Outbox · Immutable 이력 |
| 변경 대응성 | 고칠 때 마다 무너짐 | 헥사고날 · ArchUnit |
| 신뢰성 | 메시지 유실·중복 | at-least-once + idempotent |

---

## ① 정합성 — *같은 돈 이 두 번 처리 되지 않게*

분산 시스템 에서 메시지 는 *반드시* 중복 된다(at-least-once). 정산 에서 이건 곧 **이중 결제** 다. 그래서 **Triple Idempotency** — 3 겹 방어:

```
L1  Outbox event_id UNIQUE      — 발행 단계 중복 차단
L2  processed_events PK          — 수신 단계 중복 차단
L3  DB 자연키 UNIQUE 제약         — 최종 저장 단계 중복 차단
```

어느 한 층 이 뚫려도 *다음 층 이 막는다*. 교과서적 인 "at-least-once 메시징 + idempotent 수신" 구조.

📏 측정: "중복 이벤트 유입 시 중복 처리 건수" → **0**. 통합테스트 로 같은 event_id 2 번 던져도 1 번만 반영 됨을 검증.

---

## ② 감사 추적성 — *"왜 이 정산 이 이렇게 됐나" 에 답 할 수 있게*

돈 문제 는 반드시 *"언제·무엇 이·왜"* 를 물어온다. 답 하려면 이력 이 남아야 한다.

- **Transactional Outbox** — 비즈니스 트랜잭션 과 *같은 DB 트랜잭션* 에서 이벤트 를 outbox 에 기록. 상태 머신(`PENDING → PUBLISHED`) 으로 발행 추적. **DB 커밋 = 이벤트 보장**, 유실 없음.
- **Immutable 이력** — `settlement_immutability_trigger` 로 정산 레코드 의 *사후 변조 를 DB 레벨 에서 차단*. 감사 로그 는 고칠 수 없어야 감사 가 된다.
- **Micrometer 메트릭** — outbox 발행/실패/지연 을 4 종 메트릭 으로 관측.

📏 측정: "임의 정산 건 의 전체 이벤트 흐름 재구성 가능?" → outbox+이력 으로 **가능**. "이력 변조 시도" → trigger 로 거부.

---

## ③ 변경 대응성 — *고칠 때 마다 무너지지 않게*

정산 로직 은 계속 바뀐다(수수료 정책, 정산 주기…). 바꿀 때 *다른 데 가 깨지면* 정합성 도 위험 하다. 그래서 **경계 를 컴파일러 처럼 강제**:

- **헥사고날(ports & adapters)** — domain / application / adapter 분리. 도메인 은 프레임워크 를 모른다.
- **ArchUnit** — 아키텍처 규칙 을 *테스트 로* 강제:
  - 도메인 은 Spring 의존 금지
  - application 은 JPA 직접 사용 금지
  - adapter 간 cross-domain 의존 금지
- **Flyway** — 스키마 변경 을 버전 마이그레이션 으로. 롤백·재현 가능.

📏 측정: "구조 위반 PR" → ArchUnit 테스트 가 *빌드 에서 reject*. 규칙 위반 이 프로덕션 에 못 들어감.

---

## ④ 신뢰성 — *메시지 가 유실 도 중복 도 되지 않게*

①(정합성) 이 중복 을 막는다면, 신뢰성 은 *유실* 까지 포함한 end-to-end 보장 이다.

- **at-least-once + idempotent 수신** — 발행 은 최소 1 번 보장(유실 X), 수신 은 idempotent(중복 무해).
- **DLQ(Dead Letter Queue)** — 처리 실패 이벤트 를 버리지 않고 격리 → 재처리 가능.
- **outbox 배치 폴링** — 발행 실패 시 재시도. 네트워크 순단 에도 최종 일관성.

📏 측정: "메시지 유실률" → outbox 보장 으로 *0*. "실패 이벤트 유실" → DLQ 로 *0*.

---

## 한 줄 정리

정산 을 KPI 로 바꾸면:

- **정합성**: Triple Idempotency (L1/L2/L3) → 중복 처리 0
- **감사 추적성**: Outbox + Immutable 이력 → 전 흐름 재구성 가능
- **변경 대응성**: 헥사고날 + ArchUnit → 구조 위반 빌드 차단
- **신뢰성**: at-least-once + DLQ → 유실·중복 0

돈 을 다루는 코드 는 *"보통 잘 된다"* 가 아니라 *"틀릴 수 없게 설계됐다"* 여야 한다. 그 차이 를 만드는 게 위 4 개 지표다.

---

_시리즈: [쿠버네티스 를 KPI 로](#) · 다음 글 [AI 를 KPI 로](#)._
