---
layout: post
title: "DB 설계와 쿼리 — 14개월 운영 경험 으로 정리한 실전 가이드"
date: 2026-06-29 08:30:00 +0900
categories: [database, postgresql, backend, design]
tags: [database, postgresql, schema-design, index, query-optimization, n-plus-one, transaction, isolation-level, migration, flyway]
---

DB 설계 와 쿼리 는 *책 으로 학습 하는 영역* 이 아니다. *14개월 운영* 하면서 *V50 사고* 같은 *생살이* 를 *겪고 *회복* 해야 *진짜 의 깊이* 가 들어 온다. 이 글 은 settlement / sparta / lemuel-xr 의 *수십 만 row 의 PostgreSQL 운영* 위에서 *체화 한 *현실 적 패턴* 의 정리.

이전 글 *[데이터베이스 의 본질 — B+Tree 부터 MVCC, Replication 까지](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)* 가 *DB 의 *내부 구조* 였다면, 이 글 은 *애플리케이션 측 의 *설계 결정 + 쿼리 작성* 의 실전.

---

## 1. DB 설계 의 *5 가지 원칙*

내가 *모든 스키마 설계 의 *시작점* 으로 두는 5 가지:

1. **변하지 않는 것 부터 시작** — 도메인 의 *invariant* (예: order 의 total = items 의 sum). 그 invariant 가 *PK, UNIQUE, CHECK 의 출발점*.
2. **누구 가 *읽고 쓰는지 *명시*** — *읽기 빈도 vs 쓰기 빈도*. 99% read 면 *index 많이*, 99% write 면 *index 적게*.
3. **시간 이 흐르면 *어떻게 자라는지 *시뮬레이션*** — *1년 후 row 수* 추정. *1000 row → 10M row* 의 *차이* 가 *index / partitioning 의 필요성*.
4. **삭제 / 변경 의 *연쇄 영향* 미리 그리기** — *user 한 명 삭제 시 *지워지는 게 *무엇 인지*. *FK ON DELETE CASCADE* 의 *명시 적 의도*.
5. **regulatorial / audit 요구 명시** — *변경 추적 의 의무 (audit_logs)*, *immutable 필드* (settlement 의 settlement_immutability_trigger 같은 trigger), *PII 컬럼 의 암호화*.

이 5 가지 가 *명확 하지 않은 *schema 는 *수개월 후 *기술 부채*. *코드 의 *어떤 비즈니스 로직* 보다 *DB 스키마 의 *변경 비용* 이 *훨씬 비쌈*.

---

## 2. 정규화 vs 비정규화 — 진짜 의 *trade-off*

대학 교과서 의 *3NF, BCNF* 는 *이론적 이상*. 현실 의 *production* 은 *trade-off* 의 *명시 적 결정*.

### 정규화 (Normalized)
```sql
-- 3NF — 중복 0
CREATE TABLE users (id, name, email);
CREATE TABLE orders (id, user_id, total, created_at);
CREATE TABLE order_items (id, order_id, product_id, quantity, price);
```

장점: *데이터 일관성 자동*, *update 시 *한 곳 만*, *공간 효율*.
함정: *조회 시 *JOIN 의 *latency 누적*. *order list + user name + item count* 같은 *흔한 쿼리* 가 *3 JOIN*.

### 비정규화 (Denormalized)
```sql
-- 비정규화 — 중복 의 *의도 적 도입*
CREATE TABLE orders (
    id, user_id,
    user_name VARCHAR(50),   -- ← 중복 (users.name 의 snapshot)
    user_email VARCHAR(255), -- ← 중복
    total NUMERIC,
    item_count INTEGER,      -- ← 중복 (count(order_items))
    created_at
);
```

장점: *조회 시 *JOIN 0*, *latency 작음*.
함정: *user.name 변경* 시 *orders 의 모든 row update 필요* — *원자 적 안전 망 없음*. *insert / update 의 코드 의 *책임* 증가.

### 현실 의 *선택*
- *읽기 99% + 데이터 의 *snapshot 의미* 가 *자연 스러움* (예: 주문 시점 의 *user 정보* 는 *그 시점 의 *고정 값*) → **비정규화**
- *수정 가 *흔하고 *일관성 의무* (예: user 의 *현재 이메일*) → **정규화 + JOIN**
- *복잡한 GROUP BY / 집계 의 *반복* → **별도 *Materialized View* 또는 *비정규화 된 *조회 전용 테이블***

