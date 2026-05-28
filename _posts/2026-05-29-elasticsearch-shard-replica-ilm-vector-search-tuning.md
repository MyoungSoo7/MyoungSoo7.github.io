---
layout: post
title: "Elasticsearch 운영의 *3 축* — *Shard/Replica 설계*, *Index Lifecycle*, 그리고 *Vector Search 의 함정*"
date: 2026-05-29 01:30:00 +0900
categories: [elasticsearch, search, vector, infrastructure]
tags: [elasticsearch, opensearch, shard, replica, ilm, hot-warm-cold, hnsw, vector-search, knn, lucene, jvm-tuning]
---

> *''Elasticsearch 가 *느려졌어요*''*. 이 한 문장은 *원인이 *5 가지* 이상* 있을 수 있다 — *샤드가 너무 잘게 쪼개졌거나*, *세그먼트가 *수십 만 개* 쌓였거나*, *JVM 힙이 *터질 듯* 차 있거나*, *cold tier 가 *hot tier 처럼* 쿼리 받거나*, *벡터 차원 인덱싱이 *오프힙* 을 다 먹었거나*. *경험 없으면 *5 곳을 다 들여다보기* 전엔 *원인을 모른다*.
>
> 이 글은 그 *5 곳을 *체계적으로* 짚는 *Elasticsearch 운영의 *3 축* — *(1) Shard/Replica 설계*, *(2) Index Lifecycle Management*, *(3) Vector Search 튜닝* 을 *현장에서 다친 흔적* 위주로 정리한다.

대상은 *Elasticsearch 8.x / OpenSearch 2.x* 를 *직접 운영* 하거나 *MSK 의 OpenSearch Service* 위에서 *벡터 검색* 까지 쓰는 *Spring Boot 백엔드 팀*.

---

## 1. *기초* — Lucene → Segment → Shard → Index 의 *4 층*

성능 / 운영 문제는 *대부분* 이 4 층 중 *어디* 가 *어떻게* 동작하는지를 *오해* 한 데서 시작한다.

```
[Index]                  ← 논리적 단위 (예: orders-2026-05)
  └─ [Shard] × N          ← 물리적 분산 단위 — *Lucene Index 하나*
       └─ [Segment] × M   ← *Append-only 파일 묶음*
            └─ [Document] ← 실제 JSON
```

### 1.1 *Segment* — *''불변 파일''*

Lucene 은 *문서를 *추가만* 한다*. 수정/삭제는 *''*tombstone* 으로 *덮어쓰기*''*. 그래서 *세그먼트가 시간에 따라 *쌓인다***.

- *너무 많은 세그먼트* — 검색 시 *모든 세그먼트* 를 다 *훑음* → 느림
- 해법: **Merge** — *주기적으로 *세그먼트를 합침*
- 강제 merge: `_forcemerge?max_num_segments=1` — *hot tier 끝나고 *한 번* 만 해야 함*

### 1.2 *Shard* = *''작은 Lucene 인덱스''*

- *Primary shard* — 진짜 저장
- *Replica shard* — *primary 의 *복제본**, *읽기 분산 + 장애 대응*

> *''Elasticsearch 노드 = JVM 프로세스''*. *''Lucene = Elasticsearch 의 *심장*''*. *''Shard = *Lucene 인덱스 + 자신만의 *JVM 힙 사용량*''*. 이 한 줄을 *외우고 가야* 다음 절이 *이해됨*.

---

## 2. *Shard / Replica 설계* — *''몇 개로 쪼개야 하나''*

### 2.1 *황금 공식* — *''Shard 하나당 *10 ~ 50 GB*''*

Elastic 공식 권장 + 현장 경험의 합의:

- *Shard 크기* — **10 ~ 50 GB 사이**. *50 GB 넘으면 검색 느리고, 10 GB 미만이면 *오버헤드*.
- *Shard 수* = 예상 인덱스 크기 / *30 GB* (중간값) — 이걸로 *대략* 잡는다
- *노드 당 shard 수* — **JVM 힙 1 GB 당 *20 shard 이하***. 30 GB 힙이면 *600 shard* 가 한계

### 2.2 *흔한 함정 #1 — *Oversharding (과샤딩)**

