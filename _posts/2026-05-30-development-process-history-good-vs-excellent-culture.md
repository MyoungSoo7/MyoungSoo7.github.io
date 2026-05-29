---
layout: post
title: "개발 프로세스 60년 — *변하는 것* 과 *변하지 않는 것*, 그리고 *좋은 문화* 를 넘어 *훌륭한 문화* 란 무엇인가"
date: 2026-05-30 01:10:00 +0900
categories: [reflection, software-engineering, culture]
tags: [development-process, agile, devops, sre, culture, organization, history, google, amazon, netflix, toss, woowa]
---

"우리 팀은 *애자일* 합니다" 라는 문장은 *어떤 회사도* 부정하지 않는다. 그런데 같은 팀에서 *3개월에 한 번* 배포하는 데가 있고 *하루 50번* 배포하는 데가 있다. 같은 *Scrum* 을 하는데 어떤 팀은 *spec 한 줄에 일주일* 토론하고 어떤 팀은 *PRD 없이* 직접 만든다.

같은 용어를 쓰지만 *완전히 다른 세계*. 이 차이는 *프로세스* 가 아니라 *그 위에 깔린 문화* 에서 온다. 본 글은 *개발 프로세스의 60년 역사* 를 짧게 훑고, *변하는 것 / 변하지 않는 것* 을 구분한 뒤, *좋은 문화* 와 *훌륭한 문화* 의 *결정적 차이* 가 무엇인지 — 국내외 기업 사례를 통해 고찰한다.

> 본 글은 *고찰* 이다. 학술적 정의보다 *현장 경험* 과 *공개된 회사 자료* 에 기반.

---

## TL;DR

| 차원 | 변하는 것 | 변하지 않는 것 |
|---|---|---|
| **방법론** | Waterfall → Agile → DevOps → Platform Eng | *짧은 피드백 루프* |
| **도구** | CVS → Git, Jenkins → GitHub Actions | *자동화의 본질* |
| **조직** | 기능 조직 → Spotify 모델 → Team Topologies | *Conway's Law* (조직 ≠ 코드 분리) |
| **문화** | 9 to 6 → Remote → Async First | *신뢰·자율·책임* |

| 좋은 문화 | 훌륭한 문화 |
|---|---|
| Agile / Scrum 가동 | *짧은 피드백 루프 + 실험 안전성* |
| CI/CD 있음 | *실패에서 배우는 postmortem 문화* |
| Code review 수행 | *글쓰기·문서로 사고 정련* |
| 자율 강조 | *자율과 책임의 균형 + 작은 팀* |
| 좋은 성과 | *장기 사고 + 비즈니스 도메인 깊이* |
| 좋은 인재 채용 | *나쁜 결정을 인정하는 문화* |

---

## 1. 60년의 흐름 — 짧은 역사

### 1960~70년대 — *Waterfall* (폭포수)
- 항공·군사 시스템 — *명세 한 번 잘못 = 추락*
- 단계: 요구사항 → 설계 → 구현 → 테스트 → 배포
- *가정*: 요구사항이 *변하지 않는다*

### 1980년대 — *Iterative / Spiral* (Barry Boehm, 1986)
- "한 번에 다 못 한다" 인정
- 위험 분석 + 반복

### 1990년대 — *RUP, V-Model*
- IBM Rational Unified Process
- *UML* 의 시대 (다이어그램 100장 → 코드 안 짬)

### 2001년 — **Agile Manifesto** (snowbird, Utah)
> "*Individuals and interactions* over processes and tools
> *Working software* over comprehensive documentation
> *Customer collaboration* over contract negotiation
> *Responding to change* over following a plan"

17명이 한 페이지로 *그 후 25년의 산업을 바꿈*.

### 2000년대 — Scrum · XP · Kanban
- Scrum: Sprint, Retrospective, Daily Standup
- XP: Pair Programming, TDD, Continuous Integration
- Kanban: WIP 제한, *흐름 시각화*

### 2009년 — **DevOps** (Patrick Debois)
- 개발 ↔ 운영 *벽 허물기*
- *"You build it, you run it"* (Amazon Werner Vogels 인용)

### 2010년 — *Continuous Delivery* (Jez Humble, David Farley)
- 모든 commit 이 *배포 가능* 한 상태
- CI/CD 가 *기본*

### 2016년 — **SRE** (Google, Beyer et al)
- *Error Budget*, SLI/SLO/SLA
- *Toil* 줄이기

### 2018년+ — *DORA Metrics* (Accelerate, Forsgren et al)
- *과학적 증거*: 배포 빈도 / Lead time / MTTR / 변경 실패율
- 고성과 팀은 *200배* 빠르게 배포 + *3배* 적게 실패

