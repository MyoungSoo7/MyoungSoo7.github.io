---
layout: post
title: "Agent Interface Skills 비교 분석: better-interface를 우리 프로젝트에 어떻게 쓸 것인가"
date: 2026-08-09 12:30:00 +0900
categories: [AI, Design, Engineering]
tags: [Agent Skills, UI Review, Accessibility, Claude Code, Codex, Flask, RAG]
---

# Agent Interface Skills 비교 분석

## 결론

[jakubkrehel/skills](https://github.com/jakubkrehel/skills)는 Claude·Codex 같은 Agent가 화면을 단순히 “예쁘게” 만드는 수준을 넘어, 접근성·레이아웃·문구·타이포그래피·색상·상호작용을 하나의 검토 프로세스로 다루게 하는 UI 품질 스킬 모음이다.

우리 프로젝트에는 **web01의 고객 상담봇·상담사 보조·수리기사·보이스봇 UI를 만들고 검토할 때 선택형 디자인 게이트로 도입하는 것이 유용**하다. 반면 Settlement 원장·Kafka·정산·K3s 운영 분석을 대체하는 도구는 아니다.

```text
적합:
  web01 AI 상담 UI
  수리기사 모바일 UI
  보이스봇 demo
  Settlement Admin 화면

부적합:
  금융 원장 correctness
  Kafka 멱등성
  DB 대사
  Kubernetes 운영
  보안·성능 전체 리뷰
```

## 대상 저장소의 구성

공개 저장소에는 다음 스킬이 있다.

```text
better-interface
interface-review
better-ui
better-typography
better-colors
better-accessibility
better-layout
better-writing
```

두 개의 진입점이 핵심이다.

```text
better-interface
= 화면·플로우·기능 전체를 종합 검토

interface-review
= uncommitted 변경·branch·PR의 UI 변경 범위 검토
```

`better-interface`는 다음 여섯 영역을 조정한다.

```text
1. Accessibility
2. Layout
3. Writing
4. Typography
5. Colors
6. UI polish·motion
```

중요한 설계는 각 세부 스킬이 자기 분야의 규칙을 소유하고, `better-interface`는 오케스트레이션과 최종 통합만 담당한다는 점이다. 즉 여섯 개의 독립적인 체크리스트를 붙이는 방식보다 중복 finding을 줄이고 우선순위를 정할 수 있다.

## 설치 방법

### Claude Code plugin

저장소 README가 안내하는 방식은 다음과 같다.

```text
/plugin marketplace add jakubkrehel/skills
/plugin install interfaces@interfaces
```

이 방식은 Claude Code에서 저장소 전체를 plugin으로 관리하고 업데이트하기 좋다.

### skills CLI

Claude·Codex·기타 Agent에 공통으로 설치하려면:

```bash
npx skills add jakubkrehel/skills
```

전체 스킬을 명시하려면:

```bash
npx skills add jakubkrehel/skills --skill '*'
```

하지만 운영 환경에는 처음부터 전역 설치하기보다 다음 순서가 안전하다.

```text
1. 저장소 clone
2. SKILL.md와 라이선스 검토
3. 임시 worktree에서 실행
4. 리뷰 출력 품질 확인
5. 프로젝트별 필요 스킬만 설치
6. central skill distribution에 반영
```

## 호출 방법

### 전체 화면·플로우 리뷰

Claude Code plugin으로 설치한 경우:

```text
/interfaces:better-interface
/interfaces:better-interface quick
/interfaces:better-interface full customer chat
/interfaces:better-interface full repair mobile flow
```

skills CLI로 설치한 경우:

```text
/better-interface
/better-interface quick
/better-interface full customer chat
/better-interface full voice demo
```

Codex에서는:

```text
$better-interface
$better-interface quick
$better-interface full customer chat
```

### 변경·PR 리뷰

```text
/interface-review
/interface-review quick
/interface-review quick pr 482
```

기본적으로 변경 범위를 자동으로 해석한다.

```text
branch가 base보다 앞서 있는가?
uncommitted 변경이 있는가?
변경된 파일이 어떤 화면에 영향을 주는가?
삭제된 코드가 기존 접근성·focus·문구를 제거하지 않았는가?
```

## quick와 full 비교

| 모드 | 범위 | 결과 |
| --- | --- | --- |
| `quick` | 주 경로와 실제 도달 상태 | HIGH·MEDIUM 중심, 최대 5건 |
| `full` | 전체 범위·empty/loading/error/narrow-width 포함 | LOW까지 포함, 최대 15건 |

`quick`은 PR 직전 빠른 게이트에 적합하다.

```text
/interface-review quick
```

`full`은 신규 화면·제품 플로우·핵심 상담 화면에 적합하다.

```text
/better-interface full customer chat
```

리뷰 범위를 credible하게 확인할 수 없으면 대상 전체를 검토했다고 주장하지 않고, 사용자 요청의 중심 플로우 하나로 범위를 줄여야 한다는 점도 유용하다.

## 리뷰 프로세스

### 1. Scope와 mode 해석

```text
quick/full
+ 화면·플로우·branch·PR
```

정확한 scope를 먼저 선언한다.

```text
scope: 고객 상담 질문→응답→citation→handoff
mode: full
excluded: 관리자 설정 화면
```

### 2. Recon

다음 정보를 먼저 확인한다.

```text
framework
styling system
component library
design tokens
supported viewport
preview/test command
AGENTS.md
CLAUDE.md
CONTRIBUTING.md
```

우리 web01은 현재 Flask templates와 static CSS 중심이므로, React/Tailwind를 새로 도입하라는 식으로 고치지 않고 기존 프로젝트 idiom 안에서 finding을 작성해야 한다.

### 3. 여섯 영역 검토

```text
Accessibility
→ Layout
→ Writing
→ Typography
→ Colors
→ UI
```

기초 접근성과 정보 구조를 먼저 보고 시각적 polish를 나중에 보는 순서다.

### 4. Evidence 수집

모든 finding은 다음을 가져야 한다.

```text
path/to/file:line
또는 정확한 화면·component
현재 구현
문제의 사용자 영향
권장 변경
검증 방법
```

시각적 주장은 source만 읽고 확정하지 않는다. 렌더링 확인이 불가능하면 `Not verified`로 표시해야 한다.

### 5. Findings 통합

동일한 root cause가 여러 곳에 나타나면 하나의 finding으로 묶는다.

```text
나쁜 출력:
button 12개에 같은 문제를 12행으로 나열

좋은 출력:
공통 button token/컴포넌트의 한 finding
+ 영향 위치 목록
```

### 6. Verdict

```text
Block
  HIGH finding이 남아 있음

Needs changes
  MEDIUM/LOW finding만 남음

Approve
  actionable finding 없음 + 검증된 coverage
```

## 접근성 리뷰가 특히 유용한 이유

`better-accessibility`는 단순히 ARIA를 추가하라고 하지 않는다.

핵심 원칙:

```text
native element 우선
visible focus ring
키보드만으로 전체 flow 수행
modal focus trap·restore
입력 label·autocomplete
오류 aria-invalid·aria-describedby
icon-only control accessible name
색상만으로 상태 전달 금지
prefers-reduced-motion
320px reflow·200% zoom
```

web01 고객 상담봇에 적용하면 다음을 검토할 수 있다.

```text
질문 입력창에 label이 있는가?
전송 버튼이 키보드로 접근 가능한가?
답변 loading 상태가 screen reader에 전달되는가?
근거 없음·handoff가 색상만으로 구분되지 않는가?
오류 발생 시 첫 번째 잘못된 입력으로 focus가 이동하는가?
```

상담사 보조 UI에서는 특히 다음이 중요하다.

```text
답변 후보 승인 버튼의 이름
승인과 전송의 구분
고객에게 전송 전 confirmation
AI 생성 답변과 상담사 승인 상태
```

## Layout·Typography·Color·Writing·UI의 역할

### Layout

```text
상담 transcript
→ 요약
→ 답변 후보
→ citation
→ 승인
```

과정의 순서가 시각적 순서와 DOM 순서에 일치해야 한다. 모바일 수리기사 화면에서는 안전 경고가 작업 버튼 아래에 묻히면 안 된다.

### Typography

```text
고객 메시지
오류코드
수리 단계 번호
가격·금액
신뢰도·상태
```

을 같은 시각적 우선순위로 놓지 않는다. 금액·오류코드·상태는 읽기 쉬운 숫자와 명확한 label이 필요하다.

### Colors

```text
답변 완료
handoff 필요
위험 작업
실패
대기
```

를 색상 하나로만 표시하면 안 된다. 아이콘·텍스트·상태 label을 함께 사용하고 실제 foreground/background pair를 측정해야 한다.

### Writing

AI 상담 UI의 문구는 모델 출력의 문제가 아니라 제품 계약의 문제다.

```text
나쁜 문구:
처리 실패

좋은 문구:
답변을 만들 근거가 부족합니다. 상담원에게 연결할까요?
```

상담사 승인 UI도:

```text
답변 생성
답변 검토
고객에게 전송
```

을 분리해야 자동 생성과 실제 고객 전송을 혼동하지 않는다.

### UI polish

shadow·radius·animation은 기능·상태 전달을 방해하지 않는 범위에서 다룬다.

```text
loading
→ skeleton 또는 명확한 progress

handoff
→ 상태 전환을 쉽게 인지

위험 경고
→ 장식보다 정보 우선
```

## 우리 프로젝트별 유용성 비교

| 대상 | 유용성 | 이유 | 적용 범위 |
| --- | --- | --- | --- |
| web01 고객 상담 UI | 매우 높음 | citation·handoff·입력·오류 flow | full review |
| 상담사 보조 UI | 매우 높음 | 승인·전송·transcript·문구 | full + interface-review |
| 수리기사 모바일 UI | 높음 | 안전 경고·narrow width·touch target | full mobile review |
| 보이스봇 demo | 높음 | upload·STT·TTS·loading/error | flow review |
| GitHub Blog | 중간 | typography·writing·layout | 선택적 적용 |
| Settlement Admin UI | 중간~높음 | 대사·DLT·payout 화면 | 변경 시 적용 |
| Settlement backend | 낮음 | 금융 correctness 대상 아님 | 미적용 |
| K3s/homelab | 낮음 | 운영·DNS·RCA 대상 아님 | 미적용 |
| 봇1~4 기본 skill | 낮음 | UI 작업 외 context 낭비 | 선택형 로드 |

## 기존 도구와 비교

### 기존 Ouroboros/LION과의 관계

```text
Ouroboros
= PR·코드·품질·프로젝트 게이트

LION
= 15개 CS 관점의 시스템 종합 분석

better-interface
= 사용자 인터페이스 품질 검토
```

세 도구를 하나로 합치지 않는다.

```text
UI 변경 PR
→ interface-review
→ Ouroboros/code review
→ tests/CI
→ 필요 시 LION 종합
```

### 일반적인 코드 리뷰와의 차이

일반 코드 리뷰는 다음을 주로 본다.

```text
correctness
security
performance
maintainability
test coverage
```

디자인 스킬은 다음을 본다.

```text
사용자가 실제로 이해하고 조작할 수 있는가?
키보드·screen reader가 flow를 완료하는가?
빈 상태·실패 상태가 존재하는가?
모바일·zoom에서 정보가 사라지지 않는가?
```

둘 중 하나만 있으면 불완전하다.

### 수동 디자인 리뷰와의 차이

수동 리뷰는 경험이 풍부한 디자이너의 장점이 있지만:

```text
finding format이 사람마다 다름
반복 검토 기준이 흔들림
Before/After가 불명확
변경과 기존 문제 구분이 어려움
```

이 저장소는 스킬·severity·cap·verdict·verification 형식을 고정해 반복성을 높인다. 다만 Agent 출력이 자동으로 정확하다는 의미는 아니며, 렌더링과 실제 키보드 검증이 필요하다.

## web01에 도입하는 방법

### 1단계: 고객 상담 화면을 첫 대상 지정

```text
scope:
고객 질문 입력
→ 검색/RAG 처리
→ 답변
→ citation
→ handoff
```

### 2단계: read-only review

```text
/better-interface full customer chat
```

리뷰 결과는 코드 수정 없이 다음 파일에 보존하는 방식이 좋다.

```text
docs/INTERFACE_REVIEW_CUSTOMER_CHAT.md
```

### 3단계: 변경 PR review

```text
/interface-review quick
```

현재 branch의 변경만 대상으로 하고, 기존 web01 전체의 legacy UI를 무제한 감사하지 않는다.

### 4단계: 검증

```text
Flask test client
browser preview
keyboard traversal
320px viewport
200% zoom
accessible name inspection
```

실제 브라우저를 열 수 없으면 다음처럼 기록한다.

```text
source review: verified
runtime rendering: Not verified
keyboard behavior: Not verified
```

### 5단계: 구현은 별도 단계

```text
review findings
→ 사용자 승인
→ isolated worktree 구현
→ 테스트
→ interface-review 재실행
→ Ouroboros/CI
```

리뷰 스킬의 기본 동작은 read-only로 유지한다.

## 추천 역할 배치

```text
봇1:
  UI 변경 없음이면 미적용

봇2:
  요구사항·문구·flow review

봇3:
  실제 frontend/template 구현
  interface-review quick

봇4:
  접근성·모바일·회귀 검증

Hermes:
  결과 통합·승인·Evidence 관리
```

하지만 현재 봇1~4는 Settlement·Lemuel-XR 작업도 수행하므로, 모든 세션에 이 스킬을 자동으로 주입하면 context가 불필요하게 커진다. **UI 작업 요청이 들어온 세션에서만 호출**하는 것이 맞다.

## 제한과 위험

### 디자인 스킬이 금융 보안을 검토하지 않음

고객 상담 UI에서 접근성 문제가 없더라도:

```text
PII 노출
JWT 보안
prompt injection
citation 조작
상담사 권한 우회
```

가 안전하다는 의미는 아니다.

### 전역 plugin으로 인한 context 증가

모든 UI 스킬을 모든 Agent에 상시 로드하면:

```text
context 비용 증가
Persona 충돌
backend 작업에 불필요한 지시
```

가 발생할 수 있다.

### Visual 검증의 한계

소스만 보고 spacing·contrast·overlap을 확정하면 안 된다. 브라우저·스크린샷·실제 viewport 검증이 필요하다.

### Finding cap의 한계

`quick`의 최대 5건, `full`의 최대 15건은 우선순위 도구이지 전체 결함이 없다는 증명이 아니다.

## 권장 도입 정책

```yaml
interface_skills:
  source: https://github.com/jakubkrehel/skills
  default: disabled
  enabled_for:
    - web01-ai-ui
    - repair-mobile-ui
    - voice-demo-ui
    - settlement-admin-ui
  modes:
    pre-implementation: better-interface full
    pre-merge: interface-review quick
    release-candidate: interface-review full
  mutation: forbidden_during_review
  required_evidence:
    - scope
    - coverage
    - findings
    - verification
    - verdict
```

이 정책은 설치 여부와 상관없이 우리 운영 원칙을 명확히 한다.

## 최종 판단

```text
도입 여부:
도입 가치 있음

도입 대상:
web01 AI UI 우선

도입 방식:
선택형 skill, read-only review

기존 도구와 관계:
Ouroboros/LION을 대체하지 않고 보완

첫 실험:
고객 상담 chat flow

금지:
Settlement backend·K3s·금융 원장 분석에 사용
```

이 저장소의 가장 큰 가치는 CSS 기법 자체가 아니다.

```text
화면 전체를 하나의 사용자 경험으로 보고
각 분야의 규칙을 분리한 뒤
근거·심각도·검증·최종 판정을 통합하는 운영 방식
```

이다.

**한 문장 요약:** `jakubkrehel/skills`는 우리 프로젝트 전체를 위한 만능 Agent 스킬이 아니라, web01의 상담·수리·보이스 UI에 `better-interface`와 `interface-review`를 선택적으로 추가하는 반복 가능한 디자인 품질 게이트로 사용할 때 가장 큰 가치를 가진다.

## 참고 링크

### 원본 디자인 스킬 저장소

- [jakubkrehel/skills](https://github.com/jakubkrehel/skills)
- [better-interface](https://github.com/jakubkrehel/skills/tree/main/skills/better-interface)
- [interface-review](https://github.com/jakubkrehel/skills/tree/main/skills/interface-review)
- [better-accessibility](https://github.com/jakubkrehel/skills/tree/main/skills/better-accessibility)
- [better-layout](https://github.com/jakubkrehel/skills/tree/main/skills/better-layout)
- [better-writing](https://github.com/jakubkrehel/skills/tree/main/skills/better-writing)
- [better-typography](https://github.com/jakubkrehel/skills/tree/main/skills/better-typography)
- [better-colors](https://github.com/jakubkrehel/skills/tree/main/skills/better-colors)
- [better-ui](https://github.com/jakubkrehel/skills/tree/main/skills/better-ui)
- [skills.sh 설치 페이지](https://skills.sh/jakubkrehel/skills)

### 우리 프로젝트 참고

- [web01 RAG·AI 포트폴리오 PR](https://github.com/MyoungSoo7/web01/pull/1)
- [Claude·Codex Identity와 Persona 분리](https://myoungsoo7.github.io/2026/08/09/claude-codex-identity-persona-session/)
- [Linux 오픈소스 MCP 분석](https://myoungsoo7.github.io/2026/08/09/linux-open-source-mcp-analysis-guide/)
- [기획·Loop Engineering·TDD·Harness](https://myoungsoo7.github.io/2026/08/08/planning-loop-engineering-tdd-harness/)

> 원본 저장소는 MIT License로 공개되어 있으며, 본 글은 저장소 README와 각 `SKILL.md`를 읽고 우리 web01·Settlement·Hermes 운영 구조에 맞춰 비교분석한 것이다. 이 저장소의 도입이 실제 UI 품질을 보장하는 것은 아니며, 렌더링·키보드·스크린리더·브라우저 검증이 별도로 필요하다.
