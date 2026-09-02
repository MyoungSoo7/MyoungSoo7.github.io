---
layout: post
title: "SMTP 서버의 변천사 — 신뢰의 자리가 옮겨온 44년"
date: 2026-09-02 22:12:48 +0900
categories: [infrastructure, protocol]
tags: [smtp, mail, rfc, dmarc, dkim, spf, sendmail, postfix]
---

SMTP 를 처음 규정한 RFC 821 은 1982년 8월 문서다.[^rfc821] 지금 쓰는 RFC 5321 은
2008년이고,[^rfc5321] 명령어는 여전히 `HELO`/`MAIL FROM`/`RCPT TO`/`DATA` 다. 44년 동안
프로토콜의 뼈대는 사실상 그대로다.

그런데 메일 서버를 운영해 본 사람은 안다. 1982년의 SMTP 서버와 2026년의 SMTP 서버는
같은 물건이 아니다. **바뀐 건 프로토콜이 아니라 "무엇을 믿을 것인가"의 자리**다. 처음에는
네트워크를 믿었고, 그다음에는 연결을 믿었고, 지금은 도메인을 믿는다. SMTP 서버의 변천사는
그 신뢰의 자리가 한 칸씩 옮겨온 기록으로 읽을 때 가장 잘 설명된다.

## 연대표

| 시점 | 문서 / 사건 | 옮겨간 것 |
|---|---|---|
| 1981.11 | RFC 788 (RFC 780 폐기)[^rfc788] | SMTP 의 첫 형태 |
| 1982.08 | RFC 821, Postel[^rfc821] | STD 10 확정 |
| 1983 | Allman, sendmail[^allman] | 설정을 코드 밖으로 |
| 1986.01 | RFC 974 — MX 레코드[^rfc974] | 라우팅을 DNS 로 |
| 1988.11 | 모리스 웜[^rfc1135] | 메일 서버 = 원격 실행 표면 |
| 1995.11 | RFC 1869 — ESMTP[^rfc1869] | 확장 가능한 골격 |
| 1998.12 | RFC 2476 — 제출/전송 분리[^rfc2476] | 25 와 587 이 갈라짐 |
| 1999.01–02 | RFC 2487 STARTTLS[^rfc2487], RFC 2505 BCP 30[^rfc2505] | 연결을 믿기 시작 |
| 2008.10 | RFC 5321[^rfc5321] | 현행 SMTP |
| 2011–2014 | DKIM(STD 76)[^rfc6376], SPF[^rfc7208] | 도메인을 믿기 시작 |
| 2015.03 | DMARC (Informational)[^rfc7489] | 정렬과 보고 |
| 2015–2018 | DANE[^rfc7672], MTA-STS[^rfc8461], RFC 8314[^rfc8314] | 평문이 "구식"이 됨 |
| 2026.05 | RFC 9989/9990 — DMARC 표준화 트랙[^rfc9989][^rfc9990] | 30년 만의 정리 |

## 1. 릴레이가 미덕이던 시절

RFC 821 의 SMTP 서버는 받은 메일을 다음 홉으로 넘겨주는 것이 존재 이유였다. 인증이라는
개념 자체가 명세에 없다. 당시 네트워크는 서로를 아는 기관들의 집합이었고, "아무나 보낸
메일을 아무 데로나 전달해 준다"는 성질은 결함이 아니라 **기능**이었다. 네트워크에 붙어
있다는 사실 자체가 신뢰의 근거였기 때문이다.

라우팅도 지금과 달랐다. 어느 호스트로 보낼지는 호스트 테이블에 의존했고, 도메인 이름으로
메일 목적지를 찾는 방식(MX 레코드)은 1986년 1월 RFC 974 에서야 정리된다.[^rfc974] 이때
비로소 "메일 도메인"과 "그 메일을 실제로 받는 서버"가 분리된다. `example.com` 의 메일을
받는 기계가 `example.com` 이 아니어도 되는 세계가 여기서 열렸다 — 오늘날 모든 매니지드
메일 서비스가 서 있는 지반이다.

## 2. sendmail: 설정을 코드 밖으로 꺼낸 것

