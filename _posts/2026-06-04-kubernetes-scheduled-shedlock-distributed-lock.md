---
layout: post
title: "쿠버네티스 시대의 @Scheduled 함정 — replicas: 1 에서도 ShedLock 이 필요한 *세 가지* 이유, 그리고 settlement·lemuel-xr 의 7 scheduler 실전 도입기"
date: 2026-06-04 04:50:00 +0900
categories: [backend, kubernetes, spring]
tags: [shedlock, distributed-lock, scheduled, kubernetes, spring-boot, outbox, settlement, lemuel-xr, replicas, ha]
---

K3s 클러스터에 *60+ prod 서비스* 를 운영하면서 어느 날 stat 을 봤다:

```
$ kubectl get deploy -A | awk '$3+0 > 1'
kube-system  coredns  2/2   ← 시스템만
```

**모든 prod app 의 replicas: 1**. 즉 *@Scheduled 메서드가 두 instance 에 의해 동시 실행* 될 일이 *원리상 없다*. 그렇다면 ShedLock 같은 *분산 락* 은 *필요 없는* 게 아닌가?

답은 **아니다**. *replicas: 1 인데도* ShedLock 이 필요한 *세 가지* 상황이 있고, 새벽 4 시에 settlement / lemuel-xr 의 7 scheduler 에 ShedLock 을 도입한 *그 결정* 의 근거를 정리한다.

---

## TL;DR

- ✅ **replicas: 1 = 동시 실행 위험 *0***. 그래도 ShedLock 이 필요한 이유 3 가지:
  1. **ArgoCD rolling update** — 옛/새 pod 가 *0.5~5 초 공존* 하는 순간 중복 실행
  2. **kubectl scale + 미래 HA** — *replicas 늘리는 그 순간* 부터 코드 변경 없이 안전
  3. **수동 트리거의 사고** — `kubectl create job --from=cronjob/...` 으로 *옛 instance* 가 또 돌릴 수 있음
- ShedLock = *DB row 단위* 분산 락. `name` 컬럼 UNIQUE + `lock_until` TIMESTAMPTZ 로 *deadlock 방지*
- JDBC / Redis / Mongo / Zookeeper 등 다양한 backend 지원. *Postgres 운영 중* 이면 *JdbcTemplate provider 가 default 최적*
- 실전 적용: settlement 의 *Outbox publisher + 정산 배치 3종 + Payout* + lemuel-xr 의 *Outbox relay + 일별 지표 집계* = **7 곳**

---

## 1. *왜* @Scheduled 가 위험한가 — 기본 시나리오

```java
@Scheduled(fixedDelay = 2000)
public void publishOutboxEvents() {
    var pending = repo.findByStatus("PENDING", PageRequest.of(0, 100));
    for (var event : pending) {
        kafka.send(event.getTopic(), event.getPayload());
        event.setStatus("PUBLISHED");
        repo.save(event);
    }
}
```

`replicas: 2` 환경에서 이 코드:

```
[Pod A]                       [Pod B]
2초 trigger                   2초 trigger
   ↓                              ↓
SELECT WHERE status='PENDING' SELECT WHERE status='PENDING'  ← 둘 다 같은 row 가져옴
   ↓                              ↓
kafka.send(event)             kafka.send(event)              ← 같은 event 2번 발행
   ↓                              ↓
UPDATE status='PUBLISHED'     UPDATE status='PUBLISHED'      ← 첫번째가 commit, 두번째 no-op
```

결과: **같은 event 가 Kafka 에 2 번 발행**. consumer 가 idempotent 가 아니면 *중복 처리*.

너 settlement 의 **Triple Idempotency** (L1 event_id UNIQUE / L2 processed_events PK / L3 자연키 UNIQUE) 가 *수신측에서* 막아주지만, *발행측 중복 자체를 막는 것이 1차 방어*.

---

## 2. *replicas: 1 인데도* 위험한 3 가지 상황

### 시나리오 A — ArgoCD Rolling Update 중 *짧은 공존*

```
시점 T+0:   [PodA v1 실행 중]
시점 T+1s:  ArgoCD sync → new ReplicaSet 생성
시점 T+2s:  [PodA v1 실행 중]  [PodB v2 Pending → Running]
시점 T+3s:  [PodA v1 실행 중]  [PodB v2 ready]   ← *0.5~5 초 공존*
시점 T+4s:  [PodA v1 Terminating]  [PodB v2 실행 중]
시점 T+10s: [PodB v2 실행 중]
```

**T+3s 의 0.5~5 초 동안 *둘 다 @Scheduled trigger*** 가능. 흔한 *missed 시나리오*.

