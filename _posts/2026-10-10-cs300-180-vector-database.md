---
layout: post
title: "[CS300 #180] 벡터 데이터베이스 — 뜻이 가까운 것을 찾는 인덱스"
date: 2026-10-10 21:00:00 +0900
categories: [cs]
tags: [cs300, database, vector-database, ann-search, hnsw]
---

컴퓨터공학 300 주제 시리즈의 180번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

벡터 데이터베이스는 텍스트·이미지 등을 임베딩 모델로 바꾼 고차원 벡터를 저장하고, "질의 벡터와 가장 가까운 k 개"를 근사 최근접 이웃(ANN) 인덱스로 빠르게 찾아 주는 저장소다. 정확도를 조금 내주고 속도를 크게 얻는 거래가 핵심이다.

## 왜 필요한가

역색인 검색은 단어가 일치해야 찾는다. "노트북 화면이 안 켜져요"로 검색하면 "랩톱 디스플레이 무반응 해결" 문서는 겹치는 단어가 없어 놓친다. 뜻은 같은데 말이 다르기 때문이다.

임베딩 모델은 문장을 수백~수천 차원의 숫자 벡터로 바꾸되, 뜻이 비슷한 문장끼리는 벡터 공간에서 가깝게 놓이도록 학습된다. 그러면 "의미 검색"은 "가까운 벡터 찾기"라는 기하 문제가 된다. 대규모 언어 모델에 회사 문서를 찾아 붙여 주는 검색 증강 생성(RAG), 비슷한 상품 추천, 중복 이미지 탐지가 모두 이 문제다.

문제는 규모다. 벡터 1억 개와 질의 하나를 일일이 비교하면 질의마다 1억 번의 내적이 필요하다. 이를 수 밀리초로 줄이는 것이 벡터 인덱스의 역할이다.

## 핵심 개념

### 거리 함수

| 거리 | 정의 | 메모 |
|---|---|---|
| 유클리드(L2) | ‖a − b‖ | 기하적 거리 |
| 내적 | a · b | 클수록 가깝다 |
| 코사인 유사도 | a · b / (‖a‖‖b‖) | 방향만 본다, 텍스트 임베딩에서 흔함 |

벡터를 길이 1 로 정규화해 두면 코사인 유사도와 내적이 같아지고, L2 거리 순위도 같아진다(‖a−b‖² = 2 − 2a·b). 그래서 많은 시스템이 저장 전에 정규화한다. 어떤 거리를 쓸지는 임베딩 모델이 학습된 방식을 따른다.

### 왜 B+트리로는 안 되는가

B+트리는 한 차원의 정렬 순서를 이용한다. 수백 차원에는 그런 순서가 없다. k-d 트리처럼 공간을 나누는 구조도 차원이 높아지면 거의 모든 칸을 뒤져야 해 풀 스캔과 다를 바 없어진다. 이를 **차원의 저주**라 한다. 그래서 고차원에서는 정확한 답을 포기하고 **근사 최근접 이웃(ANN)** 을 찾는다. 품질은 **재현율(recall@k)**, 즉 "진짜 상위 k 개 중 몇 개를 찾았는가"로 잰다.

### IVF: 칸을 나누고 일부만 뒤진다

```
1. 학습: 표본 벡터로 k-means 를 돌려 중심점 nlist 개를 구한다.
2. 색인: 각 벡터를 가장 가까운 중심점의 목록(inverted list)에 넣는다.
3. 질의: 질의와 가까운 중심점 nprobe 개를 고르고, 그 목록 안의 벡터만 정확히 비교한다.

      ·  ·    │  ·     ·        ← 공간이 중심점 기준 칸(보로노이 셀)으로 나뉨
   ·  (C1) ·  │   (C2)  ·
  ────────────┼──────────────
     ·  ·  ★  │   ·   ·        ★ 질의: C3 와 (경계 근처라) C1 도 뒤진다
   (C3)   ·   │  (C4)  ·
```

`nprobe` 를 늘리면 재현율이 오르고 속도는 떨어진다. 이 이름의 "inverted list" 는 역색인과 같은 발상이다. 단어 대신 "가장 가까운 중심점"이 키다. FAISS 라이브러리(Johnson 등, 2017)가 이 계열의 대표 구현이며, 벡터를 압축하는 곱 양자화(PQ)와 결합해 메모리를 줄인다.

### HNSW: 계층형 근접 그래프

Malkov 와 Yashunin 이 2016년 arXiv 에 공개한 HNSW(Hierarchical Navigable Small World)는 벡터를 노드로, 가까운 이웃을 간선으로 하는 그래프를 여러 층으로 쌓는다.

```
층 2:  A ─────────────────── F            (노드 적음, 먼 거리 점프)
층 1:  A ──── C ──────── F ──── H
층 0:  A─B─C─D─E─F─G─H─I─J─K            (모든 노드, 가까운 이웃)

검색: 꼭대기 층의 진입점에서 출발 → 그 층에서 질의에 더 가까운 이웃으로
      계속 이동(탐욕) → 더 못 가면 한 층 내려가 반복 → 0층에서 후보 ef 개 유지
```

