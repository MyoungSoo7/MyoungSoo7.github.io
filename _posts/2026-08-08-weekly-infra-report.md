---
layout: post
title: "[Weekly Report] 2026년 32주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# 주간 인프라 건강 검진: 2026년 32주차

## 분석 범위 및 데이터 품질

이번 리포트는 제공된 Kubernetes 원시 데이터 중 확인 가능한 필드만을 기준으로 작성했다. 다만 백업·모니터링·로깅 데이터가 모두 일부만 제공되었고, 수집 시점도 일관되지 않아 일부 지표는 정확한 성공률이나 재시작 횟수로 확정할 수 없다.

| 영역 | 확인된 데이터 | 분석 가능 범위 | 데이터 제약 |
|---|---|---|---|
| 백업 | Velero/Kopia Pod 1건 | 대상 Job과 Pod의 존재 여부, 메타데이터 확인 | `status.phase`, 컨테이너 종료 코드, Job `conditions` 부재 |
| 모니터링 | `DNSConfigForming` 이벤트 | 경고 종류, 발생 횟수, 영향 대상 분석 | 일부 EventList만 제공되며 최근 1주 데이터인지 불명확 |
| 로깅 | `fluent-bit` Pod 1건 | Fluent Bit DaemonSet 소속 및 구성 정보 확인 | `containerStatuses`, `restartCount`, Elasticsearch/Kibana 상태 부재 |

> 주의: 제공된 데이터의 시간 범위가 일관되지 않는다. 백업 Pod는 `2026-08-07`에 생성되었지만, 모니터링 경고는 `2026-05-12`에 발생했으며, Fluent Bit Pod는 `2026-07-30`에 생성되었다. 따라서 모든 데이터를 동일한 2026년 32주차 관측치로 간주할 수 없다.

## 1. 백업: Velero/Kopia 상태 분석

### 요약

| 항목 | 결과 | 판정 |
|---|---:|---|
| 확인된 Kopia 유지보수 Pod | 1개 | 관측됨 |
| 대상 Namespace | `velero` | 정상적인 배치 위치 |
| 대상 Repository | `agent-system-default-kopia-4hxm2` | 확인됨 |
| Job 이름 | `agent-system-default-kopia-4hxm2-maintain-job-1786117445359` | 확인됨 |
| Pod 성공 여부 | 판정 불가 | `status` 필드 부재 |
| 백업 성공률 | 산출 불가 | 성공·실패 상태 부재 |
| 실패 Job | 특정 불가 | 종료 코드와 Job 조건 부재 |

관측된 Pod의 이름은 다음과 같다.

```text
agent-system-default-kopia-4hxm2-maintain-job-1786117445357w76k
```

해당 Pod는 다음 Job에 의해 생성되었다.

```text
agent-system-default-kopia-4hxm2-maintain-job-1786117445359
```

또한 다음 Repository를 대상으로 하는 Kopia 유지보수 작업으로 식별된다.

```text
agent-system-default-kopia-4hxm2
```

Pod 생성 시각은 `2026-08-07T15:44:05Z`이며, Kubernetes 메타데이터상 Job과 Pod의 소유 관계는 정상적으로 구성되어 있다.

### 성공률 계산 결과

현재 제공된 데이터만으로는 백업 성공률을 계산할 수 없다.

백업 성공률을 계산하려면 최소한 다음 정보가 필요하다.

```text
Job 수
성공한 Job 수
실패한 Job 수
Job별 status.succeeded
Job별 status.failed
Pod별 status.phase
컨테이너별 terminated.exitCode
컨테이너별 terminated.reason
```

현재 데이터에는 Pod의 `metadata`와 `spec` 일부만 존재하며, 다음 핵심 필드가 누락되어 있다.

```yaml
status:
  phase:
  containerStatuses:
    state:
      terminated:
        exitCode:
        reason:
        message:
```

따라서 확인 가능한 수치는 `관측된 유지보수 Pod 1개`뿐이며, 이를 성공으로 간주하는 것은 근거 없는 추론이다.

```text
백업 성공률 = 성공한 Job 수 / 전체 Job 수 × 100
현재 결과   = 산출 불가
```

### 실패 Job 원인 추론

현재 제공된 데이터에서는 실패한 Job 자체를 식별할 수 없다. 따라서 특정 실패 원인을 확정할 수 없다.

다만 실제로 해당 Job이 실패했다면 다음 항목을 우선 확인해야 한다.

