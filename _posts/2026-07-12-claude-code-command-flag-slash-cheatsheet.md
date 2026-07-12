---
layout: post
title: "Claude Code 사용법 — 명령·플래그·슬래시 한 장 참조, 그리고 실전 조합"
date: 2026-07-12 20:00:00 +0900
categories: [ai, agent, claude-code]
tags: [claude-code, cli, workflow, mcp, worktree, permission-mode, cheatsheet, productivity]
image: /assets/images/claude-code-command-flag-cheatsheet.jpg
---

Claude Code 를 오래 쓰다 보면, 결국 손 에 남는 건 **몇 개 의 명령 과 플래그** 다. 세션 을 어떻게 시작 하고, 어제 대화 를 어떻게 이어가고, 권한 을 어디까지 열고, 어떤 도구 를 확인 없이 굴릴지 — 이 몇 가지 만 몸 에 붙으면 나머지 는 대화 로 흘러간다. 아래 한 장 은 그 골격 이다.

![Claude Code 명령·플래그 빠른 참조 — CLI 명령(claude / -p / -c / -r / mcp / --worktree / --teleport), 자주 쓰는 플래그(--fork-session · --model · --permission-mode · --allowedTools · --add-dir · --output-format · --append-system-prompt), 핵심 슬래시(/clear)](/assets/images/claude-code-command-flag-cheatsheet.jpg)

이 글 은 그 참조표 를 *외우는* 게 아니라, **언제 무엇 을 꺼내 쓰는지** 를 실전 순서 로 꿴다. 프롬프트 자체 를 잘 쓰는 법 은 앞선 [9개 슬롯]({% post_url 2026-07-11-prompting-mastery-9-slots-top-01-vs-1-percent %}) 에서, 에이전트 의 행동 규칙 을 .md 로 고정 하는 법 은 [하네스 4프레임]({% post_url 2026-07-10-locking-down-md-behavior-harness-4-frames %}) 에서 다뤘다. 이 글 은 그 아래층 — **CLI 를 다루는 손끝** 이다.

---

## 1. CLI 명령 — 세션 을 여닫는 법

터미널 에서 `claude` 한 글자 로 시작 한다. 나머지 는 *그 세션 을 어떻게 열 것 인가* 의 변주 다.

| 명령 | 언제 쓰나 |
|---|---|
| `claude` | 그냥 대화형 세션 시작. 대부분 여기서 출발. |
| `claude "작업"` | 초기 프롬프트 를 주고 시작 — "이 버그 고쳐" 를 바로 던질 때. |
| `claude -p "질의"` | **비대화형**. 답만 받고 종료 → 스크립트·파이프 에 물릴 때. |
| `claude -c` / `claude -r` | 최근 대화 *이어가기* / 세션 *골라서 재개*. |
| `claude update` | 최신 버전 갱신. |
| `claude mcp add / list / get / remove` | MCP 서버 붙이고 관리. 외부 도구 를 세션 에 끌어오는 통로. |
| `claude --worktree <이름>` | **격리 된 git worktree** 에서 시작 — 현재 작업트리 를 건드리지 않고 실험. |
| `claude --teleport` | 웹(claude.ai/code) 세션 을 로컬 로 가져오기. |

핵심 은 **세 갈래** 다. *새로 시작* (`claude`), *이어가기* (`-c` / `-r`), *격리* (`--worktree`). 매일 쓰는 건 앞 의 둘, 위험 한 작업 을 할 때 만 세 번째 를 꺼낸다.

`-c` 와 `-r` 의 차이 는 미묘 하다. `-c` 는 *가장 최근* 대화 를 묻지 않고 바로 잇고, `-r` 은 세션 목록 을 보여줘 *어느 것* 을 이어갈지 고르게 한다. 여러 작업 을 병렬 로 굴린 날 은 `-r` 이 안전 하다.

---

## 2. 자주 쓰는 플래그 — 세션 의 성격 을 정하는 손잡이

명령 이 *문* 이라면, 플래그 는 *그 방 의 조명 과 잠금* 이다.

