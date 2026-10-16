---
layout: post
title: "[Weekly Report] 2026년 42주차 클러스터 운영 리포트"
date: 2026-10-17 03:00:00 +0900
categories: [SRE, K8s]
---

# 2026년 42주차 클러스터 운영 리포트

- 분석 기간: 2026-10-10 ~ 2026-10-17
- 주간 재시작 델타: 증가 없음
- 분석 기준: 누적 카운터가 아니라 분석 기간 내 증가분과 이벤트를 우선
- 데이터 제약: `hermes-readonly` 서비스 계정의 Nodes 및 Velero CR 목록 권한이 없어 일부 항목은 관측 불가

## 1. 주간 클러스터 변경 이력 (Changes)

| 일자 | 구분 | 변경 또는 이벤트 | 판정 | 근거(Evidence) |
|---|---|---|---|---|
| 2026-09-27 | 클러스터 설정 | 전 노드 kubelet 예약 메모리 적용 및 관련 k3s-agent 재시작 | 사실 | 운영 변경 기록: `kubelet reserved memory`, `k3s-agent restart` |
| 2026-10-03 | 관측·접근성 | lemuel Opik 포트 노출 | 사실 | 변경 기록: `Opik port exposure`, `OPIK_BASE` 설정 |
| 2026-10-10 ~ 2026-10-17 | 재시작 | 주간 재시작 증가 없음 | PASS | 제공된 주간 재시작 델타: `증가 없음` |
| 2026-10-15 | 애플리케이션 배포 | LiteLLM, Nemotron, BuildKit, Immich 등 신규 파드 생성 및 Ready 전환 | 사실 | `metadata.creationTimestamp`, `status.phase=Running`, `conditions[type=Ready].status=True` |
| 2026-10-15 | 애플리케이션 배포 | FDC detector/replayer 및 기타 서비스 배포 | 사실 | `creationTimestamp=2026-10-15`, `status.phase=Running` |
| 2026-10-16 | 플랫폼 배포 | Plane 구성요소 및 Robot Simulator 파드 배포 | 사실 | `plane-*`, `robot-sim-*`, `creationTimestamp=2026-10-16` |
| 2026-10-16 | 모니터링 | watchman 파드가 새로 생성되었고 Startup Probe 초기 실패 후 Ready 전환 | 사실 | Event `reason=Unhealthy`, `Startup probe failed`, 이후 `conditions[type=Ready]=True` |
| 2026-10-16 | 백업 | ASAT, JEN, Lemuel-XR, SNS PostgreSQL dump Job이 성공 상태로 종료 | 백업 성공 관측 | `phase=Succeeded`, `exitCode=0`, `artifact_verified`, `remote_artifact_verified=true` |
| 2026-10-16 | Velero/Kopia | Velero 본체 및 Kopia 유지보수 Job에서 메모리 limit/request 비율 정책 위반 이벤트 발생 | WARN | Event `FailedCreate`, `memory max limit to request ratio per Container is 2`, `provided ratio is 4.000000` |
| 2026-10-10 ~ 2026-10-17 | 노드 관측 | louise에서 IO pressure 약 60% 관측 | WARN | 운영 관측값: `louise IO pressure ≈ 60%` |

9월 27일의 kubelet 예약 메모리 적용과 k3s-agent 재시작은 이번 분석 기간 이전의 변경이다. 따라서 이번 주 장애로 분류하지 않고, 현재 스냅샷과 기간 내 이벤트를 해석하기 위한 기준선으로 반영한다.

또한 10월 3일 lemuel의 Opik 포트 노출은 이번 주 이전에 적용된 변경이지만, `memory-qa` 및 관련 서비스의 외부 관측 경로에 영향을 줄 수 있는 운영 변경으로 기록한다.

## 2. 인프라 건강도 요약 (Summary Table)

