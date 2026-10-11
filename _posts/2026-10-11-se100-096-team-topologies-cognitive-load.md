---
layout: post
title: "[SE100 #096] 팀 토폴로지와 인지 부하"
date: 2026-10-11 17:10:46 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, team-topologies, cognitive-load, conways-law]
---

소프트웨어 공학 100 주제 시리즈의 96번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

시스템 구조는 조직의 소통 구조를 닮는다(Conway). 그렇다면 원하는 아키텍처가 나오도록 팀을 설계해야 하고, 그 설계의 제약 조건은 **팀이 감당할 수 있는 인지 부하** 다. 팀 토폴로지는 이를 네 가지 팀 유형과 세 가지 상호작용 방식으로 정리한 어휘다.

## 왜 필요한가

조직도가 아키텍처를 망치는 장면은 흔하다.

- 프런트엔드 팀, 백엔드 팀, DBA 팀으로 나눴더니 기능 하나 내는 데 세 팀의 일정을 맞춰야 한다. 모든 기능이 인계(hand-off)를 거친다.
- 마이크로서비스로 쪼갰지만 한 팀이 서비스 열두 개, 쿠버네티스 매니페스트, 모니터링, 온콜까지 맡는다. 아무것도 깊이 알지 못한다.
- "플랫폼 팀" 을 만들었는데 티켓 큐가 되어, 모든 팀이 그 앞에 줄을 선다.

셋 다 기술 문제처럼 보이지만 원인은 **팀의 경계와 책임 범위** 다. 아키텍처 논의에 팀 설계를 넣지 않으면 같은 문제가 반복된다.

## 핵심 개념

### Conway 의 법칙

