---
layout: post
title: "*비동기 연동* 을 *배치* 로 하는 법 — *실시간이 안 맞을 때* 의 *7 가지 설계 패턴*"
date: 2026-06-15 15:30:00 +0900
categories: [backend, architecture, integration, batch]
tags: [async, batch, micro-batch, kafka, spring-batch, cronjob, outbox, polling, etl, scheduler, idempotency]
---

> *"비동기 연동* 이라고 하면 *Kafka 부터 떠올린다*. 그러나 *내 인프라 의 *비동기 의 *80% 는 *배치 다*. *settlement 의 outbox polling, velero 의 kopia maintenance, R 의 cron 잡, pg-backup, log-error-alerter, elastic-secret-replicator* — *전부 *주기적으로 도는 *배치 패턴 의 *비동기 연동**."

이 글은 *언제 *배치 가 *실시간 보다 적절 한가*, *그리고 *배치 비동기 연동 을 *설계 하는 *7 가지 패턴* 을 *본인 인프라 의 *실제 사례* 와 함께 풀어본다. *Spring Batch, K8s CronJob, outbox polling* 같은 *서로 다른 layer 의 같은 본질* 을 *한 그림에 묶는다*.

---

## TL;DR — *한 줄 결론*

> *비동기 연동* 은 *Kafka 같은 *event-stream* 만 의미하지 않는다. *주기적으로 도는 *배치* 도 *비동기 의 한 형태*. *언제 어느 형태 가 적절 한지* 는 *latency / 정합성 / 운영 부담 / 멱등성 의 *4 가지 trade-off* 의 함수. 그리고 *micro-batch 가 *event-stream 과 *대량 배치 의 *중간 지점* 에서 *대부분의 실무 문제 의 *황금 비율* 이다*.

---

## 1. *발단 — *비동기 = Kafka 가 *아니다**

신입 시절 *비동기 연동 의 *교과서* :

```
A → Kafka publish → B consume → 처리 완료
```

이게 *고전적 event-driven*. 단 *실무 의 *비동기 연동 의 *상당 부분* 은 *이 형태가 *아니다* :

- *settlement 의 outbox polling* — 1 초 주기로 DB 의 PENDING 행 *조회 → publish*
- *velero kopia maintenance* — 5 분 주기 CronJob 으로 *백업 저장소 정비*
- *R 의 GARCH 모델 publish* — 5 분 주기 cron 잡으로 *Redis 채널에 결과 publish*
- *pg-backup* — 매일 02:00 *PostgreSQL dump → R2 업로드*
- *log-error-alerter* — 5 분 주기로 *ES 검색 → Telegram 알림*
- *elastic-secret-replicator* — 시간당 *ES secret 을 *다른 namespace 로 *복제*

*이 모두 *비동기 연동* 이다*. *다만 *event-stream 이 아니라 *배치/polling*.

---

## 2. *언제 *배치* 가 *실시간* 보다 *적절 한가**

### 2.1 *4 가지 *trade-off*

| 기준 | Event-Stream (Kafka) | 배치 (CronJob / polling) |
|---|---|---|
| Latency | *수십 ms ~ 수 초* | *분 ~ 시간* |
| 운영 부담 | *broker / replication / partition* | *cron + script* |
| 정합성 | *복잡 (idempotency 필수)* | *상대적으로 단순 (transaction 안 묶음)* |
| 자원 활용 | *항상 listening (낮은 대기 비용)* | *주기적 polling (불필요한 호출)* |

### 2.2 *배치 가 *유리한 5 가지 경우**

1. *latency 가 분/시간 단위로 *느슨해도 되는 *작업** — 일 정산, 리포트
2. *입력 데이터가 *주기적으로 쌓이는* 패턴* — 어제의 거래 집계
3. *DB / 파일 시스템 의 *상태 변화 를 *주기적으로 모니터링** — outbox 의 PENDING 행
4. *외부 API 의 *호출 횟수 제약* (rate limit) — 5 분에 한 번 *모아서 batch 호출*
5. *운영 단순화 가 *우선* — broker 운영 부담 없이 *cron 한 줄*

### 2.3 *실시간 이 *유리한 5 가지 경우**

1. *Latency 가 *초 단위* 이하로 *중요* — 결제 승인, 인증
2. *Order-preserving 한 stream 처리* — 한 사용자 의 행동 시퀀스
3. *Backpressure 가 *명시적으로 필요* — Kafka consumer lag 기반
4. *Replay 가 *자주 필요* — 새 consumer 가 *과거 이벤트 재처리*
5. *동시 다발적 broadcast* — 한 이벤트가 *여러 consumer 에 *fan-out*

