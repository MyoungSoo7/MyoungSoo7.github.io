---
layout: post
title: "ATM 종합관리시스템의 여섯 계층 — 각 계층은 무엇 때문에 생겨났나"
date: 2026-09-09 12:46:38 +0900
categories: [아키텍처, 금융]
tags: [ATM, XFS, XFS4IoT, ISO8583, ISO20022, PCI, 키관리, 설정관리, 시스템설계]
---

## 계층이 먼저 있었던 게 아니다

ATM 종합관리시스템의 구성도를 그리면 대개 여섯 덩어리가 나온다. 통신 계층, 데이터 수집·처리, 운영 서버, 관리 화면, 배포·설정 관리, 외부 시스템 연동.

이 여섯이 처음부터 정답으로 정해져 있던 건 아니다. 각각은 **앞선 구조가 무너진 자리**에서 생겼다. 그래서 이 글은 계층별 기능 목록이 아니라, 계층마다 "무엇이 안 돼서 생겼나(등장 이유)"와 "생기기 전과 후에 무엇이 달라졌나(델타)" 두 축으로만 쓴다. 기능 나열은 표준 문서가 이미 훨씬 잘 해놓았고, 그 문서들은 아래 References 에 있다.

같은 날 쓴 [로컬 테스트가 끝내 재현하지 못하는 것](/2026/09/09/global-atm-management-beyond-local-testing/)이 "로컬 테스트의 사각지대" 축이라면, 이 글은 "구성 계층의 존재 이유" 축이다.

---

## ① 통신 계층 — 표준이 전송을 정의하지 않았기 때문에 생겼다

### 등장 이유

ISO 8583 은 흔히 "ATM 통신 프로토콜"이라고 불린다. 정확하지 않다. 현행판 ISO 8583:2023 의 범위 서술은 이렇다 — 어콰이어러와 발급사 사이에서 카드 발생 메시지를 교환하기 위한 **공통 인터페이스**를 규정하고, 메시지 구조·포맷·정규화된 데이터 타입을 정의한다. 그리고 곧바로 다음 문장이 붙는다.

> "The method by which messages are transported or settlement takes place is not within the scope of this document."[^1]

즉 **무엇을 보낼지는 정의하지만 어떻게 보낼지는 정의하지 않는다.** 통신 계층은 이 공백을 메우려고 생긴 계층이다. 프레이밍, 세션 유지, 재전송, 타임아웃, 순서 보장, 암호 채널 — 표준이 범위 밖이라 선언한 것들이 전부 여기로 떨어진다. 그래서 같은 ISO 8583 을 쓴다는 두 시스템이 서로 붙지 않는다. 붙지 않는 이유는 메시지가 아니라 그 아래에 있다.

참고로 ISO 8583:2023 은 3판이고 2023년 7월 18일 발행됐으며, 분리돼 있던 ISO 8583-1:2003 · 8583-2:1998 · 8583-3:2003 을 대체한다. 본문은 18쪽이고, 데이터 요소 정의·코드 목록 같은 실질 내용은 유지기관(Maintenance Agency)이 별도 부속서로 관리한다[^1][^2].

### 델타

장치 접근 쪽에서는 이 공백이 더 극적으로 메워졌다. CEN/XFS 3.x 계열(CWA 16926)의 아키텍처 설명에는 결정적인 한 줄이 있다.

> "Note that the calls are always to a local Service Provider."[^3]

XFS 3.x 에서 장치 호출은 **언제나 로컬**이다. 통신은 애초에 이 규격의 관심사가 아니었다. 반면 후속으로 지목된 XFS4IoT(CWA 17852)는 같은 자리를 이렇게 다시 쓴다 — WebSocket 위에서 JSON 메시지를 주고받으며, "단일 머신에서든 네트워크를 가로질러서든(either on a single machine or across a network)" 동작하는 환경을 다룬다. 연결은 `wss://machinename:portnumber/xfs4iot/v1.0/servicename` 형태의 URI 로 이뤄지고, 원칙적으로 TLS 를 쓰는 `wss` 를 사용하되 **ATM 함체 내부처럼 물리적으로 보호된 구간에 한해서만** 평문 `ws` 를 허용한다[^4].

