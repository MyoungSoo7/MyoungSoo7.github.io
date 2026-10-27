---
layout: post
title: "Codex · Claude Code · Antigravity 10월 동향과 장단점 순위 — 2주 사이에 셋 다 '모델'과 '운영'을 바꿨다"
date: 2026-10-27 22:10:00 +0900
categories: [AI, Agents]
tags: [Codex, Claude Code, Antigravity, Gemini 4 Argon, GPT-6.1 Terra, Claude Opus 5.5, Coding Agent]
---

나흘 전 [5종 비교 글]({% post_url 2026-10-23-codex-claude-code-cursor-antigravity-hermes-compared %})에서 기능표는 이미 정리했다. 결론은 "기능은 수렴했고, 갈리는 건 본체가 어디 사느냐" 였다. 이번 글은 그 표를 다시 그리지 않는다. 대신 **최근 2주(10월 중순~10-27) 동안 각 도구에 실제로 무엇이 들어왔는지**를 공식 체인지로그로 확인하고, 그걸 바탕으로 **장단점과 순위**를 매긴다.

모든 사실은 2026-10-27 에 벤더 공식 체인지로그·블로그에서 확인했다. 벤더가 직접 낸 수치는 "벤더 주장" 으로 표시한다.

## 0. 먼저 순위 (필자 의견)

| 순위 | 도구 | 한 줄 평 |
|---|---|---|
| 🥇 1 | **Claude Code** | 운영·보안·자동화 기능이 가장 촘촘하다. 대신 Claude 모델에 묶이고 소스가 닫혀 있다. |
| 🥈 2 | **Codex** | 오픈소스 CLI 에 새 모델이 빨리 들어오고, 터미널 사용성 개선이 공격적이다. 대신 운영 기능의 깊이는 한 발 뒤. |
| 🥉 3 | **Antigravity** | 진입 장벽이 가장 낮고(개인 무료) 여러 벤더 모델을 쓸 수 있다. 대신 제품 형태가 자주 바뀌고 최신 모델은 유료 요금제에 걸려 있다. |

