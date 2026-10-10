---
layout: post
title: "[CS300 #064] 버블·선택·삽입 정렬 — 느린 정렬 셋에서 배우는 것"
date: 2026-10-10 19:04:00 +0900
categories: [cs]
tags: [cs300, algorithms, sorting, insertion-sort, stability]
---

컴퓨터공학 300 주제 시리즈의 064번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

버블·선택·삽입 정렬은 모두 최악 Θ(n²) 이지만 성격이 다르다. 선택 정렬은 교환 횟수가 적고, 삽입 정렬은 거의 정렬된 입력에서 선형에 가깝다. 그래서 삽입 정렬만은 지금도 실전 정렬 구현 안에 살아 있다.

## 왜 필요한가

실무에서 이 셋을 직접 짤 일은 거의 없다. 그래도 배우는 이유는 세 가지다.

1. 정렬 알고리즘을 비교하는 기준(비교 횟수, 이동 횟수, 안정성, 제자리 여부, 입력 민감성)을 가장 작은 코드로 익힐 수 있다.
2. 루프 불변식(loop invariant)으로 정확성을 증명하는 연습에 딱 맞는다.
3. 삽입 정렬은 Timsort, introsort, pdqsort 같은 표준 라이브러리 정렬이 작은 구간을 처리할 때 실제로 쓴다.

## 핵심 개념

### 세 알고리즘의 동작

```
버블: 인접한 두 칸을 비교해 뒤집는다. 한 바퀴 돌면 가장 큰 값이 맨 뒤로 "떠오른다".
선택: 남은 구간에서 최솟값을 찾아 맨 앞과 한 번 바꾼다.
삽입: 왼쪽은 이미 정렬된 상태. 다음 원소를 꺼내 왼쪽에서 제자리를 찾아 끼운다.
```

삽입 정렬 한 단계를 그림으로 보면 이렇다.

```
[2 5 7 | 4 1 3]   key = 4
[2 5 _ 7 ...]     7 > 4, 오른쪽으로 민다
[2 _ 5 7 ...]     5 > 4, 오른쪽으로 민다
[2 4 5 7 | 1 3]   2 ≤ 4, 멈추고 끼운다
```

### 루프 불변식

삽입 정렬의 불변식은 "i번째 반복을 시작할 때 a[0..i−1] 은 원래 그 자리에 있던 원소들을 정렬한 것이다" 이다.

- 초기화: i = 1 일 때 a[0..0] 은 원소 하나라 정렬되어 있다.
- 유지: key 보다 큰 원소들을 오른쪽으로 한 칸씩 밀고 빈 칸에 key 를 넣으면 a[0..i] 가 정렬된다.
- 종료: i = n 이면 배열 전체가 정렬되어 있다.

이 세 단계 틀은 앞으로 나올 모든 알고리즘의 정확성 증명에 그대로 쓴다.

### 비교표

| | 최선 | 평균 | 최악 | 교환·이동 | 안정 | 제자리 |
|---|---|---|---|---|---|---|
| 버블 (조기 종료 포함) | Θ(n) | Θ(n²) | Θ(n²) | Θ(n²) | 예 | 예 |
| 선택 | Θ(n²) | Θ(n²) | Θ(n²) | 최대 n−1 번 교환 | 아니오 | 예 |
| 삽입 | Θ(n) | Θ(n²) | Θ(n²) | 역순쌍 수만큼 | 예 | 예 |

### 역순쌍(inversion)

i < j 인데 a[i] > a[j] 인 쌍을 역순쌍이라고 한다. 인접 교환 한 번은 역순쌍을 정확히 하나 없앤다. 그러므로 버블과 삽입 정렬의 교환·이동 횟수는 역순쌍 수와 같다. 무작위 배열의 평균 역순쌍 수는 n(n−1)/4 라서 평균이 Θ(n²) 이다. 거꾸로, 역순쌍이 적은 "거의 정렬된" 입력에서는 삽입 정렬이 Θ(n + 역순쌍 수) 로 끝난다.

### 안정성

같은 키를 가진 원소들의 원래 순서가 정렬 후에도 유지되면 안정(stable) 정렬이다. 선택 정렬은 멀리 떨어진 두 칸을 바꾸면서 같은 키의 순서를 뒤집을 수 있다. 예: [(3,a), (3,b), (1,c)] 에서 최솟값 (1,c) 와 맨 앞 (3,a) 를 바꾸면 (3,b) 가 (3,a) 앞에 온다.

## 직접 해 보기

세 정렬의 비교 횟수와 교환(이동) 횟수를 입력 종류별로 센다. python3 로 실행해 확인했다.