### 2019년+ — **Team Topologies** (Skelton, Pais)
- Stream-aligned / Enabling / Complicated-subsystem / Platform 팀
- *팀의 인지 부하* 가 *조직 설계의 1차 변수*

### 2020년+ — **Platform Engineering**
- DevOps 의 *피로* → 내부 개발자 플랫폼 (IDP)
- *Cognitive load* 줄이기

60년 흐름의 *방향*: *큰 단위·계획 중심* → *작은 단위·피드백 중심*. *부서별 사일로* → *팀의 자율·책임 균형*.

---

## 2. *변하는 것* — 도구·용어·관행

### 도구
- 버전 관리: CVS → SVN → **Git**
- CI: Hudson → Jenkins → CircleCI → **GitHub Actions**
- 이슈 트래킹: Trac → Jira → Linear → Notion
- 채팅: IRC → Skype → HipChat → Slack → Slack 대체
- 코드 리뷰: ad-hoc → Gerrit → GitHub PR → Graphite
- 배포: Capistrano → Chef/Puppet → Kubernetes → GitOps (ArgoCD/Flux)

### 용어
- *Agile* (2001) → *DevOps* (2009) → *SRE* (2016) → *Platform Engineering* (2020) → ?

매 5~10년마다 *새 단어* 가 나오고 *과거 용어* 가 빛바램. 단어는 *마케팅* 이지만 *실체* 는 같은 본질을 다르게 부른 것.

### 관행
- Pair Programming → 한동안 안 함 → AI 페어 (Copilot) 로 부활
- Daily Standup → 30분 → 15분 → async 텍스트
- Sprint Review → demo → product review → 비공식 채팅 update
- Retrospective → 매주 → 격주 → 분기

---

## 3. *변하지 않는 것* — 본질 5가지

### 3.1 짧은 피드백 루프

*Waterfall 의 12개월 피드백* vs *DevOps 의 12분 피드백*. 도구가 달라도 *짧은 피드백이 더 좋다* 는 명제는 *60년간 한 번도 뒤집힌 적 없다*.

근거: 사람의 *주의 폭* 은 한계가 있음. 12개월 전 결정의 *맥락* 을 기억하기 어려움. 12분 전 결정은 *고치기 쉬움*.

### 3.2 Conway's Law

> *"조직이 설계하는 시스템은 그 조직의 소통 구조를 반영한다"*
> — Melvin Conway, 1968

마이크로서비스·모놀리스·헥사고날·CQRS — 모두 *결국 조직 구조* 의 거울. Spotify 모델·Team Topologies 도 *Conway 의 응용*.

> 1968년의 통찰이 *2026년에도 그대로*.

### 3.3 신뢰·자율·책임

*Frederick Brooks (1975, Mythical Man-Month)* 부터 *Netflix Culture Deck (2009)* 까지, *Daniel Pink (2009, Drive)* 까지 — 동기부여의 *3대 요소* 는 *Autonomy / Mastery / Purpose*.

이게 *없으면* 어떤 방법론도 *형식만 남고 실체 없음*.

### 3.4 도메인 깊이

*Eric Evans (2003, DDD)* 의 핵심: *비즈니스 도메인을 깊이 이해하지 못하면 좋은 코드는 불가능*. Spring Boot · Rails · Django 어떤 스택을 써도 *도메인 모델링이 본질*.

AI 가 코드 작성 비용을 0 으로 만들수록 *도메인 깊이의 가치* 가 *상대적으로 커진다*.

### 3.5 사람 > 프로세스 > 도구

> *"People over process over tools"*

Agile Manifesto 의 첫 줄. 60년간 *이 우선순위가 뒤집혔던 적이 없음*. *좋은 사람 + 나쁜 프로세스* 가 *나쁜 사람 + 좋은 프로세스* 보다 *항상 낫다*.

---

## 4. *좋은 문화* 와 *훌륭한 문화* — 6가지 결정적 차이

| 차원 | 좋은 (Good) | 훌륭한 (Great) |
|---|---|---|
| **실패** | 비난 줄이려 노력 | *blameless postmortem* 으로 *학습 자산* 화 |
| **결정** | 자율 강조 | *작은 팀 (Two-Pizza)* + 명확한 책임 |
| **문서** | README 잘 적음 | *생각을 정련하는 글쓰기* (Amazon 6-pager) |
| **시간 지평** | 분기 OKR | *10년 후* 를 묻는 의사결정 |
| **소통** | Slack 활발 | *Async-first*, 회의 *50% 감소* |
| **개선** | Retrospective | *DORA 측정* + *원인 추적* |

좋은 문화는 *형태* 가 있다. 훌륭한 문화는 *형태 위에 본질* 이 있다. 차이는 *작아 보이지만 결과는 10배*.

