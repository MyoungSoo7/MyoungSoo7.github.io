---
layout: post
title: "[CS300 #032] 고차 함수·map·filter·reduce — 반복을 이름 붙은 패턴으로"
date: 2026-10-10 18:32:00 +0900
categories: [cs]
tags: [cs300, programming, higher-order-function, map-reduce, functional-programming]
---

컴퓨터공학 300 주제 시리즈의 032번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

고차 함수는 함수를 인자로 받거나 함수를 돌려주는 함수이며, map(변환)·filter(선별)·reduce(누적)는 반복문에서 가장 자주 나오는 세 가지 패턴에 이름을 붙인 고차 함수다.

## 왜 필요한가

반복문을 열어 보면 하는 일은 대개 셋 중 하나다. 원소마다 무언가로 바꾸거나, 조건에 맞는 원소만 남기거나, 원소들을 하나의 값으로 합친다. 매번 `for` 와 임시 리스트와 누적 변수를 손으로 쓰면 의도가 코드 속에 묻히고, 초기값이나 인덱스 실수가 끼어든다.

map·filter·reduce 로 쓰면 "무엇을 하는가"가 함수 이름으로 드러난다. 그리고 이 세 패턴은 한 컴퓨터를 넘어 분산 처리 모델(MapReduce, Spark)과 스트림 API(Java Stream, JavaScript 배열 메서드)의 공용어가 되었다.

## 핵심 개념

### 고차 함수

