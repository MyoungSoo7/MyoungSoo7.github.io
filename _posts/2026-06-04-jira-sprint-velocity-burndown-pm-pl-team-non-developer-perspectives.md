---
layout: post
title: "Jira 의 *5 핵심 키워드* — *Sprint · Story Point · Velocity · Burndown · Release Tracking* 을 *PM · PL · 팀원 · 비개발자* 가 *각자 다르게 *보는 법, 그리고 *4 명 팀의 *실전 *구성*"
date: 2026-06-04 04:00:00 +0900
categories: [process, project-management, agile]
tags: [jira, scrum, agile, sprint, story-point, velocity, burndown, release-tracking, project-management, atlassian]
---

> *''*Story Point 가 *시간이 *아니라고요? 그럼 *시간을 *어떻게 *추정해요?""*. *주니어 *백엔드가 *처음 *Jira 를 *마주칠 때 *가장 *자주 *던지는 *질문이다. *답하기는 *어렵지 *않다 — *''*Story Point 는 *상대적 *복잡도 일 뿐, *시간은 *Velocity 가 *알려준다""*. 하지만 *그 *답의 *진짜 *깊이는 *''*같은 *Jira 화면을 *PM 과 *PL 과 *팀원과 *비개발자가 *서로 *완전히 *다르게 *본다""* 는 *사실에 있다.
>
> 이 글은 *Jira 의 *5 가지 *핵심 *키워드 — **Sprint · Story Point · Velocity · Burndown · Release Tracking** — 를 *원리 부터 *풀고, 그것을 *4 개의 *역할 (PM · PL · 팀원 · 비개발자) 이 *각자 *어떤 *질문에 *답하기 위해* 보는지 *대조한 뒤, *마지막에 *''*PM 1 + PL 1 + 팀원 2""* 의 *작은 팀이 *Jira 를 *처음부터 *세팅 하는 *실전 *순서* 까지 *연결한다.

대상은 *''*Jira 에 *처음 *발 들이는 *백엔드 / 프론트 *개발자""*, *''*팀 *리드가 *되었는데 *툴부터 *어떻게 *세팅 해야 *할지 *막막한 *시니어""*, 그리고 *''*개발팀과 *대화 하려면 *적어도 *Burndown 정도는 *읽을 줄 *알아야 한다""* 는 *모든 *비개발자*.

---

## 1. *왜 *5 키워드인가*

Scrum / Agile 의 *어휘는 *수십 *개지만, *''*매일 *Jira 화면에서 *눈에 *띄는 5 가지""* 가 *결국 *전부를 *지탱한다*.

```
Sprint           ← 우리가 *언제까지 *무엇을 *약속했나
Story Point      ← 그 약속의 *크기를 *어떻게 *재나
Velocity         ← 우리가 *그 약속을 *얼마나 *지킬 수 *있나
Burndown         ← 약속을 *얼마나 *지키고 *있나
Release Tracking ← 약속들이 *합쳐서 *언제 *시장에 *나가나
```

*5 가지가 *연쇄 *질문* 이다. *Sprint 가 *없으면 *Story Point 가 *의미가 *없고, *Story Point 가 *없으면 *Velocity 가 *없고, *Velocity 가 *없으면 *Burndown 의 *이상선이 *없고, *Burndown 이 *없으면 *Release Tracking 이 *예측 *못 한다*.

---

## 2. *5 키워드 *깊이 *설명*

### 2.1 *Sprint* — *''*우리가 *2 주 안에 *완성하기로 *약속한 *작업 *묶음""*

```
Sprint 1 (1 ~ 14 일)
  ├─ Sprint Planning (Day 1, 1 시간)
  ├─ Daily Standup × 10 일 (매일 15 분)
  ├─ Sprint Review / Demo (Day 14, 1 시간)
  └─ Sprint Retrospective (Day 14, 45 분)
```

**왜 *고정 *기간 인가**:
- *''*마감이 *없는 *작업은 *끝나지 *않는다""* — Parkinson 의 *법칙
- *주기적 *피드백 — *고객·이해관계자가 *2 주마다 *진척 *확인
- *팀의 *지속 가능한 *속도 *측정 *가능

