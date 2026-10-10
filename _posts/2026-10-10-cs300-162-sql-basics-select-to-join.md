---
layout: post
title: "[CS300 #162] SQL 기초 — SELECT 부터 JOIN 까지"
date: 2026-10-10 20:42:00 +0900
categories: [cs]
tags: [cs300, database, sql, join, select]
---

컴퓨터공학 300 주제 시리즈의 162번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

SQL 의 `SELECT` 는 "어떤 행을 어떤 모양으로 원하는지"만 적는 선언형 문장이고, `JOIN` 은 두 테이블의 행을 조건에 맞게 짝지어 하나의 결과 표로 만드는 연산이다.

## 왜 필요한가

SQL 은 개발자가 평생 가장 많이 쓰는 언어 가운데 하나다. 백엔드, 데이터 분석, 운영 장애 대응까지 결국 "이 조건의 행을 보여 줘"로 끝난다. 그런데 SQL 은 위에서 아래로 읽히는 순서와 실제로 평가되는 순서가 다르다. 이 차이를 모르면 `WHERE` 에서 별칭이 안 보이는 이유, `LEFT JOIN` 이 갑자기 `INNER JOIN` 처럼 동작하는 이유를 설명하지 못한다.

이 글은 단일 테이블 질의에서 시작해 조인의 종류와 함정까지 정리한다.

## 핵심 개념

### SELECT 문의 뼈대

```sql
SELECT   열, 식, 별칭            -- 5. 무엇을 보여 줄지
FROM     테이블 [JOIN ...]       -- 1. 어디서
WHERE    행 조건                 -- 2. 어떤 행을
GROUP BY 묶을 열                 -- 3. 묶어서
HAVING   묶음 조건               -- 4. 어떤 묶음을
ORDER BY 정렬 기준               -- 6. 어떤 순서로
LIMIT    개수                    -- 7. 몇 개만
```

번호는 논리적 평가 순서다. 실제 실행기는 더 효율적인 순서로 일을 하지만, 결과는 이 순서로 평가한 것과 같아야 한다. 이 순서에서 몇 가지 규칙이 바로 나온다.

- `WHERE` 는 `SELECT` 보다 먼저 평가되므로 `SELECT` 에서 붙인 별칭을 표준 SQL 의 `WHERE` 에서 쓸 수 없다.
- `ORDER BY` 는 마지막이라 별칭을 쓸 수 있다.
- 집계 결과에 대한 조건은 `WHERE` 가 아니라 `HAVING` 에 쓴다(다음 글에서 다룬다).

### 행 거르기: WHERE

```sql
SELECT name, city FROM customer
WHERE city = '서울' AND name LIKE '민%';
```

자주 쓰는 연산자는 비교(`=`, `<>`, `<`, `>=`), 범위(`BETWEEN a AND b`, 양 끝 포함), 목록(`IN (...)`), 패턴(`LIKE`, `%` 는 임의 길이, `_` 는 한 글자), NULL 검사(`IS NULL`)다. `= NULL` 은 항상 UNKNOWN 이라 쓰면 안 된다.

### 정렬과 페이징

`ORDER BY` 가 없으면 결과 순서는 보장되지 않는다. 페이징을 `LIMIT 20 OFFSET 40` 으로 하면 DB 는 앞의 40행을 만들어 버린 뒤 20행을 준다. 페이지가 깊어질수록 느려지는 이유다. 마지막으로 본 키 다음부터 가져오는 키셋 페이징(`WHERE id > :last ORDER BY id LIMIT 20`)이 대안이다.

### JOIN 의 종류

두 테이블 `customer(id, name)` 와 `orders(id, customer_id, amount)` 가 있다고 하자.

```
customer            orders
 id name             id  customer_id amount
 1  민수             100 1           30000
 2  지은             101 1           12000
 3  현우             102 2            8000
                     103 9            5000   <- 없는 고객
```

| 조인 | 결과에 남는 것 |
|---|---|
| `INNER JOIN` | 양쪽 모두 짝이 있는 행만 |
| `LEFT [OUTER] JOIN` | 왼쪽 전부 + 짝 없으면 오른쪽 열은 NULL |
| `RIGHT [OUTER] JOIN` | 오른쪽 전부 (왼쪽·오른쪽을 바꾼 LEFT) |
| `FULL [OUTER] JOIN` | 양쪽 전부 |
| `CROSS JOIN` | 모든 조합 (행 수 = 곱) |

여기서는 현우가 주문이 없고, 주문 103 은 고객이 없다. `INNER JOIN` 은 둘 다 버리고, `LEFT JOIN` 은 현우를 NULL 주문과 함께 남기고, `FULL JOIN` 은 둘 다 남긴다.

조인은 개념적으로 카티션 곱을 만든 뒤 `ON` 조건으로 거르는 것과 같다. 실제 DB 는 곱을 만들지 않고 중첩 루프, 해시 조인, 병합 조인 중 싼 방법을 고른다. 이 선택은 "실행 계획 읽기" 주제에서 다시 본다.

### ON 과 WHERE 는 외부 조인에서 다르다

`INNER JOIN` 에서는 조건을 `ON` 에 두든 `WHERE` 에 두든 결과가 같다. 외부 조인에서는 다르다.

- `ON` 조건: 짝을 찾을 때 쓰인다. 짝이 없으면 왼쪽 행은 NULL 과 함께 그대로 남는다.
- `WHERE` 조건: 조인이 끝난 결과를 거른다. 오른쪽 열에 조건을 걸면 NULL 행이 탈락해 사실상 `INNER JOIN` 이 된다.

