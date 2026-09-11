---
layout: post
title: "SNS에 도는 '클로드 리포지토리' 폴더 구조를 채점해 봤다 — 7개 파일 중 자동으로 읽히는 건 1개다"
date: 2026-09-11 23:38:29 +0900
categories: [engineering, ai]
tags: [claude-code, claude-md, skills, hooks, subagents, output-styles, context]
---

SNS에 이런 폴더 구조가 돌아다닙니다.

```text
📁 노트 판매
├ CLAUDE.md      (전체 규칙)
├ persona.md     (연자의 말투·캐릭터)
├ sales-data.md  (잘 팔린 노트의 데이터)
├ knowhow.md     (노트 판매의 노하우)
├ hooks.md       (인기 있었던 포스트의 패턴)
├ ng-rules.md    (AI스러운 NG 모음)
└ checklist.md   (공개 전 체크리스트)
```

먼저 출처에 대해 정직하게 밝혀 두겠습니다. 저는 이 이미지를 캡처 상태로 받았고, **원작자가 누구인지 확인하지 못했습니다.** 그래서 이 글은 특정 인물의 주장을 반박하는 글이 아니라, **이 *구조*가 클로드 코드의 실제 동작 방식과 얼마나 맞물리는지**를 공식 문서 기준으로 따져 보는 글입니다. 인용은 전부 Anthropic 공식 문서(docs.claude.com)에서 가져왔습니다.

그리고 먼저 칭찬부터 해야 공평합니다. **이 구조는 어려운 절반을 이미 맞혔습니다.**

---

## 0. 이 구조가 잘한 것

두 가지가 제대로 돼 있습니다.

**첫째, 코딩이 아닌 일에 쓰고 있습니다.** '노트 판매'입니다. 클로드 코드를 개발 도구가 아니라 일반 지식 에이전트로 쓰는 건 공식 문서가 명시적으로 지원하는 용법입니다. 출력 스타일 문서의 부제가 그대로 "Adapt Claude Code for uses beyond software engineering" 입니다[^styles].

**둘째, 지식을 관심사별로 쪼갰습니다.** 말투 / 데이터 / 노하우 / 패턴 / 금지사항 / 체크리스트. 이 분해 자체는 좋습니다. 무엇이 중요한 지식인지 아는 건 밖에서 대신 해 줄 수 없는 일이고, 이 사람은 그걸 했습니다.

문제는 나머지 절반입니다. **무엇을 적을지는 맞혔는데, 어디에 둘지를 틀렸습니다.** 그리고 이건 쉬운 절반이라 고칠 수 있습니다.

---

## 1. 핵심 사실 — 저 7개 중 클로드가 자동으로 읽는 건 CLAUDE.md 하나뿐이다

이게 전부입니다. 나머지는 전부 여기서 파생됩니다.

클로드 코드가 세션 시작 시 자동으로 읽는 파일은 정해져 있습니다. 작업 디렉터리와 그 상위의 `CLAUDE.md` / `CLAUDE.local.md`, `~/.claude/CLAUDE.md`, `.claude/rules/` 의 규칙 파일, 그리고 관리 정책 파일입니다[^memory]. **`persona.md` 라는 이름의 파일은 이 목록에 없습니다.** `knowhow.md` 도, `checklist.md` 도 없습니다.

그러면 저 6개는 어떻게 됩니까. 경우는 딱 둘입니다.

**경우 A — CLAUDE.md 에서 `@` 로 임포트하지 않은 경우.** 파일은 그냥 디스크에 누워 있습니다. 클로드가 우연히 `ls` 를 하거나 사용자가 "checklist.md 읽어" 라고 말해야 들어옵니다. **작성자는 규칙을 적었다고 믿고, 클로드는 그 규칙을 본 적이 없습니다.** 이게 제일 흔한 실패이고, 조용해서 몇 달 갑니다.

**경우 B — 전부 `@` 로 임포트한 경우.** 이제 다 읽히긴 합니다. 그런데 공식 문서가 이 선택에 대해 직접 경고합니다.

> "Splitting into `@path` imports helps organization but **doesn't reduce context, since imported files load at launch**."[^memory]

즉 **7개 파일이 매 세션 전부 컨텍스트에 올라갑니다.** 잡담 한마디를 하려고 세션을 열어도 '공개 전 체크리스트'와 '잘 팔린 노트의 판매 데이터'가 같이 올라옵니다. 체크리스트는 공개 직전 한 번만 필요하고, 판매 데이터는 분석할 때만 필요한데 말입니다.

