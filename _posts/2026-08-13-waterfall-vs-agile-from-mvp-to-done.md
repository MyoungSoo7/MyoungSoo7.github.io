---
layout: post
title: "말 그리기 5단계와 소프트웨어 방법론 — MVP 부터 완성까지, 폭포수와 애자일을 다시 비교한다"
date: 2026-08-13 18:15:00 +0900
categories: [engineering, process]
tags: [agile, waterfall, mvp, royce, kniberg, methodology, project-management]
---

![말 그리는 법 5단계: 1~4단계는 졸라맨 수준의 말, 5단계는 "작은 디테일 추가"라며 사진 같은 말이 등장한다](/assets/images/how-to-draw-a-horse-waterfall-agile.jpg)

이 그림을 받고 웃다가, 웃을 일이 아니라는 걸 깨달았다. **이건 우리 스프린트 계획표다.**

1~4단계는 원 두 개와 막대기 네 개다. 그리고 5단계 "작은 디테일 추가"에 **작업의 95%가 들어 있다.** 진도는 4/5, 즉 80% 완료라고 보고된다. 실제 완료는 5% 다.

이 글은 이 그림을 축으로 폭포수와 애자일을 MVP 부터 완성까지 비교한다. 결론부터 말하면 — **이 그림은 폭포수가 아니다. 애자일도 아니다. 폭포수를 애자일이라고 부를 때 나오는 제3의 것이다.** 그리고 그 제3의 것에는 이미 공식 문서에 등재된 이름이 있다.

---

## 1. 폭포수는 원래 "이렇게 하지 마라"는 그림이었다

가장 널리 퍼진 오해부터 정리하고 가야 한다.

폭포수 모델의 출처로 항상 인용되는 문헌은 Winston W. Royce 의 1970년 논문 "Managing the Development of Large Software Systems" 다. 이 논문에 요구분석 → 설계 → 구현 → 테스트 → 운영이 한 방향으로 흐르는 그 유명한 그림이 나온다. 그런데 **논문은 그 그림을 제시한 직후에 이렇게 말한다.**

> I believe in this concept, but **the implementation described above is risky and invites failure.**[^royce]

이어지는 문단에서 Royce 는 이유까지 정확히 적는다. 개발 주기의 **맨 끝**에 오는 테스트 단계가, 타이밍·저장공간·입출력 전송량 같은 것들을 _분석이 아니라 경험으로_ 마주하는 최초의 사건이라는 것. 그리고 그것들은 정밀하게 분석 가능한 성질이 아니라는 것. 그래서 여기서 문제가 터지면 국소 수정으로 안 되고 **설계가 근거로 삼았던 요구사항 자체가 무너진다.** 그 결과를 그는 이렇게 표현한다.

> In effect the development process has returned to the origin and one can expect up to a 100-percent overrun in schedule and/or costs.[^royce]

논문의 나머지 전부는 이 위험을 없애기 위해 **추가해야 할 다섯 가지**에 대한 이야기다(그중 하나가 그 유명한 "do it twice" — 시제품을 한 번 버릴 각오로 먼저 만들라는 것이다). 즉 **Royce 는 폭포수를 팔지 않았다. 폭포수의 위험을 경고하고 반복(iteration)을 처방했다.**

우리가 "폭포수"라고 부르며 30년간 실행한 것은, 그 논문의 **첫 번째 그림만 잘라내고 나머지 경고를 버린 판본**이다. 방법론 논쟁의 출발점이 이미 오독이었다.

말 그림으로 옮기면 — 진짜 폭포수는 "5단계까지 다 계획한 뒤 한 번에 그린다"이고, Royce 가 실제로 권한 것은 "**한 마리를 먼저 그려서 버려라. 그 다음에 진짜를 그려라**"였다.

---

## 2. 애자일은 "계획하지 말자"가 아니라 "진도의 단위를 바꾸자"였다

2001년 애자일 선언문은 네 문장이다. 그리고 각 문장의 끝에는 사람들이 자주 잘라먹는 단서가 붙어 있다.

> That is, while there is value in the items on the right, **we value the items on the left more.**[^manifesto]

오른쪽(프로세스·문서·계약·계획)에 **가치가 있다고 명시**한다. 버리라는 말이 아니다. 우선순위를 바꾸라는 말이다. 이 단서를 잘라내면 "문서 쓰지 마라, 계획 세우지 마라"는 괴담이 된다.

이 글의 주제에 가장 직접적인 것은 12개 원칙 중 이 두 개다.

> Deliver working software frequently, from a couple of weeks to a couple of months, with a preference to the shorter timescale.
>
> **Working software is the primary measure of progress.**[^principles]

