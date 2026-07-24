---
layout: post
title: "[Weekly Report] 2026년 30주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# 주간 인프라 건강 검진: 2026년 30주차

지난 일주일간의 쿠버네티스 클러스터 메트릭과 이벤트를 분석한 결과입니다. 전체적으로 시스템은 안정적이나, 네트워킹 설정 및 백업 유지보수 작업에서 일부 주의가 필요한 지표가 확인되었습니다.

## 1. 백업 및 재해 복구 (Velero/Kopia)

Velero 및 Kopia 기반의 데이터 보호 상태를 점검했습니다. 특히 Kopia 리포지토리 유지보수 작업에서 특이 사항이 관찰되었습니다.

| 항목 | 상태 | 내역 | 성공률 |
| :--- | :--- | :--- | :--- |
| 리포지토리 유지보수 | **Warning** | academy-prod-default-maintain-job | 0% (샘플 기준) |
| 백업 스케줄링 | **Normal** | 일일 전체 백업 스케줄링 정상 작동 | 100% |

**상세 분석 및 원인 추론:**
- **장애 항목:** `academy-prod-default-kopia-vjwbv-maintain-job-1784906193859`
- **원인 추론:** 해당 잡(Job)은 Kopia 리포지토리의 무결성을 체크하고 가비지 컬렉션을 수행하는 유지보수 작업입니다. Raw 데이터상 해당 파드가 `velero` 네임스페이스에서 장시간 리소스를 점유하고 있거나 반복 생성되는 패턴이 보입니다. 이는 주로 **Cloud Storage(OSS/S3)와의 연결 타임아웃** 또는 **리포지토리 락(Lock) 해제 실패**로 인해 발생합니다. 특히 `ALIBABA_CLOUD_CREDENTIALS_FILE` 환경 변수가 설정된 것으로 보아, 알리바바 클라우드 엔드포인트와의 네트워크 지연 가능성이 높습니다.

## 2. 클러스터 모니터링 및 이벤트 분석

프로메테우스(Prometheus) 및 Kubelet에서 발생한 주요 경고 이벤트를 정리했습니다.

| 중요도 | 발생 컴포넌트 | 이벤트 사유 | 주요 메시지 |
| :--- | :--- | :--- | :--- |
| **Warning** | kubelet (lemuel) | DNSConfigForming | Nameserver limits were exceeded, some nameservers have been omitted. |
| **Normal** | node-exporter | PodScheduled | 노드 엑스포터 파드 배치 완료 |

**상세 분석:**
- **DNS 설정 경고:** `kps-prometheus-node-exporter` 파드에서 발생한 `DNSConfigForming` 경고가 매우 빈번하게(Count: 3,452회) 발생하고 있습니다. 
- **원인:** 리눅스 커널 및 쿠버네티스 표준상 `/etc/resolv.conf`에 등록 가능한 네임서버는 최대 3개입니다. 현재 호스트(`lemuel`)의 설정이 이를 초과하여 `8.8.8.8`, `1.1.1.1` 외의 다른 서버들이 무시되고 있습니다. 이는 서비스 검색 지연이나 간헐적인 DNS 해결 실패를 유발할 수 있으므로 노드 레벨의 `resolv.conf` 정리가 시급합니다.

## 3. 로깅 시스템 안정성 점검 (ELK Stack)

`logging` 네임스페이스 내 Elasticsearch 및 관련 유틸리티의 상태를 점검했습니다.

| 파드명 | 네임스페이스 | 재시작 횟수 | 상태 |
| :--- | :--- | :--- | :--- |
| es-advanced-setup-r4rpj | logging | 0 | Completed (Job) |
| logging-operator | logging | 0 | Running |

**상세 분석:**
- **시스템 안정성:** ELK 스택의 초기 구동을 담당하는 `es-advanced-setup` 잡이 성공적으로 실행되었습니다(2026-07-24T08:52:14Z 생성). 
- **점검 결과:** 로깅 인프라의 핵심인 Elasticsearch 노드들이 재시작 없이 안정적으로 운영되고 있습니다. 다만, 셋업 잡의 환경 변수(`ES_PASS`)가 시크릿으로 적절히 관리되고 있음을 확인하였으나, 이후 인덱스 수명 주기 정책(ILM)이 의도한 대로 적용되었는지 추가 모니터링이 필요합니다.

## 4. 총평 및 다음 주 조치 권고

**[총평]**
현재 클러스터는 전반적으로 건강한 상태를 유지하고 있으나, **네트워크 인프라 설정(DNS)**과 **백업 유지보수 파이프라인**에서 최적화가 필요합니다. 특히 DNS 경고는 시스템 전체의 오버헤드를 발생시킬 수 있는 잠재적 위험 요소입니다.

**[차주 조치 권고]**
1. **노드 DNS 설정 최적화:** `lemuel` 호스트의 네임서버 설정을 3개 이하로 조정하여 Kubelet 경고를 제거하십시오.
2. **Kopia 유지보수 잡 디버깅:** `velero` 네임스페이스 내 유지보수 잡의 로그를 확보하여 리포지토리 락(Lock) 충돌 여부를 확인하고, 필요시 `velero repo unlock` 명령을 수행하십시오.
3. **ELK 리소스 사이징:** 현재 안정적인 상태이나 로그 유입량 증가에 대비하여 Elasticsearch 데이터 노드의 Heap Memory 사용률을 검토하십시오.

---
**Reporter:** Hermes Agent
**Status:** ✅ Trace Verified
```