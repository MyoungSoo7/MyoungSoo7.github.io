---
layout: post
title: "코드 리뷰와 애자일은 어디로 가나 — Claude/Codex 가 도래한 시점에 *기존 개발 리드 가치의 하락*, 그리고 AI Agent 오케스트레이션·아키텍처 설계로 옮겨가는 미래"
date: 2026-05-29 03:10:00 +0900
categories: [engineering, leadership, ai]
tags: [code-review, agile, scrum, claude-code, codex, copilot-workspace, cursor, ai-agent, orchestration, architecture, tech-lead]
---

전통적인 개발 리드의 *핵심 일과* 두 가지:

1. **코드 리뷰** — 주니어/시니어 코드를 검토하고 *피드백*
2. **애자일 의례** — Daily standup, Sprint planning, Retrospective, Story 분해

이 둘이 *기술 리더십의 본질* 이라고 학습돼 왔다. 그런데 2024-2026 년 사이 등장한 *AI Agent* (Claude Code, OpenAI Codex / Copilot Workspace, Cursor, Devin) 가 *코드 리뷰의 절반* 과 *애자일의 의례성* 을 *집어삼키고 있다*.

이 글은 *실제 사례* 로 그 변화를 비교분석하고, *개발 리드의 미래 좌표* — AI Agent 오케스트레이션 + 전체 아키텍처 설계 — 로 옮겨가는 방향을 고찰한다.

> 이 글은 [개발 리드 30 년 변천사 + AI 시대]({% post_url 2026-05-29-engineering-leadership-evolution-overengineering-ai-era %}) 의 *코드 리뷰 / 애자일 / 오케스트레이션* 측면 심화편.

---

## TL;DR

| 영역 | 2020 의 리드 가치 | 2026 의 변화 |
|---|---|---|
| **코드 스타일 / 컨벤션 리뷰** | 매일 30분 | ⬇️ AI 가 PR 시점 자동 — 리드 *완전 면제* |
| **버그 / 안티패턴 발견** | 시니어의 *눈* 이 핵심 | ⬇️ AI 1차 + 사람 2차. 사람 시간 70% 절감 |
| **아키텍처 영향 검토** | 리드의 *판단* | ➡️ *여전히 사람 중심*. AI 는 *조언* |
| **도메인 일관성 검증** | 리드의 *기억* | ➡️ AI 가 *컨텍스트* 어느 정도 봐도 *진짜 컨텍스트* 는 사람 |
| **Daily Standup** | 30분 *현재 상태 동기화* | ⬇️ Slack bot + agent log 가 자동 |
| **Sprint Planning** | 4시간 / 격주 | ➡️ *story 분해* AI 자동, *우선순위* 는 사람 |
| **Retrospective** | 정성적 회고 | ➡️ AI 가 metric 분석 보조, *문화* 는 사람 |
| **AI Agent 오케스트레이션** (NEW) | 없음 | ⬆️ *새 핵심 책무*. 리드의 주 업무 |
| **전체 시스템 아키텍처** | 일부 | ⬆️ *비중 폭증*. AI 가 못 하는 영역 |

**핵심 결론:** 코드 리뷰 / 애자일은 *사라지지 않지만 의례성 50% 가 AI 에 흡수*. 리드의 시간은 *AI Agent 의 권한 경계 설계 + 전체 시스템 아키텍처* 로 *재배분*.

---

## 1. 전통 코드 리뷰 — *3 가지 책무* 의 분해

### 1.1 코드 리뷰가 *해왔던* 일

전통적 리드의 코드 리뷰는 *세 책무가 묶여* 있었다:

**① 표면적 검사 — 스타일 / 컨벤션 / lint 위반**
- "변수명이 camelCase 아님", "import 정렬 안 됨", "if/else 보다 early return"
- *낮은 가치 + 높은 빈도*. 리드 시간 30% 소요

**② 구조적 검사 — 안티패턴 / 버그 / 보안**
- "N+1 query 있음", "null 처리 누락", "SQL injection 가능"
- *중간 가치 + 중간 빈도*. 리드 시간 40% 소요

**③ 시스템적 검사 — 아키텍처 영향 / 도메인 일관성**
- "이건 Bounded Context 경계 침범", "이 변경이 다른 5 개 서비스 영향", "이 패턴은 우리 ADR-0042 와 모순"
- *높은 가치 + 낮은 빈도*. 리드 시간 30% 소요

