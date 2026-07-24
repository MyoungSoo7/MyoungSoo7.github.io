---
layout: post
title: "지식저장소는 에이전트 하네스의 무엇을 바꾸는가 — 다섯 개의 지렛대"
date: 2026-07-24 12:40:00 +0900
categories: [AI, Architecture]
tags: [KnowledgeRepository, Harness, RAG, ContextEngineering, AGENTSmd, MCP, Skills, Provenance, Governance, Agents]
---

# 지식저장소는 에이전트 하네스의 무엇을 바꾸는가 — 다섯 개의 지렛대

> 모델은 고정되어 있고, 바뀌는 것은 그 주변이다. 잘 설계된 지식저장소는 단순한 '문서 더미'가 아니라 에이전트 하네스의 운영체제 표면(surface)으로 작동한다. 검색 범위·컨텍스트 비용·도구 행동·신뢰도·운영 통제라는 다섯 지렛대를 통해서다.

![지식저장소가 AI 에이전트 하네스 운영에 주는 다섯 지렛대 — 검색 범위·컨텍스트 비용·도구 행동·신뢰도·운영 통제](/assets/images/knowledge-repo/knowledge-repo-5-pillars.jpg)

## 들어가며: 하네스는 모델이 아니라 '주변 장치'다

AI 에이전트를 오래 굴려보면 한 가지가 분명해진다. 성능을 좌우하는 변수는 대개 모델 그 자체가 아니라 **모델을 감싸고 있는 하네스(harness)** 다. 어떤 지식을 언제 읽히고, 어떤 규약으로 도구를 쓰게 하며, 어디까지 자율로 두고 어디서 멈춰 세우는가 — 이 배선(配線)이 실제 산출물의 품질을 만든다.

이 글은 그 배선의 중심에 **지식저장소(knowledge repository)** 를 놓고 본다. 여기서 지식저장소란 프로젝트의 지식을 구조화·버전화·질의 가능하게 담아 둔 저장소를 말한다. 메타데이터로 색인되고, 요약이 컴파일되어 있으며, 원문 출처가 참조로 연결되고, 변경이 거버넌스 아래 놓인 저장소다. 핵심 주장은 단순하다. **이런 저장소는 문서가 아니라 하네스의 외장 기억(external memory)이자 거버넌스 레이어이며, 아래 다섯 지렛대를 통해 운영 자체를 바꾼다.**

논의의 전제 하나. 대형 언어모델에게 컨텍스트 창은 크지만 **유한한 자원** 이다. Anthropic은 이를 "추론 시 모델이 보는 토큰 집합을 최적으로 큐레이션·유지하는 문제"로 규정하며, 프롬프트 엔지니어링의 자연스러운 다음 단계로 '컨텍스트 엔지니어링'을 제시한다(벤더 자신의 프레이밍).[^ce] 지식저장소의 효과는 대부분 이 유한성 위에서 발생한다.

## 1. 검색 범위 — 유한한 컨텍스트에서 '무엇을 안 읽을지'의 문제

첫 지렛대는 검색 범위다. 다이어그램의 표현을 빌리면 "path·metadata filter로 필요한 지식만 읽는" 능력이다.

직관은 "다 넣으면 좋지 않은가"이지만, 1차 연구는 반대를 가리킨다. Liu 등의 「Lost in the Middle」(TACL 2024)은 다중 문서 QA와 key-value 검색에서 **관련 정보가 입력의 처음이나 끝에 있을 때 성능이 가장 높고, 한가운데 있을 때 뚜렷하게 저하**되는 U자형 패턴을 보고했다. 명시적으로 롱컨텍스트를 표방하는 모델에서도 이 저하가 나타난다는 점이 핵심이다.[^litm] 즉 컨텍스트에 무언가를 더 넣는 것은 공짜가 아니라, 정작 중요한 근거를 '가운데'로 밀어 넣어 묻어버리는 위험을 동반한다.

여기서 지식저장소의 색인(path·metadata)이 가치를 만든다. 전부를 밀어 넣는 대신 **필요한 것만 선별해 읽히는 것** — 이는 검색 증강 생성(RAG)이 처음부터 겨냥한 지점이기도 하다. Lewis 등(NeurIPS 2020)은 사전학습된 파라메트릭 기억(seq2seq)과 비파라메트릭 기억(위키피디아 밀집 벡터 인덱스)을 결합해, 필요한 근거만 검색해 생성에 조건화하는 구조를 제시했다.[^rag] 지식저장소의 메타데이터 필터는 이 '선별 읽기'를 프로젝트 지식 전반으로 확장한 것으로 볼 수 있다.

