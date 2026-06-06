---
layout: post
title: "Chunking → Embedding → Search → LLM — *앞 단계의 결정이 뒷 단계를 묶는다*: RAG 효율화 4 축과 벡터 DB·LLM 의 진짜 관계"
date: 2026-05-29 01:10:00 +0900
categories: [ai, rag, vector-database, llm]
tags: [rag, chunking, embedding, vector-db, semantic-search, llm, hybrid-search, reranking, pgvector, qdrant, hnsw]
---

> *''Garbage in, garbage out''* — RAG 시스템에서 이 격언은 *층층이* 작동한다. **Chunking 에서 잘못 자르면 Embedding 이 의미를 못 잡고, Embedding 이 흐릿하면 Vector DB 가 검색을 못 하고, 검색이 부정확하면 LLM 이 *환각 (hallucination)* 한다.** 네 단계는 *독립* 이 아니라 *체인* 이다. *한 단계의 결정* 이 *다음 세 단계를 묶는다*.

이 글은 *RAG 의 4 단계 파이프라인* — *Chunking → Embedding → Search → LLM* — 을 *''각 단계의 결정이 어떻게 서로를 묶는가''* 라는 시선으로 다시 짚는다. *효율화의 4 축* (비용·지연·정확도·메모리), *벡터 DB 의 진짜 역할*, *LLM 의 context window 가 어떻게 *위쪽 모든 결정을* 강제하는지* — 인터넷의 RAG 튜토리얼이 *''각 단계 따로따로''* 설명하느라 놓치는 *연결성* 을 집어본다.

---

## 1. RAG 의 *4 단계 파이프라인* — *왜 따로 분리됐나*

RAG (*Retrieval-Augmented Generation*) 라는 단어가 처음 등장한 건 2020 년 Facebook AI 의 *''Retrieval-Augmented Generation for Knowledge-Intensive NLP''* 논문이지만, *대중적 의미의 RAG* — *''LLM 에 외부 문서 컨텍스트를 넣어주는 패턴''* — 은 2023 년 GPT-4 + LangChain 의 폭발과 함께 *디폴트 아키텍처* 가 되었다.

파이프라인은 단순해 보인다:

```
[문서] → Chunking → Embedding → Vector DB
                                    ↓
[질문] → Embedding ───────────────→ Search (Top-K) → LLM → 답변
```

그러나 *''단순해 보임''* 이 *''쉽다''* 와 같지 않다. *각 단계의 선택* 이 *나머지 단계를 강제* 한다:

- **Chunk size 결정** → embedding 모델의 *최대 토큰* 을 알아야 함
- **Embedding 모델 결정** → vector DB 의 *차원 (dimension)* 을 결정. 나중에 못 바꿈
- **Vector DB 결정** → search 의 *최대 K, latency, 비용* 을 결정
- **LLM 결정** → *context window 크기 = 우리가 retrieve 할 수 있는 chunk 수의 상한*

*''뒤로 갈수록 앞을 결정한다''* — 그래서 RAG 설계는 *역방향* 으로 한다. *''LLM 이 무엇을 입력 받을 수 있나''* 부터 정한 뒤, 거꾸로 chunk 크기까지 내려온다.

## 2. *Chunking* — *문장 한 줄의 결정* 이 *전체 시스템* 을 묶는다

### 2.1. *왜 자르나*

LLM 의 context window 는 *유한* 하다 (GPT-4o = 128K, Claude Opus 4.7 = 1M, Gemini 2.5 = 2M). *문서 한 권* 을 통째로 못 넣는다. *''관련된 부분만''* 잘라서 넣어야 한다. 그래서 *''자르고 → 검색하고 → 관련 조각만 LLM 에''* 가 RAG 의 본체다.

### 2.2. *Chunking 전략 비교*

| 전략 | 작동 방식 | 강점 | 약점 |
|---|---|---|---|
| **Fixed-size** | *글자 N 개씩* 자름 | 단순, 빠름 | 문장·문단 중간에서 잘림 |
| **Recursive character** | *문단 → 문장 → 단어* 순으로 점점 잘게 | 자연스러운 경계 | 길이 불균등 |
| **Semantic chunking** | *연속 문장의 embedding 거리* 가 멀어지는 지점에서 자름 | *의미 단위* 보존 | 느림, embedding 한 번 더 필요 |
| **Document-structure** | *Markdown #, HTML \<h\>, code function* 단위 | *문서의 자연 구조* 활용 | 형식 의존 |
| **Hierarchical / Parent-child** | *작게 자르되 부모-자식 관계 유지* | 정확도와 컨텍스트 둘 다 잡음 | 인덱스 2 배 |

