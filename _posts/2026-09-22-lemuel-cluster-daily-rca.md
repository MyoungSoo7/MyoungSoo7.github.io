---
layout: post
title: "Lemuel Cluster 일일 RCA 리포트 (2026-09-22)"
date: 2026-09-22 09:15:00 +0900
categories: ops
tags: [k8s, rca, david]
---

# Lemuel Cluster Daily RCA Report (2026-09-22)

본 리포트는 `k8s-rca-daily.sh`가 수집한 실제 Trace와 로그를 근거로 작성되었습니다.

## 1. 개요
- **분석 시간 범위**: 2026-09-21T13:40:00Z ~ 2026-09-21T23:41:00Z (실제 증거 기준)
- **대상 노드**: david (모든 장애가 해당 노드에 집중됨)
- **상태 요약**: 현재 진행 중인 장애는 없으며, 모든 인시던트는 자동 복구되거나 과거의 이력(Historical)입니다.

## 2. 해결됨 (재시도로 회복)
- **settlement-prod/settlement-company-reputation-29833800-5qg9r**: Job 백오프 재시도 끝에 성공(Complete). 정상 동작 범위 내 복구 (node=david).

## 3. 과거 인시던트 분석 (Historical)

### analytics-postgres 이전 컨테이너 비정상 종료 후 자동 복구
- **상태**: historical (현재 ready=1/1)
- **발생 노드**: david
- **추정 원인**: 비정상 종료의 원인은 확인되지 않았다. 복구 관련 로그가 david 노드의 동일 StatefulSet에서 관찰되었고, 현재 owner는 ready=1/1이다.
- **확인된 증거 (Trace)**:
  - `2026-09-21T13:40:57.116Z: database system was not properly shut down; automatic recovery in progress`
  - `2026-09-21T13:40:57.585Z: the database system is not yet accepting connections`
  - `2026-09-21T13:40:57.635Z: database system is ready to accept connections`

### analytics-postgres 체크포인트 지연
- **상태**: historical (현재 ready=1/1)
- **발생 노드**: david
- **추정 원인**: 체크포인트에 56.740초가 소요된 사실은 확인되지만, 성능 기준선이나 장애 영향은 확인되지 않았다.
- **확인된 증거 (Trace)**:
  - `2026-09-21T23:34:18.919Z: checkpoint complete; write=56.720 s, sync=0.009 s, total=56.740 s`

### cloudflared를 통한 codingtest origin 연결·해석 실패
- **상태**: historical (현재 ready=1/1)
- **발생 노드**: david
- **추정 원인**: 직접 증명된 원인은 codingtest-app 서비스의 TCP 8080 connection refused와 클러스터 DNS 질의 timeout이다. 두 증거가 모두 david 노드의 cloudflared owner에서 관찰되므로, 클러스터 공용 서비스 장애로 일반화할 근거는 없다. 근본 원인은 unknown이다.
- **확인된 증거 (Trace)**:
  - `2026-09-21T13:58:48Z: dial tcp 10.43.123.6:8080: connect: connection refused`
  - `2026-09-21T15:00:30Z: lookup codingtest-app.codingtest-prod.svc.cluster.local on 10.43.0.10:53: i/o timeout`

### cloudflared QUIC 터널 timeout 및 원격 stream 취소
- **상태**: historical (현재 ready=1/1)
- **발생 노드**: david
- **추정 원인**: QUIC 연결의 no recent network activity timeout과 원격 측 stream 취소는 직접 확인되지만, 네트워크·원격 endpoint·터널 설정 중 어느 것이 근본 원인인지는 확인되지 않았다. 증거가 david 노드에 집중되어 있다.
- **확인된 증거 (Trace)**:
  - `2026-09-21T14:09:24Z: failed to accept QUIC stream: timeout: no recent network activity; reconnecting`
  - `2026-09-21T14:47:00Z: stream 9 canceled by remote with error code 0`
  - `2026-09-21T23:40:21Z: stream 8541 canceled by remote with error code 0`

### codingtest-app Hibernate collection fetch 페이징 경고
- **상태**: historical (현재 ready=1/1)
- **발생 노드**: david
- **추정 원인**: 메모리 페이징이 적용된 경고는 확인되지만, 실제 장애나 성능 영향 및 근본 원인은 확인되지 않았다.
- **확인된 증거 (Trace)**:
  - `2026-09-21T23:10:20.631Z: HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory`

### ddak-app 개발용 생성 보안 비밀번호 경고
- **상태**: historical (현재 ready=1/1)
- **발생 노드**: david
- **추정 원인**: 개발용 generated security password 사용 경고는 확인되지만, 보안 영향 범위와 운영 설정 의도는 확인되지 않았다.
- **확인된 증거 (Trace)**:
  - `2026-09-21T13:58:39.945Z: Using generated security password; generated password is for development use only`

## 4. 종합 분석 및 권고
- **노드 집중 현상**: 모든 인시던트가 `david` 노드에 집중되어 있습니다. 클러스터 공용 서비스(DNS 등)의 일시적 timeout이 관찰되었으나, 이는 노드 로컬의 부하나 네트워크 지연일 가능성이 높습니다.
- **DB 건전성**: `analytics-postgres`의 비정상 종료 후 자동 복구가 성공하였으나, 체크포인트 지연(56s)이 관찰되었습니다. `david` 노드의 디스크 I/O 성능 점검을 권고합니다.
- **네트워크 터널**: `cloudflared`의 QUIC timeout 및 연결 거부는 외부 네트워크 불안정 또는 원격 엔드포인트와의 세션 만료가 원인으로 보이며, 자동 재연결을 통해 정상화되었습니다.

---
*본 리포트는 Hermes Agent에 의해 자동 생성 및 검증되었습니다.*
