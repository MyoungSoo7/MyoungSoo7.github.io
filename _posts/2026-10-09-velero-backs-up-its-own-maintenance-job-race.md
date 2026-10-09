---
layout: post
title: "Velero 가 자기 유지보수 Job 을 백업하다 지는 경주 — PartiallyFailed 2건이 'Stale' 경보가 되기까지"
date: 2026-10-09 17:14:02 +0900
categories: [sre, kubernetes, postmortem]
tags: [kubernetes, velero, kopia, backup, race-condition, toctou, prometheus, postmortem]
---

오후에 텔레그램으로 경보가 하나 왔다.

```
🔔 [VeleroDailyBackupStale] velero/velero-...
근거1: velero_backup_last_successful_timestamp 95459초 경과 (임계 93600초 = 26시간)
근거2: 최신 백업 daily-with-volumes-20261009030052 = PartiallyFailed, errors=2
```

"하루 넘게 백업이 성공하지 못했다"는 말은 무섭게 들린다. 결론부터 말하면 **앱 데이터는 하나도 빠지지 않았다.** 에러 2건은 모두 Velero 가 *자기 자신이 띄운 유지보수 Job 파드*를 백업하려다 난 것이고, 원인은 "확인한 시점"과 "사용한 시점" 사이에 상태가 바뀌는 전형적인 TOCTOU 경주다.

## 1. 에러 2건의 정체

이 클러스터엔 `velero` CLI 가 없어서, `DownloadRequest` CR(`target.kind: BackupResults`)로 결과 파일을 받았다. 에러는 정확히 두 줄이다.

```
pod volume backup failed: error to expose PVB: error to get pod volume path:
error identifying unique volume path on host for volume plugins in pod
lemuel-xr-prod-default-kopia-nglq5-maintain-job-...:
expected one matching path: /host_pods/<pod-uid>/volumes/*/plugins, got 0
```

나머지 한 줄은 같은 파드의 `scratch` 볼륨이다. 대상 파드가 앱 파드가 아니라 **`velero` 네임스페이스에 있는 kopia 저장소 유지보수 Job 파드**다.

