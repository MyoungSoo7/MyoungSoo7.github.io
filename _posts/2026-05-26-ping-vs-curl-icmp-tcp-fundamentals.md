---
layout: post
title: "ping 안 되면 서버 죽었다? — 새벽 3시 디버그가 가르쳐준 ICMP·TCP 기초"
date: 2026-05-26 20:45:00 +0900
categories: [networking, infra, debugging]
tags: [icmp, tcp, ping, curl, arp, kubernetes, k3s, troubleshooting, junior]
---

> *"ping 안 되니까 서버 죽었네요."*
> 
> *"그런데 `curl` 은 200 응답 오는데요."*
> 
> *"...?"*

이 짧은 대화가 *어제 새벽 3시 디버그* 의 핵심이었다. 자가 K3s 클러스터의 노드 5대 중 3대가 *ping LOSS* 인데 *kubectl 은 응답* 하고, *사용자 사이트 16개는 200 OK* 였다. 주니어 입장에서 이 상황은 *완전 혼란* 일 수 있다 — "ping 안 되는데 어떻게 동작하지?"

답은 *프로토콜 레이어가 다르기 때문*. 이 포스트는 *주니어가 알아야 할 ICMP vs TCP* 의 기초를 *실무 사고 진단* 의 맥락에서 풀어본다.

> ⚠️ 보안 — 도메인 / 노드명 / IP 일부는 redacted. 구조만 공유.

---

## TL;DR — 3줄

1. `ping` 은 **ICMP** 라는 *별도 프로토콜* 을 쓴다. *HTTP / SSH / 데이터베이스 등은 모두 TCP* 라는 다른 프로토콜.
2. 둘은 *완전히 분리된 경로* 로 처리될 수 있다 — *ICMP 는 막혀도 TCP 는 흐른다*.
3. 그래서 *"ping 안 되면 서버 죽었다"* 는 **틀린 진단**. *진짜 살아있는지* 는 사용자가 실제로 쓰는 프로토콜 (HTTP / TCP) 로 확인해야 한다.

---

## 1. 사건 — 새벽 3시의 미스터리

작업 맥락: 자가 K3s 클러스터 5노드 (lemuel / louise / david / ilwon / solomon) 운영 중. 한 노드 (david) 의 IP 를 *.107 → .113* 으로 바꿨다. 직후 *cluster 의 cross-node 통신이 흔들렸고*, 일부 사이트가 502 / 000 으로 떨어졌다.

`ping` 으로 노드 5대를 *Mac → LAN* 으로 찍어봤다:

```bash
$ for ip in 101 107 108 109 110; do
    ping -c 1 -W 2 192.168.219.$ip 2>&1 | grep -oE 'time=[0-9.]+' | head -1
  done
# (출력 결과 - 192.168.219.101, .107, .108, .109, .110 전부 LOSS)
```

전부 *LOSS*. 5대 노드 *모두 죽었다*?

그 직후 같은 IP 로 `kubectl` 시도:

```bash
$ kubectl get nodes
NAME      STATUS                     ROLES                AGE   VERSION
david     NotReady                   <none>               20h   v1.35.4+k3s1
ilwon     Ready                      control-plane,etcd   15d   v1.35.4+k3s1
lemuel    Ready,SchedulingDisabled   control-plane,etcd   34d   v1.35.4+k3s1
louise    Ready                      <none>               14d   v1.35.4+k3s1
solomon   NotReady                   control-plane,etcd   14d   v1.35.4+k3s1
```

**응답 옴.** 그것도 ilwon API server (192.168.219.110:6443) 와의 TCP 통신 성공. 그런데 같은 .110 으로 *ping 은 안 됨*.

curl 로 사이트도 찍어봤다:

```bash
$ curl -sI -m 5 https://xr.lemuel.co.kr
HTTP/2 200
```

