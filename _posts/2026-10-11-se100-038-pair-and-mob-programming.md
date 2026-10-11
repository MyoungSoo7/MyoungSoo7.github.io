---
layout: post
title: "[SE100 #038] 페어 프로그래밍과 몹 프로그래밍"
date: 2026-10-11 17:00:02 +0900
categories: [software-engineering]
tags: [se100, code-quality, pair-programming, mob-programming, extreme-programming]
---

소프트웨어 공학 100 주제 시리즈의 38번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

페어·몹 프로그래밍은 "두 명이 한 명 몫을 한다" 는 생산성 기법이 아니라 **리뷰, 지식 전파, 설계 결정을 작성 시점으로 당겨 오는** 협업 방식이다. 실증 연구는 "항상 더 빠르다" 를 지지하지 않는다. 언제 효과가 있는지 골라 쓰는 것이 핵심이다.

## 왜 필요한가

혼자 짜고 나중에 리뷰받는 흐름에는 구조적 지연이 있다. PR 이 올라올 때쯤 설계는 이미 굳었고, 리뷰어는 수백 줄의 diff 앞에서 표면만 본다. 한 사람만 아는 모듈이 생기고, 그 사람이 휴가를 가면 장애 대응이 멈춘다. [코드 리뷰]({% post_url 2026-10-10-cs300-190-code-review %})가 사후 검토라면, 페어링은 작성과 검토를 동시에 한다.

반대로 무조건 페어링을 강제하는 팀은 피로, 회의 같은 하루, 주니어의 수동적 관찰이라는 비용을 치른다. 둘 다 피하려면 원전이 말하는 방식과 실증 결과를 함께 봐야 한다.

## 핵심 개념

### 기원: XP 의 실천법

