---
layout: post
title: "Claude Code 서브에이전트 필드 16개 — .md 한 장 으로 에이전트 를 정의 하는 법"
date: 2026-07-14 19:00:00 +0900
categories: [ai, agent, claude-code]
tags: [claude-code, subagent, agent, frontmatter, harness, orchestration, skills, worktree]
image: /assets/images/claude-code-subagent-frontmatter-fields.jpg
---

Claude Code 에서 서브에이전트 는 별도 프로그램 이 아니다. `.claude/agents/` 밑 에 **.md 파일 한 장** — 상단 frontmatter 에 필드 몇 개, 본문 에 시스템 프롬프트. 그 필드 들 이 "이 에이전트 는 누구고, 무슨 도구 를 쥐고, 어떤 두뇌 로, 어떻게 실행 되는가" 를 통째로 정한다. 아래 16개 가 그 전부 다.

![Claude Code 서브에이전트 frontmatter 필드 16개 — name·description(필수) / tools·disallowedTools·model·permissionMode·maxTurns·skills·mcpServers·hooks·memory·background·effort·isolation·color·initialPrompt](/assets/images/claude-code-subagent-frontmatter-fields.jpg)

필드 를 *나열* 하는 글 은 이미 많다. 이 글 은 **왜 그 필드 가 거기 있는지**, 그리고 실전 에서 *진짜 손 이 가는 건 어느 것* 인지 를 묶어 읽는다. 에이전트 를 *행동 규칙 을 .md 로 고정* 하는 큰 그림 은 [하네스 4프레임]({% post_url 2026-07-10-locking-down-md-behavior-harness-4-frames %}) · [skill.md 6기둥]({% post_url 2026-07-10-harness-engineering-six-pillars-of-skill-md %}) 에서 다뤘고, 이 글 은 그 아래 한 층 — **에이전트 정의 파일 의 스펙** 이다.

---

## 1. 필수 둘 — 정체성 (name · description)

16개 중 `O` 표시 는 딱 둘. 나머지 14개 는 다 선택 이다.

- **name** — 소문자+하이픈, *파일명 과 일치*. 고유 식별자.
- **description** — 이게 사실상 이 파일 에서 **제일 중요한 한 줄** 이다. 오케스트레이터(메인 세션) 가 "지금 이 일 을 이 서브에이전트 에 위임 할까?" 를 *이 문장 만 보고* 판단 한다. 즉 description 은 설명문 이 아니라 **라우팅 트리거** 다. "무엇 을 할 때 쓰는지" 를 구체적 상황 으로 적어야 불려 나온다. 여기서 애매하면 아무리 본문 을 잘 써도 *호출 자체 가 안 된다.*

나머지 필드 를 다 비워도 에이전트 는 돈다. 하지만 이 둘 — 특히 description — 이 부실 하면 *존재 하지만 안 쓰이는* 에이전트 가 된다.

---

## 2. 손 에 무엇 을 쥐어줄까 — 도구·권한 (tools · disallowedTools · permissionMode)

- **tools** — 쉼표 구분. 허용 도구 화이트리스트. 안 적으면 기본 상속.
- **disallowedTools** — 반대로 *상속 목록 에서 빼기*. "다 주되 삭제·push 만 막자" 같은 뺄셈 이 필요할 때.
- **permissionMode** — `default` / `acceptEdits` / `auto` / `dontAsk` / `bypassPermissions` / `plan`. 이 에이전트 가 *얼마나 물어보고 얼마나 알아서* 하는지.

이 셋 이 에이전트 의 **권한 반경** 이다. 읽기·검색 전용 탐색 에이전트 라면 tools 를 읽기 계열 로 좁히고 permissionMode 를 조여서 *사고 칠 여지 를 구조적 으로 없앤다.* 반대로 격리된 워크트리 안 에서 마음껏 고치게 할 거면 `acceptEdits` 로 풀어 마찰 을 줄인다.

---

## 3. 어떤 두뇌 로 — 모델·사고량 (model · effort · maxTurns)

