---
layout: post
title: "git rebase 와 브랜치 전략 — 도구와 정책을 갈라서 보기"
date: 2026-09-17 19:10:00 +0900
categories: [devops, git]
tags: [git, rebase, 브랜치전략, GitFlow, GitHubFlow, TrunkBased, 머지]
---

"rebase 를 써야 하나, merge 를 써야 하나" 와 "Git Flow 를 쓸까, GitHub Flow 를 쓸까" 는 자주 한 덩어리로 논쟁되지만 층위가 다른 질문이다. **rebase 는 도구고, 브랜치 전략은 정책이다.** 도구를 어디에 쓸지는 정책이 정한다. 그래서 이 글은 ① rebase 가 실제로 하는 일 → ② 어기면 안 되는 규칙 하나 → ③ 대표 전략 셋 → ④ 그 전략들 속에서 rebase 가 서는 자리, 순서로 간다.

## 1. rebase 의 실체 — 커밋을 "옮기는" 게 아니라 "다시 만든다"

`git rebase` 의 공식 정의는 한 줄이다: *"Reapply commits on top of another base tip"* — 커밋들을 다른 베이스 위에 다시 적용한다[^git-rebase]. 여기서 핵심은 **재적용(reapply)** 이라는 단어다. 기존 커밋을 이동시키는 게 아니라, 같은 변경 내용으로 **새 커밋들을 만들어** 다른 출발점 위에 쌓는다. 커밋 해시가 전부 바뀌는 이유다.

merge 와 비교하면 이렇다 — Pro Git 공식 북의 정리를 빌리면, 최종 스냅샷(코드 내용)은 merge 로 하든 rebase 로 하든 **같다.** 다른 건 히스토리다: merge 는 두 갈래가 합쳐진 사실을 머지 커밋으로 남기고, rebase 는 일이 순차적으로 일어난 것처럼 직선 히스토리를 만든다[^progit-rebase]. 즉 rebase vs merge 는 정확성의 문제가 아니라 **"히스토리를 사실대로 남길 것인가, 읽기 좋게 편집할 것인가"** 라는 취향+정책의 문제다.

## 2. 어기면 안 되는 규칙은 하나뿐이다

Pro Git 이 명령형으로 박아 둔 문장: *"**Do not rebase commits that exist outside your repository and that people may have based work on.**"* — 내 저장소 밖에 이미 존재하고, 남이 그 위에 작업했을 수 있는 커밋은 rebase 하지 말라[^progit-rebase]. rebase 는 커밋을 새로 만들므로, 공유된 커밋을 rebase 하면 동료의 히스토리에는 "버려진 옛 커밋" 과 "새 커밋" 이 공존하게 되고, 그걸 수습하는 과정에서 같은 변경이 중복 머지되는 난장판이 벌어진다.

실무 번역: **push 전의 로컬 커밋은 마음껏 rebase 하고(정리·squash·순서 변경), push 된 공유 브랜치는 rebase 하지 마라.** 예외는 "이 브랜치는 나 혼자 쓰고 force-push 될 수 있다" 가 팀 규약으로 합의된 PR 브랜치뿐이고, 그때도 남의 작업을 덮지 않도록 강제 push 는 신중하게 다뤄야 한다.

## 3. 브랜치 전략 셋 — 그리고 창시자의 반성문

**Git Flow (2010).** `main`(릴리스) + `develop`(통합) 이원 축에 feature/release/hotfix 보조 브랜치를 두는, 가장 구조화된 모델이다[^nvie]. 명시적 버전 릴리스·다중 버전 동시 지원에 강하다. 그런데 이 글에는 원저자 Vincent Driessen 본인이 2020년에 덧붙인 반성문이 있다 — *"웹앱처럼 지속 배포되고 여러 버전을 지원할 필요가 없는 소프트웨어는 내가 이 모델을 설계할 때 염두에 둔 부류가 아니다. 지속 배포를 한다면 git-flow 를 팀에 욱여넣지 말고 GitHub flow 같은 훨씬 단순한 워크플로우를 권한다"*[^nvie]. 창시자가 1차 출처에서 직접 적용 범위를 좁혀 준, 드물고 귀한 사례다.

**GitHub Flow.** `main` 은 항상 배포 가능 상태로 유지하고, 짧은 토픽 브랜치 → PR → 리뷰 → 머지 → 즉시 배포로 도는 단일 축 모델이다[^gh-flow]. 지속 배포 웹 서비스의 사실상 기본값.

**Trunk-Based Development.** 한 발 더 나가서, 모두가 `trunk`(main) 하나에 작고 잦은 커밋으로 수렴한다 — 브랜치를 쓰더라도 수명이 며칠을 넘지 않는 단명(short-lived) 브랜치만 허용하고, 미완성 기능은 브랜치가 아니라 feature flag 로 숨긴다[^tbd]. 장수 브랜치가 만드는 "머지 지옥" 자체를 구조적으로 제거하는 대신, CI·테스트·플래그 운영의 성숙도를 요구한다.