### 1.2 AI 가 *흡수* 한 부분

**① 표면적 검사 — 90% 자동화**

```yaml
# .github/workflows/lint.yml
- name: Lint check
  run: ./gradlew spotlessCheck checkstyleMain
- name: AI review
  uses: anthropics/claude-review@v1   # 가상의 액션
  with:
    style: opinionated
```

Spotless / Checkstyle + AI 자동 코멘트가 *대부분의 표면 리뷰* 흡수. 리드가 "변수명" 코멘트 다는 일 *0*.

**② 구조적 검사 — 70% 자동화**

```
AI 가 PR 자동 분석:
"⚠️ OrderService.findOrders() 에서 N+1 발생 가능. 31 라인의 .getUser() 호출이 lazy loading.
 → @EntityGraph 또는 JOIN FETCH 권장."

"⚠️ 33 라인 raw SQL 에 사용자 입력 직접 보간. SQL injection 위험. ?-binding 사용 권장."
```

Claude Code / Codex 가 *PR 시점에 자동 코멘트*. 리드는 *AI 가 놓친 30%* 만 확인.

**③ 시스템적 검사 — 10-20% 정도만 자동화**

이게 *여전히 사람의 영역*. 이유:
- *전체 시스템 컨텍스트* 는 AI 의 컨텍스트 window 초과
- *ADR / 도메인 결정의 *왜*** 는 *암묵지*
- *팀의 기술 부채 패턴* 은 *오래 본 사람만* 안다

### 1.3 *실제 사례 — settlement 의 PR 리뷰 변화*

**2024 년 (AI 없음):**
- 평균 PR 리뷰 시간: *45 분*
- 평균 코멘트 수: *18 개*
- 18 개 분포: 표면 8 / 구조 7 / 시스템 3

**2026 년 (Claude Code Auto-Review 도입 후):**
- 평균 PR 리뷰 시간: *13 분* (-71%)
- 사람 리드 코멘트 수: *5 개* (시스템 3 + 구조 2)
- AI 자동 코멘트: *15 개* (표면 8 + 구조 7)

→ 리드의 *코드 리뷰 시간 71% 감소*. 그 시간을 *어디로* 옮길 것인가가 *새 질문*.

---

## 2. 애자일 — *의례 vs 본질*

### 2.1 애자일이 *원래 추구했던 것*

2001 년 Agile Manifesto:
- *개인과 상호작용* > 프로세스와 도구
- *작동하는 소프트웨어* > 포괄적 문서
- *고객 협력* > 계약 협상
- *변화에 대응* > 계획을 따름

핵심: **빠른 피드백 루프** + **자율적 팀** + **변화 대응**.

### 2.2 *현실의 의례화*

20 년이 지나며 애자일은 *의례화* 됐다:

- **Daily Standup 15분** — *세 질문* (어제 한 일 / 오늘 할 일 / 블로커) 의 *형식적 반복*
- **Sprint Planning 4시간** — *velocity 측정용 estimation 게임*
- **Sprint Review** — *데모* 라기보단 *보고*
- **Retrospective** — *Mad/Sad/Glad 포스트잇* 반복, *진짜 개선* 은 드뭄

원래 *작동하는 소프트웨어 + 빠른 피드백* 을 위한 도구였는데, *프로세스 자체가 목적* 이 됨.

### 2.3 AI 시대의 *애자일 의례 흡수*

**Daily Standup**:
- *팀 채팅 봇 (Slack/Teams)* 이 매일 아침 *각자에게 비동기 질문*
- *Linear / Jira 진행 상태 자동 집계*
- *코드 PR 상태, CI 결과, 어제 배포 결과* 자동 요약
- 사람 모임 → *주 1 회* 또는 *비동기*

**Sprint Planning**:
- *Issue 의 story 분해* — AI 가 *1 차 안* 작성
- *Estimation* — AI 가 *비슷한 옛 issue* 기반 자동 추정
- 사람 — *우선순위 결정 + AI 추정 검증*

**Sprint Review**:
- *데모 영상 / 스크린샷 + change log* AI 자동 생성
- 사람 — *비즈니스 가치 / 다음 방향* 토론

