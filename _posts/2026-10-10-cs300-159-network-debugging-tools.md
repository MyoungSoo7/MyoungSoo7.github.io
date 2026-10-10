---
layout: post
title: "[CS300 #159] 네트워크 디버깅 도구 — ping·traceroute·tcpdump 로 타임아웃의 위치 찾기"
date: 2026-10-10 20:39:00 +0900
categories: [cs]
tags: [cs300, networking, troubleshooting, tcpdump, traceroute, icmp]
---

컴퓨터공학 300 주제 시리즈의 159번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

네트워크 장애는 아래 계층부터 한 칸씩 올라가며 확인한다. 이름 풀이(dig), 도달성(ping), 경로(traceroute·mtr), 포트와 연결(ss·curl), 그리고 실제 패킷(tcpdump). 각 도구는 특정 계층의 질문 하나에 답한다.

## 왜 필요한가

이 파트의 첫 글에서 "타임아웃이 정확히 어디서 났는지 말할 수 있어야 한다"고 했다. 이 글이 그 실전편이다. "API 가 타임아웃 난다"는 보고를 받았을 때, 추측으로 설정을 바꾸기 전에 다음 질문에 증거로 답해야 한다.

1. 이름은 올바른 주소로 풀리는가?
2. 그 주소까지 패킷이 가는가? 어디서 끊기는가?
3. 포트에서 누가 듣고 있는가? 연결은 수립되는가?
4. 연결 뒤 요청은 갔는데 응답이 안 오는가, 응답이 느린가?
5. 실제로 선 위에 무엇이 오갔는가?

## 핵심 개념

### 계층별 도구 지도

| 질문 | 도구 | 보는 계층 |
|---|---|---|
| 링크가 올라왔나, 오류 카운터는? | `ip -s link`, `ethtool` | L1–L2 |
| 이웃의 MAC 을 아나? | `ip neigh` | L2–L3 |
| 경로는 어디로? | `ip route get <목적지>` | L3 |
| 상대가 살아 있나? | `ping` | L3 (ICMP) |
| 어디서 끊기나? | `traceroute`, `tracepath`, `mtr` | L3 |
| 누가 듣고 있나, 연결 상태는? | `ss -ltnp`, `ss -tan` | L4 |
| 이름이 풀리나? | `dig`, `getent hosts` | L7 (DNS) |
| HTTP 응답과 시간 분해 | `curl -v`, `curl -w` | L7 |
| 실제 패킷 | `tcpdump`, Wireshark | 전 계층 |

### ping

ping 은 ICMP Echo Request(타입 8)를 보내고 Echo Reply(타입 0)를 기다린다(ICMP 는 RFC 792). 왕복 시간과 손실률을 알려 준다.

- 응답이 오면: 3계층 도달성은 확인. 단, 그 포트의 서비스가 사는지는 모른다.
- 응답이 없으면: 상대가 죽었을 수도 있지만, ICMP 만 막혀 있을 수도 있다. 클라우드 보안 그룹은 ICMP 를 기본으로 막는 경우가 많다. "ping 이 안 되니 서버가 죽었다"는 결론은 성급하다.
- 크기와 단편화 금지 옵션으로 MTU 문제를 찾을 수 있다(158번 글).

### traceroute 와 mtr

traceroute 는 TTL 을 1, 2, 3… 으로 늘려 가며 탐침을 보낸다. TTL 이 0 이 되는 라우터마다 ICMP Time Exceeded(타입 11)를 돌려주므로, 그 응답의 출발지로 경로 위 라우터를 하나씩 알아낸다. 목적지에 닿으면 탐침 종류에 따라 Port Unreachable(UDP 탐침)이나 Echo Reply, TCP 응답으로 끝을 안다.

```
TTL=1  → 첫 라우터가 Time Exceeded  → 1번 홉
TTL=2  → 둘째 라우터가 Time Exceeded → 2번 홉
...
TTL=n  → 목적지 도달              → 끝
```

읽을 때 주의할 점:

- `* * *` 는 그 라우터가 ICMP 응답을 안 보내거나 제한했다는 뜻일 뿐, 거기서 끊겼다는 뜻이 아니다. 다음 홉들이 응답하면 경로는 이어진 것이다.
- 중간 홉의 지연이 크더라도 이후 홉이 정상이면 그 라우터가 ICMP 생성을 낮은 우선순위로 처리한 것일 수 있다. 지연은 끝까지 누적되는 경향을 봐야 한다.
- 방화벽이 UDP 탐침을 막으면 TCP SYN 탐침(`traceroute -T`, `tcptraceroute`)이 더 정확하다.

mtr 은 traceroute 와 ping 을 합쳐 각 홉의 손실률과 지연을 계속 갱신해 보여 준다. 간헐적 손실 위치를 찾는 데 좋다. tracepath 는 경로와 함께 경로 MTU 도 알려 준다.

### ss

`ss` 는 소켓 상태를 본다(옛 `netstat` 의 후계).

