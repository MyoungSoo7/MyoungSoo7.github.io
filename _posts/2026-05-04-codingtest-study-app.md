---
layout: post
title: "코딩테스트 학습 앱 — 100문제 + 카테고리 필터 + 풀이 관리"
date: 2026-05-04 01:30:00 +0900
categories: [project]
tags: [spring-boot, thymeleaf, h2, coding-test]
---

## 프로젝트 소개

프로그래머스/LeetCode 코딩테스트 문제를 관리하고 풀이를 기록하는 학습 앱입니다. 100개 문제를 카테고리/난이도/풀이 상태별로 필터링할 수 있습니다.

**Live**: [codingtest.lemuel.co.kr](https://codingtest.lemuel.co.kr)

## 핵심 기능

- **100개 문제**: BFS, DFS, DP, Greedy 각 10개 + 기타 60개
- **카테고리 필터**: 13개 카테고리 (투포인터, 슬라이딩윈도우, 이진탐색 등)
- **난이도 필터**: EASY / MEDIUM / HARD
- **풀이 상태**: NOT_ATTEMPTED / SOLVED / FAILED / RETRY
- **코드 관리**: 풀이 코드 + 메모 저장 (Java/Python/JS)
- **대시보드**: 진행률, 카테고리별 통계

## 기술적 포인트

JPA `@EntityGraph`로 N+1 해결:
```java
@EntityGraph(attributePaths = {"categories", "solutions"})
Optional<Problem> findById(Long id);
```

`open-in-view: false` 설정에서 Lazy Loading 에러를 방지하기 위해 Repository 레벨에서 fetch join을 적용했습니다.

## 기술 스택

Spring Boot 4 / Java 25 / H2 / Thymeleaf / Bootstrap 5
