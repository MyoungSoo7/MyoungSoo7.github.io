---
layout: post
title: "[CS300 #158] VPN 과 터널링 — 패킷 안에 패킷을 넣는 기술과 MTU 의 대가"
date: 2026-10-10 20:38:00 +0900
categories: [cs]
tags: [cs300, networking, vpn, tunneling, wireguard, vxlan]
---

컴퓨터공학 300 주제 시리즈의 158번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

터널링은 한 네트워크의 패킷을 통째로 다른 패킷의 데이터로 감싸 보내는 기술이다. 여기에 암호화와 인증을 더해 공용망 위에 사설망처럼 쓰는 통로를 만든 것이 VPN 이다. 대가는 헤더만큼 줄어드는 MTU 다.

## 왜 필요한가

- 재택 근무자가 사내망 서버에 접속해야 한다.
- 두 데이터센터(또는 집과 클라우드)의 사설 대역을 하나의 망처럼 잇고 싶다.
- 쿠버네티스 노드들이 서로 다른 서브넷에 있어도 파드끼리 사설 IP 로 통신해야 한다.

세 경우 모두 "중간 망은 이 주소를 모르지만, 터널 양 끝은 안다"는 구조로 해결한다. 그리고 세 경우 모두 "작은 요청은 되는데 큰 응답만 멈춘다"는 같은 종류의 장애를 겪는다. MTU 문제다. 이 글은 터널의 원리와 함께 그 장애를 설명한다.

## 핵심 개념

### 캡슐화

```
원래 패킷:                     [ IP(10.1.0.5 → 10.2.0.9) | TCP | 데이터 ]
터널 입구에서 감싼 뒤:
[ 바깥 IP(203.0.113.10 → 198.51.100.20) | 터널 헤더 | IP(10.1.0.5 → 10.2.0.9) | TCP | 데이터 ]
```

중간 라우터는 바깥 IP 헤더만 보고 터널 반대편 끝으로 전달한다. 반대편 끝은 바깥 헤더를 벗기고 안쪽 패킷을 자기 망으로 내보낸다. 안쪽 주소가 사설 대역이어도, 대역이 양쪽에서 겹치지만 않으면 된다.

### 대표 터널 프로토콜

| 프로토콜 | 운반체 | 암호화 | 특징 |
|---|---|---|---|
| GRE (RFC 2784) | IP (프로토콜 번호 47) | 없음 | 단순한 범용 캡슐화 |
| IPsec ESP (RFC 4303) | IP (프로토콜 번호 50), 또는 NAT 통과 시 UDP | 있음 | 표준 VPN. 키 교환은 IKEv2(RFC 7296) |
| WireGuard | UDP | 있음 | 작은 코드, 고정된 최신 암호 조합 |
| VXLAN (RFC 7348) | UDP (IANA 할당 포트 4789) | 없음 | L2 이더넷 프레임을 L3 위로. 24비트 VNI |
| OpenVPN 등 TLS 기반 | TCP 또는 UDP | 있음 | 사용자 공간 구현. 방화벽 통과가 쉽다 |

### IPsec

IPsec 구조는 RFC 4301 이 정한다. 두 가지 모드가 있다.

- 전송 모드: 원래 IP 헤더는 두고 페이로드만 보호한다. 호스트 간 보호에 쓴다.
- 터널 모드: 원래 패킷 전체를 암호화하고 새 IP 헤더를 붙인다. 사이트 간 VPN 의 기본이다.

ESP 는 IP 위에 바로 실리므로 포트가 없다. 포트로 매핑하는 NAT 를 통과할 수 없어, NAT 가 감지되면 ESP 를 UDP 로 한 번 더 감싼다(NAT-T). IPsec VPN 설정에서 UDP 500 과 4500 을 열라고 하는 이유다.

### WireGuard

WireGuard 는 암호 조합 협상이 없다. Curve25519 키 교환, ChaCha20-Poly1305 인증 암호화, BLAKE2s 해시로 고정돼 있고, Noise 프레임워크의 IK 핸드셰이크를 쓴다. 모든 패킷은 UDP 로 보낸다.

- 각 피어는 공개키로 식별된다. 설정 파일에 상대의 공개키와 "그 피어에게 보낼 대역(AllowedIPs)"을 적는다. 이 목록이 라우팅 표이자 접근 제어 목록이다.
- 연결 개념이 없고 조용하다. 보낼 게 없으면 아무것도 보내지 않으며, 인증되지 않은 패킷에는 응답하지 않는다. NAT 매핑 유지가 필요하면 PersistentKeepalive 를 켠다.

