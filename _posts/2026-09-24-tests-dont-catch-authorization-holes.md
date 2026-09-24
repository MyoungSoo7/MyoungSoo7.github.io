---
layout: post
title: "테스트 2,000개가 통과해도 남는 보안 구멍 — 소스 리뷰에서 실제로 나온 다섯 가지"
date: 2026-09-24 19:50:55 +0900
categories: [Security]
tags: [소스보안, 코드리뷰, OWASP, IDOR, BOLA, MassAssignment, GitHubActions, SpringBoot]
---

최근 Spring Boot 기반 정산 백엔드 하나를 종합 리뷰했다. 겉으로 보면 모범생 같은 코드였다.

- 헥사고날 구조를 ArchUnit 이 강제한다.
- 도메인 계층 커버리지 90% 게이트가 있다.
- 핵심 모듈에만 테스트가 2,000개가 넘는다.
- 실제 Postgres 위에서 동시성 경합까지 테스트한다.

그런데 보안 리뷰에서는 **"아무나 관리자로 가입할 수 있다"** 급의 구멍이 나왔다.

이 글은 그 리뷰에서 나온 유형을 일반화한 것이다. 해당 프로젝트를 특정할 수 있는 경로나 재현 절차는 싣지 않는다. 시큐어코딩 원칙 전반은 [이전 글](/2026/09/10/secure-coding/)에 정리했으니, 여기서는 한 가지 질문에 집중한다.

> **테스트가 이렇게 많은데 왜 못 잡았나?**

## 먼저 답: 테스트는 "의도한 사용자"를 검증한다

단위 테스트든 통합 테스트든, 우리는 보통 **정상 사용자가 정상 경로로 들어오는** 시나리오를 쓴다. "주문자 A 가 자기 주문 1번을 조회하면 200" 같은 식이다.

보안 결함은 대개 **아무도 테스트를 쓰지 않은 조합**에 있다.

- "사용자 B 가 A 의 주문 1번을 조회하면?"
- "가입 요청 body 에 필드를 하나 더 넣으면?"

기능 테스트가 아무리 많아도 이 질문은 스스로 생기지 않는다.

게다가 이번 프로젝트의 커버리지 게이트는 **adapter 계층(컨트롤러, 필터, 설정)을 측정에서 뺐다.** 인가 검사가 사는 곳이 바로 거기다. "90% 커버리지"와 "인가가 검증됐다"는 전혀 다른 말이었다.

## 1. 가입 요청으로 권한 올리기 — Mass Assignment

**패턴**

- 회원가입 API 는 로그인 없이 열려 있다. 당연하다.
- 그런데 요청 DTO 에 `role` 필드가 있고, 그 값이 검증 없이 도메인 객체까지 전달된다.
- 그래서 가입 body 에 관리자 role 을 넣으면 관리자 계정이 생긴다.

