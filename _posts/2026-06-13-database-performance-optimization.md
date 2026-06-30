---
layout: post
title: "*DB 성능 최적화 *전략* — *9 개 *층* 의 *순서대로 *짚기*"
date: 2026-06-13 04:10:00 +0900
categories: [backend, database, performance]
tags: [database, performance, optimization, postgres, mysql, index, query, sharding, replica]
---

> *DB 가 *느리다* 는 *백엔드 의 *흔한 *호소*. *원인 은 *9 개 *층 중 *어느 한 곳*.
> *순서 없 이 *대응 하면 — *튜닝 후 도 *느리거나 *오히려 *악화*.
> *9 개 *층 을 *위에서 아래로 *순서대로 *짚는* 방법 — 이 글의 주제.

---

## TL;DR — *9 개 층 의 *순서*

| 우선순위 | 층 | *효과 / 비용* |
|---------|-----|---------------|
| 1 | **측정** | *비용 0, *모든 의 시작* |
| 2 | **인덱스** | *대부분 90% 해결* |
| 3 | **쿼리 작성** | N+1 / 불필요 join / 비효율 sub-query |
| 4 | **스키마 설계** | 정규화 vs 비정규화 / 적정 타입 |
| 5 | **커넥션 관리** | HikariCP pool 크기 / 타임아웃 |
| 6 | **캐싱** | L1 (Caffeine) + L2 (Redis) |
| 7 | **Read replica** | 읽기 / 쓰기 분리 |
| 8 | **파티셔닝 / 샤딩** | 대용량 / 시간 기반 |
| 9 | **하드웨어** | NVMe / RAM / CPU |

*아래로 갈수록 *비용 증가* + *효과 *감소*. *위에서 아래로 *순서 대로 짚는 것* 이 *경제 적*.

---

## 1. **측정** — *모든 *시작*

> *"측정 *없이 *튜닝 *없다*."*

*이 한 줄* 이 *모든 DB 최적화의 *시작*. *짐작 으로 인덱스 추가* — *역효과 가능*.

### *측정 도구*

- **EXPLAIN ANALYZE** — *쿼리 의 *실행 계획 + 실측 시간*
- **pg_stat_statements** (Postgres) / **slow query log** (MySQL) — *느린 쿼리 추적*
- **APM (Datadog / NewRelic / Pinpoint)** — *애플리케이션 ↔ DB *전체 흐름*
- **`SHOW STATUS`** / `pg_stat_*` — *DB 자체 지표*

### *주요 지표*

```
- Query latency (P50 / P95 / P99 / P999)
- Throughput (queries / second)
- Connection pool usage
- Lock wait time
- Disk I/O 
- Cache hit ratio (buffer pool / shared_buffers)
- Replication lag (replica 운영 시)
```

이 *7 지표* 의 *변화 를 *시각화* 하지 않으면 *튜닝 시 *효과 *측정 불가*.

---

## 2. **인덱스** — *대부분 *90% 해결*

### *인덱스 의 *마법*

```
SELECT * FROM orders WHERE user_id = 123;
-- 인덱스 없음 :  O(n) — 1억 행 *전 scan*
-- 인덱스 있음 :  O(log n) — *10~20 번 *비교*
```

### *언제 *인덱스 가 *필요*

- *WHERE 절 의 *자주 쓰는 컬럼*
- *JOIN 키* (대부분 *외래 키*)
- *ORDER BY / GROUP BY* 자주 쓰는 컬럼
- *UNIQUE 제약* (자동 인덱스)

### *복합 인덱스 의 *순서*

```sql
-- ❌ 잘못
CREATE INDEX idx_orders ON orders (status, user_id);
-- *쿼리* : WHERE user_id = 123  → 인덱스 *부분 활용*

-- ✅ 올바름
CREATE INDEX idx_orders ON orders (user_id, status);
-- *쿼리* : WHERE user_id = 123 AND status = 'PAID' → 인덱스 *완전 활용*
```

**원칙** : *카디널리티 *높은* 컬럼 부터*. *equality 가 *range 보다 *앞*.

### *인덱스 의 *비용*

