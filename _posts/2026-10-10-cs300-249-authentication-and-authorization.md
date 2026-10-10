---
layout: post
title: "[CS300 #249] 인증과 인가 — 누구인가와 무엇을 해도 되는가는 다른 질문이다"
date: 2026-10-10 22:09:00 +0900
categories: [cs]
tags: [cs300, security, authentication, authorization, oauth]
---

컴퓨터공학 300 주제 시리즈의 249번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

인증(Authentication, AuthN)은 "당신이 주장하는 그 사람이 맞는가" 를 확인하고, 인가(Authorization, AuthZ)는 "그 사람이 이 자원에 이 행동을 해도 되는가" 를 판정한다. 둘을 섞으면 "로그인만 하면 다 된다" 는 구멍이 생긴다.

## 왜 필요한가

웹 서비스 보안 사고의 상당수는 암호가 깨져서가 아니라 이 두 단계 중 하나가 빠져서 일어난다. 로그인은 확인했는데 남의 주문서를 열 수 있었다(인가 누락). 관리자 메뉴를 화면에서 숨겼을 뿐 API 는 열려 있었다(인가를 UI 에 맡김). OAuth 로그인을 붙였는데 토큰이 어느 앱에 발급된 것인지 확인하지 않았다(인증 오용).

OWASP Top 10 의 2021년판과 2025년판 모두 1위가 "접근 통제 실패(Broken Access Control)" 다. 인증 실패도 꾸준히 목록에 있다. 이 두 개념을 정확히 나눠 쓰는 것이 웹 보안의 기초다.

## 핵심 개념

### 인증 요소

| 요소 | 예 | 약점 |
|---|---|---|
| 아는 것 | 비밀번호, PIN | 추측·재사용·피싱 |
| 가진 것 | OTP 앱, 보안 키, 휴대폰 | 분실, OTP 는 피싱으로 중계 가능 |
| 고유한 것 | 지문, 얼굴 | 바꿀 수 없음. 보통 기기 잠금 해제에 쓰고 서버로 보내지 않는다 |

다중 인증(MFA)은 **서로 다른 종류**의 요소를 둘 이상 쓰는 것이다. 비밀번호 두 개는 MFA 가 아니다.

TOTP(RFC 6238)는 공유 비밀과 현재 시각으로 6~8자리 코드를 만든다. 하지만 피싱 사이트가 사용자가 입력한 코드를 즉시 진짜 사이트로 중계하면 뚫린다. **WebAuthn/패스키**는 브라우저가 접속 중인 출처(origin)를 서명에 포함시키므로 가짜 도메인에서는 진짜 사이트용 서명이 나오지 않는다. 피싱 저항성이 있는 이유다.

### 인증 이후: 세션과 토큰

로그인에 성공하면 매 요청마다 비밀번호를 다시 받지 않고 **증표**를 쓴다.

| 방식 | 저장 위치 | 폐기 | 주의 |
|---|---|---|---|
| 서버 세션 + 쿠키 | 서버(DB, Redis), 쿠키엔 무작위 ID | 서버에서 즉시 삭제 | 쿠키 속성 HttpOnly·Secure·SameSite, 로그인 시 세션 ID 재발급 |
| 서명된 토큰(JWT 등) | 클라이언트 | 만료까지 유효(별도 차단 목록 필요) | 서명 알고리즘 고정, 짧은 만료, `aud`·`iss` 검증 |

JWT(RFC 7519)의 대표 함정은 RFC 8725 가 정리해 두었다. 헤더의 `alg` 를 믿고 검증 알고리즘을 고르면 `none` 이나 공개키를 HMAC 키로 쓰는 혼동 공격에 당한다. **검증 쪽이 허용 알고리즘을 고정**해야 한다.

### OAuth 2.0 과 OpenID Connect

자주 섞이는 둘이다.

