---
layout: post
title: "[CS300 #068] 이진 탐색과 그 변형 — 경계를 찾는 알고리즘"
date: 2026-10-10 19:08:00 +0900
categories: [cs]
tags: [cs300, algorithms, binary-search, bisect, parametric-search]
---

컴퓨터공학 300 주제 시리즈의 068번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

이진 탐색은 "값 찾기" 가 아니라 "참과 거짓이 바뀌는 경계 찾기" 다. 단조인 조건만 있으면 정렬된 배열이 아니어도, 심지어 배열이 없어도 쓸 수 있고, 매 단계 후보를 절반으로 줄여 Θ(log n) 에 끝난다.

## 왜 필요한가

이진 탐색은 아이디어는 쉽지만 정확히 짜기 어렵기로 유명하다. Jon Bentley 는 *Programming Pearls* 에서 첫 이진 탐색은 1946년에 발표되었지만 모든 n 에 대해 올바르게 동작하는 첫 버전은 1962년에야 나왔다고 적었다. 그리고 2006년, Joshua Bloch 는 바로 그 책의 이진 탐색과 이를 옮긴 JDK 구현에 중간값 계산 오버플로 버그가 있었다고 공개했다.

경계 조건 하나만 틀려도 무한 루프에 빠지거나 원소 하나를 놓친다. 그래서 "외워서 짜기" 보다 "불변식을 세우고 짜기" 가 필요하다.

## 핵심 개념

### 불변식으로 짜기

정렬된 배열 a 에서 `a[i] >= x` 인 첫 위치(lower bound)를 찾는다고 하자. 반열린 구간 [lo, hi) 를 쓰고 다음 불변식을 유지한다.

```
a[0 .. lo-1]  는 모두 < x       (확실히 답이 아님)
a[hi .. n-1]  는 모두 >= x      (답이거나 답보다 오른쪽)
[lo, hi)      는 아직 모름
```

- 시작: lo = 0, hi = n. 모르는 구간이 전체다.
- mid 에서 `a[mid] < x` 이면 mid 까지 확실히 답이 아니므로 lo = mid + 1.
- 아니면 mid 가 답 후보이므로 hi = mid.
- lo == hi 가 되면 모르는 구간이 비었다. lo 가 답이다.

매 단계 구간이 엄밀히 줄어들기 때문에(mid 는 [lo, hi) 안에 있다) 무한 루프가 없다. 이 틀 하나로 대부분의 변형을 처리한다.

### 네 가지 기본 변형

| 원하는 것 | 조건 | Python |
|---|---|---|
| x 이상인 첫 위치 | `a[mid] < x` 면 오른쪽으로 | `bisect_left` |
| x 초과인 첫 위치 | `a[mid] <= x` 면 오른쪽으로 | `bisect_right` |
| x 의 개수 | upper − lower | 두 번 호출 |
| x 미만인 마지막 위치 | lower − 1 | `bisect_left(a, x) - 1` |

정확히 x 가 있는지는 `i = bisect_left(a, x)` 뒤에 `i < len(a) and a[i] == x` 로 확인한다.

### 일반화: 단조 조건

배열이 없어도 된다. 정수 h 에 대해 조건 P(h) 가 "어느 지점까지 참이다가 그 뒤로 거짓" 이면, 경계를 이진 탐색으로 찾을 수 있다.

```
h:    1  2  3 ... 199 200 201 202 ...
P(h): T  T  T ...  T   T   F   F  ...
                       ↑ 찾는 답
```

이것을 "답에 대한 이진 탐색" 또는 매개변수 탐색(parametric search)이라고 부른다. 최적화 문제("최대 h 는?")를 판정 문제("h 로 가능한가?")로 바꾸고, 판정이 단조이면 쓸 수 있다.

### 실수 범위

연속된 값에서는 정해진 횟수만큼 반복하거나(예: 100번) 구간 폭이 허용 오차보다 작아질 때 멈춘다. 매 반복이 폭을 절반으로 줄이므로 64번이면 배정밀도 부동소수점의 구분 한계에 도달한다.

### 복잡도

후보가 n 개에서 시작해 매 단계 절반이 되므로 ⌊log₂ n⌋ + 1 번 안에 끝난다. n = 10억이어도 30번 정도다. 정렬된 배열에서 비교만으로 찾는 방법 중에서는 최악 비교 횟수가 최적이다.

## 직접 해 보기

lower/upper bound 를 직접 짜서 표준 라이브러리 `bisect` 와 대조하고, 답에 대한 이진 탐색을 하나 풀어 본다. python3 로 실행해 확인했다.

