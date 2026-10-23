---
layout: post
title: "Codex · Claude Code · Cursor · Antigravity · Hermes 비교 — 기능은 수렴했고, 갈리는 건 '본체가 어디 있느냐' 다"
date: 2026-10-23 10:24:18 +0900
categories: [AI, Agents]
tags: [Codex, Claude Code, Cursor, Antigravity, Hermes Agent, MCP, AGENTS.md, Sandbox, Coding Agent]
---

[9월 28일 글]({% post_url 2026-09-28-hermes-kiro-claude-code-codex-collaboration-scenarios %})은 에이전트 넷을 **한 팀으로 묶는 법**을 다뤘다. 이번엔 다섯 개 — **OpenAI Codex, Anthropic Claude Code, Cursor, Google Antigravity, Nous Research Hermes Agent** — 를 **같은 기준으로 나란히** 놓는다.

모든 항목은 2026-10-23 에 각 벤더의 공식 문서·공식 GitHub 리포·공식 요금 페이지에서 확인했다. 이 분야는 몇 주 단위로 바뀌니 날짜를 기준으로 읽어 주면 좋겠다. **가격은 일부러 뺐다.** 요금제 이름과 과금 방식만 적는다.

먼저 결론. 다섯 개를 문서로 대조해 보면 **기능 목록은 놀랄 만큼 수렴했다.** MCP, 훅, 스킬, 서브에이전트, `AGENTS.md`, "LLM 이 위험도를 판정하는 중간 권한 모드" 까지 거의 다 있다. 진짜로 갈리는 건 세 가지다. **본체가 어디에 사는가(터미널·에디터·관제 앱·상주 서버), 어떤 모델에 묶이는가, 소스가 열려 있는가.**

## 1. 한 장 비교표

| | Codex | Claude Code | Cursor | Antigravity | Hermes Agent |
|---|---|---|---|---|---|
| **만든 곳** | OpenAI | Anthropic | Anysphere | Google | Nous Research |
| **본체** | 터미널 CLI | 터미널 CLI | 에디터(IDE) | 에이전트 관제 데스크톱 앱 | 상주 에이전트(TUI + 메신저 게이트웨이) |
| **다른 형태** | IDE 확장, 데스크톱 앱, 웹/클라우드, SDK, GitHub Action | IDE 확장, JetBrains, 데스크톱 앱, 웹·모바일, Agent SDK | CLI(`agent`), 클라우드 에이전트(웹·모바일·Slack·GitHub 등) | CLI(`agy`), 여러 IDE 확장, SDK | 서버(`hermes serve`), 데스크톱 앱 |
| **소스** | 오픈, Apache-2.0 | 비공개 | 비공개 | SDK 만 Apache-2.0 | 오픈, MIT |
| **모델** | OpenAI 기본 + Ollama·LM Studio·Responses API 호환 | Claude 전용 (여러 클라우드 경유) | 여러 벤더 + 자체 모델 | Gemini + Claude + GPT-OSS (요금제별) | 아무 공급자나 (로컬 포함) |
| **지시 파일** | `AGENTS.md` | `CLAUDE.md` (`AGENTS.md` 도 읽음) | `.cursor/rules`, `AGENTS.md` (CLI 는 `CLAUDE.md` 도) | `AGENTS.md` / `GEMINI.md`, `.agents/rules/` | (스킬·메모리 중심) |
| **MCP** | O | O | O | O | O |
| **훅** | O | O | O | O | — (확인 못 함) |
| **서브에이전트** | O | O | 병렬 에이전트(worktree) | 백그라운드 서브에이전트(worktree) | `delegate_task` |
| **헤드리스** | `codex exec` | `claude -p` | CLI | CLI | `hermes chat --oneshot` 등 |
| **과금** | ChatGPT 요금제 포함 또는 API 키 | Claude 구독(Pro 이상) 또는 API | 자체 요금제 | Google AI 요금제(무료 포함) | 무료 OSS + 본인 API 키 (선택: Nous Portal) |

아래에서 축별로 풀어 쓴다.

