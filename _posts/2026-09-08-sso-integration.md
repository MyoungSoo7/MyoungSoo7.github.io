---
layout: post
title: "SSO 연동의 이해와 실전 설계: 인증·인가·세션을 분리하기"
date: 2026-09-08 01:14:05 +0900
categories: [Security]
tags: [SSO, OAuth2, OpenID Connect, OIDC, SAML, IAM, Security]
---

# SSO 연동이란 무엇인가

SSO(Single Sign-On)는 사용자가 여러 서비스마다 별도의 비밀번호를 반복해서 입력하지 않고, 하나의 신뢰된 인증 시스템을 통해 여러 애플리케이션에 로그인하는 구조다. 사용자는 한 번 로그인하지만, 각 애플리케이션은 자신의 세션·권한·토큰 정책을 별도로 관리한다.

SSO를 단순히 “로그인 버튼 하나를 공유하는 기능”으로 보면 설계가 위험해진다. 실제 연동에는 다음 질문이 포함된다.

- 누가 사용자의 신원을 인증하는가?
- 애플리케이션은 인증 결과를 어떻게 검증하는가?
- 로그인한 사용자의 권한은 어디서 결정하는가?
- access token과 ID token은 어떻게 구분하는가?
- 로그아웃과 세션 만료는 어떻게 전파하는가?
- 여러 서비스가 같은 사용자를 어떻게 식별하는가?

OpenID Connect(OIDC)는 OAuth 2.0 위에 인증 계층을 추가해 클라이언트가 인증된 최종 사용자의 신원을 검증하고 Claim을 받도록 하는 표준이다.[1] OAuth 2.0 자체는 제3자 애플리케이션이 제한된 범위의 HTTP 리소스 접근 권한을 받도록 하는 authorization framework이지, 로그인 프로토콜 그 자체는 아니다.[2]

## 1. SSO의 기본 구성요소

```text
사용자
  │
  ▼
애플리케이션(Client / Relying Party)
  │  authorization request
  ▼
Identity Provider / Authorization Server
  │  사용자 인증·동의
  ▼
Authorization Code
  │
  ▼
Token Endpoint
  │
  ├─ ID Token: 사용자 인증 결과
  └─ Access Token: API 접근 권한
```

주요 역할은 다음과 같다.

- **사용자(Resource Owner)**: 자신의 계정과 리소스에 대한 주체
- **Client/Relying Party**: 로그인 연동을 요청하는 웹·모바일·백엔드 애플리케이션
- **Identity Provider(IdP)**: 사용자를 인증하고 신원 정보를 제공하는 시스템
- **Authorization Server**: authorization code와 token을 발급하는 서버
- **Resource Server**: access token으로 보호된 API를 제공하는 서버
- **UserInfo Endpoint**: OIDC에서 사용자 Claim을 제공하는 API

실제 제품에서는 IdP와 Authorization Server가 하나의 플랫폼으로 제공되는 경우가 많다. 그러나 논리적 책임은 분리해서 이해해야 한다.

## 2. OIDC Authorization Code Flow

일반적인 웹 SSO는 Authorization Code Flow와 PKCE를 중심으로 설계한다.

```text
1. 사용자가 애플리케이션 접근
2. 애플리케이션이 IdP로 redirect
3. 사용자가 IdP에서 인증
4. IdP가 redirect_uri로 authorization code 전달
5. 애플리케이션이 code + PKCE verifier로 token 교환
6. 애플리케이션이 ID Token 검증
7. 애플리케이션 자체 세션 발급
```

인증 요청에는 보통 다음 값이 포함된다.

```text
response_type=code
client_id=...
redirect_uri=https://app.example.com/oauth/callback
scope=openid profile email
state=...
nonce=...
code_challenge=...
code_challenge_method=S256
```

OIDC 표준은 인증 요청에서 `openid` scope, redirect URI, state, nonce 등을 사용해 인증 흐름과 응답 검증을 구성한다.[1]

### state

`state`는 요청과 callback을 연결해 CSRF와 응답 혼동을 줄이는 값이다. 서버는 로그인 시작 시 생성한 state를 세션에 저장하고 callback의 state와 일치하는지 검증해야 한다.