### 2.3. *Chunk size 의 *진짜* trade-off*

*chunk 가 작을수록* — *''검색 정확도''* 가 올라간다. 작은 단위로 자르면 *''정확히 그 문장만''* 찾을 수 있다. 그러나 *''검색된 결과의 컨텍스트''* 가 부족해진다. *''that''* 이 가리키는 *''what''* 이 같은 chunk 에 없을 수 있다.

*chunk 가 클수록* — *컨텍스트는 풍부* 하지만 *embedding 의 *의미 평균화*** 가 일어난다. *''한 chunk 안에 5 가지 주제''* 가 섞이면 *embedding 벡터* 가 *모든 주제의 평균* 이 되어 *어떤 주제에도 정확하게 매칭되지 않는다*.

**경험적 sweet spot** — *256~512 토큰 + 50~100 토큰 overlap*. 그러나 이것도 *문서 종류* 에 따라 다르다. *''법률 문서''* 는 *조항 단위* (의미 단위가 커서) 1,000 토큰도 OK. *''Q&A 게시판''* 은 *각 답변 단위* 100~200 토큰. *''코드베이스''* 는 *함수 단위*.

### 2.4. *Overlap 의 의미*

*overlap = chunk 간 겹치는 토큰 수*. *''경계에서 잘린 의미를 보존''* 하기 위함. *''첫 chunk 끝의 50 토큰''* 이 *''두 번째 chunk 시작의 50 토큰''* 과 같다. *검색 시* *어느 쪽이 retrieve 되더라도* *경계 정보는 들어있다*.

다만 *overlap 이 크면* — *동일 의미가 여러 chunk 에 중복 인덱스* 되어 *Top-K 가 같은 내용으로 채워진다*. *MMR (Maximal Marginal Relevance)* 같은 *다양성 검색* 으로 보완 가능하지만, *원천적으로 chunk 설계가 잘못된 신호*.

## 3. *Embedding* — *의미를 수학으로*

### 3.1. *Embedding 의 본질*

*Embedding* 은 *''텍스트 → 벡터''* 의 함수다. *''비슷한 의미의 텍스트는 가까운 벡터''* 가 되도록 *학습된 모델* 이 만든다. *cosine similarity, dot product, L2 distance* 같은 *수학적 거리* 가 *의미적 유사도* 의 *대체값* 이 된다.

*이게 작동하는 *이유* 는 *학습 시* *''비슷한 문장 쌍''* 과 *''다른 문장 쌍''* 을 *contrastive learning* 으로 가르쳤기 때문이다. *Sentence-BERT (2019)* 가 표준화한 이 패러다임이 *모든 현대 embedding 모델의 기반*.

### 3.2. *Dense vs Sparse — 두 가지 의미 표현*

| 종류 | 예 | 작동 | 특성 |
|---|---|---|---|
| **Dense** | OpenAI text-embedding-3, BGE, E5 | 1,536 차원 *실수* 벡터 | *의미적 유사성* 강함, *희귀어* 약함 |
| **Sparse** | BM25, SPLADE | 어휘 사전 크기 *희소* 벡터 | *키워드 매칭* 정확, *paraphrase* 약함 |

*현실의 RAG 는 *둘 다 쓴다* (hybrid). *''사용자 이름''* 처럼 *정확한 매칭이 필요한 토큰* 은 BM25 가, *''로그인 안 됨''* 처럼 *의미적 매칭이 필요한 phrase* 는 dense 가 잡는다.

### 3.3. *Embedding 모델 선택의 무게*

*한 번 선택하면 *바꾸기 힘들다*. 이유:

1. *차원이 다름* — text-embedding-3-small = 1,536, BGE-large = 1,024, Cohere embed-v3 = 1,024. *벡터 DB 의 인덱스 차원이 박혀있어서 *전부 재인덱싱* 필요*
2. *벡터 공간이 다름* — A 모델로 만든 벡터와 B 모델로 만든 벡터는 *비교 불가*. *전체 재임베딩* 필요
3. *비용이 크다* — 1 백만 chunks * embedding API = *수십~수백만원*. 자주 못 바꿈

### 3.4. *2026 년 현재 주요 embedding 모델*

