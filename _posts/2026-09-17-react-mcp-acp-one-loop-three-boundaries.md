---
layout: post
title: "ReAct · MCP · ACP — 2022년 논문이 남긴 빈칸을 두 프로토콜이 채웠다"
date: 2026-09-17 21:22:50 +0900
categories: [AI, Agent, Protocol]
tags: [ReAct, MCP, ACP, Agent, LLM, JSON-RPC]
---

셋을 나란히 놓고 "무엇이 더 낫냐"를 묻는 글이 많다. 잘못된 질문이다. **ReAct는 프로토콜이 아니다.** 2022년 논문이고, 에이전트가 *생각하는 순서*를 정한 프롬프트 패러다임이다. MCP와 ACP는 그 순서를 *선 위에 올리는* 규격이다.

그래서 이 글은 비교표가 아니라 **계보**로 쓴다. ReAct가 무엇을 정의했고, 무엇을 **빈칸으로 남겼고**, 2026년의 두 프로토콜이 그 빈칸 중 어디를 채웠는지. 마지막 하나는 아직 아무도 못 채웠다는 것까지.

---

## 1. ReAct가 실제로 정의한 것 (그리고 하지 않은 것)

ReAct 는 Yao 등이 2022년 10월에 낸 논문 *ReAct: Synergizing Reasoning and Acting in Language Models* 다. ICLR 2023 에 상위 5% 로 채택됐다.[^react][^react-page][^iclr]

핵심 주장은 한 문장이다. 그때까지 **추론**(chain-of-thought)과 **행동**(action plan generation)은 따로 연구되고 있었는데, 이 둘을 *번갈아 생성*(interleaved manner)하게 하면 서로를 보강한다는 것이다.[^react]

> reasoning traces help the model induce, track, and update action plans as well as handle exceptions, while actions allow it to interface with and gather additional information from external sources such as knowledge bases or environments.

논문의 표현을 그대로 옮기면 궤적은 **thought-action-observation** 스텝의 연쇄다.[^react] 우리가 지금 "에이전트 루프"라고 부르는 그것이다.

수치도 분명하다. HotpotQA 에서 CoT 의 false positive(환각) 비율이 14% 인데 ReAct 는 6% 였고, CoT 실패의 56% 가 환각이었다. 외부 지식에 실제로 접근했기 때문이다.[^react] ALFWorld·WebShop 에서는 1~2-shot 프롬프트만으로 imitation/RL 기반 방법을 절대 성공률 기준 각각 34%p, 10%p 앞섰다.[^react]

**여기서 중요한 건 논문이 하지 않은 일이다.**

ReAct 의 action space 는 논문이 직접 손으로 만든 **동사 세 개**였다.[^react]

```
search[entity]   → 해당 위키 문서의 첫 5문장, 없으면 유사 엔티티 top-5
lookup[string]   → 그 문자열이 포함된 다음 문장 (브라우저 Ctrl+F 흉내)
finish[answer]   → 답을 내고 종료
```

논문도 이게 약하다는 걸 안다. "state-of-the-art 렉시컬·뉴럴 리트리버보다 현저히 약하다"고 스스로 적었다.[^react] 목적이 성능이 아니라 *사람이 위키를 쓰는 방식의 시뮬레이션*이었기 때문이다.

즉 ReAct 는 **루프의 모양**을 정의했지 **루프가 무엇에 손댈 수 있는지**는 정의하지 않았다. 도구 목록은 프롬프트 안에 사람이 타이핑해 넣는 것이었다. 전송 규격도, 발견(discovery) 규약도, 권한 모델도 없다. 그건 논문의 결함이 아니라 **범위**다.

그 빈칸이 셋이다.

1. **Action 을 어떻게 실어 나르나** — 도구가 세 개가 아니라 삼백 개일 때.
2. **Observation 이 컨텍스트를 태우는 문제** — 논문이 결론에서 직접 지적한 한계다.
3. **Thought 를 사람에게 어떻게 보여주나** — 논문이 자기 장점이라 주장한 바로 그것.

---

## 2. 빈칸 ①②: MCP — Action/Observation 의 전송 규격

