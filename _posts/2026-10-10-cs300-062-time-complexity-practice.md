---
layout: post
title: "[CS300 #062] 시간 복잡도 분석 연습 — 루프를 세고 재귀를 푸는 법"
date: 2026-10-10 19:02:00 +0900
categories: [cs]
tags: [cs300, algorithms, time-complexity, recurrence, master-theorem]
---

컴퓨터공학 300 주제 시리즈의 062번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

시간 복잡도 분석은 "가장 많이 실행되는 문장이 n 에 대해 몇 번 도는가" 를 세는 일이다. 반복문은 합으로, 재귀는 점화식으로 바꾼 뒤 푼다.

## 왜 필요한가

빅오 정의를 아는 것과 실제 코드의 복잡도를 읽어 내는 것은 다른 기술이다. 정의는 한 번 이해하면 되지만, 코드 읽기는 패턴을 손에 익혀야 한다. 루프 안에 숨은 `in` 연산, 슬라이싱, 문자열 더하기 같은 것들이 복잡도를 한 단계 올린다. 이걸 못 보면 테스트에선 빠르고 운영에선 느린 코드를 계속 만들게 된다.

## 핵심 개념

### 규칙 1. 순차는 더하고, 중첩은 곱한다

```python
for i in range(n):        # n 번
    work()                # O(1)
for i in range(n):        # n 번
    for j in range(n):    # 각각 n 번
        work()
```

전체는 n + n² = Θ(n²). 더할 때는 큰 항만 남는다.

### 규칙 2. 안쪽 루프 범위가 바깥 변수에 묶이면 합을 계산한다

```python
for i in range(n):
    for j in range(i + 1, n):
        work()
```

안쪽은 n-1, n-2, ..., 0 번 돈다. 합은 n(n-1)/2 이고 이는 Θ(n²) 이다. "삼각형 루프" 도 결국 제곱이다. 절반으로 줄었다고 복잡도 클래스가 바뀌지는 않는다.

### 규칙 3. 매번 절반으로 줄면 로그다

```python
k = n
while k > 1:
    k //= 2
```

k 는 n, n/2, n/4, ... 로 줄어 약 log₂ n 번 뒤에 1 이 된다. 반대로 `k *= 2` 로 n 까지 늘려도 같다. 이진 탐색, 균형 트리, 힙 연산이 모두 이 패턴이다.

### 규칙 4. 숨은 비용을 찾는다

| 겉보기 | 실제 비용 (CPython 리스트 기준) |
|---|---|
| `x in some_list` | O(n) 선형 탐색 |
| `x in some_set` | 평균 O(1) 해시 조회 |
| `lst.insert(0, x)` | O(n) 원소 이동 |
| `lst[a:b]` | O(b-a) 복사 |
| `s = s + t` (반복) | 매번 새 문자열 복사 → 누적 O(n²) 가능 |

루프 안에서 이것들을 쓰면 한 단계씩 곱해진다. `for x in a: if x in b:` 는 b 가 리스트면 O(|a|·|b|) 이다.

### 재귀는 점화식으로

병합 정렬은 반으로 나눠 두 번 재귀하고, 합치는 데 선형 시간이 든다.

```
T(n) = 2T(n/2) + Θ(n)
```

재귀 트리를 그리면 이렇다.

```
레벨 0:            n                     → 합 n
레벨 1:       n/2      n/2               → 합 n
레벨 2:   n/4  n/4  n/4  n/4             → 합 n
 ...                                     
레벨 log n: 1 1 1 ... 1 (n개)            → 합 n
```

레벨이 log n + 1 개, 각 레벨 합이 n 이므로 T(n) = Θ(n log n).

### 마스터 정리

T(n) = aT(n/b) + f(n) 꼴(a ≥ 1, b > 1)이면 f(n) 을 n^(log_b a) 와 비교한다.

| 경우 | 조건 | 결과 |
|---|---|---|
| 1 | f(n) = O(n^(log_b a − ε)), ε > 0 | Θ(n^(log_b a)) — 잎이 지배 |
| 2 | f(n) = Θ(n^(log_b a)) | Θ(n^(log_b a) · log n) — 균형 |
| 3 | f(n) = Ω(n^(log_b a + ε)) 이고 정규성 조건 | Θ(f(n)) — 뿌리가 지배 |

예시:

- 이진 탐색 T(n) = T(n/2) + Θ(1): a=1, b=2, n^0 = 1. 경우 2 → Θ(log n).
- 병합 정렬 T(n) = 2T(n/2) + Θ(n): n^1 과 같음. 경우 2 → Θ(n log n).
- T(n) = 8T(n/2) + Θ(n²) (단순 분할 행렬 곱): n^3 이 n² 보다 큼. 경우 1 → Θ(n³).

