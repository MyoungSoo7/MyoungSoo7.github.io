---
layout: post
title: "[CS300 #018] 선형대수 2 — 고유값·고유벡터·특이값 분해"
date: 2026-10-10 18:18:00 +0900
categories: [cs]
tags: [cs300, math, linear-algebra, eigenvalue, svd]
---

컴퓨터공학 300 주제 시리즈의 018번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

고유벡터는 행렬을 곱해도 방향이 바뀌지 않고 길이만 고유값 배로 변하는 특별한 벡터다. 특이값 분해(SVD)는 모든 행렬을 "회전 → 축 방향 늘리기 → 회전" 으로 쪼개며, 데이터에서 가장 중요한 방향을 찾고 차원을 줄이는 도구가 된다.

## 왜 필요한가

행렬을 반복해서 곱하는 과정, 즉 어떤 상태가 같은 규칙으로 계속 변하는 과정의 장기 행동은 고유값이 결정한다. 웹 페이지 순위(PageRank), 마르코프 체인의 정상 상태, 진동 해석, 그래프의 군집 구조가 모두 고유값 문제다.

SVD 는 더 넓게 쓰인다. 주성분 분석(PCA), 추천 시스템의 행렬 분해, 이미지 압축, 잡음 제거, 최소제곱의 안정적 풀이, 잠재 의미 분석이 SVD 위에 서 있다. "데이터에서 진짜 중요한 몇 개의 축만 남긴다" 는 생각의 수학적 형태가 SVD 다.

## 핵심 개념

### 고유값과 고유벡터

정사각 행렬 A 에 대해

```
A v = λ v,   v ≠ 0
```

을 만족하는 수 λ 를 **고유값**, 벡터 v 를 그에 대응하는 **고유벡터**라 한다. 대부분의 벡터는 A 를 곱하면 방향이 바뀌지만, 고유벡터는 같은 직선 위에 머문다.

예: A = [[2, 0], [0, 3]] 은 x 축 방향을 2 배, y 축 방향을 3 배 늘린다. (1, 0) 은 고유값 2, (0, 1) 은 고유값 3 의 고유벡터다.

### 구하는 법: 특성 방정식

Av = λv 는 (A − λI)v = 0 이다. 0 이 아닌 해 v 가 있으려면 A − λI 가 가역이 아니어야 하므로

```
det(A − λI) = 0
```

이 λ 에 대한 n 차 다항식(특성 다항식)의 근이 고유값이다. 2×2 행렬 [[a, b], [c, d]] 면 λ² − (a+d)λ + (ad − bc) = 0 이다. 고유값의 합은 대각합(trace), 곱은 행렬식이다.

008번 글에서 점화식을 풀 때 쓴 "특성 방정식" 과 같은 것이다. 피보나치 점화식을 행렬 [[1, 1], [1, 0]] 로 쓰면 그 고유값이 φ 와 ψ 다.

### 대각화와 거듭제곱

n×n 행렬 A 가 일차독립인 고유벡터 n 개를 가지면, 고유벡터를 열로 모은 P 와 고유값을 대각에 놓은 D 로

```
A = P D P⁻¹,     Aᵏ = P Dᵏ P⁻¹
```

로 쓸 수 있다. Dᵏ 는 대각 원소를 k 제곱하기만 하면 되므로, Aᵏx 의 장기 행동은 **절댓값이 가장 큰 고유값**이 지배한다. 그 고유값이 1 보다 크면 발산, 1 보다 작으면 0 으로 수렴, 정확히 1 이면 정상 상태로 간다.

**대칭 행렬**(A = Aᵀ)은 특히 좋다. 고유값이 모두 실수이고, 서로 직교하는 고유벡터로 대각화된다(스펙트럼 정리). 공분산 행렬, 무향 그래프의 인접 행렬이 대칭이다.

### 거듭제곱법과 PageRank

큰 행렬의 지배 고유벡터는 "아무 벡터에서 시작해 A 를 계속 곱하고 정규화한다" 는 **거듭제곱법**으로 구한다. 지배 고유값이 나머지보다 확실히 크면 빠르게 수렴한다.

