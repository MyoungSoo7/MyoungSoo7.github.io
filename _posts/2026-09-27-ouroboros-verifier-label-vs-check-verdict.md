---
layout: post
title: "우로보로스 — verifier 가 붙인 실패 사유는 증상이고, 판결은 check 가 내린다"
date: 2026-09-27 01:40:00 +0900
categories: [ai]
tags: [ouroboros, agent-os, verifier, harness-engineering, ai-coding, evaluation]
---

[Ouroboros](https://github.com/Q00/ouroboros)는 스스로를 **"Agent OS"**라고 소개한다. 한 줄 요약은
*"Stop prompting. Start specifying."* 이다. README 의 설명을 그대로 옮기면 이렇다.
AI 코딩 에이전트의 비결정적인 작업을 **재생 가능하고, 관측 가능하고, 정책에 묶인 실행 계약**으로 바꾸는 로컬 우선 런타임 계층이다.
흐름은 인터뷰 → 명세 결정화 → 실행 → 평가 → 진화로 이어진다. Claude Code, Codex CLI, OpenCode, Hermes 위에서 돈다.

하네스 관점에서 왜 Ouroboros 를 주축으로 삼았는지는 [예전 글]({% post_url 2026-07-22-ouroboros-harness-main-axis %})에 적었다.
이 글은 그중 한 부분, **"에이전트가 일을 했다고 말할 때 그걸 누가, 어떻게 믿는가"**만 다룬다. 아래 표 한 장이 그 답이다.

![Ouroboros 에서 기존 verifier 가 붙인 실패 사유(증상)와 check 결과를 조합해 결론과 복구 방법을 정하는 표. evidence form mismatch 이면서 check pass 면 verifier 오판으로 재실행 없이 수락, check fail 이면 진짜 실패로 반례 수리. fabrication suspected 이면서 check fail 이면 진짜 거짓 보고로 반례 수리, check pass 면 보고만 부실하고 코드는 맞으므로 수락. evidence missing 은 check 가 pass/fail 을 결정하고 결과에 따라 처리. verifier 가 수락했는데 check fail 이면 verifier 가 놓친 것으로 반례 수리. blocked 이면서 check indeterminate 면 환경 문제로 agent 를 호출하지 않는다.](/assets/images/posts/ouroboros-verifier-vs-check-table.jpg)

## 두 개의 판정자

Ouroboros 에서 에이전트의 작업(AC, acceptance criterion 단위)을 판정하는 층은 두 개다.

1. **증거 verifier** — 에이전트가 "테스트를 돌렸다, 파일을 고쳤다"라고 주장하면, 그 주장이 **실행 기록(transcript)으로 뒷받침되는지** 본다.
   [공식 정책 문서](https://github.com/Q00/ouroboros/blob/main/docs/contributing/verifier-evidence-policy.md)에 따르면 실패 유형은 크게 둘이다.
   - `FABRICATION_SUSPECTED` — 주장을 뒷받침하는 실행 이벤트나 산출물이 **아예 없다**. 지어냈을 수 있다.
   - `EVIDENCE_FORM_MISMATCH` — 관련 작업은 기록에 **보이지만**, 증거의 형태로는 주장을 증명할 수 없다. 형식을 맞춰 다시 시도할 만하다.
2. **결정적 check(verify gate)** — AC 에 걸린 성공 계약(명령, 기대 산출물, 출력 조건)을 **하네스가 직접 실행**해 본다.
   말이 아니라 결과를 본다.

표의 핵심은 한 문장이다. **verifier 의 라벨은 "증상"이고, 판결은 check 가 내린다.**

## 표 읽기 — 행마다 무엇이 다른가

| verifier 라벨 (증상) | check | 결론 | 복구 |
|---|---|---|---|
| evidence form mismatch | pass | verifier 오판 | 재실행 없이 수락 |
| evidence form mismatch | fail | 진짜 실패 | 반례 수리 |
| fabrication suspected | fail | 진짜 거짓 보고 | 반례 수리 |
| fabrication suspected | pass | 보고만 부실, 코드는 맞음 | 수락 |
| evidence missing | pass / fail | check 가 결정 | 결과에 따라 |
| (수락함) | fail | verifier 가 놓침 | 반례 수리 |
| blocked | indeterminate | 환경 문제 | agent 호출 안 함 |

### 1·4행 — 라벨은 나쁜데 check 는 통과

에이전트가 일은 제대로 했는데 **보고가 서툰** 경우다. 증거를 verifier 가 읽을 수 없는 형태로 남겼거나,
형제 AC 가 이미 만들어 둔 파일을 검증만 하고 "내가 고쳤다"고 적은 식이다.

이게 가상의 경우가 아니라는 건 Ouroboros 의 [CHANGELOG](https://github.com/Q00/ouroboros/blob/main/CHANGELOG.md)가 보여 준다.
2026-09 벤치에서 **기능 검사를 거짓 보고로 반려한 90건 중 43건은, 실행 기록에 정확히 그 명령이 exit 0 으로 남아 있었다.**
다른 항목에는 테스트 4개가 통과했는데 `FABRICATION_SUSPECTED` 로 AC 가 두 번 실패하고, run 이 3/4 로 끝난 사례도 기록돼 있다.
이 항목의 설명대로, 성공 계약이 있는 AC 에서는 숨겨진 verify gate 가 **행동의 최종 권위**다.

이 경우 에이전트를 다시 돌리면 **토큰만 태우고 같은 결과**가 나온다. 그래서 복구는 "재실행 없이 수락"이다.

### 2·3행 — 라벨도 나쁘고 check 도 실패

진짜 실패, 또는 진짜 거짓 보고다. 이때 "다시 해 봐"는 약하다. check 가 **어떤 입력에서 어떻게 실패했는지**가 곧 반례다.
복구는 그 반례를 들고 고치게 하는 **반례 수리**다.

### 6행 — verifier 는 통과시켰는데 check 가 실패

가장 위험한 행이다. 증거 층이 **놓친** 것이다. 보고서는 그럴듯했고 증거 형식도 맞았지만, 실제로 돌려 보니 틀렸다.
두 판정자를 **독립적으로** 두는 이유가 이 행에 있다. 하나만 있었다면 이 실패는 성공으로 기록됐다.

### 7행 — 환경이 막혀 판정 불가

check 자체를 실행할 수 없는 상태다. 의존성이 없거나, 네트워크가 막혔거나, 도구가 없는 경우다.
결과는 pass 도 fail 도 아닌 **indeterminate** 다. 이때 에이전트를 다시 부르는 건 의미가 없다. 에이전트가 고칠 수 있는 문제가 아니기 때문이다.
그래서 복구는 **"agent 호출 안 함"**이다. 막힌 걸 막혔다고 기록하고 멈춘다.

## 왜 이 설계가 중요한가

### 1. 재시도 예산을 아낀다

"실패하면 다시 돌린다"는 가장 비싼 기본값이다. 이 표는 실패를 네 갈래로 가른다. 재실행이 필요 없는 실패(1·4행),
반례를 들고 고쳐야 하는 실패(2·3·6행), 에이전트 탓이 아닌 실패(7행), check 에 맡길 실패(5행)다.
재시도가 실제로 도움이 되는 경우에만 에이전트를 부른다.

### 2. 정직함의 기준을 지킨다

정책 문서는 `FABRICATION_SUSPECTED` 를 **"뒷받침하는 이벤트가 전혀 없는 주장"에만** 쓰라고 못박는다.
관련 작업이 보이는데 형식만 안 맞으면 `EVIDENCE_FORM_MISMATCH` 다. 문서의 표현을 빌리면,
이 구분이 *"구현자가 일을 지어낸 건 아니지만, 하네스는 그 증거를 아직 받아들일 수 없다"*는 상태를 정직하게 남긴다.
에이전트에게 거짓말쟁이 딱지를 함부로 붙이지 않으면서도, 증거 없는 주장은 끝까지 통과시키지 않는다.

### 3. 코어 verifier 를 가볍게 유지한다

같은 정책 문서의 또 다른 원칙은 **코어 verifier 에 테스트 러너별 파서를 넣지 말라**는 것이다.
pytest JUnit XML, Go test JSON, Maven Surefire XML 을 하나씩 가르치기 시작하면, 한 생태계를 통과시키는 대가로 모든 생태계를 지원할 의무가 생긴다.
대신 `set -o pipefail && <테스트 명령> 2>&1 | tail -100` 같은 **러너 중립적인 증명 형식**을 권한다.
`pipefail` 이 없으면 뒤쪽 `tail` 이 성공해서 앞쪽 테스트의 실패 상태가 가려진다.

표는 이 원칙과 맞물린다. verifier 가 모든 형식을 완벽히 읽지 못해도 괜찮다. **최종 판결은 check 가 하기 때문이다.**
verifier 는 가볍고 보수적으로 두고, 오판은 check 가 바로잡는다.

## 정리

- 에이전트의 **말**(증거)과 **결과**(check)를 따로 판정한다.
- 둘이 어긋날 때 **결과가 이긴다.** 단, 결과를 낼 수 없는 환경이면 판정을 보류하고 에이전트를 부르지 않는다.
- 복구 방법이 결론마다 다르다. 수락, 반례 수리, 호출 안 함. "그냥 다시 해"는 없다.

사람 팀에서도 익숙한 원칙이다. 보고서가 엉성해도 테스트가 통과하면 머지하고, 보고서가 완벽해도 테스트가 깨지면 반려한다.
Ouroboros 는 그걸 에이전트 하네스의 규칙으로 명문화했다.

## References

- Ouroboros README (Q00/ouroboros) — <https://github.com/Q00/ouroboros>
- Ouroboros, *Verifier Evidence Policy* — <https://github.com/Q00/ouroboros/blob/main/docs/contributing/verifier-evidence-policy.md>
- Ouroboros CHANGELOG (evidence/verifier 항목) — <https://github.com/Q00/ouroboros/blob/main/CHANGELOG.md>
