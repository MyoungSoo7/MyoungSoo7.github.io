---
layout: post
title: "[Weekly Report] 2026년 38주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# 주간 인프라 건강 검진: 2026년 38주차

## 분석 범위 및 판정 기준

이번 리포트는 제공된 Kubernetes 원시 데이터 중 다음 항목을 기준으로 작성했다.

- 백업: `velero` 네임스페이스의 Velero/Kopia 관련 Pod 및 Job 메타데이터
- 모니터링: `monitoring` 네임스페이스의 Kubernetes Warning Event
- 로깅: `logging` 네임스페이스의 Elasticsearch 관련 Pod 메타데이터

다만 제공된 원시 데이터는 일부 필드가 중간에서 잘려 있으며, 다음 핵심 필드가 확인되지 않는다.

- Pod의 `status.phase`
- `containerStatuses`
- 컨테이너별 `restartCount`
- Job의 `status.succeeded`, `status.failed`, `conditions`
- 컨테이너 종료 코드와 종료 사유
- 전체 Pod 및 Event 목록

따라서 확인되지 않은 값을 성공 또는 실패로 추정하지 않고, 원시 데이터에서 직접 확인 가능한 사실과 판정 불가 항목을 구분했다.

## 주간 요약

| 영역 | 관측 결과 | 상태 | 판정 근거 |
|---|---:|---|---|
| Velero/Kopia 백업 | Kopia 유지보수 Job Pod 1건 확인 | 판정 보류 | Pod 상태와 Job 완료 조건이 제공되지 않음 |
| 백업 성공률 | 계산 불가 | 확인 필요 | 전체 실행 건수와 성공·실패 상태가 없음 |
| 모니터링 | `DNSConfigForming` Warning 확인 | 주의 | kubelet이 Nameserver 제한 초과를 보고 |
| 모니터링 경고 누적 | 확인 가능한 이벤트 1건에서 3,452회 | 경고 | 동일 이벤트가 반복 발생 |
| ELK | Elasticsearch 초기 설정 Job Pod 1건 확인 | 판정 보류 | 종료 상태와 재시작 횟수가 없음 |
| ELK 재시작 안정성 | 계산 불가 | 확인 필요 | `containerStatuses.restartCount` 미제공 |

## 1. 백업: Velero/Kopia 상태 분석

### 1.1 관측된 리소스

확인된 Pod는 다음과 같다.

- 네임스페이스: `velero`
- Pod: `agent-system-default-kopia-4hxm2-maintain-job-178974446131mllwq`
- 관련 Job: `agent-system-default-kopia-4hxm2-maintain-job-1789744461311`
- Kopia Repository: `agent-system-default-kopia-4hxm2`
- 생성 시각: `2026-09-18T15:14:21Z`
- 용도: Kopia repository maintenance Job

이 리소스는 일반적인 Velero 백업 실행 Pod라기보다는 Kopia repository 유지보수 작업을 수행하는 Job Pod로 보인다. 따라서 이 Pod의 존재만으로 애플리케이션 백업이 성공했다고 판단할 수 없다.

### 1.2 백업 성공률

현재 제공된 데이터만으로는 백업 성공률을 계산할 수 없다.

| 지표 | 결과 |
|---|---:|
| 확인 가능한 Pod 레코드 | 1건 |
| 성공한 Job 수 | 확인 불가 |
| 실패한 Job 수 | 확인 불가 |
| 전체 Job 실행 수 | 확인 불가 |
| 백업 성공률 | 계산 불가 |

성공률은 다음과 같은 실행 결과 필드가 있어야 계산할 수 있다.

```text
성공률 = 성공한 백업 Job 수 / 전체 백업 Job 수 × 100
```

현재 데이터에는 `status.succeeded`, `status.failed`, `conditions`, `containerStatuses.state.terminated.exitCode`가 포함되어 있지 않다.

### 1.3 실패한 특정 Job 및 원인 추론

제공된 데이터에서는 실패 상태가 확인된 Job이 없다. 따라서 특정 Job이 실패했다고 단정하거나 원인을 추론할 수 없다.

다만 실패 여부를 분석하려면 다음 항목을 추가로 확인해야 한다.

- Job의 `status.failed`
- Job의 `status.conditions`
- Pod의 `status.phase`
- 컨테이너 종료 코드
- `reason`, `message`
- Velero 서버 로그
- Kopia maintenance 로그
- Repository 접근 오류
- 오브젝트 스토리지의 인증·권한·용량 오류
- PVC 또는 네트워크 연결 오류

특히 Kopia 유지보수 Job에서 실제 실패가 확인될 경우에는 다음 순서로 원인을 분리하는 것이 적절하다.

