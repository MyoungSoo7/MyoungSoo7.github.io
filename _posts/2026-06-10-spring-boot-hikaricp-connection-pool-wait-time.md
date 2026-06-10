---
layout: post
title: "백엔드 개발자가 알아야 할 *DB 커넥션 대기시간* — Spring Boot + HikariCP 의 *5 가지 *시간 설정* 을 *전부 *합쳐서* 보는 시야*"
date: 2026-06-10 17:00:00 +0900
categories: [backend, spring-boot, database, sre]
tags: [hikaricp, spring-boot, connection-pool, jdbc, connection-timeout, idle-timeout, max-lifetime, validation-timeout, leakdetection, database, postgresql, mysql]
---

> 동료가 *p99 응답시간 알람* 을 받고 와서 말했다.
>
> *"DB 가 *느려*. *connection pool* 늘려야 해."*
>
> 그 말이 *틀린 건 아니다*. 다만 *정답도 아니다*. *DB 가 *느린지*, *pool 이 *작은지*, *pool 의 *시간 설정* 이 *서로 충돌하는지** 는 *완전히 다른 5 가지 진단*. *각각의 *처방* 도 *완전히 다르다*.

이 글은 *Spring Boot 의 *기본 connection pool, *HikariCP* 의 *5 가지 *시간 설정** — *connectionTimeout, idleTimeout, maxLifetime, validationTimeout, keepaliveTime* — 을 *각각 *무엇이며 *언제 막히고 *어떻게 *상호작용* 하는지* 를 *백엔드 개발자가 *반드시 알아야 할 시야* 로 풀어본다.

---

## TL;DR — *한 줄 결론*

> *DB connection pool 대기시간* 은 *connection pool 크기 단독* 이 아니라 *5 가지 시간 설정 (connectionTimeout / idleTimeout / maxLifetime / validationTimeout / keepaliveTime) + DB 측의 *idle session timeout** 의 *총합* 으로 결정된다. *어느 한 값* 만 *바꾼다고 해결* 되지 않는다. *전체 *시간 사슬* 을 *함께* 봐야 한다.

---

## 1. *발단 — *"DB 가 느리다"* 의 진단 함정*

가장 흔한 시나리오 :

- *Application log* 에 `HikariPool-1 - Connection is not available, request timed out after 30000ms` 가 *반복*
- 대시보드의 *p99 응답시간* 이 *튐*
- *DB 메트릭* (CPU, query latency) 은 *정상*

여기서 *3 가지 가능성* :

1. *Pool size 가 부족* — 최대 connection 다 점유 중, 대기열만 쌓임
2. *DB connection 가 *조용히 끊긴 채로* pool 에 *남아있음* — 가져가서 쓰려는 순간 실패
3. *DB 측 idle session timeout* 이 *HikariCP 의 maxLifetime* 보다 짧음 — *pool 이 *죽은 연결을 모르고 가지고 있다가* *런타임에 *깨짐*

*1번이 *흔하고 *눈에 잘 보이는 진단*. *2, 3 번은 *조용히 사고를 만든다*. *5 가지 *시간 설정* 의 *진짜 역할* 을 모르면 *2, 3 번* 을 *영원히 못 잡는다*.

---

## 2. *Spring Boot 의 *기본 pool — *HikariCP** 가 뭐길래*

Spring Boot 2.0 이후 *기본 DataSource 가 HikariCP*. 그 이유 :

- *벤치마크 1위* (대부분의 워크로드에서 *Tomcat JDBC / DBCP2 / C3P0* 보다 빠름)
- *작은 코드 size* (130KB) — *낮은 메모리 사용*
- *명확한 *시간 설정 모델*

기본 설정 :

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 10           # 의도적으로 maximum-pool-size 와 같음 (HikariCP 권장)
      connection-timeout: 30000  # 30s
      idle-timeout: 600000       # 10min
      max-lifetime: 1800000      # 30min
      validation-timeout: 5000   # 5s
      keepalive-time: 0          # disabled
      leak-detection-threshold: 0  # disabled
