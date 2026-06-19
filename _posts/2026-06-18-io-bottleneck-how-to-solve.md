---
layout: post
title: "*I/O 병목* 어떻게 *해결* 하지? — *디스크 / 네트워크 / DB* 의 *공통 패턴* 과 *층별 처방*"
date: 2026-06-18 23:30:00 +0900
categories: [performance, backend, infrastructure]
tags: [io-bottleneck, async-io, nio, io-uring, connection-pool, batching, caching, n-plus-1, hikari, jvm, postgres, kafka, performance-tuning]
---

> *"코드 는 *맞는데* *느리다*"* — *백엔드 가 *느린 *원인 의 *90%* 는 *연산 이 *아니라 *I/O* 다.
>
> *디스크* 읽기 *80 μs*. *DB 쿼리* 한 번 *5 ms*. *HTTP 외부 호출* 한 번 *50 ms*. *CPU 가 *0.25 ns* 안에 한 사이클을 도는 *4 GHz* 시대 에 *I/O 한 번* 은 *수십만 ~ 수억 사이클* 을 *기다리는 일* 이다.
>
> 그런데 *I/O 병목* 은 *CPU 처럼 *한 가지 자원* 이 *아니다*. *디스크 / 네트워크 / 데이터베이스 / 파일시스템 / 메모리 매핑* — *서로 다른 *물리적 자원* 이 *서로 다른 *방식으로 *터지고*, *해결책* 도 *각자 *다르다*.
>
> 이 글은 *I/O 병목 의 *6 가지 패턴* 을 *진단 → 원인 → 처방* 으로 정리하고, *Spring Boot / JVM* 워크로드 에서 *실제로 손이 가는 *해결책* 을 *층별* 로 분해한다.

내 *이전 글* [*CPU 의 *L1 / L2 / L3 캐시* — *메모리 벽* 과 *병목 구간* 에 대한 *고찰*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) 의 *후속 자매편*. *CPU 가 *기다리는 시간* 의 *대부분* 이 *메모리* 라면, *애플리케이션 이 *기다리는 시간* 의 *대부분* 은 *I/O*.

---

## TL;DR — *한 줄 결론*

> *I/O 병목* 은 *6 가지 패턴* 으로 *대부분 분류* 된다 : *동기 직렬화* / *N+1 쿼리* / *커넥션 풀 고갈* / *작은 랜덤 I/O* / *대역폭 포화* / *chatty network*. *각각의 처방* 은 *다르다* — *async / batch / pool 튜닝 / sequential 화 / streaming / 캐시 / CDN*. *가장 흔한 실수* 는 *원인 진단 없이 *"비동기 로 바꾸자"* 라고 결정하는 것 — *동기 직렬화 가 *아닌 *대역폭 포화* 라면 *async 는 *아무 효과 가 없다*. *측정 → 분류 → 처방* 순서 가 *전부* 다.

---

## 1. *I/O 병목 의 *물리학* — *왜 *그렇게 느린가*

### 1.1 *지연 시간 의 *층별 *체급*

| 자원 | 일반 latency | 4 GHz CPU 사이클 환산 | L1 cache 대비 |
|---|---|---|---|
| L1 cache | ~1 ns | ~4 사이클 | 1x |
| DRAM | ~80 ns | ~320 사이클 | 80x |
| **NVMe SSD (랜덤 4K read)** | **~80 μs** | **~320,000 사이클** | **80,000x** |
| **SATA SSD (랜덤 4K read)** | **~150 μs** | **~600,000 사이클** | **150,000x** |
| **회전 HDD (랜덤 read)** | **~10 ms** | **~40,000,000 사이클** | **10,000,000x** |
| **로컬 DB 쿼리 (PK lookup)** | **~1~5 ms** | **~4~20M 사이클** | **1M~5M x** |
| **DC 내부 RTT** | **~0.5 ms** | **~2M 사이클** | **500,000x** |
| **인터넷 RTT (서울↔도쿄)** | **~30 ms** | **~120M 사이클** | **30M x** |
| **인터넷 RTT (서울↔미국 동부)** | **~180 ms** | **~720M 사이클** | **180M x** |