**왜 *2 주가 *표준 인가**:
- 1 주: *Planning 의 *오버헤드가 *작업 시간에 *비해 *크다
- 4 주: *피드백이 *너무 *늦다 — *2 주 *지난 *방향 *수정이 *2 주 더 *걸린다
- 2 주: *Planning *오버헤드 *허용 *가능 + *피드백 *충분히 *빠름

**고정 *원칙**:
> *''*Sprint 시작 *후 *추가 *작업 *금지""* — *긴급 *예외만 *허용, *그조차 *기존 *작업 *드롭과 *교환

**Jira 에서**:
- *Backlog 화면 → *''*Create Sprint""* → 기간 *설정 → *백로그에서 *드래그
- *Active *Sprint 는 *한 번에 *하나 *(스크럼 *기본)
- *Velocity 계산은 *''*완료된 *Sprint""* 로 만 *기준

### 2.2 *Story Point* — *''*작업의 *상대적 *복잡도, *시간이 *아님""*

**Fibonacci 의 *이유**:
```
1 → 2 → 3 → 5 → 8 → 13 → 21 → 40 → 100
```
*''*큰 수일수록 *불확실성이 *기하급수적""* — *''*5 와 *6 의 *차이는 *명확 X 지만 *5 와 *8 의 *차이는 *명확 O""*.

**해석 *예시** (팀마다 *조정):
| SP | 의미 |
|---|---|
| 1 | 단순 *수정 — 30 분 ~ 1 시간 |
| 2 | 작은 *기능 — 반나절 |
| 3 | 표준 *기능 — 하루 |
| 5 | 복잡한 *기능 — 2 ~ 3 일 |
| 8 | *''*Story 단위 *최대""* — 일주일 *(분할 *고려)* |
| 13 | *''*너무 큼 — 반드시 *분할""* |
| 21+ | Epic 으로 *승격 |

**왜 *시간이 *아닌가**:
1. *사람마다 *속도 *다름* — A 의 *3 일이 *B 의 *1 일
2. *복잡도는 *상대적이라 *비교 *쉬움* — *''*이 *Story 는 *저거랑 *비슷한가?""*
3. *추정 *부담 ↓* — 정확한 *시간 *맞히기는 *불가능, *대략적 *크기는 *가능

**Planning Poker — *집단 *추정 *기법**:
1. PM 또는 PL 이 *Story 읽기
2. 팀원 *전원이 *Fibonacci *카드 *동시 *공개
3. 가장 *높은 / 낮은 *추정자에게 *''*왜?""* 질문
4. 다시 *카드 *공개 → 보통 *2 ~ 3 회로 *수렴

**잘 *추정된 *Story 의 *3 가지 *조건**:
- *Acceptance Criteria* 가 *명확
- *기술적 *''*불명확 영역""* 이 *드러남
- *팀 *전체가 *''*아 *이건 *대략 X 점""* *공감

### 2.3 *Velocity* — *''*우리가 *Sprint 당 *평균 *몇 점 *완료 하는가""*

```
Sprint  Completed
─────────────────
   1       23 pt
   2       28 pt
   3       21 pt
─────────────────
 Velocity  24 pt/sprint  (최근 3 평균)
```

**Velocity 의 *2 가지 *용도**:

#### 용도 1 — *다음 *Sprint *Capacity 추정*
*''*이번 *Sprint 에 *24 pt 이상 *뽑지 *말자""*. *과욕 = *미완성 = *번아웃*.

#### 용도 2 — *Release 예측*
```
백로그 *총 *200 pt
Velocity 24 pt/sprint
─────────────────────
200 / 24 ≈ 8 Sprint ≈ 16 주 ≈ 4 개월
```

*PM 이 *이해관계자에게 *''*Q3 안에 *완성""* 같은 *약속을 *할 때 *근거.

**Velocity 의 *3 가지 *함정**:

1. **KPI 로 *쓰면 *팀이 *부풀린다** — *''*우리 팀 *Velocity 50 pt!""* 라고 *자랑하려고 *Story Point 를 *부풀리기 *시작
2. **새 팀은 *Velocity 가 *안정될 때까지 *3 ~ 5 *Sprint 필요** — 그 *전엔 *예측치가 *신뢰 X
3. **팀 *구성 *바뀌면 *Velocity 도 *바뀐다** — 이전 *Velocity 그대로 *못 *씀

> **Velocity 는 *''*예측용""* 이지 *''*평가용""* 이 *아니다*. 이 *한 줄을 *PM·PL·경영진이 *모두 *공유해야 *Velocity 가 *건강하게 *작동.

### 2.4 *Burndown* — *''*Sprint 의 *남은 *작업 *시간별 *감소""*

```
Story Points (남은)
30 |\
   | \   ← 이상선 (직선, 매일 균등 감소)
20 |  \●
   |    \●  ← 실제 (계단식)
10 |      \●
   |        \●
 0 ●─────────●
   D1  ...  D10
```

**해석**:
- **이상선 *위** (실제 > 이상): 늦어짐 *위험 — 조치 *필요
- **이상선 *아래** (실제 < 이상): 잘 *진행 중
- **수평선 *지속** (3 일 *연속 *변화 X): *블로커 *존재 *— 즉시 *해결

**Daily *Standup 에서 *Burndown 의 *역할**:
- *PL: *''*이틀째 *수평이야. *무슨 *블로커야?""*
- *팀원: *''*X 가 *Y 에 *의존하는데 *Y 의 *API 명세가 *늦어요""*
- *PM: *''*외부 *팀에 *명세 *요청 *내가 *오늘 *할게""*

**Burndown 이 *항상 *이상선 *근처면**:
- 좋은 *팀처럼 *보일 수 *있지만 *실제론 *''*Story Point 를 *작게 *잡았다""* 의 *증거일 수도
- 또는 *''*매일 *조금씩 *균등하게 *완료된다""* 의 *현실적 *증거 — 보통 *후자

### 2.5 *Release Tracking* — *''*특정 *기능 *묶음의 *완성도 *추적""*

Jira 의 *3 단계 *계층:

```
Release (Version)  ← 출시 *단위 (v1.0, v1.1)
   │
   ├─ Epic         ← 큰 기능 *묶음 (예: *''*배차 시스템""*)
   │    │
   │    ├─ Story   ← 사용자 *가치 *단위 (예: *''*기사가 *배송 *수락""*)
   │    │    │
   │    │    └─ Sub-task  ← 기술 분해 (예: *''*REST API 구현""*)
   │    │
   │    └─ Task    ← 기술 작업 (예: *''*DB 마이그레이션""*)
   │
   └─ ...
```

**Release Burndown** — *여러 *Sprint 에 *걸친 *Epic 의 *완성도 *그래프

**Roadmap 뷰** — Epic *별 *타임라인, *''*이번 *분기 *어디까지?""* 에 *답.

---

## 3. *4 관점 — *같은 *Jira 를 *4 가지로 *본다*

같은 *Sprint Board, 같은 *Burndown 차트라도 *PM · PL · 팀원 · 비개발자가 *각자 *완전히 *다른 *질문에 *답하기 위해 *본다.

### 3.1 *PM (Project Manager) — *''*일정·리스크·이해관계자""*

**주된 *질문**:
- 이번 *Sprint 가 *목표 *달성 가능 한가?
- 다음 *Release 가 *언제 *나오나?
- 외부 *요청을 *어디에 *넣어야 하나?

**가장 *자주 *보는 *화면**:
1. **Roadmap (Plan tab)** — Epic 별 *타임라인, *이해관계자 *공유용
2. **Release Burndown** — *남은 *Story Point 의 *시간별 *추이
3. **Velocity Chart** — *팀 *capacity 예측
4. **Sprint Burndown** — *현재 *Sprint 위험도