- **model** — `sonnet` / `opus` / `haiku` / `inherit` / 모델 ID. 기본값 **inherit**(부모 세션 모델 그대로).
- **effort** — `low` / `medium` / `high` / `xhigh` / `max`. *추론 노력*. 기계적 변환 은 low, 어려운 설계·리뷰 는 high↑.
- **maxTurns** — 최대 에이전틱 턴 수. 폭주 방지 안전핀.

여기가 **비용·품질 다이얼** 이다. 리뷰·설계 서브에이전트 는 `opus` + `effort: high`, 대량 기계 편집 은 `sonnet`(또는 haiku) + `low`. model 을 안 정하면 inherit 라 부모 를 따라가니, *굳이 다를 이유 가 있을 때만* 지정 하는 게 맞다. 모델 별 비용·성능 은 [비용·성능 프론티어]({% post_url 2026-07-10-llm-cost-performance-frontier %}) 참고.

---

## 4. 어떻게 실행 되나 — 실행 방식 (background · isolation · initialPrompt)

- **background** — 불리언. *항상 백그라운드 실행*. 부모 컨텍스트 를 안 채우고 뒤 에서 돌린다.
- **isolation** — `worktree`. **별도 git worktree** 에서 실행 → 여러 에이전트 가 파일 을 동시 에 고쳐도 서로 안 밟는다. 병렬 수정 의 핵심.
- **initialPrompt** — `--agent` 로 메인 세션 을 이 에이전트 로 띄울 때, *첫 유저 턴 으로 자동 제출* 될 문자열.

`background` + `isolation: worktree` 조합 이 **병렬 오케스트레이션** 의 실전 장치 다. "여러 갈래 를 동시 에 쳐보되 원본 작업트리 는 지킨다" 를 필드 두 개 로 선언 한다.

---

## 5. 능력 을 얹기 — 주입 (skills · mcpServers · hooks)

- **skills** — 시작 시 *주입할 스킬* 목록. 이 에이전트 가 특정 도메인 스킬 을 항상 갖고 시작 하게.
- **mcpServers** — 이 서브에이전트 *전용* MCP 서버. 부모 와 다른 외부 도구 셋 을 줄 수 있다.
- **hooks** — 이 서브에이전트 에 *국한된* 훅. 전역 훅 과 별개 로, 이 에이전트 안 에서만 도는 자동화.

세 필드 다 "이 에이전트 만 의 능력·연결·규칙" 을 *부모 와 분리* 해 얹는 장치 다. 스킬·MCP·훅 을 에이전트 단위 로 스코핑 한다는 게 핵심.

---

## 6. 지속 과 표시 (memory · color)

- **memory** — `user` / `project` / `local`. *세션 간 지속 메모리* 스코프. 매번 새로 시작 하지 않고 이전 을 이어가게.
- **color** — 표시 색상. 순수 UX. 여러 에이전트 를 돌릴 때 로그 에서 눈 으로 구분.

---

## 정리 — 16개 를 세 문장 으로

1. **필수 는 정체성 둘**(name·description) 뿐 이고, description 이 *호출 될지 말지* 를 가른다.
2. **선택 14개 는 네 축** — 권한(tools·permissionMode) / 두뇌(model·effort) / 실행(background·isolation) / 주입(skills·mcpServers·hooks) — 으로 읽으면 외울 게 없다.
3. 실전 에서 손 이 가장 자주 가는 건 **description · tools · model · effort · isolation**. 나머지 는 필요 할 때 하나씩 꺼낸다.

에이전트 를 만든다 = 이 .md 한 장 을 쓰는 일 이다. 코드 가 아니라 *선언* 으로 "누가·무엇 으로·어떻게" 를 정하는 것 — 하네스 엔지니어링 의 가장 작은 단위 다.

---

*필드 목록·값 종류 는 Claude Code 버전 에 따라 늘거나 바뀔 수 있으니, 최신 은 공식 문서 나 `.claude/agents/` 예시 로 확인 하는 게 정확 하다.*
