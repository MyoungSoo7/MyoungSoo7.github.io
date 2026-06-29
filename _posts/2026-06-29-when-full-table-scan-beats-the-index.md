---
layout: post
title: "*풀 스캔 이 *인덱스 보다 *빠른 경우* — *옵티마이저 의 *수학* 과 *주니어 가 *흔히 *오해 하는 *7 가지 시나리오**"
date: 2026-06-29 17:30:00 +0900
categories: [database, performance, query-optimization, postgres, mysql]
tags: [full-table-scan, sequential-scan, index-scan, cost-based-optimizer, selectivity, bookmark-lookup, postgres, mysql, oracle, explain-analyze, btree, planner]
---

> *PR 리뷰* — *주니어 가 *"이 쿼리 가 *너무 느려서 *인덱스 를 *하나 *추가 했습니다"*.
>
> *나는 *EXPLAIN ANALYZE 를 *돌려 본다*. *인덱스 추가 후 의 *쿼리* 가 *추가 전 보다 *느리다*. *3 배*. *왜?*
>
> *주니어 의 *놀란 표정* — *"인덱스 가 *빠른 거 아닌가요?"*
>
> *9 년 의 *조용한 진실* — *인덱스 가 *항상 빠른 것 이 *아니다*. *때로는 *풀 스캔 이 *압도 적으로 빠르다*. *그 *때 가 *언제 인지* 를 *옵티마이저 는 *수학 으로 결정* 한다. *그 *수학 을 *모르면 *불필요한 인덱스 가 *쿼리 를 *느리게 만든다*. *그리고 *INSERT / UPDATE 를 *영구 적 으로 *5 ~ 30 % *느리게 만든다*.

이 글은 *풀 스캔 이 *인덱스 보다 *빠른 경우* 의 *7 가지 시나리오* 와 *옵티마이저 의 *판단 의 수학* 과 *실전 EXPLAIN ANALYZE 의 *읽는 법* 을 *9 년차 백엔드 개발자 의 시각* 으로 *밀도 있게* 정리한다.

함께 보면 좋은 *자매편* :
- *[DBMS 의 *3 층 구조* — *클라이언트 / 인스턴스 / 데이터베이스*](/2026/06/26/dbms-architecture-client-instance-database-three-layer-deep-dive.html)* — *Buffer / 디스크 의 *기반*
- *[DB 배치 처리 의 *2 축 — *커버링 인덱스 + 청킹*](/2026/06/21/db-batch-performance-covering-index-and-chunking.html)*
- *[MySQL 의 *7 가지 안정성 기둥*](/2026/06/05/mysql-database-stability-7-pillars.html)*

---

## TL;DR — *한 줄 결론*

> *인덱스 = 빠름* 은 *조건 부 진실*. *"테이블 의 *5 ~ 10 % 미만* 의 *행 만 *꺼낼 때"* 의 *조건 에 *한정*. *그 외* — *전체 의 *높은 비율 / 작은 테이블 / 집계 쿼리 / 정렬 / 통계 부정확 / 커버링 인덱스 없음 / 함수 적용* — *7 가지 *조건* 에서 *옵티마이저 는 *풀 스캔 (Sequential Scan) 을 *합리 적 으로 선택*. *그 선택 이 *대부분 의 경우 *옳다*. *주니어 가 *FORCE INDEX 로 *뒤집으면 *3 배 느려진다*. *옵티마이저 의 *수학 을 *이해 하는 것* 이 *DB 성능 의 *9 년차 의 *진짜 차별 화*.

---

## 1. *인덱스 의 *진짜 비용 — *주니어 가 *흔히 *간과 하는 것**

### 1.1 *인덱스 는 *공짜 가 아니다**

*인덱스 를 *추가 하면 *SELECT 가 빨라지는 *대가 로* :

1. *INSERT — *인덱스 페이지 의 *업데이트 비용 → 5 ~ 30 % 느려짐*.
2. *UPDATE — *인덱스 키 가 *변경 되면 *delete + insert 의 *두 작업* + B+Tree 재 균형*.
3. *DELETE — *인덱스 의 *해당 키 의 *제거*.
4. *디스크 공간 — *큰 테이블 의 *인덱스 = 수 GB 의 *별도 공간*.
5. *Buffer Pool 의 *경합* — *인덱스 가 *메모리 의 *데이터 페이지 와 *공간 다툼*.
6. *통계 갱신 / VACUUM 의 *부담* — *autovacuum 의 *작업 량 증가*.

