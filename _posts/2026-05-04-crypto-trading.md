---
layout: post
title: "빗썸 자동매매 시스템 — 볼린저 밴드 + RSI 24시간 자동 트레이딩"
date: 2026-05-03 22:00:00 +0900
categories: [project]
tags: [spring-boot, bithumb, crypto, auto-trading, bollinger]
---

## 프로젝트 소개

빗썸 API를 활용한 암호화폐 자동매매 시스템입니다. BTC, ETH, XRP, SOL 4개 코인을 24시간 모니터링하고 볼린저 밴드 + RSI 전략으로 자동 매매합니다.

**Live**: [crypto.lemuel.co.kr](https://crypto.lemuel.co.kr)

## 핵심 기능

- **빗썸 API 연동**: HMAC-SHA512 서명 인증, 시세/주문/잔고
- **볼린저 밴드 전략**: 하단 이탈 → 매수, 상단 이탈 → 매도
- **RSI 전략**: 25 이하 → 매수, 75 이상 → 매도
- **24시간 운영**: 5분 주기 자동 실행 (코인은 장 마감 없음)
- **대시보드**: 실시간 시세, 잔고, 매매이력

## 주식 자동매매와의 차이

| | 주식 (KIS API) | 코인 (빗썸 API) |
|---|---|---|
| 운영 시간 | 평일 09:00~15:30 | 24시간 365일 |
| 인증 | OAuth JWT | HMAC-SHA512 |
| 전략 | 이동평균선 + RSI | 볼린저 밴드 + RSI |
| 최소 단위 | 1주 | 소수점 가능 |

## 기술 스택

Spring Boot 4 / Java 25 / PostgreSQL / Bithumb API / Docker

**GitHub**: [MyoungSoo7/crypto-trading](https://github.com/MyoungSoo7/crypto-trading)
