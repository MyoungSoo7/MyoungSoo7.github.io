---
layout: post
title: "[SE100 #015] 인수 기준과 BDD — Given-When-Then"
date: 2026-10-11 16:56:29 +0900
categories: [software-engineering]
tags: [se100, requirements, bdd, gherkin, acceptance-criteria]
---

소프트웨어 공학 100 주제 시리즈의 15번째 글이다. (카테고리: 요구사항 공학)

## 한 줄 요약

BDD 는 테스트 도구가 아니라 **예시로 요구를 합의하는 방법**이다. 규칙을 구체적인 예시로 바꾸고(발견), 그 예시를 Given-When-Then 으로 다듬고(정식화), 실행 가능한 명세로 묶어 둔다(자동화). 순서를 거꾸로 하면, 즉 도구부터 깔면 실패한다.

## 왜 필요한가

[요구사항 분석]({% post_url 2026-10-10-cs300-183-requirements-analysis %}) 글에서 인수 기준을 Given-When-Then 으로 적는 형식을 봤다. 형식은 금방 배운다. 그런데 이 형식을 도입한 팀이 흔히 겪는 일이 있다.

- 시나리오가 "로그인 페이지로 이동한다 / 아이디 칸에 입력한다 / 버튼을 누른다" 같은 **클릭 순서**가 되어, UI 가 바뀔 때마다 수십 개가 깨진다.
- QA 가 혼자 시나리오를 쓰고, 기획과 개발은 읽지 않는다. 결국 느린 E2E 테스트 묶음만 남는다.
- 규칙은 하나인데 예시가 서른 개다. 무엇을 확인하는지 아무도 모른다.

이 실패는 BDD 를 **테스트 자동화 기법**으로 이해한 데서 온다. 원전을 보면 BDD 의 출발점은 테스트가 아니라 "말" 의 문제였다.

## 핵심 개념

### 원전: "테스트" 라는 단어의 문제

