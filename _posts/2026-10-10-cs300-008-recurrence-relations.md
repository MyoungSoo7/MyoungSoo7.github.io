---
layout: post
title: "[CS300 #008] 점화식과 그 풀이 — 재귀 알고리즘의 비용을 닫힌 식으로"
date: 2026-10-10 18:08:00 +0900
categories: [cs]
tags: [cs300, math, recurrence, master-theorem, algorithm-analysis]
---

컴퓨터공학 300 주제 시리즈의 008번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

점화식은 수열의 각 항을 앞선 항들로 정의하는 식이다. 재귀 알고리즘의 실행 시간은 자연스럽게 점화식으로 나오고, 그것을 "n 에 대한 닫힌 식" 으로 풀어야 알고리즘끼리 비교할 수 있다.

## 왜 필요한가

병합 정렬의 실행 시간을 코드에서 바로 읽으면 "길이 n 을 정렬하는 시간은 길이 n/2 를 두 번 정렬하는 시간에 합치는 시간 n 을 더한 것" 이다. 이것이 점화식 T(n) = 2T(n/2) + n 이다. 이 식만 보고는 n = 백만일 때 얼마나 걸리는지 감이 오지 않는다. 풀어서 T(n) = Θ(n log n) 을 얻어야 비로소 O(n²) 정렬보다 빠르다고 말할 수 있다.

점화식은 알고리즘 분석 말고도 많다. 복리 계산, 개체 수 모델, 동적 계획법의 상태 전이, 피보나치 수가 모두 점화식이다.

## 핵심 개념

### 점화식의 구성

점화식은 **초기 조건**과 **점화 관계** 두 부분으로 이루어진다.

```
a(0) = 1                  초기 조건
a(n) = 2·a(n-1)  (n ≥ 1)  점화 관계
```

이 둘이 함께 수열을 유일하게 결정한다. 004번 글의 귀납법과 같은 구조다. 초기 조건이 기저 단계, 점화 관계가 귀납 단계에 해당한다. 위 식의 해는 a(n) = 2ⁿ 이다.

### 풀이법 1: 반복 대입(펼치기)

식을 계속 대입해서 패턴을 찾는다. T(n) = T(n−1) + n, T(1) = 1 이면

```
T(n) = T(n-1) + n
     = T(n-2) + (n-1) + n
     = ...
     = T(1) + 2 + 3 + ... + n
     = n(n+1)/2
```

삽입 정렬의 최악 비교 횟수가 이런 모양이다. 추측한 답은 귀납법으로 확인한다.

### 풀이법 2: 선형 점화식과 특성 방정식

a(n) = c₁·a(n−1) + c₂·a(n−2) 꼴(상수 계수 2차 선형 동차 점화식)은 a(n) = rⁿ 을 대입해서 푼다. 양변을 rⁿ⁻² 로 나누면 **특성 방정식** r² = c₁r + c₂ 를 얻는다.

- 서로 다른 두 근 r₁, r₂ 가 있으면 일반해는 a(n) = A·r₁ⁿ + B·r₂ⁿ 이다.
- 중근 r 이면 a(n) = (A + Bn)·rⁿ 이다.
- 상수 A, B 는 초기 조건으로 정한다.

피보나치 F(n) = F(n−1) + F(n−2), F(0) = 0, F(1) = 1 의 특성 방정식은 r² = r + 1 이고 근은 φ = (1+√5)/2, ψ = (1−√5)/2 다. 초기 조건을 넣으면

```
F(n) = (φⁿ − ψⁿ) / √5
```

이것이 비네 공식이다. ψ 의 절댓값은 1 보다 작아서 ψⁿ 은 빠르게 0 으로 간다. 그래서 F(n) 은 φⁿ/√5 에 가장 가까운 정수이고, 피보나치 수는 약 1.618 배씩 커진다.

### 풀이법 3: 재귀 트리

분할 정복의 점화식 T(n) = aT(n/b) + f(n) 은 트리로 그리면 잘 보인다. T(n) = 2T(n/2) + n 이라면

```
레벨 0:            n                    → 합 n
레벨 1:       n/2      n/2              → 합 n
레벨 2:   n/4  n/4  n/4  n/4            → 합 n
...
레벨 log₂n: 1 1 1 ... 1 (n 개)           → 합 n
```

레벨이 log₂n + 1 개이고 각 레벨의 합이 n 이므로 전체는 Θ(n log n) 이다.

### 마스터 정리

T(n) = aT(n/b) + f(n) (a ≥ 1, b > 1) 꼴에 쓰는 공식이다. 핵심은 f(n) 과 n^(log_b a) 의 비교다. n^(log_b a) 는 재귀 트리의 잎 개수다.

| 경우 | 조건 | 결과 | 직관 |
|---|---|---|---|
| 1 | f(n) = O(n^(log_b a − ε)), ε > 0 | Θ(n^(log_b a)) | 잎이 지배 |
| 2 | f(n) = Θ(n^(log_b a)) | Θ(n^(log_b a) · log n) | 모든 레벨이 비슷 |
| 3 | f(n) = Ω(n^(log_b a + ε)) 이고 정칙 조건 | Θ(f(n)) | 뿌리가 지배 |

(3 번의 정칙 조건은 어떤 c < 1 과 충분히 큰 n 에 대해 a·f(n/b) ≤ c·f(n) 이다.)

