---
layout: post
title: "[SE100 #066] DevOps 의 원칙 — CALMS 와 세 가지 방법"
date: 2026-10-11 17:05:20 +0900
categories: [software-engineering]
tags: [se100, process, devops, calms, three-ways]
---

소프트웨어 공학 100 주제 시리즈의 66번째 글이다. (카테고리: 프로세스와 방법론)

## 한 줄 요약

DevOps 는 직무 이름도, 도구 묶음도 아니다. **만드는 사람과 운영하는 사람 사이의 벽 때문에 생기는 지연과 실패를 없애려는 원칙의 묶음**이다. CALMS 는 "무엇을 봐야 하는가" 의 체크리스트이고, 세 가지 방법(Three Ways)은 "어떤 순서로 개선하는가" 의 지도다.

## 왜 필요한가

전통적인 조직에서 개발 팀의 목표는 **변경**이고 운영 팀의 목표는 **안정**이다. 둘 다 옳은 목표인데 서로 충돌한다.

- 개발은 기능을 쌓아 분기마다 한 번 큰 릴리스를 넘긴다. 운영은 그 릴리스가 무섭다. 그래서 변경 승인 절차를 늘린다.
- 절차가 늘수록 릴리스는 더 드물어지고 더 커진다. 큰 릴리스는 더 자주 실패한다. 운영은 절차를 더 늘린다.
- 장애가 나면 "누가 배포했나" 를 찾는다. 개발자는 운영 환경을 모르고, 운영자는 코드를 모른다.

