---
layout: post
title: "*데이터베이스 의 *본질* — *B+Tree* 부터 *MVCC*, *Isolation*, *Replication*, *Sharding* 까지"
date: 2026-06-22 00:30:00 +0900
categories: [database, fundamentals, postgresql, backend]
tags: [database, postgresql, mysql, b-tree, lsm-tree, mvcc, isolation-level, wal, replication, sharding, connection-pool, fundamentals]
---

> *"ORM 이 *알아서 해주는데 *왜 *DB 본질을 알아야 할까?"* — 2026 년 의 *흔한 질문*. 답은 *"ORM 이 알아서 못 하는 순간"* 이 *바로 그 본질 이 깨질 때* 라는 것.
>
> *Spring Data JPA 가 *쿼리 1 줄* 을 *N+1 회 호출* 로 변환 하는 순간, *index 가 *full scan 으로 바뀌는 순간*, *낙관적 락 이 *deadlock 으로 터지는 순간*, *replica 의 *replication lag* 으로 *방금 쓴 데이터 가 *못 읽히는 순간*. *그 모든 순간* 의 *진실* 은 *DB 안 의 *B+Tree, MVCC, WAL, Replication* 의 *물리* 다.
>
> 이 글은 *PostgreSQL 을 *기본 reference* 로 두고, *DB 의 *7 가지 본질* — *Storage engine (B+Tree vs LSM)*, *Index 구조*, *MVCC*, *Isolation Level*, *Locking*, *WAL*, *Replication / Sharding* — 을 *백엔드 엔지니어 가 *알아야 하는 깊이* 로 정리한다.

내 *12 편 인프라 / 운영 연작* 의 *기본기 시리즈* 시작 :
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html) — *N+1 쿼리, 연결 풀* 의 *왜*
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *DB 암호화 / Row-level security*
- [*GitHub PAT 만료 사고*](/2026/06/21/github-pat-expiry-13-pods-down-3-prevention-patterns.html) — *현장 사고 회고*

---

## TL;DR — *한 줄 결론*

> DB 의 *본질* 은 *7 가지* : (1) *B+Tree (OLTP) vs LSM-Tree (write-heavy)* 의 *물리적 선택*, (2) *Index 의 *clustered/secondary/covering*, (3) *MVCC* 가 *읽기 와 쓰기를 *분리* 함, (4) *Isolation Level 4 개* 의 *각 anomaly 막는 정도*, (5) *Locking 의 *row / advisory / 의 *세밀도*, (6) *WAL* 이 *durability 와 *replication 의 *공통 토대*, (7) *Sync/Async/Logical Replication + Sharding* 의 *수평 확장*. *ORM 위에서 일하는 백엔드* 는 *이 7 가지 가 *어디서 *깨지는지* 만 *알면 *대부분 의 성능 / 정합성 문제 의 *원인 식별 가능*. *깊이 는 *코드 의 양 이 아니라 *어디 의 본질 이 깨졌는지 *측정 할 수 있는 능력* 이 만든다.

---

## 1. *왜 *ORM 시대 에도 *DB 본질 인가*

### 1.1 *ORM 이 *못 가르쳐 주는 것*

```java
// JPA — 단순해 보임
List<Order> orders = orderRepo.findAll();
for (Order o : orders) {
    log.info("{}", o.getUser().getName());  // ← *lazy load*
}
```

*외부 적* : 한 줄.
*내부 적* :
1. `SELECT * FROM orders` — *N row*
2. `SELECT * FROM users WHERE id = ?` — *N 회*  ← **N+1 쿼리**

→ *ORM 이 *추상화 한 *진실 (SQL)* 을 *알아야* *그 추상화 가 *언제 *깨지는지* 알 수 있다.

### 1.2 *DB 본질 의 *3 단 효과*

| 효과 | 결과 |
|---|---|
| **성능 사고 의 *원인 추론* 가능** | "왜 이 query 가 느린가" — *index? full scan? lock contention? replication lag?* |
| **정합성 사고 의 *원인 추론* 가능** | "왜 *둘 다 *update 했는데 *한 명 의 변경만 살아 남나" — *Read Committed 의 lost update* |
| **시스템 설계 의 *근거 있는 선택*** | "왜 *MySQL 이 아니라 *PostgreSQL?* 왜 *Cassandra 가 아니라 *PostgreSQL?*" — *워크로드 매핑* |

---

## 2. *본질 1 — *Storage Engine : B+Tree vs LSM-Tree*

### 2.1 *왜 *모든 DB 가 *Tree 인가*