스킵 리스트와 비슷한 구조다. 위층에서 크게 건너뛰고 아래층에서 정밀하게 찾는다. 일반적으로 IVF 보다 속도–재현율 균형이 좋지만, 그래프를 메모리에 두어야 해 메모리를 더 쓰고 구축이 느리다. 주요 매개변수는 노드당 연결 수 `m`, 구축 시 후보 수 `ef_construction`, 검색 시 후보 수 `ef_search` 다.

### 벡터 DB 가 하는 일

ANN 인덱스는 라이브러리로도 쓸 수 있다. 벡터 "데이터베이스"는 그 위에 DB 의 일을 더한다.

- 벡터와 함께 메타데이터(작성일, 권한, 카테고리) 저장
- **필터와 결합한 검색**: "우리 팀 문서 중에서 가까운 것". 필터를 인덱스 검색 뒤에 적용하면 결과가 모자랄 수 있어 까다롭다.
- 삽입·삭제·갱신, 영속성, 복제, 백업
- **하이브리드 검색**: BM25 키워드 점수와 벡터 유사도를 함께 써서 순위를 매기기

전용 제품(Milvus, Qdrant, Weaviate 등)도 있고, 기존 DB 의 확장도 있다. PostgreSQL 의 pgvector 확장은 `vector` 타입과 HNSW·IVFFlat 인덱스를 제공해, 벡터를 일반 테이블 열로 저장하고 SQL 로 조인·필터한다.

```sql
CREATE EXTENSION vector;
CREATE TABLE docs (id bigserial PRIMARY KEY, team text, body text, embedding vector(768));
CREATE INDEX ON docs USING hnsw (embedding vector_cosine_ops);
SELECT id, body FROM docs WHERE team = 'infra'
ORDER BY embedding <=> $1 LIMIT 5;      -- <=> 는 코사인 거리, <-> 는 L2, <#> 는 음의 내적
```

pgvector 문서에 따르면 HNSW 의 `m` 기본값은 16, `ef_construction` 은 64, 검색 시 `hnsw.ef_search` 는 40 이다. IVFFlat 은 `ivfflat.probes` 기본값이 1 이며, 시작점으로 `lists` 는 100만 행까지 `행 수 / 1000`, `probes` 는 `sqrt(lists)` 를 권한다. 또 근사 인덱스에서는 `WHERE` 필터가 인덱스 스캔 **뒤에** 적용되므로, 조건이 행의 10% 만 맞으면 기본 `ef_search` 40 에서 평균 4개만 남을 수 있다고 경고한다.

## 직접 해 보기

NumPy 로 10만 개의 64차원 벡터를 만들고, 정확한 검색과 IVF 근사 검색의 비교 횟수·시간·재현율을 비교한다. 실제 임베딩 대신 주제 200개 주변에 모인 합성 벡터를 썼다.

```python
import numpy as np, time

rng = np.random.default_rng(42)
DIM, N, TOPICS = 64, 100_000, 200
unit = lambda m: m / np.linalg.norm(m, axis=-1, keepdims=True)

# 군집이 있는 가짜 임베딩: 주제 200개 주변에 문서 10만 개가 흩어져 있다
topics = unit(rng.normal(size=(TOPICS, DIM)))
data = unit(topics[rng.integers(TOPICS, size=N)] + rng.normal(scale=0.08, size=(N, DIM)))
queries = unit(topics[rng.integers(TOPICS, size=100)] + rng.normal(scale=0.08, size=(100, DIM)))

def exact_top10(q):                          # 정규화했으므로 코사인 유사도 = 내적
    return set(np.argsort(-(data @ q))[:10])

# IVF: k-means 로 nlist 개의 칸(Voronoi 셀)을 만들고 벡터를 가장 가까운 칸에 넣는다
def kmeans(x, k, iters=10):
    c = x[rng.choice(len(x), k, replace=False)]
    for _ in range(iters):
        assign = np.argmax(x @ c.T, axis=1)
        c = unit(np.stack([x[assign == j].sum(0) if (assign == j).any() else c[j] for j in range(k)]))
    return c
NLIST = 256
cents = kmeans(data[rng.choice(N, 20_000, replace=False)], NLIST)
assign = np.argmax(data @ cents.T, axis=1)
lists = [np.where(assign == j)[0] for j in range(NLIST)]

def ivf_top10(q, nprobe):
    probe = np.argsort(-(cents @ q))[:nprobe]          # 질의와 가까운 칸 nprobe 개만
    cand = np.concatenate([lists[j] for j in probe])
    return set(cand[np.argsort(-(data[cand] @ q))[:10]]), len(cand)

truth = [exact_top10(q) for q in queries]
t = time.perf_counter(); [exact_top10(q) for q in queries]
print(f"정확 검색   : 질의당 비교 {N:>6}개, {(time.perf_counter()-t)*10:.2f} ms/질의")
for nprobe in (1, 4, 16):
    t = time.perf_counter()
    res = [ivf_top10(q, nprobe) for q in queries]
    dt = (time.perf_counter() - t) * 10
    recall = np.mean([len(r & tr) / 10 for (r, _), tr in zip(res, truth)])
    scanned = np.mean([s for _, s in res])
    print(f"IVF nprobe={nprobe:>2}: 질의당 비교 {scanned:>6.0f}개, {dt:.2f} ms/질의, recall@10 = {recall:.2f}")
```

