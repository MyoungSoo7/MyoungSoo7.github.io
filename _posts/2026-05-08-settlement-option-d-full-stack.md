---
layout: post
title: "정산 시스템 풀스택 — Option D 하이브리드 정책 4 단계 구현기"
date: 2026-05-08 17:30:00 +0900
categories: [backend, settlement]
tags: [spring-boot, hexagonal, jpa, java, react, typescript, micrometer, prometheus, cron, settlement]
---

이커머스 마켓플레이스에서 **정산(seller settlement)** 은 결제만큼이나 까다로운 도메인이다. 결제는 즉시 일어나지만, 정산은 *언제·어떻게·누구에게* 송금할지 정책이 다양하다. 그리고 한 번 잘못 송금하면 되돌리기 어렵다.

이 글에선 lemuel-settlement 프로젝트에 **Option D (자동 + 검토 하이브리드)** 정책을 4 단계로 나눠 구현한 과정을 공유한다.

## 정산 정책 4 가지 옵션 비교

처음 정산 시스템을 설계할 때 마주치는 4 가지 정책:

| 옵션 | 흐름 | 장점 | 단점 | 적합 |
|------|------|------|------|------|
| **A. 일배치** | 매일 02:00 자동 정산 | 운영 부담 0 | 환불 검증 짧음 | PG 검증 강한 시스템 |
| **B. 주배치** | 매주 월요일 일괄 | 회계 단순 | cashflow D+10 | 신생 마켓 |
| **C. 셀러 요청** | 셀러 → admin 승인 | cashflow 통제 | admin 부담 큼 | 대형 셀러 다수 |
| **D. 자동 + 검토** ⭐ | 자동 생성 + 의심 hold + D+3 자동 확정 | 안전망 + 자동화 | UI/룰 설계 필요 | **일반 마켓** |

D 가 가장 균형잡혔다. 한국 PG (Toss/카카오페이/네이버페이) 도 모두 D+1~D+N 정산 — 표준 흐름.

## D 옵션의 핵심 흐름

```
[Day 0]  결제 CAPTURED
         └─ outbox event (Outbox + Kafka)
                ↓
[Day 1 02:00]  CreateDailySettlements cron
               └─ 셀러별 schedule 평가 → REQUESTED 생성
[Day 1 02:15]  AutoHold cron
               └─ 의심 거래 룰 검사 → HOLD (3 룰)
[Day 1 03:00]  ConfirmDailySettlements cron
               └─ HOLD 건너뛰고 PROCESSING → DONE
[Day 1 03:30]  AutoConfirmAged cron (D+N)
               └─ N 일 이상 REQUESTED + HOLD 아닌 것 → DONE → 송금 트리거
                      ↓
                 SellerPayoutPort + SellerNotificationPort
```

핵심은 **HOLD** 라는 게이트다. admin 이 의심 거래를 발견하면 HOLD 로 표시 → 자동 cron 이 건너뛴다 → 검토 후 unhold → 다음 사이클에서 자연스럽게 처리.

## Phase 1 — HOLD 메커니즘

### 도메인 변경

`Settlement` 도메인에 `hold(reason)` / `unhold()` 메서드 추가. 상태 enum 에 `HOLD` 추가.

```kotlin
public enum SettlementStatus {
    REQUESTED,
    HOLD,        // ★ admin 보류
    PROCESSING,
    DONE,
    FAILED,
    ...
}

public boolean canTransitionTo(SettlementStatus targetStatus) {
    switch (this) {
        case REQUESTED:
            return targetStatus == PROCESSING
                || targetStatus == CANCELED
                || targetStatus == HOLD;  // ★
        case HOLD:
            return targetStatus == REQUESTED
                || targetStatus == CANCELED;
        ...
    }
}
```

### UseCase (헥사고날)

```java
public interface HoldSettlementUseCase {
    void hold(HoldCommand command);
    void unhold(Long settlementId);

    record HoldCommand(Long settlementId, String reason) { ... }
}
```

### REST 엔드포인트

```
POST /settlements/{id}/hold     {"reason":"의심 거래"}    → 204
POST /settlements/{id}/unhold                              → 204
```

자동 확정 cron 이 `settlement.isHeld()` 체크해 건너뜀.

## Phase 2 — 자동화

### D+N 자동 확정

`AutoConfirmAgedSettlementsService` — settlement_date 가 N 일 이상 경과 + REQUESTED + HOLD 아닌 것을 자동 확정.

JPA query:
```java
@Query("SELECT s FROM SettlementJpaEntity s WHERE s.status = 'REQUESTED' AND s.settlementDate <= :cutoff")
List<SettlementJpaEntity> findRequestedOlderThanOrEqual(@Param("cutoff") LocalDate cutoff);
```

