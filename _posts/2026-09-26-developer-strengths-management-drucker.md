---
layout: post
title: "개발자의 강점관리 — 약점을 메울 것인가, 강점에 걸 것인가?"
date: 2026-09-26 13:09:04 +0900
categories: [Career, Engineering Culture]
tags: [Strengths, Peter Drucker, Career, Engineering Management, Positive Psychology, Developer]
---

개발자의 성장 계획은 대개 **약점 목록**으로 시작한다. "쿠버네티스를 모른다", "프론트엔드가 약하다", "발표를 못 한다". 평가 면담도, 스터디 계획도 빈칸을 채우는 방향으로 짜인다.

이 글의 주장은 이렇다. **성과는 강점에서 나오고, 약점은 "무능" 에서 "평균" 까지만 끌어올리면 된다. 다만 강점만 파는 전략에는 과사용이라는 함정이 있다.** 피터 드러커의 원전, 동료심사 논문, 그리고 드러커를 현장 언어로 옮긴 국내 인사 전문가의 책으로 이 주장을 따라가 본다.

| 관점 | 핵심 주장 | 근거 |
|---|---|---|
| 드러커 | 사람은 강점으로만 성과를 낸다 | *Managing Oneself*, *The Effective Executive* |
| 현장 | 드러커의 "강점" 을 커리어 생존 전략으로 | 이준희(면접왕 이형), 《대체되지 않는 사람》 |
| 실증 | 강점을 "쓰는" 환경이 성과와 연결된다 | Seligman 2005, van Woerkom & Meyers 2015 |
| 반론 | 강점은 과사용되면 약점이 된다 | Kaiser & Overfield 2011, Rust et al. 2009 |

## 1. 드러커 — "사람은 강점으로만 성과를 낸다"

드러커는 1999년 글 *Managing Oneself* 에서 지식노동자에게 가장 먼저 자기 강점을 알라고 요구한다.[^mo]

> *"Most people think they know what they are good at. They are usually wrong. ... And yet, a person can perform only from strength. One cannot build performance on weaknesses, let alone on something one cannot do at all."*

그리고 투자 대비 효율을 이렇게 계산한다.

> *"It takes far more energy and work to improve from incompetence to mediocrity than it takes to improve from first-rate performance to excellence."*

이 두 문장이 강점관리의 뼈대다. 드러커는 1967년 *The Effective Executive* 에서도 한 장 전체를 **"Making Strength Productive"** 에 할애했다.[^ee] 이 책의 한국어판 제목이 《자기경영노트》다.

### 강점을 "아는" 방법: 피드백 분석

드러커가 제시하는 유일한 방법은 **피드백 분석**이다.[^mo]

> *"Whenever you make a key decision or take a key action, write down what you expect will happen. Nine or 12 months later, compare the actual results with your expectations."*

자기 평가도, 성격 검사도 아닌 **예측과 결과의 비교**다. 개발자에게는 익숙한 구조다. 가설을 적고, 배포하고, 지표로 확인하는 것과 같다.

### 드러커가 개발자에게 직접 하는 경고

같은 글에서 드러커는 강점을 키우려면 **지적 오만**을 버리라고 하며, 굳이 엔지니어를 예로 든다.[^mo]

> *"First-rate engineers, for instance, tend to take pride in not knowing anything about people. Human beings, they believe, are much too disorderly for the good engineering mind."*

드러커는 이런 무지를 자랑하는 태도가 *"self-defeating"* 이라고 못박는다. 강점에 집중하라는 말이 "내 분야 밖은 몰라도 된다" 는 허가가 아니라는 뜻이다. 강점을 **발휘하는 데 필요한 주변 지식**은 채워야 한다. 드러커는 여기에 나쁜 습관 교정과 **매너**까지 포함시킨다. 매너를 *"the lubricating oil of an organization"* 이라고 부르면서.

## 2. 현장의 번역 — 이랜드 인사총괄 출신이 드러커를 다시 꺼낸 이유

유튜브 채널 '면접왕 이형' 을 운영하는 이준희는 이랜드그룹에서 최연소 인재개발팀장, 법인 인사책임자, 그룹 인사총괄책임자를 지낸 인사 실무자다.[^lee-author] 그의 책 《대체되지 않는 사람》(2025)은 AI 시대에 대체되지 않을 인재의 관점을 드러커의 《자기경영노트》, 데일 카네기의 《인간관계론》, 이나모리 가즈오의 《왜 일하는가》를 바탕으로 정리했다고 소개된다. 1장이 드러커 편이고, 그 안에 **목표달성능력, 시간관리, 공헌, 강점, 우선순위** 가 들어 있다.[^lee-book]

(이 글은 해당 책의 공개된 소개와 목차만 참고했다. 본문 내용은 인용하지 않는다.)

