---
layout: post
title: "Hermes Agent vs OpenClaw: 구조 및 사용법 비교"
date: 2026-10-04 09:00:00 +0900
categories: [Agent Comparison, SRE]
---

Hermes Agent(Nous Research)와 OpenClaw은 모두 자율적인 AI 코딩 에이전트로, 도구 호출을 통해 로컬 시스템과 상호작용합니다. 두 프레임워크는 설계 철학과 제공하는 기능에서 유사점과 차이점을 갖습니다. 본 글은 각 에이전트의 아키텍처, 핵심 특징, 사용법(CLI, 설정, 스킬, 멀티에이전트 조율) 등을 사실 기반으로 비교합니다.

## 1. 아키텍처 개요

### Hermes Agent
- **핵심 철학**: "기억은 가이드일 뿐, Trace가 진실이다." 모든 결론은 런타임 트레이스, 로그, 소스 코드 등에 기반해야 함【hermes-agent】.
- **구성 요소**: CLI, Ink TUI, 네이티브 데스크톱 앱, 웹 대시보드, ACP 서버(IDE 통합), 다중 플랫폼 게이트웨이(Telegram, Discord 등)【hermes-agent】.
- **확장 방식**: 스킬(Skill)을 통한 절차적 메모리, 플러그인, MCP 서버, 데스크톱 UI 플러그인, TUI 위젯, 퍼스널 메모리 백엔드 등【hermes-agent】.
- **모델 제공자 무관함**: OpenRouter, Anthropic, OpenAI, Google, DeepSeek, xAI, 로컬 모델 등 20+ 제공자를 지원하며, 실행 중에도 교체 가능【hermes-agent】.
- **프로파일**: 독립적인 설정, 세션, 스킬, 메모리를 가진 다중 인스턴스 실행 가능【hermes-agent】.