*그래서 *인덱스 의 *추가 가 *언제나 *순익 인 것 이 *아니다*. *읽기 가 *빨라지는 *비용 의 *수익 이 *위 의 *6 가지 비용 의 *합 보다 *커야* 가치 가 있다.

### 1.2 *인덱스 의 *읽기 의 *진짜 단계*

```
1. B+Tree 의 *루트 부터 *리프 까지 *탐색  (3~5 페이지 read)
2. 리프 의 *RID (Row ID) 또는 *PK 획득
3. *Heap 테이블 의 *해당 페이지 *read       ← 이게 "Bookmark Lookup"
4. 행 의 *컬럼 추출
```

*핵심 — *3 단계 의 *Bookmark Lookup*. *각 행 마다 *별도 의 *디스크 read*. *Random I/O*.

*만약 *1000 행 을 꺼낸다면 *1000 회 의 *random I/O*. *Sequential read 의 *수십 배 느림*.

### 1.3 *Sequential 의 *조용한 강력 함**

| 디스크 종류 | Random Read (4KB) | Sequential Read (4KB) | 차이 |
|---|---|---|---|
| *HDD (7200 RPM)* | *~10 ms* | *~0.1 ms* | *100 배* |
| *SATA SSD* | *~0.1 ms* | *~0.01 ms* | *10 배* |
| *NVMe SSD* | *~0.05 ms* | *~0.005 ms* | *10 배* |

*풀 스캔 = *Sequential read*. *인덱스 + Bookmark = *Random read*.

> *디스크 의 *물리 적 특성 이 *옵티마이저 의 *판단 의 *근본 적 근거*. *NVMe 라도 *Sequential 이 *10 배 빠름*.

---

## 2. *옵티마이저 의 *수학 — *왜 *그렇게 결정* 하는가**

### 2.1 *Cost-Based Optimizer 의 *공식**

PostgreSQL 의 *기본 비용 모형* (단순화):

```
Sequential Scan Cost = 
    relation_pages × seq_page_cost (기본 1.0)
  + relation_tuples × cpu_tuple_cost (기본 0.01)

Index Scan Cost =
    log(index_pages) × random_page_cost (기본 4.0)
  + matched_tuples × (random_page_cost + cpu_tuple_cost)
  + matched_tuples × cpu_index_tuple_cost (기본 0.005)
```

*기본 값 의 *함의* :
- *`random_page_cost = 4.0`* — *random read 가 *sequential 보다 *4 배 비싸다 는 *가정*.
- *NVMe SSD 의 *현실* — *random 이 *2 배 정도 차이*. *옵티마이저 의 *기본 값 이 *과대 평가*. *SSD 환경 에선 *`random_page_cost = 1.5 ~ 2.0`* 권 장.

### 2.2 *Selectivity — *결정 의 *근본 지표**

*Selectivity = *조회 결과 의 행 수 / 전체 행 수*.

- *Selectivity = 0.1 % (1 천 행 중 1 행)* — *인덱스 의 *완전 한 승리*.
- *Selectivity = 1 % (1 만 행 중 100 행)* — *인덱스 우세*.
- *Selectivity = 5 ~ 10 %* — *경계 영역*.
- *Selectivity > 10 ~ 20 %* — *Sequential Scan 의 우세*.
- *Selectivity > 30 %* — *Sequential Scan 의 *압도 적 승리*.

*경계 의 *정확 한 % 는 *디스크 / 테이블 크기 / 인덱스 깊이 / Buffer 캐시 의 *함수*. *옵티마이저 가 *각 쿼리 마다 *계산*.

### 2.3 *통계 (Statistics) 의 *결정 적 역할**

옵티마이저 가 *Selectivity 를 *추정* 하는 *재료* :

- *`pg_statistic` (PostgreSQL) / `mysql.innodb_index_stats` (MySQL) / `DBA_HISTOGRAMS` (Oracle)*.
- *Histogram* — *컬럼 값 의 *분포*.
- *Most Common Values (MCV)*.
- *N_distinct* — *고유 값 의 추정 수*.

*ANALYZE / autoanalyze 가 *주기 적 으로 갱신*. *통계 가 *오래 되면 *옵티마이저 의 *판단 이 *틀어진다*.