**Retrospective**:
- *DORA metrics (Lead time, Deployment frequency, MTTR, Change failure rate)* 자동 집계
- *AI 가 패턴 분석* — "지난 4 스프린트에서 PR review 대기 시간이 *50% 증가*"
- 사람 — *팀 감정 / 문화 / 합의* 영역

### 2.4 *실제 사례 — lemuel-xr 의 애자일 의례 변형*

**2024 년 (전통적 Scrum):**
- Daily Standup 15분 × 5일 = 75분/주
- Sprint Planning 4시간 / 격주
- Retrospective 1시간 / 격주
- 합계: *주당 약 6 시간* — 의례에 *팀 전체 시간 × 6*

**2026 년 (AI Agent 보조):**
- Async Slack standup — *각자 5 분*
- Sprint Planning — *AI 가 1 차 안*, 사람 확인 *45 분*
- Retrospective — *AI 가 metric + PR 데이터 분석 보고서*, 사람 토론 *45 분*
- 합계: *주당 약 2 시간* — *4 시간 절약*

→ 그 *4 시간* 을 *진짜 일* 에. *애자일의 본질* 은 *오히려 강화* 됨.

---

## 3. *코드 리뷰의 가치 하락* — 진짜 그런가?

### 3.1 *하락한 것* vs *유지/상승한 것*

| 영역 | 변화 |
|---|---|
| ⬇️ **표면 스타일 리뷰** | 사람의 일 아님 |
| ⬇️ **단순 버그 발견** | AI 가 70% 잡음 |
| ⬇️ **boilerplate 검토** | AI 가 *생성도* AI 가 *리뷰도* |
| ➡️ **도메인 일관성 검증** | 여전히 *사람의 컨텍스트* 필요 |
| ➡️ **테스트 전략 검토** | AI 가 *작성* 까지 하지만 *전략* 은 사람 |
| ⬆️ **아키텍처 영향 분석** | *시스템 전체* 봐야. AI 의 컨텍스트 초과 |
| ⬆️ ***왜 이 결정* 의 검토** | ADR / 도메인 *역사* 는 사람만 |
| ⬆️ **AI 생성 코드 검증** | *새 책무*. AI 가 환각하지 않았는지 |

### 3.2 *코드 리뷰의 미래 모습*

AI 가 *모든 표면 + 구조* 검사를 끝낸 *후* 의 사람 리뷰:

```
[PR Review by Tech Lead]

✅ AI 자동 검사 통과 (style, security, basic patterns)
✅ AI 의 14 개 자동 코멘트 — 5 개 fix됨, 9 개 ack

[리뷰어 (사람) 의 진짜 일]
- 이 변경이 ADR-0042 의 outbox 패턴과 일관성 있나?
- BoundedContext 'Settlement' 의 invariant 깨는가?
- 5월 17일 newest-build 사고와 유사한 race condition 가능성?
- 다음 6 개월 후 마이그레이션 plan 과 충돌 없나?
```

리드가 보는 시간이 *짧지만 더 깊은* 영역. *깊이* 가 *가치의 핵심*.

### 3.3 *주니어의 성장 곡선* 위기

가장 큰 *부작용*: 주니어가 *코드 리뷰 받으며* 배우는 패턴이 *AI 가 자동 처리* 해서 *기회 손실*.

- 2020: 주니어 PR → 시니어가 *18 개 코멘트* → 주니어가 *18 가지 깨달음*
- 2026: 주니어 PR → AI 가 *15 개 코멘트* → 주니어가 *AI 코멘트 fix* 하고 끝
  - *왜* 그런 룰 인지 *심층 이해* 부족
  - 시니어와의 *대화* 기회 ↓

해결책 (리드의 새 책무):
- *주니어 페어 프로그래밍* 시간 *명시적 보장*
- AI 가 코멘트 단 *이유* 를 *시니어가 설명* 하는 의식
- *AI 모르는 영역* (시스템 결정, 도메인) 의 *전이 교육*

---

## 4. 미래의 핵심 — *AI Agent 오케스트레이션*

### 4.1 *AI Agent 가 1 명일 때 vs N 명일 때*

지금 (2026 초반):
- 팀에 *AI Agent 1 개* (예: Claude Code 한 인스턴스)
- 사람 1 명이 *한 agent* 를 *수동 운영*