*HTTP 200*. 외부에서 → Cloudflare → tunnel → louise (192.168.219.111) 까지의 *수십 hop 의 TCP 경로* 가 정상 동작. 그런데 *Mac 에서 louise 로 ping* 만 안 됨.

말이 안 된다.

— *말이 된다.* ICMP 와 TCP 는 다른 프로토콜이고, 다른 경로로 처리될 수 있다.

---

## 2. ICMP 란?

**ICMP** (Internet Control Message Protocol) 는 *네트워크 진단·제어* 를 위한 메시지 프로토콜이다. RFC 792 에 정의됐고, 1981년부터 존재한다.

ICMP 의 핵심 특징:

| 항목 | 설명 |
|---|---|
| **목적** | 진단 (ping), 라우팅 오류 통보 (`Destination unreachable`), TTL 만료 (`Time exceeded`) 등 |
| **데이터 운반?** | 아님. *제어 메시지 만* 운반 |
| **연결 지향?** | 아님. *비연결 (connectionless)* — TCP 같은 handshake 없음 |
| **포트?** | 없음. *L3 (네트워크 계층)* 의 프로토콜 |
| **신뢰성?** | 없음. UDP 처럼 *best-effort*, 손실 시 재전송 안 함 |

`ping` 명령어는 ICMP 의 *Echo Request (Type 8)* 메시지를 보내고 *Echo Reply (Type 0)* 를 기다리는 도구일 뿐이다. 응답이 오면 "살아있음", 안 오면 "응답 없음" 으로 보여준다 — 단지 그뿐.

```
ping client  ──[ICMP Echo Request type=8]──>  target
ping client  <─[ICMP Echo Reply  type=0]──   target
```

---

## 3. TCP 란?

**TCP** (Transmission Control Protocol) 는 *데이터 전송* 을 위한 *연결 지향 신뢰성 프로토콜*. RFC 793. 1981년 같은 해 정의됐지만 *목적이 완전히 다르다*.

TCP 의 핵심 특징:

| 항목 | 설명 |
|---|---|
| **목적** | 두 호스트 간 *데이터 스트림* 의 *순서 보장* + *재전송* + *흐름 제어* |
| **데이터 운반?** | 핵심 기능. HTTP, SSH, 데이터베이스, gRPC 등 *거의 모든 응용 프로토콜* 이 TCP 위에서 동작 |
| **연결 지향?** | 그렇다. 3-way handshake (SYN → SYN/ACK → ACK) 로 *세션 수립* 후 데이터 전송 |
| **포트?** | 있다. *L4 (전송 계층)*. HTTPS=443, SSH=22, PostgreSQL=5432 등 |
| **신뢰성?** | *재전송* + *순서 보장* + *흐름 제어*. 패킷 손실되면 다시 보냄 |

HTTP / kubectl / SSH 가 모두 TCP 위에서 동작하므로, *ping 안 돼도 TCP 가 흐르면 모든 응용은 정상* 이다.

```
client  ──[TCP SYN]──────────────────>  server  : 시작
client  <─[TCP SYN+ACK]──────────────   server  : 동의
client  ──[TCP ACK]──────────────────>  server  : 연결 수립
client  ──[HTTP GET /healthz]────────>  server  : 데이터 전송
client  <─[HTTP/2 200 OK]────────────   server  : 응답
```

---

## 4. *둘이 같이 안 가는* 4가지 시나리오

ICMP 와 TCP 가 *같은 호스트* 를 향해도 *다른 결과* 가 나오는 흔한 시나리오:

### 4.1. ARP 캐시 stale (가장 흔함)

OS 는 LAN 의 *같은 서브넷 IP* 와 *MAC 주소* 매핑을 ARP 캐시에 저장한다. 호스트 IP 가 *바뀌면* 이 캐시가 stale 되어, *옛 MAC* 으로 패킷을 보내려고 한다. 그 MAC 이 존재하지 않거나 다른 호스트의 것이면 패킷이 *drop* 된다.