---

## 3. *Layer 1 — *Polling 기반 비동기 — *settlement outbox 패턴**

### 3.1 *outbox polling 의 동작*

[정산 정합성 글](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) 의 *outbox publish worker* :

```kotlin
@Scheduled(fixedDelay = 1000)  // 1초마다
fun publishPendingEvents() {
    val pending = outboxRepository.findByStatusOrderById(PENDING, limit = 100)
    pending.forEach { event ->
        try {
            kafkaTemplate.send(event.topic, event.eventId, event.payload).get()
            event.status = PUBLISHED
            outboxRepository.save(event)
        } catch (e: Exception) {
            event.attempts += 1
            if (event.attempts >= 10) event.status = DEAD_LETTER
            outboxRepository.save(event)
        }
    }
}
```

이게 *micro-batch async pattern*. *1 초 단위 의 *짧은 배치* — *latency 가 *1 초 이내* 인 *비동기 연동*.

### 3.2 *왜 *micro-batch 가 *황금 비율* 인가*

- *Event-stream (Kafka direct trigger)* — *DB 와 *원자성 못 묶음* 의 *dual-write 사고*
- *야간 대량 배치 (cron 매일)* — *latency 24 시간*. *사용자 가 *기다림*
- *Micro-batch (polling 1초)* — *DB 원자성 + 1 초 latency 의 *황금 절충*

이게 *내 *settlement-service 의 *정답*. *event-driven 의 *환상* 보다 *현실적*.

### 3.3 *Partial index 의 *비용 절감**

```sql
CREATE INDEX idx_outbox_pending ON outbox (id) WHERE status = 'PENDING';
```

*전체 outbox 의 *99% 는 *PUBLISHED* — *그 행들은 *polling 쿼리 에 *안 잡힘*. *index 가 *PENDING 만 *모은다*. *polling 비용 이 *거의 0*.

---

## 4. *Layer 2 — *CronJob 기반 *주기 배치**

### 4.1 *Kubernetes CronJob — *cloud-native cron**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: log-error-alerter
spec:
  schedule: "*/5 * * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      backoffLimit: 1
      ttlSecondsAfterFinished: 3600   # 1시간 후 자동 GC
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: alerter
              image: curlimages/curl:8.10.1
              command: [sh, -c, "..."]
```

이 *7 줄 의 spec* 에 *비동기 배치 연동 의 *모든 패턴* 이 *집약되어 있다*.

### 4.2 *각 옵션 의 *진짜 의미**

| 옵션 | 의미 | 함정 |
|---|---|---|
| `schedule` | *cron 표현식* | *서버 timezone 의 함정* |
| `concurrencyPolicy: Forbid` | *이전 잡 끝나기 전엔 다음 잡 안 시작* | *잡이 길어지면 *건너뜀* |
| `successfulJobsHistoryLimit` | *성공 잡 보관 수* | *디스크 / kube-state-metrics 부담* |
| `failedJobsHistoryLimit` | *실패 잡 보관 수* | *너무 크면 좀비 alert 패턴* |
| `backoffLimit` | *재시도 횟수* | *너무 작으면 일시 환경 변화 민감* |
| `ttlSecondsAfterFinished` | *잡 끝난 후 자동 삭제 시간* | *없으면 좀비 잡 firing* |

내 [log-error-alerter 의 *좀비 잡 사고*](https://github.com/MyoungSoo7/helm-deploy/pull/39) — *failedJobsHistoryLimit: 5* 라 *옛 실패 잡 5 개가 *cluster 에 남아* *kube_state_metrics 가 *과거 실패의 *firing 을 *지속* 시킨 패턴.

### 4.3 *concurrencyPolicy 의 *3 가지 선택**

- `Allow` (기본) — *전 잡과 새 잡 *동시 실행 허용*. *순서 보장 안 됨*.
- `Forbid` — *전 잡이 끝나기 전엔 새 잡 *건너뜀*. *순서 보장*. *밀리면 *skip*.
- `Replace` — *전 잡 *kill 하고 *새 잡 시작*. *진행 중 작업 *손실 가능*.

*정합성 중요한 경우 `Forbid`*. *최신 데이터 우선이면 `Replace`*. *Allow 는 실수가 *대부분*.

---

## 5. *Layer 3 — *호스트 cron — *systemd 의 비동기 배치**

내 [R 글](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) 에서 다룬 패턴. *K8s 안이 아니라 *호스트 OS 의 *crontab + systemd timer* :

```cron
# 매 5 분 — GARCH(1,1) 변동성 추정 → Redis publish (시장 시간만)
*/5 0-7,10-23 * * 1-5  cd $LQC_HOME && Rscript r/stat_models/garch_volatility.R btcusdt \
                       >> $LQC_LOG/garch.log 2>&1
