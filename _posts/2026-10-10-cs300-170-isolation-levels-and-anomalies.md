---
layout: post
title: "[CS300 #170] 격리 수준과 이상 현상 — 동시에 돌 때 무엇이 보이는가"
date: 2026-10-10 20:50:00 +0900
categories: [cs]
tags: [cs300, database, isolation-level, concurrency, serializability]
---

컴퓨터공학 300 주제 시리즈의 170번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

격리 수준은 동시에 실행되는 트랜잭션끼리 서로의 변경을 얼마나 볼 수 있는지를 정한 계약이고, 수준을 낮출수록 빨라지는 대신 더티 읽기·반복 불가능 읽기·팬텀·갱신 손실·쓰기 왜곡 같은 이상 현상이 허용된다.

## 왜 필요한가

트랜잭션을 정말 하나씩 줄 세워 실행하면 격리 문제는 없다. 하지만 동시 처리량이 바닥난다. 그래서 DB 는 트랜잭션을 겹쳐서 실행하고, 그 결과가 "줄 세워 실행한 것과 같아 보이도록" 노력한다. 이 노력을 얼마나 할지 고르는 손잡이가 격리 수준이다.

문제는 많은 DB 의 기본 수준이 완전한 격리(직렬 가능)가 아니라는 점이다. 기본값 그대로 "재고 확인 후 차감" 코드를 짜면 동시 요청에서 재고가 음수가 된다. 어떤 수준에서 어떤 이상이 가능한지 알아야, 어디에 락을 걸고 어디서 재시도할지 정할 수 있다.

## 핵심 개념

### 이상 현상 다섯 가지

T1, T2 두 트랜잭션이 동시에 돈다고 하자.

**1. 더티 읽기 (dirty read)** — 커밋되지 않은 값을 읽는다.

```
T1: UPDATE x = 50
T2:                 READ x → 50
T1: ROLLBACK                        (x 는 원래 값으로, 그런데 T2 는 50 을 봤다)
```

**2. 반복 불가능 읽기 (non-repeatable read)** — 같은 행을 두 번 읽었는데 값이 다르다.

```
T1: READ x → 10
T2:                 UPDATE x = 20; COMMIT
T1: READ x → 20
```

**3. 팬텀 (phantom)** — 같은 조건으로 두 번 조회했는데 행 집합이 다르다.

```
T1: SELECT COUNT(*) WHERE dept = 'A' → 5
T2:                 INSERT (dept = 'A'); COMMIT
T1: SELECT COUNT(*) WHERE dept = 'A' → 6
```

**4. 갱신 손실 (lost update)** — 둘이 같은 값을 읽고 각자 계산해 쓰면, 먼저 쓴 쪽이 덮어써진다.

```
T1: READ n → 0              T2: READ n → 0
T1: WRITE n = 1             T2: WRITE n = 1      (두 번 +1 했는데 결과는 1)
```

**5. 쓰기 왜곡 (write skew)** — 둘이 같은 조건을 읽고, 서로 다른 행을 써서 함께 규칙을 깬다. 대표 예는 "당직 의사는 최소 1명"이다. 두 의사가 동시에 "지금 당직이 2명이니 나는 빠져도 된다"를 확인하고 각자 자기 행을 `off` 로 바꾼다. 각자는 다른 행을 썼으니 충돌이 없지만, 결과는 당직 0명이다.

### SQL 표준의 네 수준

SQL 표준은 앞의 세 현상(더티 읽기, 반복 불가능 읽기, 팬텀)을 기준으로 네 수준을 정의한다.

| 격리 수준 | 더티 읽기 | 반복 불가능 읽기 | 팬텀 |
|---|---|---|---|
| Read Uncommitted | 허용 | 허용 | 허용 |
| Read Committed | 방지 | 허용 | 허용 |
| Repeatable Read | 방지 | 방지 | 허용 |
| Serializable | 방지 | 방지 | 방지 |

표준의 Serializable 은 사실 "세 현상이 없다"보다 강하다. 어떤 직렬 순서로 실행한 것과 같은 결과를 요구한다.

### 표준 표의 한계

Berenson 등은 1995년 논문 "A Critique of ANSI SQL Isolation Levels" 에서 이 표가 모호하고, 실제 시스템에서 중요한 현상(갱신 손실, 쓰기 왜곡)을 빠뜨렸다고 지적했다. 그리고 많은 DB 가 실제로 구현하는 **스냅숏 격리(Snapshot Isolation)** 를 정의했다.

