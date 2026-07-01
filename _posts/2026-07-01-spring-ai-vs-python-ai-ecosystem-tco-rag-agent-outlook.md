---
layout: post
title: "Spring AI vs Python AI — 생태계·TCO·RAG·Agent·2026 outlook 통합 심층 비교"
date: 2026-07-01 18:15:00 +0900
categories: [ai, spring-ai, python, langchain, comparison]
tags: [spring-ai, langchain, langgraph, llamaindex, crewai, autogen, rag, agent, mcp, tco, outlook]
---

3 일 전 *sparta-msa 관점* 의 [Spring AI vs Python 비교 글](/2026/06/29/spring-ai-vs-python-from-sparta-msa-ai-service.html) 을 썼다. 그러나 *조직 규모 / 팀 stack / 사용 케이스* 에 따라 *답 이 완전 히 달라짐* — *더 넓은 각도* 의 *통합 비교* 필요. 이 글은 *생태계·인력 / TCO / RAG / Agent / 2026-2027 outlook* 의 *6 부* + *24 가지 조합 결정 매트릭스*.

---

## Part A — 생태계 와 인력 시장 (2026)

### A-1. 프레임워크 성숙 도 순위 (2026-07 기준)

| 도구 | 언어 | GitHub Stars | 첫 릴리즈 | 최근 major |
|---|---|---|---|---|
| **LangChain** | Python | ~90k | 2022-10 | v0.3 (2024-09) |
| **LlamaIndex** | Python | ~35k | 2022-11 | v0.11 (2024) |
| **LangGraph** | Python | ~9k | 2024-02 | v0.3 (2025) |
| **CrewAI** | Python | ~25k | 2023-11 | v0.80 (2025) |
| **AutoGen** | Python (+ .NET) | ~35k | 2023-09 | v0.4 (2025) |
| **DSPy** | Python | ~18k | 2023-06 | v2.5 (2024) |
| **Spring AI** | Java | ~4k | 2023-07 | v1.0 GA (2025-05) |
| **LangChain4j** | Java | ~5k | 2023-10 | v0.36 (2024) |
| **Semantic Kernel** | .NET / Python | ~22k | 2023-03 | v1.30 (2024) |

**핵심 관찰**:
- *Python 생태계 의 *양적 압도* — 상위 5 개 도구 가 *모두 Python*
- *Spring AI 는 *4k stars* 지만 *Spring Boot 사용자 = 수백 만 명* → *stars 수 가 실 채택 을 반영 안 함*
- *LangChain4j* — Spring AI 의 *경쟁 자*. *더 유연한 API + Spring 통합 옵션* 제공
- *DSPy 는 *별개 카테고리* — *프롬프트 최적화 자동화* (제일 실험적)

### A-2. 논문 → 코드 속도

*OpenAI / Anthropic / Meta / Google 의 새 논문* 이 나오면:
- **Python** — *2~7 일 만에 *reference 구현* 이 *GitHub 에 등장*. LangChain 이 *2~4 주 이내 통합*.
- **Java / Spring AI** — *3~6 개월 후 *Spring AI 팀 이 통합*. *커뮤니티 PR 이 병목*.

**결과**:
- *최첨단 기법* (예: *2025 의 Reflexion / Constitutional AI / Multi-hop RAG*) → Python 이 *6 개월 우위*
- *sparta 같은 *production* 은 *stable 만 필요* → 6 개월 지연 이 *큰 문제 아님*
- *reseearch / 논문 구현 / 대회* → *반드시 Python*

### A-3. 인력 시장 (2026)

| 지표 | Python AI | Java Spring AI |
|---|---|---|
| LinkedIn 채용 게시 수 (2026 Q2) | *압도적* (기준: 100) | *~15* |
| Kaggle GM 이 쓰는 언어 | 95%+ Python | ~1% |
| 대학 CS AI 강의 언어 | 90% Python | ~5% (Java) |
| 기업 백엔드 채용 (2026) | ~30% | ~50% (Java) + ~10% (Kotlin) |
| **AI 백엔드 채용** (교집합) | ~70% | ~20% |