그리고 여기서 두 번째 비용이 붙습니다. 같은 문서가 이렇게 씁니다.

> "**Files over 200 lines consume more context and may reduce adherence.**"[^memory]

컨텍스트를 더 쓰는 건 돈 문제지만, **adherence(지시 준수율)가 떨어지는 건 품질 문제**입니다. 규칙을 더 많이 넣을수록 각 규칙이 덜 지켜집니다. 7개를 다 임포트하는 순간, 가장 중요한 CLAUDE.md 의 규칙까지 같이 묽어집니다.

정리하면 이 구조에는 **선택지가 두 개뿐이고 둘 다 나쁩니다.** 안 읽히거나, 항상 읽히거나. 클로드 코드가 실제로 제공하는 건 세 번째 선택지 — **필요할 때만 읽히기** — 인데, 평평한 폴더에는 그걸 표현할 문법이 없습니다.

---

## 2. 두 번째 사실 — 규칙은 컨텍스트일 뿐 강제가 아니다

`ng-rules.md`(AI스러운 NG 모음)와 `checklist.md`(공개 전 체크리스트). 이 둘은 성격이 다릅니다. **"알고 있어라"가 아니라 "반드시 지켜라"** 입니다. 그런데 마크다운 파일은 그걸 못 합니다.

공식 문서가 이 지점을 아주 직설적으로 씁니다.

> "Claude treats them as context, **not enforced configuration**. To block an action regardless of what Claude decides, use a **PreToolUse hook** instead."[^memory]

그리고 한 번 더 못을 박습니다.

> "If the instruction is something that **must run at a specific point, such as before every commit or after each file edit**, write it as a **hook** instead. Hooks execute as shell commands at fixed lifecycle events and **apply regardless of what Claude decides to do**."[^memory]

'공개 전 체크리스트'는 문서가 든 예시와 **글자 그대로 같은 종류**입니다. 특정 시점에 반드시 실행돼야 하는 절차입니다. 그런데 `checklist.md` 는 클로드가 기억해 주면 돌고 잊으면 안 도는, 지켜질 수도 있고 안 지켜질 수도 있는 부탁입니다. 실제 훅은 그렇지 않습니다. **종료 코드 2로 끝내면 그 동작이 차단됩니다.** 문서 표현으로는 "exit 2 blocks whether or not you print JSON: even a JSON `permissionDecision` of `allow` can't override it"[^hooks].

같은 얘기가 `ng-rules.md` 에도 걸립니다. "AI스러운 표현 금지"는 금지 규칙인데, 컨텍스트에 적힌 금지는 샙니다. 100번 중 95번 지켜지고 5번 새는데, **새는 5번이 바로 공개되는 글에 남습니다.**

---

## 3. 그리고 이름 하나가 실제로 위험하다 — `hooks.md`

사소해 보이는데 사소하지 않습니다.

이 구조에서 `hooks.md` 는 "인기 있었던 포스트의 패턴", 즉 카피라이팅의 **후킹 문구** 모음입니다. 그런데 클로드 코드에서 **hooks 는 완전히 다른 것의 고유명사**입니다. 세션 생명주기 이벤트(`PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit` 등)에서 실행되는 셸 명령이고, 설정 파일에 등록합니다[^hooks].

같은 디렉터리에 `hooks.md` 라는 파일이 있고 클로드 코드가 그걸 읽는다면, **모델이 "이 프로젝트의 훅 설정"으로 오해할 소지가 실재합니다.** 사람도 헷갈립니다. 팀원이 들어와서 `hooks.md` 를 열었다가 카피 문구가 나오면 한 번 멈칫합니다.

고유명사와 충돌하는 파일명은 그 자체로 비용입니다. `copy-patterns.md` 나 `post-hooks.md` 로 바꾸면 0원에 해결됩니다.

---

## 4. 채점

각 파일을 다섯 축으로 0~2점씩, 10점 만점으로 매겼습니다.

- **로드**: 클로드가 실제로 보는가
- **타이밍**: 필요할 때 오는가 (항상 오는 것도 감점 — 항상 필요한 게 아니라면)
- **강제력**: 지켜지는 것이 보장되는가
- **네이티브**: 클로드 코드에 전용 자리가 있는데 쓰고 있는가
- **토큰**: 컨텍스트 비용이 합리적인가

임포트 여부는 그림에 안 나와 있으므로, **임포트 안 한 경우**로 채점하고 **임포트한 경우**를 화살표로 병기했습니다.

