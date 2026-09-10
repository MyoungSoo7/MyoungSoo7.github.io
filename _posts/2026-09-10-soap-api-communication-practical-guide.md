---
layout: post
title: "SOAP API 통신 실전: 규격이 어디서 갈라지고 어디서 터지는가"
date: 2026-09-10 13:20:00 +0900
categories: [Engineering]
tags: [SOAP, WSDL, WS-Security, XML, Web Services, Integration, Java, JAX-WS]
---

SOAP를 새로 설계에 넣는 사람은 이제 거의 없다. 그런데 **연동 상대로는 계속 만난다.** 금융 결제망, 공공기관 대민 서비스, 통신사 개통 시스템, ERP·보험 코어 — 20년 넘게 돌아가는 시스템의 대외 창구는 여전히 WSDL 한 장으로 시작한다. 그리고 그 연동은 예상보다 훨씬 자주 실패한다.

이유는 "낡아서"가 아니다. **규격이 여러 겹으로 쪼개져 있고, 그중 현장에서 가장 많이 쓰이는 층이 하필 표준이 아니기 때문이다.** 이 글은 그 갈라지는 지점들을 규격 원문 기준으로 짚는다.

---

## 1. 먼저 알아야 할 불편한 사실 — 현업의 SOAP 1.1은 표준이 아니다

대부분의 연동 문서가 "SOAP 1.1 / WSDL 1.1"을 요구한다. 그런데 그 두 문서의 지위는 이렇다.

> This document is a NOTE made available by the W3C **for discussion only**. Publication of this Note by W3C indicates **no endorsement** by W3C or the W3C Team, or any W3C Members. W3C has had no editorial control over the preparation of this Note.
>
> — SOAP 1.1, W3C Note 08 May 2000[^1] / WSDL 1.1, W3C Note 15 March 2001[^2] (두 문서에 동일 문구)

즉 SOAP 1.1과 WSDL 1.1은 W3C **Note**(제출 문서)이지 Recommendation(권고안)이 아니다. 실제 W3C 표준은 SOAP 1.2이고, SOAP 1.2 Part 2는 스스로 이렇게 못 박는다.

> SOAP Version 1.2 supercedes all previous versions of SOAP, including SOAP Version 1.1.
>
> — SOAP Version 1.2 Part 2: Adjuncts (Second Edition), W3C Recommendation 27 April 2007[^3]

그런데 현장은 여전히 1.1이다. 이 괴리가 만들어낸 것이 **WS-I Basic Profile**이다. 표준이 아닌 문서 위에서 상호운용성을 확보하기 위해, 업계가 "이 중 이것만 쓰자"고 합의한 제약 프로파일이다.[^4]

실무적 결론 하나: **연동 규격서에 "SOAP 1.1"이라고만 적혀 있으면 아직 아무것도 정해진 게 없다.** 최소한 바인딩 스타일, SOAPAction 사용 여부, fault 시 HTTP 상태코드 세 가지를 추가로 물어야 한다. 아래가 그 이유다.

---

## 2. 메시지 구조 — Envelope / Header / Body / Fault

기본 뼈대는 단순하다.

```xml
<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">
  <env:Header>
    <t:Transaction xmlns:t="http://example.com/tx" env:mustUnderstand="true">
      TX-20260910-0001
    </t:Transaction>
  </env:Header>
  <env:Body>
    <m:GetBalance xmlns:m="http://example.com/acct">
      <m:accountNo>110-1234-5678</m:accountNo>
    </m:GetBalance>
  </env:Body>
</env:Envelope>
```

여기서 실무자가 놓치기 쉬운 건 **`mustUnderstand`의 강도**다. 이건 "가능하면 처리해 달라"가 아니다. SOAP 1.2 처리 모델은 이렇게 규정한다.

> If one or more of the SOAP header blocks identified in the preceding step are not understood by the node then generate a single SOAP fault with the Value of Code set to `env:MustUnderstand`. **If such a fault is generated, any further processing MUST NOT be done.**
>
> — SOAP 1.2 Part 1[^5]

