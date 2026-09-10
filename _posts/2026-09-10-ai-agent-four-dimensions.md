---
layout: post
title: "AI Agent를 이해하는 네 가지 축: 자율성·반응성·사전능동성·사회성"
date: 2026-09-10 14:18:13 +0900
categories: [AI]
tags: [AI Agent, Autonomous Agent, Reactivity, Proactiveness, Social Ability, Multi-Agent]
---

# AI Agent를 이해하는 네 가지 축

AI Agent를 단순히 “LLM에 도구를 붙인 챗봇”으로 이해하면 실제 시스템의 차이를 설명하기 어렵다. Agent는 환경을 관찰하고, 목표를 향해 행동을 선택하며, 결과를 다시 확인하고, 필요하면 사람이나 다른 Agent와 협력하는 시스템이다.

고전적인 지능형 Agent 논의에서는 Agent를 환경 안에서 설계 목표를 달성하기 위해 자율적으로 행동하는 컴퓨터 시스템으로 설명하고, 유연한 행동을 위해 반응성·사전능동성·사회성을 중요한 특성으로 구분한다.[1] 오늘날의 LLM Agent도 이 네 가지 축으로 보면 “대화 가능한 모델”과 “운영 가능한 Agent”의 차이를 선명하게 볼 수 있다.

```text
환경 변화
   │
   ▼
관찰·상태 수집 ──► 반응성
   │
   ▼
목표·계획·행동 ──► 자율성 + 사전능동성
   │
   ▼
도구·사람·다른 Agent와 협업 ──► 사회성
   │
   └──────── 결과 검증·다음 행동 ────────┘
```

## 1. 자율성: 직접 지시가 없어도 목표를 향해 행동하는 능력

자율성은 Agent가 매 순간 사람에게 다음 명령을 받아야만 움직이는 것이 아니라, 주어진 목표와 정책 범위 안에서 다음 행동을 스스로 선택하는 성질이다. 고전적 정의에서도 자율성은 사람이나 다른 Agent의 직접 개입 없이 행동하고 내부 상태와 행동을 통제하는 능력으로 설명된다.[1]

현대 Agent에서 자율성은 다음 요소의 조합이다.

- 목표 해석
- 작업 분해
- 도구 선택
- 중간 결과 평가
- 실패 시 재시도·대체 경로 선택
- 종료 조건 판단

예를 들어 “CI 보안 게이트를 통과시켜라”라는 목표가 주어졌을 때 Agent는 로그를 확인하고, 취약한 의존성을 찾고, 수정 범위를 제안하고, 테스트와 스캔을 실행한 뒤, 결과가 통과했는지 확인해야 한다. 단순 챗봇은 수정 방법을 설명할 수 있지만, Agent는 제한된 권한 안에서 실제 상태를 읽고 다음 행동을 결정한다.

### 자율성은 권한이 아니다

자율성이 높다고 해서 무제한 권한을 주어야 하는 것은 아니다.

```text
자율성 = 스스로 다음 행동을 선택하는 능력
권한    = 실제 시스템을 변경할 수 있는 범위
```

좋은 Agent는 자율적으로 판단하되, 위험한 write 작업·배포·결제·삭제는 승인·정책·dry-run·rollback 경계를 통과해야 한다. OpenAI는 Agent의 핵심을 모델, 도구, 명시적인 지침의 결합으로 설명하고, 도구 사용은 guardrail 안에서 이뤄져야 한다고 안내한다.[3]

### 자율성 평가 지표

- 사람의 추가 지시 없이 완료한 단계 비율
- 잘못된 도구 호출률
- 승인 없이 수행한 위험 작업 수
- 목표 달성률
- 최대 반복 횟수 내 종료율
- 실패 후 안전한 중단 비율

자율성을 “오래 실행했다”로 측정하면 안 된다. 통제되지 않은 장시간 실행은 자율성이 아니라 runaway loop일 수 있다.