`LEFT JOIN orders o ... WHERE o.amount > 10000` 이라고 쓰면 주문 없는 고객이 사라진다. "모든 고객과, 있으면 큰 주문"을 원했다면 그 조건을 `ON` 으로 옮겨야 한다.

### 안티 조인과 세미 조인

- **안티 조인**: 짝이 없는 행만. `LEFT JOIN ... WHERE 오른쪽.키 IS NULL` 또는 `NOT EXISTS`.
- **세미 조인**: 짝이 있는지만 확인하고 왼쪽 행을 한 번씩만. `EXISTS` 또는 `IN`.

세미 조인을 `JOIN` 으로 쓰면 짝이 여러 개인 왼쪽 행이 중복된다. 민수는 주문이 둘이라 `JOIN` 결과에 두 번 나온다. "주문한 적 있는 고객 목록"이 필요하면 `EXISTS` 가 맞다.

### 셀프 조인

같은 테이블을 두 번 별칭으로 불러 조인한다. 직원과 그 상사를 한 행에 보여 줄 때 `emp e LEFT JOIN emp m ON e.manager_id = m.id` 처럼 쓴다.

## 직접 해 보기

```python
import sqlite3
con = sqlite3.connect(":memory:")
con.executescript("""
CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount INTEGER);
INSERT INTO customer VALUES (1,'민수','서울'),(2,'지은','부산'),(3,'현우','서울');
INSERT INTO orders VALUES (100,1,30000),(101,1,12000),(102,2,8000),(103,9,5000);
""")
def show(title, sql):
    print("--", title)
    for row in con.execute(sql):
        print(row)
show("INNER JOIN", """SELECT c.name, o.amount FROM customer c
  JOIN orders o ON o.customer_id = c.id ORDER BY o.id""")
show("LEFT JOIN", """SELECT c.name, o.amount FROM customer c
  LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id""")
show("주문 없는 고객", """SELECT c.name FROM customer c
  LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL""")
show("ON 과 WHERE 차이", """SELECT c.name, o.amount FROM customer c
  LEFT JOIN orders o ON o.customer_id = c.id AND o.amount > 10000
  ORDER BY c.id, o.id""")
```

실행 결과:

```
-- INNER JOIN
('민수', 30000)
('민수', 12000)
('지은', 8000)
-- LEFT JOIN
('민수', 30000)
('민수', 12000)
('지은', 8000)
('현우', None)
-- 주문 없는 고객
('현우',)
-- ON 과 WHERE 차이
('민수', 30000)
('민수', 12000)
('지은', None)
('현우', None)
```

마지막 결과를 보자. 조건을 `ON` 에 두었기 때문에 8000원 주문만 있는 지은도 NULL 과 함께 남았다. 같은 조건을 `WHERE o.amount > 10000` 으로 옮기면 지은과 현우가 모두 사라지고 민수의 두 행만 남는다. 직접 바꿔 실행해 보면 차이가 바로 보인다. 주문 103 은 어떤 고객과도 짝이 없어서 `INNER` 와 `LEFT` 결과 모두에서 빠졌다.

## 현업에서는

- **`SELECT *` 지양**: 운영 코드에서 `*` 를 쓰면 열이 추가될 때 네트워크 전송량과 ORM 매핑이 같이 흔들린다. 커버링 인덱스(인덱스만 읽고 끝나는 질의)도 쓸 수 없게 된다.
- **조인 결과 행 수 검증**: 일대다 관계를 조인하고 `SUM` 을 하면 "일" 쪽 값이 "다"의 수만큼 중복 합산된다. 매출 리포트가 두 배로 나오는 사고의 상당수가 이 패턴이다. 조인 후 행 수를 먼저 세 보는 습관이 사고를 막는다.
- **외부 조인 + WHERE 함정**은 코드 리뷰에서 가장 자주 지적되는 SQL 버그 중 하나다.
- **깊은 OFFSET**: 관리자 페이지의 "마지막 페이지" 버튼이 DB 를 느리게 만드는 일이 흔하다. 키셋 페이징으로 바꾸면 깊이와 상관없이 비슷한 비용이 든다.

## 확인 문제

1. `SELECT price * qty AS total FROM t WHERE total > 100` 이 표준 SQL 에서 오류가 나는 이유를 논리적 평가 순서로 설명하라.
2. 위 예제에서 `customer FULL JOIN orders` 의 결과 행 수는 몇 개인가?
3. "주문이 한 건이라도 있는 고객 이름"을 중복 없이 구하는 쿼리를 `EXISTS` 로 써라.
4. `LIMIT 20 OFFSET 100000` 이 느린 이유와 대안은?

### 풀이

1. `WHERE` 는 `SELECT` 보다 먼저 평가되므로 그 시점에는 `total` 별칭이 없다. `WHERE price * qty > 100` 으로 쓰거나 서브쿼리로 감싼다.
2. 짝이 맞는 3행(민수 2, 지은 1) + 왼쪽만 있는 현우 1행 + 오른쪽만 있는 주문 103 1행 = 5행.
3. `SELECT name FROM customer c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);`
4. 앞의 10만 행을 만들고 버려야 하기 때문이다. 마지막으로 본 키 이후를 가져오는 키셋 페이징을 쓴다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Joins Between Tables](https://www.postgresql.org/docs/current/tutorial-join.html)
- PostgreSQL 공식 문서, [Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html)
- SQLite 공식 문서, [SELECT](https://www.sqlite.org/lang_select.html)
- Python 공식 문서, [sqlite3 — DB-API 2.0 interface for SQLite databases](https://docs.python.org/3/library/sqlite3.html)
