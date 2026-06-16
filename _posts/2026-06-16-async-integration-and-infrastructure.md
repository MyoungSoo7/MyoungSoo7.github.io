---
layout: post
title: "*비동기 연동과 인프라* — *어떤 인프라가* *어떤 비동기를* *가능하게 하나*"
date: 2026-06-16 02:00:00 +0900
categories: [backend, architecture, infrastructure, integration]
tags: [async, infrastructure, kafka, redis, k8s, broker, message-queue, cgroup, scheduler, observability]
---

> *비동기 연동* 의 *코드* 는 *교과서에 있다*. `kafkaTemplate.send()`, `@Scheduled`, `@Async`, `CompletableFuture.supplyAsync()`. 어느 자료든 *읽으면 된다*.
>
> *그러나 *그 코드 가 *실제로 돌게 하는 *인프라* 는 *교과서에 별로 안 나온다*. *Kafka broker 의 *replication factor*, *K8s scheduler 의 *pod-anti-affinity*, *cgroup 의 *cpu.weight*, *DB 의 *connection pool*, *Redis 의 *persistence 모드*.
>
> *비동기 연동 코드 가 *제대로 도는 건 *그 인프라 가 *비동기 의 *5 가지 보장* 을 *해주기 때문*.

이 글은 *비동기 연동 의 *5 가지 본질적 보장* — *지속성 / 순서 / 격리 / 백프레셔 / 관측* — 을 *어떤 인프라 가 *어떤 layer 에서 *책임지는지* 를 *본인 인프라 의 실제 사례* 와 함께 분해한다.

---

## TL;DR

> *비동기 연동 의 *5 가지 본질적 보장* (메시지 *지속성*, *순서*, *격리*, *백프레셔*, *관측가능성*) 은 *코드가 아니라 *인프라 가 *보장* 한다. *Kafka broker / K8s scheduler / cgroup / DB / Redis / Prometheus* 의 *각 컴포넌트 가 *어느 보장 을 *책임지는지* 를 알면 *비동기 시스템 의 *진짜 디자인* 이 *명확* 해진다.

---

## 1. *발단 — *비동기 연동 의 *5 가지 본질적 보장**

비동기 연동 시스템이 *실패 없이 돌려면* :

1. **지속성 (Durability)** — 메시지가 *broker / DB 가 죽어도 살아남는다*
2. **순서 (Ordering)** — 같은 *비즈니스 entity* 의 이벤트는 *발생 순서대로 처리*
3. **격리 (Isolation)** — *한 consumer 의 폭주가 다른 consumer 를 죽이지 않는다*
4. **백프레셔 (Backpressure)** — *처리 속도 < 생산 속도* 일 때 *조용히 폭주 안 함*
5. **관측가능성 (Observability)** — *어디서 막혔는지 수치로 보인다*

이 5 가지가 *코드에 의해 완전 보장 되지 않는다*. *인프라 의 각 컴포넌트가 나눠 책임진다*.

---

## 2. *Layer 1 — Broker (Kafka)*

### 2.1 *Kafka 가 책임지는 보장*

- **지속성** — *replication factor 3, min.insync.replicas 2*. 한 broker 죽어도 *committed 메시지 안 잃음*
- **순서** — *partition 내 순서 보장*. partition key 가 *비즈니스 entity ID* 면 *그 entity 의 모든 이벤트가 같은 partition*
- **백프레셔** — *consumer lag* 메트릭. 처리 속도 못 따라가면 *broker 에 쌓임*. producer 가 알 수 있다

### 2.2 *Replication factor 의 trade-off*

```yaml
default.replication.factor: 3
min.insync.replicas: 2
```

- *replication factor 3* — *broker 1 대 손실 가능*
- *min.insync.replicas 2* — *최소 2 대가 동기화 된 후 commit*
- 둘 사이 차이 (3 - 2 = 1) — *broker 1 대 정지 시에도 publish 계속 가능*

*min.insync.replicas = replication factor* 면 *한 대만 정지해도 publish 정지*. availability ↓.

### 2.3 *Partition 수 의 trade-off*

*Partition 수 = consumer 병렬도의 상한*.

- *너무 적으면* — consumer 가 *놀고 있는데* 처리 속도 *상한*
- *너무 많으면* — *broker 메모리 ↑*, *leader election 비용*

