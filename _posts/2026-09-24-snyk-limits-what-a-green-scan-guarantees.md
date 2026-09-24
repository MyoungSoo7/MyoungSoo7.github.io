---
layout: post
title: "Snyk 의 한계 — 스캐너가 초록불을 켰을 때 실제로 보증하는 건 무엇인가?"
date: 2026-09-24 19:57:32 +0900
categories: [Security, DevSecOps]
tags: [Snyk, SCA, SAST, Supply Chain, Reachability, CI/CD, DevSecOps]
---

CI 파이프라인에서 `snyk test` 가 0으로 끝나면 대부분의 팀은 "보안 통과" 라고 읽는다. 이 글의 주장은 간단하다. **그 0은 "안전하다" 가 아니라 "Snyk 가 스캔한 범위 안에서, Snyk DB 가 알고 있는 취약점이, Snyk 가 그린 의존성 그래프에서 발견되지 않았다" 는 뜻이다.** 조건이 세 개 붙는다.

Snyk 는 좋은 도구다. 다만 좋은 도구일수록 그 결과를 과하게 믿기 쉽다. 아래는 Snyk 공식 문서와 중립적인 연구가 직접 밝히는 한계를 층위별로 정리한 것이다.

| 층위 | Snyk 가 하는 일 | 보증하지 않는 것 |
|---|---|---|
| 1. 취약점 DB | 알려진 취약점과 버전 범위 매칭 | 아직 공개되지 않은 취약점, 다른 DB 에만 있는 취약점 |
| 2. 의존성 그래프 | manifest·lockfile 로 그래프 추론 | 실제 빌드 환경과 똑같은 그래프 |
| 3. Reachability | 호출 경로가 **있음**을 증명 | 호출 경로가 **없음**을 증명 |
| 4. SAST (Snyk Code) | 코드 패턴·데이터 흐름 분석 | 인가·비즈니스 로직·설정 결함 |
| 5. 운영 | ignore·exit code·PR check | 사람이 끈 경고, 스캔되지 않은 프로젝트 |

## 1. 취약점 DB — 도구마다 "알려진 취약점" 이 다르다

SCA(Software Composition Analysis) 도구의 본질은 **"내 의존성 목록 × 취약점 DB" 의 조인**이다. 따라서 결과의 상한은 DB 가 정한다.

NC State 의 Imtiaz·Thorne·Williams 는 ESEM 2021 에서 업계 SCA 도구 9종을 같은 애플리케이션(OpenMRS)에 돌려 비교했다. 결과는 도구마다 크게 달랐다.[^imtiaz]

> *"The count of reported vulnerable dependencies ranges from 17 to 332 for Maven and from 32 to 239 for npm projects across the studied tools."*

같은 코드, 같은 의존성인데 취약 의존성 수가 17 에서 332 까지 벌어진다. 연구진은 차이의 핵심을 **취약점 DB 의 정확도**로 보았고, 결론은 명확했다.

> *"We recommend that practitioners should not rely on any single tool at the present, as that can result in missing known vulnerabilities."*

Snyk 는 자사 DB 에 대해 *"All items in the database are analyzed and verified"* 이고 *"eliminates false positives"* 한다고 설명한다.[^snykdb] 이건 **벤더 주장**이다. 수동 큐레이션은 분명히 품질을 올리지만, 위 연구가 보여주듯 "어느 한 DB 가 전부를 안다" 는 근거는 없다.

그리고 어떤 DB 든 **공개된 뒤에야** 안다. 2024년 3월 xz/liblzma 백도어는 오픈소스 메일링 리스트에 공개된 순간까지 어떤 SCA DB 에도 없었다.[^xz] 공급망 공격의 가장 위험한 구간은 정의상 스캐너의 사각지대다.

## 2. 의존성 그래프 — Snyk 가 본 그래프는 내 빌드와 다를 수 있다

Snyk 는 공식 문서에서 환경별로 취약점 개수가 다를 수 있다고 따로 설명한다.[^snykdiff] 핵심 문장은 이것이다.

> *"A Snyk SCM Integration does not have access to private dependencies or the specifics of your build environment, such as environment variables. Hence the results may be partial..."*

즉 GitHub 연동으로 Snyk 가 저장소를 스캔할 때 보는 그래프는 **빌드 도구의 동작을 근사한 것**이다. 같은 문서는 lockfile 이 있으면 훨씬 결정적인 그래프를 얻는다고 권한다.

