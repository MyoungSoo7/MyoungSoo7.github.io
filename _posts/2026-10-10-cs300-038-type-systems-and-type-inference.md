---
layout: post
title: "[CS300 #038] 타입 시스템과 타입 추론 — 적지 않아도 아는 컴파일러"
date: 2026-10-10 18:38:00 +0900
categories: [cs]
tags: [cs300, programming, type-system, type-inference, hindley-milner]
---

컴퓨터공학 300 주제 시리즈의 038번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

타입 시스템은 식에 타입을 붙이는 규칙의 모음으로 특정 종류의 오류가 실행 중에 일어나지 않음을 증명하는 도구이며, 타입 추론은 프로그래머가 적지 않은 타입을 그 규칙으로부터 역산해 채우는 기술이다.

## 왜 필요한가

#026 에서 정적 타입의 이점을 봤다. 그런데 Java 1.4 시절처럼 `Map<String, List<Integer>> m = new HashMap<String, List<Integer>>();` 를 매번 쓰는 것은 고역이다. 타입이 장황하면 사람들은 정적 타입 자체를 싫어하게 된다.

타입 추론은 이 비용을 줄인다. Haskell, OCaml 은 함수 시그니처 하나 없이도 프로그램 전체의 타입을 알아낸다. Rust, Kotlin, TypeScript, Java 의 `var`, C++ 의 `auto` 는 지역 변수 수준에서 같은 혜택을 준다. 추론이 어떻게 동작하는지 알면, 컴파일러가 "타입을 알 수 없다"고 할 때나 엉뚱한 타입을 추론했을 때 원인을 빨리 찾는다.

## 핵심 개념

### 타입 시스템이란

피어스(Pierce)의 교과서 『Types and Programming Languages』는 타입 시스템을 "구문 구조를 그것이 계산하는 값의 종류에 따라 분류함으로써, 특정 프로그램 동작이 일어나지 않음을 증명하는, 다루기 쉬운 문법적 방법"이라고 정의한다. 핵심 단어는 **증명**이다. 타입 검사는 실행해 보지 않고 프로그램의 성질을 보장한다.

타입 시스템은 보통 **타입 규칙**으로 쓴다. 가로줄 위가 전제, 아래가 결론이다.

```
  Γ ⊢ e1 : int    Γ ⊢ e2 : int          Γ ⊢ c : bool   Γ ⊢ t : T   Γ ⊢ f : T
 ─────────────────────────────         ─────────────────────────────────────
     Γ ⊢ e1 + e2 : int                       Γ ⊢ if c then t else f : T
```

"환경 Γ 에서 e1 과 e2 가 int 면 e1 + e2 도 int 다", "조건이 bool 이고 두 분기의 타입이 같으면 if 식은 그 타입이다." 이런 규칙 몇 개가 언어 전체의 타입 검사를 정의한다.

### 건전성: 진행과 보존

타입 시스템이 **건전(sound)** 하다는 것은 보통 두 정리로 보인다.

- **진행(progress)**: 타입이 맞는 식은 값이거나, 한 단계 더 계산할 수 있다. 막히지 않는다.
- **보존(preservation)**: 타입이 맞는 식을 한 단계 계산해도 타입이 유지된다.

둘을 합치면 "타입 검사를 통과한 프로그램은 실행 중에 정의되지 않은 상태에 빠지지 않는다"가 된다. 밀너(Milner)는 1978년 논문에서 이를 "Well-typed programs cannot go wrong"이라는 문장으로 남겼다.

### 다형성과 타입 시스템의 표현력

