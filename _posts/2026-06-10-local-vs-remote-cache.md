---
layout: post
title: "백엔드 개발자가 알아야 할 *로컬 캐시 vs 리모트 캐시* — 언제 무엇을 *왜*"
date: 2026-06-10 17:30:00 +0900
categories: [backend, performance, caching]
tags: [cache, local-cache, remote-cache, redis, caffeine, ehcache, performance, throughput, latency]
---

> *느린 시스템* 의 *80%* 가 *적절한 캐시* 로 *극적 개선* 된다. 그만큼 *캐시가 중요* 하다.
> 그런데 *어떤 캐시를 *어디에* 두는가* — 그 결정이 *나중에 더 큰 *복잡도* 가 된다.
> 한 잘못된 캐시 결정이 *수개월의 *디버깅 비용* 을 만들 수 있다. 이 글은 그 결정을 위한 정리다.

---

## TL;DR

| 항목 | 로컬 캐시 (in-process) | 리모트 캐시 (Redis 등) |
|------|------------------------|-------------------------|
| **응답시간** | ~10 ns ~ 1 µs | ~0.5 ms ~ 2 ms |
| **용량** | 인스턴스 RAM 한도 | 클러스터 합계 (수십 GB ~ TB) |
| **공유** | 인스턴스 *별로 *독립* | 모든 앱 *공유* |
| **일관성** | *각 인스턴스마다 *다름* 가능 | *전 인스턴스 동일* |
| **장애 영향** | 인스턴스 죽으면 *그 인스턴스만 손실* | 캐시 노드 죽으면 *전 시스템 영향* |
| **운영 비용** | *없음* (라이브러리만) | *별도 클러스터 운영* |
| **TTL / Eviction** | 단순 (Caffeine 등) | LRU / LFU / 만료 풍부 |
| **대표 라이브러리** | Caffeine, Ehcache, Guava | Redis, Memcached, Hazelcast |

*요약 한 줄* :

> *로컬 = *빠르고 단순하지만 *안 공유** / *리모트 = *공유되지만 *네트워크 hop 비용** / 대부분 시스템은 *둘 다* 가 답.

---

## 1. *왜 캐시인가*

*하드웨어 layer 간 *속도 격차* — 9년차 백엔드의 *상수* :

```
L1 cache    ~ 1   ns
RAM         ~ 100 ns
SSD         ~ 100 µs
LAN 1ms     ~ 1   ms
DB query    ~ 5   ms ~ 100 ms (인덱스 / join 의존)
원격 API    ~ 50  ms ~ 300 ms
```

이 격차 위에서 — *DB 한 번 호출* 안 해도 되는 응답이 *RAM* 으로 *5,000~50,000 배 빨라진다*. 그게 *캐시 의 *마법*.

캐시는 *시간 / 자원 * 의 비대칭 trade-off — *RAM 100MB 추가* 로 *DB CPU 80% 절감* 같은 거. 거의 *공짜 점심* 에 가까움.

> 단 — *Phil Karlton* 의 유명한 말 :
> *"컴퓨터 과학에서 *어려운 두 가지 — *캐시 무효화* 와 *이름 짓기**."

캐시 *도입* 은 쉽다. *언제 *비우고* / *얼마나 보관* / *어떻게 *최신성 유지** 가 *진짜 어려움*. 이 글의 후반에 다룬다.

---

## 2. **로컬 캐시 (Local / In-Process Cache)**

### 정의

*애플리케이션 프로세스 *내부* 의 *메모리* 에 *직접 저장*. *별도 서버 없음*.

대표 :
- **Caffeine** (Java) — *현대 표준*. *최적 LRU / TinyLFU* 정책.
- **Ehcache** — Spring Boot 의 *흔한 선택*. 단순.
- **Guava Cache** (Java) — 구글, *옛 강자*. Caffeine 으로 점점 대체.
- **node-cache / lru-cache** (Node) — 가볍게.
- **functools.lru_cache** (Python) — 데코레이터.

### 강점

