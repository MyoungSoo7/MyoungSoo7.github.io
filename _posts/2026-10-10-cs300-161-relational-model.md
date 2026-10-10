---
layout: post
title: "[CS300 #161] 관계형 모델 — 표 하나로 세상을 적는 법"
date: 2026-10-10 20:41:00 +0900
categories: [cs]
tags: [cs300, database, relational-model, relational-algebra, integrity-constraints]
---

컴퓨터공학 300 주제 시리즈의 161번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

관계형 모델은 데이터를 "이름 붙은 열을 가진 튜플들의 집합"인 릴레이션으로 표현하고, 질의는 그 집합 위의 연산(선택·투영·조인 등)으로 정의하는 데이터 모델이다.

## 왜 필요한가

1960년대의 데이터베이스는 계층형·네트워크형이었다. 레코드끼리 포인터로 이어져 있었고, 프로그램은 그 포인터를 따라가며 데이터를 찾았다. 문제는 저장 구조가 바뀌면 프로그램도 같이 바뀌어야 한다는 점이었다. 경로를 하나 추가하거나 레코드 순서를 바꾸면 그 경로를 아는 모든 코드를 고쳐야 했다.

E. F. Codd 는 1970년 논문 "A Relational Model of Data for Large Shared Data Banks" 에서 이 의존성을 끊자고 제안했다. 사용자는 데이터가 "무엇인지"만 기술하고, "어떻게 찾을지"는 시스템이 정한다. 이 분리를 **데이터 독립성**이라 부른다. 오늘날 PostgreSQL, MySQL, SQLite, Oracle 이 모두 이 모델 위에 서 있다. 인덱스를 추가해도 SQL 을 고칠 필요가 없는 이유가 여기 있다.

관계형 모델을 이해하면 SQL 이 왜 그런 모양인지, 왜 NULL 이 골칫거리인지, 왜 기본 키가 필요한지가 한 줄로 설명된다.

## 핵심 개념

### 용어 정리

| 이론 용어 | 실무 용어 | 뜻 |
|---|---|---|
| 릴레이션 (relation) | 테이블 | 같은 스키마를 가진 튜플의 집합 |
| 튜플 (tuple) | 행 (row) | 속성 값의 묶음 하나 |
| 속성 (attribute) | 열 (column) | 이름과 도메인을 가진 칸 |
| 도메인 (domain) | 타입 | 속성이 가질 수 있는 값의 집합 |
| 차수 (degree) | 열 개수 | 속성의 수 |
| 카디널리티 (cardinality) | 행 개수 | 튜플의 수 |

릴레이션 스키마는 `EMP(emp_id, name, dept_id, salary)` 처럼 이름과 속성 목록으로 적는다. 스키마는 거의 바뀌지 않는 틀이고, 그 틀에 담긴 튜플들의 현재 모습을 **인스턴스**라 한다.

### 집합이라는 성질

릴레이션은 수학적 집합이다. 여기서 두 가지 성질이 나온다.

1. **튜플 사이에 순서가 없다.** 1행, 2행이라는 개념이 모델에는 없다. SQL 에서 `ORDER BY` 없이 나온 결과 순서를 믿으면 안 되는 이유다.
2. **중복 튜플이 없다.** 모든 튜플은 서로 구별된다. 그래서 각 튜플을 유일하게 식별하는 속성 집합, 즉 **키**가 항상 존재한다(최악의 경우 모든 속성 전체).

실제 SQL 은 이 점에서 모델과 다르다. SQL 테이블은 중복 행을 허용하는 **멀티셋(bag)** 이다. `SELECT DISTINCT` 가 따로 있는 이유가 그것이다. 이론과 구현의 이 차이를 알고 있으면, 기본 키 없는 테이블이 왜 위험한지 바로 보인다.

또 하나, 각 속성 값은 **원자값**이어야 한다는 것이 고전적 정의다. 한 칸에 전화번호 목록을 넣지 않는다. 이것이 다음 주제들인 정규화의 출발점이 된다.

### 키의 종류

```
슈퍼키  : 튜플을 유일하게 식별하는 속성 집합 (군더더기가 있어도 됨)
후보키  : 더 줄이면 유일성이 깨지는 최소 슈퍼키
기본 키 : 후보키 중 대표로 고른 하나 (NULL 불가)
대체키  : 기본 키로 뽑히지 않은 나머지 후보키
외래 키 : 다른 릴레이션의 키를 참조하는 속성
```