```python
import random

def bubble(a):
    a = a[:]; cmp = swp = 0; n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            cmp += 1
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]; swp += 1; swapped = True
        if not swapped:
            break
    return a, cmp, swp

def selection(a):
    a = a[:]; cmp = swp = 0; n = len(a)
    for i in range(n - 1):
        m = i
        for j in range(i + 1, n):
            cmp += 1
            if a[j] < a[m]:
                m = j
        if m != i:
            a[i], a[m] = a[m], a[i]; swp += 1
    return a, cmp, swp

def insertion(a):
    a = a[:]; cmp = mv = 0
    for i in range(1, len(a)):
        key = a[i]; j = i - 1
        while j >= 0:
            cmp += 1
            if a[j] > key:
                a[j + 1] = a[j]; mv += 1; j -= 1
            else:
                break
        a[j + 1] = key
    return a, cmp, mv

random.seed(1)
n = 1000
cases = {"random": random.sample(range(n), n), "sorted": list(range(n)),
         "reversed": list(range(n, 0, -1)), "nearly": list(range(n))}
x = cases["nearly"]
for _ in range(10):                       # 인접 교환 10번으로 살짝 흐트러뜨림
    i = random.randrange(n - 1); x[i], x[i + 1] = x[i + 1], x[i]

for name, data in cases.items():
    r = [f(data) for f in (bubble, selection, insertion)]
    assert all(t[0] == sorted(data) for t in r)
    print(f"{name:>9} | " + " | ".join(f"{c:>8}/{s:<9}" for _, c, s in r))
```

출력 (열 순서: 버블, 선택, 삽입 — 비교/교환·이동):

```
   random |   498015/250393    |   499500/991       |   251387/250393
   sorted |      999/0         |   499500/0         |      999/0
 reversed |   499500/499500    |   499500/500       |   499500/499500
   nearly |     1997/10        |   499500/10        |     1009/10
```

읽을 거리가 많다.

- 선택 정렬은 입력과 무관하게 비교가 항상 n(n−1)/2 = 499500 이다. 대신 교환은 1000 미만이다.
- 버블과 삽입의 교환·이동 수는 같다(무작위 250393). 둘 다 역순쌍 수와 같기 때문이다.
- 거의 정렬된 입력에서 삽입 정렬은 비교 1009 번으로 끝난다. 사실상 선형이다.

## 현업에서는

- **하이브리드 정렬의 부품.** CPython 의 `list.sort()` 는 Timsort 이고, 짧은 구간(run)은 이진 삽입 정렬로 늘린다. C++ 표준 라이브러리 구현들이 쓰는 introsort, Go 1.19 부터 `sort` 패키지가 쓰는 pdqsort(pattern-defeating quicksort) 도 작은 구간에서는 삽입 정렬로 바꾼다. 작은 n 에서는 상수가 작은 단순한 알고리즘이 이긴다.
- **쓰기가 비싼 매체.** 쓰기 횟수가 수명이나 비용에 직결되는 환경에서는 교환이 적은 선택 정렬의 성질이 의미 있을 수 있다.
- **이미 거의 정렬된 데이터.** 시간순으로 쌓이다가 가끔 늦게 도착하는 이벤트를 정렬 상태로 유지할 때, 뒤에서부터 제자리를 찾는 삽입 방식이 자연스럽다.

## 확인 문제

1. 선택 정렬의 비교 횟수가 입력에 무관한 이유는?
2. 크기 n 의 역순 배열의 역순쌍 수는?
3. 안정 정렬이 필요한 실제 예를 하나 들어라.
4. 버블 정렬에서 "한 바퀴 동안 교환이 없으면 종료" 를 빼면 최선 복잡도는 어떻게 되는가?

### 풀이

1. 매 단계 남은 구간 전체를 훑어 최솟값을 찾아야 하므로, 데이터 값과 상관없이 (n−1)+(n−2)+...+1 번 비교한다.
2. 모든 쌍이 역순이므로 n(n−1)/2.
3. 주문 목록을 먼저 시간순으로 정렬한 뒤 고객별로 다시 정렬하면, 안정 정렬일 때 고객 안에서 시간순이 유지된다. 다중 키 정렬을 "덜 중요한 키부터 차례로" 하는 기법이 안정성에 의존한다.
4. 정렬된 입력에서도 모든 비교를 수행하므로 Θ(n²) 이 된다.

## 더 읽을거리 (References)

- Python 공식 문서, [Sorting Techniques](https://docs.python.org/3/howto/sorting.html) — 안정성과 다중 키 정렬
- CPython 소스, [Objects/listsort.txt](https://raw.githubusercontent.com/python/cpython/main/Objects/listsort.txt) — Timsort 설계 문서
- Go 1.19 Release Notes, [sort 패키지 변경](https://go.dev/doc/go1.19) — pdqsort 도입
- Donald E. Knuth, *The Art of Computer Programming, Vol. 3: Sorting and Searching*, 2nd ed., Addison-Wesley, 1998, 5.2절.
