---
layout: post
title: "Wireshark로 실제 통신 패킷 헤더 확인하기 — ICMP·Ethernet II·IPv4 실습 정리"
date: 2026-10-26 03:22:06 +0900
categories: [Network, Wireshark, Infrastructure]
tags: [Wireshark, packet, ICMP, Ethernet, IPv4, macOS, tcpdump]
---

> 이 글은 [원문 실습 글](https://velog.io/@nyeongwoong/Wireshark%EB%A5%BC-%EC%9D%B4%EC%9A%A9%ED%95%B4%EC%84%9C-%EC%8B%A4%EC%A0%9C-%ED%86%B5%EC%8B%A0-packet-%ED%99%95%EC%9E%84%ED%95%B4%EB%B3%B4%EA%B8%B0)을 읽고 핵심 실습 흐름을 재구성한 글이다. 원문의 패킷 캡처·주소는 복제하지 않고, 각 단계의 검증 포인트와 공식 문서를 함께 정리한다.

## 결론

Wireshark 실습의 핵심은 패킷 한 개를 선택해 **링크 계층의 Ethernet II 헤더와 네트워크 계층의 IPv4 헤더를 실제 필드로 대조하는 것**이다. `route`로 기본 gateway와 인터페이스를 확인하고, 해당 인터페이스에서 캡처한 뒤 `ping`과 `icmp` Display Filter를 사용하면 이 흐름을 재현할 수 있다.[1][2][3][4][5]

## 1. 실습에서 확인하는 계층

```text
내 컴퓨터
  └─ Ethernet II
       ├─ Destination MAC
       ├─ Source MAC
       └─ EtherType: IPv4 (0x0800)
            └─ IPv4
                 ├─ Source Address
                 ├─ Destination Address
                 └─ ICMP Echo Request
```

- **MAC 주소:** Ethernet II 헤더에 위치
- **IP 주소:** IPv4 헤더에 위치
- **EtherType:** Ethernet payload가 IPv4임을 표시
- **ICMP:** IP payload 안에서 Echo Request/Reply를 표현

Wireshark의 Packet Details pane은 선택한 패킷의 프로토콜과 필드를 트리 형태로 보여준다.[5]

## 2. Wireshark 준비

Wireshark는 라이브 네트워크 데이터를 캡처하고 프로토콜 필드를 상세히 분석하는 패킷 분석기다.[2]

macOS에서는 캡처 권한과 인터페이스 접근을 먼저 확인해야 한다. 원문은 Wireshark 설치 이미지의 `Install ChmodBPF.pkg`를 통한 캡처 권한 설정을 소개한다.[1]

```text
1. Wireshark 설치
2. macOS 캡처 권한 설정
3. 현재 연결된 인터페이스 확인
4. 캡처 시작
5. 테스트 트래픽 생성
6. 캡처 중지 후 Display Filter 적용
```

실습 전에 실제 IP·인터페이스·gateway 값을 확인해야 한다. 원문의 IP 주소와 인터페이스 이름은 설명용 예시이므로 그대로 사용하지 않는다.[1]

## 3. 기본 경로와 인터페이스 확인

macOS에서 현재 기본 경로를 확인한다.

```bash
route -n get default
```

출력에서 다음 두 값을 찾는다.

| 항목 | 의미 |
| --- | --- |
| `gateway` | 일반적인 가정용 네트워크에서 ping을 보낼 공유기의 IPv4 주소 |
| `interface` | Wireshark에서 선택할 실제 네트워크 인터페이스 |

VPN이 켜져 있으면 `utun` 같은 터널 인터페이스가 기본 경로로 선택될 수 있다. 이 경우 사용자가 실제로 연결한 Wi-Fi·Ethernet 인터페이스와 캡처 목적을 분리해 확인해야 한다. Wireshark의 Capture Options는 인터페이스와 link-layer header, traffic, snaplen, monitor mode를 보여준다.[3]

## 4. ping 패킷 캡처

1. Wireshark에서 `route -n get default`로 확인한 인터페이스를 선택한다.
2. 캡처를 시작한다.
3. 별도 터미널에서 실제 gateway 주소로 한 번 ping한다.

```bash
ping -c 1 <gateway-ip>
```

`-c 1`은 한 번만 요청하도록 제한한다. 캡처가 끝나면 Wireshark의 Display Filter에 다음을 입력한다.

```text
icmp
```

Display Filter는 캡처 파일의 내용을 삭제하지 않고 화면에 표시할 패킷만 줄인다.[4] 목록에서 `Echo (ping) request`를 선택하고, `reply`와 구분한다.

요청이 보이지 않을 때는 다음을 먼저 확인한다.

- gateway 주소가 현재 연결의 라우터인지
- ping을 실행한 뒤 캡처를 시작하지 않았는지
- Wi-Fi·Ethernet 중 실제 route가 가리키는 인터페이스인지
- ARP 해석이 아직 끝나지 않아 ICMP가 뒤늦게 나간 것은 아닌지
- VPN·방화벽·네트워크 정책이 경로를 바꾸지 않았는지

## 5. Ethernet II 헤더 확인

선택한 Echo Request에서 `Ethernet II`를 펼친다.

| 필드 | 확인 내용 |
| --- | --- |
| Destination | gateway 인터페이스의 MAC 주소 |
| Source | 내 컴퓨터 인터페이스의 MAC 주소 |
| Type | IPv4 (`0x0800`) |

이번 실습은 gateway 자체를 대상으로 하므로 Ethernet Destination MAC과 IPv4 Destination Address가 모두 gateway를 가리킨다. 그러나 두 주소는 같은 헤더에 있는 것이 아니다.

```text
Ethernet II: Source MAC → Destination MAC
IPv4:         Source IP  → Destination IP
```

이 차이는 라우팅과 링크 전달을 구분하는 기본 증거다. 같은 IP 목적지라도 다음 홉이 바뀌면 Ethernet Destination MAC은 달라질 수 있지만, IP 계층의 최종 목적지는 그대로일 수 있다.

## 6. IPv4 헤더와 길이 계산

`Internet Protocol Version 4`를 펼쳐 다음 필드를 확인한다.

- Source Address
- Destination Address
- Total Length
- Protocol: ICMP

IPv4의 Total Length는 IP header와 data를 합친 datagram 길이다.[6] 따라서 캡처 화면의 Frame 길이와 IPv4 Total Length가 다를 수 있다.

원문 실습의 예처럼 Ethernet header가 캡처에 포함되고 VLAN tag가 없다면 다음과 같은 계산을 확인할 수 있다.[1]

```text
Frame length - IPv4 Total Length = Ethernet II header length
```

전형적인 Ethernet II 헤더는 Destination MAC 6바이트, Source MAC 6바이트, EtherType 2바이트로 구성돼 총 14바이트다. 단, 캡처 방식·offload·VLAN·FCS 포함 여부에 따라 화면의 길이가 달라질 수 있으므로 숫자를 기계적으로 일반화하면 안 된다.

## 7. Wi-Fi인데 Ethernet II로 보이는 경우

무선 구간의 실제 프레임은 IEEE 802.11 계층을 사용한다. 하지만 일반 캡처에서는 드라이버나 캡처 모드에 따라 상위 계층 데이터가 가상의 Ethernet 헤더와 함께 보일 수 있다.[1]

따라서 Wi-Fi에서 `Ethernet II`가 표시됐다는 사실만으로 물리 구간이 유선이라고 결론 내리면 안 된다. Wireshark의 monitor mode는 raw 802.11 헤더를 캡처할 수 있지만, 인터페이스·하드웨어·드라이버·운영체제 지원에 따라 달라지고 무선 연결이 끊길 수도 있다.[3]

```text
일반 캡처: 상위 계층 분석에 편리한 link-layer 표현
Monitor mode: 실제 802.11 무선 프레임 분석
```

## 8. FCS가 보이지 않는 이유

Ethernet Frame Check Sequence(FCS)는 프레임 오류 검출에 사용되지만, NIC·드라이버·캡처 경로가 FCS를 전달하지 않으면 Wireshark 화면에 표시되지 않을 수 있다.[1]

그러므로 다음처럼 판단해야 한다.

- 화면에 FCS가 없음 → 반드시 프레임에 없었다는 뜻은 아님
- Frame length가 예상과 다름 → 캡처된 link-layer 범위·VLAN·offload 확인
- 작은 ping이 MTU만큼 보이지 않음 → 정상일 수 있음

MTU는 전송 가능한 IP 패킷의 최대 크기이지, 모든 패킷이 항상 그 크기를 채운다는 뜻이 아니다.

## 9. 재현 명령과 증거 보존

```bash
# 기본 경로 확인
route -n get default

# 테스트 트래픽
ping -c 1 <gateway-ip>

# 터미널 캡처가 필요할 때
sudo tcpdump -i <interface> -n -e -s 0 -w capture.pcap 'icmp'
```

캡처 파일에는 다른 애플리케이션의 주소·DNS·쿠키·토큰·내부 IP가 포함될 수 있다. 공개 저장소나 블로그에 pcap·TLS key log를 올리기 전에 다음을 수행한다.

- 사설 IP·MAC·공인 IP 마스킹
- 개인정보·인증 헤더·쿠키 삭제
- 다른 프로세스 트래픽 제거
- 캡처 시간·인터페이스·필터 기록
- 원본 pcap은 공개하지 않고 로컬에서 폐기 또는 접근제어

## 10. Kubernetes·운영 RCA에 적용

이 실습은 단순한 Wireshark 사용법을 넘어 운영 장애의 계층별 검증에 연결된다.

```text
Node interface
  → route/gateway
  → ARP/next hop
  → TCP 또는 UDP
  → TLS
  → 애플리케이션 프로토콜
  → timeout·retry·response
```

예를 들어 Kubernetes API 통신 문제라면 다음을 분리한다.

- 노드 interface가 active인가
- 목적지에 선택된 route와 gateway는 무엇인가
- 다음 홉 MAC이 해석됐는가
- TCP 연결이 성립했는가
- TLS 인증서·SNI가 맞는가
- API 응답 코드와 응답 시간이 어떠한가
- 패킷 손실·재전송·jitter가 있었는가

`ping 성공`은 애플리케이션 성공이 아니고, `HTTP 200`도 응답 본문과 업무 sentinel이 유효하다는 뜻은 아니다. 각 계층의 Trace를 시간창으로 묶어야 원인과 증상을 분리할 수 있다.

## 확인된 사실과 미확인 범위

- **원문 확인:** macOS에서 gateway·interface를 확인하고 Wireshark로 ICMP Echo Request를 캡처해 Ethernet II·IPv4 필드를 확인하는 실습 흐름을 확인했다.[1]
- **공식 문서 대조:** Wireshark의 캡처 옵션·Display Filter·Packet Details pane과 IPv4 Total Length 정의를 공식 문서에서 대조했다.[2][3][4][5][6]
- **해석:** Wi-Fi 캡처 표현·FCS·운영 RCA 연결은 원문과 공식 문서를 운영 관점으로 재구성한 내용이다.
- **미확인:** 이 글은 해당 Velog 글의 실제 pcap을 다시 분석한 결과가 아니며, 특정 사용자의 인터페이스·주소·패킷 길이를 보장하지 않는다.

## 참고 자료

[1] [Velog — Wireshark를 이용해서 실제 통신 Packet Header 확인해보기](https://velog.io/@nyeongwoong/Wireshark%EB%A5%BC-%EC%9D%B4%EC%9A%A9%ED%95%B4%EC%84%9C-%EC%8B%A4%EC%A0%9C-%ED%86%B5%EC%8B%A0-packet-%ED%99%95%EC%9D%B8%ED%95%B4%EB%B3%B4%EA%B8%B0)

[2] [Wireshark User’s Guide — Live Capture](https://www.wireshark.org/docs/wsug_html_chunked/ChapterCapture.html)

[3] [Wireshark User’s Guide — Capture Options](https://www.wireshark.org/docs/wsug_html_chunked/ChCapCaptureOptions.html)

[4] [Wireshark User’s Guide — Display Filters](https://www.wireshark.org/docs/wsug_html_chunked/ChWorkDisplayFilterSection.html)

[5] [Wireshark User’s Guide — Packet Details Pane](https://www.wireshark.org/docs/wsug_html_chunked/ChUsePacketDetailsPaneSection.html)

[6] [RFC 791 — Internet Protocol](https://www.rfc-editor.org/rfc/rfc791.html)

> ※ 원문 실습의 실제 IP·MAC·캡처 화면은 재게시하지 않았으며, 예시 주소는 독자의 환경에서 확인한 값으로 대체해야 한다.

## Sources

[1] https://velog.io/@nyeongwoong/Wireshark%EB%A5%BC-%EC%9D%B4%EC%9A%A9%ED%95%B4%EC%84%9C-%EC%8B%A4%EC%A0%9C-%ED%86%B5%EC%8B%A0-packet-%ED%99%95%EC%9D%B8%ED%95%B4%EB%B3%B4%EA%B8%B0
[2] https://www.wireshark.org/docs/wsug_html_chunked/ChapterCapture.html
[3] https://www.wireshark.org/docs/wsug_html_chunked/ChCapCaptureOptions.html
[4] https://www.wireshark.org/docs/wsug_html_chunked/ChWorkDisplayFilterSection.html
[5] https://www.wireshark.org/docs/wsug_html_chunked/ChUsePacketDetailsPaneSection.html
[6] https://www.rfc-editor.org/rfc/rfc791.html
