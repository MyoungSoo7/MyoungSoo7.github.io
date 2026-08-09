---
layout: post
title: "Claude Code vs OpenAI Codex 공식문서 정면 비교: 성능·유용성·사용자·비용 + 초급/중급/고급 사용법"
date: 2026-08-09 23:55:00 +0900
categories: [AI, Engineering, Agent]
tags: [Claude Code, Codex, Coding Agent, Benchmark, Pricing, MCP, Hooks, Skills]
---

터미널 코딩 에이전트를 고를 때 사람들이 가장 먼저 찾는 건 벤치마크 점수다. 그런데 2026년 8월 현재, **두 벤더 모두 그 점수를 더 이상 제시하지 않는다.** OpenAI 는 SWE-bench Verified 보고를 공식적으로 중단했고, Anthropic 은 Opus 5 세대에서 벤치마크 세트 자체를 갈아치웠다. 그래서 이 글은 "누가 몇 점"이 아니라, **공식 1차 문서에 텍스트로 확인되는 것만** 가지고 두 도구를 성능·유용성·사용자·비용 네 축으로 비교하고, 각각의 초급/중급/고급 사용법을 정리한다.

> **수집 기준**: 모든 사실은 **2026-08-09** 에 직접 fetch 한 1차 출처(`code.claude.com` / `platform.claude.com` / `claude.com` / `anthropic.com` / `learn.chatgpt.com` / `developers.openai.com` / `help.openai.com` / `github.com/openai/codex`)에서만 가져왔다. 벤더가 자기 제품에 대해 주장한 성능 수치는 전부 **"벤더 자체 보고"** 로 라벨링했고, 차트 이미지로만 존재해 텍스트로 확인할 수 없는 수치는 **인용하지 않았다.** 전체 링크는 글 끝 References 참조.

---

## 0. 먼저: 문서 주소가 둘 다 이사했다

비교에 들어가기 전에 실무적으로 가장 먼저 걸리는 부분이다. 두 제품 모두 최근 문서 도메인이 바뀌었고, 옛 URL 을 인용한 글들은 지금 리다이렉트를 타고 있다.

| 제품               | 옛 주소                                  | 현재 주소                       | 상태                   |
| ------------------ | ---------------------------------------- | ------------------------------- | ---------------------- |
| Claude Code        | `docs.claude.com/en/docs/claude-code/*`  | `code.claude.com/docs/en/*`     | 301 Moved Permanently  |
| Claude 모델/플랫폼 | `docs.claude.com/en/docs/about-claude/*` | `platform.claude.com/docs/en/*` | 이동                   |
| Codex              | `developers.openai.com/codex/*`          | `learn.chatgpt.com/docs/*`      | 308 Permanent Redirect |
| OpenAI API         | `developers.openai.com/api/docs/*`       | (그대로)                        | 유지                   |

