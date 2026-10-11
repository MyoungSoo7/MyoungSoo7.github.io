---
layout: post
title: "[SE100 #097] 심리적 안전감과 팀 효과성"
date: 2026-10-11 17:10:47 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, psychological-safety, team-effectiveness, blameless-postmortem, westrum]
---

소프트웨어 공학 100 주제 시리즈의 97번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

심리적 안전감은 "이 팀에서는 대인 관계상의 위험을 감수해도 안전하다" 는 팀원들의 공유된 믿음이다. 친절함이나 낮은 기준이 아니라, **실수·질문·반대가 정보로 흐르게 만드는 조건** 이다. 소프트웨어처럼 오류가 늘 생기는 일에서 그 정보 흐름이 곧 학습 속도다.

## 왜 필요한가

장애 대응 회의에서 이런 일이 생긴다.

- 신입이 설정 변경 직후 오류율이 올라간 걸 봤지만, 확신이 없어서 말하지 않는다. 30분 뒤 선임이 같은 결론에 도달한다.
- 코드 리뷰에서 "이 설계 이상한데요" 라고 말하는 사람이 없다. 작성자가 팀장이기 때문이다.
- 포스트모템이 "누가 실수했나" 로 끝난다. 다음 분기부터 장애 보고가 줄어든다. 장애가 준 게 아니라 보고가 준 것이다.

이 장면들의 공통점은 **팀 안에 있던 정보가 의사결정까지 오지 못한** 것이다. 기술이 아무리 좋아도, 문제를 본 사람이 말하지 않으면 시스템은 배우지 못한다.

## 핵심 개념

### Edmondson 의 정의와 연구