이 악순환은 사람이 게을러서가 아니라 **구조**에서 나온다. DevOps 는 그 구조를 바꾸자는 운동으로 시작했다. [devopsdays](https://devopsdays.org/about)에 따르면 첫 devopsdays 는 2009년 벨기에 겐트에서 열렸고 Patrick Debois 가 창립자다.

## 핵심 개념

### CALMS: 다섯 개의 렌즈

John Willis 는 [DevOps Culture (Part 1)](https://itrevolution.com/articles/devops-culture-part-1/)(2012)에서 기원을 직접 밝힌다. 2010년 미국 마운틴뷰에서 열린 첫 미국 devopsdays 이후 Damon Edwards 와 함께 **CAMS** — Culture, Automation, Measurement, Sharing — 라는 약어를 만들었고, 이후 Jez Humble 이 Lean 의 L 을 더해 **CALMS** 가 됐다.

| 렌즈 | 묻는 질문 | 없을 때의 증상 |
|---|---|---|
| Culture (문화) | 실패를 학습 기회로 다루는가, 책임자를 찾는가 | 장애 보고서가 "담당자 주의 요망" 으로 끝남 |
| Automation (자동화) | 반복되는 수작업이 사람 손에 남아 있는가 | 배포 체크리스트 40줄, 배포는 특정인만 가능 |
| Lean (린) | 작은 배치로 흐르는가, 대기가 어디에 쌓이는가 | 분기 릴리스, 승인 대기 2주 |
| Measurement (측정) | 흐름과 안정성을 숫자로 보는가 | "요즘 배포가 좀 불안한 것 같다" 는 감 |
| Sharing (공유) | 지식·도구·책임이 팀 경계를 넘는가 | 운영 지식이 한 사람 머리에만 |

순서에 의미가 있다. Willis 의 글이 "DevOps 문화" 연재의 일부였듯이 **C 가 맨 앞**이다. 자동화 도구만 들여놓고 문화가 그대로면, 수동으로 하던 나쁜 절차를 자동으로 빠르게 할 뿐이다.

### 세 가지 방법 (The Three Ways)

Gene Kim 은 [The Three Ways: The Principles Underpinning DevOps](https://itrevolution.com/articles/the-three-ways-principles-underpinning-devops/)(2012)에서 DevOps 의 행동 패턴이 모두 세 원칙에서 나온다고 정리했다.

```
첫째 방법: 흐름 (왼쪽 → 오른쪽)
  개발 ──▶ 테스트 ──▶ 배포 ──▶ 운영 ──▶ 고객
  "사일로 하나가 아니라 시스템 전체의 성과"

둘째 방법: 피드백 (오른쪽 → 왼쪽)
  개발 ◀── 테스트 ◀── 배포 ◀── 운영 ◀── 고객
  "오른쪽에서 왼쪽으로 가는 피드백 고리를 만들고, 짧게, 증폭한다"

셋째 방법: 지속적 실험과 학습
  ↻ 위험을 감수하는 실험, 실패에서 배우기
  ↻ 반복과 연습이 숙달의 전제임을 이해하기
```

| 방법 | 핵심 | 대표 실천 | 측정 신호 |
|---|---|---|---|
| 첫째: 흐름 | 전체 시스템 최적화, 결함을 다음 단계로 넘기지 않음, 작은 배치 | [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %}), 트렁크 기반 개발, 환경 자동 생성 | 변경 리드 타임, 배포 빈도 |
| 둘째: 피드백 | 문제를 생긴 곳에서 빨리 보이게 | 텔레메트리, 배포 직후 알림, 개발자 온콜 참여 | 실패 감지 시간, 복구 시간 |
| 셋째: 학습 | 실패를 조직의 지식으로 바꿈 | 비난 없는 사후 검토, 게임데이·카오스 실험, 개선 시간 확보 | 반복 장애 비율, 개선 항목 완료율 |

세 방법은 순서이기도 하다. 흐름 없이 피드백을 짧게 할 수 없고(분기 릴리스의 피드백은 분기 단위다), 피드백 없이 학습할 수 없다.

첫째 방법은 SE100 #065 의 린 "전체 최적화" 와 같은 생각이고, 둘째 방법은 토요타의 지도카 — 이상이 생기면 멈추고 고친다 — 와 같은 생각이다. DevOps 의 상당 부분은 린을 IT 전달 흐름에 적용한 것이다.

### 문화는 측정할 수 있다

"문화" 는 막연해 보이지만 측정 도구가 있다. DORA 는 [생성적 조직 문화](https://dora.dev/capabilities/generative-organizational-culture/) 역량에서 Ron Westrum 의 조직 문화 유형론([A typology of organisational cultures](https://doi.org/10.1136/qshc.2003.009522), 2004)을 쓴다.

| | 병리적 (권력 지향) | 관료적 (규칙 지향) | 생성적 (성과 지향) |
|---|---|---|---|
| 협력 | 낮음 | 보통 | 높음 |
| 나쁜 소식 전달자 | 처벌 | 무시 | 훈련 |
| 책임 | 회피 | 좁게 | 공유 |
| 부서 간 연결 | 억제 | 용인 | 장려 |
| 실패 | 희생양 찾기 | 책임 추궁(justice) | 탐구 |
| 새로움 | 짓밟힘 | 문제로 여김 | 실행 |

DORA 는 이를 일곱 점 척도의 설문 문항 여섯 개로 잰다. 예를 들어 "실패 소식을 전하는 사람이 처벌받지 않는다", "실패는 주로 개선의 기회로 다뤄진다" 같은 문장에 얼마나 동의하는지 묻는다. 팀 회고에서 그대로 써 볼 만하다.

## 실무 적용

### 운영 수작업을 줄이는 기준

자동화(A)는 무엇부터 할지가 문제다. Google SRE 책의 [Eliminating Toil](https://sre.google/sre-book/eliminating-toil/) 장은 토일(toil)을 "프로덕션 서비스 운영에 묶인 일 중 수동적이고, 반복적이고, 자동화 가능하고, 전술적이며, 지속적 가치가 없고, 서비스 성장에 선형으로 늘어나는 일" 로 정의한다. 그리고 SRE 조직은 각 SRE 의 시간 중 운영 업무(토일)를 50% 아래로 유지하는 목표를 공표해 두고 있다고 쓴다.

이 정의로 팀의 운영 업무를 분류해 본다.

```yaml
# 지난 4주 운영 업무 기록 (예시)
- task: 인증서 수동 갱신
  manual: true
  repetitive: true
  scales_with_growth: true   # 서비스가 늘면 같이 늘어남
  verdict: toil → 자동화 1순위
- task: 신규 고객사 DB 스키마 수동 생성
  manual: true
  repetitive: true
  scales_with_growth: true
  verdict: toil → 프로비저닝 스크립트화
- task: 장애 원인 분석
  manual: true
  repetitive: false
  verdict: 토일 아님 (엔지니어링) → 사후 검토로 학습
```

### 비난 없는 사후 검토 (셋째 방법)

[Google SRE 책](https://sre.google/sre-book/postmortem-culture/)은 "비난 없이 쓰인 사후 검토는 사고에 관련된 모든 사람이 좋은 의도를 갖고, 가진 정보로 옳은 일을 했다고 가정한다" 고 쓴다. 템플릿의 핵심은 "누가" 가 아니라 "시스템의 어떤 조건이 그 행동을 합리적으로 보이게 했나" 를 묻는 것이다. 팀 회고와의 관계는 SE100 #068 에서 다룬다.

### 도입 순서 예

1. 가치 흐름을 그린다(린). 커밋에서 운영까지 어디서 기다리는가.
2. 가장 긴 대기 하나를 자동화로 없앤다(자동화). 대개 테스트 환경이나 배포 승인이다.
3. 배포 빈도·리드 타임·변경 실패율을 대시보드에 올린다(측정, SE100 #070).
4. 개발자가 자기 서비스의 알림을 받고 온콜에 참여한다(피드백, 공유).
5. 장애마다 비난 없는 사후 검토를 쓰고, 개선 항목을 백로그에 넣어 실제로 끝낸다(문화, 학습).

## 흔한 오해와 함정

- **"DevOps 팀" 을 새로 만든다.** 개발과 운영 사이에 세 번째 사일로를 하나 더 세우는 결과가 되기 쉽다. 플랫폼 팀이라면 내부 고객에게 셀프서비스를 제공하는 역할로 설계해야 한다(팀 구조는 SE100 #096 에서 다룬다).
- **도구 도입 = DevOps.** CALMS 의 첫 글자는 C 다. 파이프라인 도구를 깔아도 배포에 세 단계 결재가 필요하면 흐름은 그대로다.
- **속도와 안정성은 반비례한다.** 작은 배치로 자주 배포하면 각 변경의 위험과 복구 범위가 작아진다. [DORA](https://dora.dev/guides/dora-metrics/)는 자신들의 연구가 "속도와 안정성이 트레이드오프가 아님" 을 거듭 보여 줬고, 대부분의 팀에서 지표들이 상관관계를 보인다고 쓴다(SE100 #070).
- **피드백 없는 자동화.** 배포는 자동인데 배포 후 지표를 아무도 안 본다면 둘째 방법이 빠졌다. 빨리 실패를 내보내는 기계가 될 뿐이다.
- **학습 시간을 따로 두지 않는다.** 사후 검토의 개선 항목이 기능 백로그와 경쟁하면 언제나 진다. 용량의 일부를 개선에 고정한다.

## 확인 문제

1. CAMS 를 처음 만든 사람들과 시점, L 을 더한 사람을 쓰라.
2. 세 가지 방법 각각을 한 문장으로 정의하라.
3. 분기 1회 릴리스 조직이 둘째 방법(피드백)을 강화하기 어려운 이유를 첫째 방법과 연결해 설명하라.
4. Google SRE 정의에 따를 때 "매달 신규 고객이 늘 때마다 수동으로 설정 파일을 만드는 일" 이 토일인 이유는?
5. Westrum 유형론에서 "실패가 탐구로 이어진다" 는 어느 유형의 특징이며, 이것이 셋째 방법과 어떻게 연결되는가?

### 풀이

1. John Willis 와 Damon Edwards 가 2010년 마운틴뷰 devopsdays 이후 CAMS 를 만들었고, Jez Humble 이 Lean 을 더해 CALMS 가 됐다.
2. 첫째: 사일로가 아닌 시스템 전체의 흐름을 최적화한다. 둘째: 오른쪽(운영·고객)에서 왼쪽(개발)으로 가는 피드백을 짧게 하고 증폭한다. 셋째: 실험·실패에서 배우고 반복 연습으로 숙달하는 문화를 만든다.
3. 피드백은 변경이 운영에 닿아야 생긴다. 흐름이 분기 단위면 피드백도 분기 단위로만 오고, 한 번에 많은 변경이 섞여 원인을 가리기도 어렵다.
4. 수동이고, 반복되고, 자동화할 수 있고, 지속적 가치가 없으며, 고객 수(서비스 성장)에 선형으로 늘기 때문이다.
5. 생성적(성과 지향) 문화. 실패를 처벌이 아니라 조사·학습의 출발점으로 다뤄야 셋째 방법의 실험과 학습이 가능하다.

## 더 읽을거리 (References)

- devopsdays, [About](https://devopsdays.org/about)
- John Willis, [DevOps Culture (Part 1)](https://itrevolution.com/articles/devops-culture-part-1/), IT Revolution, 2012
- Gene Kim, [The Three Ways: The Principles Underpinning DevOps](https://itrevolution.com/articles/the-three-ways-principles-underpinning-devops/), IT Revolution, 2012
- DORA, [Generative organizational culture](https://dora.dev/capabilities/generative-organizational-culture/)
- Ron Westrum, [A typology of organisational cultures](https://doi.org/10.1136/qshc.2003.009522), Quality and Safety in Health Care 13(suppl 2), 2004
- Google, Site Reliability Engineering: [Eliminating Toil](https://sre.google/sre-book/eliminating-toil/), [Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- Gene Kim, Jez Humble, Patrick Debois, John Willis, *The DevOps Handbook*, IT Revolution, 2016 (서지 정보)
- CS300: [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %})
