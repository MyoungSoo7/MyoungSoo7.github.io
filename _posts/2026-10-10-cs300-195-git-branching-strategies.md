---
layout: post
title: "[CS300 #195] Git 브랜치 전략 — Git Flow, GitHub Flow, 트렁크 기반 개발"
date: 2026-10-10 21:15:00 +0900
categories: [cs]
tags: [cs300, software-engineering, git, branching-strategy, trunk-based-development]
---

컴퓨터공학 300 주제 시리즈의 195번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

브랜치 전략은 "어떤 브랜치를 언제 만들고, 언제 어디로 합치는가" 에 대한 팀의 약속이다. 대표적으로 Git Flow, GitHub Flow, 트렁크 기반 개발이 있고, 고르는 기준은 **얼마나 자주 배포하는가**와 **여러 버전을 동시에 지원해야 하는가**다. 어느 전략이든 브랜치 수명이 짧을수록 병합이 쉽다.

## 왜 필요한가

앞 글에서 봤듯이 Git 에서 브랜치는 이름표 하나라 만들기 쉽다. 쉬워서 문제가 생긴다. 규칙이 없으면 `feature-login`, `kim-test`, `fix2`, `release-final` 같은 브랜치가 수십 개 쌓이고, 무엇이 배포됐는지, 무엇을 어디로 합쳐야 하는지 아무도 모른다.

브랜치 전략은 다음 질문에 답을 정해 둔다.

- 지금 운영에 나가 있는 코드는 어느 브랜치인가?
- 새 기능은 어디서 시작해서 어디로 들어가는가?
- 운영 장애를 긴급히 고칠 때는 어떻게 하는가?
- 다음 릴리스를 준비하는 동안 다른 개발은 어떻게 계속하는가?

## 핵심 개념

### 병합 방식부터: merge 와 rebase

브랜치를 합치는 방법은 크게 두 가지다.

```
merge (병합 커밋 생성)                   rebase (커밋을 옮겨 다시 쌓기)

main:    A──B──C───────M                 main:    A──B──C
              \       /                                   \
feature:       D──E──                    feature:          D'──E'
```

