---
layout: post
title: "*네트워크 기초* — *OSI 7 계층* / *IP* / *TCP vs UDP* / *DNS* / *HTTP* 까지, *입문* 부터 *실전 도구* 까지"
date: 2026-06-23 06:00:00 +0900
categories: [networking, fundamentals, backend]
tags: [network, osi, tcp-ip, ip, mac, arp, dns, http, https, ping, traceroute, fundamentals, basics]
---

> *"브라우저 주소창 에 google.com 입력 하고 엔터 치면 *무슨 일* 이 일어 나는가?"* — *주니어 면접 의 *고전 질문*. *시니어 가 보기엔 *그 한 줄* 에 *수십 개 의 *네트워크 의 *층* 이 *함께 도는 것* 이 보인다.
>
> *DNS lookup 으로 *도메인 → IP* 변환, *TCP 3-way handshake 로 *연결 수립*, *TLS handshake 로 *암호화*, *HTTP 요청 송신*, *Cloudflare edge 가 *처리*, *origin 서버 로 *forward*, *response 가 *역경로 로 돌아옴*. *각 단계 가 *서로 다른 *OSI 계층* 에서 *각자 책임* 을 *수행*.
>
> 이 글은 *기본기 시리즈 의 *네트워크 입문 편* — *OSI 7 계층 의 *각자 의무*, *IP / MAC / ARP / NAT 의 *물리적 의미*, *TCP vs UDP 의 *철학*, *DNS 의 *분산 lookup*, *HTTP / HTTPS 의 *진실*, *ping / traceroute / dig 의 *진짜 동작* — 까지 *입문자 부터 *백엔드 엔지니어 까지* *공통 으로 *알아야 하는 깊이* 로 정리한다.

내 *기본기 시리즈 의 *네트워크 편 (입문)*. *심화 편* 은 [*TCP 상태 기계 / BBR / QUIC / mTLS*](/2026/06/22/network-fundamentals-tcp-state-machine-bbr-cubic-quic-mtls.html) 참조.

---

## TL;DR — *한 줄 결론*

> 네트워크 의 *기초 7 가지* : (1) **OSI 7 계층** 의 *각자 책임 분리*, (2) **IP (Layer 3)** = *글로벌 주소 + 라우팅*, (3) **MAC + ARP (Layer 2)** = *LAN 내부 주소 + L3→L2 변환*, (4) **NAT** = *private IP ↔ public IP* 의 *주소 변환 의 마법*, (5) **TCP vs UDP (Layer 4)** = *신뢰성 vs 속도* 의 *철학*, (6) **DNS** = *도메인 → IP* 의 *분산 lookup*, (7) **HTTP / HTTPS (Layer 7)** = *웹 의 공통 어휘* + *TLS 의 암호화 종료*. *ping / traceroute / dig / netstat / tcpdump* 가 *각 계층 의 *진단 도구*. *기초 의 깊이* 가 *클러스터 운영 / 사고 진단 / 보안 의 *모든 결정 의 *밑* 에서 *작동*.

---

## 1. *왜 *네트워크 를 *나누어 보나*

### 1.1 *통신 의 *복잡성*

> *서울 의 한 컴퓨터 가 *부산 의 한 컴퓨터 에게 *메시지 보내기* — 이 *단순한 일* 에 *수십 단계 의 *기술* 이 *얽혀 있다*.

각 단계 :
- *어떻게 *부산 의 컴퓨터 를 *찾는가*? (DNS, 라우팅)
- *어떤 *포맷* 으로 보낼까? (HTTP, JSON)
- *패킷* 이 *중간 에 *손실* 되면 어떻게? (TCP 재전송)
- *데이터 가 *큰 면 어떻게 *분할*? (IP fragment, TCP segment)
- *암호화* 는 어떻게? (TLS)
- *서버 가 *나만 응답* 하게? (포트, 세션)

→ *이 *수십 가지 의 *복잡성* 을 *한 곳 에 모으면 *불가능*. *계층 으로 *분리* 가 *유일한 답*.

