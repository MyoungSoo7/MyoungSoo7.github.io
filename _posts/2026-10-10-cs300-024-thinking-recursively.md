---
layout: post
title: "[CS300 #024] 재귀적으로 생각하기 — 더 작은 같은 문제를 믿는 법"
date: 2026-10-10 18:24:00 +0900
categories: [cs]
tags: [cs300, programming, recursion, memoization, call-stack]
---

컴퓨터공학 300 주제 시리즈의 024번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

재귀는 문제를 "더 작은 같은 문제 + 약간의 일"로 쪼개고, 더 이상 쪼갤 수 없는 기저 사례에서 멈추는 사고법이며, 그 정당성은 수학적 귀납법과 같은 구조를 가진다.

## 왜 필요한가

트리, 그래프, 중첩된 JSON, 파일 시스템, 문법 규칙은 모두 자기 자신을 품는 재귀적 구조다. 이런 데이터를 다루는 코드는 재귀로 쓸 때 데이터 모양과 코드 모양이 일치해 가장 짧고 정확해진다. 분할 정복, 동적 계획법, 백트래킹 같은 알고리즘 기법도 재귀적 사고 없이는 설계하기 어렵다.

반대로 재귀를 기계적으로만 쓰면 스택 오버플로와 지수 시간 폭발을 만난다. 언제 재귀가 좋고 언제 반복으로 바꿔야 하는지 아는 것이 이 글의 목표다.

## 핵심 개념

### 재귀의 두 부분

모든 재귀 함수는 두 부분으로 되어 있다.

1. **기저 사례(base case)**: 더 쪼개지 않고 바로 답을 아는 경우.
2. **재귀 사례(recursive case)**: 문제를 더 작은 같은 문제로 줄이고, 그 답을 이용해 원래 답을 만든다.

두 가지를 반드시 확인한다. 기저 사례가 존재하는가. 그리고 모든 재귀 호출이 기저 사례 쪽으로 **엄격히 작아지는가**. 둘 중 하나라도 빠지면 끝나지 않는다.

### 믿음의 도약

재귀 함수를 설계할 때 호출 과정을 끝까지 따라가려 하면 머리가 터진다. 대신 이렇게 생각한다.

> `f(n-1)` 이 올바른 답을 준다고 **믿는다**. 그 답으로 `f(n)` 을 어떻게 만들지 만 생각한다.