## 2. 반응성: 환경 변화에 맞춰 적시에 반응하는 능력

반응성은 Agent가 환경을 관찰하고 변화에 적시에 대응하는 능력이다.[1] 여기서 환경은 물리적 장치만을 뜻하지 않는다.

- 사용자의 새 메시지
- API 응답과 오류
- 파일 변경
- GitHub Actions 결과
- Kubernetes 파드 상태
- 모니터링 알림
- 데이터베이스 상태
- 다른 Agent의 결과

반응형 Agent의 기본 루프는 다음과 같다.

```text
observe → interpret → act → observe again
```

예를 들어 배포 후 smoke test가 500을 반환하면 Agent는 성공으로 보고하지 않고, 로그·revision·환경 설정을 다시 확인해야 한다. 도구 결과가 빈 값이면 결과를 추측하지 말고 재조회하거나, 조사 불가 상태로 멈춰야 한다.

### 반응성과 단순 이벤트 처리의 차이

`if error then alert`만 구현된 시스템은 반응적일 수 있지만 충분히 지능적인 Agent라고 하기는 어렵다. Agent는 오류가 발생했음을 감지하는 것뿐 아니라 다음을 판단해야 한다.

- 일시적 오류인가, 만성 오류인가?
- 재시도해도 안전한가?
- 사용자 영향이 있는가?
- 어떤 증거가 추가로 필요한가?
- 사람에게 넘겨야 하는가?

### 반응성 평가 지표

- 이벤트 감지 지연시간
- 감지 후 첫 행동까지의 시간
- 잘못된 경보 비율
- 실제 상태 변화와 보고 내용의 일치율
- stale state를 성공으로 오판한 비율
- 중복 이벤트 처리와 idempotency

반응성이 빠르기만 하면 위험하다. 잘못된 상태를 빠르게 변경하는 Agent보다, 근거를 확인하고 안전하게 늦추는 Agent가 운영 환경에서는 낫다.

## 3. 사전능동성: 요청을 기다리지 않고 목표를 향해 다음 행동을 제안하는 능력

사전능동성(proactiveness)은 환경 변화에 단순히 반응하는 것을 넘어, 목표 지향적으로 기회를 찾고 먼저 행동하는 성질이다.[1]

반응성은 다음과 같다.

```text
장애 알림이 왔다 → 로그를 확인한다
```

사전능동성은 다음과 같다.

```text
재시작 횟수가 증가하는 추세를 발견했다
→ 아직 장애가 아니어도 원인과 위험을 조사한다
→ 다음 점검 항목과 예방 조치를 제안한다
```

### 사전능동성의 예

- 배포 전 변경 영향 분석
- 만료 예정 인증서·토큰 탐지
- 의존성 보안 업데이트 제안
- 로그 오류량 증가 추세 탐지
- 지식 문서가 오래되어 재검토 제안
- 실패 가능성이 높은 작업의 사전 승인 요청
- 반복되는 수동 작업의 자동화 제안

하지만 사전능동성은 자동 변경과 동일하지 않다. 운영 Agent는 위험을 발견하면 먼저 증거와 선택지를 제시하고, 파괴적 변경은 사용자의 승인을 받아야 한다.

```text
관측 → 위험 점수화 → 영향 분석 → 선택지 제안 → 승인 → 실행 → 검증
```

### 사전능동성의 함정

- 근거 없는 알림을 과도하게 생성
- 사용자가 요청하지 않은 변경을 수행
- 오래된 상태를 현재 위험으로 오판
- 비용·권한·운영 맥락을 무시
- “좋아 보이는 개선”을 실제 요구사항으로 착각

사전능동적인 Agent는 많이 말하는 Agent가 아니다. **다음에 필요할 가능성이 높고, 근거가 있으며, 사용자가 통제할 수 있는 행동을 제안하는 Agent**다.

## 4. 사회성: 사람·도구·다른 Agent와 협력하는 능력

