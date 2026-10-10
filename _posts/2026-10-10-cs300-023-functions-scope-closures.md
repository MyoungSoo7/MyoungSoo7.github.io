---
layout: post
title: "[CS300 #023] 함수·스코프·클로저 — 이름은 어디서 찾아지는가"
date: 2026-10-10 18:23:00 +0900
categories: [cs]
tags: [cs300, programming, function, scope, closure]
---

컴퓨터공학 300 주제 시리즈의 023번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

함수는 이름 붙은 계산 단위이고, 스코프는 이름이 어느 범위에서 보이는지 정하는 규칙이며, 클로저는 함수가 자신이 정의된 환경의 변수를 붙잡아 들고 다니는 것이다.

## 왜 필요한가

코드가 몇백 줄을 넘으면 같은 이름 `count`, `result`, `i` 가 여러 곳에 나온다. 어떤 `count` 를 읽고 쓰는지 정확히 모르면 엉뚱한 변수를 덮어쓴다. 스코프 규칙은 이 혼란을 막는 장치다.

클로저는 콜백, 데코레이터, 이벤트 핸들러, 부분 적용 같은 실무 패턴의 바탕이다. 그리고 "루프 안에서 만든 람다가 전부 마지막 값을 돌려준다" 같은 유명한 함정도 클로저에서 나온다.

## 핵심 개념

### 함수가 하는 일

함수는 입력(매개변수)을 받아 출력(반환값)을 내는 이름 붙은 코드 블록이다. 세 가지 이득이 있다.

- **재사용**: 같은 계산을 여러 번 쓴다.
- **추상화**: 호출하는 쪽은 이름과 계약만 알면 된다.
- **격리**: 함수 안의 지역 변수는 밖과 섞이지 않는다.

용어를 구분하자. 정의할 때 적는 이름은 **매개변수(parameter)**, 호출할 때 넘기는 값은 **인자(argument)** 다.

### 정적 스코프와 동적 스코프

이름을 찾을 때 "어디서 정의되었나"를 기준으로 하면 **정적(렉시컬) 스코프**, "누가 호출했나"를 기준으로 하면 **동적 스코프**다. 오늘날 주류 언어(Python, JavaScript, Java, C, Rust)는 정적 스코프를 쓴다. 코드 텍스트만 보고 이름이 무엇을 가리키는지 알 수 있기 때문이다. 동적 스코프는 초기 Lisp 계열, Bash 의 `local` 등에 남아 있다.

