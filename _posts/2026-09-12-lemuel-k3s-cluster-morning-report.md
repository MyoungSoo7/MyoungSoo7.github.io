---
layout: post
title: "[Report] 2026-09-12 Lemuel K3s Cluster Morning Briefing"
date: 2026-09-12 09:01:00 +0900
categories: [DevOps]
tags: [k3s, monitoring, homelab, kubernetes]
---

# 2026-09-12 Lemuel K3s 클러스터 아침 브리핑

본 리포트는 `lemuel_morning_probe_gate.py`의 자동화된 프로브 결과를 바탕으로 작성되었습니다.

## 1. 종합 상태 (Summary)

| 항목 | 상태 | 비고 |
| :--- | :--- | :--- |
| **PROBE STATUS** | OK | 2026-09-12 09:00:37 KST 측정 |
| **Nodes** | 6/6 Ready | David, Ilwon, Isagal, Lemuel, Louise, Solomon |
| **Endpoints** | 5/5 OK | 외부 서비스 엔드포인트 전원 정상 |
| **Failed Jobs** | 1 건 | `agent-system/cluster-curator` 실패 |

---

## 2. 세부 지표 분석

### 외부 엔드포인트 (External Endpoints)
모든 외부 서비스가 정상적으로 응답하고 있습니다.

| 서비스 URL | 응답 코드 | 크기 | 상태 |
| :--- | :--- | :--- | :--- |
| www.lemuel.co.kr | 200 | 17449B | OK |
| settlement.lemuel.co.kr | 200 | 4220B | OK |
| photos.lemuel.co.kr | 200 | 10566B | OK |
| memo.lemuel.co.kr | 200 | 1989B | OK |
| xr.lemuel.co.kr | 200 | 18578B | OK |

### 워크로드 상태 (Workload Health)
배치 작업 중 특이사항이 발견되었습니다.

- **실패한 작업**: `agent-system/cluster-curator-29817180` (Failed=2). 시스템 정리 작업이 연속 실패 중이므로 수동 로그 확인이 필요합니다.
- **정상 참작**: `settlement-prod/settlement-company-reputation` 파드는 `solomon` 노드에서 실패 흔적이 있으나, Job 자체는 재시도로 성공하였습니다. (장애 아님)

### 파드 재시작 탐지 (Restart Delta)
최근 878분(약 14시간) 동안의 재시작 증가분입니다. `louise` 노드에 부하 또는 불안정성이 의심됩니다.

| 네임스페이스/파드 | 증가분 | 누적 | 노드 |
| :--- | :--- | :--- | :--- |
| elastic-system/elastic-operator-0 | +10 | 34 | louise |
| monitoring/kps-kube-state-metrics | +10 | 88 | solomon |
| sops-operator/sops-operator | +6 | 21 | louise |
| kafka/strimzi-cluster-operator | +1 | 9 | louise |

---

## 3. 관리자 조언 (Action Items)

1. **`cluster-curator` 실패 조사**: `agent-system` 네임스페이스의 큐레이터 로그를 점검하여 정리 작업이 실패하는 원인(권한, 스토리지 등)을 파악해야 합니다.
2. **`louise` 노드 리소스 모니터링**: Elastic Operator와 SOPS Operator의 잦은 재시작은 메모리 부족(OOM)이나 노드 압박일 가능성이 큽니다.
3. **`solomon` 노드 체크**: `kube-state-metrics`의 재시작이 지속되고 있습니다.

---

**Trace Integrity Verified.**
*Probe Path: tunnel(127.0.0.1:16443)*
*Collected at: 2026-09-12 09:00:37 KST*
