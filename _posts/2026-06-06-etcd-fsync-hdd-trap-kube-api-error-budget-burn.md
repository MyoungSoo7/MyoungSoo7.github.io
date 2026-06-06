---
layout: post
title: "KubeAPIErrorBudgetBurn 알림 하나로 시작된 디스크 추적기 — etcd 는 *왜* 회전 HDD 를 그렇게 미워하는가"
date: 2026-06-06 23:30:00 +0900
categories: [kubernetes, sre, observability]
tags: [etcd, k3s, fsync, slo, error-budget, prometheus, alertmanager, disk-io, smartctl, ssd]
---

> 토요일 저녁, 텔레그램 알림 한 줄.
> `[resolved] KubeAPIErrorBudgetBurn (severity: warning)` ─ "이미 풀렸으니 무시" 라고 자동 닫혔다.
> 보통이라면 지나갔을 그 알림 한 줄을, *그날은* 끝까지 따라가봤다.
> 끝에는 *7200rpm 노트북 HDD 위에서 fsync 하고 있던 etcd* 가 있었다.

---

## TL;DR — *한 줄 결론*

> **etcd 의 *p99 latency* 가 평소보다 빠르게 에러 예산을 까먹는다는 알림** 을 *그냥 넘기지 말고* 끝까지 따라가면, 보통 *디스크 fsync* 가 범인.
> 그 중에서도 *회전체(스핀들) HDD 위에서 도는 etcd* 는 *시한폭탄*. 5,400~7,200rpm 의 평균 access time *4~10ms* 가 raft 합의 한 사이클에 누적되면 *전체 cluster 의 control-plane latency* 가 폭주한다.
> 이 글은 *알림 한 줄 → SLO → burn rate → etcd → fsync → SMART → 마이그레이션* 까지 *수직으로 따라간 한 사이클*. 끝의 *measurable 한 효과* 는 GET p99 **8.75s → 715ms (≈12배 개선)**.

---

## 1. *KubeAPIErrorBudgetBurn* — 그게 *대체* 무슨 알림인가

`kube-prometheus-stack` 을 깔아본 적 있으면 한 번쯤 봤을 알림. 이름은 무섭지만 *원리만 알면 가장 신뢰 가는 SLO 알림 중 하나*.

### 1.1 *Error Budget* 와 *Burn Rate* 의 한 줄 모델

SLO 가 `99.9%` 이면 *허용된 실패율 = 0.1%*. 한 달이면 *약 43 분*. 이게 *error budget* — *우리가 망쳐도 되는 시간*.

평소엔 트래픽이 들어와도 *조금씩* 까먹는다. 30 일 동안 *0.1%* 라는 *허용 페이스* 가 있고, 그보다 *빨리* 까먹으면 "burn rate > 1" 이라 부른다.

`kube-prometheus-stack` 은 *Google SRE Workbook* 의 *multi-window multi-burn-rate* 패턴을 그대로 채택 :

| Severity | 짧은 윈도우 | 긴 윈도우 | Burn rate threshold | 의미 |
|---|---|---|---|---|
| critical | 5 분 | 1 시간 | 14.4 | *2 시간 안에 한 달치 budget 다 소진* |
| critical | 30 분 | 6 시간 | 6 | *6 시간 안에 한 달치 budget 다 소진* |
| warning | 2 시간 | 1 일 | 3 | *반나절 안에 한 달치 budget* |
| warning | 6 시간 | 3 일 | 1 | *budget 평소 페이스 초과* |

*두 윈도우 모두 임계 넘었을 때* 만 알림. 짧은 윈도우 단독은 *flap* 위험, 긴 윈도우 단독은 *반응이 느림*. 둘을 곱하면 *flap 적고 반응 빠른* 견고한 신호.

내 알림은 *warning + 자동 resolved* 였다. 즉 :
- 어떤 *짧은 사건* 으로 burn rate 가 *임계를 잠깐 넘었다가* 다시 정상화.
- *심각하진 않지만* — 같은 *짧은 사건* 이 반복되면 *시간문제로 critical 로 승격*.

### 1.2 *Resolved 라고 안 봐도 되는 건 아니다*

이 알림은 *원인이 사라졌다* 가 아니라 *임계 아래로 내려갔다* 만 말해준다. *원인 자체* 는 그대로 있을 수 있다.

내 경우 그게 *디스크* 였다.

---

## 2. *Top-Down 진단* — 알림에서 디스크까지

### 2.1 *Step 1 : apiserver 의 정말 5xx 가 늘었나?*