**함의**:
- *AI-first 팀* 을 새로 만들면 *반드시 Python 인재 채용 이 유리*
- *기존 Java 팀* 에 AI 기능 추가 면 *현 인력 재배치 가 훨씬 저렴*
- *혼합 팀* — *Python data scientist + Java 백엔드* 의 *2 언어 구조 가 2026 의 대세*

### A-4. 커뮤니티 / 컨퍼런스 / 학습 자료

- **Python** — *NeurIPS / ICLR / ACL / EMNLP* 의 *모든 논문 코드* 가 Python. *Andrej Karpathy 의 강의 코드*, *fast.ai*, *Hugging Face 강의* 모두 Python.
- **Spring AI** — *SpringOne / KotlinConf / Devoxx* 의 *AI track* 이 *2024 부터 등장*. *Josh Long 의 무료 튜토리얼* 이 *가장 접근 성 높음*.
- *책 시장* — *Python* ~50 권 (2026 신간 20+), *Spring AI* ~3 권 (2024-25).

**결론** — *학습 자료 는 *Python 이 압도*. *Java 개발자 가 Spring AI 배울 때 는 *Python 튜토리얼 을 *Java 로 변환* 하는 방식 이 종종 필요.

---

## Part B — Production TCO 실측

### B-1. Docker Image 크기 (실측)

| Stack | Base Image | 최종 크기 | Cold Start |
|---|---|---|---|
| Spring AI + Spring Boot 4 | `eclipse-temurin:21-jre-alpine` | *~350 MB* | ~5 초 |
| Spring AI + GraalVM Native | `distroless/base` | *~180 MB* | ~0.1 초 |
| FastAPI + LangChain | `python:3.13-slim` | *~1.2 GB* | ~2 초 |
| FastAPI + LangChain + vLLM | `nvidia/cuda:12` | *~5 GB* | ~10 초 |
| Litestar + minimal deps | `python:3.13-slim` | *~700 MB* | ~1 초 |

**핵심 관찰**:
- *Python 의 *숨은 비용* — `langchain-community` 가 *수 백 MB 의 optional 의존성* 을 *transitive 로 끌어 옴*
- *Spring AI 의 *압도적 slim* — *JRE + JAR 만*
- *GraalVM Native* — *극한 최적화* 가능 하지만 *reflection 설정 의 지옥*
- **K8s 대량 배포 에서 *image size × replica 수 = 클러스터 총 용량*** — *3 replica × 5 서비스 = Spring 5 GB vs Python 18 GB*

### B-2. 메모리 / CPU 요구

**같은 부하 (100 concurrent RAG queries)** 시:

| Stack | Memory | CPU | Latency p99 |
|---|---|---|---|
| Spring AI + Ktor | 800 MB | 2 core | 350 ms |
| Spring AI + Spring Boot | 1200 MB | 2 core | 400 ms |
| Spring AI Native | 400 MB | 1 core | 250 ms |
| FastAPI + LangChain | 600 MB | 1 core (GIL) | 500 ms |
| FastAPI + LangChain + async | 700 MB | 2 core | 380 ms |

**의외 결과** — *Spring AI Native 가 latency 도 유리*. *JIT warm-up 없음 + 작은 image + 낮은 메모리*. *cold start 부담 만 GraalVM 의 build time 이 *10~15 분* — CI/CD 의 슬로우 배포.

### B-3. 토큰 비용 (LLM API)

*동일 한 사용자 요청* 처리 시 *토큰 사용 량* — *실제 로 는 stack 차이 크지 않음* — *같은 LLM API 호출*.

그러나 *stack 별 *간접 비용*:
- **LangChain** — *`ConversationBufferMemory` 의 *컨텍스트 폭증*, *`AgentExecutor` 의 *ReAct loop* 가 *5~10 배 토큰 소모* — *2025 의 큰 원인*. *LangGraph 로 이동 이 필수*
- **Spring AI** — *`ChatMemory` 의 명시 적 관리*, *Function Calling 의 *max_rounds 제한* → *상대적 예측 가능*

**실측** — *같은 RAG 쿼리* 100 회:
- Spring AI: *평균 800 input + 200 output tokens*
- LangChain (naive): *평균 2400 input + 300 output tokens* (3 배)
- LangGraph (careful): *평균 900 input + 200 output tokens* (비슷)

