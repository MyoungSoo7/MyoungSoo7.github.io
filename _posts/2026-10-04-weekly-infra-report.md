---
layout: post
title: "[Weekly Report] 2026년 40주차 클러스터 운영 리포트"
categories: [SRE, K8s]
---

# [Weekly Report] 2026년 40주차 클러스터 운영 리포트

분석 기간: 2026-09-27 ~ 2026-10-04

이번 주 재시작 판정은 누적 재시작 횟수가 아니라 분석 기간 내 증가분(delta)을 기준으로 수행했다. 이번 주 재시작 delta는 증가 없음으로 확인되었으며, 누적 재시작 수치는 참고 지표로만 취급한다.

다만 기간 내 클러스터 전체 kubelet 예약 메모리 설정 적용과 k3s-agent 재시작 이벤트가 있었으므로, 현재 노드가 Ready라는 스냅샷과 기간 중 서비스 재시작 이력은 분리해서 해석해야 한다.

## 1. 주간 클러스터 변경 이력 (Changes)

| 일자 | 대상 | 변경 또는 이벤트 | 분류 | 영향 및 해석 | Evidence |
|---|---|---|---|---|---|
| 2026-09-27 이전 | 전체 노드 | kubelet 예약 메모리 설정 변경 적용 | 설정 변경 | 노드의 kubelet 시스템 예약 메모리 정책이 변경됨. 설정 적용 과정에서 서비스 재시작이 동반됨 | 사용자 제공 변경 기록: `kubelet 예약 메모리 적용` |
| 2026-09-27 | 전체 노드 | k3s-agent 재시작 | 노드 이벤트 | 기간 내 서비스 재시작 이벤트. 현재 Ready 여부와 별도로 기간 중 재시작 이력으로 기록해야 함 | 사용자 제공 변경 기록: `k3s-agent 재시작` |
| 2026-09-27 ~ 2026-10-04 | 전체 클러스터 | 재시작 delta 증가 없음 | 안정성 지표 | 이번 주에 추가로 증가한 컨테이너 또는 파드 재시작은 없음. 판정은 누적값이 아닌 주간 delta 기준 | 사용자 제공 주간 재시작 delta: `증가 없음` |
| 2026-09-27 ~ 2026-10-04 | louise 노드 | IO 압력 약 60% | 자원 이슈 | 즉시 장애로 단정할 수는 없으나, 디스크 지연·큐 증가·로그 또는 데이터 처리 집중 여부에 대한 관측이 필요함 | 사용자 제공 노드 분석: `louise IO 압력 약 60%` |
| 2026-10-03 | lemuel 노드 | Opik 포트 노출 | 네트워크 변경 | 외부 또는 클러스터 내부 노출 범위, NetworkPolicy, 인증 및 접근 로그 확인이 필요함 | 사용자 제공 변경 기록: `10/3 lemuel Opik 포트 노출` |

현재 제공된 원시 데이터에서는 Velero, Kopia, Warning Event, Nodes, Pods, Logging 조회가 모두 `Creds extraction failed`로 종료되었다. 따라서 위 변경 이력 중 사용자 제공 기록으로 확인된 항목과, 원시 명령 결과를 통해 직접 검증하지 못한 항목을 구분한다.

## 2. 인프라 건강도 요약