사회성은 Agent가 인간과 다른 Agent를 포함한 외부 주체와 상호작용하고, 문제 해결을 위해 협력·조정·경쟁할 수 있는 능력이다.[1]

현대 Agent의 사회성은 대화 능력보다 넓다.

- 사용자와 목표·승인·우선순위 협의
- 도구와 명시적인 계약으로 상호작용
- 다른 Agent에 독립적인 하위 작업 위임
- 결과·근거·실패를 coordinator에게 반환
- 권한·세션·작업 문맥을 보존
- 중복 작업과 충돌을 조정

Anthropic은 multi-agent research system에서 여러 Agent가 도구를 사용해 병렬로 탐색하고, coordinator가 결과를 모으는 구조를 설명한다.[4] 다만 Agent 수가 늘면 통신·비용·중복·결과 통합의 복잡성도 함께 늘어난다.

### 사회적 Agent의 최소 계약

```json
{
  "task_id": "task-123",
  "owner": "coordinator",
  "scope": "read-only investigation",
  "input": "target and time window",
  "output": "findings, evidence, unknowns",
  "side_effects": "none",
  "status": "completed"
}
```

다른 Agent를 호출할 때는 작업 범위·권한·출력 형식·완료 조건을 명확히 해야 한다. “조사해줘”만 전달하면 각 Agent가 서로 다른 기준으로 조사해 결과를 합치기 어렵다.

### 사회성 평가 지표

- 위임 결과의 형식 준수율
- 중복 작업률
- 충돌·재작업률
- 사람 승인 요청의 적절성
- 다른 Agent 결과의 근거 보존율
- 사용자에게 전달된 최종 결과의 일관성

사회성은 Agent가 많다는 뜻이 아니다. 한 Agent가 사람·도구·하위 Agent와 **예측 가능한 계약으로 협력하는 능력**이 핵심이다.

## 5. 네 가지 측면의 차이

| 측면 | 핵심 질문 | 실패 형태 | 중요한 통제 |
| --- | --- | --- | --- |
| 자율성 | 스스로 다음 행동을 선택하는가? | runaway loop, 무승인 변경 | 권한·승인·최대 반복 |
| 반응성 | 환경 변화에 적시에 대응하는가? | stale state, 지연·오탐 | 관측·재조회·idempotency |
| 사전능동성 | 요청 전에 위험·기회를 발견하는가? | 과잉 알림, 근거 없는 개입 | 증거·우선순위·승인 |
| 사회성 | 사람·도구·Agent와 협력하는가? | 충돌·중복·문맥 손실 | 계약·소유권·추적 ID |

네 축은 서로 독립적이지만 실제 시스템에서는 결합된다.

```text
자율성만 높음 → 혼자 마음대로 움직이는 자동화
반응성만 높음 → 이벤트에만 반응하는 rule engine
사전능동성만 높음 → 알림을 쏟아내는 predictor
사회성만 높음 → 대화는 잘하지만 실행하지 못하는 assistant
```

신뢰할 수 있는 Agent는 네 축을 균형 있게 갖고, 각 축을 측정·제한한다.

## 6. Agent와 Workflow를 구분하기

모든 LLM 기반 자동화가 Agent인 것은 아니다. Anthropic은 정해진 코드 경로로 LLM과 도구를 연결하는 시스템을 workflow로, LLM이 자신의 과정과 도구 사용을 동적으로 지시하는 시스템을 Agent로 구분한다.[2]

### Workflow가 더 적합한 경우

- 단계가 항상 동일하다.
- 규정된 입력과 출력이 있다.
- 정확성과 재현성이 자율성보다 중요하다.
- 결제·정산·법정 보고처럼 결정 경로가 고정되어야 한다.
- 평가 케이스를 명확히 만들 수 있다.

### Agent가 더 적합한 경우

- 필요한 단계 수를 사전에 알기 어렵다.
- 여러 도구를 탐색적으로 사용해야 한다.
- 예외와 비정형 입력이 많다.
- 중간 결과에 따라 다음 행동이 달라진다.
- 사람의 판단을 checkpoint로 남길 수 있다.

