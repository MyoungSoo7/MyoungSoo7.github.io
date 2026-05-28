---
layout: post
title: "내 텔레그램 봇이 'AI Agent Architecture' 9개 컴포넌트 중 어디까지 구현됐나"
date: 2026-05-20 23:55:00 +0900
categories: [ai, agents, infra]
tags: [ai-agent, claude, anthropic, telegram, mcp, react, memory, observability, safety]
---

지난주에 인스타에서 본 Rahul Agarwal 의 *AI Agent Architecture* 도식이 내내 머리에 남아 있었다. **Input → Understanding → Reasoning → Planning → Action → Memory → Monitoring → Safety → Output** — 깔끔한 9개 블록.

그래서 이 그림을 두고 내가 며칠 동안 *실제로* 쓰고 있는 텔레그램 봇 (이 글의 작성과 K3s 운영을 둘 다 해주는 그 봇) 이 **그 9개 블록 중 어디까지 구현돼있는지** 정확하게 매핑해봤다. *말로* "에이전트다" 라고 부르는 것과 *그 그림의 각 블록이 코드 어디에 있는지* 짚을 수 있는 것은 다르다.

> ⚠️ 보안 — 도메인 / 노드명 / IP / 토큰은 모두 redacted. 구조만 공유.

---

## TL;DR — 9개 블록 매핑 현황

| # | 블록 | 현재 구현 위치 | 상태 |
|---|---|---|---|
| 1 | **Input** | Telegram Bot API + 인박스 파일 + image_path 첨부 | ✅ |
| 2 | **Understanding** | Claude (`claude-opus-4-7`) 의 자연어 이해. 별도 분류 단계는 없고 한 통의 모델 호출에 묶여있음 | 🟡 부분 |
| 3 | **Reasoning Engine / LLM** | Claude 의 ReAct (tool_use 응답 → tool 실행 → 결과 재주입) 루프 | ✅ |
| 4 | **Planning Module** | 명시 분리 없음. Claude 가 reasoning 안에서 암묵 분해 | 🔴 미구현 |
| 5 | **Action / Tool Layer** | MCP 서버 다수 + 내장 Bash/Read/Edit/Write + Telegram reply/react tool | ✅ |
| 6 | **Memory System** | 단기: 대화 컨텍스트 / 장기: `~/.claude/projects/.../memory/*.md` (수동 큐레이션) | 🟡 부분 |
| 7 | **Monitoring Layer** | 텔레그램 메시지 자체가 trace. 구조화된 별도 telemetry 없음 | 🔴 미구현 |
| 8 | **Safety & Controls** | 텔레그램 channel allowlist + Claude 의 자체 가드 (오늘만 6번 막힘) | 🟡 부분 |
| 9 | **Output** | Telegram reply / react / edit_message tool | ✅ |

요약: **5개 ✅, 3개 🟡, 1개 🔴.** Reasoning–Action–Output 의 *수직선* 은 잘 박혀 있고, Memory–Monitoring–Planning 의 *횡선* 이 비어있다. 가장 큰 구멍은 **Planning(명시 분해) 과 Monitoring(구조화된 trace)** 두 가지.

---

## 1. Input — ✅

들어오는 신호의 모양:

```xml
<channel source="plugin:telegram:telegram" chat_id="..." message_id="..." user="..."
         ts="..." image_path="...">
  메시지 본문
</channel>
```

- 텍스트 메시지는 그대로 본문.
- 이미지 첨부는 `image_path` 속성으로 로컬 파일 경로가 들어옴 — 봇 데몬이 텔레그램에서 받아 인박스 디렉토리에 떨어뜨려둠.
- 다른 파일 첨부는 `attachment_file_id` 로 와서 별도 download tool 호출이 필요.

다이어그램의 *user queries, API requests, sensor data, events, triggers* 중에서 봇은 **user queries 만** 받는다 (실질적으로). 시간 기반 트리거는 별도 `loop` / `schedule` 메커니즘으로 따로 있고, 같은 Input 블록의 형제다.

