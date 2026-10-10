---
layout: post
title: "[CS300 #211] 인증 — 세션과 토큰, 상태를 어디에 둘 것인가"
date: 2026-10-10 21:31:00 +0900
categories: [cs]
tags: [cs300, web, authentication, session, jwt, cookie]
---

컴퓨터공학 300 주제 시리즈의 211번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

HTTP 는 요청끼리 기억이 없으므로 로그인 상태를 이어 주는 장치가 필요하다. 세션 방식은 서버가 상태를 저장하고 클라이언트는 추측 불가능한 ID 만 들고 다니며, 토큰 방식은 서명된 토큰 안에 상태를 담아 서버가 저장 없이 검증한다. 둘의 차이는 결국 "취소를 어떻게 하느냐"로 모인다.

## 왜 필요한가

HTTP 는 무상태 프로토콜이다. 로그인 요청에서 비밀번호를 확인했더라도, 다음 요청에서 서버는 그 사실을 모른다. 그렇다고 매 요청마다 비밀번호를 보낼 수는 없다. 그래서 로그인에 성공하면 "이미 확인된 사람"임을 증명하는 무언가를 발급하고, 이후 요청마다 그것을 함께 보낸다.

여기서 설계 질문이 생긴다.

- 그 증표에 무엇을 담을까. 의미 없는 난수인가, 사용자 정보인가.
- 클라이언트는 그것을 어디에 보관할까. 쿠키인가, 자바스크립트 메모리인가.
- 비밀번호를 바꾸거나 기기를 잃어버렸을 때 기존 증표를 어떻게 무효로 만들까.

이 선택을 잘못하면 탈취된 토큰이 몇 주 동안 살아 있거나, 스크립트 주입 한 번으로 모든 사용자의 로그인이 새어 나간다.

## 핵심 개념

### 인증과 인가

먼저 용어를 구분한다. **인증(authentication)** 은 "너는 누구인가"를 확인하는 것이고, **인가(authorization)** 는 "너는 이것을 해도 되는가"를 판단하는 것이다. 이 글은 인증 상태를 유지하는 방법을 다룬다. 다른 서비스에 권한을 위임하는 문제는 다음 주제(OAuth 2.0)에서 다룬다.

### 세션 방식

```
1. POST /login (id, pw)          ──▶  확인 성공
                                  ◀──  Set-Cookie: sid=8f3a...; HttpOnly; Secure; SameSite=Lax
                                       서버 저장소: sid → {user: alice, exp: ...}
2. GET /orders  Cookie: sid=8f3a ──▶  저장소 조회 → alice
3. POST /logout                   ──▶  저장소에서 sid 삭제 → 즉시 무효
```

세션 ID 는 그 자체로 의미가 없는 난수다. OWASP 세션 관리 치트시트는 세션 ID 가 최소 64비트의 엔트로피를 가져야 한다고 권한다. 그리고 로그인 성공 직후 세션 ID 를 새로 발급해야 한다. 공격자가 미리 심어 둔 세션 ID 를 그대로 쓰게 만드는 세션 고정(session fixation) 공격을 막기 위해서다.

장점은 통제다. 서버에서 지우면 즉시 끝나고, "이 사용자의 모든 기기에서 로그아웃"도 간단하다. 단점은 저장소다. 서버가 여러 대면 모두가 같은 세션 저장소(Redis 등)를 봐야 한다.

### 토큰 방식 (JWT)

JWT(RFC 7519)는 `헤더.클레임.서명` 세 부분을 base64url 로 인코딩해 점으로 이은 문자열이다.

```
eyJhbGciOiJIUzI1NiJ9 . eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2MDE... . 6Gx0...
   헤더 {alg: HS256}       클레임 {sub: alice, exp: ...}            서명
```

| 클레임 | 뜻 |
|---|---|
| `iss` | 발급자 |
| `sub` | 주체(사용자 식별자) |
| `aud` | 대상(이 토큰을 받아야 할 서비스) |
| `exp` | 만료 시각 |
| `iat` | 발급 시각 |
| `jti` | 토큰 고유 ID |

서버는 저장소 조회 없이 서명과 `exp` 만 확인하면 된다. 서비스가 여러 개여도 키(또는 공개 키)만 나눠 가지면 각자 검증할 수 있다.

조심할 점도 분명하다.

