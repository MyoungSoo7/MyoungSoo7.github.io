---
layout: post
title: "\"Claude 개발자 도구 TOP 10\" 중 실제 클로드 플러그인은 3개였다 — 나머지 7개의 정체"
date: 2026-08-23 04:40:15 +0900
categories: [AI, Engineering]
tags: [claude-code, plugin, marketplace, mcp, skills, 검증]
---

이 이미지를 받았다. "Claude 개발자를 위한 GitHub 급상승 도구 TOP 10".

![Claude 개발자를 위한 GitHub 급상승 도구 TOP 10 — Orca, OmniRoute, Superpowers, Firecrawl, Karpathy Skills, OpenCode, Agent Reach, Everything Claude Code, MarkItDown, OpenMontage 를 카드 형태로 정리한 인포그래픽](/assets/images/claude-plugin-top10-source.jpg)

*이미지 출처: 이상선 님의 LinkedIn 게시물에 실린 정리 이미지, 원 출처는 텔레그램 채널 `t.me/aiinnovationstudio` 로 표기되어 있다.*

목록 자체는 유용하다. 다만 두 가지가 걸렸다.

첫째, **"+6,720" 같은 1주일 스타 증가 수치는 내가 검증할 방법이 없다.** GitHub API 는 현재 스타 수는 주지만 "최근 7일 증가분" 은 주지 않는다. 그래서 이 글에는 그 숫자를 옮겨 적지 않는다. 대신 **2026-08-23 04:50 KST 에 GitHub REST API 로 직접 조회한 현재 스타 수**를 쓴다.

둘째, 이게 진짜 궁금했던 건데 — **이 10개가 다 "클로드 플러그인" 인가?** 목록의 제목은 "Claude 개발자를 위한 도구" 지 "Claude 플러그인" 이 아니다. 그런데 이런 목록은 대체로 "설치하면 클로드가 강해지는 것들" 로 뭉뚱그려 읽힌다. 설치 경로가 전혀 다른 물건들이 한 표에 섞여 있으면, 깔다가 헤맨다.

그래서 판정 기준을 정하고 10개를 전부 돌려봤다.

---

## 1. 판정 기준 — 플러그인은 파일 하나로 정의된다

Claude Code 플러그인의 정의는 애매하지 않다. 공식 문서가 지정하는 매니페스트 경로가 있다.

