---
layout: post
title: "[Weekly Report] 2026년 37주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# 주간 인프라 건강 검진: 2026년 37주차

이번 주 클러스터 원시 데이터는 Velero/Kopia 백업 파드, 모니터링 이벤트, logging 네임스페이스 파드 정보로 구성되어 있다. 다만 일부 데이터가 중간에서 잘려 있고, 파드의 `status`, 컨테이너 종료 상태, `restartCount`, Job 완료 조건이 포함되지 않아 성공률과 재시작 안정성을 완전하게 산출하기에는 한계가 있다.

## 1. 전체 요약

| 영역 | 관측 결과 | 판단 | 신뢰도 |
|---|---|---|---|
| Velero/Kopia 백업 | Kopia 유지보수 Job 파드 1건의 메타데이터 확인 | 성공·실패 상태와 전체 대상 수 미확인 | 낮음 |
| 모니터링 | `kube-state-metrics`의 Liveness probe HTTP 503 경고 147회 확인 | 반복적인 헬스체크 실패 발생 | 높음 |
| ELK/Logging | `es-advanced-setup` Job 파드의 생성 정보 확인 | 재시작 횟수와 Elasticsearch 본체 상태 미확인 | 낮음 |
| 종합 상태 | 모니터링 계층에 반복 경고 존재 | 주의 필요. 백업·로깅은 추가 원시 데이터 필요 | 중간 |

## 2. 백업: Velero/Kopia

### 2.1 관측 데이터

확인된 파드는 다음 Kopia 유지보수 Job에 속해 있다.

| 항목 | 값 |
|---|---|
| 네임스페이스 | `velero` |
| 작업 유형 | Kopia repository maintenance |
| 대상 리포지토리 | `agent-system-default-kopia-4hxm2` |
| Job 유형 | `maintain-job` |
| 생성 시각 | 2026-09-11 15:21:40 UTC |
| 관측 파드 수 | 제공된 데이터 기준 1건 |
| 파드 상태 | 원시 데이터에 `status` 필드 없음 |
| Job 완료 조건 | 제공된 데이터에 `succeeded`, `failed`, `conditions` 없음 |

### 2.2 성공률 계산

백업 성공률은 일반적으로 다음 기준으로 계산한다.

```text
성공률 = 성공한 백업 Job 수 / 전체 백업 Job 수 × 100
```

그러나 이번 데이터에는 Job의 성공·실패 상태를 판별할 수 있는 다음 필드가 포함되어 있지 않다.

- `status.phase`
- `status.containerStatuses[*].state`
- `status.containerStatuses[*].restartCount`
- Job의 `status.succeeded`
- Job의 `status.failed`
- Job의 `status.conditions`
- 분석 기간 내 전체 백업 Job 목록

따라서 이번 원시 데이터만으로는 Velero/Kopia 백업 성공률을 수치로 계산할 수 없다.

| 지표 | 결과 |
|---|---:|
| 확인된 Kopia 유지보수 파드 | 1건 |
| 성공 파드 수 | 확인 불가 |
| 실패 파드 수 | 확인 불가 |
| 전체 백업 Job 수 | 확인 불가 |
| 백업 성공률 | 계산 불가 |

이번 데이터에서 실패한 특정 Job이 확인되었다고 판단할 근거도 없다. 확인된 파드는 `maintain-job`의 메타데이터일 뿐이며, 실패를 나타내는 `Failed`, `Error`, 비정상 종료 코드 또는 Job 조건이 제공되지 않았다.

### 2.3 실패 원인 추론

현재 데이터에는 실패 상태가 확인되지 않았으므로 특정 Job의 원인을 추론할 수 없다. 특히 다음과 같은 일반적인 원인은 추가 증거 없이 단정해서는 안 된다.

- 오브젝트 스토리지 인증 실패
- 저장소 연결 또는 네트워크 오류
- Kopia repository lock 충돌
- 스토리지 용량 부족
- 노드 리소스 부족
- 유지보수 작업 시간 초과

정확한 원인 분석을 위해서는 다음 정보가 필요하다.

```bash
kubectl -n velero get jobs,pods -l velero.io/repo-name=agent-system-default-kopia-4hxm2 -o wide
kubectl -n velero describe job <job-name>
kubectl -n velero logs <pod-name> --all-containers
kubectl -n velero get pod <pod-name> -o json
```

특히 Kopia 유지보수 Job은 일반적인 애플리케이션 백업 Job과 목적이 다르므로, 백업 자체의 성공률과 repository maintenance 성공률을 분리해 집계해야 한다.

