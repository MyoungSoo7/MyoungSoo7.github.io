---
layout: post
title: "Harness Engineering ③ Software Engineering Harness — 팀의 *toolchain* 이 코드 품질을 결정한다"
date: 2026-05-29 01:30:00 +0900
categories: [engineering, productivity]
tags: [harness, toolchain, devex, linting, formatting, pre-commit, ide, git-hooks, conventional-commits, codeowners]
---

> "Harness Engineering 의 4 가지 얼굴" 시리즈의 3 편. [① AI Agent]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %}) / [② Test]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %}) / [④ Deployment]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})

회사를 옮기면 *코드 자체* 보다 *코드를 둘러싼 환경* 의 차이가 더 크게 느껴진다. 어떤 회사는 *clone 후 30초 내 빌드/실행* 되고, 어떤 회사는 *3일 동안 환경 세팅* 한다. 어떤 팀은 *PR 5분 내 머지* 되고, 어떤 팀은 *2주 걸린다*.

이 차이를 만드는 게 *Software Engineering Harness* — 팀의 *toolchain*. 그 안에 *린트, 포맷, pre-commit hook, IDE 설정, git 정책, CI/CD 의 게이트, CODEOWNERS, 문서 자동화* 가 다 들어있다.

Google / Meta / Stripe 같은 회사가 *internal tooling 에 수십 명 엔지니어를 투자하는 이유* 가 여기 있다. *Harness 가 팀 생산성을 1.5~3 배 가른다*.

---

## TL;DR — Software Engineering Harness 의 9 가지 layer

| Layer | 도구 / 패턴 |
|---|---|
| 1. Editor / IDE | VS Code / IntelliJ + 공유 설정 (`.editorconfig`, `.vscode/settings.json`) |
| 2. 포맷터 | Prettier (JS/TS), Spotless (Java), gofmt, black (Python) |
| 3. 린터 | ESLint, Checkstyle, golangci-lint, ruff, ktlint |
| 4. Pre-commit hook | Husky / lefthook / pre-commit 라이브러리 |
| 5. Conventional commits | commitlint + Conventional Commits 규약 |
| 6. PR 게이트 | CODEOWNERS + 필수 리뷰어 + branch protection |
| 7. CI/CD | GitHub Actions / GitLab CI / CircleCI |
| 8. 자동화 봇 | Dependabot, Renovate, ImageUpdater |
| 9. 문서 자동화 | Storybook, OpenAPI codegen, ADR 템플릿 |

---

## 0. *DevEx* 라는 단어가 등장한 이유

2020 년대 들어 *Developer Experience (DevEx)* 라는 직군이 등장. 핵심 책무:

- *Onboarding 시간 단축* (3일 → 30분)
- *Build / Test 시간 단축* (30분 → 3분)
- *PR cycle time 단축* (2주 → 1일)
- *반복 작업 자동화* (script + bot)

이게 *Software Engineering Harness 의 정확한 정의* — *개발자가 자기 일에 집중하도록 환경을 깎는* 것.

---

## 1. Editor / IDE — *모두 같은 환경* 부터

### `.editorconfig` — 에디터 무관 *공통 설정*

```ini
# .editorconfig (repo 루트)
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.{java,kt}]
indent_size = 4

[*.md]
trim_trailing_whitespace = false  # markdown 의 두 칸 = 줄바꿈
```

VS Code, IntelliJ, Vim, Emacs 모두 *자동 인식*. *공백 vs 탭, LF vs CRLF* 같은 *PR 디프 오염* 방지.

### `.vscode/settings.json` — VS Code 사용자 통일

```jsonc
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit",
    "source.organizeImports": "explicit"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.exclude": {
    "**/.git": true,
    "**/node_modules": true
  }
}
```

repo 에 commit 하면 *clone 한 모든 개발자* 가 같은 설정. 한 명이 *formatting 안 함* 으로 발생하는 diff 폭탄 방지.

### IntelliJ — `.idea/codeStyles/Project.xml`

같은 효과. *팀 코드 스타일* 을 *프로젝트에 박아넣기*.

---

## 2. 포맷터 — *논쟁 자체를 없애기*

코드 포맷팅 논쟁 (탭 vs 공백, 한 줄 길이, import 정렬) 은 *영원한 시간 낭비*. 자동 포맷터가 답.

| 언어 | 표준 포맷터 |
|---|---|
| JS / TS | Prettier |
| Java | Spotless + google-java-format |
| Kotlin | ktlint |
| Go | gofmt (내장) |
| Python | black |
| Rust | rustfmt (내장) |

### Spotless (Java) 예시

