---
layout: post
title: "내 프로젝트 들 을 관통 하는 설계 — *도메인 은 다른데, 원칙 은 같았다*"
date: 2026-07-10 04:40:00 +0900
categories: [backend, architecture, portfolio]
tags: [architecture, hexagonal, msa, outbox, idempotency, concurrency, design, portfolio, homelab]
---

정산, 청각 재활, 이커머스 검색, 물류, 자동매매, 성경 XR… 만든 것 들 의 도메인 은 제각각 이다. 그런데 코드 를 열어 보면 *같은 설계 원칙* 이 반복 된다. 이 글 은 프로젝트 를 하나씩 소개 하는 대신, **여러 프로젝트 를 관통 하는 설계 결정 다섯 가지** 를 정리 한다 — 도메인 이 달라도 변하지 않았던 것들.

---

## 1. 경계 를 컴파일러 처럼 강제 한다 (헥사고날 + ArchUnit)

거의 모든 백엔드 프로젝트 를 **헥사고날(Ports & Adapters)** 로 짰다. domain / application / adapter 를 나누고, *의존 은 안쪽(도메인) 을 향해서만* 흐르게.

문제 는 — 사람 은 규칙 을 어긴다. 급하면 도메인 에서 JPA 를 부르고, adapter 가 다른 adapter 를 직접 참조 한다. 그래서 **ArchUnit** 으로 경계 를 *테스트* 로 박제 했다:

- 도메인 은 Spring 을 import 할 수 없다
- application 은 JPA 를 직접 쓸 수 없다
- adapter 는 cross-domain 의존 금지

settlement 는 이걸 더 밀어붙였다 — settlement-service 가 order-service 의 *코드 를 import 하지 않으면서* 같은 DB 테이블 을 읽는다. `@Immutable` Read-only Projection 으로 *데이터 는 공유, 코드 는 분리*. **경계 는 문서 가 아니라 빌드 에서 강제 될 때 만 지켜진다** 는 게 반복된 교훈. (→ [객체지향 설계]({% post_url 2026-07-07-object-oriented-design-from-a-diagram %}))

---

## 2. 돈·데이터 는 *틀릴 수 없게* 설계 한다 (Outbox + 멱등)

정산·주문·SNS 피드 처럼 *어긋나면 안 되는* 도메인 은 전부 같은 뼈대 를 썼다:

- **Transactional Outbox** — 비즈니스 저장 과 이벤트 발행 을 *같은 트랜잭션* 에. "DB 커밋 = 이벤트 보장". 이중 쓰기 문제 를 없앤다.
- **at-least-once + 멱등 수신** — 메시지 는 반드시 중복 된다는 전제. settlement 는 *3단 멱등*(outbox event_id / processed_events / DB 유니크)으로, SNS 는 eventId 멱등 + DLQ 로.

핵심 은 **"보통 잘 됨" 이 아니라 "틀릴 수 없음" 을 구조 로** 만든 것. 정산 확정 후 환불 은 음수 결제 가 아니라 별도 `SettlementAdjustment` 모델 로 — 회계 는 추적 가능 해야 하니까. (→ [Outbox 딥다이브]({% post_url 2026-07-07-transactional-outbox-pattern-deep-dive %}) · [정산 KPI]({% post_url 2026-07-03-settlement-system-kpi %}))

---

## 3. 동시성 전략 을 *도메인 특성 에 맞춘다*

"락 걸면 되지" 가 아니다. 프로젝트 마다 *다른 락* 을 골랐다:

| 도메인 | 전략 | 이유 |
|---|---|---|
| 결제·환불 (금액) | **Pessimistic Lock** | 충돌 잦고 손실 직결 → 비관적 으로 막음 |
| 재고 (SKU) | **Optimistic Lock (@Version)** | 짧은 트랜잭션·충돌 희귀 → 낙관적 이 빠름 |
| ASAT 적응 알고리즘 | **Optimistic Lock** | reversal 카운트 오염 방지, trial 은 순간적 |
| 선착순 쿠폰 | **DB 유니크 + 원자적 증가** | 앱 체크 는 뚫림, DB 가 최종 방어선 |

