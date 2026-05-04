---
layout: post
title: "Redis 분산 락으로 좌석 예매 동시성 제어하기"
date: 2026-05-04 09:00:00 +0900
categories: [backend, concurrency]
tags: [redis, distributed-lock, node-js, concurrency]
---

## 문제 상황

만석 콘서트에서 같은 좌석에 동시 예매 요청이 들어오면?

DB Pessimistic Lock은 단일 인스턴스에서만 동작합니다. 다중 서버 환경에서는 **Redis 분산 락**이 필요합니다.

## 구현 (Node.js + Redis)

```typescript
// 좌석별 락 키
const lockKey = `seat:${eventId}:${seatNo}`;

// Redis SETNX로 락 획득 (TTL 10분)
const acquired = await redis.set(lockKey, oderId, 'NX', 'EX', 600);

if (!acquired) {
    throw new HttpError(409, 'SEAT_ALREADY_HELD', '이미 선점된 좌석');
}

try {
    // 결제 진행
    await processPayment(orderId);
    // 좌석 상태 변경: Hold → Reserved
    await updateSeatStatus(seatNo, 'RESERVED');
} finally {
    // 락 해제
    await redis.del(lockKey);
}
```

## 좌석 상태 전이

```
Available → Hold (락 획득) → Reserved (결제 완료) → Issued (발권)
                ↓ (TTL 만료)
            Available (자동 해제)
```

## SKU Optimistic Lock과의 차이

| | Redis 분산 락 | Optimistic Lock |
|---|---|---|
| 대상 | 좌석 (1:1 배타적) | 재고 (수량 차감) |
| 재시도 | 의미 없음 (fail-fast) | 최대 5회 재시도 |
| 이유 | 다른 사람이 이미 선택 | 일시적 충돌, 재시도로 해결 |

**GitHub**: [global-seat-ticketing](https://github.com/MyoungSoo7/global-seat-ticketing)
