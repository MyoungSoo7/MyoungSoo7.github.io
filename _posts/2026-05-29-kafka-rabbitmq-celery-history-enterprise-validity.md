---
layout: post
title: "Kafka, RabbitMQ, Celery — *메시지가 가는 길* 의 세 가지 철학: 탄생, 기업 사용사례, 그리고 2026 년의 유효성"
date: 2026-05-29 00:50:00 +0900
categories: [messaging, distributed-systems, history]
tags: [kafka, rabbitmq, celery, amqp, event-driven, message-queue, linkedin, instagram, ericsson, distributed]
---

> *''메시지를 어떻게 전달할 것인가''* — 이 단순한 질문에 *세 가지 완전히 다른 답* 이 나왔다. **RabbitMQ** 는 *''똑똑한 우체국''*, **Kafka** 는 *''끝없이 쓰여지는 책''*, **Celery** 는 *''Python 의 분산 작업 위임자''*. 표면적으로 비슷해 보이지만, *근본 모델* 은 *서로 다른 우주에 있다*. 그리고 이 차이가 *''어느 회사가 어느 걸 쓰는가''* 의 *진짜 이유* 다.

이 글은 세 도구의 *탄생 배경, 핵심 모델, 기업 사용사례, 그리고 2026 년 현재의 유효성* 을 정리한다. *''Kafka 가 다 이긴 것 같다''* 는 인터넷 의견이 있는데, *반은 맞고 반은 틀리다*. 이유는 *''메시지의 의미가 무엇인가''* 가 회사마다 다르기 때문이다.

---

## 1. *''메시지''* 라는 단어의 세 가지 의미

세 도구를 비교하기 전에 *''메시지가 뭔지''* 부터 정렬해야 한다. 표면적으로는 *''A 가 보내고 B 가 받는 데이터''* 지만, *내부적으로는 셋이 다르다*:

| 도구 | *메시지란* | 메시지의 수명 | 누가 *''다 읽었는지''* 기억하나 |
|---|---|---|---|
| **RabbitMQ** | *''작업 지시서''* | *consumer 가 ack 하면 삭제* | 브로커 |
| **Kafka** | *''불변 로그 한 줄''* | *retention 기간만큼 보관 (보통 7일)* | 컨슈머 (offset 직접 관리) |
| **Celery** | *''함수 호출''* | *worker 가 실행하면 삭제* | 브로커 (RabbitMQ/Redis) + result backend |

이 *3 줄 표* 가 사실상 *''왜 셋이 다른 회사에서 다른 용도로 쓰이는가''* 의 답을 다 담고 있다. *''불변 로그''* 라는 단어 하나가 Kafka 와 RabbitMQ 를 *완전히 다른 도구* 로 만든다.

## 2. *RabbitMQ* — *Ericsson 통신 OS 의 후예* (1986 → 2007)

RabbitMQ 의 뿌리는 *놀랍게도 1986 년 Ericsson* 으로 거슬러 올라간다. Ericsson 은 *''통신 교환기 (telecom switch)''* 라는 *''절대 다운되면 안 되는''* 시스템을 만들고 있었고, 그를 위해 **Erlang** 이라는 언어를 개발한다. *''경량 프로세스 수십만 개를 동시에 돌리고, 하나가 죽어도 나머진 멀쩡하다''* 는 Erlang 의 철학은 *분산 메시징의 정확한 요구사항* 이었다.

2006 년 *AMQP (Advanced Message Queuing Protocol)* 표준이 발표된다. *JP Morgan 등 금융사가 *''벤더 종속 없이 메시지 큐를 쓰고 싶다''* 며 만든 오픈 표준*. 그리고 2007 년 *Rabbit Technologies* 가 *Erlang 으로 AMQP 를 구현한* **RabbitMQ** 를 공개한다.

### 2.1. RabbitMQ 의 *철학*: *Smart Broker, Dumb Consumer*

RabbitMQ 의 핵심은 *''브로커가 모든 라우팅 책임을 진다''* 이다:

- **Exchange** — 메시지가 *어디로 갈지* 를 결정. *direct, topic, fanout, headers* 네 가지 라우팅 모드
- **Queue** — 실제 메시지가 *대기* 하는 곳
- **Binding** — exchange 와 queue 를 잇는 *라우팅 규칙*

