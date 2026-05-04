---
layout: post
title: "Kafka + SSE로 실시간 알림 시스템 구현하기"
date: 2026-05-04 10:00:00 +0900
categories: [backend, messaging]
tags: [kafka, sse, spring-boot, event-driven]
---

## 왜 Kafka + SSE인가?

SNS 피드 시스템에서 좋아요/댓글 알림을 실시간으로 전달해야 했습니다.

| 방식 | 장점 | 단점 |
|------|------|------|
| 폴링 | 구현 간단 | 불필요한 요청, 지연 |
| WebSocket | 양방향 | 서버 리소스 큼, LB 복잡 |
| **SSE** | 단방향, HTTP 호환 | 단방향만 가능 |

알림은 서버→클라이언트 **단방향**이므로 SSE가 적합합니다. Kafka는 이벤트 내구성과 다중 컨슈머 지원을 위해 사용합니다.

## 흐름

```
[좋아요 이벤트] → Kafka 토픽 발행
                    ↓
              Kafka Consumer 수신
                    ↓
         SSE EmitterRepository에서 대상 유저 찾기
                    ↓
              SSE push → 브라우저 실시간 수신
```

## 핵심 코드

```java
// Kafka Producer — 좋아요 시 이벤트 발행
alarmProducer.send(new AlarmEvent(
    AlarmType.NEW_LIKE_ON_POST, 
    new AlarmArgs(userId, postId), 
    postOwnerId
));

// SSE Emitter — 클라이언트 연결
@GetMapping("/subscribe")
public SseEmitter subscribe(@AuthenticationPrincipal User user) {
    SseEmitter emitter = new SseEmitter(60 * 1000L);
    emitterRepository.save(user.getId(), emitter);
    return emitter;
}
```

**Live**: [sns.lemuel.co.kr](https://sns.lemuel.co.kr)
