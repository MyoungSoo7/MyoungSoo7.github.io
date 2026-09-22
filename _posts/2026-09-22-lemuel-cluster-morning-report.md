---
layout: post
title: "2026-09-22 르무엘 클러스터 데일리 리포트: David 노드 상관관계 재시작 분석"
date: 2026-09-22 09:05:00 +0900
categories: [DevOps, Kubernetes]
tags: [k3s, monitoring, cluster-report, david-node]
---

## 1. 종합 상태 (Summary)

2026년 9월 22일 오전 09:00 기준, 르무엘 클러스터는 **정상(OK)** 상태입니다. 모든 외부 엔드포인트가 응답 중이며, 노드 이탈은 발생하지 않았습니다. 단, 전일(9/21) 밤 David 노드에서 발생한 대규모 파드 재시작 이벤트를 확인했습니다.

| 항목 | 상태 | 비고 |
| :--- | :--- | :--- |
| **Probe Status** | OK | tunnel(127.0.0.1:16443) |
| **Nodes** | 6/6 Ready | 전원 정상 |
| **Endpoints** | 5/5 OK | HTTP 200 응답 확인 |
| **Abnormal Pods** | 0 | (Batch Job 제외) |
| **Failed Jobs** | 0 | 금일 실패 없음 |

---

## 2. 외부 엔드포인트 상태

모든 서비스가 안정적으로 운영되고 있습니다.

| Endpoint | Status | Content Length | Result |
| :--- | :--- | :--- | :--- |
| www.lemuel.co.kr | 200 | 17,449B | OK |
| settlement.lemuel.co.kr | 200 | 4,220B | OK |
| photos.lemuel.co.kr | 200 | 10,566B | OK |
| memo.lemuel.co.kr | 200 | 1,989B | OK |
| xr.lemuel.co.kr | 200 | 18,578B | OK |

---

## 3. 주요 이슈 분석: David 노드 동시 재시작 (Correlated Restarts)

### 현상 파악
- **발생 시각**: 2026-09-21 22:57:53 KST (13:57:53Z)
- **대상**: David 노드 소속 파드 35개
- **특이점**: 0초 안에 모든 파드가 동시에 재시작됨.

### 원인 추정
- 파드 자체의 비정상 종료가 아닌, **Node 수준의 Kubelet 재시작** 또는 **APIServer 연결 유실**로 인한 일괄 리셋으로 판단됩니다.
- 현재 David 노드는 `Ready` 상태이며, etcd 역할을 안정적으로 수행 중입니다.
- 개별 파드의 장애가 아니므로 서비스 로직 수정은 불필요하며, 인프라 가용성 차원에서 관찰이 필요합니다.

---

## 4. 배치 작업 및 크론잡 현황

- **Settlement Job**: `settlement-company-reputation` Job에서 1회 실패가 있었으나, Kubernetes 재시도 정책에 의해 최종 성공했습니다. (장애 아님)
- **Backups**: `pg-backup` 등 주요 데이터 백업 작업이 정상적으로 완료되었습니다.

---

## 5. 기술적 근거 (Trace)

```text
PROBE_PATH=tunnel(127.0.0.1:16443)
PROBE_AT=2026-09-22 09:00:18 KST
NODES_TOTAL=6, NODES_NOT_READY=0
RESTARTS_INCREASED=35 (Node: david)
```

본 보고서는 `lemuel_morning_probe_gate.py`의 자동화된 검증 결과를 바탕으로 작성되었습니다.

---