---

## 5. 글로벌 기업 사례

### 5.1 Google — *Postmortem 의 표준*

Google SRE 가 만든 *Blameless Postmortem* 은 *훌륭한 문화의 결정체*. 장애 후 *"누구 잘못이냐"* 가 아니라 *"어떤 시스템이 이걸 가능하게 했나"* 를 묻는다.

핵심 원칙:
- *사람* 이 아니라 *시스템* 을 비판
- 모든 postmortem *공개* (팀 외부도 학습)
- *액션 아이템* 에 *책임자 명시* 후 추적

이게 *지속 가능한 학습 문화* 의 기반. *비난이 두려운 조직* 은 *작은 실수* 도 숨겨 *큰 사고* 로 키운다.

### 5.2 Amazon — *Working Backwards + 6-pager*

Amazon 의 *글쓰기 문화* — 회의 시작 *처음 20분* 동안 *6 페이지 메모를 침묵으로 읽음*. PowerPoint 금지.

이유: PowerPoint 는 *bullet point* 로 *논리의 비약* 을 숨김. 문장으로 적으면 *논리의 빈 곳* 이 드러남.

또 *Working Backwards*: 신제품 *기획 단계* 에 *이미 PR (Press Release) 작성*. 고객 입장에서 *이게 흥미로운가* 를 먼저 검증.

이 두 관행의 본질: *생각을 정련하는 강제 장치*. *좋은 문화* 는 *좋은 회의* 를 한다. *훌륭한 문화* 는 *회의를 줄인다*.

### 5.3 Netflix — *Freedom & Responsibility*

> "We hire fully formed adults" — Reed Hastings

Netflix Culture Deck (2009 공개, 1700만회 조회) 의 핵심:
- *과정 통제 없음* — 출퇴근 시간·휴가일수 *추적 안 함*
- *대신 결과로 평가* — 못 하면 *후한 퇴직금 + 즉시 이별*
- *Keeper Test*: "이 사람이 떠난다면 *말릴 것인가*? 아니라면 *지금 보내야*"

극단적이지만 *훌륭한 문화* 의 한 가지 답안. *자율* 의 대가는 *책임* — 둘은 *반드시 함께* 가야 한다.

### 5.4 GitHub — *Async-first Remote*

원격이 *기본*. 회의는 *예외*. 모든 결정은 *Issue / PR 에 기록*. *시차가 다른 팀원도 동등하게* 참여 가능.

핵심: *동기 (실시간) 소통* 은 *비용이 가장 큰 형태*. 좋은 문화는 *회의가 효율적*. 훌륭한 문화는 *회의 없이도 일이 진행*.

### 5.5 Basecamp / 37signals — *Shape Up + No Meeting*

*Sprint 안 함*. 대신 *Shape Up*:
- *Shaping*: 6주 단위 *문제 정의* (separation of concerns)
- *Betting Table*: 6주 동안 *어떤 베팅 (project) 을 할지* 결정
- *Build*: 6주 작업
- *Cool-down*: 2주 *과제 없는 회복 시간*

회의는 *극도로 제한*. *Hill Charts* 로 진행 상황을 *비동기 시각화*.

핵심: *효율을 추구하는* 게 아니라 *지속 가능성을 추구*. 이게 *좋은 문화 → 훌륭한 문화* 의 다른 한 축.

---

## 6. 한국 기업 사례

### 6.1 토스 (Toss) — *사일로 + 신뢰*

토스 페이먼츠·토스 증권 등 *Two-Pizza 사이즈의 사일로* 자율조직. 각 사일로는:
- *PO + 디자이너 + 개발자* 가 *한 팀*
- *예산·기술 스택·일정* 모두 *자율*
- *결과* 만 본부장에게 보고

빠른 의사결정 + *비즈니스 도메인 깊이* 가 *동시에* 잡힘. *훌륭한 문화의 한국적 변용*.

### 6.2 우아한형제들 (배민) — *우아한테크코스 + DDD*

기술적 *깊이* 에 투자. *우아한테크코스* (외부 교육), *우아한 콘퍼런스*, *기술 블로그* 의 *극도의 활성도*.

내부적으로 *Domain-Driven Design* 적극 도입. *주문·배달·정산* 의 도메인이 *코드와 일치하는* 구조.

이는 *Eric Evans 의 DDD* (변하지 않는 것 3.4) 를 *조직 차원에서 신앙처럼 운용* 한 사례.

### 6.3 라인 (LINE / LY Corp) — *글로벌 분산 팀*

도쿄·서울·하노이·자카르타·방콕 등에 *동시에 팀*. 모든 *PR / Issue / 결정* 이 *영어 + 일본어* 로 *비동기 기록*.