| | XFS 3.x (CWA 16926) | XFS4IoT (CWA 17852) |
| --- | --- | --- |
| 호출 대상 | 항상 로컬 서비스 프로바이더 | 로컬 또는 네트워크 너머 |
| 전송 | 규격 범위 밖 | WebSocket (RFC 6455) |
| 직렬화 | C API | JSON / JSON Schema 2020-12 |
| 암호화 | 규격 외 | `wss` 원칙, 물리 보호 구간만 예외 |

델타를 한 줄로 줄이면 — **장치 접근이 함수 호출에서 네트워크 프로토콜이 되었다.** 그 순간 통신 계층은 "있으면 좋은 것"에서 "없으면 장치가 안 보이는 것"으로 바뀐다.

---

## ② 데이터 수집과 처리 — 요청/응답만으로는 사실을 표현할 수 없어서 생겼다

### 등장 이유

현금을 내주는 기계에는 요청/응답 한 쌍으로 표현할 수 없는 상태가 있다. **"승인은 났는데 돈이 안 나왔다."**

ISO 20022 의 ATM 거래 메시지 집합(catp)이 이 문제를 구조로 박아 넣었다. 출금은 두 국면으로 나뉜다. 먼저 `catp.001` ATMWithdrawalRequest / `catp.002` ATMWithdrawalResponse 로 승인을 받고, **그 다음에** 실제 방출을 시도한 뒤 결과를 `catp.003` ATMWithdrawalCompletionAdvice / `catp.004` ATMWithdrawalCompletionAcknowledgement 로 보고한다. 입금도 `catp.012`~`catp.015` 로 같은 4단 구조를 갖는다. 반면 조회(`catp.006`/`007`), PIN 관리(`catp.010`/`011`), 이체(`catp.016`/`017`)는 2단으로 끝난다 — 물리적으로 움직이는 것이 없기 때문이다[^5].

이 비대칭이 데이터 수집 계층의 존재 이유다. **물리적 결과가 있는 거래에만 완료 보고가 붙는다.** 수집 계층이 없으면 "승인 후 미방출"이 시스템 어디에도 기록되지 않고, 그 구멍이 고객 분쟁과 손실이 사는 자리다.

### 델타

장치 이벤트 쪽도 같은 방향으로 움직였다. XFS4IoT 는 메시지 타입을 다섯으로 나눈다 — `command`(클라이언트→서비스), `acknowledge`(유효성/큐잉 통보), `event`(진행 중간 보고), `completion`(완료), 그리고 명령과 **무관하게** 올라오는 `unsolicited`[^4].

수집 계층 설계에서 실제로 중요한 건 마지막 둘이다. `completion` 은 요청한 쪽만 받고, `unsolicited` 는 아무도 요청하지 않았는데 온다. 폴링 기반 수집기는 후자를 구조적으로 놓친다.

장치 상태값 열거도 그냥 on/off 가 아니다. XFS4IoT 의 `common/device` 상태에는 `online`, `offline`, `powerOff`, `noDevice`, `hardwareError`, `userError`, `deviceBusy`, `fraudAttempt`, `potentialFraud`, `starting` 이 있다[^4]. 여기서 `userError` 는 "장치는 있는데 사람이 정상 동작을 방해하고 있음"이고, `noDevice` 는 "애초에 그 장치가 있으면 안 되는 구성"이다. 이 둘을 하나의 "장애"로 접으면 현장 출동 판단이 무너진다.

수집 계층 도입 전후의 델타는 **"장애/정상 이진 상태"에서 "원인이 구별되는 상태 기계"로** 바뀐 것이다.

---

## ③ 운영 서버 — 표준이 정책 결정을 애플리케이션에 떠넘겼기 때문에 생겼다

### 등장 이유

XFS4IoT 상태 정의 중 `potentialFraud` 에는 다음 설명이 붙어 있다.

> "The device has detected a potential fraud attempt and is capable of remaining in service. In this case the application should make the decision as to whether to take the device offline."[^4]

읽는 순간 설계가 결정된다. 장치는 **사실만 보고하고, 서비스 중단 여부는 판단하지 않는다.** 그 판단은 "애플리케이션"이 한다. 운영 서버란 결국 표준이 명시적으로 비워둔 이 정책 자리에 앉는 컴포넌트다.

키 관리도 같은 구조다. ATM 은 PIN 을 다루므로 단말에 대칭키가 들어가야 하는데, 사람이 키 부품을 들고 현장에 가서 주입하던 방식은 점포 수가 늘면 성립하지 않는다. ASC X9 는 ANSI X9.24-2(비대칭 기법을 이용한 대칭키 분배)에 부합하는 방법으로 **TR-34** 기술보고서를 발행했고, X9F 분과는 TR-34 사용 증가에 따라 그 방법을 표준화하겠다고 공지하고 있다[^6]. 원격 키 주입은 곧 **키 배포 호스트(KDH)** 라는 서버 역할을 시스템에 새로 만든다.