MCP(Model Context Protocol)는 에이전트와 **도구·데이터** 사이의 경계를 표준화한다. ReAct 궤적으로 번역하면 이렇다.

| ReAct 논문의 요소 | MCP 의 대응물 |
| --- | --- |
| action space (손으로 쓴 동사 3개) | `tools/list` — 서버가 런타임에 광고 |
| `search[entity]` 실행 | `tools/call` |
| Observation | tool call 의 결과 |
| "어떤 환경에 붙었나" | `server/discover` |

`server/discover` 는 2026-07-28 개정에서 **신설되었고 구현이 필수(MUST)** 다. 서버가 지원 프로토콜 버전·capability·신원을 이 RPC 로 광고한다.[^mcp-chg] 2022년에 프롬프트 상수였던 action space 가 2026년에는 **서버가 런타임에 대답하는 값**이 됐다. 이게 ①의 답이다.

### 논문이 남긴 한계가 그대로 스펙에 박혀 있다

ReAct 논문 결론의 마지막 문단은 이렇다.[^react]

> complex tasks with large action spaces require more demonstrations to learn well, which unfortunately can easily go beyond the input length limit of in-context learning.

**행동 공간이 커지면 인컨텍스트 학습의 입력 길이 한계를 넘는다.** 2022년에 적힌 문장인데, 4년 뒤 MCP 2026-07-28 개정의 minor change 목록에 이렇게 대응물이 나타난다.[^mcp-chg]

> Servers SHOULD return tools from `tools/list` in a **deterministic order** to enable client-side caching and improve **LLM prompt cache hit rates**.

그리고 `tools/list`·`prompts/list`·`resources/list`·`resources/read` 결과에 `ttlMs`(신선도 힌트)와 `cacheScope`(`"public"` / `"private"`)가 **필수**로 붙는다(`CacheableResult`).[^mcp-chg]

프로토콜 스펙이 *LLM 프롬프트 캐시 히트율*을 SHOULD 의 근거로 명시한다는 건 꽤 드문 일이다. 이건 순수한 전송 계층 관심사가 아니라 **모델의 입력 예산 관심사**다. ReAct 가 한계로 적어둔 그 문제를, 프로토콜이 캐시로 눌러보고 있는 것이다. ②는 "해결"이 아니라 **관리**로 답이 나왔다.

### 그리고 MCP 는 상태를 버렸다

2026-07-28 개정의 가장 큰 변화는 이거다.[^mcp-chg]

- **프로토콜 레벨 세션과 `Mcp-Session-Id` 헤더 제거.** 리스트 엔드포인트가 연결마다 달라지지 않는다. 호출 간 상태가 필요하면 **서버가 발급한 핸들을 평범한 tool 인자로** 주고받는다 (SEP-2567).
- **`initialize` / `notifications/initialized` 핸드셰이크 제거 — "Make MCP stateless".** 모든 요청이 `_meta` 에 자기 프로토콜 버전과 클라이언트 capability 를 싣는다 (SEP-2575).

2025년 자료만 읽고 온 사람이 가장 크게 틀리는 지점이다. 이 얘기는 [예전 글](/2026/08/09/mcp-vs-rest-api-acp-harness/)에서 더 파고들었으니 여기서는 **왜 이 결정이 ReAct 와 맞물리는지**만 뒤에서 다시 본다.

---

## 3. 빈칸 ③: ACP — Thought 를 사람에게 보내는 규격

여기서 말하는 ACP 는 **Agent Client Protocol**, Zed 발(發)이고 에디터 ↔ 에이전트 경계를 표준화한다. 저장소 설명 한 줄이 전부를 말한다. *"A protocol for connecting any editor to any agent."*[^acp-repo] LSP 가 에디터와 언어 서버 사이에 한 일을, 에디터와 코딩 에이전트 사이에 하겠다는 것이다.

### `agent_thought_chunk` 라는 타입

ACP 스키마 v1 에서 에이전트가 클라이언트로 밀어내는 `session/update` 알림의 변종 목록을 뽑으면 이렇다.[^acp-schema]

```
user_message_chunk        agent_message_chunk      agent_thought_chunk
tool_call                 tool_call_update         plan
available_commands_update current_mode_update      config_option_update
session_info_update       usage_update
```

