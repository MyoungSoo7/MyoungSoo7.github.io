---
layout: post
title: "K3s flannel cross-node 가 안 될 때 — ufw 8472/UDP 함정"
date: 2026-05-11 19:30:00 +0900
categories: [infra, kubernetes, k3s, networking]
tags: [k3s, flannel, vxlan, ufw, networking, troubleshooting, kubernetes]
---

K3s 클러스터에서 Pod-to-Pod 통신이 안 됐습니다. cross-node Service DNS 도 안 됐고, ClusterIP 로 가는 TCP 도 timeout. 처음에는 NodeLocal DNS 의 문제라고 생각했는데, 진짜 원인은 **ufw 가 flannel VXLAN port 8472/UDP 를 막고 있었던 것** 이었습니다. 한 노드만 그래도 클러스터 전체가 망가집니다.

> 이 글에서 다루는 것
> - 증상: cross-node Pod-to-Pod TCP / DNS 가 timeout
> - 잘못된 가설들 (DNS, kube-proxy)
> - 진짜 원인 — ufw 가 8472/UDP 차단
> - K3s/flannel 노드가 열어야 할 표준 포트 6개
> - 진단 명령어 (one-liner)

---

## 1. 증상 — 모든 cross-node 통신 fail

운영중 K3s 5 노드 클러스터에서:

```bash
$ kubectl exec -n cost-prod cost-app-xxxx -- nc -zvw3 cost-postgres 5432
# command terminated with exit code 1
```

`cost-postgres` Service 는 같은 namespace 안에 있는데도 TCP connection timeout. DNS lookup 도:

```bash
$ kubectl exec -n cost-prod cost-app-xxxx -- getent hosts cost-postgres
# exit code 2 (no result)
```

같은 노드에 있는 Pod 끼리는 잘 됨. **cross-node 만 안 됨.** Spring Boot 가 HikariCP 에서 PostgreSQL 못 잡고 21초 후 실패:

```
WARN  --- HikariPool-1: The connection attempt failed.
ERROR --- PSQLException: Unable to obtain isolated JDBC connection
```

---

## 2. 헛다리 1 — NodeLocal DNS 가 문제다

`ConfigMap node-local-dns` 의 Corefile 보니 `bind 169.254.20.10` 만 잡고 있고 cluster DNS IP `10.43.0.10` 으로는 listen 안 함. NodeLocal Pod 도 link-local IP 만 listen.

```bash
$ ss -ulnp | grep ':53'
UNCONN 169.254.20.10:53   users:("node-cache")    ← 이거만
UNCONN 127.0.0.54:53      users:("systemd-resolve")
UNCONN 127.0.0.53:53      users:("systemd-resolve")
```

"이거구나" 싶어서 NodeLocal ConfigMap 손대고, DaemonSet 재시작하고, link-local interface `nodelocaldns` 가 DOWN 상태인 거 발견해서 `ip link set up` 도 시도. **여전히 안 됨.**

→ 헛다리. DNS 가 안 가는 게 아니라 그 *전 단계 네트워크 자체* 가 안 통하는 거였음.

---

## 3. 헛다리 2 — kube-proxy iptables NAT rule

ServiceIP `10.43.x.x` 패킷이 kube-proxy 의 iptables rule 로 Pod IP 로 DNAT 되는데, 그 rule 이 깨졌나? 확인:

```bash
$ iptables -t nat -L KUBE-SERVICES | grep cost-postgres
KUBE-SVC-XXXXX  tcp  --  0.0.0.0/0  10.43.52.150  /* cost-prod/cost-postgres */ tcp dpt:5432
```

룰 있음. 정상. kube-proxy 도 동작 중. 또 헛다리.

---

## 4. 진짜 원인 — ufw 8472/UDP 차단

flannel CNI 는 노드 간 통신에 **VXLAN over UDP port 8472** 를 씁니다.
Pod CIDR (`10.42.0.0/16`) 의 패킷이 다른 노드로 가려면, 호스트가 그 패킷을 VXLAN 으로 encapsulate 해서 8472/UDP 로 다른 노드에게 보냅니다.

→ **만약 한 노드의 ufw 가 8472/UDP 를 차단하면 cross-node 통신 전부 실패.**

확인:

```bash
$ ssh solomon "sudo ufw status numbered"
Status: active

     To                  Action      From
     --                  ------      ----
[ 1] 22                  ALLOW IN    192.168.0.0/16
[ 2] 9100                ALLOW IN    192.168.0.0/16
[ 3] 2049                ALLOW IN    [내부LAN]   # NFS
[ 4] 111                 ALLOW IN    [내부LAN]   # NFS
[ 5] 30432               ALLOW IN    192.168.0.0/16     # NodePort
```