즉 `mustUnderstand="true"`인 헤더를 상대가 모르면 **Body는 아예 읽히지 않는다.** 헤더 하나 잘못 붙였는데 "요청이 통째로 무시된다"는 증상이 나오는 게 이 조항 때문이다.

SOAP 1.2의 최상위 fault 코드는 다섯 개로 고정돼 있다 — `VersionMismatch`, `MustUnderstand`, `DataEncodingUnknown`, `Sender`, `Receiver`. 앞의 셋은 프로토콜 층의 실패고, 뒤의 둘이 각각 "네가 잘못 보냈다"와 "내가 처리하다 실패했다"이다. SOAP 1.1에서는 이 둘의 이름이 `Client` / `Server`였다. 이름만 바뀐 게 아니라 뒤에서 볼 HTTP 상태코드까지 갈린다.

---

## 3. 실무에서 터지는 다섯 자리

### ① 바인딩 스타일 — document/literal 외에는 고르지 마라

WSDL의 `soapbind:body`에는 `style`(document/rpc)과 `use`(literal/encoded) 두 축이 있고 조합은 넷이다. 결론부터 말하면 실무 정답은 **document/literal (wrapped)** 하나뿐이다. WS-I Basic Profile 1.1이 나머지를 잘라냈기 때문이다.

> The Profile prohibits the use of encodings, including the SOAP encoding.
> **R2706** A `wsdl:binding` in a DESCRIPTION MUST use the value of "literal" for the `use` attribute in all `soapbind:body`, `soapbind:fault`, `soapbind:header` and `soapbind:headerfault` elements.
>
> — WS-I Basic Profile 1.1[^4]

`rpc/encoded`가 왜 잘렸나. SOAP 1.1의 Section 5 인코딩은 객체 그래프(참조·순환·희소 배열)를 XML로 직렬화하는 자체 규칙인데, 그 결과물이 **XML Schema로 검증되지 않는다.** 스키마로 계약을 검증할 수 없다는 건 SOAP를 쓸 이유 절반을 버리는 것이다. 반면 document/literal은 Body의 자식이 XSD로 정의된 엘리먼트 하나이므로 스키마 검증이 그대로 성립한다.

같은 프로파일이 Body 자식 개수도 못 박는다 — **R9981: ENVELOPE MUST have exactly zero or one child elements of the `soap:Body`.** 파라미터 여러 개를 Body에 나란히 늘어놓는 WSDL을 받았다면 그건 이미 프로파일 위반이며, 상대 스택에 따라 파싱이 갈린다. "wrapped" 패턴(오퍼레이션 이름의 래퍼 엘리먼트 하나로 감싸기)이 사실상 강제되는 이유다.

### ② SOAPAction — 1.1과 1.2가 아예 다른 곳에 넣는다

**SOAP 1.1**은 HTTP 헤더로 보내며, 이건 필수다.

> An HTTP client MUST use this header field when issuing a SOAP HTTP Request.
>
> — SOAP 1.1 §6.1.1[^1]

값이 없어도 `SOAPAction: ""`처럼 **빈 문자열을 명시**해야 한다. 헤더 자체를 빼면 규격 위반이다. 또 1.1의 Content-Type은 `text/xml`이다.

**SOAP 1.2**는 이 헤더를 없애고, 미디어 타입 `application/soap+xml`의 `action` 파라미터로 옮겼다.[^3] 즉:

```http
# SOAP 1.1
POST /svc HTTP/1.1
Content-Type: text/xml; charset=utf-8
SOAPAction: "http://example.com/acct/GetBalance"

# SOAP 1.2
POST /svc HTTP/1.1
Content-Type: application/soap+xml; charset=utf-8; action="http://example.com/acct/GetBalance"
```

여기서 나오는 전형적 증상: 1.2 클라이언트가 1.1 서버를 때리면 서버가 라우팅할 오퍼레이션을 못 찾아 **500 또는 엉뚱한 오퍼레이션 실행**이 난다. 반대 방향은 `415 Unsupported Media Type`이 뜬다. 연동이 안 될 때 가장 먼저 볼 곳이 이 두 줄이다.

