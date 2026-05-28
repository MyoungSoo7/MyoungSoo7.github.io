---
layout: post
title: "SQL · PL/SQL — *생성형 AI 시대* 의 *시니어 백엔드 개발자가 *진짜 *배워야 할 *3 가지 *층*"
date: 2026-05-29 03:05:00 +0900
categories: [database, sql, ai, career]
tags: [sql, plsql, oracle, postgresql, generative-ai, claude, copilot, execution-plan, query-optimization, dba, senior-engineer]
---

> *''*ChatGPT 가 *SQL 을 *기가 막히게 *써준다*. *근데 *왜 *시니어 *DBA / *백엔드 *시니어가 *여전히 *연봉이 *높을까?''*''*. 이 질문에 *정직하게* 답하지 못하면, *''*SQL 은 *AI 가 *대체할 *분야''* 라는 *반쪽 진실에 *속아 *5 년 뒤 *후회한다*.
>
> 생성형 AI 는 *SQL 의 *어떤 부분은 *완벽히 대체*, *어떤 부분은 *전혀 못 함*. *그 경계를 *모르고 *''*나는 SQL 공부 *안 해도 *되겠다''* 라고 결정하면, *''*production 에서 *DB 가 *터지는 순간*'' *AI 에게 *''*살려달라''* 라고 *복사 - 붙여넣기 *돌리다 *시간 *수십 시간 *날린다*.

이 글은 *생성형 AI 시대* 에 *SQL 과 PL/SQL 을 *어떻게 학습 할 것인가* 를 *시니어 백엔드 *관점에서 *3 가지 층* 으로 정리한다. *각 층에서 *AI 가 *어디까지 도와주고*, *어디서부터 *시니어의 *판단* 이 *결정적인가* 를 *현장에서 다친 흔적* 위주로.

대상은 *''*ORM 만 쓰다가 *production 장애 한 번 *경험한 *주니어 / 미들 백엔드 *개발자*'' 와 *''*AI 가 SQL 다 써주는데 *내가 굳이 *공부해야 하나''* 라고 *진지하게 *고민하는 *모든 개발자*.

---

## 1. 출발 — *''*AI 가 *SQL 을 *어디까지 *할 수 있는가''*

### 1.1 *2026 년 *현실*

Claude 4.7 / GPT-5 / Copilot 에 *다음을 요청* 해보면 *놀랍게 *잘 해준다*:

- *''*orders 테이블에서 *지난 30 일간 *고객별 *총 구매액 *상위 10 명 SQL 짜줘''*
- *''*이 PL/SQL *프로시저를 *PostgreSQL 의 *PL/pgSQL 로 *변환해줘''*
- *''*이 *쿼리가 *왜 느린지 *분석해줘 — *EXPLAIN 결과 *붙임*''*
- *''*이 자연어 요청을 *SQL 로 바꿔줘 — *''*월별 매출이 *전월 대비 *20% 이상 증가한 *상품 카테고리''*''

**거의 완벽**. 주니어가 *3 시간 걸리던 *작업이 *2 분 *만에 *끝남*.

### 1.2 *그런데 *왜 *시니어가 *여전히 *필요한가**

다음 시나리오에서 *AI 가 *멈춤*:

- *''*production DB 가 *지금 *CPU 99% *로 *죽어가는 중*. 어떤 쿼리가 *원인인지 *모름. *5 분 안에 *해결''*
- *''*어떤 *인덱스를 *추가해야 *4 개 슬로 쿼리는 *살리고 *2 개 *기존 쿼리는 *안 깨지는지''*
- *''*이 *비즈니스 요구를 *''*read-heavy *읽기 모델''* 로 *어떻게 *모델링하고, *어떤 *isolation level 에 *어떤 *normal form 으로 *어디서 *역정규화 할지''*
- *''*Flyway / Liquibase 마이그레이션을 *production 에 *적용할 때 *5 천만 *행 *테이블에 *NOT NULL 컬럼 추가''*