> *CPU 가 *L1 hit 으로 *1 초 에 *2.5억 회 연산* 할 동안, *디스크 1 회 IO* 는 *그 1 초 의 *0.000008%* 만에도 *끝나지 않는다*.

### 1.2 *왜 *async 가 *공짜 가 *아닌가*

흔한 오해 :

> *"동기 가 *느리니까 *비동기 로 바꾸면 *빨라진다"*.

**아니다**. *async 가 해결하는 것* 은 *"대기 중인 *스레드* 가 *놀고 있는 시간"* 이다. *물리적 자원 의 *대역폭* 이 *부족 하면 *async 든 sync 든 *똑같이 *대기* 한다.

```text
시나리오 A : 10 개 외부 API 호출, 각 50 ms, 자원 충분
  동기 직렬 : 10 × 50 ms = 500 ms
  병렬 (async / thread pool) : ~50 ms        ← async 가 효과적 ★

시나리오 B : 100K rows DB insert, 단일 connection
  동기 : 5 분
  async : 5 분 (DB IO 가 *bottleneck* — async 무관)   ← async 무효 ★

시나리오 C : 디스크 100% util 상태에서 read 추가
  동기 : 느림
  async : 똑같이 느림 — 자원 그 자체 가 *포화*       ← async 무효 ★
```

→ *async 는 *동기 직렬화 *문제만 *해결*. *대역폭 포화* 는 *async 가 *못 푼다*. *진단 부터 *분리* 해야 한다.

---

## 2. *진단 — *어디서 *터지고 있는가*

> *측정 없이 *추측하면* *틀린 자원* 에 *시간을 *쓴다*.

### 2.1 *시스템 레벨 — *어느 자원 인가*

```bash
# CPU vs I/O — top 의 %wa (iowait) 가 핵심
top -1
# %Cpu(s):  10.2 us,  5.0 sy, 60.0 wa  ← 60% iowait → 디스크 병목 강력 의심
#                                 ↑
#                            여기 가 핵심

# 디스크 — iostat 1
iostat -xz 1
# Device  r/s  w/s  %util  await  svctm  aqu-sz
# nvme0n1  500    50  95%    8.0    1.5    4.0    ← util 95% = 포화
#                          ↑ ↑                  ↑
#                          평균 응답시간      큐 깊이

# 네트워크
sar -n DEV 1
# iface   rxpck/s  txpck/s   rxkB/s   txkB/s
# eth0      5000    4500   8200      7800

# 파일 디스크립터 / 소켓
ss -s              # 소켓 상태 요약 (TIME_WAIT 폭증?)
ss -tan | wc -l    # 총 TCP 연결 수
lsof -p <pid> | wc -l   # 프로세스 별 FD 수
```

### 2.2 *애플리케이션 레벨 — *어느 코드 인가*

**JVM** :
```bash
# async-profiler — 가장 추천. wall-clock + lock + I/O 가 같이 보임
java -jar app.jar &
PID=$!
asprof -e wall -d 30 -f profile.html $PID

# wall-clock profile 에서 *I/O 대기* 가 *얼마인지* 보임
# (CPU profile 만 보면 I/O wait 가 안 보인다!)
```

**DB** :
```sql
-- PostgreSQL 어떤 쿼리가 느린가
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 20;

-- 락 / 대기 상태
SELECT pid, wait_event_type, wait_event, state, query
FROM pg_stat_activity
WHERE wait_event IS NOT NULL;
```

**HTTP / gRPC** :
- *분산 트레이싱* (OpenTelemetry, Zipkin) — *어느 span 이 *몇 ms* 인가.
- *Micrometer 메트릭* — `http.client.requests` `db.queries` `cache.gets` p50/p95/p99.

### 2.3 *4 가지 *식별 신호* — *원인 분리*

| 신호 | 가능한 원인 |
|---|---|
| `%iowait` 높고 *디스크 util 100%* | 디스크 포화 — *작은 random I/O* 또는 *대역폭 포화* |
| `%iowait` 낮은데 *p99 latency 높음* | *동기 외부 호출 직렬화*, *N+1 쿼리* |
| *connection pool 대기* (HikariPool 로그) | *커넥션 풀 고갈* 또는 *long-running tx* |
| *thread pool full*, *active threads 폭증* | *외부 호출 동기 직렬화*, *backpressure 부재* |

