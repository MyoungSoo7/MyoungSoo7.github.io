---
layout: post
title: "[RCA] 2026-09-16 르무엘 클러스터 일일 장애 분석 리포트"
date: 2026-09-16 10:00:00 +0900
categories: [Ops, Kubernetes]
tags: [k8s, rca, homelab]
---

## 1. 요약 (Executive Summary)

2026-09-16 분석 결과, 현재 클러스터 내 지속되고 있는 크리티컬한 장애는 발견되지 않았습니다. 관찰된 주요 이벤트들은 모두 **Historical(과거 시점 발생 후 복구됨)** 또는 **Unknown(영향도 미미)** 상태이며, 소유자(Owner) 기준 Ready 상태가 정상(N/N)인 것을 확인하였습니다.

## 2. 장애 및 특이사항 분석

### 2.1. 애플리케이션 시작 시 DB 연결 지연 (Resolved)
- **대상**: `ai-ocr-app` (ilwon 노드), `trading-app` (louise 노드)
- **현상**: 컨테이너 기동 초기 PostgreSQL 연결 실패(`SQL State 08001` / `connection attempt failed`) 발생.
- **분석**:
    - `ai-ocr-app`: 재기동 후 5.033초 만에 애플리케이션 정상 시작 확인 (Ready 1/1).
    - `trading-app`: 연결 실패 이후 정상 기동되었으며, 2026-09-16 09:00 기준 KIS 토큰 발급 및 현재가 조회 업무 호출 성공이 Trace로 입증됨.
- **판정**: **해결됨 (Historical)**. 기동 시점의 일시적 네트워크/DB 가용성 지연으로 판단됨.

### 2.2. 로그/모니터링 스택 일시적 저하 (Resolved)
- **대상**: `logs-kb` (louise 노드)
- **현상**: Task Manager 및 Kibana의 일시적 degraded 상태 관찰.
- **분석**: `expired hot timestamps`로 인해 Task Manager가 일시적으로 Unhealthy 되었으나, 약 9초 후 자동 복구됨을 로그로 확인 (2026-09-15 19:12:36 UTC).
- **판정**: **해결됨 (Historical)**.

### 2.3. 시스템 메트릭 수집 이상 (Low Impact)
- **대상**: `kps-prometheus-node-exporter` (ilwon 노드)
- **현상**: `netclass` 콜렉터가 `veth` 인터페이스 파일을 읽지 못함.
- **분석**: 파드/컨테이너 생명주기에 따라 인터페이스(`veth05958106`)가 삭제된 시점과 수집 시점의 간극으로 발생한 일회성 오류임.
- **판정**: **정상 동작 (Historical)**.

## 3. 추가 조사 필요 항목 (Under Investigation)

- **node-self-healer (ilwon 노드)**: `time_sync` 점검 시 이상(`no`) 기록이 반복적으로 관찰됨. 현재 DaemonSet은 `Ready 6/6`으로 정상이나, 특정 노드(ilwon)의 시간 동기화 정밀도를 확인 중입니다.
- **logs-kb Telemetry 경고**: `Telemetry Services are not reachable` 경고가 반복되나, 서비스 가용성(Ready 1/1)에는 영향이 없음을 확인하였습니다.

## 4. 분석 환경 및 근거
- **분석 시간 범위**: 2026-09-15 07:17:13Z ~ 2026-09-16 09:00:10Z (KST 기준 약 24시간)
- **데이터 소스**: k8s-rca-daily.sh 수집 Trace 및 Owner State 검증 데이터.
- **신뢰도**: 높음 (실제 로그 및 애플리케이션 비즈니스 호출 성공 Trace 기반)

---
*본 리포트는 Hermes Agent에 의해 자동 생성되었습니다.*
