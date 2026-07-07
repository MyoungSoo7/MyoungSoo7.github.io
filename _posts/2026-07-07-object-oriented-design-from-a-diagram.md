---
layout: post
title: "객체지향 설계 를 그림 한 장 으로 읽기 — *책임* 과 *의존성 의 방향*"
date: 2026-07-07 11:10:00 +0900
categories: [backend, architecture, oop]
tags: [oop, object-oriented, solid, hexagonal, dependency-inversion, design, abstraction]
---

객체지향 설계 를 "상속·다형성·캡슐화" 같은 *문법* 으로만 배우면, 정작 *왜 그렇게 나누는지* 를 놓친다. 객체지향 의 본질 은 두 가지 다 — **책임 을 어떻게 나누고, 의존성 이 어느 방향 으로 흐르게 하는가.** 이 글 은 아래 그림 한 장 으로 그 두 가지 를 읽는다.

![객체지향 설계 다이어그램 — Mapper / Application Core / Engine / Driver·Second Driver / Dataset·Database·Message Queue](/assets/images/oop/object-oriented-design-diagram.jpg)

이 그림 은 특정 프레임워크 가 아니라 *잘 나뉜 객체 구조* 의 전형 이다. 하나씩 뜯어 보자.

---

## 1. 각 상자 는 *하나 의 책임* 을 진다 (SRP)

그림 의 컴포넌트 는 각자 *하나 의 일* 만 한다:

- **Mapper** — 스키마(XML SCHEMA) 를 보고 매핑 만.
- **Application Core** — 입력(XML Documents) 을 받아 조율 만.
- **Engine** — 실제 처리 로직 만.
- **Driver / Second Driver** — 결과 를 *바깥*(Dataset·Database) 으로 내보내기 만.

이게 **단일 책임 원칙(SRP)** 이다. "Engine 이 DB 도 붙이고 XML 도 파싱 하고…" 로 뭉치면, 한 곳 을 고칠 때 *상관없는 다른 것 이 깨진다*. **바뀌는 이유 가 다른 것 은 다른 객체 로.** 상자 를 나누는 기준 은 *기능* 이 아니라 *변경 이유* 다.

---

## 2. Engine 은 *구체* 가 아니라 *추상* 에 의존 한다 (DIP·OCP)

그림 의 핵심 은 여기다. **Engine → Driver → Dataset**, **Engine → Second Driver → Database.** Engine 은 Dataset 이나 Database 를 *직접* 알지 않는다. *Driver 라는 추상* 을 통해 내보낼 뿐.

- 새 출력 대상(예: S3, Kafka) 이 생기면? → **Third Driver 를 하나 더 꽂으면 된다.** Engine 은 안 건드린다.
- 이게 **개방-폐쇄 원칙(OCP)** — *확장 에는 열려 있고, 변경 에는 닫혀 있다.*
- 그리고 **의존성 역전(DIP)** — 상위(Engine) 가 하위(Database) 에 의존 하지 않고, *둘 다 추상(Driver 인터페이스)* 에 의존 한다.

```
❌ Engine ──▶ Database (구체에 직접 의존)
✅ Engine ──▶ Driver(추상) ◀── DatabaseDriver (구체가 추상을 구현)
```

객체지향 이 강력한 건 상속 이 아니라 **이 "추상 을 향한 의존" 을 다형성 으로 갈아끼우는" 능력** 때문이다. Driver 하나 를 갈면 출력 이 통째로 바뀐다.

---

## 3. Message Queue — *결합 을 끊는 경계*

Engine 이 Message Queue 로 보내는 화살표 는 *비동기 경계* 다. Engine 은 큐 에 던지고 *자기 일 을 계속* 한다. 소비자 가 누구 인지, 몇 명 인지 몰라도 된다.

