---
layout: post
title: "Jabis — 개인 AI 비서 (일정/메모/할일 관리)"
date: 2026-05-04 01:40:00 +0900
categories: [project]
tags: [spring-boot, ai, openai, anthropic]
---

## 프로젝트 소개

AI 기반 개인 비서 애플리케이션입니다. 일정, 메모, 할일을 관리하고 AI와 대화할 수 있습니다.

**Live**: [jabis.lemuel.co.kr](https://jabis.lemuel.co.kr)

## 핵심 기능

- **AI 채팅**: OpenAI/Anthropic API 연동
- **일정 관리**: 캘린더 기반 일정 CRUD
- **메모**: 마크다운 메모 관리
- **할일**: 체크리스트 기반 TODO 관리

## 모듈 구조

```
jabis/
├── assistant/   # AI 채팅
├── calendar/    # 일정 관리
├── memo/        # 메모
├── todo/        # 할일
└── core/        # 공통 설정
```

## 기술 스택

Spring Boot 4 / Java 25 / PostgreSQL / React / OpenAI + Anthropic API
