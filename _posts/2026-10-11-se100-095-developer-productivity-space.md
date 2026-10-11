---
layout: post
title: "[SE100 #095] 개발자 생산성 측정 — SPACE 프레임워크"
date: 2026-10-11 17:10:45 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, developer-productivity, space-framework, dora-metrics, developer-experience]
---

소프트웨어 공학 100 주제 시리즈의 95번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

개발자 생산성은 하나의 숫자로 잡히지 않는다. SPACE 는 만족·성과·활동·소통·효율의 다섯 차원 중 **최소 세 차원** 에서, 지각(설문) 지표를 하나 이상 섞어 서로 긴장하는 지표 묶음을 고르라고 권한다.

## 왜 필요한가

경영진은 "개발 조직이 얼마나 생산적인가" 를 묻고, 측정하기 쉬운 것부터 센다. 커밋 수, PR 수, 코드 라인 수, 스토리 포인트. 그러면 다음 일이 생긴다.

- PR 을 잘게 쪼개 개수를 늘린다. 리뷰어 부담만 커진다.
- 리팩터링으로 코드를 줄인 사람이 "마이너스 생산성" 으로 찍힌다.
- 야근으로 활동량이 늘어난 팀이 "생산적" 으로 보이지만, 실은 나쁜 시스템을 몸으로 버티는 중이다.

