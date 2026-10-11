---
layout: post
title: "[SE100 #074] 스토리 포인트와 플래닝 포커"
date: 2026-10-11 17:06:57 +0900
categories: [software-engineering]
tags: [se100, project-management, story-points, planning-poker, velocity]
---

소프트웨어 공학 100 주제 시리즈의 74번째 글이다. (카테고리: 프로젝트 관리와 추정)

## 한 줄 요약

스토리 포인트는 작업의 크기를 시간이 아니라 **서로에 대한 상대 크기**로 매기는 단위다. 플래닝 포커는 그 숫자를 **각자 몰래 고른 뒤 동시에 공개**해서, 숫자보다 **서로 다른 가정**을 드러내는 기법이다. 둘 다 계획을 돕는 도구이지 팀을 평가하는 지표가 아니다.

## 왜 필요한가

시간 단위 추정에는 두 가지 고질병이 있다.

1. **"이상적인 하루" 와 "달력의 하루" 가 다르다.** 회의, 리뷰, 장애 대응을 빼고 나면 하루에 쓸 수 있는 시간은 생각보다 적다.
2. **가장 목소리 큰 사람의 숫자가 기준점이 된다.** 시니어가 "이틀이면 되죠" 라고 먼저 말하면 나머지는 그 숫자 근처로 끌려간다.

