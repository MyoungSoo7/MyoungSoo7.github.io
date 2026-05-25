---
layout: post
title: "kubeconfig 가 가리킨 control-plane 이 죽었다 + etcd 가 *죽은 멤버에게 raft heartbeat* 를 보내느라 클러스터가 2초씩 느려졌다"
date: 2026-05-26 02:00:00 +0900
categories: [infra, kubernetes, etcd, postmortem]
tags: [k3s, kubeconfig, etcd, raft, control-plane, homelab, postmortem, etcdctl]
---

`kubectl get nodes` 가 `dial tcp 192.168.219.110:6443: connect: host is down` 으로 죽었다. 어제 살려놨던 클러스터가 다시 안 보였다. 두 시간 뒤 알아낸 것: *클러스터는 멀쩡했다*. 단지 **내 kubeconfig 가 죽은 노드 한 대를 가리키고 있었을 뿐이었고**, 그 노드를 갈아끼고 나니 새 문제가 보였다 — *남은 etcd 멤버 한 대가 ghost 였고, 살아있는 두 멤버가 ghost 에게 raft heartbeat 보내려다 버퍼가 가득 차서 클러스터 전체가 2초씩 느려지고 있었다*.

이 글은 그 두 시간을 *진단 가능한 형태로* 정리한다. 비슷한 상황에서 *어디부터 의심해야 하는지* 가 핵심.

---

## TL;DR

| 증상 | 원인 | 수정 |
|---|---|---|
| `kubectl` 이 `host is down` | kubeconfig server 가 죽은 노드 .110 (ilwon) | server URL 을 살아있는 control-plane (.101 lemuel) 로 변경 |
| 노드 NotReady 가 *서로 자리 바꿔가며* 발생 | etcd 가 ghost 멤버 .110 에게 raft heartbeat 무한 재시도 → raft buffer full → 모든 etcd I/O 가 2초씩 지연 → lease 갱신 실패 → kubelet NotReady | ghost 노드(ilwon) 본체에서 직접 부팅 (전원 OFF 였음). 살아나니 raft 동기화되어 자연 회복 |
| `k3s` 에는 `etcdctl` 미포함 | k3s 가 etcd 를 *embed* 하지만 control 도구는 빼고 빌드 | `etcd-v3.5.21-linux-amd64.tar.gz` 별도 다운로드 |
| ECK·TTS 등 *전혀 무관한* 서비스들이 같이 멈춤 | 멈춘 게 아니라 *느린 etcd* 가 controller manager leader election 까지 잃게 만들어서 reconcile 이 멈춰 보였음 | etcd 정상화 후 자연 회복 |

---

## 1. *''kubectl 이 안 됨''* 의 첫 분기

```bash
$ kubectl get nodes
Unable to connect to the server: dial tcp 192.168.219.110:6443: connect: host is down
```

여기서 *내 첫 의심* 은 *클러스터가 죽었다* 였다. 잘못된 가정. **kubeconfig 는 control-plane 한 대만 가리킨다**. 가리킨 그 한 대가 죽어도, 다른 control-plane 은 살아있을 수 있다.

확인 방법:

```bash
$ grep server: ~/.kube/config
    server: https://192.168.219.110:6443

# 다른 control-plane 후보 ping
$ for IP in 192.168.219.101 192.168.219.108 192.168.219.110; do
    nc -z -G 1 $IP 6443 && echo "$IP api alive" || echo "$IP dead"
  done
192.168.219.101 api alive
192.168.219.108 dead
192.168.219.110 dead
```

.101(lemuel) 만 살아있었다. 갈아끼면 끝:

```bash
$ cp ~/.kube/config ~/.kube/config.bak.$(date +%s)
$ sed -i.tmp 's|server: https://192.168.219.110:6443|server: https://192.168.219.101:6443|' ~/.kube/config
$ kubectl get nodes
NAME      STATUS                     ROLES                AGE   VERSION
david     Ready                      <none>               21h   v1.35.4+k3s1
ilwon     Ready                      control-plane,etcd   15d   v1.35.4+k3s1   # ← !!!
lemuel    Ready,SchedulingDisabled   control-plane,etcd   34d   v1.35.4+k3s1
louise    Ready                      <none>               14d   v1.35.4+k3s1
solomon   NotReady                   control-plane,etcd   14d   v1.35.4+k3s1
```

