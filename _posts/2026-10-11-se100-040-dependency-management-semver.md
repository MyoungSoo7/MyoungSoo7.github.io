---
layout: post
title: "[SE100 #040] 의존성 관리와 시맨틱 버저닝"
date: 2026-10-11 17:00:04 +0900
categories: [software-engineering]
tags: [se100, code-quality, semver, dependency-management, lockfile, supply-chain]
---

소프트웨어 공학 100 주제 시리즈의 40번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

시맨틱 버저닝은 버전 번호로 **호환성에 대한 약속**을 전달하는 규약이고, 범위 지정·잠금 파일·버전 선택 알고리즘은 그 약속을 얼마나 믿을지 정하는 장치다. 약속은 사람이 지키는 것이라 깨질 수 있으므로, 실무의 답은 "범위로 선언하고, 잠금 파일로 고정하고, 자동화로 자주 올리는 것" 이다.

## 왜 필요한가

현대 애플리케이션 코드의 대부분은 우리가 쓰지 않은 코드다. Russ Cox 는 [Our Software Dependency Problem](https://research.swtch.com/deps)(2019)에서 주요 언어 레지스트리가 각각 10만 개 넘는 패키지를 호스팅한다고 쓰며, 이 세밀한 재사용이 조심하지 않으면 심각한 문제로 이어진다고 경고한다.

문제는 두 방향에서 온다.

- **너무 느슨하면**: 어제 되던 빌드가 오늘 깨진다. 전이 의존성 하나가 몰래 올라갔기 때문이다.
- **너무 빡빡하면**: 보안 패치를 못 받는다. 2021년 12월 공개된 Log4j 의 [CVE-2021-44228](https://nvd.nist.gov/vuln/detail/CVE-2021-44228)(NVD CVSS 3.1 기본 점수 10.0)은 NVD 기술상 2.0-beta9 부터 2.15.0 까지(보안 릴리스 2.12.2, 2.12.3, 2.3.1 제외)에 영향을 줬다. 전이 의존성으로 들어온 오래된 버전을 고정해 둔 팀이라면 영향 파악부터 시작해야 했다.

## 핵심 개념

### SemVer 2.0.0 의 규칙

Tom Preston-Werner 가 만든 [Semantic Versioning 2.0.0](https://semver.org/)의 요약은 세 줄이다. 버전 `MAJOR.MINOR.PATCH` 에서

- **MAJOR**: 호환되지 않는 API 변경
- **MINOR**: 하위 호환되는 기능 추가
- **PATCH**: 하위 호환되는 버그 수정

자주 잊히는 조항이 더 중요하다.

| 조항 | 내용 |
|---|---|
| 공개 API 선언 | SemVer 를 쓰려면 공개 API 를 먼저 선언해야 한다. 버전은 그 API 에 대한 약속이다 |
| 불변 릴리스 | 한 번 릴리스한 버전의 내용은 **수정하면 안 된다(MUST NOT)**. 고치려면 새 버전 |
| 0.y.z | 초기 개발 단계. **무엇이든 언제든 바뀔 수 있다.** 공개 API 를 안정적이라 여기지 말 것 |
| 1.0.0 | 공개 API 를 정의하는 시점 |
| 사전 릴리스 | `1.0.0-alpha` 는 `1.0.0` 보다 우선순위가 낮다 |
| 빌드 메타데이터 | `+` 뒤의 메타데이터는 우선순위 비교에서 **무시**된다 |

### 0.x 의 현실적 해석

규격은 0.y.z 에서 "무엇이든 바뀔 수 있다" 고 하지만, 생태계는 관례를 만들었다. npm 의 [node-semver](https://github.com/npm/node-semver)와 Rust 의 [Cargo](https://doc.rust-lang.org/cargo/reference/semver.html)는 모두 **맨 왼쪽의 0 이 아닌 자리**가 바뀌면 호환되지 않는 변경으로 본다. 즉 0.y.z 에서는 y 가 사실상 MAJOR 역할을 한다.

### 범위 표기법 비교

| 표기 | 생태계 | 의미 |
|---|---|---|
| `^1.2.3` | npm, Cargo 기본 | `>=1.2.3 <2.0.0` |
| `^0.2.3` | npm, Cargo | `>=0.2.3 <0.3.0` |
| `^0.0.3` | npm | `>=0.0.3 <0.0.4` (사실상 고정) |
| `~1.2.3` | npm | `>=1.2.3 <1.3.0` |
| `~=1.4.5` | Python ([PEP 440](https://peps.python.org/pep-0440/)) | `>=1.4.5, ==1.4.*` |
| `~=2.2` | Python | `>=2.2, ==2.*` |
| `[1.0,2.0)` | Gradle | 1.0 이상 2.0 미만 |

npm 의 정확한 정의는 `^1.2.3 := >=1.2.3 <2.0.0-0` 처럼 상한에 `-0` 을 붙여 상한 버전의 사전 릴리스까지 배제한다.

```python
def caret_upper(base):
    major, minor, patch = base           # 맨 왼쪽의 0 이 아닌 자리를 올린 값이 상한
    if major > 0: return (major + 1, 0, 0)
    if minor > 0: return (0, minor + 1, 0)
    return (0, 0, patch + 1)
```

`1.2.3, 1.9.0, 2.0.0, 0.2.9, 0.3.0, 0.0.3, 0.0.4` 를 각 범위에 대 본 결과(Python 3.12):

```
^1.2.3  허용 1.2.3
^1.2.3  허용 1.9.0
^0.2.3  허용 0.2.9
^0.0.3  허용 0.0.3
```

### 같은 라이브러리의 두 버전이 필요할 때: 선택 알고리즘

A 가 B 와 E 를 쓰고, B 는 D 2.0 을, E 는 D 1.0 을 원한다. 도구마다 답이 다르다.

```
A ─▶ B ─▶ C ─▶ D 2.0
└──▶ E ─────▶ D 1.0
```

| 도구 | 규칙 | 위 그래프의 결과 |
|---|---|---|
| Maven | [가장 가까운 정의(nearest definition)](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html), 깊이가 같으면 먼저 선언된 것 | D 1.0 (경로가 더 짧음) |
| Gradle | [요청된 버전 중 가장 높은 것](https://docs.gradle.org/current/userguide/graph_resolution.html) | D 2.0 |
| Go 모듈 | [최소 버전 선택(MVS)](https://research.swtch.com/vgo-mvs): 각 요구가 명시한 최소 버전 중 최댓값 | D 2.0 (그 이상으로는 올리지 않음) |

Maven 결과가 특히 위험하다. B 는 D 2.0 의 API 를 쓰는데 D 1.0 이 선택되면 실행 중 `NoSuchMethodError` 가 난다. Maven 문서도 원하는 버전을 프로젝트 POM 에 명시하면 항상 그 버전을 보장할 수 있다고 안내하며, [Enforcer 의 dependencyConvergence 규칙](https://maven.apache.org/enforcer/enforcer-rules/dependencyConvergence.html)으로 버전 불일치를 빌드 실패로 만들 수 있다. Cox 는 MVS 가 사용자가 빌드하는 의존성을 작성자가 개발할 때 쓴 것과 최대한 가깝게 만든다는 의미에서 **고충실도 빌드(high-fidelity builds)** 를 낳는다고 설명한다(2018).

### 잠금 파일: 선언과 결과를 분리한다

```
선언 (사람이 편집)           결과 (도구가 생성, 커밋함)
package.json   "^4.18.0" ──▶ package-lock.json  4.21.2 + 무결성 해시
build.gradle   "1.+"     ──▶ gradle.lockfile
pyproject      "~=2.31"  ──▶ requirements.txt (--hash 포함)
go.mod         v1.9.0    ──▶ go.sum (체크섬)
```

- npm 의 [`npm ci`](https://docs.npmjs.com/cli/v10/commands/npm-ci)는 잠금 파일이 있어야 하고, `package.json` 과 맞지 않으면 잠금 파일을 고치지 않고 **오류로 종료**하며, `package.json` 이나 잠금 파일에 절대 쓰지 않는다. CI 에서는 `npm install` 대신 이것을 쓴다.
- Gradle 은 [`dependencyLocking { lockAllConfigurations() }`](https://docs.gradle.org/current/userguide/dependency_locking.html)과 `--write-locks` 로 동적 버전을 잠근다.
- pip 은 [`--require-hashes`](https://pip.pypa.io/en/stable/topics/secure-installs/) 해시 검사 모드로 원격 변조를 막는다.
- Go 는 [`go.sum` 과 체크섬 데이터베이스](https://go.dev/ref/mod)로 모듈 내용을 암호학적으로 검증한다.

**애플리케이션은 잠금 파일을 커밋한다.** 라이브러리는 범위를 넓게 선언해 사용자의 해석 여지를 남기되, 자기 CI 에서는 잠금 파일로 재현성을 확보한다.

### 약속의 한계: 하이럼의 법칙

[Hyrum's Law](https://www.hyrumslaw.com/)는 이렇게 말한다.

> API 사용자가 충분히 많으면, 계약에서 무엇을 약속했든 상관없이 시스템의 관찰 가능한 모든 동작에 누군가는 의존하게 된다.

PATCH 릴리스가 오류 메시지 문구나 정렬 순서, 성능을 바꾸면 누군가는 깨진다. SemVer 는 "깨지지 않음" 의 보증이 아니라 **작성자의 의도 표시**다. 그래서 자동 업데이트에도 테스트가 관문이어야 한다.

### 공급망 사건이 남긴 교훈

- **left-pad (2016)**: npm 공식 블로그의 [kik, left-pad, and npm](https://blog.npmjs.org/post/141577284765/kik-left-pad-and-npm)(2016-03-23)에 따르면 패키지 이름 분쟁 끝에 작성자가 자신의 `kik` 과 다른 패키지 272개를 게시 취소했고, 그중 하나가 `left-pad` 였다. 이를 직간접으로 의존하던 많은 프로젝트의 설치가 실패했다. 현재 npm [게시 취소 정책](https://docs.npmjs.com/policies/unpublish)은 게시 72시간 이내이고 의존하는 패키지가 없을 때, 또는 그 이후라도 의존 패키지가 없고 지난주 다운로드가 300 미만이며 소유자가 한 명일 때만 게시 취소를 허용한다. 레지스트리의 내용이 사라질 수 있다는 것은 사내 미러·캐시를 두는 근거가 된다.
- **xz (2024)**: [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)에 따르면 xz 5.6.0 부터 업스트림 tarball 에 악성 코드가 들어 있었다. 버전 번호와 범위 규칙은 이런 위협을 막지 못한다. 출처 증명([SLSA](https://slsa.dev/)), 의존성 건강도 평가([OpenSSF Scorecard](https://scorecard.dev/)), 취약점 DB([OSV](https://osv.dev/)), 그리고 SBOM([CycloneDX](https://cyclonedx.org/), [SPDX](https://spdx.dev/))이 다른 층의 방어다.

## 실무 적용

### 의존성 추가 전 점검 (Cox 의 체크리스트 요약)

Cox 의 글은 의존성을 **검사(inspect)하고, 테스트하고, 추상화하고, 격리하고, 피할 수 있으면 피하고, 업그레이드하고, 계속 지켜보라**고 정리한다.

- [ ] 최근 유지보수 활동, 관리자 수, 이슈 대응
- [ ] 전이 의존성의 수와 크기(`npm ls`, `gradle dependencies`, `go mod graph`)
- [ ] 내가 쓰는 기능이 몇 줄로 직접 구현 가능한 수준인가
- [ ] 바꿔야 할 때를 대비해 얇은 어댑터 뒤에 둘 수 있는가(SE100 #036 의 경계 추상화)

### 업데이트 자동화

[Dependabot](https://docs.github.com/en/code-security/dependabot)이나 [Renovate](https://docs.renovatebot.com/)로 업데이트 PR 을 자동으로 받는다. 운영 요령은 다음과 같다.

- PATCH·MINOR 는 묶어서 주기적으로, 테스트 통과 시 자동 병합. MAJOR 는 개별 PR 로 사람이 검토
- 보안 업데이트는 주기와 무관하게 즉시
- PR 마다 [의존성 검토](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/about-dependency-review)로 새로 들어오는 취약 버전을 차단

### 내가 라이브러리를 낼 때

- 공개 API 를 문서로 명시한다. 문서에 없는 동작은 바뀔 수 있다고 적는다(하이럼의 법칙 완화).
- 커밋을 [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)로 쓰면 `fix:` 는 PATCH, `feat:` 는 MINOR, `BREAKING CHANGE:` 꼬리말이나 `!` 는 MAJOR 에 대응해 버전 결정을 자동화할 수 있다.
- 제거 전에 Deprecated 를 한 MINOR 이상 먼저 내고, 변경 이력에 명시한다(SE100 #039 의 Keep a Changelog).

## 흔한 오해와 함정

- **"SemVer 를 따르는 라이브러리니까 MINOR 업데이트는 안전하다."** 의도일 뿐이다. 하이럼의 법칙 때문에 테스트 없이 믿으면 안 된다.
- **"버전을 정확히 고정하면 안전하다."** 재현성은 얻지만 보안 패치를 놓친다. 고정은 잠금 파일에 맡기고, 업데이트는 자동화로 자주.
- **잠금 파일을 `.gitignore` 에 넣기.** 애플리케이션의 빌드가 재현되지 않는다.
- **Maven 에서 전이 의존성 충돌 방치.** 가장 가까운 정의 규칙이 더 낮은 버전을 고를 수 있다. `dependencyManagement`(BOM)로 명시하고 수렴을 강제한다.

## 확인 문제

1. SemVer 2.0.0 에서 이미 릴리스한 버전에 버그가 있으면 어떻게 해야 하는가?
2. npm 에서 `^0.2.3` 과 `^1.2.3` 이 허용하는 범위를 쓰고, 차이가 나는 이유를 설명하라.
3. A→B→C→D 2.0, A→E→D 1.0 그래프에서 Maven 과 Gradle 이 각각 고르는 D 의 버전은? Maven 의 결과가 위험한 이유는?
4. 하이럼의 법칙이 SemVer 의 한계를 어떻게 보여 주는가?
5. `npm ci` 가 CI 에서 `npm install` 보다 적합한 이유를 npm 문서의 동작으로 설명하라.

### 풀이

1. 릴리스된 버전의 내용은 수정하면 안 되므로, 수정 사항을 새 버전(대개 PATCH)으로 릴리스한다.
2. `^0.2.3` 은 `>=0.2.3 <0.3.0`, `^1.2.3` 은 `>=1.2.3 <2.0.0`. 맨 왼쪽의 0 이 아닌 자리를 바꾸지 않는 변경만 허용하므로, 0.x 에서는 MINOR 자리가 사실상 MAJOR 역할을 한다.
3. Maven 은 경로가 짧은 D 1.0, Gradle 은 가장 높은 D 2.0. B(와 C)는 D 2.0 의 API 를 기대하는데 1.0 이 선택되면 실행 시점에 메서드나 클래스를 찾지 못하는 오류가 날 수 있다.
4. 사용자가 많으면 문서화된 계약 밖의 관찰 가능한 동작에도 누군가 의존하므로, 작성자가 "호환된다" 고 판단한 PATCH·MINOR 변경도 누군가에게는 깨지는 변경이 된다.
5. 잠금 파일이 반드시 있어야 하고, `package.json` 과 맞지 않으면 갱신하지 않고 오류로 종료하며, 매니페스트와 잠금 파일에 쓰지 않는다. 그래서 CI 빌드가 커밋된 잠금 파일 그대로 재현된다.

## 더 읽을거리 (References)

- [Semantic Versioning 2.0.0](https://semver.org/)
- [node-semver](https://github.com/npm/node-semver), [Cargo SemVer Compatibility](https://doc.rust-lang.org/cargo/reference/semver.html), [PEP 440](https://peps.python.org/pep-0440/)
- Russ Cox, [Minimal Version Selection](https://research.swtch.com/vgo-mvs), 2018 / [Our Software Dependency Problem](https://research.swtch.com/deps), 2019
- [Maven: Introduction to the Dependency Mechanism](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html), [Gradle: Dependency Locking](https://docs.gradle.org/current/userguide/dependency_locking.html)
- npm Blog, [kik, left-pad, and npm](https://blog.npmjs.org/post/141577284765/kik-left-pad-and-npm), 2016
- NVD, [CVE-2021-44228](https://nvd.nist.gov/vuln/detail/CVE-2021-44228), [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)
