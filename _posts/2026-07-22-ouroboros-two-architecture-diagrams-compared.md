---
layout: post
title: "같은 시스템, 다른 시선: Ouroboros MCP 아키텍처 다이어그램 두 장 비교 분석"
date: 2026-07-22 22:30:00 +0900
categories: [AI, Architecture]
tags: [Ouroboros, MCP, Architecture, Diagram, FastMCP, Harness, SpecFirst]
---

# 다이어그램은 '진실'이 아니라 '시점'이다

같은 시스템을 그린 아키텍처 다이어그램 두 장을 나란히 놓으면 재미있는 일이 벌어집니다. 두 그림이 **서로 다른 질문에 답하고 있다**는 게 보이거든요. 하나는 "요청 하나가 들어오면 내부에서 무슨 일이 벌어지나?"에 답하고, 다른 하나는 "이 시스템을 누가 어떻게 부르고, 결국 무엇을 건드리나?"에 답합니다.

오늘 비교할 두 장은 모두 **Ouroboros MCP** — 스펙 우선(spec-first) 재귀 개선 에이전트 OS를 MCP 서버로 노출한 시스템 — 의 구조도입니다. 같은 코드베이스인데 그리는 사람의 시선이 다릅니다. 이 차이를 뜯어보면 "좋은 아키텍처 다이어그램이란 무엇인가"에 대한 감각이 잡힙니다.

## 그림 A — 내부 계층을 세로로 관통하는 '요청의 여정'

![Ouroboros 상세 계층 다이어그램 — Discovery/Config, Claude Code MCP 진입, FastMCP Transport, MCPServerAdapter, SecurityLayer, IOJournalRecorder, ToolRegistry 25+ handlers, Composition Root, Persistence, OrchestratorRunner, MCPBridge](/assets/images/ouroboros/ouroboros-arch-detailed-layers.jpg)

첫 번째 그림은 **한 번의 도구 호출이 위에서 아래로 통과하는 파이프라인**을 그립니다. 위에서부터 따라가 보면:

1. **Discovery / Config** — `.mcp.json` / `.claude-plugin/mcp.json`, `~/ouroboros/mcp_servers.yaml`(`$OUROBOROS_MCP_CONFIG`). 호스트가 서버를 등록하는 지점.
2. **Claude Code / Desktop (MCP)** — 사용자가 `ooo auto "goal"`을 치면 → Skill Dispatcher가 `skills/auto/SKILL.md`를 읽고 → frontmatter의 `mcp_tool + mcp_args`를 꺼내 → ToolSearch(deferred tool load) → FastMCP Client(stdio JSON-RPC).
3. **Transport** — stdio(기본) / sse / streamable-http.
4. **MCPServerAdapter**(`mcp/server/adapter.py`)의 `call_tool()` 진입.
5. **SecurityLayer** — auth · rate-limit · validate.
6. **IOJournalRecorder** — `call_id / session_id` 단위로 입출력을 저널링.
7. **ToolRegistry** — 25개 넘는 핸들러.
8. **Composition Root** — InterviewEngine, SeedGenerator, EvolutionaryLoop(+Wonder+Reflect), EvaluationPipeline(3-stage), SpecVerifier/AssertionExtractor, JobManager, ControlBus.
9. **Persistence** — SQLite(+aiosqlite): EventStore(`~/.ouroboros/ouroboros.db`), BrownfieldStore.
10. **OrchestratorRunner** — claude/codex/opencode 자식 에이전트를 spawn → 그 자식이 다시 MCP로 연결.
11. **MCPBridge**(server-to-server) — External MCP A/B를 `tool_prefix` 주입으로 병합, 브리지가 자동 발견.

이 그림의 핵심 미덕은 **거버넌스 레이어를 숨기지 않는다**는 점입니다. `SecurityLayer → IOJournalRecorder → ToolRegistry` 순서가 명시돼 있어서, "모든 호출이 인증·레이트리밋·저널링을 거친 뒤에야 핸들러에 닿는다"는 안전/감사 스토리가 한눈에 읽힙니다. `MCP Resources`(`ouroboros://seeds/{id}`, `sessions/{id}`, `events/{id}`)까지 옆에 붙어 있어, 도구 호출뿐 아니라 **리소스 구독**이라는 MCP의 또 다른 축도 보여줍니다.

## 그림 B — 진입점과 백엔드를 가로로 펼친 '통합의 지도'

![Ouroboros 진입점·백엔드 다이어그램 — MCP 클라이언트 진입점(Claude Code/Codex CLI/OpenCode·Hermes·Gemini·Kiro·Copilot), uvx serve, create_ouroboros_server, MCP Tools, EventStore, OrchestratorRunner, Agent Runtime Backend, 외부 MCP Bridge, OpenCode plugin mode](/assets/images/ouroboros/ouroboros-arch-entrypoints-backends.jpg)

두 번째 그림은 시선을 90도 돌립니다. 세로로 관통하는 대신 **가로로 펼쳐서** "누가 부르고, 무엇으로 실행되고, 밖으로 무엇과 연결되나"를 그립니다.

