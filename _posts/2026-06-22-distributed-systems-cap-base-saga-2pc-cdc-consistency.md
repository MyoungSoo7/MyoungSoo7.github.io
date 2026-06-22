---
layout: post
title: "*분산 시스템 의 *본질* — *CAP*, *BASE*, *Saga*, *2PC vs CDC*, *일관성 spectrum*"
date: 2026-06-22 18:50:00 +0900
categories: [distributed-systems, fundamentals, architecture, backend]
tags: [distributed-systems, cap-theorem, base, saga, two-phase-commit, cdc, outbox, consistency, eventual, raft, paxos, fundamentals]
---

> *"단일 DB 가 *터졌다"* — *전통 적 시스템* 의 *최대 fear*. 해결책 은 *2 가지 뿐* : *vertical scale (한 대를 더 크게)* 또는 *horizontal scale (여러 대 로 나눔)*. *전자 는 *물리적 상한*. *후자 는 *복잡성 의 지옥*.
>
> 그 *복잡성 의 지옥* 의 *어휘* 가 *분산 시스템*. *CAP 정리*, *BASE 의 결정*, *Saga 의 보상*, *2PC 의 차단*, *CDC 의 우회*, *Raft / Paxos 의 합의*. *이 어휘 를 *알아야* *마이크로서비스 의 *경계 결정*, *eventual consistency 의 *trade-off*, *outbox 패턴 의 *왜* 가 *근거 있는 선택* 이 된다.
>
> 이 글은 *기본기 시리즈 의 *분산 편* — *CAP 의 진짜 의미*, *3 가지 trade-off 의 결정 매트릭스*, *7 가지 일관성 모델*, *분산 트랜잭션 의 *4 가지 패턴 (2PC / Saga / Outbox / Sourcing)*, *합의 알고리즘 (Raft, Paxos)* — 을 *시스템 설계자 의 *깊이* 로 정리한다.