> *내 *9 년 의 *결정 적 디버깅 의 *반복 — *"이 쿼리 가 *왜 *갑자기 *느려졌나"* 의 *주범 의 *30 % 가 *통계 의 *부정확*. *ANALYZE 한 번 으로 *복구 된 사례 *수십 회*.

---

## 3. *풀 스캔 이 *이기는 *7 가지 시나리오 — *상세**

### 3.1 *시나리오 1 — *높은 Selectivity (>10~20%)**

```sql
-- orders 테이블 1 천만 행
-- status = 'PENDING' 인 행 — 300 만 행 (30%)

SELECT * FROM orders WHERE status = 'PENDING';
```

*인덱스 사용 시* :
- *B+Tree 탐색 — 1 회*.
- *Bookmark Lookup — *300 만 회 의 *random I/O*.
- *전체 *수십 분*.

*풀 스캔 시* :
- *전 테이블 의 *Sequential read*.
- *수십 초*.

*옵티마이저 의 *합리 적 선택* — *풀 스캔*.

*주니어 의 *흔한 실수* — *`status` 에 인덱스 추가 → *FORCE INDEX 사용 → *느려짐*.

### 3.2 *시나리오 2 — *작은 테이블 (수천 행 이하)**

```sql
-- categories 테이블 — 500 행
SELECT * FROM categories WHERE name LIKE 'Electronics%';
```

*작은 테이블 의 *전체 가 *Buffer Pool 의 *한 페이지 또는 *몇 페이지 에 *상시 hot*. *Sequential 의 *비용 = *수 µs*.

*인덱스 의 *추가 가치 = *0*. *오히려 *INSERT / UPDATE 비용 만 증가*.

> *9 년 의 *경험 — *수천 행 이하 의 *마스터 테이블 / 코드 테이블 에 *인덱스 *남발* 의 *함정*. *PK 외 의 *인덱스 = *거의 항상 *불필요*.

### 3.3 *시나리오 3 — *집계 (Aggregation) 쿼리**

```sql
SELECT SUM(amount), COUNT(*) FROM orders WHERE created_at > '2026-06-01';
```

- *6 월 의 *5 백만 행 의 *합산*.
- *모든 행 을 *읽어야 하므로 *Selectivity 가 *100 % (해당 기간 안 에서)*.
- *Sequential read 가 *압도 적 우세*.

*예외* — *Covering Index (created_at, amount) 가 있으면 *Index Only Scan 가능*. *테이블 안 보고 *인덱스 만 *순회*. *그 경우 가 *유일한 *인덱스 의 우세*.

### 3.4 *시나리오 4 — *정렬 / GROUP BY*

```sql
SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id;
```

- *모든 행 을 *읽어야 *그룹화*.
- *인덱스 사용 시 *순서 가 *맞으면 (인덱스 가 *(customer_id, ...)) * *Index Scan + Stream Aggregate 가능*.
- *그러나 *고객 수 가 *적고 (~100) *주문 이 *수억* 이면 *그냥 *풀 스캔 + Hash Aggregate 가 *압도 적 빠름*.

### 3.5 *시나리오 5 — *함수 / 표현 적용**

```sql
SELECT * FROM users WHERE UPPER(email) = 'A@B.COM';
```

- *`email` 에 인덱스 가 *있어도 *UPPER() 의 *결과 가 *인덱스 와 *맞지 않음*.
- *옵티마이저 가 *풀 스캔* 선택.

*해결* — *함수 적용 의 *제거 (애플리케이션 에서 *대소문자 정규화)*, 또는 *함수 기반 인덱스 (`CREATE INDEX ... ON users (UPPER(email))`)*.

### 3.6 *시나리오 6 — *데이터 페이지 가 *Buffer 에 *대부분 hot**

*인덱스 의 *Bookmark Lookup 의 *비용 의 *전제 — *디스크 random read*.

*만약 *테이블 의 *모든 페이지 가 *이미 *Buffer Pool 에 *상주* :
- *Bookmark Lookup 의 *비용 = *RAM access*.
- *Sequential 과 *차이 ↓*.
- *옵티마이저 가 *효과 약함 을 *계산 → *풀 스캔 선택 가능*.

*PostgreSQL 의 *`effective_cache_size`* 설정 의 *영향*. *서버 의 *실제 사용 가능 RAM 의 *반영*.

