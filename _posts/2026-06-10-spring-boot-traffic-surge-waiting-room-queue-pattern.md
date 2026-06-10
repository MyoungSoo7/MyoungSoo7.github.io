---
layout: post
title: "*콘서트 예매 / 한정 특가 의 *트래픽 폭증* 을 *Spring Boot 로 어떻게 *대기열로 평탄화* 하는가 — *Virtual Waiting Room + Redis Sorted Set + Bucket4j + Resilience4j + WebSocket* 5 layer 의 *실전 구축법***"
date: 2026-06-10 19:00:00 +0900
categories: [backend, spring-boot, performance, sre, redis]
tags: [spring-boot, traffic-surge, waiting-room, redis, sorted-set, bucket4j, resilience4j, websocket, rate-limiting, flash-sale, concert-ticketing, optimistic-lock, pessimistic-lock, pg-payment]
---

이 글은 *콘서트 티켓 / 한정 특가 / 게임 오픈* 같은 *예고된 트래픽 폭증* 을 *Spring Boot 백엔드* 가 *터지지 않고 *공정하게 *처리* 하는 *5 layer 패턴* 을 정리한다. *Virtual Waiting Room (가상 대기실) → Token / Rate Limiting → Queue-based Admission → Optimistic Lock + 결제 분리 → CDN / Pre-warm* 의 *5 단계 의 *실전 구축법*. 

전 두 글 ([백엔드 TPS](/2026/06/10/backend-tps-throughput-realistic-cases-tools/) + [DB Connection Pool](/2026/06/10/spring-boot-db-connection-pool-hikaricp-deep-dive/)) 의 *후속편*. *100 TPS 시스템이 *10K TPS 가 *3 분간 *폭주* 할 때 *어떻게 *터지지 않게 하는가* 의 *진짜 답*.

읽고 가셔도 좋은 분:
1. *Spring Boot 백엔드 1-3 년차* — *flash sale / concert ticketing* 같은 *peak 트래픽 처리* 가 *처음* 인 사람
2. *티켓팅 / 커머스 / 게임 백엔드* — *대기열 도입 검토* 중인 사람
3. *SRE / 인프라* — *Redis 기반 *Virtual Waiting Room* 의 *현실적 구축법* 이 궁금한 사람

---

## TL;DR

> *트래픽 폭증 처리* 의 *진짜 패턴은 *Virtual Waiting Room + Redis Sorted Set + Bucket4j + Resilience4j + WebSocket 의 *5 layer 조합*. *모든 사용자를 *동시에 *들이지 않고*, *정해진 비율로 *순차 입장* 시키는 *공정한 throttle*. *Redis Sorted Set 의 *원자적 INCR* 가 *수십만 사용자의 *대기 순번* 을 *수 ms 안에 정확히 부여*.

**5 layer 한 그림**:

```
[수십만 사용자 동시 접속]
        │
        ▼
[Layer 1] CDN / Edge (Cloudflare) 
   정적 자산 차단 + bot 차단
        ▼
[Layer 2] Virtual Waiting Room
   Redis Sorted Set 에 *순번 부여* — 모든 사용자 우선 *대기실*
        ▼
[Layer 3] Token / Rate Limiting (Bucket4j)
   초당 *N 명만 *입장* 허용
        ▼
[Layer 4] Spring Boot Application
   *입장 토큰 검증* 후 실제 API 처리
        ▼
[Layer 5] DB / Resilience4j Circuit Breaker + Optimistic Lock
   *재고 1 = 결제 1* 의 *동시성 보장*
        ▼
[비동기 결제 분리 (Kafka)]
   결제 자체는 *별도 워커* — DB tx 최소화
```

---

## 0. *왜 *일반 시스템은 *터지는가*

### 0.1 *Flash sale 의 *전형적 *실패 시나리오***

```
14:00:00.000  티켓 오픈 직전 — 평소 100 TPS, 시스템 idle
14:00:00.001  20 만 명 동시 접속
14:00:00.010  Tomcat thread pool 200 개 *즉시 *전부 사용*
14:00:00.050  DB connection pool 50 개 *전부 사용*
14:00:00.100  Redis 도 connection 폭주 — TCP 연결 *수 만 *대기*
14:00:00.500  Tomcat queue 가 *수 만 건 적체*
14:00:01.000  사용자 1 차 timeout — *재시도 폭주 (retry storm)*
14:00:05.000  *DB CPU 100%* → *모든 쿼리 *수 십 초 지연*
14:00:30.000  *Kubernetes liveness probe 실패* → Pod 재시작
14:00:35.000  *재시작 직후 *부하 받아 *또 죽음*
14:01:00.000  *총체적 *서비스 다운*. 사용자 분노.
```

