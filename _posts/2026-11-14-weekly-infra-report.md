---
layout: post
title: "[Weekly Report] 2026년 11월 2주차 클러스터 운영 리포트"
date: 2026-11-14 03:00:02 +0900
categories: [SRE, K8s]
tags: [k3s, weekly-report, sre]
---

# 2026년 11월 2주차 클러스터 운영 리포트

- 수집 시각: 2026-11-14 03:00 KST (kubectl 읽기 전용 조회)
- 판정 기준: 재시작은 누적값이 아니라 **지난 수집 대비 증가분**으로 본다. 현재 스냅샷과 기간 중 사건은 구분해서 적는다.
- 라벨: **[사실]** 은 수집값 그대로, **[추론]** 은 수집값에서 끌어낸 해석이다.
- 데이터 제약: Warning 이벤트는 API 에 남아 있는 것만 본다(kube-apiserver `--event-ttl` 기본값은 1시간[^event-ttl]). 재시작 증가분의 기준 시점은 "지난 수집 실행"이며, 이 블로그의 직전 주간 리포트는 2026-10-17 자다. 따라서 증가분이 정확히 7일치라고 단정하지 않는다.

## 1. 이번 주 변경

| 구분 | 변경 또는 사건 | 라벨 | 근거 |
|---|---|---|---|
| 노드 | 노드 목록에 4대(ilwon·lemuel·louise·solomon)만 보인다. **david·isagal 은 목록에 없다** | 사실 | 수집 데이터 "노드(스냅샷)", `kubectl get nodes` |
| 노드 | 보이는 4대는 모두 Ready, 압력 조건 없음, kubelet v1.35.4+k3s1 | 사실 | 수집 데이터 "노드(스냅샷)" |
| 재시작 | 48개 파드에서 재시작 증가(표에 30개, 그 외 18개 생략). 최대는 kafka entity-operator +29 | 사실 | 수집 데이터 "재시작 증가분" |
| 재시작 | 4개 노드 전체의 데몬셋 파드(node-exporter·fluent-bit·velero node-agent·node-self-healer 등)가 고르게 +2 | 사실 | 수집 데이터 "재시작 증가분" |
| 재시작 | 위 +2 는 기간 중 클러스터 전반에 영향을 준 사건이 두 차례 있었음을 시사한다. 무선 단절과 함께 늘어나는 알려진 패턴과 부합한다 | 추론 | 증가 폭이 노드·네임스페이스와 무관하게 동일(+2) |
| 백업 | Velero 정기 백업은 2026-10-13 비용 절감 목적으로 **의도적으로 중단**된 상태. 스케줄 2개 모두 paused, Backup 객체 0건 | 사실 | 수집 데이터 "Velero 백업", `schedules.velero.io` 의 `spec.paused=true` |
| 스케줄링 | 현재 Pending 파드 없음. 전체 102개 중 Running 91, Succeeded 11 | 사실 | 수집 데이터 "파드", `kubectl get pods -A` |

## 2. 요약 표

| 항목 | 상태 | 이번 주 변화 | 복구 검증 | 근거 |
|---|---|---|---|---|
| 노드 Ready (스냅샷) | PASS | 보이는 4대 전부 Ready, 압력 조건 없음 | 해당 없음 | 수집 데이터 "노드(스냅샷)" |
| 노드 수 | WARN | 6대 중 4대만 목록에 있음. david·isagal 부재 | 해당 없음 | 수집 데이터 "노드 수: 4" |
| 파드 상태 (스냅샷) | PASS | Running 91, Succeeded 11, Pending 0 | 해당 없음 | 수집 데이터 "파드" |
| 재시작 증가분 — ilwon 워크로드 | WARN | entity-operator +29, ghstats +15, tgbot-heartbeat +13, logs-es-hot +8, grafana +6, logstash +6 | 해당 없음 | 수집 데이터 "재시작 증가분" |
| 재시작 증가분 — 데몬셋 전반 | WARN | 4개 노드에서 대부분 +2 | 해당 없음 | 수집 데이터 "재시작 증가분" |
| Velero 정기 백업 | 의도된 중단 | 최근 7일 0건 / 전체 0건 | 미검증 | 수집 데이터 "Velero 백업", 운영 결정(2026-10-13) |
| 복구 리허설 | WARN | 이번 수집에 근거 없음 | 미검증 | 수집기가 복구 리허설 기록을 보지 않음 |
| Warning 이벤트 | WARN | API 보존분 18건. 수집 직전 1시간 내 갱신은 3건 | 해당 없음 | 수집 데이터 "Warning 이벤트", 이벤트 `lastTimestamp` |
| PVC | PASS | 42개 전부 Bound | 해당 없음 | `kubectl get pvc -A` |

"PASS" 는 수집 시각의 스냅샷에 대한 판정이다. 기간 내내 문제가 없었다는 뜻이 아니며, 재시작 증가분이 보여 주듯 기간 중에는 사건이 있었다.

## 3. 세부

### 3.1 백업

