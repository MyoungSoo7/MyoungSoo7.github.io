---
layout: post
title: "로그인은 됐는데 남의 주문이 보인다 — Spring API 인가 결함을 전수 점검하는 Claude Code 스킬 api-authz-audit"
date: 2026-10-05 17:40:34 +0900
categories: [security]
tags: [claude-code, skill, api-security, owasp, bola, idor, spring-boot, spring-security, egovframe]
---

API 보안 사고 중에는 해커가 로그인을 뚫어서 생기는 것보다 **로그인한 사용자가 URL의 숫자 하나를 바꿔서** 생기는 것이 더 흔하다.
`GET /api/v1/orders/1001` 이 내 주문이면, `1002` 는 남의 주문이다. 서버가 "이 주문이 요청한 사람의 것인가"를
묻지 않으면 그대로 응답한다.

OWASP 는 이것을 2023년판 API 보안 Top 10 의 **1위(API1:2023 Broken Object Level Authorization)** 로 올렸다.
설명은 이렇다. "사용자에게서 받은 ID로 데이터에 접근하는 *모든* 함수에서 객체 수준 인가 검사를 해야 한다"
([OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)).
같은 결함을 MITRE 는 [CWE-639 (Authorization Bypass Through User-Controlled Key)](https://cwe.mitre.org/data/definitions/639.html) 로 분류한다.

이 글에서는 [heracul/skills 리포의 `api-authz-audit`](https://github.com/heracul/skills/tree/main/api-authz-audit) 를 다룬다.
이 결함을 Spring Boot 와 전자정부프레임워크 백엔드에서 **엔드포인트 하나도 빠짐없이** 찾도록 만든 Claude Code 스킬이다.
원문을 읽고, 스킬에 들어 있는 예제 프로젝트로 직접 돌려 봤다.

> 이 리포는 2026-10-03 에 만들어졌다. 글을 쓰는 시점(2026-10-05) 기준 버전은 0.1.0 이고 스타가 0개인 신생 프로젝트다(MIT 라이선스).
> 아래 내용은 리포 원문과 내 로컬 실행 결과다. 실제 서비스에서 검증된 실적은 아직 없다.

## 1. 왜 "인증"으로는 안 막히나

인증(authentication)은 *누구인지* 를 확인하고, 인가(authorization)는 *그 사람이 이 객체에 손대도 되는지* 를 확인한다.
게이트웨이에서 JWT 를 검사하는 것은 인증이다. 토큰이 진짜여도, 그 토큰의 주인이 주문 1002번의 주인인지는 아무도 확인하지 않았다.

이 스킬이 가장 공들이는 부분은 그래서 **"안심 패턴" 목록**이다. 현장에서 자주 듣지만 인가가 아닌 것들을
명시적으로 반증 근거로 쓰지 않도록 막아 둔다.

| 흔한 안심 | 스킬의 판단 |
|---|---|
| "ID가 UUID라서 추측 못 해요" | 추측 난이도는 노출 확률만 낮춘다. 인가가 아니다 |
| "앱은 그 API를 안 불러요" / "버튼이 숨겨져 있어요" | 서버는 클라이언트를 고를 수 없다 |
| "게이트웨이가 토큰을 검사해요" | 그것은 인증이다 |
| "`@PreAuthorize` 붙어 있어요" | 메서드 시큐리티가 *켜져* 있는지까지 봐야 한다 |
| "내부망이에요" | 우선순위 보정 사유일 뿐, 결함이 사라지지 않는다 |
| "ID를 암호화했어요" | 암호문을 그대로 재사용하면 똑같이 뚫린다 |
| 쓰기 API 에 `@PostAuthorize` | 메서드가 *실행된 뒤* 검사하므로 변경은 이미 일어났다 |
| 토큰을 디코드해서 사용자 ID 를 꺼내요 | 서명 검증 없는 디코드는 [CWE-347](https://cwe.mitre.org/data/definitions/347.html) 이다 |

## 2. "선언만 된 보안"을 잡는다

정적 분석 도구가 `@PreAuthorize` 를 보고 "보호됨"으로 넘어가는 실수를 이 스킬은 명시적으로 겨냥한다.
근거는 Spring Security 공식 문서에 있다.

- Spring Security 6 의 `@EnableMethodSecurity` 는 `prePostEnabled` 기본값이 **true** 다
  ([EnableMethodSecurity Javadoc](https://docs.spring.io/spring-security/reference/api/java/org/springframework/security/config/annotation/method/configuration/EnableMethodSecurity.html)).
- 그 이전의 `@EnableGlobalMethodSecurity` 는 `prePostEnabled`·`securedEnabled`·`jsr250Enabled` 가 모두 기본 **false** 다
  ([5.8 Javadoc](https://docs.spring.io/spring-security/site/docs/5.8.x/api/org/springframework/security/config/annotation/method/configuration/EnableGlobalMethodSecurity.html)).
  Boot 2 프로젝트에서 애노테이션만 붙이고 옵션을 안 켰다면 `@PreAuthorize` 는 장식이다.
- `@Secured` 와 `@RolesAllowed` 는 6에서도 기본 false 라 별도로 켜야 한다(위 Javadoc).
- 그리고 공식 문서에 이 한 줄이 있다. "Spring Boot Starter Security 는 메서드 수준 인가를 기본으로 활성화하지 않는다"
  ([Method Security 레퍼런스](https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html)).

그 밖에 스킬이 확인하는 "있는데 안 도는" 경우는 다음과 같다(리포 원문 기준).

- `web.ignoring()` 에 들어간 경로. 이 경로는 보안 필터 체인 자체를 건너뛴다.
- 인터셉터 `excludePathPatterns`
- 같은 클래스 안에서 자기 메서드를 호출하는 경우. 프록시를 거치지 않아 애노테이션이 무시된다.
- 커스텀 `ArgumentResolver` 가 `X-User-Id` 같은 요청 헤더로 사용자를 정하는 경우
- 전자정부프레임워크의 XML 인터셉터 설정

경로 매칭 차이도 다룬다. Spring Framework 6.0 은 후행 슬래시 매칭의 기본값을 true 에서 false 로 바꿨다.
`/resources` 는 막혔는데 `/resources/` 는 통과하는 우회가 실제로 보고됐기 때문이다
([spring-framework#28552](https://github.com/spring-projects/spring-framework/issues/28552)).
Boot 2 와 Boot 3 프로젝트에서 같은 `antMatchers` 설정이 다르게 동작할 수 있다는 뜻이다.

## 3. 어떻게 동작하나 — 기계가 목록을 만들고, Claude 가 판정한다

스킬은 다섯 단계로 돈다. 핵심은 **"빠짐없이"를 스크립트가 보장하고, "맞는지"는 Claude 가 코드를 따라가며 판단한다** 는 분업이다.

| 단계 | 하는 일 | 산출물 |
|---|---|---|
| 0 | 환경 문답: 인터넷 공개인지, 호출 주체가 누구인지, 앞단 통제, 데이터 민감도, 정보주체 수 | `.authz-audit/context.yaml` |
| 1 | `discover_endpoints.py` 로 모든 엔드포인트 추출 (Java 는 tree-sitter, Kotlin 은 렉시컬 파서) | `endpoints.json` |
| 2 | Claude 가 엔드포인트마다 컨트롤러 → 서비스 → 리포지토리를 따라가며 판정하고, 판정마다 `파일:줄` 증거를 남김 | `review/*.json` |
| 3 | `build_report.py` 로 보고서 생성 | 아래 5종 |
| 4 | P1·P2 요약 | — |

3단계의 산출물은 다음과 같다.

- `report.md`: 사람이 읽는 보고서
- `findings.csv`: 엑셀에서 한글이 깨지지 않도록 UTF-8 BOM 으로 저장
- `inventory.csv`: 전 엔드포인트 목록. *전수 점검했다는 증빙* 용도다.
- `report.sarif`: [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html) 형식이라 코드 스캐닝 도구에 넣을 수 있다.
- `testcases/*.http`: 계정 A 의 토큰으로 계정 B 의 ID 를 요청하는 차분 테스트

추출기는 일부러 까다로운 매핑을 다룬다. `@GetMapping({"/a", "/b"})` 같은 다중 경로, 주석 처리된 매핑,
메타 애노테이션으로 합성한 매핑, 인터페이스에 선언된 매핑이 여기에 들어간다. 또 Spring Data REST 가 리포지토리를
자동 노출한 경로와 Actuator 엔드포인트도 목록에 넣는다. 각각 OWASP API8(보안 설정 오류)·API9(자산 관리)에 해당한다.

## 4. 영향도와 우선순위를 분리한 점수 체계

이 스킬에서 가장 실무적이라고 본 설계다. **영향도는 코드와 데이터가 정하고, 환경은 우선순위만 바꾼다.**

- **영향도**: 응답 데이터 등급(R1~R4)이나 작업 종류로 정한다. 가중 요인이 두 개 있다.
  순차 정수 ID 에 호출량 제한이 없으면 +1 이다(1건 유출이 전량 유출로 이어진다). 응답이 마스킹돼 있으면 −1 이다.
- **환경 보정(하향)**: 노출 범위에 따라 인터넷 0, 파트너망·사내망 1, 폐쇄망+지정 단말 2단계를 내린다.
  호출 주체가 임직원이면 +1, IP 제한이 있으면 +1 을 더 내린다.
- 하향 폭은 `max_downgrade` (기본 2)로 상한을 둔다. **우선순위 = max(영향도 − 하향, 1)**, 즉 P1 아래로는 내려가지 않는다.
- P1 은 즉시, P2 는 다음 배포, P3 는 분기 내, P4 는 백로그로 조치한다.

그래서 쇼핑몰 주문 조회의 BOLA 는 인터넷 공개면 P1 이다. 똑같은 코드가 폐쇄망에 있으면 P3 로 내려가지만
보고서에는 **영향도 Critical 이 그대로 남는다.** "내부망이라 괜찮다"는 판단이 결함을 지우는 게 아니라
일정을 미루는 것일 뿐이라는 점을 숫자로 드러내는 구조다.
경로별로 환경을 달리 줄 수도 있다(예: `/admin/**` 는 사내망, `/api/**` 는 인터넷).

국내 규정도 반영한다. 프로필(`default.yaml`, `finance-kr.yaml`, `extends` 로 확장)에 따라 권고 문구와 참조 규정이 달라진다.
접속기록 보관 권고는 「개인정보의 안전성 확보조치 기준」 제8조를 따른다. 1년 이상 보관하되, 5만 명 이상의 정보주체를
처리하거나 고유식별정보·민감정보를 처리하는 시스템은 2년 이상이다
([국가법령정보센터](https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000281400&chrClsCd=010201), 개인정보보호위원회고시 제2026-9호, 2026-07-01 시행).

## 5. 직접 돌려 봤다

리포를 받아 의존성(tree-sitter 등)을 가상환경에 설치하고, 스킬에 동봉된 예제 쇼핑몰 프로젝트(`tests/fixtures/spring-boot-sample`)와
예제 판정 파일로 1단계와 3단계를 돌렸다. 2단계(Claude 의 판정)는 예제에 이미 들어 있는 판정 파일을 그대로 썼다.

**스킬 자체 테스트**는 `Ran 17 tests ... OK` 로 끝났다.

**1단계 탐색** 출력:

```
[api-authz-audit] 44 endpoints (16 controller) from 17 files
[api-authz-audit] parser: java:tree-sitter,kotlin:lexical; signals: actuator_exposed_all, cors_wildcard,
  data_rest_present, identity_header_read, method_security_disabled, none_rate_limit_in_code,
  pii_fields_in_responses, unverified_jwt, web_ignoring
[warn] Kotlin 파일은 lexical 파서로 분석했습니다 (v0.1). 복잡한 문법에서 엔드포인트를 놓칠 수 있으니 인벤토리를 확인하세요.
```

컨트롤러 엔드포인트 16개 외에 Spring Data REST 가 자동 노출한 `/orders`, `/orders/{id}`, `/orders/search/findByMemberNo` 와
`/actuator/env`·`/actuator/heapdump` 등 Actuator 경로까지 목록에 들어왔다. 코드에 `@GetMapping` 이 없어서
사람이 놓치기 쉬운 경로들이다.

**3단계 보고서**:

```
[api-authz-audit] findings: 10 (P1 4, P2 4, P4 2); coverage 10/42 (unreviewed 32)
[api-authz-audit] wrote report.md, findings.csv, inventory.csv, report.sarif, 2 test case file(s)
```

보고서 맨 위의 "가장 먼저 볼 것"은 이랬다.

> **[P1·즉시]** 로그인한 사용자가 주문 번호만 바꾸면 다른 회원의 주문(이름·연락처 포함)을 볼 수 있습니다.
> 소유권 검사 애노테이션은 있지만 메서드 시큐리티가 꺼져 있어 동작하지 않습니다. — `GET /api/v1/orders/{orderId}`

2절에서 말한 "선언만 된 보안"이 그대로 잡혔다. 영향도 근거에는 "응답 데이터 등급 R3, 순차 정수 ID 에 호출량 제한이 없어 +1"이
적혀 있었다. 또 하나 눈에 띈 것은 **"환경 답변과 코드가 다른 곳"** 섹션이다. 환경 문답에서는 "앞단이 사용자 식별 헤더를 넣지 않는다"고
답했는데, 코드는 `X-User-Id` 헤더로 사용자를 식별하고 있었다. 보고서는 그 위치를 `WebConfig.java:24` 처럼 줄 번호까지 짚었다.
사람이 한 답변을 코드로 반증하는 기능이다.

생성된 `.http` 테스트 파일 첫머리에는 이런 경고가 박혀 있다.

```
# api-authz-audit 차분 테스트 (WSTG-ATHZ-04)
# 자사 스테이징 환경에서만 실행하세요. 운영 환경과 실제 고객 데이터에는 사용하지 마세요.
```

테스트 설계는 [OWASP WSTG 의 IDOR 테스트(ATHZ-04)](https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References) 를 따른다.
스킬은 이 파일을 *만들기만 하고 실행하지 않는다.*

실측하면서 확인한 점이 두 가지 있다.

- 예제의 커버리지는 **10/42, 미검토 32** 다. 동봉된 판정 파일이 `OrderController` 하나뿐이라서다.
  실제로 쓸 때는 2단계에서 Claude 가 나머지를 모두 판정해야 하고, 그만큼 시간과 토큰이 든다. 보고서는 미검토 수를 숨기지 않고 요약 첫 줄에 적는다.
- 탐색기는 44개를 출력했는데 보고서는 42개를 기준으로 센다. 차이가 어디서 나는지는 이번에 확인하지 못했다.

## 6. 한계 — 스킬이 스스로 밝힌 것과 내가 덧붙이는 것

스킬 원문에 적힌 한계는 이렇다.

- **정적 분석이다.** 보고서 첫 줄에 "발견 사항 없음이 결함이 없다는 증명은 아니다"라고 박혀 있고, `없음` 과 `미확인` 을 구분한다.
- Kotlin 은 v0.1 에서 렉시컬 파서라 복잡한 문법에서 엔드포인트를 놓칠 수 있다(실행 중에도 경고를 띄운다).
- GraphQL, gRPC, WebFlux `RouterFunction` 은 자동 추출하지 않는다.

여기에 내가 덧붙이는 것은 다음과 같다.

- **판정 품질은 2단계의 LLM 에 달려 있다.** 증거로 `파일:줄` 을 남기게 강제하는 것은 좋은 장치지만, 증거가 판정의 정답을 보장하지는 않는다.
  P1·P2 는 사람이 해당 줄을 열어 확인하는 절차가 필요하다.
- 이 스킬의 탐지율·오탐률을 다른 도구(Semgrep, CodeQL 등)와 비교한 **중립적인 제3자 평가는 아직 없다.** 리포가 이틀 된 0.1.0 이다.
  "더 잘 찾는다"는 주장은 이 글에서 하지 않는다.
- 차분 테스트는 스테이징 전용이다. 계정 B 의 데이터를 바꾸는 쓰기 테스트(`PUT .../address`)가 포함돼 있으므로 운영 DB 에 돌리면 사고가 난다.

## 7. 정리

이 스킬의 값어치는 새로운 탐지 기법보다 **점검을 누락 없이, 근거를 남기며, 우선순위를 정직하게** 하도록 절차를 강제하는 데 있다.
엔드포인트 목록은 기계가 만들어 누락을 막는다. 판정에는 줄 번호 증거를 요구한다. 환경은 일정만 미룰 뿐 영향도를 지우지 못한다.
"`@PreAuthorize` 가 붙어 있으니 안전하다"는 말을 들었을 때, 메서드 시큐리티가 켜져 있는지부터 확인하는 습관을
도구로 옮겨 놓은 셈이다.

Spring Boot 2 에서 3으로 넘어가는 프로젝트라면 특히 써 볼 만하다. 메서드 시큐리티 기본값과 경로 매칭 기본값이
버전 사이에서 바뀌었기 때문이다(2절). 같은 코드가 다른 보안 동작을 하게 된다.

## References

1. heracul/skills — api-authz-audit (MIT, v0.1.0). <https://github.com/heracul/skills/tree/main/api-authz-audit>
2. OWASP, *API Security Top 10 2023*. <https://owasp.org/API-Security/editions/2023/en/0x11-t10/>
3. MITRE, *CWE-639: Authorization Bypass Through User-Controlled Key*. <https://cwe.mitre.org/data/definitions/639.html>
4. MITRE, *CWE-347: Improper Verification of Cryptographic Signature*. <https://cwe.mitre.org/data/definitions/347.html>
5. Spring Security Reference, *Method Security*. <https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html>
6. Spring Security API, *EnableMethodSecurity*. <https://docs.spring.io/spring-security/reference/api/java/org/springframework/security/config/annotation/method/configuration/EnableMethodSecurity.html>
7. Spring Security 5.8 API, *EnableGlobalMethodSecurity*. <https://docs.spring.io/spring-security/site/docs/5.8.x/api/org/springframework/security/config/annotation/method/configuration/EnableGlobalMethodSecurity.html>
8. spring-projects/spring-framework #28552, *Deprecate trailing slash match and change default value from true to false*. <https://github.com/spring-projects/spring-framework/issues/28552>
9. OWASP, *WSTG v4.2 — Testing for Insecure Direct Object References (WSTG-ATHZ-04)*. <https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References>
10. OASIS, *Static Analysis Results Interchange Format (SARIF) Version 2.1.0*. <https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html>
11. 개인정보보호위원회, 「개인정보의 안전성 확보조치 기준」 제8조(접속기록의 보관 및 점검), 고시 제2026-9호. <https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000281400&chrClsCd=010201>
