---
layout: post
title: "[CS300 #001] 명제 논리와 진리표 — 참과 거짓을 계산하는 법"
date: 2026-10-10 18:01:00 +0900
categories: [cs]
tags: [cs300, math, logic, propositional-logic, boolean]
---

컴퓨터공학 300 주제 시리즈의 001번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

명제 논리는 "참 또는 거짓인 문장"을 기호로 바꾸고, 연결사(그리고·또는·아니다·이면)로 묶어서 그 참거짓을 기계적으로 계산하는 체계다. 진리표는 그 계산을 가능한 모든 경우에 대해 펼쳐 놓은 표다.

## 왜 필요한가

프로그래밍에서 가장 자주 쓰는 수학이 명제 논리다. `if` 조건, 권한 검사, 피처 플래그, SQL 의 `WHERE` 절, 회로의 게이트가 모두 명제 논리식이다.

조건식이 조금만 길어지면 사람의 직관은 금방 틀린다. `!(a && b)` 가 `!a && !b` 와 같은지 헷갈린 적이 있다면, 그 순간 필요한 것이 진리표다. 진리표는 직관 대신 **모든 경우를 다 따져 보는** 방법이다. 경우의 수가 유한하기 때문에 이 방법은 언제나 끝나고, 언제나 정답을 낸다.

또 하나. 뒤에서 다룰 증명 기법(대우·귀류), 술어 논리, 회로 설계, SAT 문제는 모두 이 글의 연결사와 동치 법칙 위에 서 있다.

## 핵심 개념

### 명제와 연결사

**명제(proposition)** 는 참(T) 또는 거짓(F) 중 정확히 하나의 값을 갖는 문장이다. "3 은 소수다" 는 명제다. "x 는 소수다" 는 x 가 정해지기 전에는 참거짓이 없으므로 명제가 아니다(이건 다음 글의 술어다).

명제를 p, q, r 같은 **명제 변수**로 쓰고, 다음 연결사로 묶는다.

| 기호 | 이름 | 읽기 | 코드 |
|---|---|---|---|
| ¬p | 부정 | p 가 아니다 | `not p` |
| p ∧ q | 논리곱 | p 그리고 q | `p and q` |
| p ∨ q | 논리합 | p 또는 q (포함적) | `p or q` |
| p ⊕ q | 배타적 논리합 | 둘 중 정확히 하나 | `p != q` |
| p → q | 조건문(함의) | p 이면 q | `(not p) or q` |
| p ↔ q | 쌍조건문 | p 일 때 그리고 그때만 q | `p == q` |

### 진리표

변수가 n 개면 가능한 값의 조합은 2ⁿ 개다. 그 모든 행에 대해 식의 값을 적은 것이 진리표다.

```
 p  q | ¬p  p∧q  p∨q  p⊕q  p→q  p↔q
 T  T |  F   T    T    F    T    T
 T  F |  F   F    T    T    F    F
 F  T |  T   F    T    T    T    F
 F  F |  T   F    F    F    T    T
```

### 함의(→)가 가장 헷갈린다

p → q 는 **p 가 참인데 q 가 거짓인 경우에만 거짓**이다. 나머지 세 경우는 참이다. 특히 p 가 거짓이면 q 와 상관없이 참이 되는데, 이를 공허한 참(vacuous truth)이라 부른다.

약속으로 생각하면 쉽다. "비가 오면 우산을 가져간다" 는 약속은 비가 왔는데 우산을 안 가져갔을 때만 깨진다. 비가 안 온 날에는 무엇을 하든 약속을 어긴 게 아니다.

함의와 관련된 네 형태를 구분해 두자.

| 이름 | 형태 | 원래 식과 동치인가 |
|---|---|---|
| 원래 | p → q | — |
| 역(converse) | q → p | 아니다 |
| 이(inverse) | ¬p → ¬q | 아니다 |
| 대우(contrapositive) | ¬q → ¬p | 동치다 |

대우가 원래 식과 동치라는 사실은 증명 기법(대우 증명)의 근거가 된다.

### 항진식·모순식·논리적 동치

- **항진식(tautology)**: 모든 행에서 참. 예: p ∨ ¬p
- **모순식(contradiction)**: 모든 행에서 거짓. 예: p ∧ ¬p
- **충족 가능(satisfiable)**: 참이 되는 행이 하나라도 있음

두 식 A, B 가 모든 행에서 같은 값을 가지면 **논리적 동치**라 하고 A ≡ B 로 쓴다. 이는 A ↔ B 가 항진식이라는 말과 같다.

자주 쓰는 동치 법칙은 다음과 같다.

| 법칙 | 식 |
|---|---|
| 이중 부정 | ¬¬p ≡ p |
| 드모르간 | ¬(p ∧ q) ≡ ¬p ∨ ¬q, ¬(p ∨ q) ≡ ¬p ∧ ¬q |
| 분배 | p ∧ (q ∨ r) ≡ (p ∧ q) ∨ (p ∧ r) |
| 함의 제거 | p → q ≡ ¬p ∨ q |
| 대우 | p → q ≡ ¬q → ¬p |
| 흡수 | p ∨ (p ∧ q) ≡ p |

### 정규형과 함수적 완전성

어떤 진리표든 **참이 되는 행들을 OR 로 묶어** 식으로 되돌릴 수 있다. 이것이 선언 정규형(DNF)이다. 반대로 거짓이 되는 행을 막는 절들을 AND 로 묶으면 연언 정규형(CNF)이 된다. 따라서 {¬, ∧, ∨} 만으로 모든 진리함수를 표현할 수 있다. 이런 연결사 집합을 **함수적으로 완전하다**고 한다. NAND 하나만으로도 완전하다는 사실은 디지털 회로 설계의 출발점이다.