스냅숏 격리에서 각 트랜잭션은 시작 시점의 일관된 스냅숏을 읽는다. 두 트랜잭션이 같은 행을 쓰면 나중 쪽이 실패한다(먼저 커밋한 쪽이 이긴다). 그래서 더티 읽기, 반복 불가능 읽기, 팬텀, 갱신 손실은 막지만 **쓰기 왜곡은 막지 못한다.** 서로 다른 행을 쓰기 때문이다.

### 실제 DB 는 표와 다르다

| DB | 기본 수준 | 특이점 |
|---|---|---|
| PostgreSQL | Read Committed | Read Uncommitted 를 요청해도 Read Committed 로 동작한다. Repeatable Read 는 스냅숏 격리라 표준과 달리 팬텀도 막는다. Serializable 은 직렬화 가능 스냅숏 격리(SSI)로 쓰기 왜곡까지 감지해 한쪽을 실패시킨다. |
| MySQL InnoDB | Repeatable Read | 일관된 읽기는 스냅숏, 잠금 읽기(`SELECT ... FOR UPDATE`)는 넥스트키 락으로 팬텀을 막는다. |
| SQLite | Serializable | 쓰기는 한 번에 하나. WAL 모드에서 읽기는 스냅숏. |

PostgreSQL 의 공식 문서에 이 표가 정확히 나와 있다. 같은 이름의 격리 수준이라도 DB 마다 보장이 다르므로, 수준 이름이 아니라 **그 DB 의 문서**를 기준으로 판단해야 한다.

### 대응 방법

| 문제 | 방법 |
|---|---|
| 갱신 손실 | 원자적 갱신(`SET n = n + 1`), `SELECT ... FOR UPDATE`, 버전 열로 낙관적 락 |
| 쓰기 왜곡 | Serializable 수준, 또는 판단 근거가 되는 행들을 `FOR UPDATE` 로 잠금, 또는 제약으로 표현 |
| Serializable 실패 | 직렬화 실패 오류(PostgreSQL SQLSTATE `40001`) 를 받으면 트랜잭션 전체 재시도 |

## 직접 해 보기

SQLite 의 WAL 모드에서 두 연결로 갱신 손실과 스냅숏을 재현한다.

```python
import sqlite3, os, tempfile
path = os.path.join(tempfile.mkdtemp(), "iso.db")
setup = sqlite3.connect(path)
setup.execute("PRAGMA journal_mode=WAL")
setup.executescript("CREATE TABLE counter (id INTEGER PRIMARY KEY, n INTEGER);"
                    "INSERT INTO counter VALUES (1, 0);")
setup.commit()

def conn():
    return sqlite3.connect(path, isolation_level=None)  # BEGIN/COMMIT 을 직접 쓴다

t1, t2 = conn(), conn()
read = lambda c: c.execute("SELECT n FROM counter WHERE id = 1").fetchone()[0]

# 1) 갱신 손실: 두 클라이언트가 읽고 → 계산하고 → 쓴다 (트랜잭션 없이)
a = read(t1); b = read(t2)
t1.execute("UPDATE counter SET n = ? WHERE id = 1", (a + 1,))
t2.execute("UPDATE counter SET n = ? WHERE id = 1", (b + 1,))
print("두 번 +1 했는데:", read(t1))

# 2) 원자적 갱신으로 해결
t1.execute("UPDATE counter SET n = n + 1 WHERE id = 1")
t2.execute("UPDATE counter SET n = n + 1 WHERE id = 1")
print("n = n + 1 두 번 후:", read(t1))

# 3) 스냅숏: t1 의 읽기 트랜잭션 도중 t2 가 커밋해도 t1 은 같은 값을 본다
t1.execute("BEGIN"); first = read(t1)
t2.execute("UPDATE counter SET n = 100 WHERE id = 1")      # autocommit
second = read(t1); t1.execute("COMMIT")
print("t1 트랜잭션 안: 첫 읽기", first, "두 번째 읽기", second, "/ 커밋 후", read(t1))

# 4) 스냅숏에서 쓰기 시도: 낡은 스냅숏으로는 쓸 수 없다
t1.execute("BEGIN"); read(t1)
t2.execute("UPDATE counter SET n = 200 WHERE id = 1")
try:
    t1.execute("UPDATE counter SET n = n + 1 WHERE id = 1")
except sqlite3.OperationalError as e:
    print("t1 쓰기 거부:", e)
t1.execute("ROLLBACK")
```

