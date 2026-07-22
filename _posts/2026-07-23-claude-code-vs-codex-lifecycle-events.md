---
layout: post
title: "훅으로 보는 하네스의 깊이 — Claude Code vs Codex 라이프사이클 이벤트 비교"
date: 2026-07-23 07:05:00 +0900
categories: [AI, Architecture]
tags: [ClaudeCode, Codex, Hooks, LifecycleEvents, HarnessEngineering, CodeOverPrompts, Determinism]
---

# 하네스의 "이음새"가 곧 통제력이다

두 AI 코딩 하네스를 라이프사이클 이벤트(훅) 로 나란히 놓으면, 겉으로 안 보이던 설계 철학의 차이가 드러난다. 아래 표는 Claude Code와 Codex가 각 생애 단계에서 노출하는 훅 이벤트를 비교한 것이다.

![Claude Code vs Codex 라이프사이클 이벤트 비교표 — 세션 시작/종료, 프롬프트 제출, 도구 호출 전후, 작업 종료, 서브에이전트, 컨텍스트 압축, 파일·설정 변경 단계별로 두 하네스가 노출하는 훅 이벤트 대조](/assets/images/claude-code-vs-codex-lifecycle-events.jpg)

한눈에 보이는 사실 하나: **Claude Code 열은 촘촘하고, Codex 열은 성기다.** 서브에이전트·컨텍스트 압축·파일/설정 변경 같은 단계에서 Codex는 "현재 별도 이벤트 없음"이다. 이 성김과 촘촘함이 뜻하는 바가 이 글의 주제다.

---

## 라이프사이클 이벤트란 무엇인가

라이프사이클 이벤트는 하네스가 **"지금 이 순간이 왔다"고 알려주는 지점**이고, 훅(hook)은 그 지점에 붙이는 *결정론적 코드*다. 프롬프트(CLAUDE.md)가 에이전트가 *따르려 노력*하는 지시라면, 훅은 이벤트가 발생하는 순간 *구조적으로 실행*되는 강제다. 그래서 이벤트가 많다는 것은 곧 **"강제를 걸 수 있는 이음새(seam)가 많다"**는 뜻이다.

이 관점은 [어제 정리한 Ouroboros 코드 분석](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)의 결론과 정확히 맞닿는다 — *중요한 규칙일수록 프롬프트(확률적)에서 코드(결정론적)로 옮겨야 한다.* 라이프사이클 이벤트는 그 "코드로 옮기기"가 물리적으로 가능한 자리의 목록이다.

---

## Claude Code — 30개의 이음새

Claude Code 공식 문서 기준으로 훅 이벤트는 **총 30개**이며, 발화 주기(cadence) 별로 묶으면 이렇게 정리된다. (아래는 이미지의 Claude Code 열을 공식 목록으로 확장한 것이다.)

| 주기 | 이벤트 |
|---|---|
| 세션당 1회 | `SessionStart` · `Setup` · `SessionEnd` |
| 턴당 1회 | `UserPromptSubmit` · `UserPromptExpansion` · `Stop` · `StopFailure` |
| 도구 호출 루프 | `PreToolUse` · `PermissionRequest` · `PermissionDenied` · `PostToolUse` · `PostToolUseFailure` · `PostToolBatch` |
| 서브에이전트·태스크 | `SubagentStart` · `SubagentStop` · `TaskCreated` · `TaskCompleted` · `TeammateIdle` |
| 컨텍스트 압축 | `PreCompact` · `PostCompact` |
| 환경·파일·설정 | `FileChanged` · `CwdChanged` · `ConfigChange` · `InstructionsLoaded` · `WorktreeCreate` · `WorktreeRemove` |
| UI·MCP 상호작용 | `Notification` · `MessageDisplay` · `Elicitation` · `ElicitationResult` |

이미지에 담긴 이름들 — `Setup`, `UserPromptExpansion`, `PermissionRequest`/`PermissionDenied`, `PostToolUseFailure`, `PostToolBatch`, `StopFailure`, `TeammateIdle`, `SubagentStart`, `TaskCreated`/`TaskCompleted`, `PostCompact`, `FileChanged`/`CwdChanged`/`ConfigChange` — 은 전부 실제 공식 이벤트다. 특히 눈여겨볼 세 묶음:

- **실패를 별도 이벤트로 분리** — `PostToolUse`(성공) vs `PostToolUseFailure`(실패), `Stop`(정상 종료) vs `StopFailure`(API 오류 종료). 성공과 실패에 다른 대응을 걸 수 있다.
- **병렬·서브에이전트 관측** — `PostToolBatch`(병렬 도구 호출이 다 끝난 뒤), `SubagentStart/Stop`, `TeammateIdle`(에이전트 팀원이 유휴로 전환 직전). 멀티 에이전트 실행의 이음새가 노출돼 있다.
- **환경 변화 감지** — `FileChanged`(감시 파일 변경), `CwdChanged`(작업 디렉터리 변경), `ConfigChange`(설정 파일 변경), `InstructionsLoaded`(CLAUDE.md/rules 로드). 세션 밖에서 상태가 바뀌는 순간까지 잡는다.

---

## Codex — 의도적으로 성긴 표면

Codex는 이미지 기준으로 `SessionStart` · `UserPromptSubmit` · `PreToolUse` · `PermissionRequest` · `PostToolUse` · `Stop` 정도의 **핵심 골격만** 노출하고, 서브에이전트·컨텍스트 압축·파일 변경 계열은 "현재 별도 이벤트 없음"이다. 실제로 로컬 `~/.codex/hooks.json`을 봐도 훅 키는 `session_start` · `user_prompt_submit` · `pre_tool_use` 수준의 소수다.

이건 결함이라기보다 **철학의 차이**다. Codex는 얇고 예측 가능한 코어를 지향하고, Claude Code는 하네스 자체를 세밀하게 계측·제어할 수 있는 넓은 표면을 지향한다. 앞서 하네스 비교글에서 적었듯 — 겹쳐 쓰는 게 아니라 주축을 고르는 문제이고, "얼마나 많은 이음새가 필요한가"는 워크로드가 답한다.

---

## 그래서 이 촘촘함으로 무엇을 하나

이벤트가 많다는 건 곧 "이 순간에 결정론적 규칙을 끼울 수 있다"는 뜻이다. 대표적 활용:

| 이벤트 | 걸 수 있는 결정론적 규칙 |
|---|---|
| `PreToolUse` | 위험 명령 차단(보호 경로·파괴적 타겟 거부) — *AI 판단에 맡기지 않는 게이트* |
| `PostToolUse` / `PostToolUseFailure` | 편집 후 자동 린트·포맷 / 실패 시 자동 로깅·복구 |
| `UserPromptSubmit` | 컨텍스트 주입(현재 시각·정책·용어집) |
| `PreCompact` | 압축 전 중요 상태를 파일로 flush — 컨텍스트 유실 방어 |
| `FileChanged` / `ConfigChange` | 외부 변경 감지 시 재검증 트리거 |
| `SubagentStop` / `PostToolBatch` | 병렬 작업이 끝난 경계에서 취합·검증 |

내 실제 `~/.claude/settings.json`도 이미 이 원리로 돌아간다 — `PreToolUse`에 위험 명령 검사, `PostToolUse`(Write/Edit)에 자동 포맷, `UserPromptSubmit`에 날짜 주입을 걸어 뒀다. 훅은 "에이전트가 잘해주길 바라는" 영역을 "구조가 보장하는" 영역으로 옮기는 도구다.

---

## 한 줄 결론

라이프사이클 이벤트의 개수는 단순한 기능 목록이 아니라 **하네스가 허용하는 결정론적 통제의 해상도**다. Claude Code의 30개 이음새는 "프롬프트로 부탁할 것 vs 코드로 강제할 것"의 경계를 훨씬 촘촘하게 그을 수 있게 해준다. 감독이 줄어드는 자율 실행일수록, 이 이음새에 건 훅이 사람 대신 감독한다.

---

## 출처

- 첨부 비교표: 사용자 제공 이미지(Claude Code vs Codex 라이프사이클 이벤트).
- Claude Code 훅 이벤트 30종(공식): **Claude Code Hooks 공식 문서** — <https://code.claude.com/docs/en/hooks> (이미지의 Claude Code 열 이벤트명은 이 문서로 전부 실재 확인).
- Codex 훅 표면: 공개 문서가 얇아 이 글에서는 이미지의 비교 + 로컬 `~/.codex/hooks.json`의 실제 훅 키(`session_start`·`user_prompt_submit`·`pre_tool_use`)를 근거로만 기술했다. 세부는 Codex 버전에 따라 다를 수 있다.
