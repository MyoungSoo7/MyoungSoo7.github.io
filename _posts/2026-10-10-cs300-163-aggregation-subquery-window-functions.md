---
layout: post
title: "[CS300 #163] 집계·서브쿼리·윈도 함수 — 행을 묶고, 안고, 옆을 보는 법"
date: 2026-10-10 20:43:00 +0900
categories: [cs]
tags: [cs300, database, sql, window-function, aggregation]
---

컴퓨터공학 300 주제 시리즈의 163번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

집계는 여러 행을 하나로 접고, 서브쿼리는 질의 안에 질의를 넣어 값이나 집합을 만들며, 윈도 함수는 행을 접지 않은 채 이웃 행들을 보고 계산한다.

## 왜 필요한가

"매장별 매출 합계", "평균보다 많이 판 날", "매장 안에서 매출 순위", "일별 누적 매출". 리포트에 나오는 질문은 거의 이 네 가지 변형이다. 앞의 둘은 `GROUP BY` 와 서브쿼리로 풀린다. 뒤의 둘은 예전에는 셀프 조인이나 애플리케이션 코드로 풀었지만, 윈도 함수가 표준(SQL:2003)에 들어온 뒤로는 한 줄로 끝난다. PostgreSQL, MySQL 8, SQLite 모두 지원한다.

이 셋의 차이를 정확히 알면 "GROUP BY 를 쓰면 다른 열이 안 보인다"는 흔한 막힘이 풀린다.

## 핵심 개념

### 집계 함수와 GROUP BY

`COUNT`, `SUM`, `AVG`, `MIN`, `MAX` 는 행 집합을 값 하나로 줄인다. `GROUP BY` 가 없으면 전체가 한 묶음이고, 있으면 묶음마다 한 행이 나온다.

```
GROUP BY store

 store amount            store  SUM
 강남  100  ┐
 강남  150  ├─ 묶음 ─▶   강남   340
 강남   90  ┘
 판교  200  ┐
 판교  120  ├─ 묶음 ─▶   판교   320
 판교  NULL ┘
```

규칙 두 가지를 기억하자.

1. **`SELECT` 에는 묶음 기준 열과 집계 식만 쓸 수 있다.** 묶음 하나에 `day` 값이 셋인데 어느 것을 보여 줄지 정할 수 없기 때문이다. (SQLite, 옛 MySQL 은 이를 허용해 아무 값이나 고르는데, 이식성 없는 동작이다.)
2. **NULL 은 집계에서 무시된다.** `COUNT(*)` 는 행 수, `COUNT(amount)` 는 NULL 이 아닌 값의 수다. `AVG(amount)` 는 NULL 을 분모에서 뺀다. NULL 을 0 으로 볼지는 업무 규칙이고, 그렇다면 `COALESCE(amount, 0)` 으로 명시한다.

### WHERE 와 HAVING

`WHERE` 는 묶기 전에 행을 거르고, `HAVING` 은 묶은 뒤 묶음을 거른다. "합계가 300 이상인 매장"은 `HAVING SUM(amount) >= 300` 이다. 집계와 무관한 조건은 `WHERE` 에 두는 편이 묶을 행을 줄여 빠르다.

### 서브쿼리

질의 안에 괄호로 넣은 질의다. 들어가는 자리와 돌려주는 모양에 따라 나뉜다.

| 종류 | 돌려주는 것 | 예 |
|---|---|---|
| 스칼라 서브쿼리 | 값 하나 | `WHERE amount > (SELECT AVG(amount) FROM sales)` |
| 집합 서브쿼리 | 열 하나의 여러 값 | `WHERE store IN (SELECT ...)` |
| 존재 검사 | 참/거짓 | `WHERE EXISTS (SELECT 1 ...)` |
| 파생 테이블 | 표 | `FROM (SELECT ...) AS t` |

**상관 서브쿼리**는 바깥 행의 값을 참조한다. "자기 매장 평균보다 많이 판 날"은 다음과 같다.

```sql
SELECT day, store, amount FROM sales s
WHERE amount > (SELECT AVG(amount) FROM sales WHERE store = s.store);
```

개념상 바깥 행마다 안쪽을 다시 계산한다. 옵티마이저가 조인으로 바꿔 주는 경우가 많지만, 항상 그런 것은 아니다.

