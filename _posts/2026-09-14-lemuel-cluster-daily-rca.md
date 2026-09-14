---
layout: post
title: "2026-09-14 Lemuel Cluster Daily RCA Report"
date: 2026-09-14 09:00:00 +0900
categories: Ops RCA
---

## 1. 개요 (Summary)
2026-09-13 UTC 기준 르무엘 클러스터에서 감지된 장애 항목에 대한 근거 기반 분석 리포트입니다. 주요 이슈는 **solomon 노드의 국소적 불안정성**과 이로 인한 **Elasticsearch 데이터 노드 영향**으로 요약됩니다.

## 2. 장애 상세 (Incidents)

### [장애 1] solomon 노드 서비스 및 네트워크 불안정
- **현상**: `node-self-healer`가 k3s 서비스(inactive), overlay(flannel.1 부재), pod_density 조회 실패를 반복 기록.
- **분석 시간**: 2026-09-13T08:37:09Z ~ 2026-09-13T12:37:44Z
- **노드**: `solomon`
- **상태**: DaemonSet/node-self-healer `ready=6/6` (자가 회복 또는 플래핑)
- **증거**:
  - `CHECK k3s_service = 이상 (inactive,activating)`
  - `CHECK overlay = 이상 (flannel.1 없음)`
  - `CHECK pod_density = 이상 (조회실패:<urlopen error [Errno -3] Try again)`
  - `BrokenPipeError` 발생 (체크 스크립트 통신 장애)

### [장애 2] logs-es-cold 마스터 발견 실패
- **현상**: Elasticsearch cold 노드가 master(logs-es-hot-0)를 발견하지 못하고 쿼럼에서 제외됨.
- **노드**: `solomon`
- **원인**: [장애 1]에서 확인된 `solomon` 노드의 네트워크/커널 불안정성이 상위 어플리케이션인 ES에 파급된 것으로 판단됨.
- **증거**: `logs-es-hot-0`에 대한 discovery 및 leader check timeout 관찰.

### [장애 3] louise 노드 API 서버 도달 불가 (국소적)
- **현상**: `apiserver_reach` 검사에서 HTTP 000(응답 없음) 기록.
- **분석 시간**: 2026-09-13T08:25:22Z ~ 2026-09-13T23:42:09Z
- **노드**: `louise`
- **상태**: DaemonSet/node-self-healer `ready=6/6`
- **증거**: `CHECK apiserver_reach = 이상 (HTTP 000)` 반복 기록.

## 3. 원인 분석 (Root Cause Analysis)
- **판정**: **solomon 노드 특정 장애 (Node-Local Issue)**
- **근거**: 장애 증거가 `solomon` 노드에 집중되어 있으며, 동일 시간대 타 노드에서 클러스터 공용 서비스(Control Plane) 마비 증거는 발견되지 않음. `BrokenPipeError`는 노드 내 리소스 부족 또는 네트워크 스택의 일시적 중단 가능성을 시사함.

## 4. 조치 및 권고 (Action Items)
- **investigate**: `solomon` 노드의 시스템 로그(dmesg, journalctl)를 확인하여 k3s 서비스 중단 및 flannel 인터페이스 소멸의 근본 원인(OOM, Disk I/O Wait 등) 조사 필요.
- **monitor**: `louise` 노드와 API 서버 간의 간헐적 통신 지연 여부 지속 관찰.

---
*본 리포트는 k8s-rca-daily.sh에 의해 수집된 Trace를 바탕으로 Hermes Agent가 자동 생성하였습니다.*
