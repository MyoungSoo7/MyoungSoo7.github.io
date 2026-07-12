---
layout: post
title: "에이전트 규약의 표준화: Claude Code와 Codex 비교 분석"
date: 2026-07-13 10:00:00 +0900
categories: [AI, Agents]
tags: [ClaudeCode, Codex, Automation, TaskHarness]
---

# 에이전트 운영 규약의 표준화: Claude Code와 Codex 비교

최근 자율 AI 에이전트를 실무에 도입하면서 가장 큰 고민은 **"도구마다 다른 설정과 동작 방식을 어떻게 통일할 것인가"**였습니다. 

Claude Code와 Codex는 각각 강력한 도구이지만, 이들을 하나의 워크플로우로 묶으려면 공통된 인터페이스와 훅(Hook) 구조가 필요합니다. 제가 구축 중인 **Task Harness** 체계에서 두 런타임이 어떻게 매핑되는지 정리해 보았습니다.

## 📊 구성 체계 비교표

![Agent Runtime Comparison](/assets/images/posts/agent-runtime-comparison.jpg)

| 역할 | Claude Code | Codex |
| :--- | :--- | :--- |
| **세션 시작 규약 주입** | `.claude/settings.json` (SessionStart) | `.codex/hooks.json` (SessionStart) |
| **세션 시작 Hook** | `.claude/hooks/session_start.py` | `.codex/hooks/session_start.py` |
| **Handoff 사후 검수** | `PostToolUse(Write\|Edit)` | `PostToolUse(Edit\|Write\|apply_patch)` |
| **Review Gate Hook** | `.claude/hooks/review_gate.py` | `.codex/hooks/review_gate.py` |
| **Sub Agent (Ask)** | `.claude/agents/ask.md` | `.codex/agents/ask.toml` |
| **Sub Agent (Build)** | `.claude/agents/build.md` | `.codex/agents/build.toml` |
| **Sub Agent (Review)** | `.claude/agents/review.md` | `.codex/agents/review.toml` |
| **Meta Skill** | `using-task-harness/SKILL.md` | `using-task-harness/SKILL.md` |
| **상태판 (Status)** | `state/run-log.md` | `state/run-log.md + harness-state.md` |

## 🧐 주요 차이점 및 인사이트

1. **파일 포맷의 차이**: Claude Code는 에이전트 정의에 Markdown(`.md`)을 선호하는 반면, Codex는 구조화된 TOML(`.toml`)을 사용합니다. 이는 각 모델이 문맥을 이해하는 방식의 선호도를 반영합니다.
2. **사후 검수(Post-Inspection)**: Codex는 `apply_patch` 도구 사용 후에도 별도의 검수 훅을 두어 코드 변경의 안전성을 더 꼼꼼하게 체크하도록 설계했습니다.
3. **상태 관리**: Codex는 `harness-state.md`를 추가로 운영하여, 복잡한 재귀 작업 중에도 현재 에이전트의 위치와 남은 과업을 더 정밀하게 추적합니다.

## 🚀 결론
결국 에이전트의 성능만큼 중요한 것은 **에이전트를 통제하고 가이드하는 프레임워크**입니다. 이러한 표준화된 훅 구조를 통해 에이전트가 바뀌더라도 일관된 작업 품질을 유지할 수 있습니다.