> 💡 *Trigger* (예: cron, webhook) 가 들어오면 이 채널의 동일 shape 로 정규화하는 게 좋다. 지금은 별개 경로라 두 개의 entry point 가 존재.

## 2. Understanding — 🟡 부분 구현

다이어그램은 Input 다음에 *별도의 understanding 단계* 를 둔다. 의도 파싱, 엔터티 추출, "이게 이 봇이 다룰 범위 안인가" 같은 분류가 여기서 일어나야 한다.

봇의 현실: **분리된 단계가 없다.** 메시지가 도착하면 그대로 Claude 의 한 통의 호출 안에서 *이해하면서 동시에 reasoning 하면서 동시에 tool 을 부른다*. 이게 빠르고 똑똑한 모델에선 잘 동작하지만, *그 안의 어느 단계가 잘못 갔는지* 디버깅이 안 된다.

오늘 텔레그램으로 받았던 "이커머스 연결 확인" 한 줄을 예로 들면:
- *진짜* 의도 = "운영 페이지가 비어있는지 봐달라" 였다.
- 봇이 *해석한* 의도 = "내부 API 응답이 정상인지 확인" 으로 출발했다.
- 같은 단어 "연결 확인" 의 두 의미를 분리하려면 understanding 단계가 ambiguity 를 잡고 사용자에게 한 번 더 묻거나, 가능한 두 해석을 모두 시도하도록 planning 으로 넘겨야 한다.

**개선 아이디어**: 짧은 사전 호출로 `Intent { kind, objective, entities, needs_tools, confidence }` 같은 구조화된 출력을 받고, confidence 가 낮으면 *행동 전에* 한 번 더 묻는 게이트.

(어제 만든 `ai-agent-architecture` 레포에 이 모양이 그대로 들어가 있다 — `understanding.py` 의 `Intent` Pydantic 모델 + `client.messages.parse()` 로 1회 분류 호출.)

## 3. Reasoning Engine / LLM — ✅

여기는 *진짜 잘 굴러간다*. Claude 의 `tool_use` 응답 → 호스트가 실행 → `tool_result` 로 재주입 → 모델이 다음 행동 결정 — ReAct 루프 그대로.

오늘 한 번의 사고 디버깅에서 봇은 약 30 회 tool 호출을 자율적으로 만들었다 (kubectl, gh, curl, docker, git 의 조합). 모델이 매 단계 *무엇이 부족한지* 를 정확히 알고 다음 tool 을 골랐다. 이 블록은 다이어그램이 기대하는 그대로다.

> 💡 다이어그램에서 Reasoning Engine 박스 아래에 `Chain-of-Thought / ReAct / Plan-and-Execute` 라고 적혀 있는데, 봇은 그 중 **ReAct 만** 쓰고 있다. Plan-and-Execute 는 일부러 안 쓴다 — 짧은 task 가 많고 plan overhead 가 큰 비중이다.

## 4. Planning Module — 🔴 미구현

다이어그램에서 *명시적으로 분리된* 블록 ("Splits the goal into smaller tasks. Step 1 → Step 2 → Step 3"). 봇에는 이 분리가 없다. Claude 가 reasoning 루프 안에서 *암묵* 으로 분해를 하지만, 그 분해 결과가 *외부* 에 남지 않는다 — trace 에서 "이 작업의 1단계는 이거였다" 를 사후 추출할 수 없다.

오늘의 사고는 *우연히* 다행이었다. 봇이 머릿속에서 "ghcr push → helm 태그 변경 → ArgoCD sync 모니터링 → /products 검증" 의 4단계로 분해했고, 그게 사용자(나) 에게도 같은 step 으로 보고됐다. 하지만 만약 그 분해가 잘못됐어도 (예: ghcr push 후 바로 "끝" 으로 점프), 외부에서 알아채기 어렵다.

**개선 아이디어**: reasoning 호출 *전에* "한 번의 plan 호출" 을 두고, 산출물을 task queue (다이어그램의 *Task Queue* 박스) 로 두는 것. queue 가 비면 done. 명시 분해의 부수효과로 *사람이 중간에 step 단위로 개입* 할 수 있다.

