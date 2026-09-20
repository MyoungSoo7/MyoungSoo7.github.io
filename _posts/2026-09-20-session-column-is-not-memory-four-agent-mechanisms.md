---
layout: post
title: "표의 '세션' 칸은 기억을 뜻하지 않는다 — 실행 메커니즘 넷이 각각 버리는 것"
date: 2026-09-20 18:59:01 +0900
categories: [ai, agents]
tags: [openclaw, agent, cron, heartbeat, subagent, skills, session, automation, governance]
---

에이전트의 실행 메커니즘 네 가지를 한 장에 정리한 표를 받았다.

![메커니즘·session·directive·trigger 네 칸으로 정리한 에이전트 실행 메커니즘 표. Skill 은 호출자 세션 재사용 / workspace/skills/&lt;name&gt;/SKILL.md / 명시적 요청, Heartbeat 는 main / HEARTBEAT.md / 게이트웨이 타이머 ~30분, Cron 은 isolated 매 실행 fresh / job 의 payload.message / 예약 시각(사람 없음), Sub-agent 는 fresh 자식 부모가 핸들 보유 / 부모가 준 태스크 / 부모가 턴 중간에 결정](/assets/images/agent-execution-mechanisms-table.jpg)

이 표를 "에이전트에는 이런 실행 방식이 넷 있다" 는 목록으로 읽으면 제일 중요한 게 안 보인다. 목록은 어차피 넷보다 많다 — 공식 문서의 선택 가이드에는 hooks, standing orders, Task Flow 까지 같이 들어 있다.[^1] 이 표가 실제로 하는 일은 **행을 세는 게 아니라 축을 고른 것**이다. 두 번째 칸(`session`)과 세 번째 칸(`directive`)을 나란히 놓은 순간, "이 실행은 무엇을 물려받는가" 와 "무엇이 시킨 것인가" 가 서로 독립이라는 게 드러난다.

그리고 여기가 함정이다. `session` 칸을 **기억**으로 읽으면 틀린다. 네 메커니즘이 각각 버리는 것은 대개 대화 내용이 아니다.

아래는 표의 각 행을 OpenClaw 공식 문서에 대조한 결과다. 표 자체는 사용자가 보내준 화면 캡처 1장이고, 대조 대상은 벤더 1차 문서(`docs.openclaw.ai`, 2026-09-20 열람)다. 이 표의 분류를 검증한 **중립 제3자 자료는 찾지 못했다** — 아래 사실 주장은 전부 벤더 자신의 문서에 근거한다.

## 격리가 버리는 건 대화가 아니라 권한이다

표에서 제일 단호한 칸은 Cron 행의 `isolated — 매 실행 fresh` 다. 이걸 "지난 실행을 기억 못 한다" 로만 읽기 쉽다. 문서가 말하는 fresh 의 정의는 그보다 넓고, 더 날카롭다.

> 실행마다 새 transcript/session id. 안전한 선호값(thinking/fast/verbose 설정, 라벨, 사용자가 명시적으로 고른 모델·인증 오버라이드)은 이어지지만, 더 오래된 자동화 세션 행의 **주변 대화 컨텍스트는 상속하지 않는다 — 채널·그룹 라우팅, 발송·큐 정책, elevation, origin, ACP 런타임 바인딩**.[^2]

버려지는 목록을 다시 보자. 라우팅, 발송 정책, **elevation**, origin. 이건 기억이 아니라 **권한과 배달 경로**다. 그러니까 "격리되어 있으니 안전하다" 도 맞지만, 방향이 반대인 함정도 같이 생긴다 — 대화방에서 손으로 시켰을 때 잘 돌던 절차를 그대로 예약 잡에 넣으면, 그 절차가 기대던 승격된 권한과 "이 방으로 답한다" 는 경로가 조용히 사라진 채로 돈다. 실패는 "권한 없음" 으로 뜨지 않고 **아무 데도 안 가는 결과물**로 뜬다.

같은 표 안에 해독제도 이미 있다. 이어서 쌓고 싶으면 `current` 나 `session:<id>` 를 쓰라고 문서가 명시한다. custom 세션은 실행 간 컨텍스트를 유지해서 "어제 요약 위에 오늘 스탠드업을 얹는" 류의 워크플로를 만들 수 있다.[^2] 즉 `isolated` 는 크론의 성질이 아니라 **네 가지 실행 스타일 중 고른 하나**다(main / current / isolated / custom).

