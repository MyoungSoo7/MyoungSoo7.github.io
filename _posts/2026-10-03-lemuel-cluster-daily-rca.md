---
layout: post
title: "Lemuel Cluster Daily RCA (2026-10-03)"
date: 2026-10-03 09:00:00 +0900
categories: [Ops, Kubernetes]
tags: [k3s, rca, isagal]
---

# Lemuel Cluster 일일 RCA 보고서 (2026-10-03)

## 1. 요약 (Summary)
금일 클러스터 점검 결과, **isagal 노드의 물리적 재부팅**으로 인한 일시적인 서비스 중단 및 컨테이너 재시작 이벤트가 확인되었습니다. 현재 모든 노드 및 주요 서비스는 정상 수렴(Ready) 상태입니다.

## 2. 주요 인시던트 분석

### [Historical] isagal 노드 재부팅 및 시스템 수렴
- **시간**: 2026-10-02 10:13:11Z (부팅) ~ 10:18:56Z (수렴 완료)
- **증상**: 13개 컨테이너가 8개 네임스페이스에 걸쳐 동시에 종료됨 (exit 255/Unknown).
- **원인**: `isagal` 노드의 물리적/커널 레벨 재부팅 (`within_lookback=yes`).
- **영향 범위**: Falco, IoT Simulator, Node-local-dns 등 DaemonSet 및 Pod.
- **현재 상태**: `ready=6/6` (정상 수렴). 노드 재부팅 후 파드들이 정상적으로 재스케줄링됨.

### [Observation] Falco 보안 규칙 탐지 (정상 동작)
- **내용**: `Redirect STDOUT/STDIN` 규칙 반복 탐지.
- **분석**: `isagal` 노드의 `wifi-probe` 모니터링 스크립트(Python3)가 수행하는 `ping` 동작에 의한 것으로 확인됨.
- **판정**: 정상적인 모니터링 활동으로 인한 탐지이며, 특정 노드에 국한된 동작임.

### [Resolved] 백업 리소스(PVB) 누락 경고
- **내용**: Velero PVB(Pod Volume Backup) 누락 경고.
- **원인**: 2026-09-25 생성된 과거 백업 데이터의 만료 또는 삭제.
- **확인**: 최근 백업(`hourly-critical-20261002200029`)은 정상 완료됨을 확인.

## 3. 노드 상태 (Node Status)

| Node | Booted At | Status | Reboots (Window) |
| :--- | :--- | :--- | :--- |
| **isagal** | 2026-10-02 10:13:11 | **Active (Recovered)** | 1 |
| david | 2026-09-21 13:57:27 | Stable | 0 |
| ilwon | 2026-09-20 09:55:35 | Stable | 0 |
| lemuel | 2026-09-20 03:44:18 | Stable | 0 |
| louise | 2026-09-14 22:00:08 | Stable | 0 |
| solomon | 2026-09-13 08:33:37 | Stable | 0 |

## 4. 증거 및 추적 (Evidence & Trace)
- **RCA_NODE_BOOT**: `isagal` 노드의 `within_lookback=yes` 판정.
- **RCA_NODE_EVENT**: 2026-10-02 10:16:06Z 기준 13개 컨테이너 동시 종료 트레이스.
- **RCA_RECOVERED_BY_RETRY**: `settlement-company-reputation` 파드가 재시도로 회복된 기록 확인.

---
*본 보고서는 `k8s-rca-daily.sh`가 수집한 데이터를 바탕으로 Hermes Agent에 의해 자동 생성되었습니다.*
