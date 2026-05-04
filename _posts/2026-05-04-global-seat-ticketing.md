---
layout: post
title: "글로벌 좌석 예매 시스템 — Node.js + Redis 분산 락 + BullMQ"
date: 2026-05-04 01:50:00 +0900
categories: [project]
tags: [node-js, typescript, redis, distributed-lock, bullmq]
---

## 프로젝트 소개

글로벌 공연/투어/액티비티 실시간 예약 및 발권 플랫폼입니다. 좌석 상태 제어 + 공급사 API 연동이 핵심입니다.

## 좌석 상태 전이

```
Available → Hold → Reserved → Issued
```

- **Hold**: Redis SETNX 기반 분산 락, TTL 10분
- **Reserved**: 결제 완료 후 상태 전환
- **Issued**: 발권 완료, QR/바코드 생성

## 핵심 설계

- **분산 락**: Redis SETNX + TTL로 동시 예매 방지
- **BullMQ**: 좌석 해제, 재고 동기화, 정산 배치 큐
- **Adapter Pattern**: 공급사별 API 어댑터 + Circuit Breaker
- **정산 이원화**: KR/US 법인별 분리, 결제 시점 환율 스냅샷

## 기술 스택

Node.js / TypeScript / Fastify / PostgreSQL / Redis Cluster / BullMQ / Next.js 15 / Toss + Stripe