곧 (2026-2027):
- 팀에 *AI Agent N 개* — *24/7 운영*
- *Agent A* — PR 자동 리뷰 / lint / format
- *Agent B* — CI 실패 자동 분석 + 1 차 수정 시도
- *Agent C* — 의존성 업데이트 PR 자동 생성
- *Agent D* — 알림 (PagerDuty) 1 차 응답 + runbook 실행
- *Agent E* — 문서 / 변경 로그 자동 생성

이 *N 개 agent 의 *합주* 를 누가 *조율* 하는가* — 새 직무. **AI Agent Orchestration**.

### 4.2 *오케스트레이션* 의 핵심 책무

**① 권한 경계 설계**
- 어떤 agent 가 *자동 merge* 가능한가? (e.g. 의존성 patch update)
- 어떤 agent 가 *production 변경 가능* 인가? (e.g. pod restart 만, deploy 는 X)
- 어떤 agent 가 *외부 API 호출 가능* 인가?

**② Agent 간 통신**
- *Slack channel 분리* — `#agent-deploy`, `#agent-incident`, `#agent-review`
- *Agent 끼리 정보 공유* — MCP 서버 표준 활용

**③ 실패 시 *escalation chain***
- Agent 실패 → *다른 Agent* 가 백업 시도 → *사람 호출*
- *어느 시점에 사람 개입* 인지 명확

**④ *학습 / 개선 루프***
- Agent 실수 → *그 패턴* 을 다음 agent prompt 에 반영
- *Telemetry 기반* 으로 agent 성능 측정

**⑤ *비용 관리***
- LLM 호출 비용 = *agent 활동 비례*
- 어느 agent 가 *얼마나 LLM token* 쓰는지 모니터링
- 비용 예산 초과 시 *제한*

### 4.3 *실제 시도 사례*

내 환경 (settlement / lemuel-xr / sparta-msa) 에서 운영 중인 *Agent 풀*:

| Agent | 책무 | 권한 | 실행 빈도 |
|---|---|---|---|
| `claude-code-cli` | 개발 작업 | 사용자 세션 중 | 일 평균 20+ 호출 |
| `sparta-deploy-pipeline-verifier` | 배포 외부 검증 | 읽기만 | 배포마다 |
| `auto-trading-safety-gate` | 매매 코드 안전 게이트 | 읽기만 | PR마다 |
| `settlement-archunit-enforcer` | 헥사고날 룰 강제 | 읽기만 | PR마다 |
| `lemuel-mental-health-safety` | 텍스트 안전 검사 | 읽기만 | 컨텐츠 생성 시 |
| `security-auditor` | OWASP 검사 | 읽기만 | 요청 시 |

이 6 agent 가 *서로 다른 권한 / 책무* 로 *24 시간 협업*. 사람의 일은:
- *새 agent 추가 시* 권한 설계
- *agent 의 false positive* 패턴 보고 prompt 조정
- *agent 간 충돌* 시 중재
- *escalation* 시 최종 결정

이게 *2026 의 새 개발 리드 일*.

---

## 5. 전체 아키텍처 설계 — *AI 가 못 하는 마지막 영역*

### 5.1 *왜* 아키텍처 설계가 AI 의 영역 밖인가

**컨텍스트의 *역사적 깊이***
- "이 시스템은 *왜* 이렇게 설계됐나" — 5년 전 회의 / 사라진 ADR / 정치적 결정
- AI 의 컨텍스트 window 가 1M token 이라도 *역사 전체* 못 봄
- *암묵지* 가 본질

**다중 시스템 간 *trade-off***
- 한 시스템 좋게 하면 다른 시스템 나빠짐 — *제로섬 게임*
- AI 는 *최적화 함수* 가 필요한데, *제로섬에선* 최적화 함수 자체가 *정치적 결정*
- *우선순위 부여* 는 *사람의 가치 판단*

**미래의 *불확실성***
- "3 년 후 트래픽이 어떻게 변할까?" — AI 가 추측은 하지만 *근거 부족*
- *현 비즈니스 환경 + 산업 변화 + 회사 전략* 이 변수
- *직관 + 경험* 이 알고리즘보다 *덜 틀림*

**조직의 *능력 매핑***
- "이 아키텍처를 *우리 팀이 운영* 할 수 있나?"
- AI 는 *팀의 진짜 역량* 모름
- *훌륭한 아키텍처* < *팀이 잘 다룰 수 있는 아키텍처*

