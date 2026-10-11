---
layout: post
title: "[SE100 #046] 속성 기반 테스트"
date: 2026-10-11 17:01:45 +0900
categories: [software-engineering]
tags: [se100, software-testing, property-based-testing, quickcheck, hypothesis]
---

소프트웨어 공학 100 주제 시리즈의 46번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

예제 기반 테스트가 "입력 3 이면 출력 6" 을 적는다면, **속성 기반 테스트(PBT)** 는 "모든 입력에 대해 이 관계가 성립한다" 를 적고 도구가 입력을 생성해 그 관계를 **반박**하려 든다. 반례를 찾으면 그것을 가장 단순한 형태로 **축소(shrink)** 해서 보여 준다. 사람이 하는 일은 입력을 고르는 것에서 **불변 관계를 찾는 것** 으로 바뀐다.

## 왜 필요한가

예제 기반 테스트의 입력은 작성자의 상상력 안에 있다. 경계값 분석(SE100 #042)을 잘해도 작성자가 떠올리지 못한 분할은 테스트되지 않는다. 특히 다음 같은 입력은 사람이 잘 떠올리지 못한다.

- 부동소수점의 극단값, 오버플로, 반올림
- 빈 문자열과 유니코드 결합 문자, 서로게이트 쌍
- 같은 원소가 아주 길게 반복되는 목록
- 특정 순서로만 문제를 일으키는 연산 시퀀스

PBT 는 이 공간을 기계가 대신 탐색하게 한다. 대신 "기대 출력" 을 일일이 적을 수 없으므로, 출력이 만족해야 할 **속성** 을 적어야 한다.

## 핵심 개념

### QuickCheck 에서 시작

Claessen 과 Hughes 의 [QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs](https://doi.org/10.1145/351240.351266) (ICFP 2000) 가 출발점이다. 초록에 따르면 QuickCheck 은 프로그래머가 프로그램의 속성을 정식화하고 테스트하도록 돕는 도구이고, 속성은 Haskell 함수로 기술되며 무작위 입력으로 자동 테스트되고, 사용자 정의 테스트 데이터 생성기도 만들 수 있다. 논문은 함수형 프로그램에서는 속성을 잘게 기술할 수 있어 무작위 테스트가 특히 잘 맞는다고 주장한다.

Python 의 Hypothesis 를 다룬 [JOSS 논문](https://doi.org/10.21105/joss.01891) (MacIver, Hatfield-Dodds 외, 2019) 은 PBT 를 이렇게 요약한다. 단일한 구체 동작의 예를 드는 대신, 넓은 입력 범위에서 성립하는 속성을 명세하고, 라이브러리가 그 속성을 **반박하는** 테스트 케이스를 생성하려 시도하는 테스트 방식이다. QuickCheck 계열이 Haskell 에서 먼저, 이어 Erlang 에서 대중화했다.

Hypothesis 저자 David MacIver 는 [What is Property Based Testing?](https://hypothesis.works/articles/what-is-property-based-testing/) (2016) 에서 정의를 한 번 더 다듬는다. PBT 는 테스트를 퍼징했을 때 그 실패가, 시스템을 직접 퍼징해서는 드러나지 않았을 문제를 드러내도록 **테스트를 구성하는 일** 이다. 컴퓨터가 하는 부분은 "그냥 퍼징" 이고, PBT 는 사람이 하는 일이라는 관점이다.

### 구성 요소

| 요소 | 역할 | Hypothesis | jqwik (JVM) |
|---|---|---|---|
| 생성기 | 입력 공간과 분포를 정의 | `strategies` (`st.integers()` 등) | `Arbitrary`, `@ForAll` |
| 속성 | 모든 입력에 성립해야 할 단언 | `@given` 을 단 테스트 함수 | `@Property` 메서드 |
| 실행 횟수 | 시도할 입력 수 | `max_examples`, 기본 100 | `tries`, 리포트상 기본 1000 |
| 축소 | 반례를 최소화 | 실패 시 자동 | 통합 축소(integrated shrinking) |
| 재현 | 찾은 반례를 다시 실행 | 예제 데이터베이스, `@example` | 이전 시드 재사용(`after-failure`) |

Hypothesis 의 기본 실행 횟수 100 은 [설정 문서](https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html) 의 예제(`max_examples=200` 으로 "100 대신 200번")에서, jqwik 의 1000 은 [사용자 가이드](https://jqwik.net/docs/current/user-guide.html) 의 실행 리포트(`tries = 1000`)에서 확인할 수 있다. [API 문서](https://hypothesis.readthedocs.io/en/latest/reference/api.html) 는 반례를 "최소 실패 테스트 케이스(minimal failing test case)" 로 보고하며, `@example` 로 넣은 명시적 예제는 축소되지 않는다고 적는다.

### 축소가 핵심인 이유

무작위로 찾은 반례는 대개 크고 지저분하다. 길이 47 짜리 리스트에 음수와 거대한 수가 섞여 있으면 원인을 추론하기 어렵다. 축소기는 "실패를 유지하면서 더 작게" 를 반복해 원인만 남긴다. 아래 예제에서 Hypothesis 가 돌려준 반례 `'aaaaaaaaaa'` (정확히 10글자)는 축소가 없었다면 수십 글자짜리 무작위 문자열이었을 것이다.

### 속성을 찾는 패턴

"기대 출력을 모르는데 무엇을 단언하나" 가 PBT 의 진입 장벽이다. 자주 쓰는 패턴은 다음과 같다.

| 패턴 | 형태 | 예 |
|---|---|---|
| 왕복(round-trip) | `decode(encode(x)) == x` | 직렬화, 압축, 파서/프린터 |
| 불변식 | 출력이 항상 만족하는 조건 | 정렬 결과는 비내림차순이고 원소 다중집합이 같다 |
| 모델(오라클) 비교 | 단순하지만 느린 구현과 결과 비교 | 최적화된 자료구조 vs 리스트 |
| 메타모픽 관계 | 입력 변환과 출력 변환의 관계 | `sort(xs + ys)` 와 `sort(ys + xs)` 가 같다 |
| 멱등성 | `f(f(x)) == f(x)` | 정규화, 중복 제거, 포매터 |
| 예외 부재 | 어떤 입력에도 정의된 예외만 | 파서가 임의 바이트에 크래시하지 않는다 |

메타모픽 관계는 테스트 오라클 문제를 다룰 때 다시 나온다(SE100 #050).

## 예제

### 1. 평균은 최솟값과 최댓값 사이에 있다

```python
from hypothesis import given, strategies as st

def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)

@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1))
def test_mean_is_between_min_and_max(xs):
    assert min(xs) <= mean(xs) <= max(xs)
```

당연해 보이는 속성인데, 이 글을 쓰며 실제로 실행해 보니 실행마다 다음 같은 반례가 나왔다.

```
xs=[8.988465674311579e+307, 8.98846567431158e+307]   # 합이 오버플로해 inf
xs=[3002399751580331.0, 3002399751580331.0, 3002399751580331.0]  # 반올림으로 평균 > 최댓값
```

첫째는 오버플로, 둘째는 부동소수점 반올림이다. 둘 다 예제 기반 테스트 작성자가 좀처럼 넣지 않는 입력이다. 대응은 `math.fsum` 이나 단계별 평균 같은 수치적으로 안정된 구현, 또는 명세에 입력 범위를 명시하는 것이다.

### 2. 생성기의 분포가 결과를 좌우한다

연속 반복을 (문자, 개수) 쌍으로 압축하는 RLE 인코더에 "9개를 넘으면 쌍을 끊는" 결함을 심었다. 속성은 "인접한 쌍의 문자는 서로 달라야 한다" 이다.

```python
@given(st.text())                                   # 1) 아무 문자열
def test_no_adjacent_same_char(s): ...

runs = st.lists(st.tuples(st.sampled_from("ab"), st.integers(1, 20))).map(
    lambda rs: "".join(c * n for c, n in rs))       # 2) 반복을 직접 만드는 생성기

@given(runs)
def test_no_adjacent_with_runs(s): ...
```

1) 은 다섯 번 돌려 다섯 번 모두 **통과** 했다. 임의 문자열에서 같은 글자가 10번 연속 나오는 경우가 드물기 때문이다. 2) 는 매번 실패했고 반례는 `s='aaaaaaaaaa'` 로 축소되었다. PBT 는 "무작위면 다 찾는다" 가 아니다. **결함이 사는 곳으로 분포를 기울이는** 생성기 설계가 실력이다.

### 3. JVM: jqwik

jqwik [사용자 가이드](https://jqwik.net/docs/current/user-guide.html) 는 "실패가 놀라울 수 있는" 속성으로 다음을 든다.

```java
@Property
boolean absoluteValueOfAllNumbersIsPositive(@ForAll int anInteger) {
    return Math.abs(anInteger) >= 0;
}
```

`Integer.MIN_VALUE` 의 절댓값은 `int` 범위를 넘어 음수 그대로 나온다. 생성기가 경계값을 우선 섞는 덕에 이런 반례가 빨리 나온다(가이드의 리포트에 `edge-cases#mode = MIXIN` 으로 표시된다).

## 흔한 오해와 함정

- **구현을 그대로 다시 적은 속성.** `assert price(x) == x * 1.1` 처럼 구현 공식을 복사하면 구현과 같은 실수를 같이 한다. 속성은 구현과 **다른 각도** 의 관계여야 한다.
- **필터로 입력을 깎는다.** `assume(...)` 이나 `.filter()` 로 대부분의 입력을 버리면 생성이 비효율적이 되고 도구가 경고하거나 포기한다. 처음부터 유효한 입력만 만드는 생성기를 짠다.
- **반례를 고치고 끝낸다.** 찾은 반례는 `@example(...)` 이나 일반 단위 테스트로 고정해 회귀 테스트로 남긴다.
- **CI 에서 비결정적이라 싫다.** Hypothesis 는 실패 예제를 데이터베이스에 저장해 재생하고, `derandomize` 설정으로 결정적으로 돌릴 수도 있다([설정 문서](https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html)). 비결정성은 관리할 수 있는 문제다.
- **PBT 가 예제 테스트를 대체한다.** 예제 테스트는 "이 입력에 이 출력" 이라는 문서 역할을 한다. 둘은 보완 관계다.

## 확인 문제

1. 예제 기반 테스트와 속성 기반 테스트에서 사람이 하는 일은 각각 무엇인가?
2. 축소(shrinking)가 없으면 PBT 의 실무 가치가 크게 떨어지는 이유는?
3. 위 RLE 예에서 `st.text()` 생성기가 결함을 찾지 못한 이유와 해결책은?
4. JSON 직렬화 라이브러리에 쓸 수 있는 속성 두 가지를 패턴 이름과 함께 제시하라.
5. `assert discount(p) == p * 0.9` 가 좋은 속성이 아닌 이유는? 대신 어떤 속성을 쓸 수 있는가?

### 풀이

1. 예제 기반에서는 사람이 구체 입력과 기대 출력을 고른다. 속성 기반에서는 사람이 모든 입력에 성립할 관계(속성)와 입력 생성기를 설계하고, 입력 선택은 도구가 한다.
2. 무작위로 찾은 반례는 크고 잡음이 많아 원인 추론이 어렵다. 축소는 실패를 유지한 채 가장 작은 입력을 남겨 원인을 바로 드러낸다.
3. 임의 문자열에서 같은 문자가 10번 연속 나올 확률이 낮아 기본 실행 횟수 안에 결함 입력이 생성되지 않았다. 반복 길이를 직접 생성하는 생성기로 분포를 결함 쪽으로 기울이면 찾는다.
4. 왕복: `loads(dumps(x)) == x`. 예외 부재: 임의 문자열을 `loads` 에 넣어도 정의된 파싱 예외 외의 예외가 나지 않는다. (멱등성: `dumps(loads(dumps(x))) == dumps(x)` 도 가능)
5. 구현 공식을 그대로 옮겨 구현과 같은 실수를 공유한다. 대신 "할인가는 0 이상 원가 이하", "원가가 크면 할인가도 작지 않다(단조성)", "할인을 두 번 적용하지 않도록 멱등" 같은 관계를 쓴다.

## 더 읽을거리 (References)

- K. Claessen, J. Hughes, [QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs](https://doi.org/10.1145/351240.351266), ICFP 2000
- D. R. MacIver, Z. Hatfield-Dodds 외, [Hypothesis: A new approach to property-based testing](https://doi.org/10.21105/joss.01891), Journal of Open Source Software 4(43), 2019
- David R. MacIver, [What is Property Based Testing?](https://hypothesis.works/articles/what-is-property-based-testing/), 2016
- Hypothesis 문서, [Introduction](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html), [Settings](https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html), [API Reference](https://hypothesis.readthedocs.io/en/latest/reference/api.html)
- jqwik, [User Guide](https://jqwik.net/docs/current/user-guide.html)
- J. Hughes, [Experiences with QuickCheck: Testing the Hard Stuff and Staying Sane](https://doi.org/10.1007/978-3-319-30936-1_9), 2016
- J. Hughes, [How to Specify It!](https://doi.org/10.1007/978-3-030-47147-7_4), Trends in Functional Programming, 2020
