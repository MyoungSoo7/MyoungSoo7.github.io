---
layout: post
title: "Harness Engineering ① AI Agent 의 진짜 능력은 *모델* 이 아니라 *Harness* 가 결정한다 — Claude Code 해부"
date: 2026-05-29 01:10:00 +0900
categories: [ai, agent, infrastructure]
tags: [harness, ai-agent, claude-code, llm, agentic, mcp, hooks, skills, tool-use, context-management]
---

> 이 글은 "Harness Engineering 의 4 가지 얼굴" 시리즈의 1 편. 다른 편: [② Test Harness]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %}) / [③ Software Engineering Harness]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %}) / [④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})

2024 년까지의 AI 담론은 *어느 모델이 더 똑똑한가* 에 머물러 있었다. 2025 년 이후 진짜 화두는 다음으로 옮겨갔다:

> **"같은 모델을 쓰는 두 agent 의 능력이 *왜 그렇게 다른가?*"**

답은 *harness* 다. **모델은 두뇌, harness 는 두뇌가 일하는 환경**. 환경이 좋으면 평범한 두뇌도 잘 일하고, 환경이 나쁘면 천재 두뇌도 아무것도 못 한다.

이 글은 Claude Code 의 harness 를 *해부* 해서 *AI agent harness engineering 의 일반 원리* 를 추출한다. 내가 이 글을 쓰고 있는 *지금 이 순간* 의 시스템도 이 harness 위에서 돌고 있다.

---

## TL;DR — AI Agent Harness 의 7 가지 책무

| # | 책무 | Claude Code 의 구현 |
|---|---|---|
| 1 | **컨텍스트 관리** | 자동 압축, file state tracking, 1M context window |
| 2 | **Tool 정의 & 실행** | Bash / Read / Edit / Write / 70+ MCP tools |
| 3 | **권한 관리** | settings.json + 사용자 prompt 승인 |
| 4 | **확장성** | Skill / Agent / Hook / MCP 4 가지 확장점 |
| 5 | **Observability** | 로그 / telemetry / 모든 tool call 추적 |
| 6 | **실패 회복** | Retry / rollback / 사용자 개입 지점 |
| 7 | **외부 시스템 통합** | MCP (Model Context Protocol) 표준 |

---

## 0. *모델* 만 좋다고 안 되는 이유

같은 모델 (예: Claude Opus 4.7) 을 사용하는 두 agent:

- **Agent A**: 단순 chatbot UI — 텍스트만 주고받음
- **Agent B**: Claude Code — 파일 읽기/쓰기, Bash 실행, MCP 도구, hook, skill

같은 *모델* 인데 능력은 *10 배* 차이. 왜?

| 차원 | Agent A | Agent B |
|---|---|---|
| 코드를 *읽을 수 있나* | ❌ (붙여넣기만) | ✅ (Read 도구) |
| 코드를 *고칠 수 있나* | ❌ | ✅ (Edit/Write) |
| 명령어를 *실행할 수 있나* | ❌ | ✅ (Bash) |
| 외부 시스템과 *연동* | ❌ | ✅ (MCP) |
| 사용자 *환경 학습* | ❌ | ✅ (memory + CLAUDE.md) |
| *연속된 작업* | 매 대화 reset | ✅ (1M context + tasks) |

같은 모델, *전혀 다른 agent*. 차이는 모두 *harness* 에서 온다.

---

## 1. 컨텍스트 관리 — Token 은 RAM 이다

LLM 의 컨텍스트 window 는 *agent 의 작업 RAM*. 8K, 32K, 200K, 1M 으로 커져왔지만 *항상 부족* 하다. 좋은 harness 는 *RAM 을 영리하게 사용* 한다.

### Claude Code 의 컨텍스트 전략