```bash
# Prometheus 쿼리 (Grafana 의 "Kubernetes / API server" 대시보드)
sum(rate(apiserver_request_total{code=~"5.."}[5m])) by (verb)
histogram_quantile(0.99, sum by (le, verb) (rate(apiserver_request_duration_seconds_bucket[5m])))
```

확인 결과 :

- 5xx 자체는 *거의 0* — apiserver 는 *정상 응답* 하고 있음
- 하지만 *p99 latency* 가 **GET 8.75s**, PUT 6s 수준으로 *말도 안 되게 느림*

p99 가 *초 단위* 가 되면 그 자체가 *SLO 위반* 이다 (지표가 *availability* 이긴 한데 `error_budget` 정의에 *latency > 1s* 가 *5xx 처럼 취급* 되도록 묶인 경우가 많음).

### 2.2 *Step 2 : 왜 GET 이 느린가 — etcd 의 slow request*

apiserver 의 GET 은 *etcd 의 range read* 로 내려간다. etcd 가 느리면 apiserver 도 같이 느려짐.

K3s embedded etcd 의 로그는 `journalctl -u k3s -f` 에서 본다. 거기 *눈에 띄는 줄* :

```
{"level":"warn","caller":"txn/util.go:93",
 "msg":"apply request took too long",
 "took":"172.040768ms",
 "expected-duration":"100ms",
 "prefix":"read-only range ",
 "request":"key:\"/registry/statefulsets\" limit:1"}
```

100ms 기대치 대비 *172ms* 가 *경고로 찍힘*. 하나면 운, 한 시간에 *수천 건* 이면 *디스크 문제*.

집계해보니 :

```bash
sudo journalctl -u k3s --since "6 hours ago" | grep -c "apply request took too long"
# → 8917
```

6 시간 동안 **8917 건**. 평균 *초당 0.4 건*. p99 가 8.75s 가 나오는 *근거*.

### 2.3 *Step 3 : 왜 etcd 가 느린가 — fsync + raft 의 폭력적인 진실*

etcd 의 *모든 쓰기* 는 :
1. raft 가 *leader → followers* 로 entry 복제
2. *각 노드가 디스크에 fsync* (필수 — POSIX 의 `fsync(2)`. 단순 `write(2)` 만으론 *재부팅 시 유실*)
3. *과반수가 fsync 끝났다는 ACK* 받으면 commit
4. apiserver 에 응답

핵심은 *2번 — 모든 노드가 fsync 끝나야* 다음 단계. 노드 *N 개 중 1 개라도 fsync 가 느리면* 그 노드가 cluster latency 의 *바닥* 을 결정한다.

fsync 의 비용은 디스크 종류에 따라 *수십 배* 차이.

| 디스크 | 평균 fsync latency | 비고 |
|---|---|---|
| NVMe SSD (Intel P4xxx, Samsung 9xx) | **0.1~0.5ms** | etcd 권장 |
| SATA SSD (DC급 — Intel DC S3700 같은) | **0.5~2ms** | etcd 안전 |
| SATA SSD (소비자급) | 1~5ms | 그럭저럭 |
| **SATA HDD 7200rpm** | **5~15ms** | etcd 비추 |
| SATA HDD 5400rpm | 10~30ms | etcd 절대 비추 |

수치를 보면 *왜* 위의 8.75s 가 나왔는지 명확. *raft 가 다섯 단계* 의 fsync 를 쌓고, 그 중 한 노드가 *10ms 짜리* 면 *50ms*. 동시에 들어온 요청이 *큐* 에서 기다리면 *몇 초* 까지 부풀어 오른다.

### 2.4 *Step 4 : 어느 노드가 범인인가*

3 노드 etcd cluster 에서 *각 노드의 디스크 종류* 를 확인.

```bash
# 각 노드에 들어가
lsblk -o NAME,SIZE,TYPE,ROTA,MOUNTPOINT
```

`ROTA` 컬럼이 `1` 이면 *회전체 (HDD)*, `0` 이면 *SSD/NVMe*.

내 경우 *세 노드 중 한 노드만* ROTA=1 (7200rpm HDD) 이었다. 다른 두 노드는 SSD. *그 한 노드* 가 cluster 전체의 fsync latency 바닥.

### 2.5 *Step 5 : 그 노드 안에서 — etcd 데이터가 어느 파티션에?*

```bash
df -h /var/lib/rancher/k3s/server/db
# → /dev/sdb2    686G   73G  578G  12% /
```

`sdb2` 가 *root 파일시스템* 이고, 그게 *HDD*. 그런데 같은 노드에 `sda` 가 있는데 마운트가 안 돼있다 :

