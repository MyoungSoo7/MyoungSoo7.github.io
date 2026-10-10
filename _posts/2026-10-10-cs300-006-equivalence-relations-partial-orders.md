---
layout: post
title: "[CS300 #006] 동치 관계와 부분 순서 — 같음과 앞섬을 정의하는 규칙"
date: 2026-10-10 18:06:00 +0900
categories: [cs]
tags: [cs300, math, equivalence-relation, partial-order, topological-sort]
---

컴퓨터공학 300 주제 시리즈의 006번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

동치 관계는 반사·대칭·추이를 만족하는 "같다고 볼 수 있음" 의 관계이고, 집합을 겹치지 않는 묶음(동치류)으로 나눈다. 부분 순서는 반사·반대칭·추이를 만족하는 "앞선다" 의 관계이고, 비교할 수 없는 쌍이 있어도 된다.

## 왜 필요한가

프로그램은 끊임없이 "같은가?" 와 "어느 쪽이 앞인가?" 를 묻는다. `equals`, `__eq__`, 해시 키 비교, 정렬 비교 함수, 의존성 순서, 버전 비교가 모두 그렇다.

이 관계들이 수학적 규칙을 지키지 않으면 버그가 난다. 대칭이 아닌 `equals` 는 해시셋에서 원소를 잃어버리게 만든다. 추이성이 깨진 비교 함수는 정렬 결과를 뒤죽박죽으로 만든다. 그래서 자바 표준 라이브러리 문서는 `equals` 와 `compareTo` 가 지켜야 할 성질을 계약(contract)으로 명시한다. 그 계약이 바로 이 글의 정의다.

## 핵심 개념

### 동치 관계

집합 A 위의 관계 ~ 가 다음 셋을 만족하면 **동치 관계**다.

1. 반사성: 모든 a 에 대해 a ~ a
2. 대칭성: a ~ b 이면 b ~ a
3. 추이성: a ~ b 이고 b ~ c 이면 a ~ c

예:

- 정수에서 "n 으로 나눈 나머지가 같다"(a ≡ b mod n)
- 문자열에서 "대소문자를 무시하면 같다"
- 그래프에서 "서로 경로로 이어져 있다"(무향 그래프의 연결 요소)
- 파일에서 "내용의 해시가 같다"

반례: "두 실수의 차가 0.001 이하다" 는 반사적·대칭적이지만 추이적이지 않다. 0 과 0.0008, 0.0008 과 0.0016 은 가깝지만 0 과 0.0016 은 아니다. 부동소수점 값을 허용 오차로 비교하는 함수를 동치처럼 쓰면 안 되는 이유다.

### 동치류와 분할

a 와 동치인 원소들의 집합 [a] = {x : x ~ a} 를 a 의 **동치류**라 한다.

**정리.** 동치 관계의 동치류들은 A 의 **분할**을 이룬다. 즉 모든 원소는 정확히 하나의 동치류에 속하고, 서로 다른 동치류는 겹치지 않는다.

> **증명 요지.** 반사성 때문에 a ∈ [a] 이므로 모든 원소는 어떤 동치류에 속한다. 두 동치류 [a], [b] 가 원소 c 를 공유한다고 하자. c ~ a, c ~ b 이므로 대칭·추이성으로 a ~ b 다. 그러면 [a] 의 아무 원소 x 도 x ~ a ~ b 이므로 x ∈ [b] 다. 반대 방향도 같다. 따라서 겹치는 동치류는 같은 집합이다. ∎

역도 성립한다. 집합의 분할이 주어지면 "같은 조각에 속한다" 는 동치 관계다. 동치 관계와 분할은 같은 것을 두 방식으로 본 것이다.

mod 3 동치는 정수를 세 동치류로 나눈다.

```
[0] = {..., -3, 0, 3, 6, ...}
[1] = {..., -2, 1, 4, 7, ...}
[2] = {..., -1, 2, 5, 8, ...}
```

### 부분 순서