| 파일 | 로드 | 타이밍 | 강제력 | 네이티브 | 토큰 | 합계 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `CLAUDE.md` | 2 | 2 | 1 | 2 | 1 | **8** |
| `persona.md` | 0→2 | 1 | 1 | 0 | 0 | **2 → 4** |
| `sales-data.md` | 0→2 | 0 | 1 | 0 | 0 | **1 → 3** |
| `knowhow.md` | 0→2 | 0 | 1 | 0 | 0 | **1 → 3** |
| `hooks.md` | 0→2 | 0 | 1 | 0 | 0 | **1 → 3** |
| `ng-rules.md` | 0→2 | 0 | 0 | 0 | 0 | **0 → 2** |
| `checklist.md` | 0→2 | 0 | 0 | 0 | 0 | **0 → 2** |

**총점: 70점 만점에 13점.** 전부 임포트해도 25점입니다. 그것도 임포트하면 CLAUDE.md 의 토큰 점수가 1에서 0으로 떨어지므로 실제로는 24점입니다.

점수가 이렇게 낮은 이유는 **내용이 나빠서가 아닙니다.** 내용은 모릅니다. 못 봤으니까요. 그리고 그게 바로 요점입니다 — **클로드도 못 봤습니다.**

각 항목을 짚으면:

- **`CLAUDE.md` 8점.** 유일하게 자동으로 로드되는 파일이고, '전체 규칙'은 CLAUDE.md 에 두는 게 맞습니다. 감점은 두 군데입니다. 강제력 1점 — 문서가 명시하듯 컨텍스트일 뿐입니다. 토큰 1점 — "전체 규칙"을 한 파일에 다 넣으면 200줄 권장선을 넘기 쉽습니다.
- **`persona.md` 2점.** 말투와 캐릭터를 매 응답에 적용하는 기능이 **따로 있습니다.** 출력 스타일의 정의가 그대로 "They set Claude's **role, tone, and output format for every response**"[^styles] 입니다. 전용 자리를 비워 두고 마크다운으로 흉내 내고 있어 네이티브 0점입니다.
- **`sales-data.md` 1점.** 데이터는 애초에 컨텍스트에 상주할 물건이 아닙니다. 문서 표현으로 "Large reference docs, API specifications, or example collections **don't need to load into context every time**"[^skills].
- **`knowhow.md` 1점.** '노하우'는 재사용 가능한 작업 절차입니다. 문서의 비교표가 스킬의 용도로 딱 그것을 적습니다 — "You have a reusable workflow"[^styles].
- **`hooks.md` 1점.** 위에서 말한 이름 충돌이 여기 반영됐습니다.
- **`ng-rules.md` 0점, `checklist.md` 0점.** 강제돼야 하는 것이 강제되지 않습니다. 이 둘이 이 구조에서 **가장 크게 헛도는 파일**입니다.

---

## 5. 고친 구조

같은 7개 지식을, 클로드 코드가 실제로 제공하는 자리에 각각 옮기면 이렇게 됩니다.

```text
노트-판매/
├── CLAUDE.md                          # 전체 규칙만. 200줄 이내로 유지
└── .claude/
    ├── output-styles/
    │   └── persona.md                 # 말투·캐릭터 → 매 응답에 적용
    ├── rules/
    │   └── ng-rules.md                # paths 프론트매터로 원고 파일에만
    ├── skills/
    │   ├── draft/
    │   │   ├── SKILL.md               # /draft — 노하우 요약 + 네비게이션
    │   │   ├── copy-patterns.md       # 후킹 패턴 (필요할 때만 로드)
    │   │   └── sales-data.md          # 판매 데이터 (필요할 때만 로드)
    │   └── publish-check/
    │       └── SKILL.md               # /publish-check — 공개 전 체크
    └── settings.json                  # Stop 훅으로 체크리스트를 강제
```

바뀐 게 **파일 내용이 아니라 위치뿐**이라는 점이 중요합니다. 쓰는 사람이 다시 써야 하는 건 거의 없습니다.

### 각각이 왜 거기인가

**말투 → 출력 스타일.** `.claude/output-styles/persona.md` 에 두고 `/config` 에서 고릅니다. 문서상 "Claude Code sends the active style's instructions with every request"[^styles] 이므로 매 응답에 적용되는 게 보장됩니다. 마크다운 임포트와 달리 **역할·톤 전용 슬롯**이라 CLAUDE.md 의 규칙과 경쟁하지 않습니다.