정리하면, 검색 범위 지렛대의 본질은 '무엇을 읽을지'가 아니라 **'무엇을 안 읽을지'를 저비용으로 결정하는 능력** 이다.

## 2. 컨텍스트 비용 — 요약과 인덱스는 토큰 경제학이다

두 번째 지렛대는 비용이다. "Compiled Summary와 Index 구성으로 토큰 낭비 최소화."

컨텍스트가 유한 자원이라면, 저장소가 원문 대신 **컴파일된 요약과 인덱스** 를 먼저 제공하는 것은 곧 토큰 경제학이다. 필요한 항목만 요약 수준에서 훑고, 정말 필요할 때만 원문으로 내려가는 구조 — 이는 운영체제의 계층적 메모리와 정확히 같은 발상이다. Packer 등의 MemGPT(2023)는 OS의 가상 메모리에서 착안해, 빠른/느린 메모리 계층 사이로 데이터를 옮기며 제한된 컨텍스트 창 안에서 더 큰 기억을 다루는 기법을 제시했다.[^memgpt] 요약-우선, 원문-지연(lazy) 구조의 이론적 사촌 격이다.

Anthropic 역시 컨텍스트를 '고갈되는 자원'으로 보고, 대화가 길어질 때 이력을 압축(compaction)하고 정말 중요한 것만 유지하는 큐레이션을 핵심 규율로 든다(벤더 프레이밍).[^ce] 지식저장소의 Compiled Summary·Index는 이 압축을 **런타임 이전에, 저장소 설계 시점에 미리 해 두는 것** 이라 볼 수 있다.

다만 여기엔 정직한 유보가 필요하다. 요약은 손실 압축이다. 요약 단계에서 버려진 디테일이 하필 그 작업에 필요한 근거였을 수 있다. 그래서 좋은 저장소는 요약과 원문 사이를 값싸게 오갈 수 있는 링크(다음 절의 source_references)를 반드시 함께 둔다. 요약은 비용을 줄이되, **원문으로의 복귀 경로를 끊지 않을 때만** 안전하다.

## 3. 도구 행동 — 규약을 '문서'가 아니라 '실행 가능한 표면'으로

세 번째 지렛대는 행동의 표준화다. "Agent Skill · Plugins · AGENTS.md 로 행동 규약을 표준화."

에이전트의 재현성 문제 상당 부분은 '같은 상황에서 같은 규약으로 도구를 쓰는가'로 환원된다. 최근 생태계는 이 규약을 사람이 읽는 문서가 아니라 **에이전트가 파싱하고 실행하는 표면** 으로 옮기는 중이다.

- **AGENTS.md** 는 코딩 에이전트에게 프로젝트 컨텍스트·규약을 주기 위한 개방 표준으로, 필수 구조가 없는 최소한의 마크다운 형식이다. OpenAI·Google·Cursor·Sourcegraph·Factory 등이 함께 출범시켰고, 현재는 Linux Foundation 산하 Agentic AI Foundation이 관리한다(표준 자체는 1차 출처, 채택 규모 수치는 프로젝트 측 주장).[^agentsmd]
- **Model Context Protocol(MCP)** 은 Anthropic이 2024년 11월 공개한, AI 시스템과 외부 도구·데이터를 잇는 개방 표준이다. 매 데이터 소스마다 맞춤 연동을 만들던 파편화를 단일 프로토콜로 대체하는 것을 목표로 하며, 2025년 12월 Agentic AI Foundation에 기부되어 벤더 중립 표준이 되었다.[^mcp]
- **Agent Skills** 는 지시·스크립트·리소스를 담은 폴더(SKILL.md + 선택적 scripts/·references/·assets/)로, 에이전트가 필요할 때 동적으로 발견·로드하는 조합 가능한 단위다(벤더 문서 기준).[^skills]

이 셋의 공통점은 **행동 규약을 저장소 안에 코드처럼 얹어 둔다** 는 것이다. 지식저장소는 바로 이 규약이 사는 집이다. 규약이 문서로만 존재하면 매 세션 사람의 해석에 의존하지만, 실행 가능한 표면으로 저장소에 박히면 세션 간 편차가 줄고 재현성이 올라간다.