Martin Fowler 는 2003년 [CannotMeasureProductivity](https://martinfowler.com/bliki/CannotMeasureProductivity.html) 에서 코드 라인은 산출을 제대로 재지 못하고(잘 설계된 코드는 더 짧다), 기능 점수조차 진짜 산출인 **고객에게 전달된 사업 가치** 를 놓친다고 썼다. 문제는 측정을 포기할 수도 없다는 것이다. 개선하려면 어딘가를 봐야 한다. SPACE 는 "무엇을 재면 덜 틀리는가" 에 대한 답이다.

## 핵심 개념

### SPACE 의 출처

Nicole Forsgren, Margaret-Anne Storey, Chandra Maddila, Thomas Zimmermann, Brian Houck, Jenna Butler 의 [The SPACE of Developer Productivity](https://queue.acm.org/detail.cfm?id=3454124) (ACM Queue 19(1), 2021). 게재 당시 Forsgren 은 GitHub, Storey 는 빅토리아 대학, 나머지 넷은 Microsoft Research 소속이었다.

### 다섯 가지 오해

논문은 먼저 생산성에 관한 통념 다섯 가지를 반박한다.

| 오해 | 논문의 반박 요지 |
|---|---|
| 생산성은 개발자 활동량이다 | 활동량 증가는 나쁜 시스템을 "힘으로 밀어붙이는" 신호일 수도 있다 |
| 생산성은 개인 성과의 문제다 | 팀과 조직에 대한 기여까지 균형 있게 봐야 한다 |
| 지표 하나로 다 알 수 있다 | "단 하나의 지표" 로 팀을 점수 매기고 비교하는 것은 틀렸다 |
| 생산성 측정은 관리자에게만 쓸모 있다 | 잘 쓰면 개발자 자신이 방해 요소를 줄이는 데 쓴다 |
| 생산성은 엔지니어링 시스템과 도구의 문제다 | 환경과 문화 같은 사람 요인도 크다 |

### 다섯 차원

| 차원 | 논문의 정의 | 예시 지표 |
|---|---|---|
| **S**atisfaction and well-being | 일·팀·도구·문화에 대한 충족감, 건강과 행복 | 개발자 만족도 설문, 번아웃 지표 |
| **P**erformance | 시스템이나 프로세스의 **결과** | 결함률, 변경 실패율, 고객 만족, 기능 사용률 |
| **A**ctivity | 업무 중 완료된 행동이나 산출의 **개수** | 커밋·PR·배포·리뷰 수 |
| **C**ommunication and collaboration | 사람과 팀이 소통하고 함께 일하는 방식 | 리뷰 품질, 온보딩 시간, 지식 탐색 용이성 |
| **E**fficiency and flow | 방해와 지연을 최소화하며 일을 진척시키는 능력 | 리뷰 대기 시간, 인계 횟수, 방해 없는 시간 |

성과(Performance) 정의가 핵심이다. 논문은 개인의 기여를 제품 결과에 직접 잇기 어렵다고 인정한다. 코드를 많이 쓴 개발자가 좋은 코드를 쓴 것은 아니고, 좋은 코드가 고객 가치를 낸 것도 아니다. 그래서 성과는 **결과(outcome)** 로, 활동은 **개수(output)** 로 분리한다.

### 사용 규칙

논문에서 실무에 바로 쓰이는 규칙은 세 가지다.

1. **최소 세 차원에서 지표를 고른다.** 이미 커밋 수(활동)를 재고 있다면 PR 수와 코딩 시간을 더하는 것은 같은 차원을 채우는 것일 뿐이다.
2. **최소 하나는 지각(perceptual) 지표, 즉 설문이어야 한다.** 논문은 지각 데이터가 시스템 계측만으로 보는 것보다 더 정확하고 완전한 정보를 줄 때가 많다고 쓴다.
3. **지표들이 서로 긴장하도록 고르는 것은 의도된 설계다.** 균형 잡힌 묶음이 실제 상황을 더 잘 보여 준다.

또 개인·팀·시스템의 세 수준에서 각 차원을 볼 수 있다. 같은 리뷰 활동도 개인 수준에서는 리뷰 수, 시스템 수준에서는 리뷰 대기 시간으로 나타난다.

### DORA 지표와의 관계

[DORA 의 소프트웨어 전달 지표](https://dora.dev/guides/dora-metrics/)는 현재 다섯 개다. 처리량(throughput) 지표로 **변경 리드 타임, 배포 빈도, 실패한 배포의 복구 시간**, 불안정성(instability) 지표로 **변경 실패율, 배포 재작업률(rework rate)** 이다. 처음 알려진 "네 가지 키" 에 재작업률이 더해졌다.

DORA 지표는 SPACE 로 보면 주로 성과와 효율·흐름 차원에, 그리고 팀·시스템 수준에 놓인다. 만족·소통 차원은 비어 있다. 그래서 DORA 만으로 생산성을 말하면 SPACE 가 경고한 "한 차원 편중" 이 된다. DORA 자신도 같은 문서에서 지표를 목표로 삼지 말 것(Goodhart 의 법칙), 팀 간 비교에 쓰지 말 것, 경쟁에 쓰지 말 것을 명시한다.

### 후속: DevEx

Abi Noda, Margaret-Anne Storey, Nicole Forsgren, Michaela Greiler 는 [DevEx: What Actually Drives Productivity](https://queue.acm.org/detail.cfm?id=3595878) (ACM Queue 21(2), 2023)에서 개발자 경험을 **피드백 루프, 인지 부하, 몰입 상태(flow state)** 의 세 차원으로 압축했다(Noda·Greiler 는 개발자 경험 측정 제품을 파는 회사 DX 소속이라는 점은 감안해서 읽는다). 측정은 개발자의 **지각** 과 **워크플로** 데이터를 짝지어 수집하고, 그 위에 전체 KPI(North Star 지표)를 둔다. SPACE 가 "무엇을 균형 있게 볼지" 라면 DevEx 는 "무엇을 고치면 생산성이 오르는지" 에 초점을 둔다. 인지 부하는 다음 글(SE100 #096)의 팀 토폴로지에서 다시 나온다.

## 실무 적용

### 예: 코드 리뷰 개선 프로젝트의 지표 묶음

"리뷰가 느리다" 는 불만이 있을 때, SPACE 로 지표를 고른다.

| 차원 | 지표 | 수준 | 유형 |
|---|---|---|---|
| Satisfaction | "리뷰 과정에 만족한다" 5점 척도 (분기 설문) | 개인 | 지각 |
| Performance | 리뷰 통과 후 배포의 변경 실패율 | 시스템 | 계측 |
| Activity | 주간 리뷰 완료 수 | 팀 | 계측 |
| Efficiency/flow | PR 생성 → 첫 리뷰 응답 시간 중앙값 | 시스템 | 계측 |

네 차원, 지각 지표 하나, 그리고 **긴장 관계** 가 있다. 응답 시간을 줄이려고 리뷰를 대충 하면 변경 실패율이 오르고, 리뷰 부담을 한 사람에게 몰면 만족도가 떨어진다.

```sql
-- 첫 리뷰 응답 시간 중앙값 (주 단위). 봇 계정과 작성자 본인 코멘트는 제외.
SELECT date_trunc('week', pr.created_at)            AS week,
       percentile_cont(0.5) WITHIN GROUP (
         ORDER BY EXTRACT(EPOCH FROM (r.first_review_at - pr.created_at)) / 3600
       )                                             AS median_hours_to_first_review
FROM pull_requests pr
JOIN LATERAL (
  SELECT min(c.created_at) AS first_review_at
  FROM review_events c
  WHERE c.pr_id = pr.id AND c.author_id <> pr.author_id AND NOT c.is_bot
) r ON true
WHERE pr.is_draft = false
GROUP BY 1 ORDER BY 1;
```

### 운영 원칙

- **팀이 자기 지표를 고르고 해석한다.** 같은 지표도 팀 맥락에 따라 의미가 다르다.
- **개인 순위표를 만들지 않는다.** 논문의 둘째 오해와 DORA 의 경고가 같은 지점을 가리킨다.
- **설문은 짧게, 주기적으로.** 추세를 보려면 같은 문항을 반복해야 한다. 문화가 다른 조직끼리는 기준선이 달라 비교하지 않는다(논문도 이 점을 지적한다).
- **지표는 질문을 만든다, 답을 주지 않는다.** 응답 시간이 늘었다면 원인을 팀과 함께 찾는다.

## 흔한 오해와 함정

- **"SPACE 는 다섯 개 지표다."** 다섯 **차원** 이다. 각 차원에 어떤 지표를 둘지는 목표에 따라 고른다.
- **활동 지표를 성과로 착각한다.** 배포 수나 PR 수는 개수일 뿐 결과가 아니다.
- **지표를 목표로 만든다.** 사람은 측정되는 것에 맞춰 행동을 바꾼다. 지표가 목표가 되는 순간 지표로서의 가치가 떨어진다. DORA 문서가 Goodhart 의 법칙을 직접 거론하는 이유다.
- **설문은 주관적이라 믿을 수 없다.** 논문은 지각 데이터가 계측보다 더 완전한 그림을 줄 때가 많다고 본다. 주관성은 결함이 아니라 계측이 못 보는 것을 보는 수단이다.
- **DORA 를 팀 간 비교에 쓴다.** 서비스 특성(규제, 레거시, 하드웨어 의존)이 다르면 같은 수치가 다른 의미다.

## 확인 문제

1. SPACE 의 다섯 차원을 쓰고, Performance 와 Activity 의 차이를 설명하라.
2. 커밋 수, PR 수, 코딩 시간으로 대시보드를 만들었다. SPACE 관점의 문제는?
3. SPACE 가 지각 지표를 최소 하나 넣으라고 권하는 근거는?
4. DORA 의 다섯 지표를 처리량과 불안정성으로 나누라.
5. DevEx 의 세 차원은 무엇이며, SPACE 와 초점이 어떻게 다른가?

### 풀이

1. Satisfaction and well-being, Performance, Activity, Communication and collaboration, Efficiency and flow. Performance 는 시스템·프로세스의 결과(품질, 고객 가치), Activity 는 완료된 행동·산출의 개수다.
2. 셋 다 Activity 한 차원이다. 최소 세 차원, 지각 지표 하나 이상이라는 권고를 어기며, 활동량을 생산성으로 착각하는 첫째 오해에 빠진다.
3. 지각 데이터는 사람의 실제 경험을 담아, 시스템 계측만으로는 보이지 않는 정보를 더 정확하고 완전하게 줄 때가 많기 때문이다.
4. 처리량: 변경 리드 타임, 배포 빈도, 실패한 배포의 복구 시간. 불안정성: 변경 실패율, 배포 재작업률.
5. 피드백 루프, 인지 부하, 몰입 상태. SPACE 가 생산성을 균형 있게 보는 차원의 틀이라면, DevEx 는 개발자 경험의 동인을 지각·워크플로 데이터로 재서 개선 지점을 찾는 데 초점을 둔다.

## 더 읽을거리 (References)

- N. Forsgren, M.-A. Storey, C. Maddila, T. Zimmermann, B. Houck, J. Butler, [The SPACE of Developer Productivity](https://queue.acm.org/detail.cfm?id=3454124), ACM Queue 19(1), 2021
- A. Noda, M.-A. Storey, N. Forsgren, M. Greiler, [DevEx: What Actually Drives Productivity](https://queue.acm.org/detail.cfm?id=3595878), ACM Queue 21(2), 2023
- DORA, [DORA's software delivery performance metrics](https://dora.dev/guides/dora-metrics/)
- Martin Fowler, [CannotMeasureProductivity](https://martinfowler.com/bliki/CannotMeasureProductivity.html), 2003
- Nicole Forsgren, Jez Humble, Gene Kim, *Accelerate: The Science of Lean Software and DevOps*, IT Revolution, 2018 (서지 정보)
- [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %}) (CS300 #196), [코드 리뷰]({% post_url 2026-10-10-cs300-190-code-review %}) (CS300 #190)
