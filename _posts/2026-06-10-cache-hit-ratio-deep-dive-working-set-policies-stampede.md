---
layout: post
title: "캐시 적중률 (Cache Hit Ratio) — *90%면 충분한가*? *Working Set · 정책 (LRU/LFU/ARC) · Stampede · 분산 캐시* 의 *진짜 *체계화*"
date: 2026-06-10 17:15:00 +0900
categories: [performance, caching, sre]
tags: [cache, hit-ratio, miss-rate, working-set, lru, lfu, arc, caffeine, redis, cache-aside, write-through, write-back, stampede, thundering-herd, consistency-hashing, memory-hierarchy]
---

*"우리 캐시 적중률이 95% 인데 왜 여전히 느려요?"* — *실무에서 가장 자주 묻는 캐시 관련 질문*. *답은 *95% 가 사실 *낮은 숫자* 일 수 있다는 것*. *Working set 의 크기, *cache 의 *층층 구조*, *miss 의 *비용 비대칭*, *stampede 의 *조용한 살인자** — 이 *4 가지 의 진짜 이해* 가 없으면 *적중률 의 숫자 자체 가 *오해를 부른다*.

이 글은 *캐시 적중률 의 *진짜 깊이*. **(1) 정의 와 측정**, **(2) 90% 가 충분 한가 — *miss 의 비대칭 비용**, **(3) Working set 과 cache 크기 의 관계**, **(4) 정책 — LRU / LFU / ARC / W-TinyLFU**, **(5) Cache 패턴 — aside / write-through / write-back**, **(6) Stampede / thundering herd 의 해결**, **(7) 분산 캐시 — consistency hashing 의 의미**, **(8) 측정 도구**, **(9) 흔한 함정 5 가지**. 어제 [*서버 성능 개선 기초*](https://myoungsoo7.github.io) 글의 *심화편*.

---

## TL;DR

| 질문 | 답 |
|---|---|
| 적중률 95% 면 충분한가? | *miss 의 비용* 에 달림. *DB 쿼리 100ms* + *캐시 100μs* 면 *95% 적중률 = 평균 *5.1ms*. *99.9% 라야 *0.2ms*. *3 자리 9 를 노려야 *진짜 빠름* |
| LRU 가 무조건 정공? | 아니다. *추천 시스템 / 트렌딩 페이지* 같은 *Zipf 분포* 에는 *LFU* 또는 *ARC* 가 더 정공 |
| Write 시 무엇을 해야 하나? | *cache-aside* (조회만 캐싱) 가 표준. *write-through / write-back* 은 *데이터 정합성 의 강도* 차이 |
| 인기 키가 expire 되면? | *Cache Stampede*. 동시 다발 적 DB 부하로 *전체 다운*. *단일 비행 (single-flight) 패턴* 으로 해결 |
| 분산 캐시 의 노드 추가 시 hit ratio 가 0 으로? | *modular hashing* 의 함정. *Consistency Hashing* 이 정공 |

**핵심 명언**:

- *"There are only two hard things in Computer Science: cache invalidation and naming things."* — Phil Karlton
- *"The fastest code is the code that doesn't run; the second fastest is the code in cache."*

**실무 함의**: *적중률 숫자 만 보지 말고 — *miss 의 *총 비용 (count × per-miss latency)** 을 봐라*. *p99 latency 와 함께 보면* — *적중률 99% 인데 *p99 가 *5 초* 일 수 있다*. *1% 의 miss 가 *모든 사용자 의 *느린 경험* 의 원인*.

---

## 0. *기본 정의* — 적중률·미스율·평균 latency

```
hit ratio  = cache hits / total requests
miss rate  = 1 - hit ratio
average latency = hit_ratio × cache_lat + miss_rate × source_lat
```

```
예시:
  cache lookup: 100 μs (= 0.1 ms)
  DB query:     100 ms

  hit ratio 90%  → 평균 = 0.9 × 0.1 + 0.1 × 100 = 10.09 ms
  hit ratio 95%  → 평균 = 0.95 × 0.1 + 0.05 × 100 = 5.095 ms
  hit ratio 99%  → 평균 = 0.99 × 0.1 + 0.01 × 100 = 1.099 ms
  hit ratio 99.9% → 평균 = 0.999 × 0.1 + 0.001 × 100 = 0.1999 ms
  hit ratio 100% → 평균 = 0.1 ms
```

*적중률 5% 차이가 *평균 latency 의 *수십 배* 차이* 를 만든다. *90% 와 99% 가 같은 *느낌* 으로 들리지만 *실제 성능 은 *10 배* 차이*. *"적중률 95% 면 충분" 은 *부정확한 직관**.

### 0-1. *p99 의 진짜 의미*

평균 *latency* 가 *그럭저럭* 보여도 — *p99 = *miss 한 사용자 의 경험*. *99% hit ratio 면 *1% 의 사용자 가 *100ms 의 DB 쿼리* 를 본다*. p99 가 100ms 가 *된다*. *p99.9 는 더 나쁘다*. *적중률 의 *분포 적 해석* 이 정공.

---

## 1. *Working Set* — *cache 크기 의 정공 기준*

*working set* = *현재 *활발히 접근* 되는 데이터 의 집합. 캐시 크기 의 *진짜 정공 기준*.

```
워크로드:  하루 10,000 종 상품 중 *상위 200 종 이 *95% 의 조회* 발생
working set ≈ 200 종

cache 크기 200 종 → hit ratio ~95%
cache 크기 500 종 → hit ratio ~98%
cache 크기 2000 종 → hit ratio ~99%
cache 크기 10000 종 → hit ratio ~100%
```

*working set 보다 cache 가 *너무 작으면 *thrashing* — *항상 evict 와 fetch* 반복. *너무 크면 *메모리 낭비 + GC 비용*. *Sweet spot 은 working set 의 *1~3 배***.

### 1-1. *Zipf 분포* — *현실 의 거의 모든 워크로드*

상품 / 게시글 / 검색어 의 *조회 빈도 분포 는 *대부분 Zipf 분포* — *극소수 의 *초인기 항목 이 *대다수 의 트래픽 을 차지*. 결과:

- *상위 1% 항목 이 *50% 트래픽*
- *상위 10% 항목 이 *90% 트래픽*
- *적은 cache 크기 로도 *높은 hit ratio*

이 *불균등 이 *cache 가 효과적 인 이유*. *모든 항목이 균등하게 조회* 된다면 — *cache 는 거의 의미 없다 (반복 hit 없음)*.

---

## 2. *Cache 정책* — LRU 가 *정답* 이 아닐 때

### 2-1. *LRU (Least Recently Used)*

*가장 오랫동안 안 쓰인* 항목을 evict. *직관적이고 단순*. *대부분 의 워크로드 에 *준수한 성능*. *Java 의 `LinkedHashMap` 의 access-order 모드* 가 LRU.

**약점**: *한 번 의 *대량 스캔* 이 모든 캐시 를 오염*. 예: 야간 배치가 *전체 상품을 한 번씩 조회* 하면 — *그 동안 의 *인기 상품 이 evict*. *낮 트래픽 의 hit ratio 가 *급락*.

### 2-2. *LFU (Least Frequently Used)*

*가장 적게 쓰인* 항목 을 evict. *Zipf 분포 에 *압도적 적합*. *인기 상품 은 카운트 가 높아 *살아남는다*.

**약점**: *오래 전에 한 번 폭발 한 항목 (특가 이벤트 같은) 이 *영원히 살아 남음*. *적응성 부족*. *카운트 관리 비용 도 높음*.

### 2-3. *ARC (Adaptive Replacement Cache)*

*IBM 의 발명* — *LRU + LFU 의 *적응 적 결합*. *워크로드 의 패턴 에 따라 *자동 조정*. *디비 의 page cache* 등에 채택. *복잡 도 가 *코드 적 비용*.

### 2-4. *W-TinyLFU* — *Caffeine 의 채택*

*최신 알고리즘 (2015)*. *bloom filter 기반 의 *작은 LFU + 작은 LRU* 의 결합. *메모리 효율 + 적응성 + 단순함* 의 균형. *Caffeine (Java)*, *Cuckoo Cache (DragonflyDB)*, *Memcached 의 *modern segmented LRU* 가 변형 채택.

*Caffeine 사용 예*:

```java
Cache<Long, Product> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofMinutes(10))
    .recordStats()           // 통계 수집 (적중률 측정)
    .build();
```

*recordStats() 없이는 적중률 측정 불가*. *반드시 켜기*.

### 2-5. *어느 정책 을 *언제* 쓰나*

| 워크로드 | 정공 |
|---|---|
| *대체로 균일* + *최근 항목 우대* | LRU |
| *Zipf 분포* + *장기 인기 우대* | LFU 또는 W-TinyLFU |
| *워크로드 변화 큼* | ARC |
| *일반 적 백엔드 캐시* | W-TinyLFU (Caffeine 의 default) |
| *DB page cache* | OS 가 알아서 (LRU 변형) |

*의심 가는 워크로드 가 있다면 — *Caffeine 의 W-TinyLFU 가 *기본 정공*. *2025 년 의 *현대 적 선택*.

---

## 3. *Cache 패턴* — write 가 *진짜 의 결정점*

### 3-1. *Cache-Aside* (= Lazy Loading) — *표준*

```java
public Product getProduct(Long id) {
    Product cached = cache.get(id);
    if (cached != null) return cached;        // hit

    Product fresh = db.findById(id);          // miss → DB
    cache.put(id, fresh);
    return fresh;
}

public void updateProduct(Product p) {
    db.save(p);
    cache.evict(p.getId());                   // write 시 *invalidate*
}
```

*"필요할 때 만 채워 넣고, 변경 시 무효화"*. *Spring 의 `@Cacheable` + `@CacheEvict`* 가 정확히 이 패턴. *가장 단순 + 가장 흔함*.

### 3-2. *Write-Through* — *정합성 강도 ↑*

```java
public void updateProduct(Product p) {
    db.save(p);
    cache.put(p.getId(), p);    // 캐시 도 같이 갱신
}
```

*write 시 캐시 도 동기 갱신*. *읽기 가 항상 *최신 데이터*. *쓰기 의 latency 증가*.

### 3-3. *Write-Back* (= Write-Behind) — *쓰기 가 *비동기**

```java
public void updateProduct(Product p) {
    cache.put(p.getId(), p);
    // db.save 는 *나중* 에 *비동기 배치* 로
}
```

*쓰기 가 *cache 만* — DB 는 *늦게*. *쓰기 latency 극단 적 감소* + *데이터 손실 위험* (캐시 노드 다운 시).

*DB engine 내부 의 *page cache → disk* 도 *write-back* 패턴. *Redis 의 *AOF 비동기 모드* 도 이 정신.

### 3-4. *Read-Through* — *cache 가 *DB 조회 까지 자동**

*캐시 라이브러리 가 *miss 시 DB 자동 조회*. *Hibernate 의 *2 차 캐시* + *EhCache loader*. *코드 단순화*, *추상화 비용*.

---

## 4. *Cache Stampede* — *조용 한 살인자*

```
시점 T: 인기 상품 의 cache 가 *동시에 expire*
        → 10,000 개 의 요청 이 *동시에 *miss*
        → 10,000 회 의 DB 쿼리 *동시 발생*
        → DB *과부하 → 전체 서비스 다운*
```

*인기 키 의 *expire 가 *재앙*. *thundering herd*, *cache stampede* 라 부른다. *조용히 일어나고 거의 항상 *예방 가능*.

### 4-1. *Single-Flight (단일 비행) 패턴*

*같은 키 의 *동시 miss* 가 발생 하면 — *첫 1 명 만 DB 조회*, *나머지는 *그 결과 를 기다림*.

```java
// Caffeine 의 LoadingCache 가 *내장*
LoadingCache<Long, Product> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofMinutes(10))
    .build(id -> productRepository.findById(id).orElseThrow());

// 동시에 1000 요청 → *DB 호출 은 *1 회만*. 나머지 999 는 결과 대기
Product p = cache.get(productId);
```

*Caffeine 의 LoadingCache 가 *자동 으로 single-flight*. *Google Guava Cache 도 동일*. *반드시 이 패턴 을 사용*.

### 4-2. *Randomized TTL — *동시 expire 방지**

```java
// ❌ 모든 키 가 정확히 10 분 후 동시 expire
.expireAfterWrite(Duration.ofMinutes(10))

// ✅ 각 키 가 *9~11 분 사이* 의 *랜덤* 만료
.expireAfter(new Expiry<Long, Product>() {
    public long expireAfterCreate(...) {
        long jitter = ThreadLocalRandom.current().nextLong(-60_000, 60_000);
        return Duration.ofMinutes(10).toNanos() + jitter * 1_000_000;
    }
    // ... update / read 도 비슷
})
```

*expire 가 시간적으로 분산* → *동시 다발 적 miss 가 *시간 차로 흩어짐*.

### 4-3. *Probabilistic Early Expiration*

*"expire 직전 에 *확률 적 으로 *미리* refresh"*. *expire 가 임박한 키 가 *조회 될 때 마다 *작은 확률 로 *DB 미리 조회*. *완전 expire 전 *cache 가 *자체 새로고침*. XFetch 알고리즘.

---

## 5. *분산 캐시* — *consistency hashing*

### 5-1. *Modular Hashing 의 *함정**

```
node = hash(key) % N    where N = cache 노드 수

N = 5 → node 1
노드 추가 (N = 6) → node 3 (다른 노드)
모든 키 의 *분포 가 *완전 재배치*
→ *재배치 동안 *hit ratio = 0*
→ *origin (DB) 로 폭발*
```

*node 추가 / 제거 시 *cache 가 *전체 초기화*. *재앙*.

### 5-2. *Consistency Hashing*

*hash 공간 을 *원 (ring)* 으로 만들고 *각 노드 와 각 키 를 *그 원 위 의 *위치* 에 매핑*. *각 키 는 *원을 따라 *가장 가까운 노드* 가 담당*.

```
node 추가 시 — *추가된 노드 가 담당 하는 작은 구간 의 키만 *재배치*
→ *95% 의 키 는 *그대로 hit*
→ *hit ratio 약간만 감소*
```

*Redis Cluster*, *Memcached 의 *ketama*, *Cassandra 의 *partitioner*, *DynamoDB 의 *internal hashing* 까지 — *모든 분산 시스템 의 *표준*.

*Virtual node 기법* 으로 *부하 의 *불균등 까지 해결*. *각 물리 노드 가 *수 백 개 의 virtual 위치 를 가짐*.

### 5-3. *Redis 의 *cluster slot**

Redis Cluster 는 *16,384 개 의 슬롯* 으로 키 공간 을 분할. *각 노드 가 *일정 구간 의 슬롯* 을 담당. *재배치 = 슬롯 단위*. *consistency hashing 의 *유한 슬롯 버전*.

---

## 6. *측정 도구* — *모르면 못 튜닝*

### 6-1. *Caffeine 의 stats*

```java
CacheStats stats = cache.stats();
double hitRate = stats.hitRate();           // 적중률
double missRate = stats.missRate();         // 미스율
long evictionCount = stats.evictionCount(); // evict 횟수
long loadCount = stats.loadCount();         // 로딩 (miss 후 fetch) 횟수
double avgLoadPenalty = stats.averageLoadPenalty();  // miss 시 평균 비용 (ns)
```

*Micrometer + Prometheus* 와 연동 으로 *자동 메트릭 expose*:

```java
CaffeineCacheMetrics.monitor(meterRegistry, cache, "products-cache");
```

### 6-2. *Redis 의 INFO*

```
> INFO stats
keyspace_hits:1234567
keyspace_misses:54321

hit ratio = 1234567 / (1234567 + 54321) ≈ 95.78%

> INFO memory
used_memory_human:512.00M
maxmemory_human:1.00G

> INFO clients
connected_clients:127
blocked_clients:0
```

*evicted_keys / expired_keys* 메트릭으로 *cache pressure* 평가.

### 6-3. *Linux 의 page cache hit ratio*

```bash
# pcstat 또는 perf
$ perf stat -e cache-references,cache-misses ./your-app
       1,234,567   cache-references
          54,321   cache-misses    # = 4.4% miss

# /proc/meminfo 의 Cached 영역
$ grep Cached /proc/meminfo
Cached:         8123456 kB
```

*DB 의 OS-level page cache* 까지 *측정 대상*. *시스템 전반 의 *층층 cache* 가 *공동 작용*.

---

## 7. *흔한 함정 5 가지*

### 7-1. *적중률 숫자 만 보고 *p99 무시**

*적중률 99% = *1% miss*. *p99 latency = miss 의 latency*. *p99 를 같이 보지 않으면 *상위 1% 사용자 의 비명* 을 못 듣는다.

### 7-2. *모든 데이터 를 *cache 에 넣기**

*잘 안 쓰이는 데이터 까지 캐싱* → *워킹 셋 보다 *훨씬 큰 cache* → *메모리 낭비 + GC 폭발*. *Zipf 분포 의 *꼬리* 까지 욕심 부리면 *손해*.

### 7-3. *Stale data — *변경 후 evict 안 함**

*상품 가격 이 변경* 됐는데 *cache 가 *이전 가격* 을 *5 분 더 보여줌*. *비즈니스 의 *신뢰 손실*. *write 시 evict 가 *반드시 *함수 호출 의 *짝**.

### 7-4. *분산 환경 에서 *각 노드 의 *로컬 캐시 가 *서로 다른 값**

*5 개 의 Spring Boot 인스턴스 가 *각자 Caffeine* — *각자 다른 값 을 보여줌*. *분산 cache (Redis)* 또는 *cache invalidation broadcast* 필요.

### 7-5. *Cache 가 *DB 보다 느림**

*Redis 가 *원격 cluster* + *네트워크 RTT* 가 *DB 의 인덱스 lookup* 보다 *느림* 경우. *측정 없이 도입* 하면 *오히려 성능 저하*. *DB 가 *이미 자기 page cache 로 빠르다면* — *외부 cache 의 *순이익 이 음수*.

---

## 8. *학습 로드맵*

| 단계 | 집중 | 자료 |
|---|---|---|
| 1 | *기본 적중률 / latency 식* | 위의 식 + Caffeine docs |
| 2 | *정책 (LRU / LFU / W-TinyLFU)* | Caffeine 의 [paper](https://github.com/ben-manes/caffeine) |
| 3 | *Cache-aside / Write-through* | Spring Cache abstraction docs |
| 4 | *Stampede 와 single-flight* | Caffeine LoadingCache + XFetch 알고리즘 |
| 5 | *분산 캐시 / consistency hashing* | Redis Cluster docs + DynamoDB 백서 |
| 6 | *OS-level page cache* | *OSTEP* 의 *Persistence* part |

### 8-1. *최소 어휘* 한 줄 정리

- *Hit ratio* — *적중률*. 단순 숫자 가 아니라 *miss 의 *총 비용 의 기댓값*
- *Working set* — *현재 활발히 접근 되는 데이터*. *cache 크기 의 정공 기준*
- *Zipf 분포* — *상위 소수 가 트래픽 대부분*. *현실 의 거의 모든 워크로드*
- *LRU / LFU / W-TinyLFU* — *evict 정책 의 세 흐름*. *기본은 W-TinyLFU*
- *Cache-aside* — *조회 시 만 채움 / 변경 시 evict*. *표준 패턴*
- *Stampede* — *동시 expire → DB 폭주*. *single-flight + jitter 가 해결*
- *Consistency hashing* — *노드 변경 시 *재배치 최소화*. *분산 cache 의 표준*

---

## 마무리 — *캐시 는 *프로그램의 *지름길**

*"There are only two hard things in Computer Science: cache invalidation and naming things."* — Phil Karlton 의 명언. *캐시 의 *효과 는 압도적* 이지만 *그 *정확성 의 비용* 도 압도적*. *원본 (origin) 과 *캐시 가 *어긋나면* — 비즈니스 신뢰 가 무너진다*. *적중률 만 보고 환호 하지 말고 — *invalidation 의 *짝 호출 이 *모든 write 에 같이 있는지* 점검*.

*"가장 빠른 코드 는 *돌지 않는 코드*. 두 번째로 빠른 코드 는 *cache 안에 있는 코드*"* — *우리의 성능 개선 의 *상당 부분이 *호출 자체 를 *없애는* 방향*. 그 *없애는 도구 가 캐시*. 다만 *그 도구를 *잘못 잡으면 *손가락 까지 잘린다* — *측정 + 정책 + 패턴 + 분산 의 *네 가지 가 *세트* 로 갖춰져야 한다*.

기억 할 *세 줄*:

1. *적중률 만 보지 말고 *miss 의 비용 × count* 를 보라*. p99 와 짝.
2. *Working set 보다 *조금 큰* cache + W-TinyLFU* 가 *2025 년 기본 정공*.
3. *Stampede 는 *조용히 일어난다*. *single-flight + jitter* 를 *디폴트* 로.

*캐시 적중률 의 *깊이 를 이해 하면 *서버 성능 의 *80% 가 풀린다*. 어제 [서버 성능 개선 기초](https://myoungsoo7.github.io) 글 의 *DB 80%* 의 *큰 부분 이 *결국 cache 의 활용*. *둘은 한 짝* 이다.
