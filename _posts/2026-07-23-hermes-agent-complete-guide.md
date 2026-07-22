---
layout: post
title: "Hermes Agent 완벽 정리 — Nous Research가 만든 자기개선형 AI 에이전트 인프라"
date: 2026-07-23 07:00:00 +0900
categories: [AI, Agent]
tags: [hermes-agent, nous-research, ai-agent, self-improving, agent-skills, mcp, acp, memory, delegation, cron, harness-engineering]
---

# 한 번 설치하면 컴퓨터 위에 눌러앉는 AI — Hermes Agent

대부분의 AI 도구는 "물어보면 답하는" 대화창입니다. 반면 **Hermes Agent**는 성격이 다릅니다. 한 번 설치하면 내 컴퓨터(또는 VPS, Termux를 통한 안드로이드 폰)에 **백그라운드로 상주**하면서, 19개 이상의 메신저·터미널·웹 대시보드·IDE 어디서든 같은 기억과 같은 능력으로 접근할 수 있는 **자율 자동화 인프라**입니다.

Nous Research가 MIT 라이선스로 공개한 이 에이전트를, 공식 문서와 GitHub 릴리스 노트만을 근거로 정리한 39페이지짜리 가이드를 받아 핵심만 다시 압축했습니다. 앞서 쓴 [Agent Skills 표준 비교글]({% post_url 2026-07-22-agent-skills-four-ecosystems-compared %})의 실전판이기도 합니다 — Hermes는 그 표준을 실제로 어떻게 굴리는지 보여주는 살아있는 사례거든요.