Codex 쪽 변화가 더 의미심장하다. Codex 문서가 **ChatGPT 데스크톱 앱 문서 세트("ChatGPT Learn")로 흡수**됐다. 개발자 사이트의 독립 제품이 아니라 ChatGPT 표면의 한 모드로 문서상 재배치된 것이다. 전체 색인은 [`learn.chatgpt.com/llms.txt`](https://learn.chatgpt.com/llms.txt) 에 있고, 모든 페이지에 `.md` 트윈이 있다(`<page-url>.md`). Claude Code 도 [`code.claude.com/docs/llms.txt`](https://code.claude.com/docs/llms.txt) 를 제공한다.

---

## 1. 정체와 표면(surface)

### Claude Code

공식 소개 문구는 이렇다. ["Work with Claude directly in your codebase. Build, debug, and ship from your terminal, IDE, Slack, or the web."](https://www.claude.com/claude-code) 지원 표면은 **Desktop / Terminal / IDE / Web and iOS / Slack** 다섯 가지이고, VS Code(+ Cursor, Devin Desktop)와 JetBrains 네이티브 확장이 있다.

```bash
# macOS, Linux, WSL
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex

# Homebrew (stable 채널은 약 1주 지연)
brew install --cask claude-code
brew install --cask claude-code@latest
```

시스템 요구사항은 **macOS 13.0+ / Windows 10 1809+ / Ubuntu 20.04+ / Debian 10+ / Alpine 3.19+**, **4 GB+ RAM, x64 또는 ARM64** 다. 주의할 점 하나: **네이티브 설치만 백그라운드 자동 업데이트**를 한다. Homebrew·WinGet·apt·dnf·apk 로 깔았다면 수동 업그레이드다.

그리고 진입 조건이 명확하다. 공식 문서 문장 그대로 — **"Claude Code requires a Pro, Max, Team, Enterprise, or Console account. The free Claude.ai plan does not include Claude Code access."**

### OpenAI Codex

Codex 는 Rust 로 짜인 TUI 바이너리이고, **Apache License 2.0 오픈소스**([github.com/openai/codex](https://github.com/openai/codex))다. 이게 Claude Code 와의 가장 근본적인 구조 차이다.

```bash
# macOS/Linux
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"

# npm / Homebrew
npm install -g @openai/codex
brew install --cask codex
```

표면은 **CLI / IDE 확장(VS Code·Cursor·Windsurf, 확장 ID `openai.chatgpt`, 별도로 Xcode·JetBrains 네이티브) / ChatGPT 데스크톱 앱 Codex 모드 / Codex cloud / GitHub 코드 리뷰 / Codex SDK / GitHub Action**.

**표면 비교 요약**

|                           | Claude Code                                                  | Codex                                             |
| ------------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| 라이선스                  | 상용 (Anthropic Commercial ToS)                              | **Apache 2.0**                                    |
| 터미널                    | ✅                                                           | ✅                                                |
| IDE                       | VS Code(+Cursor, Devin Desktop), JetBrains                   | VS Code(+Cursor, Windsurf), Xcode, JetBrains      |
| 데스크톱 앱               | ✅                                                           | ✅ (ChatGPT 앱 내 모드)                           |
| 웹/모바일                 | Web + iOS                                                    | ChatGPT 표면                                      |
| Slack                     | ✅                                                           | ✅ (문서상 언급, 전용 페이지 미확인)              |
| 클라우드 실행             | Claude Code on the web, self-hosted runner (Team/Enterprise) | Codex cloud (ChatGPT 로그인 필수)                 |
| GitHub                    | `anthropics/claude-code-action`                              | `openai/codex-action@v1`, PR 에서 `@codex review` |
| 무료 플랜                 | ❌ 미포함                                                    | ✅ 포함 (한도만 다름)                             |
| 네이티브 Windows 샌드박싱 | ❌ (WSL 2 만)                                                | ✅ (PowerShell 기반)                              |

마지막 두 줄이 실무 선택을 가르는 지점이다. **무료로 시작해볼 수 있는 건 Codex 뿐이고, 네이티브 Windows 에서 샌드박스가 도는 건 Codex 뿐이다.** Claude Code 의 샌드박싱은 macOS Seatbelt, Linux/WSL2 bubblewrap 기반이며 네이티브 Windows·WSL1 은 미지원이다.

---

## 2. 성능 — 벤치마크가 무너진 자리에서 무엇을 볼 것인가

여기가 이 글에서 가장 조심스럽게 써야 하는 절이다.

### 2-1. OpenAI 는 SWE-bench 보고를 스스로 그만뒀다

2026-02-23, OpenAI 는 ["Why we no longer evaluate SWE-bench Verified"](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) 를 발표하며 다음과 같이 명시했다.

> "we have stopped reporting SWE-bench Verified scores, and we recommend that other model developers do so too."

이유는 두 가지다. 첫째, 포화 — 6개월 동안 SOTA 가 74.9% 에서 80.9% 로만 움직였다. 둘째, 데이터 품질 — 27.6% 표본을 감사한 결과 **59.4% 의 문제가 결함 있는 테스트를 갖고 있었다**(narrow test cases 35.5%, wide 18.8%, misc 5.1%).

이어서 ["Separating signal from noise in coding evaluations"](https://openai.com/index/separating-signal-from-noise-coding-evaluations/) 에서는 대안으로 밀던 SWE-bench Pro 마저 권고를 철회했다.

> "we estimate that ~30% of SWE-bench Pro tasks are broken… we retract our earlier recommendation to adopt SWE-Bench Pro."

### 2-2. Anthropic 은 벤치마크 세트를 통째로 바꿨다

Anthropic 쪽도 결과적으로 같은 지점에 도착했다. 2026-07-24 [Claude Opus 5 발표](https://www.anthropic.com/news/claude-opus-5)의 평가 축은 **Frontier-Bench v0.1 / CursorBench 3.2 / AA Coding Agent Index / ARC-AGI 3 / GDPval-AA v2 / OSWorld 2.0 / HLE / Zapier AutomationBench / DeepSearchQA** 다. SWE-bench Verified 절대 점수는 오늘 확인한 어떤 공식 페이지에도 **텍스트로 등장하지 않는다.**

### 2-3. 그래서 남는 것: 상대 표현뿐

두 벤더의 최신 세대 발표문은 절대 점수를 본문에 쓰지 않고 차트 이미지로만 제공한다. 텍스트로 확인 가능한 것은 아래가 전부이며, **모두 벤더 자체 보고이고 재현 절차·원시 데이터는 비공개다.**

**Claude Opus 5 (2026-07-24, Anthropic 자체 보고)**

- "On coding and knowledge work evaluations like Frontier-Bench and GDPval-AA, Opus 5 is the new state-of-the-art, **though it remains behind Mythos 5 on cybersecurity tasks**."
- Frontier-Bench v0.1: "**more than doubles Opus 4.8's performance** at a lower cost per task"
- CursorBench 3.2: "at max effort, the model performs **within 0.5% of Fable 5's peak score**, but at half the cost per task"
- ARC-AGI 3: "Opus 5's score is **three times as high as the next-best model**"
- 자동 행동 감사: "Opus 5 scores **2.3** on overall misaligned behavior, the lowest of our recent models"

**Claude Sonnet 5 (2026-06-30, Anthropic 자체 보고)**

- "its performance is **close to that of Opus 4.8**, but at lower prices"
- Mozilla 협업 사이버 평가(Firefox 147 취약점): "**Neither of the Sonnet models could successfully develop a working exploit (both scored 0.0%)**"

**GPT-5.6 Sol (2026-06-26 프리뷰, OpenAI 자체 보고)**

- "GPT-5.6 Sol sets a new state of the art on **Terminal-Bench 2.1**" — **본문에 숫자 없음**
- GeneBench v1: "stronger results than GPT-5.5 while using fewer tokens" — 숫자 없음
- ExploitBench: "competitive with Mythos Preview using only **~1/3 of the output tokens**"
- 안전성: **700,000 A100-equivalent GPU 시간**의 자동 레드팀

**GPT-5.3-Codex (2026-02-05, OpenAI 자체 보고)** — 한 세대 이전이지만 정성 문장이 본문에 남아 있다.

- "sets a new industry high on SWE-Bench Pro and Terminal-Bench"
- "**25% faster**" (vs GPT-5.2-Codex), "does so with **fewer tokens than any prior model**"
- OSWorld-Verified 관련: "Humans score ~72%"

### 2-4. 이 절의 한계를 분명히 한다

- 위 주장은 **전부 각 벤더가 자사 제품에 대해 발표한 값**이다. 감사되지 않았다.
- **중립 제3자의 head-to-head 비교는 두 벤더의 공식 페이지에 존재하지 않는다.** 이 글도 그런 비교를 만들지 않는다.
- 벤더 스스로가 코딩 벤치마크의 신뢰도를 문제 삼은 상황에서, "어느 쪽이 더 똑똑한가"를 공식 문서만으로 판정하는 건 **불가능**하다.

**실무적 결론**: 지금 도구 선택의 근거는 벤치 점수가 아니라 **하네스(harness) 설계 — 권한 모델, 컨텍스트 관리, 확장 지점, 비용 구조 — 여야 한다.** 아래 세 절이 그 부분이다.

---

## 3. 유용성 — 하네스 기능 정면 비교

### 3-1. 권한/샌드박스 모델 (가장 큰 설계 차이)

**Claude Code — 6개 permission mode**

| Mode                          | 프롬프트 없이 실행되는 것                       | 용도                      |
| ----------------------------- | ----------------------------------------------- | ------------------------- |
| `default` (표시명 **Manual**) | 읽기만                                          | 시작·민감 작업            |
| `acceptEdits`                 | 읽기 + 파일 편집 + `mkdir`/`touch`/`mv`/`cp` 등 | 리뷰하며 반복             |
| `plan`                        | 읽기 (+auto 가용 시 분류기 승인 명령)           | 변경 전 탐색              |
| `auto`                        | 전부, 백그라운드 안전검사 동반                  | 장시간 작업               |
| `dontAsk`                     | 사전 승인된 도구만                              | 잠금 CI/스크립트          |
| `bypassPermissions`           | 전부                                            | **격리 컨테이너/VM 전용** |

`Shift+Tab` 으로 `default` → `acceptEdits` → `plan` 을 순환한다. `dontAsk` 는 순환에 절대 나오지 않고 `--permission-mode dontAsk` 로만 진입한다. Claude Code 홈페이지가 최근 강조하는 문구가 이 설계를 요약한다 — **"Auto mode: A safer long-running alternative to `--dangerously-skip-permissions`"**.

**Codex — 샌드박스 3종 × 승인 정책**

```toml
sandbox_mode = "read-only"          # read-only | workspace-write | danger-full-access
approval_policy = "on-request"      # untrusted | on-request | never | { granular = {...} }
```

기본 프리셋 `Auto` 는 `--sandbox workspace-write --ask-for-approval on-request` 다. 실행 시 기본값이 컨텍스트에 따라 달라지는 게 특징인데, **버전관리된 폴더면 `Auto`, 비버전관리 폴더면 `read-only`** 로 시작한다.

Codex 의 강점은 **네트워크 정책이 config 로 선언된다**는 점이다.

```toml
[sandbox_workspace_write]
writable_roots = []
network_access = false              # 기본 OFF

[features.network_proxy]
enabled = true
domains = { "api.openai.com" = "allow", "example.com" = "deny" }
```

도메인 규칙은 exact host / `*.example.com`(서브도메인만) / `**.example.com`(apex+서브) / `*`(allow 전용 글로벌 와일드카드)를 지원하고 **deny 가 항상 우선**한다. allow 항목이 하나도 없으면 전부 차단이다. writable root 안이어도 `<root>/.git`, `<root>/.agents`, `<root>/.codex` 는 재귀적으로 read-only 보호된다.

플랫폼별 강제 방식:

|                  | Claude Code                          | Codex                                                                 |
| ---------------- | ------------------------------------ | --------------------------------------------------------------------- |
| macOS            | Seatbelt                             | Seatbelt                                                              |
| Linux/WSL2       | bubblewrap + socat (+선택적 seccomp) | **`bubblewrap` 별도 설치 필요** (`apt install bubblewrap`)            |
| 네이티브 Windows | ❌ 미지원                            | ✅ PowerShell 기반 (`[windows] sandbox = "elevated" \| "unelevated"`) |

> ⚠️ **Codex 함정**: 새로 나온 **Permission profiles 는 Beta 이고 구형 `sandbox_mode` 와 조합할 수 없다.** `default_permissions` + `[permissions]` 를 쓰거나, `sandbox_mode` / `[sandbox_workspace_write]` 를 쓰거나 둘 중 하나다. 로드된 어떤 config 에든 `sandbox_mode` 가 있거나 `--sandbox` 를 넘기면 구형 설정이 우선한다. 두 체계를 섞은 설정 예제를 인터넷에서 복사하면 동작하지 않는다.

### 3-2. 프로젝트 지시문: CLAUDE.md vs AGENTS.md

**Claude Code — 4계층 메모리 (넓음 → 좁음 순서로 로드)**

| Scope          | 위치                                                                                                                                                 |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Managed policy | macOS `/Library/Application Support/ClaudeCode/CLAUDE.md` · Linux/WSL `/etc/claude-code/CLAUDE.md` · Windows `C:\Program Files\ClaudeCode\CLAUDE.md` |
| User           | `~/.claude/CLAUDE.md`                                                                                                                                |
| Project        | `./CLAUDE.md` 또는 `./.claude/CLAUDE.md`                                                                                                             |
| Local          | `./CLAUDE.local.md` (gitignore 권장)                                                                                                                 |

`@path/to/import` 문법으로 다른 파일을 끌어올 수 있고 **최대 4 hop** 재귀다. 코드 스팬/펜스 안의 `` `@README` `` 는 리터럴로 무시된다. 권장 크기는 **파일당 200줄 미만**.

중요한 상호운용 포인트 하나 — **Claude Code 는 `AGENTS.md` 를 읽지 않는다.** 두 도구를 같은 리포에서 쓰려면 이렇게 잇는다.

```bash
# 방법 1: CLAUDE.md 안에서 import
echo '@AGENTS.md' >> CLAUDE.md

# 방법 2: 심볼릭 링크
ln -s AGENTS.md CLAUDE.md
```

**Codex — AGENTS.md 탐색 규칙**

1. **Global**: `~/.codex/AGENTS.override.md`, 없으면 `~/.codex/AGENTS.md` (비어있지 않은 첫 파일만)
2. **Project**: 루트 → cwd 로 내려가며 각 디렉터리에서 `AGENTS.override.md` → `AGENTS.md` → `project_doc_fallback_filenames` 순으로 검사, **디렉터리당 최대 1개**
3. 루트부터 병합, 나중 파일이 앞을 오버라이드

```toml
project_doc_fallback_filenames = ["TEAM_GUIDE.md", ".agents.md"]
project_doc_max_bytes = 32768     # 기본 32 KiB
project_root_markers = [".git"]
```

Codex 는 **`## Code Review Rules`** 섹션을 가장 가까운 `AGENTS.md` 에서 찾아 코드 리뷰 규칙으로 쓴다. Claude Code 는 경로 스코프 규칙을 `.claude/rules/` 디렉터리로 분리하고, 모노레포에서는 `claudeMdExcludes` 로 다른 팀의 CLAUDE.md 를 제외할 수 있다.

### 3-3. 설정 우선순위

**Claude Code** (높은 것부터)

1. Managed (오버라이드 불가) → 2. CLI 인자 → 3. Local(`.claude/settings.local.json`) → 4. Project(`.claude/settings.json`) → 5. User(`~/.claude/settings.json`)

단 **permission rules 만은 예외로, 오버라이드가 아니라 스코프 간 병합(merge)** 된다.

**Codex** (높은 것부터, 6계층)

1. CLI 플래그 및 `--config` → 2. 프로젝트 `.codex/config.toml` (**신뢰된 프로젝트만**) → 3. 프로파일 `~/.codex/<name>.config.toml` → 4. 사용자 `~/.codex/config.toml` → 5. 시스템 `/etc/codex/config.toml` → 6. 내장 기본값

### 3-4. 확장 지점

| 확장            | Claude Code                                                        | Codex                                                          |
| --------------- | ------------------------------------------------------------------ | -------------------------------------------------------------- |
| MCP             | `claude mcp add` (http/sse/stdio/ws), 스코프 local/project/user    | `codex mcp add`, `[mcp_servers.<name>]`, stdio/HTTP            |
| MCP 서버로 노출 | Agent SDK 경유                                                     | **`codex mcp-server`** (Codex 자체를 stdio MCP 서버로)         |
| Hooks           | **31개 이벤트**                                                    | **11개 이벤트**                                                |
| 재사용 프롬프트 | Skills (`.claude/skills/<name>/SKILL.md`) — 슬래시 커맨드와 통합됨 | Skills (`$skill-name` 호출) — **커스텀 프롬프트는 deprecated** |
| 서브에이전트    | `.claude/agents/*.md`, 14개 frontmatter 필드                       | `[agents] max_concurrent_threads_per_session`                  |
| 플러그인        | `.claude-plugin/plugin.json`, 마켓플레이스                         | `codex plugin`, ChatGPT 와 디렉터리 공유                       |
| Git worktree    | `--worktree`/`-w`, `isolation: worktree`                           | `/worktree`, `/fork`, `codex fork`                             |
| SDK             | Claude Agent SDK (Python, TypeScript)                              | Codex SDK (TypeScript, Python beta)                            |

Hooks 이벤트 수가 3배 차이 나는 게 눈에 띈다. Claude Code 는 `SessionStart`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`, `TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`, `Elicitation`, `ElicitationResult`, `SessionEnd` 를 제공한다. Codex 는 `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `SessionStart`, `SessionEnd` 다.

---

## 4. 사용자 — 누구를 위한 도구인가

### 개인 개발자

|                   | Claude Code        | Codex             |
| ----------------- | ------------------ | ----------------- |
| 무료 진입         | ❌ 불가            | ✅ Free 플랜 포함 |
| 최저 유료 진입    | Pro $17/월(연간)   | ChatGPT Plus      |
| 오픈소스 검증     | 불가               | ✅ Apache 2.0     |
| 셀프호스팅 실행기 | Team/Enterprise 만 | —                 |

Claude Code 는 "일단 써보자"가 안 되는 대신, Pro $17 부터 전 기능이 열린다. Codex 는 Free 부터 들어갈 수 있고 소스를 직접 읽을 수 있다. 학습·검증 목적이라면 Codex, 유료 구독을 이미 쓰고 있다면 Claude Code 쪽 마찰이 없다.

### 팀·엔터프라이즈

**Claude Code 의 관리 설정 전달 경로** (4가지)

- Server-managed: claude.ai admin console 또는 self-hosted **Claude apps gateway** 에서 로그인 시 원격 배포
- macOS MDM: `com.anthropic.claudecode` managed preferences 도메인 (Jamf, Iru/Kandji 등)
- Windows: `HKLM\SOFTWARE\Policies\ClaudeCode` 레지스트리 (Group Policy/Intune)
- 파일 기반: `managed-settings.json` + **`managed-settings.d/` 드롭인 디렉터리** (systemd 관례대로 base 병합 후 `*.json` 알파벳순 병합, 배열은 concat+dedup, 객체는 deep-merge)

드롭인 디렉터리가 실무적으로 크다. 보안팀과 플랫폼팀이 하나의 파일을 두고 싸우지 않고 `10-telemetry.json`, `20-security.json` 으로 나눠 배포할 수 있다.

엔터프라이즈 기능(공식 pricing 페이지 명시): 스펜드 리밋, RBAC 세분화 권한, **SCIM**, **Audit logs**, **Compliance API**, 커스텀 데이터 보존, **네트워크 수준 접근 제어**, **IP allowlisting**, **HIPAA-ready offering**, 조직 전체 스킬 배포, 조직 지시문, inference hooks.

**Codex 의 관리 강제**

- 관리 파일 `requirements.toml`, `/etc/codex/config.toml`
- **`allowed_permission_profiles`** — 명시되지 않은 프로파일은 내장분·향후 추가분 포함 전부 거부
- 우선순위: **managed `requirements.toml` > workspace 시작 기본값 > 멤버 로컬 선택**
- RBAC, **Compliance API (CLI·IDE 로컬 사용까지 로그 커버)**, SAML SSO + MFA
- `browser_use_full_cdp_access = false` 로 Developer mode CDP 접근 차단

**학습 데이터 정책 차이** (조직 선택에 직결)

| 플랜      | Claude                                               | ChatGPT/Codex                                                 |
| --------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| 개인 유료 | Free/Pro/Max = **Opt-out** (기본 학습 대상, 꺼야 함) | Plus/Pro = data controls 로 끄지 않으면 학습에 사용될 수 있음 |
| 조직      | Team/Enterprise = **None by default**                | Business/Enterprise/Edu = 기본 미학습                         |

**지역 제약** (Codex 쪽만 확인됨): Sites in Codex 는 **EEA·스위스·영국 미지원**, Record & Replay 는 **EU·스위스·영국 초기 제외**.

### 관측(Observability)

Claude Code 는 어댑션 대시보드(`claude.ai/analytics/claude-code`, CSV export), Enterprise Analytics API(`read:analytics` 스코프), OpenTelemetry export 를 제공한다. 문서가 명시하는 중요한 단서 — **OpenTelemetry export 만이 모든 셋업에서 동작**하며, Bedrock / Google Cloud Agent Platform / Microsoft Foundry 를 쓰면 Anthropic 대시보드와 Analytics API 는 포함되지 않는다.

---

## 5. 비용 — 여기는 숫자가 명확하다

### 5-1. 구독 플랜

**Claude Code (claude.com/pricing)**

| 플랜          | 가격                                           | Claude Code |
| ------------- | ---------------------------------------------- | ----------- |
| Free          | $0                                             | ❌ 미포함   |
| **Pro**       | **$17/월** (연간 $200 선결제) / $20 월간       | ✅          |
| **Max 5x**    | **$100/월**                                    | ✅          |
| **Max 20x**   | **$200/월**                                    | ✅          |
| Team Standard | $20/석/월(연간) / $25 월간                     | ✅          |
| Team Premium  | $100/석/월(연간) / $125 월간 — "5x more usage" | ✅          |
| Enterprise    | **$20/석 + 사용량 API 요율**                   | ✅          |

컨텍스트 윈도우가 플랜에 묶인다는 점이 중요하다. Free/Pro/Max/Team = **200k**, Enterprise = **기본 모델에서 500k**. 사용 한도는 **5시간 롤링 세션 창 + 유료 플랜은 주간 한도 추가**이며, "Your activity across Claude on web, desktop, mobile, and Claude Code all draws from the same pool" — 웹·데스크톱·모바일·Claude Code 가 **같은 풀을 공유**한다.

**Codex (ChatGPT 플랜)**

Codex 는 **Free 와 Go 를 포함한 모든 ChatGPT 플랜에 포함**되고 사용량 한도만 다르다. 확인된 금액은 **Business $20/user/월(연간, 2인 이상) 또는 $25 월간**, **Pro 5x $100/월**, **Pro 20x $200/월**, Enterprise 는 커스텀(크레딧 기반 또는 토큰 기반 선택 가능)이다.

> **확인 불가**: ChatGPT Free/Go/Plus 의 월 요금은 `openai.com/chatgpt/pricing` 과 `chatgpt.com/pricing` 이 자동 fetch 를 403 으로 막고 렌더 시 달러 값이 스트립되어 **1차 출처로 확인하지 못했다.** 추정 대신 공란으로 둔다.

로컬 메시지 rate limit (5시간 창, `learn.chatgpt.com/docs/pricing.md` 기준):

| Plan     | GPT-5.6 Sol | Terra     | Luna         |
| -------- | ----------- | --------- | ------------ |
| Plus     | 10–100      | 25–200    | 250–2,000    |
| Pro 5x   | 50–500      | 125–1,000 | 1,250–10,000 |
| Pro 20x  | 200–2,000   | 500–4,000 | 5,000–40,000 |
| Business | 10–100      | 25–200    | 250–2,000    |

> ⚠️ **문서 불일치 주의**: 두 1차 미러가 서로 다른 표를 낸다. `developers.openai.com/codex/pricing` 캐시본은 Plus Sol 을 **15–90** 으로 표기한다. 위 표는 라이브 리다이렉트 타깃(`learn.chatgpt.com`)을 canonical 로 채택한 값이다. 또한 그 표의 Cloud chats / Code Reviews 열이 **모든 플랜에서 "Not available"** 로 나오는데 이는 다른 문서와 모순되므로 문서 오류로 보고 인용하지 않았다.

### 5-2. Codex 의 크레딧 제도 (2026-04-02 전환)

Codex 는 2026-04-02 부터 메시지 단위가 아니라 **토큰 기반 크레딧**으로 과금한다. 1M 토큰당 크레딧:

| 모델          | Input | Cached input | Output |
| ------------- | ----- | ------------ | ------ |
| GPT-5.6 Sol   | 125   | 12.5         | 750    |
| GPT-5.6 Terra | 62.5  | 6.25         | 375    |
| GPT-5.6 Luna  | 25    | 2.5          | 150    |
| GPT-5.4 mini  | 18.75 | 1.875        | 113    |

"GPT-5.6 usage averages **5–40 credits per message**." 크레딧은 Codex / ChatGPT Work / ChatGPT for Excel / Workspace Agents 가 **공유 풀**을 쓴다.

### 5-3. API 종량제 (1M 토큰당 USD)

**Anthropic**

| 모델         | Input    | Output    | Cache write | Cache read | Context |
| ------------ | -------- | --------- | ----------- | ---------- | ------- |
| Fable 5      | $10      | $50       | $12.50      | $1         | 1M      |
| **Opus 5**   | **$5**   | **$25**   | $6.25       | $0.50      | 1M      |
| **Sonnet 5** | **$2\*** | **$10\*** | $2.50\*     | $0.20\*    | 1M      |
| Haiku 4.5    | $1       | $5        | $1.25       | $0.10      | 200k    |

\* 도입가, **2026-08-31 까지**. 이후 $3/$15.

**OpenAI** (short context 기준, long context 는 270K 토큰 초과 시)

| 모델              | Input     | Cached | Cache write | Output     | Context   |
| ----------------- | --------- | ------ | ----------- | ---------- | --------- |
| **gpt-5.6-sol**   | **$5.00** | $0.50  | $6.25       | **$30.00** | 1,050,000 |
| **gpt-5.6-terra** | **$2.00** | $0.20  | $2.50       | **$12.00** | 1,050,000 |
| **gpt-5.6-luna**  | **$0.20** | $0.02  | $0.25       | **$1.20**  | 1,050,000 |
| gpt-5.5-pro       | $30.00    | —      | —           | $180.00    | —         |

부가 조건 비교:

|                | Anthropic                                   | OpenAI                                                                             |
| -------------- | ------------------------------------------- | ---------------------------------------------------------------------------------- |
| Batch          | −50%                                        | −50%                                                                               |
| Fast/Priority  | Opus 5 fast mode ≈ 2.5배 속도, **2배 가격** | Priority processing **2배**; Codex 크레딧은 GPT-5.6/5.5 **2.5배**, GPT-5.4 **2배** |
| 캐시 읽기 할인 | 모델별 상이 (Opus 5 는 input 의 1/10)       | **90% 할인**, cache write 는 uncached input 의 1.25배, 최소 30분 수명              |
| 지역 추론      | US-only inference **1.1배**                 | Data residency **+10%**                                                            |
| 웹 검색        | $10 / 1K searches                           | $10 / 1k calls                                                                     |

토큰 기준 단가만 보면 표면적으로 이렇다. 캐시 히트율을 $h$, 입력·출력 토큰을 $T_{in}, T_{out}$ 이라 할 때 1회 턴의 비용은

$$
C = T_{in}\bigl[(1-h)\,p_{in} + h\,p_{cache}\bigr] + T_{out}\,p_{out}
$$

이고, 에이전트 워크로드는 긴 대화에서 $h$ 가 0.9 이상까지 올라가므로 **$p_{cache}$ 와 $p_{out}$ 이 실질 비용을 지배한다.** 출력 단가가 $25 vs $30 (Opus 5 vs Sol) 인 점, Sonnet 5 도입가가 $10 인 점이 여기서 크게 작용한다.

### 5-4. 실제로 얼마 드나 — 두 벤더의 자체 보고

- **Anthropic (공식 costs 문서)**: "the average cost is around **$13 per developer per active day** and **$150-250 per developer per month**, with costs remaining **below $30 per active day for 90% of users**."
- **OpenAI (공식 pricing 문서)**: "On average, Codex costs **~$100–$200/developer per month**."

> 두 수치 모두 **벤더 자체 보고**이며 산출 방법·표본은 공개되지 않았다. 워크로드 구성이 다르면 그대로 재현되지 않는다.

### 5-5. 비용 확인 명령 — 흔한 오류 하나

> 🚩 **Claude Code 의 `/cost` 는 현재 문서에 존재하지 않는다.** 공식 명령은 **`/usage`** 와 **`/usage-credits`** 다. 많은 글이 아직 `/cost` 로 쓰고 있다.

```text
/usage
Total cost:            $0.55
Total duration (API):  6m 20s
Total duration (wall): 6h 33m 10s
Total code changes:    0 lines added, 0 lines removed
Usage by model:
   claude-sonnet-4-6:  1.2k input, 5.3k output, 940.0k cache read, 50.0k cache write ($0.55)
```

문서가 붙인 단서도 정확히 알아둘 것 — "Claude Code computes the dollar figure **locally from token counts priced at standard list rates**, so it doesn't reflect promotional pricing or contracted discounts and **may differ from your actual bill**." Codex 쪽 대응 명령은 **`/status`** (챗 ID, 컨텍스트 사용량, rate limit)다.

---

## 6. Claude Code 사용법 — 초급 / 중급 / 고급

### 6-A. 초급

```bash
claude                              # 대화형 세션
claude "explain this project"       # 초기 프롬프트와 함께
claude -p "explain this function"   # 1회 질의 후 종료 (headless)
cat logs.txt | claude -p "explain"  # 파이프 입력
claude -c                           # 현재 디렉터리 최근 대화 이어가기
claude -r "auth-refactor" "Finish this PR"
claude --version                    # 예: 2.1.211 (Claude Code)
claude doctor                       # 세션 없이 read-only 진단
```

**첫 세션 순서** (공식 워크플로): `/init` 로 starter CLAUDE.md 생성 → `/memory` 로 다듬기 → `/mcp` 로 서버 설정 → `/permissions` 로 승인 규칙 설정.

**자주 쓰는 명령 묶음**

| 상황    | 명령                                                           |
| ------- | -------------------------------------------------------------- |
| 작업 중 | `/plan`, `/model`, `/effort`, `/context`, `/compact`, `/btw`   |
| 배포 전 | `/diff`, `/code-review`(별칭 `/review`), `/security-review`    |
| 세션 간 | `/clear`(별칭 `/reset`, `/new`), `/resume`, `/branch`, `/fork` |
| 문제 시 | `/rewind`, `/doctor`, `/debug`, `/feedback`                    |
| 비용    | `/usage`, `/usage-credits`                                     |

슬래시 명령은 **메시지 맨 앞에서만** 인식된다. 응답 중에 입력하면 큐잉되지만 `/status`, `/tasks`, `/usage` 는 즉시 실행된다.

**권한 모드 전환**: `Shift+Tab`. 상태바에 `⏸ manual mode on`, `⏵⏵ accept edits on`, `⏸ plan mode on`, `⏵⏵ auto mode on` 등으로 표시된다.

### 6-B. 중급

**모델 별칭** — 그냥 `opus`, `sonnet` 만 쓰면 손해다.

| Alias                     | 동작                                                       |
| ------------------------- | ---------------------------------------------------------- |
| `default`                 | 모델 오버라이드 해제 (그 자체는 모델 별칭이 아님)          |
| `best`                    | 조직이 접근 가능하면 Fable 5, 아니면 최신 Opus             |
| `opusplan`                | **plan mode 에서 `opus`, 실행 시 `sonnet` 으로 자동 전환** |
| `sonnet[1m]` / `opus[1m]` | 1M 컨텍스트 변형                                           |

설정 우선순위는 `/model <alias>` → `claude --model` → `ANTHROPIC_MODEL` → 설정 파일 `model` 필드다. `/model` 피커에서 `Enter` 는 전환 + 기본값 저장, `s` 는 이번 세션만이다.

버전 요구를 놓치면 조용히 안 된다 — **Opus 5 = v2.1.219+, Sonnet 5 = v2.1.197+, Fable 5 = v2.1.170+**. Fable 5 는 기본 모델이 아니라 `/model fable` 이 필요하고, **zero data retention 환경에서는 쓸 수 없다.**

**Effort**: `low` / `medium` / `high` / `xhigh` / `max`. Opus 5·Sonnet 5 는 Claude Code 기본값이 `high` 다. 세션 중 `/effort`, skill·subagent frontmatter 의 `effort` 로 오버라이드하고, skill 안에서는 `${CLAUDE_EFFORT}` 로 참조한다.

**MCP 설정**

```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp        # 권장(원격)
claude mcp add --env AIRTABLE_API_KEY=KEY --transport stdio airtable -- npx -y airtable-mcp-server
claude mcp add-json events '{"type":"ws","url":"wss://mcp.example.com/socket"}'
claude mcp list / get <name> / remove <name>
claude mcp login <name>          # v2.1.186+
```

| Scope            | Loads in        | 팀 공유            | 저장 위치        |
| ---------------- | --------------- | ------------------ | ---------------- |
| **Local** (기본) | 현재 프로젝트만 | No                 | `~/.claude.json` |
| **Project**      | 현재 프로젝트만 | **Yes (버전관리)** | **`.mcp.json`**  |
| **User**         | 모든 프로젝트   | No                 | `~/.claude.json` |

우선순위는 **Local > Project > User** 이고 병합하지 않는다. stdio 는 `--` 로 Claude 옵션과 서버 명령을 분리해야 한다. SSE 는 deprecated 다.

보안상 알아둘 것: 프로젝트 스코프 서버는 대화형 세션에서 승인 프롬프트가 뜨지만, **`claude -p`, Agent SDK, cloud 세션은 프롬프트 없이 로드된다.** 차단하려면 `disabledMcpjsonServers` 나 `--setting-sources` 를 쓴다.

**세션 관리**

```bash
claude --continue                  # 최근 세션 재개
claude --resume                    # 피커
claude --resume "auth-refactor"    # 이름으로 바로
claude --from-pr 1234              # 해당 PR 에 연결된 세션만 필터
claude --continue --fork-session   # 분기
```

피커 단축키: `Ctrl+R` 이름 변경 · `Ctrl+A` 모든 프로젝트 · `Ctrl+W` 모든 워크트리 · `Ctrl+B` 현재 브랜치만 · `Space` 미리보기. **PR URL 을 붙여넣으면 그 PR 을 만든 세션을 찾아준다.**

**Checkpointing / Rewind** — 모든 사용자 프롬프트마다 체크포인트가 생기고 **최근 100개**가 유지된다. `/rewind` 또는 입력창이 빈 상태에서 `Esc` 두 번. 메뉴는 Restore code and conversation / Restore conversation / Restore code / Summarize from here / Summarize up to here.

한계를 반드시 알고 써야 한다 — **bash 로 변경한 파일(`rm`, `mv`, `cp`)은 추적되지 않고**, subagent 편집은 대개 복원되지 않으며, 심볼릭/하드링크 경로는 복원하지 않는다. 문서가 못 박는다: **"Not a replacement for version control."**

### 6-C. 고급

**Subagents** — `.claude/agents/*.md`. 필수 필드는 `name`, `description` 둘뿐이고 나머지는 전부 선택이다.

```markdown
---
name: code-improver
description: Scans files and suggests improvements for readability, performance, and best practices. Use after writing or modifying code.
tools: Read, Grep, Glob
model: sonnet
effort: high
isolation: worktree
memory: project
---

You are a code improvement specialist. For each issue you find, explain
the problem, show the current code, and provide an improved version.
```

주요 선택 필드: `tools` / `disallowedTools` / `model`(기본 `inherit`) / `permissionMode` / `maxTurns` / `skills`(설명이 아니라 **전문을 프리로드**) / `mcpServers` / `hooks` / `memory` / `background` / `effort` / `isolation: worktree` / `color` / `initialPrompt`.

스코프 우선순위: Managed settings > `--agents` CLI 플래그 > `.claude/agents/` > `~/.claude/agents/` > 플러그인 `agents/`.

> ⚠️ 보안 제약: **플러그인이 제공한 subagent 는 `hooks`, `mcpServers`, `permissionMode` frontmatter 를 무시한다.** 서드파티 플러그인이 권한을 스스로 올릴 수 없게 만든 설계다.

내장 subagent 로 **Explore**(read-only, Write/Edit 거부, thoroughness = quick/medium/very thorough)와 **Plan** 이 있는데, 이 둘은 **CLAUDE.md 와 git status 를 건너뛴다.**

**Hooks** — 3단 중첩 구조(이벤트 → matcher group → handler)다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(rm *)",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh"
          }
        ]
      }
    ]
  }
}
```

핸들러가 stdout 으로 결정을 돌려준다.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook"
  }
}
```