`maxSurge: 25%` + `maxUnavailable: 0` 같은 일반 rolling update 설정에서 *항상* 발생.

### 시나리오 B — *kubectl scale* + 미래 HA

```bash
kubectl scale deploy/settlement-app -n settlement-prod --replicas=2
```

*이 한 줄을 치는 순간* 부터 *분산 락이 없으면 중복 발행 시작*. ShedLock 을 *미리* 도입해뒀으면 *코드 변경 없이* 안전.

내 환경에서 *지금은 replicas: 1* 이지만 향후 HA 가 *언제든 필요*. *그 시점에 도입* 은 *production change* 의 *risk + 시간 부담*. *미리* 도입이 *제로 코스트 보험*.

### 시나리오 C — 운영자의 *수동 트리거*

```bash
# 운영자가 "정산 배치가 안 돈 것 같다" 며 수동 실행
kubectl create job --from=cronjob/settlement-create -n settlement-prod manual-run

# 동시에 정기 @Scheduled 도 정상 시간에 trigger
# → 2 instance 가 *같은 작업* 수행
```

CronJob *수동 trigger* + *@Scheduled 정기 trigger* 가 *동시* 일 수 있음. ShedLock 이 *같은 name* 이면 *둘 중 하나만 실행*.

### 결론

| 상황 | replicas: 1 | replicas: 2+ | rolling update 중 | 수동 trigger |
|---|---|---|---|---|
| @Scheduled 중복 위험 | ❌ | ⚠️ | ⚠️ (0.5~5 초) | ⚠️ |
| ShedLock 효과 | ✅ 안전 | ✅ 안전 | ✅ 안전 | ✅ 안전 |

*replicas 가 무엇이든* ShedLock 이 *비용 0 의 안전망*.

---

## 3. 분산 락의 *4 가지 backend* — 무엇을 선택할까

| Backend | 동작 | 장점 | 단점 | 적합 |
|---|---|---|---|---|
| **JDBC (PostgreSQL/MySQL)** | DB row 단위 락 (UNIQUE + UPDATE) | *추가 인프라 0*, 트랜잭션 일관성 | DB 가 죽으면 락도 불능 | *DB 가 이미 운영 중* 인 환경 (대부분) |
| **Redis** | SETNX + EXPIRE | 빠름, 가벼움 | *Redis 가 추가 의존성*, Redlock 의 일관성 논쟁 | 이미 Redis 운영 중 |
| **MongoDB** | 단일 document 의 atomic update | 가벼움 | MongoDB 가 추가 의존성 | Mongo 운영 중 |
| **Zookeeper / etcd** | Consensus 기반 *진짜 분산* | *강한 일관성 보장* | 운영 복잡, *오버킬* | 대규모 분산 시스템 |

내 환경: *모든 prod 가 Postgres 운영 중*. 그래서 **JDBC backend 가 자명한 선택**.

```kotlin
implementation("net.javacrumbs.shedlock:shedlock-spring:5.16.0")
implementation("net.javacrumbs.shedlock:shedlock-provider-jdbc-template:5.16.0")
```

---

## 4. ShedLock 동작 원리 — *DB 한 row 의 전쟁*

### 4.1 핵심 테이블

```sql
CREATE TABLE shedlock (
    name        VARCHAR(64)  PRIMARY KEY,    -- 락 이름 (UNIQUE)
    lock_until  TIMESTAMPTZ  NOT NULL,        -- 락 자동 만료 시점
    locked_at   TIMESTAMPTZ  NOT NULL,        -- 락 잡은 시점
    locked_by   VARCHAR(255) NOT NULL         -- 누가 잡았는지 (hostname/podId)
);
```

`name` 이 PRIMARY KEY → *같은 이름의 락은 절대 두 row 못 만듦*. 이게 락의 *기반*.

### 4.2 락 획득 흐름

```
Pod A 의 @Scheduled trigger
   ↓
INSERT INTO shedlock (name, lock_until, locked_at, locked_by)
VALUES ('outbox-publisher', NOW() + INTERVAL '30 seconds', NOW(), 'pod-a-xyz')
ON CONFLICT (name) DO UPDATE SET
  lock_until = NOW() + INTERVAL '30 seconds',
  locked_at = NOW(),
  locked_by = 'pod-a-xyz'
WHERE shedlock.lock_until <= NOW()  ← 옛 락이 만료된 경우만 갱신
RETURNING *;
   ↓
RETURNING 한 row 가 *내 것* 이면 → 실행
                       *남의 것 (만료 안 됨)* 이면 → skip
```

