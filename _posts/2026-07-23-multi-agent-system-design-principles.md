---
layout: post
title: "멀티에이전트 시스템 설계 원칙 13가지 — 에이전트의 '집합'이 아니라 '아키텍처'다"
date: 2026-07-23 10:55:00 +0900
categories: [AI, Architecture]
tags: [MultiAgent, AgentArchitecture, ContextEngineering, Orchestrator, GeneratorVerifier, LatencyBudget, Observability, ClaudeCode]
---

# 멀티에이전트는 '에이전트를 여러 개 두는 것'이 아니다

핵심 명제부터. **Multi-Agent System은 Agent의 집합이 아니라, Context를 분배하고 Workflow를 제어하며 Latency와 품질을 운영하는 Architecture다.** 에이전트 수를 늘리는 게 아니라, 이 네 가지 — *컨텍스트·워크플로·지연·품질* — 를 설계하는 일이다.

아래 두 장이 그 설계 원칙 13가지다.

![멀티에이전트 설계 원칙 1~9 — single agent 우선, Skills 지연 로딩, SubAgent 컨텍스트 격리, Router/Fan-out 병렬, Async SubAgent, Handoffs, Agent Teams, Shared State, Generator-Verifier](/assets/images/multi-agent-design-principles-1.jpg)

![멀티에이전트 설계 원칙 10~13 — Prompt caching 고정, latency budget, State/Context/Memory/Artifact 분리, Observability와 Eval](/assets/images/multi-agent-design-principles-2.jpg)

이 글은 13가지 원칙을 명제의 네 축으로 재정렬하고, 각 원칙을 **Anthropic 공식 엔지니어링 자료로 근거**를 대며 정리한다.

---

## 0. 대전제 — 단일 에이전트로 되는 일은 단일 에이전트로

> **원칙 1.** Single agent로 되는 일은 single agent로 처리한다. Multi-Agent는 기본값이 아니라 *명확한 한계가 드러날 때* 도입한다.

이것이 나머지 12개를 지배하는 관문이다. Anthropic도 정확히 같은 말을 한다 — *"가능한 가장 단순한 해법을 찾고, 필요할 때만 복잡도를 올려라(find the simplest solution possible, and only increasing complexity when needed)."* 멀티에이전트는 성능을 위해 **지연과 비용을 지불**하는 교환이며, 그 값을 치를 가치가 있는 작업에만 쓴다.

숫자가 이 경고를 뒷받침한다(Anthropic 공식): 에이전트는 챗 대비 약 **4배**, 멀티에이전트는 약 **15배**의 토큰을 쓴다. 그리고 성능 평가에서 **"토큰 사용량만으로 분산의 80%가 설명"** 된다. 즉 멀티에이전트의 이득은 대체로 *더 많은 토큰을 태운 결과*다. 그래서 "명확한 한계가 드러날 때만"이 맞다.

멀티에이전트가 제값을 하는 조건(Anthropic): **병렬화가 크고, 정보가 단일 컨텍스트 창을 넘고, 복잡한 도구가 많은** 고가치 작업. 반대로 *단계가 사전에 정해져 있거나, 모든 에이전트가 같은 컨텍스트를 공유해야 하는* 작업엔 부적합하다.

---

## 축 1. Context를 분배한다

> **원칙 2.** Instruction이 큰 일은 Skills로 지연 로딩한다 — 절차·템플릿·domain rule을 progressive disclosure로.
> **원칙 3.** Context가 오염되는 일은 SubAgent로 격리한다 — web search, file read, codebase 탐색, DB query처럼 중간 결과가 많은 작업은 *isolated context window* 에서.
> **원칙 12.** State·Context·Memory·Artifact를 분리한다 — prompt는 실행 snapshot일 뿐, 시스템의 진실은 state/memory/artifact layer에 있어야 한다.

컨텍스트는 유한 자원이고, 멀티에이전트의 본질은 **그 자원을 어떻게 쪼개 담느냐**다. Anthropic의 리서치 시스템이 정확히 이 원리로 작동한다 — 서브에이전트들이 **각자의 컨텍스트 창**을 갖고 문제의 다른 측면을 동시에 탐색하며, "distinct tools, prompts, and exploration trajectories"로 관심사를 분리한다. 중간 결과가 폭발하는 탐색(검색·파일 읽기)을 서브에이전트에 격리하면, 그 소음이 메인 컨텍스트를 오염시키지 않는다(원칙 3).

원칙 12의 통찰도 중요하다: **prompt를 진실의 원천으로 착각하지 마라.** prompt는 한 순간의 스냅샷일 뿐이고, 진짜 상태는 별도 계층에 있어야 재현·재개가 가능하다. (이건 [Ouroboros의 이벤트 소싱 원칙](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) — "기록되지 않은 것은 일어나지 않은 것" — 과 같은 뿌리다.)

---

## 축 2. Workflow를 제어한다

> **원칙 4.** 여러 domain을 병렬 조회하면 Router/Fan-out — 병렬화 가능한 작업을 sequential chain으로 만들지 않는다.
> **원칙 6.** 반복적·stateful한 사용자 흐름은 Handoffs — 단계와 precondition이 중요한 support/onboarding/approval flow에.
> **원칙 7.** 장기 독립 partition 작업은 Agent Teams — worker가 context를 축적해야 하는 대규모 migration/batch에.
> **원칙 8.** agents가 서로의 findings를 실시간 활용하면 Shared State — 단, duplicate work·conflict·termination condition을 반드시 설계한다.