> 디스크 의 *random read latency* (~80 μs) 가 *sequential read 의 *100 배*. *Tree 의 *log(N) seek* 가 *flat scan 의 *N 보다 *훨씬 적은 random read*.

10억 row 의 *PK lookup* :
- Flat scan : 10^9 row × 80 μs = *22 시간*
- B+Tree (depth 5) : 5 × 80 μs = *400 μs* — *2 억 배 빠름*

### 2.2 *B+Tree (PostgreSQL, MySQL InnoDB, Oracle)*

```text
                       [Root]
                      /      \
                 [Branch]   [Branch]
                /     \      /    \
            [Leaf]  [Leaf] [Leaf] [Leaf]
            /            \
       (k1, v1)        (k4, v4)
       (k2, v2)        (k5, v5)
       (k3, v3)        (k6, v6)
       │                      │
       └──leaf 간 *linked list* (range scan 친화)
```

**B+Tree 의 *5 가지 특성*** :
1. *Leaf 만 *데이터* (또는 데이터 포인터)
2. *모든 leaf 가 *같은 깊이*
3. *Leaf 간 *linked list* — `WHERE x BETWEEN 100 AND 200` 의 *순차 scan* 효율
4. *Branch 는 *키 + child pointer* 만
5. *Page 단위* (PostgreSQL 8KB, MySQL 16KB) — 한 page 가 *수십 ~ 수백 키 보유*

→ **OLTP (Online Transaction Processing)** 의 *표준 선택*. *random PK lookup + range scan* 둘 다 효율.

### 2.3 *LSM-Tree (Cassandra, RocksDB, ScyllaDB, ClickHouse)*

```text
[Memtable (RAM, sorted)]
      ↓ flush (full or timer)
[L0 SSTable] (sorted file)
[L0 SSTable]   ← 여러 개, 키 범위 겹침
      ↓ compaction
[L1 SSTable] (정렬된 더 큰 파일)
[L1 SSTable]
      ↓ compaction
[L2 SSTable] (더 큰)
...
```

**LSM 의 *철학*** :
- *Write 는 *memtable 에 *순차* 만* — *RAM 속도*
- *Read 는 *여러 SSTable 을 *합쳐서* — *느림 가능*
- *Background compaction* — *오래된 데이터 정리*

**B+Tree vs LSM 비교**:

| | B+Tree | LSM-Tree |
|---|---|---|
| Write | 중간 (random page update) | **매우 빠름** (순차 only) |
| Read (point) | **빠름** | 느림 (여러 SSTable scan) |
| Range scan | **매우 빠름** | 빠름 |
| Space amplification | 낮음 (in-place) | 높음 (구버전 잔존) |
| Write amplification | 낮음 | 높음 (compaction 시 re-write) |
| 적합 워크로드 | OLTP, 균형 | write-heavy (시계열, 로그) |

→ *왜 *PostgreSQL 이 트랜잭션 처리* 의 표준 인가* — *B+Tree* 의 *read/write 균형*. *Cassandra 가 *시계열* 강한 이유 — *LSM* 의 *write 압도*.

### 2.4 *PostgreSQL 의 *B+Tree* 내부*

```sql
CREATE INDEX idx_orders_user_id ON orders (user_id);

-- 내부 구조 확인
SELECT relname, relpages, reltuples
FROM pg_class WHERE relname = 'idx_orders_user_id';
-- relpages = 8KB page 수, reltuples = 추정 row 수
```

PostgreSQL 의 B+Tree는 *fillfactor* (default 90) — *insert 시 *10% 여유* — *page split 최소화*.

→ 자주 update 되는 인덱스 면 *fillfactor 낮춤* (예: 70). *insert only 면 *높임* (100) — *공간 효율*.

---

## 3. *본질 2 — *Index 의 *3 종류*

### 3.1 *Clustered vs Secondary Index*

**Clustered Index** (MySQL InnoDB 의 *PK*) :
- *데이터 자체 가 *Tree 의 leaf*
- *PK lookup* — *1 회 tree 탐색* 으로 *데이터 도달*

**Secondary Index** (PostgreSQL 의 *모든 index*) :
- *Tree 의 leaf 가 *데이터 포인터* (rowid / ctid)
- *Secondary lookup* — *index tree 탐색 → 데이터 page 별도 fetch*

```sql
-- MySQL 의 PK lookup (clustered)
SELECT * FROM orders WHERE id = 1000;
-- → Btree(id) traversal 1 회 → leaf 에 *데이터 통째로*

-- PostgreSQL 의 PK lookup (secondary)
SELECT * FROM orders WHERE id = 1000;
-- → Btree(id) traversal 1 회 → leaf 에 *ctid 만* → heap fetch 1 회
```