### VXLAN 과 오버레이 네트워크

VXLAN 은 이더넷 프레임 전체를 UDP 에 싣는다. 8바이트 VXLAN 헤더에 24비트 VNI(VXLAN Network Identifier)가 있어 최대 약 1,600만 개의 논리 네트워크를 구분한다. 서로 다른 서브넷의 서버들 위에 하나의 가상 L2 망을 펼칠 때 쓴다. 쿠버네티스 CNI 중 flannel 의 기본 백엔드가 VXLAN 이고, k3s 도 flannel 의 vxlan 백엔드를 기본으로 쓴다. 암호화가 필요하면 k3s 는 `wireguard-native` 백엔드를 제공한다.

### MTU 와 경로 MTU 탐색

터널 헤더만큼 안쪽 패킷이 쓸 수 있는 공간이 준다.

```
바깥 MTU 1500
VXLAN(IPv4):  바깥 IP 20 + UDP 8 + VXLAN 8 + 안쪽 이더넷 14 = 50  → 안쪽 MTU 1450
WireGuard(IPv4): 바깥 IP 20 + UDP 8 + WireGuard 32           = 60  → 안쪽 MTU 1440
```

안쪽 인터페이스 MTU 를 1500 으로 두면, 1500바이트 패킷이 터널을 지나며 1550바이트가 되어 바깥 링크를 넘는다. 원래는 경로 MTU 탐색(PMTUD, IPv4 는 RFC 1191)이 이를 해결한다. 큰 패킷에 DF(단편화 금지) 비트를 켜 보내고, 못 지나가는 라우터가 ICMP "Fragmentation Needed" 로 알맞은 크기를 알려 준다. 그런데 방화벽이 ICMP 를 모두 막으면 이 신호가 사라진다. 송신자는 패킷이 왜 사라지는지 모른 채 재전송만 한다. 이것이 "PMTUD 블랙홀"이다.

증상은 독특하다. SSH 접속과 `ls` 는 되는데 큰 파일 출력에서 멈춘다. HTTPS 핸드셰이크는 되는데 큰 응답 본문이 오지 않는다. 작은 패킷만 통과하기 때문이다. 해결책은 터널 인터페이스 MTU 를 정확히 낮추거나, TCP SYN 의 MSS 값을 터널에 맞게 고쳐 쓰는 MSS 클램핑을 하는 것이다.

## 직접 해 보기

VXLAN 헤더를 만들어 VNI 를 넣고 꺼내 보고, 터널별 안쪽 MTU 와 TCP MSS 를 계산한다.

```python
import struct

def vxlan_header(vni):
    # 8바이트: 플래그(I 비트=0x08) + 예약 24비트 + VNI 24비트 + 예약 8비트
    return struct.pack("!B3xI", 0x08, vni << 8)

def parse_vxlan(h):
    flags, rest = struct.unpack("!B3xI", h)
    return bool(flags & 0x08), rest >> 8

h = vxlan_header(4242)
print("VXLAN 헤더:", h.hex(), "->", parse_vxlan(h))
print("VNI 최대 개수:", 2 ** 24)

OVERHEAD = {                       # 바깥 IPv4 기준 바이트
    "GRE":            20 + 4,      # 바깥 IP + GRE 기본 헤더
    "VXLAN":          20 + 8 + 8 + 14,
    "WireGuard":      20 + 8 + 32, # 바깥 IP + UDP + (타입4 + 수신자4 + 카운터8 + 인증태그16)
}
for name, ov in OVERHEAD.items():
    inner_mtu = 1500 - ov
    mss = inner_mtu - 20 - 20      # 안쪽 IPv4 + TCP
    print(f"{name:10s} 오버헤드 {ov:3d}B -> 안쪽 MTU {inner_mtu}, TCP MSS {mss}")

def fits(packet_len, tunnel):
    return packet_len + OVERHEAD[tunnel] <= 1500
for size in (1200, 1450, 1500):
    print(f"안쪽 {size}B 패킷이 VXLAN 을 지나 1500 링크를 통과?", fits(size, "VXLAN"))
```

