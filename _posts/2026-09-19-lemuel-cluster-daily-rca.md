---
layout: post
title: "르무엘 클러스터 일일 RCA 리포트 (2026-09-19)"
date: 2026-09-19 09:00:00 +0900
categories: devops
tags: [k3s, rca, isagal, ilwon, monitoring]
---

## 1. 개요
2026-09-19 09:00 KST 기준, 르무엘 클러스터(Lemuel Cluster)의 최근 24시간 운영 상태를 분석한 결과입니다. 
분석 대상 기간: 2026-09-18 08:34 UTC ~ 2026-09-19 00:00 UTC

### 종합 판정
- **상태**: **주의 (Warning / Unknown)**
- **주요 관찰 노드**: `isagal`, `ilwon`
- **핵심 요약**: `isagal` 노드에서 네트워크 오버레이 및 DNS 관련 체크 이상이 반복적으로 관측되었습니다. 다만, 실제 파드와 소유자(Owner) 상태는 정상(Ready)을 유지하고 있어 서비스 가용성에는 즉각적인 영향이 없는 것으로 판단됩니다.

---

## 2. 장애 및 이상 징후 분석

### [조사 필요] isagal 노드 네트워크 및 체크 엔진 이상
- **상태**: Unknown
- **대상**: `DaemonSet/node-self-healer` (상태: `ready=6/6`)
- **노드**: `isagal`
- **증거 (Trace)**:
    - `2026-09-18T14:42:00Z`: Overlay 네트워크 검사 중 `flannel.1` 인터페이스 부재 확인.
    - `2026-09-18T16:48:08Z`: `pod_density` 검사 중 DNS 조회 실패 (`<urlopen error [Errno -3] Try again>`).
- **원인 분석**: 
    - `isagal` 노드에만 국한된 현상으로, 클러스터 공용 서비스(CoreDNS 등)의 전역 장애보다는 해당 노드의 인터페이스 상태 또는 로컬 DNS 리졸버 일시 불능 가능성이 높습니다.
    - 소유자(DaemonSet)가 `6/6` 정상 상태를 유지하고 있으므로, 파드 자체가 죽은 것은 아니나 체크 로직이 실패했거나 노드 격리 징후일 수 있습니다.

### [해결됨/과거] ilwon 노드 Strimzi Operator 이벤트 루프 지연
- **상태**: Historical (Recovered)
- **대상**: `Deployment/strimzi-cluster-operator` (상태: `ready=1/1`)
- **노드**: `ilwon`
- **증거 (Trace)**:
    - `2026-09-18T08:34:25Z`: Vert.x event-loop thread가 6785ms 동안 블로킹됨 (임계치 2000ms 초과).
- **원인 분석**:
    - 대규모 리소스 조정(Reconciliation) 과정에서의 일시적 부하로 추정됩니다.
    - `2026-09-18T23:17:46Z` Kafka 리소스와 `2026-09-19T00:00:13Z` StrimziPodSet이 모두 `reconciled` 완료되었으며, 현재 소유자 상태가 `ready=1/1`이므로 정상 복구된 것으로 간주합니다.

### [과거] isagal 노드 k3s 서비스 일시 정지
- **상태**: Historical
- **노드**: `isagal`
- **증거 (Trace)**:
    - `2026-09-18T09:49:09Z`: `k3s_service` 상태가 `inactive,activating`으로 관측됨.
- **분석**: 과거 시점의 일시적 서비스 재시작으로 보이며, 현재는 `node-self-healer`가 정상 작동 중입니다.

---

## 3. 검증 데이터 (Evidence)

| 구분 | 대상 | 최종 상태 | 비고 |
| :--- | :--- | :--- | :--- |
| **Owner State** | `DaemonSet/node-self-healer` | `ready=6/6` | 정상 (Full Ready) |
| **Owner State** | `Deployment/strimzi-cluster-operator` | `ready=1/1` | 정상 (Full Ready) |
| **Kafka Sync** | `StrimziPodSet` | `reconciled` | 2026-09-19 00:00:13 UTC 확인 |

---

## 4. 조치 권고
1. **isagal 노드 집중 모니터링**: `flannel.1` 소실 및 DNS 오류가 재발하는지 확인 필요.
2. **self-healer 체크 로직 검증**: 실제 서비스는 정상인데 체크만 실패하는 '오탐' 가능성에 대해 healer 파드 로그 전수 조사를 권고합니다.

---
*본 리포트는 Lemuel RCA Automation에 의해 자동 생성되었습니다.*
