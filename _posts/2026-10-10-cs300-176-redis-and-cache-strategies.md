---
layout: post
title: "[CS300 #176] Redis 와 캐시 전략 — 빠른 거짓말을 관리하는 법"
date: 2026-10-10 20:56:00 +0900
categories: [cs]
tags: [cs300, database, redis, caching, cache-invalidation]
---

컴퓨터공학 300 주제 시리즈의 176번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

캐시는 비싼 결과를 빠른 저장소에 복사해 두고 재사용하는 것이고, Redis 는 그 용도로 가장 널리 쓰이는 인메모리 키-값 저장소이며, 캐시 전략의 핵심은 "언제 채우고, 언제 버리고, 원본과 얼마나 어긋나도 되는가"를 정하는 일이다.

## 왜 필요한가

상품 상세 페이지를 열 때마다 DB 에서 상품, 가격, 재고, 리뷰 요약을 조인해 가져온다고 하자. 같은 상품을 1초에 수천 명이 본다면 DB 는 같은 계산을 수천 번 반복한다. 결과는 대부분 똑같다. 이 결과를 메모리에 한 번 저장해 두고 돌려주면 DB 부하가 극적으로 줄고 응답도 빨라진다.

하지만 캐시는 원본의 복사본이다. 원본이 바뀌면 캐시는 거짓말을 한다. "컴퓨터 과학에서 어려운 것은 캐시 무효화와 이름 짓기 두 가지뿐"이라는 오래된 농담이 있을 정도다. 캐시를 쓰는 순간 반정규화와 같은 숙제가 생긴다. 이 글은 그 숙제를 다루는 표준적인 방법을 정리한다.

## 핵심 개념

### Redis 의 성격

Redis 는 데이터를 메모리에 두는 키-값 저장소다. 값으로 문자열뿐 아니라 리스트, 해시, 집합, 정렬 집합, 스트림 같은 자료구조를 지원한다. 그래서 단순 캐시를 넘어 순위표(정렬 집합), 속도 제한 카운터(`INCR` + `EXPIRE`), 작업 큐, 분산 락에도 쓰인다.

캐시로 쓸 때 알아야 할 기능 세 가지:

- **만료(TTL)**: `SET key value EX 60` 이나 `EXPIRE key 60` 으로 키에 수명을 준다. 시간이 지나면 키가 사라진다.
- **메모리 상한과 축출 정책**: `maxmemory` 로 상한을 정하고, 넘었을 때 무엇을 버릴지 `maxmemory-policy` 로 정한다. 대표적인 정책은 `noeviction`(쓰기를 거부), `allkeys-lru`(전체 키 중 가장 오래 안 쓴 것), `allkeys-lfu`(가장 적게 쓴 것), `volatile-lru`/`volatile-ttl`(TTL 이 있는 키 중에서) 등이다. Redis 의 LRU 는 정확한 LRU 가 아니라 키 일부를 표본 추출해 근사한다. 공식 문서는 특별한 이유가 없으면 `allkeys-lru` 를 무난한 선택으로 소개한다.
- **영속성**: 주기적 스냅숏(RDB)과 명령 로그(AOF)를 선택하거나 함께 쓸 수 있다. 순수 캐시라면 꺼도 되지만, 재시작 직후 캐시가 비어 DB 로 요청이 몰리는 것을 감수해야 한다.

### 읽기 전략

**캐시 어사이드(cache-aside, lazy loading)** — 가장 흔하다.

```
읽기: 앱 → 캐시 GET ── 적중 ──▶ 반환
                     └─ 미스 ──▶ DB 조회 → 캐시 SET(TTL) → 반환
쓰기: 앱 → DB 갱신 → 캐시 DELETE
```

애플리케이션이 캐시와 DB 를 모두 안다. 실제로 요청된 것만 캐시에 들어가고, 캐시가 죽어도 DB 로 동작한다.

**리드 스루(read-through)** — 캐시 계층이 미스 시 DB 를 직접 조회한다. 애플리케이션은 캐시만 안다. 라이브러리나 프록시가 이 역할을 한다.

### 쓰기 전략

| 전략 | 동작 | 장점 | 단점 |
|---|---|---|---|
| 무효화(쓰기 후 삭제) | DB 갱신 후 캐시 키 삭제 | 단순, 다음 읽기가 최신으로 채움 | 삭제 직후 미스 |
| 라이트 스루 | DB 와 캐시를 함께 갱신 | 캐시가 늘 최신에 가까움 | 쓰기 지연, 안 읽히는 데이터도 캐시 |
| 라이트 비하인드(백) | 캐시에 먼저 쓰고 DB 는 나중에 일괄 | 쓰기 매우 빠름 | 캐시 장애 시 유실 위험 |

