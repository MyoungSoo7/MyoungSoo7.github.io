---
layout: post
title: "[CS300 #228] 쿠버네티스 스토리지 — 볼륨, PV, PVC, 스토리지클래스"
date: 2026-10-10 21:48:00 +0900
categories: [cs]
tags: [cs300, devops, kubernetes, storage, persistent-volume]
---

컴퓨터공학 300 주제 시리즈의 228번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

파드는 일회용이지만 데이터는 아니다. 쿠버네티스는 "얼마나, 어떤 방식으로 필요한가"(PVC)와 "실제로 어디에 있는가"(PV)를 분리하고, 스토리지클래스가 그 사이를 자동으로 이어 준다.

## 왜 필요한가

컨테이너의 쓰기 레이어는 컨테이너와 함께 사라진다. 파드가 다른 노드로 옮겨 가면 그 노드의 로컬 디스크에 있던 파일도 따라오지 않는다. DB, 업로드 파일, 메시지 큐처럼 상태를 가진 애플리케이션을 쿠버네티스에 올리려면 파드의 수명과 데이터의 수명을 떼어 놓아야 한다.

동시에 개발자가 "이 클러스터의 NFS 서버 주소는 무엇이고 export 경로는 어디인가"까지 알아야 한다면 이식성이 사라진다. 그래서 쿠버네티스는 요청과 공급을 분리한다.

## 핵심 개념

### 볼륨의 세 부류

| 부류 | 예 | 수명 |
|---|---|---|
| 임시(ephemeral) | `emptyDir`, `configMap`, `secret` | 파드와 같다. 파드가 지워지면 사라진다 |
| 노드 경로 | `hostPath` | 노드에 남지만 파드가 다른 노드로 가면 못 본다. 보안 위험이 커서 일반 앱엔 쓰지 않는다 |
| 영속(persistent) | PVC 를 통한 PV | 파드와 독립적이다 |

`emptyDir` 은 파드 안 컨테이너끼리 파일을 주고받거나 캐시를 둘 때 쓴다. 컨테이너가 재시작해도 남지만, 파드가 지워지면 사라진다.

### PV 와 PVC

- **PersistentVolume(PV)**: 클러스터에 있는 실제 저장 공간 한 조각. 관리자가 미리 만들거나 동적으로 만들어진다. 클러스터 범위 객체다.
- **PersistentVolumeClaim(PVC)**: 사용자의 요청서. "10Gi, 한 노드에서 읽기·쓰기, fast 클래스로." 네임스페이스 범위 객체다.

컨트롤 플레인은 PVC 에 맞는 PV 를 찾아 **1:1 로 바인딩**한다. 요청보다 큰 PV 가 바인딩될 수는 있지만, 한 번 묶이면 그 PV 는 다른 PVC 가 쓸 수 없다. 맞는 PV 가 없으면 PVC 는 `Pending` 으로 남는다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: fast
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: db
spec:
  containers:
    - name: db
      image: postgres:17
      volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data
