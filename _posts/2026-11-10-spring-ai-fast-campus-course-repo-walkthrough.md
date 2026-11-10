---
layout: post
title: "Spring AI 강의 실습 레포 6단 정리 — ChatClient에서 MCP 서버까지, 그리고 공식 동작과 어긋난 두 군데"
date: 2026-11-10 22:26:21 +0900
categories: [ai, spring]
tags: [spring-ai, rag, tool-calling, mcp, ollama, java]
---

[JM-Lab/spring-ai-fast-campus-course](https://github.com/JM-Lab/spring-ai-fast-campus-course)는 패스트캠퍼스 강의 「Spring AI 컨트리뷰터에게 배우는 Spring 기반 LLM & RAG 서비스 개발」의 실습 레포다. README가 밝히듯 멀티 모듈이 아니라 **디렉터리마다 독립 실행되는 Maven 프로젝트 6개**로 되어 있고, 번호 순서대로 한 단계씩 기능이 붙는다. 이 글은 6개 모듈의 코드를 직접 읽고 핵심 구조를 정리한 것이며, 그 과정에서 Spring AI 1.0.0 공식 문서·소스와 맞춰 보다가 **주석·동작이 어긋난 곳 두 군데**를 찾아 따로 적었다.

기준 시점: 레포 마지막 커밋 2025-07-27(`d5027d8`), 전 모듈 공통 Spring Boot 3.5.0 · Java 21 · Spring AI **1.0.0**. 라이선스 파일은 없다(GitHub API `licenseInfo: null`). 그래서 이 글은 코드를 길게 옮기지 않고 구조와 핵심 줄만 인용한다.

## 한눈에 보기

| # | 모듈 | 새로 붙는 것 | 기본 LLM |
| --- | --- | --- | --- |
| 1 | `starter` | ChatClient 맛보기, Ollama 로컬 환경, SimpleChat REST | Ollama |
| 2 | `chat` | Chat Memory Advisor, 스트리밍 CLI, call/stream REST, Structured Output | Ollama |
| 3 | `rag-chat` | ETL 파이프라인, `RetrievalAugmentationAdvisor`, 벡터스토어 교체 | Ollama + bge-m3 임베딩 |
| 4 | `tool-chat` | `@Tool` 날씨 도구, returnDirect, 예외 처리 | OpenAI |
| 5 | `mcp-chat` | MCP **클라이언트** — 외부 Python 서버 + 6번 서버를 stdio로 연결 | OpenAI |
| 6 | `mcp-server` | MCP **서버** — 3번 RAG와 4번 날씨 도구를 MCP로 노출 | Ollama |

5번과 6번이 서로 물려 있다는 점이 이 레포의 설계 포인트다. 6번을 jar로 빌드하면 5번이 그 jar를 자식 프로세스로 띄워 도구를 가져다 쓴다. 3·4번에서 만든 것이 마지막에 "다른 앱이 부를 수 있는 도구"가 되는 구성이다.

## ① starter — 모델 두 개를 같이 두는 설정

starter와 chat의 `application.properties`는 Ollama와 OpenAI 스타터를 **둘 다** 넣고 `spring.ai.model.chat=ollama`로 하나를 고른다. 두 ChatModel 자동구성이 동시에 뜨면 `ChatClient.Builder`가 어느 쪽인지 모호해지기 때문이다.

볼 만한 점 두 가지:

- OpenAI 쪽은 실제 OpenAI가 아니라 **GitHub Models**(`base-url=https://models.github.ai/inference`, `completions-path=/chat/completions`, 모델 `openai/gpt-4.1-nano`)를 가리킨다. OpenAI 호환 API라 `base-url`과 `completions-path`만 바꿔 붙인 것이다([GitHub Docs — GitHub Models](https://docs.github.com/en/github-models)).
- Ollama 모델은 `hf.co/rippertnt/HyperCLOVAX-SEED-Text-Instruct-1.5B-Q4_K_M-GGUF`. Ollama는 Hugging Face의 GGUF 모델을 `hf.co/<user>/<repo>` 이름으로 바로 받을 수 있고, `pull-model-strategy=when_missing`이면 없을 때만 자동으로 받는다([Spring AI — Ollama Chat](https://docs.spring.io/spring-ai/reference/1.0/api/chat/ollama-chat.html)). 설정 주석은 "Structured Output·Tool Calling을 쓰려면 mistral 7B(약 7GB 메모리)로 바꾸라"고 적고 있다 — 1.5B 소형 모델로는 그 기능이 불안정하다는 강의 측 판단이다(강의 주장, 이 글에서 재현하지 않음).

## ② chat — Advisor 체인으로 기억·로깅·구조화 출력

이 모듈의 중심은 `ChatService` 생성자 한 줄이다.

```java
this.chatClient = chatClientBuilder.defaultAdvisors(advisors).build();
```

`Advisor[]`를 빈으로 주입받기 때문에, 설정 클래스에 `SimpleLoggerAdvisor`와 `MessageChatMemoryAdvisor`를 빈으로 등록만 하면 체인에 자동으로 들어간다. Advisor는 ChatClient 호출 전후를 가로채는 인터셉터 체인이다([Spring AI — Advisors API](https://docs.spring.io/spring-ai/reference/1.0/api/advisors.html)).

- **대화 기억**: `MessageWindowChatMemory.builder().maxMessages(10)` + `MessageChatMemoryAdvisor`. 요청마다 `advisors.param(ChatMemory.CONVERSATION_ID, conversationId)`로 대화 ID를 넘겨 대화별로 기억을 나눈다. CLI는 `"cli"` 고정 ID를 쓴다.
- **스트리밍**: `.stream().content()`가 `Flux<String>`을 돌려주고, REST는 `text/event-stream`(SSE), CLI는 `doOnNext(System.out::print)`로 토큰을 흘린다.
- **구조화 출력**: `/chat/emotion`은 `.call().entity(EmotionEvaluation.class)` 한 줄로 응답을 `record EmotionEvaluation(Emotion emotion, List<String> reason)`에 담는다. Spring AI가 레코드에서 JSON 스키마 지시문을 만들어 프롬프트에 붙이고 응답을 역직렬화한다([Spring AI — Structured Output Converter](https://docs.spring.io/spring-ai/reference/1.0/api/structured-output-converter.html)).

> **어긋남 ①** — 설정 주석은 `MessageWindowChatMemory`가 "초과 시 오래된 메시지를 제거하며, **SystemMessage는 보관하지 않음**"이라고 적는다. 공식 문서와 1.0.0 소스는 반대다: "오래된 메시지는 지우되 **system message는 보존**한다(preserving system messages)", 그리고 기본 창 크기는 20이다([Spring AI — Chat Memory](https://docs.spring.io/spring-ai/reference/1.0/api/chat-memory.html), [소스 `MessageWindowChatMemory.java` v1.0.0](https://github.com/spring-projects/spring-ai/blob/v1.0.0/spring-ai-model/src/main/java/org/springframework/ai/chat/memory/MessageWindowChatMemory.java)). 새 SystemMessage가 들어오면 이전 SystemMessage를 교체하는 동작은 있지만, "보관하지 않는다"는 아니다. 코드 자체는 문제없고 주석만 틀렸다. 같은 주석이 `mcp-chat`에도 복사돼 있다.

## ③ rag-chat — ETL과 RAG Advisor를 빈으로 조립

RAG는 두 갈래로 나뉜다. 기동 시 한 번 도는 **ETL**과 질문마다 도는 **검색 증강**이다([Spring AI — ETL Pipeline](https://docs.spring.io/spring-ai/reference/1.0/api/etl-pipeline.html), [Spring AI — RAG](https://docs.spring.io/spring-ai/reference/1.0/api/retrieval-augmented-generation.html)).

**ETL (`ApplicationRunner`, `@Order(1)`로 CLI보다 먼저)**

- Extract — `TikaDocumentReader`로 `classpath:fastcampus-springai.pdf`(강의 소개 PDF)를 읽는다. 위치 패턴이 프로퍼티라 여러 파일로 늘리기 쉽다.
- Transform — 직접 만든 `LengthTextSplitter(400, 200)`: **글자 수 400 단위, 200자 겹침**. 공식 `TokenTextSplitter`가 토큰 기준이라면 이건 문자 기준 슬라이딩 윈도다. 겹침이 50%라 청크 수가 대략 두 배가 되지만 문장이 경계에서 잘려도 앞뒤 청크 중 하나엔 온전히 남는다. LLM으로 키워드 메타데이터를 다는 `KeywordMetadataEnricher(chatModel, 3)`도 빈으로 준비돼 있으나 파이프라인에선 주석 처리돼 있다.
- Load — `DocumentWriter[]` 배열 주입. `VectorStore`도 `DocumentWriter`를 구현하므로, 콘솔에 청크를 JSON으로 찍는 디버그 writer와 벡터스토어가 **같은 배열에 들어가 동시에** 쓰인다. 작지만 영리한 패턴이다.

**벡터스토어 교체**: 기본은 `app.vectorstore.in-memory.enabled=true` → `SimpleVectorStore`(메모리). 끄면 Elasticsearch(`dims 1024`, cosine)나 OpenSearch 스타터로 바꾸도록 설정이 준비돼 있다. 1024는 임베딩 모델 **bge-m3**의 출력 차원이다([Chen et al., 2024, arXiv:2402.03216](https://arxiv.org/abs/2402.03216)). 설정 주석대로 Ollama 기본 임베딩 `mxbai-embed-large`는 영어용이라 한국어 PDF를 위해 다국어 모델로 바꾼 것이다(Ollama 기본값은 [Spring AI — Ollama Embeddings](https://docs.spring.io/spring-ai/reference/1.0/api/embeddings/ollama-embeddings.html)에서 확인).

**검색 증강 (`RetrievalAugmentationAdvisor`)**

```java
.queryAugmenter(ContextualQueryAugmenter.builder().allowEmptyContext(true).build())
.documentRetriever(VectorStoreDocumentRetriever.builder()
        .similarityThreshold(0.3).topK(3).vectorStore(vectorStore).build())
```

- `topK 3`, 유사도 하한 `0.3`.
- `allowEmptyContext(true)` — 기본값(false)이면 검색 결과가 없을 때 모델에게 **답하지 말라**고 지시한다. true로 두면 문서가 없어도 일반 지식으로 답한다([Spring AI — RAG](https://docs.spring.io/spring-ai/reference/1.0/api/retrieval-augmented-generation.html)). 강의용 데모엔 편하지만, "근거 없으면 모른다고 하라"가 필요한 서비스에선 반대로 둬야 하는 스위치다.
- `MultiQueryExpander`(질문 여러 개로 확장), `TranslationQueryTransformer`(질문 번역)는 주석으로만 남아 있다 — 다음 단계 실습용 자리.
- CLI 모드에선 `DocumentPostProcessor`를 끼워 **검색된 청크와 점수를 화면에 먼저 찍고** 답을 이어 출력한다. RAG가 무엇을 근거로 답했는지 눈으로 보는 장치다.
- `RagChatService`는 `temperature 0.0`. 검색 문서에 충실해야 하니 다양성을 끈다(코드 주석의 의도).

> **어긋남 ② (코드 대조로 찾음, 실행 재현은 안 함)** — 메타데이터 필터를 넘기는 부분:
>
> ```java
> filterExpressionAsOpt.ifPresent(filterExpression -> chatClientRequestSpec.advisors(
>         advisors -> advisors.param(VectorStoreDocumentRetriever.FILTER_EXPRESSION, filterExpressionAsOpt)));
> ```
>
> 람다 안에서 꺼낸 `filterExpression`(String)이 아니라 바깥의 **`filterExpressionAsOpt`(Optional) 자체**를 넣고 있다. Spring AI 1.0.0의 `VectorStoreDocumentRetriever`는 컨텍스트 값이 `Filter.Expression`이 아니면 `toString()`을 필터 파서에 넘긴다([소스 v1.0.0 L109–120](https://github.com/spring-projects/spring-ai/blob/v1.0.0/spring-ai-rag/src/main/java/org/springframework/ai/rag/retrieval/search/VectorStoreDocumentRetriever.java#L109-L120)). `Optional.toString()`은 `Optional[source == 'a.pdf']` 꼴이라 필터 문법으로 파싱될 수 없다. 필터를 **비워 두면** `ifPresent`가 아예 안 돌아서 드러나지 않는다 — 기본 설정(`app.cli.filter-expression=` 빈 값)으로 돌리면 멀쩡해 보이는 이유다. 고치려면 `param(FILTER_EXPRESSION, filterExpression)`. 같은 코드가 `mcp-server`의 `RagChatService`에도 있다(거기선 항상 `Optional.empty()`로 불러 영향은 없다).

## ④ tool-chat — `@Tool` 하나로 외부 API를 모델 손에

날씨 도구는 [wttr.in](https://github.com/chubin/wttr.in)을 `WebClient`로 부른다. 두 메서드가 대비를 이룬다.

| 도구 | 반환 | `returnDirect` | 의미 |
| --- | --- | --- | --- |
| `getWeather` | wttr.in `format=`으로 만든 **완성 문장** | `true` | 모델을 다시 거치지 않고 도구 결과를 그대로 사용자에게 |
| `getWeatherDetails` | `format=j1` JSON → 3일 예보·천문 `record` | `false` | 구조화 데이터를 모델에 돌려보내 모델이 문장을 만든다 |

`returnDirect=true`면 `ToolCallingManager`가 결과를 모델로 보내지 않고 바로 호출자에게 돌려준다. 단, 한 번에 여러 도구가 호출되면 **모두 true여야** 직접 반환된다는 조건이 공식 문서에 있다([Spring AI — Tool Calling](https://docs.spring.io/spring-ai/reference/1.0/api/tools.html)). 이미 사람이 읽을 문장이면 토큰과 지연을 아끼고, 원재료 데이터면 모델에 해석을 맡기는 분업이다. `record`의 `@Schema(description=...)`은 사람을 위한 문서이자 모델이 필드 뜻을 읽는 단서가 된다.

나머지 설정:

- `ToolCallingChatOptions.internalToolExecutionEnabled(true)` — 도구 실행 루프를 Spring AI가 내부에서 돈다(기본값, 명시용). `temperature 0.2`.
- **예외 처리**: `tool-chat`은 `DefaultToolExecutionExceptionProcessor(false)`, `mcp-chat`은 `(true)`. false면 RuntimeException 메시지를 **모델에게 돌려보내** 모델이 "조회에 실패했습니다" 식으로 수습하게 하고, true면 예외를 서비스 코드로 던진다. checked exception과 Error는 설정과 무관하게 항상 던져진다([Spring AI — Tool Calling](https://docs.spring.io/spring-ai/reference/1.0/api/tools.html)). 두 모듈이 일부러 반대 값을 써서 차이를 보여 준다.

## ⑤ mcp-chat — MCP 클라이언트: 도구를 "가져와" 쓴다

4번에선 도구를 같은 JVM에 `@Tool`로 두었다면, 5번은 도구가 **다른 프로세스**에 있다. `spring-ai-starter-mcp-client`가 설정된 서버들에 붙어 도구 목록을 받아 `ToolCallbackProvider` 빈으로 만들어 주고([Spring AI — MCP Client Boot Starter](https://docs.spring.io/spring-ai/reference/1.0/api/mcp/mcp-client-boot-starter-docs.html)), 서비스는 그걸 펼쳐 ChatClient에 붙인다.

```java
ToolCallback[] toolCallbacks = Arrays.stream(toolCallbackProviders)
        .flatMap(provider -> Arrays.stream(provider.getToolCallbacks()))
        .peek(cb -> log.info("ToolDefinition – name: {}, ...", cb.getToolDefinition().name()))
        .toArray(ToolCallback[]::new);
```

`application.yaml`의 stdio 연결 두 개:

1. `weather-mcp-server` — Python 패키지 `mcp_weather_server`를 `python -m`으로 실행(외부 MCP 서버).
2. `local-mcp-server` — **6번 모듈 jar**를 `java -jar ... --spring.ai.mcp.server.stdio=true --spring.main.web-application-type=none --spring.main.banner-mode=off --logging.pattern.console=`로 실행.

2번의 인자 네 개는 장식이 아니다. MCP stdio 규격은 서버가 **stdout에 유효한 MCP 메시지 외엔 아무것도 쓰면 안 된다**고 정한다([MCP Spec 2025-06-18 — Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)). Spring Boot 배너와 콘솔 로그가 stdout으로 나가면 JSON-RPC 스트림이 깨지므로 배너를 끄고 콘솔 로그 패턴을 비운다. 웹 서버도 필요 없으니 끈다.

주의: 경로가 `/Users/jm/...`로 작성자 PC에 박혀 있다. 그대로 클론해 돌리면 실패하므로 Python·jar 경로를 자기 환경에 맞게 고쳐야 한다. SSE 연결(`http://localhost:8081`)은 주석으로 대안이 남아 있다.

## ⑥ mcp-server — 만든 기능을 MCP 도구로 내보내기

`spring-ai-starter-mcp-server-webmvc`를 쓰고, 핵심은 빈 하나다.

```java
@Bean
public ToolCallbackProvider toolCallbackProvider(Tools tools) {
    return MethodToolCallbackProvider.builder().toolObjects(tools).build();
}
```

`Tools`에 `@Tool` 세 개가 있다: 3번의 RAG 서비스를 감싼 `ragTool`("Spring AI 강의에 대해 RAG 기반 답변", returnDirect), 4번의 `getWeather`, `getWeatherDetails`. 즉 **RAG 파이프라인 전체가 MCP 도구 하나**가 되어, 5번 같은 클라이언트(또는 MCP를 지원하는 다른 앱)가 "강의에 대해 물어보는 도구"로 쓸 수 있다. 서버 `instructions`에 서버의 용도를 한국어로 적어 둔 것도 클라이언트 쪽 모델이 도구를 고를 때의 단서다.

전송 방식은 둘을 겸한다. webmvc 스타터는 Spring MVC 기반 SSE 전송과 선택적 stdio를 지원하고([Spring AI — MCP Server Boot Starter](https://docs.spring.io/spring-ai/reference/1.0/api/mcp/mcp-server-boot-starter-docs.html)), 기본은 포트 8081 SSE(`sse-message-endpoint: /mcp/messages`), 5번이 띄울 땐 인자로 stdio 모드가 된다. 4번과 달리 WebClient 결과에 `publishOn(Schedulers.boundedElastic())`을 붙인 것은 MCP 서버의 요청 처리 스레드에서 `block()`할 때 생길 수 있는 블로킹 문제를 피하려는 의도로 읽힌다(코드에 주석은 없음 — 추정).

한 가지 시점 메모: 이 레포가 쓰는 HTTP+SSE 전송은 MCP 규격 2025-03-26부터 **Streamable HTTP로 대체**되어, 현행 규격(2025-06-18)에선 하위호환용 deprecated 전송이다([MCP Spec — Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)). stdio는 그대로 표준이다.

## 읽고 나서 — 이 레포가 잘 보여 주는 것

1. **"빈으로 등록하면 체인에 들어간다"는 Spring식 조립.** Advisor 배열, DocumentWriter 배열, ToolCallbackProvider 배열 — 세 곳 모두 배열 주입으로 확장 지점을 열어 둔다. 기능 추가가 `@Bean` 하나다.
2. **같은 서비스 골격의 반복.** `ChatService` → `RagChatService` → `ToolChatService` → `McpChatService`가 거의 같은 모양(`buildChatClientRequestSpec` + `call`/`stream`)이고 생성자의 `defaultXxx`만 늘어난다. 단계별 차이가 눈에 잘 들어온다.
3. **CLI와 REST를 같은 서비스에 함께 둔다.** `@ConditionalOnProperty`로 CLI를 켜고 끄며, 콘솔 appender를 떼어 로그가 대화를 덮지 않게 한다.
4. **로컬 우선.** Ollama + 1.5B GGUF + in-memory 벡터스토어로 API 키 없이 1~3·6번을 돌릴 수 있다. 4·5번만 OpenAI(GitHub Models) 키가 필요하다.

## 이 정리의 한계

- **코드를 읽었을 뿐 실행하지 않았다.** 빌드·기동·응답 품질은 확인하지 않았다. 위 "어긋남 ②"도 소스 대조에 근거한 판단이며 실제 예외 메시지를 재현한 것은 아니다.
- 레포에 **테스트·실습 정답 외의 강의 설명은 없다.** 각 단계 "왜 이렇게 했나"는 코드 주석과 README에서만 읽었다. 강의 영상 내용은 반영되지 않았다.
- 레포는 **Spring AI 1.0.0** 기준이다. 2026-11 현재 Maven Central의 `spring-ai-bom` 최신은 2.0.x이고, 1.0 → 1.1 → 2.0 사이에 API·스타터 이름이 바뀐 부분이 있을 수 있다. 이 글의 동작 설명은 모두 1.0 문서·소스 기준이다.
- 소형 모델로 Structured Output·Tool Calling이 불안정하다는 설정 주석은 강의 측 주장이며 이 글에서 검증하지 않았다.

## References

- 레포: [JM-Lab/spring-ai-fast-campus-course](https://github.com/JM-Lab/spring-ai-fast-campus-course) (커밋 `d5027d8`, 2025-07-27)
- Spring AI 1.0 Reference — [ChatClient](https://docs.spring.io/spring-ai/reference/1.0/api/chatclient.html) · [Advisors](https://docs.spring.io/spring-ai/reference/1.0/api/advisors.html) · [Chat Memory](https://docs.spring.io/spring-ai/reference/1.0/api/chat-memory.html) · [Structured Output](https://docs.spring.io/spring-ai/reference/1.0/api/structured-output-converter.html)
- Spring AI 1.0 Reference — [ETL Pipeline](https://docs.spring.io/spring-ai/reference/1.0/api/etl-pipeline.html) · [Retrieval Augmented Generation](https://docs.spring.io/spring-ai/reference/1.0/api/retrieval-augmented-generation.html) · [Tool Calling](https://docs.spring.io/spring-ai/reference/1.0/api/tools.html)
- Spring AI 1.0 Reference — [Ollama Chat](https://docs.spring.io/spring-ai/reference/1.0/api/chat/ollama-chat.html) · [Ollama Embeddings](https://docs.spring.io/spring-ai/reference/1.0/api/embeddings/ollama-embeddings.html) · [MCP Client Boot Starter](https://docs.spring.io/spring-ai/reference/1.0/api/mcp/mcp-client-boot-starter-docs.html) · [MCP Server Boot Starter](https://docs.spring.io/spring-ai/reference/1.0/api/mcp/mcp-server-boot-starter-docs.html)
- Spring AI 소스 v1.0.0 — [`MessageWindowChatMemory.java`](https://github.com/spring-projects/spring-ai/blob/v1.0.0/spring-ai-model/src/main/java/org/springframework/ai/chat/memory/MessageWindowChatMemory.java) · [`VectorStoreDocumentRetriever.java`](https://github.com/spring-projects/spring-ai/blob/v1.0.0/spring-ai-rag/src/main/java/org/springframework/ai/rag/retrieval/search/VectorStoreDocumentRetriever.java)
- Model Context Protocol — [Specification 2025-06-18: Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- Lewis et al., 2020. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)
- Chen et al., 2024. *BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation.* [arXiv:2402.03216](https://arxiv.org/abs/2402.03216)
- [GitHub Docs — GitHub Models](https://docs.github.com/en/github-models)
- [chubin/wttr.in](https://github.com/chubin/wttr.in)
