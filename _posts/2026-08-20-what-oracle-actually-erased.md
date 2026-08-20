---
layout: post
title: "Oracle 은 IMS 와 CODASYL 의 무엇을 지웠고, 무엇을 남겼나"
date: 2026-08-20 14:20:00 +0900
categories: [engineering, database]
tags: [oracle, rdbms, sql, codd, ims, codasyl, history]
---

Oracle 이 관계형 데이터베이스를 **발명했다** 고 오해하는 사람이 많다. 아니다. Oracle 은 관계형을 **팔았다.** 이 구분이 무슨 차이를 만드는지, 그리고 Oracle 이 등장하기 전의 데이터베이스가 실제로 어떻게 생겼었는지를 짚는다.

먼저 사실. Larry Ellison, Bob Miner, Ed Oates 는 **1977년** Software Development Laboratories(SDL) 라는 이름으로 회사를 세웠다. **Oracle v2** 는 **1979년** 에 나왔고, "SQL 을 쓴 가장 초기 상용 데이터베이스 중 하나" 로 기록된다.[^wiki-oracle] 이 15줄짜리 사실 안에 두 개의 함정이 있다.

- **v1 이 아니라 v2 로 시작한다.** Ellison 은 "1.0 이라는 이름을 붙이면 아무도 안 산다" 는 마케팅 판단으로 첫 상용판을 2.0 이라 붙였다.[^wiki-oracle]
- **Oracle 이 최초의 상용 관계형 DB 도 아니다.** Multics Relational Data Store 가 **1976년 6월** 에 먼저 나와 있었다.[^wiki-rdb] Oracle 이 세운 기록은 "최초" 가 아니라 "**가장 오래 팔린**" 이다.

이 글은 그 15년(1970~1985)에 무슨 일이 있었고, Oracle 이 실제로 시장에서 지운 것과 남긴 것을 나눠서 본다.

---

## 1. Oracle 이전 — 데이터베이스는 프로그램 안에 있었다

1970년대 초 상용 데이터베이스 시장을 지배하던 두 모델은 이렇다.

### 1-1. 계층형(hierarchical) — IBM IMS

IBM 이 1966년 아폴로 프로그램용으로 만들기 시작한 **IMS**(Information Management System) 는 데이터를 **트리** 로 조직한다. 부품이 조립품에 속하고, 조립품이 로켓에 속한다 — 부모-자식 1:N 관계로만 표현된다.

문제는 현실이 트리가 아니라는 것이다.

- **부품 하나가 두 조립품에 쓰이면?** 데이터를 복제해야 한다. 부품 스펙이 바뀌면 두 곳을 동기화해야 한다.
- **"이 부품이 들어간 조립품 전부" 를 찾으려면?** 트리를 뒤집는 API 가 따로 없어서 애플리케이션 코드가 트리 전체를 스캔한다.

### 1-2. 네트워크(network) — CODASYL / IDMS

**CODASYL** 표준(1969) 을 따르는 **IDMS**, IDS 같은 시스템은 계층형의 트리 제약을 완화해 **다대다** 를 허용했다. 대신 데이터 간 관계가 **포인터** 로 표현됐다.

이게 무슨 뜻이냐 — 프로그래머가 데이터베이스에서 뭔가를 꺼내려면 **"포인터를 따라 걷는" 명령을 손으로 짜야 했다.** 흔히 인용되는 CODASYL 코드 조각은 이렇게 생겼다.

```
FIND CUSTOMER USING CUST-ID.
FIND FIRST ORDER WITHIN CUSTOMER-ORDER-SET.
WHILE DB-STATUS = 0 DO
    FIND FIRST LINE-ITEM WITHIN ORDER-LINE-SET.
    ...
    FIND NEXT ORDER WITHIN CUSTOMER-ORDER-SET.
END.
```

각 `FIND` 는 **하나의 레코드** 를 반환한다. 조인은 언어에 없다 — 프로그래머가 루프로 만든다. 그리고 **저장 구조를 바꾸면(예: 인덱스를 추가하면) 위 코드를 다시 짜야 한다.** 물리 저장과 논리 질의가 붙어 있기 때문이다.

### 1-3. 공통의 통증

두 모델은 다르지만 **개발자가 데이터를 어떻게 꺼내는가** 라는 관점에서 같은 문제를 공유했다.

| 통증 | 계층형/네트워크에서 실제 모습 |
|---|---|
| **네비게이션** | 개발자가 포인터/트리를 순회하는 명시적 코드를 짠다. SELECT 같은 선언적 문장이 없다. |
| **스키마 변경 = 코드 변경** | 인덱스 추가, 필드 이동, 관계 재구조화가 애플리케이션 재작성으로 전파된다. |
| **N:N 관계** | 계층형은 데이터 복제, 네트워크는 pointer set 을 손으로 유지. |
| **애드혹 질의 불가** | 미리 짠 프로그램 외에 "이 조건으로 뽑아 봐" 를 시도할 도구가 없다. |
| **DBA 없이는 못 씀** | 물리 구조를 알아야 프로그램이 돌아간다. |