이 모델의 *강점* 은 *복잡한 라우팅을 broker 한 곳에서* 표현할 수 있다는 것. *''결제 성공 메시지를 *재고팀, 회계팀, 분석팀* 셋에게 동시에 라우팅하라''* — RabbitMQ 의 *fanout exchange* 한 줄로 끝난다.

### 2.2. RabbitMQ 가 *처음 흥한 이유*

- *AMQP 표준 준수* — *''벤더 종속이 무서운 금융권''* 이 안심하고 도입
- *Erlang 의 견고함* — 노드 죽어도 클러스터가 멀쩡
- *우체국 모델의 직관성* — *''queue 가 있고, 거기 메시지 넣으면 누가 가져간다''* 가 *모두에게 직관적*

### 2.3. 기업 사용사례

- **NASA** — Nebula cloud platform 메시징 백본
- **Reddit** — vote 처리, 알림 시스템
- **Mozilla** — Firefox Sync, crash report
- **Trivago, Bloomberg, AT&T** — 대규모 동기적 워크로드
- *한국* — **카카오** 일부 알림 시스템, **네이버** 일부 백오피스, 금융권 다수 (코어 시스템 메시징)

## 3. *Kafka* — *LinkedIn 의 로그 폭발이 만든 발명* (2010)

2010 년 **LinkedIn** 은 *''매일 *수십 억 건의* 이벤트 로그를 어떻게 처리할까''* 라는 문제에 빠져 있었다. *클릭, 검색, 친구 추가, 메시지* — 모든 사용자 행동이 *분석을 위해 어딘가에 저장* 되어야 했다.

당시 *''메시지 큐''* 라는 도구들 (RabbitMQ, ActiveMQ) 은 *이 규모를 못 받았다*. 이유는 단순했다 — *''메시지를 받으면 삭제하는 모델''* 이라 *재생, 다중 컨슈머, 장기 보관* 이 *불가능*. **Jay Kreps, Neha Narkhede, Jun Rao** 가 *''메시지 큐를 *데이터베이스* 처럼 다루면 어떨까''* 라는 *역발상* 으로 **Kafka** 를 만든다. 이름의 유래는 *Franz Kafka 의 글이 *''너무 많다''* 는 농담*.

### 3.1. Kafka 의 *철학*: *Dumb Broker, Smart Consumer*

Kafka 의 *근본 모델* 은 RabbitMQ 와 *정반대* 다:

- **Topic** = *''append-only log''*. *메시지를 쓰면 영원히 남는다 (retention 동안)*
- **Partition** = topic 을 *N 개 조각으로 쪼갠 것*. *병렬성의 단위*
- **Offset** = 컨슈머가 *''어디까지 읽었나''* 를 *스스로 기억*
- **Broker** = *그냥 로그를 디스크에 쓰고, 컨슈머가 요청하면 읽어준다*. *라우팅 결정 없음*

이 모델의 *천재성* 은:

1. *재생 가능* — 컨슈머가 *''3 시간 전 메시지부터 다시 읽고 싶다''* 면 *offset 만 되돌리면 됨*
2. *다중 컨슈머* — 같은 topic 을 *분석팀, 모니터링팀, ML팀* 이 *각자의 속도로* 읽음. 서로 영향 없음
3. *압도적 처리량* — 디스크에 *순차 쓰기* 만 함. SSD 의 *최대 대역폭* 을 뽑아냄
4. *순서 보장 (per partition)* — *event sourcing* 에 천연 적합

### 3.2. Kafka 가 *세상을 바꾼 이유*

Kafka 가 단순히 *큰 메시지 큐* 였다면 *그 정도로 흥하지 않았을 것* 이다. 진짜 영향은 *''log-centric architecture''* 라는 *새로운 시스템 디자인 패러다임* 을 만든 것이다.

Jay Kreps 의 *''The Log: What every software engineer should know about real-time data's unifying abstraction''* (2013) 은 *''분산 시스템의 진실은 *불변 로그* 다''* 라는 *철학적 선언* 이었다. *데이터베이스 replication, event sourcing, CQRS, stream processing* 모두 *''로그''* 라는 한 추상으로 통합된다는 *깨달음*.