## 4. 신뢰도 — 답변을 출처로 역추적할 수 있는가

네 번째 지렛대는 신뢰도다. "source_references로 참조한 문서를 통해 답변을 역추적 가능."

언어모델의 환각(hallucination)은 잘 정리된 연구 주제다. Ji 등의 서베이(ACM Computing Surveys, 2023)는 요약·대화·생성형 QA 등 여러 과업에서 나타나는 환각을 정의·분류하고 완화 기법을 정리한다.[^halluc] 문제는 '틀릴 수 있다'가 아니라 '**어디서 왔는지 되짚을 수 없으면 맞는지조차 검증할 수 없다**'는 데 있다.

그래서 저장소가 답변에 원문 참조(source_references)를 물려 두는 것은 단순 편의가 아니라 **검증 가능성(verifiability)의 전제** 다. Gao 등(EMNLP 2023)의 ALCE는 인용을 동반한 생성을 위한 최초의 벤치마크로, 유창성·정확성·인용 품질 세 축으로 평가한다. 이들은 최신 모델조차 여전히 개선 여지가 크다고 보고했는데, 예컨대 ELI5에서는 최상위 모델도 답변의 절반가량이 완전한 인용 근거를 갖추지 못했다.[^alce] 인용을 붙이는 일이 저절로 되지 않는다는 뜻이며, 그래서 저장소 차원에서 참조 링크를 구조적으로 강제하는 설계가 값을 한다.

역추적 가능성이 서면, 검토자는 "그럴듯하다"가 아니라 "이 문서의 이 대목에 근거했다"를 확인할 수 있다. 신뢰는 모델이 더 똑똑해져서가 아니라, **주장과 근거 사이의 배선이 끊기지 않아서** 생긴다.

## 5. 운영 통제 — 자동 / 제안 / 차단의 경계 설계

마지막 지렛대는 통제다. "PR·CI·OWNER로 자동/제안/차단 분리."

에이전트 설계의 근본 긴장은 자율성과 사람의 감독 사이에 있다. Anthropic은 효과적인 감독이 "모든 행동을 승인받는 것"이 아니라 "**중요한 순간에 개입할 수 있는 위치에 있는 것**"이라고 정리한다. 매 행동 승인을 요구하는 방식은 안전 이득 없이 마찰만 키우기 쉽고, 실제로 Claude Code는 기본을 읽기 전용 권한으로 두고 신뢰하는 반복 작업에만 지속 권한을 부여하는 식으로 자율성을 스스로 제한한다(벤더 프레이밍·자사 제품 기준).[^agents]

지식저장소와 그 주변 파이프라인은 이 '개입 가능한 위치'를 **코드로 새긴다.** PR은 변경을 제안 단계에 머물게 하고, CI는 자동 통과 조건과 차단 조건을 기계적으로 가르며, OWNER(코드 오너십)는 어느 영역을 누가 승인해야 하는지를 못 박는다. 즉 자동(auto)·제안(suggest)·차단(block)의 경계가 사람의 그때그때 판단이 아니라 저장소의 규칙으로 고정된다. 이것이 하네스에 통제를 '주입'하는 가장 견고한 방법이다 — 규칙이 저장소에 살아 있으면, 감독은 재현 가능하고 감사 가능해진다.

## 종합: 지식저장소는 하네스의 운영체제 표면이다

다섯 지렛대를 하나로 꿰면 이렇게 읽힌다. 잘 설계된 지식저장소는 에이전트가

1. **무엇을 읽고**(검색 범위),
2. **얼마의 토큰 비용으로**(컨텍스트 비용),
3. **어떤 규약으로 도구를 쓰며**(도구 행동),
4. **얼마나 검증 가능하게 답하고**(신뢰도),
5. **어디까지 자율로 움직일지**(운영 통제)

를 결정하는 **운영체제 표면** 으로 작동한다. 모델을 바꾸지 않고도 이 다섯을 바꿀 수 있다는 점이 핵심이다. 하네스 개선의 대부분은 더 큰 모델이 아니라, 이 표면을 더 잘 조직하는 데서 온다.

## 그늘: 저장소가 만드는 새로운 실패 모드

균형을 위해 반대편도 정직하게 적는다. 지식저장소는 공짜 이득이 아니라 **관리 대상 자산** 이다. 방치하면 부채가 된다.

