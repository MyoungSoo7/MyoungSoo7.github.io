---
layout: post
title: "키로·Claude·헤르메스 3자 조합, 한 달 돌려보니 — 남은 시너지와 사라진 시너지"
date: 2026-10-26 02:17:30 +0900
categories: [ai]
tags: [multi-agent, hermes-agent, kiro, claude-code, codex, orchestration, retrospective]
---

한 달 전 [협업 시나리오 글]({% post_url 2026-09-28-hermes-kiro-claude-code-codex-collaboration-scenarios %})에서 넷의 역할을 나눴다.
Hermes 는 판정, Kiro 는 설계, Claude Code 는 실행, Codex 는 반박이었다.
그 글은 *설계도*였다. 이 글은 그 설계도가 한 달 뒤 **실제로 몇 번 쓰였는지**를 센다.

결론부터 적는다.

- **도구 셋이 서로 맞물려 돈 시너지는 한 달 동안 측정되지 않았다.** 시나리오 A·B 는 9/28 이후 한 번도 실행되지 않았다.
- **살아남은 건 도구가 아니라 규칙이다.** 파일로 넘기기, 숫자 재실행, 발행은 한 곳, 반대 검토자는 임시로 띄우기.
- 남은 다중 에이전트 사용은 **Claude Code 가 Codex 를 잠깐 띄우는 것** 하나였다. 헤르메스도 키로도 거기 없었다.

수치는 모두 우리 맥의 로컬 기록에서 직접 셌다(아래 각 절에 출처 파일을 적었다).
기간은 **2026-09-28 ~ 2026-10-26** 이다. 한 가정, 한 사용자, 한 달짜리 표본이다. 일반화할 근거는 아니다.

---

## 1. 시나리오별 판정표

| 9/28 시나리오 | 설계 | 한 달 실측 | 판정 |
|---|---|---|---|
| **A. 기능 추가** | Kiro 설계 → Claude 실행 → Codex 반박 → Hermes 판정 | Kiro 사용 **0 크레딧 · 0 턴** | 한 번도 안 돌았다 |
| **B. 장애 분석** | Hermes 팬아웃 + 읽기 전용 워커 4 | Hermes 팬아웃 실행 **누적 2회, 둘 다 8/13**. 칸반 작업 **0건** | 한 번도 안 돌았다 |
| **C. 판단 질문** | Claude 주도 + Codex 임시 반박 | Codex 세션 **7개** (6개가 워크트리 격리 작업) | 살아남았다. 단, 헤르메스·키로 없이 |
| **D. 발행은 하나** | 조사는 병렬, 발행은 한 세션 | 규칙으로 계속 적용 중 | 살아남았다. 도구가 아니라 규칙으로 |

아래에서 하나씩 근거를 붙인다.

## 2. 키로 — 이틀 쓰고 멈췄다

Kiro CLI 는 세션 파일에 턴마다 과금 단위(credit)를 남긴다.
이걸 합산하는 스크립트(`~/kiro-usage/kiro_usage.py`, 세션의 `metering_usage` 합)로 40일을 셌다.

| 날짜 (KST) | credit | 세션 | 턴 |
|---|---:|---:|---:|
| 2026-09-27 | 302.3 | 56 | 43 |
| 2026-09-28 | 127.2 | 4 | 36 |
| 9/29 ~ 10/22 | **0.0** | 10 | **0** |

사용량 전부가 9/27~28 이틀에 몰려 있다.
그 뒤 세션 파일 10개가 생겼지만 턴이 0이다. 띄웠다가 아무 요청도 안 보낸 흔적이다.
유료 플랜(Pro Max)은 9/30 에 해지했다.

키로가 빠진 이유는 성능 문제가 아니었다. **기댈 수 없는 지점이 두 번 드러났다.**

- **자기 보고와 실제 상태가 어긋났다.** 셸 없이 돈 키로가 테스트 개수를 349로 보고했는데 실제는 329였다.
  사람 없이 돈 키로 크루는 쓰기가 전부 권한 거부됐는데도 "N/N 통과"를 보고했다.
  둘 다 9/28 글(3절·7절)에 적은 사고다.
- **지정한 모델이 안 쓰였다.** kiro-cli 2.24.1 기본 엔진은 `--model` 을 경고 한 줄과 함께 무시했다.

이러면 키로가 낸 결과를 Claude 가 *전부 다시 돌려* 확인해야 한다.
확인 비용이 키로 몫의 작업량과 비슷해지면 넘겨줄 이유가 없다.

