---
layout: post
title: "Claude Projects 문서 읽기 — 조율자·스레드 구조와, 레포를 하나 더 붙이면 훅이 조용히 꺼지는 벼랑"
date: 2026-09-18 17:53:25 +0900
categories: [AI, Agent, Claude Code]
tags: [Claude Code, Projects, Cloud Session, Agent, Orchestration, Hooks]
---

대상 문서는 이것 하나다. **[Let Claude coordinate ongoing work with Projects](https://code.claude.com/docs/en/claude-projects)** (Claude Code 공식 문서).[^doc] 아래 인용문은 전부 이 페이지 본문에서 받아 대조한 것이다.

먼저 밝힐 것이 있다. **나는 이 기능을 실제로 써보지 못했다.** 문서 자신이 Pro·Max 대상 공개 베타이고 순차 배포 중이라고 적어놨고, 내 계정에는 아직 오지 않았다. 그래서 이 글은 사용기가 아니라 **문서 독해**다. "실제로는 이렇더라"는 문장은 한 줄도 쓰지 않았다.

그런데 문서만 읽어도 값을 하는 대목이 하나 있었다. 4장이 그것이다. **레포지토리를 하나에서 둘로 늘리는 순간 훅과 권한 규칙이 조용히 적용을 멈춘다.** 에러도, 경고도 없다. 이건 표 한 칸에 "Don't apply" 세 글자로만 적혀 있다.

---

## 1. 이 기능이 파는 것은 병렬이 아니라 조율이다

가장 먼저 짚어야 할 문장. 문서가 직접 선을 긋는다.[^doc]

> Several Claude Code features let more than one session work at the same time, so **running work in parallel is not by itself what a project is for.**

Claude Code에는 이미 동시에 여러 세션을 돌리는 수단이 여럿 있다 — 클라우드 세션, agent view, worktree, agent teams. Projects가 새로 파는 건 병렬성이 아니라 **누가 그걸 관리하느냐**다. 문서의 대비가 명확하다.

> Without a project, running several sessions means **doing the coordinating yourself**: you decide what each one works on, repeat the same background at the start of each, and check back to see which finished or needs an answer.

이 문장은 내 얘기다. 나는 지금 이 블로그 저장소 하나에 Claude 세션 여러 개를 붙여 쓰고 있고, 그 조율을 전부 손으로 한다. 규칙을 세션마다 다시 설명하고, 어느 세션이 뭘 하는지 직접 기억하고, 같은 파일을 건드릴까 봐 매번 git 상태를 확인한다. [어제 쓴 글](/2026/09/17/os-study-and-using-ai-well/)에서 이걸 동시성 문제라고 불렀는데, Projects는 그 문제에 **스케줄러를 하나 붙이겠다**는 제안이다.

그래서 이 글의 관심사는 "편한가"가 아니다. **그 스케줄러가 무엇을 보장하고 무엇을 보장하지 않는가**다.

---

## 2. 구조 — 대화 하나 + 스레드 N개

프로젝트의 부품은 셋이다.[^doc]

- **프로젝트 대화(the project conversation)**: 조율자 역할을 하는 장기 세션 하나. 무엇을 스레드로 만들지 결정하고, 자기가 시작한 스레드를 전부 추적한다.
- **스레드(threads)**: 실제 일꾼. 각각이 **독립된 클라우드 세션**이고, 자기 컨텍스트 윈도우와 자기 브랜치를 갖고, 필요하면 PR을 연다.
- **Overview 패인**: 스레드 상태판.

여기서 조율자의 시야에 관한 한 문장이 중요하다.[^doc]

> **It sees what threads report back, not every step they take.**

조율자는 스레드의 모든 단계를 보지 않는다. **보고된 것만 본다.** 어제 글에서 서브에이전트를 `fork()` + 파이프에 빗댔는데, 여기서도 정확히 같은 구조다 — 부모는 자식의 스택을 읽지 않는다. 이건 설계상 당연하고(조율자 컨텍스트가 터지지 않으려면 그래야 한다), 동시에 **조율자의 요약을 작업 증거로 쓰면 안 된다**는 뜻이기도 하다. 확인은 스레드를 열거나 PR을 봐야 한다.

Overview의 스레드 상태는 여섯 가지다: `Ready for review` · `Waiting on you` · `Working` · `Landing` · `Idle` · `Resolved`. 마지막 하나에 자동 규칙이 붙어 있다 — 아무 활동이 없으면 **일주일 뒤 자동으로 Resolved 처리**된다.[^doc]

PR 동작에도 기본값이 하나 박혀 있다. 스레드가 PR을 열면 **auto-fix를 켠 채로 그 PR을 감시한다.**[^doc]

> watches the pull request with auto-fix turned on, **whether or not auto-fix is on for your other cloud sessions**

내 다른 클라우드 세션 설정과 **무관하게** 켜진다. CI가 깨지면 스레드가 깨어나 고치고, 리뷰 코멘트가 달리면 대응한다. 편한 동작이지만 6장에서 보듯 이건 비용 항목이기도 하다.

---

## 3. 스레드가 시작할 때 들고 가는 것

새 스레드는 매번 백지에서 시작하지 않는다. 문서가 시작 시 상속 목록을 명시한다.[^doc]

| 무엇 | 출처 |
| --- | --- |
| 레포지토리와 업로드 파일 | 프로젝트에 등록한 것 (파일은 `/mnt/project-files`) |
| 프로젝트 지침(project instructions) | `Project settings > Memory`, **최대 16,000자** |
| 프로젝트 메모리 | `MEMORY.md` 인덱스를 시작 시 읽고 나머지는 필요할 때 연다 |
| 각 레포의 `CLAUDE.md` · 스킬 · 플러그인 | 프로젝트의 **모든** 레포에서 |
| 커넥터(MCP) | claude.ai **계정**의 커넥터 |
| 클라우드 환경 | 네트워크 접근·환경변수·API 자격증명·설치 도구 |

그리고 반대편 문장이 한 줄로 못 박혀 있다.[^doc]

> **Threads don't pick up anything from the Claude Code setup on your own machine.**

내 맥에 깔린 스킬·MCP·플러그인은 하나도 따라가지 않는다. 스킬을 스레드에 주려면 **레포에 커밋**해야 하고(`.claude/skills/<name>/SKILL.md`), MCP는 **계정 커넥터**로 붙여야 한다. 로컬 설정이 그대로 간다고 가정하면 스레드는 도구가 없는 채로 일을 시작한다.

모델 기본값도 적혀 있다. **새 프로젝트는 전부 Opus**로 시작하고, 스레드는 high effort, 조율자 대화는 low effort다.[^doc] 컨텍스트 관리는 사용자가 하지 않는다 — 스레드는 자동 컴팩션하고, 조율자 대화는 전체 히스토리가 아니라 최근 메시지·최근 스레드·프로젝트 메모리로 굴러간다. 그래서 문서의 처방이 이것이다.

> **Put anything that must never be dropped in project memory.**

어제 글의 "축출은 손실이다, 중요한 건 컨텍스트 밖에 못 박아라"와 같은 처방을, 공식 문서가 같은 말로 하고 있다.

---

## 4. 가장 중요한 표 — 레포 1개와 2개 사이의 벼랑

여기가 이 문서에서 제일 값진 대목이고, 동시에 제일 눈에 안 띄는 대목이다. `What threads pick up from your repositories` 절의 표를 옮기면 이렇다.[^doc]

| 레포의 `.claude/` 안에 있는 것 | 레포 **1개** 프로젝트 | 레포 **여러 개** 프로젝트 |
| --- | --- | --- |
| `CLAUDE.md` | 로드 | **모든** 레포에서 로드 |
| 스킬·에이전트·커맨드 | 로드 | **모든** 레포에서 로드 |
| `settings.json`의 플러그인 | 로드 | 모든 레포에서 로드 (충돌 시 `Project settings > Plugins` 우선) |
| **권한 규칙 · 훅 · `env`** | 적용됨 | **적용 안 됨 (Don't apply)** |
| `.mcp.json`의 MCP 서버 | 로드 | 로드 안 됨 (계정 커넥터만) |

`CLAUDE.md`와 스킬은 레포가 늘어나면 **더 많이** 로드된다. 그런데 권한 규칙과 훅은 **반대로 사라진다.** 같은 표 안에서 방향이 갈린다.

왜 그런지도 문서가 설명한다.[^doc]

> Permission rules, hooks, and `env` defined in `.claude/settings.json` come only from the `.claude/settings.json` **in the directory the thread starts in**: inside the repository when the project has one, and **above the clones when it has several, where no repository's file is read for them.**

기계적으로는 단순하다. **시작 디렉터리가 어디냐**의 문제다.

- 레포 1개 → 스레드가 그 레포 **안에서** 시작 → 그 레포의 `.claude/settings.json`이 곧 시작 디렉터리의 설정 파일 → 훅·권한 규칙 적용.
- 레포 여러 개 → 스레드가 클론들 **위에서** 시작 → 시작 디렉터리에는 아무 `.claude/settings.json`도 없다 → 훅·권한 규칙 없음. 각 클론은 `additional directory`로 붙고, 그 경로에는 `CLAUDE.md` 로딩만 켜져 있다.

`CLAUDE.md`와 스킬이 살아남는 이유가 바로 이것이다. 그건 additional directory에서도 읽히지만, 권한 규칙과 훅은 **시작 디렉터리 한 곳에서만** 읽힌다.

### 왜 이게 위험한가

이 전환에는 **명시적인 행동이 없다.** "레포를 추가하시겠습니까, 훅이 꺼집니다" 같은 확인 절차가 문서에 없고, 실패 신호도 없다. 훅은 원래 조용히 도는 물건이라, **안 도는 것도 조용하다.** 커밋 전 린트 훅, 위험 명령 차단 훅, 자동 포맷 훅 — 이런 걸 안전장치로 믿고 있었다면, 레포 하나를 추가한 다음부터 그 안전장치 없이 스레드가 도는 것이다.

내 경우로 옮겨보면 바로 와닿는다. 나는 로컬에서 위험한 bash 패턴을 막는 훅을 쓰고 있고(이 글을 쓰다가 실제로 한 번 차단당했다), 그게 `.claude/settings.json` 계열 설정에 걸려 있다. 그런 통제를 그대로 들고 클라우드로 갈 수 있다고 가정하면, 레포 2개짜리 프로젝트에서는 **가정이 틀린 채로** 굴러간다.

### 문서가 주는 우회로

다행히 같은 절에 탈출구가 셋 적혀 있다.[^doc]

1. **훅은 플러그인으로 포장한다.** — *"hooks that an enabled plugin provides still run, since plugins load from every repository."* 플러그인은 모든 레포에서 로드되므로, 플러그인이 제공하는 훅은 레포가 여럿이어도 산다. 훅을 레포 설정에 직접 박지 말고 플러그인으로 감싸라는 뜻이다.
2. **표준 규칙은 project instructions로 올린다.** 레포 하나에 관한 규칙(빌드 명령 등)은 그 레포의 `CLAUDE.md`에, 프로젝트 전체 규칙은 지침에.
3. **환경변수는 cloud environment로 준다.** 레포 `settings.json`의 `env`에 기대지 않는다.

한 가지 덧붙이면, 레포 1개짜리에서도 `env`에는 예외가 붙는다 — *"except the `env` keys that no cloud session honors"*. 즉 로컬에서 먹히던 `env` 키 일부는 클라우드 세션 자체가 무시한다.[^doc]

---

## 5. MEMORY.md가 두 개다 — 이름이 겹치는 함정

프로젝트에서 맥락을 나르는 통로는 세 층인데, 그중 둘이 **같은 파일 이름**을 쓴다.

| 층 | 사는 곳 | 성격 |
| --- | --- | --- |
| 프로젝트 메모리 | `Project settings > Memory` (클라우드) | Claude가 스스로 쓰는 노트. 인덱스가 `MEMORY.md` |
| 레포 `CLAUDE.md` | 각 레포 클론 | 그 레포에 관한 규칙 |
| 로컬 auto memory | 내 기계 | Claude Code가 로컬에 쓰는 노트. 인덱스가 **역시** `MEMORY.md` |

문서가 이 혼동을 먼저 차단해 둔다.[^doc]

> They're separate from the auto memory Claude Code keeps on your machine, **even though both use a `MEMORY.md` index.** Project memory is also separate from the `CLAUDE.md` files in the project's repositories.

경계는 간단하다. **레포에 관한 것은 그 레포 `CLAUDE.md`, 프로젝트에 관한 것은 프로젝트 메모리.** 그리고 스레드를 교정했으면 그 교정을 기억하라고 조율자에게 따로 말해야 한다 — 그래야 프로젝트 메모리에 들어가 다음 스레드가 그걸 갖고 시작한다.

---

## 6. 비용 — 숫자가 세 개 있다

이 절은 추측이 아니라 문서에 숫자로 적혀 있는 것만 옮긴다.

**① 하드 캡은 하루 200 스레드다.**[^doc]

> There's no fixed number; Claude starts as many as the work calls for, and a limit you ask for is a preference rather than a cap. **The enforced limit is 200 new threads per day across your projects.**

동시에 몇 개 돌릴지는 말로 정할 수 있지만 그건 **선호지 상한이 아니다.** 같은 성격의 문장이 다른 절에도 있다 — *"They're instructions Claude keeps to, not enforced settings, so a thread limit you give this way isn't a hard cap."* 강제되는 유일한 숫자가 하루 200개다.

**② 유휴 스레드를 되살리면 대화 전체를 다시 읽는다.**[^doc] 캐시 수명은 Pro·Max에서 한 시간이고, 그보다 오래 쉰 스레드에 후속 작업을 보내면 그 스레드의 전체 대화를 다시 읽고 시작한다. 그래서 문서의 권고가 **새 작업은 큰 옛 스레드를 되살리기보다 새 스레드**다.

**③ 놀고 있어도 깨어나는 경로가 있다.** PR을 감시 중인 유휴 스레드는 CI가 깨지거나 리뷰 코멘트가 달리면 깨어나 다시 플랜을 쓴다. 멈추려면 그 스레드에 감시를 그만하라고 말해야 한다.

반대로 **완전히 조용한 프로젝트는 비용이 0이다** — 도는 스레드도, 감시 중인 PR도, 새 메시지도 없으면 유휴 상태에서 플랜을 쓰지 않고 보관된 프로젝트도 마찬가지다.[^doc]

그리고 한도에 닿았을 때의 동작이 하나 특이하다. 한도에 걸린 스레드는 **기다렸다가 리셋되면 알아서 이어서 돈다.** 문서 표현대로 *"work you left running starts using your next usage window without a message from you"* — 내가 아무것도 안 해도 다음 사용 창을 먹기 시작한다는 뜻이다. 다만 한도를 **넘겨서** 쓰는 건 usage credits를 켜둔 경우뿐이고, 스레드가 그걸 대신 켜줄 수는 없다.[^doc]

---

## 7. 함정 목록 — 문서에 적혀 있는 것만

읽으면서 "이건 모르면 당하겠다" 싶었던 것들. 전부 문서 문장이다.

- **`claude project` CLI 명령은 이 기능과 무관하다.** 이름만 같다. 그쪽은 디렉터리의 로컬 Claude Code 상태를 관리하는 명령이고, 문서가 *"is unrelated"* 라고 명시한다.[^doc] 검색하다 섞이기 딱 좋다.
- **샌드박스 재개에 실패하면 미커밋 변경이 날아간다.** 스레드 샌드박스는 턴 사이에 멈췄다 재개되는데, 재개가 안 되면 **새 클론에서 이어간다.** 그래서 문서의 권고가 *"On long tasks, ask Claude to commit and push work in progress."*[^doc] 긴 작업일수록 중간 커밋이 보험이다.
- **`Move to project`는 단방향이다.** 독립 클라우드 세션을 프로젝트로 들여올 수는 있지만, 스레드를 프로젝트 밖으로 빼거나 다른 프로젝트로 옮길 수는 없다.[^doc]
- **프로젝트 대화 자체에는 커넥터가 없다.** *"The project conversation itself has no connectors"* — 커넥터가 필요한 일은 조율자에게 물어보는 게 아니라 스레드 작업으로 보내야 한다.[^doc]
- **스레드에서 커넥터를 끄면 계정 기본값으로 저장된다.** *"saves that as your account default"* — 그 스레드만 끄는 게 아니라 이후 새 스레드와 claude.ai 대화까지 그 커넥터 없이 시작한다.[^doc] 일회성 조치인 줄 알고 끄면 범위가 넓다.
- **로컬 세션은 프로젝트에 못 들어간다.** 내 VPN 뒤 API, 로컬 DB, 디바이스 에뮬레이터가 필요한 일은 애초에 대상이 아니다.
- **1인 소유다.** *"A project belongs to one user"* — 공유 불가, 스레드 트랜스크립트 공유 옵션 없음, 베타 동안 조직 단위 통제 없음, Team·Enterprise 미지원.[^doc]
- **CLI·Bedrock·Vertex·Foundry에서는 안 된다.** claude.ai/code, 데스크톱 앱, 모바일 앱 전용이다.

---

## 8. 그래서 언제 쓰고 언제 쓰지 않는가

문서가 "다른 게 더 맞는 경우"를 직접 열거해 둔 게 오히려 신뢰가 간다.[^doc] 요약하면 이렇다.

**맞는 경우** — 한 세션보다 오래 가는 목표가 있고 거기서 작업이 계속 나오는 일. 문서 예시는 "모든 서비스를 새 lint 설정으로 올린다"처럼 **레포마다 스레드 하나씩** 도는 형태다.

**안 맞는 경우** — ① 한 세션에 끝나는 단일 작업(그냥 클라우드 세션 하나) ② 내 기계만 닿는 도구·서비스가 필요한 일(로컬 세션) ③ 대화 없이 주기적으로만 도는 일(routine) ④ 여러 사람이 함께 지시하는 일(Claude Tag).

내 판단을 하나 덧붙이면, **①과 ④가 실제로 갈림길**이다. 나처럼 여러 세션을 이미 굴리고 있어도, 그게 "하나의 목표에서 계속 파생되는 작업"이 아니라 **서로 무관한 요청이 채팅으로 흘러드는 형태**라면 조율자가 얹어줄 게 많지 않다. Projects의 값은 병렬성이 아니라 *같은 배경을 한 번만 설명하면 되는 것*에 있는데, 배경이 매번 다르면 그 값이 안 생긴다.

---

## 9. 마무리

문서 한 장을 정리하면 이렇다.

1. Projects가 파는 건 병렬성이 아니라 **조율**이다. 조율자 대화 하나가 스레드 N개를 만들고 추적한다.
2. 조율자는 **보고받은 것만 본다.** 요약을 증거로 쓰지 마라.
3. 스레드는 내 기계에서 **아무것도** 물려받지 않는다. 스킬은 레포에 커밋하고 MCP는 계정 커넥터로 붙인다.
4. **레포를 하나에서 둘로 늘리면 훅·권한 규칙·`env`가 조용히 꺼진다.** 훅은 플러그인으로 포장해야 살아남는다.
5. 강제되는 숫자는 **하루 200 스레드** 하나뿐이다. 내가 말한 동시 실행 수는 선호일 뿐이다.
6. 긴 작업은 중간 커밋을 시켜라. 샌드박스 재개가 실패하면 새 클론에서 이어간다.

4번 하나만 건져도 이 문서를 읽은 값은 한다고 본다. 표 한 칸에 "Don't apply"라고만 적힌 항목이, 실제로는 **내가 안전장치라고 믿고 있던 것이 통째로 빠지는 조건**이기 때문이다.

---

## References

[^doc]: Anthropic, *Let Claude coordinate ongoing work with Projects*, Claude Code Docs. 이 글의 모든 인용문과 수치(16,000자 지침 상한, 하루 200 스레드, Pro·Max 캐시 수명 1시간, Opus 기본값, 일주일 후 자동 Resolved, 레포 1개/여러 개 상속 표, 샌드박스 재개 실패 시 fresh clone, `claude project` CLI 무관 명시)는 이 페이지 본문에서 확인했다. <https://code.claude.com/docs/en/claude-projects>

> **한계 명시.** ① **나는 이 기능을 실행해보지 못했다.** 문서 기준 Pro·Max 공개 베타에 순차 배포 중이고 내 계정에 아직 오지 않았다. 따라서 이 글에는 동작 실측이 없고, 모든 서술은 공식 문서 독해다. 문서와 실제 동작이 다를 가능성은 배제하지 못한다. ② 공개 베타 기능이라 **여기 적힌 숫자와 규칙은 바뀔 수 있다.** 위 수치는 2026-09-18 시점에 받아본 문서 기준이다. ③ 4장의 위험 평가("안전장치가 빠진다")는 문서가 명시한 동작에서 내가 끌어낸 **판단**이지 문서의 경고문이 아니다. 문서는 해당 칸에 적용 여부만 적어두었다.
