---
layout: post
title: "[Weekly Report] 2026년 36주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# 주간 인프라 건강 검진: 2026년 36주차

> 분석 대상: 제공된 Kubernetes 원시 데이터 발췌본  
> 분석 기준: 파드 상태, Job 소유 관계, Kubernetes Warning 이벤트, 재시작 관련 필드  
> 데이터 신뢰도: 제한적 — 일부 객체가 중간에서 잘렸으며 `status`, `containerStatuses`, `restartCount`가 확인되지 않음

## 1. 주간 요약

제공된 원시 데이터만 기준으로 보면, 모니터링 영역에서는 `DNSConfigForming` 경고가 3,452회 누적되어 가장 명확한 운영 리스크로 확인되지만, 백업 성공률과 ELK 재시작 안정성은 필수 상태 필드가 누락되어 정량 판정할 수 없다.

| 영역 | 관찰 결과 | 상태 | 신뢰도 | 우선 조치 |
|---|---|---:|---:|---|
| Velero/Kopia 백업 | Kopia 유지보수 Job 파드 1건 식별, 성공/실패 상태 미확인 | 판정 보류 | 낮음 | Job 및 Pod `status` 재수집 |
| 백업 성공률 | 성공·실패·전체 건수를 계산할 필드 부족 | 계산 불가 | 낮음 | 지난 7일 Job 목록과 종료 상태 확보 |
| 모니터링 | `DNSConfigForming` Warning 3,452회 누적 | 주의 | 높음 | 노드 및 Pod DNS 설정 정비 |
| 이벤트 최신성 | 확인된 이벤트 시각이 2026-05-12로, 36주차와 불일치 | 데이터 정합성 경고 | 높음 | 이벤트 수집 시간창 재확인 |
| ELK | `es-advanced-setup` Job 파드 식별, 재시작 및 종료 상태 미확인 | 판정 보류 | 낮음 | `containerStatuses` 및 Job condition 재수집 |

## 2. 백업: Velero/Kopia

### 2.1 확인된 객체

확인된 백업 관련 객체는 `velero` 네임스페이스의 Kopia 저장소 유지보수 파드다.

| 항목 | 값 |
|---|---|
| 파드 | `agent-system-default-kopia-4hxm2-maintain-job-178853641782c2fxp` |
| 네임스페이스 | `velero` |
| 소유 Job | `agent-system-default-kopia-4hxm2-maintain-job-1788536417822` |
| 저장소 | `agent-system-default-kopia-4hxm2` |
| 생성 시각 | 2026-09-04 15:40:17 UTC |
| 파드 유형 | Kopia repository maintenance Job 파드 |
| 확인 가능한 상태 | 메타데이터 및 소유 관계 |
| 확인 불가능한 상태 | `Succeeded`, `Failed`, 종료 코드, 재시작 횟수, 컨테이너 로그 |

파드의 `ownerReferences`와 Job 라벨은 정상적으로 연결되어 있다. 따라서 Kubernetes가 해당 파드를 Kopia 유지보수 Job의 실행 단위로 생성한 사실은 확인된다.

다만, 메타데이터만으로는 해당 Job이 성공했는지 판단할 수 없다. 실제 성공 여부는 다음 상태 필드 중 하나 이상이 필요하다.

- `pod.status.phase`
- `pod.status.containerStatuses[].state.terminated.exitCode`
- `pod.status.containerStatuses[].restartCount`
- `job.status.succeeded`
- `job.status.failed`
- `job.status.conditions`
- 컨테이너 종료 메시지 및 로그

### 2.2 백업 성공률

백업 성공률은 다음 식으로 계산한다.

```text
성공률 = 성공한 백업 Job 수 / 전체 백업 Job 수 × 100
```

그러나 제공된 데이터에는 다음과 같은 문제가 있다.

1. 백업 전체 Job 목록이 아닌 단일 파드 객체만 포함되어 있다.
2. 해당 파드의 `status` 영역이 제공되지 않았다.
3. `Succeeded` 또는 `Failed`를 판별할 `Job.status`가 없다.
4. 유지보수 Job과 실제 Velero 백업 Job이 구분되어 있지 않다.
5. 지난 7일 전체 실행 건수와 재시도 건수가 확인되지 않는다.

따라서 이번 발췌본 기준 백업 성공률은 계산할 수 없다.

| 지표 | 결과 |
|---|---:|
| 확인된 백업 관련 파드 | 1건 |
| 성공한 Job | 미확인 |
| 실패한 Job | 미확인 |
| 전체 백업 Job | 미확인 |
| 계산 가능한 성공률 | 불가 |

