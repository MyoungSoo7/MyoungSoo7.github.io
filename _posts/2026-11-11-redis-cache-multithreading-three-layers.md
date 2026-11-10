---
layout: post
title: "Redis 캐시와 멀티스레딩 — 서버·클라이언트·애플리케이션, 세 층에서 '동시에'가 뜻하는 것이 다르다"
date: 2026-11-11 00:01:54 +0900
categories: [backend, cache]
tags: [redis, cache, multithreading, lettuce, spring-cache, caffeine, cache-stampede, concurrency]
---

> **검증 범위.** Redis 서버 동작은 redis.io 공식 문서와 `redis.conf` 원문, 클라이언트 동작은 Lettuce 공식 레퍼런스, Spring 동작은 Spring Framework·Spring Data Redis 공식 레퍼런스와 **GitHub 소스(2.7.x / 3.3.x / 3.4.x / 3.5.x / main 브랜치)를 직접 열어** 확인했다. 성능 수치는 인용하지 않는다(공식 문서가 직접 쓴 대략치 두 개만 출처와 함께 인용). "~일 것이다"로 표시한 부분은 내 추론이다.

"Redis 는 싱글 스레드다", "Lettuce 는 스레드 안전하다", "`@Cacheable(sync = true)` 를 붙이면 스탬피드가 막힌다" — 셋 다 반만 맞다. 각각 **다른 층의 '동시성'** 을 말하고 있어서다. 이 글은 요청 하나가 지나가는 세 층을 따로 떼어 본다.

| 층 | 무엇이 동시에 일어나나 | 직렬화 지점 |
|---|---|---|
| ① Redis 서버 | 수많은 클라이언트의 명령 | 명령 실행 스레드 하나 |
| ② 클라이언트(Lettuce) | 앱의 여러 스레드가 연결 하나를 공유 | 커넥션 위 명령 순서 |
| ③ 애플리케이션 | 같은 키에 대한 동시 캐시 미스 | **기본값으로는 없음** |

캐시 적중률·정책·스탬피드의 일반론은 [적중률 심화 글]({% post_url 2026-06-10-cache-hit-ratio-deep-dive-working-set-policies-stampede %})에, 멀티스레드 Redis 대안은 [KiviDB 리뷰]({% post_url 2026-11-10-kividb-multithreaded-redis-alternative-review %})에 있다. 여기서는 **스레드가 여럿일 때 어디서 무엇이 꼬이는가**만 본다.

## ① 서버 — 명령은 한 줄로 실행되고, I/O 만 스레드로 나뉜다

공식 지연 진단 문서는 Redis 를 "대체로(mostly) 싱글 스레드"라고 설명한다. 프로세스 하나가 멀티플렉싱으로 모든 요청을 받고, **한 시점에 요청 하나만 처리하므로 요청은 순차적으로 처리된다.** 2.4 부터 디스크 I/O 같은 느린 작업에 백그라운드 스레드를 쓰지만 "모든 요청을 스레드 하나로 처리한다는 사실은 바뀌지 않는다"([Diagnosing latency issues](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)).

