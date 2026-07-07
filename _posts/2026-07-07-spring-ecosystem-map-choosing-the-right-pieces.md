---
layout: post
title: "Spring 은 *하나 의 프레임워크* 가 아니다 — 생태계 지도 읽는 법"
date: 2026-07-07 11:30:00 +0900
categories: [backend, spring]
tags: [spring, spring-boot, spring-cloud, spring-data, spring-batch, ecosystem, architecture]
---

"Spring 쓴다" 고 하면 사람 마다 다른 걸 떠올린다. 누구 는 웹 MVC, 누구 는 배치, 누구 는 Cloud Gateway. 그도 그럴 것 이 — **Spring 은 하나 의 프레임워크 가 아니라 수십 개 프로젝트 의 우산** 이기 때문이다. 이 글 은 아래 생태계 지도 를 *어떻게 읽고, 무엇 을 언제 고르는지* 를 정리 한다.

![Spring 생태계 지도 — Framework 중심에 Security/Cloud/Data/Batch/Kafka/Integration 등 수십 프로젝트](/assets/images/spring/spring-ecosystem-map.jpg)

---

## 1. 지도 의 구조 — *중심 하나, 위성 다수*

그림 은 어지러워 보이지만 구조 는 단순 하다:

- **중심**: `Spring Framework` — 나머지 전부 가 여기 에 붙는다.
- **왼쪽 위성**: 웹·표현 계열 — Security, Web Flow, HATEOAS, REST Docs, Session, Web Services…
- **오른쪽 위성**: 통합·데이터 계열 — Cloud, Integration, Data, Batch, AMQP, Kafka, LDAP…
- **아래 받침**: `Spring Boot`, `Spring IO Platform`, `Cloud Data Flow` — *생태계 를 구동 하는 런처*.

핵심 은 **위성 은 골라 쓰는 것** 이라는 점. 전부 쓰라는 게 아니라, *필요한 조각 만* 중심 에 꽂는다.

---

## 2. 무엇 이 이 모든 걸 *하나 로* 묶나

수십 개 프로젝트 가 따로 놀지 않는 이유 는, 전부 **Spring 코어 의 같은 프로그래밍 모델** 위 에 서 있기 때문이다:

- **IoC / DI 컨테이너** — 객체 를 *직접 new* 하지 않고 컨테이너 가 조립. 그래서 Security 든 Data 든 *같은 방식* 으로 끼워진다.
- **이식 가능한 추상화(PSA)** — `@Transactional`, `Repository` 처럼 *기술 을 감춘 일관된 인터페이스*. JPA→MyBatis, RabbitMQ→Kafka 를 갈아도 코드 모양 이 유지 (→ [PSA 글]({% post_url 2026-07-07-spring-service-abstraction-psa %})).
- **일관된 설정 모델** — 어노테이션·프로퍼티·자동설정 이 전 프로젝트 공통.

즉 **Spring 을 배운다는 건 "코어 프로그래밍 모델 하나" 를 배우는 것** 이고, 위성 은 그 모델 의 *응용* 이다. DI 를 이해 하면 40 개 프로젝트 가 같은 문법 으로 읽힌다.

---

## 3. Spring Boot — *생태계 의 진입점*

그림 아래 에서 Boot 가 받치고 있는 건 우연 이 아니다. Boot 는 *새 프로젝트* 가 아니라, **생태계 를 "그냥 되게" 만드는 런처** 다:

- **Auto-configuration** — 클래스패스 를 보고 "너 JPA 넣었네? DataSource 자동 세팅" 하는 식.
- **Starter** — `spring-boot-starter-data-jpa` 하나 로 관련 의존성 한 묶음.
- **Opinionated default** — 합리적 기본값 을 주고, 필요할 때만 덮어쓰게.

Boot 덕분 에 우리 는 *조립* 이 아니라 *조합* 만 한다. 나 는 Spring Boot 4 / Framework 7 을 기준 으로 쓴다.

---

## 4. 내가 실제 로 고른 조각 들

생태계 를 *다* 쓰지 않는다. 시스템 마다 *필요한 것 만* 꽂는다:

| 프로젝트 | 어디에 | 왜 |
|---|---|---|
| Spring Data (JPA) | 정산·거의 전부 | 영속성 추상화, Read-only Projection |
| Spring Batch | 정산 배치 | PENDING→CONFIRMED 정산 확정 배치 |
| Spring Security | 인증·인가 | JWT + Rate Limit |
| Spring Cloud Gateway | sparta MSA | 라우팅 + 인증 필터 |
| Spring for Apache Kafka | Outbox 발행 | 이벤트 기반 정산 |
| Spring AI | jabis · sparta 검색 | ChatClient + VectorStore(RAG) |

각 선택 은 *그림 의 한 조각 을 뽑아 온 것*. 정산 은 Data+Batch+Kafka, AI 서비스 는 Spring AI, MSA 는 Cloud Gateway — **한 우산 아래 라 조합 이 매끄럽다.**

---

## 5. 함정 — *지도 를 다 정복 하려 하지 마라*

생태계 가 넓다 보니 유혹 이 있다. "Spring Cloud 다 깔고, Integration 도 붙이고…". 하지만:

- 안 쓰는 위성 하나 = *영구 운영 세금*(의존성·버전·설정).
- "언젠가 쓸 것 같아서" 미리 넣는 건 [운영 에서 아픈 설계]({% post_url 2026-07-07-six-designs-that-hurt-in-operation %}) 의 *resume-driven / premature* 그 자체.

**지도 는 정복 대상 이 아니라 참조 대상 이다.** 통증(문제) 이 생기면 그때 해당 조각 을 찾아 꽂는다. 5 명 팀 에 Spring Cloud 풀스택 은 대개 과하다.

---

## 결론 — *하나 를 깊게, 나머지 는 지도 로*

Spring 을 잘 쓴다는 건 40 개 프로젝트 를 다 아는 게 아니다:

1. **코어(IoC/DI·PSA) 를 깊게** — 이게 전 생태계 를 관통 하는 문법.
2. **Boot 로 진입** — 조립 말고 조합.
3. **필요한 위성 만** — 통증 에 대한 응답 으로 고른다. 지도 는 "언제 무엇 이 있는지" 를 기억 하는 용도.

그림 은 "이 많은 걸 다 배워라" 가 아니라, **"필요할 때 여기서 찾아 쓰면 된다" 는 안심** 이다. 중심 하나 를 단단히 잡으면, 위성 은 그때그때 붙이면 된다.

*프레임워크 를 다 아는 사람 보다, 무엇 을 언제 안 써야 하는지 아는 사람 이 낫다.*
