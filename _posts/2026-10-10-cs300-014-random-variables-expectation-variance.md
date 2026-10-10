---
layout: post
title: "[CS300 #014] 확률변수·기댓값·분산 — 불확실한 값을 숫자 두 개로 요약하기"
date: 2026-10-10 18:14:00 +0900
categories: [cs]
tags: [cs300, math, probability, expectation, variance]
---

컴퓨터공학 300 주제 시리즈의 014번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

확률변수는 무작위 결과에 수를 붙이는 함수다. 기댓값은 그 수의 장기 평균이고, 분산은 평균에서 얼마나 흩어지는지를 잰다. 기댓값의 선형성은 독립이 아니어도 성립해서, 복잡한 무작위 알고리즘의 평균 비용을 놀랄 만큼 쉽게 계산하게 해 준다.

## 왜 필요한가

"퀵정렬은 평균 O(n log n)" 의 "평균" 이 기댓값이다. 해시 테이블 버킷의 평균 길이, 재시도 정책의 평균 시도 횟수, 캐시 적중률, 요청 지연 시간의 평균과 흔들림이 모두 확률변수의 기댓값과 분산이다.

평균 하나만 보면 판단을 그르친다. 평균 응답 시간이 같아도 분산이 큰 서비스는 가끔 매우 느리다. 사용자가 체감하는 것은 그 "가끔" 이다. 그래서 분산과 꼬리를 함께 봐야 한다.

## 핵심 개념

### 확률변수

**확률변수** X 는 표본 공간의 각 결과에 실수를 대응시키는 함수다. 이름과 달리 "변수" 가 아니라 함수다.

- 주사위 두 개를 던져 나온 눈의 합
- 동전을 처음 앞면이 나올 때까지 던진 횟수
- 요청 하나의 응답 시간(밀리초)

값이 셀 수 있게 떨어져 있으면 **이산**, 구간 위의 실수 값이면 **연속** 확률변수다. 이산 확률변수는 각 값의 확률 P(X = x) 를 나열한 **확률질량함수(PMF)** 로 기술한다.

**지시 확률변수**는 사건 A 가 일어나면 1, 아니면 0 인 변수 I_A 다. E[I_A] = P(A) 라는 단순한 성질이 아래에서 큰 힘을 발휘한다.

### 기댓값

```
E[X] = Σ x · P(X = x)
```

가능한 값을 확률로 가중 평균한 것이다. 공정한 주사위 눈의 기댓값은 (1+2+…+6)/6 = 3.5 다. 기댓값은 실제로 나올 수 없는 값일 수도 있다.

**기댓값의 선형성.** 임의의 확률변수 X, Y 와 상수 a, b 에 대해

```
E[aX + bY] = a·E[X] + b·E[Y]
```

**X 와 Y 가 독립이 아니어도 성립한다.** 이것이 핵심이다.

예: 모자 n 개를 무작위로 섞어 n 명에게 돌려줄 때, 자기 모자를 받는 사람 수의 기댓값은? 사람 i 가 자기 모자를 받으면 1 인 지시 변수 Iᵢ 를 두면 E[Iᵢ] = 1/n 이다. 사건들은 서로 종속이지만 선형성 덕분에 E[ΣIᵢ] = n · (1/n) = 1 이다. n 이 10 이든 백만이든 평균 1 명이다.

### 분산과 표준편차

```
Var(X) = E[(X − E[X])²] = E[X²] − (E[X])²
σ = √Var(X)
```

분산은 평균에서 벗어난 거리의 제곱을 평균한 것이다. 표준편차 σ 는 원래 단위로 돌아온 흩어짐의 크기다.

| 성질 | 식 | 조건 |
|---|---|---|
| 상수배 | Var(aX + b) = a²·Var(X) | 항상 |
| 합 | Var(X + Y) = Var(X) + Var(Y) | X, Y 가 독립(또는 무상관)일 때만 |
| 곱의 기댓값 | E[XY] = E[X]·E[Y] | X, Y 가 독립일 때 |

기댓값과 달리 분산의 덧셈은 독립이 필요하다. 독립이 아니면 공분산 항 2·Cov(X, Y) 가 붙는다.

### 기하분포: "될 때까지" 의 기댓값

성공 확률 p 인 시도를 성공할 때까지 반복할 때 시도 횟수 X 는 기하분포를 따른다. E[X] = 1/p, Var(X) = (1−p)/p² 이다.

> **유도.** 첫 시도가 성공하면(확률 p) 1 번, 실패하면(확률 1−p) 이미 1 번 썼고 처음 상태로 돌아간다. 따라서 E[X] = p·1 + (1−p)(1 + E[X]). 풀면 E[X] = 1/p. ∎

요청이 10% 확률로 실패하고 성공할 때까지 재시도하면 평균 시도는 1/0.9 ≈ 1.11 번이다. 실패율 50% 면 평균 2 번이다.

### 쿠폰 수집 문제

n 종류의 쿠폰을 무작위로 하나씩 받을 때 모두 모으려면 평균 몇 번 받아야 하는가? 이미 k 종류를 모은 상태에서 새 종류를 받을 확률은 (n−k)/n 이므로, 다음 새 종류까지는 평균 n/(n−k) 번 걸린다(기하분포). 선형성으로 더하면

```
E[전체] = n/n + n/(n−1) + ... + n/1 = n · Hₙ ≈ n ln n
```

Hₙ 은 조화수다. 부하 분산에서 "요청을 무작위로 뿌릴 때 모든 서버가 적어도 하나씩 받으려면" 같은 질문이 이 모양이다.

