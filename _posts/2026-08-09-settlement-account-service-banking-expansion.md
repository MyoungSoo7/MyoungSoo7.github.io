---
layout: post
title: "Settlement account-service를 은행의 계정계로 확장할 수 있는가: 예금·적금·연금 분석설계"
date: 2026-08-09 00:40:00 +0900
categories: [Architecture, Finance, Backend]
tags: [Settlement, Account Service, Banking, Ledger, Deposit, Savings, Pension, Event Driven]
---

# Settlement `account-service`를 은행의 계정계로 확장할 수 있는가

## 결론부터

**확장 방향은 타당하지만, 현재 `account-service`를 그대로 예금·적금·연금의 고객 계정계로 간주하면 안 된다.**

현재 저장소의 `account-service`는 다음 성격에 더 가깝다.

```text
loan·investment·settlement 이벤트 소비
→ 전사 복식부기 GL 분개
→ owner별 잔액·trial balance·reconciliation 조회
```

즉 지금은 고객의 예금 계좌를 직접 운영하는 소매은행 계정계라기보다 **정산·대출·투자 이벤트를 집계하는 소비 전용 원장/GL 서비스**다.

가장 안전한 확장 전략은 다음이다.

```text
현재 account-service
= 불변 GL·분개·대사 코어

추가 banking core
= 고객계정·상품·거래·이자·세금·지급 조건

adapter/event layer
= deposit·savings·pension product policy와 GL 연결
```

`account-service`의 원장 코어는 재사용하되, 예금·적금·연금 상품 규칙과 고객 계정 lifecycle을 별도 도메인으로 분리해야 한다.

## 분석 범위와 근거

분석 대상:

```text
Repository: MyoungSoo7/settlement
Commit: 70d24bb
Target: account-service
Mode: 정적 소스·설정·migration·도메인 주석 분석
```

실제 은행 계정·운영 DB·고객정보·금융기관 연동은 조회하지 않았다. 따라서 아래 내용은:

```text
확인된 현재 구현
+ 은행 시스템 확장을 위한 분석설계
```

이며 예금·적금·연금 기능이 현재 구현되어 있다고 주장하지 않는다.

## 1. 현재 account-service가 실제로 가진 것

### 독립 DB와 소비 전용 경계

`AccountServiceApplication` 주석은 `account-service`가 자체 DB `lemuel_account`를 소유하고, `loan`·`investment`·`settlement`가 발행하는 Kafka 이벤트를 소비해 전사 GL로 집계한다고 설명한다.

```text
loan/investment/settlement
        ↓ Kafka events
account-service
        ↓
account_entries
account_balances
trial balance
reconciliation
```

현재 서비스는 이벤트를 발행하지 않는 소비 전용 서비스로 설계되어 있다. 이 경계는 Settlement 확장에는 적절하지만, 고객이 예금하고 출금하는 은행 계정계가 되려면 명령 처리·거래 승인·상태 전이·잔액 가용성·고객 알림 등 별도의 write model이 필요하다.

### `account_entries`: append-only 복식부기 원장

현재 핵심 테이블은 다음 형태다.

```text
account_entries
 ├─ owner_type
 ├─ owner_id
 ├─ debit_account
 ├─ credit_account
 ├─ amount
 ├─ ref_type
 ├─ ref_id
 ├─ source_topic
 └─ occurred_at
```

한 행이 차변 1개·대변 1개·양수 금액 1개로 구성되고, 차변과 대변 금액이 같은 구조다. 자연키 `(source_topic, ref_type, ref_id)` unique로 동일 이벤트 재수신을 방어한다.

현재 `GlAccount`에는 다음 계정이 확인된다.

```text
CASH
LOAN_RECEIVABLE
CORPORATE_LOAN_RECEIVABLE
SECURED_LOAN_RECEIVABLE
INVESTMENT_ASSET
SELLER_PAYABLE
HOLDBACK_PAYABLE
SELLER_RECOVERY_RECEIVABLE
SETTLEMENT_SCHEDULED
WITHHOLDING_PAYABLE
```

