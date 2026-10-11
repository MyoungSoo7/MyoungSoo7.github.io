---
layout: post
title: "[SE100 #052] 트렁크 기반 개발"
date: 2026-10-11 17:03:35 +0900
categories: [software-engineering]
tags: [se100, delivery, trunk-based-development, branching, continuous-integration]
---

소프트웨어 공학 100 주제 시리즈의 52번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

트렁크 기반 개발(Trunk-Based Development, TBD)은 모든 개발자가 하나의 공유 브랜치(trunk, main)에 적어도 하루 한 번 통합하고, 장기 브랜치를 만들지 않기 위해 피처 플래그와 추상화를 통한 분기(branch by abstraction) 같은 기법을 쓰는 브랜치 모델이다. 핵심은 브랜치 전략이 아니라 **통합 지연을 없애는 것**이다.

## 왜 필요한가

Git Flow, GitHub Flow, TBD 의 기본 비교는 [Git 브랜치 전략]({% post_url 2026-10-10-cs300-195-git-branching-strategies %})에서 다뤘다. 이 글은 TBD 를 실제로 굴릴 때의 규칙과 기법, 그리고 왜 그것이 지속적 통합의 전제인지에 집중한다.

장기 브랜치의 비용은 병합 충돌 그 자체가 아니다. 진짜 비용은 **서로의 변경을 모르는 시간**이다. 두 사람이 3주간 각자 브랜치에서 일하면, 둘의 코드는 각자 테스트를 통과하지만 합쳤을 때의 동작은 아무도 검증하지 않은 상태로 3주가 흐른다. 이것이 흔히 말하는 "병합 지옥(merge hell)" 이고, 그 결과로 통합 단계, 코드 프리즈, 안정화 스프린트가 생긴다.

## 핵심 개념

### 정의

