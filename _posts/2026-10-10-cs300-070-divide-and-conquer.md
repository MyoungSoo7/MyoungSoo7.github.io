---
layout: post
title: "[CS300 #070] 분할 정복 — 쪼개고, 풀고, 합치는 설계법"
date: 2026-10-10 19:10:00 +0900
categories: [cs]
tags: [cs300, algorithms, divide-and-conquer, karatsuba, recurrence]
---

컴퓨터공학 300 주제 시리즈의 070번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

분할 정복은 문제를 같은 꼴의 작은 문제로 쪼개 재귀로 풀고 결과를 합친다. 성능은 "몇 개로 쪼개는가(a)", "얼마나 작아지는가(b)", "합치는 데 얼마나 드는가(f(n))" 세 숫자로 정해지고, 마스터 정리가 그 셋을 답으로 바꿔 준다.

## 왜 필요한가

병합 정렬과 퀵 정렬, 이진 탐색은 모두 분할 정복이다. 이 셋을 따로 외우는 대신 하나의 설계 틀로 보면, 처음 보는 문제에도 "쪼갤 수 있나? 합칠 수 있나? 합치는 비용이 얼마인가?" 라는 질문을 던질 수 있다.

분할 정복의 진짜 힘은 "당연해 보이는 하한" 을 깨는 데서 나온다. 두 n 자리 수의 곱셈은 초등학교 방법으로 n² 번의 한 자리 곱이 필요하다. Karatsuba 는 1960년대 초에 분할 정복으로 이를 약 n^1.585 로 줄였다. 곱셈이 n² 보다 빠를 수 있다는 사실 자체가 당시엔 놀라운 결과였다.

## 핵심 개념

### 세 단계

```
solve(P):
    if P 가 충분히 작다: 직접 푼다           (기저 사례)
    P 를 P1..Pa 로 나눈다                    (분할)
    각 Pi 를 solve 로 푼다                    (정복)
    결과를 합쳐 P 의 답을 만든다              (결합)
```

점화식은 T(n) = a·T(n/b) + f(n) 이다.

| 알고리즘 | a | b | f(n) | 결과 |
|---|---|---|---|---|
| 이진 탐색 | 1 | 2 | Θ(1) | Θ(log n) |
| 병합 정렬 | 2 | 2 | Θ(n) | Θ(n log n) |
| 역순쌍 세기 | 2 | 2 | Θ(n) | Θ(n log n) |
| 단순 분할 곱셈 | 4 | 2 | Θ(n) | Θ(n²) |
| Karatsuba 곱셈 | 3 | 2 | Θ(n) | Θ(n^log₂3) ≈ Θ(n^1.585) |
| Strassen 행렬 곱 | 7 | 2 | Θ(n²) | Θ(n^log₂7) ≈ Θ(n^2.807) |

표를 보면 패턴이 보인다. **하위 문제 개수 a 를 하나 줄이는 것** 이 지수를 바꾼다. 결합 비용이 조금 늘어도 a 가 줄면 이긴다.

### Karatsuba 의 한 수

x = a·10^m + b, y = c·10^m + d 로 나누면

```
x·y = ac·10^(2m) + (ad + bc)·10^m + bd
```

곱셈이 ac, ad, bc, bd 로 4번 필요해 보인다. 그런데

```
(a + b)(c + d) = ac + ad + bc + bd
ad + bc = (a + b)(c + d) − ac − bd
```

이미 구한 ac, bd 를 재사용하면 곱셈 3번으로 충분하다. 덧셈·뺄셈은 Θ(n) 이라 싸다. T(n) = 3T(n/2) + Θ(n) 이고 마스터 정리 경우 1 에 해당해 Θ(n^log₂3) 이다.

### 역순쌍 세기: 결합에서 정보 얻기

배열의 역순쌍(i < j, a[i] > a[j]) 수를 세려면 모든 쌍을 보면 Θ(n²) 이다. 분할 정복으로 보면 역순쌍은 세 종류다.

1. 둘 다 왼쪽 절반에 있는 것 — 재귀로 센다.
2. 둘 다 오른쪽 절반에 있는 것 — 재귀로 센다.
3. 하나는 왼쪽, 하나는 오른쪽 — 결합 단계에서 센다.

3번이 핵심이다. 양쪽이 각각 정렬되어 있으면, 병합하면서 오른쪽 원소 r 이 먼저 나갈 때 왼쪽에 남은 원소 전부가 r 보다 크다. 그 개수를 한 번에 더하면 된다. 병합 정렬에 한 줄을 더해 Θ(n log n) 이 된다.

### 분할 정복이 맞지 않을 때

- **하위 문제가 겹칠 때.** 피보나치를 `fib(n-1) + fib(n-2)` 로 재귀하면 같은 하위 문제를 지수 번 다시 푼다. 이때는 동적 계획법(다음다음 글)이 답이다.
- **결합이 비쌀 때.** 결합이 Θ(n²) 이면 분할의 이득이 사라질 수 있다.
- **작은 입력.** 재귀 호출 비용이 크므로, 실무 구현은 일정 크기 아래에서 단순 알고리즘으로 바꾼다(cutoff).