### ③ HTTP 상태코드 — SOAP fault는 200이 아니다 (그리고 버전마다 다르다)

이게 가장 많이 사고 나는 자리다.

**SOAP 1.1**은 모든 fault를 500으로 규정한다.

> In case of a SOAP error while processing the request, the SOAP HTTP server MUST issue an HTTP 500 "Internal Server Error" response and include a SOAP message in the response containing a SOAP Fault element.
>
> — SOAP 1.1 §6.2[^1]

**SOAP 1.2**는 fault 코드에 따라 갈린다.

| SOAP Fault | HTTP Status |
| --- | --- |
| `env:Sender` | **400** Bad request |
| `env:Receiver` | 500 Internal server error |
| `env:VersionMismatch` | 500 Internal server error |
| `env:MustUnderstand` | 500 Internal server error |
| `env:DataEncodingUnknown` | 500 Internal server error |

*— SOAP 1.2 Part 2, Table 20: SOAP Fault to HTTP Status Mapping[^3]*

여기서 파생되는 실무 사고가 셋이다.

1. **클라이언트가 fault를 못 읽는다.** HTTP 200만 성공으로 보고 그 외에는 본문을 버리는 클라이언트(특히 직접 만든 `RestTemplate`/`HttpClient` 래퍼)는, 서버가 친절하게 담아 보낸 `faultstring`과 `detail`을 통째로 날리고 "500 에러"라고만 로그를 남긴다. 정작 원인은 본문 안에 "계좌번호 형식 오류"라고 적혀 있다. **SOAP는 4xx/5xx 응답 본문을 반드시 파싱해야 하는 프로토콜이다.**
2. **중간 장비가 삼킨다.** WAF·API 게이트웨이·L7 로드밸런서 중에는 5xx 응답 본문을 에러 페이지로 갈아치우는 설정이 흔하다. 그러면 정상적인 비즈니스 거절(fault)이 클라이언트에 도달하지 못한다. SOAP 구간은 경로상 장비의 5xx 본문 보존 여부를 반드시 확인해야 한다.
3. **버전 간 400/500 불일치.** 1.2 서버가 입력 오류에 400을 주는데, 1.1 기준으로 짠 클라이언트가 "400은 내 요청이 깨진 것"으로 보고 재시도 없이 죽거나, 반대로 재시도 로직이 500을 일시 장애로 오인해 **비즈니스 거절을 무한 재시도**한다. 후자는 상대 시스템에 중복 거래를 만든다.

실무 규칙: **fault 코드가 `Sender`/`Client` 계열이면 재시도 금지, `Receiver`/`Server` 계열만 백오프 재시도.** HTTP 상태코드가 아니라 fault 코드로 판단해야 한다.

### ④ 보안 — TLS가 아니라 메시지 계층

SOAP의 보안 모델이 REST와 근본적으로 다른 지점이다. WS-Security(정식 명칭 *Web Services Security: SOAP Message Security*)는 OASIS 표준으로, 최신판은 **버전 1.1.1, OASIS Standard 18 May 2012**이다.[^6]

핵심은 서명·암호화가 **전송 구간이 아니라 메시지 자체**에 걸린다는 것이다. 그래서 가능해지는 것들:

- **부분 암호화**: Body의 계좌번호 필드만 암호화하고 나머지는 평문으로 둔다. 중간 라우팅 노드는 헤더를 보고 라우팅하되 민감 필드는 못 본다.
- **종단 간 무결성**: TLS는 홉 단위라 게이트웨이에서 한 번 풀린다. 메시지 서명은 중간에 몇 번을 거치든 최종 수신자가 원 발신자의 서명을 검증한다.
- **부인 방지**: 서명된 메시지 자체가 증거로 남는다.

금융·의료 연동에서 SOAP가 끈질기게 살아남은 이유가 대체로 이 세 줄이다. 그냥 TLS를 걸면 되는 요건이면 SOAP를 고를 이유가 별로 없다.