`NOT IN` 은 조심해야 한다. 서브쿼리 결과에 NULL 이 하나라도 있으면 `x NOT IN (...)` 은 참이 될 수 없어 결과가 통째로 빈다. 3값 논리 때문이다. 안티 조인은 `NOT EXISTS` 로 쓰는 것이 안전하다.

복잡한 서브쿼리는 `WITH` 절(공통 테이블 식, CTE)로 이름을 붙여 위에서 아래로 읽히게 쓸 수 있다. `WITH RECURSIVE` 를 쓰면 조직도 같은 트리도 순회할 수 있다.

### 윈도 함수

윈도 함수는 `함수() OVER (PARTITION BY ... ORDER BY ... 프레임)` 꼴이다. 집계와 달리 **행 수가 줄지 않는다.** 각 행 옆에 "자기가 속한 창(window)"으로 계산한 값을 붙일 뿐이다.

```
PARTITION BY store ORDER BY day

 store day  amount  SUM() OVER(...)   ← 누적합
 강남  01   100     100
 강남  02   150     250
 강남  03    90     340
 ─────────────────── 파티션 경계, 다시 0 부터
 판교  01   200     200
 ...
```

- `PARTITION BY`: 창을 나누는 기준. 없으면 전체가 한 창.
- `ORDER BY`: 창 안의 순서. 순위·누적 계산에 필요하다.
- 프레임: 창 안에서 실제로 계산에 쓰는 범위. `ORDER BY` 가 있으면 기본값은 `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, 즉 처음부터 현재 행(과 같은 값을 가진 동료 행)까지다. 그래서 `SUM() OVER (ORDER BY ...)` 가 누적합이 된다. 이동 평균은 `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` 처럼 명시한다.

자주 쓰는 함수:

| 함수 | 뜻 |
|---|---|
| `ROW_NUMBER()` | 1, 2, 3, 4 (동점도 다른 번호) |
| `RANK()` | 1, 2, 2, 4 (동점 뒤 번호 건너뜀) |
| `DENSE_RANK()` | 1, 2, 2, 3 |
| `LAG(x, n)` / `LEAD(x, n)` | n 행 앞/뒤의 값 (전일 대비 증감) |
| `FIRST_VALUE`, `LAST_VALUE` | 프레임의 처음/끝 값 |
| `NTILE(n)` | n 등분 버킷 번호 |

윈도 함수는 `SELECT`, `ORDER BY` 단계에서 평가되므로 `WHERE` 에 쓸 수 없다. "매장별 1등만"을 원하면 서브쿼리나 CTE 로 감싼 뒤 바깥에서 `WHERE rnk = 1` 로 거른다. 이것이 "그룹별 Top-N" 의 정석 패턴이다.

## 직접 해 보기

```python
import sqlite3
con = sqlite3.connect(":memory:")
con.executescript("""
CREATE TABLE sales (day TEXT, store TEXT, amount INTEGER);
INSERT INTO sales VALUES
 ('2026-10-01','강남',100),('2026-10-02','강남',150),('2026-10-03','강남',90),
 ('2026-10-01','판교',200),('2026-10-02','판교',120),('2026-10-03','판교',NULL);
""")
q = lambda s: [print(r) for r in con.execute(s)]
print("-- 집계: COUNT(*) 와 COUNT(열)의 차이")
q("""SELECT store, COUNT(*), COUNT(amount), SUM(amount), AVG(amount)
     FROM sales GROUP BY store ORDER BY store""")
print("-- 서브쿼리: 전체 평균보다 큰 날")
q("""SELECT day, store, amount FROM sales
     WHERE amount > (SELECT AVG(amount) FROM sales) ORDER BY amount DESC""")
print("-- 윈도 함수: 순위와 누적합")
q("""SELECT store, day, amount,
       RANK() OVER (PARTITION BY store ORDER BY amount DESC) AS rnk,
       SUM(amount) OVER (PARTITION BY store ORDER BY day) AS running
     FROM sales ORDER BY store, day""")