| 항목 | 상태 | 이번 주 변화 | 복구 검증 | 근거(Evidence) |
|---|---|---|---|---|
| 컨테이너 재시작 델타 | PASS | 증가 없음 | 해당 없음 | 주간 재시작 델타 입력값: `증가 없음` |
| 누적 restartCount | 참고 | 여러 파드에 누적값 존재하나 이번 주 증가 여부와 분리 | 해당 없음 | `status.containerStatuses[].restartCount`, `lastState.terminated` |
| 노드 현재 상태 | WARN | 현재 Ready 스냅샷은 제공되었으나 Nodes API 직접 조회 불가 | 미검증 | API 오류: `nodes is forbidden`, 명령 의미: `kubectl get nodes` |
| 노드 기간 이벤트 | WARN | 9/27 전 노드 kubelet 예약 메모리 적용 및 k3s-agent 재시작 이력 존재 | 미검증 | 변경 기록: `kubelet reserved memory`, `k3s-agent restart` |
| louise IO | WARN | IO pressure 약 60% 관측 | 미검증 | 운영 관측값: `louise IO pressure ≈ 60%` |
| Velero Kubernetes 백업 | WARN | 백업 CR 목록 조회 실패 | 미검증 | `velero backups`, HTTP `403 Forbidden`, `cannot list resource "backups"` |
| Velero PodVolumeBackup | WARN | 볼륨 백업 목록 조회 실패 | 미검증 | `podvolumebackups.velero.io`, HTTP `403 Forbidden` |
| Kopia 유지보수 Job | WARN | Job 생성이 메모리 비율 정책으로 거부된 이벤트 확인 | 미검증 | Event `FailedCreate`, `memory max limit to request ratio`, `ratio is 4.000000` |
| PostgreSQL 파일 백업 | PASS | 일부 데이터베이스 dump 및 원격 업로드 성공 로그 확인 | 복구 미검증 | `phase=Succeeded`, `exitCode=0`, `artifact_verified`, `remote_artifact_verified=true` |
| ai-postgres 복구 | PASS | 복구 검증 완료 상태 | 검증됨 | 운영 기준: `ai-postgres restore verification` |
| 기타 데이터베이스 복구 | WARN | 백업 성공 증거는 있으나 리허설 증거 없음 | 복구 미검증 | 복구 명령, 복구 대상 DB 기동, 데이터 검증 로그 부재 |
| 모니터링 이벤트 | WARN | Startup Probe, DNSConfigForming, Velero FailedCreate 등 반복 이벤트 확인 | 부분 검증 | `kubectl get events --field-selector type=Warning`, `reason`, `message` |
| 주요 애플리케이션 Ready 상태 | PASS | 분석 시점 파드 다수가 Ready 상태 | 서비스별 별도 검증 필요 | `status.phase=Running`, `conditions[type=Ready].status=True` |

### 판정 원칙

이번 주 재시작 수치는 누적값이 아니라 주간 증가분으로 판정한다. 따라서 현재 일부 파드의 `restartCount`가 1 이상이거나 10 이상이어도, 이번 주 증가분이 없으면 재시작 지표는 PASS다.

다만 현재 스냅샷이 Ready라는 사실은 기간 전체에 재부팅이나 서비스 재시작이 없었다는 뜻이 아니다. 9월 27일 kubelet 예약 메모리 적용 및 전 노드 k3s-agent 재시작은 기간 이전의 변경 이벤트로 별도 기록해야 한다.

## 3. 섹션별 상세 분석

### 3.1 백업: Velero/Kopia

#### 3.1.1 Velero API 관측 한계

Velero 백업 리소스를 조회하려 했으나 `hermes-readonly` 서비스 계정에 필요한 RBAC 권한이 없다.

| 대상 | 결과 | 의미 | 근거(Evidence) |
|---|---|---|---|
| Velero Backup CR | 관측 불가 | 실제 백업 성공·실패 목록을 판정할 수 없음 | `backups.velero.io is forbidden`, `cannot list resource "backups"`, HTTP `403` |
| PodVolumeBackup CR | 관측 불가 | 파일시스템 볼륨 백업 상태를 판정할 수 없음 | `podvolumebackups.velero.io is forbidden`, `cannot list resource "podvolumebackups"`, HTTP `403` |
| Velero 서버 파드 | 현재 Running | 서버 프로세스가 실행 중이라는 사실만 확인 가능 | 파드 `velero-*`, `phase=Running`, `conditions[type=Ready]` |
| Velero Node Agent | 현재 Running | Node Agent 프로세스가 실행 중이라는 사실만 확인 가능 | 파드 `node-agent-*`, `phase=Running`, `restartCount` |

따라서 Velero와 Kopia에 대해서는 “백업이 정상적으로 수행되었다”고 단정하지 않는다. 현재 확보된 데이터는 Velero 구성요소의 실행 상태와 백업 CR 조회 권한 오류를 보여줄 뿐이다.