- **낡은 지식(staleness):** 코드가 앞서가고 문서가 뒤처지면, 저장소는 이제 '틀린 근거를 자신 있게 제공하는 장치'가 된다. 회수(retire) 경로가 없는 지식은 신뢰도 지렛대를 거꾸로 당긴다.
- **과잉 검색:** 필터가 느슨하면 '필요한 것만'이 아니라 '관련돼 보이는 전부'가 딸려 들어와, 1절의 U자형 저하를 오히려 심화시킨다.
- **규약 표류:** AGENTS.md·Skills가 늘어나기만 하고 정리되지 않으면 규약끼리 충돌하고, 표준화가 오히려 혼선을 만든다.

이 항목들에 대한 중립적 제3자 벤치마크는 아직 빈약하다. 위 위험은 대체로 운영 경험과 1절의 롱컨텍스트 저하 같은 1차 근거에서 연역한 것이며, 정량적 우열을 주장하는 문장이 아님을 밝혀 둔다. 요지는 하나다 — **저장소의 효과는 '있음'이 아니라 '거버넌스됨'에서 나온다.**

## 닫으며

지식저장소를 문서 창고로 보면 그 효과는 부수적이다. 그러나 하네스의 운영체제 표면으로 보면, 그것은 검색·비용·행동·신뢰·통제라는 다섯 축을 동시에 조절하는 중앙 장치가 된다. 모델은 계속 좋아지겠지만, 그 힘을 재현 가능하고 검증 가능하며 통제 가능한 산출물로 바꾸는 일은 여전히 하네스의 몫이고, 그 하네스의 심장에 저장소가 있다.

---

## References

- Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2024). *Lost in the Middle: How Language Models Use Long Contexts.* TACL, 12, 157–173. [aclanthology.org/2024.tacl-1.9](https://aclanthology.org/2024.tacl-1.9/) · [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)
- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 33, 9459–9474. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)
- Packer, C., Fang, V., Patil, S. G., Lin, K., Wooders, S., & Gonzalez, J. E. (2023). *MemGPT: Towards LLMs as Operating Systems.* [arXiv:2310.08560](https://arxiv.org/abs/2310.08560)
- Ji, Z., et al. (2023). *Survey of Hallucination in Natural Language Generation.* ACM Computing Surveys, 55(12), Article 248. [dl.acm.org/doi/10.1145/3571730](https://dl.acm.org/doi/10.1145/3571730) · [arXiv:2202.03629](https://arxiv.org/abs/2202.03629)
- Gao, T., Yen, H., Yu, J., & Chen, D. (2023). *Enabling Large Language Models to Generate Text with Citations.* EMNLP 2023. [aclanthology.org/2023.emnlp-main.398](https://aclanthology.org/2023.emnlp-main.398/) · [arXiv:2305.14627](https://arxiv.org/abs/2305.14627)
- Anthropic. *Effective context engineering for AI agents* (Engineering blog, 2025 — 벤더 1차 자료). [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic. *Introducing the Model Context Protocol* (2024-11 — 벤더 1차 자료). [anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol) · *Donating MCP / Agentic AI Foundation* (2025-12). [anthropic.com/news/...agentic-ai-foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- Anthropic. *Agent Skills — overview* (Platform docs — 벤더 1차 자료). [platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- Anthropic. *Building Effective AI Agents* / *Our framework for developing safe and trustworthy agents* (벤더 1차 자료). [anthropic.com/research/building-effective-agents](https://www.anthropic.com/research/building-effective-agents) · [anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents](https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents)
- AGENTS.md — 개방 표준(현 Agentic AI Foundation / Linux Foundation 관리). [agents.md](https://agents.md/) · [github.com/agentsmd/agents.md](https://github.com/agentsmd/agents.md)

*출처 등급 표기: 동료심사 논문(TACL·NeurIPS·ACM CS·EMNLP)은 1차 근거로 인용했고, Anthropic 엔지니어링/제품 문서와 AGENTS.md 채택 규모 수치는 '벤더·프로젝트 측 1차 자료'로 라벨링했다. 지식저장소의 실패 모드(4·6절 일부)에 대한 중립적 제3자 헤드투헤드 벤치마크는 현재 부재하여, 해당 대목은 1차 근거로부터의 연역임을 본문에 명시했다.*