→ MySQL 의 *PK lookup 이 *약간 빠름*. *PostgreSQL 의 *모든 index 가 *clustering 없는 secondary*.

### 3.2 *Covering Index — *index 만 으로 쿼리 해결*

```sql
-- 안티 : index 가 user_id 만 — *select * 면 heap fetch 추가*
CREATE INDEX idx_orders_user_id ON orders (user_id);

SELECT id, amount FROM orders WHERE user_id = 42;
-- → index seek + heap fetch (id, amount 가 leaf 에 없으니)

-- 좋음 : covering index (PostgreSQL 11+)
CREATE INDEX idx_orders_user_id_covering ON orders (user_id) INCLUDE (id, amount);

SELECT id, amount FROM orders WHERE user_id = 42;
-- → index seek 만 — heap fetch 0 ★
```

→ *2 ~ 5 배 빠름* (워크로드 따라). *읽기 빈도 높은 쿼리* 에 강력.

### 3.3 *Partial Index — *조건 적 index*

```sql
-- 안티 : 모든 row 색인 — *DELETED 도 포함*
CREATE INDEX idx_orders_status ON orders (status);

-- 좋음 : *active 만 색인* — *95% 작은 index*
CREATE INDEX idx_orders_status_active ON orders (status)
  WHERE deleted_at IS NULL;
```

→ *index 크기 / 메모리 / 유지 비용 모두 감소*. *soft-delete 패턴* 의 *흔한 최적화*.

### 3.4 *GIN, GiST, BRIN — *전문 index*

| Index 타입 | 용도 |
|---|---|
| **B-Tree** | 일반 (=, <, >, BETWEEN) |
| **Hash** | = 만 (B-Tree 가 거의 항상 더 나음) |
| **GIN** | *Generalized Inverted Index* — JSONB, full-text, array |
| **GiST** | *Generalized Search Tree* — geo, range, custom |
| **BRIN** | *Block Range Index* — 시계열, *대용량 + 정렬된 데이터* |
| **HNSW** | *Hierarchical Navigable Small World* — vector (pgvector) |

```sql
-- JSONB 검색
CREATE INDEX idx_orders_meta_gin ON orders USING gin (meta);
SELECT * FROM orders WHERE meta @> '{"channel": "web"}';

-- 시계열 (BRIN)
CREATE INDEX idx_events_created_brin ON events USING brin (created_at);
-- → 1 TB 테이블 의 *index 크기 100MB* (B-Tree 의 100 분 1)

-- Vector (pgvector + HNSW)
CREATE INDEX idx_docs_embedding ON docs USING hnsw (embedding vector_cosine_ops);
SELECT * FROM docs ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 10;
```

→ *Sparta 의 *AI 검색 챗봇* 이 *pgvector + HNSW* 사용. *시계열 메트릭* 은 *BRIN*. *각 워크로드 의 *적합 index 선택* 이 *큰 차이*.

---

## 4. *본질 3 — *MVCC (Multi-Version Concurrency Control)*

### 4.1 *왜 *MVCC 인가*

전통 DB :
- *Read* 는 *Read Lock* 잡고
- *Write* 는 *Write Lock* 잡고
- *Read 와 Write 가 서로 *blocking*

PostgreSQL / Oracle / MySQL InnoDB 의 *MVCC* :
- *각 row 가 *여러 버전*
- *Read 는 *자기 시점 의 *snapshot* 봄
- *Write 는 *새 버전* 만 추가
- *Read 와 Write 가 *서로 안 막음* ★

### 4.2 *PostgreSQL MVCC 의 *물리***

```sql
-- 한 row 의 내부 구조 (단순화)
+-------+-------+-------+--------+--------+
| xmin  | xmax  | data  | t_ctid |  ...   |
+-------+-------+-------+--------+--------+
  ↑       ↑                ↑
이 row 가  이 row 를      "이 row 가 update 되면 *다음 버전*"
*어느 tx*  *삭제한 tx*    *self-pointer or next version*
*생성*
```

`INSERT` :
```
new row: (xmin=tx1, xmax=NULL, data=...)
```

`UPDATE` :
```
old row: (xmin=tx0, xmax=tx2, data=old, t_ctid=→new)
new row: (xmin=tx2, xmax=NULL, data=new)
```
→ **In-place update 안 함**. *옛 버전 보존* + *새 버전 추가*.

