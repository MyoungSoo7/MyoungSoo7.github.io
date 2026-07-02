---
layout: post
title: "캐시 적중률 (Cache Hit Rate) — 7 계층 을 관통 하는 *진짜 성능 지표*"
date: 2026-07-01 19:45:00 +0900
categories: [backend, cache, performance, observability]
tags: [cache, caffeine, redis, cdn, page-cache, cpu-cache, buffer-pool, eviction, lru, tinylfu]
published: false
---

*"우리 시스템 은 캐시 를 씁니다"* — 이 문장 자체 로는 *의미 없음*. *캐시 를 *얼마나 잘 씀* = *적중률 (Hit Rate)*. 90% 는 *괜찮음*, 95% 는 *좋음*, 99% 는 *탁월*, 99.9% 는 *예술*. 이 숫자 의 차이 가 *p99 latency 의 *10 배 차이*.

이 글은 *하드웨어 부터 CDN 까지 *7 계층* 의 *캐시 적중률* 을 *한 관점 으로 정리*. settlement / sparta 의 *실 수치* + *측정 도구* + *개선 방법* + *함정*.

---

## 1. Cache Hit Rate 의 *정의*

```
Hit Rate = Hits / (Hits + Misses)
```

- **Hit** — 캐시 에 요청 데이터 *있음* → *즉시 반환*
- **Miss** — 캐시 에 *없음* → *원본 저장 소* (DB / 원격 서버 / disk) 로 이동

*Hit Rate 이 *n%* 라는 것 은 *n% 요청 이 *캐시 만 으로 완료*. *나머지 (100-n)%* 만 *느린 원본* 접근.

**Latency 로 표현**:
```
평균 latency = HitRate × HitLatency + (1 - HitRate) × MissLatency
```

*예시* — HitLatency = 1ms, MissLatency = 100ms:
- Hit Rate 90% → 평균 *10.9 ms* (miss 가 *90.9% 차지*)
- Hit Rate 95% → 평균 *5.95 ms*
- Hit Rate 99% → 평균 *1.99 ms*
- Hit Rate 99.9% → 평균 *1.1 ms*

*99% → 99.9%* 의 *0.9% 개선* 이 *latency 반감*. 이 게 *캐시 튜닝 의 *숨은 지렛대*.

---

## 2. 7 계층 캐시 — *한 요청 이 지나는 전 여정*

```
사용자 브라우저 (L7 Browser Cache)
    ↓ (Miss → HTTP 요청)
CDN 엣지 (L6 CDN Cache, Cloudflare)
    ↓ (Miss → origin)
Application (L5 Local Cache, Caffeine)
    ↓ (Miss)
Distributed (L4 Redis / Memcached)
    ↓ (Miss)
DB Buffer Pool (L3 PostgreSQL shared_buffers)
    ↓ (Miss)
OS Page Cache (L2)
    ↓ (Miss)
CPU Cache (L1 — Intel L1/L2/L3)
    ↓ (Miss)
NAND Flash / HDD  ← 여기 까지 오면 *느림*
```

**한 요청 의 *비용 배수***:
| 계층 | Hit latency | Miss latency 배수 |
|---|---|---|
| L7 Browser | ~1 ms | ×20 (CDN) |
| L6 CDN | ~10 ms | ×10 (origin) |
| L5 Application local | ~1 μs | ×1000 (Redis) |
| L4 Redis | ~1 ms | ×10 (DB) |
| L3 DB buffer pool | ~10 μs | ×1000 (SSD) |
| L2 OS page cache | ~100 ns | ×500 (SSD read) |
| L1 CPU cache | ~1 ns | ×100 (RAM) |

*각 계층* 이 *다음 계층 대비 *10~1000 배 빠름*. *Hit Rate 이 낮으면 *즉시 다음 계층* 으로 폭포*. *모든 계층 이 miss 하면 *SSD 접근* — *가장 느린 경로*.

---

## 3. L1 — CPU Cache (하드웨어)

*Intel i7 / Apple M2 등*:
- **L1 data** — 32 KB / core, ~1 ns
- **L2** — 512 KB / core, ~3 ns
- **L3** — 24 MB (전체 공유), ~10 ns
- **RAM** — GB, ~100 ns

**적중률 측정** — Linux `perf`:
```bash
perf stat -e cache-references,cache-misses,L1-dcache-load-misses ./myapp

Performance counter stats:
  1,234,567,890  cache-references
    12,345,678  cache-misses     #  1.00% of all cache refs
   456,789,012  L1-dcache-load-misses
```