## Heartbeat — 컨텍스트는 있는데 쓰지 말라고 한다

표의 Heartbeat 행은 세션이 `main` 이다. 메인 세션이니 대화 이력이 다 있다. 그런데 기본 프롬프트가 이렇게 시작한다.

> 제공된 경우 heartbeat 모니터 scratch 컨텍스트를 따르라. 반복 작업은 automations 다 … **이전 대화에서 옛 작업을 추론하거나 반복하지 마라.** 주의가 필요한 게 없으면 `NO_REPLY` 로 답하라.[^3]

이 한 줄이 이 글의 주장을 그대로 증명한다. **세션 칸이 `main` 이어도 행동을 결정하는 건 `directive` 칸이다.** 컨텍스트의 유무와 컨텍스트의 사용 허가는 다른 축이고, 표는 그 둘을 굳이 별도 열로 갈라놨다.

나머지 사실도 맞춰두면: 기본 주기는 30분이고, Anthropic OAuth/토큰 인증(Claude CLI 재사용 포함)이 걸리면 `heartbeat.every` 가 unset 인 동안만 1시간으로 올라간다. `0m` 은 반복 주기만 끄고 모니터 잡은 비활성 상태로 남으며 scratch 는 보존된다. 그리고 예약 heartbeat 은 메인 큐·자동화 작업이 바쁘거나 대상 세션에 실행·대기 중 작업이 있으면 **미룬다**.[^3] 그래서 표의 `~30분` 은 주기의 상한이 아니라 **틱의 명목값**이다 — 바쁘면 안 온다. 모니터링을 이 위에 얹을 때 이 차이가 곧 사각지대가 된다.

## 스킬 행의 괄호가 진짜 함정이다

표는 Skill 의 trigger 를 `명시적 요청` 으로 적고 괄호로 `자동 선택은 별도 검증 필요` 를 달았다. 이 유보는 문서상 근거가 둘 있다.

**첫째, 스킬 목록은 세션 시작 시점에 스냅샷된다.** OpenClaw 는 세션이 시작될 때 자격 있는 스킬을 스냅샷하고 그 목록을 재사용한다. 파일 기반 스킬이 세션 중간에 갱신되는 건 정해진 트리거가 발생했을 때뿐이다 — 워처가 `SKILL.md` 변경을 감지, 게이트웨이 재시작, 새 원격 노드 접속, 네이티브 파일워치 용량 소진 후 다음 턴, 유휴·축출된 워크스페이스의 재개. 그리고 갱신된 목록은 **같은 세션의 다음 턴에서** 반영된다.[^4]

표 첫 행의 `호출자 세션 재사용` 이 여기서 비용으로 바뀐다. 세션을 재사용한다는 건 그 세션이 시작될 때 굳은 카탈로그를 계속 쓴다는 뜻이기도 하다. 방금 쓴 스킬이 "안 불린다" 의 1순위 용의자는 스킬 본문이 아니라 **스냅샷 시점**이다.

**둘째, 프롬프트 예산이 모자라면 설명문부터 버린다.** 스킬 카탈로그는 시스템 프롬프트에 XML 블록으로 주입되고 비용은 선형이다. 스킬 하나당 약 97자 + `name`·`description`·`location` 길이이며, 4자≈1토큰으로 치면 필드 길이를 빼고도 스킬당 약 24토큰이다.[^5] 그래서 한 세션의 카탈로그 비용은 대략

$$C_{\text{total}} \;\approx\; C_{\text{base}} + \sum_{i=1}^{n}\bigl(97 + |\text{name}_i| + |\text{description}_i| + |\text{location}_i|\bigr)\ \text{chars}$$

이고, 이 값이 `skills.limits.maxSkillsPromptChars` 를 넘으면 OpenClaw 는 먼저 **이름과 위치(identity)** 를 최대한 살리고, 남는 예산으로 설명을 줄이고, **설명 예산이 남지 않으면 설명을 아예 뺀다.**[^5]