```

### 접근 모드

| 모드 | 약어 | 뜻 |
|---|---|---|
| ReadWriteOnce | RWO | **한 노드**가 읽기·쓰기로 마운트(같은 노드의 여러 파드는 가능) |
| ReadOnlyMany | ROX | 여러 노드가 읽기 전용으로 |
| ReadWriteMany | RWX | 여러 노드가 읽기·쓰기로 |
| ReadWriteOncePod | RWOP | **한 파드**만 읽기·쓰기로 |

RWO 는 "파드 하나"가 아니라 "노드 하나"다. 자주 틀리는 부분이다. 블록 스토리지(클라우드 디스크, iSCSI)는 보통 RWO 만, NFS·CephFS 같은 파일 스토리지는 RWX 를 지원한다. 어떤 모드가 가능한지는 스토리지 드라이버가 정한다.

### 스토리지클래스와 동적 프로비저닝

관리자가 PV 를 일일이 미리 만드는 것은 번거롭다. 스토리지클래스는 "이런 종류의 디스크를 이 드라이버로 만들어라"는 템플릿이다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: example.com/csi-driver   # 실제로는 설치된 CSI 드라이버 이름
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

PVC 가 이 클래스를 지정하면 프로비저너가 PV 를 새로 만들어 바인딩한다. `storageClassName` 을 생략하면 기본(default) 스토리지클래스가 쓰인다.

`volumeBindingMode: WaitForFirstConsumer` 는 중요하다. 기본값 `Immediate` 는 PVC 가 생기자마자 볼륨을 만든다. 그런데 특정 영역(zone)이나 특정 노드에만 붙는 디스크라면, 볼륨이 먼저 A 영역에 만들어지고 파드는 B 영역에 스케줄되어 영원히 붙지 못할 수 있다. 첫 파드가 스케줄될 때까지 기다리면 이 문제가 없다.

### 회수 정책

PVC 를 지우면 바인딩된 PV 는 `reclaimPolicy` 에 따라 처리된다.

- `Delete`: PV 와 실제 저장 공간을 함께 지운다. 동적 프로비저닝의 일반적 기본값이다.
- `Retain`: PV 를 `Released` 상태로 남긴다. 데이터는 보존되며 관리자가 수동으로 정리·재사용한다.

중요한 데이터는 `Retain` 을 쓰거나 별도 백업을 둔다. 실수로 PVC 를 지웠을 때 `Delete` 정책이면 데이터가 함께 사라진다.

### CSI

Container Storage Interface(CSI) 는 스토리지 드라이버의 표준 인터페이스다. 예전에는 드라이버 코드가 쿠버네티스 본체에 들어 있었지만(in-tree), 지금은 각 벤더가 CSI 드라이버를 별도로 배포한다. 스냅샷, 확장, 복제 같은 기능도 드라이버 지원 여부에 달렸다.

### StatefulSet 과의 관계

DB 처럼 파드마다 자기 디스크가 필요한 경우 StatefulSet 의 `volumeClaimTemplates` 를 쓴다. 파드 `db-0`, `db-1` 마다 PVC `data-db-0`, `data-db-1` 이 만들어지고, 파드가 재생성되어도 같은 이름의 PVC 에 다시 붙는다.

## 직접 해 보기

PVC 바인딩 규칙을 단순화해 시뮬레이션해 보자. 같은 스토리지클래스, 접근 모드 포함, 용량 충분인 PV 중에서 가장 작은 것을 고른다.

```python
pvs = [
    {"name": "pv-a", "size": 5,  "modes": {"RWO"},        "sc": "fast", "bound": None},
    {"name": "pv-b", "size": 20, "modes": {"RWO"},        "sc": "fast", "bound": None},
    {"name": "pv-c", "size": 50, "modes": {"RWO", "RWX"}, "sc": "nfs",  "bound": None},
    {"name": "pv-d", "size": 12, "modes": {"RWO"},        "sc": "fast", "bound": None},
]
pvcs = [
    ("app-data", 10, "RWO", "fast"),
    ("shared",   30, "RWX", "nfs"),
    ("logs",     10, "RWO", "fast"),
    ("big",     100, "RWO", "fast"),
]

for name, size, mode, sc in pvcs:
    candidates = [pv for pv in pvs
                  if pv["bound"] is None and pv["sc"] == sc
                  and mode in pv["modes"] and pv["size"] >= size]
    if not candidates:
        print(f"{name:9} {size:>4}Gi {mode} -> Pending (no matching PV)")
        continue
    pv = min(candidates, key=lambda p: p["size"])
    pv["bound"] = name
    waste = pv["size"] - size
    print(f"{name:9} {size:>4}Gi {mode} -> {pv['name']} ({pv['size']}Gi, unused {waste}Gi)")