핵심 단어는 _working_ 이다. 애자일이 실제로 바꾼 것은 개발 순서가 아니라 **진도를 재는 자**다. 폭포수의 진도 단위는 "완료된 단계"고, 애자일의 진도 단위는 "동작하는 소프트웨어"다.

말 그림의 4단계를 다시 보자. 폭포수 자로 재면 4/5 = 80% 다. 애자일 자로 재면 **0%** 다. 그 졸라맨 말로 할 수 있는 일이 없기 때문이다.

---

## 3. 그래서 판별식은 하나뿐이다

Henrik Kniberg 의 유명한 스케이트보드 그림이 정확히 이 지점을 그린 것이다. 그는 2016년에 그 그림의 의도를 직접 해설했다. 위쪽 시나리오(바퀴 → 차체 → 완성차)를 이렇게 평가한다.

> The top scenario (delivering the front tire) sucks because **we keep delivering stuff that the customer can't use at all.**[^kniberg]

아래쪽(스케이트보드 → 킥보드 → 자전거 → 오토바이 → 자동차)의 차이는 딱 하나다.

> as opposed to the front wheel in the first scenario, **the skateboard is actually a usable product that helps the customer get from A to B.** Not great, but a tiny bit better than nothing.[^kniberg]

여기서 **단 하나의 판별식**이 나온다.

> **이번 단계의 산출물을 사용자가 실제로 쓸 수 있는가?**

이걸 말 그림에 적용해 보자.

| 단계        | 산출물 | 사용자가 쓸 수 있나 |
| ----------- | ------ | ------------------- |
| 1. 원 두 개 | 도형   | ✗                   |
| 2. 다리     | 졸라맨 | ✗                   |
| 3. 얼굴     | 졸라맨 | ✗                   |
| 4. 갈기     | 졸라맨 | ✗                   |
| 5. 디테일   | 말     | ✓                   |

**✓ 가 하나다.** 단계가 다섯 개로 쪼개져 있어도 인도(delivery)는 한 번뿐이다. 즉 이건 **스프린트 이름표 다섯 장을 붙인 폭포수**다.

미 국방부 Defense Innovation Board 는 2018년에 이 현상을 판별하는 문서를 냈고, 제목이 대단히 솔직하다 — _"Detecting Agile BS"_. 목적을 이렇게 적는다.

> to detect software projects that are really using agile development versus those that are **simply waterfall or spiral development in agile clothing ("agile-scrum-fall")**.[^dib]

**agile-scrum-fall.** 이 그림의 정식 명칭이다. 그리고 같은 문서가 제시하는 "애자일이 아니라는 신호" 목록은 그대로 자가진단 체크리스트로 쓸 만하다.

> - Nobody on the software development team is talking with and observing the users of the software in action; **we mean the actual users of the actual code.**
> - Continuous feedback from users to the development team is not available. **Talking once at the beginning of a program to verify requirements doesn't count!**
> - **Meeting requirements is treated as more important than getting something useful into the field as quickly as possible.**
> - End users of the software are missing-in-action throughout development.[^dib]

세 번째 항목이 폭포수와 애자일의 차이를 가장 짧게 요약한다. **요구사항 충족이 먼저인가, 현장에 쓸 만한 것을 빨리 내놓는 게 먼저인가.**

---

## 4. MVP 부터 완성까지 — 같은 여정, 다른 지도

이제 정면으로 비교한다.

|                   | 폭포수                             | 애자일                      |
| ----------------- | ---------------------------------- | --------------------------- |
| **요구사항**      | 착수 시점에 확정. 변경은 예외 처리 | 계속 갱신. 변경은 정상 입력 |
| **첫 인도**       | 프로젝트 끝 (1회)                  | 몇 주 안 (반복)             |
| **진도 단위**     | 완료된 단계                        | 동작하는 소프트웨어         |
| **피드백 시점**   | UAT — 되돌리기 가장 비싼 시점      | 매 반복                     |
| **위험 발견**     | 늦게, 한꺼번에                     | 이르게, 조금씩              |
| **"완료"의 정의** | 명세를 다 채움                     | 사용자 문제를 해결함        |
| **MVP 의 위치**   | 없음 (또는 "1차 오픈")             | 여정의 **시작점**           |

가장 중요한 줄은 **위험 발견 시점**이다. 이건 취향 문제가 아니라 구조적 결과다.

직관용 모형으로 적어 본다. 총 작업량 $W$ 를 $n$ 회 반복으로 나눠 인도하고, 각 인도에서 그 시점까지 쌓인 작업만 재작업 위험에 노출된다고 하자. 치명적 오해가 어느 시점에 있든 균일하게 발견된다고 두면, 발견 시점까지 쌓인 평균 작업량은

