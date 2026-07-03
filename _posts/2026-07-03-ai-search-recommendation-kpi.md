---
layout: post
title: "AI 검색·추천 을 *KPI* 로 말하기 — 벡터 검색 의 3 가지 지표"
date: 2026-07-03 21:10:00 +0900
categories: [ai, backend, search]
tags: [ai, rag, pgvector, hnsw, spring-ai, vector-search, embedding, recommendation, kpi]
---

"AI 붙였다" 는 흔 하다. 하지만 *검색 이 정확 한지, 추천 이 쓸 만 한지, 빠른지* 를 **지표 로** 말할 수 있어야 실무 다. 이 글 은 내 AI 이커머스 검색·추천 플랫폼(Spring AI + PostgreSQL 16 + pgvector) 을 **3 개 KPI** 로 나눠 정리한다.

| KPI | 무엇 | 핵심 기술 |
|---|---|---|
| 검색 정확도 | 의미 로 찾는가 | pgvector · COSINE · 임베딩 |
| 추천 품질 | 관련 있는 걸 주는가 | 시맨틱 유사도 · RAG |
| 응답 속도 | 빠른가 | HNSW ANN 인덱스 |

---

## 배경 — 키워드 검색 의 한계

전통적 인 `LIKE '%검색어%'` 는 *글자* 를 맞춘다. "매운 라면" 을 쳐도 "불닭" 은 못 찾는다 — 글자 가 안 겹치니까. **의미(semantic)** 로 찾으려면 텍스트 를 *벡터* 로 바꿔(임베딩) *가까운 벡터* 를 찾아야 한다.

내 구성:
- **PostgreSQL 16 + pgvector** — 벡터 를 DB 에 저장·검색 (별도 벡터 DB 없이 PG 하나로)
- **3072 차원 임베딩** — 텍스트 의 의미 를 3072 개 숫자 로
- **COSINE 유사도** — 두 벡터 가 얼마나 같은 방향 인지
- **Spring AI `VectorStore`** — 임베딩·검색 을 추상화

---

## ① 검색 정확도 — *글자 가 아니라 의미 로*

핵심 은 **시맨틱 검색**. 사용자 질의 를 임베딩 → `vector_store` 에서 COSINE 유사도 로 가까운 문서 를 찾는다.

```
Service → VectorStore.similaritySearch(query, topK=5)
        → DB 벡터 유사도 검색 (COSINE)
        → 의미 상 가장 가까운 5 건
```

글자 가 안 겹쳐도 *의미 가 가까우면* 걸린다. 이게 키워드 검색 과의 결정적 차이.

📏 측정: "의도 는 맞는데 키워드 안 겹치는 질의 의 hit 율" → 시맨틱 검색 으로 상승. Testcontainers + pgvector 로 *통합 테스트* 까지 자동화(검색 결과 가 기대 문서 를 포함 하는지 검증).

---

## ② 추천 품질 — *RAG 로 근거 있는 답*

추천/QA 는 단순 검색 을 넘어 **RAG(Retrieval-Augmented Generation)** 로. 관련 문서 를 먼저 검색 해서 *그걸 근거 로* LLM 이 답 한다.

- `similaritySearch(topK=5)` 로 관련 문서 5 건 확보
- 그 문서 를 컨텍스트 로 LLM 에 전달 → *환각 줄이고 근거 있는* 답/추천
- "없는 걸 지어내지 않고, 검색된 근거 안에서" 답 하도록 설계

📏 측정: "추천 결과 의 관련성"(관련 문서 가 topK 안에 드는 비율) + "근거 없는 답변 비율" 하락. topK·유사도 임계값 을 튜닝 포인트 로.

---

## ③ 응답 속도 — *HNSW 로 근사 최근접*

벡터 가 수만 건 이면 *전수 비교(brute force)* 는 느리다. 그래서 **HNSW(Hierarchical Navigable Small World)** 인덱스:

- 다계층 그래프 로 *근사 최근접(ANN)* 검색 — 전수 비교 없이 몇 홉 만에 근접 벡터 도달
- `V15__add_hnsw_index.sql` 로 COSINE 기반 HNSW 인덱스 를 raw SQL 로 생성
- `initializeSchema=false` + 수동 인덱스 관리 — Spring AI 자동생성 대신 *마이그레이션 으로 통제* (재현성·운영 안정성)

정확도 를 약간 내주고 *속도 를 크게* 얻는 트레이드오프 — 검색 UX 에선 이게 정답 인 경우 가 많다.

📏 측정: "벡터 검색 p95 레이턴시" → HNSW 로 brute-force 대비 대폭 단축. "인덱스 유무 별 응답시간" 비교.

---

## 한 줄 정리

AI 검색·추천 을 KPI 로 바꾸면:

- **검색 정확도**: pgvector 3072d + COSINE 시맨틱 검색 → 의미 로 찾음
- **추천 품질**: RAG(topK=5) → 근거 있는 추천, 환각 감소
- **응답 속도**: HNSW ANN 인덱스 → 대규모 에서도 빠른 검색

*"AI 를 붙였다"* 가 아니라 *"정확도·품질·속도 를 지표 로 관리 한다"* — 그게 AI 를 실무 에 태우는 방법 이다.

> ⚙️ AI 보조 — 실제 정확도/레이턴시 수치 는 서비스 트래픽 기준 측정치 로 갱신 예정.

---

_시리즈 완결: [쿠버네티스 를 KPI 로](#) · [정산 을 KPI 로](#) · AI 를 KPI 로._
