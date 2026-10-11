---
layout: post
title: "[SE100 #060] 릴리스 관리와 체인지로그"
date: 2026-10-11 17:03:43 +0900
categories: [software-engineering]
tags: [se100, delivery, release-management, semantic-versioning, changelog]
---

소프트웨어 공학 100 주제 시리즈의 60번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

릴리스 관리는 "무엇을, 언제, 어떤 약속과 함께 사용자에게 내보내는가" 를 다루는 일이다. 버전 번호는 호환성에 대한 **약속**이고, 체인지로그는 그 약속을 사람이 읽을 수 있게 쓴 **설명서**이며, 릴리스 주기와 지원 정책은 사용자가 계획을 세울 수 있게 하는 **일정표**다.

## 왜 필요한가

지속적 배포(SE100 #055 에서 다룬다)를 하는 웹 서비스라면 "릴리스" 가 하루에도 수십 번 일어나고, 사용자는 버전 번호를 의식하지 않는다. 하지만 라이브러리, API, SDK, 설치형 소프트웨어, 모바일 앱, 사내 플랫폼처럼 **다른 사람이 내 산출물 위에 무언가를 만드는** 경우는 다르다. 사용자는 업그레이드를 스스로 결정해야 하고, 그 판단에 필요한 정보는 오직 릴리스가 주는 것뿐이다.

- 2.3 에서 2.4 로 올리면 내 코드가 깨지는가?
- 이번 버전에서 보안 수정이 있었는가? 지금 당장 올려야 하는가?
- 내가 쓰는 1.x 는 언제까지 보안 패치를 받는가?

이 질문에 답하지 못하는 프로젝트는 사용자가 업그레이드를 두려워하게 만들고, 결국 오래된 버전이 방치되어 보안 부채가 쌓인다.

## 핵심 개념

### 시맨틱 버저닝

[Semantic Versioning 2.0.0](https://semver.org/) 의 요약은 다음과 같다. 버전 번호 MAJOR.MINOR.PATCH 에서,

| 올리는 부분 | 조건 |
|---|---|
| MAJOR | 호환되지 않는 API 변경 |
| MINOR | 하위 호환되는 기능 추가 |
| PATCH | 하위 호환되는 버그 수정 |

요약 밑의 명세 조항들이 실무에서 더 중요하다.

- SemVer 를 쓰는 소프트웨어는 **공개 API 를 선언해야 한다(MUST)**. 무엇이 API 인지 정하지 않으면 "호환" 이라는 말이 의미가 없다.
- 0.y.z 는 초기 개발용이며 무엇이든 언제든 바뀔 수 있고, 공개 API 를 안정적이라고 여기면 안 된다. 1.0.0 이 공개 API 를 정의한다.
- 한 번 릴리스한 버전의 내용은 **수정하면 안 된다(MUST NOT)**. 수정은 새 버전으로 내야 한다.
- 공개 API 의 어떤 기능이든 **폐기 예정(deprecated)으로 표시하면 MINOR 를 올려야 한다**.
- 사전 릴리스는 하이픈 뒤에 붙이고(`1.0.0-alpha.1`), 정상 버전보다 우선순위가 낮다(`1.0.0-alpha < 1.0.0`). 빌드 메타데이터(`+build.5`)는 우선순위 비교에 쓰이지 않는다.

명세의 FAQ 는 실수로 MINOR 버전에 하위 호환이 깨지는 변경을 내보냈다면, 알아차린 즉시 문제를 고치고 호환성을 복구하는 새 MINOR 버전을 내라고 권한다. 이미 낸 버전을 고쳐 쓰지 않는다는 원칙과 같은 맥락이다.

### 하이럼의 법칙: 호환성의 현실

SemVer 는 "공개 API" 의 호환성만 약속한다. 그런데 Hyrum Wright 의 관찰(이름은 Titus Winters 가 붙였다고 본인이 밝힌다)로 알려진 [하이럼의 법칙(Hyrum's Law)](https://www.hyrumslaw.com/)은 이렇다.

> API 사용자가 충분히 많으면, 계약에서 무엇을 약속했는지는 중요하지 않다. 시스템의 관찰 가능한 모든 동작에 누군가는 의존하게 된다.

에러 메시지 문구, 결과 정렬 순서, 응답 시간까지 누군가의 코드는 그것에 기대고 있다. PATCH 릴리스라도 누군가를 깨뜨릴 수 있다는 뜻이다. 그래서 릴리스 관리는 버전 규칙만으로 끝나지 않고, **무엇이 바뀌었는지 상세히 알리는 체인지로그**와 **폐기 예고 기간**이 함께 가야 한다.

### 캘린더 버저닝

모든 프로젝트에 SemVer 가 맞지는 않는다. [CalVer](https://calver.org/)는 릴리스 달력에 기반한 버전 규약이다. 예를 들어 Ubuntu 는 `YY.0M` 형식을 쓴다. Ubuntu [릴리스 주기 페이지](https://ubuntu.com/about/release-cycle)에 따르면 6개월마다 새 버전을 내고 연도와 월로 번호를 붙이며(예: 2026년 4월의 26.04), 중간 릴리스는 9개월, LTS 는 2년마다 나와 5년간 표준 보안 유지보수를 받는다.

| 방식 | 버전이 말하는 것 | 잘 맞는 곳 |
|---|---|---|
| SemVer | 호환성의 변화 | 라이브러리, API, SDK |
| CalVer | 언제 나왔는가(얼마나 오래되었나) | 정기 릴리스 OS·배포판, 데이터셋, 인증서 번들 |
| 단조 증가 번호 | 순서만 | 내부 서비스, 브라우저처럼 자동 업데이트 위주 제품 |

### 체인지로그: 사람을 위한 기록

[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)(Olivier Lacan)은 체인지로그를 "프로젝트의 각 버전에서 일어난 주목할 만한 변경을, 선별해 시간순으로 정리한 파일" 로 정의하고 원칙을 이렇게 요약한다.

- 체인지로그는 **기계가 아니라 사람을 위한 것**이다.
- 모든 버전마다 항목이 있고, 최신 버전이 맨 위, 각 버전에 릴리스 날짜를 적는다(ISO 8601 형식, 예: 2017-07-17).
- 같은 종류의 변경을 묶는다: **Added**(새 기능), **Changed**(기존 기능 변경), **Deprecated**(곧 제거될 기능), **Removed**(제거된 기능), **Fixed**(버그 수정), **Security**(취약점).
- 맨 위에 **Unreleased** 섹션을 두어 다음 릴리스에 들어갈 변경을 모아 둔다.
- SemVer 를 따르는지 밝힌다.

같은 문서가 꼽는 나쁜 관행이 더 교훈적이다. **커밋 로그 diff 를 체인지로그로 쓰지 말 것**(병합 커밋, 모호한 제목, 문서 수정 같은 잡음이 가득하다. 커밋의 목적은 소스의 진화 단계를 기록하는 것이고 체인지로그의 목적은 사용자에게 주목할 차이를 알리는 것이다), **폐기 예정을 빠뜨리지 말 것**, 문제 때문에 회수한 버전은 지우지 말고 `[YANKED]` 로 표시할 것.

### 커밋 규약과 자동화

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)은 커밋 메시지에 구조를 주어 SemVer 와 연결한다.

| 커밋 | SemVer 대응 |
|---|---|
| `fix: ...` | PATCH |
| `feat: ...` | MINOR |
| 꼬리말 `BREAKING CHANGE: ...` 또는 타입 뒤 `!` (예: `feat!:`) | MAJOR |
| 그 밖의 타입(`docs:`, `refactor:` 등) | 명세상 SemVer 에 암묵적 영향 없음 (BREAKING CHANGE 가 없다면) |

이 규약 위에서 [semantic-release](https://semantic-release.gitbook.io/semantic-release) 는 다음 버전 번호 결정, 체인지로그 생성, 패키지 게시를 자동화하고, [release-please](https://github.com/googleapis/release-please) 는 릴리스 PR 을 생성해 추가 작업이 머지될 때마다 갱신한다. 자동화의 함정은 Keep a Changelog 가 경고한 바로 그것이다. 커밋 제목을 그대로 나열하면 사람을 위한 체인지로그가 아니라 커밋 로그 덤프가 된다. 자동 생성 결과는 **초안**으로 보고 사람이 다듬는 편이 낫다.

### 릴리스 주기와 지원 정책

지원 기간을 명확히 공표한 프로젝트들의 예:

| 프로젝트 | 정책 (공식 문서 기준) |
|---|---|
| [Kubernetes](https://kubernetes.io/releases/) | 최근 세 개의 마이너 릴리스에 대해 릴리스 브랜치 유지. 1.19 이후 버전은 약 1년간 패치 지원 |
| [Python](https://devguide.python.org/versions/) | PEP 602 의 다섯 단계: feature → prerelease → bugfix(약 2개월마다 바이너리) → 릴리스 2년 뒤 security(3.13 이전은 18개월) → 5년 뒤 end-of-life |
| [Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/process/release_cycle.md) | 2주마다 새 마일스톤을 stable 로. 브랜치 후 3주 안정화, stable 은 매주 보안 갱신, 4번째 마일스톤마다 기업용 extended stable |
| [Ubuntu](https://ubuntu.com/about/release-cycle) | 6개월마다 릴리스, LTS 는 2년마다 + 5년 표준 보안 유지보수 |

공통점은 **지원 종료일을 미리 공표한다**는 것이다. 사용자가 업그레이드 계획을 세울 수 있게 하는 것이 릴리스 관리의 핵심 서비스다.

## 실무 적용

### CHANGELOG.md 템플릿

```markdown
# Changelog
이 프로젝트는 Semantic Versioning 을 따른다.

## [Unreleased]
### Added
- 주문 조회 API 에 `status` 필터 추가 (#412)

## [2.4.0] - 2026-10-08
### Deprecated
- `GET /orders?state=` 파라미터. 3.0.0 에서 제거 예정. `status` 를 쓸 것.
### Fixed
- 부분 환불 시 합계가 음수로 표시되던 문제 (#398)
### Security
- 의존성 jackson-databind 를 취약점 수정 버전으로 갱신

## [2.3.1] - 2026-09-30 [YANKED]
- 결제 콜백 회귀로 회수. 2.3.2 를 사용할 것.
```

### 릴리스 체크리스트

```
[ ] 공개 API 의 범위가 문서화되어 있는가 (SemVer 의 전제)
[ ] 이번 변경의 SemVer 수준을 리뷰에서 확인했는가 (특히 폐기 예정 → MINOR)
[ ] Unreleased 섹션을 버전 섹션으로 옮기고 날짜를 ISO 8601 로 적었는가
[ ] 깨지는 변경에는 마이그레이션 안내가 있는가
[ ] 주석 태그(annotated tag)를 만들고 서명했는가: git tag -s v2.4.0 -m "v2.4.0"
[ ] 산출물·SBOM·출처 증명을 태그와 함께 게시했는가 (SE100 #059 에서 다룬다)
[ ] 지원 중인 이전 버전 목록과 종료일이 공표되어 있는가
```

Git 은 [가벼운(lightweight) 태그와 주석(annotated) 태그](https://git-scm.com/book/en/v2/Git-Basics-Tagging) 두 종류를 지원하고, 주석 태그는 Git 데이터베이스에 완전한 객체로 저장된다. Pro Git 은 정보를 모두 갖는 주석 태그를 일반적으로 권장한다. 릴리스 태그는 형상 관리(SE100 #051 에서 다룬다)의 베이스라인 식별자이므로 주석 태그로 만드는 것이 맞다.

## 흔한 오해와 함정

- **"버전 번호는 마케팅."** 라이브러리에서 버전 번호는 의존성 해석기가 읽는 **기계용 계약**이다. `^2.3.0` 같은 범위 지정은 SemVer 를 믿고 MINOR·PATCH 를 자동으로 받아들인다.
- **0.x 에 오래 머무르기.** 0.y.z 는 "무엇이든 바뀔 수 있다" 는 뜻이라 사용자에게 아무 약속도 하지 않는다. 운영에서 쓰이기 시작했다면 1.0.0 을 내고 약속을 시작해야 한다.
- **릴리스한 산출물 덮어쓰기.** 같은 버전 번호로 다른 내용을 다시 게시하면, 해시 고정을 쓰는 사용자의 빌드가 깨지고 공급망 신뢰가 무너진다. SemVer 도 금지한다.
- **커밋 로그 = 체인지로그.** 사용자에게 필요한 것은 "무엇이 나에게 영향을 주는가" 이지 내부 리팩터링 기록이 아니다.
- **폐기 예고 없는 제거.** 하이럼의 법칙을 생각하면, 예고 기간 없이 지우는 것은 누군가의 장애를 예약하는 일이다.

## 확인 문제

1. SemVer 에서 공개 API 의 한 기능을 폐기 예정으로 표시했다. 어떤 번호를 올려야 하는가?
2. `1.0.0-rc.1`, `1.0.0`, `1.0.0-beta`, `1.0.0+build.7` 을 우선순위 순으로 정렬하라(같은 우선순위는 함께 표시).
3. Keep a Changelog 가 커밋 로그 diff 를 체인지로그로 쓰지 말라고 하는 이유는?
4. Conventional Commits 에서 `refactor!: 설정 키 이름 변경` 커밋은 SemVer 의 어떤 변경에 해당하는가?
5. 하이럼의 법칙이 PATCH 릴리스에 대해 시사하는 바는?

### 풀이

1. MINOR. 명세는 공개 API 기능을 폐기 예정으로 표시하면 MINOR 를 올려야 한다고 규정한다.
2. `1.0.0-beta` < `1.0.0-rc.1` < `1.0.0` = `1.0.0+build.7`. 사전 릴리스는 정상 버전보다 낮고, 빌드 메타데이터는 우선순위에 영향이 없다.
3. 병합 커밋, 모호한 제목, 문서 수정 같은 잡음이 가득하기 때문이다. 커밋은 소스의 진화 단계를 기록하고, 체인지로그는 여러 커밋에 걸친 주목할 차이를 사용자에게 명확히 전달하는 것이 목적이다.
4. MAJOR. 타입 뒤의 `!` 는 BREAKING CHANGE 를 뜻하며, 타입과 무관하게 MAJOR 에 대응한다.
5. 계약상 하위 호환인 수정이라도 사용자가 의존하던 관찰 가능한 동작(메시지, 순서, 성능)을 바꾸면 누군가는 깨진다. PATCH 도 변경 내용을 구체적으로 알리고, 영향이 클 수 있는 동작 변화는 예고해야 한다.

## 더 읽을거리 (References)

- Tom Preston-Werner, [Semantic Versioning 2.0.0](https://semver.org/)
- Olivier Lacan, [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Calendar Versioning](https://calver.org/)
- Hyrum Wright, [Hyrum's Law](https://www.hyrumslaw.com/)
- Kubernetes, [Releases](https://kubernetes.io/releases/)
- Python Developer's Guide, [Status of Python versions](https://devguide.python.org/versions/)
- Chromium, [Chrome Release Cycle](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/process/release_cycle.md)
- Ubuntu, [Ubuntu release cycle](https://ubuntu.com/about/release-cycle)
- Scott Chacon, Ben Straub, [Pro Git — Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [semantic-release](https://semantic-release.gitbook.io/semantic-release), [release-please](https://github.com/googleapis/release-please)