### 델타

운영 서버가 생기기 전과 후를 가르는 건 기능이 아니라 **책임의 위치**다.

- 전: 장치가 스스로 멈추거나, 사람이 현장에서 멈춘다. 정책은 암묵지다.
- 후: 장치는 상태를 보고하고, 서버가 규칙에 따라 내린다. 정책이 코드와 설정으로 외부화된다.

키에서도 같다. 전에는 키 교체가 **출장 일정**이었고, 후에는 **서버 작업**이 됐다. 대신 새 실패 모드가 따라온다 — KDH 가 죽으면 전 지점의 키 수명이 동시에 만료를 향해 간다. 운영 서버는 정책을 중앙화한 만큼 정확히 그만큼의 단일 실패점을 만든다. 이건 도입의 부작용이 아니라 도입의 정의다.

---

## ④ 관리 화면 — 자산이 원격이고 구성이 제각각이라서 생겼다

### 등장 이유

관리 화면이 대시보드로 보이는 건 결과지, 이유가 아니다. 이유는 **"이 기계가 지금 어떤 부품으로 어떤 버전을 돌리고 있는지 아무도 모른다"** 는 상태다.

ISO 20022 의 ATM 관리 영역(caam)이 이 문제를 정면으로 정의한다. `caam.001` ATMDeviceReport 의 범위는 — ATM 이(또는 대리 에이전트가) 어콰이어러에게 ① 수행한 유지보수 명령의 결과, ② **ATM 의 구성 부품**, ③ 그 부품들의 상태를 보고하는 것이다[^7]. 즉 이 메시지가 나르는 건 "정상/장애"가 아니라 **구성 인벤토리 그 자체**다.

POS 쪽 대응 영역인 catm 의 `catm.001` StatusReport 는 이걸 더 노골적으로 쓴다 — POI 가 터미널 관리자에게 "POI 의 식별자, 그 구성요소들, **그리고 설치된 버전들**"을 포함한 상태를 알린다[^8].

### 델타

- 전: 화면은 **관측치**를 보여준다. "3번 지점 오프라인."
- 후: 화면은 **선언된 구성과 보고된 구성의 차이**를 보여준다. "3번 지점의 카드리더 펌웨어가 관리계획상 버전과 다름."

이 차이가 결정적이다. 관측치만 보는 화면은 장애가 나야 색이 바뀌고, 구성 차이를 보는 화면은 **장애가 나기 전에** 바뀐다. 그리고 후자는 다음 계층 없이는 성립하지 않는다 — 비교할 "선언된 상태"가 어디선가 와야 하기 때문이다.

---

## ⑤ 배포와 설정 관리 — 원격 자산에는 "지금 나가서 바꾸기"가 없어서 생겼다

### 등장 이유

무인 장비 수만 대에 파라미터 하나를 바꿔야 한다고 하자. 서버 배포처럼 "밀어 넣고 재시작"이 안 된다. 장비는 거래 중일 수도 있고, 회선이 끊겨 있을 수도 있고, 전원이 꺼져 있을 수도 있다.

ISO 20022 catm 집합이 이 문제에 준 답은 **푸시가 아니라 계획(plan)** 이다.

- `catm.002` ManagementPlanReplacement — 터미널 관리자가 POI 에게 **"수행할 유지보수 액션들"을 설정한다.** 밀어 넣는 게 아니라, 할 일 목록을 갱신한다.
- `catm.003` AcceptorConfigurationUpdate — TM 이 POI 의 **설정을 갱신한다.**
- `catm.007`/`catm.008` CertificateManagementRequest/Response — POI 가 X.509 인증서 관리를 요청하고, 터미널 관리자가 인증기관 역할로 응답하거나 화이트리스트 등재/해제를 처리한다[^8].

설정 데이터는 카테고리로 쪼개져 있다. `AQPR`(어콰이어러 파라미터), `MRPR`(가맹점 파라미터), `MGTP`(관리계획 자체), 애플리케이션 파라미터 등이 각각 별개의 데이터셋 범주다[^8]. **한 덩어리 설정 파일이 아니라 소유자별로 분리된 설정**이라는 뜻이다.

