---
layout: post
title: "웹 보안 헤더 실전: 브라우저를 마지막 방어선으로 쓰는 법 (CSP·HSTS·frame-ancestors·COOP)"
date: 2026-09-24 19:40:00 +0900
categories: [Security]
tags: [Web Security, CSP, HSTS, XSS, Clickjacking, COOP, OWASP, HTTP Headers]
---

[시큐어코딩 글](/2026/09/10/secure-coding/)에서는 **서버 코드**에서 취약점을 막는 법을 다뤘다. 입력을 검증하고, 쿼리를 파라미터화하고, 출력을 인코딩한다. 그런데 코드는 언젠가 한 줄쯤 실수한다. 그때 공격을 **실행 단계에서** 막는 게 HTTP 응답 헤더다. 서버가 헤더로 "이 페이지에서는 이런 것만 허용한다"고 알리면, 실제 차단은 브라우저가 한다.

이 글은 그 헤더들을 "무엇을 막는가 → 어떻게 켜는가 → 어디서 사고가 나는가" 순서로 정리한다.

## TL;DR

| 위협 | 헤더 | 권장 값 (출발점) |
|---|---|---|
| XSS | `Content-Security-Policy` | nonce 기반 strict CSP + `'strict-dynamic'` |
| 다운그레이드·SSL 스트리핑 | `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| 클릭재킹 | CSP `frame-ancestors` (+ `X-Frame-Options`) | `frame-ancestors 'none'` 또는 `'self'` |
| MIME 스니핑 | `X-Content-Type-Options` | `nosniff` |
| URL 정보 유출 | `Referrer-Policy` | `strict-origin-when-cross-origin` |
| 교차 출처 창 조작, 사이드채널 | `Cross-Origin-Opener-Policy` | `same-origin` |
| 브라우저 기능 남용 | `Permissions-Policy` | 쓰지 않는 기능은 `()` 로 끈다 |
| (쓰지 말 것) | `X-XSS-Protection` | 보내지 않는다 |

이 헤더 목록은 OWASP 가 [Secure Headers Project(OSHP)](https://owasp.org/www-project-secure-headers/)로 따로 관리한다. 거기서도 목적을 "애플리케이션 보안을 높이는 데 쓸 수 있는 HTTP 응답 헤더를 설명"하는 것이라고 밝힌다.

---

## 1. 왜 지금 헤더인가: Top 10 1·2위가 '설정' 문제다

[OWASP Top 10:2025](https://top10.owasp.org/2025)에서 1위는 **A01 Broken Access Control**, 2위는 **A02 Security Misconfiguration**이다. Injection 은 2021년판 A03 에서 **A05** 로 내려갔다. 보안 헤더가 빠졌거나 잘못 걸린 상태는 A02 의 전형이고, 코드 한 줄 고치지 않고 인프라 설정만으로 개선할 수 있는 드문 영역이기도 하다.

---

## 2. CSP: XSS 를 '실행 단계'에서 끊는다

### 화이트리스트 CSP 는 대부분 뚫린다

예전 CSP 는 "스크립트는 이 도메인들에서만"이라고 적는 **호스트 화이트리스트** 방식이었다.

```
Content-Security-Policy: script-src 'self' https://cdn.example.com https://www.google-analytics.com
```

Google 연구진이 ACM CCS 2016 에 발표한 논문 [*CSP Is Dead, Long Live CSP!*](https://research.google/pubs/csp-is-dead-long-live-csp-on-the-insecurity-of-whitelists-and-the-future-of-content-security-policy/)(Weichselbaum, Spagnuolo, Lekies, Janc)은 1,680,867 개 호스트에서 수집한 26,011 개 고유 정책을 분석했다. 결과는 다음과 같다.

- 고유 정책의 **94.72%** 가 실제 배포 결함 때문에 우회 가능했다.
- 스크립트 로드에 가장 많이 허용된 도메인 15 개 중 14 개에 안전하지 않은 엔드포인트(JSONP, 구버전 AngularJS 등)가 있었다. 그 결과 고유 정책의 **75.81%** 가 공격자에게 우회를 허용하는 화이트리스트를 쓰고 있었다.

핵심은 이렇다. 허용한 CDN 에 공격자가 콜백 이름을 조종할 수 있는 JSONP 엔드포인트가 **하나라도** 있으면, 그 도메인 전체가 공격자의 스크립트 호스팅이 된다. 허용 목록이 길수록 이런 구멍도 많아진다.

### 대안: nonce 기반 strict CSP

도메인을 믿는 대신 **이번 응답에서 서버가 직접 넣은 스크립트만** 믿는다. [web.dev 의 Strict CSP 가이드](https://web.dev/articles/strict-csp)가 권장하는 형태는 이렇다.

```
Content-Security-Policy:
  script-src 'nonce-{RANDOM}' 'strict-dynamic';
  object-src 'none';
  base-uri 'none';