```

### 5.1 *K8s CronJob vs 호스트 cron 의 *trade-off*

| 항목 | K8s CronJob | 호스트 cron |
|---|---|---|
| 분산 / 고가용 | *Kubernetes scheduler 가 자동 분산* | *단일 호스트* |
| 리소스 격리 | *cgroup + namespace* | *호스트 OS 공유* |
| 관측성 | *kube-state-metrics 자동* | *log 기반 수동* |
| 의존성 | *컨테이너 이미지* | *호스트 환경* |
| 운영 부담 | *Helm chart + ArgoCD* | *crontab + git* |

### 5.2 *왜 *R 잡 은 *호스트 cron 인가*

[R 글](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) 의 결론 :

- *R 의 메모리 burst* 는 *cgroup 의 정적 limit 보다 호스트 전체 RAM 의 *free pool 과 맞다*
- *데이터 (Redis, PG, R2) 가 *호스트에 가깝다*
- *5 분마다 도는 단일 호스트 잡* 은 *분산 스케줄러 *남용* 할 이유 없음

*같은 비동기 배치 라도 *어디서 도는지 는 *workload 의 *성격 의 함수*.

---

## 6. *Layer 4 — *Spring Batch 의 *대량 ETL 배치**

### 6.1 *Spring Batch 가 적합한 경우*

- *백만 ~ 수억 행 의 *대량 데이터 ETL*
- *Chunk-oriented processing* — *수천 행 단위 로 *읽고 처리 하고 쓴다*
- *Restart / Skip / Retry* 가 *세밀하게 필요*
- *Job parameter / Step / Tasklet 의 *명시적 구조*

```kotlin
@Bean
fun settlementReconciliationJob(jobRepository: JobRepository, ...): Job {
    return JobBuilder("settlementReconciliationJob", jobRepository)
        .start(extractDailyOrdersStep)
        .next(aggregateBySellerStep)
        .next(compareWithSettlementStep)
        .next(notifyDiscrepanciesStep)
        .build()
}
```

이게 *settlement 의 *야간 reconciliation 배치 의 *전형적 구조*.

### 6.2 *Chunk size 의 *trade-off*

```yaml
chunk-size: 1000  # 한 번에 1000 행 처리
```

- *너무 크면* — 메모리 사용량 ↑, 중간 실패 시 *큰 재처리*
- *너무 작으면* — DB connection 점유 오래 + transaction 오버헤드

*1000 ~ 5000* 이 *대부분의 *황금 범위*. *입력 데이터 1 행 의 메모리 사이즈* × *chunk-size* 가 *수십 MB 이하* 가 되도록.

### 6.3 *Spring Batch 의 *Skip + Retry**

```kotlin
.faultTolerant()
.skip(InvalidDataException::class.java).skipLimit(100)
.retry(TransientException::class.java).retryLimit(3)
.backOffPolicy(ExponentialBackOffPolicy())
```

*100 건 까지의 *부적합 데이터 *skip*, *transient 에러 는 *3 회 retry 지수 백오프*. *대량 ETL 의 *현실 적 안정성*.

---

## 7. *Layer 5 — *외부 API 의 *주기적 폴링 / 호출 통합**

### 7.1 *Rate-limited 외부 API 의 패턴*

*증권 API, 결제 API, 환율 API* 같은 *호출 횟수 제한* 이 있는 외부 시스템.

```kotlin
@Scheduled(cron = "0 */5 * * * *")  // 매 5분
fun fetchExchangeRates() {
    val symbols = listOf("USD", "EUR", "JPY", "CNY")
    // 4 개 통화 를 *한 번 의 호출 로 *batch 조회* (API 가 batch endpoint 지원 시)
    val rates = exchangeRateApi.batchFetch(symbols)
    rates.forEach { rate ->
        exchangeRateRepository.save(rate)
    }
}
```

*실시간 호출* 하면 *분당 API 호출 *수백 회* — *rate limit 즉시 hit*. *5 분 주기 batch 로 *모아서 *4 개 한 번에* — *API 호출 *2 배 절약*.

### 7.2 *Webhook 못 받는 *외부 시스템 보완**

*외부 SaaS 가 *Webhook 안 보낼 때* → *주기적 polling 으로 *state 동기화*.

```kotlin
@Scheduled(fixedDelay = 60000)  // 1분마다
fun syncOrderStatuses() {
    val recentOrders = orderRepository.findRecentPending()
    recentOrders.forEach { order ->
        val externalStatus = paymentProviderApi.getStatus(order.externalId)
        if (externalStatus != order.status) {
            order.status = externalStatus
            orderRepository.save(order)
            eventPublisher.publish(OrderStatusChangedEvent(order))
        }
    }
}
```

이건 *micro-batch 의 *외부 시스템 적응*. *Webhook 대신 *주기 polling 으로 *외부 변경 추적*.

---

## 8. *Layer 6 — *배치 비동기 의 *7 가지 운영 패턴**

### 8.1 *Idempotency — 두 번 돌아도 안전*

*Cron 잡 이 *재실행 되거나 *동시 실행 되어도 *같은 결과* :

```kotlin
val today = LocalDate.now()
if (settlementBatchRepository.existsByDate(today)) {
    log.info("Settlement batch for $today already done. Skip.")
    return
}
// 처리...
settlementBatchRepository.markDone(today)
```

*날짜 / job 식별자 로 *중복 차단*.

### 8.2 *Distributed lock — *클러스터 중복 실행 방지**

```kotlin
@Scheduled(fixedDelay = 5000)
fun process() {
    val lock = redisLockRegistry.obtain("settlement-batch-lock")
    if (!lock.tryLock(1, TimeUnit.SECONDS)) return  // 다른 노드가 처리 중
    try {
        // 처리
    } finally {
        lock.unlock()
    }
}
```

*Application replicas 3 개* — *각자 cron 도는데 *동시에 *같은 outbox 행 *처리* 하면 사고. *Redis distributed lock* 또는 *DB advisory lock* 으로 *한 노드만 처리*.

### 8.3 *Graceful shutdown — 처리 중 *중단 안전**

```kotlin
@PreDestroy
fun shutdown() {
    log.info("Waiting for in-flight batch to finish...")
    scheduler.shutdown()
    scheduler.awaitTermination(30, TimeUnit.SECONDS)
}
```

*K8s 가 *pod terminate* 보낼 때 *처리 중인 잡 *완료* 까지 *대기*. `terminationGracePeriodSeconds` 와 *잘 맞춰서* 설정.

### 8.4 *Backfill 가능성 — *과거 데이터 재처리**

*배치 가 *3 일 전부터 *깨졌다는 걸 *오늘 발견*. *과거 3 일 을 *수동 재처리* 할 수 있어야 한다.

```kotlin
@Scheduled(cron = "0 0 2 * * *")
fun dailyBatch() {
    runBatchFor(LocalDate.now().minusDays(1))
}

