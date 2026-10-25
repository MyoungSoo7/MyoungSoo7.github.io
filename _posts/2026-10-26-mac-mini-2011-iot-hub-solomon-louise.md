---
layout: post
title: "2011년형 맥미니가 IoT 허브가 되기까지 — solomon 시점에서 본 louise 와의 한 달"
date: 2026-10-26 05:32:09 +0900
categories: [IoT, Homelab, Security]
tags: [IoT, MQTT, Mosquitto, mTLS, PKI, Mac mini, homelab, OTA]
---

> [지난 글](/2026/10/06/homelab-iot-lab-what-doing-it-right-took/)은 **기기(louise)** 쪽에서 본 IoT 보안 랩이었다.
> 이번 글은 반대편, **허브 역할을 맡은 2011년형 맥미니(solomon)** 쪽 이야기다.
> 숫자는 모두 2026-10-26 새벽 solomon 에서 직접 잰 값이고, 홈랩 네트워크 정보(주소·장비 식별자)는 뺐다.

## 결론

- 15년 된 맥미니 한 대가 **MQTT 브로커 + 랩 CA + 수집기 + 탐지기**를 한 달째 맡고 있다.
  브로커 두 개를 합친 메모리는 **10MiB 이하**, 탐지기는 **약 32MB** 다. 하드웨어가 병목이었던 적은 없다.
- 허브가 하는 일의 핵심은 연산이 아니라 **"누구를 믿을지 정하는 일"** 이다 — 인증서 서명, 신원 = 권한 매핑, 이상 감지.
- 한 달 운영에서 가장 많이 울린 경보는 공격이 아니라 **louise 가 조용해졌다는 경보**였다(Last Will 53회).
  보안 랩의 일상은 대부분 "기기가 살아 있나" 를 판정하는 일이었다.

## 0. 역할 분담 — 허브와 기기

| | solomon (허브) | louise (기기) |
|---|---|---|
| 하드웨어 | Mac mini (Mid 2011), Core i5-2415M(논리 CPU 4개), RAM 15GiB(OS 표시) | 2018년 삼성 2-in-1 노트북 |
| 하는 일 | 브로커, CA(서명만), 수집·탐지, OTA 서명 | 센서 데이터 발행, 키 생성, OTA 검증 |
| 만지는 사람 | solomon 의 봇 | louise 의 봇 |