`SELECT` (tx3) 가 보는 row :
- *xmin <= tx3* (내가 시작 후 이미 commit 된 row)
- *xmax > tx3* 또는 *xmax IS NULL* (내가 시작 후 삭제 안 됨)

→ *tx3 의 *snapshot* 은 *tx3 시작 시점* 에 *고정*.

### 4.3 *VACUUM — *옛 버전 정리*

> *MVCC 의 *대가* : *옛 버전 이 *물리 적으로 남아 있음* → *디스크 / 메모리 누적*.

PostgreSQL 의 *autovacuum*:
- *dead tuple* (어느 tx 도 보지 않을 row) 찾아서 *공간 해제*
- *통계 (n_distinct 등) 갱신* — *plan 정확도*
- *transaction ID wraparound 방지* (xmin/xmax 가 32-bit, 20억 후 wraparound)

```sql
-- autovacuum 이 working 잘 하는지
SELECT relname, n_dead_tup, n_live_tup,
       last_autovacuum, autovacuum_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
```

→ *n_dead_tup 폭증* 시 *autovacuum 부족* — *큰 update / delete batch* 후 *수동 `VACUUM ANALYZE`* 권장.

### 4.4 *MVCC 의 *체감 효과*

```sql
-- tx1
BEGIN;
SELECT * FROM accounts WHERE id = 1;  -- balance=100

-- 동시에 tx2
BEGIN;
UPDATE accounts SET balance = 200 WHERE id = 1;
COMMIT;  -- tx2 끝

-- tx1 다시
SELECT * FROM accounts WHERE id = 1;  -- *여전히 balance=100*  ★
COMMIT;
```

→ *tx1 은 *자기 snapshot* 만 봄. *tx2 의 변경 은 tx1 안 에 *안 보임*.

이게 *Read Committed (PostgreSQL 기본)* 또는 *Repeatable Read* 의 *동작*. 다음 챕터 참조.

---

## 5. *본질 4 — *Isolation Level 4 종*

### 5.1 *3 가지 anomaly*

| Anomaly | 의미 |
|---|---|
| **Dirty Read** | *다른 tx 의 *commit 안 한 변경* 을 *읽음* |
| **Non-repeatable Read** | *같은 query 를 *두 번 실행* 했는데 *결과 가 다름* (다른 tx 가 commit) |
| **Phantom Read** | *같은 range query 를 *두 번* 했는데 *row 가 늘어남* (다른 tx 가 insert + commit) |

### 5.2 *4 isolation level*

| Level | Dirty Read | Non-repeatable | Phantom | 동시성 |
|---|---|---|---|---|
| **Read Uncommitted** | ⚠️ 가능 | ⚠️ 가능 | ⚠️ 가능 | 최고 |
| **Read Committed** (PostgreSQL 기본) | ❌ 차단 | ⚠️ 가능 | ⚠️ 가능 | 높음 |
| **Repeatable Read** (MySQL 기본) | ❌ | ❌ 차단 | ⚠️ 가능 (MySQL은 차단) | 중간 |
| **Serializable** | ❌ | ❌ | ❌ 차단 | 낮음 |

> *PostgreSQL 의 *Read Committed = MVCC snapshot 이 *매 statement 마다 새로 잡힘*.
> *PostgreSQL 의 *Repeatable Read = snapshot 이 *tx 시작 시 *한 번 잡히고 *유지*.

### 5.3 *Lost Update — *Read Committed 의 *고전 함정***

```sql
-- tx1: 잔액 보고 10 빼기
BEGIN;
SELECT balance FROM accounts WHERE id = 1;   -- 100
-- (애플리케이션 코드: new_balance = 100 - 10 = 90)
UPDATE accounts SET balance = 90 WHERE id = 1;
COMMIT;

-- 동시에 tx2: 잔액 보고 20 빼기
BEGIN;
SELECT balance FROM accounts WHERE id = 1;   -- 100
-- (애플리케이션 코드: new_balance = 100 - 20 = 80)
UPDATE accounts SET balance = 80 WHERE id = 1;
COMMIT;

-- 최종 balance = 80 (또는 90 — 마지막 commit 의 승리)
-- 진짜는 100 - 10 - 20 = 70 이어야 함 ★
```

이게 *Lost Update*. *Read Committed 에선 *방어 못 함*.

**해결책 3 가지**:

1. **Optimistic Lock (version 컬럼)**:
```sql
UPDATE accounts SET balance = 90, version = 2
WHERE id = 1 AND version = 1;  -- ← 변경된 행 수 0 면 retry
```
JPA `@Version` 어노테이션 의 본질.