```yaml
# 안티 패턴
PUT /logs-2026-05-29
{
  "settings": {
    "number_of_shards": 50,   # ← *''미래 대비''* 라며 큰 숫자
    "number_of_replicas": 2
  }
}
```

이 인덱스에 *10 GB* 데이터가 들어오면:
- *Shard 50 개* × 10 GB / 50 = *각 200 MB* (한참 미달)
- *Replica 까지 합쳐* 150 shard — *JVM 힙 압박*
- *클러스터에 *수천 개의 작은 shard* — *''Cluster State 가 *GB 단위*''* — *마스터 노드 *위태*

> **현장의 흉터**: *''*노드 30 개 클러스터인데 *cluster state size 가 *5 GB* 가 되어 *마스터 선출 *시 *수십 초*''*. 이게 *oversharding 의 *최종 형태*.

### 2.3 *흔한 함정 #2 — *Under-sharding***

```yaml
# 또 다른 안티 패턴
PUT /events-stream
{
  "settings": {
    "number_of_shards": 1
  }
}
```

- *Shard 1 개* 에 *TB 단위* 데이터가 쌓이면 — *검색 시 *병렬 처리 불가능**
- *Replica 있어도 *primary 가 *너무 큼*** — *recovery 시 *수시간**

### 2.4 *Replica 수* — *''짝수일 필요 없다''*

- *최소 *1***. *0 은 *production 금지** — *노드 하나 죽으면 데이터 손실*
- *읽기 부하 많으면 *2 ~ 3*** — *replica 수만큼 *읽기 처리량 ↑*
- *replica 가 많을수록 *쓰기 처리량 ↓*** — *write fanout 비용*

### 2.5 *''Rollover''* 패턴 — *시계열 데이터의 *기본 답*

로그 / 이벤트 / 메트릭 같은 *시계열* 데이터는 *''고정 인덱스''* 가 아니라 *''*시간으로 *돌아가는* 인덱스''* 로 관리:

```
logs-000001, logs-000002, logs-000003, ...
   └─ alias "logs" 가 *최신 인덱스* 가리킴

조건: 50 GB 차거나 / 7 일 지나면 / 1 천만 문서 → *rollover*
```

이 패턴이 *time-series workload* 의 *압도적 표준*. 그리고 *이게 *ILM 의 출발점*.

---

## 3. *Index Lifecycle Management (ILM)* — *''데이터의 *생애 주기*''*

### 3.1 *4 단계 라이프사이클*

```
[Hot]        [Warm]       [Cold]       [Frozen]      [Delete]
 │            │            │            │
 활발히       검색 적음     거의 안 봄    아카이브       삭제
 쓰기+읽기    읽기만        S3 마운트    오브젝트
 NVMe SSD    SATA SSD     HDD          스토리지

기간 예시:
  7일         30일          90일         365일         이후 삭제
```

### 3.2 *각 tier 의 *물리적 의미**

- **Hot** — *''현재 진행 중''*. 가장 *빠른 노드 + NVMe SSD*. *읽기 + 쓰기 모두*
- **Warm** — *''*가끔* 본다''*. *SATA SSD*, *read-only*, *force-merge 1 segment 됨*
- **Cold** — *''거의 안 본다''*. *대용량 HDD*, *read-only*, *replica = 0* (스냅샷 백업으로 대체)
- **Frozen** — *''S3 등 *오브젝트 스토리지* 에 인덱스 *마운트*''*. *쿼리 가능* 하지만 *느림*. *비용 *극단적으로 낮음*
- **Delete** — *완전 삭제*

### 3.3 *ILM Policy 예시*

