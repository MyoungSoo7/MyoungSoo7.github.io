---
layout: post
title: "[CS300 #063] 분할 상환 분석 — 가끔 비싼 연산을 평균 내는 정직한 방법"
date: 2026-10-10 19:03:00 +0900
categories: [cs]
tags: [cs300, algorithms, amortized-analysis, dynamic-array, potential-method]
---

컴퓨터공학 300 주제 시리즈의 063번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

분할 상환(amortized) 분석은 연산 하나하나의 최악이 아니라 "연산 n 개를 연달아 했을 때의 최악 총비용" 을 n 으로 나눈 값을 본다. 확률이 끼지 않는 최악 보장이라는 점에서 평균 분석과 다르다.

## 왜 필요한가

동적 배열(Python `list`, Java `ArrayList`, Go 슬라이스)의 append 를 생각해 보자. 대부분은 빈 칸에 하나 쓰고 끝난다. 그러다 배열이 꽉 차면 더 큰 배열을 만들고 기존 원소를 전부 복사한다. 이 한 번은 O(n) 이다.

그럼 append 는 O(n) 인가? 그렇게 말하면 n 번 append 하는 루프가 O(n²) 이라는 잘못된 결론이 나온다. 실제로는 O(n) 이다. 이 간극을 정확히 설명하는 도구가 분할 상환 분석이다. Java `ArrayList` 공식 문서가 add 를 "amortized constant time" 이라고 적는 것도 이 의미다.

## 핵심 개념

### 평균 분석과의 차이

| 구분 | 무엇을 평균 내나 | 보장 |
|---|---|---|
| 평균(average-case) 분석 | 입력 분포에 대한 기댓값 | 운 나쁜 입력이면 깨질 수 있음 |
| 분할 상환(amortized) 분석 | 한 연산 열(sequence) 안의 비용 | 어떤 연산 열이든 총비용 상한이 성립 |

분할 상환은 "운" 에 기대지 않는다. 다만 개별 연산 하나가 느릴 수 있다는 사실은 그대로다.

### 방법 1. 총합(aggregate) 방법

용량을 두 배씩 늘리는 동적 배열에 n 번 append 한다고 하자. 복사가 일어나는 시점은 크기가 1, 2, 4, ..., 2^k 일 때다(2^k < n). 복사 비용 합은

```
1 + 2 + 4 + ... + 2^k < 2n
```

여기에 쓰기 자체의 비용 n 을 더하면 총비용 < 3n. n 으로 나누면 append 하나당 상수, 즉 분할 상환 O(1) 이다.

### 방법 2. 회계(accounting) 방법

append 할 때마다 실제 비용보다 조금 더 "요금" 을 걷어 은행에 넣는다고 생각한다. append 한 번에 3 을 걷는다.

- 1 은 지금 쓰는 데 쓴다.
- 1 은 이 원소가 나중에 복사될 때를 위해 저축한다.
- 1 은 이미 복사된 적 있는 옛 원소 하나의 다음 복사를 위해 저축한다.

용량이 m 에서 2m 으로 늘 때, 직전 확장 이후 새로 들어온 m/2 개 원소가 각각 2 씩, 총 m 을 모아 두었다. 복사 비용 m 을 정확히 낼 수 있다. 은행 잔고가 음수가 되지 않으니 총 실제 비용 ≤ 총 요금 = 3n.

### 방법 3. 퍼텐셜(potential) 방법

자료구조 상태 D 에 "저장된 에너지" Φ(D) 를 정의한다. 분할 상환 비용은

```
ĉ_i = c_i + Φ(D_i) − Φ(D_{i−1})
```

Φ 가 처음에 0 이고 항상 0 이상이면, 분할 상환 비용의 합이 실제 비용 합의 상한이 된다. 동적 배열은 Φ = 2·size − capacity 로 두면 위 결과가 깔끔하게 나온다. 퍼텐셜 방법은 Tarjan 이 1985년 논문에서 체계화했고, 스플레이 트리·피보나치 힙·유니온 파인드 분석의 표준 도구가 되었다.

### 성장 방식이 결과를 바꾼다

용량을 "두 배" 가 아니라 "고정 10칸씩" 늘리면 어떻게 될까? 확장 횟수가 n/10 번, 각 복사가 평균 n/2 이므로 총비용은 Θ(n²) 이다. 분할 상환 O(1) 을 얻으려면 기하급수적으로(상수 배로) 늘려야 한다. 배수가 2 일 필요는 없고 1보다 크기만 하면 된다. 배수가 작을수록 메모리 낭비는 줄고 복사는 늘어난다.

