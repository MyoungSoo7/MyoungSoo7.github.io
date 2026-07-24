---
layout: post
title: "두 하네스, 두 무게중심 — Gajae-Code의 하네스 요소 vs Claude Code Ouroboros 비교분석"
date: 2026-07-24 10:30:00 +0900
categories: [AI, Architecture]
tags: [gajae-code, ouroboros, harness-engineering, mcp, spec-first, multi-agent, measure-drift, agent-os, session, verification]
---

# 같은 '하네스'라는 단어, 전혀 다른 무게중심

AI 에이전트 하네스(harness)를 두 개 나란히 놓고 뜯어보면, 겉으로는 비슷한 부품 목록을 갖고 있어도 **무게중심이 어디에 있느냐**에서 갈립니다. 오늘 비교할 두 시스템이 딱 그렇습니다.

한쪽은 **Gajae-Code(gjc)** — 세션·모델·툴 런타임을 스스로 소유하는 **자족형 코딩 에이전트 하네스**. 다른 한쪽은 이 블로그에서 여러 번 다룬 **Ouroboros** — 스펙 우선(spec-first) 재귀 개선 에이전트 OS를 MCP 서버로 노출해, 실행은 외부 에이전트에게 위임하고 자신은 **측정과 계보에 집중하는 오케스트레이터**입니다.

Gajae-Code의 하네스 요소를 정리한 표를 먼저 보시죠.

![Gajae-Code 하네스 요소 표 — 실행 진입점(gjc CLI/launch/session mode), agent session(AgentSession·SessionManager), model 선택(ModelRegistry·packages/ai), tool boundary(ToolSession·createTools·MCP tools), workflow gate(deep-interview·ralplan·ultragoal·team), 지속 상태(.gjc/ workflow state·plan·goal·ledger), multi-agent 실행(role agent·AsyncJobManager·runSubprocess), 사용자/외부 제어(TUI·RPC·ACP·bridge·coordinator MCP), 검증 가능성(tool result·artifact·completion delivery)](/assets/images/gajae-code-harness-elements.jpg)

재미있는 건, **이 9개 요소 하나하나에 Ouroboros도 정확히 대응하는 부품을 갖고 있다**는 점입니다. 부품 목록은 겹치는데, 그 부품을 **어디에 놓았느냐**가 두 시스템의 철학을 가릅니다. 요소별로 겹쳐 읽어보겠습니다.

> 배경 글: [Ouroboros MCP 아키텍처 두 다이어그램 비교]({% post_url 2026-07-22-ouroboros-two-architecture-diagrams-compared %}) · [하네스의 주축을 고르다 — 왜 Ouroboros인가]({% post_url 2026-07-22-ouroboros-harness-main-axis %})

---

## 1. 실행 소유권 — "안에 품는가, 밖에 위임하는가"

표의 위쪽 네 줄(실행 진입점·agent session·model 선택·tool boundary)은 사실 하나의 질문으로 묶입니다. **에이전트 런타임을 하네스가 직접 소유하는가?**

**Gajae-Code — 소유한다.**
- 진입점 `gjc` CLI(launch/session mode)로 들어가면
- `AgentSession` / `SessionManager`가 세션 수명을 직접 쥐고
- `ModelRegistry` + `packages/ai` provider layer가 **모델 선택을 하네스 내부에서** 담당하며
- `ToolSession` / `createTools()`가 built-in·custom·MCP 도구 경계를 in-process로 관리합니다.

즉 Gajae-Code는 **모델과 도구 런타임이 하네스 몸통 안에** 있습니다. Claude Code나 Codex 같은 "완결형 코딩 에이전트"의 전형적 구조죠.