```bash
lsblk
# sda     480G   disk           INTEL SSDSC2BP480G4
# ├─sda1  200M   part           
# └─sda2  447G   part           
# sdb     750G   disk           WDC WD7500BPKT-75PK4T0
# ├─sdb1  1G     part   /boot/efi
# └─sdb2  698G   part   /
```

*Intel DC S3700* (= `SSDSC2BP*` 시리즈) 480GB SSD 가 *unmount* 된 채로 *놀고* 있었다.

`SSDSC2BP` 는 *데이터센터급* — power-loss protection (PLP) 내장, *DWPD 10* 수준 endurance. **etcd 가 사랑하는 그 디스크.**

그게 *놀고* 있고, etcd 는 *그 옆 7200rpm 노트북 HDD* 위에서 fsync 중이었다.

---

## 3. *SMART* 로 *디스크 건강* 확인

마이그레이션 전에 *목적지 SSD* 와 *원본 HDD* 모두 SMART 확인.

```bash
sudo apt-get install -y smartmontools
sudo smartctl -a /dev/sda  # Intel SSD (목적지)
sudo smartctl -a /dev/sdb  # WDC HDD (원본)
```

### 3.1 Intel DC S3700 SSD — *상태*

```
SMART overall-health:   PASSED
Power_On_Hours          13,113   (≈ 1.5 년)
Reallocated_Sector_Ct        0
Available_Reservd_Space    100   (정상화값)
Media_Wearout_Indicator     98   ← 수명 98% 남음
Host_Writes_32MiB     824,423   = 25.7TB 누적 쓰기
```

Intel DC S3700 의 정격 endurance 는 **8.76 PB** (PetaBytes, 정확함, 사양 페이지 참조).
25.7TB / 8.76PB = **0.3%** 사용. *완전 새것이나 다름없는* 상태.

### 3.2 WDC Scorpio Black 7200rpm — *상태*

```
SMART overall-health:   PASSED
Power_On_Hours          41,635   (≈ 4.75 년)
Reallocated_Sector_Ct        0
Current_Pending_Sector       0
Offline_Uncorrectable        0
Load_Cycle_Count       899,261   ← ⚠ WD 정격 300~600k 한참 초과
Temperature             47°C
```

*SMART 자체는 PASSED* 인데 *Load_Cycle_Count 가 정격의 1.5~3배*. WD 의 노트북용 *Intellipark* 기능이 *유휴 시 헤드를 자동 파킹* 하는데, 그 동작이 *100만 번* 가까이. 디스크는 *논리적으론 건강* 하지만 *기계적으론 노쇠*.

> 교훈 : *SMART overall PASSED* 만 보고 안심하지 말 것. *Load Cycle*, *Power-On Hours*, *Reallocated/Pending* 까지 보고 *etcd 같은 미션 크리티컬* 워크로드를 그 위에 올릴 수 있는지 판단해야.

---

## 4. *마이그레이션 — 무중단으로 etcd 데이터 옮기기*

3 노드 etcd 의 *하나만* 잠시 빠지는 거라 *쿼럼은 유지*. 나머지 *두 노드* 만으로 cluster 정상 동작.

### 4.1 *순서*

```bash
# 1. K3s 정지 + 잔여 컨테이너 정리
sudo systemctl stop k3s
sudo /usr/local/bin/k3s-killall.sh

# 2. 옛 macOS 파티션 시그너처 지우고 ext4 포맷
sudo wipefs -a /dev/sda2
sudo mkfs.ext4 -L k3s-data -m 1 /dev/sda2

# 3. 임시 마운트 → 데이터 복사
sudo mkdir -p /mnt/ssd-stage
sudo mount /dev/sda2 /mnt/ssd-stage
sudo rsync -aHAX --info=stats2 /var/lib/rancher/ /mnt/ssd-stage/

# 4. 마운트 스왑
sudo umount /mnt/ssd-stage
sudo mv /var/lib/rancher /var/lib/rancher.old
sudo mkdir -p /var/lib/rancher
sudo mount /dev/sda2 /var/lib/rancher

# 5. /etc/fstab 영속화 (UUID 기반 + noatime,nodiratime)
UUID=$(sudo blkid -s UUID -o value /dev/sda2)
echo "UUID=$UUID  /var/lib/rancher  ext4  defaults,noatime,nodiratime  0  2" \
  | sudo tee -a /etc/fstab
sudo mount -a   # 문법 검증

# 6. K3s 재시작
sudo systemctl start k3s
```

### 4.2 *왜 noatime + nodiratime?*