핵심 트릭: **`WHERE shedlock.lock_until <= NOW()`** — *만료된 락만 빼앗기 가능*. 다른 instance 가 *살아있는 락* 잡고 있으면 *건드릴 수 없음*.

### 4.3 락 해제

```sql
-- 작업 끝나면
UPDATE shedlock
SET lock_until = NOW()         -- 즉시 만료
WHERE name = 'outbox-publisher' AND locked_by = 'pod-a-xyz';
```

작업 끝 즉시 `lock_until` 을 NOW() 로 → 다음 instance 가 *바로 잡을 수 있음*.

### 4.4 *Deadlock 방지* — `lockAtMostFor`

만약 *Pod A 가 작업 중 죽으면* 락 해제 SQL 이 안 돌면 *영원히 락이 잡힌 채*?

→ `lockAtMostFor` 이 *최대 락 유지 시간*. 그 시간 지나면 *자동 만료* — 다른 instance 가 빼앗을 수 있음.

```java
@SchedulerLock(
    name = "outbox-publisher",
    lockAtMostFor = "PT1M",      // 1 분 안에 끝나야 함. 안 끝나면 *다음 instance 가 빼앗음*
    lockAtLeastFor = "PT500MS"   // 빠른 재실행 방지 (clock drift 보호)
)
```

`lockAtMostFor` 는 *작업의 *최악 시간 추정***. 너무 짧으면 *남은 instance 가 빼앗아 중복*, 너무 길면 *deadlock 길어짐*. *p99 작업 시간 × 2~3 배* 가 합리적.

### 4.5 *Clock Drift* 방어 — `usingDbTime()`

여러 instance 의 *시스템 시간이 미세 다름* (NTP sync 했어도 ±100ms 흔함):

```
Pod A 의 NOW(): 04:00:00.000
Pod B 의 NOW(): 04:00:00.300   ← 300ms 빠름
```

두 instance 가 *각자 자기 NOW()* 로 `lock_until` 계산 → *Pod B 가 *항상* 락 빼앗음*.

해결: **`usingDbTime()`** — 모든 시간 계산을 *DB time* 으로. DB 는 *하나*. 모든 instance 가 *같은 시계* 사용.

```java
return new JdbcTemplateLockProvider(
    JdbcTemplateLockProvider.Configuration.builder()
        .withJdbcTemplate(new JdbcTemplate(dataSource))
        .usingDbTime()  // ← clock drift 면역
        .build());
```

---

## 5. 실전 도입 — settlement + lemuel-xr 의 7 scheduler

### 5.1 의존성

```kotlin
// shared-common/build.gradle.kts
api("net.javacrumbs.shedlock:shedlock-spring:5.16.0")
api("net.javacrumbs.shedlock:shedlock-provider-jdbc-template:5.16.0")
```

`api` 로 노출 → settlement-service, order-service, payout 모두 사용 가능.

### 5.2 Bean 구성 (한 번만)

```java
@Configuration
@EnableSchedulerLock(defaultLockAtMostFor = "PT10M")
public class SchedulingLockConfig {

    @Bean
    public LockProvider shedLockProvider(DataSource dataSource) {
        return new JdbcTemplateLockProvider(
            JdbcTemplateLockProvider.Configuration.builder()
                .withJdbcTemplate(new JdbcTemplate(dataSource))
                .usingDbTime()
                .build());
    }
}
```

### 5.3 Flyway migration

```sql
-- V47__init_shedlock.sql
CREATE TABLE shedlock (
    name        VARCHAR(64)  PRIMARY KEY,
    lock_until  TIMESTAMPTZ  NOT NULL,
    locked_at   TIMESTAMPTZ  NOT NULL,
    locked_by   VARCHAR(255) NOT NULL
);
```

### 5.4 7 scheduler 적용 매트릭스

| Repo | Class | name | lockAtMostFor | 트리거 |
|---|---|---|---|---|
| settlement | OutboxPublisherScheduler.publishPendingEvents | outbox-publisher | 1m | fixedDelay 2초 |
| settlement | SettlementScheduler.scheduledCreateDailySettlements | settlement-create-daily | 30m | 매일 02:00 |
| settlement | SettlementScheduler.scheduledConfirmDailySettlements | settlement-confirm-daily | 30m | 매일 03:00 |
| settlement | HoldbackReleaseScheduler.releaseDue | settlement-holdback-release | 30m | 매일 03:00 KST |
| settlement | PayoutScheduler.execute | settlement-payout-execute | 1h | 매일 04:00 KST |
| lemuel-xr | OutboxRelayJob.relay | xr-outbox-relay | 1m | fixedDelay 5초 |
| lemuel-xr | ComputeDailyMetricsJob.run | xr-compute-daily-metrics | 30m | 매일 04:00 KST |