핵심 의미론 하나 — **"The hook can deny the call, but staying silent doesn't approve it."** exit 0 + 출력 없음은 "결정 없음"이고 통상 권한 흐름이 이어진다. `if` 조건은 프로세스 스폰 자체를 줄이는 필터다. 핸들러 종류는 command / HTTP endpoint / MCP tool / prompt / agent 다섯 가지.

**Skills** — "Custom commands have been merged into skills." `.claude/commands/deploy.md` 와 `.claude/skills/deploy/SKILL.md` 둘 다 `/deploy` 를 만들고, 충돌 시 skill 이 이긴다. [Agent Skills 오픈 표준](https://agentskills.io)을 따른다.

```yaml
---
description: Summarizes uncommitted changes and flags anything risky. Use when the user asks what changed, wants a commit message, or asks to review their diff.
---

## Current changes

!`git diff HEAD`
```

`` !`command` `` 는 **Claude 가 보기 전에 실행 결과로 치환된다.** 문자열 치환으로 `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}` 를 쓴다. `description` + `when_to_use` 합계는 **1,536자에서 잘린다.** 체이닝은 `/skill-a /skill-b do XYZ` 형태로 **최대 6개**.

**병렬·백그라운드 실행**

```bash
/background [prompt]     # 별칭 /bg — 현재 세션을 백그라운드 에이전트로 분리
/fork                    # 대화 복사본을 별도 백그라운드 세션으로
/tasks                   # 백그라운드 작업 목록
/batch <...>             # 코드베이스 변경을 5~30개 독립 단위로 분해,
                         # 각각 격리된 git worktree 에서 subagent 실행 → 테스트 → PR

claude agents --json     # 셸에서 목록
claude attach <id> / logs <id> / stop <id> / respawn <id>
claude daemon status
```

**Headless / CI**

```bash
claude -p "review this diff" --output-format json
claude -p "..." --json-schema ./schema.json
claude -p "..." --bare            # hooks/skills/plugins/MCP/auto memory/CLAUDE.md 자동탐색 생략 → 빠른 시작
claude -p "..." --append-system-prompt-file ./ci-rules.md
claude -p "..." --autocompact auto        # v2.1.221+
```

**GitHub Actions**

```bash
/install-github-app        # gh CLI + gh auth login 선행 필요
```

시크릿은 `ANTHROPIC_API_KEY` 또는 `CLAUDE_CODE_OAUTH_TOKEN`(`claude setup-token` 으로 생성, Pro/Max/Team/Enterprise). OIDC 연합 인증도 지원한다(`anthropic_federation_rule_id`, `anthropic_organization_id`, `anthropic_service_account_id`, `anthropic_workspace_id` + `id-token: write`).

**Agent SDK** — "The Agent SDK gives you the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript." 다른 언어에서는 **"run the CLI as a subprocess with the `-p` flag and `--output-format json`"** 이 공식 권고다.

> ⚠️ 브랜딩 제약: 파트너는 "Claude Agent", "Claude", "{YourAgentName} Powered by Claude" 는 쓸 수 있지만 **"Claude Code" 또는 "Claude Code Agent" 라는 이름과 Claude Code 브랜드 ASCII 아트/유사 비주얼은 쓸 수 없다.** 또 **"Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK."**

---

## 7. Codex 사용법 — 초급 / 중급 / 고급

### 7-A. 초급

```bash
codex                                  # 인터랙티브 TUI (첫 실행 시 ChatGPT 로그인)
codex "explain this codebase"
codex --image ./screenshot.png "why does this layout break?"
codex --search "..."                   # 웹 검색
codex resume                           # 세션 재개
codex doctor                           # 진단
```

**로그인 방식**

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
printenv CODEX_ACCESS_TOKEN | codex login --with-access-token   # 엔터프라이즈
codex login --device-auth                                        # 헤드리스
codex login status / codex logout
```

> 🚩 **자격증명 평문 주의**: 기본 저장 위치는 **`~/.codex/auth.json` 평문**이다. OS 키체인으로 옮기려면 `cli_auth_credentials_store = "keyring"` 을 설정한다.

중요한 경계선 하나 — **Codex cloud 는 ChatGPT 로그인이 필수이고, API 키는 로컬 전용이다.** 공식 문서 그대로: "Codex in the CLI, SDK, or IDE extension / **No cloud-based features (GitHub code review, Slack, etc.)** / Model availability follows the API models available to your key."

**슬래시 명령 (자주 쓰는 것)**

| 명령                   | 설명                                      |
| ---------------------- | ----------------------------------------- |
| `/init`                | 현재 프로젝트에 `AGENTS.md` 스캐폴드 생성 |
| `/model`, `/reasoning` | 모델·추론 강도 전환                       |
| `/plan`                | plan mode 토글                            |
| `/review`              | 코드 리뷰 모드                            |
| `/status`              | 챗 ID, 컨텍스트 사용량, rate limit        |
| `/compact`             | 컨텍스트 압축                             |
| `/worktree`, `/fork`   | 새 git worktree / 챗 복제                 |
| `/cloud`, `/local`     | 클라우드 / 로컬 실행 전환                 |
| `/fast`                | Fast 서비스 티어 on/off                   |
| `/side`                | 메인 챗 방해 없이 임시 사이드 챗          |
| `/mcp`                 | 연결된 MCP 서버 상태                      |

스킬 명시 호출은 **`$`** 다 (ChatGPT 에서는 `@`).

### 7-B. 중급

**모델 선택**

```bash
codex -m gpt-5.6-sol      # 기본 Power 설정 = sol + medium reasoning
codex -m gpt-5.6-terra
codex -m gpt-5.6-luna
codex -m gpt-5.3-codex-spark
```

네이밍 규칙이 바뀌었다 — **숫자는 세대, 이름은 지속적 능력 티어**다. `gpt-5.6` 별칭은 Sol 로 라우팅된다.

> ⚠️ **은퇴 예정**: GPT-5.4 / GPT-5.4 mini 는 **2026-08-31 부로 Codex 에서 은퇴**한다(ChatGPT 로그인 한정, API 는 무관). `gpt-5.2`, `gpt-5.3-codex` 는 이미 deprecated. Codex 에서 Chat Completions API 지원도 deprecated 다. 또 "Currently, you can't change the default model for Codex cloud chats."

**config.toml 핵심 키**

```toml
#:schema https://developers.openai.com/codex/config-schema.json
model = "gpt-5.6"
model_reasoning_effort = "medium"      # minimal | low | medium | high | xhigh
plan_mode_reasoning_effort = "high"
model_verbosity = "medium"
approval_policy = "on-request"
sandbox_mode = "read-only"
file_opener = "vscode"                 # vscode | vscode-insiders | windsurf | cursor | none
web_search = "cached"                  # disabled | cached | indexed | live
project_doc_max_bytes = 32768
cli_auth_credentials_store = "file"    # file | keyring | auto
model_auto_compact_token_limit = 64000
tool_output_token_limit = 12000

[agents]
max_concurrent_threads_per_session = 6
default_subagent_model = "gpt-5.6-terra"

[sandbox_workspace_write]
writable_roots = []
network_access = false

[shell_environment_policy]
include_only = ["PATH", "HOME"]
```

`[features]` 로 실험 기능을 켠다: `apps`, `goals`, `hooks`, `fast_mode`, `memories`(기본 false), `multi_agent`, `personality`, `shell_snapshot`, `shell_tool`, `unified_exec`. CLI 로는 `codex --enable <feature>`.

**Fast mode**: `/fast on|off|status`, 영구 설정은 `service_tier = "fast"` + `[features] fast_mode = true`. 속도 **1.5배**, 크레딧은 GPT-5.6/5.5 **2.5배**, GPT-5.4 **2배**. API 키 사용 시에는 크레딧 배수가 적용되지 않는다.

**비대화형 / CI: `codex exec`**

```bash
codex exec "summarize the repository structure and list the top 5 risky areas"
codex exec --json "summarize the repo structure" | jq
codex exec "Extract project metadata" --output-schema ./schema.json -o ./project-metadata.json
codex exec resume --last "fix the race conditions you found"
CODEX_API_KEY=<api-key> codex exec --json "triage open bug reports"
```

> 🚩 **`codex exec` 의 기본 샌드박스는 `read-only` 다.** CI 에서 파일을 쓰게 하려면 `--sandbox workspace-write` 를 명시해야 한다. `--full-auto` 는 deprecated. 그리고 **`CODEX_API_KEY` 환경변수는 `codex exec` 에서만 지원**된다.

JSONL 이벤트 타입은 `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, `error` 다.

**Linux 에서 샌드박스가 안 돌 때** — bubblewrap 이 필요하다.

```bash
sudo apt install bubblewrap     # 또는 sudo dnf install bubblewrap
```

Ubuntu 24.04 는 AppArmor 가 unprivileged user namespace 를 막아서 추가 조치가 필요하다(`bwrap-userns-restrict` 프로파일 + `sudo apparmor_parser -r`, 또는 `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`).

### 7-C. 고급

**MCP**

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
codex mcp add <name> --env VAR=VALUE -- <stdio server-command>
codex mcp list
codex mcp login <server>

codex mcp-server        # ← Codex 자체를 stdio MCP 서버로 노출
```

마지막 줄이 Claude Code 에 없는 기능이다. Codex 를 다른 에이전트의 도구로 꽂을 수 있다. 서버별 승인 모드도 세밀하다 — `default_tools_approval_mode` (`auto` | `prompt` | `writes` | `approve`), `tools.<name>.approval_mode`, `enabled_tools` / `disabled_tools`.

**Hooks** — 11개 이벤트(`PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `SessionStart`, `SessionEnd`). 위치는 `~/.codex/hooks.json`, `~/.codex/config.toml` 의 `[hooks]`, `<project>/.codex/hooks.json`, `<project>/.codex/config.toml`. `/hooks` 로 검토·신뢰 부여하고, `--dangerously-bypass-hook-trust` 로 우회하며, `[features] hooks = false` 로 끈다. 타임아웃 기본 600초(SessionEnd 는 1초, 최대 3초).