```
[Mac]                      [Network]              [server]
ARP cache:
  192.168.219.111 -> AA:BB:CC:DD:EE:FF (OLD)
                       ↑ stale, 실제론 99:88:77:66:55:44
```

**왜 ICMP 는 막히고 TCP 는 통과?** — 두 프로토콜 모두 ARP 캐시에 *영향 받지만*, *TCP 는 SYN 재전송* + *상위 계층의 connection retry* 가 있어서 *재시도 중에 ARP 캐시가 자동 갱신* 되면 성공한다. ICMP 는 *재시도 없음, 단발성* 이라 한 번 drop 되면 그대로 *LOSS* 로 보인다.

해결:

```bash
# 강제 ARP 캐시 비우기 (Mac)
sudo arp -d -a

# 또는 OS 가 ~5분 후 자동 만료
```

### 4.2. 라우터·스위치의 QoS / Rate-limit

가정용 또는 SOHO 라우터 / 스위치 일부는 *ICMP 트래픽 우선순위를 낮추거나 rate-limit* 한다. 이유: ICMP flood attack 방지, 또는 *진단 트래픽이 데이터 트래픽을 방해하지 않게*. 

결과: *TCP 데이터는 흐르는데 ICMP ping 만 drop 된다*. 일부 ISP / 통신사 장비도 마찬가지.

해결: 다른 진단 도구 사용 (curl, telnet, nc).

### 4.3. iptables / 방화벽 룰 — *ICMP 만 차단*

서버 운영자가 *보안 정책* 으로 ICMP 만 명시적으로 차단:

```bash
# Linux 의 흔한 룰
iptables -A INPUT -p icmp -j DROP    # ICMP 전부 drop
iptables -A INPUT -p tcp -j ACCEPT   # TCP 는 통과
```

이유: *DDoS amplifier 회피*, *호스트 스캔 회피*, *내부 정책*. 클라우드 (AWS / GCP) 의 default security group 도 일부는 ICMP 차단이 기본.

### 4.4. 운영체제의 *ICMP rate-limit*

Linux 커널의 `net.ipv4.icmp_ratelimit` 가 *기본 1000ms 당 1개 응답* 으로 제한한다. 단발 ping 은 통과하지만 *연속 ping (`ping -i 0.1`)* 시 일부 drop. 이게 *간헐적 LOSS* 의 원인일 수도.

```bash
$ sysctl net.ipv4.icmp_ratelimit
net.ipv4.icmp_ratelimit = 1000
```

---

## 5. 실무 진단 워크플로우 — *ping 만 의존하지 말 것*

주니어 시절 흔한 실수: *ping 안 되면 서버 죽었다고 결론*. *시니어의 진단* 은 *layered* 다 — 여러 도구로 *각 레이어를 따로 확인*.

### 5.1. *Layered 진단* 체크리스트

```
사용자 신고: "사이트 안 되요!"
   │
   ├─ L1: 물리 (전원·케이블)
   │   └─ 콘솔/모니터 확인. 서버 *전원 들어와 있나*.
   │
   ├─ L2: 데이터링크 (스위치·MAC)
   │   └─ 스위치 포트 LED 깜빡이는지. ip link.
   │
   ├─ L3: 네트워크 (IP·ICMP)
   │   ├─ ping <target>          : ICMP 응답 확인
   │   ├─ traceroute <target>    : 경로 추적
   │   └─ arp -a                 : ARP 캐시 stale?
   │
   ├─ L4: 전송 (TCP/UDP)
   │   ├─ nc -vz <ip> <port>     : 특정 포트 reachability
   │   ├─ telnet <ip> <port>     : TCP handshake 확인
   │   └─ ss -tlnp               : listen 중인 포트
   │
   └─ L7: 응용 (HTTP/HTTPS)
       ├─ curl -v https://...    : 실제 응답 받기
       ├─ openssl s_client       : TLS handshake
       └─ kubectl / DB client    : 실제 사용자 워크플로우
```

