---
layout: post
title: "GitHub Worktree로 여러 작업을 동시에 진행하고 브랜치별 1:1 대응하는 법"
date: 2026-10-26 02:56:54 +0900
categories: [Git, GitHub, Development, Agent]
tags: [git-worktree, branch, Pull Request, parallel development, Claude Code, Hermes]
---

> 기준 시각: 2026-10-26 02:56 KST. Git·GitHub 공식 문서 기준으로 작성했다. 여러 워커를 실제로 동시에 실행한 성능 수치가 아니라, 재현 가능한 Git 구조와 운영 규칙을 설명한다.

## 결론

여러 작업을 동시에 진행하려면 **저장소 하나에 여러 브랜치를 만들고, 브랜치마다 독립된 worktree 디렉터리를 연결한 뒤, 작업자·에이전트·Pull Request를 1:1로 매칭**하면 된다. Git worktree는 같은 저장소의 여러 브랜치를 서로 다른 디렉터리에서 동시에 checkout할 수 있게 하며, GitHub Pull Request는 각 작업 브랜치의 변경을 base 브랜치와 비교·검토하는 단위가 된다.[1][2][3]

## 1. Worktree와 Branch의 차이

- **Branch:** 커밋 이력의 작업 라인
- **Worktree:** 특정 branch를 실제 파일 시스템 디렉터리에 checkout한 작업 공간
- **Worker/Agent:** 해당 worktree에서 구현·테스트를 수행하는 실행 주체
- **Pull Request:** 작업 branch를 base branch에 병합하기 위한 검토·CI 단위

브랜치만 여러 개 만들면 한 디렉터리에서 매번 checkout해야 하므로 작업 전환 때 변경사항을 stash하거나 임시 커밋해야 한다. Worktree를 사용하면 각 브랜치가 별도 디렉터리를 가지므로 한 작업에서 테스트를 실행하는 동안 다른 작업을 계속 진행할 수 있다.[1][3]

```text
저장소 Git history
       ├─ main
       ├─ feat/auth       ── worktree/auth       ── Worker A ── PR #101
       ├─ fix/payment     ── worktree/payment     ── Worker B ── PR #102
       └─ docs/runbook    ── worktree/runbook     ── Worker C ── PR #103
```

중요한 점은 worktree마다 별도의 `.git` 저장소를 새로 만드는 것이 아니라, 하나의 Git 저장소에 연결된 추가 작업 트리라는 것이다. 따라서 객체·브랜치 이력을 공유하면서 파일 작업 공간만 분리한다.[1]

## 2. CLI로 Worktree 만들기

먼저 기준 브랜치를 최신 상태로 맞춘다.

```bash
cd /path/to/repository
git fetch origin
git switch main
git pull --ff-only origin main
```

새 브랜치와 worktree를 동시에 만든다.

```bash
git worktree add -b feat/auth ../repo-auth origin/main
git worktree add -b fix/payment ../repo-payment origin/main
git worktree add -b docs/runbook ../repo-runbook origin/main
```

각 명령은 `origin/main`에서 새 브랜치를 만들고 지정한 경로에 checkout한다. 이후 작업자는 서로 다른 디렉터리에서 독립적으로 실행한다.

```bash
cd ../repo-auth
# Worker A: 인증 기능 구현·테스트

git status

git add .
git commit -m "feat: add authentication"
git push -u origin feat/auth
```

```bash
cd ../repo-payment
# Worker B: 결제 오류 수정·테스트

git status
git add .
git commit -m "fix: handle payment timeout"
git push -u origin fix/payment
```

기존 브랜치를 worktree에 연결할 수도 있다.

```bash
git worktree add ../repo-existing existing-branch
```

단, 같은 브랜치를 여러 worktree에서 동시에 checkout하는 것은 피해야 한다. Git은 작업 트리 간 branch 충돌을 방지하기 위해 이미 사용 중인 브랜치를 다시 checkout하지 못하게 한다.[1]

## 3. 브랜치·Worktree·Worker·PR 1:1 대응

가장 관리하기 쉬운 규칙은 다음과 같다.