- **암호화가 아니다**. 클레임은 base64 로 인코딩만 되어 있어 누구나 읽는다. 비밀 정보를 넣지 않는다.
- **취소가 어렵다**. 서명이 유효하고 만료 전이면 서버는 거절할 근거가 없다. 그래서 액세스 토큰은 수명을 짧게(수 분~수십 분) 잡고, 수명이 긴 리프레시 토큰은 서버가 저장·폐기할 수 있게 관리한다. 결국 일부 상태가 서버로 돌아온다.
- **알고리즘은 서버가 정한다**. 토큰 헤더의 `alg` 를 믿고 검증 방식을 고르면 `alg: none` 이나 알고리즘 바꿔치기 공격에 당한다. RFC 8725(JWT 모범 사례)는 허용할 알고리즘을 미리 정해 두고 그 외는 거부하라고 권한다.

### 어디에 보관하나

| 보관 위치 | XSS 로 탈취 | CSRF 위험 | 비고 |
|---|---|---|---|
| `HttpOnly` 쿠키 | 스크립트로 못 읽음 | 있음 → `SameSite`, CSRF 토큰 | 브라우저가 자동 전송 |
| `localStorage` | 스크립트로 읽힘 | 자동 전송 안 됨 | XSS 한 번이면 유출 |
| 자바스크립트 메모리 | 읽힘(실행 중에만) | 없음 | 새로 고침 시 사라짐 |

쿠키 속성은 RFC 6265 와 그 개정 초안이 정의한다. `HttpOnly` 는 스크립트 접근 차단, `Secure` 는 HTTPS 에서만 전송, `SameSite` 는 다른 사이트에서 시작된 요청에 쿠키를 붙일지 정한다. 브라우저 앱이라면 "HttpOnly·Secure·SameSite 쿠키에 세션 ID 또는 짧은 토큰"이 무난한 기본값이다. 모바일 앱이나 서버 간 호출처럼 쿠키가 자연스럽지 않은 곳에서는 `Authorization: Bearer` 헤더로 토큰을 보낸다.

### 비교 정리

| 항목 | 세션 | 토큰(JWT) |
|---|---|---|
| 서버 저장 | 필요 | 검증에는 불필요 |
| 즉시 무효화 | 쉬움 | 어려움 (짧은 수명 + 폐기 목록) |
| 여러 서비스 공유 | 공용 저장소 필요 | 키만 공유 |
| 크기 | 짧은 ID | 클레임만큼 커짐 |
| 내용 노출 | 없음 | 클레임이 보임 |

"JWT 가 더 현대적"이라는 이유만으로 고르지 않는다. 단일 웹 앱이면 세션이 더 단순하고 안전한 경우가 많다.

## 직접 해 보기

파이썬 표준 라이브러리로 세션과 HS256 JWT 를 직접 만들고, 변조·`alg: none`·만료가 어떻게 걸러지는지 본다. 교육용 코드이며, 실제 서비스에서는 검증된 라이브러리를 쓴다.

```python
import base64, hashlib, hmac, json, secrets, time

# --- 1) 세션: 서버가 상태를 갖는다 -------------------------------
sessions = {}                                   # 실제로는 Redis·DB

def login_session(user):
    sid = secrets.token_urlsafe(32)              # 256비트 난수, 추측 불가
    sessions[sid] = {"user": user, "exp": time.time() + 1800}
    return sid                                  # Set-Cookie: sid=...; HttpOnly; Secure

def check_session(sid):
    s = sessions.get(sid)
    return s["user"] if s and s["exp"] > time.time() else None

# --- 2) 토큰(JWT HS256): 서버는 키만 갖는다 ------------------------
KEY = secrets.token_bytes(32)
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
unb64 = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def issue_jwt(user, ttl=900):
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {"sub": user, "iat": int(time.time()), "exp": int(time.time()) + ttl}
    signing_input = b64(json.dumps(header).encode()) + "." + b64(json.dumps(claims).encode())
    sig = hmac.new(KEY, signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + b64(sig)

def verify_jwt(token):
    try:
        h, c, s = token.split(".")
    except ValueError:
        return None, "형식 오류"
    if json.loads(unb64(h)).get("alg") != "HS256":
        return None, "허용하지 않은 alg"            # alg 는 서버가 정한다
    expect = hmac.new(KEY, f"{h}.{c}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expect, unb64(s)):   # 상수 시간 비교
        return None, "서명 불일치"
    claims = json.loads(unb64(c))
    if claims["exp"] < time.time():
        return None, "만료"
    return claims["sub"], "OK"

sid = login_session("alice")
print("세션 확인:", check_session(sid))
del sessions[sid]                                # 로그아웃 = 서버에서 지우면 끝
print("세션 삭제 후:", check_session(sid))

tok = issue_jwt("alice")
print("JWT:", tok[:40] + "...")
print("검증:", verify_jwt(tok))
h, c, s = tok.split(".")
forged = json.loads(unb64(c)); forged["sub"] = "admin"
print("sub 변조:", verify_jwt(h + "." + b64(json.dumps(forged).encode()) + "." + s))
none_h = b64(json.dumps({"alg": "none"}).encode())
print("alg=none:", verify_jwt(none_h + "." + c + "."))
print("짧은 만료:", verify_jwt(issue_jwt("alice", ttl=-1)))
```

