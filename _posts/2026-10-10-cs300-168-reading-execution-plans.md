---
layout: post
title: "[CS300 #168] 실행 계획 읽기 — DB 가 무엇을 하려는지 묻는 법"
date: 2026-10-10 20:48:00 +0900
categories: [cs]
tags: [cs300, database, explain, query-optimizer, performance]
---

컴퓨터공학 300 주제 시리즈의 168번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

실행 계획은 옵티마이저가 SQL 을 어떤 접근 방법·조인 순서·조인 알고리즘으로 실행할지 정한 트리이고, `EXPLAIN` 은 그 트리를 보여 주며 `EXPLAIN ANALYZE` 는 실제로 실행해 예측과 현실을 나란히 보여 준다.

## 왜 필요한가

SQL 은 선언형이다. "무엇을" 원하는지만 쓰고 "어떻게" 할지는 DB 가 정한다. 같은 SQL 이라도 데이터 분포와 인덱스에 따라 0.1ms 에 끝나기도 하고 10분이 걸리기도 한다. 느린 쿼리를 고치려면 DB 가 고른 "어떻게"를 봐야 한다. 실행 계획을 읽지 못하면 인덱스를 추측으로 추가하고, 효과가 없으면 또 추측하게 된다.

실행 계획 읽기는 백엔드 개발자가 장애 대응에서 가장 자주 쓰는 기술 중 하나다.

## 핵심 개념

### 옵티마이저가 하는 일

1. SQL 을 파싱해 관계 대수 트리로 바꾼다.
2. 같은 결과를 내는 여러 후보 계획을 만든다. 테이블마다 접근 방법(풀 스캔, 인덱스 스캔), 조인 순서, 조인 알고리즘을 바꿔 본다.
3. 각 후보의 **비용**을 추정해 가장 싼 것을 고른다.

비용 추정의 핵심 입력은 **통계**다. 테이블 행 수, 열 값의 분포(히스토그램), 고유값 수, NULL 비율 같은 것이다. PostgreSQL 은 `ANALYZE` (자동 vacuum 이 주기적으로 실행)로, SQLite 는 `ANALYZE` 명령으로 통계를 모은다. **통계가 낡으면 행 수 추정이 틀리고, 행 수 추정이 틀리면 계획이 틀린다.** 나쁜 계획의 원인은 대개 이것이다.

### 트리를 읽는 순서

계획은 트리다. 들여쓰기가 깊은 노드가 먼저 실행되어 결과를 부모에게 올린다. PostgreSQL 공식 문서의 예를 보자.

```
EXPLAIN SELECT *
FROM tenk1 t1, tenk2 t2
WHERE t1.unique1 < 10 AND t1.unique2 = t2.unique2;

 Nested Loop  (cost=4.65..118.50 rows=10 width=488)
   ->  Bitmap Heap Scan on tenk1 t1  (cost=4.36..39.38 rows=10 width=244)
         Recheck Cond: (unique1 < 10)
         ->  Bitmap Index Scan on tenk1_unique1  (cost=0.00..4.36 rows=10 width=0)
               Index Cond: (unique1 < 10)
   ->  Index Scan using tenk2_unique2 on tenk2 t2  (cost=0.29..7.90 rows=1 width=244)
         Index Cond: (unique2 = t1.unique2)
```

읽는 법:

1. 가장 안쪽 `Bitmap Index Scan` 이 인덱스로 `unique1 < 10` 인 행 위치를 모은다.
2. `Bitmap Heap Scan` 이 그 위치의 행을 테이블에서 가져온다(약 10행 예상).
3. `Nested Loop` 가 그 10행 각각에 대해 `tenk2` 의 인덱스를 한 번씩 탐색한다.

괄호 안의 숫자:

| 항목 | 뜻 |
|---|---|
| `cost=4.65..118.50` | 첫 행을 내기까지의 비용 .. 모든 행을 내기까지의 비용 (임의 단위) |
| `rows=10` | 이 노드가 낼 것으로 **추정**한 행 수 |
| `width=488` | 행 하나의 평균 바이트 수 추정 |

비용 단위는 시간이 아니다. 기본 설정에서 순차 페이지 읽기 하나를 1.0 으로 놓은 상대값이다. 서로 다른 계획을 비교하는 용도로만 쓴다.

### EXPLAIN ANALYZE: 예측 대 현실

