---
layout: post
title: "SonarCloud 를 CI 에 붙이면 실제로 뭐가 잡히나 — 10만 줄 리포의 게이트를 열어봤다"
date: 2026-08-14 13:50:00 +0900
categories: [ci, quality]
tags:
  [sonarcloud, sonarqube, quality-gate, jacoco, code-coverage, static-analysis, sbom, trivy, github-actions]
---

## 0. 이 글이 답하려는 것

정적 분석 도구를 CI 에 붙이자는 말은 쉽다. 붙이면 **무엇이 실제로 잡히고, 무엇은 안 잡히며, 어디서 조용히 실패하는가**가 어려운 부분이다.

마침 손에 실물이 있다. 20개 남짓한 Gradle 모듈로 된 정산 시스템 리포에 SonarCloud 가 붙어 있고, 그 프로젝트는 공개라 누구나 Web API 로 상태를 조회할 수 있다. 그래서 이 글의 수치는 전부 조회 가능한 값이다. 명령도 같이 적어둔다.

---

## 1. 그 잡 하나가 실제로 하는 일

GitHub Actions 잡 이름은 `Backend - Build/Test/JaCoCo/SonarCloud` 하나지만, 안에서 다섯 단계가 순서대로 돈다.

1. **변경된 모듈만 빌드·테스트** — 전체 모듈을 매번 돌리지 않는다
2. **JaCoCo 커버리지 리포트 수집** — 테스트가 어느 줄을 실행했는지 XML 로 남긴다
3. **SBOM 생성 (CycloneDX)** — 이 빌드에 들어간 의존성 전체를 기계가 읽는 목록으로 뽑는다[^4]
4. **Trivy SCA 스캔** — 그 SBOM 을 훑어 HIGH/CRITICAL 취약점이 있으면 막는다[^5]
5. **SonarCloud 분석** — 소스를 정적 분석해 sonarcloud.io 로 올린다

순서에 의미가 있다. 이 리포의 워크플로 주석에는 **SCA(보안 게이트)를 SonarCloud(품질 분석)보다 먼저** 둔 이유가 적혀 있다. 과거에 Sonar 스텝이 토큰 문제로 실패하자 뒤따르던 SBOM·Trivy 가 통째로 skip 됐기 때문이다. 무관한 도구의 인증 실패가 보안 게이트를 건너뛰게 만드는 배치는 그 자체로 결함이다.

---

## 2. Sonar 가 보는 것 — 그리고 사람이 못 보는 것

SonarCloud 는 코드를 실행하지 않고 읽어서 문제를 찾는다. 크게 넷이다.

- **Bugs** — 논리 오류. NPE 가능 지점, 도달 불가능한 코드, `equals` 만 오버라이드하고 `hashCode` 는 안 한 클래스
- **Vulnerabilities** — SQL 인젝션, 하드코딩된 자격증명, 안전하지 않은 난수
- **Code Smells** — 동작은 하지만 유지보수를 갉아먹는 것. 과도한 인지 복잡도, 중복 블록
- **Coverage / Duplication** — 테스트가 닿지 않는 코드, 복붙 비율

여기서 중요한 건 "사람이 더 잘 본다 / 못 본다"가 아니라 **전수성(exhaustiveness)** 이다. 리뷰어는 PR 의 diff 를 본다. 97,388 줄짜리 리포에서 NPE 가능 지점을 전수로 훑는 건 사람이 할 수 있는 일이 아니다. 반대로 "이 도메인에서 이 계산이 말이 되는가"는 도구가 못 본다. 둘은 대체재가 아니라 역할이 다르다.

보안 이슈는 특히 시점이 중요하다. 하드코딩된 토큰이 커밋되면 그 순간 git 히스토리에 영구히 박힌다. 되돌리는 건 커밋 되돌리기가 아니라 **자격증명 폐기**다. 머지 전에 걸리는 것과 머지 후에 걸리는 것의 비용 차이가 여기서 갈린다.

---

## 3. 핵심 개념은 "New Code" 다