Ron Jeffries 의 [회고](https://ronjeffries.com/articles/019-01ff/story-points/Index.html)는 첫 번째 문제를 생생하게 보여 준다. 초기 XP 팀은 스토리를 "이상적인 날(ideal days)" 로 추정하고 "부하 계수(load factor)" 를 곱해 실제 기간으로 바꿨다. 부하 계수는 대략 3이었다. 그러자 이해관계자들은 "하루짜리 일이 왜 계속 사흘 걸리느냐" 며 혼란스러워했다. 그래서 단위 이름을 그냥 "포인트" 로 바꿨다는 것이다. 두 번째 문제를 풀려고 나온 것이 플래닝 포커다.

## 핵심 개념

### 상대 추정과 속도(velocity)

Martin Fowler 는 [StoryPoint](https://martinfowler.com/bliki/StoryPoint.html)에서 초기 애자일, 특히 XP 커뮤니티의 경험을 이렇게 정리한다. 시간으로 추정하면 쓸 만한 숫자가 잘 안 나왔고, 가장 효과적인 방법은 **스토리끼리 상대 크기를 매기고 과거 경험으로 한 반복에 얼마나 할 수 있는지를 정하는 것**이었다.

```
상대 크기 매기기                      속도로 기간 환산
 "로그인 화면"      = 3  (기준)        지난 3스프린트 완료: 21, 18, 24 점
 "비밀번호 재설정"  ≈ 로그인과 비슷 → 3    → 대략 20 점/스프린트
 "소셜 로그인"      ≈ 로그인의 2배 이상 → 8  남은 백로그 120 점 → 약 6 스프린트
```

과거 실적으로 다음 반복을 계획하는 원칙에는 이름도 있다. Fowler 의 [YesterdaysWeather](https://martinfowler.com/bliki/YesterdaysWeather.html)는 "이번 반복에는 지난 반복에 한 만큼 하도록 계획하라" 는 원칙이다. 그는 이 이름을 Kent Beck 과 *Planning Extreme Programming*(Addison-Wesley, 2000)을 쓰면서 붙였다고 밝힌다.

포인트 척도는 작은 범위를 쓴다. Fowler 는 1, 2, 4, 8 이나 1, 2, 3, 5, 8 을 예로 들고, 가장 큰 값을 "너무 크니 쪼개라" 의 의미로 쓰는 경우를 경고한다. '8' 이 사실은 '8 이상' 이라면 예측에 그 숫자를 그대로 넣으면 안 된다. 차라리 "추정 불가, 너무 큼" 이라고 명시하는 편이 낫다.

### 플래닝 포커의 원형 — Grenning 2002

플래닝 포커는 James Grenning 이 2002년에 쓴 3쪽짜리 글 [Planning Poker or How to avoid analysis paralysis while release planning](https://wingman-sw.com/papers/PlanningPoker-v1.1.pdf)에서 시작됐다. 그가 풀려던 문제는 두 가지였다. 추정 회의가 너무 오래 걸리고, 팀 전체가 참여하지 않는다는 것.

원문의 절차는 이렇다.

1. 고객이 스토리를 읽는다. 필요하면 짧게 질의응답한다.
2. 각 프로그래머가 **상의 없이** 카드에 추정을 적는다.
3. 모두 적었으면 **동시에** 뒤집는다.
4. 일치하면 기록하고 다음으로 넘어간다. 다르면 **양 극단의 사람이 먼저** 이유를 말한다.
5. 합의가 안 되면 고민하지 않는다. 스토리를 미루거나, 쪼개거나, 낮은 추정을 택한다.

원래 카드는 **1, 2, 3, 5, 7, 10 (이상적인 프로그래밍 일수)과 무한대**였다. Grenning 은 "추정이 길어질수록 정밀도가 떨어지게" 일부러 틈을 두었고, 2주가 넘는 스토리에는 무한대 카드를 내서 고객이 쪼개게 하라고 적었다. 그의 경험으로는 이 방식으로 스토리당 10~30분 걸리던 추정이 대부분 1분 남짓으로 줄었다.

오늘날 흔히 쓰는 덱은 Mike Cohn 의 Mountain Goat Software 가 [소개하는](https://www.mountaingoatsoftware.com/agile/planning-poker) **0, 1, 2, 3, 5, 8, 13, 20, 40, 100** 이다. 물음표(이해 못 함), 무한대(너무 큼), 커피(쉬자) 카드를 함께 쓰기도 한다.

### 왜 동시 공개인가

Grenning 은 [저자 노트](https://wingman-sw.com/articles/planning-poker)에서 아이디어의 뿌리를 델파이 기법이 아니라, 1980년대 직장에서 배운 TQM 의 "말없이 묶기(silent grouping)" 라고 밝힌다. 각자 먼저 적고 나서 공유하면 가장 지배적이거나 직급 높은 사람의 의견이 다른 사람의 생각을 오염시키지 않는다는 것이다.

Mountain Goat 의 해설도 같은 지점을 강조한다. 높은 추정은 숨은 일(데이터 마이그레이션, 보안 검토, 여러 브라우저 테스트)을 드러내고, 낮은 추정은 더 단순한 설계나 이미 있는 컴포넌트를 드러낸다. 그래서 **평균을 내면 안 된다.** 3 과 13 의 차이는 산수 문제가 아니라 서로 다른 일을 보고 있다는 신호다.

### 스크럼 가이드에는 스토리 포인트가 없다

[스크럼 가이드 2020](https://scrumguides.org/scrum-guide.html)은 백로그 항목에 "크기(size)" 같은 속성을 붙이고, 크기 산정은 **일을 할 개발자들의 책임**이라고만 말한다. 스토리 포인트, 속도, 플래닝 포커라는 말은 나오지 않는다. 진척 예측 방법으로는 번다운·번업·누적 흐름을 예로 들지만, 이것들이 경험주의를 대신하지 못한다고 덧붙인다(SE100 #080 에서 다룬다). 스토리 자체도 XP 에서 온 개념이다(SE100 #014 에서 다룬다). 스크럼 기초는 [애자일과 스크럼]({% post_url 2026-10-10-cs300-182-agile-and-scrum %}) 글을 보라.

## 실무 적용

### 진행 스크립트

```
[준비] 기준 스토리 2~3개를 벽에 붙인다 (예: "로그인 = 3", "CSV 내보내기 = 5")
[1분]  PO 가 스토리와 인수 기준을 읽는다
[2분]  질문. 구현 방법 토론은 하지 않는다
[10초] 각자 카드 선택 → "하나, 둘, 셋" 에 동시 공개
       ├─ 모두 같거나 인접 → 기록, 다음 스토리
       └─ 벌어짐 → 최고·최저가 각 30초씩 설명 → 1회 재투표
[규칙] 두 번째에도 안 모이면: 쪼개기 / 스파이크 / 질문 기록 후 보류
```

### 속도로 범위를 예측할 때의 계산

```python
from statistics import mean
velocity = [21, 18, 24, 15, 22]      # 최근 스프린트 완료 포인트
remaining = 120
lo, hi = min(velocity), max(velocity)
print(f"평균 기준 {remaining / mean(velocity):.1f} 스프린트, "
      f"범위 {remaining / hi:.1f} ~ {remaining / lo:.1f} 스프린트")
```

실행하면 `평균 기준 6.0 스프린트, 범위 5.0 ~ 8.0 스프린트` 가 나온다. 평균 하나로 말하지 말고 범위로 말한다. 범위를 확률로 바꾸는 방법은 SE100 #077 의 몬테카를로 예측에서 다룬다.

## 흔한 오해와 함정

- **"포인트로 팀을 비교한다."** Jeffries 는 같은 스토리를 한 팀이 2, 다른 팀이 6 이라고 해도 흥미로울 게 없다고 쓴다. 팀마다 기술과 환경이 다르기 때문이다. 팀 간 포인트를 정규화하면 비교의 유혹이 커진다. 그는 그 유혹이 너무 강해서 차라리 스토리 포인트를 버리는 쪽을 택하겠다고까지 말한다.
- **"추정과 실적을 맞추는 게 목표다."** Jeffries 는 추정 대비 실적 추적을 "기껏해야 낭비" 라고 본다. 관리의 초점이 가치 전달에서 추정 정확도로 옮겨 가기 때문이다.
- **"속도를 올려라."** 속도를 목표로 삼으면 포인트가 부풀거나, 팀이 테스트와 코드 품질을 깎는다. Jeffries 는 이 압력이 결함과 재작업을 늘리고 결국 더 느려지는 악순환을 부른다고 경고한다.
- **"포인트 = 시간의 변형일 뿐이다."** 결국 시간으로 환산되는 것은 맞다. 다만 환산을 개인이 아니라 **팀의 과거 실적**이 하도록 맡긴다는 점이 다르다.
- **"플래닝 포커는 모든 백로그에 해야 한다."** Grenning 자신이 며칠씩 걸리는 플래닝 포커 회의 이야기를 들으면 질색한다고 쓴다. 먼 미래의 항목은 거칠게 묶어서 추정하고, 가까운 항목에만 포커를 쓴다.
- **대안도 있다.** Fowler 는 포인트 대신 스토리 개수를 세는 방식(StoryCounting)도 똑같이 잘 작동하는 것 같다고 쓴다. Jeffries 는 추정 대신 스토리를 하루 이하로 잘게 쪼개는 쪽을 권한다.

## 확인 문제

1. 초기 XP 팀이 "이상적인 날" 대신 "포인트" 라는 이름을 쓰게 된 계기는?
2. Grenning 의 원래 플래닝 포커 카드 값과, 틈을 둔 이유는?
3. 플래닝 포커에서 추정이 벌어졌을 때 평균을 내면 안 되는 이유는?
4. Fowler 가 척도의 최댓값을 '너무 큼' 표시로 쓸 때 주의하라고 한 점은?
5. 스크럼 가이드 2020 은 크기 산정의 책임을 누구에게 두는가?

### 풀이

1. 이상적인 날에 부하 계수(약 3)를 곱해 실제 기간을 냈더니, 이해관계자가 "하루짜리가 왜 사흘 걸리느냐" 며 혼란스러워했기 때문이다.
2. 1, 2, 3, 5, 7, 10 일과 무한대. 추정이 길어질수록 정밀도가 떨어진다는 점을 반영했고, 2주를 넘는 스토리는 무한대 카드로 쪼개게 하려는 의도다.
3. 차이 자체가 서로 다른 가정(숨은 작업, 더 단순한 설계 등)을 보고 있다는 신호인데, 평균은 그 신호를 숨긴다.
4. '8' 이 실제로는 '8 이상' 을 뜻하므로 완료 시점 예측에 그대로 넣으면 안 된다. 쪼개고 나면 어떤 숫자로든 바뀔 수 있다.
5. 그 일을 할 개발자들.

## 더 읽을거리 (References)

- James Grenning, [Planning Poker or How to avoid analysis paralysis while release planning](https://wingman-sw.com/papers/PlanningPoker-v1.1.pdf), 2002 — [저자 노트](https://wingman-sw.com/articles/planning-poker)
- Ron Jeffries, [Story Points Revisited](https://ronjeffries.com/articles/019-01ff/story-points/Index.html), 2019
- Martin Fowler, [StoryPoint](https://martinfowler.com/bliki/StoryPoint.html), [YesterdaysWeather](https://martinfowler.com/bliki/YesterdaysWeather.html)
- Mountain Goat Software, [Planning Poker](https://www.mountaingoatsoftware.com/agile/planning-poker)
- Ken Schwaber, Jeff Sutherland, [The 2020 Scrum Guide](https://scrumguides.org/scrum-guide.html)
- Kjetil Moløkken-Østvold, Nils Christian Haugen, [Combining Estimates with Planning Poker — An Empirical Study](https://doi.org/10.1109/ASWEC.2007.15), ASWEC 2007
- Kent Beck, Martin Fowler, *Planning Extreme Programming*, Addison-Wesley, 2000 (서지 정보)
- Mike Cohn, *Agile Estimating and Planning*, Prentice Hall, 2005 (서지 정보)
