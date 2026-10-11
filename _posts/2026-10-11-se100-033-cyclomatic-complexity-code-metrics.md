---
layout: post
title: "[SE100 #033] 순환 복잡도와 코드 메트릭"
date: 2026-10-11 16:59:57 +0900
categories: [software-engineering]
tags: [se100, code-quality, cyclomatic-complexity, cognitive-complexity, software-metrics]
---

소프트웨어 공학 100 주제 시리즈의 33번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

순환 복잡도는 함수 안의 **독립 경로 수**이자 기초 경로 테스트에 필요한 최소 경로 수다. 테스트 설계에는 정확한 도구지만 "읽기 어려움" 의 척도로는 한계가 있고, 어떤 메트릭이든 목표가 되는 순간 왜곡된다. 메트릭은 판정이 아니라 **어디를 볼지** 정하는 데 쓴다.

## 왜 필요한가

"이 함수 너무 복잡해요" 는 리뷰에서 자주 나오지만 반박도 쉽다. 숫자가 있으면 대화가 구체적이 된다. 수천 개 파일 중 어디부터 리팩터링할지 고를 때도 사람이 다 읽을 수는 없다.

그런데 숫자는 양날의 칼이다. "복잡도 10 초과 금지" 를 CI 에 걸면 개발자는 함수를 의미 없이 쪼개 숫자만 맞춘다. 어떤 메트릭이 무엇을 재고 무엇을 못 재는지 알아야 이 함정을 피한다.

## 핵심 개념

### McCabe 의 정의 (1976)