| 확인 대상 | 가능한 원인 |
|---|---|
| 컨테이너 종료 코드 | Kopia 유지보수 명령 실패, 프로세스 오류 |
| 로그의 Repository 오류 | Object Storage 연결 실패, 인증 실패, Repository 손상 |
| Pod 이벤트 | 스케줄링 실패, 이미지 Pull 실패, 노드 자원 부족 |
| Secret 참조 | AWS/Azure/Alibaba Cloud 인증 파일 또는 Secret 누락 |
| PVC·스토리지 | 저장 공간 부족, 파일시스템 오류, I/O 지연 |
| 네트워크 | Object Storage Endpoint 연결 실패, DNS 또는 방화벽 문제 |
| Job 조건 | `BackoffLimitExceeded`, `DeadlineExceeded` 등 |

현재 메타데이터에는 다음과 같은 클라우드 인증 파일 환경변수 구성이 일부 나타난다.

```text
ALIBABA_CLOUD_CREDENTIALS_FILE
AWS_SHARED_CREDENTIALS_FILE
AZURE_CREDENTIALS_FILE
```

그러나 실제 인증 파일의 존재 여부, Secret 마운트 상태, 인증 오류 로그는 제공되지 않았다. 따라서 인증 문제를 실패 원인으로 단정할 수는 없으며, 가능한 원인 후보 중 하나로만 분류해야 한다.

### 백업 영역 권고

1. 최근 1주일의 Velero 관련 Job을 시간순으로 수집한다.
2. 각 Job의 `status.succeeded`, `status.failed`, `conditions`를 함께 보존한다.
3. 실패 Job에 대해서는 Pod 로그와 `kubectl describe job/pod` 이벤트를 수집한다.
4. Kopia Repository별 유지보수 결과와 실제 Velero Backup 리소스 결과를 분리해 관리한다.
5. 성공률뿐 아니라 다음 지표를 함께 기록한다.

```text
Backup 성공률
Repository 유지보수 성공률
실패 유형별 비율
평균 소요 시간
마지막 성공 시각
마지막 실패 시각
Repository 저장 공간
```

## 2. 모니터링: 주요 경고 이벤트

### 요약

| 경고 | 대상 | 발생 횟수 | 최초 발생 | 마지막 발생 | 심각도 |
|---|---|---:|---|---|---|
| `DNSConfigForming` | `kps-prometheus-node-exporter-2rrxl` | 3,452회 | 2026-05-12 01:54:32 UTC | 2026-05-12 12:24:37 UTC | 과거 Warning |
| 영향 노드 | `lemuel` | - | - | - | 현재 상태 별도 검증 필요 |

주요 메시지는 다음과 같다.

```text
Nameserver limits were exceeded, some nameservers have been omitted,
the applied nameserver line is:
8.8.8.8 1.1.1.1 61.41.153.2
```

### DNSConfigForming 분석

Kubelet이 Pod에 적용할 DNS 설정을 구성하는 과정에서 nameserver 개수 제한을 초과했고, 일부 nameserver를 제거했다는 의미다. 이 기록은 `2026-05-12`에 관찰된 과거 이벤트이며, 이 리포트의 원시 데이터만으로 현재도 지속 중인 경고라고 판단할 수 없다.

관측된 최종 nameserver는 다음과 같다.

```text
8.8.8.8
1.1.1.1
61.41.153.2
```

당시 이벤트 집계는 12시간이 채 되지 않는 구간에서 3,452회였으므로 해당 시점의 이벤트 노이즈가 컸음을 보여준다. 그러나 현재 장애·현재 DNS 실패·서비스 영향의 증거는 아니다.

가능한 원인은 다음과 같다.

| 가능 원인 | 설명 |
|---|---|
| 노드의 `/etc/resolv.conf` 설정 과다 | 호스트 DNS에 여러 nameserver 또는 복잡한 search domain이 설정되었을 가능성 |
| NetworkManager 또는 VPN 영향 | 호스트 DNS 설정이 동적으로 변경되며 Kubernetes에 전달되었을 가능성 |
| `systemd-resolved` 연동 문제 | Stub resolver와 실제 resolver 설정이 일치하지 않을 가능성 |
| Pod DNS 정책 구성 문제 | `dnsPolicy`, `dnsConfig.nameservers`가 기본 제한을 초과했을 가능성 |
| 외부 DNS 직접 사용 | 클러스터 내부 DNS 대신 공용 DNS를 직접 사용하도록 구성되었을 가능성 |

현재 데이터만으로는 Prometheus Node Exporter 자체의 장애라고 보기는 어렵다. 이벤트를 생성한 주체는 Node Exporter가 아니라 `kubelet`이다. 실제 노드 resolver와 node-local-dns 상태를 확인하기 전에는 현재 `lemuel`의 DNS 문제로 확정하지 않는다.

### 영향 평가