SonarCloud 를 그냥 "린터 붙이기"로 이해하면 대개 실패한다. 6개월 묵은 리포에 붙이면 수천 건이 쏟아지고, 아무도 그걸 다 고치지 않으며, 결국 경고를 끈다.

Sonar 의 설계는 그 실패를 피하려고 만들어져 있다. 공식 문서는 이렇게 말한다.

> 새 코드를 분석하고 정리하다 보면 그 과정에서 과거 코드도 손대게 되고, 결과적으로 코드베이스 전체 품질이 점진적으로 개선된다.[^3]

**New Code** 는 최근에 추가·수정된 코드다. 기준은 네 가지 중 하나로 정한다: 이전 버전(Previous version), 최근 N일(Number of days, 기본 30일·최대 90일), 특정 버전, 특정 날짜.[^3]

그리고 기본 게이트인 **Sonar way** 는 조건을 **새 코드에만** 건다. 조건은 이렇다.[^2]

- 새 버그 없음 (Reliability rating A)
- 새 취약점 없음 (Security rating A)
- 새 코드의 기술부채 제한 (Maintainability rating A)
- 새 Security Hotspot 전부 리뷰 완료
- **새 코드 테스트 커버리지 80% 이상**
- **새 코드 중복 3% 이하**

그래서 "레거시를 다 고쳐야 도입할 수 있다"가 아니라 "오늘부터 새로 쓰는 코드는 깨끗하게"가 성립한다. PR 분석에서는 새 코드 조건만 적용되고, 새 코드의 정의도 **대상 브랜치 대비 변경분**으로 바뀐다.[^2]

---

## 4. 실측 — 게이트를 열어보면 이렇게 생겼다

이론은 여기까지. 실제 값을 보자. 아래는 2026-08-14 13:41 KST 분석 기준이고, 공개 API 라 그대로 재현된다.

```bash
curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=MyoungSoo7_settlement"
```

| 조건 | 임계값 | 실제 | 판정 |
| --- | --- | --- | --- |
| new_reliability_rating | A(1) | **3 (C)** | ERROR |
| new_security_rating | A(1) | **4 (D)** | ERROR |
| new_maintainability_rating | A(1) | 1 (A) | OK |
| new_coverage | ≥ 80% | **84.3%** | OK |
| new_duplicated_lines_density | ≤ 3% | 2.1% | OK |
| new_security_hotspots_reviewed | 100% | 100% | OK |

전체 status 는 **ERROR**. 6개 중 4개는 통과했는데 2개가 못 넘었다. 그리고 이 표가 정확히 게이트의 쓸모다. "코드 품질이 안 좋다" 같은 뭉뚱그린 말 대신 **못 넘은 조건이 두 개고 그게 무엇인지**가 나온다.

전체 코드 기준 수치도 같이 뽑아봤다.

```bash
curl -s "https://sonarcloud.io/api/measures/component?component=MyoungSoo7_settlement&metricKeys=ncloc,coverage,bugs,vulnerabilities,code_smells,duplicated_lines_density"
```

- 분석 대상 97,388 줄
- 커버리지 84.4%
- 버그 18건 · 취약점 46건 · 코드 스멜 2,638건
- 중복 3.9%

커버리지 84% 를 유지하면서도 신뢰성 C, 보안 D 가 나온다. **테스트가 많다는 것과 코드가 안전하다는 것은 다른 축**이라는 게 숫자로 보인다. 이게 커버리지 하나만 게이트로 걸면 안 되는 이유다.

---

## 5. 함정 셋 — 조용히 실패하는 지점

### 함정 1. 커버리지 0% 는 대개 테스트가 없어서가 아니다

Sonar 는 커버리지를 **직접 측정하지 않는다.** 공식 문서가 명시한다.

> SonarQube Cloud 는 커버리지 리포트를 스스로 만들지 않는다. 서드파티 도구가 빌드 과정에서 리포트를 생성하게 하고, 스캐너에게 그 위치를 알려줘야 한다.[^1]