### 1.2 *계층 의 *원칙*

> *각 계층 은 *자기 책임 만* — *아래 계층 의 *세부 모름*, *위 계층 의 *세부 모름*.

이게 *추상화 의 *힘*. *Ethernet 케이블 이 *광케이블 로 바뀌어도 *TCP 는 *변경 없음*. *HTTP 가 *HTTP/2 로 바뀌어도 *IP 는 *모름*.

→ *각 계층 의 *교체 가능 성* 이 *네트워크 의 *수십 년 진화* 의 *물리적 토대*.

---

## 2. *OSI 7 계층 vs TCP/IP 4 계층*

### 2.1 *OSI 7 (이론)*

```
L7 Application   ← HTTP, FTP, SMTP, SSH, DNS
L6 Presentation  ← TLS / SSL, MIME, charset 인코딩
L5 Session       ← (대부분 L7 안 으로 흡수)
L4 Transport     ← TCP, UDP
L3 Network       ← IP, ICMP, BGP
L2 Data Link     ← Ethernet, Wi-Fi (802.11), MAC, ARP
L1 Physical      ← cable, fiber, NIC, wireless signal
```

### 2.2 *TCP/IP 4 (현실)*

```
L4 Application   ← HTTP, DNS, SSH, ... (OSI L5-L7 통합)
L3 Transport     ← TCP, UDP
L2 Internet      ← IP, ICMP
L1 Link          ← Ethernet, Wi-Fi, MAC
```

→ *TCP/IP 4 계층 이 *실무 의 표준*. OSI 는 *이론 / 교육* 의 표준. 둘 다 *알면 *유연하게 *대응 가능*.

### 2.3 *데이터 의 *변환* — *Encapsulation*

```text
[Application]   HTTP Request: "GET /index.html HTTP/1.1\r\nHost: ..."
       ↓
[Transport]     TCP Segment: src_port=54321, dst_port=80, seq=..., DATA=[위 HTTP]
       ↓
[Network]       IP Packet: src=192.168.0.5, dst=142.250.207.110, DATA=[위 TCP]
       ↓
[Link]          Ethernet Frame: src_mac=AA:BB:..., dst_mac=CC:DD:..., DATA=[위 IP]
       ↓
[Physical]      비트 신호 → 케이블/Wi-Fi 전송
```

→ *각 계층 이 *header 를 *추가* (encapsulation). 수신 측 은 *header 를 *제거* (decapsulation). *Russian doll* 같은 *중첩*.

---

## 3. *Layer 1-2 : 물리 + Ethernet + MAC + ARP*

### 3.1 *MAC Address — *NIC 의 *지문***

> *48-bit (6 byte) 의 *고유 식별자*. *제조 시 *NIC 에 *각인*. *전 세계 *유일*.

예: `B0:38:6C:F4:AF:80`
- *앞 24-bit (B0:38:6C)* = *OUI (Organizationally Unique Identifier)* — *제조사*. 위 는 *Apple* OUI.
- *뒤 24-bit (F4:AF:80)* = *NIC 별 *시리얼*.

### 3.2 *Ethernet Frame*

```text
[Preamble][Dst MAC][Src MAC][EtherType][Payload (IP packet)][CRC]
   8 byte   6 byte  6 byte    2 byte      46~1500 byte         4 byte
```

*EtherType*: `0x0800` = IPv4, `0x86DD` = IPv6, `0x0806` = ARP.

*MTU (Maximum Transmission Unit)* = *Ethernet 의 payload 최대* = *1500 byte*. *그 이상 데이터* 는 *IP 가 분할*.

### 3.3 *ARP (Address Resolution Protocol)*

> *IP 주소 만 알 때 *MAC 주소 찾는 법*.