이 시기 서버 소프트웨어의 대표는 Eric Allman 의 sendmail 이다. Allman 자신의 문서는
sendmail 을 "delivermail 의 후신"으로 소개하면서 첫 번째 차이로 이것을 든다 — 설정 정보가
컴파일되어 들어가지 않는다는 것.[^allman] 4.2BSD 매뉴얼도 delivermail 이 sendmail 로
대체되었고 컴파일된 설정 DB 가 사라졌다고 적고 있다.[^bsd42]

지금 보면 당연한 이야기지만, 이게 sendmail 을 20년 넘게 사실상의 표준으로 만든 성질이다.
프로토콜과 네트워크가 해마다 바뀌는 환경에서, 바이너리를 다시 빌드하지 않고 텍스트 설정만
고쳐 대응할 수 있다는 것. 그 대가로 우리는 악명 높은 `sendmail.cf` 를 얻었지만.

## 3. 1988년 11월: 메일 서버가 공격 표면이 되던 밤

모리스 웜이 sendmail 의 `DEBUG` 기능 등을 이용해 퍼진 사건은 RFC 로도 기록되어 있다 —
1989년 12월의 RFC 1135, 제목이 "Helminthiasis of the Internet"(인터넷의 기생충증)이다.
1988년 11월 2일 저녁에 풀려난 웜을 되돌아본 문서다.[^rfc1135]

여기서 인식이 하나 바뀐다. **메일 서버는 인터넷 전체에 열려 있는 상시 프로세스**이고,
그 프로세스가 대개 루트 권한으로 돈다는 사실이다. 이후 20년간의 MTA 설계 경쟁은 상당
부분 이 한 문장에 대한 대응이다.

## 4. ESMTP: 바꾸지 않고 늘리는 법

1995년 11월 RFC 1869 는 SMTP 확장 프레임워크를 정의한다. 클라이언트가 `EHLO` 로 인사하면
서버가 자기가 지원하는 확장 목록을 돌려주는 방식이다.[^rfc1869] 이 문서 자체는 새 기능을
거의 추가하지 않는다. 대신 **이후에 추가될 모든 것이 들어올 자리**를 만들었다.

실제로 그 뒤의 역사는 전부 이 골격 위에 얹힌다. `AUTH`, `STARTTLS`, `SIZE`,
`SMTPUTF8`[^rfc6531] — 전부 EHLO 응답 줄 하나로 협상된다. 프로토콜의 뼈대를 바꾸지 않고도
40년을 버틴 비결이 여기 있다. 오래 가는 프로토콜은 완성된 프로토콜이 아니라 **확장 지점이
명시된** 프로토콜이라는 사례다.

## 5. 1996–1998: 아키텍처로 푸는 보안

이 시기에 sendmail 의 대안들이 한꺼번에 등장한다.

- **qmail** (D. J. Bernstein) — 보안을 기능이 아니라 설계 제약으로 다뤘고, 저자가 직접
  보안 보증(security guarantee)을 내걸었다.[^qmail]
- **Postfix** (Wietse Venema) — 프로젝트 홈페이지의 표현 그대로, "널리 쓰이던 sendmail 의
  대안으로 IBM 리서치에서 시작한" 메일 서버다.[^postfix]
- **Exim** (Philip Hazel) — 케임브리지 대학에서 유닉스 시스템용으로 개발됐고, sendmail
  자리에 그대로 대체 설치할 수 있게 설계됐다.[^exim]

세 프로젝트의 접근은 제각각이지만 공통점이 하나 있다. **하나의 거대한 특권 프로세스를
작은 프로세스 여럿으로 쪼갠 것**. 네트워크에서 바이트를 받는 부분과 메일박스에 쓰는 부분이
같은 권한을 가질 이유가 없다는, 지금은 상식이 된 발상이다. 컨테이너 시대의 최소 권한
원칙과 정확히 같은 이야기를 20년 앞서 한 셈이다.

## 6. 1998–1999: 진짜 분기점 — 25 와 587 이 갈라지다

스팸이 산업이 되면서, "아무나 받아서 아무 데로나 전달"이라는 원래의 미덕이 그대로
취약점이 됐다. 오픈 릴레이 문제다. 대응은 세 갈래로 동시에 왔다.