이 *시나리오들의 *공통점*:
- *''*정답이 *하나가 *아님''*
- *''*상황 의존적 (context-dependent)''*
- *''*틀린 결정 = *production *터짐 / 데이터 손실''*
- *''*되돌릴 수 없음''*

> **시니어의 진짜 자산** = *''*이런 *비결정적 상황에서 *최선의 *판단을 *내릴 수 있는 *경험 + 직관*''*. *AI 는 *''*평균적인 *정답''* 은 *잘 *내지만 *''**이 상황의 *최선''* 은 *못 *낸다*.

---

## 2. *3 가지 *층* — *시니어가 *알아야 할 *우선순위*

```
[Level 3]  비즈니스 모델링 (Modeling)
            ├─ 정규화 / 역정규화 트레이드오프
            ├─ Read vs Write 분리
            ├─ Sharding / Partitioning 전략
            └─ 트랜잭션 경계 설계

[Level 2]  성능 / 안전 (Performance & Safety)
            ├─ 실행 계획 읽기 (EXPLAIN ANALYZE)
            ├─ 인덱스 설계
            ├─ Lock / Deadlock / Isolation
            └─ Migration 안전 (5천만 행에 컬럼 추가)

[Level 1]  SQL 문법 (Syntax)
            ├─ SELECT / JOIN / WHERE
            ├─ GROUP BY / Window function
            ├─ CTE / Subquery
            └─ Stored procedure / Trigger
```

### 2.1 *각 *층의 *''*AI 대체 가능성''*

| Level | 내용 | AI 대체율 | 시니어 *필요도 |
|---|---|---|---|
| **Level 1** | 문법 / 단순 쿼리 | *90%+* | *낮음* — *AI 가 *대부분 *처리* |
| **Level 2** | 실행 계획 / 인덱스 / Lock | *30 ~ 60%* | *높음* — *AI 가 *진단은 *돕지만 *결정은 *못 함* |
| **Level 3** | 모델링 / 트랜잭션 경계 | *10 ~ 30%* | *극단적으로 *높음* — *''*비즈니스 + 기술 + 미래 변화''* 의 *3 축 종합 판단* |

> **결론 한 줄**: ***''*Level 1 은 *AI 에 *맡기고*, Level 2 ~ 3 에 *시니어가 *집중* 한다''*** 가 *2026 년 *학습 전략의 *방향*.

---

## 3. *Level 1* — *''*SQL 문법 — *AI 에 *맡겨도 되는 *부분**

### 3.1 *최소한 *알아야 하는 *것들*

SQL 의 *문법 전체* 를 *외울 필요는 *없지만, *''*AI 가 *틀린 답을 *내면 *즉시 *알아챌 수 있는 *수준''* 은 *필요*.

#### *반드시 *몸으로 알기*
- `SELECT`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT/OFFSET`
- `INNER JOIN`, `LEFT/RIGHT/FULL OUTER JOIN`
- *Subquery / CTE (`WITH`)* — *복잡한 쿼리의 *기본 도구*
- *Window function* (`ROW_NUMBER`, `RANK`, `LAG`, `LEAD`, `SUM() OVER (...)`)
- *집계 함수* (`COUNT`, `SUM`, `AVG`, `MIN/MAX`)
- `UNION` / `UNION ALL` / `INTERSECT` / `EXCEPT`

#### *읽을 줄만 *알면 되는 *것들*
- *PIVOT / UNPIVOT*
- *Recursive CTE*
- *JSON 함수* (PostgreSQL `jsonb_path_query`, MySQL `JSON_EXTRACT`)
- *DB 별 *특수 함수*

### 3.2 *AI 와 함께 *Level 1 *학습하는 *법*

```
[좋은 학습 패턴]
1. 자연어로 *요구 작성*
2. AI 에게 *SQL 작성 *요청*
3. *AI 의 답을 *읽고 *왜 그렇게 *짰는지 *나만의 *말로 *재설명*
4. 실제 DB 에 *돌려보고 *결과 검증*
5. *EXPLAIN 으로 *어떻게 실행되는지 *확인*

