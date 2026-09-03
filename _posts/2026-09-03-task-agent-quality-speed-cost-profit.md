---
layout: post
title: "Task Agent를 Quality·Speed·Cost·Profit으로 설계하는 법"
date: 2026-09-03 18:51:03 +0900
categories: [AI, Agent]
tags: [TaskAgent, MultiAgent, Quality, Speed, Cost, Profit, MLOps]
---

## 결론부터

Task Agent의 성능은 모델의 답변 품질 하나로 결정되지 않는다. 실제 사업 성과는 다음의 곱으로 보는 편이 정확하다.

```text
실현 가치 = 유효 산출물 × 품질 × 성공률 × 처리량 − 총비용 − 실패비용
```

여기서 중요한 점은 **Quality·Speed·Cost·Profit을 서로 독립된 지표가 아니라 하나의 운영 시스템으로 관리하는 것**이다.

## 1. Quality: 좋은 답변이 아니라 성공한 작업

Task Agent의 품질은 문장 평가만으로 측정할 수 없다. 사용자가 실제로 요구한 결과물이 생성되고, 검증되며, 부작용 없이 전달됐는지를 봐야 한다.

### 품질 지표

| 지표 | 측정 질문 |
| --- | --- |
| Task success rate | 작업의 종료 조건을 실제로 만족했는가? |
| Artifact validity | 파일·PR·리포트·배포물이 존재하고 유효한가? |
| Factuality | 주장마다 출처와 실행 Trace가 있는가? |
| Rework rate | 사람이 다시 고친 비율은 얼마인가? |
| Side-effect rate | 승인하지 않은 변경·중복·오작동이 있었는가? |
| User correction rate | 사용자가 방향을 되돌린 횟수는 얼마인가? |

모델이 그럴듯한 글을 작성했더라도 출처가 없거나, commit만 하고 실제 배포를 확인하지 않았다면 Task Agent 품질은 높다고 볼 수 없다.

