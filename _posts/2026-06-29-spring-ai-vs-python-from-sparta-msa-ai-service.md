---
layout: post
title: "Spring AI vs Python — sparta-msa 의 ai-service 운영 으로 본 *현실 의 trade-off*"
date: 2026-06-29 17:30:00 +0900
categories: [ai, spring-ai, python, langchain, backend]
tags: [spring-ai, python, langchain, fastapi, gemini, openai, rag, vector-store, tool-calling, mcp]
---

내 *sparta-msa-project* 의 *ai-service* (chat.lemuel.co.kr) 는 *Spring AI 1.0.0* 기반 *Gemini 챗봇*. *14 개월 운영* 하면서 *Python 의 LangChain + FastAPI* 와 *직접 비교* 한 *현실 의 trade-off* 를 정리. *어느 한 쪽 의 우월 함* 의 *주장 이 아니라* — *팀 의 *맥락* 과 *조직 의 *기존 stack* 에 따른 *합리적 선택* 의 가이드.

---

## 1. 왜 *Spring AI* 인가 — sparta 의 *맥락*

sparta-msa 의 *5 개 서비스* (gateway / auth / user / product / order) 가 *전부 Spring Boot 4 + Java 25 + Spring Cloud 2025*. *AI 기능 추가 시* 의 *3 옵션*:

- **(A)** Spring AI 로 *기존 stack 통합* — *같은 build / observability / security / deploy 파이프라인*
- **(B)** Python + FastAPI 의 *별도 서비스* — *AI 생태계 의 *압도적 우위*
- **(C)** OpenAI / Gemini SDK 의 *raw HTTP 호출* — *프레임워크 없음*

내 선택 — **(A)**. 이유:
1. *팀 (1 인) 의 *Java 숙련 도*
2. *기존 의 *trace_id / metrics / circuit breaker 의 *재사용*
3. *Resilience4j + Prometheus + JPA 의 *통합 의 *시간 절감*

만약 *조직 이 *이미 Python data engineer 가 있다* 또는 *최첨단 LangGraph / DSPy / vLLM 의 *필수 사용* 이라면 — **(B)** 가 *합리적*.

---

## 2. Spring AI 의 *핵심 추상*

```java
@Configuration
class AiConfig {
    @Bean
    ChatClient chatClient(ChatClient.Builder builder) {
        return builder
            .defaultSystem("당신은 sparta 의 이커머스 상품 추천 도우미.")
            .defaultOptions(ChatOptions.builder()
                .temperature(0.7)
                .build())
            .build();
    }
}
```

`ChatClient` — *Spring AI 의 *통합 추상*. *OpenAI / Anthropic / Gemini / Ollama* 등 *11 개 + 의 provider 가 *동일 API*. provider 교체 시 *코드 0 줄 변경*, *application.yml 의 *property 만*.

```yaml
spring:
  ai:
    vertex:
      ai:
        gemini:
          project-id: ${GCP_PROJECT_ID}
          location: us-central1
          chat:
            options:
              model: gemini-2.5-flash
              temperature: 0.7
```

### Fluent API
```java
@Service
@RequiredArgsConstructor
class ProductRecommendService {
    private final ChatClient chatClient;

    public String recommend(String userQuery, Long userId) {
        return chatClient.prompt()
            .system("사용자 의 *과거 구매 이력* 을 반영해.")
            .user(userQuery)
            .advisors(advisor -> advisor.param("userId", userId))
            .call()
            .content();
    }
}
```

→ *type-safe* + *IDE 자동완성* + *컴파일 시점 검증*. Python 의 *런타임 에러 만 가능* 한 부분 이 *Java 에선 *컴파일 시 발견*.

### Python 의 *동등* (LangChain)
```python
from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import ChatPromptTemplate

llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.7)

prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 sparta 의 이커머스 상품 추천 도우미."),
    ("user", "{question}"),
])

chain = prompt | llm
result = chain.invoke({"question": user_query})
```

→ *간결 함 의 *압도적 우위*. *5 줄* vs Spring AI 의 *15 줄+*. *runtime flexibility* 가 *prototype 의 *극도 의 빠름*.

---

## 3. RAG (Retrieval-Augmented Generation) — Vector Store

