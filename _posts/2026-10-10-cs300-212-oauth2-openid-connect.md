---
layout: post
title: "[CS300 #212] OAuth 2.0 과 OpenID Connect — 비밀번호 대신 권한을 위임하기"
date: 2026-10-10 21:32:00 +0900
categories: [cs]
tags: [cs300, web, oauth2, openid-connect, pkce, security]
---

컴퓨터공학 300 주제 시리즈의 212번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

OAuth 2.0 은 사용자가 비밀번호를 넘기지 않고도 어떤 앱에 "내 자원에 대한 제한된 접근"을 위임하게 해 주는 **인가** 프레임워크이고, OpenID Connect 는 그 위에 ID 토큰을 얹어 "이 사용자가 누구인가"를 알려 주는 **인증** 계층이다.

## 왜 필요한가

어떤 일정 관리 앱이 내 구글 캘린더를 읽어야 한다고 하자. 가장 단순한 방법은 앱에 구글 비밀번호를 알려 주는 것이다. 그러면 다음 문제가 생긴다.

- 앱이 캘린더뿐 아니라 메일, 드라이브, 결제까지 모든 것에 접근할 수 있다.
- 앱 하나만 끊고 싶어도 비밀번호를 바꿔야 하고, 그러면 다른 모든 곳이 끊긴다.
- 앱 서버가 털리면 내 비밀번호가 그대로 유출된다.

OAuth 는 이를 "범위(scope)와 기한이 제한된 토큰"으로 바꾼다. 비밀번호는 인가 서버만 보고, 앱은 토큰만 받는다. 그리고 "구글로 로그인" 버튼처럼 로그인 자체를 외부에 맡기는 기능은 OAuth 만으로는 안전하게 만들 수 없어서 OpenID Connect 가 생겼다.

## 핵심 개념

### 네 가지 역할

RFC 6749 는 네 역할을 정의한다.

| 역할 | 예 |
|---|---|
| 자원 소유자(resource owner) | 사용자 본인 |
| 클라이언트(client) | 일정 관리 앱 |
| 인가 서버(authorization server) | 구글 계정 서버. 로그인·동의 화면, 토큰 발급 |
| 자원 서버(resource server) | 캘린더 API. 토큰을 받고 데이터를 준다 |

클라이언트는 두 종류로 나뉜다. 비밀(client secret)을 안전하게 보관할 수 있는 서버 앱은 **기밀 클라이언트**, 브라우저 SPA·모바일 앱처럼 코드가 사용자 손에 있어 비밀을 숨길 수 없는 것은 **공개 클라이언트**다.

### 인가 코드 흐름 + PKCE

현재 권장되는 기본 흐름이다.

```
 사용자 브라우저          클라이언트(앱)                 인가 서버                자원 서버
      │  "구글로 연결" 클릭     │                            │                        │
      │◀── 리다이렉트 ─────────│ verifier 생성, challenge 계산 │                        │
      │── GET /authorize?response_type=code&client_id&redirect_uri                    │
      │      &scope=calendar.read&state=..&code_challenge=..&code_challenge_method=S256 ─▶│
      │◀─────────────── 로그인·동의 화면 ────────────────────│                        │
      │── 302 redirect_uri?code=AUTH_CODE&state=.. ──▶ 앱     │                        │
      │                        │── POST /token (code, code_verifier, redirect_uri) ─▶│
      │                        │◀── access_token, refresh_token (+ id_token) ───────│
      │                        │── GET /calendar  Authorization: Bearer ... ─────────────────▶│
```

왜 한 번에 토큰을 주지 않고 코드를 거칠까. 브라우저 주소창과 리다이렉트는 히스토리, 로그, Referer 헤더 등으로 새기 쉽다. 그래서 그 경로로는 수명이 아주 짧은 일회용 **코드**만 보내고, 실제 토큰은 클라이언트가 인가 서버와 직접 통신하는 백채널에서 받는다.

그래도 코드가 가로채질 수 있다. 모바일에서 악성 앱이 같은 커스텀 URL 스킴을 등록해 리다이렉트를 가로채는 공격이 대표적이다. **PKCE**(RFC 7636)는 이를 막는다.

1. 클라이언트가 무작위 `code_verifier` 를 만들고, 그 SHA-256 해시를 base64url 로 인코딩한 `code_challenge` 만 인가 요청에 넣는다.
2. 인가 서버는 코드와 challenge 를 묶어 저장한다.
3. 토큰 교환 때 클라이언트가 원본 verifier 를 보내면, 서버가 해시해서 challenge 와 비교한다.

코드를 가로챈 공격자는 verifier 를 모르므로 토큰으로 바꿀 수 없다.

### 2025년 기준 보안 권고

OAuth 2.0 보안 모범 사례인 RFC 9700(2025년 1월)은 다음을 정했다.