맥미니의 모델 식별자는 노드에서 직접 읽은 `Macmini5,1` 이고, 애플 문서상 이 식별자는
[Mac mini (Mid 2011)](https://support.apple.com/en-us/102852) 이다.

두 노드는 **각자의 봇이 자기 노드만 만진다.** solomon 은 louise 에 로그인하지 않고,
louise 의 개인키도 본 적이 없다. 둘 사이에 오가는 건 CSR(서명 요청)과 서명된 인증서, MQTT 메시지뿐이다.
이 분리가 그대로 보안 모델이 된다 — 허브가 털려도 기기 개인키는 허브에 없다.

## 1. 허브의 첫 번째 일 — 서명하되, 아무거나 서명하지 않는다

랩 CA 는 EC P-256 키를 쓰고 solomon 에만 있다. 기기는 자기 키를 **자기 위에서** 만들고 CSR 만 보낸다.
서명 스크립트가 거절하는 경우는 세 가지다.

```bash
# sign-csr.sh 요지
[[ "$cn" =~ ^device-[a-z0-9-]+$ ]]          || refuse "CN 형식 위반"
openssl req -in "$csr" -noout -verify         || refuse "CSR 서명 무효"
[[ -e issued/$cn.crt ]]                        && refuse "이미 발급됨 (폐기/교체 먼저)"
openssl x509 -req ... -days 397 -sha256 ...
```

- **CN 을 `device-` 로 제한**하는 이유는, 뒤에서 보듯 CN 이 곧 MQTT 사용자 이름이 되기 때문이다.
  `ops`·`collector` 같은 운영 신원을 기기 CSR 로 받아내는 길을 막는다.
- **이미 발급된 CN 재발급 거절**은 같은 신원을 가진 인증서가 둘이 되는 걸 막는다(3절에서 이게 왜 중요한지 나온다).
- 유효기간 397일은 "1년에 한 번은 교체한다" 는 운영 습관을 강제하려고 고른 값이다. 사설 CA 라 외부에서 강제되는 상한은 없다.

현재 발급된 기기 인증서는 `device-louise` 와 반도체 랩 게이트웨이 `device-fab-gw01` 두 장이다.
같은 허브가 성격이 다른 기기 두 대를 같은 규칙으로 받고 있다.

## 2. 허브의 두 번째 일 — 신원이 곧 권한

브로커는 Mosquitto 2(컨테이너 안에서 `mosquitto -h` 로 확인한 버전은 2.1.2)이고, 핵심 설정은 이게 전부다.

```conf
allow_anonymous false
listener 8883
require_certificate true          # 클라이언트 인증서 없으면 TLS 단계에서 끊는다
use_identity_as_username true     # 인증서 CN = MQTT 사용자 이름
use_username_as_clientid true     # 사용자 이름 = client-id  (3절의 수정)
tls_version tlsv1.2
acl_file /mosquitto/config/acl
```

각 옵션의 의미는 [mosquitto.conf 공식 매뉴얼](https://mosquitto.org/man/mosquitto-conf-5.html)에 있다.
ACL 은 패턴 하나로 모든 기기를 덮는다. `%u` 가 사용자 이름, 즉 인증서 CN 으로 치환된다.

```conf
pattern write iot/%u/telemetry/#
pattern write iot/%u/status
pattern write iot/%u/event/#
pattern read  iot/%u/cmd/#
pattern read  iot/%u/ota/#
```

기기를 하나 더 붙여도 ACL 은 한 줄도 안 바뀐다. **인증서를 하나 서명하는 것이 곧 권한을 주는 것**이다.
그래서 1절의 서명 규칙이 허브 보안의 전부라고 해도 과장이 아니다.

검증 결과(2026-09-26):

| 시도 | 결과 |
|---|---|
| 인증서 없이 접속 | TLS 단계 거절 (`peer did not return a certificate`) |
| 다른 CA 로 만든 `CN=device-louise` 인증서 | 거절 (`certificate verify failed`) |
| 정상 기기가 남의 토픽에 발행 | MQTT 5 에선 PUBACK 사유 코드 135(0x87, Not authorized), 3.1.1 에선 조용히 버려짐 |
| 정상 기기가 `iot/#` 구독 | 아무것도 안 옴 |

사유 코드 0x87 의 정의는 [MQTT 5.0 명세](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)의 PUBACK Reason Code 표에 있다.
3.1.1 에는 PUBACK 에 사유 코드가 없어서([MQTT 3.1.1 명세](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html)) 기기는 거절당한 줄도 모른다.
**허브 쪽 로그를 봐야 하는 이유**가 여기 있다.

## 3. 허브에서 찾은 구멍 — 정상 인증서로 하는 DoS

처음 설정에는 `use_username_as_clientid` 가 없었다. 그러자 이런 일이 됐다.

1. 정상 발급된 **아무 기기 인증서**로 접속하면서 client-id 만 `device-louise` 로 적는다.
2. MQTT 는 같은 client-id 의 새 연결이 오면 **기존 연결을 끊는다**(명세상 정상 동작).
3. 진짜 louise 가 "session taken over" 로 끊기고, 브로커는 louise 의 Last Will(offline)을 뿌린다.

ACL 은 사용자 이름(CN) 기준이라 이 사칭 연결은 louise 토픽에 쓸 수 없었다. 즉 **데이터 위조는 막혔지만 가용성은 뚫렸다.**
`use_username_as_clientid true` 로 client-id 를 CN 에 묶어서 고쳤다.

대가도 있었다. 이제 **같은 인증서로 두 프로세스가 붙으면 서로를 계속 쫓아낸다.**
그래서 허브에서 상시 도는 수집기와 탐지기는 각자 `collector`, `detector` 인증서를 따로 받았다.
1절에서 "이미 발급된 CN 재발급 거절" 을 넣은 것도 같은 이유다 — 한 신원, 한 인증서, 한 연결.

## 4. 허브의 세 번째 일 — 감시

탐지기는 systemd 사용자 서비스로 돌면서 두 군데를 본다.

- **메시지 스트림**(`iot/#` 구독): 전원 어댑터 분리·저전력, 기울기 20° 이상 변화, 120초 무응답, OTA 결과
- **브로커 로그**: TLS 실패 폭주(60초에 5회), ACL 거부, 세션 탈취(3절), Last Will

경보는 텔레그램과 `alerts.jsonl` 에 동시에 남는다. 2026-09-26 부터 10-23 까지 쌓인 314건을 종류별로 세면:

| 종류 | 건수 | 내용 |
|---|---:|---|
| fab | 167 | 반도체 랩 게이트웨이 경보 (별도 실험) |
| silence | 123 | 무응답·Last Will·복귀 |
| motion | 10 | 기기 측 충격 감지 |
| ota | 6 | 서명 OTA 검증 결과 (실험) |
| dup | 5 | 같은 client-id 중복 접속 (3절 실험) |
| acl | 3 | 남의 토픽 접근 거부 (실험) |

`silence` 123건 중 louise 의 Last Will 이 **53회**, "다시 수신됨" 이 44회, 120초 무응답이 25회다.
같은 키의 경보는 10분 안에 다시 울리지 않게 묶어 두었으니 실제 끊김은 이보다 많을 수 있다.

솔직히 말하면 **이 끊김들의 원인은 아직 분리하지 못했다.** louise 의 절전·네트워크·프로세스 재시작 중 무엇인지
허브 쪽 로그만으로는 구분이 안 된다. 허브가 확실히 말할 수 있는 건 "연결이 비정상 종료됐다" 까지다.
이 구분이 왜 어려운지는 [Keep Alive 와 Last Will 글](/2026/10/04/mqtt-keep-alive-last-will-silent-device/)에 따로 정리했다.

반대로 `acl`·`dup`·`ota` 는 모두 첫날 일부러 일으킨 실험이고, 그 뒤 한 달 동안 **실제 공격성 경보는 0건**이었다.
닫힌 홈랩이라 당연한 결과이기도 하다. 그래서 이 숫자는 "안전하다" 가 아니라 "탐지기가 조용할 때 조용하다(오탐이 없다)" 정도로만 읽는 게 맞다.

## 5. 허브의 네 번째 일 — 업데이트에 서명한다, 기기는 검증만 한다

OTA 는 허브가 Ed25519 키로 서명하고 louise 는 공개키를 고정해 두고 **검증만** 한다(실행은 안 함).
Ed25519 의 정의는 [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032) 다. 허브에서 일부러 보낸 일곱 가지 경우:

| 보낸 것 | louise 판정 |
|---|---|
| 정상 1.1.0 | 통과 |
| 같은 패키지 재전송 | `replayed_nonce` |
| 본문 변조 | `bad_signature` |
| 키 ID 를 사칭한 위조 서명 | `bad_signature` |
| 만료 | `expired` |
| 0.9.0 (다운그레이드) | `downgrade` |
| 다른 기기용 | `wrong_device` |

서명 키는 허브에만 있고 ACL 상 OTA 토픽에 쓸 수 있는 신원은 `ops` 뿐이다.
**OTA 를 보내려면 서명 키와 ops 인증서 둘 다 필요하다** — 허브 한 곳에 몰려 있다는 점은 남은 숙제다.

## 6. 15년 된 하드웨어로 충분했나

2026-10-26 새벽 실측:

| 구성 요소 | 측정 |
|---|---|
| 보안 브로커 컨테이너 | CPU 0.07%, 메모리 7.4MiB (상한 256MiB) |
| 수집 브로커 컨테이너 | CPU 0.01%, 메모리 1.5MiB |
| 탐지기 (Python) | RSS 약 32MB, 15일째 무중단 |
| 노드 가동 시간 | 42일 |

기기 두 대, 10초 간격 샘플이면 이 정도가 당연하다. 이 규모에서 허브의 병목은 CPU 가 아니라
**사람이 경보를 읽는 시간**이었다. 314건 중 절반 이상이 한 실험(fab)에서 나왔고, 그걸 묶는 디바운스를 늦게 넣었다.

전력 쪽은 [홈랩 전력 비교 글](/2026/10/17/homelab-power-louise-solomon-lemuel/)에서 애플 공식 수치로 따로 다뤘다.

## 정리 — 허브는 "믿음의 경계" 다

맥미니가 한 달 동안 한 일을 한 줄로 줄이면 이렇다.

> 누구에게 인증서를 줄지 정하고(1절), 그 인증서 이름으로 권한을 그리고(2절),
> 그 이름을 두 연결이 나눠 갖지 못하게 하고(3절), 조용해진 이름을 알아차리고(4절),
> 그 이름에게 보낼 업데이트에 서명한다(5절).

연산은 2011년 CPU 로도 남는다. 어려운 건 그 경계를 정확히 긋는 일과, 경계에서 울리는 소리를 해석하는 일이었다.

## References

- Apple, [Identify your Mac mini model](https://support.apple.com/en-us/102852) — Macmini5,1 = Mac mini (Mid 2011)
- Eclipse Mosquitto, [mosquitto.conf(5) man page](https://mosquitto.org/man/mosquitto-conf-5.html) — `require_certificate`, `use_identity_as_username`, `use_username_as_clientid`, `acl_file` 패턴(`%u`)
- OASIS, [MQTT Version 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html) — PUBACK Reason Code 0x87, Will Message, 같은 Client Identifier 의 기존 연결 처리
- OASIS, [MQTT Version 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html) — PUBACK 구조(사유 코드 없음)
- IETF, [RFC 8032 — Edwards-Curve Digital Signature Algorithm (EdDSA)](https://www.rfc-editor.org/rfc/rfc8032)