### nonce

`nonce`는 인증 요청과 ID Token을 연결하는 값이다. 서버는 요청 시 nonce를 저장하고, 반환된 ID Token의 nonce Claim과 비교해야 한다.

### PKCE

PKCE는 authorization code를 가로채도 공격자가 token으로 교환하기 어렵게 만드는 검증 절차다. client가 `code_verifier`를 보관하고, 그 해시인 `code_challenge`를 authorization request에 보낸다. token 교환 때 verifier가 일치해야 한다.

공개 클라이언트와 모바일·SPA뿐 아니라, 웹 애플리케이션에서도 PKCE를 기본값으로 고려하는 것이 좋다.

## 3. ID Token과 Access Token의 차이

### ID Token

ID Token은 “사용자가 누구인지”에 대한 인증 결과다. 일반적으로 JWT 형태이며 다음과 같은 Claim을 포함할 수 있다.

- `iss`: 발급자
- `sub`: IdP 안에서의 사용자 식별자
- `aud`: 이 토큰을 받은 client
- `exp`: 만료 시각
- `iat`: 발급 시각
- `nonce`: 로그인 요청과의 연결 값
- `email`, `name`, `picture`: 선택적 사용자 정보

애플리케이션은 서명, issuer, audience, expiration, nonce를 검증해야 한다. ID Token을 API 인증용 bearer token처럼 다른 서비스에 전달하는 것은 올바른 사용이 아니다.

### Access Token

Access Token은 Resource Server API에 접근할 권한을 나타낸다. scope, audience, expiration, sender constraint 등의 정책에 따라 API 접근이 허용된다.

```text
ID Token    → 애플리케이션이 로그인한 사용자를 이해하기 위한 토큰
Access Token → API가 호출자를 검사하기 위한 토큰
```

두 토큰을 구분하지 않으면 다음 문제가 발생한다.

- API가 audience가 맞지 않는 ID Token을 받아들임
- 사용자 인증 정보와 API 권한을 혼동
- scope 검사를 하지 않고 로그인 여부만으로 API 허용
- token의 수신 대상과 검증 책임이 불분명해짐

## 4. Spring Boot 백엔드 연동 구조

Spring Boot에서 브라우저 로그인과 API resource server는 서로 다른 역할로 구성할 수 있다.

```text
Spring Boot Web App
  ├─ oauth2Login(): IdP 로그인·callback·애플리케이션 세션
  └─ resourceServer(): Bearer access token 검증
```

개념적인 설정은 다음과 같다.

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          company-idp:
            client-id: ${OIDC_CLIENT_ID}
            client-secret: ${OIDC_CLIENT_SECRET}
            scope: [openid, profile, email]
        provider:
          company-idp:
            issuer-uri: https://idp.example.com/realms/company
      resourceserver:
        jwt:
          issuer-uri: https://idp.example.com/realms/company
```

실제 설정에서는 secret을 Git 저장소나 이미지에 넣지 않고 Secret Manager, Kubernetes Secret, workload identity 등으로 주입한다.

### API 권한 검증

인증 성공만 확인해서는 부족하다. API는 다음을 검증해야 한다.

- issuer
- audience
- expiration
- signature/JWK key rotation
- scope
- role 또는 group claim
- tenant claim
- 요청 리소스의 소유권

예를 들어 `admin` role이 토큰에 있다고 해서 모든 리소스에 접근할 수 있는 것은 아니다. 조직·tenant·프로젝트 범위의 권한을 서버에서 다시 확인해야 한다.

## 5. 사용자 식별자와 계정 연결

SSO 연동에서 이메일을 주 식별자로 쓰는 것은 위험할 수 있다. 이메일은 변경될 수 있고, IdP 정책에 따라 재사용될 수 있기 때문이다.

일반적으로 다음 조합을 고려한다.

```text
identity_provider + issuer + subject(sub)
```

예:

```text
provider = company-idp
issuer   = https://idp.example.com/realms/company
sub      = stable-user-id
```

애플리케이션 DB에는 다음과 같은 구조를 둘 수 있다.

```text
users
- id
- display_name
- status

