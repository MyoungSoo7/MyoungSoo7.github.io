---
layout: post
title: "[CS300 #066] 퀵 정렬과 피벗 선택 — 평균은 빠르고 최악은 피하는 법"
date: 2026-10-10 19:06:00 +0900
categories: [cs]
tags: [cs300, algorithms, sorting, quicksort, randomization]
---

컴퓨터공학 300 주제 시리즈의 066번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

퀵 정렬은 피벗 하나를 골라 작은 것은 왼쪽, 큰 것은 오른쪽으로 나눈 뒤 양쪽을 재귀로 정렬한다. 평균 Θ(n log n) 에 제자리 정렬이라 빠르지만, 피벗을 잘못 고르면 Θ(n²) 이 된다. 그래서 피벗 선택이 알고리즘의 절반이다.

## 왜 필요한가

병합 정렬은 최악도 n log n 인데 왜 퀵 정렬을 따로 배울까. 실제 기계에서 퀵 정렬 계열이 빠른 경우가 많기 때문이다. 보조 배열이 필요 없고, 분할 루프가 연속된 메모리를 순서대로 훑어 캐시에 친화적이다. 주요 C++ `std::sort` 구현, Java 의 기본형 배열 정렬, Go 의 `sort` 패키지가 모두 퀵 정렬을 뼈대로 한 변형을 쓴다.

대신 약점이 분명하다. 이 약점을 이해하지 못하고 직접 구현하면 정렬된 입력 하나에 서비스가 멈출 수 있다.

## 핵심 개념

### 분할(partition)

Hoare 가 1962년에 발표한 원래 아이디어는 이렇다.

```
피벗 p = 5
[3 8 2 5 9 1 7]
 → 분할 후 [3 2 1] 5 [8 9 7]
           < p    p   > p
```

분할이 끝나면 피벗은 최종 위치에 있다. 이후 왼쪽과 오른쪽은 서로 섞일 일이 없으니 따로 정렬하면 된다. 병합 정렬이 "나누기는 쉽고 합치기가 일" 이라면, 퀵 정렬은 "나누기가 일이고 합치기는 공짜" 다.

분할 구현은 두 가지가 유명하다.

| 방식 | 특징 |
|---|---|
| Lomuto | 한 포인터로 왼쪽부터 훑는다. 코드가 짧다. 교환이 많고 같은 값이 많으면 불균형해진다. |
| Hoare | 양 끝에서 안쪽으로 두 포인터가 다가온다. 교환이 적다. 경계 처리가 까다롭다. |

### 복잡도는 피벗이 정한다

- 피벗이 매번 정확히 가운데면: T(n) = 2T(n/2) + Θ(n) = Θ(n log n).
- 피벗이 매번 최솟값이나 최댓값이면: T(n) = T(n−1) + Θ(n) = Θ(n²).
- 매번 1:9 로 갈라져도 깊이가 log_{10/9} n 이라 여전히 Θ(n log n) 이다. 극단적으로 치우치지만 않으면 된다.

"마지막 원소를 피벗" 으로 하는 교과서 구현은 이미 정렬된 입력에서 매번 최댓값을 피벗으로 고른다. 실무 데이터는 정렬되어 있거나 거의 정렬된 경우가 흔하다. 최악이 흔한 입력에서 터진다는 뜻이다.

### 피벗 고르는 법

| 전략 | 방법 | 효과 |
|---|---|---|
| 고정 위치 | 첫 원소나 마지막 원소 | 정렬된 입력에서 Θ(n²) |
| 무작위 | 구간에서 아무 위치나 | 어떤 입력이든 기대 Θ(n log n). 최악은 확률적으로 극히 드묾 |
| 세 값의 중앙값 | 처음·가운데·끝 중 가운데 값 | 정렬·역순 입력에 강함. 일부러 만든 입력에는 여전히 당할 수 있음 |
| ninther 등 | 중앙값의 중앙값 표본 | 큰 배열에서 더 좋은 피벗 |

### 최악을 원천 차단하는 하이브리드

- **introsort**: 재귀 깊이가 약 2 log n 을 넘으면 힙 정렬로 바꾼다. 최악 O(n log n) 이 보장된다. Musser 가 1997년에 제안했다.
- **pdqsort**: 나쁜 분할이 반복되면 패턴을 흐트러뜨리고, 그래도 안 되면 힙 정렬로 넘어간다. Go 1.19 의 `sort` 패키지가 도입했다.
- **3-way 분할**: 같은 값이 많을 때 `< p`, `= p`, `> p` 세 구역으로 나눠 같은 값 덩어리를 다시 정렬하지 않는다. Bentley 와 McIlroy 의 1993년 논문 "Engineering a Sort Function" 이 이 문제를 정면으로 다뤘다.
- **dual-pivot**: Java 의 기본형 배열 `Arrays.sort` 는 피벗 두 개로 세 구역을 만드는 Dual-Pivot Quicksort 를 쓴다고 공식 문서에 적혀 있다.

### 스택 깊이

재귀를 두 번 다 하면 최악에 깊이가 n 이 되어 스택이 넘친다. 작은 쪽만 재귀하고 큰 쪽은 루프로 처리하면 깊이가 O(log n) 으로 묶인다. 아래 예제가 그렇게 짰다.

### 안정성

