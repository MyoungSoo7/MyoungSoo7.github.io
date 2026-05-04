---
layout: post
title: "Pessimistic vs Optimistic Lock — 도메인 특성에 맞는 동시성 전략"
date: 2026-05-04
categories: [backend, concurrency]
tags: [jpa, spring-boot, lock, transaction]
---

## 금액 도메인 → Pessimistic Lock

부분 환불에서는 동시 요청으로 인한 초과 환불이 절대 발생하면 안 됩니다.

```java
@Transactional(isolation = Isolation.REPEATABLE_READ)
public Refund refund(Long paymentId, BigDecimal amount, String idempotencyKey) {
    // SELECT FOR UPDATE — 다른 트랜잭션이 같은 결제를 수정하지 못하게 잠금
    Payment payment = loadPaymentPort.loadForUpdate(paymentId);
    
    if (payment.getRefundableAmount().compareTo(amount) < 0) {
        throw new RefundExceedsPaymentException();
    }
    // ...
}
```

## 재고 도메인 → Optimistic Lock

SKU 재고 차감은 짧은 트랜잭션 + 높은 동시성이라 재시도가 효율적입니다.

```java
// @Version 기반 Optimistic Lock + 최대 5회 재시도
for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
        txTemplate.execute(status -> {
            ProductVariant v = loadPort.loadById(variantId).orElseThrow();
            v.decreaseStock(quantity);  // stockQuantity < quantity면 예외
            savePort.save(v);           // UPDATE WHERE version = N
            return null;
        });
        return; // 성공
    } catch (OptimisticLockException e) {
        Thread.sleep(10L << (attempt - 1)); // 지수 백오프
    }
}
```

## 선택 기준

| 기준 | Pessimistic | Optimistic |
|------|-------------|------------|
| 충돌 빈도 | 높음 | 낮음 |
| 트랜잭션 길이 | 길어도 OK | 짧아야 효과적 |
| 실패 비용 | 높음 (금액) | 낮음 (재시도) |
| 처리량 | 제한적 | 높음 |

**핵심**: 도메인 특성에 따라 선택하되, 100스레드 동시성 테스트로 검증해야 합니다.