`201 Created`와 같은 생성 응답이나 파드 객체의 존재만으로 백업 성공을 판정해서는 안 된다. 백업 데이터의 실제 저장 성공 여부는 Velero Backup 리소스의 완료 상태와 Kopia 저장소 유지보수 결과를 함께 확인해야 한다.

### 2.3 실패 원인 추론

현재 제공된 데이터에는 실패 상태나 종료 코드가 없으므로 특정 Job의 실패 원인을 확정할 수 없다.

다만 대상이 `maintain-job`인 점을 고려하면, 실제 실패 여부가 확인될 경우 우선 조사할 후보는 다음과 같다.

| 후보 원인 | 확인해야 할 증거 |
|---|---|
| 오브젝트 스토리지 인증 또는 권한 오류 | 컨테이너 로그의 `AccessDenied`, `Unauthorized`, credential 관련 메시지 |
| 저장소 연결 및 네트워크 오류 | timeout, DNS resolution, TLS handshake 오류 |
| Kopia 저장소 잠금 또는 동시 실행 | repository lock, concurrent maintenance 메시지 |
| 디스크 공간 부족 | 노드 디스크 사용량, ephemeral-storage eviction 이벤트 |
| Job 실행 시간 초과 | `activeDeadlineSeconds`, Job 종료 시각, kubelet 이벤트 |
| 리소스 부족 또는 OOM | 종료 코드 137, `OOMKilled`, 노드 메모리 압박 이벤트 |

현재 확인된 정보만으로는 위 후보 중 어느 것도 원인으로 선택할 수 없다.

### 2.4 권고 데이터

다음 수집 결과가 확보되면 실제 성공률과 실패 원인을 계산할 수 있다.

```bash
kubectl -n velero get jobs,pods \
  -l velero.io/repo-name=agent-system-default-kopia-4hxm2 \
  -o json

kubectl -n velero get backup -o json

kubectl -n velero logs \
  agent-system-default-kopia-4hxm2-maintain-job-178853641782c2fxp \
  --all-containers
```

특히 지난 7일의 실행 건수를 정확히 계산하려면 유지보수 Job뿐 아니라 실제 Velero Backup 리소스와 Kopia repository 상태를 시간 범위로 분리해 수집해야 한다.

## 3. 모니터링: 주요 경고 이벤트

### 3.1 `DNSConfigForming`

확인된 주요 경고는 `monitoring` 네임스페이스의 Prometheus Node Exporter 파드에서 발생한 `DNSConfigForming` 이벤트다.

| 항목 | 값 |
|---|---|
| 대상 파드 | `kps-prometheus-node-exporter-2rrxl` |
| 네임스페이스 | `monitoring` |
| 경고 사유 | `DNSConfigForming` |
| 이벤트 유형 | `Warning` |
| 발생 컴포넌트 | `kubelet` |
| 발생 노드 | `lemuel` |
| 최초 발생 | 2026-05-12 01:54:32 UTC |
| 마지막 발생 | 2026-05-12 12:24:37 UTC |
| 누적 횟수 | 3,452회 |
| 적용된 nameserver | `8.8.8.8 1.1.1.1 61.41.153.2` |

주요 메시지는 다음과 같다.

```text
Nameserver limits were exceeded, some nameservers have been omitted,
the applied nameserver line is: 8.8.8.8 1.1.1.1 61.41.153.2
```

### 3.2 원인 분석

Kubernetes 파드의 `/etc/resolv.conf`에 적용할 nameserver 수가 허용 한도를 초과하여 일부 nameserver가 제거된 상황이다.

가능한 구성 경로는 다음과 같다.

- 노드의 `/etc/resolv.conf`에 nameserver가 과도하게 설정됨
- `dnsConfig.nameservers`를 파드 또는 Helm chart에서 추가함
- kubelet의 `clusterDNS` 또는 노드 resolver 설정이 중복됨
- VPN, 사내 DNS, Docker 또는 NetworkManager가 resolver 항목을 누적시킴
- `ndots`, search domain과 함께 DNS 설정이 비정상적으로 확장됨

이 경고는 즉시 애플리케이션 장애를 의미하지는 않는다. 다만 제거된 nameserver가 내부 서비스 DNS 또는 특정 외부 도메인 해석에 필요하다면 간헐적인 이름 해석 실패와 지연으로 이어질 수 있다.

특히 Node Exporter 자체는 DNS 의존도가 낮을 수 있지만, 동일 노드에 배치된 다른 파드가 동일한 DNS 구성을 상속받을 가능성이 있으므로 노드 단위의 구성 문제로 보는 것이 타당하다.

### 3.3 이벤트 최신성 검증

