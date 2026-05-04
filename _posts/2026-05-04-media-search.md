---
layout: post
title: "Media Search — Pexels API로 무료 이미지/동영상 검색 사이트 만들기"
date: 2026-05-04 00:00:00 +0900
categories: [project]
tags: [spring-boot, pexels-api, thymeleaf, media]
---

## 프로젝트 소개

무료 고품질 이미지와 동영상을 검색하고 다운로드할 수 있는 미디어 검색 서비스입니다. Pexels API를 활용하여 수백만 장의 무료 사진과 동영상을 제공합니다.

**Live**: [media.lemuel.co.kr](https://media.lemuel.co.kr)

## 핵심 기능

- **사진 검색**: 키워드로 고품질 무료 사진 검색
- **동영상 검색**: HD 무료 동영상 검색
- **다운로드**: 원본 해상도 다운로드
- **큐레이션**: 메인 화면에 Pexels 추천 사진
- **Caffeine 캐시**: 동일 검색 10분간 캐싱 (API 호출 최소화)
- **반응형 UI**: 다크 테마, 모바일 지원

## 아키텍처

```
사용자 → Spring Boot (Thymeleaf)
              ↓
         PexelsService
              ↓ (RestClient + Caffeine Cache)
         Pexels API (photos + videos)
              ↓
         검색 결과 → 그리드 UI 렌더링
```

## 핵심 코드

```java
@Cacheable(value = "pexels-photos", key = "#query + '-' + #page")
public SearchResult searchPhotos(String query, int page, int perPage) {
    Map<String, Object> response = restClient.get()
        .uri("/v1/search?query={q}&page={p}&per_page={pp}", query, page, perPage)
        .retrieve()
        .body(new ParameterizedTypeReference<>() {});
    // ... 결과 매핑
}
```

## API 엔드포인트

```
GET /              → 큐레이션 사진 (메인)
GET /search?q=nature&type=photo  → 사진 검색
GET /search?q=ocean&type=video   → 동영상 검색
GET /api/search?q=korea          → JSON API
```

## 기술 스택

Spring Boot 4 / Java 25 / Thymeleaf / Pexels API / Caffeine Cache / Docker

**GitHub**: [MyoungSoo7/media-search](https://github.com/MyoungSoo7/media-search)