**이 시나리오의 *진짜 원인*:**
- *모든 사용자를 *동시에 들임*. *공정성 X*.
- *Retry 가 *상황을 *더 악화*.
- *DB / Redis / Tomcat / Pod 의 *어느 한 layer 만 *터져도 *연쇄*.

### 0.2 *Virtual Waiting Room 의 *철학***

> *모든 사용자에게 *순번을 부여* 하고, *시스템이 처리 가능한 속도로만 *입장 허용*. *대기는 *공정함의 비용*, *시스템 다운은 *모두에게 0*.

```
모든 사용자 → 대기실 → 순차 입장 → 실제 시스템

[20 만 명]   [대기 + 순번]   [초당 500 명 허용]   [정상 처리]
            "당신 앞에            "당신 차례입니다"
            12,847 명"
```

---

## 1. *Layer 1 — *CDN / Edge 단계 *방어***

### 1.1 *정적 자산 캐싱*

```
이벤트 페이지 HTML / CSS / JS / 이미지
        │
        ▼
[Cloudflare CDN]
  cache-control: public, max-age=300
        │
        ▼ (캐시 hit 99%)
사용자
```

→ *정적 트래픽은 *원본 서버에 *오지 않음*. *원본 서버는 *동적 API 만 처리*.

### 1.2 *Bot 차단 + DDoS 방어*

```
Cloudflare Rules:
  - User-Agent 가 curl, python-requests 차단
  - JS challenge (cf_chl_jschl_tk__) 통과 못 하면 차단
  - 동일 IP 분당 100 요청 초과 시 captcha
```

→ *진짜 사용자만 *Layer 2 로 진입*.

### 1.3 *예약 대기 페이지 — *static HTML***

```html
<!-- waiting.html — CDN 으로 *수십만 명에게 *0 부하* 로 전달 -->
<div id="wait">
  <p>티켓 오픈 대기 중</p>
  <p>오픈 시각: 2026-06-15 14:00:00</p>
  <p>예상 대기자: <span id="count">12,847</span></p>
</div>
<script>
  // 오픈 시각 까지 *클라이언트 timer*. 서버 부하 0.
  setInterval(updateTimer, 1000);
</script>
```

→ *오픈 *전* 대기는 *서버 한 줄 부하 X*. CDN 의 *static HTML* 이 *전부 처리*.

---

## 2. *Layer 2 — *Virtual Waiting Room (Redis Sorted Set)***

### 2.1 *Sorted Set 으로 *순번 자동 부여***

> *Redis Sorted Set* 이 *대기실 의 *진짜 무기*. *ZADD + ZRANK* 가 *원자적*. *수십만 명의 *순번 부여 + 조회* 가 *수 ms 안*.

```java
@Service
public class WaitingRoomService {

    private final StringRedisTemplate redis;
    private static final String QUEUE_KEY = "ticket:queue:concert-2026-06-15";
    private static final String ENTRY_KEY = "ticket:entry:concert-2026-06-15";

    /**
     * 사용자가 대기실 *진입* 시 호출.
     * Score = 진입 시각 (밀리초). 동일 시각이면 사용자 ID 로 결정.
     */
    public WaitingPosition enqueue(String userId) {
        long now = System.currentTimeMillis();
        // ZADD NX — 이미 있으면 update X (재진입 보호)
        Boolean added = redis.opsForZSet().addIfAbsent(QUEUE_KEY, userId, now);

        // 현재 순위 조회
        Long rank = redis.opsForZSet().rank(QUEUE_KEY, userId);
        Long total = redis.opsForZSet().size(QUEUE_KEY);

        return new WaitingPosition(
            userId,
            rank != null ? rank + 1 : -1L,
            total
        );
    }

    /**
     * 입장 허용된 사용자만 *입장 token* 부여 후 *대기실에서 제거*.
     */
    public boolean grantEntry(String userId, String token) {
        // 입장 토큰을 별도 set 에 저장 — 1 시간 유효
        Boolean granted = redis.opsForSet().add(ENTRY_KEY, userId) > 0;
        if (granted) {
            redis.opsForValue().set("ticket:token:" + token, userId, Duration.ofHours(1));
            redis.opsForZSet().remove(QUEUE_KEY, userId);
        }
        return granted;
    }

    /**
     * 토큰 검증 — 실제 API 호출 시.
     */
    public boolean validateToken(String token) {
        return redis.opsForValue().get("ticket:token:" + token) != null;
    }
}
```