이건 객체 사이 의 **낮은 결합(loose coupling)** 을 시간 축 으로 확장 한 것. 동기 호출 은 *"네가 끝날 때까지 기다린다"* 지만, 큐 는 *"남겨둘 테니 알아서 가져가"* 다. 결합 을 끊는 만큼 *자유* 를 얻고, 대신 *즉시성* 을 내준다(→ [설계 세 축]({% post_url 2026-07-07-backend-design-three-axes %}) 의 결합도↔일관성).

---

## 4. 안쪽(Core) 과 바깥(IO) 이 나뉜다 — *헥사고날 의 뿌리*

그림 을 멀리서 보면 구조 가 보인다:

- **안쪽** = Application Core + Engine (순수 로직·도메인)
- **바깥** = Mapper, Driver, Dataset, Database, Message Queue (외부 세계·IO)
- 안쪽 은 바깥 을 *추상 으로만* 안다. 바깥 이 안쪽 을 향해 꽂힌다.

이게 정확히 **헥사고날 아키텍처(Ports & Adapters)** 다. Driver·Second Driver 는 *출력 어댑터*, Engine·Core 는 *도메인*. 도메인 은 "DB 가 뭔지" 몰라도 돌아가고, DB 는 나중에 갈아끼울 수 있다.

나 도 이 원칙 을 실제 로 강제 한다:

- 도메인 은 Spring/JPA 를 *모른다*. adapter 만 안다.
- 규칙 위반(도메인 이 인프라 를 import) 은 **ArchUnit 으로 빌드 에서 reject**.
- 정산 에서 order 테이블 을 읽을 때 도, `@Immutable` Read-only Projection *어댑터* 로 격리 → Core 는 "어디서 오는 데이터" 인지 신경 안 씀.

즉 그림 의 "Core 를 IO 가 감싸는" 구조 는, 유행 이 아니라 *변경 비용 을 낮추는* 오래된 지혜다. (→ [정산 시스템 을 KPI 로]({% post_url 2026-07-03-settlement-system-kpi %}))

---

## 5. 되먹임 화살표 — *제어 의 흐름 ≠ 의존 의 방향*

그림 에서 Driver 가 다시 Mapper 로 돌아가는 화살표 가 있다. 여기서 헷갈리기 쉬운 걸 짚자 — **"데이터 가 흐르는 방향" 과 "코드 가 의존 하는 방향" 은 다르다.**

- 데이터·제어 는 순환 할 수 있다(파이프라인).
- 하지만 *컴파일 타임 의존* 은 *한 방향(안쪽 을 향해)* 이어야 순환 의존 이 안 생긴다.

좋은 객체지향 설계 는 이 둘 을 분리 한다. 실행 흐름 은 자유롭게, *의존 그래프 는 비순환(acyclic)* 으로. 이게 무너지면 [운영 에서 아픈 설계]({% post_url 2026-07-07-six-designs-that-hurt-in-operation %}) 의 "distributed monolith" 같은 얽힘 이 된다.

---

## 결론 — 객체지향 은 *명사 가 아니라 경계 의 기술*

객체지향 설계 를 잘 한다는 건 클래스 를 많이 만드는 게 아니다:

1. **책임 을 변경 이유 로 나눈다** (SRP) — 상자 하나 = 바뀌는 이유 하나.
2. **구체 가 아니라 추상 에 의존 한다** (DIP·OCP) — Driver 를 갈아끼우듯, 확장 은 꽂기 로.
3. **결합 을 의식적 으로 끊는다** — 필요한 곳 은 큐·이벤트 로 시간 결합 까지 분리.
4. **의존 을 안쪽(도메인) 으로 모은다** — 헥사고날. 바깥 은 언제든 갈아끼울 수 있게.

그림 한 장 이 말 하는 건 결국 이거다 — **잘 나뉜 객체 는, 어디 를 바꿔도 그 변경 이 *그 상자 안 에서 멈춘다*.** 변경 이 번지지 않는 구조, 그게 객체지향 설계 의 목적 이다.

*좋은 객체지향 은 "무엇 을 클래스 로 만드나" 가 아니라, "변경 을 어디서 멈추게 하나" 의 문제다.*