이는 예금 고객의 `원금·이자·출금가능잔액·지급제한`을 표현하는 상품계정이라기보다, 정산·대출·투자·회수·원천징수에 필요한 GL 계정과목이다.

### Materialized balance와 재계산 대사

`account_balances`는 원장 합계를 매번 재계산하지 않기 위한 실체화 잔액이다.

```text
account_entries append
  → account_balances upsert delta

검증:
SUM(account_entries)
  vs
account_balances
```

이 구조는 고성능 잔액 조회와 재현 가능한 대사를 동시에 제공한다. 은행 확장에서 매우 유용한 기반이지만, **GL balance와 고객의 사용가능 잔액은 동일하지 않다.**

```text
GL balance
= 회계상 누적 잔액

ledger balance
= 거래 원장 기준 잔액

available balance
= 보류·예약·제한·미결제를 반영한 사용 가능 금액
```

예금 출금 승인에는 `available balance`가 필요하므로 별도의 balance projection 또는 reservation model이 필요하다.

## 2. 은행 시스템으로 확장할 때 분리해야 할 계층

권장 목표 구조는 다음과 같다.

```text
Customer/Party
  고객·법인·실소유자·KYC 상태

Product Catalog
  예금·적금·연금 상품 조건과 version

Customer Account
  고객이 보유한 금융 계좌와 lifecycle

Transaction Ledger
  입금·출금·이체·납입·이자·세금 거래

Available Balance
  사용 가능액·보류액·예약액·제한액

Interest Engine
  금리·일할·복리·우대·세후 계산

GL / Accounting
  회계 계정·분개·trial balance

Settlement/Payout
  외부 지급·은행 이체·대사

Audit/Compliance
  KYC·AML·금융감독·감사 추적
```

현재 `account-service`는 마지막에서 세 번째인 **GL/Accounting**에 가장 가깝다. 이것을 고객계정과 직접 섞으면 상품 규칙과 회계 규칙이 서로 오염된다.

## 3. 목표 도메인 모델

### Product와 Account를 분리

상품은 조건이고 계정은 고객과의 계약이다.

```text
DepositProduct
  product_id
  version
  currency
  base_rate
  fee_policy
  withdrawal_policy
  tax_policy
  start_at/end_at

CustomerAccount
  account_id
  customer_id
  product_id/version
  status
  opened_at
  maturity_at
  currency
```

같은 예금 상품의 금리가 변경되어도 이미 가입한 계정의 계약 조건과 신규 가입 조건을 혼동하지 않으려면 product version을 계정에 고정해야 한다.

### 거래는 불변 사실로 저장

```text
AccountTransaction
  transaction_id
  account_id
  type
  amount
  currency
  effective_at
  posted_at
  status
  idempotency_key
  source_ref
```

거래 금액을 사후 수정하지 말고, 오류는 reversal·adjustment 거래로 정정한다.

```text
잘못된 거래
→ UPDATE amount 금지
→ reversal
→ corrected transaction
```

### 잔액은 여러 종류로 나눈다

```text
posted_balance
pending_balance
held_balance
available_balance
accrued_interest
```

예금 계좌의 출금 가능 여부는 단순히 `posted_balance >= withdrawal`로 계산하면 안 된다.

```text
available
= posted
+ 확정된 입금
- 출금 예약
- 지급 제한
- 보류 금액
```

## 4. 예금(Deposit) 확장

### 예금의 본질

예금은 고객이 금융기관에 자금을 맡기고 필요에 따라 인출하는 상품이다. 시스템 관점에서 중요한 것은:

```text
계좌 개설
→ 입금
→ 잔액 반영
→ 출금
→ 이자 산정
→ 세금 공제
→ 해지
```

### 권장 예금 상태

```text
APPLICATION
  → OPEN
  → ACTIVE
  → RESTRICTED
  → DORMANT
  → CLOSED
```