```
VXLAN 헤더: 0800000000109200 -> (True, 4242)
VNI 최대 개수: 16777216
GRE        오버헤드  24B -> 안쪽 MTU 1476, TCP MSS 1436
VXLAN      오버헤드  50B -> 안쪽 MTU 1450, TCP MSS 1410
WireGuard  오버헤드  60B -> 안쪽 MTU 1440, TCP MSS 1400
안쪽 1200B 패킷이 VXLAN 을 지나 1500 링크를 통과? True
안쪽 1450B 패킷이 VXLAN 을 지나 1500 링크를 통과? True
안쪽 1500B 패킷이 VXLAN 을 지나 1500 링크를 통과? False
```

VNI 4242 는 16진수 0x001092 로 헤더의 5~7번째 바이트에 들어갔다. 안쪽 MTU 를 1500 으로 둔 채 VXLAN 을 쓰면 최대 크기 패킷부터 통과하지 못한다. 작은 요청은 되고 큰 응답만 막히는 이유가 이 표에 있다. 바깥이 IPv6 면 헤더가 20바이트 더 커져 여유가 더 줄어든다.

## 현업에서는

- 오버레이 CNI 를 쓰는 클러스터에서 파드 인터페이스 MTU 는 보통 노드 MTU 보다 터널 오버헤드만큼 작게 자동 설정된다. 노드 쪽에 이미 VPN 이나 PPPoE 처럼 MTU 를 줄이는 층이 있으면 자동 계산이 틀어질 수 있다. 홈랩에서 노드 간 통신을 다른 VPN 위로 돌릴 때 특히 확인한다.
- MTU 문제 확인은 단편화 금지 플래그를 켠 ping 으로 한다. 리눅스 iputils 의 `ping -M do -s 1472 <상대>` 처럼 크기를 줄여 가며 통과하는 최대치를 찾는다(1472 + ICMP 8 + IP 20 = 1500).
- 방화벽에서 ICMP 를 통째로 막지 않는다. 최소한 IPv4 의 Fragmentation Needed 와 IPv6 의 Packet Too Big 은 통과시켜야 PMTUD 가 동작한다.
- VPN 대역은 사내망·클러스터 대역과 겹치지 않게 정한다(144번 글). 겹치면 터널 안으로 가야 할 패킷이 로컬로 빠진다.

## 확인 문제

1. 터널링에서 중간 라우터가 안쪽 패킷의 사설 주소를 몰라도 되는 이유는?
2. IPsec ESP 가 NAT 를 그대로 통과하지 못하는 이유와 해결책은?
3. 바깥 MTU 1500, IPv4 위 VXLAN 에서 안쪽 TCP MSS 는 얼마가 적절한가?
4. "SSH 는 되는데 큰 출력에서 멈춘다"는 증상과 ICMP 차단의 관계를 설명하라.
5. WireGuard 설정의 AllowedIPs 가 하는 두 가지 역할은?

### 풀이

1. 중간 라우터는 바깥 IP 헤더의 공인(또는 경로상 유효한) 주소만 보고 전달하며, 안쪽 패킷은 그저 데이터로 취급하기 때문이다.
2. ESP 는 포트 번호가 없어 포트 기반 NAPT 가 매핑할 수 없다. NAT 를 감지하면 ESP 를 UDP(4500)로 감싸는 NAT-T 를 쓴다.
3. 안쪽 MTU 1450 에서 IP 20 과 TCP 20 을 빼 1410바이트.
4. 큰 패킷이 터널을 지나며 MTU 를 넘어 버려지는데, 그 사실을 알리는 ICMP 메시지가 차단돼 송신자가 크기를 줄이지 못한다. 작은 패킷만 통과하므로 대화형 입력은 되고 큰 출력은 멈춘다.
5. 그 피어에게 보낼 목적지 대역을 정하는 라우팅 역할과, 그 피어에게서 받은 패킷의 출발지로 허용할 대역을 정하는 접근 제어 역할이다.

## 더 읽을거리 (References)

- RFC 7348, *Virtual eXtensible Local Area Network (VXLAN)*: <https://www.rfc-editor.org/rfc/rfc7348.html>
- RFC 4301, *Security Architecture for the Internet Protocol*: <https://www.rfc-editor.org/rfc/rfc4301.html>
- WireGuard, *Protocol & Cryptography*: <https://www.wireguard.com/protocol/>
- RFC 1191, *Path MTU Discovery*: <https://www.rfc-editor.org/rfc/rfc1191.html>
- K3s 문서, *Basic Network Options*: <https://docs.k3s.io/networking/basic-network-options>