이게 Codd 가 1970년에 논문을 쓴 배경이다.

---

## 2. Codd 의 1970년 논문 — 이론이 먼저 도착했다

Edgar F. Codd 는 IBM 산호세 연구소에서 일하던 수학자였다. 그가 쓴 논문 **"A Relational Model of Data for Large Shared Data Banks"** 는 _Communications of the ACM_ **Vol. 13, No. 6 (June 1970), pp. 377–387** 에 실렸다.[^codd]

이 논문의 핵심 주장은 두 개다.

1. **데이터는 관계(수학적 의미의 relation, 즉 튜플의 집합)로 표현할 수 있다.** 트리도 포인터 그래프도 아니고, 그냥 테이블이다.
2. **애플리케이션은 데이터의 물리적 표현으로부터 독립해야 한다.** 저장 구조가 바뀌어도 질의는 바뀌지 않아야 한다.

두 번째 주장 — **"data independence"** — 이 사실상 이 논문의 파괴력이었다. Codd 는 CODASYL 스타일 접근이 "**과도한 데이터 종속성** 을 강요한다" 고 지적했다. 요약하면: "당신은 데이터가 **무엇인지** 만 말해라. **어떻게 가져올지** 는 시스템이 정한다."

이 아이디어를 문법으로 옮긴 것이 **SQL**(당시 SEQUEL, 1974, IBM System R 프로젝트) 이다. SQL 은 관계형 모델 자체가 아니라 그 위에 얹힌 **선언적 질의어** 다. Codd 는 SQL 이 자신의 관계 대수를 완전히 표현하지 못한다며 평생 불만이었지만, 시장은 SQL 을 골랐다.

---

## 3. Oracle 이 실제로 판 것 — "이론을 상용에서 돌게 만든 회사"

여기서 Ellison 이 등장한다. 그는 IBM System R 논문을 읽고 "이걸 상용화하면 IBM 이 자기 제품을 자기 손으로 잠재우기 전에 시장을 먹을 수 있다" 고 판단했다.[^wiki-oracle] IBM 은 실제로 System R 을 상용화하는 데 **7년** 이 더 걸렸다(DB2, 1983).

Oracle 이 시장에서 지운 것 셋.

### 3-1. 네비게이션을 지웠다

CODASYL 의 20줄짜리 `FIND` 루프가 이렇게 됐다.

```sql
SELECT o.id, li.product, li.qty
FROM   customer c
JOIN   orders o     ON o.customer_id = c.id
JOIN   line_item li ON li.order_id = o.id
WHERE  c.cust_id = 12345;
```

**개발자는 조인 순서, 인덱스 사용, 접근 경로를 지정하지 않는다.** 옵티마이저가 정한다. Codd 가 20년 전 논문에 쓴 "data independence" 가 사용자 눈에 처음으로 보인 형태였다.

### 3-2. 스키마 진화의 비용을 낮췄다

`ALTER TABLE customer ADD COLUMN email VARCHAR(255)` 한 줄로 필드가 추가되고, 기존 애플리케이션 코드는 손대지 않아도 된다(그 필드를 안 쓴다면). CODASYL 세계에서 이건 며칠 걸리는 작업이었다.

### 3-3. **이식성** 을 팔았다

Oracle 은 1980년대 초반부터 VAX/VMS, Unix 여러 종, IBM 메인프레임, PC-DOS 까지 **여러 플랫폼에 이식** 됐다. IMS 는 IBM 하드웨어에 붙어 있었고, IDMS 는 특정 벤더에 종속됐다. **"어느 서버를 사도 같은 DB 를 돌릴 수 있다"** 는 것이 1980년대 기업에게 대단히 강력한 판매 포인트였다.

이 세 가지를 묶으면 Oracle 의 실제 발명은 이렇게 정리된다 — **관계형 이론과 SQL 을 다중 플랫폼에 상용급 성능으로 이식한 첫 회사.**

---

## 4. Oracle 이 남긴 것 — 이론이 시장을 만나면 생기는 그림자

40년이 지난 지금 Oracle DB 는 여전히 세계에서 가장 많이 팔리는 상용 DBMS 중 하나다. 그 사이 Oracle 이 남긴 것들.

### 4-1. 라이선스 비용과 감사(audit)

Oracle Enterprise Edition 의 코어당 라이선스는 4자리 달러다. 여기에 옵션(Partitioning, RAC, Active Data Guard, Advanced Security) 이 각각 별도 과금이고, 실행 중인 서버 CPU 를 잘못 세면 감사에서 수십억 원 청구가 나온다. **"기술적으로 훌륭한 제품" 과 "상업적으로 두려운 벤더" 가 같이 붙어왔다.**

### 4-2. Vendor lock-in

