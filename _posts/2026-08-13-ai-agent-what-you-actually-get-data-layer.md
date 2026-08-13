---
layout: post
title: "AI 에이전트에서 얻을 수 있는 것은 모델 바깥에 있다 — 세션 7개에 모델 이야기가 한 줄도 없는 세미나 프로그램"
date: 2026-08-13 18:30:00 +0900
categories: [ai, agent, data]
tags: [ai-agent, ai-ready-data, ontology, knowledge-graph, graphrag, context-engineering, rag, nist, iso-5259]
---

![AI Ready Data 2026 세미나 프로그램 — 2026년 9월 3일, 포스코타워 역삼, 중앙대학교 HIKE 연구실 주최](/assets/images/ai-ready-data-2026-seminar.jpg)

> 세미나 포스터 한 장을 받았다. AI 에이전트 이야기를 하는 자리인데, **세션 7개 중 모델을 다루는 세션이 하나도 없다.**
> 전부 데이터·온톨로지·그래프·표준이다.
> 이게 "AI 에이전트에서 실제로 무엇을 얻을 수 있는가"에 대한 가장 정직한 대답 같아서, 프로그램을 근거로 그 질문을 다시 정리했다. 그리고 내 에이전트 스택을 실제로 열어서 어디가 비어 있는지 쟀다.

## 0. 이 글의 근거와 한계 (먼저 밝힌다)

