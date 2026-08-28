---
layout: post
title: "jakubkrehel/skills 뜯어보기: 인터페이스 품질을 11개 스킬로 쪼갠 저장소"
date: 2026-08-28 20:08:26 +0900
categories: [ai, agent-skills]
tags: [claude-code, agent-skills, codex, opencode, design-engineering, accessibility]
---

[jakubkrehel/skills](https://github.com/jakubkrehel/skills) 는 "인터페이스를 잘 만들도록 돕는" 에이전트 스킬 모음이다. 타이포그래피·색·레이아웃·접근성·UX 라이팅 같은 디자인 엔지니어링 지식을 에이전트가 읽을 수 있는 형태로 정리해 두었다.

읽어 볼 가치가 있는 이유는 스킬의 *내용* 보다 *구조* 다. 스킬을 11개로 쪼갠 기준, 어떤 스킬이 스스로 뜨고 어떤 스킬이 사람만 부를 수 있는지, 규칙 하나가 정확히 어느 파일에 사는지가 저장소 안에 문서로 못박혀 있다. 스킬을 직접 만들어 본 사람이라면 이 부분이 본문보다 더 쓸모 있다.

이 글은 저장소를 커밋 [`ca48385`](https://github.com/jakubkrehel/skills/tree/ca483852de23d48ab4f4ea71da37dad12bd70a95) (2026-08-28 확인) 기준으로 읽고 정리한 것이다. 아래 수치와 인용은 그 시점의 파일에서 직접 확인한 값이다.

## 무엇이 들어 있나

저장소 최상위는 이렇게 생겼다.

```text
.claude-plugin/
  plugin.json          # Claude Code 플러그인 정의
  marketplace.json     # 같은 저장소가 마켓플레이스 역할
AGENTS.md              # 이 저장소에서 일하는 에이전트를 위한 유일한 지침
CLAUDE.md              # 본문은 @AGENTS.md 한 줄
README.md
opencode.json          # opencode 가 skills/ 를 로드하도록 등록
skills/                # 11개 스킬 디렉터리
```

[`AGENTS.md`](https://github.com/jakubkrehel/skills/blob/main/AGENTS.md) 는 저장소 성격을 이렇게 못박는다. 문서 전용이고 빌드·린트·테스트 도구가 없다. 실제로 CI 워크플로가 없고, 검증은 `claude plugin validate` 뿐이다. [`plugin.json`](https://github.com/jakubkrehel/skills/blob/main/.claude-plugin/plugin.json) 의 이름은 `interfaces`, 라이선스는 MIT, 확인 시점 버전은 `1.6.2` 였다.

## 11개 스킬, 두 가지 모양

`AGENTS.md` 의 **Structure** 절이 스킬을 두 모양으로 나눈다. **도메인 스킬** 은 지식을 담는다. 타이포그래피·색·레이아웃에 대해 무엇이 참인가. **동사 스킬** 은 절차를 담는다. 이 변경을 리뷰해라, 이 변형들을 탐색해라, 이 인터페이스를 설명해라. 그리고 한 문장으로 정리한다. 도메인 스킬 안에 들어앉은 절차는 추출 후보고, 동사 스킬 안에 들어앉은 도메인 규칙은 원래 주인에게 돌려보내야 한다.

그 기준으로 11개가 이렇게 갈린다.

| 스킬 | 모양 | 하는 일 |
| --- | --- | --- |
| [`better-interface`](https://github.com/jakubkrehel/skills/blob/main/skills/better-interface/SKILL.md) | 오케스트레이터 | 6개 도메인 스킬로 라우팅하고 하나의 순위 매긴 판정으로 통합 |
| [`better-accessibility`](https://github.com/jakubkrehel/skills/blob/main/skills/better-accessibility/SKILL.md) | 도메인 | 시맨틱 HTML, 키보드·포커스, 접근 가능한 이름, 폼, 보조기술 |
| [`better-layout`](https://github.com/jakubkrehel/skills/blob/main/skills/better-layout/SKILL.md) | 도메인 | 공간적 그룹핑, 정렬, 간격, 반응형 구조, 논리적 CSS 속성 |
| [`better-writing`](https://github.com/jakubkrehel/skills/blob/main/skills/better-writing/SKILL.md) | 도메인 | 원본 문구, 용어, 보이스, 레이블, 에러·빈 상태 카피 |
| [`better-typography`](https://github.com/jakubkrehel/skills/blob/main/skills/better-typography/SKILL.md) | 도메인 | 텍스트 렌더링, 타입 시스템, 폰트 동작, 줄바꿈·말줄임 메커니즘 |
| [`better-colors`](https://github.com/jakubkrehel/skills/blob/main/skills/better-colors/SKILL.md) | 도메인 | 팔레트 구조와 단계 역할, 토큰 이름, 색 표기, 색역(gamut), 대비 측정 |
| [`better-ui`](https://github.com/jakubkrehel/skills/blob/main/skills/better-ui/SKILL.md) | 도메인 | 선택적 시각 폴리시. 표면, 아이콘, 모션 미학 |
| [`interface-review`](https://github.com/jakubkrehel/skills/blob/main/skills/interface-review/SKILL.md) | 동사 (사용자 호출) | 변경 범위 해석, 영향 반경, 발견 분류, 변경 범위 리포트 포맷 |
| [`variant`](https://github.com/jakubkrehel/skills/blob/main/skills/variant/SKILL.md) | 동사 (사용자 호출) | 한 UI 조각의 진짜로 다른 버전 여러 개를 피커 뒤에 만들어 실제 페이지에서 비교 |
| [`break`](https://github.com/jakubkrehel/skills/blob/main/skills/break/SKILL.md) | 동사 (사용자 호출) | 컴포넌트 하나를 실사용이 만들 수 있는 모든 상태로 렌더해 시각 리포트로 넘김 |
| [`explain-interface`](https://github.com/jakubkrehel/skills/blob/main/skills/explain-interface/SKILL.md) | 동사 (사용자 호출) | URL 이나 스크린샷을 가리키면 그 효과 뒤의 레이어들을 찾아 설명 |

도메인 스킬만 `better-*` 접두사를 쓴다. `interface-review` 가 접두사를 뗀 건 커맨드라인에서 더 잘 읽히기 때문이라고 `AGENTS.md` 가 밝힌다.

## 왜 스스로 뜨는 스킬과 사람만 부르는 스킬을 나눴나

가장 흥미로운 규칙은 [`AGENTS.md` 의 Invocation 절](https://github.com/jakubkrehel/skills/blob/main/AGENTS.md)에 있다. 규칙 자체는 한 줄이다.

> 사용자 호출 스킬은 모델 호출 스킬을 부를 수 있지만, 다른 사용자 호출 스킬에는 절대 닿을 수 없다.

이게 취향이 아니라 *설정을 결정한다* 고 문서가 명시한다. 그래서 `variant`, `break`, `explain-interface`, `interface-review` 네 개만 사용자 호출이다. 이유도 각각 적혀 있다. `variant` 는 던져 버릴 코드를 쓰고 나서 사람만 답할 수 있는 질문을 하므로, 에이전트가 알아서 켜면 아무도 부탁하지 않은 작업물과 아무도 지우지 않는 하네스가 남는다. `break` 도 같은 이유다. 컴포넌트를 건드릴 때마다 자동으로 뜨면 저장소가 테스트 페이지로 뒤덮인다. `explain-interface` 는 URL 을 붙여넣는 게 분석 요청이 아니기 때문이다.

반대로 `better-interface` 는 굳이 모델 호출로 남겼다. 사용자 호출로 만들면 `interface-review` → `better-interface` 로 올라가는 핸드오프가 끊기고, 그러면 `interface-review` 가 심각도·상한·포맷·판정을 전부 다시 적어야 하기 때문이다. 스킬 하나의 호출 방식이 다른 스킬의 중복 분량을 결정한다는 얘기다.

구현은 하네스마다 다른 두 스위치를 *짝으로* 맞추는 방식이다.

- Claude Code: SKILL.md 프론트매터에 `disable-model-invocation: true`. [공식 문서](https://code.claude.com/docs/en/skills)에 있는 필드로, 이 스킬을 모델이 자동으로 부르지 못하게 하고 `/skill-name` 호출만 남긴다.
- Codex: `agents/openai.yaml` 에 `policy.allow_implicit_invocation: false`. [OpenAI 공식 문서](https://developers.openai.com/codex/skills)가 기본값을 `true` 로 두고, `false` 면 프롬프트 기반 암묵 호출을 하지 않는다고 설명한다.

`AGENTS.md` 는 이 둘을 "같은 스위치의 Claude Code 쪽과 Codex 쪽" 이라 부르고 반드시 함께 설정하라고 요구한다. 한쪽만 켜면 하네스마다 동작이 갈린다.

한 가지 덧붙이면, Codex 쪽은 문서와 실제 동작이 어긋난다는 보고가 열려 있다. codex-cli 0.149.0 에서 `allow_implicit_invocation: false` 를 걸면 명시적 `$skill` 호출까지 막힌다는 [이슈](https://github.com/openai/codex/issues/40600)다. 필자가 재현해 보지는 않았으므로 제3자 보고로만 적어 둔다. 사실이라면 Codex 사용자에게는 네 개의 동사 스킬이 사실상 호출 경로를 잃는다.

## 규칙은 정확히 한 곳에만 산다

`AGENTS.md` 의 **Rule ownership** 표가 이 저장소의 뼈대다. 각 스킬이 무엇을 *소유* 하는지 한 줄씩 적어 두고, 도메인이 겹치는 지점은 따로 명시한다.

- `better-accessibility` 는 대비가 필요한지, 그 쌍이 실패인지를 판단한다. 렌더된 쌍을 *측정* 하고 색을 바꾸는 건 `better-colors` 다.
- `better-accessibility` 는 시맨틱 헤딩 구조를, `better-typography` 는 헤딩 레벨이 시각적으로 어떻게 렌더되는지를 소유한다.
- `better-typography` 는 말줄임 메커니즘을, `better-layout` 은 주변 레이아웃에 자리가 있는지를, `better-writing` 은 원본 카피를 소유한다.
- `interface-review` 는 diff 일 때 무엇을 리뷰할지를, `better-interface` 는 그 리뷰가 어떻게 라우팅·순위·통합·보고되는지를 소유한다. 의존은 한 방향이다.

그리고 스킬끼리 참조할 때는 상대 링크가 아니라 **백틱으로 감싼 스킬 이름** 만 쓴다. 이유가 명확하다. 각 스킬 디렉터리는 혼자서도 설치되기 때문이다. `better-typography` 만 설치한 사람의 디스크에는 `better-interface` 가 없다. 그래서 리뷰 포맷이 세 곳에 조금씩 겹치는데, 문서는 그 중복을 "혼자 설치돼도 동작하는 스킬의 대가" 라고 인정하고 넘어간다.

원칙을 가리킬 때 번호가 아니라 굵게 쓴 제목으로 가리키라는 규칙도 있다. 위에 원칙 하나가 삽입되는 순간 번호 참조는 조용히 깨지고, 깨져도 아무것도 실패하지 않기 때문이다.

## 리뷰는 취향이 아니라 증거로 막는다

[`better-interface/SKILL.md`](https://github.com/jakubkrehel/skills/blob/main/skills/better-interface/SKILL.md) 는 "Evidence, not taste" 라는 제목의 보정 절로 시작한다. 스타일 가이드가 뭐라 하든 트리거는 실패이고, 그냥 마음에 안 드는 밀도·라운딩·보이스는 발견이 아니다. 문서화된 관습이 그 관습이 좋다는 증거는 아니며 "스타일 가이드에 있다" 가 발견을 무효화하지 않는다는 문장도 있다. 대신 그럴 때는 *어디에* 보고할지가 바뀐다. 원인이 공유 토큰이나 가이드라인이면 그 출처에 한 번 보고하고 컴포넌트들은 위치로 나열한다.

심각도는 HIGH/MEDIUM/LOW 하나의 척도이고, 그 위에 **에스컬레이션 트리거** 13개가 얹힌다. 도메인 스킬이 증상을 확인하는 순간 무조건 HIGH 가 되는 항목들이다.

- 접근 가능한 이름이 없는 인터랙티브 컨트롤
- 키보드로 닿는데 보이는 포커스 표시가 없는 컨트롤
- 포인터로는 되는데 키보드로는 안 되는 경로
- `prefers-reduced-motion` 을 무시하는 모션이나 자동 재생
- 320px 너비 또는 200% 확대에서 잘리거나 겹치거나 닿을 수 없는 콘텐츠
- 요구 대비를 통과하지 못하는 본문·컨트롤 텍스트
- 색만으로 전달되는 상태나 의미
- 확인·되돌리기·구분되는 처리가 없는 파괴적 동작
- 전체 값에 닿을 방법이 없는 말줄임
- 보이는 단서 없이 스크롤 끝이나 디스클로저 뒤에만 있는 콘텐츠
- 복구 방법을 알려주지 않는 에러
- 의미에 어긋나게 쓰인 시맨틱 색 (파괴적이지 않은 동작에 danger 색조)
- 애니메이션이 실행되지 않으면 색·아이콘·레이블이 아무것도 남지 않는 상태 변화

발견은 15개까지만 보고하는데, 트리거가 상한을 넘치면 트리거부터 먼저 싣고 상한이 몇 개를 잘랐는지 밝히라고 한다. "상한은 리포트를 짧게 만들 수는 있어도, 블로커가 보고되지 않은 이유가 될 수는 없다" 는 문장이 그대로 들어 있다.

수정 제안에도 순서가 있다. 심각도가 *얼마나 나쁜가* 라면 이건 *어떤 수정을 제안할 것인가* 다. 여러 방법이 통할 때 가장 이른 것을 택한다.

1. **삭제한다.** 여백이면 될 구분선, 고빈도 인터랙션의 애니메이션, 네이티브 요소가 이미 제공하는 ARIA 속성, 아무도 import 하지 않는 램프.
2. **플랫폼을 쓴다.** 커스텀 재구현 대신 네이티브 요소·컨트롤·브라우저 기본 포커스 링.
3. **프로젝트에 이미 있는 걸 재사용한다.** 새 값보다 기존 토큰·간격 단계·모션 커브.
4. **값을 고친다.** 잘못된 이징·라운딩·간격·대비 쌍을 소유 스킬이 주는 정확한 값으로.
5. **추가한다.** 새 토큰, 래퍼, 미디어 쿼리, 플랫폼이 줄 수 없는 ARIA 속성.

그리고 한 줄 더. 1번이 가능한데 5번으로 쓴 수정은 그 자체가 발견이다. 삭제를 보고하라고 한다.

## "정확한 값" 이라는 저술 규약

`AGENTS.md` 의 **Authoring conventions** 는 원칙이 규범적이고 구체적이어야 한다고 요구한다. 모호한 조언이 아니라 정확한 CSS 속성과 정확한 값. 예시로 든 것이 스케일 `0.25` → `1`, 블러 `4px` → `0px` 인데, 실제로 [`better-ui/SKILL.md`](https://github.com/jakubkrehel/skills/blob/main/skills/better-ui/SKILL.md) 를 열면 그 값들이 그대로 있다. 아이콘 전환 애니메이션의 스케일·불투명도·블러, 스프링 프리셋 `{ type: "spring", duration: 0.3, bounce: 0 }`, 크로스페이드 이징 `cubic-bezier(0.2, 0, 0, 1)`, 누름 상태 `scale(0.96)` 같은 식이다.

동시에 처방의 강도를 결정의 성격에 맞추라고 단서를 단다. 요구사항은 무조건일 수 있지만, 디자인 휴리스틱은 맥락과 예외 조건을 먼저 밝힌 뒤 정확한 레시피 값을 준다. 그리고 스킬은 대상 프로젝트의 스타일 시스템(Tailwind / 순수 CSS / CSS-in-JS)을 따르라고 지시하지 자기 스택을 강요하지 않는다.

편집 후 돌리는 체크 네 가지도 명문화돼 있다.

- **30단어 넘는 문장 금지.** 코드 스팬은 한 단어로 센다. 평균이 아니라 천장이다. 평균을 낮추면 문장이 툭툭 끊기고, 읽기 힘들게 만드는 건 절 네 개를 끌고 가는 40단어짜리 한 문장이라는 이유다.
- **description 당 트리거 20개 안팎.** 한 갈래를 두 표현으로 쓴 건 한 갈래를 두 번 쓴 것이다.
- **각 규칙은 한 번만 진술.** "명확성을 위해" 경계를 다시 적는 반사 때문에 `better-interface` 에 소유권 문장이 네 벌 생겼던 적이 있다고 자기 사례를 적어 두었다.
- **분량 상한이 아니라 가지치기 패스.** 문장마다 이게 무엇을 바꾸는지 묻고, 지시·사실·숫자로 다시 쓸 수 없는 문장은 자른다. 다른 프로젝트 문서에 그대로 들어가도 말이 되는 문장은 이 프로젝트에 대해 아무 말도 하지 않은 것이다.

표기 규칙도 있다. 곧은 따옴표, 문장형 제목, em 대시 금지, 대신 쓰는 괄호나 문장 중간 콜론도 금지, 옥스퍼드 콤마 금지. 취향처럼 보이지만 목적은 하나다. 여러 사람과 여러 에이전트가 고쳐도 문서가 평균으로 되돌아가지 않게 하는 것.

## 설치 두 가지, 그리고 이름이 달라진다

README 가 두 경로를 준다. 같은 스킬을 설치하지만 **부르는 이름이 다르다.**

```bash
npx skills add jakubkrehel/skills
```

CLI 로 설치하면 스킬이 평범한 이름을 유지한다. 변경 리뷰는 `/interface-review` 로 뜬다. Claude Code·Codex·opencode 등에서 동작한다.

```text
/plugin marketplace add jakubkrehel/skills
/plugin install interfaces@interfaces
```

Claude Code 플러그인으로 설치하면 전부 한 번에 들어오고 제자리에서 업데이트되지만, 스킬이 플러그인 이름 아래로 네임스페이스된다. 그래서 `/interfaces:interface-review`, `/interfaces:variant` 가 된다. 업데이트는 `/plugin update interfaces@interfaces` 후 재시작.

여기 걸려 넘어지기 쉬운 함정이 하나 있다. `AGENTS.md` 는 `skills/` 아래를 바꾸면 *같은 커밋에서* `plugin.json` 의 `version` 을 올리라고 요구한다. 플러그인 사용자가 업데이트 여부를 판단하는 신호는 그 숫자 하나뿐이고, `claude plugin update` 는 그것만 비교하기 때문이다. 버전을 안 올리고 내보낸 변경은 "이미 최신입니다" 라는 답만 받고 영원히 전달되지 않는다.

## 이 구조가 왜 말이 되나

Anthropic 이 [Agent Skills 를 소개한 글](https://www.anthropic.com/news/skills)과 [엔지니어링 블로그](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)가 설명하는 핵심은 **점진적 공개(progressive disclosure)** 다. 프론트매터의 `name` 과 `description` 만 항상 시스템 프롬프트에 올라가 있고, 스킬이 트리거되면 SKILL.md 본문이, 필요할 때만 번들된 참조 파일이 읽힌다. [공식 문서](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)도 같은 3단계를 명시한다.

이 저장소의 규칙 대부분이 그 구조에서 나온다. description 을 본문보다 더 세게 가지치기하라는 것은 그것만 매 턴 로드되기 때문이고, 원칙은 규칙만 진술하고 레시피는 참조 파일로 링크하라는 것은 3단계를 실제로 쓰는 것이다. 원칙이 참조 파일을 짧게 다시 쓰지도, 참조 파일이 원칙을 길게 다시 쓰지도 말라는 요구가 그래서 붙는다.

## 안 하는 것

과대평가를 막기 위해 경계도 적어 둔다.

- 이 저장소는 **인터페이스 품질** 만 다룬다. 정합성·보안·테스트·성능은 범위 밖이다. `better-ui` 조차 "밑에 깔린 인터랙션이 멀쩡해진 다음의 선택적 폴리시" 로 자기 위치를 정의한다.
- **문서 전용이라 자동 검증이 없다.** 빌드·린트·테스트가 없으니 규약(30단어, 트리거 20개)은 사람이나 에이전트가 읽어서 지키는 것이지 CI 가 막아 주지 않는다.
- **리뷰 품질 자체는 이 저장소가 보장하지 않는다.** `better-interface` 가 "검증할 수 있는 것만 검증하라, 돌릴 수 없는 체크는 발견이 아니라 Not verified 다" 라고 요구하지만, 그 요구를 지키는 주체는 에이전트다. 규칙이 좋다는 것과 어떤 모델이 그 규칙을 따라 낸 리포트가 정확하다는 것은 다른 문제다.
- 스타·설치 수는 인기 지표지 품질 지표가 아니다. GitHub API 로 확인한 값은 2026-08-28 20:10 기준 스타 4,538 · 포크 151 이다. README 배지가 가리키는 [skills.sh 페이지](https://skills.sh/jakubkrehel/skills)의 설치 수는 제3자 애그리게이터 집계이고, 저장소에서 이름이 바뀐 이전 스킬들도 함께 세는 것으로 보이므로 여기서는 인용하지 않는다.

## 지난번 글 이후 바뀐 것

[2026-08-09 글](/2026/08/09/agent-interface-skills-comparative-review/)에서 이 저장소를 다룬 적이 있는데, 그때 이후 구조가 꽤 달라졌다. 그 글이 설명한 `quick` / `full` 두 리뷰 모드는 현재 저장소에 없다. 대신 `interface-review` 가 변경 범위 해석을 전담하고 `better-interface` 로 리뷰를 올려 보내는 구조로 갈렸다. `break`, `variant`, `explain-interface` 세 동사 스킬도 그 글에는 등장하지 않는다. 스킬 모음을 인용할 때 커밋을 박아야 하는 이유가 이거다. 한 달이면 목차가 바뀐다.

## 정리

가져갈 만한 것은 세 가지다.

1. **지식과 절차를 다른 파일에 둔다.** 도메인 스킬은 무엇이 참인가, 동사 스킬은 무엇을 하는가. 섞이기 시작하면 같은 규칙이 여러 벌 생긴다.
2. **호출 방식은 취향이 아니라 설계다.** 부작용을 남기는 스킬은 사람만 부르게 하고, 그 결정이 어떤 핸드오프를 끊는지까지 계산한다. 하네스가 둘이면 스위치도 짝으로 맞춘다.
3. **규칙 하나에 주인 하나.** 소유권 표를 문서로 만들어 두면 겹치는 도메인에서 무엇을 어디에 적을지 매번 다시 논쟁하지 않아도 된다.

스킬을 몇 개 넘게 굴려 본 사람이면 세 번째에서 가장 크게 이득을 볼 것이다.

## References

- jakubkrehel/skills, 커밋 `ca483852de23d48ab4f4ea71da37dad12bd70a95` (2026-08-28 확인). <https://github.com/jakubkrehel/skills/tree/ca483852de23d48ab4f4ea71da37dad12bd70a95>
- 같은 저장소, `AGENTS.md`. <https://github.com/jakubkrehel/skills/blob/main/AGENTS.md>
- 같은 저장소, `skills/better-interface/SKILL.md`. <https://github.com/jakubkrehel/skills/blob/main/skills/better-interface/SKILL.md>
- 같은 저장소, `README.md` 및 `.claude-plugin/plugin.json`. <https://github.com/jakubkrehel/skills/blob/main/README.md>
- Anthropic, "Introducing Agent Skills". <https://www.anthropic.com/news/skills>
- Anthropic Engineering, "Equipping agents for the real world with Agent Skills". <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>
- Anthropic Docs, "Agent Skills overview". <https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview>
- Claude Code Docs, "Skills" (`disable-model-invocation` 필드). <https://code.claude.com/docs/en/skills>
- OpenAI Developers, "Agent Skills – Codex" (`agents/openai.yaml`, `policy.allow_implicit_invocation`). <https://developers.openai.com/codex/skills>
- openai/codex issue #40600, `allow_implicit_invocation: false` 관련 제3자 보고. <https://github.com/openai/codex/issues/40600>
- 스타·포크 수는 GitHub REST API `GET /repos/jakubkrehel/skills` 응답 (2026-08-28 확인).