1. `exitCode`와 종료 사유 확인
2. Kopia repository 접근 가능 여부 확인
3. 오브젝트 스토리지 인증 및 권한 확인
4. 저장소 용량과 API 오류 확인
5. Velero 로그와 Kopia 로그의 동일 시각 오류 대조
6. Job 재시도 횟수 및 backoff 동작 확인

현재 단계의 결론은 다음과 같다.

> Kopia 유지보수 Pod가 생성된 사실은 확인되지만, 작업 완료 또는 백업 성공은 검증되지 않았다.

## 2. 모니터링: 주요 경고 이벤트

### 2.1 확인된 경고

제공된 이벤트에서 명확하게 해석할 수 있는 주요 경고는 `DNSConfigForming`이다.

| 시각 | 대상 | Reason | 메시지 | 발생 횟수 | 심각도 |
|---|---|---|---|---:|---|
| 2026-05-12 01:54:32Z ~ 12:24:37Z | `kps-prometheus-node-exporter-2rrxl` | `DNSConfigForming` | Nameserver limits were exceeded | 3,452회 | Warning |

kubelet이 보고한 실제 적용 nameserver는 다음과 같다.

```text
8.8.8.8 1.1.1.1 61.41.153.2
```

### 2.2 DNSConfigForming 분석

Kubernetes Pod의 DNS 설정에는 nameserver 개수 제한이 있다. 노드의 `/etc/resolv.conf` 또는 kubelet이 참조하는 DNS 설정에 nameserver가 과도하게 등록되어 있으면 kubelet은 일부 nameserver를 제거한 뒤 Pod에 적용한다.

이번 이벤트의 메시지는 다음 상태를 의미한다.

- Pod DNS 설정에 입력된 nameserver가 Kubernetes 제한을 초과함
- kubelet이 일부 nameserver를 생략함
- Pod에는 일부 nameserver만 적용됨
- 애플리케이션이 의도하지 않은 DNS resolver를 사용할 가능성이 있음

다만 현재 데이터만으로는 실제 DNS 질의 실패가 발생했는지 확인할 수 없다. 따라서 이 이벤트는 즉시 장애를 의미한다기보다, 노드 DNS 설정과 Pod DNS 동작이 불일치할 수 있다는 운영 경고로 보는 것이 적절하다.

### 2.3 시간 범위의 불일치

분석 대상은 2026년 38주차로 제시되었고 백업 및 로깅 데이터는 2026년 9월 18일에 생성되었다. 그러나 확인 가능한 모니터링 이벤트는 2026년 5월 12일에 발생했다.

따라서 이 이벤트를 38주차에 최근 발생한 경고라고 표현하기는 어렵다. 현재 제공된 데이터 기준으로는 다음과 같이 정리하는 것이 정확하다.

> 모니터링 데이터에는 과거에 반복적으로 발생한 DNS 설정 경고가 포함되어 있으나, 38주차에 새로 발생한 이벤트인지 여부는 확인할 수 없다.

### 2.4 권고 조치

다음 항목을 노드 및 Pod 단위로 확인해야 한다.

```bash
kubectl get pod -n monitoring kps-prometheus-node-exporter-2rrxl -o yaml
kubectl get event -n monitoring --sort-by=.lastTimestamp
kubectl describe node lemuel
kubectl get pod -n monitoring kps-prometheus-node-exporter-2rrxl \
  -o jsonpath='{.spec.dnsPolicy}{"\n"}{.spec.dnsConfig}{"\n"}'
```

운영 조치는 다음 순서가 적절하다.

1. 노드의 실제 `/etc/resolv.conf` nameserver 구성 확인
2. kubelet의 `--resolv-conf` 설정 확인
3. NetworkManager, systemd-resolved 또는 DHCP가 중복 nameserver를 주입하는지 확인
4. 클러스터 DNS 설정과 노드 DNS 설정의 책임 범위 분리
5. 수정 후 신규 Pod에서 `/etc/resolv.conf`를 재확인
6. `DNSConfigForming` 이벤트의 재발 여부 확인

## 3. ELK: 로깅 시스템 안정성 점검

### 3.1 관측된 Elasticsearch 관련 Pod

확인된 Pod는 Elasticsearch 초기 설정 작업으로 보인다.

- 네임스페이스: `logging`
- Pod: `es-advanced-setup-xxq7z`
- 관련 Job: `es-advanced-setup`
- 생성 시각: `2026-09-18T17:25:34Z`
- 컨테이너: `setup`

Pod 정의에서 다음 정보는 확인된다.

- 컨테이너가 Secret에서 `ES_PASS`를 주입받음
- `/cfg` 볼륨을 읽기 전용으로 마운트
- Job 소유 Pod로 생성됨

그러나 Pod의 실행 결과와 종료 상태는 제공되지 않았다.

### 3.2 재시작 횟수 및 안정성

ELK 안정성을 판단하려면 `containerStatuses.restartCount`와 종료 상태가 필요하다. 현재 데이터에는 해당 필드가 없으므로 재시작 횟수와 안정성을 계산할 수 없다.

