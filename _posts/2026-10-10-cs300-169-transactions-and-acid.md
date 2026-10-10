---
layout: post
title: "[CS300 #169] 트랜잭션과 ACID — 전부 아니면 전무"
date: 2026-10-10 20:49:00 +0900
categories: [cs]
tags: [cs300, database, transaction, acid, durability]
---

컴퓨터공학 300 주제 시리즈의 169번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

트랜잭션은 여러 읽기·쓰기를 하나의 논리적 작업으로 묶는 단위이고, ACID 는 그 단위가 지켜야 할 네 가지 성질(원자성, 일관성, 격리성, 지속성)이다.

## 왜 필요한가

계좌 이체는 두 개의 쓰기다. A 에서 빼고, B 에 더한다. 첫 번째가 끝나고 두 번째 전에 서버가 죽으면 돈이 사라진다. 두 이체가 동시에 같은 계좌를 건드리면 잔액이 엉뚱해진다. 커밋했다고 응답했는데 전원이 나가 기록이 없어지면 고객과 회사의 장부가 어긋난다.

이 문제들은 애플리케이션이 각자 풀기에는 너무 어렵고, 너무 자주 나온다. 그래서 DB 가 트랜잭션이라는 추상화로 한꺼번에 해결한다. 개발자는 "여기서 여기까지가 한 덩어리"라고만 선언하면 된다. Jim Gray 의 1981년 논문 "The Transaction Concept: Virtues and Limitations" 가 개념을 정리했고, Härder 와 Reuter 가 1983년 논문에서 ACID 라는 약어를 붙였다.

## 핵심 개념

### 트랜잭션의 생애

```
BEGIN ──▶ 읽기/쓰기 ... ──┬──▶ COMMIT   ──▶ 모든 변경이 확정, 이후 영구
                           └──▶ ROLLBACK ──▶ 모든 변경이 취소, 시작 전 상태
```

SQL 로는 다음과 같다.

```sql
BEGIN;
UPDATE account SET balance = balance - 300 WHERE id = 'A';
UPDATE account SET balance = balance + 300 WHERE id = 'B';
COMMIT;
```

명시적으로 `BEGIN` 하지 않으면 대부분의 DB 는 문장 하나하나를 각각의 트랜잭션으로 자동 커밋한다(autocommit). 위 두 `UPDATE` 를 autocommit 으로 실행하면 그 사이가 무방비다.

### A — 원자성 (Atomicity)

트랜잭션 안의 변경은 **전부 반영되거나 전혀 반영되지 않는다.** 중간에 오류가 나거나 프로세스가 죽으면, DB 는 그 트랜잭션이 한 일을 모두 되돌린다. 구현은 되돌릴 정보를 기록해 두는 방식이다. 로그(undo 정보)나, 변경 전 페이지를 따로 저장하는 롤백 저널 같은 것이다. 이는 "WAL 과 복구" 글에서 자세히 본다.

여기서 원자성은 동시성과 관련된 "원자적 연산"과 다른 뜻이다. ACID 의 A 는 **실패 시 전부 취소**에 대한 이야기다. 동시에 실행되는 다른 트랜잭션에 어떻게 보이는가는 I 의 몫이다.

### C — 일관성 (Consistency)

트랜잭션은 DB 를 하나의 올바른 상태에서 다른 올바른 상태로 옮긴다. "올바름"은 두 층이다.

- DB 가 강제하는 것: 기본 키, 외래 키, `CHECK`, `NOT NULL` 같은 선언된 제약.
- 애플리케이션이 책임지는 것: "이체 전후 총액이 같다" 같은 업무 규칙.

C 는 나머지 셋과 성격이 다르다. A, I, D 는 DB 가 보장하는 기계적 성질이고, C 는 그 위에서 애플리케이션이 올바른 트랜잭션을 작성했을 때 얻는 결과다. DB 는 제약 위반을 감지하면 트랜잭션을 실패시켜 C 를 돕는다.

### I — 격리성 (Isolation)

