---
layout: post
title: "Claude Code 를 넓히는 GitHub 프로젝트 20선 — 리포를 직접 열어 확인한 기록"
date: 2026-11-28 15:19:23 +0900
categories: [ai, tools]
tags: [claude-code, mcp, agent-skills, multi-agent, developer-tools, open-source]
---

텔레그램으로 "Claude Code 활용도를 높여줄 GitHub 프로젝트 20가지"라는 목록이 돌아다닌다. 목록 자체는 쓸 만하지만, 이런 큐레이션은 설명이 한 줄씩이고 출처가 홍보 채널이라 그대로 믿기 어렵다. 그래서 **20개 리포를 GitHub API 로 하나씩 조회**해 실제로 있는지, 리포가 스스로 뭐라고 설명하는지, 라이선스와 최근 활동은 어떤지 확인했다.

> **읽는 법.** 아래 "한 줄 설명"은 각 리포의 GitHub 공식 description 을 옮긴 것이다. 즉 **만든 쪽의 주장**이다. "토큰 60–90% 절감" 같은 수치는 벤더 주장이며, 이 글에서 독립 재현하지 않았다. 20개를 서로 비교한 중립 벤치마크는 찾지 못했다(부재). 스타 수·라이선스·마지막 push 날짜는 2026-11-28 에 [GitHub REST API](https://docs.github.com/en/rest/repos/repos#get-a-repository) `GET /repos/{owner}/{repo}` 로 조회한 값이다.

---

## 먼저 알아둘 배경: Claude Code 의 확장 지점 4개

20개 프로젝트는 결국 Claude Code 가 공식으로 열어 둔 몇 개의 구멍 중 하나에 꽂힌다. 어디에 꽂히는지 알면 서로 겹치는 도구를 덜 깔게 된다.

| 확장 지점 | 무엇을 바꾸나 | 공식 문서 |
|---|---|---|
| **MCP 서버** | 에이전트가 부를 수 있는 *도구*를 추가 | [Model Context Protocol](https://modelcontextprotocol.io/) · [Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp) |
| **Hooks** | 도구 호출 전후·세션 시작 등 *이벤트*에 스크립트를 끼움 | [Claude Code Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) |
| **Skills** | 필요할 때만 로드되는 *지시문·스크립트 묶음* | [Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) |
| **Subagents / Plugins** | 별도 컨텍스트의 *하위 에이전트*, 그리고 이것들을 묶어 배포하는 단위 | [Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents) · [Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins) |

여기에 더해 Claude Code **바깥**에서 세션을 감싸는 도구(원격 제어, 프로바이더 전환, 사용량 집계)가 있다. 아래 분류 끝에 각 도구가 어느 지점을 쓰는지 적었다.

---

## 1. 컨텍스트·토큰 절약

컨텍스트 창은 유한하고, 도구 출력(테스트 로그, `git diff`, 빌드 출력)이 그 창을 가장 빨리 채운다. 이 묶음은 "모델에게 덜 보여주기" 또는 "다음 세션에 필요한 것만 넘기기"를 노린다.

| 프로젝트 | 리포 설명(벤더 주장) | 라이선스 | ★ | 언어 |
|---|---|---|---|---|
| [RTK](https://github.com/rtk-ai/rtk) | 자주 쓰는 개발 명령의 출력을 줄여 LLM 토큰 소비를 60–90% 줄이는 CLI 프록시. 단일 Rust 바이너리 | Apache-2.0 | 88,064 | Rust |
| [claude-mem](https://github.com/thedotmack/claude-mem) | 세션 중 에이전트가 한 일을 캡처·AI 압축해서 다음 세션에 관련 컨텍스트로 주입 | Apache-2.0 | 120,258 | TypeScript |
| [Beads](https://github.com/gastownhall/beads) | "코딩 에이전트를 위한 메모리 업그레이드" — 작업과 의존성을 이슈 그래프로 관리 | MIT | 29,175 | Go |
| [context-mode](https://github.com/mksglu/context-mode) | 도구 출력을 컨텍스트 밖(샌드박스 + SQLite FTS5 검색)에 두는 로컬 플러그인. "컨텍스트 바이트 99% 감소", 텔레메트리 없음 | 미분류(NOASSERTION) | 34,552 | JavaScript |

- **꽂히는 곳.** RTK 는 *hook* 으로 셸 명령을 가로채 압축본을 돌려준다. context-mode 도 hook·MCP 로 출력을 바깥에 저장한다. claude-mem 은 세션 시작 hook 으로 기억을 주입한다. Beads 는 에이전트가 직접 부르는 CLI 다.
- **겹침 주의.** RTK 와 context-mode 는 같은 문제(도구 출력 비대)를 푼다. 둘 다 깔면 같은 출력이 두 번 가공된다. 하나만 고르는 편이 낫다.
- **트레이드오프.** 압축은 정보 손실이다. 에러 메시지 한 줄이 잘려서 원인을 못 찾는 경우가 생길 수 있다. 압축 도구를 쓸 때는 원본 출력을 다시 볼 수 있는 탈출구가 있는지부터 확인해 두자.
- **라이선스.** context-mode 의 `NOASSERTION` 은 GitHub 이 라이선스 파일을 표준 SPDX 로 분류하지 못했다는 뜻이다. 회사에서 쓸 거라면 LICENSE 원문을 직접 읽어야 한다.

## 2. 코드 이해·브라우저 연동

grep 과 파일 읽기만으로는 큰 코드베이스에서 "이 함수 누가 부르지?"를 매번 비싸게 다시 계산한다. 이 묶음은 *구조화된 질의 수단*을 MCP 도구로 준다.

| 프로젝트 | 리포 설명(벤더 주장) | 라이선스 | ★ | 언어 |
|---|---|---|---|---|
| [Graphify](https://github.com/Graphify-Labs/graphify) | 코드·문서·SQL 스키마·설정·PDF 를 질의 가능한 지식 그래프로 변환. 로컬 결정론적 AST 파싱, 벡터 스토어 없음 | Apache-2.0 | 154,338 | Python |
| [Serena](https://github.com/oraios/serena) | 의미 기반 검색·편집을 제공하는 MCP 툴킷 — "에이전트를 위한 IDE" | 미분류(NOASSERTION) | 31,765 | Python |
| [Context7](https://github.com/upstash/context7) | AI 에이전트용 최신 라이브러리 문서 제공 플랫폼 | MIT | 65,560 | TypeScript |
| [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 코딩 에이전트를 위한 Chrome DevTools | Apache-2.0 | 59,652 | TypeScript |

- **Serena** 는 LSP(Language Server Protocol) 위에서 심볼 단위로 찾고 고친다. 텍스트 치환이 아니라 "이 메서드 정의"를 대상으로 삼는 방식이다. 원리는 [LSP 사양](https://microsoft.github.io/language-server-protocol/)과 같다.
- **Graphify** 는 벡터 임베딩 대신 AST 를 파싱해 그래프를 만든다고 밝힌다. 같은 입력이면 같은 그래프가 나오고, 엣지마다 근거가 붙는다는 점을 내세운다.
- **Context7** 은 모델이 학습 시점 이후 바뀐 API 를 옛 문법으로 쓰는 문제를 겨냥한다.
- **Chrome DevTools MCP** 는 Chrome DevTools 팀 계정(`ChromeDevTools`)이 직접 운영하는 리포다. 콘솔·네트워크·성능 트레이스를 에이전트가 읽게 해 준다. 같은 목록 안에서도 *1차 벤더가 만든 것*과 *개인이 만든 것*이 섞여 있다는 점을 구분해 둘 만하다.

## 3. 개발 방법론·스킬

이 묶음은 도구라기보다 **일하는 방식을 주입**한다. 대부분 Skills·slash command·subagent 정의 파일의 모음이다.

| 프로젝트 | 리포 설명(벤더 주장) | 라이선스 | ★ | 언어 |
|---|---|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | 에이전트 스킬 프레임워크이자 소프트웨어 개발 방법론 (브레인스토밍→계획→TDD) | MIT | 328,495 | Shell |
| [Spec Kit](https://github.com/github/spec-kit) | 명세 주도 개발(SDD) 툴킷 | MIT | 152,386 | Python |
| [gstack](https://github.com/garrytan/gstack) | Garry Tan 의 Claude Code 설정. CEO·디자이너·엔지니어링 매니저·릴리스 매니저·문서·QA 역할의 도구 23개 | MIT | 142,829 | TypeScript |
| [Anthropic Agent Skills](https://github.com/anthropics/skills) | Agent Skills 공개 저장소 | 루트 LICENSE 미표기* | 201,613 | Python |

\* GitHub API 의 `license` 필드가 비어 있다. README 는 "많은 스킬이 Apache 2.0 오픈소스"이고 docx·pdf·pptx·xlsx 스킬도 Apache 2.0 이라고 밝힌다([anthropics/skills README](https://github.com/anthropics/skills#readme)). 라이선스가 스킬 폴더 단위로 붙어 있으니, 쓰려는 스킬 폴더의 LICENSE 를 확인하면 된다.

- **Spec Kit** 은 `github` 조직 공식 리포다. 요구사항 명세 → 계획 → 작업 분해 → 구현 순서를 강제한다. 에이전트가 "일단 짜고 보는" 경향을 문서로 막는 접근이다.
- **Anthropic Agent Skills** 는 Skills 형식을 정의한 쪽의 예제 저장소다. 직접 스킬을 만들 거라면 다른 큐레이션보다 이 리포의 구조(`SKILL.md` front matter + 보조 파일)를 먼저 보는 게 맞다. 형식 사양은 [Agent Skills 문서](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)에 있다.
- **함정 하나.** 스킬 front matter 는 YAML 이다. 한국어 설명에 `예: /명령 인자` 처럼 *콜론+공백*이 들어가면 따옴표 없이는 파싱이 깨지고, 그 스킬은 **에러 없이 목록에서 사라진다.** 필자 환경에서 스킬 5개가 이 이유로 몇 달간 조용히 죽어 있었다. `description:` 값은 항상 따옴표로 감싸는 게 안전하다([YAML 1.2 사양, plain scalar 제약](https://yaml.org/spec/1.2.2/#733-plain-style)).

## 4. 멀티 에이전트 협업

하나의 세션이 순서대로 하던 일을 여러 에이전트에 나눈다. 병렬화의 대가는 **충돌**이다. 같은 파일을 동시에 고치면 깨진다. 그래서 이 묶음의 핵심 차이는 "어떻게 격리하느냐"에 있다.

| 프로젝트 | 리포 설명(벤더 주장) | 라이선스 | ★ | 언어 |
|---|---|---|---|---|
| [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | 팀 우선 멀티 에이전트 오케스트레이션 | MIT | 41,102 | TypeScript |
| [Ruflo](https://github.com/ruvnet/ruflo) | 에이전트 스웜·자율 워크플로 조정. 적응형 메모리, 페더레이션, 벡터 RAG | MIT | 82,568 | TypeScript |
| [Orca](https://github.com/stablyai/orca) | 자기 구독(Claude Code·Codex 등)으로 봇 여러 대를 굴리는 앱. 데스크톱·모바일·원격 런타임 | MIT | 142,826 | TypeScript |
| [wshobson/agents](https://github.com/wshobson/agents) | Claude Code·Codex·Cursor 등용 플러그인·에이전트·스킬·명령을 Markdown 한 번으로 작성해 각 도구로 변환 | MIT | 42,995 | Python |

- **격리 수단은 대개 git worktree 다.** 한 저장소에서 작업 디렉터리를 여러 개 만들어 브랜치별로 따로 체크아웃하는 git 기본 기능이다([git-worktree 문서](https://git-scm.com/docs/git-worktree)). 원 목록은 Orca 를 "worktree 기반"이라 소개했다. 하지만 지금 리포 설명은 "여러 구독으로 봇 함대를 굴리는 앱"으로 범위가 넓어져 있다. 큐레이션 문구가 리포보다 늦을 수 있다는 예다.
- **현실 체크.** 필자는 같은 텔레그램 채팅에 Claude 세션 여러 개를 붙여 운영한다. 병렬의 이득은 조사·검토에서 크다. 반면 *발행·push* 처럼 결과물이 남는 일은 실행 횟수만큼 결과도 늘어난다. 같은 요청에 세션 여럿이 반응해 하루에 블로그 글 10편이 나간 적도 있다. 오케스트레이터를 고를 때 "누가 최종 쓰기 권한을 갖는가"를 먼저 봐야 하는 이유다.
- **wshobson/agents** 는 다른 셋과 성격이 다르다. 실행기가 아니라 *정의 파일 모음 + 변환기*다.

## 5. 제어·모니터링

Claude Code 세션 **바깥**에서 붙는 도구들이다.

| 프로젝트 | 리포 설명(벤더 주장) | 라이선스 | ★ | 언어 |
|---|---|---|---|---|
| [Happy](https://github.com/slopus/happy) | Claude·Codex·Grok 을 한 앱에서 조정. 이미 내는 구독을 재사용 | MIT | 24,874 | Swift |
| [CC Switch](https://github.com/farion1231/cc-switch) | Claude Code·Codex·OpenCode 등을 위한 크로스플랫폼 데스크톱 올인원 도우미 | MIT | 157,704 | Rust |
| [Claude HUD](https://github.com/jarrodwatts/claude-hud) | 컨텍스트 사용량·활성 도구·실행 중 에이전트·할 일 진행을 보여 주는 Claude Code 플러그인 | MIT | 29,322 | JavaScript |
| [ccusage](https://github.com/ccusage/ccusage) | `npx ccusage` — 로컬 사용 기록에서 토큰·비용 리포트 | MIT | 19,629 | Rust |

- **Happy** 는 원 목록에서 "모바일 원격 제어"로 소개됐다. 지금 리포 설명은 여러 에이전트를 한 앱에서 조정하는 쪽으로 넓어졌다.
- **CC Switch** 는 프로바이더 설정(엔드포인트·키)을 바꿔 준다. 리포 설명에 "공식 사이트는 ccswitch.io 뿐"이라고 따로 적혀 있다. 같은 이름을 쓰는 사칭 배포처가 있다는 경고로 읽힌다. API 키를 다루는 도구이니 설치 경로를 꼭 확인할 것.
- **Claude HUD** 는 Claude Code 의 [status line](https://docs.anthropic.com/en/docs/claude-code/statusline) 확장 지점을 쓴다.
- **ccusage** 는 코딩 에이전트 CLI 가 로컬에 남긴 사용 데이터를 읽어 일·주·월·세션 단위 리포트를 만든다([ccusage README](https://github.com/ccusage/ccusage/tree/main/apps/ccusage)). 별도 계정 연동 없이 로컬 데이터만 본다는 점이 장점이다. 원 목록 시점과 달리 현재 주 언어는 Rust 로 바뀌어 있다.

---

## 고르는 기준 — 20개를 다 깔면 안 되는 이유

1. **확장 지점이 겹치면 하나만.** 같은 hook(셸 출력 가공)이나 같은 세션 시작 주입을 두 도구가 쓰면 서로의 결과를 다시 가공한다. 위 분류마다 "꽂히는 곳"을 적은 이유다.
2. **스킬·MCP 도구는 공짜가 아니다.** MCP 도구 정의와 스킬 설명은 컨텍스트에 상시 올라간다. Skills 문서가 *필요할 때만 본문을 로드*하는 구조(progressive disclosure)를 강조하는 것도 이 비용 때문이다([Agent Skills overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)). 압축 도구를 깔고 동시에 MCP 서버 다섯 개를 붙이면 이득이 상쇄될 수 있다.
3. **권한과 공급망.** hook 은 임의 셸 명령이고, MCP 서버는 로컬 프로세스 혹은 원격 엔드포인트다. Claude Code 문서는 command hook 이 "사용자의 전체 권한으로 셸 명령을 실행"하며 사용자 계정이 접근할 수 있는 모든 파일을 수정·삭제할 수 있다고 경고한다([Hooks — Security considerations](https://docs.anthropic.com/en/docs/claude-code/hooks)). 스타 수는 안전성 지표가 아니다. API 키를 만지는 도구(프로바이더 전환류)는 특히 배포처를 확인하자.
4. **라이선스 확인.** 20개 중 3개(context-mode·Serena·Anthropic Skills)는 GitHub 이 표준 라이선스로 분류하지 못했다. 개인 실험에는 상관없지만 회사 코드에 섞을 거라면 원문을 읽어야 한다.
5. **스타 수의 한계.** 위 숫자는 관심도일 뿐 품질·유지보수성 지표가 아니다. 20개 모두 조회일 기준 일주일 안에 push 가 있어 "방치된 리포"는 없었다. 다만 이것도 활동량이지 품질은 아니다.

## 정리

| 하고 싶은 것 | 먼저 볼 것 |
|---|---|
| 긴 세션에서 컨텍스트가 빨리 찬다 | RTK *또는* context-mode (하나만) |
| 다음 세션이 지난 일을 모른다 | claude-mem, Beads |
| 큰 코드베이스 탐색이 비싸다 | Serena(심볼), Graphify(그래프) |
| 옛 API 문법으로 짠다 | Context7 |
| 프론트 버그를 눈으로 봐야 한다 | Chrome DevTools MCP |
| 에이전트가 계획 없이 짠다 | Spec Kit, Superpowers |
| 스킬을 직접 만들고 싶다 | Anthropic Agent Skills (형식 원본) |
| 여러 에이전트를 동시에 | git worktree 를 쓰는 오케스트레이터 + "쓰기는 하나만" 원칙 |
| 비용·사용량이 궁금하다 | ccusage, Claude HUD |

> **근거의 한계.** 이 글의 기능 설명은 각 리포의 자기 설명과 README 에 근거한다. 성능 수치(토큰 절감률 등)는 모두 벤더 주장이고 독립 검증되지 않았다. 20개를 같은 조건에서 비교한 중립 벤치마크는 확인하지 못했다. 스타 수·라이선스·활동 날짜는 2026-11-28 조회 시점 값이며 계속 바뀐다.

---

## References

**공식 문서**

1. Anthropic. Claude Code — MCP. <https://docs.anthropic.com/en/docs/claude-code/mcp>
2. Anthropic. Claude Code — Hooks. <https://docs.anthropic.com/en/docs/claude-code/hooks>
3. Anthropic. Agent Skills overview. <https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview>
4. Anthropic. Claude Code — Subagents. <https://docs.anthropic.com/en/docs/claude-code/sub-agents>
5. Anthropic. Claude Code — Plugins. <https://docs.anthropic.com/en/docs/claude-code/plugins>
6. Anthropic. Claude Code — Status line. <https://docs.anthropic.com/en/docs/claude-code/statusline>
7. Model Context Protocol. <https://modelcontextprotocol.io/>
8. Microsoft. Language Server Protocol Specification. <https://microsoft.github.io/language-server-protocol/>
9. Git. git-worktree Documentation. <https://git-scm.com/docs/git-worktree>
10. YAML Ain't Markup Language, Version 1.2.2 — Plain Style. <https://yaml.org/spec/1.2.2/#733-plain-style>
11. GitHub. REST API — Get a repository. <https://docs.github.com/en/rest/repos/repos#get-a-repository>

**소개한 리포 (설명·메타데이터 출처, 2026-11-28 조회)**

12. rtk-ai/rtk · thedotmack/claude-mem · gastownhall/beads · mksglu/context-mode
13. Graphify-Labs/graphify · oraios/serena · upstash/context7 · ChromeDevTools/chrome-devtools-mcp
14. obra/superpowers · github/spec-kit · garrytan/gstack · anthropics/skills
15. Yeachan-Heo/oh-my-claudecode · ruvnet/ruflo · stablyai/orca · wshobson/agents
16. slopus/happy · farion1231/cc-switch · jarrodwatts/claude-hud · ccusage/ccusage

(각 리포 링크는 본문 표에 있다.)