- *쓰기 시 *인덱스 도 갱신* — *INSERT/UPDATE/DELETE *느려짐*
- *디스크 공간 사용*
- *너무 많으면 *통계 정보 가 *복잡*
- *Hot 컬럼 의 *과한 인덱스 가 *쓰기 병목*

→ *인덱스 의 *추가는 *측정 *후*.

### *흔한 *오용*

1. ***모든 컬럼 인덱스*** — 쓰기 *심각히 느려짐*
2. ***복합 인덱스 *순서 잘못*** — *반쪽 활용*
3. ***LIKE '%abc%'*** — *인덱스 *못 씀*
4. ***함수 적용*** — `WHERE UPPER(name) = ...` *인덱스 못 씀*. *함수 인덱스 또는 *직접 저장*
5. ***NULL 의 *처리*** — DB 별 다름

---

## 3. **쿼리 작성** — *N+1 의 *지옥*

### *N+1 의 *전형*

```java
// ORM
List<Order> orders = orderRepo.findAll();  // SELECT * FROM orders → 1000건
for (Order o : orders) {
    User u = o.getUser();  // *각 행 마다 *SELECT * FROM users WHERE id = ?*
    // → 1 + 1000 = 1001 queries
}
```

해결 :

```java
// JPA
@Query("SELECT o FROM Order o JOIN FETCH o.user")
List<Order> findAllWithUser();
```

또는 *EntityGraph / FetchType.EAGER*.

### *흔한 *쿼리 함정 *5 가지*

1. ***N+1*** — *위 예시*
2. ***불필요한 SELECT *** — *큰 BLOB / TEXT 컬럼 *반복 로딩*
3. ***SELECT * 의 *남용*** — *필요한 컬럼만*
4. ***OR 의 *남용*** — *인덱스 활용 어려움. *UNION* 으로 분리*
5. ***DISTINCT 의 *남용*** — *조인 결과 *전체 정렬*

### *Query Plan 보기*

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id)
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id;
```

응답 :

```
HashAggregate  (cost=... rows=...)
  ->  Hash Right Join
        Hash Cond: (o.user_id = u.id)
        ->  Seq Scan on orders         ← *Seq Scan = 위험 신호*
        ->  Hash
              ->  Seq Scan on users
```

`Seq Scan` 가 *대용량 테이블 에 나오면 *인덱스 누락*. `Index Scan` / `Index Only Scan` 으로 *유도*.

---

## 4. **스키마 설계** — *정규화 *vs 비정규화*

### *정규화 의 *이상*

```
3NF :
- 1NF : 원자 값
- 2NF : 부분 종속 제거
- 3NF : 이행 종속 제거
```

이상 — *데이터 *중복 없음, *수정 안전*. 단 *읽기 시 *조인 비용 *증가*.

### *비정규화 의 *현실*

```
대시보드 / 통계 / 검색 :
- *반정규화 된 *집계 테이블*
- *조회 컬럼 *복사*
- *Materialized View*
```

읽기 *압도적 빠름*. 단 *쓰기 시 *일관성 *관리* 필요.

### *경험 적 *권장*

```
대부분 시스템 :
- *주요 도메인* — 3NF 정규화
- *통계 / 대시보드* — 별도 *반정규화 테이블*
- *Cache 계층 으로 *재 합산*
```

### *타입 선택 의 *세부*

- *VARCHAR vs TEXT* — VARCHAR (n) 권장. *큰 TEXT 는 *별 도 테이블*.
- *INT vs BIGINT* — *현대 시스템 *대부분 BIGINT*. 미래 안전.
- *TIMESTAMP vs TIMESTAMPTZ* — *항상 TIMESTAMPTZ 권장*. 타임존 안전.
- *JSON vs JSONB* — *JSONB 가 인덱스 가능*. *대부분 JSONB*.
- *UUID* — *분산 시스템 친화*. 단 *인덱스 크기 ↑*.

---

## 5. **커넥션 관리** — *HikariCP 의 *세계*

### *Pool 크기 의 *오해*

> *"Pool 크기 *크게 잡으면 *더 빠를 거다"*

→ **틀림**.

### *Little's Law 의 *현실*

```
*최적 Pool 크기 ≈ CPU 코어 수 × 2 + Disk 수 (Postgres 의 *공식 권장)*
```

*8 코어 + NVMe 1개* → *Pool 17 정도*. *50 ~ 100 은 *대부분 *과한 *낭비*.

### *왜 *작은 게 *낫나*

- *Connection 1 개 가 *서버 메모리 *수 MB ~ 십 MB*
- *Context switch 가 *많아 *CPU 비용 ↑*
- *Lock contention 증가*

### *HikariCP *기본 설정*

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      idle-timeout: 300000
      max-lifetime: 1800000        # 30분
      connection-timeout: 5000     # 5초
```

