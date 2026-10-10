---
layout: post
title: "[CS300 #026] 정적 타입과 동적 타입 — 타입 오류를 언제 잡을 것인가"
date: 2026-10-10 18:26:00 +0900
categories: [cs]
tags: [cs300, programming, type-system, static-typing, dynamic-typing]
---

컴퓨터공학 300 주제 시리즈의 026번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

정적 타입은 프로그램을 실행하기 전에 타입을 검사하고, 동적 타입은 실행 중에 값이 쓰이는 순간 검사한다. 이것은 "강한 타입/약한 타입"과는 다른 축이다.

## 왜 필요한가

"파이썬은 타입이 없다", "자바스크립트는 약한 타입이라 나쁘다", "타입스크립트는 정적 타입이라 안전하다". 이런 문장은 반은 맞고 반은 틀리다. 용어를 섞어 쓰면 언어 선택이나 코드 리뷰에서 엉뚱한 논쟁을 한다.

실무에서는 두 세계가 섞인다. Python 에 타입 힌트를 달고 mypy 를 CI 에 돌리고, TypeScript 를 쓰면서 외부 JSON 은 런타임에 다시 검증한다. 각 방식이 무엇을 보장하고 무엇을 보장하지 않는지 알아야 이런 조합을 제대로 설계할 수 있다.

## 핵심 개념

### 두 개의 축

| | 암묵적 형변환 적음 (강함) | 암묵적 형변환 많음 (약함) |
|---|---|---|
| **정적** (실행 전 검사) | Java, Rust, Haskell, Go | C (포인터·정수 변환이 느슨) |
| **동적** (실행 중 검사) | Python, Ruby | JavaScript, PHP |

- **정적/동적**은 타입 검사 **시점**의 문제다. 변수·식에 컴파일 시점에 타입이 정해지는가, 값에만 타입이 붙어 있고 실행 시 확인하는가.
- **강함/약함**은 엄밀한 정의가 없는 비공식 용어다. 대체로 "서로 맞지 않는 타입을 만나면 오류를 내는가, 조용히 변환하는가"를 가리킨다. 학술적으로는 타입 오류가 정의되지 않은 동작으로 이어지지 않는다는 **타입 안전성(type safety)** 으로 말하는 편이 정확하다.

Python 은 동적이면서 강한 쪽이다. `"1" + 1` 은 `TypeError` 다. JavaScript 는 동적이면서 약한 쪽이라 `"1" + 1` 이 `"11"` 이 된다.

### 정적 타입: 실행 전에 증명한다

정적 타입 검사기는 프로그램의 모든 실행 경로에 대해 "이 식은 이 타입의 값만 낸다"를 증명하려 한다. 증명하지 못하면 거부한다.

장점:
- 오류를 **실행하지 않은 경로**에서도 찾는다. 드물게 실행되는 에러 처리 분기의 오타가 대표적이다.
- 리팩터링이 안전하다. 함수 시그니처를 바꾸면 깨지는 호출 지점이 모두 드러난다.
- 타입이 문서 역할을 하고, IDE 자동 완성이 정확해진다.
- 컴파일러가 타입 정보를 써서 최적화한다(필드 위치를 고정 오프셋으로 접근 등).

