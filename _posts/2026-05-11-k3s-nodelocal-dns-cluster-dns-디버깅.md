---
layout: post
title: "K3s NodeLocal DNS — Pod 가 Service 이름을 못 풀 때, 진짜 원인은 forward loop"
date: 2026-05-11 23:30:00 +0900
categories: [infra, kubernetes, k3s, networking, dns]
tags: [k3s, node-local-dns, coredns, dns, kube-dns-upstream, troubleshooting, kubelet]
---

오늘 K3s 5 노드 클러스터에서 Pod 가 Service 이름을 DNS resolve 못 하는 문제를 추적했습니다. 8 케이스 마이그를 IP 직접 사용으로 우회하고 있었는데, ArgoCD 자동 sync 가 같은 이유로 실패하는 걸 보고 근본 해결에 들어갔습니다. 진짜 원인은 NodeLocal DNS 의 **forward loop** 였습니다.

> 이 글에서 다루는 것
> - 증상: `getent hosts <service>` → exit=2, ClusterIP 해석 실패
> - 헛다리들 (ufw, ConfigMap bind, listen IP)
> - 진짜 원인: forward destination 이 자기 자신 IP
> - 해결: `kube-dns-upstream` Service 사용
> - kubelet `--cluster-dns` 변경 + 모든 노드 적용

---

## 1. 증상

K3s Pod 에서:

```bash
$ kubectl exec -n cost-prod cost-app-xxxx -- getent hosts cost-postgres
# 결과 없음 (exit code 2)
```

Service DNS 가 cross-namespace 도, 같은 namespace 도 안 됨. ClusterIP 직접 호출은 됨:

```bash
$ kubectl exec ... -- nc -zvw3 10.43.52.150 5432
OK
```

→ TCP 는 OK, **DNS 만 안 됨**.

---

## 2. 헛다리 1 — ufw flannel 8472

처음에는 cross-node 통신 자체가 안 됐었습니다. 솔로몬 ufw 가 flannel VXLAN port 8472/UDP 를 차단해서, 노드 간 패킷이 안 갔던 것. ufw 5 노드 모두 열어준 후 TCP 는 회복.

그러나 **DNS 는 여전히 fail**. ufw 문제가 아니었음.

---

## 3. 헛다리 2 — NodeLocal DNS Pod 의 listen IP

NodeLocal DNS DaemonSet 이 args 로 `-localip 169.254.20.10,10.43.0.10` 를 받아서 두 IP 모두 잡아야 함:
- 169.254.20.10: link-local (NodeLocal 표준)
- 10.43.0.10: cluster DNS Service IP (Pod resolv.conf 의 nameserver)

확인 결과:

```bash
$ ss -ulnp | grep ':53\b' | grep node-cache
UNCONN 169.254.20.10:53   users:(("node-cache"))    ← 이거만
                                                      10.43.0.10 은 listen X
```

Pod 의 resolv.conf 는 `10.43.0.10` 가리키는데 그 IP 에서 listen 안 함 → Pod → 호스트 routing → 빈 응답.

링크 인터페이스 `nodelocaldns` 가 DOWN 상태였습니다. 수동 UP → 인터페이스에 두 IP 잡혔지만, Pod (node-cache 프로세스) 가 ConfigMap Corefile 의 `bind 169.254.20.10` 만 보고 10.43.0.10 에는 bind 안 함.

이걸 고치려고 ConfigMap 의 bind 에 10.43.0.10 추가 시도 → **여전히 DNS 안 됨**.

→ 헛다리. listen IP 가 아니라 forward 가 문제.

---

## 4. 진짜 원인 — forward loop

NodeLocal Pod 로그 보니:

```
[ERROR] plugin/errors: 2 cost-postgres.cost-prod.svc.cluster.local. A:
        dial tcp 10.43.0.10:53: connect: connection refused
```

`connection refused`. NodeLocal Pod 가 forward destination 으로 `10.43.0.10` 으로 가는데, 그게 **자기 자신**:

```
                       NodeLocal Pod
       /etc/resolv.conf            Corefile
       nameserver 10.43.0.10  ──>  bind 169.254.20.10
                                   forward . 10.43.0.10 ──>  자기 자신
                                                              (loop)
```

Pod 가 10.43.0.10 으로 쿼리 → kube-proxy iptables → NodeLocal Pod 의 169.254.20.10 (NAT) → CoreDNS forward → 10.43.0.10 으로 또 보냄 → 또 자기 자신 → **connection refused** (왜냐면 NodeLocal 이 그 IP listen 안 함).

---

## 5. 해결 — kube-dns-upstream Service

K3s 의 NodeLocal 배포는 `kube-dns-upstream` 이라는 별도 Service 를 만들어 둡니다. 이게 진짜 백엔드 CoreDNS 를 가리키는 Service.

```bash
$ kubectl get svc -n kube-system kube-dns-upstream
NAME                TYPE        CLUSTER-IP      PORT(S)
kube-dns-upstream   ClusterIP   10.43.244.20    53/UDP,53/TCP
```

