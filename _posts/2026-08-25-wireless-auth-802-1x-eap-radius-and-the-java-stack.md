---
layout: post
title: "무선인증 서버는 무엇을 하는 프로그램인가 — 802.1X·EAP·RADIUS 와 그 옆의 자바 스택"
date: 2026-08-25 04:02:40 +0900
categories: [network, security]
tags: [802.1x, eap, radius, radsec, netty, protobuf, jdk21, wifi, 본질]
---

채용 공고에 이런 줄이 붙어 있었다.

> Java Concurrent 프로그램 개발 경험 · Linux 배포판(Ubuntu, Rocky) 사용 및 패키지 설치 경험 ·
> JDK17\~21, SpringBoot, Netty, MariaDB, Gradle, JasperReport, Git, SVN, Google Protocol Buffer

그리고 도메인은 **무선인증**이었다.

기술 나열은 그 자체로는 아무 말도 하지 않는다. 하지만 도메인이 붙는 순간 이 목록은
서로 무관한 키워드 더미가 아니라 **한 대의 서버를 분해한 부품표**로 읽힌다.
이 글은 그 부품표를 거꾸로 조립해 보는 글이다. 무선인증이라는 문제가 무엇이고,
그 문제의 어떤 성질이 이 부품들을 하나씩 불러들였는지.

---

## 1. 무선인증은 "비밀번호 맞추기" 가 아니다

집 공유기의 WPA2-PSK 는 모두가 같은 암호 하나를 쓴다. 직원 500명이 쓰는 사내 무선랜에서
이 방식은 성립하지 않는다. 퇴사자 한 명 때문에 전 직원의 Wi-Fi 비밀번호를 바꿔야 하고,
누가 언제 접속했는지 알 방법이 없다.

그래서 기업용 무선랜은 다른 구조를 쓴다. IEEE 802.1X 다.
802.1X 는 **포트 기반 네트워크 접근 제어(Port-Based Network Access Control)** 표준으로,
"인증되기 전까지 이 포트로는 인증 트래픽 말고 아무것도 못 지나간다" 를 규정한다.
현행판은 2020년 2월 28일에 나온 **IEEE Std 802.1X-2020** 이며 802.1X-2010 을 대체한다.[^1]

여기서 등장인물이 셋으로 갈린다.

| 역할 | 실체 | 하는 일 |
|---|---|---|
| Supplicant | 노트북·휴대폰 | 자기가 누구인지 증명 |
| Authenticator | AP·스위치 | 문지기. 판단은 하지 않음 |
| Authentication Server | **우리가 만들 서버** | 실제 판단 |

핵심은 가운데다. **AP 는 인증을 하지 않는다.** AP 는 단말이 보낸 인증 메시지를
그대로 뒤로 넘기고, 뒤에서 "통과" 라는 답이 오면 포트를 연다.
그 뒤에 있는 것이 무선인증 서버이고, 이 글의 주인공이다.

## 2. EAP — 인증 방식이 아니라 인증 방식을 담는 봉투

단말과 서버 사이에 오가는 것은 EAP(Extensible Authentication Protocol) 다.
RFC 3748 이 정의하며, 여기서 자주 오해가 생긴다.
**EAP 는 인증 방식이 아니라 인증 방식을 실어 나르는 프레임워크다.**

RFC 3748 이 명시하는 성질 두 가지가 설계에 직접 영향을 준다.[^2]

1. **여러 인증 방식을 지원한다.** 인증서 기반(EAP-TLS[^3]), 아이디/패스워드 기반,
   SIM 기반 등이 모두 같은 봉투 안에 들어간다. 서버는 방식마다 다른 상태 기계를 돌린다.
2. **IP 없이 동작한다.** EAP 는 PPP 나 IEEE 802 같은 **데이터 링크 계층 위에서 직접** 돈다.
   IP 주소를 아직 못 받은 단말도 인증을 할 수 있어야 하기 때문이다. 당연하다 —
   인증을 통과해야 DHCP 를 받으니까.

