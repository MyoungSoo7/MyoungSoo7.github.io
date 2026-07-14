---
layout: post
title: "포트를 하나도 열지 않고 홈랩을 공개하기 — Cloudflare로 보는 실전 보안"
date: 2026-07-14 23:00:00 +0900
categories: [security, cloud, infrastructure]
tags: [cloudflare, cloudflare-tunnel, zero-trust, waf, ddos, tls, dnssec, kubernetes, homelab, security]
---

집에 있는 K3s 클러스터를 인터넷에 공개하려면, 보통은 공유기에서 **포트 포워딩**을 열고 공인 IP를 DNS에 박는다. 그 순간부터 전 세계의 스캐너가 그 포트를 두드린다. 공인 IP가 유동이면 DDNS로 씨름해야 하고, origin IP가 노출되니 DDoS를 정면으로 맞는다.

나는 이 문제를 **포트를 단 하나도 열지 않고** 푼다. Cloudflare다. 이 글은 Cloudflare가 제공하는 보안 계층을, 내가 실제로 `lemuel.co.kr` 홈랩을 운영하는 방식에 근거해 정리한다.

> 핵심 전환: 방화벽에 구멍을 뚫어 **밖에서 안으로** 들어오게 하는 대신, 내부에서 Cloudflare로 **안에서 밖으로** 연결을 걸어 두고 그 위에 모든 트래픽을 태운다.

---

## 1. Cloudflare Tunnel — origin은 포트를 열지 않는다

핵심은 `cloudflared` 데몬이다. 클러스터 내부에서 `cloudflared`가 **아웃바운드로** Cloudflare 엣지에 지속 연결을 맺는다. 외부 사용자의 요청은 Cloudflare 엣지로 들어오고, 엣지가 이미 맺어진 그 터널을 통해 origin으로 되돌려 보낸다.

```
   사용자 ──HTTPS──▶ Cloudflare 엣지 ──(기존 아웃바운드 터널)──▶ cloudflared ──▶ K3s NodePort
                         │
                    WAF · DDoS · TLS · Bot · Rate limit
                    (모든 방어가 여기서 먼저 걸린다)

   ✦ 인바운드 포트 개방: 없음   ✦ 공인 IP DNS 노출: 없음
```

이 구조의 보안적 의미는 크다.

- **인바운드 포트 0개.** 공유기/방화벽에 열린 포트가 없으니, 포트 스캔·직접 공격의 표면 자체가 사라진다.
- **origin IP 은닉.** DNS에는 Cloudflare 엣지 IP만 보인다. 우리 집 공인 IP는 어디에도 안 뜬다 → DDoS가 origin을 직접 못 때린다.
- **유동 IP 무관.** 연결을 내부에서 걸므로 공인 IP가 바뀌어도 상관없다. DDNS 불필요.

내 셋업에서는 이 터널을 Cloudflare가 원격 관리(remote-managed)하고, 백엔드는 K3s **NodePort**로 지정한다. 새 서브도메인을 붙일 때 origin 쪽에 방화벽 규칙을 건드릴 일이 없다.

---

## 2. 앞단 방어 — DDoS · WAF · Rate Limiting · Bot

모든 트래픽이 엣지를 먼저 통과하므로, origin에 닿기 전에 방어가 걸린다.

- **DDoS 방어** — L3/L4 볼류메트릭 공격을 엣지에서 흡수한다. origin은 그 존재조차 모른다.
- **WAF(Web Application Firewall)** — OWASP 코어 룰셋 + 커스텀 룰. SQL 인젝션·XSS·경로 순회 같은 요청을 시그니처/휴리스틱으로 차단한다. "특정 국가만 허용", "이 경로는 특정 헤더 없으면 차단" 같은 규칙을 엣지에서 선언적으로 건다.
- **Rate Limiting** — `/login`, `/api/*` 같은 민감 경로에 "IP당 분당 N회" 제한. 크리덴셜 스터핑·브루트포스를 origin이 아니라 엣지에서 막는다.
- **Bot Management** — 스크래퍼·악성 봇을 지문으로 식별해 챌린지(Turnstile 등)로 거른다.

핵심은 **방어의 위치**다. 이 모든 게 우리 집 클러스터의 CPU를 쓰기 전에, Cloudflare의 전 세계 엣지에서 처리된다.

---

## 3. TLS/SSL — 종단 모드가 곧 보안 수준

Cloudflare를 앞단에 두면 TLS가 두 구간으로 나뉜다: **사용자↔엣지**, **엣지↔origin**. 이 두 번째 구간을 어떻게 설정하느냐가 함정이다.