주의: WS-Security를 붙이면 **서명 대상 정규화(XML Canonicalization)**가 개입한다. 공백·네임스페이스 선언 위치·속성 순서가 달라져도 서명이 깨지므로, 중간에서 메시지를 "예쁘게" 재포맷하는 로깅 필터나 프록시가 하나라도 있으면 검증이 실패한다. 서명 검증 실패의 상당수는 암호 문제가 아니라 이 문제다.

### ⑤ 바이너리 — base64 인라인은 33% 팽창한다

XML 본문에 파일을 넣으려면 base64로 인코딩해야 하고, base64는 3바이트를 4문자로 바꾸므로 **크기가 약 4/3(≈33%) 늘어난다.** 10MB 첨부가 13.3MB가 되고, 파싱할 때는 그 전체가 문자열로 메모리에 올라온다.

해법이 **MTOM/XOP**다. W3C Recommendation(2005-01-25)으로, 바이너리를 XML 밖 MIME 파트로 빼고 본문에는 참조만 남긴다.[^7] 첨부가 있는 SOAP 연동을 설계한다면 처음부터 MTOM을 켜는 게 맞다. 나중에 켜면 WSDL과 클라이언트 스텁을 다시 만들어야 한다.

---

## 4. Java 진영의 함정 — JAX-WS는 이제 JDK에 없다

`wsimport`로 스텁 만들고 `@WebService` 붙이던 기억으로 접근하면 바로 막힌다. JDK 11에서 Java EE 모듈이 통째로 제거됐다.

> Remove the Java EE and CORBA modules from the Java SE Platform and the JDK. These modules were deprecated in Java SE 9 with the declared intent to remove them in a future release. … Since standalone versions of the Java EE technologies are readily available from third-party sites, such as Maven Central, there is no need for the Java SE Platform or the JDK to include them.
>
> — JEP 320: Remove the Java EE and CORBA Modules (Delivered, JDK 11)[^8]

여기 포함된 것이 JAX-WS(Java API for XML-Based Web Services)와 JAXB다. 지금은 **Jakarta XML Web Services**로 이관돼 별도 의존성으로 가져와야 하고,[^9] 패키지 네임스페이스도 `javax.*` → `jakarta.*`로 바뀌었다. 오래된 블로그 예제를 그대로 복붙하면 컴파일부터 안 된다.

Spring 진영에서는 `spring-ws`(Spring Web Services)의 `WebServiceTemplate`을 쓰는 쪽이 현실적이다. 계약 우선(contract-first)을 전제로 설계돼 있어 WSDL/XSD가 이미 확정된 대외 연동과 궁합이 맞는다.

---

## 5. 그래서 언제 SOAP인가

정직하게 정리하면 이렇다.

| 상황 | 판단 |
| --- | --- |
| 상대가 SOAP만 제공한다 | 선택지 없음 — 잘 붙이는 게 전부 |
| 계약을 **기계가 검증**해야 한다 (필드 타입·필수 여부·enum) | SOAP 유리 (WSDL + XSD) |
| 메시지 **부분 암호화**·종단 간 서명·부인 방지 | SOAP 유리 (WS-Security) |
| 여러 홉을 거치며 신뢰 경계가 바뀐다 | SOAP 유리 |
| 그 외 신규 설계 | REST 또는 gRPC |

"SOAP는 무겁고 REST는 가볍다"는 흔한 요약은 반쯤만 맞다. 무거운 건 XML 파싱 비용보다 **WS-\* 스택 전체를 켰을 때의 운영 복잡도**이고, 그 복잡도는 위 표의 2~4행 요건이 실제로 있을 때는 어차피 어딘가에서 직접 구현해야 하는 것들이다. OpenAPI + JWT + 애플리케이션 레벨 필드 암호화로 같은 요건을 다시 만들면, 검증받지 못한 자체 규격이 하나 더 생길 뿐이다.

---

## 6. 연동 착수 체크리스트

새 SOAP 연동을 받았을 때 규격서에서 확인할 것들.

