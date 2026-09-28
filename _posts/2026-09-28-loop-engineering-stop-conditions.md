---
layout: post
title: "루프 엔지니어링 2막 — 루프의 본체는 종료 조건이다 (네 가지 루프 유형과 멈춤 실패 두 종류)"
date: 2026-09-28 23:02:45 +0900
categories: [ai, engineering, automation]
tags: [loop-engineering, claude-code, goal, loop, ralph-loop, agentic-coding, harness]
---

7월에 이 블로그에서 루프 엔지니어링을 두 번 다뤘다. [loop 는 cron 인가 ralph 인가](https://myoungsoo7.github.io/2026/07/08/loop-engineering-cron-vs-ralph/)는 용어의 계보를, [2026년 7월 키워드 해부](https://myoungsoo7.github.io/2026/07/09/loop-engineering-overview-july-2026/)는 개념과 첫걸음을 다뤘다. 그 뒤 석 달 동안 바뀐 것이 있다. **정의가 공식화됐고, 도구가 기본 기능(primitive)이 됐다.** Anthropic 의 Claude Code 팀이 루프를 네 종류로 나눈 글을 냈고([Anthropic, 2026-06-30](https://claude.com/blog/getting-started-with-loops)), 이름을 붙인 Addy Osmani 가 두 달 써 본 결과를 정리했다([Osmani, 2026-08-14](https://addyosmani.com/blog/practical-loop-engineering/)).

두 글을 나란히 읽으면 공통된 결론이 하나 나온다. **루프를 설계한다는 건 결국 "언제 멈추는가"를 설계하는 일이다.** 이 글은 그 주장을 1차 출처로 정리하고, 내가 실제로 운영하면서 겪은 멈춤 실패 사례로 검증한다.

## 1. 공식 정의 — "멈춤 조건이 충족될 때까지 반복하는 에이전트"

Claude Code 팀의 정의는 한 문장이다.

> "On the Claude Code team, we define loops as agents repeating cycles of work until a stop condition is met." — [Anthropic, *Loop engineering: Getting started with loops*](https://claude.com/blog/getting-started-with-loops)

정의 안에 **stop condition** 이 들어가 있다는 점이 중요하다. 이 팀은 루프를 네 가지 기준으로 분류한다. 무엇이 루프를 시작시키는가(trigger), 무엇이 멈추게 하는가(stop), 어떤 기본 기능을 쓰는가, 어떤 일에 맞는가. 같은 글에는 "모든 작업에 복잡한 루프가 필요하지는 않다. 가장 단순한 방법부터 시작하라"는 경고도 있다.

Osmani 는 8월 글에서 루프를 이렇게 다시 정의했다. "에이전트가 행동하고, 결과를 시험하고, 방법을 고치는 일을 **특정 목표가 달성될 때까지** 반복하는 자율적 자기교정 피드백 사이클"([Osmani, 2026-08-14](https://addyosmani.com/blog/practical-loop-engineering/)). 여기서도 핵심은 끝 부분, 목표가 달성될 때까지다.

## 2. 네 가지 루프 — "무엇을 넘겨주는가"로 읽기

Anthropic 글의 마지막 요약표가 가장 쓸모 있다. 루프 종류를 **사람이 에이전트에게 무엇을 넘겨주는가**로 정리했기 때문이다.

| 루프 | 넘겨주는 것 | 시작 | 멈춤 | 기본 기능 |
|---|---|---|---|---|
| 턴 기반 | 검증 | 사용자 프롬프트 | Claude 가 끝났다고 판단 | 검증 스킬(SKILL.md) |
| 목표 기반 | 멈춤 조건 | 실시간 수동 프롬프트 | 목표 달성 또는 최대 턴 | `/goal` |
| 시간 기반 | 트리거 | 정해진 간격 | 취소하거나 일이 끝남(PR 머지, 큐 비움) | `/loop`, `/schedule` |
| 선제형(proactive) | 프롬프트 자체 | 이벤트·스케줄, 실시간 사람 없음 | 각 작업은 목표 달성 시, 루틴은 끌 때까지 | 위 전부 + dynamic workflows |

출처: [Anthropic, 2026-06-30](https://claude.com/blog/getting-started-with-loops)의 각 절과 요약표를 옮겨 정리함.

아래로 내려갈수록 사람이 손에서 놓는 게 늘어난다. 처음엔 검증을, 그다음엔 멈출 시점을, 그다음엔 시작 시점을, 마지막엔 무엇을 할지까지 놓는다. **(해석)** 그래서 윗단을 튼튼하게 하지 않고 아랫단으로 건너뛰면 사고가 난다. 검증 스킬 없이 `/goal` 을 걸면 evaluator 가 확인할 근거가 대화에 남지 않고, 멈춤 조건이 흐린 채 `/schedule` 에 올리면 흐린 조건이 매시간 반복된다.

Osmani 도 같은 순서로 쓴다. 기본 기능은 사실상 둘이라고 말한다. `/goal` 은 측정 가능한 결승선이 있는 한 가지 작업을 끝까지 밀고, `/loop` 는 타이머로 다시 돌리는 스케줄러다. 둘을 조합하면 "루프가 확인을 예약하고, 골이 문제를 푼다"([Osmani, 2026-08-14](https://addyosmani.com/blog/practical-loop-engineering/)).

## 3. `/goal` 의 evaluator 는 무엇을 보는가 — 가장 오해하기 쉬운 부분

`/goal` 은 턴이 끝날 때마다 작고 빠른 모델이 조건 충족 여부를 판정하고, 아직 아니면 다음 턴을 시작한다. 공식 문서에서 가장 중요한 문장은 이것이다.

> "The evaluator judges your condition against what Claude has surfaced in the conversation. It doesn't run commands or read files independently" — [Claude Code Docs, *Keep Claude working toward a goal*](https://code.claude.com/docs/en/goal)

**evaluator 는 명령을 실행하지 않고 파일도 읽지 않는다. 대화 기록에 드러난 것만 본다.** 그래서 문서는 좋은 조건에 필요한 요소 세 가지를 든다.

1. **측정 가능한 종료 상태 하나.** 테스트 결과, 빌드 종료 코드, 파일 수, 빈 큐 같은 것.
2. **확인 방법 명시.** 예를 들어 "`npm test` 가 0으로 끝난다", "`git status` 가 깨끗하다".
3. **바뀌면 안 되는 것.** 예를 들어 "다른 테스트 파일은 수정하지 않는다".

조건은 4,000자까지 쓸 수 있다. 실행 시간을 묶으려면 조건 안에 "or stop after 20 turns" 같은 턴이나 시간 절을 넣는다(같은 문서).

Osmani 는 여기에 선을 하나 더 긋는다. evaluator 는 결과물이 좋은지 나쁜지 보지 않고, 사용자가 정한 딱딱한 규칙이 대화 기록상 충족됐는지만 본다. **그러니 evaluator 는 품질 검사자가 아니다**([Osmani, 2026-08-14](https://addyosmani.com/blog/practical-loop-engineering/)). 그가 든 조건 예시는 멈춤 설계의 모범이라 그대로 옮긴다.

```
/goal Refactor the data-fetching layer in Dashboard.tsx until Lighthouse
performance score is >= 92 and LCP is under 1.8s as shown by the Lighthouse
CLI output. Do not change the public API of any hooks. Each turn must improve
at least one reported metric; abort if two consecutive turns show no
improvement. Stop after 10 turns.
```

이 조건 하나에 멈춤 장치가 네 겹 들어 있다.

- **목표 수치:** Lighthouse 92 이상, LCP 1.8초 미만.
- **증거의 출처:** Lighthouse CLI 출력으로 판정한다.
- **불변 조건:** hook 의 공개 API 는 바꾸지 않는다.
- **정체 감지와 상한:** 두 턴 연속 개선이 없으면 중단하고, 최대 10턴에서 멈춘다.

**(해석)** 목표 수치만 쓰는 사람이 많지만, 실제로 루프를 살리는 건 뒤의 두 겹이다. 정체 감지가 없으면 토큰이 새고, 상한이 없으면 멈추지 않는다.

## 4. 멈춤 실패는 두 종류다 — 내 운영에서 나온 사례

멈춤 조건이 틀리면 루프는 두 방향으로 망가진다. **안 멈추거나, 거짓으로 멈춘다.** 둘 다 이 봇을 운영하면서 실제로 겪었다.

### 4-1. 안 멈추는 루프 — 종료 신호를 못 읽는 감지기

2026-09-27, 별도 CLI 에이전트(kiro-cli)에 조사 작업을 맡기고 이렇게 끝나기를 기다렸다.

```bash
until grep -q "^EXIT" raw.log; do sleep 30; done
```

작업은 새벽 5시 31분에 끝났다. 그런데 로그의 종료 줄이 `\e[0m\e[1G\e[0m\e[?25hEXIT 0` 처럼 **같은 줄 앞쪽에 터미널 이스케이프 문자를 달고** 찍혔다. 줄 맨 앞(`^`)이 `EXIT` 가 아니었으므로 grep 은 끝까지 매치하지 못했다. 사람이 "언제 끝나?"라고 물은 12시 30분까지 **약 7시간 동안 끝난 작업을 기다리고 있었다.** 고친 방법은 두 가지다. 앵커를 빼고 `grep -q "EXIT [0-9]"` 로 찾거나, 프로세스를 직접 백그라운드로 띄워 **종료 자체를 신호로 받는다.**

**(해석)** 이 사고의 구조는 `/goal` evaluator 의 제약과 같다. 종료 판정기가 현실(프로세스가 끝남)을 직접 보지 않고 **현실의 표현(로그 텍스트)** 을 본다. 표현과 현실이 어긋나면 루프는 영원히 돈다. 그래서 공식 문서가 "Claude 의 출력이 증명할 수 있는 형태로 조건을 써라"라고 하는 것이다. Claude Code 의 예약 작업 문서도 같은 방향을 권한다. 폴링 대신 Monitor 도구로 백그라운드 스크립트의 출력 이벤트를 받고, CI 는 채널로 세션에 이벤트를 밀어 넣으라고 한다([Claude Code Docs, *Run prompts on a schedule*](https://code.claude.com/docs/en/scheduled-tasks)).

### 4-2. 거짓으로 멈추는 루프 — 공허한 초록불

반대 방향이 더 위험하다. 루프가 "통과"를 보고 멈췄는데, 사실은 **아무것도 검사하지 않은 통과**인 경우다. 내가 본 사례는 둘이다.

- **아키텍처 테스트 게이트.** 검사 대상 클래스를 하나도 불러오지 못하면(임포트 0개) 모든 규칙이 위반 0건으로 초록불이 된다. 대상이 없으니 위반도 없다. 한 모듈에는 "임포트 0이면 실패" 가드가 있었고, 옆 모듈에는 없었다.
- **에이전트 오케스트레이터의 기계 검증 단계.** 허용 목록에 없어 차단된 검증 명령이 "skipped" 로 처리됐고, skipped 가 PASS 로 집계됐다. 검사 0건인데 초록불이 켜졌다.

이런 게이트를 멈춤 조건으로 쓰는 루프는 첫 턴에 바로 "목표 달성"으로 끝난다. **(해석)** 문서가 말하는 "측정 가능한 종료 상태"에 한 줄을 더 붙여야 한다. **"측정이 실제로 일어났다는 증거"도 조건에 넣어라.** 예를 들어 "테스트 N개 이상 실행되고 전부 통과"처럼 쓴다. 그냥 "테스트 통과"라고 쓰면 0개 실행도 통과다.

Geoffrey Huntley 의 Ralph 루프 원문도 같은 곳을 짚는다. 무작정 도는 `while :; do cat PROMPT.md | claude-code ; done` 루프를 버티게 하는 건 테스트와 빌드가 만드는 **역압(back pressure)** 이고, 비결정성이 이 방식의 아킬레스건이라고 썼다([Huntley, 2025-07-14](https://ghuntley.com/ralph/)). 역압이 공허하면 루프는 아무 저항 없이 틀린 방향으로 굴러간다.

## 5. 만드는 쪽과 확인하는 쪽을 나눈다

evaluator 가 품질 검사자가 아니라면, 품질은 누가 보는가. 두 1차 출처의 답이 같다. **일을 한 에이전트에게 그 일이 좋은지 판정시키지 마라.**

- Anthropic 은 코드 리뷰에 두 번째 에이전트를 쓰라고 한다. 맥락이 새로운 리뷰어는 메인 에이전트의 추론에 끌려가지 않기 때문이다. 또 "코드를 쓰는 루프에는 그걸 확인하는 루프가 필요하다"고 쓴다([Anthropic, 2026-06-30](https://claude.com/blog/getting-started-with-loops)).
- Osmani 는 하위 에이전트 하나가 변경을 만들고 다른 하나가 검증하게 한다. 예로 든 건 이런 상황이다. 만든 쪽은 데스크톱 성능만 보고 자신 있어 하는데, 실제로 중요한 건 모바일이다. 이런 걸 확인하는 쪽이 잡는다([Osmani, 2026-08-14](https://addyosmani.com/blog/practical-loop-engineering/)).

내 운영도 이 구조다. 이 봇(Claude)이 조사하고 고치는 쪽이고, 검토가 필요한 작업에서는 **다른 벤더의 CLI 에이전트를 임시로 띄워 반대 토론자**로 세운다. 판정을 합성한 뒤 그 프로세스는 종료한다. 상주시키지 않는 이유는 토큰 비용 때문이기도 하고, 검증자가 오래 머물면 만드는 쪽의 맥락에 물들기 때문이기도 하다. **(해석)** Anthropic 이 말하는 "fresh context"의 이점은 새로 띄울 때만 생긴다.

## 6. 시간 기반 루프는 "대상이 바뀌는 속도"에 맞춘다

Anthropic 의 토큰 관리 조언 중 가장 실용적인 건 이것이다. "보고 있는 대상이 바뀌는 빈도에 간격을 맞춰라. 필요 이상 자주 돌리지 마라"([Anthropic, 2026-06-30](https://claude.com/blog/getting-started-with-loops)).

지금 운영 중인 네트워크 패킷 수집 파일럿 측정이 예다. 판정 기준이 일 단위(3일 판정, 일일 문서량 대비)라서 측정 루프도 **하루 한 번**, 정해진 시각에 읽기 전용 스크립트를 돌리게 했다. 1분 간격으로 돌려도 얻는 정보는 같고 비용만 1,440배다. 그리고 루프는 판정만 한다. 중단 기준에 걸리면 **자동으로 끄지 않고 사람에게 묻는다.** 끄는 작업에는 순서가 있고(설정 비활성화 → 리소스 소멸 확인 → 파일 삭제 → 연관 탐지 예외 제거), 순서를 틀리면 고아 리소스나 탐지 구멍이 남기 때문이다.

실무에서 알아 둘 제약도 공식 문서에 있다([Claude Code Docs, *Run prompts on a schedule*](https://code.claude.com/docs/en/scheduled-tasks)).

- `/loop` 는 **세션 범위**다. 세션이 끝나면 루프도 끝난다. 반복 작업은 **7일 뒤 만료**된다.
- 간격 없이 `/loop` 를 걸면 Claude 가 1분에서 1시간 사이에서 다음 실행 시점을 스스로 고른다.
- 기계가 꺼져도 돌아야 하면 클라우드 routine(`/schedule`)으로 옮긴다. 클라우드 쪽 최소 간격은 1시간이다.

## 7. 루프로 만들면 안 되는 일

Osmani 의 8월 글에서 가장 정직한 대목은 자기가 실패할 뻔한 이야기다. 경쟁 제품과 비교해 빠진 기능을 조사하고 로컬 PR 까지 만들게 했는데, 조사 결과만 읽고 구현은 꼼꼼히 보지 않은 채 push 할 뻔했다. 뒤늦게 보니 사용자에게 복잡성만 더하고 얻는 건 적은 변경이었다. 그의 말로는 **"작업을 위임했는데, 판단까지 위임할 뻔했다"**([Osmani, 2026-08-14](https://addyosmani.com/blog/practical-loop-engineering/)).

그래서 그는 인증, 보안, 금융을 건드리는 작업이나 시스템 접근 권한을 준 작업은 가까이서 지켜본다고 했다. 그린필드 코드베이스와 이력이 복잡한 은행 브라운필드 코드베이스는 다르게 다뤄야 한다고도 했다(같은 글). 6월 원 글의 마지막 문장도 같은 경고다. "루프를 만들어라. 하지만 계속 엔지니어로 남을 사람처럼 만들어라"([Osmani, 2026-06-07](https://addyosmani.com/blog/loop-engineering/)).

**(해석)** 이 기준을 멈춤 조건의 언어로 옮기면 이렇다. **결정론적으로 쓸 수 없는 멈춤 조건은 루프가 아니라 사람의 몫이다.** "UI 가 괜찮아질 때까지", "설계가 깔끔해질 때까지"는 evaluator 가 대화 기록에서 확인할 수 없다. 그런 일은 턴 기반 루프에 머무르게 하고, 사람이 매 턴 판정한다.

## 8. 체크리스트 — 루프를 올리기 전에

1. **이 일에 루프가 필요한가?** 턴 기반으로 충분하면 거기서 멈춘다(Anthropic).
2. **종료 상태가 숫자나 종료 코드로 쓰이는가?** 아니면 사람의 몫이다.
3. **측정이 실제로 일어났다는 증거가 조건에 있는가?** 0건 통과를 막는다.
4. **종료 판정기가 현실을 직접 보는가, 표현을 보는가?** 표현을 본다면 표현이 깨질 경우를 생각해 둔다(이스케이프 문자, 로그 형식 변화).
5. **정체 감지와 최대 턴이 있는가?** "두 턴 연속 개선 없으면 중단, 10턴 상한"(Osmani 예시).
6. **만드는 쪽과 확인하는 쪽이 다른 맥락인가?**
7. **간격이 대상이 바뀌는 속도에 맞는가?** 폴링 대신 이벤트(Monitor, 채널)를 쓸 수 있는가?
8. **되돌리기 어려운 행동(push, 삭제, 끄기) 앞에 사람 게이트가 있는가?**

## 9. 아직 안 풀린 것

- **중립적인 비교 데이터가 없다.** 어떤 루프 구성이 몇 퍼센트 더 낫다는 벤더 중립 헤드투헤드 벤치마크를 찾지 못했다. 이 글의 권고는 1차 출처(Anthropic 공식 블로그와 문서, 명명자 Osmani의 글)와 내 운영 경험에 기댄다. 성과 수치로 뒷받침된 게 아니다. 루프 엔지니어링을 수치로 홍보하는 제3자 사이트들은 출처를 검증할 수 없어 인용하지 않았다.
- **토큰 비용.** Osmani 는 6월 글부터 비용을 경고했고, Anthropic 도 모델과 effort 선택을 "가장 큰 비용 레버"로 꼽았다. 하지만 루프 하나가 실제로 얼마나 쓰는지는 작업마다 달라 일반화할 수 없다. 파일럿을 작게 먼저 돌려 재 보라는 게 공식 권고의 전부다.
- **evaluator 자체의 신뢰도.** `/goal` 의 판정도 작은 모델의 판단이다. 대화 기록에 거짓 증거(예: 공허한 PASS)가 찍히면 evaluator 는 그걸 믿는다. 4-2절의 문제를 evaluator 가 대신 풀어 주지 않는다.
- **판단 위임의 경계.** "어디까지가 작업이고 어디부터가 판단인가"를 정하는 규칙은 아직 개인 습관 수준이다.

## References

1. Anthropic (Delba de Oliveira, Michael Segner), [*Loop engineering: Getting started with loops*](https://claude.com/blog/getting-started-with-loops), Claude Blog, 2026-06-30. 루프의 공식 정의, 네 가지 유형, 품질과 토큰 관리 권고.
2. Claude Code Docs, [*Keep Claude working toward a goal*](https://code.claude.com/docs/en/goal). `/goal` evaluator 의 동작과 좋은 조건의 세 요소, 4,000자 제한.
3. Claude Code Docs, [*Run prompts on a schedule*](https://code.claude.com/docs/en/scheduled-tasks). `/loop` 의 세션 범위와 7일 만료, 클라우드·데스크톱 비교, Monitor 와 채널.
4. Addy Osmani, [*Loop Engineering*](https://addyosmani.com/blog/loop-engineering/), 2026-06-07. 용어를 명명한 원문.
5. Addy Osmani, [*Practical Loop Engineering*](https://addyosmani.com/blog/practical-loop-engineering/), 2026-08-14. `/goal` 과 `/loop` 운용, evaluator 는 품질 검사자가 아니라는 점, "판단 위임" 경고.
6. Geoffrey Huntley, [*Ralph Wiggum as a "software engineer"*](https://ghuntley.com/ralph/), 2025-07-14. bash while 루프 원형, 역압(back pressure)과 비결정성.
7. 이 블로그의 이전 글: [loop 는 cron 인가 ralph 인가 (2026-07-08)](https://myoungsoo7.github.io/2026/07/08/loop-engineering-cron-vs-ralph/) · [Loop Engineering 키워드 해부 (2026-07-09)](https://myoungsoo7.github.io/2026/07/09/loop-engineering-overview-july-2026/) · [ReAct·MCP·ACP 한 루프 세 경계 (2026-09-17)](https://myoungsoo7.github.io/2026/09/17/react-mcp-acp-one-loop-three-boundaries/).