v1.14 부터 Velero 는 저장소 유지보수(kopia maintenance)를 서버 프로세스 안에서 돌리지 않고, Velero 설치 네임스페이스에 **별도 Kubernetes Job 을 띄워** 수행한다. kopia 의 기본 유지보수 주기는 1시간이다 ([Velero Docs — Repository Maintenance](https://velero.io/docs/v1.18/repository-maintenance/)). 그리고 Velero 는 네임스페이스마다 저장소를 하나씩 만든다 ([Velero Docs — File System Backup](https://velero.io/docs/v1.18/file-system-backup/)). 이 클러스터에는 BackupRepository 가 46개 있으니, 유지보수 Job 이 한 시간 동안 46번 뜬다.

## 2. 로그로 재구성한 71초

백업 로그(`BackupLog`)를 같은 방법으로 받아 해당 파드만 추렸다.

| 시각 (UTC) | 일어난 일 |
| --- | --- |
| 03:00:52 | `daily-with-volumes` 백업 시작. `includedNamespaces: ["*"]` 라 `velero` 네임스페이스도 포함된다 |
| 03:14:44 | 유지보수 Job 파드를 처리하면서 *"Perform fs-backup action for volume plugins … due to opt-in/out way"* 를 남긴다. 이 시점에 파드는 Running 이었다 |
| 03:15:55 | 노드에서 볼륨 경로를 찾지만 0개가 나온다. 그 사이에 Job 이 끝나 emptyDir 디렉터리가 정리됐기 때문이다 |

이 스케줄은 `defaultVolumesToFsBackup: true`, 즉 opt-out 방식이다. opt-out 에서는 서비스어카운트 토큰·Secret·ConfigMap·hostPath 를 뺀 **모든 파드 볼륨**이 파일시스템 백업 대상이 된다 ([Velero Docs — File System Backup, "Using the opt-out approach"](https://velero.io/docs/v1.18/file-system-backup/)). 유지보수 파드의 emptyDir 두 개(`plugins`, `scratch`)도 예외가 아니다.

## 3. 소스로 확인한 경주 구간 (v1.18.1)

추측으로 끝내지 않으려고 운영 중인 버전(v1.18.1) 태그의 소스를 직접 읽었다.

**확인(Check).** `pkg/podvolume/backupper.go` 의 `BackupPodVolumes` 는 파드가 Running 이 아니면 그 파드의 볼륨을 전부 *건너뛰고 에러 없이* 반환한다.

```go
if err := kube.IsPodRunning(pod); err != nil {
    skipAllPodVolumes(pod, volumesToBackup, err, pvcSummary, log)
    return nil, pvcSummary, nil
}
```

이미 끝난(Succeeded) 유지보수 파드들은 여기서 걸러져 **경고**로만 남는다. 이날 백업의 경고 98건 중 92건이 바로 이것이다. 유지보수 파드 46개 × emptyDir 2개다.

**사용(Use).** 확인을 통과한 뒤 실제 백업을 위해 PodVolumeBackup 을 "노출(expose)"하는 단계에서, `pkg/exposer/pod_volume.go` 가 노드의 볼륨 경로를 찾는다.

```go
path, err := getPodVolumeHostPath(ctx, pod, param.ClientPodVolume, e.kubeClient, e.fs, e.log)
if err != nil {
    return errors.Wrapf(err, "error to get pod volume path")
}
```

경로 탐색은 `pkg/util/kube/utils.go` 의 `SinglePathMatch` 가 glob 으로 하며, 결과가 정확히 1개가 아니면 실패한다.

```go
if len(matches) != 1 {
    return "", errors.Errorf("expected one matching path: %s, got %d", path, len(matches))
}
```

두 단계 사이에 파드가 끝나면 확인은 통과했는데 경로는 사라진 상태가 된다. 이때는 경고가 아니라 **에러**로 집계되고, 백업 전체가 `PartiallyFailed` 가 된다. 파드가 확인 시점에 이미 끝나 있었으면 경고, 아직 돌고 있었으면 에러다. 같은 파드라도 백업이 몇 초 늦거나 빨랐느냐에 따라 결과가 갈린다.

## 4. 왜 "Stale" 경보가 됐나

경보의 근거인 `velero_backup_last_successful_timestamp` 는 `pkg/controller/backup_controller.go` 의 `getLastSuccessBySchedule` 에서 계산한다.

```go
for _, backup := range backups {
    if backup.Status.Phase != velerov1api.BackupPhaseCompleted {
        continue
    }
    ...
}
```

`Completed` 가 아니면 건너뛴다. `PartiallyFailed` 는 실패로도 성공으로도 세지지 않고, 그냥 *없었던 일*이 된다. 그래서 일일 스케줄에서 하루라도 PartiallyFailed 가 나오면 "마지막 성공"은 그 전날에 멈추고, 26시간 임계가 지나는 순간 Stale 경보가 뜬다. 처음 받은 경보와 원인은 같은 사건이고, Stale 은 그 하류 증상일 뿐이다. 다음 일일 백업이 Completed 로 끝나면 지표가 따라 올라가고 경보도 스스로 풀린다.

## 5. 우연이 아니라 반복이었다

최근 20일의 `daily-with-volumes` 를 보면, `errors=2` 로 PartiallyFailed 가 된 날이 **5번**(9/25, 9/26, 9/27, 10/1, 10/9)이다. 네 날의 결과 파일을 모두 받아 보니 시그니처가 같았다. 날마다 다른 저장소의 유지보수 파드가, 같은 `plugins`·`scratch` 두 볼륨에서 `got 0` 으로 실패했다. 걸린 저장소는 registry-mirror, arc-system, logistic, grid, lemuel-xr 였다. (10/2 의 53건은 시그니처가 다른 별건이라 이 글에서는 제외한다.)

4분의 1 확률로 매일 이 경주에 지고 있었던 셈이다. 저장소가 늘수록 유지보수 Job 도 늘어나니 더 자주 질 것이다.

## 6. 고치는 방법 — 후보 셋과 트레이드오프

유지보수 파드의 emptyDir 은 kopia 가 작업 중에 쓰는 임시 공간이다. 백업할 가치가 없다. 문제는 *어떻게 빼느냐*다. 아래는 아직 적용하지 않은 후보이며, 백업 범위를 바꾸는 일이라 적용 여부는 운영자가 결정한다.

1. **`velero` 네임스페이스를 통째로 제외** (`excludedNamespaces`). 가장 단순하다. 하지만 그 네임스페이스에는 kopia 저장소 비밀번호가 든 `velero-repo-credentials` Secret 이 있다 ([File System Backup 문서의 "Note"](https://velero.io/docs/v1.18/file-system-backup/)). 클러스터를 통째로 잃었을 때 리소스 백업에서 그걸 꺼낼 길이 사라진다. 비용이 가장 크다.
2. **라벨 셀렉터로 유지보수 파드만 제외.** 이 클러스터에서 실측해 보니 유지보수 Job 파드에는 `velero.io/repo-name` 라벨이 붙어 있다. 스케줄 템플릿에 `labelSelector` 로 `velero.io/repo-name DoesNotExist` 를 주면 라벨이 없는 나머지 리소스는 그대로 포함된다. Velero 는 "셀렉터에 맞지 않는 것 포함"을 셀렉터 문법으로 지원한다 ([Velero Docs — Resource filtering, `--selector`](https://velero.io/docs/v1.18/resource-filtering/)). 다만 셀렉터는 *모든* 리소스에 적용되므로, 범위를 바꾸기 전에 일회성 백업으로 포함 항목 수를 비교해 검증해야 한다.
3. **볼륨 정책으로 emptyDir 전체를 건너뛰기** (resource policy 의 `volumePolicies`). 유지보수 파드뿐 아니라 클러스터의 모든 emptyDir 이 빠진다. emptyDir 은 원래 파드와 수명을 같이하는 임시 볼륨이지만, 그 안에 뭔가를 기대하는 앱이 있는지 먼저 확인해야 하는 범위 변경이다.

개인적으로는 2번을 추천한다. 빠지는 것이 정확히 "유지보수 Job 과 그 파드"뿐이라 손실이 0이고, 경고 92건도 같이 사라져 진짜 경고가 묻히지 않는다.

> **근거의 한계.** Velero 업스트림 이슈 트래커에서 *"expected one matching path"* 와 *"maintenance job pod volume backup"* 으로 검색해 봤지만, 이 경주(유지보수 Job 파드가 Running 확인과 경로 탐색 사이에 종료)를 직접 다룬 이슈는 찾지 못했다. 비슷한 메시지의 이슈들(예: [#6749](https://github.com/velero-io/velero/issues/6749), [#8290](https://github.com/velero-io/velero/issues/8290))은 복원 쪽이나 다른 원인을 다룬다. 위 분석은 이 클러스터의 로그와 v1.18.1 소스를 대조한 결과다.

## 정리

- 경보 두 개(PartiallyFailed, Stale)는 **사건 하나**다. Stale 은 "마지막 성공" 지표가 PartiallyFailed 를 건너뛰어서 생긴 하류 증상이다.
- 에러는 Velero 가 **자기 유지보수 Job 의 임시 볼륨**을 백업하려다 Job 종료와 겹쳐 진 경주다. Running 확인과 경로 탐색 사이의 TOCTOU 다.
- 앱 볼륨은 빠지지 않았다. 하지만 이대로 두면 4~5일에 한 번씩 "백업 실패" 경보가 울리고, 사람은 결국 그 경보를 무시하게 된다. 그때 진짜 실패가 섞이면 놓친다. 고칠 이유는 데이터가 아니라 경보의 신뢰도다.

## References

- Velero Docs (v1.18) — [Repository Maintenance](https://velero.io/docs/v1.18/repository-maintenance/): 유지보수 Job 분리(v1.14+), kopia 기본 주기 1시간, ConfigMap 설정
- Velero Docs (v1.18) — [File System Backup](https://velero.io/docs/v1.18/file-system-backup/): opt-in/opt-out 방식, 네임스페이스별 저장소, `velero-repo-credentials`
- Velero Docs (v1.18) — [Resource filtering](https://velero.io/docs/v1.18/resource-filtering/): 네임스페이스 제외, 라벨 셀렉터, `velero.io/exclude-from-backup`, resource policies
- Velero 소스 v1.18.1 — [`pkg/podvolume/backupper.go`](https://github.com/velero-io/velero/blob/v1.18.1/pkg/podvolume/backupper.go) (`IsPodRunning` 확인), [`pkg/exposer/pod_volume.go`](https://github.com/velero-io/velero/blob/v1.18.1/pkg/exposer/pod_volume.go) (경로 탐색), [`pkg/util/kube/utils.go`](https://github.com/velero-io/velero/blob/v1.18.1/pkg/util/kube/utils.go) (`SinglePathMatch`), [`pkg/controller/backup_controller.go`](https://github.com/velero-io/velero/blob/v1.18.1/pkg/controller/backup_controller.go) (`getLastSuccessBySchedule`)
- Velero Issues — [#6749](https://github.com/velero-io/velero/issues/6749), [#8290](https://github.com/velero-io/velero/issues/8290) (유사 메시지, 다른 원인)