*Hit Rate = 1 - 1% = 99%*. *일반 앱* 은 *L1 95~99%*, *데이터 밀집 (numpy, blas)* 는 *L1 99%+*.

**개선 방법**:
- **cache-friendly data layout** — struct of arrays (SoA) > array of struct (AoS)
- **loop tiling** — *큰 배열* 을 *cache 크기 로 분할*
- **prefetching** — `__builtin_prefetch()`
- **false sharing 방지** — *같은 cache line (64 B) 의 *다른 field* 를 *다른 core 가 접근* → *cache invalidation 폭증*

**함정** — *멀티 스레드 의 `AtomicInteger[]` 배열* — *배열 원소 가 *같은 cache line* 이면 *false sharing*. `@Contended` (Java 9+) 로 *64 byte padding*.

---

## 4. L2 — OS Page Cache

*리눅스 / macOS* 는 *디스크 파일 을 *RAM 에 자동 캐시*. *file open* 시 *실 데이터 는 RAM 에 이미 있으면 disk 접근 0*.

**측정**:
```bash
# 캐시 사용 량
free -h
              total        used        free      buff/cache
Mem:           32Gi         12Gi        5.0Gi        15Gi

# 특정 파일 이 캐시 됐는지
vmtouch /var/lib/postgresql/data/base/*
Files: 5433
Directories: 21
Resident Pages: 234567/456789 (51.3%)

# hit ratio (전체)
cat /proc/meminfo | grep -E "Cached|Buffers"
```

**활용**:
- *DB 데이터 파일* 이 *OS page cache 에 있으면 *SSD 접근 없이 read*
- *2 번 째 실행 부터 는 *warm cache*
- *sync 후 강제 flush* — `sync && echo 3 > /proc/sys/vm/drop_caches` (테스트 용)

**개선**:
- **posix_fadvise** — 앱 이 *"이 파일 은 순차 read 만 함"* 힌트 → *kernel 이 aggressive readahead*
- **O_DIRECT** — *page cache 우회* (DB / DBMS 가 *자체 buffer pool 관리 하는 경우*, page cache 는 오히려 방해)
- **hugepages** — 큰 파일 의 *page 관리 overhead 감소*

---

## 5. L3 — Database Buffer Pool

*PostgreSQL 의 `shared_buffers`*, *MySQL 의 `innodb_buffer_pool_size`*. *디스크 페이지 (8 KB) 를 RAM 에 캐시*.

### PostgreSQL — shared_buffers hit ratio
```sql
-- 전역 hit ratio
SELECT 
    ROUND(sum(blks_hit) * 100.0 / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2) 
    AS cache_hit_ratio
FROM pg_stat_database;

-- 테이블 별
SELECT 
    schemaname, relname,
    heap_blks_hit,
    heap_blks_read,
    ROUND(heap_blks_hit * 100.0 / NULLIF(heap_blks_hit + heap_blks_read, 0), 2)
    AS hit_ratio
FROM pg_statio_user_tables
ORDER BY heap_blks_read DESC LIMIT 20;
```

**settlement 의 실 수치**:
- 전역: **99.4%**
- `payments`: 99.8%
- `outbox_events`: 99.9% (핫 테이블)
- `orders`: 99.5%
- `audit_logs`: 87% (append-only, 옛 데이터 조회 시 miss)

**권장 값**:
- shared_buffers 는 *RAM 의 25%* — *32 GB RAM 이면 8 GB*
- *너무 크게 (50%+)* 하면 *page cache 와 중복 캐시* → *실 효과 감소*
- *hit ratio < 99%* 이면 *shared_buffers 증설 또는 *튜닝 검토*

**개선**:
- **인덱스 추가** — full scan 이 원인 이면 index scan 으로
- **pg_prewarm** — *서버 재시작 후 *hot 테이블 을 *미리 buffer pool 에 로드*
- **partition** — *cold 데이터* 를 *별도 파티션* 으로 → *hot 파티션 만 buffer 유지*

### PostgreSQL 의 *특이 점* — *2 단 캐시*
PostgreSQL 은 *shared_buffers* + *OS page cache* 를 *동시 사용*. *shared_buffers miss* 시 *바로 SSD 가 아니라 *OS page cache* 시도. 그래서 *`blks_read` 도 *많은 부분 이 *OS cache hit* — *실 SSD 접근 은 훨씬 적음*.

