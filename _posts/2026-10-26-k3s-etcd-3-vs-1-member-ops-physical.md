---
layout: post
title: "etcd 3개 vs 1개 — 홈랩 K3s 실측으로 본 운영·물리 구조의 차이"
date: 2026-10-26 14:58:05 +0900
categories: [kubernetes, sre]
tags: [etcd, k3s, raft, quorum, high-availability, homelab, wireless, etcd-snapshot]
---

> "개발·실험용이면 컨트롤 플레인 1, etcd 1, 워커 2 정도면 되지 않나?"
> 맞는 말이다. 그런데 지금 우리 클러스터는 etcd 표가 **3개**다.
> 3개를 1개로 줄이면 정확히 무엇을 잃고 무엇을 얻는지,
> 일반론 말고 **지금 돌고 있는 4노드 K3s의 etcd 지표**로 따져 봤다.

## TL;DR

| | etcd 3개 (현재) | etcd 1개 |
| --- | --- | --- |
| 견딜 수 있는 장애 | 멤버 1개 | **0개** ([etcd FAQ](https://etcd.io/docs/v3.5/faq/)) |
| 쓰기 1건이 기다리는 것 | 리더 + 팔로워 1개의 디스크 기록과 왕복 | 로컬 디스크 기록만 |
| 데이터 사본 | 3벌, 실시간 | 1벌 + 12시간마다 찍는 스냅샷 |
| 노드 하나가 죽으면 | API 계속 동작, 선출 지연은 ≥10초 (우리 설정) | API 중단, 스냅샷 복구 필요 |
| 망가뜨릴 수 있는 것 | 쿼럼 계산, 멤버 교체 순서 | 거의 없음. 대신 디스크가 곧 클러스터 |
| 적합한 용도 | 운영 서비스가 올라가 있을 때 | 개발·실험 전용 |

결론부터 말하면, **개발·실험만 한다면 1개는 합리적인 선택이다.** 다만 1개로 가는 순간 "백업이 그 노드 밖에 있는가"가 유일한 생명줄이 된다. 그런데 지금 이 클러스터의 스냅샷은 **노드 로컬 디스크에만 있다.**

---

## 1. 지금 클러스터의 물리 구조

2026-10-26 기준 노드는 4대다. 측정은 `kubectl get nodes`, 각 노드의 `ip`·`iw`·`lsblk`, 그리고 K3s 내장 etcd의 메트릭 엔드포인트(`127.0.0.1:2381/metrics`)를 직접 읽어서 했다.

| 노드 | 역할 | etcd 링크 | etcd 디스크 | 코어/메모리 |
| --- | --- | --- | --- | --- |
| **ilwon** | control-plane, etcd (**현재 리더**) | 유선 `eno1` (무선 동글을 active-backup 본딩의 예비로) | NVMe (Samsung 970 EVO Plus) | 12 / 30GB |
| **lemuel** | control-plane, etcd | 유선 `enp2s0` (5GHz 무선도 있지만 기본 경로는 유선) | SATA SSD | 4 / 31GB |
| **solomon** | **etcd 전용** (apiserver·scheduler·controller 끔) | **무선 USB 동글** (5GHz, 유선 포트는 NO-CARRIER) | SATA SSD | 4 / 15GB |
| louise | 워커 | 무선 (5GHz 내장) | – | – |

여기서 짚을 점이 두 가지 있다.

**첫째, solomon은 "etcd만 하는 서버"다.** K3s는 `--disable-apiserver --disable-controller-manager --disable-scheduler`로 etcd 역할만 따로 떼어 낼 수 있다([K3s: Managing Server Roles](https://docs.k3s.io/installation/server-roles)). 그래서 `kubectl get nodes`에서 solomon의 ROLES는 `etcd` 하나뿐이다. 즉 지금 구조는 **API 서버 2개 + etcd 표 3개**다.

**둘째, 세 번째 표가 무선 위에 있다.** solomon 설정 파일에 남은 이력 주석을 보면, 2026-08-19에 "무선 2.4GHz 동글 위의 표가 최악 링크"라는 이유로 강등됐다가 유선 노드(david)로 표가 넘어갔었다. 그 david가 전력 문제로 퇴역하면서 표가 다시 solomon으로 돌아왔다. 지금 solomon은 5GHz 동글로 붙어 있다. 무선 노드는 IoT 연구용으로 일부러 유지하는 조건이라, 이 글은 "유선으로 바꿔라"가 아니라 **"표를 어디에 몇 개 두느냐"** 의 문제로 다룬다.

---

## 2. 숫자로 본 세 표의 체력

etcd는 "디스크 지연이 리더 생존 판정의 일부"라고 공식 문서에 적혀 있을 만큼 디스크와 네트워크에 민감하다([etcd FAQ](https://etcd.io/docs/v3.5/faq/), [etcd Tuning](https://etcd.io/docs/v3.5/tuning/)). 그래서 두 축을 쟀다. 값은 각 멤버가 기동한 뒤 누적된 값이다(lemuel·ilwon은 10/18, solomon은 10/22 기동). etcd 메트릭은 재시작하면 0으로 돌아간다([etcd Metrics](https://etcd.io/docs/v3.5/metrics/)).

### 2-1. 디스크: WAL fsync

`etcd_disk_wal_fsync_duration_seconds`는 etcd가 로그를 디스크에 확정하는 시간이다.

| 멤버 | 평균 | 8ms 이내 비율 | `slow_apply_total` |
| --- | --- | --- | --- |
| solomon | **0.67 ms** | 99.9% | 1 |
| ilwon | 2.30 ms | 97.5% | 65 |
| lemuel | **5.52 ms** | **80.2%** | **1,057** |

의외의 결과다. **디스크만 보면 무선 노드 solomon이 가장 빠르고, 유선 노드 lemuel이 가장 느리다.** solomon의 `/var/lib/rancher`는 사용률 4%인 거의 빈 SSD이고, lemuel의 루트 디스크는 209GB를 쓰고 있는 데다 다른 워크로드와 디스크를 나눠 쓴다. etcd 하드웨어 가이드가 예시 사양을 들면서 "etcd 전용 머신"을 전제로 두고, 다른 앱과 섞으면 자원 경합으로 불안정해질 수 있다고 경고하는 바로 그 상황이다([etcd Hardware recommendations](https://etcd.io/docs/v3.5/op-guide/hardware/)).

### 2-2. 네트워크: 피어 왕복 시간

`etcd_network_peer_round_trip_time_seconds`는 멤버끼리 재는 RTT 히스토그램이다.

| 경로 | 평균 RTT | 12.8ms 이내 비율 |
| --- | --- | --- |
| lemuel → ilwon | 6.9 ms | 80.0% |
| ilwon → lemuel | 8.3 ms | 66.3% |
| solomon → ilwon | 11.6 ms | 49.3% |
| solomon → lemuel | 16.5 ms | 49.1% |
| ilwon → solomon | **27.4 ms** | **49.1%** |
| lemuel → solomon | **29.6 ms** | **49.0%** |

이번에는 반대다. **solomon으로 가는 경로는 절반이 12.8ms를 넘는다.** 리더 ilwon이 보낸 피어 전송 실패(`peer_sent_failures_total`)도 solomon 쪽이 4,886건, lemuel 쪽이 2,640건이다.

정리하면, **세 표 중 "디스크는 약하고 망은 강한" lemuel과 "디스크는 강하고 망은 약한" solomon이 섞여 있다.** 완벽한 표는 리더 ilwon 하나뿐이다.

### 2-3. 그래도 지금 클러스터는 건강하다

세 멤버 모두 `has_leader 1`, `leader_changes_seen_total 1`(기동 직후의 최초 선출 한 번), `heartbeat_send_failures_total 0`이다. 8일 동안 리더가 한 번도 바뀌지 않았다. 여기에는 이유가 있다. 이 클러스터는 etcd 타이머를 기본값보다 10배 넉넉하게 잡아 두었다.

```yaml
# /etc/rancher/k3s/config.yaml.d/20-etcd-timing.yaml (세 노드 동일)
etcd-arg:
  - heartbeat-interval=1000   # 기본 100ms
  - election-timeout=10000    # 기본 1000ms
```

etcd 공식 튜닝 문서는 하트비트를 "멤버 간 RTT 수준(0.5~1.5배)"으로, 선출 타임아웃을 "최소 RTT의 10배"로 잡으라고 권한다. 같은 문서에 "모든 멤버가 같은 값을 써야 한다"는 조건도 있다([etcd Tuning](https://etcd.io/docs/v3.5/tuning/)). 우리 값은 RTT 대비 훨씬 크다. 무선 지터를 흡수하려고 일부러 둔 여유다. **그 대가로 리더가 진짜 죽었을 때 알아채는 데 최소 10초가 걸린다.**

---

## 3. 운영 관점: 3개와 1개가 갈리는 지점

### 3-1. 장애 내성

etcd는 Raft 합의를 쓰고, 쓰기는 과반(쿼럼) 이 받아야 확정된다([Ongaro & Ousterhout, 2014](https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro)). 공식 FAQ의 표가 전부를 말해 준다([etcd FAQ](https://etcd.io/docs/v3.5/faq/)).

| 멤버 수 | 과반 | 견딜 수 있는 장애 |
| --- | --- | --- |
| 1 | 1 | 0 |
| 2 | 2 | **0** |
| 3 | 2 | 1 |

**2개는 1개보다 나쁘다.** 견딜 수 있는 장애 수는 똑같이 0인데 죽을 수 있는 기계만 하나 늘어난다. 그래서 줄일 거면 3에서 1로 바로 간다.

우리 클러스터에 대입하면 이렇다.

- **3개(현재)** — lemuel이든 ilwon이든 solomon이든 하나가 죽어도 API는 계속 쓰기를 받는다. 단 **ilwon이나 lemuel이 빠지면 남은 과반에 solomon이 반드시 들어간다.** 그때부터 모든 쓰기가 "절반이 12.8ms를 넘는 무선 링크"를 기다린다. 3개 구성의 진짜 내성은 "아무 노드 1개"가 아니라 "**유선 노드가 빠지면 품질이 떨어지는 1개**"다.
- **1개** — 그 노드가 죽으면 Kubernetes API가 멈춘다. 이미 떠 있는 파드는 kubelet이 계속 돌리지만 새 배포, 재스케줄, 자가치유는 전부 멈춘다.

### 3-2. 쓰기 지연 (단순 모델 — 측정이 아니라 추정)

Raft에서 쓰기는 리더 기록과 팔로워 과반의 응답을 기다린다. 위 실측치를 단순 모델에 넣으면:

- **3개, 리더 ilwon**: 가장 빠른 팔로워인 lemuel 응답을 기다린다 ≈ 왕복 ~8ms + lemuel fsync ~5.5ms → **대략 10ms대**
- **1개, ilwon 단독**: 로컬 fsync ~2.3ms → **수 ms**

체감 차이는 있겠지만 현재 DB가 70MB 수준이라(`etcd_mvcc_db_total_size_in_bytes` ≈ 70MB) 둘 다 etcd 가이드의 "small cluster"(100MB 이하) 범위 안이다([etcd Hardware](https://etcd.io/docs/v3.5/op-guide/hardware/)). **성능 때문에 1개로 갈 이유는 크지 않다.** 위 숫자는 평균값으로 계산한 모델일 뿐이며, 이 클러스터에서 두 구성을 헤드투헤드로 잰 결과가 아니다.

### 3-3. 데이터 보존: "복제"와 "백업"은 다르다

3개 구성에서는 세 노드가 데이터를 **실시간으로 3벌** 들고 있다. 디스크 하나가 날아가도 데이터는 잃지 않는다. 그렇다고 백업이 필요 없다는 뜻은 아니다. 누가 실수로 네임스페이스를 지우면 그 삭제도 3벌로 복제된다.

1개 구성에서는 **스냅샷이 유일한 사본**이다. 그런데 현재 상태를 보면:

```
$ k3s etcd-snapshot ls   (lemuel)
etcd-snapshot-lemuel-1792940405  file:///var/lib/rancher/k3s/server/db/snapshots/...  69828640  2026-10-26T00:00:05+09:00
etcd-snapshot-lemuel-1792983601  file:///var/lib/rancher/k3s/server/db/snapshots/...  69828640  2026-10-26T12:00:01+09:00
```

K3s 기본값 그대로다. 00시와 12시에 찍고, 노드마다 로컬에 5개를 보관하며, 위치는 `file://`다([K3s etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot)). 3개 구성에서는 세 노드가 각자 찍으니 이 정도로도 버틸 만하다. **1개로 가면 이 설정은 "디스크와 백업이 같이 죽는" 구조가 된다.** 최대 12시간치를 잃는 것(RPO 12h)도 감수해야 한다. 1개로 간다면 S3 호환 저장소로 내보내는 `--etcd-s3` 설정이 필수다. 복구할 때는 서버 토큰(`/var/lib/rancher/k3s/server/token`)도 같이 있어야 하니 토큰도 백업해야 한다([K3s Backup and Restore](https://docs.k3s.io/datastore/backup-restore)).

### 3-4. 운영 난이도

1개의 진짜 장점은 성능이 아니라 **실수할 거리가 없어진다는 것**이다. 3개 구성에는 이런 함정이 있다.

- 멤버를 교체할 때는 **반드시 "제거 후 추가"** 순서다. 3개 중 1개가 죽은 상태에서 새 멤버를 먼저 추가하면 쿼럼이 3으로 올라간다. 그 새 멤버가 못 붙으면 쿼럼이 영구 손실된다([etcd FAQ](https://etcd.io/docs/v3.5/faq/)).
- 무선 표는 끊길 때마다 피어 재연결과 따라잡기를 하고, 그 흔적이 전송 실패 카운터에 쌓인다.
- 타이머를 넉넉하게 잡으면 오탐은 줄지만 장애 감지는 느려진다.

이 블로그에도 3노드 etcd에서 유령 멤버나 `cluster-reset`으로 고생한 기록이 여러 편 있다. 1개 구성에서는 이런 종류의 사고가 구조적으로 생기지 않는다.

---

## 4. 3 → 1로 줄인다면

K3s에서 멤버를 줄이는 정석은 남길 서버에서 `--cluster-reset`을 쓰는 것이다. 이 플래그는 "모든 피어를 잊고 새 클러스터의 유일한 멤버가 된다"([K3s server CLI](https://docs.k3s.io/cli/server)). 데이터를 지우는 게 아니라 **멤버십만 1로 리셋**한다. 공식 복구 절차도 "리셋한 노드를 다시 띄우고, 나머지 etcd 서버는 `server/db`를 지운 뒤 재가입"하는 구조다([K3s etcd-snapshot — Restoring](https://docs.k3s.io/cli/etcd-snapshot)).

이 클러스터에 맞춰 순서를 적으면 이렇다.

1. **남길 노드를 고른다.** 실측으로는 **ilwon**이 답이다. 현재 리더이고, NVMe에 fsync 평균 2.3ms, 유선 본딩, 12코어다. lemuel은 디스크가, solomon은 망이 약점이다.
2. 실행 전에 `k3s etcd-snapshot save`로 스냅샷을 찍는다. **스냅샷과 토큰을 클러스터 밖으로 복사한다.**
3. 로컬 PV에 묶인 파드가 어느 노드에 있는지 먼저 확인한다. etcd를 줄여도 파드는 안 옮겨지지만, 서버를 agent로 바꾸는 과정에서 그 노드가 재시작된다.
4. 다른 노드들의 `config.yaml`에 `server: https://192.168.219.101:6443`(lemuel)이 박혀 있으니 접속 주소를 바꿔야 하는지 점검한다.
5. 리셋 후 lemuel과 solomon은 agent로 재가입시켜 **워커**로 쓴다. 무선 연구 조건은 그대로 유지된다.

사용자가 처음 말한 "컨트롤 플레인 1 + etcd 1"을 서로 다른 노드에 따로 두는 것(K3s의 etcd 전용 / control-plane 전용 역할 분리)도 가능하다. 하지만 이 경우 노드 둘 중 **하나만 죽어도** API가 멈춘다. 장애점이 하나에서 둘로 늘어나는 셈이다. Kubernetes 문서도 etcd를 분리하는 외부 etcd 토폴로지는 HA를 위해 "control-plane 3대 + etcd 3대"를 전제로 설명한다([Kubernetes: Options for HA Topology](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ha-topology/)). **1+1을 한다면 같은 노드에 두는 게 낫다.**

---

## 5. 결론

- **"3개 = 안전, 1개 = 위험"은 반만 맞다.** 지금의 3개는 "무선 표 하나를 낀 3개"라서, 유선 노드가 빠지는 순간 품질이 무선 링크에 묶인다.
- **1개의 이득은 성능보다 단순함이다.** 70MB짜리 etcd에서 쓰기 지연 차이는 체감하기 어렵다. 대신 멤버십 사고라는 범주 하나가 통째로 사라진다.
- **1개의 대가는 백업 체계다.** 지금처럼 스냅샷이 로컬 `file://`에만 있는 상태로 1개로 가면 안 된다. 외부 저장소와 토큰 백업이 선행 조건이다.
- 운영 서비스(이 클러스터에서는 settlement 등)가 올라가 있는 동안에는 3개를 유지하는 쪽이 맞다. **순수 개발·실험 클러스터로 바꾼다면 1개(ilwon)로 줄이는 건 합리적이다.**

### 근거의 한계

- 위 지표는 단일 시점의 누적값이고, solomon은 lemuel·ilwon보다 4일 늦게 기동해 누적 기간이 다르다.
- 3-2절의 쓰기 지연은 평균값을 넣은 단순 모델이다. 이 클러스터에서 3개와 1개를 같은 부하로 비교 측정한 결과는 없다.
- etcd 성능 비교 중에 같은 하드웨어에서 3개와 1개를 비교한 중립적인 제3자 헤드투헤드 측정은 찾지 못했다.

---

## References

1. etcd Authors, *FAQ* — 홀수 멤버, 장애 내성 표, 멤버 교체 순서. <https://etcd.io/docs/v3.5/faq/>
2. etcd Authors, *Tuning* — heartbeat-interval·election-timeout 권장치, 디스크 지연. <https://etcd.io/docs/v3.5/tuning/>
3. etcd Authors, *Hardware recommendations* — 디스크·네트워크 요구사항, 클러스터 규모 구분. <https://etcd.io/docs/v3.5/op-guide/hardware/>
4. etcd Authors, *Metrics* — `has_leader`, `wal_fsync_duration_seconds`, `peer_round_trip_time_seconds` 정의. <https://etcd.io/docs/v3.5/metrics/>
5. D. Ongaro, J. Ousterhout, *In Search of an Understandable Consensus Algorithm (Raft)*, USENIX ATC 2014. <https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro>
6. K3s Project, *High Availability Embedded etcd*. <https://docs.k3s.io/datastore/ha-embedded>
7. K3s Project, *Managing Server Roles* — etcd 전용 노드. <https://docs.k3s.io/installation/server-roles>
8. K3s Project, *k3s etcd-snapshot* — 기본 스케줄·보존, S3, 복구 절차. <https://docs.k3s.io/cli/etcd-snapshot>
9. K3s Project, *server CLI* — `--cluster-reset`. <https://docs.k3s.io/cli/server>
10. K3s Project, *Backup and Restore* — 토큰 백업 필요. <https://docs.k3s.io/datastore/backup-restore>
11. Kubernetes Authors, *Options for Highly Available Topology*. <https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ha-topology/>