마스터 정리에 안 맞는 꼴(T(n) = T(n−1) + n 등)은 직접 펼치거나 재귀 트리로 푼다. T(n) = T(n−1) + n 을 펼치면 n + (n−1) + ... + 1 = Θ(n²) 이다.

## 직접 해 보기

같은 문제(리스트에 중복이 있는가)를 두 방식으로 풀고, n 을 두 배씩 늘려 본다. Θ(n²) 이면 시간이 약 4배, Θ(n) 이면 약 2배가 되어야 한다.

```python
import timeit

def has_dup_quadratic(xs):
    n = len(xs)
    for i in range(n):
        for j in range(i + 1, n):
            if xs[i] == xs[j]:
                return True
    return False

def has_dup_set(xs):
    seen = set()
    for x in xs:
        if x in seen:
            return True
        seen.add(x)
    return False

for n in [1000, 2000, 4000]:
    data = list(range(n))          # 중복 없음 = 최악의 입력
    t1 = timeit.timeit(lambda: has_dup_quadratic(data), number=1)
    t2 = timeit.timeit(lambda: has_dup_set(data), number=1)
    print(f"n={n:5d}  quadratic={t1:.4f}s  set={t2:.6f}s")
```

필자 환경에서 한 번 돌린 결과다. 절대값은 기계마다 다르니 비율만 보면 된다.

```
n= 1000  quadratic=0.0432s  set=0.000088s
n= 2000  quadratic=0.1985s  set=0.000513s
n= 4000  quadratic=1.1343s  set=0.000771s
```

이중 루프는 n 이 두 배가 될 때마다 대략 4~5배 느려진다. 집합 버전은 시간이 너무 짧아 잡음이 크지만 증가 폭이 훨씬 작다. 이 "두 배 실험(doubling experiment)" 은 분석 결과를 확인하는 가장 싼 방법이다. 측정은 `timeit` 처럼 반복·타이머를 관리해 주는 도구로 하는 게 좋다.

## 현업에서는

- **ORM 의 N+1 쿼리.** 목록 n 개를 가져온 뒤 루프 안에서 하나씩 연관 데이터를 조회하면 쿼리가 n+1 번 나간다. 쿼리 하나의 왕복 비용이 커서 n 이 수백만 되기 전에 이미 체감된다. 복잡도 분석은 CPU 연산만이 아니라 "네트워크 왕복 횟수" 에도 그대로 적용된다.
- **실행 계획 읽기.** PostgreSQL `EXPLAIN` 의 Nested Loop 와 Hash Join 차이는 위의 이중 루프와 집합 버전 차이와 같은 구조다.
- **운영 스크립트.** 클러스터의 모든 파드에 대해 모든 이벤트를 다시 훑는 스크립트는 파드 수 × 이벤트 수다. 파드가 수십 개일 때는 몰라도 수천 개면 문제가 된다. 한 번 훑어 딕셔너리로 묶는 쪽으로 바꾸면 선형이 된다.

## 확인 문제

1. 다음 코드의 복잡도는? `for i in range(n): j = 1; while j < n: j *= 2`
2. `result = []; for x in a: if x not in result: result.append(x)` 의 최악 복잡도는? (a 의 길이 n)
3. T(n) = 4T(n/2) + n 을 마스터 정리로 풀어라.
4. T(n) = 2T(n−1) + 1, T(0)=1 의 해는 어떤 성장률인가?

### 풀이

1. 바깥 n 번 × 안쪽 log n 번 = Θ(n log n).
2. `not in result` 가 리스트 선형 탐색이라 Θ(n²). 순서를 유지하며 중복을 빼려면 집합을 함께 쓰거나 `dict.fromkeys(a)` 를 쓰면 Θ(n) 이다.
3. a=4, b=2, n^(log₂4) = n². f(n) = n 은 n² 보다 다항식 차이로 작으므로 경우 1, Θ(n²).
4. 펼치면 1 + 2 + 4 + ... + 2ⁿ = 2ⁿ⁺¹ − 1, 즉 Θ(2ⁿ). 하노이 탑과 같은 꼴이다.

## 더 읽을거리 (References)

- Python 공식 문서, [timeit — Measure execution time of small code snippets](https://docs.python.org/3/library/timeit.html)
- PostgreSQL 공식 문서, [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- MIT OpenCourseWare, [Introduction to Algorithms, Spring 2020](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022, 4장 (점화식과 마스터 정리).