- **OAuth 2.0**(RFC 6749)은 **인가 위임** 프로토콜이다. "이 앱이 내 캘린더를 읽어도 된다" 를 허락하고 앱은 액세스 토큰을 받는다. 액세스 토큰은 "누가 로그인했다" 를 증명하려고 만든 것이 아니다.
- **OpenID Connect**는 OAuth 2.0 위에 **인증 계층**을 올린 것이다. ID 토큰(서명된 JWT)에 사용자 식별자(`sub`), 발급자(`iss`), 대상 앱(`aud`), 만료 등을 담는다. "구글로 로그인" 은 OIDC 다.

브라우저 앱은 Authorization Code 흐름에 PKCE 를 붙여 쓰는 것이 현재 권장 방식이다. 토큰을 URL 조각으로 받는 Implicit 흐름은 피한다.

### 인가 모델

| 모델 | 판단 근거 | 예 |
|---|---|---|
| ACL | 자원마다 허용 주체 목록 | 파일 권한 |
| RBAC | 사용자 → 역할 → 권한 | 쿠버네티스 Role/RoleBinding |
| ABAC | 주체·자원·환경 속성의 규칙 | "같은 부서 문서는 근무 시간에만 읽기" (NIST SP 800-162) |
| ReBAC | 객체 간 관계 그래프 | "이 문서의 소유자의 팀원" |

어떤 모델이든 원칙은 같다.

1. **기본 거부**: 명시적으로 허용된 것만 된다.
2. **서버에서, 매 요청마다** 판정한다. UI 에서 버튼을 숨기는 건 인가가 아니다.
3. **최소 권한**: 필요한 만큼만 준다.
4. 기능 수준(이 API 를 부를 수 있나)과 **객체 수준(이 레코드에 손댈 수 있나)** 을 모두 본다. 객체 수준 누락이 IDOR 로, 별도 글에서 다룬다.

### 401 과 403

HTTP(RFC 9110)에서 **401 Unauthorized** 는 이름과 달리 "인증이 없거나 실패함" 이다. **403 Forbidden** 은 "누군지는 알지만 허락하지 않음" 이다. 상태 코드부터 두 개념이 갈린다.

## 직접 해 보기

RFC 6238 TOTP 를 표준 라이브러리로 구현해 RFC 부록의 테스트 벡터와 맞춰 보고, 기본 거부 RBAC 판정기를 만든다.

```python
import hmac, hashlib, struct

# 1) 인증: RFC 6238 TOTP
def hotp(key: bytes, counter: int, digits=6, algo=hashlib.sha1) -> str:
    mac = hmac.new(key, struct.pack(">Q", counter), algo).digest()
    off = mac[-1] & 0x0F                                   # 동적 절단(RFC 4226)
    code = struct.unpack(">I", mac[off:off+4])[0] & 0x7FFFFFFF
    return str(code % 10**digits).zfill(digits)

def totp(key: bytes, unix_time: int, step=30, digits=6) -> str:
    return hotp(key, unix_time // step, digits)

seed = b"12345678901234567890"                             # RFC 6238 부록 B 의 SHA1 시드
for t in (59, 1111111109, 1234567890):
    print(f"T={t:<11} TOTP(8자리) = {totp(seed, t, digits=8)}")

# 2) 인가: 역할 기반 + 기본 거부
ROLE_PERMS = {
    "viewer": {"invoice:read"},
    "accountant": {"invoice:read", "invoice:create"},
    "admin": {"invoice:read", "invoice:create", "invoice:delete", "user:manage"},
}
def authorize(user, action):
    if user is None:
        return 401                                        # 누군지 모른다
    perms = set().union(*(ROLE_PERMS.get(r, set()) for r in user["roles"]))
    return 200 if action in perms else 403                # 알지만 권한 없음

alice = {"id": 1, "roles": ["viewer"]}
bob = {"id": 2, "roles": ["accountant"]}
for who, user, act in [("익명", None, "invoice:read"), ("alice", alice, "invoice:read"),
                       ("alice", alice, "invoice:delete"), ("bob", bob, "invoice:create"),
                       ("bob", bob, "invoice:refund")]:
    print(f"{who:<6} {act:<15} -> {authorize(user, act)}")
```