**Ouroboros — 위임한다.**
Ouroboros에는 `ModelRegistry`에 대응하는 자기 모델 계층이 **없습니다.** 대신 `OrchestratorRunner`가 **Agent Runtime Backend(Claude / Codex / OpenCode / Hermes / Gemini / Kiro / Copilot)** 를 골라 자식 에이전트로 spawn하고, 그 자식이 다시 MCP로 붙어 실제 파일·셸·코드를 건드립니다. 진입도 `gjc`처럼 자체 CLI가 아니라 `ooo auto "goal"` → Skill Dispatcher가 `SKILL.md` frontmatter의 `mcp_tool + mcp_args`를 꺼내 → **FastMCP 클라이언트(stdio JSON-RPC)** 로 서버에 닿는 구조입니다.

도구 경계도 위치가 다릅니다. Gajae는 `createTools()`가 프로세스 안에서 도구를 만든다면, Ouroboros는 `MCPServerAdapter.call_tool()` → **SecurityLayer(auth·rate-limit·validate) → IOJournalRecorder → ToolRegistry(25+ handlers)** 라는 거버넌스 파이프라인을 통과시키고, `MCPToolProvider`가 내장 도구와 외부 MCP 도구를 병합합니다.

> **정리:** Gajae-Code는 런타임을 *몸 안에 품는 목적지(destination)*, Ouroboros는 런타임을 *밖에 두고 조율하는 계층(layer)*. 이 한 줄이 나머지 차이를 전부 파생시킵니다.

---

## 2. 워크플로 게이트 — 같은 어휘, 다른 배치

표의 workflow gate 칸이 특히 눈에 띕니다: **`deep-interview`, `ralplan`, `ultragoal`, `team`.** 이 이름들은 oh-my-claudecode(OMC) 스킬 패밀리의 어휘와 그대로 겹칩니다. Gajae-Code가 OMC 계열의 워크플로 문법을 **코딩 에이전트 하네스 안에 모드로 내장**했다고 읽힙니다.

Ouroboros도 같은 개념의 게이트를 갖고 있는데, **배치가 다릅니다.**

| 개념 | Gajae-Code | Ouroboros |
|---|---|---|
| 요구사항 크리스탈라이즈 | `deep-interview` | `interview` / `pm_interview` |
| 계획 게이팅 | `ralplan` | `generate_seed`(불변 스펙으로 굳힘) |
| 목표 지속 실행 | `ultragoal` | `auto` + seed goal + `ralph` 루프 |
| 멀티에이전트 편성 | `team` | `OrchestratorRunner` + `JobManager` |

핵심 차이는 이렇습니다. Gajae-Code에서 이 게이트들은 **각각 독립된 CLI 모드**로 존재합니다. 필요할 때 골라 켜는 스위치죠. 반면 Ouroboros는 이것들을 **하나의 재귀 루프로 꿰맵니다**: `interview → 불변 seed → execute → evolve_step(Wonder+Reflect) → measure_drift → lineage`. 즉 Gajae는 게이트를 *병렬 메뉴*로, Ouroboros는 게이트를 *직렬 파이프라인*으로 둡니다. 자기 꼬리를 무는 뱀(Ouroboros)이라는 이름 그대로요.

---

## 3. 지속 상태 — 문서 상태 vs 이벤트 소싱

- **Gajae-Code:** `.gjc/` 아래에 **workflow state · plan · goal · ledger**를 둡니다. 프로젝트 로컬 디렉터리에 상태 파일을 쌓는, 읽기 쉬운 **문서 상태(document-state)** 모델입니다.
- **Ouroboros:** SQLite 기반 **EventStore(`~/.ouroboros/ouroboros.db`)** + `BrownfieldStore`. 여기에 **불변 seed(스펙)** 와 **lineage(계보)** 가 얹힙니다. 상태를 파일로 '덮어쓰는' 게 아니라 이벤트로 '쌓는' **이벤트 소싱(event-sourced)** 모델이죠.

