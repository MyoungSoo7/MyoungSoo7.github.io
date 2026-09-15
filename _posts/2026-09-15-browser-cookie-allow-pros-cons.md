---
layout: post
title: "브라우저에서 쿠키 허용, 좋은 점과 나쁜 점 — '쿠키'가 아니라 '누구의 쿠키냐'가 질문이다"
date: 2026-09-15 21:55:00 +0900
categories: [Engineering, Web]
tags: [쿠키, 브라우저, 프라이버시, 3rd-party-cookie, SameSite, 보안]
---

"쿠키를 허용하시겠습니까?" 앞에서 매번 멈칫한다면, 문제를 하나 정리하고 가자. **쿠키 허용/차단은 하나의 스위치가 아니다.** 쿠키에는 성격이 전혀 다른 두 종류가 있고, 좋은 점은 거의 전부 한쪽에서, 나쁜 점은 거의 전부 다른 쪽에서 나온다.

## 먼저 용어 — 1st-party 와 3rd-party

쿠키는 서버가 브라우저에 맡겨두는 작은 데이터 조각이다. HTTP 는 원래 상태가 없어서(stateless), 요청과 요청 사이에 "아까 그 사람" 임을 알 방법이 없다 — 쿠키가 그 연결고리다 ([MDN: HTTP 쿠키](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies), 동작 규격은 [RFC 6265](https://datatracker.ietf.org/doc/html/rfc6265)).

- **1st-party 쿠키**: 지금 주소창에 떠 있는 그 사이트가 심은 쿠키. 로그인 유지, 장바구니, 다크모드 설정이 여기 산다.
- **3rd-party 쿠키**: 그 페이지에 끼워진 **다른 도메인**(광고, 추적 스크립트, 소셜 위젯)이 심는 쿠키. 여러 사이트에 같은 제3자가 끼워져 있으면, 그 제3자는 당신이 어느 사이트들을 돌아다녔는지 이어붙일 수 있다 — 이것이 크로스사이트 추적이다 ([MDN: Third-party cookies](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies)).

## 허용했을 때 좋은 점

거의 전부 1st-party 쿠키의 공로다.

1. **로그인이 유지된다.** 쿠키 없이는 페이지를 넘길 때마다 다시 로그인해야 한다. 세션 쿠키가 "아까 인증한 그 브라우저" 임을 증명한다.
2. **장바구니·설정이 살아남는다.** 언어, 테마, 지역 설정, 결제 직전의 장바구니 — 전부 쿠키(또는 쿠키로 연결된 서버 세션)에 있다.
3. **보안 절차가 부드러워진다.** "이 기기 기억하기" 로 2단계 인증을 매번 반복하지 않는 것도 쿠키다.
4. **사이트가 애초에 동작한다.** 쿠키를 전부 차단하면 상당수 로그인 기반 서비스는 그냥 쓸 수 없다.

## 허용했을 때 나쁜 점

거의 전부 3rd-party 쿠키의 소행이다.

1. **사이트를 넘나드는 행동 추적.** 쇼핑몰에서 본 신발이 뉴스 사이트 광고로 따라오는 그 현상이다. 방문 이력이 제3자 서버에 프로필로 쌓인다 ([MDN 의 설명](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies)).
2. **프로필의 용도를 내가 통제할 수 없다.** 수집 주체가 광고 네트워크면 광고 타게팅에, 데이터 브로커면 판매에 쓰일 수 있다. 어디까지 가는지 사용자에겐 보이지 않는다.
3. **보안 공격면.** 세션 쿠키가 탈취되면(XSS 등) 비밀번호 없이도 계정이 넘어간다. 이건 허용/차단의 문제라기보다 사이트가 `HttpOnly`·`Secure`·`SameSite` 속성을 제대로 쓰느냐의 문제지만, 쿠키가 많을수록 면적은 넓어진다 ([MDN 보안 섹션](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies)).

## 브라우저들은 이미 결론을 냈다 — 단, 서로 다르게

"3rd-party 가 문제" 라는 진단에는 주요 브라우저가 대체로 동의한다. 대응은 갈렸다.

| 브라우저 | 3rd-party 쿠키 기본 정책 | 근거 |
| --- | --- | --- |
| Safari | ITP 로 크로스사이트 추적 쿠키 차단 | [WebKit 공식 블로그](https://webkit.org/blog/7675/intelligent-tracking-prevention/) |
| Firefox | Total Cookie Protection — 쿠키를 사이트별 칸막이에 격리 | [Mozilla 공식 문서](https://support.mozilla.org/en-US/kb/introducing-total-cookie-protection-standard-mode) |
| Chrome | 퇴출 계획을 철회하고 **사용자 선택**으로 유지 (2025-04 발표) | [Privacy Sandbox 공식 블로그](https://privacysandbox.google.com/blog/privacy-sandbox-next-steps) |

Chrome 공지의 핵심 문장은 이렇다: *"we've made the decision to maintain our current approach to offering users third-party cookie choice in Chrome"* — 즉 Safari·Firefox 는 기본 차단·격리, Chrome 은 기본 허용에 설정으로 선택권을 주는 구도다. 어느 브라우저를 쓰느냐에 따라 "쿠키 허용" 버튼의 실제 의미가 다르다는 뜻이기도 하다.

## 실용 결론 — 이렇게 정하면 된다

1. **1st-party 는 허용한다.** 로그인·장바구니·설정이 여기 달려 있고, 이걸 막으면 웹이 불편해지는 것에 비해 얻는 프라이버시 이득은 작다.
2. **3rd-party 는 차단하거나 격리한다.** Safari·Firefox 사용자는 이미 기본값이 그렇다. Chrome 사용자는 설정 → 개인 정보 보호 및 보안에서 서드파티 쿠키를 차단할 수 있다. 일부 사이트의 소셜 로그인·임베드가 깨질 수 있는데, 그 경우만 예외를 열어주면 된다.
3. **사이트의 쿠키 배너에서는 "필수만 허용"** 이 위 원칙의 근사치다. 필수 쿠키 ≈ 1st-party 기능성 쿠키, "마케팅/분석" ≈ 추적 쿠키인 경우가 대부분이다.

한 줄 요약: **"쿠키 허용?" 이라는 질문에 예/아니오로 답하지 말 것.** "내 쿠키(1st-party)는 예, 남의 쿠키(3rd-party)는 아니오" 가 비용 대비 가장 남는 답이다.

## References

- MDN — [Using HTTP cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies)
- MDN — [Third-party cookies](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies)
- IETF — [RFC 6265: HTTP State Management Mechanism](https://datatracker.ietf.org/doc/html/rfc6265)
- WebKit — [Intelligent Tracking Prevention](https://webkit.org/blog/7675/intelligent-tracking-prevention/)
- Mozilla — [Total Cookie Protection](https://support.mozilla.org/en-US/kb/introducing-total-cookie-protection-standard-mode)
- Google Privacy Sandbox — [Next steps for Privacy Sandbox and tracking protections in Chrome](https://privacysandbox.google.com/blog/privacy-sandbox-next-steps) (2025-04-22)