즉 JaCoCo 로 XML 을 만들었어도 `sonar.coverage.jacoco.xmlReportPaths` 로 경로를 연결하지 않으면 **커버리지는 0% 로 표시된다.** 테스트를 열심히 짜놓고 대시보드에서 0% 를 보는 상황이 여기서 나온다. 그리고 이건 에러가 아니라 그냥 0 이어서, 아무도 알려주지 않는다.

Gradle 이라면 최소 형태는 이렇다.[^1]

```kotlin
plugins {
    jacoco
    id("org.sonarqube") version "<버전>"
}

tasks.jacocoTestReport {
    reports { xml.required = true }
}
```

멀티모듈이면 모듈별 XML 경로를 각각 넘겨야 한다. 그리고 **JaCoCo 리포트 생성이 Sonar 스캔보다 먼저** 실행돼야 한다. 순서가 뒤집히면 스캐너가 아직 없는 파일을 찾는다.

### 함정 2. New Code 기준선이 낡으면 "새 코드"가 전체가 된다

앞의 실측에서 새 코드 커버리지(84.31%)와 전체 커버리지(84.4%)가 거의 같다. 버그도 18건 중 18건이 "새 버그"로 잡혔다. 왜인가.

이 프로젝트의 새 코드 기준은 `previous_version` 이고, 기준 날짜가 **2026-02-24** 다. 즉 반년 가까이 버전 증가가 없었고, 그동안의 모든 변경이 "새 코드"로 분류된다. New Code 게이트의 장점 — 오래된 부채를 면제해주는 성질 — 이 사실상 꺼져 있는 상태다.

이건 도구 결함이 아니라 설정 문제다. `sonar.projectVersion` 을 릴리스마다 올리거나, 새 코드 정의를 "최근 30일" 같은 값으로 바꾸면 해결된다. 다만 **바꾸는 순간 게이트 판정이 달라진다**는 걸 알고 바꿔야 한다.

### 함정 3. 분석이 도는 것과 게이트가 막는 것은 별개다

가장 흔한 오해다. Sonar 스텝이 초록이면 품질 게이트를 통과했다고 생각하기 쉽지만, 기본값은 그렇지 않다. 스캐너는 결과를 **올리고 끝난다.**

파이프라인을 실제로 실패시키려면 `sonar.qualitygate.wait=true` 를 줘야 한다. 이 값을 켜면 스캐너가 게이트 결과가 나올 때까지 폴링하고, 게이트가 실패하면 분석 자체는 성공했어도 스텝을 실패시킨다. 대기 시간은 `sonar.qualitygate.timeout` 으로 조절하며 기본 300초다.[^6]

앞의 리포는 이 값을 **일부러 `false` 로 두고 있다.** 지금 켜면 reliability C·security D 때문에 모든 빌드가 즉시 막힌다. 대신 스텝의 `continue-on-error` 는 제거해서, **분석 자체가 실패하는 것(토큰 만료·플러그인 크래시)은 빌드를 깨도록** 해뒀다.

이 구분이 실무적으로 중요하다.

- **분석이 안 도는 것** → 즉시 차단해야 한다. 안 그러면 게이트가 꺼진 줄도 모르고 몇 달이 간다
- **게이트 내용이 실패하는 것** → 단계적으로 조인다

조이는 순서도 정해두는 게 좋다. ① 커버리지 연결을 먼저 정상화하고 → ② 신뢰성·보안 등급을 A 로 만들고 → ③ 그때 `wait=true` 로 잠근다. 순서를 뒤집으면 첫날부터 아무도 머지를 못 하고, 그러면 사람들은 게이트를 끈다.

---

## 6. 그래서 붙이면 뭐가 좋은가

정리하면 다섯 가지다.

- **전수성** — 사람이 diff 를 보는 동안 도구는 10만 줄을 본다. 역할이 다르다
- **시점** — 보안 이슈가 머지 전에 걸린다. 커밋된 시크릿은 되돌릴 수 없고 폐기해야 한다
- **측정 가능한 언어** — "테스트 짰습니다"가 "이 PR 의 새 코드 84.3% 커버, 임계 80%"로 바뀐다. 논쟁이 협상에서 판정으로 바뀐다
- **부채의 방향** — New Code 게이트는 전체를 요구하지 않고 증분만 요구한다. 그래서 계속 지킬 수 있다
- **역량의 증거** — 테스트·정적분석·SCA·SBOM 을 한 파이프라인에 배선하고, 각각을 언제 차단하고 언제 경고만 할지 구분한 흔적 자체가 포트폴리오다