이것은 수학적 귀납법(#004)의 "n-1 에서 참이면 n 에서도 참"과 같은 구조다. 기저 사례가 귀납의 시작점이고, 재귀 사례가 귀납 단계다. 이 둘이 맞으면 모든 크기에서 맞다.

하노이 탑이 좋은 예다. n 개 원판을 A 에서 C 로 옮기려면, 위의 n-1 개를 B 로 옮기고(믿는다), 가장 큰 것을 C 로 옮기고, n-1 개를 B 에서 C 로 옮긴다(또 믿는다). 이동 횟수 T(n) = 2T(n-1) + 1, T(0) = 0 이므로 T(n) = 2^n - 1 이다.

### 호출 스택

재귀 호출 하나마다 **스택 프레임**이 하나 쌓인다. 프레임에는 매개변수, 지역 변수, 돌아갈 위치가 들어 있다(#027 에서 자세히 다룬다).

```
depth(3)
 └ depth(2)
    └ depth(1)
       └ depth(0) → 0     ← 여기서부터 되감기
       1 + 0 = 1
    1 + 1 = 2
 1 + 2 = 3
```

스택은 유한하다. Python 은 무한 재귀로 C 스택이 넘쳐 인터프리터가 죽는 것을 막으려고 재귀 깊이 상한을 둔다. 기본값은 대개 1000 이고 `sys.getrecursionlimit()` 으로 확인한다([sys](https://docs.python.org/3/library/sys.html#sys.getrecursionlimit)). 넘으면 `RecursionError` 가 난다.

### 꼬리 재귀

재귀 호출이 함수의 **마지막 동작**이면 꼬리 호출이라 한다. 돌아와서 할 일이 없으므로 현재 프레임을 재사용할 수 있다. Scheme 표준은 이를 언어 요구 사항으로 정한다. R7RS 3.5절 "Proper tail recursion"은 꼬리 호출이 무한히 이어져도 유한한 공간에서 돌아야 한다고 규정한다([R7RS small](https://small.r7rs.org/attachment/r7rs.pdf)).

Python, Java 는 꼬리 호출 최적화를 하지 않는다. 그래서 이 언어들에서 깊은 재귀는 명시적 스택을 쓰는 반복으로 바꿔야 한다.

### 중복 호출과 메모이제이션

피보나치를 정의 그대로 쓰면 `fib(n-1)` 과 `fib(n-2)` 가 같은 하위 문제를 반복해서 푼다. 호출 횟수가 지수적으로 늘어난다. 이미 푼 답을 저장해 두면(메모이제이션) 각 하위 문제를 한 번씩만 풀어 선형 시간이 된다. Python 은 `functools.lru_cache` 데코레이터로 이를 제공한다([functools](https://docs.python.org/3/library/functools.html#functools.lru_cache)). 이것이 동적 계획법의 하향식 형태다.

SICP 1.2절은 같은 문제를 "재귀 과정"과 "반복 과정"으로 나눠, 과정이 쓰는 공간과 시간이 어떻게 다른지 보여 준다([SICP 1.2](https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/6515/sicp.zip/full-text/book/book-Z-H-11.html)).

### 재귀 vs 반복

| 기준 | 재귀가 낫다 | 반복이 낫다 |
|---|---|---|
| 데이터 모양 | 트리·중첩 구조 | 선형 순회 |
| 깊이 | 로그 수준(균형 트리) | 입력 크기에 비례 |
| 언어 | 꼬리 호출 보장(Scheme 등) | Python, Java |
| 가독성 | 정의가 재귀적인 문제 | 상태가 단순한 누적 |

모든 재귀는 명시적 스택을 써서 반복으로 바꿀 수 있다. 컴퓨터가 호출 스택으로 하던 일을 직접 자료구조로 하는 것이다.

## 직접 해 보기

```python
import sys
from functools import lru_cache

def hanoi(n, src, dst, via, moves):
    if n == 0:                      # 기저 사례
        return
    hanoi(n - 1, src, via, dst, moves)
    moves.append((src, dst))
    hanoi(n - 1, via, dst, src, moves)

m = []; hanoi(3, "A", "C", "B", m)
print(len(m), m[:3])        # 7 [('A', 'C'), ('A', 'B'), ('C', 'B')]

calls = 0
def fib(n):
    global calls; calls += 1
    return n if n < 2 else fib(n - 1) + fib(n - 2)
print(fib(25), calls)       # 75025 242785

@lru_cache(maxsize=None)
def fib2(n):
    return n if n < 2 else fib2(n - 1) + fib2(n - 2)
print(fib2(100), fib2.cache_info())
# 354224848179261915075 CacheInfo(hits=98, misses=101, maxsize=None, currsize=101)

print(sys.getrecursionlimit())   # 1000
def depth(n):
    return 0 if n == 0 else 1 + depth(n - 1)
try:
    depth(100_000)
except RecursionError as e:
    print("RecursionError:", e)  # maximum recursion depth exceeded

def flatten(x):                  # 재귀 버전
    if not isinstance(x, list):
        return [x]
    out = []
    for item in x:
        out.extend(flatten(item))
    return out

def flatten_iter(x):             # 명시적 스택 버전
    stack, out = [x], []
    while stack:
        cur = stack.pop()
        if isinstance(cur, list):
            stack.extend(reversed(cur))   # 순서를 지키려고 뒤집어 넣는다
        else:
            out.append(cur)
    return out

data = [1, [2, [3, [4]], 5], []]
print(flatten(data), flatten_iter(data))  # [1, 2, 3, 4, 5] [1, 2, 3, 4, 5]
```

Python 3.12.3 에서 실행한 결과다. `fib(25)` 하나에 함수 호출이 24만 번 넘게 일어났고, 메모이제이션 버전은 `fib2(100)` 에 하위 문제 101개만 풀었다.

## 현업에서는

- **트리 순회**: 파일 시스템 탐색, DOM 순회, AST 처리, 조직도 집계는 재귀가 자연스럽다. 다만 사용자 입력으로 깊이가 정해지는 구조(예: 깊게 중첩된 JSON)는 공격자가 깊이를 키워 스택을 터뜨릴 수 있다. 파서들이 중첩 깊이 상한을 두는 이유다.
- **재귀 쿼리**: PostgreSQL 의 `WITH RECURSIVE` 는 카테고리 트리, 조직 계층 같은 데이터를 SQL 안에서 재귀적으로 펼친다. 순환 데이터가 있으면 끝나지 않으므로 방문 경로를 기록해 막는다.
- **헬름 차트와 템플릿**: 설정 병합(딥 머지)은 대개 재귀 함수다. 중첩 딕셔너리를 키마다 내려가며 합친다.
- **스택 크기 조정은 최후 수단**: `sys.setrecursionlimit` 을 크게 올리면 RecursionError 대신 프로세스가 세그폴트로 죽을 수 있다. 문서도 너무 높으면 크래시가 날 수 있다고 경고한다. 깊은 재귀는 반복으로 바꾸는 것이 정석이다.

## 확인 문제

1. 재귀 함수가 반드시 끝나기 위한 두 조건은?
2. 하노이 탑 원판 10개의 최소 이동 횟수는?
3. 메모이제이션 없는 `fib(n)` 의 호출 횟수가 지수적으로 늘어나는 이유는?
4. 꼬리 재귀가 아닌 `1 + depth(n - 1)` 을 꼬리 재귀 형태로 바꿔 보라.
5. Python 에서 깊이 10만의 연결 리스트를 재귀로 순회하면 어떻게 되며, 해결책은?

### 풀이

1. 기저 사례가 있고, 모든 재귀 호출이 기저 사례를 향해 엄격히 작아져야 한다.
2. 2^10 - 1 = 1023.
3. 같은 하위 문제를 여러 경로에서 반복해서 다시 풀기 때문이다. 호출 트리의 크기가 fib 값 자체에 비례해 늘어난다.
4. 누적 인자를 둔다. `def depth(n, acc=0): return acc if n == 0 else depth(n - 1, acc + 1)`. 단 Python 은 이를 최적화하지 않으므로 깊이 문제는 그대로다.
5. 기본 한도 1000 을 넘어 `RecursionError` 가 난다. `while` 루프나 명시적 스택으로 바꾼다.

## 더 읽을거리 (References)

- Abelson, Sussman, *Structure and Interpretation of Computer Programs*, 2nd ed., [Procedures and the Processes They Generate](https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/6515/sicp.zip/full-text/book/book-Z-H-11.html)
- Python Docs, [sys.getrecursionlimit / setrecursionlimit](https://docs.python.org/3/library/sys.html)
- Python Docs, [functools.lru_cache](https://docs.python.org/3/library/functools.html)
- [Revised7 Report on the Algorithmic Language Scheme](https://small.r7rs.org/attachment/r7rs.pdf) — 3.5절 Proper tail recursion
