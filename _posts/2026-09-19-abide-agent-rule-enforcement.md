---
layout: post
title: "Abide — 코딩 에이전트가 AGENTS.md 규칙을 어기는 순간을 잡는 훅 도구"
date: 2026-09-19 14:54:02 +0900
categories: [ai, devtools]
tags: [abide, claude-code, codex, opencode, agents-md, hooks, llm]
---

코딩 에이전트를 써본 사람이라면 누구나 겪는 문제가 있다. AGENTS.md 나 CLAUDE.md 에 아무리 규칙을 적어놔도 — "검증은 Yup 으로, 손으로 짜지 마라", "호출자가 하나뿐인 헬퍼 만들지 마라", "시키지 않은 것 추가하지 마라" — 에이전트는 그걸 어긴다. 린터로 잡을 수 있는 규칙이 아니라서 아무것도 강제하지 못한다.

[**Abide**](https://github.com/coldteadotai/abide) 는 정확히 이 틈을 겨냥한 오픈소스(MIT) 도구다. Claude Code · Codex · OpenCode 세 에이전트에 훅으로 끼어들어, **매 편집마다** 리포의 자연어 규칙 위반 여부를 검사하고, 위반이면 에이전트에게 어느 규칙인지 알려 **같은 턴 안에서 고치게** 만든다. 이 글은 리포의 README·벤치마크 문서·코드를 근거로 내용을 정리한 것이다.[^repo]

## 동작 방식 — 훅 4개와 rubric

설치는 두 줄이다:

```
npx @coldtea/abide login    # TypeSafe API 키 1회 저장
npx @coldtea/abide init     # 이 머신의 모든 에이전트에 훅 설치
```

에이전트별로 훅이 들어가는 위치가 다르다 — Claude Code 는 `~/.claude/settings.json`, Codex 는 `~/.codex/hooks.json`, OpenCode 는 훅 프로세스가 없어 플러그인(`~/.config/opencode/plugins/abide.js`)으로 동작한다. `--project` 를 붙이면 리포 단위로 설치돼 팀원이 체크아웃과 함께 받는다.[^repo]

훅은 에이전트당 4개다:[^repo]

1. **세션 시작** — 지시 파일들(AGENTS.md·CLAUDE.md 등)을 해시하고, 바뀌었으면 에이전트에게 rubric 재컴파일을 요청
2. **턴 시작** — git 으로 워킹트리 스냅샷
3. **편집 직후** — 그 hunk 에 edit 단계 규칙 실행
4. **턴 종료** — 스냅샷 대비 턴 전체 diff 에 turn 단계 규칙 실행 (셸 명령이 쓴 파일 포함)

핵심 산출물은 `.abide/rubric.json` 이다. 에이전트가 리포의 지시 파일을 읽고 규칙들을 구조화된 rubric 으로 컴파일하는데(그 절차 자체가 `skills/abide-compile` 스킬로 정의돼 있다), 설계 원칙이 명확하다 — **규칙은 사용자의 파일에서만 나온다. 도구가 "있어야 할 규칙"을 임의로 추가하지 않는다.** 모든 판정은 rubric 의 규칙을 지목하고, 모든 규칙은 원본 지시 파일의 몇 번째 줄에서 왔는지 인용한다. 오판이 나오면 모델을 탓하는 게 아니라 규칙 문구를 고치면 된다.[^skill]

규칙에는 실행 시점(`edit`/`turn`)과 적용 범위(`scope` glob)가 붙는다. "시킨 것보다 많이 추가했는가" 같은 질문은 12개 편집 중 1번째에서는 답이 없으니 turn 단계로 가는 식이다. 판정은 확률 밴드로 나뉜다 — **0.8 이상이면 에이전트에게 수리 지시, 0.5~0.8 은 사용자에게만 노트, 그 미만은 침묵.**[^repo]

## 왜 이게 이제야 가능한가 — 비용 산수

이 아이디어 자체는 새롭지 않다. 문제는 산수였다. 일반 LLM 으로 편집 하나를 검사하면 약 2,500 토큰, 편집당 1센트 이상에 수 초가 걸리고, 답이 산문으로 와서 파싱해야 하며 온전히 신뢰할 수 없다. 하루 200번 편집이면 시작할 이유가 없는 게임이다.[^repo]

Abide 는 검사를 [TypeSafe](https://typesafe.ai) 의 결정 모델(decision model) **Jev** 에 맡긴다. 규칙 하나와 diff 하나를 주고 타입이 정해진 질문을 던지면 **보정된 확률 하나만** 돌아온다. 자유 텍스트가 없으니 지어낼 것도 없고, 리포 주장으로는 검사당 약 300ms · 수천분의 1센트다(1,000~1,600 입력 토큰, $0.00004~0.00007). Jev 는 규칙과 diff 만 보고 대화 맥락은 보지 않으므로, 200번째 편집도 1번째와 똑같이 검사된다 — 컨텍스트가 길어지면 규칙을 잊는 에이전트와 정확히 반대 성질이다.[^repo]

## 저자 자체 벤치마크 — "13턴에 1번"의 출처

README 상단의 "1 in 13 turns break a rule no linter can catch" 는 저자가 자기 리포 두 곳에서 돌린 자체 측정이다. 방법론과 규칙별 수치는 공개돼 있지만 대상 코드 일부가 비공개라 완전 재현은 안 되는, **벤더(저자) 주장**으로 읽어야 한다. 중립 제3자 검증은 아직 없다(2026-09-19 기준 v0.0.1 의 신생 프로젝트다).[^bench]

방법 자체는 흥미롭다. `abide replay` 가 Claude Code 의 과거 세션 트랜스크립트(`~/.claude/projects/`)에서 모든 Edit/Write 를 훅 페이로드로 재구성해, 그 리포의 rubric 으로 "그때 설치돼 있었다면 뭘 잡았을까"를 재판정한다. 93개 실제 세션, 1,256개 편집, 147개 턴을 22센트에 재생했고:[^bench]

- 편집의 3.1%, 턴의 10% 가 0.8 이상으로 플래그
- 독립 리뷰어(규칙 원문을 엄격 적용한 Claude)가 확인한 결과 **정밀도는 edit 규칙 26%, turn 규칙 73%** — 단일사용 추상화·500줄 초과 파일·중복 로직 같은 turn 레벨 규칙이 잘 맞았다
- 오탐의 대부분은 규칙 2개에 집중됐고, 저자 분석으로는 모델이 아니라 rubric 문구·scope 로 고칠 문제
- 위반율은 턴이 진행돼도 오르지 않았다 — 에이전트는 "잘하다가 드리프트하는" 게 아니라 **첫 편집부터 일정한 비율로** 규칙을 어긴다

이 26% 라는 edit 정밀도를 저자가 숨기지 않고 표로 공개한 점, 그리고 오탐을 `calibrate`(git 히스토리의 실제 hunk 20개로 규칙 채점)와 `tune`(안 맞는 규칙 재작성)이라는 도구로 되먹임하는 구조는 정직한 설계다.

## 주의할 점

- **변경 라인이 외부로 나간다.** 검사할 diff 가 TypeSafe API 로 전송된다(zero data retention 요청을 매 호출에 붙인다고 하나, 이는 벤더 약속이다). 민감한 코드베이스라면 이 지점부터 평가해야 한다.[^repo]
- **fail-open 설계.** 키가 없거나 네트워크가 끊기면 편집은 검사 없이 통과하고 누락만 `.abide/events.jsonl` 에 기록된다. 세션을 깨지 않는다는 장점의 뒷면으로, 강제가 조용히 꺼질 수 있다는 뜻이다.[^repo]
- **v0.0.1.** 2026-09-18 마지막 커밋의 초기 프로젝트로, 벤치마크도 저자 리포 2곳뿐이다. 성능·정밀도 주장에 대한 중립 헤드투헤드는 부재하다.

## 정리

Abide 가 겨냥한 문제 — "지시 파일의 자연어 규칙은 아무도 강제하지 않는다" — 는 에이전트 코딩을 실제로 운영하는 사람이라면 체감하는 실재하는 틈이다. 해법의 골격도 깔끔하다: 규칙을 rubric 으로 컴파일하고, 싸고 빠른 결정 모델로 매 편집을 판정하고, 위반은 에이전트가 같은 턴에 수리한다. 판정 근거가 항상 사용자 자신의 규칙 문구로 소급되는 구조라, 도구가 취향을 강요하는 게 아니라 **이미 적어둔 규칙이 비로소 효력을 갖게** 만드는 쪽이다. 신생 프로젝트인 만큼 수치는 저자 주장으로 걸러 읽되, 훅 4개 + rubric + 결정 모델이라는 아키텍처 자체는 에이전트 거버넌스 도구가 어디로 가는지 보여주는 좋은 표본이다.

---

## References

[^repo]: coldteadotai, "Abide" GitHub 저장소 README (v0.0.1, 최종 커밋 2026-09-18 기준). <https://github.com/coldteadotai/abide>
[^bench]: coldteadotai, "Replay: what abide would have caught in 93 real sessions" — 저장소 내 벤치마크 문서(저자 자체 측정, 방법·규칙별 표 공개, 대상 hunk 는 비공개). <https://github.com/coldteadotai/abide/blob/main/benchmarks/replay/README.md>
[^skill]: coldteadotai, `skills/abide-compile/SKILL.md` — rubric 컴파일 절차 정의. <https://github.com/coldteadotai/abide/blob/main/skills/abide-compile/SKILL.md>