| 모델 | 차원 | 비용 / 1M tokens | 강점 |
|---|---|---|---|
| OpenAI text-embedding-3-small | 1,536 | $0.02 | 가성비 |
| OpenAI text-embedding-3-large | 3,072 | $0.13 | 최고 정확도 |
| Cohere embed-v3 | 1,024 | $0.10 | 다국어, 압축 가능 |
| Voyage AI voyage-3 | 1,024 | $0.10 | code, finance 특화 |
| **BGE-M3** (오픈소스) | 1,024 | *self-host 무료* | dense+sparse+colbert 통합 |
| **E5-mistral-7b** (오픈소스) | 4,096 | *self-host* | SOTA on MTEB, 무겁다 |

*self-host vs API* 의 *진짜 손익분기점* — *월 임베딩 양 100 만 토큰 미만* 이면 API 가 *압도적으로 쌈*. *그 이상* 이면 *GPU 한 장 + BGE-M3* 가 *더 싸고 더 빠름*.

## 4. *Vector DB* — *유사도 검색의 인프라*

### 4.1. *''왜 일반 DB 가 안 되나''*

100 만 개 벡터 (1,536 차원) 중에서 *''질문 벡터와 가장 가까운 10 개''* 를 찾으려면 *brute-force* 로는 *1.5GB 메모리 한 번 통째로 스캔*. 한 검색에 *수 백 ms~수 초*. *production 에선 불가*.

**ANN (Approximate Nearest Neighbor)** 알고리즘이 답이다. *''완벽한 top-10 이 아니라 *''아마 top-10 일 것''* 을 찾는다''*. 정확도 95~99% 를 유지하면서 *수 백 배 빠르다*.

### 4.2. *ANN 알고리즘 비교*

| 알고리즘 | 메모리 | 빌드 시간 | 쿼리 속도 | 정확도 |
|---|---|---|---|---|
| **HNSW** (대중적) | 높음 | 느림 | *매우 빠름* | 95~99% |
| **IVF** (Faiss) | 중간 | 빠름 | 중간 | 가변 |
| **DiskANN** (MS) | *낮음* (디스크) | 느림 | 빠름 | 95% |
| **ScaNN** (Google) | 중간 | 중간 | 빠름 | 98% |
| **PQ (Product Quantization)** | *극히 낮음* | 느림 | 빠름 | 80~90% |

*HNSW* 가 *현재 표준* — *Hierarchical Navigable Small World*. *그래프 기반*. 메모리 많이 먹지만 *''millions 단위에선 ms 단위 응답''*. *''billions 단위''* 가 되면 *DiskANN* 이 살아남는다.

### 4.3. *주요 Vector DB 비교 (2026)*

| DB | 모델 | 장점 | 단점 |
|---|---|---|---|
| **Pinecone** | 매니지드 SaaS | 운영 부담 0 | 비쌈, lock-in |
| **Qdrant** | 오픈소스 + Cloud | 빠름, payload 풍부 | 운영 부담 |
| **Weaviate** | 오픈소스 + Cloud | GraphQL, multi-modal | 학습 곡선 |
| **Milvus / Zilliz** | 오픈소스 (대규모) | *billions 스케일* | 무거움 |
| **pgvector** | Postgres 확장 | *기존 RDB 와 통합* | 거대 스케일에 약함 |
| **Chroma** | 임베디드 | *prototyping 최적* | production 비추 |
| **OpenSearch / Elastic** | 검색엔진 + 벡터 | hybrid 자연스러움 | 무거움 |

**선택 기준** — *''DB 한 개로 RAG + transactional''* 이면 **pgvector**. *''순수 벡터 검색 + 빠름''* 이면 **Qdrant**. *''운영 부담 0 + 돈 OK''* 면 **Pinecone**. *''10 억 벡터 이상''* 이면 **Milvus**.

### 4.4. *pgvector 가 *떠오르는 이유**

2024~2026 년 사이 *pgvector 채택* 이 폭증했다. 이유:

1. *''DB 가 하나면 좋다''* — 사용자 메타데이터·권한·트랜잭션이 *같은 Postgres* 에 있음. *join 가능*
2. *HNSW 인덱스 지원 (0.5.0+)* — 성능이 *''전용 DB 와 격차가 좁혀짐''*
3. *AWS Aurora, Supabase, Neon* 등이 *기본 활성화*

*단점* — *수 천만 벡터까지는 OK*, *그 이상엔 부담*. *''작은~중간 RAG 는 pgvector, 대규모는 Qdrant/Milvus''* 가 현재 합의.

