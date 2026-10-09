---
layout: post
title: "백업이 자기 청소부를 백업하려다 실패했다 — Velero 'PartiallyFailed' 의 범인은 kopia 정리 잡이었다"
date: 2026-10-09 17:30:00 +0900
categories: [devops]
tags: [velero, kopia, kubernetes, backup, k3s, homelab, troubleshooting]
---

오늘 우리 k3s 클러스터의 매일 백업이 `PartiallyFailed`(일부 실패)로 끝났다. 처음엔 다른 노드의 문제로 의심했다.
그런데 실패 기록을 열어 보니 실패한 대상은 앱이 아니었다. 백업 도구 Velero 가 **자기 자신의 청소 작업 파드**를 백업하려다 실패한 것이었다.

짧은 사건이지만 "모든 걸 백업한다"는 설정이 어떻게 자기 꼬리를 무는지 잘 보여 줘서 기록해 둔다.
버전은 Velero v1.18.1, 볼륨 백업은 kopia 기반 파일 시스템 백업(FSB)이다.

## 1. 증상

```
daily-with-volumes-20261009030052   PartiallyFailed   errors=2   warnings=98
items backed up: 7512 / 7512
```

리소스 7,512개는 전부 백업됐다. 에러는 2건뿐이다. 볼륨별 백업 기록(PodVolumeBackup)에서 실패한 것만 추리면 이렇다.

```
NS      POD                                                    PHASE   MESSAGE
velero  lemuel-xr-prod-default-kopia-…-maintain-job-…          Failed  error to get pod volume path:
        … for volume scratch … expected one matching path: /host_pods/<uid>/volumes/*/scratch, got 0
velero  lemuel-xr-prod-default-kopia-…-maintain-job-…          Failed  … for volume plugins … got 0
```

실패한 두 건 모두 **velero 네임스페이스의 `…-kopia-…-maintain-job-…` 파드**, 그 파드의 볼륨 두 개(`scratch`, `plugins`)였다.

## 2. maintain-job 이 뭔가

