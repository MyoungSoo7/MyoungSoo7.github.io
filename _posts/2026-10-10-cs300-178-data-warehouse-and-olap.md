---
layout: post
title: "[CS300 #178] 데이터 웨어하우스와 OLAP — 장사하는 DB 와 분석하는 DB 는 다르다"
date: 2026-10-10 20:58:00 +0900
categories: [cs]
tags: [cs300, database, data-warehouse, olap, columnar-storage]
---

컴퓨터공학 300 주제 시리즈의 178번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

OLTP 는 짧은 트랜잭션을 많이 처리하는 운영용 DB 이고, OLAP 는 대량의 이력을 훑어 집계하는 분석용 처리이며, 데이터 웨어하우스는 OLAP 를 위해 여러 원천의 데이터를 모아 스타 스키마와 컬럼 지향 저장으로 정리한 저장소다.

## 왜 필요한가

쇼핑몰 운영 DB 는 "주문 하나 넣기", "회원 하나 조회하기" 같은 작은 작업을 초당 수천 번 처리하도록 설계되어 있다. 여기에 "지난 2년간 지역별·카테고리별·월별 매출 추이"를 물으면 두 가지 일이 생긴다. 쿼리는 수억 행을 읽느라 오래 걸리고, 그동안 운영 트래픽이 같은 디스크와 메모리를 두고 경쟁해 서비스가 느려진다.

또 분석 질문은 대개 여러 시스템에 걸쳐 있다. 주문은 주문 DB, 광고비는 광고 플랫폼, 고객 상담은 CS 도구에 있다. 이를 한곳에 모아 같은 기준(같은 고객 ID, 같은 날짜 경계)으로 맞춰야 답이 나온다. 그래서 분석용 데이터는 운영 DB 와 분리된 별도 저장소, 데이터 웨어하우스로 옮긴다.

## 핵심 개념

### OLTP 대 OLAP

| | OLTP | OLAP |
|---|---|---|
| 대표 작업 | 주문 생성, 잔액 갱신 | 월별·지역별 매출 집계 |
| 한 번에 건드리는 행 | 몇 개 | 수백만~수십억 |
| 쓰기 | 잦은 소량 갱신 | 주기적 대량 적재 |
| 읽는 열 | 행의 대부분 | 수십~수백 열 중 몇 개 |
| 스키마 | 정규화 | 스타·스노플레이크(반정규화) |
| 저장 방식 | 행 지향 | 열 지향 |
| 지표 | 지연 시간, 초당 트랜잭션 | 스캔 처리량 |

### 차원 모델링과 스타 스키마

Ralph Kimball 이 정리한 차원 모델링은 데이터를 두 종류의 테이블로 나눈다.

- **팩트 테이블**: 측정 가능한 사건. 판매 한 건, 클릭 한 번. 수량·금액 같은 숫자(측정값)와 차원을 가리키는 키로 이루어진다. 길고(행이 매우 많음) 좁다.
- **차원 테이블**: 사건의 맥락. 날짜, 상품, 매장, 고객. 사람이 읽는 속성(카테고리, 도시, 요일)이 많다. 짧고 넓다.

```
                 dim_date
                 (월, 분기, 요일, 공휴일 여부)
                     │
 dim_product ── fact_sales ── dim_store
 (이름, 카테고리)  (qty, revenue,   (도시, 지역)
                   date_key,
                   product_key,
                   store_key)
                     │
                 dim_customer
```

가운데 팩트, 둘레에 차원이 별 모양으로 붙어 스타 스키마라 부른다. 차원이 다시 정규화되어 가지를 치면 스노플레이크 스키마다. 스타 스키마는 의도적인 반정규화다. 분석 질의가 "팩트 하나 + 차원 몇 개 조인 + GROUP BY" 라는 단순한 모양이 되도록 맞춘 것이다.

설계에서 가장 중요한 결정은 팩트의 **그레인(grain)**, 즉 팩트 한 행이 무엇을 뜻하는가다. "주문 한 건"인지 "주문 품목 한 줄"인지에 따라 가능한 질문이 달라진다. 더 잘게 잡을수록 나중에 할 수 있는 질문이 많다.

### OLAP 연산

다차원 큐브를 떠올리면 이해하기 쉽다.

| 연산 | 뜻 | SQL 로는 |
|---|---|---|
| 롤업 | 더 큰 단위로 요약 (일 → 월) | `GROUP BY` 를 굵게, `ROLLUP` |
| 드릴다운 | 더 잘게 (월 → 일) | `GROUP BY` 를 가늘게 |
| 슬라이스 | 한 차원을 하나의 값으로 고정 | `WHERE month = '2026-10'` |
| 다이스 | 여러 차원에 범위 조건 | `WHERE ... AND ...` |
| 피벗 | 행과 열 바꾸기 | 조건부 집계 |