## 5. Action / Tool Layer — ✅

가장 풍부한 블록. 다이어그램의 *MCP / File access / API requests / Database searches / Code running / External tools (GitHub, etc.)* 6 박스 모두 봇에 매핑된다:

| 다이어그램 | 봇 구현 |
|---|---|
| MCP | telegram, project-monitor, log-viewer, docker, db-query, supabase, slack, gmail, calendar, drive, linear, notion, figma, canva, gamma, vercel, … 다수 |
| File access | 내장 Read / Write / Edit / Glob / Grep |
| API requests | curl via Bash, WebFetch tool, gh CLI |
| Database searches | mcp__db-query, sqlite via Bash, MongoDB / Postgres via mcp |
| Code running | Bash (shell), kubectl, git, docker |
| External tools | gh CLI, ArgoCD CLI, kubectl, helm |

이 블록은 *과잉* 에 가깝다 — 도구가 너무 많아서 모델이 어느 걸 쓸지 선택할 때 약간 흔들리는 게 보일 때가 있다. tool search (skill 화) 가 그래서 필요해진다.

## 6. Memory System — 🟡 부분 구현

다이어그램이 정확히 둘로 나눠 적은 *Short-term: chat history, current state* / *Long-term: vector database, past events, learned patterns* — 둘 다 봇에 있지만 모양이 다르다.

- **Short-term**: 텔레그램 대화 그 자체. 한 conversation context 가 turn 들을 누적.
- **Long-term**: `~/.claude/projects/.../memory/MEMORY.md` + 폴더 안의 개별 `.md` 파일들. 매 conversation 시작 시 MEMORY.md 가 자동 로드됨.

문제: **벡터 DB 가 아니다. 키워드/사람 큐레이션 기반.** "이 사람의 K8s 클러스터는 어떻게 생겼었지?" 같은 fuzzy lookup 은 long-term 파일을 *직접 읽으면서* 일어난다. 100건 안쪽일 땐 충분히 동작하지만, 1000건이 되면 안 된다.

장기 메모리에 들어가는 *기준* 도 사람 (= 나) 이 정한다. 다이어그램의 *learned patterns* — 봇이 사용 중에 학습하는 부분 — 은 아직 구현되지 않았다. 어제 텔레그램으로 받았던 "권한 룰 정리" 같은 일이 자주 반복되면, 봇이 *권한 막힘이 N회 발생했을 때 자동으로 정리 권유* 같은 패턴을 *스스로* 추가해두는 것 — 이게 진짜 long-term learning 인데, 지금은 사람의 수동 정리.

(어제의 `ai-agent-architecture` 레포에선 SQLite FTS5 로 키워드 검색 가능한 long-term 을 넣어뒀다. 벡터 DB 가 아니라도 *interface* 만 동일하면 swap 이 쉽다.)

## 7. Monitoring Layer — 🔴 사실상 미구현

다이어그램에서 *Content checks / Rate control / Human review checkpoints* 도 적힌 부분이지만, 핵심은 **trace 가 어디에 남는가** 다.

봇의 trace = **텔레그램 메시지 그 자체**. 그게 다다.

이게 가져오는 한계:
- 봇이 30번의 tool 호출을 한 사이클이 끝나면, 그 30번이 *왜* 일어났는지를 사후 분석할 단일 source-of-truth 가 없다.
- 비용/시간 분석이 안 된다 — 어느 단계가 어느 만큼의 토큰을 썼는지, 어디가 느렸는지.
- 같은 사용자에게서 같은 종류의 사고가 반복되는지 추적 못 한다.

**개선 아이디어**: 모든 단계 (input received, understanding parsed, planned, react_start, tool called, tool result, react_end, answered) 에 구조화된 trace event 를 emit. JSON line 으로 SQLite 나 LogStash 에 흘려보냄. 다이어그램의 Monitoring Layer 가 정확히 이 자리.