Thomas McCabe 는 IEEE TSE 에 실린 [A Complexity Measure](https://doi.org/10.1109/TSE.1976.233837)(1976)에서 프로그램의 제어 흐름 그래프로 복잡도를 정의했다. NIST 가 펴낸 Watson·McCabe 의 [Structured Testing](https://www.nist.gov/publications/structured-testing-software-testing-methodology-using-cyclomatic-complexity-metric)(NIST SP 500-235, 1996, [PDF](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf))은 이를 실무용으로 정리한 문서다.

모듈 하나에 대해, 간선 수를 $$e$$, 노드 수를 $$n$$ 이라 하면

$$v(G) = e - n + 2$$

이다. 모든 결정이 이진이고 이진 결정 술어가 $$p$$ 개라면 더 간단히

$$v(G) = p + 1$$

로 셀 수 있다. 소스 코드에서 세는 규칙은 이렇다(NIST 4장).

| 구문 | 기여 |
|---|---|
| `if`, `while`, `for` 같은 이진 결정 | +1 |
| 단락 평가 불리언 연산자(C 의 `&&`, Ada 의 `and then`) | +1 (조건부 실행을 만들기 때문) |
| 완전 평가 연산자(Ada 의 `and`) | 0 |
| k 갈래 다중 분기(`switch`) | +(k−1) |

### 테스트와의 관계: 기초 경로

v(G) 는 제어 흐름 그래프에서 **선형 독립인 경로의 수**다. NIST 의 구조적 테스트(structured testing, 기초 경로 테스트) 기준은 이 개수만큼의 독립 경로, 즉 기초 집합(basis set)을 테스트하라는 것이다. 그래서 v(G) 는 "이 함수를 제대로 덮으려면 테스트가 최소 몇 개 필요한가" 의 하한으로 읽을 수 있다. 분기 커버리지 100% 보다 강한 기준이다.

```
  shipping_fee(order)          v(G) = 4 → 독립 경로 4개
  ┌─────────────┐
  │ total≥50000 │──예──▶ return 0                (경로 1)
  └──────┬──────┘
         아니오
  ┌──────┴──────┐
  │ jeju?       │──예──▶ return 6000             (경로 2)
  └──────┬──────┘
         아니오
  ┌──────┴──────┐
  │ island?     │──예──▶ return 6000             (경로 3: 'or' 의 두 번째 항)
  └──────┬──────┘
         아니오 ──────▶ return 3000              (경로 4)
```

### 임계값 10 의 출처

NIST SP 500-235 2.5절은 "McCabe 가 제안한 원래 한계 10 은 상당한 근거가 있지만, 15 까지도 성공적으로 쓰인 사례가 있다" 고 쓴다. 다만 10 을 넘기는 것은 숙련된 인력, 형식적 설계, 코드 워크스루, 포괄적 테스트 계획 같은 **운영상 이점이 있는 프로젝트**에 한정하라고 덧붙인다. 같은 절은 정확한 숫자보다 **예외 처리 방식**이 더 흥미롭다며, McCabe 가 원래 단일 다중 분기(`switch`)만으로 된 모듈은 한계에서 면제하자고 권했다는 점도 적는다.

도구의 기본값도 이 전통을 따른다. Checkstyle 의 [CyclomaticComplexity](https://checkstyle.sourceforge.io/checks/metrics/cyclomaticcomplexity.html) 검사는 `max` 기본값이 10 이고 `switchBlockAsSingleDecisionPoint` 옵션으로 switch 를 결정 하나로 볼 수 있다. Python 의 [mccabe](https://github.com/PyCQA/mccabe) 플러그인은 기본으로 꺼져 있어 `--max-complexity` 를 직접 줘야 하고, [Radon](https://radon.readthedocs.io/en/latest/api.html)은 1–5 를 A(낮은 위험), 6–10 을 B, 11–20 을 C … 41 이상을 F 로 등급을 매긴다.

### 비판: 길이의 대리 변수인가

Martin Shepperd 는 [A critique of cyclomatic complexity as a software metric](https://doi.org/10.1049/sej.1988.0003)(Software Engineering Journal, 1988)에서 이 메트릭이 이론적 기반이 약하고, "유용한 공학적 근사" 라는 주장이 실증적으로 뒷받침되지 않으며, 많은 소프트웨어에서 **코드 줄 수(LOC)의 대리 변수에 불과하고 종종 LOC 보다 못하다**고 비판했다. 복잡도와 길이는 함께 커지므로, 복잡도가 결함을 "예측한다" 는 상관관계 중 상당 부분은 길이 효과일 수 있다는 지적이다.

### 인지 복잡도: 읽기 어려움을 재려는 시도

SonarSource 의 G. Ann Campbell 은 [Cognitive Complexity](https://www.sonarsource.com/docs/CognitiveComplexity.pdf) 백서(버전 1.7, 2023)와 TechDebt 2018 논문([DOI](https://doi.org/10.1145/3194164.3194186))에서 다른 규칙을 제안했다(벤더가 만든 메트릭이다). 세 가지 기본 규칙은

1. 여러 문장을 읽기 쉽게 하나로 줄이는 구조(축약)는 무시한다.
2. 선형 흐름이 끊길 때마다 +1.
3. 흐름을 끊는 구조가 **중첩될 때** 추가로 가산한다.

이다. 또 `switch` 전체는 한 번만 세고, `a && b && c` 처럼 같은 연산자의 연속은 한 번만, 연산자가 섞일 때마다 추가로 센다. 백서의 대표 예시는 순환 복잡도가 똑같이 4 인 두 메서드다. 중첩 루프에 `continue OUT` 이 들어간 `sumOfPrimes` 는 인지 복잡도 7, 평평한 `switch` 하나인 `getWords` 는 1 이다. 사람이 느끼는 차이를 순환 복잡도는 못 잡고 인지 복잡도는 잡는다.

| | 순환 복잡도 | 인지 복잡도 |
|---|---|---|
| 재는 것 | 독립 경로 수 | 읽는 사람의 정신적 부담(추정) |
| 중첩 | 무관 | 깊을수록 가중 |
| switch | 갈래 수만큼 | 전체 한 번 |
| 좋은 용도 | 테스트 개수 하한, 경로 설계 | 리팩터링 후보, 리뷰 신호 |

### 그 밖의 메트릭

- **크기**: LOC, 함수 길이. 거칠지만 Shepperd 의 지적처럼 생각보다 강한 기준선이다.
- **객체지향 설계**: Chidamber·Kemerer 의 [A Metrics Suite for Object Oriented Design](https://doi.org/10.1109/32.295895)(IEEE TSE, 1994)가 제안한 WMC, DIT, NOC, CBO, RFC, LCOM.
- **변경 이력**: 파일별 변경 빈도(churn). 복잡도와 곱하면 "자주 바뀌는데 복잡한 곳", 즉 핫스팟이 나온다(Adam Tornhill, *Your Code as a Crime Scene*, Pragmatic Bookshelf, 2015 참고).

## 실무 적용

### 직접 세어 보기

Python `ast` 로 v(G) 를 세는 최소 구현이다. 단락 평가 `and`/`or` 를 하나씩 세고, k 갈래 `match` 는 k−1 로 센다.

```python
import ast

DECISIONS = (ast.If, ast.For, ast.While, ast.IfExp, ast.ExceptHandler, ast.Assert)

def cyclomatic(func: ast.FunctionDef) -> int:
    v = 1
    for node in ast.walk(func):
        if isinstance(node, DECISIONS):
            v += 1
        elif isinstance(node, ast.BoolOp):          # a and b and c → 2
            v += len(node.values) - 1
        elif isinstance(node, ast.comprehension):   # for ... if ...
            v += 1 + len(node.ifs)
        elif isinstance(node, ast.Match):           # k 갈래 분기 → k-1
            v += len(node.cases) - 1
    return v
```

배송비 함수, 중첩 루프로 소수를 더하는 함수, 네 갈래 `match` 함수에 돌린 결과(Python 3.12):

```
shipping_fee    v(G) = 4
sum_of_primes   v(G) = 4
word            v(G) = 4
```

세 함수 모두 4 다. 하지만 중첩 루프 안에 조건과 `break` 가 있는 `sum_of_primes` 가 평평한 `match` 보다 읽기 어렵다는 데는 대부분 동의할 것이다. 이것이 순환 복잡도가 "테스트 경로 수" 로는 정확하지만 "가독성" 으로는 부족한 이유다.

### 핫스팟 뽑기

```bash
# 최근 1년 파일별 변경 횟수 상위 20 (churn)
git log --since=1.year --name-only --format= -- '*.py' \
  | sort | uniq -c | sort -rn | head -20
```

이 목록과 복잡도 상위 목록이 **겹치는** 파일이 첫 리팩터링 대상이다. 복잡하지만 1년간 아무도 안 고친 파일은 뒤로 미룬다.

### 운영 정책 예

- 새로 추가·수정한 함수에만 복잡도 한계를 적용한다(기존 위반은 기준선으로 동결).
- 한계 초과 시 차단 대신 **리뷰어 확인 필요** 라벨을 붙이는 단계부터 시작한다.
- 예외는 허용하되 이유를 주석으로 남긴다(예: 프로토콜 상태 기계의 큰 `switch`).

## 흔한 오해와 함정

- **"복잡도가 낮으면 좋은 코드다."** 복잡도 2 짜리 함수 50개로 쪼갠 코드는 흐름을 따라가기가 오히려 어렵다. 메트릭은 함수 **안**만 본다.
- **"복잡도 10 은 과학적 상수다."** 원전도 근거가 있는 출발점이라고 했을 뿐, 15 까지 쓴 사례와 예외 규칙을 함께 제시한다.
- **메트릭을 개인 평가에 쓰기.** 측정 대상이 목표가 되면 사람들은 숫자를 최적화한다. 팀이 스스로 개선 지점을 찾는 데만 쓴다.
- **도구 간 숫자 비교.** 단락 연산자, `switch`, 예외 처리를 세는 방식이 도구마다 다르다. 같은 도구 안에서의 추세만 의미가 있다.

## 확인 문제

1. 이진 결정이 3개이고 그중 하나의 조건에 `&&` 가 하나 있는 C 함수의 v(G) 는?
2. v(G) 가 테스트 설계에서 의미하는 바는 무엇인가?
3. 순환 복잡도가 같은 두 함수의 가독성이 크게 다를 수 있는 이유를 인지 복잡도의 규칙으로 설명하라.
4. Shepperd 의 비판을 받아들인다면, 복잡도와 결함의 상관을 해석할 때 무엇을 통제해야 하는가?

### 풀이

1. 결정 술어는 if 3개 + `&&` 1개 = 4, 따라서 v(G) = 4 + 1 = 5.
2. 제어 흐름 그래프의 선형 독립 경로 수다. 구조적 테스트는 그만큼의 기초 경로를 테스트하도록 요구하므로 필요한 테스트 경로 수의 하한이 된다.
3. 순환 복잡도는 중첩 깊이를 무시하고 `switch` 갈래를 모두 센다. 인지 복잡도는 중첩될수록 가중하고 `switch` 는 한 번만 세므로, 깊이 중첩된 루프는 높게, 평평한 분기는 낮게 나온다.
4. 코드 길이(LOC). 복잡도가 길이의 대리 변수일 수 있으므로 길이를 통제한 뒤에도 복잡도가 추가 설명력을 갖는지 봐야 한다.

## 더 읽을거리 (References)

- T. J. McCabe, "A Complexity Measure", *IEEE TSE* SE-2(4), 1976, [DOI](https://doi.org/10.1109/TSE.1976.233837)
- A. H. Watson, T. J. McCabe, [Structured Testing: A Software Testing Methodology Using the Cyclomatic Complexity Metric](https://www.nist.gov/publications/structured-testing-software-testing-methodology-using-cyclomatic-complexity-metric), NIST SP 500-235, 1996
- M. Shepperd, "A critique of cyclomatic complexity as a software metric", *Software Engineering Journal* 3(2), 1988, [DOI](https://doi.org/10.1049/sej.1988.0003)
- G. A. Campbell, [Cognitive Complexity](https://www.sonarsource.com/docs/CognitiveComplexity.pdf), SonarSource 백서 v1.7, 2023 / TechDebt 2018, [DOI](https://doi.org/10.1145/3194164.3194186)
- S. R. Chidamber, C. F. Kemerer, "A Metrics Suite for Object Oriented Design", *IEEE TSE* 20(6), 1994, [DOI](https://doi.org/10.1109/32.295895)
- [Checkstyle CyclomaticComplexity](https://checkstyle.sourceforge.io/checks/metrics/cyclomaticcomplexity.html), [Radon](https://radon.readthedocs.io/en/latest/api.html), [mccabe](https://github.com/PyCQA/mccabe)