**Permission profiles (Beta)** — 내장 3종(`:read-only`, `:workspace`, `:danger-full-access`)을 상속해 명명 프로파일을 만든다.

```toml
default_permissions = "project-edit"

[permissions.project-edit]
description = "Project editing with OpenAI API access."
extends = ":workspace"

[permissions.project-edit.workspace_roots]
"~/code/app" = true

[permissions.project-edit.filesystem]
":minimal" = "read"

[permissions.project-edit.filesystem.":workspace_roots"]
"." = "write"
".devcontainer" = "read"
"**/*.env" = "deny"

[permissions.project-edit.network]
enabled = true

[permissions.project-edit.network.domains]
"api.openai.com" = "allow"
"*.github.com" = "allow"
"tracking.example.com" = "deny"
```

`extends` 는 `:read-only` / `:workspace` / 다른 명명 프로파일만 가능하고 **`:danger-full-access` 는 상속할 수 없다.** 알 수 없는 부모나 순환 상속도 거부된다. 앞서 말한 대로 **구형 `sandbox_mode` 와는 섞이지 않는다.**

**Codex cloud 환경** — 라이프사이클을 알아야 시크릿 사고가 안 난다.

컨테이너 생성 → 리포 체크아웃 → **setup script (인터넷 O)** → (캐시 재개 시) maintenance script → **agent phase (인터넷 기본 OFF)** → diff/PR

