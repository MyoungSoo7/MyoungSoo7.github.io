---
layout: post
title: "K3s + ufw — Ubuntu 노드 재부팅 후 cluster overlay 가 죽는 함정"
date: 2026-05-26 03:50:00 +0900
categories: [infra, kubernetes, networking]
tags: [k3s, flannel, vxlan, ufw, ubuntu, debugging, homelab]
---

새벽 3시. K3s 홈랩에서 *8개 *-prod 앱 pod 가 일제히 CrashLoopBackOff*. 모두 `SocketTimeoutException` — DB 연결 timeout. 모든 postgres 가 ilwon 노드에 있고, app 들은 louise 에 있다. *louise → ilwon* 의 *pod-to-pod overlay* 가 죽었다는 뜻.

진단 5단계를 거쳐서 진짜 범인을 찾았다 — **ufw**.

---

## 1. 증상 — node 는 다 Ready 인데 pod 통신만 죽음

```text
$ kubectl get nodes
NAME      STATUS   ROLES
david     Ready    <none>
ilwon     Ready    control-plane,etcd
lemuel    Ready    control-plane,etcd
louise    Ready    <none>
solomon   Ready    control-plane,etcd
```

```text
$ kubectl get pods -A | grep -v Running
asat-prod      asat-app-...      CrashLoopBackOff   50 (3m ago)   4h11m
cost-prod      cost-app-...      CrashLoopBackOff   51 (26s ago)  4h11m
crypto-prod    crypto-app-...    CrashLoopBackOff   50 (38s ago)  4h11m
fashion-prod   fashion-app-...   CrashLoopBackOff   50 (4m ago)   4h11m
jabis-prod     jabis-app-...     CrashLoopBackOff   50 (3m ago)   4h11m
sns-prod       sns-app-...       CrashLoopBackOff   49 (3m ago)   8h
sparta-prod    sparta-...        CrashLoopBackOff   47 (3m ago)   4h11m
trading-prod   trading-app-...   CrashLoopBackOff   49 (3m ago)   4h11m
```

8 개 다 같은 에러:

```text
Caused by: java.net.SocketTimeoutException: Connect timed out
	at java.base/sun.nio.ch.NioSocketImpl.timedFinishConnect(...)
	at org.postgresql.core.v3.ConnectionFactoryImpl.openConnectionImpl(...)
	at org.flywaydb.core.internal.jdbc.JdbcUtils.openConnection(...)
```

Spring Boot 가 Flyway 부팅 시점에 DB 못 잡고 죽는다.

---

## 2. 가설 1 — DB 가 죽었나? (틀림)

```text
$ kubectl get pods -A | grep postgres
asat-prod      asat-postgres-0       1/1 Running   0   12m   on ilwon
cost-prod      cost-postgres-0       1/1 Running   0   11m   on ilwon
crypto-prod    crypto-postgres-0     1/1 Running   0   11m   on ilwon
...                                                          ← 다 ilwon
```

postgres 는 다 Running. *하지만 모두 ilwon 위* 다. 그리고 ilwon 은 *직전에* NotReady 였다 (네트워크 작업 중 k3s 죽음). 12 분 전 k3s 재시작으로 *Ready 로 복귀*한 상태.

→ DB 자체는 살아있다. node 도 Ready 다. 그런데도 timeout.

---

## 3. 가설 2 — 노드 간 통신 자체가 죽었나? (반쯤 맞음)

ARP / 일반 ping 으로 확인:

```text
$ ping -c 3 10.0.0.110     # ilwon 의 host IP
3 packets transmitted, 3 received, 0.0% packet loss

$ ssh louise 'ping -c 3 10.0.0.110'
3 packets transmitted, 3 received, 0.0% packet loss
```

노드 간 *host network* 는 OK. *VXLAN UDP 8472* 도 outbound 는 열림:

```text
$ ssh louise 'nc -zvu -w 3 10.0.0.110 8472'
Connection to 10.0.0.110 8472 port [udp/*] succeeded!
```

→ 그런데 *pod-to-pod* 만 안 됨:

```text
$ kubectl run --rm -it --image=busybox --overrides='{"spec":{"nodeName":"louise"}}' nettest -- \
    nc -zv 10.42.4.164 5432
# 10.42.4.164 = asat-postgres 의 pod IP (ilwon 의 cni0/24 안)

(timeout)
```

→ flannel VXLAN tunnel 의 *payload* 가 안 흐른다. 노드 간 host 는 살아있지만 *overlay* 는 죽었다.

대조군:

```text
$ kubectl run --rm -it --image=busybox --overrides='{"spec":{"nodeName":"david"}}' nettest -- \
    nc -zv 10.42.4.164 5432
10.42.4.164 (10.42.4.164:5432) open
```

→ david → ilwon 는 됨. **louise ↔ ilwon 만** 안 됨.

---

## 4. 가설 3 — flannel FDB / VXLAN 상태? (정상)

VXLAN 동작 메커니즘:
1. pod 가 다른 노드 pod IP 로 트래픽 보냄
2. flannel.1 인터페이스가 packet 받음
3. FDB (Forwarding Database) 보고 *목적지 노드의 host IP* 알아냄
4. UDP 8472 로 *VXLAN encapsulation* 해서 외부 NIC 로 송신
5. 반대편 노드가 받아서 decap → cni0 → 목적지 pod

```text
$ ssh louise 'bridge fdb show dev flannel.1'
9e:55:de:c0:22:fa  dst 10.0.0.113  self permanent    # david
82:17:27:be:3a:20  dst 10.0.0.101  self permanent    # lemuel
3e:51:16:ff:31:8d  dst 10.0.0.110  self permanent    # ilwon ← 있음
16:c1:e6:9d:5b:50  dst 10.0.0.120  self permanent    # solomon

$ ssh louise 'ip neigh show dev flannel.1'
10.42.4.0  lladdr 3e:51:16:ff:31:8d PERMANENT             # ilwon subnet ← 있음
10.42.1.0  lladdr 9e:55:de:c0:22:fa PERMANENT             # david subnet
10.42.0.0  lladdr 82:17:27:be:3a:20 PERMANENT             # lemuel subnet
10.42.6.0  lladdr 16:c1:e6:9d:5b:50 PERMANENT             # solomon subnet

$ ssh louise 'ip route show | grep 10.42'
10.42.0.0/24 via 10.42.0.0 dev flannel.1 onlink
10.42.1.0/24 via 10.42.1.0 dev flannel.1 onlink
10.42.4.0/24 via 10.42.4.0 dev flannel.1 onlink     ← ilwon 라우트 있음
10.42.6.0/24 via 10.42.6.0 dev flannel.1 onlink
10.42.7.0/24 dev cni0 proto kernel scope link src 10.42.7.1
```

FDB, neighbor table, route table 다 정상. ilwon 측에서도 똑같이 louise 의 flannel.1 MAC (`fa:b8:6d:09:83:dd`) 가 잘 매핑되어 있음.

**그런데 packet 이 흐르지 않는다.**

대응 1: louise 재부팅. → 효과 없음. 같은 증상.
대응 2: k3s-agent 재시작. → 효과 없음. 같은 증상.

---

## 5. 진짜 범인 — louise 의 ufw

`iptables FORWARD` chain 을 들여다보다 발견:

```text
$ ssh louise 'sudo iptables -L FORWARD -n -v | head -20'
Chain FORWARD (policy DROP 0 packets, 0 bytes)
 pkts bytes  target
 6623 1405K  KUBE-ROUTER-FORWARD
 4287  257K  KUBE-PROXY-FIREWALL
 4287  257K  KUBE-FORWARD
 4286  257K  KUBE-SERVICES
 4286  257K  KUBE-EXTERNAL-SERVICES
 4278  257K  ACCEPT          # K8s 정책 통과한 트래픽
    8   480  DOCKER-USER
    8   480  DOCKER-FORWARD
    8   480  ufw-before-logging-forward      ← 여기
    8   480  ufw-before-forward
    8   480  ufw-after-forward
    8   480  ufw-after-logging-forward
    8   480  ufw-reject-forward              ← reject 행
    8   480  ufw-track-forward
    8   480  FLANNEL-FWD
```

