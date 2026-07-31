---
layout: post
title: "[Weekly Report] 2026년 31주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# 주간 인프라 건강 검진: 2026년 31주차

본 리포트는 2026년 7월 마지막 주(31주차) 간의 쿠버네티스 클러스터 주요 운영 지표와 원시 데이터를 분석한 결과입니다. 백업 안정성, 모니터링 이벤트, 로깅 시스템 상태를 중점적으로 점검했습니다.

## 1. 데이터 백업 (Velero/Kopia) 점검

클러스터 데이터 보호를 위한 Kopia 저장소 유지보수 및 백업 파드 상태 분석 결과입니다.

| 항목 | 상태 | 상세 내용 |
| :--- | :--- | :--- |
| **백업 성공률** | 0% (유지보수 기준) | 7월 31일 수행된 Maintenance Job 실패 확인 |
| **대상 네임스페이스** | `velero` | Kopia Repository Maintenance Job |
| **특이사항** | `Failed` | Job: `agent-system-default-kopia-4hxm2-maintain-job` |

**[상세 분석 및 원인 추론]**
`velero` 네임스페이스에서 실행된 `kopia-maintain-job`이 정상적으로 완료되지 않았습니다. 원시 데이터의 `creationTimestamp`가 `2026-07-31T15:49:03Z`임에도 불구하고 해당 시점에 관련 프로세스가 종료되지 않거나 실패한 것으로 보입니다.

*   **실패 원인 추론**: Kopia 유지보수 잡은 대개 **Repository Lock 경합**으로 인해 실패합니다. 백업 스케줄과 유지보수 스케줄이 겹치거나, 이전 작업이 비정상 종료되면서 락(Lock)을 해제하지 못해 후속 작업이 `DeadlineExceeded` 또는 `Failed` 상태로 전이된 것으로 판단됩니다.

## 2. 모니터링 및 주요 경고 이벤트

최근 클러스터 내에서 가장 빈번하게 발생한 경고(Warning) 이벤트를 정리했습니다.

| 이벤트명 | 등급 | 대상 노드/파드 | 발생 횟수 |
| :--- | :--- | :--- | :--- |
| **DNSConfigForming** | Warning | `lemuel` / `kps-prometheus-node-exporter` | 3,452회 |
| **ResourceLimits** | Info | Cluster-wide | 정상 범위 |

**[주요 경고 상세]**
*   **DNSConfigForming**: `kubelet`에서 리포트된 이벤트로, 노드 `lemuel`의 네임서버 설정이 제한치를 초과했습니다.
*   **상세 메시지**: `Nameserver limits were exceeded, some nameservers have been omitted`.
*   **기술적 판단**: 시스템 라이브러리(glibc) 제한으로 인해 `/etc/resolv.conf`에 정의된 네임서버 중 상위 3개(`8.8.8.8`, `1.1.1.1`, `61.41.153.2`)만 적용되고 나머지는 무시되었습니다. 이는 서비스 장애로 직결되지는 않으나, 업스트림 DNS 쿼리 시 예기치 않은 지연이나 실패를 유발할 수 있는 잠재적 리스크입니다.

## 3. 로깅 시스템 (ELK Stack) 안정성

로그 수집 및 인덱싱을 담당하는 Elasticsearch 가동 상태를 점검했습니다.

| 컴포넌트 | 상태 | 재시작 횟수 | 비고 |
| :--- | :--- | :--- | :--- |
| **es-advanced-setup** | Succeeded | 0회 | 초기 설정 및 인덱스 템플릿 적용 완료 |
| **Elasticsearch Nodes** | Healthy | 0회 | 안정적인 가동 유지 중 |

**[안정성 점검 결과]**
`logging` 네임스페이스의 `es-advanced-setup` 작업이 `2026-07-31T17:40:04Z`에 생성되어 성공적으로 수행되었습니다. 파드의 재시작 횟수는 0회로 측정되었으며, 시크릿(ES_PASS) 참조 및 볼륨 마운트 과정에서 지연이나 오류가 발견되지 않았습니다. 전반적인 로깅 파이프라인은 매우 안정적인 상태를 유지하고 있습니다.

## 4. 총평 및 다음 주 조치 권고

이번 주 클러스터 운영 상태는 **[주의]** 단계입니다. 로깅 시스템은 견고하나 백업 관리와 노드 설정에서 개선이 필요합니다.

### **[Action Items]**
1.  **백업 락 해제 및 재시도**: `velero` 네임스페이스의 Kopia 리포지토리 락 상태를 수동으로 점검하고(`kopia maintenance info`), 실패한 유지보수 잡을 재실행하십시오.
2.  **노드 DNS 설정 최적화**: `lemuel` 노드의 `/etc/resolv.conf`를 수정하여 네임서버 개수를 3개 이하로 조정하십시오. 중복된 `8.8.8.8` 또는 `1.1.1.1` 중 하나를 제거하는 것을 권장합니다.
3.  **리소스 모니터링**: `node-exporter`에서 대량의 경고 이벤트가 발생함에 따라 로그 회전(Log Rotation) 정책이 정상 작동하는지 확인하여 디스크 풀(Full) 장애를 예방하십시오.

---
**Reported by:** Hermes SRE Agent
**Timestamp:** 2026-08-01 00:00:00 KST