```json
PUT _ilm/policy/logs_policy
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "7d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "forcemerge": { "max_num_segments": 1 },
          "shrink":     { "number_of_shards": 1 },
          "allocate":   { "include": { "data_tier": "warm" } }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "allocate":  { "number_of_replicas": 0,
                         "include": { "data_tier": "cold" } },
          "freeze":    {}
        }
      },
      "delete": {
        "min_age": "365d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

### 3.4 *흔한 함정 #3 — *cold tier 에 *hot 처럼* 쿼리가 감***

```
[증상]  ''대시보드를 *6개월 전부터 *현재* 까지'' 그렸더니 *3 분 응답*
[원인]  Grafana / Kibana 쿼리가 *cold tier 인덱스에도 *fan-out*
[해결]  쿼리에서 *time range 를 *명시적으로 제한*, 또는 *index pattern 분리*
```

> **인사이트**: *''*ILM 의 *진짜 어려운 부분* 은 *데이터 이동* 이 아니라 *쿼리가 *경계를 모름*''* — *팀 교육 + Kibana data view 분리* 가 *절반*.

### 3.5 *흔한 함정 #4 — *taint / toleration 으로 *분리한 노드* 가 *제대로* 동작 안 함***

K3s / k8s 위에서 운영할 때 *''hot 노드''*, *''cold 노드''* 를 *taint* 로 분리하지만:

- *Pod 의 toleration 을 *추가 안 함* → *cold pod 가 hot 노드에 올라옴*
- *Elasticsearch 의 *node attribute* (`node.attr.data_tier=cold`) 와 *k8s taint 가 *정렬 안 됨*

> 본 블로그의 [별도 글](/2026/05/26/k3s-cold-tier-taint-toleration-trap/) 에 *현장에서 다친 흔적* 정리.

---

## 4. *Scale-out 전략* — *''*수직* vs *수평*''*

### 4.1 *수직 확장의 *한계**

> *''힙 32 GB 이상 *피해라*''*. 이게 *Elasticsearch 운영의 *철칙*.

이유:
1. **JVM 의 *compressed oops*** — 32 GB 이하에서만 *4 바이트 포인터* (메모리 절약). 32 GB 넘으면 *8 바이트 포인터* 로 *오히려 메모리 효율 ↓*
2. **GC 부담** — *큰 힙* → *Full GC 시 *수분* 멈춤*

권장: *시스템 메모리의 *50%*, *최대 31 GB*. 나머지 *50% 는 *OS page cache* (Lucene 이 *적극 활용*).

### 4.2 *수평 확장의 *물리적 진실**

```
노드 추가 → 자동으로 shard rebalancing → 처리량 ↑
```

하지만 *3 가지 함정*:

#### 함정 1 — *Recovery 폭주*

- *새 노드 들어오면* 기존 shard 가 *복제됨* → *네트워크 폭주*
- 해법: `cluster.routing.allocation.cluster_concurrent_rebalance: 2` 같은 *throttle*

#### 함정 2 — *데이터 skew*

- *특정 shard 가 *과도하게 큼* — *''hot shard''*
- 원인: *raw partition key 가 *uneven* (예: *''customer_id 99 가 *전체 80%*''*)
- 해법: *routing key* 를 *해시* 로 분산, 또는 *shard rebalance*

#### 함정 3 — *Cross-AZ 네트워크 비용*

- AWS 에서 *AZ 간 트래픽 = *유료**
- *3 AZ 에 분산* + *replica 가 *cross-AZ*** 하면 *네트워크 비용 폭증*
- 해법: `cluster.routing.allocation.awareness.attributes: zone` 으로 *''replica 는 *다른 AZ 에 두되* primary 와 동일 AZ 안에서만 *읽기 fanout*''*

### 4.3 *''Coordinating Node''* 분리 — *대규모의 *필수 패턴**

```
[Client] → [Coordinating Node × N] → [Data Node × M]

Coordinating Node 의 역할:
  - 쿼리 분산 (fan-out)
  - 결과 머지
  - *데이터 없음*, *마스터 아님*
```

- *대규모 fan-out 쿼리* 가 *data node 의 CPU 를 잡아먹는 것* 을 *coordinating node 가 *흡수*
- *200+ shard 클러스터* 부터는 *coordinating node 분리* 가 *체감*

### 4.4 *Master / Data / Ingest / Coord 의 *역할 분리**

대규모 클러스터의 *4 종 노드*:

| 노드 종류 | 역할 | 권장 사양 |
|---|---|---|
| **Master-eligible** | 클러스터 상태 관리 | *작은* 사양, *3 노드* (홀수) |
| **Data** | 인덱스 저장 + 검색 | *큰 디스크 + 큰 메모리* |
| **Ingest** | *pipeline* 처리 | 중간 사양, *CPU 위주* |
| **Coordinating** | 쿼리 fan-out / 머지 | *큰 메모리 + 빠른 네트워크* |

*''*마스터가 *data 역할 같이*''* 가 *소규모는 OK*. *대규모는 *분리 필수*.

---

## 5. *Vector Search 의 *현장**

### 5.1 *벡터 검색이 *왜* 이렇게 *까다로운가*

전통적 검색 (BM25) 는 *역인덱스* — *''단어 → 문서 ID''* 의 *해시 같은 구조*. *빠르고 가벼움*.

벡터 검색은:
- *문서당 *768 ~ 1536 차원의 *float 벡터***
- *''*가장 유사한* N 개 찾기''* = *모든 벡터와 *거리 계산** = *brute force = 느림*
- 그래서 **ANN (Approximate Nearest Neighbor)** 알고리즘 — *''*정확히* 가장 가까운* 대신 *''*거의 *가장 가까운*''*

### 5.2 *Elasticsearch 의 *벡터 인덱싱 — HNSW**

Elasticsearch / OpenSearch / Lucene 9+ 의 *기본 ANN 알고리즘* 은 **HNSW (Hierarchical Navigable Small World)**.

```
[L2 layer]      sparse — *고속 큰 점프*
[L1 layer]      medium
[L0 layer]      dense — *최종 정밀 검색*

