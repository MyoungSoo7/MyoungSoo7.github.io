---
layout: post
title: "[CS300 #030] 객체지향 2 — 상속·다형성·합성"
date: 2026-10-10 18:30:00 +0900
categories: [cs]
tags: [cs300, programming, oop, polymorphism, composition]
---

컴퓨터공학 300 주제 시리즈의 030번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

다형성은 같은 메시지에 객체마다 다른 동작으로 응답하게 하는 능력이고, 상속과 합성은 그 다형성과 코드 재사용을 얻는 두 가지 방법이다. 상속은 강하게 묶고, 합성은 느슨하게 묶는다.

## 왜 필요한가

도형 목록의 넓이를 모두 더하는 코드를 쓴다고 하자. 다형성이 없으면 `if type == "rect" ... elif type == "circle" ...` 분기가 생기고, 새 도형이 추가될 때마다 이 분기를 찾아 고쳐야 한다. 다형성이 있으면 `shape.area()` 한 줄로 끝나고, 새 도형은 자기 `area` 만 구현하면 된다.

그런데 다형성을 얻으려고 상속을 남발하면 깊은 클래스 계층이 생기고, 부모 클래스를 조금만 바꿔도 자식들이 줄줄이 깨진다. 언제 상속을 쓰고 언제 합성을 쓸지가 객체지향 설계의 핵심 판단이다.

## 핵심 개념

### 다형성의 세 종류

"다형성(polymorphism)"은 여러 형태를 가진다는 뜻이다. 프로그래밍 언어론에서는 보통 셋으로 나눈다.

