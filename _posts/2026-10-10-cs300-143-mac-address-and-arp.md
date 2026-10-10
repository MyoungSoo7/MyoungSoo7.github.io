---
layout: post
title: "[CS300 #143] MAC 주소와 ARP — IP 주소만으로는 옆 컴퓨터에 닿지 못한다"
date: 2026-10-10 20:23:00 +0900
categories: [cs]
tags: [cs300, networking, mac-address, arp, ndp]
---

컴퓨터공학 300 주제 시리즈의 143번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

MAC 주소는 같은 링크 안에서 프레임을 배달하는 2계층 주소이고, ARP 는 "이 IP 를 가진 장비의 MAC 주소가 뭐냐"를 링크 전체에 물어 알아내는 프로토콜이다.

## 왜 필요한가

IP 패킷은 결국 이더넷 프레임에 실려야 선을 탄다. 그런데 이더넷 프레임에는 목적지 MAC 이 들어가야 한다. 운영체제가 아는 건 상대의 IP 뿐이다. 이 빈칸을 메우는 게 ARP 다.

ARP 가 실패하면 증상이 묘하다. `ping` 은 "Destination Host Unreachable" 을 내고, 애플리케이션은 연결 타임아웃을 낸다. 라우팅 표도 방화벽도 멀쩡한데 통신이 안 된다. IP 를 바꾼 장비가 예전 MAC 캐시 때문에 몇 분간 닿지 않는 일, 가상 IP 를 다른 노드로 옮겼는데 트래픽이 옛 노드로 가는 일도 모두 ARP 이야기다.

## 핵심 개념

### MAC 주소의 구조

이더넷 MAC 주소는 48비트(6바이트)다. 보통 `00:00:5e:00:53:01` 처럼 16진수 두 자리씩 쓴다.

```
  첫 바이트의 하위 두 비트
  +---+---+---+---+---+---+---+---+
  | x | x | x | x | x | x |U/L|I/G|
  +---+---+---+---+---+---+---+---+
  I/G = 1 : 멀티캐스트(그룹) 주소,  0 : 유니캐스트
  U/L = 1 : 로컬 관리 주소,       0 : 제조사가 할당한 전역 주소
```

- 앞 24비트는 보통 OUI(Organizationally Unique Identifier)로, IEEE 가 제조사에 할당한다. 뒤 24비트는 제조사가 기기마다 붙인다.
- `ff:ff:ff:ff:ff:ff` 는 브로드캐스트 주소다. 링크 위 모든 장비가 받는다.
- 가상 머신, 컨테이너의 veth, 스마트폰의 무작위 MAC 은 대개 U/L 비트가 1 인 로컬 관리 주소다.
- 문서와 예제용으로 IANA 가 `00-00-5E-00-53-00` 부터 `00-00-5E-00-53-FF` 까지를 따로 정해 두었다(RFC 7042). 이 글의 예시는 모두 이 범위다.

MAC 주소는 "같은 링크 안" 에서만 의미가 있다. 라우터를 하나 넘을 때마다 이더넷 헤더는 새로 쓰인다. 출발지·목적지 IP 는 끝까지 유지되지만 MAC 은 홉마다 바뀐다.

### ARP 의 동작

ARP 는 RFC 826 에서 정의됐다. 이더넷 위 IPv4 기준으로 흐름은 다음과 같다.

```
호스트 A (192.0.2.10)                          호스트 B (192.0.2.20)
  |  ARP Request (브로드캐스트 ff:ff:ff:ff:ff:ff)        |
  |  "192.0.2.20 가진 분? 저는 192.0.2.10, MAC ...:01"   |
  |----------------------------------------------------->|  (링크 위 모두 수신)
  |                                                      |
  |  ARP Reply (유니캐스트, A 에게만)                     |
  |  "192.0.2.20 은 MAC ...:02 입니다"                    |
  |<-----------------------------------------------------|
  |  이후 IP 패킷을 목적지 MAC ...:02 로 감싸서 전송        |
```