이 차이는 실전에서 두 갈래로 벌어집니다. `.gjc/`의 ledger는 사람이 열어 바로 읽기 좋고 git으로 관리하기 편합니다. 반대로 Ouroboros의 이벤트 스토어는 **replay·감사·드리프트 추적**에 강합니다 — "이 개선(evolve_step)이 진짜 개선이었나"를 계보를 거슬러 물을 수 있으니까요. 사람 친화적 가독성 vs 기계 친화적 재현성의 트레이드오프입니다.

---

## 4. 멀티에이전트 실행 — 서브프로세스 vs 백엔드 어댑터

- **Gajae-Code:** `role agent` + `AsyncJobManager` + `runSubprocess()`. **역할을 가진 에이전트를 비동기 잡으로 띄우고 서브프로세스로 실행**합니다. 병렬성이 하네스 내부의 잡 매니저에 의해 관리됩니다.
- **Ouroboros:** `OrchestratorRunner`가 자식 에이전트(claude/codex/opencode)를 spawn → 그 자식이 다시 MCP로 재접속. 여기에 `MCPBridge`(server-to-server)가 외부 MCP 서버를 `tool_prefix`로 병합하고, OpenCode에서는 플러그인 훅(`_subagent` JSON → task panes)으로도 붙습니다.

둘 다 멀티에이전트를 하지만, Gajae는 **자기 프로세스 트리 안에서**(runSubprocess), Ouroboros는 **여러 호스트/백엔드를 갈아끼우며**(Agent Runtime Backend + MCPBridge) 확장합니다. Gajae의 멀티에이전트가 *수직적*(내가 자식을 낳는다)이라면, Ouroboros는 *수평적*(어느 CLI든 실행 어댑터로 꽂는다)입니다.

---

## 5. 사용자/외부 제어 — 목적지의 UI vs 계층의 프로토콜

- **Gajae-Code:** `TUI` · `RPC` · `ACP` · `bridge` · `coordinator MCP`. 자체 TUI라는 **사람이 앉는 자리**를 갖고, RPC/ACP로 에디터·외부와 연결하며, coordinator MCP로 조율합니다. 완결형 하네스답게 **자기만의 조종석**이 있습니다.
- **Ouroboros:** 자체 조종석 대신 **MCP 서버라는 표준 표면**으로 존재합니다. Claude Code·Codex·OpenCode·Hermes 등 **여러 호스트를 동시에 상대**하고, `ac_dashboard` / `ac_tree_hud`(HUD)와 `ControlBus` · `query_events`로 관측·제어를 노출합니다.

Gajae-Code는 ACP·coordinator MCP를 갖췄으니 **그 자체가 MCP 참여자**가 될 수 있습니다. 반대로 Ouroboros는 호스트에 얹히는 걸 전제로 설계됐습니다. 그래서 흥미로운 가능성이 생깁니다 — 뒤에서 다룹니다.

---

## 6. 검증 가능성 — 가장 날카로운 철학 차이

표의 마지막 줄(검증 가능성)은 **tool result · artifact · completion delivery**로 정리돼 있습니다. Gajae-Code의 검증은 **출력 중심(output verification)** 입니다: 도구가 뭘 냈고, 어떤 아티팩트가 나왔고, 완료가 전달됐는가.

Ouroboros의 검증은 결이 다릅니다. **스펙 준수 중심(spec-conformance verification)** 입니다.

- **`SpecVerifier` / `AssertionExtractor`** — seed에서 검증 가능한 단언을 추출해 결과를 대조.
- **`measure_drift`** — 결과가 불변 seed에서 얼마나 벗어났는지를 **수치로** 잰다. 드리프트를 은근히 만드는 게 아니라 **1급 관측 지표**로 올린다.
- **TraceGuard / evidence-gate** — 부모의 종합(synthesis)이 자식이 만든 증거 없이는 주장하지 못하도록 **결정론적으로** 강제. 멀티에이전트에서 "그럴듯하지만 근거 없는" 결과가 위로 새는 걸 막는다.
- **EvaluationPipeline(3-stage)** — 평가를 단계화.