---

## 6. L4 — Distributed Cache (Redis / Memcached)

*네트워크 를 통한 캐시*. *여러 앱 인스턴스 가 공유*.

### Redis Hit Rate
```bash
redis-cli INFO stats | grep keyspace
keyspace_hits:12345678
keyspace_misses:234567
# Hit Rate = 12345678 / (12345678 + 234567) = 98.14%
```

Or `redis-cli --stat`:
```
keyspace_hits/sec: 5000
keyspace_misses/sec: 100
Hit Rate: 98%
```

**settlement 의 실 수치**:
- 세션 캐시: **99.9%**
- 상품 조회 캐시: 95%
- 정산 대사 캐시: 92%

**적정 target**:
- 세션 / 로그인: *반드시 99%+*
- 상품 목록: *90%+ 이면 좋음*
- 검색: *80%+*

### Eviction Policy
```
maxmemory 4gb
maxmemory-policy allkeys-lru
```

옵션:
- **noeviction** — 메모리 가득 차면 *새 SET 거부* (위험)
- **allkeys-lru** — *모든 키* 중 *LRU 제거* (가장 흔함)
- **allkeys-lfu** — *LFU (사용 빈도)* — *희소 하지만 hot 인 key* 보존
- **volatile-lru** — *TTL 있는 키* 만 LRU 제거
- **allkeys-random** — 랜덤 (거의 안 씀)

**settlement 의 선택** — `allkeys-lru` + `maxmemory 4gb`.

### 함정 — Cache Stampede
*캐시 만료 순간* + *동시 요청 100 개* → *100 개 요청 이 *동시 에 원본 DB 조회* → *DB 폭발*.

**해결**:
- **PERK** (Probabilistic Early Refresh) — *만료 임박* 시 *일부 요청 만 갱신*, 나머지 는 *옛 캐시 반환*
- **XFETCH** — Redis 의 *stochastic caching*
- **분산 락** — *한 요청 만 갱신*, 나머지 는 *대기 또는 옛 값*
- **coalescing** (`singleflight` 라이브러리) — *같은 key 의 *동시 요청 을 *1 개 로 통합*

---

## 7. L5 — Application Local Cache (Caffeine)

*JVM 프로세스 안* 의 캐시. *네트워크 없음 → ns 단위 latency*.

### Caffeine (Java 표준)
```java
Cache<String, Product> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofMinutes(5))
    .recordStats()      // ← 통계 활성화
    .build();

// 사용
Product p = cache.get(productId, id -> productRepo.findById(id).orElse(null));

// 통계
CacheStats stats = cache.stats();
double hitRate = stats.hitRate();  // 0.0 ~ 1.0
long missCount = stats.missCount();
```

**Caffeine 의 *마법* — TinyLFU**:
- *Sliding window* + *frequency sketch*
- *"자주 사용 되지만 최근 사용 안 됨"* 도 유지
- *LRU 보다 *5~10% 높은 hit rate* (실측)

### Metrics 통합 (Spring Boot)
```java
@Bean CacheManager cacheManager() {
    return new CaffeineCacheManager("products", "sellers");
}

// application.yml
spring:
  cache:
    caffeine:
      spec: maximumSize=10000,expireAfterWrite=5m,recordStats
management:
  metrics:
    cache:
      instrument: true   // Micrometer 자동 등록
```

Prometheus:
```
cache_gets_total{cache="products",result="hit"}
cache_gets_total{cache="products",result="miss"}
```

Grafana:
```promql
rate(cache_gets_total{cache="products",result="hit"}[5m]) /
rate(cache_gets_total{cache="products"}[5m])
```

**settlement 의 실 수치**:
- `products` — 96%
- `sellers` — 99%
- `commission_rates` — 99.9% (거의 변하지 않음)

### 함정 — *메모리 폭증*
Caffeine 의 `maximumSize` 는 *entry 수*, *바이트 아님*. *큰 객체 를 캐시 하면 *heap OOM 위험*. 

**해결** — `maximumWeight` + `weigher`:
```java
.maximumWeight(1_000_000_000L)  // 1 GB
.weigher((k, v) -> ((Product) v).estimatedByteSize())
```

---

## 8. L6 — CDN Cache (Cloudflare)

