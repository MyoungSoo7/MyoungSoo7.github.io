---
layout: post
title: "상자 안에 무엇을 넣었나 — Claude Code와 Codex의 기본 스킬 비교"
date: 2026-09-11 23:52:56 +0900
categories: [ai-agent, engineering]
tags: [claude-code, codex, agent-skills, SKILL-md, bundled-skills, plugins, harness]
---

두 도구의 스킬 **형식**을 비교하는 일은 이제 의미가 옅어졌다. 둘 다 같은 표준을 쓰기 때문이다. Anthropic은 "Claude Code skills follow the Agent Skills open standard"라고 적고([Claude Code Skills](https://code.claude.com/docs/en/skills)), OpenAI도 "Skills build on the open agent skills standard"라고 적는다([Codex Agent Skills](https://developers.openai.com/codex/skills)). 폴더 하나에 `SKILL.md`, 필수 필드는 `name`과 `description`, 선택적으로 `scripts/` · `references/` · `assets/` — [명세](https://agentskills.io/specification)가 정한 그대로다.

형식이 같아지면 비교할 게 없어지는 게 아니라, **비교할 지점이 옮겨간다.** 같은 포맷을 손에 쥔 두 팀이 "그럼 상자 안에 무엇을 미리 넣어둘 것인가"를 서로 다르게 답했다면, 그 목록이 각 팀이 생각하는 *에이전트의 약한 고리*를 드러낸다. 이 글은 그 목록을 본다.

## 1. 상자 안에 든 것

**Claude Code — 번들 스킬.** 공식 문서가 예시로 드는 것은 `/doctor`, `/code-review`, `/batch`, `/debug`, `/loop`, `/claude-api`이고, 별도 절로 묶인 3종 세트가 `/run` · `/verify` · `/run-skill-generator`다. 문서는 이들을 "prompt-based: they give Claude detailed instructions and let it orchestrate the work using its tools"라고 정의한다 — 고정 로직을 실행하는 내장 명령과 달리, 지시문을 주고 도구 사용은 모델에 맡긴다. 끄고 싶으면 `disableBundledSkills` 설정 하나로 전부 꺼지되 `/doctor`만 남는다.

**Codex — 시스템/큐레이티드 스킬.** 문서의 스킬 스코프 표에서 `SYSTEM` 칸은 "Bundled with Codex by OpenAI. Useful skills relevant to a broad audience such as the skill-creator and plan skills"로 설명된다. 그 밖의 것은 `$skill-installer`로 가져온다(`$skill-installer linear`). 카탈로그 저장소였던 [openai/skills](https://github.com/openai/skills)는 README에 "This repository is deprecated"를 달고 [openai/plugins](https://github.com/openai/plugins)로 넘어갔고, 그쪽 README가 대표 예시로 드는 것은 `figma` · `notion` · `build-ios-apps` · `build-macos-apps` · `build-web-apps` · `expo` · `netlify` · `remotion` · `google-slides`다.

나란히 놓으면 성격 차이가 바로 보인다.

| | Claude Code 번들 | Codex 시스템 + 대표 플러그인 |
| --- | --- | --- |
| 무엇을 향하나 | 에이전트 자신의 루프 | 스킬 저작과 외부 제품 연동 |
| 대표 항목 | `/debug` `/code-review` `/verify` `/run` `/loop` `/batch` `/doctor` | `skill-creator` `plan` `skill-installer`, figma·notion·expo·netlify |
| 기본 제공 범위 | 세션마다 전부 로드 | 시스템 소수 + 나머지는 설치 |
| 끄는 방법 | `disableBundledSkills`(`/doctor` 제외) | `~/.codex/config.toml`의 `[[skills.config]]`로 개별 비활성 |

## 2. 안쪽을 보는 스킬 vs 바깥을 보는 스킬

Claude Code가 상자에 넣은 것들은 거의 전부 **에이전트 자신의 출력을 의심하는 도구**다. `/debug`는 실패를 진단하고, `/code-review`는 방금 만든 diff를 되본다. 그중 가장 노골적인 것이 `/verify`인데, 문서의 정의부터가 방어적이다 — "Build and run your app to confirm a code change does what it should, **without falling back to tests or type checks**". 테스트가 초록불이어도 그건 앱이 도는 증거가 아니라는 전제가 스킬 설명문에 박혀 있다.

Codex가 상자에 넣은 것은 반대쪽이다. `skill-creator`는 스킬을 만들고, `skill-installer`는 남의 스킬을 가져오고, 플러그인 카탈로그는 Figma·Notion·Expo·Netlify로 나간다. 즉 **에이전트를 어떻게 확장하고 배포할 것인가**가 기본 제공의 중심이다. 실제로 Codex 문서는 스킬과 플러그인의 역할을 명시적으로 갈라둔다: "Skills are the authoring format for reusable workflows. Plugins are the installable distribution unit."

이 차이를 "누가 낫다"로 읽으면 틀린다. 각 팀이 *기본값으로 해결해줘야 할 문제*를 다르게 본 것에 가깝다. 한쪽은 "에이전트가 자기 결과를 과신하는 것"을, 다른 쪽은 "쓸 만한 워크플로가 팀 사이에 안 퍼지는 것"을 기본 제공으로 막으려 했다.

## 3. 스킬이 자기 자신을 고쳐 쓴다 — 그리고 그 흉터

Claude Code 쪽에만 있는 설계가 하나 있다. **번들 스킬이 디스크에 새 스킬을 써 놓는다.**

`/run-skill-generator`는 앱을 깨끗한 환경에서 한 번 띄워본 뒤 "무엇이 통했는지(설치 명령, 환경변수, 실행 스크립트)"를 잡아 `.claude/skills/run-<이름>/`으로 커밋한다. 그다음부터 `/run`과 `/verify`는 매번 추론하지 않고 기록된 레시피를 따른다. `/verify`도 같은 일을 스스로 한다 — 레시피 없이 앱을 굴려야 했으면 통한 절차를 `.claude/skills/verify/SKILL.md`에 적고, 리포 루트에 적힌 그 파일이 **번들 `/verify`를 대체한다**(v2.1.200+).

여기서 흥미로운 건 문서가 이 기능의 *실패했던 버전*을 그대로 남겨뒀다는 점이다:

> Claude edits the recorded file only when it steered a run wrong, such as a command that failed or a missing step, so you can commit the file without per-session diffs. **Before v2.1.205, the bundled skill told Claude to fold in anything a run learned, which caused frequent merge conflicts.**

"배운 걸 다 적어라"는 초판은 세션마다 파일이 흔들려서 팀이 커밋할 수 없는 물건이 됐고, "잘못 인도했을 때만 고쳐라"로 좁혀서 해결했다. 자기수정 스킬을 만들려는 사람이 반드시 먼저 읽어야 할 대목이다 — 기록 조건을 좁히지 않으면 산출물이 아니라 소음이 된다. Codex 문서에는 이에 대응하는 자기기록 메커니즘이 없다. Codex는 같은 필요를 `scripts/`(결정적 실행)와 `agents/openai.yaml`(의존성 선언)로 *사람이 미리 적어두는* 쪽으로 푼다.

## 4. 암묵 호출을 되돌린 사건

스킬은 두 방식으로 켜진다. 사람이 부르거나(`/name`, `$name`), 모델이 `description`을 보고 스스로 고르거나. 둘 다 양쪽에 있다. 그런데 Claude Code 문서에 날짜가 박힌 **후퇴** 기록이 있다:

> others, including `/verify` and `/code-review`, run only when you invoke them, which keeps you in control of when these longer-running checks spend time and tokens. **Before v2.1.215, Claude could also run `/verify` and `/code-review` on its own.**

즉 비싼 검증 스킬의 자동 호출을 한 번 열었다가 닫았다. 이유도 적혀 있다 — 시간과 토큰. 에이전트에게 "알아서 검증해"를 허용하면 검증을 *지나치게* 자주 한다는 게, 기본값을 되돌릴 만큼의 문제였다는 뜻이다.

Codex는 같은 스위치를 스킬 작성자 쪽에 둔다. `agents/openai.yaml`의 `policy.allow_implicit_invocation: false`를 켜면 모델이 못 고르고 `$skill` 명시 호출만 남는다. 반면 Claude Code는 축을 둘로 쪼갰다 — `disable-model-invocation`(모델이 못 부름)과 `user-invocable: false`(사람이 못 부름). 후자는 "사용자가 직접 부를 일 없는 배경 지식"용이다. 한쪽은 스위치 하나, 다른 쪽은 2×2 격자다.

## 5. 확장을 어디에 두느냐 — 그리고 그 이식성 비용

가장 구조적인 차이는 **벤더 확장을 어디에 적느냐**다.

Claude Code는 frontmatter를 확장했다. 공식 표에 있는 필드만 해도 `context: fork`(서브에이전트 격리 실행), `agent`, `background`, `model`, `effort`, `allowed-tools`, `disallowed-tools`, `hooks`, `paths`, `arguments`, `argument-hint`, `shell`, `when_to_use` 등이다. 본문에서도 확장이 돈다 — `` !`git diff HEAD` `` 한 줄을 적으면 모델이 파일을 보기 *전에* 셸이 먼저 돌아 그 출력이 자리에 박힌다(dynamic context injection).

Codex는 `SKILL.md`를 명세 그대로 두고, 벤더 확장을 **옆 파일**로 뺐다. `agents/openai.yaml`이 `interface`(표시 이름·아이콘·기본 프롬프트), `policy`(암묵 호출 허용 여부), `dependencies`(필요한 MCP 서버)를 담는다.

이 선택의 대가는 Anthropic 문서가 자기 입으로 적어놨다. 스펙 밖 필드가 섞인 스킬을 claude.ai나 Skills API로 올리면 **무시가 아니라 하드 에러**다:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint.
Allowed properties are: allowed-tools, compatibility, description, license, metadata, name
```

같은 문서의 표가 더 분명하다. Claude Code 안에서는 모든 필드가 되지만, claude.ai 업로드·Skills API·`package_skill.py` 경로에서 허용되는 건 `name` `description` `license` `compatibility` `metadata` `allowed-tools` 여섯 개뿐이다. **Claude Code의 확장은 Anthropic 자사 제품 사이에서도 이식되지 않는다.** Codex의 사이드카 방식은 이 문제를 구조적으로 안 만든다 — `SKILL.md`는 어디로 가든 스펙에 맞고, 벤더 파일은 모르는 도구가 그냥 무시하면 된다.

바꿔 말하면 이건 표현력과 이식성의 교환이다. `context: fork` 한 줄로 서브에이전트를 띄우는 건 사이드카로는 안 되는 일이다.

## 6. 잘리는 방식이 다르다

스킬이 많아지면 목록 자체가 컨텍스트를 먹는다. 두 쪽이 서로 다른 지점에서 자른다.

Codex는 **목록 전체**에 예산을 건다. 문서에 따르면 초기 스킬 목록은 "roughly 2% of the model's context window, or 8,000 characters when the context window is unknown"으로 제한되고, 넘치면 먼저 설명문을 줄이고, 그래도 안 되면 일부 스킬을 목록에서 빼고 경고를 띄운다. 그래서 문서가 작성 요령을 따로 못 박는다 — "Front-load the key use case and trigger words so Codex can still match the skill if descriptions are shortened." **설명문이 줄어도 앞부분은 살아남으니 트리거 단어를 앞에 두라**는 뜻이다.

Claude Code는 **스킬 하나**에 예산을 건다. `description`과 `when_to_use`를 합친 텍스트가 목록에서 1,536자에서 잘린다. 그래서 문서의 요령도 "Put the key use case first"다.

결과적으로 실패 모드가 다르다. Codex 쪽은 스킬을 많이 깔수록 *모든* 스킬의 설명이 함께 얇아지다가 일부가 목록에서 사라진다(경고는 뜬다). Claude Code 쪽은 스킬 하나가 길어도 다른 스킬을 밀어내진 않는다. 스킬을 수십 개 쌓아둔 사람에게는 이 차이가 실제로 체감된다.

## 7. 놓아두는 위치도 다르다

사소해 보이지만 방향성이 드러나는 대목. Claude Code는 `~/.claude/skills/`와 프로젝트 `.claude/skills/`를 읽는다. Codex는 **`.agents/skills`** 를 읽는다 — CWD, 그 위 디렉터리, 리포 루트, 그리고 사용자 홈은 `$HOME/.agents/skills`, 머신 공용은 `/etc/codex/skills`. 벤더 이름이 안 들어간 경로를 고른 쪽은 Codex다.

이름 충돌 처리도 반대다. Claude Code는 **결정적 우선순위**를 정해뒀다(enterprise > personal > project, 스킬 > 커맨드, 로컬 > claude.ai 동기화, 플러그인은 `plugin:skill`로 네임스페이스 분리). Codex는 병합하지 않는다 — "If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors." 한쪽은 규칙으로 자동 해소하고, 한쪽은 둘 다 보여주고 사람에게 고르게 한다.

## 8. 그래서 고를 때 갈리는 지점

- **스킬을 여러 도구에 돌려 쓸 생각이라면** — `SKILL.md`를 스펙 여섯 필드로 유지하라. Claude Code는 스펙에 맞는 frontmatter를 그대로 읽으니 손해가 없고, 확장 필드를 쓰는 순간 claude.ai·API 경로가 막힌다.
- **서브에이전트 격리·모델 전환·훅 등록까지 스킬 한 장으로 하고 싶다면** — 그건 Claude Code 확장 필드로만 된다. 이식성을 포기하는 선택임을 알고 하면 된다.
- **스킬을 팀에 배포하는 게 목적이라면** — 양쪽 다 답은 "플러그인"이다. Codex는 저장소 자체를 skills에서 plugins로 옮겼고, Claude Code도 플러그인 스킬만 `plugin:skill` 네임스페이스를 받아 충돌에서 자유롭다.
- **스킬이 수십 개라면** — Codex에서는 설명문 앞부분에 트리거 단어를 몰아넣어라. 목록이 얇아질 때 뒤쪽부터 사라진다.
- **검증을 자동으로 돌릴지** — Claude Code는 그 기본값을 한 번 열었다가 닫았다(v2.1.215). 비용 때문이었다. 자동 검증을 붙이려는 사람은 같은 비용을 만나게 된다.

## 9. 유보

이 글은 **공식 문서에 적힌 설계**만 비교했다. 어느 쪽 스킬이 실제 작업에서 더 잘 트리거되는지, 암묵 호출 정확도가 어떤지는 중립 제3자의 헤드투헤드 측정이 공개돼 있지 않다 — 그래서 여기에 성능 우열은 쓰지 않았다. 버전 번호(v2.1.200 · v2.1.205 · v2.1.215)와 컨텍스트 예산(약 2% / 8,000자 / 1,536자)은 전부 각 벤더 문서의 서술을 그대로 옮긴 것이고, 문서는 예고 없이 바뀐다. 읽는 시점에는 원문을 한 번 확인하는 편이 안전하다.

## References

- Anthropic, [Extend Claude with skills — Claude Code Docs](https://code.claude.com/docs/en/skills) (번들 스킬 목록, `/run`·`/verify`·`/run-skill-generator`, frontmatter 전체 표, 스펙 외 필드 하드 에러, v2.1.200/205/215 서술, 1,536자 절단)
- OpenAI, [Agent Skills — Codex](https://developers.openai.com/codex/skills) (스킬 스코프 표, `$skill-installer`, `agents/openai.yaml`, 초기 목록 약 2% / 8,000자 예산, 동명 스킬 비병합)
- OpenAI, [Customization — Codex](https://developers.openai.com/codex/concepts/customization) (AGENTS.md·메모리·스킬·MCP·서브에이전트의 역할 분담)
- [Agent Skills Specification — agentskills.io](https://agentskills.io/specification) (`name` 64자·`description` 1024자 등 필수/선택 필드, progressive disclosure 3단계)
- [openai/skills](https://github.com/openai/skills) (deprecated 고지) · [openai/plugins](https://github.com/openai/plugins) (대표 플러그인 목록)