```text
PC A 가 *192.168.0.5* (서버 B) 와 통신 하려고 함.
PC A 는 *서버 B 의 MAC 모름*.

[Broadcast]
  PC A → 모든 LAN 노드 : "192.168.0.5 의 MAC 누가 가지고 있나요?"
[Unicast]
  서버 B → PC A : "내가 가지고 있어요. CC:DD:EE:..." (응답)

PC A 의 ARP table 에 *(192.168.0.5 → CC:DD:EE:...)* 캐시 (수 분).
```

```bash
# Linux 에서 ARP table 보기
ip neigh
# 192.168.0.5 dev eth0 lladdr cc:dd:ee:11:22:33 REACHABLE
```

→ *우리 클러스터 의 *DHCP 진단* (2026-06-19 사고) 시 *ARP table* 로 *MAC ↔ IP 매핑* 확인. *.120 (유령 솔로몬)* 의 정체 도 *ARP* 로 추적.

### 3.4 *Switch 의 *작동*

> *Hub* (deprecated) = *모든 포트에 *broadcast*. *Switch* = *MAC 학습 후 *해당 포트에만 전달*.

Switch 의 *학습* :
- *각 포트 에서 *들어오는 frame 의 *src MAC* 기록 → *MAC 테이블*
- *destination MAC* 찾아 *해당 포트* 만 전달
- *없으면 (학습 안 됨) *broadcast*

→ *Hub 보다 *Switch 의 *throughput 압도적 우위*.

---

## 4. *Layer 3 : IP, 라우팅, NAT*

### 4.1 *IP 주소 의 *역할***

> *Ethernet 의 MAC 은 *LAN 내부 만*. *인터넷 전체 의 *유일한 주소* 가 *IP*.

**IPv4** (32-bit, 약 43억) :
```
192.168.0.5
└─ 4 byte . 각 byte 0~255 (8-bit)
```

**IPv6** (128-bit, 약 3.4 × 10^38) :
```
2001:0db8:85a3:0000:0000:8a2e:0370:7334
└─ 8 segment (각 16-bit)
```

→ *IPv4 주소 고갈* 이 *2010 년대 부터 *큰 문제*. *NAT 가 *임시 해결*. *IPv6 는 *2026 년 *전체 인터넷 의 *45% 채택*.

### 4.2 *Subnet — *네트워크 의 *나눔***

```
192.168.0.0/24  ← /24 = 앞 24-bit 가 *네트워크 부분*
                  192.168.0.0 ~ 192.168.0.255  (256 개 IP)

192.168.0.5     ← 호스트 IP
└ 같은 subnet 안 — *직접 통신 가능* (ARP)

192.168.1.5     ← *다른 subnet*
└ *Gateway 통해 라우팅* 필요
```

### 4.3 *Private IP — *RFC 1918*

```
10.0.0.0/8        ← 16,777,216 개 (대기업)
172.16.0.0/12     ← 1,048,576 개 (중기업)
192.168.0.0/16    ← 65,536 개 (가정)
```

이 IP 들은 *인터넷 에 *라우팅 안 됨*. *NAT 거쳐야 함*. → *우리 클러스터 의 *.219.0/24 LAN* 도 *private*.

### 4.4 *Routing — *다른 subnet 으로 가는 길*

```text
PC (192.168.0.5)
     ↓ "104.21.66.89 (vault.lemuel.co.kr) 로 가고 싶다"
     ↓ 자기 subnet (192.168.0.0/24) 밖
     ↓ Default Gateway (192.168.0.1) 로 보냄
[Home Router]
     ↓ ISP 의 라우터 로
[ISP Router]
     ↓ BGP 라우팅 테이블 따라 *Cloudflare* 의 ASN 으로
[Cloudflare]
     ↓ Anycast 로 가장 가까운 edge POP 으로
```

`ip route` 또는 `route -n` 으로 *내 컴퓨터 의 *라우팅 테이블* 확인.

```bash
$ ip route
default via 192.168.0.1 dev eth0       ← *default gateway*
192.168.0.0/24 dev eth0 scope link     ← *직접 연결 된 subnet*
```

### 4.5 *NAT (Network Address Translation)*

> *Private IP → Public IP 변환*. *IPv4 고갈 의 *임시 해결*.

