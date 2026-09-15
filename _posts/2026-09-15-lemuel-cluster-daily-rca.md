---
layout: post
title: "르무엘 클러스터 일일 RCA 리포트 (2026-09-15)"
date: 2026-09-15 09:00:00 +0900
categories: [DevOps, K3s, RCA]
tags: [kubernetes, rca, troubleshooting]
---

# 르무엘 클러스터 일일 RCA 리포트 (2026-09-15)

본 리포트는 `k8s-rca-daily.sh`가 수집한 실제 Trace와 로그를 근거로 작성되었습니다.

## 1. 분석 개요
- **분석 시간 범위 (UTC)**: 2026-09-14T17:51:00Z ~ 2026-09-14T23:58:30Z
- **대상 노드**: david, louise, solomon
- **주요 탐지**: PostgreSQL 연결 거부, Ghost 쿼리 지연, Elasticsearch 클러스터링 이슈

## 2. 장애 진행 중 (Current Issues)

| 서비스 | 노드 | 소유자 (State) | 현상 및 원인 | 증거 |
| :--- | :--- | :--- | :--- | :--- |
| crypto-app | david | Deployment/crypto-app (ready=1/1) | PostgreSQL 엔드포인트가 연결을 거부함 | 2026-09-14T23:58:29.746Z PSQLException: Connection refused |
| Ghost | louise | Deployment/ghost (ready=1/1) | postsPublic.browse 호출 지연 (389ms) | 2026-09-14T23:25:26Z SLOW_GET_HELPER: 389ms |
| lemuel-xr-postgres | louise | StatefulSet/lemuel-xr-postgres (ready=1/1) | DB collation version mismatch (2.41 vs 2.36) | 2026-09-14T23:42:16.380Z created with 2.41, OS provides 2.36 |

## 3. 조사 필요 및 상태 불분명 (Pending/Unknown)

| 서비스 | 노드 | 소유자 (State) | 현상 및 분석 | 조치 권고 |
| :--- | :--- | :--- | :--- | :--- |
| node-self-healer | louise | DaemonSet/node-self-healer (ready=5/6) | 최근 재부팅 이후 체크 이상 관찰 | investigate |
| logs-es-cold | solomon | StatefulSet/logs-es-cold (ready=0/1) | Elasticsearch 마스터 미발견 및 연결 타임아웃 | investigate |
| logs-kb | louise | Deployment/logs-kb (ready=0/1) | Elasticsearch 버전 조회 실패 및 DNS 오류 | investigate |

## 4. 과거 이력 및 복구됨 (Historical/Recovered)

| 서비스 | 노드 | 현상 | 분석 결과 |
| :--- | :--- | :--- | :--- |
| logs-kb | louise | Kibana Task Manager 오류 후 복구 | expired hot timestamps 발생 후 Healthy 복구됨 |

---
*주의: 본 리포트는 자동화 스크립트에 의해 생성되었습니다. 실제 조치 전 반드시 현행 상태를 재확인하시기 바랍니다.*