직접적인 애플리케이션 장애 로그는 제공되지 않았으므로 서비스 장애를 확정할 수는 없다. 다만 nameserver가 일부 제거되면 다음 문제가 발생할 수 있다.

- 특정 외부 도메인 해석 실패
- 내부 도메인과 외부 도메인 간 해석 불일치
- DNS 응답 지연 또는 간헐적 연결 실패
- 이미지 Pull, Object Storage, Elasticsearch Endpoint 연결 오류
- 모니터링 대상 Endpoint scrape 실패

백업과 로깅이 외부 Endpoint 또는 별도 DNS 이름을 사용하는 구조라면 이 DNS 경고와의 연관성을 함께 확인해야 한다.

### 모니터링 영역 권고

1. 먼저 해당 이벤트가 현재도 재현되는지 확인한다. 과거 이벤트만으로 노드 설정을 변경하지 않는다.

```bash
cat /etc/resolv.conf
resolvectl status
```

2. 해당 Pod의 DNS 설정을 확인한다.

```bash
kubectl -n monitoring get pod kps-prometheus-node-exporter-2rrxl -o yaml
```

3. 클러스터 DNS와 외부 DNS를 분리하여 확인한다.

```bash
kubectl -n kube-system get pods
kubectl -n kube-system logs -l k8s-app=kube-dns
```

4. `node-local-dns` DaemonSet, Pod의 `/etc/resolv.conf`, CoreDNS Service(`10.43.0.10`), 실제 DNS 질의를 함께 확인한다.
5. VPN, NetworkManager, `systemd-resolved` 또는 K3s override를 변경하기 전에 현재 장애 Trace와 영향 범위를 확인한다.
6. nameserver를 무조건 공용 DNS로 고정하지 말고 클러스터의 node-local-dns 설계와 일치시키며, 현재 장애가 없으면 설정 변경을 하지 않는다.
7. 동일 이벤트가 반복 생성되지 않도록 Alertmanager에는 이벤트 횟수보다 실제 DNS 질의 실패율과 지연 시간을 주요 신호로 사용한다.

## 3. ELK 및 로깅: 안정성 점검

### 요약

| 항목 | 관측 결과 | 판정 |
|---|---|---|
| 확인된 로깅 컴포넌트 | Fluent Bit | 확인됨 |
| Namespace | `logging` | 확인됨 |
| 배포 방식 | DaemonSet | 노드별 로그 수집 구조 |
| Pod 생성 시각 | 2026-07-30 12:08:53 UTC | 확인됨 |
| Container 재시작 횟수 | 확인 불가 | `containerStatuses` 부재 |
| Ready 상태 | 확인 불가 | `status.conditions` 부재 |
| Elasticsearch 상태 | 확인 불가 | 관련 Pod·StatefulSet 데이터 부재 |
| Kibana 상태 | 확인 불가 | 관련 Pod·Deployment 데이터 부재 |
| Fluent Bit 오류 로그 | 확인 불가 | 컨테이너 로그 부재 |

확인된 Fluent Bit Pod는 다음과 같다.

```text
fluent-bit-8m9r6
```

해당 Pod는 `logging` Namespace의 `fluent-bit` DaemonSet에 의해 관리된다.

```text
owner: DaemonSet/fluent-bit
```

또한 다음 설정 체크섬 Annotation이 존재한다.

```text
checksum/config: ddfabf00c463bbcb42005ebd92e3e82b4d4e6b02eced1ca192bac2d2b4811ce2
```

이는 ConfigMap 또는 관련 설정 변경 시 Pod 재배포를 유도하는 Helm 계열 운영 패턴으로 보인다. 다만 이 정보만으로 실제 재시작이나 설정 변경 성공 여부를 판단할 수는 없다.

### 재시작 횟수 분석

현재 제공된 Fluent Bit Pod 데이터에는 다음 필드가 포함되어 있지 않다.

```yaml
status:
  phase:
  conditions:
  containerStatuses:
    restartCount:
    state:
```

따라서 Fluent Bit의 재시작 횟수, CrashLoopBackOff 여부, Ready 상태는 산출할 수 없다.

특히 Pod 생성 시각이 `2026-07-30T12:08:53Z`라는 사실만으로는 재시작 여부를 판단할 수 없다. 컨테이너 재시작은 같은 Pod 내부에서 일어날 수 있으며, Pod 생성 시각은 변경되지 않을 수 있기 때문이다.

### ELK 전체 안정성 판단의 한계

제공된 로깅 원시 데이터에는 Fluent Bit만 포함되어 있다. Elasticsearch와 Kibana에 대한 다음 정보가 누락되어 있다.

