---
layout: post
title: "무선 네트워크 보안 — WPA2 에서 WPA3 까지, 실제로 뚫린 방식으로 배우기"
date: 2026-09-24 20:10:00 +0900
categories: [security, network]
tags: [wifi, wireless, wpa2, wpa3, sae, krack, fragattacks, dragonblood, wps, pmf, owe, 802.11]
---

유선 네트워크를 공격하려면 적어도 케이블에 손이 닿아야 한다. **무선은 전파가 닿는 곳이면
어디서든 공격할 수 있다.** 벽 너머에서도, 주차장에서도, 옆 건물에서도 된다. 그래서 무선 보안은
"비밀번호를 걸었다" 에서 끝나지 않는다. 암호화 방식, 핸드셰이크, 관리 프레임, 편의 기능까지
전부 공격 대상이 된다.

이 글은 지난 10 년 가까이 **실제로 발표된 Wi-Fi 공격 네 가지**(KRACK, FragAttacks, Dragonblood, WPS PIN)
를 따라가며, 각각이 무엇을 노렸고 **결국 무엇을 설정해야 하는지**를 정리한다.
기업용 인증(802.1X / EAP / RADIUS)은
[이전 글](/2026/08/25/wireless-auth-802-1x-eap-radius-and-the-java-stack/)에서 다뤘으니,
여기서는 가정·소규모 사무실에서 쓰는 **Personal(공유 비밀번호) 모드**가 중심이다.

---

## TL;DR