2. **Pessimistic Lock**:
```sql
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
-- 다른 tx 는 이 row 의 SELECT FOR UPDATE / UPDATE 시 *대기*
```
JPA `@Lock(PESSIMISTIC_WRITE)`.

3. **Atomic UPDATE — *읽고 쓰기를 *한 번 에***:
```sql
UPDATE accounts SET balance = balance - 10 WHERE id = 1;
-- ← DB 가 *원자 적으로 *처리*. 가장 단순 + 빠름
```

→ **돈 / 재고 / 카운트** 같은 *strict* 수치 는 *Atomic UPDATE 또는 *Pessimistic Lock 권장*.

### 5.4 *Repeatable Read 의 *PostgreSQL 변형*

PostgreSQL 의 *Repeatable Read* 는 *snapshot isolation*. *Phantom Read 도 차단* (단순한 Repeatable Read 정의보다 강함).

```sql
-- tx1 (Repeatable Read)
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM orders WHERE status = 'PENDING';  -- 100

-- tx2
INSERT INTO orders (...) VALUES (..., 'PENDING');
COMMIT;

-- tx1
SELECT count(*) FROM orders WHERE status = 'PENDING';  -- 여전히 100  ★
COMMIT;
```

→ *PostgreSQL Repeatable Read* 는 *Serializable 에 가까운 *snapshot 일관성*.

### 5.5 *Serializable — *직렬화 가능 의 보장***

PostgreSQL 의 *Serializable Snapshot Isolation (SSI)* :
- *각 tx 의 *read/write 가 *직렬 실행* 한 *어느 순서 와 *같은 결과* 가 *반드시 존재*
- *anomaly 검출 시 *한 tx 를 *abort* 시킴 (`could not serialize access`)
- 애플리케이션 이 *retry* 해야 함

```java
@Retryable(value = SerializationFailureException.class, maxAttempts = 5)
@Transactional(isolation = Isolation.SERIALIZABLE)
public void transfer(long from, long to, BigDecimal amount) {
    ...
}
```

→ *금융 / 정산* 처럼 *정합성 절대* 인 곳에서. *대신 *throughput 손해*.

---

## 6. *본질 5 — *Locking*

### 6.1 *Lock 의 *세밀도*

| 종류 | 범위 |
|---|---|
| **Row-level lock** | 한 row (PostgreSQL / InnoDB 의 기본) |
| **Page-level lock** | 8KB 또는 16KB 단위 |
| **Table-level lock** | 전체 테이블 (DDL, 명시적 LOCK TABLE) |
| **Advisory lock** | *애플리케이션 의 *임의 키* — DB 외부 자원 mutex |

### 6.2 *PostgreSQL row lock 의 *모드*

```sql
-- 약한 → 강한 순서
SELECT ... FOR KEY SHARE;        -- *FK 검증 용*
SELECT ... FOR SHARE;            -- *읽기 잠금* (다른 SHARE 와 호환)
SELECT ... FOR NO KEY UPDATE;    -- *update 예정 (FK 는 안 건드림)*
SELECT ... FOR UPDATE;           -- *update 예정 (모든 잠금 차단)*
```

→ **`FOR UPDATE`** 가 *전형적인 비관적 락*. *해당 row 가 *다른 tx 의 *SELECT FOR UPDATE / UPDATE 를 *block*.

### 6.3 *Deadlock — *원형 wait***

```
tx1: UPDATE accounts WHERE id = 1;  (lock id=1)
tx2: UPDATE accounts WHERE id = 2;  (lock id=2)

tx1: UPDATE accounts WHERE id = 2;  ← tx2 가 잠금 → tx1 wait
tx2: UPDATE accounts WHERE id = 1;  ← tx1 이 잠금 → tx2 wait

→ Deadlock!
```

PostgreSQL deadlock detector :
- *deadlock_timeout* (default 1초) 후 *원형 wait 검출*
- *희생자 tx 한 명* 을 *abort* — `deadlock detected` 에러

**예방 패턴**:
- *모든 tx 가 *같은 순서* 로 row 접근 (id 정렬)
- *짧은 tx + 짧은 critical section*
- *advisory lock 으로 *순서 강제* 가능

### 6.4 *Advisory Lock — *DB 외부 자원 mutex***

```sql
-- "user 42 의 점수 갱신" 작업 mutex
SELECT pg_advisory_lock(42);   -- 다른 tx 가 *42* 잡고 있으면 wait
-- (작업 ...)
SELECT pg_advisory_unlock(42);
```