### 델타

- 전: 설정 변경 = 밀어넣기(push). 장비가 안 받으면 실패. 부분 성공 상태가 시스템에 남지 않는다.
- 후: 설정 변경 = **계획 갱신 + 장비 주도 수렴**. 장비가 접속했을 때(`catm.001`/`caam.001` 보고) 계획을 받아가고 스스로 맞춘다. 부분 수렴 상태가 관리 화면에 그대로 드러난다.

여기서 앞 계층과 고리가 닫힌다. 관리 화면이 "선언 vs 보고"의 차이를 보여줄 수 있는 건 **배포 계층이 선언을 계획으로 만들어두기 때문**이다. 두 계층 중 하나만 만들면 둘 다 반쪽이 된다. 이 수렴 모델이 Kubernetes 의 desired/observed state 와 같은 모양이라는 점도 우연은 아니다 — 원격 자산 함대를 다루면 결국 같은 형태로 수렴한다.

인증서 관리를 **전용 메시지 쌍으로 따로 뺀 것**도 델타의 일부다. 인증서는 만료되면 통신 자체가 죽는다. 그래서 일반 설정 갱신에 섞지 않고 자기 채널을 갖는다.

---

## ⑥ 외부 시스템 연동 — 경계마다 신뢰 모델이 달라서 생겼다

### 등장 이유

ATM 한 대의 출금은 최소 네 주체를 거친다. 카드 소지자, 수납장치(ATM), 어콰이어러, 발급사. ISO 20022 카드 영역이 이 경로를 **구간별로 다른 메시지 집합**으로 나눈 이유가 여기 있다. `catp` 는 ATM↔ATM매니저 구간, `caaa` 는 가맹점 단말↔어콰이어러 구간, 그리고 관리 트래픽은 `caam`/`catm` 으로 분리된다[^5][^8].

왜 굳이 나누나. **구간마다 신뢰 가정과 갱신 주기가 다르기 때문**이다. 거래 트래픽은 고빈도이고 고객이 유발한다. 관리 트래픽은 주기적이고 관리자가 유발한다. 특히 거래를 보호하는 키를 내려보내는 일을 거래 채널에 섞으면, 보호받아야 할 것과 보호 수단이 같은 관에서 흐른다.

카드 자체와의 인터페이스는 또 다른 표준 축이다. EMVCo 의 접촉식 칩 사양은 Book 1(애플리케이션 독립 ICC-단말 인터페이스), Book 2(보안과 키 관리), Book 3(애플리케이션 사양), Book 4(카드 소지자·직원·어콰이어러 인터페이스 요구사항)로 나뉘고, 현행 4.4 판은 2022년 10월 발행됐다[^9][^10].

### 델타

- 전: 하나의 호스트 링크에 거래·관리·키가 모두 흐른다. 경계는 코드 안에 if 문으로 존재한다.
- 후: 경계가 **프로토콜로 존재한다.** caam/catm 메시지는 헤더 + 암호화된 본문(Protected...) + MAC 또는 전자서명을 담은 보안 트레일러 구조를 갖는다[^7]. 어느 구간에서 무엇이 보호되는지가 메시지 구조 자체에 박힌다.

연동 계층이 하는 일은 결국 **번역이 아니라 경계 유지**다. 프로토콜 변환만 하는 어댑터로 설계하면, 구간마다 다른 신뢰 가정이 변환 과정에서 조용히 평탄화된다.

---

## 여섯 계층을 한 표로

| 계층 | 등장 이유 (무엇이 안 됐나) | 델타 (무엇이 달라졌나) |
| --- | --- | --- |
| 통신 | 메시지 표준이 전송을 범위 밖으로 선언 | 장치 접근이 로컬 함수 호출 → 네트워크 프로토콜 |
| 수집·처리 | 승인과 물리적 결과가 다를 수 있음 | 이진 장애 → 원인이 구별되는 상태 기계 |
| 운영 서버 | 표준이 정책 판단을 애플리케이션에 위임 | 정책이 암묵지 → 외부화된 규칙(+ 단일 실패점) |
| 관리 화면 | 원격 자산의 구성을 아무도 모름 | 관측치 표시 → 선언과 보고의 차이 표시 |
| 배포·설정 | 무인 자산엔 즉시 푸시가 없음 | 푸시 → 계획 갱신 + 장비 주도 수렴 |
| 외부 연동 | 구간마다 신뢰 가정이 다름 | 경계가 코드 안 if → 프로토콜과 메시지 구조 |