`EXPLAIN ANALYZE` 는 쿼리를 **실제로 실행**하고 노드마다 실측값을 붙인다. 같은 문서의 결과에서 일부 줄을 추리면 다음과 같다.

```
 Nested Loop  (cost=4.65..118.50 rows=10 width=488) (actual time=0.017..0.051 rows=10.00 loops=1)
   ->  Bitmap Heap Scan on tenk1 t1  (...) (actual time=0.009..0.017 rows=10.00 loops=1)
   ->  Index Scan using tenk2_unique2 on tenk2 t2  (cost=0.29..7.90 rows=1 width=244) (actual time=0.003..0.003 rows=1.00 loops=10)
 Planning Time: 0.485 ms
 Execution Time: 0.073 ms
```

봐야 할 것은 세 가지다.

- **추정 rows 와 실제 rows 의 차이.** 몇 배 이상 차이 나는 노드가 있으면 그 아래 통계나 조건 해석이 틀린 것이다. 대부분의 나쁜 계획은 여기서 시작한다.
- **loops.** 실제 시간과 행 수는 한 번 실행 기준이다. `loops=10` 이면 그 노드는 10번 돌았다. 총비용은 곱해서 본다.
- **시간이 가장 많이 늘어나는 노드.** 자식의 시간은 부모에 포함되어 있으므로, 부모 시간에서 자식 시간을 뺀 값이 큰 곳이 병목이다.

주의: `ANALYZE` 는 정말 실행한다. `UPDATE`, `DELETE` 를 분석할 때는 `BEGIN; EXPLAIN ANALYZE ...; ROLLBACK;` 으로 감싼다.

### 자주 보는 노드

| 노드 | 뜻 | 좋을 때 / 나쁠 때 |
|---|---|---|
| Seq Scan | 테이블 전체 읽기 | 작은 테이블, 대부분 행이 필요할 때는 최선 |
| Index Scan | 인덱스로 찾고 테이블 방문 | 적은 행을 고를 때 |
| Index Only Scan | 인덱스만 읽기 | 커버링 인덱스 |
| Bitmap Heap Scan | 인덱스로 위치를 모은 뒤 페이지 순서로 방문 | 중간 정도 선택도 |
| Nested Loop | 바깥 행마다 안쪽 탐색 | 바깥이 작고 안쪽에 인덱스 |
| Hash Join | 작은 쪽으로 해시 테이블, 큰 쪽으로 탐색 | 등호 조인, 큰 데이터 |
| Merge Join | 양쪽을 정렬해 나란히 걷기 | 이미 정렬된 입력 |
| Sort | 정렬 | 메모리 부족 시 디스크로 넘침 |

Seq Scan 이 늘 나쁜 것은 아니다. 테이블의 30% 를 읽어야 한다면 인덱스로 하나씩 찾는 것보다 순서대로 다 읽는 쪽이 싸다.

## 직접 해 보기

SQLite 의 `EXPLAIN QUERY PLAN` 은 PostgreSQL 보다 간단하지만 같은 생각을 보여 준다.

```python
import sqlite3, random
con = sqlite3.connect(":memory:")
con.executescript("""
CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT, grade TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER,
                     created TEXT, amount INTEGER);
""")
random.seed(1)
con.executemany("INSERT INTO customer VALUES (?,?,?)",
    ((i, f"c{i}", random.choice("ABC")) for i in range(5000)))
con.executemany("INSERT INTO orders VALUES (?,?,?,?)",
    ((i, random.randrange(5000), f"2026-{random.randint(1,12):02d}-01",
      random.randint(1, 100) * 1000) for i in range(50000)))

sql = """SELECT c.name, SUM(o.amount) FROM orders o
         JOIN customer c ON c.id = o.customer_id
         WHERE o.created >= '2026-10-01' AND c.grade = 'A'
         GROUP BY c.name ORDER BY 2 DESC LIMIT 5"""
def show_plan(title):
    print("--", title)
    for id_, parent, _, detail in con.execute("EXPLAIN QUERY PLAN " + sql):
        print(f"  [{id_:>2} <- {parent:>2}] {detail}")
show_plan("인덱스 없음")
con.execute("CREATE INDEX idx_orders_created ON orders(created)")
con.execute("ANALYZE")
show_plan("orders(created) 인덱스 + ANALYZE")
```

SQLite 3.45 에서의 결과:

```
-- 인덱스 없음
  [ 9 <-  0] SCAN o
  [13 <-  0] SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
  [18 <-  0] USE TEMP B-TREE FOR GROUP BY
  [60 <-  0] USE TEMP B-TREE FOR ORDER BY
-- orders(created) 인덱스 + ANALYZE
  [10 <-  0] SEARCH o USING INDEX idx_orders_created (created>?)
  [15 <-  0] BLOOM FILTER ON c (id=?)
  [23 <-  0] SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
  [30 <-  0] USE TEMP B-TREE FOR GROUP BY
  [72 <-  0] USE TEMP B-TREE FOR ORDER BY
```

해석:

- 첫 계획은 `orders` 5만 행을 모두 훑고(`SCAN o`), 각 행마다 고객을 기본 키로 찾는다. 사실상 중첩 루프 조인이다.
- 인덱스를 만들고 통계를 모으자 `created` 범위로 주문을 좁혀 시작한다(`SEARCH ... (created>?)`). 10~12월이라 전체의 약 4분의 1 이다.
- `BLOOM FILTER` 는 SQLite 가 조인 안쪽 탐색을 줄이려고 넣은 확률적 필터다. 통계가 생긴 뒤에 나타났다는 점이 흥미롭다. 통계가 계획을 바꾼다.
- `USE TEMP B-TREE` 는 정렬·그룹핑을 위해 임시 트리를 만든다는 뜻이다. PostgreSQL 의 Sort, HashAggregate 노드에 해당한다.

## 현업에서는

- **느린 쿼리 대응 순서**: 슬로 쿼리 로그에서 쿼리를 잡는다 → `EXPLAIN (ANALYZE, BUFFERS)` 를 운영과 비슷한 데이터에서 실행한다 → 추정과 실제 rows 가 크게 어긋나는 노드를 찾는다 → 통계 갱신, 인덱스, 쿼리 재작성 중 하나를 고른다.
- **개발 DB 에서 빠른데 운영에서 느린 쿼리**는 대개 데이터 양과 분포 차이 때문이다. 행 100개짜리 테이블에서는 어떤 계획이든 빠르다. 계획은 반드시 운영 규모 데이터로 본다.
- **파라미터에 따라 계획이 바뀌는 문제**: 같은 쿼리라도 `status = 'DONE'`(전체의 95%) 과 `status = 'FAILED'`(0.1%)는 최적 계획이 다르다. 준비된 문장(prepared statement)이 일반 계획으로 굳으면 한쪽이 느려진다.
- **`auto_explain`** 같은 확장으로 일정 시간 넘는 쿼리의 계획을 자동으로 로그에 남기면, 새벽에 한 번 느렸던 쿼리의 계획도 나중에 볼 수 있다.

## 확인 문제

1. `cost=0.29..7.90` 에서 두 숫자는 각각 무엇을 뜻하는가? 단위는 밀리초인가?
2. `rows=10` 이라고 추정한 노드가 실제로 `rows=50000` 을 냈다. 가장 먼저 의심할 것은?
3. `loops=1000`, `actual time=0.010..0.020` 인 노드의 총 소요 시간은 대략 얼마인가?
4. Seq Scan 이 Index Scan 보다 나은 경우를 설명하라.
5. `EXPLAIN ANALYZE DELETE ...` 를 운영 DB 에서 실행하면 무슨 일이 생기는가?

### 풀이

1. 첫 행까지의 비용과 전체 행까지의 비용. 단위는 시간이 아니라 순차 페이지 읽기를 1 로 둔 상대 비용이다.
2. 통계가 낡았거나, 조건 사이 상관관계(열이 독립이라는 가정의 붕괴)로 선택도 추정이 틀렸을 가능성.
3. 한 번에 약 0.02ms × 1000 = 약 20ms.
4. 많은 비율의 행을 읽어야 할 때. 인덱스로 하나씩 찾아가는 랜덤 접근보다 순차 읽기가 싸다.
5. 실제로 삭제된다. 트랜잭션으로 감싸 `ROLLBACK` 해야 한다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) — 이 글의 PostgreSQL 예시 출처
- PostgreSQL 공식 문서, [EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html), [Statistics Used by the Planner](https://www.postgresql.org/docs/current/planner-stats.html)
- SQLite 공식 문서, [EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html)
- P. Griffiths Selinger 외, "Access Path Selection in a Relational Database Management System", *Proceedings of ACM SIGMOD*, 1979.
