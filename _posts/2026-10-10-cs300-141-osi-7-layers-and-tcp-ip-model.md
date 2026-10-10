---
layout: post
title: "[CS300 #141] OSI 7계층과 TCP/IP 4계층 — 장애를 층으로 나눠 말하는 법"
date: 2026-10-10 20:21:00 +0900
categories: [cs]
tags: [cs300, networking, osi, tcp-ip, encapsulation]
---

컴퓨터공학 300 주제 시리즈의 141번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

네트워크 계층 모델은 "누가 무엇을 책임지는가"를 나눈 지도다. OSI 7계층은 개념을 말할 때, TCP/IP 4계층은 실제 인터넷 구현을 말할 때 쓴다.

## 왜 필요한가

"API 가 타임아웃 났다"는 보고는 정보가 거의 없다. 이름 풀이(DNS)가 안 됐을 수도 있고, 패킷이 라우터에서 버려졌을 수도 있고, TCP 연결은 됐는데 서버 앱이 응답을 안 했을 수도 있다. 이 셋은 고치는 사람도, 고치는 방법도 다르다.

계층 모델은 이 문제를 쪼개는 칼이다. "3계층까지는 정상, 4계층에서 SYN 에 응답이 없다"고 말할 수 있으면 대화가 끝난다. 이 파트 전체가 결국 이 문장을 정확히 말하기 위한 준비다.

## 핵심 개념

### 두 모델

OSI 참조 모델은 ITU-T X.200(ISO/IEC 7498-1 과 같은 내용)으로 표준화됐다. 7개 계층으로 통신 기능을 나눈다. TCP/IP 모델은 인터넷 호스트 요구사항을 정리한 RFC 1122 에서 네 계층(링크, 인터넷, 전송, 응용)으로 설명한다.

| OSI 계층 | 이름 | TCP/IP 계층 | 대표 프로토콜·장비 | 데이터 단위 |
|---|---|---|---|---|
| 7 | 응용 (Application) | 응용 | HTTP, DNS, SMTP | 메시지 |
| 6 | 표현 (Presentation) | 응용 | 인코딩, 압축, (TLS 를 여기 두기도) | |
| 5 | 세션 (Session) | 응용 | 세션 관리 | |
| 4 | 전송 (Transport) | 전송 | TCP, UDP | 세그먼트 / 데이터그램 |
| 3 | 네트워크 (Network) | 인터넷 | IP, ICMP, 라우터 | 패킷 |
| 2 | 데이터 링크 (Data Link) | 링크 | 이더넷, ARP, 스위치 | 프레임 |
| 1 | 물리 (Physical) | 링크 | 케이블, 광, 전파 | 비트 |

OSI 의 5·6계층은 인터넷 프로토콜에서 별도 계층으로 존재하지 않는다. 그 기능은 응용 프로그램이나 라이브러리(TLS 등) 안에 녹아 있다. 그래서 현업에서 "L5", "L6" 라는 말은 거의 안 쓰고, "L4 로드 밸런서", "L7 로드 밸런서"처럼 4와 7만 자주 들린다.

### 캡슐화

위 계층의 데이터는 아래 계층으로 내려가면서 헤더를 하나씩 덧붙인다. 이것을 캡슐화(encapsulation)라 한다.

```
응용 데이터                         [ HTTP 요청 ]
전송 계층       [ TCP 헤더 | HTTP 요청 ]
인터넷 계층  [ IP 헤더 | TCP 헤더 | HTTP 요청 ]
링크 계층 [ Eth 헤더 | IP 헤더 | TCP 헤더 | HTTP 요청 | FCS ]
```

받는 쪽은 반대로 한 겹씩 벗긴다. 각 계층은 자기 헤더만 읽고, 그 안의 내용은 "위 계층의 짐"으로 취급한다. 라우터는 원칙적으로 3계층까지만 보고, 스위치는 2계층까지만 본다. 이 분리 덕분에 이더넷을 와이파이로 바꿔도 TCP 와 HTTP 는 그대로 쓸 수 있다.

### 헤더 크기 감각

| 헤더 | 최소 크기 | 근거 |
|---|---|---|
| 이더넷 (목적지 MAC, 출발지 MAC, EtherType) | 14바이트 + FCS 4바이트 | IEEE 802.3 |
| IPv4 | 20바이트 (옵션 없을 때) | RFC 791 |
| TCP | 20바이트 (옵션 없을 때) | RFC 9293 |
| UDP | 8바이트 | RFC 768 |

이더넷의 기본 페이로드 최대치(MTU)가 1500바이트이므로, IPv4 와 옵션 없는 TCP 를 쓰면 한 프레임에 응용 데이터는 최대 1460바이트가 들어간다. 이 숫자가 TCP 의 MSS(Maximum Segment Size)로 흔히 보이는 값이다.

### 계층 모델의 한계

모델은 깔끔하지만 현실은 경계를 넘나든다.

- ARP 는 IP 주소를 MAC 주소로 바꾸므로 2계층과 3계층 사이에 걸쳐 있다.
- TLS 는 TCP 위, HTTP 아래에 있다. OSI 로는 6계층쯤이지만 TCP/IP 모델로는 그냥 응용 계층이다.
- QUIC 은 UDP 위에서 신뢰성·혼잡 제어(전송 계층 일)와 암호화를 모두 한다.
- NAT 장비는 3계층 장비이면서 4계층 포트 번호를 고쳐 쓴다.

그래서 계층 번호는 "정확한 분류"보다 "대화의 좌표"로 쓰는 편이 맞다.

## 직접 해 보기