[나쁜 학습 패턴]
1. AI 에게 SQL 받음
2. *복사 - 붙여넣기*
3. *동작하면 *끝*
```

*''*받은 SQL 을 *3 분 *간 *해석할 수 있어야* *학습이 *된다*''. *''*해석 못 하는 *5 줄 SQL 을 *production 에 *넣는 순간*'' *''*나중에 *내가 *디버깅 해야 *할 때 *나는 *그것을 *모름''*.

### 3.3 *함정* — *''*AI 가 *자주 *틀리는 *부분**

#### **함정 1 — *NULL 처리***

```sql
-- AI 가 자주 짜는 *틀린* 쿼리
SELECT * FROM users WHERE deleted_at != '2026-05-29';
-- 문제: NULL != '...' 은 *NULL 을 반환*. NULL 행이 *제외됨*.

-- 정답
SELECT * FROM users
 WHERE deleted_at IS NULL OR deleted_at != '2026-05-29';
```

#### **함정 2 — *GROUP BY 와 *집계의 *모호함***

```sql
-- 표준 SQL 에서 *오류*, MySQL 의 *비표준 동작* 으로 *통과될 수도*
SELECT customer_id, MAX(amount), product_name
  FROM orders
 GROUP BY customer_id;
-- 문제: product_name 이 *어느 행의 값인지 모호*. *비결정적*.
```

#### **함정 3 — *Date / Timezone***

```sql
-- AI 가 *''*server timezone 가정''* 한 쿼리
SELECT * FROM events WHERE created_at >= '2026-05-29';
-- production server 가 UTC, 사용자는 KST 라면 *9 시간 *어긋남*
```

> **시니어의 차이**: *''*이 3 가지 함정을 *AI 가 *자주 만들어내는 *것을 *알고 있음*''*. *''*AI 의 답을 *그대로 *받지 않고 *교정''*.

---

## 4. *Level 2* — *''*성능 / 안전 — *시니어의 *진짜 영역**

이 영역에서 *AI 가 *''*도와주는 *조수''* 는 되지만 *''*결정하는 *시니어''* 가 *반드시 필요* 하다.

### 4.1 *EXPLAIN / EXECUTION PLAN — *''*쿼리의 *실제 동작을 *읽는 *눈''*

```sql
EXPLAIN ANALYZE
SELECT o.id, c.name
  FROM orders o
  JOIN customers c ON o.customer_id = c.id
 WHERE o.created_at >= '2026-05-01'
   AND o.status = 'PAID';
```

```
Hash Join  (cost=125.32..1234.56 rows=5000 width=64) (actual time=3.214..125.678 rows=4823 loops=1)
  Hash Cond: (o.customer_id = c.id)
  ->  Seq Scan on orders o  (cost=0.00..1000.00 rows=10000 width=32)
        Filter: ((created_at >= '2026-05-01') AND (status = 'PAID'))
        Rows Removed by Filter: 90000
  ->  Hash  (cost=100.00..100.00 rows=2000 width=32)
        ->  Seq Scan on customers c  (cost=0.00..100.00 rows=2000 width=32)
Planning Time: 0.234 ms
Execution Time: 128.456 ms
```

#### *시니어가 *읽어야 하는 *5 가지 신호*

1. **`Seq Scan` vs `Index Scan`** — *index 가 *쓰이고 있는가*
2. **`Rows Removed by Filter: 90,000`** — *''*10 만 행 읽고 9 만 행 버림''* → *인덱스 추가 후보*
3. **`actual time` vs `cost`** — *cost 가 낮아도 *실제 *느리면 *통계 오래됨* (`ANALYZE` 필요)
4. **`loops`** — *바깥 *루프 *횟수 *× 안쪽 *비용 = *총 비용*
5. **`Nested Loop` vs `Hash Join` vs `Merge Join`** — *각자 *언제 *최적 *인지*

### 4.2 *인덱스 설계 — *''*B-Tree, *Composite, Covering, Partial*''*

#### *B-Tree Index 의 *기본*

```sql
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