## 3. 모니터링: 주요 경고 이벤트

### 3.1 반복된 Liveness probe 실패

이번 데이터에서 가장 명확한 운영 경고는 `kube-state-metrics` 파드의 Liveness probe 실패다.

| 항목 | 값 |
|---|---|
| 네임스페이스 | `monitoring` |
| 대상 컴포넌트 | `kube-state-metrics` |
| 이벤트 유형 | `Warning` |
| Reason | `Unhealthy` |
| 메시지 | `Liveness probe failed: HTTP probe failed with statuscode: 503` |
| 최초 발생 | 2026-09-10 13:20:03 UTC |
| 최근 발생 | 2026-09-11 17:38:53 UTC |
| 누적 횟수 | 147회 |
| 이벤트 보고 주체 | kubelet |

HTTP 503은 프로세스가 완전히 종료되었다는 의미라기보다, 프로브가 호출한 헬스체크 엔드포인트가 당시 요청을 정상 처리하지 못했다는 의미다. 다만 Liveness probe이므로 반복 실패가 임계치를 넘으면 kubelet이 컨테이너를 재시작할 수 있다.

가능한 원인은 다음 범주로 나눌 수 있다.

1. `kube-state-metrics` 프로세스의 일시적인 과부하
2. Kubernetes API 서버 조회 지연 또는 API rate limit
3. CPU·메모리 부족으로 인한 응답 지연
4. Liveness probe의 timeout 또는 failure threshold 설정 불일치
5. 메트릭 수집 대상 증가에 따른 내부 처리 지연
6. 파드 네트워크 또는 서비스 라우팅 문제

현재 데이터만으로는 위 원인 중 하나를 확정할 수 없다. 다만 147회 반복되었다는 점에서 단발성 이벤트보다는 지속적인 불안정 또는 프로브 설정 문제를 우선 점검해야 한다.

### 3.2 모니터링 영역 판단

`kube-state-metrics`는 Kubernetes 오브젝트 상태를 Prometheus 형식으로 노출하는 컴포넌트다. 이 컴포넌트의 Liveness 실패가 지속되면 다음과 같은 2차 영향이 발생할 수 있다.

- 파드·Deployment·Job 상태 메트릭의 수집 공백
- 알림 규칙 평가의 지연 또는 누락
- 실제 장애와 모니터링 장애를 구분하기 어려운 상태
- kubelet에 의한 반복적인 컨테이너 재시작
- Prometheus의 scrape error 증가

따라서 이번 경고는 단순한 이벤트 수 증가보다, 모니터링 신뢰도 자체가 저하될 수 있는 신호로 평가해야 한다.

## 4. ELK/Logging 안정성 점검

### 4.1 확인된 파드

제공된 logging 데이터에서는 다음 파드의 메타데이터가 확인된다.

| 항목 | 값 |
|---|---|
| 네임스페이스 | `logging` |
| 파드 | `es-advanced-setup` 계열 |
| Job | `es-advanced-setup` |
| 컨테이너 | `setup` |
| 생성 시각 | 2026-09-11 17:23:19 UTC |
| 역할 | Elasticsearch 초기 설정 또는 구성 작업으로 추정 |
| 재시작 횟수 | 확인 불가 |
| 종료 코드 | 확인 불가 |
| 파드 상태 | 확인 불가 |

이 파드는 Elasticsearch 데이터 노드나 Kibana, Logstash와 같은 상시 서비스 파드가 아니라 Elasticsearch 초기 설정을 수행하는 Job 파드로 보인다. 따라서 이 파드 한 건만으로 ELK 전체의 안정성을 판단할 수 없다.

### 4.2 재시작 안정성

재시작 안정성을 평가하려면 최소한 다음 정보가 필요하다.

- `status.containerStatuses[*].restartCount`
- 현재 파드 phase
- `lastState.terminated.exitCode`
- `lastState.terminated.reason`
- `ready` 상태
- Elasticsearch 클러스터 health
- 데이터 노드별 상태와 shard allocation
- Logstash 또는 ingest pipeline 오류
- Kibana readiness 및 Elasticsearch 연결 상태

이번 데이터에는 해당 필드가 포함되어 있지 않으므로 재시작 횟수, CrashLoopBackOff 여부, OOMKilled 여부를 확인할 수 없다.

| 점검 항목 | 결과 |
|---|---|
| Elasticsearch 데이터 노드 재시작 횟수 | 확인 불가 |
| Logstash 재시작 횟수 | 확인 불가 |
| Kibana 재시작 횟수 | 확인 불가 |
| Elasticsearch 클러스터 health | 확인 불가 |
| 초기 설정 Job 성공 여부 | 확인 불가 |
| 로깅 시스템 전체 안정성 | 판단 보류 |

