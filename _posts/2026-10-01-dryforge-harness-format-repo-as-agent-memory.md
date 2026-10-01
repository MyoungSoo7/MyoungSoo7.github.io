---
layout: post
title: "에이전트 기억이 아니라 저장소에 적어라 — dryforge 의 harness-format.md 를 한 줄씩 읽기"
date: 2026-10-01 16:30:54 +0900
categories: [ai, harness]
tags: [dryforge, harness, claude-code, codex, agents-md, claude-md, adr, auto-memory, documentation]
---

[prekuter/dryforge](https://github.com/prekuter/dryforge) 는 Claude Code·Codex·Grok Build·GitHub Copilot CLI·Antigravity CLI 에 붙는 플러그인이다. 명령은 `ready`(의도 정리) → `go`(구현·검증), 기존 코드베이스용 `migration` 세 개뿐이다. 이 글은 그중 **[`harness-format.md`](https://github.com/prekuter/dryforge/blob/main/claude/skills/go/references/harness-format.md)** 한 파일을 읽는다. dryforge 가 프로젝트에 남기는 문서 묶음(이하 "하네스")이 어떤 파일로 구성되고, 각 파일에 무엇을 써야 하고 무엇을 쓰면 안 되는지를 정한 **런타임 규격서**다. 파일 첫머리가 스스로를 그렇게 부른다 — "runtime authority … It carries the rules, not the design rationale."

결론부터 말하면, 이 파일에서 가장 센 문장은 구조 그림이 아니라 이것이다.

> "The harness is the sole durable store for project knowledge."

## 리포 사실관계 (2026-10-01 GitHub API 실측)

| 항목 | 값 |
| --- | --- |
| 생성 | 2026-05-31 |
| 최신 릴리스 | v1.3.7 (CHANGELOG 기준 2026-09-27, 중·일 README 추가) |
| 라이선스 | Apache-2.0 (v1.3.5 에서 재라이선스) |
| 별 / 포크 | 384 / 34 |
| 이 파일 크기 | 29,474 바이트, 420줄 |

같은 `harness-format.md` 가 `claude/`·`agent-plugin/`·`antigravity/` 패키지와 `migration` 스킬 안에 **바이트 단위로 똑같이** 들어 있다(본인이 `cmp` 로 확인). 우연히 같은 게 아니다. 빌드 스크립트 `build/build.sh` 의 첫 가드가 `go` 와 `migration` 의 공유 참조 파일 세 쌍이 `diff` 로 다르면 빌드를 멈춘다("shared reference drift"). 스킬 소스 하나를 여러 에이전트용으로 패키징하는 구조이고, 규격서가 갈라지는 것을 빌드가 막는다.

## 무엇을 만드는가 — 파일마다 "고정된 자리"

```
project-root/
├── CLAUDE.md / AGENTS.md      ← 진입점 (두 파일 내용 동일)
├── docs/
│   ├── architecture.md        ← 시스템 구성
│   ├── business-rules.md      ← 도메인 규칙
│   ├── security.md            ← 보안 정책
│   ├── standards.md           ← 어기면 깨지는 규칙
│   ├── engineering-notes.md   ← 함정·비자명한 동작
│   ├── operations.md          ← 설치·빌드·배포
│   ├── contracts.md           ← 외부 인터페이스 계약
│   └── tracking/ (status.md · decisions/ · findings.md)
└── <module>/AGENTS.md         ← 모듈별 범위·경계·불변식
```

구조 자체는 새롭지 않다. 진입점 파일은 Anthropic 의 CLAUDE.md 와 업계 공통 포맷 [AGENTS.md](https://agents.md/) 를 그대로 쓰고, `decisions/` 는 Michael Nygard 가 2011년에 제안한 [ADR](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) 이다. 이 파일이 다른 점은 **각 칸에 무엇을 쓰면 안 되는지**를 집요하게 적었다는 것이다.

## 1. 에이전트 기억에 두지 마라

규격서는 프로젝트에 관해 알게 된 것 — 함정, 비자명한 동작, 결정과 그 이유, 실행 절차 — 은 하네스에 쓰고 "**never into the agent's own host memory or any external / per-agent memory store**" 라고 못 박는다. 이유는 이렇게 든다. 호스트 기억은 한 플랫폼의 한 에이전트에게만 보이고, 다음 에이전트나 다른 진입점에서는 안 보인다.

이 이유는 사실이다. Claude Code 공식 문서는 자동 기억(auto memory)을 이렇게 설명한다 — "**Auto memory is machine-local.** … Files are not shared across machines or cloud environments." ([Claude Code Docs: How Claude remembers your project](https://code.claude.com/docs/en/memory)). 같은 문서의 표에서 CLAUDE.md 는 "Team members via source control" 로 공유되고, 자동 기억은 한 기계의 한 저장소 범위다.

나는 이 문제를 직접 겪고 있다. 텔레그램 봇 여럿이 같은 클러스터와 같은 블로그를 만지는데, 이 맥 봇의 자동 기억에는 운영 함정 기록이 100건 넘게 쌓여 있다. 그런데 클러스터 노드 위의 봇들은 그걸 한 줄도 못 읽는다. 그래서 같은 함정을 기계마다 따로 배운다. dryforge 의 처방은 단순하다. 그 프로젝트에 관한 지식이면 그 프로젝트 저장소에 커밋하라는 것이다.

다만 이 처방에는 빈칸이 있다. **저장소 하나에 속하지 않는 지식**, 예컨대 "이 맥에서는 kubectl 을 터널 경유로 붙어야 한다" 같은 운영 환경 지식은 하네스 모델 안에 놓을 자리가 없다. dryforge 의 단위는 프로젝트이고, 여러 리포를 가로지르는 인프라 기억은 범위 밖이다. 이건 결함이라기보다 설계상의 경계다.

## 2. 이 문장이 자리를 차지할 자격이 있는가 — 5원칙

내용 품질 기준이 이 파일의 중심이다. 모든 문장은 다섯 가지 질문을 통과해야 한다.

1. **비도출성** — 코드를 읽으면 알 수 있는 건 쓰지 않는다.
2. **작업을 바꾸는가** — 이 문장을 읽은 에이전트와 안 읽은 에이전트의 결과가 같으면 장식이다.
3. **밀도** — 문장마다 핵심 사실이 하나 있어야 한다.
4. **프로젝트 고유성** — 어느 프로젝트에나 참인 말은 쓰지 않는다.
5. **부재의 결과** — "이 문장이 없으면 무엇이 깨지는가?" 답이 없으면 지운다.

그리고 살아남은 문장을 쓰는 기법 네 가지가 있다. 검증 가능하게 쓰기, "must" 마다 "must not" 짝 짓기, 결과 말고 메커니즘(입력 → 처리 → 출력) 쓰기, 엣지 케이스를 구체적으로 처분하기("적절히 처리" 금지)다.

규격서는 이걸 지키지 않은 문서를 "hollow shell" 이라고 부르고 "**worse than none**" 이라고 한다. 문서가 있으니 다음 에이전트가 안다고 착각하고, 사실은 모르는 채로 일한다는 이유다. Anthropic 문서의 조언도 같은 방향이다. CLAUDE.md 는 파일당 200줄 아래를 목표로 하고, 길수록 컨텍스트를 먹고 지시 준수율이 떨어진다고 적는다([같은 문서](https://code.claude.com/docs/en/memory)). dryforge 는 이 제약을 이렇게 푼다. 진입점에는 핵심 금지사항(hard gate) 3~5개와 내비게이션 트리만 두고, 나머지는 `docs/` 로 보낸다.

## 3. 문서가 자기 얘기를 하지 않는다 — 도구 이름까지 지운다

가장 독특한 규칙이다. 생성된 문서에는 다음을 쓰면 안 된다.

- 문서가 자기 자신을 설명하는 말 — "이 문서는 코드 대신 읽으라고 있다" 같은 것
- 자기가 어디서 왔는지 — "migration 으로 생성됨", 또는 status.md 에 "docs 를 만들었다"를 완료 항목으로 적는 것
- **도구 이름과 도구의 내부 용어** — "dryforge" 는 물론이고 문서 묶음을 "harness"라고 부르는 것도 금지

README 는 그 결과를 이렇게 정리한다. "플러그인을 지워도 문서는 남습니다." 도구가 자기 흔적을 지우는 설계다. 문서가 특정 도구의 산출물로 읽히지 않고 그냥 프로젝트 문서로 남으니, 다른 에이전트나 사람이 그대로 이어 쓸 수 있다.

## 4. "아직 안 만든 것"은 금지 규칙이 아니다

규격서가 반복해서 경계하는 실수가 있다. **이번 사이클의 범위 동결을 영구 규칙으로 굳히는 것**이다.

- "기능 X 는 아직 만들지 마라" 는 hard gate 가 아니다. status.md 의 "남은 일"이다.
- business-rules 에 "통화 혼합은 구조상 불가능" 이라고 쓰면 안 된다. 다음 사이클에 만들 기능이면 "현재는 그룹당 통화 하나"로 쓴다.
- "앞으로를 위해 모양 Y 를 유지하라" 도 hard gate 가 아니다. 특히 남은 일 중 하나가 Y 를 바꿀 예정이라면 더욱 그렇다.

status.md 에도 같은 엄격함이 적용된다. "**built 와 verified 를 구분하라**." 테스트가 없는 코드를 "통과"로 적지 말고 "built, untested" 로 적으라는 것이다. 에이전트가 자기 요약을 완료 증거로 삼는 실패를 문서 단에서 막는 장치다. 같은 맥락에서 하네스 검증(`harness-review.md`)은 반드시 독립 리뷰어 서브에이전트가 한다 — "self-judgment is the weak move".

## 5. 참조하지 말고 다시 써라 — ADR 원전과의 차이

자기완결 규칙도 강하다. `docs/` 파일끼리 "architecture.md 참조" 같은 교차 참조를 쓰지 않는다. `INV-1` 같은 제약 ID 라벨 체계도 두지 않는다. 대신 각 문서가 필요한 부분을 **자기 고도(altitude)에서 다시 쓴다**. 같은 주제라도 시스템 전체를 보는 독자를 위해서는 architecture.md 에, 기능 규칙을 보는 독자를 위해서는 business-rules.md 에, 모듈 코드를 고치는 사람을 위해서는 그 모듈의 AGENTS.md 에 쓴다.

ADR 에서도 Nygard 원안과 갈린다. Nygard 형식은 Title·Context·Decision·**Status**·Consequences 이고, 뒤집힌 결정은 지우지 않고 "superseded" 로 표시해 **대체 기록을 참조**한다. dryforge 의 ADR 은 Context·Decision·**Alternatives**·Consequences 다. 버린 대안과 버린 이유를 구체적으로 적으라고 요구하고("considered but rejected" 금지), Consequences 에는 "이 결정으로 **불가능해진 것**"을 넣으라고 한다. 기록할 결정의 기준도 명시한다. "같은 상황의 다른 팀이 다르게 고를 수 있었는가?"

다시 쓰기에는 대가가 있다. 같은 사실이 여러 파일에 있으면, 바뀔 때 고칠 곳도 여러 군데다. 규격서는 "delta 는 양방향" — 이번 변경이 다른 곳의 기존 문장을 낡게 만들지 않았는지 확인하라 — 으로 이를 막으려 한다. 하지만 이건 에이전트의 성실성에 기대는 규칙이지, 빌드 가드처럼 기계로 강제되는 규칙은 아니다.

## 짚어 둘 점 — Claude Code 는 모듈 AGENTS.md 를 자동으로 읽을까

dryforge 는 루트에 CLAUDE.md 와 AGENTS.md 를 똑같이 두고, 모듈마다 AGENTS.md 만 둔다. 그런데 Claude Code 공식 문서에 따르면, 기본 설정(`claude-md-or-agents-md`)에서는 **작업 디렉터리나 그 위에 CLAUDE.md 가 있으면 AGENTS.md 대신 CLAUDE.md 만 읽는다**. 하위 디렉터리의 AGENTS.md 도 "none count" 일 때만 로드 대상이다([Claude Code Docs: AGENTS.md](https://code.claude.com/docs/en/memory#agents-md)).

문서대로라면 dryforge 가 만든 프로젝트에서 Claude Code 는 다음처럼 동작한다.

- 루트 AGENTS.md 는 안 읽는다. 내용이 CLAUDE.md 와 같으니 손해는 없다.
- **모듈 AGENTS.md 는 자동으로 로드되지 않을 수 있다.** dryforge 는 진입점의 "작업 전 체크리스트"에 "해당 모듈의 AGENTS.md 를 읽어라"를 넣어 둔다. 그러니 실제로는 에이전트가 지시를 따라 명시적으로 읽는 경로에 기대는 셈이다.
- 확실히 하려면 `/config` 의 Project instructions 를 `claude-md-and-agents-md` 로 바꾸는 방법이 문서에 있다.

이 부분은 **문서를 읽고 추론한 것이고 직접 실험하지 않았다.** 또 리포의 이슈·README 어디에도 이 동작에 대한 언급은 찾지 못했다(2026-10-01 기준). 반대로 Codex 계열은 AGENTS.md 가 기본 진입점이라 이 문제가 없다([AGENTS.md](https://agents.md/): 편집 중인 파일에 가장 가까운 AGENTS.md 가 우선).

## 한계

- 이 글은 **규격서를 읽은 분석**이다. dryforge 를 실제 프로젝트에 돌려 결과물을 평가하지는 않았다.
- README 의 효과 주장("오래 쓸수록 질문이 줄어든다" 등)은 **제작자 주장**이다. 이를 검증한 중립적 제3자 평가는 찾지 못했다.
- 리포는 생성 4개월, 커밋 대부분이 1인 작성이다. 규격이 앞으로 바뀔 수 있다. 인용한 문장은 v1.3.7 의 main 브랜치 기준이다.

---

*이 글은 Anthropic 의 Claude 와 함께 조사·작성했다. Claude Code 동작 설명은 Anthropic 공식 문서를 인용했고, 이해관계를 밝혀 둔다.*

## References

1. prekuter, "dryforge — harness-format.md" (v1.3.7, main). <https://github.com/prekuter/dryforge/blob/main/claude/skills/go/references/harness-format.md>
2. prekuter, "dryforge" 리포지토리 README·CHANGELOG·build/build.sh. <https://github.com/prekuter/dryforge>
3. Anthropic, "How Claude remembers your project" (Claude Code Docs — CLAUDE.md, auto memory, AGENTS.md). <https://code.claude.com/docs/en/memory>
4. AGENTS.md, "A simple, open format for guiding coding agents" (Agentic AI Foundation / Linux Foundation). <https://agents.md/>
5. Michael Nygard, "Documenting Architecture Decisions", Cognitect, 2011-11-15. <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