| 항목 | 값 | 라벨 | 근거 |
|---|---|---|---|
| Backup 객체 | 최근 7일 0건 / 전체 0건 | 사실 | 수집 데이터 "Velero 백업" |
| 스케줄 `daily-with-volumes` | paused, 마지막 백업 2026-10-13 12:00 KST | 사실 | `schedules.velero.io` 의 `spec.paused`, `status.lastBackup` |
| 스케줄 `hourly-critical` | paused, 마지막 백업 2026-10-13 21:00 KST | 사실 | 같은 항목 |
| Velero 디플로이먼트 | 1/1 Available | 사실 | `kubectl get deploy -n velero` |
| 백업 저장 위치 `default` | Available | 사실 | `kubectl get bsl -n velero` |
| node-agent 재시작 | 4개 노드 각 +2 | 사실 | 수집 데이터 "재시작 증가분" |
| 복구 검증 | 미검증 | 사실 | 수집기가 복구 리허설 기록을 보지 않음 |

백업 0건은 장애가 아니라 2026-10-13 의 운영 결정(비용 절감)에 따른 의도된 상태다. 두 스케줄의 마지막 백업 시각이 그 날짜에서 멈춘 것도 이와 일치한다. 다만 "백업이 있었다"와 "복구가 된다"는 별개이고, 복구 쪽은 이번 수집에 근거가 없으므로 미검증으로 둔다.

### 3.2 모니터링 — 재시작 증가분

| 파드 | 노드 | 증가 | 누적 | 근거 |
|---|---|---|---|---|
| kafka/lemuel-entity-operator | ilwon | +29 | 37 | 수집 데이터 "재시작 증가분" |
| ghstats/ghstats | ilwon | +15 | 15 | 같은 항목 |
| lemuel-monitor/tgbot-heartbeat | ilwon | +13 | 14 | 같은 항목 |
| logging/logs-es-hot-0 | ilwon | +8 | 11 | 같은 항목 |
| monitoring/kps-grafana | ilwon | +6 | 11 | 같은 항목 |
| logging/logs-ls-0 | ilwon | +6 | 12 | 같은 항목 |
| monitoring/prometheus-kps-prometheus-0 | ilwon | +4 | 8 | 같은 항목 |
| monitoring/alertmanager-kps-alertmanager-0 | ilwon | +4 | 6 | 같은 항목 |
| logging/fluent-bit | ilwon | +3 | 4 | 같은 항목 |
| lemuel-monitor/tgbot-heartbeat | louise | +3 | 3 | 같은 항목 |
| settlement-prod/settlement-elasticsearch-0 | ilwon | +2 | 3 | 같은 항목 |
| monitoring/node-exporter | louise / solomon / ilwon / lemuel | 각 +2 | 195 / 191 / 8 / 6 | 같은 항목 |
| kube-system/node-self-healer | 4개 노드 | 각 +2 | 각 2 | 같은 항목 |
| kube-system/wifi-probe | louise / solomon | 각 +2 | 각 2 | 같은 항목 |
| logging/fluent-bit | lemuel / louise / solomon | 각 +2 | 각 3 | 같은 항목 |
| velero/node-agent | 4개 노드 | 각 +2 | 2~3 | 같은 항목 |
| kube-system/node-local-dns | lemuel | +2 | 6 | 같은 항목 |

- **[사실]** 증가 폭이 +3 이상인 파드 10개 중 9개가 ilwon 에 있다. ilwon 은 control-plane·etcd 역할을 겸한다.
- **[사실]** louise·solomon 의 node-exporter 는 누적이 195·191 이지만 이번 증가분은 +2 다. 누적값은 과거 이력이며 이번 주 판정에는 증가분만 쓴다.
- **[추론]** node-exporter·node-self-healer·wifi-probe 의 +2 는 무선 단절 때 함께 늘어나는 알려진 패턴으로 보인다. 재시작 원인을 직접 확인한 것은 아니다.
- **[추론]** ilwon 에 증가가 몰린 것은 ilwon 고유의 사건(노드 재기동 또는 노드 단위 자원 압박)이 더해졌을 가능성을 가리킨다. 다만 entity-operator 의 +29 는 다른 파드보다 한 자릿수 크므로 노드 사건만으로는 설명되지 않고, 해당 파드 자체의 반복 재시작일 가능성이 높다. 종료 사유는 이번 수집에 없어 확정하지 않는다.

### 3.3 모니터링 — Warning 이벤트

| 사유 | 대상 | 건수 | 마지막 갱신 | 근거 |
|---|---|---|---|---|
| FailedScheduling | DB·ES 스테이트풀셋 파드 7개 | 7 | 2026-05-12 | 수집 데이터 "Warning 이벤트", 이벤트 `eventTime` |
| DNSConfigForming | node-local-dns·node-exporter (lemuel) | 2 | 2026-11-14 02:59 KST | 이벤트 `lastTimestamp` |
| DNSConfigForming | coredns·node-local-dns·node-exporter (그 외) | 3 | 2026-05-12 | 이벤트 `lastTimestamp` |
| FailedCreate | velero ReplicaSet | 3 | 2026-05-12 | 이벤트 `lastTimestamp` |
| FailedCreate | velero kopia 유지보수 Job | 1 | 2026-05-12 | 이벤트 `lastTimestamp` |
| ApplyManifestFailed | coredns 애드온 | 1 | 2026-05-12 | 이벤트 `lastTimestamp` |
| Unhealthy | fluent-bit (solomon) | 1 | 2026-11-14 02:30 KST | 이벤트 `lastTimestamp` |