1. **자동 압축** — 대화가 한계 근접 시 *이전 메시지를 요약* 으로 압축. 작업 연속성 유지하면서 token 절약
2. **File state tracking** — *읽은 파일은 다시 안 읽어도 됨* (harness 가 캐싱). "Read it back" 같은 비효율 차단
3. **Tool result truncation** — 큰 출력 (e.g. `ls -R /`) 은 *일정 크기 이상이면 잘림*. agent 가 *모든 걸 보려는* 함정 방지
4. **Subagent dispatch** — 큰 탐색은 *별도 agent 에 위임* → 결과만 부모 컨텍스트로 반환

### 일반 원리

```
모델의 컨텍스트 = RAM
파일 시스템 = SSD
DB / 외부 시스템 = HDD
```

좋은 agent 는 *RAM 에 항상 모든 걸 올리지 않는다*. *Just-in-time fetch* + *유효 기간 짧은 요약* + *대용량은 외부 위임* 패턴.

---

## 2. Tool 정의 & 실행 — JSON Schema 가 한계를 정한다

LLM 은 *자연어로 의도* 를 말할 수 있지만, *외부 시스템에 영향* 을 주려면 구조화된 *Tool Call* 이 필요. 이건 표준화돼있다 — JSON Schema 로 tool 정의.

### Claude Code 의 핵심 Tool

```json
{
  "name": "Edit",
  "parameters": {
    "file_path": "string (absolute path)",
    "old_string": "string (must be unique in file)",
    "new_string": "string"
  },
  "rules": [
    "Must Read file before Edit",
    "old_string must be unique or use replace_all",
    "Preserve exact indentation"
  ]
}
```

핵심 관찰:
- *명령 (verb)* 이 아니라 *파라미터 (noun)* 가 도구의 본질
- *유효성 규칙* 이 tool description 에 자연어로 들어가있음 → 모델이 *읽고 따름*
- *명확한 단일 책임* — Edit 은 *수정만*, Read 와 분리

### Tool 설계의 함정 3가지

❌ **너무 많은 파라미터** → 모델이 헷갈림. 5 개 이하 권장
❌ **모호한 description** → "사용자 정보 가져오기" (어떤 사용자? 무엇 가져옴?)
❌ **하나의 tool 이 너무 많은 일** → "doEverything(args)" 안티패턴. 분리해라

### MCP — Tool 표준화

**MCP (Model Context Protocol)** 는 Anthropic 이 2024 년 공개한 표준. *Tool 정의 + 실행 프로토콜* 을 표준화해, 어느 agent 든 어느 MCP 서버든 연결 가능.

내 Claude Code 환경에 연결된 MCP 서버 일부:
- `mcp__claude_ai_Slack__*` — Slack 통합
- `mcp__claude_ai_Notion__*` — Notion 페이지 조작
- `mcp__claude_ai_Supabase__*` — DB 작업
- `mcp__plugin_telegram_telegram__*` — Telegram 채널 (이 글의 chat 도 이걸로 옴)

각 MCP 서버는 *별도 프로세스* 로 실행, *stdio 또는 SSE* 로 agent 와 통신. *언어 무관* — Python / Go / TypeScript / Rust 다 가능.

---

## 3. 권한 관리 — Agent 가 어디까지 자기 멋대로 해도 되나

Tool 호출 = *외부 시스템 변경*. *얼마나 자유롭게* 허용할지가 핵심 설계 결정.

### Claude Code 의 권한 모델

```jsonc
// settings.json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(npm test)",
      "Read(~/projects/**)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl * | sh)"
    ],
    "ask": [
      "Bash(git push *)",   // 매번 사용자 승인
      "Write(/etc/**)"
    ]
  }
}
```

3 단계 권한:
- **allow** → 자동 실행
- **ask** → 사용자에게 매번 물음
- **deny** → 거부

### 일반 원리: *Principle of Least Privilege*

Agent 는 *그 작업에 필요한 최소* 권한만 가져야 함. 좋은 harness 는:
1. *기본 deny*, 명시 allow
2. *Read 는 자유*, *Write 는 신중*, *외부 호출은 ask*
3. *Production 시스템 변경* 은 *항상 명시 승인*

