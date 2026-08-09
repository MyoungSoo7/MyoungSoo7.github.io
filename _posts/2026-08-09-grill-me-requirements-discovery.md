---
layout: post
title: "grill-me로 모호한 아이디어를 결정 가능한 설계로 바꾸는 법"
date: 2026-08-09 13:30:00 +0900
categories: [AI, Engineering, Productivity]
tags: [grill-me, Agent Skills, Requirements, Planning, Claude Code, Codex, Harness Engineering]
---

# `grill-me`로 모호한 아이디어를 결정 가능한 설계로 바꾸는 법

## 결론

[`mattpocock/skills`의 `grill-me`](https://github.com/mattpocock/skills/blob/main/docs/productivity/grill-me.md?utm_source=chatgpt.com)는 구현 계획을 대신 써주는 도구가 아니라, **아직 결정되지 않은 아이디어를 질문 라운드로 검증해 실행 가능한 결정으로 바꾸는 Stateless 요구사항 탐색 스킬**이다.

```text
느슨한 아이디어
→ 질문 frontier
→ 숨은 결정 노출
→ 범위·trade-off 확정
→ spec/plan/구현으로 handoff
```

우리 프로젝트에서는 web01 AI 포트폴리오·Settlement 분석설계·Agent Harness 기획을 시작하기 전에 사용하면 유용하다. 다만 이미 충분히 구체적인 이슈나 즉시 수정해야 하는 장애에는 과하다.

## 1. `grill-me`가 하는 일

공식 문서의 핵심은 다음과 같다.

```text
loose idea를 입력
→ Agent가 질문
→ 사용자가 결정
→ 다음 질문 frontier 생성
→ 모든 결정 가능한 가지가 소진될 때 종료
```

여기서 frontier는 현재까지 답한 전제 위에서 지금 물을 수 있는 질문의 집합이다. 앞 질문의 답을 기다려야 하는 질문을 너무 일찍 묻지 않도록 설계된 점이 핵심이다.

예를 들어:

```text
아이디어:
고객 상담 AI를 만들자
```

바로 “어떤 React 컴포넌트를 만들까요?”라고 묻지 않고:

```text
대상 사용자는 고객인가 상담사인가?
답변 실패 시 handoff인가 재질문인가?
실제 CRM인가 synthetic CRM인가?
실시간 음성인가 파일 기반 demo인가?
근거 없는 답변을 허용할 것인가?
```

처럼 상위 결정부터 좁힌다.

## 2. Stateless라는 점이 중요하다

`grill-me`는 공식 설명상 파일을 쓰지 않고 workspace를 남기지 않는 Stateless 스킬이다.

```text
입력: 대화 속 아이디어
출력: 더 선명한 결정과 공통 문맥
파일 생성: 없음
저장소 변경: 없음
```

장점:

- 어떤 저장소·제품·업무 의사결정에도 사용 가능
- 별도 초기 설정이 거의 없음
- 코드베이스에 영향을 주지 않음
- 아이디어가 소프트웨어가 아니어도 사용 가능

단점:

- 결정 결과를 자동으로 `CONTEXT.md`나 ADR에 저장하지 않음
- 세션이 끝나면 별도 handoff가 없을 경우 결정이 사라질 수 있음
- 코드베이스와 실제 제약을 자동으로 대조하지 않음

따라서 우리 운영에서는 다음처럼 연결하는 것이 좋다.

```text
/grill-me
  → 대화로 결정
  → handoff 또는 수동 decision.md
  → /to-spec·계획서
  → TDD·구현
```

## 3. 언제 사용하는가

공식 문서의 사용 기준을 우리 작업에 맞추면 다음과 같다.

### 사용하는 경우

```text
새 기능 방향
제품 아이디어
사업 의사결정
아키텍처 선택
글의 논지·목차
큰 작업의 범위 정의
```

예:

```text
“Settlement account-service를 은행 계정계로 확장할까?”
“web01에 보이스봇을 어느 수준까지 넣을까?”
“100개 Agent를 실제 실행할까, 대기 슬롯으로 둘까?”
```

### 사용하지 않는 경우

```text
정확한 파일과 수정사항이 이미 확정된 버그
긴급 장애 대응
단순 rename·formatting
이미 승인된 구현 계획의 기계적 실행
```

이미 다음이 정해져 있다면 grill-me보다 바로 TDD가 빠르다.

```text
파일
API 계약
실패 테스트
완료 조건
rollback
```

## 4. 사용법

새로운 대화에서 명시적으로 호출한다.

```text
/grill-me
```

그 뒤 아이디어를 설명한다.

```text
/grill-me
Settlement의 account-service를 축으로 예금·적금·연금 시스템으로 확장하고 싶다.
코드 구현 전에 도메인 경계와 위험을 결정하고 싶다.
```

또는:

```text
/grill-me
web01에 삼성SDS 지원용 고객 상담봇·상담사 보조·수리봇·보이스봇 포트폴리오를 만들고 싶다.
실제 연동과 mock의 경계를 결정하고 싶다.
```

중요한 사용 방식:

```text
새 대화에서 시작
Plan mode는 끄기
Agent가 계획을 먼저 쓰게 하지 않기
질문에 적극적으로 반박하기
모르는 것은 모른다고 답하기
```

Plan mode는 Agent를 계획 생성으로 서두르게 할 수 있으므로, 먼저 질문을 통해 결정하는 `grill-me`의 목적과 충돌할 수 있다.

## 5. 질문 라운드 운영

`grill-me`는 한 질문씩만 무한히 묻는 방식이 아니라 라운드 단위로 frontier를 묻는다.

```text
Round 1:
문제·사용자·목표·범위

Round 2:
상태·실패·권한·데이터·외부 의존성

Round 3:
trade-off·운영·비용·평가·rollback

Round 4:
남은 암묵적 결정과 handoff 조건
```

좋은 세션은 질문 수가 많아서가 아니라, 뒤 라운드가 앞 라운드의 결정 위에 쌓인다.

종료 기준:

```text
현재 frontier가 비어 있음
모든 중요한 branch에 결정이 있음
각 결정에 이유가 있음
남은 미확정은 명시됨
```

## 6. 수동적으로 답하면 실패한다

공식 문서가 강조하는 가장 큰 실패는 Agent의 질문에 계속 동의만 하는 것이다.

```text
Agent: 고객 상담봇이면 React 화면이 필요하겠네요.
사용자: 네.
Agent: 실시간 음성도 넣을까요?
사용자: 네.
Agent: production CRM도 연결하죠?
사용자: 네.
```

이렇게 하면 많은 질문을 거쳤어도 실제 결정은 없다. Agent가 만든 가정을 사용자가 승인한 것처럼 보일 뿐이다.

활동적으로 답하는 방식:

```text
그 범위는 이번 포트폴리오에서 제외한다.
실시간 전화망이 아니라 WAV 기반으로 제한한다.
실제 CRM 대신 Synthetic CRM으로 계약만 증명한다.
근거 없는 질문은 handoff한다.
이 결정은 비용보다 안전성을 우선한 것이다.
```

`grill-me`의 품질은 질문 개수가 아니라 **사용자가 얼마나 명시적으로 선택하고 반박했는가**에 좌우된다.

## 7. Grilling할 수 없는 질문

모든 불확실성이 대화로 해결되지는 않는다.

다음은 직접 보고 판단해야 하는 질문이다.

```text
긴 form 하나인가 세 페이지인가?
모바일 화면의 실제 배치는 어떤 느낌인가?
버튼 간격이 충분한가?
차트가 읽기 쉬운가?
```

이런 질문은 말로만 계속 돌리지 않는다.

```text
grill 중단
→ throwaway prototype
→ 실제 화면 관찰
→ 한 줄 결정
→ 다시 spec/구현
```

우리 web01 UI에서도 “상담사 화면을 한 페이지로 할까?”는 prototype을 먼저 만드는 편이 낫다. `grill-me`가 디자인 리뷰나 브라우저 렌더링 검증을 대체하지 않는 이유다.

## 8. `grill-me`·`grill-with-docs`·`wayfinder` 비교

저장소와 관련 문서가 제시하는 세 가지 흐름을 구분해야 한다.

| 스킬 | 대상 | 상태 | 적합한 상황 |
| --- | --- | --- | --- |
| `grill-me` | 무엇이든 | Stateless | 아이디어·사업·글·초기 설계 |
| `grill-with-docs` | 코드베이스 포함 | Stateful | 코드·문서·ADR과 정렬해야 할 때 |
| `wayfinder` | 큰 범위 | Map/다중 세션 | 한 세션으로 끝나지 않는 대형 작업 |

선택 기준:

```text
아이디어만 있다
→ grill-me

기존 repository 제약을 읽어야 한다
→ grill-with-docs

작업이 너무 커서 여러 grilling session이 필요하다
→ wayfinder
```

우리 Settlement 분석에는 `grill-me`로 초기 범위를 결정한 뒤, 실제 repository와 ADR·Graphify를 읽는 별도 분석으로 이어가는 방식이 적합하다.

## 9. 우리 프로젝트 적용

### web01 AI 포트폴리오

`grill-me`에 다음을 물을 수 있다.

```text
1. 삼성SDS JD 네 가지 업무 중 무엇을 demo의 중심으로 할 것인가?
2. 실제 Gemini·Qdrant·CRM·STT/TTS와 mock의 경계는?
3. 고객·상담사·기사 중 첫 사용자 여정은?
4. citation·handoff를 필수 acceptance criteria로 둘 것인가?
5. 실제 전화망 없이 음성 파일 demo로 충분한가?
6. 평가 세트와 Trace를 어느 수준까지 만들 것인가?
```

결정 결과:

```text
고객 상담 flow 우선
Qdrant local
Gemini adapter
Synthetic CRM
WAV 기반 voice demo
citation·handoff·trace 필수
```

처럼 정리한 뒤 TDD와 구현으로 넘긴다.

### Settlement 분석설계

```text
account-service를 GL 코어로 고정할 것인가?
예금·적금·연금을 같은 서비스에 넣을 것인가?
고객 subledger와 enterprise GL을 분리할 것인가?
실제 banking integration을 구현할 것인가 설계로 제한할 것인가?
```

이 질문을 먼저 결정하면 코드 저장소의 현재 구현과 포트폴리오 표현을 혼동하지 않게 된다.

### Agent Harness

```text
봇1~4의 Identity는 무엇인가?
Persona는 언제 바뀌는가?
누가 설계·구현·리뷰·전달을 맡는가?
어떤 작업은 반드시 사람 승인을 거치는가?
100개 Agent는 실행 슬롯인가 대기 슬롯인가?
```

`grill-me`는 여기서 하네스 구현을 대신하지 않지만, 하네스가 지켜야 할 책임·권한·완료 조건을 먼저 결정하게 한다.

## 10. `grill-me`와 TDD·Harness의 연결

`grill-me`는 TDD 이전의 요구사항 결정 계층이다.

```text
Grill
  아이디어·범위·결정

Spec
  입력·출력·상태·실패 조건

TDD
  RED·GREEN·REFACTOR

Harness
  worktree·권한·loop·evidence

Delivery
  commit·PR·CI·승인
```

이 흐름에서 `grill-me`가 하는 일은 “테스트를 작성”하는 것이 아니라, **무엇을 테스트할지 결정하는 것**이다.

예:

```text
grill 결정:
근거 없는 상담 질문은 자동 답변하지 않는다.

TDD:
unsupported query → citation 0 + handoff true

Harness:
FakeLLM·Synthetic fixture·trace 검증

Delivery:
테스트 결과·PR·평가 리포트
```

## 11. Claude Code와 Codex에서의 활용

### Claude Code

새로운 설계나 장기 프로젝트 방향을 `grill-me`로 먼저 정리할 수 있다.

```text
새 Claude session
→ /grill-me
→ 결정 대화
→ 같은 session에서 /to-spec 또는 계획 handoff
```

공식 문서가 강조하듯, `grill-me` 직후 같은 대화의 context를 이어서 spec으로 넘기는 것이 의미가 있다. 단, 중요한 결정은 최종적으로 문서화해야 한다.

### Codex

Codex에서는 더 작은 범위로 grill한다.

```text
$grill-me
PaymentCaptured retry 정책의 선택지를 결정하고 싶다.
```

그 후:

```text
결정된 계약
→ 독립 worktree
→ 작은 TDD task
→ diff/test 제출
```

Claude가 구조를 조정하고 Codex가 bounded 구현을 맡는 구조와 잘 결합된다.

## 12. `grill-me`의 한계

### Stateless의 기억 손실

파일을 쓰지 않으므로, 중요한 결정은 다음 세션 전에 직접 보존해야 한다.

```text
결정 요약
ADR
CONTEXT.md
handoff.md
```

### 질문이 실행을 대체할 수 있음

질문이 길어질수록 설계를 잘하고 있다는 착각이 생길 수 있다. 일정 라운드 후에도 prototype·실험·source inspection으로 넘어가지 않으면 dumb zone에 들어갈 수 있다.

### 모델 품질 의존

Grilling은 시스템이 어떻게 깨지는지 추론하는 능력에 의존한다. 공식 문서도 이 작업에는 모델 선택이 다른 스킬보다 중요하다고 설명한다.

### 사용자 답변 품질 의존

Agent가 좋은 질문을 해도 사용자가 계속 동의하거나 추측으로 답하면 결과는 약하다.

### 기존 코드와 자동 정렬되지 않음

repository의 실제 API·DB·배포 구조를 반영하려면 `grill-with-docs`나 직접적인 code reconnaissance가 필요하다.

## 13. 실전 운영 체크리스트

```text
[ ] 새 대화에서 시작했는가
[ ] Plan mode가 꺼져 있는가
[ ] 아이디어의 범위를 한 문장으로 설명했는가
[ ] 질문에 적극적으로 반박했는가
[ ] 모르는 것은 모른다고 했는가
[ ] 질문으로 해결할 수 없는 것은 prototype으로 넘겼는가
[ ] 라운드별 결정과 미확정을 정리했는가
[ ] 같은 세션에서 spec handoff를 했는가
[ ] 중요 결정을 ADR/CONTEXT에 보존했는가
[ ] TDD acceptance criteria로 변환했는가
[ ] 구현과 리뷰를 별도 Agent/Persona로 분리했는가
```

## 최종 판단

| 항목 | 평가 |
| --- | --- |
| 초기 아이디어 구체화 | 매우 유용 |
| 요구사항 누락 방지 | 유용 |
| 코드베이스 분석 | 단독으로 부족 |
| UI 시각 판단 | prototype 필요 |
| TDD 연결 | 매우 유용 |
| Stateless portability | 매우 유용 |
| 대형 프로젝트 | wayfinder/grill-with-docs와 조합 필요 |
| 즉시 장애 대응 | 부적합 |

`grill-me`를 우리 프로젝트에 적용한다면 기본 정책은 다음이 적절하다.

```yaml
grill_me:
  trigger: user-invoked
  session: fresh
  plan_mode: off
  state: stateless
  output: decisions + unknowns + next_handoff
  next_steps:
    - to-spec
    - ADR
    - TDD acceptance criteria
  stop_conditions:
    - frontier_empty
    - prototype_required
    - scope_too_large
```

## 결론

`grill-me`는 Agent가 사용자를 대신해 설계를 결정하는 기능이 아니라, 사용자가 암묵적으로 갖고 있던 선택을 질문으로 드러내고 책임 있게 결정하도록 돕는 **요구사항 발견 하네스**다.

```text
질문이 많아서 좋은 것이 아니다.
결정되지 않은 가지가 줄어들어서 좋다.
```

우리 환경에서는:

```text
/grill-me
→ 제품·아키텍처·글의 초기 아이디어 정리
→ 결정·미확정·범위 기록
→ /to-spec 또는 ADR
→ TDD
→ Claude/Codex bounded 실행
→ Harness evidence gate
```

순서로 쓰는 것이 가장 효과적이다.

**한 문장 요약:** `grill-me`는 코드를 생성하기 전에 사용자의 모호한 아이디어를 질문 frontier와 적극적인 의사결정으로 압축해, TDD·Harness·구현으로 넘길 수 있는 출발점으로 만드는 Stateless Agent Skill이다.

## 참고 자료

- [`grill-me.md` 원문](https://github.com/mattpocock/skills/blob/main/docs/productivity/grill-me.md?utm_source=chatgpt.com)
- [`mattpocock/skills` 저장소](https://github.com/mattpocock/skills)
- [`grill-me` 설치/스킬 디렉터리](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me)
- [`grill-with-docs`](https://aihero.dev/skills-grill-with-docs)
- [`wayfinder`](https://aihero.dev/skills-wayfinder)
- [`to-spec`](https://aihero.dev/skills-to-spec)
- [`grilling` primitive](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md)
- [기획·Loop Engineering·TDD·Harness](https://myoungsoo7.github.io/2026/08/08/planning-loop-engineering-tdd-harness/)
- [Claude Code와 Codex를 하네스로 사용하기](https://myoungsoo7.github.io/2026/08/09/claude-code-codex-as-harness/)

> `grill-me`는 MIT License로 공개된 `mattpocock/skills` 저장소의 문서를 기준으로 분석했다. 저장소의 스킬 구성과 명령은 변경될 수 있으므로 사용 전 원문과 최신 설치 경로를 확인해야 한다.

<!-- source: https://github.com/mattpocock/skills/blob/main/docs/productivity/grill-me.md -->