흥미로운 지점은 **채용·면접을 업으로 하는 사람**이 AI 시대의 생존 전략으로 반세기 전의 드러커를 꺼냈다는 사실이다. 코드를 쓰는 능력 자체가 빠르게 범용화되는 지금, "무엇을 잘하는 사람인가" 라는 질문은 개발자에게 오히려 더 날카로워졌다.

## 3. 연구가 말하는 것 — "아는 것" 과 "쓰는 것" 은 다르다

### Seligman et al. (2005): 강점은 써야 효과가 있다

긍정심리학의 대표적 무작위 대조 연구에서 Seligman 등은 여러 개입을 비교했다.[^seligman] 그중 두 가지가 강점 관련이었다.

- **자기 대표 강점 파악 후 "더 자주" 쓰기**
- **자기 대표 강점을 "새로운 방식으로" 쓰기**

결과는 선명했다.

> *"Two of the exercises—using signature strengths in a new way and three good things—increased happiness and decreased depressive symptoms for six months."*

반면 나머지 개입과 위약 대조군은 *"positive but transient effects"* 에 그쳤다. 강점을 **알아내는 것만으로는** 오래가지 않았고, **새로운 방식으로 쓰는 것**이 차이를 만들었다. 강점 진단 결과를 받아 두고 끝내는 조직에게 불편한 결과다.

### van Woerkom & Meyers (2015): 강점을 쓰게 하는 "분위기" 와 성과

네덜란드·벨기에 8개 조직, 39개 부서의 442명을 조사한 이 연구는, 구성원이 **자기 강점을 파악·개발·활용할 기회가 있다고 느끼는 정도**(강점 기반 심리적 풍토)가 역할 내 성과와 역할 외 성과 모두와 양의 관계를 보였고, 이 관계가 **긍정 정서**를 통해 매개된다고 보고했다.[^vw]

### Meyers & van Woerkom (2017): 효과는 있지만 과장하면 안 된다

116명을 대상으로 한 현장 실험에서 강점 개입은 긍정 정서를 단기적으로, 심리적 자본을 단기·장기적으로 높였다. 그러나 **삶의 만족, 업무 몰입, 번아웃에 대한 직접 효과는 찾지 못했고** 긍정 정서를 통한 간접 효과만 확인했다.[^mv] 강점 워크숍 한 번이 번아웃을 해결해 주지는 않는다는 뜻이다.

## 4. 반론 — 강점만 파면 생기는 일

### Kaiser & Overfield (2011): 강점의 과사용

리더십 연구자 Kaiser 와 Overfield 는 강점 기반 개발론에 정면으로 문제를 제기했다.[^kaiser] 강점을 최대화하라는 조언이 역설적으로 **강점을 과사용해 약점으로 바꾸고**, 성과를 떨어뜨리는 결점을 방치하게 만들 수 있다는 것이다. 이들은 관리자들이 **자기 강점과 관련된 행동을 과하게 하는 경향**을 강하게, 그 반대편의 보완 행동을 **덜 하는 경향**을 더 약하게 확인했다.

개발자 버전으로 옮기면 익숙한 장면들이다.

| 강점 | 과사용하면 |
|---|---|
| 추상화 설계 능력 | 쓰지 않을 확장점으로 가득한 과설계 |
| 성능 감각 | 병목이 아닌 곳의 마이크로 최적화 |
| 꼼꼼한 리뷰 | 스타일 지적으로 멈춰 선 PR |
| 빠른 구현 | 테스트·문서 없는 속도 |
| 기술 탐구 | 팀이 유지할 수 없는 신기술 도입 |

### Rust et al. (2009): 약점을 같이 다뤄도 손해가 아니다

대학생 76명을 무작위로 "강점 두 개" 또는 "강점 하나 + 상대적 약점 하나" 를 개발하는 그룹으로 나눈 예비 연구에서, 두 그룹 모두 무처치군보다 삶의 만족이 올랐고 **두 그룹 간 차이는 유의하지 않았다.**[^rust] 표본이 작은 예비 연구지만, "약점을 보면 동기가 꺾인다" 는 통념에 대한 반례로는 충분하다.

## 5. 개발자를 위한 강점관리 — 실전 설계

이상을 종합하면 전략은 **"강점에 걸되, 약점에 바닥을 깐다"** 로 정리된다.

### 5.1 피드백 분석을 엔지니어링 습관으로

- 중요한 기술 결정(ADR)마다 **"예상 결과" 칸**을 둔다. 9~12개월 뒤 실제와 비교한다.
- 회고에서 "무엇이 잘못됐나" 뿐 아니라 **"누가 어떤 종류의 문제를 예상보다 잘 풀었나"** 를 기록한다.
- 이 기록이 쌓이면 성격 검사보다 정확한 강점 지도가 된다. 드러커가 말한 방법 그대로다.