→ *어느 신호 인가* 를 *먼저 *분리* 하면 *처방 이 *자동으로 좁혀진다*.

---

## 3. *패턴 1 — 동기 직렬화* (*N 회 외부 호출 을 *한 줄 *씩* )

### 3.1 *증상*

```java
// 안티패턴 — 5 개 외부 API 호출 을 *순차* 로
List<UserProfile> profiles = userIds.stream()
    .map(id -> restClient.get("/users/" + id))  // 각 50 ms
    .toList();
// 5 회 × 50 ms = 250 ms (대부분 *대기* 중)
```

→ *5 개 호출 의 *대기 시간* 이 *전부 *직렬*. *CPU 는 *놀고 있고* *스레드 는 *기다리고만 있다*.

### 3.2 *처방 — *병렬화 + 비동기*

**JDK 21 가상 스레드** (Spring Boot 3.2+ 기본 지원) :
```java
// 가상 스레드 + parallelStream — 가장 단순
List<UserProfile> profiles = userIds.parallelStream()
    .map(id -> restClient.get("/users/" + id))
    .toList();
// 5 개 가상 스레드 가 *동시* 대기 → 총 ~50 ms
```

**Reactor / WebFlux** :
```java
Flux.fromIterable(userIds)
    .flatMap(id -> webClient.get().uri("/users/{id}", id).retrieve().bodyToMono(UserProfile.class), 32)
    .collectList()
    .block();
```

**CompletableFuture + 명시적 풀** :
```java
ExecutorService pool = Executors.newFixedThreadPool(32);
List<CompletableFuture<UserProfile>> futures = userIds.stream()
    .map(id -> CompletableFuture.supplyAsync(() -> restClient.get("/users/" + id), pool))
    .toList();
List<UserProfile> profiles = futures.stream().map(CompletableFuture::join).toList();
```

### 3.3 *주의* — *병렬화 의 *상한*

- *외부 API 의 *rate limit* — 1000 RPS 라면 *동시 호출* 도 *그 안* 으로 *제한*.
- *상대 서버* 의 *DDoS 보호* — 갑작스러운 *N 배 부하* 가 *상대 서버를 *터뜨릴 수 있다*.
- *Semaphore* 또는 *rate limiter* (Resilience4j) 로 *동시성 상한* 을 *명시*.

---

## 4. *패턴 2 — N+1 쿼리* (*ORM 의 *가장 흔한 함정*)

### 4.1 *증상*

```java
// 외부적으론 한 줄 — 내부적으로 *N+1 회 DB 호출*
List<Order> orders = orderRepo.findAll();   // 1 회 쿼리
for (Order o : orders) {
    log.info("user = {}", o.getUser().getName());   // 각 Order 마다 *1 회 lazy load*
}
// 1000 개 order → 1001 회 DB 호출
```

*증거* — `pg_stat_statements` 에 *같은 쿼리 가 *수천 번 호출* 됨.

### 4.2 *처방 — *Fetch 전략*

**Spring Data JPA `@EntityGraph`** :
```java
@EntityGraph(attributePaths = {"user", "items"})
List<Order> findAll();
// 한 번의 join 쿼리로 *모두 가져옴*
```

**JPQL `JOIN FETCH`** :
```java
@Query("SELECT o FROM Order o JOIN FETCH o.user JOIN FETCH o.items WHERE o.id IN :ids")
List<Order> findWithUserAndItems(@Param("ids") List<Long> ids);
```

**Batch fetch** — *연관 컬렉션 이 *너무 크면 *카르테시안 폭발* 위험. *그럴 때* :
```yaml
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 100   # IN (?, ?, ?, ...) 100 개씩 묶어서 한 번
```

→ *N+1 → N/100 + 1* 로 *축소*.

### 4.3 *진단 자동화*

```yaml
# 개발 환경 — 쿼리 로깅 + count
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE

# Hypersistence Utils 의 SQLStatementCountValidator 로 *테스트 에서 강제*
@Test
void getOrders_쿼리_3회_이하() {
    SQLStatementCountValidator.reset();
    orderService.getOrders();
    SQLStatementCountValidator.assertSelectCount(3);
}
```

→ *N+1 은 *코드 리뷰* 가 아니라 *테스트* 가 *잡아야* *재발* 안 한다.

