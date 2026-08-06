---
layout: post
title: "LION 코드 지식 그래프 기반 평가: Settlement·Lemuel-XR·Inter-ASAT"
date: 2026-08-07 06:12:40 +0900
categories: [AI, Architecture, DevOps]
tags: [LION, Graphify, code-review-graph, Settlement, Lemuel-XR, Inter-ASAT, Kubernetes]
---

# LION 코드 지식 그래프 기반 평가: Settlement·Lemuel-XR·Inter-ASAT

## 요약

이번 글은 세 프로젝트의 코드를 직접 수정하거나 운영 DB에 접속하지 않고, 로컬 코드·문서·SQL·설정에서 추출한 관계 그래프를 먼저 만든 뒤 LION의 컴퓨터과학 15개 렌즈로 평가하는 접근을 정리한다. 그래프는 최종 판정기가 아니라 대규모 코드베이스의 탐색 범위를 줄이는 **증거·관계 탐색 계층**이다.

> 중요: 아래 그래프 수치는 로컬 결정론적 read-only extractor가 추출한 결과다. Graph edge 자체는 런타임 동작의 증명이 아니며, 중요한 관계는 소스코드·테스트·마이그레이션·ADR·실행 Trace로 재검증해야 한다.

## 1. 평가 방법

```text
저장소 HEAD 확인
→ 코드·문서·SQL·설정 관계 추출
→ graph.json·GRAPH_REPORT.md·manifest 생성
→ LION_INPUT.md로 commit·노드·관계·안전 범위 고정
→ API·DB·이벤트·테스트 경로 재검증
→ 15개 CS 렌즈 평가
```

공통 안전 범위는 다음과 같다.

- 운영 DB 접근 없음
- 운영 데이터·Secret 접근 없음
- 저장소 코드 수정 없음
- 그래프 관계 provenance는 `EXTRACTED`만 사용
- `INFERRED`·`AMBIGUOUS` 관계는 확인 전 사실로 사용하지 않음

## 2. 비교 개요

| 프로젝트 | 기준 commit | 그래프 노드 | 그래프 관계 | 핵심 관찰 |
|---|---|---:|---:|---|
| Settlement | `70d24bb` | 4,058 | 32,136 | 다중 MSA·정산·원장·대사·이벤트 관계가 가장 큼 |
| Lemuel-XR | `07fe3ec` | 910 | 3,650 | Kotlin/Spring·Next.js·AI·안전 게이트가 결합됨 |
| Inter-ASAT | `7078b60` | 583 | 3,571 | 훈련 세션·trial·적응 알고리즘·분석·export 경로가 핵심 |

생성 산출물은 프로젝트별 `graph.json`, `GRAPH_REPORT.md`, `manifest.json`, `LION_INPUT.md`로 관리한다.

## 3. Settlement 평가

### 확인된 구조

Settlement 그래프는 다음 종류의 관계를 포착했다.

- import 관계: 24,611
- 테이블 참조: 2,621
- 선언된 endpoint: 258
- Spring/Kafka/JPA 관련 선언: 591
- topic 문자열: 8
- 모듈 소속 관계: 4,047

도메인 관점에서 핵심 경로는 다음과 같이 검토해야 한다.

```text
order/payment
  → outbox_events
  → Kafka topic
  → projection consumer
  → settlement view/aggregate
  → ledger
  → payout
  → reconciliation
```

### LION 관점의 판단

- **분산 시스템:** Outbox·이벤트·projection·대사 관계를 분리해 검토할 수 있는 구조다. 다만 그래프만으로 순서·멱등성·DLT 복구가 보장됐다고 판단할 수 없다.
- **데이터베이스:** 서비스별 DB와 원장 불변성·adjustment/reversal 규칙이 핵심이다. migration·entity·repository·계약 테스트를 함께 확인해야 한다.
- **보안:** 금융 데이터와 운영 권한 경계가 중요하다. Secret·RBAC·내부 API·감사 로그는 그래프 후보를 실제 설정과 테스트로 재검증해야 한다.
- **운영:** Kubernetes·ArgoCD·Prometheus/Grafana·ELK를 연결할 수 있지만, SLO·RTO/RPO·복구 실측은 별도 증거가 필요하다.
- **종합:** 세 프로젝트 중 그래프 전략의 기대효과가 가장 크다. 관계 수와 서비스 경계가 커서 변경 영향도 분석, 이벤트 계약 검토, 대사 경로 추적에 유리하다.

### 주요 리스크

1. 그래프의 import·문자열 추출만으로 실제 producer/consumer 의미를 확정하면 안 된다.
2. 원장·대사·지급의 불변식은 코드·테스트·실행 결과를 함께 봐야 한다.
3. 대규모 문서·샘플 JSON이 그래프 입력에 포함되면 핵심 코드 관계가 묻힐 수 있다. source/document 계층과 도메인별 필터가 필요하다.

## 4. Lemuel-XR 평가

### 확인된 구조

- import 관계: 2,357
- 테이블 참조: 364
- endpoint 선언: 26
- topic 관계: 2
- 전체 노드: 910

프로젝트 문서 기준 핵심 흐름은 다음과 같다.

```text
training/session
  → trial
  → adaptive algorithm
  → result/reliability grade
  → dashboard/export
```

### LION 관점의 판단

