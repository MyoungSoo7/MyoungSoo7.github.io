---
layout: post
title: "[CS300 #072] 동적 계획법 1 — 메모이제이션과 테이블"
date: 2026-10-10 19:12:00 +0900
categories: [cs]
tags: [cs300, algorithms, dynamic-programming, memoization, tabulation]
---

컴퓨터공학 300 주제 시리즈의 072번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

동적 계획법(DP)은 겹치는 하위 문제의 답을 한 번만 계산해 저장하고 재사용한다. 위에서 재귀로 내려가며 저장하면 메모이제이션, 아래에서 표를 채워 올라가면 테이블(tabulation) 방식이다. 시간은 대개 "상태 수 × 상태당 전이 비용" 이다.

## 왜 필요한가

피보나치 수를 정의대로 재귀하면 fib(25) 하나에 함수가 24만 번 넘게 호출된다. 같은 fib(10) 을 수천 번 다시 계산하기 때문이다. 이미 푼 것을 기억만 해도 호출은 26번이면 된다.

이 차이는 장난감 문제에만 있지 않다. 텍스트 diff, 맞춤법 교정의 편집 거리, 최적 경로, 자원 배분 같은 실제 문제가 모두 "작은 문제의 답을 조합해 큰 문제의 답을 만들고, 그 작은 문제들이 서로 겹치는" 구조다.

## 핵심 개념

### DP 가 성립하는 두 조건

1. **최적 부분 구조**: 큰 문제의 최적해가 작은 문제들의 최적해로 구성된다.
2. **겹치는 하위 문제**: 같은 하위 문제가 여러 번 등장한다.

2번이 없으면 분할 정복으로 충분하다(병합 정렬의 두 절반은 겹치지 않는다). 2번이 있을 때 저장의 효과가 생긴다.

### 설계 네 단계

1. **상태 정의**: dp[i] 가 정확히 무엇을 뜻하는지 한 문장으로 쓴다. 가장 중요하고 가장 어렵다.
2. **점화식**: dp[i] 를 더 작은 상태들로 표현한다.
3. **기저 사례**: 더 쪼갤 수 없는 상태의 값.
4. **계산 순서**: 의존하는 상태가 먼저 계산되도록 순서를 정한다.

피보나치라면 상태 dp[i] = i번째 피보나치 수, 점화식 dp[i] = dp[i−1] + dp[i−2], 기저 dp[0]=0, dp[1]=1, 순서는 i 증가 방향이다.

### 메모이제이션 vs 테이블

```
메모이제이션 (top-down)          테이블 (bottom-up)
fib(5)                           i:  0 1 2 3 4 5
 ├ fib(4)                        dp: 0 1 1 2 3 5
 │  ├ fib(3)                         →→→→→→→→→→→
 │  │  ├ fib(2) ...              왼쪽부터 채운다
 │  │  └ fib(1)
 │  └ fib(2)  ← 캐시에서 바로
 └ fib(3)     ← 캐시에서 바로
```

| | 메모이제이션 | 테이블 |
|---|---|---|
| 작성 | 재귀 정의에 캐시만 붙이면 됨 | 계산 순서를 직접 정해야 함 |
| 계산 범위 | 실제로 필요한 상태만 | 보통 모든 상태 |
| 비용 | 함수 호출·해시 조회 오버헤드, 재귀 깊이 제한 | 반복문이라 빠르고 깊이 문제 없음 |
| 공간 최적화 | 어렵다 | 필요한 직전 행만 남기기 쉽다 |

Python 은 `functools.lru_cache` 나 `functools.cache` 데코레이터로 메모이제이션을 한 줄에 붙일 수 있다. 인자가 해시 가능해야 하고, 재귀가 깊으면 기본 재귀 한도에 걸릴 수 있다는 점은 기억해 두자.

### 복잡도 세기

DP 의 시간은 거의 항상

```
(서로 다른 상태의 수) × (상태 하나를 계산하는 데 보는 이전 상태 수)
```

피보나치: 상태 n 개 × 전이 2 = Θ(n). 아래의 격자 경로: 상태 R·C 개 × 전이 2 = Θ(RC). 이 공식으로 설계 단계에서 이미 실행 시간을 예측할 수 있다.

### 공간 줄이기

dp[i] 가 dp[i−1], dp[i−2] 만 본다면 배열 전체가 필요 없다. 변수 두 개로 충분하다. 2차원 표에서 각 행이 직전 행만 본다면 행 두 개(또는 한 개)로 줄일 수 있다. 다만 공간을 줄이면 "최적해 자체를 역추적" 하기 어려워진다는 대가가 있다.

## 직접 해 보기

세 가지 피보나치와 장애물이 있는 격자 경로 수를 계산한다. python3 로 실행해 확인했다.