## 5. *Search* — *Top-K 가 답이 아니다*

### 5.1. *Top-K 의 한계*

*''K 개를 더 가져오면 정답이 들어있을 가능성 높다''* — 부분적으로 맞다. 그러나 *K 가 커지면*:

1. *LLM context 가 차서 *비싸진다**
2. *관련 없는 chunk 가 *노이즈* 가 됨 (lost-in-the-middle 현상)
3. *LLM 이 *어느 chunk 가 정답인지* 못 고름*

### 5.2. *Hybrid Search* — Dense + Sparse 의 결혼

*Reciprocal Rank Fusion (RRF)* 같은 방법으로 *''BM25 의 top-K 와 dense 의 top-K 를 합쳐 ranking''*. *대부분의 production RAG 가 이 패턴*. *순수 dense* 보다 *15~30% 정확도 향상* (Pinecone, Vespa 벤치마크).

### 5.3. *Reranking* — *Cross-encoder 의 두 번째 패스*

*Retrieval 은 *bi-encoder* — 질문과 문서를 *따로* 임베딩. 빠르지만 *정밀도* 한계. *Reranking* 은 *cross-encoder* — *''(질문, 문서)''* 를 *함께* 본 뒤 *''관련도 점수''* 를 계산. *느리지만 정확*.

**전형적 패턴**:
1. Vector DB 에서 *top-50* retrieval (bi-encoder, 50ms)
2. *Cohere Rerank, Voyage rerank-2, BGE-reranker* 같은 모델로 *top-50 → top-10* (cross-encoder, 100ms)
3. *top-10* 만 LLM 에 전달

*추가 비용 150ms* 로 *정확도 20~40% 점프*. 2026 년 RAG 의 *''반드시 해야 하는 단계''*.

### 5.4. *MMR — 다양성*

*Maximal Marginal Relevance* — *''관련성도 보고 *다양성도* 본다''*. *Top-K 가 *전부 같은 문장의 paraphrase* 가 되는 것을 방지*. *Chunking overlap* 이 만든 중복을 사후에 보정.

## 6. *효율화의 4 축* — *비용·지연·정확도·메모리* 의 상충

RAG 의 *''잘 만든다''* 는 단일 지표가 아니다. *4 가지 축* 의 *균형*:

| 축 | 영향 인자 | 줄이는 법 |
|---|---|---|
| **비용** | embedding API, LLM token, DB 호스팅 | *chunk 압축, 작은 embedding 모델, query caching* |
| **지연** | embedding(질문), DB 쿼리, reranker, LLM | *작은 reranker, 적은 K, 저차원 임베딩* |
| **정확도** | recall@K, MRR, NDCG | *hybrid, reranker, chunk 설계* |
| **메모리** | 인덱스 RAM 사용 | *PQ 양자화, DiskANN, 차원 축소* |

*하나를 늘리면 다른 게 깎인다*. *''비용 줄이려고 작은 embedding 쓰면 정확도 떨어진다''*. *''정확도 올리려고 K 늘리면 LLM 비용 폭증''*. *''메모리 줄이려고 양자화하면 정확도 -5%''*.

*production 의 진짜 일* 은 *''내 use case 의 *''허용 가능한 trade-off''*''* 를 찾는 것. *법률 검색* 은 *정확도 최우선*. *고객 챗봇* 은 *지연 최우선*. *''내부 위키 RAG''* 는 *비용 최우선*.

## 7. *LLM 과의 *상호 관계* — Context Window 가 *위쪽 전부* 를 강제한다

*''Long-context LLM 이 나오면 RAG 가 필요 없어진다''* 는 주장이 있다. *반은 맞고 반은 틀리다*. Gemini 2.5 의 2M 토큰 window 에 *책 5 권* 을 넣을 수 있다. 그러나:

1. *비용* — 2M 토큰 input = *Claude Opus 4.7 기준 $30/1 회 호출*. *문서당 매번 그 비용은 비현실*
2. *Lost in the middle* — *Liu et al. 2023* 이 보여준 현상: *long context 의 *''중간''* 에 있는 정보를 LLM 이 *잘 못 본다*. *''앞과 뒤''* 만 잘 본다*. RAG 의 *''관련된 부분만 골라서 넣는다''* 가 *오히려 더 정확한 결과*
3. *지연* — 2M 토큰 처리 latency = *수십 초*. *실시간 챗봇 안 됨*

