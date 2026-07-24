---
layout: post
title: "Claude Code /goal로 PRD→MVP→SPEC 개발하기 — 조건이 완료를 정의한다"
date: 2026-07-24 10:55:00 +0900
categories: [AI, Productivity]
tags: [ClaudeCode, GoalSkill, PRD, MVP, SPEC, SpecDrivenDevelopment, DoneCriteria, Harness]
---

# PRD에서 시작해 /goal로 끝내는 개발 흐름

아이디어를 검증된 코드로 바꾸는 실전 흐름은 대략 이렇다 — **PRD를 쓰고 → MVP로 범위를 자르고 → ROADMAP을 SPEC 단위로 쪼갠 뒤 → 각 SPEC을 Claude Code의 `/goal`로 개발**한다. 아래는 그 과정을 단계로 정리한 것이다.

![PRD→MVP→ROADMAP→SPEC→goal 개발 워크플로 세션 목록 — PRD와 MVP 범위 자르기, ROADMAP을 SPEC으로 쪼개기, MVP 레벨 하네스 설정, PRD기반 SPEC 문서로 goal 개발](/assets/images/claude-goal-skill-prd-spec-workflow.jpg)

먼저 이 글의 주인공 `/goal`이 *정확히* 무엇인지부터. (Claude Code 공식 문서 기준)

> **`/goal <조건>`** 은 Claude Code의 **네이티브 기능**(v2.1.139+)이다. *완료 조건*을 세우면, 세션이 그 조건을 만족할 때까지 **매 턴 자동으로 계속 작업**한다. 각 턴이 끝날 때마다 **가벼운 별도 모델(기본 Haiku)이 조건 충족 여부를 판정**하고, 아직이면 스스로 다음 턴을 시작한다. 세션당 목표는 하나, 충족되면 자동 해제.

핵심은 마지막 문장이다 — **완료를 판정하는 건 작업하던 모델이 아니라 *별도의 평가 모델*이다.** 이게 왜 중요한지는 아래에서 드러난다.

---

## 1. PRD를 쓰고 MVP 범위를 자른다

시작은 PRD(제품 요구사항 문서)다. 하지만 PRD를 다 만들려 들면 영영 못 시작한다. 그래서 **MVP로 범위를 자른다** — "이번에 반드시 되는 것"과 "이번엔 안 하는 것(비목표)"을 명시적으로 가른다.

이건 [멀티에이전트가 손해인 순간](/2026/07/24/when-multi-agent-is-a-loss/)에서 본 "단순한 것부터"와 같은 규율이다. MVP의 비목표 목록은 [SPEC.md의 비목표](/2026/07/24/harness-spec-plan-done-criteria/)가 되어, 이후 과잉 구현과 범위 확장을 막는 가장 싼 장치가 된다.

- **PRD**: 문제·사용자·성공 지표·전체 그림
- **MVP 컷**: 그중 "가장 얇게 가치를 증명하는 슬라이스" + 명시적 비목표

## 2. ROADMAP을 SPEC 단위로 쪼갠다

MVP가 정해지면 ROADMAP을 **작업 단위(SPEC)로 분해**한다. 각 SPEC은 [독립적으로 가치 있고 사용자에게 보이는 결과 하나](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)이고, **각각 검증 가능한 수용 기준**을 가진다.

```markdown
# SPEC-auth.md
## 목표: 이메일/비번 로그인
## 수용 기준 (각각 검증 명령 포함)
1. 로그인 성공 → JWT 발급  — `pytest tests/auth/test_login.py`
2. 잘못된 비번 → 401       — `pytest tests/auth/test_login.py::test_bad_pw`
3. lint/type 통과          — `ruff check . && mypy .`
## 비목표: OAuth, 비번 재설정 (다음 SPEC)
```

여기서 수용 기준을 *검증 명령*으로 적는 게 핵심이다 — 그게 곧 다음 단계에서 `/goal`의 **완료 조건**이 되기 때문이다.

## 3. MVP 레벨에서 '하네스 설정'이 불편해지는 이유

솔직한 지점. [앞서 정리한 무거운 하네스](/2026/07/24/agentic-feedback-eval-pipeline/)(증거 원장·다중 게이트·역할 분리 서브에이전트…)는 강력하지만, **MVP 단계에선 그 세팅 자체가 마찰**이다. 아직 가치도 검증 안 된 것에 파이프라인부터 까는 건 [저가치·저복잡도 작업에 과도한 비용](/2026/07/24/when-multi-agent-is-a-loss/)을 무는 셈이다.

그래서 MVP엔 **가벼운 하네스**가 필요하다. 그리고 `/goal`이 정확히 그것이다 — 별도 인프라 없이, *완료 조건 하나*로 "될 때까지 돌리고, 별도 모델이 됐는지 판정"하는 최소 하네스를 세션에 붙인다. 무거운 하네스의 두 핵심(자동 반복 + 독립 검증)을 명령 한 줄로 얻는다.

## 4. PRD 기반 SPEC을 /goal로 개발한다

이제 각 SPEC을 `/goal`로 돌린다. **SPEC의 수용 기준을 그대로 완료 조건으로** 넣는다:

```text
/goal SPEC-auth.md의 수용기준 전부 충족: pytest tests/auth 가 전부 green,
      ruff/mypy clean, 그리고 SPEC 비목표(OAuth/비번재설정)는 건드리지 않음
```

그러면 무슨 일이 벌어지나:
1. `/goal`이 **즉시 첫 턴을 시작**한다(별도 프롬프트 불필요). 상태줄에 `◎ /goal active` 표시.
2. Claude가 구현 → 턴 종료.
3. **별도 평가 모델(Haiku)이 조건을 판정** — "pytest green인가? lint clean인가?" 아니면 근거와 함께 "미충족".
4. 미충족이면 Claude가 **스스로 다음 턴**을 시작해 이어서 고친다.
5. 조건 충족 시 목표 **자동 해제**.

`/goal` 만 치면 현재 상태(턴 수·토큰·판정 사유)를, `/goal clear` 로 중단한다. 비대화형으로도: `claude -p "/goal CHANGELOG에 이번 주 머지된 PR마다 항목이 있다"`.

### 왜 이게 '검증된 개발'인가 — 평가자 독립성

`/goal`의 진짜 가치는 자동 반복이 아니라 **완료 판정을 작업 모델이 아닌 별도 모델이 한다**는 점이다. 작업하던 모델에게 "다 됐어?"라고 물으면 자기 결정을 정당화하기 쉽다. `/goal`은 매 턴 *신선한 평가자*가 조건을 본다 — 이건 시리즈 내내 강조한 **[완료는 승인이 아니다](/2026/07/23/agent-roles-explorer-implementer-verifier/)**, **[작성자≠검증자](/2026/07/24/agentic-feedback-eval-pipeline/)** 원칙의 *네이티브 구현*이다.

그리고 그 평가자는 하나의 **grader**다 — 조건이 "pytest green"처럼 결정론적이면 [test/exact 채점](/2026/07/24/eval-harness-grader-types/)에 가깝고, "설명이 명확한가"처럼 주관적이면 LLM-judge다. **그래서 완료 조건을 검증 명령으로 못 박을수록** 평가가 결정론적이고 게이밍이 어렵다. SPEC에서 수용 기준을 `pytest ...`로 적으라 한 이유가 여기서 회수된다.

---

## /goal 정확한 레퍼런스 (공식)

| 항목 | 내용 |
|---|---|
| 정체 | 네이티브 기능(플러그인/스킬 아님), v2.1.139+ |
| 설정 | `/goal <조건>` — 즉시 시작 · `/goal` 상태 · `/goal clear` 중단 |
| 평가 | 매 턴 종료 시 별도 소형 모델(기본 Haiku)이 조건 yes/no + 사유 |
| 지속성 | 세션 내 유지(압축에도 생존), `--resume`/`--continue` 시 *활성 상태면* 복원(타이머·토큰 기준선은 리셋). **디스크 파일은 안 남김** |
| 조건 길이 | 최대 4,000자(문서화됨) |
| 언제 | 끝 상태가 명확한 상당량 작업(모듈 마이그레이션·설계문서 구현·이슈 백로그 소거) |
| 언제 아님 | 시간 주기 폴링→`/loop`, 세션 넘는 반복→Routines, 커스텀 완료 로직→Stop hook |

주의: 내 환경의 `/ultragoal`(oh-my-claudecode 플러그인)은 `.omc/ultragoal/`에 계획 아티팩트를 남기고 `/goal` 핸드오프 텍스트를 출력하는 *상위 래퍼*로, 네이티브 `/goal`과는 별개다.

---

## 한 줄 결론

이 흐름의 골격은 **문서로 좁히고(PRD→MVP→SPEC), 조건으로 닫는다(/goal)** 이다. PRD·SPEC은 *무엇을*을 사람이 정하고, `/goal`은 *됐는지를 별도 평가자가* 판정하며 그때까지 돌린다. MVP엔 무거운 하네스 대신 이 최소 하네스가 맞고, **완료 조건을 검증 명령으로 적을수록** 그 판정이 믿을 만해진다. 조건이 곧 완료의 정의다.

---

## 출처

- 첨부 이미지: 사용자 제공(PRD→SPEC→goal 개발 워크플로 세션 목록).
- Claude Code, **/goal 공식 문서** — 네이티브 기능·매 턴 별도 모델 판정·조건 기반 반복·지속성·다른 방식과 비교: <https://code.claude.com/docs/en/goal>
- 개념 근거(본인 정리글): [하네스의 세 문서 SPEC/PLAN/DONE](/2026/07/24/harness-spec-plan-done-criteria/) · [Eval Harness와 Grader 6종](/2026/07/24/eval-harness-grader-types/) · [Explorer/Implementer/Verifier](/2026/07/23/agent-roles-explorer-implementer-verifier/) · [멀티에이전트가 손해인 순간](/2026/07/24/when-multi-agent-is-a-loss/)

> 참고: `/goal` 동작·요건은 Claude Code 공식 문서 기준이며 버전(v2.1.139+)에 따라 다를 수 있다. 평가 토큰 비용·판정 프롬프트 등 일부 내부 세부는 공식 문서에 명시돼 있지 않아 본문에서 단정하지 않았다.