**의사결정 *예시**:
- *''*Velocity 24 pt × 4 Sprint = 96 pt 가능* → *우선순위 *Top 96 pt 만 *이번 *Release 에 *포함""*
- *''*Burndown *3 일 *연속 *수평 → *다른 *팀에 *지원 *요청""*
- *''*외부 고객이 *추가 *요청 → *기존 *작업 *드롭 *또는 *다음 *Sprint 로 *밀기""*

**PM 의 *Jira *활용 *핵심**:
- *Filter / JQL* 로 *''*이번 *분기 *Release 에 *들어갈 *Story""* *추적
- *Custom Dashboard* 로 *이해관계자 *공유용 *요약 *보기 *구성
- *Confluence 와 *연동해 *회의록·결정 사항을 *Story 에 *링크

### 3.2 *PL (Project Lead / Tech Lead) — *''*기술 *결정·코드 *품질·일정 *가능성""*

**주된 *질문**:
- Story 의 *기술 *분해가 *정확한가?
- 한 *팀원에게 *작업이 *몰리고 *있지 않나?
- 이 *Story 가 *진짜 *Sprint 안에 *끝날 *것인가?

**가장 *자주 *보는 *화면**:
1. **Sprint Backlog** — 작업 *세부 *내용
2. **개별 *이슈 *상세** — 기술 *설계·댓글
3. **Cumulative Flow Diagram** — *In Progress 가 *쌓이는지 (WIP 한도 위반)
4. **개별 *팀원 *작업 *분포** — 한 *사람에게 *집중되는지

**의사결정 *예시**:
- *''*이 *Story 는 *5 pt 라더니 *실제로는 *13 pt 같음 — 분할 *필요""*
- *''*A 가 *모든 *백엔드 *작업 *맡음 → B 에게 *분산""*
- *''*Story X 는 *Story Y 에 *의존 → Y 먼저 *완료""*

**PL 의 *Jira *활용 *핵심**:
- *Sub-task* 로 *기술 *분해 — Story 1 = Backend 3 task + Frontend 2 task
- *Linked Issues* 로 *의존성 *명시 — `blocks`, `is blocked by`, `relates to`
- *Component* 로 *영역 *분류 — `api`, `db`, `infra`

### 3.3 *팀원 (Developer) — *''*내 *작업·내 *블로커·협업""*

**주된 *질문**:
- 오늘 *내가 *해야 할 *것은?
- 내가 *막혀 있는 *것은?
- 다른 *팀원의 *PR 리뷰는?

**가장 *자주 *보는 *화면**:
1. **My Open Issues** — 내가 *지금 *해야 할 것
2. **Active Sprint Board** — 칼럼 (To Do / In Progress / Review / Done)
3. **개별 *이슈** (assigned to me)
4. **Notifications** — 나에게 *멘션 *온 *댓글

**Daily Standup *3 가지 *답변**:
1. *''*어제 *무엇""* — 어제 *Done 칸 *옮긴 *티켓
2. *''*오늘 *무엇""* — 오늘 *In Progress 칸 *옮길 *티켓
3. *''*블로커""* — *어떤 *티켓이 *왜 *멈춰 있나

**팀원의 *Jira *활용 *핵심**:
- *작업 *시작 시* → 상태 *''*In Progress""* 로 *옮김 + assignee = 본인
- *PR 올렸을 때* → *''*In Review""* 로 *옮김 + PR 링크 *댓글
- *블로커 *있으면* → 즉시 *댓글 + Linked Issue 또는 @멘션
- *작업 *예상보다 *훨씬 *커짐* → 즉시 *PL 에 *알림 + sub-task 분할

> **팀원의 *티켓 *위생 *3 가지**: ①상태를 *''*실제""* 와 *일치, ②변경 시 *댓글 *남김, ③막히면 *즉시 *공유.

### 3.4 *비개발자 (PO / Sales / CS / 경영진) — *''*결과·예측·진척""*

**주된 *질문**:
- 이번 *분기 *목표 *기능 *언제 *나오나?
- 고객이 *요청한 *기능 *상태는?
- 전체 *로드맵 *어디까지 *왔나?