Python 은 2.1~2.2 시절 PEP 227 로 중첩 함수의 정적 스코프를 도입했다([PEP 227](https://peps.python.org/pep-0227/)).

### Python 의 LEGB 규칙

Python 에서 이름을 읽을 때는 네 단계로 찾는다.

```
L  Local       현재 함수 안
E  Enclosing   바깥 함수들 (안쪽부터)
G  Global      모듈 최상위
B  Built-in    len, print 같은 내장
```

공식 실행 모델 문서는 이를 "블록"과 "바인딩"으로 정의한다. 핵심 규칙 하나가 중요하다. **블록 안 어디에서든 이름에 대입이 있으면, 그 이름은 블록 전체에서 지역 변수다**([Execution model](https://docs.python.org/3/reference/executionmodel.html)). 그래서 함수 안에서 전역 `n` 을 읽은 뒤 `n += 1` 을 하려 하면, 읽는 시점에 이미 `n` 이 지역으로 판정되어 `UnboundLocalError` 가 난다.

바깥 변수를 수정하려면 의도를 선언해야 한다.

| 선언 | 대상 |
|---|---|
| `global n` | 모듈 전역 `n` |
| `nonlocal n` | 가장 가까운 바깥 함수의 `n` ([PEP 3104](https://peps.python.org/pep-3104/)) |

### 일급 함수와 클로저

Python, JavaScript 에서 함수는 **일급 값**이다. 변수에 넣고, 인자로 넘기고, 반환할 수 있다. 함수를 반환할 수 있으면 질문이 생긴다. 반환된 안쪽 함수가 바깥 함수의 지역 변수를 쓰는데, 바깥 함수는 이미 끝났다. 그 변수는 어디에 있는가?

답이 **클로저(closure)** 다. 안쪽 함수는 자신이 참조하는 바깥 변수(자유 변수)를 함께 붙잡아 둔다. MDN 은 클로저를 "함수와 그 함수가 선언된 렉시컬 환경의 조합"으로 설명한다([Closures](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Closures)).

```
make_counter() 호출 1회
 ┌─ 환경 ─────────┐
 │ count = 0      │<─── inc 함수가 참조를 쥐고 있다
 └────────────────┘
make_counter() 가 끝나도 inc 가 살아 있는 한 환경도 산다
```

CPython 은 이를 **셀(cell)** 객체로 구현한다. 바깥 함수와 안쪽 함수가 같은 셀을 공유하고, 함수 객체의 `__closure__` 속성에 셀들이 들어 있다.

### 늦은 바인딩 함정

클로저는 변수의 **값이 아니라 변수 자체**를 붙잡는다. 루프에서 람다를 여러 개 만들면 모두 같은 루프 변수를 가리키고, 호출 시점의 값(마지막 값)을 읽는다. 해결책은 정의 시점의 값을 고정하는 것이다. Python 에서는 기본 인자 `lambda i=i: i` 나 `functools.partial` 을 쓴다. JavaScript 는 `let` 이 루프 바퀴마다 새 바인딩을 만들어 이 문제를 언어 차원에서 피한다.

## 직접 해 보기

```python
x = "global"
def outer():
    x = "enclosing"
    def inner():
        print(x)        # E 단계에서 찾는다
    inner()
outer()                 # enclosing
print(x)                # global

def make_counter():
    count = 0
    def inc():
        nonlocal count
        count += 1
        return count
    return inc

c1 = make_counter(); c2 = make_counter()
print(c1(), c1(), c1(), c2())          # 1 2 3 1  각자 다른 환경
print(c1.__code__.co_freevars,          # ('count',)
      c1.__closure__[0].cell_contents)  # 3

fs = [lambda: i for i in range(3)]
print([f() for f in fs])                # [2, 2, 2]  늦은 바인딩
fs = [lambda i=i: i for i in range(3)]
print([f() for f in fs])                # [0, 1, 2]

n = 0
def bump():
    n += 1              # 대입이 있으므로 n 은 지역 변수
bump()                  # UnboundLocalError
```

Python 3.12 에서 마지막 줄은 `cannot access local variable 'n' where it is not associated with a value` 메시지를 낸다.

JavaScript 로 같은 함정을 보자(Node.js 22 에서 확인).

```javascript
var fs = []; for (var i = 0; i < 3; i++) fs.push(() => i);
console.log(fs.map(f => f()));   // [ 3, 3, 3 ]  var 는 함수 스코프 하나
let gs = []; for (let j = 0; j < 3; j++) gs.push(() => j);
console.log(gs.map(f => f()));   // [ 0, 1, 2 ]  let 은 바퀴마다 새 바인딩
```

## 현업에서는

- **데코레이터**: 직접 만드는 `@retry(times=3)` 같은 데코레이터는 대개 클로저로 구현된다. 설정값(`times`)을 바깥 함수가 받고, 안쪽 래퍼가 그것을 붙잡는다.
- **콜백과 핸들러**: 웹 프론트엔드에서 이벤트 핸들러는 컴포넌트의 상태를 클로저로 참조한다. 오래된 값을 붙잡는 "stale closure" 문제가 대표적인 버그다.
- **전역 상태 줄이기**: 설정·커넥션 풀을 전역 변수에 두면 테스트에서 격리가 안 된다. 팩토리 함수가 의존성을 받아 클로저로 감싸 반환하면 테스트마다 다른 의존성을 넣을 수 있다.
- **메모리 누수**: 클로저가 큰 객체를 붙잡고 있고, 그 클로저가 전역 캐시나 이벤트 리스너 목록에 남아 있으면 객체가 해제되지 않는다. 장시간 도는 서버에서 메모리가 서서히 오르는 원인 중 하나다.

## 확인 문제

1. 정적 스코프와 동적 스코프의 차이를 한 문장으로 말하라.
2. 다음 코드의 결과는? `def f(): print(y); y = 1` 을 호출할 때(전역에 `y = 0` 이 있다).
3. `nonlocal` 과 `global` 의 차이는?
4. `[lambda: i for i in range(3)]` 이 모두 2 를 돌려주는 이유를 "클로저가 무엇을 붙잡는가"로 설명하라.
5. `make_counter()` 를 두 번 호출해 얻은 두 함수가 카운트를 공유하지 않는 이유는?

### 풀이

1. 정적 스코프는 이름을 정의된 위치(코드 텍스트)로, 동적 스코프는 호출된 경로(실행 시 호출 스택)로 찾는다.
2. `UnboundLocalError`. 함수 안에 `y` 대입이 있으므로 `y` 는 함수 전체에서 지역 변수이고, `print` 시점에는 아직 값이 없다.
3. `global` 은 모듈 최상위 이름을, `nonlocal` 은 전역이 아닌 가장 가까운 바깥 함수 스코프의 이름을 가리킨다.
4. 클로저는 변수 `i` 자체(셀)를 붙잡는다. 호출 시점에 그 셀의 값은 루프가 끝난 뒤의 2 다.
5. `make_counter` 를 호출할 때마다 새 지역 환경(새 `count` 셀)이 만들어지기 때문이다.

## 더 읽을거리 (References)

- Python Language Reference, [Execution model — Naming and binding](https://docs.python.org/3/reference/executionmodel.html)
- [PEP 227 — Statically Nested Scopes](https://peps.python.org/pep-0227/), [PEP 3104 — Access to Names in Outer Scopes](https://peps.python.org/pep-3104/)
- MDN, [Closures](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Closures)
- Harold Abelson, Gerald Jay Sussman, *Structure and Interpretation of Computer Programs*, 2nd ed., MIT Press, 1996 — 3.2절 환경 모델
