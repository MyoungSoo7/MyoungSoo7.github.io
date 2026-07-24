---
layout: post
title: "AI 에이전트를 잘 다루기 위한 다섯 개의 레이어 — 스택으로 읽는 하네스"
date: 2026-07-24 12:50:00 +0900
categories: [AI, Architecture]
tags: [AgentHarness, Structure, Knowledge, Permission, Observability, ReAct, LeastPrivilege, LlamaGuard, LLMasJudge, Agents]
---

# AI 에이전트를 잘 다루기 위한 다섯 개의 레이어 — 스택으로 읽는 하네스

> 에이전트를 '잘 다룬다'는 것은 더 좋은 프롬프트를 쓰는 일이 아니라, 다섯 개의 레이어를 함께 설계하는 일이다. 구조(STRUCTURE)·지식(KNOWLEDGE)·실행 루프(EXECUTION/LOOP)·권한(PERMISSION)·관측(OBSERVABILITY). 각 층은 서로 다른 실패를 막고, 서로 다른 지렛대를 쥔다.

![AI 에이전트를 잘 다루기 위한 다섯 레이어 — STRUCTURE(AGENTS.md·md-architecture·500-line-per-md), KNOWLEDGE(LLM-wiki·Skills·sub-agents·agent-team), EXECUTION/LOOP(Hooks·cron·worktree·goal), PERMISSION(sLLM-guard·allowed-tools·MCP-split·DB-view), OBSERVABILITY(diff-watch·session-log·eval-loop·token-board)](/assets/images/agent-layers/agent-5-layers.jpg)

## 들어가며: 에이전트는 '설득'이 아니라 '스택'으로 다룬다

에이전트를 처음 다룰 때 우리는 프롬프트를 붙든다. 더 좋은 문장, 더 그럴듯한 지시. 그런데 조금만 규모가 커지면 깨닫는다. 산출물의 품질을 결정하는 건 문장 하나가 아니라 **에이전트를 둘러싼 레이어 스택** 이라는 것을. 무엇이 어떻게 구조화돼 있고(STRUCTURE), 어떤 지식을 끌어오며(KNOWLEDGE), 어떤 루프로 돌고(EXECUTION), 어디까지 할 수 있으며(PERMISSION), 우리가 그걸 어떻게 지켜보는가(OBSERVABILITY).

이 글은 이 다섯 레이어를 하나씩 고찰한다. 각 층을 1차 문헌에 붙여 "왜 이 층이 필요한가"를 짚되, 층마다 있는 그늘도 함께 적는다. 전제 하나만 깔고 시작하자. 대형 언어모델에게 컨텍스트 창은 크지만 **유한한 자원** 이고, 에이전트 운영의 상당 부분은 이 유한성을 어떻게 다스리느냐의 문제다(Anthropic의 컨텍스트 엔지니어링 프레이밍).[^ce]

## 1. STRUCTURE — 규약을 '읽을 수 있는 한 장'으로 쪼갠다

첫 층은 구조다. 다이어그램의 태그로는 `#AGENTS.md`, `#md-architecture`, `#500-line-per-md`.

에이전트에게 프로젝트를 넘길 때 가장 먼저 필요한 건 "여기선 이렇게 일한다"는 규약이다. 최근 생태계는 이 규약을 **AGENTS.md** 라는 개방 표준으로 모으고 있다. 필수 구조가 없는 최소 마크다운 형식으로, OpenAI·Google·Cursor 등이 함께 출범시켰고 현재는 Linux Foundation 산하 Agentic AI Foundation이 관리한다(표준 자체는 1차 출처, 채택 규모는 프로젝트 측 주장).[^agentsmd]

여기서 `#500-line-per-md`, `#md-architecture` 라는 태그가 중요한 원칙을 담는다. **한 문서를 무한정 키우지 않고, 읽을 수 있는 단위로 쪼갠다**는 것. 이유는 1절에서 다룰 컨텍스트의 유한성과 직결된다. Anthropic은 좋은 컨텍스트를 "가장 적은 토큰으로 가장 넓은 행동 반경을 지시하는, 적절한 고도(altitude)의 정보"로 표현하며, 부풀린 문서보다 최소한의 정예 정보를 권한다(벤더 프레이밍).[^ce] 즉 구조 층의 목표는 '많이 쓰기'가 아니라 **필요할 때 필요한 한 장만 읽히도록 모듈화하기** 다. Agent Skills가 SKILL.md 한 장에 요지를 두고 세부는 하위 폴더로 미루는 점진적 공개(progressive disclosure) 구조를 택한 것도 같은 이유다.[^skills]