**가장 *자주 *보는 *화면**:
1. **Dashboard** — PM 이 *공유한 *요약 보드
2. **Release Hub** — *''*우리 *기능 *언제 *나옴?""* 답
3. **Issue Filter** — *''*고객 X 가 *요청한 Y 의 *상태?""*

**보는 *목적**:
- 영업: *''*다음 *분기 *고객 *제안에 *이 *기능 *포함 *가능?""*
- CS: *''*이 *버그 *언제 *수정?""*
- 경영진: *''*전체 *로드맵 *얼마나 *진행됨?""*

**비개발자에게 *보여줄 *것**:
- *세부 *기술 *티켓 *X (오해 *유발)
- *Epic + Release 단위 *진행률 ✓
- *Roadmap (간트 *유사 *뷰) ✓
- *''*이번 *분기 *목표 *대비""* 진척도 ✓

> **PM 의 *책임**: *비개발자가 *기술 *티켓을 *보고 *''*왜 *이렇게 *늦어?""* 라고 *오해 *못 *하도록 *Epic·Release 뷰만 *공유.

---

## 4. *4 관점의 *대조 *표*

| | PM | PL | 팀원 | 비개발자 |
|---|---|---|---|---|
| 핵심 질문 | 일정? | 기술 위험? | 내 작업? | 언제 나옴? |
| 주 화면 | Roadmap / Release Burndown | Sprint Backlog / CFD | My Issues / Sprint Board | Dashboard / Release Hub |
| 시간 단위 | 분기 / 월 | 주 / Sprint | 일 / 시간 | 분기 |
| 결정 권한 | 우선순위 / Release | 기술 / 분해 | 작업 방법 | 요청 / 거부 |
| 자주 쓰는 *기능 | Filter / JQL / Custom Dashboard | Sub-task / Linked Issues / Component | Comment / Status Drag | Release Hub / Filter |
| 위험 *신호 | Burndown 이상선 *벗어남 | In Progress 가 *쌓임 | 내 *블로커 | Release 일정 *밀림 |

---

## 5. *실전 — *4 명 팀의 *Jira *세팅 *(PM 1 + PL 1 + 팀원 2)*

이제 *원리에서 *실전으로*. *작은 팀이 *Jira 를 *처음 *세팅 하는 *완전한 *흐름.

### 5.1 *팀 *구성 *예시*

가정 *상황: 사내 *물류 *플랫폼 *(LMS — Logistics Management System) 의 *백엔드 *팀.

| 역할 | 호칭 | 책임 |
|---|---|---|
| **PM** | Lim_PM | 일정·우선순위·이해관계자, Roadmap |
| **PL** | Lim_PL | 기술 결정·코드 리뷰·아키텍처 |
| **팀원 1 (Backend)** | Lim_BE | Spring / JPA / 도메인 |
| **팀원 2 (Frontend / DevOps)** | Lim_FE | UI / K8s 배포 |

### 5.2 *프로젝트 *생성*

```
Jira → Create Project
- 템플릿: Scrum (Kanban 도 가능, 우리는 Sprint 쓸 거니까 Scrum)
- 이름: Logistic LMS
- 키: LLMS (이슈 ID: LLMS-1, LLMS-2, ...)
- Access: Private
```

### 5.3 *Issue Type *5 종으로 *충분*

- **Epic** (Phase 단위) — 색: 보라
- **Story** (사용자 가치) — 색: 초록
- **Task** (기술 작업) — 색: 파랑
- **Bug** (결함) — 색: 빨강
- **Sub-task** (Story / Task 분해) — 색: 회색

### 5.4 *Workflow 설정*

```
[To Do]
   ↓ (작업 시작)
[In Progress]
   ↓ (PR 올림)
[In Review]
   ↓ (PR merge)
[QA] ← 선택, 작은 팀은 *생략 *가능
   ↓
[Done]

(언제든) → [Blocked] ← 막힐 때
```

> **권장**: *''*Blocked""* 상태를 *반드시 *추가. *Daily standup 에서 *빨간 깃발 *역할.

