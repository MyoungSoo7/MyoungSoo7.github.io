---
layout: post
title: "Lemuel Cluster Daily RCA - 2026-10-02"
date: 2026-10-02 09:00:00 +0900
categories: devops
tags: k8s rca homelab
---

# 르무엘 클러스터 일일 RCA 리포트 (2026-10-02)

본 리포트는 `k8s-rca-daily.sh`가 수집한 Trace와 이벤트를 바탕으로 작성되었습니다.

## 1. 요약 (Executive Summary)
- **전체 상태**: 주의 (Warning)
- **주요 탐지**: 
    - 노드 `isagal` 통신 불능 (`ssh_unreachable`) 탐지.
    - 배치 작업 `settlement-company-reputation` 재시도 후 성공 처리.
- **분석 시간 범위**: 2026-10-01 09:00 ~ 2026-10-02 09:00 (KST)

## 2. 인시던트 분석 (Incident Analysis)

### [해결됨] settlement-company-reputation 배치 재시도 회복
- **대상**: `settlement-prod/settlement-company-reputation-29848200-5n79s`
- **노드**: `lemuel`
- **상태**: `Complete` (회복됨)
- **상세**: 백오프 재시도 끝에 최종 성공 처리됨. `RCA_REPORT_RULE`에 따라 정상 동작으로 간주하며 현재 장애 아님.

## 3. 노드 상태 점검 (Node Health)

| 노드명 | 부팅 시각 | 상태 | 비고 |
| :--- | :--- | :--- | :--- |
| **isagal** | - | **ssh_unreachable** | **통신 불능 (점검 필요)** |
| david | 2026-09-21 | Stable | 시간창 내 재부팅 없음 |
| ilwon | 2026-09-20 | Stable | 시간창 내 재부팅 없음 |
| lemuel | 2026-09-20 | Stable | 시간창 내 재부팅 없음 |
| louise | 2026-09-14 | Stable | 시간창 내 재부팅 없음 |
| solomon | 2026-09-13 | Stable | 시간창 내 재부팅 없음 |

## 4. 근본 원인 분석 (Root Cause Analysis)

### 노드 `isagal` 접근 불가
- **증상**: SSH 연결 실패.
- **영향**: 해당 노드는 고사양 워커(40-core)이므로, CPU 집약적인 추론 작업이나 워크로드 할당에 제한이 있을 수 있음.
- **권고**: 
    - 물리적 전원 상태 확인.
    - 네트워크 연결 및 내부 IP(`192.168.219.108`) 가용성 확인.
    - K3s 에이전트 프로세스 상태 점검.

## 5. 분석 기준 및 규칙 (Metadata)
- **소스**: `k8s-rca-daily.sh`
- **신뢰도**: 높음 (실제 노드 부팅 기록 및 SSH 연결 테스트 결과 기반)
- **Rule 적용**: 파드가 아닌 소유자(Job)의 최종 상태를 기준으로 판정함.

---
*Reported by Hermes Agent OS (Cron Job)*
