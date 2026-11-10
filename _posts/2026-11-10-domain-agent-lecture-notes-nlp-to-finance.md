---
layout: post
title: "도메인 AI Agent 강의 4부작 정리 — 임베딩에서 금융 에이전트 가드레일까지"
date: 2026-11-10 22:14:35 +0900
categories: [ai, llm]
tags: [nlp, embedding, transformer, llm, rag, agent, mcp, a2a, guardrail, finance]
---

패스트캠퍼스 「도메인 AI Agent의 모든 것」 강의 자료 네 권(이한울 강사)을 읽고 정리한 노트다. 순서는 **① 자연어처리 입문 → ② 거대언어모델과 RAG → ③ Agent의 이해 → ④ 금융 Agent 실전** 이다.

원본 슬라이드는 강의 수강생에게 배포된 자료라 여기 첨부하지 않는다. 슬라이드를 옮겨 적지 않고 내용을 내 말로 줄였다. 강의가 인용한 논문은 가능하면 **원 논문 링크로 직접** 걸었다. 강의에서만 나온 주장은 "강의 주장"이라고 따로 표시했다.

한 줄 요약: **"엔지니어링에 정답은 없다. 목적에 맞는 설계만 있다."** 네 권 모두 이 말로 돌아온다. 벡터 검색·멀티에이전트·프레임워크도 이 원칙에 맞춰 골라 쓰라는 것이다.

---

## ① 자연어처리 입문 — "의미를 연산 가능하게"

### 토큰화와 희소 표현의 한계

UTF-8 바이트열은 문장을 *표현* 할 뿐이고, 의미는 담지 않는다. 그래서 자주 쓰이는 조각(token)에 ID를 붙이는 **토큰화** 부터 시작한다. 그런데 토큰 ID를 원-핫 벡터로 만들면 어휘 크기만큼 길어진다. 값은 거의 다 0인 **희소(sparse)** 벡터가 되고, 두 단어가 얼마나 비슷한지도 계산할 수 없다.

### 임베딩 = 의미를 담은 저차원 공간

강의는 **매니폴드 가설**(고차원 데이터는 그보다 낮은 차원의 다양체 위에 놓인다)로 임베딩을 설명한다. 희소한 고차원 토큰을 의미가 반영된 저차원 밀집 벡터로 옮기면 의미를 계산할 수 있다. 가까움은 두 가지로 잰다.

| 척도 | 묻는 것 | 강의 예시 |
| --- | --- | --- |
| 유클리드 거리 | 얼마나 떨어져 있나 | 은행–사과는 멀다 |
| 코사인 유사도 | 같은 방향을 보나 | 은행–증권은 방향이 비슷하다 |

`일본 − 도쿄 + 서울 ≈ 한국` 같은 벡터 연산이 대표 예시다. 문장 임베딩은 수백~수천 차원이라 사람이 보려면 t-SNE·UMAP으로 2~3차원에 투영한다. 다만 투영 과정에서 정보가 많이 빠지므로 **시각화용이지 연산용은 아니다.**

### Word2Vec · FastText · GloVe