---

## 5. *패턴 3 — 커넥션 풀 고갈* (*HikariPool 의 *조용한 살인자*)

### 5.1 *증상*

```text
ERROR  com.zaxxer.hikari.pool.HikariPool : HikariPool-1 - Connection is not available, request timed out after 30000ms.
```

또는 *p99 latency 가 *갑자기 *30 초* 로 *치솟음*.

### 5.2 *원인 후보 (3 가지)*

1. *풀 크기 부족* — `maximumPoolSize` 가 *동시 요청 수* 보다 작음.
2. *Long-running transaction* — 누군가 *트랜잭션 안에서 *외부 API 호출* 또는 *큰 계산*. 그 동안 *그 연결은 *반환되지 않음*.
3. *connection leak* — 코드에서 *try-with-resources* 없이 *명시적으로 close 안 함*.

### 5.3 *처방*

**1. 풀 크기 — 작게 시작, 측정 후 조정** :

> *큰 풀이 *항상 좋은 것은 *아니다*. *DB 서버* 자체 가 *상한* 이다.

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20          # PostgreSQL max_connections / 앱 인스턴스 수 보다 *작게*
      minimum-idle: 5
      connection-timeout: 3000       # 30s 기본은 *너무 길다* — 빨리 fail 하게
      leak-detection-threshold: 5000 # 5s 동안 안 돌려주면 *경고 로그*
```

> PostgreSQL `max_connections=100` 인데 *앱 인스턴스 5 개* 가 *각자 풀 30* 이면 *총 150 > 100* — *DB 가 *추가 연결 거부*. 인스턴스 수 × 풀 크기 ≤ DB max_connections 의 80% 가 *안전선*.

**2. 트랜잭션 안에서 외부 호출 금지** :

```java
// 안티 패턴
@Transactional
public void process(Long orderId) {
    Order o = repo.findById(orderId);
    externalApi.notify(o);   // ← 50 ms — 그 동안 *DB 연결 잡고 있음*
    o.setStatus("DONE");
}

// 올바름 — 외부 호출 *밖으로 빼기*
public void process(Long orderId) {
    Order o = txTemplate.execute(s -> repo.findById(orderId));
    externalApi.notify(o);   // ← 외부 호출 시 *DB 연결 안 잡고 있음*
    txTemplate.execute(s -> {
        Order fresh = repo.findById(orderId);
        fresh.setStatus("DONE");
        return null;
    });
}
```

또는 *Saga* / *Outbox* 패턴 으로 *트랜잭션 경계를 *명시적으로 *짧게* 유지.

**3. Leak detection 활성화** :

```yaml
spring:
  datasource:
    hikari:
      leak-detection-threshold: 5000  # 5초 → *스택 트레이스* 와 함께 경고 로그
```

→ *어디서 *반환 안 한 *코드* 가 *있는지* *명시* 됨.

---

## 6. *패턴 4 — 작은 랜덤 I/O* (*디스크 의 *공포*)

### 6.1 *증상*

`iostat -x 1` 에서 :
```text
Device   r/s    w/s    rkB/s   wkB/s   await   %util
nvme0n1  5000   100    20000   400      4.0    95%
                      ↑                ↑       ↑
                  4KB ÷ 5000 = 4KB 평균     포화
```

> *IOPS 가 *높은데* *대역폭 (MB/s) 은 *낮다* → *작은 랜덤 I/O 가 *디스크를 *포화* 시키고 있음.

### 6.2 *원인 패턴*

- *fsync 빈도 가 높다* — 트랜잭션 마다 강제 fsync (Postgres `synchronous_commit=on`).
- *작은 파일 *수천 개* 를 *각각 read*.
- *append-only log* 가 *각 line 마다 *write+flush*.

### 6.3 *처방*

**1. Sequential 화 — *Group commit / batching*** :

```sql
-- PostgreSQL : 1000 row insert
-- 안티
INSERT INTO orders (...) VALUES (...);   -- 1000 회
COMMIT;                                   -- 1000 회 fsync