★ **8472 가 없습니다.** SSH/node_exporter/NFS/NodePort 만 열려있고, K3s 자체가 필요한 포트가 빠짐.

다른 노드 (르무엘 control-plane) 도 보니 일부 노드 IP 만 명시적으로 8472 허용:

```
[14] 8472/udp  ALLOW IN  [LAN노드]  # k3s-flannel
[17] 8472/udp  ALLOW IN  [LAN노드]  # k3s-flannel david
[21] 8472/udp  ALLOW IN  [LAN노드]  # flannel ilwon
```

→ 솔로몬(108), 루이스(109) IP 가 빠져있음. 노드 추가 시 ufw rule 갱신 안 한 결과.

---

## 5. K3s/flannel 노드가 열어야 할 표준 포트

각 노드에 다음 5 개를 LAN 에서 허용하면 cluster 작동:

```bash
# K3s API server (control-plane 노드만)
sudo ufw allow from [내부LAN] to any port 6443 proto tcp \
  comment 'K3s API'

# kubelet (모든 노드)
sudo ufw allow from [내부LAN] to any port 10250 proto tcp \
  comment 'kubelet'

# flannel VXLAN (모든 노드, 가장 중요)
sudo ufw allow from [내부LAN] to any port 8472 proto udp \
  comment 'flannel VXLAN'

# Pod CIDR — Pod 가 호스트 통해 다른 노드와 통신
sudo ufw allow from 10.42.0.0/16 \
  comment 'Pod CIDR'

# Service CIDR — Service ClusterIP traffic
sudo ufw allow from 10.43.0.0/16 \
  comment 'Service CIDR'

sudo ufw reload
```

> 💡 wireguard 백엔드를 쓴다면 `51820/UDP` 와 `51821/UDP` 도 열어야 합니다.

---

## 6. 적용 후 즉시 회복

5 노드 모두 위 rules 추가 → ufw reload → **즉시 cross-node 통신 회복**:

```bash
$ kubectl exec -n cost-prod cost-app-xxxx -- sh -c \
    'timeout 3 bash -c "</dev/tcp/cost-postgres/5432" && echo OK'
OK
```

cost.lemuel.co.kr 도 502 → 200 OK.

---

## 7. 진단 — 5분 안에 ufw 가 원인인지 확인

```bash
# 1. 같은 노드의 다른 Pod 와는 통신 되나?
kubectl exec POD -- nc -zvw3 SAME-NODE-POD-IP PORT

# 2. 다른 노드의 Pod 와는?
kubectl exec POD -- nc -zvw3 CROSS-NODE-POD-IP PORT

# 3. 같은 노드 = OK, cross-node = timeout 이면 flannel 의심

# 4. 노드에서 다른 노드로 udp 8472 도달 확인
ssh NODE1 "nc -u -zvw3 NODE2 8472"

# 5. ufw rules 점검
ssh NODE2 "sudo ufw status | grep 8472"
```

같은 노드는 OK + cross-node 만 fail = flannel encapsulation 문제. ufw 8472 가 가장 흔한 원인.

---

## 8. 추가 함정 — ufw 가 active 인데도 active 라고 표시 안 됨

K3s 가 설치되면 `iptables` 룰을 호스트 전역에 작성하는데, 그 룰 중 일부가 ufw 정책을 우회합니다. 그래서:

- `ufw status` 가 `active` 라고 나오지만 일부 K3s 트래픽은 그냥 통과
- 또는 K3s 설치 시 ufw 가 자동 비활성화되는 경우도 있음

ufw 와 K3s 같이 쓸 때는 **항상 위 5개 rules 명시적으로 추가** 하는 게 안전합니다.

---

## 9. 회고 — 디버깅 시간 분배

이번 트러블슈팅 시간:
- NodeLocal DNS 의심 (헛다리): 1시간
- iptables / kube-proxy 확인: 30분
- ufw 발견: 10분 ★
- 5 노드 fix + 검증: 20분

처음부터 ufw 봤으면 30분 안에 끝났을 일.

**홈랩 K3s 새 노드 추가할 때 체크리스트**:

```
[ ] ufw 6443/tcp from LAN (control-plane 만)
[ ] ufw 10250/tcp from LAN
[ ] ufw 8472/udp from LAN ★
[ ] ufw allow from 10.42.0.0/16
[ ] ufw allow from 10.43.0.0/16
[ ] ufw reload
[ ] kubectl get nodes 에서 Ready 확인
[ ] cross-node nc -zvw3 5432 테스트
```

이 한 장만 챙기면 같은 함정에 다시 빠질 일 없습니다.

---

## 다음 글

- **K3s ghcr private 패키지 — PAT vs Public 변경, 어느 게 표준?**
- 같은 날 빠진 다른 함정.