이게 두 하네스의 가장 큰 갈림입니다. **Gajae-Code는 "무엇이 나왔나"를 검증하고, Ouroboros는 "얼마나 스펙대로였나"를 측정합니다.** 완료 전달(completion delivery)과 드리프트 측정(measure_drift)은 검증의 층위가 다릅니다. 전자는 결과물의 존재를, 후자는 결과물과 원래 의도 사이의 거리를 봅니다.

---

## 7. 두 무게중심, 그리고 뜻밖의 상보성

9개 요소를 겹쳐 읽고 나면 그림이 선명해집니다.

| 하네스 요소 | Gajae-Code | Ouroboros |
|---|---|---|
| 실행 진입점 | `gjc` CLI (launch/session) | `ooo auto` → Skill Dispatcher → FastMCP |
| agent session | `AgentSession`·`SessionManager` | EventStore 세션(`session_id` 저널) |
| model 선택 | `ModelRegistry`·`packages/ai` (**소유**) | OrchestratorRunner → 백엔드 에이전트 (**위임**) |
| tool boundary | `ToolSession`·`createTools()` | MCPServerAdapter→Security→Journal→ToolRegistry |
| workflow gate | deep-interview·ralplan·ultragoal·team (모드) | interview→seed→ralph→evolve (루프) |
| 지속 상태 | `.gjc/` 파일(plan·goal·ledger) | EventStore+seed+lineage (이벤트 소싱) |
| multi-agent | role agent·AsyncJobManager·runSubprocess | OrchestratorRunner·MCPBridge (백엔드 어댑터) |
| 사용자/외부 제어 | TUI·RPC·ACP·coordinator MCP (자체 조종석) | MCP 서버·HUD·ControlBus (표준 표면) |
| 검증 가능성 | tool result·artifact·completion (출력) | measure_drift·TraceGuard·SpecVerifier (스펙) |

**무게중심이 다릅니다.**

- **Gajae-Code의 중심은 '세션과 도구 경계'** 입니다. 모델·도구·멀티에이전트를 전부 몸 안에 품은 **자족형 코딩 에이전트 하네스** — 그 자체가 앉아서 일하는 목적지입니다.
- **Ouroboros의 중심은 '스펙과 측정'** 입니다. 실행은 밖에 위임하고, 자신은 불변 seed·드리프트 측정·계보에 집중하는 **호스트 독립 오케스트레이터** — 어느 하네스 위에도 얹히는 계층입니다.

그래서 이 둘은 경쟁 관계가 아니라 **상보 관계**일 수 있습니다. Gajae-Code는 ACP·coordinator MCP를 갖춘 완결형 실행 하네스이니, **Ouroboros의 OrchestratorRunner가 고르는 "Agent Runtime Backend"의 하나로 Gajae-Code를 꽂을 수 있습니다.** 스펙을 굳히고 드리프트를 재는 일은 Ouroboros가, 실제 코딩 실행은 Gajae-Code가 맡는 조합이죠. 이건 예전 글에서 정리한 **"주축 하나(측정하는 Ouroboros) + 부품 몇 개(실행하는 하네스)"** 구도와 정확히 맞물립니다.

---

## 한 줄 요약

**Gajae-Code는 런타임을 몸 안에 품어 "무엇이 나왔나"를 검증하는 자족형 코딩 하네스이고, Ouroboros는 실행을 밖에 위임하고 "얼마나 스펙대로였나"를 측정하는 호스트 독립 오케스트레이터다.** 부품 목록은 9개 다 겹치지만, Gajae는 그것들을 *목적지의 조종석*에, Ouroboros는 *계층의 표준 표면*에 놓는다. 그리고 가장 좋은 그림은 둘 중 하나를 고르는 게 아니라 — **재는 Ouroboros 위에서 실행하는 Gajae-Code를 돌리는 것**일지도 모른다.