셋의 차이는 한 축으로 줄일 수 있다: **브랜치의 수명.** Git Flow 는 길고(릴리스 주기만큼), GitHub Flow 는 짧고(PR 하나만큼), Trunk-Based 는 최소(수 시간~수일)다. 그리고 브랜치 수명이 짧아질수록 rebase 의 쓸모는 커지고 위험은 줄어든다 — 다음 절의 이야기다.

## 4. 전략 속에서 rebase 가 서는 자리 — 세 군데

**① PR 브랜치를 최신 main 위로 올릴 때.** 토픽 브랜치가 뒤처졌을 때 `git rebase main` 으로 최신 위에 다시 얹으면, 충돌을 머지 시점이 아니라 내 브랜치에서 미리 해소하고 리뷰어에게 깨끗한 diff 를 보여줄 수 있다. 브랜치가 단명일수록(GitHub Flow·TBD) rebase 할 커밋이 적어 이 작업이 싸진다. 황금률과의 관계: 내 PR 브랜치가 "내 것" 이라는 팀 합의가 있으면 안전하다.

**② 머지 버튼의 세 가지 모드.** GitHub 기준 PR 머지는 머지 커밋 / **Squash and merge** / **Rebase and merge** 세 방식이고, squash 와 rebase 머지는 직선 히스토리를 만드는 대신 원 브랜치의 커밋 이력이 재작성된다[^gh-merge]. "main 히스토리를 직선으로 유지한다" 는 정책은 이 버튼 설정으로 리포 수준에서 강제하는 게 팀원 개개인의 습관에 기대는 것보다 확실하다.

**③ 공유 전 커밋 정리 (interactive rebase).** `git rebase -i` 로 로컬 커밋을 합치고 메시지를 다듬어 "리뷰 단위로 읽히는 커밋 열" 을 만드는 용도[^progit-rebase]. Pro Git 의 표현을 빌리면 rebase 는 "이야기를 다듬어 내보내는 것" 이다 — push 전에만 하면 편집은 미덕이다.

## 5. 정리 — 선택 기준 한 장

| | Git Flow | GitHub Flow | Trunk-Based |
| --- | --- | --- | --- |
| 축 브랜치 | main + develop | main | trunk |
| 브랜치 수명 | 길다 (릴리스 주기) | 짧다 (PR 단위) | 최소 (수 시간~수일) |
| 맞는 소프트웨어 | 명시적 버전·다중 버전 지원 | 지속 배포 웹 서비스 | 지속 배포 + 높은 CI 성숙도 |
| rebase 의 자리 | 제한적 (장수 브랜치는 위험) | PR 갱신·머지 방식으로 | 상시 (커밋이 작고 적어서) |
| 요구 조건 | 릴리스 관리 인력 | PR·리뷰 문화 | 테스트 자동화 + feature flag |

한 줄 요약 — **rebase 는 도구고, 브랜치 전략은 정책이다. 정책은 소프트웨어의 배포 방식(버전 릴리스냐 지속 배포냐)이 정하고, rebase 는 "공유 전 히스토리만 편집한다" 는 황금률 안에서 그 정책에 봉사한다.** 창시자 본인이 "웹앱이면 Git Flow 말고 더 단순한 걸 쓰라" 고 말한 시대다 — 전략을 고를 땐 모델의 명성이 아니라 자기 배포 방식을 먼저 보라.

---

## 근거의 한계

- 세 전략의 채택률·생산성 비교 같은 정량 데이터는 중립 출처를 확인하지 못해 싣지 않았다 — 이 글의 근거는 각 전략의 1차 문서와 창시자 본인의 서술이다.
- Trunk-Based Development 사이트는 커뮤니티가 널리 참조하는 사실상의 표준 문서지만, 표준화 기구의 사양은 아니다.
- 머지 방식 서술은 GitHub 기준이다. GitLab 등 다른 플랫폼도 동등 기능을 제공하지만 이 글에서 검증하지는 않았다.

## References

[^git-rebase]: Git 공식 문서 — [git-rebase](https://git-scm.com/docs/git-rebase) ("Reapply commits on top of another base tip")
[^progit-rebase]: Pro Git (공식 북) — [Git Branching: Rebasing](https://git-scm.com/book/en/v2/Git-Branching-Rebasing) (merge 와 스냅샷 동일·히스토리 상이, 황금률 원문, interactive rebase)
[^nvie]: Vincent Driessen — [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/) (Git Flow 원문 + 2020-03-05 "note of reflection")
[^gh-flow]: GitHub 공식 문서 — [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)
[^tbd]: Trunk Based Development — [trunkbaseddevelopment.com](https://trunkbaseddevelopment.com/) (단명 브랜치·feature flag)
[^gh-merge]: GitHub 공식 문서 — [About merge methods on GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github) (merge commit / squash / rebase and merge)