실전에서는 workflow와 Agent를 조합하는 것이 일반적이다.

```text
고정된 인증·결제·배포 정책 = workflow / guardrail
비정형 조사·원인 탐색·계획 수립 = agent
```

복잡성을 무조건 Agent로 해결하지 말고, 단순한 코드 경로로 충분한 영역은 결정론적 workflow로 남겨야 한다. Anthropic도 Agent 시스템은 성능 향상과 함께 latency·cost·compounding error를 늘릴 수 있으므로 단순한 해법부터 시작하라고 권고한다.[2]

## 7. 네 축을 Agent 아키텍처에 배치하기

```text
                    사용자·다른 Agent
                           ▲
                           │ 사회성
                           ▼
환경 ──► 관측/상태 저장 ──► 계획기 ──► 도구 실행기 ──► 환경
          │ 반응성           │ 자율성       │ guardrail
          │                 │ 사전능동성   │ 승인/권한
          └─────────────────┴───────────────┘
                    trace·평가·감사
```

### 상태와 기억

Agent가 반응하고 사전능동적으로 행동하려면 현재 상태와 과거 결과를 구분해야 한다.

- 현재 관측값
- 작업별 실행 상태
- 장기 사용자 선호
- 도구 호출 결과
- 실패·재시도 이력
- 승인·거부 기록

기억을 사실의 원천으로 취급하면 안 된다. 현재 runtime trace와 실제 도구 결과가 우선이며, 오래된 기억은 검증 대상이다.

### 도구

도구는 Agent의 능력을 늘리지만 공격면과 실패면도 늘린다. OpenAI는 Agent를 모델·도구·지침의 결합으로 설명하고, 데이터 조회 도구·행동 도구·다른 Agent를 호출하는 orchestration 도구를 구분한다.[3]

좋은 도구는 다음을 갖는다.

- 목적이 하나이고 이름이 명확하다.
- 입력 schema가 엄격하다.
- read와 write 권한이 분리된다.
- 결과에 근거·상태·오류·미확인을 포함한다.
- pagination·filter·truncation을 지원한다.
- dry-run과 rollback 경로가 있다.
- 호출 trace와 actor를 기록한다.

### 종료 조건

자율 Agent는 반드시 종료 조건을 가져야 한다.

- 목표 달성
- 검증 통과
- 최대 반복 횟수
- 시간·비용 예산 초과
- 동일 오류 반복
- 사용자 승인 필요
- 필수 도구 unavailable

## 8. 운영 Agent 예시

### Kubernetes RCA Agent

- **반응성**: 파드 비정상·노드 NotReady 이벤트를 감지
- **자율성**: 상태·로그·이벤트·최근 배포를 순서대로 조회
- **사전능동성**: restartCount 증가와 DNS 경고 추세를 조기 제안
- **사회성**: read-only worker에 조사 위임하고 사용자에게 승인 선택지 제공

단, `Running` 파드만 보고 정상이라고 결론 내리면 안 된다. 현재 상태, 누적 재시작, Last State, 시간창, 실제 업무 처리량을 분리해야 한다.

### 코드 수정 Agent

- **반응성**: CI 실패와 테스트 결과를 읽음
- **자율성**: 영향 파일을 찾고 수정·테스트 순서를 계획
- **사전능동성**: 보안 게이트와 회귀 위험을 사전에 점검
- **사회성**: 리뷰어·CI·배포 시스템과 계약으로 협력

코드 수정 Agent는 commit·push를 성공으로 간주하지 않고, 테스트·보안 스캔·배포된 artifact·실제 URL까지 확인해야 한다.

### 연구 Agent

- **반응성**: 검색 결과와 출처 품질을 반영
- **자율성**: 검색·추출·비교·초안 단계를 조정
- **사전능동성**: 출처 충돌과 미확인 주장을 표시
- **사회성**: 병렬 subagent 결과를 중복 제거해 통합