## 2. 본체가 어디에 사는가 — 다섯 개의 출발점

기능이 비슷해져도 **출발점**은 여전히 다르고, 이게 일하는 방식을 정한다.

- **Codex·Claude Code — 터미널에서 출발했다.** 둘 다 CLI 가 원형이고 IDE·데스크톱·웹은 거기서 뻗어 나갔다. Claude Code 문서는 "the terminal, IDE extensions, a desktop app, and the web" 에서 돈다고 적는다.[^cc-overview] Codex 도 CLI·IDE 확장·데스크톱 앱·웹·SDK·GitHub Action 을 갖췄다.[^codex-docs]
- **Cursor — 에디터에서 출발했다.** 사람이 코드를 보면서 에이전트와 같이 고치는 게 원형이다. 지금은 CLI 와, "isolated VMs in the cloud" 에서 도는 클라우드 에이전트까지 생겼다.[^cursor-cloud]
- **Antigravity — 에이전트 "관제" 에서 출발했다.** 문서는 앱을 "a standalone desktop application for launching, orchestrating, and inspecting autonomous agent teams" 라고 소개한다.[^ag-overview] 코드 편집기라기보다 여러 에이전트를 띄우고 결과물(artifact)을 검토하는 **관제실**에 가깝다. 에디터 쪽은 VS Code·JetBrains·Zed·Xcode 등의 확장으로 붙는다.[^ag-install]
- **Hermes — 코딩 도구가 아니라 상주 에이전트에서 출발했다.** README 가 스스로를 "The self-improving AI agent" 라 부르고, 단일 게이트웨이 프로세스로 Telegram·Discord·Slack·WhatsApp·Signal 등에서 대화한다. 내장 크론 스케줄러도 있다.[^hermes-readme] 코딩도 하지만, 본질은 **늘 켜져 있으면서 기억하고 스킬을 쌓는 비서**다.

그래서 "어느 게 제일 좋으냐" 보다 **"내 일의 중심이 터미널인가, 에디터인가, 여러 에이전트의 관제인가, 메신저인가"** 를 먼저 묻는 게 맞다.

## 3. 모델 종속성 — 한쪽 끝은 Claude 전용, 반대쪽 끝은 아무거나

다섯 개를 모델 자유도로 줄 세우면 이렇다.

1. **Claude Code — Claude 전용.** 경로는 여러 갈래다. Anthropic API, Claude 구독, Amazon Bedrock, Google Cloud, Microsoft Foundry 등을 거칠 수 있고 LLM 게이트웨이도 `ANTHROPIC_BASE_URL` 로 붙는다.[^cc-3p] 하지만 모델 자체는 Claude 다.
2. **Codex — OpenAI 기본, 로컬·호환 공급자 가능.** CLI 소스에 `--oss`("Use open-source provider")와 `--local-provider`(lmstudio 또는 ollama) 옵션이 있다. 커스텀 공급자는 **Responses API 호환** 엔드포인트여야 한다.[^codex-models]
3. **Antigravity — Google + 일부 타사.** 공식 모델 목록에 Gemini 계열과 함께 Claude Sonnet·Opus, GPT-OSS-120b 가 있다. 쓸 수 있는 모델은 요금제에 따라 다르다.[^ag-models]
4. **Cursor — 여러 벤더 + 자체 모델.** Anthropic·OpenAI·Google 등 여러 벤더 모델과 Cursor 자체 모델(Composer)을 고를 수 있다.[^cursor-docs] 다만 요금제에 따라 쓸 수 있는 모델과 과금 방식이 달라지니 공식 요금 페이지를 직접 확인해야 한다.[^cursor-pricing]
5. **Hermes — 아무 공급자나.** "Use any model you want — Nous Portal, OpenRouter, OpenAI, your own endpoint, and many others… no code changes, no lock-in."[^hermes-readme] Ollama·vLLM 같은 자체 호스팅도 된다.[^hermes-providers]

모델에 묶인 도구일수록 **그 모델에 맞춰 다듬은 경험**을 주고, 풀린 도구일수록 **바꿔 끼우는 자유**를 준다. 어느 쪽이 낫다기보다 트레이드오프다.

