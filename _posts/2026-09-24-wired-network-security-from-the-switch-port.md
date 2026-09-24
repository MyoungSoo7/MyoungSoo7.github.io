---
layout: post
title: "유선 네트워크 보안 — '케이블을 꽂을 수 있으면 신뢰한다'를 깨는 법"
date: 2026-09-24 20:14:45 +0900
categories: [Security, Network]
tags: [네트워크보안, 802.1X, MACsec, DHCPSnooping, DAI, VLAN, STP, L2보안]
---

무선 네트워크를 설계할 때는 누구나 "전파는 벽을 넘는다" 를 전제로 한다. 그래서 WPA, 802.1X, 게스트 분리 같은 것을 당연하게 챙긴다. ([무선 인증 글](/2026/08/25/wireless-auth-802-1x-eap-radius-and-the-java-stack/)에서 이 쪽을 다뤘다.)

유선은 다르다. 대부분의 사내망과 홈랩은 여전히 이렇게 돌아간다.

> **"건물 안에서 케이블을 꽂을 수 있다면, 신뢰해도 된다."**

이 글은 그 암묵적 신뢰가 L2(이더넷) 어디서 깨지는지, 그리고 스위치 포트부터 위로 어떻게 막는지를 정리한다.

## 왜 유선 L2 가 약한가 — 프로토콜이 인증을 하지 않는다

이더넷 LAN 의 기본 프로토콜들은 **같은 브로드캐스트 도메인 안의 모두를 믿는다**는 전제로 설계됐다.