Melvin Conway 는 [How Do Committees Invent?](https://www.melconway.com/Home/Committees_Paper.html) (Datamation, 1968년 4월)의 결론에서 이렇게 썼다.

> 시스템을 설계하는 조직은 (여기서 쓰는 넓은 의미에서) 그 조직의 소통 구조를 복제한 설계를 만들도록 제약된다.

Martin Fowler 는 [ConwaysLaw](https://martinfowler.com/bliki/ConwaysLaw.html) (2022)에서 Conway 의 통찰을 "소프트웨어 결합은 사람 사이의 소통이 가능하게 하고 부추긴다" 로 요약하고, 대응을 셋으로 나눈다.

| 대응 | 내용 |
|---|---|
| 무시 | 조직 구조의 영향을 고려하지 않는다 |
| 수용 | 실제 소통 구조에 아키텍처를 맞춘다 |
| 역(逆) Conway 기동 | 원하는 아키텍처가 나오도록 팀 구조를 먼저 바꾼다 |

Fowler 는 같은 글에서 팀을 재편해도 이미 굳은 아키텍처가 바로 바뀌지는 않으며, 둘을 함께 점진적으로 진화시켜야 한다고 경고한다.

### 인지 부하

인지 부하(cognitive load)는 교육심리학자 John Sweller 의 개념이다. 그는 1988년 *Cognitive Science* 12(2) 논문 "Cognitive Load During Problem Solving: Effects on Learning" 에서 작업 기억의 한계가 문제 해결과 학습에 미치는 영향을 다뤘고, 이후 Sweller, van Merriënboer, Paas 의 1998년 논문 "Cognitive Architecture and Instructional Design" (*Educational Psychology Review* 10(3))에서 내재적·외재적·본유적 부하의 구분이 정리됐다. 팀 토폴로지는 이 구분을 팀에 적용한다.

| 부하 유형 | 개인 학습에서 | 팀에 적용하면 | 대응 |
|---|---|---|---|
| 내재적(intrinsic) | 과제 자체의 난이도 | 도메인과 핵심 기술의 본질적 복잡성 | 교육, 짝 작업 |
| 외재적(extraneous) | 과제와 무관한 방해 | 배포 절차, 환경 설정, 수동 운영 | **제거·자동화** (플랫폼) |
| 본유적(germane) | 학습·이해에 쓰는 부하 | 도메인 이해를 깊게 하는 데 쓰는 여력 | **최대한 남겨 둔다** |

목표는 외재적 부하를 줄여 본유적 부하에 쓸 여력을 늘리는 것이다. 앞 글(SE100 #095)의 DevEx 프레임워크가 인지 부하를 개발자 경험의 세 차원 중 하나로 둔 것도 같은 맥락이다.

### 네 가지 팀 유형

Matthew Skelton 과 Manuel Pais 의 *Team Topologies* (IT Revolution, 2019; 2판 2025)와 [공식 사이트의 핵심 개념](https://teamtopologies.com/key-concepts) 정리를 따른다.

| 유형 | 정의 | 존재 이유 |
|---|---|---|
| 스트림 정렬(stream-aligned) | (대개) 사업 도메인의 한 부분에서 오는 작업 흐름에 정렬된 팀 | 가치를 직접 전달하는 기본 단위 |
| 활성화(enabling) | 스트림 정렬 팀이 장애물을 넘도록 돕고, 빠진 역량을 찾아냄 | 새 기술·관행 전파 |
| 복잡 하위 시스템(complicated subsystem) | 상당한 수학·계산·기술 전문성이 필요한 영역 | 전문 부하를 격리 |
| 플랫폼(platform) | 스트림 정렬 팀의 전달을 가속하는 **설득력 있는 내부 제품** 을 제공 | 외재적 부하 제거 |

스트림 정렬 팀이 기본이고, 나머지 셋은 **스트림 정렬 팀의 인지 부하를 줄이기 위해** 존재한다. 플랫폼은 "인프라 팀의 새 이름" 이 아니라 내부 제품이라는 점이 핵심이다. 쓰지 않을 자유가 있어도 쓰고 싶은 것이어야 한다.

### 세 가지 상호작용 방식

| 방식 | 정의 | 언제 |
|---|---|---|
| 협업(collaboration) | 정해진 기간 동안 함께 일하며 새것(API, 관행, 기술)을 발견 | 경계가 아직 불분명할 때 |
| X-as-a-Service | 한 팀이 제공하고 다른 팀이 서비스로 소비 | 경계가 안정됐을 때 |
| 촉진(facilitating) | 한 팀이 다른 팀을 돕고 멘토링 | 역량 이전 |

협업은 비싸다. 두 팀의 인지 부하가 서로 섞이기 때문이다. 그래서 협업은 **기간을 정해서** 하고, 발견이 끝나면 X-as-a-Service 로 옮긴다. 상호작용 방식은 고정이 아니라 진화한다.

```
 [결제 스트림 팀] ──collaboration(6주)──► [플랫폼 팀]   : 새 배포 파이프라인 설계
         │
         └─ 이후 ── X-as-a-Service ──► [플랫폼 팀]      : 셀프서비스로 사용

 [활성화 팀: 관측성] ──facilitating──► [결제 스트림 팀] : 트레이싱 도입 코칭 후 철수
 [복잡 하위 시스템: 사기 탐지 모델] ──X-as-a-Service──► [결제 스트림 팀]
```

## 실무 적용

### 팀 인지 부하 점검 설문

정답이 있는 측정은 아니지만, 분기마다 같은 문항으로 추세를 본다.

1. 우리 팀이 책임지는 서비스·컴포넌트를 한 사람이 화이트보드에 설명할 수 있는가? (1~5)
2. 지난 분기 장애 중, 원인을 아는 사람이 팀 안에 있었던 비율은?
3. 기능 하나를 배포하기 위해 다른 팀의 작업을 **기다려야** 하는 경우가 얼마나 잦은가?
4. 업무 시간 중 도메인 문제가 아니라 도구·환경·절차와 씨름하는 비율은? (외재적 부하)
5. 팀이 맡은 영역 중 "그냥 아무도 안 건드렸으면 좋겠는" 영역이 있는가?

### 경계 설계 체크리스트

- [ ] 각 스트림 정렬 팀의 소유 범위가 **사업 흐름** 기준으로 정의되어 있다 (기술 계층 기준이 아님)
- [ ] 한 기능의 리드 타임에서 팀 간 대기 시간이 차지하는 비중을 안다
- [ ] 플랫폼은 문서화된 셀프서비스 인터페이스와 내부 고객 피드백 루프가 있다
- [ ] 협업 관계에는 종료 시점이 있다
- [ ] 서비스 소유권 목록(예: 저장소별 CODEOWNERS)이 조직도와 일치한다

```yaml
# 팀 API: 팀이 다른 팀에 공개하는 '사용 설명서' (팀 토폴로지의 Team API 개념을 단순화)
team: payments-stream
owns: [payment-api, refund-worker, settlement-batch]
interaction:
  platform-team: x-as-a-service
  observability-enabling: facilitating   # 2026 Q4 까지
contact: "#payments-team, on-call: payments-oncall"
not_owned_but_used: [fraud-model (complicated-subsystem)]
```

## 흔한 오해와 함정

- **"팀 토폴로지 = 플랫폼 팀 만들기."** 플랫폼은 넷 중 하나이고, 스트림 정렬 팀을 돕기 위한 존재다. 플랫폼이 요청 큐가 되면 외재적 부하를 줄이는 게 아니라 대기 시간을 늘린다.
- **역 Conway 기동을 한 번의 조직 개편으로 끝낸다.** Fowler 가 경고했듯 굳은 아키텍처는 팀을 바꿔도 바로 따라오지 않는다. 팀과 코드 경계를 같이 옮긴다.
- **인지 부하를 "업무량" 으로 착각한다.** 일이 많은 것과 알아야 할 것이 많은 것은 다르다. 서비스 수가 적어도 기술 스택이 제각각이면 부하가 크다.
- **협업을 상시 모드로 둔다.** 모든 팀이 모든 팀과 협업하면 경계가 사라지고 결국 Conway 의 법칙대로 결합된 시스템이 나온다.
- **팀을 자주 섞는다.** 공식 사이트는 안정적인 팀이 공유 맥락과 소통 패턴을 쌓아 전달을 크게 가속한다고 강조한다. 사람을 프로젝트에 배치하지 말고 일을 안정된 팀에 보낸다.

## 확인 문제

1. Conway 의 원문 명제를 한 문장으로 쓰고, 역 Conway 기동이 무엇인지 설명하라.
2. 팀 토폴로지의 네 팀 유형 중 기본 단위는 무엇이며, 나머지 셋의 공통 목적은?
3. 외재적 인지 부하의 예를 셋 들고, 어느 팀 유형이 주로 줄이는가?
4. 협업(collaboration) 상호작용을 기간 한정으로 두라고 하는 이유는?
5. 프런트엔드/백엔드/DBA 로 나눈 조직에서 기능 리드 타임이 긴 이유를 Conway 의 법칙으로 설명하라.

### 풀이

1. 시스템을 설계하는 조직은 그 조직의 소통 구조를 복제한 설계를 만들도록 제약된다. 역 Conway 기동은 원하는 아키텍처가 나오도록 팀 구조와 소통 경로를 먼저 설계하는 것이다.
2. 스트림 정렬 팀이 기본이고, 활성화·복잡 하위 시스템·플랫폼 팀은 스트림 정렬 팀의 인지 부하를 줄여 흐름을 빠르게 하는 것이 공통 목적이다.
3. 배포 절차, 개발 환경 설정, 수동 인프라 운영, 권한 신청 절차 등. 주로 플랫폼 팀이 셀프서비스 제품으로 줄인다.
4. 두 팀의 인지 부하가 섞여 비용이 크기 때문이다. 발견이 끝나 경계가 분명해지면 X-as-a-Service 로 옮겨야 각 팀이 자기 영역에 집중한다.
5. 소통 구조가 기술 계층별로 나뉘어 있어 시스템도 계층별로 나뉘고, 사업 기능 하나가 세 팀의 경계를 모두 가로지른다. 모든 기능에 팀 간 인계와 일정 조율이 끼어든다.

## 더 읽을거리 (References)

- Melvin E. Conway, [How Do Committees Invent?](https://www.melconway.com/Home/Committees_Paper.html), Datamation, 1968
- Martin Fowler, [Conway's Law](https://martinfowler.com/bliki/ConwaysLaw.html), 2022
- Team Topologies, [Key Concepts](https://teamtopologies.com/key-concepts)
- Matthew Skelton, Manuel Pais, *Team Topologies: Organizing Business and Technology Teams for Fast Flow*, IT Revolution, 2019 (2판 2025) (서지 정보)
- John Sweller, "Cognitive Load During Problem Solving: Effects on Learning", *Cognitive Science* 12(2), 257–285, 1988, DOI 10.1207/s15516709cog1202_4 (서지 정보)
- John Sweller, Jeroen J. G. van Merriënboer, Fred G. W. C. Paas, "Cognitive Architecture and Instructional Design", *Educational Psychology Review* 10(3), 251–296, 1998, DOI 10.1023/A:1022193728205 (서지 정보)
- [마이크로서비스 vs 모놀리스]({% post_url 2026-10-10-cs300-199-microservices-vs-monolith %}) (CS300 #199), [도메인 주도 설계]({% post_url 2026-10-10-cs300-198-domain-driven-design %}) (CS300 #198)
