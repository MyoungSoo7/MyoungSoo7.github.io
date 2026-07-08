---
layout: post
title: "Dell R730XD iDRAC 첫 셋업 — 전용 포트·DHCP·600초 잠금·F2 리셋·모뎀 직결의 함정 5종"
date: 2026-05-28 22:55:00 +0900
categories: [infra, homelab]
tags: [dell, r730xd, idrac, idrac8, bmc, homelab, k3s, networking, dhcp, ipmi]
---

홈랩 K3s 클러스터 6번째 노드로 *중고 Dell PowerEdge R730XD* 한 대를 들였다. 489,000원에 20코어 / 40스레드 / 16GB DDR4 / iDRAC 8 Enterprise / X540 quad-port NIC — 가성비는 미친 가격인데, *iDRAC 첫 셋업* 에서 다섯 군데서 막혔다. 매번 "이게 진짜 안 되는 건가?" 싶었지만, 결국 전부 *문서엔 잘 안 나오는 함정* 이었다.

이 글은 *그 다섯 함정의 정체 + 해결책* 을 한자리에 정리한다. R730xd 뿐 아니라 R7x0 / R6x0 / iDRAC8 / iDRAC9 세대 전반에 비슷하게 적용된다.

> 본 글의 IP / MAC 주소는 *문서화용 예시* (RFC 5737 TEST-NET-3 / 임의 host part) 입니다. 본인 환경에 맞춰 치환해서 읽어주세요.

---

## TL;DR

| # | 함정 | 증상 | 해결 |
|---|---|---|---|
| 1 | iDRAC 전용 포트에 케이블 안 꽂음 | NIC Selection 은 `Dedicated` 인데 `Active NIC Interface: None` | 시리얼 포트 옆 작은 RJ45 (라벨 `iDRAC` / 🔧 스패너 아이콘) 에 케이블 꽂기 |
| 2 | BIOS 화면이 *실시간 갱신 안 됨* | 케이블 꽂아도 `Active NIC Interface: None` 그대로 표시 | 무시하고 ESC → 재진입 또는 *그냥 노트북에서 ARP 로 확인* (실제 iDRAC 은 잘 동작) |
| 3 | 공장 기본 비번 `root/calvin` 그대로 사용 | 누구나 알 수 있는 비번 → *집 네트워크 안에서도* 위험 | 즉시 변경, 단 *오타 주의* (변경 시 의도와 다른 비번 저장되면 본인도 못 들어감) |
| 4 | 비번 5회 틀리면 *600초 잠금* | `RAC0212: Log in delayed for 600 seconds` | 10분 대기 + *F2 BIOS → iDRAC Settings → Reset Configurations to Defaults* 로 강제 초기화 |
| 5 | 관리 PC 가 *모뎀 직결* 이라 사설망 못 봄 | iDRAC `10.0.50.106` 접속 timeout, 본인 IP 는 `203.0.113.x` (공인 IP) | 데스크탑 LAN 케이블 → *공유기 LAN 포트* 로 이동 (모뎀 직결 X) |

---

## 0. iDRAC 이 *서버 본체와 별개로 동작하는 작은 컴퓨터* 라는 사실

대부분의 함정의 뿌리는 이 한 줄을 *직관적으로* 받아들이지 못한 데서 온다.

```
┌─────────────────────────────────────────────┐
│  Dell PowerEdge R730XD 본체                  │
│                                             │
│  ┌──────────────┐    ┌──────────────────┐  │
│  │ 메인 서버    │    │ iDRAC8 (BMC)    │  │
│  │ - CPU x 2    │    │ - 자체 CPU       │  │
│  │ - DDR4 16G   │    │ - 자체 RAM       │  │
│  │ - 디스크     │    │ - 자체 OS         │  │
│  │ - X540 NIC   │    │ - 자체 NIC ←──── │ ← 전용 RJ45 포트
│  │              │    │ - 자체 IP        │  │
│  └──────┬───────┘    └────────┬─────────┘  │
│         │                     │            │
│         └─── 같은 PSU 전원 ───┘            │
│              (PSU 만 살아있으면              │
│               본체 OFF 여도 iDRAC ON)        │
└─────────────────────────────────────────────┘
```

귀결:
- iDRAC 의 *MAC* 은 메인 NIC 의 MAC 과 다르다 (별개 칩)
- iDRAC 의 *IP* 도 메인 OS 의 IP 와 다르다 (별개 네트워크 스택)
- iDRAC 은 *5V standby 전력* 으로 동작 → PSU 가 콘센트에 꽂혀있기만 하면 *본체 전원 OFF 여도 살아있음*
- iDRAC 자체 펌웨어 업데이트 / 비번 / 네트워크 설정은 *서버 OS 와 무관* (BIOS / iDRAC GUI 에서만)