```

이 *7 개 시간 / 크기 설정* 의 *각 값이 *왜 그 값* 인지* 는 *진짜 운영* 에선 *매번 *다시 계산* 해야 한다*.

---

## 3. *connectionTimeout* — *진짜 사용자 가 *기다리는 시간**

> *Pool 에 *빈 connection 이 없을 때*, *얼마나 *기다릴지** 의 시간

### 3.1 *기본값 30s 의 *함정**

기본값 30 초는 *너무 길다*. *진짜 사용자의 *체감 timeout* 은 *3~5 초**. 30 초 기다리는 사이 *사용자는 *F5 누르고* *retry 요청* 보내고 — *pool 이 더 막힌다*.

권장 :

```yaml
hikari:
  connection-timeout: 3000  # 3s
```

이걸 *3 초로 짧게* 잡으면 *pool 부족 상태가 *빠르게 *503 으로 노출*. *조용한 대기* 가 아니라 *명시적 실패*. *Circuit breaker* 가 *backpressure 를 *상위 layer 에 전달*.

### 3.2 *p99 응답시간 = pool wait + query time*

```
HTTP 응답시간 = (pool 대기) + (query 실행) + (네트워크 + serialize)
              ↑
        이 부분 만 *5 초* 일 수도 있다
```

*p99 가 5 초인데 DB 메트릭은 *50ms* 같은 경우* — *5 초의 *대부분이 pool wait*. *DB 자체 는 멀쩡*, *pool 이 부족*.

진단 : *Micrometer 의 *`hikaricp.connections.pending`* + `hikaricp.connections.timeout`* 메트릭을 *Prometheus 에 노출*. *p99 가 *높을 때* 그 값들이 *함께 튀면* *진짜 원인 *pool 부족*.

### 3.3 *권장 pool size 공식*

```
pool size = ((core_count * 2) + effective_spindle_count)
```

(Brett Wooldridge, HikariCP 저자)

- CPU 4 core, SSD 1 개 → pool 9
- CPU 8 core, SSD 1 개 → pool 17
- *NVMe SSD 는 effective_spindle 을 *훨씬 크게* 잡아도 됨*

*공식은 *idle CPU 와 *blocking I/O* 의 균형*. *과도하게 크게 잡으면 *DB lock contention* + *컨텍스트 switch 비용*. *너무 작으면 *대기*.

---

## 4. *idleTimeout* — *유휴 connection 의 *수명**

> *minimum-idle 보다 많은 connection 이 *얼마나 idle 하면 *닫을지** 의 시간

### 4.1 *기본값 10 분 의 의미*

```yaml
maximum-pool-size: 20
minimum-idle: 5           # 최소 5 개는 유지
idle-timeout: 600000      # 10min — 5 개 초과한 connection 이 10분 idle 이면 close
```

피크 시간엔 *20 개 모두 사용* 중. 한가한 시간이 되면 *15 개가 idle*. *10 분간 안 쓰이면 *닫는다*. *최소 5 개* 까지 줄어들고 *그 아래로는 *안 닫는다*.

### 4.2 *왜 *full 유지* 가 권장인가 — minimum-idle = maximum-pool-size*

HikariCP 의 공식 권장은 *minimum-idle 을 *maximum-pool-size 와 같게* 두는 것*.

이유 :

- *Connection 생성 자체가 비싸다* (TCP handshake + TLS + DB 인증 + 권한 체크). *수십 ~ 수백 ms*
- *피크 트래픽 이 갑자기 들어왔을 때* *5 → 20 으로 *늘리는 시간* 동안* *기존 5 개가 *과부하* 받고 *p99 가 *튄다*
- *fixed-size pool* 이 *predictable*. *resource budgeting 도 쉽다*

```yaml
hikari:
  maximum-pool-size: 20
  minimum-idle: 20         # ← 권장