따라서 현재 근거로는 ELK가 안정적이라고도, 불안정하다고도 결론 내릴 수 없다. 확인된 것은 `es-advanced-setup` Job이 존재했다는 사실뿐이다.

## 5. 종합 분석

이번 원시 데이터에서 가장 신뢰도 높게 확인되는 운영 이슈는 `kube-state-metrics`의 반복적인 Liveness probe HTTP 503이다. 2026년 9월 10일부터 9월 11일까지 동일 유형의 이벤트가 147회 발생했기 때문에, 모니터링 컴포넌트의 응답성 또는 프로브 설정에 대한 점검이 필요하다.

반면 백업과 ELK는 상태 데이터가 충분하지 않다.

- 백업은 Kopia 유지보수 Job의 메타데이터만 확인되며, 성공·실패 결과가 없다.
- ELK는 Elasticsearch 초기 설정 Job의 메타데이터만 확인되며, 상시 서비스 파드의 상태와 재시작 정보가 없다.
- 따라서 백업 성공률이나 ELK 재시작 횟수를 임의의 숫자로 보고하는 것은 부정확하다.

이번 분석의 핵심은 “데이터가 없다”와 “문제가 없다”를 구분하는 것이다. 현재 백업과 로깅에 장애 증거가 없다는 의미가 아니라, 장애 여부를 판단할 필수 필드가 제공되지 않았다는 의미다.

## 6. 총평 및 다음 주 조치 권고

### 총평

모니터링 계층에서는 `kube-state-metrics`의 Liveness probe 503이 147회 반복되어 주의가 필요하다. 이 문제가 지속되면 Kubernetes 상태 메트릭의 수집 신뢰도와 알림 품질이 함께 저하될 수 있다. 백업과 ELK는 제공된 원시 데이터가 메타데이터 중심으로 제한되어 성공률과 재시작 안정성을 산출할 수 없으므로, 현재 상태를 정상으로 판정해서는 안 된다.

### 다음 주 조치 권고

| 우선순위 | 조치 | 목적 |
|---:|---|---|
| P1 | `kube-state-metrics` 파드의 CPU·메모리 사용량과 컨테이너 로그 확인 | HTTP 503의 실제 원인 확인 |
| P1 | Liveness probe의 `path`, `timeoutSeconds`, `failureThreshold`, `periodSeconds` 점검 | 과도하거나 부정확한 프로브 설정 여부 확인 |
| P1 | 해당 파드의 `restartCount`와 마지막 종료 상태 확인 | 147회 경고가 실제 재시작으로 이어졌는지 검증 |
| P2 | Prometheus scrape error 및 `kube-state-metrics` 응답 지연 확인 | 모니터링 데이터 공백 여부 확인 |
| P2 | Velero/Kopia Job 목록과 Job condition을 기간 기준으로 재수집 | 백업 성공률을 정상적으로 계산 |
| P2 | 실패 Job의 컨테이너 로그와 종료 코드를 수집 | 저장소·인증·리소스·락 문제 구분 |
| P2 | Elasticsearch, Logstash, Kibana 전체 파드의 `restartCount` 수집 | ELK 안정성 판단 |
| P3 | Elasticsearch `_cluster/health`와 노드별 상태 점검 | 데이터 계층의 실제 가용성 확인 |
| P3 | 백업·모니터링·로깅 지표를 주간 리포트용으로 구조화 | 다음 분석의 재현성과 자동화 확보 |

다음 주부터는 단순한 `PodList`와 `EventList`만 수집하지 말고, Job 결과와 컨테이너 상태를 함께 저장해야 한다. 특히 다음 필드는 운영 리포트의 필수 기준으로 관리하는 것이 바람직하다.

```text
Pod:
- metadata.name
- status.phase
- status.containerStatuses[*].ready
- status.containerStatuses[*].restartCount
- status.containerStatuses[*].state
- status.containerStatuses[*].lastState

Job:
- status.active
- status.succeeded
- status.failed
- status.startTime
- status.completionTime
- status.conditions

Event:
- reason
- message
- type
- firstTimestamp
- lastTimestamp
- count
```

이번 주 결론은 다음과 같다.

> 모니터링에서는 반복적인 `kube-state-metrics` Liveness 503 경고가 확인되었고, 백업 성공률과 ELK 재시작 안정성은 상태·결과 필드가 누락되어 추가 수집 전까지 판정할 수 없다.