단점:
- 올바른 프로그램을 거부할 수 있다. 검사기는 보수적이어서 "안전함을 증명 못 한 것"을 막는다.
- 표현력이 부족한 타입 시스템에서는 장황한 선언이 필요하다. 타입 추론(#038)과 제네릭(#033)이 이를 줄인다.

### 동적 타입: 값이 타입을 들고 다닌다

동적 언어에서 변수는 아무 값이나 가리킬 수 있고, **값(객체)** 이 자신의 타입을 기억한다. 연산을 할 때 인터프리터가 피연산자의 타입을 보고 허용 여부를 정한다. Python 데이터 모델은 모든 객체가 타입을 가지며 그 타입이 객체가 지원하는 연산을 결정한다고 정의한다([Data model](https://docs.python.org/3/reference/datamodel.html)).

장점: 빠른 프로토타이핑, 덕 타이핑("오리처럼 걸으면 오리"), 메타프로그래밍이 쉽다.
단점: 실행된 경로에서만 오류를 찾는다. 그래서 테스트 커버리지가 곧 타입 검사 커버리지가 된다.

### 점진적 타입: 둘 사이의 다리

Python 은 2014년 PEP 484 로 타입 힌트 문법을 표준화했다([PEP 484](https://peps.python.org/pep-0484/)). 핵심은 **힌트가 런타임에 강제되지 않는다**는 점이다. PEP 484 는 Python 이 동적 타입 언어로 남을 것이며, 힌트를 의무화할 의도가 없다고 명시한다. 검사는 mypy 같은 외부 도구가 실행 전에 한다([mypy documentation](https://mypy.readthedocs.io/en/stable/)).

TypeScript 도 비슷하다. 컴파일하면 타입 정보가 지워진 JavaScript 가 나온다. 그래서 정적 검사가 통과해도 외부에서 들어온 JSON 이 선언과 다르면 런타임에는 아무도 막지 않는다. 핸드북은 이를 "Erased Types" 로 설명한다([TypeScript Handbook, The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html)).

```
 소스 + 타입 힌트
      │
      ├── mypy / tsc  ──> 실행 전 검사 (선택적)
      │
      └── 인터프리터 / JS 엔진 ──> 힌트 무시, 값의 타입으로만 동작
```

### 건전성

정적 타입 시스템이 **건전(sound)** 하다는 것은 "검사를 통과하면 실행 중 그 종류의 타입 오류가 절대 나지 않는다"는 뜻이다. 많은 실용 시스템은 의도적으로 완전히 건전하지 않다. TypeScript 의 `any`, Python 의 `Any`, Java 배열의 공변성이 그런 예다. 정적 타입이 있다고 런타임 검증을 생략해도 되는 것은 아니다.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
def area(w: int, h: int) -> int:
    return w * h

print(area(3, 4))           # 12
print(area("ab", 3))        # ababab   힌트는 강제되지 않는다
print(area.__annotations__) # {'w': <class 'int'>, 'h': <class 'int'>, 'return': <class 'int'>}

def report(flag):
    if flag:
        return len(42)      # 버그가 숨어 있는 분기
    return "ok"

print(report(False))        # ok   실행되지 않은 경로의 오류는 드러나지 않는다
report(True)                # TypeError: object of type 'int' has no len()

"1" + 1                     # TypeError: can only concatenate str (not "int") to str
```

같은 실수를 Java 로 쓰면 컴파일 단계에서 막힌다(OpenJDK 25 `javac` 출력).

```java
public class T {
    static int area(int w, int h) { return w * h; }
    public static void main(String[] a) { System.out.println(area("ab", 3)); }
}
```

```
T.java:3: error: incompatible types: String cannot be converted to int
```

JavaScript 의 암묵적 변환(Node.js 22):

```javascript
console.log("1" + 1, "5" - 2, 1 == "1", 1 === "1");
// 11 3 true false
```

`+` 는 문자열이 끼면 연결로, `-` 는 숫자로 변환한다. `==` 는 변환 후 비교, `===` 는 변환 없이 비교한다.

## 현업에서는

- **Python 서비스의 타입 힌트 + CI**: 팀 규모가 커지면 mypy 나 pyright 를 CI 에 넣고, 새 코드부터 힌트를 의무화하는 방식으로 점진 도입한다.
- **경계에서의 런타임 검증**: 정적 타입은 프로세스 안의 일관성만 보장한다. HTTP 요청 본문, 메시지 큐 페이로드, 설정 파일은 스키마 검증(Pydantic, JSON Schema, Zod 등)을 거쳐야 한다. 쿠버네티스 API 서버가 매니페스트를 OpenAPI 스키마로 검증하는 것도 같은 이유다.
- **언어 선택 기준**: 짧은 스크립트·데이터 탐색은 동적 언어가 빠르다. 오래 유지보수할 대형 코드베이스, 여러 팀이 공유하는 라이브러리는 정적 타입의 리팩터링 안전성이 비용을 넘어선다.
- **`any` 의 확산**: TypeScript 프로젝트에서 `any` 가 늘면 정적 검사의 이득이 조용히 사라진다. `noImplicitAny` 같은 엄격 옵션을 켜는 이유다.

## 확인 문제

1. "Python 은 타입이 없는 언어다"라는 말이 틀린 이유는?
2. 정적/동적과 강함/약함은 각각 무엇을 기준으로 나누는가?
3. 위 `report` 함수의 버그를 동적 언어에서 실행 전에 찾으려면 무엇이 필요한가?
4. PEP 484 타입 힌트를 단 함수에 잘못된 타입을 넘기면 Python 인터프리터는 어떻게 하는가?
5. 정적 타입 언어인 TypeScript 를 써도 API 응답을 런타임에 검증해야 하는 이유는?

### 풀이

1. Python 의 모든 값은 타입을 가지며, 타입에 맞지 않는 연산은 `TypeError` 로 거부된다. 변수에 타입 선언이 없을 뿐 값에는 타입이 있다.
2. 정적/동적은 타입 검사 시점(실행 전/실행 중), 강함/약함은 맞지 않는 타입을 조용히 변환하는 정도다.
3. 타입 힌트와 mypy 같은 정적 검사기, 또는 그 분기를 실제로 실행하는 테스트.
4. 아무것도 하지 않는다. 힌트는 `__annotations__` 에 저장될 뿐 강제되지 않는다. 연산 시점에 타입이 맞지 않으면 그때 오류가 난다.
5. 컴파일 후 타입 정보가 지워지고, 외부 데이터는 컴파일러가 본 적 없는 값이기 때문이다.

## 더 읽을거리 (References)

- [PEP 484 — Type Hints](https://peps.python.org/pep-0484/)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- TypeScript Handbook, [The Basics — Erased Types](https://www.typescriptlang.org/docs/handbook/2/basic-types.html)
- Benjamin C. Pierce, *Types and Programming Languages*, MIT Press, 2002 — 1장 타입 시스템의 정의와 안전성
