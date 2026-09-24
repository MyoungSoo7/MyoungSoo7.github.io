---
layout: post
title: "SonarCloud 보안 등급 A 인데 인가 구멍 넷이 운영에 들어갔다 — SAST 가 볼 수 없는 것"
date: 2026-09-24 19:57:07 +0900
categories: [Security]
tags: [SonarCloud, SAST, Access Control, Authorization, OWASP, Spring Security, SCA, CI]
---

12만 줄짜리 정산 리포지토리([settlement](https://github.com/MyoungSoo7/settlement))의 SonarCloud 대시보드는 오늘 기준 이렇다 — **Vulnerabilities 0, Security Rating A, Security Hotspots 0**. 그런데 같은 리포에서 지난 8월, 로그인만 하면 누구나 호출할 수 있는 관리자 경로가 네 곳이나 발견됐다. 쿠폰 발행, VAN 카드 거래 진입점, 포인트 운영 콘솔, 보험 언더라이팅 승인. **네 건 모두 컴파일도 테스트도 통과한 채 운영에 들어가 있었다.**

이 글은 SonarCloud 가 나빴다는 이야기가 아니다. Sonar 는 같은 기간에 진짜 취약점을 잡았다. 요점은 **"SAST 가 초록"이라는 말이 무엇을 보장하고 무엇을 보장하지 않는지**다. 앞서 쓴 [SonarCloud 품질 게이트 편](/2026/08/14/sonarcloud-quality-gate-what-it-actually-catches/)이 커버리지·New Code 같은 _품질_ 쪽 함정을 다뤘다면, 이번엔 _보안_ 쪽 한계만 다룬다.

## 1. 무엇을 풀려고 나온 도구인가

정적 분석(SAST)은 코드를 실행하지 않고 읽어서 결함 패턴을 찾는다. SonarQube Cloud 의 보안 규칙은 크게 두 부류다 — 외부 입력이 위험한 곳(SQL, 로그, 파일 경로)까지 흘러가는지 추적하는 **taint 분석(인젝션 계열)**, 그리고 약한 암호·잘못된 설정 같은 **패턴 규칙**이다([Sonar, Security-related rules](https://docs.sonarsource.com/sonarqube-cloud/standards/managing-rules/security-related-rules)).

이 도구가 바꾼 것은 분명하다. 사람이 리뷰에서 매번 놓치던 "요청값이 문자열 연결로 쿼리에 들어간다" 류의 _데이터 흐름_ 결함을, 모든 커밋에서 기계가 빠짐없이 본다.

## 2. 실제로 잡은 것 — 로그 인젝션 6곳

2026-08-12 분석에서 이 리포의 Vulnerabilities 는 **49건, Security Rating 은 E(4.0)** 였다(SonarCloud 공개 API `measures/search_history` 실측). 그 뒤 처리 커밋을 보면 성격이 둘로 갈린다.

- **진짜 결함 — `javasecurity:S5145` 로그 인젝션 6곳.** 사용자가 제어하는 값(DLQ 토픽명, 운영자 ID, PG 파일명 등)을 그대로 로그에 찍고 있었다. 값에 개행을 넣으면 `operator=admin, replayed=9999` 같은 **가짜 로그 줄**을 만들 수 있다. 감사 로그가 증거로 쓰이는 정산 도메인에선 증거 위조다. 공용 `LogSafe` 로 CR/LF·제어문자를 무력화해 닫았다(커밋 `d8f2a1a8`).
- **사람이 "안전하다"고 판정한 것 — 동적 SQL(`S2077`) 20곳, CSRF 비활성(`S4502`) 7곳, 임시파일(`S5443`) 1곳.** 이어 붙이는 건 코드 상수 식별자뿐이고 요청값은 전부 바인딩 파라미터로 간다는 것, 세션·쿠키 없는 토큰 API 라 CSRF 가 막을 대상이 없다는 것을 호출부 주석에 근거로 남기고 종결했다(커밋 `9e18531c`).

2026-09-01 분석에서 Vulnerabilities 는 0, 등급은 A 로 돌아왔다. 여기서 첫 번째 교훈이 나온다. **"0건"은 "결함 0"이 아니라 "기계 지적 + 사람 판정의 합계가 0"이다.** 동적 SQL 을 안전하다고 판정한 건 도구가 아니라 사람이고, 그 판정이 틀렸다면 대시보드는 여전히 A 다.

## 3. 못 잡은 것 — "이 경로는 ADMIN 이어야 한다"

인가 구멍 네 건의 공통 원인은 `SecurityConfig` 의 구조였다. 포괄적인 `/admin/**` 매처 없이 경로를 하나씩 열거하는데, 목록에서 빠진 경로는 **막히는 게 아니라 `anyRequest().authenticated()` 로 떨어진다.** 즉 "로그인만 하면 통과"다.

- 월마감·원장 기간마감 경로에 ADMIN 게이트가 없었다 — 일반 USER 토큰으로 월마감 실행 가능(`0279bad6`, 8/12)
- VAN 진입 경로(`/van/v1/*`)가 매처 목록에 없었다 — 사용자 JWT 로 카드 거래 위조 가능(`9738e160`, 8/13)
- 보험 언더라이팅 승인 무권한 호출 + 수수료 수령인(fcId) 조작(`78b91e41`, 8/14). 게다가 `@EnableMethodSecurity` 가 없어서 **`@PreAuthorize` 가 조용히 무시되고 있었다.**
- 쿠폰 발행 — 누구나 자기에게 100% 할인 쿠폰 발행 가능

이 코드들은 문법적으로 완벽하다. 오염된 입력이 위험한 싱크로 흐르지도 않는다. 결함은 **"이 URL 은 관리자 전용이어야 한다"는 의도**와 코드 사이의 불일치에 있는데, 그 의도는 코드 어디에도 적혀 있지 않다. 적혀 있지 않은 것을 정적 분석이 대조할 방법은 없다.

이건 이 도구 하나의 결함이 아니라 SAST 라는 범주의 알려진 한계다. OWASP 는 소스코드 분석 도구의 약점으로 **"인증 문제, 접근 제어 문제, 안전하지 않은 암호 사용 등은 자동으로 찾기 어렵다"**고 명시하고, 전체 보안 결함 중 비교적 작은 비율만 자동으로 찾을 수 있으며 설정 문제는 찾지 못하는 경우가 많다고 적는다([OWASP, Source Code Analysis Tools](https://owasp.org/www-community/Source_Code_Analysis_Tools)). `@EnableMethodSecurity` 누락이 정확히 "설정 문제"다 — 어노테이션은 있는데 그걸 켜는 스위치가 없는 상태.

Sonar 스스로도 설계 방향을 밝힌다. 이슈 탐지는 오탐을 최소화하기 위해 **"의도적으로 보수적(purposely conservative)"**으로 설계됐다([Sonar, What SonarQube Cloud can do](https://docs.sonarsource.com/sonarqube-cloud/discovering-sonarcloud/what-sonarcloud-can-do)). 취약점 규칙의 목표가 참양성 80% 이상이라는 것도 문서에 있다([Sonar, Rules](https://docs.sonarsource.com/sonarqube-cloud/standards/managing-rules/rules)). 오탐을 줄이는 쪽으로 기울인 도구는 **미탐(false negative)을 감수**한 도구다. "등급 A"는 "도구가 확신할 수 있는 범위 안에서 문제 없음"이지 "문제 없음"이 아니다.

> 공정하게 적어 둔다. 이 네 건이 _분석된 코드 안에서_ Sonar 가 놓친 것인지는 엄밀히 증명하지 못한다. 이 리포의 분석 이력은 2/24 → 8/12 → 9/1 → 9/24 로 듬성듬성하다(아래 5절). 확실히 말할 수 있는 건 **해당 경로들이 운영에 있는 동안 보안 등급이 이 결함을 반영한 적이 없고, 반영할 수 있는 규칙 부류도 없다**는 것이다.

## 4. 요금제가 가리는 것 — 운영 브랜치는 분석 대상이 아니다

이 리포는 `develop`(CI·검증)과 `main`(배포) 두 브랜치를 쓴다. SonarCloud 공개 API 로 `main` 을 조회하면 이렇게 거절된다.

```
Organization is not allowed to access data from non main branches
```

Sonar 문서의 요금제 표에 그대로 있다. **Free 플랜은 "Only main branch analysis"**, PR 분석도 대상 브랜치가 main 일 때만이다([Sonar, Subscription plans](https://docs.sonarsource.com/sonarqube-cloud/administering-sonarcloud/managing-subscription/subscription-plans)). 여기서 Sonar 의 "main 브랜치"는 _Sonar 프로젝트에 지정된 기본 브랜치_(이 리포에선 develop)를 뜻한다. 결과적으로 **실제로 배포되는 `main` 의 코드는 한 번도 Sonar 가 보지 않는다.** develop 이 초록이면 main 도 괜찮으리라는 가정 위에 서 있는 셈이다.

의존성 쪽도 마찬가지다. 라이브러리 CVE·악성 패키지·SBOM 을 다루는 SCA 와, 의존성 코드 안까지 taint 를 추적하는 Advanced SAST 는 **Advanced Security 라는 별도 구독**이다([Sonar, Advanced Security](https://docs.sonarsource.com/sonarqube-cloud/advanced-security/introduction)). 이 리포에서 Spring Boot 를 올려 의존성 취약점 48건 중 40건을 없앤 건(`f32b2351`) Sonar 가 아니라 CI 의 Trivy 였다. **Free 플랜의 "Vulnerabilities 0"에는 의존성 취약점이 애초에 들어있지 않다.**

> 공개 리포라면 OSS 플랜으로 브랜치·PR 분석이 무제한이다(같은 요금제 문서). 이 리포는 최근 public 으로 전환했으므로 이 제약은 풀 수 있는 제약이다 — 다만 전환 전 기간 동안 그랬다는 사실은 남는다.

## 5. 파이프라인이 가리는 것 — 초록은 "실패하지 않았다"일 뿐

도구의 한계보다 더 조용한 건 파이프라인 쪽이었다. CI 설정 주석과 커밋에 남은 실제 사례들.

| 무슨 일이 있었나 | 결과 |
| --- | --- |
| Gradle 9 에서 sonarqube 플러그인이 크래시 → `continue-on-error` 가 삼킴 | 분석 결과가 업로드되지 않았는데 잡은 초록 |
| 2/24 등록한 `SONAR_TOKEN` 만료 → HTTP 403 | 마지막 분석이 2/26 에 멈춤. 그리고 **같은 잡 안에서 뒤따르던 SBOM 생성·Trivy SCA 단계까지 건너뜀** |
| 커버리지 리포트 없이 돈 분석이 게이트를 덮어씀 | develop 게이트가 ERROR(new_coverage 79.8%) → OK 로 뒤집힘 (8/22) |
| `sonar.qualitygate.wait=false` | 게이트가 빨개도 머지는 막히지 않음 |

두 번째 줄이 가장 아프다. **보안과 무관한 인증 실패 하나가 보안 게이트(SCA)를 통째로 꺼 버렸다.** 그래서 SCA 단계를 Sonar 앞으로 옮겼다(`5bac1b75`). 3절의 인가 구멍은 "도구가 못 보는 것"이고, 이 표는 "도구가 볼 수 있었는데 안 돈 것"이다. 대시보드에서는 둘 다 똑같이 초록으로 보인다.

## 6. 그래서 무엇을 더했나 — 의도를 코드로 적는다

SAST 가 의도를 모르면, 의도를 **실행 가능한 형태로 적어 주면** 된다. 인가 구멍 네 건 이후 세운 `SecurityAuthorizationMatrixTest` 는 실제 `springSecurityFilterChain` 에 요청을 흘려 **상태코드로 판정을 읽는다** — 미인증 401, 권한 부족 403, 통과 200. 경로×역할 조합 32케이스, 과거 누출된 네 경로를 포함한다(`7359d421`).

이 테스트를 세우기 전에 일부러 `/api/reports/**` 매처 한 줄을 지워 봤다. 22건 중 6건이 깨졌는데, 실패 메시지가 이랬다.

```
expected 403 but was 200
```

403 도 500 도 아니고 **200** 이다. 매처가 빠지면 에러가 나는 게 아니라 _조용히 열린다_. 이게 이 설정의 실패 모드이고, 기존 테스트(필터 체인이 "빌드되는지"만 보던)가 네 번 다 초록이었던 이유다.

정리하면 역할 분담은 이렇다.

| 결함 부류 | 잡는 수단 |
| --- | --- |
| 입력 → 위험 싱크 (SQL·로그·경로 인젝션) | SAST (Sonar taint) — 실제로 잡았다 |
| 의존성 CVE·악성 패키지 | SCA (여기선 Trivy, Sonar 는 유료 애드온) |
| "이 경로는 누가 호출할 수 있어야 하나" | **인가 매트릭스 테스트** — 사람이 의도를 표로 적고 기계가 대조 |
| 스위치 누락 (`@EnableMethodSecurity` 등) | 설정 존재 자체를 어서트하는 테스트, 또는 사람 리뷰 |
| 파이프라인이 조용히 안 돈 것 | 분석 _결과_ 가 새로 생겼는지 확인 (잡 성공 ≠ 분석 성공) |

## 7. 새로 생긴 비용

- **매트릭스는 손으로 유지해야 한다.** 새 관리자 경로를 추가하면서 매트릭스에 안 넣으면 똑같이 조용히 열린다. 근본 해법은 열거형 매처를 포괄 매처(`/admin/**` 거부 기본값)로 바꾸는 것이고, 테스트는 그 전까지의 안전망이다.
- **"안전함" 판정은 부채다.** CSRF 억제 근거는 "세션 인증이 없다"는 전제 위에 있다. 세션 인증을 도입하는 날 그 7곳의 억제는 무효가 된다 — 그래서 각 지점에 그 조건을 적어 두었지만, 적어 둔 걸 읽는 건 여전히 사람이다.
- **등급 하나로 말할 수 없게 된다.** "Sonar A 니까 안전하다" 대신 "taint 계열은 Sonar, 의존성은 Trivy, 인가는 매트릭스 32케이스, main 브랜치는 미분석"이라고 말해야 한다. 길어지지만 그게 실제 상태다.

## 8. 이 글의 한계

- 사례는 **리포 하나**다. SAST 의 인가 결함 탐지율에 대한 일반 통계를 제시하지 않는다 — 텍스트로 검증 가능한 중립 제3자 비교 수치를 찾지 못했다.
- 49건의 규칙별 전체 내역은 공개 API 로 다 보이지 않는다(현재 조회되는 건 해소된 `S2077` 9건). 2절의 분류는 처리 커밋 메시지 기준이다.
- Sonar 유료 플랜(Advanced SAST 등)이 이 인가 구멍을 잡았을지는 **검증하지 않았다.** 다만 3절의 논리 — 의도가 코드에 없으면 대조할 대상이 없다 — 는 도구 등급과 무관하다.

## 한 줄

**SAST 의 초록은 "도구가 아는 결함 부류 안에서, 분석이 실제로 돌았다면, 문제가 안 보였다"이다.** 세 개의 조건 중 어느 하나라도 빠지면 등급 A 는 아무것도 말하지 않는다. 특히 "누가 이걸 호출해도 되는가"는 코드가 아니라 사람의 머릿속에 있고, 그걸 꺼내 테스트로 적기 전까지는 어떤 스캐너도 대신 봐주지 않는다.

## References

1. OWASP Foundation, *Source Code Analysis Tools* — 강점·약점(접근 제어·인증·설정 문제 탐지 한계). <https://owasp.org/www-community/Source_Code_Analysis_Tools>
2. Sonar, *Subscription plans* (SonarQube Cloud docs) — Free: "Only main branch analysis", PR 분석 조건, OSS 플랜. <https://docs.sonarsource.com/sonarqube-cloud/administering-sonarcloud/managing-subscription/subscription-plans>
3. Sonar, *Introduction to Advanced Security* — SCA·Advanced SAST 범위(별도 구독). <https://docs.sonarsource.com/sonarqube-cloud/advanced-security/introduction>
4. Sonar, *Security-related rules* — injection(taint) 규칙과 기타 보안 규칙 구분. <https://docs.sonarsource.com/sonarqube-cloud/standards/managing-rules/security-related-rules>
5. Sonar, *Rules* — 취약점 규칙 참양성 목표 80% 이상, 핫스팟 정의. <https://docs.sonarsource.com/sonarqube-cloud/standards/managing-rules/rules>
6. Sonar, *What SonarQube Cloud can do* — 탐지는 오탐 최소화를 위해 "purposely conservative". <https://docs.sonarsource.com/sonarqube-cloud/discovering-sonarcloud/what-sonarcloud-can-do>
7. 1차 데이터: SonarCloud 공개 Web API (`api/measures/search_history`, `api/project_analyses/search`, `api/issues/search`), 프로젝트 `MyoungSoo7_settlement`, 2026-09-24 조회.
8. 1차 데이터: settlement 리포 커밋 `0279bad6`, `9738e160`, `78b91e41`, `7359d421`, `d8f2a1a8`, `9e18531c`, `5bac1b75`, `f32b2351` 및 `.github/workflows/ci.yml` 주석. <https://github.com/MyoungSoo7/settlement>
