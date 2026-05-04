---
layout: post
title: "약국 추천 서비스 — 카카오 지도 API + Redis 캐시 + Retry/Backoff"
date: 2026-05-04 04:00:00 +0900
categories: [project]
tags: [spring-boot, redis, kakao-api, retry]
---

## 프로젝트 소개

사용자 위치 기반으로 가까운 약국을 추천하는 서비스입니다. 카카오 지도 API + Redis 캐시 + 외부 API 장애 대응(Retry/Backoff)을 구현했습니다.

**Live**: [pharmacy.lemuel.co.kr](https://pharmacy.lemuel.co.kr)

## 핵심 설계

- **카카오 지도 API**: 주소 → 좌표 변환, 거리 계산
- **Redis 캐시**: 약국 데이터 캐싱으로 API 호출 최소화
- **Retry/Backoff**: 외부 API 장애 시 지수 백오프 재시도
- **DDD 도메인 분리**: 약국, 위치, 추천 도메인 분리

## 기술 스택

Spring Boot 4 / Java 25 / Redis / Kakao API