같은 "동시성" 문제 라도 *충돌 빈도 × 트랜잭션 길이 × 실패 비용* 을 따져 다르게 갔다. 100 스레드 동시성 테스트 로 실제 검증 하고. (→ [CS 기초]({% post_url 2026-07-06-why-cs-fundamentals-matter-for-backend %}))

---

## 4. 측정·품질 을 *일급 시민* 으로

ASAT(청각 재활) 에서 배운 게 다른 프로젝트 로 번졌다 — **"동작 했다" 와 "믿을 수 있다" 는 다르다.**

- ASAT: 모든 훈련 세션 에 *데이터 신뢰도 등급(A/B/C/F)* 을 자동 부여. reversal·정답률·헤드폰 확인 을 종합 해서. "정산 확정" 처럼, *연구 데이터 도 A등급 이어야* 논문 에 쓴다.
- settlement: 배포 후 운영 도메인(jen.lemuel.co.kr) 에 **Playwright E2E 품질 게이트**. 단위테스트 가 못 잡는 통합 결함 을 배포 직후 감지.
- 전반: Prometheus/Micrometer 로 *비즈니스 KPI* 를 메트릭 으로. Outbox 발행 실패 까지 관측.

품질 을 *나중에 붙이는 것* 이 아니라 *설계 의 입구* 에 둔 것. ASAT 의 "캘리브레이션 없이는 훈련 불가" 정책 이 그 상징 이다.

---

## 5. 운영 을 *설계 안* 으로 끌어들인다

만드는 것 과 굴리는 것 을 분리 하지 않았다. 6 노드 K3s 홈랩 위 에서 40+ 서비스 를 직접 운영 하면서, 운영 이 설계 를 바꿨다:

- **GitOps(ArgoCD)** — 배포 를 "열심히" 가 아니라 "push 하면 자동" 인 *시스템* 으로. 75 앱 선언적 관리.
- **관측 3층** — Prometheus(메트릭) / ELK(로그) / 커스텀 대시보드(상태). 없는 걸 못 고친다.
- **장애 를 전제한 설계** — 외부 API 는 죽는다 전제 로 Retry/Circuit Breaker. 되돌릴 수 없는 결정 은 느리게, ADR 로.

*"새벽 3시 에 장애 로 깨어난 나"* 를 상상 하며 설계 하는 것. 이게 프로젝트 를 실험 이 아니라 *운영 가능한 시스템* 으로 만든 차이다. (→ [운영 에서 아픈 설계 6가지]({% post_url 2026-07-07-six-designs-that-hurt-in-operation %}) · [K8s·Java 운영 회고]({% post_url 2026-07-09-a-day-of-k8s-java-ops-senior-retrospective %}))

---

## 관통 하는 것 — 설계 철학 한 줄씩

프로젝트 는 달라도, 내가 반복해서 내린 결정 은 이거였다:

1. **경계 는 강제 한다** — 문서 말고 빌드(ArchUnit)로
2. **틀릴 수 없게 만든다** — 돈·데이터 는 Outbox+멱등 으로
3. **도메인 에 맞춘다** — 동시성 도, 락 도, 하나 의 정답 은 없다
4. **품질 은 입구 에** — 신뢰도·E2E 게이트 를 사후 가 아니라 사전 에
5. **운영 을 설계 한다** — 만드는 순간 부터 굴릴 것 을 상상

---

## 맺으며

포트폴리오 를 "무엇 을 만들었나" 로만 보면 도메인 나열 이 된다. 하지만 진짜 자산 은 *"어떻게 결정 했나"* 에 있다. 정산 이든 청각 재활 이든, 결국 나는 같은 질문 을 반복 했다 — **"이거, 6 개월 뒤 에도 고치기 쉬운가? 틀렸을 때 추적 되는가? 새벽 에 안 깨우는가?"**

도메인 은 배우면 되는 것이고, *설계 감각* 은 프로젝트 를 가로질러 축적 되는 것이다. 그게 열 개 의 서로 다른 프로젝트 가 나에게 남긴 진짜 유산 이다.

*무엇 을 만들었는지 보다, 무엇 을 포기 하지 않았는지 가 그 사람 의 설계다.*