settlement 의 *order_items 의 *price* — *주문 시점 의 *상품 가격 snapshot*. *나중에 *상품 가격 이 바뀌어도 *옛 주문 의 *원래 가격* 은 *유지*. 이게 *비정규화 의 *올바른 사용* — *audit + 변경 불가 의 *명시 적 의도*.

---

## 3. PK 설계 — UUID vs BIGINT, 자연키 의 함정

### BIGINT (autoincrement)
```sql
id BIGSERIAL PRIMARY KEY
```

장점: *작은 크기 (8 byte)*, *index 효율 최고*, *대규모 INSERT 빠름* (B+Tree 의 *끝 page 만 사용*).
함정: *URL 노출 시 *enumeration 공격* (예: `/orders/1`, `/orders/2` 로 *순회*). *외부 system 통합 시 *충돌 위험*.

### UUID (v4 random)
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

장점: *전 세계 유일*, *외부 노출 안전*, *분산 시스템 의 *generation 충돌 없음*.
함정: *큰 크기 (16 byte)*, *random 한 분포 → B+Tree 의 *모든 page 에 INSERT 분산* → *write amplification + cache miss 폭증*.

### UUID v7 (time-ordered) — *2024 표준*
```sql
-- PostgreSQL 의 uuidv7 함수 (17+, 또는 extension)
id UUID PRIMARY KEY DEFAULT uuidv7()
```

장점: *UUID 의 *유일성* + *시간 순서 (대부분 의 새 row 가 *B+Tree 끝* 에 추가)*. *BIGINT 의 INSERT 효율 + UUID 의 외부 안전*.
→ *2026 의 새 시스템 의 *합리적 default*.

### 자연키 — *대부분 함정*
```sql
-- 안티 패턴
CREATE TABLE users (
    email VARCHAR(255) PRIMARY KEY,   -- ← 자연키
    ...
);
```

함정: *user 가 *email 변경 시* *모든 FK 가 *cascade update 필요* → *수만 row 의 *동시 변경 → lock 폭증*. *현실 의 *유연성 부족*.

**예외 — *진짜 immutable 한 *자연키***:
- *주민등록번호 (절대 안 변함 가정)* — 그러나 *PII 의 *보안 문제 별개*
- *국가 코드 ISO 3166-1 (KR, US, JP)* — *진짜 immutable*

**원칙**: *대리키 (BIGINT 또는 UUID v7) + 자연키 의 UNIQUE 제약* 의 *2 단 구조*.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuidv7(),  -- 대리키
    email VARCHAR(255) UNIQUE NOT NULL,    -- 자연키 의 *UNIQUE 강제*
    ...
);
```

→ FK 는 *대리키 참조*. email 변경 시 *cascade 없음*. *유연성 + 일관성* 둘 다.

---

## 4. 인덱스 설계 — 잘 안 만들고 / 잘 만들고

내가 *14개월 운영* 하면서 *직접 만든 *진단 패턴*:

### 만들어야 할 인덱스
```sql
-- 1. 모든 FK 에 자동 인덱스 (PG 는 *자동 안 만듦*. MySQL InnoDB 는 자동)
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- 2. WHERE 절 에 자주 쓰는 컬럼
CREATE INDEX idx_orders_status ON orders(status);

-- 3. 정렬 (ORDER BY) 컬럼
CREATE INDEX idx_orders_created_at_desc ON orders(created_at DESC);

-- 4. 복합 인덱스 (자주 쓰는 *조합*)
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
-- 위 인덱스 가 *user_id 만 검색* 또는 *user_id + status* 둘 다 커버
-- 하지만 *status 만 검색* 은 *못 커버* (leftmost prefix rule)
```

### 만들지 말아야 할 인덱스
- *카디널리티 낮은* 컬럼 (예: `is_deleted BOOLEAN`) — *전체 의 *50% 면 *full scan 보다 *나쁜 경우* 흔함
- *write heavy + read 거의 없는* 테이블 — *index maintenance 비용*
- *너무 많은 인덱스* (10+ per 테이블) — *write 마다 *모든 인덱스 update*

### Partial Index — *카디널리티 낮은 컬럼 의 *해결책*
```sql
-- 100M row 중 *active 가 0.1%* 인 경우
CREATE INDEX idx_users_active_only ON users(id)
    WHERE is_active = true AND deleted_at IS NULL;
