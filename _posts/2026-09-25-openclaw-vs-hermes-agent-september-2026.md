---
layout: post
title: "OpenClaw vs Hermes Agent, 2026년 9월 재비교 — 두 에이전트는 서로를 닮아 가고 있다"
date: 2026-09-25 02:30:17 +0900
categories: [AI]
tags: [OpenClaw, HermesAgent, NousResearch, AI에이전트, 개인비서, 셀프호스팅, AgentSkills, MCP]
---

7월에 [Hermes Agent vs OpenClaw 비교](/2026/07/09/hermes-agent-vs-openclaw-comparison/)를 썼다. 그때의 결론을 한 줄로 줄이면 이랬다.

> **OpenClaw 는 "어디서나 붙는 게이트웨이", Hermes 는 "스스로 배우는 에이전트".**

두 달 반이 지난 지금 공식 문서를 다시 읽어 보면, 이 구분이 흐려지고 있다. 두 프로젝트는 서로의 강점을 가져오면서 **닮아 가고 있다.** 이 글은 2026-09-25 기준 두 프로젝트의 공식 저장소와 문서만 근거로 다시 비교한다.

## 한눈에 비교

| 항목 | OpenClaw | Hermes Agent |
|---|---|---|
| 한 줄 소개 | "Your assistant, on your devices, in your chats" | "The agent that grows with you" |
| 만든 곳 | Peter Steinberger 가 시작, 현재는 OpenClaw Foundation(501(c)(3))이 관리 | Nous Research |
| 라이선스 | MIT | MIT |
| 런타임 | Node.js(24.16+ 또는 26.1+, 26 권장), TypeScript | Python 3.11, uv |
| 설치 | `curl …/install.sh \| bash`, npm, Docker, Nix | `curl …/install.sh \| bash`, Docker 이미지, Nix flake |
| 중심 구조 | 로컬 Gateway 가 세션·도구·채널을 관리하는 제어 평면 | Gateway 백그라운드 프로세스(systemd, launchd 등) + 7종 터미널 백엔드 |
| 최신 릴리스 | v2026.9.6 (2026-09-23) | v0.21.5 (태그 v2026.9.24, 2026-09-24) |
| GitHub 스타 | 약 39만 | 약 24.9만 |