#### 3.1.2 Kopia 유지보수 실패 이벤트

분석 기간의 Warning Event에는 Kopia 유지보수 Job과 Velero Deployment에서 동일한 리소스 정책 위반이 기록되어 있다.

| 대상 | 상태 | 상세 | 근거(Evidence) |
|---|---|---|---|
| Kopia 유지보수 Job | WARN | 컨테이너 memory limit/request 비율이 정책상 허용값 2를 초과 | Event `reason=FailedCreate`, `memory max limit to request ratio per Container is 2`, `provided ratio is 4.000000` |
| Velero 파드 생성 | WARN | 동일한 메모리 비율 정책으로 ReplicaSet이 파드 생성을 거부 | Event `Error creating: pods "velero-..." is forbidden` |
| 원인 판정 | 사실 | Admission 또는 LimitRange 계열 정책이 파드 생성을 거부 | Event 키워드 `FailedCreate`, `forbidden`, `ratio is 4.000000` |
| 근본 원인 | 추정(Inference) | Velero/Kopia 리소스 정의와 네임스페이스의 limit/request 비율 정책이 불일치했을 가능성 | 직접적인 LimitRange 및 Deployment 원본 조회 증거 부족 |

#### 3.1.3 PostgreSQL dump 백업

Velero와 별도로 PostgreSQL dump 기반 백업 Job의 성공 흔적은 확인된다.

| 대상 | 백업 성공 | 원격 업로드 | 복구 검증 | 근거(Evidence) |
|---|---:|---:|---:|---|
| asat-prod | 확인 | 확인 | 복구 미검증 | `phase=Succeeded`, `pg_dump exitCode=0`, `artifact_verified`, `remote_artifact_verified=true` |
| jen-prod | 확인 | 확인 | 복구 미검증 | `phase=Succeeded`, `pg_dump exitCode=0`, `remote_artifact_verified=true` |
| lemuel-xr-prod | 확인 | 확인 | 복구 미검증 | `phase=Succeeded`, `artifact_verified`, `remote_artifact_verified=true` |
| sns-prod | 확인 | 확인 | 복구 미검증 | `phase=Succeeded`, `artifact_verified`, `remote_artifact_verified=true` |
| ai-postgres | 확인 | 확인 | 검증됨 | 운영 기준: `ai-postgres restore verification` |
| 기타 백업 대상 | 일부 확인 | 대상별 확인 필요 | 복구 미검증 | `pg_dump`, `rclone copy`, `rclone check` 로그 부재 또는 대상별 검증 자료 부족 |

백업 성공은 복구 가능성을 의미하지 않는다. 특히 현재 데이터에는 dump 파일 생성, gzip 무결성 검사, SHA-256 계산, 원격 저장소 `rclone check` 흔적은 있으나, 실제 별도 환경에서의 PostgreSQL 복원과 애플리케이션 수준 데이터 검증은 ai-postgres만 확인된 상태다.

### 3.2 모니터링: Warning Events

#### 3.2.1 분석 기간 내 주요 이벤트

| 시각 | 대상 | 이벤트 | 영향 판정 | 근거(Evidence) |
|---|---|---|---|---|
| 2026-10-16 17:48 UTC | `agent-system/watchman` | Startup Probe가 포트 연결 거부로 실패 | 일시적 초기화 지연 가능성 | `reason=Unhealthy`, `Startup probe failed`, `connect: connection refused`, `host=david` |
| 2026-10-16 이후 | `agent-system/watchman` | 이후 Ready 상태로 전환 | 현재 영향 해소 관측 | `conditions[type=Ready].status=True`, `startedAt`, `phase=Running` |
| 2026-10-15 ~ 2026-10-16 | `kube-system/node-local-dns` | Nameserver limits exceeded | WARN, DNS 설정 품질 점검 필요 | `reason=DNSConfigForming`, `Nameserver limits were exceeded` |
| 2026-10-16 | `velero` | Velero 파드 생성 거부 | 백업 구성요소 변경·복구 검증에 영향 가능 | `reason=FailedCreate`, `memory max limit to request ratio` |
| 2026-10-15 ~ 2026-10-16 | `velero` | Kopia 유지보수 Job 생성 반복 실패 | 저장소 유지보수 지연 가능성 | `argocd-default-kopia-...-maintain-job`, `count=1328`, `FailedCreate` |