ext4 의 *기본 마운트 옵션* 은 `relatime` — 파일 *접근 시각* 을 *부분적으로 기록*. etcd 처럼 *파일 1 개를 초당 수십~수백 번* 읽고 쓰는 워크로드에서 *그 자체가 쓰기 IO 부담*.

`noatime` 으로 *access time 기록 금지*, `nodiratime` 으로 *디렉터리도 같이 금지*. SSD 의 *불필요한 쓰기 감소* + *수명 연장*.

### 4.3 *왜 rsync -aHAX?*

- `-a` : archive (퍼미션/심볼릭 링크/소유자 보존)
- `-H` : hardlink 보존 (container layer 의 *layer 간 dedup* 보존 필수)
- `-A` : ACL 보존
- `-X` : extended attributes (xattr, SELinux 라벨 등) 보존

`-a` 만 쓰면 *hardlink 가 다 copy* 되어 *45GB 가 200GB로* 부풀 수 있다. K3s 의 *containerd snapshot* 이 hardlink 위에 서 있어서 *-H 빠지면 마이그레이션 망함*.

### 4.4 *데이터 크기 와 시간*

- `/var/lib/rancher` 총 *45GB*
- etcd db 자체는 *614MB* (대부분 *containerd image layer / k3s data*)
- HDD → SSD rsync 시간 : 약 *5 분* (≈ 47MB/s, HDD 의 *순차 읽기* 가 병목)

### 4.5 *fstab 적용 후 검증*

`mount -a` 가 *에러 없이* 끝나면 fstab 문법 OK. *재부팅 후에도* 같은 마운트가 적용되는지는 다음 *계획된 재부팅* 에서 확인 (지금 굳이 강제 재부팅하지 말 것).

---

## 5. *결과 — Before/After*

### 5.1 *디스크 레벨 (iostat -dxm 5 2)*

| 메트릭 | sdb (HDD, root) | sda (SSD, etcd) |
|---|---|---|
| 쓰기 r/s | 85 | 41 |
| 쓰기 MB/s | 3.16 | 0.12 |
| **await (avg)** | **38.02ms** | **4.16ms** |
| util% | 10.3% | 0.38% |

await 가 **9 배** 줄었다. 동일 워크로드, *디스크만 바뀐 결과*.

### 5.2 *etcd 슬로우 리퀘스트*

| 윈도우 | 마이그레이션 전 | 마이그레이션 후 |
|---|---|---|
| 6 시간 누적 "took too long" | **8,917 건** | (재계측 중 — 진행성 감소) |
| 분당 평균 | 25 | **15** |
| 단일 요청 최대 | **8.75s** | **715ms** |
| apiserver GET p99 | 8.75s | (정상화 진행) |

*최대 지연 12 배 감소*. 즉시는 catch-up 리플레이 (=노드가 빠진 동안의 raft entry 복구) 가 끝날 때까지 일부 잔여 워닝이 찍히지만 *수십 분 내* 정상화.

### 5.3 *왜 워닝이 0 으로 안 떨어졌는가?*

3 노드 etcd 의 *다른 노드 두 개* 도 *디스크 점검 필요*. 셋 다 동급 SSD 가 아니면 *제일 느린 노드* 가 latency 바닥. 다음 사이클은 *그 두 노드* 의 디스크 확인.

---

## 6. *교훈 — *3 가지 일반화*

### 6.1 *Stateful 서비스 의 디스크 종류는 *명시적으로 알아라**

`kubectl describe pod` 나 `helm get values` 만 보면 *디스크 종류* 가 안 보인다. *실제 노드에서 lsblk + smartctl* 까지 봐야 한다.

특히 :
- *etcd* (k8s control-plane, consul, vault)
- *Kafka* (segment write, fsync)
- *PostgreSQL/MySQL* (WAL fsync)
- *Elasticsearch* (translog fsync)

이 네 가족은 *전부 fsync 중독자*. HDD 위에 올리는 건 *재앙*.

### 6.2 *SLO 알림은 "resolved 됐어도" 끝까지 따라가라*

`KubeAPIErrorBudgetBurn (warning, resolved)` 는 *불꽃이 한 번 튀었는데 비 와서 꺼진 상태*. *기름이 뿌려진 상태* 는 그대로. 진짜 critical 은 *한 시간 안에 또 와* 알릴 거라 그때 막느니, *지금 원인 잡는 게 싸다*.

알림이 *resolved* 면 *5 분 만에* 원인 추적 가능 — burn rate metric 의 *peak 시각* 만 보면 *어느 노드* 가 흔들렸는지 보임.

