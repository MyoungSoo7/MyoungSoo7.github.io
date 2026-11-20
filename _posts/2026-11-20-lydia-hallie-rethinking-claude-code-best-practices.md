---
layout: post
title: "사람이 루프에서 빠지면 무엇이 그 자리를 채우나 — Lydia Hallie 「Rethinking Claude Code Best Practices」 요약"
date: 2026-11-20 17:48:32 +0900
categories: [AI, 개발문화]
tags: [ClaudeCode, AI에이전트, 코딩에이전트, AutoMode, 샌드박스, 훅, CI, 하네스]
---

> 🎤 원 발표: [Rethinking Claude Code Best Practices — Lydia Hallie, Anthropic (AI Engineer)](https://www.youtube.com/watch?v=vlfCjWuv4es)

## 누가 한 발표인가

Lydia Hallie는 Anthropic의 Claude Code 팀 소속이다. 원래 AI Engineer 행사 무대에서 하려던 발표였는데, 현장에서 기술 문제가 생겨 집에 돌아가 자기 컴퓨터로 다시 녹화해 올렸다고 영상 첫머리에서 밝힌다. 그래서 영상은 슬라이드와 화면 녹화 위주다.

발표 전체를 한 문장으로 줄이면 이렇다. **올해 초의 베스트 프랙티스는 사라진 게 아니라, 사람에게서 모델·하네스·환경으로 자리를 옮겼다.**

이 글은 붙여 받은 요약본을 원 발표 녹취와 공식 문서에 대조해 다시 정리한 것이다. 요약본과 다른 부분은 글 끝의 대조표에 모았다.

## 1. 무엇이 바뀌었나 — 운전자에서 관리자로

올해 초의 세션은 Opus 4.5 위에서 돌았다. 그 시절 모델은 일찍 멈췄고, 사람이 계속 고쳐 주고 상기시켜 줘야 했다. CLAUDE.md에는 `IMPORTANT!` 같은 강조가 쌓였다. auto mode가 없었으니 권한은 전부 손으로 승인하거나 `--dangerously-skip-permissions` 로 위험을 떠안았다.

지금 Anthropic 내부 세션은 다르다고 한다. 수십 개 세션이 몇 시간씩 동시에 돌고, 스스로 결과를 검증하고, 세션이 다른 세션을 지휘한다. 개발자는 한두 세션을 모는 사람에서 수십 개 세션의 관리자가 됐다.

규모 감각을 주는 숫자는 발표가 직접 언급한 Anthropic 엔지니어링 블로그 글에 있다. 사내 모노레포에 하루 병합되는 변경이 2026년 5월 평균 약 2,500건에서 9월 3만 건 이상으로 늘었다 ([Anthropic, 2026-10-13](https://www.anthropic.com/engineering/redesigning-source-control)). Anthropic 자사 수치이고 외부에서 재현할 수 있는 자료는 공개되지 않았다.

그래서 질문이 바뀐다. 예전 베스트 프랙티스는 사람이 하던 다섯 가지였다. 세션 방향 잡기, 명령 승인, 거절·제한, 결과물 확인, 세션 시작. 사람이 빠지는 자리마다 **모델, 하네스, 실행 환경** 중 하나가 그 일을 넘겨받아야 한다.

| 예전에 사람이 하던 일 | 지금 넘겨받는 것 |
| --- | --- |
| 세션 중간에 방향 잡기 | 모델 (의도 파악이 좋아짐) |
| 명령마다 승인 | auto mode 분류기 |
| 절대 안 되는 것 막기 | 하네스의 deny 규칙 |
| 부작용 범위 제한 | 실행 환경 (샌드박스, 클라우드 세션) |
| 결과가 맞는지 확인 | 테스트·훅·CI |
| 세션 시작·분배 | 오케스트레이터 세션 |

## 2. 기본값부터 — 모델, auto mode, 가벼운 CLAUDE.md

첫 단계는 그냥 지금의 기본값을 쓰는 것이다. 모델을 Opus 5.5로, 권한 모드를 auto mode로 바꾼다.

**auto mode.** Anthropic은 2026년 8월 14일부터 Pro·Max·Team 플랜의 새 세션을 auto mode로 시작하게 바꿨다 ([Claude 공지](https://claude.com/resources/articles/auto-mode-default-in-claude-code)). auto mode는 프로젝트 안 파일 읽기·편집 같은 일을 빼고 거의 모든 동작을 별도 분류기에 통과시킨다. 테스트 실행이나 의존성 설치처럼 안전하다고 아는 것은 통과시키고, 확신이 없는 것은 막는다.

**auto mode 다듬기.** 기본값은 현재 폴더와 현재 리포만 신뢰한다. 그래서 "스테이징에 올려줘"처럼 배포 리포에 push하는 일은 막히고 사람이 다시 루프로 들어온다. 이런 승인이 잦다면 설정에서 auto mode에 줄 기준을 평문 영어로 적을 수 있다. 신뢰하는 리포·버킷·도메인, 항상 허용할 것, 절대 하지 말 것을 쓰면 그 글이 분류기에 그대로 전달된다.

**CLAUDE.md 다이어트.** 지금 모델에게 `IMPORTANT`, `NEVER DO THIS!` 같은 강조는 필요 없다. 오히려 궤도를 벗어나게 만들어 툴 호출이 늘고 결과가 나빠질 수 있다고 Hallie는 말한다. CLAUDE.md에는 **코드만 봐서는 알 수 없는 것**만 남긴다. 예를 들면 코드에서 직접 참조하지 않는 레거시 소스를 아직 쓰는 서비스가 있다는 사실이다. 어떤 스택을 쓰는지, 어디를 보라는 안내는 모델이 코드에서 알아낸다.

정리를 돕는 명령이 `/doctor prompt-audit` 이다 (v2.1.283 이상). CLAUDE.md·AGENTS.md·스킬·서브에이전트 등을 읽고 세 가지를 찾아 diff로 제안한다. 예전 모델용으로 쓴 문구, 더 이상 없는 파일·명령 참조, 서로 다른 말을 하는 파일이다. 사용자가 적용하라고 하기 전에는 아무것도 바꾸지 않는다 ([Claude Code 문서 — skills](https://code.claude.com/docs/en/skills), [commands](https://code.claude.com/docs/en/commands)).

> 이 블로그 주인의 전역 CLAUDE.md에도 ⚠️ 와 굵은 글씨 "절대" 가 꽤 있다. 다만 그중 상당수는 "코드에서 알 수 없는 사고 이력"이라 Hallie 기준으로도 남길 쪽에 가깝다. 강조 표시를 지우는 일과 내용을 지우는 일은 별개다.

## 3. 안전 — 모델이 아니라 하네스와 환경으로 보장한다

루프에서 빠지는 건 쉽다. 어려운 건 빠져도 괜찮다는 확신이다. Hallie는 그 확신을 안전과 검증 두 축으로 나눈다.

### 분류기는 확률이다

모델과 auto mode는 대부분 시키는 대로 하지만, 보장은 아니다. Anthropic이 8월에 공개한 통제 실험에서 유료 테스터 1,053명에게 위험한 명령 하나를 슬쩍 섞어 보여 줬다. 사람은 13.6%(143건)만 잡았고 auto mode는 89%(937건)를 막았다 ([Claude 공지](https://claude.com/resources/articles/auto-mode-default-in-claude-code)). 사람보다 훨씬 낫지만, 거꾸로 보면 그 실험에서 열 개 중 하나꼴은 통과했다.

### 보장이 필요하면 deny 규칙

보장이 필요한 것은 하네스에서 강제해야 한다. 여기서 예전 베스트 프랙티스 중 권한 규칙이 여전히 살아 있다. deny 규칙에 걸리는 툴 호출은 분류기에 가기 전에 막히고, 분류기는 그 호출을 보지도 못한다. 단, `python:*` 처럼 임의 코드 실행을 통째로 허용하는 넓은 allow 규칙은 auto mode에서 잠시 꺼진다 (같은 공지).

무엇을 규칙으로 만들고 무엇을 모델에 맡길지는 한 질문으로 가른다. **이걸 한 번 틀렸을 때 되돌릴 수 있나?**

- 코드를 잘못 쓰는 건 되돌릴 수 있다. 모델에 맡긴다.
- 커밋 안 한 변경을 날리거나, 비밀키를 읽어 transcript에 남기는 건 되돌릴 수 없다. 규칙으로 막는다.

예를 들어 `.env` 는 auto mode 기본값으로는 그냥 읽힌다. 절대 못 읽게 하려면 `Read(./.env)` 같은 deny 규칙을 넣는다 ([권한 문서](https://code.claude.com/docs/en/permissions)).

### 규칙이 못 보는 곳 — 샌드박스

그런데 `npm test` 는 어떤가. 평범한 테스트 명령이니 auto mode는 통과시킨다. 하지만 테스트가 돌 때는 내가 쓰지 않은 의존성 코드가 실행된다. 그중 하나가 오염돼 있으면 `.env` 나 SSH 키를 열어 처음 보는 서버로 보낼 수 있다. 사람이 승인하던 시절이었어도 그냥 허용을 눌렀을 것이다. 거절할 거리가 화면에 안 보이니까.

권한 규칙은 툴 호출을 실행할지만 정할 뿐, 실행된 뒤 무엇에 닿는지는 제한하지 못한다. 그래서 명령을 막는 대신 실행 환경을 좁힌다. 로컬이라면 **샌드박스**다. 읽을 파일, 쓸 폴더, 접속할 호스트를 정하면 OS가 강제하고, 그 명령이 띄운 자식 프로세스에도 적용된다. deny 규칙도 OS 수준으로 내려가서, 의존성이 `.env` 를 열려 하면 OS가 거부한다.

공식 문서로 확인한 두 가지 함정이 있다 ([샌드박스 문서](https://code.claude.com/docs/en/sandboxing)).

- 샌드박스는 기본적으로 **꺼져 있고**, 켜도 읽기는 기본값으로 기계 대부분이 열려 있다. `~/.ssh`, `~/.aws/credentials` 같은 자격 증명 파일도 포함이다. SSH 키를 지키려면 규칙을 따로 넣어야 한다.
- 샌드박스는 **셸 명령만** 감싼다. Claude의 파일 도구, MCP 서버, 훅은 바깥에서 돈다.

### 아예 없는 곳에서 돌리기 — 클라우드 세션

두 번째 함정 때문에 Hallie는 한 걸음 더 간다. 세션 전체를, 애초에 그런 것들이 없는 곳에서 돌리자는 것이다. 클라우드 세션은 새 리포 복사본이 든 전용 머신에서 돌고, 노트북을 덮어도 계속 간다.

- `.env`, SSH 키, GitHub 토큰은 git에 없으니 거기에도 없다.
- API 키가 필요하면 **network secret** 으로 넣는다. Anthropic 에이전트 프록시가 요청이 VM을 떠난 뒤에 키를 붙이므로 키가 VM 안으로 들어오지 않고, 모델에게도 보이지 않는다 ([클라우드 환경 문서](https://code.claude.com/docs/en/cloud-environments)).
- 네트워크는 기본값 Limited다. 패키지 레지스트리와 GitHub 정도만 열리고, 나머지 도메인은 직접 추가해야 한다.

다만 머신은 일회용이어도 **거기서 나간 것은 남는다.** push한 커밋, 커넥터로 보낸 메시지가 그렇다. 그래서 클라우드에서도 auto mode를 켜고 deny 규칙을 리포에 커밋해 같이 가져가라고 한다. 강제 push나 커밋에 섞인 비밀을 거기서 잡는다.

## 4. 검증 — 결과물 전체 대신 검증 지점을 리뷰한다

사람이 루프에 있을 땐 모든 변경을 이미 봤으니 결과가 괜찮다는 걸 알았다. 몇 시간짜리 백그라운드 작업은 그렇지 않고, 끝나고 모든 파일을 읽지도 않을 것이다.

Hallie의 예시가 좋다. "인증을 새 API로 옮겨줘"라는 같은 프롬프트로 돌려도, 한 번은 옛 API를 남겨 두고, 한 번은 새 로그인에만 적용하고, 한 번은 모든 사용자를 로그아웃시킨다. 셋 다 그럴듯해 보인다. 그래서 중간중간 **통과/실패로 답이 나오는 검증 지점**을 둔다. 테스트, 빌드, 스크린샷, 뭐든 된다. 사람은 변경 전체가 아니라 이 검증 지점을 리뷰하면 되니 훨씬 짧다. 모두 로그아웃시키는 실행은 첫 검증에서 걸려 다른 길을 찾아야 한다.

**프롬프트로.** 가장 쉬운 방법이다. 완료가 무엇인지 말하고, 작업을 각자 테스트가 있는 태스크로 쪼개게 한다. Hallie는 실제 출력을 보여 달라고도 덧붙인다. 그 자리에 없었으니까. 하지만 프롬프트는 보장이 아니다.

**훅으로.** 반드시 돌아야 하는 검증은 훅으로 건다.

- 파일을 편집할 때마다 린터
- 태스크를 완료로 표시하려 할 때 바뀐 부분의 테스트 (인증 코드를 건드렸으면 인증 테스트 통과)
- 세션을 끝내려 할 때 전체 테스트 스위트

여기서 실수하기 쉬운 점이 하나 있다. 대부분의 도구는 실패하면 종료 코드 1을 내는데, Claude Code에서 1은 **차단이 아니다.** `TaskCompleted` 훅이 1로 끝나면 태스크는 그냥 완료 처리된다. Claude를 고치러 돌려보내는 건 **종료 코드 2**다. `Stop`·`TaskCompleted` 같은 이벤트에서 2를 내면 멈추지 못하고 계속 일하게 된다 ([훅 문서](https://code.claude.com/docs/en/hooks)).

## 5. 여러 세션으로 — CI, 위험도별 리뷰, 오케스트레이터

세션 하나를 혼자 둬도 마음이 놓이면 몇 개 더 띄운다. 각자 자기 머신이 있으니 같은 폴더를 두고 싸우지 않고, worktree를 직접 신경 쓸 일도 줄어든다. 그래도 여전히 모든 세션을 사람이 시작하고 사람이 리뷰한다.

**CI가 공통분모다.** 모든 세션은 결국 PR을 연다. 세션이 어떻게 설정됐든, Claude가 중간에 무엇을 정했든, CI는 모든 PR에 같은 검사를 돌린다. CI autofix를 켜면 Claude가 실패한 검사를 보고 돌아가 고친다. 체크가 잡을 수 있던 걸 사람이 리뷰하느라 시간 쓰지 않게 된다. merge when ready를 켜면 체크가 모두 통과했을 때 GitHub이 병합하지만, 기본값은 아니고 위험도에 달렸다.

**리뷰는 위험도별로 차등.** Hallie 팀에서는 모든 PR을 먼저 Claude가 리뷰한다. 코드를 쓴 세션이 아니라 새 컨텍스트의 Claude이고, 찾은 버그를 다시 확인하는 별도 에이전트 묶음이 붙는다. 그다음 사람 리뷰는 위험도로 정한다.

| 변경 종류 | 사람 리뷰 |
| --- | --- |
| 문서·문구 같은 작은 변경 | 자동 체크가 초록이면 사람 없이 |
| 평범한 제품 변경 | 1명 |
| 위험한 변경 | 2명 |

**오케스트레이터.** 마지막 단계는 세션 시작도 넘기는 것이다. Hallie는 자기가 컨텍스트 스위칭을 못한다고 털어놓는다. 메인 세션 하나가 오케스트레이터가 되어 일을 쪼개고, 태스크마다 다른 세션(스레드)을 띄우고, 돌아온 결과를 검증한다. 덜 됐으면 다시 돌려보낸다. 여덟 세션과 대화하는 대신 하나와 대화한다. 지금 베타인 Claude Code Projects가 이 구조다 ([Projects 문서](https://code.claude.com/docs/en/claude-projects)).

모델은 역할에 따라 따로 고른다. 메인 세션은 코드를 직접 쓰지 않으니 무엇을 할지 정하고 돌아온 걸 판단하는 데 강한 모델(Hallie는 Fable을 예로 든다), 스레드는 실제 작업에 강한 모델(Opus 5.5)이다. Projects 설정에서 Coordinator 모델과 Thread 모델을 따로 지정할 수 있다. 참고로 새 프로젝트의 기본값은 양쪽 모두 Opus이고, 조합은 Hallie의 제안이다. Projects에서는 컨텍스트 관리도 자동이라 언제 compact하고 clear할지 고민하지 않아도 된다.

## 6. 직접 해 보려면

Hallie의 마무리 제안은 이렇다.

1. 평소 Claude에게 주는 것보다 훨씬 큰 작업 하나를 고른다.
2. CI가 내가 신경 쓰는 것을 실제로 잡는지 확인한다.
3. 실행 환경을 조금 손본다. 네트워크 접근, 시크릿, 셋업 스크립트.
4. 클라우드에서 시작해서, 세션이 어디서 막히는지, 내가 여전히 어디서 루프에 있는지 본다. **그게 다음에 Claude에게 넘길 것이다.**

## 요약본 대조 — 고친 것, 보탠 것

붙여 받은 AI 요약본은 흐름은 정확했다. 원 녹취와 문서에 대조해서 바로잡거나 보탠 부분은 다음과 같다.

| 요약본 | 확인 결과 |
| --- | --- |
| "`/doctor`나 prompt audit 같은 명령어" | 명령 두 개가 아니라 하나다. `/doctor prompt-audit` (v2.1.283+). 그냥 `/doctor` 는 설치·설정 점검이라 다른 일을 한다 |
| "Auto Mode(8월부터 기본 적용)" | 맞다. 정확히는 2026-08-14부터, Pro·Max·Team 플랜의 새 세션 기준 |
| (없음) | 사람 13.6% vs auto mode 89% 실험 수치와 "열 개 중 하나는 통과" 언급을 보탰다. 분류기만 믿으면 안 되는 근거다 |
| (없음) | deny 규칙은 분류기보다 먼저 평가되어 분류기는 그 호출을 보지도 못한다. 이게 "규칙으로 막아라"의 메커니즘이다 |
| "샌드박스로 OS 수준 제한" | 맞다. 다만 기본은 꺼져 있고, 켜도 `~/.ssh` 를 포함해 읽기는 대부분 열려 있다. 파일 도구·MCP·훅은 감싸지 않는다 |
| "API 키는 시크릿으로 주입해 모델에 직접 노출되지 않게" | 맞다. 정확히는 키가 VM 안으로 아예 들어오지 않고 프록시가 나가는 요청에 붙인다 |
| "종료 코드 2를 반환해야 수정 루프로" | 맞다. 1이면 태스크가 그냥 완료 처리된다는 점까지 문서로 확인 |
| "오케스트레이터는 Fable 계열, 하위는 Opus 5.5" | 발표자의 권장 조합이다. Projects 기본값은 양쪽 모두 Opus |
| (없음) | 하루 병합 2,500건 → 3만 건 이상(Anthropic 자사 수치)을 보탰다 |

## 근거의 한계

- 하루 병합 건수와 auto mode 실험 수치는 모두 **Anthropic 자사 발표**다. 재현 가능한 자료는 공개되지 않았고, 중립적인 제3자 검증은 찾지 못했다.
- auto mode 실험은 테스터가 실제 코드베이스가 아닌 시험 환경에서 일한 통제 연구다. 실사용 차단율과 같다고 볼 수 없다.
- 발표는 Anthropic 내부의 일하는 방식을 소개한 것이다. 세션 수십 개를 동시에 돌리는 운용이 다른 팀에서도 같은 효과를 낸다는 근거는 이 발표에 없다.

## References

1. Lydia Hallie, "Rethinking Claude Code Best Practices", AI Engineer (YouTube). <https://www.youtube.com/watch?v=vlfCjWuv4es>
2. Anthropic Engineering, "Redesigning source control", 2026-10-13. <https://www.anthropic.com/engineering/redesigning-source-control>
3. Anthropic, "Auto mode is now the default in Claude Code for Pro, Max, Ultra, and Team plans", 2026-08-07. <https://claude.com/resources/articles/auto-mode-default-in-claude-code>
4. Claude Code Docs, "Extend Claude with skills" (`/doctor`, `/doctor prompt-audit`). <https://code.claude.com/docs/en/skills>
5. Claude Code Docs, "Commands". <https://code.claude.com/docs/en/commands>
6. Claude Code Docs, "Configure permissions". <https://code.claude.com/docs/en/permissions>
7. Claude Code Docs, "Configure the sandboxed Bash tool". <https://code.claude.com/docs/en/sandboxing>
8. Claude Code Docs, "Configure cloud environments" (network secrets, network access, setup scripts). <https://code.claude.com/docs/en/cloud-environments>
9. Claude Code Docs, "Hooks reference" (exit code 2 behavior per event). <https://code.claude.com/docs/en/hooks>
10. Claude Code Docs, "Let Claude coordinate ongoing work with Projects". <https://code.claude.com/docs/en/claude-projects>