자동 선택은 설명문을 보고 도는데, 예산이 모자랄 때 제일 먼저 잘리는 게 그 설명문이다. 즉 스킬이 많아질수록 "있는데 안 골라진다" 가 구조적으로 발생하고, 증상은 조용하다 — 에러가 아니라 그냥 안 부른다. 문서는 압축이나 절단이 일어나면 프롬프트에 `openclaw skills check` 를 가리키는 주석이 붙는다고 명시한다.[^5] 표의 괄호를 실무 절차로 바꾸면 이 명령 한 줄이다.

## Sub-agent — "부모가 핸들 보유" 는 비용이자 안전장치다

서브에이전트는 자기 세션(`agent::subagent:<id>`)에서 돌고, 기본적으로 결과를 요청자에게 announce 하며, 모든 실행이 백그라운드 태스크로 추적된다. 비용 항목이 문서에 대놓고 적혀 있다 — **각 서브에이전트는 기본적으로 자기 컨텍스트와 자기 토큰 사용량을 가진다.** 무겁거나 반복적인 작업이면 `agents.defaults.subagents.model` 로 자식만 싼 모델에 태우라고 권한다. 자식이 정말로 요청자의 현재 transcript 가 필요하면 `context: "fork"` 로 띄운다.[^6]

표의 `부모가 핸들 보유` 는 그래서 단순한 소유 관계가 아니다. 문서의 설계 목표에 **"도구 표면을 오용하기 어렵게 유지한다 — 서브에이전트는 기본적으로 세션 도구와 메시지 도구를 받지 않는다"** 가 명시돼 있다.[^6] 자식은 부모보다 적게 할 수 있고, 결과는 부모를 통해 나간다. 여기서도 버려지는 건 대화 내용이 아니라 **도구 표면**이다.

행마다 버려지는 것을 한 칸으로 모으면 표의 두 번째 열은 이렇게 다시 읽힌다.

| 메커니즘 | 표의 `session` | 실제로 버려지는 것 |
| --- | --- | --- |
| Skill | 호출자 세션 재사용 | (대화는 유지) 대신 스킬 카탈로그가 **세션 시작 시점에 고정** |
| Heartbeat | main | 아무것도 안 버림 — 대신 **directive 가 사용을 금지** |
| Cron (isolated) | 매 실행 fresh | 라우팅·발송 정책·**elevation**·origin·ACP 바인딩 |
| Sub-agent | fresh 자식 | 부모 transcript(`fork` 로 선택 가능) + **세션·메시지 도구** |

## '사람 없음' 은 주석이 아니라 계약이다

표의 Cron 행 trigger 칸에 붙은 `(사람 없음)` 은 괄호 안 메모처럼 보이지만, 문서에는 이름이 붙은 계약으로 존재한다.

> 격리된 자동화 실행과 hook 에이전트 턴은 명시적으로 **무인(unattended)** 이다: 명확히 해주거나 승인해 줄 사람이 없다. 최종 응답은 계획이나 확인 요청이 아니라 **결과물 자체**여야 한다. 할 일이 없으면 `NO_REPLY` 를 반환하고 실패는 그대로 진술한다. 재시도와 실패 알림 정책은 스케줄러가 소유한다.[^2]

그리고 경계가 한 겹 더 있다. 신뢰된 예약 잡은 자기 지시가 우선해서 질문이나 계획을 일부러 요구할 수 있고 더 이상 필요 없는 잡을 스스로 제거할 수도 있지만, **외부 hook 턴은 그 예외를 받지 못한다** — 외부 콘텐츠 경계를 넘어서는 자기 제거 권한이 전달되지 않는다.[^2] 사람이 없다는 사실이 권한을 넓히는 게 아니라 좁히는 방향으로 설계돼 있다는 뜻이다.

여기에 payload 종류를 겹쳐 보면 표의 `job 의 payload.message` 칸이 왜 하필 그 필드인지도 분명해진다. 잡은 payload 를 정확히 하나만 갖는데, `--system-event` 는 메인 세션에 이벤트만 넣고 그 자체로는 모델을 부르지 않고, `--command` 는 게이트웨이 호스트에서 셸을 돌릴 뿐 모델을 안 부르며, `--script` 는 헤드리스 코드모드 스크립트다. **모델이 도는 건 `--message` 짜리 agent turn 하나뿐이다.**[^2] 표는 네 행을 전부 "에이전트가 생각하는 실행" 으로 맞춰놓은 것이고, 그 정렬이 우연이 아니다.