### *Connection Leak* 추적

- `leak-detection-threshold: 60000` — 60초 사용 안 되면 로그
- *Lazy connection* (Spring 의 `LazyConnectionDataSourceProxy`) — *실 SQL 시까지 *지연*

---

## 6. **캐싱** — *L1 + L2 의 *조합*

### *DB 측 캐시*

- **Buffer Pool / Shared Buffers** — *DB 자체 의 *RAM 캐시*. *전체 데이터 의 *50~70% 정도 *권장*.
- **Query Cache** (MySQL 옛) — *deprecated*. *현대 안 씀*.
- **Materialized View** — *집계 쿼리 *결과 *물리 저장*. *주기적 갱신*.

### *애플리케이션 측 캐시* (이전 글)

- *L1 (Caffeine)* — *100 ns 응답*
- *L2 (Redis)* — *1 ms 응답*
- *합산 hit ratio 90%+ → DB *부담 *극적 감소*

### *Cache 의 *주의*

- *Cache invalidation* — *어렵다*
- *Thundering herd* — *대량 키 동시 만료 → DB 폭주*
- *Hot key* — *분산 캐시의 *단일 노드 부하 집중*

---

## 7. **Read Replica** — *읽기 / 쓰기 *분리*

### *전형 구조*

```
주문 / 결제 (write)    → Master DB
대시보드 / 조회 (read) → Read Replica 1, 2, 3
```

### *Read Replica 의 *고려*

- ***Replication Lag*** — *수 ms ~ 수 초*. *읽기 일관성 *주의*.
- ***트랜잭션 *경계*** — *write 의 *직후 read* 가 *Master 로 가야*. Spring 의 `@Transactional(readOnly = true)` 와 *라우팅 조합*.
- ***Replica 수*** — *읽기 부담 / 1 개 capacity 비율*.

### *AWS RDS / GCP CloudSQL*

- *자동 Replica 추가*
- *Multi-AZ standby* (HA)
- *Read pool* — 부하 자동 분산

---

## 8. **파티셔닝 / 샤딩** — *대용량 *분할*

### *파티셔닝 (Partitioning)* — *같은 DB *안 분할*

```sql
CREATE TABLE orders (...)
PARTITION BY RANGE (created_at);

CREATE TABLE orders_2026_q1 PARTITION OF orders
  FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
```

장점 :
- *옛 데이터 *드롭 빠름* (DROP PARTITION)
- *최근 데이터 *접근 *빠름*
- *인덱스 도 *분할*

### *샤딩 (Sharding)* — *다른 DB 노드 로 *분할*

```
사용자 ID 1 ~ 1000만   → Shard A
사용자 ID 1000만 ~ ... → Shard B
```

장점 :
- *수평 확장*
- *각 shard 가 *독립 처리*

단점 :
- *cross-shard 쿼리 *복잡*
- *재 샤딩 *어려움*

→ *샤딩 은 *최후의 수단*. *대부분 시스템 은 *Read replica + 파티셔닝* 으로 충분.

---

## 9. **하드웨어** — *NVMe + RAM + CPU*

### *우선 순위*

```
1. NVMe SSD       — *random IOPS *결정 적*
2. RAM            — *buffer pool / cache *크기*
3. CPU            — *복잡 쿼리 / 정렬 / 집계*
4. 네트워크        — *replica / 분산 시*
```

### *NVMe SSD 의 *비대칭 가성비*

이전 글 — *HDD 100 개 = NVMe 1 개*. *DB 운영 의 *가장 큰 단일 *결정*.

