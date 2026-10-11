---
layout: post
title: "[SE100 #044] 테스트 피라미드와 테스트 포트폴리오"
date: 2026-10-11 17:01:43 +0900
categories: [software-engineering]
tags: [se100, software-testing, test-pyramid, test-strategy, test-automation]
---

소프트웨어 공학 100 주제 시리즈의 44번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

테스트 피라미드는 "넓고 느리고 깨지기 쉬운 테스트는 적게, 좁고 빠르고 안정적인 테스트는 많이" 라는 **비용 가정**에서 나온 테스트 포트폴리오 모형이다. 핵심은 모양이 아니라 그 밑에 깔린 가정이고, 가정이 깨지는 곳(빠르고 안정적인 통합 테스트가 가능한 곳)에서는 모양도 달라져야 한다.

## 왜 필요한가

테스트를 "많이" 쓰는 것과 "잘 배분해" 쓰는 것은 다르다. 배분이 틀린 팀에서 흔히 보이는 장면은 이렇다.

- CI 가 40분 걸려 개발자들이 푸시 전에 테스트를 안 돌린다.
- 매일 아침 E2E 몇 개가 "원래 가끔 깨지는 것" 이라며 재시도 버튼이 눌린다.
- UI 문구 하나를 바꿨더니 테스트 수십 개가 실패한다.
- 반대로 단위 테스트는 수천 개인데, 서비스 사이 설정 오류로 배포 직후 장애가 난다.

앞의 셋은 넓은 테스트에 너무 기댄 경우, 마지막은 좁은 테스트만 믿은 경우다. 각 층위의 테스트 자체는 [단위 테스트]({% post_url 2026-10-10-cs300-191-unit-testing %}) 와 [통합 테스트와 E2E 테스트]({% post_url 2026-10-10-cs300-192-integration-and-e2e-testing %}) 에서 다뤘다. 여기서는 그것들을 **어떤 비율로, 어떤 근거로** 섞을지를 다룬다.

## 핵심 개념

### 기원