- Elasticsearch Pod 상태
- Elasticsearch StatefulSet Replica 상태
- Elasticsearch 노드별 클러스터 상태
- 디스크 사용량 및 watermark 초과 여부
- JVM heap pressure
- 인덱스 write 오류
- Kibana Pod 상태
- Fluent Bit의 Elasticsearch output 오류
- 로그 유실 또는 Backpressure 지표

따라서 현재 데이터만으로 “ELK가 안정적으로 운영되고 있다” 또는 “ELK에 장애가 발생했다”고 결론 내릴 수 없다.

### 로깅 영역 권고

다음 데이터를 추가 수집해야 안정성을 정량적으로 판단할 수 있다.

```bash
kubectl -n logging get pods -o wide
kubectl -n logging describe pod fluent-bit-8m9r6
kubectl -n logging logs fluent-bit-8m9r6 --since=168h
kubectl -n logging get daemonset fluent-bit -o yaml
```

Elasticsearch와 Kibana가 별도 Namespace에 있다면 다음 항목도 확인해야 한다.

```bash
kubectl get pods -A | grep -E 'elasticsearch|kibana|fluent-bit'
kubectl get statefulset -A
kubectl get events -A --sort-by=.lastTimestamp
```

운영 지표는 다음 기준으로 관리하는 것이 적절하다.

| 지표 | 권고 기준 |
|---|---|
| Fluent Bit Pod Ready 비율 | 100%에 근접하게 유지 |
| Fluent Bit 재시작 횟수 | 주간 증가 추세 감시 |
| Output 전송 오류 | 지속적인 오류 0건 목표 |
| Buffer 사용률 | 임계치 초과 여부 감시 |
| Elasticsearch disk watermark | high/flood-stage 도달 전 조치 |
| Elasticsearch cluster health | `green` 유지 |
| 로그 수집 지연 | 서비스별 SLO 설정 |
| 로그 유실 | 수집량과 저장량 대조 |

## 종합 운영 지표

| 영역 | 현재 판정 | 신뢰도 | 핵심 근거 |
|---|---|---|---|
| Velero/Kopia | 성공 여부 판정 불가 | 낮음 | Pod `status`와 Job 결과 부재 |
| 모니터링 | DNS 설정 경고 반복 확인 | 높음 | `DNSConfigForming` 3,452회 |
| Fluent Bit | DaemonSet 구성 확인, 안정성 판정 불가 | 낮음 | 재시작·Ready·로그 부재 |
| Elasticsearch/Kibana | 분석 불가 | 없음 | 관련 원시 데이터 부재 |

## 총평 및 다음 주 조치 권고

이번 데이터에서 확인된 것은 `2026-05-12`에 발생한 과거 `DNSConfigForming` 이벤트다. 현재 노드의 DNS 장애 또는 외부 저장소·로그 저장소·이미지 레지스트리 연결 실패로 확정할 수 없다. 후속 점검에서는 node-local-dns와 CoreDNS, 현재 Pod DNS 설정 및 실제 질의를 함께 검증해야 한다.

반면 Velero/Kopia와 ELK는 리소스 메타데이터 일부만 제공되어 성공률, 실패 원인, 재시작 횟수 등 핵심 SRE 지표를 계산할 수 없다. 현재 상태에서 “백업 성공” 또는 “로깅 시스템 안정”이라고 보고하는 것은 데이터 근거가 부족하다.

다음 주에는 아래 순서로 점검하는 것을 권고한다.

1. 과거 이벤트와 현재 이벤트를 분리하고, 현재 동일 경고 재현 여부를 확인한다.
2. 모든 Kubernetes 노드의 node-local-dns, Pod `/etc/resolv.conf`, CoreDNS Service와 실제 DNS 질의를 비교한다.
3. Velero Backup과 Kopia 유지보수 Job의 최근 1주 결과를 `status` 기준으로 재수집한다.
4. 실패 Job별 종료 코드, Pod 로그, Kubernetes Event를 연결해 원인을 분류한다.
5. Fluent Bit 전체 DaemonSet의 Ready 수, 재시작 수, 오류 로그, 출력 버퍼 상태를 수집한다.
6. Elasticsearch cluster health, 디스크 watermark, JVM pressure, 인덱스 오류를 별도로 점검한다.
7. 다음 주 리포트부터 백업 성공률과 로깅 안정성 지표를 동일한 UTC 기준으로 수집한다.
8. 원시 데이터 수집 시 `metadata`뿐 아니라 반드시 `status`, `events`, `logs`를 함께 저장한다.

최종적으로 이번 주의 운영 판정은 다음과 같다.

> DNS 구성 경고는 명확한 개선 대상이며, 백업과 ELK의 성공·안정성은 현재 제공된 원시 데이터만으로 확정할 수 없으므로 상태 필드와 로그를 보강한 재점검이 필요하다.