#### 3.2.2 분석 기간 밖 또는 오래된 이벤트

Event 목록에는 2026년 5월에 생성된 `FailedScheduling` 이벤트가 함께 포함되어 있다. 이 이벤트들은 10월 10일~17일 분석 기간의 신규 장애로 분류하지 않는다.

| 대상 | 이벤트 | 판정 | 근거(Evidence) |
|---|---|---|---|
| `asat-prod/asat-postgres-0` | PV node affinity, taint, pod affinity 불일치 | 기간 밖 과거 이벤트 | `eventTime=2026-05-12`, `reason=FailedScheduling` |
| `crypto-prod/crypto-postgres-0` | 동일한 스케줄링 제약 | 기간 밖 과거 이벤트 | `eventTime=2026-05-12`, `reason=FailedScheduling` |
| `database-prod/database-mysql-0` | 동일한 스케줄링 제약 | 기간 밖 과거 이벤트 | `eventTime=2026-05-12`, `reason=FailedScheduling` |
| `kube-system/coredns` | Nameserver 제한 및 Service clusterIP 변경 불가 | 기간 밖 과거 이벤트 | `eventTime=2026-05-12`, `reason=DNSConfigForming`, `reason=ApplyManifestFailed` |

과거 이벤트가 현재 EventList에 남아 있다는 사실만으로 이번 주에 동일 문제가 재발했다고 판단하지 않는다. 기간 내 재발 여부는 `firstTimestamp`, `lastTimestamp`, `eventTime`, `count`를 함께 확인해야 한다.

### 3.3 자원 상태: Nodes / IO

#### 3.3.1 노드 상태

Nodes API는 읽기 권한 부족으로 직접 조회되지 않았다.

| 항목 | 상태 | 해석 | 근거(Evidence) |
|---|---|---|---|
| 현재 Node Ready 스냅샷 | 제한적 확인 | 제공된 파드의 `nodeName` 및 Ready 상태로 일부 배치 상태만 확인 가능 | 파드 `spec.nodeName`, `phase=Running`, `Ready=True` |
| 전체 Node 상태 | 미검증 | 모든 노드의 Ready/Pressure/Conditions를 직접 확인할 수 없음 | API 오류 `nodes is forbidden`, HTTP `403` |
| 기간 내 재부팅 | 변경 이력 존재 | 9/27 전 노드 kubelet 설정 변경 및 k3s-agent 재시작을 별도 이벤트로 기록 | 변경 기록 `kubelet reserved memory`, `k3s-agent restart` |
| 노드 가동률 100% | 사용하지 않음 | 현재 Ready 스냅샷과 기간 내 재부팅·서비스 재시작은 서로 다른 지표 | `kubectl get nodes`, `kubectl get events`, `systemctl status k3s-agent` 구분 필요 |

이번 주 보고서에서는 “노드 가동률 100%”라고 표현하지 않는다. 현재 Ready 여부는 스냅샷이고, 가동률은 기간 전체의 NotReady, 재부팅, kubelet 및 k3s-agent 서비스 중단 시간을 포함해 산출해야 하는 별도 지표다.

#### 3.3.2 louise IO pressure

louise 노드에서 약 60% 수준의 IO pressure가 관측되었다.

| 항목 | 상태 | 사실 | 추정(Inference) | 근거(Evidence) |
|---|---|---|---|---|
| louise IO pressure | WARN | IO 압력 약 60% 관측 | 디스크 지연이 해당 노드의 파드 응답 지연 또는 Probe 지연에 영향을 줄 가능성 | 운영 관측값 `louise IO pressure ≈ 60%` |
| 저장장치 영향 | 조사 필요 | 이번 데이터만으로 장애 발생을 확정할 수 없음 | Velero/Kopia 파일 백업, Elasticsearch, 로컬 볼륨 작업과 경합했을 가능성 | `iostat -xz`, `vmstat`, `kubectl top pod --containers` 추가 확인 필요 |
| 애플리케이션 영향 | 미확정 | watchman Startup Probe 실패는 david에서 발생 | louise IO와 watchman Probe 실패의 인과관계는 증거 부족 | Event `host=david`, `connect: connection refused` |

