---
layout: post
title: "르무엘 클러스터 일일 RCA 리포트 (2026-09-18)"
date: 2026-09-18 09:00:00 +0900
categories: [Ops, Kubernetes]
tags: [k3s, rca, lemuel, monitoring]
---

## 1. 개요
- **분석 시간 범위**: 2026-09-17 12:47:04Z ~ 2026-09-17 23:16:09Z (실제 증거 기준)
- **클러스터 상태**: 현재 장애 없음 (모든 소유자 Ready 상태 정상)
- **요약**: 분석 기간 중 4건의 일시적 이상 징후가 관찰되었으나, 모두 자동 복구되거나 현재 정상 상태(Ready=N/N)임을 확인하였습니다.

## 2. 현재 장애 항목
- **해당 없음**

## 3. 과거 이력 및 해결된 항목 (Historical)

### [frpc] FRP 서버 연결 timeout
- **노드**: `louise`
- **상태**: 해결됨 (Deployment/frp-frpc ready=1/1)
- **원인**: louise 노드에서 FRP 서버(ClusterIP)로의 연결 시 timeout 발생. 공용 서비스 장애 증거는 부족하며 노드 국소 현상으로 추정됩니다.
- **증거**: `2026-09-17T19:41:42.902Z: dial tcp 10.43.116.235:7000: i/o timeout`

### [Strimzi] Vert.x event-loop blocking
- **노드**: `ilwon`
- **상태**: 정상 유지 (Deployment/strimzi-cluster-operator ready=1/1)
- **원인**: Operator 내부 event-loop가 2260ms 동안 점유됨. 이후 Kafka reconciliation이 성공(23:16:09Z)하여 운영상 영향은 없었습니다.
- **증거**: `2026-09-17T22:44:08Z: event-loop-thread-0가 2260ms 동안 blocked`

### [Self-Healer] isagal 노드 상태 이상 연쇄 관찰
- **노드**: `isagal`
- **상태**: 정상 (DaemonSet/node-self-healer ready=6/6)
- **원인**: isagal 노드에서 overlay network, pod density 조회 실패, k3s-agent 불안정 현상이 동시 관찰됨. 특정 시점에 노드 자원 부족 또는 agent 지연이 발생했으나 현재는 복구된 상태입니다.
- **증거**: `flannel.1 없음`, `pod_density 조회 실패`, `k3s-agent inactive/activating`

### [Velero] PVB reconcile 실패 (PVB not found)
- **노드**: `david`
- **상태**: 정상 (DaemonSet/node-agent ready=6/6)
- **원인**: 백업 작업 중 InProgress 상태의 PodVolumeBackup(PVB) 삭제 시점에 reconciliation 시도가 겹쳐 'not found' 에러 발생.
- **증거**: `2026-09-17T12:52:35Z: finalizer 제거 중 PVB not found`

## 4. 노드별 분석 요약
- **isagal**: k3s-agent 및 네트워크 인터페이스 불안정 이력 (조사 필요)
- **louise**: 일시적 네트워크 타임아웃
- **ilwon**: Operator 부하 (일시적)
- **david**: 백업 프로세스상 자원 삭제 타이밍 이슈

---
*본 리포트는 k8s-rca-daily.sh 에 의해 자동 생성되었습니다.*
