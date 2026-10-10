---
layout: post
title: "[CS300 #005] 집합·관계·함수 — 모든 자료 구조의 바탕 언어"
date: 2026-10-10 18:05:00 +0900
categories: [cs]
tags: [cs300, math, set-theory, relation, function]
---

컴퓨터공학 300 주제 시리즈의 005번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

집합은 원소들의 모임, 관계는 두 집합의 원소 쌍들의 집합, 함수는 각 입력에 출력이 정확히 하나씩 대응하는 특별한 관계다. 이 세 개념만으로 데이터베이스 테이블, 해시맵, 타입, 그래프를 모두 설명할 수 있다.

## 왜 필요한가

관계형 데이터베이스의 "관계(relation)" 는 이 글의 관계와 같은 단어다. 테이블은 튜플의 집합이고, SQL 의 `UNION`, `INTERSECT`, `EXCEPT` 는 집합 연산이다. 파이썬의 `dict` 는 유한 함수이고, 타입은 값들의 집합이다.

함수의 성질(단사·전사·전단사)은 실무 질문으로 바로 이어진다. 해시 함수는 왜 충돌을 피할 수 없는가? 암호화는 왜 반드시 되돌릴 수 있어야 하는가? ID 매핑 테이블이 일대일인가? 이 질문들은 모두 함수의 성질에 대한 질문이다.

## 핵심 개념

### 집합

**집합**은 서로 다른 원소의 모임이며 순서와 중복이 없다. {1, 2, 3} = {3, 1, 2} = {1, 1, 2, 3}. 이 글에서는 집합 A 의 원소 개수를 n(A) 로 쓴다.

| 연산 | 기호 | 정의 | 파이썬 |
|---|---|---|---|
| 합집합 | A ∪ B | A 또는 B 에 속함 | `A.union(B)` |
| 교집합 | A ∩ B | A 와 B 모두에 속함 | `A.intersection(B)`, `A & B` |
| 차집합 | A − B | A 에 속하고 B 에 속하지 않음 | `A.difference(B)`, `A - B` |
| 대칭차 | A △ B | 둘 중 정확히 하나에 속함 | `A.symmetric_difference(B)`, `A ^ B` |
| 부분집합 | A ⊆ B | A 의 모든 원소가 B 에 속함 | `A.issubset(B)`, `A <= B` |
| 여집합 | Aᶜ | 전체집합 U 에서 A 를 뺀 것 | `U - A` |

집합 연산은 논리 연결사와 짝을 이룬다. ∪ 는 ∨, ∩ 는 ∧, 여집합은 ¬ 에 해당한다. 그래서 드모르간 법칙이 집합에서도 성립한다: (A ∪ B)ᶜ = Aᶜ ∩ Bᶜ.

- **멱집합(power set)** P(A): A 의 모든 부분집합의 집합. n(A) = n 이면 n(P(A)) = 2ⁿ 이다. 각 원소를 "넣는다/뺀다" 두 가지로 고르기 때문이다. 비트마스크로 부분집합을 표현하는 기법의 근거다.
- **곱집합(Cartesian product)** A × B = {(a, b) : a ∈ A, b ∈ B}. 순서쌍이므로 (a, b) ≠ (b, a) 일 수 있다. n(A × B) = n(A)·n(B). SQL 의 `CROSS JOIN` 이 바로 이것이다.

### 관계

A 에서 B 로의 **이항 관계** R 은 A × B 의 부분집합이다. (a, b) ∈ R 이면 a R b 로 쓴다.

예: A = 학생, B = 강의, R = "수강한다". 수강 테이블의 각 행이 순서쌍 하나다. 관계는 표, 순서쌍 목록, 0/1 행렬, 화살표 그림(유향 그래프)으로 나타낼 수 있다.

A 에서 A 로의 관계(집합 위의 관계)에서는 다음 성질이 중요하다. 다음 글에서 동치 관계와 부분 순서를 정의할 때 그대로 쓴다.

| 성질 | 정의 | 예 (정수 위) |
|---|---|---|
| 반사적 | 모든 a 에 대해 a R a | ≤ 는 반사적, < 는 아님 |
| 대칭적 | a R b 이면 b R a | = 는 대칭, ≤ 는 아님 |
| 반대칭적 | a R b 이고 b R a 이면 a = b | ≤ |
| 추이적 | a R b 이고 b R c 이면 a R c | <, ≤, = 모두 |

관계의 **합성** S ∘ R 은 a R b 이고 b S c 인 b 가 있으면 a 와 c 를 잇는다. SQL 의 조인이 정확히 이 연산이다.

### 함수

A 에서 B 로의 **함수** f: A → B 는 모든 a ∈ A 에 대해 (a, b) ∈ f 인 b 가 **정확히 하나** 있는 관계다. A 는 정의역, B 는 공역, 실제로 나오는 값들의 집합 f(A) 는 치역(상)이다.

| 성질 | 정의 | 직관 |
|---|---|---|
| 단사(injective, 일대일) | f(a₁) = f(a₂) 이면 a₁ = a₂ | 서로 다른 입력은 서로 다른 출력 |
| 전사(surjective, 위로) | 모든 b ∈ B 에 대해 f(a) = b 인 a 존재 | 공역을 빠짐없이 덮음 |
| 전단사(bijective) | 단사이면서 전사 | 완벽한 짝짓기, 역함수 존재 |

유한 집합에서 다음이 성립한다.