*''*B-Tree 는 *=, <, >, BETWEEN, IN, LIKE 'foo%' *에 효과*''*. *`LIKE '%foo'` 은 *효과 없음*''*.

#### *Composite Index 의 *순서*

```sql
-- Index 1
CREATE INDEX idx_a ON orders(customer_id, created_at);
-- Index 2
CREATE INDEX idx_b ON orders(created_at, customer_id);
```

이 *두 인덱스는 *완전히 다른 동작*. *''*컬럼 순서가 *쿼리 패턴과 *맞아야 효과*''*:

- `WHERE customer_id = ? AND created_at >= ?` → *Index 1 효과*
- `WHERE created_at >= ?` → *Index 2 효과*
- `WHERE customer_id = ?` → *Index 1 효과*

> **시니어의 *암묵 *원칙**: *''*Equality (=) 가 *앞, *Range (>, <) 가 *뒤* — composite 의 *황금 규칙*''*.

#### *Covering Index — *''*인덱스만으로 *쿼리 답할 수 있게**

```sql
-- 쿼리
SELECT customer_id, amount FROM orders WHERE status = 'PAID';

-- Covering index — *''*인덱스에 *답이 *다 있음''*
CREATE INDEX idx_orders_paid_covering
   ON orders(status) INCLUDE (customer_id, amount);
```

*''*테이블 행을 *읽지 *않고 *인덱스 *페이지만으로 *답함''*. *수십 배 *빠름*.

#### *Partial Index — *''*조건 만족 행에만 인덱스**

```sql
CREATE INDEX idx_orders_pending
    ON orders(created_at)
 WHERE status = 'PENDING';
```

*''*PENDING 이 *전체의 1%* 면 *전체 인덱스 1% 크기*''*. *''*PENDING 쿼리 *압도적 빠름*''*.

### 4.3 *Lock 과 *Isolation Level — *''*동시성의 *진짜 비용''*

| Isolation Level | 가능한 문제 | 사용처 |
|---|---|---|
| **READ UNCOMMITTED** | Dirty Read | *거의 안 씀* |
| **READ COMMITTED** | Non-repeatable read, Phantom | *PostgreSQL 기본*, *대부분의 *서비스 적합* |
| **REPEATABLE READ** | Phantom (PG 는 SI 로 막음) | *MySQL InnoDB 기본*, *PG 에서 *MVCC* |
| **SERIALIZABLE** | (없음) | *''*돈 관련 *비즈니스* — *느림*''* |

#### *Lock 의 *진짜 비용 *예시*

```sql
-- 트랜잭션 A
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- ... *5 초 동안 *다른 작업 *...
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

-- 트랜잭션 B (동시에)
BEGIN;
UPDATE accounts SET balance = balance - 50 WHERE id = 2;
UPDATE accounts SET balance = balance + 50 WHERE id = 1;
-- → *Deadlock*. 트랜잭션 *하나 *Rollback*
COMMIT;
```

> **시니어의 *판단***: *''*트랜잭션 *순서를 *전 시스템 *통일 (예: ID 작은 순)''*. *''*트랜잭션 시간 *최소화''*.

### 4.4 *Migration 안전 — *''*5 천만 행에 *컬럼 추가**

```sql
-- ❌ 위험 — *전체 *테이블 *락*
ALTER TABLE orders ADD COLUMN refund_status VARCHAR(20) NOT NULL DEFAULT 'NONE';

-- ✅ 안전 패턴 (PostgreSQL 11+)
-- 1) Nullable 컬럼 *추가* (메타데이터만 변경, 즉시)
ALTER TABLE orders ADD COLUMN refund_status VARCHAR(20);

-- 2) 배치로 *값 채우기*
UPDATE orders SET refund_status = 'NONE' WHERE id BETWEEN 1 AND 10000;
-- ... 반복 ...

-- 3) NOT NULL 제약 추가
ALTER TABLE orders ALTER COLUMN refund_status SET NOT NULL;

-- 4) DEFAULT 추가
ALTER TABLE orders ALTER COLUMN refund_status SET DEFAULT 'NONE';
```

