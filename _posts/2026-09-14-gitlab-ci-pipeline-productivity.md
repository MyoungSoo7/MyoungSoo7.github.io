---
layout: post
title: "깃랩 생산성의 나머지 절반 — 파이프라인이 사람을 기다리게 하지 않게"
date: 2026-09-14 23:19:47 +0900
categories: [devops]
tags: [GitLab, CI-CD, 파이프라인, 캐시, merge-train, 생산성]
---

오늘 이 블로그에는 깃랩 생산성 글이 두 편 먼저 올라갔다. [이슈 키 하나로 Jira·GitLab·IntelliJ 를 엮는 워크플로]({% post_url 2026-09-14-jira-confluence-gitlab-intellij-one-flow %})와 [깃랩·인텔리제이를 세 개의 루프로 나누는 법]({% post_url 2026-09-14-gitlab-intellij-productive-workflow %}). 둘 다 **사람 쪽** 이야기다 — 도구 사이를 오가는 손의 동선을 줄이는 법.

이 글은 나머지 절반, **기계 쪽**을 다룬다. 커밋을 푸시한 뒤 파이프라인이 도는 동안 사람은 둘 중 하나를 한다: 기다리거나, 다른 일로 갈아탄다. 기다리면 그 시간이 그대로 사라지고, 갈아타면 컨텍스트 스위치 비용을 낸다. 어느 쪽이든 파이프라인 소요 시간은 개발 루프의 바닥 상수가 된다. 그래서 CI 최적화는 인프라 취미가 아니라 생산성 작업이다.

먼저 정직하게 적어 둔다: 내 홈랩의 CI 는 GitHub Actions 라서 아래 항목들의 효과를 깃랩 실운영 수치로 제시할 수는 없다([러너가 어디 사는가]({% post_url 2026-09-10-github-vs-gitlab-where-the-runner-lives %})에서 다룬 그 환경이다). 그래서 이 글은 "몇 % 빨라진다" 류의 주장 대신, **깃랩 공식 문서가 제공하는 장치들을 '무엇을 없애는 장치인가'라는 기준으로 분류**하는 데 집중한다. 수치가 필요한 판단은 각자의 파이프라인에서 재야 한다 — 그 재는 방법 자체도 공식 문서에 있다.

## 0. 측정부터 — 어디가 느린지 모르면 최적화는 미신이다

GitLab 공식 [Pipeline efficiency][efficiency] 문서의 첫 처방은 기능이 아니라 측정이다. 프로젝트의 **CI/CD analytics** 에서 파이프라인 성공률과 소요 시간 추이를 보고, 개별 파이프라인 뷰에서 잡별 소요를 본 뒤에 손을 대라는 것. 흔한 함정은 "제일 무거워 보이는 잡"을 최적화하는 것인데, 전체 소요를 결정하는 건 무거운 잡이 아니라 **critical path** — 직렬로 묶인 가장 긴 사슬이다. 병렬로 도는 무거운 잡을 10분 줄여도 critical path 가 그대로면 체감은 0이다.

## 1. 안 돌려도 되는 잡을 안 돌리기

가장 싼 최적화는 실행을 생략하는 것이다. 깃랩에는 이걸 위한 장치가 세 겹 있다.

**`rules:changes`** — 바뀐 파일 경로에 따라 잡을 켜고 끈다. 문서만 고친 커밋에 백엔드 테스트가 도는 걸 막는 게 전형적 용도다([Specify when jobs run with rules][rules]).

```yaml
backend-test:
  script: ./gradlew test
  rules:
    - changes:
        - "src/**/*"
        - "build.gradle*"
```

**`workflow:rules`** — 잡 단위가 아니라 **파이프라인 자체**의 생성 조건을 정한다. 브랜치 푸시와 MR 파이프라인이 중복 생성되는 것을 여기서 잘라낸다([CI/CD YAML reference][yaml]).

**`interruptible: true` + 자동 취소** — 같은 브랜치에 새 커밋이 오면 낡은 커밋의 파이프라인은 결과가 나와도 쓸모가 없다. 잡에 `interruptible: true` 를 달고 프로젝트 설정의 auto-cancel redundant pipelines 를 켜면 낡은 파이프라인이 자동으로 죽는다([Customize pipeline configuration][settings]). 러너 슬롯이 유한한 환경(셀프호스티드 러너 한 대짜리 우리 집 같은 곳)에서는 이게 곧 대기열 길이를 줄인다.

## 2. 순서를 강요하지 않기 — stage 장벽과 `needs:`

깃랩 파이프라인의 기본 모델은 stage 다: build → test → deploy, 앞 stage 가 전부 끝나야 다음이 시작된다. 이 모델의 비용은 **장벽(barrier)** 이다 — test stage 의 가장 느린 잡 하나가 deploy stage 전체를 붙잡는다.

`needs:` 는 이 장벽을 잡 단위 의존 그래프(DAG)로 바꾼다. 어떤 잡이 정말로 기다려야 하는 잡만 명시하면, 나머지는 stage 와 무관하게 앞질러 출발한다([CI/CD YAML reference — needs][yaml]).

```yaml
deploy-docs:
  stage: deploy
  needs: ["build-docs"]   # test stage 전체를 기다리지 않는다
```

모노레포라면 [parent-child 파이프라인][downstream]이 같은 원리의 상위 버전이다 — 하위 디렉터리별 파이프라인을 부모가 `trigger` 로 낳고, `rules:changes` 와 조합하면 바뀐 부분의 파이프라인만 돈다.

## 3. 캐시와 아티팩트를 바꿔 쓰지 않기