GitHub 의 *async-first* 를 *기업 차원에서* 운용. *시차 + 언어* 모두 다른데 *함께 일이 굴러감*.

### 6.4 카카오 / 네이버 — *대조되는 두 가지 답*

- **카카오**: 자율 강조 + *9 to 9 분위기*. 도전적 / 빠른 / 때로는 *번아웃*
- **네이버**: 보수적 안정 + *프로세스 중심*. 안전한 / 느린 / 때로는 *경직*

둘 다 *좋은 회사*. 그러나 *훌륭한 문화* 는 *그 둘의 균형* 에 가깝다.

### 6.5 작은 스타트업의 함정

*"우리는 애자일하니까 문서 안 적어요"* → 6개월 뒤 신입은 *맥락 없이 떠도는 결정* 사이에서 *번아웃*

좋은 문화는 *유연* 하다. 훌륭한 문화는 *유연성과 기록의 균형*. 작은 팀에서도 *Amazon 6-pager 의 본질 (생각을 글로 정련)* 은 유효.

---

## 7. *훌륭한 문화* 의 *6가지 진짜 시그널*

좋은 문화 = *눈에 보이는 형식 (Scrum, CI/CD, OKR)*. 훌륭한 문화 = *그 형식 뒤의 본질*.

다음 *6가지가 진짜* 시그널:

### 7.1 *나쁜 결정을 인정하는 회의*
좋은 회사도 *나쁜 결정* 을 한다. 훌륭한 회사는 *그걸 회의 안에서 인정* 하고 *공개적으로 학습 자산화* 한다. (Google postmortem, Amazon "we got it wrong" memos)

### 7.2 *시간 지평이 길다*
분기 OKR 만 추구하면 *6개월짜리 리팩토링* 이 안 됨. 훌륭한 문화는 *5년 후* 를 묻는 결정을 *정기적* 으로 한다.

### 7.3 *작은 팀 (≤ 8명) 을 고수한다*
Amazon 의 *Two-Pizza Team*. *팀이 커지면 조직 비용* 이 *지수적* 으로 증가. 훌륭한 문화는 *팀이 커지기 전에 분할*.

### 7.4 *글쓰기 문화*
회의 대신 *글*. *생각의 정련 도구* 로서. Slack 한 줄 vs 6-pager 의 *결정 품질 차이* 는 100배.

### 7.5 *실험의 안전성*
훌륭한 문화의 *심리적 안전성*. *작은 실험이 안전한 조직* 에서 *큰 혁신* 이 나온다. (Google's psychological safety study, Amy Edmondson)

### 7.6 *바깥의 도전자 환영*
좋은 회사는 *컨퍼런스 발표*. 훌륭한 회사는 *비판적 외부 의견* 을 *환영*. (Stripe 의 *내부 RFC 공개*, GitHub 의 *외부 contributor 우대*)

---

## 8. 결론 — *훌륭한 문화는 형식이 아니라 *질문의 종류**

### 좋은 문화는 *답* 을 한다
- Sprint 어떻게? → Scrum 으로
- 배포 어떻게? → CI/CD 로
- 문서 어떻게? → Notion 으로

### 훌륭한 문화는 *질문* 을 한다
- *왜* 우리는 매번 이걸 해야 하나?
- *지금 이 결정* 이 10년 뒤에도 좋을까?
- *우리가 모르고 있는 것* 은 무엇일까?

### 변하지 않는 5가지 *질문 형태*
1. 피드백은 *얼마나 짧은가*?
2. 팀은 *얼마나 자율적이고 책임을 지나*?
3. 도메인을 *얼마나 깊이* 아나?
4. 실패에서 *얼마나 배우나*?
5. *글로 생각을 정련* 하나?

이 5가지 *질문* 이 명확한 조직은 *어떤 방법론* 을 써도 *훌륭한 결과* 를 낸다. 반대로 *질문이 모호* 한 조직은 *최신 도구를 다 깔아도* 본질이 빈약하다.

### 마지막 — *도구가 답을 주지 않는다*
Jira·GitHub Copilot·ArgoCD·Datadog 가 *훌륭한 문화* 를 *만들어주지 않는다*. *훌륭한 사람들이 모여 좋은 질문을 하는 것* 이 먼저고, 도구는 *그 질문의 답을 가속* 시킬 뿐.

60년 전 *Conway* 가 본 것, 25년 전 *Agile Manifesto* 가 본 것, 17년 전 *Netflix Culture Deck* 이 본 것 — 모두 같은 한 문장:

> ***사람이 먼저이고, 그 사이의 신뢰가 본질이며, 도구는 도구일 뿐이다.***

다음 글에선 *DORA 4가지 메트릭* 의 *실제 측정 방법* 과 *개선 우선순위* 를 정리할 예정.