### 3.7 *시나리오 7 — *통계 의 *극단 적 *부정확*

```sql
SELECT * FROM events WHERE type = 'CLICK';
```

- *통계 상 *CLICK 의 *비율 = 1 %* → 인덱스 선택.
- *실제 — *CLICK 이 *90 %* (통계 가 *몇 달 전*).
- *Bookmark Lookup *9 백만 회*. *재앙*.

*해결* — *ANALYZE 의 *습관 화*. *통계 가 *오래 되지 않게*.

> *9 년 의 *반복 적 경험 — *"내 *쿼리 가 *갑자기 *느려졌어요"* 의 *디버깅 의 *첫 단계 가 *ANALYZE*.

---

## 4. *실전 EXPLAIN ANALYZE 의 *읽는 법**

### 4.1 *3 가지 *스캔 *연산자*

```
Seq Scan on orders
  (cost=0.00..123456.78 rows=10000000 width=64)
  (actual time=0.012..2345.67 rows=9876543 loops=1)
```

- *Seq Scan* — *풀 테이블 스캔*.
- *Index Scan* — *인덱스 + Bookmark Lookup*.
- *Index Only Scan* — *인덱스 만 *순회 (Covering)*.
- *Bitmap Heap Scan + Bitmap Index Scan* — *중간 형태*. *여러 행 의 *Bookmark 를 *모아 *순서 화 한 후 *batch read*.

### 4.2 *cost vs actual time*

- *cost (예측)* — *옵티마이저 의 *추정 비용*.
- *actual time (실측)* — *실제 시간*.

*둘 의 *차이 가 *크면 *통계 부정확 의 *증거*. *cost 와 actual rows 가 *수십 배 차이* 면 *통계 갱신 필요*.

### 4.3 *Bitmap Scan — *경계 영역 의 *영리한 타협**

```
Bitmap Heap Scan on orders
  Recheck Cond: (created_at > '2026-06-01')
  -> Bitmap Index Scan on idx_orders_created_at
       Index Cond: (created_at > '2026-06-01')
```

- *인덱스 에서 *모든 RID 를 *비트맵 으로 모음*.
- *RID 를 *디스크 페이지 순서 로 정렬*.
- *Sequential 에 *가까운 패턴 으로 *Heap read*.

*Selectivity 가 *10 ~ 30 %* 의 *경계 영역* 에서 *옵티마이저 의 *영리한 선택*.

---

## 5. *언어 별 *행동 의 *3 가지 차이**

### 5.1 *PostgreSQL — *유연 한 옵티마이저**

- *Cost-based*. *통계 의 *질 에 *민감*.
- *`pg_stat_statements`* 로 *쿼리 별 *실측 시간 *수집 가능*.
- *`EXPLAIN (ANALYZE, BUFFERS)`* 로 *Buffer Hit / Read 분리 시각 화*.
- *Parallel Seq Scan* — *큰 풀 스캔 의 *멀티코어 분할*.

### 5.2 *MySQL InnoDB — *클러스터드 인덱스 의 *특수성**

- *PK 가 *자동 으로 *클러스터드 인덱스*. *PK 순서 = *디스크 의 *물리 순서*.
- *세컨더리 인덱스 의 *Bookmark Lookup = *PK 의 *재 조회*. *추가 단계*.
- *그래서 *MySQL 의 *세컨더리 인덱스 의 *Bookmark Lookup 비용 ↑ → *풀 스캔 의 *상대 적 우세 ↑*.
- *Optimizer Trace* — *MySQL 의 *옵티마이저 의 *판단 의 *공개*.

### 5.3 *Oracle — *Hint 의 *전통**

- *`/*+ FULL(orders) */`*, *`/*+ INDEX(orders idx_status) */`*.
- *과거 의 *주된 튜닝 방법*. *현재 는 *통계 + Plan Baseline 의 *자동 관리 가 *주력*.
- *Adaptive Plans* — *실행 중 *옵티마이저 가 *판단 변경*.

---

## 6. *실 무 적 *체크리스트 — *내 가 *인덱스 추가 전 의 *5 분 자가 점검**

