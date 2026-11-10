---
layout: post
title: "MSA · EDA · CDC · CQRS 비교 — 넷은 같은 층의 선택지가 아니다"
date: 2026-11-10 23:32:45 +0900
categories: [architecture, msa]
tags: [msa, microservices, eda, event-driven, cdc, debezium, cqrs, outbox, event-sourcing]
---

MSA, EDA, CDC, CQRS는 한 문장에 같이 나오는 일이 많다. 그래서 "넷 중 무엇을 고를까" 하는 식으로 비교되곤 한다. 하지만 넷은 **서로 다른 질문에 대한 답**이다. 고르는 대상이 아니라 *겹쳐 쓰는* 대상이다. 이 글은 각각이 어떤 문제를 풀려고 나왔는지, 어느 층에서 작동하는지, 실제로 어떻게 맞물리는지를 1차 출처를 기준으로 정리한다.

## 1. 한 장 요약 — 층이 다르다

| | **MSA** | **EDA** | **CDC** | **CQRS** |
| --- | --- | --- | --- | --- |
| 정체 | 아키텍처 *스타일* (시스템 분해·배포 단위) | 통신 *스타일* (상호작용 방식) | 데이터 통합 *기법* (변경 포착) | 모델링 *패턴* (읽기/쓰기 모델 분리) |
| 답하는 질문 | "시스템을 무엇으로 쪼개고 어떻게 따로 배포하나?" | "서비스끼리 무엇으로 대화하나?" | "DB에 일어난 변경을 어떻게 빠짐없이 밖으로 내보내나?" | "쓰기에 맞춘 모델로 읽기까지 감당해야 하나?" |
| 작동 범위 | 시스템 전체 | 서비스 사이 | DB ↔ 외부 | 서비스 하나 안 (또는 한 바운디드 컨텍스트) |
| 대표 출처 | Lewis & Fowler (2014) | Fowler (2017) | Debezium 문서 | Greg Young (2010), Fowler (2011) |
| 대가 | 분산 시스템 운영 비용 | 흐름이 코드에 안 보임 | 스키마 결합·운영 컴포넌트 추가 | 모델 둘 + 최종 일관성 |

비교표를 한 줄로 줄이면 이렇다. **MSA는 "어떻게 나눌지", EDA는 "나뉜 것끼리 어떻게 말할지", CDC는 "말할 거리를 DB에서 어떻게 뽑을지", CQRS는 "읽는 쪽과 쓰는 쪽을 같은 모델로 둘지"를 다룬다.**

## 2. MSA — 독립 배포가 핵심

