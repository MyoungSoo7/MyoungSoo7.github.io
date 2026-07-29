---
layout: post
title: "로드맵은 지켜졌는가 — 우로보로스 AgentOS 보드 한 장을 2달 뒤에 검증해봤다"
date: 2026-07-30 01:40:00 +0900
categories: [OpenSource, Engineering]
tags: [Ouroboros, AgentOS, Roadmap, GitHub, TraceGuard, HITL, 오픈소스분석]
---

로드맵 보드는 대개 두 번 읽힌다. 만들 때 한 번, 그리고 아무도 다시 안 본다. 그래서 실험을 하나 해봤다. **2달 전 공개된 로드맵 한 장을 들고 와서, 거기 적힌 것이 실제로 코드가 됐는지 GitHub에서 하나씩 대조해보는 것.**

대상은 [Q00/ouroboros](https://github.com/Q00/ouroboros)다. 2026년 1월 14일에 만들어져 반년 만에 star 5,197개를 모은 에이전트 오케스트레이션 프레임워크다.[^repo]

![우로보로스 AgentOS 로드맵 보드 (2026년 5월)](/assets/images/ouroboros/2026-05-agentos-roadmap-board.jpg)

이 보드는 레포 주인이 2026년 5월 17일 공개한 유튜브 영상 **「[우로보로스] 100개의 커밋 폭격을 막아낸 AI PM '워든' 🛡️ | 에이전트 OS와 새로운 협업 패러다임」** 의 맥락에서 등장한다.[^video]

> **먼저 밝혀둘 것**: 나는 이 영상을 시청하지 않았다. 확인한 것은 제목과 공개일(2026-05-17)뿐이다. 따라서 이 글은 **"영상에서 무슨 말을 했는가"를 다루지 않는다.** 다루는 것은 **"보드에 적힌 항목들이 이후 실제로 어떻게 됐는가"** 이며, 그것만 GitHub 데이터로 검증한다.

---

# 보드에 뭐가 적혀 있나

보드는 다섯 칸으로 나뉘고, 각 칸에 이슈 번호가 붙어 있다. 검증 가능한 형태라 좋다.

| 칸 | 항목 |
|---|---|
| **Tier 1 · now** | #925 Runtime reliability · #939 Plugins · #960 HITL |
| **Tier 2 · next** | #946 Projections · #956 Workflow IR |
| **Evidence spine** | #978 TraceGuard · #1044 |
| **`ooo auto`** | #1046 → #1047 · #1045 |
| **Policy** | No new surfaces · Narrow slices |

"Policy" 칸이 눈에 띈다. 기능이 아니라 **하지 않을 것**을 적어뒀다.

> "No new surfaces — External control planes are references only unless existing gates cannot cover the need."
> "Narrow slices — Attach PRs to canonical issues; avoid duplicate substrate RFCs."

로드맵에 "무엇을 만들까"보다 "무엇을 만들지 않을까"를 명시한 보드는 흔치 않다. 이게 실제로 지켜졌는지는 뒤에서 다시 이야기한다.

---

# 검증 1 — 이슈는 실재하고, 닫혔는가

`gh issue view`로 11개를 전부 조회했다.

| 이슈 | 생성 | 종료 | 상태 |
|---|---|---|---|
| #920 (참조) | 05-12 | 05-14 | closed |
| #925 Runtime reliability | 05-12 | 05-18 | closed |
| #960 HITL | 05-12 | 05-18 | closed |
| #978 TraceGuard | 05-13 | 05-18 | closed |
| #946 Projections | 05-12 | 05-26 | closed |
| #956 Workflow IR | 05-12 | 05-26 | closed |
| #939 Plugins | 05-12 | **06-15** | closed |
| #1044 | 05-16 | 05-16 | merged |
| #1045 | 05-16 | 05-18 | closed |
| #1046 / #1047 | 05-16 | 05-16 | merged |

**11개 전부 실재했고 전부 닫혔다.** 번호·제목·순서가 보드와 정확히 일치한다.

흥미로운 건 종료 시점의 분포다. Tier 1으로 표시된 #925·#960은 **영상 공개 다음 날인 5월 18일**에 닫혔고, Tier 2로 표시된 #946·#956은 8일 뒤인 5월 26일에 닫혔다. 보드의 "now / next" 구분이 실제 종료 순서와 맞아떨어진다.

예외는 #939 Plugins다. Tier 1인데 6월 15일까지 갔다. 한 달 가까이 걸렸다.

---

# 검증 2 — 닫은 게 아니라 만든 게 맞는가

이슈를 닫는 건 쉽다. `Closed as not planned` 한 번이면 된다. 그래서 **지금 코드베이스에 그 개념이 남아 있는지**를 봤다. 기준 시점은 `upstream/main` 최신 커밋이다.

```
TraceGuard      33개 파일
Workflow IR     24개 파일
Projections    162개 파일
Plugins        301개 파일  + 전용 plugin/ 디렉터리
```

HITL은 처음에 `wait_resume` 같은 문자열로 찾다가 0건이 나와서 없는 줄 알았다. 이름을 바꿔 다시 찾으니 **전용 모듈 세 개**가 나왔다.

```
src/ouroboros/core/hitl_contract.py
src/ouroboros/core/hitl_resume.py
src/ouroboros/core/hitl_state.py
```

보드의 #960 설명은 "WAIT/RESUME, ask-user, approvals, persistent suspend states"였다. `hitl_resume.py`와 `hitl_state.py`라는 파일명이 그 문장을 거의 그대로 옮겨놓은 형태다.

**결론: 보드의 항목들은 실제 아키텍처가 됐다.** 이슈만 닫고 넘어간 게 아니다.

각 이슈의 타임라인 이벤트도 18~48건씩 붙어 있다. 논의와 PR 교차참조가 실제로 오갔다는 뜻이다.

---

# 검증 3 — "100개의 커밋 폭격"은 과장인가

영상 제목의 이 표현이 검증 가능해 보여서 재봤다. `git log`로 구간을 끊었다.

| 구간 | 커밋 |
|---|---|
| 2026-05-01 ~ 05-12 (11일) | 398 |
| **05-12 ~ 05-17 (보드 생성 → 영상 공개, 5일)** | **170** |
| 05-17 ~ 05-25 (8일) | 119 |
| 5월 전체 | **777** |

**과장이 아니라 오히려 축소다.** 보드의 이슈들이 생성된 5월 12일부터 영상이 공개된 5월 17일까지 닷새 동안 170커밋이 들어갔다. 5월 12일 하루에만 30커밋이다. 5월 한 달 머지된 PR은 115개.

한 사람이 어디까지 감당했는지도 봤다. 이메일 기준으로 집계하면(같은 사람이 다른 표시 이름으로 커밋한 경우가 있어 이름 기준은 부정확하다):

```
535  shaun0927
113  Q00 (github noreply)
 66  Q00 (gmail)
 19  andrew.adamson
 13  hermes-agent      ← 사람이 아니다
```

5월 777커밋 중 **535개가 한 사람**이다. 26명이 커밋했지만 분포는 극단적으로 기울어 있다.

그리고 `hermes-agent`가 13커밋을 남겼다. **에이전트 프레임워크의 커밋 로그에 에이전트가 저자로 찍혀 있다.** 이 프로젝트가 자기 자신을 어떤 방식으로 쓰고 있는지 보여주는 대목이다.

---

# 검증 4 — 릴리스는 따라왔는가

```
보드 시점 (2026-05-12~13)   v0.38.x
현재      (2026-07-24)      v0.50.6
5월 이후 릴리스 32회 / 누적 108회
```

버전은 확실히 나아갔다. 다만 여기서 **어긋나는 지점**이 하나 나온다.

CHANGELOG.md에서 보드의 용어들을 찾아봤다.

| 용어 | CHANGELOG 등장 |
|---|---|
| plugin | 13회 |
| TraceGuard | 1회 |
| projection | 1회 |
| **Workflow IR** | **0회** |
| **HITL** | **0회** |

코드에는 24개·3개 모듈이 있는데 릴리스 노트에는 한 번도 안 나온다.

이건 모순이 아니라 **성격의 문제**로 보인다. Workflow IR과 HITL은 사용자가 직접 만지는 기능이 아니라 내부 실행 계약이다. 릴리스 노트는 사용자 대상 문서이니 안 쓰는 게 자연스럽다.

다만 이 사실은 한 가지를 함의한다. **"릴리스 노트를 보면 로드맵이 어떻게 진행됐는지 알 수 있다"는 기대는 이 프로젝트에서 성립하지 않는다.** 진행 상황은 이슈와 코드에 있고, 릴리스 노트에는 그 일부만 올라온다.

---

# 검증하지 못한 것

여기까지가 데이터로 말할 수 있는 범위다. **말할 수 없는 것**도 분명히 적어둔다.

**① "이 보드를 토대로 개선했다"는 인과는 증명되지 않는다.**

내가 보인 건 "보드의 항목이 이후 구현됐다"까지다. 보드가 원인인지, 이미 진행 중이던 작업을 보드로 정리한 것인지는 구분할 수 없다. 오히려 후자를 시사하는 정황이 있다 — **11개 이슈 중 8개가 5월 12일 하루에 생성됐다.** 계획을 세우고 이슈를 만든 게 아니라, 이미 있던 방향을 하루에 몰아서 이슈화하고 그걸 보드로 시각화했을 가능성이 크다.

로드맵이 개발을 이끈 것인지, 개발이 로드맵으로 정리된 것인지 — 커밋 이력만으로는 갈라낼 수 없다.

**② "AI PM 워든"은 코드베이스에 없다.**

영상 제목의 핵심 소재인데, 레포 전체를 `grep -ri "warden"` 해도 **0건**이다. `.py` `.md` `.ts` `.yaml` 전부 훑었다.

대신 실재하는 건 `skills/pm/SKILL.md`와 MCP 툴 `ouroboros_pm_interview`다. 설명은 이렇다.

> "PM-focused Socratic interview that produces a Product Requirements Document."

즉 워든은 **코드 식별자가 아니라 영상에서 붙인 이름**으로 보인다. 역할이나 프로세스를 부르는 호칭일 수 있다. 영상을 안 봤으니 단정하지 않는다. 다만 *"워든이라는 컴포넌트를 찾으려고 레포를 뒤지면 안 나온다"* 는 사실은 확인했다.

**③ Policy 항목("No new surfaces", "Narrow slices")은 검증 불가다.**

지켜졌는지 알려면 그 기간의 PR을 하나하나 열어 "새 표면을 추가했는가"를 판정해야 한다. 자동화된 지표로 잡히지 않는다. 이 글에서는 **판단하지 않는다.**

---

# 그래서 무엇이 남았나

로드맵 한 장을 2달 뒤에 대조해본 결과를 한 줄로 줄이면 이렇다.

> **적힌 것은 다 만들어졌다. 다만 "적었기 때문에 만들어졌다"는 증거는 없다.**

그리고 이 검증 과정 자체에서 배운 게 두 개 있다.

**첫째, 로드맵의 검증 가능성은 이슈 번호를 적었느냐로 갈린다.** 이 보드가 검증 가능했던 유일한 이유는 칸마다 `#925` 같은 번호가 박혀 있었기 때문이다. "런타임 안정성 개선"이라고만 적혀 있었다면 2달 뒤에 아무것도 대조할 수 없었을 것이다. 로드맵에 번호를 적는 건 미래의 자신에게 감사 추적(audit trail)을 남기는 일이다.

**둘째, 문자열 검색의 실패는 부재의 증거가 아니다.** HITL을 `wait_resume`으로 찾았을 때 0건이 나왔고, 나는 하마터면 "HITL은 구현 안 됐다"고 쓸 뻔했다. 실제로는 `hitl_state.py`라는 전용 모듈이 있었다. **찾지 못한 것과 없는 것은 다르다.** 이건 이 글을 쓰면서 실제로 한 번 틀렸다가 잡은 실수다.

마지막으로, 이 글은 우로보로스가 좋은 프로젝트인지 나쁜 프로젝트인지 말하지 않는다. 그건 이 데이터로 판단할 문제가 아니다. 확인한 것은 **보드에 적힌 11개 항목의 2달 뒤 상태** 하나뿐이다.

---

## References

- Q00. *ouroboros* (GitHub 저장소). 2026-01-14 생성, 검증 시점 star 5,197 · fork 522. 본문의 이슈 상태·커밋 수·파일 수·릴리스 목록은 모두 이 저장소의 `upstream/main`과 GitHub API(`gh`)에서 직접 조회한 값이다. [github.com/Q00/ouroboros](https://github.com/Q00/ouroboros)
- 인용한 이슈 원문 — [#925](https://github.com/Q00/ouroboros/issues/925) *Agent OS roadmap: harden MCP/runtime reliability for long-running agent flows* · [#960](https://github.com/Q00/ouroboros/issues/960) *Agent OS HITL: standardize WAIT/RESUME ask-user and approval contract* · [#978](https://github.com/Q00/ouroboros/issues/978) *Design spine: AgentOS evidence-gated delivery via TraceGuard* · [#939](https://github.com/Q00/ouroboros/issues/939) · [#946](https://github.com/Q00/ouroboros/issues/946) · [#956](https://github.com/Q00/ouroboros/issues/956)
- 「[우로보로스] 100개의 커밋 폭격을 막아낸 AI PM '워든' 🛡️ | 에이전트 OS와 새로운 협업 패러다임」, YouTube, 2026-05-17 공개. [youtube.com/watch?v=9LH8K03zKZU](https://www.youtube.com/watch?v=9LH8K03zKZU&t=1404s)
- 로드맵 보드 이미지 — 위 영상 맥락에서 공개된 것을 독자가 제보. 이미지에 적힌 이슈 번호를 그대로 조회해 검증했다.

*출처 등급과 한계: 이슈 상태·커밋 수·파일 수·릴리스 이력은 GitHub의 1차 데이터를 직접 조회한 값이므로 재현 가능하다(`gh issue view`, `git log --since/--until`, `git grep`). **유튜브 영상은 시청하지 않았고 제목과 공개일만 확인했다** — 따라서 영상의 주장 내용에 대한 평가는 이 글에 없다. 「이 보드를 토대로 개선했다」는 인과, Policy 항목의 준수 여부, 「워든」의 정확한 의미는 모두 검증 불가로 분류해 판단을 보류했다. 커밋 수는 `upstream/main` 기준이며 머지 커밋 포함 여부에 따라 달라질 수 있다. 기여자 집계는 표시 이름이 아니라 이메일 기준이다(동일인이 다른 이름으로 커밋한 사례가 있었다).*

[^repo]: GitHub API 조회값, 검증 시점 2026-07-30.
[^video]: 제목·공개일은 페이지 메타데이터에서 확인. 영상 내용은 확인하지 않았다.