Dan North 의 [Introducing BDD](https://dannorth.net/blog/introducing-bdd/) 는 2006년 3월 *Better Software* 잡지에 처음 실렸다. 출발은 TDD 를 가르치며 겪은 문제였다. 어디서 시작할지, 무엇을 테스트할지, 테스트 이름을 어떻게 지을지 사람들이 계속 혼란스러워했다.

글이 짚는 전환점은 이렇다.

1. 동료 Chris Stevenson 의 agiledox 라는 도구가 JUnit 테스트 메서드 이름을 문장으로 출력하는 것을 보고, 테스트 이름이 **문장**이어야 한다는 것을 깨달았다.
2. TDD 에 대한 오해가 거의 언제나 **"테스트" 라는 단어**에서 온다고 보고, "행위(behaviour)" 가 더 쓸모 있는 단어라고 결론 내렸다. 2003년 말에는 테스트라는 말을 빼고 행위 검증 어휘로 만든 JUnit 대체물 JBehave 를 쓰기 시작했다.
3. 비즈니스 분석가 Chris Matts 와 함께, 이것을 **분석 과정 자체의 보편 언어**로 넓혔다. 이미 회사에서 쓰던 "As a [X] I want [Y] so that [Z]" 스토리 템플릿 옆에, 인수 기준을 시나리오로 적는 형식을 붙였다.

> Given some initial context (the givens), When an event occurs, Then ensure some outcomes.

즉 Given-When-Then 은 **요구를 말하는 문법**으로 태어났다. 테스트 코드로 실행되는 것은 그 결과다.

### Given-When-Then 은 새로운 것이 아니다

Martin Fowler 는 [GivenWhenThen](https://martinfowler.com/bliki/GivenWhenThen.html) (2013)에서 이 형식이 Dan North(현 Daniel Terhorst-North)와 Chris Matts 가 BDD 의 일부로 개발한 것이라고 쓰고, 기존 테스트 구조와의 대응을 짚는다.

| BDD | Meszaros 의 4단계 테스트 | Wake 의 AAA | 뜻 |
|---|---|---|---|
| Given | Setup | Arrange | 행위 전의 세계 상태 |
| When | Exercise | Act | 명세하려는 그 행위 |
| Then | Verify | Assert | 행위로 인해 기대하는 변화 |
| — | Teardown | — | 정리 |

그러니 [단위 테스트]({% post_url 2026-10-10-cs300-191-unit-testing %})를 AAA 로 쓰는 개발자에게 Given-When-Then 은 낯설지 않다. 차이는 **누가 읽느냐**다. BDD 시나리오는 도메인 전문가가 읽고 "맞다/틀리다" 를 말할 수 있어야 한다.

### 예시에 의한 명세

Fowler 는 2004년 글 [Specification By Example](https://martinfowler.com/bliki/SpecificationByExample.html) 에서 2002년 XP/Agile Universe 워크숍에서 이 문구를 떠올렸다고 쓴다. 추상적인 규칙 대신 **구체적 예시**로 명세하는 것이다. Gojko Adzic 의 책 [*Specification by Example*](https://gojko.net/books/specification-by-example/) (Manning, 2011)은 이 실천을 여러 팀 사례로 정리했다.

규칙과 예시는 이렇게 다르다.

```
규칙:  쿠폰은 최소 주문 금액 이상에서만 적용된다.
예시:  최소 10,000원 쿠폰, 9,999원 주문  → 할인 없음
       최소 10,000원 쿠폰, 10,000원 주문 → 할인 적용
```

규칙만 보면 다들 고개를 끄덕인다. 예시를 들이밀면 "10,000원 '이상' 이었나 '초과' 였나?", "배송비 포함인가?" 같은 질문이 즉시 나온다. **예시가 모호함을 드러낸다.**

### 세 가지 실천: 발견, 정식화, 자동화

Cucumber 프로젝트의 [BDD 문서](https://cucumber.io/docs/bdd/)는 BDD 를 세 실천의 반복으로 설명한다.

| 실천 | 하는 일 | 누가 | 산출물 |
|---|---|---|---|
| 발견(Discovery) | 구체적 예시로 규칙과 모르는 것을 찾는다 | 기획·개발·테스트(흔히 "세 친구") | 규칙, 예시, 질문 |
| 정식화(Formulation) | 예시를 Gherkin 시나리오로 다듬는다 | 개발·테스트, 도메인 전문가 검토 | `.feature` 파일 |
| 자동화(Automation) | 시나리오를 실행 가능한 테스트로 연결 | 개발 | 스텝 정의, CI |

**발견이 빠진 BDD** 가 앞에서 본 실패의 공통 원인이다.

### 발견 도구: 예시 매핑

Matt Wynne 의 [Example Mapping](https://cucumber.io/blog/bdd/example-mapping-introduction/) (2015)은 발견 단계를 위한 짧은 회의 기법이다. 네 가지 색 카드를 쓴다.

```
[노랑] 스토리: 쿠폰으로 할인받는다
   ├─[파랑] 규칙: 최소 주문 금액 이상에서만
   │     ├─[초록] 9,999원 → 할인 없음
   │     └─[초록] 10,000원 → 할인
   ├─[파랑] 규칙: 할인 후 0원 미만 불가
   │     └─[초록] 4,000원 주문, 5,000원 쿠폰 → 0원
   └─[빨강] 질문: 쿠폰 두 장 중복 적용 가능한가?
```

Wynne 은 적당한 크기의 스토리라면 작은 팀이 **약 25분** 안에 매핑할 수 있다고 하고, 결과를 이렇게 읽으라고 한다. 빨간 카드가 많으면 아직 모르는 게 많으니 개발을 시작하기 이르다. 파란 카드가 많으면 스토리가 너무 크니 잘라야 한다(SE100 #014). 한 규칙에 예시가 지나치게 많으면 규칙 여러 개가 섞여 있다.

### Gherkin 의 구조

[Gherkin 레퍼런스](https://cucumber.io/docs/gherkin/reference/)의 주요 키워드는 `Feature`, `Rule`(Gherkin 6부터), `Example`/`Scenario`, `Given`/`When`/`Then`/`And`/`But`, `Background`, `Scenario Outline`, `Examples` 다. 문서는 각 스텝을 이렇게 설명한다.

- **Given**: 사용자(또는 외부 시스템)가 상호작용을 시작하기 전에 시스템을 알려진 상태로 둔다.
- **When**: 사건 또는 행동.
- **Then**: 실제 결과를 기대 결과와 비교하는 단언. 결과는 **관찰 가능한 출력**이어야 한다(데이터베이스 내부 상태가 아니라).

Gherkin 은 70개가 넘는 언어로 번역돼 있고, 파일 첫 줄의 `# language:` 헤더로 언어를 정한다. 공식 키워드 표([gherkin-languages.json](https://raw.githubusercontent.com/cucumber/gherkin/main/gherkin-languages.json))의 한국어는 `기능`, `규칙`, `배경`, `시나리오`, `시나리오 개요`, `예`, `조건`/`먼저`, `만일`/`만약`, `그러면`, `그리고`, `하지만`/`단` 이다.

## 예제

예시 매핑 결과를 정식화한 시나리오다. `Rule` 로 규칙별로 묶어, 파란 카드와 초록 카드의 구조를 그대로 옮겼다.

```gherkin
# language: ko
기능: 주문 쿠폰 적용
  단골 고객이 쿠폰으로 할인받되, 매장이 손해 보는 주문은 막는다.

  Rule: 쿠폰은 최소 주문 금액 이상에서만 적용된다

    시나리오 개요: 최소 주문 금액 경계
      조건 최소 주문 금액이 10000원인 3000원 할인 쿠폰이 있다
      만일 고객이 <금액>원어치를 주문하고 쿠폰을 적용한다
      그러면 결제 금액은 <결제>원이다

      예:
        | 금액  | 결제  |
        | 9999  | 9999  |
        | 10000 | 7000  |
        | 15000 | 12000 |

  Rule: 할인 후 금액은 0원 아래로 내려가지 않는다

    시나리오: 쿠폰 할인액이 주문 금액보다 크다
      조건 최소 주문 금액이 0원인 5000원 할인 쿠폰이 있다
      만일 고객이 4000원어치를 주문하고 쿠폰을 적용한다
      그러면 결제 금액은 0원이다
```

Python 의 [behave](https://behave.readthedocs.io/en/latest/) 로 스텝을 연결한다.

```python
# features/steps/coupon_steps.py
from behave import given, when, then

def apply_coupon(total, minimum, discount):   # 실제로는 도메인 코드를 호출
    if total < minimum:
        return total
    return max(total - discount, 0)

@given("최소 주문 금액이 {minimum:d}원인 {discount:d}원 할인 쿠폰이 있다")
def step_coupon(context, minimum, discount):
    context.coupon = (minimum, discount)

@when("고객이 {total:d}원어치를 주문하고 쿠폰을 적용한다")
def step_order(context, total):
    context.paid = apply_coupon(total, *context.coupon)

@then("결제 금액은 {expected:d}원이다")
def step_paid(context, expected):
    assert context.paid == expected, f"{context.paid} != {expected}"
```

behave 1.3.3 으로 실행한 결과:

```
1 feature passed, 0 failed, 0 skipped
2 rules passed, 0 failed, 0 skipped
4 scenarios passed, 0 failed, 0 skipped
12 steps passed, 0 failed, 0 skipped
```

여기서 실제로 부딪힌 함정 하나: Cucumber 공식 표의 한국어 `규칙` 키워드를 쓰면 behave 1.3.3 은 파싱에 실패한다. behave 가 자체적으로 들고 있는 한국어 키워드 표에서는 rule 이 `Rule` 로 되어 있기 때문이다. 그래서 위 예제는 `Rule:` 을 썼다. **도구마다 키워드 표가 다를 수 있으니** 팀 도구로 한 번 돌려 보고 정한다.

주목할 점은 시나리오에 화면, 버튼, URL 이 하나도 없다는 것이다. 같은 시나리오를 API 테스트로도, 도메인 단위 테스트로도 연결할 수 있다. 이게 **선언적** 시나리오의 힘이다.

## 흔한 오해와 함정

- **"BDD = Cucumber."** 도구는 자동화 단계의 선택지일 뿐이다. 발견 대화 없이 `.feature` 파일만 늘리면, 읽는 사람이 개발자뿐인 장황한 테스트가 된다.
- **명령형 시나리오.** "아이디 칸에 입력한다, 버튼을 누른다" 식의 스텝은 UI 변경에 취약하고 규칙을 가린다. 시나리오는 **무엇**을, 스텝 정의가 **어떻게**를 맡는다.
- **긴 Background.** Gherkin 레퍼런스는 Background 를 짧게 유지하고, 4줄을 넘으면 세부를 상위 수준 스텝으로 옮기라고 권한다.
- **Then 에서 내부 상태를 확인한다.** "DB 의 coupon_used 컬럼이 1이다" 는 사용자가 관찰할 수 없다. 관찰 가능한 결과(결제 금액, 받은 알림)로 쓴다.
- **모든 시나리오를 E2E 로 돌린다.** 시나리오는 명세다. 실행 수준은 테스트 피라미드에 맞게 고른다([통합·E2E 테스트]({% post_url 2026-10-10-cs300-192-integration-and-e2e-testing %})).
- **경계 예시가 없다.** 9,999 와 10,000 같은 경계 예시가 빠지면 "이상/초과" 모호함은 그대로 남는다.

## 확인 문제

1. Dan North 가 "테스트" 대신 "행위" 라는 단어를 택한 이유는?
2. Given-When-Then 과 AAA(Arrange-Act-Assert)의 대응 관계를 쓰고, 둘의 차이를 한 문장으로 말하라.
3. 예시 매핑에서 빨간 카드가 많을 때와 파란 카드가 많을 때 각각 어떻게 판단하는가?
4. 다음 스텝을 선언적으로 고쳐라: "Given 사용자가 /login 에 접속해 id 칸에 kim 을 입력하고 로그인 버튼을 누른다"
5. Gherkin `Rule` 키워드는 언제부터 있었고, 무엇을 묶는가?

### 풀이

1. TDD 에 대한 오해가 거의 늘 "테스트" 라는 말에서 왔기 때문이다. 행위로 생각하면 무엇부터 할지, 무엇을 확인할지, 이름을 어떻게 지을지가 자연스럽게 정해진다.
2. Given↔Arrange, When↔Act, Then↔Assert. 구조는 같지만 BDD 시나리오는 도메인 전문가가 읽고 판정할 수 있는 언어로 쓴다.
3. 빨강이 많으면 미지수가 많으니 개발 시작을 미루고 질문부터 해결한다. 파랑이 많으면 스토리가 크니 규칙 단위로 자른다.
4. "Given 김 고객이 로그인해 있다". 로그인 방법은 스텝 정의가 맡는다.
5. Gherkin 6 부터. 하나의 비즈니스 규칙과 그 규칙을 보여 주는 시나리오들을 묶는다.

## 더 읽을거리 (References)

- Dan North, [Introducing BDD](https://dannorth.net/blog/introducing-bdd/), *Better Software*, 2006
- Martin Fowler, [GivenWhenThen](https://martinfowler.com/bliki/GivenWhenThen.html), [SpecificationByExample](https://martinfowler.com/bliki/SpecificationByExample.html)
- Gojko Adzic, [*Specification by Example*](https://gojko.net/books/specification-by-example/), Manning, 2011
- Cucumber, [Behaviour-Driven Development](https://cucumber.io/docs/bdd/), [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/), [gherkin-languages.json](https://raw.githubusercontent.com/cucumber/gherkin/main/gherkin-languages.json)
- Matt Wynne, [Introducing Example Mapping](https://cucumber.io/blog/bdd/example-mapping-introduction/), 2015
- [behave 문서](https://behave.readthedocs.io/en/latest/)
- CS300: [테스트 주도 개발]({% post_url 2026-10-10-cs300-193-test-driven-development %})
