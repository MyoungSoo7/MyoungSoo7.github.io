---
layout: post
title: "NAC 의 기능과 한계 — 문지기는 들어온 사람이 무엇을 하는지 보는가?"
date: 2026-09-24 20:25:54 +0900
categories: [Security, Network]
tags: [NAC, Genian NAC, 802.1X, MAB, ARP Enforcement, Zero Trust, ZTNA, Endpoint Security]
---

NAC(Network Access Control)는 사내망 보안에서 가장 오래된 질문에 답하는 장비다. **"지금 망에 꽂힌 이 기기는 누구이고, 들어와도 되는가?"** 이 글은 국내에서 쓰이는 제품 중 하나인 Genian 의 공개 관리자 문서를 기준으로 NAC 가 **무엇을 하는지** 와 **어디서 멈추는지** 를 정리한다.

결론을 먼저 말하면, NAC 는 **입장 통제와 가시성**에는 탁월하고, **입장 이후의 행위**와 **사내망 바깥**에는 구조적으로 약하다.

| 단계 | NAC 가 하는 일 | 한계 |
|---|---|---|
| 식별 | 망 위의 모든 기기를 찾고 종류를 분류 | 분류는 추정이다 — 오탐이 정책 오류로 이어진다 |
| 인증 | 802.1X · MAB · 사용자 인증 | MAB 는 MAC 주소만 본다 |
| 상태 검사 | 에이전트로 OS · 백신 · 필수 SW 점검 | 에이전트 없는 기기, 자기 신고의 신뢰 문제 |
| 차단 | 802.1X · ARP · SPAN 기반 통제 | 방식마다 강제력과 커버 범위가 다르다 |
| 이후 | 준수 여부 지속 감시 | 인가된 기기의 내부 이동, 망 밖 접속 |

## 1. 무엇을 하는가

### 1.1 Pre-Connect 와 Post-Connect

Genian 문서는 NAC 기능을 두 시점으로 나눈다.[^g-intro]

- **Pre-Connect** — 기기가 정상 통신을 시작하기 전에 사용자명·비밀번호·인증서·MAC 주소 같은 정보로 식별·인증한다. 인가되지 않으면 연결을 거부한다.
- **Post-Connect** — 접속 뒤에도 에이전트가 하드웨어·소프트웨어 상태를 계속 감시하고, 정책 위반이 생기면 권한을 줄이거나 격리한다.

즉 현대 NAC 는 "문 앞에서 한 번 검사" 가 아니라, 에이전트를 통해 **접속 중에도 상태를 추적**하도록 설계되어 있다.

### 1.2 식별 — Device Platform Intelligence

NAC 의 첫 가치는 **가시성**이다. Genian 은 네트워크 센서가 수집한 HTTP 헤더, User-Agent, TELNET·SSH·SMTP 배너 등 여러 프로토콜 정보로 기기의 제조사·제품명·모델을 식별하고, 단종(EOS/EOL) 여부와 관련 CVE 까지 보여준다고 설명한다.[^g-gdpi] "우리 망에 무엇이 꽂혀 있는지" 를 자동으로 아는 것만으로도 자산 관리의 절반이 해결된다.

### 1.3 인증 — 802.1X 와 MAB

표준적인 인증은 IEEE 802.1X 다.[^ieee8021x] 스위치나 무선 AP 가 포트를 닫아 두고, RADIUS 서버가 인증한 기기에만 연다. Genian 은 RADIUS 서버를 내장하고 있다.[^g-enforce]

802.1X 를 지원하지 않는 프린터·IoT 기기를 위해 **MAB(MAC Authentication Bypass)** 도 제공한다. 문서의 설명은 단순하다: 인증을 요청한 MAC 주소가 지정한 노드 그룹에 있으면 허용하고, 없으면 거부한다.[^g-mab]

### 1.4 차단 — 세 가지 방식

Genian 문서가 밝히는 강제(enforcement) 방식은 세 가지다.[^g-enforce]

| 방식 | 원리 | 장점 | 전제 조건 |
|---|---|---|---|
| **ARP Enforcement** | 센서가 ARP 요청에 **자기 MAC 으로 응답**해 트래픽을 가로챈 뒤, 정책에 따라 버리거나 전달 | 스위치 교체·대규모 설정 변경 불필요 | 관리할 **모든 브로드캐스트 도메인**에 센서 연결 |
| **Port Mirroring (SPAN)** | 미러링 포트로 새 세션을 보고 TCP RST · ICMP Unreachable 로 끊음 | 네트워크 변경 최소 | 미러링 지원 스위치 또는 TAP |
| **802.1X (RADIUS)** | 스위치·AP 포트 자체를 열고 닫음 | 문서 스스로 "가장 이상적인 방식" 이라 표현 | 802.1X 지원 장비, 포트별 설정 |