### 5.5 *Component / Label 정의*

```
Components (영역):
  - api          (REST 컨트롤러)
  - domain       (Aggregate / 도메인 로직)
  - persistence  (JPA / Flyway)
  - outbox       (이벤트 발행)
  - dispatch     (배차)
  - driver-app   (기사 앱)
  - infra        (K8s / ArgoCD / GHA)
  - docs

Labels (속성 / 분류):
  - phase-1, phase-2, phase-3 ...
  - tech-debt
  - blocker
  - need-design
  - external-request
```

### 5.6 *Epic 정의 — *Roadmap 의 *골격*

```
LLMS-EPIC-1: [Phase 1] Shipment + Outbox        ✅ Done
LLMS-EPIC-2: [Phase 2] Dispatch + Driver/Vehicle ✅ Done
LLMS-EPIC-3: [Phase 3] Driver App + PoD          ✅ Done
LLMS-EPIC-4: [Phase 4] Kafka 어댑터              ✅ Done
LLMS-EPIC-5: [Phase 5] Route + Cost              ✅ Done
LLMS-EPIC-6: K8s 배포 자동화 (GitOps)            ✅ Done
LLMS-EPIC-7: [차기] OMS 실제 연동 + Webhook
LLMS-EPIC-8: [차기] Frontend 관제 대시보드
LLMS-EPIC-9: [차기] 모바일 기사 앱 (React Native)
LLMS-EPIC-10: [차기] Observability (Prometheus + Grafana)
```

### 5.7 *Sprint 1 — *백로그 *예시*

```
[LLMS-EPIC-7] OMS 실제 연동 + Webhook
├── [Story] LLMS-12: OMS 가 *POST /shipments 호출 시 *받아 *DB 저장
│   Acceptance:
│     ✓ 동일 externalReference → 기존 ID 반환 (멱등)
│     ✓ 필수 필드 누락 → 400 + 검증 에러
│     ✓ /actuator/health 200
│   Story Points: 3
│   Component: api, persistence
│   Assignee: Lim_BE
│
├── [Story] LLMS-13: Webhook 으로 *shipment.status_changed 발행
│   Acceptance:
│     ✓ 상태 변경 시 outbox 에 *PENDING 행 *추가
│     ✓ 1 초 안에 *webhook URL 로 *POST 전송
│     ✓ 4xx 응답 시 5 회 재시도 후 FAILED
│   Story Points: 5
│   Component: outbox
│   Assignee: Lim_BE
│
├── [Task] LLMS-14: webhook.site 등록 + 환경변수 *세팅
│   Story Points: 1
│   Component: infra
│   Assignee: Lim_FE
│
└── [Task] LLMS-15: 통합 테스트 시나리오 *작성 (Postman)
    Story Points: 2
    Component: docs
    Assignee: Lim_PL
```

### 5.8 *Sprint Planning *(1 시간)*

1. **PM**: *''*이번 *Sprint 목표 = *OMS 연동 *완성 + *외부 *데모 *가능""*
2. **PL**: 기술 *위험 *공유 — *''*Webhook *재시도 *로직이 *시간 *오래 *걸릴 수 있음""*
3. **팀원**: Story Point *추정 (Planning Poker)
4. **Capacity 확인** — 팀원 2 × 8 일 = 16 공수 ≈ 20 ~ 25 pt 추정

**Sprint Backlog (예)**:

| ID | 제목 | SP | Assignee | 상태 |
|---|---|---|---|---|
| LLMS-12 | OMS POST /shipments | 3 | BE | To Do |
| LLMS-13 | Webhook 발행 | 5 | BE | To Do |
| LLMS-14 | webhook.site 세팅 | 1 | FE | To Do |
| LLMS-15 | Postman 시나리오 | 2 | PL | To Do |
| LLMS-16 | Frontend 대시보드 PoC | 8 | FE | To Do |
| LLMS-17 | 운영 *문서화 | 2 | PL | To Do |
| **합계** | | **21** | | |