예를 들어 `EMP` 에서 `{emp_id}` 는 후보키이고 `{emp_id, name}` 은 슈퍼키지만 후보키는 아니다. 주민번호 같은 속성이 있다면 그것도 후보키가 되어 대체키로 남는다.

### 무결성 제약

모델은 데이터가 지켜야 할 규칙을 스키마에 선언하게 한다.

- **개체 무결성**: 기본 키는 NULL 이 될 수 없다.
- **참조 무결성**: 외래 키 값은 참조 대상에 실제로 있거나 NULL 이어야 한다.
- **도메인 제약**: 속성 값은 정해진 도메인 안에 있어야 한다. SQL 에서는 타입과 `CHECK` 로 표현한다.

이 규칙을 애플리케이션 코드가 아니라 DB 가 강제하는 것이 핵심이다. 코드는 여러 개이고 버그가 있지만, 제약은 한 곳에서 모든 쓰기를 막는다.

### 관계 대수

Codd 는 릴레이션을 입력받아 릴레이션을 내놓는 연산 집합을 정의했다. 결과가 다시 릴레이션이므로 연산을 얼마든지 이어 붙일 수 있다(닫힘 성질).

| 연산 | 기호 | SQL 대응 | 설명 |
|---|---|---|---|
| 선택 | σ | `WHERE` | 조건을 만족하는 튜플만 |
| 투영 | π | `SELECT 열목록` | 일부 속성만 |
| 합집합 | ∪ | `UNION` | 스키마가 같은 두 릴레이션 |
| 차집합 | − | `EXCEPT` | |
| 카티션 곱 | × | `CROSS JOIN` | 모든 조합 |
| 이름 바꾸기 | ρ | `AS` | |
| 조인 | ⋈ | `JOIN ... ON` | 곱 + 선택의 축약 |

"연봉 5000 이상인 직원 이름"은 `π_name(σ_salary≥5000(EMP))` 이다. SQL 옵티마이저는 사실상 SQL 을 이런 대수식 트리로 바꾼 뒤, 같은 결과를 내는 더 싼 트리를 찾는다. 예를 들어 조인 전에 선택을 먼저 하는 "선택 밀어내리기"가 대표적인 변환이다.

```
     π name                        π name
       |                             |
     σ salary>=5000      ==>        ⋈
       |                           /   \
       ⋈                 σ salary>=5000  DEPT
      / \                      |
   EMP   DEPT                 EMP
```

### NULL 과 3값 논리

SQL 은 값이 없음을 `NULL` 로 표현하고, 비교 결과로 참·거짓 외에 UNKNOWN 을 둔다. `NULL = NULL` 은 참이 아니라 UNKNOWN 이고, `WHERE` 는 참인 행만 통과시킨다. 그래서 `WHERE x = NULL` 은 아무 행도 돌려주지 않는다. `IS NULL` 을 써야 한다. NULL 은 Codd 의 모델에서도 오래 논쟁거리였고, 실무에서도 집계와 조인 결과를 뒤틀리게 만드는 단골 원인이다.

## 직접 해 보기

파이썬 표준 라이브러리의 `sqlite3` 만으로 릴레이션, 키, 제약, 관계 연산을 확인할 수 있다. SQLite 는 외래 키 검사가 기본으로 꺼져 있으므로 연결마다 `PRAGMA foreign_keys = ON` 을 켠다.

```python
import sqlite3
con = sqlite3.connect(":memory:")
con.execute("PRAGMA foreign_keys = ON")
con.executescript("""
CREATE TABLE dept (
  dept_id INTEGER PRIMARY KEY,
  name    TEXT NOT NULL UNIQUE
);
CREATE TABLE emp (
  emp_id  INTEGER PRIMARY KEY,
  name    TEXT NOT NULL,
  dept_id INTEGER NOT NULL REFERENCES dept(dept_id),
  salary  INTEGER CHECK (salary > 0)
);
INSERT INTO dept VALUES (1, '개발'), (2, '영업');
INSERT INTO emp VALUES (10, '김', 1, 5000), (11, '이', 1, 6000), (12, '박', 2, 4500);
""")
# 선택(σ)과 투영(π)
print(con.execute("SELECT name FROM emp WHERE salary >= 5000").fetchall())
# 조인(⋈)
print(con.execute("""SELECT e.name, d.name FROM emp e JOIN dept d
                     ON e.dept_id = d.dept_id ORDER BY e.emp_id""").fetchall())
# 무결성 위반 세 가지
for sql in ["INSERT INTO emp VALUES (10, '최', 1, 3000)",
            "INSERT INTO emp VALUES (13, '최', 9, 3000)",
            "INSERT INTO emp VALUES (14, '정', 2, -1)"]:
    try:
        con.execute(sql)
    except sqlite3.IntegrityError as e:
        print("거부:", e)
```