- 공개 클라이언트는 PKCE 를 **반드시** 쓰고, 기밀 클라이언트에도 권장한다.
- 리다이렉트 URI 는 미리 등록한 값과 **정확한 문자열 일치**로 비교한다(네이티브 앱의 localhost 포트는 예외).
- 토큰을 인가 응답에 바로 싣는 암묵적 흐름(implicit)은 쓰지 않아야 한다(SHOULD NOT).
- 사용자 비밀번호를 클라이언트가 직접 받는 비밀번호 그랜트(resource owner password credentials)는 쓰면 **안 된다**(MUST NOT).

예전 글에서 "SPA 는 implicit 흐름"이라는 설명을 보면 지금은 낡은 조언이다.

### 그 밖의 그랜트

| 그랜트 | 용도 |
|---|---|
| 인가 코드 (+PKCE) | 사용자가 있는 모든 앱 |
| 클라이언트 자격 증명 | 사용자 없는 서버 간 호출 |
| 리프레시 토큰 | 액세스 토큰 만료 후 재발급 |
| 디바이스 인가(RFC 8628) | TV·CLI 처럼 입력이 불편한 기기 |

### OpenID Connect: 누가 로그인했는가

OAuth 액세스 토큰은 "이 토큰으로 무엇을 할 수 있는가"를 나타낼 뿐, 클라이언트에게 "사용자가 누구인가"를 알려 주도록 설계되지 않았다. 액세스 토큰 형식도 자원 서버와의 약속이라 클라이언트가 해석하면 안 된다. 그래서 OAuth 를 로그인 용도로 쓰면 "다른 앱용으로 발급된 토큰을 들고 와서 로그인"하는 식의 공격에 취약해진다.

OpenID Connect Core 1.0 은 다음을 더한다.

- `scope` 에 `openid` 를 넣으면 토큰 응답에 **ID 토큰**(JWT)이 함께 온다.
- ID 토큰에는 `iss`(발급자), `sub`(사용자 식별자), `aud`(이 토큰을 받을 클라이언트 ID), `exp`, `iat`, 그리고 요청 때 보낸 `nonce` 가 들어 있다.
- 클라이언트는 서명, `iss`, `aud` 가 자기 클라이언트 ID 인지, `exp`, `nonce` 를 반드시 검증한다.
- 추가 프로필은 UserInfo 엔드포인트에서 받는다.
- 인가 서버의 엔드포인트와 공개 키 위치는 Discovery 문서(`/.well-known/openid-configuration`)로 자동으로 알아낸다.

사용자를 식별할 때는 이메일이 아니라 `iss` + `sub` 조합을 키로 쓴다. 이메일은 바뀔 수 있고, 발급자마다 검증 수준이 다르다.

## 직접 해 보기

PKCE 계산과 인가 서버의 검증 로직을 파이썬으로 재현한다. 먼저 RFC 7636 부록 B 의 예시 값으로 S256 계산이 맞는지 확인한다.

```python
import base64, hashlib, secrets

def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

# RFC 7636 부록 B 의 예시 값으로 S256 계산을 먼저 확인
rfc_v = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
print("RFC 예시 일치:", b64url(hashlib.sha256(rfc_v.encode()).digest())
      == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")

# --- 클라이언트(앱): 인가 요청 전에 verifier 를 만들고 challenge 만 보낸다
verifier = b64url(secrets.token_bytes(32))          # 43자, RFC 7636 허용 범위 43~128
challenge = b64url(hashlib.sha256(verifier.encode()).digest())
state = secrets.token_urlsafe(16)
print("code_verifier :", verifier, len(verifier), "자")
print("code_challenge:", challenge)

# --- 인가 서버: 코드 발급 시 challenge 를 함께 저장
codes = {}
def authorize(client_id, redirect_uri, code_challenge, method="S256"):
    code = secrets.token_urlsafe(16)
    codes[code] = (client_id, redirect_uri, code_challenge)
    return code

def token(code, client_id, redirect_uri, code_verifier):
    entry = codes.pop(code, None)                    # 코드는 한 번만 쓴다
    if not entry:
        return "invalid_grant (없거나 이미 쓴 코드)"
    cid, ruri, chal = entry
    if (cid, ruri) != (client_id, redirect_uri):
        return "invalid_grant (클라이언트·리다이렉트 불일치)"
    if b64url(hashlib.sha256(code_verifier.encode()).digest()) != chal:
        return "invalid_grant (PKCE 검증 실패)"
    return {"access_token": secrets.token_urlsafe(24)[:12] + "...", "token_type": "Bearer", "expires_in": 600}

redirect = "https://app.example/cb"
code = authorize("app", redirect, challenge)
stolen = code
print("공격자가 가로챈 코드로 교환:", token(stolen, "app", redirect, "guess-" + "x" * 40))
code = authorize("app", redirect, challenge)
print("정상 앱이 verifier 로 교환  :", token(code, "app", redirect, verifier))
print("같은 코드 재사용            :", token(code, "app", redirect, verifier))
```

