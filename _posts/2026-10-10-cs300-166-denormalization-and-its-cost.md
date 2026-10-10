---
layout: post
title: "[CS300 #166] 반정규화와 그 대가 — 읽기를 사고 일관성을 판다"
date: 2026-10-10 20:46:00 +0900
categories: [cs]
tags: [cs300, database, denormalization, materialized-view, consistency]
---

컴퓨터공학 300 주제 시리즈의 166번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

반정규화는 읽기 성능을 위해 정규화로 없앤 중복을 의도적으로 되살리는 것이고, 그 대가는 "중복된 값들을 누가, 언제, 어떻게 맞출 것인가"라는 영구적인 숙제다.

## 왜 필요한가

정규화된 스키마는 쓰기에 강하다. 사실이 한 곳에만 있으니 고칠 곳도 한 곳이다. 대신 읽을 때 여러 테이블을 조인해야 한다. 게시판 목록 화면에 글마다 댓글 수를 보여 주려면, 글 목록을 가져올 때마다 댓글 테이블을 세야 한다. 글이 수백만 개, 댓글이 수억 개가 되고 목록 화면이 초당 수천 번 열리면 이 집계가 병목이 된다.

이때 `post` 테이블에 `comment_count` 열을 하나 두면 목록 조회는 조인 없이 끝난다. 이것이 반정규화다. 문제는 그 순간부터 "댓글 수"라는 사실이 두 곳(댓글 행의 개수, 그리고 `comment_count` 값)에 존재한다는 것이다. 둘이 어긋나면 어느 쪽이 맞는지 판단할 근거는 원본뿐이다.

반정규화는 금지된 기술이 아니다. 비용이 분명한 거래다. 이 글은 그 거래의 종류와 가격표를 정리한다.

## 핵심 개념

### 원칙: 먼저 정규화, 측정, 그다음 반정규화

순서가 중요하다. 정규화된 설계가 있어야 "무엇이 원본이고 무엇이 파생인지"가 분명해진다. 반정규화된 값은 언제나 원본에서 다시 계산할 수 있어야 한다. 그 경로가 없는 중복은 반정규화가 아니라 그냥 설계 결함이다.

그리고 반정규화의 근거는 측정이어야 한다. 실행 계획과 지연 시간을 보고, 인덱스나 쿼리 수정으로 풀리지 않을 때 고려한다.

### 대표적인 형태

| 기법 | 예 | 맞추는 방법 |
|---|---|---|
| 파생 값 저장 | `post.comment_count`, `order.total_amount` | 트리거, 애플리케이션, 배치 |
| 열 복제 | `order_item` 에 `product_name` 복사 | 쓰기 시 복사, 이후 갱신 정책 결정 |
| 테이블 합치기 | 1:1 관계 두 테이블을 하나로 | 스키마 변경 |
| 요약 테이블 | 일별 매출 집계 테이블 | 배치, 구체화 뷰 갱신 |
| 구체화 뷰 | `CREATE MATERIALIZED VIEW` | `REFRESH` (PostgreSQL) |
| 문서형 내장 | 주문 문서 안에 고객 정보 포함 | 애플리케이션 |

열 복제에는 두 종류가 있다는 점을 구분해야 한다. 주문 당시의 상품명·가격을 주문품목에 저장하는 것은 **스냅숏**이다. 원본이 바뀌어도 바뀌면 안 되므로 동기화 대상이 아니며, 엄밀히는 중복이 아니라 다른 사실이다. 반면 "현재 상품명"을 보여 주려고 복사한 것은 원본이 바뀔 때 따라 바뀌어야 하는 진짜 중복이다. 둘을 섞으면 "지난 영수증의 상품명이 바뀌었다"는 민원이 들어온다.

### 가격표

반정규화가 치르는 비용은 다음과 같다.

1. **쓰기 비용 증가**: 댓글 하나를 쓸 때 `post` 행도 갱신해야 한다. 인기 글 하나에 댓글이 몰리면 그 행 하나에 갱신이 몰려 **락 경합**이 생긴다.
2. **일관성 책임**: 원본을 바꾸는 모든 경로가 파생 값도 고쳐야 한다. 경로는 시간이 지나면서 늘어난다. 관리자 도구, 배치, 마이그레이션 스크립트, 다른 팀의 서비스.
3. **불일치 탐지와 복구 장치**: 어긋남을 찾는 검증 쿼리와 원본에서 다시 계산하는 복구 절차가 필요하다.
4. **저장 공간**: 대개 사소하지만, 큰 열을 복제하면 무시할 수 없다.
5. **인지 부하**: 새로 온 사람이 "어느 값이 진짜인가"를 알아야 한다.

### 동기화 방식의 비교

| 방식 | 장점 | 단점 |
|---|---|---|
| DB 트리거 | 모든 쓰기 경로를 DB 가 잡는다 | 숨어 있어 보이지 않음, 대량 작업 시 느림 |
| 애플리케이션 코드 | 명시적, 테스트 쉬움 | 다른 경로(직접 SQL, 다른 서비스)가 빠뜨림 |
| 주기적 배치·구체화 뷰 | 단순, 원본과 분리 | 갱신 사이에는 낡은 값 |
| 이벤트 기반(CDC 등) | 서비스 간 확장 | 지연, 순서·중복 처리 필요 |

PostgreSQL 의 구체화 뷰는 질의 결과를 테이블처럼 저장하고, `REFRESH MATERIALIZED VIEW` 를 실행할 때만 갱신된다. `CONCURRENTLY` 옵션을 쓰면 갱신 중에도 읽기를 막지 않지만, 그러려면 뷰에 고유 인덱스가 있어야 한다. "얼마나 낡아도 되는가"가 분명한 리포트에 잘 맞는다.