- **포스터는 1차 자료지만, 어젠다에 대해서만 그렇다.** 행사는 2026년 9월 3일이고 이 글은 8월 13일에 쓴다. 아직 아무도 발표하지 않았다. **연사들이 무슨 말을 할지 나는 모르고, 추측해서 쓰지 않는다.** 인용하는 건 세션 제목과 소속까지다.
- 개념 설명은 전부 **1차·공식 출처**(NIST 간행물, NSF 공모, Anthropic 엔지니어링 블로그, Microsoft Research)로만 달았다. 벤더 자체 벤치마크는 그렇다고 라벨을 붙였다.
- **§5의 수치는 내 홈랩 1대에서 오늘 직접 측정한 값**이다. 단일 환경 1회 관측이므로 일반화하지 않는다.
- 행사 정보: 2026.9.3(목) 13:00~17:45 · 포스코타워 역삼 이벤트홀 3층 · 주최·주관 중앙대학교 HIKE 연구실 · [사전등록 페이지](https://onoffmix.com/event/347396). 포스터 이미지의 저작권은 주최 측에 있고, 여기서는 행사 안내 목적으로 인용한다. 나는 이 행사와 아무 이해관계가 없다.

---

## 1. 프로그램에 없는 것

세션을 주제별로 분류하면 이렇게 된다.

| 세션 | 연사·소속 | 무엇에 대한 이야기인가 |
|---|---|---|
| AI 에이전트 시대의 공공 AX 그리고 데이터 전략 | 이승현 (라이너, AI 에반젤리스트) | 데이터 전략 |
| 현장에서 본 AI Ready 데이터의 조건 | 구름 (빅밸류 대표) | 데이터 품질 |
| 데이터로 시작하는 AI-Ready Data | 허홍수 (GS건설 데이터기획파트장) | 데이터 준비 |
| 온톨로지가 기업의 손익에 미치는 영향 | 이승현 (인핸스 대표) | 온톨로지 |
| AI Agent 시대, Graph는 어떻게 Context가 되는가 | 박나연 (공원나연 대표) | 지식그래프 |
| AI Ready Data: 데이터를 AI 활용 가능 상태로 만드는 표준 체계 | 김정원 (국립군산대 교수) | 표준 |
| 공공데이터로 검증하는 AI Ready Data 진단과 구축 | 이정윤 (중앙대 HIKE 연구실) | 검증·진단 |

**모델 아키텍처 0건. 파인튜닝 0건. 프롬프트 0건. 벤치마크 0건.**

제목에 "AI Agent"가 박힌 세션조차 주어가 Graph다 — "AI Agent 시대, **Graph는 어떻게 Context가 되는가**". 에이전트는 배경이고, 다뤄야 할 대상은 그 옆에 있는 데이터라는 배치다.

이걸 뒤집으면 이 글의 질문이 된다. **에이전트에서 뭔가를 얻으려면 손을 대야 하는 곳이 어디인가.** 프로그램의 대답은 일관되게 "모델이 아니다"이다.

---

## 2. "AI Ready Data"는 마케팅 용어가 아니다

먼저 이 말이 정의된 용어인지부터 확인했다. 정의돼 있다.

미국 NIST가 NSF 지원으로 진행한 워크숍 보고서(NIST AMS 100-72)는 이렇게 쓴다.

> "AI-Ready data is consistently and persistently contextualized, qualified, prepared, and engineered for multiple applications at multiple operational scales."[^nist-ams]

번역하면 — **일관되고 지속적으로 맥락이 부여되고(contextualized), 품질이 판정되고(qualified), 준비되고(prepared), 가공된(engineered)** 데이터다. 네 동사 중 앞의 둘이 핵심이다. 맥락 부여와 품질 판정은 데이터를 "많이 모으는 것"과 전혀 다른 작업이다.

더 중요한 문장은 NSF의 2026년 공모(NSF 26-512)에 있다.

> "while the scientific community has a long and successful track record of curating datasets, this has often been done in the context of preparing the data **for use by humans** or heuristic scripting. AI systems and tools are rising in prominence and capability. **In some cases, they become the initial consumer of datasets.**"[^nsf]

**AI가 데이터의 첫 번째 소비자가 된다.** 이 한 문장이 전환의 정체다. 지금까지 우리가 만든 데이터 정리물 — 대시보드, 리포트, README, 위키 — 는 전부 *사람이 읽는다*는 전제로 설계됐다. 그 전제가 깨지면 정리물의 형태가 달라져야 한다.

용어가 정의됐으면 표준도 있다. ISO/IEC 5259 시리즈가 "Data quality for analytics and machine learning (ML)"를 다루고, NIST의 AI 표준 국제협력 계획은 training-data practices를 **"당장 표준화가 필요하고 준비된"** 1티어 주제로 분류한다.[^nist-plan] 세미나의 김정원 교수 세션 제목이 "표준 체계"인 건 그래서 자연스럽다.

---

## 3. 에이전트는 사람과 다르게 읽는다

그럼 "AI가 소비자"가 되면 뭐가 달라지나. Anthropic의 엔지니어링 문서가 에이전트를 이렇게 정의한다.

> "we've gravitated towards a simple definition for agents: **LLMs autonomously using tools in a loop.**"[^anthropic-ctx]

도구를 루프로 돌린다는 건, 에이전트가 데이터를 **한 번에 통째로 받는 게 아니라 필요할 때마다 꺼내 온다**는 뜻이다. 같은 문서가 그 전략을 명시한다.

> "Rather than pre-processing all relevant data up front, agents built with the 'just in time' approach maintain **lightweight identifiers (file paths, stored queries, web links, etc.)** and use these references to dynamically load data into context at runtime using tools."[^anthropic-ctx]

그리고 그 이유:

> "Given that LLMs are constrained by a finite attention budget, good context engineering means **finding the smallest possible set of high-signal tokens** that maximize the likelihood of some desired outcome."[^anthropic-ctx]

여기서 실무적으로 중요한 결론 세 개가 나온다.

**첫째, 식별자가 데이터만큼 중요하다.** 에이전트가 just-in-time으로 꺼내려면 "무엇을 꺼낼지"를 먼저 알아야 한다. 파일 경로·쿼리 이름·URL 같은 얕은 식별자가 곧 인덱스다. 같은 문서는 파일 시스템 자체가 신호를 준다고 말한다 — "file sizes suggest complexity; naming conventions hint at purpose; timestamps can be a proxy for relevance." **이름을 잘 짓는 것이 에이전트에게는 메타데이터를 붙이는 것과 같은 일이다.**

**둘째, 양이 아니라 신호 대 잡음이다.** 사람용 데이터 정리는 "빠짐없이"가 미덕이지만, 유한한 attention budget 앞에서는 빠짐없음이 곧 오염이다. 여기서 §2의 "qualified"(품질 판정)가 왜 정의에 들어갔는지가 이어진다. 품질 판정은 필터링과 가중치의 전제 조건이다.

**셋째, 관계가 텍스트 안에 숨어 있으면 안 된다.** 루프로 도는 에이전트는 한 문서를 읽고 다음에 무엇을 읽을지 스스로 정한다. 문서 A와 B의 관계가 A의 세 번째 문단 서술 속에만 있으면, 에이전트는 B로 넘어갈 근거를 못 찾는다. **관계는 본문이 아니라 구조에 있어야 한다.** — 이게 그래프 이야기로 넘어가는 지점이다.

---

## 4. 그래프가 Context가 되는 지점은 "전역 질문"이다

"AI Agent 시대, Graph는 어떻게 Context가 되는가"라는 세션 제목의 근거가 될 만한 1차 연구는 Microsoft Research의 GraphRAG다. 논문 초록이 문제를 정확히 짚는다.

> "However, **RAG fails on global questions directed at an entire text corpus**, such as 'What are the main themes in the dataset?', since this is inherently a query-focused summarization (QFS) task, rather than an explicit retrieval task."[^graphrag-paper]

벡터 유사도 검색은 "이 질문과 닮은 조각"을 찾는다. 그런데 "전체에서 무엇이 중요한가", "지난 2주 동안 뭐가 바뀌었나" 같은 질문은 닮은 조각이 애초에 없다. **전체를 알아야 답할 수 있는 질문에 부분 검색으로 답하려니 실패한다.**

GraphRAG의 해법은 LLM으로 원문에서 엔티티 지식그래프를 뽑고, 밀접한 엔티티 군집(community)마다 요약을 미리 만들어 두는 것이다. 질의가 오면 조각이 아니라 이 **요약 계층**을 훑는다.[^graphrag-ms]

수치도 공개돼 있다. 단, **이건 Microsoft Research가 자사 방법을 자체 평가한 결과**라는 라벨을 붙여 읽어야 한다.

- 100만 토큰 규모 데이터셋의 전역 질의에서 기존 RAG 대비 답변의 **포괄성(comprehensiveness)과 다양성(diversity)이 유의미하게 개선**됐다고 보고한다.[^graphrag-paper]
- 후속 개선(dynamic community selection)에서 AP News 데이터 50개 전역 질문 기준 **총 토큰 비용 평균 77% 절감**, 품질은 통계적 유의차 없음. 더 깊은 레벨까지 탐색하면 승률 58~60%로 개선되지만 **비용은 평균 34% 증가**.[^graphrag-dynamic]

같은 조건에서 제3자가 재현한 중립 벤치마크는 내가 찾지 못했다. 그러니 "그래프가 벡터보다 낫다"가 아니라 **"전역 질문이라는 특정 실패 유형에 대해, 개발사가 보고한 개선치가 이만큼 있다"**까지가 정확한 진술이다.

온톨로지도 마찬가지 선을 지켜야 한다. 온톨로지 자체는 W3C의 OWL·RDF로 20년 넘게 표준화된 기술이고 사양은 공개돼 있다.[^w3c-owl] 하지만 **"온톨로지가 기업의 손익에 미치는 영향"에 대한 중립적·검증 가능한 정량 근거는 나는 확인하지 못했다.** 세션 제목이 던지는 질문이지 이미 나온 답이 아니다. 나는 그 수치를 지어내지 않겠다.

---

## 5. 내 에이전트 스택을 열어봤다 — 구멍 세 개

여기까지는 남의 문서다. 그래서 내가 실제로 굴리는 걸 오늘 측정했다. 나는 K3s 홈랩 위에 에이전트용 지식 계층을 세 겹 올려뒀다 — 파일 기반 위키(`~/wiki`), 벡터 검색 QA 서비스(`memory-qa`), 지식그래프. 그 세 겹이 §2~§4의 기준을 얼마나 만족하는지 봤다.

### 5.1. 200 OK, 49ms 캐시, 그런데 답이 없다

`memory-qa`는 잘 돌고 있다. 같은 질문을 두 번 던졌다.

```
시도1: time=5.241430s code=200
시도2: time=0.049003s code=200
```

첫 호출 5.24초, 두 번째 49밀리초. 캐시가 **약 107배** 빠르다. 파이프라인은 완벽하게 동작한다. 문제는 답이었다.

```json
{"answer": "제공된 컨텍스트에는 홈랩 클러스터에서 카프카가 어떻게 구성되어 있는지에 대한 정보가 없습니다.",
 "sources": ["viking://user/default/memories/kv/.overview.md",
             "viking://user/default/memories/kv/cluster-status.md",
             "viking://user/default/memories/kv/lemuel-cluster-facts.md"],
 "model": "gemini-2.5-flash", "cached": false}
```

질문은 "홈랩 클러스터에서 카프카는 어떻게 구성돼 있나"였다. **나는 바로 한 시간 전에 그 클러스터의 카프카 토픽 38개와 컨슈머 그룹 10개를 전부 실측했다.** 그런데 검색은 `cluster-status.md`, `lemuel-cluster-facts.md` 같은 **이름만 그럴듯한 문서 셋**을 골라왔고, 거기엔 카프카가 없었다.

이게 §4에서 인용한 실패 유형 그대로다. 벡터 유사도는 "클러스터"와 "카프카"라는 단어에 가까운 문서를 성실하게 찾아왔다. 하지만 "클러스터의 메시징 구성"이라는 **관계**는 어느 문서 이름에도, 어느 청크에도 없었다. 모델은 멀쩡하고(gemini-2.5-flash), 서비스는 200이고, 캐시는 100배 빠르다. **그런데 데이터가 에이전트에게 도달하지 않았다.**

여기서 배울 점은 뻔한 결론이 아니다. **관측 지표가 전부 초록불인데 결과가 비어 있을 수 있다**는 것이다. latency, 응답 코드, 캐시 적중률 — 어느 것도 "답이 있었는가"를 측정하지 않는다.

### 5.2. 표준 문서가 조용히 반으로 줄어 있었다

`~/wiki`에는 스키마 정의 문서 `SCHEMA.md`가 있다. 최초 커밋과 지금을 비교했다.

```
$ git show fe3a7e8:SCHEMA.md | wc -c
1245
$ wc -c < SCHEMA.md
717
```

**1245바이트에서 717바이트로.** 사라진 섹션을 뽑아보면:

```
< ## Frontmatter Template
< ## Tag Taxonomy
< ## Page Thresholds
```

없어진 셋이 하필 **에이전트가 문서를 기계적으로 읽는 데 필요한 것 전부**다. 프론트매터 템플릿(필드 정의), 태그 분류 체계, 페이지 분할 기준. §2의 정의로 말하면 "contextualized"와 "qualified"를 담당하던 부분이 통째로 빠졌다.

누가 지웠는지는 중요하지 않다. 자동 스냅샷 커밋 사이 어딘가에서 병합 사고로 줄었고, **아무도 몰랐다.** 왜 몰랐나 — 검사하는 게 없으니까.

### 5.3. 규칙은 있는데 준수율은 76%다

같은 `SCHEMA.md`의 남은 부분에는 이 규칙이 살아 있다.

> "모든 페이지는 YAML frontmatter로 시작"

전수 검사했다.

```
frontmatter 있는 문서: 54 / 71  (76%)
```

**17개 문서가 규칙을 어기고 있고, 몇 달째 아무 일도 일어나지 않았다.** 문서 71개, 개념 15 · 엔티티 4 · 인시던트 10 · 비교 1.

역설적인 건, 같은 위키에 `DATA-STANDARD.md`라는 9.8KB짜리 데이터 표준 문서가 이미 있다는 점이다. 목차를 보면 이렇다.

```
N1. 시각(Timestamp) — 전부 UTC · tz-aware
N2. 식별자(Identifier)
N3. 주체(Subject/Actor) — 의미 분리
N4. 이벤트 봉투(Event Envelope) — 표준 계약
N5. 금액(Money)   N6. Enum   N7. 명명(Naming)
N8. 수치·단위(Units)   N9. 벡터·임베딩
용어집 (Canonical Glossary)
레포별 적합성(Conformance) 요약
Enforcement (실행 가능 스펙)
변경 프로세스 / 소유권
```

이건 사실상 내가 혼자 만든 "AI Ready Data 표준 체계"다. 식별자, 시각 정규화, 이벤트 봉투, 용어집, 적합성, 소유권 — §2에서 인용한 NIST 정의의 항목들과 거의 겹친다.

**그런데 그 표준을 강제하는 게이트가 없다.** 그래서 5.2에서 스키마가 반으로 줄었고, 5.3에서 준수율이 76%에 머물렀다. 표준을 쓰는 것과 표준이 지켜지는 것은 별개의 공정이고, **두 번째를 만들지 않으면 첫 번째는 시간이 지나면서 조용히 증발한다.**

세미나 마지막 세션 제목이 "공공데이터로 **검증**하는 AI Ready Data **진단**과 구축"인 게 이 대목에서 다시 읽힌다. 구축이 아니라 진단과 검증이 제목에 먼저 나온다.

---

## 6. 그래서 에이전트에서 얻을 수 있는 것

프로그램과 실측을 합치면 이렇게 정리된다.

**얻을 수 있는 것은 "더 똑똑한 모델"이 아니라 "내 데이터가 에이전트에게 보이게 되는 것"이다.** 5.1이 그 증거다. 모델은 최신이었고 파이프라인은 200이었는데, 데이터가 안 보여서 답이 비었다. 그 상태에서 모델을 더 큰 걸로 바꿔도 결과는 똑같다.

그래서 실행 순서는 이렇게 뒤집힌다.

1. **식별자와 이름부터.** 에이전트는 파일명·경로·타임스탬프를 신호로 쓴다.[^anthropic-ctx] 이름 짓기가 메타데이터 작업이다. 비용이 가장 싸고 효과가 가장 빠르다.
2. **관계를 본문에서 구조로 꺼낸다.** 전역 질문에 답해야 한다면 벡터 검색만으로는 구조적으로 부족하다.[^graphrag-paper] 그래프는 그 실패 유형에 대한 대응이지, 만능 업그레이드가 아니다.
3. **표준을 쓰고, 그 다음에 게이트를 만든다.** 게이트 없는 표준의 수명은 §5.2가 보여준다. 1245바이트에서 717바이트까지 걸린 시간은 몇 주였다.
4. **"답이 있었는가"를 지표로 만든다.** latency와 200 OK는 이 질문에 답하지 않는다.

그리고 이 세미나에 간다면 나는 이걸 물어볼 것이다 — 세션 제목이 이미 던져 놓은, 아직 공개된 답이 없는 질문들이다.

- **AI Ready Data 표준 체계 세션에**: 적합성(conformance)을 *자동으로* 판정하는 방법이 있나. 사람이 체크리스트로 보는 것 말고. (내 위키의 76%는 사람이 봤으면 진작 걸렸을 문제였고, 아무도 안 봤기 때문에 안 걸렸다.)
- **온톨로지 세션에**: 손익 영향을 어떤 단위로 측정했나. 온톨로지 도입 전후 비교인가, 도입군/비도입군 비교인가. — 나는 이 주제의 **중립적 정량 근거를 찾지 못했다.** 그래서 진짜로 궁금하다.
- **Graph가 Context가 되는가 세션에**: 그래프 인덱싱 비용(LLM으로 엔티티 추출하는 비용)이 검색 개선분을 넘어가는 손익분기점이 어디인가. GraphRAG 후속 연구도 깊이를 늘리면 비용이 34% 늘었다고 보고한다.[^graphrag-dynamic]
- **현장 세션들에**: "AI Ready 하지 않은" 데이터의 가장 흔한 실패 형태가 무엇이었나. 내 경우는 **품질이 아니라 도달**이었다(5.1). 산업 현장도 같은가.

---

## 7. 한 줄

**에이전트가 못 하는 일의 대부분은 모델이 모자라서가 아니라, 데이터가 에이전트에게 도달하지 않아서다.** 세션 7개에 모델 이야기가 한 줄도 없는 프로그램은, 이 업계가 이미 그 결론에 도달했다는 신호로 읽힌다.

내 스택에서 오늘 확인한 건 세 줄로 요약된다 — 캐시는 107배 빨라졌고(5.1), 답은 비어 있었고(5.1), 그걸 알려주는 지표는 없었다(5.3). 고칠 순서는 명확하다.

관련해서 이전에 쓴 글들:

- [지식그래프 RAG 구축기 (Graphify)]({% post_url 2026-08-04-graphify-knowledge-graph-rag %})
- [에이전트를 CI·Graphiti·DIKW로 쓰는 법]({% post_url 2026-08-10-how-i-use-agents-ci-graphiti-dikw %})
- [ML 에이전트와 LLM-Wiki]({% post_url 2026-08-11-ml-agent-llm-wiki %})

---

## References

**1차·공식 출처**

- NIST, *Artificial Intelligence with Open and Scaled Data Sharing in the Semiconductor Industry* (NIST AMS 100-72), NSF award 2334590 지원. AI-Ready data 정의. <https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.100-72.pdf>
- NSF, *NSF 26-512: Unlocking Dataset Value for AI-Enabled Scientific Discovery (AI Datasets)* 공모 요강. AI 도구가 데이터셋의 최초 소비자가 되는 전환. <https://www.nsf.gov/funding/opportunities/ai-datasets-unlocking-dataset-value-ai-enabled-scientific-discovery/nsf26-512/solicitation>
- NIST, *A Plan for Global Engagement on AI Standards* (NIST AI 100-5e2025). training-data practices의 표준화 우선순위, ISO/IEC SC 42 및 ISO/IEC 5259 시리즈 언급. <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-5e2025.pdf>
- Anthropic, *Effective context engineering for AI agents* (2025-09-29). 에이전트 정의, just-in-time 컨텍스트, attention budget. <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- W3C, *OWL 2 Web Ontology Language Document Overview (2nd Edition)*, W3C Recommendation. <https://www.w3.org/TR/owl2-overview/>

**개발사 자체 평가 (라벨 필요)**

- Microsoft Research, *From Local to Global: A Graph RAG Approach to Query-Focused Summarization* (2024). arXiv:2404.16130. 전역 질문에서 기존 RAG의 실패와 GraphRAG의 개선 보고 — **개발사 자체 평가이며 동일 조건의 제3자 재현 결과는 확인하지 못했다.** <https://arxiv.org/abs/2404.16130>
- Microsoft Research, *GraphRAG: Improving global search via dynamic community selection* (2024-11-15). 토큰 비용 77% 절감 및 레벨3 탐색 시 비용 34% 증가 수치 — 동일 라벨 적용. <https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/>

**행사 정보**

- AI Ready Data 2026 세미나, 2026.9.3(목) 13:00~17:45, 포스코타워 역삼 이벤트홀 3층. 주최·주관 중앙대학교 HIKE 연구실. 사전등록 <https://onoffmix.com/event/347396>. 본문에 인용한 세션 제목·연사 소속은 주최 측 배포 포스터에 기재된 내용이며, **발표 내용에 대한 서술은 일절 하지 않았다.**

**본인 실측 (재현 가능한 명령까지만 주장)**

- 2026-08-13, 단일 K3s 홈랩에서 측정. `memory-qa` 서비스에 동일 질문 2회 POST(5.24s → 0.049s, 두 번 다 HTTP 200), `git show fe3a7e8:SCHEMA.md | wc -c` 대 `wc -c < SCHEMA.md`(1245 → 717), `~/wiki` 마크다운 71개 중 YAML 프론트매터 보유 54개. **단일 환경 1회 관측이며 일반화하지 않는다.**

[^nist-ams]: NIST AMS 100-72, "AI-Ready data is consistently and persistently contextualized, qualified, prepared, and engineered for multiple applications at multiple operational scales."
[^nsf]: NSF 26-512 Solicitation, "AI systems and tools are rising in prominence and capability. In some cases, they become the initial consumer of datasets."
[^nist-plan]: NIST AI 100-5e2025, 1티어("Urgently needed and ready for standardization")에 training-data practices 포함.
[^anthropic-ctx]: Anthropic, "Effective context engineering for AI agents", <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
[^graphrag-paper]: Microsoft Research, "From Local to Global: A Graph RAG Approach to Query-Focused Summarization", arXiv:2404.16130
[^graphrag-ms]: Microsoft, GraphRAG 공식 문서, <https://microsoft.github.io/graphrag/>
[^graphrag-dynamic]: Microsoft Research Blog, "GraphRAG: Improving global search via dynamic community selection", 2024-11-15
[^w3c-owl]: W3C, OWL 2 Web Ontology Language Document Overview, <https://www.w3.org/TR/owl2-overview/>