결론 — *''long-context LLM 이 *RAG 를 죽이는* 게 아니라 *RAG 의 어려운 부분 (chunking) 을 *덜 까다롭게* 한다''*. *더 큰 chunk, 더 적은 chunk 수, 더 풍부한 context* 가 가능해지지만, *''검색이라는 단계 자체''* 는 사라지지 않는다.

## 8. *실전 — 흔한 실수*

1. ***Embedding 모델을 *나중에* 바꿀 수 있을 거라 생각** — 못 바꾼다. *''첫 선택이 평생''*. *벤치마크 충분히 한 뒤* 결정
2. **Chunk size 를 *처음부터 작게* 설정** — *''256 으로 하면 빠르겠지''* 식 결정. *실제로는 *문서 종류* 마다 다름*
3. **Reranker 없이 production** — 2026 년 기준 *reranker 없는 RAG = 절반 짜리*
4. **Hybrid search 안 함** — *키워드 매칭* 이 필요한 도메인 (코드, 이름, 숫자) 에서 dense-only 는 *재앙*
5. **Metadata 필터 안 씀** — *시간, 카테고리, 권한* 같은 *''structured filter + vector search''* 가 *production 의 정석*. 그냥 top-K 뿌리지 말 것
6. **Evaluation 없이 운영** — *''좋아보임''* 으로 결정하지 말 것. *Ragas, TruLens, DeepEval* 같은 *자동 평가* 셋업

## 9. *2026~ 의 방향*

- **GraphRAG** — Microsoft 의 *''vector + knowledge graph''* 패턴. *추론* 이 필요한 질문에 vector 만으론 부족할 때
- **Agentic RAG** — *''한 번 검색하고 끝''* 이 아니라 *''agent 가 *반복 검색* + *self-correction*''*
- **ColBERT v2, ColPali** — *late interaction* — *문서를 *''여러 벡터''* 로 표현*. 정확도 압도적, 비용 증가
- **Multimodal RAG** — *이미지·표·차트* 도 같은 벡터 공간에. *CLIP, ColPali* 가 시작
- **On-device RAG** — *Llama 3.2 1B + sqlite-vec* 같은 *''핸드폰 안의 RAG''*
- **Reranking 의 표준화** — *Cohere, Voyage, BGE* 의 *''reranker-as-a-service''* 가 *RAG 의 *디폴트 단계*

## 10. 정리 — *''각 단계가 *서로를 묶는다*''*

RAG 시스템은 *''4 개의 자유로운 선택''* 이 아니다. *''4 개의 *서로 묶인* 선택''* 이다:

- **LLM 의 context window** 가 *retrieve 할 chunk 수의 상한*
- **Embedding 모델** 이 *vector DB 의 차원 + 비용 곡선*
- **Chunk 크기** 가 *embedding 의 의미 해상도 + retrieval 정확도*
- **Vector DB** 가 *latency + 메모리 + 확장성*

*제일 흔한 실패 모드* 는 *''각 단계를 *튜토리얼대로* 따로 결정''* 하는 것. *''chunk 512, BGE-large, Qdrant, GPT-4''* 라는 *기본값 세팅* 으로 시작해서 *전체를 측정해본 뒤* — *''내 도메인에선 어디가 *병목인가''*''* 를 찾아 *축 별로* 조정하는 게 *진짜 일*.

> *''RAG 는 *''벡터 DB 한 개 깔면 끝''* 이 아니다. *''파이프라인 전체의 trade-off 를 본인 도메인에 맞춰 *조율* 하는 것''*. 그래서 *RAG 엔지니어* 라는 직군이 생겼다.''

---

## 더 읽을 거리

- *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* — Lewis et al., 2020 (RAG 원논문)
- *Lost in the Middle: How Language Models Use Long Contexts* — Liu et al., 2023
- *Sentence-BERT* — Reimers & Gurevych, 2019 (현대 embedding 의 시작)
- *Microsoft GraphRAG* — *https://github.com/microsoft/graphrag*
- *MTEB Leaderboard* — *embedding 모델 비교의 표준* — *https://huggingface.co/spaces/mteb/leaderboard*
- *Pinecone Learn* — *https://www.pinecone.io/learn/* (실전 가이드 모음)
- *Anthropic 의 Contextual Retrieval* — *''chunk 에 LLM 으로 context 를 *prepend*''* 라는 신선한 접근

*다음 글 예고: lemuel-xr 의 vector RAG 실전 — pgvector + BGE-M3 + Cohere Rerank 로 묵상 검색을 어떻게 튜닝했는가*