> 🔒 **시크릿은 setup script 에만 제공되고 agent phase 전에 제거된다.** setup script 는 별도 Bash 세션에서 돌기 때문에 환경변수를 유지하려면 `~/.bashrc` 에 써야 한다. 컨테이너 캐시는 최대 **12시간**이고 스크립트·환경·시크릿 변경 시 자동 무효화된다. 기본 이미지는 `openai/codex-universal`.

**코드 리뷰**

```bash
codex review --uncommitted
codex review --base main
codex review --commit <sha> --title "..."
```

GitHub 에서는 Codex settings 에서 리포별 Code review 를 켠 뒤 PR 에서 **`@codex review`** 로 트리거한다. Codex 가 👀 리액션을 달고 **P0·P1 이슈만** 플래그한다. Automatic reviews 토글, `@codex security review`(리서치 프리뷰), `@codex fix the P1 issue` 도 있다. 데스크톱 앱에서 PR 컨텍스트를 쓰려면 `gh auth login` 이 필요하다.

**Codex SDK**

```bash
npm install @openai/codex-sdk     # TypeScript, Node.js 18+
pip install openai-codex          # Python 3.10+, beta
```

```ts
const codex = new Codex();
const thread = codex.startThread();
const result = await thread.run(
  "Make a plan to diagnose and fix the CI failures",
);
const thread2 = codex.resumeThread(threadId);
```