*''*Postgres 11 부터는 *NOT NULL + DEFAULT 가 *메타데이터만 *변경* 으로 *즉시 가능*''*. *''*이전 버전은 *수십 분 *락*''*.

> **시니어의 *암묵 지식**: *''*Migration 적용 전에 *production *유사 환경에서 *실제 *수십 GB 데이터로 *시간 측정 *필수* — *AI 는 *이걸 *안 해줌*''*.

### 4.5 *AI 와 함께 *Level 2 *학습하는 *법*

```
1. EXPLAIN ANALYZE 결과를 *AI 에 *붙여넣고 *''*이 쿼리 왜 느린가''* 질문
2. AI 의 *진단을 *받되, *''*직접 EXPLAIN 결과를 다시 *읽으며 *검증*'''
3. *AI 추천 *인덱스를 *그대로 *적용하지 않고 *''*기존 인덱스 영향 *분석*'''
4. *Staging 환경에서 *실제 데이터로 *적용 *후 *측정*
5. *Production 적용은 *DBA 또는 *시니어 *검토 후*
```

---

## 5. *Level 3* — *''*비즈니스 모델링 — *AI 가 *가장 *못 하는 영역**

### 5.1 *정규화 vs *역정규화의 *트레이드오프**

```
[정규화 (3NF)]
  + 데이터 무결성 ↑
  + 저장 효율 ↑
  − 조회 시 JOIN 폭증 → *읽기 느림*

[역정규화]
  + 읽기 빠름 (JOIN 없음)
  − 데이터 *중복* → *동기화 부담*
  − Update 시 *여러 곳 갱신*
```

*''*Read : Write *비율''* 이 *결정 기준*:
- **Read >> Write (예: 검색, 통계)** — *역정규화 + 캐싱*
- **Write >> Read (예: 로그, 메트릭)** — *역정규화 OK, JOIN 무시*
- **Read ≈ Write (대부분의 OLTP)** — *정규화 *기본, *부분 역정규화*

> **시니어의 *판단***: *''*''*전부 정규화*'' 도, *''*전부 역정규화*'' 도 *틀림*. *''*테이블별 *컬럼별 *결정''* 이 *시니어의 *경험치*''*.

### 5.2 *Read / Write 분리 — *''*같은 데이터의 *2 가지 *시각*''*

```
[OLTP — 쓰기/짧은 읽기]
  ├─ 정규화된 *주 테이블
  ├─ 트랜잭션 *보장
  └─ 인덱스 *최소화* (쓰기 부담 줄임)

[OLAP — 분석 / 대량 읽기]
  ├─ Snowflake / Redshift / BigQuery
  ├─ 역정규화 + 컬럼 기반
  ├─ 인덱스 *적극*
  └─ Eventual consistency *OK*
```

CDC (Change Data Capture) 로 *주 → 분석 동기화*. *''*Debezium / Maxwell / DMS*''*.

### 5.3 *Sharding / Partitioning 전략*

#### *Partitioning — *''*같은 DB 안의 *분할**

```sql
CREATE TABLE orders (
  id BIGINT,
  customer_id BIGINT,
  created_at TIMESTAMP,
  ...
) PARTITION BY RANGE (created_at);

CREATE TABLE orders_2026_05 PARTITION OF orders
   FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

*''*오래된 *파티션은 *''*OLD 노드''* 로 *이동*, *최신은 *''*HOT 노드''*'' — *비용 ↓*.

#### *Sharding — *''*여러 DB 인스턴스에 *분할**

```
[Shard Key 결정의 *기로*]
  - Customer ID 로 분산 → *고객별 *조회 *빠름*, *Cross-customer 쿼리 *어려움*
  - Geographic 분산 → *지역별 *지연 ↓*, *지역 *불균형*
  - Hash 분산 → *균등*, *Range 쿼리 *불가*