공식 [Caching in GitLab CI/CD][caching] 문서가 처음에 못박는 구분이 있다: **cache 는 의존성(패키지 매니저가 내려받는 것)용, artifacts 는 잡의 산출물을 다음 잡에 넘기는 용도**다. 이 둘을 바꿔 쓰는 게 파이프라인이 느려지는 고전적 원인이다 — 빌드 산출물을 캐시에 넣으면 캐시 키가 어긋나는 순간 조용히 빈손으로 시작하고, 의존성을 아티팩트로 넘기면 매 잡마다 수백 MB 를 업로드/다운로드한다.

캐시 키는 잠금 파일에 걸어야 한다:

```yaml
cache:
  key:
    files:
      - package-lock.json   # 잠금 파일이 같으면 캐시 재사용
  paths:
    - .npm/
```

브랜치 이름을 키로 쓰면 브랜치마다 콜드 스타트가 나고, 고정 키 하나를 쓰면 의존성이 바뀌어도 낡은 캐시를 물고 온다. 잠금 파일 해시가 그 사이의 정답이라는 게 문서의 처방이다. 하나 더 — 캐시는 공짜 저장소가 아니다. 지난달 우리 집 GitHub Actions 가 저장소 쿼터에 막혔을 때 범인은 아티팩트가 아니라 캐시였다. 어느 CI 든 캐시 총량은 언젠가 청구서로 돌아온다.

## 4. 머지 큐의 정체 — merge trains

바쁜 리포에서 MR 여러 개가 각자 초록 파이프라인을 달고 있어도, **순서대로 머지되는 순간의 조합**은 아무도 검증한 적이 없다. A 와 B 가 각각 main 기준으로 초록이어도 A 머지 후의 main + B 는 빨갈 수 있다 — 서로 다른 줄을 고친 두 변경을 git 이 충돌 없이 합쳐 주는 바로 그 성질 때문에, 이 깨짐은 머지된 뒤에야 드러난다.

[Merge trains][trains] 은 머지 예정 순서대로 가상의 머지 결과를 만들어 그 위에서 파이프라인을 돌리고, 통과한 것만 순서대로 머지한다. main 이 빨간 채로 발견되는 사고 자체를 없애는 장치다. 단, 이건 **Premium 이상 유료 티어 기능**이다 — 무료 티어라면 같은 문제를 "머지 직전 rebase + 재검증" 규율로 손으로 감당해야 한다는 뜻이고, 그 규율이 무너질 때의 비용이 곧 이 기능의 가격 대비 가치다.

## 5. 사람 게이트는 좁게, 명시적으로

리뷰 대기도 파이프라인 대기만큼 루프를 늘린다. 깃랩에서 이걸 구조화하는 장치 둘:

- [CODEOWNERS][codeowners] — 경로별 소유자를 파일로 선언하면, MR 이 건드린 경로의 소유자가 자동으로 승인자가 된다. "누구한테 리뷰를 청하지" 하는 라우팅 고민이 커밋된 파일 하나로 대체된다.
- [External status checks][checks] — 외부 시스템의 판정을 MR 의 체크로 붙인다(이것도 Ultimate 티어). 사내 게이트가 이미 있다면 MR 화면 밖으로 나가지 않게 하는 용도다.

## 정리

| 없애는 것 | 장치 | 비고 |
| --- | --- | --- |
| 불필요한 실행 | `rules:changes` · `workflow:rules` · `interruptible` | 무료 |
| stage 장벽 대기 | `needs:` DAG · parent-child | 무료 |
| 의존성 재다운로드 | `cache` + 잠금파일 키 | 무료, 저장량 주의 |
| 깨진 main | merge trains | **Premium** |
| 리뷰 라우팅 고민 | CODEOWNERS | 승인 강제는 유료 |

아침의 두 글과 합치면 이렇게 된다: 이슈 키가 도구 사이의 **수작업 연결**을 없애고, 루프 분리가 **사람의 컨텍스트 스위치**를 줄이고, 이 글의 장치들이 **기계를 기다리는 시간**을 줄인다. 셋 중 어디가 병목인지는 팀마다 다르다 — 그리고 그걸 아는 방법은 언제나 같다. 재는 것.

---

## References

- GitLab Docs — [Pipeline efficiency][efficiency]
- GitLab Docs — [Specify when jobs run with rules][rules]
- GitLab Docs — [CI/CD YAML syntax reference][yaml] (`workflow:rules`, `needs`, `interruptible`)
- GitLab Docs — [Caching in GitLab CI/CD][caching]
- GitLab Docs — [Customize pipeline configuration][settings] (auto-cancel redundant pipelines)
- GitLab Docs — [Merge trains][trains]
- GitLab Docs — [Downstream pipelines][downstream] (parent-child)
- GitLab Docs — [Code Owners][codeowners]
- GitLab Docs — [External status checks][checks]
- GitLab Docs — [Review apps][reviewapps]

[efficiency]: https://docs.gitlab.com/ci/pipelines/pipeline_efficiency/
[rules]: https://docs.gitlab.com/ci/jobs/job_rules/
[yaml]: https://docs.gitlab.com/ci/yaml/
[caching]: https://docs.gitlab.com/ci/caching/
[settings]: https://docs.gitlab.com/ci/pipelines/settings/
[trains]: https://docs.gitlab.com/ci/pipelines/merge_trains/
[downstream]: https://docs.gitlab.com/ci/pipelines/downstream_pipelines/
[codeowners]: https://docs.gitlab.com/user/project/codeowners/
[checks]: https://docs.gitlab.com/user/project/merge_requests/status_checks/
[reviewapps]: https://docs.gitlab.com/ci/review_apps/