### 2.2 *Admission Controller — 정해진 비율로 *입장***

```java
@Component
public class AdmissionController {

    private final WaitingRoomService waitingRoom;
    private final StringRedisTemplate redis;

    /**
     * 매 *1 초* 마다 실행 — *N 명씩 *입장* 시킴.
     * @Scheduled 가 ShedLock 으로 *분산 환경 *단일 실행 보장*.
     */
    @Scheduled(fixedRate = 1000)
    @SchedulerLock(name = "ticket-admission", lockAtLeastFor = "PT1S")
    public void admitNextBatch() {
        // 시스템 capacity 의 *80% 이하* 만 입장 허용
        int admitCount = calculateAdmissionRate();   // 예: 500 명/초

        // Sorted set 의 *앞 N 명* 만 입장 토큰 부여
        Set<String> nextUsers = redis.opsForZSet()
            .range(QUEUE_KEY, 0, admitCount - 1);

        for (String userId : nextUsers) {
            String token = UUID.randomUUID().toString();
            waitingRoom.grantEntry(userId, token);
            // WebSocket 으로 *입장 알림 푸시* (다음 layer)
            notifyUserEntry(userId, token);
        }
    }

    /**
     * 현재 시스템 부하 보고 *admission 속도 동적 조절*.
     */
    private int calculateAdmissionRate() {
        // Prometheus 의 *DB pool active* / *Tomcat thread* 비율 보고
        // 70% 이하 → 500 명/초
        // 80% 이상 → 200 명/초 (감속)
        // 90% 이상 → 0 명/초 (정지)
        double dbUsage = getDbPoolUsage();
        if (dbUsage > 0.9) return 0;
        if (dbUsage > 0.8) return 200;
        return 500;
    }
}
```

### 2.3 *대기 순번 *클라이언트 푸시 — WebSocket***

```java
@Controller
public class WaitingWebSocketController {

    private final SimpMessagingTemplate messaging;

    /**
     * 사용자가 WebSocket 연결 시 *대기 순번* 구독.
     * 매 5 초 마다 갱신 push.
     */
    @MessageMapping("/queue/subscribe")
    public void subscribe(String userId) {
        WaitingPosition pos = waitingRoom.getPosition(userId);
        messaging.convertAndSendToUser(
            userId, "/queue/position", pos);
    }

    /**
     * 입장 허용 시 *즉시 알림*.
     */
    public void notifyEntry(String userId, String token) {
        messaging.convertAndSendToUser(
            userId, "/queue/admit", 
            Map.of("token", token, "redirectUrl", "/ticket/select"));
    }
}
```

---

## 3. *Layer 3 — *Rate Limiting (Bucket4j)***

### 3.1 *Bucket4j 설치*

```kotlin
dependencies {
    implementation("com.bucket4j:bucket4j-redis:8.10.1")
    implementation("io.github.bucket4j:bucket4j-spring-boot-starter:0.10.1")
}
```

### 3.2 *사용자별 / IP별 / API별 *3 단 rate limiting***

```java
@Configuration
public class RateLimitConfig {

    /**
     * 사용자별: *분당 60 요청* + 초당 burst 5.
     */
    @Bean
    public Bucket userBucket(@Value("${rate.user.capacity:60}") long capacity) {
        Bandwidth limit = Bandwidth.classic(
            capacity,
            Refill.intervally(capacity, Duration.ofMinutes(1)));
        Bandwidth burst = Bandwidth.classic(
            5, Refill.intervally(5, Duration.ofSeconds(1)));
        return Bucket.builder()
            .addLimit(limit)
            .addLimit(burst)
            .build();
    }
}

@RestController
public class TicketController {

    private final Bucket userBucket;

    @PostMapping("/ticket/select")
    public ResponseEntity<?> selectTicket(
            @RequestHeader("X-Entry-Token") String token,
            @RequestBody TicketSelectRequest req) {

        // 1. 입장 토큰 검증
        if (!waitingRoom.validateToken(token)) {
            return ResponseEntity.status(403).body("invalid entry token");
        }

        // 2. Rate limit 검사
        if (!userBucket.tryConsume(1)) {
            return ResponseEntity.status(429)
                .header("Retry-After", "1")
                .body("rate limit — wait 1s");
        }

        // 3. 실제 처리
        return ResponseEntity.ok(ticketService.select(req));
    }
}
```