구조 층이 부실하면, 에이전트는 매 세션 규약을 '추측'한다. 잘 쪼갠 구조는 그 추측을 없앤다.

## 2. KNOWLEDGE — 파라메트릭 기억 밖의 것을 끌어온다

둘째 층은 지식이다. `#LLM-wiki`, `#Skills`, `#sub-agents`, `#agent-team`.

모델의 가중치 안에 든 지식(파라메트릭 기억)은 고정이고, 최신도 아니며, 우리 프로젝트를 모른다. 그래서 밖의 지식을 끌어오는 층이 필요하다. 고전적 해법이 검색 증강 생성(RAG)이다. Lewis 등(NeurIPS 2020)은 사전학습 파라메트릭 기억과 외부 벡터 인덱스(비파라메트릭 기억)를 결합해, 필요한 근거만 검색해 생성에 조건화하는 구조를 제시했다.[^rag] `#LLM-wiki` 는 이 비파라메트릭 기억을 프로젝트 지식 전반으로 키운 형태로 볼 수 있다.

`#Skills` 는 지식을 **실행 가능한 형태로** 담는다. 지시·스크립트·리소스를 폴더(SKILL.md + 선택적 scripts/·references/)에 넣어 필요할 때 동적으로 로드하는 조합 단위다(벤더 문서 기준).[^skills]

`#sub-agents`, `#agent-team` 은 지식과 작업을 **여러 에이전트로 분산** 한다. Anthropic은 리드 에이전트가 병렬 하위 에이전트에게 위임하는 오케스트레이터-워커 구조로 리서치 시스템을 구축했고, Claude Opus 4 오케스트레이터 + Sonnet 4 하위 에이전트 조합이 단일 Opus 4 대비 내부 평가에서 90.2% 향상을 보였다고 보고했다(벤더 자사 평가). 다만 같은 글은 멀티 에이전트가 일반 대화의 약 15배 토큰을 쓴다고 밝히며, 성과 가치가 비용을 넘어서는 작업에만 적합하다고 못 박는다.[^multiagent] 지식 층의 확장은 공짜가 아니라는 정직한 단서다.

## 3. EXECUTION / LOOP — '생각-행동'을 교대로 돌린다

셋째 층은 실행 루프다. `#Hooks`, `#cron`, `#worktree`, `#goal`.

에이전트가 '에이전트'인 이유는 한 번 답하고 끝나는 게 아니라, **관찰→추론→행동을 반복** 하기 때문이다. 이 루프의 이론적 원형이 ReAct다. Yao 등(ICLR 2023)은 언어모델이 추론 흔적(reasoning trace)과 행동(action)을 교대로 생성하게 하여, 계획을 세우고 조정하면서 외부 환경과 상호작용해 정보를 추론에 반영하는 패러다임을 제시했다.[^react] `#goal` 은 이 루프가 향하는 목적함수, `#Hooks`·`#cron` 은 루프를 언제·무엇으로 촉발하고 개입할지의 트리거, `#worktree` 는 루프가 파괴적 변경을 낼 때 작업공간을 격리하는 장치다.

Anthropic은 이런 자율 루프의 적용 기준을 분명히 한다. 에이전트가 가장 값을 하는 것은 **대화와 행동이 함께 필요하고, 성공 기준이 명확하며, 피드백 루프가 가능하고, 의미 있는 사람의 감독이 통합된** 작업이라는 것(벤더 프레이밍).[^agents] 즉 실행 루프 층의 설계는 '얼마나 자율로 돌릴까'가 아니라 '**어디서 멈추고 무엇으로 되먹일까**'를 정하는 일이다. 루프에 정지·격리·트리거가 없으면, 자율성은 곧 통제 불능이 된다.