## 직접 해 보기

역순쌍 세기와 Karatsuba 곱셈을 짜서 단순 방법과 대조한다. python3 로 실행해 확인했다.

```python
import random

def count_inversions(a):
    """병합 정렬하면서 역순쌍 수를 센다. Θ(n log n)."""
    if len(a) <= 1:
        return a, 0
    mid = len(a) // 2
    left, x = count_inversions(a[:mid])
    right, y = count_inversions(a[mid:])
    out, i, j, cross = [], 0, 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
            cross += len(left) - i     # 왼쪽에 남은 것 전부가 right[j] 보다 크다
    out += left[i:] + right[j:]
    return out, x + y + cross

def brute(a):
    return sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if a[i] > a[j])

def karatsuba(x, y):
    if x < 10 or y < 10:
        return x * y
    m = max(len(str(x)), len(str(y))) // 2
    p = 10 ** m
    a, b = divmod(x, p)
    c, d = divmod(y, p)
    ac = karatsuba(a, c)
    bd = karatsuba(b, d)
    mid = karatsuba(a + b, c + d) - ac - bd     # 곱셈 4번이 아니라 3번
    return ac * p * p + mid * p + bd

random.seed(7)
a = [random.randint(0, 99) for _ in range(500)]
print("역순쌍:", count_inversions(a)[1], "검산:", brute(a))

x, y = 1234567890123456789, 9876543210987654321
print(karatsuba(x, y) == x * y)
```

출력:

```
역순쌍: 60554 검산: 60554
True
```

교육용 코드라 `str` 로 자릿수를 세고 10진수로 나눈다. 실제 구현은 2진수 기반 큰 자릿수 단위로 나눈다. CPython 의 정수 곱셈 소스(`Objects/longobject.c`)에도 `k_mul` 이라는 Karatsuba 구현이 있고, 두 수가 `KARATSUBA_CUTOFF` 보다 작으면 단순 곱셈을 쓴다. 위에서 말한 cutoff 가 실제 코드에 그대로 있다.

## 현업에서는

- **큰 수 연산.** 암호 라이브러리, 임의 정밀도 정수(Python `int`, Java `BigInteger`)는 크기에 따라 단순 곱셈과 Karatsuba 등 분할 정복 곱셈을 골라 쓴다.
- **병렬 처리.** 쪼갠 하위 문제가 서로 독립이라 병렬화하기 쉽다. Java 의 fork/join 프레임워크, 맵리듀스(쪼개 처리하고 리듀스로 합침)가 같은 틀이다.
- **기하·신호 처리.** 고속 푸리에 변환(FFT)은 크기 n 의 변환을 n/2 두 개로 쪼개 Θ(n log n) 에 계산한다. 오디오·이미지 처리, 큰 수 곱셈의 더 빠른 방법들의 기반이다.
- **운영 장애 분석.** 설정 변경 수십 개 중 무엇이 문제인지 찾을 때 절반씩 되돌려 보는 것도 분할 정복이다. 이진 탐색처럼 한쪽만 따라가는 특수한 경우다.

## 확인 문제

1. T(n) = 3T(n/2) + n 의 해를 구하라.
2. 역순쌍 세기에서 결합 단계가 Θ(n) 이 될 수 있는 전제 조건은?
3. 피보나치 수를 단순 분할 정복으로 구하면 왜 지수 시간인가?
4. Strassen 이 행렬 곱의 하위 곱셈을 8번에서 7번으로 줄였을 때 지수는 어떻게 바뀌는가?

### 풀이

1. a=3, b=2, n^log₂3 ≈ n^1.585 가 f(n) = n 보다 다항식만큼 크다. 마스터 정리 경우 1, Θ(n^log₂3).
2. 두 절반이 각각 정렬되어 있어야 한다. 그래서 세면서 동시에 정렬(병합)도 한다.
3. 하위 문제 fib(n−1), fib(n−2) 가 서로 겹치는 하위 문제를 대량으로 공유하는데, 이를 매번 새로 푼다. 호출 수가 피보나치 수 자체처럼 지수적으로 는다.
4. log₂8 = 3 에서 log₂7 ≈ 2.807 로 줄어든다.

## 더 읽을거리 (References)

- NIST Dictionary of Algorithms and Data Structures, [divide and conquer](https://xlinux.nist.gov/dads/HTML/divideAndConquer.html)
- CPython 소스, [Objects/longobject.c](https://raw.githubusercontent.com/python/cpython/main/Objects/longobject.c) — `k_mul`, `KARATSUBA_CUTOFF`
- MIT OpenCourseWare, [Introduction to Algorithms, Spring 2020](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022, 4장.
