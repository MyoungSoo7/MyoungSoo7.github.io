---
layout: post
title: "Claude Code DAG·Mod의 Pane 분리와 80컬럼 제한 — 외부 모니터가 해결하는 문제인가"
date: 2026-10-31 22:54:44 +0900
categories: [AI, Claude Code, Developer Tools, Terminal]
tags: [Claude Code, Mod, DAG, Pane, Agent Teams, tmux, iTerm2]
---

> 기준 시각: 2026-10-31 22:54 KST. 이 글은 Claude Code 공식 Mods·Agent Teams 문서와 공개 이슈를 기준으로, “80컬럼 아래에서는 pane을 나눌 수 없다”는 메시지의 원인을 분석한 글이다. 특정 DAG mod의 실제 소스·버전·터미널 설정은 제공되지 않았으므로, 제품 공통 동작과 추정 가능한 원인을 분리한다.

## 결론

**외부 모니터 자체가 pane 분리를 켜는 것은 아니다.** 현재 확인되는 공식 동작은 `터미널의 실제 columns 수`, `fullscreen 여부`, `mod가 pane을 여는 방식`, 그리고 Agent Teams의 경우 `tmux/iTerm2 사용 여부`에 의해 결정된다.[1][2][3]

따라서 노트북에서 안 되고 외부 모니터에서 되는 현상은 대개 외부 모니터가 직접 기능을 추가해서가 아니라, 창을 넓혀 **임계 columns를 넘겼기 때문**이다.

## 1. 먼저 구분해야 하는 두 종류의 pane

스크린샷의 “pane”이라는 말은 서로 다른 UI를 가리킬 수 있다.

| 구분 | 동작 주체 | 분리 조건 |
| --- | --- | --- |
| Mod pane | Claude Code Mods API | Claude Code가 terminal 폭에 따라 sidebar 또는 prompt 위 영역으로 배치 |
| Agent Teams split pane | tmux 또는 iTerm2 | 각 teammate를 별도 terminal pane으로 표시 |
| tmux 수동 분할 | tmux | 터미널 세션을 직접 분할 |
| Desktop Code pane | Claude Desktop 앱 | 앱 내부 layout이 pane을 배치하며 terminal columns 규칙과 다름 |

Claude Code 공식 Mods 문서는 pane을 넓은 fullscreen terminal에서는 transcript 옆 sidebar로, 좁은 terminal에서는 prompt 위의 framed region으로 배치한다고 설명한다.[1] 반면 Agent Teams의 split-pane display는 tmux 또는 iTerm2가 필요하다.[3]

즉, 같은 “나눠진 화면”처럼 보여도 **Claude Code가 그린 Mod pane인지, terminal multiplexer가 만든 pane인지**부터 확인해야 한다.

## 2. 80컬럼은 무엇을 의미하는가

“80컬럼 아래에서는 pane을 나눌 수 없다”는 문구는 보통 pane 내부 콘텐츠가 최소 폭을 확보하지 못했을 때의 안전장치다.

가능한 의미는 세 가지다.

1. **mod 자체의 compact/disable 정책**: 모드가 80 columns 미만이면 정상 레이아웃을 그릴 수 없다고 판단해 split을 거부
2. **Claude Code의 pane placement 변화**: sidebar 대신 prompt 위 inline 영역으로 바뀌어 사용자가 기대한 좌우 pane이 보이지 않음
3. **tmux 분할 뒤 각 pane 폭 부족**: 전체 terminal은 넓어도 분할된 각 pane이 80 columns 아래로 내려감

공식 Mods 문서는 narrow terminal에서 pane이 transcript 옆이 아니라 prompt 위에 놓인다고 설명한다.[1] 또 pane을 스스로 여는 자동 동작은 넓은 terminal을 요구하며, 문서에는 처음 자동으로 열 때 144 columns, 사용자가 한 번 직접 연 뒤에는 110 columns 기준이 제시되어 있다.[1][2]

따라서 “80컬럼”과 “sidebar dock이 시작되는 폭”은 같은 임계값이 아닐 수 있다. 80은 mod 콘텐츠의 최소 사용 폭일 수 있고, 110·144는 pane을 자동 dock/open하는 Claude Code UI 정책일 수 있다.

## 3. 외부 모니터를 연결하면 왜 달라질까

외부 모니터 연결 자체가 Claude Code의 기능 플래그를 바꾸는 것은 아니다. 그러나 다음 값이 달라질 수 있다.