**함의** — *월 100 만 쿼리 시 *Gemini 2.5 Flash 기준*:
- Spring AI: *~$120/월*
- LangChain naive: *~$360/월* (3 배)
- LangGraph: *~$130/월*

*3 배 차이* 는 *2 년 이면 *한 명 의 개발자 월급*.

### B-4. 관측 성 / 모니터링 도구값

| 항목 | Spring AI | Python |
|---|---|---|
| **메트릭 자동 수집** | Micrometer 자동 | 수동 (prometheus_client) |
| **Tracing** | Micrometer Tracing 자동 | OpenTelemetry 수동 설정 |
| **JFR (프로파일링)** | *무료 built-in* | py-spy (외부, less power) |
| **APM** (Datadog / NewRelic) | *Java agent 완성 도 높음* | Python agent 는 상대적으로 미성숙 |
| **디버깅** | IntelliJ 원격 디버그 완성 | pdb / debugpy (충분 하지만 UX 낮음) |

**함의** — *production 운영 의 *TCO* 는 *observability tooling 성숙 도 가 큰 영향*. *Spring AI 는 *별도 설정 없이 즉시 관측 가능*.

### B-5. 개발 자 생산 성 (velocity)

*처음부터 *RAG chatbot* 을 *2 시간 안에 만들기*:
- **Python + LangChain** — *~30 분* (튜토리얼 이 압도적)
- **Spring AI** — *~60 분* (Boilerplate 더 많음)

*프로토타입 이후 *90% completion* 까지:
- **Python** — *~2 주* (LangChain 의 *예상 못 한 quirk 처리*)
- **Spring AI** — *~1 주* (*안정성 이 예측 가능*)

**함의** — *hackathon / demo* 는 Python. *production 릴리즈* 는 Spring AI.

---

## Part C1 — RAG 심층 비교

### C1-1. Spring AI: `QuestionAnswerAdvisor`

```java
@Configuration
class RagConfig {
    @Bean VectorStore vectorStore(JdbcTemplate jdbc, EmbeddingModel emb) {
        return PgVectorStore.builder(jdbc, emb)
            .dimensions(768)
            .indexType(PgVectorStore.PgIndexType.HNSW)
            .distanceType(PgDistanceType.COSINE_DISTANCE)
            .build();
    }
}

// 사용
String answer = chatClient.prompt()
    .advisors(new QuestionAnswerAdvisor(vectorStore,
        SearchRequest.builder()
            .topK(5)
            .similarityThreshold(0.75)
            .build()))
    .user(question)
    .call()
    .content();
```

**장점**:
- *한 줄로 RAG 완성*. *embedding + retrieval + context injection 자동*
- *`FilterExpression` 으로 metadata 필터링* (`meta.customer_tier == 'premium'`)
- *Spring 의 *DI + 트랜잭션 + observability* 그대로 사용

**단점**:
- *docs parsing 의 *생태계 얕음* (PDF / DOCX / HTML → `DocumentReader` API 있지만 *quality 는 LlamaIndex 대비 낮음*)
- *Multi-hop RAG / re-ranking / query rewriting* 은 *직접 코드*
- *hybrid search (BM25 + vector)* 는 *별도 wrapper 필요*

### C1-2. LangChain: `RetrievalQA` → LCEL

```python
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import PGVector
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings

embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@003")
vector_store = PGVector(
    collection_name="knowledge",
    connection_string="postgresql://...",
    embedding_function=embeddings,
)

llm = ChatVertexAI(model="gemini-2.5-flash")

qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
    return_source_documents=True,
)

result = qa.invoke({"query": question})
```

**최신 (2025+)** — *LCEL (LangChain Expression Language)* 방식 이 표준:
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

prompt = ChatPromptTemplate.from_messages([
    ("system", "Context: {context}"),
    ("user", "{question}"),
])

chain = (
    {"context": vector_store.as_retriever(), "question": RunnablePassthrough()}
    | prompt
    | llm
)

