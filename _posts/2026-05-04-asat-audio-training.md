---
layout: post
title: "ASAT — Web Audio API로 ±5ms 정밀도의 청각 재활 훈련 시스템 만들기"
date: 2026-05-04 14:00:00 +0900
categories: [project]
tags: [web-audio, spring-boot, staircase-algorithm, hexagonal]
---

## 프로젝트 소개

이명 환자·청각 재활 대상자를 위한 연구용 웹 애플리케이션입니다. Web Audio API 정밀 타이밍(±5ms) + 적응형 staircase 알고리즘 + 데이터 신뢰도 등급화(A/B/C/F)까지 고려한 임상 연구 지향 훈련 시스템입니다.

**Live**: [eln.lemuel.co.kr](https://eln.lemuel.co.kr)

## 왜 만들었는가

- 청각 재활 훈련은 "자극을 들려주는 것"이 아니라 **밀리초 단위 타이밍·개인별 적응형 난이도·데이터 품질 보증**이 전제되어야 함
- 고정 난이도 훈련은 개인별 JND(최소변별차)를 측정할 수 없음 → 적응형 staircase 필수
- 연구 데이터로 쓰려면 "reversal 몇 번 만에 수렴했는가, 정답률이 우연 수준인가, 헤드폰을 제대로 썼는가"까지 판정해야 함

## 핵심 설계 포인트

### 1. 적응형 알고리즘 (2-down 1-up Staircase)

```
2연속 정답 → 난이도 UP (step down)
1 오답 → 난이도 DOWN (step up)
→ 70.7% 정답률에 수렴 = 청각 역치
```

- TrainingSession / TrainingTrial / AdaptiveAlgorithmState를 별도 엔티티로 분리
- reversal 12회 도달 시 세션 자동 완료, 마지막 8개 reversal의 기하평균으로 JND 산출

### 2. 동시성 제어 (Optimistic Lock)

환불 도메인의 `PESSIMISTIC_WRITE`와 달리, 짧은 trial 트랜잭션 + 충돌 희귀 특성에 맞춰 **낙관적 락**을 선택했습니다.

```java
@Version
private Long version;
// 동일 세션에 동시 trial 기록 시 OptimisticLockException으로 차단
```

### 3. 데이터 신뢰도 등급화 (A/B/C/F)

| 등급 | 조건 |
|------|------|
| **A** | reversal ≥ 8 + 정답률 60~85% + 헤드폰 확인 |
| **B** | fallback (A도 C도 아닌 경우) |
| **C** | reversal < 8 / 정답률 비정상 / floor·ceiling 도달 |
| **F** | reversal 0회 (데이터 무효) |

### 4. 환경 검증 (Calibration) 선행 강제

훈련 전 헤드폰 확인 + L/R 채널 테스트 + 볼륨·오디오 지연 측정을 `CalibrationRecord`로 영속화. **"캘리브레이션 없이는 훈련 불가"** 정책.

## 아키텍처

- Backend: Spring Boot 4.0 / Java 25 / Hexagonal
- Frontend: Next.js 16 / React 19 / TypeScript 5
- Audio: Web Audio API (`AudioContext.currentTime` 스케줄링)
- DB: PostgreSQL 16 / Flyway V1~V36
- Cache: Redis
- Test: JUnit 5 + TestContainers

## 교훈

> 측정 도메인은 "타이밍 정밀도 + 재현성"이 핵심 — 500ms 재생과 ±5ms RT 측정이 무너지면 JND는 쓰레기값

> 데이터 품질 등급은 옵션이 아니라 필수 — 정산의 "CONFIRMED"처럼, 연구 데이터도 "A등급"이어야 논문에 쓸 수 있다