- 단사 f: A → B 가 있으면 n(A) ≤ n(B).
- 전사 f: A → B 가 있으면 n(A) ≥ n(B).
- 전단사가 있으면 n(A) = n(B). 두 집합의 크기가 같다는 것의 정의가 이것이다.

n(A) > n(B) 이면 단사가 불가능하다. 이것이 비둘기집 원리이고(007번 글), 해시 충돌이 피할 수 없는 이유다.

함수의 **합성** (g ∘ f)(x) = g(f(x)) 와 **역함수** f⁻¹ 은 전단사일 때만 정의된다. 인코딩·디코딩, 직렬화·역직렬화, 암호화·복호화는 모두 "역함수가 존재해야 하는" 쌍이다.

### 부분 함수

프로그래밍에서는 일부 입력에 값이 없는 **부분 함수**가 흔하다. `dict` 에 없는 키, 0 으로 나누기, 빈 리스트의 `max` 가 그 예다. 수학의 함수는 정의역 전체에서 정의돼야 하므로, 코드에서는 예외, `None`, `Optional` 타입으로 "값이 없음" 을 명시한다.

## 직접 해 보기

파이썬 집합으로 드모르간 법칙을 확인하고, 함수의 단사·전사 여부를 판정하는 코드를 짜 보자. 파이썬 집합 연산은 공식 문서의 set 타입에 정의돼 있다.

```python
from itertools import chain, combinations

U = set(range(10))
A = {1, 2, 3, 4}
B = {3, 4, 5, 6}
print(A | B, A & B, A - B, A ^ B)
print(U - (A | B) == (U - A) & (U - B))       # 드모르간

def powerset(s):
    s = list(s)
    return [set(c) for c in chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))]
print(len(powerset({'a', 'b', 'c'})))           # 2^3

def kind(f, domain, codomain):
    image = [f(x) for x in domain]
    inj = len(set(image)) == len(image)
    sur = set(image) == set(codomain)
    return inj, sur

print(kind(lambda x: 2 * x, range(5), range(10)))           # 단사, 전사 아님
print(kind(lambda x: x % 3, range(9), range(3)))            # 전사, 단사 아님
print(kind(lambda x: (x * 7) % 10, range(10), range(10)))   # 전단사
```

실행 결과다.

```
{1, 2, 3, 4, 5, 6} {3, 4} {1, 2} {1, 2, 5, 6}
True
8
(True, False)
(False, True)
(True, True)
```

마지막 줄의 x ↦ 7x mod 10 이 전단사인 이유는 7 과 10 이 서로소이기 때문이다. 012번 글(모듈러 역원)에서 이 사실을 정확히 증명한다.

## 현업에서는

- **SQL 은 집합 연산이다.** `UNION`, `INTERSECT`, `EXCEPT` 는 각각 합집합·교집합·차집합이며, 기본적으로 중복을 제거한다. 중복을 남기려면 `UNION ALL` 을 쓴다([PostgreSQL, Combining Queries](https://www.postgresql.org/docs/current/queries-union.html)). 엄밀히 말하면 SQL 테이블은 중복 행을 허용하므로 집합이 아니라 다중집합(bag)이다. 이 차이 때문에 `DISTINCT` 가 필요하다.
- **쿠버네티스 셀렉터는 집합 질의다.** `environment in (production, qa)`, `tier notin (frontend)` 같은 집합 기반 셀렉터는 원소 판정(∈, ∉)이다([Kubernetes, Labels and Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)).
- **해시 함수는 단사가 아니다.** 임의 길이의 입력을 고정 길이 출력으로 보내므로 정의역이 공역보다 크다. 충돌은 반드시 존재하며, 좋은 해시 함수는 충돌을 "찾기 어렵게" 만들 뿐이다.
- **ID 매핑 검증.** 마이그레이션에서 옛 ID → 새 ID 매핑을 만들 때 단사인지(두 옛 ID 가 같은 새 ID 로 가지 않는지), 전사인지(새 쪽에 주인 없는 ID 가 없는지)를 확인한다. 위의 `kind` 함수가 그대로 검증 스크립트가 된다.

## 확인 문제

1. A = {1, 2}, B = {x, y, z} 일 때 n(A × B) 와 n(P(A × B)) 는?
2. 정수 위의 관계 "a 와 b 의 차가 짝수다" 는 반사적·대칭적·추이적인가?
3. f: 정수 → 정수, f(x) = x² 는 단사인가, 전사인가?
4. 원소 5 개 집합에서 원소 3 개 집합으로 가는 단사 함수가 없는 이유는?

### 풀이

1. n(A × B) = 6, n(P(A × B)) = 2⁶ = 64.
2. 셋 다 성립한다. a - a = 0 은 짝수, a - b 가 짝수면 b - a 도 짝수, 짝수 + 짝수는 짝수다. 따라서 동치 관계다(다음 글).
3. 둘 다 아니다. f(1) = f(-1) 이므로 단사가 아니고, 2 를 출력하는 정수가 없으므로 전사가 아니다.
4. 서로 다른 5 개 입력이 서로 다른 출력을 가지려면 출력이 5 개 이상 필요하다. 비둘기집 원리다.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 4장 Mathematical Data Types — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Python Documentation, Set Types — set, frozenset](https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset)
- [PostgreSQL Documentation, Combining Queries (UNION, INTERSECT, EXCEPT)](https://www.postgresql.org/docs/current/queries-union.html)
- E. F. Codd, "A Relational Model of Data for Large Shared Data Banks", *Communications of the ACM*, 13(6), 1970