- **ARP** — [RFC 826](https://www.rfc-editor.org/rfc/rfc826) 의 수신 알고리즘에는 송신자를 검증하는 단계가 없다. 오히려 같은 IP 에 대한 항목이 이미 있으면 *"the new hardware address supersedes the old one"*, 즉 새로 들어온 MAC 주소로 덮어쓴다.
  - 그래서 공격자가 게이트웨이 IP 를 자기 MAC 이라고 주장하는 ARP 를 뿌리면 트래픽이 공격자를 거쳐 간다(ARP 스푸핑, 중간자 공격).
- **DHCP** — 클라이언트는 응답한 서버를 가리지 않는다. 가짜 DHCP 서버가 먼저 응답하면 게이트웨이와 DNS 를 공격자 주소로 내려줄 수 있다.
- **STP** — 스위치는 받은 BPDU 로 토폴로지를 계산한다. 포트에 꽂은 장비가 더 우선순위 높은 BPDU 를 보내면 루트 브리지 선출이 흔들린다.

공통점은 하나다. **포트에 연결됐다는 사실만으로 발언권이 생긴다.** 그래서 유선 보안은 "누가 포트에 연결될 수 있나" 와 "연결된 뒤에 무엇을 주장할 수 있나" 두 층으로 나뉜다.

## 1층 — 포트에 누가 붙을 수 있나

### 802.1X: 포트 단위 인증

[IEEE 802.1X-2020](https://standards.ieee.org/ieee/802.1X/7345/) 의 이름 자체가 *Port-Based Network Access Control* 이다.

- 스위치 포트는 인증이 끝나기 전까지 EAP 인증 트래픽만 통과시킨다.
- 인증 판단은 RADIUS 서버가 한다. 802.1X 와 RADIUS 를 어떻게 엮는지는 [RFC 3580](https://www.rfc-editor.org/rfc/rfc3580) 에 가이드가 있다.
- 인증 결과에 따라 VLAN 을 동적으로 배정할 수도 있다. 같은 벽면 포트라도 직원 PC 는 업무 VLAN, 모르는 장비는 격리 VLAN 에 넣는 식이다.

무선에서 쓰는 EAP-TLS 같은 인증서 기반 방식을 유선에도 그대로 쓸 수 있다. 가장 강한 선택지다.

### MAB 는 802.1X 의 대체재가 아니다

프린터, IP 카메라, IoT 기기처럼 802.1X 를 못 하는 장비에는 흔히 **MAC Authentication Bypass(MAB)** 를 쓴다. MAC 주소를 신원 삼아 RADIUS 에 묻는 방식이다.

Cisco 의 [MAB 배포 가이드](https://www.cisco.com/c/en/us/td/docs/solutions/Enterprise/Security/TrustSec_1-99/MAB/MAB_Dep_Guide.html)는 한계를 직접 적어 두었다. *"Unlike IEEE 802.1X, MAB is not a strong authentication method. MAB can be defeated by spoofing the MAC address of a valid device."*

MAC 주소 기반 포트 보안도 마찬가지다. 그래서 MAB 로 받은 장비는 **그 장비가 필요한 목적지만 갈 수 있는 VLAN·ACL 에 가둬야** 한다. 프린터 MAC 을 흉내 낸 노트북이 전사망을 돌아다닐 수 없게 하는 것이다.

### 안 쓰는 포트는 끈다

가장 싸고 효과 큰 조치다.

- 연결되지 않은 벽면 포트와 스위치 포트는 비활성화(shutdown)하거나, 아무 데도 못 가는 격리 VLAN 에 둔다.
- 회의실·로비처럼 외부인이 접근하는 공간의 포트가 우선이다.

## 2층 — 연결된 뒤에 무엇을 주장할 수 있나

포트에 정당하게 붙은 장비도 감염되거나 오설정될 수 있다. 여기서부터는 스위치가 **프로토콜 메시지를 검사**하는 기능들이다. 아래 설명은 Cisco Catalyst 9300 보안 설정 가이드를 기준으로 한다. 다른 벤더에도 이름만 다른 같은 기능이 있다.

### DHCP 스누핑 — 가짜 DHCP 서버 차단

- 포트를 신뢰(trusted)·비신뢰(untrusted)로 나눈다.
- DHCP 서버 응답은 **신뢰 포트(업링크, 실제 DHCP 서버 쪽)에서만** 허용하고, 사용자 포트에서 오는 서버 응답은 버린다.
- 부산물로 "어느 포트에 어떤 MAC 이 어떤 IP 를 받았는가" 라는 **바인딩 테이블**이 생긴다. 아래 두 기능이 이 테이블을 쓴다.

### Dynamic ARP Inspection(DAI) — ARP 스푸핑 차단

Cisco 문서는 DAI 가 *"intercepts, logs, and discards ARP packets with invalid IP-to-MAC address bindings"* 라고 설명한다. 판단 기준은 DHCP 스누핑 바인딩 데이터베이스다([Configuring Dynamic ARP Inspection](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/sec/b_179_sec_9300_cg/configuring_dynamic_arp_inspection.html)).

"게이트웨이 IP 는 내 MAC" 이라는 거짓 ARP 는 바인딩 테이블과 맞지 않으므로 스위치에서 버려진다. RFC 826 에 없던 검증을 스위치가 대신 해 주는 셈이다.

- 고정 IP 장비(서버, 프린터)는 바인딩 테이블에 없으므로 ARP ACL 로 따로 등록해야 한다. 이걸 빠뜨리면 DAI 를 켜는 순간 그 장비들이 끊긴다.

### IP Source Guard — IP 위조 차단

같은 가이드의 [IP Source Guard 장](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/sec/b_179_sec_9300_cg/configuring_ip_source_guard.html)에 따르면, 이 기능을 켠 포트는 DHCP 스누핑이 허용한 DHCP 패킷 말고는 모든 IP 트래픽을 막는다. 그 뒤로는 바인딩된 출발지 IP 만 통과시킨다. 남의 IP 를 달고 패킷을 보내는 것을 포트에서 막는다.

### BPDU Guard — 사용자 포트에서 STP 참여 금지

Cisco 문서의 설명은 이렇다. *"When BPDU Guard is enabled and the port receives a BPDU, the switch immediately shuts the port down by placing it in the errdisable state."* ([PortFast and BPDU Guard](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/10586-65.html))

사용자 포트에는 PC 가 붙어야지 스위치가 붙을 이유가 없다. 그러니 BPDU 가 들어오면 포트를 닫는다. 공격뿐 아니라 **누가 책상 밑에 공유기나 허브를 꽂아 루프를 만드는 사고**도 같이 막는다. 실무에서는 오히려 이쪽이 더 흔하다.

## VLAN 은 경계지만, 설정이 경계를 만든다

VLAN(IEEE 802.1Q 태깅)으로 망을 나누는 것은 기본이다. 다만 **트렁크 설정이 느슨하면 VLAN 경계를 넘을 수 있다(VLAN hopping).**

- **스위치 스푸핑:** 사용자 포트가 트렁크 자동 협상을 받아들이면, 공격자 장비가 자기를 스위치처럼 소개해 트렁크를 맺는다. 그러면 여러 VLAN 의 트래픽에 접근할 수 있다.
- **이중 태깅:** 트렁크의 네이티브(untagged) VLAN 과 공격자의 access VLAN 이 같으면, 태그를 두 겹 붙인 프레임이 다른 VLAN 으로 넘어갈 수 있다.

대응 원칙은 단순하다.

- 사용자 포트는 **access 모드로 고정**하고 트렁크 자동 협상을 끈다.
- 트렁크의 네이티브 VLAN 은 **아무 호스트도 쓰지 않는 VLAN** 으로 바꾼다.
- 트렁크에는 필요한 VLAN 만 허용한다.

구체적인 명령어는 벤더마다 다르니 사용하는 장비의 하드닝 가이드를 따른다.

## 전송 구간 자체를 암호화: MACsec

위의 기능들은 모두 "스위치가 검사한다" 이다. 케이블 자체를 도청하거나, 스위치 사이 구간에 탭을 거는 공격은 막지 못한다.

[IEEE 802.1AE(MACsec)](https://standards.ieee.org/ieee/802.1AE/7154/)는 *"connectionless user data confidentiality, frame data integrity, and data origin authenticity"* 를 L2 에서 제공한다. 링크 단위로 이더넷 프레임을 암호화하고 무결성을 검증한다는 뜻이다. 키 교환은 802.1X 의 MKA 로 한다.

- 스위치와 스위치 사이, 건물과 건물 사이처럼 **물리적으로 통제하기 어려운 구간**에 쓰는 것이 일반적이다.
- 하드웨어 지원이 필요하므로 장비 사양부터 확인해야 한다.

## 관리 평면을 잊지 말 것

데이터 평면을 아무리 막아도 **스위치 자체를 장악당하면** 모든 설정이 무의미하다.

- 관리 접속은 SSH 만 허용하고 Telnet·HTTP 는 끈다.
- SNMP 는 인증과 암호화가 있는 v3 를 쓴다.
- 관리 인터페이스는 **별도 관리 VLAN 이나 대역 외(out-of-band) 망**에 둔다. 사용자 VLAN 에서는 스위치 관리 IP 에 닿지 않게 ACL 을 건다.
- 기본 계정·비밀번호를 바꾸고, 설정 변경은 로그로 남긴다.
- 펌웨어를 패치한다. 네트워크 장비는 "한 번 설치하면 잊는" 대표 장비다.

## 우선순위 — 무엇부터 할까

모든 기능을 한 번에 켤 필요는 없다. 비용 대비 효과 순으로 정리하면 대략 이렇다.

| 순서 | 조치 | 비용 | 막는 것 |
|---|---|---|---|
| 1 | 안 쓰는 포트 비활성화, 사용자 포트 access 고정 | 거의 0 | 무단 연결, VLAN hopping |
| 2 | BPDU Guard | 거의 0 | 루프 사고, STP 조작 |
| 3 | 관리 평면 분리(SSH·SNMPv3·관리 VLAN) | 낮음 | 장비 장악 |
| 4 | DHCP 스누핑 → DAI → IP Source Guard | 중간(고정 IP 예외 관리) | 가짜 DHCP, ARP 스푸핑, IP 위조 |
| 5 | 802.1X(+MAB 격리) | 높음(RADIUS·인증서 운영) | 무단 장비 접속 |
| 6 | MACsec | 높음(하드웨어) | 구간 도청·변조 |

4번은 **순서가 중요하다.** DAI 와 IP Source Guard 는 DHCP 스누핑의 바인딩 테이블에 의존한다. 스누핑을 먼저 켜고 테이블이 채워지는 것을 확인한 뒤에 나머지를 켜야, 멀쩡한 장비를 끊는 사고를 피할 수 있다.

## 정리

유선 네트워크 보안의 핵심은 **"물리적으로 연결됐다 = 신뢰한다" 는 등식을 깨는 것**이다.

- 1층에서는 연결될 수 있는 대상을 인증으로 제한하고(802.1X, 격리된 MAB), 안 쓰는 포트는 닫는다.
- 2층에서는 연결된 장비가 거짓을 주장하지 못하게 스위치가 검사한다(DHCP 스누핑, DAI, IP Source Guard, BPDU Guard).
- 그 위에 VLAN 경계를 설정으로 지키고, 필요한 구간은 암호화하고(MACsec), 스위치 자체를 보호한다.

제로 트러스트가 거창한 제품 이름처럼 들리지만, 유선망에서는 결국 **스위치 포트 하나하나에 "너는 누구고, 그 말이 사실인가" 를 묻는 일**이다.

## References

- IEEE 802.1X-2020 — [Port-Based Network Access Control](https://standards.ieee.org/ieee/802.1X/7345/)
- IEEE 802.1AE-2018 — [MAC Security (MACsec)](https://standards.ieee.org/ieee/802.1AE/7154/)
- [RFC 826 — An Ethernet Address Resolution Protocol](https://www.rfc-editor.org/rfc/rfc826)
- [RFC 3580 — IEEE 802.1X RADIUS Usage Guidelines](https://www.rfc-editor.org/rfc/rfc3580)
- Cisco — [Catalyst 9300 Security Configuration Guide: Dynamic ARP Inspection](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/sec/b_179_sec_9300_cg/configuring_dynamic_arp_inspection.html) · [IP Source Guard](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/sec/b_179_sec_9300_cg/configuring_ip_source_guard.html)
- Cisco — [Understand Spanning Tree PortFast and BPDU Guard Features](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/10586-65.html)
- Cisco — [MAC Authentication Bypass Deployment Guide](https://www.cisco.com/c/en/us/td/docs/solutions/Enterprise/Security/TrustSec_1-99/MAB/MAB_Dep_Guide.html)
- NIST SP 800-215 — [Guide to a Secure Enterprise Network Landscape](https://csrc.nist.gov/pubs/sp/800/215/final) (2022)
