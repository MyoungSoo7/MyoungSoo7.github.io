---
layout: post
title: "깃헙 코파일럿 잘 쓰는 법 — 도구 고르기·지시문·클라우드 에이전트·리뷰·과금"
date: 2026-09-29 20:10:14 +0900
categories: [ai]
tags: [github-copilot, copilot-cloud-agent, code-review, custom-instructions, ai-coding]
---

GitHub Copilot 은 이제 자동완성 하나가 아니다. 인라인 제안, IDE 채팅(에이전트 모드 포함), GitHub 위에서 혼자 브랜치를 파고 PR 을 올리는 **클라우드 에이전트**, PR **코드 리뷰**, CLI 가 한 구독에 묶여 있다. 그리고 2026-06-01 부터 개인 요금제의 과금 단위가 "프리미엄 요청 횟수" 에서 **토큰 기반 AI 크레딧** 으로 바뀌었다[^billing][^legacy].

잘 쓰는 법은 결국 세 가지로 모인다. **어느 기능에 어떤 일을 맡기나**, **저장소가 코파일럿에게 무엇을 알려주나**, **얼마가 어디서 나가나.** 이 글은 GitHub 공식 문서만 근거로 이 셋을 정리한다. 필자 의견은 **(필자 제안)** 으로 따로 표시했다.

## 1. 일에 맞는 도구 고르기

공식 모범 사례 문서는 인라인 제안과 채팅의 쓰임을 이렇게 나눈다[^bp].

| 도구 | 잘 맞는 일 |
| --- | --- |
| 인라인 제안 | 쓰는 중인 코드·변수명·함수 완성, 반복 코드, 주석에서 코드 생성, TDD 용 테스트 |
| 채팅 | 코드에 대한 질문, 큰 코드 덩어리 생성 후 반복 수정, 키워드·스킬로 정해진 작업, 페르소나 지정(예: 품질 중시 시니어 개발자로서 리뷰) |

여기에 에이전트 계열 둘이 더 있다. 둘은 **일하는 장소**가 다르다[^about-ca].

- **IDE 에이전트 모드** — 로컬 개발 환경에서 직접 자율 편집. 동기적으로 옆에서 본다.
- **클라우드 에이전트** — GitHub Actions 위의 일회용 환경에서 조사·계획·브랜치 수정을 하고, 원하면 PR 을 연다. 비동기로 맡겨 둔다.

문서가 꼽은 코파일럿의 강점은 테스트·반복 코드, 디버깅·문법 수정, 코드 설명·주석, 정규식 생성이다. 동시에 "당신의 전문성을 대체하도록 설계되지 않았다" 고 적었다[^bp].

**(필자 제안)** 선택 기준은 한 줄이다. _결과를 한 화면 안에서 바로 판정할 수 있으면 인라인·채팅, 테스트를 돌려 봐야 판정되면 에이전트._

## 2. 프롬프트와 컨텍스트

공식 권고는 네 가지다[^bp].

- 복잡한 작업은 **쪼갠다**
- 요구사항을 **구체적으로** 쓴다
- 입력·출력·구현 **예시** 를 준다
- 좋은 코딩 관행을 따른다 (코파일럿은 주변 코드를 보고 따라 한다)

컨텍스트 관리에 대한 지시가 특히 실용적이다[^bp].

- IDE 에서는 **관련 파일을 열고, 무관한 파일은 닫는다.**
- 채팅에서 더 이상 도움이 안 되는 요청은 **대화에서 지운다.** 대화 전체가 무관해졌으면 **새 대화** 를 연다.
- 원하는 답이 안 나오면 프롬프트를 다시 쓰거나 더 작게 나눈다.
- 인라인 제안은 여러 개가 나올 수 있으니 단축키로 넘겨 보고 **가장 나은 것** 을 고른다.

## 3. 저장소가 먼저 말하게 하기 — 커스텀 지시문

