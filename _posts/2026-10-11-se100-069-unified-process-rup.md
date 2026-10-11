---
layout: post
title: "[SE100 #069] 통합 프로세스(UP/RUP) — 단계와 반복"
date: 2026-10-11 17:05:23 +0900
categories: [software-engineering]
tags: [se100, process, unified-process, rup, iterative-development]
---

소프트웨어 공학 100 주제 시리즈의 69번째 글이다. (카테고리: 프로세스와 방법론)

## 한 줄 요약

통합 프로세스의 핵심 아이디어는 **시간 축(단계·반복)과 내용 축(분야·워크플로)을 분리**한 것이다. 요구·설계·구현·테스트는 "단계" 가 아니라 모든 반복에서 비중만 달리하며 계속되는 활동이고, 단계는 활동이 아니라 **어떤 위험을 해소했는가**로 끝난다.

## 왜 필요한가

폭포수의 단계 이름은 활동 이름이다. "분석 단계", "설계 단계", "구현 단계". 그래서 "설계 단계가 끝났다" 는 "설계 문서를 다 썼다" 는 뜻이 되고, 설계가 실제로 맞는지는 구현 단계에 가서야 안다.

반대로 계획 없는 반복은 방향을 잃는다. 2주마다 무언가를 만들지만 "아키텍처는 언제 굳히나", "고객에게 고정가 견적은 언제 줄 수 있나" 에 답하지 못한다.

통합 프로세스(Unified Process, UP)는 이 둘 사이의 답이다. 반복으로 일하되, 반복들을 **위험 해소 기준의 관문**으로 묶어 관리자와 고객이 의사결정할 지점을 준다. 오늘날 대형 프로젝트에서 "애자일 반복 + 단계 관문" 을 섞는 방식의 원형이 여기 있다.

## 핵심 개념

### UP 와 RUP

| 이름 | 성격 | 대표 문헌 |
|---|---|---|
| Unified Process (UP) | 공개된 프로세스 프레임워크 | Ivar Jacobson, Grady Booch, James Rumbaugh, *The Unified Software Development Process*, Addison-Wesley, 1999 |
| Rational Unified Process (RUP) | Rational 사의 상용 프로세스 제품 (현재 IBM Rational) | Philippe Kruchten, *The Rational Unified Process: An Introduction*, Addison-Wesley, 1998 |

