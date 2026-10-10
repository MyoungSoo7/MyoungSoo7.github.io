---
layout: post
title: "[CS300 #160] 쿠버네티스 네트워킹 — Service·Ingress·CNI 를 앞선 19개 글로 읽기"
date: 2026-10-10 20:40:00 +0900
categories: [cs]
tags: [cs300, networking, kubernetes, cni, service, ingress]
---

컴퓨터공학 300 주제 시리즈의 160번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

쿠버네티스 네트워킹은 세 층이다. CNI 플러그인이 모든 파드에 고유 IP 를 주고 서로 NAT 없이 닿게 하고(파드 네트워크), Service 가 바뀌는 파드 집합 앞에 고정된 가상 IP 와 DNS 이름을 주며(L4), Ingress·Gateway API 가 HTTP 를 호스트·경로로 나눈다(L7).

## 왜 필요한가

쿠버네티스의 네트워킹은 새 기술이 아니다. 이 파트에서 다룬 서브넷, 라우팅, NAT, 터널, DNS, 로드 밸런싱을 조합한 것이다. 그래서 이 글을 파트의 마지막에 둔다. 앞의 개념을 알면 "Service IP 로 ping 이 안 된다", "파드끼리는 되는데 다른 노드 파드와는 안 된다", "Ingress 에서 502", "외부 서버 로그에 노드 IP 만 찍힌다" 같은 증상이 각각 어느 층의 이야기인지 바로 보인다.

## 핵심 개념

### 쿠버네티스 네트워크 모델

공식 문서가 정한 기본 규칙은 이렇다.

- 클러스터의 모든 파드는 클러스터 전체에서 고유한 IP 를 받는다.
- 파드 안의 컨테이너들은 네트워크 네임스페이스를 공유한다. 서로 `localhost` 로 닿는다.
- 모든 파드는 노드에 상관없이 다른 모든 파드와 프록시나 주소 변환(NAT) 없이 직접 통신할 수 있다.

쿠버네티스 자체는 이 규칙을 구현하지 않는다. 구현은 CNI 플러그인 몫이다.

### CNI: 파드 네트워크를 만드는 플러그인

CNI(Container Network Interface)는 컨테이너 런타임이 네트워크 플러그인을 부르는 규약이다. 명세(1.1.0)는 ADD, DEL, CHECK, STATUS, VERSION, GC 연산을 정의한다. 파드가 생기면 런타임이 플러그인을 ADD 로 부르고, 플러그인은 대략 이런 일을 한다.

```
노드 A                                        노드 B
┌─────────────────────────────┐               ┌──────────────────────────┐
│ 파드1 netns   파드2 netns    │               │ 파드3 netns               │
│  eth0          eth0          │               │  eth0                     │
│   │ veth쌍      │ veth쌍     │               │   │                       │
│  ─┴──── 브리지(cni0) ──┴──   │               │  ─┴── cni0 ──             │
│        │ 라우팅 표           │   노드 간 전달  │        │                  │
│      노드 eth0 ─────────────────(오버레이 또는 라우팅)────── 노드 eth0       │
└─────────────────────────────┘               └──────────────────────────┘
```

1. 파드의 네트워크 네임스페이스에 veth 한쪽 끝을 넣어 `eth0` 으로 만들고, 다른 끝은 노드에 둔다.
2. IPAM 으로 파드에 IP 를 준다. 보통 노드마다 파드 대역의 작은 서브넷(예: `/24`)을 나눠 준다(144번 글).
3. 다른 노드의 파드 대역으로 가는 길을 만든다. 방법은 크게 둘이다.
   - 오버레이: 파드 패킷을 VXLAN 이나 WireGuard 로 감싸 노드 IP 끼리 보낸다(158번 글). 기반 망을 건드리지 않아 어디서나 동작하지만 MTU 가 준다. flannel 의 기본 방식이다.
   - 라우팅: 노드가 "이 파드 대역은 저 노드로"라는 경로를 갖는다. 같은 L2 망이면 직접 경로(flannel host-gw), 아니면 BGP 로 경로를 광고한다(Calico, 145번 글).

Calico, Cilium 같은 플러그인은 여기에 NetworkPolicy(파드 간 방화벽)를 더한다. 기본적으로 모든 파드는 서로 통신할 수 있으므로, 격리가 필요하면 NetworkPolicy 로 막아야 한다. NetworkPolicy 를 지원하지 않는 플러그인에서는 정책을 만들어도 아무 효과가 없다.

### Service: 바뀌는 파드 앞의 고정 주소

파드는 재시작되면 IP 가 바뀐다. Service 는 레이블 셀렉터로 고른 파드 집합 앞에 고정된 가상 IP(ClusterIP)와 DNS 이름을 준다.