## 4. 소스 — 둘은 열려 있고, 셋은 닫혀 있다

- **Codex CLI** — Apache-2.0. Rust 로 쓰였다.[^codex-repo]
- **Hermes Agent** — MIT.[^hermes-readme]
- **Claude Code** — 공개 리포(`anthropics/claude-code`)는 있지만 LICENSE 는 "All rights reserved. Use is subject to Anthropic's Commercial Terms of Service." 다. 오픈소스가 아니다.[^cc-license]
- **Cursor** — 제품 소스는 공개되지 않았다. 공식 GitHub 의 `cursor/cursor` 는 이슈 트래커 용도다.
- **Antigravity** — Python SDK 만 Apache-2.0 이다. 앱·CLI 는 소스가 공개되어 있지 않다.

소스가 열려 있으면 **에이전트가 실제로 무엇을 하는지 직접 읽을 수 있다.** 위 표의 Codex 모델 옵션도 문서가 아니라 소스 파일에서 확인한 것이다. 보안 검토가 까다로운 조직이라면 이 차이가 작지 않다.

## 5. 수렴 ① — 지시 파일은 `AGENTS.md` 로 모이고 있다

에이전트에게 프로젝트 규칙을 알려 주는 파일 이름이 한때는 도구마다 달랐다. 지금은 `AGENTS.md` 가 사실상 공통어다.

- Codex 는 `AGENTS.md` 가 기본이고, 전역부터 현재 디렉터리까지 내려가며 읽는다.[^codex-agentsmd]
- Claude Code 는 `CLAUDE.md` 가 기본이지만 "If your repository already has an `AGENTS.md`… Claude Code can read that" 이라고 적는다.[^cc-headless]
- Cursor 는 `.cursor/rules` 와 함께 `AGENTS.md` 를 지원하고,[^cursor-rules] CLI 는 프로젝트 루트의 `CLAUDE.md` 도 읽는다.[^cursor-cli]
- Antigravity 는 `AGENTS.md` 또는 `GEMINI.md` 와 `.agents/rules/` 를 쓴다.[^ag-rules]

여러 도구를 섞어 쓴다면 **규칙은 `AGENTS.md` 한 곳에 쓰고**, 도구별 파일은 그걸 가리키거나 차이만 적는 게 가장 덜 어긋난다.

## 6. 수렴 ② — MCP·훅·스킬·서브에이전트

- **MCP** — 다섯 개 모두 지원한다. 설정 파일 위치만 다르다(Codex `config.toml`, Claude Code `.mcp.json`, Cursor `.cursor/mcp.json`, Antigravity `mcp_config.json`, Hermes `config.yaml` 의 `mcp_servers`).
- **훅** — Codex·Claude Code·Cursor·Antigravity 가 모두 도구 호출 전후(Pre/PostToolUse 계열)에 스크립트를 끼우는 훅을 문서화했다.[^codex-hooks][^cursor-hooks][^ag-hooks] Hermes 는 이번에 확인한 범위에서는 같은 형태의 훅을 찾지 못했다.
- **서브에이전트·병렬** — Codex 는 TOML 로 서브에이전트를 정의하고,[^codex-sub] Cursor 와 Antigravity 는 **Git worktree** 로 여러 에이전트를 같은 리포에서 충돌 없이 병렬로 돌린다.[^cursor-worktree][^ag-overview] Hermes 의 `delegate_task` 는 격리된 컨텍스트의 자식 에이전트를 띄우고 **최종 요약만** 부모에게 돌려준다.[^hermes-delegation]
- **스킬** — Hermes 가 가장 멀리 갔다. 복잡한 작업을 끝낸 뒤 **스스로 스킬을 만들고 쓰면서 고친다**("Autonomous skill creation after complex tasks. Skills self-improve during use").[^hermes-readme]

기능 체크리스트로 고르는 시대는 지났다는 뜻이다. 다 있다.

## 7. 수렴 ③ — 권한 모델의 "LLM 판정 중간 모드"

