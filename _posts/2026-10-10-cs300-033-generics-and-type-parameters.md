---
layout: post
title: "[CS300 #033] 제네릭과 타입 매개변수 — 타입을 인자로 받는 코드"
date: 2026-10-10 18:33:00 +0900
categories: [cs]
tags: [cs300, programming, generics, type-parameter, type-erasure]
---

컴퓨터공학 300 주제 시리즈의 033번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

제네릭은 타입을 매개변수로 받아 하나의 코드를 여러 타입에 안전하게 쓰게 하는 기능이며, 구현 방식은 크게 타입 소거(Java)와 단형화(Rust, C++)로 갈린다.

## 왜 필요한가

정수 스택, 문자열 스택, 주문 객체 스택을 따로 만들고 싶은 사람은 없다. 그렇다고 Java 1.4 시절처럼 모든 것을 `Object` 로 담으면 꺼낼 때마다 형변환을 해야 하고, 실수로 다른 타입을 넣어도 컴파일러가 막지 못한다. 오류는 한참 뒤 꺼내는 쪽에서 `ClassCastException` 으로 터진다.

제네릭은 이 두 요구, **재사용**과 **타입 안전성**을 동시에 만족시킨다. #030 에서 본 다형성 분류의 "매개변수 다형성"이 바로 이것이다.

## 핵심 개념

### 타입 매개변수

함수가 값을 매개변수로 받듯, 제네릭 코드는 **타입**을 매개변수로 받는다.

```java
class Box<T> {            // T: 타입 매개변수
    private T value;
    T get() { return value; }
    void set(T v) { value = v; }
}
Box<String> b = new Box<>();   // T = String 으로 인스턴스화
```