external_identities
- user_id
- issuer
- subject
- provider
- linked_at
```

이렇게 하면 사용자의 표시 이메일이 변경되어도 IdP의 안정적인 subject와 내부 사용자 계정을 연결할 수 있다.

## 6. SAML과 OIDC는 언제 사용하는가

SAML 2.0은 XML 기반 assertion과 authentication·attribute·authorization 정보를 전달하는 표준이다. SAML 메시지는 XML로 인코딩되고 HTTP POST나 SOAP 같은 전송 구조에 포함될 수 있으며, binding과 profile이 실제 사용 방식을 구체화한다.[3]

### OIDC가 적합한 경우

- 신규 웹·모바일·SPA 애플리케이션
- REST API와 OAuth scope가 중심인 시스템
- JavaScript·모바일·현대적인 API client
- JWT와 JSON 기반 Claim을 선호하는 환경
- PKCE 기반 authorization code flow가 필요한 경우

### SAML이 적합한 경우

- 기존 기업 IdP와의 연동
- 오래 운영된 엔터프라이즈 SaaS
- XML assertion, 기업 attribute profile, 기존 federation 정책
- 고객사가 SAML metadata와 인증서를 요구하는 경우

둘 중 하나가 항상 우월한 것은 아니다. 신규 API 중심 시스템은 OIDC가 단순한 경우가 많지만, 엔터프라이즈 고객의 기존 IdP와 연동하려면 SAML 지원이 계약 조건이 될 수 있다.

## 7. SSO 로그아웃과 세션 만료

로그인보다 어려운 것이 로그아웃이다.

```text
IdP 세션 종료
  ≠
애플리케이션 세션 종료
  ≠
API access token 즉시 폐기
```

설계 선택지는 다음과 같다.

- 애플리케이션 로컬 세션 삭제
- IdP logout endpoint redirect
- refresh token revoke
- 짧은 access token TTL
- back-channel logout
- 세션 상태 조회 또는 introspection

JWT access token은 이미 발급되면 서버가 매 요청마다 즉시 폐기하기 어려울 수 있다. 민감한 권한은 짧은 만료시간, token rotation, 중앙 세션 상태, 즉시 권한 조회를 조합해야 한다.

## 8. Multi-Tenancy와 SSO

SaaS에서는 사용자가 인증되었다는 것과 특정 tenant에 접근할 수 있다는 것을 분리해야 한다.

```text
인증: 이 사용자는 누구인가?
인가: 어떤 tenant·project·resource를 사용할 수 있는가?
```

검증 항목:

- token의 tenant/group claim
- 내부 계정과 tenant membership
- tenant별 role
- 리소스 소유권
- tenant 간 데이터 격리
- 관리자 impersonation 감사 로그

토큰의 `tenant_id`만 믿고 DB 쿼리를 만들면 안 된다. 서버의 membership과 리소스 scope를 함께 검사하고, 모든 데이터 접근이 tenant 조건을 포함하는지 테스트해야 한다.

## 9. Kubernetes 환경에서의 SSO 연동

Kubernetes 환경에서는 SSO를 애플리케이션 인증과 운영자 접근에 나누어 적용한다.

### 애플리케이션 경로

```text
Ingress / Gateway
  → OAuth2 Proxy 또는 애플리케이션
  → Spring/Python API
  → DB·내부 서비스
```

선택지는 다음과 같다.

- Ingress 앞단의 OAuth2 Proxy
- API Gateway에서 OIDC token 검증
- 각 서비스의 resource server 검증
- 내부 서비스 간 workload identity

앞단에서 로그인만 처리하고 내부 API가 토큰을 전혀 검증하지 않으면, 네트워크 내부의 우회 요청에 취약할 수 있다. 신뢰 경계를 명확히 정하고, 서비스별 권한 검증이 필요한 경우 각 서비스에서도 audience·scope·tenant를 확인해야 한다.

### Kubernetes 운영자 접근

Kubernetes API 접근도 OIDC 기반으로 구성할 수 있다. 운영자에게 장기 bearer token을 공유하는 방식보다 사용자의 IdP 계정·그룹과 Kubernetes RBAC를 연결하는 구조가 감사와 권한 회수에 유리하다.

```text
IdP group: platform-readonly
       ↓