여섯 계층은 서로 독립이 아니다. ④는 ⑤ 없이는 반쪽이고, ③은 ②가 원인을 구별해 보고해야 판단할 수 있고, ②는 ①이 `unsolicited` 를 흘려보내야 놓치지 않는다. 계층을 하나씩 도입할 수는 있지만, **하나만 도입하면 그 계층이 약속한 효과는 나오지 않는다.**

---

## 근거의 한계

정직하게 적어둔다.

- ISO 8583, ISO 20022 MDR, CEN CWA 문서는 유료이거나 대형 PDF다. 이 글이 인용한 부분은 **각 표준의 공개된 범위(scope)·목차·발췌**에 한정된다. 전문을 대조한 것이 아니다.
- 계층별 설계의 우열을 다룬 **중립 제3자 벤치마크는 찾지 못했다.** 이 글의 "델타"는 표준 문서가 명시한 범위 변화에서 도출한 것이지, 성능·비용 측정이 아니다.
- XFS4IoT 를 XFS 3.x 의 "후속"으로 부르는 근거는 XFS4IoT 사양 본문 서두의 진술("XFS4IoT has been identified as a successor to XFS 3.x")이다[^11]. 다만 XFS 3.x 계열도 별도 CWA 로 유지되고 있으므로, **현장 모수에 두 세대가 공존한다**는 사실이 설계 전제로는 더 중요하다.
- PCI SSC 의 ATM Security Guidelines 는 스스로 "definitive 하지도 exhaustive 하지도 않으며 PCI SSC 검증 프로그램의 요구사항으로 쓰일 의도가 아니다"라고 명시한다[^12]. 인증 근거로 인용하면 안 된다.

---

## References

[^1]: ISO, "ISO 8583:2023 — Financial-transaction-card-originated messages — Interchange message specifications" (Edition 3, published 2023-07-18). <https://www.iso.org/standard/79451.html>
[^2]: ISO Standards Maintenance Portal, ISO 8583 ed-3 부속서 목록. <https://standards.iso.org/iso/8583/ed-3/en/>
[^3]: CEN/XFS Workshop, "CWA 16926-1 — Extensions for Financial Services (XFS) interface specification, Part 1: API/SPI Programmer's Reference". <https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA16926_Release350/cwa16926_part1.pdf>
[^4]: CEN/XFS Workshop, "CWA 17852 — Extensions for Financial Services (XFS): XFS4IoT Specification, 2024-03 Release" (2025-04-23 정정 재발행). <https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA17852/cwa17852_2024-03-release_2025.pdf>
[^5]: ISO 20022, Message Definitions — ATM Card Transactions (`catp.001`–`catp.017`). <https://www.iso20022.org/iso-20022-message-definitions>
[^6]: ASC X9, "X9F Data and Information Security Subcommittee — Project Status" (TR-34 및 X9.24-2 관련 기술). <https://x9.org/standards/x9-project-status/x9f-data-information-security-subcommittee-project-status/>
[^7]: ISO 20022, Message Definitions — ATM Management (`caam.001` ATMDeviceReport, `caam.003`/`caam.004` ATMKeyDownloadRequest/Response). <https://www.iso20022.org/iso-20022-message-definitions>
[^8]: ISO 20022, "Message Definition Report Part 2 — Card Payments Exchanges: catm (Terminal Management)". <https://www.iso20022.org/sites/default/files/2021-12/ISO20022_MDRPart2_CAPE_catm_2021_2022_ForSEGReview_v1.pdf>
[^9]: EMVCo, "EMV Specifications & Associated Bulletins". <https://www.emvco.com/specifications/>
[^10]: EMVCo, "Annual Report 2023" — EMV Contact Chip Specification v4.4 발행 및 Book 구성. <https://www.emvco.com/wp-content/uploads/2024/01/EMVCo-Annual-Report-2023.pdf>
[^11]: CEN/XFS Workshop, XFS4IoT Specification (공개 렌더링본) 서두. <https://xfs4iot.github.io/Specifications-Preview.github.io/2023-02/index.html>
[^12]: PCI Security Standards Council, "Information Supplement: ATM Security Guidelines" (v1.0, January 2013). <https://listings.pcisecuritystandards.org/pdfs/PCI_ATM_Security_Guidelines_Info_Supplement.pdf>
