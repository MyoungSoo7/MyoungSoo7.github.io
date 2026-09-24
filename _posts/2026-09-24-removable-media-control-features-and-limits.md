---
layout: post
title: "매체제어(USB·외장하드·블루투스)는 무엇을 막고 무엇을 못 막나"
date: 2026-09-24 20:15:00 +0900
categories: [security]
tags: [device-control, dlp, usb, badusb, endpoint-security, usbguard]
---

보안 점검표에 거의 빠지지 않는 항목이 **매체제어**다. USB 메모리, 외장하드, SD카드, 스마트폰, 블루투스 같은
외부 장치의 사용을 제한하는 통제다. 도입은 쉽다. 정책 몇 줄이면 USB 가 안 먹힌다.
그래서 "매체제어 했으니 반출은 막혔다"는 착시가 생기기 쉽다.

이 글은 매체제어가 **실제로 해 주는 것**과 **구조적으로 못 하는 것**을, 벤더 공식 문서와 MITRE ATT&CK 기준으로 나눠 정리한다.

## 1. 매체제어가 해 주는 것

### 장치 종류별 차단·허용

[Microsoft Defender for Endpoint 의 Device control 문서](https://learn.microsoft.com/en-us/defender-endpoint/device-control-overview)는 대표 시나리오를 이렇게 든다.

- 특정 장치(USB 드라이브 등)의 설치·사용 금지
- 모든 외부 장치를 막고 **특정 예외만** 허용
- 특정 장치만 허용

윈도우 기본 기능만으로도 가능하다. [그룹 정책의 장치 설치 제한](https://learn.microsoft.com/en-us/windows/client-management/client-tools/manage-device-installation-with-group-policy)은
"승인 목록에 없는 장치는 설치할 수 없게" 하는 방식과 "금지 목록의 장치만 막는" 방식을 모두 지원한다.
장치는 하드웨어 ID, 장치 인스턴스 ID, 장치 클래스 같은 식별 문자열로 구분한다.

리눅스에는 [USBGuard](https://usbguard.github.io/)가 있다. 장치 속성을 기준으로 허용·차단 목록을 운영하는 프레임워크다.
[규칙 언어](https://usbguard.github.io/documentation/rule-language.html)로 제조사/제품 ID, 시리얼, 연결 포트, **장치가 제공하는 인터페이스 종류**까지 조건에 걸 수 있다.

### 읽기·쓰기 단위 권한

통째로 막는 대신 **읽기만 허용**하는 게 현실적인 절충인 경우가 많다. 자료를 가져오는 건 되고, 내보내는 건 안 된다.
Microsoft 문서도 이동식 저장소 파일에 대한 Read/Write/Execute 접근 제어를 사용 사례로 언급한다.

### 감사 로그

정책에 감사(audit) 항목을 두면, 이동식 저장소 정책이 발동될 때마다 이벤트가 남는다. 누가, 언제, 어떤 장치(시리얼 포함)를 꽂았는지 추적할 수 있다.
사고 후 조사에 필요하고, 차단 정책을 켜기 전에 **감사만 먼저 켜서 실제 사용 현황을 보는** 용도로도 쓴다.

---

## 2. 매체제어가 못 하는 것

### ① "USB 장치" 전부가 통제 대상은 아니다

이게 가장 오해가 많은 부분이다. Microsoft 문서는 이렇게 못박는다.

> 윈도우에서 이동식 미디어라는 말은 **모든 USB 장치를 뜻하지 않는다.**
> 이동식 미디어로 간주되어 Device control 의 범위에 들어가려면, 장치가 윈도우에 디스크(예: `E:`)를 만들어야 한다.

같은 문서에 따르면 Device control 이 제한할 수 있는 건 Windows Portable Devices, 이동식 미디어, CD/DVD, 프린터다.
그러면 **키보드로 인식되는 USB** 는 어떻게 될까. 저장장치 차단 정책의 대상이 아니다.

MITRE ATT&CK 은 이 공격을 [Hardware Additions (T1200)](https://attack.mitre.org/techniques/T1200/)으로 분류한다.
악의적인 주변기기로 할 수 있는 일로 **키 입력 주입(keystroke injection)**, DMA 를 통한 커널 메모리 읽기 등을 든다.
키보드인 척하는 장치는 꽂히는 순간 명령을 타이핑한다. 저장장치가 아니므로 "USB 저장장치 차단"을 그대로 통과한다.

USBGuard 가 자신을 "악성 USB 장치(BadUSB)로부터 보호"하는 도구로 소개하는 이유가 이것이다.
USBGuard 는 저장장치만이 아니라 **모든 USB 장치의 연결 자체**를 허용 목록으로 통제한다.
예를 들어 "새로 꽂힌 장치가 키보드 인터페이스를 갖고 있으면 막는다" 같은 규칙을 쓸 수 있다.

### ② 허용 목록의 식별값은 장치가 스스로 말하는 값이다

제조사 ID, 제품 ID, 시리얼은 장치가 연결될 때 **스스로 보고하는** 속성이다. 허용 목록이 "특정 모델"이면,
같은 값을 보고하도록 만든 장치가 같은 모델로 보일 수 있다. 식별값만으로는 "진짜 회사 지급 USB 인가"를 증명하지 못한다.
그래서 실무에서는 **암호화 인증을 거치는 보안 USB**나, 연결 포트·인터페이스 조합까지 묶은 규칙을 쓴다.

### ③ 매체만 막는다 — 다른 출구는 그대로다

MITRE ATT&CK 은 USB 반출([T1052.001](https://attack.mitre.org/techniques/T1052/001/))과 별도로
**정상 웹 서비스를 통한 반출**([T1567](https://attack.mitre.org/techniques/T1567/))을 따로 정의한다.
설명대로, 이미 조직이 평소에 통신하는 웹 서비스를 쓰면 트래픽이 자연스럽게 묻힌다. 방화벽 규칙도 이미 열려 있기 쉽다.

USB 를 막아도 개인 클라우드 업로드, 웹메일, 메신저 파일 전송, 인쇄, 화면 캡처, 모니터를 폰으로 찍기는 매체제어의 범위 밖이다.
매체제어는 **여러 출구 중 하나**를 닫는 통제다.

### ④ 통제 에이전트는 OS 위에서 돈다

- 로컬 관리자 권한이 있으면 에이전트나 정책을 끌 수 있는 여지가 생긴다. **관리자 권한 회수**가 전제 조건이다.
- 외부 매체로 **다른 OS 를 부팅**하면 설치된 에이전트는 아예 실행되지 않는다. BIOS/UEFI 부팅 순서 잠금과 관리자 암호,
  그리고 [BitLocker](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/) 같은
  **디스크 암호화**가 함께 있어야 "우회 부팅해 봐야 읽을 수 없는" 상태가 된다.
- 썬더볼트 같은 고속 포트는 DMA 공격 면이 있다. Microsoft 는 이를 [Kernel DMA Protection](https://learn.microsoft.com/en-us/windows/security/hardware-security/kernel-dma-protection-for-thunderbolt) 문서에서
  "소유자가 자리를 비운 몇 분 사이, 기성품 도구로, 분해 없이" 가능한 drive-by DMA 공격으로 설명한다. 이건 매체제어가 아니라 **하드웨어·펌웨어 보호**의 영역이다.

### ⑤ 서버는 사각지대가 되기 쉽다

Microsoft Defender for Endpoint 문서에는 **"현재 Device control 은 서버를 지원하지 않는다"**는 문장이 있다.
PC 중심 솔루션만 도입하면 서버, 개발자 맥, 리눅스 장비가 빠지기 쉽다. 리눅스는 USBGuard 같은 별도 수단으로 채워야 한다.

### ⑥ 블루투스는 켜고 끄는 것만으로 부족하다

블루투스로 파일 전송은 막고 싶지만, 무선 이어폰과 키보드는 써야 한다. 제품마다 제어 단위(장치 종류, 프로파일)가 다르다.
결국 통째로 끄거나 통째로 허용하는 경우가 많고, 둘 다 만족스럽지 않다. 도입 전에 제품이 **어느 단위까지** 제어하는지 확인해야 한다.

### ⑦ 허용된 사람의 합법적 반출은 못 막는다

승인받은 사람이 승인받은 USB 로 자료를 옮기는 건 매체제어 입장에서 정상 동작이다. 내부자 유출은 통제가 아니라
**로그 모니터링과 이상 행위 탐지**의 영역이다. 실무에서 흔한 구멍은 결재로 준 "임시 허용"이 회수되지 않고 쌓이는 것이다.
허용에는 반드시 만료일을 둔다.

---

## 3. 정리 — 매체제어는 울타리의 한 칸이다

| 목적 | 매체제어로 충분한가 | 함께 필요한 것 |
|---|---|---|
| USB 저장장치 반출 | 대부분 | 읽기전용 정책, 감사 로그 |
| 키보드 위장 USB (키 입력 주입) | ❌ 저장장치 정책으로는 아님 | 모든 USB 장치 허용 목록 (예: USBGuard) |
| 웹·클라우드·메신저 반출 | ❌ | 네트워크 DLP, 프록시 |
| 외부 부팅 우회 | ❌ | BIOS/UEFI 잠금, 디스크 암호화 |
| DMA 공격 | ❌ | Kernel DMA Protection 등 하드웨어 보호 |
| 서버·리눅스 | ❌ (지원 범위 밖인 경우) | USBGuard, udev 규칙 |
| 내부자 합법 반출 | ❌ | 로그 모니터링, 임시 허용 만료 |

도입 순서를 권한다면 이렇다.
**감사 모드로 현황 파악 → 저장장치 읽기전용 → 관리자 권한 회수 + 부팅 잠금 + 디스크 암호화 → 모든 USB 장치 허용 목록 → 네트워크 쪽 DLP.**

매체제어는 "손쉬운 반출"을 막는 기본 울타리다. 울타리가 있다는 사실이 문이 다 잠겼다는 뜻은 아니다.

## References

- Microsoft Learn, *Device control in Microsoft Defender for Endpoint* — <https://learn.microsoft.com/en-us/defender-endpoint/device-control-overview>
- Microsoft Learn, *Manage Device Installation with Group Policy* — <https://learn.microsoft.com/en-us/windows/client-management/client-tools/manage-device-installation-with-group-policy>
- Microsoft Learn, *Kernel DMA Protection* — <https://learn.microsoft.com/en-us/windows/security/hardware-security/kernel-dma-protection-for-thunderbolt>
- Microsoft Learn, *BitLocker overview* — <https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/>
- USBGuard 프로젝트 — <https://usbguard.github.io/>, 규칙 언어 — <https://usbguard.github.io/documentation/rule-language.html>
- MITRE ATT&CK, *Hardware Additions (T1200)* — <https://attack.mitre.org/techniques/T1200/>
- MITRE ATT&CK, *Exfiltration over USB (T1052.001)* — <https://attack.mitre.org/techniques/T1052/001/>
- MITRE ATT&CK, *Exfiltration Over Web Service (T1567)* — <https://attack.mitre.org/techniques/T1567/>
