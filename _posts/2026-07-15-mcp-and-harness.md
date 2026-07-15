---
layout: post
title: "MCP와 Harness — 좋은 에이전트는 모델이 아니라 운영 구조에서 나온다"
date: 2026-07-15 22:40:00 +0900
categories: [ai, engineering, agentic-coding]
tags: [mcp, harness, agent, llm, model-context-protocol, tool-use, skill, capability, orchestration]
---

![에이전트 harness 설계 8구획 — Candidate Workflow / Outside / Inside / State & Checkpoints / Retry & Re-question / Output Contract / Capability Matrix(NEW) / Skill Bundle(NEW)](/assets/images/design/agent-harness-8-sections.jpg)

같은 모델(Claude, GPT)을 써도 어떤 에이전트는 실무를 맡길 만하고 어떤 에이전트는 데모에서만 그럴듯하다. 차이는 대부분 **모델이 아니라 harness** — 모델을 감싸 "신뢰할 수 있는 업무"로 만드는 운영 구조 — 에서 온다. 그리고 그 harness에 **능력(capability)을 꽂는 표준 커넥터가 MCP**다.

미리 결론 한 줄:

> 모델은 토큰 생성기일 뿐이다. 그걸 재현 가능·검수 가능·복구 가능한 업무로 바꾸는 건 harness이고, 그 harness가 외부 세계와 연결되는 규격이 MCP다. **위 그림은 그 harness를 설계할 때 빠뜨리면 안 되는 8개 구획이다.**

---

## 1. Harness란 무엇인가

harness는 **모델을 둘러싼 모든 것**이다. 프롬프트 조립, 도구 호출, 상태 관리, 재시도, 검수, 사람 개입 지점 — 모델이 뱉는 확률적 텍스트를 결정적인 업무 흐름으로 묶는 뼈대.

핵심 구분:

- **모델**: "다음 토큰"을 잘 맞히는 것. 똑똑하지만 상태가 없고, 틀려도 자신 있게 틀린다.
- **harness**: 그 출력을 **명세에 맞는 산출물**로 강제하고, 실패를 감지하고, 어디까지 사람이 책임질지 경계를 긋는 것.

에이전트 품질의 상한은 모델이 정하지만, **실제 품질은 harness가 정한다.** 좋은 모델 + 허술한 harness = 그럴듯한 데모. 평범한 모델 + 탄탄한 harness = 맡길 수 있는 도구.

---

## 2. Harness 설계 8구획 (위 그림)

harness를 설계할 때 점검해야 할 8개 축이다. 앞 6개는 "업무를 어떻게 신뢰 가능하게 굴릴까", 뒤 2개(NEW)는 "능력을 어떻게 선언·확장할까"다.

1. **Candidate Workflow** — 이 에이전트에 맡길 업무·입력·산출물, 그리고 **사람이 판단할 지점**을 먼저 못 박는다. 아무 일이나 시키는 게 아니라 "이 워크플로가 에이전트 후보인가"부터.
2. **Outside** — 경계선. **사람이 최종 책임질 것**은 무엇인가. 배포 승인, 삭제, 외부 발행 같은 되돌리기 어려운 행위는 harness 밖(사람)에 둔다.
3. **Inside** — 내부 실행 파이프라인: **입력 정리 → 명세 → 실행 → 검수**. 모델을 바로 실행에 던지지 않고, 입력을 정규화하고 명세로 계약을 세운 뒤 실행하고 스스로 검수한다.
4. **State & Checkpoints** — **단계·결정·실패·검수를 기록**한다. 상태 없는 모델에 상태를 부여하는 층. 중간에 끊겨도 체크포인트에서 재개되고, "왜 이렇게 했나"가 로그로 남는다.
5. **Retry & Re-question** — 실패했을 때 **자동 재시도할지 vs 사람에게 되물을지, 그리고 어디로 복귀할지**를 규정한다. 무한 재시도는 조용한 낭비고, 아무 때나 되묻는 건 자율성 상실이다. 그 경계 설계가 harness의 성숙도다.
6. **Output Contract** — 산출물 계약: **결과물·근거·남은 질문·요약**을 정해진 형태로 낸다. "대충 답"이 아니라 스키마가 있는 출력. 이게 있어야 다음 단계가 그 출력을 기계적으로 소비한다.
7. **Capability Matrix (NEW)** — 능력을 **Workflow / Runtime / Integration** 세 층으로 정리. 무슨 절차(workflow)를, 어떤 실행환경(runtime)에서, 어떤 외부연동(integration)으로 할 수 있는가. **MCP는 바로 이 Integration 축에 꽂힌다.**
8. **Skill Bundle (NEW)** — `SKILL.md` 묶음으로 **capability를 선언**한다. "이 에이전트는 이런 능력이 있고, 이렇게 쓴다"를 코드가 아니라 선언으로. 능력을 재사용·조합·배포 가능한 단위로 만든다.