```text
[PC 192.168.0.5]            [Home Router]              [Internet 서버]
     │                            │                          │
     │ src=192.168.0.5:54321      │                          │
     │ dst=104.21.66.89:443       │                          │
     │ ────────────────────────→│                          │
     │                            │ src=58.123.45.67:60001  │
     │                            │ ↑ public IP             │
     │                            │ dst=104.21.66.89:443    │
     │                            │ ────────────────────────→│
     │                            │                          │
     │                            │ NAT table :             │
     │                            │   192.168.0.5:54321 ↔  │
     │                            │     58.123.45.67:60001 │
     │                            │ ←────────────────────── │
     │ ←────────────────────────│                          │
```

→ *Router 가 *NAT table* 로 *outbound 시 src 변환*, *inbound 시 dst 복원*. *연결 추적*.

NAT 의 *함정*:
- *서버 측에선 *모든 사용자 가 *같은 public IP 로 보임* (CGNAT 환경). *rate limit / DDoS 차단 어려움*.
- *Inbound connection* (외부 → 내부) 이 *port forwarding* 없으면 *불가능*. → *우리 클러스터 의 *Cloudflare Tunnel 이 *outbound only* 로 *이 한계 우회*.

### 4.6 *ICMP — *L3 의 *제어 프로토콜***

> *ping*, *traceroute* 가 사용.

ICMP type:
- *Echo Request / Reply* — `ping`
- *TTL Exceeded* — `traceroute` 가 사용
- *Destination Unreachable* — 라우팅 실패

---

## 5. *Layer 4 : TCP vs UDP*

### 5.1 *Port — *프로세스 의 *구별*

> *IP 는 *호스트 까지*. *Port 는 *그 호스트 의 *어느 프로세스* 인지*.

```
0~1023      Well-known ports (HTTP 80, HTTPS 443, SSH 22, DNS 53, ...)
1024~49151  Registered ports (PostgreSQL 5432, MySQL 3306, ...)
49152~65535 Dynamic / Private ports (client 의 src port 보통 여기)
```

### 5.2 *TCP — *신뢰성***

**3-way handshake** :
```
Client                   Server
  │                         │
  │ ──── SYN ────────────→ │
  │ ←── SYN-ACK ─────────── │
  │ ──── ACK ────────────→ │
  │       (연결 수립)        │
```

**보장**:
- *순서 보장* — 보낸 순서 대로 도착
- *재전송* — 손실 패킷 *자동 재전송*
- *흐름 제어* — 수신 측 buffer 가득 차면 *송신 측 멈춤*
- *혼잡 제어* — 네트워크 혼잡 감지 시 *송신 속도 감소*

**대가**: *handshake overhead*, *latency 증가*, *bandwidth 소모*.

### 5.3 *UDP — *속도***

> *Connectionless + 신뢰성 보장 X*.

```
Client → Server : "data"   (그게 끝)
```

- *handshake 없음*
- *재전송 없음* (애플리케이션 책임)
- *순서 보장 없음*

**용도**:
- DNS query (대부분)
- VoIP, video streaming (재전송 보다 *지연 회피* 우선)
- 게임 (실시간)
- QUIC (HTTP/3 의 *기반*) — *UDP 위에 *재전송 / 암호화 직접 구현*

### 5.4 *TCP vs UDP 의 *선택*

| | TCP | UDP |
|---|---|---|
| 신뢰성 | ✅ | ❌ |
| 순서 | ✅ | ❌ |
| 재전송 | ✅ | ❌ |
| Latency | 높음 (handshake) | 낮음 |
| Bandwidth overhead | 높음 | 낮음 |
| 사용 예 | HTTP, SSH, DB | DNS, VoIP, 게임 |

→ *대부분 의 백엔드 코드* 가 *TCP 위*. *UDP 는 *특수 용도*.

---

## 6. *DNS — *도메인 → IP*

### 6.1 *왜 *DNS 인가*

> *우리 가 *142.250.207.110 외우지 않고 *google.com* 으로 접근 가능 한 *이유*.