## 직접 해 보기

두 성장 정책의 복사 횟수를 세어 본다. python3 로 실행해 확인했다.

```python
import sys

class DynArray:
    def __init__(self, growth):
        self.cap, self.size, self.copies = 1, 0, 0
        self.growth = growth
    def append(self, x):
        if self.size == self.cap:
            self.copies += self.size          # 새 배열로 옮기는 비용
            self.cap = self.growth(self.cap)
        self.size += 1

for name, g in [("x2", lambda c: c * 2), ("+10", lambda c: c + 10)]:
    for n in [1_000, 10_000, 100_000]:
        a = DynArray(g)
        for i in range(n):
            a.append(i)
        print(f"{name:>4} n={n:>7}  copies={a.copies:>11}  copies/n={a.copies/n:8.2f}")
```

출력:

```
  x2 n=   1000  copies=       1023  copies/n=    1.02
  x2 n=  10000  copies=      16383  copies/n=    1.64
  x2 n= 100000  copies=     131071  copies/n=    1.31
 +10 n=   1000  copies=      49600  copies/n=   49.60
 +10 n=  10000  copies=    4996000  copies/n=  499.60
 +10 n= 100000  copies=  499960000  copies/n= 4999.60
```

두 배 정책은 원소당 복사가 2 미만으로 묶여 있다. 고정 증가 정책은 n 이 10배가 되면 원소당 복사도 10배가 된다. 앞은 분할 상환 O(1), 뒤는 분할 상환 O(n) 이다.

실제 CPython 리스트도 여유 용량을 두고 늘린다. `sys.getsizeof` 로 append 하면서 크기를 찍어 보면 매번이 아니라 띄엄띄엄 바뀌는 것을 볼 수 있다. 정확한 증가 비율은 구현 세부라 버전마다 다를 수 있다.

## 현업에서는

- **지연 시간 꼬리(tail latency).** 분할 상환 O(1) 은 "평균적으로 빠르다" 이지 "매번 빠르다" 가 아니다. 거대한 배열이 확장되는 순간이나 해시 테이블이 재해싱되는 순간 한 요청이 튄다. 지연 시간 상한이 중요한 시스템은 미리 용량을 잡거나(`reserve`, 초기 용량 지정) 점진적 재해싱을 쓴다.
- **미리 크기 잡기.** 원소 수를 알면 Java 는 `new ArrayList<>(n)`, Go 는 `make([]T, 0, n)` 처럼 용량을 먼저 준다. 복사가 아예 사라진다.
- **로그·버퍼.** 쓰기 버퍼를 모았다가 한 번에 flush 하는 구조도 같은 사고방식이다. 대부분의 쓰기는 메모리에 붙이기만 하고, 가끔 한 번 비싼 디스크 쓰기가 일어난다. 총비용을 쓰기 횟수로 나누면 싸다.

## 확인 문제

1. 분할 상환 O(1) 인 연산이 한 번 호출에 O(n) 이 걸릴 수 있는가?
2. 동적 배열에서 원소가 용량의 1/4 이하로 줄 때 용량을 절반으로 줄이는 정책을 쓴다. 왜 "1/2 이하일 때 절반으로" 가 아니라 1/4 인가?
3. 이진 카운터를 0 부터 n 번 1씩 증가시킬 때 뒤집히는 비트의 총수가 O(n) 인 이유를 총합 방법으로 설명하라.

### 풀이

1. 그렇다. 확장이 일어나는 그 한 번은 O(n) 이다. 분할 상환은 연산 열 전체의 합에 대한 보장이다.
2. 1/2 에서 줄이면 경계에서 append 와 pop 을 번갈아 할 때마다 확장·축소가 반복되어 매번 O(n) 이 된다. 1/4 로 간격을 두면 확장 직후와 축소 직후 모두 다음 재조정까지 Θ(n) 번의 연산이 필요해 비용이 상환된다.
3. 최하위 비트는 매번, 그 다음 비트는 2번에 한 번, k번째 비트는 2^k 번에 한 번 뒤집힌다. 총합은 n(1 + 1/2 + 1/4 + ...) < 2n.

## 더 읽을거리 (References)

- Robert E. Tarjan, "Amortized Computational Complexity", *SIAM Journal on Algebraic and Discrete Methods* 6(2), 1985.
- Java SE 21 API, [ArrayList](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html)
- CPython 소스, [Objects/listobject.c](https://raw.githubusercontent.com/python/cpython/main/Objects/listobject.c) — `list_resize` 의 여유 할당(over-allocation) 주석
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022, 16장.