SQL 표준의 `GROUP BY ROLLUP(...)`, `CUBE(...)`, `GROUPING SETS(...)` 는 여러 수준의 소계를 한 번에 계산한다. PostgreSQL, DuckDB 등이 지원한다.

### 열 지향 저장

분석 질의는 넓은 테이블에서 몇 개 열만 읽는다. 행 지향 저장은 한 행의 모든 열이 붙어 있어, `SUM(revenue)` 하나를 위해 모든 열을 디스크에서 읽어야 한다. 열 지향 저장은 같은 열의 값을 모아 저장한다.

```
행 지향:   [1|키보드|서울|2|60000] [2|마우스|부산|1|15000] ...
열 지향:   date_key: [..........]   revenue: [60000, 15000, ...]
           product:  [..........]   city:    [서울, 부산, ...]
```

이점은 세 가지다.

1. 필요한 열만 읽는다.
2. 같은 타입, 비슷한 값이 연속되어 압축이 잘 된다. 정렬된 열은 런 길이 인코딩으로, 값 종류가 적은 열은 사전 인코딩으로 크게 준다.
3. 값 배열을 한꺼번에 처리하는 벡터화 실행과 잘 맞는다.

Stonebraker 등의 C-Store(VLDB 2005) 논문이 이 설계를 학계에 체계적으로 보였고, Google 의 Dremel 논문(2010)은 중첩 데이터를 열 단위로 저장해 대규모 대화형 분석을 하는 방법을 보였다. 오늘날 Apache Parquet 파일 형식, ClickHouse, DuckDB, 그리고 주요 클라우드 웨어하우스가 열 지향 저장을 쓴다.

### 적재: ETL 과 ELT

원천에서 추출(Extract)해 변환(Transform)한 뒤 적재(Load)하는 것이 전통적 ETL 이다. 웨어하우스의 계산 능력이 커지면서, 먼저 원본 그대로 적재하고 웨어하우스 안에서 SQL 로 변환하는 ELT 가 흔해졌다. 어느 쪽이든 핵심 과제는 같다. 키 맞추기, 중복 제거, 늦게 도착한 데이터 처리, 그리고 차원 속성이 시간에 따라 바뀌는 것(고객의 주소 변경 등)을 어떻게 기록할지다. 마지막 것을 Kimball 은 "천천히 변하는 차원(SCD)" 으로 분류했다.

## 직접 해 보기

작은 스타 스키마를 만들고 롤업과 슬라이스를 해 본 뒤, 열 하나를 런 길이 인코딩해 본다.

```python
import sqlite3, random
con = sqlite3.connect(":memory:")
con.executescript("""
-- 차원 테이블: '누가, 무엇을, 언제, 어디서'
CREATE TABLE dim_date    (date_key INTEGER PRIMARY KEY, ymd TEXT, month TEXT);
CREATE TABLE dim_product (product_key INTEGER PRIMARY KEY, name TEXT, category TEXT);
CREATE TABLE dim_store   (store_key INTEGER PRIMARY KEY, city TEXT);
-- 팩트 테이블: 측정값 + 차원 키. 길고 좁다
CREATE TABLE fact_sales (date_key INTEGER, product_key INTEGER, store_key INTEGER,
                         qty INTEGER, revenue INTEGER);
""")
days = [(20260900 + d, f"2026-09-{d:02d}", "2026-09") for d in range(1, 31)]
days += [(20261000 + d, f"2026-10-{d:02d}", "2026-10") for d in range(1, 11)]
con.executemany("INSERT INTO dim_date VALUES (?,?,?)", days)
con.executemany("INSERT INTO dim_product VALUES (?,?,?)",
    [(1, "키보드", "입력장치"), (2, "마우스", "입력장치"), (3, "모니터", "디스플레이")])
con.executemany("INSERT INTO dim_store VALUES (?,?)", [(1, "서울"), (2, "부산")])
random.seed(0)
rows = []
for dk, *_ in days:
    for pk in (1, 2, 3):
        for sk in (1, 2):
            q = random.randint(0, 5)
            rows.append((dk, pk, sk, q, q * {1: 30000, 2: 15000, 3: 200000}[pk]))
con.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?)", rows)

print("-- 롤업: 월 × 카테고리, 그리고 월 소계")
for r in con.execute("""
    SELECT d.month, p.category, SUM(f.revenue) FROM fact_sales f
    JOIN dim_date d USING (date_key) JOIN dim_product p USING (product_key)
    GROUP BY d.month, p.category
    UNION ALL
    SELECT d.month, '(전체)', SUM(f.revenue) FROM fact_sales f
    JOIN dim_date d USING (date_key) GROUP BY d.month
    ORDER BY 1, 2"""):
    print(r)
print("-- 슬라이스: 2026-10, 부산만")
print(con.execute("""SELECT SUM(qty), SUM(revenue) FROM fact_sales f
    JOIN dim_date d USING (date_key) JOIN dim_store s USING (store_key)
    WHERE d.month = '2026-10' AND s.city = '부산'""").fetchone())

# 컬럼 저장의 맛보기: 정렬된 열은 런 길이 인코딩(RLE)으로 크게 줄어든다
col = [r[0] // 100 for r in sorted(rows)]          # 각 행의 '월' 열 (202609, 202610 ...)
rle = []
for v in col:
    if rle and rle[-1][0] == v: rle[-1][1] += 1
    else: rle.append([v, 1])
print("월 열:", len(col), "개 값 → RLE", rle)
```

