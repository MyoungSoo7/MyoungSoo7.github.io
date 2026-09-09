---
layout: post
title: "Lemuel Cluster Daily RCA: 2026-09-09"
date: 2026-09-09 09:00:00 +0900
categories: [DevOps]
tags: [K8s, RCA, ELK, Kafka, Lemuel]
---

# Lemuel Cluster Daily RCA 리포트 (2026-09-09)

> **TraceGuard Verdict**: ELK 및 Kafka 서비스 가동 중(Running/Ready). ECK Operator의 만성적인 재시작과 리소스 설정 경고가 관찰됨.

---

## 1. 서비스 가용성 요약 (Availability Summary)

| 서비스 | 상태 | 상세 (Pod Ready) | 비고 |
|:---|:---:|:---|:---|
| **Elasticsearch** | ✅ 정상 | `logs-es-{hot,warm,cold}-0` (3/3) | Operational |
| **Kibana** | ✅ 정상 | `logs-kb` (1/1) | Operational |
| **Logstash** | ✅ 정상 | `logs-ls-0` (1/1) | Operational |
| **Kafka** | ✅ 정상 | `lemuel-dual-role-0` (1/1) | Operational |
| **Operators** | ⚠️ 주의 | `elastic-operator` (Ready, 95 Restarts) | 만성적 재시작 관찰 |

---

## 2. 주요 인시던트 분석 (Incident Analysis)

### [Historical] ECK Manifest 예약 설정 충돌
- **현상**: Elasticsearch 리소스 manifest에 `cluster.initial_master_nodes` 및 `xpack.security.enabled`가 포함되어 ECK 로그에서 경고 발생.
- **원인**: 해당 설정들은 ECK가 내부적으로 관리하도록 예약(Reserved)된 항목이나, 사용자 구성(manifest)에 직접 포함됨.
- **증거**: `2026-09-08T22:33:44.013Z ECK logs - Forbidden and reserved for internal use`.
- **영향**: 서비스 구동에는 성공했으나, 향후 업그레이드나 reconciliation 과정에서 예기치 않은 동작 유발 가능성 있음.

### [Chronic] ECK Operator 고빈도 재시작
- **현상**: `elastic-operator-0` 파드의 `restartCount`가 **95**에 도달함.
- **원인**: (추정) 리소스 부족(OOM) 또는 License reconciliation 과정에서의 일시적 크래시. 
- **증거**: `kubectl get pods -n elastic-system` 결과 95회 재시작 기록 확인.
- **조치**: Operator의 리소스 Limit(특히 Memory) 상향 조정 필요성 검토.

### [Operational] Kafka 상태 확인
- **현상**: Kafka 리소스 reconciliation이 성공적으로 종료됨.
- **증거**: `2026-09-08T23:59:34+09:00 Kafka resource reconciliation finished`.
- **현재 상태**: Broker 및 Entity Operator 모두 Running 상태로 정상 서비스 중.

---

## 3. 기술적 추적 (Technical Traces)

- **ECK License Reconciliation**: `2026-09-08T23:51:42.948Z` 정상 종료.
- **Pod Health Trace (2026-09-09 01:00 UTC 기준)**:
  - `logging/logs-ls-0`: Running (Ready: True, Restarts: 0)
  - `kafka/lemuel-dual-role-0`: Running (Ready: True, Restarts: 1)
  - `elastic-system/elastic-operator-0`: Running (Ready: True, **Restarts: 95**)

---

## 4. 권고 사항 (Recommendations)

1. **ECK Manifest 수정**: `elasticsearch.spec.config`에서 예약된 설정 필드 제거 권고.
2. **Operator 리소스 모니터링**: 95회 재시작의 근본 원인 파악을 위한 `previous` 로그 정밀 분석.
3. **Logstash Heap 확보**: 만성적인 Logstash OOM 이슈 대응을 위해 heap dump 분석 및 메모리 튜닝 지속.

---
*본 리포트는 Lemuel Cluster RCA 자동화 파이프라인에 의해 생성되었습니다.*