`RESTRICTED`는 AML·법원 지급정지·본인확인 미완료 같은 업무 상태를 의미한다. 단순히 계좌를 닫는 것과 구분해야 한다.

### 예금 거래 흐름

```text
입금 요청
  → 인증·한도·계좌 상태 검증
  → 결제/이체 rail 승인
  → pending transaction
  → 입금 확정
  → posted balance 증가
  → GL 분개
```

회계 관점의 개념적 예시는 다음과 같다.

```text
고객 예금 유입:
DR CASH / CR CUSTOMER_DEPOSIT_LIABILITY

고객 출금:
DR CUSTOMER_DEPOSIT_LIABILITY / CR CASH
```

현재 `GlAccount`에는 `CUSTOMER_DEPOSIT_LIABILITY`가 없다. 따라서 은행 확장에서는 기존 GL enum을 그대로 재사용하기보다 고객예금·이자비용·세금예수금·미지급이자 등 계정과목을 별도로 설계해야 한다.

## 5. 적금(Savings) 확장

적금은 예금과 달리 납입 스케줄과 만기 조건이 핵심이다.

```text
가입
→ 납입 일정 생성
→ 월별/주기별 납입
→ 미납·부분납입 판정
→ 우대금리 조건 계산
→ 만기/중도해지
→ 원금+이자 지급
```

### 적금에 필요한 모델

```text
SavingsContract
  product_version
  installment_amount
  payment_frequency
  scheduled_count
  paid_count
  maturity_date
  preferential_rate_conditions
  early_termination_policy
```

납입 거래와 예정 납입은 분리한다.

```text
InstallmentSchedule
= 해야 할 납입

DepositTransaction
= 실제로 발생한 납입
```

스케줄만 보고 잔액을 올리면 안 된다. 실제 결제 확정 이벤트가 도착한 경우에만 원장과 잔액을 반영해야 한다.

### 적금의 어려운 부분

- 자동이체 실패 후 재시도
- 납입일 휴일 처리
- 월말·윤년·타임존
- 일부 납입 허용 여부
- 미납이 우대금리에 미치는 영향
- 중도해지 이율
- 만기일 이후 보통예금 전환
- 세금·이자 지급 시점

이 규칙은 `account-service`의 일반 분개 기능에 넣지 말고 `SavingsPolicy` 또는 별도 savings 도메인에서 계산한 뒤 확정 거래 이벤트로 내려보내는 것이 낫다.

## 6. 연금(Pension) 확장

연금은 예금·적금보다 상품 lifecycle과 지급 조건이 훨씬 복잡하다.

```text
가입
→ 납입
→ 적립
→ 운용/수익 반영
→ 연금 개시 조건 도달
→ 지급 스케줄
→ 수령
→ 중도해지/이전/사망/상속 처리
```

연금은 단순한 `account balance`가 아니다.

```text
PensionContract
  납입기간
  연금개시연령
  지급기간/종신 여부
  수령 방식
  세제 조건
  위험보장 조건
  이전/중도인출 정책
```

### 연금의 별도 경계

```text
Pension Product
  계약·세제·지급 조건

Contribution
  납입·한도·납입 중지

Accumulation
  적립금·운용수익·평가

Annuity Benefit
  연금 개시·지급액·주기

Tax/Compliance
  세액공제·과세·원천징수·보고
```

특히 연금 지급액은 단순 잔액 나누기가 아니다. 상품 약관, 지급률, 기대수명/보증기간, 세금, 지급주기가 함께 작동하므로 별도의 계산 엔진과 versioned policy가 필요하다.

## 7. 기존 Settlement와의 연결

Settlement와 Banking Core를 직접 결합하지 않고 이벤트 계약으로 연결하는 것이 적합하다.

```text
order/payment
  → settlement
  → payout
  → account banking/GL
```

현재 저장소에서 account-service는 `SettlementCreated`, `SettlementConfirmed`, `PayoutCompleted`, holdback, recovery, withholding 이벤트를 소비해 GL 분개를 기록한다.

이 구조를 확장하면:

```text
SettlementCreated
  → SELLER_PAYABLE 인식

PayoutCompleted
  → SELLER_PAYABLE 감소 / CASH 감소

DepositAccepted
  → CUSTOMER_DEPOSIT_LIABILITY 증가

WithdrawalCompleted
  → CUSTOMER_DEPOSIT_LIABILITY 감소

InterestAccrued
  → INTEREST_EXPENSE 증가 / INTEREST_PAYABLE 증가
```

여기서 `account-service`를 두 가지로 분리할 수 있다.

### 선택지 A: 하나의 account-service에 모두 넣기

```text
account-service
 ├─ settlement GL
 ├─ customer deposit account
 ├─ savings
 └─ pension
```

장점:

- 하나의 원장과 대사 계층
- 초기 시스템 수가 적음
- 공통 금액·멱등·감사 기능 재사용

단점:

- 계정계의 책임 범위가 폭발
- 상품 규칙과 GL 규칙 결합
- 독립 배포 어려움
- 금융상품별 규제 변경 영향 범위 증가
- 장애 blast radius 확대

### 선택지 B: Banking Core와 GL 분리

```text
banking-account-service
  고객계정·잔액·거래·계좌 lifecycle

product-service
  예금·적금·연금 상품·version·policy

interest-service
  이자·세금·일할·복리 계산

account-service
  전사 GL·분개·trial balance·회계 대사

settlement-service
  판매자 정산·payout·reconciliation
```

장점:

- 도메인 책임 명확
- 상품 변경과 회계 변경 분리
- 계정계 고가용성·성능을 독립적으로 설계
- 금융상품 확장에 유리

단점:

- 이벤트 계약 증가
- 분산 대사 필요
- 운영 복잡도와 데이터 lineage 증가

**장기적으로는 B가 낫고, 단기 포트폴리오 분석에서는 현재 `account-service`를 GL core로 고정한 뒤 Banking Core를 별도 논리 모듈로 설계하는 절충안이 가장 안전하다.**

## 8. 권장 목표 아키텍처

```text
                    ┌────────────────────┐
                    │ Customer/Identity  │
                    │ KYC/AML            │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Product Catalog    │
                    │ Deposit/Saving/    │
                    │ Pension Versions   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Banking Account    │
                    │ lifecycle/ledger   │
                    │ available balance  │
                    └──────┬───────┬─────┘
                           │       │
                 ┌─────────▼─┐ ┌──▼──────────┐
                 │ Interest  │ │ Transaction │
                 │ & Tax     │ │/Payment Rail│
                 └──────┬────┘ └──┬──────────┘
                        │         │
                        └────┬────┘
                             ▼
                    ┌────────────────────┐
                    │ Accounting GL      │
                    │ current account-   │
                    │ service core       │
                    └─────────┬──────────┘
                              │
                ┌─────────────▼─────────────┐
                │ Settlement/Payout/Recon   │
                └───────────────────────────┘
```

## 9. 원장 설계 원칙

### 고객 보조원장과 GL을 구분

```text
Customer subledger
  고객별 계좌·거래·잔액

Enterprise GL
  회계 계정·차변·대변·trial balance
```

고객 계좌 한 건과 GL 계정 한 건은 일대일로 대응하지 않는다. 상품 거래 하나가 여러 GL 분개를 만들 수 있다.

```text
예금 입금
→ 고객계정 credit
→ 현금 증가
→ 고객예금부채 증가
→ 수수료/세금 분개가 추가될 수 있음
```

### 금액과 통화

- 금액은 `numeric(19,2)` 같은 고정 정밀도를 사용한다.
- 통화별 소수점 정책을 별도로 둔다.
- 원화·달러·엔화의 scale을 동일하게 가정하지 않는다.
- 반올림은 임의로 하지 말고 policy version과 rounding mode를 기록한다.
- 이자 계산에서는 중간 계산 정밀도와 최종 게시 정밀도를 분리한다.

### 멱등성과 자연키

모든 금융 명령과 이벤트는 idempotency key를 가져야 한다.

