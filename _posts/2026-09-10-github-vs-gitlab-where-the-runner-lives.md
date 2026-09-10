---
layout: post
title: "깃헙과 깃랩, 결국 러너가 어디서 도느냐의 문제: 무료 한도·자체호스팅·그리고 공식 보안 경고"
date: 2026-09-10 22:55:41 +0900
categories: [DevOps, CI/CD]
tags: [GitHub, GitLab, GitHub Actions, GitLab CI, Self-hosted Runner, Homelab]
---

# 깃헙과 깃랩, 결국 러너가 어디서 도느냐의 문제

어느 날 배포용 비공개 리포지터리의 CI 가 통째로 멈췄다. 잡이 실패한 게 아니라 **시작 자체가 안 됐다.** 워크플로 파일도 그대로였고 러너 설정도 건드린 적이 없었다. 원인은 코드가 아니라 청구서였다 — 비공개 리포에 할당된 GitHub 호스팅 러너의 월 무료 분이 소진된 것이다.

이 사고를 겪고 나서야 깃헙과 깃랩을 고르는 기준이 바뀌었다. 그전까지는 "UI 가 어떻다", "이슈 트래커가 낫다" 같은 걸 봤는데, 실제로 운영을 갈라놓는 축은 하나였다. **파이프라인을 돌리는 러너가 누구 기계에서 도는가, 그리고 그 시간을 누가 계산하는가.**

이 글은 그 축을 기준으로 두 서비스를 정리한 것이다. 수치는 전부 공식 문서에서 확인한 값만 썼다.

## 1. 주 사용처는 이미 갈려 있다

**GitHub 은 "공개하고 남과 엮이는" 곳이다.**

오픈소스의 사실상 표준 집결지이고, 남이 내 코드를 볼 일이 있으면 여기다. 포트폴리오와 이력도 마찬가지고 — 이 블로그 자체가 GitHub Pages 위에 올라가 있다. 생태계가 압도적이라 Actions 마켓플레이스, 컨테이너 레지스트리(ghcr.io), Dependabot 같은 걸 조립만 하면 파이프라인이 선다. 기본이 SaaS 이고 자체호스팅은 GitHub Enterprise Server 라는 별도 제품이라 사실상 기업 예산이 필요하다.

**GitLab 은 "우리 안에서 전부 통제하는" 곳이다.**

자체호스팅이 곁다리가 아니라 1급 시민이다. Community Edition 은 무료고 내 서버에 통째로 올린다. 소스·CI·컨테이너 레지스트리·이슈·보안 스캔이 한 제품 안에 들어 있는 올인원 구성이라, 조각을 붙이는 대신 켜기만 하면 된다. 망분리·금융·공공처럼 코드가 밖으로 나가면 안 되는 조직이 여기로 간다. 그리고 공식 FAQ 에 명시돼 있듯, 구독을 갱신하지 않으면 Enterprise Edition 은 동작을 멈추지만 **무료인 Community Edition 으로 내려서 계속 쓸 수 있다.** 락인이 덜하다는 뜻이다.

## 2. 사용법에서 실제로 갈리는 건 파일 하나다

git 자체는 완전히 같다. clone / commit / push / 리뷰 요청 흐름에 차이가 없다. 손이 바뀌는 지점은 사실상 CI 설정 파일 하나다.

| | GitHub | GitLab |
| --- | --- | --- |
| CI 설정 위치 | `.github/workflows/*.yml` | 루트의 `.gitlab-ci.yml` |
| 변경 제안 | Pull Request (PR) | Merge Request (MR) |
| 실행 주체 | Actions runner | GitLab Runner |
| 컨테이너 레지스트리 | ghcr.io | 프로젝트마다 자동 생성되는 Container Registry |

옮겨 간다고 해서 git 을 새로 배우는 게 아니다. 워크플로 문법과 용어를 바꿔 쓰는 작업이다.

## 3. 무료 한도 — 공식 문서 기준

여기가 본론이다. 두 서비스의 무료 정책은 겉보기 숫자와 실제 체감이 꽤 다르다.

### GitHub