### 5.9 *Active Sprint Board*

```
┌───────┬────────────┬─────────┬─────┬──────┬──────┐
│ To Do │ In Progress│ In Review│ QA  │Block │ Done │
└───────┴────────────┴─────────┴─────┴──────┴──────┘
```

**WIP 한도**:
- **In Progress**: 팀원 *수 × 2 = *최대 4 (PL 도 *코드 *쓰면 *6)
- **In Review**: 무제한 — *빨리 *리뷰하라는 *신호

### 5.10 *Daily Standup *(15 분, 9:00)*

각자 *순서대로*:
- *''*어제 *뭐 했어""* (이슈 ID 언급)
- *''*오늘 *뭐 할 거""*
- *''*막힌 *것 *있어""*

**PL 의 *역할**: *''*Burndown 봤는데 *2 일째 *수평 — *원인 *공유""*
**PM 의 *역할**: *''*외부 *요청 *들어왔는데 *다음 *Sprint 로 *밀 *수 있나""*

### 5.11 *대시보드 *구성 *(PM 용)*

```
대시보드 1: "Sprint 1 — OMS 연동"
  - Sprint Burndown (큰 그래프)
  - Issues by Assignee (파이)
  - Recently Updated Issues (목록)
  - Blocked Issues (필터)

대시보드 2: "Release v1.0 Roadmap"
  - Release Burndown
  - Epic Progress Bar
  - Created vs Resolved (7 일)
  - Velocity Chart (지난 3 Sprint)
```

### 5.12 *역할별 *하루 *루틴*

#### **PM 의 *하루**:
```
09:00  Daily standup
09:20  Sprint Burndown 확인 → 위험 시 PL 과 논의
10:00  외부 *이해관계자에게 *Release Hub *공유
14:00  새 요청 → 백로그에 *Story 추가, *우선순위 *결정
17:00  내일 *blocker 정리
```

#### **PL 의 *하루**:
```
09:00  Daily standup
09:30  PR 리뷰 — *Jira 의 *In Review 칼럼 → PR 링크 *따라가기
11:00  새 Story 의 *기술 *분해 → Sub-task 생성
14:00  팀원 *페어 *프로그래밍
16:00  Architecture *결정 → Confluence 또는 ADR 작성
17:00  내일 *예상 *블로커 *점검
```

#### **팀원의 *하루**:
```
09:00  Daily standup
09:15  My Issues → 오늘 *작업 *티켓 *''*In Progress""*
12:00  티켓 *댓글로 *진행 *공유
15:00  PR 올림 → 티켓 상태 *''*In Review""* + PR URL 댓글
16:00  다른 *팀원 *PR 리뷰
17:00  내일 *작업 *티켓 *예약
```

#### **비개발자의 *하루**:
```
주 1 회  Sprint Demo 참관
필요 시  Release Hub 으로 *진척도 확인
요청 시  Jira 댓글로 *질문 (개발자 *시간 *방해 X)
```

### 5.13 *Sprint Review / Retrospective*

**Sprint Review (1 시간, 데모)**:
- 완료된 *Story *데모 (PM + 이해관계자)
- *''*다음 *Sprint *우선순위는?""*

**Retrospective (45 분, 팀만)**:
- 잘된 것 (**Keep**)
- 불만 (**Stop**)
- 시도해볼 것 (**Try**)
- → 다음 *Sprint 에 *액션 *반영

---

## 6. *Atlassian 툴 *조합*

- **Jira** — 이슈 / Sprint / Roadmap
- **Confluence** — 기획서 / ADR / 회의록 (Story 의 *Acceptance 가 *복잡 *경우)
- **Bitbucket / GitHub** — PR 자동 *링크 (LLMS-12 *언급 *시 *티켓에 *자동 댓글)
- **OpsGenie / PagerDuty** — *Production 인시던트 → Jira 티켓 자동 생성

> **소규모 팀 (5 명 이하)**: Jira *단독으로 *충분.
> **중규모 (10 ~ 50 명)**: Jira + Confluence + Bitbucket.
> **대규모 (50 명+)**: 위 + OpsGenie + Power BI / Tableau 외부 *시각화.