```text
(customer_id, request_id)
(account_id, transaction_type, external_ref)
(source_topic, event_type, event_id)
```

현재 account-service의 `(source_topic, ref_type, ref_id)` unique 전략은 재사용 가치가 높지만, 고객 금융거래에서는 외부 결제 승인번호·계좌거래번호·업무 요청 ID를 분리해 저장하는 것이 더 명확하다.

### 정정은 역분개

```text
수정 UPDATE
  금지

reversal
  + corrected transaction
  허용
```

원장과 고객 거래 모두 append-only 사실 모델을 기본으로 한다. 읽기 모델과 materialized balance는 재계산으로 복원 가능해야 한다.

## 10. 예금·적금·연금의 공통 코어와 차이

### 공통화할 것

```text
고객/계정 식별
상품 version
통화·금액
거래 상태
idempotency
잔액 projection
원장 posting
감사 log
대사
```

### 공통화하면 안 되는 것

| 영역 | 예금 | 적금 | 연금 |
|---|---|---|---|
| 납입 | 자유 입출금 | 납입 스케줄 | 장기 납입/한도 |
| 만기 | 없거나 선택 | 핵심 조건 | 개시연령·지급기간 |
| 이자 | 잔액·일수 | 납입일·우대금리 | 적립·운용·지급률 |
| 중도해지 | 출금 수수료 | 중도해지 이율 | 이전·세제 환수 |
| 지급 | 요청 즉시 | 만기 일시금 | 정기 연금 |
| 규제 | 거래·KYC | 상품 약관 | 세제·연금 규정 |

따라서 `ProductPolicy` 인터페이스 하나로 모든 상품의 내부 로직을 억지로 통합하는 것보다 공통 계정/거래 코어 위에 상품별 정책 모듈을 두는 편이 낫다.

## 11. 대사 설계

금융 확장에서 대사는 하나가 아니다.

```text
계정 잔액 대사
  account_entries vs account_balances

고객계정 대사
  customer subledger vs banking transaction

GL 대사
  subledger total vs enterprise GL

외부 rail 대사
  bank/PG statement vs internal transaction

상품 대사
  scheduled installment vs actual payment

이자 대사
  accrued interest vs posted interest

세금 대사
  withholding payable vs tax report
```

각 대사 실행은 다음을 기록해야 한다.

```text
recon_run_id
기준 시각/기간
입력 snapshot
차이 금액·건수
분류
해결 상태
승인자
```

대사 차이를 발견했다고 운영 DB를 직접 수정하면 안 된다. 차이의 원인을 분류하고, 승인된 adjustment/reversal 흐름으로 해소해야 한다.

## 12. 분산 이벤트와 상태 일관성

계좌 입금과 GL posting이 다른 서비스에서 처리된다면 다음 상태를 명확히 해야 한다.

```text
REQUESTED
AUTHORIZED
PENDING
POSTED
SETTLED
REVERSED
FAILED
QUARANTINED
```

고객에게 “입금 완료”를 보여주는 시점은 `REQUESTED`가 아니라 상품과 거래의 확정 계약에 따라 정해야 한다.

```text
외부 bank accepted
≠ 내부 ledger posted
≠ GL reconciled
```

각 상태의 고객 노출 문구와 회계 의미를 분리해야 한다.

## 13. 보안·규제 설계

뱅킹 확장에서 보안은 기능 이후의 체크리스트가 아니다.

필수 설계 영역:

- KYC/AML 상태와 거래 제한
- 본인 인증과 step-up authentication
- maker-checker 승인
- 고객·직원·시스템 역할 분리
- 계좌번호 masking/tokenization
- 민감정보 암호화·키 rotation
- 원장·감사 로그 변조 방지
- 이상거래 탐지와 case 관리
- 거래 한도·일일 누적 한도
- 법원/기관 지급정지
- 보존기간과 삭제 예외
- 장애·재해복구·업무연속성

