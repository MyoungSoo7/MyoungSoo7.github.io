---
layout: post
title: "시큐어코딩의 핵심과 실전 적용: 취약점을 만드는 경계를 먼저 막기"
date: 2026-09-10 14:04:34 +0900
categories: [Security]
tags: [Secure Coding, DevSecOps, OWASP, CWE, REST API, Kubernetes, SAST]
---

# 시큐어코딩이란 무엇인가

시큐어코딩은 취약점이 발견된 뒤 패치하는 활동만을 뜻하지 않는다. 요구사항·설계·구현·테스트·배포·운영의 각 단계에서 공격자가 통제할 수 있는 입력과 시스템이 신뢰하는 경계를 찾아, 안전한 기본값과 검증으로 위험을 줄이는 개발 방식이다.

OWASP Top 10은 웹 애플리케이션의 대표적인 보안 위험을 설명하는 인식·교육 기준이며, 2025 목록에는 Broken Access Control, Security Misconfiguration, Software Supply Chain Failures, Cryptographic Failures, Injection 등이 포함되어 있다.[1] MITRE CWE Top 25는 현재 흔하고 영향이 큰 소프트웨어 약점을 정리한 목록으로, 개발자가 반복되는 약점 유형을 우선 점검하는 데 활용할 수 있다.[6]

핵심은 보안 기능을 마지막에 덧붙이는 것이 아니라, 처음부터 **입력·권한·상태·비밀·의존성·오류**를 설계 대상으로 삼는 것이다.

## 1. 시큐어코딩의 기본 원칙

### 신뢰하지 말고 검증한다

브라우저 검증은 사용자 경험을 위한 보조 수단일 뿐 보안 경계가 아니다. API 서버는 모든 입력을 다시 검증해야 한다.

- 타입
- 길이
- 허용 범위
- 형식
- 열거형 값
- 중첩 객체 구조
- 파일 크기와 실제 content type
- 요청 body와 query parameter

OWASP의 보안 코드 리뷰 가이드는 서버 측 validation, allowlist, 출력 인코딩, 파일 업로드, 파라미터화된 쿼리를 주요 검토 대상으로 제시한다.[2]

### 권한은 모든 보호된 endpoint에서 확인한다

로그인한 사용자라는 사실은 특정 리소스에 접근할 권한이 있다는 뜻이 아니다.

```text
인증(Authentication): 누구인가?
인가(Authorization): 무엇을 할 수 있는가?
소유권(Ownership): 이 리소스의 주체인가?
범위(Scope): 어떤 tenant·project에 속하는가?
```

REST API는 각 endpoint에서 호출자의 권한을 확인해야 한다. OWASP는 비공개 REST 서비스가 endpoint별 access control을 수행하고, JWT를 사용할 때 issuer·audience·expiration·not-before 같은 Claim을 검증해야 한다고 안내한다.[4]

### 최소 권한과 안전한 기본값

- 기본 role은 가장 낮은 권한으로 둔다.
- 관리자 endpoint를 별도 namespace·권한·감사 로그로 분리한다.
- 필요하지 않은 HTTP method는 허용하지 않는다.
- 실패하면 허용하는 대신 실패하면 거부한다.
- 내부 네트워크라는 이유로 인증을 생략하지 않는다.

## 2. Injection을 막는 실전 방법

### SQL Injection

나쁜 예:

```java
String sql = "SELECT * FROM users WHERE name = '" + name + "'";
```

안전한 방향:

```java
String sql = "SELECT * FROM users WHERE name = ?";
PreparedStatement statement = connection.prepareStatement(sql);
statement.setString(1, name);
```

Spring Data JPA를 쓰더라도 native query 문자열 조합, 정렬 조건, 동적 table name, filter expression을 별도로 검토해야 한다. ORM이 모든 injection을 자동으로 막아준다고 가정하면 안 된다.

### NoSQL Injection

MongoDB 등 document query를 요청 JSON 그대로 query object로 변환하지 않는다. 검색 필드와 연산자를 allowlist로 제한하고, 사용자 입력이 query operator로 해석되지 않도록 DTO와 타입을 분리한다.

### OS Command Injection

사용자 입력을 shell command 문자열에 이어 붙이지 않는다. 가능하면 command 자체를 제거하고 라이브러리 API를 사용한다. 반드시 실행해야 한다면 executable과 argument를 고정하고, shell 해석을 거치지 않으며, 실행 권한과 timeout·resource limit을 둔다.