### 3.3 *Redis 기반 분산 *Bucket***

```java
// 다중 인스턴스 환경에서는 Redis 로 *공유 카운터*
@Bean
public ProxyManager<String> proxyManager(RedisClient client) {
    return Bucket4jRedis.casBasedBuilder(client)
        .expirationAfterWrite(ExpirationAfterWriteStrategy.basedOnTimeForRefillingBucketUpToMax(Duration.ofHours(1)))
        .build();
}

@Service
public class DistributedRateLimit {
    private final ProxyManager<String> proxyManager;

    public boolean tryAcquire(String userId) {
        return proxyManager.builder()
            .build(userId, () -> BucketConfiguration.builder()
                .addLimit(Bandwidth.classic(60, Refill.intervally(60, Duration.ofMinutes(1))))
                .build())
            .tryConsume(1);
    }
}
```

---

## 4. *Layer 4 — *Optimistic Lock + 결제 분리***

### 4.1 *재고 1 = 결제 1 의 *동시성 보장***

> *수십 명이 *동시에 *마지막 1 개* 를 *클릭*. *DB 가 *정확히 1 명에게만 *판매* 해야 함.

```java
@Entity
public class Ticket {
    @Id private Long id;
    private int stock;
    
    @Version  // ← *Optimistic Lock 의 핵심*
    private long version;
}

@Service
public class TicketService {
    
    @Transactional
    public Reservation reserve(Long ticketId, Long userId) {
        Ticket t = ticketRepository.findById(ticketId).orElseThrow();
        
        if (t.getStock() <= 0) {
            throw new SoldOutException();
        }
        
        t.setStock(t.getStock() - 1);   // ★ 여기서 version 검사
        // commit 시점에 *UPDATE ticket SET stock=?, version=version+1 
        //                  WHERE id=? AND version=?* 
        // *다른 사용자가 먼저 update 했으면 *0 row affected → OptimisticLockException*
        
        return reservationRepository.save(
            new Reservation(ticketId, userId));
    }
}
```

### 4.2 *Optimistic Lock 실패 시 *재시도***

```java
@Retryable(
    value = ObjectOptimisticLockingFailureException.class,
    maxAttempts = 3,
    backoff = @Backoff(delay = 100, multiplier = 2))
public Reservation reserve(Long ticketId, Long userId) {
    // 위 코드
}

@Recover
public Reservation recover(ObjectOptimisticLockingFailureException ex,
                          Long ticketId, Long userId) {
    throw new SoldOutException("재고 동시 차감 — 다시 시도해주세요");
}
```

### 4.3 *결제 분리 — Kafka 비동기*

> ⚠️ **transaction 안에 *PG 결제 호출 X*** ([Connection Pool 글 Case 2](/2026/06/10/spring-boot-db-connection-pool-hikaricp-deep-dive/)).

```
[동기 구간 — 1초 내]              [비동기 구간 — 별도 워커]
                                   
사용자 클릭                         결제 워커
   ↓                                ↓
Optimistic Lock 으로 *재고 차감*     Kafka 구독
   ↓                                ↓
"예약 완료" 상태로 DB 저장           PG (Toss / KCP) 호출
   ↓                                ↓
Kafka 발행: ReservationCreated      결제 결과로 *상태 갱신*
   ↓                                ↓
사용자에게 "결제 대기" 응답          WebSocket 으로 결제 완료 푸시
                                   "결제 성공 — 티켓 발급"
```

→ *동기 처리 시간 *1초 미만 = TPS 폭증* 견딤.

```java
@Transactional
public Reservation reserve(Long ticketId, Long userId) {
    // ... 위와 동일 ...
    
    Reservation r = reservationRepository.save(...);
    
    // Outbox 패턴 — DB tx 안에서 *이벤트도 INSERT*
    outboxRepository.save(new OutboxEvent("ReservationCreated", r));
    
    return r;
}

// 별도 Poller — 2 초 주기로 Outbox → Kafka 발행
// 별도 Consumer (다른 인스턴스) — Kafka → PG 결제 호출
```