퀵 정렬은 멀리 떨어진 원소를 교환하므로 안정 정렬이 아니다. 안정성이 필요하면 병합 정렬 계열을 쓴다. Java 가 기본형 배열에는 퀵 정렬, 객체 배열에는 안정적인 병합 정렬 계열을 쓰는 이유도 여기 있다. 기본형은 같은 값끼리 구분할 방법이 없으니 안정성이 의미가 없다.

## 직접 해 보기

같은 퀵 정렬에 피벗 전략만 바꿔 비교 횟수를 센다. python3 로 실행해 확인했다.

```python
import random

def quicksort(a, choose):
    cmp = 0
    def partition(lo, hi):               # Lomuto 분할, a[hi] 가 피벗
        nonlocal cmp
        p = a[hi]; i = lo
        for j in range(lo, hi):
            cmp += 1
            if a[j] < p:
                a[i], a[j] = a[j], a[i]; i += 1
        a[i], a[hi] = a[hi], a[i]
        return i
    def qs(lo, hi):
        while lo < hi:
            k = choose(a, lo, hi)
            a[k], a[hi] = a[hi], a[k]    # 고른 피벗을 맨 끝으로
            m = partition(lo, hi)
            if m - lo < hi - m:          # 작은 쪽만 재귀 → 스택 깊이 O(log n)
                qs(lo, m - 1); lo = m + 1
            else:
                qs(m + 1, hi); hi = m - 1
    qs(0, len(a) - 1)
    return cmp

def last(a, lo, hi):
    return hi
def rand(a, lo, hi):
    return random.randint(lo, hi)
def median3(a, lo, hi):
    mid = (lo + hi) // 2
    return sorted([lo, mid, hi], key=lambda i: a[i])[1]

random.seed(42)
n = 2000
inputs = {"random": random.sample(range(n), n), "sorted": list(range(n))}
for name, data in inputs.items():
    row = []
    for ch in (last, rand, median3):
        a = data[:]
        c = quicksort(a, ch)
        assert a == sorted(data)
        row.append(f"{ch.__name__}={c:>8}")
    print(f"{name:>7}: " + "  ".join(row))
```

출력:

```
 random: last=   24854  rand=   24673  median3=   20154
 sorted: last= 1999000  rand=   24374  median3=   17964
```

무작위 입력에서는 세 전략이 비슷하다. 정렬된 입력에서 "마지막 원소" 전략은 n(n−1)/2 = 1,999,000 번 비교한다. 정확히 최악이다. 무작위 피벗과 세 값의 중앙값은 입력이 정렬되어 있어도 n log n 수준을 지킨다. 작은 쪽만 재귀하도록 짰기 때문에 최악 입력에서도 스택은 넘치지 않았다.

## 현업에서는

- **직접 구현하지 않는다.** 표준 라이브러리 정렬은 위의 함정을 모두 처리해 두었다. 직접 짠 퀵 정렬이 운영에서 문제를 일으키는 전형적 원인이 고정 피벗과 깊은 재귀다.
- **선택(selection) 문제.** "상위 k 개", "중앙값" 처럼 정렬 전체가 필요 없을 때는 분할을 한쪽으로만 재귀하는 quickselect 가 평균 Θ(n) 이다. C++ 의 `nth_element` 가 대표적이다. 응답 시간 p99 를 구할 때 전체 정렬 대신 쓸 수 있다.
- **적대적 입력.** 사용자가 입력을 마음대로 만들 수 있는 서비스라면, 결정적 피벗 규칙은 공격 대상이 될 수 있다. 무작위화나 최악 보장 하이브리드가 방어책이다.

## 확인 문제

1. 퀵 정렬과 병합 정렬에서 "일" 이 이루어지는 단계는 각각 어디인가?
2. 모든 원소가 같은 배열을 Lomuto 분할로 정렬하면 어떻게 되는가?
3. 작은 쪽만 재귀하면 스택 깊이가 O(log n) 인 이유는?
4. Java 가 객체 배열에 퀵 정렬을 쓰지 않는 이유는?

### 풀이

1. 퀵 정렬은 분할 단계, 병합 정렬은 결합(병합) 단계.
2. `a[j] < p` 가 한 번도 참이 아니어서 피벗이 맨 왼쪽에 놓이고 매번 n−1 : 0 으로 갈라진다. Θ(n²). 3-way 분할이나 Hoare 분할이 해결책이다.
3. 재귀로 들어가는 쪽의 크기가 항상 현재 구간의 절반 이하이므로, 재귀 한 단계마다 크기가 절반 이하로 준다.
4. 객체는 같은 키라도 서로 다른 객체라서 안정성이 의미가 있다. 공식 문서도 객체 배열 정렬이 안정적임을 보장한다.

## 더 읽을거리 (References)

- C. A. R. Hoare, "Quicksort", *The Computer Journal* 5(1), 1962.
- Jon L. Bentley, M. Douglas McIlroy, "Engineering a Sort Function", *Software: Practice and Experience* 23(11), 1993.
- Orson R. L. Peters, [Pattern-defeating Quicksort](https://arxiv.org/abs/2106.05123), arXiv:2106.05123, 2021
- Java SE 21 API, [Arrays](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Arrays.html) — 기본형 정렬의 Dual-Pivot Quicksort, 객체 정렬의 안정성
