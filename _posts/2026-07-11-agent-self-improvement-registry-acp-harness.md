---
layout: post
title: "스스로 나아지는 에이전트 — *Registry · ACP · Harness* 세 기둥 과 되먹임 루프"
date: 2026-07-11 18:15:00 +0900
categories: [ai, agent, harness]
tags: [ai-agent, self-improvement, tool-registry, acp, harness, eval, feedback-loop, observability, mlops]
---

에이전트 의 "자기 개선" 은 *"모델 이 더 똑똑 해지는 것"* 이 아니다. **에이전트 가 *자기 능력 을 스스로 넓히고 고치는 것* — 툴 을 측정 하고, 개선 하고, 새로 만드는 루프** 다. 그걸 가능 하게 하는 부품 은 딱 세 개다.

![에이전트 자기개선 3기둥 — Tool Registry(Data) · ACP(Protocol) · Harness(Eval)](/assets/images/agent/self-improvement-three-pillars.jpg)

> **에이전트 에게 자기개선 을 할 수 있게 하려면 — ① Tool Registry(Data) ② ACP(Protocol) ③ Harness(Eval).**
> ACP 는 *어떤 툴 이 언제·어떻게·어떤 권한 으로·어디서 실행* 될 수 있는지 알려주고, Harness 는 *trace 를 기록·측정·수치화* 한다. 그 수치 를 근거 로 ACP 를 통해 툴 을 *개선 하거나 생성* 한다.

---

## 0. "자기 개선" 을 오해 하지 말자

흔한 오해 — 자기 개선 = 모델 이 스스로 파라미터 를 바꾸는 것. 아니다. 실무 의 자기 개선 은 훨씬 *공학적* 이다:

- 에이전트 가 **어떤 툴 을 자주 실패 하는지** 안다 (측정)
- 그 툴 을 **고치거나, 더 나은 툴 을 만든다** (개선/생성)
- 개선 결과 를 **다시 측정** 해서 나아졌는지 확인 한다 (검증)

즉 *모델 을 재학습* 하는 게 아니라 **에이전트 의 *능력 표면(capability surface)* 을 진화** 시키는 것. 그리고 이건 새로운 개념 이 아니다 — **관측 → 피드백 → 배포** 라는, 백엔드/DevOps 가 20년 해온 루프 를, *에이전트 자기 자신 에게* 적용 한 것이다.

---

## 1. Tool Registry (Data) — *무엇 을 할 수 있나*

첫 기둥 은 **능력 의 카탈로그** 다. 에이전트 가 쓸 수 있는 툴/스킬 의 목록 과 정의. [Codex 플러그인]({% post_url 2026-07-10-codex-plugins-extending-the-agent %}) 의 `plugin.json`, [SKILL.md]({% post_url 2026-07-10-superpowers-6-pillars-of-skill-md %}), MCP 의 tool 목록 — 전부 Registry 다.

Registry 가 **데이터** 인 게 핵심 이다. 코드 에 박힌 게 아니라 *조회·추가·수정 가능한 목록.* 그래야 에이전트 가 *"내가 뭘 할 수 있지?"* 를 런타임 에 묻고, *새 툴 을 등록* 할 수 있다. Registry 가 없으면 능력 자체 가 없다.

---

## 2. ACP (Protocol) — *언제·어떻게·어떤 권한 으로·어디서*

Registry 가 "무엇" 이라면, **ACP 는 "어떻게 쓰나" 의 규약** 이다. 그림 의 정의 그대로 — *어떤 툴 이 언제, 어떻게, 어떤 권한 으로, 어디서 실행* 될 수 있는지 를 에이전트 에게 알려준다.

이 네 가지 를 뜯어보면 낯익다:

| ACP 의 축 | 대응 | 내가 이번 에 다룬 것 |
|---|---|---|
| **언제(when)** | 트리거 조건 | SKILL.md 의 ROLE/description |
| **어떻게(how)** | 입출력 계약 | 플러그인 input schema |
| **어떤 권한(permission)** | 실행 허가 | plugin.json `permissions`, [superpowers hooks]({% post_url 2026-07-10-superpowers-6-pillars-of-skill-md %}) 의 FORBID |
| **어디서(where)** | 실행 환경 | 읽기전용 vs write, 어느 네임스페이스 |

즉 ACP 는 [superpowers 6기둥]({% post_url 2026-07-10-superpowers-6-pillars-of-skill-md %}) 과 [Codex 플러그인 권한]({% post_url 2026-07-10-codex-plugins-extending-the-agent %}) 을 하나 로 묶은 **"툴 을 *안전 하고 정확 하게* 호출 하는 규약"** 이다. ACP 가 없으면 — 에이전트 는 툴 을 *아무 때나, 아무 권한 으로* 부르거나(위험), *영영 안 부른다*(무용). 언제·권한 을 못 박아야 툴 이 *제대로* 작동 한다.

*(이번 세션 의 coordinator hook 이 정확히 ACP 의 "권한·어디서" 예시 다 — 어떤 세션 이 kubectl write 를 언제 할 수 있는지 를 규약 으로 강제 했다. Hermes 에 읽기전용 kubeconfig 를 준 것 도 "어디서·어떤 권한" 을 ACP 로 좁힌 것.)*

---

## 3. Harness (Eval) — *잘 하고 있나 를 수치 로*