내 환경에서 `git push origin main` 같은 명령은 *항상 ask*. 단 `git push origin <feature-branch>` 같은 feature 브랜치 push 는 *allow*. 이 정밀도가 *agent 가 production 안전* 을 지키는 핵심.

---

## 4. 확장성 — 4 가지 확장점

Claude Code 의 *확장성* 은 4 가지 메커니즘으로 설계됨:

### Skill — 재사용 가능한 *작업 패턴*

```markdown
# .claude/skills/security-review.md
---
name: security-review
description: Complete a security review of the pending changes on the current branch
---

## When to use
PR 작성 전, 보안 위험 점검 필요할 때

## Steps
1. `git diff main...HEAD` 로 변경 확인
2. OWASP Top 10 항목별 검토 ...
```

LLM 이 자연어로 *skill 호출* → harness 가 *그 markdown 의 instructions* 를 컨텍스트에 주입.

### Agent — 특정 작업의 *전문 worker*

```yaml
# .claude/agents/security-auditor.md
name: security-auditor
description: OWASP audits, secret hunting, IDOR detection
tools: [Read, Write, Edit, Bash, Grep, Glob]
```

부모 agent 가 *복잡한 작업을 위임* 가능. Subagent 는 *자기 컨텍스트* 로 작업, 결과만 부모에 반환.

### Hook — 이벤트 기반 *자동 트리거*

```jsonc
// settings.json
{
  "hooks": {
    "UserPromptSubmit": "/usr/local/bin/date-stamp.sh",
    "PostToolUse": "/usr/local/bin/lint-check.sh"
  }
}
```

Tool 호출 *전/후*, 사용자 prompt *제출 시* 등 이벤트에 shell 명령 자동 실행. *agent 자체 변경 없이* 환경 커스터마이즈.

### MCP — *외부 시스템 통합* 의 표준

위에서 설명. 회사 내 SaaS, 사내 시스템과 *언어 무관 통합* 가능.

이 4 가지가 *Claude Code 의 진짜 가치*. 모델은 *기본기*, 확장점들이 *팀별 맞춤화* 의 layer.

---

## 5. Observability — 모든 Tool Call 이 기록된다

좋은 harness 는 *agent 가 무엇을, 언제, 왜 했는지* 모두 기록한다. 사용자가 *나중에 검토* + *비용 추적* + *실패 디버깅* 가능.

### 기록되는 것

```
Timestamp    | Tool          | Input                          | Output  | Status
─────────────┼───────────────┼────────────────────────────────┼─────────┼────────
00:35:01.122 | Read          | /Users/lms/.zshrc              | 1.2KB   | OK
00:35:02.844 | Bash          | git status                     | (8 lines) | OK
00:35:03.901 | Edit          | /Users/lms/foo.py              | -2 +5   | OK
00:35:04.567 | mcp__telegram | reply(chat_id=..., text=...)   | (id 6783) | OK
```

이 로그는:
- *사용자 검토* — agent 가 뭘 했는지 확인
- *비용 추적* — tool call 수 × 모델 호출 token
- *실패 분석* — 어디서 reasoning 이 잘못됐는지
- *재현성* — 같은 입력으로 *동일 동작 재현* 가능

### Telemetry — 잘못된 결정 패턴 학습

Anthropic 은 *집계된 telemetry* 로 agent 의 *흔한 실패 패턴* 을 학습 → 다음 모델 학습 데이터로 사용. 이게 *harness 가 모델 발전에 기여* 하는 루프.

---

## 6. 실패 회복 — Agent 도 실수한다, harness 가 받쳐줘야

실수의 종류:
- Tool 호출 실패 (네트워크, 권한, 잘못된 input)
- 모델 reasoning 실수 (잘못된 파일 경로, 의도 misunderstand)
- 외부 시스템 변경 후 *되돌리고 싶을 때*

### Claude Code 의 회복 메커니즘