### 비용: 2ⁿ 의 벽

진리표는 확실하지만 변수 하나가 늘 때마다 행이 두 배가 된다. 변수 30 개면 약 10억 행이다. 그래서 큰 식의 충족 가능성(SAT)을 판정하는 일은 진리표 대신 영리한 탐색 알고리즘(SAT 솔버)에 맡긴다. SAT 는 NP-완전 문제의 대표이며, 복잡도 파트에서 다시 만난다.

## 직접 해 보기

진리표를 출력하고, 두 식이 동치인지 모든 경우를 대입해 확인하는 코드다.

```python
from itertools import product

def implies(p, q):
    return (not p) or q

def truth_table(names, expr):
    print(" ".join(names), "| result")
    for values in product([True, False], repeat=len(names)):
        env = dict(zip(names, values))
        row = " ".join("T" if v else "F" for v in values)
        print(row, "|", "T" if expr(**env) else "F")

def equivalent(n, f, g):
    return all(f(*v) == g(*v) for v in product([True, False], repeat=n))

truth_table(["p", "q"], lambda p, q: implies(p, q))

# 드모르간
print(equivalent(2, lambda p, q: not (p and q), lambda p, q: (not p) or (not q)))
# 대우는 동치, 역은 동치가 아니다
print(equivalent(2, lambda p, q: implies(p, q), lambda p, q: implies(not q, not p)))
print(equivalent(2, lambda p, q: implies(p, q), lambda p, q: implies(q, p)))
# 흔한 실수: not (a and b) 를 (not a) and (not b) 로 바꾸기
print(equivalent(2, lambda a, b: not (a and b), lambda a, b: (not a) and (not b)))
```

실행 결과다.

```
p q | result
T T | T
T F | F
F T | T
F F | T
True
True
False
False
```

마지막 줄이 `False` 다. 드모르간 법칙에서 부정을 안으로 넣을 때 AND 가 OR 로 바뀌어야 한다는 것을 기계가 확인해 준다.

## 현업에서는

- **조건문 리팩터링.** `if not (is_admin or is_owner):` 를 `if not is_admin and not is_owner:` 로 바꾸는 것은 드모르간 법칙이다. 리뷰에서 조건식을 바꾼 PR 을 볼 때, 변수가 2~3 개면 머릿속으로 진리표를 그려 보는 습관이 사고를 막는다.
- **단락 평가.** 파이썬의 `and`/`or` 는 왼쪽만으로 결과가 정해지면 오른쪽을 평가하지 않는다([Python 공식 문서, Boolean operations](https://docs.python.org/3/reference/expressions.html#boolean-operations)). 그래서 `user is not None and user.active` 처럼 앞의 조건으로 뒤의 오류를 막는 관용구가 생긴다. 논리적으로는 교환 법칙(p ∧ q ≡ q ∧ p)이 성립하지만, 부수효과와 예외까지 따지면 순서를 바꿀 수 없다는 점이 수학과 코드의 차이다.
- **SQL 의 3값 논리.** SQL 은 TRUE·FALSE 에 더해 NULL(알 수 없음)을 갖는다. PostgreSQL 문서의 진리표를 보면 `NULL AND FALSE` 는 FALSE 지만 `NULL AND TRUE` 는 NULL 이다([PostgreSQL, Logical Operators](https://www.postgresql.org/docs/current/functions-logical.html)). 그래서 `WHERE NOT (col = 1)` 은 col 이 NULL 인 행을 돌려주지 않는다. 2값 논리의 동치 법칙을 그대로 믿으면 행이 사라진다.
- **클러스터 설정.** 쿠버네티스 노드 어피니티에서 `nodeSelectorTerms` 여러 개는 OR, 한 항 안의 `matchExpressions` 여러 개는 AND 로 묶인다([Kubernetes, Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)). 즉 노드 선택 조건은 DNF 형태다. 파드가 "왜 이 노드에 안 뜨지?" 를 따질 때 이 구조를 알면 빨리 풀린다.

## 확인 문제

1. p → q 가 거짓이 되는 경우를 모두 적어라.
2. "테스트가 통과하면 배포한다" 의 대우를 써라.
3. (p → q) ∧ (q → p) 와 p ↔ q 가 동치임을 진리표로 보여라.
4. p ∨ (p ∧ q) 를 가장 간단한 식으로 줄여라.
5. 변수 20 개짜리 식의 진리표는 몇 행인가?

### 풀이

1. p 가 참이고 q 가 거짓인 한 경우뿐이다.
2. "배포하지 않았다면 테스트가 통과하지 않은 것이다." (¬q → ¬p)
3. 네 행(TT, TF, FT, FF)에서 두 식 모두 T, F, F, T 다. 따라서 동치다.
4. 흡수 법칙으로 p 다. p 가 참이면 전체가 참, p 가 거짓이면 두 항 모두 거짓이다.
5. 2²⁰ = 1,048,576 행이다.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 1–3장 — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Stanford Encyclopedia of Philosophy, Propositional Logic](https://plato.stanford.edu/entries/logic-propositional/)
- [PostgreSQL Documentation, Logical Operators](https://www.postgresql.org/docs/current/functions-logical.html)
- [Python Language Reference, Boolean operations](https://docs.python.org/3/reference/expressions.html#boolean-operations)