> *Triple Idempotency* + Outbox 패턴 — *결제 중복 / 누락 0*. ([settlement 정산 글](/2026/06/06/personal-k3s-cluster-and-three-flagship-projects-deep-dive/))

---

## 5. *Layer 5 — *Resilience4j Circuit Breaker***

### 5.1 *외부 PG 가 *느려졌을 때***

> PG 사 *Toss / KCP* 가 *느려지면 — 우리 시스템도 *연쇄 지연*. *Circuit Breaker* 가 *조기 차단*.

```java
@CircuitBreaker(name = "paymentGateway", fallbackMethod = "paymentFallback")
@TimeLimiter(name = "paymentGateway")
public CompletableFuture<PaymentResult> charge(Order order) {
    return CompletableFuture.supplyAsync(() -> 
        tossClient.charge(order)
    );
}

public CompletableFuture<PaymentResult> paymentFallback(
        Order order, Throwable t) {
    // 결제 실패 시 *예약 자동 취소 + 사용자 알림*
    reservationService.cancel(order.getReservationId());
    return CompletableFuture.completedFuture(
        PaymentResult.failed("결제 시스템 일시 지연 — 자동 취소"));
}
```

### 5.2 *application.yml*

```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentGateway:
        failure-rate-threshold: 50       # 50% 실패 시 OPEN
        slow-call-rate-threshold: 80     # 80% 가 *2 초 초과* 면 OPEN
        slow-call-duration-threshold: 2s
        wait-duration-in-open-state: 30s # 30 초 후 HALF_OPEN
        sliding-window-size: 100         # 최근 100 요청 기준
        minimum-number-of-calls: 50
  timelimiter:
    instances:
      paymentGateway:
        timeout-duration: 3s             # 3 초 넘으면 timeout
```

---

## 6. *실전 사례 — *콘서트 / 한정 특가 패턴 4 종***

### Case 1 — *콘서트 티켓 *오픈 직후 *5 분 burst***

| 항목 | 값 |
|------|----|
| 동시 접속 | 20 만 명 |
| 판매 좌석 | 5,000 석 |
| 처리 시간 | 5 분 안 *모두 매진* |
| 평균 TPS | 17 TPS (5000 / 300 초) |
| Peak TPS | 800 TPS (오픈 직후 10 초) |

**전략**:
- Virtual Waiting Room 으로 *모든 사용자 *순번 부여*
- *초당 100 명* 만 admission
- 좌석 선택은 *Optimistic Lock* + Redis 의 *atomic decrement*
- 결제는 *3 분 hold* 후 Kafka 비동기

### Case 2 — *한정 특가 *플래시 세일***

| 항목 | 값 |
|------|----|
| 동시 접속 | 50만 명 |
| 판매 수량 | 100 개 |
| 처리 시간 | *5 초 안 매진* |
| Peak TPS | 5,000 TPS (initial spike) |

**전략**:
- *오픈 *5 초 전* 부터 *대기실 시작*
- *Token bucket 5,000 개를 *0 초에 즉시 발행*
- *재고 100 개 * 의 *5,000 → 100 entry 만 *Optimistic Lock 성공*
- *나머지 4,900 명은 *sold-out 페이지*

### Case 3 — *게임 *대규모 업데이트 후 *로그인 폭주***

| 항목 | 값 |
|------|----|
| 동시 접속 | 100 만 명 |
| 처리 대상 | 인증 + 캐릭터 로드 |
| Peak TPS | 50,000 TPS |

**전략**:
- *지역별 *입장 큐* (대기실 *5 개 *지역 별*)
- *서버 인스턴스 *2 배 *pre-warm* (HPA 대응 못 함)
- *캐릭터 데이터 read replica* + *Redis L1 캐시*
- *결제 / 충전은 *별도 도메인 분리*

### Case 4 — *수강 신청 (대학교 LMS)*

| 항목 | 값 |
|------|----|
| 동시 접속 | 1 만 명 (한 대학) |
| 처리 대상 | 수업 신청 + 시간표 충돌 검사 |
| Peak TPS | 500 TPS (오픈 10 초) |

**전략**:
- 대기실 *학년 별 *순차 오픈* (4 학년 → 3 → 2 → 1)
- *시간표 충돌 검사는 *Redis 의 *Set 연산*
- *최종 신청은 *Pessimistic Lock* (Optimistic 보다 안전)