```gradle
// build.gradle
plugins {
    id 'com.diffplug.spotless' version '6.25.0'
}

spotless {
    java {
        googleJavaFormat('1.22.0')
        importOrder()
        removeUnusedImports()
        endWithNewline()
    }
}
```

```bash
./gradlew spotlessApply   # 자동 포맷
./gradlew spotlessCheck   # CI 에서 검증 (수정 안 함, 위반 시 실패)
```

CI 에 `spotlessCheck` 게이트 걸면 *PR 머지 전 필수*. 포맷 논쟁 *영구 종결*.

---

## 3. 린터 — *잠재 버그* 잡는 정적 분석

포맷터는 *스타일*, 린터는 *논리적 위험*. 둘은 다르다.

```js
// Prettier 는 OK 라고 함 (포맷 정상)
const x = users.find(u => u.id = currentId);
//                              ^^^^^^^^^^^ 할당 (=) 아닌 비교 (===) 해야

// ESLint 는 `no-cond-assign`, `eqeqeq` 룰로 잡음
```

### 주요 룰 카테고리

- **Possible Errors** — `no-undef`, `no-unused-vars`
- **Best Practices** — `eqeqeq`, `no-console`
- **Variables** — `no-shadow`
- **Stylistic** (포맷터로 옮겨감) — `indent` (deprecated)
- **ES6** — `prefer-const`, `no-var`

### Java Checkstyle / SpotBugs / PMD

```xml
<!-- checkstyle.xml -->
<module name="UnusedImports"/>
<module name="MagicNumber">
    <property name="ignoreNumbers" value="0, 1, 2, 100"/>
</module>
<module name="CyclomaticComplexity">
    <property name="max" value="10"/>
</module>
```

CyclomaticComplexity > 10 인 메서드는 *PR 거부*. *코드 분기 폭증* 자동 방지.

---

## 4. Pre-commit Hook — *commit 되기 전에* 막기

CI 가 잡으면 *늦다*. Local 에서 *commit 전에* 잡는 게 빠른 피드백.

### lefthook 예시 (Go, JS, Java 다 지원)

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    format:
      glob: "*.{ts,tsx,js,jsx}"
      run: npx prettier --write {staged_files}
      stage_fixed: true   # 포맷 후 자동 re-stage
    lint:
      glob: "*.{ts,tsx,js,jsx}"
      run: npx eslint --fix {staged_files}
      stage_fixed: true
    type-check:
      glob: "*.{ts,tsx}"
      run: npx tsc --noEmit
    java-format:
      glob: "*.java"
      run: ./gradlew spotlessApply
      stage_fixed: true

commit-msg:
  commands:
    commitlint:
      run: npx commitlint --edit {1}