각 레이어가 *독립적* 이라 — *L3 이 막혀도 L4 / L7 은 통과 가능*. 진단은 *위에서 아래* 또는 *아래에서 위* 로 차례로 확인.

### 5.2. *어제 새벽 3시 진단의 실제 흐름*

```bash
# Step 1: L3 (ICMP) — 전부 LOSS
$ for ip in 101 107 108 109 110; do
    ping -c 1 -W 2 192.168.219.$ip
  done
# → 5대 모두 LOSS

# Step 2: L4 (TCP) — 일부 통과
$ for ip in 101 108 110; do
    curl -k -m 3 -sI https://192.168.219.$ip:6443/healthz
  done
# → .101 → 401 (TCP 정상, auth 만 필요)
#   .108 → 000 (TCP timeout)
#   .110 → 000 (TCP timeout)

# Step 3: L7 (HTTPS via Cloudflare) — 사이트 정상
$ curl -sI https://xr.lemuel.co.kr
HTTP/2 200
```

**결론:** *Mac 의 LAN ICMP 만 막힘 (L3)*, *TCP 는 lemuel(.101) 만 통과* (L4), *외부 → Cloudflare → cluster 의 사이트는 모두 정상* (L7). 즉 *실제 사용자 facing 영향 0*. 실제 사고는 *cluster control plane API server 일부 down* (ilwon/solomon API), *사이트 라우팅은 louise (.111) 가 받아내고 있어서 정상*.

이걸 *ping LOSS = 다 죽었다* 라고 판단했으면 *물리 콘솔로 달려가서 reboot 4대* 할 뻔 했다.

### 5.3. 권장 도구 — *ping 보다 강한 진단*

| 상황 | 도구 | 이유 |
|---|---|---|
| 호스트 살아있는지 *진짜* 확인 | `nc -vz <ip> 22` (SSH) 또는 `curl <known_port>` | TCP 도 확인 |
| 경로 끊긴 곳 확인 | `traceroute -n <ip>` (TCP 모드: `-T -p 443`) | hop 별 분리 |
| ARP 캐시 의심 | `arp -a` + `sudo arp -d -a` | stale entry 제거 |
| 포트 열려있는지 | `ss -tlnp`, `lsof -i :PORT` | listener 확인 |
| TLS 문제 | `openssl s_client -connect <ip>:443` | handshake 추적 |
| HTTP/2 응답 | `curl -v --http2 ...` | 응답 헤더·body |

---

## 6. 사이드 — UDP 도 있음 (잠깐)

ICMP / TCP 외에도 *UDP* 가 있다. 비교:

| 프로토콜 | 연결? | 신뢰성? | 용도 예 |
|---|---|---|---|
| ICMP | 비연결 | 없음 | ping, traceroute |
| TCP | 연결 지향 | 재전송·순서 | HTTP, SSH, DB |
| UDP | 비연결 | 없음 | DNS, NTP, 게임, 비디오 스트림 |

UDP 는 *TCP 와 같은 L4* 이지만 *handshake 없음 + 재전송 없음*. *지연이 더 중요한 경우* (DNS, 게임) 에 사용. ICMP 의 *형제* 가 아니라 *전혀 다른 목적의 형제*.

DNS 가 안 되는데 ping 은 되는 경우도 자주 본다 — *TCP 53 / UDP 53 / ICMP* 가 *서로 독립* 적이기 때문.

---

## 7. *L1~L7 의 OSI 모델 — 다시 보면*

OSI 7계층 모델은 대학에서 한 번씩 외우고 잊는다. 그러나 *진단 관점* 에서는 *실무적 의미* 가 분명하다.

