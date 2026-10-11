---
layout: post
title: "자바 패턴 매칭 완전 정리 — instanceof 패턴, switch 식, record 패턴, switch 패턴 매칭까지"
date: 2026-10-12 00:16:42 +0900
categories: [java]
tags: [java, pattern-matching, switch-expression, record-pattern, sealed, instanceof, jdk16, jdk17, jdk21, jdk25, jep-441, jep-440, jep-394, jep-361]
---

자바·코틀린 20편 시리즈의 **자바 6번째 글(J6)** 입니다. 이번 글은 JDK 14 부터 21 까지 여러 릴리스에 걸쳐 조금씩 완성된 **패턴 매칭(pattern matching)** 을 한 번에 정리합니다. `instanceof` 패턴, `switch` 식, `switch` 패턴 매칭, record 패턴, 그리고 그 뒤에 붙은 unnamed 패턴(`_`)과 아직 프리뷰인 원시 타입 패턴까지 다룹니다. 각 문법은 **무엇인가 → 코드 → 실무 사용사례 → 함정** 순서로 봅니다.

코틀린의 `when` + `sealed class` 와 비교하고 싶다면 짝이 되는 [K3 — 코틀린 클래스: data/sealed/enum/object/value](https://myoungsoo7.github.io/2026/10/12/kotlin-classes-data-sealed-object-value/) 를 같이 읽으면 좋습니다. record 와 sealed 의 선언 자체는 [J3 — 클래스 모델의 진화](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/) 에서 다뤘습니다.

---

## 1. 큰 그림 — 패턴 매칭은 "검사 + 형변환 + 추출" 을 한 번에

패턴 매칭의 목표를 JEP 394 는 이렇게 설명합니다. 패턴은 객체가 가져야 할 "모양(shape)" 을 간결하게 표현하고, 여러 문장과 식이 그 모양을 입력에 대해 검사할 수 있게 한다는 것입니다 ([JEP 394](https://openjdk.org/jeps/394)).

전통적인 자바 코드에서는 이 세 단계가 따로 놀았습니다.

```java
if (obj instanceof String) {        // 1) 검사
    String s = (String) obj;        // 2) 형변환
    int len = s.length();           // 3) 사용
}
```

패턴 매칭은 이 셋을 하나의 구문으로 묶습니다. 핵심 기능별로 언제 정식(final) 기능이 되었는지부터 표로 정리합니다. 모든 행은 해당 JEP 문서에서 직접 확인했습니다.

| 기능 | 프리뷰 이력 | 정식 도입 | 근거 |
|---|---|---|---|
| `switch` 식 (`->`, `yield`) | JEP 325(JDK 12), JEP 354(JDK 13) | **JDK 14** | [JEP 361](https://openjdk.org/jeps/361) |
| `instanceof` 패턴 매칭 | JEP 305(JDK 14), JEP 375(JDK 15) | **JDK 16** | [JEP 394](https://openjdk.org/jeps/394) |
| sealed 클래스 | JEP 360(JDK 15), JEP 397(JDK 16) | **JDK 17** | [JEP 409](https://openjdk.org/jeps/409) |
| record 패턴 | JEP 405(JDK 19), JEP 432(JDK 20) | **JDK 21** | [JEP 440](https://openjdk.org/jeps/440) |
| `switch` 패턴 매칭 | JEP 406(17), 420(18), 427(19), 433(20) | **JDK 21** | [JEP 441](https://openjdk.org/jeps/441) |
| unnamed 변수·패턴 `_` | JEP 443(JDK 21 프리뷰) | **JDK 22** | [JEP 456](https://openjdk.org/jeps/456) |
| 원시 타입 패턴 | JEP 455(23), 488(24), 507(25), 530(26) | **아직 프리뷰** | [JEP 507](https://openjdk.org/jeps/507), [JEP 530](https://openjdk.org/jeps/530) |

실무 관점에서 요약하면 이렇습니다.

- **JDK 17 LTS** 에서는 `instanceof` 패턴, `switch` 식, sealed 까지 쓸 수 있습니다. `switch` 의 `case` 에 패턴을 쓰는 것은 17 에서는 프리뷰(JEP 406)였습니다.
- **JDK 21 LTS** 에서 record 패턴과 `switch` 패턴 매칭이 정식이 되면서 "sealed + record + switch" 조합이 완성됩니다.
- **JDK 25 LTS** 에서는 `_`(JDK 22 정식)까지 기본으로 쓸 수 있습니다.

---

## 2. `instanceof` 패턴 매칭 (JDK 16)

### 2.1 무엇인가

`instanceof` 뒤에 타입 대신 **타입 패턴**(타입 + 바인딩 변수)을 씁니다. 검사가 성공하면 바인딩 변수가 이미 그 타입으로 형변환된 상태로 스코프에 들어옵니다.

### 2.2 코드

```java
Object obj = fetch();

if (obj instanceof String s) {
    System.out.println(s.length());   // s 는 String
}

// && 오른쪽에서도 바로 사용 가능 — 왼쪽이 참일 때만 평가되기 때문
if (obj instanceof String s && !s.isBlank()) {
    System.out.println(s.strip());
}
```

**흐름 스코프(flow scoping)** 가 핵심입니다. 바인딩 변수는 "패턴이 확실히 매칭된 곳" 에서만 보입니다. 그래서 부정 조건으로 조기 반환하면 그 뒤에서 변수를 쓸 수 있습니다.

```java
if (!(obj instanceof String s)) {
    return;
}
// 여기서는 obj 가 String 임이 보장되므로 s 사용 가능
System.out.println(s.toUpperCase());
```

반대로 `||` 오른쪽에서는 쓸 수 없습니다. 왼쪽이 거짓일 때(=매칭 실패) 평가되기 때문입니다.

```java
if (obj instanceof String s || s.isEmpty()) { }  // 컴파일 에러: s 를 찾을 수 없음
```

### 2.3 실무 사용사례 — `equals` 구현

`instanceof` 패턴이 가장 깔끔하게 빛나는 곳은 `equals` 입니다.

```java
public final class Money {
    private final long amount;
    private final String currency;

    public Money(long amount, String currency) {
        this.amount = amount;
        this.currency = currency;
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof Money other
                && amount == other.amount
                && currency.equals(other.currency);
    }

    @Override
    public int hashCode() {
        return java.util.Objects.hash(amount, currency);
    }
}
```

형변환 줄이 사라지고, 한 개의 불리언 식으로 의도가 드러납니다.

### 2.4 함정

1. **"항상 참인 검사" 규칙이 JDK 버전에 따라 다르다.** JDK 16 정식화 때, 식의 타입이 이미 패턴 타입의 하위 타입이라 검사가 항상 성공하는 경우를 컴파일 에러로 만들었습니다 ([JEP 394](https://openjdk.org/jeps/394)). JLS 17 §15.20.2 에도 이 규칙이 있습니다. 그런데 JLS 21 의 같은 절에서는 이 문장이 빠지고 "패턴이 식의 타입에 적용 가능해야 한다(applicable)" 는 규칙으로 바뀌었습니다 ([JLS 17 §15.20.2](https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.20.2), [JLS 21 §15.20.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.20.2)).

   ```java
   String str = "a";
   if (str instanceof CharSequence cs) { }  // JDK 17: 컴파일 에러 / JDK 21: 허용
   ```

   어느 쪽이든 이런 검사는 의미가 없으니 쓰지 않는 게 맞습니다. 다만 **17 에서 21 로 올리면서 이런 코드가 갑자기 컴파일되는 것** 은 정상입니다.

2. **패턴 변수는 `final` 이 아니다.** 프리뷰 때는 암묵적 `final` 이었지만 정식판에서 그 제약이 빠졌습니다 ([JEP 394](https://openjdk.org/jeps/394)). 재할당이 가능하지만, 재할당하면 "이 변수는 매칭된 그 객체" 라는 읽는 사람의 기대가 깨집니다. 필요하면 직접 `final` 을 붙이세요.

   ```java
   if (obj instanceof final String s) { /* s 재할당 불가 */ }
   ```

3. **필드 이름 가리기(shadowing).** 바인딩 변수 이름이 필드와 같으면, 스코프에 따라 같은 이름이 필드를 가리켰다가 지역 변수를 가리켰다가 합니다. 패턴 변수에는 필드와 겹치지 않는 이름을 쓰는 게 안전합니다.

---

## 3. `switch` 식 (JDK 14)

패턴을 `case` 에 쓰기 전에, 먼저 `switch` 자체가 **식(expression)** 이 되어야 했습니다.

### 3.1 무엇인가

JEP 361 은 다음을 정식화했습니다 ([JEP 361](https://openjdk.org/jeps/361)).

- **화살표 레이블 `case L ->`**: 화살표 오른쪽만 실행되고 **fall-through 가 없다.**
- **여러 레이블 묶기**: `case MONDAY, FRIDAY, SUNDAY -> 6;`
- **`yield`**: 블록 안에서 `switch` 식의 값을 돌려준다.
- **enum 완전성 검사**: 모든 상수를 다룬 enum `switch` 식에는 컴파일러가 암묵적 default 를 넣어, 컴파일 이후 enum 이 바뀐 경우를 런타임에 잡는다.

### 3.2 코드

```java
enum Day { MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY }

int letters = switch (day) {
    case MONDAY, FRIDAY, SUNDAY -> 6;
    case TUESDAY                -> 7;
    case THURSDAY, SATURDAY     -> 8;
    case WEDNESDAY              -> 9;
};  // 모든 상수를 다뤘으므로 default 불필요
```

블록이 필요하면 `yield` 로 값을 냅니다.

```java
String label = switch (status) {
    case 200, 201, 204 -> "OK";
    case 404 -> "NOT_FOUND";
    default -> {
        log.warn("unexpected status {}", status);
        yield "UNKNOWN";
    }
};
```

### 3.3 실무 사용사례

- **enum → 값 매핑**: 주문 상태 → 화면 표시 문자열, 결제 수단 → 수수료율 등. `Map` 상수 대신 `switch` 식을 쓰면 **상수 하나가 추가됐을 때 컴파일러가 누락을 알려 줍니다.**
- **분기 결과를 `final` 지역 변수에 담기**: 이전에는 `String x; switch(...) { case ...: x = ...; break; }` 처럼 변수를 먼저 선언해야 했지만, 이제 한 번에 초기화합니다.

### 3.4 함정

1. **`default` 를 습관적으로 붙이면 완전성 검사가 무력화됩니다.** 위 `Day` 예제에 `default -> 0` 을 붙이면, 나중에 enum 상수가 늘어도 컴파일러가 아무 말도 하지 않습니다. enum 이나 sealed 타입을 `switch` 할 때는 **`default` 를 쓰지 않는 것**이 완전성 검사를 살리는 방법입니다.
2. **화살표와 콜론을 섞을 수 없습니다.** 한 `switch` 블록에서 `case X ->` 와 `case Y:` 를 섞으면 컴파일 에러입니다.
3. **`yield` 와 `return`.** `switch` 식 블록 안에서 `return` 으로 메서드를 빠져나갈 수 없습니다. 값을 내려면 `yield` 를 씁니다.

---

## 4. `switch` 패턴 매칭 (JDK 21)

### 4.1 무엇인가

JDK 21 의 JEP 441 은 `case` 레이블에 **패턴**을 허용합니다 ([JEP 441](https://openjdk.org/jeps/441)). 동시에 다음이 들어왔습니다.

- **선택자 타입 확장**: 선택자는 정수형 원시 타입(`long` 제외) 또는 **어떤 참조 타입이든** 될 수 있다.
- **`case null`**: 선택자가 `null` 이면 `null` 레이블이 매칭된다. `null` 레이블이 없으면 기존처럼 `NullPointerException`.
- **가드 `when`**: `case String s when s.length() > 0 ->`
- **지배(dominance) 검사**: 앞선 레이블이 뒤 레이블을 항상 덮으면 컴파일 에러. 하위 타입이 상위 타입보다 먼저 와야 한다.
- **완전성(exhaustiveness)**: 패턴이나 `null` 레이블을 쓰는 `switch` 는 **문(statement)이든 식이든** 모든 입력을 다뤄야 한다.
- **한정된 enum 상수**: `case Suit.HEARTS ->` 처럼 enum 이 아닌 선택자 타입에서도 enum 상수를 쓸 수 있다.

### 4.2 코드 — 타입 패턴과 가드

```java
static String describe(Object o) {
    return switch (o) {
        case null                         -> "null";
        case Integer i when i > 0         -> "양의 정수 " + i;
        case Integer i                    -> "정수 " + i;
        case String s when s.isBlank()    -> "빈 문자열";
        case String s                     -> "문자열 " + s;
        case int[] arr                    -> "int 배열, 길이 " + arr.length;
        default                           -> "기타 " + o.getClass().getSimpleName();
    };
}
```

여기서 `Integer i when i > 0` 이 `Integer i` 보다 **먼저** 와야 합니다. 순서를 바꾸면 `Integer i` 가 모든 `Integer` 를 먹어 버리므로 지배 규칙 위반으로 컴파일 에러가 납니다. JLS 는 "가드가 붙은 레이블은 같은 패턴의 가드 없는 레이블에 지배된다" 고 정하고, 반대로 가드 붙은 레이블이 가드 없는 레이블을 지배하지는 않는다고 정합니다. 그래서 "좁은 조건 먼저, 넓은 조건 나중" 이라는 흔한 스타일이 허용됩니다 ([JLS 21 §14.11.1](https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html#jls-14.11.1)).

### 4.3 `null` 처리

```java
switch (o) {
    case String s      -> System.out.println(s);
    case null, default -> System.out.println("null 이거나 처리하지 않는 타입");
}
```

`case null, default` 는 JEP 441 이 명시적으로 허용한 형태입니다. 중요한 점은 **`default` 단독으로는 `null` 에 매칭되지 않는다**는 것입니다. 기존 `switch` 의 의미를 보존하기 위해서입니다 ([JEP 441](https://openjdk.org/jeps/441)).

**위치도 규칙입니다.** JLS 21 §14.11.1 은 `default` 가 패턴 `case` 나 `case null` 보다 앞에 오는 것, 그리고 `case null, default` 뒤에 다른 레이블이 오는 것을 컴파일 에러로 정합니다 ([JLS 21 §14.11.1](https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html#jls-14.11.1)). 패턴을 쓰는 `switch` 에서 `default` 는 항상 맨 끝에 둡니다.

### 4.4 sealed 와 만나면 — `default` 없는 완전성

`switch` 패턴 매칭의 진가는 sealed 계층과 함께 쓸 때 드러납니다. JEP 409 는 sealed 클래스가 패턴 매칭 `switch` 의 완전성 검사를 가능하게 한다고 명시합니다 ([JEP 409](https://openjdk.org/jeps/409)).

```java
public sealed interface PaymentResult
        permits PaymentResult.Approved, PaymentResult.Declined, PaymentResult.Pending {

    record Approved(String txId, long amount) implements PaymentResult {}
    record Declined(String reason) implements PaymentResult {}
    record Pending(String txId) implements PaymentResult {}
}

static String toMessage(PaymentResult r) {
    return switch (r) {
        case PaymentResult.Approved a -> "승인: " + a.txId();
        case PaymentResult.Declined d -> "거절: " + d.reason();
        case PaymentResult.Pending p  -> "대기: " + p.txId();
        // default 없음 — 세 경우가 전부이므로 완전함
    };
}
```

나중에 `record Refunded(...)` 를 `permits` 에 추가하면, `default` 가 없는 모든 `switch` 가 **컴파일 에러**로 바뀝니다. "새 상태를 추가했는데 처리 안 한 곳" 을 컴파일러가 찾아 주는 것, 이게 sealed + switch 조합을 쓰는 가장 큰 이유입니다.

컴파일 이후 계층이 바뀌어 런타임에 맞는 레이블이 없으면 예외가 납니다. JEP 441 은 이 의미를 맞추기 위해 enum `switch` 식도 `IncompatibleClassChangeError` 대신 `MatchException` 을 던지도록 바꿨다고 설명합니다 ([JEP 441](https://openjdk.org/jeps/441)).

### 4.5 실무 사용사례

- **도메인 결과 타입 → HTTP 응답 매핑**: 서비스가 예외 대신 sealed 결과를 반환하고, 컨트롤러 경계에서 한 번 `switch` 로 매핑합니다.

  ```java
  @PostMapping("/payments")
  ResponseEntity<?> pay(@RequestBody PayRequest req) {
      return switch (paymentService.pay(req)) {
          case PaymentResult.Approved a -> ResponseEntity.ok(a);
          case PaymentResult.Declined d -> ResponseEntity.unprocessableEntity().body(d);
          case PaymentResult.Pending p  -> ResponseEntity.accepted().body(p);
      };
  }
  ```

- **이벤트/메시지 디스패치**: Kafka 등에서 역직렬화한 이벤트를 sealed 인터페이스로 받아 타입별 핸들러로 분기.
- **레거시 `instanceof` 사슬 정리**: `if (x instanceof A) ... else if (x instanceof B) ...` 를 `switch` 로 바꾸면 순서 오류(상위 타입이 먼저 오는 실수)를 컴파일러가 잡아 줍니다.

### 4.6 함정

1. **`default` 가 완전성 검사를 지운다.** 3.4 와 같은 이야기지만 sealed 에서는 훨씬 치명적입니다. sealed 계층을 `switch` 할 때는 `default` 를 빼세요.
2. **가드 안의 부수효과.** `when` 절은 매칭 시도 과정에서 평가됩니다. 로그 출력, DB 조회 같은 부수효과를 넣지 마세요.
3. **다형성으로 풀어야 할 문제를 `switch` 로 풀지 말 것.** 각 타입이 "자기 행동" 을 가지는 것이 자연스러우면(예: `Shape.area()`), 메서드 오버라이딩이 여전히 정답입니다. `switch` 패턴 매칭은 **데이터와 연산을 분리하고 싶을 때**(연산이 자주 늘어나고 타입 집합은 닫혀 있을 때) 유리합니다. 이는 비지터 패턴이 풀던 문제와 같습니다.
4. **`switch` 문도 완전해야 할 수 있다.** 예전 `switch` 문은 일부 `case` 만 써도 됐지만, 패턴이나 `null` 레이블을 쓰거나 선택자가 레거시 타입(정수형, `String`, enum 등)이 아니면 **문도 완전해야** 합니다 ([JEP 441](https://openjdk.org/jeps/441)).

---

## 5. record 패턴 (JDK 21)

### 5.1 무엇인가

record 패턴은 record 를 **구성요소 단위로 분해(deconstruct)** 합니다. JEP 440 의 정의로는, 값 `v` 가 `Point` 의 인스턴스이면 `v` 는 record 패턴 `Point(int i, int j)` 에 매칭됩니다 ([JEP 440](https://openjdk.org/jeps/440)). 이때 `i`, `j` 에는 접근자 메서드가 돌려준 값이 바인딩됩니다.

### 5.2 코드 — 분해, 중첩, `var`

```java
record Point(int x, int y) {}
enum Color { RED, GREEN, BLUE }
record ColoredPoint(Point p, Color c) {}
record Rectangle(ColoredPoint upperLeft, ColoredPoint lowerRight) {}

static void printSum(Object obj) {
    if (obj instanceof Point(int x, int y)) {
        System.out.println(x + y);
    }
}

// 중첩 패턴 — 한 번에 깊이 분해
static void printUpperLeftColor(Rectangle r) {
    if (r instanceof Rectangle(ColoredPoint(Point p, Color c), ColoredPoint lr)) {
        System.out.println(c);
    }
}

// var 로 타입 추론
static int sumWithVar(Object obj) {
    if (obj instanceof Point(var a, var b)) {
        return a + b;
    }
    return 0;
}
```

JEP 440 은 중첩 패턴에 대해 "집합체를 조립하는 코드만큼 명확하고 간결하게 분해할 수 있게 해 준다" 고 설명합니다 ([JEP 440](https://openjdk.org/jeps/440)).

### 5.3 제네릭 record 의 타입 인자 추론

```java
record Box<T>(T t) {}

static void test(Box<Box<String>> bbs) {
    if (bbs instanceof Box(Box(var s))) {     // Box<Box<String>> 로 추론
        System.out.println("String " + s);
    }
}
```

`Box(Box(var s))` 처럼 타입 인자를 생략해도 컴파일러가 추론합니다 ([JEP 440](https://openjdk.org/jeps/440)).

### 5.4 실무 사용사례 — 식(expression) 트리 평가

record 패턴 + sealed + switch 조합의 교과서적 사례는 트리 구조 해석입니다. 할인 규칙 엔진, 검색 쿼리 DSL, 권한 정책 식 같은 곳에 그대로 쓰입니다.

```java
sealed interface Expr permits Const, Neg, Add, Mul {}
record Const(int value) implements Expr {}
record Neg(Expr e) implements Expr {}
record Add(Expr left, Expr right) implements Expr {}
record Mul(Expr left, Expr right) implements Expr {}

static int eval(Expr e) {
    return switch (e) {
        case Const(int v)              -> v;
        case Neg(Expr inner)           -> -eval(inner);
        case Add(Expr l, Expr r)       -> eval(l) + eval(r);
        case Mul(Const(int v), Expr r) when v == 0 -> 0;   // 단락 최적화
        case Mul(Expr l, Expr r)       -> eval(l) * eval(r);
    };
}
```

- `Mul(Const(int v), Expr r) when v == 0` 은 일반 `Mul` 보다 **좁은** 패턴이므로 앞에 와야 합니다.
- `default` 가 없어도 `Expr` 가 sealed 이므로 완전합니다.

### 5.5 실무 사용사례 — 결과 타입 분해

```java
sealed interface Result<T> permits Ok, Err {}
record Ok<T>(T value) implements Result<T> {}
record Err<T>(String code, String message) implements Result<T> {}

static <T> String render(Result<T> r) {
    return switch (r) {
        case Ok<T>(var v)                      -> "OK " + v;
        case Err<T>(var code, var msg) when code.startsWith("5") -> "서버 오류: " + msg;
        case Err<T>(var code, var msg)         -> "클라이언트 오류(" + code + "): " + msg;
    };
}
```

### 5.6 함정

1. **record 패턴은 `null` 에 매칭되지 않습니다.** JEP 440 은 "`null` 값은 어떤 record 패턴에도 매칭되지 않는다" 고 명시합니다 ([JEP 440](https://openjdk.org/jeps/440)). 선택자가 `null` 일 수 있으면 `case null` 을 따로 두세요.
2. **향상된 `for` 에서는 못 씁니다.** 두 번째 프리뷰(JDK 20)까지는 `for (Point(var x, var y) : points)` 가 가능했지만, JDK 21 정식판에서 **제거**되었습니다 ([JEP 440](https://openjdk.org/jeps/440)). 오래된 블로그 예제를 복사하면 컴파일되지 않습니다.
3. **구성요소 순서에 묶입니다.** record 패턴은 위치 기반입니다. record 의 구성요소 순서를 바꾸면, 타입이 같은 구성요소끼리는 **컴파일 에러 없이 의미가 뒤바뀝니다**(`Point(int x, int y)` → `Point(int y, int x)`). 공개 API 의 record 구성요소 순서는 바꾸지 않는 것을 원칙으로 두세요.
4. **분해는 접근자를 호출합니다.** 구성요소 값은 접근자 메서드를 통해 얻습니다. 접근자를 오버라이드해 무거운 로직을 넣었다면 패턴 매칭 때마다 실행됩니다.

---

## 6. unnamed 변수와 패턴 `_` (JDK 22)

### 6.1 무엇인가

JDK 22 의 JEP 456 은 **쓰지 않는 바인딩**을 `_` 로 표시할 수 있게 했습니다. JDK 21 에서는 JEP 443 으로 프리뷰였고, 22 에서 변경 없이 정식화되었습니다 ([JEP 456](https://openjdk.org/jeps/456)). JDK 21 LTS 에서는 프리뷰라 `--enable-preview` 없이는 못 쓰고, **JDK 25 LTS** 에서는 정식입니다.

- **unnamed 변수**: 지역 변수, try-with-resources, `for` 루프, `catch` 블록, 람다 파라미터.
- **unnamed 패턴**: 필요 없는 구성요소 이름을 생략. 한 `case` 에 여러 패턴을 대안으로 나열할 수 있게 해 줍니다.

### 6.2 코드

```java
// 쓰지 않는 구성요소
if (r instanceof ColoredPoint(Point(var x, var y), _)) {
    System.out.println(x + y);
}

// 여러 패턴을 한 case 로
static String kind(Expr e) {
    return switch (e) {
        case Const _              -> "상수";
        case Neg _                -> "단항";
        case Add _, Mul _         -> "이항";
    };
}

// catch 에서 예외 객체를 쓰지 않을 때
try {
    Integer.parseInt(input);
} catch (NumberFormatException _) {
    return Optional.empty();
}

// 람다 파라미터
map.forEach((_, v) -> total.add(v));
```

### 6.3 함정

- `_` 는 **읽을 수도 쓸 수도 없습니다.** JEP 456 의 표현대로 unnamed 변수를 선언하면 스코프에 이름이 생기지 않습니다. 디버깅 중 값을 찍어 보려면 이름을 다시 붙여야 합니다.
- JDK 9 부터 `_` 를 식별자로 쓰는 것은 이미 에러였습니다([JEP 213](https://openjdk.org/jeps/213)). 아주 오래된 코드에서 `_` 를 변수 이름으로 쓰고 있었다면 그때 이미 깨졌을 것입니다.

---

## 7. 아직 프리뷰 — 원시 타입 패턴

JDK 23 부터 원시 타입을 패턴, `instanceof`, `switch` 에서 쓰는 기능이 프리뷰로 들어왔습니다. JDK 25 에서는 세 번째 프리뷰(JEP 507), JDK 26 에서는 네 번째 프리뷰(JEP 530)입니다 ([JEP 507](https://openjdk.org/jeps/507), [JEP 530](https://openjdk.org/jeps/530)).

```java
// 프리뷰(JDK 25, JDK 26) — --enable-preview 필요
int i = 300;
if (i instanceof byte b) {
    // i 가 byte 범위에 정확히 들어갈 때만 매칭
    System.out.println("byte 로 안전하게 표현됨: " + b);
}
```

JEP 507 은 이를 "대입문의 편리함과 패턴 매칭의 안전성" 의 결합이라고 설명합니다. 범위 검사 후 캐스팅하던 코드를 대체하려는 목적입니다.

**주의**: JEP 530 은 지배 검사를 더 엄격하게 바꾸면서 일부 기존 `switch` 가 컴파일 에러가 될 수 있는 **소스 비호환 변경**을 포함합니다 ([JEP 530](https://openjdk.org/jeps/530)). 프리뷰 기능은 릴리스마다 바뀔 수 있으니 운영 코드에는 쓰지 않는 것이 원칙입니다.

---

## 8. 설계 관점 — "닫힌 타입 집합 + 데이터 + 연산 분리"

패턴 매칭 기능들을 한 문장으로 묶으면 **대수적 데이터 타입(ADT)을 자바로 표현하는 도구** 입니다.

| 구성요소 | 자바 문법 | 역할 |
|---|---|---|
| 합 타입(sum type) — "A 이거나 B" | `sealed interface ... permits` | 경우의 수를 닫는다 |
| 곱 타입(product type) — "A 와 B" | `record` | 데이터를 담는다 |
| 분해 + 분기 | `switch` 패턴 + record 패턴 | 경우별 연산 |
| 누락 검출 | 완전성 검사 | 컴파일 타임 안전망 |

### 8.1 언제 이 조합을 쓰나

- **타입 집합이 안정적이고 연산이 자주 늘어날 때.** 결제 결과(승인/거절/대기)는 거의 안 늘어나지만, 그 결과로 하는 일(응답 매핑, 알림, 정산, 통계)은 계속 늘어납니다. 이럴 때 연산마다 `switch` 를 하나씩 두는 게 각 record 에 메서드를 계속 추가하는 것보다 낫습니다.
- **경계(boundary)에서 변환할 때.** 외부 API 응답, 메시지, 커맨드 객체처럼 "데이터일 뿐인 것" 을 다룰 때.

### 8.2 언제 쓰지 말아야 하나

- **타입이 계속 늘어나는 확장 지점.** 플러그인, 전략 패턴 구현체처럼 외부에서 구현을 추가해야 하면 sealed 로 닫으면 안 됩니다. 인터페이스 + 다형성이 맞습니다.
- **JPA 엔티티.** record 는 `final` 이고 필드가 `private final` 이며 인스턴스 필드를 추가로 선언할 수 없습니다 ([JEP 395](https://openjdk.org/jeps/395)). 프록시·지연 로딩·변경 감지를 쓰는 엔티티에는 맞지 않습니다. record 는 DTO·값 객체·결과 타입에 씁니다.

### 8.3 코틀린과의 대응

| 자바 | 코틀린 |
|---|---|
| `sealed interface` + `record` | `sealed interface` + `data class` |
| `switch` 패턴 + 완전성 | `when` + 완전성 (sealed 대상) |
| `instanceof` 패턴의 흐름 스코프 | 스마트 캐스트 |
| record 패턴 분해 | 구조 분해 선언 `val (a, b) = ...` (위치 기반, `componentN`) |

코틀린 쪽 세부 문법과 차이는 [K3](https://myoungsoo7.github.io/2026/10/12/kotlin-classes-data-sealed-object-value/) 와 [K2 — 널 안전과 스마트 캐스트](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/) 에서 다룹니다.

---

## 9. 마이그레이션 체크리스트

| 현재 코드 | 바꿀 형태 | 최소 JDK |
|---|---|---|
| `if (x instanceof T) { T t = (T) x; ... }` | `if (x instanceof T t)` | 16 |
| 콜론 `switch` + `break` 로 값 대입 | `switch` 식 + `->` | 14 |
| `instanceof` 사슬로 타입 분기 | `switch` 패턴 매칭 | 21 |
| 분기 후 접근자 여러 번 호출 | record 패턴 분해 | 21 |
| `catch (Exception ignored)` | `catch (Exception _)` | 22 (LTS 기준 25) |

적용 순서는 이렇게 권합니다.

1. **JDK 17 에서 바로**: `instanceof` 패턴, `switch` 식. IDE 가 자동 변환을 제안하는 경우가 많아 위험이 낮습니다.
2. **JDK 21 이후**: 도메인 결과 타입을 sealed + record 로 정의하고, 경계에서 `switch` 패턴 매칭으로 처리.
3. **`default` 감사**: sealed/enum 대상 `switch` 의 `default` 를 찾아 지울 수 있는지 봅니다. 지울 수 있으면 지우는 것이 완전성 검사를 되살립니다.

---

## 10. 정리

- `instanceof` 패턴(16)과 `switch` 식(14)은 **문법 설탕 이상**입니다. 흐름 스코프와 완전성 검사가 컴파일러에게 더 많은 것을 검증하게 합니다.
- JDK 21 의 `switch` 패턴 매칭과 record 패턴이 들어오면서, **sealed + record + switch** 로 "닫힌 경우의 수" 를 타입으로 표현하고 누락을 컴파일 타임에 잡는 것이 자바에서도 자연스러워졌습니다.
- 핵심 함정은 세 가지: **습관적 `default`**, **`null` 처리 누락**(`default` 는 `null` 에 매칭 안 됨, record 패턴도 `null` 에 매칭 안 됨), **구성요소 순서 변경**.
- 원시 타입 패턴은 JDK 26 기준 아직 프리뷰입니다.

---

## References

- [JEP 361: Switch Expressions](https://openjdk.org/jeps/361) — OpenJDK
- [JEP 394: Pattern Matching for instanceof](https://openjdk.org/jeps/394) — OpenJDK
- [JEP 409: Sealed Classes](https://openjdk.org/jeps/409) — OpenJDK
- [JEP 395: Records](https://openjdk.org/jeps/395) — OpenJDK
- [JEP 440: Record Patterns](https://openjdk.org/jeps/440) — OpenJDK
- [JEP 441: Pattern Matching for switch](https://openjdk.org/jeps/441) — OpenJDK
- [JEP 456: Unnamed Variables & Patterns](https://openjdk.org/jeps/456) — OpenJDK
- [JEP 213: Milling Project Coin](https://openjdk.org/jeps/213) — OpenJDK
- [JEP 507: Primitive Types in Patterns, instanceof, and switch (Third Preview)](https://openjdk.org/jeps/507) — OpenJDK
- [JEP 530: Primitive Types in Patterns, instanceof, and switch (Fourth Preview)](https://openjdk.org/jeps/530) — OpenJDK
- [JDK 21 프로젝트 페이지](https://openjdk.org/projects/jdk/21/) — OpenJDK
- [JLS 21 §14.11.1 Switch Blocks](https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html#jls-14.11.1) — Oracle
- [JLS 17 §15.20.2](https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.20.2), [JLS 21 §15.20.2 The instanceof Operator](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.20.2) — Oracle

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/) ← 지금 글
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/)
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/)
- J9. [스프링이 자바를 쓰는 방식 — 리플렉션·프록시·DI](/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/)
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/)

**코틀린**

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/)
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