- **진입점의 다양성** — `ooo` 또는 `/ouroboros:` → Skill Router(`SKILL.md` frontmatter의 `mcp_tool + mcp_args`) → **세 갈래 클라이언트**: Claude Code(`.mcp.json`), Codex CLI(`~/.codex/config.toml`), 그리고 OpenCode / Hermes / Gemini / Kiro / Copilot. 그림 A가 Claude 하나에 집중했다면, 여기선 **하나의 MCP 서버가 여러 호스트를 동시에 상대**하는 현실이 드러납니다.
- **기동 명령의 사슬** — `uvx --from ouroboros-ai[...] ouroboros mcp serve` → Typer command `ouroboros mcp serve` → `create_ouroboros_server()` 컴포지션 루트. 그림 A가 "이미 serve 중"인 서버 내부에서 시작했다면, 그림 B는 **어떻게 그 서버가 뜨는가**부터 그립니다.
- **실행 백엔드의 다형성** — OrchestratorRunner → Agent Runtime Backend(Claude / Codex / OpenCode / Hermes / Gemini / Kiro / Copilot) → **사용자 프로젝트(파일·셸·코드 변경)**. 즉 Ouroboros는 어느 CLI 에이전트든 갈아끼울 수 있는 실행 어댑터를 갖고 있습니다.
- **외부 MCP 브리지를 1급 시민으로** — `OUROBOROS_MCP_CONFIG`(`~/.ouroboros/mcp_servers.yaml`, `cwd/.ouroboros/mcp_servers.yaml`) → MCPBridge → MCPClientManager → 외부 MCP 서버들(filesystem / github / browser / db 등), 그리고 **MCPToolProvider가 내장 도구와 외부 MCP 도구를 병합**. 이 열이 통째로 그림 B의 오른쪽을 차지합니다.
- **OpenCode plugin mode(optional)** — 그림 A엔 아예 없는 경로. `_subagent / _subagents` JSON → `ouroboros-bridge.ts`의 `tool.execute.after` 훅 → OpenCode Task panes(병렬 자식 세션). MCP가 아니라 **플러그인 훅**으로 붙는 대안 통합입니다.

## 두 그림이 공유하는 '척추'

시선은 달라도 두 그림은 같은 등뼈를 공유합니다. 겹쳐보면 이렇게 정렬됩니다.

| 단계 | 그림 A(내부 계층) | 그림 B(진입·백엔드) |
|---|---|---|
| 진입 | Skill Dispatcher → mcp_tool+mcp_args | Skill Router → mcp_tool+mcp_args |
| 부트 | (serve 가정) | uvx → Typer → create_ouroboros_server() |
| 어댑터 | MCPServerAdapter + SecurityLayer + Journal | MCPServerAdapter + FastMCP |
| 도구 | ToolRegistry 25+ handlers | Ouroboros MCP Tools |
| 상태 | EventStore(`ouroboros.db`) + BrownfieldStore | EventStore + BrownfieldStore(`~/.ouroboros/data`) |
| 실행 | OrchestratorRunner → child agent | OrchestratorRunner → Agent Runtime Backend |
| 확장 | MCPBridge(server-to-server) | 외부 MCP Bridge + MCPToolProvider |

같은 도구 집합도 양쪽에 다 나옵니다 — `auto`, `interview`/`pm_interview`, `generate_seed`, `execute_seed`/`start_execute_seed`, `evolve_step`/`rewind`/`lineage`, `ralph`, `evaluate`/`measure_drift`, `session_status`/`query_events`/`ac_dashboard`/`ac_tree_hud`, `qa`/`lateral_think`/`brownfield`. 이 목록이 곧 Ouroboros의 정체성입니다: **인터뷰로 불변 스펙(seed)을 굳히고 → 실행하고 → evolve_step(Wonder+Reflect)으로 개선하고 → measure_drift로 이탈을 재고 → lineage로 계보를 추적**하는 재귀 루프. 이름 그대로 자기 꼬리를 무는 뱀(Ouroboros)입니다.

## 관점 차이가 만든 '드리프트'와 교훈

두 그림을 겹쳐보면 미세한 불일치도 잡힙니다 — 그림 A는 저장소를 `~/.ouroboros/ouroboros.db`로, 그림 B는 `~/.ouroboros/data`로 적었습니다. 어느 쪽이 최신인지는 코드가 답할 문제지만, **다이어그램이 서로 다른 스냅샷을 찍었다**는 신호입니다. 다이어그램은 코드가 아니라 코드에 대한 '주장'이라, 시간이 지나면 조용히 어긋납니다.

여기서 얻는 실전 교훈:

- **한 장으로 다 담으려 하지 마라.** 그림 A는 '요청의 세로 여정 + 거버넌스'를, 그림 B는 '통합의 가로 지도 + 진입/백엔드 다형성'을 맡습니다. 한 장에 우겨넣었다면 둘 다 흐려졌을 겁니다. 다이어그램은 **질문 단위로 나누는 게** 낫습니다.
- **거버넌스는 눈에 보여야 산다.** 그림 A의 `SecurityLayer → Journal` 계층은 그림 B에서 통째로 생략됐습니다. 진입/통합만 보는 사람에겐 안전·감사 레이어가 '없는 것'처럼 보입니다. 어떤 관점을 고르든 **빠진 축이 무엇인지**는 알고 있어야 합니다.
- **다이어그램 드리프트를 전제로 하라.** `ouroboros.db` vs `data` 같은 불일치는 정상입니다. 다이어그램은 '지금 이 순간의 이해'일 뿐, 단일 진실 소스(SSOT)는 코드입니다.

## 한 줄 요약

**같은 Ouroboros MCP인데, 그림 A는 "요청 하나가 내부를 어떻게 통과하는가(깊이)"를, 그림 B는 "누가 부르고 무엇으로 실행되며 밖으로 어떻게 뻗는가(넓이)"를 그린다.** 좋은 아키텍처 이해는 이 둘을 겹쳐 읽을 때 완성됩니다 — 깊이 없는 넓이는 안전을 놓치고, 넓이 없는 깊이는 통합을 놓치니까요.