| 작업 ID | 브랜치 | Worktree | Worker | PR | 담당 범위 |
| --- | --- | --- | --- | --- | --- |
| A | `feat/auth` | `../repo-auth` | Worker A | PR #101 | 인증 |
| B | `fix/payment` | `../repo-payment` | Worker B | PR #102 | 결제 오류 |
| C | `docs/runbook` | `../repo-runbook` | Worker C | PR #103 | 운영 문서 |

이 매핑을 작업 시작 시 기록하면 “어느 에이전트가 어느 파일을 고쳤는가”, “어느 PR이 어느 테스트 결과를 갖는가”를 추적하기 쉽다.

권장 메타데이터는 다음과 같다.

```yaml
work_id: A
task: authentication
branch: feat/auth
worktree: /workspace/repo-auth
worker: claude-code-a
base: main
pull_request: 101
status: testing
```

여러 에이전트를 사용할 때는 같은 worktree를 두 워커가 공유하지 않는 것이 원칙이다. 공유하면 생성 파일·lock 파일·빌드 산출물·미커밋 변경이 서로 섞여 원인 추적이 어려워진다.

## 4. GitHub에서 PR을 만드는 흐름

각 worktree에서 자신의 브랜치를 push한 뒤 PR을 만든다.

```bash
cd ../repo-auth
git push -u origin feat/auth
gh pr create \
  --base main \
  --head feat/auth \
  --title "feat: add authentication" \
  --body "## Summary
- Add authentication flow

## Test Plan
- Run auth unit tests
- Run integration tests"
```

GitHub의 PR은 head branch와 base branch를 비교한다. 따라서 `feat/auth → main`, `fix/payment → main`처럼 각 브랜치가 독립 PR이 된다.[2]

### 1:1 PR 원칙

- 하나의 작업 목표 = 하나의 브랜치
- 하나의 브랜치 = 하나의 worktree
- 하나의 worktree = 하나의 Worker/Agent
- 하나의 Worker 결과 = 하나의 PR
- PR의 CI 결과는 해당 branch commit에 귀속

이 원칙은 기능을 지나치게 잘게 쪼개라는 뜻이 아니다. 서로 충돌 가능성이 높거나 검증 단위가 다른 작업을 분리해 추적하라는 뜻이다.

## 5. 병렬 작업의 실제 실행 순서

```text
1. Orchestrator가 요구사항을 분해
2. main 최신 commit을 기준으로 작업 목록 생성
3. 작업별 branch/worktree 생성
4. Worker를 각 worktree에 1개씩 배정
5. Worker가 구현·테스트·커밋
6. 각 branch를 origin에 push
7. 각 branch에서 PR 생성
8. CI·Reviewer가 PR 단위로 검증
9. 순차 또는 의존성 순서대로 merge
10. main 최신화 후 worktree 정리
```

작업 의존성이 없다면 병렬 실행한다. 예를 들어 인증·문서·독립 테스트는 동시에 진행할 수 있다. 반대로 DB 스키마 변경과 그 스키마를 사용하는 API 구현처럼 선행 작업이 있으면, 먼저 스키마 PR을 merge하거나 후속 branch를 선행 branch에서 만들어야 한다.

## 6. Merge 순서와 충돌 관리

GitHub는 PR의 3-dot 비교를 사용해 base와 분기된 시점 이후 head branch가 도입한 변경을 보여준다.[2] base가 크게 변하면 각 PR을 최신 main과 맞춰야 한다.

```bash
cd ../repo-auth
git fetch origin
git rebase origin/main
# 충돌 해결 후
git add <resolved-files>
git rebase --continue
git push --force-with-lease origin feat/auth
```

공유 브랜치에 force push하는 것은 피하고, 해당 branch의 단독 소유자가 rebase 후 `--force-with-lease`를 사용하는 것이 안전하다. 보호된 main에는 직접 push하지 않고 PR과 필수 CI·리뷰를 통과시킨다. GitHub branch protection은 status check·review·CODEOWNERS·signed commit 등을 요구할 수 있다.[2]

PR 간 변경이 겹치면 다음 순서를 선택한다.

- 독립 작업: 둘 다 CI 통과 후 순차 merge
- 선행 관계: 선행 PR merge 후 후속 branch rebase
- 같은 파일 충돌: 담당자와 merge 순서 조정
- 긴 작업: 주기적으로 main을 branch에 반영
- 긴급 수정: 별도 `hotfix/*` worktree와 PR 사용