출처: [openclaw/openclaw](https://github.com/openclaw/openclaw), [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). 스타 수와 릴리스는 2026-09-25 기준이다.

OpenClaw 의 이름 변천사도 공식 문서([Lore](https://docs.openclaw.ai/start/lore))에 정리돼 있다. Warelay → Clawd/Clawdbot 순서로 이름이 바뀌었고, 2026년 1월 Anthropic 의 상표 관련 요청을 받은 뒤 1월 27일 Moltbot, 1월 30일 OpenClaw 가 됐다. README 는 재단에 대해 *"OpenAI is a donor, not an owner"* 라고 밝힌다.

## 1. 어디에 붙나 — 채널과 모델

**채널:** 둘 다 텔레그램, 디스코드, 슬랙, 왓츠앱, 시그널, iMessage, 팀즈, 매트릭스, LINE, 위챗 계열까지 폭넓게 지원한다.

- OpenClaw([Channels](https://docs.openclaw.ai/channels))는 Nostr, Twitch, Synology Chat 처럼 **범위가 더 넓다.** 음성 통화 플러그인도 있다. 문서는 봇 토큰만 있으면 되는 텔레그램으로 시작하길 권한다.
- Hermes([Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/))는 이메일, Home Assistant, ntfy, SimpleX 처럼 **자동화·프라이버시 쪽 채널**이 눈에 띈다.

채널 수로는 더 이상 우열을 가리기 어렵다. 쓰는 메신저가 양쪽 목록에 다 있을 가능성이 높다.

**모델:** 둘 다 주요 상용 API(OpenAI, Anthropic, Gemini, xAI, Moonshot 등)와 로컬 모델(Ollama, LM Studio 등)을 지원한다.

- Hermes([Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers))는 자사 Nous Portal OAuth 를 "권장" 경로로 두고, 중국계 모델(DeepSeek, DashScope, Xiaomi MiMo, Tencent, StepFun)까지 목록이 길다.
- OpenClaw([Model providers](https://docs.openclaw.ai/concepts/model-providers))는 모델과 에이전트 하네스를 **"교체 가능한 플러그인"** 으로 다룬다.

## 2. 기억 — 둘 다 Markdown 파일, 규모는 다르다

두 프로젝트 모두 기억을 **사람이 읽을 수 있는 Markdown 파일**로 둔다. `MEMORY.md`(장기 기억)와 `USER.md`(사용자 모델)라는 파일명까지 같다.

| | OpenClaw ([Memory](https://docs.openclaw.ai/concepts/memory)) | Hermes ([Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)) |
|---|---|---|
| 위치 | `~/.openclaw/workspace` | `~/.hermes/memories/` |
| 파일 | `USER.md`, `MEMORY.md`, 일별 노트 `memory/YYYY-MM-DD.md`, `DREAMS.md` | `MEMORY.md`(2,200자 ≈ 800토큰), `USER.md`(1,375자 ≈ 500토큰) |
| 검색 | SQLite 기반 키워드·벡터·하이브리드 검색 | 과거 세션 전체를 SQLite FTS5 로 검색(`session_search`) |
| 정리 방식 | "Dreaming": cron 으로 도는 백그라운드 정리가 기본으로 켜져 있음 | 턴 뒤에 도는 "self-improvement review" |
| 외부 연동 | Honcho, LanceDB 플러그인 | Honcho, Mem0, Supermemory 등 7종 번들 |

설계 철학이 드러나는 부분이다.

- OpenClaw 는 *"there is no hidden state"* 를 내세우며 **많이 적고 검색**한다.
- Hermes 는 핵심 기억을 **작게 유지해서 매 세션 프롬프트에 통째로** 넣는다. 나머지는 세션 검색으로 꺼낸다.

## 3. 스킬 — 가장 크게 수렴한 지점

7월 글에서 Hermes 의 결정적 차별점은 **학습 루프**였다. 복잡한 작업을 끝내면 에이전트가 스스로 스킬을 만들고 고친다는 것이다. 지금도 README 는 *"the only agent with a built-in learning loop"* 라고 말한다.

그런데 지금 OpenClaw 에도 비슷한 기능이 있다. [Skills 문서](https://docs.openclaw.ai/tools/skills)의 **Skill Workshop** 은 재사용할 만한 작업을 발견하면 *"drafts a proposal instead of writing directly to SKILL.md"* 한다. 즉 바로 쓰지 않고 제안서를 만들고, 운영자가 `openclaw skills workshop` 으로 검토한 뒤 적용한다.

반대 방향의 수렴도 있다. Hermes 는 자동 학습이 기본이지만 `skills.write_approval`, `memory.write_approval` 로 **쓰기 전 승인**을 걸 수 있다([Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)).

| | OpenClaw | Hermes |
|---|---|---|
| 스킬 형식 | `SKILL.md` 폴더, AgentSkills 규격 | `SKILL.md`, agentskills.io 규격 호환 |
| 자동 생성 | 제안 → 사람 검토 → 적용 (기본이 보수적) | 에이전트가 직접 생성·수정 (승인 게이트는 선택) |
| 공개 저장소 | ClawHub(clawhub.ai), VirusTotal·ClawScan 검사 결과 확인 | Skills Hub (ClawHub 도 소스 중 하나), 설치 시 보안 스캔 |
| MCP | 서버(`openclaw mcp serve`)와 클라이언트 둘 다 | 클라이언트(MCP 서버 연결, `/reload-mcp`) |

**두 프로젝트가 같은 스킬 규격을 쓰고, Hermes 가 ClawHub 스킬을 가져올 수 있다**는 점이 중요하다. 스킬 생태계가 하나로 합쳐지고 있다.

## 4. 서로를 가져가는 마이그레이션

두 프로젝트가 서로를 얼마나 의식하는지는 마이그레이션 기능에서 가장 잘 보인다.

- **Hermes ← OpenClaw:** `hermes claw migrate` 가 SOUL.md, MEMORY.md, USER.md, 스킬, 명령 허용목록, 메신저 설정, API 키, AGENTS.md 까지 가져온다. `hermes setup` 은 `~/.openclaw` 를 **자동으로 감지**해서 이전을 제안한다(README).
- **OpenClaw ← Hermes:** 설정의 Import Memory 로 Hermes 의 `MEMORY.md`·`USER.md` 를 가져온다. 설정·자격증명·스킬은 가져오지 않고 **기억만** 가져온다([Memory](https://docs.openclaw.ai/concepts/memory)).

비대칭이 눈에 띈다. **Hermes 는 OpenClaw 사용자를 통째로 데려오려 하고, OpenClaw 는 기억만 받아 준다.**

## 5. 보안 — 기본값의 차이

둘 다 "모르는 사람의 DM 은 페어링 코드로 승인" 이 기본이다. 차이는 **에이전트가 명령을 실행할 때의 기본값**에 있다.

**OpenClaw** (README, [Security](https://docs.openclaw.ai/gateway/security))
- *"Tools run on the host for the main session unless you configure sandboxing."* 샌드박스는 설정해야 켜진다.
- 신뢰 모델은 *"One trust boundary per gateway"* 이고, *"not a hostile multi-tenant security boundary"* 라고 명시한다. 여러 사람이 같이 쓰는 격리 환경이 아니라는 뜻이다.
- 호스트 설치는 루프백에만 바인딩하지만, **컨테이너 이미지는 기본이 외부 노출 바인딩**이다.
- `openclaw security audit` 로 설정을 점검할 수 있고, 프롬프트 인젝션, SSRF, MITRE ATLAS 위협 모델 문서가 따로 있다.

**Hermes** ([Security](https://hermes-agent.nousresearch.com/docs/user-guide/security))
- 8계층 모델을 문서화했다. 사용자 인가, 위험 명령 승인, 파일 쓰기 보호, 컨테이너 격리, MCP 자격증명 필터링, 컨텍스트 파일 인젝션 스캔 등이다.
- 명령 승인 기본값은 `smart` 다. 보조 LLM 이 위험도를 판단한다. `--yolo` 로 승인을 꺼도 `rm -rf /` 같은 하드라인 차단 목록은 남는다.
- cron 작업의 위험 명령은 기본 거부(`cron_mode: deny`)다.
- 문서는 한계도 솔직하게 적는다. 쓰기 차단 목록은 *"does not sandbox a hostile or compromised agent"*. Docker 같은 백엔드에서는 위험 명령 검사를 건너뛰는데, **컨테이너 자체를 경계로 보기 때문**이다.

정리하면 이렇다. **OpenClaw 는 "기본은 열어 두고, 감사 도구와 문서로 잠그게 한다" 쪽이다.** 그래서 컨테이너로 띄우면 외부 노출이 기본이라는 점을 꼭 기억해야 한다. **Hermes 는 "기본으로 승인 게이트를 건다" 쪽이다.** 다만 그 게이트가 LLM 판단(smart)이라는 점은 알고 써야 한다.

두 문서 모두 **서드파티 스킬은 신뢰할 수 없는 코드로 취급하라**고 강조한다. 스킬 생태계가 합쳐질수록 이 경고는 더 중요해진다.

## 6. 자동화

- **OpenClaw**([Automations](https://docs.openclaw.ai/automation/cron-jobs)): 스케줄러가 `openclaw automations` 로 이름을 바꿨다(`cron` 은 별칭). 1회·반복 작업, 이벤트 트리거, 인바운드 웹훅, Gmail PubSub 트리거까지 **이벤트 기반 자동화**가 강하다.
- **Hermes**: 게이트웨이가 60초마다 도는 cron 스케줄러를 가지고 있고, 자연어로 작업을 걸고 결과를 아무 채널로나 보낸다. 실행 위치도 로컬, Docker, SSH, Modal, Daytona 등 7종 백엔드 중에서 고를 수 있다. README 는 *"a $5 VPS, a GPU cluster, or serverless infrastructure"* 를 예로 든다.

## 그래서 무엇을 쓰나 (2026년 9월 기준)

| 상황 | 추천 | 이유 |
|---|---|---|
| 메신저·기기 연결 범위가 가장 중요 | OpenClaw | 채널·컴패니언 앱(iOS·Android·데스크톱)이 가장 넓고, 이벤트 트리거가 풍부 |
| 에이전트가 알아서 배우고 쌓아 가길 원함 | Hermes | 자동 스킬 생성이 기본값, 작고 항상 주입되는 기억 |
| 보수적인 기본값이 필요 | Hermes, 또는 OpenClaw + 샌드박스 설정 | Hermes 는 승인 게이트가 기본, OpenClaw 는 샌드박스를 직접 켜야 함 |
| 서버리스·원격 실행 | Hermes | Modal·Daytona 등 원격 백엔드가 내장 |
| Node/TS 생태계에서 확장 | OpenClaw | TypeScript 기반, 플러그인 구조 |
| Python·ML 쪽에서 확장 | Hermes | Python 기반, Nous 의 모델·연구 생태계 |

7월과 달라진 점은 이것이다. **"둘 중 하나" 가 아니라 "옮겨 다닐 수 있다"** 가 됐다. 같은 스킬 규격, 같은 기억 파일명, 양방향 마이그레이션이 있으니 한쪽을 골라도 락인이 약하다. 선택 기준도 기능 목록보다 **기본값의 철학**이다. 열어 두고 잠그게 하느냐, 잠가 두고 열게 하느냐, 그리고 사람이 검토하느냐, 에이전트가 스스로 배우느냐.

## References

2026-09-25 에 확인한 페이지들이다.

- OpenClaw — [GitHub](https://github.com/openclaw/openclaw) · [Releases](https://github.com/openclaw/openclaw/releases) · [Channels](https://docs.openclaw.ai/channels) · [Model providers](https://docs.openclaw.ai/concepts/model-providers) · [Memory](https://docs.openclaw.ai/concepts/memory) · [Skills](https://docs.openclaw.ai/tools/skills) · [MCP](https://docs.openclaw.ai/cli/mcp) · [Automations](https://docs.openclaw.ai/automation/cron-jobs) · [Security](https://docs.openclaw.ai/gateway/security) · [Lore](https://docs.openclaw.ai/start/lore)
- Hermes Agent — [GitHub](https://github.com/NousResearch/hermes-agent) · [Releases](https://github.com/NousResearch/hermes-agent/releases) · [Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) · [Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers) · [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) · [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) · [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)