### 5.5 코드 변경 *한 줄씩*

```java
// before
@Scheduled(fixedDelayString = "${app.outbox.polling-delay-ms:2000}")
public void publishPendingEvents() { ... }

// after
@Scheduled(fixedDelayString = "${app.outbox.polling-delay-ms:2000}")
@SchedulerLock(
    name = "outbox-publisher",
    lockAtMostFor = "PT1M",
    lockAtLeastFor = "PT500MS")
public void publishPendingEvents() { ... }
```

*비즈니스 로직 0 변경*. 안전.

---

## 6. 흔한 함정 5 가지

### ❌ 함정 1: `name` 충돌

```java
@SchedulerLock(name = "outboxPublisher")   // settlement 의 락
@SchedulerLock(name = "outboxPublisher")   // lemuel-xr 의 락 (다른 서비스!)
```

같은 name → *서로 다른 서비스의 scheduler 가 서로 차단*. **name 에 *서비스 prefix*** 권장:
- ✅ `settlement-outbox-publisher`
- ✅ `xr-outbox-relay`
- ❌ `outbox-publisher` (충돌 가능)

내 환경에선 *서비스별 prefix* 사용.

### ❌ 함정 2: `lockAtMostFor` 너무 짧음

```java
@SchedulerLock(name = "...", lockAtMostFor = "PT5S")  // 5 초만 락 유지
public void heavyBatch() {
    // 실제 10 초 걸리는 작업
}
```

5 초 후 다른 instance 가 *락 빼앗음* → *둘이 동시 실행*. *최악 시간 × 2~3* 권장.

### ❌ 함정 3: `lockAtLeastFor` 미설정

```java
@SchedulerLock(name = "...", lockAtMostFor = "PT1M")
@Scheduled(fixedDelay = 100)  // 100ms 마다
```

작업이 *50ms* 안에 끝나면 락 해제 → *바로 다른 instance 가 또 잡음* → clock drift 시 *같은 instance 가 또* 실행. `lockAtLeastFor` 로 *최소 보장 시간* 명시 권장.

### ❌ 함정 4: `@Transactional` + `@SchedulerLock` 순서

```java
@Transactional
@SchedulerLock(name = "...")        // ← 락이 트랜잭션 *안* 에서 잡힘
public void doWork() { ... }
```

이러면 *트랜잭션 commit 시점에 락 해제* — 락이 *너무 일찍* 풀림. 또는 *데드락* 위험. **`@SchedulerLock` 이 `@Transactional` *바깥* 에 있어야** — Spring AOP proxy 순서 중요.

```java
@SchedulerLock(name = "...")        // ← AOP 가 *바깥* 에서 잡음
@Transactional
public void doWork() { ... }
```

### ❌ 함정 5: 같은 `name` 의 *서로 다른 메서드*

```java
@Scheduled @SchedulerLock(name = "daily")
public void method1() { ... }

@Scheduled @SchedulerLock(name = "daily")  // 같은 name!
public void method2() { ... }
```

*둘 중 하나만 실행* — 의도 위배. *각 메서드별 고유 name*.

---

## 7. 검증 — *진짜 동작하는지* 확인

### 7.1 락 테이블 직접 조회

```bash
kubectl exec -n settlement-prod settlement-postgres-0 -- \
  psql -U postgres -d settlement -c "SELECT * FROM shedlock ORDER BY locked_at DESC"
```

```
        name             |          lock_until          |          locked_at           |        locked_by
-------------------------+------------------------------+------------------------------+--------------------------
 outbox-publisher        | 2026-06-04 04:50:23.123+09  | 2026-06-04 04:50:22.087+09  | settlement-app-xyz_12345
 settlement-create-daily | 2026-06-04 03:30:00.000+09  | 2026-06-04 03:00:01.456+09  | settlement-app-xyz_12340
```

→ *어떤 락이 잡혀있는지*, *언제까지 유지* 되는지 한 눈에.

### 7.2 로그 확인

```bash
kubectl logs -n settlement-prod settlement-app-xyz | grep -i "shedlock\|lock acquired\|lock released"
```

ShedLock 의 *DEBUG 레벨* 로그가 도움. application.yml:

```yaml
logging:
  level:
    net.javacrumbs.shedlock: DEBUG
```

### 7.3 *진짜* 검증 — replicas 2 로 한 번 띄워서 중복 실행 안 되는지

