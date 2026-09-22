---
layout: post
title: "Lemuel Cluster 일일 RCA 리포트 (2026-09-22)"
date: 2026-09-22 09:15:00 +0900
categories: ops
tags: [k8s, rca, david]
---

# Lemuel Cluster Daily RCA Report (2026-09-22)

본 리포트는 `k8s-rca-daily.sh`가 수집한 실제 Trace와 로그를 근거로 작성되었습니다.

> **정정 (2026-09-22 21:45 KST 추가).** 아래 3장의 "과거 인시던트" 6건은 서로 독립된 사건이
> 아니라 **david 노드 재부팅(그날 두 번)의 파생 전부**였고, 4장의 "david 디스크 I/O 점검"
> 권고는 이 글이 인용한 증거 자체로 반증된다. 사후 실측과 근거는 글 끝 "정정" 절에 적었다.
> 원문은 무엇을 어떻게 틀렸는지 남기기 위해 고치지 않고 그대로 둔다.

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

## 정정 (2026-09-22 21:45 KST)

위 3장의 인시던트 6건은 **독립된 사건이 아니다.** 전부 david 노드가 재부팅되면서 생긴 파생이다.
같은 날 저녁 사후 실측으로 확인한 사실은 다음과 같다.

**1) 같은 초에 한꺼번에 끝났다.** 쿠버네티스 API(`/api/v1/pods`)의 컨테이너 종료 기록을
노드별·초 단위로 세면, david 의 컨테이너 **37개(파드 35개, 네임스페이스 21개)** 가
`2026-09-21T13:57:53Z` 부터 20초 안에 전부 끝났고 그중 **35개가 `exitCode 255 / reason Unknown`**
이다. 최근 24시간으로 넓혀도 `exit != 0` 종료는 david 36건뿐이고 **나머지 다섯 노드는 0건**이다.
21개 네임스페이스가 같은 초에 함께 끝나는 것은 워크로드 사정으로 설명되지 않는다.

**2) 그 노드는 실제로 재부팅됐다 — 그것도 두 번.** david 에서 직접 확인하면,

- `/proc/uptime` 기준 부팅 시각이 `2026-09-21T13:57:28Z`(= 22:57:28 KST)로, 위 종료 기록보다
  **25초 앞선다.**
- `journalctl --list-boots` 에 그날 저녁 부팅이 둘이다. 직전 부팅은 22:37:09 KST 에 끝났고,
  다음 부팅은 22:40:05 → 22:55:35 KST 로 **15분짜리**이며 마지막이 `systemd-reboot.service
  Finished` 다 — 정전이나 커널 패닉이 아니라 **의도된 재부팅**이다. 그 다음이 지금 살아 있는
  22:57:28 KST 부팅이다.

그래서 이 글이 인용한 증거들은 시각만 보면 두 재부팅에 정확히 나뉜다. `13:40:57Z` 의
analytics-postgres 복구 로그는 **첫 번째** 재부팅 직후(22:40 KST 기동)이고, `13:58` 대의
cloudflared `connection refused` 는 **두 번째** 재부팅 직후(22:57 KST 기동)다. 그런데 원문은 이
둘을 서로 무관한 "근본 원인 unknown" 두 건으로 적었다.

**3) 인용해 놓고 읽지 못한 증거.** 3장 첫 항목이 인용한 `database system was not properly shut
down` 은 그 자체가 **직전에 비정상 종료가 있었다는 증거**다. PostgreSQL 은 정상 종료였다면 이
줄을 쓰지 않는다. 이 줄을 근거로 올려놓고 원인을 unknown 으로 남길 수는 없다.

**4) 디스크 I/O 점검 권고는 철회한다.** 4장은 `write=56.720 s` 를 보고 david 의 디스크 점검을
권고했는데, **같은 줄의 `sync=0.009 s` 가 그것을 반증한다.** 체크포인트 쓰기는 느려서 오래
걸리는 것이 아니라 `checkpoint_timeout` × `checkpoint_completion_target` 만큼 **일부러 분산**된다.
이 인스턴스(PostgreSQL 16.15)의 실측값은 `300초 × 0.9 = 270초` 창이고, 56.72초는 그 **21%** 다.
디스크가 느릴 때 커지는 값은 write 가 아니라 **sync** 이며, 여기서는 **9밀리초**다. 그 주기만
유독 길었던 이유는 재부팅 직후 캐시가 다시 차면서 더티 버퍼가 평소(25~30 buffers, distance 약
200kB)보다 훨씬 많은 **568 buffers(6410kB)** 였기 때문이다 — 디스크가 아니라 재부팅의 결과다.

**5) 애초에 인시던트가 아닌 것 셋.** `stream ... canceled by remote with error code 0` 의
**code 0 은 "에러 없음"**, 즉 상대편의 정상적인 스트림 종료다. Hibernate `HHH90003004` 와 Spring
의 `generated security password` 는 그날 일어난 사건이 아니라 **상시 설정 스멜**이다 — 설정을
고치지 않는 한 매일 같은 항목이 올라온다.

**그래서 맞는 요약은 이렇다.** 2026-09-21 저녁 david 노드가 두 번 재부팅됐고, 그 위에 있던 파드
35개가 함께 죽었다가 돌아왔다. 남는 질문은 "여섯 증상의 원인이 각각 무엇인가" 가 아니라
**"david 는 왜 재부팅됐나"** 하나다.

**파이프라인도 고쳤다.** 이 판정은 사람이 매번 다시 할 일이 아니라서, 리포트를 쓰기 전 수집
단계에서 기계가 세도록 했다. 종료 타임스탬프를 노드별·초별로 묶어 한 노드에 여러 네임스페이스가
겹쳐 몰리면 `RCA_NODE_EVENT`(= 장애 N건이 아니라 노드 이벤트 1건)로, 노드에 직접 물어본 부팅
시각과 시간창 내 재부팅 횟수는 `RCA_NODE_BOOT` 으로 올린다. 어제 데이터로 다시 돌리면 리포트
첫 세 줄에서 "david 재부팅 2회, 파생 35건" 이 확정된다.

### References

- PostgreSQL 16 Documentation, *Write Ahead Log* — [`checkpoint_completion_target`](https://www.postgresql.org/docs/16/runtime-config-wal.html#GUC-CHECKPOINT-COMPLETION-TARGET)
- PostgreSQL 16 Documentation, [*WAL Configuration*](https://www.postgresql.org/docs/16/wal-configuration.html)
- systemd, [*journalctl(1)*](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html) — `--list-boots`
- 위 컨테이너·노드 수치는 2026-09-22 저녁에 클러스터 API(`/api/v1/pods`)와 david 노드에서 직접
  측정한 값이다.

---
*본 리포트는 Hermes Agent에 의해 자동 생성 및 검증되었습니다.*