sparta 의 *상품 추천* 의 *진짜 가치* — *상품 DB 에서 *관련 상품 검색 + LLM 응답 생성* 의 *RAG 패턴*.

### Spring AI 의 RAG
```java
@Configuration
class VectorStoreConfig {
    @Bean
    VectorStore vectorStore(JdbcTemplate jdbcTemplate, EmbeddingModel embeddingModel) {
        return PgVectorStore.builder(jdbcTemplate, embeddingModel)
            .dimensions(768)
            .distanceType(PgVectorStore.PgDistanceType.COSINE_DISTANCE)
            .indexType(PgVectorStore.PgIndexType.HNSW)
            .initializeSchema(true)
            .build();
    }
}

@Service
@RequiredArgsConstructor
class RagService {
    private final ChatClient chatClient;
    private final VectorStore vectorStore;

    public String answer(String question) {
        return chatClient.prompt()
            .advisors(new QuestionAnswerAdvisor(vectorStore,
                SearchRequest.builder().topK(5).build()))
            .user(question)
            .call()
            .content();
    }
}
```

→ `QuestionAnswerAdvisor` — *Spring AI 의 *advisor 추상* 이 *RAG 의 *boilerplate 제거*. *embedding + retrieval + context injection* 의 *자동화*.

### 인덱싱
```java
@Service
@RequiredArgsConstructor
class ProductIndexingService {
    private final VectorStore vectorStore;
    private final ProductRepository productRepo;

    @Scheduled(cron = "0 0 3 * * *")
    public void reindexAll() {
        List<Document> documents = productRepo.findAll().stream()
            .map(p -> new Document(
                p.getDescription(),
                Map.of(
                    "productId", p.getId(),
                    "category", p.getCategory(),
                    "price", p.getPrice()
                )))
            .toList();

        vectorStore.add(documents);
    }
}
```

→ *pgvector* 가 *automatic schema creation + HNSW 인덱스 + cosine similarity*. *모두 *자동*.

### Python 의 *동등*
```python
from langchain_community.vectorstores import PGVector
from langchain_google_vertexai import VertexAIEmbeddings

embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@003")
vector_store = PGVector(
    collection_name="products",
    connection_string="postgresql://...",
    embedding_function=embeddings,
)

# RAG chain
from langchain.chains import RetrievalQA
qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
)
result = qa.invoke({"query": question})
```

### *비교*
| 측면 | Spring AI | Python (LangChain) |
|---|---|---|
| **boilerplate** | 더 많음 (15~20 줄) | 더 적음 (8~10 줄) |
| **type safety** | 컴파일 시점 검증 | runtime 만 |
| **observability** | Micrometer / Actuator 자동 | OpenTelemetry 수동 |
| **벡터 store provider** | PgVector / Redis / Pinecone / Chroma / Weaviate (~15) | *압도적* (모든 vector store 의 사실 상 표준) |
| **새 모델 대응** | *느림* (provider PR 기다림) | *빠름* (community 가 즉시 추가) |
| **production 안정성** | Spring Boot 의 *14 년 운영 노하우 상속* | *상대적 으로 *불안정* (LangChain 의 *빠른 변경*) |

---

## 4. Tool Calling — *함수 자동 호출*

LLM 이 *코드 의 함수 를 *호출* 하는 패턴. sparta 의 *주문 조회 / 상품 검색 / 결제* 같은 *비즈니스 로직* 의 *자연어 인터페이스*.

### Spring AI 의 Tool Calling
```java
@Service
@RequiredArgsConstructor
class OrderQueryTool {
    private final OrderRepository orderRepo;

    @Tool(description = "특정 사용자 의 *최근 주문 N 건 조회*")
    public List<OrderDto> getRecentOrders(
            @ToolParam(description = "조회 할 사용자 ID") Long userId,
            @ToolParam(description = "조회 할 주문 수") int limit) {
        return orderRepo.findRecentByUserId(userId, limit)
            .stream().map(OrderDto::from).toList();
    }
}

@Service
@RequiredArgsConstructor
class ChatService {
    private final ChatClient chatClient;
    private final OrderQueryTool orderQueryTool;

    public String chat(String userMessage, Long userId) {
        return chatClient.prompt()
            .system(s -> s.text("사용자 의 *주문 정보 가 필요 하면 *tool 을 호출*."))
            .tools(orderQueryTool)
            .user(userMessage)
            .call()
            .content();
    }
}
```