### XSS와 출력 인코딩

입력을 저장할 때 모든 HTML을 무조건 지우는 방식보다 출력 context에 맞는 encoding이 중요하다.

- HTML context
- JavaScript context
- URL context
- CSS context
- JSON context

Markdown·HTML을 허용하는 게시 기능은 sanitizer와 허용 태그 정책을 함께 사용하고, Content Security Policy 같은 defense-in-depth도 검토한다.

## 3. 인증·세션·토큰

인증이 성공해도 세션이 탈취되면 공격자는 사용자를 가장할 수 있다. OWASP는 세션 ID가 인증 강도와 연결되어 있어 탈취·예측·고정이 발생하면 세션 hijacking으로 이어질 수 있다고 설명한다.[3]

실전 체크리스트:

- 세션 ID는 CSPRNG로 생성한다.
- 로그인·권한 상승 후 세션 ID를 재발급한다.
- 로그아웃과 timeout에서 세션을 무효화한다.
- Cookie에 `Secure`, `HttpOnly`, 적절한 `SameSite`를 설정한다.
- 인증 token을 URL query string에 넣지 않는다.
- 브라우저 `localStorage`에 장기 인증정보를 보관하지 않는다.
- refresh token은 짧은 수명 access token과 분리한다.
- 민감한 작업은 재인증 또는 step-up authentication을 요구한다.
- 동시 로그인과 비정상 세션을 감사한다.

JWT를 검증할 때는 header의 algorithm을 그대로 신뢰하지 말고, 서버 설정으로 허용 알고리즘과 키를 고정한다. `iss`, `aud`, `exp`, `nbf`를 확인하고, 필요한 경우 `jti` denylist나 중앙 세션 상태로 조기 폐기를 구현한다.[4]

## 4. 암호화와 비밀정보 관리

암호화는 알고리즘 이름만 붙인다고 안전해지지 않는다. threat model, 키 수명, 키 보관 위치, rotation, backup, 폐기 정책을 함께 설계해야 한다.

### 비밀번호

비밀번호는 복호화 가능한 암호화로 저장하지 않고, 전용 password hashing 방식을 사용한다.[5]

### 데이터 암호화

OWASP는 저장 데이터 보호에서 인증된 암호화 모드를 우선하고, 일반적인 대칭 암호화에는 AES 계열을 권장한다. AES-GCM·CCM처럼 기밀성·무결성을 함께 제공하는 authenticated mode를 우선 검토하고 ECB는 피해야 한다.[5]

### 키 관리

- 키를 소스 코드에 hard-code하지 않는다.
- Git에 secret과 private key를 commit하지 않는다.
- 환경변수만으로 충분하다고 가정하지 않는다.
- Secret Manager 또는 KMS를 사용한다.
- 암호화 키와 암호화 데이터를 가능한 한 분리한다.
- key rotation과 이전 키로 암호화된 데이터의 migration을 설계한다.
- 로그·exception·dump에 키가 노출되지 않게 한다.

## 5. REST API 시큐어코딩

REST API는 HTTPS를 사용해야 한다. HTTPS는 credential과 token의 전송을 보호하고 서버 인증과 전송 무결성을 제공한다.[4]

### 요청 경계

- Content-Type을 검증한다.
- body·header·query 크기 제한을 둔다.
- JSON depth와 배열 길이를 제한한다.
- multipart 파일 크기와 확장자·실제 파일 형식을 검사한다.
- 허용 HTTP method만 열어 둔다.
- timeout과 rate limit을 설정한다.

### 응답 경계

- 401과 403을 구분한다.
- 오류 응답에 stack trace와 내부 경로를 포함하지 않는다.
- API key·password·token을 URL에 넣지 않는다.
- 민감한 필드를 DTO 응답에서 명시적으로 제외한다.
- 작업이 비동기라면 202 Accepted와 상태 조회 API를 사용한다.
- 모든 endpoint의 authorization을 독립적으로 확인한다.

### HTTP 상태 코드

모든 성공·실패를 200으로 반환하면 모니터링과 보안 탐지가 어려워진다. 인증 실패는 401, 권한 부족은 403, 잘못된 입력은 400, payload 초과는 413, rate limit은 429처럼 의미에 맞는 상태 코드를 사용한다.[4]

## 6. 예외 처리와 로그

예외 처리는 보안과 가용성을 동시에 좌우한다.

안전한 오류 응답:

```json
{
  "code": "INVALID_REQUEST",
  "message": "요청을 처리할 수 없습니다.",
  "traceId": "safe-correlation-id"
}
```

피해야 할 응답:

```json
{
  "exception": "org.postgresql.util.PSQLException",
  "sql": "SELECT ... password ...",
  "stackTrace": "..."
}
```

로그에는 다음을 기록한다.

- 인증 실패와 권한 거부
- 입력 validation 실패의 유형과 빈도
- rate limit 초과
- token 검증 실패
- 관리자 작업과 권한 변경
- 의존성·서명·배포 검증 실패
- trace ID와 안전한 request ID

기록하지 말아야 할 것:

- 비밀번호
- access token·refresh token
- API key
- session cookie
- private key
- 전체 카드번호와 민감한 개인정보

보안 로그는 저장만 하는 것으로 끝나지 않는다. alert 기준과 담당자, 보존기간, 위변조 방지, 시간 동기화까지 정해야 한다.

## 7. 파일 업로드·SSRF·비직렬화

### 파일 업로드

- 허용 MIME과 실제 content를 함께 검사한다.
- 파일명은 서버에서 새로 생성한다.
- web root 밖에 저장한다.
- 확장자와 content type을 allowlist로 제한한다.
- 압축 해제 폭탄과 archive traversal을 방어한다.
- 크기·해상도·처리시간을 제한한다.
- 바이러스 검사와 격리 저장을 검토한다.

### SSRF

사용자가 제공한 URL을 서버가 가져오는 기능은 내부 네트워크와 metadata endpoint 공격으로 이어질 수 있다. 허용 도메인·scheme·port를 제한하고, DNS 재해석·redirect·IPv4/IPv6 우회·private address를 검증한다.

### 안전하지 않은 역직렬화

신뢰할 수 없는 입력을 임의의 객체로 역직렬화하지 않는다. 허용 타입을 제한하고, JSON DTO·스키마 검증·서명 검증을 사용한다.

## 8. 공급망과 DevSecOps

시큐어코딩은 애플리케이션 소스만의 문제가 아니다. 라이브러리, base image, build action, container registry, package lock, artifact provenance까지 공격면이다. OWASP Top 10:2025도 Software Supply Chain Failures를 주요 위험으로 포함한다.[1]

CI/CD에 넣을 수 있는 검증:

1. dependency lockfile 검사
2. SCA와 CVE scanner
3. SAST
4. secret scanning
5. container image scan
6. IaC와 Kubernetes manifest 검사
7. license policy 검사
8. unit·integration·security test
9. SBOM 생성과 artifact 보관
10. 서명·provenance·registry 정책 검증

하지만 scanner 결과가 0이라고 업무 성공을 의미하지는 않는다. 빌드 대상·실행 이미지·배포된 digest·실제 runtime 설정을 연결해서 확인해야 한다.

## 9. Kubernetes와 시큐어코딩

애플리케이션이 안전해도 배포 설정이 취약하면 공격면이 다시 열린다.

- container는 non-root로 실행한다.
- 필요 없는 Linux capability를 제거한다.
- read-only root filesystem을 검토한다.
- image tag보다 immutable digest를 사용한다.
- Kubernetes Secret을 Git에 평문으로 저장하지 않는다.
- ServiceAccount 권한을 최소화한다.
- NetworkPolicy로 통신 범위를 제한한다.
- Ingress와 API의 TLS를 강제한다.
- liveness·readiness probe에 민감한 정보를 노출하지 않는다.
- debug actuator와 admin endpoint를 외부에 열지 않는다.
- resource limit와 요청 크기를 정해 DoS 영향을 줄인다.
- 감사 로그와 변경 이력을 남긴다.

Kubernetes의 `Running` 상태는 보안 검증을 의미하지 않는다. 실제 endpoint 노출, RBAC, Secret mount, network path, image digest, runtime user를 함께 확인해야 한다.

## 10. 보안 코드 리뷰 절차

OWASP는 보안 코드 리뷰를 자동화 도구만으로 대체할 수 없는 수동 검토 과정으로 설명한다. 특히 business logic, 인증·인가, cryptography, data flow 같은 맥락 의존 영역은 사람의 판단이 필요하다.[2]

### PR 단위 리뷰

1. 변경된 trust boundary 확인
2. 새 입력·endpoint·파일·외부 연동 확인
3. 인증과 권한 검증 위치 확인
4. DB·shell·template·파일 sink 추적
5. secret과 개인정보 노출 여부 확인
6. 오류·로그·metric 확인
7. dependency·image·IaC 변경 확인
8. security regression test 추가

