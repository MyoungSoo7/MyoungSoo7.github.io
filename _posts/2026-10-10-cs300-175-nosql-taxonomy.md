---
layout: post
title: "[CS300 #175] NoSQL 분류 — 키값·문서·컬럼·그래프"
date: 2026-10-10 20:55:00 +0900
categories: [cs]
tags: [cs300, database, nosql, data-model, distributed-database]
---

컴퓨터공학 300 주제 시리즈의 175번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

NoSQL 은 관계형 모델이 아닌 데이터 모델을 쓰는 저장소들의 묶음 이름이고, 크게 키-값, 문서, 와이드 컬럼, 그래프의 네 계열로 나뉘며, 각각은 특정 접근 패턴을 아주 싸게 만드는 대신 다른 패턴을 포기한다.

## 왜 필요한가

2000년대 중반, 대규모 웹 서비스들은 관계형 DB 한 대로는 감당할 수 없는 쓰기량과 데이터 양을 마주했다. Amazon 은 2007년 논문에서 장바구니 같은 서비스를 위해 "항상 쓰기 가능한" 키-값 저장소 Dynamo 를 설명했고, Google 은 2006년 논문에서 웹 색인 등을 위한 분산 저장소 Bigtable 을 설명했다. 두 논문은 이후 Cassandra, HBase, DynamoDB 같은 시스템의 설계에 큰 영향을 주었다.

이 시스템들의 공통점은 조인과 범용 트랜잭션을 포기하거나 제한하는 대신, 여러 서버로 수평 확장하기 쉽게 만든 것이다. 그리고 데이터 모델도 "접근 패턴에 맞춘" 형태로 바뀌었다. NoSQL 을 이해한다는 것은 결국 "이 모델은 어떤 질문에 싸게 답하고, 어떤 질문은 못 하는가"를 아는 것이다.

## 핵심 개념

### 네 계열 한눈에

| 계열 | 데이터 모양 | 싸게 하는 것 | 어려운 것 | 예 |
|---|---|---|---|---|
| 키-값 | 키 → 불투명한 값 | 키로 읽기·쓰기 | 값 내부로 검색, 범위 질의(구현에 따라) | Redis, DynamoDB(기본 모델), etcd |
| 문서 | 키 → JSON 같은 계층 문서 | 한 문서 통째로 읽기, 내부 필드 질의 | 문서 간 조인, 여러 문서 걸친 트랜잭션(제한적) | MongoDB, Couchbase |
| 와이드 컬럼 | (파티션 키, 정렬 키) → 열들 | 파티션 안 범위 조회, 대량 쓰기 | 파티션 키 없는 질의, 임의 조건 검색 | Cassandra, HBase, Bigtable |
| 그래프 | 노드와 간선, 속성 | 관계를 여러 단계 따라가기 | 전체 집계, 수평 분할 | Neo4j, Amazon Neptune |

### 키-값

가장 단순하다. `GET key`, `PUT key value`, `DELETE key` 가 거의 전부다. DB 는 값의 내부 구조를 모른다. 대신 해시로 키를 서버에 분산하기 쉬워 수평 확장이 자연스럽다. 세션, 캐시, 설정, 분산 락처럼 "키를 정확히 아는" 접근에 쓴다. Redis 는 값으로 리스트·해시·정렬 집합 같은 자료구조를 지원해 단순 키-값 이상의 일을 한다. 쿠버네티스의 모든 상태를 담는 etcd 도 키-값 저장소다.

### 문서

값이 JSON(또는 BSON) 문서이고, DB 가 그 구조를 이해한다. 내부 필드에 인덱스를 걸고 조건으로 찾을 수 있다. 핵심 설계 질문은 **내장(embed)할 것인가, 참조(reference)할 것인가**다. 주문과 주문 품목처럼 늘 함께 읽고 함께 사라지는 것은 한 문서에 내장하고, 여러 곳에서 공유되거나 끝없이 늘어나는 것(사용자의 전체 활동 기록 등)은 별도 문서로 두고 참조한다. MongoDB 공식 문서는 "함께 접근되는 데이터는 함께 저장하라"는 원칙을 강조한다. 관계형의 정규화와 반대 방향의 출발점이다.

### 와이드 컬럼