매번 프롬프트에 "우리는 `make test` 로 테스트한다" 를 적는 대신 저장소에 적어 둔다. 지원되는 파일은 다음과 같다[^instr].

| 파일 | 범위 |
| --- | --- |
| `.github/copilot-instructions.md` | 저장소 전체. 채팅·클라우드 에이전트·코드 리뷰가 모두 읽는다 |
| `.github/instructions/**/NAME.instructions.md` | front matter 의 `applyTo` glob 에 맞는 경로만 |
| `AGENTS.md` (어디든) | 에이전트용. 디렉터리 트리에서 **가장 가까운 것** 이 우선 |
| 루트의 `CLAUDE.md` 또는 `GEMINI.md` | `AGENTS.md` 대신 쓸 수 있는 단일 파일 |

경로별 지시문 예:

```markdown
---
applyTo: "**/*.ts,**/*.tsx"
excludeAgent: "code-review"
---
컴포넌트는 함수형으로 쓰고, 테스트는 같은 폴더의 *.test.tsx 에 둔다.
```

`excludeAgent` 에 `"code-review"` 나 `"cloud-agent"` 를 넣으면 한쪽에서만 쓰이게 막을 수 있다. 단, GitHub.com 에서 경로별 지시문은 현재 **클라우드 에이전트와 코드 리뷰만** 지원한다[^instr].

우선순위도 알아 둘 만하다. 개인 지시문이 가장 높고, 그다음 저장소, 그다음 조직 순이다. 하지만 관련된 지시문은 **전부** 모델에 전달되므로 서로 모순되지 않게 쓰라고 한다[^instr]. 지시문이 실제로 쓰였는지는 채팅 응답 상단의 참조 목록에 `.github/copilot-instructions.md` 가 있는지로 확인한다[^instr].

무엇을 적을지는 GitHub 이 공개한 **자동 생성 프롬프트** 가 좋은 체크리스트다[^instr]. 핵심 요구만 추리면 이렇다.

- **2쪽 이내**, 특정 작업에 한정되지 않을 것
- 부트스트랩·빌드·테스트·실행·린트 명령을 **실제로 돌려 본 뒤** 순서와 버전까지 적을 것
- 선택처럼 보이지만 실제로는 필요한 환경 설정 단계를 적을 것
- CI 에서 도는 검사를 적어, 에이전트가 **스스로 재현** 할 수 있게 할 것
- "항상 빌드 전에 `npm install` 을 먼저" 처럼 **항상** 을 써서 강제할 것

목표도 명시돼 있다. CI 실패로 PR 이 거절될 가능성을 줄이고, grep·find 로 헤매는 탐색을 줄이는 것[^instr].

**(필자 제안)** 이미 `CLAUDE.md` 나 `AGENTS.md` 를 쓰고 있다면 코파일럿용 파일을 새로 만들기 전에 그걸 공유하는 편이 낫다. 같은 내용이 파일 세 개로 갈라지면 한 곳만 고쳐지고 나머지가 거짓이 된다.

## 4. 클라우드 에이전트 — 이슈가 곧 프롬프트다

### 맡길 일과 맡기지 말 일

공식 문서의 표현 그대로, **이슈를 코파일럿에게 할당하는 것은 그 이슈를 프롬프트로 주는 것** 이다[^ca-bp]. 좋은 이슈는 세 가지를 갖춘다.

1. 풀 문제에 대한 명확한 설명
2. **완결된 수락 기준** (예: 단위 테스트가 있어야 하나?)
3. 바꿔야 할 파일에 대한 방향

처음엔 버그 수정, UI 변경, 테스트 커버리지, 문서, 접근성, 기술 부채 같은 단순한 일부터 맡기라고 한다. 사람이 직접 하라고 명시한 일은 다음과 같다[^ca-bp].

- **복잡·광범위** — 저장소를 넘나드는 리팩터링, 레거시 의존성 이해, 깊은 도메인 지식, 많은 비즈니스 로직
- **민감·핵심** — 운영 장애, 보안·개인정보·인증, 인시던트 대응
- **모호함** — 요구사항이 불분명하거나 열린 과제
- **학습 목적** — 개발자가 직접 이해하려는 과제