가장 흥미로운 수렴은 권한 모델이다. 다섯 개 중 넷이 **"전부 묻기" 와 "전부 허용" 사이에, 별도 모델이 위험도를 판정하는 모드**를 두었다.

| 도구 | 중간 모드 | 문서 표현 |
|---|---|---|
| Claude Code | `auto` | 백그라운드 분류기가 행동을 검사[^cc-perm] |
| Cursor | Auto-review (권장) | 허용 목록은 바로, 나머지 셸 명령은 가능하면 샌드박스에서, 그 밖은 LLM 분류기로[^cursor-runmodes] |
| Antigravity | Auto (Preview) | 샌드박스 밖 실행이 필요할 때 "safe, reversible commands run without prompting"[^ag-perm] |
| Hermes | `smart` (기본값) | 보조 LLM 이 위험도 판정: 낮으면 자동 승인, 위험하면 자동 거부, 애매하면 사람에게[^hermes-security] |

Codex 는 결이 조금 다르다. 승인 정책 `on-request` 는 "The model decides when to ask" — 별도 분류기가 아니라 **작업하는 모델 자신이** 물어볼 때를 정한다.[^codex-sandbox]

여기에 **OS 수준 샌드박스**가 받쳐 준다. Codex 와 Claude Code 는 macOS 에서 Seatbelt, Linux 에서 bubblewrap 을 쓴다.[^codex-sandbox][^cc-sandbox] Codex 는 네이티브 Windows 샌드박스도 있는 반면, Claude Code 문서는 네이티브 Windows 에선 명령이 샌드박스 없이 돈다고 적는다.[^cc-sandbox] Antigravity 는 기본·Auto 모드에서 터미널 명령을 **네트워크 없는** 격리 샌드박스에서 돌린다.[^ag-perm] Hermes 는 실행 백엔드를 local·Docker·SSH·Modal 등에서 고르는 방식이고, 사용자 승인이나 YOLO 모드로도 **풀 수 없는 하드코딩 차단 목록**을 따로 둔다.[^hermes-security]

정리하면, 다섯 다 "에이전트에게 얼마나 맡길까" 를 **사람의 클릭 대신 판정 모델 + 샌드박스**로 옮기는 중이다. 다만 판정 모델도 모델이다. 판정이 틀릴 때 피해를 줄이는 건 결국 샌드박스와 차단 목록 쪽이라는 걸 기억해 두자. (Antigravity 설정 화면을 하나씩 뜯어본 [이전 글]({% post_url 2026-09-27-antigravity-general-settings-explained %})도 같은 문제를 다뤘다.)

## 8. 무엇을 고를까 — 필자 의견

아래는 문서 대조를 바탕으로 한 **필자 의견**이다.

- **터미널·CI 중심, 모델은 하나로 충분** → Claude Code 또는 Codex. 헤드리스(`claude -p`, `codex exec`)가 1급 시민이다. 소스를 읽고 싶거나 로컬 모델을 섞고 싶으면 Codex.
- **사람이 코드를 보며 같이 고치는 게 중심** → Cursor. 에디터가 본체이고 모델 선택 폭이 넓다.
- **여러 에이전트를 동시에 띄우고 결과물로 검토** → Antigravity. 관제 앱과 artifact(계획서·diff·브라우저 녹화 등)가 중심이다.[^ag-artifacts]
- **늘 켜져서 메신저로 부르고, 기억하고, 스케줄로 도는 비서** → Hermes. 모델 종속도 없다.
- **섞어 쓴다면** → 규칙은 `AGENTS.md` 한 곳, 권한은 도구마다 샌드박스부터 켜고, 역할 분담은 [9월 28일 글]({% post_url 2026-09-28-hermes-kiro-claude-code-codex-collaboration-scenarios %})의 "넘겨주기는 말이 아니라 파일로" 원칙을 따른다.

## 한계