## 직접 해 보기

댓글 수를 트리거로 유지하는 반정규화를 만들고, 일부러 빈틈을 낸 뒤 탐지·복구해 본다.

```python
import sqlite3
con = sqlite3.connect(":memory:")
con.executescript("""
CREATE TABLE post (id INTEGER PRIMARY KEY, title TEXT,
                   comment_count INTEGER NOT NULL DEFAULT 0);   -- 반정규화 열
CREATE TABLE comment (id INTEGER PRIMARY KEY, post_id INTEGER, body TEXT);
CREATE TRIGGER c_ins AFTER INSERT ON comment BEGIN
  UPDATE post SET comment_count = comment_count + 1 WHERE id = NEW.post_id;
END;
CREATE TRIGGER c_del AFTER DELETE ON comment BEGIN
  UPDATE post SET comment_count = comment_count - 1 WHERE id = OLD.post_id;
END;
INSERT INTO post (id, title) VALUES (1,'정규화'),(2,'반정규화');
INSERT INTO comment (post_id, body) VALUES (1,'a'),(1,'b'),(2,'c');
DELETE FROM comment WHERE body = 'b';
""")
check = """SELECT p.id, p.comment_count, COUNT(c.id) AS actual
           FROM post p LEFT JOIN comment c ON c.post_id = p.id
           GROUP BY p.id HAVING p.comment_count <> COUNT(c.id)"""
print("트리거 유지 후 불일치:", con.execute(check).fetchall())
# 누군가 트리거가 없는 경로(예: 댓글을 다른 글로 옮기는 UPDATE)를 만들었다
con.execute("UPDATE comment SET post_id = 2 WHERE body = 'a'")
print("UPDATE 경로 누락 후 불일치:", con.execute(check).fetchall())
# 원본에서 다시 계산해 바로잡기
con.execute("""UPDATE post SET comment_count =
               (SELECT COUNT(*) FROM comment WHERE post_id = post.id)""")
print("재계산 후 불일치:", con.execute(check).fetchall())
```

결과:

```
트리거 유지 후 불일치: []
UPDATE 경로 누락 후 불일치: [(1, 1, 0), (2, 1, 2)]
재계산 후 불일치: []
```

삽입과 삭제는 트리거가 잡았다. 하지만 "댓글을 다른 글로 옮기는" 갱신 경로는 아무도 생각하지 못했고, 그 한 번으로 두 글의 숫자가 모두 틀어졌다. 반정규화의 사고는 거의 항상 이렇게 "생각 못 한 쓰기 경로"에서 난다. 그래서 반정규화에는 세 가지가 세트로 붙어야 한다. 동기화 장치, 불일치 검증 쿼리, 원본에서 재계산하는 복구 절차다.

## 현업에서는

- **카운터 열의 핫스팟**: 인기 게시물의 `like_count` 를 매 클릭마다 `UPDATE` 하면 그 행 락에 요청이 줄을 선다. 그래서 카운트는 Redis 같은 곳에서 누적하고 주기적으로 DB 에 반영하거나, 증분 행을 쌓아 두고 나중에 합치는 방식을 쓴다. 정확도와 실시간성 중 무엇을 양보할지가 설계 질문이 된다.
- **검색·분석 저장소는 거대한 반정규화**다. Elasticsearch 색인이나 데이터 웨어하우스의 넓은 팩트 테이블은 원본 DB 를 조인한 결과를 복제해 둔 것이다. 원본이 RDB 에 있고 그쪽이 진실이라는 합의가 있어야 재색인으로 복구할 수 있다.
- **"이 값은 파생이다"를 스키마 주석이나 문서에 적는 팀**이 사고가 적다. 원본이 무엇인지, 어떻게 재계산하는지를 한 줄이라도 남겨 둔다.
- **야간 정합성 점검**: 반정규화 열마다 위의 `check` 같은 쿼리를 배치로 돌려 불일치 건수를 지표로 내보내면, 어긋남이 생겼을 때 사용자보다 먼저 안다.

## 확인 문제

1. 주문품목에 주문 당시 단가를 저장하는 것은 반정규화인가? 이유를 설명하라.
2. 댓글 수를 반정규화했을 때 동기화가 필요한 쓰기 경로를 세 가지 이상 나열하라.
3. 구체화 뷰가 적합한 경우와 부적합한 경우를 하나씩 들어라.
4. 반정규화 열에 대해 "정답"을 판정할 근거는 어디에 있어야 하는가?

### 풀이

1. 일반적으로 아니다. 주문 시점의 가격은 상품의 현재 가격과 다른 사실이며, 원본이 바뀌어도 바뀌면 안 되는 스냅숏이다.
2. 댓글 작성, 삭제, 다른 글로 이동, 글 삭제 시 댓글 일괄 삭제, 관리자 일괄 정리, 데이터 마이그레이션.
3. 적합: 몇 분~하루 지연이 허용되는 대시보드 집계. 부적합: 사용자가 방금 쓴 결과를 즉시 봐야 하는 화면.
4. 정규화된 원본 데이터. 파생 값은 언제나 원본에서 재계산할 수 있어야 한다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [CREATE MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-creatematerializedview.html), [REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html)
- PostgreSQL 공식 문서, [CREATE TRIGGER](https://www.postgresql.org/docs/current/sql-createtrigger.html)
- MongoDB 공식 문서, [Data Modeling](https://www.mongodb.com/docs/manual/data-modeling/) — 내장(embedding)과 참조의 선택
- Abraham Silberschatz, Henry F. Korth, S. Sudarshan, *Database System Concepts*, 7th ed., McGraw-Hill, 2019. 7장 "Relational Database Design" 중 denormalization 논의