```

### 4.3 *idleTimeout 이 무력화되는 케이스*

위처럼 *minimum-idle = maximum-pool-size* 이면 *idleTimeout 이 *작동 안 함* (절대 idle 로 안 줄어들기 때문에). *그게 정상* — Brett Wooldridge 의 *의도된 *부작용 없는 권장*.

---

## 5. *maxLifetime* — *connection 의 *절대 최대 수명**

> *Connection 이 *얼마나 오래 살았으면 *교체할지** 의 시간

### 5.1 *기본값 30 분 의 *진짜 이유**

DB 측이 *오래된 connection 을 *조용히 끊는다*. 예 :

- *MySQL `wait_timeout` 기본 8 시간* — *그 시간 후 *MySQL 측이 *연결을 끊는다*
- *PostgreSQL `idle_in_transaction_session_timeout`* — *idle in transaction 의 *세션 강제 종료*
- *AWS RDS Proxy* — *24 시간 후 *재연결*
- *방화벽 / NAT* — *idle 5 ~ 30 분* 후 *세션 stale*

*Application 측은 그걸 *모른다*. Pool 에 *살아있다고 *생각* 하는 connection 을 *가져가서 쓰는 순간* `Connection reset by peer` 또는 `Communications link failure`. *p99 가 *튀고 *5xx 가 *발생*.

해결 : *maxLifetime 을 *DB 측 timeout 보다 *명시적으로 짧게* 잡는다*.

```yaml
hikari:
  max-lifetime: 1800000  # 30min
```

*30 분 사용 후 *Hikari 가 *스스로 close + 재생성*. *DB 가 끊기 전에 *우리가 *먼저 끊는다*. *조용한 stale connection* 가 *생기지 않는다*.

### 5.2 *DB 측 설정 과 *맞춰야 할 비율*

```
maxLifetime  <  (DB 측 idle timeout 의 *70~80%*)
```

예 :
- MySQL `wait_timeout = 600s (10분)` 이면 → `maxLifetime = 420s ~ 480s` (7~8분)
- PostgreSQL `idle_in_transaction_session_timeout = 1800s (30분)` 이면 → `maxLifetime = 1500s` (25분)

*반대로 *maxLifetime 이 *DB timeout 보다 길면* *영구적인 *stale connection* 사고*. *흔한 *실수**.

### 5.3 *AWS RDS Proxy / Cloud SQL 의 *주의**

*RDS Proxy* 는 *connection 다중화 (multiplexing)* 후 *기존 connection 에 *24시간 limit*. *Hikari 의 maxLifetime 을 *그것보다 짧게* 잡아야 *예기치 못한 *세션 종료* 가 안 생긴다.

---

## 6. *validationTimeout + connectionTestQuery* — *살았는지 *체크하는 시간**

> *Connection 을 *pool 에서 *꺼낼 때* *살았는지 체크하는 *최대 시간**

### 6.1 *Pool 의 connection 이 *진짜 살았는지* 모른다*

`borrowConnection()` 호출 시 *Hikari 가 자동으로 *살아있는지 체크*. 기본은 *JDBC 4.0 의 `Connection.isValid()` 메서드* — *DB 에 *ping 같은 *짧은 round-trip*.

validationTimeout 은 그 *체크의 *max wait*. 기본 5s.

### 6.2 *connectionTestQuery 의 *legacy 옵션**

JDBC 4 이전 드라이버 (옛 DB / 일부 임베디드) 는 `isValid()` 가 *지원 안 됨*. 그 경우 :

```yaml
hikari:
  connection-test-query: "SELECT 1"
```

*매 borrow 마다 *SELECT 1* 실행*. 정상 driver 에선 *불필요한 비용*. JDBC 4 이상이면 *비워두는 게* 권장.

### 6.3 *Keepalive — 안 쓰이는 connection 의 *주기적 *살아있음 체크**

```yaml
hikari:
  keepalive-time: 300000  # 5min