이걸 받아들이지 못하면 "왜 ipconfig 에 iDRAC IP 가 안 보이지?" 같은 질문이 나온다 — 메인 OS 입장에서 iDRAC 은 *다른 컴퓨터* 이기 때문에 자기 ipconfig 에 나올 리가 없다.

---

## 함정 1: NIC Selection 은 `Dedicated` 인데 케이블이 *X540* 에 꽂혀있음

### 증상

F2 → iDRAC Settings → Network 화면:

```
Enable NIC ............... ⦿ Enabled  ✅
NIC Selection ............ [Dedicated]  ✅
MAC Address .............. 10:98:36:00:11:22
Auto Negotiation ......... ⦿ On
Active NIC Interface ..... None       ← ⚠️ 빨간 줄
```

`NIC Selection: Dedicated` 는 "iDRAC 전용 포트로 통신함" 이라는 뜻인데, *그 전용 포트에 랜선이 안 꽂혀있다* 는 상태.

### 왜 헷갈리나

R730XD 뒷면에 RJ45 가 *4개 + 1개* 있다:
- **X540 PCIe 카드**: 4개 RJ45 (10Gb x 2 + 1Gb x 2) — *서버 OS 용 데이터 NIC*
- **메인보드 iDRAC 전용 포트**: 1개 작은 RJ45 — *iDRAC 전용*

처음 보면 *큰 4포트 카드가 모든 네트워크* 라고 착각하고 거기에 케이블을 꽂게 된다. iDRAC 전용 포트는 *시리얼 (DB9) 옆에 외롭게 하나만* 박혀있고, 라벨이 `iDRAC` 라고 작게 적혀있어서 못 보고 지나치기 쉽다.

### 해결

```
┌─────────────────── R730XD 뒷면 ──────────────────┐
│  PSU2  PSU1   │ Serial │ VGA │ USB │X540 4 ports │
│               │  IOIOI │  📺 │ ▭▭ │ 🟦🟦🟦🟦   │
│               │        │     │     │            │
│       ┌──────────────┐                          │
│       │ ⬛ iDRAC      │ ← 여기!                  │
│       │   (작은 RJ45) │                          │
│       └──────────────┘                          │
└─────────────────────────────────────────────────┘
```

이 *iDRAC 라벨이 있는 단독 RJ45* 에 케이블 꽂으면 끝. LED 가 초록색으로 켜진다.

대안: `NIC Selection` 을 `Shared LOM1` / `Shared LOM2` 로 바꾸면 메인보드 *rNDC* (rack Network Daughter Card) 의 1번/2번 포트와 *공유* 사용. 단 이 옵션은 rNDC 가 *설치돼있어야* 동작 — X540 PCIe 카드는 rNDC 가 아니다.

---

## 함정 2: BIOS 화면이 *실시간 갱신 안 됨* — Active NIC Interface 영원히 None

함정 1 을 해결하고 케이블을 iDRAC 포트에 꽂아도, BIOS 의 *그 화면* 은 여전히 `Active NIC Interface: None` 로 보인다. *진짜 안 되는 줄 알고* 케이블을 빼고 꽂고 반복하게 된다.

### 진실

`Active NIC Interface` 필드는 *BIOS 화면이 처음 그려진 순간의 값* 을 그대로 표시한다. 그 이후의 link state 변화는 *반영되지 않는다*. BIOS 는 그런 UI 가 아니라서.

### 확인 방법 (BIOS 밖에서)

이미 *맥/노트북에서* iDRAC 동작 여부를 확인할 수 있다 — iDRAC 의 MAC 은 BIOS 에 표시돼있으므로:

```bash
$ ping -c 5 10.0.50.0/24 의 가능한 IP 들  # 또는 router admin 페이지에서 DHCP 리스트
$ arp -a | grep -i "10:98:36"      # Dell OUI
? (10.0.50.106) at 10:98:36:00:11:22 on en0 ifscope [ethernet]  ← iDRAC IP 찾았다!

$ curl -sk https://10.0.50.106/
HTTP/1.1 302 Found
Location: /start.html               ← iDRAC 웹 살아있음 ✅
```

Dell iDRAC MAC OUI 모음 (검색에 쓸 prefix):

```
10:98:36   24:6e:96   d4:ae:52   18:fb:7b   18:66:da
b0:83:fe   f8:db:88   00:14:22   d0:67:e5   f8:b1:56
```

이걸로 잡히면 *BIOS 화면이 None 이라고 말하든 말든* 실제 iDRAC 은 잘 동작 중이다. ESC 로 BIOS 나가면 끝.

---

## 함정 3: 공장 기본 비번 `root/calvin` + 변경 시 *오타 주의*