```python
from openai_codex import Codex, Sandbox

with Codex() as codex:
    thread = codex.thread_start(model="gpt-5.6-terra", sandbox=Sandbox.workspace_write)
    result = thread.run("...")
```

**GitHub Action** — `openai/codex-action@v1`. inputs 중 눈여겨볼 것은 `safety-strategy` (기본 `drop-sudo`, 대안 `unprivileged-user`, **Windows 에서는 `unsafe` 필수**), `sandbox`, `effort`, `allow-users`, `allow-bots`. output 은 `final-message`.

> ⚠️ **커스텀 프롬프트는 deprecated 다.** 공식 문서 문장: "Deprecated. Use skills for reusable prompts." 스킬 제작은 `$skill-creator` 로 하고, 플러그인 디렉터리는 ChatGPT 와 공유한다. 아직도 커스텀 프롬프트를 소개하는 글이 많으니 주의.

---

## 8. 그래서 뭘 골라야 하나

공식 문서만 근거로 말할 수 있는 것은 "어느 쪽이 더 똑똑한가"가 아니라 **"어느 하네스가 당신의 제약에 맞는가"** 다.

**Codex 가 유리한 경우**

- **무료로 시작해야 한다** — ChatGPT Free 플랜에도 포함된다.
- **소스를 감사해야 한다** — Apache 2.0 오픈소스.
- **네이티브 Windows 에서 샌드박스가 필요하다** — Claude Code 는 WSL 2 만 지원.
- **에이전트를 다른 에이전트의 도구로 꽂아야 한다** — `codex mcp-server`.
- **네트워크 egress 를 도메인 단위로 선언적으로 통제해야 한다** — `[features.network_proxy]` 의 allow/deny 규칙.