| 타입 | 동작 |
|---|---|
| ClusterIP | 클러스터 안에서만 닿는 가상 IP. 기본값 |
| NodePort | 모든 노드의 같은 포트(기본 범위 30000-32767)로 들어오면 Service 로 전달 |
| LoadBalancer | 외부 로드 밸런서를 붙여 외부 IP 를 받음. 클라우드나 MetalLB, k3s ServiceLB 가 제공 |
| ExternalName | DNS CNAME 만 돌려줌 |
| 헤드리스(clusterIP: None) | 가상 IP 없이 DNS 가 파드 IP 들을 직접 돌려줌 |

ClusterIP 는 어떤 인터페이스에도 붙어 있지 않은 주소다. 각 노드의 kube-proxy 가 EndpointSlice(준비된 파드 IP·포트 목록)를 지켜보다가, "이 가상 IP:포트로 가는 패킷은 이 파드들 중 하나로 DNAT 하라"는 규칙을 커널에 넣는다(146번 글). 모드는 iptables, nftables 가 있고, IPVS 모드는 v1.35 부터 폐기 예정(deprecated)으로 표시됐다. 규칙이 TCP·UDP 포트 단위라서 ClusterIP 로 ping(ICMP)을 보내면 보통 응답이 없다. 고장이 아니다.

Service 는 L4 다. 연결 단위로 파드를 고르므로 HTTP/2·gRPC 처럼 오래 사는 연결은 한 파드에 고정된다(157번 글).

### DNS

클러스터 DNS(보통 CoreDNS)는 Service 마다 `<서비스>.<네임스페이스>.svc.cluster.local` 이름을 만든다. 파드의 `/etc/resolv.conf` 에는 검색 도메인과 `ndots:5` 가 들어가 있어, 같은 네임스페이스에서는 `my-svc` 만으로도 풀린다. 대신 외부 이름 조회가 여러 번으로 불어날 수 있다(151번 글).

### Ingress 와 Gateway API: L7

Ingress 는 "호스트 `api.example.com` 의 `/v1` 경로는 Service A 로" 같은 HTTP 라우팅 규칙이다. 규칙만으로는 아무 일도 안 하고, Ingress 컨트롤러(nginx, Traefik 등)가 이를 읽어 L7 프록시를 구성한다. TLS 종료도 보통 여기서 한다(154번 글).

공식 문서는 Ingress API 를 동결(frozen)했다고 밝힌다. GA 상태로 유지되지만 새 기능은 Gateway API 에 들어간다. Gateway API 는 인프라 운영자(Gateway)와 앱 개발자(HTTPRoute 등)의 역할을 나눈 더 표현력 있는 후속 API 다.

### 패킷 하나의 여정

외부 사용자가 `https://api.example.com/v1/items` 를 부를 때를 앞 글들의 언어로 따라가 보자.

```
1. DNS: api.example.com → LoadBalancer 외부 IP (151)
2. TCP·TLS 핸드셰이크: 외부 IP → (L4 LB) → 노드의 Ingress 컨트롤러 파드 (147, 154, 157)
3. Ingress 컨트롤러가 TLS 종료, Host·경로 보고 Service A 선택 (152, 157)
4. 컨트롤러 → Service A 의 엔드포인트(파드 IP)로 새 연결 (150)
5. 그 파드가 다른 노드에 있으면 CNI 가 오버레이로 감싸 노드 간 전달 (158)
6. 응답은 역순. 파드가 외부 API 를 부르면 노드 IP 로 SNAT 되어 나감 (146)
```

## 직접 해 보기

kube-proxy 의 iptables 모드는 엔드포인트가 n 개일 때, 첫 규칙을 확률 1/n, 다음을 1/(n−1), …, 마지막을 1 로 두어 결과적으로 균등하게 고른다. 이를 흉내 내고, 준비되지 않은 엔드포인트를 빼는 것과 파드별 서브넷 할당도 계산해 본다. 주소는 예시용 사설 대역이다.

```python
import random, ipaddress
from collections import Counter

endpoints = [
    {"ip": "10.200.0.11", "ready": True},
    {"ip": "10.200.1.12", "ready": True},
    {"ip": "10.200.2.13", "ready": False},   # readiness probe 실패
    {"ip": "10.200.0.14", "ready": True},
]
ready = [e["ip"] for e in endpoints if e["ready"]]   # EndpointSlice 의 ready 조건

def pick(eps):
    n = len(eps)
    for i, ip in enumerate(eps):
        if i == n - 1 or random.random() < 1 / (n - i):   # 1/n, 1/(n-1), ..., 1
            return ip

random.seed(1)
cnt = Counter(pick(ready) for _ in range(30000))
for ip in ready:
    print(f"{ip:12s} {cnt[ip] / 30000:.3f}")
print("준비 안 된 10.200.2.13 선택 횟수:", cnt["10.200.2.13"])

# 클러스터 파드 대역을 노드별 /24 로 나누기
cluster = ipaddress.ip_network("10.200.0.0/16")
nodes = ["node-a", "node-b", "node-c"]
alloc = dict(zip(nodes, cluster.subnets(new_prefix=24)))
for n, s in alloc.items():
    print(f"{n}: {s} (파드 최대 {s.num_addresses - 2}개)")
print("최대 노드 수(/24 단위):", 2 ** (24 - 16))

def svc_dns(svc, ns, domain="cluster.local"):
    return f"{svc}.{ns}.svc.{domain}"
print(svc_dns("api", "shop"))
```