```
→ index 크기 *작음*, *active 검색 시 *극도로 효율*.

### Covering Index — *index 만 으로 *쿼리 종결*
```sql
-- 쿼리: SELECT id, name FROM users WHERE user_type = 'PREMIUM'
CREATE INDEX idx_users_type_covering ON users(user_type) INCLUDE (id, name);
```
→ *heap 접근 0 회 *index 만으로 *모든 컬럼 반환*. *3~5 배 빠름*.

### BRIN — *시계열 의 *압도적 효율*
```sql
-- audit_logs 같은 *append-only + 시간 순* 테이블
CREATE INDEX idx_audit_logs_created_brin ON audit_logs USING brin(created_at);
```
→ *B-Tree 의 *1/100 크기*. 시계열 / 로그 에 적합.

### GIN — *JSONB 검색*
```sql
CREATE INDEX idx_orders_meta_gin ON orders USING gin(meta);
SELECT * FROM orders WHERE meta @> '{"channel": "web"}';
```

### HNSW — *vector similarity*
```sql
-- pgvector
CREATE INDEX idx_docs_embedding ON docs USING hnsw(embedding vector_cosine_ops);
```
→ sparta MSA 의 *AI 검색 의 토대*.

---

## 5. 데이터 타입 — *잘못 선택 의 비용*

### TEXT vs VARCHAR(N)
PostgreSQL 에선 *둘 의 성능 차이 거의 없음*. *VARCHAR(N) 의 N* 은 *제약* 일 뿐. *대부분 *TEXT 가 충분*.

예외 — *길이 제한 이 *비즈니스 요구* 인 경우 (예: 주민번호 13자리) → `VARCHAR(13)` 로 *DB 단 검증*.

### NUMERIC vs FLOAT
**돈 / 정산** 같은 *정확 도 필수* → `NUMERIC(precision, scale)`. *FLOAT 는 *binary 표현 의 *오차* — *0.1 + 0.2 = 0.30000000000000004*.

```sql
-- 돈
amount NUMERIC(15, 2)   -- 최대 9,999,999,999,999.99

-- 비율
discount_rate NUMERIC(5, 2)  -- 100.00 까지
```

### TIMESTAMP vs TIMESTAMPTZ
**항상 TIMESTAMPTZ**. *timezone 정보 없는 timestamp 는 *2 노드 가 *다른 timezone 시 *지옥*.

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

PG 는 *내부 적으로 UTC 저장* + *조회 시 *세션 timezone 으로 변환*. application 의 *시간 일관성* 자동 보장.

### JSON vs JSONB
*항상 JSONB*. *JSON 은 *raw text 보관 만*, *JSONB 는 *binary + indexable + 검색 가능*. *대부분 의 경우 JSONB*.

```sql
-- 메타 데이터
meta JSONB NOT NULL DEFAULT '{}'::jsonb
CREATE INDEX idx_meta_gin ON orders USING gin(meta);
```

### ENUM — *함정***
PostgreSQL 의 ENUM 은 *확장 어려움* (`ALTER TYPE ADD VALUE` 가 *transaction 안 에서 못 함* 등). *대안*:

```sql
-- 좋음 — CHECK 제약 + VARCHAR
status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','PAID','CANCELLED','REFUNDED'))

-- 또는 별도 lookup table
CREATE TABLE order_statuses (code VARCHAR(20) PRIMARY KEY, label TEXT);
-- orders 가 FK 참조
```

→ *추가 / 변경* 시 *자유*. *ENUM 의 *경직성* 피함.

---

## 6. 제약 조건 — *DB 가 *마지막 방어 막***

application 코드 가 *모든 invariant 보장* 한다는 *환상*. 현실 — *어떤 라이브러리 / 다른 service / 수동 SQL* 이 *우회 가능*. *DB 의 *제약 조건* 이 *최후의 보루*.

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    total NUMERIC(15, 2) NOT NULL CHECK (total >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PAID','CANCELLED','REFUNDED')),
    cancelled_amount NUMERIC(15, 2) NOT NULL DEFAULT 0
        CHECK (cancelled_amount <= total),  -- ← 초과 취소 *DB 단 차단*
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, created_at)
);
```

각 제약 의 *역할*:
- `NOT NULL` — *없으면 의미 없음* 의 명시
- `CHECK` — *비즈니스 규칙 의 *DB 단 강제*
- `UNIQUE` — *중복 방지 (settlement 의 outbox.event_id UNIQUE 가 *Triple Idempotency 의 L3*)
- `FOREIGN KEY` — *참조 무결성*
- `ON DELETE RESTRICT / CASCADE / SET NULL` — *연쇄 영향 의 *명시 적 결정*