### 질문 방식

- 이 값은 누가 통제하는가?
- 검증은 client와 server 중 어디에 있는가?
- 이 endpoint는 객체 소유권을 확인하는가?
- 실패했을 때 기본 동작이 허용인가 거부인가?
- 로그에 공격에 활용될 정보가 남는가?
- token의 audience와 권한 범위는 맞는가?
- 이 데이터가 다른 tenant로 넘어갈 수 있는가?
- retry가 중복 결제나 중복 작업을 만들 수 있는가?

## 11. 실전 체크리스트

### 개발 전

- [ ] 자산과 trust boundary를 정의했는가?
- [ ] 위협 모델과 abuse case를 작성했는가?
- [ ] 개인정보·비밀정보 저장을 최소화했는가?
- [ ] 권한 모델과 tenant 경계를 설계했는가?

### 개발 중

- [ ] 서버 측 allowlist validation
- [ ] parameterized query
- [ ] output encoding
- [ ] endpoint별 authorization
- [ ] secure session cookie
- [ ] timeout·크기 제한·rate limit
- [ ] 안전한 crypto library와 key management
- [ ] 예외·로그 민감정보 제거

### PR·CI

- [ ] SAST
- [ ] SCA·lockfile 검사
- [ ] secret scanning
- [ ] container/IaC scanning
- [ ] security unit/integration test
- [ ] SBOM 생성
- [ ] dependency·base image 업데이트
- [ ] 변경된 권한·네트워크 정책 검토

### 배포·운영

- [ ] 실제 배포 digest 확인
- [ ] runtime user와 capability 확인
- [ ] TLS·RBAC·NetworkPolicy 확인
- [ ] 인증 실패·권한 거부 alert
- [ ] key rotation과 revoke 절차
- [ ] incident 대응과 rollback runbook
- [ ] 보안 로그가 실제 수집·검색되는지 확인

## 결론

시큐어코딩은 특정 라이브러리를 추가하는 작업이 아니라, **신뢰 경계마다 검증·권한·무결성·관측을 배치하는 설계 습관**이다.

- 입력은 서버에서 allowlist로 검증한다.
- 인증과 인가와 소유권 검사를 분리한다.
- SQL·NoSQL·shell·template injection을 데이터와 명령의 분리로 막는다.
- session·JWT·cookie의 수명과 검증을 설계한다.
- 키와 비밀은 소스·로그·이미지에서 제거한다.
- REST API는 HTTPS·endpoint 권한·rate limit·의미 있는 상태 코드를 사용한다.
- CI에서는 dependency·image·IaC·secret까지 공급망을 검사한다.
- 운영에서는 스캐너 결과보다 실제 배포 artifact와 runtime 설정을 검증한다.

가장 좋은 시큐어코딩은 취약점 목록을 외우는 것이 아니라, 코드를 볼 때마다 다음을 묻는 것이다.

> 이 입력은 어디서 왔고, 누가 통제하며, 어떤 권한으로 어떤 상태를 바꾸고, 실패했을 때 무엇이 노출되는가?

## 참고 자료

[1] OWASP Top 10:2025 — 웹 애플리케이션 주요 보안 위험  
[2] OWASP Secure Code Review Cheat Sheet — 수동 보안 코드 리뷰 절차와 취약점 패턴  
[3] OWASP Session Management Cheat Sheet — 세션 ID·cookie·세션 lifecycle  
[4] OWASP REST Security Cheat Sheet — HTTPS·JWT·endpoint access control·입력 검증  
[5] OWASP Cryptographic Storage Cheat Sheet — 암호화·키 관리·authenticated encryption  
[6] MITRE CWE Top 25:2025 — 흔하고 영향이 큰 소프트웨어 약점

## 출처

- OWASP Top 10:2025: https://owasp.org/Top10/2025/
- OWASP Secure Code Review: https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html
- OWASP Session Management: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP REST Security: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- OWASP Cryptographic Storage: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- MITRE CWE Top 25:2025: https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html

## Sources

[1] https://owasp.org/Top10/2025 — OWASP Top 10 2025
[2] https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html — OWASP Secure Code Review
[3] https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html — OWASP Session Management
[4] https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html — OWASP REST Security
[5] https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html — OWASP Cryptographic Storage
[6] https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html — MITRE CWE Top 25 2025