Jacobson 등은 UP 를 **유스케이스 주도, 아키텍처 중심, 반복·점증적** 프로세스로 특징짓는다. 이 글에서 인용하는 구체적인 단계·마일스톤 정의는 Rational 의 백서 [Rational Unified Process: Best Practices for Software Development Teams](https://public.dhe.ibm.com/software/rational/web/whitepapers/2003/rup_bestpractices.pdf)(TP026B)에서 가져왔다.

### 두 개의 축

백서는 RUP 를 두 차원으로 설명한다.

- **가로축(시간, 동적 측면)**: 주기(cycle), 단계(phase), 반복(iteration), 마일스톤.
- **세로축(내용, 정적 측면)**: 활동, 산출물, 작업자(worker), 워크플로.

```
                 도입        정련          구축              전이
               Inception  Elaboration  Construction      Transition
              ┌────────┬──────────────┬────────────────┬──────────┐
 비즈니스 모델링 │▓▓▓▓    │▓▓            │                │          │
 요구사항       │▓▓▓▓▓▓  │▓▓▓▓▓▓▓       │▓▓▓             │▓         │
 분석·설계      │▓▓      │▓▓▓▓▓▓▓▓      │▓▓▓▓▓           │▓         │
 구현           │▓       │▓▓▓▓▓         │▓▓▓▓▓▓▓▓▓▓▓▓    │▓▓        │
 테스트         │▓       │▓▓▓▓          │▓▓▓▓▓▓▓▓▓       │▓▓▓▓      │
 배포           │        │▓             │▓▓▓             │▓▓▓▓▓▓▓   │
              ├────────┼──────────────┼────────────────┼──────────┤
 반복           │  I1    │  E1   E2     │ C1  C2  C3  C4 │  T1  T2  │
              └────────┴──────────────┴────────────────┴──────────┘
                     LCO           LCA               IOC        제품 릴리스
```

(막대 길이는 개념 설명용이다.) 이 그림 — 흔히 "혹 그림(hump chart)" 이라 부른다 — 이 UP 의 요점을 한 장에 담는다. **모든 분야가 모든 단계에 있다.** 정련 단계에도 구현과 테스트가 있고, 구축 단계에도 요구사항 작업이 있다. 단계마다 달라지는 것은 비중이다.

### 아홉 워크플로

백서는 아홉 개의 핵심 워크플로를 든다.

| 엔지니어링 워크플로 (6) | 지원 워크플로 (3) |
|---|---|
| 비즈니스 모델링, 요구사항, 분석·설계, 구현, 테스트, 배포 | 프로젝트 관리, 형상·변경 관리, 환경 |

그리고 이렇게 경고한다. 여섯 엔지니어링 워크플로의 이름이 전통적 폭포수의 순차 단계를 떠올리게 하지만, 반복 프로세스의 단계는 그와 다르며 이 워크플로들은 생명주기 내내 거듭 다시 방문된다.

### 네 단계와 네 마일스톤

| 단계 | 목적 (백서) | 끝나는 마일스톤 | 통과 못 하면 |
|---|---|---|---|
| 도입 | 비즈니스 케이스를 세우고 프로젝트 범위를 정한다 | 생명주기 목표 (LCO) | 취소 또는 근본적 재검토 |
| 정련 | 문제 영역 분석, 견고한 아키텍처 기반 확립, 계획 수립, **가장 위험한 요소 제거** | 생명주기 아키텍처 (LCA) | 중단 또는 근본적 재검토 |
| 구축 | 남은 구성 요소·기능을 개발·통합·테스트 | 초기 운영 능력 (IOC) | 전이를 한 릴리스 연기 |
| 전이 | 제품을 사용자 커뮤니티로 넘긴다 | 제품 릴리스 | — |

LCO, LCA, IOC 라는 이름은 Boehm 의 나선 모델에서 왔다. Boehm 의 [SEI 보고서](https://www.sei.cmu.edu/library/spiral-development-experience-principles-and-refinements-spiral-development-workshop-february-9-2000/)(CMU/SEI-2000-SR-008)는 이 앵커 포인트가 USC 제휴 워크숍에서 정의됐고, 당시 RUP 의 단계를 정의하던 Rational 이 이를 단계 관문으로 채택했다고 쓴다(SE100 #062 에서 다룬다).

### 정련 단계가 가장 중요하다

백서는 "네 단계 중 정련 단계가 가장 중요하다고 쉽게 주장할 수 있다" 고 쓴다. 이 단계가 끝나면 어려운 "엔지니어링" 은 끝난 것으로 보고, 구축·전이에 투자할지를 결정한다. 대부분의 프로젝트에서 이것은 **가볍고 민첩한 저위험 운영에서 관성이 큰 고비용·고위험 운영으로 넘어가는** 지점이다. 그래서 정련의 기준은 이렇게 표현된다. 아키텍처·요구·계획이 충분히 안정되고 위험이 충분히 완화되어, 조직이 **고정가 구축 단계**에 약속할 수 있을 수준.

정련의 핵심 산출물은 문서가 아니라 **실행 가능한 아키텍처 원형**이다. 백서에 따르면 이것은 도입 단계에서 식별한 중요 유스케이스 — 보통 프로젝트의 주요 기술 위험을 드러내는 것들 — 를 최소한 다뤄야 한다. 버리는 탐색용 프로토타입을 따로 만들 수도 있지만, 목표는 제품 품질의 진화형 원형이다.

### 여섯 가지 모범 실천

백서가 드는 RUP 의 여섯 실천이다.

1. 반복적으로 개발한다
2. 요구사항을 관리한다
3. 컴포넌트 기반 아키텍처를 쓴다
4. 소프트웨어를 시각적으로 모델링한다 (UML)
5. 소프트웨어 품질을 검증한다
6. 소프트웨어 변경을 통제한다

백서는 폭포수 대비 반복 접근의 이점으로 위험의 조기 완화, 변경 관리 용이성, 높은 재사용, 진행하며 배우는 팀, 전반적 품질 향상을 든다.

## 실무 적용

### 애자일 팀이 UP 에서 가져올 것

UP 를 통째로 도입할 필요는 없다. 스프린트로 일하는 팀이라도 **단계 관문의 질문**은 그대로 쓸모 있다.

```yaml
# 신규 서비스 로드맵: 스프린트는 2주, 관문은 위험 기준
phases:
  inception:
    sprints: 1
    exit_question: "만들 가치가 있고, 실현 가능한 구조가 적어도 하나 있는가?"   # LCO
    evidence: [problem-statement, top-10-risks, rough-estimate-range]
  elaboration:
    sprints: 2-4
    exit_question: "가장 위험한 유스케이스가 실제 아키텍처 위에서 끝까지 동작하는가?"  # LCA
    evidence:
      - walking-skeleton deployed to staging   # 실행 가능한 아키텍처
      - load test on critical path
      - external API integration proven
      - ADRs for irreversible decisions          # SE100 #025
  construction:
    sprints: N
    exit_question: "사용자·운영 쪽이 실제로 쓸 준비가 됐는가?"   # IOC
  transition:
    exit_question: "사용자가 만족하고, 지출이 계획 대비 수용 가능한가?"
```

정련을 "걷는 해골(walking skeleton)" — 가장 얇은 수준이지만 끝에서 끝까지 실제로 배포되어 동작하는 시스템 — 로 끝내는 것이 현대적 해석이다. 백서의 "실행 가능한 아키텍처 원형" 과 같은 생각이다.

### 정련 단계의 반복 계획 예

| 반복 | 목표 | 해소하는 위험 |
|---|---|---|
| E1 | 결제 흐름을 실제 PG 샌드박스와 끝까지 연결 | 외부 연동 규격 |
| E1 | 주문 조회를 예상 피크 부하로 시험 | 성능 요건 |
| E2 | 인증·권한 구조 확정, ADR 작성 | 보안 아키텍처 |
| E2 | 배포 파이프라인과 관측 기본 세트 | 운영 가능성 |

각 반복은 "기능 몇 개" 가 아니라 "위험 몇 개" 로 계획된다. 기능은 그 위험을 확인하는 수단이다.

## 흔한 오해와 함정

- **단계 = 활동.** 정련 단계를 "설계 문서 쓰는 기간" 으로 운영하면 RUP 의 탈을 쓴 폭포수다. 정련 단계에서도 코드를 짜고 테스트한다.
- **산출물 전부를 만든다.** RUP 는 많은 템플릿을 제공하지만 백서 스스로 RUP 를 "구성 가능한 프로세스" 라 부르고, 조직 특성에 맞게 조정(tailoring)해야 하며 "부가가치가 거의 없는 산출물을 만드는 쓸모없는 일" 을 하며 맹목적으로 따르지 말라고 쓴다. 가능한 한 린하게 만들라는 것이다.
- **반복 없이 단계만 쓴다.** 단계마다 한 번씩만 돌면 네 단계짜리 폭포수다. 반복이 단계 안에서 실제로 실행 가능한 결과를 내야 한다.
- **LCA 를 날짜로 통과시킨다.** 정련의 종료 기준은 일정이 아니라 위험 해소다. 위험이 남았는데 날짜가 됐다고 구축으로 넘어가면, 가장 비싼 단계에서 가장 비싼 방식으로 위험을 만난다.
- **UP 와 애자일은 반대다.** UP 는 반복·점증 개발을 전제로 한다. 차이는 문서 비중과 계획 단위이지 철학의 정반대가 아니다.

## 확인 문제

1. UP 에서 "단계" 와 "워크플로(분야)" 는 각각 어느 축에 속하며, 둘을 분리한 이점은?
2. 정련 단계가 끝날 때 통과해야 하는 마일스톤의 이름과, 그 기준을 위험 관점에서 쓰라.
3. 백서가 정련 단계를 가장 중요하다고 한 이유는?
4. LCO·LCA·IOC 라는 이름은 어디서 왔는가?
5. 애자일 팀이 UP 의 단계 관문을 쓸 때 반복 계획의 단위는 무엇이어야 하는가?

### 풀이

1. 단계는 시간(동적) 축, 워크플로는 내용(정적) 축이다. 분리했기 때문에 모든 활동이 모든 단계에서 비중만 달리해 일어날 수 있고, 단계를 활동 완료가 아니라 위험 해소로 끝낼 수 있다.
2. 생명주기 아키텍처(LCA). 아키텍처·요구·계획이 충분히 안정되고 주요 위험이 충분히 완화되어 구축 단계의 비용·일정을 예측 가능하게 정할 수 있어야 한다.
3. 정련이 끝나면 구축·전이에 투자할지 결정하는데, 이것이 저비용·저위험 운영에서 고비용·고관성 운영으로 넘어가는 지점이기 때문이다.
4. Boehm 의 나선 모델 앵커 포인트에서 왔다. Rational 이 RUP 의 단계 관문으로 채택했다.
5. 기능 수가 아니라 해소할 위험. 각 반복이 어떤 위험을 실행 가능한 결과로 확인하는지가 계획의 단위다.

## 더 읽을거리 (References)

- Rational Software, [Rational Unified Process: Best Practices for Software Development Teams](https://public.dhe.ibm.com/software/rational/web/whitepapers/2003/rup_bestpractices.pdf), White Paper TP026B
- Barry Boehm (ed. Wilfred J. Hansen), [Spiral Development: Experience, Principles, and Refinements](https://www.sei.cmu.edu/library/spiral-development-experience-principles-and-refinements-spiral-development-workshop-february-9-2000/), CMU/SEI-2000-SR-008, 2000
- Barry Boehm, [Anchoring the Software Process](https://doi.org/10.1109/52.526834), IEEE Software 13(4), 1996
- Ivar Jacobson, Grady Booch, James Rumbaugh, *The Unified Software Development Process*, Addison-Wesley, 1999 (서지 정보)
- Philippe Kruchten, *The Rational Unified Process: An Introduction*, Addison-Wesley, 1998 (서지 정보)
- CS300: [소프트웨어 개발 생명주기]({% post_url 2026-10-10-cs300-181-software-development-life-cycle %}), [UML 기초]({% post_url 2026-10-10-cs300-184-uml-basics %})