### 마르코프와 체비쇼프 부등식

분포를 몰라도 꼬리 확률의 상한을 줄 수 있다.

- **마르코프**: X ≥ 0 이면 P(X ≥ a) ≤ E[X] / a.
- **체비쇼프**: 평균이 μ, 표준편차가 σ 이면 P(X ≤ μ − kσ 또는 X ≥ μ + kσ) ≤ 1/k².

체비쇼프에 따르면 어떤 분포든 평균에서 표준편차 3 배 이상 벗어날 확률은 1/9 이하다. 상한이 느슨하지만 분포 가정이 전혀 필요 없다는 것이 장점이다.

## 직접 해 보기

모자 문제와 쿠폰 수집 문제를 시뮬레이션해 이론값과 비교한다. 표본 평균과 분산은 `statistics` 모듈로 계산한다.

```python
import random, statistics, math

random.seed(7)

# 1) 모자 문제: 자기 모자를 받는 사람 수의 평균은 n 과 무관하게 1
def hats(n):
    perm = list(range(n))
    random.shuffle(perm)
    return sum(1 for i, h in enumerate(perm) if i == h)
for n in [5, 50, 500]:
    xs = [hats(n) for _ in range(20000)]
    print(n, round(statistics.mean(xs), 3), round(statistics.pvariance(xs), 3))

# 2) 쿠폰 수집: 이론값 n * H_n
def collect(n):
    seen, t = set(), 0
    while len(seen) < n:
        seen.add(random.randrange(n))
        t += 1
    return t
n = 50
sim = statistics.mean(collect(n) for _ in range(5000))
theory = n * sum(1 / k for k in range(1, n + 1))
print(round(sim, 1), round(theory, 1), round(n * math.log(n), 1))

# 3) 주사위의 기댓값과 분산(정확히)
faces = range(1, 7)
mu = sum(faces) / 6
var = sum((x - mu) ** 2 for x in faces) / 6
print(mu, round(var, 4), round(math.sqrt(var), 4))
```

실행 결과 예시다(난수 시드에 따라 소수점 아래가 조금 달라질 수 있다).

```
5 1.0 0.999
50 0.997 1.007
500 1.004 1.009
226.2 225.0 195.6
3.5 2.9167 1.7078
```

모자 문제는 n 과 상관없이 평균 1, 분산도 약 1 이다. 쿠폰 수집은 시뮬레이션이 이론값 n·Hₙ ≈ 225 와 맞는다. 근사 n ln n ≈ 196 과 차이가 나는 것은 Hₙ ≈ ln n + 0.577 이기 때문이다.

## 현업에서는

- **평균만 보면 안 된다.** 프로메테우스 문서는 지연 시간 같은 값의 분위수를 히스토그램이나 요약(summary)으로 계산하는 방법과 둘의 차이를 설명한다([Prometheus, Histograms and summaries](https://prometheus.io/docs/practices/histograms/)). 평균은 이상값 몇 개에 끌려가고, 분산이 큰 꼬리를 숨긴다. SLO 를 p99 같은 분위수로 정의하는 이유다.
- **재시도 비용 추정.** 실패율 p 인 호출을 성공할 때까지 재시도하면 평균 호출 수는 1/(1−p) 다. 실패율이 1% 에서 50% 로 오르면 하위 서비스로 가는 부하는 약 두 배가 된다. 장애 상황에서 재시도가 부하를 키우는 메커니즘이 이 식에 들어 있다.
- **무작위 알고리즘 분석.** 퀵정렬의 평균 비교 횟수는 "원소 i 와 j 가 비교되면 1" 인 지시 변수들의 기댓값 합으로 구한다. 쌍들이 서로 종속이지만 선형성 덕분에 계산이 쉬워진다. 알고리즘 파트에서 다시 쓴다.
- **오토스케일링.** 쿠버네티스 HPA 는 파드들의 메트릭 평균을 목표값과 비교해 레플리카 수를 정한다([Kubernetes, Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)). 부하의 분산이 크면 평균은 목표 안에 있어도 일부 파드는 과부하일 수 있다.

## 확인 문제

1. 주사위 두 개 눈의 합의 기댓값은? 분산은?
2. 성공 확률 0.2 인 시도를 성공할 때까지 반복하면 평균 몇 번 시도하는가?
3. n 명이 각자 1 부터 365 중 생일을 무작위로 가질 때, 생일이 같은 쌍의 수의 기댓값은?
4. 평균 응답 시간이 100ms 인 서비스에서, 분포를 모른다면 응답 시간이 1 초 이상일 확률의 상한은?

### 풀이

1. 기댓값 3.5 + 3.5 = 7. 두 주사위가 독립이므로 분산 2.9167 × 2 ≈ 5.833.
2. 1 / 0.2 = 5 번.
3. 쌍마다 같은 생일이면 1 인 지시 변수를 두면 E = C(n, 2) / 365. n = 28 이면 약 1.04 로, 이 무렵부터 같은 생일 쌍이 평균 하나 이상 생긴다.
4. 응답 시간은 0 이상이므로 마르코프 부등식으로 100 / 1000 = 0.1 이하.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 19장 Random Variables, 20장 Deviation from the Mean — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Python Documentation, statistics — Mathematical statistics functions](https://docs.python.org/3/library/statistics.html)
- [Prometheus Documentation, Histograms and summaries](https://prometheus.io/docs/practices/histograms/)
- Michael Mitzenmacher, Eli Upfal, *Probability and Computing*, 2판, Cambridge University Press, 2–3장