-- 좋음
INSERT INTO orders (...) VALUES (...), (...), (...), ...;  -- 1회 multi-row
COMMIT;                                                     -- 1회 fsync
```

JDBC 배치 :
```java
try (PreparedStatement ps = conn.prepareStatement(sql)) {
    for (Order o : orders) {
        ps.setLong(1, o.getId());
        ps.setString(2, o.getName());
        ps.addBatch();
        if (i++ % 1000 == 0) ps.executeBatch();
    }
    ps.executeBatch();
}
// 데이터 1000개 → DB 왕복 1회, fsync 1회
```

**2. 비동기 flush** :

```yaml
# Postgres : 약간의 데이터 손실 위험 vs 처리량 (replica 있는 환경에서)
synchronous_commit = off            # fsync 안 기다림 → 처리량 10x
# 또는
synchronous_commit = remote_apply   # 동기 replication 으로 영속 보장 — 디스크 fsync 는 비동기
```

**3. 디스크 자체 교체** :

| 디스크 | 4K random read IOPS | 4K random write IOPS |
|---|---|---|
| 7200 RPM HDD | ~100 | ~100 |
| SATA SSD | ~80,000 | ~30,000 |
| NVMe Gen3 | ~500,000 | ~200,000 |
| NVMe Gen4 | ~1,000,000 | ~500,000 |
| **Intel Optane (DC P5800X)** | **~1,500,000** | **~1,500,000** |

→ *etcd / PostgreSQL WAL / Kafka log* 처럼 *작은 fsync 가 자주 발생* 하는 워크로드 는 *Optane / 좋은 NVMe* 로 *체급 차이* 만큼 즉시 빨라진다.

(*나도 *솔로몬 노드 의 *etcd 디스크* 를 *Intel DC S3700 SSD* 로 *이전* 한 후 *p99 latency 가 *극적으로 개선* 되는 것을 본 경험.)

---

## 7. *패턴 5 — 대역폭 포화* (*async 가 *못 푸는 영역*)

### 7.1 *증상*

```text
sar -n DEV 1
iface  rxkB/s   txkB/s
eth0   118000   116000     ← 1 Gbps NIC 의 ~95% 포화 (실효 ~118 MB/s)
```

또는 *디스크 throughput 이 *제조사 spec 의 80%+* 에 *고정*.

> *자원 자체 가 *물리적으로 포화* — 더 빨리 도는 *방법 이 *없다*.

### 7.2 *처방 — *전송량 자체 를 줄이기*

**1. Compression** :
- HTTP : `Content-Encoding: gzip / br / zstd` — *5~10 배 감소* (텍스트), *1.5~3 배* (이미 압축된 이미지 빼고).
- gRPC : `grpc.default_compression_algorithm=gzip`.
- Kafka : `compression.type=zstd` (lz4 보다 비율 좋음, snappy 보다 CPU 적게).

**2. Payload 축소** :
- 필요 없는 필드 *제거* (`fields` 파라미터 또는 GraphQL).
- *Pagination* — `LIMIT` 없이 *모두 보내지 않기*.
- *Avro / Protobuf* — JSON 대비 *3~5 배 압축*.

**3. CDN — *데이터를 *사용자 근처로*** :

- Cloudflare / CloudFront / Fastly — *정적 자원* 은 *origin 까지 안 옴*.
- *origin offload* 50~95% → *대역폭 사용량 자체 가 *감소*.
- *지리적 latency* 도 함께 해결 (서울 사용자 → 서울 edge).

**4. 인프라 업그레이드** :
- 1 Gbps → 10 Gbps NIC.
- *NVMe Gen3 → Gen4* (sequential 대역폭 2 배).
- *DDR4 → DDR5* (메모리 대역폭 1.5~2 배 — 메모리-bound 워크로드).

---

## 8. *패턴 6 — Chatty Network* (*여러 작은 요청 의 *지옥*)

### 8.1 *증상*

- 한 페이지 로딩 에 *50+ API 호출*.
- 각 호출 *RTT 10 ms* — *총 wall-clock 500 ms* (병렬 해도 *최소 RTT 1 회*).
- *fan-out * 마이크로서비스 에서 *흔함*.

### 8.2 *처방*

**1. *API gateway / BFF 패턴*** — *클라이언트 가 *1 회* 만 호출, *서버 가 *내부 aggregation*. 내부 호출은 *LAN RTT (0.5 ms)* — *인터넷 RTT (30 ms) 의 1/60*.

**2. *GraphQL / TRPC*** — *클라이언트 가 *원하는 필드* 를 *한 번* 에 *기술*. *서버 가 *batch + dataloader* 로 *N+1 자동 해소*.

**3. *HTTP/2 multiplexing*** — *한 TCP 연결* 위에 *N 개 요청* 동시. *connection setup 비용* 제거.

**4. *Keep-Alive + Connection pooling*** — *매 요청 마다 *TCP 3-way handshake* 하지 않기. *Apache HttpClient*, *OkHttp*, *Spring WebClient* 모두 *기본* 으로 제공 — *연결 풀 크기* 만 *조정*.

```java
WebClient client = WebClient.builder()
    .clientConnector(new ReactorClientHttpConnector(
        HttpClient.create(ConnectionProvider.builder("pool")
            .maxConnections(200)
            .pendingAcquireTimeout(Duration.ofSeconds(3))
            .build())
    ))
    .build();