> The manifest file at `.claude-plugin/plugin.json` defines your plugin's identity: its name, description, and version.
> — [Create plugins](https://code.claude.com/docs/en/plugins), Claude Code 공식 문서

플러그인 루트에 `.claude-plugin/plugin.json` 이 있고, 그 옆에 기능 디렉토리들이 놓인다. 공식 문서의 구조 표를 그대로 옮기면 이렇다.

| 디렉토리 | 용도 |
|---|---|
| `.claude-plugin/` | `plugin.json` 매니페스트가 들어가는 곳 |
| `skills/` | `<name>/SKILL.md` 형태의 스킬 |
| `commands/` | 평평한 마크다운 파일. 신규 플러그인은 `skills/` 를 쓸 것 |
| `agents/` | 커스텀 에이전트 정의 |
| `hooks/` | `hooks.json` 이벤트 핸들러 |
| `.mcp.json` | MCP 서버 설정 |
| `.lsp.json` | LSP 서버 설정 |
| `monitors/` | 백그라운드 모니터 설정 |
| `bin/` | 플러그인이 켜져 있는 동안 Bash 툴 `PATH` 에 추가되는 실행 파일 |
| `settings.json` | 플러그인이 켜질 때 적용되는 기본 설정 |

공식 문서는 흔한 실수도 명시해 뒀다 — `commands/`, `agents/`, `skills/`, `hooks/` 를 `.claude-plugin/` **안에** 넣지 말 것. 저 안에 들어가는 건 `plugin.json` 뿐이다.

여기서 중요한 구분이 하나 더 나온다. 공식 문서는 확장 방식을 **두 가지**로 나눈다.

- **Standalone** — `.claude/` 디렉토리에 스킬·훅을 두는 방식. 스킬 이름은 `/hello`. 개인 워크플로우·프로젝트 전용 커스터마이징용.
- **Plugin** — `.claude-plugin/plugin.json` 을 갖춘 자립 디렉토리. 스킬 이름은 `/plugin-name:hello`. 팀 공유·커뮤니티 배포·버전 릴리스용.

즉 **`.claude/skills/` 에 스킬을 잔뜩 넣어둔 리포는 "스킬을 제공하는 리포" 이지 "플러그인" 이 아니다.** 마켓플레이스에 올라가지 않고, `/plugin install` 로 깔리지 않고, 네임스페이스도 안 붙는다. 이 차이가 뒤에서 실제로 갈린다.

판정 방법은 단순하다. 각 리포의 루트 트리에 `.claude-plugin/` 이 있는지 GitHub API 로 확인하면 된다.

```bash
gh api repos/<owner>/<repo>/contents/.claude-plugin --jq '[.[].name] | join(",")'
```

---

## 2. 10개를 돌린 결과

스타 수는 2026-08-23 04:50 KST 조회값이다. 지금 보는 시점에는 당연히 달라져 있다.

| # | 도구 | 실제 리포 | ★ | `.claude-plugin/` | 실제 정체 |
|---|---|---|---:|---|---|
| 1 | Orca | `stablyai/orca` | 51,178 | 없음 | 데스크톱/모바일 앱 (ADE) |
| 2 | OmniRoute | `diegosouzapw/OmniRoute` | 53,162 | 없음 | 셀프호스트 AI 게이트웨이 |
| 3 | **Superpowers** | `obra/superpowers` | 276,110 | **있음** | **Claude Code 플러그인** |
| 4 | Firecrawl | `firecrawl/firecrawl` | 170,887 | 없음 | 웹 스크레이핑·검색 서비스 |
| 5 | **Karpathy Skills** | `multica-ai/andrej-karpathy-skills` | 205,234 | **있음** | **Claude Code 플러그인** |
| 6 | OpenCode | `anomalyco/opencode` | 200,309 | 없음 | 별도의 오픈소스 코딩 에이전트 |
| 7 | Agent Reach | `Panniantong/Agent-Reach` | 74,106 | 없음 | 파이썬 패키지 + MCP 연동 |
| 8 | **ECC** | `affaan-m/ECC` | 242,112 | **있음** | **Claude Code 플러그인** |
| 9 | MarkItDown | `microsoft/markitdown` | 175,489 | 없음 | 파이썬 라이브러리 (+MCP 패키지) |
| 10 | OpenMontage | `calesthio/OpenMontage` | 49,442 | 없음 | 비디오 제작 시스템 |

**10개 중 3개.** Superpowers, Karpathy Skills, ECC 만이 `.claude-plugin/plugin.json` 을 가진 진짜 Claude Code 플러그인이다.

나머지 7개가 나쁜 도구라는 뜻이 전혀 아니다. Firecrawl 도 MarkItDown 도 훌륭하다. 다만 **설치하는 방법이 다르다.** `/plugin install` 로 깔리는 건 3개뿐이고, 나머지는 각자의 방법(npm, pip, Docker, MCP 등록, 아예 별도 앱 설치)을 따로 알아봐야 한다.

---

## 3. 진짜 플러그인 3개를 열어봤다

### Superpowers (`obra/superpowers`, v6.3.0, MIT)

매니페스트 그대로:

```json
{
  "name": "superpowers",
  "description": "Core skills library for Claude Code: TDD, debugging, collaboration patterns, and proven techniques",
  "version": "6.3.0",
  "author": { "name": "Jesse Vincent", "email": "jesse@fsck.com" },
  "license": "MIT"
}
```

루트 구성은 `skills/` 와 `hooks/` 두 개뿐이다. 트리를 세어 보니 `skills/*/SKILL.md` 가 **14개**다.

```
brainstorming            dispatching-parallel-agents   executing-plans
finishing-a-development-branch   receiving-code-review  requesting-code-review
subagent-driven-development      systematic-debugging   test-driven-development
using-git-worktrees      using-superpowers             verification-before-completion
writing-plans            writing-skills
```

스타 27만짜리 리포의 알맹이가 마크다운 14장이라는 게 이 생태계의 성격을 잘 보여준다. 코드가 아니라 **과정을 강제하는 문장**이 자산이다. 구조를 더 뜯은 건 예전에 쓴 [Superpowers 의 구조]({% post_url 2026-07-10-superpowers-plugin-structure %}) 에 있다.

`.claude-plugin/marketplace.json` 도 같이 들어 있어서 이 리포 자체가 마켓플레이스로 동작한다 — 별도 카탈로그 없이 리포 하나만 추가하면 된다.

### Karpathy Skills (`multica-ai/andrej-karpathy-skills`, v1.0.0, MIT)

가장 작다. `skills/` 하나, `SKILL.md` **1개**. 매니페스트가 그 하나를 명시적으로 가리킨다.

```json
{
  "name": "andrej-karpathy-skills",
  "description": "Behavioral guidelines to reduce common LLM coding mistakes, derived from Andrej Karpathy's observations on LLM coding pitfalls",
  "skills": ["./skills/karpathy-guidelines"]
}
```

이미지에서는 "CLAUDE.md 파일 하나" 로 소개돼 있는데, 리포 설명도 실제로 "A single CLAUDE.md file to improve Claude Code behavior" 다. 플러그인 형태로도 포장돼 있는 것이다. 즉 **CLAUDE.md 로 붙일 수도, 플러그인으로 깔 수도 있다.** 목록에서 유일하게 두 방식을 다 지원한다.

### ECC (`affaan-m/ECC`, v2.2.0, MIT)

셋 중 압도적으로 크다. 매니페스트 설명이 "68 agents, 286 skills, 94 legacy command shims" 라고 주장하길래 트리를 직접 세어봤다.

| 항목 | 매니페스트 주장 | 트리 실측 |
|---|---:|---:|
| `agents/*.md` | 68 | **68** |
| `skills/*/SKILL.md` | 286 | **286** |
| `commands/*.md` | 94 | **94** |

정확히 일치한다. 여기에 `hooks/` 6개 파일과 `.mcp.json` 이 붙는다. `.mcp.json` 내용은 이거다.

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

**이 한 조각이 플러그인의 신뢰 경계를 보여준다.** ECC 를 설치하면 `npx -y chrome-devtools-mcp@latest` 가 내 머신에서 실행된다. `-y` 는 확인 프롬프트 없이 받겠다는 뜻이고, `@latest` 는 매번 최신을 끌어온다는 뜻이다. 나쁜 설정이라는 게 아니라 — MCP 서버를 번들한 플러그인은 **설치가 곧 남의 코드 실행**이라는 사실이 이 세 줄에 그대로 드러난다는 얘기다. 공식 문서도 같은 말을 한다.

> Plugins and marketplaces are highly trusted components that can execute arbitrary code on your machine with your user privileges. Only install plugins and add marketplaces from sources you trust.
> — [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins), Security 절

286개 스킬이 매 턴 컨텍스트를 먹는 것도 고려 대상이다. 공식 `/plugin` 화면은 설치 전에 **Context cost** 추정치와 **Will install** 목록(커맨드·에이전트·스킬·훅·MCP·LSP)을 보여준다. 큰 플러그인일수록 이걸 보고 결정하는 게 맞다.

---

## 4. 나머지 7개는 어떻게 붙는가

플러그인이 아니라고 못 쓰는 게 아니다. 경로가 다를 뿐이다. 루트 트리를 근거로 분류하면 이렇게 갈린다.

**(a) 스킬은 있는데 플러그인은 아닌 것 — `.claude/` standalone 방식**

- `calesthio/OpenMontage` — 루트에 `.claude/` 가 있고 그 안에 `commands/`, `skills/` 가 들어 있다. `.claude-plugin/` 은 없다. 즉 리포를 클론해서 그 디렉토리에서 작업할 때 쓰이는 프로젝트 스코프 구성이다. `.agents`, `.codex`, `.cursor`, `.windsurfrules` 도 같이 있어서 특정 에이전트 전용도 아니다.
- `firecrawl/firecrawl` — 루트에 `firecrawl-skills/`, `firecrawl-cli-skills/`, `firecrawl-workflows/` 디렉토리가 있다. 스킬 자산을 제공하지만 플러그인 매니페스트는 없다.

이 둘이 앞에서 말한 구분의 실물이다. **스킬을 제공한다 ≠ 플러그인이다.**

**(b) MCP 서버로 붙이는 것**

- `microsoft/markitdown` — `packages/` 아래에 `markitdown`, `markitdown-mcp`, `markitdown-ocr`, `markitdown-sample-plugin` 이 있다. MCP 서버 패키지가 따로 있으니 MCP 로 등록해 쓰는 물건이다.
- `Panniantong/Agent-Reach` — `pyproject.toml` 기반 파이썬 패키지. README 는 설치 문서 URL 을 에이전트에게 읽히는 방식을 안내하고, 플랫폼별로 MCP 연동을 쓴다. 참고로 이 리포는 브라우저 쿠키·세션을 다루므로 권한 범위를 반드시 읽고 붙여야 한다.

**(c) 애초에 클로드의 확장이 아닌 것**

- `anomalyco/opencode` — "The open source coding agent". Claude Code 를 확장하는 게 아니라 **대체하는** 별도 에이전트다.
- `stablyai/orca` — 여러 에이전트를 병렬로 굴리는 데스크톱/모바일 앱. 루트에 `electron.vite.config.ts`, `mobile/`, `native/`, `Casks/` 가 있다. 클로드를 그 안에서 굴리는 상위 도구지 플러그인이 아니다.
- `diegosouzapw/OmniRoute` — "one endpoint, 340 providers" 를 표방하는 셀프호스트 AI 게이트웨이. Docker·env 파일 중심 구성이다. 붙는 지점이 클로드가 아니라 **API 엔드포인트**다.

---

## 5. 캡처 목록의 URL 은 이미 낡아 있었다

부수적으로 발견한 건데, 이게 실무적으로 제일 쓸모 있는 교훈일 수 있다. 10개를 조회하는 동안 **리포 3개가 이미 이름이 바뀌어 있었다.** GitHub 은 리다이렉트를 해 주니 옛 URL 로도 도달은 되지만, 조회 결과로 돌아오는 정식 이름은 다르다.

| 목록/과거 표기 | 현재 정식 이름 |
|---|---|
| `sst/opencode` | `anomalyco/opencode` |
| `affaan-m/everything-claude-code` | `affaan-m/ECC` |
| `forrestchang/andrej-karpathy-skills` | `multica-ai/andrej-karpathy-skills` |

확인은 간단하다.

```bash
$ gh api repos/affaan-m/everything-claude-code --jq '.full_name'
affaan-m/ECC
```

정리 이미지 한 장의 수명이 얼마나 짧은지를 보여준다. 이런 목록은 **스크린샷이 아니라 리포 주소로** 보관하고, 쓰기 직전에 한 번 조회하는 게 맞다.

---

## 6. 그래서 뭘 어떻게 깔 것인가

플러그인 3개는 표준 경로로 깔린다. 마켓플레이스를 등록하고 설치하는 2단계다.

```shell
/plugin marketplace add <owner>/<repo>
/plugin install <plugin-name>@<marketplace-name>
```

공식 마켓플레이스도 있다. Anthropic 이 운영하는 건 두 개다.

- `claude-plugins-official` — Anthropic 이 큐레이션. 처음 대화형으로 실행하면 자동 등록된다. 안 됐으면 `/plugin marketplace add anthropics/claude-plugins-official`.
- `claude-community` — 자동 검증·안전성 스크리닝을 통과한 서드파티 플러그인. `/plugin marketplace add anthropics/claude-plugins-community` 로 직접 추가하고 `/plugin install <name>@claude-community` 로 설치한다. 승인된 플러그인은 특정 커밋 SHA 에 핀 고정된다.

공식 마켓플레이스에 이미 들어 있는 것부터 보는 게 순서다. 언어별 LSP 플러그인(`typescript-lsp`, `pyright-lsp`, `rust-analyzer-lsp` 등), 외부 연동 MCP 번들(`github`, `slack`, `linear`, `notion`, `figma`, `sentry` 등), `security-guidance`, `commit-commands`, `pr-review-toolkit`, `plugin-dev` 같은 것들이다. TOP 10 목록에는 이 중 하나도 없다 — 목록의 성격이 "급상승" 이지 "표준" 이 아니기 때문이다.

설치 전에 확인할 게 있다면 이 정도다.

1. `.claude-plugin/plugin.json` 이 실제로 있는지 (없으면 `/plugin install` 대상이 아니다)
2. `hooks/`, `.mcp.json`, `bin/` 이 있는지 — 있으면 **내 머신에서 남의 코드가 돈다**
3. `/plugin` 의 **Context cost** 와 **Will install** 목록 — 매 턴 붙는 비용
4. 안 쓰게 되면 `/plugin` 의 Installed 탭에서 **Not used recently** 로 잡아내 정리

---

## 정리

- 검증 기준은 스타 수가 아니라 **`.claude-plugin/plugin.json` 의 존재**다. 목록의 10개 중 3개만 통과했다.
- 통과한 셋: **Superpowers**(스킬 14개+훅), **Karpathy Skills**(스킬 1개), **ECC**(에이전트 68·스킬 286·커맨드 94·훅·MCP, 매니페스트 주장과 트리 실측이 일치).
- 나머지 7개는 standalone `.claude/` 구성이거나, MCP 서버이거나, 아예 별도 앱·게이트웨이·경쟁 에이전트다. 좋고 나쁨이 아니라 **설치 경로와 신뢰 경계가 다르다.**
- 정리 이미지의 리포 주소 3개는 이미 낡아 있었다. 목록은 조회로 갱신해서 쓰자.
- 이 글에는 이미지의 "1주일 스타 증가" 수치를 옮기지 않았다. 검증 방법이 없기 때문이다.

---

## References

**Claude Code 공식 문서**

- [Create plugins](https://code.claude.com/docs/en/plugins) — `.claude-plugin/plugin.json` 매니페스트, 플러그인 디렉토리 구조, standalone 대비 플러그인, `--plugin-dir` 테스트
- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins) — `/plugin marketplace add`, `/plugin install <name>@<marketplace>`, 공식·커뮤니티 마켓플레이스, Context cost 와 Will install, Security 절
- [Plugins reference](https://code.claude.com/docs/en/plugins-reference) — 매니페스트 스키마, 버전 관리, LSP·모니터 규격

**리포지토리 (2026-08-23 04:50 KST 조회)**

- [obra/superpowers](https://github.com/obra/superpowers)
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
- [affaan-m/ECC](https://github.com/affaan-m/ECC)
- [stablyai/orca](https://github.com/stablyai/orca) · [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) · [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) · [anomalyco/opencode](https://github.com/anomalyco/opencode) · [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) · [microsoft/markitdown](https://github.com/microsoft/markitdown) · [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage)

**조회 방법**

- [GitHub REST API — Repositories](https://docs.github.com/en/rest/repos/repos) · [Repository contents](https://docs.github.com/en/rest/repos/contents) · [Git trees](https://docs.github.com/en/rest/git/trees)

**이미지 출처**

- 이상선 님 LinkedIn 게시물에 실린 정리 이미지. 이미지 하단에 원 출처가 `https://t.me/aiinnovationstudio` 로 표기되어 있다. 이미지 내 "1주일 스타 증가" 수치는 본문에 인용하지 않았다.