- ***응답시간이 *압도적*** — *수 나노초 ~ 수 마이크로초*. *RAM 직접 접근*.
- ***네트워크 hop 없음*** — *예외 / 타임아웃 / DNS / TLS handshake* 의 *모든 비용 0*.
- ***운영 부담 0*** — *별도 서버 없음*. *모니터링 / 백업 / 복제 없음*.
- ***GC 와 *함께 *작동** — 캐시도 *프로세스의 *일부*. *메모리 한계* 가 *명확*.

### 약점

- ***인스턴스마다 *별도 *상태*** — *N 대 서버에 *N 개의 캐시 사본*. *데이터 일관성 부재*.
- ***인스턴스 재시작 = 캐시 전체 소실*** — *cold start* 시 *모든 요청이 DB 까지*. *쓰러질 위험*.
- ***확장 불가*** — 단일 프로세스 RAM 한도. *전 사용자 데이터 캐싱* 불가.

---

## 3. **리모트 캐시 (Remote / Distributed Cache)**

### 정의

*별도 서버 (또는 클러스터)* 에 캐시 데이터 저장. *애플리케이션은 *네트워크 호출* 로 접근.

대표 :
- **Redis** — *현대 거의 표준*. *데이터 구조 풍부* (string, hash, list, set, zset, stream, geospatial). *Cluster / Sentinel*.
- **Memcached** — *가볍고 단순*. *key-value 만*. *대규모 트래픽 절제 캐시* 에 강함.
- **Hazelcast** — *Java 친화 분산 컴퓨팅*.
- **AWS ElastiCache / Cloud Memorystore** — *클라우드 매니지드*.

### 강점

- ***모든 인스턴스 *공유*** — *서버 1 / 서버 2 / 서버 3* 가 *같은 데이터* 봄. *일관성 가능*.
- ***인스턴스 재시작 무관*** — *캐시 살아있음*. *cold start 없음*.
- ***대용량*** — *수십 GB ~ TB* 까지 가능 (cluster).
- ***풍부한 데이터 구조*** — Redis 의 zset 으로 *랭킹*, stream 으로 *event*, geospatial 로 *위치 기반*. *DB 의 일부 대체*.
- ***pub/sub*** — *cache invalidation broadcasting* 등 활용.

### 약점

- ***네트워크 hop*** — *0.5 ms ~ 2 ms* 의 *최소 latency*. *로컬 캐시 대비 *수천 배 느림*.
- ***별도 운영*** — *클러스터 / replication / monitoring / backup*. *수 시간의 *주간 운영 비용*.
- ***장애 영향 크다*** — *캐시 노드 다운* → *전 시스템에 *thundering herd 위험*.
- ***serialization 비용*** — *객체 → bytes 변환* 의 *CPU + bytes 비용*. *큰 객체* 의 캐싱은 *주의*.
- ***네트워크 대역폭 한계*** — *큰 객체 N 번/초* 면 *Gbps 단위 트래픽*.

---

## 4. *둘의 *직관적 비교*

| 차원 | 로컬 캐시 | 리모트 캐시 |
|------|-----------|-------------|
| 응답시간 | ~ 100 ns | ~ 1 ms |
| 비교 비율 | 1 배 | *10,000 배 느림* |
| 용량 | *인스턴스 RAM 의 *일부* (예: 200MB)* | *수십 GB ~ TB* |
| 공유 | *각 인스턴스 *독립* | *전 인스턴스 *공유* |
| 일관성 | *불가능 (각자 다름)* | *가능 (단 race condition 주의)* |
| 운영 | *0* | *클러스터 운영 필요* |
| 장애 시 | *해당 인스턴스 만 *cold* | *전체 *thundering herd* 위험* |

이 표가 **결정의 *출발점*. 그러나 *대부분 시스템은 *둘 다* 가 답** 이다.

---

## 5. *Cache Pattern* — 5 가지 표준

### 5.1. Cache-Aside (Look-Aside)

```
1. 앱 → 캐시 조회 → hit 면 끝
2. miss → DB 조회 → 캐시 저장 → 반환
```

*가장 흔한 패턴*. 단순. 단 *cache miss 폭증* 시 *DB 폭주*.

### 5.2. Write-Through

```
write 시 :
1. 앱 → 캐시 갱신
2. 앱 → DB 갱신
3. 둘 다 성공해야 응답
```