iDRAC 의 *공장 기본 자격증명* 은 30년 가까이 변하지 않은:

```
Username: root
Password: calvin
```

문제 1: *이걸 *Dell 매뉴얼이 검색되는 모든 인터넷이 안다*. 집 공유기 안이라도 다른 디바이스 (스마트 TV, IoT 등) 가 침해당해 내부 스캔하면 *바로* iDRAC 들어옴 → 가상 콘솔 / 전원 제어 / 펌웨어 변조 가능.

문제 2: 비밀번호 변경할 때 *오타로 의도와 다른 비번이 저장* 되면, *본인도 못 들어감*. 그리고 잠시 후 함정 4 발동.

### 권장 절차

```
1. iDRAC 웹 (https://iDRAC-IP) 접속
2. 좌측 메뉴 iDRAC Settings → User Authentication → Users
3. User ID 2 (root) 클릭
4. Configure User → Change Password 체크
5. 새 비번 입력 *전에 메모장에 먼저 적기*
6. 메모장에서 복사 → New Password 에 붙여넣기
7. 같은 방식으로 Confirm Password
8. Apply
9. *반드시* 1Password / KeePass / 메모장 *외부에 저장*
```

비번 정할 때:
- 12자 이상
- 영문 대소문자 + 숫자 + 특수문자
- 이미 알고 있는 *기존 strong password manager 패턴* 권장
- *복잡하지만 입력 가능* (가상콘솔에서 직접 타이핑할 일 있음)

---

## 함정 4: 비번 5회 틀리면 *600초 잠금* + F2 BIOS 리셋 복구

### 증상

iDRAC 웹 로그인 화면:

```
🚫 Login Error
   RAC0212: Login failed. Verify that username and password is correct.
   
   Log in delayed for 600 seconds.
```

함정 3 의 오타 → *내가 정한 비번* 으로 로그인 시도 → 실패 → 또 시도 → 또 실패 → *5번 누적* → *10분 잠금*. 그리고 잠금 풀려도 *같은 비번* 시도하면 또 잠김 (실제 저장된 비번이 다르니까).

### 해결: F2 BIOS 에서 iDRAC 설정 리셋

물리 점퍼 (메인보드의 작은 점퍼 핀) 까지 안 가도 된다. F2 BIOS 에서 *iDRAC Settings → Reset iDRAC Configurations to Defaults* 가 답.

```
1. 서버 전원 켜기 → Dell 로고 → F2 연타 (System Setup)
2. iDRAC Settings 선택
3. 메뉴 하단의 "Reset iDRAC Configurations to Defaults" 찾기
   (또는 비슷한 이름: "Restore Defaults" / "Reset Configuration")
4. Yes 선택 → 1~2분 소요
   - 비번: calvin 로 초기화
   - 네트워크: DHCP / Dedicated 로 초기화
5. ESC → Save → Exit and Reboot
6. 재부팅 후 iDRAC IP 재할당 (보통 같은 IP 받음 — 같은 MAC 이라서)
7. https://<iDRAC-IP> → root/calvin 로그인
8. *천천히* 비번 변경 (함정 3 의 절차 다시)
```

장점:
- *서버 본체 가까이 안 가도* (모니터/키보드 잠깐만 연결)
- *600초 잠금과 무관* (BIOS 는 잠금 영향 없음)
- *데이터 손실 없음* (메인 OS / 디스크 그대로)

단점:
- 모니터 + USB 키보드 필요 (디스플레이 1번만 잠시)
- iDRAC 네트워크 설정 다시 해야 함 (10분)

### 더 좋은 예방책: 비번 변경 *한 번에 끝내기*

비번 변경 후 *반드시 즉시 새 비번으로 재로그인 테스트*. 메모장에 적은 비번을 *복사*해서 입력. 다른 브라우저 (incognito) 에서 새로 로그인. 이때 *실패하면 즉시 비번 다시 변경* — 변경 직후엔 *기존 세션이 살아있어서* 잠금 없이 또 바꿀 수 있다.

---

## 함정 5: 관리 PC 가 *모뎀 직결* 이라 사설망을 못 봄

### 증상

iDRAC `10.0.50.106` 가 *분명히 살아있는데* 데스크탑 브라우저:

```
사이트에 연결할 수 없음
10.0.50.106에서 응답하는 데 시간이 너무 오래 걸립니다.
ERR_CONNECTION_TIMED_OUT
```

`ipconfig` 결과:

```
이더넷 어댑터 이더넷 4:
   IPv4 주소: 203.0.113.45      ← ⚠️ 공인 IP!
   서브넷 마스크: 255.255.255.224
   기본 게이트웨이: 203.0.113.1
```

### 원인

집 네트워크 토폴로지가 *모뎀 직결* + *공유기 별도* 였다:

```
[ISP 모뎀] ─┬── 데스크탑 (203.0.113.45)  ← 직결, 공인 IP
            │
            └── [ipTime 공유기] ── 노트북 (WiFi) / iDRAC (LAN)
                  10.0.50.1      (10.0.50.x 사설망)
```

데스크탑은 *공인 IP* 를 직접 받아서 사설망 `10.0.50.x` 와 *완전히 다른 네트워크* — 서로 통신 불가. 노트북은 WiFi 로 공유기에 붙어있어서 iDRAC 잘 보였던 것.

### 부가 문제: 보안 노출

공인 IP 를 *직접* 받는다는 건 = *외부 인터넷에서 그대로 접근 가능*. NAT 보호 없이 데스크탑이 인터넷 그라운드에 *벗어있다*. Windows Firewall 만 죽으면 SMB(445) / RDP(3389) 등 무차별 공격 대상.

### 해결

```
[ISP 모뎀] ─── [ipTime 공유기] ─┬── 데스크탑 (LAN, 10.0.50.115)
                  10.0.50.1   ├── 노트북 (WiFi, 10.0.50.x)
                                  └── iDRAC (LAN, 10.0.50.106)
```

1. 데스크탑의 LAN 케이블을 *모뎀이 아니라 공유기 LAN 포트* 로 옮김
2. 데스크탑에서 `ipconfig /release && ipconfig /renew`
3. 새 IPv4 가 `10.0.50.xxx` 로 잡힘 → iDRAC 접속 가능 + NAT 보호도 얻음

---

## 보너스: iDRAC 의 *standby power* 마법

함정 풀면서 자연스럽게 깨닫게 되는 사실:

```
서버 본체 전원 OFF 상태에서도 ⤵️

$ ping 10.0.50.106
64 bytes from 10.0.50.106: time=2.78 ms    ← 응답 ✅
0% packet loss

$ curl -sk https://10.0.50.106/
HTTP/1.1 302 Found                              ← 웹 살아있음 ✅
```

iDRAC 은 PSU 가 콘센트에 *꽂혀있기만* 하면 동작한다. 본체 전원 버튼은 *무관*. 일반 PC 의 *전원 버튼 누르기 전 마더보드 LED 가 깜빡이는 것* 과 같은 원리 — *5V standby 전력*.

이 덕분에:
- 새벽 3시 클러스터 장애 → *서버 가까이 안 가도* 노트북에서 원격 ON
- 평소엔 본체 OFF (전기료 절약, 소음 0) → 필요할 때만 가상콘솔로 켜기
- 디스크 도착 → 본체 OFF 인 상태로 디스크 끼우고 → 노트북에서 원격으로 가상미디어 mount → Ubuntu 설치까지 *원격*

iDRAC Enterprise (가상미디어 라이선스) 의 진가는 여기서 나온다. *한 번도 서버 모니터에 무릎 안 꿇고* OS 설치 → K3s join 까지 가능.

---

## 정리: *기억해둘 명령 / 위치 5종*

| 도구 | 명령 / 위치 |
|---|---|
| iDRAC IP 찾기 (Dell MAC) | `arp -a | grep -i "10:98:36"` (또는 다른 Dell OUI) |
| iDRAC 웹 접속 | `https://<iDRAC-IP>/` (HTTP 도 → HTTPS 로 자동 redirect) |
| 비번 잠금 시 복구 | F2 → iDRAC Settings → Reset Configurations to Defaults |
| 본체 OFF + iDRAC 동작 확인 | `ping <iDRAC-IP>` (응답 오면 standby 살아있음) |
| 데스크탑이 어느 네트워크에 있나 | Windows `ipconfig`, IPv4 의 첫 옥텟이 사설망 (10/172.16-31/192.168) 인지 확인 |

---

## 마지막: *왜* 이걸 글로 정리했나

홈랩 K3s 클러스터에 *6번째 노드를 추가* 하려고 했을 뿐인데, *서버 전원 자체* 부터 5개 함정을 다 밟았다. 매번 검색해도 *각 함정* 은 단편적인 답만 나오고, *연결된 흐름* 이 없어서 한 번에 풀리지 않았다.

R730XD 는 중고 시장에서 *너무 저렴한 가격으로 풀려있어서* (8년된 하드웨어지만 여전히 20코어 / 40스레드 / iDRAC8 Enterprise) 홈랩 입문자가 자주 사게 되는데, 첫 셋업의 함정이 *문서엔 잘 안 정리돼있다*. 이 글이 그 시간을 *한두 시간이라도* 줄여주면 좋겠다.

다음 글에선 *디스크 도착 후 iDRAC 가상미디어로 Ubuntu Server 24.04 설치 → K3s agent join* 까지의 흐름을 정리할 예정.