*지리 적 으로 분산 된 엣지*. *정적 파일 (이미지, JS, CSS) 의 최전선*.

### Cloudflare 대시보드 지표
- **Cache Hit Ratio** — 계정 별 대시보드
- **Bytes served from cache** — 트래픽 의 몇 % 가 캐시 에서

**내 도메인 의 실 수치**:
- `myoungsoo7.github.io` (블로그) — **97%** (GitHub Pages 정적)
- `chat.lemuel.co.kr` (sparta) — 85% (JS/CSS 캐시, API 는 우회)
- `immich.lemuel.co.kr` (사진) — 92% (이미지 캐시)

### Cache-Control 헤더
```
Cache-Control: public, max-age=31536000, immutable
```

- `public` — *모든 캐시* (CDN, 브라우저) *공유 가능*
- `max-age=31536000` — 1 년
- `immutable` — *만료 전 재검증 없음* (fingerprint URL 전제)

### Cloudflare Page Rule
```
URL: chat.lemuel.co.kr/_next/static/*
Cache Level: Cache Everything
Edge Cache TTL: 1 year
Browser Cache TTL: 1 year
```

*Next.js 의 *fingerprint 된 정적 파일* 을 *영구 캐시*.

---

## 9. L7 — Browser Cache

*사용자 브라우저 의 로컬 저장*. *0 네트워크*.

### 헤더 조합
```
Cache-Control: public, max-age=3600
ETag: "abc123"
Last-Modified: Wed, 01 Jul 2026 00:00:00 GMT
```

- **Fresh** — `max-age` 안 → *네트워크 0*
- **Stale + Revalidation** — *만료 후 *304 확인 요청* (ETag / If-Modified-Since)

### Service Worker + Cache API
*PWA / 오프라인 앱*:
```javascript
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});
```

*브라우저 완전 오프라인 에서도 동작*.

---

## 10. *실 튜닝 사례* — settlement 의 hit rate 개선

### 문제
2026-04 시점 — *상품 목록 API 의 *p99 latency 500ms*. *DB 부하 폭증*.

### 진단
```
pg_statio_user_tables — products 의 hit ratio: 82%
Caffeine (products cache) — hit rate: 40%
Redis (session) — 99% (문제 없음)
```

*Caffeine 40%* 가 원인. *maximumSize=1000* 인데 *실 상품 5000 개*.

### 개선
```java
// Before
.maximumSize(1000)
.expireAfterWrite(Duration.ofMinutes(1))

// After
.maximumSize(10_000)
.expireAfterWrite(Duration.ofMinutes(15))
.refreshAfterWrite(Duration.ofMinutes(5))   // 백그라운드 갱신
```

### 결과
- Caffeine hit rate: **40% → 94%**
- DB hit rate: 82% → 99%
- p99 latency: 500ms → 45ms
- DB TPS: 3000 → 1200 (부하 감소)

*1 번 의 튜닝* — *10 배 latency 개선*. *cache 튜닝 의 지렛대*.

---

## 11. Cache 계층 별 *권장 target*

| 계층 | 최소 | 권장 | 탁월 |
|---|---|---|---|
| L1 CPU | 90% | 95% | 99%+ |
| L2 Page Cache | 60% | 80% | 90%+ |
| L3 DB Buffer Pool | 95% | 99% | 99.5%+ |
| L4 Redis | 80% | 95% | 99%+ |
| L5 Caffeine | 70% | 90% | 95%+ |
| L6 CDN | 70% | 85% | 95%+ |
| L7 Browser | 50% | 70% | 90%+ |

*상위 계층 (L7 → L1)* 순서 로 *hit rate 낮아짐 이 자연*. *하위 로 갈 수록 *데이터 량 이 커지고 만료 자주*.

---

## 12. *운영 함정 6 가지*

### (1) Cache Invalidation 의 *지옥*
*"컴퓨터 과학 의 2 대 난제 — cache invalidation 과 naming things"* (Phil Karlton).

- **event-based** — DB 변경 시 *이벤트* 로 캐시 삭제 (Kafka + Redis DEL)
- **TTL based** — 짧은 TTL 로 *max staleness 제한*
- **stale-while-revalidate** — *만료 데이터 반환 + 백그라운드 갱신*

### (2) *공짜 캐시 는 없다*
*캐시 = 메모리 소비 + 무효화 비용*. *hit rate < 50%* 면 *캐시 없이 가 나음*.