ARP 방식이 국내 환경에서 매력적인 이유도 문서에 그대로 적혀 있다. 802.1X 는 *"can be expensive, requiring large network configuration changes, such as replacing unsupported devices and converting to a single vendor for networking equipment"* 라는 것이다.[^g-enforce] ARP 방식은 이 비용을 피하는 대신, 스위치가 아니라 **L2 프로토콜의 성질**에 기대어 통제한다.

정적 ARP 를 설정해 가로채기를 피하려는 시도에 대해서는, 게이트웨이 쪽 응답까지 통제하는 **양방향 강제**와 에이전트에 의한 정적 ARP 차단을 제공한다고 문서는 설명한다.[^g-enforce]

## 2. 어디서 멈추는가

### 2.1 MAC 주소는 신원이 아니다

MAB 는 MAC 주소를 "누구인가" 의 증거로 쓴다. 그런데 MAC 주소는 대부분의 OS 에서 **사용자가 바꿀 수 있는 값**이다. 허가된 프린터의 MAC 을 확인해 노트북에 설정하면, MAB 관점에서 그 노트북은 프린터다.

그래서 MAB 로 들어온 기기는 **최소 권한 VLAN · ACL** 로 묶는 게 원칙이다. 프린터로 인증된 기기가 프린터가 쓰는 포트 외에는 아무 데도 못 가게 해야 복제의 이득이 사라진다.

### 2.2 분류는 추정이다

기기 식별은 배너·헤더 같은 **간접 증거**로 추론한다. Genian 의 트러블슈팅 문서는 이 한계를 솔직하게 적어 둔다. 탐지된 플랫폼이 스캔이 쌓이거나 기기 행동이 바뀌면서 달라질 수 있고, 그러면 "차단 예외" 정책에서 빠져 **정상 기기가 차단**될 수 있다는 것이다. 문서는 해결책으로 자동 탐지값이 아닌 **관리자가 확인(Admin-Confirmed)한 값**으로 예외 조건을 걸라고 권한다.[^g-fp]

뒤집어 말하면, **자동 분류를 신뢰 근거로 쓰면 안 된다.** 공격자 입장에서도 배너와 User-Agent 는 흉내 낼 수 있는 값이다.

### 2.3 ARP 강제는 센서가 있는 곳에서만 작동한다

설치 문서는 센서가 ARP·DHCP 같은 브로드캐스트 패킷을 봐야 하므로 *"connected to all segments (broadcast domains) you plan to manage"* 되어야 한다고 명시한다.[^g-sensor] 센서가 빠진 VLAN 은 곧 **통제 사각지대**다. 망이 증설될 때마다 센서 연결도 함께 늘려야 한다.

또 ARP 강제는 원리상 **센서가 다른 기기를 사칭**하는 동작이다. 문서도 ARP Enforcement 가 IDS·EDR 의 보안 경보를 유발할 수 있다고 경고한다.[^g-arp] 보안 장비끼리 서로를 공격으로 오인하지 않도록 예외를 맞추는 운영 작업이 따라온다.

### 2.4 상태 검사는 에이전트의 보고를 믿는다

Post-Connect 감시는 에이전트가 보고한 상태에 기반한다. 이 구조의 한계는 두 가지다.

- **에이전트를 깔 수 없는 기기** — 프린터, IP 카메라, 생산 설비, 의료 기기는 상태 검사 자체가 불가능하다. 이들은 식별과 MAB 수준의 통제만 받는다. 망에서 가장 패치가 안 되는 기기들이 가장 느슨한 검사를 받는 역설이다.
- **이미 장악된 기기** — 커널 권한을 얻은 공격자는 에이전트의 판단 근거를 조작할 수 있다. "백신 최신, 패치 완료" 라는 보고는 **보고일 뿐 증명이 아니다.** 하드웨어 기반 증명(TPM attestation 등)과 결합되지 않는 한 자기 신고의 한계는 남는다.

### 2.5 입장 통제는 내부 이동을 막지 않는다

NAC 가 막는 것은 **허가되지 않은 기기**다. 허가된 기기가 감염되거나, 정상 사용자의 계정이 탈취되면 그 트래픽은 NAC 입장에서 정상이다.

NIST SP 800-207 은 경계 기반 보안의 한계를 이렇게 요약한다.[^nist207]

> *"Perimeter-based network security has also been shown to be insufficient since once attackers breach the perimeter, further lateral movement is unhindered."*

NAC 가 만든 경계는 "사내망 입구" 라는 경계다. 그 안에서의 이동은 내부망 분리(마이크로 세그멘테이션), EDR, 내부 트래픽 탐지가 맡아야 한다.

