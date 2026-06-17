---
layout: post
title: "*Spring AI 의 *깊이* — ChatModel · Embedding · RAG · Function Calling"
date: 2026-06-15 15:30:00 +0900
categories: [backend, spring, ai]
tags: [spring-ai, llm, rag, function-calling, embedding, vector-store, openai, anthropic, gemini]
---

> *Spring 이 *23 년 동안 *Java 의 *복잡도 를 *흡수* 했듯, *Spring AI 는 *LLM 의 *복잡 도 를 *흡수* 한다*.
> *OpenAI / Anthropic / Gemini / Mistral 의 *제각각 *API* 를 *하나의 *추상* 으로 — *그게 Spring AI 의 *핵심 가치*.
> 이 글은 *Spring AI 의 *4 주요 기능* 의 *깊이* 분석.

---

## TL;DR

| 기능 | 역할 |
|------|------|
| **ChatModel** | LLM 호출 의 *통일 추상* (OpenAI / Claude / Gemini 등 *동일 인터페이스*) |
| **Prompt** | *체계 적 *프롬프트 *작성* (Template / Role / Format) |
| **Embedding** | *텍스트 → 벡터* 변환 *통일 추상* |
| **Vector Store** | *벡터 DB 의 *추상* (pgvector / Milvus / Chroma / Pinecone) |
| **RAG** | *Retrieval-Augmented Generation* — 위 *4 가지 의 *조합* |
| **Function Calling** | *LLM 이 *Java 메서드 *호출* 가능 — *Agent 의 *기본* |
| **Observability** | Micrometer 통합 — *토큰 / latency / 비용 추적* |

핵심 한 줄 :

> *Spring AI 는 *AI 모델 의 *교체 가 *Bean 정의 *한 줄 수정* 으로 *가능* 하게 한다. *AI 시대 의 *Strategy 패턴*.*

---

## 1. **Spring AI 의 *등장 배경*

### *2023 ~ 2024 의 *문제*

각 LLM 의 *API 가 *제각각*:

```
OpenAI :  POST /v1/chat/completions  + messages: [{role, content}]
Claude :  POST /v1/messages          + system: ..., messages: [...]
Gemini :  POST /v1beta/models/.../generateContent + contents: [...]
```

이 *3 API 모두 통합 *지원* 하는 Java 코드 — *조건 분기 의 *지옥*.

### Spring AI 의 *발상*

> *"하나의 *ChatModel 인터페이스* 가 *모든 LLM 의 *공통 추상*."*

```java
ChatResponse response = chatModel.call(new Prompt("Hello"));
```

이 한 줄 — *어느 LLM 이든 *동일*. *Bean 설정 만 *교체*.

### *Spring AI 1.0 (2024)*

- ChatModel / EmbeddingModel 통합
- 주요 Provider 지원 (OpenAI / Anthropic / Azure / Vertex / Ollama / Mistral)
- Vector Store 추상
- RAG 의 *기본 구성*

### *Spring AI 1.1+ (2025+)*

- Function Calling 표준화
- Multi-modality (이미지 / 음성)
- Observability (Micrometer 통합)
- Agent 패턴 의 *공식 *지원*

---

## 2. **ChatModel** — *가장 기본*

### *기본 사용*

```java
@Autowired ChatModel chatModel;

public String ask(String question) {
    Prompt prompt = new Prompt(question);
    ChatResponse res = chatModel.call(prompt);
    return res.getResult().getOutput().getContent();
}
```

### *Provider 교체* — *application.yml 한 줄*

```yaml
# OpenAI
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY}
      chat:
        options:
          model: gpt-4o

# Anthropic 으로 교체
spring:
  ai:
    anthropic:
      api-key: ${ANTHROPIC_API_KEY}
      chat:
        options:
          model: claude-sonnet-4-5
```

→ ***Java 코드 *0 줄 변경* — *모델 교체* 가능. *Strategy 의 *진짜 활용*.

### *Streaming*

```java
Flux<ChatResponse> stream = chatModel.stream(new Prompt("..."));
stream.subscribe(res -> 
    print(res.getResult().getOutput().getContent()));
```

*Reactive 의 *깊이 가 *AI 시대 의 *친화*. WebFlux 와 *완벽 통합*.

---

## 3. **Prompt** — *체계 적 작성*

### *Role 의 *구분*

```java
SystemMessage system = new SystemMessage(
    "You are a helpful assistant specialized in Korean.");
UserMessage user = new UserMessage("안녕하세요.");

Prompt prompt = new Prompt(List.of(system, user));
```