| 항목 | 상태 | 이번 주 변화 | 복구 검증 | 근거(Evidence) |
|---|---|---|---|---|
| 주간 재시작 delta | PASS | 증가 없음 | 해당 없음 | 주간 재시작 delta: `증가 없음`; 판정 기준: 분석 기간 내 증가분 |
| 누적 재시작 수 | 참고 | 누적값은 주간 판정에 사용하지 않음 | 해당 없음 | 재시작 판정 규칙: `누적 수치가 아닌 주간 delta 기준` |
| 노드 현재 상태 | PASS | 현재 Ready 스냅샷 확인 기준 | 해당 없음 | 노드 상태 기준: `현재 Ready`; 단, 원시 `nodes` 조회 결과는 `Creds extraction failed` |
| 기간 내 노드 가용성 | WARN | 9/27 kubelet 예약 메모리 적용 및 k3s-agent 재시작 | 해당 없음 | 이벤트 키워드: `kubelet 예약 메모리`, `k3s-agent 재시작` |
| kubelet 예약 메모리 설정 | PASS | 9/27 클러스터 전체 적용 | 해당 없음 | 설정 변경 기록: `kubelet 예약 메모리 적용` |
| Velero 백업 성공 | WARN | 백업 성공 여부를 원시 조회 결과로 검증하지 못함 | 복구 미검증 | 조회 결과: `velero backups` → `Creds extraction failed` |
| Velero 파드 볼륨 백업 | WARN | 볼륨 백업 상태를 검증하지 못함 | 복구 미검증 | 조회 결과: `velero pod volume backups` → `Creds extraction failed` |
| Kopia 백업 | WARN | 백업 및 스냅샷 상태를 검증하지 못함 | 복구 미검증 | Kopia 상태·스냅샷·복구 리허설 로그 미확인; 백업 조회 인증 실패 |
| ai-postgres 복구 | PASS | 복구 검증 완료 상태로 취급 | 검증됨 | 사용자 제공 기준: `현재 ai-postgres만 검증됨` |
| 모니터링 Warning Event | WARN | 최근 7일 Warning Event 원시 조회 실패 | 해당 없음 | 조회 결과: `warning events - last 7 days` → `Creds extraction failed` |
| louise IO 압력 | WARN | 약 60% 수준 관측 | 해당 없음 | 노드 자원 기록: `louise IO 압력 약 60%` |
| lemuel Opik 포트 노출 | WARN | 10/3 포트 노출 변경 | 해당 없음 | 변경 기록: `10/3 lemuel Opik 포트 노출` |
| 전체 파드 상태 | WARN | 파드별 상태 및 재시작 세부값 검증 실패 | 해당 없음 | 조회 결과: `all pods` → `Creds extraction failed` |
| 클러스터 로그 | WARN | 기간 내 로그 기반 원인 분석 불가 | 해당 없음 | Logging 조회 결과: `Creds extraction failed` |

### 판정 기준

- `PASS`: 이번 주 delta 기준으로 재시작 증가가 없거나, 사용자 제공 근거상 정상으로 확인된 항목
- `WARN`: 장애로 단정할 수는 없지만 설정 변경, 서비스 재시작, 자원 압력, 외부 노출 또는 검증 공백이 존재하는 항목
- `복구 미검증`: 백업 성공 여부와 별개로 실제 복구 리허설 또는 복구 결과가 확인되지 않은 상태
- 현재 노드가 `Ready`라는 사실만으로 분석 기간 전체의 가동률 100%를 의미하지 않는다.

## 3. 섹션별 상세 분석

### 3.1 백업: Velero / Kopia

백업 상태는 다음 세 가지를 분리해서 판단해야 한다.

1. 백업 작업이 성공했는가
2. 백업 산출물이 정상적으로 보존되었는가
3. 실제 복구가 가능한지 검증했는가

이번 원시 데이터에서는 Velero 백업 목록과 파드 볼륨 백업 목록 조회 모두 인증 정보 추출 실패로 완료되지 않았다. 따라서 백업 성공 여부를 직접 PASS로 판정할 수 없다.

또한 백업 성공은 복구 검증을 의미하지 않는다. 현재 제공된 정보 기준으로 복구 검증이 완료된 항목은 `ai-postgres`뿐이며, 나머지 항목은 `복구 미검증`으로 기록한다.

