---
layout: post
title: "settlement-service 해부 — 결제 1건이 정산·환불·확정·지급까지 가는 길"
date: 2026-10-28 02:22:08 +0900
categories: [settlement, architecture]
tags: [settlement, spring-batch, hexagonal, holdback, state-machine, kafka, outbox, adr]
---

settlement 리포의 자바 서비스는 order·settlement·finance·external-data·operation 다섯 개다(앞단에 gateway 가 하나 더 있다). 이 글은 그중 **settlement-service 안에서 "정산"이 어떤 구조로 돌아가는지**를 다룬다. 결제 한 건을 따라가면서 각 단계에 어떤 코드와 규칙이 있는지 본다.

기준 코드는 `origin/develop` 9ab31b7(2026-10-27)이다. 운영(settlement-prod)의 `settlement-query` 디플로이먼트가 돌리는 이미지는 `main-95c29ab` 다. 두 커밋 사이에 `settlement` 패키지는 한 줄도 다르지 않다는 것을 `git diff` 로 확인했다. 그러니 아래 내용이 곧 지금 운영 중인 코드다.

카프카가 무엇을 보장하는지(outbox·멱등 수신)는 같은 날 올라온 [정산 서비스에서 카프카의 역할](/2026/10/27/settlement-kafka-role-who-guarantees-what/) 글이 다룬다. 이 글은 그 메시지를 **받은 다음** 서비스 안에서 일어나는 일에 집중한다.

## 1. 서비스의 자리 — 독립 DB, 그리고 남의 데이터는 사본으로만

예전에는 settlement-service 가 독립 서비스가 아니었다. 라이브러리 jar 로 빌드돼 order-service 의 fat jar 안에 함께 들어갔다. ADR 0020(주문·정산 DB 분리)의 Phase 0 에서 이것을 떼어 냈고, 지금은 다음과 같다.

- 독립 프로세스(:8082)로 뜬다.
- 자기 DB `settlement_db` 와 자기 Flyway 이력(V1 baseline)을 가진다.
- 주문 데이터는 **직접 읽지 않는다.** 카프카 이벤트로 채우는 로컬 프로젝션(`settlement_*_view`)만 본다.
- 대사(reconciliation)에 원본이 필요할 때만 order 의 내부 API(`OrderReconClient`)를 부른다.

결과적으로 다른 서비스 DB 로 가는 커넥션은 0개다.

내부는 헥사고날(ports & adapters) 구조다([Cockburn, Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)). `domain` 에는 스프링 의존이 없다. `application` 은 port in/out 과 서비스로 나뉜다. `adapter` 는 in(batch·kafka·web·internal)과 out(persistence·event·search·pdf·external·readmodel)으로 나뉜다. 서비스 전체는 1,219개 파일이다. 하위 패키지별 파일 수를 보면 무게중심이 보인다.

| 패키지 | 파일 수 | 하는 일 |
|---|---|---|
| settlement | 191 | 정산 본체 (이 글의 주제) |
| payout | 114 | 지급 |
| ai | 91 | 보조 기능 |
| deposit | 81 | 예치금 |
| ledger | 73 | 원장(복식부기) |
| tax | 72 | 원천징수·세금 |
| report · pgreconciliation · closing | 35 · 34 · 32 | 리포트 · PG 대사 · 마감 |
| recovery · integrity · chargeback | 23 · 22 · 18 | 회수 · 정합성 · 차지백 |

"정산 서비스"라고 부르지만 정산 본체는 전체의 일부다. 나머지는 정산 **결과**를 돈의 흐름(원장·지급·세금)으로 옮기는 코드다.

## 2. 결제 1건의 일생

```
payment.captured ──▶ ① 정산 생성 (REQUESTED, 수수료·유보금 계산)
                        │
refund ─────────────▶ ② 환불 = 조정(adjustment) 행 추가 (본 행은 안 고침)
                        │
매일 03:00 KST ─────▶ ③ 확정 배치 ─┬─ 조정으로 전액 소멸 → CANCELED
                                   └─ 그 외 → DONE (확정액 = 실효 순액)
                        │
loan 공제 응답 ─────▶ ④ 지급 생성 = 즉시분 − 원천징수 − 상계
                        │
유보 해제일 ───────▶ ⑤ 유보금(holdback) 해제 지급
```