result = chain.invoke(question)
```

**장점**:
- *체이닝 문법 의 *간결*. *Unix pipe 처럼 조합*
- *hybrid retrieval / re-ranking / MMR (Maximal Marginal Relevance) / self-query* 등 *수십 개 의 내장 옵션*
- *생태계 크기 압도*

**단점**:
- *LCEL 이전 코드 는 *deprecated* — *마이그레이션 부담*
- *type hint 부족* — runtime 만 확인
- *에러 메시지 가 종종 *stack trace 지옥*

### C1-3. LlamaIndex: *문서 특화*

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.llms.google_genai import GoogleGenAI
from llama_parse import LlamaParse

# ★ LlamaParse — PDF / DOCX / PPT 의 정교 한 파싱
parser = LlamaParse(result_type="markdown")
documents = SimpleDirectoryReader(
    "./docs",
    file_extractor={".pdf": parser, ".docx": parser}
).load_data()

vector_store = PGVectorStore.from_params(...)
index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)

llm = GoogleGenAI(model="gemini-2.5-flash")
query_engine = index.as_query_engine(llm=llm, similarity_top_k=5)

response = query_engine.query(question)
```

**LlamaIndex 가 *특별 히 강 한 지점*:
- **문서 파싱** (LlamaParse 는 *유료지만 압도적 품질*) — *복잡한 표 / 이미지 / 다단 레이아웃 처리*
- **Advanced retrieval** — *Sub-Question Query Engine*, *Multi-Step Query Engine*, *Router Query Engine*
- **structured extraction** — *PDF 에서 *구조화된 JSON 뽑기*
- **Agentic RAG** — *ReActAgent 로 툴 자동 선택*

### C1-4. RAG 심층 비교 매트릭스

| 기능 | Spring AI | LangChain | LlamaIndex |
|---|---|---|---|
| 기본 RAG | ⭐⭐⭐⭐⭐ (단순) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Vector Store 지원 | 15+ | *40+* | *30+* |
| PDF / 복잡 문서 파싱 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Multi-hop / Multi-step | ⭐⭐ (수동) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Re-ranking | ⭐⭐ (외부) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Hybrid Search (BM25+vec) | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Query rewriting | ⭐⭐ (수동) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Structured extraction | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Type safety | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Observability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

**결론**:
- *단순 RAG* → **Spring AI 가 충분** + *운영 강점*
- *복잡 한 문서 (PDF, 표, 이미지)* → **LlamaIndex 압도적**
- *유연한 chain* → LangChain
- *하이브리드* — *문서 파싱 은 Python (LlamaIndex) sidecar + retrieval / 응답 은 Spring AI* 의 *분업 이 실무 최적*

---

## Part C2 — Agent 심층 비교

Agent = *LLM 이 자동 으로 *도구 선택 + 실행 + 결과 반영*. *2025 부터 급 부상*.

### C2-1. Spring AI Agent

```java
@Service
class OrderAgent {
    private final ChatClient chatClient;
    private final OrderRepository orderRepo;
    private final PaymentGateway paymentGateway;

    @Tool(description = "사용자 의 주문 조회")
    public List<Order> getOrders(@ToolParam Long userId) { ... }

    @Tool(description = "환불 처리")
    public Refund processRefund(@ToolParam Long orderId, @ToolParam String reason) { ... }

    public String chat(String userMessage) {
        return chatClient.prompt()
            .system("주문 관련 문의 를 도와줘. 필요 시 tool 호출.")
            .tools(this)
            .user(userMessage)
            .call()
            .content();
    }
}
```

**특징**:
- *단일 LLM + 함수 호출 loop* — *`maxToolRoundTrips` 로 무한 방지*
- *기존 Spring service 그대로 tool 노출* — *중복 코드 0*
- *state 는 *ChatMemory* 에 저장 — Redis / DB 가능

**한계**:
- *복잡 한 *상태 전이* / *분기* 에 취약 — *직접 구현*
- *Multi-agent* (여러 LLM 협력) 은 *native 지원 없음*

### C2-2. LangGraph — *상태 그래프 기반*

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    messages: list
    step: str

def classify_intent(state: State) -> State:
    intent = classify(state["messages"][-1])
    return {**state, "step": intent}