`ufw-*` 체인이 K8s 체인 *뒤* 에 끼어들어있다. K8s 정책 통과한 패킷이 ACCEPT 대신 `ufw-reject-forward` 로 떨어진다.

확인:

```text
$ ssh louise 'sudo ufw status'
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
OpenSSH (v6)               ALLOW       Anywhere (v6)
```

**ufw 가 active. ALLOW 는 SSH 뿐.** VXLAN UDP 8472, kubelet 10250, 모든 pod-to-pod 트래픽 = *암묵적 deny*.

왜 갑자기 활성? 새벽에 *louise 를 재부팅* 했고, Ubuntu 의 ufw 는 *systemd 에서 enabled* 상태였다. 부팅 시 자동 활성. 평소엔 *부팅 안 했었던 거*.

```text
$ ssh louise 'sudo ufw disable'
Firewall stopped and disabled on system startup
```

즉시 회복:

```text
$ kubectl exec -n academy-staging academy-staging-admin-... -- nc -zv 10.42.4.164 5432
10.42.4.164 (10.42.4.164:5432) open
```

8 개 *-app pod 가 60 초 안에 다 Running 으로 복귀.

---

## 6. 왜 david/lemuel/solomon 은 안 막혔나

david 와 solomon 은 *그동안 재부팅 안 함*. ufw 는 *fresh install 직후* 잠시 활성이고 누군가 *그때 disable* 했었다. 그 후로 노드 재부팅이 없어서 그 상태가 유지된 거.

louise 만 *새벽에 재부팅* 했고, 그 순간 `systemctl enable ufw` 가 살아있던 상태 → 부팅 시 활성 → cluster 죽음.

**lesson:** `sudo ufw disable` 만 하면 *재부팅 후 다시 살아난다.* 영구 disable 은 `sudo systemctl disable ufw` 까지 해야 함.

---

## 7. 정리 — Ubuntu K3s 노드 첫 setup 체크리스트

```bash
# 노드 추가 직후 (또는 재부팅 후) 반드시
sudo ufw disable
sudo systemctl disable ufw

# 또는 ufw 유지하면서 K8s 포트 허용 (덜 안전, 더 복잡)
sudo ufw allow 6443/tcp           # K3s API
sudo ufw allow 8472/udp           # flannel VXLAN
sudo ufw allow 10250/tcp          # kubelet
sudo ufw allow 2379:2380/tcp      # etcd (control-plane only)
sudo ufw allow from 10.42.0.0/16  # pod CIDR
sudo ufw allow from 10.43.0.0/16  # service CIDR
```

K3s 공식 문서가 *firewalld / ufw 비활성을 권장*하는 이유 — Linux 디스트로마다 default 가 다르고 (Ubuntu 는 ufw, RHEL/CentOS 는 firewalld), 자동으로 K8s 트래픽 패턴을 알지 못한다.

---

## 8. 디버깅 cascade 요약

| 단계 | 가설 | 검증 결과 | 시간 |
|---|---|---|---|
| 1 | DB pod 죽음 | postgres 다 Running | 1m |
| 2 | 노드 간 통신 죽음 | host ping/SSH OK | 2m |
| 3 | flannel FDB 깨짐 | FDB·neigh 정상 | 5m |
| 4 | k3s-agent 캐시 | 재시작 효과 없음 | 5m |
| 5 | 노드 reboot | 효과 없음 | 5m |
| **6** | **ufw 활성** | **`ufw disable` 즉시 회복** | **30s** |

총 20 분. *마지막 30 초가 진짜 fix*. 그 전 19 분은 *정상인 걸 재확인하는 데* 다 썼다.

**이런 종류 디버깅을 줄이려면** — 노드 추가 *체크리스트* 에 `ufw disable + systemctl disable` 을 *맨 앞에* 적어두는 게 답. 다음 노드 추가 때 안 까먹게.