**`agent_thought_chunk` 가 `agent_message_chunk` 와 별개의 타입으로 존재한다.** 그리고 `tool_call` 이 또 별개다.

이게 ReAct 의 Thought / Action 구분이 **와이어 타입으로 승격된 순간**이다. 2022년에는 프롬프트 안에서 `Thought 1:` `Act 1:` 로 시작하는 텍스트 관례였던 것이, 2026년에는 에디터가 "생각은 흐리게, 툴 콜은 접히는 카드로" 렌더링할 수 있게 **판별 가능한 열거형**이 됐다.

논문이 자기 기여로 내세운 항목을 다시 보자.[^react]

> improved human interpretability and trustworthiness

- **interpretability** → `agent_thought_chunk` + `plan`. 궤적이 사람이 볼 수 있는 구조로 나간다.
- **trustworthiness** → `session/request_permission`. 스키마의 `PermissionOptionKind` 는 네 가지다 — `allow_once`, `allow_always`, `reject_once`, `reject_always`.[^acp-schema]

논문에서 "사람이 모델의 내부 지식과 외부 정보를 구분할 수 있다"는 *해석 가능성 주장*이, 프로토콜에서는 **행동 직전에 사람이 끼어드는 제어점**이 됐다. 주장이 통제로 바뀐 것이다.

### ACP 는 MCP 를 실어 나른다 (경쟁이 아니다)

ACP 스키마에는 `McpServer` 라는 타입이 있다. 설명이 이렇다.[^acp-schema]

> Configuration for connecting to an MCP (Model Context Protocol) server. MCP servers provide tools and context that the agent can use when processing prompts.

변종은 `McpServerStdio` / `McpServerHttp` / `McpServerSse` 이고, HTTP·SSE 는 에이전트의 `mcpCapabilities.http` / `.sse` 가 `true` 일 때만 쓸 수 있다(둘 다 기본값 `false`).[^acp-schema]

즉 **에디터가 에이전트에게 "이 MCP 서버들에 붙어라"고 지시하는 통로가 ACP 안에 규격으로 들어 있다.** 두 프로토콜은 같은 층에서 싸우는 게 아니라, 위층이 아래층의 설정을 전달한다.

같은 에이전트가 **동시에 두 모자**를 쓴다. 에디터에 대해서는 ACP **서버**, 도구에 대해서는 MCP **클라이언트**다.

```
  사람 ──▶ 에디터 ──[ACP]──▶ 에이전트 ──[MCP]──▶ 도구/데이터
            ▲                  │  │                  │
            └── agent_thought_chunk │                  │
                tool_call          └── ReAct 루프가    └── Observation
                request_permission     도는 곳
```

---

## 4. "ACP" 는 두 개다 — 하나는 이미 끝났다

검색하면 반드시 섞인다. 짚고 간다.

**(A) Agent Client Protocol** — Zed 발, 에디터 ↔ 에이전트. 위에서 다룬 것. 저장소 `agentclientprotocol/agent-client-protocol`, 현재도 활발하다(2026-09-15 기준 최근 push, 별 4.2k).[^acp-repo] 안정 **프로토콜** 버전은 `1` 이고, 스키마 아티팩트 디렉터리에 `v1` 과 `v2` 가 함께 있다 — **크레이트/스키마 버전과 와이어 프로토콜 버전을 혼동하면 안 된다.**[^acp-repo]

**(B) Agent Communication Protocol** — IBM Research / BeeAI 발, REST 기반의 에이전트 간 프로토콜. **이쪽은 끝났다.** IBM Research 프로젝트 페이지 최상단에 이렇게 붙어 있다.[^ibm-acp]

> IMPORTANT UPDATE - ACP is now part of A2A under the Linux Foundation!

2025년 8월 29일 Linux Foundation LF AI & Data 공지가 1차 출처다.[^lf-acp] IBM Research 는 2025년 3월 ACP 를 내놨고, 같은 달 BeeAI 프로젝트와 함께 Linux Foundation 에 기증했다. 한 달 뒤 Google 의 **A2A(Agent2Agent)** 가 등장했고, 결국 ACP 가 A2A 로 병합됐다. 공지문에 이렇게 적혀 있다.[^lf-acp]