실행 결과(무작위 값은 실행마다 다르다):

```
RFC 예시 일치: True
code_verifier : tyv_s9GfAJJ5nkMe5Zqn1d1qjwMCLIHaGK4qx_ZL8dw 43 자
code_challenge: gBRlWSYmLQAgU9pL39Ds_HySIPEvEhSQYrd-KucvOGA
공격자가 가로챈 코드로 교환: invalid_grant (PKCE 검증 실패)
정상 앱이 verifier 로 교환  : {'access_token': 'z4ngPZyBmir9...', 'token_type': 'Bearer', 'expires_in': 600}
같은 코드 재사용            : invalid_grant (없거나 이미 쓴 코드)
```

코드를 가로챈 공격자는 verifier 를 몰라 실패했다. 이 실습의 서버는 실패한 시도에서도 코드를 소모하므로, 정상 흐름은 새 코드를 받아서 진행했다. 한 번 쓴 코드를 다시 쓰면 거절되는 것도 확인할 수 있다. RFC 6749 는 인가 코드를 한 번만 쓸 수 있게 하고, 재사용 시도가 있으면 그 코드로 발급된 토큰을 폐기하는 것이 좋다고 적고 있다.

## 현업에서는

- **직접 만들지 않는다**: 인가 서버는 Keycloak 같은 검증된 제품이나 클라우드 ID 서비스를 쓰고, 클라이언트도 공인된 라이브러리를 쓴다. 홈랩 k3s 에서도 여러 관리 화면(Grafana, Argo CD 등)을 하나의 OIDC 제공자에 붙이면 계정 관리를 한곳에서 한다.
- **scope 는 최소로**: "일단 다 달라"는 scope 는 동의 화면에서 사용자를 쫓아내고, 토큰이 유출됐을 때 피해를 키운다.
- **state 와 nonce**: `state` 는 인가 응답이 내가 시작한 요청에 대한 것인지 확인하는 CSRF 방어이고, `nonce` 는 ID 토큰 재사용을 막는다. 둘 다 빠뜨리기 쉬워 점검 항목에 넣는다.
- **SPA 의 토큰 보관**: 브라우저 앱이 액세스 토큰을 `localStorage` 에 두는 대신, 같은 도메인의 백엔드가 토큰을 들고 브라우저에는 세션 쿠키만 주는 BFF 패턴을 택하는 팀이 늘고 있다. 211번 주제의 보관 위치 논의와 같은 이유다.

## 확인 문제

1. OAuth 2.0 의 네 역할을 들고, 비밀번호를 보는 쪽은 어디인지 말하라.
2. 인가 코드 흐름이 리다이렉트로 토큰을 바로 주지 않고 코드를 거치는 이유는?
3. PKCE 에서 클라이언트가 인가 요청에 보내는 값과 토큰 요청에 보내는 값은 각각 무엇인가.
4. OAuth 액세스 토큰만으로 "로그인"을 구현하면 안 되는 이유와, OIDC 가 더하는 것은?
5. RFC 9700 이 사용을 금지(MUST NOT)한 그랜트는 무엇인가.

### 풀이

1. 자원 소유자, 클라이언트, 인가 서버, 자원 서버. 비밀번호는 인가 서버만 본다.
2. 브라우저 리다이렉트 경로는 히스토리·로그·Referer 로 새기 쉬우므로 짧은 일회용 코드만 보내고, 토큰은 백채널에서 클라이언트 인증·PKCE 검증을 거쳐 받기 위해서다.
3. 인가 요청에는 `code_challenge`(verifier 의 SHA-256 을 base64url 인코딩한 값)와 `code_challenge_method=S256`, 토큰 요청에는 원본 `code_verifier`.
4. 액세스 토큰은 자원 접근 권한을 나타낼 뿐 어느 클라이언트를 위해 누가 인증했는지 보장하지 않는다. OIDC 는 `aud`·`nonce` 등을 담은 서명된 ID 토큰과 그 검증 규칙을 더한다.
5. 자원 소유자 비밀번호 자격 증명(resource owner password credentials) 그랜트.

## 더 읽을거리 (References)

- RFC 6749, *The OAuth 2.0 Authorization Framework*: <https://www.rfc-editor.org/rfc/rfc6749>
- RFC 7636, *Proof Key for Code Exchange (PKCE)*: <https://www.rfc-editor.org/rfc/rfc7636>
- RFC 9700, *Best Current Practice for OAuth 2.0 Security*: <https://www.rfc-editor.org/rfc/rfc9700>
- OpenID Foundation, *OpenID Connect Core 1.0*: <https://openid.net/specs/openid-connect-core-1_0.html>
