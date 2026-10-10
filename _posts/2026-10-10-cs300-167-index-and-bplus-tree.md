---
layout: post
title: "[CS300 #167] 인덱스와 B+트리 — 1억 행에서 네 번 만에 찾기"
date: 2026-10-10 20:47:00 +0900
categories: [cs]
tags: [cs300, database, index, b-plus-tree, query-performance]
---

컴퓨터공학 300 주제 시리즈의 167번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

인덱스는 열 값을 정렬된 상태로 따로 보관하는 보조 구조이고, 대부분의 관계형 DB 는 이를 디스크 페이지 단위로 넓게 가지를 치는 B+트리로 구현해 몇 번의 페이지 읽기만으로 원하는 행을 찾는다.

## 왜 필요한가

인덱스가 없으면 DB 가 할 수 있는 일은 테이블 전체를 처음부터 끝까지 읽는 것(풀 스캔)뿐이다. 행이 20만 개면 20만 개를, 1억 개면 1억 개를 본다. 비용이 데이터 양에 정비례한다.

책 뒤의 찾아보기를 떠올리면 된다. 단어가 가나다순으로 정렬되어 있고 옆에 쪽 번호가 있다. 정렬되어 있으니 이진 탐색처럼 빠르게 찾고, 쪽 번호로 본문에 바로 간다. DB 인덱스도 똑같다. 다만 데이터가 디스크에 있다는 조건 때문에, 이진 탐색 트리가 아니라 B+트리를 쓴다. 그 이유를 이해하면 "어떤 인덱스를 만들어야 하는가"에 대한 답이 대부분 따라 나온다.

## 핵심 개념

### 왜 이진 트리가 아니라 B+트리인가

디스크(SSD 포함)는 바이트 단위가 아니라 **페이지**(PostgreSQL 기본 8KB, SQLite 기본 4KB) 단위로 읽는다. 한 번 읽을 때 페이지 하나가 통째로 온다. 이진 트리는 노드마다 키 하나와 자식 둘이라, 1억 개 키면 높이가 약 27이다. 노드 하나가 페이지 하나라면 찾기 한 번에 페이지 27개를 읽는다.

B트리 계열은 노드 하나를 페이지 하나에 맞추고 그 안에 키를 수백 개 넣는다. 자식 수(팬아웃)가 수백이 되니 높이가 급격히 낮아진다.

```
높이 ≈ ⌈ log_f N ⌉

N = 1억, f = 100  →  높이 4
N = 1억, f = 500  →  높이 3
```

게다가 위쪽 몇 단계는 자주 쓰이니 거의 항상 메모리 버퍼에 있다. 실제로 디스크까지 가는 것은 마지막 한두 페이지인 경우가 많다.

### B+트리의 구조

Bayer 와 McCreight 가 1972년에 발표한 B트리를 변형한 것이다. B+트리의 특징은 두 가지다.

1. **모든 실제 값(또는 행 위치)은 리프에만 있다.** 내부 노드는 길 안내용 키만 가진다. 그래서 내부 노드에 키를 더 많이 넣을 수 있고 팬아웃이 커진다.
2. **리프끼리 연결 리스트로 이어져 있다.** 범위 검색(`BETWEEN`, `>`, `ORDER BY`)은 시작 리프를 한 번 찾은 뒤 옆으로 걸어가면 된다.

```
                     [ 30 | 60 ]                    루트 (내부)
            ┌────────────┼─────────────┐
       [ 10 | 20 ]   [ 40 | 50 ]   [ 70 | 80 ]       내부
       ┌──┼──┐        ┌──┼──┐       ┌──┼──┐
      [..][..][..] ⇄ [..][..][..] ⇄ [..][..][..]     리프 (키 → 행 위치)
                 ← 리프는 양옆으로 연결 →
```

삽입으로 노드가 꽉 차면 둘로 **분할**하고 가운데 키를 부모로 올린다. 루트가 분할되면 높이가 1 늘어난다. 트리는 항상 모든 리프가 같은 깊이에 있는 균형 상태를 유지한다. 삭제로 노드가 너무 비면 이웃과 합치거나 빌려 온다.

### 클러스터드 인덱스와 보조 인덱스

| 구분 | 리프에 있는 것 | 예 |
|---|---|---|
| 클러스터드(테이블 자체가 트리) | 행 전체 | MySQL InnoDB 기본 키, SQLite rowid 테이블 |
| 보조 인덱스 | 키 + 행을 찾을 포인터 | 그 밖의 인덱스 |

