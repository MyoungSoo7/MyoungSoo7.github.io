---
layout: post
title: "access token 과 refresh token — 왜 둘로 나누고, 회전은 어디서 깨지나 (직접 만든 토큰 서버로 7가지 시나리오)"
date: 2026-10-16 00:24:38 +0900
categories: [security]
tags: [oauth2, access-token, refresh-token, token-rotation, rfc9700, authentication, security]
---

> [어제 JWT 글](/2026/10/15/jwt-seven-failure-points-rfc8725/)의 7절이 "refresh 토큰은 회전시켜라"에서 멈췄다면, 이 글은 그 다음 이야기다.
> 회전을 **직접 구현해 보면** 어디서 정상 사용자가 튕겨 나가고, 어디서 공격자가 빠져나가는지를 표준 라이브러리만으로 만든 작은 토큰 서버로 돌려 봤다.
> 토큰 보관 위치(localStorage·HttpOnly 쿠키·메모리)는 어제 글의 표에서 다뤘으니 여기서는 반복하지 않는다.

## TL;DR

- **access token 은 짧게, 상태 없이.** 리소스 서버가 서명만 보고 통과시킨다. 그래서 빠르지만 중간에 끊기 어렵다.
- **refresh token 은 길게, 상태 있게.** 인가 서버만 받고, 서버가 기억하고, 언제든 끊을 수 있다.
- 공개 클라이언트(브라우저·모바일 앱)라면 OAuth 보안 BCP([RFC 9700 §4.14.2](https://www.rfc-editor.org/rfc/rfc9700#section-4.14.2))가 **sender-constrained 토큰이나 회전 중 하나를 MUST** 로 요구한다.
- 회전을 구현하며 실험에서 확인한 함정 네 가지:
  1. **탈취 탐지는 정상 사용자도 함께 로그아웃시킨다.** 서버는 누가 공격자인지 모른다.
  2. **여러 탭이 동시에 갱신하면** 재사용 탐지가 정상 사용자를 공격자로 오인한다.
  3. 그걸 막는 **유예 시간(grace)** 은 그 몇 초 동안 공격자에게도 똑같이 열린다.
  4. 회전을 **원자적으로 안 하면** 계열이 둘로 갈라지고, 재사용 탐지가 영영 안 걸린다.
- 로그아웃해도 이미 나간 access token 은 **exp 까지 살아 있다.** 즉시 끊으려면 상태 조회를 감수해야 한다.

---

## 1. 왜 토큰을 둘로 나누나

OAuth 2.0 원 사양은 refresh token 을 "access token 을 얻는 데 쓰는 자격 증명"으로 정의하고, 새 access token 은 원래보다 **짧은 수명과 더 적은 권한**으로 받을 수 있다고 설명한다([RFC 6749 §1.5](https://www.rfc-editor.org/rfc/rfc6749#section-1.5)).
보안 BCP 도 같은 이유를 든다. refresh token 이 있으니 인가 서버가 access token 을 짧은 수명·좁은 범위로 발급할 수 있고, 그래서 access token 이 새도 피해가 줄어든다([RFC 9700 §4.14](https://www.rfc-editor.org/rfc/rfc9700#section-4.14)).

둘의 성격을 나란히 놓으면 이렇다.

| | access token | refresh token |
|---|---|---|
| 누가 받나 | 리소스 서버 (API) — 매 요청마다 | 인가 서버 — 갱신할 때만 |
| 검증 방식 | 서명·만료만 보는 **무상태** 검증이 흔하다 | 서버 저장소를 **조회**한다 |
| 수명 | 분 단위 | 일~주 단위 |
| 새면 | exp 까지 쓰인다 | 계속 새 access token 을 찍어낼 수 있다 |
| 끊으려면 | 어렵다 (상태 조회를 추가해야 함) | 저장소에서 지우면 끝 |

핵심은 **자주 쓰이는 쪽은 빠르게(무상태), 강력한 쪽은 통제 가능하게(상태)** 나눈 것이다.
그래서 RFC 9700 은 refresh token 을 공격자에게 "매력적인 표적"이라고 부른다. 클라이언트에 허락된 권한 전체를 대표하고 특정 리소스에 묶여 있지도 않기 때문이다(§4.14.1).

## 2. 표준이 요구하는 것 — RFC 6749 와 RFC 9700

**RFC 6749 §6** (갱신 요청):
- 인가 서버는 새 refresh token 을 발급할 수 **있다(MAY)**. 그 경우 클라이언트는 옛 것을 **버려야 한다(MUST discard)**.
- 새로 발급하는 refresh token 의 scope 는 원래 것과 **같아야 한다(MUST be identical)**.

**RFC 9700 §4.14.2** (2025년 1월, OAuth 2.0 보안 BCP):
- refresh token 을 발급할지는 위험 평가로 정한다(MUST).
- 발급한다면 사용자가 동의한 scope 와 리소스 서버에 **묶어야 한다(MUST)**.
- **공개 클라이언트**에는 재사용 탐지를 위해 둘 중 하나를 **반드시(MUST)** 쓴다.
  - **sender-constrained refresh token**: 토큰을 특정 클라이언트 인스턴스에 암호학적으로 묶는다. mTLS([RFC 8705](https://www.rfc-editor.org/rfc/rfc8705))나 DPoP([RFC 9449](https://www.rfc-editor.org/rfc/rfc9449))를 쓴다.
  - **refresh token rotation**: 갱신할 때마다 새 refresh token 을 주고 옛 것은 무효화하되, **둘의 관계는 서버가 기억한다.**
- 비밀번호 변경·로그아웃 같은 보안 이벤트 때 refresh token 을 자동 폐기할 수 있다(MAY).
- 한동안 안 쓴(inactive) refresh token 은 **만료시켜야 한다(SHOULD)**.

폐기 엔드포인트([RFC 7009](https://www.rfc-editor.org/rfc/rfc7009))도 짚어 둘 만하다. refresh token 을 폐기할 때, 서버가 access token 폐기를 지원한다면 **같은 grant 에서 나온 access token 도 무효화해야 한다(SHOULD)**고 쓴다.

## 3. 실험 — 표준 라이브러리로 만든 토큰 서버

RFC 문장만으로는 "그래서 구현하면 뭐가 문제냐"가 안 보여서, 최소 구현을 만들어 시나리오를 돌렸다.

- **access token**: HMAC-SHA256 으로 서명한 JWT 모양 문자열(`sub`, `fam`, `exp`, `jti`). 기본 검증은 서명과 만료만 본다.
- **refresh token**: `secrets.token_urlsafe(32)` 무작위 문자열. 서버에는 **SHA-256 해시만** 저장한다. DB 가 새도 원문은 안 새게 하려는 것이다.
- 한 번의 로그인에서 이어진 refresh token 들은 **family(계열)** 로 묶는다. 이미 회전된 토큰이 다시 오면 계열 전체를 폐기한다.
- 정책: access 5분, 유휴 만료 14일, 절대 수명 30일. 유예 시간은 기본 0.
- 시간은 함수 인자로 주입해서 시나리오가 매번 똑같이 재현되게 했다. 동시성 시나리오만 실제 스레드 두 개로 돌렸다. 세 번 돌려서 출력이 바이트 단위로 같았다.

### 결과 한 장

```
1 정상 회전          | t=250 refresh                     | OK
                     | t=550 새 토큰으로 refresh          | OK
                     | 옛 access 토큰 t=310 검증          | expired
2 탈취(공격자 먼저)  | t=100 공격자 refresh               | OK
                     | t=250 사용자 refresh(옛 토큰)      | FAIL: refresh token reuse detected
                     | t=260 공격자가 받은 새 refresh     | FAIL: family revoked (reuse detected (presented by alice))
                     | 공격자 access t=260, 무상태 검증   | ok
                     | 공격자 access t=260, 계열 확인 검증 | family revoked (...)
3 탈취(사용자 먼저)  | t=250 사용자 refresh               | OK
                     | t=400 공격자 refresh(옛 토큰)      | FAIL: refresh token reuse detected
                     | t=550 사용자 다음 refresh          | FAIL: family revoked (reuse detected (presented by attacker))
4 동시 갱신 grace=0s | tabA                               | OK
                     | tabB (50ms 뒤 같은 토큰)           | FAIL: refresh token reuse detected
                     | t=600 다음 refresh                 | FAIL: family revoked (reuse detected (presented by tabB))
4 동시 갱신 grace=2s | tabA                               | OK
                     | tabB (50ms 뒤 같은 토큰)           | OK
                     | t=600 다음 refresh                 | OK
4b 원자성 없는 회전  | tabA                               | OK
                     | tabB (같은 토큰, DB 왕복 20ms 사이) | OK
                     | 살아 있는 refresh 토큰 수          | 2개 (계열이 둘로 갈라짐)
5 유예의 대가 2s     | t=300 사용자 refresh               | OK
                     | t=301.5 공격자 옛 토큰             | OK (사용자와 같은 새 토큰을 받음)
6 로그아웃 t=60      | refresh 시도 t=70                  | FAIL: family revoked (logout)
                     | access 무상태 검증 t=120           | ok
                     | access 계열 확인 검증 t=120        | family revoked (logout)
                     | access 무상태 검증 t=301           | expired
7 수명               | 매일 refresh, 29일째까지           | OK
                     | 31일째 refresh (절대 수명 30일)    | FAIL: absolute lifetime exceeded
                     | 15일 만에 처음 refresh (유휴 14일) | FAIL: idle timeout
```

이제 하나씩 읽어 본다.

## 4. 시나리오별로 읽기

### ② ③ 탈취 — 탐지는 되지만, 누가 공격자인지는 모른다

공격자가 먼저 쓰든(②) 사용자가 먼저 쓰든(③), 두 번째로 옛 토큰을 내민 쪽에서 재사용이 걸리고 **계열 전체가 폐기된다.**
②에서 공격자가 이미 받아 간 새 refresh token 도 함께 죽는다. 회전의 핵심 효과다.

하지만 ③을 보면 폐기 사유에 `presented by attacker` 가 찍혀 있어도 **정상 사용자도 함께 튕긴다.**
RFC 9700 이 정확히 이렇게 쓴다 — 서버는 누가 무효한 토큰을 냈는지 알 수 없고, 활성 토큰을 폐기해 공격을 멈추는 대가로 정상 클라이언트도 새로 인가를 받아야 한다.
→ **재사용 탐지는 "공격 차단 + 강제 재로그인"이 한 세트다.** 사용자에게 "보안상 다시 로그인해 주세요"를 보여 줄 UX 를 미리 준비해야 한다.

②의 마지막 두 줄도 중요하다. 계열이 폐기된 뒤에도 공격자가 들고 있는 **access token 은 무상태 검증으로는 여전히 `ok`** 다. exp 까지 몇 분은 쓸 수 있다. 이걸 막으려면 API 가 계열 폐기 여부를 한 번 조회해야 한다(6절에서 다시).

### ④ 동시 갱신 — 정상 사용자가 공격자로 오인된다

같은 refresh token 을 가진 탭 두 개가 거의 동시에 만료를 맞으면, 둘 다 갱신 요청을 보낸다.
첫 요청이 회전에 성공하는 순간 두 번째 요청은 **이미 회전된 토큰**을 낸 셈이 되고, 서버는 그걸 재사용으로 판정한다. 결과는 **정상 사용자 로그아웃**이다(grace=0s 줄).

해결은 두 갈래다.
- **클라이언트에서 갱신을 하나로 모은다.** 탭 사이에 잠금을 두거나(예: 한 탭만 갱신하고 나머지는 결과를 받아 씀), 진행 중인 갱신 요청을 공유한다. 서버 쪽 판단을 건드리지 않아 가장 깨끗하다.
- **서버에 짧은 유예 시간을 둔다.** 회전 직후 몇 초 안에 옛 토큰이 다시 오면, 재사용으로 보지 않고 **방금 발급한 것과 같은 응답**을 다시 준다(grace=2s 줄 — 두 탭이 같은 새 토큰을 받고, 다음 갱신도 정상).

### ⑤ 유예 시간의 대가

유예 시간은 RFC 9700 에 있는 장치가 아니라 **구현 쪽 타협**이다. 실험 ⑤가 그 대가를 보여 준다.
사용자가 t=300 에 갱신한 직후, 공격자가 t=301.5 에 훔친 옛 토큰을 내밀면 **유예 2초 안이라 그대로 통과하고, 사용자와 같은 새 토큰을 받는다.** 재사용 탐지도 안 걸린다.
→ 유예는 짧게(초 단위) 잡고, 가능하면 ④의 클라이언트 쪽 해결을 먼저 쓴다. 유예를 쓴다면 같은 클라이언트에서 온 요청인지(클라이언트 인증, 또는 DPoP 키) 같이 확인하는 게 안전하다.

### ④b 원자성 — 가장 조용한 구멍

회전은 "이 토큰이 아직 active 인가?"를 **읽고**, 맞으면 새 토큰을 만들고 옛 것을 rotated 로 **바꾸는** 동작이다.
이 사이에 DB 왕복이 있고 잠금이 없으면, 동시에 온 두 요청이 **둘 다 active 라고 읽고 둘 다 회전에 성공한다.**
실험에서는 20ms 왕복 사이에 두 번째 요청이 끼어들었고, 한 계열에 **살아 있는 refresh token 이 두 개**가 됐다.

이게 왜 위험하냐면, 두 가지가 각자 회전을 이어 가면 어느 쪽도 "이미 회전된 토큰"을 내밀 일이 없다. **재사용 탐지가 영영 안 걸린다.** 공격자와 사용자가 계열을 하나씩 나눠 갖고 평화롭게 공존하는 상태다.
→ 회전은 반드시 원자적으로 한다. 예: `UPDATE ... SET status='rotated' WHERE token_hash=? AND status='active'` 처럼 **조건부 갱신을 한 문장으로** 하고 영향받은 행이 1일 때만 새 토큰을 발급한다. 또는 행 잠금, 분산 락을 쓴다.

### ⑥ 로그아웃해도 access token 은 살아 있다

로그아웃(t=60)으로 계열을 폐기하면 refresh 는 즉시 막힌다. 하지만 **무상태 검증으로는 access token 이 t=120 에도 `ok`** 이고, exp(t=300)가 지나서야 `expired` 가 된다.

선택지는 이렇다.
- **수명을 짧게 두고 감수한다.** 대부분의 서비스가 이렇게 한다. 5분이면 5분짜리 위험이다.
- **API 에서 계열(또는 `jti`) 폐기 여부를 조회한다.** 실험의 "계열 확인 검증" 줄처럼 즉시 막힌다. 대신 매 요청 상태 조회가 생겨 무상태의 이점이 줄어든다. 캐시로 비용을 줄일 수 있다.
- **인트로스펙션**([RFC 7662](https://www.rfc-editor.org/rfc/rfc7662))으로 리소스 서버가 인가 서버에 토큰 상태를 묻는다. 불투명(opaque) access token 을 쓰는 구조에서 자연스럽다.

### ⑦ 유휴 만료와 절대 수명은 다른 문제를 막는다

- **유휴 만료**: 15일 동안 한 번도 안 쓴 토큰은 만료된다. 잊힌 기기, 버려진 브라우저에 남은 토큰을 정리한다. RFC 9700 이 SHOULD 로 권하는 부분이다.
- **절대 수명**: 매일 부지런히 갱신해도 로그인 후 30일이 지나면 끝난다. 회전만 있으면 토큰이 **영원히 연장**될 수 있는데, 그걸 끊는 장치다. 탈취된 계열이 탐지되지 않은 채(④b 같은 경우) 계속 사는 것도 결국 여기서 끊긴다.

## 5. 체크리스트

- [ ] access token 수명은 분 단위다. "즉시 끊어야 하는 요건"이 있다면 상태 조회(계열·`jti`·인트로스펙션)를 설계에 넣었다.
- [ ] refresh token 은 무작위 값이고, 서버에는 **해시**로 저장한다.
- [ ] 공개 클라이언트에는 **회전** 또는 **sender-constraining(DPoP·mTLS)** 중 하나를 쓴다 (RFC 9700 MUST).
- [ ] 회전은 **원자적**이다 (조건부 UPDATE 한 문장 / 행 잠금).
- [ ] 재사용이 탐지되면 **계열 전체**를 폐기하고, 사용자에게 재로그인 UX 를 보여 준다.
- [ ] 여러 탭·여러 요청의 **동시 갱신**을 클라이언트에서 하나로 모은다. 서버 유예 시간을 쓴다면 초 단위로 짧게 둔다.
- [ ] **유휴 만료 + 절대 수명**을 둘 다 둔다.
- [ ] 로그아웃·비밀번호 변경 때 refresh 계열을 폐기한다. 가능하면 같은 grant 의 access token 도 무효화한다 (RFC 7009 SHOULD).
- [ ] 새 refresh token 의 scope 는 원래와 같다 (RFC 6749 §6 MUST).

## 정리

refresh token 회전은 "토큰을 바꿔 준다"가 전부가 아니다. **관계를 기억하고, 재사용을 탐지하고, 원자적으로 바꾸고, 언젠가는 끝내는 것**까지가 한 묶음이다.
그리고 그 각각이 사용자 경험과 부딪힌다 — 재사용 탐지는 정상 사용자를 로그아웃시키고, 그걸 막는 유예는 공격자에게도 문을 연다.
정답이 하나인 문제가 아니니, 어떤 위험을 받아들이고 어떤 불편을 감수할지 **팀이 명시적으로 정해 두는 것**이 구현보다 먼저다.

## References

1. D. Hardt (Ed.), *RFC 6749: The OAuth 2.0 Authorization Framework*, 2012 — §1.5 Refresh Token, §6 Refreshing an Access Token. <https://www.rfc-editor.org/rfc/rfc6749>
2. T. Lodderstedt, J. Bradley, A. Labunets, D. Fett, *RFC 9700: Best Current Practice for OAuth 2.0 Security*, January 2025 — §4.14 Refresh Token Protection. <https://www.rfc-editor.org/rfc/rfc9700#section-4.14>
3. T. Lodderstedt (Ed.), S. Dronia, M. Scurtescu, *RFC 7009: OAuth 2.0 Token Revocation*, 2013. <https://www.rfc-editor.org/rfc/rfc7009>
4. J. Richer (Ed.), *RFC 7662: OAuth 2.0 Token Introspection*, 2015. <https://www.rfc-editor.org/rfc/rfc7662>
5. D. Fett, B. Campbell, J. Bradley, T. Lodderstedt, M. Jones, D. Waite, *RFC 9449: OAuth 2.0 Demonstrating Proof of Possession (DPoP)*, 2023. <https://www.rfc-editor.org/rfc/rfc9449>
6. B. Campbell, J. Bradley, N. Sakimura, T. Lodderstedt, *RFC 8705: OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens*, 2020. <https://www.rfc-editor.org/rfc/rfc8705>
7. 이 블로그, "JWT 가 실제로 뚫리는 7가지 자리 — RFC 8725 와 직접 돌려 본 위조 토큰", 2026-10-15. </2026/10/15/jwt-seven-failure-points-rfc8725/>