두 번째 성질이 아키텍처를 규정한다. 무선 구간의 EAP 는 EAPOL(EAP over LAN) 로 흐르고,
AP 는 그것을 꺼내 **다른 프로토콜에 다시 실어** 인증 서버로 보낸다.
그 "다른 프로토콜" 이 RADIUS 다.

## 3. RADIUS — 25년 된 UDP 프로토콜

RFC 2865(2000년 6월)가 RADIUS 를 정의한다. 공식 포트는 1812,
과금(Accounting)은 RFC 2866 이 따로 맡는다.[^4][^5]

RADIUS 는 **UDP** 위에서 돈다. RFC 2865 는 아예 2.4절 제목을 "Why UDP?" 로 달고
그 선택을 변호한다.[^4] 그리고 같은 문서의 IESG 노트는 이 프로토콜이
혼잡 제어와 확장성 면에서 알려진 한계를 가진다고 스스로 적어 두었다.[^4]
2000년에 이미 그렇게 적혀 있었다.

이 한 줄이 뒤이어 나오는 모든 기술 선택의 이유가 된다.

- **커넥션이 없다.** TCP 처럼 소켓 하나에 세션 하나가 대응하지 않는다.
  수천 대의 AP 가 하나의 UDP 소켓으로 몰려든다.
- **그런데 상태는 있다.** EAP 는 요청/응답을 여러 번 왕복한다.
  EAP-TLS 라면 TLS 핸드셰이크 전체가 그 왕복 위에서 조각나 흐른다.
  **커넥션 없는 전송 위에서 서버가 세션 상태를 직접 들고 있어야 한다.**
- **재전송이 정상이다.** UDP 니까 응답이 늦으면 AP 가 같은 요청을 다시 보낸다.
  서버는 중복 요청을 새 세션으로 착각하면 안 된다.

## 4. 그래서 Netty 이고, 그래서 Java Concurrent 다

이제 부품표의 절반이 설명된다.

**Netty** 는 비동기 이벤트 기반 네트워크 애플리케이션 프레임워크로,
TCP·UDP 소켓 서버를 만드는 데 쓰인다.[^6]
UDP 를 다룬다는 점, 그리고 소켓 수와 세션 수가 분리된다는 점이 정확히 맞아떨어진다.
스레드 하나가 소켓 하나를 붙들고 앉아 있는 모델로는 애초에 표현이 안 되는 문제다.
(Netty 가 무엇을 해결하려고 나타났는지는
[따로 쓴 글]({% post_url 2026-08-24-netty-what-it-solved-before-and-after %})이 있다.)

**Java Concurrent** 가 요구되는 이유도 여기서 나온다.
"동시 접속이 많아서" 라는 뻔한 이유가 아니다. 진짜 이유는 **세션 상태 때문**이다.
EAP 세션은 여러 패킷에 걸쳐 살아 있고, 그 상태는 이벤트 루프 스레드들이 공유한다.
동시성 문제가 나오는 자리가 명확하다 — 세션 테이블, 타임아웃 만료, 재전송 중복 제거.
`ConcurrentHashMap` 을 안다고 되는 게 아니라, 만료와 갱신이 경합할 때
세션이 조용히 사라지거나 두 벌로 갈라지는 걸 막을 줄 알아야 한다.

**JDK 17\~21** 이라는 범위도 우연이 아니다. JDK 21 에서 가상 스레드가 정식 기능이 됐다(JEP 444).
JEP 444 는 그 동기를 **리틀의 법칙**으로 설명한다. 처리량을 올리려면
동시에 살아 있는 요청 수를 늘려야 하는데, 플랫폼 스레드로는 그 수가 막힌다는 것이다.[^7]
비동기 스타일이 그 벽을 우회하는 대가로 코드를 뒤집어 놓았다면,
가상 스레드는 요청당 스레드 모양을 되돌려 준다.