louise IO pressure 약 60%는 우선 관측 단계의 WARN이다. IO pressure 시점과 파드별 디스크 사용량, PVC 위치, 백업·로그 수집 작업 시간을 겹쳐 보지 않은 상태에서는 원인을 확정하지 않는다.

## 4. 사실과 추정의 분리

### 사실

- 주간 재시작 델타는 증가하지 않았다.
- 현재 파드 스냅샷에서 다수 파드가 `Running` 및 `Ready=True` 상태다.
- Nodes API와 Velero CR 목록 조회는 `403 Forbidden`으로 실패했다.
- 9월 27일 전 노드 kubelet 예약 메모리 적용 및 k3s-agent 재시작 이력이 있다.
- 10월 3일 lemuel Opik 포트 노출 이력이 있다.
- louise IO pressure 약 60%가 관측되었다.
- 10월 16일 watchman Startup Probe 실패 이벤트가 있었고 이후 Ready 상태로 전환되었다.
- Kopia 유지보수 Job과 Velero 파드 생성에서 메모리 limit/request 비율 위반 이벤트가 발생했다.
- 일부 PostgreSQL dump Job은 `exitCode=0`, `artifact_verified`, `remote_artifact_verified=true`로 종료되었다.
- ai-postgres만 복구 검증이 완료되었고, 나머지는 복구 미검증이다.

### 추정(Inference)

- Velero/Kopia 파드 생성 실패는 리소스 limit/request 비율 정책과 현재 리소스 정의가 불일치했기 때문일 가능성이 있다.
- louise의 IO pressure는 대용량 로그, Elasticsearch, PVC 기반 서비스 또는 백업 작업과의 디스크 경합으로 발생했을 가능성이 있다.
- watchman Startup Probe 실패는 프로세스 기동 지연 또는 포트 listen 시점과 Probe 시작 시점의 불일치일 가능성이 있다.
- DNSConfigForming 이벤트는 노드 또는 파드의 nameserver 설정이 Kubernetes의 nameserver 제한을 초과했기 때문일 가능성이 있다.
- 위 추정은 추가 로그와 시간대 상관관계 검증 전까지 원인 확정으로 사용하지 않는다.

## 5. 총평 및 차주 조치 권고 (Action Items)

### 조사 단계

| 우선순위 | 조치 | 목적 | 완료 기준 | 근거(Evidence) |
|---|---|---|---|---|
| P0 | Velero 및 PodVolumeBackup 조회용 최소 RBAC 검토 | 백업 CR의 실제 성공·실패 상태 확인 | `kubectl get backup -n velero`, `kubectl get podvolumebackup -n velero` 결과 확보 | 현재 `403 Forbidden`, `cannot list resource` |
| P0 | Velero/Kopia Deployment, Job, LimitRange 리소스 정의 대조 | 메모리 비율 위반 원인 확정 | `kubectl get deploy,job,limitrange -n velero -o yaml` 대조 완료 | `memory max limit to request ratio ... 4.000000` |
| P0 | ai-postgres 외 전체 데이터베이스 복구 리허설 수행 | 백업 성공과 복구 가능성 분리 검증 | 임시 복구 클러스터에서 DB 기동·스키마·핵심 조회 성공 | 현재 기준 `ai-postgres만 검증됨` |
| P1 | louise IO pressure 시간대와 파드/PVC/백업 작업 상관분석 | IO 병목 원인 파악 | `iostat -xz`, `vmstat`, `kubectl top`, PVC 사용량을 동일 시간축으로 비교 | 운영 관측값 `louise IO pressure ≈ 60%` |
| P1 | DNSConfigForming 이벤트의 노드별 resolv.conf 및 kubelet DNS 설정 확인 | DNS 설정 경고 제거 | `kubectl get events`, `cat /etc/resolv.conf`, kubelet DNS 설정 대조 | `reason=DNSConfigForming` |
| P1 | 9/27 kubelet 예약 메모리 적용 후 노드 Allocatable 변화 확인 | 설정 변경의 실제 효과 검증 | 변경 전후 `capacity`, `allocatable`, `system-reserved` 비교 | 변경 기록 `kubelet reserved memory` |
| P1 | 10월 16일 watchman Probe 실패 재현 여부 확인 | 일시적 기동 지연과 실제 장애 분리 | `kubectl describe pod`, 컨테이너 로그, Probe 성공 시각 비교 | `Startup probe failed`, 이후 `Ready=True` |