- 목적지가 같은 서브넷이 아니면 A 는 상대 IP 가 아니라 기본 게이트웨이 IP 의 MAC 을 묻는다. 프레임은 게이트웨이로 가고, 게이트웨이가 다음 링크에서 다시 ARP 를 한다.
- 결과는 ARP 캐시(리눅스에서는 neighbour table)에 저장된다. 리눅스는 항목을 REACHABLE, STALE, DELAY, PROBE, FAILED, INCOMPLETE 같은 상태로 관리하며 `ip neigh` 로 볼 수 있다.

### ARP 패킷 형식

이더넷/IPv4 용 ARP 패킷은 28바이트다.

| 필드 | 크기 | 값 (이더넷/IPv4) |
|---|---|---|
| 하드웨어 타입 | 2 | 1 (Ethernet) |
| 프로토콜 타입 | 2 | 0x0800 (IPv4) |
| 하드웨어 주소 길이 | 1 | 6 |
| 프로토콜 주소 길이 | 1 | 4 |
| 동작(opcode) | 2 | 1 = 요청, 2 = 응답 |
| 송신자 MAC / IP | 6 / 4 | |
| 대상 MAC / IP | 6 / 4 | 요청에서는 대상 MAC 을 0 으로 채움 |

이더넷 프레임의 EtherType 은 0x0806 이다. ARP 는 IP 패킷이 아니라 IP 와 나란히 이더넷에 바로 실린다. 그래서 2계층과 3계층 사이에 걸친 프로토콜이라 부른다.

### Gratuitous ARP 와 보안

- Gratuitous ARP: 묻지도 않았는데 "내 IP 는 이 MAC 이다"라고 알리는 패킷이다. IP 중복 감지나, 장애 조치로 가상 IP 가 다른 장비로 옮겨 갔을 때 이웃의 캐시를 갱신하는 데 쓴다.
- ARP 에는 인증이 없다. 누구든 거짓 응답을 보내 남의 캐시를 오염시킬 수 있다(ARP 스푸핑). 같은 링크 안 공격자가 중간자 공격을 하는 고전적 방법이다. 스위치의 동적 ARP 검사 같은 기능이나, 상위 계층 암호화(TLS)로 막는다.

### IPv6 에서는

IPv6 는 ARP 를 쓰지 않는다. 대신 ICMPv6 기반의 이웃 탐색(Neighbor Discovery, RFC 4861)이 Neighbor Solicitation / Neighbor Advertisement 메시지로 같은 일을 한다. 브로드캐스트 대신 대상 주소에서 파생한 멀티캐스트 그룹으로 묻는다는 점이 다르다.

## 직접 해 보기

ARP 요청을 바이트로 만들고 다시 해석해 보자. MAC 주소의 I/G, U/L 비트를 판별하는 함수도 함께 만든다.

```python
import struct, socket

def mac_bytes(s): return bytes.fromhex(s.replace(":", ""))
def mac_str(b):   return ":".join(f"{x:02x}" for x in b)

def mac_kind(mac):
    first = mac_bytes(mac)[0]
    group = "멀티캐스트" if first & 0b01 else "유니캐스트"
    admin = "로컬 관리" if first & 0b10 else "전역(제조사)"
    return f"{mac}: {group}, {admin}"

for m in ["00:00:5e:00:53:01", "ff:ff:ff:ff:ff:ff", "02:00:5e:00:53:01", "01:00:5e:00:00:fb"]:
    print(mac_kind(m))

def arp_request(sender_mac, sender_ip, target_ip):
    return struct.pack("!HHBBH6s4s6s4s",
        1, 0x0800, 6, 4, 1,
        mac_bytes(sender_mac), socket.inet_aton(sender_ip),
        b"\x00" * 6,           socket.inet_aton(target_ip))

pkt = arp_request("00:00:5e:00:53:01", "192.0.2.10", "192.0.2.20")
frame = mac_bytes("ff:ff:ff:ff:ff:ff") + mac_bytes("00:00:5e:00:53:01") \
        + struct.pack("!H", 0x0806) + pkt
print("ARP 길이:", len(pkt), "프레임 헤더+ARP:", len(frame))

htype, ptype, hlen, plen, op, sha, spa, tha, tpa = struct.unpack("!HHBBH6s4s6s4s", frame[14:42])
print("opcode", op, "|", mac_str(sha), socket.inet_ntoa(spa), "->", socket.inet_ntoa(tpa), "는 누구?")
```