**노하우·패턴·데이터 → 스킬 하나와 그 부속 파일들.** 이게 이 글에서 제일 큰 이득입니다. 스킬은 **이름과 설명만 컨텍스트에 있고, 본문은 호출될 때 들어옵니다.**

> "In a regular session, **skill descriptions are loaded into context** so Claude knows what's available, but **full skill content only loads when invoked**."[^skills]

그리고 부속 파일은 한 겹 더 늦게 옵니다. `SKILL.md` 에서 "판매 데이터가 필요하면 sales-data.md 를 보라"고 안내만 해 두면, 실제로 필요한 순간에만 읽힙니다[^skills]. 평평한 폴더가 못 하던 **세 번째 선택지가 여기서 생깁니다.**

참고로 `SKILL.md` 자체는 500줄 이내로 유지하라는 권장이 있고, 한 번 로드된 스킬 본문은 이후 턴에도 컨텍스트에 남습니다[^skills]. 그러니 본문은 네비게이션으로 쓰고 살은 부속 파일로 미는 게 맞습니다.

**NG 규칙 → `.claude/rules/` + 훅.** 규칙 파일은 `paths` 프론트매터로 범위를 좁힐 수 있습니다.

```text
---
paths:
  - "drafts/**/*.md"
---
```

이렇게 두면 초안 파일을 만질 때만 로드되고, 다른 대화에서는 안 옵니다[^memory]. 다만 이것도 여전히 **컨텍스트**입니다. 절대 나가면 안 되는 표현이 있다면 그건 규칙이 아니라 **훅**이어야 합니다. `PostToolUse` 로 방금 쓴 파일을 grep 해서 금지어가 나오면 종료 코드 2로 막는 식입니다.

**체크리스트 → Stop 훅 + `/publish-check` 스킬.** 두 겹으로 갑니다. 사람이 언제든 부를 수 있는 `/publish-check` 스킬을 두고, 동시에 발행 동작에 훅을 걸어 검사를 통과하지 못하면 차단합니다. 클로드가 기억하든 말든 도는 쪽이 훅입니다.

**교정은 서브에이전트로 분리해도 좋습니다.** `.claude/agents/editor.md` 에 교정 전용 에이전트를 두면 **별도 컨텍스트 창**에서 돕니다. 문서상 "Each subagent runs in its own context window"[^agents] 이므로, 초안 전체를 훑는 지저분한 작업이 본 대화를 오염시키지 않습니다. 다만 함정이 하나 있습니다 — 서브에이전트는 CLAUDE.md 는 물려받지만 **출력 스타일은 안 물려받습니다**[^agents]. 그러니 말투가 중요한 작업은 서브에이전트에 맡기면 안 됩니다. 교정처럼 말투를 *판정*만 하는 일에 쓰십시오.

### 고친 뒤 점수

| 지식 | 옮긴 자리 | 로드 | 타이밍 | 강제력 | 네이티브 | 토큰 | 합계 |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| 전체 규칙 | `CLAUDE.md` (200줄 이내) | 2 | 2 | 1 | 2 | 2 | **9** |
| 말투 | 출력 스타일 | 2 | 2 | 1 | 2 | 1 | **8** |
| 판매 데이터 | 스킬 부속 파일 | 2 | 2 | 1 | 2 | 2 | **9** |
| 노하우 | 스킬 본문 | 2 | 2 | 1 | 2 | 2 | **9** |
| 후킹 패턴 | 스킬 부속 파일 | 2 | 2 | 1 | 2 | 2 | **9** |
| NG 규칙 | 경로 규칙 + PostToolUse 훅 | 2 | 2 | 2 | 2 | 2 | **10** |
| 체크리스트 | Stop 훅 + 스킬 | 2 | 2 | 2 | 2 | 2 | **10** |

**13점 → 64점.** 내용은 한 글자도 안 바꿨습니다.

---

## 6. 그래서 이 그림에서 가져갈 것

SNS에 도는 폴더 그림을 볼 때 확인할 게 세 개입니다.

**① 이 파일이 자동으로 읽히는가.** `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/*.md`, 그리고 `@` 로 임포트된 것. 이 목록에 없으면 클로드는 그 파일을 모릅니다. 확인 방법도 있습니다 — 세션에서 `/context` 를 치고 **Memory files** 목록을 보면 됩니다. 거기 없으면 안 읽힌 겁니다[^memory].

**② 항상 필요한가, 가끔 필요한가.** 항상이면 `CLAUDE.md`, 가끔이면 스킬입니다. 이 구분 하나가 컨텍스트 예산 대부분을 결정합니다.