**Claude Code 가 유리한 경우**

- **하네스를 깊게 커스터마이즈한다** — 훅 이벤트 31개 vs 11개, subagent frontmatter 14필드.
- **장시간 자율 실행이 필요하다** — `auto` 모드가 `bypassPermissions` 의 안전한 대안으로 설계됐고, `/batch` 가 작업을 5~30개 worktree 로 쪼개 병렬 실행한다.
- **MDM 으로 정책을 강제 배포해야 한다** — Jamf/Intune/Group Policy + `managed-settings.d/` 드롭인.
- **잘못된 편집을 되돌려야 한다** — 프롬프트 단위 체크포인트 100개 + `/rewind`.
- **컨텍스트가 크다** — Enterprise 플랜은 기본 모델에서 500k.

**둘 다 쓰는 경우** (실제로 흔한 선택) — `AGENTS.md` 를 단일 소스로 두고 Claude Code 쪽에서 `@AGENTS.md` 로 import 하거나 심볼릭 링크를 걸면 지시문을 한 벌만 유지할 수 있다.

**마지막으로 한 번 더** — 이 글의 성능 절에 인용된 모든 수치와 주장은 **각 벤더가 자사 제품에 대해 발표한 자체 보고**이며, 재현 절차와 원시 데이터는 공개되지 않았다. 두 벤더의 공식 페이지 어디에도 **중립 제3자의 head-to-head 비교는 존재하지 않는다.** 그리고 OpenAI 스스로가 코딩 벤치마크의 신뢰도 문제를 공식화한 지금, 벤치 점수로 도구를 고르는 프레임 자체가 벤더에 의해 부정된 상태다. 결정은 당신의 리포에서 두 도구를 같은 태스크로 돌려본 결과로 내리는 게 맞다.