| 백업 대상 | 백업 성공 여부 | 복구 검증 | 상태 | 분석 |
|---|---|---|---|---|
| Velero 일반 백업 | 확인 불가 | 복구 미검증 | WARN | 백업 목록 조회가 인증 실패로 종료되어 실제 성공·실패 건수 확인 불가 |
| Velero 파드 볼륨 백업 | 확인 불가 | 복구 미검증 | WARN | 파드 볼륨 백업 목록과 최신 완료 시각을 확인하지 못함 |
| Kopia 스냅샷 | 확인 불가 | 복구 미검증 | WARN | Kopia 스냅샷, 저장소 무결성, 최근 성공 작업을 확인할 수 있는 원시 증거 부족 |
| ai-postgres | 성공 여부의 상세 로그 미제공 | 검증됨 | PASS | 사용자 제공 기준상 현재 복구 검증이 완료된 유일한 항목 |
| 기타 애플리케이션 데이터 | 확인 불가 | 복구 미검증 | WARN | 실제 복구 리허설 증거가 제공되지 않음 |
| 확인 항목 | 필요한 검증 | 복구 검증 기준 | 근거(Evidence) |
|---|---|---|---|
| Velero 백업 완료 | `velero backup get`, `velero backup describe <backup> --details` | `Completed`, 오류 및 경고 없음 | 현재 조회 결과: `velero backups` → `Creds extraction failed` |
| 볼륨 백업 완료 | `velero backup describe <backup> --details`, 볼륨 백업 상태 확인 | 대상 PVC와 볼륨 데이터가 백업 대상에 포함됨 | 현재 조회 결과: `velero pod volume backups` → `Creds extraction failed` |
| Kopia 저장소 상태 | `kopia snapshot list`, 저장소 무결성 및 최신 스냅샷 확인 | 최신 스냅샷 존재 및 무결성 검사 통과 | Kopia 원시 조회 로그 미제공 |
| 실제 복구 | 별도 namespace 또는 격리된 복구 환경에서 restore 수행 | 애플리케이션 기동, 데이터 조회, 체크섬 또는 샘플 데이터 일치 | 사용자 제공 기준: `ai-postgres만 검증됨` |

#### 사실과 추정

- 사실(Fact): Velero 관련 조회는 `Creds extraction failed`로 완료되지 않았다.
- 사실(Fact): 현재 복구 검증이 완료된 대상은 `ai-postgres`이다.
- 사실(Fact): 나머지 백업 대상은 복구 미검증 상태다.
- 추정(Inference): 인증 정보 추출 실패가 지속되면 실제 백업 실패가 아니라도 운영자는 백업 성공 여부를 확인할 수 없으므로 백업 관측 공백이 발생한다.
- 확인 필요: 인증 오류의 원인이 만료된 자격 증명인지, 권한 부족인지, 실행 환경의 secret 접근 실패인지 로그로 분리해야 한다.

### 3.2 모니터링: Warning Events

최근 7일간 Warning Event 원시 조회도 `Creds extraction failed`로 종료되었다. 따라서 이벤트가 없었다고 판단해서는 안 되며, `조회 실패`와 `Warning Event 없음`을 구분해야 한다.

| 분석 항목 | 현재 판정 | 사실(Fact) | 추정(Inference) | 근거(Evidence) |
|---|---|---|---|---|
| 최근 7일 Warning Event | WARN | 이벤트 목록을 확보하지 못함 | 인증 실패로 인해 실제 Warning Event가 관측되지 않았을 가능성 | `warning events - last 7 days` → `Creds extraction failed` |
| 재시작 관련 이벤트 | 확인 불가 | 이벤트 상세를 확인하지 못함 | 9/27 서비스 재시작이 Warning 또는 Normal Event에 기록되었을 수 있음 | `kubectl get events --all-namespaces --sort-by=.lastTimestamp` 필요 |
| 노드 압력 이벤트 | 확인 불가 | MemoryPressure, DiskPressure, PIDPressure 여부 미확인 | louise IO 압력이 노드 이벤트 또는 kubelet 경고로 이어졌을 가능성 | `kubectl describe node louise`, 이벤트의 `Pressure` 키워드 필요 |
| Opik 포트 노출 관련 이벤트 | 확인 불가 | 네트워크 정책 변경 이벤트 미확인 | 서비스 노출 이후 비인가 접근 또는 정책 누락 위험이 있을 수 있음 | `10/3 lemuel Opik 포트 노출`; NetworkPolicy 및 접근 로그 필요 |

Warning Event 분석에서 우선 확인해야 할 키워드는 다음과 같다.

- `Failed`
- `BackOff`
- `Unhealthy`
- `FailedMount`
- `FailedAttachVolume`
- `Evicted`
- `NodeNotReady`
- `MemoryPressure`
- `DiskPressure`
- `NetworkUnavailable`
- `FailedScheduling`

