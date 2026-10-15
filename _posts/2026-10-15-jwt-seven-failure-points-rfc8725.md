---
layout: post
title: "JWT 가 실제로 뚫리는 7가지 자리 — RFC 8725 와 직접 돌려 본 위조 토큰"
date: 2026-10-15 21:32:23 +0900
categories: [Security, Backend]
tags: [JWT, 인증, RFC8725, OAuth, 보안, PyJWT, Spring]
---

JWT 를 "로그인하면 주는 토큰" 정도로만 알고 쓰면, 서명이 있으니 안전하다고 믿기 쉽다.
그런데 JWT 가 공개된 뒤 실제로 터진 사고는 대부분 **암호가 깨져서가 아니라 검증을 잘못해서** 났다.
IETF 는 그 사고들을 모아 2020년에 *JWT Best Current Practices* — [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725) (BCP 225) 를 냈다.
서론부터 이렇게 적는다.

> Since the JWT specification was published, there have been several widely published attacks on implementations and deployments. Such attacks are the result of under-specified security mechanisms, as well as incomplete implementations and incorrect usage by applications.

이 글은 RFC 8725 의 위협 목록을 뼈대로, **실제로 위조 토큰을 만들어 통과하는지** 직접 돌려 본 결과를 함께 적는다.
JWT 의 구조나 세션 방식과의 비교 같은 기초는 [이전 글 — 세션과 토큰]({{ site.baseurl }}/2026/10/10/cs300-211-authentication-session-token/) 에서 다뤘다.

> 실험 환경: Python 3.14.4, PyJWT 2.15.1, cryptography 50.0.2. 아래 출력은 전부 이 환경에서 실제로 나온 값이다.

## 0. 먼저 — JWT 는 암호화가 아니다

서명된 JWT(JWS, [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515)) 의 페이로드는 base64url 인코딩일 뿐이다. 키 없이 누구나 읽는다.

```text
[3] 페이로드는 암호화가 아니다 — 키 없이 읽힌다
   {'sub': 'alice', 'role': 'user', 'exp': 1792067827}
```