→ *Spring AI 가 *자동 으로 *JSON schema 생성* + *LLM 의 function call 응답 파싱* + *Java 메서드 호출* + *결과 를 LLM 에 재전달*. *모든 boilerplate 제거*.

**핵심 강점** — *기존 Spring service / repository 를 *그대로 *tool 로 노출*. *새 layer 없음*.

### Python 의 *동등*
```python
from langchain_core.tools import tool

@tool
def get_recent_orders(user_id: int, limit: int) -> list:
    """특정 사용자 의 최근 주문 N 건 조회"""
    return order_repo.find_recent_by_user_id(user_id, limit)

llm_with_tools = llm.bind_tools([get_recent_orders])
response = llm_with_tools.invoke("user 123 의 최근 주문 3 개 알려줘")
```

→ *Python 의 *간결 함 의 *우위*. 그러나 *기존 코드 가 *FastAPI 라우터* 면 *별도 의 *tool wrapper 작성 의 *중복*.

---

## 5. Structured Output — *type-safe response*

LLM 의 *raw text* 를 *structured 객체* 로 변환.

### Spring AI
```java
record ProductRecommendation(
    String productName,
    String reasoning,
    Double confidence,
    List<String> alternativeOptions) {}

@Service
class RecommendService {
    public ProductRecommendation recommend(String query) {
        return chatClient.prompt()
            .user(query)
            .call()
            .entity(ProductRecommendation.class);  // ← 자동 변환
    }
}
```

→ *record 의 *type* 을 *Jackson schema 로 변환* → *LLM 의 *JSON 응답* 을 *자동 으로 *POJO 로 deserialize*. *runtime error 가 *컴파일 시 발견*.

### Python (Pydantic)
```python
from pydantic import BaseModel

class ProductRecommendation(BaseModel):
    product_name: str
    reasoning: str
    confidence: float
    alternative_options: list[str]

structured_llm = llm.with_structured_output(ProductRecommendation)
result = structured_llm.invoke(query)
```

→ *Pydantic 의 *runtime validation*. *Java 의 *compile-time* 만큼 *강 하진 않지만 *충분*.

---

## 6. Streaming — *실시간 응답*

ChatGPT 처럼 *토큰 별 점진 적 응답*. sparta 의 *chat.lemuel.co.kr* 의 *UX 의 핵심*.

### Spring AI
```java
@RestController
@RequiredArgsConstructor
class ChatController {
    private final ChatClient chatClient;

    @GetMapping(value = "/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> chat(@RequestParam String message) {
        return chatClient.prompt()
            .user(message)
            .stream()
            .content();
    }
}
```

→ *Spring WebFlux 의 *Flux* 가 *streaming 의 *자연 표현*. *Server-Sent Events* 의 *자동 직렬화*.

### Python (FastAPI)
```python
from fastapi.responses import StreamingResponse

@app.get("/chat")
async def chat(message: str):
    async def event_stream():
        async for chunk in llm.astream(message):
            yield f"data: {chunk.content}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

→ *async generator 의 *간결 함*. Python 의 *async 가 *streaming 에 *자연*.

*비슷 한 수준 의 *동등성*. *언어 차이 만*.

---

## 7. Observability — *진짜 강점*

운영 시 *AI 의 *비용 / latency / error* 의 *추적 의 *필수*.

### Spring AI (Micrometer 자동)
```yaml
management:
  endpoints.web.exposure.include: prometheus,health,metrics
  metrics:
    distribution.percentiles-histogram.spring.ai.chat.client: true
```

자동 메트릭:
- `spring.ai.chat.client` — *호출 횟수 + latency*
- `spring.ai.chat.client.tokens` — *입력 / 출력 토큰*
- `spring.ai.chat.client.tokens.cost` — *추정 비용 (USD)*
- *기존 의 *trace_id 자동 전파*

```java
@Observed(name = "product.recommend",
         contextualName = "ai-product-recommendation")
