---
layout: post
title: "html-plan — Claude Code 의 계획서를 '읽고 그 자리에서 답하는' HTML 한 장으로"
date: 2026-10-06 23:56:52 +0900
categories: [ai]
tags: [claude-code, plugin, planning, html, agent-skills, anthropic]
---

Anthropic Claude Code 팀의 Thariq Shihipar(@trq212)가 X 에 올린 트윗이다. 새 플러그인을 설치해 보고 피드백을 달라는 내용이다.

![Thariq(@trq212) 트윗 — "install it and give me feedback with: claude plugin marketplace add anthropics/claude-plugins-community / claude plugin install html-plan@claude-community / here's an example:" 아래에 'Scheduling Sent Messages in PostBox' 계획 페이지 예시. Proposed · 9 files +5 new ~4 changed, Why · 2 requests, 번호 붙은 주장 1~4 와 '1 decision' 배지, 하단에 '4 to answer' 와 'Respond' 버튼](/assets/images/html-plan-thariq-tweet.jpg)

이 글은 그림에 보이는 것이 무엇인지를, 플러그인 **소스(1차 자료)** 를 직접 읽고 설명한다.

> **확인 범위.** 아래 내용은 GitHub 의 [`anthropics/claude-plugins-community`](https://github.com/anthropics/claude-plugins-community/tree/main/html-plan) 리포에 있는 `plugin.json`·`README.md`·`SKILL.md`·커밋 기록을 읽은 것이다. 플러그인을 직접 설치해 돌려 보지는 않았다. 트윗 원문 URL 은 확인하지 못해 캡처로 대신한다.

## 1. 그림 위쪽 — 설치 명령 두 줄

```bash
claude plugin marketplace add anthropics/claude-plugins-community
claude plugin install html-plan@claude-community
```

- 첫 줄은 **플러그인 마켓플레이스**를 등록한다. `anthropics/claude-plugins-community` 는 Anthropic 이 운영하는 커뮤니티 플러그인 목록이다. 리포 설명에 따르면 "Claude Cowork 와 Claude Code 용 커뮤니티 플러그인 마켓플레이스"이고, 읽기 전용 미러다. 플러그인 제출은 별도 양식으로 받는다.
- 둘째 줄은 그 마켓플레이스(`claude-community`)에서 `html-plan` 플러그인을 설치한다.
- 플러그인 매니페스트의 작성자는 Thariq Shihipar, 라이선스는 MIT, 버전은 1.0.0 이다. 리포에 처음 들어온 것은 **2026-10-01** 이고, 10월 5일까지 세 번 다듬어졌다.
- 플러그인과 마켓플레이스 개념 자체는 Claude Code 공식 문서([Plugins](https://docs.claude.com/en/docs/claude-code/plugins), [Plugin marketplaces](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces))에 설명돼 있다.

설치 후 사용법은 한 줄이다.

```
/html-plan add send later to the composer
```

## 2. 그림 아래쪽 — 계획 페이지 예시

예시는 가상의 메일 앱 PostBox 에 **"예약 발송"** 기능을 넣는 계획이다(플러그인에 `examples/scheduled-send.html` 로 들어 있다). 화면의 각 요소는 이런 뜻이다.

| 그림 속 요소 | 의미 |
| --- | --- |
| **Scheduling Sent Messages in PostBox** | 제목. 규칙상 "무엇을, 어디에" 를 3~7 단어로 쓴다. 문장이나 목표가 아니다 |
| **Proposed · 9 files +5 new ~4 changed** | 이 계획대로 하면 파일 9개가 바뀐다. 5개 새로 만들고 4개 수정 |
| **Why · 2 requests** | 이 계획이 나온 이유. 사용자가 *한 말 그대로* 를 접힌 인용으로 넣는다(바꿔 쓰지 않는다) |
| **1 ~ 4 번호 줄** | 계획의 최상위 "주장". 사용자가 *무엇을 할 수 있게 되는가* 로 쓴다 |
| **1 decision 배지** | 그 주장에 사용자가 골라야 할 결정이 하나 걸려 있다 |
| **4 to answer ↓** | 아직 열어 보지 않은 결정 4개. 누르면 다음 결정으로 이동 |
| **Respond** | 내 답을 마크다운 하나로 모아 준다. 그걸 Claude 에 붙여 넣으면 된다 |

그림의 주장 네 줄을 읽으면 기능 전체가 요약된다.

1. 사용자가 작성 화면에서 시간을 고를 수 있다.
2. 예약된 메시지를 한 목록에서 보고 바꿀 수 있다.
3. 메시지는 정해진 시각에만 발송된다. 실패한 발송은 남겨 둔다.
4. 예약 발송이 실패하면 사용자에게 알린다.

## 3. 핵심 아이디어 — 계획서는 "주장의 나무"

`SKILL.md` 가 정한 구조는 **주장(claim)을 3단까지 펼치는 나무**다. 단계마다 답하는 질문이 하나씩이고, 질문이 증거(exhibit)의 종류를 정한다.

| 단계 | 답하는 질문 | 증거 |
| --- | --- | --- |
| 제목 | 이게 뭔가? | 없음 |
| Why | 왜? | 사용자 원문 인용 |
| 1 | 무엇을 할 수 있게 / 보게 되나? | UI 목업, 상태가 있으면 상태 머신 |
| 2 | 어떻게 동작하나? | 호출 스택, 스키마, 짧은 코드 |
| 3 | 어디에? | `파일:줄` 과 실제 코드 |

나무를 **닫아 두면 그게 곧 요약**이고, 궁금한 주장만 한 단계씩 열어 본다. 그래서 따로 TL;DR 이나 "작업 순서" 목록을 쓰지 않는다.

규칙 중 눈에 띄는 것들:

- **최상위는 동작(behaviour) 기준으로 나눈다.** 파일·계층·작업 순서로 나누지 않는다. 동작은 코드를 안 읽어도 판단할 수 있는 유일한 기준이기 때문이다.
- **1·2 단계 주장은 참/거짓을 따질 수 있는 문장**이어야 한다. "메시지 한도"(X) → "사용자는 예약 메시지를 최대 50개까지 가질 수 있다"(O).
- **주장 하나에 증거 하나.** 증거가 둘이면 주장도 둘로 쪼갠다.
- **자식은 최대 5개, 깊이는 최대 3단.**
- **결정은 그것이 바꾸는 주장 바로 위에 놓는다.** 계획 하나에 2~5개만, 실제로 만들 것을 바꾸는 갈림길만 묻는다. 기본 선택지는 Claude 가 자기라면 고를 것으로 미리 체크해 둔다.
- 맨 끝에는 여러 주장이 공유하는 것(예: 새 테이블 하나)과 **바꾸지 않는 것**(scope)을 따로 둔다.
- 스키마는 표가 아니라 **그 프로젝트의 언어로 된 텍스트**(TypeScript, SQL 등)로 쓴다.
- 이미 있는 코드는 **실제 경로와 줄 번호**로 인용하고, 아직 없는 코드는 "스케치"라고 표시한다.

## 4. 문장 규칙 — Simplified Technical English

재미있는 점은 문체 규칙이다. 주장·캡션·질문·선택지 등 모든 산문을 **ASD-STE100 Simplified Technical English(STE)** 로 쓰라고 정해 두었다. STE 는 원래 항공 정비 매뉴얼을 위해 만들어진 통제 영어 규격이다([ASD-STE100](https://www.asd-ste100.org/)).

- 승인된 단어만, 승인된 뜻으로 쓴다 (`utilize` 대신 `use`, `ensure` 대신 `make sure`).
- 지시문은 20단어, 설명문은 25단어 이하.
- 능동태, 단순 시제. *should / may / might* 대신 *must*(규칙)와 *can*(가능)만 쓴다.
- 비유·관용구·농담 금지.

계획서는 빠르게 읽혀야 하므로, 모호함이 적은 통제 영어를 고른 것으로 읽힌다. 단, 사용자의 원문 인용, 코드, UI 목업 안의 글자는 예외다.

## 5. 동작 흐름

`SKILL.md` 가 정한 순서는 다음과 같다.

1. **먼저 읽는다.** 변경이 건드리는 진입점·레코드·화면을 찾아 경로와 줄 번호를 적는다.
2. **1단계 주장부터 쓰고** 소리 내어 읽어 본다. 이게 맞아야 나머지를 쓴다.
3. 2·3단계 주장, 증거, 결정을 채운다. HTML 은 `doc-plan`, `doc-claim`, `doc-mock`, `doc-machine`, `doc-calls`, `doc-schema`, `doc-code`, `doc-ask` 같은 전용 태그로 쓴다.
4. **`pack.mjs` 로 묶는다.** 규칙 일부를 검사(lint)하고, CSS·JS 를 인라인해 오프라인에서도 열리는 HTML 파일 하나로 만든다. 필요한 것은 `node` 뿐이다.
5. 브라우저로 열어 목업이 잘리지 않는지 확인한다.
6. "결정 4개. 기본값이 제가 만들 것입니다." 한 줄과 함께 넘긴다.
7. **사용자 응답이 올 때까지 구현을 시작하지 않는다.**

사용자가 Respond 를 누르면 이런 마크다운이 나온다(SKILL.md 예시).

```
# Re: Scheduling Sent Messages in PostBox
## Decisions
1. [1.3] How many scheduled messages per user?
   → **500** `500`  ✎ (was: 50)
2. [3.3] Should a failed send retry on its own?  _(kept as proposed)_
   → **Yes, 3 times, 5 minutes apart** `3`
...
## Edits
### migrations/0042_scheduled_messages.sql
(unified diff)
```

결정 변경, 스키마 수정(diff), 지운 호출, 주장별 코멘트가 **한 번에** 돌아온다. Claude 는 주장 번호로 그것들을 반영하고, 계획의 모양이 바뀌면 페이지를 다시 보내고, 그다음에 만든다.

## 6. 왜 이런 게 나왔나 — 긴 마크다운 계획서의 문제

에이전트에게 계획을 먼저 쓰게 하는 것은 이미 흔한 방법이다. 문제는 결과물이 **수백 줄짜리 마크다운**이 되기 쉽다는 것이다. 사람은 그걸 훑어보고 넘어가고, 정작 골라야 할 갈림길은 본문 어딘가에 묻힌다.

html-plan 은 이 문제를 세 가지로 푼다.

1. **접힌 나무** — 기본 화면이 요약이다. 깊이 볼 곳만 연다.
2. **증거 중심** — 설명 문단 대신 목업·상태 머신·스키마·실제 코드를 보여 준다. 규칙에도 "주장과 증거 사이에 문단을 두지 말라. 설명이 필요하면 더 나은 증거를 골라라"라고 돼 있다.
3. **답하는 자리** — 결정이 해당 주장 위에 붙어 있고, "N to answer" 버튼이 남은 결정으로 데려가며, 응답은 붙여 넣기 한 번이다.

Thariq 는 이전부터 "에이전트의 출력물을 마크다운 대신 HTML 로" 라는 주제로 예시를 모아 왔다([html-effectiveness 갤러리](https://thariqs.github.io/html-effectiveness/)). html-plan 은 그 생각을 **구현 계획**이라는 한 용도에 맞춰 규칙과 런타임까지 묶어 낸 것으로 보인다.

## 7. 정리

| | 일반 마크다운 계획 | html-plan |
| --- | --- | --- |
| 형태 | 긴 텍스트 문서 | 접히는 주장 나무, HTML 한 파일 |
| 근거 | 문단으로 설명 | 목업·상태 머신·스키마·실제 코드 |
| 결정 | 본문에 흩어짐 | 해당 주장 위에 번호로, 기본값 체크 |
| 피드백 | 사람이 따로 정리해 입력 | Respond → 마크다운 하나 붙여 넣기 |
| 구현 시작 | 바로 시작하기도 함 | 응답 전에는 시작하지 않음 |

> **한계.** 이 글은 소스 문서를 읽고 정리한 것이다. 실제 설치·실행 결과, 큰 코드베이스에서의 품질, 토큰 비용은 확인하지 않았다. 갓 나온 1.0.0 이라 규칙과 화면은 바뀔 수 있다(공개 후 5일 사이에도 스타일과 규칙이 두 번 바뀌었다).

## References

1. Anthropic, `claude-plugins-community` — html-plan 플러그인 (plugin.json, README.md, SKILL.md, 커밋 기록). <https://github.com/anthropics/claude-plugins-community/tree/main/html-plan>
2. Anthropic, Claude Code Docs — *Plugins*. <https://docs.claude.com/en/docs/claude-code/plugins>
3. Anthropic, Claude Code Docs — *Plugin marketplaces*. <https://docs.claude.com/en/docs/claude-code/plugin-marketplaces>
4. ASD, *ASD-STE100 Simplified Technical English*. <https://www.asd-ste100.org/>
5. Thariq Shihipar, *html-effectiveness* 예시 갤러리. <https://thariqs.github.io/html-effectiveness/>
6. Thariq Shihipar(@trq212), X 트윗 (본문 캡처 이미지).