서명은 *변조* 를 막지 *열람* 을 막지 않는다. 주민번호·전화번호·내부 권한 구조 같은 것을 클레임에 넣으면 그대로 노출된다.
숨겨야 하면 JWE([RFC 7516](https://www.rfc-editor.org/rfc/rfc7516)) 를 쓰거나, 아예 넣지 않는다.

## 1. `alg: none` — 서명 없는 토큰을 받아 준다

RFC 8725 §2.1 의 첫 번째 위협이다. JWT 헤더에는 서명 알고리즘(`alg`)이 적혀 있고,
[RFC 7519 §6](https://www.rfc-editor.org/rfc/rfc7519#section-6) 은 서명 없는 "Unsecured JWT"(`alg: none`) 도 정의한다.
검증기가 **헤더에 적힌 alg 를 믿고** 그 알고리즘으로 검증하면, 공격자는 `alg` 를 `none` 으로 바꾸고 서명을 비운 채 아무 클레임이나 넣으면 된다.

## 2. 알고리즘 혼동 — RS256 공개키를 HMAC 비밀로

같은 절의 두 번째 위협이다. 서버가 RS256(비대칭) 으로 서명하고 공개키로 검증한다고 하자.
공격자가 헤더를 `HS256`(대칭) 으로 바꾸고, **누구나 구할 수 있는 그 공개키를 HMAC 비밀키로 삼아** 서명한다.
헤더의 alg 를 믿는 라이브러리는 "HS256 이니까 HMAC 으로, 키는 설정된 그 키로" 검증하고 — 통과시킨다.

이건 이론이 아니라 실제 CVE 다. Node.js `jsonwebtoken` 4.2.2 미만이 이 공격에 당했고
([CVE-2015-9235](https://nvd.nist.gov/vuln/detail/CVE-2015-9235), NVD CVSS 3.x 9.8 CRITICAL),
최초 보고는 Tim McLean 의 2015년 글이다([Auth0 블로그 게재본](https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/)).

### 직접 해 봤다

헤더의 alg 를 믿는 "순진한 검증기" 를 30줄로 만들고, `role: admin` 으로 바꾼 위조 토큰 두 개를 넣었다.
같은 토큰을 **허용 알고리즘을 고정한** PyJWT 에도 넣었다.

```python
# 순진한 검증기: 헤더의 alg 를 그대로 믿는다
alg = json.loads(ub64u(header))["alg"]
if alg == "none":  return payload                     # 서명 확인 안 함
if alg == "HS256": hmac(key, msg) == sig ...          # key = 서버가 가진 RSA 공개키 PEM
if alg == "RS256": rsa_verify(key, msg, sig) ...

# 공격 2 — 공개키 PEM 을 HMAC 비밀로 써서 서명
sig = hmac.new(pub_pem, f"{h}.{forged_payload}".encode(), hashlib.sha256).digest()

# 올바른 검증
jwt.decode(token, pub_pem, algorithms=["RS256"])
```

```text
[1] 순진한 검증기 (헤더 alg 신뢰)
  정상 토큰      : ACCEPT -> user
  alg=none 위조  : ACCEPT -> admin
  RS->HS 혼동 위조: ACCEPT -> admin
[2] PyJWT, algorithms=['RS256'] 고정
  정상 토큰      : ACCEPT -> user
  alg=none 위조  : REJECT (InvalidAlgorithmError: The specified alg value is not allowed)
  RS->HS 혼동 위조: REJECT (InvalidAlgorithmError: The specified alg value is not allowed)
```

두 위조 토큰 모두 순진한 검증기에서 **관리자 권한으로 통과**했고, 알고리즘을 고정하자 둘 다 막혔다.
RFC 8725 §3.1 이 바로 이것을 요구한다.

> Libraries MUST enable the caller to specify a supported set of algorithms and MUST NOT use any other algorithms when performing cryptographic operations. … Moreover, each key MUST be used with exactly one algorithm.

참고로 PyJWT 는 한 겹 더 막는다. 허용 목록에 `HS256` 과 `RS256` 을 같이 넣는 실수를 해도,
PEM 공개키가 HMAC 키로 들어오면 따로 거절한다.

```text
InvalidKeyError The specified key is an asymmetric key or x509 certificate and should not be used as an HMAC secret.
```

다만 이건 *이 라이브러리의* 방어다. 라이브러리마다 다르므로 거기에 기대지 말고, **알고리즘은 설정에서 하나로 고정**하는 것이 원칙이다.

## 3. 약한 HMAC 비밀키 — 토큰 하나로 오프라인 사전 공격

RFC 8725 §2.2. HS256 에 사람이 외울 수 있는 비밀을 쓰면, 공격자는 **토큰 하나만 손에 넣으면**
서버에 요청 한 번 안 보내고 오프라인으로 비밀을 맞춘다. 맞추면 모든 토큰을 위조할 수 있다.

`summer2026` 으로 서명한 토큰을, 흔한 단어 10개 × 연도 200개 = 2,000개 후보로 맞춰 봤다.

```text
[4] 약한 HS256 비밀 — 사전 공격
  후보 2000개 중 1327번째에서 발견: 'summer2026'  (5.4 ms)
```

노트북 한 대, 단일 스레드, 5ms 다. PyJWT 2.15.1 은 서명할 때부터 경고를 띄운다.

```text
InsecureKeyLengthWarning: The HMAC key is 10 bytes long, which is below the minimum
recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
```

[RFC 7518 §3.2](https://www.rfc-editor.org/rfc/rfc7518#section-3.2) 는 HS256 키가 해시 출력 크기(256비트) 이상이어야 한다고 규정한다.
비밀은 사람이 고르지 말고 CSPRNG 로 32바이트 이상 생성해서 시크릿 저장소에 둔다(RFC 8725 §3.5).

## 4. `aud`·`iss` 를 안 본다 — 다른 서비스용 토큰이 통한다

RFC 8725 §2.7 *Substitution Attacks*. 서비스 A 에 정상 발급된 토큰을, 같은 키(또는 같은 발급자)를 믿는 서비스 B 에 그대로 내미는 공격이다.
MSA 에서 여러 서비스가 키를 공유할 때 흔히 생긴다.

```text
[5] aud — 다른 서비스용 토큰
  B 가 audience 지정: REJECT (InvalidAudienceError: Audience doesn't match)
  B 가 aud 검증 끔   : ACCEPT -> {'sub': 'alice', 'aud': 'service-a'}
```

대책은 §3.8(*Validate Issuer and Subject*) · §3.9(*Use and Validate Audience*) — 발급자와 수신자를 **둘 다** 검증하는 것이다.
더 나아가 용도가 다른 JWT(ID 토큰과 액세스 토큰 등)가 서로 섞이지 않도록 §3.11 은 `typ` 헤더로 명시적 타입을 붙이라고 권한다.
OAuth 액세스 토큰용 표준 타입은 [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068) 의 `at+jwt` 다.

## 5. 검증을 "잠깐" 끈다

디버깅하다 넣은 옵션 하나가 그대로 배포되는 경우다. 서명 검증을 끄면 만료(`exp`)까지 같이 꺼진다.

```text
[6] exp — 만료 토큰
  기본 검증          : REJECT (ExpiredSignatureError: Signature has expired)
  verify_signature 끔: ACCEPT -> {'sub': 'alice', 'exp': 1792067517}
```

`decode` 와 `verify` 가 이름만으로 구분되지 않는 라이브러리도 많다. Java 의 `JWT.decode()`(검증 안 함) vs `verifier.verify()` 같은 식이다.
코드 리뷰에서 **"서명 검증 없이 클레임을 꺼내는 호출"** 을 grep 대상으로 정해 두면 좋다.
RFC 7519 §11.1 의 말 그대로다.

> The contents of a JWT cannot be relied upon in a trust decision unless its contents have been cryptographically secured and bound to the context necessary for the trust decision.

## 6. 헤더의 `kid`·`jku` 를 믿는다 — 인젝션과 SSRF

RFC 8725 §2.9 · §3.10. `kid`(key ID) 헤더로 DB·LDAP 에서 키를 조회하거나, `jku` 같은 URL 헤더로 키를 받아 오는 구현이 있다.
이 값은 **서명 검증 전에, 공격자가 마음대로 쓴 입력**이다.

- `kid` 를 그대로 SQL 에 넣으면 SQL 인젝션 (예: 공격자가 고른 값을 키로 반환하게 만들기)
- `kid` 를 파일 경로로 쓰면 경로 조작 (예: 내용이 뻔한 파일을 키로 지정)
- `jku`/`x5u` 를 따라가면 SSRF, 혹은 공격자 서버의 키로 검증

대책: `kid` 는 **미리 정해 둔 키 목록 안에서 찾는 식별자**로만 쓴다(화이트리스트 맵 조회).
원격 키셋(JWKS) URL 은 헤더에서 받지 말고 설정에 고정한다.

## 7. 탈취된 토큰을 끊을 수 없다 — 수명과 refresh 회전

이건 버그가 아니라 설계 특성이다. 서명만으로 검증하는 JWT 는 **서버가 상태를 안 갖는 대신, 발급한 토큰을 중간에 무효화하기 어렵다.**
로그아웃해도, 비밀번호를 바꿔도, `exp` 까지는 유효하다.

그래서 실무 패턴은 대개 이렇다.

1. **액세스 토큰은 짧게**(분 단위). 탈취돼도 피해 시간이 짧다.
2. **refresh 토큰은 서버가 상태를 갖는다.** OAuth 2.0 보안 BCP [RFC 9700 §4.14.2](https://www.rfc-editor.org/rfc/rfc9700#section-4.14.2) 는
   공개 클라이언트(브라우저·모바일)의 refresh 토큰에 대해 **sender-constrained** 이거나 **refresh token rotation** 중 하나를 쓰도록 MUST 로 요구한다.
3. **회전(rotation)** 은 refresh 할 때마다 새 refresh 토큰을 주고 이전 것을 무효화하되, 둘의 관계는 서버가 기억한다.
   탈취된 토큰을 공격자와 정상 사용자가 둘 다 쓰면 한쪽이 *이미 무효화된* 토큰을 내밀게 되고, 서버는 그걸 침해 신호로 보고 그 계열 전체를 폐기한다.
   (RFC 9700 은 서버가 *누가* 공격자인지는 모른다고 명시한다 — 그래서 정상 사용자도 다시 로그인해야 한다.)
4. 비밀번호 변경·로그아웃 같은 보안 이벤트 때 refresh 토큰을 자동 폐기할 수 있다(같은 절, MAY).

액세스 토큰까지 즉시 끊어야 하는 요건이 있다면 `jti` 블랙리스트나 토큰 인트로스펙션이 필요하다. 그 순간 "무상태" 의 이점은 일부 포기하는 셈이다.
**즉시 폐기가 핵심 요건이면, JWT 가 아니라 서버 세션이 더 맞는 도구일 수 있다.**

## 보관 위치 — 정답이 아니라 트레이드오프

| 위치 | XSS 로 탈취 | CSRF 위험 | 메모 |
| --- | --- | --- | --- |
| `localStorage` | 스크립트가 바로 읽음 | 자동 전송 안 됨 → 낮음 | XSS 한 번이면 토큰이 밖으로 나간다 |
| `HttpOnly` 쿠키 | 스크립트가 못 읽음 | 자동 전송 → 대책 필요 | `Secure`·`SameSite` 와 CSRF 토큰 병행 ([RFC 6265](https://www.rfc-editor.org/rfc/rfc6265)) |
| 메모리(JS 변수) | 페이지 안 스크립트는 접근 가능 | 낮음 | 새로고침 시 사라짐 → refresh 를 HttpOnly 쿠키로 두는 조합이 흔하다 |

`HttpOnly` 쿠키도 XSS 를 막아 주지는 않는다. 토큰을 *훔쳐 가지* 못할 뿐, 공격 스크립트가 그 페이지 안에서 사용자 대신 요청을 보내는 건 막지 못한다.
**보관 위치는 XSS 방어를 대신하지 못한다.**

## 체크리스트

| # | 확인할 것 | 근거 |
| --- | --- | --- |
| 1 | 허용 알고리즘을 **설정에서 하나로 고정**, 헤더 alg 를 믿지 않음 | RFC 8725 §3.1 · §3.2 |
| 2 | `none` 거절 | RFC 8725 §2.1 · §3.2 |
| 3 | 키 하나엔 알고리즘 하나 | RFC 8725 §3.1 |
| 4 | HS* 비밀은 CSPRNG 32바이트 이상, 혹은 비대칭(RS/ES/EdDSA) 사용 | RFC 8725 §3.5 · RFC 7518 §3.2 |
| 5 | `exp` · `nbf` 검증 (시계 오차 허용치는 짧게) | RFC 7519 §4.1.4–4.1.5 |
| 6 | `iss` · `aud` 검증 | RFC 8725 §3.8 · §3.9 |
| 7 | 용도별 `typ` 명시 (액세스 토큰은 `at+jwt`) | RFC 8725 §3.11 · RFC 9068 |
| 8 | `kid` 는 고정 키 목록 조회로만, JWKS URL 은 설정에 고정 | RFC 8725 §3.10 |
| 9 | 페이로드에 민감 정보 없음 | RFC 7515 (서명 ≠ 기밀성) |
| 10 | 짧은 액세스 토큰 + refresh 회전 또는 sender-constrained | RFC 9700 §4.14.2 |
| 11 | 서명 검증 없이 클레임을 꺼내는 호출이 운영 코드에 없음 | RFC 7519 §11.1 |
| 12 | 라이브러리 보안 업데이트 추적 | 아래 사례 |

12번이 따로 있는 이유: 위 원칙을 다 지켜도 **라이브러리나 런타임 자체가 서명을 잘못 검증하면** 소용없다.
2022년 Java 15~18 의 ECDSA 구현이 `r = s = 0` 인 서명을 유효하다고 받아들인 결함이 그 예다
([CVE-2022-21449](https://nvd.nist.gov/vuln/detail/CVE-2022-21449), 발견자 Neil Madden 의 [해설 "Psychic Signatures in Java"](https://neilmadden.blog/2022/04/19/psychic-signatures-in-java/)).
ES256 JWT 를 쓰던 Java 서비스는 애플리케이션 코드가 완벽해도 위조 서명을 통과시켰다. NVD 기준 영향 범위는 Oracle Java SE 17.0.2 · 18 등이다.

## 정리

JWT 사고의 공통점은 *토큰이 스스로 "나는 이렇게 검증하라" 고 말하게 둔 것* 이다 — 헤더의 `alg`, `kid`, `jku` 를 믿었다.
검증 규칙은 토큰이 아니라 **서버 설정이 정해야 한다.** RFC 8725 의 권고 대부분이 결국 그 한 문장으로 모인다.

## References

1. Sheffer, Y., Hardt, D., Jones, M. *JSON Web Token Best Current Practices.* RFC 8725 (BCP 225), IETF, 2020. <https://www.rfc-editor.org/rfc/rfc8725>
2. Jones, M., Bradley, J., Sakimura, N. *JSON Web Token (JWT).* RFC 7519, IETF, 2015. <https://www.rfc-editor.org/rfc/rfc7519>
3. *JSON Web Signature (JWS).* RFC 7515 · *JSON Web Encryption (JWE).* RFC 7516 · *JSON Web Algorithms (JWA).* RFC 7518, IETF, 2015. <https://www.rfc-editor.org/rfc/rfc7515> · <https://www.rfc-editor.org/rfc/rfc7516> · <https://www.rfc-editor.org/rfc/rfc7518>
4. Lodderstedt, T. et al. *Best Current Practice for OAuth 2.0 Security.* RFC 9700, IETF, 2025. <https://www.rfc-editor.org/rfc/rfc9700>
5. Bertocci, V. *JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens.* RFC 9068, IETF, 2021. <https://www.rfc-editor.org/rfc/rfc9068>
6. Barth, A. *HTTP State Management Mechanism.* RFC 6265, IETF, 2011. <https://www.rfc-editor.org/rfc/rfc6265>
7. NVD. *CVE-2015-9235* (jsonwebtoken < 4.2.2, 알고리즘 혼동). <https://nvd.nist.gov/vuln/detail/CVE-2015-9235>
8. McLean, T. *Critical vulnerabilities in JSON Web Token libraries.* 2015. <https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/>
9. NVD. *CVE-2022-21449* (Java ECDSA 서명 검증). <https://nvd.nist.gov/vuln/detail/CVE-2022-21449>
10. Madden, N. *CVE-2022-21449: Psychic Signatures in Java.* 2022. <https://neilmadden.blog/2022/04/19/psychic-signatures-in-java/>
11. PyJWT 공식 문서 (실험에 쓴 버전 2.15.1). <https://pyjwt.readthedocs.io/en/stable/>