```

```html
<script nonce="{RANDOM}" src="/app.js"></script>
```

- `'nonce-{RANDOM}'`: 요청마다 새로 만든 예측 불가능한 값이다. 이 값을 가진 `<script>` 만 실행된다. 공격자가 HTML 에 태그를 끼워 넣어도 nonce 를 모르니 실행되지 않는다. **nonce 를 캐시된 HTML 에 박아 재사용하면 의미가 없다.**
- `'strict-dynamic'`: nonce 로 신뢰받은 스크립트가 동적으로 로드하는 스크립트에도 신뢰를 넘겨준다. 번들러·태그매니저와 함께 쓸 때 현실적인 선택이다.
- `object-src 'none'`: 플러그인 기반 실행 경로를 막는다.
- `base-uri 'none'`: `<base>` 태그를 주입해 상대 경로 스크립트를 공격자 서버로 돌리는 공격을 막는다.

정적 HTML 이라 요청마다 nonce 를 넣기 어렵다면, 같은 가이드의 **hash 기반** 변형(`'sha256-...'`)을 쓴다.

### 운영 적용은 Report-Only 부터

CSP 를 곧바로 강제하면 인라인 이벤트 핸들러(`onclick="..."`)나 서드파티 위젯이 한꺼번에 깨진다. [`Content-Security-Policy-Report-Only`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy-Report-Only)는 정책을 **강제하지 않고 위반만 보고**하는 헤더다. 적용 전에 위반을 확인하고 고칠 수 있다.

1. `Report-Only` 로 배포하고 위반 리포트를 모은다.
2. 인라인 핸들러를 `addEventListener` 로 옮기고, 남은 인라인 스크립트에 nonce 를 붙인다.
3. 리포트가 조용해지면 `Content-Security-Policy` 로 전환한다.

참고로 `Report-Only` 는 `<meta>` 태그로는 설정할 수 없다. 반드시 응답 헤더로 보내야 한다.

---

## 3. HSTS: 첫 요청 이후의 평문 HTTP 를 없앤다

사용자가 주소창에 `example.com` 만 치면 첫 요청은 HTTP 로 나간다. 서버가 HTTPS 로 리다이렉트하더라도 **그 첫 평문 구간**을 중간자가 가로챌 수 있다(SSL 스트리핑).

[RFC 6797](https://www.rfc-editor.org/rfc/rfc6797)의 HTTP Strict Transport Security 는 서버가 `Strict-Transport-Security` 응답 헤더로 "앞으로 `max-age` 초 동안은 이 호스트에 HTTPS 로만 접속하라"고 선언하는 방식이다.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

- `max-age` 는 필수, `includeSubDomains` 는 선택이다.
- HTTPS 응답에 실린 헤더만 유효하다. HTTP 응답에 넣은 HSTS 는 무시된다.
- **처음 한 번**은 여전히 보호받지 못한다. 이 구멍을 메우는 게 preload 다.

### preload: 되돌리기 어려운 결정

[hstspreload.org](https://hstspreload.org/)에 도메인을 등록하면 브라우저에 내장된 목록에 들어가 첫 요청부터 HTTPS 로 강제된다. 제출 요건은 다음과 같다.

- `max-age` 가 최소 `31536000` 초(1년)
- `includeSubDomains` 지정
- `preload` 지정
- 포트 80 을 열어 두었다면 같은 호스트에서 HTTP → HTTPS 로 리다이렉트
- 유효한 인증서, 모든 서브도메인의 HTTPS 서빙

`preload` 지시어는 RFC 6797 에 없다. 이 목록 운영 측의 규약이다. 그리고 해당 사이트는 현재 **"HSTS preloading 은 권장하지 않는다"** 고 직접 적고 있다. 목록에서 빠지는 데 오래 걸리고, HTTPS 가 안 되는 내부용 서브도메인이 하나라도 있으면 그 서비스가 통째로 막히기 때문이다. `includeSubDomains` 를 켜기 전에 **서브도메인 전수 조사**부터 한다.

권장 순서는 `max-age=300` 같은 짧은 값으로 시작해 문제가 없을 때 늘려 가는 것이다. 처음부터 1년을 걸면 실수를 1년 동안 되돌릴 수 없다.

---

## 4. 클릭재킹: frame-ancestors

공격자 페이지가 투명한 `<iframe>` 으로 내 사이트를 겹쳐 놓고 사용자의 클릭을 가로채는 공격이다.

```
Content-Security-Policy: frame-ancestors 'none';
X-Frame-Options: DENY
```

[MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options)은 `X-Frame-Options` 보다 세밀한 제어가 필요하면 CSP `frame-ancestors` 를 보라고 안내한다. 또 `X-Frame-Options` 의 `ALLOW-FROM` 값을 **obsolete** 로 표시하고 대신 `frame-ancestors` 를 쓰라고 한다. `X-Frame-Options` 자체는 HTML 표준에 여전히 정의되어 있으므로, 구형 클라이언트까지 고려해 **둘 다 보내는 것**이 무난하다. 특정 파트너 도메인에만 임베드를 허용해야 한다면 `frame-ancestors https://partner.example` 처럼 CSP 쪽에서 표현한다.