$$
E[W_{\text{exposed}}] \;=\; \frac{W}{2n}
$$

$n=1$(폭포수)이면 $W/2$, $n=10$(2주 스프린트 10회)이면 $W/20$ 이다. **반복 횟수는 잘못 만든 것을 버릴 때의 손실을 나누는 분모다.** (실제로는 반복마다 고정비가 붙고 오해가 균일 분포도 아니므로, 이 식은 예측용이 아니라 크기 감각용이다.)

말 그림이 위험한 이유가 이 식으로 설명된다. 겉보기엔 $n=5$ 인데, **인도가 한 번뿐이라 실질 $n=1$** 이다. 분모만 문서상으로 커져 있다. 그래서 agile-scrum-fall 은 폭포수보다 나쁠 수 있다 — 폭포수의 위험을 그대로 지면서, 반복하고 있다는 **착각까지 얹기** 때문이다.

---

## 5. 그럼에도 폭포수가 옳은 경우 (전향서가 아니라 조건표)

애자일 진영의 가장 정직한 문장을 인용하겠다. 스케이트보드 그림을 그린 Kniberg 본인의 말이다.

> **If you know what you're doing** – your product has very little complexity and risk, perhaps you've built that type of thing hundreds of times before – **then go ahead and just do big bang.** Build the thing and deliver it when done.[^kniberg]

그가 이어서 붙이는 단서가 조건을 정확히 규정한다 — "_however, most product development efforts I've seen are much too complex and risky for that_". 즉 **big bang 이 틀린 게 아니라, 대부분의 경우 조건이 안 맞는 것**이다.

조건이 맞는 경우는 실제로 존재한다.

- **불확실성이 낮을 때.** 같은 걸 백 번 만들어봤다면 반복해서 배울 것이 없다. 반복은 학습 장치이고, 배울 게 없으면 순수 오버헤드다.
- **인도가 물리적으로 쪼개지지 않을 때.** 하드웨어 동시 출시, 규제 인증, 한 번에 넘어가는 데이터 마이그레이션. 스케이트보드를 중간에 인도할 방법이 아예 없는 종류의 일이 있다.
- **되돌리기가 불가능할 때.** 배포된 자동차를 리콜하는 비용과 웹 서비스를 롤백하는 비용은 다르다. Royce 의 논문 자체가 **우주선 미션 소프트웨어** 이야기였다는 걸 기억할 필요가 있다. 궤도에 올라간 다음엔 스프린트가 없다.
- **계약 구조가 고정 범위·고정 가격일 때.** 이건 기술이 아니라 조달의 문제이고, 방법론으로 이길 수 없다.

거꾸로 **애자일이 반드시 이기는 조건**도 하나로 요약된다. **무엇을 만들어야 하는지를 만들기 전에 알 수 없을 때.** 이 조건이면 폭포수는 정확한 계획으로 잘못된 것을 만든다.

---

## 6. 숫자 이야기 — 이 논쟁에서 가장 많이 인용되는 통계를 쓰지 말아야 하는 이유

방법론 글에서 거의 반드시 등장하는 숫자가 있다. Standish Group 의 CHAOS 리포트, 특히 1994년판의 "평균 189% 비용 초과". 이 글에서는 **쓰지 않는다.** 이유를 밝히는 게 이 절의 목적이다.

Jørgensen 과 Moløkken-Østvold 의 동료심사 논문(_Information & Software Technology_, 2006)이 그 숫자를 검증했다. 결과는 이렇다.

- 같은 시기·같은 지역의 다른 비용추정 조사들은 **평균 초과가 30% 내외**로, 189% 와 자릿수가 다르다. 그 조사들은 연구방법이 학술 심사를 거친 것들이다.
- 연구진이 Standish 에 표본 선정 방법과 'cost overrun' 의 정의를 물었을 때, 돌아온 답은 **그런 정보를 주는 건 사업을 공짜로 넘기는 것과 같다**는 것이었고, 측정 정의에 대해서는 답이 없었다.
- CHAOS 자신의 초과 구간별 분포로 평균을 재계산하면 **89% 에 가깝게 나온다.** 즉 189% 는 자기 결과에 대한 자기 오해일 가능성이 있다.
- 논문의 결론: 표본이 '실패 프로젝트'로 강하게 편향됐을 수 있으며, **그 숫자를 기준점으로 계속 쓰는 것은 잘못된 의사결정을 부르고 진보를 방해한다.**[^chaos]