```
10.200.0.11  0.333
10.200.1.12  0.334
10.200.0.14  0.334
준비 안 된 10.200.2.13 선택 횟수: 0
node-a: 10.200.0.0/24 (파드 최대 254개)
node-b: 10.200.1.0/24 (파드 최대 254개)
node-c: 10.200.2.0/24 (파드 최대 254개)
최대 노드 수(/24 단위): 256
api.shop.svc.cluster.local
```

순서대로 확률을 다르게 걸었는데도 세 엔드포인트가 거의 정확히 3분의 1씩 선택됐다. 첫 규칙은 1/3, 둘째는 남은 2/3 중 1/2(전체 1/3), 마지막은 나머지 전부(1/3)이기 때문이다. 준비되지 않은 파드는 아예 후보 목록에 들어가지 않는다. readiness probe 가 트래픽 제어 장치라는 뜻이다.

## 현업에서는

- 장애를 층으로 나눈다. 파드 IP 로 직접 붙어 보고(CNI 층), ClusterIP 로 붙어 보고(Service·kube-proxy 층), Service DNS 이름으로 붙어 보고(DNS 층), Ingress 호스트로 붙어 본다(L7 층). 처음 실패하는 층이 범인이다.
- `kubectl get endpointslices -l kubernetes.io/service-name=<서비스>` 로 Service 뒤에 준비된 파드가 실제로 있는지 본다. 셀렉터 오타나 readiness 실패로 엔드포인트가 비면 Service 는 연결을 받을 곳이 없다.
- k3s 는 기본으로 flannel(vxlan 백엔드), CoreDNS, Traefik Ingress 컨트롤러, ServiceLB 를 함께 띄운다. 홈랩 클러스터에서 노드 간 파드 통신만 안 되면 노드 사이 UDP 터널 트래픽이 방화벽에 막히지 않았는지부터 확인한다.
- 파드 대역, Service 대역, 노드 대역, VPN 대역이 서로 겹치지 않는지 클러스터를 만들 때 확인한다. 나중에 바꾸기 가장 어려운 설정이다.
- 기본값은 "모두가 모두와 통신 가능"이다. 네임스페이스 간 격리가 필요하면 기본 거부 NetworkPolicy 부터 깐다.

## 확인 문제

1. 쿠버네티스 네트워크 모델이 요구하는 파드 간 통신의 조건은 무엇인가?
2. ClusterIP 로 ping 이 안 되는데 HTTP 요청은 되는 이유는?
3. 오버레이 방식과 라우팅 방식 CNI 의 차이를 MTU 와 기반 망 요구 사항 관점에서 설명하라.
4. readiness probe 가 실패한 파드에 Service 트래픽이 가지 않는 이유는?
5. gRPC 서비스를 ClusterIP Service 로만 노출했더니 한 파드에 부하가 몰렸다. 원인과 해결책은?

### 풀이

1. 모든 파드가 고유한 클러스터 IP 를 갖고, 노드에 상관없이 프록시나 NAT 없이 서로 직접 통신할 수 있어야 한다.
2. ClusterIP 는 인터페이스에 붙은 주소가 아니라 kube-proxy 가 만든 TCP·UDP 포트 단위 DNAT 규칙의 대상일 뿐이라, ICMP 에 응답할 주체가 없기 때문이다.
3. 오버레이는 파드 패킷을 터널로 감싸므로 기반 망이 파드 대역을 몰라도 되지만 터널 헤더만큼 MTU 가 준다. 라우팅은 캡슐화가 없어 MTU 손실이 없지만, 기반 망(같은 L2 이거나 BGP 를 받는 라우터)이 파드 대역 경로를 알아야 한다.
4. 준비되지 않은 파드는 EndpointSlice 에서 ready 가 아니므로 kube-proxy 가 만드는 전달 규칙의 후보에서 빠지기 때문이다.
5. Service 는 L4 라 연결 단위로 파드를 고르는데, gRPC 는 오래 사는 HTTP/2 연결 하나에 요청을 다중화하므로 한 파드에 고정된다. L7 프록시(Envoy, 서비스 메시)나 헤드리스 Service 와 클라이언트 측 분산을 쓴다.

## 더 읽을거리 (References)

- Kubernetes 문서, *Services, Load Balancing, and Networking*: <https://kubernetes.io/docs/concepts/services-networking/>
- Kubernetes 문서, *Virtual IPs and Service Proxies*: <https://kubernetes.io/docs/reference/networking/virtual-ips/>
- CNI 명세, *Container Network Interface (CNI) Specification*: <https://www.cni.dev/docs/spec/>
- Kubernetes 문서, *Ingress* / Gateway API: <https://kubernetes.io/docs/concepts/services-networking/ingress/>, <https://gateway-api.sigs.k8s.io/>
- K3s 문서, *Networking Services*: <https://docs.k3s.io/networking/networking-services>