실무적 함의:

- **lockfile 을 커밋하지 않는 프로젝트**는 스캔 결과가 실제 설치 버전과 어긋날 수 있다.
- **private registry 의존성**은 SCM 연동 스캔에서 빠질 수 있다. CLI 를 빌드 환경 안에서 돌려야 한다.
- 웹 UI 의 숫자와 CI 의 숫자가 다르면 버그가 아니라 **서로 다른 그래프를 본 것**이다.

## 3. Reachability — "경로 없음" 은 "안전" 이 아니다

취약점 경보 피로를 줄이려고 Snyk 는 reachability 분석을 제공한다. 취약한 함수까지 내 코드에서 호출 경로가 있는지 본다. 상태는 세 가지다: `REACHABLE`, `NO PATH FOUND`, `NOT APPLICABLE`.[^snykreach]

문제는 두 번째 상태의 해석이다. Snyk 문서 스스로 이렇게 적는다.

> *"A vulnerability with the status NO PATH FOUND it does not mean that the vulnerability is completely unreachable or unexploitable."*

> *"Static analysis techniques can show that a vulnerability or code element can be reached through at least one execution path. However, just because there is no evidence of this does not mean that the element cannot be reached."*

정적 분석은 **존재 증명에는 강하고 부재 증명에는 약하다.** 리플렉션, 동적 디스패치, 직렬화, DI 컨테이너, 설정 파일로 로딩되는 클래스 — 자바·스프링 생태계에서 흔한 것들 — 이 전부 호출 그래프를 흐린다. 문서도 리플렉션을 정확한 답을 주기 어려운 예로 직접 든다.

그래서 "NO PATH FOUND 는 백로그로" 라는 정책은 합리적일 수 있어도, **"NO PATH FOUND 는 무시"** 는 문서가 명시적으로 권하지 않는 해석이다.

## 4. SAST — 코드가 말하지 않는 취약점은 못 본다

Snyk Code 는 SAST 도구다. Snyk 는 AI 기반 엔진이 오탐을 줄인다고 설명하지만(벤더 주장),[^snykcode] SAST 라는 범주 자체의 한계는 엔진과 무관하다. OWASP 는 SAST 의 약점을 이렇게 정리한다.[^owaspsast]

- 인증 문제, **접근 제어 결함**, 암호 오용은 자동 탐지가 어렵다.
- *"Current SAST tools are limited. They can automatically identify only a relatively small percentage of application security flaws."*
- *"Frequently unable to find configuration issues, since they are not represented in the code."*

실제 사고를 생각해 보면 이 목록이 아프다. "로그인한 사용자가 남의 주문 ID 를 넣으면 조회된다" 같은 IDOR 은 코드 패턴으로는 **정상적인 조회 쿼리**다. 틀린 건 코드가 아니라 **빠진 소유권 검사**이고, 빠진 것은 패턴으로 잡기 어렵다. 쿠버네티스 매니페스트의 과도한 RBAC, 퍼블릭으로 열린 버킷 정책도 애플리케이션 코드에 없다.

또 하나: Snyk Code 의 기본 동작은 **코드를 Snyk 로 업로드해 분석**한다. 업로드 없이 도는 Local Engine 이 있었지만, 문서에 따르면 *"Snyk is not onboarding new Local Engine deployments."*[^snykscle] 소스 반출이 규제상 어려운 조직이라면 도입 전에 확인해야 할 제약이다.

## 5. 운영 — 도구보다 사람이 끄는 경보가 더 많다

### ignore 는 기본이 영구다

`.snyk` 파일로 이슈를 무시할 때 **`expires` 필드는 선택**이고, 생략하면 영구 ignore 가 된다.[^snykignore] 또 SCM 프로젝트와 CLI 프로젝트의 ignore 는 서로 영향을 주지 않는 별개 설정이다. 한쪽에서 끈 경보가 다른 쪽에선 살아 있거나, 그 반대가 된다.

"일단 ignore, 나중에 보자" 가 1년 쌓이면 그 저장소의 실제 보안 상태는 대시보드가 아니라 `.snyk` 파일에 적혀 있다.

### exit code 를 정확히 읽는다

`snyk test` 의 종료 코드는 네 가지다.[^snyktest]

