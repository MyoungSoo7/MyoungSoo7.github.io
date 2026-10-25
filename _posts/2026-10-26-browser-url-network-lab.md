---
layout: post
title: "브라우저 주소창에 URL을 입력하면 무슨 일이 일어나는가 — 실습 글을 바탕으로 재구성한 네트워크 흐름"
date: 2026-10-26 03:14:53 +0900
categories: [Network, Web, Infrastructure]
tags: [DNS, DHCP, ARP, TCP, TLS, HTTP2, tcpdump, Wireshark, 실습]
---

> 이 글은 [rgunny.tistory.com의 네트워크 실습 글](https://rgunny.tistory.com/m/16)을 읽고, 그 실습 흐름을 공개 가능한 형태로 재구성한 기술 해설이다. 원문의 명령·관측을 그대로 복제하지 않고, 핵심 개념과 검증 포인트를 별도 설명한다. RFC와 원문 관측을 구분하며, 원문에 포함된 사설 주소·MAC·공인 식별자는 이 글에서 재게시하지 않는다.

## 결론

브라우저 주소창에 `https://www.google.com`을 입력하는 순간 애플리케이션 요청만 발생하는 것이 아니다. 운영체제는 먼저 **인터페이스·DHCP·라우팅·ARP·DNS**를 통해 목적지에 도달할 경로를 준비하고, 이후 **TCP·TLS·HTTP/2**를 차례로 사용해 암호화된 웹 요청을 전달한다.[1][2][3][4][5][6]

```text
링크 연결
  → DHCP 주소·게이트웨이·DNS 확보
  → 라우팅 경로 선택
  → ARP로 다음 홉의 링크 주소 확인
  → DNS로 도메인 이름을 IP로 변환
  → TCP 연결
  → TLS 협상
  → HTTP/2 요청·응답
  → 하위 리소스 병렬 다운로드
  → 연결 유지 또는 종료
```

## 1. 출발점: 유선과 Wi-Fi 인터페이스

원문 실습은 macOS에서 유선 인터페이스와 Wi-Fi 인터페이스가 동시에 연결된 상황을 비교했다.[1] 유선은 링크 속도·duplex 협상과 포트 상태를 확인하고, Wi-Fi는 AP·주파수 대역·채널·보안·신호와 잡음 수준을 확인하는 방식이다.

여기서 중요한 점은 **인터페이스가 연결되어 있다는 사실과 실제 목적지 트래픽이 그 인터페이스로 나간다는 사실이 다르다**는 것이다. 두 인터페이스가 모두 활성화돼도 운영체제는 목적지와 라우팅 우선순위를 바탕으로 하나의 경로를 선택한다.

확인 예시는 다음과 같다.

```bash
ifconfig <interface>
networksetup -listallhardwareports
route -n get <destination-ip>
system_profiler SPAirPortDataType
```

실습에서는 `route -n get`으로 특정 목적지에 선택된 인터페이스를 먼저 확인한 뒤 패킷을 캡처했다.[1] 이 순서를 지키지 않으면 유선 문제를 조사한다고 생각하면서 실제로는 Wi-Fi 트래픽을 캡처하는 오류가 생긴다.

## 2. DHCP: IP와 네트워크 설정을 받는다

새 인터페이스가 네트워크에 붙으면 DHCP 서버로부터 IP 주소와 네트워크 설정을 받을 수 있다. DHCP는 호스트에 네트워크 구성 정보를 전달하고, 동적·자동·수동 방식으로 주소를 할당하는 구조를 정의한다.[3]

전형적인 흐름은 다음과 같다.

```text
DHCPDISCOVER
      ↓
DHCPOFFER
      ↓
DHCPREQUEST
      ↓
DHCPACK
```

실습에서는 `tcpdump`로 DHCP 포트 67·68 트래픽을 캡처해 이 교환을 관측했다.[1]

```bash
tcpdump -i <interface> -n -v -e 'port 67 or port 68'
```

DHCP ACK에는 보통 다음 정보가 포함된다.

- 할당된 IP 주소
- 서브넷 마스크
- 기본 게이트웨이
- DNS 서버
- 임대 시간

클라이언트가 요청한 임대 시간과 DHCP 서버가 실제로 부여한 임대 시간은 다를 수 있다. 따라서 클라이언트 설정만 보고 임대 정책을 단정하지 말고, Offer·ACK를 함께 확인해야 한다.[1][3]

## 3. 라우팅: 직접 보낼 것인가, 게이트웨이로 보낼 것인가

운영체제는 목적지 IP가 같은 로컬 네트워크에 있는지, 외부 네트워크에 있는지 판단한다. 로컬 목적지라면 같은 세그먼트의 장비로 직접 보내고, 외부 목적지라면 기본 게이트웨이로 패킷을 전달한다.

```bash
route -n get <local-gateway>
route -n get <dns-server>
netstat -rn
```

원문 실습의 중요한 관측은 유선과 Wi-Fi가 모두 연결된 상태에서 기본 경로가 한쪽 인터페이스로만 선택된다는 점이다.[1] 인터페이스가 둘 다 살아 있다는 이유만으로 트래픽이 자동 분산되는 것은 아니다.

**운영 판단:** 특정 경로의 품질을 비교하려면 인터페이스를 명시한 ping·traceroute·tcpdump와 `route -n get` 결과를 같은 시간창으로 묶어야 한다.

## 4. ARP: 다음 홉의 MAC 주소를 찾는다

IPv4 패킷을 Ethernet 프레임에 실으려면 다음 홉의 링크 계층 주소가 필요하다. ARP는 프로토콜 주소와 48비트 Ethernet 주소의 대응을 찾는 절차를 제공한다.[2]

```bash
arp -an
tcpdump -i <interface> -n -e arp
```

ARP 캐시에 다음 홉 정보가 있으면 바로 프레임을 만들 수 있다. 없거나 만료되면 요청을 브로드캐스트하고, 해당 IP를 가진 장비가 Reply로 자신의 링크 주소를 알려준다.[2]

```text
ARP Request: Who has <next-hop-ip>?
ARP Reply:   <next-hop-ip> is-at <mac-address>
```

패킷 캡처에서 ARP Request와 Reply를 확인하면 “라우팅은 게이트웨이를 선택했고, 링크 계층은 그 게이트웨이의 MAC을 확보했다”는 흐름을 분리해서 증명할 수 있다.

## 5. DNS: 이름을 IP 주소로 변환한다

브라우저는 URL의 호스트 이름을 IP 주소로 변환해야 한다. DNS는 이름 공간을 분산 데이터베이스로 관리하고, resolver가 name server에 질의해 주소·별칭 등 필요한 정보를 얻는 구조다.[4]

실습에서는 운영체제 resolver 경로와 `dig`의 직접 질의를 비교했다.[1]

```bash
scutil --dns
dscacheutil -q host -a name www.google.com
dig A www.google.com
```

이 세 명령은 항상 같은 계층을 의미하지 않는다.

- `scutil --dns`: macOS가 사용할 resolver 설정 확인
- `dscacheutil`: 운영체제 이름 조회 경로와 캐시 확인
- `dig`: 지정한 DNS 서버에 직접 질의하거나 DNS 질의 결과 확인

`/etc/hosts`에 테스트 이름을 넣었을 때 운영체제 조회와 `dig` 결과가 달라질 수 있다는 실습은 **DNS 질의와 로컬 이름 조회 경로를 동일시하면 안 된다**는 점을 보여준다.[1][4]

## 6. TCP: 웹 서버와 연결을 만든다

DNS 결과를 얻은 뒤 브라우저는 목적지의 HTTPS 포트로 TCP 연결을 시작한다. TCP는 연결 설정·신뢰성 있는 바이트 스트림·혼잡 제어·연결 종료를 제공하는 전송 계층 프로토콜이다.[5]

전형적인 연결 설정은 다음과 같다.

```text
Client → SYN
Server → SYN/ACK
Client → ACK
```

이후 TLS 협상과 애플리케이션 데이터 교환이 진행된다. 연결 종료 시에는 FIN·ACK 교환이 나타나며, 양쪽이 비슷한 시점에 종료를 시작하면 동시 종료처럼 일반적인 순서와 다른 패킷 흐름도 관찰될 수 있다.[1][5]

```bash
sudo tcpdump -i <interface> -n 'host <server-ip> and port 443'
netstat -an -p tcp
lsof -i :443
```

여기서 `SYN`이 보였다고 웹 요청이 성공한 것은 아니다. TCP 연결, TLS 협상, HTTP 응답을 각각 확인해야 한다.

## 7. TLS: TCP 위에 암호화된 세션을 만든다

HTTPS는 TCP 연결 위에서 TLS 협상을 수행한다. 이 단계에서 브라우저와 서버는 암호화 방식·키 교환·인증서를 확인하고 이후 HTTP 데이터를 암호화한다.

```bash
openssl s_client -connect www.google.com:443 -servername www.google.com
```

패킷 캡처만으로는 TLS 이후 HTTP 헤더와 본문을 읽을 수 없다. 원문 실습은 브라우저의 TLS key log와 pcap을 Wireshark/tshark에 연결해 HTTP/2 프레임을 분석하는 방법을 소개한다.[1]

단, TLS 키 로그와 pcap에는 다른 애플리케이션의 트래픽이나 세션 정보가 포함될 수 있다. 실습이 끝난 뒤 공개 저장소에 올리지 말고, 쿠키·토큰·개인정보가 포함됐는지 확인한 후 안전하게 폐기해야 한다.

## 8. HTTP/2: 하나의 연결에서 여러 요청을 multiplexing한다

HTTP/2는 헤더 필드 압축과 하나의 연결에서 여러 교환을 동시에 처리하는 multiplexing을 통해 네트워크 자원을 효율적으로 사용하고 지연을 줄이는 것을 목표로 한다.[6]

HTTP/1.1의 요청 개념은 HTTP/2에서 다음과 같은 pseudo-header로 표현될 수 있다.

```text
:method    GET
:authority www.google.com
:scheme    https
:path      /
```

HTTP/2는 요청마다 stream ID를 부여하고, HEADERS·DATA 프레임을 사용한다. 따라서 브라우저가 HTML·CSS·JavaScript·이미지를 요청할 때 TCP 연결 여러 개를 무조건 새로 만들지 않고 기존 연결 위에서 여러 stream을 사용할 수 있다.[1][6]

원문 실습에서는 DevTools와 tshark를 이용해 요청 수, 전송량, 리소스 크기, HTTP/2 stream, `content-encoding`을 확인했다.[1]

```bash
tshark -r <pcap> -2 \
  -o tls.keylog_file:<keylog> \
  -Y 'http2.streamid == <stream-id>' \
  -O http2
```

## 9. 실습을 재현할 때의 안전한 순서

```text
1. 목적지와 인터페이스를 기록
2. route -n get으로 실제 경로 확인
3. IP·게이트웨이·DNS 설정 확인
4. ARP 캐시와 다음 홉 확인
5. DNS 조회 결과 확인
6. TCP 443 연결 확인
7. TLS 인증서·협상 확인
8. 브라우저 DevTools에서 HTTP 요청 확인
9. 필요할 때만 pcap과 TLS key log로 HTTP/2 분석
10. 민감한 캡처·키 로그 폐기
```

### 검증 결과를 분리해서 기록하기

| 단계 | 성공의 증거 | 성공으로 오해하면 안 되는 것 |
| --- | --- | --- |
| 링크 | interface active, AP 연결 | 인터넷 사용 가능 전체 보장 |
| DHCP | ACK와 IP·gateway·DNS | 외부 목적지 접근 보장 |
| 라우팅 | 목적지별 선택 interface/gateway | 패킷 전달 성공 |
| ARP | Request/Reply 또는 캐시 항목 | DNS 성공 |
| DNS | A/AAAA 응답 | TCP·TLS 성공 |
| TCP | SYN/ACK와 연결 상태 | HTTP 200 |
| TLS | 인증서·handshake 완료 | 애플리케이션 응답 유효성 |
| HTTP/2 | HEADERS·DATA·status 확인 | HTML이 사용자에게 정상 표시됨 |

## 10. Kubernetes·운영 네트워크와 연결되는 지점

이 실습은 단순한 면접 질문 풀이가 아니라 운영 장애 분석의 기본 프레임으로도 사용할 수 있다. 예를 들어 Kubernetes API server에 접근하지 못할 때 곧바로 “클러스터 장애”라고 하지 말고, 링크·DHCP·라우팅·ARP·DNS·TCP·TLS·HTTP 계층을 분리해서 확인해야 한다.

```text
노드 링크 상태
→ 노드 IP·gateway·DNS
→ 목적지 route
→ 다음 홉 ARP
→ API server 이름 해석
→ TCP 6443 연결
→ TLS 인증서·SNI
→ Kubernetes API 응답
```

이 계층 중 어디에서 실패했는지를 확인하면 무선 링크 문제, DNS 문제, 방화벽·라우팅 문제, API server 문제를 분리할 수 있다. 단일 `curl` 실패나 단일 ping 성공만으로 원인을 확정하지 않는 것이 핵심이다.

## 확인된 사실과 미확인 범위

- **원문 관측:** 제공된 실습 글은 macOS에서 유선·Wi-Fi 인터페이스, DHCP, 라우팅, ARP, DNS, TCP, TLS, HTTP/2를 명령어와 패킷 캡처로 단계별 확인한다.[1]
- **표준 근거:** ARP·DHCP·DNS·TCP·HTTP/2의 역할은 각각 RFC 문서와 대조했다.[2][3][4][5][6]
- **재구성:** 이 글의 Kubernetes 운영 연결과 계층별 판정표는 원문 실습을 운영·RCA 관점으로 재구성한 해석이다.
- **미확인:** 원문 작성자의 실험 환경을 이 호스트에서 동일하게 재현한 것은 아니다. 특정 네트워크의 실제 지연·손실·경로는 별도 Trace가 필요하다.

## 참고 자료

[1] [rgunny — 브라우저 주소창에 www.google.com을 입력하면 나타나는 일: 실습](https://rgunny.tistory.com/m/16)

[2] [IETF RFC 826 — ARP](https://datatracker.ietf.org/doc/html/rfc826)

[3] [IETF RFC 2131 — DHCP](https://datatracker.ietf.org/doc/html/rfc2131)

[4] [IETF RFC 1035 — DNS](https://datatracker.ietf.org/doc/html/rfc1035)

[5] [IETF RFC 9293 — TCP](https://datatracker.ietf.org/doc/html/rfc9293)

[6] [IETF RFC 9113 — HTTP/2](https://datatracker.ietf.org/doc/html/rfc9113)

> ※ 원문 실습에 포함된 사설 IP·MAC·공인 네트워크 식별자·쿠키·TLS key log·pcap은 재게시하지 않았다.

## Sources

[1] https://rgunny.tistory.com/m/16
[2] https://datatracker.ietf.org/doc/html/rfc826
[3] https://datatracker.ietf.org/doc/html/rfc2131
[4] https://datatracker.ietf.org/doc/html/rfc1035
[5] https://datatracker.ietf.org/doc/html/rfc9293
[6] https://datatracker.ietf.org/doc/html/rfc9113
