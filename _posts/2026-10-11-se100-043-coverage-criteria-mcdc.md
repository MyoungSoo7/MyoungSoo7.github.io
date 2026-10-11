---
layout: post
title: "[SE100 #043] 화이트박스 기법 — 커버리지 기준과 MC/DC"
date: 2026-10-11 17:01:42 +0900
categories: [software-engineering]
tags: [se100, software-testing, code-coverage, mcdc, do-178c]
---

소프트웨어 공학 100 주제 시리즈의 43번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

커버리지 기준은 "코드의 어떤 구조를 최소 한 번씩 실행했는가" 를 정하는 규칙이다. 문장 → 분기 → 조건/결정 → **MC/DC** → 다중 조건으로 갈수록 엄격해지고, MC/DC 는 "결정 안의 각 조건이 **혼자서** 결과를 바꿀 수 있음을 보였는가" 를 요구한다. 커버리지는 **테스트되지 않은 곳을 찾는 도구**이지 테스트 품질 점수가 아니다.

## 왜 필요한가

블랙박스 기법(SE100 #042)은 명세에서 출발하므로, 명세에 드러나지 않은 구현 내부의 분기는 놓칠 수 있다. 반대로 코드에서 출발하는 화이트박스 기법은 "이 `if` 의 거짓 쪽은 한 번도 실행된 적이 없다" 같은 사실을 기계적으로 알려 준다.

문제는 "실행했다" 의 기준이 여러 개라는 것이다. 다음 코드는 문장 커버리지 100% 를 테스트 하나로 달성한다.

```java
if (user.isAdmin() || request.isInternal()) {
    allow();
}
audit();
```

`isAdmin()=true` 인 테스트 하나면 모든 줄이 실행된다. 그러나 결정이 거짓인 경우(`deny` 경로), `isInternal()` 이 결과를 좌우하는 경우는 전혀 확인되지 않았다. 권한 검사처럼 틀리면 비싼 로직일수록 "어떤 커버리지인가" 가 중요하다.

## 핵심 개념

### 용어: 조건과 결정

NASA 튜토리얼(아래)이 DO-178B 를 따라 쓰는 정의다.

- **조건(condition)**: 불리언 연산자를 포함하지 않는 불리언 식. `a > 0`, `isAdmin()`
- **결정(decision)**: 조건들과 0개 이상의 불리언 연산자로 이루어진 불리언 식. `isAdmin() || isInternal()`
- 같은 조건이 결정 안에 여러 번 나오면 **각 등장을 별개의 조건**으로 센다.

### 기준의 사다리

NASA 의 [A Practical Tutorial on Modified Condition/Decision Coverage](https://ntrs.nasa.gov/citations/20010057789) (Hayhurst, Veerhusen, Chilenski, Rierson, NASA/TM-2001-210876, 2001) 의 표 1 은 구조 커버리지 기준을 이렇게 정의한다(번역).

| 기준 | 요구 사항 |
|---|---|
| 문장(statement) | 모든 문장이 최소 한 번 실행됨 |
| 결정(decision) | 모든 결정이 가능한 모든 결과를 최소 한 번 가짐 (+ 진입·출구점) |
| 조건(condition) | 결정 안의 모든 조건이 가능한 모든 결과를 최소 한 번 가짐 |
| 조건/결정 | 결정 커버리지 + 조건 커버리지 |
| **MC/DC** | 위에 더해, 결정 안의 각 조건이 결정 결과에 **독립적으로 영향**을 줌을 보임 |
| 다중 조건 | 결정 안 조건 결과의 **모든 조합** 실행 |

몇 가지 관계를 짚어 둔다.

- ISTQB [강의계획서 v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) 4.3.2절: **분기 커버리지는 문장 커버리지를 포섭(subsume)** 한다. 분기 100% 면 문장 100% 지만 역은 아니다.
- 조건 커버리지는 결정 커버리지를 보장하지 **않는다**. 튜토리얼의 예로 `A or B` 에 (T,F), (F,T) 두 테스트는 각 조건을 참·거짓으로 한 번씩 만들지만 결정은 두 번 다 참이다.
- 조건/결정 커버리지도 약하다. `A or B` 에 (T,T), (F,F) 를 쓰면 기준은 만족하지만, 튜토리얼이 지적하듯 이 두 테스트는 올바른 식 `A or B` 를 `A` 만 있는 식이나 `B` 만 있는 식, `A and B` 와 구별하지 못한다.
- 다중 조건 커버리지는 입력이 n 개면 2ⁿ 개 테스트가 필요해 대부분 비현실적이다.

### MC/DC 의 정의와 출처

Chilenski 와 Miller 의 [Applicability of modified condition/decision coverage to software testing](https://doi.org/10.1049/sej.1994.0025) (Software Engineering Journal, 1994) 은 MC/DC 를 "결정 안의 각 조건이 실행을 통해 결정 결과에 **독립적이고 올바르게** 영향을 준다는 것을 보이도록 요구하는" 구조 커버리지 기준으로 기술하고, 안전 필수 응용에서 복잡한 불리언 식을 철저히 시험할 필요 때문에 개발되었다고 설명한다.

MC/DC 가 실무 의무가 된 곳은 항공이다. RTCA 의 [DO-178 페이지](https://www.rtca.org/do-178/) 에 따르면 DO-178() 는 1981년 처음 발행된 항공 소프트웨어 보증의 핵심 문서이고, 현행판 DO-178C 는 2011년에 발행되었다. NASA 튜토리얼은 당시 판인 DO-178B 를 기준으로, 문장 커버리지는 레벨 A–C, 결정 커버리지는 레벨 A–B, MC/DC 는 **레벨 A** 소프트웨어에 요구된다고 정리한다. 소프트웨어 레벨이 높을수록 더 엄격한 기준이 붙는 구조다.

### 독립 영향을 보이는 두 방법

| 방법 | 내용 |
|---|---|
| 고유 원인(unique-cause) | 한 조건만 바꾸고 나머지는 고정했을 때 결과가 바뀌는 테스트 쌍을 찾는다 |
| 가림(masking) | 다른 조건이 바뀌더라도, 논리 분석으로 그 조건들이 결과에 영향을 주지 못함(가려짐)을 보인다 |

NASA 튜토리얼은 고유 원인 방식이 역사적으로 독립 영향을 보이는 거의 유일하게 인정된 방법이었다고 설명하고, 결합된 조건(`(A and B) or (A and C)` 처럼 같은 조건이 여러 번 나오는 식)에서는 고유 원인 쌍을 만들 수 없는 경우가 있어 가림 방식이 필요하다고 다룬다.

### 짧은 회로 평가

C 계열·Java 의 `&&`, `||` 는 짧은 회로로 평가되어 뒤 조건이 실행되지 않을 수 있다. 튜토리얼은 짧은 회로 식도 일반 and/or 게이트처럼 다룰 수 있다고 하면서, 정해진 평가 순서를 테스트 설계에 활용하는 예를 보여 준다. 또 컴파일러 기능에 기대 소스 수준과 목적 코드 수준 커버리지의 동등성을 주장하려면 그 컴파일러 기능 자체를 검증 도구로 자격 인정(qualify)해야 할 수 있다고 경고한다.

## 예제

### MC/DC 테스트 집합 만들기

결정 `D = A && (B || C)`. 고유 원인 쌍을 찾는다.

| # | A | B | C | D |
|---|---|---|---|---|
| 1 | T | T | F | **T** |
| 2 | F | T | F | **F** |
| 3 | T | F | F | **F** |
| 4 | T | F | T | **T** |

- A 의 독립 영향: 1 ↔ 2 (B=T, C=F 고정, A 만 바뀜, D 가 T→F)
- B 의 독립 영향: 1 ↔ 3 (A=T, C=F 고정)
- C 의 독립 영향: 4 ↔ 3 (A=T, B=F 고정)

조건 3개에 테스트 4개다. 다중 조건 커버리지라면 2³ = 8개가 필요하다. 이 예처럼 서로 독립인 조건 n 개로 된 결정에서는 n+1 개로 MC/DC 를 맞추는 집합을 찾을 수 있는 경우가 많다. 조건 수가 늘어날수록 2ⁿ 과의 격차가 MC/DC 가 실용적인 이유다.

```python
# 위 집합이 MC/DC 를 만족하는지 기계적으로 확인
from itertools import combinations

def D(a, b, c): return a and (b or c)
tests = [(True, True, False), (False, True, False),
         (True, False, False), (True, False, True)]

for i, name in enumerate("ABC"):
    pairs = [(s, t) for s, t in combinations(tests, 2)
             if s[i] != t[i]
             and all(s[j] == t[j] for j in range(3) if j != i)
             and D(*s) != D(*t)]
    print(name, "독립 영향 쌍:", pairs[:1])
```

### 도구가 세는 것

| 도구 | 측정 단위 | 비고 |
|---|---|---|
| [JaCoCo](https://www.jacoco.org/jacoco/trunk/doc/counters.html) | 명령어(C0), 분기(C1), 줄, 메서드, 순환 복잡도 | 바이트코드 명령어 단위. `if`·`switch` 분기를 세며 **예외 처리는 분기로 세지 않는다** |
| [coverage.py](https://coverage.readthedocs.io/en/latest/branch.html) | 문장, `--branch` 시 분기 | 한 줄에서 갈 수 있는 다음 줄(목적지) 중 방문하지 않은 것을 "부분 분기" 로 표시 |

둘 다 기본적으로 MC/DC 를 측정하지 않는다. MC/DC 가 필요한 도메인은 별도의 자격 인정된 도구를 쓴다. 범용 도구의 "branch" 를 MC/DC 로 착각하지 않는다.

## 흔한 오해와 함정

- **커버리지를 목표치로 삼는다.** Martin Fowler 는 [TestCoverage](https://martinfowler.com/bliki/TestCoverage.html) (2012) 에서 커버리지가 "테스트되지 않은 부분을 찾는 데 유용한 도구" 이지만 "테스트가 얼마나 좋은지에 대한 수치로는 거의 쓸모가 없다" 고 정리한다. 높은 수치는 낮은 품질의 테스트로도 쉽게 달성되며, 극단적으로는 단언 없는 테스트로도 된다. 그는 생각 있게 테스트하면 80% 대 후반이나 90% 대를 예상하고, 100% 는 오히려 수치를 맞추려 테스트를 쓴 냄새로 의심한다고 썼다.
- **커버리지와 결함 검출력이 비례한다고 믿는다.** Inozemtseva 와 Holmes 의 ICSE 2014 논문 제목이 곧 결론이다: [Coverage is not strongly correlated with test suite effectiveness](https://doi.org/10.1145/2568225.2568271). 초록은 기존 연구들이 테스트 묶음 **크기**의 교란 효과를 통제하지 않은 경우가 있었다고 지적한다. 테스트를 많이 쓰면 커버리지도 오르고 결함도 더 잡히니, 둘 사이의 상관이 부풀려 보일 수 있다.
- **"실행됨" 을 "검증됨" 으로 읽는다.** 커버리지는 도달만 측정한다(SE100 #041 의 도달·감염·전파). 실행된 코드가 의미 있게 검사됐는지는 뮤테이션 테스팅(SE100 #047)이 측정한다.
- **누락 결함은 화이트박스로 못 잡는다.** ISTQB 강의계획서 4.3.3절도 지적하듯, 요구사항을 아예 구현하지 않았다면 코드에 구조가 없으므로 화이트박스 기법은 그 누락을 발견하지 못할 수 있다.
- **도구의 분기 정의를 확인하지 않는다.** 예외 경로, 짧은 회로, 삼항 연산자, 컴파일러가 만든 합성 코드를 도구마다 다르게 센다.

## 확인 문제

1. 분기 커버리지가 문장 커버리지를 포섭한다는 것은 무슨 뜻인가? 역은 왜 성립하지 않는가?
2. `A or B` 에서 조건 커버리지는 만족하지만 결정 커버리지는 만족하지 않는 테스트 집합을 들어라.
3. `D = A || (B && C)` 에 대해 고유 원인 방식의 MC/DC 테스트 집합을 4개로 만들어라.
4. 커버리지 90% 를 CI 게이트로 강제할 때 생길 수 있는 부작용 두 가지는?
5. JaCoCo 의 분기 커버리지가 100% 인데도 `try/catch` 의 예외 경로가 한 번도 실행되지 않았을 수 있는 이유는?

### 풀이

1. 분기 100% 를 만족하는 모든 테스트 집합은 문장 100% 도 만족한다. 그러나 앞의 `if (isAdmin() || isInternal())` 예처럼 참 경로만 실행해도 모든 문장이 실행될 수 있어, 문장 100% 가 분기 100% 를 보장하지 않는다.
2. (A=T, B=F), (A=F, B=T). 각 조건은 참과 거짓을 모두 가지지만 결정은 두 번 다 참이다.
3. 예: (F,T,T)→T, (F,F,T)→F, (F,T,F)→F, (T,F,T)→T. A 는 (F,F,T)↔(T,F,T), B 는 (F,T,T)↔(F,F,T), C 는 (F,T,T)↔(F,T,F) 쌍이 각각 그 조건만 바꿔 결과를 바꾼다.
4. 단언이 약하거나 없는 테스트로 수치만 맞추게 된다. 중요하지 않은 코드에 테스트를 몰아 쓰며 정작 위험한 로직의 검증 깊이는 그대로일 수 있다.
5. JaCoCo 문서에 따르면 분기 카운터는 `if`·`switch` 분기를 세고 예외 처리는 분기로 세지 않는다. 예외 경로의 실행 여부는 명령어·줄 카운터로 따로 확인해야 한다.

## 더 읽을거리 (References)

- K. J. Hayhurst, D. S. Veerhusen, J. J. Chilenski, L. K. Rierson, [A Practical Tutorial on Modified Condition/Decision Coverage](https://ntrs.nasa.gov/citations/20010057789), NASA/TM-2001-210876, 2001
- J. J. Chilenski, S. P. Miller, [Applicability of modified condition/decision coverage to software testing](https://doi.org/10.1049/sej.1994.0025), Software Engineering Journal 9(5), 1994
- RTCA, [DO-178() Software Considerations in Airborne Systems and Equipment Certification](https://www.rtca.org/do-178/)
- L. Inozemtseva, R. Holmes, [Coverage is not strongly correlated with test suite effectiveness](https://doi.org/10.1145/2568225.2568271), ICSE 2014
- Martin Fowler, [TestCoverage](https://martinfowler.com/bliki/TestCoverage.html)
- ISTQB, [Certified Tester Foundation Level Syllabus v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) (PDF), 4.3절
- JaCoCo, [Coverage Counters](https://www.jacoco.org/jacoco/trunk/doc/counters.html) / coverage.py, [Branch coverage measurement](https://coverage.readthedocs.io/en/latest/branch.html)