```
00:00:5e:00:53:01: 유니캐스트, 전역(제조사)
ff:ff:ff:ff:ff:ff: 멀티캐스트, 로컬 관리
02:00:5e:00:53:01: 유니캐스트, 로컬 관리
01:00:5e:00:00:fb: 멀티캐스트, 전역(제조사)
ARP 길이: 28 프레임 헤더+ARP: 42
opcode 1 | 00:00:5e:00:53:01 192.0.2.10 -> 192.0.2.20 는 누구?
```

브로드캐스트 주소는 모든 비트가 1 이라 I/G 비트도 1, 곧 그룹 주소의 특수한 경우다. 42바이트 프레임은 최소 크기 64바이트에 못 미치므로 실제 전송 때는 패딩이 붙는다.

## 현업에서는

- `ip neigh show` 로 이웃 캐시를 본다. 특정 IP 가 FAILED 나 INCOMPLETE 로 남아 있으면 상대가 ARP 에 응답하지 않는다는 뜻이다. 케이블, VLAN 설정, 상대 장비 전원을 의심한다.
- 장애 조치용 가상 IP(keepalived 의 VRRP, 쿠버네티스의 MetalLB L2 모드 등)는 IP 를 넘겨받은 노드가 gratuitous ARP 를 보내 주변 캐시를 갱신하는 방식에 기댄다. 일부 장비가 이를 무시하면 전환 직후 몇 분간 트래픽이 옛 노드로 간다.
- 홈랩처럼 노드가 같은 L2 망에 있으면, 노드 하나의 IP 를 바꾼 직후 다른 노드에서만 접속이 안 되는 일이 있다. 오래된 캐시 항목 탓이다. `ip neigh flush` 로 비우거나 잠시 기다리면 풀린다.
- MAC 주소와 내부 IP 대응표는 망 구성 정보이므로 외부 문서에 그대로 옮기지 않는다. 예제에는 문서용 주소를 쓴다.

## 확인 문제

1. MAC 주소 `03:00:5e:00:53:01` 은 유니캐스트인가 멀티캐스트인가? 전역 주소인가 로컬 관리 주소인가?
2. 호스트가 다른 서브넷에 있는 서버로 패킷을 보낼 때 ARP 로 누구의 MAC 을 묻는가?
3. ARP 요청은 브로드캐스트로, 응답은 유니캐스트로 보내는 이유는?
4. ARP 스푸핑이 가능한 근본 원인은 무엇인가?
5. IPv6 에서 ARP 의 역할을 하는 것은 무엇인가?

### 풀이

1. 첫 바이트 0x03 의 하위 두 비트가 모두 1 이다. 멀티캐스트이고 로컬 관리 주소다.
2. 기본 게이트웨이(다음 홉 라우터)의 IP 에 대한 MAC 을 묻는다.
3. 요청 시점에는 상대 MAC 을 모르므로 모두에게 물어야 하고, 응답 시점에는 요청 패킷에 송신자 MAC 이 들어 있어 그 하나에게만 보내면 된다.
4. ARP 응답에 인증이 없어, 요청하지 않은 응답이나 거짓 응답도 캐시에 반영될 수 있기 때문이다.
5. ICMPv6 기반 이웃 탐색(Neighbor Discovery, RFC 4861)의 Neighbor Solicitation/Advertisement 다.

## 더 읽을거리 (References)

- RFC 826, *An Ethernet Address Resolution Protocol*: <https://www.rfc-editor.org/rfc/rfc826.html>
- RFC 7042, *IANA Considerations and IETF Protocol and Documentation Usage for IEEE 802 Parameters*: <https://www.rfc-editor.org/rfc/rfc7042.html>
- RFC 4861, *Neighbor Discovery for IP version 6 (IPv6)*: <https://www.rfc-editor.org/rfc/rfc4861.html>
- arp(7), ip-neighbour(8) 매뉴얼: <https://manpages.debian.org/bookworm/manpages/arp.7.en.html>, <https://manpages.debian.org/bookworm/iproute2/ip-neighbour.8.en.html>
