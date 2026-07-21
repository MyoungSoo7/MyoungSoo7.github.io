---
layout: post
title: "Garry Tan의 gstack 해부: 열광, 회의, 그리고 내 스택에 가져올 것"
date: 2026-07-22 04:08:00 +0900
categories: [AI, Architecture]
tags: [ClaudeCode, gstack, GarryTan, Harness, Skills, Orchestration, ProductThinking]
---

# YC CEO의 작업복을 열어보다

Y Combinator CEO **Garry Tan**이 자신의 실제 Claude Code 셋업을 통째로 공개했습니다. 이름은 **gstack** — "CEO, 디자이너, 엔지니어링 매니저, 릴리즈 매니저, 문서 엔지니어, QA 역할을 하는 23개의 의견이 담긴(opinionated) 도구"입니다. GitHub 스타 12만 3천 개. 지금 하네스 엔지니어링 판에서 가장 유명한 물건임은 논쟁의 여지가 없습니다.

유명하다는 것과 좋다는 것은 다른 문제입니다. 이 글은 gstack을 하나의 관점이 아니라 **다섯 개의 렌즈**로 돌려가며 봅니다 — 무엇이 진짜 기여이고, 무엇이 과장이며, 내 스택에는 무엇을 가져와야 하는지.

## 렌즈 1: 제품 사고 — gstack의 진짜 발명품

23개 도구 목록을 처음 보면 리뷰·QA·배포 자동화가 눈에 들어오지만, 그건 다른 하네스에도 있습니다. gstack의 진짜 발명품은 **코드를 만들기 전 단계**에 있습니다.

- `/office-hours` — "회의적인 PM"이 되어 강제 질문(forcing questions)으로 아이디어를 심문합니다. 만들 가치가 있는지부터 따집니다.
- `/plan-ceo-review` — "지금 올바른 문제를 풀고 있는가?"라는 전략적 스코프 챌린지.
- `/plan-eng-review` — 기술 계획에 숨은 가정을 파내는 아키텍처 챌린지.

대부분의 코딩 하네스는 "어떻게 잘 만들까"의 규율입니다. gstack은 그 앞에 **"이걸 만드는 게 맞나?"라는 게이트**를 세웁니다. 엔지니어가 만든 하네스와 투자자·창업자가 만든 하네스의 차이가 정확히 여기서 드러납니다. Garry Tan은 수천 개 스타트업이 "잘 만든 불필요한 것"으로 죽는 걸 본 사람이고, 그 경험이 도구 순서에 새겨져 있습니다.

에이전트 시대에 이 게이트는 더 중요해집니다. 구현 비용이 급락하면 **잘못된 것을 빠르게 만드는 비용도 급락**하기 때문입니다. 심문이 먼저, 코드는 나중 — 이게 gstack의 제1 기여입니다.

## 렌즈 2: 워크플로 설계 — 먹이사슬로 연결된 스킬들

두 번째로 볼 것은 23개 도구가 나열이 아니라 **파이프라인**이라는 점입니다.

```
Think → Plan → Build → Review → Test → Ship → Reflect
```

각 스킬의 산출물이 다음 스킬의 입력입니다. `/office-hours`가 생성한 설계 문서를 `/plan-ceo-review`가 읽고, `/plan-eng-review`가 출력한 테스트 매트릭스를 `/qa`가 소비합니다. 결정 사항은 로컬 JSONL로 세션을 넘어 지속되고요.

여기에 역할 분리가 겹칩니다. 리뷰는 **적대적 역할**(CEO 스코프 챌린지, 스태프 엔지니어 리뷰, `/cso`의 OWASP+STRIDE 보안 감사)로 나뉘어 있고, `/design-shotgun`은 목업을 4~6종 뿌려 수렴이 아닌 발산부터 시작합니다. 소프트웨어 공학의 오래된 원칙들 — 계획과 구현의 분리, 관점을 나눈 리뷰, 기본값으로서의 보안 감사 — 을 에이전트 오케스트레이션에 이식한 형태입니다.

병렬화는 Conductor라는 별도 도구가 맡습니다. 격리된 워크스페이스에서 Claude Code 세션 10~15개를 동시에 굴리며, 한 세션은 `/office-hours`, 다른 세션은 `/review`, 또 다른 세션은 구현을 돌리는 식입니다.

## 렌즈 3: 회의적 시선 — 810배라는 숫자 앞에서

이제 브레이크를 밟을 차례입니다. Garry는 "2013년의 810배 속도로 출시한다"고 말합니다. 60일에 프로덕션 서비스 3개, 40+ 기능을 YC 경영과 병행하며 출시했다고요.

몇 가지를 냉정하게 짚어야 합니다.

**첫째, 측정 단위의 문제.** "논리적 코드 변경"은 자기 정의 지표입니다. 2013년의 Garry(Bookface를 만들던)와 2026년의 Garry는 경험, 자원, 만드는 것의 성격이 전부 다릅니다. 810이라는 숫자는 마케팅으로 읽는 게 안전합니다.