**③ 알아야 하는 건가, 지켜야 하는 건가.** 알아야 하면 마크다운, 지켜야 하면 훅입니다. 마크다운으로 적은 금지 규칙은 대체로 지켜지고 가끔 샙니다. 가끔 새도 되는 규칙이면 마크다운이 맞고, 아니면 훅이어야 합니다.

이 세 질문은 클로드 코드 문서의 비교표를 세 줄로 줄인 것에 가깝습니다[^styles]. 그 표가 원본이니 한 번 보시길 권합니다.

---

## 7. 이 글의 한계

- **원작자를 확인하지 못했습니다.** 캡처 이미지 한 장이 근거의 전부이고, 그 폴더의 실제 파일 내용도, `CLAUDE.md` 안에 `@` 임포트가 있는지도 보지 못했습니다. 그래서 채점은 **그림에 보이는 정보만으로** 했고, 임포트한 경우를 따로 병기했습니다. 원본에 제가 못 본 사정이 있을 수 있습니다.
- **점수는 제 배점입니다.** 다섯 축과 0~2점 배분은 제가 정한 것이지 공식 기준이 아닙니다. 인용한 동작 방식은 문서에 있는 사실이지만, **몇 점을 깎을지는 의견**입니다.
- **클로드 코드는 빠르게 바뀝니다.** 인용한 문서는 2026년 9월 기준입니다. 슬래시 커맨드가 스킬로 통합된 것처럼[^skills] 구조 자체가 바뀌는 일이 실제로 있었습니다. 버전이 다르면 다시 확인하십시오.
- **동작 방식이 결과를 보장하지는 않습니다.** 파일을 제자리에 옮기면 클로드가 **본다**는 건 보장되지만, 본 다음 **잘 쓴다**는 건 별개 문제입니다. 문서도 같은 구분을 합니다 — 컨텍스트는 준수를 보장하지 않고, 보장이 필요하면 훅으로 가라는 게 그 얘기입니다.

---

## References

[^memory]: Anthropic, ["How Claude remembers your project"](https://docs.claude.com/en/docs/claude-code/memory) (Claude Code 공식 문서, 2026년 9월 확인). 자동 로드되는 파일 목록과 로드 순서, `@path` 임포트가 "doesn't reduce context, since imported files load at launch" 라는 점, 200줄 권장선과 adherence 저하, "Claude treats them as context, not enforced configuration" 및 특정 시점에 반드시 실행돼야 하는 지시는 훅으로 쓰라는 안내, `.claude/rules/` 와 `paths` 프론트매터, `/context` 의 Memory files 로 로드 여부를 확인하는 방법.

[^skills]: Anthropic, ["Extend Claude with skills"](https://docs.claude.com/en/docs/claude-code/skills) (Claude Code 공식 문서, 2026년 9월 확인). 스킬은 설명만 컨텍스트에 있고 본문은 호출 시 로드된다는 점, 부속 파일을 `SKILL.md` 에서 안내해 필요할 때만 읽히게 하는 패턴, `SKILL.md` 500줄 권장, 한 번 로드된 스킬 본문이 이후 턴에 남는다는 점, 커스텀 커맨드가 스킬로 통합된 변경.

[^hooks]: Anthropic, ["Hooks reference"](https://docs.claude.com/en/docs/claude-code/hooks) (Claude Code 공식 문서, 2026년 9월 확인). 훅 이벤트 목록(`PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`, `SessionStart` 등)과 종료 코드 2 의 차단 동작 — "exit 2 blocks whether or not you print JSON".

[^styles]: Anthropic, ["Output styles"](https://docs.claude.com/en/docs/claude-code/output-styles) (Claude Code 공식 문서, 2026년 9월 확인). "Adapt Claude Code for uses beyond software engineering", 출력 스타일이 "role, tone, and output format for every response" 를 정하고 매 요청에 전송된다는 점, `.claude/output-styles/` 위치와 프론트매터, 그리고 출력 스타일·CLAUDE.md·에이전트·스킬을 언제 각각 쓰는지 정리한 비교표.

[^agents]: Anthropic, ["Create custom subagents"](https://docs.claude.com/en/docs/claude-code/sub-agents) (Claude Code 공식 문서, 2026년 9월 확인). 서브에이전트가 "its own context window" 에서 돈다는 점, `.claude/agents/` 위치, 시작 시 CLAUDE.md 계층은 상속하지만 출력 스타일과 자동 메모리는 상속하지 않는다는 점.