```

*5 분마다 *pool 의 idle connection 들에 *살아있음 확인*. *NAT / 방화벽이 *idle session 을 *조용히 끊는* 환경에서 필수*. AWS RDS / Cloud SQL 환경에서 *권장*.

기본은 *비활성 (0)*. *enable 안 하면 *idle connection 이 *stale* 되어도 *알 수 없음*.

---

## 7. *5 개 설정의 *상호 작용 — *시간 사슬***

5 가지 시간을 한 그림으로 :

```
[connection 생성] ─── connectionTimeout ─── [borrow 성공]
   ↓
[query 실행]
   ↓
[return to pool]
   ↓
... idle ...
   ↓
keepalive-time 마다 살아있음 체크
   ↓
... idle 이 idleTimeout 넘으면 close (minimum-idle 초과분만) ...
   ↓
... maxLifetime 넘으면 *무조건* close + 새 connection ...
   ↓
[다음 borrow]
   ↓
borrow 시점 validationTimeout 안에 살아있음 확인
   ↓
[query 실행]
```

*어느 한 단계 *시간 설정 이 *DB 측과 *어긋나면* *전체 사슬이 *조용히 깨진다***.

---

## 8. *진단 — *내 Pool 이 *지금 어떤 상태**

### 8.1 *Micrometer 메트릭 (Spring Boot 자동 노출)*

```
hikaricp.connections                      # 총 connection 수
hikaricp.connections.active               # 사용 중
hikaricp.connections.idle                 # 유휴
hikaricp.connections.pending              # 대기 중 (← 이게 증가하면 *경고*)
hikaricp.connections.acquire              # 가져오는 데 걸린 시간 (Timer)
hikaricp.connections.timeout              # timeout 발생 횟수
hikaricp.connections.creation             # 생성 횟수 (높으면 *stale 발생 의심*)
hikaricp.connections.usage                # 사용 시간 분포
```

Grafana 에 *active / idle / pending* 을 *같은 패널* 에 띄우면 *지금 pool 상태* 가 *한눈에*. *pending > 0* 이 *지속적으로 발생* 하면 *pool 부족*.

### 8.2 *Leak Detection*

```yaml
hikari:
  leak-detection-threshold: 60000  # 60s — connection 60초 점유 시 stacktrace 로그
```

*Connection 을 *가져갔는데 *60 초 안에 *return 안 한 경우* *thread stacktrace 를 log 에 남긴다*. *코드 어디서 connection 누수가 있는지* 잡는 *핵심 도구*.

운영에선 *60s 정도* 권장. *5~10 초로 너무 짧게 하면* *legitimate slow query* 가 *오탐* 발생.

### 8.3 *Slow query log 와 *함께 *교차 분석**

```
[14:23:01] HikariPool: pending=8 active=20 idle=0  ← pool 부족
[14:23:01] PostgreSQL slow query: SELECT ... 3.2s ← 그 시점 slow query
```

*같은 시각의 *Hikari pending* 과 *DB slow query* 가 *둘 다 튀면* *원인은 DB query — Hikari 는 *증상**.

*Pending 만 튀고 DB 가 멀쩡하면* *원인은 *코드 안의 *connection 누수** — *leak detection* 으로 *해당 코드 위치* 추적.

---

## 9. *실무 권장 값 — *환경별*

### 9.1 *온프레미스 PostgreSQL / MySQL (안정적 네트워크)*

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      minimum-idle: 20            # full 유지
      connection-timeout: 3000    # 3s — 빠른 fail
      idle-timeout: 0             # min=max 면 무의미
      max-lifetime: 1500000       # 25min (DB wait_timeout < 30min 가정)
      validation-timeout: 3000    # 3s
      keepalive-time: 0           # 안정 네트워크면 비활성
      leak-detection-threshold: 60000  # 60s
```

### 9.2 *AWS RDS / Cloud SQL + Proxy*