> the ACP team will be winding down active development and will begin contributing its technology and expertise directly to A2A.

BeeAI 플랫폼 자체도 ACP 에서 A2A 로 옮겼다(`A2AServer` 어댑터 / `A2AAgent`).[^lf-acp] **새 프로젝트가 (B) 를 채택할 이유는 없다.** 2025년에 쓰인 "MCP vs A2A vs ACP" 비교글을 지금 읽으면 이 항목이 통째로 낡아 있다.

---

## 5. 왜 MCP 는 상태를 버렸고 ACP 는 세션을 들고 있나

두 프로토콜의 최신 결정이 정반대로 보인다.

| | 상태 | 근거 |
| --- | --- | --- |
| MCP (2026-07-28) | **무상태** — 핸드셰이크·세션 ID 제거 | [^mcp-chg] |
| ACP (v1) | **세션 있음** — `session/new` · `session/load` · `sessionId` | [^acp-overview] |

모순이 아니다. **ReAct 궤적이 어디에 사는지를 두 프로토콜이 같은 답으로 말하고 있는 것이다.**

ReAct 의 루프에서 상태란 곧 **궤적**이다. 지금까지의 Thought·Action·Observation 이 다음 토큰의 조건이 된다. 그 궤적은 누구 것인가?

- **도구의 것이 아니다.** 도구는 `search[entity]` 한 번을 처리할 뿐, 대화를 기억할 이유가 없다. → 그래서 MCP 는 세션을 버리고, 굳이 상태가 필요한 서버만 **서버가 발급한 핸들을 평범한 tool 인자로** 주고받게 했다.[^mcp-chg] 대신 MCP 서버는 로드밸런서 뒤에 그냥 여러 대 띄우면 되는 물건이 됐다.
- **에디터의 것도 아니다.** 에디터는 궤적을 *렌더링*할 뿐 소유하지 않는다. 그래서 ACP 는 `sessionId` 라는 **핸들**만 들고, 내용물은 에이전트에 둔다. 그러니 `session/load` 로 나중에 다시 붙을 수 있다.
- **궤적은 에이전트의 것이다.** 두 프로토콜 모두 그걸 자기가 들고 있지 않겠다고 선언한 것이다.

이게 세 이름을 한 문장으로 묶는다. **ReAct 는 궤적의 모양이고, MCP 는 궤적이 바깥에 닿는 방법이고, ACP 는 궤적이 사람에게 보이는 방법이다.**

---

## 6. 아직 아무도 못 채운 빈칸

ReAct 논문은 자기 실패 모드도 적어뒀다. HotpotQA 에서 성공·실패 사례를 사람이 직접 라벨링한 분석에 이런 항목이 있다.[^react]

> one frequent error pattern specific to ReAct, in which the model repetitively generates the previous thoughts and actions, and we categorize it as part of "reasoning error" as the model fails to reason about what the proper next action to take and **jump out of the loop**

**같은 생각과 같은 행동을 반복하며 루프에서 빠져나오지 못하는 것.** 2022년에 기록된 이 실패는 MCP 에도 ACP 에도 대응물이 없다. `tools/call` 을 열 번째 같은 인자로 부르는 걸 막는 규격은 없고, `agent_thought_chunk` 가 앞과 똑같아도 프로토콜은 아무 말도 하지 않는다.

그건 **하네스의 몫**으로 남아 있다. 반복 탐지, 스텝 상한, 예산 컷, 같은 실패의 재시도 금지 — 전부 프레임워크가 각자 자기 방식으로 한다. 프로토콜 두 개가 전송과 렌더링을 규격화하는 동안, 논문이 짚은 *가장 실질적인 실패*는 여전히 표준 밖에 있다.

에이전트를 직접 운영해 본 사람이라면 이게 어디서 아픈지 안다. 도구가 안 붙어서 죽는 일보다, **붙긴 붙었는데 같은 자리를 도는** 일이 훨씬 자주 돈을 태운다.

---

## 요약

