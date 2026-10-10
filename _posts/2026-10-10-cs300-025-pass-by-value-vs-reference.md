---
layout: post
title: "[CS300 #025] 값 전달과 참조 전달 — 함수는 인자를 어떻게 받는가"
date: 2026-10-10 18:25:00 +0900
categories: [cs]
tags: [cs300, programming, parameter-passing, reference, aliasing]
---

컴퓨터공학 300 주제 시리즈의 025번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

값 전달은 인자의 복사본을 넘기고, 참조 전달은 호출한 쪽 변수 자체를 넘긴다. Java·Python·JavaScript 는 "참조를 값으로 전달"하므로, 객체 내부 수정은 밖에서 보이지만 매개변수 재대입은 보이지 않는다.

## 왜 필요한가

"함수 안에서 리스트를 바꿨더니 밖에서도 바뀌었다"와 "함수 안에서 바꿨는데 밖에서는 그대로다"는 같은 언어에서 동시에 일어난다. 이 차이를 설명하지 못하면 버그를 고칠 때 운에 맡기게 된다.

면접 단골 질문인 "Java 는 참조 전달인가?"의 정확한 답도 여기서 나온다. 답은 "아니다, Java 는 언제나 값 전달이다"이고, 그 이유를 말할 수 있어야 한다.

## 핵심 개념

### 전달 방식의 정의

함수를 호출할 때 인자와 매개변수를 연결하는 방식을 **매개변수 전달 방식(parameter passing)** 이라 한다.

| 방식 | 매개변수가 받는 것 | 매개변수에 재대입하면 | 대표 |
|---|---|---|---|
| 값 전달 (call by value) | 인자 값의 복사본 | 호출자 변수는 그대로 | C, Java, Python(참조 값) |
| 참조 전달 (call by reference) | 호출자 변수의 별칭 | 호출자 변수도 바뀐다 | C++ `int&`, C# `ref`, Pascal `var` |
| 이름 전달 (call by name) | 평가 안 된 식 | 쓸 때마다 다시 평가 | Algol 60 |

판별법은 간단하다. **함수 안에서 매개변수에 새 값을 대입했을 때 호출한 쪽 변수가 바뀌는가?** 바뀌면 참조 전달, 아니면 값 전달이다. 고전적인 시험이 `swap(a, b)` 함수다. 값 전달만 있는 언어에서는 두 변수를 맞바꾸는 일반 `swap` 함수를 쓸 수 없다.

### "참조를 값으로 전달"

Java 의 객체 변수에는 객체 자체가 아니라 객체를 가리키는 참조가 들어 있다. 메서드를 호출하면 이 **참조 값이 복사**되어 매개변수에 들어간다. Java 언어 명세는 메서드 호출 시 "실제 인자 식의 값이 새로 만든 매개변수 변수를 초기화한다"고 정의한다(JLS §8.4.1, [Chapter 8. Classes](https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html)).

```
호출 전            호출 중 (append(x))
 x ──┐              x ──┐
     ▼                  ▼
  [StringBuilder "x"]  <── s   (참조 값의 복사본)

 s.append("!")  → 같은 객체를 수정 → x 에서도 "x!" 로 보인다
 s = new ...    → s 만 다른 객체로 옮겨 감 → x 는 그대로
```