현재 account-service의 append-only·audit·DLT·processed_events는 좋은 기반이지만, 이것만으로 은행 규제 준수나 실제 금융기관 인증이 완료되는 것은 아니다.

## 14. 단계별 확장안

### 0단계: 현재 account-service를 GL core로 동결

```text
현재 분개·불변성·대사·멱등성 보존
고객 예금 기능을 바로 삽입하지 않음
```

### 1단계: Banking domain 분석 모델

```text
CustomerAccount
ProductVersion
AccountTransaction
AvailableBalance
AccountHold
```

이 단계는 코드가 아니라 경계·상태·불변식·이벤트 계약을 확정한다.

### 2단계: 예금만 별도 설계

```text
DepositProduct
DepositAccount
DepositTransaction
InterestAccrual
WithdrawalPolicy
```

가장 단순한 상품부터 시작해 입출금·잔액·대사·원장을 증명한다.

### 3단계: 적금 추가

```text
SavingsContract
InstallmentSchedule
MissedPayment
Maturity
EarlyTermination
```

예금 코어를 재사용하되 납입·만기 policy를 분리한다.

### 4단계: 연금은 마지막

```text
PensionContract
ContributionLimit
Accumulation
BenefitSchedule
TaxPolicy
Transfer/Surrender
```

연금은 규제·세제·장기 계약·수익 계산이 복잡하므로 예금/적금 코어가 안정된 뒤 별도 bounded context로 확장한다.

### 5단계: 외부 기관 연동

```text
Bank rail
PG/payment rail
KYC/AML
Tax reporting
Statement ingestion
```

이 단계 전에는 “실제 뱅킹 시스템”이 아니라 분석·설계·synthetic simulation으로 표현해야 한다.

## 최종 판단

| 질문 | 판단 |
|---|---|
| `account-service`를 축으로 확장할 수 있는가? | 가능 |
| 현재 서비스가 고객 예금 계정계인가? | 아님. GL 소비·집계 코어에 가까움 |
| 기존 원장을 재사용할 가치가 있는가? | 높음 |
| 예금·적금·연금을 한 모듈에 넣어도 되는가? | 장기적으로 부적합 |
| 권장 구조 | Banking Account Core + Product Policy + Interest/Tax + 기존 GL |
| 구현 순서 | GL 동결 → 예금 → 적금 → 연금 |
| 현재 작업 범위 | 분석설계만. 코드 구현·실제 금융기관 연동 없음 |

가장 적합한 문장은 다음이다.

> Settlement의 `account-service`를 기존 정산·대출·투자 이벤트를 수용하는 불변 GL 코어로 유지하고, 그 위에 고객계정·상품·거래·잔액·이자·세금 bounded context를 분리해 예금·적금·연금으로 확장하는 것이 안전하다.

```text
Settlement
  = 돈이 발생하고 지급되는 업무 흐름

Banking Account Core
  = 고객의 금융계약과 사용 가능 잔액

Product Policy
  = 예금·적금·연금의 상품 규칙

Accounting GL
  = 모든 금융 사실의 회계적 표현

Reconciliation
  = 서로 다른 원천이 같은 돈을 말하는지 검증
```

이 경계를 지켜야 `account-service`가 단순히 기능이 많은 서비스가 아니라, **금융상품 확장을 견디는 계정계·원장 플랫폼**으로 발전할 수 있다.

## 참고 자료

- [Settlement repository](https://github.com/MyoungSoo7/settlement)
- [account-service source](https://github.com/MyoungSoo7/settlement/tree/feat/card-service-phase2-gowid/account-service)
- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Spring Kafka Reference](https://docs.spring.io/spring-kafka/reference/)

> 이 글은 Settlement `account-service`의 정적 코드·migration·설정·주석을 근거로 한 분석설계다. 예금·적금·연금 기능, 금융기관 연동, 규제 적합성, 실제 원장 운영은 구현·검증되지 않았으며 별도 프로젝트와 기관 요구사항 검토가 필요하다.

> 기준 commit: `70d24bb` · 코드 구현 없음 · 운영 DB 접근 없음