### 6.2 *Resolution 의 *단계*

```text
[Browser] : "google.com 의 IP?"
   ↓
[OS Stub Resolver] : /etc/resolv.conf 의 *nameserver* 에 query
   ↓
[Recursive Resolver (예: 1.1.1.1 Cloudflare)]
   ↓ 캐시 없으면 ↓
[Root Server (.)] : "TLD 'com' 의 nameserver 는 a.gtld-servers.net..."
   ↓
[TLD Server (.com)] : "google.com 의 nameserver 는 ns1.google.com..."
   ↓
[Authoritative Server (ns1.google.com)] : "google.com 의 IP 는 142.250.207.110"
   ↓
응답 (caching 됨)
```

**Caching** :
- *각 단계 마다 *TTL (Time To Live)* 따라 캐시
- *Recursive resolver* + *OS resolver* + *Browser* 의 *3 단 캐시*
- *자주 가는 도메인 은 *DNS 한 번 후 *수 분 ~ 수 시간 캐시*

### 6.3 *DNS Record 타입*

| Type | 의미 |
|---|---|
| **A** | hostname → IPv4 |
| **AAAA** | hostname → IPv6 |
| **CNAME** | hostname → 다른 hostname (alias) |
| **MX** | mail server |
| **TXT** | 임의 텍스트 (SPF, DKIM, verification) |
| **NS** | 이 zone 의 nameserver |
| **SOA** | zone 의 metadata |
| **SRV** | 서비스 + 포트 |

### 6.4 *dig — *실전 도구***

```bash
$ dig google.com

; <<>> DiG 9.18.0 <<>> google.com
;; QUESTION SECTION:
;google.com.                    IN      A

;; ANSWER SECTION:
google.com.             292     IN      A       142.250.207.110

;; SERVER: 1.1.1.1#53(1.1.1.1)
;; Query time: 8 msec
```

```bash
# 특정 nameserver 직접 query
dig @8.8.8.8 google.com

# 모든 record
dig google.com ANY

# 역방향 (IP → hostname)
dig -x 142.250.207.110

# DNSSEC 검증
dig +dnssec google.com
```

→ 우리 클러스터 의 *Cloudflare DNS* 진단 (2026-06-23) 시 `dig` 로 *각 도메인 의 *CNAME 추적* + *Tunnel 매핑* 확인.

### 6.5 *우리 클러스터 의 *내부 DNS*

K8s 안 의 *CoreDNS*:
- `<service>.<namespace>.svc.cluster.local` 형식
- 예: `postgres.settlement-prod.svc.cluster.local` → ClusterIP

```bash
# Pod 안 에서 nslookup
nslookup postgres.settlement-prod.svc
# Server:     169.254.20.10  (nodelocaldns) 또는 10.43.0.10 (kube-dns)
# Address:    10.43.x.y      (postgres service ClusterIP)
```

→ K8s 의 *모든 서비스 통신* 이 *DNS 기반*. *2026-06-19 outage* 의 *root cause* 도 *cluster-dns 의 잘못된 IP* 였음.

---

## 7. *Layer 7 : HTTP / HTTPS*

### 7.1 *HTTP 요청 / 응답*

**Request**:
```http
GET /index.html HTTP/1.1
Host: google.com
User-Agent: Mozilla/5.0
Accept: text/html
Cookie: session=abc123

(body — POST 등 의 경우)
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234
Set-Cookie: session=def456

<html>...</html>
```

### 7.2 *Status Code*

| 범위 | 의미 |
|---|---|
| 1xx | Informational (잘 안 씀) |
| 2xx | Success — 200 OK, 201 Created, 204 No Content |
| 3xx | Redirect — 301 Moved Permanently, 302 Found, 304 Not Modified |
| 4xx | Client Error — 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Too Many Requests |
| 5xx | Server Error — 500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout |

→ *백엔드 의 *모든 에러 분류 의 *공통 어휘*.

### 7.3 *HTTP Methods*