→ *cron job 의 *single-instance* 보장, *외부 API 호출 의 *동시성 제어* 등. *row 단위 lock 의 비교적 가벼운 대안*.

---

## 7. *본질 6 — *WAL (Write-Ahead Logging)*

### 7.1 *왜 *WAL 인가*

DB 가 *crash 후 *데이터 일관성 보장* 하려면 :
- *변경 을 *page 에 직접 쓰기* 전 *log 에 먼저 기록*
- *Crash 후 *log 재생* 으로 *완전한 상태 복원*

→ *Durability (D in ACID) 의 *물리적 토대*.

### 7.2 *PostgreSQL WAL 의 *구조*

```text
[Client COMMIT]
   ↓
[WAL buffer (RAM)]
   ↓
[WAL file 에 fsync]  ← *commit 대기 의 *진실*
   ↓
[Client 에게 OK]
                                                  (async)
                                                     ↓
                                              [page cache 의 dirty page]
                                                     ↓
                                              [data file 에 flush]
```

→ *commit latency 의 *핵심* 은 *WAL fsync 한 번*. *data file flush 는 *background*.

### 7.3 *Performance 와 *Durability 의 *trade-off***

```sql
-- PostgreSQL 의 *3 가지 commit 모드*
SET synchronous_commit = on;            -- *기본*. WAL fsync 대기.
SET synchronous_commit = off;           -- WAL fsync 안 기다림. ★ *crash 시 *최근 commit 손실*
SET synchronous_commit = remote_apply;  -- *replica 가 *apply 완료* 까지 대기 (synchronous replication)
```

`synchronous_commit = off` 시 *throughput 10x 증가*, *그러나 commit 후 *최대 *3 wal_writer_delay (~300ms)* 의 *데이터 손실 가능*.

→ *분석 / log 적재* 처럼 *간헐 적 손실 OK 한 워크로드* 에서. *결제 / 정산 은 *반드시 on*.

### 7.4 *Checkpoint — *WAL 정리***

WAL 은 *무한 누적 안 함*. *주기적 으로*:
- *Dirty page 를 *data file 에 모두 flush*
- *그 시점 까지 의 WAL 폐기 가능*

```sql
-- checkpoint 빈도 / I/O 영향
SHOW checkpoint_timeout;     -- 기본 5min
SHOW max_wal_size;            -- 기본 1GB
```

→ *너무 자주 checkpoint* = *I/O spike*. *너무 드물면 *crash recovery 시간 길어짐*. 대용량 워크로드 는 *max_wal_size 늘림* (예: 4GB).

### 7.5 *우리 클러스터 의 *etcd WAL 사례*

[*K8s 클러스터 outage 회고*](/2026/06/21/github-pat-expiry-13-pods-down-3-prevention-patterns.html) 에서 본 *솔로몬 etcd SSD 이전* (2026-06-06) — *etcd WAL 의 *fsync 가 *느린 디스크* 였던 게 *etcd p99 latency 폭증* 의 원인. *Intel DC S3700 SSD 로 이전* 후 *latency 극적 개선*.

→ DB 든 etcd 든 *WAL = commit 의 진실*. *디스크 fsync 성능 이 *시스템 의 *throughput 상한*.

---

## 8. *본질 7 — *Replication, Sharding*

### 8.1 *Replication 4 모드*

| 모드 | 의미 |
|---|---|
| **Physical (PostgreSQL Streaming Replication)** | *primary 의 WAL 을 *replica 가 *그대로 적용*. byte-level 복제 |
| **Logical** | *INSERT/UPDATE/DELETE 만 복제* — *schema 다른 DB 간 가능* |
| **Synchronous** | primary 가 *replica 의 *적용 대기* 후 commit OK 반환 |
| **Asynchronous** | primary 가 *replica 의 적용 안 기다림*. *replica lag* 가능 |

### 8.2 *Synchronous Replication 의 *대가***

```sql
-- PostgreSQL primary
SET synchronous_standby_names = 'replica1, replica2';
-- commit 시 primary 가 replica1 / replica2 *둘 다* WAL 받을 때까지 대기
```

→ *데이터 손실 0 보장*. *commit latency = max(primary fsync, replica fsync, network)* 로 *증가*.

*Synchronous 의 *치명적 함정* : *replica 가 *down 되면 *primary 도 commit 못 함*. *quorum-based* 패턴 권장.

### 8.3 *Async Replication 의 *replica lag***