그리고 *Kafka Streams, ksqlDB, Kafka Connect* 가 등장하면서 *''Kafka 가 그 자체로 데이터 인프라''* 가 된다. 2014 년 LinkedIn 의 *Kreps, Narkhede, Rao 가 *Confluent* 를 창업*. 2024 년 시가총액 *$10B+*.

### 3.3. 기업 사용사례

- **LinkedIn** — 창업 모태, *수조 메시지/일*
- **Netflix** — 모든 마이크로서비스 간 이벤트 백본
- **Uber** — 실시간 위치, 배차, 가격 계산
- **Airbnb, Spotify, Yelp** — 이벤트 소싱 표준
- **Goldman Sachs, JPMorgan** — 트레이딩 시스템 이벤트 버스
- *한국* — **쿠팡** (주문/배송 이벤트), **토스** (금융 트랜잭션), **카카오 페이** (결제 이벤트), **배달의민족** (주문 흐름), **당근마켓** (실시간 활동)

## 4. *Celery* — *Python 의 작업 위임자* (2009)

Celery 는 *''메시지 큐''* 라기보다 *''Python 의 분산 작업 시스템''* 이다. **Ask Solem** 이 2009 년 *Last.fm* 에서 일하다가 *''Django 에서 *''메일 전송, 이미지 리사이즈, 보고서 생성''* 같은 *느린 작업* 을 *비동기* 로 떼어내고 싶다''* 는 문제에서 출발했다.

### 4.1. Celery 의 *위치*

Celery 는 *자체 브로커가 없다*. *RabbitMQ 또는 Redis* 를 *브로커로* 쓰고, 그 위에 *''Python 함수를 분산 실행하는 레이어''* 를 얹는다:

```python
@app.task
def send_email(to, subject, body):
    # ... 시간 오래 걸리는 작업
    pass

# 호출 측
send_email.delay("user@x.com", "Hi", "Body")  # 큐로 던짐
```

*''함수를 그냥 부르면 비동기 작업이 된다''* 는 *DX* 가 Celery 의 *진짜 매력* 이다. RabbitMQ/Kafka 처럼 *''메시지 포맷을 직접 정의''* 할 필요 없음.

### 4.2. Celery 가 *Python 진영을 지배한 이유*

- *Django 의 표준 비동기 작업 도구* 가 *''사실상 Celery''* 가 됨
- *주기적 작업 (celery beat)* 까지 한 도구로 통합
- *Result backend* — 작업 결과를 *돌려받을 수 있음*. *''비동기지만 결과는 필요''* 한 케이스에 fit
- *Chain, Group, Chord* — *복잡한 워크플로* 를 *Python 함수 조합* 으로 표현

### 4.3. 기업 사용사례

- **Instagram** — 초기 Django + Celery 로 *수억 사용자* 까지 성장한 전설적 사례. *''Instagram is built on Django and Celery''* 가 2013~2017 년 PyCon 단골 발표
- **Mozilla** — Firefox Add-ons 사이트 백엔드
- **Udemy** — 강의 인코딩, 결제 후처리
- **Doordash, Stripe** — Python 백엔드의 비동기 작업
- *한국* — **무신사** (Python 기반 배치), **쏘카** (정산 작업), 다수 스타트업 표준

## 5. *셋의 충돌* — *왜 한 회사가 셋 다 쓸 수도 있는가*

흥미로운 점은 *대형 시스템에선 셋이 *공존* 한다* 는 것이다. 같은 회사가:

- **Kafka 로** 이벤트 소싱과 분석 파이프라인을 돌리고
- **RabbitMQ 로** 동기적 RPC 와 *낮은 지연 라우팅* 을 하고
- **Celery 로** *''매일 새벽 3 시 보고서 생성''* 같은 *Python 배치* 를 돌린다

*''왜 통합 안 하나''* 라는 질문은 *''왜 우편, 전화, 메신저를 다 쓰나''* 와 같은 답이다. *각 도구가 잘하는 영역이 다르다*.