---

## References

**Claude Code / Anthropic** (모두 2026-08-09 fetch)

1. Claude Code 제품 페이지 — <https://www.claude.com/claude-code>
2. Claude Code Setup — <https://code.claude.com/docs/en/setup>
3. Claude Code Model configuration — <https://code.claude.com/docs/en/model-config>
4. Claude Code Permission modes — <https://code.claude.com/docs/en/permission-modes>
5. Claude Code Settings — <https://code.claude.com/docs/en/settings>
6. Claude Code Memory (CLAUDE.md) — <https://code.claude.com/docs/en/memory>
7. Claude Code Slash commands — <https://code.claude.com/docs/en/commands>
8. Claude Code CLI reference — <https://code.claude.com/docs/en/cli-reference>
9. Claude Code MCP — <https://code.claude.com/docs/en/mcp>
10. Claude Code Subagents — <https://code.claude.com/docs/en/sub-agents>
11. Claude Code Hooks — <https://code.claude.com/docs/en/hooks>
12. Claude Code Skills — <https://code.claude.com/docs/en/skills>
13. Claude Code Sessions — <https://code.claude.com/docs/en/sessions>
14. Claude Code Checkpointing — <https://code.claude.com/docs/en/checkpointing>
15. Claude Code Costs — <https://code.claude.com/docs/en/costs>
16. Claude Code GitHub Actions — <https://code.claude.com/docs/en/github-actions>
17. Claude Agent SDK overview — <https://docs.claude.com/en/docs/claude-code/agent-sdk/overview>
18. Claude 모델 overview (가격·컨텍스트) — <https://platform.claude.com/docs/en/about-claude/models/overview>
19. Claude 요금제 — <https://www.claude.com/pricing>
20. Claude Opus 5 발표 (2026-07-24) — <https://www.anthropic.com/news/claude-opus-5>
21. Claude Sonnet 5 발표 (2026-06-30) — <https://www.anthropic.com/news/claude-sonnet-5>
22. Claude Fable 5 / Mythos 5 발표 (2026-06-09) — <https://www.anthropic.com/news/claude-fable-5-mythos-5>
23. Claude Code 릴리스 노트 — <https://docs.claude.com/en/release-notes/claude-code>

**Codex / OpenAI** (모두 2026-08-09 fetch)

24. Codex 리포지토리 (Apache 2.0) — <https://github.com/openai/codex>
25. Codex CLI 문서 — <https://learn.chatgpt.com/docs/codex/cli.md>
26. Codex Sandboxing — <https://learn.chatgpt.com/docs/sandboxing.md>
27. Codex Agent approvals & security — <https://learn.chatgpt.com/docs/agent-approvals-security.md>
28. Codex Permissions (Beta) — <https://learn.chatgpt.com/docs/permissions.md>
29. Codex AGENTS.md — <https://learn.chatgpt.com/docs/agent-configuration/agents-md.md>
30. Codex config 기본 — <https://learn.chatgpt.com/docs/config-file/config-basic.md>
31. Codex config 샘플 — <https://learn.chatgpt.com/docs/config-file/config-sample.md>
32. Codex 비대화형 모드 (`codex exec`) — <https://learn.chatgpt.com/docs/non-interactive-mode.md>
33. Codex 슬래시 명령 — <https://learn.chatgpt.com/docs/reference/slash-commands.md>
34. Codex 개발자 명령 — <https://learn.chatgpt.com/docs/developer-commands.md>
35. Codex MCP — <https://learn.chatgpt.com/docs/extend/mcp.md>
36. Codex Hooks — <https://learn.chatgpt.com/docs/hooks.md>
37. Codex Skills & plugins — <https://learn.chatgpt.com/docs/skills-and-plugins.md>
38. Codex 코드 리뷰 — <https://learn.chatgpt.com/docs/code-review.md>
39. Codex cloud 환경 — <https://learn.chatgpt.com/docs/environments/cloud-environment.md>
40. Codex SDK — <https://learn.chatgpt.com/docs/codex-sdk.md>
41. Codex GitHub Action — <https://learn.chatgpt.com/docs/github-action.md>
42. Codex 인증 — <https://learn.chatgpt.com/docs/auth.md>
43. Codex 속도 설정 (Fast mode) — <https://learn.chatgpt.com/docs/agent-configuration/speed.md>
44. Codex 모델 — <https://learn.chatgpt.com/docs/models>
45. Codex 가격·rate limit — <https://learn.chatgpt.com/docs/pricing.md>
46. Codex 및 ChatGPT 플랜 사용 한도 — <https://help.openai.com/en/articles/11369540-codex-and-chatgpt-plan-usage-limits>
47. Codex rate card — <https://help.openai.com/en/articles/20001106-codex-rate-card>
48. OpenAI API 가격 — <https://developers.openai.com/api/docs/pricing>
49. OpenAI 모델 비교 (컨텍스트 윈도우) — <https://developers.openai.com/api/docs/models/compare>
50. OpenAI Business 요금 — <https://openai.com/business/pricing/>
51. "Why we no longer evaluate SWE-bench Verified" (2026-02-23) — <https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/>
52. "Separating signal from noise in coding evaluations" — <https://openai.com/index/separating-signal-from-noise-coding-evaluations/>
53. GPT-5.6 Sol 프리뷰 (2026-06-26) — <https://openai.com/index/previewing-gpt-5-6-sol/>
54. GPT-5.3-Codex 발표 (2026-02-05) — <https://openai.com/index/introducing-gpt-5-3-codex/>

**확인하지 못한 항목 (정직하게 남김)**

- **ChatGPT Free / Go / Plus 월 요금** — `openai.com/chatgpt/pricing` 과 `chatgpt.com/pricing` 이 자동 fetch 를 403 으로 차단하고, 렌더된 텍스트에서 달러 값이 제거됨.
- **양측 최신 세대의 절대 벤치마크 점수** — 발표문 본문에 숫자가 없고 차트 이미지로만 존재. 텍스트로 확인 불가한 수치는 인용하지 않음.
- **SWE-bench Verified 점수** — 두 벤더 모두 최신 세대에 대해 공개하지 않음 (OpenAI 는 명시적 중단 선언, Anthropic 은 벤치 세트 교체).
- **Codex CLI 체인지로그** — `learn.chatgpt.com/docs/changelog.md` 404. 문서에 등장하는 유일한 버전 앵커는 permission profile 관련 "Codex 0.138.0 or later".
- **Claude Code 최신 버전의 릴리스 날짜** — CHANGELOG 최상단은 2.1.226 이나 날짜 표기가 없음. setup 문서 예시는 2.1.211 로 문서 간 시차가 있음.
- **Slack 통합 상세 (Codex)** — 여러 문서에서 언급되나 전용 페이지를 찾지 못함.