// 수동 호출 가능한 endpoint
fun runBatchFor(date: LocalDate) {
    // ...
}
```

*batch 의 *입력 파라미터 (date)* 가 *명시적* 이어야 *재실행 가능*.

### 8.5 *모니터링 — *실패 즉시 알람**

- *kube-state-metrics 의 `kube_job_failed`* — Alertmanager rule 로
- *Spring Boot Actuator 의 *Scheduled task 메트릭*
- *Micrometer 의 *Timer + Counter* 로 *각 batch 실행 시간 / 성공 / 실패*

### 8.6 *DLQ — *반복 실패 격리**

*같은 데이터가 *10 번 실패 하면 *처리 큐 에서 *제외* 하고 *수동 개입 알람*. [정산 정합성 글](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) 의 *outbox DLQ* 와 같은 패턴.

### 8.7 *Observability — *batch 흐름 의 trace**

*하나 의 batch 가 *수십 분 도는데 *어디서 막혔는지* 모르면 *디버깅 불가*. *Step 별 로그 + Micrometer Timer + OpenTelemetry trace* 가 *batch 의 *시각화 필수*.

---

## 9. *흔한 함정 5 가지*

### 9.1 *Cron 표현식 의 *timezone 함정**

```yaml
schedule: "0 0 9 * * *"   # 09:00 - 어느 시간대?
```

*K8s CronJob 은 *UTC 기본*. *09:00 UTC = 18:00 KST*. *예상 시간 다른 사고*. `spec.timeZone: Asia/Seoul` 명시 (K8s 1.27+).

### 9.2 *concurrencyPolicy: Allow 의 *암묵적 데이터 race**

기본값이 `Allow`. 잡이 *예상보다 오래 걸리면* *전 잡이 안 끝났는데 새 잡 시작* → *같은 데이터 *동시 처리* → 사고.

`Forbid` 명시 권장.

### 9.3 *backoffLimit: 1 의 *환경 민감*

*한 번 실패 = 잡 fail*. *일시 ES slow / 네트워크 hiccup 에도 fail*. 내 [log-error-alerter 사고](https://github.com/MyoungSoo7/helm-deploy/pull/40) 처럼 *환경 sensitivity*. *3~5* 가 안전.

### 9.4 *Polling 간격 너무 짧음*

*1 초 polling × 100 개 잡* = 초당 100 SELECT. *DB 부담 + connection pool 점유*. *partial index + reasonable 간격 (5 ~ 30 초)* 으로 균형.

### 9.5 *외부 API rate limit 무시*

*batch 가 *외부 API 100 회 호출* → *rate limit*. *재시도 폭주* → *rate limit 만 더*. *Exponential backoff + jitter + circuit breaker* 필수.

---

## 10. *언제 어느 layer 가 적합한가 — *결정 트리***

```
[비동기 연동 필요]
   │
   ├─ Latency 가 *초 단위* 이내 필수?
   │    ├─ YES → Event-stream (Kafka direct)
   │    └─ NO ↓
   │
   ├─ Latency *1초 이내* + DB 원자성 필수?
   │    ├─ YES → Outbox polling (micro-batch, settlement 패턴)
   │    └─ NO ↓
   │
   ├─ K8s 환경 + 컨테이너 격리 필요?
   │    ├─ YES → K8s CronJob (log-error-alerter, velero kopia 패턴)
   │    └─ NO ↓
   │
   ├─ 호스트 자원 활용 + 메모리 burst 큰 잡?
   │    ├─ YES → 호스트 cron + systemd (R 글의 quant-core 패턴)
   │    └─ NO ↓
   │
   ├─ 대량 데이터 ETL + step-by-step 처리?
   │    ├─ YES → Spring Batch (정산 reconciliation)
   │    └─ NO ↓
   │
   └─ 외부 API 동기화 + rate limit?
        └─ → 주기적 polling (exchange rate, payment status sync)