1. **SOAP 버전** — 1.1인가 1.2인가. Content-Type과 SOAPAction 위치가 갈린다.
2. **바인딩 스타일** — WSDL에서 `soapbind:body`의 `use`가 `literal`인지 확인. `encoded`면 WS-I 위반이므로 상대 담당자에게 먼저 확인한다.
3. **Body 자식 개수** — 하나인지(wrapped). 여러 개면 스택별로 갈린다.
4. **fault 시 HTTP 상태코드** — 400인지 500인지. 그리고 경로상 장비가 그 본문을 보존하는지 실측한다.
5. **재시도 정책** — fault 코드 기준으로 `Sender`/`Client`는 재시도 금지로 분기한다.
6. **mustUnderstand 헤더 목록** — 보낼 것과 받을 것을 양쪽 다 확정한다.
7. **WS-Security 프로파일** — UsernameToken인지 X.509 서명인지, 서명 대상 요소와 정규화 알고리즘까지.
8. **첨부 방식** — base64 인라인인지 MTOM인지. 최대 크기와 타임아웃도 함께.
9. **타임아웃과 멱등성** — SOAP는 대개 동기 호출이고, 타임아웃 후 재시도가 중복 거래를 만든다. 상대가 거래 고유번호 기반 멱등성을 보장하는지 명시적으로 확인한다.

이 아홉 줄을 착수 전에 못 채우면, 그 항목들은 통합 테스트가 아니라 **운영에서** 하나씩 발견된다.

---

## References

[^1]: D. Box et al., "Simple Object Access Protocol (SOAP) 1.1," **W3C Note** 08 May 2000. Note는 Recommendation이 아니며 W3C의 승인을 의미하지 않는다고 문서 스스로 명시한다. SOAPAction 필수 규정은 §6.1.1, fault 시 HTTP 500 규정은 §6.2. <https://www.w3.org/TR/2000/NOTE-SOAP-20000508/>
[^2]: E. Christensen et al., "Web Services Description Language (WSDL) 1.1," **W3C Note** 15 March 2001. <https://www.w3.org/TR/2001/NOTE-wsdl-20010315>
[^3]: M. Gudgin et al., "SOAP Version 1.2 Part 2: Adjuncts (Second Edition)," **W3C Recommendation** 27 April 2007. SOAP 1.2가 1.1을 supersede한다는 선언, `application/soap+xml` 미디어 타입(부록 A), fault→HTTP 상태 매핑(§7.5, Table 20)이 여기 있다. <https://www.w3.org/TR/soap12-part2/>
[^4]: WS-I, "Basic Profile Version 1.1 (Final)," 2006-04-10. R2706(literal 강제), R9981(Body 자식 0 또는 1), R1000(Fault 구조 제한) 등. <http://www.ws-i.org/profiles/basicprofile-1.1.html>
[^5]: M. Gudgin et al., "SOAP Version 1.2 Part 1: Messaging Framework (Second Edition)," **W3C Recommendation** 27 April 2007. mustUnderstand 처리 규칙 및 fault 코드 5종 정의. <https://www.w3.org/TR/soap12-part1/>
[^6]: OASIS, "Web Services Security: SOAP Message Security Version 1.1.1," **OASIS Standard** 18 May 2012. <https://docs.oasis-open.org/wss-m/wss/v1.1.1/os/wss-SOAPMessageSecurity-v1.1.1-os.html>
[^7]: M. Gudgin, N. Mendelsohn, M. Nottingham, H. Ruellan, "SOAP Message Transmission Optimization Mechanism (MTOM)," **W3C Recommendation** 25 January 2005. <https://www.w3.org/TR/soap12-mtom/>
[^8]: L. Andersen, "JEP 320: Remove the Java EE and CORBA Modules," OpenJDK. Status: Closed/Delivered, Release 11. <https://openjdk.org/jeps/320>
[^9]: Eclipse Foundation, "Jakarta XML Web Services 4.0" 사양 페이지. <https://jakarta.ee/specifications/xml-web-services/4.0/>

*본문의 규격 인용문은 2026-09-10에 각 원문 URL에서 직접 확인한 것이다. base64의 4/3 팽창은 인코딩 정의에서 따라오는 산술이며 특정 구현의 측정값이 아니다. 체크리스트 9항목은 규격 조항에서 도출한 것으로, 특정 벤더 스택의 동작을 보장하지 않는다.*
