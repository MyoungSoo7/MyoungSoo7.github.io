---
layout: post
title: "[Daily Report] 2026-10-02 Lemuel 클러스터 아침 브리핑"
date: 2026-10-02 09:00:00 +0900
categories: devops
tags: k8s homelab status
---

# 르무엘 클러스터 아침 브리핑 (2026-10-02)

본 브리핑은 `lemuel_morning_probe_gate.py`의 Canonical Probe 결과를 바탕으로 작성된 클러스터 상태 요약입니다.

## 1. 종합 상태 요약
- **프로브 시각**: 2026-10-02 19:11:15 KST
- **상태**: **주의 (Warning)**
- **주요 사항**: `isagal` 노드 **NotReady** 상태로 인해 일부 서비스 Pending 상태. 외부 엔드포인트는 모두 정상.

## 2. 노드 상태 (Nodes)
현재 총 6개 노드 중 1개 노드에서 장애가 감지되었습니다.

| 노드명 | 역할 | 상태 | 비고 |
| :--- | :--- | :--- | :--- |
| **isagal** | worker | **NotReady** | 점검 필요 (SSH 불능 가능성) |
| david | etcd | Ready | 정상 |
| ilwon | control-plane, etcd | Ready | 정상 |
| lemuel | control-plane, etcd | Ready | 정상 |
| louise | worker | Ready | 정상 |
| solomon | worker | Ready | 정상 |

- **특이사항**: `isagal` 노드는 오늘 02:58 KST경 잠시 Ready 상태로 복구되었으나, 현재 다시 NotReady 상태로 전이되었습니다.

## 3. 서비스 및 파드 상태 (Pods)
`isagal` 노드 장애 영향으로 총 11개의 파드가 **Pending** 상태입니다.

- **영향을 받는 주요 서비스**:
  - `agent-system`: litellm, nemotron-nano
  - `immich-prod`: postgres, redis, server, machine-learning
  - `memos-prod`: memos
  - `n8n`: n8n
  - `vaultwarden-prod`: vaultwarden
  - `network-agent-prod`: network-agent-service

## 4. 외부 엔드포인트 점검
외부 공개 서비스들은 정상적으로 응답하고 있습니다.

| 엔드포인트 | 상태 | 결과 |
| :--- | :--- | :--- |
| www.lemuel.co.kr | 200 OK | 정상 |
| settlement.lemuel.co.kr | 200 OK | 정상 |
| xr.lemuel.co.kr | 200 OK | 정상 |
| photos.lemuel.co.kr | 302 | 정상 (Redirect) |
| memo.lemuel.co.kr | 302 | 정상 (Redirect) |

## 5. 배치 작업 (Jobs)
- 오늘 발생한 배치 작업 실패는 없으며, `settlement-company-reputation` 등 일부 작업에서 재시도 후 성공한 기록이 확인되나 현재 장애 상황은 아닙니다.

## 6. 결론 및 권고 사항
- **isagal** 노드의 물리적 전원 및 네트워크 상태 확인이 시급합니다.
- 해당 노드 복구 시 Pending 상태의 주요 서비스(`immich`, `memos`, `n8n` 등)가 자동 복구될 것으로 예상됩니다.

---
*Reported by Hermes Agent OS (Cron Job)*
