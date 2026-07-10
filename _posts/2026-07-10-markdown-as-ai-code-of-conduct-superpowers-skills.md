---
layout: post
title: "마크다운 으로 쓰는 AI 행동강령 — obra/superpowers 스킬 해부"
date: 2026-07-10 12:50:00 +0900
categories: [ai, agent, engineering, tooling]
tags: [superpowers, claude-code, skills, ai-agent, prompt-engineering, tdd, behavior, markdown]
---

AI 에이전트 에게 "이렇게 일 해라" 를 가르치는 방법 은 보통 *프롬프트* 다. 그런데 obra(Jesse Vincent) 가 만든 **superpowers** 는 다른 길 을 간다 — 에이전트 의 **행동강령 을 `.md` 파일** 로 쓴다. 코드 도, 파인튜닝 도 아니고, 사람 이 읽을 수 있는 마크다운 한 장 이 에이전트 의 규율 이 된다.

지금 이 글 을 쓰는 세션 도 superpowers 위 에서 돈다. 그래서 실제 스킬 파일 을 열어, **마크다운 이 어떻게 '행동강령' 이 되는지** 를 해부 해 봤다.

---

## 1. 스킬 = SKILL.md 한 장

superpowers 에서 **스킬(skill)** 은 "검증된 기법·패턴 의 참조 가이드" 다. 각 스킬 은 폴더 하나 에 `SKILL.md` 한 파일 로 존재 한다:

```
skills/
  test-driven-development/
    SKILL.md
  systematic-debugging/
    SKILL.md
  verification-before-completion/
    SKILL.md
  ...
```

Claude Code 플러그인 으로 로드 되면, 에이전트 는 대화 중 "지금 이 스킬 이 필요 한가?" 를 판단 해 해당 `.md` 를 읽고 그대로 따른다. **행동 이 코드 에 컴파일 돼 있는 게 아니라, 문서 에 선언 돼 있다.**

---

## 2. SKILL.md 의 구조 — frontmatter + 본문

파일 은 두 부분 이다. YAML frontmatter 와 마크다운 본문:

```markdown
---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

## Overview
Write the test first. Watch it fail. Write minimal code to pass.
...
```

frontmatter 는 딱 두 필드 만 필수 다 — `name` 과 `description`. 그리고 여기 에 **첫 번째 설계 지혜** 가 숨어 있다.

`description` 은 *"이 스킬 이 무엇 을 하는지"* 가 아니라 **"언제 써야 하는지(Use when...)"** 만 적는다. 이유 가 반직관적 이다:

> description 이 워크플로 를 요약 하면, 에이전트 는 스킬 본문 을 안 읽고 *그 요약 만 따른다.* "리뷰 를 두 번 하라" 는 스킬 인데 description 에 "리뷰 를 한다" 라고 쓰면 — 에이전트 는 리뷰 를 한 번 만 하고 넘어간다.

description 은 스킬 을 *로드 할지 말지* 를 결정 하는 트리거 일 뿐, 행동 자체 는 본문 이 쥔다. 요약 은 지름길 을 만들고, 지름길 은 규율 을 새게 한다. 그래서 description 에는 *증상 과 상황* 만 담는다.

---

## 3. 왜 `.md` 가 "행동강령" 이 되나 — 규율 을 강제 하는 스킬

일반 문서 라면 여기 서 끝 이다. superpowers 가 특별 한 건, 일부 스킬 이 *권고* 가 아니라 **강제 규율** 이라는 점 이다. TDD 스킬 의 본문 을 보자:

```markdown
## The Iron Law
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```

이건 "가능 하면 테스트 먼저 쓰세요" 가 아니다. **철칙(Iron Law)** 이고, 예외 를 하나 하나 봉쇄 한다. "참고 용 으로 남겨두면 안 되나요?" → 안 된다. "조금 만 고쳐 쓰면?" → 안 된다. *Delete means delete.*

그리고 결정적 한 줄:

> **Violating the letter of the rules is violating the spirit of the rules.**
> (규칙 의 문구 를 어기는 것 은 규칙 의 정신 을 어기는 것 이다.)

이 한 문장 이 "저는 규칙 의 *정신* 을 따르는 거예요" 라는 부류 의 합리화 를 통째로 차단 한다.

---

## 4. 합리화 를 이기는 장치들

여기 서부터 가 진짜 흥미 롭다. superpowers 는 **에이전트 가 압박 을 받으면 스스로 빠져나갈 구멍 을 찾는다** 는 걸 전제 로 설계 됐다. 그래서 행동강령 안에 *합리화 방어 장치* 를 내장 한다.

**① Rationalization Table (합리화 대응표)** — 에이전트 가 할 법한 변명 을 미리 표 로 적고, 각각 에 반박 을 붙인다:

| 변명 | 현실 |
|------|------|
| "Too simple to test" | 단순한 코드 도 깨진다. 테스트 는 30초 다. |
| "I'll test after" | 나중 에 통과 하는 테스트 는 아무것 도 증명 못 한다. |
| "Tests after achieve same goals" | 사후 테스트 = "이게 뭐 하지?", 사전 테스트 = "뭘 해야 하지?" |

**② Red Flags 리스트** — "이런 생각 이 들면 멈춰라" 는 자기 점검 신호:

```markdown
## Red Flags - STOP and Start Over
- Code before test
- "I already manually tested it"
- "It's about spirit not ritual"
- "This is different because..."

All of these mean: Delete code. Start over with TDD.
```

에이전트 가 *"이건 좀 다른데…"* 라고 생각 하는 순간, 그 생각 자체 가 위반 신호 라고 스킬 이 미리 못 박아 둔 것. 행동강령 이 *자기 를 지키는 항체* 를 품고 있는 셈 이다.

---

## 5. 실패 유형 에 형식 을 맞춘다

superpowers 문서 의 가장 정교한 부분 은 **"어떤 실패 에는 어떤 형식 이 맞는가"** 다. 무조건 금지(prohibition) 가 답 이 아니다:

| 기저 실패 | 맞는 형식 | 틀린 형식 |
|-----------|----------|----------|
| 규칙 을 알면서 압박 에 어긴다 | 금지 + 합리화표 + Red Flags | 물렁한 권고("가능 하면…") |
| 따르긴 하는데 출력 모양 이 틀리다 | 긍정형 레시피(출력 이 *무엇 인지* 명시) | 금지 목록("하지 마라") |
| 만들면서 필수 요소 를 빠뜨린다 | 템플릿 의 REQUIRED 슬롯(구조) | 산문 형 잔소리 |
| 조건 에 따라 달라야 한다 | 관측 가능 한 조건문("brief 가 있으면…") | 무조건 규칙 + 예외 절 |

**금지 는 협상 을 부른다.** "하지 마라" 는 경쟁 하는 인센티브 앞 에서 에이전트 가 흥정 한다. 반면 *레시피*("출력 은 A·B·C 로 구성 된다") 는 협상 할 게 없다 — 모양 이 맞거나 안 맞거나 둘 중 하나. 행동강령 을 쓸 때 조차 *형식 이 결과 를 좌우* 한다는 통찰 이다.

---

## 6. 스킬 을 만드는 법 도 TDD 다

그럼 이 `.md` 들 은 어떻게 쓰나? superpowers 의 답 은 급진적 이다 — **스킬 작성 은 문서 에 적용한 TDD** 다.

```
RED   : 스킬 없이 압박 시나리오 를 돌려, 에이전트 가 실패 하는 걸 관찰 한다
        (변명 을 verbatim 으로 받아 적는다)
GREEN : 그 변명 들 을 정확히 겨냥한 스킬 을 쓴다
REFACTOR: 새 변명 이 나오면 반박 을 추가 한다 — bulletproof 될 때 까지
```

핵심 원칙 이 TDD 와 똑같다:

> **If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.**
> (스킬 없이 에이전트 가 실패 하는 걸 못 봤다면, 그 스킬 이 옳은 걸 가르치는지 모른다.)

그래서 철칙 도 똑같다 — **NO SKILL WITHOUT A FAILING TEST FIRST.** 테스트(압박 시나리오) 먼저 안 돌리고 스킬 부터 쓰면? 지우고 다시. 행동강령 을 *경험적 으로 검증* 하는 것 이다. "이렇게 하면 좋을 것 같다" 가 아니라, "이 문구 가 실제로 위반 을 막았다" 를 데이터 로 확인.

---

## 7. 고찰 — 왜 프롬프트 가 아니라 파일 인가

행동 을 마크다운 파일 로 빼면 세 가지 가 생긴다.

- **버전 관리** — 행동강령 이 git 에 들어간다. "왜 이 규칙 이 생겼나" 가 커밋 이력 에 남고, 나쁜 규칙 은 revert 된다. *행동 이 코드 처럼 다뤄진다.*
- **조합 가능성** — 스킬 이 다른 스킬 을 참조 한다(`REQUIRED BACKGROUND: test-driven-development`). 작은 규율 들 이 레고 처럼 쌓인다.
- **온디맨드 로드** — 전부 를 항상 프롬프트 에 넣으면 컨텍스트 가 터진다. description 으로 *지금 필요한 것만* 골라 읽는다. 200k 토큰 을 아끼는 설계.

더 깊은 층 도 있다. 이건 결국 **AI 의 행동 을 사람 이 읽고·고치고·리뷰 할 수 있는 인공물 로 외재화** 하는 시도 다. 모델 가중치 속 에 암묵 적 으로 박힌 습관 을, *명시적 문서* 로 끌어낸다. 그러면 팀 이 그걸 두고 토론 하고, PR 로 고치고, 실패 시나리오 로 검증 할 수 있다.

재미있는 건, 이 방식 이 사람 조직 의 *행동강령* 과 똑 닮았다는 것. 좋은 규율 은 "착하게 굴자" 같은 구호 가 아니라 — *구체적 상황*, *예외 봉쇄*, *변명 대응표*, *자기 점검 신호* 로 되어 있다. superpowers 는 그걸 AI 용 으로 다시 쓴 것 뿐 이다.

**행동 을 문서 로 쓰면, 행동 을 디버깅 할 수 있다.** 마크다운 한 장 이 프롬프트 보다 강한 이유 는 거기 있다 — 읽히고, 버전 되고, 실패 로 검증 되니까.

---

_관련: [멀티 에이전트 란 무엇 인가]({% post_url 2026-07-09-what-is-multi-agent %}) · [실무 AI 사용법 8 원칙]({% post_url 2026-07-02-ai-in-practice-8-self-assessment %})_