- `ss -ltnp`: TCP 로 듣고 있는 소켓과 프로세스. "서버가 0.0.0.0 이 아니라 127.0.0.1 에 붙어 있다"를 한눈에 본다.
- `ss -tan state syn-sent`: SYN 을 보냈는데 응답이 없는 연결. 상대 쪽 드롭을 뜻한다.
- `ss -ti`: 연결별 RTT, cwnd, 재전송 수(148번 글).

### curl 의 시간 분해

`curl -w` 는 요청 한 번을 단계별 시간으로 쪼갠다.

```
curl -s -o /dev/null -w 'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://example.com/
```

각 값은 요청 시작부터의 누적 시간이다. `connect - dns` 가 TCP 핸드셰이크, `tls - connect` 가 TLS, `ttfb - tls` 가 서버 처리 시간에 가깝다. "느리다"를 "DNS 가 느리다"나 "서버 처리가 느리다"로 바꿔 주는 가장 싼 도구다.

### tcpdump

결국 패킷을 봐야 끝나는 문제가 있다. tcpdump 는 인터페이스의 패킷을 BPF 필터로 골라 보여 주거나 파일로 저장한다.

```
tcpdump -ni eth0 'host 198.51.100.20 and tcp port 443'      # 특정 상대와 443 만
tcpdump -ni any 'tcp[tcpflags] & (tcp-syn|tcp-rst) != 0'    # SYN 과 RST 만
tcpdump -ni eth0 -w cap.pcap 'port 53'                      # 파일로 저장 후 Wireshark 로 분석
```

- `-n` 은 이름 풀이를 끈다. 디버깅 중 DNS 질의를 더 만들지 않고 출력도 빠르다.
- 필터 문법은 pcap-filter(7) 매뉴얼에 있다.
- 양쪽 끝에서 동시에 캡처하면 "보냈는데 안 왔다"와 "왔는데 응답을 안 했다"를 구분할 수 있다. 패킷 캡처에는 민감한 데이터가 담기므로 저장·공유에 주의한다.

### 증상으로 위치 좁히기

| 증상 | 의미 | 다음 확인 |
|---|---|---|
| 이름 풀이 실패 | DNS | `dig`, resolv.conf, 검색 도메인 |
| Connection refused | 패킷은 도달, 포트에 듣는 프로세스 없음(RST) | `ss -ltnp`, bind 주소 |
| 연결 타임아웃 | SYN 에 응답 없음. 경로나 방화벽 드롭 | traceroute, 방화벽 규칙, `tcpdump` 로 SYN 확인 |
| 연결은 되는데 응답 타임아웃 | 앱이 느리거나 멈춤, 또는 큰 패킷만 사라짐 | 서버 로그, `curl -w`, MTU |
| 간헐적 실패 | 일부 백엔드·경로 문제, 손실 | mtr, LB 백엔드별 확인 |

## 직접 해 보기

로컬호스트에서 세 가지 실패 유형(거부, 읽기 타임아웃, 정상)을 만들고 분류하는 작은 진단기를 만든다. 그리고 tcpdump 가 저장하는 pcap 파일 형식으로 패킷 하나를 기록했다가 다시 읽어 본다.

```python
import socket, struct, threading, time, io

def probe(host, port, connect_timeout=1.0, read_timeout=1.0):
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((host, port), timeout=connect_timeout)
    except ConnectionRefusedError:
        return "REFUSED (RST 수신: 포트에 듣는 프로세스 없음)"
    except socket.timeout:
        return "CONNECT TIMEOUT (SYN 무응답: 경로·방화벽)"
    t1 = time.perf_counter()
    s.settimeout(read_timeout)
    try:
        s.sendall(b"PING\n")
        data = s.recv(100)
        return f"OK connect={1000*(t1-t0):.1f}ms reply={data!r}"
    except socket.timeout:
        return "READ TIMEOUT (연결은 됐으나 응답 없음: 앱 문제)"
    finally:
        s.close()

def server(reply):
    ls = socket.create_server(("127.0.0.1", 0))
    def run():
        while True:
            c, _ = ls.accept()
            if reply: c.recv(100); c.sendall(b"PONG\n")
            # reply=False 이면 받기만 하고 아무 응답도 안 함
    threading.Thread(target=run, daemon=True).start()
    return ls.getsockname()[1]

good, silent = server(True), server(False)
tmp = socket.create_server(("127.0.0.1", 0)); closed = tmp.getsockname()[1]; tmp.close()

for name, port in (("정상 서버", good), ("응답 안 하는 서버", silent), ("닫힌 포트", closed)):
    print(f"{name:12s} -> {probe('127.0.0.1', port)}")

# pcap 형식: 전역 헤더 24바이트 + (레코드 헤더 16바이트 + 패킷) 반복
pkt = bytes.fromhex("00005e005302" "00005e005301" "0800") + bytes(20) + bytes(8)
buf = io.BytesIO()
buf.write(struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))  # linktype 1 = Ethernet
buf.write(struct.pack("<IIII", 1700000000, 123456, len(pkt), len(pkt)) + pkt)
raw = buf.getvalue()

magic, vmaj, vmin, _, _, snaplen, linktype = struct.unpack("<IHHiIII", raw[:24])
ts, us, incl, orig = struct.unpack("<IIII", raw[24:40])
frame = raw[40:40+incl]
print(f"pcap v{vmaj}.{vmin} linktype={linktype} | 패킷 {incl}B, 목적지 MAC {frame[:6].hex(':')}, EtherType 0x{frame[12:14].hex()}")
```