### *RAM 권장*

```
PostgreSQL :
  shared_buffers     = RAM 의 25%
  effective_cache_size = RAM 의 50~75%
  work_mem            = 4~16MB (쿼리 별)
  maintenance_work_mem = 64~256MB
```

*RAM 부족 = *모든 쿼리 가 *디스크 까지*. *작아도 *DB 한 노드 *32GB 이상* 권장.

---

## 10. **현장 *경험* — *7년 의 *5 가지 *오답*

### 10.1. *인덱스 없는 *큰 테이블*

*1000 만 행 *테이블 의 *조회 쿼리 5 초*. *인덱스 추가 → 5 ms*. **무려 *1000 배***.

### 10.2. *N+1 의 *반복*

*대시보드 의 1 페이지 = *3000 query*. *fetch join 으로 *3 query* → *p99 -90%*.

### 10.3. *Connection pool *너무 큼*

*100 connection 으로 운영 — *context switch 폭주*. *20 으로 줄이자 *p99 -30%*.

### 10.4. *Read replica 의 *Lag 무시*

*write 후 *읽기 가 *replica 로 가서 *옛 데이터*. *@Transactional(readOnly=true) + 라우팅 조정* 으로 해결.

### 10.5. *Materialized View 없이 *대시보드*

*대시보드 1 화면 = *복잡 집계 30 초*. *MView 로 *3 초*. *주기 갱신* 으로 *최신성* 유지.

---

## 11. **흔한 함정 7 개**

1. ***측정 없는 *튜닝*** — *짐작 *최악*.
2. ***모든 컬럼 인덱스*** — *쓰기 *느려짐*.
3. ***N+1 무시*** — *대시보드 *느림의 *상위 원인*.
4. ***Pool 크기 *과대*** — *수십 ~ 수백*.
5. ***@Transactional 없이 *복수 read*** — *각 query 가 *별 도 connection*.
6. ***JSON 컬럼 의 *인덱스 누락***.
7. ***replica lag 무시 — *write 직후 *read 부정합***.

---

## 12. **결정 체크리스트**

```
□ 측정 도구 (EXPLAIN / APM / slow query log) 가 설치 됐는가?
□ 자주 쓰는 WHERE / JOIN 에 *인덱스* 가 있는가?
□ *N+1* 이 *대시보드 / 목록 화면* 에 *없는가?
□ *불필요 SELECT * / DISTINCT / OR* 가 *없는가?
□ *Connection pool 크기* 가 *최적* 인가?
□ *L1 (Caffeine) + L2 (Redis)* 가 *적정 hit ratio* 인가?
□ *Read replica* 활용 가 *읽기 부담 줄였는가?
□ *대용량 테이블* 이 *파티셔닝* 되었는가?
□ *NVMe + RAM 충분* 한가?
```

이 *9 체크리스트* 가 *대부분 *DB 성능 문제 의 *예방*.

---

## 13. *마치며*

> *DB 성능 최적화 는 *9 개 *층 의 *순서 적용*. *위에서 아래로 — *비용 / 효과 비율 의 *순서*.

3 줄 요약 :

1. ***측정 → 인덱스 → 쿼리 → 스키마 → connection*** — *상위 4 층 이 *90% 해결*.
2. ***캐시 + Replica + 파티셔닝 + 하드웨어*** — *하위 5 층 은 *대용량 / 분산 *시 점진 적*.
3. ***튜닝 의 *진짜 능력 = *측정 의 *습관*** — *짐작 *튜닝 은 *최악의 *낭비*.

9년차 회고 :

> *"인덱스 한 개 추가 가 *수십 번 의 *리팩터링 보다 *큰 *효과 *낸* 적이 *수도 *없다*."*

다음 글 — *EXPLAIN 의 *깊이 *분석* — *Seq Scan / Hash Join / Nested Loop 의 *실 무 해석*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *9년차 백엔드 / DB 운영 회고*. *PostgreSQL / MySQL 중심*. *원리* 는 *모든 RDBMS 공통*. *NoSQL (MongoDB, DynamoDB) 도 *비슷한 원리* 의 *다른 표현*.