출력은 다음과 같다(Python 3.12, SQLite 3.45 에서 확인).

```
[('김',), ('이',)]
[('김', '개발'), ('이', '개발'), ('박', '영업')]
거부: UNIQUE constraint failed: emp.emp_id
거부: FOREIGN KEY constraint failed
거부: CHECK constraint failed: salary > 0
```

세 줄의 "거부"가 각각 개체 무결성(키 중복), 참조 무결성(없는 부서), 도메인 제약(음수 연봉)이다. 애플리케이션이 어떤 경로로 쓰든 DB 가 막는다.

## 현업에서는

- **제약을 DB 에 둘지 코드에 둘지**는 늘 나오는 논쟁이다. 대량 트래픽 서비스에서 외래 키를 끄는 팀도 있지만, 그러면 고아 행(참조 대상이 사라진 행)을 찾는 배치를 따로 돌리게 된다. 작은 서비스라면 제약을 DB 에 두는 편이 거의 항상 싸다.
- **ORM 은 관계형 모델 위의 번역기**다. JPA 엔티티의 `@Id`, `@ManyToOne` 은 기본 키와 외래 키의 다른 이름일 뿐이다. 모델을 모르면 N+1 쿼리처럼 ORM 이 만들어 내는 비효율을 알아보기 어렵다.
- **순서 의존 버그**: `ORDER BY` 없는 쿼리가 개발 환경에선 늘 같은 순서로 나오다가, 운영에서 병렬 스캔이나 다른 실행 계획이 걸리면서 순서가 바뀌는 일이 있다. 릴레이션은 순서가 없는 집합이라는 정의를 떠올리면 원인이 바로 보인다.
- 홈랩 k3s 클러스터에서 PostgreSQL 을 파드로 띄워 여러 서비스가 함께 쓰는 경우에도, 스키마와 제약을 DB 쪽에 선언해 두면 서비스가 늘어나도 데이터 규칙은 한 군데서 관리된다.

## 확인 문제

1. 릴레이션이 집합이라는 정의에서 나오는 두 가지 성질을 말하라. SQL 테이블은 이 중 어느 것을 지키지 않는가?
2. `STUDENT(학번, 주민번호, 이름)` 에서 학번과 주민번호가 각각 유일하다. 후보키, 기본 키, 대체키, 슈퍼키의 예를 하나씩 들어라.
3. `σ_dept_id=1(EMP ⋈ DEPT)` 와 `σ_dept_id=1(EMP) ⋈ DEPT` 가 같은 결과를 내는 이유와, 옵티마이저가 뒤쪽을 선호하는 이유를 설명하라.
4. `SELECT * FROM emp WHERE manager_id = NULL` 이 행을 돌려주지 않는 이유는 무엇인가?

### 풀이

1. 튜플 간 순서가 없고, 중복 튜플이 없다. SQL 테이블은 중복 행을 허용하는 멀티셋이라 두 번째 성질을 지키지 않는다(키를 선언해야 보장된다).
2. 후보키: `{학번}`, `{주민번호}`. 기본 키: 둘 중 고른 `{학번}`. 대체키: `{주민번호}`. 슈퍼키: `{학번, 이름}` 등 후보키를 포함하는 모든 집합.
3. 선택 조건이 `EMP` 의 속성에만 걸리므로 조인 전후 어디서 걸러도 결과가 같다. 먼저 거르면 조인에 들어가는 튜플 수가 줄어 비용이 낮아진다.
4. `NULL` 과의 비교는 UNKNOWN 이고 `WHERE` 는 참인 행만 통과시킨다. `IS NULL` 을 써야 한다.

## 더 읽을거리 (References)

- E. F. Codd, "A Relational Model of Data for Large Shared Data Banks", *Communications of the ACM*, 13(6), 1970. 원문 PDF: [seas.upenn.edu 사본](https://www.seas.upenn.edu/~zives/03f/cis550/codd.pdf)
- PostgreSQL 공식 문서, [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- SQLite 공식 문서, [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html)
- Abraham Silberschatz, Henry F. Korth, S. Sudarshan, *Database System Concepts*, 7th ed., McGraw-Hill, 2019. 2장 "Introduction to the Relational Model"