public ProductRecommendation recommend(String query) {
    return chatClient.prompt().user(query).call().entity(...);
}
```

→ *Prometheus / Grafana / ELK 의 *기존 대시보드* 에 *자동 통합*. *별도 의 *AI dashboard 없음*.

### Python (수동)
```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
ai_calls = meter.create_counter("ai_calls")
ai_latency = meter.create_histogram("ai_latency_ms")

with tracer.start_as_current_span("ai-chat") as span:
    start = time.time()
    result = llm.invoke(message)
    ai_latency.record((time.time() - start) * 1000)
    ai_calls.add(1, {"model": "gemini-2.5"})
```

→ *수동 instrumentation* 의 *boilerplate*. *Spring AI 의 *자동* 과 *큰 차이*.

**이게 Spring AI 의 *진짜 우위***. *14 개월 운영* 의 *관점 에서 *압도적*.

---

## 8. 의존성 / 빌드 / 배포

### Spring AI
```gradle
dependencies {
    implementation 'org.springframework.ai:spring-ai-starter-model-vertex-ai-gemini'
    implementation 'org.springframework.ai:spring-ai-starter-vector-store-pgvector'
    implementation 'org.springframework.ai:spring-ai-advisors-vector-store'
}
```

- *Gradle 의 *transitive dependency 해결*
- *Docker image 의 *대략 250 MB* (JRE + Spring Boot + AI libs)
- *startup time 의 *3~5 초*
- *production 의 *안정성* 의 *상속*

### Python (LangChain)
```toml
[project]
dependencies = [
    "langchain>=0.3",
    "langchain-google-vertexai>=2.0",
    "langchain-postgres>=0.0.13",
    "fastapi>=0.115",
    "uvicorn>=0.32",
]
```

- *pip 의 *의존성 지옥* 의 *흔함* (LangChain 의 *빠른 변경* → *breaking change*)
- *Docker image 의 *대략 800 MB* (Python + 모든 ML libs)
- *startup time 의 *1~2 초*
- *production 의 *상대적 으로 *덜 안정*

**경험** — sparta 의 ai-service 가 *14 개월 동안 *0 회 의 *의존성 충돌 사고*. *경험 상 LangChain 은 *분기 마다 *upgrade 시 *breaking change* 의 *각오 필요*.

---

## 9. *어떨 때 무엇 을 쓰는가* — *내 가이드*

### Spring AI 가 *적합*
- *기존 Java / Spring 팀* 의 *기존 stack 통합* 우선
- *프로덕션 운영* 의 *안정성 + observability* 우선
- *RAG / Tool Calling 의 *기본 기능* 만 필요
- *조직 의 *type safety + 컴파일 검증* 의 *문화*

### Python 이 *적합*
- *데이터 엔지니어 / ML 엔지니어* 가 *있는 팀*
- *최첨단 기술* (LangGraph / DSPy / vLLM / 새 모델 의 *바로 사용*) 의 *필수*
- *prototyping 의 *극도 의 빠름* 의 *조직 문화*
- *대규모 batch 추론* (HuggingFace + GPU)

### 둘 다 *적합* — *상황 별 선택*
- *프로덕션 의 *API 서버 = Spring AI*, *batch ML pipeline = Python* 의 *분리* — sparta + airflow / prefect 같은 *조합*
- *MCP 의 *server / client* — *둘 다 지원* — 어떤 stack 이든 *상호 호환*

---

## 10. *MCP* — *둘 의 *통합 접점*

*Model Context Protocol* (Anthropic 2024 11월 발표) — *LLM 의 *도구 / 데이터 source* 의 *표준 protocol*.

```java
// Spring AI 의 MCP Server
@Bean
McpSyncServer mcpServer(OrderQueryTool orderQueryTool) {
    return McpServer.sync()
        .tool(orderQueryTool)
        .build();
}
```

```python
# Python 의 MCP Server
from mcp.server import Server

server = Server("product-search")

@server.tool()
async def search_products(query: str) -> list:
    return await product_repo.search(query)