다만 여기서 정직해야 한다. **가상 스레드가 Netty 를 대체하는 것은 아니다.**
가상 스레드가 푸는 건 블로킹 호출에 스레드가 묶이는 문제고,
Netty 가 푸는 건 커넥션 없는 소켓 위에서 프로토콜 상태를 다루는 문제다.
같은 서버 안에서 두 층이 공존하는 쪽이 자연스럽다 —
패킷 층은 이벤트 루프, 인증 백엔드(LDAP·DB·외부 연동) 호출 층은 가상 스레드.

## 5. MariaDB 와 JasperReport — 인증의 절반은 기록이다

RADIUS 규격이 인증(RFC 2865)과 **과금(RFC 2866)** 을 별도 문서로 나눠 놓은 것은
우연이 아니다.[^5] 누가 언제 붙어서 언제 끊었고 얼마나 썼는지를 남기는 일은
인증만큼이나 이 시스템의 본체다. 처음에 말한 "누가 언제 접속했는지 알 방법이 없다" 가
바로 이걸로 풀린다.

그래서 **MariaDB** 가 있다. 계정·정책·인증서 폐기 목록 같은 상태 데이터와,
계속 쌓이는 접속 이력이 함께 들어간다.

그리고 그 옆에 **JasperReport** 가 있다.
JasperReports Library 는 오픈소스 자바 리포팅 엔진으로,
데이터 소스로부터 PDF·Excel·HTML 등으로 출력물을 만든다.[^8]
웹 화면으로 조회하는 것과 **감사에 제출할 수 있는 문서를 뽑는 것**은 다른 요구다.
접속 이력 보고서, 월간 인증 통계, 정책 위반 내역 — 이건 스크린샷으로는 안 되는 종류의 산출물이다.

부품표에 리포팅 라이브러리가 들어 있다는 사실 자체가
이 시스템이 사내 도구가 아니라 **감사받는 시스템**이라는 신호다.

## 6. Protocol Buffers 와 Linux — 이건 어플라이언스다

**Google Protocol Buffers** 가 목록에 있다는 건 무선인증 서버가 단일 프로세스가 아니라는 뜻이다.
RADIUS 를 종단하는 프론트, 정책을 판단하는 부분, 세션·이력을 관리하는 부분이 나뉘어 있고
그 사이에 내부 통신이 있다. 그 자리에 JSON 대신 protobuf 를 쓰는 이유는
스키마가 명시적이고 버전이 진화해도 옛 노드가 깨지지 않기 때문이다.[^9]
공교롭게도 RADIUS 속성 자체가 Type-Length-Value 구조라, 발상이 낯설지 않다.

**Ubuntu·Rocky 배포판 사용 및 패키지 설치 경험**이라는 항목은 인프라 담당자를 뽑는다는 뜻이 아니다.
이 종류의 제품은 대체로 **고객사 안에 설치되는 형태**로 나간다.
데비안 계열과 RHEL 계열 양쪽에 올라가야 하고, 패키지로 묶여야 하고,
고객 방화벽 안에서 문제가 나면 그 서버에 들어가 봐야 한다.
클라우드에 배포하고 끝나는 제품이라면 굳이 배포판 두 계열을 나열하지 않는다.

**Git 과 SVN 이 함께** 적혀 있는 것도 같은 이야기다.
오래 유지보수되는 제품 라인과, 고객사별로 갈라진 브랜치가 있다는 뜻으로 읽는 게 자연스럽다.

## 7. 지금 이 분야에서 실제로 벌어지고 있는 일

여기까지가 구조라면, 마지막은 **왜 지금 이 분야에 사람을 뽑는가**다.
RADIUS 는 조용한 레거시가 아니다. 2024년 이후 이 프로토콜은 재검토 국면에 들어가 있다.