| Method | 의미 | Idempotent |
|---|---|---|
| GET | 조회 | ✅ |
| POST | 생성 (또는 임의 action) | ❌ |
| PUT | 전체 갱신 또는 생성 | ✅ |
| PATCH | 부분 갱신 | ❌ (대부분) |
| DELETE | 삭제 | ✅ |
| HEAD | 헤더만 (body 없이) | ✅ |
| OPTIONS | 지원 method 조회 (CORS preflight) | ✅ |

### 7.4 *HTTPS = HTTP + TLS*

```text
[Client]                              [Server]
   │                                     │
   │ ─── TCP 3-way handshake ─────────→ │
   │ ←─────────────────────────────────── │
   │                                     │
   │ ─── TLS ClientHello ──────────────→ │
   │ ←── ServerHello + Cert ──────────── │
   │ ─── Key Exchange ─────────────────→ │
   │ ←── Finished ────────────────────── │
   │                                     │
   │ ─── HTTP Request (암호화) ─────────→ │
   │ ←── HTTP Response (암호화) ────────── │
```

→ *TLS 가 *Layer 6 (Presentation)* 위치. *TCP 위, HTTP 아래*.

자세히는 [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) 참조.

### 7.5 *HTTP 의 *진화*

| 버전 | 출시 | 핵심 |
|---|---|---|
| HTTP/0.9 | 1991 | GET 만, HTML 만 |
| HTTP/1.0 | 1996 | Header, status code |
| HTTP/1.1 | 1997 | Keep-Alive, virtual host, chunked encoding |
| HTTP/2 | 2015 | Multiplexing, binary framing, HPACK 헤더 압축 |
| HTTP/3 | 2022 | QUIC (UDP 위), 0-RTT, connection migration |

자세히는 [*심화 편 — TCP / BBR / QUIC*](/2026/06/22/network-fundamentals-tcp-state-machine-bbr-cubic-quic-mtls.html).

---

## 8. *실전 도구 — *7 가지***

### 8.1 *ping — *L3 의 *살아 있나?***

```bash
$ ping -c 4 google.com
PING google.com (142.250.207.110): 56 data bytes
64 bytes from 142.250.207.110: icmp_seq=0 ttl=115 time=12.345 ms
...
--- google.com ping statistics ---
4 packets transmitted, 4 received, 0% packet loss
round-trip min/avg/max/stddev = 10.123/12.456/14.789/0.987 ms
```

→ *ICMP Echo* 로 *서버 까지 *왕복 RTT* 측정. *기본 진단 도구*.

### 8.2 *traceroute — *경로 추적*

```bash
$ traceroute google.com
 1  192.168.0.1 (192.168.0.1)         1.234 ms     ← home router
 2  10.34.56.78 (10.34.56.78)        10.567 ms     ← ISP
 3  223.62.234.5 (223.62.234.5)      15.234 ms     ← ISP backbone
 4  ...
12  142.250.207.110 (google.com)     20.456 ms     ← destination
```

**원리** : *TTL=1, 2, 3, ...* 로 *각 hop 마다 *ICMP TTL Exceeded* 응답* 받음.

→ *어디서 *느린지 / 끊기는지* *경로 의 *어느 hop* 식별.

### 8.3 *dig — *DNS resolver*

```bash
dig +short google.com           # 짧게
dig @1.1.1.1 google.com         # 특정 resolver
dig -x 142.250.207.110          # 역방향
dig google.com MX               # mail server
```

### 8.4 *nslookup — *간단 DNS*

```bash
nslookup google.com
# Server:    1.1.1.1
# Address:   1.1.1.1#53
# Name:    google.com
# Address: 142.250.207.110
```

### 8.5 *netstat / ss — *연결 상태*

```bash
# 모든 TCP listen
ss -tln
# Local Address:Port
# 0.0.0.0:22       ← SSH
# 0.0.0.0:443      ← HTTPS
# 127.0.0.1:5432   ← PostgreSQL local

# established 연결
ss -tan state established

# process 정보
sudo ss -tnp
```

