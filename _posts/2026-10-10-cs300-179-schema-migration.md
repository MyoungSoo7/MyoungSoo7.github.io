---
layout: post
title: "[CS300 #179] 스키마 마이그레이션 — 달리는 차의 바퀴 갈아 끼우기"
date: 2026-10-10 20:59:00 +0900
categories: [cs]
tags: [cs300, database, schema-migration, zero-downtime, devops]
---

컴퓨터공학 300 주제 시리즈의 179번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

스키마 마이그레이션은 DB 구조 변경을 번호 붙은 스크립트로 관리해 코드처럼 버전 관리·검토·자동 적용하는 방법이고, 운영 중인 서비스에서는 "확장 → 이전 → 축소" 순서로 나눠야 무중단으로 바꿀 수 있다.

## 왜 필요한가

코드는 배포할 때마다 통째로 교체된다. 데이터베이스는 그렇지 않다. 어제의 데이터가 오늘도 그대로 있어야 하고, 그 위에서 구조만 바뀌어야 한다. 개발자 각자가 로컬 DB 에 `ALTER TABLE` 을 손으로 치고, 운영에는 누군가 기억에 의존해 같은 명령을 친다면, 환경마다 스키마가 조금씩 달라진다. "내 컴퓨터에서는 되는데"가 DB 에서도 일어난다.

또 운영 DB 는 멈추지 않는다. 열 이름 하나를 바꾸는 순간, 아직 옛 이름을 쓰는 서버가 하나라도 떠 있으면 그 서버는 오류를 낸다. 큰 테이블에 대한 변경은 테이블 전체를 잠가 서비스를 세울 수도 있다. 마이그레이션은 이 두 문제, 즉 **재현성**과 **무중단**을 다루는 기술이다.

Martin Fowler 와 Pramod Sadalage 의 글 "Evolutionary Database Design" 은 DB 변경을 작은 마이그레이션의 연속으로 다루고, 그것을 애플리케이션 코드와 같은 저장소에서 관리하자는 생각을 정리했다.

## 핵심 개념

### 버전 기반 마이그레이션

대부분의 도구(Flyway, Liquibase, Rails/Django/Alembic 의 마이그레이션)가 같은 구조를 쓴다.

```
migrations/
  V1__create_users.sql
  V2__add_email_to_users.sql
  V3__backfill_email.sql
  V4__index_email.sql

DB 안의 기록 테이블
  schema_migrations(version, description, applied_at, checksum)
```

1. 마이그레이션은 순번(또는 타임스탬프)이 붙은 파일이다.
2. DB 안의 기록 테이블이 "어디까지 적용했는지"를 저장한다.
3. 도구는 기록에 없는 파일만 순서대로 적용하고 기록을 남긴다.
4. **한 번 배포된 마이그레이션 파일은 고치지 않는다.** 고칠 일이 생기면 새 파일을 추가한다. Flyway 는 적용된 파일의 체크섬을 저장해, 누가 옛 파일을 고치면 검증 단계에서 오류를 낸다.

이렇게 하면 빈 DB 에서 시작해 모든 파일을 적용하면 언제나 같은 스키마가 나온다. 테스트 환경, 스테이징, 운영이 같은 경로를 밟는다.

### 트랜잭션 DDL

마이그레이션이 중간에 실패하면 어떻게 되는가? DB 마다 다르다.

- PostgreSQL 과 SQLite 는 대부분의 DDL 을 트랜잭션 안에서 실행할 수 있다. 실패하면 그 마이그레이션 전체가 롤백된다. 단, PostgreSQL 의 `CREATE INDEX CONCURRENTLY` 는 트랜잭션 블록 안에서 실행할 수 없다고 공식 문서에 명시되어 있다.
- MySQL 은 DDL 문이 암묵적 커밋을 일으킨다(레퍼런스 매뉴얼 "Statements That Cause an Implicit Commit"). 여러 DDL 로 된 마이그레이션이 중간에 실패하면 앞부분만 적용된 상태로 남는다. 그래서 MySQL 에서는 마이그레이션 하나에 DDL 하나를 두는 것이 안전하다.

### 무중단의 핵심: 확장 → 이전 → 축소

배포 중에는 옛 버전 서버와 새 버전 서버가 **동시에** 같은 DB 를 쓴다. 롤링 업데이트라면 몇 분, 롤백까지 생각하면 더 길게. 따라서 모든 스키마 상태는 "앞뒤 두 버전의 코드가 모두 동작하는" 상태여야 한다. `users.name` 을 `full_name` 으로 바꾸는 예를 보자.

```
단계 1 확장(expand)    ADD COLUMN full_name (nullable)
                        코드: name 과 full_name 둘 다 쓰기, 읽기는 name
단계 2 이전(migrate)   기존 행 backfill: full_name = name (작은 묶음으로 나눠서)
                        코드: 읽기를 full_name 으로 전환
단계 3 축소(contract)  코드: name 쓰기 중단 → 충분히 지난 뒤
                        DROP COLUMN name
```