| 케이스 | 추천 도구 | 왜 |
|---|---|---|
| 주문 → 결제 → 배송 *이벤트 체인* | **Kafka** | event sourcing, 재생, 순서 보장 |
| 5 개 마이크로서비스 *동기 RPC* | **RabbitMQ** | low latency, *''작업 지시서 모델''* |
| 결제 성공 → *이메일/SMS/푸시* fan-out | **RabbitMQ** (fanout) | smart routing |
| *''매일 새벽 정산 배치''* (Python) | **Celery + Redis** | 결과 추적, beat 스케줄 |
| *수십 억 이벤트/일 로그 수집* | **Kafka** | 처리량, 장기 보관 |
| *''사용자 액션 → 5 단계 워크플로''* | **Temporal / Celery chain** | workflow orchestration |
| *''사용자 알림 한 번 전송''* (fire-and-forget) | **RabbitMQ** | 가벼움, 빠른 ack |

## 6. *2026 년 현재의 유효성* — *누가 이기고 있는가*

### 6.1. *Kafka 의 압승* — *그러나 *완전한* 압승은 아님*

2018~2024 년 동안 *''마이크로서비스 이벤트 백본''* 시장은 *Kafka 가 거의 독점*. 이유:

- *event sourcing, CQRS 패턴이 *주류* 가 됨*. RabbitMQ 의 *''메시지 삭제 모델''* 로는 못 함
- *Kafka Connect* 로 *DB → S3 → Elasticsearch* 같은 데이터 이동도 표준화
- *Confluent Cloud 등 매니지드 옵션* 이 *운영 부담* 을 줄임

*그러나*:

- *Kafka 는 *복잡하다*. ZooKeeper (혹은 KRaft), 파티션 설계, retention 정책, consumer group rebalancing — *DevOps 부담 큼*
- *작은 팀, 작은 처리량* 에선 *over-engineering*
- *콜드 스타트, 디스크 비용, 운영 복잡도* — 큰 회사도 *Kafka 를 *''잘 운영하는 SRE 팀''* 이 따로 있어야* 함

### 6.2. *RabbitMQ 의 *위치 재정의*

RabbitMQ 는 *''Kafka 에 자리를 뺏긴 도구''* 처럼 보이지만, *2026 년 현재* 살아남았다:

- *낮은 지연 RPC* 시장은 *여전히 RabbitMQ*. *gRPC 보다 RabbitMQ RPC* 가 깔끔한 경우 많음
- *간단함 = 작은 팀의 무기*. *''100 메시지/초 처리에 Kafka 는 미친 짓''*
- *AMQP 표준* — *공공·금융 안정성*. *''표준 준수''* 가 도입 결정 요인인 곳에선 여전히 강세
- *2023 RabbitMQ Streams* 출시 — *Kafka 닮은 기능* 도 흡수 중

### 6.3. *Celery 의 *틈새 압도*

Python 진영에서 Celery 는 *2026 년에도 표준* 이다. *FastAPI + Celery* 도 흔한 조합. 그러나 *경쟁자* 도 등장:

- **Dramatiq** — *''Celery 의 복잡함을 줄이자''*. *''task queue 가 *작은 것* 이어야 한다''* 는 철학
- **RQ (Redis Queue)** — *극단적 단순함*. *Redis 만 있으면 됨*
- **Temporal / Prefect / Airflow** — *''workflow''* 까지 다루는 도구들. *Celery 의 chain/group 영역을 잠식*
- **arq, taskiq** — *async/await 네이티브* 신세대

2026 년 시점에서 *Celery 의 점유율은 점점 줄고* 있지만, *''쓰던 사람이 쓰던 걸 계속 쓰는''* 관성이 압도적이라 *''교체''* 보단 *''신규 프로젝트는 다른 걸 쓴다''* 패턴.

## 7. *다음 세대의 도전자들*

세 도구 외에도 *''메시지 큐 시장''* 은 *조용히 진화* 중이다:

- **NATS / NATS JetStream** — *''Kafka 보다 가볍고 RabbitMQ 보다 빠르다''*. *CloudFlare, Synadia* 채택. *Edge / IoT* 에 강점
- **Apache Pulsar** — *''Kafka 의 차세대''*. *Yahoo 가 만들고 StreamNative 가 상용화*. *멀티 테넌시, 지리적 복제* 가 강점
- **Redpanda** — *''Kafka API 호환, C++ 재구현, ZooKeeper 없음''*. *''Kafka 의 운영 복잡도를 *없앤* 버전''*
- **Temporal** — *''workflow orchestration''* 의 새 표준. *''메시지 큐가 아니라 *상태 기계*''* 라는 시선. **Stripe, Snap, Datadog** 채택
- **Kafka 자체의 진화** — KRaft (ZooKeeper 제거), Tiered Storage, KIP-848 (consumer group 재설계) — *''운영 복잡도를 *스스로* 줄이려는 중''*

## 8. *''뭘 골라야 하나''* — 실전 결정 트리

```
처리량이 *초당 만 건 이상* 인가?
├─ 예 → Kafka (또는 Redpanda/Pulsar)
└─ 아니오:
   메시지 모델이 *''작업 지시서''* 인가 *''불변 로그''* 인가?
   ├─ 지시서 → RabbitMQ
   └─ 로그:
      *Python 단일 언어* 인가?
      ├─ 예 → Celery (간단) / Dramatiq (개선)
      └─ 아니오 → Kafka 작게 시작
```

다만 *''쓰는 사람의 *익숙함*''* 이 *기술 선택의 절반* 이라는 *현실* 도 잊으면 안 된다. 5 명짜리 팀이 *Kafka 의 베스트 프랙티스* 를 *밤마다 공부할* 시간이 있을까? *''Celery 가 30 분이면 돌아간다''* 는 *진짜 가치*.

## 9. 정리 — *셋은 같은 시장의 도구가 아니다*

처음에 했던 *''Kafka 가 다 이긴 것 같다''* 라는 가정으로 돌아가보자. *틀렸다*. 셋은 *같은 시장에 있지 않다*:

- **Kafka 는 *''데이터 인프라''*** — DB 와 분석 시스템의 *중간층*
- **RabbitMQ 는 *''서비스 간 통신''*** — *''동기 RPC 의 비동기 버전''*
- **Celery 는 *''작업 분산 실행기''*** — *''Python 의 비동기 함수''*

*같은 회사 안에서 셋 다 쓰는 게 이상한 게 아니라 *정상* 이다*. 도구의 *모델* 이 다르기 때문이다. *''메시지가 가는 길''* 이 다르다.

*''내 시스템에서 *메시지의 의미가 뭔지''*** 를 먼저 정의해야 한다. *''사용자 행동 로그''* 라면 Kafka, *''결제 후 알림 fan-out''* 이라면 RabbitMQ, *''Python 으로 배치 돌리고 결과 받기''* 라면 Celery. *답이 다른 *이유* 는 *질문이 다르기 때문*.

> *''The right tool for the right job''* 이라는 격언은 *''다른 도구들이 *왜 다른지* 를 안다''* 는 *전제* 위에서만 작동한다. 모르면 *''다 같아 보이고''*, *''유행''* 따라간다. 그게 *기술 부채의 가장 흔한 출처* 다.

---

## 더 읽을 거리

- Jay Kreps, *The Log: What every software engineer should know about real-time data's unifying abstraction* (LinkedIn Engineering, 2013) — Kafka 의 *철학적 선언*
- *AMQP 0-9-1 specification* — *https://www.rabbitmq.com/specification.html*
- *Designing Data-Intensive Applications* — Martin Kleppmann. *9 장 ''replication and the log''* 가 사실상 Kafka 의 *학술적 설명*
- *Celery Documentation: First Steps* — *https://docs.celeryq.dev/*
- *Streaming Systems* — Tyler Akidau (Google). *Kafka/Flink/Beam 의 *공통 추상* 이해*
- *Confluent Blog* — 운영 best practice 모음. *''Kafka 를 *제대로* 쓰는 법''*

*다음 글 예고: Outbox Pattern 과 Transactional Messaging — settlement 11 env 에서 Kafka 와 DB 트랜잭션 일관성을 잡은 경험*