### 5.2 *2026 리드의 아키텍처 설계 의제*

**의제 1: AI Agent 가 *연결되는 시스템 경계*** 
- *Agent 가 자동 접근 가능* 한 시스템 list
- *Agent 의 input/output 검증 layer* 설계
- *Agent 가 실수해도* 안전한 *blast radius* 설계

**의제 2: *AI 로 인한 데이터 흐름* 추가**
- LLM 호출 logging → 어떤 데이터가 LLM 으로 갔는지 *audit trail*
- 개인정보 / 영업비밀 *마스킹 레이어*
- *AI 응답 캐시* — 비용 절감 + 일관성

**의제 3: *AI 가 만든 코드의 격리***
- AI 가 *자동 merge* 한 변경의 *Feature flag* 보호
- *Rollback 자동화* — AI 결정의 *되돌리기 비용 0*
- *Canary deployment* — AI 변경 점진 노출

**의제 4: *비즈니스 SLO 의 재정의***
- 기존 SLO: latency, error rate, availability
- 추가: *AI 의존성 SLO* — LLM API down 시 *fallback* 동작 보장

**의제 5: *팀 토폴로지 재설계***
- *AI 가 흡수한 일* 빼고 *남은 일* 의 *최소 팀 구성*
- *Platform team* 이 *Agent infrastructure* 책임
- *Stream-aligned team* 이 *비즈니스 + AI 협업*

### 5.3 *실제 사례 — sparta-msa 의 AI 통합 아키텍처*

```
┌─────────────────────────────────────────────────────────┐
│  외부 사용자 (chat.lemuel.co.kr)                          │
└────────────────────────────┬────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────┐
│  Ingress + WAF + Rate Limit                             │
└────────────────────────────┬────────────────────────────┘
                             ↓
┌──────────── 비즈니스 API ─────────┐  ┌─── AI Layer ────┐
│  sparta-chat (사람 작성 코드)      │←→│ LLM Gateway     │
│  sparta-product                   │   │ (audit + cache) │
│  sparta-order                     │   │                 │
└───────────────┬───────────────────┘   │ Claude / GPT    │
                ↓                       └─────────────────┘
┌─────────────────────────────────────────────────────────┐
│  Postgres + Redis + Kafka                                │
└─────────────────────────────────────────────────────────┘
                ↑
┌─── Agent Infrastructure (Platform) ───┐
│  Agent Orchestrator                    │
│  ├── auto-deploy (read-only ArgoCD)    │
│  ├── auto-test (PR trigger)            │
│  ├── auto-incident (PagerDuty 1차)     │
│  └── auto-docs (commit 기반 changelog) │
└────────────────────────────────────────┘
```

핵심:
- *LLM Gateway* 가 *모든 LLM 호출의 중간 layer* — audit + cache + masking
- *Agent Infrastructure* 가 *별도 plane* — production 비즈니스 시스템과 분리
- *Agent 가 읽기만* 가능. 변경은 *PR 통해 사람 승인*

이 아키텍처 결정 자체가 *2026 리드의 일*. AI 가 *못 하는 영역*.

---

## 6. *그래서 개발 리드는 어디로 가나*

### 6.1 *시간 재배분*

**2020 의 리드 (40 시간/주):**
- 코드 리뷰: 12 시간 (30%)
- 회의 / 애자일 의례: 12 시간 (30%)
- 기술 결정 / 설계: 8 시간 (20%)
- 개인 코딩: 4 시간 (10%)
- 사람 관리 / 1on1: 4 시간 (10%)

**2026 의 리드 (40 시간/주):**
- 코드 리뷰: **4 시간** (-67%, 깊은 부분만)
- 회의 / 애자일 의례: **6 시간** (-50%)
- **AI Agent Orchestration**: **8 시간** (NEW, 20%)
- **아키텍처 설계 / ADR**: **10 시간** (+25%, 비중 ↑)
- 개인 코딩: 4 시간 (변화 없음, AI 보조로 더 큰 일)
- 사람 관리 / 1on1: **6 시간** (+50%, 주니어 성장 곡선 대응)
- *학습 / 산업 변화 추적*: **2 시간** (NEW)

### 6.2 *새 책무의 *나열*

리드의 *2026 추가 책무*:

1. **AI Agent 풀 운영** — 권한 설계, prompt 튜닝, 비용 관리
2. **AI 생성 코드의 *책임* 시스템** — 누가 검토했고 누가 *책임* 지는지
3. **주니어 성장 곡선 재설계** — AI 가 *흡수한 학습 기회* 보충
4. **LLM 의존성의 *SLO 관리*** — 외부 LLM down 시 대응 plan
5. **AI 비용 모니터링** — token 사용 추적, 비용 예산
6. **컴플라이언스 + 보안** — AI 가 *어떤 데이터* 처리하는지 audit
7. **벤더 lock-in 회피** — *모델 교체 가능* 한 아키텍처
8. ***AI 가 못 하는 일* 의 *조직 학습***

### 6.3 *위협받지 않는 리드의 *기술***

다음 영역에 *시간을 투자* 한 리드는 *5 년 후에도 가치 유지*:

✅ **분산 시스템 설계** — *진짜 실수 사례 + 회복* 경험
✅ **DDD / 도메인 모델링** — *AI 가 모르는 컨텍스트*
✅ **장애 대응 능력** — *불완전한 정보로 의사결정*
✅ **사람 관리 / 코칭** — *AI 가 본질적으로 못 함*
✅ ***기술 선택의 가치 판단*** — Resume-Driven 회피
✅ **다중 시스템 trade-off 결정**
✅ **AI 의 *답을 검증* 하는 능력** — *AI 가 틀렸을 때 잡는 눈*

### 6.4 *위협받는 영역*

⚠️ **순수 코딩 능력** — *AI 보조 없이* 코드 작성하는 속도는 가치 하락
⚠️ **단순 코드 리뷰** — AI 가 흡수
⚠️ **boilerplate 작성** — AI 흡수
⚠️ **단순 디버깅** — AI 흡수 (단순 case 만)
⚠️ ***최신 기술 따라잡기 자체*** — AI 가 *빨라짐*, 사람의 비교 우위 ↓

---

## 7. 결론 — *리드의 가치는 *더 깊어진다**

코드 리뷰 / 애자일이 *없어지는 게 아니라 *재배분***. AI 가 *반복적 의례* 를 흡수하고, 사람은 *판단 + 책임 + 통합* 에 집중.

*가치가 하락하는 리드*: AI 가 흡수할 수 있는 일에 매달리는 리드.
*가치가 상승하는 리드*: AI Agent 오케스트레이션 + 아키텍처 + 사람 코칭에 집중하는 리드.

미래의 *진짜 좋은 리드* 의 모습:
- *5 개 AI Agent 를 마치 5 명 주니어처럼 운영*
- *코드 리뷰는 AI 가 1 차*, 본인은 *시스템 영향* 만 검토
- *아키텍처 ADR* 을 *주 1 개* 작성 (AI 가 *템플릿*, 결정은 사람)
- *주니어 1on1 시간 늘림* — AI 가 흡수한 학습 기회 보충
- *주 1 회 산업 동향 학습* 시간 명시적 확보

이건 *위협* 이 아니라 *기회*. *반복 의례* 에서 해방돼 *진짜 어려운 일* 에 집중할 수 있는 시대.

**한 줄 결론:** *코드 리뷰 / 애자일의 *형식* 은 사라지고, *본질* (작동하는 소프트웨어 + 빠른 피드백) 은 *AI 가 가속*. 리드의 좌표는 *AI Agent 오케스트레이션* + *전체 아키텍처 설계* 로 이동. *판단의 가치* 는 *오히려 상승*.*

---

## 참고

- *The Phoenix Project* — Kim, Behr, Spafford (2013)
- *Accelerate* — Forsgren, Humble, Kim (2018)
- *Team Topologies* — Skelton & Pais (2019)
- *The Mythical Man-Month* — Brooks (1975) — 50 년 후에도 유효
- Anthropic, [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- Martin Fowler, [Refactoring with AI](https://martinfowler.com/articles/2023-chatgpt-tech-writing.html)
- 관련 글:
  - [개발 리드 30 년 변천사 + 오버엔지니어링 + AI 시대]({% post_url 2026-05-29-engineering-leadership-evolution-overengineering-ai-era %})
  - [Harness Engineering 1 — AI Agent harness]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %})
  - [Harness Engineering 4 — Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
  - [JPA vs MyBatis — AI 시대]({% post_url 2026-05-29-jpa-vs-mybatis-ai-era-coding %})