InnoDB 에서 보조 인덱스의 포인터는 기본 키 값이다. 보조 인덱스로 찾은 뒤 기본 키 트리를 한 번 더 내려간다. PostgreSQL 은 테이블이 힙(순서 없는 파일)이고 모든 인덱스가 행의 물리 위치(TID)를 가리킨다.

### 커버링 인덱스

질의에 필요한 열이 모두 인덱스 안에 있으면 테이블을 볼 필요가 없다. 이를 **커버링 인덱스**라 한다. 테이블 방문(랜덤 I/O)이 사라지므로 큰 차이가 난다. PostgreSQL 은 `CREATE INDEX ... INCLUDE (열)` 로 검색 키가 아닌 열을 리프에 실어 커버링을 만들 수 있다.

### 복합 인덱스와 왼쪽 접두사 규칙

`(city, age)` 인덱스는 city 로 먼저 정렬하고, 같은 city 안에서 age 로 정렬한 것이다. 전화번호부가 성으로 정렬되고 같은 성 안에서 이름으로 정렬된 것과 같다.

- `city = ?` → 사용 가능
- `city = ? AND age = ?` → 사용 가능
- `city = ? AND age > ?` → 사용 가능 (city 로 좁힌 뒤 age 범위)
- `age = ?` 만 → 트리 탐색 불가. 이름만 알고 전화번호부를 찾는 격이다.

그래서 복합 인덱스의 열 순서는 "등호로 자주 쓰이는 열을 앞에, 범위 조건 열을 뒤에"가 기본 원칙이다.

### 인덱스의 비용

인덱스는 공짜가 아니다.

- 행을 쓸 때마다 모든 인덱스를 함께 갱신한다. 인덱스가 다섯 개면 삽입 하나가 트리 여섯 개를 건드린다.
- 디스크와 버퍼 메모리를 차지한다.
- 선택도가 낮은 열(예: 성별)에 대한 인덱스는 결국 테이블 대부분을 읽게 되어, 옵티마이저가 풀 스캔을 고르는 일이 많다.

B+트리 외의 인덱스도 있다. PostgreSQL 은 해시, GiST, SP-GiST, GIN, BRIN 을 제공한다. 등호 전용, 공간 데이터, 전문 검색·배열, 시간순으로 쌓이는 거대 테이블처럼 용도가 다르다.

## 직접 해 보기

SQLite 에서 20만 행 테이블을 만들고 실행 계획과 시간을 비교한다.

```python
import sqlite3, random, time, math
con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, city TEXT, age INTEGER, email TEXT)")
random.seed(7)
cities = ["서울", "부산", "대구", "광주", "대전"]
con.executemany("INSERT INTO users VALUES (?,?,?,?)",
    ((i, random.choice(cities), random.randint(18, 80), f"u{i}@example.com")
     for i in range(200_000)))

def plan(sql):
    return " / ".join(r[3] for r in con.execute("EXPLAIN QUERY PLAN " + sql))

def timed(sql, n=50):
    t = time.perf_counter()
    for _ in range(n):
        con.execute(sql).fetchall()
    return (time.perf_counter() - t) / n * 1000

q = "SELECT id FROM users WHERE email = 'u123456@example.com'"
print("인덱스 전:", plan(q), f"{timed(q):.2f} ms")
con.execute("CREATE INDEX idx_email ON users(email)")
print("인덱스 후:", plan(q), f"{timed(q):.3f} ms")

con.execute("CREATE INDEX idx_city_age ON users(city, age)")
for sql in ["SELECT * FROM users WHERE city = '부산' AND age = 30",
            "SELECT * FROM users WHERE age = 30",
            "SELECT id FROM users WHERE city = '부산' AND age > 70"]:
    print(sql[7:], "=>", plan(sql))

# 팬아웃 f 인 B+트리의 높이 ~ ceil(log_f N)
for f in (100, 500):
    print(f"팬아웃 {f}: 1억 키의 높이 ≈ {math.ceil(math.log(1e8, f))}")
```

한 번 실행한 결과(시간은 기기마다 다르다):