## 4. PERMISSION — 할 수 있는 것을 '최소'로 깎는다

넷째 층은 권한이다. `#sLLM-guard`, `#allowed-tools`, `#MCP-split`, `#DB-view`.

에이전트에게 도구를 쥐여 주는 순간, "무엇을 하게 둘 것인가"가 안전의 핵심이 된다. 여기서 반세기 된 보안 원칙이 그대로 살아 있다. Saltzer와 Schroeder(1975)의 **최소 권한 원칙(least privilege)** — 모든 프로그램과 사용자는 작업 완수에 필요한 최소한의 권한만 가져야 한다는 것.[^saltzer] `#allowed-tools`(허용 도구 화이트리스트), `#MCP-split`(연결을 용도별로 분리), `#DB-view`(전체 테이블 대신 제한된 뷰만 노출)는 모두 이 원칙을 에이전트 층위로 옮긴 구현이다.

`#sLLM-guard` 는 다른 각도의 방어다. 큰 모델의 입출력을 작은 안전 전용 모델로 검사하는 방식으로, Meta의 Llama Guard(Inan 등, 2023)가 대표적이다. 프롬프트와 응답을 안전 위험 분류체계에 따라 분류하는 LLM 기반 입출력 세이프가드이며, 프롬프트만으로 새 정책·분류체계에 적응할 수 있다.[^llamaguard] 큰 모델이 뚫려도 작은 문지기가 한 겹 더 막는 구조다.

권한 층의 철학은 Anthropic의 제품 설계와도 맞물린다. Claude Code는 기본을 읽기 전용으로 두고, 신뢰하는 반복 작업에만 지속 권한을 부여한다(벤더·자사 제품 기준).[^agents] 요지는 하나다 — **권한은 기본적으로 닫혀 있고, 필요할 때 명시적으로 열려야 한다.**

## 5. OBSERVABILITY — 지켜볼 수 없으면 다룰 수 없다

마지막 층은 관측이다. `#diff-watch`, `#session-log`, `#eval-loop`, `#token-board`.

앞의 네 층을 아무리 잘 쌓아도, **무슨 일이 벌어졌는지 볼 수 없으면 개선할 수 없다.** `#diff-watch`(변경 감시)와 `#session-log`(세션 로그)는 에이전트의 행동을 사후 추적 가능하게 만들고, `#token-board`(토큰 대시보드)는 비용을 가시화한다. 앞서 본 멀티 에이전트의 15배 토큰 소모[^multiagent]를 떠올리면, 토큰 가시화는 사치가 아니라 운영 필수다.

`#eval-loop` 는 이 층의 심장이다. 사람의 눈으로 매 산출물을 채점하는 건 비싸고 느리다. 그래서 등장한 것이 LLM-as-a-judge다. Zheng 등(NeurIPS 2023)은 MT-Bench와 Chatbot Arena를 제시하며, GPT-4 같은 강한 LLM 심판이 통제·크라우드소싱 인간 선호와 80% 이상 일치(인간끼리의 일치 수준)를 보인다고 보고했다. 이는 값비싼 인간 선호를 확장 가능하고 설명 가능하게 근사하는 방법으로 제시된다.[^llmjudge] 다만 저자들 스스로 위치 편향·자기선호 같은 한계를 함께 지적하며, 심판을 만능으로 보지 말 것을 경고한다 — 관측 층조차 검증이 필요하다는 정직한 신호다.

관측이 없으면 나머지 네 층은 '느낌'으로만 운영된다. 관측이 있으면 비로소 하네스는 **측정→개선의 복리 루프** 에 올라탄다.

## 종합: 다섯 층은 서로 다른 실패를 막는다

다섯 레이어를 한 문장으로 꿰면 이렇게 읽힌다. 에이전트를 잘 다룬다는 것은

1. 규약을 읽을 수 있게 **구조화** 하고(STRUCTURE),
2. 밖의 지식을 필요할 때 끌어오며(KNOWLEDGE),
3. 멈춤·격리·트리거가 있는 **실행 루프** 를 돌리고(EXECUTION),
4. 할 수 있는 것을 **최소로** 깎으며(PERMISSION),
5. 벌어진 일을 **지켜보고 되먹이는**(OBSERVABILITY)