```

`git commit` 하면 자동 실행. 통과해야 commit 완료.

### `prepare-commit-msg` — 자동 commit 메시지

```bash
#!/bin/bash
# .git/hooks/prepare-commit-msg
BRANCH=$(git branch --show-current)
if [[ $BRANCH == feat/* ]]; then
    PREFIX="feat: "
elif [[ $BRANCH == fix/* ]]; then
    PREFIX="fix: "
fi
sed -i.bak "1s|^|$PREFIX|" "$1"
```

브랜치명에서 *commit 타입* 자동 추출.

---

## 5. Conventional Commits — *commit 메시지의 표준*

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

타입:
- `feat:` 새 기능
- `fix:` 버그 수정
- `docs:` 문서
- `refactor:` 리팩토링
- `perf:` 성능
- `test:` 테스트
- `chore:` 잡일 (빌드, 의존성)
- `ci:` CI 설정

예:
```
feat(payment): Toss Pay 결제 수단 추가

- /api/v1/payments?provider=toss 엔드포인트
- TossPayGateway 어댑터 구현
- E2E 테스트 5개 추가

Closes #1234
```

### 자동 changelog / semantic-release

```bash
npm install -D semantic-release
```

```jsonc
// .releaserc
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",   // commit 메시지 분석
    "@semantic-release/release-notes-generator",  // CHANGELOG 생성
    "@semantic-release/github"             // GitHub Release 생성
  ]
}
```

`feat:` → minor 버전 up, `fix:` → patch up, `BREAKING CHANGE:` → major up. *완전 자동 versioning*.

내 settlement / lemuel-xr 도 이 패턴으로 CHANGELOG 자동.

---

## 6. PR 게이트 — *머지 전 필수 통과*

### CODEOWNERS

```
# .github/CODEOWNERS
*.tf                    @platform-team
/backend/payment/**     @payment-team @senior-engineer
/db/migration/**        @dba-team
*.md                    @docs-team
```

해당 파일 수정 PR 은 *그 팀의 승인 필수*. *책임자 누락* 사고 방지.

### Branch Protection (GitHub)

```yaml
# 머지 조건
- 1 명 이상 approve
- CI 모든 체크 통과
- 브랜치 up-to-date with main
- conversation 모두 resolved
- 직접 push 금지 (PR 만)
```

이 룰들이 *팀의 *최소 품질 게이트*.

---

## 7. CI/CD — 자동화의 동맥

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { java-version: '21', distribution: 'temurin' }
      - run: ./gradlew spotlessCheck checkstyleMain

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_PASSWORD: test }
        options: >-
          --health-cmd pg_isready --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew test jacocoTestReport
      - uses: codecov/codecov-action@v4

  arch-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew test --tests "*ArchitectureTest"

  build:
    needs: [lint, test, arch-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew bootJar
      - uses: docker/build-push-action@v5
```

**핵심**: lint → test → arch-test 가 *병렬*, build 가 *그 다음*. CI 시간 단축의 표준.

---

## 8. 자동화 봇 — *지속적 유지보수*

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule: { interval: "weekly" }
    open-pull-requests-limit: 10
    groups:
      minor-and-patch:
        update-types: [minor, patch]   # 한 PR 로 묶음

  - package-ecosystem: "gradle"
    directory: "/"
    schedule: { interval: "weekly" }

  - package-ecosystem: "docker"
    directory: "/"
    schedule: { interval: "monthly" }
```

매주 자동 PR. *수동 업그레이드 부담* 제거.

**Renovate** 는 더 강력한 대안 (groupName, autoMerge minor 등).

---

## 9. 문서 자동화

### OpenAPI codegen

```yaml
# build.gradle (Spring)
openApiGenerate {
    generatorName = 'kotlin'
    inputSpec = "$rootDir/api-spec.yml"
    outputDir = "$buildDir/generated"
}
```

API 명세 (YAML) → *client/server stub 자동 생성*. *수동 동기화 비용 0*.

### ADR (Architecture Decision Record)

```markdown
# 0042-use-outbox-pattern-for-event-publishing.md

## Status
Accepted

## Context
서비스 간 이벤트 발행 시 DB commit 과 메시지 발행이 ...

## Decision
Outbox Pattern 채택.

## Consequences
- ✅ At-least-once 메시징 보장
- ⚠️ DB 부하 약간 증가 (outbox 테이블)
- ⚠️ Triple Idempotency 패턴 도입 필요
```

`docs/adr/` 디렉터리에 *번호 매겨* 보관. *왜 이 결정을 했는지* 가 *코드보다 길게 산다*.

---

## 10. 내 환경의 toolchain (개인 + 회사)

### 공통

| 도구 | 용도 |
|---|---|
| `.editorconfig` | 모든 repo |
| Spotless + google-java-format | Java 포맷 |
| Checkstyle + ArchUnit | Java 린트 + 아키텍처 |
| lefthook | pre-commit hook |
| commitlint + Conventional Commits | commit 메시지 |
| GitHub Actions | CI |
| Dependabot | 의존성 자동 |

### Claude Code 특화

- *AI agent 가 자체적으로* lint / format / test 돌림 (Bash tool 권한 allow)
- *Hook 으로* commit 메시지 자동 검증 (Conventional Commits)
- *Skill 로* `commit-smart` (변경 분석 후 자동 commit) 같은 *반복 작업 자동화*

이게 *AI 시대의 toolchain* — *사람이 직접 명령 안 해도* 자동 lint/format/test 가 돌고, *AI agent 가 그 결과를 보고 자가 수정*.

---

## 결론 — Toolchain 은 *조용한 1인 1.5 배기*

좋은 software engineering harness 는 *드러나지 않는다*. *그저 모든 게 잘 돌아갈 뿐*. 새 팀원이 *왜 빨리 일이 되는지* 모를 정도로 *background 에서* 일하는 인프라.

회사 인터뷰 시 좋은 신호:
- 새 repo *clone → 30초 안에 빌드 통과*
- PR 만들면 *5분 안에 모든 자동 체크 통과*
- *환경 차이로 인한 "내 로컬에서는 됐는데"* 한 번도 없음
- *Senior 가 *toolchain 자체* 를 *제품* 으로 다룸*

이 환경의 팀이 *생산성 1.5~3 배 더 높다*. *코드가 더 좋아서가 아니라 *환경* 이 더 좋아서*.

다음 편: [④ Deployment Harness — CI/CD + GitOps]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})

---

## 참고

- DORA *State of DevOps Report* — DevEx 가 생산성에 미치는 영향
- *Team Topologies* — Skelton & Pais (2019)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Atlassian DevEx Guide](https://www.atlassian.com/devops)
- 시리즈 다른 편:
  - [① AI Agent Harness]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %})
  - [② Test Harness]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %})
  - [④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
