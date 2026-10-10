---
layout: post
title: "[CS300 #002] 술어 논리와 한정자 — 모든 것과 어떤 것을 정확히 말하기"
date: 2026-10-10 18:02:00 +0900
categories: [cs]
tags: [cs300, math, logic, predicate-logic, quantifiers]
---

컴퓨터공학 300 주제 시리즈의 002번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

술어 논리는 "x 는 소수다" 처럼 변수를 품은 문장(술어)과 "모든 x 에 대해"(∀), "어떤 x 가 존재해서"(∃) 라는 한정자를 써서, 명제 논리로는 표현할 수 없는 일반 명제를 정확히 적는 언어다.

## 왜 필요한가

명제 논리는 "3 은 소수다", "5 는 소수다" 를 각각 따로 다룬다. 하지만 우리가 정말 말하고 싶은 것은 "2 보다 큰 모든 소수는 홀수다" 같은 일반 명제다. 원소가 무한히 많은 대상에 대해 진리표를 그릴 수는 없다.

프로그래밍에서도 똑같다. "모든 파드가 Ready 다", "만료된 토큰이 하나라도 있다", "모든 주문에 대해 결제 기록이 존재한다". 테스트의 단언문, 데이터베이스 제약, API 명세가 전부 한정자로 쓰인 문장이다. 한정자의 순서나 부정을 잘못 다루면 정반대의 조건을 검사하게 된다.

## 핵심 개념

### 술어와 논의 영역

**술어(predicate)** 는 변수를 받아 참거짓을 돌려주는 함수다. P(x) = "x 는 짝수다" 라고 하면 P(4) 는 참, P(7) 은 거짓이다. 변수를 두 개 받는 Q(x, y) = "x < y" 도 술어다.

변수가 어떤 값의 범위에서 움직이는지를 **논의 영역(domain of discourse)** 이라 한다. 같은 문장도 영역에 따라 참거짓이 바뀐다. "모든 x 에 대해 x² ≥ x" 는 정수 영역에서 참이지만, 실수 영역에서는 x = 0.5 때문에 거짓이다. 그래서 한정자를 쓸 때는 영역을 반드시 함께 밝힌다.

### 두 한정자

| 기호 | 이름 | 의미 | 참이 되려면 | 거짓임을 보이려면 |
|---|---|---|---|---|
| ∀x P(x) | 전칭 한정자 | 모든 x 에 대해 P(x) | 영역의 모든 원소가 만족 | 반례 하나 |
| ∃x P(x) | 존재 한정자 | P(x) 인 x 가 있다 | 예 하나 | 모든 원소가 불만족 |

영역이 유한하다면 ∀ 는 긴 AND, ∃ 는 긴 OR 이다. 영역 {a, b, c} 에서 ∀x P(x) ≡ P(a) ∧ P(b) ∧ P(c) 다.