```

---

## 11. *교훈*

> *"비동기 연동* 은 *Kafka 한 가지 형태가 아니다*. *주기적으로 도는 *배치 도 *비동기 의 한 형태*. *Latency, 정합성, 운영 부담, 멱등성* 의 *4 가지 trade-off* 를 *workload 의 *성격 에 맞게 *선택* 하는 게 *진짜 설계*. *micro-batch (polling) + cron + Spring Batch + event-stream* 의 *4 가지 layer 가 *각자 *책임 영역* 을 갖는다*."*

내 인프라 의 *비동기 연동 의 *80%* 는 *micro-batch 와 *CronJob*. *Kafka 는 *나머지 20%* 의 *특수 영역*. *그 80% 를 *제대로 설계 하는 시야 가 *실무 의 *대부분* 을 *결정 한다*.

*다음에 *비동기 연동* 이 필요할 때 — *Kafka 부터 떠올리지 말고 *결정 트리 의 *4 단계 *각각 을 *함께 검토 하자**. *micro-batch 가 *황금 비율 인 경우 가 *생각보다 많다*.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [R 은 클러스터에 *없다*](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · [HikariCP 의 5 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) · [백엔드 응답시간 + 모니터링](/2026/06/10/backend-latency-and-monitoring-truth.html) · [Python vs Java 알고리즘](/2026/06/11/python-vs-java-algorithms-comparison.html) · [정산 정합성](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) · [AI 가 할 수 있는 것 / 못 하는 것](/2026/06/15/ai-coding-limits-and-anti-spaghetti-criteria.html) · *비동기 연동 배치 패턴 (현재 글)*

*이 글은 settlement / sparta-msa-project / lemuel-quant-core / helm-deploy 의 다양한 비동기 배치 잡 (outbox polling, log-error-alerter, R cron, pg-backup, elastic-secret-replicator, velero kopia maintenance) 의 운영 경험을 종합.*