세 번째 이자 자기 개선 의 *엔진* — **Harness 는 trace 를 기록 하고, 측정 하고, 수치화** 한다. 에이전트 가 툴 을 부를 때마다 남는 *궤적(trace)* — 성공/실패, 지연, 토큰, 재시도 — 을 모아 **숫자** 로 만든다.

왜 이게 엔진 인가. **개선 은 측정 에서만 나오기** 때문 이다. 어떤 툴 이 실패율 40% 인지, 어떤 경로 가 토큰 을 태우는지 를 *숫자 로 알아야* 고칠 지점 이 보인다. 이건 내가 [하네스 엔지니어링]({% post_url 2026-07-10-harness-engineering-weekly-app-cycle %}) 에서 "관측 없는 자동화 는 폭주 한다", [운영 회고]({% post_url 2026-07-09-a-day-of-k8s-java-ops-senior-retrospective %}) 에서 "hang 은 침묵 한다" 며 반복 한 그 원리 다.

*(이번 세션 에서 auto-trading 의 KIS 토큰 만료 버그 를 잡은 것 도 결국 **로그(trace) 가 "기간 이 만료된 token" 이라고 수치 로 말해줬기** 때문 이다. Harness 없이 는 "왜 안 되지" 로 끝났다.)*

---

## 4. 세 기둥 이 *루프* 로 닫힌다 — 그게 자기 개선

핵심 은 이 셋 이 **되먹임 고리** 로 연결 된다는 것:

```
Registry(무엇) ──▶ ACP(언제/권한/어디서) ──▶ 실행 ──▶ Harness(trace 측정·수치화)
     ▲                                                          │
     └───────────  수치 근거 로 툴 개선/생성  ◀────────────────┘
```

1. Registry 의 툴 을, ACP 규약 대로 실행 한다
2. Harness 가 그 실행 을 *측정* 한다 (실패율·비용·지연)
3. **수치 를 근거 로**, ACP 를 통해 툴 을 *고치거나 새로 만든다*
4. 새/개선 툴 이 Registry 에 등록 되고 — 다시 1번

이 고리 가 돌 때마다 에이전트 의 능력 표면 이 *조금씩 나아진다.* 이건 내가 [weekly app cycle]({% post_url 2026-07-10-harness-engineering-weekly-app-cycle %}) 에서 그린 *"회고 → 개발"* 피드백 루프 와 **똑같은 구조** 다 — 다만 대상 이 *앱* 이 아니라 *에이전트 자신 의 툴* 이라는 것. 자기 개선 = *회고 루프 를 자기 자신 에게 겨눈 것.*

---

## 5. 하나 라도 빠지면 무너진다

| 빠진 기둥 | 결과 |
|---|---|
| **Registry 없음** | 능력 자체 가 없다. 개선 할 대상 이 없음 |
| **ACP 없음** | 툴 을 아무렇게 부르거나(위험) 안 부른다(무용). 권한·시점 통제 불가 |
| **Harness 없음** | *어디 를 고칠지 모른다.* 눈 감고 개선 — 그냥 랜덤 |

특히 **Harness 없는 자기 개선 은 자기 개선 이 아니다.** 측정 없이 툴 을 바꾸면, 나아졌는지 나빠졌는지 조차 모른다. 숫자 가 없으면 그건 *개선* 이 아니라 *변경* 일 뿐이다.

---

## 6. ⚠️ 자기 개선 에는 *가드레일* 이 세트 다

에이전트 가 *자기 툴 을 스스로 만들고 고친다* — 강력 하지만 위험 하다. ACP 의 **권한(permission)** 축 이 여기서 결정적 이다. 자기 개선 루프 가 *무엇 까지 바꿀 수 있는지* 를 못 박지 않으면, 에이전트 가 새벽 에 혼자 prod 를 만지는 [auto-trading 에 RiskGuard 없는 것]({% post_url 2026-07-09-a-day-of-k8s-java-ops-senior-retrospective %}) 과 같은 구조 가 된다 — *메타 레벨 에서.*

그래서 실전 자기 개선 은 **"측정 은 넓게, 변경 은 좁게"** — Harness 로 모든 걸 관측 하되, ACP 로 *자동 변경 의 범위 를 게이트* 한다. 툴 을 새로 *제안* 하는 것 까진 자율, 실제 *배포/실행* 은 사람 승인. (내가 Hermes 를 읽기전용 으로 붙이고, 매매 코드 를 safety-gate 로 검토 한 것 과 같은 발상.)

---

## 맺으며

에이전트 의 자기 개선 은 마법 이 아니라 **엔지니어링 루프** 다 — *능력 을 카탈로그화(Registry) 하고, 호출 규약 을 정하고(ACP), 측정 해서(Harness), 수치 로 고친다.* 그리고 이 셋 은, 백엔드 가 늘 하던 것 과 같다 — 아티팩트 레지스트리, 설정/권한, 관측·피드백.

*결국 스스로 나아지는 에이전트 를 만드는 일 은, 좋은 관측 가능한 시스템 을 만드는 일 과 다르지 않다 — 다만 그 피드백 루프 를 에이전트 자신 에게 겨눌 뿐이다.*

---

_관련: [하네스 엔지니어링]({% post_url 2026-07-10-harness-engineering-weekly-app-cycle %}) · [superpowers 6기둥]({% post_url 2026-07-10-superpowers-6-pillars-of-skill-md %}) · [Codex 플러그인]({% post_url 2026-07-10-codex-plugins-extending-the-agent %}) · [멀티 에이전트]({% post_url 2026-07-09-multi-agent-systems-in-practice %})_