---

## 7. *함정과 *학습 압축*

### 7.1 *대기실 *자체가 *터지면 안 됨***

> *대기실 Redis 가 *터지면 *모든 사용자 *동시에 정문 통과* — 시스템 *터짐*. *Redis Cluster* + *Sentinel* 로 *HA* 필수.

### 7.2 *공정성 vs 시스템 보호*

```
공정성:    먼저 클릭한 사람이 먼저 입장 (FIFO)
시스템 보호: 부하 *너무 높으면 *공정성 일부 희생 후 *throttle*
```

> *둘 다 100% 보장 X*. *경계 선이 어디인지 *비즈니스 와 *합의*.

### 7.3 *재시도 폭주 (Retry Storm)*

> 사용자 *클라이언트 자동 재시도* 가 *서버 부하 *× 5*. *response 에 *Retry-After 헤더* 명시 + *클라이언트 에게 *지수 백오프 강제*.

### 7.4 *Test 환경에서 *재현 어려움***

> *Production 부하 = 50만 동시* 인데 *staging = 10 명*. *k6 + 부하 머신 5 대* 로 *실전 가까운 *시뮬레이션* 정기 실시.

```bash
# k6 — 분산 부하
k6 run --vus 50000 --duration 5m ticketing-load.js
```

### 7.5 *DB 가 *진짜 천장***

> 모든 layer 통과 후 *최종 DB 가 *터지면 *답 없음*. *Read replica 분리 + Redis L1 캐시* 로 *DB 가 *80% 미만 부하 유지*.

---

## 8. *마무리 — *대기열 시스템의 *진짜 가치***

### 8.1 *대기는 *공정함의 비용***

> *사용자가 30 분 기다린 끝에 *정상 결제 = 분노 0*. *5 초 만에 *서비스 다운 = 분노 100*. *적절한 대기는 *결제 성공 보다 *큰 가치*.

### 8.2 *5 layer 의 *조합이 *진짜 솔루션***

> *Virtual Waiting Room 만 / Bucket4j 만 / Circuit Breaker 만* 으로는 *부족*. *5 layer 의 *조합* 이 *진짜 답*. *어느 layer 한 곳 만 약하면 *그곳에서 *터짐*.

### 8.3 *Spring Boot 의 *현실적 우위*

> *Spring Boot + Redis + Bucket4j + Resilience4j + Kafka* 가 *진짜 *production-grade 조합*. *이 스택의 *각자의 책임 명확* — *학습 곡선이 *제어 가능*.

### 8.4 *이력서 변환 hook*

> *"트래픽 폭증 처리 경험"* 한 줄에:
> - 5 layer 패턴 (CDN / Waiting Room / Rate Limit / Optimistic Lock / Circuit Breaker)
> - Redis Sorted Set 의 *원자성 보장* 메커니즘
> - Bucket4j 의 *분산 rate limit* 구조
> - Optimistic vs Pessimistic Lock 의 *trade-off*
> - Outbox + Kafka 의 *결제 비동기 분리*
> - 4 가지 사고 패턴 (콘서트 / 플래시 세일 / 게임 / 수강)
> 
> *4 단 깊이 면접 답변 hook* 모두 준비.

---

## 부록 — *Spring Boot + Redis Waiting Room *최소 셋업***

```bash
# 1. 의존성
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-websocket")
    implementation("io.github.bucket4j:bucket4j-spring-boot-starter:0.10.1")
    implementation("com.bucket4j:bucket4j-redis:8.10.1")
    implementation("io.github.resilience4j:resilience4j-spring-boot3:2.2.0")
    implementation("net.javacrumbs.shedlock:shedlock-spring:6.0.0")
}

# 2. application.yml — Redis + WebSocket + Resilience4j
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: 6379
  scheduling:
    enabled: true
      
resilience4j:
  circuitbreaker:
    instances:
      paymentGateway:
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s

# 3. 실행
./gradlew bootRun
```

→ *10 분 안에 *대기열 + rate limit + circuit breaker* 기본 셋업 완료.

---

*다음 글:* *Redis Cluster 의 *failover 시점에 *대기열 데이터 손실* 을 *어떻게 *최소화 하는가* — *AOF + RDB + sentinel 의 *조합 + 백업 정책*.