**그래도 남은 것:** 키로 스펙의 `requirements.md`·`design.md`·`tasks.md` 3파일 형식[^kiro-specs]이다.
이건 그냥 마크다운이라 키로 없이도 쓸 수 있다.
"인수 조건은 검증 가능한 문장으로" 라는 규칙은 지금도 Claude 작업에 그대로 쓴다.

## 3. 헤르메스 — 허브 자리가 비어 있었다

### 3.1 팬아웃과 칸반은 거의 안 쓰였다

9/28 글의 시나리오 B 는 헤르메스 팬아웃 정책 파일을 근거로 썼다.
그런데 실행 기록 디렉터리(`~/.hermes/fanout/`)에 남은 실행은 **2026-08-13 의 2건이 전부**다.
9/28 글을 쓰기 *전에* 이미 한 달 넘게 안 쓰이던 기능이었다.
헤르메스의 작업 보드(`kanban.db` 의 `tasks` 테이블)도 **0건**이다.

즉 "Hermes 가 판정한다" 는 칸은 9/28 당시에도 실제로는 비어 있었다.
그 글이 *관측*과 *설계*를 구분해 적긴 했지만, 정책 파일이 있다는 것과 그게 돈다는 것을 충분히 구분하지 못했다.
이번 글을 쓰는 이유의 절반이 이 정정이다.

### 3.2 크론은 돌았지만 실패의 대부분이 한도였다

헤르메스가 실제로 일한 곳은 스케줄러였다.
크론 실행 기록(`~/.hermes/cron/executions.db`)을 9/28 이후로 셌다.

| 상태 | 건수 |
|---|---:|
| completed | 53 |
| failed | 29 |
| unknown | 2 |

실패율은 $$29 / 84 \approx 34.5\%$$ 다.
실패 29건 중 **25건이 같은 원인**이었다. 크론이 쓰던 Gemini API 가 월 한도 초과(HTTP 429)나 선불 크레딧 소진(HTTP 402)을 돌려줬다.
헤르메스 자체가 깨진 게 아니라, *헤르메스가 기대는 또 하나의 계정*이 막힌 것이다.

10/26 기준으로 크론 일곱 개는 전부 일시정지 상태다.
그중 셋(청소·주간 리포트·데일리 브리핑)은 Claude Code headless 실행 + macOS launchd 로 옮겼다.
옮긴 과정은 [크론 이전 글]({% post_url 2026-10-26-hermes-cron-to-claude-launchd %})에 있다.
launchd 는 잠자기 중 놓친 일정을 깨어난 뒤 실행해 준다.[^launchd] 그래서 상주 에이전트가 스케줄러를 맡을 이유가 줄었다.

### 3.3 봇 사이 조율은 훅이 가져갔다

허브의 또 다른 역할은 "누가 무슨 일을 잡았나" 를 아는 것이었다.
이 역할은 지금 Claude Code 봇들의 훅이 한다.
각 봇이 상태 파일에 `agent / state / task` 를 쓰고, 프롬프트를 받을 때 다른 봇의 상태를 읽는다.
클러스터 쓰기 충돌은 `PreToolUse` 훅이 실행 직전에 막는다.[^cc-hooks]
헤르메스와 봇이 메시지를 주고받던 중계 디렉터리(`~/.hermes/bot_relay/outbox`, `replies`)는 비어 있다(마지막 변경 10/4).

## 4. 남은 것 — Claude 가 Codex 를 잠깐 띄우는 것

9/28 이후 Codex 세션은 7개다(`~/.codex/sessions`).
그중 6개가 10/13~14 에 생겼고, 각각 별도 git 워크트리(`ouroboros-c1` ~ `c6`)에서 돌았다.
Claude 쪽 작업이 일감을 나누고, Codex 가 격리된 작업 공간에서 하나씩 맡은 형태다.

이 조합이 살아남은 이유는 세 가지로 본다. 필자 해석이다.

1. **도입 비용이 작다.** 상주 프로세스가 없다. 부를 때 띄우고, 끝나면 내린다.
2. **격리가 기본값이다.** `codex exec` 는 기본이 읽기 전용 샌드박스이고[^codex-exec], 쓰기가 필요하면 워크트리 안에서만 한다.
3. **결과를 확인하는 경로가 이미 있다.** 반박이든 구현이든 diff 와 테스트 로그로 돌아오니, Claude 가 같은 명령으로 다시 돌려 볼 수 있다.

헤르메스와 키로에는 이 셋이 없었다.
헤르메스는 상주하고, 별도 모델 계정에 기대고, 결과가 텔레그램 메시지로 끝났다.
키로는 결과 보고가 실제 상태와 어긋났다.