집합 A 위의 관계 ≼ 가 다음을 만족하면 **부분 순서**이고, (A, ≼) 를 부분 순서 집합(poset)이라 한다.

1. 반사성: a ≼ a
2. 반대칭성: a ≼ b 이고 b ≼ a 이면 a = b
3. 추이성: a ≼ b 이고 b ≼ c 이면 a ≼ c

예:

- 정수의 ≤
- 집합의 포함 관계 ⊆
- 양의 정수의 "나누어떨어진다"(a ∣ b)
- 작업 의존성 "a 가 끝나야 b 를 시작한다"(반사성을 더해 생각)

a ≼ b 또는 b ≼ a 인 쌍은 **비교 가능**하다. 모든 쌍이 비교 가능하면 **전순서(total order)** 다. 정수의 ≤ 는 전순서다. ⊆ 는 아니다. {1} 과 {2} 는 어느 쪽도 다른 쪽의 부분집합이 아니다. "부분" 순서라는 이름이 여기서 나온다.

### 하세 다이어그램과 위상 정렬

부분 순서는 반사 고리와 추이로 유도되는 선을 생략한 **하세 다이어그램**으로 그린다. {1, 2, 3, 4, 6, 12} 의 나눗셈 순서는 다음과 같다.

```
        12
       /  \
      4    6
       \  / \
        2    3
         \  /
          1
```

선을 따라 위로 올라갈 수 있으면 아래쪽이 위쪽을 나눈다. 2 와 3, 4 와 6 은 서로 비교할 수 없다.

**위상 정렬**은 부분 순서를 거스르지 않는 전순서 하나를 고르는 일이다. 즉 a ≼ b 면 결과 목록에서 a 가 b 보다 앞에 온다. 유한 부분 순서에는 위상 정렬이 항상 존재한다. 의존성 그래프에 순환이 있으면 반대칭성이 깨진 것이므로 부분 순서가 아니고, 위상 정렬도 불가능하다.

### 엄격한 순서와 정렬 비교 함수