### PR 을 바로 열지 말고 조사·계획부터

클라우드 에이전트는 PR 을 곧장 열지 않고, 저장소를 조사하고 구현 계획을 세우고 브랜치에서 반복 수정한 뒤 **사람이 PR 여부를 결정** 하게 할 수 있다[^ca-bp][^about-ca]. 코드가 쓰이기 전에 접근법에 합의하는 단계다.

### 리뷰 코멘트는 묶어서

PR 에 `@copilot` 을 멘션하면 코파일럿이 그 브랜치에 커밋을 올린다. 코파일럿은 코멘트가 **제출되는 즉시** 보기 시작한다. 그래서 코멘트가 여러 개면 "Add single comment" 대신 **"Start a review" 로 묶어 한 번에 제출** 하라고 권한다[^ca-bp]. 과금 구조상으로도 이게 맞다 (6절).

### 환경을 결정적으로 — `copilot-setup-steps.yml`

에이전트는 의존성을 시행착오로 설치할 수 있지만, 문서는 이게 **느리고 불안정** 하며 비공개 의존성이면 아예 불가능할 수 있다고 적었다[^env]. 해법은 `.github/workflows/copilot-setup-steps.yml` 이다.

```yaml
name: "Copilot Setup Steps"
on:
  workflow_dispatch:
  push:
    paths: [.github/workflows/copilot-setup-steps.yml]
jobs:
  copilot-setup-steps:        # 잡 이름이 정확히 이것이어야 인식된다
    runs-on: ubuntu-latest
    permissions:
      contents: read          # 필요한 최소 권한
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v7
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
```

함정이 셋 있다[^env].

- **기본 브랜치에 있어야만** 동작한다.
- 잡에서 바꿀 수 있는 건 `steps`·`permissions`·`runs-on`·`services`·`snapshot`·`timeout-minutes`(최대 59)뿐이다. 나머지는 무시된다.
- 셋업 단계 하나가 실패하면 남은 단계를 **건너뛰고 그 상태로 작업을 시작** 한다. 즉 셋업이 깨져도 에이전트는 멈추지 않는다. 세션 로그를 봐야 안다.

코드 리뷰도 기본적으로 이 파일을 재사용하고, 따로 쓰려면 `copilot-code-review.yml` 을 둔다[^env].

## 5. 안전장치 — 이미 있는 것과 내가 할 것

공식 문서가 밝힌 내장 방어는 다음과 같다[^risks].

| 위험 | 내장 방어 |
| --- | --- |
| 취약한 코드 | CodeQL, 새 의존성의 Advisory DB 대조(악성·High/Critical), 시크릿 스캐닝, 코파일럿 코드 리뷰로 2차 의견 |
| 저장소에 push | 쓰기 권한자만 트리거, **단일 브랜치**(`copilot/…` 또는 해당 PR 브랜치)만 push, 브랜치 보호 적용 |
| 스스로 병합 | Ready for review 전환·승인·병합 **불가**. 요청한 사람도 그 PR 을 승인할 수 없음 |
| 워크플로 실행 | 기본값: 쓰기 권한자가 **Approve and run workflows** 를 눌러야 실행 |
| 정보 유출 | 인터넷 접근을 **방화벽** 으로 제한 |
| 프롬프트 주입 | 숨은 문자 필터링. 예: 이슈의 HTML 주석은 전달되지 않음 |
| 추적성 | 커밋 작성자=Copilot, 공동 작성자=요청자, 서명(Verified), 커밋 메시지에 세션 로그 링크 |

**(필자 제안)** 사람이 할 일은 둘이다.