경험치 : *consumer 노드 수 × 2 ~ × 4*. 내 sparta-prod 의 Kafka topic 들은 *partition 12~24* 정도.

---

## 3. *Layer 2 — K8s scheduler 와 pod 배치*

### 3.1 *Pod-anti-affinity — 동일 노드 집중 방지*

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: kafka-broker
        topologyKey: kubernetes.io/hostname
```

Kafka broker 3 대가 *같은 노드에 몰리면* 그 노드 fail 시 *3 대 동시 정지*. anti-affinity 로 *서로 다른 노드에 분산*.

### 3.2 *Topology spread constraints*

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: tier
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: kafka-broker
```

*storage / worker tier* 별 *균등 분포*. 내 Lemuel K3s 클러스터의 *tier=storage / tier=worker* 분리 패턴 활용.

### 3.3 *PodDisruptionBudget — rolling restart 안전망*

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: kafka-broker
```

K8s 가 *노드 drain 할 때* *최소 2 대는 항상 살아있게*. *cluster 운영의 암묵적 보장*.

---

## 4. *Layer 3 — cgroup 과 리소스 격리*

### 4.1 *cgroup v2 의 cpu.weight*

```yaml
resources:
  requests:
    cpu: 500m       # → cgroup cpu.weight ≈ 500
  limits:
    cpu: 2          # → cgroup cpu.max = "200000 100000" (= 2 core)
```

같은 노드에 *Kafka broker + Spring Boot app + 다른 워크로드* 가 섞여 있어도 *cgroup 이 서로의 CPU 를 훔치지 못하게* 격리.

### 4.2 *cpu.max 의 throttling 함정*

비동기 consumer 가 spike 시 *cpu.max 다 쓰면* cgroup throttler 가 *그 process 의 CPU access 를 100ms 차단*. 처리 지연.

내 velero CPU throttling 99.54% 사고가 직접 사례. *Kafka consumer 도 같은 위험*.

### 4.3 *memory.max — OOM 격리*

Consumer 가 메모리 누수가 있어도 *그 pod 만 OOMKilled*. 다른 pod 에 영향 없음. cgroup memory.max 가 *그 격리 책임*.

---

## 5. *Layer 4 — DB 와 outbox / processed_events*

### 5.1 *DB 가 책임지는 보장*

- **지속성** — Write-ahead log (WAL) 로 *commit 후 전원 차단에도 살아남음*
- **순서** — Outbox 의 *id 컬럼이 publish 순서*. partition key 동기화
- **트랜잭션 격리 수준** — READ COMMITTED / REPEATABLE READ — *consumer 가 반쪽 데이터 못 봄*

### 5.2 *Outbox 의 partial index*

```sql
CREATE INDEX idx_outbox_pending ON outbox (id) WHERE status = 'PENDING';
```

[정산 정합성 글](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) 의 *outbox polling 비용 최소화*. PUBLISHED 99% 는 index 에 안 잡힘 → polling 거의 무료.

### 5.3 *Connection pool 의 공유 책임*

[HikariCP 글](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) 의 *5 가지 시간 설정* — outbox publish 와 consumer 의 비즈니스 logic 이 *같은 pool 쓰면* 서로 점유 경쟁. *Bulkhead 패턴* 으로 pool 분리 필요할 수 있음.

---

## 6. *Layer 5 — Redis 와 분산 락 / 캐시*

### 6.1 *Redis 가 책임지는 보장*

- **분산 락** — cluster 의 여러 노드가 *같은 잡 동시 실행 방지* (`SET NX EX`)
- **rate limit** — *token bucket / leaky bucket* 의 고속 카운터
- **transient state** — *이메일 발송 중복 방지, 최근 본 상품* 같은 *짧은 수명 상태*

### 6.2 *Redis persistence 모드 의 trade-off*

```yaml
save: ""              # RDB snapshot 비활성
appendonly: yes       # AOF 활성
appendfsync: everysec # 1초 단위 fsync
```

- *AOF + fsync everysec* — 최악 1 초의 *데이터 손실 가능*
- *AOF + fsync always* — 모든 write 동기. *throughput 30~50% 감소*
- *RDB only* — snapshot 사이의 *수십 초 손실 가능*

비동기 lock / counter 는 *분 단위 손실 허용 가능* — AOF everysec 이 *황금 절충*.

### 6.3 *Redis Streams — 경량 Kafka 대체*

소규모 시스템에선 *Redis Streams* 가 *Kafka 의 90% 기능* 을 *broker 운영 부담 없이* 제공.

- *consumer group 지원*
- *XACK / XPENDING* 으로 at-least-once 메시징
- *XADD MAXLEN* 으로 자동 trim

Kafka 가 *오버스펙 한 워크로드* 에 적합.

---

## 7. *Layer 6 — Prometheus + Grafana + Tempo 의 관측가능성*

### 7.1 *비동기 시스템 의 핵심 메트릭*

| 메트릭 | 의미 | 알람 임계 |
|---|---|---|
| `kafka_consumer_lag` | broker 의 쌓인 메시지 수 | *partition 별 1000+ 지속* |
| `outbox_pending_count` | DB outbox 의 PENDING 행 수 | *1000+ 지속 → publish worker 점검* |
| `outbox_dead_letter_count` | DLQ 진입 수 | *1+ → 즉시 알람* |
| `outbox_publish_duration_p99` | publish 의 p99 latency | *1s+ → Kafka 또는 DB 느림* |
| `container_cpu_throttled_seconds_total` | cgroup throttling | *50%+ → limit 부족* |
| `hikaricp_connections_pending` | DB pool 대기 | *증가 추세 → pool 부족 or DB 느림* |

자세한 응답시간 모니터링 관점은 [별편 글](/2026/06/10/backend-latency-and-monitoring-truth.html) 참고.

### 7.2 *Trace — 분산 이벤트의 전 여정*

```
[Order Service]
  └─ POST /orders → Spring Tx
     └─ outbox INSERT
        └─ COMMIT