| 알고리즘 | 점화식 | log_b a | 결과 |
|---|---|---|---|
| 이진 탐색 | T(n) = T(n/2) + 1 | 0 | Θ(log n) (경우 2) |
| 병합 정렬 | T(n) = 2T(n/2) + n | 1 | Θ(n log n) (경우 2) |
| 카라추바 곱셈 | T(n) = 3T(n/2) + n | log₂3 ≈ 1.585 | Θ(n^1.585) (경우 1) |
| 이진 트리 순회 | T(n) = 2T(n/2) + 1 | 1 | Θ(n) (경우 1) |

마스터 정리가 덮지 못하는 꼴도 있다. T(n) = T(n−1) + n 처럼 크기가 비율이 아니라 상수만큼 줄어드는 경우, 또는 f(n) 이 경계에 걸리는 경우다. 그때는 반복 대입이나 재귀 트리로 직접 푼다.

## 직접 해 보기

점화식을 그대로 코드로 옮겨 값을 계산하고, 풀이로 얻은 닫힌 식과 비교한다. 메모이제이션에는 `functools.lru_cache` 를 쓴다.

```python
import math
from functools import lru_cache

# 1) 비네 공식 vs 점화식
@lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

phi = (1 + math.sqrt(5)) / 2
psi = (1 - math.sqrt(5)) / 2
binet = lambda n: round((phi**n - psi**n) / math.sqrt(5))
print(all(fib(n) == binet(n) for n in range(60)), fib(60), fib(61) / fib(60))

# 2) 병합 정렬 점화식 T(n) = 2T(n/2) + n, T(1) = 0  vs  n log2 n
@lru_cache(maxsize=None)
def T(n):
    return 0 if n == 1 else 2 * T(n // 2) + n
for k in [4, 10, 20]:
    n = 2**k
    print(n, T(n), int(n * math.log2(n)))

# 3) 메모이제이션 없는 피보나치의 호출 횟수도 점화식을 따른다
calls = 0
def slow_fib(n):
    global calls
    calls += 1
    return n if n < 2 else slow_fib(n - 1) + slow_fib(n - 2)
slow_fib(25)
print(calls, 2 * fib(26) - 1)
```

실행 결과다.

```
True 1548008755920 1.618033988749895
16 64 64
1024 10240 10240
1048576 20971520 20971520
242785 242785
```

셋째 실험이 흥미롭다. 호출 횟수 C(n) 은 C(n) = C(n−1) + C(n−2) + 1, C(0) = C(1) = 1 을 따르고, 풀면 C(n) = 2F(n+1) − 1 이다. 순진한 재귀 피보나치가 지수 시간인 이유를 점화식이 정확히 보여 준다. `lru_cache` 를 붙이면 각 n 을 한 번씩만 계산하므로 선형 시간이 된다.

(비네 공식은 부동소수점 오차 때문에 n 이 70 을 넘어가면 정수 점화식과 어긋나기 시작한다. 큰 n 에서는 정수 연산이나 행렬 거듭제곱을 쓴다.)

## 현업에서는

- **재귀 함수의 비용 추정.** 코드 리뷰에서 재귀 함수를 보면 "한 번 호출이 자기 자신을 몇 번, 얼마나 작은 입력으로 부르는가" 를 세어 점화식을 세운다. 호출이 두 번이고 크기가 1 만 줄면 지수, 크기가 절반이면 마스터 정리로 판정한다. 메모이제이션 유무가 지수와 다항식의 차이를 만든다.
- **지수 백오프.** 재시도 대기 시간을 d(k) = 2·d(k−1) 로 늘리면 d(k) = d(0)·2ᵏ 다. 상한(cap)을 두지 않으면 열 번째 재시도에서 대기 시간이 초기값의 1024 배가 된다. 쿠버네티스에서 컨테이너가 계속 죽을 때 보는 CrashLoopBackOff 도 재시작 지연이 지수적으로 늘어나다가 상한에서 멈추는 방식이다([Kubernetes, Pod Lifecycle — Container restarts](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-restarts)).
- **동적 계획법.** DP 문제를 푸는 첫 단계는 점화식을 세우는 것이다. "길이 n 의 답은 길이 n−1, n−2 의 답으로 어떻게 표현되는가" 를 쓰고 나면 코드는 그 식을 표로 채우는 일일 뿐이다.

## 확인 문제

1. a(n) = 3a(n−1), a(0) = 2 의 닫힌 식은?
2. a(n) = 5a(n−1) − 6a(n−2), a(0) = 0, a(1) = 1 을 풀어라.
3. T(n) = 4T(n/2) + n 의 점근적 해는?
4. T(n) = T(n/2) + n 의 점근적 해는?

### 풀이

1. a(n) = 2·3ⁿ.
2. 특성 방정식 r² = 5r − 6 의 근은 2, 3. a(n) = A·2ⁿ + B·3ⁿ 에 초기 조건을 넣으면 A = −1, B = 1. 따라서 a(n) = 3ⁿ − 2ⁿ.
3. log₂4 = 2 이고 f(n) = n 은 n² 보다 다항식만큼 작으므로 경우 1, Θ(n²).
4. log₂1 = 0 이고 f(n) = n 이 n⁰ 보다 크며 정칙 조건(f(n/2) = n/2 ≤ c·n, c = 1/2)도 만족하므로 경우 3, Θ(n).

## 더 읽을거리 (References)

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein, *Introduction to Algorithms*, 4판, MIT Press, 4장 Divide-and-Conquer(마스터 정리)
- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 22장 Recurrences — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Python Documentation, functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [Kubernetes Documentation, Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