### 06-23 V50 사고 의 교훈

settlement 의 V50 마이그레이션 에서 *ADD CONSTRAINT 의 *non-idempotent* 가 *partial 적용 후 *160 회 CrashLoop* 의 원인. 

```sql
-- ❌ 안티
ALTER TABLE product_variants
    ADD CONSTRAINT chk_discount_price
        CHECK (discount_price IS NULL OR discount_price >= 0);

-- ✅ idempotent
DO $$ BEGIN
    ALTER TABLE product_variants
        ADD CONSTRAINT chk_discount_price
            CHECK (discount_price IS NULL OR discount_price >= 0);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
```

자세한 회고: [V50 사고 + idempotent 패턴](/2026/06/23/v50-flyway-incident-and-idempotent-add-constraint-pattern.html) (settlement README 에서 일반화).

---

## 7. 쿼리 안티 패턴 — *현실 의 흔한 함정*

### N+1 — *가장 흔한 함정*
```java
// 안티
List<Order> orders = orderRepo.findAll();   // 1 쿼리
for (Order o : orders) {
    User u = o.getUser();  // ← lazy load → *N 회 쿼리*
}

// 좋음
@EntityGraph(attributePaths = {"user"})
List<Order> findAll();   // 1 회 JOIN
```

또는 *JPQL*:
```java
@Query("SELECT o FROM Order o JOIN FETCH o.user")
List<Order> findAllWithUser();
```

### OFFSET 의 *느림*
```sql
-- 안티 — 100,000 페이지 로 가면 *느려짐*
SELECT * FROM orders ORDER BY created_at DESC LIMIT 20 OFFSET 2000000;
-- OFFSET 가 *200만 row scan + 버림*

-- 좋음 — cursor pagination
SELECT * FROM orders
WHERE created_at < $last_seen_created_at
ORDER BY created_at DESC LIMIT 20;
```

### LIKE 의 *왼쪽 와일드카드*
```sql
-- ❌ index 안 탐
SELECT * FROM users WHERE email LIKE '%@gmail.com';

-- ✅ index 탐
SELECT * FROM users WHERE email LIKE 'jin%';

-- 풀텍스트 검색 필요 면 — pg_trgm
CREATE INDEX idx_users_email_trgm ON users USING gin(email gin_trgm_ops);
```

### WHERE 절 의 *함수*
```sql
-- ❌ index 안 탐 — function 결과 의 *모든 row 비교*
SELECT * FROM users WHERE LOWER(email) = 'foo@gmail.com';

-- ✅ functional index
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
```

### SELECT *
```sql
-- ❌ 모든 컬럼 읽음 — heap 접근 + network 부담
SELECT * FROM users WHERE id = 1;

-- ✅ 필요한 컬럼 만
SELECT id, email, name FROM users WHERE id = 1;
```

### Cartesian Product
```sql
-- ❌ JOIN 조건 누락 — *모든 row × 모든 row*
SELECT * FROM orders o, users u;
-- 1000 × 1000 = 1,000,000 row 의 *지옥*

-- ✅ 명시 적 JOIN
SELECT * FROM orders o JOIN users u ON o.user_id = u.id;
```

---

## 8. EXPLAIN ANALYZE — *진단 의 핵심***

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.id, u.name FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'PAID' AND o.created_at > NOW() - INTERVAL '7 days';
```

읽는 법:
```
Hash Join  (cost=10.5..100.2 rows=500 width=200) (actual time=0.5..15.3 rows=480 loops=1)
  Hash Cond: (o.user_id = u.id)
  Buffers: shared hit=200 read=10
  ->  Index Scan using idx_orders_status_created on orders o  (cost=...) (actual ...)
        Index Cond: (status = 'PAID' AND created_at > ...)
        Rows Removed by Filter: 50
  ->  Hash  (cost=...) (actual ...)
        Buckets: 1024
        ->  Seq Scan on users u  (cost=...)