[Outbox Worker]
  └─ poll PENDING (5ms)
     └─ Kafka publish (12ms)
[Settlement Consumer]
  └─ poll Kafka (consumer lag 0)
     └─ processed_events INSERT
        └─ settlement INSERT
        └─ COMMIT
```

OpenTelemetry 의 *trace propagation* 으로 비동기 hop 을 가로질러 *같은 trace 안에 묶는다*. *어디서 lag 가 시작됐는지* 수치로 보인다.

---

## 8. *5 가지 보장 × 5 가지 인프라 — 책임 행렬*

| 보장 ↓ / 인프라 → | Kafka | K8s | cgroup | DB | Redis |
|---|---|---|---|---|---|
| 지속성 | *Replication* | (storage class) | - | *WAL + fsync* | *AOF* |
| 순서 | *Partition* | - | - | *id 컬럼* | *Streams* |
| 격리 | (별도 cluster) | *Namespace + RBAC* | *cpu/memory.max* | *Schema/DB 분리* | *DB index* |
| 백프레셔 | *Consumer lag* | (HPA) | (throttling) | *Connection pool* | *Streams lag* |
| 관측가능성 | (메트릭 노출) | (kube-state-metrics) | (cAdvisor) | (Micrometer) | (INFO) |

각 보장이 *여러 layer 에 분산되어 있고*, 어느 한 layer 만 책임지면 *부족*. *모든 layer 가 각자 자기 영역 의 책임 을 다할 때 비동기 시스템 이 실제로 돈다*.

---

## 9. *내 인프라 의 실제 책임 분담*

### 9.1 *sparta-msa-project (이커머스)*

| 컴포넌트 | 책임 |
|---|---|
| Kafka (sparta-prod) | order ↔ payment 이벤트 전파 |
| K8s (Lemuel K3s) | pod 분산 + tier 격리 (worker / storage) |
| cgroup | priorityClass `lemuel-production` 우선 스케줄 |
| MySQL + pgvector | outbox + processed_events + 비즈니스 데이터 |
| Redis | rate limit + 세션 |
| Prometheus | Micrometer hikaricp.* + outbox.* 메트릭 |

### 9.2 *settlement (정산)*

| 컴포넌트 | 책임 |
|---|---|
| PostgreSQL | outbox (event_id UNIQUE) + processed_events PK + settlement UK = *Triple Idempotency* |
| Kafka | 이벤트 전파 + replay |
| Spring Batch (야간) | 일 reconciliation |
| Micrometer | Outbox 4 종 메트릭 (pending / published / dead_letter / publish_duration) |
| ArchUnit | 컴파일러 수준 경계 강제 |

### 9.3 *lemuel-quant-core (양적 분석)*

| 컴포넌트 | 책임 |
|---|---|
| 호스트 cron | R 잡 주기 실행 (cgroup 안 거치고 호스트 RAM burst) |
| Redis pub/sub | GARCH / ARIMA 모델 출력 전파 |
| Cloudflare R2 | 일간 리포트 snapshot 저장 |
| host journald + fluent-bit | 로그를 K8s logging stack 으로 |

---

## 10. *비동기 시스템의 흔한 실패 모드 7 가지*

### 10.1 *Replication factor 1 의 데이터 손실*

비용 절감 이유로 broker 1 대 / replication factor 1 — *그 broker 죽으면 commit 메시지 손실*.

### 10.2 *Partition key 잘못 — 순서 깨짐*

`orderId` 가 partition key 인데 *코드에서 userId 를 우연히 key 로 보낸* 케이스. 같은 주문의 이벤트가 *다른 partition 으로 가서 순서 보장 안 됨*.

### 10.3 *Consumer group 의 rebalance 폭주*

consumer pod 가 *자주 떴다 죽었다* 하면 Kafka rebalance 가 *지속 발생*. 그 동안 *모든 consumer 가 멈춤*. 주의 깊은 *startup probe + readiness 시점* 조정 필요.

### 10.4 *Outbox polling 의 Lost-Update*

A worker 가 PENDING 행 fetch + 처리 중 B worker 가 같은 행 fetch — *중복 처리*. *SELECT FOR UPDATE SKIP LOCKED* 또는 *distributed lock* 으로 해결.

### 10.5 *DLQ 의 조용한 누적*

[velero kopia 좀비 잡 사고](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug.html) 의 패턴 — DLQ 가 알람 없이 *한 달간 누적*. *DLQ count 알람 필수*.

### 10.6 *Connection pool 의 Kafka publish 점유*

[HikariCP 글](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) 의 함정 — @Transactional 안에서 *kafkaTemplate.send().get()* 호출 → *Kafka 응답 대기 5 초 동안 DB connection 점유* → p99 폭주.

### 10.7 *Cgroup throttling 의 조용한 lag*

Kafka consumer pod 의 cpu limit 부족 → cgroup throttling → 처리 지연 → consumer lag 누적. velero 사고와 같은 패턴.

---

## 11. *교훈 — 코드와 인프라의 책임 분담*

> *"비동기 연동 의 코드는 교과서에 있다. 그 코드가 *제대로 도는 5 가지 보장* (지속성/순서/격리/백프레셔/관측가능성) 은 *인프라 가 분담* 한다. 코드 작성자가 그 분담을 모르면 *조용히 비동기 시스템이 부러진다*."*

비동기 시스템의 *진짜 디자인* 은 *코드 + 인프라 의 합치된 책임 분담*. *Kafka 하나로 전부 해결된다는 환상* 은 *비싸게 부서진다*.

다음 비동기 시스템을 설계할 때 — *5 가지 보장 × 5 가지 인프라 의 책임 행렬* 을 *그려보자*. *어느 칸이 비어 있는지가 다음 사고의 후보 점*.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [R 은 클러스터에 *없다*](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · [HikariCP 의 5 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) · [백엔드 응답시간 + 모니터링](/2026/06/10/backend-latency-and-monitoring-truth.html) · [Python vs Java 알고리즘](/2026/06/11/python-vs-java-algorithms-comparison.html) · [정산 정합성](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) · [AI 가 할 수 있는 것 / 못 하는 것](/2026/06/15/ai-coding-limits-and-anti-spaghetti-criteria.html) · [비동기 배치 7 패턴](/2026/06/15/batch-as-async-integration-pattern.html) · *비동기 연동과 인프라 (현재 글)*

*이 글은 sparta-msa-project / settlement / lemuel-quant-core / helm-deploy 의 운영 경험 + Kafka cluster + Lemuel K3s 의 5 노드 토폴로지 + cgroup v2 의 throttling 사고 + HikariCP / Redis / Prometheus 의 실제 사례를 종합.*