## 5. 왜 시너지가 안 생겼나

Anthropic 은 에이전트 설계 지침에서 이렇게 권한다.

> When building applications with LLMs, we recommend finding the simplest solution possible, and only increasing complexity when needed.[^bea]

같은 회사의 멀티에이전트 리서치 시스템 글은 비용도 적어 둔다.
에이전트는 채팅보다 약 4배, 멀티에이전트는 약 15배 토큰을 쓴다고 한다.[^mars]
또 대부분의 코딩 작업은 리서치보다 *진짜로 병렬화할 수 있는 부분*이 적다고 한다.[^mars]
이 두 문장은 Anthropic 의 자사 시스템 관측이다. 중립 제3자가 재현한 수치는 아니다.

우리 한 달은 이 두 글의 주장과 같은 방향으로 움직였다. 정리하면 이렇다.

- **도구를 하나 더할 때마다 계정과 한도가 하나 더 붙는다.** 헤르메스 실패의 86%(29건 중 25건)가 Gemini 한도였다. 키로는 구독이 끊기자 그대로 멈췄다.
- **넘겨줄 때마다 확인 비용이 생긴다.** 확인을 건너뛰면 349 대 329 같은 사고가 난다. 확인하면 받는 쪽이 일을 거의 다시 한다.
- **우리 일감은 병렬화할 부분이 적었다.** 블로그 글 하나, PR 하나, 장애 하나는 대개 한 줄기 일이다. 넷에게 나눌 만큼 넓지 않았다.

전에 쓴 [멀티에이전트가 손해인 경우]({% post_url 2026-07-24-when-multi-agent-is-a-loss %})를 이번엔 우리 기록으로 확인한 셈이다.

## 6. 그래서 지금의 조합

| 자리 | 9/28 설계 | 10/26 현재 |
|---|---|---|
| 판정·사용자 보고 | Hermes | 그 일을 맡은 Claude Code 봇 하나 |
| 스펙·설계 | Kiro | 마크다운 3파일 형식만 남음 (작성은 Claude) |
| 실행·게이트 | Claude Code | Claude Code (변화 없음) |
| 반박·격리 작업 | Codex | Codex, 필요할 때만 띄움 |
| 스케줄러 | Hermes 크론 | launchd + Claude headless |
| 봇 간 조율 | Hermes 허브 | 상태 파일 + 훅 |

헤르메스를 다시 켤 조건도 적어 둔다. 필자 의견이다.

- **쉽게 쪼개지는 넓은 조사**가 반복될 때. 예를 들면 여러 노드·여러 리포를 동시에 훑는 정기 점검이다. Anthropic 글이 말하는 "넓게 먼저 훑는" 일감이 이 경우다.[^mars]
- **모델 계정이 막혀도 대체 경로가 있을 때.** 한도에 걸릴 때마다 멈추는 허브는 허브가 아니다.

둘 다 지금 우리 환경에서는 성립하지 않는다.

## 한계

- 표본은 **한 가정의 맥 한 대, 한 달**이다. 큰 조직, 다른 일감, 다른 도구 버전에서는 다를 수 있다.
- "사용 횟수가 0" 은 "쓸모가 0" 과 다르다. 이 글은 *안 쓰였다*를 셌고, *쓸 수 없었다*를 증명하지 않았다.
- 생산성이나 결함률을 비교한 측정은 없다. 그래서 "조합이 더 빨랐다/느렸다" 는 주장은 하지 않았다.
- 9/28 이전 키로 사용량에는 시험 실행이 섞여 있다(9/27 하루 세션 56개).

## References

[^bea]: Anthropic, "Building effective agents", 2024-12-19. <https://www.anthropic.com/engineering/building-effective-agents>
[^mars]: Anthropic, "How we built our multi-agent research system", 2025-06-13. 토큰 배수(약 4배·15배)와 코딩 작업의 병렬화 한계는 Anthropic 자사 관측이다. <https://www.anthropic.com/engineering/multi-agent-research-system>
[^kiro-specs]: Kiro, "Specs", *Kiro Docs*. <https://kiro.dev/docs/specs/>
[^cc-hooks]: Anthropic, "Hooks reference", *Claude Code Docs*. <https://code.claude.com/docs/en/hooks>
[^codex-exec]: OpenAI, "Command line options – Codex CLI", *OpenAI Developers*. <https://developers.openai.com/codex/cli/reference>
[^launchd]: Apple, "Scheduling Timed Jobs", *Daemons and Services Programming Guide*. <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html>