Anthropic의 multi-agent research 사례처럼 병렬 탐색은 속도와 범위를 늘릴 수 있지만, 도구 품질·결과 통합·평가가 함께 필요하다.[4]

## 9. 평가 설계

Agent의 품질을 최종 답변 하나만 보고 평가하면 안 된다. 실행 trace를 평가 대상으로 포함해야 한다.

### 자율성

- 목표 달성률
- 무승인 side effect 수
- 불필요한 도구 호출 수
- 최대 반복 내 종료율

### 반응성

- 이벤트 감지 지연
- 상태 변화 후 올바른 행동까지의 시간
- stale state 오판률
- 재시도·중복 처리율

### 사전능동성

- 사전에 발견한 실제 위험 비율
- false positive 비율
- 조치 제안의 유용성
- 사용자 승인 요청의 적절성

### 사회성

- 도구 계약 준수율
- 위임 결과 형식 준수율
- 중복 작업률
- 충돌·재작업률
- 사람에게 적절히 handoff한 비율

OpenAI는 Agent run을 반복 루프로 보고, 도구 호출·최종 출력·오류·최대 turn 같은 종료 조건을 두는 구조를 설명한다.[3] 또한 Agent 평가는 모델뿐 아니라 도구·orchestration·harness 전체를 평가해야 한다.

## 결론

AI Agent의 본질은 “LLM이 대답한다”가 아니다. Agent는 환경 안에서 목표를 향해 행동하고, 결과를 검증하며, 필요할 때 사람과 다른 Agent와 협력하는 시스템이다.

네 가지 측면으로 요약하면 다음과 같다.

- **자율성**: 직접 지시 없이 목표를 향해 다음 행동을 선택한다.
- **반응성**: 환경 변화와 실행 결과를 관측하고 적시에 대응한다.
- **사전능동성**: 요청을 기다리지 않고 위험·기회·다음 행동을 제안한다.
- **사회성**: 사람·도구·다른 Agent와 계약을 지키며 협력한다.

그러나 자율성이 클수록 권한과 승인 경계가 필요하고, 반응성이 빠를수록 관측 오류와 중복 처리를 관리해야 하며, 사전능동성이 강할수록 근거와 알림 품질이 중요하고, 사회성이 넓을수록 위임 계약과 추적성이 필요하다.

좋은 Agent는 네 가지 능력을 최대화하는 시스템이 아니다. **목표·위험·권한·비용에 맞춰 네 축을 조절하고, 모든 행동을 trace와 평가로 검증하는 시스템**이다.

## 참고 자료

[1] Jennings & Wooldridge, *Applications of Intelligent Agents* — 자율성·반응성·사전능동성·사회성의 고전적 Agent 특성  
[2] Anthropic, *Building Effective Agents* — workflow와 Agent 구분, 단순한 조합과 guardrail  
[3] OpenAI, *A Practical Guide to Building Agents* — 모델·도구·지침·orchestration·run 구조  
[4] Anthropic, *How We Built Our Multi-Agent Research System* — 병렬 multi-agent 연구와 도구·평가·관측

## 출처

- Jennings & Wooldridge, Applications of Intelligent Agents: http://www.cs.ox.ac.uk/people/michael.wooldridge/pubs/applications.pdf
- Anthropic, Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents
- OpenAI, A Practical Guide to Building Agents: https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
- Anthropic, Multi-Agent Research System: https://www.anthropic.com/engineering/multi-agent-research-system

## Sources

[1] http://www.cs.ox.ac.uk/people/michael.wooldridge/pubs/applications.pdf — Jennings and Wooldridge Applications of Intelligent Agents
[2] https://www.anthropic.com/engineering/building-effective-agents — Anthropic Building Effective Agents
[3] https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents — OpenAI Practical Guide to Building Agents
[4] https://www.anthropic.com/engineering/multi-agent-research-system — Anthropic Multi-Agent Research System