### OpenClaw
- **내장 런타임**: `openclaw`라는 내장 에이전트 런타임을 소유하며, 모델/프로바이더 정규화, 세션 관리, 스킬/테마/TUI 도구 렌더링 등을 담당【web_search:0】.
- **작업 공간(Workspace)**: 각 에이전트는 단일 작업 디렉터리를 가지며, 거기에는 `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `BOOTSTRAP.md`, `MEMORY.md` 등이 배치됨【web_search:3】.
- **런타임 정책**: 모델/프로바이더 스코프에서 `agentRuntime.id` 설정을 통해 내장 런타임(`openclaw`) 또는 플러그인 등록 런타임(예: `codex`) 중 선택 가능【web_search:0】.
- **플러그인 시스템**: 플러그인은 문서화된 `openclaw/plugin-sdk/*` 엔트리포인트만 사용하며, 소스 코드(`src/**`)를 직접 import하지 않음【web_search:0】.

## 2. 핵심 특징 비교

| 항목 | Hermes Agent | OpenClaw |
|------|--------------|----------|
| **메모리·컨텍스트** | 세션 간 지속 메모리, 사용자 프로필, 환경 사실 저장. 스킬에 절차적 지식 저장【hermes-agent】 | 첫 턴에 작업 공간 파일을 시스템 프롬프트에 주입. 세션 행은 per-agent SQLite에 저장【web_search:3】 |
| **도구 호출** | 내장 도구(terminal, read_file, web_search 등)와 스킬을 통한 커스텀 도구. 도구 사용은 필수이며, 설명만으로는 불충분【hermes-agent】 | 내장 도구 목록(셸 명령, 파일 시스템, 웹 브라우징, 메시징 플랫폼 등)과 플러그인을 통한 확장【web_search:0】 |
| **멀티에이전트 조율** | `delegate_task`로 서브에이전트 생성(격리된 컨텍스트, 자체 터미널 세션). 또는 전체 Hermes 프로세스를 tmux 등으로 스폰하여 독립 실행【hermes-agent】 | 멀티에이전트 라우팅을 지원하며, 각 에이전트는 자체 작업 공간과 세션을 가짐【web_search:3】 |
| **설정 관리** | `config.yaml`(설정)와 `.env`(비밀). 변경은 `hermes config set` 명령으로 강제 (수동 편집 금지)【hermes-agent】 | 설정은 likely YAML/JSON 형태이나, 구체적인 방법은 문서에서 확인 필요 (본 글 범위 외) |
| **보안·시크릿 처리** | 시크릿은 `.env`에만 저장하고 출력 금지. 로그·출력에서 자동 마스킹 및 `[REDACTED]` 처리 강제【hermes-agent】 | 보안 분석 문서 존재하지만, 구체적 시크릿 처리 방식은 본 글 범위 외【web_search:4】 |
| **임베디드 vs 게이트웨이 모드** | `--worktree`로 격리된 git 워크트리 모드 제공. 또한 `hermes chat -q`로 일회성 쿼리, 백그라운드 데몬 실행 가능【hermes-agent】 | `openclaw agent exec`는 게이트웨이 없이 한 번의 에이전트 턴을 실행하며, CI/CD에 적합【web_search:2】 |

## 3. 사용법 (CLI 중심)

### Hermes Agent 기본 사용법
- **대화형 채팅**: `hermes` (기본값: 클래식 REPL, `--tui`로 Ink TUI)【hermes-agent】.
- **단일 쿼리(스크립트용)**: `hermes chat -q "질문 내용"`【hermes-agent】.
- **설정 Wizard**: `hermes setup` (모델, TTS, 터미널, 게이트웨이, 도구, 에이전트 중 선택)【hermes-agent】.
- **모델/프로바이더 교체**: `hermes model` 인터랙티브 피커 또는 플래그 `-m MODEL --provider P`【hermes-agent】.
- **폴백 체인 관리**: `hermes fallback [add|remove|list]`【hermes-agent】.
- **스킬 관리**: 
  - 목록: `hermes skills list`
  - 설치: `hermes skills install <Hub ID 또는 URL>`
  - 활성화/비활성화: `hermes skills enable <NAME>` / `disable`
  - 업데이트: `hermes skills update`
- **게이트웨이(메시징 플랫폼) 실행**: `hermes gateway run` (Telegram, Discord 등 20+ 플랫폼 지원)【hermes-agent】.
- **크론 작업**: `hermes cron create "0 9 * * *" hermes chat -q "일일 브리핑 생성"` 형태.
- **웹훅**: `hermes webhook subscribe <NAME>` (payload/path 상세는 `references/webhooks.md`)【hermes-agent】.
- **MCP 서버**: `hermes mcp add <NAME> --url <URL>` 혹은 `--command <CMD>`로 추가, `hermes mcp serve`로 Hermes 자신을 MCP 서버로 실행 가능【hermes-agent】.

### OpenClaw 기본 사용법 (참고)
- **내장 런타임 실행**: `openclaw agent exec` – 게이트웨이 연결 없이 한 번의 턴 실행 (CI 적합)【web_search:2】.
- **워크스페이스 준비**: 에이전트별 디렉터리에 필수 파일(`AGENTS.md`, `SOUL.md` 등) 배치 후 실행【web_search:3】.
- **플러그인 등록**: `openclaw/plugin-sdk/*`를 통해 허브 런타임 ID 추가 가능 (예: `codex`)【web_search:0】.
- **세션 관리**: 세션은 `~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite`에 저장【web_search:3】.

## 4. 멀티에이전트 조율 사례

### Hermes Agent
- **서브에이전트 경량 작업**: `delegate_task`로 목표와 컨텍스트를 전달해 독립된 대화에서 서브태스크 수행. 결과는 요약 툴콜만 반환.
- **완전 독립 인스턴스**: `tmux new-session -d -s agent1 'hermes'` 후 `tmux send-keys`로 메시지 전달, `tmux capture-pane`로 출력 확인. 에이전트 간 컨텍스트 연동은 수동으로 전달 필요【hermes-agent】.
- **작업 트리(mode)**: `-w` 플래그로 격리된 git 워크트리에서 작업해 병렬 에이전트 간 충돌 방지【hermes-agent】.

### OpenClaw
- **멀티에이전트 라우팅**: 각 에이전트는 설정에서 `agentRuntime.id` 등을 달리해 별도 러타임 사용 가능. 작업 공간과 세션은 완전히 격리됨【web_search:3】.
- **채널 시스템**: 중앙 게이트웨이를 통해 다양한 메시징 플랫폼(Telegram, Slack 등)과 연결 가능하며, 플러그인을 통한 확장 가능【web_search:4】.

## 5. 보안 및 운영 모범 사례

Hermes Agent에서 강조하는 운영 원칙은 다음과 같습니다【hermes-agent】:
- **증거 우선(Evidence First)**: 모든 결론은 트레이스 > 로그 > 소스 코드 > 구성 > 문서 > 메모리 > 추측 순으로 검증.
- **TraceGuard**: 결론 내리기 전 반드시 관련 트레이스, 코드, 로그를 확인.
- **자동화의 미학**: 반복 작업은 스크립트, 파이프라인, CI/CD, 에이전트 등으로 자동화.
- **멱등성**: 동일 명령 반복 실행 시 동일한 결과를 보장하려 시도 (중복 실행으로 데이터/설정 오염 방지).
- **시크릿 처리**: 절대 시크릿을 저장하거나 출력하지 않으며, `[REDACTED]`로 마스킹.

OpenClaw도 보안 분석 문서가 존재하며, 채널·게이트웨이·플러그인·런타임 등으로 구조화되어 있으나, 구체적인 운영 매뉴얼은 본 글에서 다룰 수 없음【web_search:4】.

## 6. 요약

| 구분 | Hermes Agent | OpenClaw |
|------|--------------|----------|
| **주요 강점** | 지속 메모리·스킬 기반 자기 개선, 다중 플랫폼 게이트웨이, 모델 제공자 자유 전환, 엄격한 증거 기반 운영 철학 | 내장 런타임의 단순함, 작업 공간 기반 컨텍스트 주입, 게이트웨이 독립 실행 옵션(CI 친화적), 플러그인 격리 구조 |
| **적합 시나리오** | 장기 자율 미션, 복잡한 멀티에이전트 워크플로우, 다양한 메시징 플랫폼 연동 필요 시 | 빠른 일회성 작업, 내장 런타임만으로 충분한 환경, 플러그인 기반 경량 확장 원하는 경우 |
| **운영 철학** | Trace as Truth, 증거 기반 의사결정, 자동화 우선, 시크릿 절대 노출 금지 | (문서 내 보안 설계 존재) 구체적인 운영 가이드는 별도 참조 필요 |

두 에이전트는 자율 AI 에이전트라는 공통 목표를 달성하기 위해 서로 다른 설계 트레이드오프를 취합니다. Hermes는 메모리·스킬·게이트웨이를 통한 확장성과 운영 엄격함에 초점을 두었고, OpenClaw는 내장 런타임의 단순함과 작업 공간 기반 컨텍스트 모델에 주목합니다. 실제 운영 환경에서는 사용 목적과 기존 인프라에 맞춰 선택하거나, 두 시스템의 좋은 점을 혼합한 하이브리드 접근도 고려해볼 만합니다.

---
*참고 문서*
1. Hermes Agent Skill 및 참조 파일 (`~/.hermes/skills/autonomous-ai-agents/hermes-agent/*`)【hermes-agent】.
2. OpenClaw 문서: Agent Runtime Architecture, CLI agent page, Session storage, Security analysis【web_search:0】【web_search:2】【web_search:3】【web_search:4】.