검색: top layer 부터 *빠르게 접근* → 아래 layer 로 *정밀화*
```

#### 핵심 파라미터 *3 개*

```json
{
  "type": "dense_vector",
  "dims": 1536,
  "index": true,
  "similarity": "cosine",
  "index_options": {
    "type": "hnsw",
    "m": 16,                  # ← 노드 당 연결 수
    "ef_construction": 200    # ← 인덱싱 시 후보 수
  }
}

# 검색 시
"knn": {
  "field": "embedding",
  "query_vector": [...],
  "k": 10,
  "num_candidates": 100       # ← *ef_search* — 검색 시 후보 수
}
```

- **m** (default 16) — *높을수록 *정확도 ↑*, 인덱싱 *느림*, 메모리 ↑*
- **ef_construction** (default 100) — *높을수록 *인덱스 *품질 ↑*, 인덱싱 *느림**
- **num_candidates** (검색 ef_search) — *높을수록 *recall ↑*, 검색 *느림**

### 5.3 *''*벡터 차원이 *오프힙*''* 의 함정

> *''Elasticsearch 가 *OOM 안 나고도 *왜 죽어요?''*''*

답: **HNSW 가 *오프힙 메모리* 를 *과식*** 한다.

- *문서 *100 만 개 × 1536 차원 × float (4 byte)* = *약 6 GB* — *그래프 구조* 까지 합치면 **약 10 GB**
- 이게 *''*JVM 힙이 아닌* 곳''* 에 잡힘 — *OS 가 *직접 관리*
- *모니터링* 시 *jvm heap 만 보면* *''왜 노드가 *죽지?''* — *RSS / 시스템 메모리* 를 *동시에 봐야 함*

> **공식**: *''*벡터 인덱스 메모리 = 문서 수 × dim × 4 byte × (1 + m/2)*''*. *m=16, 1536 차원, 1M 문서* → *약 14 GB*. *노드당 *벡터 인덱스 메모리 + JVM 힙 + OS cache* 가 *시스템 메모리* 안에 *들어가야 함*.

### 5.4 *벡터 *성능 튜닝의 *5 가지 노브**

#### 노브 1 — *차원 줄이기*

- OpenAI `text-embedding-3-small` 의 *기본 1536 → *Matryoshka* 로 *512 까지 줄여도 *품질 90% 유지*
- *차원 1/3 → 메모리 1/3, 검색 1/3 *빠름**

#### 노브 2 — *Quantization*

- **int8 quantization** — *float 32 → int 8* — *메모리 1/4*, *품질 *거의 동일**
- **binary quantization** — *float → 1 bit* — *메모리 1/32*, 품질 *살짝 ↓*
- Elasticsearch 8.13+ / OpenSearch 2.13+ 에서 *기본 지원*

```json
"index_options": {
  "type": "int8_hnsw",   # ← *공식 quantization*
  "m": 16,
  "ef_construction": 200
}
```

#### 노브 3 — *Pre-filter vs Post-filter*

```json
# Pre-filter — *필터 통과한 *후보만* HNSW 탐색*
"knn": {
  "field": "embedding",
  "query_vector": [...],
  "k": 10,
  "filter": { "term": { "category": "electronics" } }
}
```

*''카테고리 *전자제품* 안에서 가장 유사한 *10 개*''* 같은 쿼리는 **pre-filter 가 *수십 배 빠름***. *post-filter (검색 후 거르기)* 는 *''*1000 개 찾고 *990 개 버림*''* 패턴이라 *느림*.

#### 노브 4 — *Hybrid Search* (BM25 + Vector)

- *벡터만* 으로는 *''정확한 단어 매칭''* 을 놓침 (예: 상품 코드, 사람 이름)
- *BM25 만* 으로는 *의미 유사* 를 놓침
- **RRF (Reciprocal Rank Fusion)** 으로 *두 결과를 *지능적으로 머지**

```json
"retriever": {
  "rrf": {
    "retrievers": [
      { "standard": { "query": { "match": { "title": "노트북" } } } },
      { "knn":      { "field": "embedding", "query_vector": [...], "k": 50 } }
    ],
    "rank_window_size": 100,
    "rank_constant": 60
  }
}
```

#### 노브 5 — *Refresh interval 늘리기*

- 벡터 인덱싱은 *세그먼트 merge 비용* 이 *크다*
- 기본 `refresh_interval: 1s` 를 *벡터 인덱스에선 *30s* 이상*
- *''*검색이 *1 초 뒤에 보여야 한다*''* 가 *진짜 요구* 인지 *비즈니스에 확인*

### 5.5 *Elasticsearch vs *pgvector* — *어느 게 답인가*

| | **Elasticsearch** | **pgvector (PostgreSQL)** |
|---|---|---|
| 알고리즘 | HNSW (Lucene) | HNSW, IVFFlat |
| 메모리 | *오프힙*, 큰 클러스터 | *PG shared_buffers* — 작은 데이터셋에 *효율* |
| 운영 | *클러스터 운영 필요* | *기존 PG 운영* 에 *얹기* |
| Hybrid search | *RRF 공식 지원* | *BM25 미지원* (text search 있지만 별도) |
| 적합 | *수천만 ~ 수억 문서* | *수십만 ~ 수백만 문서* |
| 적합 | *전사 검색 플랫폼* | *기존 PG 위에 *작은 RAG* |

> **2026 의 합리적 선택**:
>
> - *벡터 데이터가 *PG 의 다른 테이블과 *조인 필요** → **pgvector**
> - *벡터 + BM25 + 클러스터 규모** → **Elasticsearch / OpenSearch**
> - *AWS 올인 + 운영 인력 부족* → **OpenSearch Service + k-NN plugin**

---

## 6. *현장 사례* — *어떻게 다쳤고, 어떻게 살아났나*

### 6.1 *사례 1 — *''Cluster State 5 GB 마스터 선출 30 초''**

**상황**: 로그 클러스터, *200,000 shard*, *master node 3 대 5 GB heap*

**증상**: *마스터 노드 *재시작* 시 *cluster state sync* 가 *30 초+*. *그 동안 쓰기 전부 *큐 적체*

**원인**: *oversharding* — *daily index × 50 shard × 1 년 = 18,250 shard 만으로* 도 이미 *큰데* *여러 데이터 종류 합쳐* 200K 까지 폭증

**해법**:
- ILM 의 `shrink` 액션으로 *warm/cold 에서 shard 1 개로 *축소**
- *3 ~ 6 개월 이전 인덱스 *삭제* 또는 *frozen tier*
- *Index Template* 에서 *number_of_shards default 1*

### 6.2 *사례 2 — *''Vector 검색이 *갑자기 느려짐*''**

**상황**: 1500 만 문서 × 1536 차원 벡터 검색. 평소 100ms, 어느 날부터 *2 초+*

**증상**: *p99 latency 만 폭증*. p50 은 정상

**원인**: *인덱싱 burst* 로 *segment 가 수백 개로 폭증*. HNSW 가 *segment 마다 *별도 그래프* → *segment 100 개 = 100 번 탐색*

**해법**:
- `index.merge.policy.max_merged_segment` 를 *5 GB → 10 GB* 로 늘림 (큰 세그먼트 허용)
- *야간에 *force_merge* 로 *세그먼트 정리*
- *결과*: p99 *2,000ms → 150ms*

### 6.3 *사례 3 — *''int8 quantization 으로 *비용 4 배 절감*''**

**상황**: OpenSearch Service, m5.4xlarge × 12 대, *월 $14K*

**증상**: *벡터 인덱스가 *RAM 의 80%* 잠식. *축소 불가* 라고 판단*

**해법**:
- *float32 dense_vector → int8_hnsw* 로 *re-index*
- *Recall@10 = 98% → 97%* (거의 영향 없음)
- *클러스터를 *m5.xlarge × 6 대* 로 축소* — *월 $3.5K*

> **인사이트**: *''*벡터 메모리 *= 비용*. *Quantization 은 *2025 년 이후 *기본값*''*.

---

## 7. *2026 권장 출발점*

### 7.1 *새 Elasticsearch 클러스터 시작 시 체크리스트*

- [ ] Master / Data / Coordinating 노드 *역할 분리* — *5 노드부터*
- [ ] JVM 힙 **최대 31 GB**, 시스템 메모리 *50%*
- [ ] *Hot 인덱스 shard 수* — *예상 크기 / 30 GB*
- [ ] *ILM* policy — Hot 7d → Warm 30d → Cold 90d → Delete 365d (시계열 기본)
- [ ] *Rollover alias* — 시계열은 *반드시*
- [ ] *Index Template* 으로 *number_of_shards default 1* 설정
- [ ] *AZ 분산 + awareness* 설정
- [ ] *모니터링* — `_cat/shards`, `_nodes/stats`, *cluster state size*

### 7.2 *벡터 검색 추가 시 체크리스트*

- [ ] *차원 *최소화** — Matryoshka 사용 검토
- [ ] **int8_hnsw 기본** (8.13+, 2.13+)
- [ ] *Filter 가 있는 검색* 은 *반드시* `knn.filter` 사용 (post-filter X)
- [ ] *벡터 인덱스 메모리* = `doc * dim * 4 * (1 + m/2)` *공식으로 사전 계산*
- [ ] *Refresh interval *30s 이상**
- [ ] *Hybrid search* 가 *필요한지* 검증 — RRF 기본
- [ ] *Coordinating node 분리* — 벡터 fan-out 부담

---

## 8. 정리 — *''*상태가 *분산*'' 의 *3 가지 진실*

```
1) Shard 는 *적당히* 쪼개라 — *너무 많으면 *마스터 죽음*, *너무 적으면 *recovery 죽음*
2) 데이터는 *나이* 에 따라 *움직여라* — *Hot 으로만 잡으면 *비용 폭발*
3) 벡터는 *오프힙* 에 산다 — *JVM 힙만 보면 *틀린 진단*, *시스템 메모리 + RSS 도 함께*
```

Elasticsearch 운영의 *진짜 어려움* 은 *''설정값을 *외우기*''* 가 아니라 *''*수많은 설정값이 *서로 영향*'' 을 *체계적으로* 추적하는 *멘탈 모델*. *Shard 수 ↑ → 마스터 부담 ↑*, *벡터 차원 ↑ → 오프힙 ↑*, *force_merge → IO 폭증 → 검색 느려짐* — *연쇄 관계를 *몸으로 익히는 것* 이 *시니어의 차이*.

> **한 줄로**: *''Elasticsearch 는 *데이터의 *물리적 흐름*'' 을 *내가 설계* 해야 하는 시스템 — *RDBMS 처럼 *''내버려둬도 알아서''* 동작하지 않는다*.

기본 *3 축* (Shard 설계, ILM, Vector 튜닝) 을 *처음부터 *알고 설계* 하면 *''운영이 *재밌어진다*''*. 모르고 시작하면 *''*몇 달 뒤 *대수술*''* 이 *기다린다*.

---

## 더 읽으면 좋은 자료

- Elastic 공식 문서, **Shard sizing** + **Index Lifecycle Management** 절
- OpenSearch 공식 문서, **k-NN plugin** + **vector quantization**
- Lucene 9 / 10 release notes — *HNSW 구현 변천사*
- Benchmark — **ANN benchmarks** (ann-benchmarks.com) — *HNSW vs IVF vs ScaNN*
- *Facebook* / *Pinterest* / *Spotify* — *벡터 검색 사례 블로그*
- **pgvector** GitHub — *PG 진영의 답*
- Elastic 블로그, **Reciprocal Rank Fusion in Elasticsearch** — *Hybrid search 의 *공식 정리*
- *OpenAI* / *Cohere* — *Matryoshka 임베딩* 공식 문서