내 *기본기 시리즈* :
- [*JVM 본질*](/2026/06/22/jvm-internals-jit-gc-memory-model-escape-analysis.html)
- [*DB 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
- [*오브젝트 서평*](/2026/06/22/object-book-review-cho-younghoo-object-oriented-design.html)

---

## TL;DR — *한 줄 결론*

> 분산 시스템 의 *본질* 은 *7 가지* : (1) **CAP** — *Partition 발생 시 *C 와 A 중 택일*, (2) **BASE** — *strict ACID 대신 *eventual consistency* 의 *throughput 교환*, (3) **일관성 spectrum** — Linearizability → Sequential → Causal → Eventual 의 *7 단계*, (4) **2PC** — *atomicity 의 *blocking 동기 합의*, (5) **Saga** — *long-lived transaction 의 *보상 (compensating)*, (6) **Outbox + CDC** — *dual-write 의 *우회*, *settlement 의 핵심 패턴*, (7) **Raft / Paxos** — *leader-based 합의 의 *현대 표준* (etcd, ZooKeeper, Kafka KRaft). *MSA 의 *모든 결정 의 *근거* 가 *이 7 가지 trade-off* 의 *명시 적 선택*. *깊이 는 *어떤 패턴 을 *왜 선택* 했는지 *설명 할 수 있는 능력* 이 만든다.

---

## 1. *왜 *분산 시스템 인가*

### 1.1 *단일 머신 의 *3 가지 벽*

| 벽 | 한계 |
|---|---|
| **CPU** | 60 코어 (Threadripper 9995WX) 정도 가 *현실적 상한* |
| **메모리** | TB 단위 가능 하지만 *DDR5 8 채널* 정도. *cache locality* 의 *latency 증가* |
| **단일 실패점** | 노드 죽으면 *서비스 0* — *HA 불가능* |

→ *어느 단일 머신* 도 *수억 사용자 의 *throughput + availability* 둘 다 *동시에 보장 못 함*.

### 1.2 *분산 의 *3 가지 어려움*

분산 시스템 = *여러 machine 이 *network 로 통신*. *그 network 가 *불완전*:
1. **Partial failure** — *일부 노드 만 죽음*. *살아있는 노드 가 *그 사실 을 *늦게 알아냄*.
2. **Network partition** — *네트워크 분리 가 *일시적 발생*.
3. **Clock skew** — *각 노드 의 *시계 가 *조금씩 다름*. *NTP 도 ms 단위 오차*.

→ *이 3 가지 가 *분산 의 *모든 복잡성 의 *원천*.

---

## 2. *CAP 정리*

### 2.1 *Eric Brewer 의 *2000 년 conjecture, 2002 년 증명***

> *Consistency, Availability, Partition tolerance — 3 가지 중 *최대 2 가지 만* 동시 보장 가능*.

| | |
|---|---|
| **C** (Consistency) | 모든 노드 가 *동일한 데이터* 본다 (= Linearizability) |
| **A** (Availability) | 살아있는 모든 노드 가 *응답 한다* |
| **P** (Partition tolerance) | 네트워크 partition 시에도 *시스템 계속 작동* |

### 2.2 *진짜 의미 — *"P 발생 시 C vs A"***

P 는 *선택 의 문제 가 아니다*. *현실 의 *네트워크 는 *언젠가 partition 됨*. 그러므로 *분산 시스템 은 *P 를 항상 가짐*. *진짜 선택 은 *partition 발생 시*:

- **CP** (Consistency 선택) — partition 시 *일부 노드 응답 거부* (예: etcd, ZooKeeper, MongoDB primary-only)
- **AP** (Availability 선택) — partition 시 *모든 노드 응답 (옛 데이터 가능)* (예: Cassandra, DynamoDB)

### 2.3 *CAP 의 *오해 와 진실***

**오해 1** : *"우리 시스템 은 CA 다 (CP 도 AP 도 아님)"*
→ **틀림**. *P 는 *선택 안 함*. *partition 일어나면 *어떻게 든 행동* 해야 함. *CA 는 *non-distributed* 단일 머신 만.

**오해 2** : *"CP 는 항상 C 다"*
→ *틀림*. *partition 없을 때 의 *Consistency 는 *isolation level 같은 *별도 개념*. CAP 의 C 는 *partition 시 만* 중요.

**오해 3** : *"Cassandra 는 AP 라 C 가 없음"*
→ *틀림*. *Cassandra 도 *tunable consistency* — `LOCAL_QUORUM` / `ALL` 같은 *write/read level* 로 *partition 없을 때 C 보장 가능*.

### 2.4 *PACELC — *CAP 의 확장 (2010)***

> *Daniel Abadi* 의 *2010 년 확장* : *if Partition then A vs C, **Else** then **L**atency vs **C**onsistency*.

```
PACELC:
  P (Partition 있을 때) → A or C
  E (Else / partition 없을 때) → L (Latency) or C (Consistency)
```

→ *partition 없는 *평상시* 에도 *strong consistency 는 *latency 대가* 가 있음. *quorum read = network round-trip 추가*.

| 시스템 | PACELC |
|---|---|
| MySQL primary-replica | **P**A / **E**L (replica 가 lag) |
| PostgreSQL synchronous replication | **P**C / **E**C (둘 다 strong) |
| Cassandra (QUORUM) | **P**A / **E**L (lower latency 선택 가능) |
| DynamoDB | **P**A / **E**L |
| etcd | **P**C / **E**C |
| Spanner | **P**C / **E**C (geographic — TrueTime) |

---

## 3. *BASE — *ACID 의 *반대편***

### 3.1 *ACID vs BASE*

| | ACID (전통 RDBMS) | BASE (분산) |
|---|---|---|
| **A** | *Atomic* — all or nothing | *Basically Available* — 항상 응답 |
| **C** | *Consistent* — invariant 보존 | *Soft state* — 시간 지남 에 따라 상태 변할 수 있음 |
| **I** | *Isolated* — 동시 tx 영향 0 | |
| **D** | *Durable* — commit 후 영속 | *Eventually consistent* — 결국 일관 |

> *BASE 는 *strict ACID 를 *throughput / availability 와 교환*. *대부분 의 e-commerce, social media, IoT* 가 *BASE 채택*.

### 3.2 *언제 ACID, 언제 BASE*

**ACID 가 필수**:
- 금융 (잔액 / 결제 / 정산)
- 재고 (oversell 절대 불가)
- 의료 / 법률 기록

**BASE 가 합리적**:
- *사용자 프로필 / 게시물 / 좋아요* — *수 초 지연 허용*
- *시계열 메트릭* — *최근 데이터 우선*
- *추천 / 검색 인덱스* — *eventual 충분*

→ *settlement (정산)* 은 *ACID 필수*. *sns / sparta 검색* 은 *BASE OK*.

---

## 4. *일관성 Spectrum — *7 단계***

### 4.1 *강한 순서*

```
가장 강함 ↓                                                      가장 약함 ↓
[Linearizable] > [Sequential] > [Causal] > [Read-your-writes] > [Monotonic] > [Bounded staleness] > [Eventual]
```

### 4.2 *각 단계 의 *정의 와 *예***

**Linearizable** (= Strict / Atomic Consistency) :
- *외부 관찰자 가 *모든 operation 의 *전체 순서 합의*. 각 operation 이 *원자 적 으로 *그 사이 어딘가 의 순간* 에 발생.
- *단일 머신 의 atomicity 와 동등*.
- 예: etcd, ZooKeeper, Spanner.

**Sequential** :
- *모든 노드 가 *같은 순서로 operation 봄*. 하지만 *그 순서 가 *실제 시간 과 다를 수 있음*.
- *Lamport 1979*.

**Causal** :
- *인과 관계 가 있는 operation 만 *순서 보장*. *동시 적 operation 은 *각 노드 에서 *다른 순서 가능*.
- *vector clock 사용*.

**Read-your-writes** :
- *내가 쓴 데이터 는 *내가 다음 read 에서 *반드시 봄*. *다른 사용자 는 늦게 봄 가능*.
- session affinity 로 구현.

**Monotonic reads** :
- *내가 한 번 본 데이터 의 *옛 버전 을 *다시 보지 않음*.

**Bounded staleness** :
- *최대 X 초 (또는 X 회 write) 만큼 옛 데이터 가능*. *그 이상 안 됨*.
- Azure Cosmos DB 의 *공식 모델*.

**Eventual** :
- *언젠가* 수렴. *언제* 는 *모름*.
- DNS, S3 (옛날 read-after-write 제외).

### 4.3 *trade-off — *Strong = Slow***

```
Linearizable:  매 write 마다 *quorum 합의* (예: Raft 의 majority). latency ↑↑
Eventual:      master 가 *즉시 응답*. *나머지 노드 는 *async 복제*. latency ↓↓
```

→ *latency 와 *consistency 의 *반비례*. *어느 지점 을 선택* 하는가 가 *시스템 설계 의 *핵심 결정*.

---

## 5. *분산 트랜잭션 — *4 가지 패턴***

### 5.1 *문제 설정*

```
주문 시스템:
  1. Order 서비스 — order 생성
  2. Inventory 서비스 — 재고 감소
  3. Payment 서비스 — 결제 호출

→ *3 가지 가 *모두 성공* 해야 *order 완료*. *하나만 실패* 하면 *나머지 도 *롤백* 해야*.

이게 *분산 트랜잭션* 의 고전 문제.
```

### 5.2 *패턴 1 — *2PC (Two-Phase Commit)***

```text
[Coordinator]                    [Service A]   [Service B]   [Service C]

Phase 1 (Prepare):
  PREPARE ─────────────────────→
                         ←───── VOTE_YES (또는 NO, abort 시작)
  PREPARE ─────────────────────────────────────→
                                       ←───── VOTE_YES
  PREPARE ──────────────────────────────────────────────────→
                                                     ←───── VOTE_YES

Phase 2 (Commit):
  COMMIT ───────────────────────→ COMMIT ──────→ COMMIT ───→
  ACK ←──────────────────────── ACK ←─────── ACK ←────────
```

**작동 시**: 모두 *원자 적 commit*.
**문제** : 
- *Coordinator 가 *Phase 2 사이 죽으면* — *참여자 가 *영원히 대기* (blocking).
- *latency 증가* — 모든 참여자 의 *왕복 2 회*.
- *availability 감소* — *한 참여자 가 응답 안 하면 *전체 차단*.

→ *XA Transaction* 의 표준. *현대 MSA 에선 *거의 사용 안 함*. Java 의 *JTA* 도 *legacy enterprise* 영역.

### 5.3 *패턴 2 — *Saga***

> *long-lived transaction* 을 *짧은 local transaction 의 sequence + 보상 (compensating) 트랜잭션* 으로 분해.

```text
[Forward path]
   Step 1: Order 생성       (T1)
   Step 2: 재고 감소        (T2)
   Step 3: 결제 호출        (T3)
   Step 4: Order 확정       (T4)

[실패 시 보상]
   Step 3 실패 → T2' (재고 복구) + T1' (Order 취소)
```

**2 종류**:
- **Orchestration Saga** — 중앙 *coordinator (Saga manager)* 가 *모든 단계 진행 / 보상 결정*.
- **Choreography Saga** — 각 서비스 가 *이벤트 발행/구독* 으로 *분산 협력*.

**장점**: *blocking 없음*, *각 단계 local 트랜잭션*.
**단점**: 
- *보상 의 *복잡성* (이미 발송 한 SMS 는 *어떻게 보상?*)
- *isolation 약함* — 다른 사용자 가 *중간 상태* 볼 수 있음
- *이중성 (idempotency) 의무* — 보상 트랜잭션 도 *중복 실행 안전* 해야

→ *settlement / sparta MSA* 의 *분산 처리 의 *기본 패턴*.

### 5.4 *패턴 3 — *Transactional Outbox***

> *single-write atomicity* — *DB 변경 + 메시지 발행* 을 *한 트랜잭션* 안 에.

```sql
BEGIN;
INSERT INTO orders (...) VALUES (...);        -- 비즈니스 변경
INSERT INTO outbox (event, payload, ...) VALUES ('OrderCreated', ...);  -- 발행할 이벤트
COMMIT;
```

별도 *Outbox Relay* 가 *주기 적* 으로 :
1. `SELECT * FROM outbox WHERE published = false`
2. *Kafka 등 으로 *발행*
3. *published = true* 표시

**왜** :
- *dual-write 문제 해결* — DB 트랜잭션 commit 했는데 Kafka publish 실패하면 *불일치*.
- *at-least-once delivery 보장*.
- *consumer 가 idempotent 면 *완전한 메시징*.

→ 내 [*Outbox 패턴 글*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) 참조. *settlement 의 *핵심 자산*.

### 5.5 *패턴 4 — *CDC (Change Data Capture)***

> *Outbox 의 변종* — *DB 의 WAL / binlog 자체* 를 *이벤트 스트림* 으로.

```text
[App] → [PostgreSQL]
              ↓ logical replication
        [Debezium]
              ↓
            [Kafka]
              ↓
        [downstream consumers]
```

**Debezium** 같은 *CDC 도구* 가 *DB 의 *모든 변경 (insert/update/delete) 을 *event* 로 변환.

**장점**:
- *애플리케이션 코드 변경 0* (outbox 테이블 없어도 됨)
- *기존 DB 그대로*
- *모든 변경 캡처* 보장

**단점**:
- *schema evolution 어려움* (Avro / Schema Registry 같은 인프라 필요)
- *DB 의 *replication slot* 자원 점유
- *복잡한 transformation 은 외부 stream processor (Kafka Streams, Flink) 필요*

→ *MySQL → Elasticsearch 동기화*, *legacy DB → Data Lake* 같은 *integration 의 표준*.

---

## 6. *합의 알고리즘 — *Raft, Paxos***

### 6.1 *왜 *합의 필요*

> *N 개 노드 가 *값 의 동일 sequence* 에 *합의* 하려면 *합의 알고리즘 필수*.

용도:
- *etcd* (Kubernetes 의 *brain*) — Raft
- *ZooKeeper* — ZAB (Paxos 변형)
- *Consul* — Raft
- *Kafka KRaft mode* — Raft

### 6.2 *Raft (2014) — *이해 가능 한 합의***

3 단계:
1. **Leader Election** — 시작 시 또는 leader 죽으면 *follower 들 이 *투표 로 선출*.
2. **Log Replication** — leader 가 *write 받으면 *follower 들에 *복제* — *majority 가 *받으면 *commit*.
3. **Safety** — 일관성 보장 (Election Restriction, Leader Append-Only, Log Matching).

```text
Leader (lemuel)
   write 받음 → log 에 append → followers (ilwon, solomon) 에 replicate
                                ↓ majority 응답 (2/3)
                            commit → client 에 OK
```

→ *N 개 노드 중 *(N/2) + 1* 이 *살아 있어야 *quorum*. *3 노드 면 *2 노드 살아도 OK*. *5 노드 면 *3 노드 살아도 OK*.

### 6.3 *Paxos — *원조***

*Leslie Lamport 1989* 의 *논문*. *이해 어렵기로 *악명*.

3 역할:
- **Proposer** — 값 제안
- **Acceptor** — 제안 수락
- **Learner** — 합의 결과 학습

2 단계:
- **Prepare phase** — proposer 가 *번호 N 으로 prepare*. acceptor 들 이 *N 보다 큰 번호 없으면 수락*.
- **Accept phase** — proposer 가 *N 과 값 v 보냄*. *majority 수락 시 *합의*.

→ *현장 적용* 은 *Multi-Paxos* 또는 *Raft* (단순 화). *Spanner 의 *TrueTime + Paxos*, *Google Chubby* 등.

### 6.4 *Byzantine Fault Tolerance — *악의 적 노드***

Raft / Paxos 의 *전제* : *노드 는 *crash 가능 하지만 *거짓말 안 함*.

*Byzantine* : *악의 적 / bug 로 *거짓말 하는 노드*. *blockchain (Bitcoin, Ethereum)* 이 *해결* 함 — *PoW, PoS*.

→ *기업 내부 시스템 에선 Byzantine 안 가정 (Raft 충분)*. *오픈 블록체인* 에선 *필수*.

---

## 7. *시간 의 문제 — *Lamport / Vector Clock***

### 7.1 *Physical Clock 의 *문제***

> *NTP 도 *수 ms 오차*. *다른 노드 의 *timestamp 비교 불가*.

GPS / TrueTime (Google Spanner) — *수 ms 의 *bounded error*. *전세계 분산 db 가 *linearizable* 가능.

### 7.2 *Lamport Clock — *논리 시계***

```
event 발생 시 counter++
다른 노드 의 message 받을 때: counter = max(local, received) + 1
```

→ *모든 event 에 *고유 순서 부여*. *동시 발생 도 *정렬*. *causal order 보장*.

### 7.3 *Vector Clock — *각 노드 의 counter*

```
A 의 vector: [Va=3, Vb=2, Vc=1]
B 의 vector: [Va=2, Vb=4, Vc=1]
```

→ *A 의 event 1 < B 의 event 1?* — *vector 비교 로 *판단*. *부분 순서 (partial order)*. *동시 발생 (concurrent) 감지 가능*.

→ *Cassandra, DynamoDB* 의 *conflict resolution 기반*.

---

## 8. *Distributed Patterns — *실전***

### 8.1 *Idempotency*

> *at-least-once delivery + idempotent consumer = exactly-once 효과*.

```java
// 안티
@KafkaListener(topics = "orders")
void handle(OrderCreated event) {
    repo.save(event.order());  // 같은 event 중복 시 *중복 저장*
}

// 좋음
@KafkaListener(topics = "orders")
void handle(OrderCreated event) {
    if (processedRepo.existsByEventId(event.id)) return;  // *중복 차단*
    transactionTemplate.execute(s -> {
        repo.save(event.order());
        processedRepo.markProcessed(event.id);
        return null;
    });
}
```

→ *settlement 의 *Triple Idempotency* — *outbox event_id UNIQUE → processed_events PK → DB UNIQUE 제약*.

### 8.2 *Circuit Breaker*

> *상대 가 죽었으면 *시도 중단* + *주기 적 retry*.

Resilience4j 의 *3 상태 전이*:
- **CLOSED** — 정상. 요청 통과.
- **OPEN** — 실패율 임계치 초과. *모든 요청 즉시 reject*.
- **HALF_OPEN** — 시간 지난 후 *몇 개 요청 *시도*. 성공 시 CLOSED, 실패 시 OPEN.

→ 내 [*I/O 병목 글*](/2026/06/18/io-bottleneck-how-to-solve.html) 참조.

### 8.3 *Bulkhead — *자원 격리***

> *Titanic 의 *방수 칸막이* 가 *유래*.

```yaml
resilience4j.bulkhead:
  instances:
    paymentClient:
      maxConcurrentCalls: 10   # 다른 client 가 *thread pool 100 다 써도 *payment 는 *10 까지 보장*
```

### 8.4 *Backpressure*

> *느린 consumer 가 *fast producer 를 *멈추게 함*. *Reactive Streams* 의 *핵심*.

```java
Flux.create(sink -> {
    sink.onRequest(n -> {
        for (int i = 0; i < n; i++) {
            sink.next(produce());  // *consumer 요청 만큼만*
        }
    });
}, FluxSink.OverflowStrategy.BUFFER);
```

### 8.5 *Quorum Read/Write*

```text
N = 3 (3 replicas)
W = 2 (write 시 *2 노드 에 *commit 확인*)
R = 2 (read 시 *2 노드 에 *동시 read 후 *최신 반환*)

→ W + R > N (2+2 > 3) 면 *strong consistency 보장*
```

→ Cassandra, DynamoDB 의 *tunable consistency 의 *기반*.

---

## 9. *실전 의사결정 — *5 가지 질문***

새 분산 시스템 설계 시 *반드시 답해야 할 질문* :

### 9.1 *Q1 — *Partition 시 *어떻게 행동?*

- **CP** — 응답 거부 (etcd, MongoDB, ZooKeeper)
- **AP** — 옛 데이터 응답 (Cassandra, DynamoDB)

### 9.2 *Q2 — *Eventual consistency 수용 가능?*

- *읽기 가 *수 ms ~ 수 분 lag 가능* 한가?
- *user-facing 데이터 면 *read-your-writes 필수*

### 9.3 *Q3 — *Idempotency 보장?*

- *consumer 가 *중복 메시지 받아도 안전*?
- *event_id 기반 dedup* 필수 (Triple Idempotency)

### 9.4 *Q4 — *분산 트랜잭션 패턴?*

- 2PC — *legacy, 거의 안 씀*
- Saga — *long-running, 보상 가능*
- Outbox — *single DB + Kafka, settlement 의 표준*
- CDC — *DB binlog 자체 가 source*

### 9.5 *Q5 — *HA 와 quorum?*

- *최소 3 노드* (1 fail 가능)
- *5 노드 권장* (2 fail 가능)
- *etcd 처럼 *write-heavy* 는 *3 또는 5 이하* (합의 비용)

---

## 10. *결론 — *trade-off 의 *명시화***

> 분산 시스템 의 *모든 결정 의 *밑* 에 *trade-off* 가 있다. *strong consistency vs latency*, *availability vs durability*, *exactly-once vs simplicity*, *flexibility vs throughput*.

오늘 정리한 *7 본질* :
1. **CAP** — *partition 시 *C vs A*
2. **BASE** — *ACID 의 *throughput 교환*
3. **일관성 spectrum** — Linearizable → Eventual 의 7 단계
4. **2PC vs Saga vs Outbox vs CDC** — *분산 트랜잭션 의 *4 패턴*
5. **Raft / Paxos** — *합의 의 *현대 표준*
6. **Lamport / Vector Clock** — *시간 의 *논리적 모델*
7. **실전 패턴** — Idempotency / Circuit Breaker / Bulkhead / Backpressure / Quorum

> *MSA 의 *모든 결정* 이 *근거 있게 *설명 가능* 해지려면 — *이 7 가지 의 *각 trade-off 의 *명시 적 선택 의 *어휘* 가 *필요*.

*settlement / sparta MSA 의 *Outbox + Triple Idempotency + Saga* 의 *조합* 이 *그 어휘 위에서 *근거 있게 *서 있다*. *그 근거 없이 *MSA 라 다 분산* 으로 부른 *시스템* 은 *eventually consistent 의 *의미 도 모른 채 *production 의 *eventual 오류* 를 *겪는다*.

*분산 의 *본질* 은 *"같이 가는 게 *불가능* 한 *두 좋은 것 의 *선택 의 명시화"*. *그 명시화 가 *시니어 의 *시스템 설계 의 *진짜 일*.

---

## *참고*

- *Designing Data-Intensive Applications* (Martin Kleppmann) — *분산 의 *최고 의 reference*.
- *Distributed Systems for Practitioners* (Dimos Raptis).
- *In Search of an Understandable Consensus Algorithm (Raft)* (Diego Ongaro, John Ousterhout, 2014).
- *Paxos Made Simple* (Lamport, 2001).
- *Time, Clocks, and the Ordering of Events in a Distributed System* (Lamport, 1978).
- *CAP Twelve Years Later* (Brewer, 2012).
- 자매편:
  - [*Outbox 패턴*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)
  - [*Kafka 운영 (settlement)*](/2026/06/17/kafka-in-production-settlement.html)
  - [*I/O 병목*](/2026/06/18/io-bottleneck-how-to-solve.html)