## 7. Hermes·Claude Code와 결합하는 구조

이 구조는 오케스트레이터와 코딩 워커를 분리할 때 유용하다.

```text
Hermes Orchestrator
  ├─ Worktree A: Claude Code Worker A → feat/auth → PR #101
  ├─ Worktree B: Claude Code Worker B → fix/payment → PR #102
  └─ Worktree C: Claude Code Worker C → docs/runbook → PR #103

Reviewer/Test
  ├─ PR #101 CI·리뷰
  ├─ PR #102 CI·리뷰
  └─ PR #103 CI·리뷰

Final Verification
  └─ merge 결과·배포 asset·운영 URL 재확인
```

Hermes가 작업을 분해하고 worktree·branch·worker·PR 매핑을 관리할 수는 있지만, 각 워커가 같은 파일·브랜치·배포 대상을 동시에 변경하지 않도록 해야 한다. 병렬이라는 이유만으로 Kubernetes apply·DB 변경·운영 rollout을 자동 실행하면 안 되며, 공유 시스템에 영향을 주는 단계는 별도 승인과 read-back 검증이 필요하다.

## 8. 정리 명령

PR이 merge되고 해당 worktree가 더 이상 필요하지 않으면 정리한다.

```bash
git worktree list
git worktree remove ../repo-auth
git branch -d feat/auth
git push origin --delete feat/auth
git worktree prune
```

아직 커밋하지 않은 변경이 있으면 `git worktree remove`가 거부할 수 있다. 먼저 `git status`와 `git diff`를 확인하고, 변경을 커밋·백업·폐기할지 결정한다. 강제 삭제는 복구가 어려울 수 있으므로 신중해야 한다.[1]

## 9. 자주 하는 실수

- worktree와 branch를 같은 개념으로 생각함
- 여러 Worker가 하나의 worktree를 공유함
- 같은 branch를 여러 worktree에서 checkout하려고 함
- base branch를 최신화하지 않고 오래 작업함
- PR 하나에 서로 무관한 작업을 섞음
- CI 통과를 배포 완료로 오해함
- merge 후 worktree 디렉터리만 지우고 Git 메타데이터를 남김
- `git push --force`로 다른 작업자의 branch를 덮어씀
- submodule이 있는 저장소에서 worktree 동작을 검증하지 않음

## 최종 체크리스트

- [ ] 작업별 브랜치가 있는가
- [ ] 브랜치별 독립 worktree가 있는가
- [ ] Worker와 worktree가 1:1인가
- [ ] PR head/base가 올바른가
- [ ] 각 PR의 CI가 해당 commit을 대상으로 성공했는가
- [ ] 충돌 가능 파일과 의존성을 확인했는가
- [ ] merge 후 배포 artifact·URL을 검증했는가
- [ ] worktree·local branch·remote branch를 정리했는가

## 확인된 사실과 미확인 범위

- **문서 확인:** Git worktree는 동일 저장소에서 여러 작업 트리를 관리하고, GitHub PR은 base와 head branch를 비교한다.[1][2][3]
- **설계 판단:** 브랜치·worktree·worker·PR 1:1 대응은 추적성과 충돌 격리를 위한 운영 패턴이다.
- **미확인:** 특정 프로젝트의 최적 Worker 수, 병렬 처리량, merge 순서는 저장소 구조·빌드 시간·작업 의존성에 따라 달라진다.

## 참고 자료

[1] [Git — git-worktree Documentation](https://git-scm.com/docs/git-worktree)

[2] [GitHub Docs — Branches and Pull Request Comparisons](https://docs.github.com/en/pull-requests/reference/branches)

[3] [GitHub Docs — Managing Worktrees in GitHub Desktop](https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-worktrees-in-github-desktop)

> ※ 이 글의 명령은 예시 경로와 브랜치명이다. 운영 저장소에 적용하기 전 `git status`, 현재 branch, remote URL, 보호 규칙을 확인해야 한다.

## Sources

[1] https://git-scm.com/docs/git-worktree
[2] https://docs.github.com/en/pull-requests/reference/branches
[3] https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-worktrees-in-github-desktop