Amy Edmondson 은 [Psychological Safety and Learning Behavior in Work Teams](http://nrs.harvard.edu/urn-3:HUL.InstRepos:37968728) (*Administrative Science Quarterly* 44(2), 1999)에서 팀 심리적 안전감을 이렇게 정의했다.

> 팀 심리적 안전감 — 팀이 대인 관계상의 위험 감수에 안전하다는, 팀원들이 공유하는 믿음.

이 논문은 한 제조 기업의 51개 작업 팀을 조사해, 심리적 안전감은 **학습 행동** 과 관련이 있지만 팀 효능감(team efficacy)은 심리적 안전감을 통제하면 관련이 없다는 결과를 보고했다. 또 학습 행동이 심리적 안전감과 팀 성과 사이를 **매개** 했다. 즉 경로는 다음과 같다.

```
 심리적 안전감 ──► 학습 행동 ──► 팀 성과
                 (질문, 피드백 요청,
                  오류 보고, 실험,
                  외부 정보 탐색)
```

안전감이 성과를 직접 만드는 것이 아니라, **배우는 행동을 가능하게** 하고 그 행동이 성과를 만든다. 이 구분이 실무에서 중요하다. 안전감만 있고 학습 행동이 없는 팀은 그냥 편한 팀이다.

### 무엇이 아닌가

흔히 혼동되는 개념과 구분하면 다음과 같다(필자 정리).

| 심리적 안전감은 | 아니다 |
|---|---|
| 반대 의견을 말해도 처벌받지 않는다는 믿음 | 늘 동의하고 갈등이 없는 상태 |
| 높은 기준과 함께 있을 때 학습이 일어남 | 기준을 낮추는 것 |
| 팀 수준의 공유된 믿음 | 개인의 성격(외향성, 자신감) |
| 실수를 정보로 다루는 것 | 실수에 결과가 없는 것 |

### Google 의 Project Aristotle

Google 의 [Understand team effectiveness](https://rework.withgoogle.com/intl/en/guides/understand-team-effectiveness) 가이드는 180개 팀(엔지니어링 프로젝트 팀 115개, 영업 팀 65개)을 연구한 결과를 공개했다. 결론은 **누가 팀에 있는가보다 팀이 어떻게 함께 일하는가** 가 중요하다는 것이었고, 효과적인 팀의 다섯 동인을 중요도 순으로 들었다.

| 순위 | 동인 | 요지 |
|---|---|---|
| 1 | 심리적 안전감 | 무지·무능·부정적·방해꾼으로 보일 위험을 감수해도 안전하다고 느낌 |
| 2 | 신뢰성(dependability) | 팀원이 품질 높은 일을 제때 해낸다 |
| 3 | 구조와 명확성 | 역할·목표·계획이 분명하다 |
| 4 | 의미 | 일 자체나 그 결과에서 목적을 찾는다 |
| 5 | 영향 | 내 일이 차이를 만든다고 느낀다 |

같은 가이드는 Google 안에서 팀 효과성과 유의하게 연결되지 **않은** 변수로 같은 사무실 근무, 합의 기반 의사결정, 팀원의 외향성, 개인 성과, 업무량, 연차, 팀 규모, 재직 기간을 들고, 이는 Google 의 측정에서 그랬다는 단서를 단다. 기업 내부 연구이고 동료심사 논문이 아니므로 일반화에는 신중해야 한다.

### 소프트웨어 팀에서의 연구

Per Lenberg 와 Robert Feldt 는 [Psychological Safety and Norm Clarity in Software Engineering Teams](https://arxiv.org/abs/1802.01378) (CHASE 2018)에서 5개 조직 38개 개발 팀의 실무자 217명을 설문했다. 심리적 안전감과 **팀 규범의 명확성** 이 모두 자기 평가 팀 성과와 직무 만족을 예측했고, 규범 명확성이 더 강한 예측 변수였다. 안전감만으로는 부족하고 "우리 팀은 어떻게 일하는가" 가 분명해야 한다는 것이다. Google 의 다섯 동인 중 "구조와 명확성" 과 같은 방향이다.

### 조직 문화와 정보 흐름: Westrum

사회학자 Ron Westrum 은 "A Typology of Organisational Cultures" (*Quality and Safety in Health Care* 13 suppl 2, 2004)에서 조직을 정보 처리 방식으로 분류했다. [DORA 의 생성적 문화 문서](https://dora.dev/capabilities/generative-organizational-culture/)가 이 표를 인용한다.

| 병리적(pathological) | 관료적(bureaucratic) | 생성적(generative) |
|---|---|---|
| 권력 지향 | 규칙 지향 | 성과 지향 |
| 낮은 협력 | 보통 협력 | 높은 협력 |
| 전달자를 처벌 | 전달자를 무시 | 전달자를 훈련 |
| 책임 회피 | 좁은 책임 | 위험을 공유 |
| 연결을 막음 | 연결을 용인 | 연결을 장려 |
| 실패 → 희생양 | 실패 → 처벌(정의) | 실패 → 탐구 |
| 새로움을 짓밟음 | 새로움 → 문제 | 새로움을 실행 |

DORA 는 높은 신뢰의 생성적 문화가 소프트웨어 전달 성과와 조직 성과를 예측한다고 보고한다. "전달자를 처벌" 하는 조직에서는 나쁜 소식이 위로 올라가지 않는다. 심리적 안전감은 팀 수준, Westrum 유형은 조직 수준의 같은 현상이다.

## 실무 적용

### 비난 없는 포스트모템

Google 의 [SRE 책 포스트모템 장](https://sre.google/sre-book/postmortem-culture/)은 비난 없는 포스트모템을 "개인이나 팀을 나쁘거나 부적절한 행동으로 지목하지 않고 사건의 기여 원인을 찾는 것" 으로 정의하고, 관련된 모든 사람이 **가진 정보로 선의에 따라 옳은 일을 했다** 고 가정하라고 한다. 사람을 고칠 수는 없지만 시스템과 프로세스는 고칠 수 있다는 것이다. 장애 대응 전체는 [사고 대응과 포스트모템]({% post_url 2026-10-10-cs300-236-incident-response-and-postmortem %}) 글에서 다뤘다.

```markdown
## 타임라인 작성 규칙
- "김OO 가 잘못된 설정을 배포함" (X)
- "14:02 설정 변경 배포. 배포 파이프라인에 해당 키의 스키마 검증 없음" (O)

## 질문 바꾸기
- "왜 확인 안 했나?" → "그 시점에 무엇을 보고 있었고, 무엇이 보이지 않았나?"
- "누가 승인했나?" → "승인 절차가 이 위험을 잡도록 설계되어 있었나?"
```

### 리더가 하는 구체적 행동

- **불확실성을 먼저 인정한다.** "이 설계 나도 확신이 없다. 구멍을 찾아 달라." 리더의 실수 인정은 팀원의 비용을 낮춘다.
- **질문에 감사로 답한다.** 바보 같은 질문에 대한 첫 반응이 다음 질문의 수를 결정한다.
- **회의에서 가장 늦게 말한다.** 직급이 높은 사람이 먼저 결론을 말하면 반대 의견이 사라진다.
- **나쁜 소식을 가져온 사람을 보호한다.** Westrum 표의 "전달자를 훈련" 이 이것이다.
- **규범을 명시한다.** 리뷰 응답 기대 시간, 반대 의견 표명 방법, 결정 방식. Lenberg 와 Feldt 의 결과처럼 명확한 규범이 안전감을 받친다.

### 측정

Edmondson 의 1999년 연구는 설문을 포함한 다중 방법 현장 연구로 팀 심리적 안전감을 측정했다. 팀 단위 익명 설문으로 추세를 보되, 점수를 관리자 평가에 직접 쓰면 응답이 왜곡된다. 앞 글(SE100 #095)의 SPACE 처럼 지각 지표로 쓰고 팀이 스스로 해석한다.

## 흔한 오해와 함정

- **"심리적 안전감 = 다들 착하게 대하기."** 오히려 반대 의견과 나쁜 소식을 말할 수 있게 하는 것이다. 갈등을 피하는 팀은 안전감이 낮을 수 있다.
- **"안전하면 책임이 없어진다."** 비난 없는 포스트모템도 개선 조치와 담당자를 정한다. 사람을 처벌하지 않을 뿐, 시스템의 책임은 분명히 한다.
- **Project Aristotle 을 일반 법칙처럼 인용한다.** Google 내부 연구 결과이며, 가이드 스스로 "Google 의 측정에서" 라는 단서를 단다. 동료심사 연구(Edmondson 1999 등)와 구분해 인용한다.
- **안전감만 올리고 기준은 없다.** 학습 행동이 매개 변수라는 1999년 결과를 기억한다. 높은 기준 + 높은 안전감이 학습을 만든다.
- **포스트모템에서 "인적 오류" 를 근본 원인으로 적는다.** 그건 조사의 시작점이지 결론이 아니다.

## 확인 문제

1. Edmondson 의 팀 심리적 안전감 정의를 쓰라.
2. Edmondson 1999 연구에서 심리적 안전감과 팀 성과 사이를 매개한 변수는? 이것이 실무에 주는 시사점은?
3. Project Aristotle 의 다섯 동인을 순서대로 쓰고, 이 결과를 인용할 때 주의할 점은?
4. Westrum 의 세 문화 유형에서 "실패" 에 대한 반응은 각각 어떻게 다른가?
5. 포스트모템 문장 "운영자가 실수로 잘못된 명령을 실행했다" 를 비난 없는 형태로 고쳐 쓰라.

### 풀이

1. 팀이 대인 관계상의 위험 감수에 안전하다는, 팀원들이 공유하는 믿음.
2. 학습 행동. 안전감 자체보다 그것이 가능하게 하는 질문·피드백 요청·오류 보고·실험 같은 행동이 성과로 이어지므로, 안전감과 함께 학습 행동을 촉진하고 기준을 유지해야 한다.
3. 심리적 안전감, 신뢰성, 구조와 명확성, 의미, 영향. Google 내부 180개 팀 연구이며 동료심사 논문이 아니고, 가이드 스스로 Google 의 측정에서의 결과라는 단서를 단다.
4. 병리적: 희생양 찾기, 관료적: 처벌(정의 집행), 생성적: 탐구.
5. 예: "운영자는 런북 3단계의 명령을 실행했다. 해당 명령은 대상 클러스터를 확인하지 않으며, 터미널 프롬프트에 현재 컨텍스트가 표시되지 않았다." 사람 대신 그 행동을 가능하게 한 조건을 적는다.

## 더 읽을거리 (References)

- Amy Edmondson, [Psychological Safety and Learning Behavior in Work Teams](http://nrs.harvard.edu/urn-3:HUL.InstRepos:37968728), *Administrative Science Quarterly* 44(2), 350–383, 1999
- Amy C. Edmondson, Zhike Lei, "Psychological Safety: The History, Renaissance, and Future of an Interpersonal Construct", *Annual Review of Organizational Psychology and Organizational Behavior* 1, 23–43, 2014, DOI 10.1146/annurev-orgpsych-031413-091305 (서지 정보)
- Google re:Work, [Guide: Understand team effectiveness](https://rework.withgoogle.com/intl/en/guides/understand-team-effectiveness)
- Per Lenberg, Robert Feldt, [Psychological Safety and Norm Clarity in Software Engineering Teams](https://arxiv.org/abs/1802.01378), CHASE 2018
- Ron Westrum, "A Typology of Organisational Cultures", *Quality and Safety in Health Care* 13(suppl 2), ii22–ii27, 2004, DOI 10.1136/qshc.2003.009522 (서지 정보)
- DORA, [Generative organizational culture](https://dora.dev/capabilities/generative-organizational-culture/)
- Betsy Beyer 외, [Site Reliability Engineering, Chapter 15: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