```python
from functools import cache

calls = 0
def fib_naive(n):
    global calls
    calls += 1
    return n if n < 2 else fib_naive(n - 1) + fib_naive(n - 2)

@cache
def fib_memo(n):
    return n if n < 2 else fib_memo(n - 1) + fib_memo(n - 2)

def fib_table(n):
    if n < 2:
        return n
    prev, cur = 0, 1                 # 직전 두 칸만 기억하면 된다
    for _ in range(n - 1):
        prev, cur = cur, prev + cur
    return cur

print("naive fib(25) =", fib_naive(25), "호출 수:", calls)
print("memo  fib(25) =", fib_memo(25), fib_memo.cache_info())
print("table fib(90) =", fib_table(90))

# 격자 경로: 장애물(#)을 피해 왼쪽 위 → 오른쪽 아래, 오른쪽/아래로만
grid = ["....",
        ".#..",
        "...#",
        "#..."]
R, C = len(grid), len(grid[0])
dp = [[0] * C for _ in range(R)]
for r in range(R):
    for c in range(C):
        if grid[r][c] == "#":
            continue
        if r == 0 and c == 0:
            dp[r][c] = 1; continue
        dp[r][c] = (dp[r - 1][c] if r else 0) + (dp[r][c - 1] if c else 0)
for row in dp:
    print(" ".join(f"{v:2d}" for v in row))
print("경로 수:", dp[-1][-1])
```

출력:

```
naive fib(25) = 75025 호출 수: 242785
memo  fib(25) = 75025 CacheInfo(hits=23, misses=26, maxsize=None, currsize=26)
table fib(90) = 2880067194370816120
 1  1  1  1
 1  0  1  2
 1  1  2  0
 0  1  3  3
경로 수: 3
```

단순 재귀는 242,785번 호출했다. 메모이제이션은 서로 다른 상태 26개(fib(0)~fib(25))를 한 번씩 계산하고 23번은 캐시에서 꺼냈다. 테이블 방식은 재귀가 없어 fib(90) 도 바로 나온다. 격자의 dp[r][c] 는 "(r, c) 까지 오는 경로 수" 이고, 위와 왼쪽에서 오는 경로를 더한다. 표를 직접 들여다보면 점화식이 맞게 돌았는지 눈으로 확인할 수 있다.

## 현업에서는

- **캐시 데코레이터의 함정.** `lru_cache` 를 인스턴스 메서드에 붙이면 `self` 가 캐시 키에 들어가 인스턴스가 해제되지 않을 수 있다. 크기 제한 없는 `cache` 를 입력이 무한히 다양한 함수에 붙이면 메모리가 계속 는다. 공식 문서도 이 점을 경고한다.
- **요청 단위 메모이제이션.** 한 요청 처리 중 같은 설정값이나 권한 정보를 여러 번 조회한다면 요청 범위 캐시에 저장한다. 같은 하위 문제를 두 번 풀지 않는다는 DP 의 발상과 같다.
- **빌드 시스템.** Make, Bazel 같은 빌드 도구는 입력이 같으면 이전 결과를 재사용한다. "이 타깃의 답은 의존 타깃들의 답으로 정해진다" 는 구조라서, 하위 결과를 저장하면 전체 빌드가 증분으로 빨라진다.
- **최적화 문제.** 배포 순서, 예산 배분, 경로 문제처럼 선택의 조합이 폭발하는 문제를 만나면 "상태를 무엇으로 정의할까" 부터 생각한다. 상태 수가 감당 가능하면 DP 로 정확한 답을 얻는다.

## 확인 문제

1. 계단을 한 번에 1칸 또는 2칸 오를 때 n 칸 계단을 오르는 방법 수의 점화식과 기저 사례를 써라.
2. 메모이제이션 버전 fib(n) 의 시간·공간 복잡도는?
3. DP 가 아니라 분할 정복이 맞는 문제의 특징은?
4. 격자 경로 문제를 행 하나 크기의 배열로 풀 수 있는 이유는?

### 풀이

1. ways[n] = ways[n−1] + ways[n−2], ways[0] = 1, ways[1] = 1. 마지막 한 걸음이 1칸이었는지 2칸이었는지로 나눈다.
2. 시간 Θ(n), 공간 Θ(n)(캐시 n 개 + 재귀 스택 깊이 n).
3. 하위 문제가 서로 겹치지 않는다. 각 하위 문제가 한 번씩만 등장하므로 저장해 봐야 재사용이 없다.
4. dp[r][c] 가 바로 위 dp[r−1][c] 와 왼쪽 dp[r][c−1] 만 본다. 한 행짜리 배열을 왼쪽부터 덮어쓰면, 덮어쓰기 전 값이 "위" 이고 이미 갱신된 왼쪽 칸이 "왼쪽" 이 된다.

## 더 읽을거리 (References)

- Python 공식 문서, [functools.lru_cache, functools.cache](https://docs.python.org/3/library/functools.html)
- NIST Dictionary of Algorithms and Data Structures, [dynamic programming](https://xlinux.nist.gov/dads/HTML/dynamicprog.html)
- NIST Dictionary of Algorithms and Data Structures, [memoization](https://xlinux.nist.gov/dads/HTML/memoize.html)
- Richard Bellman, *Dynamic Programming*, Princeton University Press, 1957.