캐시 어사이드에서 쓰기 시 "갱신"이 아니라 **삭제**를 권하는 이유가 있다. 두 요청이 동시에 DB 를 갱신하고 각자 캐시를 갱신하면, DB 에는 B 가 마지막인데 캐시에는 A 가 마지막으로 남는 순서 역전이 생길 수 있다. 삭제는 순서가 바뀌어도 결과가 "없음"이라 안전하다. 그래도 "읽기 요청이 옛 값을 DB 에서 읽음 → 쓰기 요청이 DB 갱신·캐시 삭제 → 읽기 요청이 옛 값을 캐시에 SET" 같은 경합은 남는다. 그래서 **TTL 은 항상 건다.** TTL 은 모든 불일치의 상한선이다.

### 세 가지 고전적 장애

| 장애 | 상황 | 대응 |
|---|---|---|
| 캐시 스탬피드 (thundering herd) | 인기 키가 만료되는 순간 수많은 요청이 동시에 DB 로 | 키별 락으로 한 요청만 재계산(single-flight), 만료 전 미리 갱신, TTL 에 무작위 편차 |
| 캐시 관통 (penetration) | 존재하지 않는 키를 반복 요청해 매번 DB 로 | "없음"도 짧은 TTL 로 캐시, 블룸 필터 |
| 캐시 눈사태 (avalanche) | 많은 키가 같은 시각에 만료되거나 캐시 서버가 통째로 다운 | TTL 분산, 캐시 고가용성 구성, DB 앞 속도 제한 |

### 무엇을 캐시할 것인가

- 읽기가 쓰기보다 훨씬 많은 데이터.
- 접근이 치우친 데이터. 상위 일부 키가 요청 대부분을 차지하면 작은 캐시로도 적중률이 높다.
- 조금 늦어도 되는 데이터. 재고 수량처럼 정확해야 하는 값은 캐시에서 판단하지 말고, 최종 확인은 DB 에서 한다.

## 직접 해 보기

TTL 과 LRU 축출을 갖춘 작은 캐시로 캐시 어사이드, 적중률, 스탬피드를 실험한다.

```python
import time, threading, random
from collections import OrderedDict

class TTLLRUCache:
    """Redis 의 maxmemory + allkeys-lru + EXPIRE 를 흉내 낸 작은 캐시."""
    def __init__(self, capacity):
        self.cap, self.d = capacity, OrderedDict()
        self.hits = self.misses = 0
    def get(self, k):
        item = self.d.get(k)
        if item is None or item[1] < time.monotonic():
            self.d.pop(k, None); self.misses += 1
            return None
        self.d.move_to_end(k); self.hits += 1          # 최근 사용으로 갱신
        return item[0]
    def set(self, k, v, ttl):
        self.d[k] = (v, time.monotonic() + ttl); self.d.move_to_end(k)
        if len(self.d) > self.cap:
            self.d.popitem(last=False)                 # 가장 오래 안 쓴 키 축출
    def delete(self, k):
        self.d.pop(k, None)

db_calls = 0
def slow_db_query(product_id):
    global db_calls
    db_calls += 1; time.sleep(0.05)
    return {"id": product_id, "price": 1000 * product_id}

cache = TTLLRUCache(capacity=100)
def get_product(pid):                                  # 캐시 어사이드
    v = cache.get(f"product:{pid}")
    if v is None:
        v = slow_db_query(pid)
        cache.set(f"product:{pid}", v, ttl=60)
    return v

# 1) 치우친 접근(상위 몇 개가 대부분)에서 적중률
random.seed(3)
for _ in range(2000):
    get_product(min(int(random.paretovariate(1.2)), 500))
print(f"적중률 {cache.hits / (cache.hits + cache.misses):.1%}, DB 호출 {db_calls}회")

# 2) 캐시 스탬피드: 인기 키가 만료된 순간 50개 요청이 동시에 DB 로
def stampede(single_flight):
    global db_calls
    db_calls = 0; cache.delete("product:1")
    lock = threading.Lock()
    def worker():
        if cache.get("product:1") is not None:
            return
        if single_flight:
            with lock:                                 # 한 명만 DB 로, 나머지는 기다렸다 캐시에서
                if cache.get("product:1") is None:
                    cache.set("product:1", slow_db_query(1), ttl=60)
        else:
            cache.set("product:1", slow_db_query(1), ttl=60)
    ts = [threading.Thread(target=worker) for _ in range(50)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return db_calls
print("스탬피드 DB 호출:", stampede(False), "→ single-flight:", stampede(True))
```