Python 도 같다. 공식 튜토리얼은 인자가 "값에 의한 호출(값은 언제나 객체의 값이 아닌 객체 참조)"로 전달된다고 설명하고([More Control Flow Tools](https://docs.python.org/3/tutorial/controlflow.html#defining-functions)), FAQ 는 이를 "대입에 의한 전달"이라 부른다([Programming FAQ](https://docs.python.org/3/faq/programming.html#how-do-i-write-a-function-with-output-parameters-call-by-reference)). 이름이 무엇이든 동작은 하나다. 매개변수는 호출자와 같은 객체를 가리키는 새 이름표다.

그래서 결과는 객체의 **가변성**에 따라 갈린다.

- 가변 객체(리스트, 딕셔너리, StringBuilder)를 제자리 수정 → 호출자에게 보인다.
- 매개변수에 재대입 → 호출자에게 보이지 않는다.
- 불변 객체(정수, 문자열, 튜플) → 제자리 수정이 불가능하므로 사실상 값 전달처럼 보인다.

### C 의 포인터: 값 전달로 참조를 흉내 내기

C 는 값 전달만 있다. 호출자의 변수를 바꾸려면 변수의 **주소**를 값으로 넘기고(`&x`), 함수 안에서 역참조(`*a`)한다. 포인터 자체는 복사되지만, 복사본도 같은 주소를 가리키므로 원본을 바꿀 수 있다.

C++ 의 참조 매개변수 `int&` 는 진짜 참조 전달이다. 매개변수가 호출자 변수의 다른 이름이 된다.

### 별칭과 방어적 복사

참조를 공유하면 **별칭(aliasing)** 이 생긴다. 함수가 받은 리스트를 저장해 두었는데, 호출자가 나중에 그 리스트를 수정하면 함수 쪽 상태도 바뀐다. 이를 막는 방법은 두 가지다.

1. **방어적 복사**: 받을 때나 내보낼 때 복사본을 만든다.
2. **불변 타입 사용**: 튜플, `frozenset`, Java 의 `List.of(...)` 처럼 아예 못 바꾸게 한다.

복사도 깊이가 있다. **얕은 복사**는 바깥 컨테이너만 새로 만들고 안쪽 원소는 공유한다. **깊은 복사**는 안쪽까지 재귀적으로 복제한다. Python 은 `copy.copy` 와 `copy.deepcopy` 로 구분한다([copy](https://docs.python.org/3/library/copy.html)).

### Python 의 가변 기본 인자 함정

Python 함수의 기본 인자는 **함수를 정의할 때 한 번만** 평가된다. `def f(x, acc=[])` 의 빈 리스트는 모든 호출이 공유한다. 공식 튜토리얼이 경고하는 대표 함정이다. 기본값은 `None` 으로 두고 함수 안에서 새로 만든다.

## 직접 해 보기

Python (3.12.3 에서 실행):

```python
def mutate(xs):
    xs.append(99)      # 같은 객체를 수정
def rebind(xs):
    xs = [0]           # 지역 이름표만 옮김

a = [1, 2]
mutate(a); print(a)    # [1, 2, 99]
rebind(a); print(a)    # [1, 2, 99]  그대로

def add_item(item, bucket=[]):
    bucket.append(item)
    return bucket
print(add_item("x"), add_item("y"))    # ['x', 'y'] ['x', 'y']  공유된다

def add_item2(item, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
print(add_item2("x"), add_item2("y"))  # ['x'] ['y']

import copy
orig = {"tags": ["a"], "n": 1}
sh, dp = copy.copy(orig), copy.deepcopy(orig)
orig["tags"].append("b")
print(sh["tags"], dp["tags"])          # ['a', 'b'] ['a']
```

Java (OpenJDK 25 에서 실행):

```java
public class Swap {
    static void swap(StringBuilder a, StringBuilder b) { StringBuilder t = a; a = b; b = t; }
    static void append(StringBuilder s) { s.append("!"); }
    static void inc(int n) { n++; }
    public static void main(String[] args) {
        StringBuilder x = new StringBuilder("x"), y = new StringBuilder("y");
        swap(x, y);  System.out.println(x + " " + y);  // x y   (바뀌지 않음)
        append(x);   System.out.println(x);            // x!    (객체 수정은 보임)
        int k = 1; inc(k); System.out.println(k);      // 1
    }
}
```

C 와 C++ (gcc/g++ 에서 실행):

```c
void swap_val(int a, int b) { int t = a; a = b; b = t; }      /* 효과 없음 */
void swap_ptr(int *a, int *b) { int t = *a; *a = *b; *b = t; } /* 주소를 값으로 */
/* C++: void swap_ref(int &a, int &b) { int t = a; a = b; b = t; } 진짜 참조 전달 */
```

`swap_val(x, y)` 후에는 `1 2`, `swap_ptr(&x, &y)` 후에는 `2 1` 이 출력된다. C++ `swap_ref(x, y)` 도 `2 1` 이다.

## 현업에서는

- **요청 간 상태 누수**: 웹 핸들러에서 모듈 수준 기본 딕셔너리를 받아 수정하면 다음 요청에 값이 남는다. 가변 기본 인자 함정의 실무 판이다.
- **캐시 오염**: 캐시에서 꺼낸 객체를 호출자가 수정하면 캐시 안의 원본도 바뀐다. 캐시는 불변 객체나 복사본을 돌려줘야 한다.
- **설정 병합**: 쿠버네티스 매니페스트나 헬름 values 를 코드로 합칠 때, 기본값 딕셔너리를 얕은 복사한 뒤 중첩 키를 수정하면 기본값까지 오염된다. 이런 병합 코드는 깊은 복사부터 한다.
- **성능 판단**: C++·Rust 에서 큰 구조체를 값으로 넘기면 복사 비용이 든다. 그래서 읽기 전용이면 `const T&`(C++)나 `&T`(Rust)로 빌려 넘긴다. Rust 의 빌림 규칙은 #040 에서 다룬다.

## 확인 문제

1. 매개변수 전달 방식이 값 전달인지 참조 전달인지 판별하는 시험은?
2. Java 에서 `void reset(List<String> xs) { xs = new ArrayList<>(); }` 를 호출하면 호출자의 리스트는 어떻게 되는가? `xs.clear()` 였다면?
3. Python 의 `def f(x, cache={})` 에서 `cache` 는 언제 만들어지는가?
4. 얕은 복사와 깊은 복사의 차이를 중첩 리스트 예로 설명하라.
5. C 에서 함수가 두 개의 결과를 돌려주는 관용적인 방법은?

### 풀이

1. 함수 안에서 매개변수에 새 값을 대입한 뒤 호출자 변수가 바뀌는지 본다. `swap` 함수가 전형적인 시험이다.
2. 재대입은 지역 매개변수만 바꾸므로 호출자 리스트는 그대로다. `xs.clear()` 는 같은 객체를 수정하므로 호출자 리스트도 비워진다.
3. `def` 문이 실행되는 시점, 즉 함수 정의 시 한 번 만들어져 모든 호출이 공유한다.
4. `[[1], [2]]` 를 얕은 복사하면 바깥 리스트만 새것이고 `[1]`, `[2]` 는 원본과 공유된다. 깊은 복사는 안쪽 리스트까지 새로 만든다.
5. 결과를 담을 변수의 포인터를 출력 매개변수로 받는다(`int divmod(int a, int b, int *rem)`). 또는 구조체를 반환한다.

## 더 읽을거리 (References)

- Python Tutorial, [Defining Functions](https://docs.python.org/3/tutorial/controlflow.html#defining-functions) — 객체 참조의 값 전달, 기본 인자 평가 시점
- Python FAQ, [How do I write a function with output parameters (call by reference)?](https://docs.python.org/3/faq/programming.html#how-do-i-write-a-function-with-output-parameters-call-by-reference)
- The Java Language Specification, Java SE 21, [Chapter 8 — 8.4.1 Formal Parameters](https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html)
- Python Docs, [copy — Shallow and deep copy operations](https://docs.python.org/3/library/copy.html)
