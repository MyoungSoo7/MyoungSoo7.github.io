---
layout: post
title: "[Report] 2026-09-21 르무엘 클러스터 아침 브리핑"
date: 2026-09-21 09:00:17 +0900
categories: [ops]
tags: [kubernetes, k3s, report, monitoring]
---

# [Report] 2026-09-21 르무엘 클러스터 아침 브리핑

## 1. 개요 (Summary)
2026년 09월 21일 오전 09:00 기준, 르무엘 클러스터의 프로브 결과는 **정상(OK)**입니다. 6개 노드 모두 Ready 상태를 유지하고 있으며, 주요 외부 엔드포인트 응답성도 양호합니다. 다만, 지난 24시간 내 `ilwon` 및 `david` 노드에서 발생한 대규모 파드 재시작 이벤트가 관측되었습니다.

## 2. 외부 엔드포인트 상태
주요 서비스의 외부 접근성이 100% 유지되고 있습니다.

| 서비스 엔드포인트 | 상태 | 본문 크기 | 결과 |
| :--- | :--- | :--- | :--- |
| www.lemuel.co.kr | 200 | 17449B | OK |
| settlement.lemuel.co.kr | 200 | 4220B | OK |
| photos.lemuel.co.kr | 200 | 10566B | OK |
| memo.lemuel.co.kr | 200 | 1989B | OK |
| xr.lemuel.co.kr | 200 | 18578B | OK |

## 3. 노드 및 파드 상태
전체 6개 노드가 정상 작동 중입니다.

| 노드명 | 상태 | 역할 |
| :--- | :--- | :--- |
| david | Ready | etcd |
| ilwon | Ready | control-plane, etcd |
| isagal | Ready | <none> |
| lemuel | Ready | control-plane, etcd |
| louise | Ready | <none> |
| solomon | Ready | <none> |

### 비정상 파드 (Abnormal Pods)
| 네임스페이스 | 파드명 | 상태 | 노드 |
| :--- | :--- | :--- | :--- |
| velero | hourly-critical-20260921000003-brkws | Pending | louise |
| velero | hourly-critical-20260921000003-xcj8v | Pending | solomon |

*참고: Velero 배치 작업 파드들이 Pending 상태로 머물러 있습니다. 노드 자원 부족 혹은 스케줄링 제약 사항 확인이 필요합니다.*

## 4. 특이 사항: 동시 재시작 이벤트 (Correlated Restarts)
직전 프로브 대비 총 64건의 재시작이 증가했습니다. 특히 어제(09-20) 저녁 시간대(KST 기준)에 `ilwon`과 `david` 노드에서 대규모 동시 종료가 발생했습니다.

- **node=david**: 2026-09-20 09:53:20Z (KST 18:53:20) 경 **33개 파드** 동시 종료.
- **node=ilwon**: 2026-09-20 09:57:43Z (KST 18:57:43) 경 **26개 파드** 동시 종료.

해당 이벤트는 개별 파드의 문제가 아닌, 노드 서비스(k3s) 재시작 혹은 네트워크 불안정으로 인한 API 서버와의 연결 유실 가능성이 높습니다. 현재는 복구되어 정상 가동 중입니다.

## 5. 결론 및 향후 계획
- 클러스터 전체 서비스 가용성은 100%로 복구되었습니다.
- Pending 상태인 Velero 파드에 대한 후속 조치(Eviction 여부 등)를 검토하겠습니다.
- 주말 간 발생한 노드별 대규모 재시작 원인을 분석하여 재발 방지책을 수립할 예정입니다.

---
*본 보고서는 lemuel_morning_probe_gate.py 프로브 결과를 바탕으로 자동 생성되었습니다.*
