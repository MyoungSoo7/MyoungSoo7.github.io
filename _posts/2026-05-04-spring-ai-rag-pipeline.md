---
layout: post
title: "Spring AI + RAG — 상품 데이터를 자연어로 검색하기"
date: 2026-05-04 13:00:00 +0900
categories: [ai, spring]
tags: [spring-ai, rag, gemini, pgvector, embedding]
---
{% raw %}

## RAG(Retrieval-Augmented Generation)란?

LLM이 학습하지 않은 **내부 데이터**를 검색해서 답변에 활용하는 패턴입니다. 이커머스 상품 데이터를 자연어로 검색할 수 있게 만들었습니다.

**Live**: [chat.lemuel.co.kr](https://chat.lemuel.co.kr)

## 아키텍처

```
사용자 질문 → Intent 분석 → Vector 유사도 검색 (pgvector)
                                    ↓
                           관련 문서 추출 (Top-K)
                                    ↓
                    프롬프트 = 시스템 지시 + 문서 컨텍스트 + 질문
                                    ↓
                         Gemini LLM → 답변 생성
```

## 핵심 구현

### 1. 벡터 임베딩

상품 등록 시 이벤트 리스너가 자동으로 임베딩을 생성합니다:

```java
@EventListener
public void onProductCreated(ProductEmbeddingEvent event) {
    String text = String.format("%s %s 카테고리:%s 가격:%d",
        product.getName(), product.getDescription(),
        product.getCategory().getName(), product.getPrice());
    
    Document doc = new Document(text, metadata);
    vectorStore.add(List.of(doc));  // pgvector에 저장
}
```

### 2. RAG 검색 + 답변 생성

```java
public AnswerResponse ask(String question) {
    // 1. 벡터 유사도 검색
    List<Document> relevantDocs = vectorStore.similaritySearch(
        SearchRequest.builder()
            .query(question)
            .topK(5)
            .similarityThreshold(0.0)
            .build()
    );
    
    // 2. 프롬프트 구성 (문서 + 질문)
    String prompt = String.format(RAG_PROMPT_TEMPLATE, 
        docsToText(relevantDocs), question);
    
    // 3. LLM 답변 생성
    return chatClient.prompt().user(prompt).call().content();
}
```

### 3. Intent 분석

자연어 질문의 의도를 분류하여 검색 전략을 최적화합니다:

```java
// "3만원 이하 가방" → PRICE_RANGE + CATEGORY
// "인기 있는 상품" → POPULARITY
// "빨간색 티셔츠" → COLOR + CATEGORY
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| LLM | Google Gemini (Spring AI) |
| Vector DB | PostgreSQL + pgvector |
| Embedding | Spring AI EmbeddingModel |
| Framework | Spring Boot 4.0 |

## 배운 점

- RAG의 품질은 **임베딩 텍스트 구성**에 크게 좌우됨 — 상품명+설명+카테고리+가격을 포함해야 정확도 향상
- Top-K와 similarity threshold 조합이 중요 — 너무 엄격하면 결과 없음, 너무 느슨하면 노이즈
- 프롬프트에 "문서에 없는 내용은 답변하지 마세요"를 명시해야 환각(hallucination) 방지

{% endraw %}