| 종류 | 의미 | 예 |
|---|---|---|
| 서브타입 다형성 | 상위 타입 자리에 하위 타입 객체가 들어갈 수 있다 | `Shape s = new Circle()` |
| 매개변수 다형성 | 타입을 매개변수로 받아 여러 타입에 같은 코드 | 제네릭 `List<T>` (#033) |
| 임시(ad hoc) 다형성 | 타입마다 다른 구현을 같은 이름으로 | 메서드 오버로딩, 연산자 오버로딩 |

객체지향에서 "다형성"이라 하면 대개 서브타입 다형성을 말한다. 그 핵심 장치가 **동적 디스패치**다. `shape.area()` 를 호출할 때 어떤 `area` 를 실행할지 변수의 선언 타입이 아니라 **실행 시점 객체의 실제 타입**으로 정한다. Java·C++ 은 클래스마다 가상 메서드 테이블(vtable)을 두고 그 표를 따라가는 방식이 흔하다.

### 상속

상속은 기존 클래스의 필드와 메서드를 물려받아 새 클래스를 만드는 것이다. 두 가지가 동시에 일어난다.

1. **타입 상속(서브타이핑)**: 자식은 부모 타입으로 쓰일 수 있다.
2. **구현 상속**: 자식은 부모의 코드를 재사용한다.

문제는 2번에서 생긴다. 자식이 부모의 내부 구현에 기대게 되면, 부모의 내부 변경이 자식을 깨뜨린다. 이를 **깨지기 쉬운 기반 클래스 문제**라 한다. 상속은 캡슐화를 부모와 자식 사이에서 약하게 만든다.

### 리스코프 치환 원칙

상속이 옳은지 판단하는 기준이 **리스코프 치환 원칙(LSP)** 이다. 리스코프와 윙은 1994년 논문에서 "하위 타입 객체는 상위 타입 객체를 기대하는 어떤 프로그램에서도 그 프로그램의 바람직한 성질을 깨지 않고 대신 쓰일 수 있어야 한다"는 행동적 서브타이핑을 정식화했다.

고전적인 반례가 정사각형-직사각형이다. 수학에서는 정사각형이 직사각형이지만, "너비와 높이를 따로 바꿀 수 있는 직사각형" 클래스를 정사각형이 상속하면 계약이 깨진다. 아래 직접 해 보기에서 확인한다. **"is-a" 관계가 말로 성립해도 행동 계약이 성립하지 않으면 상속하면 안 된다.**

### 다중 상속과 MRO

여러 부모를 상속하면 같은 이름의 메서드가 여러 경로로 들어오는 **다이아몬드 문제**가 생긴다.

```
      A
     / \
    B   C
     \ /
      D      D().hello() 는 B 의 것? C 의 것? A 는 몇 번?
```

언어마다 대응이 다르다.

- **Java**: 클래스의 다중 상속을 금지한다. 인터페이스는 여러 개 구현할 수 있고, 디폴트 메서드 충돌은 컴파일러가 명시적 재정의를 요구한다. 공식 튜토리얼은 이를 "상태의 다중 상속"은 없고 "타입의 다중 상속"은 있다고 정리한다([Multiple Inheritance of State, Implementation, and Type](https://docs.oracle.com/javase/tutorial/java/IandI/multipleinheritance.html)).
- **Python**: 다중 상속을 허용하고, C3 선형화 알고리즘으로 **메서드 결정 순서(MRO)** 를 하나의 줄로 정한다. `super()` 는 "부모"가 아니라 MRO 상의 다음 클래스를 부른다([The Python 2.3 Method Resolution Order](https://docs.python.org/3/howto/mro.html)).
- **Rust, Go**: 클래스 상속 자체가 없다. Rust 공식 책은 매크로 없이 부모 구조체의 필드와 메서드 구현을 상속하는 구조체를 정의하는 방법은 없다고 밝히고, 트레이트로 다형성을 얻으라고 안내한다([Characteristics of Object-Oriented Languages](https://doc.rust-lang.org/book/ch18-01-what-is-oo.html)).

### 덕 타이핑

동적 언어에서는 상속 관계 없이도 다형성이 된다. 객체가 `speak()` 메서드를 갖고 있으면 `x.speak()` 를 부를 수 있다. 타입 계층이 아니라 **가진 메서드**로 판단하는 것이 덕 타이핑이다. Python 은 `typing.Protocol` 로 이것을 정적 검사기에도 알릴 수 있다(구조적 서브타이핑, [PEP 544](https://peps.python.org/pep-0544/)).

### 합성

합성(composition)은 다른 객체를 필드로 **가지고** 일을 위임하는 것이다. "is-a" 대신 "has-a" 관계다.

```
상속:  ElectricCar ──is-a──> Car ──is-a──> Vehicle   (계층이 굳는다)
합성:  Car ──has-a──> PowerSource  (Engine | ElectricMotor 를 끼운다)
```

GoF 의 『디자인 패턴』은 서론에서 "클래스 상속보다 객체 합성을 선호하라"는 원칙을 내세운다. 합성의 장점은 이렇다.

- 내부 객체의 공개 인터페이스에만 의존하므로 캡슐화가 유지된다.
- 실행 중에 부품을 바꿀 수 있다(전략 패턴).
- 계층 폭발이 없다. "전기 + 자율주행 + 오픈카"를 클래스 조합으로 만들 필요가 없다.

상속이 맞는 경우도 있다. 진짜 행동적 하위 타입이고, 부모가 상속을 염두에 두고 설계되었으며(확장 지점이 문서화됨), 계층이 얕을 때다.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
class Shape:
    def area(self): raise NotImplementedError
class Rect(Shape):
    def __init__(self, w, h): self.w, self.h = w, h
    def area(self): return self.w * self.h
class Circle(Shape):
    def __init__(self, r): self.r = r
    def area(self): return 3.14159 * self.r ** 2
print([round(s.area(), 2) for s in (Rect(2, 3), Circle(1))])   # [6, 3.14]

# 다이아몬드와 MRO
class A:
    def hello(self): return "A"
class B(A):
    def hello(self): return "B>" + super().hello()
class C(A):
    def hello(self): return "C>" + super().hello()
class D(B, C):
    def hello(self): return "D>" + super().hello()
print(D().hello())                          # D>B>C>A   A 는 한 번만
print([k.__name__ for k in D.__mro__])      # ['D', 'B', 'C', 'A', 'object']

# 합성: 부품을 끼운다
class Engine:
    def start(self): return "엔진 시동"
class ElectricMotor:
    def start(self): return "모터 기동"
class Car:
    def __init__(self, power): self.power = power
    def drive(self): return self.power.start() + " → 출발"
print(Car(Engine()).drive(), "|", Car(ElectricMotor()).drive())
# 엔진 시동 → 출발 | 모터 기동 → 출발

# LSP 위반
class Rectangle:
    def __init__(self, w, h): self.w, self.h = w, h
    def set_width(self, w): self.w = w
    def set_height(self, h): self.h = h
    def area(self): return self.w * self.h
class Square(Rectangle):
    def __init__(self, s): super().__init__(s, s)
    def set_width(self, w): self.w = self.h = w
    def set_height(self, h): self.w = self.h = h

def stretch(r: Rectangle):
    r.set_width(5); r.set_height(4)
    return r.area()                          # 직사각형 계약상 20 이어야 한다
print(stretch(Rectangle(1, 1)), stretch(Square(1)))   # 20 16
```

`B` 의 `super()` 가 `A` 가 아니라 `C` 를 불렀다는 점에 주목하자. `super()` 는 MRO 의 다음 칸이다. 마지막 예에서 `stretch` 는 `Rectangle` 계약을 믿었는데 `Square` 가 끼어들자 결과가 달라졌다. 타입 검사는 통과하지만 행동이 깨진 것이다.

## 현업에서는

- **프레임워크 확장점**: 웹 프레임워크의 기반 클래스 상속(예: 뷰 클래스)은 프레임워크가 처음부터 상속용으로 설계한 경우다. 문서화된 메서드만 재정의하고 내부 메서드에 기대지 않는다.
- **전략 객체 주입**: 재시도 정책, 직렬화 방식, 가격 계산 규칙을 합성으로 끼우면 설정만 바꿔 동작을 교체할 수 있다. 의존성 주입 컨테이너가 하는 일이 이것이다.
- **깊은 계층 정리**: 레거시 코드에서 `BaseService → AbstractUserService → UserServiceImpl → ...` 같은 깊은 계층은 리팩터링 대상 1순위다. 공통 코드는 헬퍼 객체로 빼 합성한다.
- **쿠버네티스 매니페스트의 합성**: Kustomize 는 기반 매니페스트에 패치를 겹쳐 쓰는 방식, 헬름은 템플릿에 values 를 끼우는 방식이다. 둘 다 거대한 상속 계층 대신 부품을 조합한다는 점에서 합성의 사고방식이다.

## 확인 문제

1. 서브타입 다형성에서 실제로 실행될 메서드는 무엇을 기준으로 정해지는가?
2. 깨지기 쉬운 기반 클래스 문제란?
3. 정사각형이 직사각형을 상속하는 것이 LSP 위반이 되는 조건은?
4. Python 에서 `class D(B, C)` 의 `B.hello` 안 `super().hello()` 는 어느 클래스의 메서드를 부르는가?
5. 합성이 상속보다 유연한 이유 두 가지를 들라.

### 풀이

1. 변수의 선언 타입이 아니라 실행 시점 객체의 실제 타입(동적 디스패치).
2. 부모 클래스의 내부 구현 변경이 그 구현에 의존하던 자식 클래스를 예상치 못하게 깨뜨리는 문제.
3. 직사각형의 계약에 "너비와 높이를 독립적으로 바꿀 수 있다"가 포함될 때(가변 직사각형). 불변 객체라면 문제가 사라진다.
4. `D` 의 MRO `D, B, C, A` 에서 `B` 다음인 `C.hello`.
5. 내부 객체의 공개 인터페이스에만 의존해 캡슐화가 유지되고, 실행 중에 부품을 바꿀 수 있으며, 조합마다 클래스를 만들 필요가 없다.

## 더 읽을거리 (References)

- Barbara H. Liskov, Jeannette M. Wing, "A Behavioral Notion of Subtyping", ACM TOPLAS 16(6), 1994
- Gamma, Helm, Johnson, Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, 1994
- Python Docs, [The Python 2.3 Method Resolution Order](https://docs.python.org/3/howto/mro.html)
- The Java Tutorials, [Multiple Inheritance of State, Implementation, and Type](https://docs.oracle.com/javase/tutorial/java/IandI/multipleinheritance.html)
- The Rust Programming Language, [Characteristics of Object-Oriented Languages](https://doc.rust-lang.org/book/ch18-01-what-is-oo.html)