현재 이벤트 조회가 복구되지 않은 상태에서는 “이번 주 경고 이벤트가 없었다”는 결론을 내릴 수 없다.

### 3.3 자원 상태: Nodes / IO

현재 노드 상태가 Ready라는 것은 조회 시점의 상태 스냅샷이다. 이를 분석 기간 전체의 가동률 100%로 확장해서 표현하지 않는다.

이번 주에는 9/27 클러스터 전체 kubelet 예약 메모리 설정 적용과 k3s-agent 재시작이 있었으므로, 노드의 현재 상태와 기간 내 운영 이벤트를 다음과 같이 분리한다.

| 대상 | 현재 스냅샷 | 기간 내 이벤트 | 상태 | 분석 | 근거(Evidence) |
|---|---|---|---|---|---|
| 전체 노드 | 현재 Ready 기준 | 9/27 kubelet 예약 메모리 적용 및 k3s-agent 재시작 | WARN | 현재 Ready이지만 기간 내 서비스 재시작이 존재하므로 100% 가동률로 표현하지 않음 | `현재 Ready`, `kubelet 예약 메모리`, `k3s-agent 재시작` |
| kubelet 예약 메모리 | 설정 적용 상태 | 9/27 클러스터 전체 적용 | PASS | 시스템 및 kubelet 예약 영역을 명시적으로 반영한 변경. 적용 후 메모리 여유와 eviction 동작 확인 필요 | 변경 기록: `클러스터 전체 kubelet 예약 메모리 적용` |
| louise | IO 압력 약 60% | 기간 중 지속 여부 미확인 | WARN | 단일 시점 관측인지 지속 압력인지 구분 필요. 디스크 latency와 I/O wait를 함께 확인해야 함 | 자원 기록: `louise IO 압력 약 60%` |
| lemuel | 현재 상태 상세 확인 불가 | 10/3 Opik 포트 노출 | WARN | 네트워크 노출 변경과 노드 건강 상태를 별도로 확인해야 함 | 변경 기록: `10/3 lemuel Opik 포트 노출` |
| 전체 파드 | 상태 및 세부 재시작 정보 확인 불가 | 주간 재시작 delta는 증가 없음 | PASS/WARN | 재시작 delta는 PASS이나 파드별 Ready, Pending, CrashLoopBackOff 상태는 조회 실패로 별도 WARN | `all pods` → `Creds extraction failed`; 주간 delta `증가 없음` |

louise의 IO 압력 약 60%는 즉시 장애를 의미하지 않는다. 다만 다음 지표가 함께 증가하면 실제 서비스 영향 가능성이 높아진다.

- 디스크 사용률 및 inode 사용률
- 디스크 read/write latency
- I/O wait
- 디바이스 queue depth
- kubelet 및 container runtime의 응답 지연
- PVC 또는 데이터베이스의 flush 지연
- `DiskPressure` 이벤트
- 애플리케이션의 timeout 및 retry 증가

#### 사실과 추정

- 사실(Fact): louise에서 IO 압력 약 60%가 관측되었다.
- 사실(Fact): 9/27 클러스터 전체 kubelet 예약 메모리 적용과 k3s-agent 재시작 이벤트가 있었다.
- 사실(Fact): 현재 노드 상태는 Ready 스냅샷 기준이다.
- 추정(Inference): louise의 IO 압력이 지속될 경우 로그 증가, 데이터베이스 I/O, 백업 작업 또는 특정 워크로드 집중이 원인일 수 있다.
- 확인 필요: IO 압력의 측정 기준과 관측 시각, 지속 시간, 실제 디바이스 latency를 확인해야 한다.

## 4. 총평 및 차주 조치 권고 (Action Items)

이번 주 재시작 delta는 증가하지 않아 재시작 증가 기준으로는 PASS다. 그러나 9/27 전체 노드의 kubelet 예약 메모리 설정 적용과 k3s-agent 재시작이 있었으므로, 현재 Ready 상태만으로 기간 전체의 가동률 100%를 주장해서는 안 된다.

