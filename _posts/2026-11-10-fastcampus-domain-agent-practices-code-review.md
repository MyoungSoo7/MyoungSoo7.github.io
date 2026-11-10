---
layout: post
title: "패스트캠퍼스 '도메인 AI Agent' 실습 코드 8개 뜯어보기 — RAG부터 금융 멀티에이전트까지, 그리고 그대로 돌리면 깨지는 곳"
date: 2026-11-10 22:05:01 +0900
categories: [AI, Agent]
tags: [rag, agent, mcp, smolagents, langgraph, guardrail, multi-agent, finance, code-review]
---

> **검증 범위.** [h-albert-lee/fastcampus-domain-agent-practices](https://github.com/h-albert-lee/fastcampus-domain-agent-practices)를 클론해 노트북 8개를 셀 단위 텍스트로 풀어서 **정적으로** 읽었다. 기준 커밋은 2025-12-26의 `8311f4f`다. OpenAI API를 호출하는 셀은 **실행하지 않았다.** 그래서 이 글에 LLM 출력 품질이나 검색 정확도 수치는 하나도 없다. 직접 돌려 본 것은 세 가지뿐이다. 첫째, 05번의 시저 암호 계산. 둘째, NumPy 2.5.4에서 `ndarray.ptp()` 호출. 셋째, smolagents 1.26.0에서 `@tool` 데코레이터가 docstring을 파싱하는 동작. 결과는 본문에 그대로 적었다.

## 1. 이 리포는 무엇인가

README는 두 줄이다. *"패스트 캠퍼스 "도메인 AI의 모든 것" 강의에서 사용된 코드 모음입니다. 버그나 이슈가 발견되어 강의 영상에 사용된 코드와 일부 달라질 수 있습니다."*

강의 상품명은 「[도메인 AI Agent의 모든 것: 보안 특화 모델 설계부터 금융 멀티 에이전트 구축까지](https://fastcampus.co.kr/data_online_financedomain)」다. 상세 페이지 기준으로 4파트, 82클립, 약 12시간 분량이다. 강사 소개에는 *신한투자증권 AI 솔루션부 AI Engineer, HAE-RAE Research Lead*라고 적혀 있다. 강사 이력 중 *금융 임베딩모델(NMIXX) 개발*이 있는데, 이 모델이 03번 RAG 실습의 기본 임베딩으로 그대로 쓰인다. [NMIXX 모델 카드](https://huggingface.co/nmixx-fin/nmixx-bge-m3)의 인용 저자도 Hanwool Lee다.

라이선스 파일이 없다. 그래서 이 글은 코드를 길게 옮겨 싣지 않고 구조와 판단을 설명하는 데 집중한다.

| # | 노트북 | 다루는 것 |
|---|---|---|
| 01 | word_embedding | 단어 임베딩 기초 |
| 02 | pretrained_language_model | 사전학습 언어모델 |
| 03 | RAG | 청킹 → 질의분해 → BM25·FAISS 하이브리드 → 리랭크 → 생성 → 압축 → RAGAS 평가 |
| 04 | agent | ReAct 1스텝 + "더미 MCP" 서버 + smolagents 래핑 |
| 05 | multiagent | Blackboard vs Hierarchical 조직 구조 비교 |
| 06 | smolagent_langchain | 같은 과제를 CodeAgent / LangGraph / ToolCallingAgent로 구현 |
| 07 | guardrail | Moderation API + 정규식 입력·출력 가드레일 |
| 08 | practical_multiagent | Quant-X: 감사로그·RAG·가드레일·RBAC를 묶은 금융 리서치 시스템 |

강의 페이지 커리큘럼과 비교하면 01–02는 Part 1(자연어처리 입문), 03은 Part 2(LLM과 RAG), 04–07은 Part 3(Agent 이해), 08은 Part 4(금융 Agent 실전)에 해당한다. 이 대응은 내가 추정한 것이다.

## 2. 03 RAG — 이 리포에서 가장 밀도 높은 노트북

장난감 수준의 금융 코퍼스(한국어 문장 10개)를 놓고 RAG 파이프라인의 거의 모든 단계를 한 번씩 거친다. 문장마다 `topic`/`tags` 라벨이 붙어 있고 질의 5개에는 `needs`가 붙어 있다. 이 라벨을 정답셋으로 써서 검색 지표를 직접 계산한다는 점이 좋다.

- **청킹**: NLTK 슬라이딩 윈도와 LangChain `RecursiveCharacterTextSplitter(220, 40)`를 비교한다.
- **질의 분해**: gpt-4o-mini에 JSON 배열을 요구하고, 실패하면 3번까지 재시도한다. 함수 이름은 `rule_rewrite`인데 실제로는 LLM을 부른다. 이름과 동작이 어긋나 있다.
- **검색**: FAISS `IndexFlatIP`(정규화 벡터 → 코사인)와 `BM25Okapi`를 따로 돌린 뒤, 둘을 min-max 정규화하고 선형 결합한다.

$$
s_{\text{hyb}}(d) = \lambda \cdot \frac{s_{\text{bm25}}(d) - \min s_{\text{bm25}}}{\operatorname{ptp}(s_{\text{bm25}}) + \epsilon} + (1-\lambda)\cdot \frac{s_{\cos}(d) - \min s_{\cos}}{\operatorname{ptp}(s_{\cos}) + \epsilon}
$$

  $$\lambda$$는 0.3, 0.5, 0.7로 스윕한다. 서브쿼리가 여러 개면 문서별 점수를 max-pool한다. LangChain `EnsembleRetriever(weights=[0.4, 0.6])` 버전도 따로 있다.
- **지표**: P@k, R@k, MRR, nDCG@k를 직접 구현한다.
- **리랭크**: `BAAI/bge-reranker-v2-m3` CrossEncoder를 쓴다.
- **압축**: LLMLingua `PromptCompressor`를 쓴다. 근거 논문인 [Jiang et al., 2023](https://arxiv.org/abs/2310.05736)은 *"up to 20x compression with little performance loss"*라고 주장한다. 다만 이건 GSM8K·BBH 등 영어 데이터셋에서 낸 저자 측 수치다. 한국어 금융 문장에서 같은 결과가 나오는지는 이 노트북이 보여주지 않는다. 노트북은 `target_token=10`이라는 극단적인 값을 쓰기 때문이다.
- **평가**: RAGAS(context_precision / recall / answer_relevance)로 평가한다. 노트북에는 *Colab에서는 ragas 0.3.9만 된다*는 메모가 있다.

**함정 ① — `ndarray.ptp()`.** 위 수식의 $$\operatorname{ptp}$$가 노트북 앞쪽에서는 `np.ptp(bm)`로, 뒤쪽 A/B 섹션에서는 `bm.ptp()`로 쓰였다. NumPy 2.5.4에서 직접 호출해 보니 결과는 이렇다.

```
AttributeError: 'numpy.ndarray' object has no attribute 'ptp'
```

메서드 형태는 NumPy 2에서 제거됐다. 그래서 그 셀만 터진다. 노트북이 `numpy`를 고정(pin)하지 않았으므로 Colab에 NumPy 2가 깔려 있으면 재현된다. 고치려면 `np.ptp(bm)`로 통일하면 된다.

**함정 ② — 한국어에 `nltk.word_tokenize`.** BM25 토크나이저가 영어용 공백·구두점 분리기다. "HBM3E를"과 "HBM3E"가 서로 다른 토큰이 된다. 그러면 하이브리드에서 BM25 쪽 기여가 과소평가될 수 있다. 다만 이건 **정적 판단**이고 수치로 측정하지는 않았다. 한국어라면 형태소 분석기(Kiwi, MeCab 등)로 바꿔 놓고 $$\lambda$$ 스윕을 다시 보는 게 먼저다.

**함정 ③ — 정답 라벨이 너그럽다.** 관련 문서 판정이 *topic 또는 tags 중 하나라도 겹치면 관련*이라는 OR 조건이다. 코퍼스가 10문장이고 태그가 겹치는 문서가 많다. 그래서 P@k가 실제보다 후하게 나올 수 있다. 지표 계산 방법을 익히는 실습으로는 충분하지만, 여기서 나온 숫자를 모델 비교 근거로 쓰면 안 된다.

## 3. 04 Agent — "MCP"라고 부르지만 MCP는 아니다

이 노트북은 ReAct의 원리를 1스텝으로 보여준다. ReAct는 [Yao et al.](https://arxiv.org/abs/2210.03629)의 *"reasoning traces and task-specific actions in an interleaved manner"*를 말한다. 그리고 FastAPI로 **더미 MCP 서버**를 띄운다.

- `MANIFEST`에 도구 3개(`calc_add`, `fx_convert`, `kb_search`)를 등록한다. 각 도구에는 JSON Schema 입출력 정의가 붙어 있다. `fx_convert`는 환율을 1350원으로 고정해 둔다.
- 엔드포인트는 `GET /manifest`, `GET /resources/kb.corpus`, `POST /tools/{name}`이다. 입력은 `jsonschema`의 `Draft202012Validator`로 검증하고, 실패하면 400을 돌려준다.
- 서버는 스레드에서 `127.0.0.1:8000`으로 뜬다.
- 도구 선택(`decide_tool`)은 LLM이 아니라 **키워드·정규식 규칙**으로 한다. 실행 기록은 `agent_trace.jsonl`에 남는다.

설계 의도는 좋다. 스키마 검증, 400 응답, 트레이스 로그를 처음부터 넣었기 때문이다. 그런데 이름이 오해를 부른다. [MCP 공식 스펙의 Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)는 *"MCP uses JSON-RPC to encode messages"*라고 하고, 표준 전송 방식으로 **stdio와 Streamable HTTP** 두 가지를 정의한다. 반면 이 노트북의 서버는 REST 모양의 HTTP API다. 그래서 Claude Desktop, Cursor 같은 실제 MCP 클라이언트는 붙지 않는다.

매니페스트의 `"modelContextProtocolVersion": "2025-11-01"`도 실존하는 스펙 버전이 아니다. [2025-11-25 변경 이력](https://modelcontextprotocol.io/specification/2025-11-25/changelog)이 바로 앞 개정판으로 2025-06-18을 가리킨다. 그러니 2025-11-01은 정식 개정판이 아니다. [Versioning 페이지](https://modelcontextprotocol.io/specification/versioning)는 이 글을 쓰는 시점의 현행 버전을 2026-07-28로 적고 있다.

> 정리하면 이 서버는 **"MCP가 해결하려는 문제(도구 목록 공개 + 스키마 기반 호출)를 REST로 흉내 낸 교보재"**다. 실습 목적으로는 괜찮다. 다만 이걸 MCP 서버라고 알고 실무로 가져가면 안 된다.

자잘한 버그도 하나 있다. 트레이스 요약에서 `success`는 `ok and 'error' not in obs`로 계산하는데, `errors`는 `0 if ok else 1`로 따로 계산한다. 그래서 `ok=True`인데 관찰값에 `error`가 섞인 경우 `success=False, errors=0`이라는 모순된 요약이 남는다.

## 4. 05 Multi-agent — Blackboard vs Hierarchical, 그런데 정답이 프롬프트에 있다

비밀 금고 퍼즐이다. 단서 3개를 해커, 암호학자, 언어학자 세 에이전트가 하나씩 풀어 `BLUE ROUND SOFT`를 맞춘다. 같은 문제를 두 가지 조직 구조로 돌린다.

- **Shared Memory(Blackboard)**: 리더 없이 세 에이전트가 게시판 전체를 읽고 발견한 것을 덧붙인다. 마지막에 '해결사'가 조합한다. 코드는 `max_turns = 1`이다.
- **Hierarchical**: 매니저가 단서를 하나씩 해당 전문가에게 넘기고 보고를 취합한다.

마지막 셀의 "생각해볼 포인트"는 이렇게 정리한다. Blackboard는 매 턴 전체 컨텍스트를 읽어 토큰이 많이 든다. Hierarchical은 매니저가 병목이다. 창의적 작업에는 Blackboard가, SOP가 있는 업무에는 Hierarchical이 맞다. 교과서적이고 쓸 만한 정리다.

**문제는 퍼즐 쪽이다.** 단서는 *"'VQLZ' (Hint: Caesar Cipher -1)"*이고, 기대하는 답은 ROUND다. 직접 계산해 봤다.

```
VQLZ, shift -1 → UPKY
VQLZ, shift +1 → WRMA
V→R, Q→O, L→U, Z→N 의 이동량 = [4, 2, 17, 12]  (일정하지 않음)
```

**4글자가 5글자(ROUND)가 될 수 없고, 글자마다 이동량도 다르다.** 시저 암호가 성립하지 않는다. 그래서인지 암호학자 프롬프트에 *"'VQLZ'는 … 'ROUND'가 됩니다. V -> R, Q -> O, L -> U, Z -> N = ROUND"*라고 **답이 직접 적혀 있다.** 그러면 이 실험은 "에이전트가 암호를 푸는가"가 아니라 "프롬프트에 적힌 답을 받아 적는가"를 재는 셈이 된다. 두 아키텍처 모두 성공해도 구조의 차이를 말해 주지 않는다.

고치는 방법은 두 가지다. 정상 시저 암호를 쓰거나(ROUND를 shift +1 하면 `SPVOE`), 해독을 도구(파이썬 함수)로 주고 프롬프트에서 답을 빼야 비교가 의미를 가진다.

`Vault.unlock`도 확인할 점이 있다. 이 함수는 `set(code.upper().split())`에 정답 세 단어가 **포함되기만 하면** 통과시킨다. 그래서 단어를 잔뜩 나열한 답도 통과한다. 반대로 매니저가 형식 지시대로 `[BLUE] [ROUND] [SOFT]`처럼 대괄호를 붙여 출력하면 실패할 가능성이 있다. 이건 실행하지 않은 추정이다.

## 5. 06 Framework 비교 — smolagents CodeAgent / LangGraph / ToolCallingAgent

같은 과제("TSLA 주가와 뉴스로 투자 의견")를 세 가지 방식으로 구현한다. 도구 로직(`yfinance`, DuckDuckGo 검색)은 공통으로 쓰고, 래핑만 프레임워크별로 다르다.

- **CodeAgent**: LLM이 파이썬 코드를 짜서 실행한다. 노트북 스스로 "보안 리스크, Sandbox 필수"라고 적는다. [smolagents 공식 문서](https://huggingface.co/docs/smolagents/tutorials/secure_code_execution)도 *"By default, the `CodeAgent` runs LLM-generated code in your environment"*, *"no solution will be 100% safe"*라고 쓴다. 문서가 권하는 것은 원격 샌드박스(E2B, Docker 등)다.
- **LangGraph**: 실제 코드는 `create_react_agent(llm, tools)` 한 줄이다. 주석에는 "노드와 엣지로 흐름을 제어(정교함)", "보일러플레이트가 많다"고 적혀 있다. 하지만 여기서는 prebuilt ReAct 에이전트를 썼기 때문에 그 장단점이 코드에 드러나지 않는다. 노드와 엣지를 직접 그리는 `StateGraph` 버전이 있어야 비교가 공정하다.
- **ToolCallingAgent**: JSON 도구 호출 방식이고, 노트북은 이걸 추천한다.

**함정 — `duckduckgo_search` 패키지명 변경.** [PyPI 페이지](https://pypi.org/project/duckduckgo-search/)에 *"This package (`duckduckgo_search`) has been renamed to `ddgs`! Use `pip install ddgs` instead."*라는 공지가 붙어 있다. 06과 08 모두 옛 이름으로 import한다. 지금 새로 설치하면 경고가 뜨거나 동작이 달라질 수 있으니 버전을 고정하거나 `ddgs`로 옮기는 게 안전하다.

## 6. 07 Guardrail — 입력 2단 + 출력 1단

- **입력**: 1차로 키워드 블랙리스트(`"ignore previous instructions"`, `"system prompt"`, `"관리자 모드"`)를 보고, 2차로 OpenAI Moderation API를 본다.
- **벤치마크**: [lmsys/toxic-chat](https://huggingface.co/datasets/lmsys/toxic-chat)(`toxicchat0124`, 논문 [arXiv:2310.17389](https://arxiv.org/abs/2310.17389))에서 `train[:10]`을 흘려 본다. 주석에는 "5개만 샘플링"이라고 돼 있지만 실제로는 10개다.
- **출력**: 전화번호·주민번호 정규식으로 마스킹하고, 금융 컴플라이언스 금지어("무조건 수익", "원금 보장", "100%")를 표시한다.

구조는 교과서적이다. 그래도 실무로 옮길 때 세 가지는 짚어 둔다.

1. **10건으로는 가드레일 성능을 말할 수 없다.** toxic-chat에는 `toxicity`, `jailbreaking` 라벨이 있다. 노트북은 라벨을 출력만 하고 차단 결과와 비교하지 않는다. 그래서 오탐률과 미탐률이 계산되지 않는다. 라벨과 비교해 혼동행렬을 만드는 셀 하나만 추가해도 "테스트"가 "측정"이 된다.
2. **영어 문구 블랙리스트는 우회가 쉽다.** 대소문자는 `.lower()`로 처리하지만, 띄어쓰기를 바꾸거나 다른 언어로 쓰거나 동의어로 바꾸면 그대로 통과한다. 1차 필터는 "싸고 빠른 거름망"으로만 봐야 한다.
3. **출력 금지어 `"100%"`는 오탐이 많다.** "전년 대비 100% 증가"처럼 사실을 서술하는 문장에도 경고가 붙는다. 금지어는 문맥이 있는 구(句) 단위로 정하는 게 낫다.

## 7. 08 Quant-X — 부품은 다 있는데 배선이 덜 됐다

마지막 노트북은 `%%writefile`로 `QuantX_Project/` 패키지를 만든다. 들어가는 부품은 다음과 같다.

- `core/logger.py`: 감사로그. 파일과 콘솔에 남기고, 스레드 락과 메모리 버퍼 100개를 둔다.
- `core/rag_engine.py`: 싱글턴 FAISS. 더미 문장 3개와 `text-embedding-ada-002`를 쓴다.
- `agents/tools.py`: 사내검색·웹검색·주가·시장요약·리포트저장 도구. 미들웨어 데코레이터를 씌운다.
- `core/guardrails.py`: 입력 블랙리스트와 출력 대체어.
- `core/auth.py`: junior/senior 2단계 RBAC.
- `agents/core.py`: Manager → Research / MarketAnalyst. 둘 다 smolagents `CodeAgent`다.

목차만 보면 "엔터프라이즈급"이다. 그런데 통합 시나리오(`QuantXMultiAgent.process_request`)를 따라가 보면 이렇다.

- **가드레일이 호출되지 않는다.** `security_guardrails.check_input`과 `filter_output`은 별도 테스트 셀에서만 불린다. 매니저 경로에는 연결돼 있지 않다.
- **RBAC가 걸린 `save_report`는 어떤 에이전트의 도구 목록에도 없다.** Research는 `[search_internal, search_web]`, Analyst는 `[get_stock_price, get_market_summary]`만 갖는다. 그래서 "senior만 저장 가능"이라는 규칙이 시나리오 안에서 한 번도 실행되지 않는다.
- **역할 판정이 user_id 문자열이다.** `role = "senior" if "senior" in user_id else "junior"`. 아이디에 senior만 넣으면 권한이 올라간다. 교육용 스텁이라는 건 분명하지만, 이 줄을 그대로 복사하면 사고가 난다.
- **매니저는 LLM이 아니다.** 종합 단계는 두 결과를 f-string으로 이어 붙인다. 강의 페이지가 Project 2로 소개하는 "크로스체크 및 사실 검증 Judge Agent"와 "인용·각주 자동화"는 이 파일에 없다. 영상에서 다룬 것인지는 확인하지 못했다.
- **협업 로그가 모듈 전역 dict(`AGENT_SESSION_STATE`)다.** 사용자와 세션 구분 없이 쌓인다. 금융 감사로그라면 사용자별로 분리하고 변조를 막는 것이 핵심이다.
- **`CodeAgent` + `add_base_tools=True`를 샌드박스 없이 쓴다.** 06에서 "Sandbox 필수"라고 해 놓고 08의 금융 시스템은 로컬 실행 기본값을 그대로 쓴다.

여기서는 smolagents의 docstring 규칙을 직접 확인했다. 08의 도구 중 `search_web`, `get_stock_price`의 docstring에는 `Args:` 섹션이 없다. smolagents 1.26.0에서 같은 모양(`@tool` + `@wraps` 미들웨어 + Args 없는 docstring)의 함수를 정의해 보면 **데코레이터 단계에서 바로 예외가 난다.**

```
DocstringParsingException: Cannot generate JSON schema for search_web
because the docstring has no description for the argument 'query'
```

`Args:`가 있는 `search_internal`은 통과한다. 다만 *"Function 'search_internal' has decorators other than @tool. This may cause issues with serialization in the remote executor"* 경고가 뜬다. 즉 **현 smolagents 기준으로는 `agents/tools.py`를 import하는 순간 통합 테스트가 시작도 못 하고 멈춘다.** 강의 당시 버전에서는 동작했을 수 있다. 노트북이 smolagents 버전을 고정하지 않은 게 근본 원인이다.

## 8. 그래서 이 리포를 어떻게 쓰면 좋은가

| 노트북 | 추천도 | 이유 |
|---|---|---|
| 03 RAG | ★★★ | 하이브리드·리랭크·압축·평가 지표를 한 파일에서 직접 계산한다. `bm.ptp()`만 고치면 된다 |
| 04 Agent | ★★☆ | 스키마 검증과 트레이스 설계는 좋다. "MCP"라는 이름은 지우고 읽을 것 |
| 05 Multi-agent | ★☆☆ | 조직 구조 비교라는 질문은 좋은데, 퍼즐이 깨져 있어 실험이 성립하지 않는다 |
| 06 Framework | ★★☆ | 같은 과제를 세 방식으로 구현했다. LangGraph 쪽은 prebuilt라 비교가 한쪽으로 기운다 |
| 07 Guardrail | ★★☆ | 구조는 표준이다. 라벨과 비교하는 셀을 추가해야 측정이 된다 |
| 08 Quant-X | ★★☆ | 모듈 경계 설계를 보기 좋다. 가드레일·RBAC를 직접 배선하는 연습 문제로 쓰면 가장 좋다 |

이 리포의 가치는 "완성된 금융 에이전트"보다 **도메인 에이전트에 어떤 부품이 필요한지 보여 주는 지도**에 있다. 그 지도를 실제 시스템으로 바꾸려면 다음이 필요하다.

1. 의존성 버전을 고정한다(smolagents, numpy, duckduckgo-search, langchain).
2. 가드레일과 RBAC를 매니저 실행 경로 안에 넣는다.
3. 진짜 MCP(JSON-RPC, stdio/Streamable HTTP)로 바꾼다.
4. CodeAgent를 샌드박스 안에서 실행한다.
5. 평가셋 라벨과 비교해 혼동행렬을 낸다.

이 다섯 가지가 "실습"과 "운영"의 차이다.

---

## References

1. h-albert-lee, *fastcampus-domain-agent-practices* (GitHub, 커밋 `8311f4f`, 2025-12-26). <https://github.com/h-albert-lee/fastcampus-domain-agent-practices>
2. 패스트캠퍼스, 「도메인 AI Agent의 모든 것: 보안 특화 모델 설계부터 금융 멀티 에이전트 구축까지」 강의 상세 페이지. <https://fastcampus.co.kr/data_online_financedomain>
3. nmixx-fin, *NMIXX-BGE-M3* 모델 카드 (Hugging Face). <https://huggingface.co/nmixx-fin/nmixx-bge-m3>
4. Yao, S. et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, arXiv:2210.03629. <https://arxiv.org/abs/2210.03629>
5. Jiang, H. et al., *LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models*, arXiv:2310.05736 (저자 측 실험 수치). <https://arxiv.org/abs/2310.05736>
6. Model Context Protocol, *Specification 2025-06-18 — Transports*. <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports>
7. Model Context Protocol, *Specification 2025-11-25 — Key Changes*. <https://modelcontextprotocol.io/specification/2025-11-25/changelog>
8. Model Context Protocol, *Versioning*. <https://modelcontextprotocol.io/specification/versioning>
9. Hugging Face, *smolagents — Secure code execution*. <https://huggingface.co/docs/smolagents/tutorials/secure_code_execution>
10. lmsys, *toxic-chat* 데이터셋 카드 (Hugging Face) / Lin, Z. et al., arXiv:2310.17389. <https://huggingface.co/datasets/lmsys/toxic-chat>
11. PyPI, *duckduckgo-search* — `ddgs`로 이름 변경 공지. <https://pypi.org/project/duckduckgo-search/>