Planning Time: 0.123 ms
Execution Time: 15.456 ms
```

핵심 신호:
- **Seq Scan** — *index 없음* 또는 *plan 이 *full scan 선택*. 큰 테이블 이면 *경고*
- **Index Scan / Bitmap Index Scan** — *index 사용 중* 
- **rows estimate vs actual** — *차이 크면 *통계 outdated*. `ANALYZE table_name;` 필요
- **Buffers shared hit vs read** — *hit = cache 에서, read = disk 에서*. *read 많으면 *느림*
- **Rows Removed by Filter** — *index 가 *not optimal*. *추가 index 또는 *composite index 검토*

### pg_stat_statements — *느린 쿼리 의 *순위***
```sql
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 20;
```
→ *총 시간 의 *top 20 쿼리*. *N+1 의 *흔적 발견* 의 *결정적 도구*.

---

## 9. 트랜잭션 + Isolation Level

### 4 isolation level (PostgreSQL)
| Level | Dirty | Non-repeatable | Phantom |
|---|---|---|---|
| Read Uncommitted (PG 는 Read Committed 와 동일) | ❌ | ⚠️ | ⚠️ |
| Read Committed (기본) | ❌ | ⚠️ | ⚠️ |
| Repeatable Read | ❌ | ❌ | ❌ (PG 는 snapshot) |
| Serializable | ❌ | ❌ | ❌ |

### Lost Update — *Read Committed 의 함정*
```sql
-- tx1
BEGIN;
SELECT balance FROM accounts WHERE id = 1;  -- 100
-- (코드: new = 100 - 10 = 90)
UPDATE accounts SET balance = 90 WHERE id = 1;
COMMIT;

-- 동시 tx2
BEGIN;
SELECT balance FROM accounts WHERE id = 1;  -- 100
-- (코드: new = 100 - 20 = 80)
UPDATE accounts SET balance = 80 WHERE id = 1;
COMMIT;

-- 결과: 80 (또는 90) — *마지막 commit 의 승리*. 진짜는 70 이어야 함.
```

**해결 3 가지**:

1. **Atomic UPDATE — *가장 단순***
```sql
UPDATE accounts SET balance = balance - 10 WHERE id = 1;
-- DB 가 *원자 적으로 처리*. JPA 면 @Modifying @Query
```

2. **Optimistic Lock** — @Version
```sql
UPDATE accounts SET balance = 90, version = 2
WHERE id = 1 AND version = 1;
-- 영향 받은 row 0 면 *retry*
```

3. **Pessimistic Lock** — SELECT FOR UPDATE
```sql
SELECT * FROM accounts WHERE id = 1 FOR UPDATE;
-- 다른 tx 의 *SELECT FOR UPDATE / UPDATE 가 *대기*
```

settlement 의 *잔액 / 정산 금액* 변경 은 *Atomic UPDATE 또는 *Pessimistic Lock 의무*.

---

## 10. Migration 정책 — *production 의 *deploy 의 *진실***

application 코드 보다 *훨씬 *위험* 한 작업.

### 원칙
1. **모든 schema 변경 은 *migration file*** — 수동 SQL 직접 실행 금지
2. **migration file 은 *immutable*** — 한 번 commit + 적용 후 *수정 불가*
3. **idempotent 의무** — `IF NOT EXISTS`, `DO $$ EXCEPTION` 패턴
4. **rollback 명시** — *forward migration 마다 *대응 하는 *revert 의 *가능성* 검토
5. **production 적용 전 *staging 의무*** — *순서, 락 시간, 데이터 영향* 모두 검증

### Naming Convention
```
V{N}__{snake_case}.sql                            (정수, settlement)
V{YYYYMMDDhhmmss}__{snake_case}.sql               (타임스탬프, sparta / lemuel-xr)
```

내 클러스터 의 *3 종 컨벤션* (settlement-flyway-migration, sparta-flyway-migration, lemuel-xr-flyway-migration SKILL.md) 가 *각자 의 진화 *반영*.

### Long-running migration 의 *함정*
```sql
-- ❌ 100M row 의 *full table lock*
ALTER TABLE orders ADD COLUMN new_field INTEGER NOT NULL DEFAULT 0;