print("unbound PVs:", [p["name"] for p in pvs if p["bound"] is None])
```

결과는 다음과 같다.

```
app-data    10Gi RWO -> pv-d (12Gi, unused 2Gi)
shared      30Gi RWX -> pv-c (50Gi, unused 20Gi)
logs        10Gi RWO -> pv-b (20Gi, unused 10Gi)
big        100Gi RWO -> Pending (no matching PV)
unbound PVs: ['pv-a']
```

`logs` 는 10Gi 를 원했지만 20Gi PV 를 통째로 가져갔다. 정적 프로비저닝에서는 이런 낭비가 생긴다. `big` 은 맞는 PV 가 없어 Pending 이다. 동적 프로비저닝이라면 이 두 문제가 사라진다. 요청한 크기대로 새로 만들기 때문이다.

## 현업에서는

- **PVC 가 Pending 이다.** 기본 스토리지클래스가 없거나, 지정한 클래스 이름이 틀렸거나, 프로비저너(CSI 드라이버) 파드가 죽어 있는 경우가 대부분이다. `kubectl describe pvc` 의 Events 를 본다. `WaitForFirstConsumer` 라면 파드가 생기기 전까지 Pending 이 정상이다.
- **"Multi-Attach error".** RWO 볼륨을 쓰던 파드가 다른 노드로 옮겨 갔는데 옛 노드에서 볼륨 분리가 끝나지 않은 경우다. 디플로이먼트의 롤링 업데이트가 새 파드를 다른 노드에 먼저 띄우려 할 때도 생긴다. 단일 RWO 볼륨을 쓰는 디플로이먼트는 `Recreate` 전략이 안전하다.
- **로컬 디스크 기반 프로비저너.** 홈랩이나 경량 배포판에서는 노드의 로컬 디렉터리를 PV 로 만들어 주는 프로비저너가 기본 클래스로 들어 있는 경우가 많다. 간편하지만 데이터가 특정 노드에 묶인다. 그 노드가 죽으면 파드는 다른 곳에서 뜰 수 없다. 노드 간 복제가 필요하면 Longhorn·Ceph 같은 분산 스토리지를 쓴다.
- **백업은 별개다.** PV 는 영속적이지만 백업이 아니다. 디스크가 망가지거나 실수로 지우면 함께 사라진다. 스냅샷이나 애플리케이션 수준 백업을 따로 둔다(237번 주제).

## 확인 문제

1. `emptyDir` 볼륨의 데이터는 컨테이너 재시작 후 남는가? 파드 삭제 후에는?
2. PV 와 PVC 중 네임스페이스 범위 객체는 무엇인가?
3. ReadWriteOnce 볼륨을 같은 노드의 두 파드가 동시에 마운트할 수 있는가?
4. `volumeBindingMode: WaitForFirstConsumer` 가 해결하는 문제는?
5. `reclaimPolicy: Delete` 인 클래스로 만든 PVC 를 실수로 지웠다. 데이터는 어떻게 되는가?

### 풀이

1. 컨테이너 재시작 후에는 남는다. 파드가 삭제되면 사라진다.
2. PVC. PV 는 클러스터 범위다.
3. 가능하다. RWO 는 노드 단위 제한이다. 파드 하나로 제한하려면 RWOP 를 쓴다.
4. 볼륨이 파드가 스케줄될 수 없는 영역·노드에 먼저 만들어지는 문제. 파드 배치가 정해진 뒤 볼륨을 만든다.
5. PV 와 실제 저장 공간이 함께 삭제된다. 별도 백업·스냅샷이 없으면 복구할 수 없다.

## 더 읽을거리 (References)

- Kubernetes Docs, [Volumes](https://kubernetes.io/docs/concepts/storage/volumes/)
- Kubernetes Docs, [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- Kubernetes Docs, [Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- Kubernetes Docs, [Dynamic Volume Provisioning](https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/)