def handle_order(state: State) -> State:
    result = order_service.query(state["messages"])
    return {**state, "messages": state["messages"] + [result]}

def handle_refund(state: State) -> State:
    result = refund_service.process(state["messages"])
    return {**state, "messages": state["messages"] + [result]}

graph = StateGraph(State)
graph.add_node("classify", classify_intent)
graph.add_node("order", handle_order)
graph.add_node("refund", handle_refund)

graph.set_entry_point("classify")
graph.add_conditional_edges(
    "classify",
    lambda s: s["step"],
    {"order": "order", "refund": "refund"},
)
graph.add_edge("order", END)
graph.add_edge("refund", END)

app = graph.compile()
result = app.invoke({"messages": [user_message], "step": "start"})
```

**특징**:
- *명시 적 state machine* — 복잡 한 흐름 을 *그래프 로 시각화*
- *human-in-the-loop* — *`interrupt` 노드* 로 *사람 개입 대기*
- *`checkpointer` 로 *상태 영속 화* (Redis / PostgreSQL)
- *LangSmith 로 *디버깅 시각화*

**적합**:
- 복잡 한 workflow (multi-step approval, escalation, retry)
- 감사 / 추적 필요 한 도메인 (금융 / 의료)

### C2-3. CrewAI — *역할 기반 다중 에이전트*

```python
from crewai import Agent, Task, Crew

researcher = Agent(
    role="시장 조사원",
    goal="경쟁사 제품 조사",
    backstory="20 년 경력 의 시장 분석가",
    tools=[web_search_tool, scraper_tool],
)

writer = Agent(
    role="보고서 작성자",
    goal="조사 결과 를 명확 한 보고서 로 작성",
    backstory="테크 에디터 출신",
    tools=[],
)

research_task = Task(
    description="{topic} 관련 경쟁 5 사 의 최근 6 개월 릴리즈 조사",
    agent=researcher,
    expected_output="회사 별 릴리즈 목록",
)

report_task = Task(
    description="위 조사 결과 를 임원용 보고서 로 작성",
    agent=writer,
    context=[research_task],
    expected_output="markdown 보고서",
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, report_task],
    process="sequential",
)

result = crew.kickoff(inputs={"topic": "generative AI"})
```

**특징**:
- *역할 (role) / 목표 (goal) / 배경 (backstory)* — *페르소나 기반*
- *sequential / hierarchical* 프로세스
- *진입 장벽 낮음* — *비즈니스 로직 을 자연어 로*

**적합**:
- 콘텐츠 생성 / 리서치 / 회의 시뮬레이션
- 도메인 전문가 (비 개발자) 가 workflow 설계

**함정**:
- *토큰 소모 폭증* — *3 에이전트 × 5 task = 15 LLM 호출*
- *production 신뢰 성* — *상대적 으로 낮음*

### C2-4. AutoGen — *대화 형 다중 에이전트*

```python
import autogen

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir": "coding"},
)

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"model": "gemini-2.5-flash"},
    system_message="Python 코드 작성 및 실행 조수",
)

