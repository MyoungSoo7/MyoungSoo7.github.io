---
layout: post
title: "2026-09-20 르무엘 클러스터 아침 브리핑 (관측 실패)"
date: 2026-09-20 09:00:00 +0900
categories: [Ops, Report]
tags: [homelab, k3s, monitoring]
---

# 2026-09-20 르무엘 클러스터 아침 브리핑 (관측 실패)

본 리포트는 `lemuel_morning_probe_gate.py`의 canonical probe 결과를 기반으로 작성되었습니다.

## 1. 관측 실패 보고
- **상태**: 🔴 FAILED
- **사유**: apiserver 에 두 경로 모두 도달 실패 (터널 루프백, 직결 LAN)
- **조치 필요**: 이 호스트가 집 LAN 밖이거나 `isagal` 노드 SSH 연결이 끊겼을 가능성이 큼. 클러스터 내부 상태는 관측 불가.

## 2. 외부 엔드포인트 상태
외부 측정값(Cloudflare Edge 기준)은 apiserver 도달 여부와 독립적인 지표입니다.

| 엔드포인트 | 상태 | 응답 코드 |
| :--- | :--- | :--- |
| www.lemuel.co.kr | 🔴 DOWN | 530 |
| settlement.lemuel.co.kr | 🟢 OK | 200 |
| photos.lemuel.co.kr | 🟢 OK | 200 |
| memo.lemuel.co.kr | 🟢 OK | 200 |
| xr.lemuel.co.kr | 🔴 DOWN | 530 |

---
**보고자**: Hermes Agent (Cron Job)
**기준 시각**: 2026-09-20 09:00 KST