```yaml
hikari:
  maximum-pool-size: 30
  minimum-idle: 30
  connection-timeout: 5000        # 5s (proxy 가 약간 추가 latency)
  max-lifetime: 1200000           # 20min (Proxy 의 24h 한참 전)
  keepalive-time: 300000          # 5min — NAT / VPC 환경 필수
  leak-detection-threshold: 60000
```

### 9.3 *K8s 환경 (cgroup CPU limit 적용)*

```yaml
hikari:
  maximum-pool-size: 15           # cgroup CPU 2 core 기준
  minimum-idle: 15
  connection-timeout: 3000
  max-lifetime: 1500000
  keepalive-time: 300000
  leak-detection-threshold: 60000
```

*pool size 가 *cgroup CPU * 2 + spindle* 의 공식보다 *작아야 *cgroup throttling* 회피*.

---

## 10. *흔한 함정 5 가지*

### 10.1 *pool size 를 *무한정 키우는 *반사적 반응**

*"느려? pool 키워."* — *잘못된 반사*. *DB 가 *처리할 수 있는 *진짜 동시성* 은 *DB CPU + I/O 의 *함수*. *그 이상 늘리면 *DB lock contention 만 *늘어남*. *체감 *역효과*.

### 10.2 *connection-timeout 30 초 *그대로*

*기본값을 *바꾸지 않은 채 *운영* 하면 *p99 가 *30 초로 *튀는 *조용한 사고*. 짧게 (3~5s) 잡고 *명시적 503* 으로 *backpressure 전달* 이 정답.

### 10.3 *maxLifetime 미설정 → DB 측 timeout 충돌*

*8 시간 후 *MySQL 이 끊은 connection 을 *Hikari 가 *모른 채 *재사용 시도* → *Communications link failure*. *주말 트래픽 낮은 *월요일 아침* 에 *우연히 *재현되는 *유명한 사고*.

### 10.4 *connection-test-query: SELECT 1 *를 *수동으로 깔아둠**

JDBC 4 driver 에서 *불필요*. 매 borrow 마다 *DB round-trip 1 회 추가* — *수십 ms 비용*. *제거* 권장.

### 10.5 *Transaction 안에서 *외부 HTTP 호출**

*가장 위험한 패턴*. `@Transactional` 안에서 외부 HTTP API 호출 (예: 결제 게이트웨이) :

- HTTP 호출 *5 초* 동안 *connection 이 *점유* 됨
- 동시 요청이 *pool size 만큼* 들어오면 *전체 *pool *점유*
- *모든 요청이 *5 초 대기*. *p99 = 5 초*

해결 : *@Transactional 밖에서 *외부 호출*. *DB 작업 끝낸 후 *outbox 패턴* 으로 *비동기 publish*.

---

## 11. *교훈 — *시간 사슬 전체를 보는 시야**

> *"DB 가 느리다는 진단의 *80% 는 *pool 의 *시간 설정 또는 *코드 안의 *connection 점유 패턴* 의 문제다. *연결 자체가 *진짜 느린 경우* 는 *나머지 20%* 다."*

*5 가지 시간 설정 (connectionTimeout / idleTimeout / maxLifetime / validationTimeout / keepaliveTime)* + *DB 측 *세션 timeout* + *코드의 *connection 점유 패턴* + *Bulkhead (thread pool 분리)* 의 *모든 것이 *맞물려* 야 *제대로 작동 하는 시스템 이 된다*.

*어느 한 값* 을 *바꾸기 전* 에 — *그 값이 다른 *6 개 설정과 *어떻게 만나는지* 를 *항상 *함께 생각하자**. 그게 *DB connection 의 *진짜 시야**.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · *HikariCP 의 *5 시간 설정* (현재 글)*

*이 글은 sparta-msa-project / settlement / order-oms 의 운영 경험을 기반으로 작성. HikariCP 의 [공식 README](https://github.com/brettwooldridge/HikariCP) + Brett Wooldridge 의 GitHub Issue 답변 + [Spring Boot Auto-configuration docs](https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/#data.sql.datasource.connection-pool) 참고.*