Anthropic은 다중 에이전트가 서로를 명확한 입력·출력·artifact를 가진 도구처럼 사용할 때 효과적으로 협업할 수 있다고 설명한다. 반대로 장기 실행 peer 간 상호작용은 조정이 어려워진다고 지적한다. 따라서 품질의 핵심은 에이전트 수가 아니라 **계약과 검증 경계**다. ([Anthropic, 2026-08-13](https://www.anthropic.com/research/multiagent-systems))

## 2. Speed: 응답 시간이 아니라 완료 시간

Speed를 첫 토큰 시간이나 답변 생성 시간만으로 측정하면 잘못된 결론을 내리기 쉽다.

```text
총 완료 시간
= 대기 시간
+ 모델 추론 시간
+ 도구 실행 시간
+ 재시도 시간
+ 사람 승인 시간
+ 실패 복구 시간
```

예를 들어 빠른 모델이 초안을 빨리 만들었지만 검증 실패로 세 번 재실행된다면, 느린 모델이 한 번에 유효한 artifact를 만든 경우보다 실제 생산성이 낮을 수 있다.

### 속도 개선 방법

- 독립적인 조사 작업은 병렬화한다.
- 파일·저장소·도메인 단위로 작업을 분할한다.
- 모델 호출보다 느린 테스트·빌드·네트워크 구간을 별도로 측정한다.
- 큰 작업은 중앙 Agent가 직접 수행하지 않고 worker로 오프로딩한다.
- 완료 조건을 명확히 하여 불필요한 대화를 줄인다.

Hermes의 `delegate_task`는 각 child에 독립 context와 terminal을 주고 병렬 작업을 수행할 수 있다. 다만 결과는 child의 최종 summary로만 들어오므로, 실제 파일·로그·hash 등 artifact 검증을 별도로 해야 한다. ([Hermes Agent Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation))

## 3. Cost: 토큰 가격보다 실패의 총비용

모델의 토큰 단가만 비교해서는 안 된다.

```text
총비용
= 모델 비용
+ 도구·컴퓨트 비용
+ 대기 비용
+ 재작업 비용
+ 실패로 인한 장애 비용
+ 사람 검토 비용
```

Claude 공식 모델 비교표는 Opus 5를 복잡한 agentic coding·enterprise 업무용, Sonnet 5를 속도와 지능의 균형을 위한 모델로 설명한다. 공개 단가 기준 Opus 5는 input/output MTok당 $5/$25, Sonnet 5는 $2/$10이다. ([Claude Models Overview](https://platform.claude.com/docs/en/models/overview))

따라서 모든 작업을 고성능 모델로 처리하는 것이 비용 최적은 아니다.

| 작업 유형 | 권장 전략 |
| --- | --- |
| 단순 분류·형식 변환 | 저비용 모델 또는 결정적 코드 |
| 자료 수집·초안 | Sonnet급·병렬 worker |
| 복잡한 설계·RCA | Opus급 |
| 최종 검토·위험 판정 | 고성능 모델 + evidence gate |
| 반복 테스트·hash·lint | 모델 대신 스크립트 |

핵심은 모델을 싸게 쓰는 것이 아니라 **실패할 가능성이 높은 구간에만 비싼 추론을 배치하는 것**이다.

## 4. Profit: Agent가 번 돈이 아니라 의사결정 단위의 순가치

Profit은 단순히 매출에서 API 비용을 뺀 값이 아니다. Task Agent가 절약한 시간과 실패를 예방한 가치를 함께 계산해야 한다.

```text
순가치
= (절약한 사람 시간 × 시간당 가치)
+ 추가 처리량의 기여이익
+ 예방한 실패비용
− Agent 운영비
− 검토·통합 비용
```

예를 들어 자동화가 하루 100건을 처리해도 재작업이 30건이면 순이익은 낮다. 반대로 하루 20건만 처리하더라도 실패율이 낮고 고숙련자의 검토 시간을 줄이면 더 높은 가치가 될 수 있다.

### Profit을 측정할 단위

```text
요청당 이익
성공한 Task당 비용
유효 artifact당 비용
절약 시간당 비용
재작업 1건당 손실
장애 예방 1건당 가치
```

가장 유용한 기준은 `요청당 비용`이 아니라 **검증을 통과한 유효 산출물당 비용**이다.

## 5. 네 가지 지표의 균형점

네 지표는 다음처럼 trade-off 관계를 가진다.

```text
Quality ↑ → 보통 Cost·Latency ↑
Speed ↑   → 병렬화 비용·조정 복잡도 ↑
Cost ↓    → 재작업·실패 위험 ↑ 가능
Profit ↑  → 품질·속도·비용의 최적점에서 발생
```

최적화 목표는 각 지표의 최대값이 아니다.

```text
Quality threshold를 넘긴다
→ Speed를 높인다
→ Cost를 줄인다
→ Profit을 측정한다
```

품질 기준을 통과하지 못한 작업을 아무리 빠르고 싸게 처리해도 이익이 아니다.

## 6. 권장 Task Agent 아키텍처

```text
User Request
    ↓
Command Center / Orchestrator
    ├─ Task classifier
    ├─ Risk·permission gate
    ├─ Model router
    ├─ Worker dispatcher
    └─ Evidence fan-in
            ↓
    Worker pool
    ├─ Sonnet: 수집·초안·반복 작업
    ├─ Opus: 고난도 분석·최종 판단
    ├─ Remote CPU worker: 테스트·정적 분석
    └─ Deterministic scripts: lint·hash·URL·artifact 검사
            ↓
    Quality gate
    ├─ artifact exists
    ├─ tests pass
    ├─ provenance exists
    ├─ side effects approved
    └─ delivery verified
```

중앙 Agent는 직접 모든 일을 수행하는 모델이 아니라 다음을 책임지는 **지휘 계층**이어야 한다.

```text
계획
권한
분해
라우팅
결과 통합
최종 검증
```

## 7. 운영에 적용하는 모델 배치

```text
Command Center:
  Opus급 — 작업 분해·위험 판단·최종 검증

일반 worker:
  Sonnet급 — 조사·초안·코드 반복 작업

원격 CPU worker:
  모델 없이 테스트·정적 분석·hash 처리

결정적 검증기:
  모델 없이 exit code·artifact·URL 확인
```

이 구조는 “모든 Agent를 Opus로 실행”하는 구조보다 비용 효율적이다. Opus는 전체 pipeline의 병목이 아니라 **품질·위험 판단이 필요한 지점**에 배치해야 한다.

## 8. 최소 운영 대시보드

| 영역 | 최소 지표 |
| --- | --- |
| Quality | success rate, rework rate, correction rate |
| Speed | p50/p95 completion time, queue time, tool time |
| Cost | input/output tokens, retry cost, worker cost |
| Profit | validated artifact당 비용, 절약 시간, 순가치 |
| Governance | 승인 위반, provenance 누락, drift, side effect |

각 실행은 다음 trace를 남기는 것이 좋다.

```json
{
  "run_id": "unique-run-id",
  "task_type": "research|coding|ops|publishing",
  "model": "model-id",
  "workers": ["worker-a"],
  "started_at": "timestamp",
  "completed_at": "timestamp",
  "status": "PASS|FAIL|UNVERIFIED",
  "artifacts": ["path-or-url"],
  "verification": ["command-or-trace"],
  "cost": {"input_tokens": 0, "output_tokens": 0},
  "rework_count": 0
}
```

## 결론

Task Agent에서 좋은 모델은 품질의 상한을 높일 수 있다. 그러나 profit을 만드는 것은 모델 자체가 아니라 다음의 조합이다.

```text
좋은 모델
+ 정확한 Task contract
+ 역할별 모델 라우팅
+ 병렬·원격 worker
+ 결정적 검증
+ provenance·permission 관리
+ 실제 완료 시간·실패 비용 측정
```

가장 실용적인 운영 원칙은 다음 한 줄이다.

> **Sonnet으로 많이 처리하고, Opus로 중요한 판단을 맡기며, 스크립트로 사실을 검증한다.**

## References

1. [Anthropic, Patterns and problems in emerging multiagent systems, 2026-08-13](https://www.anthropic.com/research/multiagent-systems)
2. [Anthropic, Claude Models Overview](https://platform.claude.com/docs/en/models/overview)
3. [Hermes Agent, Subagent Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)