### *Template + 변수*

```java
PromptTemplate template = new PromptTemplate("""
    너는 {role} 분야의 전문가다.
    질문: {question}
    답변은 {format} 형식으로.
    """);

Prompt prompt = template.create(Map.of(
    "role", "백엔드 개발",
    "question", "JPA N+1 해결 방법",
    "format", "마크다운"
));
```

### *OutputParser — *구조화 응답*

```java
BeanOutputConverter<UserInfo> converter = 
    new BeanOutputConverter<>(UserInfo.class);

PromptTemplate template = new PromptTemplate(
    "사용자 의 *생성: {format}",
    Map.of("format", converter.getFormat())
);

ChatResponse res = chatModel.call(template.create());
UserInfo user = converter.convert(res.getResult().getOutput().getContent());
```

→ *LLM 응답 을 *Java 객체* 로 *직접 *변환*. *Spring 의 *전형* 적 *추상*.

---

## 4. **Embedding** — *텍스트 → 벡터*

### *기본*

```java
@Autowired EmbeddingModel embeddingModel;

public float[] embed(String text) {
    EmbeddingResponse res = embeddingModel.embedForResponse(List.of(text));
    return res.getResults().get(0).getOutput();
}
```

### *Provider 교체*

```yaml
# OpenAI text-embedding-3-large : 3072 차원
# Cohere multilingual           : 1024 차원
# Sentence-Transformers (로컬)  : 384 차원
```

*벡터 차원* 이 *Provider 마다 다름*. *Vector Store 의 *스키마* 와 *맞춰 야 함*.

### *Batch Embedding*

```java
List<String> docs = List.of("doc1 ...", "doc2 ...", "doc3 ...");
EmbeddingResponse res = embeddingModel.embedForResponse(docs);

for (Embedding emb : res.getResults()) {
    float[] vec = emb.getOutput();
    vectorStore.add(...);
}
```

*수백 개 *문서 *벡터화 가 *한 번 호출*.

---

## 5. **Vector Store** — *추상 *DB*

### *지원 *DB*

```
- pgvector  (PostgreSQL 확장)
- Redis Stack (RedisSearch + 벡터)
- Milvus
- Chroma
- Pinecone
- Weaviate
- Elasticsearch (8.x 의 dense_vector)
- Qdrant
```

### *통일 API*

```java
@Autowired VectorStore vectorStore;

// 저장
List<Document> docs = List.of(
    new Document("Spring is a framework", Map.of("source", "doc1")),
    new Document("AI is a field", Map.of("source", "doc2"))
);
vectorStore.add(docs);  // 자동 임베딩 + 저장

// 검색
List<Document> similar = vectorStore.similaritySearch(
    SearchRequest.query("What is Spring?")
                  .withTopK(5)
                  .withSimilarityThreshold(0.7)
);
```

→ *어떤 *벡터 DB 든 *동일 API*. *Bean 교체 만으로 *전환*.

### *Spring 의 *전형 적 추상 의 *진수*

`JdbcTemplate ↔ VectorStore` 의 *대응* :

```
JdbcTemplate.query    ↔  VectorStore.similaritySearch
JdbcTemplate.update    ↔  VectorStore.add
JdbcTemplate.delete    ↔  VectorStore.delete
```

*DB 의 *추상* 의 *현대 적 *재현*.

---

## 6. **RAG** — *통합 사용 의 *완성*

### *RAG 의 *흐름*

```
사용자 질문
   ↓
1. Embedding (질문 → 벡터)
   ↓
2. Vector Store 검색 (유사 문서 K 개)
   ↓
3. Prompt 구성 (질문 + 검색 결과)
   ↓
4. ChatModel 호출
   ↓
응답
```

### *Spring AI 의 *RAG 구현*

```java
@Service
public class RagService {
    @Autowired ChatModel chatModel;
    @Autowired VectorStore vectorStore;

    public String ask(String question) {
        // 1. 유사 문서 검색
        List<Document> similar = vectorStore.similaritySearch(
            SearchRequest.query(question).withTopK(3)
        );
        
        String context = similar.stream()
            .map(Document::getContent)
            .collect(Collectors.joining("\n---\n"));
        
        // 2. Prompt 구성
        PromptTemplate template = new PromptTemplate("""
            다음 문서를 참고 해 질문에 답하세요.
            
            문서:
            {context}
            
            질문: {question}
            """);
        
        Prompt prompt = template.create(Map.of(
            "context", context,
            "question", question
        ));
        
        // 3. LLM 호출
        return chatModel.call(prompt).getResult().getOutput().getContent();
    }
}
```