- **[사실]** 18건 중 수집 직전 1시간 안에 갱신된 것은 3건(lemuel 의 DNSConfigForming 2건, solomon fluent-bit 의 liveness 실패 1건)이다. 나머지 15건은 타임스탬프가 2026-05-12 다.
- **[사실]** FailedScheduling 7건의 대상 파드 중 현재 Pending 인 것은 없다. 따라서 이 7건은 현재의 스케줄링 실패를 뜻하지 않는다.
- **[추론]** 5월 자 이벤트가 TTL 을 넘겨 API 에 남아 있는 이유는 확인하지 못했다. 이 15건은 "이번 주 사건"이 아니라 정리되지 않은 과거 기록으로 읽는 것이 타당하다.
- **[사실]** DNSConfigForming 의 메시지는 "nameserver 한도 초과로 일부가 생략됨"이다. 쿠버네티스는 리눅스 libc 의 nameserver 3개 한도를 알려진 제약으로 문서화하고 있다[^dns].
- **[사실]** velero 의 FailedCreate 메시지는 "메모리 limit/request 비율 상한 2, 요청 비율 4"다. 이는 LimitRange 의 `maxLimitRequestRatio` 위반 형태다[^limitrange]. 타임스탬프는 5월이고 현재 velero 디플로이먼트는 1/1 이다.

### 3.4 리소스

| 노드 | CPU 사용 | CPU % | 메모리 사용 | 메모리 % | 근거 |
|---|---|---|---|---|---|
| ilwon | 1007m | 9% | 18635Mi | 66% | `kubectl top nodes` (수집 직후 스냅샷) |
| lemuel | 1825m | 60% | 9698Mi | 34% | 같은 항목 |
| louise | 491m | 7% | 5299Mi | 43% | 같은 항목 |
| solomon | 406m | 13% | 3050Mi | 25% | 같은 항목 |

- **[사실]** 메모리 사용률은 ilwon 이 66% 로 가장 높고, CPU 사용률은 lemuel 이 60% 로 가장 높다. 4대 모두 압력 조건은 없다.
- **[추론]** 재시작 증가가 ilwon 에 몰려 있고 메모리 사용도 ilwon 이 가장 높다. 둘 사이의 인과는 이 수집만으로는 판단할 수 없다. 한 시점 스냅샷이라 기간 중 최고치도 알 수 없다.

## 4. 액션 아이템

| 우선순위 | 항목 | 이유 | 근거 |
|---|---|---|---|
| 1 | kafka entity-operator 의 종료 사유 확인(`lastState.terminated`, 이전 컨테이너 로그) | +29 로 다른 파드보다 한 자릿수 크다 | 수집 데이터 "재시작 증가분" |
| 2 | david·isagal 이 노드 목록에 없는 것이 의도된 상태인지 기록으로 남기기 | 6대 중 2대 부재가 사실로 관측됨. 의도 여부는 이 수집으로 알 수 없다 | 수집 데이터 "노드 수: 4" |
| 3 | ghstats(+15)·tgbot-heartbeat(+13)·logs-es-hot(+8) 의 종료 사유 확인 | ilwon 에 증가가 집중. 노드 사건인지 파드 개별 문제인지 구분 필요 | 수집 데이터 "재시작 증가분" |
| 4 | 2026-05-12 자 Warning 이벤트 15건이 API 에 남아 있는 이유 확인 | 과거 기록이 현재 경보처럼 집계되어 주간 판정을 흐린다 | 이벤트 `lastTimestamp` |
| 5 | lemuel 의 nameserver 개수 점검 | DNSConfigForming 이 수집 직전까지 갱신되고 있다 | 이벤트 `lastTimestamp` |
| 6 | 재시작 수집기에 기준 시점(지난 실행 시각) 기록 추가 | 증가분이 며칠치인지 리포트에서 확정할 수 없다 | 수집 데이터 "재시작 증가분 (지난 실행 대비)" |

복구 검증은 이번 주에도 "미검증"이다. Velero 정기 백업은 의도적으로 중단된 상태이므로 이 리포트는 재가동을 권고하지 않는다.

## References

[^event-ttl]: Kubernetes 공식 문서, [kube-apiserver 명령행 레퍼런스](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver/) — `--event-ttl` 항목.
[^dns]: Kubernetes 공식 문서, [Debugging DNS Resolution — Known issues](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/#known-issues).
[^limitrange]: Kubernetes 공식 문서, [Limit Ranges](https://kubernetes.io/docs/concepts/policy/limit-range/).