### ① 생성 — 결제 이벤트가 정산을 만든다

정산은 사람이 만들지 않는다. `PaymentEventKafkaConsumer` 가 `payment.captured` 를 받으면 `CreateSettlementFromPaymentService` 가 정산 행을 만든다. 순서는 이렇다.

1. **멱등 확인**: 먼저 `findByPaymentId` 로 이미 있는지 본다.
2. **등급·주기 결정**: 이벤트에 실린 값을 쓴다. 없으면 DB 조인으로 찾고, 그래도 없으면 NORMAL 등급과 그 등급의 기본 주기로 떨어진다.
3. **정산 예정일 계산**: 소비한 시각이 아니라 **결제 캡처일** 기준이다. 캡처일이 없을 때만 KST 시계로 대신하고 경고 로그를 남긴다. 컨슈머가 밀렸다 따라잡을 때 예정일이 밀리지 않게 하려는 것이다.
4. **수수료율 결정** → 수수료·순액 계산 → 유보금 적용.
5. **저장**: 같은 결제로 두 컨슈머가 동시에 들어오면 `uk_settlements_payment_id` 유니크 제약이 하나를 막는다. 진 쪽은 `DataIntegrityViolationException` 을 잡아 **이긴 쪽 행을 다시 읽고 그 결과로 수렴**한다. 이긴 쪽이 없으면(다른 원인의 위반) 그대로 던진다.
6. 같은 트랜잭션 안에서 감사 로그를 남기고, 먼저 와 있던 차지백을 이 정산에 붙이고, `SettlementCreated` 를 outbox 로 `lemuel.settlement.created` 에 낸다. loan-service 가 이걸 대출 담보로 쓴다.

### 등급이 정하는 세 가지 — 수수료율, 주기, 유보금

`SellerTier` enum 한 곳에 세 가지 정책이 같이 묶여 있다.

| 등급 | 기본 수수료율 | 기본 정산 주기 | 유보율 | 유보 해제 |
|---|---|---|---|---|
| NORMAL | 3.5% | T+7 영업일 | 30% | 30 영업일 |
| VIP | 2.5% | T+3 영업일 | 10% | 14 영업일 |
| STRATEGIC | 2.0% | T+1 영업일 | 0% | 즉시 |

모르는 등급 값이 들어오면 NORMAL 로 떨어진다. 가장 보수적인(유보가 가장 큰) 쪽이다.

**유보금(holdback)** 은 순액의 일부를 지급하지 않고 잡아 두는 돈이다. 코드 주석에 목적이 적혀 있다. 신뢰가 낮은 판매자의 환불 폭주나 사기 위험을 흡수하기 위해서다. 30 영업일은 달력으로 약 42일이다.

**수수료율**은 등급 기본값이 끝이 아니다. ADR 0032(효력일자 기반 수수료율 정책)의 `CommissionRatePolicy` 가 결정한다.

- 각 요율은 반열린 구간 `[시작일, 종료일)` 동안만 유효하다.
- 행을 **UPDATE 하지 않는다.** 요율을 바꾸려면 옛 행을 닫고 새 행을 넣는다. 그래서 테이블 자체가 이력이 된다.
- 기간이 겹치는 행은 PostgreSQL 의 EXCLUDE 제약이 막는다([PostgreSQL — Exclusion Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION)).
- `resolve()` 는 순수 함수다. 우선순위는 **판매자 개별 요율 > 등급 요율**이다. 아무 행도 맞지 않으면 등급 기본값으로 떨어진다. 어느 규칙으로 정해졌는지는 `SELLER:{id}` / `TIER:{등급}` / `DEFAULT_TIER` 로 남는다.

결정된 요율은 정산 행에 **스냅샷**으로 박힌다(`commissionRate`, final). 나중에 정책 테이블이 바뀌어도 이미 만들어진 정산의 수수료는 변하지 않는다.