```text
노트북 화면
  → 작은 window width
  → terminal columns 감소
  → inline 또는 compact layout
  → split 불가/축약

외부 모니터
  → 큰 window width
  → terminal columns 증가
  → dock 조건 충족
  → sidebar 또는 여러 pane 표시
```

특히 macOS의 창을 외부 모니터로 옮긴 뒤 maximize하거나 fullscreen으로 만들면 terminal emulator가 보고하는 `COLUMNS`와 `ROWS`가 달라진다. 이때 중요한 값은 모니터의 물리 해상도보다 **현재 터미널 창이 실제로 보고하는 columns**다.

확인 명령은 다음과 같다.

```bash
printf 'columns=%s rows=%s\\n' "$COLUMNS" "$LINES"
tput cols
tput lines
```

Shell 변수와 `tput` 값이 다르면 resize 이벤트나 shell 초기화 상태도 함께 확인해야 한다. Claude Code 내부 UI가 측정한 viewport와 terminal emulator의 값이 일시적으로 다를 가능성도 있으므로 창 크기를 바꾼 뒤 mod를 다시 열어 보는 것이 좋다.

## 4. DAG mod와 Agent Teams를 혼동하지 않기

DAG라는 이름은 작업을 그래프로 표현하는 UI·mod를 가리킬 수 있지만, 공개된 Claude Code 공식 문서에서 확인되는 일반 원리는 다음과 같다.

- Mod는 plugin이며 이벤트 hook으로 UI와 동작을 확장한다.[4]
- Mod는 pane·button·tab 등을 그릴 수 있다.[1][4]
- Agent Teams는 여러 Claude Code 인스턴스를 조정하는 실험 기능이다.[3]
- Agent Teams의 in-process 모드는 어떤 terminal에서도 동작한다.[3]
- 각 teammate를 별도 split pane에 보이려면 tmux 또는 iTerm2가 필요하다.[3]

따라서 DAG 화면에 여러 작업 노드가 보인다고 해서 각각이 반드시 OS-level terminal pane인 것은 아니다. 하나의 Claude Code pane 안에서 mod가 여러 작업 상태를 그리는 경우와, tmux가 실제 terminal을 여러 세션으로 나누는 경우를 구분해야 한다.

## 5. 재현 실험: 모니터보다 먼저 columns를 통제하라

### 실험 A — 같은 노트북, 다른 창 폭

1. 외부 모니터를 연결하지 않는다.
2. 같은 terminal emulator와 같은 Claude Code 버전을 사용한다.
3. 창을 좁힌 상태에서 `tput cols`를 기록한다.
4. mod 또는 DAG 명령을 실행한다.
5. 창을 넓히고 다시 `tput cols`를 기록한다.
6. 같은 명령을 다시 실행한다.

결과가 columns 변화와 함께 달라지면 모니터가 아니라 **terminal width 조건**이 원인일 가능성이 높다.

### 실험 B — 같은 columns, 다른 모니터

1. 노트북과 외부 모니터에서 terminal 창을 같은 폭으로 맞춘다.
2. `tput cols`가 같은지 확인한다.
3. Claude Code 버전·shell·tmux 여부를 동일하게 맞춘다.
4. 같은 mod·같은 session 조건에서 비교한다.

같은 columns인데 결과가 다르면 다음 차이를 조사해야 한다.

- iTerm2와 Terminal.app 등 emulator 차이
- fullscreen 여부
- tmux/iTerm2 `it2` CLI 유무
- 창 분할 전후의 session 구조
- mod 버전·설정·persisted pane width
- Claude Code CLI와 Desktop Code tab 차이

### 실험 C — Agent Teams split 확인

Agent Teams 화면이라면 mod가 아니라 split backend를 확인한다.

```bash
printf 'TERM=%s TMUX=%s\\n' "$TERM" "$TMUX"
command -v tmux || true
command -v it2 || true
tmux display-message -p '#{pane_width}x#{pane_height}' 2>/dev/null || true
```

공식 문서상 Agent Teams split-pane는 tmux 또는 iTerm2가 필요하며, 기본 display mode는 in-process다.[3] 따라서 `TMUX`가 비어 있고 `it2`도 없다면 split pane이 아닌 in-process panel이 기본 결과다.

## 6. “80컬럼 아래”에서의 현실적인 해결책

### 해결책 A — pane 하나를 넓게 유지

세로로 pane을 많이 나누면 각 pane 폭이 급격히 줄어든다. 작업자 4명을 동시에 보려는 경우보다, 2개만 동시에 띄우고 나머지는 tab 또는 in-process panel로 보는 편이 읽기 쉽다.