실행 결과(Python 3.12):

```
T=59          TOTP(8자리) = 94287082
T=1111111109  TOTP(8자리) = 07081804
T=1234567890  TOTP(8자리) = 89005924
익명     invoice:read    -> 401
alice  invoice:read    -> 200
alice  invoice:delete  -> 403
bob    invoice:create  -> 200
bob    invoice:refund  -> 403
```

TOTP 세 값은 RFC 6238 부록 B 의 SHA1 테스트 벡터와 일치한다. `invoice:refund` 는 어떤 역할에도 정의되지 않았으므로 자동으로 거부된다. 새 기능을 추가하고 권한 정의를 깜빡해도 열리지 않는 것, 이것이 기본 거부의 가치다.

## 현업에서는

- **쿠버네티스는 둘을 명확히 나눈다**: API 서버는 요청을 받으면 인증(클라이언트 인증서, 서비스 어카운트 토큰, OIDC 등)으로 사용자를 정하고, 그다음 인가(보통 RBAC)로 동사·리소스·네임스페이스를 판정한다. 인증된 서비스 어카운트라도 Role 이 없으면 403 이다. 홈랩에서 `kubectl auth can-i --list --as=system:serviceaccount:ns:sa` 로 실제 권한을 확인하는 습관이 유용하다.
- **API 게이트웨이와 서비스의 분담**: 게이트웨이가 토큰 서명과 만료(인증)를 확인하고, 각 서비스가 객체 수준 인가를 한다. 게이트웨이를 통과했다는 이유로 서비스가 인가를 생략하면 내부망에서 직접 호출하는 경로로 우회된다.
- **세션 고정 방지**: 로그인 성공 시 세션 ID 를 새로 발급한다. 권한이 바뀌는 시점(관리자 모드 진입 등)에도 재발급한다.
- **로그인 실패 메시지**: "아이디가 없습니다" 와 "비밀번호가 틀렸습니다" 를 구분하면 계정 존재 여부가 샌다. OWASP 인증 치트시트는 일반적인 메시지를 권한다.

## 확인 문제

1. 인증과 인가를 한 문장씩으로 정의하라.
2. OAuth 2.0 액세스 토큰만 받고 "로그인 완료" 로 처리하면 무엇이 문제인가?
3. TOTP 와 WebAuthn 중 피싱에 강한 쪽은 무엇이고, 그 이유는?
4. 로그인은 했지만 권한이 없는 요청에 돌려줄 HTTP 상태 코드는?
5. JWT 검증 시 헤더의 `alg` 값을 따르면 안 되는 이유는?

### 풀이

1. 인증: 주체가 주장하는 신원이 맞는지 확인하는 것. 인가: 확인된 주체가 특정 자원에 특정 행동을 해도 되는지 판정하는 것.
2. 액세스 토큰은 인가 위임용이라 누가, 어느 앱을 위해 로그인했는지 보장하지 않는다. 다른 앱에 발급된 토큰을 들고 와도 구별하지 못할 수 있다. OIDC 의 ID 토큰과 `aud` 검증을 써야 한다.
3. WebAuthn. 서명에 접속 출처가 포함되어 가짜 도메인에서는 진짜 사이트용 응답을 만들 수 없다. TOTP 코드는 그대로 중계할 수 있다.
4. 403.
5. 공격자가 헤더를 조작해 `none` 이나 다른 알고리즘(공개키를 HMAC 키로 쓰는 혼동)을 지정할 수 있다. 검증자가 허용 알고리즘을 고정해야 한다.

## 더 읽을거리 (References)

- OWASP, [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) / [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- IETF, [RFC 6749: The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749) / OpenID Foundation, [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- IETF, [RFC 8725: JSON Web Token Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725)
- IETF, [RFC 6238: TOTP: Time-Based One-Time Password Algorithm](https://www.rfc-editor.org/rfc/rfc6238)
