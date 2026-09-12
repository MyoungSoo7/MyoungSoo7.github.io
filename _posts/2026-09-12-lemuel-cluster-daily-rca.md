---
layout: post
title: "르무엘 클러스터 일일 RCA 리포트 (2026-09-12)"
date: 2026-09-12 09:05:16 +0900
categories: [DevOps]
tags: [k8s, rca, automation, elasticsearch]
---

## 1. 개요
`k8s-rca-daily.sh` 수집 데이터에 기반한 르무엘 클러스터 24시간 분석 리포트입니다.

- **분석 시간 범위**: 2026-09-11 ~ 2026-09-12 (KST 기준 24시간)
- **신뢰도**: 0.96
- **신뢰도 근거**: 최근 시간창의 직접 로그에 경고 대상 필드와 timestamp가 명시되어 있고, Elasticsearch owner의 현재 상태가 ready=1/1로 확인됨. 원인이 louise 노드에 집중된다는 점도 모든 증거의 node 값으로 직접 확인됨. 다만 경고가 현재 서비스 영향으로 이어졌다는 증거는 없어 장애 영향 자체는 주장하지 않음

---

## 2. 장애 및 특이사항 분석 (Current Incidents)

### [1] Elasticsearch ECK reconciliation에서 사용자 구성으로 금지된 내부 예약 설정 경고와 알 수 없는 필드가 반복 관찰됨
- **상태**: CURRENT
- **대상 노드**: `louise` (Node-specific)
- **소유자(Owner)**: `StatefulSet/elastic-operator` (ready=1/1)
- **원인 분석**: Elasticsearch manifest의 spec.nodeSets[0].config.cluster.initial_master_nodes 및 각 nodeSets의 xpack.security.enabled가 사용자 구성으로 직접 설정되어 있고, 생성·상태 메타데이터 필드가 manifest에 포함되어 있음. 관련 증거가 모두 louise 노드에 집중되어 있어 클러스터 공용 서비스 장애로 단정할 근거는 없음
- **증거 (Evidence)**:
  - `2026-09-11T19:10:41.840Z: cluster.initial_master_nodes 및 nodeSets[0-2].xpack.security.enabled에 대해 'Forbidden: Configuration setting is reserved for internal use' 경고 발생`
  - `2026-09-11T20:02:54.689Z: 동일한 내부 예약 설정 경고 반복`
  - `2026-09-11T20:02:33.197Z: spec.http.service.metadata.creationTimestamp, volumeClaimTemplates.metadata.creationTimestamp/status, transport.service.metadata.creationTimestamp 등의 unknown field 관찰`
  - `2026-09-11T20:02:33.024Z: Elasticsearch cannot be reached yet, re-queuing. 이후 owner는 ready=1/1 상태`
- **권고 조치**: approved_change_only

---

## 3. 해결 및 완화된 항목 (Resolved/Recovered)
- `RCA_RECOVERED_BY_RETRY` 기준: 해당 시간창 내 자동 재시도로 해결된 항목 없음.

---

## 4. 종합 평가
Elasticsearch ECK Operator 관련 설정 경고가 지속되고 있으나, 서비스 가용성(`ready=1/1`)에는 지장이 없는 상태입니다. louise 노드에 집중된 로그 특성상 클러스터 전체 장애로 번질 위험은 낮으나, manifest에서 예약된 필드 및 unknown field를 제거하여 reconciliation 노이즈를 줄이는 작업이 권장됩니다.

---
*본 리포트는 Hermes Agent에 의해 자동 생성 및 검증되었습니다.*