```

**5. *Batch API 설계*** — *외부 API 와 협의* 해서 *N 개를 한 번에 받는 endpoint* 추가. `/users?ids=1,2,3,4,5` 형식. *5 회 호출 → 1 회 호출* — *5 배 효과*.

---

## 9. *층별 처방 정리 — *어디서 *무엇 을 *고치나*

### 9.1 *애플리케이션 레벨*

- *batching* (insert / API / Kafka producer).
- *async/concurrent* (가상 스레드, WebFlux, CompletableFuture).
- *fetch 전략* (`@EntityGraph`, `JOIN FETCH`, batch size).
- *connection pool 튜닝* (HikariCP, WebClient connector).
- *circuit breaker / timeout / retry* (Resilience4j) — *상대 서버 가 죽으면 *내가 대신 죽지 않게*.

### 9.2 *캐싱 레벨*

> *I/O 안 하기* 가 *최고의 I/O 최적화* 다.

- *로컬 캐시* (Caffeine) — *프로세스 내, ~ns 단위*.
- *분산 캐시* (Redis) — *수 ms*, *프로세스 간 공유*.
- *DB query result cache* — Hibernate L2 cache, *조건 부 사용* (invalidate 어려움).
- *HTTP cache headers* (`Cache-Control`, `ETag`).
- *CDN* — *edge 에서 origin 보호*.

### 9.3 *데이터베이스 레벨*

- *인덱스* — *full scan 을 *index scan* 으로 (10000 배 차이 흔함).
- *partitioning* — *큰 테이블 을 *조각* 으로 (월별 / 해시별).
- *read replica* — *읽기 부하 분산*.
- *connection pooler* (PgBouncer) — *앱 다중 인스턴스* 가 *DB 연결을 *집약*.
- *vacuum / analyze* — *통계 갱신*, *bloat 제거*.

### 9.4 *인프라 레벨*

- *디스크 업그레이드* (Optane / NVMe Gen4).
- *NIC 업그레이드* (1G → 10G / 25G).
- *NUMA 친화 배치* (이전 글 [*CPU 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) 참조).
- *kernel tuning* — `vm.dirty_ratio`, `net.core.somaxconn`, `fs.file-max`.

### 9.5 *OS / Kernel 레벨* — *고급 / 특수 케이스*

- **io_uring** (Linux 5.1+) — *async I/O 의 *진정한 미래*. *epoll + AIO* 보다 *시스템콜 횟수 ↓*, *zero-copy 친화*. PostgreSQL 17, Nginx 등이 도입 중. JVM 은 *Netty io_uring* 으로 *제한적 활용*.
- **mmap (Memory-mapped file)** — *큰 파일 의 *page cache 직접 접근*. *Kafka 가 사용* 하는 핵심 패턴.
- **sendfile / splice** — *user space 거치지 않고 *kernel 안에서 *바로 전송*. *Nginx static 서빙* 이 *zero-copy*.
- **Direct I/O (O_DIRECT)** — *page cache 우회*. DB / 스토리지 엔진이 *자체 캐시 가 더 잘 됐을 때* 사용.

---

## 10. *현장 의 *전형적 *디버깅 흐름*

> *"왜 *p99 latency 가 *3 초 인가요?"* 라는 질문을 받았을 때 *내가 따르는 순서*.

```text
1. *어디서* 느린가 — 분산 트레이싱 / Micrometer / async-profiler wall-clock
   ├ 외부 API ?    → 패턴 1 (동기 직렬화) 또는 패턴 5/6
   ├ DB 쿼리 ?     → 패턴 2 (N+1) 또는 슬로우 쿼리 또는 패턴 3 (풀 고갈)
   ├ 디스크 I/O ?  → 패턴 4 (작은 랜덤) 또는 패턴 5 (대역폭)
   └ CPU ?         → I/O 가 아님 (이전 글 참조)