- [`git merge`](https://git-scm.com/docs/git-merge)는 두 갈래를 그대로 두고 둘을 잇는 병합 커밋 `M` 을 만든다. 역사가 실제로 일어난 그대로 남는다.
- [`git rebase`](https://git-scm.com/docs/git-rebase)는 feature 의 커밋들을 main 의 끝 위로 **새로 만들어** 쌓는다(`D'`, `E'` 는 내용은 같아도 ID 가 다른 새 커밋이다). 역사가 한 줄로 깔끔해진다.

rebase 는 커밋을 새로 만들기 때문에, **이미 다른 사람과 공유한 브랜치를 rebase 해서 강제 푸시하면** 그 사람의 역사와 어긋난다. Pro Git 의 규칙은 간단하다. 저장소 밖에 있는, 남이 작업 기반으로 삼았을 수 있는 커밋은 rebase 하지 않는다.

플랫폼의 PR 병합 버튼은 보통 세 가지를 제공한다. 병합 커밋 생성, 스쿼시 병합(feature 의 커밋 전체를 하나로 합쳐 올림), rebase 병합. 팀이 하나로 정해 두는 편이 역사를 읽기 쉽다.

### Git Flow

Vincent Driessen 이 2010년 [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/)에서 제안했다.

```
main     ●───────────────●──────────────●      (배포된 버전만, 태그)
          \             / \            /
hotfix     \           /   ●──────────●        (운영 긴급 수정)
            \         /                \
release      \   ●───●                  \      (릴리스 준비, 버그만 수정)
              \ /     \                  \
develop  ●─────●───────●───●──────────────●    (다음 릴리스 통합)
          \       /     \     /
feature    ●─────●       ●───●                 (기능 개발)
```

| 브랜치 | 수명 | 역할 |
|---|---|---|
| `main` | 영구 | 운영에 나간 버전. 병합할 때마다 버전 태그 |
| `develop` | 영구 | 다음 릴리스를 위한 통합 브랜치 |
| `feature/*` | 기능 하나 | `develop` 에서 갈라져 `develop` 으로 |
| `release/*` | 릴리스 준비 기간 | `develop` 에서 갈라져 `main` 과 `develop` 양쪽으로 |
| `hotfix/*` | 긴급 수정 | `main` 에서 갈라져 `main` 과 `develop` 양쪽으로 |

정해진 릴리스 주기가 있고, 여러 버전을 동시에 지원해야 하는 제품(설치형 소프트웨어, 모바일 앱)에 맞는다. 대신 브랜치가 많고 병합 경로가 복잡하다.

Driessen 본인도 2020년 글 머리에 "반성의 글(Note of reflection)" 을 덧붙였다. 웹 앱처럼 **지속적으로 배포**되고 여러 버전을 지원할 필요가 없는 소프트웨어라면 GitHub Flow 같은 더 단순한 흐름을 쓰라는 내용이다.

### GitHub Flow

[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)는 GitHub 문서의 표현대로 "가벼운 브랜치 기반 워크플로" 다.

```
main  ●──────●──────────●──────●     (항상 배포 가능)
       \    /  \       /
        ●──●    ●──●──●              (짧은 기능 브랜치 → PR → 리뷰 → 병합 → 배포)
```

1. `main` 에서 설명적인 이름의 브랜치를 만든다.
2. 커밋하고 푸시한다.
3. PR 을 열어 리뷰와 CI 를 받는다.
4. 병합하고, 브랜치를 지운다.

규칙은 하나다. **`main` 은 언제나 배포 가능해야 한다.** 그래서 CI 가 PR 단계에서 테스트를 통과시켜야 한다.

### 트렁크 기반 개발(Trunk-Based Development)

[trunkbaseddevelopment.com](https://trunkbaseddevelopment.com/)이 정리한 방식으로, 개발자들이 **하나의 브랜치(트렁크, 보통 `main`)에 자주**, 적어도 하루 한 번 이상 통합한다. 짧은 기능 브랜치를 쓰더라도 수명은 하루 이틀이다.

아직 완성되지 않은 기능은 어떻게 하나? 코드는 트렁크에 넣되 **기능 플래그(feature flag)** 로 꺼 둔다. "코드 배포" 와 "기능 공개" 를 분리하는 것이다. 큰 구조 변경은 새 구현을 옆에 만들고 추상화 계층 뒤에서 조금씩 갈아 끼우는 "추상화에 의한 브랜치(branch by abstraction)" 로 한다.

### 비교

| 기준 | Git Flow | GitHub Flow | 트렁크 기반 |
|---|---|---|---|
| 영구 브랜치 | `main`, `develop` | `main` | `main` |
| 기능 브랜치 수명 | 기능 완성까지(길 수 있음) | 짧게(PR 단위) | 매우 짧게(하루 이틀) 또는 없음 |
| 배포 주기 | 정해진 릴리스 | 병합할 때마다 | 수시로 |
| 여러 버전 동시 지원 | 쉽다 | 어렵다 | 릴리스 브랜치를 따로 따서 지원 |
| 미완성 기능 | 브랜치에 숨긴다 | 브랜치에 숨긴다 | 기능 플래그로 숨긴다 |
| 전제 조건 | 릴리스 관리 인력 | 좋은 CI | 매우 좋은 CI, 기능 플래그 |

## 직접 해 보기

브랜치를 오래 살려 두면 왜 병합이 힘들어질까. 단순한 확률 모형으로 감을 잡아 본다. 파일 200개짜리 저장소에서 개발자 6명이 각자 하루에 파일 3개씩 무작위로 고친다고 **가정**하고, 내 브랜치가 살아 있는 동안 내가 고친 파일과 다른 사람들이 고친 파일이 하나라도 겹칠 확률을 추정한다. 겹친다고 반드시 충돌은 아니지만, 충돌은 겹치는 곳에서만 생긴다.

```python
import random

FILES = 200            # 저장소의 파일 수 (가정)
TOUCH_PER_DAY = 3      # 개발자 한 명이 하루에 고치는 파일 수 (가정)
DEVS = 6
TRIALS = 2000

def overlap_rate(branch_days, seed=7):
    """내 브랜치가 사는 동안 다른 사람들이 main 에 병합한 변경과
    내가 고친 파일이 하나라도 겹칠 확률(= 병합 충돌 후보)을 추정한다."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(TRIALS):
        mine = set()
        others = set()
        for _ in range(branch_days):
            mine.update(rng.sample(range(FILES), TOUCH_PER_DAY))
            for _ in range(DEVS - 1):
                others.update(rng.sample(range(FILES), TOUCH_PER_DAY))
        hits += bool(mine & others)
    return hits / TRIALS

print("브랜치 수명  겹칠 확률")
for days in (1, 2, 3, 5, 10):
    p = overlap_rate(days)
    print(f"{days:>4}일      {p:6.1%}  {'#' * round(p * 40)}")
```

실행 결과:

```
브랜치 수명  겹칠 확률
   1일       20.1%  ########
   2일       60.6%  ########################
   3일       87.8%  ###################################
   5일       99.6%  ########################################
  10일      100.0%  ########################################
```

숫자 자체는 가정에 따라 얼마든지 달라진다. 실제 저장소에서는 자주 고치는 파일이 몰려 있어서 겹침이 더 잦을 수도 있다. 주목할 것은 **모양**이다. 브랜치 수명이 두 배가 되면 위험은 두 배보다 빨리 커진다. 내가 고친 파일 집합과 남이 고친 파일 집합이 **둘 다** 시간에 따라 커지기 때문이다. 트렁크 기반 개발이 "하루에 한 번은 통합하라" 고 하는 근거가 이 모양이다.

## 현업에서는

- **대부분의 웹 서비스 팀은 GitHub Flow 계열이다.** PR 단위의 짧은 브랜치, 보호된 `main`, 병합 시 자동 배포. 여기에 기능 플래그를 더하면 트렁크 기반에 가까워진다.
- **모바일 앱과 설치형 제품은 릴리스 브랜치가 필요하다.** 앱 스토어 심사 중인 버전, 이미 배포된 이전 버전의 보안 패치를 동시에 다뤄야 하기 때문이다.
- **보호 브랜치로 규칙을 강제한다.** `main` 에 직접 푸시 금지, PR 리뷰 승인 필수, CI 통과 필수 같은 규칙을 플랫폼 설정으로 걸어 두면 "급해서 그냥 푸시했다" 가 사라진다.
- **GitOps 저장소는 환경을 브랜치가 아니라 디렉터리로 나누는 경우가 많다.** 홈랩 클러스터의 매니페스트 저장소에서 `dev`/`prod` 를 브랜치로 나누면 두 브랜치가 서서히 갈라져 병합이 지옥이 된다. 한 브랜치 안에 `overlays/dev`, `overlays/prod` 처럼 디렉터리로 나누면 차이가 diff 한 번으로 보인다.

## 확인 문제

1. `merge` 와 `rebase` 가 역사에 남기는 모양의 차이를 설명하라.
2. 이미 공유한 브랜치를 rebase 한 뒤 강제 푸시하면 왜 문제가 되는가?
3. Git Flow 에서 `hotfix` 브랜치는 어디서 갈라져 어디로 병합되는가?
4. 트렁크 기반 개발에서 미완성 기능을 트렁크에 넣으면서도 사용자에게 보이지 않게 하는 방법은?
5. 위 모형에서 브랜치 수명이 늘 때 겹칠 확률이 선형보다 빠르게 커지는 이유는?

### 풀이

1. `merge` 는 두 갈래를 보존하고 병합 커밋으로 잇는다. `rebase` 는 한쪽 커밋을 다른 쪽 끝 위에 새 커밋으로 다시 쌓아 한 줄 역사를 만든다.
2. rebase 는 같은 내용의 새 커밋(새 ID)을 만들기 때문에, 원래 커밋을 기반으로 작업한 다른 사람의 역사와 갈라져 중복 커밋과 혼란스러운 병합이 생긴다.
3. `main` 에서 갈라져 `main` 과 `develop` 양쪽으로 병합된다.
4. 기능 플래그로 기능을 꺼 둔다. 큰 구조 변경은 추상화에 의한 브랜치로 점진적으로 교체한다.
5. 내가 고친 파일 집합과 다른 사람들이 고친 파일 집합이 둘 다 시간에 따라 커지므로, 겹칠 기회가 두 크기의 곱처럼 늘어나기 때문이다.

## 더 읽을거리 (References)

- Vincent Driessen, [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/) (2010, 2020년 반성의 글 포함)
- GitHub Docs, [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)
- Paul Hammant 외, [Trunk Based Development](https://trunkbaseddevelopment.com/)
- Pro Git, [3.4 Git Branching — Branching Workflows](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
- Git 공식 문서, [git-rebase](https://git-scm.com/docs/git-rebase), [git-merge](https://git-scm.com/docs/git-merge)