### Blast-RADIUS (CVE-2024-3596)

2024년 공개된 이 취약점은 RADIUS 의 응답 인증이 **MD5** 에 기대고 있다는 사실을 공격한다.
중간자가 MD5 chosen-prefix 충돌을 이용해, 실패한 인증(Access-Reject)에 대한 응답을
**유효한 Access-Accept 로 위조**할 수 있다. 비밀번호를 모르는 채로 통과가 된다.
UDP 위에서 EAP 가 아닌 인증 방식을 쓰는 모든 RADIUS 구현이 영향을 받으며,
단기 완화책은 `Message-Authenticator` 속성을 필수로 강제하는 것이다.[^10][^11]

이 대목에서 앞의 이야기가 다시 걸린다.
EAP 를 쓰는 802.1X 무선인증 경로는 이 공격의 직접 대상이 아니다.
그러나 같은 서버가 관리자 로그인이나 다른 장비 인증에 비-EAP 경로를 열어 두고 있다면 대상이 된다.
**한 프로세스 안에 안전한 경로와 위험한 경로가 공존한다** 는 게 이 취약점의 실무적 형태다.

### 전송 계층을 바꾸는 쪽으로 가고 있다

근본 해법은 RADIUS 를 TLS 안에 넣는 것이다.
RADIUS/TLS(RadSec)는 RFC 6614(2012), RADIUS/DTLS 는 RFC 7360(2014)으로 이미 나와 있는데,
**둘 다 Experimental** 이었다.[^12][^13] 이제 그 상태를 바꾸려는 작업이 진행 중이다.

여기서부터는 **아직 RFC 가 아니다**. 사실 확인이 필요한 부분이라 명시해 둔다.

- `draft-ietf-radext-deprecating-radius` — UDP·TCP 위의 RADIUS 를 폐기(deprecate)하고
  TLS 전송을 요구하는 방향의 IETF 작업 문서. 2026년 7월 기준 10판까지 나왔고
  Standards Track 을 목표로 하며, 승인되면 RFC 2865/2866/5176/7585 를 갱신한다.[^14]
- `draft-ietf-radext-radiusdtls-bis` — RadSec 개정판. 2026년 7월 기준 IESG 에 제출된 상태이며,
  승인되면 RFC 6614 와 7360 을 대체한다.[^15]

즉 **"RADIUS 는 UDP 프로토콜이다" 라는 전제 자체가 지금 교체되는 중**이다.
25년 된 프로토콜의 전송 계층을 바꾸는 일이고, 현장에는 그 전제 위에 세워진 서버가 잔뜩 있다.
사람을 뽑는 이유로 이만한 게 없다.

### 무선 쪽도 같은 방향이다

Wi-Fi Alliance 는 WPA3 를 Wi-Fi CERTIFIED 기기의 필수 요건으로 두고 있으며,
낡은 레거시 프로토콜을 배제하고 **관리 프레임 보호(PMF)** 를 요구한다.[^16]
암호화되지 않던 관리 프레임 — 접속 해제 요청 같은 것들 — 이 그동안 공격 표면이었다.

## 정리

무선인증 서버는 이런 문제를 푸는 프로그램이다.

- 인증이 끝나기 전이라 **IP 도 없는** 단말과 대화해야 한다 → EAP
- 그 대화가 **커넥션 없는 UDP** 위에서 여러 왕복에 걸쳐 이어진다 → Netty, 그리고 공유 세션 상태
- 세션 상태를 여러 스레드가 만지는데 **조용히 틀리면 인증이 뚫린다** → Java Concurrent
- 백엔드 조회로 스레드가 묶이면 처리량이 막힌다 → JDK 21 가상 스레드
- 인증만큼 **기록이 본체**다 → MariaDB, JasperReport
- 서버가 여러 조각으로 나뉘어 있다 → Protocol Buffers
- **고객사 안에 설치되는 제품**이다 → Ubuntu/Rocky, 패키지, SVN
- 그리고 지금 이 프로토콜의 **전송 계층이 교체되는 중**이다 → RadSec, 그리고 진행 중인 IETF 작업