```python
import bisect

def lower_bound(a, x):
    """a[i] >= x 인 첫 i. 없으면 len(a)."""
    lo, hi = 0, len(a)            # 반열린 구간 [lo, hi)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo

def upper_bound(a, x):
    """a[i] > x 인 첫 i."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo

a = [1, 3, 3, 3, 5, 8]
for x in [0, 3, 4, 8, 9]:
    lb, ub = lower_bound(a, x), upper_bound(a, x)
    assert lb == bisect.bisect_left(a, x) and ub == bisect.bisect_right(a, x)
    print(f"x={x}: lower={lb} upper={ub} 개수={ub - lb}")

# 답에 대한 이진 탐색: 통나무들을 잘라 길이 h 조각을 k 개 이상 얻는 최대 h
logs = [802, 743, 457, 539]
k = 11
def ok(h):
    return sum(L // h for L in logs) >= k     # h 가 커질수록 참 → 거짓 (단조)
lo, hi = 1, max(logs) + 1                     # ok(lo) 참, ok(hi) 거짓 을 유지
while hi - lo > 1:
    mid = (lo + hi) // 2
    if ok(mid):
        lo = mid
    else:
        hi = mid
print("최대 조각 길이:", lo, "| 그때 조각 수:", sum(L // lo for L in logs))
```

출력:

```
x=0: lower=0 upper=0 개수=0
x=3: lower=1 upper=4 개수=3
x=4: lower=4 upper=4 개수=0
x=8: lower=5 upper=6 개수=1
x=9: lower=6 upper=6 개수=0
최대 조각 길이: 200 | 그때 조각 수: 11
```

두 번째 탐색은 다른 불변식을 쓴다. "ok(lo) 는 참, ok(hi) 는 거짓" 을 지키며 둘 사이가 1 이 될 때까지 좁힌다. 구간 표현은 달라도 원리는 같다. 불변식을 먼저 정하고 그에 맞게 갱신식을 고른다.

## 현업에서는

- **`git bisect`.** 커밋 이력에서 "이 커밋부터 버그가 있다" 의 경계를 찾는다. good/bad 판정이 단조라는 가정 위에서, 커밋 1,000개도 10번 정도의 테스트로 범인을 좁힌다.
- **정렬된 데이터 조회.** 시계열 데이터에서 "이 시각 이후 첫 기록", 버전 목록에서 "이 버전 이상 첫 릴리스" 같은 질의는 lower bound 다. B-트리 노드 안의 키 탐색도 같은 연산이다.
- **용량 산정.** "p99 지연이 목표 이하로 유지되는 최대 동시 사용자 수" 를 부하 테스트로 찾을 때, 사용자 수를 이진 탐색으로 바꿔 가며 측정하면 실험 횟수가 로그로 준다. 결과가 단조라는 가정이 맞는지는 측정 잡음 때문에 따로 확인해야 한다.
- **설정값 찾기.** 리소스 한도를 얼마까지 줄여도 파드가 OOM 없이 도는지 찾는 실험도 같은 구조다. 홈랩에서 메모리 한도를 반씩 줄여 가며 경계를 찾는 식이다.

## 확인 문제

1. lower bound 코드에서 `hi = mid` 대신 `hi = mid - 1` 로 쓰면 어떤 문제가 생기는가?
2. 고정 폭 정수를 쓰는 언어에서 `(lo + hi) / 2` 대신 무엇을 쓰는가?
3. 정렬된 배열에서 x 의 등장 횟수를 O(log n) 에 구하는 방법은?
4. "답에 대한 이진 탐색" 을 쓰기 위한 필수 조건은?

### 풀이

1. mid 자체가 답일 수 있는데 그걸 구간에서 빼 버려 답을 놓친다. 불변식 "a[hi..] 는 모두 >= x" 에서 hi 가 가리키는 칸이 답 후보라는 의미가 깨진다.
2. `lo + (hi - lo) / 2`. 또는 Java 의 경우 부호 없는 시프트 `(lo + hi) >>> 1`.
3. `bisect_right(a, x) - bisect_left(a, x)`.
4. 판정 함수가 단조여야 한다. 어떤 값까지 참이고 그 뒤로 거짓(또는 그 반대)이어야 경계가 하나로 정해진다.

## 더 읽을거리 (References)

- Python 공식 문서, [bisect — Array bisection algorithm](https://docs.python.org/3/library/bisect.html)
- Git 공식 문서, [git-bisect](https://git-scm.com/docs/git-bisect)
- Joshua Bloch, [Extra, Extra - Read All About It: Nearly All Binary Searches and Mergesorts are Broken](https://research.google/blog/extra-extra-read-all-about-it-nearly-all-binary-searches-and-mergesorts-are-broken/), Google Research Blog, 2006
- Donald E. Knuth, *The Art of Computer Programming, Vol. 3: Sorting and Searching*, 2nd ed., Addison-Wesley, 1998, 6.2.1절.