`kubectl` 은 살아났다. 그런데 *ilwon Ready* 라고 표시된다. 어떻게 *.110:6443 이 dead* 인데 *ilwon Ready* 일 수 있나? — 답: **node Ready 는 *지금* 의 사실이 아니라 *마지막 heartbeat* 의 사실**. kubelet 이 30초 마다 heartbeat 를 쏘는데, 그 사이에 노드가 죽으면 *몇 분 동안 Ready 라고 보인다*. 노드 컨트롤러가 *5분 grace period* 후에 NotReady 로 마킹.

> *교훈 1*: `STATUS Ready` 와 *''지금 살아있다''* 는 다른 명제. *마지막 heartbeat 시각* (`kubectl describe node X | grep LastHeartbeat`) 까지 봐야 진짜 상태를 안다.

---

## 2. *''왜 노드들이 서로 자리 바꾸며 NotReady 가 되나''*

ilwon 이 NotReady 였다가 다시 Ready 가 되더니, 이번엔 solomon 이 NotReady. solomon 살아나니 louise 가 NotReady. *번갈아 가며* 깨지는 패턴.

처음엔 *''WiFi 가 불안정한가''* 라고 의심했다. 하지만 모든 노드가 동시에 WiFi 가 흔들릴 리는 없다.

다음 단서는 `kubectl describe node` 의 condition:

```
Ready   Unknown   Mon, 25 May 2026 15:55:19 +0900   NodeStatusUnknown   Kubelet stopped posting node status.
```

*''kubelet stopped posting''* 은 *kubelet 이 죽었다* 가 아니라 *kubelet 의 *heartbeat 가 API server 까지 못 닿았다*. API server 입장에서는 노드가 보이지 않는다.

다음 단서는 lemuel(현재 leader) 의 k3s 로그:

```
{"level":"warn","ts":"2026-05-25T15:58:15.606Z","caller":"v3rpc/interceptor.go:202",
 "msg":"request stats","time spent":"4.996854979s",
 "request content":"key:\"/registry/leases/kube-system/kube-scheduler\" limit:1 "}
{"level":"warn","ts":"2026-05-25T15:58:15.641Z","caller":"rafthttp/peer.go:254",
 "msg":"dropped internal Raft message since sending buffer is full",
 "remote-peer-id":"e08783cfcc895f20","remote-peer-name":"pipeline",
 "remote-peer-active":false}
E0525 leaderelection.go:452 "Error retrieving lease lock" err="context deadline exceeded"
"k3s-cloud-controller-manager"
I0525 leaderelection.go:299 "Failed to renew lease" lock="kube-system/k3s-cloud-controller-manager"
```

세 가지가 동시에 나타났다:
1. **5초** 짜리 `/registry/leases/kube-system/kube-scheduler` range read — etcd 가 *극도로* 느리다
2. **dropped Raft message** — etcd 가 ghost peer 에게 heartbeat 못 보내고 버퍼가 가득 참
3. **cloud-controller leaderelection lost** — leader election 도 etcd 위에 동작하는데 etcd 가 느려서 lease 갱신 실패

세 번째가 *''서로 자리 바꿔가며 NotReady''* 의 직접 원인이었다. *모든* lease 갱신이 5초씩 걸리니, *어느 노드든 가장 운 나쁜 갱신 시점* 에 NotReady 로 떨어진다. 다음 주기에는 다른 노드가 운 나쁜 차례.

그리고 그 *5초씩 걸리는 etcd I/O* 의 원인이 `dropped Raft message` 였다.

---

## 3. etcd 의 ghost member — `etcdctl` 가 k3s 에 없다

ghost peer ID `e08783cfcc895f20` 가 누구인지 알아야 했다. `etcdctl` 이 필요한데:

```bash
$ which etcdctl
# (없음)

$ sudo /usr/local/bin/k3s --help | grep -i etcd
etcd-snapshot    Manage etcd snapshots

$ sudo /var/lib/rancher/k3s/data/current/bin/etcdctl
sudo: command not found
```

**k3s 는 etcd 를 embed 하지만 `etcdctl` binary 는 포함하지 않는다.** 빌드 사이즈를 줄이려는 의도적 결정. 직접 받아야 한다:

```bash
$ curl -sL https://github.com/etcd-io/etcd/releases/download/v3.5.21/etcd-v3.5.21-linux-amd64.tar.gz -o /tmp/etcd.tgz
$ tar xzf /tmp/etcd.tgz -C /tmp
$ cp /tmp/etcd-v3.5.21-linux-amd64/etcdctl /tmp/etcdctl

$ sudo /tmp/etcdctl \
    --endpoints=https://127.0.0.1:2379 \
    --cacert=/var/lib/rancher/k3s/server/tls/etcd/server-ca.crt \
    --cert=/var/lib/rancher/k3s/server/tls/etcd/server-client.crt \
    --key=/var/lib/rancher/k3s/server/tls/etcd/server-client.key \
    member list -w table

+------------------+---------+------------------+------------------------------+
|        ID        | STATUS  |       NAME       |          PEER ADDRS          |
+------------------+---------+------------------+------------------------------+
| 84bb708329b5a819 | started | solomon-5068b1dd | https://192.168.219.108:2380 |
| e08783cfcc895f20 | started |   ilwon-b2c6a1ee | https://192.168.219.110:2380 |
| e5ff91e8e2ce2970 | started |  lemuel-d2eb1a27 | https://192.168.219.101:2380 |
+------------------+---------+------------------+------------------------------+
```

ghost peer ID `e08783cfcc895f20` 가 **ilwon** 이다. *''pipeline''* 이라는 이름은 멤버 이름이 아니라 *raft transport stream type* (pipeline vs stream). 로그가 *''remote-peer-name: pipeline''* 이라고 했을 때 *peer 의 이름이 pipeline* 인 게 아니라 *''pipeline 채널을 통해 ID e0… 에게 보낸 메시지가 drop 됐다''* 는 의미.

> *교훈 2*: rafthttp 로그의 `remote-peer-name` 은 *peer 의 hostname* 이 아니라 *raft transport channel name* (`pipeline`/`stream`). peer 확인은 `member list` 와 `remote-peer-id` 로.

---

## 4. ghost 제거 vs ghost 살리기 — 둘 중 뭐가 안전한가

ilwon 이 ghost 인 채로 두 멤버 (lemuel + solomon) 가 잘 돌아가긴 했다. *quorum 은 정상* (2/3). 그런데 etcd 가 *5초씩 느려져서* leader election 까지 잃고 있다.

두 옵션:

**A) ghost ilwon 을 etcd 멤버에서 제거**

```bash
$ etcdctl member remove e08783cfcc895f20
```

장점: raft buffer overflow 즉시 해소.
**단점: 2-member etcd 가 된다 — quorum=2 라서 *두 멤버 모두* 살아있어야 동작. 한 대 더 죽으면 cluster down.**

**B) ghost 살리기 — ilwon 본체를 다시 켠다**

장점: 3-member quorum 유지. 1 노드 fault tolerance.
**단점: ilwon 본체에 접근 가능해야 함.**

B 가 정답이지만 *전제 조건* 이 있다: ilwon 본체에 *물리적으로* 갈 수 있어야 한다. 홈랩이라서 가능했다. production 클라우드라면 *그 노드 인스턴스를 다시 시작* 해야 한다.

ilwon 의 케이스에서는 *전원이 꺼져 있었다*. *리셋 버튼* (작은 빨간 사각형) 이 아니라 *전원 버튼* (큰 빨간 사각형) 을 눌러야 한다는 사실을 사진으로 확인한 후 켰다. 부팅 35초 후 etcd quorum 정상화, etcd 응답 *2초 → 100ms 미만* 으로 회복. 자동으로 *번갈아 NotReady* 패턴도 사라졌다.

> *교훈 3*: ghost 멤버 *제거* 는 *복원 가능성이 0 일 때만*. 잠시 unreachable 한 노드는 *멤버로 두고 본체를 살리는 게* 거의 항상 정답.

---

## 5. *''관계없어 보이는 서비스들이 같이 멈춘 이유''*

ECK operator, Tempo, TTS, fluent-bit — *어제 사건* 의 잔재로 보였던 것들이 갑자기 또 죽어 보였다. 그런데 사실은 죽은 게 아니었다.

기전:

```
etcd 느림 (5초씩 range read)
   ↓
controller-manager leader election lease 갱신 실패
   ↓
controller-manager 가 leadership lost → 모든 reconcile 중지
   ↓
deployment / statefulset / replicaset controller 가 잠시 멈춤
   ↓
사용자 시점: pod 재시작 안 됨, scale-up 안 됨, image 안 받음
   ↓
"서비스가 죽었다" 라고 잘못 읽힘
```