동시에 실행되는 트랜잭션들이 서로의 중간 상태를 보지 않는 성질이다. 이상적으로는 트랜잭션들이 **어떤 순서로 하나씩 실행된 것과 같은 결과**가 나와야 한다. 이를 직렬 가능성(serializability)이라 한다.

완전한 직렬 가능성은 비싸다. 그래서 SQL 표준은 여러 **격리 수준**을 정의해 성능과 정확성을 맞바꾸게 한다. 많은 DB 의 기본값은 직렬 가능이 아니다. PostgreSQL 은 Read Committed, MySQL InnoDB 는 Repeatable Read 가 기본이다. 이 차이가 어떤 버그를 만드는지는 다음 글 "격리 수준과 이상 현상"에서 다룬다.

### D — 지속성 (Durability)

`COMMIT` 이 성공했다고 응답한 변경은 **그 뒤 전원이 꺼져도 남아 있다.** 이를 위해 DB 는 커밋 응답 전에 변경 기록을 디스크에 실제로 내려 쓴다(`fsync`). 메모리에만 있는 상태에서 "커밋됨"이라고 말하지 않는다.

지속성은 설정으로 약해질 수 있다. 예를 들어 PostgreSQL 의 `synchronous_commit = off` 는 커밋 응답을 디스크 기록보다 먼저 보내 지연을 줄이는 대신, 크래시 시 최근 커밋 일부를 잃을 수 있다(데이터 손상은 아니다). 디스크 컨트롤러가 쓰기 캐시를 거짓 보고하면 DB 가 아무리 `fsync` 를 해도 지속성이 깨진다.

### 네 성질을 한 장으로

| 성질 | 질문 | 주로 쓰는 장치 |
|---|---|---|
| 원자성 | 실패하면 반쯤 남지 않는가? | undo 로그, 롤백 저널 |
| 일관성 | 규칙을 어기는 상태로 끝나지 않는가? | 제약 조건 + 올바른 애플리케이션 |
| 격리성 | 동시에 돌아도 서로 간섭하지 않는가? | 락, MVCC |
| 지속성 | 커밋 후 장애에도 남는가? | WAL, fsync, 복제 |

## 직접 해 보기

파일 DB 로 이체를 만들고, 중간 실패와 프로세스 크래시를 흉내 낸다. Python `sqlite3` 의 연결 객체를 `with` 블록으로 쓰면 정상 종료 시 커밋, 예외 시 롤백한다.

```python
import sqlite3, os, subprocess, sys, tempfile
path = os.path.join(tempfile.mkdtemp(), "bank.db")
con = sqlite3.connect(path)
con.executescript("""
CREATE TABLE account (id TEXT PRIMARY KEY, balance INTEGER NOT NULL CHECK (balance >= 0));
INSERT INTO account VALUES ('A', 1000), ('B', 0);
""")
con.commit()

def transfer(con, src, dst, amount):
    with con:   # 블록이 정상 종료되면 COMMIT, 예외면 ROLLBACK
        con.execute("UPDATE account SET balance = balance + ? WHERE id = ?", (amount, dst))
        con.execute("UPDATE account SET balance = balance - ? WHERE id = ?", (amount, src))

def show(label):
    print(label, dict(con.execute("SELECT id, balance FROM account")))

transfer(con, "A", "B", 300); show("300 이체 후:")
try:
    transfer(con, "A", "B", 5000)   # 입금은 성공, 출금에서 CHECK 위반
except sqlite3.IntegrityError as e:
    print("실패:", e)
show("실패 후(원자성):")

# 지속성: 커밋 전에 프로세스가 죽으면? 커밋 후에 죽으면?
crash = f"""
import sqlite3, os
c = sqlite3.connect({path!r})
c.execute("UPDATE account SET balance = 0 WHERE id = 'A'")       # 커밋 안 함
os._exit(1)
"""
subprocess.run([sys.executable, "-c", crash])
show("커밋 전 크래시 후:")
crash2 = crash.replace("# 커밋 안 함", "\nc.commit()")
subprocess.run([sys.executable, "-c", crash2])
show("커밋 후 크래시 후:")
```

결과:

```
300 이체 후: {'A': 700, 'B': 300}
실패: CHECK constraint failed: balance >= 0
실패 후(원자성): {'A': 700, 'B': 300}
커밋 전 크래시 후: {'A': 700, 'B': 300}
커밋 후 크래시 후: {'A': 0, 'B': 300}
```

5000원 이체는 B 에 입금하는 첫 문장이 이미 성공한 상태에서 실패했다. 그런데 B 는 300 그대로다. 롤백이 첫 문장까지 되돌렸다. 이것이 원자성이다. 두 번째 실험에서 자식 프로세스는 `os._exit` 로 정리 없이 죽었다. 커밋 전이면 변경이 없고, 커밋 후면 변경이 남는다. 이것이 지속성의 경계선이 `COMMIT` 이라는 뜻이다. (진짜 전원 차단까지 흉내 내지는 않았다. 그 경우를 견디는 장치는 SQLite 문서의 "Atomic Commit In SQLite" 에 자세히 나온다.)

## 현업에서는

- **트랜잭션 경계는 서비스 메서드 단위**로 잡는 것이 일반적이다. Spring 의 `@Transactional`, Django 의 `transaction.atomic()` 이 모두 이 블록을 선언하는 도구다. 경계 밖에서 예외를 삼키면 롤백이 일어나지 않는 버그가 흔하다.
- **긴 트랜잭션은 독**이다. 트랜잭션 안에서 외부 API 를 호출하고 응답을 기다리면 그동안 락과 오래된 버전이 유지된다. PostgreSQL 에서는 오래 열린 트랜잭션이 vacuum 을 막아 테이블이 부풀어 오른다. 외부 호출은 트랜잭션 밖으로 뺀다.
- **DB 트랜잭션은 DB 안에서만 원자적**이다. "DB 에 주문 저장 + 메시지 큐에 이벤트 발행"은 하나의 트랜잭션이 아니다. 그래서 아웃박스 패턴(같은 트랜잭션으로 아웃박스 테이블에 이벤트를 쓰고, 별도 프로세스가 발행)을 쓴다.
- **재시도 가능하게 작성**: 직렬화 실패나 교착 상태로 트랜잭션이 취소될 수 있다. 트랜잭션 전체를 다시 실행할 수 있도록 멱등하게 짜 두는 것이 안전하다.

## 확인 문제

1. autocommit 모드에서 이체의 두 `UPDATE` 를 차례로 실행하면 어떤 위험이 있는가?
2. ACID 의 C 가 나머지 셋과 성격이 다른 이유는?
3. "원자성"과 "격리성"을 혼동하기 쉬운 이유와 둘의 차이를 설명하라.
4. 위 실험에서 5000원 이체의 첫 문장(입금)은 성공했는데 결과에 반영되지 않은 이유는?
5. `synchronous_commit = off` 를 쓰면 ACID 중 무엇을 일부 양보하는가?

### 풀이

1. 각 문장이 별도 트랜잭션이라 첫 문장 뒤에 장애가 나면 한쪽만 반영된다.
2. A·I·D 는 DB 가 기계적으로 보장하지만, C 는 업무 규칙을 지키는 트랜잭션을 애플리케이션이 작성해야 성립한다. DB 는 선언된 제약만 강제한다.
3. 둘 다 "중간 상태가 드러나지 않는다"는 느낌을 주기 때문이다. 원자성은 실패 시 전부 취소, 격리성은 동시 실행 중 서로의 중간 상태가 보이지 않음에 관한 것이다.
4. 두 번째 문장에서 예외가 나 `with` 블록이 롤백했고, 롤백은 트랜잭션 안의 모든 변경을 되돌린다.
5. 지속성. 크래시 직전에 커밋 응답을 받은 일부 트랜잭션이 사라질 수 있다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- SQLite 공식 문서, [Atomic Commit In SQLite](https://www.sqlite.org/atomiccommit.html), [Transaction](https://www.sqlite.org/lang_transaction.html)
- Python 공식 문서, [sqlite3 — Transaction control](https://docs.python.org/3/library/sqlite3.html)
- Theo Härder, Andreas Reuter, "Principles of Transaction-Oriented Database Recovery", *ACM Computing Surveys*, 15(4), 1983.