```bash
kubectl scale deploy/settlement-app -n settlement-prod --replicas=2

# 1 분 정도 보고
kubectl logs -n settlement-prod -l app=settlement-app --tail=100 | grep "publishOutbox"

# 원복
kubectl scale deploy/settlement-app -n settlement-prod --replicas=1
```

두 pod 의 로그를 *합쳐* 봐도 *같은 event_id 가 2 번 처리* 되지 않으면 ✅.

---

## 8. 운영 — *Outbox + Triple Idempotency + ShedLock* 의 3 단 방어

내 settlement 의 *완전한 안전망*:

```
                ┌──────────────────────────────────────┐
[발행측]        │   Pod A          Pod B               │
                │  @Scheduled    @Scheduled            │
                │     ↓             ↓                  │
                │  ShedLock      ShedLock              │ ← L0 (분산 락)
                │  ✅ acquired   ❌ skipped            │
                │     ↓                                │
                │  Outbox SELECT WHERE PENDING         │ ← L1 (event_id UNIQUE)
                │     ↓                                │
                │  Kafka publish + status='PUBLISHED'  │
                └──────────────┬───────────────────────┘
                               │
                               ▼ Kafka (at-least-once)
                               │
                ┌──────────────┴───────────────────────┐
[수신측]        │  Consumer (multiple instances)       │
                │     ↓                                │
                │  processed_events PK check           │ ← L2 (idempotent)
                │     ↓                                │
                │  Business INSERT WHERE natural_key   │ ← L3 (UNIQUE 제약)
                └──────────────────────────────────────┘
```

ShedLock 이 *L0 (발행 자체 중복 차단)*. Triple Idempotency 가 *L1/L2/L3 (수신측 중복 흡수)*. 둘이 *합쳐* 만이 *진짜 at-least-once + idempotent* 가 됨.

---

## 9. 비용 — 사실상 *0*

ShedLock 추가 비용:
- *추가 인프라*: 0 (Postgres 이미 운영 중)
- *Code change*: 6 줄 / scheduler (annotation + import)
- *DB load*: 무시 가능 (락 INSERT/UPDATE는 단일 row, < 1ms)
- *latency 증가*: ~5ms (락 acquire 시간)
- *Runtime memory*: ~몇 KB

vs *얻는 안전성*:
- 미래 HA 전환 *코드 변경 0*
- ArgoCD rolling update 중 *중복 발행* 차단
- 수동 trigger 와 정기 trigger 의 *우연한 동시 실행* 차단

**ROI = ∞**. 안 도입할 이유가 없음.

---

## 10. 결론 — *지금* 도입의 가치

K8s 시대의 *대부분* Spring 서비스가 *@Scheduled* 를 쓴다. *replicas 가 무엇이든* ShedLock 은 *추가 비용 거의 0 의 안전망*. 특히:

- *Outbox publisher* 처럼 *at-least-once 시스템의 발행측*
- *daily batch* 처럼 *돈/정산이 걸린* 작업
- *수신측 idempotency 가 약한* 옛 시스템 통합

이런 곳엔 *지금 당장* 도입 가치.

내 환경의 *7 scheduler* (settlement 5 + lemuel-xr 2) 가 모두 *분산 락 보호* 받음. 미래 HA 가 *kubectl scale 한 줄* 로 가능해짐. 작업 시간 *30 분*, 추가 비용 *연 0 원*.

**한 줄 결론:** *replicas: 1 이라도 K8s 의 rolling update + 미래 HA + 수동 트리거 때문에 ShedLock 은 *비용 0 의 보험***. 지금 *Spring + Postgres* 운영 중이면 *주말 한 번에 도입* 권장.

---

## 참고

- [ShedLock GitHub](https://github.com/lukas-krecan/ShedLock) — 공식 문서
- [ShedLock JDBC Lock Provider](https://github.com/lukas-krecan/ShedLock/tree/master/providers/jdbc/shedlock-provider-jdbc-template)
- [Spring `@Scheduled` reference](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)
- *Chris Richardson, Microservices Patterns* — Transactional Outbox 패턴
- 관련 글:
  - [DDD ↔ MSA — Bounded Context = 서비스 경계]({% post_url 2026-05-29-ddd-msa-bounded-context-aggregate-event-storming %})
  - [Harness Engineering ④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
  - [K3s 의 한계 — 1 년 운영 경험]({% post_url 2026-05-29-k3s-limitations-real-world-homelab-experience %})
  - [홈랩 Capacity Planning]({% post_url 2026-05-29-homelab-capacity-planning-datacenter-style %})
