---
layout: post
title: "SNS 피드 시스템 — Kafka at-least-once + DLQ 재처리"
date: 2026-05-04 05:00:00 +0900
categories: [project]
tags: [kafka, sse, spring-boot, event-driven]
---

## 프로젝트 소개

게시글, 댓글, 좋아요, 실시간 알림 기능을 갖춘 소셜 네트워크 서비스입니다. Kafka와 SSE를 활용한 실시간 이벤트 처리를 지원합니다.

**Live**: [sns.lemuel.co.kr](https://sns.lemuel.co.kr)

## 핵심 설계

### Kafka 비동기 이벤트

```java
// 좋아요 시 알림 이벤트 발행
alarmProducer.send(new AlarmEvent(
    AlarmType.NEW_LIKE_ON_POST,
    new AlarmArgs(userId, postId),
    postOwnerId
));
```

- at-least-once 보장 + eventId 멱등성
- Dead Letter Queue(DLQ) 재처리

### Redis 캐시

```java
public User loadUserByUsername(String userName) {
    return redisRepository.getUser(userName)
        .orElseGet(() -> {
            User user = userRepository.findByUserName(userName)
                .map(User::fromEntity).orElseThrow();
            redisRepository.setUser(user);  // DB 조회 후 Redis 갱신
            return user;
        });
}
```

### Soft Delete

`@SQLDelete` + `@Where(clause = "removed_at IS NULL")` — 삭제 시 타임스탬프 기록, 조회 시 자동 필터링.

## 기술 스택

Spring Boot 4 / Java 25 / PostgreSQL / Redis / Kafka / React
