---
layout: post
title: "패션 디자이너 매칭 플랫폼 — AI 프로필 생성 + 에스크로 결제"
date: 2026-05-04 07:00:00 +0900
categories: [project]
tags: [spring-boot, ai, modular-monolith, websocket]
---

## 프로젝트 소개

패션 디자이너와 의뢰인, 생산업체를 연결하는 3자 매칭 플랫폼입니다. AI 프로필 자동 생성, 실시간 3자 채팅, 에스크로 결제를 제공합니다.

**Live**: [fashion.lemuel.co.kr](https://fashion.lemuel.co.kr)

## 아키텍처: 모듈형 모놀리스

```
fashion-desgin/
├── member/        # 인증/인가, 3종 프로필 (CLIENT/PARTNER/ADMIN)
├── matching/      # 프로젝트 CRUD, 지원, AI 매칭
├── payment/       # 에스크로 결제/정산
├── chat/          # WebSocket + STOMP + Redis Pub/Sub
├── notification/  # 알림
├── ai/            # OpenAI 추상화 (Strategy 패턴)
├── storage/       # MinIO 파일 스토리지
└── plugin-fashion/# 패션 카테고리 전용 플러그인
```

11개 모듈, 모듈 간 느슨한 결합은 **Spring ApplicationEvent**로 구현.

## 핵심 기능

- **AI 프로필 생성**: 이력서 업로드 → AI가 프로필 자동 구성
- **플러그인 패턴**: `CategoryPlugin` 인터페이스로 카테고리 확장 (K-POP 굿즈 등)
- **3자 채팅**: 매칭 성사 시 자동 채팅방 생성 (디자이너+의뢰인+생산업체)

## 기술 스택

Spring Boot 4 / Java 25 / PostgreSQL / Redis / MinIO / WebSocket / Next.js