| 코드 | 의미 |
|---|---|
| 0 | 스캔 완료, 취약점 없음 |
| 1 | 스캔 완료, 취약점 발견 |
| 2 | 실패 — 재실행 필요 |
| 3 | 실패 — **지원되는 프로젝트를 찾지 못함** |

CI 스크립트가 `|| true` 로 감싸져 있거나 "1이 아니면 통과" 로 짜여 있으면, **아무것도 스캔하지 못한 3** 도 초록불이 된다. 모노레포에서 디렉터리를 옮긴 뒤 조용히 스캔이 사라지는 전형적인 경로다.

## 6. 그래서 어떻게 쓸 것인가

1. **lockfile 을 커밋하고, CLI 를 실제 빌드 환경에서 돌린다.** SCM 연동 결과는 참고값이다.
2. **SCA 는 둘 이상을 교차한다.** [OSV](https://osv.dev/) 같은 공개 DB 기반 도구 하나를 보조로 붙이면 DB 편차를 줄일 수 있다 — 위 연구의 권고 그대로다.
3. **`NO PATH FOUND` 는 우선순위 신호로만 쓴다.** 삭제 사유가 아니다.
4. **ignore 에는 반드시 `expires` 와 사유를 붙인다.** 만료 없는 ignore 는 코드 리뷰에서 막는다.
5. **CI 는 0 만 통과로 본다.** 2·3 은 실패로 처리한다.
6. **SAST 가 못 보는 것은 다른 층에서 막는다.** 인가 로직은 테스트와 리뷰로, 설정은 IaC 스캔과 정책 엔진으로, 런타임은 모니터링으로.

## 맺으며 — 초록불의 비용

Snyk 가 주는 가치는 크다. 수백 개의 전이 의존성을 사람이 추적할 수는 없다. 그러나 스캐너의 가장 큰 위험은 **놓치는 취약점이 아니라, 초록불이 만드는 확신**이다. 대시보드가 깨끗해지는 순간 팀은 질문을 멈추고, 위 표의 오른쪽 열 — DB 가 모르는 것, 그래프가 틀린 것, 경로를 못 찾은 것, 코드에 없는 것, 사람이 끈 것 — 은 아무도 보지 않게 된다.

도구는 **"알려진 것을 빠르게"** 잡는 데 쓰고, **"모르는 것"** 은 여전히 설계·리뷰·운영이 책임진다. Snyk 의 문서가 스스로 그 경계를 꽤 정직하게 적어 두었다는 점은 오히려 칭찬할 일이다. 문제는 그 문서를 읽지 않고 초록불만 읽는 쪽이다.

---

## References

[^imtiaz]: Nasif Imtiaz, Seaver Thorne, Laurie Williams, *A Comparative Study of Vulnerability Reporting by Software Composition Analysis Tools*, ESEM 2021. <https://arxiv.org/abs/2108.12078>
[^snykdb]: Snyk User Docs, *Snyk Vulnerability Database*. <https://docs.snyk.io/scan-with-snyk/snyk-open-source/manage-vulnerabilities/snyk-vulnerability-database>
[^xz]: Andres Freund, *backdoor in upstream xz/liblzma leading to ssh server compromise*, oss-security mailing list, 2024-03-29. <https://www.openwall.com/lists/oss-security/2024/03/29/4>
[^snykdiff]: Snyk User Docs, *Differences in Open Source vulnerability counts across environments*. <https://docs.snyk.io/scan-with-snyk/snyk-open-source/manage-vulnerabilities/differences-in-open-source-vulnerability-counts-across-environments>
[^snykreach]: Snyk User Docs, *Reachability analysis*. <https://docs.snyk.io/manage-risk/prioritize-issues-for-fixing/reachability-analysis>
[^snykcode]: Snyk User Docs, *Snyk Code*. <https://docs.snyk.io/scan-with-snyk/snyk-code>
[^owaspsast]: OWASP, *Source Code Analysis Tools*. <https://owasp.org/www-community/Source_Code_Analysis_Tools>
[^snykscle]: Snyk User Docs, *Snyk Code Local Engine*. <https://docs.snyk.io/scan-with-snyk/snyk-code/snyk-code-local-engine>
[^snykignore]: Snyk User Docs, *Ignore issues*. <https://docs.snyk.io/manage-risk/prioritize-issues-for-fixing/ignore-issues>
[^snyktest]: Snyk User Docs, *snyk test* (CLI command reference). <https://docs.snyk.io/snyk-cli/commands/test>
