---
layout: post
title: "K-POP 굿즈 래플 시스템 — SHA-256 해시 체인으로 투명성 보장"
date: 2026-05-04 08:00:00 +0900
categories: [project]
tags: [spring-boot, raffle, hash-chain, toss-payments]
---
{% raw %}

## 프로젝트 소개

K-POP 팬덤 대상 온라인 굿즈 뽑기(래플) 플랫폼입니다. 100% 당첨(꽝 없음) 시스템으로, 수량 기반 확률 계산 + SHA-256 해시 체인으로 투명성을 보장합니다.

**Live**: [goods.lemuel.co.kr](https://goods.lemuel.co.kr)

## 핵심 설계

### 해시 체인으로 조작 불가능한 추첨

```
Hash = SHA-256(drawId + seed + result + timestamp + prevHash)
```

- 추첨 전 시드값의 해시를 공개
- 추첨 후 시드값을 공개하면 누구나 검증 가능
- 각 라운드를 이전 해시와 연결 → 중간 조작 탐지

### 비관적 락으로 재고 동시성 제어

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT r FROM RaffleItem r WHERE r.id = :id")
Optional<RaffleItem> findByIdForUpdate(@Param("id") Long id);
```

### 포인트 선차감

뽑기 전 포인트 차감 → 실패 시 환불. Toss Payments PG 연동으로 포인트 충전.

## 기술 스택

Spring Boot 4 / Java 25 / PostgreSQL / Redis / Next.js / WebSocket(STOMP) / Toss Payments

{% endraw %}