### (3) *캐시 크기 vs TTL trade-off*
- *TTL 짧음 + 큰 캐시* → *메모리 낭비*
- *TTL 길음 + 작은 캐시* → *staleness 위험*
- *sweet spot* — *데이터 변경 빈도* 기반 결정

### (4) *cold start 후 stampede*
*재배포 직후* — *모든 캐시 miss* → *DB 폭발*.

**해결** — *Redis 는 재부팅 시 AOF/RDB 복원*, *Caffeine 은 warm-up 로직*:
```java
@PostConstruct
void warmUp() {
    productRepo.findTop1000ByOrderByViewCountDesc()
        .forEach(p -> cache.put(p.getId(), p));
}
```

### (5) *멀티 인스턴스 의 *cache coherence*
*3 replica 앱 인스턴스* → *각자 별도 Caffeine 캐시*. *staleness 편차*.

**해결** — *2 계층* — Caffeine (L1, 1 초 TTL) + Redis (L2, 5 분 TTL). *3 replica 가 동기화*.

### (6) *hot key* 문제
*Redis 의 *특정 key 가 QPS 폭증* → 해당 shard *과부하*.

**해결**:
- *hot key 감지* — `redis-cli --hotkeys`
- *client-side cache* — Redis 6+ 의 *tracking* + *client cache*
- *shard 분산* — *hot key 를 *N 개 로 split*

---

## 13. 도구 정리

| 계층 | 측정 | 개선 도구 |
|---|---|---|
| L1 CPU | `perf stat` | `__builtin_prefetch`, `@Contended` |
| L2 OS | `vmtouch`, `/proc/meminfo` | `posix_fadvise`, hugepages |
| L3 DB | `pg_statio_user_tables` | pg_prewarm, index, partition |
| L4 Redis | `INFO stats` | LFU / LRU, sharding |
| L5 Caffeine | Micrometer + Grafana | TinyLFU, refreshAfterWrite |
| L6 CDN | Cloudflare dashboard | Cache-Control, Page Rule |
| L7 Browser | DevTools Network | ETag, Service Worker |

---

## 14. 마치며 — *hit rate 는 *성능 의 *진짜 신호*

*"응답 이 느려요"* — *DB 튜닝 부터* 시작 하는 실수. 진짜 순서:
1. **각 계층 의 *hit rate 측정***
2. *가장 낮은 계층 부터 개선*
3. *다시 측정*

*90% → 99%* 의 *hit rate 개선* 이 *10 개 의 인덱스 추가 보다 *큰 효과*. *캐시 튜닝* 이 *성능 최적화 의 *제 1 무기*.

내 클러스터 의 *14 개월 운영* 의 *작은 결론* — *hit rate 모니터링 이 없으면 *캐시 를 쓰는 게 아니라 *캐시 를 소비 만 함*. *Prometheus + Grafana 로 *각 계층 의 hit rate 를 *상시 대시보드* 에 두는 것 이 *진짜 시작*.

**핵심 메시지**: *"캐시 를 *쓴다* 는 사실 이 중요 한 게 아니다. *hit rate 이 *얼마인지* 가 *진짜 지표*. *측정 없는 캐시 는 *캐시 가 아니라 *메모리 낭비*"*

---

## 참고

- *Systems Performance, 2nd Ed* (Brendan Gregg)
- *Designing Data-Intensive Applications* (Martin Kleppmann) — Chapter 6 캐시 부분
- *High-Performance Java Persistence* (Vlad Mihalcea) — DB buffer pool
- *Caffeine Wiki* — [github.com/ben-manes/caffeine/wiki](https://github.com/ben-manes/caffeine/wiki)
- *Redis Documentation* — [redis.io/docs](https://redis.io/docs/)
- 자매편:
    - [CPU 의 L1, L2, L3 캐시 와 병목 구간 고찰](/2026/06/17/cpu-cache-hierarchy-l1-l2-l3-and-memory-bottleneck.html)
    - [DB 설계 와 쿼리 — 14 개월 운영 경험](/2026/06/29/db-design-and-query-practical-guide.html)
    - [IntelliJ 실행 (데스크탑) 과 Telegram 실행 (모바일) — 실 과정 추적](/2026/07/01/what-happens-when-you-launch-intellij-and-telegram.html)
    - [I/O 병목 어떻게 해결하지?](/2026/06/18/io-bottleneck-how-to-solve.html)
