---
layout: post
title: "K3s local-path-provisioner 에 4TB HDD 통합 — configmap 자동 복원 우회하기"
date: 2026-05-12 22:50:00 +0900
categories: [infra, kubernetes, k3s, storage]
tags: [k3s, local-path-provisioner, storage, bind-mount, hdd]
---

K3s 의 default storage class `local-path` 는 `/var/lib/rancher/k3s/storage` 에 PVC 를 만듭니다. 일원 노드에 4TB HDD 를 새로 장착한 김에 모든 ilwon PVC 를 HDD 에 자동 할당하도록 통합한 기록입니다. 처음 ConfigMap 수정 방식이 **K3s addon 매니지드** 라서 자동 복원되는 함정도 같이.

> 이 글에서 다루는 것
> - local-path-provisioner 의 nodePathMap 동작 원리
> - K3s addon 이 ConfigMap 을 5 초마다 복원하는 함정
> - bind mount 방식이 더 안정적인 이유
> - PVC 데이터 migration 안전 절차

---

## 1. 일원 디스크 추가

```bash
$ lsblk -d -o NAME,SIZE,TYPE,MODEL
NAME      SIZE TYPE  MODEL
sda       3.6T disk  WDC WD40EFZZ-68CPAN0    ← WD Red Plus 4TB 새로 장착
nvme0n1 465.8G disk  Samsung SSD 970 EVO Plus (OS)
```

목표: `sda` 를 K3s PVC 풀로 통합. 기존 NVMe (OS) 는 그대로.

## 2. 파티션 + 포맷 + 마운트

```bash
sudo parted /dev/sda -- mklabel gpt
sudo parted -a optimal /dev/sda -- mkpart primary ext4 0% 100%
sudo mkfs.ext4 -L hdd-4tb /dev/sda1

sudo mkdir -p /mnt/hdd-4tb
echo 'LABEL=hdd-4tb /mnt/hdd-4tb ext4 defaults,nofail 0 2' \
  | sudo tee -a /etc/fstab
sudo mount -a
```

검증:
```
$ df -h /mnt/hdd-4tb
/dev/sda1   3.6T   2.1M  3.4T   1%   /mnt/hdd-4tb
```

## 3. local-path-provisioner 구조

K3s 의 default provisioner. ConfigMap `local-path-config` 에 `nodePathMap` 정의:

```json
{
  "nodePathMap":[
    {
      "node":"DEFAULT_PATH_FOR_NON_LISTED_NODES",
      "paths":["/var/lib/rancher/k3s/storage"]
    }
  ]
}
```

원하는 효과: 일원에서 PVC 생성 시 `/mnt/hdd-4tb/...` 에 저장.

## 4. 첫 시도 — ConfigMap 직접 수정 (실패)

```bash
kubectl patch cm local-path-config -n kube-system --type=merge -p '{
  "data": {
    "config.json": "{\"nodePathMap\":[
      {\"node\":\"DEFAULT_PATH_FOR_NON_LISTED_NODES\", \"paths\":[\"/var/lib/rancher/k3s/storage\"]},
      {\"node\":\"ilwon\", \"paths\":[\"/mnt/hdd-4tb\"]}
    ]}"
  }
}'
```

테스트 PVC 생성 → 일원 노드에 스케줄 → 결과:

```
$ kubectl get pv pvc-xxx -o yaml | grep path:
path: /var/lib/rancher/k3s/storage/...    ← ilwon 경로 무시됨!
```

ConfigMap 다시 보니:
```
$ kubectl get cm -n kube-system local-path-config -o jsonpath='{.data.config\.json}'
{
  "nodePathMap":[
    {
      "node":"DEFAULT_PATH_FOR_NON_LISTED_NODES",
      "paths":["/var/lib/rancher/k3s/storage"]
    }
  ]
}
```

**복원돼 있음.** K3s 가 매니지드 애드온으로 local-path 를 관리해서, 변경된 ConfigMap 을 자동으로 원래대로 되돌립니다.

> **K3s 매니지드 애드온**: traefik, local-path, metrics-server, coredns 등. `/var/lib/rancher/k3s/server/manifests/` 의 매니페스트가 매번 적용. `--disable=local-storage` 로 비활성화 가능하지만 그러면 우리가 직접 provisioner 운영.

## 5. 두 번째 시도 — bind mount (성공)

발상 전환: ConfigMap 의 경로는 그대로 두고, **실제 디스크 경로를 HDD 로 가리키게** 한다.

```bash
# 1. k3s-agent 정지 (포드 일시 중지)
sudo systemctl stop k3s-agent

# 2. 기존 storage 데이터 옮기기 (380MB)
sudo rsync -aAXv /var/lib/rancher/k3s/storage/ /mnt/hdd-4tb/
sudo rm -rf /var/lib/rancher/k3s/storage
sudo mkdir -p /var/lib/rancher/k3s/storage

# 3. bind mount + fstab
echo 'LABEL=hdd-4tb /var/lib/rancher/k3s/storage none bind,nofail 0 0' \
  | sudo tee -a /etc/fstab
sudo mount --bind /mnt/hdd-4tb /var/lib/rancher/k3s/storage

# 4. 재시작
sudo systemctl start k3s-agent
```