실행 결과(토큰 값은 실행마다 다르다):

```
세션 확인: alice
세션 삭제 후: None
JWT: eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9...
검증: ('alice', 'OK')
sub 변조: (None, '서명 불일치')
alg=none: (None, '허용하지 않은 alg')
짧은 만료: (None, '만료')
```

세션은 서버에서 지우는 순간 무효가 됐다. JWT 는 `sub` 를 `admin` 으로 바꾸자 서명이 맞지 않아 거부됐다. 서명 비교에 `hmac.compare_digest` 를 쓴 것은 바이트를 앞에서부터 비교하다 중간에 멈추는 일반 비교가 처리 시간 차이로 정보를 흘릴 수 있기 때문이다. 반대로 생각해 보자. 이 JWT 를 발급 직후 "로그아웃"시키려면 어떻게 해야 할까. 키를 바꾸면 모든 사용자가 로그아웃되고, 그 토큰만 막으려면 `jti` 폐기 목록을 서버에 저장해야 한다. 무상태의 대가다.

## 현업에서는

- **로그아웃이 안 되는 JWT**: "로그아웃했는데 다른 탭에서 계속 API 가 된다"는 신고는 액세스 토큰 수명이 길 때 생긴다. 수명을 줄이고, 리프레시 토큰은 회전(rotation)시키며 서버에서 폐기할 수 있게 한다.
- **쿠키 속성 점검**: 보안 점검에서 세션 쿠키에 `HttpOnly`, `Secure`, `SameSite` 가 빠졌다는 지적은 단골이다. 프레임워크 기본값을 믿지 말고 실제 응답의 `Set-Cookie` 를 확인한다.
- **여러 레플리카의 세션**: 홈랩 k3s 에 웹 앱을 레플리카 2개로 띄웠더니 새로 고침할 때마다 로그인이 풀린다면, 세션을 파드 메모리에 저장하고 있어서다. 세션 저장소를 외부(Redis 등)로 빼거나, 세션 어피니티는 임시방편으로만 쓴다.
- **로그에 토큰 남기지 않기**: 액세스 로그에 `Authorization` 헤더나 쿼리 문자열의 토큰이 찍히면 로그 열람 권한이 곧 로그인 권한이 된다. 로깅 미들웨어에서 마스킹한다.

## 확인 문제

1. 인증과 인가의 차이를 한 문장씩으로 설명하라.
2. 로그인 직후 세션 ID 를 다시 발급해야 하는 이유는?
3. JWT 의 클레임에 비밀번호 해시나 개인정보를 넣으면 안 되는 이유는?
4. JWT 를 즉시 무효화하기 어려운 이유와 현실적인 대응 두 가지를 들라.
5. `HttpOnly` 쿠키는 XSS 와 CSRF 중 무엇에 대한 방어이며, 다른 하나는 무엇으로 막는가.

### 풀이

1. 인증은 상대가 누구인지 확인하는 것, 인가는 그 상대가 특정 행동을 해도 되는지 판단하는 것이다.
2. 공격자가 미리 알고 있는 세션 ID 를 피해자가 로그인 후에도 쓰게 만드는 세션 고정 공격을 막기 위해서다.
3. JWT 는 서명만 되어 있고 암호화되지 않아 누구나 base64 디코딩으로 내용을 읽을 수 있다.
4. 서버가 상태를 저장하지 않으므로 서명이 유효하고 만료 전이면 거절할 근거가 없다. 액세스 토큰 수명을 짧게 하고 리프레시 토큰을 서버에서 관리·폐기하거나, `jti` 폐기 목록을 둔다.
5. `HttpOnly` 는 XSS 로 스크립트가 쿠키를 읽어 가는 것을 막는다. CSRF 는 `SameSite` 속성과 CSRF 토큰으로 막는다.

## 더 읽을거리 (References)

- RFC 7519, *JSON Web Token (JWT)*: <https://www.rfc-editor.org/rfc/rfc7519>
- RFC 8725, *JSON Web Token Best Current Practices*: <https://www.rfc-editor.org/rfc/rfc8725>
- RFC 6265, *HTTP State Management Mechanism*: <https://www.rfc-editor.org/rfc/rfc6265>
- OWASP, *Session Management Cheat Sheet*: <https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html>