- 2026-10-23 시점 공식 문서 기준이다. 버전·모델 목록·요금제는 자주 바뀐다.
- 성능·품질 벤치마크는 다루지 않았다. 중립적인 동일 조건 비교 자료를 이번에 찾지 못했다.
- Cursor·Antigravity 의 편집기가 VS Code 계열인지는 공식 문서에서 확인하지 못해 적지 않았다.
- Hermes 의 훅 지원 여부는 확인 범위 밖이라 "확인 못 함" 으로 두었다.

## References

[^codex-docs]: OpenAI, Codex docs. <https://learn.chatgpt.com/docs>
[^codex-repo]: openai/codex (GitHub). <https://github.com/openai/codex>
[^codex-models]: OpenAI, Codex docs — Models. <https://learn.chatgpt.com/docs/models> ; CLI options `codex-rs/utils/cli/src/shared_options.rs` in openai/codex.
[^codex-agentsmd]: OpenAI, Codex docs — AGENTS.md. <https://learn.chatgpt.com/docs/agent-configuration/agents-md>
[^codex-hooks]: OpenAI, Codex docs — Hooks. <https://learn.chatgpt.com/docs/hooks>
[^codex-sub]: OpenAI, Codex docs — Subagents. <https://learn.chatgpt.com/docs/agent-configuration/subagents>
[^codex-sandbox]: OpenAI, Codex docs — Sandboxing. <https://learn.chatgpt.com/docs/sandboxing>
[^cc-overview]: Anthropic, Claude Code docs — Overview. <https://code.claude.com/docs/en/overview>
[^cc-3p]: Anthropic, Claude Code docs — Third-party integrations. <https://code.claude.com/docs/en/third-party-integrations>
[^cc-license]: anthropics/claude-code, LICENSE.md. <https://github.com/anthropics/claude-code/blob/main/LICENSE.md>
[^cc-headless]: Anthropic, Claude Code docs — Headless mode. <https://code.claude.com/docs/en/headless>
[^cc-perm]: Anthropic, Claude Code docs — Permissions. <https://code.claude.com/docs/en/permissions>
[^cc-sandbox]: Anthropic, Claude Code docs — Sandboxing. <https://code.claude.com/docs/en/sandboxing>
[^cursor-docs]: Cursor docs. <https://cursor.com/docs>
[^cursor-pricing]: Cursor, Pricing. <https://cursor.com/pricing>
[^cursor-cloud]: Cursor docs — Cloud Agents. <https://cursor.com/docs/cloud-agent>
[^cursor-rules]: Cursor docs — Rules. <https://cursor.com/docs/context/rules>
[^cursor-cli]: Cursor docs — Using the CLI. <https://cursor.com/docs/cli/using>
[^cursor-hooks]: Cursor docs — Hooks. <https://cursor.com/docs/agent/hooks>
[^cursor-worktree]: Cursor docs — Worktrees. <https://cursor.com/docs/configuration/worktrees>
[^cursor-runmodes]: Cursor docs — Run Modes. <https://cursor.com/docs/agent/security/run-modes>
[^ag-overview]: Google, Antigravity docs — Overview. <https://antigravity.google/docs/overview/>
[^ag-install]: Google, Antigravity docs — Install. <https://antigravity.google/docs/install/>
[^ag-models]: Google, Antigravity docs — Models. <https://antigravity.google/docs/models/>
[^ag-rules]: Google, Antigravity docs — Rules. <https://antigravity.google/docs/rules/>
[^ag-hooks]: Google, Antigravity docs — Hooks. <https://antigravity.google/docs/hooks/>
[^ag-perm]: Google, Antigravity docs — Permissions. <https://antigravity.google/docs/permissions/>
[^ag-artifacts]: Google, Antigravity docs — Artifacts. <https://antigravity.google/docs/artifacts/>
[^hermes-readme]: NousResearch/hermes-agent, README. <https://github.com/NousResearch/hermes-agent>
[^hermes-providers]: Hermes Agent docs — Providers. <https://hermes-agent.nousresearch.com/docs/integrations/providers>
[^hermes-delegation]: Hermes Agent docs — Delegation. <https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation>
[^hermes-security]: Hermes Agent docs — Security. <https://hermes-agent.nousresearch.com/docs/user-guide/security>