1. **Tool 실패 → 자동 재시도** (transient error 만)
2. **에러 메시지 → 모델에게 전달** → 모델이 *수정 시도*
3. **Git 기반 rollback** — Edit/Write 작업 후 *git diff* 로 변경 확인, *git checkout* 으로 되돌리기
4. **사용자 개입 지점** — ask 권한, ExitPlanMode, AskUserQuestion 같은 도구로 *agent 가 멈추고 사람에게 물음*

### 일반 원리: *Fail-safe 가 fail-fast 보다 중요*

Agent 가 *실수* 했을 때:
- ❌ 그냥 멈추기 (fail-fast 만)
- ✅ *에러를 모델에 피드백* → 자가 수정 시도
- ✅ *변경 되돌릴 수단* 항상 제공
- ✅ *치명적이면 사용자 개입* 요청

이게 *agent harness 의 안전성* 핵심.

---

## 7. 외부 시스템 통합 — MCP 의 진짜 의미

MCP 가 *Anthropic 만의 표준* 같지만, 사실 *USB-C of AI* 를 노린 보편 표준. 이미 OpenAI, Google Gemini 등이 *MCP 호환* 발표.

### 왜 표준이 중요한가

표준 없으면:
- *Agent A* 는 *Slack* 연동 직접 작성
- *Agent B* 는 *동일한 Slack* 연동 또 작성
- 슬랙 API 변경 시 *둘 다 패치* 필요

표준 있으면:
- *Slack* 이 MCP 서버 한 번 작성
- *모든 agent* 가 자동 연동 가능
- API 변경은 *MCP 서버만* 패치

이건 *OS 의 device driver* 가 hardware 와 OS 의 표준 인터페이스 역할을 한 것과 같음. AI agent 생태계에 *device driver layer* 가 깔린 것.

---

## 8. 내가 매일 쓰는 harness — Claude Code 실전

지금 내가 이 글을 쓰고 있는 *시스템* 자체가 harness engineering 의 산물:

- *Telegram 채널 → Claude 의 inbox* (mcp__plugin_telegram)
- *나의 `/loop` 명령 → 정기 실행* (skill + hook)
- *코드 변경 → ArchUnit 자동 검증* (hook)
- *PR 리뷰 → security-auditor agent 자동 dispatch*
- *블로그 작성 → 이 글이 commit/push 까지 자동*

이 모든 것이 *Claude Code 의 harness* 없으면 불가능. *모델* 한테 "Telegram 으로 답해" 라고만 해선 안 됨 — *MCP 서버, hook, skill, agent* 의 합주로 가능.

---

## 결론 — Harness Engineering 은 *비가역적 추세*

AI Agent 의 미래는:
- *모델은 commodity* 화 (Opus, GPT, Gemini 가 비슷한 수준으로 수렴)
- *Harness 가 차별화* (어느 agent 가 어떤 도구 / 권한 / 메모리 / 확장점을 잘 설계했는가)

이건 *클라우드 시대의 AWS vs GCP vs Azure* 와 동일한 패턴. *VM (모델)* 이 commodity 화 되고 *플랫폼 서비스 (harness)* 가 차별화.

Backend 엔지니어가 *백엔드 시스템* 만들 듯, AI 엔지니어가 *agent harness* 를 만든다. 둘은 본질적으로 같은 일 — *비즈니스 로직 (LLM 의 reasoning) + 인프라 (tool, 권한, observability)* 를 *시스템* 으로 묶는 일.

다음 편: [② Test Harness — JUnit/Mockito/Testcontainers]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %})

---

## 참고

- Anthropic, [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (2024)
- Anthropic, [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude Code Docs](https://docs.claude.com/en/docs/claude-code)
- 시리즈 다른 편:
  - [② Test Harness — JUnit/Mockito/Testcontainers]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %})
  - [③ Software Engineering Harness — 개발자 toolchain]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %})
  - [④ Deployment Harness — CI/CD + GitOps]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