Kubernetes RBAC Group
       ↓
read-only ClusterRoleBinding
```

권한은 최소화하고, 읽기 전용·운영 변경·클러스터 관리자 권한을 분리해야 한다.

## 10. 보안 체크리스트

### 필수 검증

- redirect URI exact match
- HTTPS 강제
- state 검증
- nonce 검증
- PKCE S256
- issuer 검증
- audience 검증
- signature와 JWK rotation 처리
- token expiration 검증
- scope·role·tenant 검증
- refresh token 보호
- client secret 비공개 관리
- 로그에서 authorization code와 token 제거

### 피해야 할 구현

- ID Token을 API access token처럼 사용
- 이메일만으로 계정 연결
- wildcard redirect URI
- URL fragment나 query string에 token 노출
- localStorage에 장기 토큰 저장
- client secret을 SPA 코드에 포함
- state를 고정 문자열로 사용
- 만료된 JWK를 영구 캐시
- `admin` claim 하나만 보고 모든 요청 허용
- 로그에 `Authorization: Bearer ...` 기록

OAuth 2.0 표준은 authorization code, access token, refresh token, redirect, endpoint, error 및 보안 고려사항을 구분한다.[2] 구현은 흐름만 연결하는 것보다 각 값의 검증과 수명주기까지 다뤄야 한다.

## 11. 장애 분석 순서

SSO가 안 될 때는 다음 순서로 나눈다.

1. IdP authorization endpoint까지 redirect되는가?
2. callback의 code와 state가 도착하는가?
3. token endpoint 교환이 성공하는가?
4. issuer·audience·signature 검증이 통과하는가?
5. 내부 사용자 계정 연결이 성공하는가?
6. 세션 cookie가 저장되는가?
7. API access token의 scope가 충분한가?
8. tenant membership과 resource authorization이 통과하는가?
9. clock skew로 `iat`·`exp`가 실패하지 않는가?
10. JWK cache와 key rotation이 정상인가?

오류 페이지 하나만 보고 “IdP 문제”라고 단정하지 말고, authorization·callback·token·session·API·DB 계층을 분리해 trace해야 한다.

## 결론

SSO는 로그인 화면을 통합하는 작업이 아니라 **신원 인증, 토큰 발급, 세션, API 권한, tenant 범위, 로그아웃, 감사 추적을 연결하는 보안 아키텍처**다.

- OIDC는 OAuth 2.0 위의 인증 계층이다.
- OAuth 2.0은 API 접근 권한 위임 프레임워크다.
- SAML은 XML assertion과 기업 federation에 강하다.
- ID Token과 Access Token은 목적이 다르다.
- 인증 성공과 API 인가는 별도로 검증해야 한다.
- Kubernetes에서는 애플리케이션 사용자 인증과 운영자 RBAC를 분리해야 한다.
- 가장 안전한 설계는 표준 flow를 사용하고 state·nonce·PKCE·issuer·audience·scope를 검증하는 것이다.

SSO 도입의 성공 기준은 “로그인 버튼이 동작한다”가 아니다. 계정 연결, 권한 회수, 만료·로그아웃, key rotation, tenant 격리, 장애 추적까지 재현 가능한지 확인해야 한다.

## 참고 자료

[1] OpenID Connect Core 1.0 — OAuth 2.0 위의 인증 계층, ID Token과 Claim  
[2] RFC 6749 — OAuth 2.0 authorization framework와 token flow  
[3] OASIS SAML V2.0 Core — XML assertion과 protocol 구조

## 출처

- OpenID Connect Core 1.0: https://openid.net/specs/openid-connect-core-1_0.html
- OAuth 2.0 RFC 6749: https://datatracker.ietf.org/doc/html/rfc6749
- SAML 2.0 Core: https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf

## Sources

[1] https://openid.net/specs/openid-connect-core-1_0.html — OpenID Connect Core 1.0
[2] https://datatracker.ietf.org/doc/html/rfc6749 — OAuth 2.0 RFC 6749
[3] https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf — SAML 2.0 Core
