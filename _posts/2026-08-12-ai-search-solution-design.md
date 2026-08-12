---
layout: post
title: "신규 AI 검색 솔루션 구축 — 요구사항 분석부터 아키텍처 설계까지"
date: 2026-08-12 21:35:00 +0900
categories: [AI, 검색]
tags:
  [
    검색,
    하이브리드검색,
    BM25,
    벡터검색,
    RRF,
    리랭킹,
    Elasticsearch,
    pgvector,
    한국어검색,
    검색평가,
  ]
---

"AI 검색 붙여주세요"라는 요구가 들어오면 대개 벡터 DB부터 고른다. 그런데 검색 품질을 결정하는 건 벡터 DB 선택이 아니라 **무엇을 정답으로 볼 것인지 정의했는가**다. 정답 정의가 없으면 어떤 엔진을 골라도 개선 여부를 알 수 없다.

이 글은 신규 AI 검색 솔루션을 처음부터 설계할 때의 분석·설계 문서다. 범위는 **검색(retrieval·ranking)** 에 한정한다. 검색 결과로 답변을 생성하는 RAG 합성 단계, 문서에서 텍스트를 뽑아내는 OCR 단계는 다루지 않는다. 그 앞뒤 단계가 아무리 좋아도 검색이 틀린 문서를 물어오면 전체가 무너지기 때문에, 가운데 토막만 따로 떼어 설계한다.

인용한 수치는 모두 1차 자료(공식 문서·논문·벤더 자체 발표)로 표시했고, 벤더 자체 측정치는 "벤더 주장"으로 라벨을 붙였다.

---

## 1. 먼저 질의를 분류한다 — 요구사항 분석

설계의 출발점은 데이터가 아니라 **질의**다. 사용자가 실제로 던지는 질의를 유형별로 나누면, 필요한 검색 방식이 자동으로 결정된다.

| 질의 유형          | 예시                                  | 필요한 능력    | 렉시컬(BM25)     | 벡터(임베딩)           |
| ------------------ | ------------------------------------- | -------------- | ---------------- | ---------------------- |
| 식별자·정확 일치   | `ERR-4021`, `KafkaErrorHandlerConfig` | 정확 토큰 매칭 | ◎                | △ (놓치기 쉬움)        |
| 개념·자연어        | "정산이 왜 밀렸지"                    | 의미 유사도    | △                | ◎                      |
| 동의어·표기 흔들림 | "송장" / "인보이스"                   | 어휘 확장      | △ (사전 필요)    | ○                      |
| 오탈자             | "카프까 리밸런싱"                     | 퍼지 매칭      | ○ (fuzziness)    | ○                      |
| 필터 + 정렬        | "최근 7일, 정산팀 문서만"             | 구조화 필터    | ◎                | 필터 결합이 함정 (5절) |
| 롱테일 전문용어    | 사내 약어, 제품 코드                  | 도메인 사전    | ◎ (사전 등록 시) | × (학습에 없음)        |

여기서 바로 나오는 결론이 하나 있다. **어느 한쪽만으로는 안 된다.** 임베딩 모델은 의미를 잘 잡지만 정확 일치를 놓치고, BM25는 정확 일치는 확실하지만 표현이 다르면 못 찾는다. Anthropic도 같은 지점을 지적한다 — 임베딩 모델은 의미 관계를 잘 잡지만 "중요한 정확 일치를 놓칠 수 있고", BM25는 고유 식별자나 기술 용어가 포함된 질의에 특히 효과적이라는 것이다([Anthropic, Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)).

### 비기능 요구사항도 같이 못 박는다

| 항목             | 설계 목표(예시)                    | 이유                            |
| ---------------- | ---------------------------------- | ------------------------------- |
| p95 검색 지연    | 300ms (리랭킹 포함 500ms)          | 리랭킹은 런타임 비용이 붙는다   |
| 색인 지연        | 문서 저장 후 60초 내 검색 가능     | 실시간성 요구 수준을 먼저 합의  |
| 전체 재색인 시간 | 무중단, 6시간 내                   | 임베딩 모델 교체 시 반드시 발생 |
| 권한             | 검색 결과에 비인가 문서 0건        | 사후 필터링은 위험 (5절)        |
| 비용             | 질의당 임베딩·리랭커 API 비용 상한 | 리랭킹은 질의마다 과금된다      |