Lewis와 Fowler는 마이크로서비스를 이렇게 정의했다. *하나의 애플리케이션을 작은 서비스들의 묶음으로 개발하되, 각 서비스는 자기 프로세스에서 돌고 가벼운 메커니즘(흔히 HTTP API)으로 통신하며, 비즈니스 역량을 중심으로 만들어지고, 완전 자동화된 배포로 독립 배포할 수 있다* ([Lewis & Fowler, 2014](https://martinfowler.com/articles/microservices.html)).

- **푸는 문제**: 모놀리스는 작은 변경에도 전체를 다시 빌드하고 배포해야 한다. 팀과 서비스가 같은 릴리스 열차에 묶인다.
- **도입 전후 델타**: 배포 단위가 "시스템 전체"에서 "서비스 하나"로 바뀐다. 같은 글은 *분산된 데이터 관리*(Decentralized Data Management)도 특징으로 꼽는다. 서비스마다 자기 DB를 갖는다.
- **대가**: Fowler는 1년 뒤 "Microservice Premium"에서, 마이크로서비스가 복잡한 시스템을 다루기 위한 방식이지만 *그 자체로 복잡성을 들여온다*고 썼다. 자동 배포, 모니터링, 장애 대응, **최종 일관성** 같은 분산 시스템 비용을 치러야 한다는 것이다 ([Fowler, 2015](https://martinfowler.com/bliki/MicroservicePremium.html)).

여기서 나머지 셋이 등장할 이유가 생긴다. **DB를 쪼갰으니 다른 서비스의 데이터를 어떻게 알 것인가**라는 문제다.

## 3. EDA — "이벤트"라는 말에는 네 가지 뜻이 있다

Fowler는 Thoughtworks 내부 워크숍 결과를 정리하면서, 사람들이 "event-driven"이라고 부르는 것이 실제로는 *꽤 다른 것들*이라고 결론 내렸다 ([Fowler, 2017](https://martinfowler.com/articles/201701-event-driven.html)).

| 패턴 | 이벤트에 담기는 것 | 얻는 것 | 잃는 것 |
| --- | --- | --- | --- |
| Event Notification | "바뀌었다" + ID 정도 | 낮은 결합, 쉬운 구성 | 여러 이벤트에 걸친 흐름이 코드에 안 보이고, 운영 중 모니터링으로만 파악된다 |
| Event-Carried State Transfer | 바뀐 데이터 자체 | 원천 시스템이 죽어도 동작, 원격 호출 지연 제거 | 데이터 사본이 많아지고, 받는 쪽이 상태 관리 부담을 진다 |
| Event Sourcing | 모든 상태 변경 이력 | 과거 상태 재구성 | 저장·재생 설계 복잡도 |
| CQRS | (이벤트 패턴 목록에 같이 언급) | — | — |

- **푸는 문제**: MSA에서 서비스끼리 동기 호출을 연쇄로 걸면 하나가 느려질 때 전체가 느려진다. Lewis & Fowler의 사이드바 제목부터가 "Synchronous calls considered harmful"이다.
- **도입 전후 델타**: 호출자가 "누구에게 무엇을 시킬지"를 알던 구조가, 발행자는 "무슨 일이 일어났는지"만 알리는 구조로 바뀐다.
- **함정**: Fowler는 받는 쪽이 특정 행동을 하길 기대하면서 그걸 이벤트로 포장하는 것을 *passive-aggressive command*라고 부른다. 그럴 때는 명령 메시지를 써야 한다.

## 4. CDC — 이벤트를 "빠짐없이" 내보내는 기법

EDA를 하려면 "DB에 저장했다"와 "이벤트를 보냈다"가 함께 일어나야 한다. 둘을 따로 하면(dual write) 커밋은 됐는데 이벤트 발행 직전에 죽는 경우가 생긴다. 2PC는 DB와 브로커가 지원하지 않거나 결합이 심해 대개 쓸 수 없다 ([microservices.io — Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)).

CDC(Change Data Capture)는 **DB의 트랜잭션 로그를 읽어** 변경을 이벤트로 바꾼다. Debezium 문서는 폴링이나 dual write 같은 다른 방식과 비교한 로그 기반 CDC의 장점을 이렇게 든다 ([Debezium Features](https://debezium.io/documentation/reference/stable/features.html)).

- 모든 데이터 변경이 포착된다.
- 잦은 폴링에 드는 CPU 없이 낮은 지연으로 이벤트가 나온다. Debezium은 MySQL·PostgreSQL에서 *밀리초 단위*라고 설명한다. 벤더 문서의 주장이고, 중립적인 제3자 측정은 확인하지 못했다.
- "Last Updated" 같은 컬럼을 추가하는 등 데이터 모델을 바꿀 필요가 없다.
- 삭제도 포착한다.

**CDC를 그대로 쓸 때의 함정**: 테이블 행 변경을 그대로 내보내면 다른 서비스가 *내 테이블 스키마*에 결합된다. MSA가 DB를 쪼갠 이유를 우회해 버리는 셈이다. 그래서 실무에서는 대개 **Transactional Outbox와 결합한다.**

1. 서비스는 비즈니스 데이터와 함께 `outbox` 테이블에 *도메인 이벤트*를 **같은 트랜잭션으로** 저장한다. 그러면 커밋됐을 때만 이벤트가 존재한다.
2. CDC가 `outbox` 테이블만 읽어 브로커로 보낸다. Debezium은 이를 위한 Outbox Event Router SMT를 제공한다 ([Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)).
3. 릴레이가 같은 메시지를 두 번 보낼 수 있으므로 **소비자는 멱등해야 한다**. microservices.io는 처리한 메시지 ID를 추적하는 방법을 권한다.

정리하면 이렇다. **CDC는 EDA의 "배관"이다. 무엇을 보낼지(도메인 이벤트)는 outbox가 정하고, 빠짐없이 보내는 일은 CDC가 맡는다.**

## 5. CQRS — 읽기와 쓰기를 다른 모델로

Fowler는 CQRS를 Greg Young에게서 처음 들었다고 밝히며, 핵심을 *갱신에 쓰는 모델과 읽기에 쓰는 모델을 다르게 둘 수 있다*는 것으로 요약했다 ([Fowler, 2011](https://martinfowler.com/bliki/CQRS.html)). 이름은 Bertrand Meyer의 CQS(Command-Query Separation) 용어에서 왔다.

- **푸는 문제**: Microsoft의 아키텍처 문서는 하나의 CRUD 모델로 읽기와 쓰기를 다 감당할 때의 문제로 네 가지를 든다. 읽기·쓰기 표현의 불일치, 락 경합, 복잡한 조회로 인한 성능 저하, 보안 경계가 겹치는 것이다 ([Azure Architecture Center — CQRS](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)).
- **도입 전후 델타**: 커맨드는 "객실 예약"처럼 *비즈니스 의도*로, 쿼리는 도메인 로직 없는 DTO로 바뀐다. 읽기 모델은 화면에 맞춘 비정규화 저장소(검색엔진, 리포팅 DB 등)가 될 수 있다.
- **같은 DB여도 된다**: Fowler는 두 모델이 같은 DB를 공유할 수도, 별도 DB를 쓸 수도 있다고 적었다. *CQRS = DB 두 개*가 아니다.
- **경고**: 같은 글에 이런 문장이 있다. *"대부분의 시스템에서 CQRS는 위험한 복잡성을 더한다."* 적용 범위는 시스템 전체가 아니라 **특정 바운디드 컨텍스트**로 한정하라는 것이 Fowler의 권고다.
- **Event Sourcing과는 별개다**: 둘은 자주 같이 쓰이지만 CQRS가 Event Sourcing을 요구하지는 않는다. Event Sourcing은 *모든 상태 변경을 이벤트 시퀀스로 저장하는* 별도 패턴이다 ([Fowler, 2005](https://martinfowler.com/eaaDev/EventSourcing.html)).

## 6. 넷이 맞물리는 그림

```
[주문 서비스]  ← MSA: 독립 배포, 자기 DB
   │  ① 주문 저장 + outbox insert (한 트랜잭션)
   ▼
 orders DB ──② CDC(Debezium)가 outbox 만 읽음──▶ Kafka 토픽 "order.placed"
                                                     │  ← EDA: 이벤트로 통신
             ┌───────────────────────────────────────┼───────────────────────┐
             ▼                                       ▼                       ▼
     [배송 서비스]                          [정산 서비스]              [주문조회 뷰]
  Event-Carried State Transfer        멱등 소비(처리 ID 기록)      ← CQRS 읽기 모델
  (주문 사본 보관)                                                    (검색용 비정규화)
```

- **MSA**가 문제를 만들었다. DB가 쪼개졌다.
- **EDA**가 통신 방식을 정한다. 동기 호출 대신 이벤트로 알린다.
- **CDC + Outbox**가 이벤트 유실을 막는다. 커밋된 것만, 빠짐없이 내보낸다.
- **CQRS**가 이벤트를 받아 *읽기 전용 모델*을 따로 만든다. 쓰기 모델을 조회 요구로부터 보호한다.

## 7. 언제 무엇을 — 거꾸로 묻기

| 증상 | 먼저 볼 것 | 필요 없는 경우 |
| --- | --- | --- |
| 한 팀의 배포가 다른 팀을 계속 막는다 | MSA | 팀 하나·도메인 단순. 모듈러 모놀리스로 충분할 수 있다 (Microservice Premium) |
| 서비스 사이 동기 호출 체인이 장애를 전파한다 | EDA | 호출이 적고 즉시 응답이 꼭 필요한 흐름 |
| "저장은 됐는데 이벤트가 안 나갔다" 사고 | Outbox + CDC (또는 outbox 폴링) | 이벤트 유실이 허용되는 알림성 메시지 |
| 조회 화면 때문에 쓰기 테이블 인덱스·조인이 망가진다 | CQRS | CRUD로 충분한 도메인 (Fowler: 대부분의 시스템) |

넷 다 **"최종 일관성"이라는 같은 청구서**를 낸다. 쓰고 나서 바로 읽은 값이 아직 이전 값일 수 있다. 이 청구서를 감당할 이유가 없다면, 넷 중 어느 것도 도입할 이유가 없다.

> 근거 한계: 위 판단 기준은 각 출처의 정성적 권고를 정리한 것이다. "MSA·CQRS 도입 시 X% 개선" 같은 중립적인 정량 비교 연구는 이번 조사에서 찾지 못했고, 그래서 수치를 쓰지 않았다.

---

## References

1. James Lewis, Martin Fowler, "Microservices — a definition of this new architectural term", 2014-03-25. <https://martinfowler.com/articles/microservices.html>
2. Martin Fowler, "Microservice Premium", 2015-05-13. <https://martinfowler.com/bliki/MicroservicePremium.html>
3. Martin Fowler, "What do you mean by 'Event-Driven'?", 2017-02-07. <https://martinfowler.com/articles/201701-event-driven.html>
4. Martin Fowler, "CQRS", 2011-07-14. <https://martinfowler.com/bliki/CQRS.html>
5. Martin Fowler, "Event Sourcing", 2005-12-12. <https://martinfowler.com/eaaDev/EventSourcing.html>
6. Microsoft, "CQRS pattern", Azure Architecture Center. <https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs>
7. Debezium, "Debezium Features" (로그 기반 CDC). <https://debezium.io/documentation/reference/stable/features.html>
8. Debezium, "Outbox Event Router". <https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html>
9. Chris Richardson, "Pattern: Transactional outbox", microservices.io. <https://microservices.io/patterns/data/transactional-outbox.html>