| | ReAct | MCP | ACP (Agent Client Protocol) |
| --- | --- | --- | --- |
| 무엇인가 | 논문 / 프롬프트 패러다임 | 프로토콜 | 프로토콜 |
| 나온 때 | 2022-10 (ICLR 2023) | 현행 개정 2026-07-28 | 안정 프로토콜 버전 `1` |
| 표준화하는 것 | 루프의 **모양** (thought→action→observation) | 에이전트 ↔ 도구/데이터 | 에디터 ↔ 에이전트 |
| 에이전트의 역할 | — | 클라이언트 | 서버 |
| 상태 | 궤적 = 상태 그 자체 | **무상태** | 세션 핸들 |
| 대표 기표 | `search[entity]` | `tools/call`, `server/discover` | `agent_thought_chunk`, `session/request_permission` |

셋 중 무엇을 "고를" 일은 없다. ReAct 는 이미 당신 에이전트 안에서 돌고 있고, MCP 는 그 루프의 오른쪽 끝이고, ACP 는 왼쪽 끝이다. 고를 수 있는 건 **어느 끝을 규격에 맡기고 어느 끝을 직접 짤 것인가** 뿐이다. 그리고 터미널에서 도는 에이전트에게는 왼쪽 끝이 아예 없다 — MCP 만 있다.

---

## References

[^react]: Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. *ReAct: Synergizing Reasoning and Acting in Language Models.* arXiv:2210.03629v3. 본문 인용(action space 3종, thought-action-observation, 환각 14% vs 6%, 결론의 입력 길이 한계, 루프 탈출 실패 분석)은 모두 논문 본문에서 확인. <https://arxiv.org/abs/2210.03629>
[^react-page]: 저자 프로젝트 페이지. <https://react-lm.github.io/>
[^iclr]: ICLR 2023 Poster — "top 5% paper". <https://iclr.cc/virtual/2023/poster/11003>
[^mcp-chg]: Model Context Protocol, *Changelog for MCP specification revision 2026-07-28* (이전 개정 2025-11-25 대비). 세션/핸드셰이크 제거(SEP-2567·SEP-2575), `server/discover` 필수, `CacheableResult`(`ttlMs`·`cacheScope`), `tools/list` 결정적 순서 SHOULD 는 모두 이 문서에서 확인. <https://modelcontextprotocol.io/specification/2026-07-28/changelog>
[^acp-schema]: Agent Client Protocol, JSON Schema v1 (`schema/v1/schema.json`, `$defs` 170개). `SessionUpdate` 11개 변종, `McpServer`(Stdio/Http/Sse) 와 `McpCapabilities`, `PermissionOptionKind` 4종을 스키마에서 직접 확인. <https://github.com/agentclientprotocol/agent-client-protocol/blob/main/schema/v1/schema.json>
[^acp-repo]: 저장소 `agentclientprotocol/agent-client-protocol`, Apache-2.0. 설명·기본 브랜치·최근 push 시각은 GitHub API 로 확인. <https://github.com/agentclientprotocol/agent-client-protocol>
[^acp-overview]: Agent Client Protocol 공식 문서 — 프로토콜 개요 및 메시지 흐름(`initialize` → `session/new`·`session/load` → `session/prompt` → `session/update`). <https://agentclientprotocol.com/protocol/v1/overview>
[^ibm-acp]: IBM Research, *Agent Communication Protocol (ACP)* 프로젝트 페이지. 최상단 배너 "ACP is now part of A2A under the Linux Foundation!" <https://research.ibm.com/projects/agent-communication-protocol>
[^lf-acp]: LF AI & Data, *ACP joins forces with A2A under the Linux Foundation's LF AI & Data* (2025-08-29). <https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/>

> 한계 명시: 이 글의 "ReAct 의 빈칸을 MCP/ACP 가 채웠다"는 **인과 주장이 아니다.** 두 프로토콜 어느 쪽도 스펙에서 ReAct 논문을 근거로 인용하지 않는다. 여기서 대조한 것은 *논문이 명시한 한계·기여*와 *스펙이 명시한 설계 결정*이 같은 문제를 가리킨다는 구조적 대응이며, 양쪽 문구를 각각 1차 출처에서 확인한 범위까지다.