```

→ *Spring AI 의 *MCP server 가 *Python 의 *Claude Desktop* 에서 *그대로 사용 가능*. *교차 호환* 의 *2026 의 큰 변화*.

내 *cluster 의 *cluster-coordinator hook* — *Spring AI* 가 *MCP server 로 *제공*, *Claude Code 의 *Python* / *Node.js* 에서 *호출*. *language-agnostic 통합*.

---

## 11. 운영 함정 — *내가 *14 개월 *겪은 것들*

### (1) Gemini 451 error (lemuel-xr — 2026-06-21)
*옛 API key 가 *Google 측 의 *블락*. *Spring AI 의 *exception 이 *Resilience4j 의 *circuit breaker 와 *통합* — *자동 fallback*. *Python 이면 *수동 retry / circuit*.

### (2) Token 비용 폭증
*무한 retry* 또는 *streaming 의 *중단 안 됨* → *비용 폭증*. *Spring AI 의 *advisors 의 *budget guard 추가*:

```java
@Component
class BudgetGuardAdvisor implements CallAroundAdvisor {
    @Override
    public AdvisedResponse aroundCall(AdvisedRequest req, CallAroundAdvisorChain chain) {
        if (todaySpend() > DAILY_LIMIT_USD) {
            throw new BudgetExceededException();
        }
        return chain.nextAroundCall(req);
    }
}
```

### (3) PgVector 의 *HNSW 인덱스 의 *느린 빌드*
초기 *10만 row 인덱스* — *수십 분*. *Spring AI 의 *initializeSchema=false* 로 *수동 관리* 권장.

### (4) Tool Call 의 *무한 루프*
*LLM 이 *같은 tool 을 *반복 호출* — *max_tool_calls 제한*:
```java
ChatOptions.builder()
    .toolCallbacks(List.of(...))
    .maxToolRoundTrips(5)
    .build();
```

### (5) Embedding 의 *cache miss*
*매 query 마다 *embedding* — *비용 + latency*. *Caffeine cache 의 *embedding 결과 cache*:
```java
@Cacheable("embeddings")
public List<Float> embed(String text) {
    return embeddingModel.embed(text);
}
```

---

## 12. 마치며 — *작은 결론*

Spring AI 의 *진짜 가치* — *기존 Spring 운영 노하우 의 *완전 상속*. *14 년 의 *Spring Boot 의 *안정성 / observability / security* 가 *AI 부분 에도 *자동 적용*. *별도 운영 의 *추가 비용 없음*.

Python 의 *진짜 가치* — *생태계 의 *압도적 우위*. *모든 새 모델 / 새 기법* 이 *Python 에 먼저 등장*. *최첨단 의 *현장 의 *기본 언어*.

내 *sparta 의 ai-service* — *Spring AI 의 *합리적 선택*. 그러나 *lemuel-xr 의 *RAG + Scene 분기* 의 *복잡 도* 가 *수개월 후 *Python 으로 *분리 검토 의 *가능성 도 *남김*. *기술 의 선택 은 *조직 의 *상황 의 *함수*. *어느 한 쪽 의 우월 함* 의 *주장* 은 *비현실 적*.

**핵심 메시지**: *팀 의 *기존 stack + 운영 노하우* 가 *기술 선택 의 *제 1 변수*. *최신 기술* 의 *조급 한 도입* 보다 *기존 의 *통합 의 *시간 절감* 이 *대부분 의 경우 *더 큰 가치*. 이게 *14 개월 운영 의 *진짜 학습*.

---

## 참고

- *Spring AI Reference* — [docs.spring.io/spring-ai/reference](https://docs.spring.io/spring-ai/reference/)
- *LangChain Documentation* — [python.langchain.com](https://python.langchain.com)
- *Model Context Protocol* — [modelcontextprotocol.io](https://modelcontextprotocol.io)
- *pgvector* — [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)
- 자매편:
    - [AI Agent Architecture — 단일 모델 의 *분해*](/2026/06/26/ai-agent-architecture-decomposition.html)
    - [Claude Code 의 gstack 과 SKILL.md 의 *harness 관점*](/2026/06/26/claude-code-gstack-skill-md-harness-perspective.html)
    - [AI 코드 머지 전 7 가지 질문](/2026/06/21/ai-code-pr-merge-7-questions-checklist.html)
    - [DB 설계 와 쿼리 — 14 개월 운영 경험](/2026/06/29/db-design-and-query-practical-guide.html)