Velero 가 kopia 로 볼륨을 백업하면 백업 저장소(repository)가 생긴다. 이 저장소는 주기적으로 정리해 줘야 한다.
지워진 백업의 데이터 조각을 실제로 치우는 것도 이 정리 작업이다.
[파일 시스템 백업 문서](https://velero.io/docs/v1.18/file-system-backup/)도 백업을 지워도 정리 작업이 끝나기 전까지는 저장 용량이 줄지 않는다며,
*주기적인 저장소 정리 잡이 실제로 돌고 성공하는지 확인하라*고 적는다.

[저장소 정리 문서](https://velero.io/docs/v1.18/repository-maintenance/)에 따르면 이 정리는 원래 Velero 서버 안에서 돌았다.
그러다 서버가 OOM 으로 죽는 문제가 있어서, 지금은 **Velero 설치 네임스페이스에 독립된 쿠버네티스 Job 을 띄워서** 정리한다.
주기는 kopia 기준 **기본 1시간**이다.

우리 클러스터에서는 백업 저장소가 네임스페이스마다 하나씩 생겨 수십 개다. 그래서 velero 네임스페이스에는 **짧게 떴다 사라지는 정리 파드가 거의 늘 몇 개씩 있다.**
지금 이 순간에도 `…-maintain-job-…` 파드가 줄줄이 `Completed` 상태로 남아 있다.

## 3. 무슨 일이 있었나 — 13초 차이

우리 매일 백업의 설정은 이렇다.

```yaml
spec:
  schedule: "0 3 * * *"
  template:
    includedNamespaces: ["*"]                         # 모든 네임스페이스
    excludedNamespaces: [kube-public, kube-node-lease]
    defaultVolumesToFsBackup: true                    # 모든 파드 볼륨을 파일 백업 (opt-out 방식)
```

"모든 네임스페이스의 모든 파드 볼륨"이다. 여기에는 velero 네임스페이스도, 그 안의 정리 파드도 들어간다.

시간을 맞춰 보면 이렇다. 정리 Job 이름 끝의 숫자는 생성 시각(유닉스 밀리초)이다.

| 시각 (UTC) | 일 |
|---|---|
| 03:00:39 | lemuel-xr 저장소 정리 Job 파드 생성 |
| 03:00:52 | 매일 백업 시작. 그 순간 떠 있던 정리 파드도 백업 대상 목록에 들어감 |
| 잠시 뒤 | 정리 파드가 할 일을 끝내고 종료. 볼륨 디렉터리 정리됨 |
| 볼륨 복사 차례 | 노드에서 `/host_pods/<uid>/volumes/*/scratch` 를 찾음 → **0개** → 실패 |

백업이 목록을 만들 때는 파드가 있었다. 하지만 실제로 볼륨을 복사하러 갔을 때는 파드가 이미 일을 마치고 볼륨이 사라진 뒤였다.
에러 메시지의 *"expected one matching path … got 0"*이 그 뜻이다.

덧붙여 `0 3 * * *` 는 **UTC** 기준이라 한국 시간으로는 새벽 3시가 아니라 **정오**다. 처음 보고에서 "새벽 백업"이라고 했는데, 기록을 다시 보니 시작이 03:00:52Z 였다.
스케줄을 읽을 때는 시간대부터 확인해야 한다.

## 4. 왜 매일 안 터지나

지난 8일 동안 매일 백업 결과는 이랬다.

| 날짜 | 결과 |
|---|---|
| 10-02 | PartiallyFailed (다른 원인, 에러 53건) |
| 10-03 ~ 10-08 | Completed |
| 10-09 | PartiallyFailed (에러 2건, 이번 건) |

정리 파드는 몇 초에서 수십 초면 끝난다. 백업 시작 시점에 **마침 막 뜬 정리 파드가 있고**, 그 파드의 볼륨 차례가 오기 전에 파드가 끝나야 이 실패가 난다.
그래서 매일이 아니라 가끔 터진다. 이런 **간헐적 경합**이 제일 성가시다. 재현이 안 되니 "어제는 됐는데"로 넘어가기 쉽다.

## 5. 고치는 방법

### 1안: 매일 백업에서 velero 네임스페이스 제외 (권장)

```yaml
excludedNamespaces: [kube-public, kube-node-lease, velero]
```

[리소스 필터링 문서](https://velero.io/docs/v1.18/resource-filtering/)의 `--exclude-namespaces` 와 같은 기능이다.

velero 네임스페이스를 빼도 되는 이유가 있다. [동작 원리 문서](https://velero.io/docs/v1.18/how-velero-works/)는
*"Velero 는 오브젝트 스토리지를 진실의 원천(source of truth)으로 본다"*고 적는다. 버킷에 백업 파일이 있고 클러스터에 해당 Backup 리소스가 없으면, Velero 가 스토리지에서 클러스터로 다시 동기화한다.
즉 백업 목록은 velero 네임스페이스를 백업해서 지키는 게 아니라 **버킷에 이미 있다.** 클러스터를 새로 만들어도 Velero 를 같은 버킷에 연결하면 목록이 돌아온다.
정리 파드는 애초에 지킬 데이터가 없는 일회성 파드다.

Velero 설치 자체(배포 설정, 자격증명)는 GitOps 리포에서 다시 깔 수 있으니, 그쪽 복구도 백업이 아니라 리포가 맡는다.

### 2안: 파드 단위 제외 어노테이션

[파일 시스템 백업 문서](https://velero.io/docs/v1.18/file-system-backup/)는 opt-out 방식에서 `backup.velero.io/backup-volumes-excludes` 어노테이션으로
특정 파드의 볼륨을 뺄 수 있다고 안내한다. 하지만 정리 Job 파드는 Velero 가 직접 만드는 것이라 매번 어노테이션을 붙이기 어렵다. 이번 경우엔 맞지 않는다.

### 3안: opt-in 으로 전환

모든 볼륨을 기본으로 백업하는 대신, 백업할 볼륨에만 표시를 다는 방식이다. 가장 깔끔하지만 지금 백업되는 수십 개 네임스페이스의 볼륨을 전부 다시 지정해야 한다.
작은 소음 하나 끄자고 바꾸기엔 범위가 너무 크다.

1안이 가장 작고 안전한 변경이라고 본다. 다만 이 스케줄은 ArgoCD 가 리포에서 관리한다(`velero-tuning` 앱). 노드에서 `kubectl edit` 로 고치면 ArgoCD 가 되돌린다.
그래서 수정은 리포에서 한다.

## 6. 교훈 — "일부 실패"는 그냥 두면 안 된다

이번 실패는 데이터 손실이 아니다. 앱 데이터는 전부 백업됐다. 그래서 그냥 두고 싶어진다.
하지만 `PartiallyFailed` 가 일상이 되면 **진짜 일부 실패가 왔을 때 아무도 열어 보지 않는다.** 경보는 울릴 때마다 의미가 있어야 한다.

정리하면 이렇다.

1. **"전부 백업"에는 백업 도구 자신도 들어간다.** 백업 도구가 띄우는 일회성 파드는 백업 대상이 아니라 소음이다.
2. **간헐적 실패는 시각을 맞춰 보면 풀린다.** 이번에는 Job 이름 속 생성 시각과 백업 시작 시각의 13초 차이가 답이었다.
3. **스케줄은 시간대부터 읽는다.** cron 표현식만 보고 "새벽 3시"라고 생각하면 틀린다.
4. **무엇을 백업하지 않아도 되는지 알려면 복구 경로를 알아야 한다.** velero 네임스페이스를 빼도 되는 건, 백업 목록이 버킷에 있고 설치는 리포에 있기 때문이다.

## References

- Velero v1.18 문서, *Repository Maintenance* — <https://velero.io/docs/v1.18/repository-maintenance/>
- Velero v1.18 문서, *File System Backup* — <https://velero.io/docs/v1.18/file-system-backup/>
- Velero v1.18 문서, *Resource filtering* — <https://velero.io/docs/v1.18/resource-filtering/>
- Velero v1.18 문서, *How Velero Works* (Object storage sync) — <https://velero.io/docs/v1.18/how-velero-works/>