이 보고서의 제목은 2026년 36주차를 대상으로 하지만, 제공된 모니터링 이벤트의 최초·최종 발생 시각은 2026-05-12다.

따라서 이 이벤트는 다음 중 하나일 수 있다.

1. 현재 주간 데이터가 아니라 과거 이벤트가 혼입됨
2. 이벤트 저장소가 오래된 리소스를 반환함
3. 수집 시점과 이벤트 발생 시점이 서로 다름
4. “최근 일주일” 필터가 적용되지 않음

그러므로 `DNSConfigForming` 3,452회는 누적 경고로는 유효하지만, 2026년 36주차에 새롭게 발생한 경고라고 단정해서는 안 된다.

### 3.4 권고 조치

노드와 파드의 실제 DNS 구성을 비교해 원인을 좁혀야 한다.

```bash
kubectl get pod -n monitoring kps-prometheus-node-exporter-2rrxl \
  -o yaml

kubectl get node lemuel -o yaml

kubectl -n monitoring exec \
  kps-prometheus-node-exporter-2rrxl -- cat /etc/resolv.conf

cat /etc/resolv.conf
```

권고 순서는 다음과 같다.

1. 노드의 nameserver 개수와 파드의 `dnsConfig`를 비교한다.
2. 중복 또는 불필요한 nameserver를 제거한다.
3. 내부 DNS가 필요한 경우 CoreDNS와 upstream resolver의 역할을 분리한다.
4. Node Exporter 파드만이 아니라 동일 노드의 주요 워크로드에서도 DNS 오류가 발생하는지 확인한다.
5. 수정 후 동일 이벤트의 신규 발생 횟수가 감소하는지 확인한다.

## 4. ELK: 로깅 시스템 안정성

### 4.1 확인된 객체

제공된 로깅 데이터에서는 `logging` 네임스페이스의 Elasticsearch 초기 설정 Job 파드가 확인된다.

| 항목 | 값 |
|---|---|
| 파드 | `es-advanced-setup-6whld` |
| 네임스페이스 | `logging` |
| 소유 Job | `es-advanced-setup` |
| 컨테이너 | `setup` |
| 생성 시각 | 2026-09-04 17:22:36 UTC |
| 사용 Secret | `ES_PASS` |
| 확인 가능한 상태 | Job 소유 관계, 컨테이너 및 Secret 참조 |
| 확인 불가능한 상태 | 종료 상태, 재시작 횟수, 종료 코드, 로그, Job condition |

파드는 `es-advanced-setup` Job에 의해 생성되었고, `ES_PASS` 환경 변수는 Secret 참조를 통해 주입되도록 구성되어 있다. 설정 구조 자체는 확인되지만, 실제 Elasticsearch 초기화가 성공했는지는 알 수 없다.

### 4.2 재시작 및 안정성 점검

ELK 안정성의 핵심 지표인 다음 필드가 원시 데이터에 포함되지 않았다.

- `status.containerStatuses[].restartCount`
- `status.containerStatuses[].ready`
- `status.containerStatuses[].state`
- `status.containerStatuses[].lastState`
- `status.phase`
- Job의 `succeeded`, `failed`, `backoffLimit`
- Elasticsearch StatefulSet 파드의 재시작 횟수
- Elasticsearch 클러스터 health 상태
- 디스크 watermark 및 shard allocation 상태

따라서 현재 데이터로는 ELK가 안정적으로 운영되고 있다고 판단할 수 없다.

| 안정성 지표 | 결과 |
|---|---:|
| `es-advanced-setup` 파드 확인 | 1건 |
| 컨테이너 재시작 횟수 | 미확인 |
| OOMKilled 여부 | 미확인 |
| CrashLoopBackOff 여부 | 미확인 |
| Elasticsearch 클러스터 health | 미확인 |
| StatefulSet 전체 상태 | 미확인 |
| 로깅 시스템 안정성 최종 판정 | 보류 |

초기 설정 Job은 일회성 작업이므로 재시작 횟수만으로 전체 ELK 안정성을 대표할 수 없다. 실제 안정성 검증에는 Elasticsearch 노드 파드, Kibana, Logstash 또는 Fluent Bit/Fluentd 수집기까지 함께 확인해야 한다.

### 4.3 우선 확인할 장애 후보

초기 설정 Job이 실패한 것으로 확인될 경우 다음 항목을 우선 조사해야 한다.