```
인덱스 전: SCAN users 32.79 ms
인덱스 후: SEARCH users USING COVERING INDEX idx_email (email=?) 0.003 ms
* FROM users WHERE city = '부산' AND age = 30 => SEARCH users USING INDEX idx_city_age (city=? AND age=?)
* FROM users WHERE age = 30 => SCAN users
id FROM users WHERE city = '부산' AND age > 70 => SEARCH users USING COVERING INDEX idx_city_age (city=? AND age>?)
팬아웃 100: 1억 키의 높이 ≈ 4
팬아웃 500: 1억 키의 높이 ≈ 3
```

관찰할 점:

- `SCAN` 은 풀 스캔, `SEARCH` 는 트리 탐색이다. 수십 밀리초가 밀리초 이하로 줄었다. 정확한 배율은 환경마다 다르지만 자릿수가 바뀐다는 점은 같다.
- 이메일 검색이 `COVERING INDEX` 로 나온 것은 SQLite 인덱스 리프에 rowid(여기선 `id`)가 함께 들어 있어, `SELECT id` 에 테이블 방문이 필요 없기 때문이다.
- `age = 30` 만으로는 `(city, age)` 인덱스를 탐색하지 못해 `SCAN` 이 되었다. 왼쪽 접두사 규칙 그대로다.
- `SELECT *` 는 인덱스로 찾은 뒤 테이블에 가서 나머지 열을 가져온다(`USING INDEX`). `SELECT id` 는 인덱스만으로 끝난다(`COVERING`).

## 현업에서는

- **느린 쿼리의 첫 번째 용의자는 빠진 인덱스, 두 번째는 쓰이지 못하는 인덱스**다. `WHERE LOWER(email) = ?` 처럼 열에 함수를 씌우거나, 문자열 열을 숫자와 비교해 형변환이 일어나면 인덱스가 있어도 못 쓴다. 이럴 땐 식 인덱스(`CREATE INDEX ... ON users (lower(email))`)를 만든다.
- **`LIKE '%키워드%'`** 는 앞이 고정되지 않아 B+트리를 쓸 수 없다. 전문 검색 인덱스나 검색 엔진의 영역이다.
- **인덱스 추가는 운영 중 작업**이다. 큰 테이블에 그냥 `CREATE INDEX` 를 하면 쓰기가 막힐 수 있다. PostgreSQL 은 `CREATE INDEX CONCURRENTLY` 로 쓰기를 막지 않고 만들 수 있지만 더 오래 걸리고, 실패하면 무효 인덱스가 남아 정리해야 한다.
- **쓰지 않는 인덱스 정리**: 인덱스 사용 통계(PostgreSQL `pg_stat_user_indexes` 의 `idx_scan`)를 보고 오랫동안 0 인 인덱스를 지우면 쓰기 성능과 저장 공간을 되찾는다.

## 확인 문제

1. 디스크 기반 DB 가 이진 탐색 트리 대신 B+트리를 쓰는 이유를 "페이지"라는 단어를 넣어 설명하라.
2. B+트리에서 범위 검색이 효율적인 구조적 이유는 무엇인가?
3. `(last_name, first_name, birth)` 인덱스가 도움이 되는 조건과 안 되는 조건을 하나씩 들어라.
4. 커버링 인덱스가 빠른 이유는?
5. 인덱스를 많이 만들수록 좋지 않은 이유 두 가지는?

### 풀이

1. 디스크는 페이지 단위로 읽으므로 노드 하나를 페이지 하나에 맞추고 키를 수백 개 넣으면 팬아웃이 커져 높이가 3~4 로 낮아진다. 이진 트리는 높이가 수십이라 페이지 읽기가 그만큼 많다.
2. 값이 리프에 정렬되어 있고 리프끼리 연결되어 있어, 시작점을 한 번 찾은 뒤 옆으로 순차 이동하면 된다.
3. 도움: `last_name = ? AND first_name = ?`. 안 됨: `first_name = ?` 만, 또는 `birth = ?` 만.
4. 필요한 열이 모두 인덱스 리프에 있어 테이블(힙)을 방문하는 추가 I/O 가 없다.
5. 쓰기마다 모든 인덱스를 갱신해야 해 쓰기가 느려지고, 저장 공간과 버퍼 메모리를 차지한다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- PostgreSQL 공식 문서, [B-Tree Indexes](https://www.postgresql.org/docs/current/btree.html)
- SQLite 공식 문서, [Query Planning](https://www.sqlite.org/queryplanner.html) — 인덱스와 커버링 인덱스를 그림으로 설명
- R. Bayer, E. McCreight, "Organization and Maintenance of Large Ordered Indexes", *Acta Informatica*, 1(3), 1972.