`redis.conf` 의 THREADED I/O 절은 그 위에 하나를 더한다. `io-threads` 를 켜면 클라이언트 소켓의 **읽기·쓰기와 프로토콜 파싱**을 별도 I/O 스레드가 맡는다. 기본은 꺼져 있고, 4코어 이상에서 코어 하나는 남겨 두고, Redis 가 CPU 를 상당히 쓰는 실제 성능 문제가 있을 때만 켜라고 권한다(4코어면 3, 8코어면 7). `redis-benchmark` 로 효과를 볼 때는 벤치마크 쪽도 `--threads` 로 맞추지 않으면 개선이 안 보인다고 적혀 있다([redis.conf](https://raw.githubusercontent.com/redis/redis/unstable/redis.conf)).

멀티스레딩 관점에서 이게 뜻하는 바는 두 가지다.

**좋은 점 — 명령 하나는 원자적이다.** `INCR`, `SET key v NX`, `HINCRBY` 는 다른 클라이언트의 명령과 섞이지 않는다. `MULTI/EXEC` 트랜잭션은 "모든 명령이 직렬화되어 순차 실행되고, 다른 클라이언트의 요청이 그 중간에 끼어들지 않는다"([Transactions](https://redis.io/docs/latest/develop/using-commands/transactions/)). Lua 스크립트는 원자 실행이 보장되고, 실행되는 동안 **서버의 다른 모든 활동이 막힌다**([Scripting with Lua](https://redis.io/docs/latest/develop/programmability/eval-intro/)).

**나쁜 점 — 느린 명령 하나가 모두를 세운다.** 같은 문서가 대표 범인으로 프로덕션의 `KEYS` 를 꼽고 `SCAN` 계열을 권한다. 큰 집합의 교집합, 긴 Lua 스크립트도 같다. I/O 스레드는 소켓 읽기·쓰기를 나눌 뿐이라 이 문제를 풀지 못한다(내 추론: 실행 단계는 여전히 하나이므로).

> 함정 하나. Spring Data Redis 의 `RedisCache` 는 캐시 전체 삭제(`clean`)에 **기본적으로 `KEYS` + `DEL`** 을 쓴다. 공식 문서가 키가 많으면 성능 문제가 될 수 있다며 `BatchStrategies.scan(1000)` 같은 SCAN 기반 전략을 권한다([Spring Data Redis — Redis Cache](https://docs.spring.io/spring-data/redis/reference/redis/redis-cache.html)). `@CacheEvict(allEntries = true)` 한 줄이 서버 전체를 세울 수 있다는 뜻이다.

## ② 클라이언트 — 연결 하나를 스레드 여럿이 나눠 쓴다

Lettuce 레퍼런스의 첫 문장은 "스레드 안전한 Redis 클라이언트"이고, 바로 단서가 붙는다. **`BLPOP` 같은 블로킹 명령과 `MULTI/EXEC` 같은 트랜잭션을 피한다면** 여러 스레드가 연결 하나를 공유해도 된다([Lettuce Reference](https://redis.github.io/lettuce/)).

왜 연결 하나로 충분한가 — 커넥션 풀링 문서의 설명이 ①과 맞물린다. 모든 Redis 사용자 연산은 서버에서 싱글 스레드로 실행되므로, **연결을 여러 개 쓴다고 애플리케이션 성능이 좋아지지 않는다**([Connection Pooling](https://redis.github.io/lettuce/advanced-usage/connection-pooling/)). Lettuce 는 netty 위에서 쓰기와 읽기를 분리해, 한 스레드가 응답을 기다리는 동안 다른 스레드가 같은 연결로 다음 명령을 보낸다. 동기 API 의 블로킹은 "그 스레드 관점"일 뿐 전역 블로킹이 아니다([Pipelining](https://redis.github.io/lettuce/advanced-usage/pipelining/)).

공유 연결에서 깨지는 세 가지:

1. **트랜잭션.** "한 연결을 여러 스레드가 쓸 때 트랜잭션은 외부 동기화가 필요하다. Lettuce 자신은 트랜잭션/비트랜잭션 호출을 동기화하지 않는다"([Transactions/Multi](https://redis.github.io/lettuce/user-guide/transactions-multi/)). A 스레드가 `MULTI` 를 보낸 사이 B 스레드의 `GET` 이 같은 연결로 들어가면, B 의 명령이 A 의 트랜잭션 큐에 섞인다(내 추론: Redis 는 연결 단위로 `MULTI` 상태를 갖기 때문).
2. **블로킹 명령.** 공유 연결에서 `BLPOP` 을 부르면 그 명령이 돌아올 때까지 **그 연결의 모든 호출**이 막힌다(Pipelining 문서).
3. **auto-flush 끄기.** `setAutoFlushCommands(false)` 는 연결 단위 상태라 공유 연결의 모든 스레드에 보인다. 문서는 단일 스레드 대량 적재 외에는 쓰지 말라고 경고한다.

그래서 풀링이 필요한 경우는 좁다. 문서 표현으로 "블로킹 연산은 보통 전용 연결을 가진 워커 스레드와 함께 쓰이고, 트랜잭션이 동적 풀링의 대표 사례"다. 원자성이 목적이라면 대개 트랜잭션보다 **명령 하나(`SET NX`, `INCR`) 또는 Lua 스크립트**가 공유 연결에서도 안전하다(내 추론: 둘 다 연결 상태를 남기지 않는 단일 요청이므로).

## ③ 애플리케이션 — 같은 키를 동시에 놓치면 누가 DB 에 가나

①과 ②가 아무리 안전해도, 앱 코드의 **check-then-act** 는 보호받지 못한다.

```java
Product p = redis.get(key);          // 스레드 100개가 동시에 null 을 본다
if (p == null) {
    p = repository.findById(id);     // → DB 쿼리 100번
    redis.set(key, p, ttl);          // → 같은 값을 100번 쓴다
}
```

`GET` 과 `SET` 은 각각 원자적이지만 그 사이 간격은 아니다. 인기 키의 TTL 이 만료되는 순간 이 간격으로 요청이 몰리는 것이 캐시 스탬피드다. Spring 레퍼런스도 같은 말을 한다. 멀티스레드 환경에서 같은 인자로 동시 호출이 일어날 수 있고, "**기본적으로 캐시 추상화는 아무것도 잠그지 않아** 같은 값이 여러 번 계산될 수 있다". 이를 위해 `@Cacheable(sync = true)` 가 있고, 이 기능은 선택 사항이라 캐시 라이브러리가 지원하지 않을 수 있다고 덧붙인다([Spring Framework — Synchronized Caching](https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html#cache-annotations-cacheable-synchronized)).

### `sync = true` 를 Redis 에 붙이면 실제로 무슨 일이 일어나나 — 버전마다 다르다

`sync = true` 는 `Cache.get(key, Callable)` 호출로 바뀌고, 무엇을 잠글지는 **캐시 구현체**가 정한다. Spring Data Redis 의 `RedisCache` 소스를 브랜치별로 열어 보면 이렇다.

| Spring Data Redis | `get(key, Callable)` 의 동기화 | 범위 |
|---|---|---|
| 2.7.x | `private synchronized … getSynchronized(…)` | **JVM 하나 안, 캐시 인스턴스 전체** |
| 3.3.x | 캐시 인스턴스당 `ReentrantLock` 하나 | **JVM 하나 안, 캐시 인스턴스 전체** |
| 3.4.0 이후(3.5.x, main) | 앱 쪽 락 제거 → `RedisCacheWriter` 에 위임 | **기본 writer 는 락 없음** / locking writer 면 Redis 의 캐시 단위 락 |

3.4 의 변경은 이슈 [#2890](https://github.com/spring-projects/spring-data-redis/issues/2890) "`RedisCache.get(Object, Callable)` 이 개별 키가 아니라 캐시 전체에 동기화한다"에서 시작해 커밋 `06bbd3d`("Use Redis locking for value retrieval synchronization", 마일스톤 3.4 M1)로 반영됐다. 지금의 `DefaultRedisCacheWriter#get(…, valueLoader, …)` 는 locking writer 일 때만 `SET <캐시명>~lock "" NX`(lock TTL 을 설정했다면 만료 포함)로 락을 잡고 → 다시 조회 → 없으면 로더 실행 → 저장 → 락 해제를 한다. **기본값인 non-locking writer 에서는 조회 후 없으면 그냥 로더를 실행한다.**

여기서 나오는 결론:

- **3.4 이상 + 기본 설정**이면 `sync = true` 를 붙여도 동시 미스가 **막히지 않는다**(소스 기준 내 해석). 문서에도 `RedisCacheManager` 의 기본 writer 는 lock-free 라고 적혀 있다.
- `RedisCacheWriter.lockingRedisCacheWriter(…)` 로 바꾸면 여러 인스턴스에 걸쳐 막히지만, 공식 문서대로 **락은 엔트리가 아니라 캐시 단위**다. 서로 다른 키의 미스도 한 줄로 서고, 락 키 확인용 요청과 대기 시간이 추가된다.
- 3.3 이하에서는 JVM 안에서만, 그것도 캐시 전체에 걸린다. 파드가 10개면 동시 미스는 최대 10번 DB 로 간다.

어느 쪽이든 "sync=true = 키별 분산 single-flight" 는 아니다. 업그레이드 노트에서 놓치기 쉬운 부분이라 버전을 먼저 확인할 것을 권한다.

### 실무 조합 — 로컬 키별 single-flight + 리모트 캐시

Caffeine 은 키 단위 원자 계산을 직접 제공한다. `cache.get(key, k -> value)` 는 없으면 **원자적으로 계산해 넣고**, 있으면 기존 값을 돌려준다([Caffeine — Population](https://github.com/ben-manes/caffeine/wiki/Population)). `refreshAfterWrite` 의 refresh 는 새 값을 비동기로 읽어 오는 동안 **기존 값을 계속 돌려주고**, 진행 중인 refresh 요청은 중복 제거된다. 실패하면 기존 값을 유지한다([Caffeine — Refresh](https://github.com/ben-manes/caffeine/wiki/Refresh)). 만료(evict)는 다음 조회가 새 값을 기다리게 만들지만, refresh 는 그렇지 않다.

그래서 흔한 구성(내 정리)은:

1. **L1 Caffeine**(키별 원자 로드, refresh-ahead) → 한 JVM 안의 동시 미스를 1회로 줄인다.
2. **L2 Redis** → 인스턴스 간 공유. L1 미스 때만 간다.
3. 인스턴스 수만큼의 동시 미스도 감당이 안 되는 소수의 핫 키만 **키 단위 분산 락**(`SET lock:<key> <token> NX PX`, 해제는 토큰 비교 Lua)이나 TTL 지터·사전 갱신으로 따로 다룬다. 분산 락의 구현과 함정은 [Redis 분산 락 글]({% post_url 2026-05-04-redis-distributed-lock %})에 있다.

로컬과 리모트의 일관성 트레이드오프는 [로컬 vs 리모트 캐시]({% post_url 2026-06-10-local-vs-remote-cache %})를 참고.

## 체크리스트

1. **서버**: 프로덕션에서 `KEYS` 금지, `RedisCacheManager` 는 SCAN 배치 전략, 긴 Lua 금지. `io-threads` 는 Redis CPU 가 실제로 병목일 때만.
2. **클라이언트**: Lettuce 는 공유 연결 하나가 기본. 트랜잭션·블로킹 명령을 쓰는 코드만 전용 연결이나 풀을 쓴다. 원자성은 가능하면 단일 명령이나 Lua 로.
3. **애플리케이션**: `GET → 없으면 → SET` 은 원자적이지 않다. `sync = true` 의 실제 의미는 **Spring Data Redis 버전과 cache writer 종류**로 정해진다 — 3.4 이상 기본값이면 아무것도 막지 않는다.
4. 핫 키는 L1 Caffeine(키별 원자 로드 + refresh) 앞단으로 줄이고, 남는 것만 분산 락으로 다룬다.

## References

1. Redis, *Diagnosing latency issues* (single threaded nature, slow commands, `KEYS`). <https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/>
2. Redis, `redis.conf` — THREADED I/O 절 (`io-threads`). <https://raw.githubusercontent.com/redis/redis/unstable/redis.conf>
3. Redis, *Transactions*. <https://redis.io/docs/latest/develop/using-commands/transactions/>
4. Redis, *Scripting with Lua*. <https://redis.io/docs/latest/develop/programmability/eval-intro/>
5. Lettuce Reference Guide — 개요 · *Connection Pooling* · *Pipelining* · *Transactions/Multi*. <https://redis.github.io/lettuce/>
6. Spring Framework Reference, *Declarative Annotation-based Caching* — Synchronized Caching. <https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html>
7. Spring Data Redis Reference, *Redis Cache* (lock-free 기본 writer, 캐시 단위 락, `KEYS`/SCAN 전략). <https://docs.spring.io/spring-data/redis/reference/redis/redis-cache.html>
8. spring-data-redis 소스 — `RedisCache.java`(2.7.x, 3.3.x, 3.4.x, main), `DefaultRedisCacheWriter.java`(main), 이슈 #2890, 커밋 06bbd3d. <https://github.com/spring-projects/spring-data-redis>
9. Caffeine Wiki, *Population* · *Refresh*. <https://github.com/ben-manes/caffeine/wiki>