OWASP API Security Top 10 2023 은 이 유형을 [API3:2023 Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/) 에 묶는다. 예전 이름인 *Mass Assignment* 와 *Excessive Data Exposure* 를 합친 항목이다. CWE 로는 [CWE-915: Improperly Controlled Modification of Dynamically-Determined Object Attributes](https://cwe.mitre.org/data/definitions/915.html) 에 해당한다.

**막는 법**

[OWASP Mass Assignment Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html) 의 일반 해법은 "DTO 를 만들고 입력을 도메인 객체에 직접 바인딩하지 말라" 이다. 한 단계 더 나가면 이렇다.

- **엔드포인트별 DTO 를 따로 둔다.** 가입 DTO 에는 애초에 `role` 이 없어야 한다. 관리자 승격은 별도의 관리자 전용 API 로만 한다.
- 도메인에도 방어선을 둔다. "자가 가입으로 만들 수 있는 role" 화이트리스트를 두면 다른 진입점이 생겨도 막힌다.
- **테스트는 공격자 입력으로 쓴다.** `role=ADMIN` 을 넣은 가입 요청이 거절되는지 확인한다.

## 2. 남의 객체 ID 넣기 — IDOR / BOLA

**패턴**

- `GET /orders/{id}` 는 로그인만 확인하고 **그 주문이 요청자 것인지는 확인하지 않는다.**
- 흥미로운 점은 같은 컨트롤러의 목록 API 에는 소유권 검사가 들어 있었다는 것이다. 한 파일 안에서도 일관성이 깨진다.
- 결제, 환불 이력, 배송지, 회원 상세 API 도 같은 모양이었다.

OWASP 는 이를 [API1:2023 Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/) 로 첫 번째에 올려 두었다. 공격자는 "요청에 담긴 객체 ID 를 조작"하는 것만으로 이를 악용한다. CWE 는 [CWE-639: Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html) 이다.

**막는 법**

- **사용자 식별자는 요청 body 나 query 가 아니라 인증 토큰에서만 꺼낸다.** body 에 `userId` 를 받는 API 는 그 자체가 신호다.
- 소유권 검사를 컨트롤러마다 손으로 넣지 말고, **조회 자체를 소유자 조건으로** 한다. 예: `findByIdAndOwnerId`. 검사를 잊을 수 없는 구조로 만드는 것이다.
- 통합 테스트에 "다른 사용자 토큰 → 403/404" 케이스를 **엔드포인트마다** 하나씩 둔다. 여기가 기능 테스트 2,000개로는 채워지지 않는 칸이다.

## 3. 운영 엔드포인트가 새어 나가기 — Actuator 노출

**패턴**

- 개별 서비스는 actuator 를 조심스럽게 설정했다.
- 그런데 프런트 nginx 가 `actuator|swagger-ui|v3/api-docs` 경로를 그대로 **게이트웨이로 넘겼다.**
- 게이트웨이 자체에는 보안 필터가 없었다.

각 조각은 맞게 설정됐는데, 조합하니 외부로 열렸다.

[Spring Boot 공식 문서](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html)에 따르면 기본값으로는 **health 엔드포인트만** HTTP 로 노출된다. 노출 범위를 넓힐 때는 방화벽 뒤에 두거나 Spring Security 같은 것으로 보호하라고 권고한다. 문제는 대개 이 권고를 **한 서비스 안에서만** 지키고, 앞단 프록시 라우팅은 따로 보지 않는 데서 생긴다.

**막는 법**

- 관리용 포트를 따로 두고(`management.server.port`), 외부 프록시에서는 그 포트로 가는 경로를 아예 만들지 않는다.
- 리뷰할 때 서비스 설정만 보지 말고 **프록시 → 게이트웨이 → 서비스 라우팅을 한 줄로 이어서** 본다.

## 4. 조용히 열려 있는 내부 API — fail-open 기본값

**패턴**

- `/internal/**` API 는 공유 키로 보호한다.
- 그런데 **키가 설정되지 않으면 통과시키는** 필터였다.
- 운영 프로필에서만 "키 필수" 로 바꾸는데, 한 서비스는 운영 프로필 파일이 아예 없었다.
- 그 서비스의 내부 API 는 **아무 수신자에게나 회사 SMTP 로 메일을 보내는** 기능이었다.

개발 편의를 위한 fail-open 기본값은 새 서비스를 추가할 때마다 한 번씩 잊힌다.

**막는 법**

- 보안 설정의 기본값은 **fail-closed** 로 둔다. 로컬 개발에서만 명시적으로 푼다.
- 키 비교는 `String.equals` 대신 상수 시간 비교(`MessageDigest.isEqual` 등)를 쓴다.
- "모든 서비스에 prod 프로필이 있고 필수 보안 키가 설정돼 있는가" 를 CI 에서 검사한다. 사람이 기억하는 대신 기계가 확인하게 한다.

## 5. 코드 밖의 소스 보안 — CI 와 저장소 설정

소스 보안은 코드 줄에서 끝나지 않는다. 이번 리뷰에서 저장소 쪽은 이랬다.

- **Actions 는 대부분 커밋 SHA 로 고정돼 있었다(좋음).** GitHub 공식 문서는 "전체 길이 커밋 SHA 로 고정하는 것이 액션을 불변 릴리스로 쓰는 현재 유일한 방법" 이라고 말한다 ([Secure use reference](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)). 그런데 워크플로 하나만 태그로 고정돼 있었고, 그 워크플로에는 `permissions:` 블록도 없었다. `GITHUB_TOKEN` 은 최소 권한으로 두라는 게 같은 문서의 권고다.
- **PR 이 self-hosted runner 에서 돌고, 노드의 빌드 캐시를 공유했다.** 같은 문서는 self-hosted runner 를 공개 저장소에 쓰면 "누구나 PR 을 열어 환경을 오염시킬 수 있다" 고 경고한다. 비공개 저장소라도 캐시 오염 경로는 남는다.
- `pull_request_target` 은 쓰지 않았다(좋음). 이 트리거로 신뢰할 수 없는 PR 코드를 체크아웃하면 쓰기 권한과 시크릿이 노출될 수 있다 ([GitHub Security Lab](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/)).
- **Secret scanning 과 push protection 이 꺼져 있었다.** [Push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection) 은 시크릿이 담긴 push 를 저장소에 도달하기 *전에* 막는다. 커밋 이력에 한 번 들어간 키는 지워도 이미 복제돼 있다고 봐야 하므로, 사후 탐지보다 이쪽이 싸다.
- **필수 체크가 항상 빨간데 머지가 계속됐다.** 아티팩트 저장 쿼터 초과로 보안 워크플로가 10번 연속 실패했는데 PR 은 머지됐다. 항상 빨간 체크는 "빨간불은 무시해도 된다" 는 습관을 가르친다. 보안 게이트가 없는 것보다 나쁠 수 있다.

덧붙여 **라이선스도 소스 관리의 일부다.** 이 프로젝트는 PDF 라이브러리 때문에 전체가 AGPL 이었다. [AGPL-3.0 제13조](https://www.gnu.org/licenses/agpl-3.0.html)는 수정한 프로그램을 네트워크로 사용자에게 제공하면 그 사용자에게 소스를 받을 기회를 줘야 한다고 정한다. SaaS 로 팔 생각이 있다면 의존성 하나가 사업 모델을 정한다.

## 정리 — 리뷰 질문을 바꾸면 보인다

| 기능 리뷰의 질문 | 보안 리뷰의 질문 |
|---|---|
| 이 API 가 올바른 값을 돌려주는가? | **다른 사용자**가 호출하면 무엇을 돌려주는가? |
| DTO 에 필요한 필드가 다 있는가? | DTO 에 **있으면 안 되는** 필드가 있는가? |
| 서비스 설정이 맞는가? | 프록시부터 서비스까지 **이어 붙이면** 무엇이 열려 있는가? |
| 키가 설정되면 잘 막는가? | 키가 **없으면** 어떻게 동작하는가? |
| CI 가 초록인가? | 빨간 체크가 **머지를 실제로 막는가?** |

테스트 개수와 커버리지 숫자는 "만든 사람이 생각한 것" 이 잘 돌아간다는 증거다. 보안은 **만든 사람이 생각하지 않은 것**에서 깨진다. 그래서 보안 테스트는 기능 테스트를 늘려서 얻는 게 아니라 **질문을 바꿔서** 얻는다.

## References

- OWASP API Security Top 10 2023 — [API1 BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/) · [API3 BOPLA](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/) · [API5 BFLA](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/)
- MITRE CWE — [CWE-915](https://cwe.mitre.org/data/definitions/915.html) · [CWE-639](https://cwe.mitre.org/data/definitions/639.html)
- [OWASP Mass Assignment Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- [Spring Boot Reference — Actuator Endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html)
- GitHub Docs — [Secure use reference (Actions)](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions) · [About push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection)
- GitHub Security Lab — [Keeping your GitHub Actions and workflows secure: Preventing pwn requests](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/)
- [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html)