### 2.6 사내망 밖은 보지 못한다

재택·출장 중 VPN, 클라우드, SaaS 로의 접속은 사내 스위치를 거치지 않는다. 같은 문서는 제로 트러스트의 전제를 이렇게 적는다.[^nist207]

> *"Zero trust assumes there is no implicit trust granted to assets or user accounts based solely on their physical or network location (i.e., local area networks versus the internet)..."*

"사내망에 있으니 믿는다" 는 NAC 의 전통적 모델과 정면으로 부딪히는 문장이다. 업계가 **ZTNA** 로 옮겨가는 이유가 여기 있고, Genian 도 제품군과 문서 체계에서 NAC 를 ZTNA 로 확장하고 있다.[^g-intro]

### 2.7 운영이 실제 보안 수준을 정한다

NAC 도입의 가장 흔한 실패는 기술이 아니라 운영에서 온다.

- **예외 목록의 누적** — 차단하면 업무가 멈추는 기기(회의실 장비, 생산 설비, 임원 기기)가 하나씩 예외로 등록된다. 몇 년 뒤엔 예외 목록이 정책의 실체가 된다.
- **모니터링 모드 고착** — Genian 센서의 기본값은 수집만 하는 Monitoring 모드이고, 차단하려면 Enforcement 로 바꿔야 한다.[^g-arp] 오탐 차단을 한 번 겪은 조직은 이 스위치를 다시 켜기 어렵다.

## 3. 실무 체크리스트

1. **가능한 구간은 802.1X, 불가능한 구간만 ARP · MAB** 로 설계한다.
2. **MAB 기기는 전용 VLAN · 최소 권한**으로 묶어 MAC 복제의 이득을 없앤다.
3. **예외 조건은 자동 탐지값이 아닌 관리자 확인값**으로 건다.
4. **센서 커버리지를 자산으로 관리**한다 — 새 VLAN 이 생기면 센서 연결도 체크리스트에 넣는다.
5. **NAC 로그를 SIEM · EDR 과 연결**해 "누가 들어왔나" 와 "들어와서 무엇을 했나" 를 한 화면에서 본다.
6. **망 밖 접속은 ZTNA 로** — 사내 NAC 정책을 원격 접속에도 같은 기준으로 적용한다.

## 맺으며 — 문지기의 비용

NAC 는 좋은 문지기다. 누가 들어오는지 알고, 모르는 기기를 막고, 상태가 나쁜 기기를 격리한다. 사내망에 무엇이 붙어 있는지 모르는 조직에게 NAC 의 가시성은 그 자체로 큰 성과다.

하지만 문지기의 가치는 **문이 하나일 때** 가장 크다. 클라우드와 원격 근무로 문이 수십 개가 된 지금, 그리고 공격자가 문을 부수는 대신 **정상 출입증을 훔치는** 지금, NAC 는 전체 방어의 한 층일 뿐이다. 도입 비용보다 무서운 건 "NAC 가 있으니 내부는 안전하다" 는 가정이다. NIST 의 표현대로, 경계를 넘은 공격자의 내부 이동은 경계가 막아 주지 않는다.

---

## References

[^g-intro]: Genians, *Understanding Network Access Control* — Genian NAC 6.0 Administrator's Guide. <https://docs.genians.com/nac/6.0/release/en/intro.html>
[^g-gdpi]: Genians, *Genian Device Platform Intelligence (GDPI)*. <https://docs.genians.com/nac/6.0/release/en/monitoring/network-nodes/device-platform-intelligence.html>
[^ieee8021x]: IEEE, *IEEE 802.1X — Port-Based Network Access Control*. <https://standards.ieee.org/ieee/802.1X/7345/>
[^g-enforce]: Genians, *Policy Enforcement Methods*. <https://docs.genians.com/nac/6.0/release/en/controlling/enforcement-methods.html>
[^g-mab]: Genians, *Configuring MAC Authentication (MAB)*. <https://docs.genians.com/nac/6.0/release/en/controlling/radius/enable-mab.html>
[^g-fp]: Genians, *A problem in which the node is assigned the wrong policy due to platform false positives*. <https://docs.genians.com/nac/6.0/release/en/troubleshoot/false-positive-platform.html>
[^g-sensor]: Genians, *Installing Network Sensor*. <https://docs.genians.com/nac/6.0/release/en/install/installing-network-sensor.html>
[^g-arp]: Genians, *Configuring ARP Enforcement*. <https://docs.genians.com/nac/6.0/release/en/controlling/config-arp.html>
[^nist207]: NIST, *SP 800-207: Zero Trust Architecture* (2020). <https://csrc.nist.gov/pubs/sp/800/207/final>