GitHub 공식 문서는 이렇게 시작한다 — *"GitHub Actions usage is free for self-hosted runners and for public repositories that use standard GitHub-hosted runners."* 즉 **공개 리포는 무료, 그리고 자체 러너는 공개·비공개 상관없이 무료다.**

돈이 걸리는 건 딱 한 조합이다. **비공개 리포 + GitHub 호스팅 러너.**

| 플랜 | 월 무료 분 (표준 러너) | 아티팩트 저장소 |
| --- | --- | --- |
| GitHub Free | 2,000 | 500 MB |
| GitHub Pro | 3,000 | 1 GB |
| GitHub Free for organizations | 2,000 | 500 MB |
| GitHub Team | 3,000 | 2 GB |
| GitHub Enterprise Cloud | 50,000 | 50 GB |

주의할 함정이 두 개 있다. 첫째, **저장소 용량은 Actions 아티팩트와 GitHub Packages 가 공유한다.** 이미지를 ghcr.io 에 쌓으면 아티팩트 몫이 같이 줄어든다. 둘째, **larger runner 는 무료 분이 남아 있어도 항상 과금된다.** 공개 리포에서 써도 마찬가지다.

### GitLab

GitLab 은 반대편에서 접근한다. 공식 가격 FAQ 의 문장이 핵심이다 — *"Execution on your own runners will not use your compute minutes and is unlimited."* **자체 러너로 돌리면 compute minutes 를 아예 소모하지 않는다.**

| 플랜 | 월 compute minutes |
| --- | --- |
| GitLab.com Free | 400 |
| GitLab.com Premium | 10,000 |
| GitLab.com Ultimate | 50,000 |
| GitLab Self-Managed | 기본 quota 비활성 (= 무제한) |

GitLab.com 의 무료 400 분은 깃헙 무료 2,000 분의 1/5 이다. 여기에 제약이 하나 더 붙는데, **GitLab.com Free 는 비공개 최상위 그룹에 사용자 5명 제한**이 있다. 다만 이 제한은 GitLab.com 의 Free 에만 적용되고 자체호스팅 Free 에는 적용되지 않는다.

반면 자체호스팅(Self-Managed)은 공식 문서상 *"By default, GitLab instances do not have a compute quota. The default value for the quota is 0, which is unlimited."* — 기본이 무제한이다.

## 4. 그래서 결정 축은 러너다

위 표들을 한 문장으로 줄이면 이렇게 된다.

**남의 기계를 빌려 쓰면 분(minute) 을 세고, 내 기계에서 돌리면 안 센다. 이건 깃헙이든 깃랩이든 똑같다.**

그래서 "깃헙이 비싸서 깃랩으로 간다"는 판단은 대개 잘못된 진단이다. 비공개 리포의 CI 가 분 소진으로 멈췄다면, 플랫폼을 바꾸는 게 아니라 **러너를 내 쪽으로 가져오면** 해결된다. 공식 문서가 명시적으로 self-hosted runner 는 무료라고 못 박고 있기 때문이다.

집에 놀고 있는 서버가 있다면 이 계산은 더 확실해진다. 필자의 경우 K3s 홈랩 클러스터에 노드가 여러 대 있고, 그중 가장 사양이 좋은 노드는 대부분의 시간에 CPU 가 남는다. 거기에 러너를 붙이면 비공개 리포의 파이프라인이 무료로 무제한 돈다.

## 5. 그런데 공짜에는 조건이 붙는다

여기서 대부분의 비교 글이 멈추는데, 정작 중요한 건 그다음이다. GitHub 공식 문서는 self-hosted runner 를 소개하면서 **경고 박스**를 함께 띄운다.

> *"We recommend that you only use self-hosted runners with private repositories. This is because forks of your public repository can potentially run dangerous code on your self-hosted runner machine by creating a pull request that executes the code in a workflow."*

보안 하드닝 문서는 더 강하게 쓴다. self-hosted runner 는 **깨끗한 일회용 가상머신이라는 보장이 없어 워크플로의 신뢰할 수 없는 코드에 의해 지속적으로 오염될 수 있다**는 것이다. 그래서 공개 리포에는 *"almost never be used"* 라고 표현한다. GitHub 호스팅 러너가 매번 격리된 임시 VM 에서 돌기 때문에 지속적 오염이 구조적으로 불가능한 것과 대비된다.