기술 목록을 목록으로 읽으면 외울 것이 여덟 개다.
도메인을 알고 읽으면 하나다.

---

## 근거의 한계

- 7절의 IETF 문서 두 건은 **Internet-Draft** 이며 RFC 가 아니다.
  드래프트는 언제든 바뀌거나 폐기될 수 있으므로, 위 내용은 인용 시점(2026년 7월 판) 기준이다.
- 이 글은 특정 제품의 내부 구조를 서술한 것이 아니라,
  공개 표준과 기술 목록으로부터 역으로 추론한 것이다. 개별 벤더의 실제 구현은 다를 수 있다.
- 성능 수치는 재현 가능한 중립 측정치를 확인하지 못해 일절 싣지 않았다.

## References

[^1]: IEEE, "IEEE Standard for Local and Metropolitan Area Networks—Port-Based Network Access Control" (IEEE Std 802.1X-2020), 2020-02-28. <https://standards.ieee.org/ieee/802.1X/7345/>
[^2]: B. Aboba et al., "Extensible Authentication Protocol (EAP)", RFC 3748, June 2004. <https://www.rfc-editor.org/rfc/rfc3748>
[^3]: D. Simon, B. Aboba, R. Hurst, "The EAP-TLS Authentication Protocol", RFC 5216, March 2008. <https://www.rfc-editor.org/rfc/rfc5216>
[^4]: C. Rigney et al., "Remote Authentication Dial In User Service (RADIUS)", RFC 2865, June 2000. (§2.4 "Why UDP?", IESG Note) <https://www.rfc-editor.org/rfc/rfc2865>
[^5]: C. Rigney, "RADIUS Accounting", RFC 2866, June 2000. <https://www.rfc-editor.org/rfc/rfc2866>
[^6]: The Netty Project, "Netty User Guide for 4.x". <https://netty.io/wiki/user-guide-for-4.x.html>
[^7]: R. Pressler, A. Bateman, "JEP 444: Virtual Threads", OpenJDK. (JDK 21 정식 기능) <https://openjdk.org/jeps/444>
[^8]: Jaspersoft, "JasperReports® — Free Java Reporting Library". <https://github.com/Jaspersoft/jasperreports>
[^9]: Protocol Buffers 공식 문서. <https://protobuf.dev/>
[^10]: CERT/CC, "Vulnerability Note VU#456537: RADIUS protocol susceptible to forgery attacks". <https://www.kb.cert.org/vuls/id/456537>
[^11]: Blast-RADIUS 연구팀, "Blast-RADIUS (CVE-2024-3596)". <https://www.blastradius.fail/>
[^12]: S. Winter et al., "Transport Layer Security (TLS) Encryption for RADIUS", RFC 6614, May 2012. (Experimental) <https://www.rfc-editor.org/rfc/rfc6614>
[^13]: A. DeKok, "Datagram Transport Layer Security (DTLS) as a Transport Layer for RADIUS", RFC 7360, September 2014. (Experimental) <https://www.rfc-editor.org/rfc/rfc7360>
[^14]: A. DeKok, "Deprecating Insecure Practices in RADIUS", draft-ietf-radext-deprecating-radius-10, IETF Internet-Draft, 2026-07-03. <https://datatracker.ietf.org/doc/draft-ietf-radext-deprecating-radius/>
[^15]: "(D)TLS as a Transport Layer for RADIUS", draft-ietf-radext-radiusdtls-bis, IETF Internet-Draft. <https://datatracker.ietf.org/doc/draft-ietf-radext-radiusdtls-bis/>
[^16]: Wi-Fi Alliance, "Security". <https://www.wi-fi.org/discover-wi-fi/security>