ConfigMap 의 forward 를 이 IP 로 변경:

```yaml
cluster.local:53 {
    ...
    bind 169.254.20.10
    forward . 10.43.244.20 {     # ← 10.43.0.10 → kube-dns-upstream
        force_tcp
    }
    ...
}
```

```bash
kubectl patch cm node-local-dns -n kube-system --type=merge \
  -p='{"data":{"Corefile":"...kube-dns-upstream IP..."}}'
kubectl rollout restart ds node-local-dns -n kube-system
```

---

## 6. Pod 가 NodeLocal 을 보도록 — kubelet `--cluster-dns`

NodeLocal 이 정상 동작해도, Pod 의 `resolv.conf` 가 `10.43.0.10` 가리키면 의미 없음. 그 IP 가 NodeLocal Pod 의 link-local 인터페이스로 NAT 되어야 하는데, K3s 의 iptables rule 이 그 redirect 를 안 만들어줍니다 (또는 만들어주지만 cross-node 문제로 실패).

가장 깨끗한 해결: Pod 가 직접 `169.254.20.10` 을 nameserver 로 사용하게 만들기.

`/etc/rancher/k3s/config.yaml`:

```yaml
kubelet-arg:
  - cluster-dns=169.254.20.10
```

이걸 **모든 5 노드** 에 적용 + `systemctl restart k3s` (또는 `k3s-agent`).

그 후 새로 만들어지는 Pod 의 resolv.conf:

```bash
nameserver 169.254.20.10
search <ns>.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

각 노드 자신의 NodeLocal Pod 로 바로 가니까 cross-node 트래픽 없음 (성능도 좋음).

---

## 7. 검증

```bash
$ kubectl exec -n cost-prod cost-app-xxxx -- getent hosts cost-postgres
10.43.52.150    cost-postgres.cost-prod.svc.cluster.local
$ echo $?
0
```

✅ cross-namespace, cross-node 모두 OK.

이제 차트의 `existing.host` 를 IP 직접 (`[내부VIP]:31788`) 에서 Service 이름 (`cost-postgres`) 으로 되돌릴 수 있고, ArgoCD 의 `argocd-application-controller` 가 `argocd-repo-server` DNS resolve 가능 → GitOps 자동 sync 활성화.

---

## 8. 회고 — 디버깅 시간 분배

1. ufw 8472 발견 (1시간)
2. NodeLocal listen IP 의심 (1시간)
3. Pod dnsConfig 시도 / nodelocaldns 인터페이스 UP (30분)
4. Corefile forward loop 발견 (15분)
5. kube-dns-upstream + kubelet-arg (30분)

**진짜 원인 (`forward 10.43.0.10` 이 자기 자신)** 까지 가는 데 너무 오래 걸렸음. 처음부터 NodeLocal Pod 로그 (`plugin/errors: connection refused`) 봤으면 30분 안에 끝났을 일.

---

## 9. K3s + NodeLocal 운영 체크리스트

```
[ ] DaemonSet 5 노드 모두 Running
[ ] nodelocaldns 인터페이스 UP (수동 또는 systemd hook)
[ ] ConfigMap Corefile forward 가 kube-dns-upstream Service IP
[ ] /etc/rancher/k3s/config.yaml: kubelet-arg cluster-dns=169.254.20.10
[ ] 모든 노드 K3s/k3s-agent 재시작
[ ] 새 Pod resolv.conf 가 169.254.20.10 가리키는지
[ ] getent hosts <svc>.<ns>.svc.cluster.local 동작 확인
```

이 체크리스트로 다음에 새 K3s 클러스터 구축할 때 30분 안에 NodeLocal 까지 정상화 가능합니다.

---

## 10. 부산물 — coredns 가 어디 있는지

운영 중 발견한 K3s 의 DNS 구조:

```
[Pod resolv.conf]                 [NodeLocal DNS]              [kube-dns-upstream]
nameserver 169.254.20.10  ─────>  link-local interface  ─────> ClusterIP Service
                                  (per-node DaemonSet)         │
                                                                ▼
                                                         [coredns Deployment]
                                                         (2 Pod, kube-system)
```

- 모든 Pod 는 자기 노드의 NodeLocal 만 봄 (cross-node 트래픽 ✅)
- NodeLocal 은 캐시. 미스 시 kube-dns-upstream → coredns Pod
- kube-dns-upstream 은 coredns Pod selector 의 Service (replicas 변경에도 영향 X)

이 흐름이 작동하면 DNS 의 **latency 50% 감소** + **kube-proxy iptables 부하 감소**. 홈랩 5 노드 정도면 체감 거의 없지만, 운영 클러스터에선 큰 차이가 납니다.

---

오늘은 이 한 문제로 4 시간을 썼지만, 다음 K3s 작업부터는 같은 함정에 안 빠질 거라 생각하면 가치 있는 시간이었습니다.