```
정상 서버        -> OK connect=9.7ms reply=b'PONG\n'
응답 안 하는 서버   -> READ TIMEOUT (연결은 됐으나 응답 없음: 앱 문제)
닫힌 포트        -> REFUSED (RST 수신: 포트에 듣는 프로세스 없음)
pcap v2.4 linktype=1 | 패킷 42B, 목적지 MAC 00:00:5e:00:53:02, EtherType 0x0800
```

연결 시간은 실행 환경에 따라 조금씩 다르다. 중요한 건 같은 "실패"가 세 가지로 갈린다는 점이다. 응답 안 하는 서버의 경우 TCP 연결은 커널이 수립해 주므로 연결은 성공하고, 읽기에서 타임아웃이 난다. 연결 타임아웃과 읽기 타임아웃을 하나의 숫자로 묶어 설정하면 이 구분이 사라진다. 로컬호스트에서는 SYN 을 버리는 상황을 만들기 어려워 CONNECT TIMEOUT 은 재현하지 않았다. pcap 파일은 이렇게 단순한 구조라 tcpdump 로 저장한 파일을 Wireshark 나 직접 만든 스크립트로 다시 읽을 수 있다.

## 현업에서는

- 쿠버네티스 파드 안에는 디버깅 도구가 없는 경우가 많다. `kubectl debug` 로 도구가 든 임시 컨테이너를 붙이거나, 노드에서 파드의 네트워크 네임스페이스에 들어가 tcpdump 를 돈다.
- 타임아웃 값은 계층별로 따로 정하고 로그에 어떤 타임아웃인지 남긴다. "timeout" 한 단어보다 "connect timeout to 198.51.100.20:443 after 1s" 가 장애 시간을 크게 줄인다.
- 홈랩 클러스터처럼 노드가 몇 대 안 되는 환경에서도, 노드 간 통신 문제는 양쪽 노드에서 동시에 tcpdump 를 떠서 비교하는 게 가장 빠르다. 캡처 파일과 출력에는 내부 주소와 MAC 이 그대로 담기므로 외부에 공유할 때는 지운다.
- 증거를 모은 다음에 설정을 바꾼다. 원인을 모른 채 타임아웃만 늘리면 장애는 느린 장애로 바뀔 뿐이다.

## 확인 문제

1. ping 이 실패했는데 HTTPS 접속은 되는 경우가 있다. 왜인가?
2. traceroute 출력의 5번 홉이 `* * *` 이고 6번 홉부터 정상이다. 5번 홉에서 패킷이 버려지고 있는가?
3. `curl -w` 결과가 `dns=0.002 connect=0.010 tls=0.030 ttfb=2.900` 이다. 어느 구간이 느린가?
4. "Connection refused" 와 "connection timed out" 을 받았을 때 각각 먼저 확인할 것은?
5. tcpdump 에 `-n` 옵션을 주는 이유 두 가지는?

### 풀이

1. ICMP 가 방화벽이나 보안 그룹에서 막혀 있고 TCP 443 은 열려 있기 때문이다.
2. 아니다. 5번 홉 라우터가 ICMP Time Exceeded 를 보내지 않거나 제한할 뿐이다. 6번 홉 이후가 응답하므로 패킷은 5번 홉을 통과하고 있다.
3. TLS 완료(0.030초)부터 첫 바이트(2.9초)까지, 곧 서버(또는 그 뒤 백엔드)의 요청 처리 구간이다.
4. refused 는 서버에서 해당 포트에 듣는 프로세스와 bind 주소(`ss -ltnp`)를, timed out 은 경로와 방화벽(traceroute, 보안 그룹, tcpdump 로 SYN 도착 여부)을 먼저 본다.
5. 주소를 이름으로 바꾸는 DNS 질의를 만들지 않아 관찰 대상을 오염시키지 않고, 출력이 지연되지 않게 하기 위해서다.

## 더 읽을거리 (References)

- RFC 792, *Internet Control Message Protocol*: <https://www.rfc-editor.org/rfc/rfc792.html>
- tcpdump(1) 매뉴얼과 pcap-filter(7): <https://www.tcpdump.org/manpages/tcpdump.1.html>, <https://www.tcpdump.org/manpages/pcap-filter.7.html>
- mtr(8), tracepath(8) 매뉴얼: <https://manpages.debian.org/bookworm/mtr-tiny/mtr.8.en.html>, <https://manpages.debian.org/bookworm/iputils-tracepath/tracepath.8.en.html>
- curl 매뉴얼(`-w` 변수): <https://curl.se/docs/manpage.html>