---

## 5. 보내지 말아야 할 헤더: X-XSS-Protection

오래된 보안 체크리스트에는 아직 `X-XSS-Protection: 1; mode=block` 이 남아 있다. [MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-XSS-Protection)은 이 헤더를 **Deprecated·Non-standard**("어떤 명세나 초안에도 속하지 않음")로 표시하고, 더 나아가 **"안전했던 웹사이트에 오히려 XSS 취약점을 만들 수 있다"** 고 경고한다. 권고 역시 XSS 필터 대신 CSP 를 쓰라는 것이다.

스캐너가 "X-XSS-Protection 누락"을 경고하면 헤더를 추가할 게 아니라 **스캐너 룰을 업데이트**한다.

---

## 6. 나머지 기본 세트

- **[`X-Content-Type-Options: nosniff`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Content-Type-Options)**: 브라우저가 `Content-Type` 을 무시하고 내용을 추측(MIME sniffing)하지 못하게 한다. 업로드된 "이미지"가 스크립트로 실행되는 경로를 막는다. 대신 서버가 `Content-Type` 을 정확히 보내야 한다.
- **[`Referrer-Policy`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy)**: 외부로 나가는 링크에 전체 URL(쿼리스트링의 토큰·검색어 포함)이 `Referer` 로 새지 않게 한다. `strict-origin-when-cross-origin` 이면 교차 출처에는 origin 만, HTTPS→HTTP 로는 아무것도 보내지 않는다. 최신 브라우저의 기본값이기도 하지만, 명시해 두면 구형 클라이언트와 의도 표현 면에서 낫다.
- **[`Cross-Origin-Opener-Policy: same-origin`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy)**: 문서를 같은 출처 문서만 있는 browsing context group 에 격리한다. `window.open` 으로 연 교차 출처 창이 `window.opener` 로 내 창을 조작하는 경로를 끊는다. 교차 출처 격리(cross-origin isolation)를 구성하는 한 축이기도 하다. OAuth·결제 팝업처럼 **opener 참조가 필요한 흐름은 깨질 수 있으니** 그 페이지는 `same-origin-allow-popups` 를 검토한다.
- **[`Permissions-Policy`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Permissions-Policy)**: 카메라·마이크·위치 같은 브라우저 기능을 페이지와 임베드된 iframe 에서 쓸 수 있는지 제한한다. 예: `Permissions-Policy: camera=(), microphone=(), geolocation=()`.