[trunkbaseddevelopment.com](https://trunkbaseddevelopment.com/)(Paul Hammant 가 운영)의 한 줄 정의는 이렇다.

> 개발자들이 'trunk' 라는 단일 브랜치에서 협업하고, 문서화된 기법을 사용해 다른 장기 개발 브랜치를 만들라는 압력에 저항하는 소스 관리 브랜치 모델. 그 결과 병합 지옥을 피하고, 빌드를 깨뜨리지 않는다.

같은 사이트는 TBD 를 지속적 통합의 핵심 조건으로 설명한다. 팀원 모두가 **최소 24시간에 한 번** trunk 에 커밋한다는 CI 의 핵심 요구가, 하루 여러 번 trunk 에 커밋하는 팀에서는 자연스럽게 충족된다는 것이다. Martin Fowler 의 [Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html) 글도 같은 요구를 "모두가 매일 mainline 에 커밋한다" 로 표현한다.

### DORA 가 제시하는 측정 가능한 기준

[DORA 의 trunk-based development 역량 문서](https://dora.dev/capabilities/trunk-based-development/)는 TBD 를 하고 있는지 판단하는 실천 항목을 구체적으로 적는다.

| 실천 | 무엇을 재는가 |
|---|---|
| 저장소의 활성 브랜치를 셋 이하로 유지 | 활성 브랜치 수 |
| 적어도 하루 한 번 trunk 에 병합 | 브랜치 수명, 병합 빈도 |
| 코드 프리즈와 통합 단계를 두지 않음 | 프리즈 기간 존재 여부 |

같은 문서는 흔한 실패 원인으로 **여러 명의 승인을 요구하는 무거운 코드 리뷰 절차**를 든다. 리뷰가 몇 시간, 며칠씩 걸리면 개발자는 변경을 모아 큰 PR 을 만들고, 큰 PR 은 리뷰가 더 오래 걸려 악순환이 된다. 처방은 페어 프로그래밍이나 동기식 리뷰로 리뷰 대기 시간을 줄이는 것이다.

### 두 가지 규모

```
소규모 팀: trunk 에 직접 커밋
  dev A ──commit──┐
  dev B ──commit──┼──▶ trunk ──▶ CI ──▶ 배포 가능 상태
  dev C ──commit──┘

확장형: 짧은 수명의 피처 브랜치 (1~2일)
  feature/x ─┐ (PR, 리뷰, CI)
  feature/y ─┼──▶ trunk
  feature/z ─┘   └─ 규모가 더 크면 merge queue
```

[short-lived feature branches](https://trunkbaseddevelopment.com/short-lived-feature-branches/) 방식에서도 브랜치는 코드 리뷰와 CI 검사용일 뿐, 그 브랜치에서 산출물을 만들어 배포하지 않는다. 산출물은 trunk 에서만 나온다. 커밋 빈도가 아주 높은 조직은 GitHub 의 [merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) 같은 장치로 "PR 단독으로는 통과하지만 합치면 깨지는" 경우를 막는다.

### 장기 브랜치 없이 큰 변경을 하는 법

TBD 의 진짜 기술은 "몇 주 걸리는 작업을 어떻게 매일 trunk 에 넣느냐" 다.

**1) 피처 플래그.** 미완성 기능을 꺼진 상태로 trunk 에 넣는다. Pete Hodgson 의 분류로는 Release Toggle 이 이 용도다(SE100 #057 에서 자세히 다룬다).

**2) 추상화를 통한 분기(Branch by Abstraction).** Fowler 의 [BranchByAbstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)에 정리된 기법이다. 대규모 교체를 버전 관리 브랜치가 아니라 **코드 안의 추상화 계층**으로 분기한다.

```
1단계: 호출부 ──▶ 기존 구현
2단계: 호출부 ──▶ [추상화] ──▶ 기존 구현          (추상화 도입, 동작 불변)
3단계: 호출부 ──▶ [추상화] ──┬▶ 기존 구현
                            └▶ 새 구현 (점진 작성, 플래그로 일부만)
4단계: 호출부 ──▶ [추상화] ──▶ 새 구현            (기존 구현 삭제)
5단계: (선택) 추상화 제거
```

각 단계가 trunk 에 들어가도 시스템은 계속 동작하고 배포 가능하다.

**3) 병행 변경(Parallel Change, expand-contract).** [ParallelChange](https://martinfowler.com/bliki/ParallelChange.html)는 인터페이스를 바꿀 때 새 방식을 추가(expand)하고, 호출부를 옮기고(migrate), 옛 방식을 지우는(contract) 세 단계로 나눈다. DB 컬럼 이름 변경처럼 한 번에 바꾸면 배포 순서에 따라 깨지는 변경에 특히 유용하다.

### 릴리스 브랜치는 허용되는가

TBD 에서도 릴리스 브랜치는 쓸 수 있다. 조건이 있다. [Branch for release](https://trunkbaseddevelopment.com/branch-for-release/) 문서는 **버그는 trunk 에서 고치고 릴리스 브랜치로 체리픽**하라고 하고, 릴리스 브랜치에서 고친 뒤 trunk 로 가져오기를 기대하지 말라고 명시한다. 거꾸로 하면 수정이 trunk 에 빠지는 회귀가 생긴다. 하루 여러 번 배포하는 팀은 [release from trunk](https://trunkbaseddevelopment.com/release-from-trunk/)처럼 릴리스 브랜치 자체가 필요 없다.

### Fowler 의 패턴 언어로 보면

Fowler 의 [Patterns for Managing Source Code Branches](https://martinfowler.com/articles/branching-patterns.html)(2020)는 브랜치 전략을 패턴들의 조합으로 설명한다. TBD 는 다음 패턴을 강하게 적용한 형태다.

| 패턴 | TBD 에서의 모습 |
|---|---|
| Mainline | trunk 하나가 진실의 원천 |
| Healthy Branch | 매 커밋마다 자동 검사로 trunk 를 녹색 유지 |
| Mainline Integration + 높은 Integration Frequency | 최소 하루 한 번 |
| Release-Ready Mainline | trunk 는 언제든 배포 가능 |

## 실무 적용

### 전환 체크리스트

```
[ ] trunk 의 빌드+테스트가 10분 안팎으로 끝나는가 (느리면 하루 여러 번 통합이 고통)
[ ] 실패한 trunk 빌드를 최우선으로 고치는 팀 규칙이 있는가
[ ] 활성 브랜치 수와 브랜치 평균 수명을 대시보드로 보는가
[ ] PR 크기 상한(예: 변경 400줄)을 팀 합의로 두었는가
[ ] 리뷰 응답 시간 목표가 있는가
[ ] 피처 플래그 라이브러리와 플래그 정리 규칙이 있는가
[ ] DB 마이그레이션을 expand-contract 로 나누는 습관이 있는가
```

### 브랜치 수명 측정 스크립트

```python
# 원격 브랜치별 마지막 커밋이 main 에서 얼마나 갈라져 있는지 본다
import subprocess, datetime

def sh(*a): return subprocess.check_output(a, text=True).strip()

for ref in sh("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").splitlines():
    if ref.endswith(("/main", "/HEAD")):
        continue
    base = sh("git", "merge-base", "origin/main", ref)
    ahead = int(sh("git", "rev-list", "--count", f"{base}..{ref}"))
    first = sh("git", "log", "--reverse", "--format=%ct", f"{base}..{ref}").splitlines()
    age_days = (datetime.datetime.now().timestamp() - int(first[0])) / 86400 if first else 0
    flag = "  <-- 장기 브랜치" if age_days > 2 else ""
    print(f"{ref:40} 커밋 {ahead:3}개, 분기 후 {age_days:5.1f}일{flag}")
```

숫자 "2일" 은 팀이 정하는 임계값이다. 중요한 것은 측정해서 보이게 만드는 것이다.

## 흔한 오해와 함정

- **"TBD = 리뷰 없이 main 에 push."** 소규모 팀의 한 가지 형태일 뿐이다. 짧은 PR 과 리뷰를 쓰는 TBD 가 더 흔하다. 기준은 리뷰 유무가 아니라 브랜치 수명이다.
- **"TBD 는 테스트 자동화 없이도 된다."** 거꾸로다. 하루 수십 번의 통합을 사람이 확인할 수는 없다. 빠르고 믿을 수 있는 자동 테스트가 전제 조건이다.
- **플래그 부채.** 피처 플래그로 장기 브랜치를 없앴는데 플래그를 지우지 않으면, 브랜치 대신 코드 안에 조건문이 쌓인다. 플래그에도 만료일이 필요하다.
- **릴리스 브랜치에서 버그 수정.** trunk 로 역이식하는 것을 잊으면 다음 릴리스에서 같은 버그가 되살아난다.
- **trunk 가 빨간 채로 방치.** 모두가 trunk 를 기반으로 일하므로 깨진 trunk 는 팀 전체를 멈춘다. "깨뜨린 사람이 즉시 고치거나 되돌린다" 가 기본 규칙이다.

## 확인 문제

1. 장기 브랜치의 본질적 비용을 "병합 충돌" 이 아닌 다른 말로 설명하라.
2. DORA 가 제시하는 TBD 의 세 가지 실천은 무엇인가?
3. 결제 모듈을 새 라이브러리로 교체하는 데 4주가 걸린다. 장기 브랜치 없이 진행하는 방법을 단계로 설명하라.
4. 릴리스 브랜치에서 발견된 버그를 어디서 먼저 고쳐야 하며, 그 이유는?
5. 무거운 코드 리뷰 절차가 TBD 를 무너뜨리는 경로를 설명하라.

### 풀이

1. 서로의 변경이 합쳐진 상태를 아무도 검증하지 않는 시간이 길어지는 것. 그 사이 쌓인 의미적 충돌은 통합 시점에 한꺼번에 드러난다.
2. 활성 브랜치를 셋 이하로 유지, 적어도 하루 한 번 trunk 에 병합, 코드 프리즈와 통합 단계를 두지 않음.
3. Branch by Abstraction: 기존 결제 호출을 감싸는 인터페이스를 먼저 도입(동작 불변)해 trunk 에 넣고, 새 구현을 인터페이스 뒤에서 점진적으로 작성해 매일 trunk 에 넣되 플래그로 꺼 두거나 일부 트래픽에만 켠다. 검증이 끝나면 기존 구현을 지운다.
4. trunk 에서 먼저 고치고 릴리스 브랜치로 체리픽한다. 릴리스 브랜치에서만 고치면 trunk 로 옮기는 것을 잊기 쉽고, 다음 릴리스에서 회귀가 생긴다.
5. 리뷰가 오래 걸리면 개발자는 리뷰 횟수를 줄이려 변경을 모아 큰 PR 을 만든다. 큰 PR 은 리뷰가 더 어렵고 느려 브랜치 수명이 늘어나며, 결국 장기 브랜치와 같은 상태가 된다.

## 더 읽을거리 (References)

- Paul Hammant 외, [Trunk Based Development](https://trunkbaseddevelopment.com/)
- DORA, [Capabilities: Trunk-based development](https://dora.dev/capabilities/trunk-based-development/)
- Martin Fowler, [Patterns for Managing Source Code Branches](https://martinfowler.com/articles/branching-patterns.html), 2020
- Martin Fowler, [Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)
- Martin Fowler, [BranchByAbstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)
- Danilo Sato, [ParallelChange](https://martinfowler.com/bliki/ParallelChange.html)
- Rachel Potvin, Josh Levenberg, [Why Google Stores Billions of Lines of Code in a Single Repository](https://doi.org/10.1145/2854146), Communications of the ACM, 2016 — 거대 단일 저장소에서 trunk 기반으로 일하는 사례
- CS300: [Git 브랜치 전략]({% post_url 2026-10-10-cs300-195-git-branching-strategies %})