→ *어떤 포트 가 *열려 있고 *누가 듣고 있는지*.

### 8.6 *tcpdump / Wireshark — *패킷 캡처***

```bash
# 80 포트 패킷
sudo tcpdump -i any -nn 'tcp port 80' -w /tmp/dump.pcap

# 특정 host
sudo tcpdump -i any host google.com

# Wireshark 로 분석
wireshark /tmp/dump.pcap
```

→ *애플리케이션 의 *진짜 트래픽* 보는 *마지막 도구*. *handshake, header, RTT* 모두 보임.

### 8.7 *curl — *HTTP 클라이언트*

```bash
# 기본
curl https://google.com

# 헤더 보기
curl -I https://google.com

# 각 단계 시간 분리
curl -w "DNS: %{time_namelookup}s
TCP connect: %{time_connect}s
TLS handshake: %{time_appconnect}s
TTFB: %{time_starttransfer}s
Total: %{time_total}s\n" -o /dev/null -s https://google.com

# 자세한 디버그
curl -v https://google.com
```

→ *애플리케이션 의 *latency 분리* — *어디서 *느린지* 정량적 확인.

---

## 9. *현실 — *브라우저 에 google.com 입력 시 *전체 흐름*

```text
1. [Browser] : "google.com" 입력
   ↓
2. [DNS Resolution] : OS resolver → Recursive → Root → TLD → Authoritative
   → 142.250.207.110 받음 (cached 면 즉시)
   ↓
3. [TCP 3-way handshake] : Browser ↔ 142.250.207.110:443
   → 50ms (서울 ↔ 캘리포니아)
   ↓
4. [TLS handshake (TLS 1.3 1-RTT)]
   → 추가 50ms
   ↓
5. [HTTP Request] : "GET / HTTP/2..."
   ↓ Wi-Fi → Home Router → ISP → 백본 → Google AS → 데이터 센터 → 서버
   ↓
6. [Server processing] : Google 의 frontend → 로드 밸런서 → backend
   ↓
7. [HTTP Response] : "HTTP/2 200 OK ... <html>"
   ↓ 역경로
   ↓
8. [Browser rendering] : DOM 파싱, JS 실행, additional fetches (CSS, JS, image)
   ↓
9. [추가 fetch 들] : 각자 또 DNS / TCP / TLS / HTTP 사이클
```

→ *우리 가 *한 번 의 페이지 로드* 라고 *생각* 하지만 *실제 로는 *수십 개 의 *네트워크 cycle*. *각자 의 *latency 비용*. *CDN (Cloudflare)* 가 *그 cycle 의 *대부분 을 *지역 edge* 에서 *처리* 해서 *느낌 상 빠르게* 만든다.

---

## 10. *우리 클러스터 의 *네트워크 토폴로지* (현실 사례)*

```text
[Internet]
    ↓
[Cloudflare Edge POP]                ← 사용자 가 가장 가까운 *Cloudflare 노드*
    │ HTTP / TLS termination
    │ WAF, rate limit, DDoS
    ↓ 
[Cloudflare Tunnel (cfargotunnel.com)]
    │ outbound-only 연결 (NAT 우회)
    ↓
[lemuel / louise 노드 의 cloudflared (systemd)]
    │ 노드 의 *kube-proxy* 가 *NodePort* 받음
    ↓
[kube-proxy (iptables)]
    │ ClusterIP → Pod IP 변환
    ↓
[CNI (Flannel) overlay]
    │ Pod 간 *VXLAN* 통신
    ↓
[Pod 안 의 컨테이너]
```

각 단계 별 도구:
- *Cloudflare edge* — *전 세계 200+ POP*
- *Cloudflare Tunnel* — *outbound 연결 만, *방화벽 친화*
- *cloudflared* — *systemd 서비스*, *Tunnel A / B 두 개*
- *NodePort (30000~32767)* — K8s 의 *외부 노출 단순 방법*
- *kube-proxy iptables 모드* — *Service ClusterIP → Pod IP 변환*
- *Flannel VXLAN* — *Pod 간 *cross-node 통신*