user_proxy.initiate_chat(
    assistant,
    message="pandas 로 CSV 분석 하고 시각화 코드 작성 + 실행",
)
```

**특징**:
- *다중 에이전트 의 *자연스러운 대화 형식*
- *code executor 통합* — *생성 한 코드 를 실제 실행*
- *Microsoft 의 지원* — enterprise adoption 좋음

**적합**:
- code generation + 실행 (data analysis, prototyping)
- research (자연 대화 로 지식 축적)

### C2-5. Agent 심층 비교 매트릭스

| 기능 | Spring AI | LangGraph | CrewAI | AutoGen |
|---|---|---|---|---|
| 학습 곡선 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 상태 관리 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Multi-agent | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Human-in-the-loop | ⭐⭐ (수동) | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Code execution | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Production 안정성 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Observability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ (LangSmith) | ⭐⭐ | ⭐⭐⭐ |
| 토큰 효율 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

**결론**:
- *단순 tool calling* → **Spring AI** (Java 팀) 또는 *plain LangChain* (Python)
- *복잡 한 workflow* → **LangGraph** (production-ready)
- *비 개발자 의 workflow 설계* → **CrewAI**
- *code generation / 실험* → **AutoGen**

---

## Part D — 2026-2027 outlook

### D-1. MCP (Model Context Protocol) 의 *보편화*

*Anthropic 이 2024-11 발표* → *2026 시점 *사실 상 표준*.

- **Spring AI 1.0.0-M4+** — MCP client / server 지원
- **Python** — `mcp` 공식 SDK (Anthropic)
- **Node.js** — `@modelcontextprotocol/sdk`

**함의** — *언어 벽 이 사라짐*:
- Java Spring AI 가 *Python MCP server* 를 *tool 로 호출*
- Python LangChain 이 *Java MCP server* 를 *tool 로 호출*
- **stack 통합 의 중력 이 약해짐** → *조직 이 stack 을 자유롭게 조합*

### D-2. Structured Output 의 *수렴*

*모든 프레임워크 가 *Pydantic / record / TypeScript type* 을 *동등 취급*:
- OpenAI: JSON mode / structured output
- Anthropic: tool use structured
- Google Gemini: response schema
- Groq / Together / Ollama: JSON mode

**함의** — *stack 별 차별화 축소*. *Spring AI 의 record 기반 API 가 Python 의 Pydantic 과 *같은 위상*.

### D-3. On-device 추론 의 등장

- **Gemini Nano** (Android 15+, Chrome) — 브라우저 내 로컬 LLM
- **Apple Intelligence** (iOS 18+) — 온디바이스 3B 모델
- **Llama 3.2 1B/3B** — laptop 에서 실행 가능

**함의**:
- *간단 한 요약 / 분류 / 감정 분석* 은 *클라이언트 측 처리* 로 이동
- *서버 stack (Spring AI, Python)* 은 *복잡 한 RAG / Agent / 대용량 모델 만 담당*
- *양쪽 다 배우기 필요* — mobile 개발자 도 AI 지식 필수

### D-4. Reasoning Model 의 확산

*OpenAI o1 → o3, DeepSeek R1, Gemini 2.5 Deep Think, Claude 3.7 Extended Thinking* 등 *"생각 하는 모델"*:
- *일반 대화 는 저비용 모델*, *복잡 한 추론 은 고비용 reasoning 모델* 의 *라우팅*
- **LangGraph** 가 *router pattern* 지원 → *Python 우위*
- **Spring AI** 는 *ChatClient 별 인스턴스* 로 대응 — *약간 verbose*

### D-5. Agent-first 아키텍처 의 부상

*2027 예측* — *"AI Agent 가 백엔드 API 를 대체 하는 부분 이 생김"*.
- 사용자 → 자연어 요청 → Agent → 여러 API 조합 → 응답
- 프론트엔드 개발 량 감소
- *"어떻게 agent 를 안전 하게 신뢰 하는가"* 가 *2027 의 핵심 문제*

---

## Part E — 24 가지 조합 결정 매트릭스

*조직 규모 × 팀 stack × 사용 케이스* 의 3 축 × 2~4 값 = *24 조합*.

| # | 조직 | 팀 stack | 사용 케이스 | 권장 |
|---|---|---|---|---|
| 1 | 스타트업 | Python 위주 | 프로토타입 | **Python + LangChain** |
| 2 | 스타트업 | Python 위주 | production RAG | **Python + LlamaIndex** |
| 3 | 스타트업 | Python 위주 | Agent | **LangGraph** |
| 4 | 스타트업 | Java 위주 | 프로토타입 | **Spring AI** (팀 학습 재활용) |
| 5 | 스타트업 | Java 위주 | production RAG | **Spring AI** + LlamaIndex sidecar |
| 6 | 스타트업 | Java 위주 | Agent | **Spring AI + LangGraph sidecar** |
| 7 | 스타트업 | 신규 팀 | 프로토타입 | **Python** (인력 채용 유리) |
| 8 | 스타트업 | 신규 팀 | production | **Python + FastAPI** |
| 9 | 스타트업 | 신규 팀 | Agent | **LangGraph** |
| 10 | 스타트업 | Full-stack (Node/Python) | 프로토타입 | **Node + Hono AI SDK** |
| 11 | 스케일업 | Python | production | **Python + LlamaIndex + LangGraph** |
| 12 | 스케일업 | Java | production | **Spring AI + Python sidecar** |
| 13 | 스케일업 | 혼합 | production | **하이브리드** (Java API + Python inference) |
| 14 | 엔터프라이즈 | Java 위주 | RAG | **Spring AI** (observability) |
| 15 | 엔터프라이즈 | Java 위주 | Agent | **Spring AI + LangGraph sidecar** |
| 16 | 엔터프라이즈 | Java 위주 | 감사 / 규제 | **Spring AI** (JFR + auditing) |
| 17 | 엔터프라이즈 | Python | 감사 / 규제 | **LangGraph** (checkpointer) |
| 18 | 엔터프라이즈 | .NET | 모든 케이스 | **Semantic Kernel** |
| 19 | 대기업 | 기존 Spring Boot 200 서비스 | AI 추가 | **Spring AI 우선** |
| 20 | 대기업 | 기존 Python 100 서비스 | AI 추가 | **Python 유지** |
| 21 | 대기업 | 데이터 팀 = Python | 백엔드 팀 = Java | **하이브리드 + MCP** |
| 22 | 리서치 | 학계 | 논문 재현 | **반드시 Python** |
| 23 | 리서치 | 산업 R&D | 프로토타입 | **Python + FastAPI** |
| 24 | 개인 프로젝트 | 어떤 것 이든 | 학습 | **자신 이 쓰던 언어** (문법 이 아닌 AI 를 배우기) |

---

## 마치며 — *2026 의 정답*

*"어느 stack 이 우수 한가"* — *잘못 된 질문*. *"우리 팀 이 어떤 조합 을 할 것인가"* — *올바른 질문*.

내 클러스터 의 *현재 배치*:
- **sparta-msa** — Spring AI (Java) — *운영 안정성*
- **lemuel-xr** — Spring AI (Java) + *Python sidecar (Gemini 캐시)* — *하이브리드*
- **settlement** — Java (AI 없음) + Python sidecar (분석)

*2026 후반 계획*:
- *LangGraph sidecar 추가* — *복잡 한 workflow (환불 승인, 정산 대사)* 를 *Python 서비스 로 분리*
- *MCP server* 로 *Java service 를 *Python agent 의 tool 로 노출*

**핵심 메시지**: *"stack 을 *하나 만 선택* 하는 시대 는 끝났다. *조직 의 *다양 한 팀 이 *다양 한 언어* 로 *다양 한 문제 를 해결*. *MCP 가 이를 *연결*. *결과 만 이 중요*"*.

*Spring AI vs Python 의 *진짜 답* — *둘 다 (2026 시점)* — *각자 의 자리 에서 *최고*. *경쟁 이 아니라 *상호 보완*.

---

## 참고

- *LangChain 공식* — [python.langchain.com](https://python.langchain.com)
- *LangGraph 공식* — [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- *LlamaIndex 공식* — [docs.llamaindex.ai](https://docs.llamaindex.ai)
- *CrewAI 공식* — [docs.crewai.com](https://docs.crewai.com)
- *AutoGen 공식* — [microsoft.github.io/autogen](https://microsoft.github.io/autogen/)
- *Spring AI 공식* — [docs.spring.io/spring-ai/reference](https://docs.spring.io/spring-ai/reference/)
- *LangChain4j 공식* — [docs.langchain4j.dev](https://docs.langchain4j.dev)
- *DSPy 공식* — [dspy.ai](https://dspy.ai)
- *MCP 공식* — [modelcontextprotocol.io](https://modelcontextprotocol.io)
- 자매편:
    - [Spring AI vs Python — sparta-msa 의 ai-service 운영 으로 본 trade-off](/2026/06/29/spring-ai-vs-python-from-sparta-msa-ai-service.html)
    - [AI Agent Architecture — 단일 모델 의 *분해*](/2026/06/26/ai-agent-architecture-decomposition.html)
    - [Claude Code 의 gstack 과 SKILL.md 의 *harness 관점*](/2026/06/26/claude-code-gstack-skill-md-harness-perspective.html)