- **소프트웨어 공학:** Kotlin/Spring 헥사고날 경계와 테스트·게이트 문서가 중요한 평가 근거다.
- **데이터:** Flyway·JPA entity·DTO·export 사이의 컬럼 일관성을 그래프 후보로 찾기 좋다.
- **보안·안전:** JWT·관리자 경계뿐 아니라 신학·임상 안전 게이트가 기능 품질의 일부다. 그래프 연결만으로 안전 승인을 대체할 수 없다.
- **AI·데이터:** Python sidecar와 분석 산출물의 lineage를 추적할 수 있지만, 분석 결과의 통계적 타당성은 별도 검증이 필요하다.
- **종합:** 코드 그래프는 endpoint·entity·migration·export 누락을 찾는 데 유용하다. 그러나 사용자 노출 콘텐츠는 정적 관계보다 정책·검토 게이트의 실제 실행 여부가 더 중요하다.

현재 작업 트리에는 `application.yml`과 안전 테스트 변경이 있었으므로, 평가 시 해당 변경을 기준 commit과 분리해 보고해야 한다.

## 5. Inter-ASAT 평가

### 확인된 구조

- import 관계: 2,400
- 테이블 참조: 545
- endpoint 선언: 52
- 전체 노드: 583

핵심 구조는 다음과 같다.

```text
User/TrainingSession
  → TrainingTrial
  → AdaptiveAlgorithmState
  → TrainingResult/JND
  → Dashboard
  → CSV/Excel export
```

### LION 관점의 판단

- **데이터 모델:** 훈련 세션·trial·결과·알고리즘 상태가 분리되어 있어 재현성·감사 추적을 그래프로 확인하기 좋다.
- **데이터베이스:** Flyway와 JPA 모델의 관계, soft delete·version·snapshot 필드 일관성이 핵심이다.
- **운영:** PostgreSQL·Redis·MinIO·Python 분석 sidecar가 여러 경계를 만든다. 장애 시 데이터 재처리·export 재현성을 검증해야 한다.
- **보안:** TRAINEE/ADMIN 권한과 export 데이터 경계가 중요하다. 그래프는 후보 경로를 주지만 접근통제의 실제 효과는 테스트와 runtime 검증이 필요하다.
- **종합:** 프로젝트 규모가 Settlement보다 작아 전체 관계를 빠르게 이해하기 좋다. 그래프 전략은 데이터 lineage와 migration/entity drift 검출에 특히 적합하다.

`docs/STATUS.md`가 변경된 상태이므로, 자동화 파이프라인은 해당 변경을 덮어쓰지 않고 현재 HEAD와 working tree를 분리해 기록해야 한다.

## 6. 세 프로젝트 비교

| 평가축 | Settlement | Lemuel-XR | Inter-ASAT |
|---|---|---|---|
| 관계 복잡도 | 매우 높음 | 높음 | 중간 |
| 그래프 효과 | 이벤트·원장·대사 영향도 | 안전·AI·migration lineage | 세션·trial·결과 lineage |
| 주요 위험 | 문자열 관계의 과해석 | 안전 게이트 실행 여부 | 분석·export 재현성 |
| 우선 검증 | Kafka·Outbox·DB·대사 | 권한·안전·Flyway | JPA·Flyway·sidecar |
| 추천 활용 | 변경 리뷰·장애 RCA | 아키텍처·안전 리뷰 | 데이터 모델·품질 리뷰 |

## 7. 운영 파이프라인

세 프로젝트에 다음 실행기를 적용했다.

```text
Settlement:
  /Users/lms/.hermes/scripts/run_settlement_lion_pipeline.py

Lemuel-XR/Inter-ASAT:
  /Users/lms/.hermes/scripts/run_local_lion_pipeline.py
```

각 실행기는 repository HEAD와 graph manifest의 commit이 다르면 그래프를 재생성하고, 검증된 `LION_INPUT.md`를 만든다. pipeline 실패·stale graph·저장소 부재 시에는 graph-assisted review라고 주장하지 않고 원인을 보고해야 한다.

## 결론

그래프 전략의 본질은 LION을 대체하는 것이 아니라 LION의 첫 탐색 단계를 구조화하는 데 있다.

```text
코드 그래프
= 관계 탐색·영향도 축소

LION
= 15개 CS 렌즈 종합평가

실제 코드·테스트·Trace
= 중요 관계의 최종 검증

LLM Wiki
= 근거·결정·변경 이력 저장
```

세 프로젝트 모두 적용 가치가 있지만 우선순위는 다음과 같다.

1. Settlement: 이벤트·원장·대사 복잡도가 높아 효과가 가장 큼
2. Lemuel-XR: 안전 게이트·AI·데이터 lineage 검토에 유리
3. Inter-ASAT: 세션·trial·분석 데이터 흐름 검증에 유리

이번 평가는 로컬 코드·문서·설정 그래프 기반의 정적 사전평가다. 운영 안정성, 실제 성능, 보안 적합성, 데이터 품질을 최종 확정하려면 테스트·runtime Trace·권한 검증·실측이 추가로 필요하다.

## References

- [LION skill and Graphify evidence-graph integration](https://github.com/MyoungSoo7/leopard/blob/main/skills/lion/SKILL.md)
- [Settlement repository](https://github.com/MyoungSoo7/settlement)
- [Lemuel-XR repository](https://github.com/MyoungSoo7/lemuel-xr)
- [Inter-ASAT repository](https://github.com/MyoungSoo7/inter-asat)
- [Graphify](https://github.com/Graphify-Labs/graphify)

> 그래프 산출물 기준일: 2026-08-07. 그래프는 로컬 read-only extractor로 생성했으며 실제 운영 DB·Secret·운영 데이터에는 접근하지 않았다.