1. **Selectivity 의 *추정* — *내 WHERE 조건 의 *결과 행 수 / 전체 행 수*. *> 10 %* 면 *추가 하지 말 것*.
2. **테이블 크기 의 *확인* — *< 10,000 행* 이면 *PK 외 *추가 불필요*.
3. **EXPLAIN 의 *현재 상태 확인* — *지금 의 *옵티마이저 가 *어떤 선택* 인가*. *Seq Scan 이라도 *현재 *충분히 빠르면 *추가 하지 말 것*.
4. **INSERT / UPDATE 빈도 확인** — *높은 쓰기 빈도 의 *테이블 에 *읽기 *최적화 인덱스 *남발 의 *위험*.
5. **Covering 의 *가능성 확인* — *Covering 이면 *Index Only Scan 으로 *큰 효용*. *아니면 *Bookmark Lookup 의 *비용 감안*.

---

## 7. *언제 *인덱스 를 *제거 해야 하는가**

*9 년 의 *드물지만 *결정 적 *반대 패턴*. *대부분 의 팀 이 *인덱스 *추가 만 *생각 하고 *제거 를 *놓친다*.

### 7.1 *제거 의 *3 가지 신호*

1. **`pg_stat_user_indexes` 의 *idx_scan = 0** — *6 개월 동안 *한 번도 *안 쓰인 인덱스*.
2. **INSERT / UPDATE 의 *지속 적 성능 하락** — *주범 의 *후보 가 *불필요 인덱스*.
3. **테이블 크기 와 *불균형 인 *인덱스 크기 의 *합* — *테이블 의 *2 배 이상 의 *인덱스 의 *합* — *대부분 *불필요*.

### 7.2 *제거 의 *실제 효용 사례 (내 경험)*

*Settlement 의 *transactions 테이블* — *9 개 의 *인덱스 중 *6 개가 *6 개월 미 사용*.

```sql
DROP INDEX CONCURRENTLY idx_transactions_unused_1;
-- ... × 6
```

*결과* :
- *INSERT 의 *p99 — 80ms → 35ms (-56 %)*.
- *디스크 공간 — 12 GB 회수*.
- *autovacuum 의 *부담 ↓ → CPU 사용 ↓*.

> *"인덱스 의 *추가 만 *생각 하고 *제거 를 *놓치는 *조직 의 *DB 가 *서서히 *부풀어 오른다*. *9 년 의 *결정 적 *교훈*.

---

## 8. *결론 — *풀 스캔 의 *명예 회복**

*"인덱스 = 빠름, 풀 스캔 = 느림"* — *이 *통념 의 *수정* 이 *시니어 의 *진짜 시야*.

*옵티마이저 의 *판단 의 *수학 의 *내면 화* :
- *Selectivity 가 *주된 결정 자*.
- *Random vs Sequential I/O 의 *물리 적 차이*.
- *통계 의 *정확 성 이 *그 모든 것 의 *기반*.

*풀 스캔 의 *7 가지 *합리 적 시나리오* :
1. 높은 Selectivity (>10~20%)
2. 작은 테이블
3. 집계 쿼리
4. 정렬 / GROUP BY
5. 함수 / 표현 적용
6. Buffer Pool 의 *hot data*
7. 통계 의 *부정확*

*인덱스 의 *추가 의 *5 분 자가 점검* + *제거 의 *3 가지 신호* — *9 년 의 *실 무 적 압축*.

> *"인덱스 를 *추가 하기 전 에 *EXPLAIN 을 *먼저 본다"* — *9 년 의 *모든 DB 튜닝 의 *시작 점*. *옵티마이저 가 *대부분 *옳다*. *틀린 경우 만 *내가 도와 줄 가치 가 있다*.

---

## 다음 으로 *권 하는 읽기**

- *Markus Winand 의 *Use The Index, Luke!* — *인덱스 의 *교과서 의 *현대 적 *온라인 버전*.
- *PostgreSQL 의 *Query Planning 문서*.
- *Bill Karwin 의 *SQL Antipatterns* — *인덱스 의 *실 무 적 함정*.
- *자매편 — *내 [DBMS 의 3 층 구조](/2026/06/26/dbms-architecture-client-instance-database-three-layer-deep-dive.html)* + *[DB 배치 처리 의 *2 축](/2026/06/21/db-batch-performance-covering-index-and-chunking.html)*.

*다음 글* — *옵티마이저 의 *Hint 의 *현 명한 사용 + Parameter Sniffing 의 *함정 + Plan Cache 의 *불안정 의 *3 부 시리즈* — *곧*.