| 점검 항목 | 결과 |
|---|---|
| Elasticsearch Pod 재시작 횟수 | 확인 불가 |
| Setup 컨테이너 종료 코드 | 확인 불가 |
| Setup Job 성공 여부 | 확인 불가 |
| Elasticsearch 본체 Pod 상태 | 제공 데이터에서 확인 불가 |
| CrashLoopBackOff 여부 | 확인 불가 |
| OOMKilled 여부 | 확인 불가 |

따라서 `es-advanced-setup` Pod가 생성된 사실만으로 Elasticsearch 설정이 완료되었거나 로깅 시스템이 정상이라고 판단해서는 안 된다.

### 3.3 필요한 검증 명령

다음 정보를 확보하면 ELK 안정성을 정량적으로 판단할 수 있다.

```bash
kubectl get pods -n logging -o wide
kubectl get pods -n logging -o json \
  | jq '.items[] | {
      name: .metadata.name,
      phase: .status.phase,
      containers: [
        .status.containerStatuses[]? |
        {
          name: .name,
          ready: .ready,
          restartCount: .restartCount,
          state: .state,
          lastState: .lastState
        }
      ]
    }'

kubectl get jobs -n logging
kubectl describe job -n logging es-advanced-setup
kubectl logs -n logging job/es-advanced-setup --all-containers
```

특히 다음 상태가 있으면 장애 위험도가 높다.

- `restartCount`의 지속적인 증가
- `CrashLoopBackOff`
- `OOMKilled`
- `Error` 종료
- Elasticsearch readiness probe 실패
- Filebeat 또는 Logstash의 전송 실패
- Elasticsearch cluster health가 `yellow` 또는 `red`
- 디스크 watermark 초과
- 인덱싱 지연 또는 bulk reject 증가

## 종합 판정

| 점검 영역 | 현재 판정 | 주요 리스크 |
|---|---|---|
| Velero/Kopia | 상태 미확정 | Job 완료 여부와 백업 성공 여부를 검증할 수 없음 |
| 백업 성공률 | 계산 불가 | 전체 실행 수 및 성공·실패 결과 부재 |
| 모니터링 | DNS 설정 경고 확인 | 노드 DNS 설정 과다 및 일부 nameserver 누락 |
| ELK | 상태 미확정 | 재시작, 종료 코드, Elasticsearch 본체 상태 부재 |
| 데이터 품질 | 일부 원시 데이터 잘림 | `status` 기반의 확정적 RCA 제한 |

## 총평 및 다음 주 조치 권고

이번 데이터만으로는 백업과 ELK가 정상 동작했다고 확정할 수 없다. Velero/Kopia와 Elasticsearch 관련 리소스가 생성된 사실은 확인되지만, Kubernetes 운영 상태를 판정하는 핵심 근거인 `status`, `conditions`, `restartCount`, 종료 코드가 빠져 있기 때문이다.

반면 모니터링 영역에서는 `DNSConfigForming` 경고가 3,452회 반복된 사실이 확인되었다. 이 경고는 kubelet이 nameserver 제한을 초과한 DNS 설정을 일부 제거하고 Pod에 적용했다는 의미다. 실제 장애가 발생했다는 증거는 없지만, 노드 DNS 구성의 불일치와 이름 해석 장애 가능성을 남기는 운영 리스크다.

다음 주에는 아래 순서로 점검하는 것을 권고한다.

1. 백업 Job의 전체 실행 목록과 성공·실패 상태 수집
2. Velero Backup 리소스의 `phase`, `errors`, `warnings` 확인
3. Kopia repository maintenance Job의 종료 코드와 로그 확인
4. 실제 백업 아티팩트가 저장소에 생성되었는지 별도 검증
5. 노드별 `/etc/resolv.conf`와 kubelet DNS 설정 비교
6. `DNSConfigForming` 이벤트의 신규 발생 여부 확인
7. logging 네임스페이스 전체 Pod의 `restartCount`, `lastState`, readiness 확인
8. Elasticsearch cluster health와 디스크 watermark 확인
9. Filebeat, Logstash 또는 수집기에서 Elasticsearch로의 전송 성공 여부 확인
10. 다음 주 리포트부터 원시 수집 시 `status`와 `containerStatuses`를 필수 필드로 포함

운영 판단은 다음과 같다.

> 현재 클러스터는 즉시 장애로 단정할 수 있는 증거는 부족하지만, DNS 경고는 반복성이 높고 백업·ELK 상태는 검증 필드가 누락되어 있다. 다음 점검에서는 리소스 생성 여부가 아니라 Job 완료 상태, 실제 백업 결과, 컨테이너 재시작, 로그 전송 결과를 기준으로 성공 여부를 판정해야 한다.