**① 제출과 전송의 분리.** 1998년 12월 RFC 2476 이 메시지 제출(submission)을 메시지
릴레이에서 떼어낸다. 지금 표준인 RFC 6409(STD 72)는 이 구조를 이렇게 요약한다 — 릴레이는
영향받지 않고 계속 25번 포트의 SMTP 를 쓰며, 제출은 통상 587번 포트에서 이 문서의
프로토콜을 쓴다.[^rfc2476][^rfc6409] 사용자가 자기 메일을 밀어넣는 통로와 서버끼리
주고받는 통로는 요구되는 보안·정책이 다르다는 인식이다. **오늘날 메일 클라이언트 설정에
587 을 적는 이유가 여기서 나왔다.**

**② 연결 암호화.** 1999년 1월 RFC 2487 이 STARTTLS 를 정의한다(현행은 2002년의 RFC
3207).[^rfc2487][^rfc3207]

**③ 인증.** SMTP AUTH 가 들어오고(RFC 2554, 현행 RFC 4954[^rfc4954]), 같은 해 2월
RFC 2505 는 BCP 30 으로 MTA 의 안티스팸 구현 권고를 정리한다.[^rfc2505]

이 셋이 합쳐진 결과가 오늘 우리가 아는 메일 서버다. **신뢰의 자리가 "네트워크에 붙어
있음"에서 "인증된 연결"로 옮겨온 지점.**

## 7. 2006–2015: 도메인을 믿기 시작하다

연결을 믿는 것만으로는 부족했다. SMTP 는 설계상 보내는 쪽이 `MAIL FROM` 과 `HELO` 에
무엇을 쓰든 제약하지 않는다 — SPF 명세가 자기 존재 이유를 설명하며 그대로 지적하는
지점이다.[^rfc7208] 연결이 암호화되어 있어도 발신자를 사칭하는 것은 여전히 가능했다.

그래서 축이 한 번 더 옮겨간다. 연결이 아니라 **도메인**을 인증 단위로 삼는 것이다.

- **SPF** — 도메인 소유자가 자기 도메인 이름으로 메일을 보낼 수 있는 호스트를 DNS 로
  명시한다. 현행은 2014년 4월 RFC 7208(RFC 4408 폐기).[^rfc7208]
- **DKIM** — 서명 도메인이 메시지에 서명해 그 메시지에 대한 책임을 주장한다. 2011년 9월
  RFC 6376, STD 76.[^rfc6376]
- **DMARC** — 위 둘의 결과를 **헤더의 From 도메인과 정렬**시키고, 실패 시 처리 방침을
  도메인 소유자가 선언하며, 리포트를 받는다. 2015년 3월 RFC 7489.[^rfc7489]

여기서 눈여겨볼 것은 DMARC 가 오랫동안 **Informational** 이었다는 사실이다. 사실상 전
세계 메일이 그 위에서 돌아가는데도 표준화 트랙 문서가 아니었다. 게다가 그것은
독립 제출(Independent Submission)이었다.

## 8. 2015–2018: 전송 구간의 신뢰

STARTTLS 에는 구조적 약점이 있다. 평문으로 시작해 협상으로 올라가는 방식이라, 중간자가
`STARTTLS` 광고를 지워버리면 그냥 평문으로 떨어진다. 두 가지 답이 나왔다.

- **DANE for SMTP** (2015년 10월 RFC 7672) — DNSSEC 로 서명된 TLSA 레코드에 기대어
  다운그레이드에 저항하는 방식.[^rfc7672]
- **MTA-STS** (2018년 9월 RFC 8461) — DNSSEC 없이 HTTPS 로 게시한 정책으로 같은 문제를
  다루는 방식. 저자 소속이 Google·Oath·Comcast·Microsoft 로 걸려 있는 것이 이 문서의
  성격을 말해준다.[^rfc8461]

그리고 2018년 1월, 제목 자체가 결론인 문서가 나온다 — RFC 8314, "Cleartext Considered
Obsolete".[^rfc8314] 사용자와 서버 사이 구간에서 평문은 더 이상 기본값이 아니게 됐다.

## 9. 그리고 2026년 5월: DMARC 가 제자리를 찾다

이 글을 쓰는 기준으로 가장 최근의 변화다. **RFC 7489 는 폐기됐다.** 2026년 5월 19일
공개된 RFC 9989 가 DMARC 프로토콜 본체를,[^rfc9989] RFC 9990 이 집계 리포팅을[^rfc9990]
가져가면서 RFC 7489 를 폐기했고, 둘 다 **Standards Track** 이다. 11년간 Informational
문서로 굴러가던 사실상의 표준이 드디어 형식을 갖췄다.