```

결과(SQLite 3.45):

```
-- 집계: COUNT(*) 와 COUNT(열)의 차이
('강남', 3, 3, 340, 113.33333333333333)
('판교', 3, 2, 320, 160.0)
-- 서브쿼리: 전체 평균보다 큰 날
('2026-10-01', '판교', 200)
('2026-10-02', '강남', 150)
-- 윈도 함수: 순위와 누적합
('강남', '2026-10-01', 100, 2, 100)
('강남', '2026-10-02', 150, 1, 250)
('강남', '2026-10-03', 90, 3, 340)
('판교', '2026-10-01', 200, 1, 200)
('판교', '2026-10-02', 120, 2, 320)
('판교', '2026-10-03', None, 3, 320)
```

읽을 거리가 세 개 있다. 판교의 평균은 `320/2 = 160` 이다. NULL 행이 분모에서 빠졌다. 전체 평균은 NULL 을 뺀 5개 값의 평균 132 이고, 그보다 큰 두 날이 나왔다. 마지막으로 판교 10월 3일의 누적합은 NULL 을 더하지 않아 320 그대로다. 순위에서 NULL 이 꼴찌가 된 것은 SQLite 가 NULL 을 가장 작은 값으로 정렬하기 때문이다. PostgreSQL 은 기본적으로 NULL 을 가장 큰 값처럼 다뤄 `DESC` 에서 맨 앞에 둔다. 이식성이 필요하면 `NULLS LAST` 를 명시한다.

## 현업에서는

- **대시보드 쿼리의 대부분은 윈도 함수**다. 전주 대비 증감(`LAG`), 코호트별 리텐션, 매장별 Top 3 상품이 모두 윈도 함수 한두 개로 끝난다.
- **중복 제거에 `ROW_NUMBER`**: 같은 키로 여러 번 적재된 이벤트에서 최신 한 건만 남길 때 `ROW_NUMBER() OVER (PARTITION BY key ORDER BY updated_at DESC) = 1` 패턴을 쓴다. 데이터 파이프라인에서 매일 보는 코드다.
- **NULL 처리 정책**: `AVG` 가 NULL 을 빼는 것을 몰라 "미입력"과 "0원"이 섞인 지표가 나오는 일이 있다. 지표 정의서에 NULL 의미를 적어 두는 팀이 많다.
- **`NOT IN` + NULL** 은 데이터가 늘다가 NULL 한 건이 들어오는 순간 결과가 0건이 되는, 늦게 터지는 버그다.

## 확인 문제

1. 판교의 `COUNT(*)` 와 `COUNT(amount)` 가 다른 이유는?
2. 매장별 매출 합계가 300 이상인 매장만 보이려면 조건을 `WHERE` 와 `HAVING` 중 어디에 써야 하는가?
3. `x NOT IN (1, NULL)` 의 결과는 x 값과 상관없이 무엇이 되는가?
4. `RANK`, `DENSE_RANK`, `ROW_NUMBER` 가 점수 `90, 80, 80, 70` 에 매기는 번호를 각각 적어라.
5. "매장별 매출 1위 날짜"를 구하려면 왜 윈도 함수 결과를 한 번 감싸야 하는가?

### 풀이

1. `COUNT(*)` 는 행 수(3), `COUNT(amount)` 는 NULL 이 아닌 값의 수(2)를 센다.
2. `HAVING`. 합계는 묶은 뒤에만 존재한다.
3. `x = 1` 이면 거짓, 아니면 `x <> NULL` 이 UNKNOWN 이라 전체가 UNKNOWN 이다. 어느 쪽도 참이 아니므로 행이 통과하지 못한다.
4. RANK: 1,2,2,4. DENSE_RANK: 1,2,2,3. ROW_NUMBER: 1,2,3,4(동점 순서는 비결정적).
5. 윈도 함수는 `WHERE` 보다 늦게 평가되므로 같은 단계에서 거를 수 없다. CTE·서브쿼리로 감싸 바깥 `WHERE rnk = 1` 로 거른다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Window Functions](https://www.postgresql.org/docs/current/tutorial-window.html)
- PostgreSQL 공식 문서, [Aggregate Functions](https://www.postgresql.org/docs/current/functions-aggregate.html), [Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html)
- SQLite 공식 문서, [Window Functions](https://www.sqlite.org/windowfunctions.html)
- PostgreSQL 공식 문서, [WITH Queries (Common Table Expressions)](https://www.postgresql.org/docs/current/queries-with.html)