---

## 7. *흔히 *빠지는 *함정 *5 개*

### 7.1 *''*Story Point = *시간""* 환상*
- *''*1 SP = 1 시간""* 같은 *고정 *환산 *금지
- 팀에게 *반복 *교육 *필요

### 7.2 *Velocity 를 *KPI 로 *쓰기*
- *''*우리 팀 *Velocity 50 pt!""* 자랑 → *부풀림 *시작
- *''*Velocity 평가 *X, 예측 *O""* 원칙 *고수

### 7.3 *WIP 한도 *없음*
- *In Progress 가 *팀원 *수 *× 5 쌓이면 *''*Sprint 끝나도 *완성 *X""*
- WIP 한도 = *팀원 수 × 1.5 ~ 2 가 *경험적 *최적

### 7.4 *Blocker *공유 *늦음*
- *''*혼자 *3 일 *고민""* — 그 3 일 동안 *다른 작업이 *연쇄 *지연
- *''*1 시간 *막히면 *공유""* 의 *팀 *문화

### 7.5 *Retrospective 의 *액션이 *그냥 *사라짐*
- *''*다음 *Sprint 에 *XYZ 개선하자""* → 다음 Sprint 에 *아무도 *기억 *X
- Retrospective *액션을 *반드시 *다음 *Sprint 의 *Task 로 *등록

---

## 8. *정리 — *Jira 의 *진짜 *교훈*

> **''*Jira 는 *도구일 뿐이다 — *그 도구 *위에 *얹는 *팀의 *어휘와 *문화가 *진짜 *생산성을 *만든다.""**

5 키워드는 *''*같은 *어휘를 *모두가 *공유""* 하기 위한 *언어다*. *Sprint 가 *''*우리의 *약속""*, *Story Point 가 *''*약속의 *크기""*, *Velocity 가 *''*약속 *지킬 *능력""*, *Burndown 이 *''*지키고 있나 점검""*, *Release Tracking 이 *''*약속들 *합쳐 *언제 *시장에""* 다.

4 관점은 *''*같은 *언어를 *각자 *다른 *질문에 *답하기 위해 *읽는""* 방법이다. *PM 은 *일정, *PL 은 *기술, *팀원은 *내 작업, *비개발자는 *결과를 *본다.

실전 *세팅은 *''*도구를 *세팅 하기 *전에 *팀의 *약속을 *세팅""* 하는 *작업이다. *Workflow 결정 *전에 *''*우리 팀의 *Done 의 *정의가 *무엇인가?""* 가 *먼저고, *Story Point *기준 결정 *전에 *''*우리에게 *1 SP 가 *무엇인가?""* 가 *먼저다.

> **마지막 *한 *문장**:
>
> *''*Jira 는 *팀을 *관리하지 *않는다 — *팀의 *약속을 *기억할 뿐이다*. *기억할 *약속이 *없으면 *Jira 는 *비어 *있고, *너무 많으면 *Jira 가 *짐이 *된다*. *적절한 *약속의 *수와 *크기를 *찾는 것이 *결국 *Sprint 운영의 *예술이다.""*

---

## 더 읽으면 *좋은 *자료

- *Mike Cohn*, **Agile Estimating and Planning** (2005) — Story Point / Velocity 의 *고전
- *Kenneth Rubin*, **Essential Scrum** (2012) — Scrum 의 *완전한 *교과서
- *Atlassian University* — Jira *공식 *튜토리얼 (무료)
- *Jeff Sutherland*, **Scrum: The Art of Doing Twice the Work in Half the Time** (2014) — Scrum 창시자의 *원전
- *Marty Cagan*, **Inspired** (2017) — Product 관점 의 *Agile
- *Will Larson*, **An Elegant Puzzle** — *조직 운영의 *실무 (PM / PL 관점)
- *우아한형제들 *기술 블로그*, *''*우아한 *Sprint 운영기""* — *국내 *케이스 *스터디