`ALTER TABLE ... RENAME COLUMN` 한 줄이면 끝날 일을 세 번의 배포로 나눈다. 대신 어느 시점에 배포를 멈추거나 되돌려도 서비스가 깨지지 않는다. 이 패턴은 parallel change 라고도 부른다.

### 위험한 연산 목록

| 연산 | 위험 | 안전한 방법 |
|---|---|---|
| 열 이름 변경·삭제 | 옛 코드가 깨짐 | 확장 → 이전 → 축소 |
| `NOT NULL` 열 추가 | 기존 행에 값이 없어 실패하거나 전체 재작성 | 기본값과 함께 추가하거나, nullable 로 추가 후 채우고 제약 추가 |
| 큰 테이블에 인덱스 생성 | 생성 중 쓰기 차단 | PostgreSQL `CREATE INDEX CONCURRENTLY` |
| 외래 키·CHECK 추가 | 전체 행 검사 동안 락 | PostgreSQL `ADD CONSTRAINT ... NOT VALID` 후 `VALIDATE CONSTRAINT` |
| 열 타입 변경 | 대개 테이블 재작성 | 새 열 추가 후 이전 |
| 대량 backfill | 긴 트랜잭션, 락, 복제 지연 | 1,000~10,000 행 단위로 나눠 커밋 |

PostgreSQL 문서에 따르면 `ADD COLUMN` 에 휘발성이 아닌 `DEFAULT` 를 주면 그 값은 테이블 메타데이터에 저장되고 기존 행을 다시 쓰지 않는다. 반면 `random()` 같은 휘발성 기본값은 모든 행을 다시 써야 한다. 이런 세부 사항이 "1초 걸리는 마이그레이션"과 "한 시간 동안 테이블이 잠기는 마이그레이션"을 가른다.

### 락 대기 줄 서기

DDL 은 대개 강한 테이블 락을 원한다. 그 락을 얻으려고 기다리는 동안, 그 뒤에 들어온 평범한 `SELECT` 까지 DDL 뒤에 줄을 선다. 긴 분석 쿼리 하나 + `ALTER TABLE` 하나 = 서비스 정지가 될 수 있다. 그래서 마이그레이션 세션에는 `SET lock_timeout = '3s'` 같은 짧은 상한을 걸고, 실패하면 재시도하게 한다.

## 직접 해 보기

마이그레이션 도구의 핵심을 30줄로 구현한다. 기록 테이블, 순서대로 적용, 재실행 시 건너뛰기, 실패 시 롤백.

```python
import sqlite3

MIGRATIONS = [   # (버전, 설명, SQL) — 한 번 배포된 항목은 절대 고치지 않고 뒤에 덧붙인다
    (1, "create users", "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"),
    (2, "expand: add email (nullable)", "ALTER TABLE users ADD COLUMN email TEXT"),
    (3, "backfill email", "UPDATE users SET email = name || '@example.com' WHERE email IS NULL"),
    (4, "index email", "CREATE UNIQUE INDEX idx_users_email ON users(email)"),
]

def migrate(con, target=None):
    con.execute("""CREATE TABLE IF NOT EXISTS schema_migrations
                   (version INTEGER PRIMARY KEY, description TEXT,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    done = {v for (v,) in con.execute("SELECT version FROM schema_migrations")}
    for version, desc, sql in MIGRATIONS:
        if version in done or (target and version > target):
            continue
        con.execute("BEGIN")                        # 마이그레이션 하나 = 트랜잭션 하나
        try:
            for stmt in sql.split(";"):
                con.execute(stmt)
            con.execute("INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                        (version, desc))
            con.execute("COMMIT")
        except sqlite3.Error:
            con.execute("ROLLBACK")
            raise
        print(f"  적용 V{version}: {desc}")

con = sqlite3.connect(":memory:", isolation_level=None)   # BEGIN/COMMIT 을 직접 관리
print("1차 배포 (V1 까지)"); migrate(con, target=1)
con.executemany("INSERT INTO users (name) VALUES (?)", [("kim",), ("lee",)])
print("2차 배포 (끝까지)"); migrate(con)
print("다시 실행 (아무것도 안 함)"); migrate(con)
print(con.execute("SELECT * FROM users").fetchall())

# 두 문장 중 두 번째가 실패하면 첫 번째 DDL 까지 롤백된다 (SQLite 는 트랜잭션 DDL 지원)
MIGRATIONS.append((5, "add phone + bad index",
    "ALTER TABLE users ADD COLUMN phone TEXT; CREATE UNIQUE INDEX idx_name ON users(nam)"))
try:
    migrate(con)
except sqlite3.OperationalError as e:
    print("V5 실패:", e)
cols = [r[1] for r in con.execute("PRAGMA table_info(users)")]
print("users 열:", cols, "/ 현재 버전:",
      con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
```

결과:

```
1차 배포 (V1 까지)
  적용 V1: create users
2차 배포 (끝까지)
  적용 V2: expand: add email (nullable)
  적용 V3: backfill email
  적용 V4: index email
다시 실행 (아무것도 안 함)
[(1, 'kim', 'kim@example.com'), (2, 'lee', 'lee@example.com')]
V5 실패: no such column: nam
users 열: ['id', 'name', 'email'] / 현재 버전: 4
```

V2~V4 가 확장 → 이전(backfill) → 제약 추가의 축소판이다. 데이터가 있는 상태에서 `email` 을 처음부터 `NOT NULL UNIQUE` 로 추가하려 했다면 기존 행 때문에 실패했을 것이다. V5 에서는 첫 문장(`ADD COLUMN phone`)은 성공했지만 두 번째 문장의 오타로 실패했고, 트랜잭션 DDL 덕분에 `phone` 열까지 함께 사라졌다. 기록 테이블도 4 에 머물러, 고친 뒤 다시 실행하면 V5 부터 깨끗하게 시작한다. MySQL 이었다면 `phone` 열만 남은 어정쩡한 상태가 되었을 것이다.

참고로 Python `sqlite3` 의 기본(레거시) 트랜잭션 모드는 DML 앞에서만 암묵적으로 `BEGIN` 을 넣는다. 그래서 위 코드는 `isolation_level=None` 으로 자동 처리를 끄고 `BEGIN`/`COMMIT` 을 직접 썼다. 그렇지 않으면 DDL 이 트랜잭션 밖에서 즉시 커밋된다.

## 현업에서는

- **마이그레이션은 배포 파이프라인의 한 단계**다. 컨테이너 환경에서는 애플리케이션 시작 전에 마이그레이션 잡(쿠버네티스 Job 이나 init container, Helm 훅)을 돌리는 구성이 흔하다. 여러 파드가 동시에 마이그레이션을 시도하지 않도록, 도구가 DB 락(PostgreSQL 권고 락 등)으로 한 번에 하나만 실행하게 하는지 확인한다.
- **리뷰 체크리스트**: "이 마이그레이션은 옛 버전 코드와 호환되는가?", "큰 테이블을 재작성하는가?", "인덱스를 동시 생성하는가?", "롤백 경로가 있는가?". 몇몇 팀은 위험 연산을 자동으로 잡아내는 린터를 CI 에 붙인다.
- **다운 마이그레이션의 현실**: 도구들은 되돌리기 스크립트를 지원하지만, 열을 지운 뒤에는 데이터가 돌아오지 않는다. 운영에서는 "앞으로 고치는 마이그레이션(roll forward)"이 대부분이다. 그래서 축소 단계(DROP)는 충분히 늦게, 백업이 있는 상태에서 한다.
- **스테이징에서 운영 규모로 리허설**: 행 100개짜리 테이블에서는 모든 마이그레이션이 즉시 끝난다. 운영 크기의 사본에서 걸린 시간과 락을 측정해 보는 것이 가장 확실한 검증이다.

## 확인 문제

1. 이미 운영에 적용된 마이그레이션 파일을 수정하면 안 되는 이유는?
2. 열 이름 변경을 한 번의 `RENAME` 으로 하면 롤링 배포 중 어떤 일이 생기는가?
3. 확장 → 이전 → 축소의 각 단계에서 코드는 무엇을 읽고 쓰는가?
4. PostgreSQL 에서 큰 테이블에 외래 키를 추가할 때 락 시간을 줄이는 방법은?
5. MySQL 에서 한 마이그레이션 파일에 DDL 을 여러 개 넣는 것이 위험한 이유는?

### 풀이

1. 이미 적용된 환경에서는 다시 실행되지 않으므로 환경마다 스키마가 갈라진다. 새 마이그레이션을 추가해야 모든 환경이 같은 경로를 밟는다.
2. 아직 옛 이름을 쓰는 옛 버전 서버들이 "열 없음" 오류를 낸다. 롤백해도 옛 코드가 새 이름을 모른다.
3. 확장: 새 열 추가, 코드는 양쪽에 쓰고 옛 열을 읽음. 이전: 기존 데이터 채우고, 읽기를 새 열로 전환. 축소: 옛 열 쓰기를 멈춘 뒤 옛 열 삭제.
4. `ADD CONSTRAINT ... NOT VALID` 로 새 행에만 적용되게 빠르게 추가하고, 나중에 `VALIDATE CONSTRAINT` 로 기존 행을 더 약한 락으로 검사한다.
5. DDL 이 암묵적으로 커밋되어, 중간 실패 시 앞부분 DDL 만 적용된 상태로 남고 자동 롤백되지 않는다.

## 더 읽을거리 (References)

- Pramod Sadalage, Martin Fowler, [Evolutionary Database Design](https://martinfowler.com/articles/evodb.html)
- PostgreSQL 공식 문서, [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html), [CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html)
- Redgate Flyway 공식 문서, [Flyway Documentation](https://documentation.red-gate.com/fd)
- SQLite 공식 문서, [ALTER TABLE](https://www.sqlite.org/lang_altertable.html)