- **Word2Vec** ([Mikolov et al., 2013](https://arxiv.org/abs/1301.3781)): **분포 가설**("비슷한 문맥에 나오는 단어는 뜻도 비슷하다")에 기반한다. 주변 단어로 가운데 단어를 맞히는 **CBOW** 와, 가운데 단어로 주변 단어를 맞히는 **Skip-gram** 두 방식이 있다.
- **FastText** ([Bojanowski et al., 2016](https://arxiv.org/abs/1607.04606)): 단어를 문자 n-gram으로 쪼개 학습한다. 학습 때 못 본 단어(OOV)나 희귀어도 조각 벡터를 합쳐 임베딩을 만들 수 있다. 강의 예시는 `<공기놀이>` 를 3-gram으로 나눈 `<공기`·`공기놀`·`기놀이`·`놀이>` 였다.
- **GloVe** ([Pennington et al., 2014](https://nlp.stanford.edu/pubs/glove.pdf)): 앞의 둘은 국소 문맥으로 예측하는 방식이다. GloVe는 코퍼스 전체의 **동시출현 통계** 로 학습한다. 논문의 ice/steam 예시처럼 `P(solid|ice) ≫ P(solid|steam)` 같은 확률 *비율* 에 의미가 담긴다.

**금융 데이터 실무 팁(강의 주장):** 정적 임베딩은 여러 출처가 섞이면 금융 용어의 뜻이 왜곡되기 쉽다. 그래서 숫자는 `<AMOUNT>`·`<PERCENT>`·`<DATE>` 같은 특수 토큰으로 바꿔 두고 학습한다. "ESG 투자"처럼 코퍼스에서 드문 신조어에는 FastText가 상대적으로 낫다.

### 트랜스포머 → BERT vs GPT

언어모델은 단어 시퀀스에 확률을 매기는 모델이다("밥을 먹었다"는 그럴듯하고 "밥을 인사했다"는 그렇지 않다). RNN·LSTM·ELMo를 거쳐 지금의 표준은 [Transformer(Vaswani et al., 2017)](https://arxiv.org/abs/1706.03762) 다. 핵심은 **어텐션** 이다. 강의는 Q·K·V를 오픈북 시험에 비유했다. Query는 풀 문제, Key는 책의 목차, Value는 해당 목차의 본문이다.

- **인코더** 는 입력 전체를 양방향으로 본다. **디코더** 는 *Masked* 어텐션으로 미래 토큰을 가린다. 생성할 때는 아직 쓰지 않은 미래를 볼 수 없기 때문이다.
- **BERT** ([Devlin et al., 2018](https://arxiv.org/abs/1810.04805)) 는 인코더만 쌓은 모델이다. 입력 토큰의 15%를 가리고 맞히는 MLM으로 사전학습한 뒤 분류·QA 등으로 파인튜닝한다.
- **GPT** 는 디코더만 쌓은 모델이다. 다음 토큰 예측(NTP)으로 학습하고 생성에 강하다.

강의의 한 줄 정리: 예전에 **파인튜닝으로 하던 일(분류·번역·요약·QA)을 지금은 프롬프트로 한다.**

---

## ② 거대언어모델과 RAG

### 스케일링과 "창발 능력"

- **스케일링 법칙**: [Kaplan et al., 2020](https://arxiv.org/abs/2001.08361) 이 모델·데이터·연산량과 손실 사이의 멱법칙을 보였다. 이후 [Chinchilla(Hoffmann et al., 2022)](https://arxiv.org/abs/2203.15556) 는 같은 연산량이라면 *더 작은 모델에 더 많은 데이터* 를 쓰는 편이 낫다고 수정했다.
- **창발 능력**([Wei et al., 2022](https://arxiv.org/abs/2206.07682)): 규모가 어느 선을 넘으면 지시 따르기·단계별 추론·인컨텍스트 학습이 갑자기 나타난다는 관찰이다.
- 반론도 같이 짚는다. [Schaeffer et al., 2023](https://arxiv.org/abs/2304.15004) 은 "갑자기"처럼 보이는 것이 **불연속적인 평가지표가 만든 착시** 일 수 있다고 주장한다. 강의는 손실 임계설·데이터 노출설·암묵적 베이지안 추론설도 함께 소개한다. 결론은 **원인이 아직 정리되지 않았다** 는 것이다.
- **역스케일링**([McKenzie et al., 2023](https://arxiv.org/abs/2306.09479)): 모델이 커질수록 오히려 못하는 과제도 있다. 학습된 상식이 새 정보를 이기는 경우, 사람의 오류를 그대로 흉내 내는 경우, few-shot 예시의 겉모양을 규칙으로 착각하는 경우 등이다.

### "성능"은 하나가 아니다

에이전트에 넣을 LLM은 **품질 · 비용 · 지연 · 처리량** 을 함께 본다. 이 넷은 서로 맞바꾸는 관계다. 강의는 축별 처방을 이렇게 묶었다.

| 맞바꾸는 축 | 처방 예 |
| --- | --- |
| 품질 vs 지연 | Distillation, LoRA, 양자화, 프롬프트·응답 캐시 |
| 비용 vs 처리량 | 배치 추론, KV 캐시 재사용, 적응형 라우팅 |
| 품질 vs 비용 | MoE, Speculative decoding, RAG |

품질 안에서도 **Hallucination**(사실이 아닌 내용 생성), **Faithfulness**(주어진 근거에 충실한가), **Calibration**(모델의 확신이 실제 정답률과 맞는가)을 따로 봐야 한다. 테크니컬 리포트의 벤치마크 점수는 *특정 언어·도메인* 에서 그대로 재현되지 않을 수 있다. 그래서 **우리 문제에 필요한 능력을 정의하고, 직접 평가셋을 만드는 것** 이 출발점이다.

### RAG — 오픈북으로 바꾸기

RAG의 원형([Lewis et al., 2020](https://arxiv.org/abs/2005.11401))은 확률적 혼합으로 쓸 수 있다.

```text
P(y|x) = Σ_z P(y|x,z) · P(z|x)
         └ Reader ┘   └ Retriever ┘
```

**Naive RAG** 의 품질은 대개 검색에서 갈린다.

- **청킹**: 의미 단위(문단·섹션·함수)로 자른다. 각 청크에 상위 헤더를 붙이고 10~20% 겹치게 둔다(강의 경험칙). 너무 길게 자르면 어텐션이 분산된다.
- **벡터 검색의 한계**: [Weller et al.(Google DeepMind)](https://arxiv.org/abs/2508.21038) 은 임베딩 차원 수가 그 임베딩으로 표현할 수 있는 top-k 조합에 이론적 상한을 건다는 것을 보였다. 그래서 키워드 정밀 검색인 **BM25** 와 섞는 **하이브리드 검색**(`λ·BM25 + (1−λ)·cosine` 등)을 쓴다.
- 강의는 **벡터 검색이 아예 필요 없는 애플리케이션도 많다** 고 강조했다.

**Advanced RAG** 는 여기에 단계를 더한다.

1. **Rerank**: 검색은 빠른 Bi-Encoder로, 재정렬은 쿼리와 문서를 함께 읽는 Cross-Encoder로 한다.
2. **쿼리 변환**: "삼성전자와 하이닉스 가격 상승 요인 비교" 같은 질의는 기업별 질의로 *분해* 해 따로 검색한 뒤 *재조합* 한다. 한 번의 검색으로 처리하면 비교 문서가 없을 때 노이즈만 돌아온다.
3. **컨텍스트 압축·쿼리 라우팅**: LLMLingua 같은 압축 기법을 쓰고, 도메인별 인덱스로 질의를 보낸다.
4. **애초에 RAG가 필요한가?** 컨텍스트 창이 길어지고 KV 캐시 재사용이 쉬워졌다. 그래서 데이터가 자주 바뀌지 않고 양도 크지 않으면 전부 넣고 캐시하는 쪽이 나을 수 있다([Li et al., 2024 — Long Context vs. RAG](https://arxiv.org/abs/2501.01880)).

평가는 구성요소별(검색·생성)과 E2E 두 갈래로 한다. 대표 도구는 [RAGAS](https://docs.ragas.io/en/latest/) 다. context precision·recall, faithfulness, answer relevancy 등을 잰다.

---

## ③ Agent의 이해

### 정의보다 계보

강의는 Agent를 정의 하나로 고정하지 않는다. 대신 **무엇을 풀려고 나온 기술인지** 를 세 논문으로 따라간다.

| 논문 | 더한 것 |
| --- | --- |
| [ReAct (Yao et al., 2022)](https://arxiv.org/abs/2210.03629) | Thought → Act → Observation 루프. 추론과 행동을 번갈아 하며 환각을 줄인다 |
| [Toolformer (Schick et al., 2023)](https://arxiv.org/abs/2302.04761) | 언제·어떤 입력으로·어떤 도구를 부를지 자기지도 방식으로 학습 |
| [Reflexion (Shinn et al., 2023)](https://arxiv.org/abs/2303.11366) | 실패를 말로 요약해 메모리에 두고, 다음 시도에서 반성하며 전략을 고침 |

이 셋이 합쳐져 지금 Agent의 뼈대인 **reasoning + acting + tool use + memory** 가 됐다. "Workflow냐 자율 Agent냐"도 대립 구도가 아니라 상황에 따라 고르는 문제라고 본다.

### 상태·메모리·계획

- **단기 상태 = 컨텍스트 창** 이다. 시퀀스가 길어지면 정보가 빠진다. 장기 기억은 에피소드 메모리(과거 요약)와 의미 메모리(지식·도구 사용 패턴)로 나눠 따로 저장한다.
- 컨텍스트 관리 패턴은 세 가지다. 오래된 내용은 **요약**, 필요한 것만 **검색해 삽입**, 최근·중요 정보 **우선/감쇠**.
- **Planner–Executor 분리**: Planner가 하위 작업을 만든다. Executor는 그 작업을 실행하고 관찰 결과를 보고한다. Planner는 보고를 보고 계획을 고친다.
- 중간 추론이 틀리면 오류가 누적된다. 그래서 다섯 가지 안전장치를 둔다. 추론 흔적 기록, 행동 전후 검증, 도구 샌드박스, 자기비판, 고위험 단계의 **Human-in-the-loop**.

### MCP와 A2A

- **[MCP](https://modelcontextprotocol.io/docs/getting-started/intro)**: LLM 앱과 도구·리소스·프롬프트를 잇는 표준 프로토콜이다(흔히 "LLM의 USB-C"라고 한다). 도구마다 커넥터를 따로 만드는 N×M 문제를 하나의 인터페이스로 줄인다. 툴 입출력은 JSON Schema로 명확히 정의한다. 권한은 **최소권한** 으로 설계한다. 스코프는 `도메인×행위` 조합(`repo:read`)으로 정하고, 위험도 메타데이터를 붙이고, 리소스 URI에 테넌트 경계를 넣는다.
- **[A2A](https://a2a-protocol.org/latest/topics/what-is-a2a/)**: MCP가 *도구 접근* 이라면 A2A는 *에이전트 간 협업* 이다. 에이전트는 Agent Card(JSON)로 자기 능력을 알리고, 일은 수명주기가 있는 태스크 단위로 넘기며, 결과물은 Artifact로 주고받는다.
- 둘 다 기존 API처럼 미리 정한 메트릭만으로는 안전을 보장하기 어렵다. 그래서 Langfuse 같은 LLM 입출력 추적에 OpenTelemetry 기반 metrics·logs·traces를 더하고, **감사추적을 설계 단계부터** 넣으라고 한다.

### 멀티에이전트

- 조직 구조는 고전 분류(Weiss 편, *Multiagent Systems*, 1999) 네 가지를 쓴다. **중앙형**(결정은 빠르지만 Planner가 병목), **계층형**(관리는 쉽지만 유연성이 낮음), **분산형**(자율적이지만 조정이 어려움), **시장형**(효율적이지만 메커니즘이 복잡). 실제로는 섞어 쓴다.
- 통신은 1:1 Message, Pub/Sub Topic, 공용 Blackboard 세 방식이다.
- 작업은 **DAG(Task Graph)** 로 쪼갠다. 실패한 노드만 다시 돌리면 복구 비용이 작다.
- 결과 고르기는 Voting·Tournament·Judge로 한다. 품질을 올리려면 Debate나 Self-Consistency를 쓴다.
- 여러 에이전트가 동시에 돌면 **경쟁 조건** 이 생긴다. Lock·Queue·우선순위로 막는다. 실패하면 Retry·Backoff·Checkpoint로 복구한다.

### 프레임워크 고르기

에이전트 프레임워크는 **Agent · Tool · Memory · Planner · Orchestrator** 다섯 요소를 얼마나 두껍게 추상화했는지가 다를 뿐이다. 강의의 구분은 이렇다.

| 프레임워크 | 성격 | 강의가 꼽은 용도 |
| --- | --- | --- |
| smolagents | 최소 추상화. CodeAgent와 ToolCallingAgent 두 방식 | 에이전트 루프 학습, 최대 제어권 |
| LangChain/LangGraph | 풍부한 RAG 구성요소 | RAG 파이프라인 (smolagents 툴로 감싸 함께 쓰는 패턴) |
| AutoGen | 이벤트·액터 런타임 | 연구·프로토타입 |
| CrewAI | 역할·크루 중심 | 업무 자동화 |
| Semantic Kernel | 플러그인·엔터프라이즈 통합 | .NET/Azure 기반 기업 시스템 |

강의의 기준은 이렇다. 비용은 프레임워크보다 **호출 패턴·컨텍스트 길이·재시도 전략·모델 선택** 에서 갈린다. 금융·공공처럼 감사 로그와 접근 제어가 필수인 곳에서는 그걸 받쳐 주는 스택을 고른다.

---

## ④ 금융 Agent 실전

### 데이터 지형부터

강의는 금융기관 데이터를 넷으로 나눈다. **고객·계좌·거래**(원장, 보안 최상위), **시장·시세**(거래소 실시간 피드), **뉴스·리포트**(비정형 데이터), **규제·정책**(감독규정·내부 컴플라이언스)이다. 에이전트 설계는 *어떤 데이터가 어디에 있고, 누가 관리하며, 어떤 권한이 필요한지* 확인하는 데서 시작한다.

- 실제 RAG·Agent에 가장 많이 쓰이는 층은 **리서치 리포트·공시·뉴스** 다(강의 주장).
- 원장 데이터는 신용정보법·전자금융거래법의 보호 대상이다. 강의는 가명처리 없이 LLM 학습이나 외부 로그로 보내는 것은 사실상 불가능하다고 설명한다.
- 규제 문서는 "장-절-조-항-목" 계층이다. 그래서 조항별 ID를 붙여 인덱싱하고, 답변에 **근거 조항을 추적** 할 수 있게 한다.

### Agent는 "내부자"다

강의의 핵심 문장이다. Agent를 사람 사용자와 똑같이 **ID · Role · Permission** 을 가진 주체로 다룬다.

- **업무분리**: 조회 Agent(읽기·분석·리포트)와 실행 Agent(주문·이체)를 나눈다.
- **세션 스코프 토큰**: OAuth처럼 `ACCOUNT_READ` 같은 스코프를 세션에 실어 보낸다. RAG·DB 계층에서 매번 스코프를 검사한다. 세션이 끝나면 토큰도 만료된다.
- **망 구조 반영**: Core(원장·체결)는 미리 정의된 간접 API로만 접근한다. Middle(리포트·데이터마트)이 주된 읽기 영역이다. DMZ는 외부 접점이다.
- **오픈뱅킹**: Agent가 직접 호출하지 않는다. 고객 동의는 고객 본인만 할 수 있고, API 키와 인증서는 백엔드에만 둔다.
- **자동화 등급**: 조회·요약·리포트는 자동으로 처리한다. 이체·주문 같은 고위험 작업은 반드시 사람이 승인한다.

### 금융 텍스트 전처리

숫자·단위·약어가 뒤섞인 것이 금융 텍스트의 기본 성질이다. 단위를 하나의 규칙으로 통일한다.

| 원문 | 정규화 |
| --- | --- |
| 2조 5,300억 원 | 2.53e12 (KRW) |
| 35bp 상승 | +0.35%p |
| '25년 2분기 | 2025-Q2 |
| PER 14배 | PER 14.0x |

표는 행 단위 레코드(종목·지표·값·단위·시점)로 바꾼다. 설명 텍스트는 벡터 저장소에, 숫자는 수치 DB에 따로 넣고 질의할 때 합친다. NIM·QoQ·YoY 같은 약어 사전과 티커↔종목명 매핑도 따로 관리한다.

### 보안과 가드레일

위협은 넷이다. **프롬프트 인젝션**, **데이터 추출·유출**, **무권한 도구 호출**, **공급망·모델 변조**. 이 중 프롬프트 인젝션은 [OWASP LLM Top 10 2025의 1번(LLM01)](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) 이다. OWASP는 사람 눈에 보이지 않는 입력이라도 모델이 파싱하기만 하면 공격이 성립한다고 설명한다. 문서 속에 숨긴 "이전 지시를 무시하고 이체하라" 같은 **간접 인젝션** 이 RAG에서 특히 위험한 이유다.

강의가 제시한 방어선은 이렇다.

1. **입력 필터**: PII, 내부 등급·상품코드, 우회 명령 패턴, 숨김 HTML/JS를 걸러낸다.
2. **출력 필터**: 민감정보가 다시 노출되는지, 투자 권유 규제 위반("반드시 수익이 납니다")은 없는지, 시장조작으로 읽힐 표현은 없는지 검사한다. 위반이면 차단·마스킹·완화 재작성한다.
3. **정책 3계층**: 법무·준법의 자연어 정책 → Policy DSL/룰 엔진 → 모델에 넣는 프롬프트 정책 요약.
4. **컨텍스트 격리**: 사용자 세션, Agent 인스턴스, 툴 호출, 검색 결과를 각각 분리한다. 검색 문서는 **"Untrusted"** 로 표시하고 시스템 정책과 다른 영역에 둔다.
5. **Tool Gateway**: 모든 외부 호출을 한 곳으로 모은다. 여기서 인증·스코프 확인, Rate limit, 금액 한도, 로깅을 처리한다. 고위험 도구는 **정책 DSL 검사 → 금액 한도 → 사람 승인** 세 단계를 거치게 해 Agent 혼자 실행하지 못하게 한다.
6. **레드팀**: 콘텐츠 수준(유해 출력)과 행동 수준(인젝션·도구 오용·RAG 메모리 오염·멀티에이전트 메시지 변조)을 모두 시험한다.
7. **모니터링·차단**: 프롬프트·검색 쿼리·툴 호출·의사결정 흔적·안전 점수·재시도까지 남긴다. 알람 예시는 이렇다. 하루 툴 호출이 비정상적으로 많을 때, 같은 툴을 반복 호출해 인젝션 루프가 의심될 때, **승인 없이 고위험 툴을 시도할 때(CRITICAL)**.

강의 표현으로는 "LLM은 블랙박스일 수 있어도 **Agent는 블랙박스가 아니다**". 게이트웨이에서 남길 수 있는 것은 전부 남기라는 뜻이다.

---

## 읽고 나서 — 네 권을 관통하는 것

1. **임베딩 → RAG → Agent → 금융은 한 줄로 이어진다.** 의미를 벡터로 만들 수 있어야 검색할 수 있다. 검색이 돼야 근거를 줄 수 있다. 근거가 있어야 도구를 맡길 수 있다. 도구를 맡기려면 권한과 감사가 있어야 한다.
2. **반론을 같이 가르친다.** 창발 능력에는 지표 착시설을, 벡터 검색에는 이론적 한계와 "필요 없을 수도"를, RAG에는 롱컨텍스트를 붙였다. 유행어를 그대로 믿지 말라는 태도가 일관된다.
3. **금융편의 실체는 모델이 아니라 경계 설계다.** 스코프 토큰, 망 구분, 게이트웨이, 사람 승인. 모델을 바꿔도 남는 것은 이쪽이다.

## 이 정리의 한계

- 강의는 실습(Colab/Jupyter, 미니 에이전트, 금융 Deep Research 멀티에이전트)이 핵심인데 **실습 코드는 다루지 않았다.** 슬라이드 텍스트만 읽었다.
- 슬라이드 속 그림·도표 상당수는 텍스트로 추출되지 않아 반영하지 못했다.
- "강의 주장"으로 표시한 실무 팁(청크 overlap 10~20%, 금융 RAG에 가장 많이 쓰이는 데이터 층 등)은 **독립적으로 검증하지 않았다.**
- 프레임워크 비교표는 강의 시점 기준이다. 각 프레임워크는 빠르게 바뀌므로 도입 전에 공식 문서를 다시 확인해야 한다.

## References

- 원 강의: 패스트캠퍼스, 「도메인 AI Agent의 모든 것」 Part 1~4 강의 자료, 이한울 (수강생 배포 자료 — 본문은 요약이며 원본은 첨부하지 않음)
- Mikolov et al., [Efficient Estimation of Word Representations in Vector Space](https://arxiv.org/abs/1301.3781), 2013
- Bojanowski et al., [Enriching Word Vectors with Subword Information](https://arxiv.org/abs/1607.04606), 2016
- Pennington, Socher, Manning, [GloVe: Global Vectors for Word Representation](https://nlp.stanford.edu/pubs/glove.pdf), EMNLP 2014
- Vaswani et al., [Attention Is All You Need](https://arxiv.org/abs/1706.03762), 2017
- Devlin et al., [BERT](https://arxiv.org/abs/1810.04805), 2018
- Kaplan et al., [Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361), 2020
- Hoffmann et al., [Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556), 2022
- Wei et al., [Emergent Abilities of Large Language Models](https://arxiv.org/abs/2206.07682), 2022
- Schaeffer, Miranda, Koyejo, [Are Emergent Abilities of Large Language Models a Mirage?](https://arxiv.org/abs/2304.15004), NeurIPS 2023
- McKenzie et al., [Inverse Scaling: When Bigger Isn't Better](https://arxiv.org/abs/2306.09479), 2023
- Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401), 2020
- Weller et al., [On the Theoretical Limitations of Embedding-Based Retrieval](https://arxiv.org/abs/2508.21038), 2025
- Li et al., [Long Context vs. RAG for LLMs: An Evaluation and Revisits](https://arxiv.org/abs/2501.01880), 2024
- RAGAS, [공식 문서](https://docs.ragas.io/en/latest/)
- Yao et al., [ReAct](https://arxiv.org/abs/2210.03629), 2022 · Schick et al., [Toolformer](https://arxiv.org/abs/2302.04761), 2023 · Shinn et al., [Reflexion](https://arxiv.org/abs/2303.11366), 2023
- [Model Context Protocol — Introduction](https://modelcontextprotocol.io/docs/getting-started/intro)
- [A2A Protocol — What is A2A](https://a2a-protocol.org/latest/topics/what-is-a2a/)
- OWASP Gen AI Security Project, [LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