함수가 일급 값이면(#023) 함수를 다른 함수에 넘길 수 있다. 다음 중 하나라도 하면 고차 함수다.

- 함수를 **인자로 받는다**: `sorted(xs, key=len)`, `map(f, xs)`
- 함수를 **반환한다**: 데코레이터, `functools.partial`, `compose`

고차 함수는 "무엇을 반복할지(데이터)"와 "각 원소에 무엇을 할지(함수)"를 분리한다. 반복의 뼈대는 한 번만 올바르게 짜 두고, 바뀌는 부분만 함수로 끼운다.

### 세 가지 패턴

```
map(f)      [a, b, c]  →  [f(a), f(b), f(c)]          길이 유지, 원소 변환
filter(p)   [a, b, c]  →  [a, c]   (p(a), p(c) 참)    원소 유지, 길이 축소
reduce(g,z) [a, b, c]  →  g(g(g(z, a), b), c)         하나의 값으로 접기
```

| 패턴 | 반복문으로 쓰면 | 결과 |
|---|---|---|
| map | 빈 리스트 → 원소마다 `f(x)` 를 append | 같은 길이의 새 컬렉션 |
| filter | 빈 리스트 → 조건 참이면 append | 같거나 짧은 컬렉션 |
| reduce | 누적 변수 → 원소마다 `acc = g(acc, x)` | 단일 값 |

reduce 는 **fold(접기)** 라고도 부른다. 합계, 곱, 최댓값, 문자열 연결, 딕셔너리 만들기가 모두 reduce 다. 사실 map 과 filter 도 reduce 로 표현할 수 있다. 누적값을 리스트로 두고 변환된 원소나 통과한 원소만 덧붙이면 된다.

### 초기값과 빈 입력

reduce 에서 가장 흔한 실수는 초기값을 빠뜨리는 것이다. Python 의 `functools.reduce(f, iterable)` 는 초기값이 없으면 첫 원소를 초기값으로 쓰고, 입력이 비어 있으면 `TypeError` 를 낸다([functools.reduce](https://docs.python.org/3/library/functools.html#functools.reduce)). 합계면 0, 곱이면 1 처럼 **연산의 항등원**을 초기값으로 주면 빈 입력도 자연스럽게 처리된다. 결합 법칙을 만족하는 연산과 항등원의 쌍을 모노이드라 하는데, 이 성질이 있어야 데이터를 쪼개 병렬로 접은 뒤 합칠 수 있다.

### Python 에서의 위치

Python 3 에서 `map`, `filter` 는 리스트가 아니라 **지연 반복자**를 돌려준다. 필요할 때 하나씩 계산하고, 한 번 소비하면 비어 있다([Built-in Functions](https://docs.python.org/3/library/functions.html#map)). `reduce` 는 내장 함수에서 빠져 `functools` 로 옮겨졌다.

Python 커뮤니티는 단순한 map·filter 대신 **리스트 내포**와 **생성자 표현식**을 더 선호한다. `[x*x for x in xs if x % 2 == 0]` 이 `list(map(lambda x: x*x, filter(lambda x: x % 2 == 0, xs)))` 보다 읽기 쉽기 때문이다. 합계·최댓값 같은 흔한 reduce 는 `sum`, `max`, `min`, `any`, `all` 로 이미 제공된다. `itertools` 에는 `accumulate`(중간 누적값을 모두 내는 reduce), `groupby`, `chain` 같은 반복자 조합 도구가 있다([itertools](https://docs.python.org/3/library/itertools.html)).

### JavaScript 의 배열 메서드

JavaScript 는 배열 메서드로 체이닝한다. `xs.map(...).filter(...).reduce(...)`. 주의할 점이 있다. `map` 은 콜백에 `(원소, 인덱스, 배열)` 세 인자를 넘긴다. 그래서 `["1","2","3"].map(parseInt)` 는 `parseInt("2", 1)`, `parseInt("3", 2)` 를 호출해 `[1, NaN, NaN]` 이 된다. MDN 이 이 사례를 직접 다룬다([Array.prototype.map](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map)). `reduce` 도 초기값이 없고 배열이 비면 `TypeError` 를 던진다([Array.prototype.reduce](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/reduce)).

### 함수 조합과 부분 적용

고차 함수의 다른 축은 함수로 함수를 만드는 것이다.

- **조합(compose)**: `f` 다음 `g` 를 실행하는 새 함수 `x → g(f(x))`.
- **부분 적용(partial)**: 일부 인자를 고정한 새 함수. `partial(pow, exp=2)` 는 제곱 함수다.

작은 순수 함수를 조합해 파이프라인을 만드는 방식은 유닉스 파이프(`cat | grep | sort | uniq -c`)와 같은 철학이다.

### 분산으로의 확장

딘(Dean)과 게마왓(Ghemawat)의 2004년 OSDI 논문 "MapReduce: Simplified Data Processing on Large Clusters"는 사용자가 map 과 reduce 두 함수만 작성하면 런타임이 수천 대 머신에 분산·재시도·집계를 처리하는 모델을 제시했다. 함수가 순수하면(#031) 실패한 작업을 아무 머신에서나 다시 돌려도 결과가 같다는 점이 이 모델의 바탕이다.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
from functools import reduce, partial
import operator, itertools

nums = [3, 1, 4, 1, 5, 9, 2, 6]
m = map(lambda x: x * x, nums)
print(list(m), list(m))        # [9, 1, 16, 1, 25, 81, 4, 36] []  한 번 쓰면 끝
print(list(filter(lambda x: x % 2 == 0, nums)))            # [4, 2, 6]
print(reduce(lambda acc, x: acc + x, nums, 0),
      reduce(operator.mul, nums, 1))                        # 31 6480
print([x * x for x in nums if x % 2 == 0])                  # [16, 4, 36]

def compose(*fs):
    return reduce(lambda f, g: lambda x: g(f(x)), fs)
slugify = compose(str.strip, str.lower, lambda s: s.replace(" ", "-"))
print(slugify("  Hello World  "))                           # hello-world

words = "the cat and the hat and the bat".split()
counts = reduce(lambda acc, w: {**acc, w: acc.get(w, 0) + 1}, words, {})
print(counts)  # {'the': 3, 'cat': 1, 'and': 2, 'hat': 1, 'bat': 1}

pow2 = partial(pow, exp=2)
print(pow2(7))                                              # 49
print(list(itertools.accumulate([1, 2, 3, 4])))             # [1, 3, 6, 10]
reduce(operator.add, [])
# TypeError: reduce() of empty iterable with no initial value
```

단어 세기 예는 개념 설명용이다. 매 단계 딕셔너리를 통째로 복사하므로 O(n²) 이다. 실무에서는 `collections.Counter(words)` 를 쓴다.

JavaScript (Node.js 22):

```javascript
const xs = [3, 1, 4, 1, 5];
console.log(xs.map(x => x * 2).filter(x => x > 4).reduce((a, x) => a + x, 0)); // 24
console.log(["1", "2", "3"].map(parseInt));   // [ 1, NaN, NaN ]
```

## 현업에서는

- **스트림 처리 코드**: Java Stream, Kotlin 컬렉션 연산, JavaScript 배열 메서드로 쓴 데이터 가공 코드는 대부분 map·filter·reduce 의 조합이다. 각 단계가 무엇을 하는지 한 줄씩 읽힌다.
- **로그 분석**: `kubectl logs ... | grep ERROR | awk '{print $5}' | sort | uniq -c` 는 셸에서 쓰는 filter → map → reduce 다. 클러스터 장애를 볼 때 가장 먼저 손이 가는 패턴이다.
- **성능 주의**: 지연 반복자를 여러 번 소비하려다 두 번째에 빈 결과를 얻는 버그, 큰 배열에 `map().filter()` 를 길게 이어 중간 배열을 여러 개 만드는 비용, reduce 안에서 객체를 매번 복사하는 O(n²) 패턴을 리뷰에서 자주 본다.
- **가독성 기준**: 람다가 두세 줄을 넘거나 reduce 의 누적 로직이 복잡해지면 이름 붙은 함수나 평범한 `for` 문이 더 낫다. 고차 함수는 의도를 드러낼 때만 쓴다.

## 확인 문제

1. map, filter, reduce 를 각각 한 문장으로 정의하라.
2. 빈 리스트의 곱을 reduce 로 구할 때 초기값으로 무엇을 줘야 하는가?
3. Python 3 에서 `m = map(f, xs)` 후 `list(m)` 을 두 번 호출하면 두 번째 결과는?
4. `["1","2","3"].map(parseInt)` 가 `[1, 2, 3]` 이 아닌 이유는?
5. reduce 로 병렬 집계를 하려면 연산에 어떤 성질이 필요한가?

### 풀이

1. map 은 각 원소를 변환한 같은 길이의 컬렉션, filter 는 조건을 만족하는 원소만 남긴 컬렉션, reduce 는 누적 함수로 원소들을 하나의 값으로 접은 결과를 만든다.
2. 곱셈의 항등원 1.
3. 빈 리스트. `map` 은 한 번 소비되는 반복자다.
4. `map` 이 콜백에 인덱스를 두 번째 인자로 넘기고, `parseInt` 는 두 번째 인자를 진법으로 해석하기 때문이다. 진법 1 과 "3" 의 2진법 해석이 모두 `NaN` 이 된다.
5. 결합 법칙(묶는 순서와 무관)과 항등원. 덧붙여 교환 법칙이 있으면 조각을 아무 순서로 합칠 수 있다.

## 더 읽을거리 (References)

- Python Docs, [functools.reduce](https://docs.python.org/3/library/functools.html), [Built-in Functions — map, filter](https://docs.python.org/3/library/functions.html), [itertools](https://docs.python.org/3/library/itertools.html)
- MDN, [Array.prototype.map()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map), [Array.prototype.reduce()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/reduce)
- Jeffrey Dean, Sanjay Ghemawat, [MapReduce: Simplified Data Processing on Large Clusters](https://www.usenix.org/legacy/event/osdi04/tech/full_papers/dean/dean.pdf), OSDI 2004