워크플로 제어는 "무엇을, 어떻게 이어붙이나"의 문제다. Anthropic의 [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)가 정리한 패턴들이 여기 그대로 대응한다 — **Routing**(입력 분류 후 전문 경로로), **Parallelization**(독립 작업 분할/투표), **Orchestrator-Workers**(중앙 LLM이 하위작업을 동적 분해·종합). 원칙 4의 Router/Fan-out이 정확히 이것이다.

원칙 8의 단서가 실전의 핵심이다: Shared State는 강력하지만 **중복 작업·충돌·종료 조건**을 설계하지 않으면 재앙이 된다. Anthropic도 "모든 에이전트가 같은 컨텍스트를 공유해야 하는" 작업엔 멀티에이전트가 부적합하다고 경고한다 — 공유는 조율 비용을 부른다.

---

## 축 3. Latency를 운영한다

> **원칙 5.** 오래 걸리는 일은 Async SubAgent로 critical path 밖으로 뺀다 — user-visible latency를 줄이고 background task state를 message history와 분리한다.
> **원칙 10.** Prompt caching은 설계 초기에 고정한다 — static prefix, stable tools, deferred loading, cache-safe compaction을 *architecture constraint* 로.
> **원칙 11.** 모든 workflow에는 latency budget이 있어야 한다 — max critical path calls, timeout, quorum, partial result, async 허용 여부를 명시한다.

지연은 "나중에 최적화"가 아니라 **설계 제약**이다. 특히 원칙 10 — prompt caching은 나중에 붙이는 게 아니라 아키텍처를 정할 때 *고정*해야 한다. static prefix와 stable tools를 흔들면 캐시가 깨지고 비용이 폭증한다. (캐시 가능 구조는 [Ouroboros가 Seed를 불변으로 두는 것](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)과 통한다 — 앞부분이 고정돼야 뒷부분을 싸게 굴린다.)

원칙 11의 latency budget은 [어제 정리한 Ouroboros의 "모든 루프에 예산"](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) 원칙의 멀티에이전트 버전이다 — max calls·timeout·quorum·partial result를 *미리 숫자로* 정해두지 않으면, 멀티에이전트는 토큰 소각로가 된다(위의 15배를 기억하라).

---

## 축 4. 품질을 운영한다

> **원칙 9.** 품질이 중요한 결과에는 Generator-Verifier를 넣는다 — verifier는 rubric, source of truth, max iteration, escalation policy를 가져야 한다.
> **원칙 13.** Observability와 Eval 없이 production으로 가지 않는다 — trace, latency, token, cache hit, verifier result, rework rate를 측정한다.

원칙 9의 Generator-Verifier는 Anthropic이 말하는 **Evaluator-Optimizer** 패턴(한 모델이 생성하고 다른 모델이 피드백하는 반복 정제)과 동일하다. 그리고 [Ouroboros의 3단계 평가 게이트](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) — verifier가 rubric과 max iteration, escalation을 갖춰야 한다는 요구 — 와 정확히 겹친다. verifier가 기준 없이 "좋아 보임"만 내면 그건 검증이 아니다.

원칙 13은 협상 대상이 아니다. Anthropic 역시 못 박는다 — *"좋은 평가는 신뢰할 수 있는 AI 애플리케이션의 필수 요소"*, 그리고 *"전체 프로덕션 트레이싱을 붙이자 에이전트가 왜 실패했는지 진단하고 체계적으로 고칠 수 있었다."* 비결정적 시스템은 측정 없이는 디버깅 불가능하다. (무엇을 어떻게 측정하냐는 [LLM 관측 3대장 글](/2026/07/23/llm-observability-langfuse-langsmith-arize/)에서 다뤘다.)

---

## 한 줄 결론

멀티에이전트 설계는 **"에이전트를 몇 개 둘까"가 아니라 "컨텍스트를 어떻게 쪼개고, 워크플로를 어떻게 잇고, 지연을 어떻게 예산화하고, 품질을 어떻게 검증할까"** 다. 13가지 원칙은 그 네 축의 체크리스트이고, Anthropic의 공식 데이터(15배 토큰·80% 분산)는 그 첫 번째 관문 — *단일 에이전트로 되면 단일 에이전트로* — 이 왜 가장 중요한지를 숫자로 증명한다. 아키텍처가 조율 비용을 벌어들일 때만 멀티에이전트로 간다.

---

## 출처

- 첨부 이미지 2장: 사용자 제공(멀티에이전트 설계 원칙 13가지).
- Anthropic, **Building Effective Agents** (공식) — 단순함 우선, workflow 패턴(routing·parallelization·orchestrator-workers·evaluator-optimizer): <https://www.anthropic.com/engineering/building-effective-agents>
- Anthropic, **How we built our multi-agent research system** (공식) — 오케스트레이터-워커, 서브에이전트 컨텍스트 격리, "토큰 사용량이 분산의 80% 설명", "멀티에이전트 ~15배 토큰", "단일 에이전트 대비 90.2% 향상", 프로덕션 트레이싱: <https://www.anthropic.com/engineering/multi-agent-research-system>
- 관련 본인 정리글: [Ouroboros 3부작](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) · [LLM 관측 3대장](/2026/07/23/llm-observability-langfuse-langsmith-arize/)

> 참고: 13원칙 프레임은 이미지 제공자의 종합이며, 본문은 그 각 원칙을 Anthropic 공식 자료의 패턴·수치로 근거를 대는 방식으로 정리했다. 인용 수치는 Anthropic 공식 게시물 기준이다.