---

## 3. MCP란 무엇인가

**MCP(Model Context Protocol)** 는 에이전트를 외부 도구·데이터·능력에 잇는 **표준 프로토콜**이다. 흔한 비유로 **"AI를 위한 USB-C"** — 어떤 모델이든 어떤 도구든 같은 규격으로 꽂는다.

MCP 서버는 세 가지를 제공한다:

- **Tools** — 에이전트가 호출하는 함수(파일 검색, DB 쿼리, 메시지 전송…)
- **Resources** — 에이전트가 읽는 데이터(문서, 로그, 레코드…)
- **Prompts** — 재사용 가능한 프롬프트 템플릿

왜 표준이 필요한가? 모델 N개 × 도구 M개를 각자 붙이면 **N×M개의 통합**을 손으로 짜야 한다. MCP는 이걸 **N+M**으로 줄인다 — 도구는 MCP 서버 하나만 만들면 되고, 모델은 MCP 클라이언트만 있으면 그 도구를 전부 쓴다.

---

## 4. MCP는 harness의 어디에 꽂히나

여기서 두 개념이 만난다.

- **Capability Matrix의 Integration 축** = "이 에이전트가 외부와 무엇을 할 수 있나" → **MCP 서버들이 그 능력의 공급원**이다.
- **Skill Bundle** = 그 능력을 언제·어떻게·안전하게 쓸지 선언 → MCP가 "무엇을 할 수 있나"라면 Skill Bundle은 "언제 그걸 꺼내 쓰나"다.

즉 역할 분담이 명확하다:

> **MCP는 "능력을 꽂는 규격", harness는 "그 능력을 신뢰 가능하게 쓰는 구조".** MCP만 있고 harness가 없으면 강력한 도구를 아무렇게나 휘두르는 에이전트가 되고, harness만 있고 MCP가 없으면 세상과 단절된 채 똑똑하기만 한 에이전트가 된다.

MCP로 도구를 꽂았다면, 그 도구 호출은 여전히 harness의 규율을 따라야 한다 — Inside(명세→실행→검수)를 거치고, State에 기록되고, 실패하면 Retry/Re-question 정책을 타고, 결과는 Output Contract로 나온다. **도구가 강력할수록 harness의 Outside(사람 책임 경계)가 중요해진다.** 예를 들어 "프로덕션 배포"나 "삭제" 같은 MCP 도구는 harness가 반드시 사람 승인 뒤로 보내야 한다.

---

## 5. 실전 — 신뢰성은 모델이 아니라 harness에서 나온다

같은 그림을 실무 체크리스트로 읽으면 이렇게 된다:

- **되돌리기 어려운 건 Outside로** — 외부 발행·배포·삭제는 자동화하지 말고 사람 승인 게이트를 둔다.
- **모델을 바로 실행에 던지지 말 것(Inside)** — 입력 정규화 → 명세 → 실행 → 자기검수. 특히 자기검수 없는 에이전트는 "자신 있게 틀린" 출력을 그대로 내보낸다.
- **재개 가능하게(State & Checkpoints)** — 긴 작업일수록 단계·결정을 남겨야 중단·재시작·감사가 된다.
- **자동 재시도 vs 되묻기 경계(Retry & Re-question)** — 명확히 실패면 재시도, 판단이 갈리면 사람에게 되묻기. 이 경계가 없으면 무한루프 아니면 과잉질문이다.
- **출력에 계약을(Output Contract)** — 근거·남은 질문·요약을 강제하면 다음 단계가 그 출력을 신뢰하고 소비한다.

한 가지 구체적 예: **이 블로그의 배포·관리 파이프라인 자체가 harness + MCP 조합**으로 돌아간다. 텔레그램 메시지가 입력으로 들어오면(Integration=MCP 서버), 에이전트가 명세를 세우고(Inside), 격리된 작업공간에서 실행하고(Runtime), 배포는 사람 승인 뒤에만 진행하며(Outside), 결과는 라이브 검증까지 포함한 요약으로 보고한다(Output Contract). 모델이 똑똑해서가 아니라, **이 8구획이 채워져 있어서 맡길 수 있는 것**이다.

---

## 마무리

에이전트를 만들 때 우리는 자꾸 "어떤 모델이 제일 똑똑한가"를 묻는다. 하지만 실무에서 맡길 수 있느냐를 가르는 건 대부분 그 아래 harness다.

> **모델은 상한을 정하고, harness는 실제 품질을 정한다.** MCP는 그 harness에 세상과 연결되는 능력을 표준 규격으로 꽂아주는 커넥터다.

위 8구획 — Candidate Workflow, Outside, Inside, State & Checkpoints, Retry & Re-question, Output Contract, Capability Matrix, Skill Bundle — 을 다 채웠는지 물어보는 것. 그게 "그럴듯한 데모"와 "맡길 수 있는 에이전트"를 가른다.