| 할 일 | 이유 |
|---|---|
| **WPA3-Personal(SAE)** 을 쓴다. 안 되면 최소 WPA2-AES(CCMP) | WEP·TKIP 는 이미 깨진 방식 |
| **WPS 를 끈다** | PIN 구조 결함으로 약 11,000 번이면 전수 대입 가능 (CERT VU#723755) |
| **PMF(802.11w)** 를 켠다 | 관리 프레임 위조(강제 연결 끊기 등) 방어. WPA3 는 필수 |
| **공유기·단말 펌웨어를 업데이트한다** | KRACK·FragAttacks 는 비밀번호가 아니라 **패치**로 막는다 |
| **길고 무작위인 비밀번호**를 쓴다 | 오프라인 사전 대입과 WPA3 전환 모드 다운그레이드 대비 |
| 손님·IoT 는 **별도 네트워크**로 분리 | 무선이 뚫려도 내부망까지 가지 않게 |
| 무선 위에서도 **HTTPS·VPN** 을 쓴다 | 무선 암호화는 공유기까지만 보호한다 |

---

## 1. 먼저 용어 — WEP, WPA, WPA2, WPA3

Wi-Fi 보안 규격은 IEEE 802.11 표준([IEEE 802.11](https://standards.ieee.org/ieee/802.11/7028/))
과 Wi-Fi Alliance 인증 프로그램(WPA2, WPA3 같은 이름)이 함께 정한다.

| 방식 | 상태 |
|---|---|
| WEP | 사용 금지. 1997 년 원래 규격의 암호화 |
| WPA (TKIP) | 사용 금지. WEP 를 급히 대체하려고 만든 과도기 방식 |
| WPA2 (CCMP/AES) | 여전히 가장 흔하다. 4-way 핸드셰이크로 세션 키를 만든다 |
| WPA3 (SAE) | 현재 권장. 공유 비밀번호로 핸드셰이크를 하는 방식 자체를 SAE 로 바꿨다 |

WPA2 전반의 설계와 보안 기능은 NIST 의
[SP 800-97 (802.11i 가이드)](https://csrc.nist.gov/pubs/sp/800/97/final) 에,
조직의 무선망 운영 지침은 [SP 800-153 *Guidelines for Securing WLANs*](https://csrc.nist.gov/pubs/sp/800/153/final)
에 정리돼 있다.

---

## 2. KRACK (2017) — 비밀번호가 아니라 핸드셰이크를 노렸다

Mathy Vanhoef 와 Frank Piessens 가 ACM CCS 2017 에서 발표한
[KRACK (Key Reinstallation Attacks)](https://www.krackattacks.com/)은 WPA2 의 **4-way 핸드셰이크**를 공격한다
([논문 PDF](https://papers.mathyvanhoef.com/ccs2017.pdf)).

- 4-way 핸드셰이크는 클라이언트가 보호된 네트워크에 붙을 때, 양쪽이 올바른 자격 증명(예: 공유 비밀번호)을
  가졌는지 확인하고 세션 키를 정하는 절차다.
- 공격자는 핸드셰이크 메시지를 재전송하게 만들어 **이미 쓰던 키를 다시 설치**하게 한다. 그러면 암호화에
  쓰이는 nonce 가 초기화되고, 암호화된 트래픽을 복호화하거나(설정에 따라) 조작할 수 있다.
- 공식 사이트 표현으로 이 공격은 *"모든 현대적인 보호된 Wi-Fi 네트워크"* 에 통했다.

여기서 제일 중요한 교훈은 KRACK 사이트의 Q&A 에 그대로 나온다.

> **Wi-Fi 비밀번호를 바꿔도 이 공격은 막히지 않는다.** 모든 기기를 업데이트하고 공유기 펌웨어를 업데이트해야 한다.
> 모든 공격을 막으려면 **클라이언트와 AP 양쪽 모두** 패치해야 한다.

**비밀번호는 알아낼 필요가 없었다.** 프로토콜 구현의 상태 기계를 공격했기 때문에, 방어도 비밀번호가
아니라 소프트웨어 업데이트가 된다.

---

## 3. FragAttacks (2021) — 1997 년부터 있던 설계 결함

같은 연구자가 USENIX Security 2021 에서 발표한
[FragAttacks](https://www.fragattacks.com/)
([발표 페이지](https://www.usenix.org/conference/usenixsecurity21/presentation/vanhoef))는
프레임 **단편화(fragmentation)와 집계(aggregation)** 처리를 노린다.

사이트에 적힌 요지는 이렇다.

- 발견된 취약점 중 **세 개는 Wi-Fi 표준 자체의 설계 결함**이어서 대부분의 기기에 영향을 준다.
- 이 결함은 WPA3 를 포함한 모든 현대 보안 프로토콜에 해당하고, WEP 에도 있다. 즉
  **1997 년 Wi-Fi 가 처음 나왔을 때부터** 규격 안에 있었다.
- 다만 설계 결함 자체는 사용자 상호작용이 필요하거나 흔하지 않은 설정에서만 가능해 악용이 어렵다.
  실제로 더 큰 문제는 Wi-Fi 제품들에 **널리 퍼진 구현 버그**였고, 실험한 모든 Wi-Fi 제품이 최소 하나 이상의 취약점에 해당했다.

그리고 패치가 아직 없는 기기에 대한 조언으로 **방문하는 사이트가 HTTPS 를 쓰는지 확인하라**는 내용이 나온다.
무선 암호화만 믿지 말고 그 위에 한 겹을 더 두라는 뜻이다.

---

## 4. Dragonblood (2019) — WPA3 도 첫 버전은 흔들렸다

WPA3-Personal 은 WPA2 의 PSK 핸드셰이크 대신 **SAE(Simultaneous Authentication of Equals)**,
일명 Dragonfly 핸드셰이크를 쓴다. 연구자들의 표현으로는 *"WPA3 의 장점으로 여겨진 것 중 하나는
Dragonfly 덕분에 네트워크 비밀번호를 크랙하는 것이 거의 불가능하다는 점"* 이었다.

[Dragonblood](https://wpa3.mathyvanhoef.com/) 는 그 WPA3 의 초기 구현과 설계에서 두 종류의 문제를 찾았다.

1. **다운그레이드 공격** — WPA2 만 지원하는 구형 기기를 위해 WPA3 규격에는 *전환 모드(transition mode)*
   가 있다. 같은 비밀번호로 WPA3 와 WPA2 를 동시에 받는 모드다. 공격자가 WPA2 전용 가짜 AP 를 띄우면
   WPA3 를 지원하는 클라이언트도 그쪽에 붙게 만들 수 있고, 그렇게 얻은 핸드셰이크로 **사전 대입 공격**을 할 수 있다
   (CERT VU#871675).
2. **사이드 채널** — Dragonfly 핸드셰이크 구현에서 타이밍·캐시 접근 패턴이 새어 나와 비밀번호를 추정할 수
   있었다(CVE-2019-9494). 후속 연구에서는 Wi-Fi Alliance 의 권고(Brainpool 곡선)를 따라도 새로운 누출이
   생길 수 있음을 보였다.

실무적으로 얻는 결론은 두 가지다.

- **전환 모드는 과도기용이다.** 모든 기기가 WPA3 를 지원하면 WPA3 전용으로 바꾼다.
  구형 기기가 남아 있으면 그 기기들만 별도 네트워크로 분리하는 게 낫다.
- 전환 모드를 써야 하는 동안에는 **비밀번호가 사전에 없는, 길고 무작위인 문자열**이어야 한다.
  다운그레이드 공격은 결국 사전 대입으로 끝나기 때문이다.

---

## 5. WPS — 편의 기능이 가장 큰 구멍

WPS(Wi-Fi Protected Setup)는 버튼이나 8 자리 PIN 으로 기기를 쉽게 연결하려고 만든 기능이다.
[CERT 취약점 노트 VU#723755](https://www.kb.cert.org/vuls/id/723755) 의 설명은 이렇다.

- PIN 인증이 실패하면 AP 가 EAP-NACK 을 보내는데, 그 방식 때문에 공격자가
  **PIN 의 앞 절반이 맞았는지를 따로 알 수 있다.**
- PIN 의 마지막 자리는 체크섬이라 이미 정해져 있다.
- 그래서 시도 횟수가 10^8 에서 **10^4 + 10^3 = 11,000 번**으로 줄어든다.
- 많은 공유기가 실패 횟수 제한(lock out)을 구현하지 않았다.

**WPA2 든 WPA3 든 비밀번호가 아무리 강해도 WPS PIN 이 켜져 있으면 의미가 없다.** CERT 가 권고한 대응도
"알려진 실질적 해결책이 없으니 **WPS 를 끄라**" 였다. 제조사에 따라 메뉴 이름이 *external registrar*,
*router PIN*, *WiFi Protected Setup* 등으로 다르다. 끈 뒤에는 설정 화면만 믿지 말고
**다른 기기에서 스캔해 WPS 광고가 사라졌는지** 확인한다.

```bash
# 리눅스 클라이언트에서 주변 AP 의 보안 방식과 WPS 광고 확인 (인터페이스 이름은 환경에 맞게)
nmcli -f SSID,SECURITY dev wifi list
sudo iw dev wlan0 scan | grep -E 'SSID|WPS|RSN|Authentication suites'
```

---

## 6. PMF — 관리 프레임도 보호해야 한다

데이터 프레임은 암호화돼도, 연결·연결 해제 같은 **관리 프레임**은 오랫동안 보호받지 못했다.
그래서 공격자가 위조한 deauthentication 프레임 하나로 클라이언트를 끊고, 재연결할 때 핸드셰이크를
캡처하는 수법이 흔했다.

[Wi-Fi Alliance 설명](https://www.wi-fi.org/discover-wi-fi/security)에 따르면
**PMF(Protected Management Frames)** 는 유니캐스트 관리 프레임을 도청·위조로부터,
멀티캐스트 관리 프레임을 위조로부터 보호한다. **WPA3 네트워크는 PMF 사용이 필수**이고,
새로 인증받는 모든 기기에 PMF 가 요구된다.

WPA2 를 쓰는 동안에도 공유기에 PMF(802.11w) 옵션이 있으면 **"선택(optional)" 이상**으로 켠다.
"필수(required)" 로 두면 PMF 를 지원하지 않는 구형 기기는 붙지 못한다.

---

## 7. 공개 Wi-Fi — Enhanced Open(OWE)

카페나 공항의 비밀번호 없는 Wi-Fi 는 전통적으로 **암호화가 전혀 없다.** 같은 공간의 누구나 트래픽을 볼 수 있다.

**Wi-Fi Enhanced Open** 은 비밀번호 없이 쓰는 편의는 그대로 두면서 **인증 없는 데이터 암호화**를 제공한다
([Wi-Fi Alliance](https://www.wi-fi.org/discover-wi-fi/security)). 기반 메커니즘은 IETF
[RFC 8110 *Opportunistic Wireless Encryption*](https://www.rfc-editor.org/rfc/rfc8110) 으로, 802.11 에
*기회적(인증 없는) 암호화*를 더하는 확장이다.

여기서 **"인증 없는"** 이 핵심이다. 도청은 막지만, **내가 붙은 AP 가 진짜 그 카페의 AP 인지는 보장하지 않는다.**
가짜 AP 를 이용한 중간자 공격([MITRE ATT&CK T1557](https://attack.mitre.org/techniques/T1557/))까지 막아 주지는 못한다.
공개 망에서는 여전히 HTTPS 와 VPN 이 기본이다.

---

## 8. 설계 — 뚫렸을 때를 가정한다

위의 네 가지 공격이 공통으로 보여 주는 건, **무선 계층은 언젠가 또 뚫린다**는 사실이다. 규격 자체의 결함이
20 년 넘게 숨어 있기도 했다. 그래서 무선 보안의 마지막 단계는 무선 설정이 아니라 네트워크 설계다.

- **분리** — 손님용, IoT 용, 업무용 네트워크를 나눈다(별도 SSID + VLAN 또는 게스트 격리). 스마트 플러그 하나가
  뚫려도 서버까지 닿지 않게 한다.
- **무선을 신뢰 경계로 쓰지 않는다** — "사내 Wi-Fi 에 붙었으니 믿는다" 는 가정을 버린다. NIST 의
  [SP 800-207 Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final) 가 말하는 것처럼,
  네트워크 위치만으로 신뢰를 주지 않는다.
- **종단 간 암호화** — 무선 암호화는 공유기까지만 보호한다. 그 너머는 TLS 가 지킨다.
- **조직이라면 Enterprise 모드** — 공유 비밀번호 대신 사용자별 자격 증명(802.1X)을 쓰면, 퇴사자가 생겨도
  모든 기기의 비밀번호를 바꿀 필요가 없다.

---

## 마무리

네 가지 사례를 한 줄씩 정리하면 이렇다.

- **KRACK** — 비밀번호를 바꿔도 소용없다. **패치**가 답이다.
- **FragAttacks** — 규격 자체도 틀릴 수 있다. **무선 위에 한 겹 더**(HTTPS, VPN) 둔다.
- **Dragonblood** — 새 규격도 **전환 모드**에서 약해진다. 과도기를 길게 끌지 않는다.
- **WPS** — 편의 기능 하나가 강한 비밀번호를 무력화한다. **끈다.**

무선 보안은 비밀번호 하나로 끝나지 않는다. 방식(WPA3), 부가 기능(WPS 끄기, PMF 켜기), 업데이트,
네트워크 분리, 그리고 그 위의 암호화까지 **겹겹이 쌓는 것**이다.

---

## References

- IEEE, [IEEE 802.11 Standard](https://standards.ieee.org/ieee/802.11/7028/)
- Wi-Fi Alliance, [Wi-Fi Security (WPA3, Enhanced Open, PMF)](https://www.wi-fi.org/discover-wi-fi/security)
- NIST, [SP 800-97: Establishing Wireless Robust Security Networks: A Guide to IEEE 802.11i](https://csrc.nist.gov/pubs/sp/800/97/final)
- NIST, [SP 800-153: Guidelines for Securing Wireless Local Area Networks](https://csrc.nist.gov/pubs/sp/800/153/final)
- NIST, [SP 800-207: Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final)
- M. Vanhoef, F. Piessens, "Key Reinstallation Attacks: Forcing Nonce Reuse in WPA2", ACM CCS 2017 — [논문](https://papers.mathyvanhoef.com/ccs2017.pdf) · [krackattacks.com](https://www.krackattacks.com/)
- M. Vanhoef, "Fragment and Forge: Breaking Wi-Fi Through Frame Aggregation and Fragmentation", USENIX Security 2021 — [발표 페이지](https://www.usenix.org/conference/usenixsecurity21/presentation/vanhoef) · [fragattacks.com](https://www.fragattacks.com/)
- M. Vanhoef, E. Ronen, "Dragonblood: Analyzing the Dragonfly Handshake of WPA3 and EAP-pwd", IEEE S&P 2020 — [wpa3.mathyvanhoef.com](https://wpa3.mathyvanhoef.com/)
- CERT/CC, [VU#723755: WiFi Protected Setup (WPS) PIN brute force vulnerability](https://www.kb.cert.org/vuls/id/723755)
- IETF, [RFC 8110: Opportunistic Wireless Encryption](https://www.rfc-editor.org/rfc/rfc8110)
- MITRE ATT&CK, [T1557 Adversary-in-the-Middle](https://attack.mitre.org/techniques/T1557/)