### *Spring AI 의 *Advisor 패턴 (2025+)*

```java
@Bean
ChatClient chatClient(ChatClient.Builder builder, VectorStore vectorStore) {
    return builder
        .defaultAdvisors(new QuestionAnswerAdvisor(vectorStore))
        .build();
}

// 사용
String answer = chatClient.prompt()
    .user(question)
    .call()
    .content();
```

→ *RAG 가 *한 줄 의 *Advisor 등록* 으로 *자동 처리*. *Spring 다운 *간결 화*.

---

## 7. **Function Calling** — *LLM 의 *Java 메서드 호출*

### *발상*

> *"LLM 이 *답을 *직접 모를 때 — *Java 의 *함수를 *호출 해 *답 *얻기*."*

대표 예 — *날씨 / 시간 / DB 조회*.

### Spring AI 의 *구현*

```java
@Configuration
public class FunctionConfig {
    
    @Bean
    @Description("현재 날씨를 조회한다")
    public Function<WeatherRequest, WeatherResponse> weatherFunction() {
        return req -> {
            // 외부 날씨 API 호출
            return new WeatherResponse(...);
        };
    }
}

// 사용
ChatResponse res = chatModel.call(new Prompt(
    "서울의 *현재 날씨 는?",
    OpenAiChatOptions.builder()
        .withFunction("weatherFunction")  // 자동 호출 가능
        .build()
));
```

LLM 이 *질문 *분석* → `weatherFunction` 호출 *결정* → *Spring 이 *Java 함수 *호출* → *결과 가 *LLM 으로 *반환* → *최종 응답 *작성*.

### *2026 의 *Agent 패턴*

```java
@Bean
ChatClient agentClient(ChatClient.Builder builder) {
    return builder
        .defaultFunctions(
            "weatherFunction",
            "stockPriceFunction",
            "calendarFunction"
        )
        .build();
}

// 사용
agentClient.prompt()
    .user("오늘 *서울 비 와 코스피 보고 일정 *3 개 추천 해 줘.")
    .call()
    .content();
// → LLM 이 *3 함수 *순차 *호출* + *통합 응답*
```

→ *Agent 의 *진짜 모습 — *복수 도구의 *자동 조합*.

---

## 8. **Observability** — *AI 의 *운영 *추적*

### *Micrometer 통합*

```java
@Bean
ChatModel chatModel(MeterRegistry registry) {
    return ChatModel.builder()
        .observationRegistry(...)
        .build();
}
```

자동 *수집 지표* :

```
- spring.ai.chat.client (latency, success/fail)
- spring.ai.chat.client.tokens (input, output)
- spring.ai.embedding (latency)
- spring.ai.vectorstore (search latency)
```

### *비용 추적*

```
모델 별 *토큰 단가* x *호출 토큰 수* → *비용 추정*
```

*Grafana 대시보드 *연결* 으로 *비용 + 성능 동시 *추적*.

---

## 9. **실 무 적용 *사례*

### *9.1. RAG 기반 *고객 지원*

```
1. *기존 *고객 지원 *문서 (FAQ, 매뉴얼) *벡터화*
2. *사용자 질문 → 검색 → LLM 답변*
3. *답 의 *근거 문서 *함께 표시*
4. *모름 응답 *명시* — *없는 답 *지어 내기* 방지
```

### *9.2. Function Calling 기반 *내부 자동화*

```
사용자 : "8 월 보고서 작성"
LLM :
  1. SalesDataFunction(month=8)
  2. ChartGenerationFunction(data=...)
  3. ReportTemplateFunction(charts=...)
  → 통합 응답
```

### *9.3. Embedding 기반 *유사 상품 추천*

```
상품 설명 → 임베딩 → pgvector 저장
사용자 의 *최근 본 상품* → 유사 검색 → 추천
```

### *9.4. Streaming 응답 *UI*

```
WebFlux + SSE :
  - LLM 응답 *토큰 별 *전달*
  - *사용자 *대기 시간 ↓*
  - *체감 *반응성 ↑*
```

---

## 10. **흔한 함정**

### 10.1. *Provider 의 *옵션 *차이 무시*