## 그래서, 지금 SMTP 서버를 세운다는 것

44년의 궤적을 한 줄로 압축하면 이렇다.

> 네트워크에 붙어 있으면 믿는다 → 인증된 연결이면 믿는다 → 도메인이 서명하고 정렬되면 믿는다

오늘 자체 메일 서버를 세우는 일이 어려운 이유도 여기에 있다. 어려운 부분은 SMTP 구현이
아니다. `MAIL FROM`/`RCPT TO`/`DATA` 를 말하는 서버는 옛날에도 며칠이면 만들었다. 진짜
일은 SPF·DKIM·DMARC 를 정렬시키고, TLS 정책을 게시하고, 리포트를 읽고, 수신 측 사업자의
정책을 따라가는 쪽이다. **프로토콜을 구현하는 문제에서 평판과 정책 준수를 관리하는 문제로
바뀐 것이다.**

## 아직 안 풀린 것

**① 봉투와 헤더의 이중 발신자는 여전히 남아 있다.** SMTP 의 `MAIL FROM`(봉투)과 메시지
헤더의 `From:` 은 원래 다른 것이고, 지금도 다를 수 있다. DMARC 는 이 둘의 정렬을 *요구*해서
틈을 덮은 것이지 틈을 없앤 것이 아니다.[^rfc7489] 원설계는 그대로 살아 있다.

**② 그 정렬이 중계 경로를 깬다.** 메일링 리스트나 자동 포워딩은 메시지를 건드리거나 다른
IP 에서 재전송하기 때문에 SPF·DKIM 검증을 무너뜨린다. ARC(RFC 8617)가 인증 결과를 홉마다
봉인해 넘기려고 나온 이유가 이것이다.[^rfc8617] 다만 이건 원인을 없앤 게 아니라 결과를
전달하는 우회로이고, 2019년에 나온 그 문서는 지금도 **Experimental** 상태다.

**③ 표준과 현실의 시차.** DMARC 가 표준화 트랙에 오른 건 2026년이고, 그전 11년 동안 실제
운영 규칙을 정한 건 대형 수신 사업자들의 정책이었다. 프로토콜 문서만 읽고 메일 시스템을
설계하면 반드시 어긋나는 지점이 생긴다 — 그 간극은 문서로 확인할 수 있는 성격의 것이
아니어서, 이 글에서도 수치로 적지 않는다.

## References

