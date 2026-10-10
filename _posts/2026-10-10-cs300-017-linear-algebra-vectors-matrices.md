---
layout: post
title: "[CS300 #017] 선형대수 1 — 벡터·행렬·연립방정식"
date: 2026-10-10 18:17:00 +0900
categories: [cs]
tags: [cs300, math, linear-algebra, matrix, numpy]
---

컴퓨터공학 300 주제 시리즈의 017번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

벡터는 수의 목록이자 공간의 화살표이고, 행렬은 벡터를 다른 벡터로 보내는 선형 변환이다. 연립일차방정식 Ax = b 는 "어떤 입력이 이 출력을 만드는가" 를 묻는 문제이며, 가우스 소거법으로 풀고 계수(rank)로 해의 개수를 판정한다.

## 왜 필요한가

그래픽스의 회전·이동·투영, 머신러닝의 모든 층, 추천 시스템의 임베딩, 검색 엔진의 페이지 순위, 회로와 네트워크 흐름 해석이 모두 행렬 계산이다. GPU 가 잘하는 일도 결국 큰 행렬 곱셈이다.

선형대수를 알면 "이 데이터 처리 코드는 사실 행렬 곱 하나" 라는 것이 보이고, 반복문 세 겹을 라이브러리 호출 한 줄로 바꿔 훨씬 빠르게 만들 수 있다. 반대로 모르면 역행렬을 직접 구하는 것 같은, 느리고 수치적으로 불안정한 코드를 쓰게 된다.

## 핵심 개념

### 벡터

n 차원 벡터는 실수 n 개의 순서 있는 목록 v = (v₁, …, vₙ) 이다. 2·3 차원에서는 원점에서 뻗은 화살표로 그릴 수 있다.

| 연산 | 정의 | 뜻 |
|---|---|---|
| 덧셈 | u + v = (u₁+v₁, …, uₙ+vₙ) | 화살표 이어 붙이기 |
| 스칼라배 | c·v = (cv₁, …, cvₙ) | 길이를 c 배 |
| 내적 | u·v = u₁v₁ + … + uₙvₙ | 같은 방향 성분의 곱 |
| 노름(길이) | ‖v‖ = √(v·v) | 화살표 길이 |

내적에는 기하학적 의미가 있다. u·v = ‖u‖‖v‖cos θ 다. 그래서 내적이 0 이면 두 벡터는 **직교**한다. 길이로 나눈 값 cos θ 가 **코사인 유사도**이며, 문서·임베딩 검색에서 "얼마나 같은 방향인가" 를 재는 표준 척도다.

### 일차결합, 생성, 일차독립

c₁v₁ + c₂v₂ + … + cₖvₖ 꼴을 **일차결합**이라 한다. 벡터들의 모든 일차결합이 이루는 집합을 그 벡터들이 **생성하는 공간(span)** 이라 한다.

어떤 벡터도 나머지의 일차결합으로 쓸 수 없으면 **일차독립**이다. 같은 말로, c₁v₁ + … + cₖvₖ = 0 이 되는 계수가 모두 0 뿐이다. 일차독립이면서 공간 전체를 생성하는 벡터 묶음이 **기저**이고, 기저의 원소 수가 **차원**이다.

### 행렬과 행렬 곱

m×n 행렬 A 는 n 차원 벡터를 받아 m 차원 벡터를 내는 함수 x ↦ Ax 로 볼 수 있다. 이 함수는 **선형**이다: A(x + y) = Ax + Ay, A(cx) = c·Ax.

Ax 를 보는 두 관점이 있다.

```
행 관점:  (Ax)ᵢ = A 의 i 번째 행 · x          (내적 m 번)
열 관점:  Ax = x₁·(1열) + x₂·(2열) + ... + xₙ·(n열)   (열들의 일차결합)
```

열 관점이 더 중요하다. Ax = b 가 해를 갖는다는 것은 "b 가 A 의 열들의 일차결합으로 쓰인다", 즉 b 가 A 의 **열공간**에 있다는 뜻이다.

행렬 곱 AB 는 "B 를 먼저 하고 A 를 하는" 함수 합성이다. 그래서

- (AB)C = A(BC) 결합 법칙은 성립한다.
- AB ≠ BA 일 수 있다. 회전한 뒤 한 방향으로 늘리는 것과, 늘린 뒤 회전하는 것은 다르다(아래 예제).
- (m×n)(n×p) 는 m×p 이고, 단순 구현의 곱셈 횟수는 m·n·p 번이다.

### 연립일차방정식과 가우스 소거법

```
 2x +  y −  z =   8
−3x −  y + 2z = −11
−2x +  y + 2z =  −3
```

는 Ax = b 다. **가우스 소거법**은 세 가지 행 연산(행 바꾸기, 행에 0 아닌 수 곱하기, 한 행의 배수를 다른 행에 더하기)으로 A 를 위삼각 형태로 만든 뒤, 아래 행부터 거꾸로 대입한다. 행 연산은 해를 바꾸지 않는다. 위 식의 해는 x = 2, y = 3, z = −1 이다. n×n 행렬에서 비용은 대략 n³ 에 비례한다.

### 해의 개수와 계수

행렬의 **계수(rank)** 는 일차독립인 열(또는 행)의 최대 개수, 즉 열공간의 차원이다. n 개의 미지수가 있는 Ax = b 에 대해

| 상황 | 해 |
|---|---|
| rank(A) < rank([A b]) | 해 없음 (b 가 열공간 밖) |
| rank(A) = rank([A b]) = n | 해가 하나 |
| rank(A) = rank([A b]) < n | 해가 무수히 많음 |