1. **"Approve and run workflows" 를 기계적으로 누르지 않는다.** 이 버튼이 에이전트가 쓴 코드가 CI 시크릿이 있는 환경에서 처음 실행되는 지점이다. diff 에 `.github/workflows/` 변경이 있으면 특히 그렇다.
2. **방화벽을 끄지 말고 필요한 호스트만 연다.** 셋업이 외부 레지스트리를 못 받아서 실패하면 끄고 싶어진다. 하지만 이 방화벽은 유출 방어의 핵심 장치다.

## 6. 과금 — 무엇이 크레딧을 먹나

### 2026-06-01 이후 (개인 요금제)

과금 단위는 **AI 크레딧** 이다(1 크레딧 = 0.01달러). 사용한 모델과 입력·출력·캐시 토큰 수로 계산된다[^billing].

| 요금제 | 월 가격 | 기본 | 유동(flex) | 합계 |
| --- | --- | --- | --- | --- |
| Pro | $10 | 1,000 | 500 | 1,500 |
| Pro+ | $39 | 3,900 | 3,100 | 7,000 |
| Max | $100 | 10,000 | 10,000 | 20,000 |

- **코드 완성과 다음 편집 제안은 크레딧을 쓰지 않는다.** 유료 요금제에서 무제한이다[^billing].
- 채팅, CLI, 클라우드 에이전트, Spaces, Spark, 서드파티 코딩 에이전트는 크레딧을 쓴다[^billing].
- 유동분은 "AI 경제 변화에 맞춰 조정되도록 설계된" **가변** 부분이다. 합계가 고정이라고 가정하지 않는다[^billing].
- 채팅·CLI·클라우드 에이전트에서 **자동 모델 선택** 을 쓰면 모델 비용 10% 할인[^billing].

코드 리뷰는 한 번에 대략 다음 정도를 쓴다고 GitHub 이 추정한다. 문서에 적힌 추정 범위일 뿐이며 모델에 따라 바뀔 수 있다고 명시돼 있다[^cr].

- Lite 노력: 0.05~1달러어치
- Balanced 노력: 0.25~5달러어치

PR 이 크고 지시문이 길수록 늘어나고, **Actions 분은 별도** 다.

### 연간 요금제로 옛 과금에 남은 경우

2026-06-01 이후에도 옛 방식에 남은 Pro/Pro+ 연간 가입자는 여전히 **프리미엄 요청** 으로 센다. 이때 비용 구조가 꽤 다르다[^legacy].

- 코드 리뷰 1회 = 프리미엄 요청 **13개** (배수 13)
- 클라우드 에이전트 = **세션당 1개** × 모델 배수. 실행 중 조향 코멘트는 코멘트마다 1개씩 추가
- 에이전트가 스스로 하는 도구 호출은 세지 않는다. 사람이 보낸 프롬프트만 센다

### 돈이 새는 곳

**(필자 제안)** 문서의 사실에서 곧바로 나오는 절약법이다.

- **자동 리뷰를 "매 push 마다" 로 켜지 않는다.** 기본값은 PR 을 열 때 한 번이다. push 마다 리뷰하는 설정을 켜면 커밋 수만큼 리뷰 비용이 곱해진다[^cr].
- **중요한 PR 만 Balanced 로 돌린다.** 문서도 Balanced 는 보안 민감 코드·다중 서비스 PR 용이고, 일상 변경은 Lite 를 쓰라고 한다[^cr].
- **리뷰 코멘트는 묶어서 제출한다** (4절). 옛 과금에서는 코멘트 하나하나가 요청이다.
- **지시문을 짧게 유지한다.** 리뷰 비용은 지시문 길이에 따라 늘어난다[^cr]. 2쪽 상한은 품질 때문만이 아니다.
- **Actions 분도 같이 본다.** 클라우드 에이전트와 리뷰의 에이전트 기능은 GitHub Actions 위에서 돈다[^about-ca][^cr]. 코파일럿 크레딧이 남아 있어도 계정의 Actions 할당량이 먼저 바닥날 수 있다.

## 7. 코파일럿의 결과물을 검증하기

마지막은 공식 문서가 가장 분명하게 말하는 부분이다[^bp].