< 처럼 반사성 대신 비반사성(어떤 a 도 a < a 가 아님)을 갖는 순서를 엄격한 순서라 한다. 정렬 알고리즘이 요구하는 비교 함수는 대개 엄격한 약순서(strict weak ordering)다. C++ 표준 라이브러리는 이 요구사항을 Compare 명세로 정의한다([cppreference, Compare](https://en.cppreference.com/w/cpp/named_req/Compare)). 비교 함수가 추이성을 어기면 정렬 결과는 정의되지 않는다.

## 직접 해 보기

mod 동치로 정수를 분할하고, 나눗셈 순서를 파이썬 표준 라이브러리 `graphlib` 으로 위상 정렬해 보자. `graphlib.TopologicalSorter` 는 순환이 있으면 `CycleError` 를 낸다.

```python
from collections import defaultdict
from graphlib import TopologicalSorter, CycleError

# 1) 동치류로 분할
classes = defaultdict(list)
for x in range(-6, 10):
    classes[x % 3].append(x)
print(dict(classes))

# 2) 동치 관계 성질 검사기
def is_equivalence(R, A):
    refl = all(R(a, a) for a in A)
    sym = all(R(b, a) for a in A for b in A if R(a, b))
    trans = all(R(a, c) for a in A for b in A for c in A if R(a, b) and R(b, c))
    return refl, sym, trans

A = [i * 0.0008 for i in range(4)]
print(is_equivalence(lambda a, b: abs(a - b) <= 0.001, A))   # 추이성 실패

# 3) 나눗셈 순서의 위상 정렬 (각 원소의 '앞서야 하는 것'을 넘긴다)
S = [1, 2, 3, 4, 6, 12]
graph = {b: {a for a in S if a != b and b % a == 0} for b in S}
print(list(TopologicalSorter(graph).static_order()))

# 4) 순환이 있으면 부분 순서가 아니다
try:
    list(TopologicalSorter({"a": {"b"}, "b": {"c"}, "c": {"a"}}).static_order())
except CycleError as e:
    print("CycleError:", e.args[1])
```

실행 결과 예시다(위상 정렬 결과는 여러 개가 가능하다).

```
{0: [-6, -3, 0, 3, 6, 9], 1: [-5, -2, 1, 4, 7], 2: [-4, -1, 2, 5, 8]}
(True, True, False)
[1, 2, 3, 4, 6, 12]
CycleError: ['a', 'c', 'b', 'a']
```

파이썬의 `%` 는 음수에서도 0 이상의 나머지를 돌려준다. 그래서 -5 가 [1] 에 들어간다. C 나 자바의 `%` 는 피제수의 부호를 따르므로 같은 코드가 음수 키를 엉뚱한 곳에 넣는다. 언어마다 나머지 정의가 다르다는 점은 011번 글에서 다시 다룬다.

## 현업에서는

- **equals 와 hashCode 계약.** 자바 `Object.equals` 문서는 반사·대칭·추이·일관성을 요구하고, 같은 객체는 같은 `hashCode` 를 가져야 한다고 명시한다([Java SE 21, Object](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html)). 해시 테이블은 동치류마다 같은 해시 값을 갖는다고 가정하고 버킷을 찾기 때문이다. 파이썬도 같은 규칙을 데이터 모델 문서의 `__hash__` 항목에 둔다([Python Data Model](https://docs.python.org/3/reference/datamodel.html#object.__hash__)).
- **compareTo 와 equals 의 일치.** `Comparable` 문서는 `compareTo` 가 0 을 돌려주는 것과 `equals` 가 참인 것이 일치하도록 권장한다. 그렇지 않으면 `TreeSet` 과 `HashSet` 이 같은 원소들에 대해 다른 크기를 보고할 수 있다([Java SE 21, Comparable](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Comparable.html)).
- **분산 시스템의 사건 순서.** 램포트는 분산 시스템의 사건 사이에 "happened before" 관계를 정의했다. 이 관계는 엄격한 부분 순서이며, 동시에 일어난 두 사건은 비교할 수 없다([Lamport, Time, Clocks, and the Ordering of Events in a Distributed System, 1978](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)). 논리 시계는 이 부분 순서를 거스르지 않는 전순서를 만드는 방법이다.
- **배포 의존성.** 헬름 차트 설치 순서, 데이터베이스 마이그레이션 순서, 빌드 단계 순서가 모두 위상 정렬 문제다. 순환 의존이 생기면 어느 도구든 "cycle detected" 류의 오류를 낸다. 그 오류는 "이 관계는 부분 순서가 아니다" 라는 수학적 진술이다.

## 확인 문제

1. "같은 생일을 가졌다" 는 사람들 위의 동치 관계인가? 동치류는 몇 개까지 생길 수 있는가?
2. 집합 {1, 2, 3} 의 멱집합 위에서 ⊆ 순서로 비교할 수 없는 쌍을 하나 들어라.
3. 정수 위의 관계 "a < b 또는 a = b" 는 어떤 순서인가?
4. 비교 함수 `cmp(a, b)` 가 추이성을 어기면 정렬에 어떤 일이 생길 수 있는가?

### 풀이

1. 그렇다. 반사·대칭·추이가 모두 성립한다. 2월 29일을 포함하면 동치류는 최대 366 개다.
2. {1} 과 {2}, 또는 {1, 2} 와 {3}.
3. ≤ 이며 전순서다.
4. 정렬 알고리즘은 추이성을 가정하고 비교를 생략하므로, 결과가 정렬되지 않거나 실행할 때마다 달라질 수 있다. 언어에 따라서는 예외가 나기도 한다.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 10장 Directed graphs & Partial Orders — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Java SE 21 API, java.lang.Object (equals, hashCode)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html)
- [Python Documentation, graphlib — Functionality to operate with graph-like structures](https://docs.python.org/3/library/graphlib.html)
- Leslie Lamport, [Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.azurewebsites.net/pubs/time-clocks.pdf), *Communications of the ACM*, 21(7), 1978