결과:

```
적중률 97.2%, DB 호출 55회
스탬피드 DB 호출: 50 → single-flight: 1
```

파레토 분포로 치우친 2,000번의 요청 중 DB 까지 간 것은 서로 다른 상품 수인 55번뿐이다. 이 실험에서는 서로 다른 키가 용량(100)보다 적어 축출이 일어나지 않았다. `capacity` 를 10 으로 줄이면 축출이 생기며 적중률이 떨어지는 것을 볼 수 있다. 스탬피드 실험에서는 락 없이 50개 요청이 모두 DB 를 때렸고, single-flight 를 쓰자 1번으로 줄었다. 분산 환경에서는 이 락을 Redis 의 `SET key value NX PX 3000` 같은 원자 명령으로 구현한다. 다만 분산 락은 만료와 시계 문제 때문에 정확성 보장용이 아니라 "중복 작업 줄이기" 용도로 쓰는 것이 안전하다.

## 현업에서는

- **캐시 키 설계**: `product:{id}:v3` 처럼 객체 타입, ID, 스키마 버전을 넣는다. 캐시 값의 형식을 바꾸는 배포를 할 때 버전만 올리면 옛 형식과 섞이지 않는다.
- **적중률과 메모리 지표**: Redis `INFO` 의 `keyspace_hits`, `keyspace_misses`, `evicted_keys`, `used_memory` 를 모니터링한다. 축출이 갑자기 늘면 메모리가 부족하거나 키 TTL 이 빠진 것이다.
- **큰 키와 느린 명령**: 수백만 원소를 가진 해시 하나, `KEYS *` 같은 전체 스캔 명령은 Redis 전체를 멈추게 할 수 있다. 운영에서 키 열람은 `SCAN` 으로 한다.
- **캐시가 DB 의 용량 계획을 숨긴다**: 캐시 적중률이 95% 일 때 DB 는 전체 트래픽의 5% 만 본다. 캐시가 재시작되어 비면 DB 는 갑자기 20배 부하를 받는다. 캐시 없이도 버틸 수 있는지, 아니면 워밍업 절차가 있는지 확인해 둔다.

## 확인 문제

1. 캐시 어사이드에서 쓰기 시 캐시를 "갱신"하지 않고 "삭제"하는 이유는?
2. 캐시 무효화를 잘 해도 TTL 을 걸어야 하는 이유는?
3. 스탬피드, 관통, 눈사태를 각각 한 문장으로 구분하라.
4. `allkeys-lru` 와 `volatile-lru` 의 차이는? 모든 키에 TTL 이 없을 때 `volatile-lru` 는 어떻게 동작하겠는가?
5. 재고 수량을 캐시에서 읽어 "구매 가능" 여부를 최종 판단하면 안 되는 이유는?

### 풀이

1. 동시 갱신 순서가 뒤바뀌면 캐시에 옛 값이 남을 수 있지만, 삭제는 어느 순서로 일어나도 "없음"이 되어 다음 읽기가 최신 값으로 채운다.
2. 경합, 버그, 누락된 무효화 경로로 생긴 불일치가 영원히 남지 않도록 상한을 두기 위해서다.
3. 스탬피드: 인기 키 하나의 만료에 동시 요청이 몰림. 관통: 없는 키 요청이 매번 DB 로 감. 눈사태: 대량 키 동시 만료나 캐시 전체 장애로 DB 가 한꺼번에 맞음.
4. `allkeys-lru` 는 모든 키에서, `volatile-lru` 는 TTL 이 설정된 키에서만 축출 대상을 고른다. TTL 키가 없으면 축출할 키가 없어 `noeviction` 처럼 쓰기가 실패한다.
5. 캐시는 원본보다 늦을 수 있어 실제 재고와 어긋날 수 있다. 최종 차감은 DB 의 원자적 갱신으로 확인해야 한다.

## 더 읽을거리 (References)

- Redis 공식 문서, [Key eviction](https://redis.io/docs/latest/develop/reference/eviction/)
- Redis 공식 문서, [EXPIRE](https://redis.io/docs/latest/commands/expire/), [SET](https://redis.io/docs/latest/commands/set/)
- Redis 공식 문서, [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- AWS Whitepaper, [Database Caching Strategies Using Redis — Caching patterns](https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-patterns.html)
