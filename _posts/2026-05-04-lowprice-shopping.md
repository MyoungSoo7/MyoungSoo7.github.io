---
layout: post
title: "최저가 쇼핑 — 네이버 API + Scheduler 가격 배치 갱신"
date: 2026-05-04 01:00:00 +0900
categories: [project]
tags: [spring-boot, naver-api, scheduler, kakao-oauth]
---

## 프로젝트 소개

네이버 쇼핑 API를 활용한 최저가 상품 검색 서비스입니다. Kakao OAuth 인증, Scheduler 기반 가격 배치 갱신을 지원합니다.

**Live**: [lowshopping.lemuel.co.kr](https://lowshopping.lemuel.co.kr)

## 핵심 기능

- **네이버 쇼핑 API**: 상품 검색 + 가격 비교
- **Kakao OAuth**: 소셜 로그인
- **Scheduler**: 등록 상품 가격 주기적 갱신
- **관심 상품**: 즐겨찾기 + 가격 변동 알림

## 기술 스택

Spring Boot 4 / Java 25 / Thymeleaf / Naver API / Kakao OAuth