```
primary: tx commit 완료
   ↓ (network delay, replica apply delay)
replica: 그 commit 적용 완료

이 사이 *수 ms ~ 수 분* 동안 *replica 가 *옛 상태* 봄
```

전형적 *bug* :
```java
// primary 에 write
orderRepo.save(order);
// replica 에 read (load balancer 가 replica 라우팅)
Order saved = orderRepo.findById(order.getId());  // ← 못 찾을 수 있음!
```

**해결**:
- *Read-your-writes consistency* — *방금 write 한 tx 의 *후속 read 는 *primary 로*
- *Session affinity* — *동일 session 의 모든 query 가 *primary*
- *Causal consistency* — *application 이 *각 read 의 *최소 LSN 명시*

### 8.4 *Logical Replication — *cross-version / cross-schema 마이그레이션***

```sql
-- primary
CREATE PUBLICATION my_pub FOR TABLE orders;

-- replica
CREATE SUBSCRIPTION my_sub CONNECTION 'host=primary user=...' PUBLICATION my_pub;
```

용도:
- *PostgreSQL 14 → 17 무중단 업그레이드*
- *읽기 전용 datawarehouse 분기*
- *Microservice 간 *Change Data Capture (CDC)* — Debezium 의 본질

### 8.5 *Sharding — *수평 분할***

```
Single DB:
   orders 테이블 — 10억 row
       ↓ shard by user_id
Sharded:
   shard-0: orders WHERE user_id % 4 == 0  — 2.5억 row
   shard-1: orders WHERE user_id % 4 == 1
   shard-2: orders WHERE user_id % 4 == 2
   shard-3: orders WHERE user_id % 4 == 3
```

**문제**:
- *Cross-shard query* — *느리고 복잡* (예: `SELECT * FROM orders` — 4 shard 를 *모두 *fan-out*)
- *Cross-shard transaction* — *2PC 또는 Saga 필요*
- *Rebalancing* — *shard 추가 시 *데이터 재배치*

→ *대부분 의 경우* *read replica + caching 이 *충분*. *Sharding 은 *최후 의 수단*. *Vitess, Citus* 가 *PostgreSQL/MySQL sharding 의 대표*.

---

## 9. *부록 — *연결 풀 + Query Plan*

### 9.1 *Connection Pool 의 *진실***

```java
// HikariCP
spring.datasource.hikari:
  maximum-pool-size: 20
```

20 의 의미:
- *Java 앱 의 *최대 20 동시 DB 호출*
- *그 이상 의 요청 은 *connection 풀에서 *대기*

**N 인스턴스 의 *DB 연결 상한*** :
```
인스턴스 5 × pool 20 = 100 동시 연결
+ ArgoCD, batch, monitoring 등 ~30
+ PostgreSQL 의 max_connections = 100
→ 충돌! 일부 인스턴스 가 *연결 못 받음*
```

→ *(인스턴스 수 × 풀 크기) ≤ max_connections × 0.8* 이 *권장 공식*.

**PgBouncer** :
- *애플리케이션 ↔ PgBouncer ↔ PostgreSQL*
- *수천 클라이언트 의 *수백 연결 다중화*
- *transaction-pooling* 모드 의 *cost 0 동시성 확대*

### 9.2 *EXPLAIN ANALYZE — *plan 의 진실***

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.* FROM orders o WHERE o.user_id = 42;

/*
Index Scan using idx_orders_user_id on orders  (cost=0.42..8.44 rows=1)
  Index Cond: (user_id = 42)
  Buffers: shared hit=4
Planning Time: 0.123 ms
Execution Time: 0.345 ms
*/
```

**핵심 신호** :
- *Seq Scan* : *index 없음 또는 *plan 이 *full scan 선택*. 큰 테이블 면 *경고*.
- *rows estimate* vs *actual rows* 차이 → *통계 outdated*. `ANALYZE` 필요.
- *Buffers* : *shared hit* (cache) vs *read* (disk). *disk read 많으면 *느림*.
- *Sort method* : *quicksort (RAM) vs external merge (disk)*. *work_mem 부족 시 disk*.

### 9.3 *느린 쿼리 탐지*

```sql
-- pg_stat_statements
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

→ 시간 차지 top 20 쿼리 *식별*. *N+1 의심* 또는 *missing index* 의 *증거*.

---

## 10. *체크리스트 — *DB 본질 의 실전*

내가 *코드 리뷰* 또는 *production 진단* 시 *반드시 확인* 하는 *15 가지* :

