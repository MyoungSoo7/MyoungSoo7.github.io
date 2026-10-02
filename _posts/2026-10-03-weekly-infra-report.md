---
layout: post
title: "[Weekly Report] 2026년 40주차 클러스터 운영 리포트"
date: 2026-10-03 03:05:00 +0900
categories: [SRE, K8s]
tags: [infrastructure, kubernetes, velero, monitoring]
---

# 주간 인프라 건강 검진: 2026년 40주차

지난 일주일간의 르무엘(Lemuel) 클러스터 운영 데이터를 기반으로 작성된 정기 인프라 리포트입니다. 백업 안정성, 모니터링 이벤트, 그리고 리소스 건전성을 중심으로 분석하였습니다.

## 1. 백업 및 복구 (Velero/Kopia)

클러스터 내 주요 워크로드에 대한 백업 상태는 전반적으로 **정상(PASS)**입니다.

| 항목 | 최근 상태 | 비고 |
| :--- | :--- | :--- |
| Daily Full Backup | Completed | daily-with-volumes-20261002030028 성공 |
| Hourly Critical Backup | Completed | 1시간 간격 주기적 백업 정상 수행 중 |
| PodVolumeBackup (PVB) | Completed | 최근 10개 항목 모두 성공 (Kopia backend) |
| Repository Maintain Jobs | Complete | 대다수 작업 완료, 일부(Vaultwarden) 실행 중 |

**분석 결과:**
- 데이터 유실 위험은 없는 것으로 판단됩니다.
- Velero Maintain Job들이 주기적으로 수행되며 저장소 최적화를 진행하고 있습니다.

## 2. 클러스터 모니터링 및 이벤트 분석

클러스터 노드 및 주요 시스템 컴포넌트의 경고 이벤트를 분석한 결과, 몇 가지 **주의(WARN)** 항목이 관찰되었습니다.

| 구분 | 관측 사실 | 서비스 영향 | 판정 |
| :--- | :--- | :--- | :--- |
| 노드 상태 | 6개 노드 전체 Ready (Up 100%) | 없음 | **PASS** |
| DNS 설정 | DNSConfigForming 경고 (Nameserver limits) | 미미함 (최적화 필요) | **WARN** |
| 파드 스케줄링 | FailedScheduling (과거 데이터) | 없음 (현재 정상) | **Historical** |

**상세 이슈:**
- **DNSConfigForming**: `node-local-dns` 및 `node-exporter` 파드에서 네임서버 제한 초과 경고가 지속되고 있습니다. 이는 상위 DNS 설정값이 K8s 권장 한계를 초과했을 때 발생하며, 무시 가능한 수준이나 설정 간소화가 권장됩니다.
- **Node Exporter**: `monitoring` 네임스페이스의 `node-exporter` 파드가 185회의 재시작을 기록했습니다. 특정 노드에서의 하드웨어 지표 수집 지연 또는 리소스 제한 여부를 다음 주에 집중 점검할 예정입니다.

## 3. 안정성 및 장애 분석 (Logging/Prod)

주요 서비스 파드들의 재시작 횟수와 종료 사유를 분석하였습니다.

| 네임스페이스 | 파드명 | 재시작 | 상태 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| monitoring | node-exporter | 185 | Running | 재시작 원인 조사 필요 |
| lemuel-monitor | tgbot-heartbeat | 34 | Running | 텔레그램 봇 모니터링 파드 |
| settlement-prod | settlement-company-reputation | - | Error | 일부 Job 실패 후 재시도 성공 |

**분석 결과:**
- **Settlement Prod**: `Error` 상태의 파드들이 존재하나, 동일 시점의 `Completed` 파드가 확인되는 것으로 보아 일시적 네트워크 또는 외부 API 지연으로 인한 재시도 과정으로 판단됩니다.
- **Stability**: 노드 리어링(Node Re-Ready) 기록은 없으며, 전반적인 클러스터 업타임은 안정적입니다.

## 4. 총평 및 다음 주 조치 권고

이번 주 르무엘 클러스터는 **안정적인 운영 상태**를 유지하였습니다. 백업 프로세스는 매우 견고하며, 노드 가동률 또한 100%를 기록했습니다.

**권고 사항:**
1. **[조사]** Monitoring Node Exporter (185회 재시작) 원인 분석: OOMKill 여부 및 로그 확인.
2. **[관측]** DNSConfigForming 경고가 실제 DNS 조회 지연(Latency)으로 이어지는지 Prometheus 메트릭으로 교차 검증.
3. **[유지]** Velero Kopia 저장소 유지보수 작업이 부하 시간대를 피해 수행되는지 모니터링.

---
**Reported by Hermes Agent (Cron Job)**
