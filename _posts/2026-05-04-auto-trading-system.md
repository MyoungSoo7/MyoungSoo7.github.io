---
layout: post
title: "자동 주식매매 시스템 — KIS API + 이동평균선/RSI 전략"
date: 2026-05-03 23:00:00 +0900
categories: [project]
tags: [spring-boot, stock-trading, kis-api, auto-trading]
---

## 프로젝트 소개

한국투자증권 Open API를 활용한 자동 주식매매 시스템입니다. 이동평균선 크로스와 RSI 전략으로 평일 장 시간에 자동 매매합니다.

**Live**: [stock.lemuel.co.kr](https://stock.lemuel.co.kr)

## 핵심 기능

- **KIS API 연동**: OAuth 인증, 실시간 시세, 자동 주문, 잔고 조회
- **매매 전략 2종**: 이동평균선 골든/데드 크로스 + RSI 과매수/과매도
- **자동 스케줄러**: 평일 09:00~15:30 매 분 실행
- **텔레그램 알림**: 매수/매도 시 실시간 알림
- **대시보드**: 포트폴리오, 매매이력, 전략 설명

## 매매 전략

### 이동평균선 크로스 (MA Cross)

5일 이동평균선이 20일선을 **상향 돌파(골든크로스) → 매수**, **하향 돌파(데드크로스) → 매도**.

### RSI (Relative Strength Index)

14일 기준 RSI가 **30 이하(과매도) → 매수**, **70 이상(과매수) → 매도**.

## 감시 종목

삼성전자(005930), SK하이닉스(000660), NAVER(035420), 카카오(035720)

## 기술 스택

Spring Boot 4 / Java 25 / PostgreSQL / KIS Open API / Docker

**GitHub**: [MyoungSoo7/auto-trading](https://github.com/MyoungSoo7/auto-trading)