*캐시와 DB *일관성 강함*. 단 *write 응답시간 ↑*.

### 5.3. Write-Behind (Write-Back)

```
write 시 :
1. 앱 → 캐시 갱신 → 즉시 응답
2. background → DB 비동기 갱신
```

*응답시간 최소*. 단 *캐시 노드 죽으면 *데이터 손실 위험*.

### 5.4. Refresh-Ahead

```
TTL 만료 *전에 *백그라운드 *미리 갱신*
사용자는 *항상 hot cache* 봄
```

*응답시간 최소* + *cold start 없음*. 단 *불필요한 갱신* 도 발생.

### 5.5. Read-Through

```
앱 → 캐시 라이브러리 호출
   캐시 라이브러리 → miss 시 DB 자동 조회 + 캐시 저장
```

*Cache-aside 의 *추상화*. *앱 코드 깔끔*. Caffeine, Spring Cache 의 패턴.

---

## 6. *Cache Invalidation* — *진짜 어려운* 문제

캐시의 *진짜 어려움* :

> *언제 / 어떻게 *오래된 데이터* 를 *비울지*.*

### 전략

1. **TTL (Time-To-Live)** — *N 초 후 자동 만료*. *가장 단순*. *최신성과 cache hit 의 trade-off*.
2. **Explicit Invalidation** — *write 시 *해당 key *직접 삭제*. *정확*. 단 *모든 write 경로* 가 *invalidation 책임* 짐.
3. **Pub/Sub Invalidation** — *write 후 *publish*, 모든 인스턴스가 *subscribe 로 받아 *로컬 캐시 비움*. *분산 시스템에 *유용*.
4. **Versioned Key** — *key 에 *버전* 포함* (`user:123:v5`). *데이터 변경 → 버전 ↑ → 옛 key 자연 만료*.
5. **Probabilistic Early Expiration** — *TTL 임박 시 *일부 요청만* 새로 갱신*. *thundering herd 방지*.

### *로컬 캐시 의 *진짜 어려움**

리모트 캐시는 *공유 상태* 라 *한 곳 비우면 끝*. 로컬 캐시는 *N 개 인스턴스 *각자* 비워야 함*. *Pub/Sub 또는 *Versioned key* 가 *필수* 패턴.

---

## 7. **다층 캐시 (L1 Local + L2 Remote)** — *현실의 *조합*

대부분 *대규모 백엔드* 의 표준 :

```
요청 → L1 (Caffeine local) → hit 면 끝 (100ns)
                            ↓ miss
                        L2 (Redis remote) → hit 면 끝 (1ms)
                            ↓ miss
                        DB                  → 100ms ~
```

이 *3 단계* 에서 :

- *L1 hit률 80%* — *대부분 요청 *서버 안 떠남*
- *L2 hit률 18%* — *남은 요청 *대부분 1ms 안*
- *DB hit 2%* — *진짜 새 데이터 만*

→ *평균 응답시간* :
*0.8 × 100ns + 0.18 × 1ms + 0.02 × 100ms = ~0.2ms + 2ms = ~2.2ms*

*DB 직접* 이었으면 *100ms* — *50 배 개선*.

### 다층 캐시의 *주의점*

- *L1 invalidation 이 *복잡* — *각 인스턴스* 의 L1 을 *모두 비워야* 함. *Pub/Sub 패턴* 권장.
- *L1 stale 시 *L2 와 *L1 불일치* — *최신성 요구* 가 *높은 데이터* 엔 L1 *짧은 TTL*.
- *L2 가 *모두 hit 되도록 *warm-up*** — *cold start* 시 *L2 미리 채움*.

---

## 8. *결정 가이드* — *언제 무엇을*

### *로컬 캐시 만* 으로 충분한 경우

- *읽기 위주, 변경 거의 없음* — *설정값, 환율, 카테고리 목록*
- *데이터가 *작다* (< 100MB)*
- *불일치 허용* — *몇 초 stale 도 OK*
- *팀 / 운영 자원 제한*

### *리모트 캐시* 가 필요한 경우