결과:

```
-- 롤업: 월 × 카테고리, 그리고 월 소계
('2026-09', '(전체)', 37050000)
('2026-09', '디스플레이', 30600000)
('2026-09', '입력장치', 6450000)
('2026-10', '(전체)', 11280000)
('2026-10', '디스플레이', 9000000)
('2026-10', '입력장치', 2280000)
-- 슬라이스: 2026-10, 부산만
(88, 6490000)
월 열: 240 개 값 → RLE [[202609, 180], [202610, 60]]
```

모든 분석 질의가 "팩트 + 차원 조인 + 그룹" 모양이라는 점을 보자. 소계를 `UNION ALL` 로 붙였는데, PostgreSQL 이나 DuckDB 라면 `GROUP BY ROLLUP (d.month, p.category)` 한 줄로 같은 결과를 얻는다(SQLite 는 아직 `ROLLUP` 을 지원하지 않는다). 마지막 줄은 240개의 월 값이 정렬되어 있으면 두 쌍으로 줄어든다는 것을 보여 준다. 열 지향 저장이 압축에 강한 이유다.

## 현업에서는

- **운영 DB 에서 분석하지 않는다**: 대시보드 쿼리를 운영 프라이머리에 직접 붙이는 것은 흔한 장애 원인이다. 최소한 읽기 레플리카로, 규모가 커지면 웨어하우스로 옮긴다.
- **지표 정의가 먼저**: "활성 사용자", "매출"의 정의가 팀마다 다르면 같은 웨어하우스에서 다른 숫자가 나온다. 의미 계층(semantic layer)이나 지표 정의 문서를 두는 이유다.
- **Parquet + 객체 저장소**: 데이터를 Parquet 파일로 객체 저장소에 두고, 여러 엔진(Spark, Trino, DuckDB)이 같은 파일을 읽는 "레이크하우스" 구성이 흔하다. 작은 규모라면 노트북의 DuckDB 하나로 수천만 행 Parquet 를 분석할 수 있다.
- **파티션과 정렬 키**: 웨어하우스 테이블은 날짜로 파티션하고 자주 거르는 열로 정렬해 둔다. 질의가 파티션 조건을 포함하지 않으면 전체를 읽어 비용(클라우드에서는 실제 돈)이 커진다.

## 확인 문제

1. 같은 매출 집계 쿼리를 운영 DB 에서 돌리면 안 되는 이유 두 가지는?
2. 팩트 테이블과 차원 테이블을 각각 설명하고 예를 들어라.
3. 팩트의 그레인을 "주문 한 건"으로 잡으면 할 수 없는 질문의 예는?
4. 열 지향 저장이 `SELECT SUM(revenue) FROM 100열짜리_테이블` 에 유리한 이유는?
5. ETL 과 ELT 의 차이는?

### 풀이

1. 대량 스캔이 오래 걸리고, 그동안 운영 트랜잭션과 디스크·메모리·락을 두고 경쟁해 서비스 성능을 떨어뜨린다. 또 다른 원천 데이터와 결합하기 어렵다.
2. 팩트: 측정 가능한 사건과 그 수치(판매 수량·금액). 차원: 사건의 맥락 속성(날짜, 상품, 매장).
3. "상품별 판매 수량"처럼 주문 안의 품목 단위 질문. 그레인이 주문이라 품목 정보가 없다.
4. 100열 중 revenue 열만 읽으면 되고, 그 열은 압축이 잘 되어 읽을 바이트가 훨씬 적다.
5. ETL 은 적재 전에 외부에서 변환하고, ELT 는 원본을 먼저 적재한 뒤 웨어하우스 안에서 변환한다.

## 더 읽을거리 (References)

- Ralph Kimball, Margy Ross, *The Data Warehouse Toolkit*, 3rd ed., Wiley, 2013.
- M. Stonebraker 외, "C-Store: A Column-oriented DBMS", *VLDB*, 2005.
- S. Melnik 외, "Dremel: Interactive Analysis of Web-Scale Datasets", *VLDB*, 2010. [Google Research](https://research.google/pubs/dremel-interactive-analysis-of-web-scale-datasets-2/)
- Apache Parquet 공식 문서, [File Format](https://parquet.apache.org/docs/file-format/)
- PostgreSQL 공식 문서, [GROUPING SETS, CUBE, and ROLLUP](https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-GROUPING-SETS)