### 관측 단계

| 우선순위 | 조치 | 목적 | 완료 기준 | 근거(Evidence) |
|---|---|---|---|---|
| P1 | 주간 restart delta 수집을 별도 지표화 | 누적 restartCount 오판 방지 | 기준 시점과 종료 시점의 `restartCount` 차이를 자동 계산 | `containerStatuses[].restartCount` |
| P1 | 노드 상태와 기간 이벤트를 별도 리포트로 저장 | Snapshot과 Timeline 분리 | `kubectl get nodes -o yaml`, `kubectl get events --sort-by=.lastTimestamp` 저장 | 현재 Nodes API 권한 오류 및 9/27 변경 이력 |
| P1 | Backup Success와 Restore Verification을 별도 메트릭으로 관리 | 복구 미검증 상태의 가시화 | `backup_success`, `remote_artifact_verified`, `restore_verified`를 분리 기록 | `artifact_verified`, `remote_artifact_verified=true` |
| P2 | louise IO pressure 및 PVC latency 대시보드 추가 | IO 압력 추세 관측 | node-exporter 및 PVC 관련 패널에서 5분·1시간 추세 확인 | 운영 관측값 `IO pressure ≈ 60%` |
| P2 | Warning Event를 기간 필터와 namespace별로 집계 | 오래된 Event와 신규 Event 분리 | `eventTime` 또는 `lastTimestamp` 기준으로 분석 기간 필터 적용 | EventList에 2026년 5월 이벤트 혼재 |
| P2 | 9/27 및 10/3 변경을 Change Timeline에 고정 | 변경과 장애의 시간적 관계 보존 | kubelet 예약 메모리, k3s-agent, Opik 노출을 변경 이력에 유지 | 변경 기록 `kubelet`, `k3s-agent`, `Opik` |

### 유지 단계

| 우선순위 | 조치 | 목적 | 유지 기준 | 근거(Evidence) |
|---|---|---|---|---|
| P1 | 주간 재시작 델타가 0인 상태 유지 | 불필요한 재시작 방지 | 다음 주에도 증가분 기준 PASS 판정 | 주간 델타 `증가 없음` |
| P1 | ai-postgres 복구 검증 절차를 표준 템플릿화 | 검증된 복구 절차의 재사용 | 백업 대상별 동일한 restore receipt 생성 | `ai-postgres restore verification` |
| P2 | Velero/Kopia 리소스 정책 수정 후 반복 관측 | 백업 경로 안정화 | `FailedCreate` 및 ratio violation Event 재발 없음 | `reason=FailedCreate`, `ratio is 4.000000` |
| P2 | watchman Probe 성공 상태 유지 | 기동 지연 재발 방지 | Startup/Readiness Probe 실패율과 Ready 전환 시간 추적 | `Startup probe failed`, `Ready=True` |
| P2 | Opik 외부 노출 경로와 접근 로그 지속 점검 | 관측 엔드포인트 노출 위험 관리 | 접근 로그, 인증 정책, 필요 포트만 허용 | 변경 기록 `Opik port exposure` |

## 결론

이번 주 재시작 델타는 증가하지 않았으므로 재시작 건강도는 PASS로 판정한다. 다만 이는 누적 `restartCount`가 0이라는 뜻이 아니며, 9월 27일의 전 노드 kubelet 예약 메모리 적용 및 k3s-agent 재시작과 같은 기간 외 변경 이벤트도 현재 상태와 분리해 관리해야 한다.

가장 큰 운영 리스크는 백업 자체보다 복구 검증의 공백과 Velero/Kopia 조회·유지보수 경로의 불확실성이다. PostgreSQL dump와 원격 업로드 성공 증거는 일부 확보되었지만, ai-postgres를 제외한 대상은 모두 복구 미검증으로 유지한다.

차주의 우선순위는 다음과 같다.

1. Velero/Kopia 리소스 조회 권한과 메모리 정책 오류를 해소한다.
2. ai-postgres 외 백업 대상의 복구 리허설을 수행한다.
3. louise IO pressure 약 60%의 원인을 시간축 기반으로 조사한다.
4. 노드 현재 상태, 재부팅 이벤트, 서비스 재시작 이벤트를 별도 지표로 수집한다.
5. Warning Event에서 분석 기간 밖의 오래된 이벤트를 제거하거나 기간 필터링한다.
```