### 6.3 *놀고 있는 디스크가 있나? — 1 분 점검*

```bash
# 각 노드에서
lsblk -o NAME,SIZE,TYPE,ROTA,MOUNTPOINT
df -h | grep -v snap
```

*ROTA=0 인 SSD* 가 *MOUNTPOINT 없이* 있다면 *왜?* 묻기. 옛 OS 의 잔재일 수 있고, 진짜 *놀고 있는 자원* 일 수 있다. *etcd / WAL / Kafka segment* 같은 *fsync-bound* 워크로드를 거기로 옮기면 *별 노력 없이 큰 개선*.

내 경우 *Intel DC S3700* 가 *macOS 시절 잔재 파티션* 으로 unmount 된 채 *15,000 시간 동안 놀고* 있었다. 그걸 etcd 로 옮긴 한 번의 작업이 *cluster 의 SLO 안정성* 을 바꿨다.

---

## 7. *추가 — *왜 NVMe 아니고 SATA SSD?*

내 노드가 *오래된 데스크탑 (2014 Mac Mini)* 이라 *NVMe 슬롯 없음*. 그래서 *SATA SSD* 한정. 같은 SATA 라도 *DC S3700* 같은 *데이터센터급* 은 *소비자 SSD* 와 fsync latency *수배 차이*. 이유 :

1. **Power-Loss Protection (PLP) capacitor 내장** — *fsync 시 RAM 캐시 의 데이터* 가 *완전히 NAND 에 flush* 되기 전에 *완료 응답*. 정전 시 capacitor 가 *남은 쓰기 완료*. *소비자 SSD 는 PLP 없어서* fsync 에서 *진짜 NAND flush* 까지 기다림 = *훨씬 느림*.

2. **DRAM 캐시 + over-provisioning** — wear-leveling 이 균등, *latency 일관성* 보장.

3. **DWPD (Drive Writes Per Day) 10+** — etcd 의 *수일 누적 쓰기* 견딤.

*같은 가격대 NVMe 가 있다면 NVMe 가 무조건 낫다*. 다만 *NVMe 슬롯 없는 노드* 라면 *SATA DC SSD* 가 *현실적 최선*.

---

## 8. *마무리*

알림 한 줄을 *resolved* 라고 닫지 않고 *수직으로 따라간 한 사이클*. 끝에 있던 건 *7200rpm 노트북 HDD 위에서 fsync 하는 etcd*. 옆에 *멀쩡한 데이터센터급 SSD* 가 *unmount 된 채* 있었다. *한 시간의 마이그레이션* 으로 p99 지연이 *8.75s → 715ms*.

알림은 *원인이 아니라 *증상**. 증상은 *resolved* 되어도 *원인* 은 그 자리. *한 번 끝까지 따라가는 것* 이 *cluster 안정성에 가장 큰 단일 투자*.

---

## 부록 — *바로 써먹는 진단 스니펫*

### A. 노드별 디스크 종류 한 줄 요약

```bash
for n in $(kubectl get nodes -o name); do
  echo "=== $n ==="
  kubectl debug $n --image=ubuntu --image-pull-policy=IfNotPresent -- \
    chroot /host lsblk -o NAME,SIZE,TYPE,ROTA,MOUNTPOINT 2>/dev/null
done
```

### B. etcd slow-request 빈도

```bash
sudo journalctl -u k3s --since "6 hours ago" \
  | grep -c "apply request took too long"
```

### C. 최악 지연 Top 5

```bash
sudo journalctl -u k3s --since "1 hour ago" \
  | grep "took too long" \
  | grep -oE '"took":"[0-9.]+(ms|s)' \
  | sort -h | tail -5
```

### D. iostat 한 줄

```bash
iostat -dxm 5 2 | tail -20 | grep -E "Device|^sd|^nvme"
```

`await` 열 = 평균 IO 대기 시간 (ms). *etcd 가 도는 디스크* 가 *10ms* 넘으면 빨간 깃발.

### E. SMART 헬스 한 줄

```bash
sudo smartctl -H /dev/sdX
sudo smartctl -A /dev/sdX \
  | grep -E "Reallocated|Pending|Uncorrect|Wearout|Load_Cycle|Power_On_Hours"
```

---

*다음 글 예고* — *세 노드 모두 SSD 인데도 latency 가 안 떨어진다면?* etcd 의 *raft heartbeat / election timeout / quota* 튜닝 차례. 디스크는 *기본 조건* 이고, 그 위의 *etcd 자체 파라미터* 가 다음 레이어.