즉 *서비스 자체* 는 멀쩡하고 *그 위의 control loop* 가 일시 정지한 상황. etcd 가 회복되면 *수 분 안에* control loop 가 다시 돌고, 그 동안 밀린 변화가 한꺼번에 반영된다 (그래서 ArgoCD apps 가 한꺼번에 Progressing 으로 표시됨).

> *교훈 4*: 클러스터의 *''여러 서비스가 동시에 망가졌다''* 는 신호는 *control-plane 자체* 를 의심하는 게 첫 단계. 각 서비스의 직접 원인을 파헤치기 전에 `etcdctl endpoint status -w table` 부터 본다.

---

## 6. 이런 사고를 *덜* 겪기 위한 영구 조치

### 6.1 kubeconfig 를 *load-balanced endpoint* 로

지금: `server: https://192.168.219.110:6443` — 한 노드 가리킴.

권장: `server: https://k3s-api.lemuel.local:6443` (DNS 라운드 로빈) 또는 HAProxy/keepalived VIP. 한 노드 죽어도 클라이언트는 모름.

k3s 단순화: `server: https://k3s-api:6443` 를 `/etc/hosts` 에 *모든 control-plane IP* 로. 첫 번째가 죽으면 SSH/TCP retry 가 다음 IP 로 시도 (단, kubectl 은 *재시도 X* 라 별도 wrapper 필요).

### 6.2 *''dropped Raft message''* 알람화

PrometheusRule:

```yaml
- alert: EtcdRaftMessageDropped
  expr: rate(etcd_network_peer_sent_failures_total[5m]) > 0.1
  for: 5m
  labels:  { severity: critical }
  annotations:
    summary: "etcd is dropping raft messages — peer unreachable"
    runbook: "Check if member is ghost. Decide: remove member OR revive node."
```

이 알람이 *어제 사건* 에서 5분 안에 떴다면 *kubeconfig 의심* 단계를 건너뛰고 바로 ilwon 본체 점검으로 갔을 것.

### 6.3 etcdctl 을 *모든 control-plane 에 미리 설치*

```bash
# Ansible 또는 cloud-init 에 추가
curl -sL https://github.com/etcd-io/etcd/releases/download/v3.5.21/etcd-v3.5.21-linux-amd64.tar.gz \
  | tar xz --strip-components=1 -C /usr/local/bin etcd-v3.5.21-linux-amd64/etcdctl
```

장애 발생 *후에* 다운로드하는 건 *느리고 위험* (NTP·DNS·CDN 셋 다 의존). 평상시에 설치해두기.

### 6.4 *전원 버튼 위치* 가 명확하지 않은 노드는 *전원 사진 + 라벨링*

ilwon 의 본체 사진을 보내달라고 했을 때, *작은 빨간 사각형* 과 *큰 빨간 사각형* 둘 다 보였다. 어느 게 전원이고 어느 게 리셋인지가 *디버깅의 중요한 단계* 였다. 작은 게 리셋, 큰 게 전원이라는 일반 규칙은 있지만 *케이스마다 다르다*. 라벨링 한 번 해두는 게 *5분의 헛수고* 를 막는다.

---

## 7. 마무리

이 사건의 *주관적 어려움* 은 *증상이 너무 많아서* 였다. *''kubectl 안 됨''* → *''노드가 번갈아 NotReady''* → *''서비스 12개 OutOfSync''* → *''etcd 느림''* — *5 단계의 증상* 이 보였는데 *진짜 원인* 은 *맨 마지막 한 줄* (ghost member) 이었다. 그 사이 *4 단계* 는 *증상의 증상의 증상* 이었다.

> *''여러 게 동시에 망가졌다''* 는 *원인이 여러 개* 가 아니라 *하나의 원인이 여러 곳에 보이는* 신호다. *공통 원인* 을 찾는 게 *각 증상을 따로 고치는* 것보다 빠르다.

다음 글에서는 — 이 사건의 직접 후속으로 — *DHCP 가 매번 IP 를 바꿔서 노드 이름이 안 굳는 홈랩에서 NetworkManager 로 wired+wireless 같은 정적 IP 를 박는 방법* 을 정리한다.

---

> 작성: 2026-05-26. 환경: K3s v1.35.4 (embedded etcd v3.5), 5 노드 (lemuel, ilwon, solomon = control-plane; louise, david = worker). etcdctl v3.5.21 별도 다운로드.