**Schema / Index**:
1. *모든 FK 에 *index* 있는가 (cascade 성능 의 근간)
2. *큰 테이블 의 *WHERE 절 자주 쓰는 컬럼* 에 *index 있는가*
3. *Covering index 로 *heap fetch 줄일 수 있는 쿼리* 가 있는가
4. *soft-delete 필드 에 *partial index 적용* 했는가

**Transaction / Isolation**:
5. *돈 / 재고 / 잔액 변경* 코드 가 *Atomic UPDATE 또는 *FOR UPDATE 사용 하는가
6. *@Transactional 안* 에서 *외부 API 호출 / 큰 계산* 없는가 (트랜잭션 길이)
7. *Repeatable Read / Serializable 이 *필요한 영역* 에서 *Read Committed 쓰는가*
8. *Lost update 위험* 있는 코드 에 *@Version 또는 *FOR UPDATE*

**Locking**:
9. *Deadlock 위험* 있는 path 가 *접근 순서 일관* (id 정렬) 한가
10. *Advisory lock* 으로 *cron / 외부 호출 single-instance 보장 하는가*

**Replication / Pool**:
11. *Read-your-writes* 필요한 후속 read 가 *primary 로 라우팅* 하는가
12. *연결 풀 크기 × 인스턴스 수* 가 *DB max_connections 의 80% 미만* 인가
13. *PgBouncer / connection pooler* 사용 검토 했는가

**모니터링**:
14. *pg_stat_statements* 로 *느린 쿼리 모니터링* 하는가
15. *autovacuum 이 잘 도는가* (n_dead_tup 폭증 알람)

---

## 11. *결론 — *추상화 의 *물리적 근거***

> ORM 위에서 *추상적 으로 보이는 *DB 동작* 의 *밑* 에 *B+Tree*, *MVCC*, *WAL*, *Replication* 의 *물리* 가 *놓여있다*.

오늘 정리한 *7 본질*:
1. **Storage Engine** — B+Tree vs LSM 의 *워크로드 매핑*
2. **Index** — clustered / secondary / covering / partial / GIN / BRIN / HNSW
3. **MVCC** — *읽기와 쓰기 의 분리* 의 *비용 (옛 버전 누적, vacuum 의무)*
4. **Isolation Level** — *4 종 의 anomaly 차단 정도*
5. **Locking** — *row / advisory / deadlock 의 wait-for graph*
6. **WAL** — *Durability 의 *물리적 토대*, *replication 의 *공통 어휘*
7. **Replication / Sharding** — *physical / logical, sync / async, *scale-out 의 한계*

> *ORM 의 *추상화* 가 *어디서 깨지는지* 알려면 *그 *추상화 가 *어떤 SQL 로 변환* 되고, *그 SQL 이 *어떤 plan 으로 실행* 되며, *그 plan 이 *어떤 index / lock / version 위에서 도는지* — 그 *내려가는 추적* 이 *시니어 백엔드 의 깊이*.

*수만 줄 의 *비즈니스 로직* 위에서 *0.1 줄 의 *잘못된 transaction 경계* 가 *production 의 정합성 사고* 를 만든다. *그 0.1 줄 을 *예방 하는 시야* — *DB 본질 의 7 가지* 가 *그 시야 의 *각 도구*.

*"ORM 이 *알아서 해준다"* 는 말 의 *진실* 은 *"내가 *알아야 할 *7 가지* 의 *어디서 깨질지 *알아채야* *ORM 이 *알아서 해준 결과 가 *신뢰 가능* 하다"* 는 것.

---

## *참고*

- *Designing Data-Intensive Applications* (Martin Kleppmann) — *7 본질 의 *대부분 의 깊이*.
- *Database Internals* (Alex Petrov) — *Storage Engine 의 *물리적 깊이*.
- *PostgreSQL 공식 문서* — [postgresql.org/docs](https://www.postgresql.org/docs/).
- *Vlad Mihalcea* 의 블로그 — *Hibernate / JPA performance* 의 *현장 적 reference*.
- *Use the Index, Luke!* (Markus Winand) — *Index 의 *모든 것*.
- *Jepsen* — *isolation 의 *실제 검증* (어느 DB 가 *주장 한 isolation 을 *진짜 지키는가*).
- 자매편 :
  - [*I/O 병목 해결*](/2026/06/18/io-bottleneck-how-to-solve.html) — *N+1, Connection pool 의 *물리*
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *DB 암호화*
  - [*GitHub PAT 만료 사고*](/2026/06/21/github-pat-expiry-13-pods-down-3-prevention-patterns.html) — *현장 사고 회고*