## 그래서 이 표를 어떻게 쓰나

고를 때 던질 질문은 "얼마나 자주 도나" 가 아니다. 순서대로 셋이다.

1. **누가 기다리고 있나.** 사람이 있으면 계획을 답해도 되고 되물어도 된다. 없으면 무인 계약이 걸린다 — 결과물이 아니면 실패다.
2. **이 일이 기대는 게 대화인가 권한인가.** 대화면 `current`/`session:<id>`, 권한·배달 경로면 격리가 그걸 떨어뜨린다는 걸 먼저 확인해야 한다.
3. **호출이 명시적인가 추론인가.** 추론이면(=스킬 자동 선택) 스냅샷 시점과 프롬프트 예산 두 개를 같이 봐야 한다.

표에 없는 행들 — hooks(세션 리셋·컴팩션 같은 수명주기 이벤트), standing orders(모든 세션에 주입되는 상시 권한), Task Flow(다단계 흐름 오케스트레이션), 그리고 webhook·IMAP·Gmail PubSub 같은 외부 트리거 — 도 같은 세 질문으로 갈린다.[^1] 행을 더 그리는 것보다 이 세 질문을 표 옆에 적어두는 쪽이 낫다.

마지막으로 스스로에게 정직할 것 하나. 위 내용은 전부 **벤더 1차 문서에 적힌 설계 의도**이고, 내가 이 네 메커니즘을 돌려 재현한 측정이 아니다. 특히 "격리 실행에서 elevation 이 안 따라온다" 같은 항목은 실제 사고로 확인하기 전까지는 문서의 약속일 뿐이다. 확인하는 방법 자체는 간단하다 — 대화방에서 되던 절차를 격리 잡으로 옮겨 **한 번은 일부러 실패시켜 보는 것**이다. 실패가 어디서 뜨는지(권한 오류인지, 아무 데도 안 가는 침묵인지)가 문서보다 정확한 답을 준다.

## References

- OpenClaw Docs, *Automation* — 자동화 메커니즘 선택 가이드, automations vs heartbeat 비교표, hooks·standing orders·Task Flow: <https://docs.openclaw.ai/automation>
- OpenClaw Docs, *Automation payloads* — payload 종류, 실행 스타일(main/current/isolated/custom), fresh session 의 정의, 무인 실행 계약: <https://docs.openclaw.ai/automation/cron-jobs/payloads>
- OpenClaw Docs, *Automations* — 스케줄러 CLI 와 잡 수명주기: <https://docs.openclaw.ai/automation/cron-jobs>
- OpenClaw Docs, *Heartbeat* — 기본 주기, 기본 프롬프트 전문, 지연(defer) 조건: <https://docs.openclaw.ai/heartbeat>
- OpenClaw Docs, *Skills* — 스냅샷과 갱신 트리거, 토큰 영향과 프롬프트 예산 축소 규칙: <https://docs.openclaw.ai/skills>
- OpenClaw Docs, *Sub-agents* — 세션 분리, 기본 도구 정책, `context: "fork"`, 비용 주의: <https://docs.openclaw.ai/subagents>
- 표 이미지: 사용자가 보내온 화면 캡처 1장(2026-09-20). 본문의 대조는 위 문서 기준이며, 이 표의 분류를 독립 검증한 제3자 자료는 확인하지 못했다.

[^1]: OpenClaw Docs, *Automation*, "Quick decision guide" 및 "Core concepts". 2026-09-20 열람.
[^2]: OpenClaw Docs, *Automation payloads* — "Payloads", "Main session vs current vs isolated vs custom", "What 'fresh session' means for isolated jobs", "Unattended run contract". 2026-09-20 열람.
[^3]: OpenClaw Docs, *Heartbeat* — "Defaults" 의 프롬프트 본문·주기·지연 규칙. 2026-09-20 열람.
[^4]: OpenClaw Docs, *Skills* — "Snapshots and refresh". 2026-09-20 열람.
[^5]: OpenClaw Docs, *Skills* — "Token impact". 수식은 문서가 서술한 선형 비용을 그대로 옮긴 것이다. 2026-09-20 열람.
[^6]: OpenClaw Docs, *Sub-agents* — 도입부의 설계 목표와 비용 주의. 2026-09-20 열람.