→ *2026-06-19 outage* (k3s config.yaml cluster-dns 한 줄), *2026-06-22 Tunnel 라우팅 사고*, *2026-06-23 Gemini token 회전* — *모두 *이 토폴로지 의 *어느 한 곳* 의 *작은 변화* 가 *전체 의 *큰 영향*. *기초 의 깊이* 가 *진단 의 *속도* 를 *결정*.

---

## 11. *백엔드 엔지니어 의 *체크리스트***

내가 *네트워크 관련 사고* 진단 시 *순서 대로 확인* :

**L3 (IP)**:
1. `ping <target>` — *기본 reachability*
2. `traceroute <target>` — *경로 / hop loss*
3. `ip route` — *라우팅 테이블 정상*

**L4 (TCP / UDP)**:
4. `ss -tan` — *연결 상태 (ESTABLISHED, TIME_WAIT 등)*
5. `nc -zv <host> <port>` — *port reachable*
6. `tcpdump` — *실제 패킷 흐름*

**L7 (HTTP / DNS)**:
7. `dig <domain>` — *DNS 해석*
8. `curl -v <url>` — *HTTP 단계 별 시간*
9. *Browser DevTools — Network tab* — *waterfall*

**Application**:
10. *로그 / 메트릭* — *5xx, latency, error rate*

→ *위 → 아래* 순서 로 *층별 진단* — *어디 가 깨졌는지* 식별.

---

## 12. *결론 — *7 계층 의 *우아함***

> *서울 → 부산 의 *복잡성* 이 *7 계층 의 *책임 분리* 로 *단순* 해 진다. *각 계층 은 *자기 일* 만. *밑 / 위 계층 의 *세부 모름*.

오늘 정리한 *7 기초* :
1. **OSI 7 계층** — *책임 분리 의 *원칙*
2. **MAC + ARP** — *LAN 내부 의 *물리적 주소*
3. **IP + NAT** — *글로벌 주소 + private 우회*
4. **TCP vs UDP** — *신뢰성 vs 속도*
5. **DNS** — *도메인 의 *분산 lookup*
6. **HTTP / HTTPS** — *웹 의 *공통 어휘*
7. **실전 도구** — *ping / traceroute / dig / ss / tcpdump / curl*

> *백엔드 엔지니어 가 *알아야 하는 깊이* 는 *각 계층 의 *철학 과 *도구*. *그 도구 들 의 *조합* 으로 *어디 깨졌는지* 식별 가능 한 능력 — *그게 *시니어 의 *진짜 기본기*.

*"브라우저 에 google.com 입력 시 무슨 일* 이 *일어나는가"* 의 *답이 *5 분 분량 의 *흐름 으로 *입에서 *나올 수 있다면* — *기초 가 *체화 된 것*. *수만 줄 의 *코드* 와 *수십 개 의 *프레임워크* 의 *밑* 에 *이 7 계층 이 *언제나 *돈다*. *그 흐름 을 *놓치지 않는 시야* 가 *2026 년 *백엔드 의 *기본기 의 *진실*.

---

## *참고*

- *Computer Networks* (Andrew Tanenbaum, 6th ed.) — *교과서 의 표준*.
- *TCP/IP Illustrated, Vol. 1* (Kevin Fall, W. Richard Stevens, 2nd ed.).
- *Computer Networking: A Top-Down Approach* (Kurose / Ross).
- *Wireshark User's Guide* — *실전 패킷 분석*.
- *RFC 791* (IPv4), *RFC 793* (TCP), *RFC 768* (UDP), *RFC 1035* (DNS), *RFC 7230* (HTTP/1.1).
- 자매편:
  - [*심화 편 — TCP 상태 기계 / BBR / QUIC / mTLS*](/2026/06/22/network-fundamentals-tcp-state-machine-bbr-cubic-quic-mtls.html)
  - [*K8s 로드밸런서*](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html)
  - [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