### 영업일 계산 — 달력도 도메인 코드다

T+N 은 영업일이다. `BusinessDayCalculator` 는 주말에 더해 세 갈래의 휴일을 뺀다.

1. **고정 양력 공휴일**: 코드에 상수로 있다.
2. **음력 공휴일·대체공휴일**: **연도별로 하드코딩**돼 있다. 등록된 해에만 정확하다. 대체공휴일 규칙의 근거는 「관공서의 공휴일에 관한 규정」 제3조다([국가법령정보센터](https://www.law.go.kr/법령/관공서의공휴일에관한규정)).
3. **임시공휴일**: 설정값 `app.settlement.extra-holidays` 로 넣는다. 갑자기 지정된 임시공휴일에 재배포할 필요가 없다.

계산기 자체에는 스프링 의존이 없고, 기본 인스턴스는 설정 계층이 끼워 넣는다.

### ② 환불 — 정산 행을 고치지 않고 조정 행을 쌓는다

ADR 0004(조정을 통한 역정산) 이후 환불은 **정산 행을 수정하지 않는다.** 대신 `SettlementAdjustment` 행을 추가한다. 처리 순서(`AdjustSettlementForRefundService`)는 다음과 같다.

1. `findByPaymentIdForUpdate` 로 정산 행에 비관적 잠금을 건다([PostgreSQL — FOR UPDATE](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)).
2. `ensureAdjustableForRefund`: **이미 DONE 인 정산이면 예외를 던진다.** 조용히 넘어가지 않고 실패시켜서 메시지가 DLT 로 가게 한다.
3. 아직 반영되지 않은 이전 조정을 모은다. PG 대사로 생긴 회수(clawback) 조정은 여기서 뺀다.
4. `ensureAdjustmentsWithinPaymentAmount`: 조정 합계가 결제액을 넘지 못하게 한다.
5. 조정 행을 저장한다.
6. 이벤트를 차례로 낸다. 유보금에서 깎인 몫(`HoldbackConsumed`), 판매자 지급 대상 금액의 변화(`SettlementAdjusted`, 이미 즉시지급된 몫을 넘지 않게 상한), 전액 소멸했으면 `SettlementCanceled`.
7. 원장 역분개 작업을 outbox 로 넣는다.

**환불은 유보금에서 먼저 빠진다.** 유보금은 아직 판매자에게 나가지 않은 돈이라 거기서 빼는 게 가장 안전하다. 유보금이 그 용도로 존재하기도 하다.

PG 대사 불일치에 따른 회수 여부는 `ClawbackPolicy` 가 정한다. **기본값은 "회수하지 않는다"** 이다. 회수하는 경우는 두 가지뿐이다.

- 금액 불일치(AMOUNT_MISMATCH)인데 PG 쪽이 적은 경우: 차액만큼 회수.
- PG 에 거래 자체가 없는 경우(MISSING_PG): 내부 금액 전체 회수.

수수료 불일치·중복·반올림 차이는 회수하지 않는다. 이 규칙은 도메인에 있어서, 관리자가 승인 전에 보는 미리보기와 실제 카프카 컨슈머가 **같은 함수**를 쓴다.

### ③ 확정 — 매일 03:00 의 Spring Batch

`SettlementScheduler` 는 `@Scheduled(cron = "0 0 3 * * *", zone = "Asia/Seoul")` 로 매일 새벽 3시(KST)에 돈다. 대상은 **어제** 날짜다.

- 파드가 여러 개여도 한 번만 돌도록 `@SchedulerLock(name = "settlement-confirm-daily", lockAtMostFor = "PT30M")` 으로 ShedLock 을 건다([ShedLock](https://github.com/lukas-krecan/ShedLock)).
- 실제 일은 Spring Batch 잡 `confirmSettlementJob` 이 한다. `JobOperator` 로 동기 실행하고, 파라미터에 `requestedAt` 을 넣어 매 실행이 새 JobInstance 가 되게 한다.
- 예전에는 하루치를 트랜잭션 하나로 처리하는 tasklet 이었다. 지금은 **청크 단위**(`app.settlement.confirm.chunk-size`, 기본 100)다([Spring Batch — Chunk-oriented Processing](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html)). 한 건이 실패해도 하루치 전체가 롤백되지 않는다.

Processor 의 판정은 단순하다. 조정으로 전액 소멸했으면 `cancel()`, 아니면 `confirm()` 이다(REQUESTED → PROCESSING → DONE).

Writer 가 하는 일은 이렇다.

- 저장한다. CANCELED 는 여기서 끝나고 후속 처리가 없다.
- 확정액은 **실효 순액**(순액 − 조정 합계, 0 미만은 0)이다.
- loan-service 에 `SettlementConfirmed` 를 낸다.
- 개인 판매자면 원천징수를 적립한다(`lemuel.settlement.withholding_accrued`, ADR 0029 §B).
- 원장 생성 작업과 검색 인덱스 이벤트를 넣는다.

이 모든 것이 **청크 트랜잭션 하나 안에서 outbox 에 기록**된다. 확정은 됐는데 원장 작업이 빠지는 일이 구조적으로 생기지 않는다.

### ④ 지급 — 대출 공제를 기다린다

지급 생성은 확정 배치에 없다. 예전에는 있었지만 지금은 `ApplyLoanDeductionService` 로 옮겨졌다. loan-service 가 정산을 담보로 잡은 대출의 공제액을 회신해야 지급액이 정해지기 때문이다.

> 지급액 = 즉시지급분 − 원천징수 − 상계(대출 공제)

### ⑤ 유보금 해제

`HoldbackReleaseScheduler` 가 해제일이 된 유보금을 풀어 별도 지급(HOLDBACK_RELEASE)을 만든다. 해제일 전에 `releaseHoldback(today)` 를 부르면 예외가 난다.

## 3. 상태 기계

`SettlementStatus.canTransitionTo` 가 전이 규칙의 유일한 출처다.

| 현재 | 갈 수 있는 곳 |
|---|---|
| REQUESTED | PROCESSING, CANCELED |
| PROCESSING | DONE, FAILED, CANCELED |
| FAILED | REQUESTED(재시도), CANCELED |
| DONE | — (종결) |
| CANCELED | — (종결) |

알 수 없는 문자열은 REQUESTED 로 읽는다. 예전에 쓰던 레거시 상태값들은 마이그레이션 V26 에서 정리됐다.

## 4. 돈이 두 번 나가지 않게 하는 장치들

정산 코드의 핵심 가치는 계산이 아니라 **불변식**에 있다. `Settlement` 집합 루트(693줄)에는 public setter 가 하나도 없다. 생성은 `createFromPayment` 와 `rehydrate` 두 팩토리로만 하고, `assignId` 는 한 번만 쓸 수 있다. 금액은 `Money` 값 객체(소수 2자리, HALF_UP)로만 다룬다.

| 장치 | 무엇을 막나 |
|---|---|
| `getImmediatePayoutBase()` = max(순액 − 유보금, 0) | 유보 해제 여부와 상관없이 같은 값을 낸다. 그래서 **즉시지급 + 유보해제 지급의 합이 정확히 순액**이 된다. 코드에서 INV-6(이중 지급 방지)으로 부른다 |
| DB CHECK `net_amount >= 0` | 회수·조정이 순액을 음수로 만드는 것 |
| 조정 합계 ≤ 결제액 | 환불이 결제보다 많이 잡히는 것 |
| DONE 정산의 환불 거부 (fail-loud → DLT) | 이미 확정된 돈을 조용히 바꾸는 것 |
| 요율 스냅샷 (final) | 정책 변경이 과거 정산에 소급되는 것 |
| `uk_settlements_payment_id` + 승자 재조회 | 같은 결제로 정산이 두 개 생기는 것 |
| `FOR UPDATE` (환불) · `@Version` (낙관적 잠금) | 동시 갱신에서 덮어쓰기 |
| ShedLock | 파드 여러 개에서 배치가 중복 실행되는 것 |

## 5. 이 구조가 치르는 비용

- **음력 공휴일은 해마다 사람이 넣어야 한다.** 등록 안 된 해의 설·추석에는 T+N 이 틀린다. 실패도 아니고 경고도 없이 날짜만 틀린다.
- **확정 후 환불은 자동으로 처리되지 않는다.** DONE 에 대한 환불은 DLT 로 가고 사람이 본다. 의도된 선택(조용한 오답보다 시끄러운 실패)이지만, 그만큼 운영 큐가 생긴다.
- **본 행 + 조정 행 구조라 "지금 얼마인가"가 한 컬럼에 없다.** 실효 순액은 조정 합계를 더해야 나온다. 조회·리포트 쪽 코드가 모두 이 계산을 알아야 한다.
- **지급이 loan 응답을 기다린다.** loan-service 가 늦으면 확정은 끝났는데 지급이 안 생기는 구간이 생긴다.
- **복잡도.** 정산 본체만 191개 파일이다. 등급·주기·요율·유보·조정·회수·원천징수가 서로 엮여 있어서 하나를 바꿀 때 ADR 을 먼저 읽어야 한다. 이 리포에 ADR 이 40개 넘게 쌓인 이유다.

## 정리

settlement-service 의 정산은 "결제액 × 수수료율"이 아니다. 다음 다섯 가지 결정의 묶음이다.

1. **언제** 줄지 — 등급별 주기 + 한국 영업일 달력
2. **얼마를** 줄지 — 효력일자가 있는 요율, 스냅샷
3. **얼마를 잡아 둘지** — 유보금
4. **환불을 어떻게 반영할지** — 원본을 고치지 않는 조정 행
5. **두 번 주지 않을 방법** — 불변식, 유니크 제약, 잠금, outbox

같은 날 올라온 [market-stream 해부](/2026/10/27/settlement-market-stream-anatomy-healthy-but-unreachable/) 글과 함께 읽으면 settlement 리포의 다른 서비스가 어떻게 생겼는지도 비교해 볼 수 있다.

## References

**1차 출처 — 코드·설계 문서** (settlement 리포는 비공개라 경로만 적는다)

- `settlement-service/src/main/java/github/lms/lemuel/settlement/` — `domain/Settlement.java`, `SettlementStatus`, `SellerTier`, `SettlementCycle`, `HoldbackPolicy`, `BusinessDayCalculator`, `CommissionRatePolicy`, `ClawbackPolicy`, `application/service/CreateSettlementFromPaymentService`, `AdjustSettlementForRefundService`, `adapter/in/batch/SettlementScheduler`, `SettlementConfirmJobConfig` · `Processor` · `ItemWriter` (origin/develop 9ab31b7)
- `docs/adr/0004-reverse-settlement-via-adjustment.md` — 조정을 통한 역정산
- `docs/adr/0020-order-settlement-db-split.md` — 주문·정산 DB 분리
- `docs/adr/0026-account-payout-cash-recognition.md` — 지급과 현금 인식
- `docs/adr/0029-settlement-tax-deliverables.md` — 정산 세무 산출물(§B 원천징수)
- `docs/adr/0032-effective-dated-commission-rate-policy.md` — 효력일자 기반 수수료율

**공식 문서·법령**

- 국가법령정보센터 — [관공서의 공휴일에 관한 규정](https://www.law.go.kr/법령/관공서의공휴일에관한규정) (제3조 대체공휴일)
- Spring Batch Reference — [Chunk-oriented Processing](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html)
- ShedLock — [lukas-krecan/ShedLock](https://github.com/lukas-krecan/ShedLock)
- PostgreSQL Documentation — [Exclusion Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION)
- PostgreSQL Documentation — [SELECT … FOR UPDATE](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
- Alistair Cockburn — [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

**같은 블로그**

- [정산 서비스에서 카프카의 역할](/2026/10/27/settlement-kafka-role-who-guarantees-what/)
- [settlement market-stream 해부](/2026/10/27/settlement-market-stream-anatomy-healthy-but-unreachable/)