-- ✅ 2 단 분리
-- 1) NULL 허용 column 추가
ALTER TABLE orders ADD COLUMN new_field INTEGER;
-- 2) 백필 (chunked) — production load 적은 시간
UPDATE orders SET new_field = 0 WHERE id BETWEEN 1 AND 10000;
-- ... (반복)
-- 3) NOT NULL 강제
ALTER TABLE orders ALTER COLUMN new_field SET NOT NULL;
```

`gh-ost`, `pt-online-schema-change` (MySQL), `pg_repack` (PG) 같은 *online schema change* 도구.

---

## 11. 모니터링 — *어떤 메트릭 을 *항상 보는지*

내 클러스터 의 *Prometheus + Grafana* dashboard 의 *DB 지표*:

| 지표 | 의미 | 임계 |
|---|---|---|
| `pg_stat_database_xact_commit` | 초당 commit 수 | baseline 의 *2 배 이상 변화* 시 의심 |
| `pg_stat_database_tup_returned / fetched` | row 처리 양 | 폭증 = N+1 의심 |
| `pg_stat_database_blks_hit / blks_read` | buffer cache hit ratio | *< 99% 면 *cache 부족 *또는 *table 너무 큼* |
| `pg_locks_count` | 동시 잠금 수 | 50+ 면 *lock contention 의심* |
| `pg_replication_slots_active` | replication lag | 큰 lag = *read replica stale* |
| HikariCP `connections_active / max` | 풀 사용률 | *80%+ 지속 시 *풀 부족* |
| HikariCP `connections_pending` | 대기 connection | *> 0 의 *반복 발생 시 *심각* |

### pg_stat_statements 의 *주간 분석*
```sql
-- 한 주 의 *상위 20 쿼리*
SELECT 
  substring(query, 1, 80) AS query,
  calls,
  ROUND(mean_exec_time::numeric, 2) AS avg_ms,
  ROUND(total_exec_time::numeric, 2) AS total_ms,
  rows
FROM pg_stat_statements
WHERE query NOT ILIKE '%pg_stat%'
ORDER BY total_exec_time DESC
LIMIT 20;
```

→ *느린 쿼리 의 *체계 적 식별*. 매 주 *분석* 가능.

---

## 12. 마치며 — *14개월 의 *작은 결론*

DB 설계 와 쿼리 는 *책 으로 *학습 가능 하지만 *체화 는 *사고 가 가르친다*. 06-23 V50 사고 의 *160 회 CrashLoop* 가 *idempotent 패턴* 의 *진짜 의도* 를 *각인*. 02-25 의 *연결 풀 고갈* 이 *@Transactional 안 외부 호출 금지* 의 *진짜 무게* 를 *체감*. 

내가 *14개월 운영* 하면서 *체득* 한 *작은 결론* — *DB 설계 의 *진짜 가치* 는 *변경 비용* 이다*. *수십 줄 의 *application 코드* 는 *언제든 *바꿀 수 있다*. *수억 row 의 *production DB 의 *스키마 변경* 은 *수일 ~ 수주 의 *고통*. 그러므로 *처음 설계 의 *5 가지 원칙* (invariant 부터, 읽기/쓰기 명시, 시간 흐름 시뮬, 연쇄 영향 그리기, audit 의무) 의 *시간 투자* 가 *수년 의 *부채 회피*.

쿼리 작성 의 *진짜 가치* 는 *production 의 *p99 latency* 의 *대부분* 이 *몇 개 의 슬로우 쿼리* 에 *집중* 된다는 *사실 의 이해*. pg_stat_statements 의 *상위 20* 의 *주간 분석* 이 *대부분 의 *latency 사고* 의 *예방*. EXPLAIN ANALYZE 의 *습관* 이 *코드 작성 시점 의 *비용 직감*.

[데이터베이스 의 본질](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html) 의 *물리* 를 *알고*, 이 글 의 *애플리케이션 측 *결정 패턴* 을 *체화* 하면 — *대부분 의 *백엔드 의 *데이터 측 사고* 는 *예방 가능*. 그래도 *남는 사고* 는 *14개월 마다 한 번* 의 V50 같은 *학습 의 *진짜 시간*. *그 사고 가 *깊이 를 만든다*.

---

## 참고

- *Designing Data-Intensive Applications* (Martin Kleppmann)
- *PostgreSQL: Up and Running* (Regina Obe, Leo Hsu, 3rd ed.)
- *SQL Performance Explained* (Markus Winand) — [use-the-index-luke.com](https://use-the-index-luke.com)
- *Vlad Mihalcea 의 블로그* — Hibernate / JPA performance 의 reference
- 자매편:
  - [데이터베이스 의 본질 — B+Tree 부터 MVCC, Replication 까지](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
  - [I/O 병목 어떻게 해결하지?](/2026/06/18/io-bottleneck-how-to-solve.html)
  - [Transactional Outbox 패턴](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)
  - [AI 코드 PR 머지 7 질문](/2026/06/21/ai-code-pr-merge-7-questions-checklist.html)