---

## 7. 어디에 거는가: 앱보다 엣지

헤더를 애플리케이션 코드마다 넣으면 서비스별로 설정이 어긋난다. 모든 응답이 지나가는 **리버스 프록시·Ingress·CDN 한 곳**에 기본 세트를 걸고, CSP 처럼 페이지마다 달라야 하는 것만 앱에서 내려보내는 구성이 관리하기 쉽다.

Nginx 예시:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# CSP 는 nonce 가 필요하므로 앱에서 응답마다 생성해 내려보낸다.
```

[Nginx 문서](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header)에 따르면 `add_header` 는 기본적으로 200·201·204·206·301·302·303·304·307·308 응답에만 붙는다. 에러 페이지에도 붙이려면 `always` 가 필요하다. 또 하위 블록(`location`)에 `add_header` 가 **하나라도** 있으면 상위 레벨의 `add_header` 는 상속되지 않는다. 특정 `location` 에서 헤더 하나를 추가했더니 나머지 보안 헤더가 전부 빠지는 사고가 흔한 이유다. (nginx 1.29.3 부터는 `add_header_inherit merge;` 로 상위 헤더를 합칠 수 있다. 기본값은 여전히 기존 동작이다.)

---

## 8. 체크리스트

- [ ] CSP 는 호스트 화이트리스트가 아니라 nonce/hash + `'strict-dynamic'` 이다
- [ ] nonce 는 요청마다 새로 생성되고, 캐시된 HTML 에 고정되지 않는다
- [ ] CSP 는 `Report-Only` 로 먼저 돌려 봤다
- [ ] HSTS 는 짧은 `max-age` 로 시작해 늘렸고, `includeSubDomains` 전에 서브도메인을 전수 조사했다
- [ ] preload 는 되돌리기 어렵다는 걸 알고 결정했다
- [ ] `frame-ancestors` 와 `X-Frame-Options` 를 함께 보낸다
- [ ] `X-XSS-Protection` 은 보내지 않는다
- [ ] `nosniff` 를 켰고 `Content-Type` 이 정확하다
- [ ] 헤더는 엣지 한 곳에서 관리하고, 에러 응답에도 붙는다(`always`)
- [ ] 결과를 실제 응답으로 확인한다: `curl -sI https://example.com`

마지막 항목이 가장 중요하다. 설정 파일에 적었다고 응답에 실린다는 보장은 없다. 앞에서 본 Nginx 상속 규칙 하나로도 조용히 빠진다. **응답 헤더를 직접 찍어 보기 전까지는 적용된 게 아니다.**

---

## References

1. OWASP, *Top 10:2025*. <https://top10.owasp.org/2025>
2. OWASP, *Secure Headers Project (OSHP)*. <https://owasp.org/www-project-secure-headers/>
3. L. Weichselbaum, M. Spagnuolo, S. Lekies, A. Janc, *CSP Is Dead, Long Live CSP! On the Insecurity of Whitelists and the Future of Content Security Policy*, ACM CCS 2016. <https://research.google/pubs/csp-is-dead-long-live-csp-on-the-insecurity-of-whitelists-and-the-future-of-content-security-policy/>
4. web.dev, *Mitigate cross-site scripting (XSS) with a strict Content Security Policy (CSP)*. <https://web.dev/articles/strict-csp>
5. MDN, *Content-Security-Policy-Report-Only*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy-Report-Only>
6. IETF, *RFC 6797 — HTTP Strict Transport Security (HSTS)*, 2012. <https://www.rfc-editor.org/rfc/rfc6797>
7. HSTS Preload List Submission. <https://hstspreload.org/>
8. MDN, *X-Frame-Options*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options>
9. MDN, *X-XSS-Protection*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-XSS-Protection>
10. MDN, *X-Content-Type-Options*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Content-Type-Options>
11. MDN, *Referrer-Policy*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy>
12. MDN, *Cross-Origin-Opener-Policy*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy>
13. MDN, *Permissions-Policy*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Permissions-Policy>
14. nginx, *Module ngx_http_headers_module — add_header*. <https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header>