논문이 남긴 교훈 첫 줄이 이 글 전체에 해당한다.

> **Lesson 1: When something does not correspond with own experience and other studies, doubt it.**[^chaos]

방법론 논쟁이 오래 진창인 이유 중 하나가 이것이다. **양쪽 다 검증되지 않은 숫자로 싸운다.** "폭포수 프로젝트의 X% 가 실패한다" 류의 문장을 만나면 출처를 끝까지 따라가 보길 권한다. 대개 벤더 리포트에서 멈춘다.

그래서 이 글은 숫자 대신 **구조**로 논증했다. 인도 횟수 $n$ 이 분모라는 것, 판별식이 "사용자가 쓸 수 있는가" 하나라는 것 — 이건 통계가 아니라 정의에서 따라 나온다.

---

## 7. 내 프로젝트에서 실제로 일어난 일

방법론 글이 공허해지는 걸 막으려면 자기 사례를 대야 한다. 오늘 [바로 앞 글]({% post_url 2026-08-13-kafka-enforcement-boundary-settlement %})에서 실측한 것 중 이 주제에 정확히 걸리는 게 둘 있다.

**하나. MVP 로 정한 값이 프로덕션이 됐다.** 내 정산 시스템의 Kafka 토픽 선언 코드에는 이런 주석이 달려 있다.

```java
// 복제본 1 — 개발/데모용. 프로덕션은 최소 3 권장.
.replicas(1)
```

주석은 틀리지 않았다. 문제는 이 코드가 도는 네임스페이스 이름이 `settlement-prod` 라는 것이다. **MVP 는 나쁘지 않다. MVP 를 끝이라고 부르는 순간이 나쁜 게 아니라, 아무도 그렇게 부르지 않았는데 조용히 그렇게 되어버리는 게 나쁘다.** 5단계 "디테일 추가"가 영원히 오지 않는 방식은 취소가 아니라 망각이다.

**둘. 80% 완료의 실체.** 컨슈머 코드가 있고, 계약 테스트가 있고, 린트도 통과했다. 4단계까지 완벽했다. 그런데 배포 환경변수 한 줄이 빠져서 **브로커에는 그 컨슈머 그룹이 아예 없었다.** 코드 관점 진도는 100%, 사용자 관점 진도는 0%다. 말 그림의 4단계가 실제로 어떻게 생겼는지를 본 셈이다.

교훈은 방법론 이름표에 있지 않았다. **"동작하는 소프트웨어"의 '동작'을 어디서 확인하느냐**에 있었다. 내 저장소 안에서 확인하면 4단계가 완성으로 보이고, 사용자가 서 있는 자리에서 확인해야 5단계가 남아 있는 게 보인다. 애자일 원칙의 _working_ 은 형용사가 아니라 **측정 장소에 대한 지시**다.

---

## 8. 실무 결론 — 다섯 줄

1. **"우리 애자일 해요"를 자가진단하라.** DIB 체크리스트가 무료다. 실제 코드의 실제 사용자와 이야기하고 있는가, 초기에 한 번 요구사항 확인한 걸 피드백이라 부르고 있지 않은가.
2. **스케이트보드를 먼저 정의하라.** 착수 회의의 첫 질문은 "언제 끝나나"가 아니라 "**사용자 손에 쥐여줄 수 있는 가장 작은 것이 무엇인가**"여야 한다.
3. **진도를 단계로 재지 말고 인도로 재라.** 5단계 중 4단계 완료는 진도가 아니다. 인도 횟수가 실제로 1회라면 그건 폭포수다 — 그렇게 부르고 그에 맞는 위험 관리를 하는 편이 훨씬 낫다.
4. **폭포수를 부끄러워하지 마라. 조건을 확인하라.** 불확실성이 낮고, 인도가 쪼개지지 않고, 되돌리기가 불가능하다면 big bang 이 정답이다. 문제는 방법이 아니라 조건을 확인하지 않는 것이다.
5. **MVP 에 만료일을 붙여라.** "개발/데모용"이라고 적을 거면 언제 무엇으로 대체할지도 같이 적어야 한다. 안 적으면 그 주석이 3년 뒤 프로덕션 코드 리뷰에서 발견된다. 내 경우엔 오늘이었다.

---

## 9. 한 줄

**말을 다섯 단계로 나눠 그린다고 애자일이 되지 않는다. 3단계에서 누가 그 말을 탈 수 있어야 애자일이다.**

Royce 는 폭포수를 경고하려고 그 그림을 그렸고, 애자일 선언문은 계획을 버리라고 한 적이 없다. 30년 논쟁의 양쪽 원전이 모두 우리가 아는 것보다 온건했다. **극단은 원전이 아니라 인용에서 태어났다.**