Bigtable 계열이다. 이름 때문에 "열 지향 저장(컬럼너)"과 혼동하기 쉬운데 다른 개념이다. 데이터 웨어하우스의 컬럼너 저장은 디스크에 열 단위로 저장하는 물리적 방식이고, 와이드 컬럼은 행마다 다른 열 집합을 가질 수 있는 논리 모델이다.

Cassandra 를 예로 들면 기본 키가 **파티션 키**와 **클러스터링(정렬) 키**로 나뉜다. 파티션 키는 데이터가 어느 노드에 갈지 정하고, 클러스터링 키는 파티션 안의 정렬 순서를 정한다. "센서 9 의 오늘 10시 이후 측정값"처럼 파티션 하나 안의 범위 조회는 매우 싸다. 반면 "온도가 30도 넘는 모든 센서"는 모든 파티션을 뒤져야 한다. 그래서 테이블을 **질의마다 하나씩** 설계하고, 같은 데이터를 여러 테이블에 중복 저장하는 것이 정상이다.

### 그래프

노드(사람, 상품)와 간선(팔로우, 구매)을 일급으로 저장한다. 관계형에서 "친구의 친구의 친구"는 셀프 조인 세 번이고, 단계가 늘수록 비싸진다. 그래프 DB 는 노드에서 이웃으로 바로 건너가는 저장 구조라 단계 탐색이 자연스럽다. 추천, 사기 탐지, 권한 상속, 네트워크 토폴로지에 쓴다. Neo4j 의 Cypher 는 `(a)-[:FOLLOWS*1..2]->(b)` 처럼 패턴을 그림처럼 쓰는 질의 언어다.

### 분산과 일관성

NoSQL 의 상당수는 분산을 전제로 한다. 네트워크 분할이 일어났을 때 일관성(모든 노드가 같은 값)과 가용성(모든 요청에 응답) 중 하나를 포기해야 한다는 것이 CAP 정리다(Brewer 의 2000년 추측, Gilbert 와 Lynch 의 2002년 증명). Dynamo 계열은 분할 중에도 쓰기를 받고 나중에 충돌을 해소하는 쪽을, etcd 같은 합의 기반 저장소는 과반이 없으면 쓰기를 거부하는 쪽을 택한다. Cassandra 는 요청마다 일관성 수준(ONE, QUORUM, ALL 등)을 골라 이 선택을 조절하게 한다.

### "NoSQL 대 SQL"은 낡은 구도

경계는 흐려졌다. PostgreSQL 은 `jsonb` 와 GIN 인덱스로 문서 저장을 잘한다. MongoDB 는 다중 문서 트랜잭션을 지원한다. 분산 SQL DB 들은 관계형 모델을 유지하면서 수평 확장을 한다. 그래서 질문은 "어느 진영인가"가 아니라 "내 접근 패턴과 일관성 요구에 맞는 모델이 무엇인가"다.

## 직접 해 보기

같은 파이썬 자료구조로 네 모델의 "싸게 하는 질문"을 흉내 낸다.

```python
import json, bisect
from collections import deque

# 1) 키-값: 키를 알면 O(1), 값의 내부는 DB 가 모른다
kv = {}
kv["session:7f3a"] = json.dumps({"user": 42, "exp": 1760000000})
print("KV  :", json.loads(kv["session:7f3a"])["user"])

# 2) 문서: 값이 구조를 가진 문서이고, 내부 필드로 질의한다
orders = [
    {"_id": 1, "user": 42, "items": [{"sku": "KB", "qty": 1}, {"sku": "MS", "qty": 2}]},
    {"_id": 2, "user": 7,  "items": [{"sku": "MS", "qty": 1}]},
]
print("DOC :", [o["_id"] for o in orders if any(i["sku"] == "MS" and i["qty"] >= 2 for i in o["items"])])

# 3) 와이드 컬럼: (파티션 키, 정렬 키) → 열들. 파티션 안은 정렬되어 범위 조회가 싸다
table = {}
def put(pk, ck, row):
    part = table.setdefault(pk, [])
    bisect.insort(part, (ck, row))
for ts, temp in [("10:02", 21.5), ("10:00", 21.0), ("10:01", 21.2)]:
    put("sensor-9", ts, {"temp": temp})
part = table["sensor-9"]
lo = bisect.bisect_left(part, ("10:01",))
print("WIDE:", [(ck, r["temp"]) for ck, r in part[lo:]])

# 4) 그래프: 관계 자체가 1급 데이터. 깊이 n 탐색이 자연스럽다
follows = {"a": ["b", "c"], "b": ["d"], "c": ["d", "e"], "d": ["f"], "e": [], "f": []}
def within(start, depth):
    seen, q = {start: 0}, deque([start])
    while q:
        u = q.popleft()
        if seen[u] == depth:
            continue
        for v in follows[u]:
            if v not in seen:
                seen[v] = seen[u] + 1; q.append(v)
    return sorted(k for k, d in seen.items() if d > 0)
print("GRAPH: a 로부터 2단계 이내:", within("a", 2))
```