마지막 항목을 조금 더 말하면, 도구를 붙였다는 사실보다 **왜 이 게이트는 켜고 저 게이트는 껐는지 설명할 수 있는가**가 실제 신호다. 전부 켜는 건 쉽고, 전부 끄는 것도 쉽다. 어려운 건 순서를 정하는 것이다.

---

## 7. 이 글의 한계

- 실측 수치는 공개 프로젝트 하나(`MyoungSoo7_settlement`)의 2026-08-14 13:41 KST 분석 기준이다. 이후 분석에서 값은 바뀐다. 위 `curl` 로 현재 값을 확인할 수 있다.
- Sonar way 조건과 New Code 정의는 SonarQube Cloud 공식 문서 기준이다. SonarQube Server(자체 호스팅) 는 버전에 따라 다를 수 있다.
- "정적 분석이 잡는 것 / 못 잡는 것"의 경계는 규칙 세트(Quality Profile)에 달렸다. 이 글은 기본 프로파일을 전제한다.
- 도구 간 우열은 다루지 않았다. SonarCloud 와 다른 정적 분석 도구를 같은 코드베이스에 돌려 비교한 중립적 실측은 이 글에 없다.
- SBOM·Trivy 단계는 파이프라인 맥락으로만 언급했고, 취약점 탐지율 같은 수치는 측정하지 않았다.

---

## 8. 한 줄

**게이트를 붙였느냐가 아니라, 무엇을 차단하고 무엇을 아직 차단하지 않는지 말할 수 있느냐가 실력이다. 그리고 제일 위험한 상태는 게이트가 빨간 것이 아니라, 꺼져 있는 줄 모르는 것이다.**

---

## References

1. SonarSource, _Java test coverage_ — SonarQube Cloud 는 커버리지 리포트를 직접 생성하지 않으며, JaCoCo XML 경로를 스캐너에 알려줘야 한다. Gradle 설정 예시 포함. <https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/test-coverage/java-test-coverage/>
2. SonarSource, _Understanding quality gates_ — Sonar way 기본 게이트 조건(신뢰성·보안·유지보수 A, 핫스팟 100% 리뷰, 새 코드 커버리지 80%, 중복 3%)과 PR 분석 시 새 코드 조건만 적용된다는 규칙. <https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates/>
3. SonarSource, _Quality standards and new code_ — New Code 정의 네 가지(Previous version / Number of days 기본 30일·최대 90일 / Specific version / Specific date). <https://docs.sonarsource.com/sonarqube-cloud/standards/about-new-code/>
4. OWASP, _CycloneDX Specification Overview_ — SBOM 표준 사양. <https://cyclonedx.org/specification/overview/>
5. Aqua Security, _Trivy — SBOM scanning_ — SBOM 파일을 입력으로 취약점을 스캔하는 공식 사용법. <https://trivy.dev/latest/docs/target/sbom/>
6. SonarSource, _CI integration overview_ — `sonar.qualitygate.wait=true` 는 게이트 결과를 폴링해 실패 시 파이프라인을 실패시키며, `sonar.qualitygate.timeout` 기본값은 300초. <https://docs.sonarsource.com/sonarqube-server/latest/analyzing-source-code/ci-integration/overview/>
7. SonarCloud Web API — `api/qualitygates/project_status`, `api/measures/component`, `api/project_analyses/search` (2026-08-14 조회). <https://sonarcloud.io/web_api>

관련 글: [사고는 층과 층 사이에서 난다 — 홈랩 K3s 장애를 '어느 문서를 안 읽었나'로 분류했다]({% post_url 2026-08-13-incidents-between-layers-which-doc %})