```yaml
# OpenAI 에선 max-tokens
# Anthropic 에선 max_tokens (포맷 다름)
# Gemini 에선 maxOutputTokens
```

*Provider 별 *옵션 의 *세부 차이* — *Spring AI 의 *추상 위에서 도 *주의*.

### 10.2. *Token *제한 무시*

```
LLM 의 *context window 한계 (128K 등)
RAG 검색 결과 + 질문 의 *총 토큰 = *입력*
→ *제한 초과 시 *예외*
```

### 10.3. *RAG 의 *검색 정확도*

*Top-K 선택 + Similarity Threshold* 의 *튜닝 부족* → *부적합 문서 가 *답 의 *기반*. *체계 적 *평가 필요*.

### 10.4. *Function Calling 의 *권한 누락*

```java
@Bean
public Function<DbQueryRequest, ...> dbQueryFunction() {
    return req -> jdbc.query(req.sql, ...);  // ❌ SQL injection 위험
}
```

LLM 이 *제안 하는 input 의 *검증 없이* DB / 외부 호출* — *심각 *보안 위험*. *OWASP LLM07 Insecure Plugin Design*.

### 10.5. *Prompt 의 *민감 정보*

*시스템 프롬프트 에 *비밀 정보 포함* — *prompt injection 으로 *누설 가능*. *최소화 + 출력 필터링*.

### 10.6. *비용 *폭발*

*Embedding 의 *대량 호출* 또는 *Chat 의 *반복 호출* — *예산 *초과*. *Observability + 알람 설정* 필수.

---

## 11. *내 *경험* — *Spring AI *적용 회고*

### *처음 도입 (2024 중반)*

- OpenAI 만 *단일 *통합*
- *Prompt 의 *세부 튜닝 *수동*
- *Function Calling *시도 안 함*
- *비용 모니터링 *부족*

### *현재 (2026)*

- *OpenAI / Anthropic / Gemini 의 *Fallback 패턴*
- *Advisor 로 *RAG 자동 *적용*
- *Function Calling 으로 *내부 도구 통합*
- *Micrometer + Grafana 의 *비용 + 성능 *추적*

### *얻은 *교훈*

1. ***Provider 의 *교체 가 *진짜 *가능 함을 *체감*** — *Bean 한 줄*.
2. ***RAG 의 *진짜 *어려움 = 검색 정확도***. Spring AI 가 *통합 해 주지만 *튜닝 은 *수동*.
3. ***Function Calling 의 *보안 = *함수 설계 의 *철저*** — *LLM 의 *입력 *검증 *강력*.
4. ***비용 추적 *없으면 *예산 *3 배 *초과 가능***.

---

## 12. **Spring AI 의 *현재 한계*

### *부족 한 부분 (2026 시점)*

1. ***Agent 의 *고급 패턴 (ReAct, Plan-and-Execute) 의 *미흡***
2. ***Multi-Agent *조정* 부족***
3. ***Long context 활용 *최적화 부족***
4. ***Fine-tuning 통합 *부족***
5. ***Image / Audio 모델의 *통합 발전 중***

이 부분 들 — *2026 후반 ~ 2027 *발전* 예상.

---

## 13. *마치며*

> *Spring AI 는 *Java 백엔드 의 *AI 시대 진입 의 *최대 의 *간소화*. *복잡 한 *LLM 운영 의 *대부분 *고민 의 *Spring 다운 *추상*.

3 줄 요약 :

1. ***ChatModel / EmbeddingModel / VectorStore / Function 의 *4 추상 *이* Spring AI 의 *핵심***.
2. ***Provider 의 *교체 가 *Bean 한 줄 *— Strategy 의 *진짜 사례***.
3. ***Observability + 비용 추적 = *AI 운영 의 *필수 *기본***.

9년차 회고 :

> *"3 년 *전 의 *나는 *OpenAI SDK 직접 호출 의 *지옥 *살았다*. *지금 *Spring AI 의 *추상 덕분 — *AI 운영 의 *부담 이 *80% 감소* 함을 *몸 으로 *체감 *한다*."*

다음 글 — *Function Calling 의 *깊이* — *Agent 패턴 / Tool 설계 / 보안 / 추적* 의 *실 무 적용*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *9년차 백엔드 / Spring AI 운영 회고*. *Spring AI 의 *변화 속도 가 *매우 빠르므로* — *6 개월 후 *세부 가 *변할 수 있음*. *원리 + 추상 패턴* 에 *무게 중심* 을 두는 게 *오래 가는 지식*.
