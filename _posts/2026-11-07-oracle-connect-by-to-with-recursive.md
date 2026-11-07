---
layout: post
title: "계층형 쿼리 다시 보기 — Oracle CONNECT BY 에서 표준 WITH RECURSIVE 까지"
date: 2026-11-07 21:54:22 +0900
categories: [database, sql]
tags: [oracle, connect-by, hierarchical-query, recursive-cte, postgresql, sqlite]
---

부서 조직도, 메뉴 트리, 댓글 대댓글, 부품 BOM 은 모두 한 테이블 안에 "내 부모가 누구인가" 컬럼을 두는 **인접 리스트(adjacency list)** 모델이다. 이걸 트리 순서로 펼쳐 읽는 게 계층형 쿼리다.

이 글은 리신 님의 [「[ Oracle SQL ] 계층형쿼리 (Hierarchy Query)」](https://dev-cini.tistory.com/m/47)(2022-06-07) 를 출발점으로 삼는다. 그 글의 부서 예제(`TB_DEPT`) 를 그대로 가져와서, 원문이 다루지 않은 세 가지를 덧붙인다.

1. Oracle 이 `CONNECT BY` 를 **어떤 순서로** 처리하는지, 그래서 `WHERE` 가 왜 가지를 자르지 못하는지
2. 원문 이후의 의사컬럼(`CONNECT_BY_ISLEAF`, `CONNECT_BY_ROOT`, `NOCYCLE`/`CONNECT_BY_ISCYCLE`)
3. 같은 쿼리를 SQL 표준 **재귀 CTE(`WITH RECURSIVE`)** 로 옮기는 법 — PostgreSQL·SQLite 에서도 돌아가게

> **검증 범위.** 재귀 CTE 쿼리는 전부 SQLite 3.51.0 에서 실제로 돌려 결과를 붙였다. Oracle 전용 문법(`CONNECT BY`, 의사컬럼)과 PostgreSQL 전용 문법(`SEARCH`/`CYCLE` 절)은 이번에 실행 환경이 없어 **돌려보지 않았고**, 동작 설명은 각 벤더 공식 문서를 근거로 했다.

## 1. 예제 테이블 (원문 그대로)

```sql
CREATE TABLE TB_DEPT (
   DEPT_CD     VARCHAR2(8) NOT NULL PRIMARY KEY,
   PAR_DEPT_CD VARCHAR2(8),
   DEPT_NM     VARCHAR2(50)
);
-- 회사(DE_001) ─┬ 개발부문(DE_002) ─┬ 개발부(DE_004)
--               │                  └ 부설연구소(DE_005)
--               └ 영업부문(DE_003) ─┬ 해외영업부(DE_006)
--                                  ├ 국내영업부(DE_007)
--                                  └ 영업기획팀(DE_008)
```

원문의 핵심 쿼리는 이것이다.

```sql
SELECT LEVEL LEV, DEPT_CD, DEPT_NM, PAR_DEPT_CD
  FROM TB_DEPT
 START WITH PAR_DEPT_CD IS NULL
CONNECT BY PAR_DEPT_CD = PRIOR DEPT_CD
 ORDER SIBLINGS BY DEPT_CD;
```

## 2. `PRIOR` 는 "부모 행 쪽"에 붙는다

원문은 방향을 "순방향: 상위 = PRIOR 하위" 로 외우게 하는데, 컬럼 이름과 섞이면 헷갈리기 쉽다. Oracle 문서의 정의가 더 단순하다. **`PRIOR` 는 바로 뒤의 식을 _부모 행_ 의 값으로 평가하는 단항 연산자**이고, 등호 어느 쪽에 붙여도 된다 ([Oracle, Hierarchical Queries](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Hierarchical-Queries.html)).

- `PAR_DEPT_CD = PRIOR DEPT_CD` → "자식의 상위코드 = **부모의** 부서코드" → 위에서 아래로(순방향)
- `DEPT_CD = PRIOR PAR_DEPT_CD` → "다음 행의 부서코드 = **이전 행의** 상위코드" → 아래에서 위로(역방향)

즉 외울 건 "어느 컬럼이 상위냐" 가 아니라 "**방금 읽은 행의 무엇을 다음 행과 맞출 것이냐**" 다.

## 3. 처리 순서 — `WHERE` 는 가지를 자르지 않는다

Oracle 문서는 계층 쿼리의 평가 순서를 이렇게 적는다 ([Oracle, Hierarchical Queries](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Hierarchical-Queries.html)).

1. 조인이 있으면 먼저 평가
2. `CONNECT BY` 조건 평가
3. 남은 `WHERE` 조건 평가

그리고 4단계 설명에 결정적인 문장이 있다. `WHERE` 조건은 **행마다 개별로** 평가하며, *조건을 통과하지 못한 행의 자식들까지 지우지는 않는다.*

그래서 "개발부문을 빼고 보여줘" 를 `WHERE DEPT_NM <> '개발부문'` 으로 쓰면 개발부문 **한 줄만** 사라지고, 그 밑의 개발부·부설연구소는 부모 없이 떠 있는 채로 남는다. 가지째 잘라내려면 조건을 `CONNECT BY` 쪽에 넣어야 한다.

```sql
-- 행 하나만 빠짐
... WHERE DEPT_NM <> '개발부문' START WITH ... CONNECT BY PAR_DEPT_CD = PRIOR DEPT_CD
-- 가지째 빠짐
... START WITH ... CONNECT BY PAR_DEPT_CD = PRIOR DEPT_CD AND DEPT_NM <> '개발부문'
```

재귀 CTE 로 옮기면 이 차이가 "바깥 `WHERE`" 냐 "재귀항 `WHERE`" 냐로 그대로 나타난다. SQLite 실측 결과다(쿼리는 5절).

| 위치 | 결과 |
| --- | --- |
| 바깥 `WHERE` (행 필터) | 회사 / 영업부문 / **개발부 / 부설연구소** / 해외영업부 / 국내영업부 / 영업기획팀 |
| 재귀항 `WHERE` (가지 필터) | 회사 / 영업부문 / 해외영업부 / 국내영업부 / 영업기획팀 |

같은 이유로 Oracle 문서는 계층 쿼리에 일반 `ORDER BY` 나 `GROUP BY` 를 쓰지 말라고 한다. 계층 순서를 덮어쓰기 때문이다. 형제끼리만 정렬하려면 원문 설명대로 `ORDER SIBLINGS BY` 를 쓴다.

## 4. 원문 이후의 의사컬럼 세 가지

모두 [Oracle, Hierarchical Query Pseudocolumns](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Hierarchical-Query-Pseudocolumns.html) 와 [Hierarchical Queries](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Hierarchical-Queries.html) 의 정의다.

- **`CONNECT_BY_ISLEAF`** — 현재 행이 `CONNECT BY` 로 정의된 트리의 잎(자식 없음)이면 1. "더 펼칠 게 있는가" 를 화면에 ▸ 아이콘으로 표시할 때 쓴다.
- **`CONNECT_BY_ROOT 컬럼`** — 그 행이 속한 트리의 **루트 행** 값을 돌려주는 연산자. `START WITH` 없이 돌리면 모든 행이 각자 루트가 되므로 "이 직원 위의 모든 상사" 처럼 조상-자손 쌍을 전부 뽑을 수 있다.
- **`NOCYCLE` + `CONNECT_BY_ISCYCLE`** — 데이터에 순환(A 의 조상이 다시 A)이 있으면 Oracle 은 `ORA-01436: CONNECT BY loop in user data` 로 실패한다. `CONNECT BY NOCYCLE` 을 쓰면 순환을 만나도 결과를 돌려주고, `CONNECT_BY_ISCYCLE` 이 **"자식 중 하나가 자기 조상인 행"** 에 1 을 찍는다. 이 의사컬럼은 `NOCYCLE` 을 지정했을 때만 쓸 수 있다.

원문 5절의 `SYS_CONNECT_BY_PATH` 와 합치면 조직도 화면에 필요한 정보(깊이·경로·루트·잎 여부)가 쿼리 하나로 나온다.

```sql
SELECT LEVEL,
       LPAD(' ', 2*(LEVEL-1)) || DEPT_NM        AS TREE,
       SYS_CONNECT_BY_PATH(DEPT_NM, '/')         AS PATH,
       CONNECT_BY_ROOT DEPT_NM                   AS ROOT_NM,
       CONNECT_BY_ISLEAF                         AS IS_LEAF
  FROM TB_DEPT
 START WITH PAR_DEPT_CD IS NULL
CONNECT BY PAR_DEPT_CD = PRIOR DEPT_CD
 ORDER SIBLINGS BY DEPT_CD;
```

## 5. 표준으로 옮기기 — `WITH RECURSIVE`

`CONNECT BY` 는 Oracle 고유 문법이다. PostgreSQL·SQLite·MySQL 8 같은 DB 에서는 재귀 공통 테이블 식(CTE)을 쓴다. 구조는 항상 같다 ([PostgreSQL 7.8.2](https://www.postgresql.org/docs/current/queries-with.html#QUERIES-WITH-RECURSIVE), [SQLite, The WITH Clause](https://www.sqlite.org/lang_with.html)).

- **비재귀항** = `START WITH` 에 해당. 루트 행을 고른다.
- `UNION ALL`
- **재귀항** = `CONNECT BY` 에 해당. 직전 단계 결과(작업 테이블)와 원본 테이블을 조인해 다음 세대를 만든다.
- 작업 테이블이 빌 때까지 반복한다. PostgreSQL 문서 표현으로 "재귀라고 쓰지만 내부적으로는 **반복**으로 평가" 된다.

의사컬럼은 없으니 **직접 컬럼으로 들고 다닌다.** 대응표는 이렇다.

| Oracle | 재귀 CTE 에서 |
| --- | --- |
| `LEVEL` | 비재귀항 `1`, 재귀항 `부모.lev + 1` |
| `SYS_CONNECT_BY_PATH` | 비재귀항은 `'/이름'`, 재귀항은 부모의 path 뒤에 `'/이름'` 을 이어 붙임 |
| `CONNECT_BY_ROOT` | 비재귀항에서 정한 값을 재귀항이 그대로 복사 |
| `CONNECT_BY_ISLEAF` | 바깥에서 `NOT EXISTS (자식)` |
| `ORDER SIBLINGS BY` | 정렬 키 경로를 들고 다니다 마지막에 `ORDER BY` |
| `NOCYCLE` | 방문 경로에 이미 있으면 재귀 중단 |

SQLite 에서 실제로 돌린 쿼리와 결과다.

```sql
WITH RECURSIVE h(lev, dept_cd, dept_nm, par_dept_cd, path, sort_key, root_nm) AS (
  SELECT 1, dept_cd, dept_nm, par_dept_cd, '/'||dept_nm, dept_cd, dept_nm
    FROM TB_DEPT WHERE par_dept_cd IS NULL                       -- START WITH
  UNION ALL
  SELECT h.lev+1, c.dept_cd, c.dept_nm, c.par_dept_cd,
         h.path||'/'||c.dept_nm, h.sort_key||'>'||c.dept_cd, h.root_nm
    FROM TB_DEPT c JOIN h ON c.par_dept_cd = h.dept_cd           -- CONNECT BY
)
SELECT lev, substr('          ',1,2*(lev-1))||dept_nm AS tree, path, root_nm,
       CASE WHEN EXISTS (SELECT 1 FROM TB_DEPT x WHERE x.par_dept_cd = h.dept_cd)
            THEN 0 ELSE 1 END AS is_leaf
  FROM h
 ORDER BY sort_key;                                              -- ORDER SIBLINGS BY
```

```text
lev|tree        |path                     |root_nm|is_leaf
1  |회사         |/회사                     |회사    |0
2  |  개발부문    |/회사/개발부문             |회사    |0
3  |    개발부    |/회사/개발부문/개발부       |회사    |1
3  |    부설연구소 |/회사/개발부문/부설연구소   |회사    |1
2  |  영업부문    |/회사/영업부문             |회사    |0
3  |    해외영업부 |/회사/영업부문/해외영업부   |회사    |1
3  |    국내영업부 |/회사/영업부문/국내영업부   |회사    |1
3  |    영업기획팀 |/회사/영업부문/영업기획팀   |회사    |1
```

원문 5절의 Oracle 결과와 같은 모양이다.

**정렬 키 주의.** 여기서는 경로를 문자열로 이어 붙여 정렬했다. `DE_001` 처럼 코드 길이가 고정이라 성립하는 것이다. 코드가 `9`, `10` 처럼 가변 길이면 문자열 비교에서 `10` 이 `9` 보다 앞에 와서 형제 순서가 틀어진다. PostgreSQL 이라면 문서 예제처럼 **배열**(`ARRAY[dept_cd]`, `path || dept_cd`)로 들고 다니면 요소 단위로 비교되어 이 문제가 없다 ([PostgreSQL 7.8.2.1](https://www.postgresql.org/docs/current/queries-with.html#QUERIES-WITH-SEARCH)).

**역방향**도 조인 방향만 뒤집으면 된다. 국내영업부에서 위로 올라간 SQLite 결과는 `1 국내영업부 → 2 영업부문 → 3 회사` 였다.

```sql
WITH RECURSIVE up(lev, dept_cd, dept_nm, par_dept_cd) AS (
  SELECT 1, dept_cd, dept_nm, par_dept_cd FROM TB_DEPT WHERE dept_cd = 'DE_007'
  UNION ALL
  SELECT up.lev+1, p.dept_cd, p.dept_nm, p.par_dept_cd
    FROM TB_DEPT p JOIN up ON p.dept_cd = up.par_dept_cd
)
SELECT lev, dept_nm FROM up;
```

## 6. 순환 데이터 — 무한 루프는 CTE 가 더 위험하다

Oracle 은 순환을 만나면 최소한 `ORA-01436` 으로 **멈춘다.** 재귀 CTE 는 다르다. PostgreSQL 문서는 재귀항이 결국 빈 결과를 내도록 보장하지 않으면 "쿼리가 무한히 돈다" 고 경고한다 ([PostgreSQL 7.8.2.2](https://www.postgresql.org/docs/current/queries-with.html#QUERIES-WITH-CYCLE)). `UNION` 으로 중복 행을 버리는 방법도 있지만, `lev` 처럼 매 단계 바뀌는 컬럼이 있으면 행이 완전히 같아지지 않아 소용이 없다.

표준적인 해법은 방문한 키를 경로로 들고 다니다가 이미 있으면 멈추는 것이다. 회사(DE_001)의 상위를 일부러 영업기획팀(DE_008)으로 바꿔 순환을 만든 뒤 SQLite 에서 돌렸다.

```sql
UPDATE TB_DEPT SET par_dept_cd = 'DE_008' WHERE dept_cd = 'DE_001';

WITH RECURSIVE h(lev, dept_cd, dept_nm, path, is_cycle) AS (
  SELECT 1, dept_cd, dept_nm, '/'||dept_cd||'/', 0 FROM TB_DEPT WHERE dept_cd = 'DE_001'
  UNION ALL
  SELECT h.lev+1, c.dept_cd, c.dept_nm, h.path||c.dept_cd||'/',
         instr(h.path, '/'||c.dept_cd||'/') > 0
    FROM TB_DEPT c JOIN h ON c.par_dept_cd = h.dept_cd
   WHERE h.is_cycle = 0
)
SELECT lev, dept_nm, is_cycle, path FROM h ORDER BY path;
```

```text
lev|dept_nm  |is_cycle|path
1  |회사      |0       |/DE_001/
2  |개발부문  |0       |/DE_001/DE_002/
3  |개발부    |0       |/DE_001/DE_002/DE_004/
3  |부설연구소 |0       |/DE_001/DE_002/DE_005/
2  |영업부문  |0       |/DE_001/DE_003/
3  |해외영업부 |0       |/DE_001/DE_003/DE_006/
3  |국내영업부 |0       |/DE_001/DE_003/DE_007/
3  |영업기획팀 |0       |/DE_001/DE_003/DE_008/
4  |회사      |1       |/DE_001/DE_003/DE_008/DE_001/
```

여기서 **Oracle 과 의미가 한 칸 어긋난다**는 점을 짚어 둔다.

- Oracle `CONNECT_BY_ISCYCLE` 은 "자식 중 하나가 자기 조상인 행", 즉 순환을 **일으키는 쪽**(위 예에서는 영업기획팀)에 1 을 찍는다(문서 정의).
- 위 CTE 는 순환으로 **다시 도착한 행**(4레벨 '회사')을 한 줄 더 내보내고 거기에 1 을 찍는다. PostgreSQL 문서의 `is_cycle` 패턴과 같은 방식이다.

Oracle 쿼리를 CTE 로 옮기면서 "순환 행 = 1" 을 그대로 화면 로직에 연결하면 표시 위치가 한 줄 밀린다. Oracle 과 맞추려면 마지막에 `WHERE is_cycle = 0` 으로 재도착 행을 버리고, 그 부모 행에 표시를 옮겨야 한다.

PostgreSQL 14 부터는 이 손작업을 표준 `SEARCH`·`CYCLE` 절이 대신한다 ([PostgreSQL 14 릴리스 노트](https://www.postgresql.org/docs/release/14.0/)). 아래는 문서 문법을 이 예제에 적용한 형태다. **PostgreSQL 에서는 실행해 보지 않았다.**

```sql
WITH RECURSIVE h(lev, dept_cd, dept_nm, par_dept_cd) AS (
  SELECT 1, dept_cd, dept_nm, par_dept_cd FROM tb_dept WHERE par_dept_cd IS NULL
  UNION ALL
  SELECT h.lev+1, c.dept_cd, c.dept_nm, c.par_dept_cd
    FROM tb_dept c JOIN h ON c.par_dept_cd = h.dept_cd
) SEARCH DEPTH FIRST BY dept_cd SET ord      -- ORDER SIBLINGS BY 대응
  CYCLE dept_cd SET is_cycle USING path      -- NOCYCLE 대응
SELECT lev, dept_nm, is_cycle FROM h ORDER BY ord;
```

## 7. 정리

| 하고 싶은 것 | Oracle | 표준 재귀 CTE |
| --- | --- | --- |
| 루트 지정 | `START WITH` | 비재귀항 `WHERE` |
| 부모-자식 연결 | `CONNECT BY ... PRIOR ...` | 재귀항 `JOIN` |
| 가지째 제외 | `CONNECT BY` 조건에 추가 | 재귀항 `WHERE` |
| 행만 제외 | `WHERE` | 바깥 `WHERE` |
| 형제 정렬 | `ORDER SIBLINGS BY` | 경로 키(가능하면 배열) `ORDER BY` / PG14+ `SEARCH` |
| 순환 처리 | `NOCYCLE` (기본은 에러로 멈춤) | 경로 검사 필수 (기본은 무한 루프) / PG14+ `CYCLE` |

원문은 `START WITH`·`CONNECT BY`·`ORDER SIBLINGS BY`·`SYS_CONNECT_BY_PATH` 네 가지로 계층 쿼리의 뼈대를 깔끔하게 보여준다. 실무에서 사고가 나는 지점은 그 바깥, 즉 **`WHERE` 의 위치**와 **순환 데이터**다. 그리고 다른 DB 로 옮길 때는 "에러로 멈추던 것이 무한 루프가 된다" 는 기본 동작의 차이를 먼저 막아 두는 편이 안전하다.

## References

- 리신, 「[ Oracle SQL ] 계층형쿼리 (Hierarchy Query)」, 2022-06-07 — <https://dev-cini.tistory.com/m/47> (예제 테이블·기본 쿼리 출처)
- Oracle, *SQL Language Reference 23ai* — Hierarchical Queries. <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Hierarchical-Queries.html>
- Oracle, *SQL Language Reference 19c* — Hierarchical Query Pseudocolumns. <https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Hierarchical-Query-Pseudocolumns.html>
- PostgreSQL Global Development Group, *Documentation* §7.8 WITH Queries (Common Table Expressions). <https://www.postgresql.org/docs/current/queries-with.html>
- PostgreSQL Global Development Group, *Release 14 Release Notes* (SEARCH·CYCLE 도입). <https://www.postgresql.org/docs/release/14.0/>
- SQLite, *The WITH Clause*. <https://www.sqlite.org/lang_with.html>