`Box<String>` 에 `Integer` 를 넣으려 하면 컴파일 오류다. 꺼낼 때 형변환도 필요 없다. 오류 발견 시점이 실행 시에서 컴파일 시로 당겨진다. Java 튜토리얼은 제네릭의 이점으로 컴파일 시점의 강한 타입 검사, 형변환 제거, 일반화된 알고리즘 구현을 꼽는다([Lesson: Generics](https://docs.oracle.com/javase/tutorial/java/generics/index.html)).

### 제약(바운드)

아무 타입이나 받으면 그 타입에 대해 할 수 있는 일이 거의 없다. 최댓값을 구하려면 "비교할 수 있는 타입"이어야 한다. 이것을 **제약** 또는 **바운드**로 표현한다.

| 언어 | 문법 | 의미 |
|---|---|---|
| Java | `<T extends Comparable<T>>` | T 는 자기 자신과 비교 가능 |
| Rust | `fn max<T: PartialOrd>(...)` | T 는 `PartialOrd` 트레이트 구현 |
| Go | `[T constraints.Ordered]` 또는 `[T cmp.Ordered]` | 순서 비교 가능한 타입 집합 |
| TypeScript | `<T extends { length: number }>` | `length` 속성을 가진 타입 |
| Python 3.12+ | `def f[T: Comparable](...)` | 정적 검사기용 상한 |

Go 는 2022년 Go 1.18 에서 타입 매개변수를 도입했다. 제약을 인터페이스로 표현하되, 메서드 집합뿐 아니라 **타입 집합**도 담을 수 있게 인터페이스 개념을 넓혔다([An Introduction To Generics](https://go.dev/blog/intro-generics)).

### 구현 전략 1: 타입 소거 (Java)

Java 는 제네릭을 하위 호환을 위해 **타입 소거(type erasure)** 로 구현했다. 컴파일러가 타입 검사를 마치면 타입 매개변수를 지우고 바운드(없으면 `Object`)로 바꾼 뒤, 필요한 곳에 형변환(`checkcast`)을 끼워 넣는다. JLS 4.6 이 소거를 정의한다([JLS Chapter 4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)).

결과:
- 런타임에는 `List<String>` 과 `List<Integer>` 가 **같은 클래스**다.
- `new T()`, `T.class`, `instanceof List<String>` 을 쓸 수 없다. 런타임에 T 정보가 없기 때문이다.
- 원시 타입(raw type)을 섞으면 컴파일러 경고만 나고, 오염된 값은 꺼낼 때 터진다(힙 오염).
- 기본형은 타입 인자가 될 수 없어 `List<int>` 대신 `List<Integer>` 로 박싱한다.

### 구현 전략 2: 단형화 (Rust, C++)

Rust 와 C++ 템플릿은 사용된 타입 인자마다 **별도의 코드를 생성**한다. `max::<i32>` 와 `max::<f64>` 가 각각 기계어로 만들어진다. Rust 공식 책은 이를 단형화(monomorphization)라 부르며, 제네릭을 써도 구체 타입으로 쓴 코드와 런타임 비용이 같다고 설명한다([Generic Data Types](https://doc.rust-lang.org/book/ch10-01-syntax.html)).

| | 타입 소거 | 단형화 |
|---|---|---|
| 런타임 타입 정보 | 없음 | 타입마다 별도 코드 |
| 실행 속도 | 형변환·박싱 비용 | 구체 타입과 동일 |
| 바이너리 크기 | 작다 | 타입 수만큼 커질 수 있다 |
| 컴파일 시간 | 짧다 | 길어질 수 있다 |

Go 는 그 중간이다. 같은 메모리 모양(GC shape)을 가진 타입끼리는 코드를 공유하고 숨은 사전(dictionary)을 넘기는 방식을 쓴다([Go 1.18 구현 설계 문서](https://github.com/golang/proposal/blob/master/design/generics-implementation-dictionaries-go1.18.md)).

### 변성

`String` 이 `Object` 의 하위 타입이면 `List<String>` 은 `List<Object>` 의 하위 타입인가? 그렇게 허용하면 `List<Object>` 로 보고 `Integer` 를 넣을 수 있어 타입 안전성이 깨진다. 그래서 Java 의 제네릭은 기본적으로 **무공변(invariant)** 이다. 읽기만 하는 경우는 `List<? extends Number>`(공변), 쓰기만 하는 경우는 `List<? super Integer>`(반공변)로 표현한다. 흔히 "생산자는 extends, 소비자는 super(PECS)"라고 외운다.

### Python 의 제네릭

Python 은 런타임에 타입 매개변수를 강제하지 않는다(#026). 제네릭 문법은 정적 검사기를 위한 것이다. Python 3.12 의 PEP 695 는 `TypeVar` 를 따로 선언하던 방식 대신 `def first[T](xs: list[T]) -> T` 같은 간결한 문법을 도입했다([PEP 695](https://peps.python.org/pep-0695/), [typing](https://docs.python.org/3/library/typing.html)).

## 직접 해 보기

Python 3.12.3 에서 실행(새 문법은 3.12 이상 필요):

```python
from typing import Sequence, Protocol

def first[T](xs: Sequence[T]) -> T:
    return xs[0]
print(first([1, 2, 3]), first("abc"))       # 1 a

class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []
    def push(self, x: T) -> None:
        self._items.append(x)
    def pop(self) -> T:
        return self._items.pop()

s = Stack[int](); s.push(1); s.push(2); print(s.pop())   # 2

class SupportsLessThan(Protocol):
    def __lt__(self, other, /) -> bool: ...

def biggest[T: SupportsLessThan](xs: list[T]) -> T:
    best = xs[0]
    for x in xs[1:]:
        if best < x:
            best = x
    return best
print(biggest([3, 7, 2]), biggest(["b", "a"]))  # 7 b
print(first.__type_params__)                    # (T,)
```

Java 의 타입 소거를 눈으로 확인한다(OpenJDK 25).

```java
import java.util.*;
public class G {
    static <T extends Comparable<T>> T max(List<T> xs) {
        T best = xs.get(0);
        for (T x : xs) if (x.compareTo(best) > 0) best = x;
        return best;
    }
    public static void main(String[] a) {
        List<String> s = new ArrayList<>(); List<Integer> i = new ArrayList<>();
        System.out.println(s.getClass() == i.getClass());   // true  런타임엔 같은 클래스
        System.out.println(max(List.of(3, 9, 4)) + " " + max(List.of("kiwi", "apple"))); // 9 kiwi
        List raw = s; raw.add(42);                          // 컴파일 경고만
        try { String x = s.get(0); }
        catch (ClassCastException e) { System.out.println("ClassCastException"); }
    }
}
```

`javac` 는 "uses unchecked or unsafe operations" 경고만 내고 컴파일한다. `javap -c G` 로 바이트코드를 보면 `List.get` 은 `Object` 를 돌려주고, 그 뒤에 컴파일러가 넣은 `checkcast java/lang/String` 이 보인다. 오염된 값 42 는 바로 이 `checkcast` 에서 걸린다.

## 현업에서는

- **컬렉션과 응답 래퍼**: `ApiResponse<T>`, `Page<T>`, `Result<T, E>` 처럼 공통 모양에 내용 타입만 바꾸는 클래스는 제네릭의 대표 용도다.
- **Jackson 과 타입 토큰**: 타입 소거 때문에 JSON 을 `List<User>` 로 역직렬화하려면 런타임에 원소 타입을 따로 알려 줘야 한다. `TypeReference<List<User>>` 같은 "타입 토큰" 관용구가 그래서 존재한다.
- **Go 의 제네릭 도입 이후**: `sort.Slice` 같은 `interface{}` 기반 API 대신 `slices.Sort` 같은 제네릭 함수가 표준 라이브러리에 들어왔다. 쿠버네티스 생태계 Go 코드에서도 제네릭 헬퍼가 늘고 있다.
- **과한 추상화 경계**: 타입 매개변수가 서너 개 겹치고 바운드가 중첩되면 읽기 어렵다. 실제로 두 가지 이상의 타입에 쓰일 때 제네릭으로 올린다.

## 확인 문제

1. 제네릭이 `Object` 로 모든 것을 담는 방식보다 나은 점 두 가지는?
2. Java 에서 `new T()` 를 쓸 수 없는 이유는?
3. 단형화의 장점과 단점을 하나씩 들라.
4. `List<String>` 이 `List<Object>` 의 하위 타입이 아닌 이유는?
5. Python 3.12 의 `def f[T](x: T) -> T` 에서 런타임에 `f(1)` 과 `f("a")` 는 어떻게 다르게 처리되는가?

### 풀이

1. 컴파일 시점 타입 검사로 잘못된 타입 삽입을 막고, 꺼낼 때 형변환이 필요 없다.
2. 타입 소거로 런타임에 `T` 가 무엇인지 알 수 없기 때문이다.
3. 장점은 구체 타입과 같은 실행 성능, 단점은 바이너리 크기와 컴파일 시간 증가.
4. 허용하면 `List<Object>` 로 참조해 `Integer` 를 넣을 수 있어 `List<String>` 의 타입 안전성이 깨진다. 그래서 제네릭은 기본적으로 무공변이다.
5. 다르지 않다. 타입 매개변수는 정적 검사기를 위한 정보이며 런타임에 강제되지 않는다.

## 더 읽을거리 (References)

- The Java Tutorials, [Lesson: Generics](https://docs.oracle.com/javase/tutorial/java/generics/index.html)
- The Java Language Specification, Java SE 21, [Chapter 4 — 4.6 Type Erasure](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)
- The Rust Programming Language, [Generic Data Types](https://doc.rust-lang.org/book/ch10-01-syntax.html)
- The Go Blog, [An Introduction To Generics](https://go.dev/blog/intro-generics)
- [PEP 695 — Type Parameter Syntax](https://peps.python.org/pep-0695/)