"전체 재색인 시간"을 초기에 정하는 게 특히 중요하다. 임베딩 모델을 바꾸면 **기존 벡터는 전부 무효**가 된다. 이 비용을 나중에 발견하면 모델 업그레이드가 영원히 미뤄진다.

---

## 2. 왜 하이브리드인가 — 근거는 벤치마크에 있다

"BM25는 옛날 기술, 이제 벡터"라는 통념은 1차 자료와 맞지 않는다.

BEIR는 9개 태스크·18개 데이터셋에서 렉시컬·희소·밀집·late-interaction·리랭킹 5가지 아키텍처, 10개 검색 시스템을 zero-shot으로 평가한 벤치마크다. 논문의 결론은 이렇다:

> "우리 결과는 **BM25가 강건한 베이스라인**이며, 리랭킹과 late-interaction 기반 모델이 평균적으로 최고의 zero-shot 성능을 내지만 높은 계산 비용이 든다는 것을 보여준다. 반면 밀집·희소 검색 모델은 계산적으로는 효율적이지만 다른 접근법보다 **성능이 떨어지는 경우가 많다**."
> — [Thakur et al., BEIR (NeurIPS 2021 Datasets & Benchmarks)](https://arxiv.org/abs/2104.08663)

같은 논문의 더 중요한 발견: **in-domain 성능은 일반화 성능을 예측하지 못한다.** MS MARCO에서 BM25를 이긴 여러 모델이 BEIR 데이터셋에서는 성능이 나빴다. 벤더 데모나 리더보드 점수를 보고 "우리 도메인에서도 잘 될 것"이라 판단하면 안 된다는 뜻이다. 우리 데이터로 직접 재야 한다(6절).

설계 결론:

- **1차 검색은 렉시컬 + 벡터 병렬**, 결과를 융합한다.
- **2차로 리랭커**를 얹는다. 정확도는 리랭킹이 가장 크게 올려주지만 비용도 가장 크다 — 그래서 후보 수십~수백 건에만 적용한다.
- 리랭커의 원형은 질의-문서 쌍을 함께 인코딩하는 cross-encoder([Nogueira & Cho, Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085))이고, 정확도와 비용의 중간 지점을 노린 late-interaction 계열이 ColBERT다([Khattab & Zaharia, ColBERT](https://arxiv.org/abs/2004.12832)).

### 융합은 점수가 아니라 순위로 — RRF

렉시컬 점수와 벡터 점수는 **스케일이 다르다.** Elastic 공식 문서의 표현대로 "BM25 점수는 상한이 없고, text_embedding 모델의 벡터 유사도 점수는 [0, 1] 사이"다([Elasticsearch, Retrievers examples](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/retrievers-examples)). 그래서 두 점수를 그냥 더하면 안 된다.

두 가지 선택지가 있다.

**(a) RRF(Reciprocal Rank Fusion)** — 점수를 버리고 **순위만** 쓴다. Elastic 공식 문서는 RRF를 "서로 다른 relevance 지표를 가진 여러 결과 집합을 하나로 결합하는 방법"으로 정의하며, "**튜닝이 필요 없고**, 서로 다른 relevance 지표들이 서로 관련되어 있지 않아도 고품질 결과를 낸다"고 설명한다([Elasticsearch, Reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)). 원 논문은 [Cormack, Clarke & Buettcher (SIGIR 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)다.

**(b) 선형 결합** — 점수를 minmax 등으로 정규화한 뒤 가중합. 직관적이고 가중치로 의도를 표현할 수 있지만, 정규화 방식과 가중치를 **튜닝해야** 한다. Elasticsearch는 `linear` retriever로 이를 제공한다.

초기 구축이라면 (a) RRF로 시작하는 게 맞다. 튜닝할 데이터(골든셋)가 아직 없기 때문이다. 골든셋이 쌓이고 나서 (b)로 옮겨 가중치를 최적화하면 된다.

Elasticsearch 기준 최소 구현은 이 정도다 — 공식 문서의 hybrid search 예제 형태다:

```json
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "multi_match": {
                "query": "정산 지연 원인",
                "fields": ["title^2", "body"]
              }
            }
          }
        },
        {
          "knn": {
            "field": "body_vector",
            "query_vector": [/* ... */],
            "k": 50,
            "num_candidates": 200
          }
        }
      ],
      "rank_constant": 60,
      "rank_window_size": 100
    }
  }
}
```

`rank_constant`의 기본값은 60이며 "값이 클수록 하위 순위 문서의 영향력이 커진다", `rank_window_size`는 "값이 클수록 관련성은 좋아지고 성능은 나빠진다"고 공식 문서가 명시한다(같은 문서). 즉 이 두 값이 **품질↔지연 다이얼**이다.

OpenSearch를 쓴다면 같은 역할을 `normalization-processor` 기반 hybrid query가 담당한다([OpenSearch, Hybrid search](https://opensearch.org/docs/latest/vector-search/ai-search/hybrid-search/)).

---

## 3. 전체 아키텍처 — 두 개의 파이프라인

검색 시스템은 사실상 **서로 다른 두 시스템**이다. 색인 파이프라인은 배치·처리량 중심이고, 질의 파이프라인은 온라인·지연 중심이다. 둘을 하나의 서비스에 섞으면 색인 부하가 검색 지연을 밀어 올린다.

```
[색인 파이프라인]  (배치/스트리밍, 처리량 최적화)
 원본 문서
   → 정규화(공백·표기·메타데이터 추출)
   → 청킹 (+ 청크에 문서 맥락 한 줄 부여)
   → ① 렉시컬 색인(형태소 분석 + BM25)
   → ② 임베딩 생성 → 벡터 색인(HNSW)
   → 색인 버전 태그 → alias 스왑으로 공개

[질의 파이프라인]  (온라인, p95 지연 최적화)
 사용자 질의
   → 질의 이해(정규화 / 필터 추출 / 오타 교정)
   → ① BM25 top-100      ② kNN top-100      (병렬)
   → 융합(RRF)  → 후보 100
   → 권한·비즈니스 필터
   → 리랭커(cross-encoder) → top-10
   → 결과 + 근거 하이라이트 + 로깅
```

### 청킹에서 맥락을 잃지 않기

청킹은 가장 과소평가된 단계다. 문서를 잘게 자르면 각 조각은 자기가 무엇에 대한 이야기인지 모른다. "그 값은 2,000ms입니다"라는 청크는 무슨 값인지 알 수 없고, 임베딩도 BM25도 이걸 못 살린다.

Anthropic이 제안한 Contextual Retrieval은 각 청크 앞에 **그 청크가 문서 전체에서 어디에 위치하는지 설명하는 짧은 맥락(보통 50~100 토큰)** 을 LLM으로 생성해 붙인 뒤, 그 상태로 임베딩과 BM25 색인을 함께 만드는 방법이다. 자사 평가 결과(**벤더 자체 측정치 — 자사 데이터셋, 중립 제3자 재현 결과는 공개돼 있지 않음**)는 다음과 같다:

- Contextual Embeddings만: top-20 검색 실패율 5.7% → 3.7% (35% 감소)
- \+ Contextual BM25: 5.7% → 2.9% (49% 감소)
- \+ 리랭킹: 5.7% → 1.9% (67% 감소)

([Anthropic, Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval))

수치 자체는 그들의 데이터셋 기준이므로 그대로 기대하면 안 되지만, **설계 방향**은 가져올 만하다: 맥락 부여는 색인 시점 1회 비용이고, 질의 시점 지연을 늘리지 않는다. 질의마다 LLM을 태우는 HyDE 같은 기법([Gao et al., HyDE](https://arxiv.org/abs/2212.10496))과의 결정적 차이가 여기다. 초기 구축에서는 **런타임 지연을 늘리지 않는 개선을 먼저** 소진하는 게 정석이다.

---

## 4. 한국어 — 여기서 대충 하면 나머지가 무의미하다

영어 자료를 그대로 따라 하면 반드시 걸리는 곳이 한국어 토크나이징이다. 공백 기준 분리로는 조사가 붙은 "정산이 / 정산을 / 정산은"이 전부 다른 토큰이 된다.

Elasticsearch의 Korean(nori) 플러그인은 Lucene nori 모듈을 통합한 것으로, **mecab-ko-dic 사전으로 형태소 분석**을 수행한다([Elasticsearch, Korean (nori) analysis plugin](https://www.elastic.co/docs/reference/elasticsearch/plugins/analysis-nori)). 설계 시 실제로 결정해야 하는 옵션은 두 개다.

**`decompound_mode`** — 복합명사를 어떻게 다룰지. 공식 문서의 예시 그대로:

| 모드               | 동작                 | `가곡역` 처리          |
| ------------------ | -------------------- | ---------------------- |
| `none`             | 분해 안 함           | `가곡역`               |
| `discard` (기본값) | 분해하고 원형 버림   | `가곡`, `역`           |
| `mixed`            | 분해하고 원형도 유지 | `가곡역`, `가곡`, `역` |

([Elasticsearch, nori_tokenizer](https://www.elastic.co/docs/reference/elasticsearch/plugins/analysis-nori-tokenizer))

기본값 `discard`는 재현율(recall)은 올라가지만 "가곡역"을 정확히 찾는 질의의 정밀도(precision)를 떨어뜨린다. 사내 문서 검색처럼 **복합명사 자체가 고유명사인 경우가 많은 도메인**이라면 `mixed`를 후보로 두고 골든셋으로 비교하는 게 맞다. 감으로 정하지 말고 재라는 뜻이다.

**`user_dictionary` / `user_dictionary_rules`** — 사내 약어·제품명·코드를 사전에 등록한다. 공식 문서는 `["c++", "C쁠쁠", "세종", "세종시 세종 시"]` 형태로 규칙을 인라인 정의하는 예를 든다(같은 문서). 이게 **롱테일 전문용어 질의의 유일한 해법**이다. 임베딩 모델은 학습에 없던 사내 약어를 알 수 없다.

운영 관점의 함정: 사용자 사전을 바꾸면 **기존 색인은 옛 분석 결과를 그대로 갖고 있다.** 사전 변경은 재색인 트리거로 취급해야 한다. 사전 파일을 CI에서 형상 관리하고, 변경 시 재색인 잡이 자동으로 도는 구조를 처음부터 넣어야 한다.

---

## 5. 저장소 선택 — pgvector냐 검색엔진이냐

가장 자주 받는 질문이고, 가장 흔하게 잘못 답하는 질문이다. 먼저 밝혀둘 것: **두 제품의 검색 품질을 동일 조건에서 비교한 중립 제3자 벤치마크는 확인하지 못했다.** 아래는 성능 우열이 아니라 **공식 문서에 명시된 기능·제약**을 기준으로 한 판단표다.

| 판단 기준            | PostgreSQL + pgvector             | Elasticsearch / OpenSearch      |
| -------------------- | --------------------------------- | ------------------------------- |
| 이미 쓰는 인프라인가 | RDB가 이미 있으면 추가 컴포넌트 0 | 클러스터 신규 운영 부담         |
| 트랜잭션 일관성      | 원본과 벡터가 같은 트랜잭션       | 최종 일관성, 색인 지연 존재     |
| BM25 품질            | PostgreSQL 전문검색은 BM25가 아님 | Lucene BM25가 기본 similarity   |
| 한국어 형태소        | 별도 확장 필요                    | nori 플러그인 공식 제공         |
| 하이브리드 융합      | 애플리케이션에서 직접 구현        | `rrf` / `linear` retriever 내장 |
| 검색 품질 평가       | 직접 구현                         | `_rank_eval` API 내장           |
| 규모                 | 단일 노드 한계                    | 샤딩·수평 확장 전제 설계        |

**초기 규모(문서 수십만 건 이하)이고 이미 PostgreSQL을 운영 중이라면 pgvector로 시작**하는 게 합리적이다. 컴포넌트 하나를 안 늘리는 것의 가치가 크다. 다만 pgvector의 HNSW 파라미터와 **필터 결합 함정**은 반드시 알고 들어가야 한다.

pgvector 공식 README 기준:

```sql
CREATE INDEX ON items USING hnsw (embedding vector_l2_ops)
  WITH (m = 16, ef_construction = 64);   -- 문서상 기본값
SET hnsw.ef_search = 100;                -- 기본값 40
```

- `m` = 레이어당 최대 연결 수(기본 16), `ef_construction` = 그래프 구성 시 후보 리스트 크기(기본 64). "`ef_construction` 값이 클수록 recall이 좋아지지만 색인 구축/삽입 속도가 느려진다."
- `hnsw.ef_search` = 검색 시 후보 리스트 크기(기본 40).

([pgvector README](https://github.com/pgvector/pgvector))

그리고 가장 중요한 함정, 문서에 그대로 적혀 있다:

> "근사 인덱스에서는 **필터링이 인덱스 스캔 이후에 적용된다.** 조건이 전체 행의 10%에 매칭되고 HNSW의 기본 `hnsw.ef_search`가 40이라면, 평균적으로 **4건만 매칭된다.** 더 많은 결과가 필요하면 iterative index scan을 켜라."
> — 같은 문서

`WHERE tenant_id = ? AND deleted_at IS NULL` 같은 조건을 붙인 순간 결과가 텅 비는 이유가 이것이다. 특히 **권한 필터**를 이 방식으로 걸면 "권한 있는 문서가 있는데 안 나오는" 버그가 된다. pgvector 0.8.0부터는 `hnsw.iterative_scan`(`strict_order` / `relaxed_order`)으로 필요한 만큼 인덱스를 더 스캔하게 할 수 있고, `hnsw.max_scan_tuples`(기본 20,000)로 상한을 둔다(같은 문서).

이 함정은 pgvector만의 문제가 아니라 **ANN 인덱스 + 사후 필터 조합의 일반적 성질**이다. 설계 단계에서 정해야 할 것은 하나다 — **필터를 검색 앞에 둘 것인가 뒤에 둘 것인가.** 권한처럼 정확성이 필수인 필터는 앞(또는 인덱스에 파티션 자체를 분리), 랭킹 보정용 소프트 필터는 뒤.

---

## 6. 평가 체계 — 이 절이 이 설계의 핵심이다

앞의 모든 선택(하이브리드 가중치, `decompound_mode`, `ef_search`, 리랭커 유무)은 **측정할 수 있어야만 결정할 수 있다.** 그래서 평가 체계를 엔진보다 먼저 만든다.

### 골든셋

- 실제 사용자 질의 로그에서 **50~200개**를 유형별(1절 표)로 층화 추출.
- 각 질의에 대해 사람이 판단한 관련 문서를 3단계(2=정답, 1=관련, 0=무관)로 표기.
- 롱테일과 zero-result 질의를 **의도적으로 포함**한다. 잘 되는 질의만 넣으면 평가가 무의미해진다.
- 골든셋은 코드와 같은 저장소에 두고 리뷰를 거쳐 변경한다. 골든셋을 조용히 고치면 지표는 언제든 원하는 대로 만들 수 있다.

### 오프라인 지표

| 지표          | 무엇을 보는가                     | 쓰는 곳                     |
| ------------- | --------------------------------- | --------------------------- |
| Recall@50     | 1차 검색이 정답을 후보에 넣었는가 | 렉시컬/벡터/융합 단계 튜닝  |
| nDCG@10       | 최종 순위가 좋은가                | 전체 파이프라인 회귀 게이트 |
| MRR@10        | 첫 정답이 얼마나 위에 있는가      | 단일 정답형 질의            |
| Zero-result율 | 아예 못 찾는 질의 비율            | 사전·동의어 보강 신호       |

Recall@50과 nDCG@10을 **분리해서** 보는 게 중요하다. 리랭커는 nDCG만 올릴 수 있을 뿐, 1차 검색이 후보에 못 넣은 문서는 절대 살려내지 못한다. nDCG가 안 오를 때 리랭커를 손보는 건 대개 헛수고고, Recall@50부터 봐야 한다.

Elasticsearch를 쓴다면 이 측정이 API로 내장돼 있다 — [Ranking evaluation API(`_rank_eval`)](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval)로 골든셋을 던져 nDCG 등을 산출할 수 있다. nDCG 지표 자체의 원 정의는 Järvelin & Kekäläinen, _Cumulated gain-based evaluation of IR techniques_, ACM TOIS 20(4), 2002 (doi:10.1145/582415.582418)이다.

### 온라인 지표

오프라인 지표는 대리 지표일 뿐이다. 운영에서는 **재질의율(사용자가 결과를 보고 다시 검색한 비율)**, 상위 3건 클릭률, zero-result율, p95 지연을 같이 본다. 재질의율은 특히 정직한 지표다 — 검색이 실패했을 때 사용자가 실제로 하는 행동이기 때문이다.

### CI 게이트로 못 박기

골든셋 평가를 CI에 넣고 **nDCG@10이 기준치 대비 일정 폭 이상 떨어지면 배포를 막는다.** 검색은 코드 한 줄 없이도 품질이 무너질 수 있는 시스템이다(사전 변경, 임베딩 모델 버전, 색인 매핑 수정). 자동 게이트가 없으면 품질 저하는 반드시 사용자가 먼저 발견한다.

---

## 7. 운영 설계 — 재색인을 전제로 짓는다

**재색인은 예외 상황이 아니라 정기 업무다.** 임베딩 모델 교체, 청킹 전략 변경, 사용자 사전 갱신, 매핑 수정 — 전부 재색인을 부른다. 처음부터 아래를 넣는다.

1. **색인 별칭(alias) 필수.** 애플리케이션은 항상 `docs-current`를 보고, 실제 색인은 `docs-v3-emb2`처럼 **임베딩 모델 버전을 이름에 박는다.** 스왑은 별칭 전환 한 번.
2. **임베딩 모델 버전 = 색인 스키마 버전.** 같은 색인에 서로 다른 모델의 벡터가 섞이면 유사도는 의미를 잃는다. 모델 버전을 문서 필드로도 저장해 섞임을 탐지한다.
3. **원본은 항상 보관.** 재색인은 "원본 → 재처리"여야 한다. 청크만 갖고 있으면 청킹 전략을 못 바꾼다.
4. **질의 로그를 남긴다.** 질의문, 반환된 문서 ID, 클릭, 지연을 남겨야 다음 달의 골든셋과 튜닝 근거가 생긴다. (개인정보·사내 기밀이 질의문에 섞이므로 보존 기간과 마스킹 정책을 같이 정한다.)
5. **지연 예산을 단계별로 분해**해 관측한다. 질의 임베딩 / BM25 / kNN / 융합 / 리랭킹 각각에 타이머를 건다. "검색이 느리다"는 리포트는 이 분해 없이는 손댈 수 없다.

---

## 8. 단계별 구축 로드맵 — 승급 조건을 숫자로

한 번에 다 만들지 않는다. 각 단계는 **다음 단계로 넘어갈 조건**을 지표로 정의한다.

| 단계        | 구축 내용                                                                       | 승급 조건                              |
| ----------- | ------------------------------------------------------------------------------- | -------------------------------------- |
| **Phase 0** | 형태소 분석(nori) + BM25 베이스라인, **골든셋 100건**, 오프라인 평가 파이프라인 | 골든셋으로 nDCG@10 측정치가 나온다     |
| **Phase 1** | 임베딩·벡터 색인 추가, RRF 하이브리드                                           | Recall@50이 Phase 0 대비 유의하게 상승 |
| **Phase 2** | 리랭커(cross-encoder) 상위 후보 재정렬                                          | nDCG@10 상승 + p95 지연 예산 내        |
| **Phase 3** | 질의 이해(오타 교정·동의어·필터 추출), 청크 맥락 부여                           | zero-result율·재질의율 감소            |
| **Phase 4** | 클릭 로그 기반 가중치 학습, 개인화                                              | 온라인 A/B에서 유의미한 개선           |

**Phase 0에서 골든셋을 만들지 않으면 Phase 1 이후는 전부 감으로 하는 작업이 된다.** 여기가 이 로드맵에서 유일하게 건너뛰면 안 되는 칸이다.

---

## 9. 흔한 안티패턴 5가지

1. **벡터 DB 선정부터 시작한다.** 질의 유형 분석과 골든셋이 먼저다. 저장소는 그 다음에 자동으로 좁혀진다.
2. **골든셋 없이 튜닝한다.** "이게 더 나은 것 같다"는 판단은 재현되지 않는다. BEIR가 보여준 대로 in-domain 성능조차 다른 도메인 성능을 예측하지 못한다.
3. **BM25를 건너뛴다.** 식별자·에러코드·사내 약어 질의는 벡터로 못 잡는다. BEIR 기준으로도 BM25는 여전히 강건한 베이스라인이다.
4. **ANN 인덱스에 사후 필터를 붙이고 결과가 빈 걸 버그로 취급한다.** 그건 명세된 동작이다(5절). 권한 필터는 특히 앞단에서 처리한다.
5. **벤더 데모 수치를 우리 시스템 기대치로 삼는다.** 벤더의 개선율은 벤더의 데이터셋에서 측정된 것이다. 방향은 참고하되 수치는 우리 골든셋으로 다시 잰다.

---

## 마치며

신규 AI 검색 솔루션 설계에서 실제로 어려운 부분은 모델도 벡터 DB도 아니다. **무엇을 정답으로 볼지 정의하고, 그걸 자동으로 반복 측정하는 장치를 먼저 만드는 것**이다. 그 장치가 있으면 하이브리드 가중치도, `decompound_mode`도, 리랭커 도입 여부도 논쟁이 아니라 측정으로 결정된다. 없으면 6개월 뒤에도 "이게 더 나은 것 같은데요"를 반복하게 된다.

그래서 이 설계의 순서는 이렇게 요약된다 — **질의 분류 → 골든셋 → BM25 베이스라인 → 하이브리드 → 리랭킹.** 벡터는 네 번째다.

### 근거의 한계 (명시)

- 이 글에는 필자가 직접 실행한 벤치마크 수치가 없다. 인용 수치는 전부 출처를 밝힌 논문·공식 문서·벤더 자체 발표다.
- Anthropic Contextual Retrieval의 개선율은 **자사 데이터셋 기준 벤더 자체 측정치**이며, 중립 제3자의 재현 결과는 확인하지 못했다.
- pgvector와 Elasticsearch/OpenSearch의 **검색 품질을 동일 조건에서 비교한 중립 헤드투헤드 벤치마크는 확인하지 못했다.** 5절 표는 성능 우열이 아니라 공식 문서에 명시된 기능·제약의 비교다.
- 표의 SLO 수치(300ms 등)는 설계 예시이며 실측값이 아니다.

---

## References

**논문 (1차 자료)**

1. Nandan Thakur, Nils Reimers, Andreas Rücklé, Abhishek Srivastava, Iryna Gurevych. _BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models._ NeurIPS 2021 Datasets & Benchmarks. <https://arxiv.org/abs/2104.08663>
2. Gordon V. Cormack, Charles L. A. Clarke, Stefan Buettcher. _Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods._ SIGIR 2009. <https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf>
3. Yu. A. Malkov, D. A. Yashunin. _Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs._ IEEE TPAMI. <https://arxiv.org/abs/1603.09320>
4. Rodrigo Nogueira, Kyunghyun Cho. _Passage Re-ranking with BERT._ <https://arxiv.org/abs/1901.04085>
5. Omar Khattab, Matei Zaharia. _ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT._ SIGIR 2020. <https://arxiv.org/abs/2004.12832>
6. Luyu Gao, Xueguang Ma, Jimmy Lin, Jamie Callan. _Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE)._ <https://arxiv.org/abs/2212.10496>
7. Stephen Robertson, Hugo Zaragoza. _The Probabilistic Relevance Framework: BM25 and Beyond._ Foundations and Trends in Information Retrieval, 2009. <https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf>
8. Kalervo Järvelin, Jaana Kekäläinen. _Cumulated gain-based evaluation of IR techniques._ ACM TOIS 20(4), 2002. doi:10.1145/582415.582418

**공식 문서 (1차 자료)**

9. Elasticsearch — Reciprocal rank fusion. <https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion>
10. Elasticsearch — RRF retriever. <https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever>
11. Elasticsearch — Retrievers examples (hybrid / linear retriever). <https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/retrievers-examples>
12. Elasticsearch — Korean (nori) analysis plugin. <https://www.elastic.co/docs/reference/elasticsearch/plugins/analysis-nori>
13. Elasticsearch — nori_tokenizer. <https://www.elastic.co/docs/reference/elasticsearch/plugins/analysis-nori-tokenizer>
14. Elasticsearch — Ranking evaluation API. <https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval>
15. OpenSearch — Hybrid search. <https://opensearch.org/docs/latest/vector-search/ai-search/hybrid-search/>
16. pgvector — README (HNSW 옵션 / iterative index scans). <https://github.com/pgvector/pgvector>

**벤더 자체 발표 (벤더 주장으로 라벨)**

17. Anthropic. _Introducing Contextual Retrieval._ 2024-09-19. <https://www.anthropic.com/engineering/contextual-retrieval>