결과:

```
두 번 +1 했는데: 1
n = n + 1 두 번 후: 3
t1 트랜잭션 안: 첫 읽기 3 두 번째 읽기 3 / 커밋 후 100
t1 쓰기 거부: database is locked
```

1번은 읽기와 쓰기가 다른 문장이라 사이에 끼어들 틈이 있었고, 한 번의 증가가 사라졌다. 2번은 읽기·계산·쓰기를 DB 안에서 한 문장으로 처리해 둘 다 반영되었다. 3번에서 t1 은 트랜잭션 동안 처음 본 스냅숏을 계속 본다. 반복 불가능 읽기가 없다. 4번에서 t1 은 낡은 스냅숏 위에서 쓰려다 거부되었다. SQLite 문서는 이 경우를 `SQLITE_BUSY_SNAPSHOT` 으로 설명한다. 메시지는 "locked" 지만 기다린다고 풀리지 않으므로 트랜잭션을 처음부터 다시 해야 한다. 스냅숏 격리가 갱신 손실을 막는 방식이 이것이다.

## 현업에서는

- **재고·좌석·쿠폰 차감**은 격리 수준 버그의 단골이다. `SELECT stock` → 애플리케이션에서 비교 → `UPDATE stock = ?` 패턴은 Read Committed 에서 갱신 손실을 낸다. `UPDATE ... SET stock = stock - 1 WHERE id = ? AND stock > 0` 처럼 조건부 원자 갱신으로 바꾸고, 영향받은 행 수로 성공 여부를 판단한다.
- **JPA 의 `@Version`** 은 낙관적 락이다. 수정 시 `WHERE version = ?` 를 붙여, 그사이 누가 바꿨으면 영향 행이 0이 되어 예외가 난다.
- **Serializable 을 켜면 재시도 코드가 필수**다. PostgreSQL 은 직렬화 이상을 감지하면 트랜잭션을 실패시키고, 애플리케이션이 다시 실행해야 한다. 재시도 없이 수준만 올리면 오류율만 오른다.
- **리포트 쿼리와 Repeatable Read**: 여러 쿼리로 된 리포트가 서로 다른 시점의 데이터를 섞어 보지 않도록, 리포트 전체를 Repeatable Read 트랜잭션으로 감싸 한 스냅숏에서 읽게 한다.

## 확인 문제

1. 더티 읽기와 반복 불가능 읽기의 차이는?
2. 스냅숏 격리가 막지 못하는 이상 현상과 그 이유는?
3. PostgreSQL 에서 `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` 를 하면 더티 읽기를 볼 수 있는가?
4. "잔액이 충분하면 출금" 로직을 Read Committed 에서 안전하게 만드는 방법 두 가지를 들어라.

### 풀이

1. 더티 읽기는 커밋되지 않은 값을 보는 것이고, 반복 불가능 읽기는 커밋된 값이지만 같은 트랜잭션 안에서 두 번 읽은 값이 달라지는 것이다.
2. 쓰기 왜곡. 두 트랜잭션이 서로 다른 행을 쓰므로 쓰기 충돌 검사에 걸리지 않는다.
3. 볼 수 없다. PostgreSQL 은 Read Uncommitted 를 Read Committed 로 동작시킨다.
4. `UPDATE account SET balance = balance - ? WHERE id = ? AND balance >= ?` 후 영향 행 수 확인. 또는 `SELECT ... FOR UPDATE` 로 행을 잠근 뒤 확인·갱신.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- H. Berenson, P. Bernstein, J. Gray, J. Melton, E. O'Neil, P. O'Neil, "A Critique of ANSI SQL Isolation Levels", *ACM SIGMOD*, 1995. [arXiv 사본](https://arxiv.org/abs/cs/0701157)
- SQLite 공식 문서, [Isolation In SQLite](https://www.sqlite.org/isolation.html), [Write-Ahead Logging](https://www.sqlite.org/wal.html)
- PostgreSQL 공식 문서, [SET TRANSACTION](https://www.postgresql.org/docs/current/sql-set-transaction.html)