`HOLD` 는 `status = 'REQUESTED'` 매칭으로 자동 제외 — 별도 조건 불필요.

### 일괄 hold/unhold

```
POST /settlements/hold-batch   {"ids":[1,2,3], "reason":"..."}
POST /settlements/unhold-batch {"ids":[1,2,3]}
```

도메인 거절 (ex. 이미 HOLD 인 것) 은 skip 카운트.

### 환불 시 settlement_adjustments 자동 생성

`AdjustSettlementForRefundService` 가 settlement.refunded_amount 갱신과 동시에 `settlement_adjustments` 감사 레코드 생성. 운영에서 환불 발생을 추적할 수 있다.

### 셀러별 schedule

`settlement_schedule_config` 테이블 + Spring `CronExpression` 으로 셀러별 정산 주기 차등화:

```
"0 0 2 * * *"        매일 02:00 (D+1)
"0 0 2 * * MON"      매주 월요일 02:00 (주간)
"0 0 2 1 * *"        매월 1일 02:00 (월간)
"0 0 2 1,15 * *"     1일 / 15일 02:00 (격주)
```

도메인이 cron 검증 + `shouldTriggerAt(LocalDateTime)` 평가:

```java
public boolean shouldTriggerAt(LocalDateTime when) {
    if (!Boolean.TRUE.equals(enabled)) return false;
    CronExpression cron = CronExpression.parse(cronExpression);
    LocalDateTime next = cron.next(when.minusMinutes(1));
    return next != null && !next.isAfter(when.withSecond(59));
}
```

## Phase 3 — 룰 + 통합 + 가시성

### 의심 거래 자동 보류

3 가지 룰:

```java
private String scoreReason(Settlement s, BigDecimal hugeThreshold, Map<Long, Double> refundRates) {
    if (s.getPaymentAmount().compareTo(hugeThreshold) > 0) {
        return "이상 금액 (평균의 5배 초과)";
    }
    if (s.getRefundedAmount().compareTo(s.getPaymentAmount().divide(TWO)) > 0) {
        return "부분환불 50% 초과";
    }
    Long sellerId = loadSellerIdForSettlement(s.getId());
    Double rate = refundRates.get(sellerId);
    if (rate != null && rate > 0.30) {
        return String.format("셀러 환불률 높음 (%.1f%%)", rate * 100);
    }
    return null;
}
```

매일 02:15 cron 실행 — 룰 매치 시 자동 HOLD.

### CreateDailySettlements 가 셀러 schedule 평가

CapturedPaymentInfo 에 `sellerId` 추가, payment + order + product native join:

```java
SELECT pay.id, pay.order_id, pay.amount, pay.captured_at, prd.seller_id
FROM opslab.payments pay
JOIN opslab.orders   o   ON o.id = pay.order_id
LEFT JOIN opslab.products prd ON prd.id = o.product_id
WHERE pay.status = 'CAPTURED'
  AND pay.captured_at BETWEEN :start AND :end
```

서비스에서 모든 schedule 한 번 로드 (Map 캐시) 후 셀러 매칭, cron 평가:

```java
.filter(payment -> {
    if (payment.sellerId() == null) return true;
    SellerSettlementSchedule sched = schedules.get(payment.sellerId());
    if (sched == null) return true;
    return sched.shouldTriggerAt(triggerTime);
})
```

### Admin 대시보드 위젯

`GET /admin/settlement-dashboard` 한 번의 호출로 6 위젯 모두 반환:
- 상태별 카운트
- 오늘 매출 (gross / commission / net / count)
- HOLD 요약 + 최근 5건
- 셀러 매출 Top 5
- 환불률 Top 5 (이상 셀러 후보)

## Phase 4 — 운영 외부 연동

### 셀러 송금 + 알림

Hexagonal port:

```java
public interface SellerPayoutPort {
    PayoutResult triggerPayout(Long settlementId, Long sellerId, BigDecimal netAmount);
    record PayoutResult(boolean success, String externalTxId, String errorMessage) { ... }
}
```

데모 환경에선 `LoggingSellerPayoutAdapter` 가 90% 성공 시뮬 + `seller_payout_log` 테이블 기록. 운영에선 `BankApiSellerPayoutAdapter` (토스 정산 송금 API 등) 으로 어댑터만 교체하면 된다.

### bulk PDF (ZIP)

```
GET /settlements/bulk-pdf?sellerId=42&from=2026-04-01&to=2026-04-30
→ application/octet-stream + Content-Disposition: attachment; filename="settlements-seller42-...zip"
```

iText 8 로 단건 PDF 생성하던 기존 로직을 ZipOutputStream 으로 묶음.