| SSL 모드 | 엣지↔origin | 평가 |
|---|---|---|
| Off | 평문 | ✗ |
| Flexible | 평문 HTTP | ✗ 사용자에겐 자물쇠가 보이지만 origin 구간은 평문 |
| Full | HTTPS(인증서 검증 안 함) | △ 중간자 위험 |
| **Full (strict)** | HTTPS + 인증서 검증 | ✅ **정답** |

반드시 **Full (strict)** 를 써야 한다. Flexible은 브라우저에 자물쇠를 보여주면서 엣지-origin 구간은 평문이라, 보안을 *연출*할 뿐이다. Full(strict)에서는 origin에도 유효한 인증서(Cloudflare Origin CA 인증서로 충분)를 깔고 엣지가 그것을 검증한다.

---

## 4. Zero Trust Access — 내부 도구를 로그인 뒤로

홈랩엔 세상에 보이면 안 되는 것들이 있다 — ArgoCD, Grafana, Kibana, 각종 어드민. 이걸 공개 URL로 열되 **인증 없이는 못 들어오게** 하는 게 Cloudflare Access(Zero Trust)다.

- 애플리케이션 단위로 "Google/GitHub SSO로 인증된, 이 이메일 도메인만" 같은 정책을 건다.
- 인증은 **애플리케이션에 닿기 전, 엣지에서** 강제된다. 앱 자체에 로그인 기능이 없어도 그 앞에 인증 게이트가 생긴다.
- 세션·디바이스 posture·MFA를 조건으로 걸 수 있다.

즉 origin 앱을 고치지 않고도, "인터넷에 열려 있지만 나만 들어갈 수 있는" 상태를 만든다. VPN 없이 어디서든 접근하되, 신원은 매 요청 검증된다 — 이것이 "Zero Trust"의 실무적 형태다.

---

## 5. DNS 레이어 — DNSSEC와 프록시 레코드

- **Proxied 레코드(오렌지 클라우드)** — DNS 레코드를 Cloudflare 프록시로 태우면 응답에 엣지 IP만 나간다. origin IP 은닉의 출발점. (터널을 쓰면 이 은닉이 기본으로 강제된다.)
- **DNSSEC** — DNS 응답에 서명을 붙여 캐시 포이즌닝/스푸핑을 막는다. 도메인 등록기관에 DS 레코드만 등록하면 켜진다.
- **자동화 주의** — 서브도메인·터널 라우팅을 API로 관리한다면, 그 **API 토큰이 곧 도메인 전체의 열쇠**다. 나는 이 토큰을 평문으로 두지 않고 **SOPS로 암호화**해 GitOps 저장소에 넣는다. 최소 권한(특정 존의 DNS 편집만)으로 발급하는 것도 필수.

---

## 6. 놓치기 쉬운 함정

강력한 만큼, 잘못 쓰면 보안을 *연출만* 하게 된다.

1. **origin 직접 노출 금지.** Cloudflare를 앞에 두고도 origin IP가 어딘가(옛 A 레코드, 메일 서버, SSL 인증서 투명성 로그)로 새면 공격자는 엣지를 우회해 origin을 직접 때린다. 터널을 쓰면 애초에 열린 포트가 없어 이 우회가 원천 봉쇄된다 — 터널의 가장 큰 이점.
2. **Flexible SSL 금지.** 위에서 말한 그 함정.
3. **신뢰 경계 인식.** Cloudflare는 TLS를 종단한다 = 평문을 엣지가 본다. 규제 데이터라면 이 신뢰를 감안해야 한다.
4. **엣지를 믿고 origin 방어를 끄지 말 것.** WAF가 앞에 있어도 앱 자체의 인증/인가/입력검증은 그대로 필요하다. 다층 방어(defense in depth)지, 대체가 아니다.

---

## 7. 정리 — 내 홈랩에 적용된 형태

```
lemuel.co.kr (+ 서브도메인들)
   │  Proxied DNS (origin IP 은닉) + DNSSEC
   ▼
Cloudflare 엣지  ── DDoS · WAF · Rate limit · Bot · TLS(Full strict) · Access(Zero Trust)
   │  remote-managed Tunnel (인바운드 포트 0)
   ▼
K3s NodePort ──▶ 내부 서비스 (정산·커머스·ArgoCD·Grafana…)
   ※ API 토큰은 SOPS 암호화로 GitOps 저장
```

포트 포워딩 없이, 공인 IP 노출 없이, VPN 없이 — 그러면서도 DDoS·WAF·Zero Trust 인증까지. 홈랩 한 대를 안전하게 공개하는 가장 실용적인 답이 Cloudflare였다. 요점을 한 줄로 줄이면: **공격 표면을 줄이는 가장 좋은 방법은 방화벽에 규칙을 더하는 게 아니라, 애초에 열 포트를 없애는 것**이다.