다섯 가지를 함께 설계하는 일이다. 각 층은 서로 다른 실패를 막는다. 구조는 '추측'을, 지식은 '무지·구식'을, 루프는 '통제 불능'을, 권한은 '과잉 행동'을, 관측은 '깜깜이 운영'을 막는다. 어느 한 층만 잘해선 안 되는 이유가 여기 있다 — 스택은 가장 약한 층의 높이에서 무너진다.

## 그늘: 층마다 있는 함정

균형을 위해 반대편도 적는다. 각 층은 이득만큼의 부채도 만든다.

- **구조:** 문서·스킬이 늘기만 하고 정리되지 않으면 규약끼리 충돌한다. 표준화가 오히려 혼선이 된다.
- **지식:** 낡은 위키는 '틀린 근거를 자신 있게 주는 장치'가 되고, 멀티 에이전트는 토큰을 배로 태운다.[^multiagent]
- **루프:** 정지·격리 없는 자율 루프는 조용히 파괴적 변경을 누적한다.
- **권한:** 편의를 위해 한 번 넓힌 권한은 좀처럼 다시 좁혀지지 않는다(권한의 래칫).
- **관측:** LLM 심판 자체가 편향될 수 있다.[^llmjudge] 대시보드가 '보고 있다'는 착각만 줄 수도 있다.

이 함정들에 대한 중립적 제3자 헤드투헤드 벤치마크는 아직 빈약하다. 위 경고는 대체로 1차 근거(컨텍스트 유한성·멀티에이전트 비용·심판 편향)로부터의 연역이며, 정량적 우열 주장이 아님을 밝혀 둔다.

## 닫으며

에이전트를 '설득'의 대상으로 보면 우리는 계속 프롬프트만 매만지게 된다. **스택**으로 보면 다르다 — 구조·지식·루프·권한·관측이라는 다섯 개의 조절 손잡이가 보인다. 모델은 계속 좋아지겠지만, 그 힘을 재현 가능하고 안전하며 측정 가능한 결과로 바꾸는 일은 여전히 이 다섯 층을 함께 다루는 사람의 몫이다. 잘 다룬다는 건, 결국 이 스택을 잘 쌓는다는 뜻이다.

---

## References

- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 33, 9459–9474. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)
- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR 2023. [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- Inan, H., et al. (2023). *Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations.* [arXiv:2312.06674](https://arxiv.org/abs/2312.06674)
- Zheng, L., et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 36. [arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
- Saltzer, J. H., & Schroeder, M. D. (1975). *The Protection of Information in Computer Systems.* Proceedings of the IEEE, 63(9), 1278–1308. (최소 권한 원칙의 출처) [doi.org/10.1109/PROC.1975.9939](https://doi.org/10.1109/PROC.1975.9939)
- Anthropic. *Effective context engineering for AI agents* (Engineering blog, 2025 — 벤더 1차 자료). [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic. *How we built our multi-agent research system* (Engineering blog, 2025 — 벤더 자사 평가). [anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Anthropic. *Building Effective AI Agents* (벤더 1차 자료). [anthropic.com/research/building-effective-agents](https://www.anthropic.com/research/building-effective-agents)
- Anthropic. *Agent Skills — overview* (Platform docs — 벤더 1차 자료). [platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- AGENTS.md — 개방 표준(현 Agentic AI Foundation / Linux Foundation 관리). [agents.md](https://agents.md/)

*출처 등급 표기: 동료심사·아카이브 논문(NeurIPS·ICLR·IEEE Proc.)은 1차 근거로 인용했고, Anthropic 엔지니어링/제품 문서와 AGENTS.md 채택 규모는 '벤더·프로젝트 측 1차 자료(자사 평가 포함)'로 라벨링했다. 90.2%·15배·80% 등 수치는 각 1차 자료가 보고한 값이며, 멀티에이전트 향상치는 벤더 자사 내부 평가 기준임을 본문에 명시했다. 각 층의 실패 모드에 대한 중립적 제3자 벤치마크는 현재 부재하여 해당 대목은 1차 근거로부터의 연역임을 밝혔다.*