```

> **시니어의 *결정**: *''*Sharding 은 *''*마지막 수단''*. *''*Read replica + Partitioning 으로 *해결되면 *Sharding 하지 마라''*''*. *''*Sharding 후 *되돌리기는 *수개월 *작업*''*.

### 5.4 *트랜잭션 *경계 설계*

```java
// 안티 패턴 — *트랜잭션이 *너무 큼*
@Transactional
public void processOrder(OrderCommand cmd) {
    var order = orderRepo.save(...);
    var payment = paymentGateway.charge(...);   // ← *외부 HTTP 호출 *5 초*
    inventoryService.reserve(...);
    emailService.send(...);                      // ← *외부 SMTP 호출 *3 초*
}
```

*''*트랜잭션이 *8 초 동안 *열려 있음''* → *DB connection *점유 → *connection pool 고갈 → *전체 서비스 마비*.

**해법** — *''*트랜잭션 경계 *작게, 외부 호출은 *밖에''*:

```java
public void processOrder(OrderCommand cmd) {
    var order = orderRepo.saveOrder(...);    // *짧은 트랜잭션
    var payment = paymentGateway.charge(...);  // *외부, 트랜잭션 *밖*
    eventPublisher.publish(new OrderPaid(...));  // *나머지는 *이벤트*
}
```

> **시니어의 *원칙***: *''*트랜잭션 = *DB 호출만*. *외부 호출 / 긴 작업은 *반드시 *밖''*.

---

## 6. *PL/SQL — *''*Oracle 시대의 *유산'' 을 *어떻게 봐야 하나*

### 6.1 *PL/SQL 의 *역사적 *위치*

PL/SQL 은 *Oracle 의 *Procedural Language extension for SQL*. *1991 년 출시*. *''*DB 안에서 *비즈니스 로직을 *실행''* 한다는 *철학*.

```sql
-- PL/SQL 예시
CREATE OR REPLACE PROCEDURE process_order (
    p_order_id IN NUMBER
) AS
    v_amount NUMBER;
    v_status VARCHAR2(20);
BEGIN
    SELECT amount, status INTO v_amount, v_status
      FROM orders WHERE id = p_order_id;

    IF v_status = 'PENDING' THEN
        UPDATE orders SET status = 'PAID' WHERE id = p_order_id;
        INSERT INTO order_log VALUES (p_order_id, SYSDATE, 'PAID');
    END IF;

    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END;
```

### 6.2 *''*DB 안에 *로직을 *넣자''* 의 *장단점*

#### *장점*
- *네트워크 *왕복 ↓ → *극단적으로 빠름*
- *데이터 *바로 옆에서 *처리 → *대량 batch 작업*
- *트랜잭션 *원자성 *자연스러움*

#### *단점*
- *''*비즈니스 로직이 *DB 에 *갇힘''* → *DB 교체 *수개월*
- *''*버전 관리 *어려움''* — Git 친화적이지 않음
- *''*테스트 *어려움''*
- *''*DB 인스턴스가 *비즈니스 로직 *부담까지 *떠안음''* → *확장성 *제약*
- *''*PL/SQL 개발자 *공급 *부족''* — *현장 인력 *희소화*

### 6.3 *2026 년 *현대적 *입장*

> *''*신규 시스템은 *PL/SQL *대신 *애플리케이션 *언어로**. *기존 PL/SQL 자산은 *''*점진적 *축소'' 가 *현실적''*.

#### *학습 우선순위*

| 상황 | PL/SQL 학습 *필요도 |
|---|---|
| *신입 / 신규 *시스템 *주력* | *낮음* |
| *기존 *공공 / 금융 *프로젝트 *유지보수* | *중간* (있으면 *경쟁력 ↑*) |
| *Oracle DBA 진로* | *높음* |
| *PostgreSQL PL/pgSQL* | *중간* — *PL/SQL 보다 *''*기능 함수''* 정도로* |

#### *AI 가 PL/SQL 에서 *돕는 부분*

- *Legacy PL/SQL → Java / Python *전환*
- *PL/SQL → PL/pgSQL *문법 변환*
- *''*긴 PL/SQL *프로시저 *읽고 *문서화''*

#### *AI 가 PL/SQL 에서 *못 하는 *부분*

- *''*기존 *수만 라인 *PL/SQL 의 *전체 흐름 *재설계''*
- *''*PL/SQL → 마이크로서비스 *전환의 *경계 결정''*
- *''*Oracle hint 와 *실행 계획 *튜닝''*

---

## 7. *AI 와 *시니어 *백엔드의 *공존 패턴**

### 7.1 *효과적인 *작업 분담**

```
[Junior + AI] = *Mid 수준 *생산성*
[Senior + AI] = *Senior × 2 ~ 3 *생산성*
```

같은 AI 인데 *결과 차이가 크다*. 이유:
- *시니어는 *''*AI 의 답이 *틀린 *순간''* 을 *바로 *인지*
- *시니어는 *''*AI 가 *놓친 *맥락''* 을 *질문에 *미리 넣음*
- *시니어는 *''*AI 가 *주는 *옵션''* 중 *최적을 *선택*

### 7.2 *''*Prompt 의 *3 단계 진화''*

```
[Level 1 — 초급]
"orders 테이블에서 최근 30일 매출 top 10 SQL 짜줘"
  → *AI 가 *''*평균적인 답''*