- *전 인스턴스 *공유 데이터** — *세션, 카트, rate limit counter*
- *큰 데이터* — *전체 사용자 프로필 (TB 단위)*
- *분산 락 / 메시지 큐 / pub-sub* — Redis 의 부가 능력
- *재시작 후 *cold start 회피*

### *둘 다* 가 필요한 경우 (대부분)

- *대용량 트래픽 + *대용량 데이터*
- *읽기 압도적*
- *복잡한 마이크로서비스 환경*
- *글로벌 분산 / 멀티 리전*

---

## 9. *흔한 함정* 7가지

1. ***모든 걸 캐시*** — *write 가 많은 데이터* 의 캐시는 *invalidation 비용 > 캐시 이득*.
2. ***TTL 너무 김*** — *오래된 데이터* 가 *사용자에게 *손실*.
3. ***TTL 너무 짧음*** — *캐시 의 의미가 *없음*. DB 부담 *그대로*.
4. ***thundering herd 무시*** — *대량 key 가 *동시 만료* → *DB 폭주*. *probabilistic early refresh* 또는 *jitter* 필요.
5. ***hot key 무시*** — *극도로 인기 key* 가 *single Redis node 부하 집중*. *local cache 1 단계* 로 분산.
6. ***로컬 캐시 의 *invalidation 무시*** — *N 인스턴스 *각자 stale* → *사용자마다 *다른 결과*.
7. ***serialization 비용 무시*** — *큰 객체 (100KB+)* 의 Redis 캐싱 — *직렬화 비용 > DB 호출 비용* 가능.

---

## 10. *모니터링* — *캐시는 *측정해야 *의미*

```
필수 지표 :
- Cache hit ratio  (목표 90%+, 못 미치면 *TTL / 키 설계* 재검토)
- Cache size       (메모리 사용량)
- Eviction count   (너무 많으면 *용량 부족*)
- Operation latency (P99, P999)
- Errors           (timeout, connection failure)
```

Caffeine 의 *built-in metrics* + Redis 의 `INFO` + Prometheus exporter — *기본 stack*.

> *측정 없는 캐시* 는 *최적화 가설*. *측정 있는 캐시* 가 *진짜 성능 자산*.

---

## 11. *내 경험* — *2 단계 캐시 + Pub/Sub*

본인이 운영하는 *Spring Boot MSA* 의 패턴 :

```
L1 : Caffeine
   - 자주 읽는 *설정 / 카테고리*
   - TTL 5분
   - max size 1만 개
   - hit ratio ~ 95%

L2 : Redis Cluster
   - 세션 / 사용자 권한 / 동시 사용자 카운터
   - TTL 30분
   - max memory 8GB
   - hit ratio ~ 88%

Invalidation :
   - admin 이 *카테고리 변경* → Redis pub/sub publish
   - 모든 인스턴스의 Caffeine 이 해당 key 삭제
   - 다음 요청 → DB → 새 데이터로 갱신
```

이 패턴이 *대부분 시스템 에 *적정*. *복잡도 vs 성능* 의 *균형점*.

---

## 12. 마치며

> *캐시는 *공짜 점심에 가장 가까운 *백엔드 도구*. 그러나 *틀리게 쓰면 *디버깅 지옥*. 그래서 *결정 전에 *원리를* 이해* 하는 것* 이 *시간 절약*.

3 줄 요약 :

1. ***로컬 + 리모트 *둘 다 *써라*** — *대부분 시스템에 *2 단계 캐시 가 *기본*.
2. ***Invalidation 부터 *설계* 하라*** — *TTL 만 으로는 부족*. *명시적 invalidation 패턴* 필요.
3. ***측정* 안 하면 *모른다*** — *hit ratio / eviction / latency* 를 *Prometheus 로 *항상 추적*.

다음 글 — *Cache Stampede / Thundering Herd / Hot Partition* — *대규모 트래픽 시 *캐시 의 *3 대 함정*. 같은 시리즈로 이어집니다.

---

> 본 글은 *9년차 백엔드 운영 회고*. *권장은 *내 시스템 * 의 경험치* 라 *항상 정답* 은 아니다. *시스템 / 트래픽 / 팀* 에 맞춰 *조정* 필요.
