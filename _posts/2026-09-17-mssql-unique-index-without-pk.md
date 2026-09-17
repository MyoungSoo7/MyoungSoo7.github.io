---
layout: post
title: "MSSQL 에서 PK 없이 UNIQUE 인덱스로 컬럼 관리하기 — 되는 것, 잃는 것, 조심할 것"
date: 2026-09-17 19:05:00 +0900
categories: [Engineering, Database]
tags: [MSSQL, SQL Server, Primary Key, Unique Index, Heap, Filtered Index]
---

레거시 테이블을 물려받으면 종종 만난다 — PK 는 없는데 UNIQUE 인덱스가 중복을 막고 있는 테이블. 또는 설계 단계에서 "자연키가 NULL 을 가질 수 있어서 PK 를 못 걸겠다" 는 상황. **PK 없이 UNIQUE 인덱스만으로 테이블을 관리하는 것은 SQL Server 에서 완전히 합법이고, 어떤 경우엔 더 맞는 설계다.** 다만 공짜가 아니다. 되는 것과 잃는 것을 [Microsoft 공식 문서](https://learn.microsoft.com/en-us/sql/relational-databases/tables/unique-constraints-and-check-constraints) 기준으로 정리한다.

## 1. PK 와 UNIQUE 는 생각보다 가깝다

기능만 보면 둘 다 "중복 금지" 다. 차이는 세 줄로 줄어든다.

| | PRIMARY KEY | UNIQUE 제약/인덱스 |
| --- | --- | --- |
| NULL | 불가 | **가능 — 단 컬럼당 1개** |
| 테이블당 개수 | 1개 | 여러 개 |
| 만들어지는 인덱스 | 기본 **클러스터드** (없을 때) | 기본 **넌클러스터드** |

MS 문서의 표현 그대로: UNIQUE 제약은 ["컬럼당 NULL 하나를 허용"](https://learn.microsoft.com/en-us/sql/relational-databases/tables/unique-constraints-and-check-constraints)하고, ["기본으로 넌클러스터드 인덱스를 만들어 제약을 강제"](https://learn.microsoft.com/en-us/sql/relational-databases/tables/unique-constraints-and-check-constraints)한다.

그리고 중요한 사실 하나 — **FK 는 PK 만 참조할 수 있는 게 아니다.** [공식 문서](https://learn.microsoft.com/en-us/sql/relational-databases/tables/primary-and-foreign-key-constraints)는 FK 가 "primary **or unique** key column" 과 매칭된다고 명시한다. 즉 PK 를 포기해도 이 테이블을 부모로 하는 FK 관계는 유지할 수 있다 (단, UNIQUE **제약**이어야 하며 뒤에서 볼 필터드 인덱스로는 안 된다).

## 2. NULL 이 문제라면 — 표준 해법은 필터드 UNIQUE 인덱스

UNIQUE 제약의 "NULL 1개 허용" 은 표준 SQL(NULL 무제한)과 다른 SQL Server 의 고유 동작이라 자주 발목을 잡는다. 사번은 유일해야 하지만 미발급자는 NULL 인 컬럼처럼 **"값이 있으면 유일, NULL 은 여러 개"** 가 필요하면 [필터드 인덱스](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/create-filtered-indexes)로 푼다:

```sql
CREATE UNIQUE NONCLUSTERED INDEX UX_Employee_EmpNo
ON dbo.Employee(EmpNo)
WHERE EmpNo IS NOT NULL;
```

NULL 행은 인덱스에서 제외되므로 유일성 검사 대상에서 빠진다. 이 패턴이 "PK 없이 UNIQUE 인덱스로 관리" 구성의 가장 큰 실전 이유다 — **PK 로는 표현 자체가 불가능한 규칙**이기 때문이다. 대신 이건 제약(constraint)이 아니라 인덱스라서 FK 의 참조 대상이 될 수 없다는 트레이드오프가 있다.

## 3. 잃는 것 ① — 클러스터드 인덱스가 저절로 생기지 않는다

PK 를 지우면 같이 사라지는 게 있다. PK 는 (다른 클러스터드 인덱스가 없다면) 클러스터드 인덱스를 만들어 테이블의 물리 구조를 잡아준다. PK 도 클러스터드 인덱스도 없는 테이블은 [힙(heap)](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/heaps-tables-without-clustered-indexes)이 된다. MS 의 힙 문서가 경고하는 내용을 요약하면:

- 데이터가 정렬 없이 쌓이고, 행 이동 시 **forwarding pointer** 가 생겨 스캔이 점점 비싸진다
- 공간 회수·조각화 관리가 클러스터드 테이블보다 손이 간다
- 힙이 합리적인 경우는 대량 적재 스테이징처럼 좁은 용도다

그러니 "PK 없이" 가 "클러스터드 없이" 가 되지 않게 하라. UNIQUE 인덱스를 아예 클러스터드로 만드는 것도 방법이다:

```sql
CREATE UNIQUE CLUSTERED INDEX UX_Employee_EmpNo
ON dbo.Employee(EmpNo);  -- PK 없이도 물리 구조는 잡힌다
```

([CREATE INDEX 공식 구문](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql) — `UNIQUE` 와 `CLUSTERED` 는 자유롭게 조합된다.)

## 4. 잃는 것 ② — PK 를 요구하는 기능들

PK 는 사람만 보는 게 아니라 도구들이 본다. 대표적으로 [트랜잭션 복제는 "게시되는 테이블에 PK 가 반드시 있어야 한다"](https://learn.microsoft.com/en-us/sql/relational-databases/replication/publish/publish-data-and-database-objects) 고 공식 문서에 못박혀 있다. 그 외에도 ORM(JPA/EF)의 엔티티 매핑, 일부 BI·CDC·동기화 도구가 "PK 또는 그에 준하는 유일키" 를 요구하거나, 없으면 성능이 나쁜 경로로 우회한다. **지금 안 쓰더라도 미래의 복제·마이그레이션 옵션을 하나 닫는 결정**이라는 점은 계산에 넣어야 한다.

## 5. 정리 — 이 구성이 맞는 경우, 아닌 경우

**맞는 경우**
- 유일해야 할 컬럼이 NULL 을 (여러 개) 가질 수 있다 → 필터드 UNIQUE 인덱스가 유일한 정공법
- 유일키가 여러 개고 어느 것도 "대표" 라 부르기 애매하다 (UNIQUE 는 여러 개 걸 수 있다)
- 스테이징·적재 전용 테이블처럼 PK 의 의미가 없는 곳

**아닌 경우 (그냥 PK 를 두라)**
- FK 로 참조당하는 부모 테이블 — 특히 필터드 인덱스는 참조 대상이 못 된다
- 복제·CDC·ORM 등 PK 를 기대하는 도구가 로드맵에 있다
- "PK 정하기 귀찮아서" — 이건 설계가 아니라 미룸이다

실무 절충안은 대개 이렇다: **대리키(IDENTITY/시퀀스)를 PK 로 두고, 업무 규칙은 UNIQUE(필터드 포함) 인덱스로 별도 강제.** PK 가 주는 것(클러스터드 기본, 도구 호환, FK 앵커)과 UNIQUE 인덱스가 주는 것(NULL 유연성, 복수 규칙)을 둘 다 갖는 구성이고, 이 글에서 본 함정을 전부 피해 간다.

## References

- Microsoft Learn — [Unique constraints and check constraints](https://learn.microsoft.com/en-us/sql/relational-databases/tables/unique-constraints-and-check-constraints)
- Microsoft Learn — [Primary and foreign key constraints](https://learn.microsoft.com/en-us/sql/relational-databases/tables/primary-and-foreign-key-constraints)
- Microsoft Learn — [Create unique indexes](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/create-unique-indexes) · [Create filtered indexes](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/create-filtered-indexes) · [CREATE INDEX (T-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql)
- Microsoft Learn — [Heaps (tables without clustered indexes)](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/heaps-tables-without-clustered-indexes)
- Microsoft Learn — [Publish data and database objects (트랜잭션 복제의 PK 요구)](https://learn.microsoft.com/en-us/sql/relational-databases/replication/publish/publish-data-and-database-objects)