백업 영역은 백업 성공과 복구 검증을 분리해야 한다. 현재 복구 검증이 확인된 대상은 `ai-postgres`뿐이며, 나머지는 `복구 미검증`이다. Velero, Kopia, Warning Event, Nodes, Pods, Logging 원시 조회가 모두 인증 정보 추출 실패로 중단되었기 때문에, 다음 주에는 기능 장애보다 먼저 관측 경로와 자격 증명 문제를 복구해야 한다.

| 단계 | 우선순위 | 조치 | 완료 기준 | Evidence |
|---|---:|---|---|---|
| 조사 | P0 | `Creds extraction failed` 원인 분석 | secret 접근, 토큰 만료, RBAC 권한, 실행 주체를 구분하고 Velero·Kubernetes API 조회 성공 | 실패 문자열: `Creds extraction failed` |
| 조사 | P0 | Velero 백업 목록과 최근 실패 작업 재조회 | 최근 7일 백업의 `Completed`, `PartiallyFailed`, `Failed` 상태와 오류 확인 | `velero backup get`, `velero backup describe --details` |
| 조사 | P0 | Warning Event 최근 7일 재조회 | `Failed`, `BackOff`, `Unhealthy`, `Pressure`, `Evicted` 이벤트를 namespace·노드별로 분류 | `kubectl get events --all-namespaces --sort-by=.lastTimestamp` |
| 조사 | P1 | louise IO 압력 원인 확인 | 관측 시각, 지속 시간, latency, iowait, queue, DiskPressure를 상관 분석 | `kubectl describe node louise`, 노드 I/O 지표 및 kubelet 로그 |
| 조사 | P1 | lemuel Opik 포트 노출 검토 | Service, Ingress, NodePort, LoadBalancer, NetworkPolicy, 인증 및 접근 로그 확인 | `10/3 lemuel Opik 포트 노출`, Service·NetworkPolicy 조회 |
| 관측 | P0 | 주간 재시작 delta 자동 수집 | 누적 restartCount와 주간 delta를 분리 표시하고 delta 기준으로 PASS/WARN 판정 | `kubectl get pods -A -o json`, 기간 시작·종료 시점 비교 |
| 관측 | P1 | kubelet 예약 메모리 적용 후 메모리 여유 모니터링 | allocatable 변화, MemoryPressure, eviction, OOMKilled를 전후 비교 | kubelet 설정, `kubectl describe node`, `MemoryPressure`, `OOMKilled` |
| 관측 | P1 | Velero/Kopia 백업 성공과 복구 검증 대시보드 분리 | `backup_success`와 `restore_verified`를 별도 상태로 표시 | Velero/Kopia 작업 로그 및 복구 리허설 결과 |
| 관측 | P1 | 노드 이벤트와 서비스 재시작 이력 통합 | Ready 스냅샷, NotReady 구간, k3s-agent 재시작 시각을 별도 표시 | `k3s-agent 재시작`, Node condition 및 systemd/journal 로그 |
| 유지 | P1 | ai-postgres 복구 검증 절차 유지 | 정기 복구 리허설과 데이터 검증 결과 보관 | 현재 검증 완료 항목: `ai-postgres` |
| 유지 | P1 | 기타 백업 대상 복구 리허설 수행 | 각 대상별 복구 namespace, 애플리케이션 기동, 샘플 데이터 검증 완료 | 현재 상태: 기타 대상 `복구 미검증` |
| 유지 | P2 | Opik 노출 정책 문서화 및 최소 권한 유지 | 허용 출발지, 인증 방식, TLS, NetworkPolicy, 접근 로그 보존 기간 명시 | `10/3 lemuel Opik 포트 노출` |
| 유지 | P2 | 주간 운영 리포트의 Evidence 표준화 | 모든 표에 실행 명령어, 로그 키워드, 조회 시각을 포함 | 리포트 규칙: 모든 분석 표에 `근거(Evidence)` 열 포함 |

다음 주의 핵심 목표는 다음 세 가지다.

1. 인증 정보 추출 실패를 해결해 클러스터 원시 데이터를 다시 확보한다.
2. 백업 성공과 복구 검증을 별도 지표로 운영한다.
3. louise IO 압력과 lemuel Opik 포트 노출에 대한 지속 관측 및 보안 검증을 완료한다.