페어 프로그래밍은 Kent Beck 의 *Extreme Programming Explained*(Addison-Wesley, 1999; 2판 Cynthia Andres 공저, 2004)에서 XP 의 핵심 실천법 중 하나로 널리 알려졌다. Laurie Williams, Robert Kessler, Ward Cunningham, Ron Jeffries 의 [Strengthening the Case for Pair Programming](https://doi.org/10.1109/52.854064)(IEEE Software, 2000)은 업계가 오래 실천해 왔지만 해 보지 않은 사람은 자원 낭비로 여긴다는 문제의식에서 출발해, 페어링이 더 짧은 시간에 더 나은 결과물과 더 자신감 있는 개발자를 만든다고 주장했다. 다만 이 글은 주장을 담은 잡지 기고이므로, 효과의 크기는 아래의 통제 실험과 함께 읽는 편이 안전하다.

### 실증: 전문가 295명 실험

가장 자주 인용되는 대규모 통제 실험은 Arisholm, Gallis, Dybå, Sjøberg 의 [Evaluating Pair Programming with Respect to System Complexity and Programmer Expertise](https://doi.org/10.1109/TSE.2007.17)(IEEE TSE, 2007)다. 노르웨이, 스웨덴, 영국의 컨설팅 회사 29곳에서 Java 전문가 295명(개인 99명, 페어 98쌍)을 하루 고용해 복잡도가 다른 두 시스템에 변경 작업을 시켰다. 초록이 보고하는 결과는 다음과 같다.

| 조건 | 결과 |
|---|---|
| 전체 | 페어링이 정답까지 걸리는 시간을 줄이거나 정답 비율을 높인다는 가설은 **지지되지 않음**. 정답을 내는 데 든 노력(인시)은 **84% 증가** |
| 복잡한 시스템 | 정답 비율 **48% 증가**, 시간 차이는 유의하지 않음. 이득은 **주로 주니어**에게서 |
| 단순한 시스템 | 시간 **20% 감소**, 정답률 차이는 유의하지 않음. 이득은 **주로 중급·시니어**에게서 |

저자들은 더 크고 복잡한 과제나 오래 함께 일한 페어라면 이득이 더 클 수 있다고 덧붙인다. 실무적으로 읽으면 이렇다. **복잡하고 낯선 일 + 경험 차가 있는 조합**에서 품질 이득이 크고, **단순한 일**에서는 숙련자끼리의 속도 이득 정도이며, 어느 경우든 **인시 비용은 늘어난다**. 단 이 실험은 하루짜리 과제라서, 페어링의 장기 효과로 꼽히는 지식 전파와 버스 팩터 개선은 재지 않았다.

### 스타일

Birgitta Böckeler 와 Nina Siessegger 의 [On Pair Programming](https://martinfowler.com/articles/on-pair-programming.html)(2020)이 정리한 대표 스타일이다.

| 스타일 | 방식 | 잘 맞는 상황 |
|---|---|---|
| 드라이버·내비게이터 | 드라이버는 키보드를 잡고 눈앞의 작은 목표에, 내비게이터는 관찰하며 더 큰 그림·다음 단계·위험에 집중 | 일반적 기본형 |
| 핑퐁 | A 가 실패하는 테스트 작성 → B 가 통과시키고 다음 실패 테스트 작성 → 반복, 사이사이 함께 리팩터링 | TDD 로 풀 수 있는 명확한 과제 |
| 강한 스타일(strong-style) | "아이디어가 머리에서 컴퓨터로 가려면 반드시 **다른 사람의 손**을 거쳐야 한다" | 지식 전수, 온보딩 |

강한 스타일의 황금률은 Llewellyn Falco 의 [글](http://llewellynfalco.blogspot.com/2014/06/llewellyns-strong-style-pairing.html)(2014)에서 왔다. 경험자가 내비게이터로 말하고 초심자가 드라이버로 타이핑한다. Böckeler 등은 이 방식이 마이크로매니지먼트에 가까워질 수 있으니 "왜" 에 대한 논의는 세션 뒤로 미루되 반드시 하라고 조언한다.

같은 글은 이점(지식 공유, 집중 유지, 실시간 코드 리뷰, 집단 코드 소유, 팀 WIP 감소, 빠른 온보딩)과 함께 도전도 명시한다. 페어링은 지치고, 회의에 끊기며, 실력 차와 권력 관계가 작동하고, 혼자 생각할 시간이 없다. 피로 관리를 위해 25분 작업 후 짧은 휴식을 두는 뽀모도로 기법을 권한다.

### 몹 프로그래밍(앙상블)

Woody Zuill 은 몹 프로그래밍을 [mobprogramming.org](https://mobprogramming.org/)에서 이렇게 요약한다.

> 모든 뛰어난 사람들이 같은 일을, 같은 시간에, 같은 공간에서, 같은 컴퓨터로.

한 명이 타이피스트, 나머지가 함께 내비게이션하며 짧은 간격으로 역할을 돌린다. 원격 팀을 위한 실천은 Simon Harrer, Jochen Christ, Martin Huber 의 [Remote Mob Programming](https://www.remotemobprogramming.org/)이 정리했다. 소규모 팀, 카메라 켜기, 화면 공유, **10분 간격 교대**, 그리고 임시 브랜치에 WIP 커밋을 올려 다음 사람에게 넘기는 **Git 핸드오버**가 핵심이다. 이를 자동화한 [mob](https://mob.sh/) 도구는 `mob start`, `mob next`, `mob done` 세 명령으로 교대를 처리한다.

### 페어 vs 몹 vs 혼자 + 리뷰

| | 혼자 + 비동기 리뷰 | 페어 | 몹 |
|---|---|---|---|
| 피드백 시점 | 작성 후 | 작성 중 | 작성 중, 전원 |
| 인시 비용 | 낮음 | 높음 | 가장 높음 |
| 지식 전파 | 리뷰어 1~2명 | 2명 + 로테이션 | 팀 전체 |
| 적합한 일 | 명확·반복적 | 복잡·낯섦, 온보딩 | 팀 전체가 합의해야 할 설계, 어려운 장애, 새 영역 개척 |
| 대기 | 리뷰 대기 큐 | 없음 | 없음 |

## 실무 적용

### 페어링을 고르는 기준

```
과제가 복잡하거나 낯선가? ─ 예 ─▶ 페어 (경험 차가 있으면 강한 스타일)
        │아니오
한 사람만 아는 영역인가? ─ 예 ─▶ 페어 + 로테이션 (지식 전파가 목적)
        │아니오
팀 전체의 합의가 필요한 설계인가? ─ 예 ─▶ 몹 (시간 상자 1~2시간)
        │아니오
혼자 작성 + 작은 PR 리뷰
```

### 세션 템플릿

```
[시작 5분]  오늘의 목표 1개, 작은 목표 목록(테스트 이름이나 커밋 메시지로), 끝나는 시각
[작업]      25분 단위, 교대할 때 역할 전환. 내비게이터는 큰 생각을 메모로 미루고 흐름을 끊지 않기
[휴식]      매 단위 사이 5분, 3~4단위 후 긴 휴식
[끝 5분]    무엇을 배웠나, 다음에 바꿀 것 하나, 미뤄 둔 "왜" 질문 정리
```

### 원격과 커밋 기록

화면 공유만으로도 되지만, [Live Share](https://learn.microsoft.com/en-us/visualstudio/liveshare/) 같은 공동 편집 도구를 쓰면 교대 비용이 줄어든다. 함께 만든 커밋은 GitHub 이 인식하는 [`Co-authored-by:` 트레일러](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors)로 공동 저자를 남긴다.

```
Add retry budget to payment client

Co-authored-by: Kim Dev <kim@example.com>
```

### 리뷰 정책과의 연결

페어로 작성한 변경을 다시 같은 강도로 비동기 리뷰하면 비용이 이중으로 든다. 예를 들어 "페어·몹으로 작성한 변경은 참여하지 않은 1명의 가벼운 승인으로 갈음" 같은 규칙을 팀이 정할 수 있다. 다만 감사·규제 요구가 있는 저장소라면 그 요구가 우선한다.

## 흔한 오해와 함정

- **"페어링은 항상 더 빠르다."** 대규모 실험에서 전체적으로는 지지되지 않았고, 노력은 늘었다. 이득은 과제 복잡도와 경험 조합에 따라 다르다.
- **"내비게이터는 쉬는 사람."** 내비게이터의 일은 전략적 관찰과 다음 단계 준비다. 휴대폰을 보는 내비게이터는 페어링이 아니다.
- **"시니어가 키보드를 독점."** 주니어는 구경꾼이 된다. 강한 스타일로 역할을 뒤집거나 타이머로 강제 교대한다.
- **하루 종일 페어링.** 지친다. 혼자 생각하고 조사할 시간을 일정에 남긴다.
- **몹을 회의처럼 운영.** 타이피스트 교대 없이 한 사람이 화면을 공유하고 나머지가 구경하면 몹이 아니라 시연이다.

## 확인 문제

1. Arisholm 등(2007)의 실험에서 복잡한 시스템과 단순한 시스템의 결과는 각각 어땠고, 이득은 누구에게서 주로 나타났는가?
2. 드라이버·내비게이터 방식에서 두 역할의 사고 수준은 어떻게 다른가?
3. 강한 스타일 페어링의 황금률은 무엇이며 어떤 상황에 적합한가?
4. 원격 몹 프로그래밍에서 "Git 핸드오버" 가 필요한 이유와 방법은?

### 풀이

1. 복잡한 시스템에서는 정답 비율이 48% 늘고 시간 차는 유의하지 않았으며 이득은 주로 주니어에게서, 단순한 시스템에서는 시간이 20% 줄고 정답률 차는 유의하지 않았으며 이득은 주로 중급·시니어에게서 나타났다. 전체 노력은 84% 늘었다.
2. 드라이버는 눈앞의 작은 목표와 코드 줄 단위의 전술적 사고를, 내비게이터는 큰 그림·다음 단계·위험을 보는 전략적 사고를 맡는다.
3. "아이디어가 머리에서 컴퓨터로 가려면 반드시 다른 사람의 손을 거쳐야 한다." 경험자가 내비게이터, 초심자가 드라이버가 되는 지식 전수와 온보딩에 적합하다.
4. 원격에서는 키보드를 물리적으로 넘길 수 없다. 임시 브랜치에 WIP 커밋을 올려 다음 사람이 받아 이어 가고, 세션이 끝나면 WIP 커밋을 의미 있는 커밋으로 합쳐 메인에 반영한다.

## 더 읽을거리 (References)

- Kent Beck, Cynthia Andres, *Extreme Programming Explained: Embrace Change*, 2nd ed., Addison-Wesley, 2004 (서지 정보)
- L. Williams, R. Kessler, W. Cunningham, R. Jeffries, "Strengthening the Case for Pair Programming", *IEEE Software* 17(4), 2000, [DOI](https://doi.org/10.1109/52.854064)
- E. Arisholm, H. Gallis, T. Dybå, D. Sjøberg, "Evaluating Pair Programming with Respect to System Complexity and Programmer Expertise", *IEEE TSE* 33(2), 2007, [DOI](https://doi.org/10.1109/TSE.2007.17)
- J. Hannay, T. Dybå, E. Arisholm, D. Sjøberg, "The effectiveness of pair programming: A meta-analysis", *IST* 51(7), 2009, [DOI](https://doi.org/10.1016/j.infsof.2009.02.001)
- Birgitta Böckeler, Nina Siessegger, [On Pair Programming](https://martinfowler.com/articles/on-pair-programming.html), 2020
- Llewellyn Falco, [Llewellyn's strong-style pairing](http://llewellynfalco.blogspot.com/2014/06/llewellyns-strong-style-pairing.html), 2014
- [Mob Programming](https://mobprogramming.org/), [Remote Mob Programming](https://www.remotemobprogramming.org/), [mob.sh](https://mob.sh/)