[Level 2 — 중급]
"orders 테이블 (5천만 행, customer_id/created_at 복합 인덱스 있음)에서
최근 30일 매출 top 10. 응답 100ms 안에 끝나야 함."
  → *AI 가 *''*인덱스 활용 답''*

[Level 3 — 시니어]
"orders 5천만 행, customer_id/created_at 복합 인덱스 있음.
파티셔닝은 created_at RANGE. 최근 30일 매출 top 10.
실행 계획에서 partition pruning + index-only scan 이 되어야 함.
CTE 와 window function 어느 게 더 빠를지 두 가지 모두 작성하고 비교."
  → *AI 가 *''*시니어의 *직관에 *근접한 답''*
```

**시니어의 prompt 는 *''*상황 + 제약 + 검증 기준''* 까지 *명시***.

### 7.3 *''*AI 가 *못 *주는 *것''*

- *''*production *경험에서 *온 *직관''*
- *''*실패에서 *배운 *''*다시는 안 함''* 의 *목록''*
- *''*같은 팀과 *5 년 *일한 *암묵적 *합의''*
- *''*비즈니스 *맥락 (CEO 의 *우선순위, 경쟁사 *움직임)''*

이 *4 가지가 *''*시니어의 *진짜 자산''*. *AI 는 *''*기술적 답안''* 만 *준다*.

---

## 8. *시니어 백엔드의 *2026 년 *학습 *권장 로드맵*

### 8.1 *6 개월 학습 계획 (월별)*

**Month 1 — *Level 2 *기초**
- EXPLAIN ANALYZE *읽는 법* 마스터
- B-Tree / Hash / GIN / GiST 인덱스 *각각 언제 쓰는지*
- *PostgreSQL 또는 *MySQL *하나 *깊게*

**Month 2 — *Lock 과 *Isolation*
- Lock 종류 (Row / Table / Advisory)
- *각 Isolation Level 의 *재현 가능한 *예제*
- *MVCC 의 *동작 원리*

**Month 3 — *대량 데이터 *운영*
- *Partitioning *실습
- *Slow query 추적 (`pg_stat_statements`)
- *vacuum / autovacuum *튜닝
- *Connection pooling (HikariCP, PgBouncer)*

**Month 4 — *Modeling*
- *DDD aggregate 를 *DB 스키마에 *매핑*
- *Event Sourcing + CQRS 의 *DB 측 *함의*
- *Outbox / Inbox 패턴*

**Month 5 — *Cloud DB *심화*
- *AWS RDS / Aurora 의 *내부*
- *Read Replica / Multi-AZ *전략*
- *Backup / PITR (Point-in-Time Recovery)*

**Month 6 — *통합 + 실전*
- *Migration *안전 패턴*
- *Production *사고 *사례 *분석*
- *''*내 회사 DB 의 *Top 10 슬로 쿼리''* 직접 *튜닝*

### 8.2 *학습 *자원 *순위*

1. **공식 문서** — *PostgreSQL / MySQL / Oracle *공식 문서가 *최고*
2. **Markus Winand, *''Use The Index, Luke!'**** — *index 의 *교과서*
3. **Joe Celko, *''SQL Programming Style'**** — *SQL 의 *철학*
4. **C. J. Date, *''Database Design and Relational Theory'**** — *모델링의 *근본*
5. **AWS / GCP 의 *DB 백서*** — *클라우드 환경의 *실무 가이드*
6. *내 회사 DB 의 *실제 슬로 쿼리* — *가장 비싼 *교과서*

### 8.3 *AI 와 함께 *학습 시 *주의 사항*

- *''*AI 가 *짠 SQL 을 *실행 전에 *반드시 *EXPLAIN*''*
- *''*Production 적용 전에 *staging 환경에서 *실제 데이터로 *검증*''*
- *''*Migration 은 *AI 추천이라도 *DBA / 시니어 *교차 검증*''*
- *''*복잡한 *비즈니스 로직은 *AI 에 *전부 위임 *금지*''*

---

## 9. 정리 — *''*시니어의 *3 가지 *결정 *능력''*

생성형 AI 시대에 *시니어 백엔드 개발자가 *유지 / 강화해야 할 *3 가지 *결정 능력*:

> 1. ***''*무엇을 *AI 에 *맡기고 *무엇을 *내가 *결정 하는가''*** — *Level 1 ↔ Level 3 의 *경계 *판단*
> 2. ***''*AI 의 답이 *옳은가 *틀린가''* 를 *3 초 안에 *판단** — *경험 기반 *직관*
> 3. ***''*비즈니스 + 기술 + 운영 + 미래 변화''* 의 *4 축 종합 *판단** — *AI 가 *영원히 *못 *하는 영역*

세 능력 *모두* 가 *''*Level 2 와 *Level 3 을 *직접 *공부 한 *사람만 *가질 수 있다*. *Level 1 만 *AI 와 *놀다 *시니어가 *된 사람은 *''*production 위기에서 *무력''*.

> **한 줄로**: *''*AI 가 *SQL 을 *빠르게 *써주는 시대* 에 *''*시니어의 *가치''* 는 *''*무엇을 *왜 *어떻게''* 에 *대한 *판단력*. *''*문법''* 을 *외울 시간을 *''*판단력*'' 에 *투자해라''*.

PL/SQL 은 *''*과거의 *언어''* 가 *되어 *간다. 하지만 *''*SQL 그 자체''* 는 *50 년이 *지난 *지금도 *백엔드의 *핵심 언어*. *''*Codd 의 *관계형 모델 (1970)''* 이 *2026 년에도 *유효한 *이유* 는 *''*수학적 정확성 + 비즈니스 표현력''* 의 *유일한 결합*. *AI 가 *바꾸지 못한다*.

***''*문법은 *AI 에 *맡기고, *판단력에 *시간을 *투자하라*''* — 이게 *2026 년 *시니어 백엔드의 *SQL 학습 전략의 *한 줄 답이다*.

---

## 더 읽으면 좋은 자료

- **Markus Winand, *Use The Index, Luke!*** — *index 의 *세계 최고 자료*
- **PostgreSQL 공식 문서** — *''*Performance''* / *''*Indexes''* 절
- **MySQL 8.0 Reference Manual** — *''*Optimization''* 장
- **Oracle Database Performance Tuning Guide** — *''*PL/SQL 코어 사용자''* 의 필독
- **Joe Celko, *SQL for Smarties*** — *고급 SQL 패턴*
- **Martin Kleppmann, *Designing Data-Intensive Applications*** — *''*DB 의 본질''*
- **Edgar Codd, *''A Relational Model of Data for Large Shared Data Banks'**** (1970) — *원전*
- **Postgres Weekly / Planet PostgreSQL** — *주간 *최신 동향*
- *Anthropic / OpenAI / GitHub Copilot* 의 *Code with AI* 가이드