정사각 행렬 A 가 계수 n(최대 계수)이면 **가역**이고 역행렬 A⁻¹ 이 있으며 행렬식 det(A) ≠ 0 이다. 이 조건들은 모두 동치다.

### 역행렬을 직접 구하지 말 것

수학적으로는 x = A⁻¹b 지만, 수치 계산에서는 역행렬을 구하지 않고 `solve` 로 바로 푼다. 역행렬을 구하는 것이 더 느리고 반올림 오차도 더 크기 때문이다. NumPy 의 `numpy.linalg.solve` 는 역행렬을 만들지 않고 LAPACK 의 gesv 루틴(LU 분해 기반)으로 해를 바로 구한다([NumPy, numpy.linalg.solve](https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html)). 또 거의 특이한(조건수가 큰) 행렬은 입력의 작은 오차를 크게 키운다.

## 직접 해 보기

위 연립방정식을 순수 파이썬 가우스 소거로 풀고 NumPy 와 비교한다. 이어서 행렬 곱이 교환되지 않는 것, 코사인 유사도, 계수로 해의 개수를 판정하는 것을 확인한다.

```python
import numpy as np

def gauss_solve(A, b):
    n = len(A)
    M = [row[:] + [bi] for row, bi in zip(A, b)]          # 첨가 행렬
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))   # 부분 피벗팅
        M[col], M[pivot] = M[pivot], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            M[r] = [a - f * c for a, c in zip(M[r], M[col])]
    x = [0.0] * n
    for i in reversed(range(n)):                            # 뒤로 대입
        x[i] = (M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))) / M[i][i]
    return x

A = [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]
b = [8, -11, -3]
print([round(v, 6) for v in gauss_solve(A, b)])
print(np.linalg.solve(np.array(A, float), np.array(b, float)))

# 회전과 확대: 순서를 바꾸면 결과가 다르다
R = np.array([[0, -1], [1, 0]])        # 90도 회전
S = np.array([[2, 0], [0, 1]])         # x 방향 2배
print((R @ S).tolist(), (S @ R).tolist())

# 코사인 유사도
u, v = np.array([1.0, 2.0, 3.0]), np.array([2.0, 4.0, 6.5])
print(round(float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v))), 4))

# 계수로 해의 개수 판정
A2 = np.array([[1, 2], [2, 4]], float)
for b2 in ([3, 6], [3, 7]):
    aug = np.column_stack([A2, b2])
    print(b2, np.linalg.matrix_rank(A2), np.linalg.matrix_rank(aug))
```

실행 결과다.

```
[2.0, 3.0, -1.0]
[ 2.  3. -1.]
[[0, -1], [2, 0]] [[0, -2], [1, 0]]
0.9993
[3, 6] 1 1
[3, 7] 1 2
```

마지막 두 줄에서 A2 의 두 열은 평행해서 계수가 1 이다. b = (3, 6) 은 열공간 위에 있어 해가 무수히 많고(계수 1 < 미지수 2), b = (3, 7) 은 열공간 밖이라 해가 없다.

## 현업에서는

- **벡터화.** 파이썬 반복문으로 행렬 곱을 짜는 것과 NumPy 의 `@` 연산자를 쓰는 것은 큰 행렬에서 속도 차이가 매우 크다. NumPy 의 선형대수 함수는 BLAS·LAPACK 같은 최적화된 라이브러리를 호출한다([NumPy, Linear algebra](https://numpy.org/doc/stable/reference/routines.linalg.html)).
- **임베딩 검색.** 문장·이미지를 벡터로 바꾼 뒤 코사인 유사도가 높은 것을 찾는 것이 벡터 검색의 기본이다. 벡터를 미리 길이 1 로 정규화하면 코사인 유사도는 내적 하나가 된다.
- **그래픽스 변환.** 회전·확대·이동(동차 좌표를 쓰면 이동도 행렬이 된다)을 행렬로 표현하고 곱해서 하나로 합친다. 곱하는 순서가 결과를 바꾸므로, 변환 순서 버그는 대개 행렬 곱 순서 버그다.
- **최소제곱.** 방정식보다 데이터가 많아 정확한 해가 없을 때(rank(A) < rank([A b])) 오차 제곱합을 최소로 하는 근사해를 구한다. 선형 회귀가 바로 이것이며 `numpy.linalg.lstsq` 로 푼다.

## 확인 문제

1. u = (1, 2), v = (−2, 1) 의 내적은? 두 벡터의 관계는?
2. (3×5) 행렬과 (5×2) 행렬의 곱의 크기는? 단순 구현의 곱셈 횟수는?
3. 벡터 (1, 0, 1), (0, 1, 1), (1, 1, 2) 는 일차독립인가?
4. 4×4 행렬 A 의 행렬식이 0 이다. Ax = b 의 해에 대해 무엇을 말할 수 있는가?

### 풀이

1. −2 + 2 = 0. 직교한다.
2. 3×2. 3·5·2 = 30 번.
3. 아니다. 셋째 벡터가 첫째와 둘째의 합이다.
4. A 는 가역이 아니고 계수가 4 보다 작다. b 에 따라 해가 없거나 무수히 많다. 유일한 해는 없다.

## 더 읽을거리 (References)

- [MIT OpenCourseWare, 18.06 Linear Algebra (Gilbert Strang)](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)
- [NumPy Documentation, Linear algebra (numpy.linalg)](https://numpy.org/doc/stable/reference/routines.linalg.html)
- [NumPy Documentation, numpy.linalg.solve](https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html)
- Gilbert Strang, *Introduction to Linear Algebra*, 6판, Wellesley-Cambridge Press