```java
try (ZipOutputStream zip = new ZipOutputStream(baos)) {
    for (Number n : ids) {
        byte[] pdf = generateSettlementPdfUseCase.generate(n.longValue());
        zip.putNextEntry(new ZipEntry("settlement-" + n + ".pdf"));
        zip.write(pdf);
        zip.closeEntry();
    }
}
```

### 가장 골치 아팠던 함정

#### 1. PostgreSQL LATERAL random() 캐싱

100K 주문 시드를 만들 때:

```sql
CROSS JOIN LATERAL (SELECT (1 + floor(random() * prd.n)::int) AS idx) lat
```

이게 **per-row 평가가 아니라 한 번만** 평가되는 함정. 결과: 모든 주문이 같은 product_id. 해결은 PL/pgSQL FOR 루프로 명시적 루프.

#### 2. WebConfig.configureMessageConverters 가 default 컨버터 모두 제거

기존 코드:
```java
@Override
public void configureMessageConverters(List<HttpMessageConverter<?>> converters) {
    converters.add(stringConverter);     // ← 기본 ByteArray 컨버터 사라짐
    converters.add(jsonConverter);
}
```

이 한 줄로 PDF/ZIP 응답이 `HttpMessageNotWritableException: No converter for [class [B]` 로 500 에러. **`extendMessageConverters` 로 변경** 하면 default 유지하면서 추가만 가능.

#### 3. Spring Security 추가 차단

`/auth/dev/**` 데모 엔드포인트에 JwtAuthenticationFilter `shouldNotFilter` 만 추가했더니 여전히 401. SecurityFilterChain 의 `authorizeHttpRequests` 에도 `permitAll` 명시 필요.

## Phase 4.6 — Frontend Admin 대시보드

React + TypeScript + Tailwind 로:

- KPI 카드 4개 (오늘 count/gross/commission/net)
- 상태별 정산 카운트 (DONE/HOLD/REQUESTED/FAILED)
- HOLD 요약 + 최근 5건
- 셀러 Top 5 (gross 기준)
- 환불률 Top 5 (이상 셀러 후보)
- 즉시 트리거 버튼 (⚠️ Auto-Hold / ✅ Auto-Confirm)

검색·필터링 페이지 (`SettlementAdmin`) 도 일괄 hold/unhold 체크박스 + PDF 다운로드(blob, JWT 헤더 동행) + 환불 조정 모달까지.

## Micrometer 메트릭

```
lemuel.settlement.hold              (Counter)
lemuel.settlement.unhold            (Counter)
lemuel.settlement.hold.batch        (Counter)
lemuel.settlement.unhold.batch      (Counter)
lemuel.settlement.auto.confirmed    (Counter)
lemuel.settlement.payout.ok         (Counter)
lemuel.settlement.payout.fail       (Counter)
```

`/actuator/prometheus` 로 노출 → Grafana 에서 일별/시간별 추이.

## 데이터 시드 (시연·테스트용)

```
사용자        5,000명 (USER 4,912 / MANAGER 80 / ADMIN 8)
상품          1,001개 (10 카테고리 × 100)
셀러          75명 (MANAGER 중 정산 대상)
주문          100,000건 (PAID 87% / REFUNDED 4.6% / CANCELED 4.1% / CREATED 4.1%)
결제          95,887건 (TOSS 100%, 부분환불 9.98%)
정산          91,798건 (DONE 88% / REQUESTED 12% / FAILED 0.5%)
쿠폰          50개 + 사용 21,317건 (주문의 19%)
```

총 거래액 ₩422억, 수수료 ₩11.4억, 셀러 정산액 ₩369억 (3% 수수료 적용).

## 정리

Option D 하이브리드 정책의 핵심은 **자동화의 안전망**이다:

1. **자동** — 매일 03:30 cron 으로 D+3 후 자동 확정 → 운영 부담 거의 0
2. **검토** — admin 이 발견한 의심 거래를 HOLD 게이트로 격리 → 잘못된 송금 방지
3. **룰** — 시스템이 평소 패턴(평균 매출, 셀러 환불률) 을 학습해 의심도 자동 표시 → 사람의 부담 감소
4. **차등 schedule** — VIP 셀러 D+1, 신규 셀러 D+7 등 셀러별 정책 가능

이 4 가지가 결합되면 admin 1명이 100,000건 결제도 운영할 수 있다. 실제 코드는 헥사고날 아키텍처로 어댑터(은행 API/SMTP/Slack) 만 교체하면 운영 환경에 바로 투입 가능하다.

---

전체 소스: [github.com/MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement) `perf/security-round2` 브랜치
스택: Java 21 / Spring Boot 4.0.4 / PostgreSQL 17 / iText 8 / Micrometer / React 18 + TypeScript + Tailwind

**Tags**: #spring-boot #hexagonal #jpa #java #typescript #react #micrometer #cron #settlement
