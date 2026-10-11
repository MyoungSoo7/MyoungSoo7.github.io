---
layout: post
title: "[SE100 #047] 뮤테이션 테스팅 — 테스트를 테스트하기"
date: 2026-10-11 17:01:46 +0900
categories: [software-engineering]
tags: [se100, software-testing, mutation-testing, pitest, test-adequacy]
---

소프트웨어 공학 100 주제 시리즈의 47번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

뮤테이션 테스팅은 코드에 작은 결함(뮤턴트)을 일부러 심고 테스트를 돌려, 테스트가 그 결함을 **잡아내는지(killed)** 아니면 **놓치는지(survived)** 로 테스트 묶음의 결함 검출력을 잰다. 커버리지가 "실행했는가" 를 묻는다면 뮤테이션은 "실행한 코드가 틀렸을 때 **알아챘는가**" 를 묻는다.

## 왜 필요한가

다음 테스트는 `isEligible` 의 모든 줄과 분기를 실행한다. 커버리지 도구는 100% 라고 보고한다.

```java
boolean isEligible(int age) { return age >= 19; }

@Test void adult() { assertTrue(isEligible(30)); }
@Test void minor() { assertFalse(isEligible(10)); }
```

그런데 누군가 `>=` 를 `>` 로 바꿔도 두 테스트는 그대로 통과한다. 19세 경계를 확인하는 테스트가 없기 때문이다. 커버리지(SE100 #043)는 이 구멍을 보지 못한다. 실행은 했지만 **경계에서 다르게 동작하는 버전과 구별하지 못하는** 테스트이기 때문이다. 뮤테이션 테스팅은 바로 그 "구별하지 못함" 을 기계적으로 찾아낸다.

## 핵심 개념

### 기본 절차

[PIT](https://pitest.org/) 의 설명을 따르면 개념은 단순하다. 결함(뮤테이션)을 코드에 자동으로 심고 테스트를 돌린다. 테스트가 실패하면 뮤테이션은 **죽은(killed)** 것이고, 통과하면 **살아남은(lived/survived)** 것이다. 테스트의 품질은 죽인 뮤테이션의 비율로 가늠한다.

```
 원본 코드 ──(뮤테이션 연산자)──▶ 뮤턴트 1, 2, …, N
                                   │
                    각 뮤턴트에 대해 테스트 실행
                    ┌──────────────┴──────────────┐
               테스트 실패                     테스트 통과
              (killed: 좋음)              (survived: 테스트 구멍 후보)
```

$$\text{mutation score} = \frac{\text{killed}}{\text{전체 뮤턴트} - \text{동등 뮤턴트}}$$

### 이론적 근거: 유능한 프로그래머 가설과 결합 효과

뮤턴트는 연산자 하나, 상수 하나를 바꾼 **단순한** 결함이다. 진짜 버그는 더 복잡한데 왜 이것으로 테스트를 평가할 수 있을까.

DeMillo, Lipton, Sayward 의 [Hints on Test Data Selection: Help for the Practicing Programmer](https://doi.org/10.1109/C-M.1978.218136) (IEEE Computer, 1978) 는 두 가지 근거를 내세웠다.

- **유능한 프로그래머 가설**: 프로그래머는 정답에 가까운 프로그램을 쓰므로, 실제 결함은 정답에서 작은 차이인 경우가 많다.
- **결합 효과(coupling effect)**: 초록의 표현으로, 단순한 오류를 드러내는 테스트는 많은 경우 훨씬 복잡한 오류도 드러낸다.

결합 효과는 Offutt 의 [Investigations of the software testing coupling effect](https://doi.org/10.1145/125489.125473) (ACM TOSEM, 1992) 등에서 실험적으로 검토되었다. 같은 시기 Hamlet 의 [Testing Programs with the Aid of a Compiler](https://doi.org/10.1109/TSE.1977.231145) (IEEE TSE, 1977) 도 컴파일러를 이용해 프로그램 변형으로 테스트를 평가하는 생각을 내놓았다. 분야 전체의 흐름은 Jia 와 Harman 의 서베이 [An Analysis and Survey of the Development of Mutation Testing](https://doi.org/10.1109/TSE.2010.62) (IEEE TSE, 2011) 이 정리한다.

### 뮤턴트는 실제 결함의 대리인이 될 수 있는가

Just 외의 [Are mutants a valid substitute for real faults in software testing?](https://doi.org/10.1145/2635868.2635929) (FSE 2014) 가 이 질문을 직접 다뤘다. 초록에 따르면 5개 오픈소스 애플리케이션(합계 32만 1천 줄)의 실제 결함 357개를 대상으로, 개발자가 쓴 테스트와 자동 생성 테스트를 모두 써서 실험했다. 결과는 뮤턴트 검출과 실제 결함 검출 사이에 **코드 커버리지와 독립적으로** 통계적으로 유의한 상관이 있다는 것이었고, 동시에 뮤테이션 분석의 개선 방향과 내재적 한계도 드러냈다.

### 뮤테이션 연산자

[PIT 뮤테이터 문서](https://pitest.org/quickstart/mutators/) 의 기본 활성 연산자 중 대표적인 것:

| 연산자 | 변환 | 잡아내려는 테스트 구멍 |
|---|---|---|
| CONDITIONALS_BOUNDARY | `<` ↔ `<=`, `>` ↔ `>=` | 경계값 테스트 누락 |
| NEGATE_CONDITIONALS | `==` ↔ `!=`, `<=` ↔ `>` 등 | 분기 결과를 실제로 검증하지 않음 |
| EMPTY_RETURNS, NULL_RETURNS, FALSE_RETURNS 등 | 반환값을 빈 값·null·false 등으로 | 반환값을 단언하지 않음 |
| VOID_METHOD_CALLS | void 메서드 호출을 지움 | 부수효과를 검증하지 않음 |

### 결과 유형과 동등 뮤턴트

PIT 의 [기본 개념 문서](https://pitest.org/quickstart/basic_concepts/) 는 결과를 Killed, Survived, No coverage, Non viable, Timed Out, Memory error, Run error 로 나눈다. No coverage 는 그 줄을 실행하는 테스트조차 없는 Survived 다.

골치 아픈 것은 **동등 뮤턴트(equivalent mutant)** 다. 같은 문서의 예:

```java
int i = 2;
if (i >= 1) { return "foo"; }
// 뮤턴트
int i = 2;
if (i > 1)  { return "foo"; }   // i 가 항상 2 라 동작이 같다 — 어떤 테스트도 죽일 수 없다
```

문서는 또 하나의 유형으로, 동작은 달라지지만 테스트 범위 밖인 경우(로깅·디버그 코드)를 들고, PIT 는 흔한 로깅 프레임워크 호출이 있는 줄에는 뮤테이션을 만들지 않는다고 설명한다. 동등 뮤턴트 판별은 일반적으로 자동화할 수 없어서, 살아남은 뮤턴트는 사람이 하나씩 보고 "테스트 구멍" 인지 "동등" 인지 판정해야 한다. 이것이 뮤테이션 점수 100% 를 목표로 삼으면 안 되는 이유다.

### 비용 문제와 Google 의 접근

뮤턴트 N 개마다 테스트를 다시 돌리므로 비용이 크다. PIT 는 먼저 줄 커버리지를 분석해 **그 뮤턴트를 실행하는 테스트만** 골라 돌리는 방식으로 이전 도구(Jester, Jumble)보다 훨씬 빠르다고 설명한다.

Petrović 와 Ivanković 의 [State of Mutation Testing at Google](https://doi.org/10.1145/3183519.3183521) (ICSE-SEIP 2018) 은 다른 각도로 접근했다. 초록에 따르면 전통적 뮤테이션 분석은 계산 비용이 커서 산업 표준이 되기 어려웠고, 이들은 **변경분(diff) 기반의 확률적** 방식을 제안했다. 문장 커버리지가 없는 줄과, 흥미롭지 않다고 판단되는 줄(**arid lines**)을 언어별 휴리스틱으로 제외해 뮤턴트 수를 크게 줄이고, 결과를 **코드 리뷰** 에 표시한다. 이 시스템은 Google 엔지니어 6,000명이 작성하거나 리뷰하는 모든 변경에 쓰이고, 문장 커버리지가 계산되는 diff 의 약 30% 를 처리한다고 보고했다.

핵심 교훈은 "전체 코드베이스의 뮤테이션 점수" 대신 "**이번 변경에서 살아남은 의미 있는 뮤턴트 몇 개**" 를 사람에게 보여 주는 편이 실무에 맞는다는 것이다.

## 실무 적용

### 1. 도입 순서

| 단계 | 내용 |
|---|---|
| 범위 한정 | 핵심 도메인 패키지 하나부터. 전체에 돌리지 않는다 |
| 증분 실행 | 변경된 클래스·줄만 대상으로(PIT 의 [증분 분석](https://pitest.org/quickstart/incremental_analysis/), diff 기반 도구) |
| 리뷰 연결 | 살아남은 뮤턴트를 PR 코멘트로 — "이 경계가 테스트되지 않았다" |
| 판정 기록 | 동등 뮤턴트로 판정한 것은 제외 목록에 사유와 함께 |
| 게이트 | 절대 점수 대신 "새 코드에서 살아남은 뮤턴트 0개 또는 사유 기재" |

### 2. Maven 에 PIT 붙이기

```xml
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <configuration>
    <targetClasses><param>com.example.billing.*</param></targetClasses>
    <targetTests><param>com.example.billing.*Test</param></targetTests>
  </configuration>
</plugin>
<!-- 실행: mvn test-compile org.pitest:pitest-maven:mutationCoverage -->
```

JavaScript/TypeScript·C#·Scala 는 [Stryker](https://stryker-mutator.io/), Python 은 [mutmut](https://mutmut.readthedocs.io/) 이 같은 역할을 한다.

### 3. 살아남은 뮤턴트 읽는 법

앞의 `isEligible` 에 PIT 를 돌리면 CONDITIONALS_BOUNDARY 뮤턴트(`>=` → `>`)가 살아남는다. 대응은 테스트 추가다.

```java
@Test void boundary() {
    assertTrue(isEligible(19));
    assertFalse(isEligible(18));
}
```

살아남은 뮤턴트는 "어떤 테스트를 추가해야 하는가" 를 구체적으로 알려 준다는 점에서 커버리지 보고서보다 실행 가능한 피드백이다.

## 흔한 오해와 함정

- **뮤테이션 점수를 KPI 로 삼는다.** 동등 뮤턴트 때문에 100% 는 원리적으로 불가능할 수 있고, 수치를 맞추려 의미 없는 단언이 늘어난다.
- **전체 코드베이스에 밤마다 돌린다.** 결과가 너무 많아 아무도 읽지 않는다. 변경분·핵심 모듈로 좁힌다.
- **살아남은 뮤턴트 = 무조건 테스트 추가.** 동등 뮤턴트일 수도, 죽은 코드일 수도 있다. 후자라면 코드를 지우는 것이 답이다.
- **뮤턴트가 실제 결함과 같다고 믿는다.** Just 외(2014)가 보여 준 것은 **상관**이고, 같은 논문이 한계도 함께 보고했다. 누락된 요구사항처럼 코드에 흔적이 없는 결함은 뮤테이션으로 대리할 수 없다.
- **느린 테스트 묶음에 그대로 적용한다.** 뮤테이션 비용은 테스트 실행 시간에 비례해 커진다. 빠른 단위 테스트가 먼저다(SE100 #044).

## 확인 문제

1. 커버리지 100% 인 테스트 묶음에서 뮤턴트가 살아남을 수 있는 이유를 SE100 #041 의 도달·감염·전파·관찰로 설명하라.
2. 결합 효과란 무엇이며, 뮤테이션 테스팅에서 왜 중요한가?
3. 동등 뮤턴트의 예를 하나 들고, 그것이 뮤테이션 점수 해석에 미치는 영향을 설명하라.
4. Google 의 diff 기반 접근이 전통적 뮤테이션 분석과 다른 점 세 가지는?
5. `if (balance - amount < 0) throw …` 에 CONDITIONALS_BOUNDARY 뮤턴트가 살아남았다. 어떤 테스트를 추가하는가?

### 풀이

1. 커버리지는 도달만 보장한다. 뮤턴트가 도달되어 상태를 바꾸더라도(감염) 그 차이가 출력까지 가지 않거나(전파 실패), 출력이 달라져도 테스트가 그 값을 단언하지 않으면(관찰 실패) 테스트는 통과하고 뮤턴트는 살아남는다.
2. 단순한 결함을 잡는 테스트가 많은 경우 더 복잡한 결함도 잡는다는 관찰이다. 이것이 성립해야 연산자 하나를 바꾼 단순 뮤턴트로 실제의 복잡한 결함에 대한 테스트 검출력을 추정할 수 있다.
3. 값이 항상 2 인 `i` 에 대해 `i >= 1` 을 `i > 1` 로 바꾼 뮤턴트. 어떤 테스트로도 죽일 수 없으므로 분모에 남아 있으면 점수를 끌어내린다. 사람이 판정해 분모에서 빼야 하며, 그 판정 비용 때문에 점수 자체를 목표로 삼기 어렵다.
4. 전체 코드가 아니라 변경분(diff)에만 적용한다. 커버리지가 없는 줄과 흥미롭지 않은 줄(arid lines)을 빼고 확률적으로 골라 뮤턴트 수를 줄인다. 결과를 점수가 아니라 코드 리뷰 안의 개별 지적으로 개발자에게 보여 준다.
5. 잔액과 출금액이 정확히 같은 경우(`balance == amount`)를 테스트해, 예외가 나지 않고 잔액이 0 이 되는지 단언한다. 필요하면 1원 차이로 예외가 나는 경우도 함께 둔다.

## 더 읽을거리 (References)

- R. A. DeMillo, R. J. Lipton, F. G. Sayward, [Hints on Test Data Selection: Help for the Practicing Programmer](https://doi.org/10.1109/C-M.1978.218136), IEEE Computer 11(4), 1978
- R. G. Hamlet, [Testing Programs with the Aid of a Compiler](https://doi.org/10.1109/TSE.1977.231145), IEEE TSE SE-3(4), 1977
- A. J. Offutt, [Investigations of the software testing coupling effect](https://doi.org/10.1145/125489.125473), ACM TOSEM 1(1), 1992
- Y. Jia, M. Harman, [An Analysis and Survey of the Development of Mutation Testing](https://doi.org/10.1109/TSE.2010.62), IEEE TSE 37(5), 2011
- R. Just 외, [Are mutants a valid substitute for real faults in software testing?](https://doi.org/10.1145/2635868.2635929), FSE 2014
- G. Petrović, M. Ivanković, [State of Mutation Testing at Google](https://doi.org/10.1145/3183519.3183521), ICSE-SEIP 2018
- PIT, [Basic Concepts](https://pitest.org/quickstart/basic_concepts/), [Mutation Operators](https://pitest.org/quickstart/mutators/)