| 기능 | 예 | 표현하는 것 |
|---|---|---|
| 매개변수 다형성 | `∀a. a -> a` | 모든 타입에 같은 동작(#033) |
| 서브타이핑 | `Cat <: Animal` | 대체 가능성(#030) |
| 합 타입 | `Result<T, E>`, `Option<T>` | "이것 또는 저것" |
| 널 가능성 | `String?` vs `String` | 널 참조 오류의 제거 |
| 소유·수명 | Rust 의 `&'a T` | 메모리 안전성(#040) |

타입 시스템이 표현력이 클수록 더 많은 오류를 컴파일 시점에 막지만, 검사와 추론은 어려워진다.

### 타입 추론의 원리: 제약을 세우고 푼다

추론은 세 단계로 이해할 수 있다.

1. **모르는 타입에 변수를 붙인다.** `λx. x + 1` 의 `x` 타입을 `t0` 라 둔다.
2. **타입 규칙에서 제약을 모은다.** `+` 의 규칙은 피연산자가 int 여야 하므로 `t0 = int`.
3. **제약을 푼다(단일화, unification).** 두 타입을 같게 만드는 대입을 찾는다. 해가 있으면 그것이 타입, 없으면 타입 오류.

단일화의 규칙은 단순하다.
- 타입 변수와 아무 타입: 변수를 그 타입으로 묶는다. 단 변수가 그 타입 안에 들어 있으면 안 된다(**출현 검사**). `t = t -> int` 같은 무한 타입을 막기 위해서다.
- 같은 모양의 타입(`a -> b` 와 `c -> d`): 부분끼리 단일화한다.
- 다른 기본 타입(`int` 와 `bool`): 실패.

이 방식을 체계화한 것이 **힌들리-밀너(Hindley-Milner) 타입 추론**이다. 밀너가 1978년 논문에서 알고리즘 W 를 제시했고([A theory of type polymorphism in programming](https://doi.org/10.1016/0022-0000%2878%2990014-4)), 다마스(Damas)와 밀너가 1982년 그것이 가장 일반적인 타입(principal type)을 찾음을 보였다. 여기에 `let` 으로 묶은 이름을 일반화하는 **let-다형성**이 더해지면, 타입 주석 없이도 `id` 함수를 정수와 문자열에 모두 쓸 수 있다. ML, OCaml, Haskell 의 바탕이다.

### 주류 언어의 추론은 지역적이다

Java, C#, TypeScript, Kotlin, Rust 는 전역 HM 추론 대신 **지역 추론**을 주로 쓴다. 함수 시그니처는 사람이 적고, 함수 안의 변수 타입은 초기값에서 추론한다. 이유는 서브타이핑·오버로딩과 HM 이 잘 어울리지 않고, 시그니처가 문서이자 오류 위치를 좁히는 경계 역할을 하기 때문이다.

- **Java**: Java 10 의 JEP 286 이 지역 변수 `var` 를 도입했다. 필드나 메서드 시그니처에는 쓸 수 없다([JEP 286](https://openjdk.org/jeps/286)).
- **TypeScript**: 초기값에서 추론하고, 여러 후보가 있으면 "최적 공통 타입"을, 콜백 매개변수처럼 위치가 정해 주면 "문맥적 타입"을 쓴다([Type Inference](https://www.typescriptlang.org/docs/handbook/type-inference.html)).
- **mypy**: 주석이 없는 변수는 첫 대입에서 추론하고, 빈 컬렉션처럼 알 수 없는 경우에는 주석을 요구한다([Type inference and type annotations](https://mypy.readthedocs.io/en/stable/type_inference_and_annotations.html)).

## 직접 해 보기

단일화 기반 추론기를 50줄로 만들어 본다. 작은 람다 언어(정수, 불리언, 덧셈, if, 함수, 적용)를 대상으로 한다. let-다형성은 생략했다. Python 3.12.3 에서 실행했다.

```python
import itertools

class TVar:                               # 타입 변수
    _ids = itertools.count()
    def __init__(self): self.id = next(TVar._ids); self.ref = None
    def __repr__(self): return f"t{self.id}" if self.ref is None else repr(self.ref)

def prune(t):                             # 묶인 변수를 따라가 실제 타입을 얻는다
    while isinstance(t, TVar) and t.ref is not None:
        t = t.ref
    return t

def occurs(v, t):                         # 출현 검사
    t = prune(t)
    if t is v: return True
    return isinstance(t, tuple) and (occurs(v, t[1]) or occurs(v, t[2]))

def unify(a, b):
    a, b = prune(a), prune(b)
    if isinstance(a, TVar):
        if a is not b:
            if occurs(a, b): raise TypeError("무한 타입")
            a.ref = b
    elif isinstance(b, TVar):
        unify(b, a)
    elif isinstance(a, tuple) and isinstance(b, tuple):   # ('->', 인자, 결과)
        unify(a[1], b[1]); unify(a[2], b[2])
    elif a != b:
        raise TypeError(f"{a} 와 {b} 는 맞지 않는다")

def infer(e, env):
    if isinstance(e, bool): return "bool"     # bool 검사가 int 보다 먼저(True 는 int 이기도 하다)
    if isinstance(e, int): return "int"
    tag = e[0]
    if tag == "var": return env[e[1]]
    if tag == "add":
        unify(infer(e[1], env), "int"); unify(infer(e[2], env), "int"); return "int"
    if tag == "lam":
        tv = TVar()
        return ("->", tv, infer(e[2], {**env, e[1]: tv}))
    if tag == "app":
        f, a, r = infer(e[1], env), infer(e[2], env), TVar()
        unify(f, ("->", a, r)); return r
    if tag == "if":
        unify(infer(e[1], env), "bool")
        t, f = infer(e[2], env), infer(e[3], env)
        unify(t, f); return t
```

여섯 개의 식을 넣은 결과:

```
λx. x + 1                    : (int -> int)
λx. x                        : (t1 -> t1)
λf. λx. f (f x)              : ((t5 -> t5) -> (t5 -> t5))
λb. if b then 1 else 2       : (bool -> int)
if true then 1 else false    : 타입 오류 — int 와 bool 는 맞지 않는다
λx. x x                      : 타입 오류 — 무한 타입
```

주석 하나 없이 `λf. λx. f (f x)` 가 "a 를 a 로 보내는 함수를 받아 a 를 a 로 보내는 함수를 돌려준다"는 가장 일반적인 타입을 얻었다. `λx. x x` 는 `x` 의 타입이 `t -> s` 이면서 `t` 여야 해서 출현 검사에 걸린다.

Java 의 지역 추론도 확인해 보자(OpenJDK 25).

```java
var xs = new ArrayList<String>();   // ArrayList<String> 로 추론
xs.add(1);
// error: incompatible types: int cannot be converted to String
```

`var` 는 동적 타입이 아니다. 컴파일러가 정한 타입이 고정된다.

## 현업에서는

- **추론 실패 메시지 읽기**: Rust·TypeScript 의 긴 타입 오류는 대개 단일화 실패다. "기대한 타입 A, 실제 타입 B" 쌍을 찾고, 어느 지점에서 A 라는 제약이 생겼는지 거슬러 올라가면 원인이 나온다.
- **경계에는 주석을**: 공개 함수 시그니처, 모듈 경계, 복잡한 제네릭 반환값에는 타입을 명시한다. 추론에 맡기면 구현을 고칠 때 공개 타입이 조용히 바뀐다.
- **TypeScript 의 넓어지는 추론**: `let status = "ok"` 는 `string` 으로, `const status = "ok"` 는 리터럴 타입 `"ok"` 로 추론된다. 유니언 타입 판별이 기대대로 안 될 때 흔한 원인이다.
- **설정 언어의 타입**: 쿠버네티스 CRD 는 OpenAPI 스키마로 필드 타입을 선언하고 API 서버가 검증한다. 타입 시스템의 아이디어가 프로그래밍 언어 밖에서도 "잘못된 설정이 클러스터에 들어가지 못하게" 막는 데 쓰인다.

## 확인 문제

1. 타입 시스템의 건전성을 이루는 두 정리는 무엇이며 각각 무엇을 말하는가?
2. `λx. x + 1` 의 타입을 추론하는 과정에서 생기는 제약은?
3. 단일화에서 출현 검사를 하지 않으면 어떤 일이 생기는가?
4. Java 의 `var` 로 선언한 변수에 나중에 다른 타입의 값을 대입할 수 있는가?
5. 주류 언어들이 전역 HM 추론 대신 지역 추론을 쓰는 이유 두 가지는?

### 풀이

1. 진행: 타입이 맞는 식은 값이거나 더 계산할 수 있다. 보존: 계산 한 단계 후에도 타입이 유지된다.
2. `x : t0` 로 두면 `+` 규칙에서 `t0 = int`, 결과는 `int`. 따라서 `int -> int`.
3. `t = t -> int` 같은 순환 대입이 생겨 무한 타입을 만들거나, 추론기가 무한 루프에 빠진다.
4. 추론된 타입과 호환되지 않는 값은 대입할 수 없다. `var` 는 초기값으로부터 컴파일 시점에 타입이 고정되는 정적 타입 변수이고, 이후에는 명시적으로 그 타입을 적은 변수와 똑같이 검사된다.
5. 서브타이핑·오버로딩과 전역 추론이 잘 맞지 않아 추론이 어렵거나 결정 불가능해지고, 명시된 시그니처가 문서 역할과 오류 위치 국한 역할을 하기 때문이다.

## 더 읽을거리 (References)

- Robin Milner, [A theory of type polymorphism in programming](https://doi.org/10.1016/0022-0000%2878%2990014-4), Journal of Computer and System Sciences 17(3), 1978
- Luis Damas, Robin Milner, "Principal type-schemes for functional programs", POPL 1982
- Benjamin C. Pierce, *Types and Programming Languages*, MIT Press, 2002 — 22장 타입 재구성
- TypeScript Handbook, [Type Inference](https://www.typescriptlang.org/docs/handbook/type-inference.html)
- [JEP 286 — Local-Variable Type Inference](https://openjdk.org/jeps/286)