> 📄 원본 가이드 전문(PDF, 39p): [hermes-agent-complete-guide.pdf](/assets/files/hermes-agent-complete-guide.pdf)
> 최종 출처: [hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs) · [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

---

## 1. 세 가지 철학이 전부를 설명한다

Hermes를 관통하는 설계 철학은 딱 세 가지입니다. 나머지 기능은 전부 이 셋의 파생입니다.

**① 자기개선(Self-Improvement).** 에이전트가 **5번 이상의 도구 호출**로 복잡한 작업을 성공시키면, 그 워크플로를 `~/.hermes/skills/` 아래 `SKILL.md`로 **스스로 저장**합니다. 다음에 비슷한 요청이 오면 즉시 재사용하죠. 여기에 메모리 시스템(`MEMORY.md`, `USER.md`)이 사용자의 선호·프로젝트 구조·환경을 누적합니다. **쓸수록 나에게 맞춰 자라는** 겁니다.

**② 어디서든(Everywhere).** CLI, TUI, 19개 메신저, 웹 대시보드, IDE(VS Code/Zed/JetBrains), API 서버, Webhook — 내가 어디 있든 **동일한 에이전트·동일한 메모리·동일한 스킬**에 접근합니다.

**③ 실용적·비용효율적(Practical & Cost-Effective).** 한 블로그 보고 기준 OpenClaw 대비 약 **90% 토큰 비용 절감**, ChatGPT Plus 한 달치($20) 미만의 VPS로 24시간 개인 비서를 돌릴 수 있습니다. 게다가 Tinker-Atropos 기반 RL 학습 파이프라인까지 내장.

---

## 2. Core — 무엇을 할 수 있고 무엇을 기억하는가

### 도구와 7가지 터미널 백엔드

도구(tool)는 논리적 묶음인 **도구셋(toolset)**으로 조직되어 플랫폼별로 켜고 끕니다. 흥미로운 건 `terminal` 도구가 **7가지 환경**에서 명령을 실행한다는 점입니다: `local`(기본), `docker`(격리), `ssh`(에이전트가 자기 코드를 못 건드리게 격리 권장), `singularity`(클러스터), `modal`(서버리스), `daytona`(클라우드 샌드박스), `vercel_sandbox`(마이크로VM). 컨테이너 백엔드는 읽기전용 루트FS·capability 제거·PID 제한(256)·네임스페이스 격리까지 적용합니다.

### 스킬 시스템 — agentskills.io 표준을 그대로

스킬은 필요할 때만 로드하는 온디맨드 지식 문서로, **점진적 공개(progressive disclosure)** 3단계로 작동합니다.

- **Level 0** `skills_list()` — 약 3,000토큰으로 모든 스킬의 이름·설명·카테고리만
- **Level 1** `skill_view(name)` — 특정 스킬 전체 내용
- **Level 2** `skill_view(name, path)` — 스킬 폴더 안의 특정 참조 파일만

앞선 글에서 다룬 그 표준입니다. 여기에 Hermes만의 실전 장치가 붙습니다.

- **`fallback_for_toolsets`** — 예: `duckduckgo-search` 스킬은 `FIRECRAWL_API_KEY`가 있으면 자동으로 숨고, 없을 때만 무료 대안으로 노출.
- **Skills Hub, 8개 소스 설치** — `official`, `skills-sh`(Vercel skills.sh), `well-known`(사이트가 `/.well-known/skills/`로 게시), `github`(기본 탭에 openai/skills·anthropics/skills 포함), `clawhub`, `claude-marketplace`, `lobehub`, `url`. **설치할 때마다 보안 스캐너**가 데이터 유출·프롬프트 주입·파괴적 명령·공급망 신호를 검사하고, 신뢰 등급(builtin/official/trusted/community)으로 정책을 차등 적용.
- **Curator(자동 정리)** — 에이전트가 만든 스킬만 백그라운드로 유지보수. 30일 미사용 → stale 표시, 90일 미사용 → 아카이브(삭제 아님, 복구 가능). 번들·허브 스킬은 절대 안 건드림.

### 영속 메모리 — 고정 스냅샷 패턴

`MEMORY.md`(에이전트 노트, 2,200자 한도)와 `USER.md`(사용자 프로필, 1,375자)가 세션 시작 시 시스템 프롬프트에 **한 번 고정 스냅샷으로 주입**됩니다. 세션 중 메모리를 바꿔도 디스크엔 즉시 반영되지만 시스템 프롬프트는 다음 세션까지 그대로 — **prefix 캐시를 보존해 성능을 지키려는 의도된 설계**입니다. (앞선 글의 "프롬프트 캐시 보존" 원칙이 여기서도 반복됩니다.) 여기에 **8개의 외부 메모리 프로바이더**(Honcho·OpenViking·Mem0·Hindsight·Holographic·RetainDB·ByteRover·Supermemory)를 플러그인으로 붙일 수 있고, 항상 내장 메모리와 함께(대체가 아니라 보완) 작동합니다.

### 컨텍스트 파일 & 인격(SOUL.md)

`.hermes.md`→`AGENTS.md`→`CLAUDE.md`→`.cursorrules` 순으로 첫 매칭 하나만 로드하고, 하위 디렉토리로 들어가면 점진적으로 발견합니다(시스템 프롬프트 비대화 방지 + 캐시 보존). **모든 컨텍스트 파일은 주입 전 프롬프트 인젝션 스캔**을 거칩니다("이전 지시 무시하라", 숨겨진 HTML 주석, zero-width 문자 등). 인격은 `SOUL.md`(시스템 프롬프트 1번 슬롯)로 정의하고, `/personality`로 14개 내장 인격(helpful·concise·technical·teacher·pirate·noir…)을 즉석 전환할 수 있습니다.

---

## 3. Automation — 사람 개입 없이 스스로 일하는 축

여기가 Hermes의 진짜 색깔입니다.

**Cron.** 자연어로 스케줄링합니다("매일 아침 9시 Hacker News AI 뉴스를 Telegram으로 요약해줘"). 출력은 19개 이상 타깃으로 전달 가능하고, **`[SILENT]`로 시작하면 전달을 완전히 억제**(문제 있을 때만 보고하는 모니터링에 유용). `wakeAgent` 사전검사 스크립트로 상태가 실제 변했을 때만 LLM을 깨울 수 있습니다. 안전장치: **cron 실행 세션은 재귀적으로 새 cron을 못 만듭니다**(폭주 방지).

**Subagent Delegation.** `delegate_task`가 격리 컨텍스트·제한 도구셋의 자식 에이전트를 만듭니다. 자식은 부모 대화를 **전혀 모르고** 오직 `goal`/`context` 필드만 받습니다. `role="orchestrator"`로 다단계 트리(깊이 최대 3)를 만들 수 있는데, **3×3 트리면 동시 27개 리프**에 도달하니 비용을 의식적으로 올려야 합니다.

**Persistent Goals (`/goal`).** 턴을 넘어 지속되는 목표를 주면, 매 턴 후 **경량 판사(judge) 모델**이 "목표 달성됐나?"를 판정하고 아니면 자동으로 계속합니다. 이건 **OpenAI Codex의 `/goal`에서 영감받은 Ralph 루프의 Hermes 구현**입니다. 판사가 에러 나면 `continue`로 처리(fail-open)하고, 진짜 안전판은 턴 예산(기본 20턴). 이 블로그에서 다뤄온 self-referential 루프 패턴과 정확히 같은 계보죠.

**Code Execution.** `execute_code`는 에이전트가 **여러 도구 호출을 파이썬 스크립트 한 방**으로 묶게 합니다. 핵심은 중간 도구 결과가 컨텍스트에 안 들어가고 최종 `print()`만 돌아온다는 것 — **토큰이 극적으로 줄어듭니다.** 자식 프로세스는 최소 환경으로 실행되고 KEY/TOKEN/SECRET 류 환경변수는 완전히 제거됩니다(Unix 소켓 RPC 필요 → Linux/macOS 전용).

**Event Hooks.** 게이트웨이 훅·플러그인 훅·셸 훅 3계층. `pre_tool_call`로 위험한 도구 호출을 `{"action":"block"}`으로 막고, `pre_llm_call`로 매 턴 사용자 메시지에 컨텍스트를 주입(시스템 프롬프트엔 절대 안 넣음 — 또 캐시 보존). YAML만으로 셸 스크립트를 라이프사이클에 거는 셸 훅은 Claude Code의 hooks와 판박이입니다.

---

## 4. Media·Web, 관리, 그리고 RL

- **Voice.** faster-whisper(로컬 무료)로 STT, Edge TTS(무료 322음성)/ElevenLabs/OpenAI로 TTS. Discord 음성 채널에 봇이 들어가 라이브 대화까지. Whisper의 "Thank you for watching" 같은 **환각 구문 26종을 정규식으로 필터링**하는 디테일이 인상적입니다.
- **Browser.** 6개 백엔드(Browserbase·Browser Use·Firecrawl·Camofox·로컬 Chrome CDP·로컬 Chromium). **하이브리드 라우팅**이 핵심 — 공개 URL은 클라우드, LAN/localhost는 로컬 사이드카로 자동 분기해서 "로컬 개발 중인데 클라우드 브라우저 쓰는" 문제를 해결합니다. 페이지는 접근성 트리(텍스트)로 표현해 LLM에 최적화.
- **Web Dashboard** (`hermes dashboard`, localhost:9119). 150+ 설정 필드 폼 편집, API 키 관리, 세션/로그/분석, 브라우저에 TUI 임베드까지. 데이터가 localhost를 안 떠납니다.
- **RL Training.** Tinker-Atropos 기반, LoRA + GRPO로 환경 특화 파인튜닝을 에이전트 도구(`rl_*`)로 오케스트레이션. 전체 학습 전 `rl_test_inference`로 저비용 검증.

---

## 5. Integrations — MCP를 '양방향'으로 쓴다

가장 엔지니어링적으로 흥미로운 대목입니다. Hermes는 MCP를 **두 방향 모두** 사용합니다.

- **MCP 클라이언트로서** — 외부 도구 서버(GitHub·DB·파일시스템)를 붙이고, 도구는 `mcp_<server>_<tool>` 접두사로 등록. `notifications/tools/list_changed`로 **런타임 동적 도구 발견**까지 지원.
- **MCP 서버로서** (`hermes mcp serve`) — Claude Code·Cursor·Codex 같은 다른 MCP 클라이언트가 Hermes의 **메시징 능력**(대화 목록·메시지 읽기·전송)을 도구로 쓸 수 있게 10개 도구를 노출. 즉 다른 에이전트가 Hermes를 통해 Telegram/Discord로 사람과 소통합니다.

여기에 **ACP**(에디터 통합), **OpenAI 호환 API 서버**(Open WebUI 등 수백 개 프론트가 Hermes를 백엔드로), 그리고 3계층 복원력 스택이 붙습니다: **자격증명 풀**(같은 프로바이더 여러 키 회전) → **주 모델 폴백**(크로스 프로바이더) → **보조 작업 폴백**. 25개 이상 LLM 프로바이더를 지원하고, OpenRouter 사용 시 `sort: price/latency/throughput`으로 라우팅을 튜닝합니다.

---

## 6. 번들 스킬 ~90개 — "이게 다 기본 탑재"

설치 시 `~/.hermes/skills/`로 복사되는 스킬만 약 90개입니다. 몇 개만 추리면:

- **github**: github-pr-workflow(브랜치→CI→머지), github-code-review(인라인 코멘트), github-issues(트리아지)
- **software-development**: systematic-debugging(4단계 근본원인), test-driven-development(RED-GREEN-REFACTOR 강제), plan/writing-plans, subagent-driven-development, requesting-code-review
- **mlops**: axolotl·unsloth·vllm·dspy·TRL·lm-eval-harness — 파인튜닝/서빙/평가 풀스택
- **productivity**: notion·linear·google-workspace·airtable·powerpoint·ocr-and-documents
- **creative**: manim-video·p5js·excalidraw·pixel-art·popular-web-designs(54개 실제 디자인 시스템)
- **autonomous-ai-agents**: claude-code·codex·opencode에 **코딩을 위임**하는 스킬(!)

`software-development` 카테고리의 스킬 이름들이 눈에 익다면 맞습니다 — Anthropic Superpowers의 systematic-debugging·TDD·writing-plans와 같은 계보입니다. 표준이 열리니 좋은 절차적 스킬이 생태계를 가로질러 이식되고 있다는 방증이죠.

---

## 7. 버전 흐름으로 읽는 방향성

| 버전 | 코드네임 | 핵심 |
| :-- | :-- | :-- |
| v0.9.0 (4/13) | Everywhere | Termux/Android, 웹 대시보드 첫 공개, 플러그인 컨텍스트 엔진 |
| v0.10.0 (4/16) | Tool Gateway | Nous 구독 하나로 Firecrawl·FAL·TTS·Browser Use 통합 |
| v0.11.0 (4/23) | — | Ink 기반 TUI 재작성, `/steer` 중간개입, 셸 훅, 스마트 위임 |
| v0.12.0 (4/30) | Curator | **자율 큐레이터**, MS Teams(19번째 플랫폼), Vercel Sandbox |

방향은 분명합니다. **"더 많은 접근 지점 → 더 자율적인 유지보수 → 더 저렴한 통합."** 사람이 덜 개입해도 시스템이 스스로 자라고 정리되는 쪽으로 가고 있습니다.

---

## 마치며 — 이건 '도구'가 아니라 '인프라'다

Hermes Agent를 한 문장으로 요약하면, **내 컴퓨팅 환경 위에 얹혀 자율적으로 자라는 개인 AI 인프라**입니다. 19개 메신저 · 8개 외부 메모리 · 14개 인격 · 90개 번들 스킬 · 25개 LLM 프로바이더 · 7개 터미널 백엔드 · 3계층 훅 · 자기개선 큐레이터 · RL 파이프라인 — 이 모든 게 **하나의 일관된 시스템**으로 맞물립니다.

제 시선에서 가장 배울 점은 **반복되는 두 원칙**입니다. 하나는 **프롬프트 캐시 보존**(메모리 고정 스냅샷, 컨텍스트를 시스템 프롬프트가 아닌 사용자 메시지에 주입), 다른 하나는 **컨텍스트 예산 절약**(스킬 점진적 공개, code_execution의 중간결과 은닉). 결국 좋은 에이전트 하네스의 승부처는 "무엇을 컨텍스트에 넣지 **않을지**"를 얼마나 정교하게 설계하느냐라는 걸, Hermes가 기능 하나하나로 증명하고 있습니다.

> 이 글은 Nous Research 공식 문서·GitHub 릴리스 노트 기반으로 정리된 [가이드 PDF](/assets/files/hermes-agent-complete-guide.pdf)를 다시 압축한 것입니다. 수치·기능은 버전에 따라 바뀔 수 있으니 최신 정보는 [공식 문서](https://hermes-agent.nousresearch.com/docs)를 확인하세요.