결과:

```
KV  : 42
DOC : [1]
WIDE: [('10:01', 21.2), ('10:02', 21.5)]
GRAPH: a 로부터 2단계 이내: ['b', 'c', 'd', 'e']
```

각 모델에서 "어려운 질문"도 떠올려 보자. 키-값에서 `user == 42` 인 세션을 찾으려면 모든 값을 열어 봐야 한다. 와이드 컬럼에서 "모든 센서의 10:01 값"은 파티션 키가 없으니 모든 파티션을 훑어야 한다. 문서 모델에서 "MS 를 산 사용자의 이름"은 사용자 문서와 조인이 필요하다. 모델을 고른다는 것은 이 목록을 고르는 것이다.

## 현업에서는

- **"스키마리스"는 스키마가 없다는 뜻이 아니다.** 스키마가 DB 가 아니라 애플리케이션 코드에 있다는 뜻이다. 문서마다 필드 이름이 조금씩 다른 상태로 몇 년이 지나면, 모든 읽기 코드가 다섯 가지 버전의 문서를 처리해야 한다. MongoDB 도 스키마 검증 기능을 제공한다.
- **와이드 컬럼은 질의를 먼저 정하고 테이블을 설계**한다. 나중에 새 질의가 생기면 새 테이블을 만들고 데이터를 다시 채운다. 관계형처럼 "일단 저장하고 나중에 SQL 로 아무거나"가 안 된다.
- **Redis 를 주 저장소로 쓸 때**는 영속성 설정과 메모리 한계를 반드시 확인한다(다음 글).
- **폴리글랏 퍼시스턴스**: 한 서비스 안에서 주문은 PostgreSQL, 세션은 Redis, 검색은 Elasticsearch 를 쓰는 구성이 흔하다. 운영할 저장소가 늘어나는 비용도 같이 계산해야 한다.

## 확인 문제

1. 키-값 저장소가 수평 확장에 유리한 이유는?
2. 문서 모델에서 주문 품목을 주문 문서에 내장하는 것이 적절한 이유와, 사용자의 전체 활동 로그를 사용자 문서에 내장하면 안 되는 이유는?
3. 와이드 컬럼 저장소와 컬럼 지향(컬럼너) 저장의 차이는?
4. "친구의 친구의 친구" 질의가 그래프 DB 에 잘 맞는 이유는?
5. CAP 정리가 말하는 선택은 언제 강제되는가?

### 풀이

1. 키 하나가 연산 단위이고 키 간 관계가 없어, 키의 해시로 서버를 정하면 서버 간 협조 없이 분산할 수 있다.
2. 주문 품목은 주문과 함께 읽히고 함께 사라지며 개수가 제한적이다. 활동 로그는 끝없이 늘어 문서 크기 상한과 갱신 비용 문제를 일으킨다.
3. 와이드 컬럼은 행마다 다른 열 집합을 가질 수 있는 논리 모델이고, 컬럼너는 같은 열의 값을 디스크에 모아 저장하는 물리 저장 방식이다.
4. 간선을 따라 이웃 노드로 직접 이동하는 저장 구조라, 단계마다 조인을 하는 대신 인접 목록을 따라가면 된다.
5. 네트워크 분할이 일어났을 때. 분할이 없을 때는 둘 다 가질 수 있다.

## 더 읽을거리 (References)

- G. DeCandia 외, "Dynamo: Amazon's Highly Available Key-value Store", *SOSP*, 2007. [PDF](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- F. Chang 외, "Bigtable: A Distributed Storage System for Structured Data", *OSDI*, 2006. [Google Research](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/)
- MongoDB 공식 문서, [Data Modeling](https://www.mongodb.com/docs/manual/data-modeling/)
- Neo4j 공식 문서, [Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- Seth Gilbert, Nancy Lynch, "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services", *ACM SIGACT News*, 33(2), 2002.