- IETF/RFC Editor 1차 문서 (본문 각주에 개별 링크)
- Eric Allman, [*SENDMAIL — An Internetwork Mail Router*](https://docs-archive.freebsd.org/44doc/smm/09.sendmail/paper.pdf), BSD System Manager's Manual (SMM:9) — FreeBSD 문서 아카이브 소장본
- [*4.2BSD UNIX Programmer's Manual*](https://www.bitsavers.org/pdf/stanford/stanford_4.2_BSD_manual/4.2_BSD_Vol_2C.pdf) (bitsavers 스캔본)
- [The Postfix Home Page](https://www.postfix.org/), [qmail (D. J. Bernstein)](https://cr.yp.to/qmail.html), [Exim Internet Mailer](https://www.exim.org/) — 각 프로젝트 공식 사이트

[^rfc788]: RFC 788, *Simple Mail Transfer Protocol*, J. Postel, 1981년 11월 (RFC 780 폐기, RFC 821 로 폐기됨). <https://www.rfc-editor.org/info/rfc788>
[^rfc821]: RFC 821 (STD 10), *Simple Mail Transfer Protocol*, J. Postel, 1982년 8월. <https://www.rfc-editor.org/info/rfc821>
[^rfc974]: RFC 974, *Mail routing and the domain system*, C. Partridge, 1986년 1월. 현재 상태 HISTORIC. <https://www.rfc-editor.org/info/rfc974>
[^allman]: Eric Allman, *SENDMAIL — An Internetwork Mail Router*, §4.1 "Delivermail": "Sendmail is an outgrowth of delivermail. The primary differences are: (1) Configuration information is not compiled in." <https://docs-archive.freebsd.org/44doc/smm/09.sendmail/paper.pdf>
[^bsd42]: *4.2BSD UNIX Programmer's Manual*: "The delivermail program has been replaced by sendmail... and eliminates the compiled in configuration database previously used by delivermail."
[^rfc1135]: RFC 1135, *Helminthiasis of the Internet*, J. K. Reynolds, 1989년 12월. 1988년 11월 2일 저녁 사건에 대한 회고. <https://www.rfc-editor.org/info/rfc1135>
[^rfc1869]: RFC 1869 (STD 10), *SMTP Service Extensions*, 1995년 11월 (RFC 1651 폐기). <https://www.rfc-editor.org/info/rfc1869>
[^qmail]: D. J. Bernstein, *qmail: the Internet's MTA of choice* — "qmail security guarantee". <https://cr.yp.to/qmail.html>
[^postfix]: The Postfix Home Page: "Wietse Venema's mail server that started life at IBM research as an alternative to the widely-used Sendmail program." <https://www.postfix.org/>
[^exim]: Exim Internet Mailer: "originally developed at the University of Cambridge for use on Unix systems connected to the Internet... can be installed in place of Sendmail." <https://www.exim.org/>
[^rfc2476]: RFC 2476, *Message Submission*, 1998년 12월. <https://www.rfc-editor.org/info/rfc2476>
[^rfc6409]: RFC 6409 (STD 72), *Message Submission for Mail*, 2011년 11월 (RFC 4409 폐기): 릴레이는 계속 25번 포트, 제출은 통상 587번 포트. <https://www.rfc-editor.org/info/rfc6409>
[^rfc2487]: RFC 2487, *SMTP Service Extension for Secure SMTP over TLS*, 1999년 1월. <https://www.rfc-editor.org/info/rfc2487>
[^rfc3207]: RFC 3207, 2002년 2월 (RFC 2487 폐기). <https://www.rfc-editor.org/info/rfc3207>
[^rfc2505]: RFC 2505 (BCP 30), *Anti-Spam Recommendations for SMTP MTAs*, G. Lindberg, 1999년 2월. <https://www.rfc-editor.org/info/rfc2505>
[^rfc4954]: RFC 4954, *SMTP Service Extension for Authentication*, 2007년 7월 (RFC 2554 폐기). <https://www.rfc-editor.org/info/rfc4954>
[^rfc5321]: RFC 5321, *Simple Mail Transfer Protocol*, J. Klensin, 2008년 10월 (RFC 2821 폐기, RFC 1123 갱신). <https://www.rfc-editor.org/info/rfc5321>
[^rfc6531]: RFC 6531, *SMTP Extension for Internationalized Email*, 2012년 2월. <https://www.rfc-editor.org/info/rfc6531>
[^rfc6376]: RFC 6376 (STD 76), *DomainKeys Identified Mail (DKIM) Signatures*, 2011년 9월. <https://www.rfc-editor.org/info/rfc6376>
[^rfc7208]: RFC 7208, *Sender Policy Framework (SPF) ... Version 1*, S. Kitterman, 2014년 4월 (RFC 4408 폐기). <https://www.rfc-editor.org/info/rfc7208>
[^rfc7489]: RFC 7489, *DMARC*, 2015년 3월, Informational / Independent Submission. 현재 폐기됨. <https://www.rfc-editor.org/info/rfc7489>
[^rfc7672]: RFC 7672, *SMTP Security via Opportunistic DANE TLS*, 2015년 10월. <https://www.rfc-editor.org/info/rfc7672>
[^rfc8461]: RFC 8461, *SMTP MTA Strict Transport Security (MTA-STS)*, 2018년 9월. <https://www.rfc-editor.org/info/rfc8461>
[^rfc8314]: RFC 8314, *Cleartext Considered Obsolete: Use of TLS for Email Submission and Access*, 2018년 1월. <https://www.rfc-editor.org/info/rfc8314>
[^rfc8617]: RFC 8617, *The Authenticated Received Chain (ARC) Protocol*, 2019년 7월. <https://www.rfc-editor.org/info/rfc8617>
[^rfc9989]: RFC 9989, *DMARC*, T. Herr·J. Levine (Ed.), 2026년 5월 19일. Standards Track, RFC 7489·9091 폐기. <https://www.rfc-editor.org/info/rfc9989>
[^rfc9990]: RFC 9990, *DMARC Aggregate Reporting*, A. Brotman (Ed.), 2026년 5월 19일. Standards Track. <https://www.rfc-editor.org/info/rfc9990>