더 눈여겨볼 대목은, 문서가 **비공개·내부 리포에서도 조심하라**고 덧붙인다는 점이다. 리포를 fork 하고 PR 을 열 수 있는 사람 — 보통 읽기 권한만 있어도 된다 — 이라면 러너 환경을 장악해 시크릿과 `GITHUB_TOKEN` 에 접근할 수 있기 때문이다. 환경(environment) 과 필수 승인으로 시크릿 접근을 통제해도, 그 워크플로 자체는 격리된 환경에서 도는 게 아니라 같은 위험에 노출된다.

"잡 끝날 때마다 러너를 파괴하면 되지 않나" 라는 완화책에 대해서도 문서는 선을 긋는다. 러너가 잡을 단 하나만 실행한다고 보장할 방법이 없고, 어떤 잡은 시크릿을 커맨드라인 인자로 넘겨서 같은 러너의 다른 잡이 `ps x -w` 로 들여다볼 수 있다는 것이다. 제대로 하려면 REST API 로 **JIT(just-in-time) 러너** — 최대 한 개의 잡만 수행하고 자동으로 등록 해제되는 러너 — 를 쓰라고 안내한다.

정리하면 이렇다. 자체 러너는 공짜지만, **그 기계에 무엇이 올라가 있는지가 곧 보안 경계**가 된다. 홈랩 노드에 개인 SSH 키나 쿠버네티스 자격증명이 널려 있다면, 거기에 러너를 붙이는 순간 그것들이 파이프라인 실행 권한을 가진 모두에게 노출 가능한 상태가 된다.

## 6. 어떻게 고를 것인가

두 제품의 우열을 가리는 중립적인 헤드투헤드 벤치마크는 없다. 아래는 공식 문서에서 확인한 사실을 근거로 한 선택 기준이지 성능 우열 주장이 아니다.

- **코드를 공개할 일이 있다** → GitHub. 공개 리포는 Actions 가 무제한 무료이고, 생태계 접근성이 다른 선택지와 비교가 안 된다.
- **코드가 조직 밖으로 나가면 안 된다** → GitLab Self-Managed. CE 가 무료이고 compute quota 가 기본 무제한이다.
- **비공개 리포인데 CI 분이 부족하다** → 플랫폼 이전보다 **자체 러너 도입이 먼저**다. 양쪽 다 자체 러너는 무료다.
- **자체 러너를 도입하기로 했다** → 공개 리포에는 붙이지 말고, 붙일 기계에서 민감 정보를 먼저 걷어낸 뒤, 가능하면 JIT 러너로 구성한다.

필자의 결론도 여기였다. 멈춰 있던 비공개 리포의 CI 는 깃랩 이전이 아니라 홈랩 노드에 러너를 붙이는 방향으로 정리하는 게 맞다. 다만 그 노드에는 클러스터 자격증명이 올라가 있어서, 러너를 붙이기 전에 그것부터 분리하는 게 순서다. 공짜라는 이유로 순서를 건너뛰면, 아낀 CI 요금보다 훨씬 비싼 걸 잃는다.

## References

- GitHub Actions billing — [docs.github.com/en/billing/concepts/product-billing/github-actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- GitHub Actions limits — [docs.github.com/en/actions/reference/limits](https://docs.github.com/en/actions/reference/limits)
- GitHub, Adding self-hosted runners — [docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)
- GitHub, Security hardening for GitHub Actions — [docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- GitLab, Compute minutes — [docs.gitlab.com/ci/pipelines/compute_minutes/](https://docs.gitlab.com/ci/pipelines/compute_minutes/)
- GitLab, Compute minutes administration — [docs.gitlab.com/administration/cicd/compute_minutes/](https://docs.gitlab.com/administration/cicd/compute_minutes/)
- GitLab Pricing — [about.gitlab.com/pricing/](https://about.gitlab.com/pricing/)
