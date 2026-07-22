---
layout: post
title: "하나의 표준, 네 개의 얼굴: Claude Code · OpenAI · Codex · agentskills.io 스킬 비교 분석"
date: 2026-07-22 22:50:00 +0900
categories: [AI, Agent]
tags: [agent-skills, claude-code, openai, codex, agentskills, SKILL-md, progressive-disclosure, harness-engineering, mcp]
---

# 네 개를 비교하려다 발견한 것 — 사실은 '한 개'였다

이 글은 원래 네 개의 **AI 에이전트 스킬(Agent Skills)** 체계를 나란히 놓고 우열을 가리려는 의도로 시작했습니다.

- [Claude Code 스킬](https://code.claude.com/docs/ko/skills)
- [OpenAI Skills 저장소](https://github.com/openai/skills)
- [Codex의 Build Skills 문서](https://learn.chatgpt.com/docs/build-skills)
- [agentskills.io](https://agentskills.io/home)

그런데 네 문서를 다 읽고 나니 결론이 뒤집혔습니다. **이건 서로 경쟁하는 네 개의 포맷이 아니라, 하나의 개방형 표준과 그 위의 세 가지 구현(+표준 그 자체)** 이었습니다. 자바 진영으로 비유하면 `JPA 스펙(JSR-338)` 하나에 `Hibernate`, `EclipseLink` 구현이 붙는 구조와 똑같습니다. 그래서 이 글의 진짜 주제는 "누가 이겼나"가 아니라 **"표준이 어떻게 만들어지고, 각 구현이 어디를 어떻게 확장했나"** 입니다.

---

## 0. 공통 코어 — 폴더 하나와 SKILL.md 한 장

네 곳 모두가 공유하는 최소 단위는 놀랄 만큼 단순합니다.

```text
my-skill/
├── SKILL.md          # 필수: 메타데이터(frontmatter) + 지침
├── scripts/          # 선택: 실행 코드
├── references/       # 선택: 상세 문서
└── assets/           # 선택: 템플릿·리소스
```

`SKILL.md`의 맨 위에는 YAML frontmatter가 있고, 최소 두 필드만 있으면 됩니다.

```yaml
---
name: skill-name
description: 이 스킬을 언제 써야 하고 언제 쓰지 말아야 하는지.
---

(여기부터 에이전트가 따를 지침)
```

그리고 네 곳 모두 **점진적 공개(progressive disclosure)** 라는 동일한 로딩 전략을 씁니다.

1. **Discovery(발견)** — 시작 시엔 각 스킬의 `name`과 `description`만 컨텍스트에 올린다. "이런 게 있다"는 것만 안다.
2. **Activation(활성화)** — 작업이 어떤 스킬의 설명과 맞아떨어지면, 그때 비로소 `SKILL.md` 본문 전체를 읽어들인다.
3. **Execution(실행)** — 지침을 따르며, 필요하면 번들된 스크립트를 돌리거나 참조 파일을 추가로 연다.

이게 스킬 시스템의 핵심 발명입니다. **수백 개의 스킬을 손에 쥐고 있어도, 평소엔 이름표만 걸려 있으니 컨텍스트 비용이 거의 안 든다.** CLAUDE.md처럼 항상 통째로 로드되는 방식과 결정적으로 다른 지점이죠.

이 공통 코어가 어디서 왔는지가 이 글의 첫 번째 반전입니다.

---

## 0.5. 스킬은 어떻게 태어났나 — MCP에서 Skills로 이어진 진화

스킬을 이해하려면 그 앞 세대인 **MCP(Model Context Protocol)** 를 먼저 봐야 합니다. 스킬은 갑자기 튀어나온 게 아니라 MCP가 풀어준 문제 위에서 자연스럽게 다음 단계로 자란 것이기 때문입니다. 이 흐름을 한 장으로 정리하면 이렇습니다.

![Tools 파편화 → MCP(툴 스펙 통일·컨텍스트 유연 주입·AI Agent 폭발) → Skills(초기/이후 컨텍스트 로드 감소·점진적 공개·안정적 결과를 위한 Prompt+Context 제공) 로 이어지는 진화 다이어그램](/assets/images/mcp-to-skills-evolution.jpg)

### 1단계 — MCP 이전: 툴은 파편화되어 있었다

MCP가 나오기 전, 에이전트에 도구(툴)를 붙이는 일은 난장판이었습니다.

- **Tools 스펙이 제각각**이었다. 도구마다 정의 방식이 달라 통일된 규격이 없었다.
- **툴의 입·출력이 모델로 전달되는 과정이 유연하지 못했다.** 무엇을 언제 컨텍스트에 넣고 뺄지를 다루기가 어려웠다.

도구를 하나 붙일 때마다 배선을 새로 짜야 하니, 에이전트가 쓸 수 있는 능력이 좀처럼 확장되지 못했습니다.

### 2단계 — MCP: 툴 스펙을 통일하고 컨텍스트를 유연하게 만들다

MCP는 이 문제를 정확히 겨냥했습니다.

- **Tools 스펙 통일** — "도구를 이렇게 정의하고, 이렇게 호출한다"는 공통 규격을 세웠다. USB-C 포트처럼, 한 번 맞춰두면 아무 도구나 꽂힌다.
- **컨텍스트를 필요에 의해 주입하거나 제외** — 무엇을 모델에게 보여줄지를 규격 안에서 조절할 수 있게 됐다.
- 그 결과 **폭발적인 AI Agent 생태계**가 열렸다. 도구 붙이기가 표준화되니 누구나 에이전트를 조립할 수 있게 됐다.

이게 2023년 이후 MCP가 만든 변화입니다. 하지만 새로운 병목이 드러났습니다. **도구가 늘어날수록, 그리고 절차적 지식(procedural knowledge)을 모델에게 알려주려 할수록, 컨텍스트가 무거워졌다**는 점입니다. "이 작업은 이렇게 하라"는 지침을 항상 통째로 컨텍스트에 이고 다녀야 했으니까요.

### 3단계 — Skills: 컨텍스트 부담을 덜고 '절차'를 얹다

Skills는 MCP가 남긴 이 병목을 정조준합니다. 다이어그램의 오른쪽 상자가 스킬의 세 가지 기여입니다.

1. **컨텍스트 초기 로드 감소** — 시작할 땐 스킬의 이름·설명만 올린다. 능력은 많이 쥐고 있되, 평소 비용은 거의 없다.
2. **컨텍스트 이후 로드 감소 → 점진적으로 읽어나가는 과정** — 실제로 그 스킬이 필요할 때만 본문을, 더 깊이 필요하면 참조 파일을 단계적으로 연다. 앞서 본 **점진적 공개(progressive disclosure)** 가 바로 이것이다.
3. **안정적 결과물을 위한 Prompt + Context 제공** — 즉흥적으로 매번 프롬프트를 다시 짜는 대신, 검증된 절차와 맥락을 패키지로 제공해 결과의 일관성을 높인다.

정리하면 이렇습니다.

> **MCP = "도구를 붙이는 표준"** (능력의 표준화)
> **Skills = "절차적 지식을 붙이는 표준"** (지식과 워크플로의 표준화, 그것도 컨텍스트 예산을 아끼면서)

MCP가 "무엇을 할 수 있는가(what tools)"를 표준화했다면, Skills는 "그 도구들로 어떤 절차를 어떻게 밟는가(how to)"를 표준화했습니다. 그리고 앞서 2장에서 본 Claude Code의 **동적 컨텍스트 주입**(`` !`git diff` ``)이나 Codex의 **`dependencies.tools`로 MCP 서버 선언**은, 이 두 세대가 서로 맞물려 돌아간다는 증거입니다. 스킬은 MCP를 대체하는 게 아니라, MCP 위에 얹혀 그것을 조율하는 상위 계층인 셈이죠.

---

## 1. agentskills.io — 스킬이 아니라 '헌법'이다

[agentskills.io](https://agentskills.io/home)를 마켓플레이스로 오해하기 쉽지만, 실체는 **표준의 명세서(spec)와 본가(home)** 입니다. 페이지 하단에 결정적인 한 줄이 있습니다.

> "The Agent Skills format was originally developed by **Anthropic**, released as an open standard, and has been adopted by a growing number of agent products."

즉 이 포맷은 Anthropic이 만들어 **개방형 표준으로 풀었고**, agentskills.io는 그 표준의 스펙·퀵스타트·평가(eval) 가이드를 문서화한 중립 지대입니다. GitHub(`agentskills/agentskills`)과 Discord에서 커뮤니티 기여를 받습니다.

이 사이트에서 가장 인상적인 건 **클라이언트 쇼케이스**였습니다. 같은 `SKILL.md` 포맷을 채택한 도구가 로고 캐러셀로 흐르는데, 면면이 화려합니다.

- **에이전트/IDE**: Claude Code, OpenAI Codex, Cursor, GitHub Copilot, VS Code, Gemini CLI, Roo Code, Kiro, Amp, Goose, OpenCode
- **프레임워크/플랫폼**: **Spring AI**(!), Laravel Boost, Letta, OpenHands, fast-agent
- **데이터/인프라**: Databricks Genie, Snowflake Cortex Code, Pulumi Neo

자바 백엔드 개발자 입장에서 가장 눈이 간 건 **Spring AI가 2026년 1월 "Generic Agent Skills"를 공식 지원**하기 시작했다는 점입니다. 스킬이 더 이상 "코딩 에이전트 CLI만의 장난감"이 아니라, 애플리케이션 프레임워크 레벨까지 침투한 **범용 확장 규격**이 되었다는 신호죠.

**한 줄 요약**: agentskills.io = 표준 그 자체. 여기가 기준점이고, 나머지 셋은 이 기준을 얼마나 충실히 따르고 어디를 확장했는지로 평가된다.

---

## 2. Claude Code — 표준의 레퍼런스 구현이자 최다 확장

[Claude Code 문서](https://code.claude.com/docs/ko/skills)는 스스로를 이렇게 규정합니다.

> "Claude Code skills는 Agent Skills 개방형 표준을 따르며, 호출 제어·subagent 실행·동적 컨텍스트 주입 같은 추가 기능으로 표준을 확장합니다."

표준을 **가장 공격적으로 확장**한 구현입니다. Anthropic이 표준의 원저자이니 당연한 위치죠. 백엔드 개발자 관점에서 실전 가치가 높은 확장 기능들을 추렸습니다.

### (a) 동적 컨텍스트 주입 — 프롬프트가 실행되기 전에 shell이 먼저 돈다

```yaml
---
name: summarize-changes
description: 커밋 안 된 변경을 요약하고 위험 요소를 표시. diff 리뷰 요청 시 사용.
---

## Current changes
!`git diff HEAD`

## Instructions
위 변경을 2~3줄로 요약하고 위험 요소를 나열하라...
```

`` !`git diff HEAD` `` 라인은 **Claude가 프롬프트를 보기 전에** 셸에서 실행되어, 그 출력으로 자리가 채워집니다. 즉 에이전트가 열린 파일에서 추측하는 게 아니라 **실제 작업 트리의 라이브 데이터**를 근거로 답합니다. 이건 다른 세 곳엔 없는 Claude Code 고유의 강력한 패턴입니다.

### (b) 호출 주체 제어 — 배포는 사람만 누른다

두 개의 frontmatter 필드로 "누가 이 스킬을 부를 수 있는가"를 통제합니다.

| Frontmatter | 사용자 호출 | Claude 자동 호출 | 용도 |
| :-- | :-- | :-- | :-- |
| (기본값) | ✅ | ✅ | 대부분의 스킬 |
| `disable-model-invocation: true` | ✅ | ❌ | `/deploy`, `/commit` — 사람이 타이밍을 쥐어야 하는 부수효과 작업 |
| `user-invocable: false` | ❌ | ✅ | 배경 지식 — Claude만 참조, 메뉴엔 숨김 |

`disable-model-invocation`은 실무에서 특히 중요합니다. **"코드가 준비된 것처럼 보인다고 Claude가 알아서 프로덕션에 배포하지 않도록"** 막는 안전장치죠.

### (c) subagent 격리 실행 — `context: fork`

`context: fork`를 주면 스킬 본문이 **격리된 subagent의 프롬프트**가 됩니다. 대화 기록에 접근하지 못하니 컨텍스트 오염이 없고, `agent: Explore`처럼 읽기 전용 에이전트에 태우면 무거운 리서치를 깔끔하게 위임할 수 있습니다.

### (d) 그 밖의 실무 필드

- `allowed-tools` — 스킬 활성 시 특정 도구(`Bash(git add *)` 등)를 승인 없이 사용. `.claude/settings.json`의 권한 규칙과 동일한 문법.
- `paths` — glob 패턴으로 특정 파일 작업 시에만 자동 로드. monorepo에서 유용.
- `model` / `effort` — 스킬이 켜진 턴 동안만 모델·추론 강도를 오버라이드.
- `hooks` — 스킬 라이프사이클에 훅 부착.
- **중첩·심링크 로딩** — monorepo에서 `apps/web/.claude/skills/`가 `apps/web:deploy`로 네임스페이스되어 붙는다.

Claude Code의 스킬은 사실상 **기존 `/commands`를 흡수**했습니다. `.claude/commands/deploy.md`와 `.claude/skills/deploy/SKILL.md`가 똑같이 `/deploy`를 만들고, 스킬 쪽이 지원 파일·frontmatter 제어라는 상위 기능을 더한 형태입니다.

**한 줄 요약**: 표준 + 최다 확장. 특히 동적 컨텍스트 주입과 호출 주체 제어는 프로덕션 안전성 측면에서 다른 구현 대비 앞서 있다.

---

## 3. Codex — OpenAI판 구현, 같은 뼈대 다른 배선

[Codex의 Build Skills 문서](https://learn.chatgpt.com/docs/build-skills)를 보면, 같은 `SKILL.md` 표준 위에 OpenAI의 배선을 얹은 구조입니다. 공통 코어는 동일하되 **디렉터리 규칙·메타 확장·컨텍스트 예산**에서 차이가 드러납니다.

### (a) 위치 계층 — `.agents/skills`

Claude Code가 `.claude/skills/`를 쓰는 자리에, Codex는 `.agents/skills`를 씁니다.

| 범위 | 경로 |
| :-- | :-- |
| Repository | CWD 및 상위 폴더의 `.agents/skills` |
| User | `$HOME/.agents/skills` |
| Admin | `/etc/codex/skills` (시스템 전역) |
| System | OpenAI 번들 기본 제공 |

### (b) `agents/openai.yaml` — UI·브랜딩·의존성 분리

Claude Code가 모든 제어를 `SKILL.md` frontmatter 한 곳에 몰아넣는 반면, Codex는 **표시/실행 설정을 별도 파일로 분리**합니다.

```text
my-skill/
├── SKILL.md
└── agents/openai.yaml   # display_name, icon, brand_color,
                         # allow_implicit_invocation, dependencies.tools(MCP)
```

- `display_name` / `short_description` / `icon_small` / `brand_color` — 앱 UI용 메타
- `allow_implicit_invocation` (기본 true) — Claude의 `disable-model-invocation`에 대응하는, 자동 선택 허용 스위치
- `dependencies.tools` — 이 스킬이 요구하는 **MCP 서버**를 선언

이 분리는 취향의 문제입니다. Claude 쪽은 "한 파일에서 다 본다"는 응집도, OpenAI 쪽은 "지침(SKILL.md)과 패키징 메타(openai.yaml)를 분리한다"는 관심사 분리를 택했습니다.

### (c) 호출 문법과 컨텍스트 예산

- **명시 호출**: `$skill-name` (Claude Code의 `/skill-name`에 대응)
- **컨텍스트 예산**: 초기 스킬 목록에 **"모델 컨텍스트의 최대 2%, 또는 8,000자"** 를 할당. Claude Code도 동일하게 1%(설정으로 2%까지) 예산을 두고 초과 시 저빈도 스킬 설명부터 잘라내는데, 두 구현이 **같은 문제의식(스킬 목록의 토큰 비용)** 을 공유한다는 게 흥미롭습니다.

**한 줄 요약**: 표준 준수 구현. 디렉터리(`.agents/skills`)와 메타 분리(`agents/openai.yaml`)가 Claude Code와 다른 지점이며, MCP 의존성을 스킬 메타에 명시적으로 선언하는 점이 실무적으로 깔끔하다.

---

## 4. github.com/openai/skills — 이미 은퇴한 '예제 카탈로그'

여기서 반전이 하나 더 있습니다. 사용자가 링크로 준 [github.com/openai/skills](https://github.com/openai/skills) 저장소는 **이미 deprecated 상태**입니다. 저장소 상단에 이렇게 적혀 있습니다.

> "This repository is deprecated. For current Codex skill and plugin examples, use the **OpenAI Plugins** repository."

이 저장소는 애초에 **표준 명세가 아니라 예제 스킬 모음(catalog)** 이었습니다.

- `.system` — 최신 Codex에 자동 설치되는 것들
- `.curated` — `$skill-installer` 도구로 설치 가능
- `.experimental` — 폴더를 지정해야 설치되는 실험용
- 언어 구성: Python 78%, JS 17%, Shell 2% — **스킬은 결국 스크립트를 번들한다**는 걸 보여주는 통계
- 114개 커밋, 릴리스 없음 → 버전 배포 시스템이 아니라 참조용 카탈로그

즉 이 링크는 **"OpenAI가 스킬을 어떻게 쓰는지 보여주는 샘플집"** 이었고, 지금은 그 역할이 OpenAI Plugins 저장소로 넘어갔습니다. 스킬 → 플러그인으로 패키징해 배포한다는 흐름은 Claude Code가 스킬을 플러그인으로 묶어 배포하는 것과 **정확히 같은 진화 경로**입니다.

**한 줄 요약**: 표준도 도구도 아닌 '예제 저장소'였고 이미 은퇴. 스킬이 실전에서 어떻게 스크립트를 번들하고 카테고리를 나누는지 보는 참고용으로만 가치.

---

## 5. 한눈에 비교

| 항목 | agentskills.io | Claude Code | Codex | openai/skills |
| :-- | :-- | :-- | :-- | :-- |
| **정체** | 표준(스펙) 본가 | 레퍼런스 구현 | OpenAI 구현 | 예제 카탈로그(폐기) |
| **핵심 단위** | `SKILL.md` 폴더 | 동일 | 동일 | 동일 |
| **로딩** | 점진적 공개 3단계 | 동일 | 동일 | — |
| **스킬 위치** | (규정) | `.claude/skills/` | `.agents/skills/` | (샘플) |
| **명시 호출** | (규정 없음) | `/skill-name` | `$skill-name` | `$skill-installer` |
| **메타 위치** | frontmatter | frontmatter 집중형 | SKILL.md + `openai.yaml` 분리형 | — |
| **차별 기능** | 중립 스펙·eval 가이드 | 동적 컨텍스트 주입, `context:fork`, 호출제어, paths, hooks | MCP 의존성 선언, 위치계층 | 카테고리 분류 예시 |
| **컨텍스트 예산** | (개념 제시) | 1~2% | 2% / 8,000자 | — |
| **원저작** | Anthropic → 개방 표준 | Anthropic | OpenAI(표준 채택) | OpenAI |

---

## 5.5. 스킬과 토큰 비용 — 점진적 공개는 공짜가 아니다

"점진적 공개 덕에 스킬을 많이 쥐고 있어도 비용이 거의 안 든다"고 했지만, **일단 호출된 스킬은 결코 공짜가 아닙니다.** 이 지점이 실무에서 가장 오해하기 쉬운 부분이라 따로 떼어 다룹니다. 근거는 Anthropic 공식 Claude Code 문서의 [Skill content lifecycle](https://code.claude.com/docs/ko/skills#skill-content-lifecycle) 섹션입니다. (Anthropic이 정책을 바꾸면 수치도 바뀔 수 있으니 참고용으로 보세요.)

![Claude Code Skill content lifecycle — 스킬은 호출되면 단일 메시지로 세션 끝까지 유지, 자동 압축 시 스킬당 최대 5,000토큰 생존, 재부착 스킬은 합쳐서 25,000토큰 예산 공유](/assets/images/skill-token-cost-lifecycle.jpg)

### 호출된 스킬은 세션 끝까지 눌러앉는다

핵심 규칙은 세 가지입니다.

1. **스킬은 한 번 호출되면 본문이 단일 메시지로 컨텍스트에 들어가 세션 끝까지 유지된다.** Claude Code는 이후 턴에 스킬 파일을 다시 읽지 않는다. 그래서 지침은 "이번에 한 번 하는 단계"가 아니라 "작업 전체에 계속 적용되는 상시 규칙"으로 써야 한다.
2. **자동 압축(auto-compaction)이 일어나면 각 스킬의 가장 최근 호출 본문이 앞에서부터 최대 5,000토큰까지 살아남는다.**
3. **재부착되는 모든 스킬은 합쳐서 25,000토큰 예산을 공유하며, 가장 최근 호출부터 채운다. 예산을 넘으면 오래된 스킬은 통째로 빠진다.**

즉 한 세션에서 스킬을 많이 호출하면, 압축 이후엔 예전에 부른 스킬이 흔적도 없이 사라질 수 있습니다. "분명 아까 스킬을 불렀는데 왜 그 규칙을 안 따르지?" 하는 상황의 상당수가 여기서 옵니다.

### 두 종류의 토큰 비용을 구분하라

스킬의 토큰 비용은 성격이 다른 **두 겹**으로 나뉩니다. 이걸 구분하는 게 최적화의 출발점입니다.

| 비용 종류 | 언제 드는가 | 크기 | 절약법 |
| :-- | :-- | :-- | :-- |
| **목록 비용(listing)** | 항상 (모든 스킬의 name+description) | 컨텍스트의 1%(설정 시 2%)까지. 초과 시 저빈도 스킬 설명부터 잘림, 항목당 1,536자 상한 | description을 짧고 트리거 위주로. `when_to_use`도 이 예산에 포함 |
| **본문 비용(body)** | 호출된 이후 세션 내내 | 스킬 본문 전체가 매 턴 반복 계산 | **SKILL.md는 500줄 이하로**, 상세 참조는 별도 파일(`references/`)로 분리해 필요할 때만 로드 |

문서가 명시적으로 강조하는 원칙이 이겁니다.

> "본문 자체는 간결하게 유지하라. 스킬이 로드되면 그 콘텐츠는 턴 전체에 걸쳐 컨텍스트에 유지되므로, **모든 줄이 반복되는 토큰 비용**이다. 어떻게·왜인지 설명하기보다 무엇을 할지 명시하고, CLAUDE.md에 적용하는 것과 같은 간결성 테스트를 적용하라."

### 실무 체크리스트

- **description은 트리거 키워드를 앞에** — 목록 예산이 초과되면 뒤쪽부터 잘리고, 저빈도 스킬일수록 먼저 삭제된다. 자주 안 쓰는 스킬일수록 설명 첫머리에 핵심 트리거를 박아둬야 한다.
- **SKILL.md 본문은 다이어트** — 긴 API 스펙·예제는 `references/`, `examples.md`로 빼고 SKILL.md에선 링크로만 가리킨다. 호출 시 매 턴 반복되는 비용을 줄이는 가장 직접적인 방법.
- **`/context`와 `/doctor`로 실측** — `/context`의 Skills 행은 예산 적용 후 실제 목록 크기를, `/doctor`는 목록의 컨텍스트 비용 추정치와 최대 기여 스킬을 보여준다. 감이 아니라 숫자로 관리한다.
- **압축 후 규칙이 흐려지면 다시 호출** — 큰 스킬이거나 그 뒤로 다른 스킬을 여럿 불렀다면, 압축이 그 스킬을 밀어냈을 수 있다. 결정론적 강제가 필요하면 스킬 대신 [hooks](https://code.claude.com/docs/ko/hooks)로 넘긴다.

이 토큰 경제학은 **0.5장에서 본 MCP→Skills 진화의 이면**이기도 합니다. 스킬이 "컨텍스트 로드를 줄인다"는 건 목록 단계 얘기이고, 일단 활성화되면 그 본문은 엄연히 자리를 차지합니다. 점진적 공개는 비용을 **없애는** 게 아니라 **필요한 순간까지 미루는** 기술이라는 걸 기억하면, 스킬을 훨씬 경제적으로 설계할 수 있습니다.

---

## 6. 백엔드 개발자의 시선 — 이 표준화가 왜 중요한가

이 비교에서 얻은 실무적 결론 세 가지.

**첫째, 스킬은 이제 벤더 종속이 아니다.** `SKILL.md` 하나를 잘 써두면 Claude Code, Codex, Cursor, Gemini CLI, 심지어 Spring AI까지 **같은 자산을 재사용**합니다. "write once, use everywhere"가 마케팅 문구가 아니라 실제 스펙이 된 겁니다. 제가 운영하는 여러 프로젝트(settlement, lemuel-xr, sparta-msa)의 도메인 규칙·배포 절차를 스킬로 정리해두면, 어떤 에이전트를 쓰든 그 지식이 따라옵니다.

**둘째, 이식할 때 갈아끼울 지점은 명확하다.** 표준 코어(SKILL.md 본문)는 그대로 두고, **경로(`.claude` vs `.agents`)와 확장 메타(frontmatter 필드 vs `openai.yaml`)만 조정**하면 됩니다. Claude Code의 `disable-model-invocation`은 Codex의 `allow_implicit_invocation: false`로, `allowed-tools`의 MCP 권한은 Codex의 `dependencies.tools`로 대응합니다.

**셋째, 안전장치는 아직 구현마다 다르다.** 프로덕션 배포·커밋처럼 부수효과가 큰 작업이라면, 현재로선 **호출 주체를 명시적으로 잠그는 기능(Claude의 `disable-model-invocation`)** 이 가장 성숙합니다. 자동 호출을 허용한 채 "알아서 하겠거니" 두는 건, 제가 예전에 겪은 오배포 사고처럼 언제든 발등을 찍을 수 있습니다. 스킬을 쓰더라도 **"사람만 누르는 버튼"과 "에이전트가 알아서 참조하는 지식"의 경계**는 반드시 frontmatter에 못 박아두는 게 좋습니다.

---

## 마치며

네 개를 비교하려다 "사실은 하나"라는 걸 발견한 게 이 글의 가장 큰 수확이었습니다. 2023년 MCP가 "도구를 붙이는 표준"을 열었다면, 2025~2026년의 Agent Skills는 **"절차적 지식을 붙이는 표준"** 을 연 셈입니다. 그리고 그 표준을 Anthropic이 만들어 개방했고, OpenAI를 포함한 생태계 전체가 채택하는 중입니다.

도구를 고르는 문제가 아니라, **한 번 잘 쓴 스킬이 모든 도구에서 굴러가게 하는 문제**가 되었습니다. 그게 표준화의 힘이죠.

### 참고 링크

- [Claude Code 스킬 문서](https://code.claude.com/docs/ko/skills)
- [OpenAI Skills 저장소 (deprecated)](https://github.com/openai/skills)
- [Codex Build Skills 문서](https://learn.chatgpt.com/docs/build-skills)
- [agentskills.io — Agent Skills 개방형 표준](https://agentskills.io/home)