검증:
```
$ df -h /var/lib/rancher/k3s/storage
/dev/sda1   3.6T   396M  3.4T   1%   /var/lib/rancher/k3s/storage
```

이제 모든 ilwon PVC 는 **path 는 그대로** `/var/lib/rancher/k3s/storage/pvc-xxx/` 보이지만 **실제 데이터는 HDD** 에 저장. K3s 가 ConfigMap 복원해도 영향 없음.

## 6. Prometheus 30Gi PVC 이전 — 실전 검증

prometheus 가 솔로몬 (storage-backup) 에서 ilwon 으로 옮겨야 했음:

```bash
# 1. StatefulSet replicas=0 (Pod 종료)
kubectl scale sts prometheus-kps-prometheus -n monitoring --replicas=0

# 2. 옛 PVC 삭제 (PV 도 같이 사라짐 — Delete reclaim policy)
kubectl delete pvc prometheus-kps-prometheus-db-prometheus-kps-prometheus-0 -n monitoring

# 3. 복원
kubectl scale sts prometheus-kps-prometheus -n monitoring --replicas=1

# 4. 검증
kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.local.path} ({.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}){"\n"}{end}'
```

결과:
```
pvc-50fb87e5-...: /var/lib/rancher/k3s/storage/pvc-..._prometheus-... (node=ilwon)
```

bind mount 덕분에 실제 데이터는 `/mnt/hdd-4tb/` 에. 일원 노드 보면:
```
$ ls /mnt/hdd-4tb/
pvc-50fb87e5-..._monitoring_prometheus-...
lost+found
```

> **메트릭 데이터 손실 8 시간**: prom 의 새 PVC 는 fresh 시작이라 옛 메트릭 없음. 운영 중이라면 prom snapshot 후 restore. 학습 환경이라 OK.

## 7. 다른 옵션과 비교

| 방식 | 장점 | 단점 |
|---|---|---|
| **bind mount** (선택) | K3s addon 우회, 투명 | 노드별 수동 설정 |
| ConfigMap 직접 수정 | 깔끔 | K3s addon 이 복원함 (k3s 1.34) |
| `--disable=local-storage` + 자체 provisioner | 완전 통제 | 운영 부담 ↑ |
| OpenEBS / Longhorn (분산) | 노드 장애 견딤 | 복잡, IOPS overhead |
| Symlink (`ln -s`) | 더 가벼움 | inode 추적 일부 도구 혼란 |

bind mount 가 sweet spot. mount 자체가 표준이라 어떤 도구도 헷갈리지 않음.

## 8. storage-tier 라벨링 — SC 1 개로 다중 디스크 흉내

ilwon 만 HDD. 다른 노드는 다 SSD/내장. PVC 가 자동으로 적절한 디스크에 가게 하려면 노드 라벨 + nodeAffinity 활용:

```bash
# 노드 라벨링
kubectl label node ilwon   storage-tier=hdd-4tb tier=storage   --overwrite
kubectl label node solomon tier=storage-backup                 --overwrite
kubectl label node david   storage-tier=ssd                    --overwrite
```

차트에서:
```yaml
# stateful (콜드)
postgres:
  nodeSelector:
    tier: storage     # → ilwon HDD
```

**SSD 도착하면**: ilwon 에 `/dev/nvme1n1` 추가 → `/mnt/ssd-1tb` 마운트 → 새 StorageClass `local-path-ssd` 만들거나 PVC nodeAffinity 로 분리.

## 9. 함정 회피 체크리스트

- [ ] `nofail` mount option (디스크 빠져도 부팅 가능)
- [ ] `mkfs` 전 `lsblk -f` 로 빈 디스크 확인
- [ ] bind mount 전 k3s-agent stop (포드 동시 쓰기 충돌 회피)
- [ ] `rsync -aAX` 로 권한/ACL 보존
- [ ] `/etc/fstab` 에 추가 후 `mount -a` 로 dry-run
- [ ] PV 의 `path:` 확인 (kubectl get pv -o yaml)
- [ ] 실제 데이터가 새 마운트 포인트에 쓰이는지 `du -sh`

---

## 10. 정리 — K3s 매니지드 애드온은 양날의 검

K3s 의 매니지드 애드온은:
- ✅ 설치 즉시 동작 (zero config)
- ❌ 사용자가 변경하면 무력화

해법: **데이터 평면을 건드리지 말고, 디스크 표현만 바꾼다.** bind mount, symlink, overlayfs 등 OS 레벨 도구가 K3s addon 매니지드 우회의 정답.
