---
layout: post
title: "쿠키·세션·토큰 — 셋은 같은 층위가 아니다: 운반·상태·자격증명으로 나눠 보기"
date: 2026-10-16 00:24:54 +0900
categories: [security, backend]
tags: [cookie, session, jwt, oauth2, bff, csrf, xss, spring-security]
---

"쿠키 vs 세션 vs 토큰" 이라는 질문은 자주 나오지만, 셋을 나란히 놓고 고르는 순간 설계가 꼬인다. **쿠키는 운반 수단**이고, **세션은 서버가 들고 있는 상태**이며, **토큰은 자격 증명의 형식**이다. 실제 시스템은 보통 "세션 ID 를 쿠키로 나른다" 거나 "토큰을 쿠키 또는 `Authorization` 헤더로 나른다" 처럼 둘 이상을 조합한다.

기초 개념(세션 방식과 JWT 방식의 차이)은 [CS300 #211 인증 — 세션과 토큰]({% post_url 2026-10-10-cs300-211-authentication-session-token %})에서 다뤘다. 이 글은 그 위에서 **각 층위에서 무엇을 정해야 하는지**를 RFC 와 OWASP 기준으로 정리한다.

## 한 줄 요약

| 층위 | 질문 | 대표 선택지 |
|---|---|---|
| 운반 (transport) | 자격 증명을 요청마다 어떻게 실어 보내나 | `Cookie` 헤더, `Authorization: Bearer` 헤더 |
| 상태 (state) | 로그인 상태를 누가 기억하나 | 서버 세션 저장소 / 토큰 자체에 담음 |
| 형식 (credential) | 자격 증명이 어떻게 생겼나 | 무작위 세션 ID, 불투명(opaque) 토큰, JWT |

이 세 질문에 따로 답하면 "쿠키냐 토큰이냐" 라는 잘못된 양자택일이 사라진다.

## 1. 쿠키 — 브라우저가 자동으로 붙여 보내는 운반 수단

쿠키는 [RFC 6265](https://www.rfc-editor.org/rfc/rfc6265)가 정의한 HTTP 상태 관리 메커니즘이다. 서버가 `Set-Cookie` 로 내려 주면 브라우저가 이후 조건에 맞는 요청마다 `Cookie` 헤더로 **자동으로** 붙인다. 이 "자동" 이 쿠키의 장점(클라이언트 코드가 필요 없음)이자 위험(CSRF)의 근원이다.

```http
Set-Cookie: __Host-SID=Hx9...; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=1800
```

| 속성 | 뜻 | 놓치면 |
|---|---|---|
| `Secure` | HTTPS 연결에서만 전송 | 평문 구간에서 탈취 |
| `HttpOnly` | JavaScript(`document.cookie`)에서 읽을 수 없음 | XSS 한 번으로 세션 ID 유출 |
| `SameSite` | 교차 사이트 요청에 실을지 결정 | CSRF 방어선 하나가 빠짐 |
| `Domain` | 생략하면 설정한 호스트에만 전송(host-only) | 넣으면 하위 도메인 전체로 퍼짐 |
| `Path` | 전송할 경로 범위 | 보안 경계로는 약하다 |
| `Max-Age`/`Expires` | 수명. 없으면 브라우저 세션 동안만 | 영구 쿠키로 남은 세션 ID |

**SameSite 의 세 값**은 개정 중인 쿠키 명세 [draft-ietf-httpbis-rfc6265bis](https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/)(2026-10 현재 Internet-Draft)에 이렇게 정의돼 있다.

- `Strict`: same-site 요청에만 보낸다.
- `Lax`: same-site 요청 + 교차 사이트의 **최상위 내비게이션**(링크를 눌러 이동 등)에 보낸다.
- `None`: 교차 사이트 요청에도 보낸다(`Secure` 필요).

같은 초안은 `SameSite` 값이 알 수 없는 값일 때 기본 강제 모드가 `Lax` 와 같다고 적고 있다. 다만 속성 자체를 생략했을 때 브라우저마다 기본 동작이 다를 수 있으니, **항상 명시**하는 편이 안전하다.

**쿠키 이름 접두사**도 같은 초안에 있다. 이름이 `__Host-` 로 시작하면 브라우저는 `Secure` 이고 `Path=/` 이며 `Domain` 이 **없는** 경우에만 그 쿠키를 받아들인다. 하위 도메인이 상위 도메인 세션 쿠키를 덮어쓰는 공격(세션 고정 변형)을 구조적으로 막는다. 세션 쿠키 이름은 `__Host-` 로 시작하게 만드는 것을 기본값으로 삼자.

**크기 한계**: RFC 6265 §6.1 은 브라우저가 최소한 쿠키 하나당 4096 바이트, 도메인당 50개를 지원해야 한다고 정한다. 그리고 "쿠키는 모든 요청에 실리므로 가능한 한 적고 작게 쓰라(SHOULD)" 고 덧붙인다. 큰 JWT 를 쿠키에 넣을 때 부딪히는 지점이다.

## 2. 세션 — 서버가 상태를 들고, 클라이언트는 열쇠만 든다

세션 방식에서 클라이언트가 가진 것은 **의미 없는 무작위 문자열(세션 ID)** 하나다. 사용자 정보와 권한은 서버(메모리, Redis, DB)에 있다.

[OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)의 핵심 요구사항은 다음과 같다.

- 세션 ID 는 **최소 64비트 엔트로피**를 가져야 하고, 암호학적으로 안전한 난수 생성기(CSPRNG)로 만든다.
- **권한 수준이 바뀌면(특히 로그인 직후) 세션 ID 를 새로 발급**한다. 그래야 세션 고정(session fixation) 공격이 막힌다.
- 유휴(idle) 만료와 절대(absolute) 만료를 둘 다 둔다.
- 로그아웃하면 서버 쪽 세션을 실제로 무효화한다(쿠키 삭제만으로는 부족).

Spring Security 는 세션 고정 방어가 기본으로 켜져 있다. Servlet 3.1 이상 컨테이너에서 기본 전략은 `changeSessionId` 로, 인증 시 컨테이너의 `HttpServletRequest#changeSessionId()` 로 ID 를 바꾼다 ([Spring Security — Session Management](https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html)). 쿠키 속성은 Spring Boot 설정으로 바로 잡을 수 있다 ([Spring Boot application properties](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)).

```yaml
server:
  servlet:
    session:
      timeout: 30m
      cookie:
        name: __Host-SID     # __Host- 규칙: Secure + Path=/ + Domain 없음
        secure: true
        http-only: true
        same-site: lax
        path: /
        # domain: 지정하지 않는다
```

**세션의 장점**은 통제다. 서버에서 지우면 그 순간 끝난다. 강제 로그아웃, 동시 로그인 제한, 권한 변경 즉시 반영이 쉽다. **비용**은 저장소다. 서버가 여러 대면 세션 저장소를 공유(예: Spring Session + Redis)하거나 고정 세션(sticky session)을 써야 한다.

## 3. 토큰 — 자격 증명 자체에 정보를 담거나, 담지 않거나

"토큰" 은 넓은 말이다. 두 종류를 구분하자.

| 종류 | 생김새 | 검증 방법 | 폐기 |
|---|---|---|---|
| 불투명(opaque) 토큰 | 무작위 문자열 | 발급자에게 조회(introspection) 또는 DB 조회 | 저장소에서 지우면 끝 — 사실상 세션과 같다 |
| 자체 포함(self-contained) 토큰, JWT | 헤더.페이로드.서명 | 서명 검증만으로 끝 | 만료 전에는 어렵다 |

### JWT 는 "암호화된 토큰" 이 아니다

[RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) 의 JWT 는 보통 **서명(JWS)** 만 된 형태로 쓴다. 페이로드는 base64url 인코딩일 뿐이라 누구나 읽을 수 있다. 내용을 숨겨야 하면 암호화 형식인 [JWE(RFC 7516)](https://www.rfc-editor.org/rfc/rfc7516)를 써야 한다. 그러니 JWT 페이로드에 개인정보나 내부 정보를 넣지 않는다.

JWT 를 검증하는 쪽이 반드시 지킬 것은 [RFC 8725 (JWT Best Current Practices)](https://www.rfc-editor.org/rfc/rfc8725)에 있다.

- **알고리즘을 검증한다(§3.1)**: 헤더의 `alg` 를 그대로 믿지 말고, 허용할 알고리즘을 서버가 정해 둔다. 공격자가 `alg` 를 `none` 으로 바꾸는 공격이 실제로 있었다.
- 발급자(`iss`)·주체(`sub`)를 검증하고(§3.8), 대상(`aud`)을 쓰고 검증한다(§3.9). 만료(`exp`)가 지난 토큰은 받지 않는다([RFC 7519 §4.1.4](https://www.rfc-editor.org/rfc/rfc7519)).
- 키에 맞는 알고리즘만 허용한다. RFC 8725 §2.1 은 `HS256` 헤더를 보고 RSA **공개키를 HMAC 비밀키로** 써서 검증해 버린 라이브러리 사례(CVE-2015-9235)를 든다.

### 폐기 문제와 그 해법

JWT 의 장점(조회 없이 검증)은 그대로 단점(만료 전에는 못 죽임)이 된다. 표준적인 해법은 이렇다.

1. **접근 토큰(access token)은 짧게** 발급한다. 탈취돼도 피해 시간이 짧다.
2. 수명이 긴 **갱신 토큰(refresh token)** 으로 새 접근 토큰을 받는다.
3. 갱신 토큰은 **회전(rotation)** 시킨다. [RFC 9700 (OAuth 2.0 Security BCP) §4.14](https://www.rfc-editor.org/rfc/rfc9700)에 따르면, 갱신할 때마다 새 갱신 토큰을 주고 이전 것은 무효화한다. 탈취된 토큰과 정상 토큰이 둘 다 쓰이면 한쪽은 무효화된 토큰을 내밀게 되고, 서버는 이를 침해 신호로 보고 활성 토큰을 폐기한다.
4. RFC 9700 은 **공개 클라이언트(브라우저 앱 등)의 갱신 토큰은 sender-constrained 이거나 회전을 써야 한다(MUST)** 고 정한다. sender-constrained 방식으로는 [DPoP(RFC 9449)](https://www.rfc-editor.org/rfc/rfc9449)와 [mTLS(RFC 8705)](https://www.rfc-editor.org/rfc/rfc8705)가 있다.
5. 로그아웃 시에는 [토큰 폐기 엔드포인트(RFC 7009)](https://www.rfc-editor.org/rfc/rfc7009)로 갱신 토큰을 폐기한다.

**갱신 토큰을 서버에 저장하고 회전·폐기하는 순간, 그 시스템은 다시 상태를 갖는다.** "JWT 라서 무상태" 라는 말은 접근 토큰 검증 경로에만 해당한다.

### Bearer 토큰은 URL 에 넣지 않는다

[RFC 6750](https://www.rfc-editor.org/rfc/rfc6750)은 토큰을 보내는 방법으로 `Authorization` 헤더, 폼 본문, URI 쿼리 파라미터 셋을 정의한다. 그런데 같은 문서 §5.3 은 "Bearer 토큰을 페이지 URL(예: 쿼리 문자열)로 전달하지 않아야 한다(SHOULD NOT)" 고 권고한다. URL 은 로그·브라우저 기록·Referer 로 새기 쉽다. 기본은 `Authorization: Bearer` 헤더다.

## 4. 브라우저에서 어디에 둘 것인가 — XSS 와 CSRF 의 교환

브라우저 앱에서 토큰을 어디 저장할지는 결국 **어떤 공격에 더 노출될지**를 고르는 문제다.

| 저장 위치 | XSS 로 탈취 | CSRF | 비고 |
|---|---|---|---|
| `localStorage` | **가능** — 같은 출처의 스크립트는 다 읽는다 | 자동 전송 안 되므로 해당 없음 | 탭 간 공유, 오래 남음 |
| `sessionStorage` | **가능** | 해당 없음 | 탭 수명, 탭 간 공유 안 함 |
| 메모리(JS 변수) | 실행 중엔 가능 | 해당 없음 | 새로고침하면 사라짐 |
| `HttpOnly` 쿠키 | **값을 읽을 수는 없음** | 자동 전송되므로 **대비 필요** | SameSite + CSRF 토큰 |

[RFC 10017 (OAuth 2.0 for Browser-Based Applications, 2026-08)](https://www.rfc-editor.org/rfc/rfc10017) §8 은 localStorage 가 같은 출처에서 실행되는 악성 JavaScript 를 막지 못한다고 명시한다. 그러나 `HttpOnly` 쿠키도 만능은 아니다. XSS 가 있으면 공격자는 값을 못 읽어도 **사용자 브라우저를 통해 요청을 대신 보낼 수 있다**(같은 문서 §5.1.4 "Proxying Requests via the User's Browser"). 결론은 저장 위치보다 **XSS 자체를 막는 것**이 먼저라는 점이다.

쿠키를 쓰면 CSRF 방어를 반드시 한다. [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)는 `SameSite` 를 "Defense In Depth Techniques" 항목에 둔다. 즉 주 방어가 아니라 **보조 방어**다(SameSite 만으로 충분할 수 있는 조건도 따로 설명한다). 상태를 바꾸는 요청에는 동기화 토큰(synchronizer token) 같은 주 방어를 함께 쓰는 것이 기본이다. Spring Security 는 POST 같은 안전하지 않은 메서드에 대해 CSRF 보호를 기본으로 켠다([Spring Security — CSRF](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)).

## 5. 권장 구조 — BFF: 토큰은 서버에, 브라우저에는 세션 쿠키만

RFC 10017 이 첫 번째로 제시하는 패턴이 **BFF(Backend for Frontend)** 다(§6.1).

```
브라우저 ──(HttpOnly 세션 쿠키)──> BFF ──(access token)──> API 서버
                                   │
                                   └─(code·refresh token)─> 인가 서버
```

- BFF 가 **기밀(confidential) 클라이언트**로서 인가 서버와 OAuth 흐름을 처리한다.
- 접근·갱신 토큰은 BFF 가 보관하고, 브라우저에는 **세션 쿠키만** 준다.
- 브라우저의 API 호출은 BFF 를 거치고, BFF 가 토큰을 붙여 전달한다.

같은 절(§6.1.3.2)의 쿠키 요구사항이 그대로 체크리스트가 된다.

- `Secure` 를 반드시 켠다(MUST).
- `HttpOnly` 를 반드시 켠다(MUST).
- `SameSite=Strict` 를 권장한다(SHOULD).
- `Path=/` 로 두고(SHOULD), `Domain` 은 지정하지 않는다(SHOULD NOT).
- HTTP 로 설정된 쿠키임을 나타내는 접두사를 쓴다(SHOULD). 문서는 `__Host-Http-` 를 예로 드는데, 이 접두사는 아직 초안인 [draft-ietf-httpbis-layered-cookies](https://datatracker.ietf.org/doc/draft-ietf-httpbis-layered-cookies/)에 정의돼 있다. 지원 여부를 확인하기 전에는 `__Host-` 를 쓰면 된다.

결국 브라우저 앱의 모범 답안은 "토큰 방식" 이 아니라 **"브라우저 구간은 세션, 서버 구간은 토큰"** 이다. 반대로 RFC 10017 §7 은 암묵적 승인(implicit grant)과 비밀번호 승인(ROPC)을 권장하지 않는 패턴으로 분류한다. RFC 9700 도 클라이언트는 implicit grant 를 쓰지 않아야 한다(SHOULD NOT)고 적는다.

## 6. 상황별 선택

| 상황 | 운반 | 상태 | 형식 |
|---|---|---|---|
| 서버 렌더링 웹(Spring MVC + Thymeleaf 등) | `HttpOnly` 쿠키 | 서버 세션 | 무작위 세션 ID |
| SPA + 자체 백엔드(같은 사이트) | `HttpOnly` 쿠키 | 서버 세션 | 무작위 세션 ID — 가장 단순하고 안전 |
| SPA + 외부 인가 서버(OAuth/OIDC) | 브라우저↔BFF 쿠키, BFF↔API Bearer | BFF 세션 + 인가 서버 | 세션 ID + 접근/갱신 토큰 |
| 모바일 앱 | `Authorization` 헤더 | 인가 서버 | 짧은 접근 토큰 + 회전하는 갱신 토큰 |
| 서비스 간(M2M) 호출 | `Authorization` 헤더 | 없음/인가 서버 | 클라이언트 자격증명으로 받은 접근 토큰, 가능하면 mTLS |

## 흔한 오해

- **"JWT 를 쓰면 세션이 필요 없다."** 접근 토큰 검증만 무상태다. 갱신 토큰 회전·폐기, 강제 로그아웃이 필요해지는 순간 서버 상태가 다시 생긴다.
- **"JWT 는 안전하게 암호화돼 있다."** 서명만 돼 있고 내용은 누구나 읽는다(JWS). 암호화는 JWE 다.
- **"HttpOnly 쿠키에 두면 XSS 는 끝."** 값 유출은 막지만, XSS 로 사용자 브라우저에서 요청을 대신 보내는 공격은 남는다.
- **"SameSite=Lax 면 CSRF 방어 끝."** OWASP 는 SameSite 를 보조 방어로 본다. 상태 변경 요청에는 CSRF 토큰을 함께 쓴다.
- **"로그아웃 = 쿠키 삭제."** 서버 세션 무효화와 갱신 토큰 폐기까지 해야 로그아웃이다.
- **"쿠키는 구식, 토큰이 최신."** RFC 10017 이 권하는 브라우저 앱 구조(BFF)의 브라우저 구간은 쿠키 세션이다.

## References

- IETF, [RFC 6265 — HTTP State Management Mechanism](https://www.rfc-editor.org/rfc/rfc6265) (2011)
- IETF, [draft-ietf-httpbis-rfc6265bis — Cookies: HTTP State Management Mechanism](https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/) (Internet-Draft)
- IETF, [draft-ietf-httpbis-layered-cookies](https://datatracker.ietf.org/doc/draft-ietf-httpbis-layered-cookies/) (Internet-Draft)
- IETF, [RFC 7519 — JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519)
- IETF, [RFC 7516 — JSON Web Encryption (JWE)](https://www.rfc-editor.org/rfc/rfc7516)
- IETF, [RFC 8725 — JSON Web Token Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725)
- IETF, [RFC 6749 — The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749)
- IETF, [RFC 6750 — OAuth 2.0 Bearer Token Usage](https://www.rfc-editor.org/rfc/rfc6750)
- IETF, [RFC 7009 — OAuth 2.0 Token Revocation](https://www.rfc-editor.org/rfc/rfc7009)
- IETF, [RFC 9700 — Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700)
- IETF, [RFC 9449 — OAuth 2.0 Demonstrating Proof of Possession (DPoP)](https://www.rfc-editor.org/rfc/rfc9449)
- IETF, [RFC 8705 — OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens](https://www.rfc-editor.org/rfc/rfc8705)
- IETF, [RFC 10017 — OAuth 2.0 for Browser-Based Applications](https://www.rfc-editor.org/rfc/rfc10017) (BCP 212, 2026-08)
- OWASP, [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- OWASP, [Cross-Site Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- Spring, [Spring Security — CSRF](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)
- Spring, [Spring Security — Session Management](https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html)
- Spring, [Spring Boot — Common Application Properties](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
