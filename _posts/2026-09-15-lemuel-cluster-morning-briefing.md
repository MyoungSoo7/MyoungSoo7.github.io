---
layout: post
title: "[Cluster] 2026-09-15 Lemuel 클러스터 아침 브리핑"
date: 2026-09-15 09:00:57 +0900
categories: ops
tags: [k3s, monitoring, briefing, infrastructure]
---

## 1. 개요 (Executive Summary)

- **측정 시각**: 2026-09-15 09:00:57 KST
- **외부 엔드포인트**: 5/5 OK (100% 가동)
- **노드 상태**: 5/6 Ready (1개 노드 NotReady: `ilwon`)
- **주요 이벤트**:
  - `louise` 노드 동시 종료 (07:00 KST): 15개 파드 0초 내 동시 종료 및 재시작.
  - `ilwon` 노드 장애 지속: NotReady 상태이며 관련 파드 Pending/Restarting 중.
  - 배치 Job 실패: `cluster-curator`, `etcd-leader-observe` 등 5건 실패.

## 2. 세부 상태 분석

### 2.1 외부 서비스 엔드포인트
모든 외부 엔드포인트는 정상 응답을 기록하고 있습니다. apiserver 상태와 무관하게 서비스 가용성은 유지되고 있습니다.

| Endpoint | Status | Size | Result |
| :--- | :--- | :--- | :--- |
| www.lemuel.co.kr | 200 | 17449B | OK |
| settlement.lemuel.co.kr | 200 | 4220B | OK |
| photos.lemuel.co.kr | 200 | 10566B | OK |
| memo.lemuel.co.kr | 200 | 1989B | OK |
| xr.lemuel.co.kr | 200 | 18578B | OK |

### 2.2 노드 상태 (Node Health)
`ilwon` 노드가 NotReady 상태로 관측되었습니다. `louise` 노드는 07:00 KST경 일시적인 불안정(Ready 상태 전이 및 파드 동시 종료)을 겪었으나 현재는 Ready 상태입니다.

| Node | Status | Roles |
| :--- | :--- | :--- |
| david | Ready | etcd |
| ilwon | **NotReady** | control-plane,etcd |
| isagal | Ready | <none> |
| lemuel | Ready | control-plane,etcd |
| louise | Ready | <none> |
| solomon | Ready | <none> |

### 2.3 비정상 파드 및 재시작 (Abnormal Pods & Restarts)
`ilwon` 노드 장애 및 리소스 스케줄링 이슈로 인해 9개 파드가 Pending 상태입니다. `fluent-bit`와 `memory-qa` 파드에서 잦은 재시작이 관측되었습니다.

**[Pending Pods]**
- `ai-ocr`, `kafka`, `monitoring`, `nfs-server`, `registry-mirror`, `trading-prod`, `velero` 네임스페이스의 일부 파드.

**[Significant Restarts (Increased)]**
- `logging/fluent-bit-jwjxp`: +60 (node: solomon)
- `logging/fluent-bit-mbmrn`: +41 (node: ilwon)
- `agent-system/memory-qa`: +36 (node: isagal)

## 3. 이상 징후 조사 (Incident Analysis)

### 3.1 `louise` 노드 동시 파드 종료 건
- **시간**: 2026-09-14T22:00:26Z (07:00:26 KST)
- **현상**: `ghost-prod`, `lemuel-xr-prod`, `ollama`, `openviking` 등 서로 다른 네임스페이스의 15개 파드가 정확히 같은 시각에 종료됨.
- **분석**: 특정 앱의 오류가 아닌 노드 레벨의 kubelet 중단 또는 apiserver와의 연결 유실로 인한 일괄 퇴출(Eviction) 혹은 노드 재시작으로 추정됩니다. `louise` 노드가 22:00:30Z에 Ready로 복구된 흔적이 이를 뒷받침합니다.

### 3.2 배치 Job 실패 현황
- `agent-system/cluster-curator`: 실패 지속 (failed=2)
- `kube-system/etcd-leader-observe`: 실패 (failed=1)
- `logging/log-error-alerter`: 실패 (failed=1)
- `settlement-prod/settlement-company-reputation`: 실패 (failed=2)

## 4. 조치 권고 사항

1. **`ilwon` 노드 상태 점검**: SSH 접속 및 K3S 서비스 상태 확인 필요. etcd 멤버 상태 점검(`etcdctl member list`).
2. **`louise` 노드 커널 로그 확인**: 동시 종료 시점의 OOM Killer 작동 여부 또는 시스템 패닉 흔적 조사.
3. **`fluent-bit` 리소스 튜닝**: `solomon` 및 `isagal` 노드에서 `fluent-bit` 재시작이 잦음. 메모리 제한 및 로그 버퍼링 설정 검토.
4. **Failed Job 수동 재실행 및 로그 분석**: 실패한 Job들의 로그(`kubectl logs`)를 확인하여 공통된 연결 이슈나 리소스 부족 확인.

---
*본 브리핑은 르무엘 클러스터 자동 프로브(lemuel_morning_probe_gate.py)의 데이터를 바탕으로 작성되었습니다.*