**둘째, 생존 편향.** 12만 스타는 도구의 품질만큼이나 **만든 사람의 위치**를 반영합니다. 같은 스킬 팩을 무명 개발자가 올렸다면 어땠을까요. "YC CEO의 실제 셋업"이라는 서사가 배포의 절반입니다.

**셋째, 23개 스킬의 컨텍스트 비용.** 스킬은 공짜가 아닙니다. 트리거 설명만으로도 세션마다 토큰을 얹고, 스킬이 많아질수록 **어떤 스킬이 발동해야 하는지의 혼선**도 커집니다. 이미 다른 하네스를 운영 중인 환경이라면 이 비용은 배가됩니다.

그럼에도 과장을 걷어낸 뒤 남는 것이 있습니다. "한 사람이 스무 명 팀처럼 출시하려면?"이라는 Karpathy의 질문에 대해, gstack은 적어도 **작동하는 답안 하나를 공개 코드로** 내놨습니다. 숫자는 의심하되 구조는 배울 가치가 있습니다.

## 렌즈 4: 생태계 속의 gstack — Superpowers·OMC와 겹쳐 보기

[하네스 시리즈](/2026/07/22/harness-flywheel-synergy/)에서 다룬 스택과 나란히 놓으면 위치가 선명해집니다.

| | Superpowers | OMC | gstack |
|---|---|---|---|
| 핵심 질문 | 어떤 **절차**로 일하나 | 어떻게 **편성**하나 | 이걸 만드는 게 **맞나** |
| 단위 | 프로세스 스킬 | 모드 + 에이전트 로스터 | 페르소나 스킬 23종 |
| 강제 방식 | 행동 전 스킬 호출 규율 | 라우팅 + 검증 루프 | 파이프라인 먹이사슬 |
| 만든 이의 시각 | 엔지니어 (Jesse Vincent) | 엔지니어 (Yeachan Heo) | 투자자·창업자 (Garry Tan) |
| 배포 형태 | 플러그인 | 플러그인 | 스킬 팩 (`~/.claude/skills`) |

겹침도 분명합니다. Superpowers의 `brainstorming` ≈ `/office-hours`, `systematic-debugging` ≈ `/investigate`, 리뷰 스킬군도 중복됩니다. OMC의 역할 편성과 gstack의 페르소나도 발상이 같은 계열이고요(전자는 실제 서브에이전트, 후자는 스킬 페르소나라는 구현 차이).

**겹치지 않는 것**이 gstack의 도입 가치입니다: 제품 심문 게이트(`/office-hours`, `/plan-ceo-review`), 발산형 디자인(`/design-shotgun`), 기본값 보안 감사(`/cso`), 실브라우저 QA. 셋을 다 까는 건 규율의 강화가 아니라 소음의 증가입니다 — [도구함 글](/2026/07/22/harness-engineering-toolbox/)에서 세운 원칙 그대로, **겹치면 안 깐다**.

## 렌즈 5: 내 스택에 가져올 것 — 선별 도입 전략

그래서 저의 결론은 전체 설치가 아니라 **선별 이식**입니다.

1. **`/office-hours` + `/plan-ceo-review`** — 제 스택(Superpowers + OMC + Ouroboros)에 유일하게 없는 층. Ouroboros의 인터뷰가 요구사항의 애매함을 줄인다면, office-hours는 **요구사항 자체의 존재 이유**를 심문합니다. 상호보완이지 중복이 아닙니다.
2. **`/cso`** — 보안 감사를 옵션이 아닌 파이프라인 기본값으로 만드는 발상. 운영 클러스터에 배포하는 개인 프로젝트일수록 필요합니다.
3. **나머지 20개는 보류** — brainstorming, systematic-debugging, 리뷰·QA 계열은 이미 커버됨. 같은 역할의 스킬 두 벌은 트리거 혼선만 만듭니다.

gstack이 스킬 팩(디렉토리 단위)이라는 점이 이 전략을 가능하게 합니다. 통째로 사느냐 마느냐가 아니라, 필요한 장기만 이식할 수 있습니다.

## 맺으며: 유명세를 걷어내고 남는 것

gstack에서 배울 가장 중요한 것은 23개 도구 중 어느 하나가 아니라 **순서**입니다. 심문 → 계획 → 구현 → 적대적 리뷰 → 검증 → 출시 → 회고. 구현 능력이 상향 평준화되는 시대에 차별화는 "얼마나 잘 만드나"에서 "무엇을 만들지 얼마나 잘 고르나"로 이동합니다. 투자자가 만든 하네스가 코드 리뷰보다 아이디어 심문에 첫 번째 도구를 배정했다는 사실 — 그게 이 물건의 가장 정직한 교훈입니다.

---

**참고 자료**
- [gstack GitHub (garrytan)](https://github.com/garrytan/gstack)
- [GStack — Product Hunt](https://www.producthunt.com/products/gstack)
- [A Claude Code Skills Stack: Superpowers, gstack, GSD 조합 가이드](https://dev.to/imaginex/a-claude-code-skills-stack-how-to-combine-superpowers-gstack-and-gsd-without-the-chaos-44b3)
- [GStack: Turn Claude Code Into a Full Engineering Team](https://dev.to/max_quimby/gstack-turn-claude-code-into-a-full-engineering-team-1c7e)