Martin Fowler 의 [TestPyramid](https://martinfowler.com/bliki/TestPyramid.html) (2012) 어원 항목에 따르면, 대부분의 사람들은 Mike Cohn 이 2009년 책 *Succeeding with Agile* 에서 설명한 것으로 이 개념을 안다. 책에서는 "Test Automation Pyramid" 라고 불렀고, Cohn 은 2003–4년 Lisa Crispin 과의 대화에서 처음 그렸으며 2004년 스크럼 모임에서 소개했다. Jason Huggins 도 2006년 무렵 독립적으로 같은 생각에 이르렀다고 적혀 있다.

ISTQB [강의계획서 v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) 5.1.6절은 Cohn 의 원래 모형이 **단위 테스트, 서비스 테스트, UI 테스트** 의 세 층이었고, 층의 수와 이름은 모형마다 다를 수 있다고 정리한다.

```
            ╱╲          느림·비쌈·깨지기 쉬움
           ╱UI╲         ── 적게
          ╱────╲
         ╱서비스╲        API·서비스 계층 경유(피하 테스트)
        ╱────────╲
       ╱   단위    ╲     빠름·쌈·격리 ── 많이
      ╱────────────╲
```

### 피라미드가 기대는 가정

Fowler 는 같은 글에서 UI 를 통과하는 E2E 테스트가 **깨지기 쉽고, 작성 비용이 크고, 실행이 느리다** 고 요약하고, 비결정성 문제에 더 취약해 테스트에 대한 신뢰를 갉아먹는다고 지적한다. 동시에 각주에서 이렇게 못 박는다. 피라미드는 넓은 범위 테스트가 비싸고 느리고 깨지기 쉽다는 **가정**에 기반하며, 상위 테스트가 빠르고 안정적이고 고치기 싸다면 하위 테스트가 필요 없을 수도 있다.

그래서 피라미드를 "단위 70%" 같은 숫자로 외우는 것보다 다음 표로 이해하는 편이 정확하다.

| 축 | 아래(좁음) | 위(넓음) |
|---|---|---|
| 실행 시간 | 밀리초 | 초~분 |
| 격리 | 높음 | 낮음 (외부 의존 다수) |
| 실패 시 원인 위치 | 바로 보임 | 찾아야 함 |
| 비결정성(flaky) | 드묾 | 흔함 |
| 잡는 결함 | 로직 결함 | 연결·설정·배포·통합 결함 |
| 사용자 관점 신뢰 | 낮음 | 높음 |

마지막 두 줄이 위층이 필요한 이유다. 단위 테스트는 컴포넌트 사이 연결이 틀린 것을 잡지 못한다.

Fowler 는 또 상위 테스트를 **두 번째 방어선**으로 본다. 상위 테스트에서 실패가 났다면 기능 코드의 버그와 함께 **빠졌거나 틀린 단위 테스트** 도 있다는 뜻이므로, 고치기 전에 그 버그를 단위 테스트로 먼저 재현하라고 권한다.

### Google 의 시각: 크기와 70/20/10

Google 테스팅 블로그의 [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html) (Simon Stewart, 2010) 는 "단위/통합/E2E" 라는 모호한 이름 대신 테스트가 쓰는 **자원** 으로 크기를 정의했다.

| 항목 | Small | Medium | Large |
|---|---|---|---|
| 네트워크 접근 | 안 됨 | localhost 만 | 됨 |
| 데이터베이스 | 안 됨 | 됨 | 됨 |
| 파일 시스템 | 안 됨 | 됨 | 됨 |
| 외부 시스템 사용 | 안 됨 | 권장 안 함 | 됨 |
| 멀티스레드 | 안 됨 | 됨 | 됨 |
| sleep 문 | 안 됨 | 됨 | 됨 |
| 시간 제한(초) | 60 | 300 | 900+ |

이 분류의 장점은 **기계적으로 강제할 수 있다** 는 것이다. "단위 테스트인가?" 는 논쟁거리지만 "네트워크를 썼는가?" 는 검사할 수 있다.

같은 블로그의 [Just Say No to More End-to-End Tests](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html) (Mike Wacker, 2015) 는 E2E 중심 전략이 겪은 문제(결과가 다음 날에야 나옴, 테스트가 가끔 흔들림, 큰 버그 뒤에 작은 버그가 숨음)를 가상의 사례로 보여 준 뒤, 이상적인 피드백 루프는 **빠르고, 믿을 수 있고, 고장 위치를 좁혀 주는** 것이라고 정리한다. 그리고 "좋은 첫 추정" 으로 Google 이 자주 제안하는 비율이 **단위 70%, 통합 20%, E2E 10%** 이며, 정확한 비율은 팀마다 다르지만 피라미드 모양은 유지해야 한다고 쓴다. 피해야 할 모양으로 **역피라미드(아이스크림 콘)** 와 **모래시계**(단위와 E2E 는 많은데 통합이 빈약함)를 든다.

### 다른 모양들: 트로피와 벌집

Kent C. Dodds 는 2018년 ["Testing Trophy"](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications) 를 제안했다. 2017년 글 ["Write tests. Not too many. Mostly integration."](https://kentcdodds.com/blog/write-tests) 의 연장으로, JavaScript 애플리케이션의 테스트 종류별 **투자 대비 효과** 를 나타낸 그림이다. 그는 피라미드가 소개되던 시절의 주류 언어와 달리 JavaScript 에서는 정적 검사가 당연하지 않아서 **정적(static)** 층을 따로 넣었다고 설명하고, 제목 그대로 통합 테스트에 무게를 둔다.

Fowler 는 2021년 글 [On the Diverse And Fantastical Shapes of Testing](https://martinfowler.com/articles/2021-test-shapes.html) 에서 피라미드 대 벌집·트로피 논쟁의 상당 부분이 **"단위 테스트" 의 정의가 다르기 때문** 이라고 본다. 협력 객체를 진짜로 쓰는 **사교적(sociable)** 단위 테스트와 모두 테스트 더블로 바꾸는 **고립된(solitary)** 단위 테스트(용어는 Jay Fields)를 구분하면, 벌집·트로피 지지자가 비판하는 것은 주로 목(mock)을 과하게 쓰는 고립형 테스트이고, 그들이 말하는 "통합 테스트" 는 피라미드 쪽에서 보면 사교적 단위 테스트와 크게 다르지 않을 때가 많다는 것이다.

## 실무 적용

### 1. 포트폴리오를 크기로 태깅하고 단계별로 돌린다

```java
// JUnit 5: 크기를 태그로 명시 — 크기 정의는 팀 문서에 Small/Medium/Large 표로 둔다
@Tag("medium")
@Testcontainers
class OrderRepositoryTest { /* 실제 PostgreSQL 컨테이너 사용 */ }
```

```yaml
# CI 단계: 빠른 피드백 먼저, 넓은 테스트는 뒤로 (구조만 보인 의사 YAML)
# includeTags 는 build.gradle 의 useJUnitPlatform { includeTags(...) } 에 연결한 프로젝트 속성이라고 가정
jobs:
  small:   { run: "./gradlew test -PincludeTags=small" }          # 커밋마다, 수 분 내
  medium:  { needs: small,  run: "./gradlew test -PincludeTags=medium" }
  large:   { needs: medium, run: "./gradlew e2eTest" }             # 머지 후 / 배포 전
```

### 2. 포트폴리오 점검표

| 질문 | 나쁜 신호 |
|---|---|
| 커밋 후 첫 실패 신호까지 몇 분인가 | 10분 이상 |
| 지난 30일 재시도로 통과한 테스트 수 | 0 이 아님이 방치됨 |
| 운영 장애 중 테스트가 잡았어야 할 것은 어느 층 몫이었나 | 같은 층 누락이 반복 |
| 상위 테스트 실패 시 하위 테스트를 추가했나 | 상위 테스트만 고침 |
| UI 문구 변경에 깨지는 테스트 수 | 두 자릿수 |

### 3. 층을 고르는 규칙

- 비즈니스 규칙 → 가장 좁은 층. UI 가 아니라 도메인 객체에서.
- 직렬화, SQL, 프레임워크 설정 → 실제 의존성을 띄운 Medium(테스트 컨테이너 등).
- 서비스 간 호환성 → 전체 E2E 대신 계약 테스트(SE100 #048).
- 핵심 사용자 여정(로그인, 결제) → 소수의 E2E. "몇 개" 가 아니라 "어떤 여정" 으로 정한다.

## 흔한 오해와 함정

- **70/20/10 을 규정으로 받아들인다.** 원문은 "좋은 첫 추정" 이라고 했고, 팀마다 다르다고 명시했다.
- **피라미드 = 단위 테스트 많이.** 수의 비율보다 **실행 비용과 신뢰의 비율** 이 본질이다. 고립형 단위 테스트 수천 개가 리팩터링마다 깨진다면 그것도 비싼 포트폴리오다.
- **E2E 와 UI 테스트와 고객 관점 테스트를 같은 것으로 본다.** Fowler 는 TestPyramid 글에서 이 셋이 **직교하는** 특성이라고 지적한다. 복잡한 비즈니스 규칙을 고객이 읽을 수 있는 형식으로 쓰되 해당 모듈에만 대고 단위 테스트처럼 돌릴 수 있다.
- **느린 테스트는 무조건 나쁘다.** 느린 테스트는 파이프라인 뒤쪽으로 옮기면 된다. 진짜 문제는 **비결정적인** 테스트다. 신뢰를 잃은 테스트는 아무것도 지키지 못한다.
- **모양 논쟁에서 이기려 한다.** 피라미드·트로피·벌집은 같은 질문(어디에 비용을 쓰면 가장 빨리, 가장 믿을 만한 피드백을 얻는가)에 대한 서로 다른 맥락의 답이다.

## 확인 문제

1. Fowler 가 피라미드의 전제로 명시한 가정은 무엇이며, 그 가정이 깨지면 어떻게 되는가?
2. Google 의 Small/Medium/Large 구분이 "단위/통합/E2E" 보다 운영하기 쉬운 이유는?
3. 모래시계 모양 포트폴리오의 문제는 무엇이고, 무엇으로 보완하는가?
4. 피라미드와 트로피가 실제로는 덜 다를 수 있는 이유를 sociable/solitary 로 설명하라.
5. E2E 테스트에서 결제 버그가 잡혔다. 버그를 고치기 전에 해야 할 일은?

### 풀이

1. 넓은 범위 테스트가 좁은 테스트보다 비싸고 느리고 깨지기 쉽다는 가정이다. 상위 테스트가 빠르고 안정적이고 고치기 싸다면 하위 테스트를 많이 둘 이유가 줄어든다.
2. 크기가 네트워크·DB·파일 시스템·시간 제한 같은 **검사 가능한 자원 사용** 으로 정의되어, 테스트 프레임워크나 CI 에서 기계적으로 강제·분류할 수 있기 때문이다.
3. 단위와 E2E 는 많은데 통합 테스트가 빈약해, 컴포넌트 연결 결함이 느리고 불안정한 E2E 에서야 드러난다. 실제 의존성을 쓰는 통합 테스트(Medium)와 계약 테스트로 중간층을 채운다.
4. 트로피 쪽의 "통합 테스트" 는 협력 객체를 실제로 쓰는 테스트인데, 피라미드 쪽에서는 이것을 사교적 단위 테스트로 부를 수 있다. 결국 논쟁의 상당 부분은 목을 과하게 쓰는 고립형 테스트에 대한 비판이다.
5. 그 버그를 재현하는 하위(단위·통합) 테스트를 먼저 쓴다. 상위 테스트의 실패는 하위 테스트의 누락을 뜻하고, 하위 테스트가 그 버그를 계속 막아 준다.

## 더 읽을거리 (References)

- Martin Fowler, [TestPyramid](https://martinfowler.com/bliki/TestPyramid.html)
- Ham Vocke, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html), martinfowler.com, 2018
- Martin Fowler, [On the Diverse And Fantastical Shapes of Testing](https://martinfowler.com/articles/2021-test-shapes.html), 2021
- Martin Fowler, [UnitTest](https://martinfowler.com/bliki/UnitTest.html)
- Simon Stewart, [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html), Google Testing Blog, 2010
- Mike Wacker, [Just Say No to More End-to-End Tests](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html), Google Testing Blog, 2015
- Kent C. Dodds, [The Testing Trophy and Testing Classifications](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- ISTQB, [Certified Tester Foundation Level Syllabus v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) (PDF), 5.1.6절
- Mike Cohn, *Succeeding with Agile: Software Development Using Scrum*, Addison-Wesley, 2009 (서지 정보)