**이 순위가 무엇이 아닌지**부터 밝힌다. 이건 성능 순위가 아니다. 세 도구를 같은 과제·같은 조건으로 잰 **중립 제3자 벤치마크를 찾지 못했다.** Terminal-Bench 공식 리더보드([tbench.ai](https://www.tbench.ai/leaderboard))는 현재 4.0 판으로 넘어갔는데, 확인 시점에 세 도구 이름으로 된 항목을 확인할 수 없었다. 그래서 순위는 아래 다섯 기준으로 공식 문서를 읽고 매긴 **필자 판단**이다.

1. **최근 출시 속도와 내용** — 2주 동안 무엇이 실제로 들어왔나
2. **운영·보안 기능** — 샌드박스, 권한, 감사(텔레메트리), 팀 배포
3. **모델 선택의 폭** — 한 벤더에 묶이는가
4. **진입 비용** — 무료로 어디까지 되는가
5. **제품 안정성** — 형태가 자주 바뀌어 습관을 다시 들여야 하는가

## 1. 최근 2주 동향

### Claude Code — 2.1.299 → 2.1.311 (10-14 ~ 10-26)

공식 [changelog](https://code.claude.com/docs/en/changelog) 기준으로 2주 동안 **13개 버전**이 나왔다. 눈에 띄는 것만 추리면:

- **auto mode 손질** — `/auto-mode-setup`(2.1.304)은 "프로젝트와 최근 세션을 읽어서 auto mode 에 환경을 가르치는" 안내형 설정이다. `CLAUDE_CODE_AUTO_MODE_MODEL`(2.1.302)로 판정용 분류기 모델도 고를 수 있게 됐다.
- **샌드박스 강화** — 2.1.305 에 리눅스 샌드박스에서 user namespace 를 허용하는 `sandbox.allowNestedUserNamespaces` 가 들어왔다.
- **감사·관측** — 2.1.307 에 `claude_code.safety_event` OpenTelemetry 이벤트 추가.
- **에이전트 구조** — fork 서브에이전트가 `claude -p`, Agent SDK, 데스크톱 앱, VS Code 에서 기본 켜짐(2.1.302).
- **클라우드·엔터프라이즈 범위 확대** — Monitor 툴과 플러그인 모니터가 Bedrock·Vertex·Foundry 에서도 동작(2.1.310), `claude ultrareview` 는 워크스페이스 신뢰를 요구하도록 바뀜(2.1.309).

모델 쪽은 Anthropic 공식 발표 기준으로 [Opus 5.5](https://www.anthropic.com/claude-opus-5-5)(9-22), [Sonnet 5.5](https://www.anthropic.com/claude-sonnet-5-5)(9-28), [Haiku 5.5](https://www.anthropic.com/claude-haiku-5-5)(10-7)가 차례로 나왔다. 5.5 세대가 한 바퀴 다 깔린 상태다.

**흐름 요약:** 새 기능보다 **"자동으로 돌려도 안전하게"** 쪽 투자가 압도적이다.

### Codex — CLI 0.163.0 / 0.164.0, 그리고 GPT-6.1 Terra

공식 [Codex changelog](https://learn.chatgpt.com/docs/changelog) 기준:

- **0.163.0 (10-15)** — 검색 가능한 `/config`, 응답 도중 후속 메시지로 방향을 트는 steering, `/keymap` 리더 키(기본 Ctrl+X), `/daemon` 에서 백그라운드 서버 재시작, **독립적인 읽기 전용 툴의 병렬 실행**.
- **0.164.0 (10-23)** — 프롬프트·슬래시 명령을 저장하는 10칸짜리 `/presets`, `/model`·`/permissions` 인라인 인자, Kitty/Sixel 터미널에서 이미지 미리보기, **엔터프라이즈 MCP 인증과 자격증명 마스킹**, Amazon Bedrock 설정 마법사 기본 활성화.
- **GPT-6.1 Terra (10-26)** — 이미지 이해와 컴퓨터 사용을 묶은 업무용 모델. Plus·Pro·Business·Enterprise·Edu 요금제의 ChatGPT Work 와 Codex 에서 사용 가능. 공식 문구로 "Chat 에서는 쓸 수 없다".

**흐름 요약:** 터미널 **사용성**(키맵·프리셋·steering)과 **엔터프라이즈 진입로**(MCP 인증, Bedrock)를 동시에 밀고 있다. 새 모델은 Codex 에 바로 들어온다.

### Antigravity — Gemini 4 Argon 투입

[공식 사이트](https://antigravity.google/)는 이제 제품을 다섯 갈래로 소개한다 — App(여러 로컬 에이전트 관제), CLI, IDE, 확장, Python SDK. 개인 개발자는 "Available at no charge" 라고 적혀 있다.

- **Gemini 4 Argon (10-13)** — [공식 블로그](https://antigravity.google/blog/gemini-4-argon-in-google-antigravity)에 따르면 Antigravity 데스크톱 앱과 CLI 에 **Google AI Pro·Ultra 구독자** 대상으로 배포. Gemini Enterprise 일부 구독과 API 도 포함.
  - 벤더 주장: 사내 도입 후 4주간 에이전트 작성 코드 35% 증가, 제출 후 롤백 30% 감소, 134개 버그 중 97개를 3시간 안에 종료. **모두 Google 내부 수치이고 표준 벤치마크 점수는 이 글에 없다.**
- **10-26 연구 글** — Argon 이 Antigravity 에서 그래프·TPU 커널 작업을 어떻게 했는지 다룬 후속 글이 올라왔다.
- **Gemini 앱 통합** — [9to5Google 보도](https://9to5google.com/2026/10/13/gemini-app-macos-antigravity/)에 따르면 macOS Gemini 앱에도 Antigravity 가 들어갔고, 그쪽 접근은 AI Ultra 요금제가 필요하다. (공식 블로그가 아닌 언론 보도다.)

**흐름 요약:** 이번 2주의 핵심은 **모델 교체**다. 도구 자체의 세부 변경 내역은 Claude Code·Codex 처럼 버전별 체인지로그로 공개되는 정도가 덜해서 비교하기 어렵다.

## 2. 장단점

### 🥇 Claude Code

**장점**
- **출시 속도가 가장 빠르고 내용이 운영 쪽이다.** 2주 13버전, 그중 다수가 샌드박스·권한·텔레메트리.
- auto mode 를 프로젝트에 맞게 "가르치는" 설정까지 생겨서, **무인 자동화**에 가장 가깝다.
- Bedrock·Vertex·Foundry 같은 **클라우드 경유 사용**에서 기능 격차를 줄이는 중.
- 모델 라인업(Opus·Sonnet·Haiku 5.5)이 한 세대로 정렬돼 있어 서브에이전트에 작은 모델을 붙이기 쉽다.

**단점**
- **Claude 전용.** 다른 벤더 모델로 바꿀 수 없다.
- **소스 비공개.** 동작을 코드로 확인할 수 없다.
- 기능이 너무 빨리 늘어서 **설정 표면이 넓다.** 환경변수·모드·훅을 다 따라가기 버겁다.

### 🥈 Codex

**장점**
- **CLI 가 오픈소스**(Apache-2.0, [openai/codex](https://github.com/openai/codex)). 문제가 생기면 코드를 읽을 수 있다.
- **새 모델이 바로 들어온다** — GPT-6.1 Terra 가 Codex 에 동시 출시.
- 키맵·프리셋·응답 중 steering 등 **터미널 사용성** 개선이 꼼꼼하다.
- 읽기 전용 툴 병렬 실행처럼 **체감 속도**를 직접 노린 변경이 있다.

**단점**
- 엔터프라이즈 MCP 인증·Bedrock 마법사가 이제 막 들어온 단계라, **운영·감사 기능의 깊이**는 Claude Code 보다 뒤에 있다(필자 판단).
- 최신 모델은 **유료 ChatGPT 요금제** 기준으로 열린다.
- 이번 체인지로그에는 ChatGPT 앱 릴리스가 섞여 있어서, **Codex 변경만 골라 읽기가 번거롭다.**

### 🥉 Antigravity

**장점**
- **개인 무료**로 시작할 수 있다 — 셋 중 진입 장벽이 가장 낮다.
- **여러 벤더 모델**을 한 도구에서 쓴다([10-23 글]({% post_url 2026-10-23-codex-claude-code-cursor-antigravity-hermes-compared %}) 비교표 참고). 한 회사에 묶이기 싫다면 가장 유리하다.
- App·CLI·IDE·확장·SDK 로 **쓰는 자리를 고르기 쉽다.**
- Gemini 4 Argon 이라는 **새 대형 모델**이 막 들어왔다.

**단점**
- **최신 모델은 유료** — Argon 은 AI Pro·Ultra 대상. "무료" 와 "최신" 이 동시에 되지 않는다.
- 표면이 다섯 갈래(App·CLI·IDE·확장·SDK)로 나뉘어 있어 **어느 쪽이 주력인지 따라가야 하는 비용**이 있다.
- 공개 체인지로그가 촘촘하지 않아 **무엇이 바뀌었는지 추적하기 어렵다.**
- Argon 성능 근거가 **Google 내부 수치뿐**이다. 아직 중립 검증이 없다.

## 3. 상황별로 고르면

종합 순위와 다르게, 목적이 분명하면 답이 바뀐다.

| 원하는 것 | 추천 |
|---|---|
| 무인 자동화·팀 운영·감사 | Claude Code |
| 오픈소스·코드로 동작 확인·최신 GPT | Codex |
| 무료로 시작·여러 벤더 모델 섞기 | Antigravity |
| 터미널에서 손에 붙는 사용성 | Codex |
| 클라우드(Bedrock·Vertex) 경유 사용 | Claude Code (Codex 도 Bedrock 지원 시작) |

## 한계

- **성능 비교가 없다.** 같은 조건의 중립 벤치마크를 찾지 못해 순위에서 성능은 뺐다. 벤더 수치는 모두 벤더 주장이다.
- **가격은 적지 않았다.** 요금제 이름만 적었다. 자주 바뀐다.
- Antigravity 는 버전별 공개 체인지로그가 상대적으로 적어, 다른 둘보다 **"모델 소식" 위주**로 읽혔을 수 있다.
- 2026-10-27 기준이다. 이 분야는 주 단위로 바뀐다.

## References

- Claude Code changelog — <https://code.claude.com/docs/en/changelog>
- Anthropic, Introducing Claude Opus 5.5 — <https://www.anthropic.com/claude-opus-5-5>
- Anthropic, Introducing Claude Sonnet 5.5 — <https://www.anthropic.com/claude-sonnet-5-5>
- Anthropic, Introducing Claude Haiku 5.5 — <https://www.anthropic.com/claude-haiku-5-5>
- OpenAI, Codex changelog — <https://learn.chatgpt.com/docs/changelog>
- openai/codex (GitHub) — <https://github.com/openai/codex>
- Google Antigravity — <https://antigravity.google/>
- Google, Gemini 4 Argon in Google Antigravity — <https://antigravity.google/blog/gemini-4-argon-in-google-antigravity>
- 9to5Google, Google Antigravity is now built into Gemini app for macOS (2026-10-13) — <https://9to5google.com/2026/10/13/gemini-app-macos-antigravity/>
- Terminal-Bench leaderboard — <https://www.tbench.ai/leaderboard>