### 해결책 B — mod의 inline fallback 사용

mod가 narrow terminal에서 inline pane을 지원한다면 sidebar를 고집하지 말고 prompt 위 영역을 사용한다. mod 개발자는 `bodyColumns`, `bodyRows`, `placement` 같은 실제 render site 크기를 읽어 콘텐츠를 그려야 한다.[2]

### 해결책 C — tmux pane을 직접 zoom

Agent Teams split pane이 너무 좁다면 tmux에서 현재 pane을 일시적으로 확대해 질문·로그를 확인할 수 있다.

```text
Ctrl-b z
```

이는 pane을 새로 만드는 기능이 아니라 현재 pane을 임시 확대하는 기능이다. 원래 layout으로 돌아가려면 같은 키를 다시 누른다.

### 해결책 D — 외부 모니터에서는 columns를 측정해 비교

“외부 모니터 연결 여부”를 원인으로 기록하기 전에 다음을 함께 저장한다.

```text
Claude Code version
Terminal emulator
Window fullscreen 여부
COLUMNS / LINES
TERM / TMUX
tmux version 또는 it2 설치 여부
mod/plugin 버전과 설정
```

## 7. 보안과 신뢰성

Mod는 Claude Code 내부에서 실행되며 사용자 권한으로 파일을 읽고 쓰거나 프로세스를 시작하고 네트워크 요청을 할 수 있다. 공식 문서도 mod를 설치하기 전에 신뢰할 수 있는 작성자와 marketplace인지 확인하라고 경고한다.[4]

DAG mod를 설치할 때는 다음을 먼저 확인한다.

- repository와 정확한 commit
- `plugin.json`, `hooks.json`, entry module
- `tool.call`, `agent.spawn`, `process` 관련 hook
- 파일·환경변수·네트워크 접근
- `claude plugin validate` 결과
- 실제로 로드된 mod 목록

```bash
claude plugin validate ./path/to/dag-mod
```

pane이 예쁘게 보이는 것과 안전한 것은 별개다. 특히 agent 상태·토큰 사용량·파일 경로를 보여주는 mod는 세션 정보와 민감한 경로를 외부로 전송하지 않는지 확인해야 한다.

## 확인된 사실·해석·미확인

- **확인된 사실:** 공식 Mods 문서는 pane을 넓은 fullscreen terminal에서는 transcript 옆에, 좁은 terminal에서는 prompt 위에 배치한다고 설명한다.[1]
- **확인된 사실:** 자동으로 열린 pane에는 144 columns, 사용자가 한 번 연 뒤에는 110 columns 기준이 문서에 제시되어 있다.[1][2]
- **확인된 사실:** Agent Teams의 split-pane display는 tmux 또는 iTerm2가 필요하며, 기본은 in-process다.[3]
- **확인된 사실:** Mod는 plugin이며 UI를 그리고 tool call·prompt 등의 이벤트를 가로채거나 변경할 수 있다.[4]
- **해석:** 외부 모니터에서만 분리가 보인다면 물리적 모니터보다 terminal columns·fullscreen·backend 차이를 우선 의심하는 것이 타당하다.
- **미확인:** 사용자가 본 특정 DAG mod의 “80컬럼” 문구는 해당 repository·버전·소스가 제공되지 않아 정확한 구현 조건까지 확인하지 못했다.

## 참고 자료

[1] [Claude Code Docs — Draw in the interface with a mod](https://code.claude.com/docs/en/plugins/mods/interface)

[2] [Claude Code Docs — Mods reference](https://code.claude.com/docs/en/plugins/mods/reference.md)

[3] [Claude Code Docs — Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)

[4] [Claude Code Docs — Mods overview](https://code.claude.com/docs/en/plugins/mods/overview)

[5] [Claude Code GitHub — built-in mods](https://github.com/anthropics/claude-code/tree/main/mods)

> ※ 이 글은 특정 DAG mod를 실제 실행한 벤치마크가 아니다. 정확한 판정을 위해서는 해당 mod의 GitHub URL·commit, Claude Code 버전, 터미널 emulator, `tput cols`, tmux/iTerm2 상태가 필요하다.

## Sources

[1] https://code.claude.com/docs/en/plugins/mods/interface
[2] https://code.claude.com/docs/en/plugins/mods/reference.md
[3] https://code.claude.com/docs/en/agent-teams
[4] https://code.claude.com/docs/en/plugins/mods/overview
[5] https://github.com/anthropics/claude-code/tree/main/mods