```
┌──────────────────────────────────────────────────────┐
│ L7  응용 계층    │ HTTP / HTTPS / SSH / gRPC / DNS      │ curl, kubectl, psql
├──────────────────┼──────────────────────────────────┤
│ L6  표현 계층    │ TLS / SSL / 압축 / 인코딩            │ openssl s_client
├──────────────────┼──────────────────────────────────┤
│ L5  세션 계층    │ Session resume, NetBIOS              │ (대부분 합쳐서 처리)
├──────────────────┼──────────────────────────────────┤
│ L4  전송 계층    │ TCP / UDP / SCTP                      │ nc, telnet, ss
├──────────────────┼──────────────────────────────────┤
│ L3  네트워크     │ IP / ICMP / IPSec / ARP               │ ping, traceroute, ip route
├──────────────────┼──────────────────────────────────┤
│ L2  데이터링크   │ Ethernet / MAC / VLAN                 │ ip link, arp -a
├──────────────────┼──────────────────────────────────┤
│ L1  물리         │ 케이블 / 광섬유 / Wi-Fi 신호           │ ethtool, iwconfig
└──────────────────────────────────────────────────────┘
```

**진단 시 활용:**
- *L7 안 되면* — L4, L3, L2 *차례로* 내려가며 확인
- *L3 만 안 되면* — L4 / L7 도 안 됐을 텐데? → *ICMP 만 차단된 별 케이스*
- *L1·L2 의심* (케이블 빠짐) — *L3 부터 다 안 됨*

각 레이어는 *위 레이어의 문제를 가릴 수 없지만*, *아래 레이어의 문제는 가릴 수 있다*. 즉 *문제는 항상 가장 낮은 레이어* 의 것을 의심해 가는 게 정석.

---

## 8. 교훈 — *주니어가 가져갈 5가지*

1. **`ping` 은 *살아있는지* 의 *충분 조건 아니라 한 신호일 뿐* 이다.** *진짜 살아있는지* 는 *사용자가 쓰는 프로토콜 (HTTP / TCP)* 로 확인.

2. **반대도 마찬가지** — `curl` 안 되는데 ping 만 되면? *L7 응용 문제 (포트 안 떠있음, TLS 문제)*. 그것대로 진단 경로 다름.

3. **ARP 캐시는 *생각보다* 자주 stale 된다** — 노드 IP 변경 / DHCP 재할당 / 가상화 환경 라이브 마이그레이션 시. 한 번 의심해볼 가치.

4. **진단 도구를 *주머니 속에 4개* 항상 챙겨라:** `ping`, `nc -vz`, `curl -v`, `traceroute`. 이 4개로 *대부분의 L3~L7 문제* 를 *원격에서* 진단 가능.

5. **시니어가 *물리 콘솔까지 달려가기 전에 5분 더 진단* 하는 이유** — *물리 작업의 비용 (시간, 다른 작업 망가짐)* 이 *진단 한 번 더 하는 비용보다 100배 크다*. *ping LOSS = 다 죽었다* 가설 만으로 reboot 시도하면 안 된다.

---

## 9. 마치며

새벽 3시에 *"ping 안 되네요"* 라는 신호 하나로 패닉에 빠질 뻔했다. *layered 진단* — `ping` 다음에 `curl`, 그 다음에 `kubectl`, 그 다음에 *사용자 사이트 16개 전수 검증* — 으로 *진짜 상태* 를 정확히 보고 *최소 침습적 조치* 만 하면 됐다.

*ICMP* 는 *진단 보조 도구*. *TCP* 는 *사용자가 실제로 쓰는 길*. 둘이 *완전히 다른 프로토콜이고 다른 경로* 라는 사실을 알면, *"ping 안 되는데 사이트 정상"* 같은 모순처럼 보이는 상황도 *납득* 된다.

오늘 새벽의 디버그는 *5시간이 걸렸지만 사용자 facing 사고는 *전혀 발생하지 않았다*. 그게 *layered 진단의 가치* — *증상* 과 *원인* 을 분리해 보는 능력.

> *"Ping is a hint, not a verdict."*

— *2026-05-26 (화), 르무엘에서.*