| 장애 후보 | 확인 증거 |
|---|---|
| Elasticsearch 인증 실패 | `401`, `403`, invalid password 로그 |
| Elasticsearch endpoint 연결 실패 | connection refused, timeout, DNS 오류 |
| 설정 파일 또는 ConfigMap 오류 | `/cfg` 마운트 파일 누락 및 파싱 오류 |
| 초기화 순서 문제 | Elasticsearch readiness 이전 setup 실행 |
| TLS 인증서 문제 | certificate verify failed, unknown CA |
| 리소스 부족 | OOMKilled, CPU throttling, 노드 pressure |
| 반복 실행 충돌 | 이미 생성된 index/template/role 관련 오류 |

## 5. 데이터 품질 및 분석 한계

이번 분석은 제공된 JSON 발췌본에 한정한다. 다음과 같은 이유로 일부 요구사항은 정량적으로 완료할 수 없다.

| 제한 사항 | 영향 |
|---|---|
| Backup `items` 중 단일 객체만 제공 | 전체 백업 실행 건수와 성공률 계산 불가 |
| Backup 파드 `status` 누락 | 성공·실패 및 종료 코드 판정 불가 |
| Monitoring 이벤트 목록 중 일부만 제공 | 최근 일주일의 주요 경고 전체 정리 불가 |
| 이벤트 시각이 2026-05-12 | 2026년 36주차 최근성 검증 불가 |
| Logging 파드 `status` 누락 | 재시작 횟수와 CrashLoop 여부 판정 불가 |
| Elasticsearch 워크로드 정보 부재 | ELK 전체 안정성 판정 불가 |
| Job condition 및 로그 부재 | 실패 원인 확정 불가 |

따라서 본문에서 “백업 성공률”, “ELK 재시작 횟수”, “특정 Job 실패 원인”을 확정 수치나 단일 원인으로 제시하는 것은 근거가 부족하다.

## 6. 총평 및 다음 주 조치 권고

### 총평

현재 확인 가능한 가장 명확한 운영 리스크는 `lemuel` 노드에서 발생한 nameserver 초과 경고다. 누적 3,452회라는 수치는 단발성 이벤트가 아니라 resolver 구성이 반복적으로 잘못 적용되고 있음을 보여준다.

반면 Velero/Kopia와 ELK는 파드 메타데이터와 소유 관계만 확인되며, 성공·실패·재시작을 판단하는 핵심 Runtime Trace가 누락되어 있다. 따라서 두 영역을 정상으로 분류하는 것도, 장애로 분류하는 것도 현재로서는 부적절하다.

또한 모니터링 이벤트가 2026년 5월에 발생한 것으로 기록되어 있어, 2026년 36주차 주간 리포트에 포함하기 전에 수집 시간창과 필터 조건을 먼저 검증해야 한다.

### 다음 주 우선순위

| 우선순위 | 조치 | 성공 기준 |
|---:|---|---|
| P0 | `lemuel` 노드의 `/etc/resolv.conf`, kubelet DNS 설정, 파드 `dnsConfig` 비교 | nameserver 중복 제거 및 신규 `DNSConfigForming` 미발생 |
| P0 | 최근 7일 Monitoring Event만 대상으로 재수집 | 이벤트 발생 시각이 보고 기간과 일치 |
| P1 | Velero Backup 및 Kopia Job 전체 상태 재수집 | 전체 건수, 성공 건수, 실패 건수, 성공률 산출 |
| P1 | 실패한 백업 Job의 컨테이너 로그와 종료 코드 확보 | 인증·네트워크·스토리지·리소스 중 원인 분류 |
| P1 | Elasticsearch StatefulSet 및 setup Job 상태 확인 | Ready 파드 수, 재시작 횟수, 종료 코드 확인 |
| P2 | Elasticsearch `_cluster/health` 및 디스크 watermark 점검 | 클러스터 health와 shard allocation 정상 확인 |
| P2 | 백업·모니터링·로깅 수집 쿼리에 시간 필터 적용 | 다음 주부터 동일 기준의 재현 가능한 리포트 생성 |

최종적으로 다음 주 리포트에는 다음 지표를 고정 포함하는 것이 좋다.

```text
Backup:
- 전체 Backup Job 수
- 성공/실패/실행 중 건수
- 성공률
- 실패 Job별 exit code와 원인
- Velero Backup 완료 상태

Monitoring:
- 보고 기간 내 Warning 이벤트 수
- reason별 발생 횟수
- 대상 노드·네임스페이스·파드
- 최초/최종 발생 시각
- 반복 이벤트 여부

ELK:
- 구성 요소별 Ready 파드 수
- 파드별 restartCount
- OOMKilled 및 CrashLoopBackOff 여부
- Elasticsearch cluster health
- 디스크 사용량과 shard allocation 상태
```

이번 주의 결론은 “모니터링 DNS 구성 이상은 확인되었고, 백업 및 ELK의 정상 여부는 상태·로그 데이터 보강 전까지 판정 보류”다.