2. *어느 자원* 이 포화 인가 — top %wa / iostat / sar / ss
   ├ %wa 60%+        → 디스크
   ├ NIC saturation  → 네트워크 대역폭
   ├ Hikari 대기 폭증  → DB 연결 풀
   └ active threads 폭증 → app thread pool

3. *처방* 선택 — 위 6 가지 패턴 중 *해당 분류 만* 적용

4. *측정* — 같은 워크로드 로 *재현* 후 *전후 비교*

5. *백서* (postmortem / ADR) — *왜* 그 처방이 *효과 가 있었는지* 기록
```

---

## 11. *백엔드 개발자 의 *I/O 체크리스트*

낮은 레벨 까지 가지 않아도 *알면 *바로 적용* 가능한 *체크* :

1. *외부 API 호출 직렬화* 안 하고 있나 (`stream` 안 의 *순차 map*).
2. *N+1 쿼리* 가 *테스트 로 *검증* 되는가 (SQLStatementCountValidator).
3. *Hikari leak detection* 활성화 되어 있는가.
4. *@Transactional 안* 에서 *외부 호출* 또는 *큰 계산* 없는가.
5. *Bulk insert* / *Kafka batch* 가 *건당* 이 아니라 *묶어서* 보내는가.
6. *Connection pool size × instance count* 가 *DB max_connections* 보다 *작은가*.
7. *HTTP 응답 compression* (gzip / br) 활성화 되어 있는가.
8. *CDN* 으로 *정적 자원 offload* 되어 있는가.
9. *Caffeine + TTL* 또는 *Redis* 가 *읽기 hot path* 에 적용 되어 있는가.
10. *분산 트레이싱* 으로 *어디서 *몇 ms* 인지* *실시간 가시화* 되어 있는가.

---

## 12. *결론 — *측정 없는 *처방 은 *추측*

> *I/O 병목 의 *6 가지 패턴* 은 *각자 *다른 원인* 과 *다른 처방* 을 가진다.

가장 흔한 *실패 패턴* 은 *"느리다 → async 로 바꿔보자"* 처럼 *진단 없이 *처방 부터 *집는 것*. *대역폭 포화* 에 *async 를 적용* 하면 *0 효과 + 코드 복잡도 증가* 라는 *최악의 결과* 다.

> *측정 → 분류 (6 가지 중 어느 것인가) → 처방 → 재측정* — *이 순서를 *지키지 않으면* *튜닝 은 *추측 게임* 이다.

*CPU 가 *기다리는 시간* 의 *대부분* 이 *메모리* 라면, *애플리케이션 이 *기다리는 시간* 의 *대부분* 은 *I/O*. *L1 / L2 / L3 캐시 의 *3 단계 완충재* 를 *이해 한 후* *I/O 의 *6 가지 패턴* 까지 *분류 할 수 있게 되면*, *"왜 이 코드가 *느린가"* 라는 질문 앞에서 *추측 대신 *측정* 으로 시작 할 수 있다.

*수십 줄의 fetch 전략 / batch / pool 튜닝* 이 *수만 줄의 코드 재작성* 보다 *효과적인 경우* — *그게 *I/O 의 물리* 다.

---

## *참고*

- Brendan Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd ed.
- Martin Kleppmann, *Designing Data-Intensive Applications*.
- Jens Axboe, *Efficient IO with io_uring* (kernel.dk 문서).
- Vlad Mihalcea 의 블로그 — *Hibernate / JPA performance* 의 *현대적 reference*.
- *async-profiler* (Andrei Pangin) — JVM 워크로드 의 *I/O wait 가시화 의 *표준*.
- 이전 글 [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) — *메모리 벽* 의 자매편.