한 번 실행한 결과(NumPy 1.26, 시간은 기기마다 다르다):

```
정확 검색   : 질의당 비교 100000개, 27.21 ms/질의
IVF nprobe= 1: 질의당 비교    483개, 0.47 ms/질의, recall@10 = 0.96
IVF nprobe= 4: 질의당 비교   1626개, 0.95 ms/질의, recall@10 = 1.00
IVF nprobe=16: 질의당 비교   6323개, 5.55 ms/질의, recall@10 = 1.00
```

`nprobe=1` 만으로 비교 대상이 10만 개에서 약 500개로 줄었고, 진짜 상위 10개 중 평균 9.6개를 찾았다. `nprobe` 를 늘리면 재현율은 오르고 비교 수와 시간도 늘어난다. 이 합성 데이터는 군집이 아주 뚜렷해서 재현율이 실제보다 후하게 나온다. 실제 임베딩은 경계가 흐릿해 같은 `nprobe` 에서 재현율이 더 낮은 경우가 많으므로, 자기 데이터로 재현율과 지연을 함께 재서 매개변수를 정해야 한다.

## 현업에서는

- **RAG 품질은 인덱스보다 앞단에서 갈린다**: 문서를 어떤 크기로 자르는지(청킹), 어떤 임베딩 모델을 쓰는지, 키워드 검색과 섞는지가 ANN 매개변수보다 결과에 더 큰 영향을 주는 경우가 많다. 검색 품질은 질문–정답 문서 쌍을 모아 재현율로 측정한다.
- **임베딩 모델을 바꾸면 전부 다시 계산**: 모델이 다르면 벡터 공간이 다르므로 옛 벡터와 새 벡터를 섞을 수 없다. 재색인 비용과 이중 운영 기간을 계획에 넣는다. 저장할 때 모델 이름과 버전을 함께 기록해 두면 혼선을 막는다.
- **"이미 Postgres 가 있다면"**: 벡터 수가 수백만 개 수준이고 메타데이터 조인·권한 필터가 중요하다면, pgvector 로 기존 DB 안에서 시작하는 선택이 운영 부담이 적다. 홈랩 k3s 위의 PostgreSQL 파드에 확장 하나만 추가하면 된다. 규모와 지연 요구가 커지면 전용 엔진을 검토한다.
- **메모리 계산**: 768차원 float32 벡터 하나는 768 × 4 = 3,072 바이트다. 1,000만 개면 원본만 약 30GB 이고, HNSW 그래프 간선이 더해진다. 반정밀도(halfvec)나 양자화로 줄이는 이유다.

## 확인 문제

1. 벡터를 길이 1 로 정규화하면 코사인 유사도와 내적의 관계는 어떻게 되는가?
2. 고차원 벡터 검색에 B+트리나 k-d 트리가 잘 맞지 않는 이유는?
3. IVF 에서 `nprobe` 를 늘리면 무엇이 좋아지고 무엇이 나빠지는가?
4. HNSW 가 위층에서 아래층으로 내려가며 검색하는 이유를 스킵 리스트와 비교해 설명하라.
5. 근사 인덱스 검색 뒤에 `WHERE team = 'infra'` 필터를 적용하면 어떤 문제가 생길 수 있는가?

### 풀이

1. 같아진다. 코사인 유사도의 분모가 1 이 되기 때문이다.
2. B+트리는 한 차원의 정렬 순서에 기대는데 고차원에는 유용한 단일 순서가 없고, 공간 분할 트리는 차원이 높아지면 거의 모든 칸을 뒤져야 하는 차원의 저주에 빠진다.
3. 재현율은 오르고, 비교할 벡터 수와 지연 시간은 늘어난다.
4. 위층은 노드가 적고 간선이 길어 질의 근처로 빠르게 이동하고, 아래층으로 갈수록 노드가 촘촘해 정밀하게 찾는다. 스킵 리스트가 위 레벨에서 크게 건너뛰고 아래 레벨에서 세밀하게 찾는 것과 같다.
5. 인덱스가 돌려준 후보(예: `ef_search` 개) 중 필터를 통과하는 것만 남아, 요청한 개수보다 적은 결과가 나올 수 있다.

## 더 읽을거리 (References)

- Yu. A. Malkov, D. A. Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs", [arXiv:1603.09320](https://arxiv.org/abs/1603.09320)
- J. Johnson, M. Douze, H. Jégou, "Billion-scale similarity search with GPUs", [arXiv:1702.08734](https://arxiv.org/abs/1702.08734); [FAISS](https://faiss.ai/)
- pgvector 공식 저장소, [README](https://github.com/pgvector/pgvector) — 연산자, HNSW·IVFFlat 매개변수와 기본값