Oracle 의 PL/SQL, 힌트, 파티셔닝 문법, 시퀀스 사용 관행은 표준 SQL 을 벗어난다. 대규모 Oracle 시스템을 PostgreSQL 로 옮기는 프로젝트는 여전히 년 단위로 걸린다. Oracle 이 "표준을 지키지 않아서" 가 아니라, **표준이 확립되기 전에 사실상의 표준을 먼저 정착시켰기 때문에** 그렇다.

### 4-3. "RDBMS 는 만능" 이라는 15년의 관성

1990~2005 사이에 새 시스템은 일단 RDBMS 부터 골랐다. 로그도 관계형에 넣고, 세션도 관계형에 넣고, 파일 첨부도 BLOB 으로 관계형에 넣었다. 성능이 필요하면 Oracle 을 더 사 왔다. 이 관성이 깨진 게 대략 2007~2009 년이다.

- **Google Bigtable 논문** (2006) → 컬럼 지향 분산 저장의 상용화 시작
- **Amazon Dynamo 논문** (2007) → eventual consistency, 해시 파티셔닝
- **MongoDB** (2009), **Cassandra** (2008), **Redis** (2009) 의 오픈소스 확산

이걸 지금 우리는 "NoSQL 운동" 이라고 부른다. 그러나 정확히 말하면 이건 관계형 모델에 대한 반대가 아니었다 — **Oracle 이 정착시킨 "RDBMS 하나로 다 한다" 는 관행에 대한 반대** 였다. Codd 의 논문 자체를 반박한 사람은 지금까지도 거의 없다.

### 4-4. 오픈소스의 성장이 결국 Oracle 을 좁혔다

**PostgreSQL** (1996 이후 안정판) 과 **MySQL** (1995) 이 커지면서, "관계형 = Oracle" 은 "관계형 = 여러 선택지" 로 바뀌었다. 아이러니하게도 Oracle 은 2009년 **MySQL 자체를 인수** 했다(Sun 인수의 일부로). 그 시점부터 MySQL 개발자 중 상당수가 이탈해 **MariaDB** 를 포크했고, 지금도 두 갈래로 흐른다.

---

## 5. 정리 — 두 개의 겹치는 시대

**Before Oracle (1970 이전)** : 데이터베이스는 사실상 애플리케이션의 일부였다. 프로그래머가 물리 구조를 알아야 데이터를 꺼냈고, 스키마 변경은 프로그램 재작성을 의미했다. 데이터베이스는 "코드에 딸린 저장 계층" 이었다.

**With Oracle (1980년대~2000년대)** : 데이터베이스가 애플리케이션에서 **분리** 됐다. 개발자는 SQL 을 던지고, 옵티마이저가 계획을 짜고, DBA 가 물리 구조를 관리하고, 애플리케이션은 무엇을 원하는지만 말했다. Codd 의 이론이 상업적 규모에서 검증됐다.

**After Oracle 의 단일 시대 (2010년대~)** : 관계형은 살아남았지만 "**유일한 답**" 은 아니게 됐다. 워크로드마다 다른 저장소가 붙는다 — 이벤트 스트림은 Kafka, 시계열은 InfluxDB/TimescaleDB, 그래프는 Neo4j, 캐시는 Redis, 그리고 여전히 트랜잭션 코어는 PostgreSQL 또는 Oracle. 이 다층 구조를 우리는 지금 **polyglot persistence** 라고 부른다.

---

## 6. 한 문장으로

**Codd 는 이론을 썼고, IBM 은 SQL 을 만들었지만, Oracle 은 이론과 문법을 회사가 살 수 있는 제품으로 바꾼 첫 벤더였다.** 그래서 우리는 지금도 "관계형 = 테이블 + SQL" 이라고 자연스럽게 말하고, 그 문장 안에 Codd 의 이름은 잘 등장하지 않는다. Oracle 이 남긴 진짜 유산은 소프트웨어가 아니라, **그 문장이 자연스러워진 사실 그 자체다.**

---

[^wiki-oracle]: Wikipedia, _Oracle Database_ — <https://en.wikipedia.org/wiki/Oracle_Database>. SDL(1977) → RSI → Oracle Corporation. Oracle v2 가 1979년 첫 상용판(v1 을 건너뛴 것은 마케팅 판단). "SQL 을 쓴 가장 초기 상용 데이터베이스 중 하나."

[^wiki-rdb]: Wikipedia, _Relational database_ — <https://en.wikipedia.org/wiki/Relational_database>. Multics Relational Data Store 가 1976년 6월로 최초 상용 RDBMS; IBM System R 은 1974년 시작된 연구 프로젝트; "관계형 데이터베이스가 계층형·네트워크 데이터베이스를 대체하게 된 이유는 구현과 관리가 더 쉬웠기 때문."

[^codd]: E. F. Codd, "A Relational Model of Data for Large Shared Data Banks", _Communications of the ACM_, Vol. 13, No. 6 (June 1970), pp. 377–387. 관계형 모델의 기초 논문. 데이터 독립성(data independence), 관계(relation) 로서의 데이터 표현, 선언적 접근을 제시. 원문 PDF: <https://www.seas.upenn.edu/~zives/03f/cis550/codd.pdf>