### 5.2 약점은 "바닥" 까지만

- 보안, 테스트, 코드 리뷰 응답 같은 **팀의 최소 기준**은 강점과 무관하게 모두가 넘는다.
- 그 위로는 약점 보완보다 **강점 확장**에 시간을 쓴다. 드러커의 "무능→평균은 비싸다" 계산을 따른다.
- 드러커가 경고한 **지적 오만**은 예외다. 비용, 제품, 사용자 이해처럼 강점을 성과로 바꾸는 데 필요한 주변 지식은 채운다.

### 5.3 "새로운 방식으로 쓰기" 를 업무에 넣는다

Seligman 연구의 핵심은 **새로운 방식**이었다. 디버깅에 강한 사람이 같은 종류의 장애만 계속 맡으면 그건 강점 활용이 아니라 소모다. 같은 강점을 온보딩 문서, 장애 대응 런북, 관측성 설계처럼 **다른 맥락**에 써 보게 한다.

### 5.4 과사용 점검표를 둔다

강점마다 "과하면 어떻게 되는가" 를 팀이 함께 적어 둔다(위 표처럼). 리뷰나 1:1 에서 **"이번엔 강점이 과했나?"** 를 묻는 게 약점 지적보다 방어적 반응이 적다.

### 5.5 팀장이라면 — 배정이 곧 강점관리다

van Woerkom & Meyers 가 측정한 것은 개인의 강점 목록이 아니라 **강점을 쓸 기회가 있다는 인식**이었다. 강점 진단보다 **업무 배정**이 더 강력한 개입이다. 누가 무엇을 잘하는지 아는 팀장이 그걸 배정에 반영하지 않으면, 진단은 비용일 뿐이다.

## 맺으며 — 강점관리의 비용

강점관리는 공짜 점심이 아니다. 강점을 쓰게 하려면 업무를 재배치해야 하고, 누군가는 원래 하던 일을 놓아야 한다. 약점을 방치한 대가는 과사용과 사각지대로 돌아온다. 그리고 연구가 보여주듯 효과는 **진단이 아니라 사용**에서, **단기 이벤트가 아니라 풍토**에서 나온다.

드러커가 반세기 전에 말한 것, 그리고 현장의 인사 전문가가 AI 시대에 다시 꺼낸 것은 결국 같은 질문이다. **"나는 무엇으로 기여하는가?"** AI 가 평균적인 코드를 무한히 쓰는 시대에, 평균을 채우는 약점 보완보다 이 질문에 답하는 강점이 개발자의 대체 불가능성을 만든다. 단, 그 강점이 **과해지지 않도록** 지켜보는 눈과 함께.

---

## References

[^mo]: Peter F. Drucker, *Managing Oneself*, Harvard Business Review (1999; HBR Classics reprint, January 2005). <https://hbr.org/2005/01/managing-oneself>
[^ee]: Peter F. Drucker, *The Effective Executive*, Chapter 4 "Making Strength Productive". <https://www.taylorfrancis.com/chapters/mono/10.4324/9780080549354-4/making-strength-productive-peter-drucker>
[^lee-author]: 예스24, 저자 소개 — 이준희(면접왕 이형). <https://www.yes24.com/product/goods/150820205>
[^lee-book]: 이준희(면접왕 이형), 《대체되지 않는 사람》, 얼라이브북스, 2025 — 책 소개 및 목차. <https://www.yes24.com/product/goods/146518146>
[^seligman]: Martin E. P. Seligman, Tracy A. Steen, Nansook Park, Christopher Peterson, *Positive Psychology Progress: Empirical Validation of Interventions*, American Psychologist 60(5), 410–421 (2005). <https://doi.org/10.1037/0003-066X.60.5.410>
[^vw]: Marianne van Woerkom, Maria Christina Meyers, *My Strengths Count! Effects of a Strengths-Based Psychological Climate on Positive Affect and Job Performance*, Human Resource Management 54(1), 81–103 (2015). <https://doi.org/10.1002/hrm.21623>
[^mv]: Maria Christina Meyers, Marianne van Woerkom, *Effects of a Strengths Intervention on General and Work-Related Well-Being: The Mediating Role of Positive Affect*, Journal of Happiness Studies 18(3), 671–689 (2017). <https://doi.org/10.1007/s10902-016-9745-x>
[^kaiser]: Robert B. Kaiser, Darren V. Overfield, *Strengths, strengths overused, and lopsided leadership*, Consulting Psychology Journal: Practice and Research 63(2), 89–109 (2011). <https://doi.org/10.1037/a0024470>
[^rust]: Teri Rust, Rhett Diessner, Lindsay Reade, *Strengths Only or Strengths and Relative Weaknesses? A Preliminary Study*, The Journal of Psychology 143(5), 465–476 (2009). <https://doi.org/10.3200/JRL.143.5.465-476>
