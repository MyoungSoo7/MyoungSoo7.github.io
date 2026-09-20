---
layout: post
title: "Lemuel Cluster Daily RCA: 2026-09-20"
date: 2026-09-20 09:00:00 +0900
categories: devops
tags: k3s rca homelab
---

# Lemuel Cluster Daily RCA (2026-09-20)

## 1. 개요 (Summary)
금일 Lemuel 클러스터의 상태 점검 결과, **전체 클러스터 마스터 노드 불능(Down)** 상태가 확인되었습니다. `k8s-rca-daily.sh` 수집 단계에서 API 서버 접속 실패로 인해 상세 파드 분석이 수행되지 않았습니다.

## 2. 장애 증거 및 분석 (Evidence & Analysis)

### 2.1 데이터 수집 실패 (Trace)
- **증상**: `RCA_COLLECT_FAILED` 발생.
- **상태**: `/tmp/k8s-rca-corpus` 내 수집된 데이터 0건.

### 2.2 인프라 도달 가능성 점검 (Infrastructure)
- **Master Node (192.168.219.101)**: 
    - Mac 및 Isagal 워커 노드에서의 `ping` 응답 없음 (`Destination Host Unreachable`).
    - SSH 접속 (Port 2652) 시도 시 `Operation timed out` 발생.
- **Worker Node (192.168.219.108 - Isagal)**: 
    - 정상 동작 중 (Uptime 9일).
    - 단, 마스터 노드와의 통신 단절로 인해 K8s API 서비스 연동 불가.

### 2.3 로컬 리소스 영향 (Local Impact)
- **SSH 터널 좀비 프로세스**: Mac 로컬 환경에서 `192.168.219.101`로 향하는 SSH 터널 프로세스(`ssh -fN -L 16443...`) 수백 개가 중복 실행 중임이 확인되었습니다. 이는 마스터 노드 불능 상태에서 스크립트가 반복 실행되며 발생한 부작용으로 판단됩니다.

## 3. 원인 진단 (Root Cause)
- **잠정적 원인**: 마스터 노드(`lemuel`)의 하드웨어 전원 차단 또는 네트워크 인터페이스 장애.
- **만성 여부**: 신규 장애 (이전 Trace 기록 확인 필요하나 현재 도달 불가).

## 4. 조치 권고 (Recommendations)
1. **마스터 노드 물리 상태 확인**: `192.168.219.101` 장비의 전원 및 LAN 케이블 연결 상태 확인이 필요합니다.
2. **Mac 로컬 정리**: 중복 실행 중인 SSH 프로세스 강제 종료 (`pkill -f "ssh -fN -L 16443"`)가 필요합니다.
3. **네트워크 복구**: VPN 또는 로컬 네트워크 경로 정상화 후 K3s 서비스 상태 재점검.

---
*본 보고서는 Hermes Agent에 의해 자동 생성되었습니다.*