(전날 정리한 ELK 가 클러스터에 떠 있긴 한데, 봇 자신의 trace 는 거기에 안 흘러간다. fluent-bit DaemonSet 가 노드 kube logs 만 본다. 봇은 그 위 응용계층이라서 별도 경로 필요.)

## 8. Safety & Controls — 🟡 부분 구현

다이어그램이 적은 5가지:
- Access control
- Approval steps
- Content checks
- Rate control
- Human-in-the-loop

봇의 현실:

| 다이어그램 | 봇 구현 |
|---|---|
| Access control | 텔레그램 채널 allowlist (`access.json`). 등록된 chat_id 만 봇이 응답. ✅ |
| Approval steps | Claude 의 권한 가드. prod 영향 큰 작업 (docker push, force push, settings 자기수정, default branch push) 을 자동 보호. ✅ |
| Content checks | 없음. 🔴 |
| Rate control | 텔레그램 봇 자체 rate 만 있고, conversation 차원의 rate 는 없음. 🔴 |
| Human-in-the-loop | 가드가 막힐 때 텔레그램으로 자동 보고 → 사람이 결정 → 진행. ✅ |

오늘 하루 동안 가드는 6번 막혔다 (ghcr push, settings 자기수정, helm-deploy push, blog _posts write, blog push, branch delete). *수동으로 매번* 사람이 결정을 내리는 *Human-in-the-loop 패턴* 의 실제 구현이다. 약간 *과도* 한 보호인 순간도 있었지만 (5월 19일의 ELK 블로그 글 push 가 두 번 막힌 게 대표 사례), 본질적으로는 다이어그램의 *Approval steps* 가 정확히 동작한 사례다.

## 9. Output — ✅

텔레그램 reply / react / edit_message tool. 첨부 (이미지·파일) 지원. 끝.

다이어그램에는 *Output* 박스가 하나지만, 실제로는 *목적지 분기* 가 있다 — 일부 출력은 사용자에게 (텔레그램), 일부는 git commit / push (블로그, 코드 레포), 일부는 클러스터 (kubectl apply). 다이어그램 그림에선 한 박스이지만 실제로는 *다중 sink* 다. 다음 도식 그릴 땐 이 부분을 fan-out 으로 그릴 듯.

---

## 결론 — 구멍 세 개와 우선순위

매핑하니까 정확히 어디가 비었는지 보인다. 우선순위로 정리하면:

1. **Monitoring (1순위)** — 구조화된 trace 없이는 다른 모든 개선이 *결과 측정* 이 안 된다. 이게 첫 번째.
2. **Planning (2순위)** — 명시 분해가 있어야 *중간에 사람이 step 단위로 검수* 할 수 있다. 봇이 prod 영향 큰 작업을 자율로 더 많이 처리하게 만들고 싶으면 필수.
3. **Understanding (3순위)** — confidence 낮은 의도에 "한 번 더 묻는" 게이트. 오늘의 "이커머스 연결 확인" 같은 어휘 충돌이 그 게이트 없이는 *시간이 더 흐른 뒤* 에야 발견된다.

이 세 가지가 일종의 그룹 으로 묶인다 — **agent 가 자기 *내부 상태를 외부 관측 가능하게* 만드는** 것. 봇이 잘 동작하는 건 좋지만, 잘 동작하는지 *증명* 할 수 있어야 prod 운영을 더 신뢰하고 맡길 수 있다.

다음 글에서는 이 세 개 중 첫 번째 — **Monitoring layer 를 어떻게 봇에 박을지** — 를 구체화한다. 어제 만든 `ai-agent-architecture` 레포의 `monitoring.py` 가 출발점이다.

---

### 참고

- Rahul Agarwal, *AI Agent Architecture* 도식
- 어제 만든 reference 구현: 9개 컴포넌트가 각각 별 파일로 — 매핑 작업의 부수 산출물
- Anthropic SDK 의 `tool_runner` (ReAct), `messages.parse()` (Understanding 의 구조화 출력 가능 형태)