---

## References

**1차 출처**

- Winston W. Royce, "Managing the Development of Large Software Systems", _Proceedings of IEEE WESCON_, August 1970. [PDF](https://cpske.github.io/ISP/resources/Royce1970-Managing-the-Development-of-Large-Software-Systems.pdf) — 폭포수 그림의 원전이자, 그 그림을 "risky and invites failure" 라고 평가한 문헌.
- [Manifesto for Agile Software Development](https://agilemanifesto.org/) (2001) — 네 가지 가치와 "while there is value in the items on the right" 단서.
- [Principles behind the Agile Manifesto](https://agilemanifesto.org/principles.html) — "Working software is the primary measure of progress" 를 포함한 12원칙.
- Defense Innovation Board, ["DIB Guide: Detecting Agile BS"](https://media.defense.gov/2018/Oct/09/2002049591/-1/-1/0/DIB_DETECTING_AGILE_BS_2018.10.05.PDF), Version 0.4, 2018-10-03 — "agile-scrum-fall" 용어와 판별 체크리스트. 미 국방부 발간 공식 문서.
- Defense Innovation Board, ["Software Is Never Done: Refactoring the Acquisition Code for Competitive Advantage" (SWAP Study)](https://media.defense.gov/2019/May/01/2002126690/-1/-1/0/SWAP%20EXECUTIVE%20SUMMARY.PDF), 2019 — "Speed and cycle time are the most important metrics for managing software".

**동료심사 논문**

- Magne Jørgensen, Kjetil Moløkken-Østvold, ["How large are software cost overruns? A review of the 1994 CHAOS report"](https://www.sciencedirect.com/science/article/abs/pii/S0950584905001023), _Information and Software Technology_ 48(4):297–301, 2006. ([전문 PDF](https://web-backend.simula.no/sites/default/files/publications/Jorgensen.2006.4.pdf)) — 업계에서 가장 많이 인용되는 189% 수치의 타당성 검증.

**실무자 1차 기록 (저자 본인의 해설)**

- Henrik Kniberg, ["Making sense of MVP (Minimum Viable Product) – and why I prefer Earliest Testable/Usable/Lovable"](https://blog.crisp.se/2016/01/25/henrikkniberg/making-sense-of-mvp), Crisp's Blog, 2016-01-25 — 스케이트보드 그림을 그린 본인이 직접 쓴 의도 해설. big bang 이 정당한 조건까지 명시한 부분을 함께 인용했다.

**출처에 대한 주석 (읽는 분을 위해)**

- 이 글은 **벤더 리포트·마케팅 자료·출처 불명의 통계를 인용하지 않았다.** 특히 CHAOS 리포트 계열 수치는 6절에서 밝힌 이유로 **의도적으로 배제**했다.
- 4절의 $E[W_{\text{exposed}}] = W/2n$ 은 **인용이 아니라 필자가 세운 직관용 모형**이다. 실증 데이터가 아니며 예측에 쓰면 안 된다.
- 7절의 사례는 필자 개인 프로젝트에서 **2026-08-13 직접 실측**한 것이다. 상세 근거와 측정 명령은 [앞 글]({% post_url 2026-08-13-kafka-enforcement-boundary-settlement %})에 있다.
- 상단 이미지는 인터넷에 널리 유통되는 밈으로, 이미지 내 서명은 "VAN OKTOP" 이다. **1차 저작자를 확인하지 못했으므로 원작자 귀속을 단정하지 않는다.**

[^royce]: Winston W. Royce, "Managing the Development of Large Software Systems", Proceedings of IEEE WESCON, 1970, pp. 1–9.

[^manifesto]: "Manifesto for Agile Software Development", 2001, <https://agilemanifesto.org/>

[^principles]: "Principles behind the Agile Manifesto", <https://agilemanifesto.org/principles.html>

[^kniberg]: Henrik Kniberg, "Making sense of MVP", Crisp's Blog, 2016-01-25, <https://blog.crisp.se/2016/01/25/henrikkniberg/making-sense-of-mvp>

[^dib]: Defense Innovation Board, "DIB Guide: Detecting Agile BS", v0.4, 2018-10-03, <https://media.defense.gov/2018/Oct/09/2002049591/-1/-1/0/DIB_DETECTING_AGILE_BS_2018.10.05.PDF>

[^chaos]: Magne Jørgensen, Kjetil Moløkken-Østvold, "How large are software cost overruns? A review of the 1994 CHAOS report", Information and Software Technology 48(4), 2006.