PageRank 는 웹을 유향 그래프로 보고, 무작위로 링크를 따라가는 사용자가 오래 머문 뒤 각 페이지에 있을 확률을 순위로 쓴다. 이는 전이 행렬의 고유값 1 에 대응하는 고유벡터(정상 분포)다. 브린과 페이지의 원 논문은 이 순위가 정규화된 링크 행렬의 주 고유벡터에 해당한다고 설명한다([Brin & Page, The Anatomy of a Large-Scale Hypertextual Web Search Engine](http://infolab.stanford.edu/~backrub/google.html)).

### 특이값 분해(SVD)

고유값 분해는 정사각 행렬에만, 그것도 일부에만 된다. SVD 는 **모든 m×n 행렬**에 된다.

```
A = U Σ Vᵀ
U: m×m 직교 행렬(열이 왼쪽 특이벡터)
Σ: m×n 대각 행렬, 대각 원소 σ₁ ≥ σ₂ ≥ ... ≥ 0 (특이값)
V: n×n 직교 행렬(열이 오른쪽 특이벡터)
```

기하학적으로 A 는 "Vᵀ 로 회전 → Σ 로 축마다 늘리거나 줄이기 → U 로 회전" 이다. 특이값은 AᵀA 의 고유값의 제곱근이다. 0 이 아닌 특이값의 개수가 계수(rank)다.

### 저계수 근사와 PCA

SVD 를 항으로 풀면 A = σ₁u₁v₁ᵀ + σ₂u₂v₂ᵀ + … 이다. 큰 특이값 k 개의 항만 남긴 Aₖ 는 **계수가 k 인 행렬 중 A 와 가장 가까운 행렬**이다(에카르트-영 정리). 버린 정보의 크기는 버린 특이값들로 정확히 알 수 있다.

**주성분 분석(PCA)** 은 각 열의 평균을 뺀 데이터 행렬에 SVD 를 적용한 것이다. 오른쪽 특이벡터가 데이터가 가장 넓게 퍼진 방향(주성분)이고, 특이값의 제곱이 그 방향의 분산에 비례한다. scikit-learn 의 PCA 문서도 데이터를 중심화한 뒤 SVD 로 주성분을 구한다고 설명한다([scikit-learn, PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)).

| 도구 | 대상 | 결과 | 대표 용도 |
|---|---|---|---|
| 고유값 분해 | 정사각(대각화 가능) | A = PDP⁻¹ | 반복 과정의 장기 행동, 진동, 마르코프 체인 |
| 대칭 고유값 분해 | 대칭 행렬 | A = QDQᵀ (Q 직교) | 공분산, 그래프 라플라시안 |
| SVD | 모든 행렬 | A = UΣVᵀ | PCA, 압축, 추천, 최소제곱 |

## 직접 해 보기

작은 웹 그래프의 PageRank 를 거듭제곱법으로 구하고 NumPy 의 고유값 분해와 비교한다. 이어서 SVD 로 잡음 섞인 저계수 행렬을 복원해 본다.

```python
import numpy as np

# 1) 페이지 4 개의 링크: 0->1,2 / 1->2 / 2->0 / 3->2
links = {0: [1, 2], 1: [2], 2: [0], 3: [2]}
n, d = 4, 0.85
M = np.zeros((n, n))
for src, dsts in links.items():
    for dst in dsts:
        M[dst, src] = 1 / len(dsts)          # 열 확률 행렬
G = d * M + (1 - d) / n * np.ones((n, n))   # 감쇠 계수를 넣은 구글 행렬

r = np.ones(n) / n
for _ in range(100):
    r = G @ r
print("거듭제곱법:", np.round(r, 4))

w, V = np.linalg.eig(G)
k = np.argmax(np.abs(w))
v = np.real(V[:, k]); v = v / v.sum()
print("고유벡터  :", np.round(v, 4), "고유값", np.round(np.real(w[k]), 4))

# 2) SVD 저계수 근사: 계수 2 행렬 + 잡음
rng = np.random.default_rng(0)
low = rng.normal(size=(50, 2)) @ rng.normal(size=(2, 30))
noisy = low + 0.1 * rng.normal(size=low.shape)
U, s, Vt = np.linalg.svd(noisy, full_matrices=False)
print("특이값 앞 5개:", np.round(s[:5], 2))
A2 = U[:, :2] @ np.diag(s[:2]) @ Vt[:2]
err = lambda X: np.linalg.norm(X - low) / np.linalg.norm(low)
print("잡음 행렬 오차:", round(err(noisy), 4), " 계수2 근사 오차:", round(err(A2), 4))
```

실행 결과다.

```
거듭제곱법: [0.3725 0.1958 0.3941 0.0375]
고유벡터  : [0.3725 0.1958 0.3941 0.0375] 고유값 1.0
특이값 앞 5개: [43.33 28.86  1.13  1.06  1.06]
잡음 행렬 오차: 0.0743  계수2 근사 오차: 0.0254
```

거듭제곱법과 고유값 분해가 같은 순위를 낸다. 지배 고유값은 정확히 1 이다. 아무도 링크하지 않는 페이지 3 이 가장 낮고, 세 페이지가 가리키는 페이지 2 가 가장 높다.

SVD 에서는 특이값이 두 개만 크고 나머지는 잡음 수준이다. 큰 두 개만 남기면 잡음 섞인 원본보다 진짜 행렬에 더 가까워진다. 차원 축소가 잡음 제거가 되는 이유다.

## 현업에서는

- **추천 시스템.** 사용자×아이템 평점 행렬을 저계수 행렬 두 개의 곱으로 근사하는 행렬 분해는 SVD 의 발상을 확장한 것이다. 각 사용자와 아이템이 짧은 벡터(잠재 요인)로 요약되고, 그 내적이 예상 평점이 된다.
- **차원 축소와 시각화.** 수백 차원 메트릭이나 임베딩을 PCA 로 2~3 차원에 투영해 그려 보면 군집과 이상값이 눈에 들어온다. 특이값이 몇 개만 크다면 데이터가 실제로는 저차원이라는 신호다.
- **대칭 행렬 전용 함수.** `numpy.linalg.eig` 는 일반 행렬용이고, 실수 대칭(또는 에르미트) 행렬에는 `eigh` 가 따로 있다([NumPy, numpy.linalg.eig](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eig.html)). 공분산 행렬처럼 대칭임을 아는 경우 `eigh` 를 쓴다.
- **그래프 분석.** 그래프 라플라시안의 작은 고유값에 대응하는 고유벡터로 정점을 나누는 스펙트럴 군집화는 서비스 의존성 그래프나 소셜 그래프에서 덩어리를 찾는 데 쓰인다.

## 확인 문제

1. A = [[4, 1], [2, 3]] 의 고유값을 구하라.
2. 고유값이 0.5 와 0.9 인 2×2 행렬 A 에 대해 Aᵏx 는 k 가 커지면 어떻게 되는가?
3. 5×3 행렬의 0 이 아닌 특이값은 최대 몇 개인가?
4. 특이값이 [10, 5, 0.01, 0.01] 인 행렬을 계수 2 로 근사하면 무엇을 잃는가?

### 풀이

1. λ² − 7λ + 10 = 0 이므로 λ = 5, 2.
2. 모든 고유값의 절댓값이 1 보다 작으므로 0 벡터로 수렴한다. 수렴 속도는 0.9 쪽이 결정한다.
3. 계수는 min(5, 3) = 3 이하이므로 최대 3 개.
4. 크기 0.01 짜리 두 성분뿐이다. 행렬의 거의 모든 정보(에너지)를 보존한다.

## 더 읽을거리 (References)

- [MIT OpenCourseWare, 18.06 Linear Algebra (Gilbert Strang)](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)
- [NumPy Documentation, numpy.linalg.svd](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html)
- Sergey Brin, Lawrence Page, [The Anatomy of a Large-Scale Hypertextual Web Search Engine](http://infolab.stanford.edu/~backrub/google.html), 1998
- [scikit-learn Documentation, sklearn.decomposition.PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