| 플래그 | 무엇 을 바꾸나 |
|---|---|
| `-p, --print` | 비대화형 출력 — 자동화 의 기본. |
| `-c, --continue` | 최근 대화 로드. |
| `-r, --resume` | 세션 재개(선택). |
| `--fork-session` | 새 세션 ID 로 **분기** — 원본 은 두고 갈래 를 친다. |
| `--model` | 모델 지정(`sonnet` / `opus` / 전체 이름). |
| `--permission-mode` | 권한 모드 지정 — 확인 을 얼마나 물을지. |
| `--allowedTools` | **확인 없이** 실행할 도구 화이트리스트. |
| `--add-dir` | 작업 디렉터리 추가 — 리포 밖 경로 를 붙일 때. |
| `--output-format` | `text` / `json` / `stream-json`. |
| `--append-system-prompt` | 시스템 프롬프트 에 규칙 을 덧댐. |

여기서 *실전 에서 체감 이 큰* 세 개 만 짚는다.

- **`--permission-mode` + `--allowedTools`** — 이 둘 이 세션 의 *속도* 를 정한다. 매번 "이 명령 실행 해도 될까요?" 를 물으면 흐름 이 끊긴다. 신뢰 하는 읽기 계열(`Read`, `Grep`, `git status` …) 을 미리 허용 하면 마찰 이 확 준다. 다만 *쓰기·삭제·push* 는 열어두지 말 것 — 편의 와 안전 의 경계 는 여기 다.
- **`--model`** — 어려운 설계·리뷰 는 `opus`, 기계적 편집 은 `sonnet`. 한 세션 안 에서도 `/model` 로 갈아탄다. 모델 별 강점 과 비용 은 [비용·성능 프론티어]({% post_url 2026-07-10-llm-cost-performance-frontier %}) 에서 따로 다뤘다.
- **`--fork-session`** — "지금 맥락 은 살리되, 위험 한 갈래 를 쳐보고 싶다" 일 때. 원본 대화 를 오염 시키지 않고 실험 → 아니면 버리면 된다. `--worktree` 가 *파일* 의 격리 라면, `--fork-session` 은 *대화* 의 격리 다.

---

## 3. 핵심 슬래시 명령 — 세션 *안* 에서

CLI 플래그 가 세션 을 *열 때* 의 설정 이라면, 슬래시 명령 은 세션 *도중* 에 바꾸는 스위치 다. 입력창 에 `/` 를 치면 목록 이 뜬다.

- **`/clear`** — 대화 기록 비우기. 맥락 이 길어져 모델 이 헤매기 시작 하면, 붙들고 있던 실 을 놓고 *새 종이* 로 간다. 가장 자주 쓰는 한 방.
- 그 밖에 세션 안 에서 `/model`(모델 교체), `/config`(설정), `/agents`·`/mcp`(에이전트·MCP 확인) 같은 스위치 를 그때그때 꺼낸다. **핵심 은 하나** — *열 때 못 정한 건, 안 에서 슬래시 로 바꾼다.*

`/clear` 를 언제 쓰는지 가 은근히 실력 이다. 맥락 을 *덜* 지우면 옛 실수 가 따라오고, *너무* 자주 지우면 방금 쌓은 이해 를 버린다. 한 작업 이 끝나 *주제 가 바뀌는 지점* — 거기 가 `/clear` 자리 다.

---

## 4. 하루 를 굴리는 조합

참조표 를 *조합* 으로 읽으면 이렇게 굳는다.

1. **아침** — `claude -c` 로 어제 흐름 을 잇는다. 주제 가 바뀌면 `/clear`.
2. **집중 작업** — 신뢰 도구 를 `--allowedTools` 로 열어 확인 프롬프트 를 줄이고, 어려운 판단 은 `--model opus`.
3. **위험 한 실험** — 파일 은 `--worktree`, 대화 는 `--fork-session` 으로 격리. 잘못 되면 버린다.
4. **자동화** — `claude -p "..." --output-format json` 을 스크립트·크론 에 물려 사람 없이 굴린다.

명령 과 플래그 는 *외우는 지식* 이 아니라 *손 에 붙는 습관* 이다. 위 표 를 한 번 훑고, 나머지 는 매일 한두 개 씩 꺼내 쓰다 보면 — 어느새 터미널 이 대화 처럼 느껴진다.

---

*참조 이미지 는 Claude Code 부록 A(명령·플래그 빠른 참조) 를 옮긴 것. 플래그 상세 는 버전 에 따라 달라질 수 있으니, 최신 목록 은 세션 안 에서 `/help` 로 확인 하는 게 정확 하다.*
