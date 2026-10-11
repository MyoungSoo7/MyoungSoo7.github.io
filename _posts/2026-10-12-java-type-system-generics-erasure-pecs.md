---
layout: post
title: "자바 타입 시스템 — 원시/참조 타입과 박싱, 제네릭과 타입 소거, 와일드카드와 PECS"
date: 2026-10-12 00:12:42 +0900
categories: [java]
tags: [java, generics, type-erasure, wildcard, pecs, autoboxing, heap-pollution, jls]
---

자바·코틀린 20편 시리즈의 **자바 2편(J2)** 이다. 자바 타입 시스템을 네 덩어리로 나눠 본다.

1. **원시 타입 vs 참조 타입** — 그리고 둘을 잇는 박싱/언박싱
2. **제네릭** — 클래스·메서드 제네릭, 경계(bound), 타입 추론
3. **타입 소거** — 런타임에 무엇이 사라지고 무엇이 남는가
4. **와일드카드와 PECS** — 불변 제네릭을 유연하게 쓰는 법

짝이 되는 코틀린 글은 [K8 제네릭 변성: in/out, 스타 프로젝션, reified](https://myoungsoo7.github.io/2026/10/12/kotlin-generics-variance-in-out/) 이다. 자바의 "사용 지점 변성(와일드카드)" 과 코틀린의 "선언 지점 변성(in/out)" 을 비교해서 읽으면 둘 다 더 잘 보인다. 자바가 왜 소거를 택했는지는 [J1](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/) 의 하위 호환성 절에 있다.

---

## 1. 원시 타입과 참조 타입

### 1.1 무엇인가

| 구분 | 종류 | 값 | null | 제네릭 타입 인자 |
|---|---|---|---|---|
| 원시 타입 | `boolean byte short char int long float double` | 값 자체 | 불가 | 불가 (`List<int>` X) |
| 참조 타입 | 클래스·인터페이스·배열·타입 변수 | 객체에 대한 참조 | 가능 | 가능 |

원시 타입마다 래퍼 클래스(`Integer`, `Long` …)가 있고, J2SE 5.0 부터 컴파일러가 둘 사이를 자동 변환한다(오토박싱/언박싱, [J2SE 5.0 새 기능](https://docs.oracle.com/javase/1.5.0/docs/relnotes/features.html)).

### 1.2 코드 예제

```java
int a = 10;
Integer boxed = a;          // 박싱: 컴파일러가 Integer.valueOf(a) 로 바꾼다
int back = boxed;           // 언박싱: boxed.intValue()

List<Integer> nums = new ArrayList<>();
nums.add(1);                // 1 → Integer.valueOf(1)
int first = nums.get(0);    // intValue()
```

### 1.3 함정 1 — `==` 로 래퍼 비교

```java
Integer x = 127, y = 127;
System.out.println(x == y);     // true

Integer p = 128, q = 128;
System.out.println(p == q);     // 구현에 따라 false 일 수 있다
System.out.println(p.equals(q)); // true — 항상 이것을 쓴다
```

왜 127 은 같고 128 은 다를 수 있을까? JLS 는 상수 표현식의 박싱 결과가 `-128` 에서 `127` 사이의 정수(그리고 `true`/`false`, `'\u0000'`~`'\u007f'` 문자)이면 두 박싱 결과가 항상 `==` 라고 **보장**한다([JLS §5.1.7](https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html)). `Integer.valueOf(int)` Javadoc 도 "will always cache values in the range -128 to 127, inclusive, and may cache other values outside of this range" 라고 적는다([Integer.valueOf](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Integer.html#valueOf(int))). 즉 범위 밖은 **같을 수도, 다를 수도** 있다 — 테스트에서는 통과하고 운영에서 깨지는 전형적인 버그다.

**실무 사례**: JPA 엔티티의 `Long id` 를 `==` 로 비교하는 코드. 개발 DB 에서는 id 가 작아서 통과하고, 운영에서 id 가 128 을 넘는 순간 권한 검사가 실패한다.

```java
// 나쁜 예
if (order.getUserId() == currentUser.getId()) { ... }  // Long == Long

// 좋은 예
if (Objects.equals(order.getUserId(), currentUser.getId())) { ... }
```

### 1.4 함정 2 — null 언박싱

JLS 는 "If `r` is `null`, unboxing conversion throws a `NullPointerException`" 이라고 정의한다([JLS §5.1.8](https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html)).

```java
Map<String, Integer> stock = new HashMap<>();
int n = stock.get("apple");          // NPE: get 이 null 을 반환 → 언박싱

int safe = stock.getOrDefault("apple", 0);  // 좋은 예
```

삼항 연산자에서도 숨어 있다.

```java
Integer cached = null;
boolean useCache = true;
int v = useCache ? cached : 0;   // NPE — 결과 타입이 int 로 정해져 cached 가 언박싱된다
```

### 1.5 함정 3 — 래퍼 생성자

`new Integer(5)` 는 Java 9 부터 `@Deprecated(since="9", forRemoval=true)` 다. Javadoc 은 "The static factory `valueOf(int)` is generally a better choice" 라고 안내한다([Integer](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Integer.html)). 정적 분석기에 걸리면 바로 `valueOf` 나 오토박싱으로 바꾼다.

### 1.6 성능 관점의 사용사례

반복문 안의 박싱은 객체 할당을 만든다. 수치 집계는 원시 특화 스트림/컬렉션을 쓴다.

```java
// 나쁜 예: Long 누적 — 매 반복 박싱
Long sum = 0L;
for (long v : values) sum += v;

// 좋은 예
long total = 0;
for (long v : values) total += v;

// 스트림이라면 mapToLong / LongStream
long total2 = orders.stream().mapToLong(Order::amount).sum();
```

### 1.7 앞으로: 값 객체

"원시 타입처럼 효율적인 사용자 정의 타입" 은 Project Valhalla 의 주제다. [JEP 401 Value Objects (Preview)](https://openjdk.org/jeps/401) 는 이 글을 쓰는 시점(2026-10)에 상태가 "Integrated", 릴리스가 JDK 28 로 표시되어 있다. 즉 아직 **정식 기능도, 출시된 프리뷰도 아니다**. 실무 코드는 지금의 박싱 규칙을 기준으로 짠다.

---

## 2. 제네릭 기초

### 2.1 무엇인가

타입을 파라미터로 받는 클래스·인터페이스·메서드다. J2SE 5.0 문서는 제네릭이 "compile-time type safety to the Collections Framework and eliminates the drudgery of casting" 한다고 소개한다([J2SE 5.0](https://docs.oracle.com/javase/1.5.0/docs/relnotes/features.html)).

### 2.2 제네릭 클래스와 메서드

```java
// 제네릭 클래스
public final class Result<T> {
    private final T value;
    private final String error;

    private Result(T value, String error) { this.value = value; this.error = error; }

    public static <T> Result<T> ok(T value)        { return new Result<>(value, null); }
    public static <T> Result<T> fail(String error) { return new Result<>(null, error); }

    // 제네릭 메서드: 메서드 자체의 타입 파라미터 R
    public <R> Result<R> map(Function<? super T, ? extends R> f) {
        return error == null ? ok(f.apply(value)) : fail(error);
    }
}

Result<Integer> r = Result.ok("42").map(Integer::parseInt);
```

### 2.3 경계(bound)

```java
// 상한 경계: T 는 Comparable<T> 를 구현해야 한다
static <T extends Comparable<T>> T maxOf(List<T> xs) {
    T best = xs.get(0);
    for (T x : xs) if (x.compareTo(best) > 0) best = x;
    return best;
}

// 교차 경계(intersection): 여러 상한
static <T extends Number & Comparable<T>> T clampMax(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

### 2.4 다이아몬드와 타입 추론

```java
Map<String, List<Order>> byUser = new HashMap<>();   // Java 7 다이아몬드
var cache = new HashMap<String, Integer>();          // Java 10 var: 오른쪽에 타입을 써야 한다

// 익명 클래스 다이아몬드는 Java 9 부터
Comparator<String> c = new Comparator<>() {
    @Override public int compare(String a, String b) { return a.length() - b.length(); }
};
```

익명 클래스에 다이아몬드를 허용한 것은 [JEP 213](https://openjdk.org/jeps/213)(Java 9)이다. `var` 는 [JEP 286](https://openjdk.org/jeps/286)(Java 10)이고 지역 변수에만 쓸 수 있다.

**함정**: `var list = new ArrayList<>();` 는 `ArrayList<Object>` 로 추론된다. `var` 와 다이아몬드를 같이 쓰면 타입 정보가 사라진다.

### 2.5 raw 타입은 쓰지 않는다

```java
List raw = new ArrayList();      // raw 타입 — 컴파일러가 unchecked 경고
raw.add("a");
raw.add(1);                      // 아무 타입이나 들어간다
```

raw 타입은 제네릭 이전 코드와의 호환을 위해 남아 있는 것이다. 새 코드에서 쓸 이유는 없다. 타입을 모르면 `List<?>` 를 쓴다.

---

## 3. 타입 소거 (Type Erasure)

### 3.1 무엇인가

JLS 는 소거를 "a mapping from types (including parameterized types and type variables) to types that are never parameterized types or type variables" 로 정의한다([JLS §4.6](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)). 규칙은 다음과 같다.

| 원래 타입 | 소거 결과 |
|---|---|
| `List<String>` | `List` |
| `T` (경계 없음) | `Object` |
| `T extends Comparable<T>` | `Comparable` (가장 왼쪽 경계) |
| `T extends Number & Comparable<T>` | `Number` (가장 왼쪽 경계) |
| `T[]` | 소거된 `T` 의 배열 |

소거 이후 컴파일러는 필요한 곳에 캐스트를 끼워 넣는다. 그래서 런타임의 `ArrayList<String>` 과 `ArrayList<Integer>` 는 같은 클래스다.

```java
List<String> a = new ArrayList<>();
List<Integer> b = new ArrayList<>();
System.out.println(a.getClass() == b.getClass());  // true
```

### 3.2 소거 때문에 안 되는 것들

```java
class Box<T> {
    // T t = new T();                // 컴파일 에러: T 의 런타임 클래스를 모른다
    // T[] arr = new T[10];          // 컴파일 에러: 제네릭 배열 생성 불가
    // static T shared;              // 컴파일 에러: static 문맥에서 T 사용 불가

    boolean check(Object o) {
        // return o instanceof T;    // 컴파일 에러
        return o instanceof List<?>; // OK — 비한정 와일드카드는 실체화 가능
    }
}

// 오버로드 충돌: 소거 후 시그니처가 같다
// void handle(List<String> xs) {}
// void handle(List<Integer> xs) {}   // 컴파일 에러: same erasure
```

`List<?>` 가 되는 이유는 JLS 의 **실체화 가능 타입(reifiable type)** 정의에 있다. 비제네릭 타입, 모든 인자가 비한정 와일드카드인 파라미터화 타입(`List<?>`), raw 타입, 원시 타입, 요소가 실체화 가능한 배열 등이 여기에 속한다([JLS §4.7](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)). 런타임에 정보가 완전히 남는 타입만 `instanceof` 나 배열 생성에 안전하게 쓸 수 있다.

### 3.3 우회 패턴 1 — `Class<T>` 토큰

```java
public <T> T readJson(String json, Class<T> type) {
    return objectMapper.readValue(json, type);
}
User u = readJson(body, User.class);
```

단점: `List<User>` 같은 파라미터화 타입은 `Class` 로 표현할 수 없다(`List<User>.class` 는 문법 오류).

### 3.4 우회 패턴 2 — 슈퍼 타입 토큰

소거가 모든 것을 지우지는 않는다. 클래스·메서드·필드 **선언**에 쓰인 제네릭 정보는 클래스 파일의 `Signature` 속성에 남는다([JVMS §4.7.9](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html)). 익명 하위 클래스를 만들면 "부모 타입이 `X<List<User>>`" 라는 선언 정보가 남고, 리플렉션으로 읽을 수 있다.

스프링의 `ParameterizedTypeReference` 가 정확히 이 방식이다. Javadoc 은 "In order to capture the generic type and retain it at runtime, you need to create a subclass (ideally as anonymous inline class)" 라고 설명한다([ParameterizedTypeReference](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/core/ParameterizedTypeReference.html)).

```java
// 실무 사용사례: RestClient/RestTemplate 로 제네릭 응답 받기
List<User> users = restClient.get()
        .uri("/users")
        .retrieve()
        .body(new ParameterizedTypeReference<List<User>>() {});   // 끝의 {} 가 핵심
```

`{}` 를 빼먹으면 익명 하위 클래스가 아니게 되어 타입 정보가 남지 않는다(이 클래스는 abstract 라 애초에 컴파일이 안 된다). 스프링이 리플렉션으로 제네릭 정보를 읽는 다른 방식은 [J9](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 에서 다룬다.

### 3.5 힙 오염 (Heap Pollution)

JLS 의 정의:

> "It is possible that a variable of a parameterized type will refer to an object that is not of that parameterized type. This situation is known as heap pollution."
> — [JLS §4.12.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)

JLS 는 이어서 힙 오염은 unchecked 경고를 낳는 raw 타입 연산이 있었을 때만 생긴다고 적는다. 즉 **unchecked 경고를 무시한 곳이 범인**이다.

```java
List<String> strings = new ArrayList<>();
List raw = strings;           // raw 로 우회
raw.add(42);                  // unchecked 경고 — 여기서 오염
String s = strings.get(0);    // ClassCastException — 전혀 다른 줄에서 터진다
```

예외가 오염 지점이 아니라 **꺼내는 지점**에서 난다는 것이 디버깅을 어렵게 만든다.

### 3.6 제네릭 가변 인자와 `@SafeVarargs`

가변 인자는 배열로 구현되는데, 제네릭 배열은 실체화가 안 되므로 `T...` 는 경고를 만든다.

```java
@SafeVarargs
static <T> List<T> listOf(T... items) {      // static 이라 @SafeVarargs 가능
    return List.of(items);
}
```

JLS 는 "a variable arity method declaration that is neither `static` nor `final` nor `private`" 에 `@SafeVarargs` 를 붙이면 컴파일 에러라고 규정한다([JLS §9.6.4.7](https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html)). `private` 인스턴스 메서드 허용은 Java 9 에서 추가됐다([JEP 213](https://openjdk.org/jeps/213)). `@SafeVarargs` 자체는 Java 7 부터다([SafeVarargs](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/SafeVarargs.html)).

**함정**: `@SafeVarargs` 는 "이 메서드가 가변 인자 배열에 다른 타입을 넣거나 배열을 바깥으로 유출하지 않는다" 는 **개발자의 약속**이다. 컴파일러가 검증하지 않는다. 배열을 그대로 반환하거나 필드에 저장하면 약속 위반이다.

---

## 4. 변성 — 제네릭은 왜 불변인가

### 4.1 무엇인가

JLS 하위 타입 규칙상 `Integer` 가 `Number` 의 하위 타입이어도 `List<Integer>` 는 `List<Number>` 의 하위 타입이 **아니다**([JLS §4.10.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)). 이것을 **불변(invariant)** 이라고 한다.

```java
List<Integer> ints = new ArrayList<>(List.of(1, 2));
// List<Number> nums = ints;    // 컴파일 에러
// 만약 허용되면:
// nums.add(3.14);              // Integer 리스트에 Double 이 들어간다
```

배열은 반대로 공변이고, 그 대가가 런타임 `ArrayStoreException` 이다([J1 §6.3](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/)). 제네릭은 그 실수를 반복하지 않고, 대신 **사용하는 쪽에서** 변성을 선언하게 했다. 그것이 와일드카드다.

### 4.2 세 가지 와일드카드

| 표기 | 의미 | 읽기 | 쓰기 |
|---|---|---|---|
| `List<?>` | 어떤 타입의 리스트 | `Object` 로만 | `null` 만 |
| `List<? extends Number>` | `Number` 이거나 그 하위 타입의 리스트 (공변) | `Number` 로 읽힘 | `null` 만 |
| `List<? super Integer>` | `Integer` 이거나 그 상위 타입의 리스트 (반공변) | `Object` 로만 | `Integer` 쓰기 가능 |

```java
double sum(List<? extends Number> xs) {        // List<Integer>, List<Double> 모두 받는다
    double s = 0;
    for (Number n : xs) s += n.doubleValue();  // 읽기 OK
    // xs.add(1);                              // 컴파일 에러 — 실제 타입이 List<Double> 일 수도
    return s;
}

void fill(List<? super Integer> out) {         // List<Integer>, List<Number>, List<Object>
    out.add(1);                                // 쓰기 OK
    Object o = out.get(0);                     // 읽으면 Object
}
```

### 4.3 PECS — Producer Extends, Consumer Super

**값을 꺼내 주는(produce) 파라미터는 `extends`, 값을 받아 먹는(consume) 파라미터는 `super`.** JDK 표준 API 시그니처가 이 규칙의 교과서다([Collections](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collections.html), [Comparator](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Comparator.html)).

```java
// Collections
static <T> void copy(List<? super T> dest, List<? extends T> src)
//                   ^ consumer: 받아 씀      ^ producer: 꺼내 줌

static <T> boolean addAll(Collection<? super T> c, T... elements)

static <T extends Object & Comparable<? super T>> T max(Collection<? extends T> coll)

// Comparator
static <T, U extends Comparable<? super U>> Comparator<T> comparing(
        Function<? super T, ? extends U> keyExtractor)
//               ^ T 를 소비          ^ U 를 생산
```

`Function<? super T, ? extends R>` 은 함수형 인터페이스 파라미터의 표준 형태다. 입력은 소비(`super`), 출력은 생산(`extends`)이다.

### 4.4 실무 사용사례: 도메인 서비스 API

```java
public class NotificationService {

    // 나쁜 예: List<Notification> 만 받는다 → List<EmailNotification> 을 못 넘긴다
    public void sendAll(List<Notification> items) { ... }

    // 좋은 예: producer → extends
    public void sendAll(Collection<? extends Notification> items) {
        for (Notification n : items) send(n);
    }

    // 결과를 호출자가 준 컨테이너에 담아 준다: consumer → super
    public void collectFailures(Collection<? super FailedNotification> sink) {
        sink.add(new FailedNotification("..."));
    }
}
```

```java
// 정렬 기준을 받는 API: Comparator 는 T 를 소비 → super
public <T> List<T> topN(Collection<? extends T> src, Comparator<? super T> cmp, int n) {
    return src.stream().sorted(cmp).limit(n).collect(Collectors.toList());
}

// Comparator<Object>, Comparator<Notification> 모두 EmailNotification 정렬에 쓸 수 있다
```

### 4.5 `Comparable<? super T>` 는 왜 필요한가

```java
class Money implements Comparable<Money> { ... }
class Krw extends Money { ... }   // Comparable<Money> 를 상속 — Comparable<Krw> 아님

static <T extends Comparable<T>> T max1(List<T> xs) { ... }
static <T extends Comparable<? super T>> T max2(List<T> xs) { ... }

List<Krw> list = ...;
// max1(list);   // 컴파일 에러: Krw 는 Comparable<Krw> 가 아니다
max2(list);      // OK: Krw 는 Comparable<Money>, Money 는 Krw 의 상위 타입
```

상속 계층에서 비교 기준을 부모에 둘 때 반드시 `? super T` 가 필요하다. `Collections.max` 시그니처가 그렇게 생긴 이유다.

### 4.6 함정과 가이드라인

1. **반환 타입에 와일드카드를 쓰지 않는다.** `List<? extends Foo> find()` 는 호출자를 불편하게 만들 뿐이다. 와일드카드는 **파라미터**에만.
2. **읽고 쓰기를 둘 다 하면 와일드카드 없이 `T`** 를 쓴다.
3. **`?` 로 받은 리스트를 수정하고 싶으면 캡처 헬퍼**를 쓴다.

```java
static void swapFirstLast(List<?> list) { swapHelper(list); }

private static <T> void swapHelper(List<T> list) {   // 와일드카드 캡처
    T first = list.get(0);
    list.set(0, list.get(list.size() - 1));
    list.set(list.size() - 1, first);
}
```

4. **`Optional<? extends T>`, `Supplier<? extends T>`** 처럼 함수형 파라미터는 PECS 를 기계적으로 적용하면 된다.

---

## 5. 자바 vs 코틀린 변성 한눈에

| 개념 | 자바 | 코틀린 |
|---|---|---|
| 공변 (읽기 전용) | `List<? extends T>` (사용 지점) | `out T` (선언 지점), `List<out T>` (사용 지점) |
| 반공변 (쓰기 전용) | `Comparator<? super T>` | `in T`, `Comparable<in T>` |
| 미지 타입 | `List<?>` | `List<*>` (스타 프로젝션) |
| 런타임 타입 인자 | 소거 — `Class<T>` / 슈퍼 타입 토큰 | 소거 — 단, `inline` + `reified` 로 우회 |
| 원시 타입 | `int` vs `Integer` 명시 | `Int` 하나, 컴파일러가 원시/박싱 선택 |

자바는 `List` 를 선언할 때 변성을 정하지 못하기 때문에 **API 를 쓰는 곳마다** 와일드카드를 반복해야 한다. 코틀린은 `interface List<out E>` 처럼 선언 시점에 정해두어 이 반복을 없앴다. 상세 비교는 [K8](https://myoungsoo7.github.io/2026/10/12/kotlin-generics-variance-in-out/).

---

## 6. 정리 체크리스트

- 래퍼 비교는 `equals`/`Objects.equals`. `==` 는 -128~127 에서만 우연히 맞는다.
- `Map.get` 결과를 원시 타입에 바로 대입하지 않는다(null 언박싱 NPE).
- raw 타입 금지. 모르면 `<?>`.
- unchecked 경고는 무시하지 말고 `@SuppressWarnings("unchecked")` 를 **가장 좁은 범위**에, 이유 주석과 함께.
- 제네릭 응답 역직렬화는 `ParameterizedTypeReference` / `TypeReference` 처럼 익명 하위 클래스로.
- 파라미터는 PECS: 꺼내면 `extends`, 넣으면 `super`, 둘 다면 `T`. 반환 타입엔 와일드카드 금지.

---

## References

- JLS SE 21, Chapter 4 Types, Values, and Variables (§4.6, §4.7, §4.10.2, §4.12.2) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html
- JLS SE 21, Chapter 5 Conversions and Contexts (§5.1.7, §5.1.8) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html
- JLS SE 21, Chapter 9 Interfaces (§9.6.4.7 @SafeVarargs) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html
- JVMS SE 21, Chapter 4 (§4.7.9 Signature attribute) — https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html
- J2SE 5.0 New Features and Enhancements — https://docs.oracle.com/javase/1.5.0/docs/relnotes/features.html
- `Integer` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Integer.html
- `Collections` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collections.html
- `Comparator` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Comparator.html
- `SafeVarargs` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/SafeVarargs.html
- Spring Framework `ParameterizedTypeReference` Javadoc — https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/core/ParameterizedTypeReference.html
- JEP 213: Milling Project Coin — https://openjdk.org/jeps/213
- JEP 286: Local-Variable Type Inference — https://openjdk.org/jeps/286
- JEP 401: Value Objects (Preview) — https://openjdk.org/jeps/401

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/) ← 지금 글
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
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