빈 영역에서는 ∀x P(x) 가 참, ∃x P(x) 가 거짓이다. 지난 글에서 본 공허한 참과 같은 이야기다. 파이썬의 `all([])` 이 `True`, `any([])` 가 `False` 인 이유도 이것이다([Python 내장 함수 all, any](https://docs.python.org/3/library/functions.html#all)).

### 한정자의 부정 — 드모르간의 일반화

```
¬∀x P(x)  ≡  ∃x ¬P(x)     "모두가 그렇진 않다" = "그렇지 않은 것이 있다"
¬∃x P(x)  ≡  ∀x ¬P(x)     "그런 것이 없다"     = "모두가 그렇지 않다"
```

부정 기호가 한정자를 통과할 때마다 ∀ 와 ∃ 가 서로 바뀐다. 여러 겹이어도 같은 규칙을 차례로 쓰면 된다.

```
¬∀x ∃y P(x, y)  ≡  ∃x ¬∃y P(x, y)  ≡  ∃x ∀y ¬P(x, y)
```

### 제한된 한정자

"모든 양수 x 에 대해 ..." 처럼 범위를 좁힐 때는 형태가 정해져 있다.

- 모든 S 인 x 가 P 다: ∀x (S(x) → P(x))
- 어떤 S 인 x 가 P 다: ∃x (S(x) ∧ P(x))

∀ 에는 →, ∃ 에는 ∧ 가 붙는다. ∃x (S(x) → P(x)) 라고 쓰면, S 가 아닌 원소 하나만 있어도 함의가 공허하게 참이 되어 식 전체가 참이 된다. 초보자가 가장 자주 하는 실수다.

### 한정자의 순서

같은 종류의 한정자끼리는 순서를 바꿔도 된다. 다른 종류는 안 된다.

```
∀x ∃y (y > x)   정수에서 참: 어떤 수를 줘도 그보다 큰 수가 있다
∃y ∀x (y > x)   정수에서 거짓: 모든 수보다 큰 하나의 수는 없다
```

첫 문장에서 y 는 x 에 따라 달라져도 된다. 둘째 문장에서는 y 를 먼저 하나 골라 고정해야 한다. 순서가 곧 "누가 먼저 고르느냐" 다. 이 차이가 극한의 ε-δ 정의, 알고리즘 복잡도의 Big-O 정의(∃c ∃n₀ ∀n ≥ n₀ ...)를 읽는 열쇠다.

### 자유 변수와 묶인 변수

∀x P(x, y) 에서 x 는 한정자에 **묶인 변수**, y 는 **자유 변수**다. 자유 변수가 남아 있으면 그 식은 아직 명제가 아니다. 프로그래밍의 지역 변수와 바깥 스코프 변수의 관계와 닮았다.

## 직접 해 보기

유한 영역에서 한정자는 `all` 과 `any` 로 그대로 옮겨진다. 한정자 순서를 바꾸면 결과가 달라지는 것도 직접 확인해 보자.

```python
D = range(1, 11)          # 논의 영역: 1..10

def is_prime(n):
    return n >= 2 and all(n % d for d in range(2, int(n**0.5) + 1))

# ∀x (x 가 2보다 큰 소수 → x 는 홀수)
print(all((not (is_prime(x) and x > 2)) or x % 2 == 1 for x in D))

# ∃x (x 는 소수 ∧ x 는 짝수)
print(any(is_prime(x) and x % 2 == 0 for x in D))

# 부정 법칙 확인: ¬∀x P(x) == ∃x ¬P(x)
P = lambda x: x < 8
print((not all(P(x) for x in D)) == any(not P(x) for x in D))

# 한정자 순서: ∀x ∃y (x + y == 11) vs ∃y ∀x (x + y == 11)
print(all(any(x + y == 11 for y in D) for x in D))
print(any(all(x + y == 11 for x in D) for y in D))

# 흔한 실수: 제한된 존재 한정자에 → 를 쓰면
S = lambda x: x > 100     # 영역에 S 를 만족하는 원소가 없다
print(any((not S(x)) or x == 0 for x in D))   # ∃x (S(x) → x == 0): 엉뚱하게 참
print(any(S(x) and x == 0 for x in D))        # ∃x (S(x) ∧ x == 0): 거짓
```

실행 결과다.

```
True
True
True
True
False
True
False
```

넷째, 다섯째 줄이 한정자 순서의 차이다. 모든 x 에 대해 짝이 되는 y 는 있지만, 모든 x 와 짝이 되는 단 하나의 y 는 없다.

## 현업에서는

- **SQL 의 EXISTS 와 ALL.** `WHERE EXISTS (서브쿼리)` 는 ∃, `x > ALL (서브쿼리)` 는 ∀ 다([PostgreSQL, Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html)). SQL 에는 ∀ 를 직접 쓰는 문법이 마땅치 않아서, "모든 강의를 들은 학생" 같은 질의는 `NOT EXISTS (... NOT EXISTS ...)` 로 쓴다. 바로 ∀x P(x) ≡ ¬∃x ¬P(x) 다.
- **빈 집합의 함정.** "모든 파드가 Ready 면 배포 성공" 을 `all(pod.ready for pod in pods)` 로 짰다면, 파드가 하나도 안 떴을 때도 성공으로 판정한다. 헬스체크에서 실제로 자주 나오는 버그다. 의도가 "적어도 하나 있고 모두 Ready" 라면 `pods and all(...)` 로 써야 한다.
- **쿠버네티스 레이블 셀렉터.** 셀렉터의 여러 요구사항은 모두 만족해야 하는 AND 이고, `in`, `notin`, `exists` 같은 집합 기반 연산자를 쓴다([Kubernetes, Labels and Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)). "이 셀렉터에 걸리는 파드가 존재하는가(∃)" 와 "모든 파드가 걸리는가(∀)" 를 구분하지 않으면 서비스 엔드포인트가 비는 이유를 찾기 어렵다.
- **명세와 테스트.** 속성 기반 테스트(property-based testing)는 "모든 입력 x 에 대해 decode(encode(x)) == x" 같은 ∀ 문장을 무작위 표본으로 반박하려 시도한다. 반례 하나면 ∀ 가 깨진다는 성질을 그대로 이용하는 방식이다.

## 확인 문제

1. 정수 영역에서 ∃x (x² = 2) 의 참거짓은?
2. ¬∀x ∃y (x < y) 를 부정 기호가 술어 바로 앞에만 오도록 바꿔라.
3. "모든 관리자는 2단계 인증을 켰다" 를 술어 A(x), T(x) 로 써라.
4. 3 번 문장의 부정을 자연어로 써라.
5. 파이썬 `all([])` 이 `True` 인 이유를 한정자로 설명하라.

### 풀이

1. 거짓이다. 제곱해서 2 가 되는 정수는 없다.
2. ∃x ∀y ¬(x < y), 즉 ∃x ∀y (x ≥ y). "모든 수보다 크거나 같은 수가 있다." 정수에서는 거짓이다.
3. ∀x (A(x) → T(x)).
4. ∃x (A(x) ∧ ¬T(x)). "2단계 인증을 켜지 않은 관리자가 적어도 한 명 있다."
5. 빈 영역에서 ∀x P(x) 를 반박할 반례가 없으므로 참이다. 유한 영역의 ∀ 를 AND 의 연쇄로 보면, 항이 없는 AND 의 항등원이 참인 것과 같다.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 3장 — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Stanford Encyclopedia of Philosophy, Classical Logic](https://plato.stanford.edu/entries/logic-classical/)
- [PostgreSQL Documentation, Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html)
- [Python Documentation, Built-in Functions — all(), any()](https://docs.python.org/3/library/functions.html)