파이썬 `struct` 로 HTTP 요청 한 줄을 UDP·IPv4·이더넷 헤더로 차례로 감싸 보자. 체크섬 같은 세부는 0 으로 두고, 바이트 수가 어떻게 불어나는지만 본다. 주소는 문서용 예시 대역(RFC 5737 의 192.0.2.0/24, 198.51.100.0/24)과 문서용 MAC(RFC 7042 의 00-00-5E-00-53-xx)을 쓴다.

```python
import struct, socket

payload = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"

# 4계층: UDP 헤더 8바이트 (출발 포트, 목적 포트, 길이, 체크섬)
udp = struct.pack("!HHHH", 50000, 8080, 8 + len(payload), 0) + payload

# 3계층: IPv4 헤더 20바이트
src = socket.inet_aton("192.0.2.10")
dst = socket.inet_aton("198.51.100.20")
total_len = 20 + len(udp)
ip = struct.pack("!BBHHHBBH4s4s",
                 0x45, 0, total_len, 1, 0, 64, 17, 0, src, dst) + udp

# 2계층: 이더넷 헤더 14바이트 (목적 MAC, 출발 MAC, EtherType 0x0800 = IPv4)
dmac = bytes.fromhex("00005e005302")
smac = bytes.fromhex("00005e005301")
frame = dmac + smac + struct.pack("!H", 0x0800) + ip

for name, b in [("응용", payload), ("UDP", udp), ("IPv4", ip), ("Ethernet", frame)]:
    print(f"{name:9s} {len(b):4d} 바이트")

# 받는 쪽: 한 겹씩 벗기기
eth_type = struct.unpack("!H", frame[12:14])[0]
ihl = (frame[14] & 0x0F) * 4
proto = frame[14 + 9]
l4 = frame[14 + ihl:]
sport, dport, ulen, _ = struct.unpack("!HHHH", l4[:8])
print(hex(eth_type), "IHL", ihl, "proto", proto, "ports", sport, dport)
print(l4[8:ulen].split(b"\r\n")[0])
```

실행 결과는 다음과 같다.

```
응용          37 바이트
UDP         45 바이트
IPv4        65 바이트
Ethernet    79 바이트
0x800 IHL 20 proto 17 ports 50000 8080
b'GET / HTTP/1.1'
```

37바이트 요청이 79바이트 프레임이 됐다(FCS 4바이트와 최소 프레임 패딩은 생략). 받는 쪽 코드는 EtherType 을 보고 IPv4 라는 걸 알고, IP 헤더의 프로토콜 필드 17 을 보고 UDP 라는 걸 안다. 각 계층이 "다음 계층이 무엇인지" 알려주는 필드를 갖고 있다는 점이 핵심이다.

## 현업에서는

- 장애 보고서를 쓸 때 계층으로 증상을 적는다. 예: "DNS 응답 정상(L7), TCP 443 연결 수립 정상(L4), TLS 핸드셰이크 중 서버가 RST(L4/L6 경계)."
- 로드 밸런서·방화벽 제품을 고를 때 "L4 냐 L7 이냐"가 첫 질문이다. L4 는 IP·포트만 보고, L7 은 HTTP 경로와 헤더까지 본다.
- 쿠버네티스에서 Service 는 대체로 L4, Ingress 는 L7 이다. 홈랩 k3s 클러스터에서도 "Service 로는 붙는데 Ingress 로는 404"라면 L7 라우팅 규칙을 먼저 의심한다.
- 패킷 캡처(tcpdump, Wireshark) 화면이 바로 캡슐화의 단면이다. 이더넷 → IP → TCP → HTTP 순으로 펼쳐진다.

## 확인 문제

1. OSI 7계층 중 TCP/IP 4계층의 "응용 계층" 하나로 묶이는 계층 세 개는 무엇인가?
2. 라우터와 L2 스위치는 각각 어느 계층의 헤더까지 보고 전달을 결정하는가?
3. 이더넷 MTU 가 1500바이트일 때, IPv4 와 옵션 없는 TCP 를 쓰면 한 세그먼트의 최대 응용 데이터는 몇 바이트인가?
4. 받는 쪽이 이더넷 프레임 안의 데이터가 IPv4 인지 IPv6 인지 아는 방법은?
5. QUIC 이 "계층 모델에 딱 맞지 않는" 이유를 한 문장으로 설명하라.

### 풀이

1. 세션(5), 표현(6), 응용(7).
2. 라우터는 3계층(IP 헤더), L2 스위치는 2계층(이더넷 헤더의 MAC 주소).
3. 1500 − 20(IP) − 20(TCP) = 1460바이트.
4. 이더넷 헤더의 EtherType 필드다. IPv4 는 0x0800, IPv6 는 0x86DD 다.
5. UDP(전송 계층) 위에 올라가면서 다시 신뢰성·혼잡 제어 같은 전송 계층 기능과 암호화를 함께 수행하기 때문이다.

## 더 읽을거리 (References)

- ITU-T Recommendation X.200, *Information technology – Open Systems Interconnection – Basic Reference Model*: <https://www.itu.int/rec/T-REC-X.200-199407-I/en>
- RFC 1122, *Requirements for Internet Hosts – Communication Layers*: <https://www.rfc-editor.org/rfc/rfc1122.html>
- RFC 791, *Internet Protocol*: <https://www.rfc-editor.org/rfc/rfc791.html>
- RFC 7042, *IANA Considerations and IETF Protocol and Documentation Usage for IEEE 802 Parameters* (문서용 MAC 주소): <https://www.rfc-editor.org/rfc/rfc7042.html>