- 쓰기 전에 **이해한다.** 모르겠으면 채팅에게 설명을 시킨다.
- 기능·보안뿐 아니라 **가독성·유지보수성** 까지 본다.
- 린트, 코드 스캐닝, IP 스캐닝 같은 **자동 검사** 를 한 겹 더 둔다.
- 공개 코드와 비슷한 제안을 원치 않으면 **공개 코드 일치 제안을 끈다.**

**(필자 제안)** 코파일럿 리뷰의 "승인 가능" 판정은 참고로만 본다. 문서도 기본적으로 코파일럿 리뷰는 필수 승인 수에 포함되지 않는다고 적었다(승인 기능은 공개 프리뷰)[^cr]. 사람 리뷰어가 AI 리뷰를 읽고 "봤다" 로 갈음하는 순간, 두 겹이던 방어가 한 겹이 된다.

## 요약 체크리스트

| 할 일 | 한 줄 |
| --- | --- |
| 도구 고르기 | 한 화면에서 판정 가능하면 인라인·채팅, 테스트가 필요하면 에이전트 |
| 컨텍스트 | 무관한 파일 닫기, 무관한 대화는 새로 열기 |
| 지시문 | `copilot-instructions.md` 2쪽 이내, 실행해 본 빌드·테스트 명령 |
| 이슈 | 문제 + 수락 기준 + 파일 방향. 민감·모호한 일은 맡기지 않기 |
| 환경 | `copilot-setup-steps.yml` 을 기본 브랜치에. 실패해도 조용히 진행되니 로그 확인 |
| 안전 | 워크플로 승인 버튼은 diff 를 본 뒤에. 방화벽은 끄지 말고 허용 목록으로 |
| 비용 | 자동 리뷰는 PR 당 1회, Balanced 는 선별, 코멘트는 묶어서, Actions 분도 보기 |

## 한계

- **효과를 잰 중립 연구를 인용하지 않았다.** 이 글의 권고는 GitHub 공식 문서의 권고와 필자의 추론이다. "지시문을 넣으면 PR 병합률이 X% 오른다" 같은 수치는 검증 가능한 1차 출처를 찾지 못해 쓰지 않았다.
- 과금은 **2026-09-29 기준 문서** 다. 문서 스스로 유동분과 리뷰 비용 범위가 바뀔 수 있다고 명시한다. 조직(Business/Enterprise) 과금은 다루지 않았다.
- 기능 이름이 자주 바뀐다. 예전의 "coding agent" 는 현재 문서에서 "cloud agent" 다. 글의 경로명은 작성 시점 문서 기준이다.

## References

[^bp]: GitHub Docs, "Best practices for using GitHub Copilot". <https://docs.github.com/en/copilot/get-started/best-practices>
[^instr]: GitHub Docs, "Adding repository custom instructions for GitHub Copilot" (자동 생성 프롬프트 포함). <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>
[^ca-bp]: GitHub Docs, "Best practices for using GitHub Copilot to work on tasks". <https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results>
[^about-ca]: GitHub Docs, "About GitHub Copilot cloud agent". <https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent>
[^env]: GitHub Docs, "Configure the development environment" (copilot-setup-steps.yml). <https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-environment>
[^risks]: GitHub Docs, "Risks and mitigations for GitHub Copilot cloud agent". <https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations>
[^cr]: GitHub Docs, "About GitHub Copilot code review" (노력 수준·예상 소비·자동 리뷰 트리거·승인). <https://docs.github.com/en/copilot/concepts/agents/code-review>
[^billing]: GitHub Docs, "Usage-based billing for individuals" (AI 크레딧·요금제별 할당). <https://docs.github.com/en/copilot/concepts/billing/usage-based-billing-for-individuals>
[^legacy]: GitHub Docs, "Requests in GitHub Copilot (legacy)" (2026-06-01 이후 연간 요금제 잔류자, 코드 리뷰 배수 13). <https://docs.github.com/en/copilot/concepts/billing/copilot-requests>
