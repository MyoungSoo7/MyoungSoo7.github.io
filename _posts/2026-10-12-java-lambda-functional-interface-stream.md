---
layout: post
title: "자바 람다·메서드 참조·함수형 인터페이스·Stream API — 사용사례와 함정"
date: 2026-10-12 00:14:42 +0900
categories: [java]
tags: [java, lambda, method-reference, functional-interface, stream, collectors, gatherers, sequenced-collections]
---

자바·코틀린 20편 시리즈의 **자바 4편(J4)** 이다. Java 8 에 함께 들어온 네 가지를 한 묶음으로 본다.

1. **람다 식** — 코드 블록을 값으로 전달
2. **메서드 참조** — 이미 있는 메서드를 람다처럼 전달
3. **함수형 인터페이스** — 람다의 "타입"
4. **Stream API** — 람다를 조합하는 컬렉션 처리 파이프라인

그리고 Java 9 이후 Stream 에 추가된 것(`takeWhile`, `toList`, `mapMulti`, Gatherers)과 운영에서 자주 터지는 함정까지 정리한다. 코틀린 쪽 대응은 [K4 함수: 고차 함수·inline](https://myoungsoo7.github.io/2026/10/12/kotlin-functions-extension-inline-reified/) 과 [K6 컬렉션과 Sequence](https://myoungsoo7.github.io/2026/10/12/kotlin-collections-and-sequences/) 에 있다. 람다가 바이트코드로 어떻게 컴파일되는지(`invokedynamic`)는 [J1 §3.2](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/) 에서 다뤘다.

---

## 1. 람다 식

### 1.1 무엇인가

Java 8 의 [JEP 126](https://openjdk.org/jeps/126) 으로 들어왔다. 람다는 **함수형 인터페이스의 인스턴스를 만드는 식**이다. 람다 자체에는 타입이 없고, 대입되는 문맥(목표 타입)이 타입을 정한다.

```java
// 형태
Runnable r1 = () -> System.out.println("run");               // 파라미터 없음
Function<String, Integer> len = s -> s.length();              // 파라미터 1개, 괄호 생략
BinaryOperator<Integer> add = (a, b) -> a + b;                // 2개
Comparator<String> cmp = (String a, String b) -> {            // 명시적 타입 + 블록
    int c = Integer.compare(a.length(), b.length());
    return c != 0 ? c : a.compareTo(b);
};
BiFunction<String, String, Boolean> eq = (var a, var b) -> a.equals(b);  // Java 11 var
```

람다 파라미터에 `var` 를 쓰는 문법은 Java 11 의 [JEP 323](https://openjdk.org/jeps/323) 이다. 주 용도는 파라미터에 애노테이션을 붙이는 것이다(`(@NonNull var x) -> ...`). 쓰지 않는 파라미터는 Java 22 부터 `_` 로 이름 없이 둘 수 있다([JEP 456](https://openjdk.org/jeps/456)).

```java
map.forEach((_, v) -> total.add(v));                          // Java 22+
```

### 1.2 캡처 규칙 — effectively final

JLS: "Any local variable, formal parameter, or exception parameter used but not declared in a lambda body must either be final or effectively final, or a compile-time error occurs."([JLS §15.27.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.27.2))

```java
int count = 0;
list.forEach(x -> count++);          // 컴파일 에러: count 가 effectively final 이 아님

// 나쁜 우회: 배열/AtomicInteger 로 "상태 몰래 바꾸기"
int[] box = {0};
list.forEach(x -> box[0]++);         // 컴파일은 되지만 병렬 스트림에서 레이스

// 좋은 예: 상태를 바꾸지 말고 값을 계산한다
long count2 = list.stream().filter(this::isValid).count();
```

**왜 이런 제약인가.** 람다는 만들어진 메서드보다 오래 살 수 있다(다른 스레드에 넘겨지거나 필드에 저장됨). 지역 변수는 스택에 있고 메서드가 끝나면 사라지므로, 람다는 **값을 복사해서** 가져간다. 복사본과 원본이 달라지는 혼란을 막으려면 원본이 바뀌지 않아야 한다.

### 1.3 `this` 는 바깥 객체다

JLS: "The value denoted by `this` in a lambda body is the same as the value denoted by `this` in the surrounding context."([JLS §15.27.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.27.2))

```java
public class OrderService {
    private final String name = "order";

    void demo() {
        Runnable lambda = () -> System.out.println(this.name);   // OrderService.this
        Runnable anon = new Runnable() {
            @Override public void run() {
                System.out.println(this);                         // 익명 클래스 인스턴스
            }
        };
    }
}
```

익명 클래스를 람다로 기계적으로 바꿀 때 `this`, `toString()` 호출의 의미가 바뀔 수 있다는 점을 기억한다.

### 1.4 실무 사용사례

```java
// 1) 전략 주입: 할인 정책을 람다로
public long checkout(Cart cart, ToLongFunction<Cart> discountPolicy) {
    return cart.total() - discountPolicy.applyAsLong(cart);
}
checkout(cart, c -> c.total() >= 50_000 ? 3_000 : 0);

// 2) 지연 계산: 로그 메시지는 필요할 때만 만든다
log.debug("payload={}", () -> expensiveToJson(payload));   // Supplier 를 받는 API 일 때

// 3) 트랜잭션 템플릿 콜백 (스프링)
Long id = transactionTemplate.execute(status -> orderRepository.save(order).getId());

// 4) 정렬 기준
orders.sort(Comparator.comparing(Order::createdAt).reversed());
```

### 1.5 함정

- **람다 몸체가 5줄을 넘으면 메서드로 뺀다.** 스택트레이스에 `lambda$process$3` 같은 이름만 남아 디버깅이 어렵다. 이름 있는 private 메서드 + 메서드 참조가 읽기에도, 추적에도 낫다.
- **checked 예외를 못 던진다.** `java.util.function` 의 인터페이스들은 `throws` 절이 없다. 아래 §3.4 참고.

---

## 2. 메서드 참조

### 2.1 무엇인가

이미 이름이 있는 메서드를 람다 대신 넘기는 축약형이다. JLS 의 메서드 참조 식 형태([JLS §15.13](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html)):

| 종류 | 문법 | 같은 뜻의 람다 |
|---|---|---|
| 정적 메서드 | `Integer::parseInt` | `s -> Integer.parseInt(s)` |
| 특정 객체의 인스턴스 메서드 | `System.out::println`, `this::isValid` | `x -> System.out.println(x)` |
| 임의 객체의 인스턴스 메서드 | `String::length` | `s -> s.length()` |
| 상위 클래스 메서드 | `super::toString` | `() -> super.toString()` |
| 생성자 | `ArrayList::new` | `() -> new ArrayList<>()` |
| 배열 생성자 | `int[]::new` | `n -> new int[n]` |

### 2.2 코드 예제

```java
List<Integer> ids = rawIds.stream().map(Integer::parseInt).toList();                // 정적
List<String> names = users.stream().map(User::name).toList();             // 임의 객체
users.forEach(notifier::send);                                            // 특정 객체
Map<String, List<User>> byTeam = users.stream()
        .collect(Collectors.groupingBy(User::team, TreeMap::new, Collectors.toList())); // 생성자
String[] arr = names.stream().toArray(String[]::new);                     // 배열 생성자
```

### 2.3 함정 1 — 수신 객체 평가 시점

```java
Supplier<String> s1 = config.current()::name;      // config.current() 는 "지금" 한 번 평가된다
Supplier<String> s2 = () -> config.current().name(); // 호출할 때마다 평가된다
```

`expr::method` 의 `expr` 은 메서드 참조가 **만들어질 때** 평가된다. `expr` 이 null 이면 그 시점에 NPE 가 난다. 설정 리로드처럼 "호출 시점의 값" 이 필요하면 람다를 쓴다.

### 2.4 함정 2 — 오버로드 모호성

```java
// Integer::toString 은 static toString(int) 와 인스턴스 toString() 둘 다 후보 → 모호
// list.stream().map(Integer::toString);         // 컴파일 에러 (ambiguous)
list.stream().map(String::valueOf);              // 해결
list.stream().map(i -> i.toString());            // 또는 람다
```

---

## 3. 함수형 인터페이스

### 3.1 무엇인가

JLS: 함수형 인터페이스는 (`Object` 의 public 메서드를 제외하고) **추상 메서드가 정확히 하나**인 인터페이스다([JLS §9.8](https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html)). default·static 메서드는 몇 개든 상관없다. `@FunctionalInterface`(Java 8)는 **필수가 아니며**, 붙이면 조건을 어길 때 컴파일 에러를 내주는 확인용 표시다([FunctionalInterface](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/FunctionalInterface.html)).

그래서 Java 8 이전에 만들어진 `Runnable`, `Callable`, `Comparator` 도 그대로 람다의 목표 타입이 된다.

### 3.2 `java.util.function` 핵심 표

`java.util.function` 패키지는 Java 8 부터다([Function](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/function/Function.html)).

| 인터페이스 | 시그니처 | 쓰임 |
|---|---|---|
| `Supplier<T>` | `() -> T` | 지연 생성, 기본값 |
| `Consumer<T>` | `T -> void` | 부수효과(로그, 전송) |
| `BiConsumer<T,U>` | `(T,U) -> void` | `Map.forEach` |
| `Function<T,R>` | `T -> R` | 변환 |
| `BiFunction<T,U,R>` | `(T,U) -> R` | 두 값 결합 |
| `UnaryOperator<T>` | `T -> T` | 같은 타입 변환 (`List.replaceAll`) |
| `BinaryOperator<T>` | `(T,T) -> T` | 리듀스 |
| `Predicate<T>` | `T -> boolean` | 필터 |
| `IntFunction`, `ToLongFunction`, `IntPredicate` … | 원시 특화 | 박싱 회피 |

### 3.3 조합 메서드

```java
Predicate<Order> paid      = Order::isPaid;
Predicate<Order> big       = o -> o.amount() >= 100_000;
Predicate<Order> target    = paid.and(big.negate());          // 결제됨 AND 소액
Predicate<String> notBlank = Predicate.not(String::isBlank);  // Predicate.not, String.isBlank 은 Java 11

Function<String, String> trim  = String::trim;
Function<String, String> lower = String::toLowerCase;
Function<String, String> normalize = trim.andThen(lower);    // trim → lower

Comparator<Order> byAmountDescThenId =
        Comparator.comparingLong(Order::amount).reversed()
                  .thenComparing(Order::id);
```

### 3.4 checked 예외와 함수형 인터페이스

```java
// Files.readString 은 IOException(checked) 을 던진다
// paths.stream().map(Files::readString)   // 컴파일 에러: Function.apply 는 throws 가 없다
```

선택지:

```java
// (1) 람다 안에서 감싸서 unchecked 로 — UncheckedIOException 은 Java 8 부터
List<String> contents = paths.stream()
        .map(p -> {
            try { return Files.readString(p); }
            catch (IOException e) { throw new UncheckedIOException(e); }
        })
        .toList();

// (2) 자체 함수형 인터페이스 정의
@FunctionalInterface
interface IoFunction<T, R> { R apply(T t) throws IOException; }

static <T, R> Function<T, R> unchecked(IoFunction<T, R> f) {
    return t -> {
        try { return f.apply(t); }
        catch (IOException e) { throw new UncheckedIOException(e); }
    };
}
paths.stream().map(unchecked(Files::readString)).toList();
```

`UncheckedIOException` 은 Java 8 에 추가된 표준 예외다([UncheckedIOException](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/UncheckedIOException.html)). checked/unchecked 설계 철학 자체는 [J5](https://myoungsoo7.github.io/2026/10/12/java-null-optional-exceptions/) 에서 다룬다.

**함정**: "sneaky throw" 처럼 제네릭 트릭으로 checked 예외를 컴파일러 몰래 던지는 기법은 호출자가 catch 할 수 없게 만든다(컴파일러가 해당 checked 예외를 catch 블록에 허용하지 않음). 팀 코드에서는 피한다.

---

## 4. Stream API 기본

### 4.1 무엇인가

`java.util.stream.Stream` 은 Java 8 부터다([Stream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html)). **소스 → 0개 이상의 중간 연산 → 1개의 최종 연산** 파이프라인이다.

Javadoc 의 세 가지 핵심 성질:

1. **지연(lazy)** — "computation on the source data is only performed when the terminal operation is initiated, and source elements are consumed only as needed."
2. **일회용** — "A stream should be operated on … only once." 재사용을 감지하면 `IllegalStateException` 을 던질 수 있다.
3. **행위 파라미터 규칙** — 람다는 **non-interfering**(소스를 수정하지 않음)이어야 하고, 대부분의 경우 **stateless** 여야 한다.

```java
Stream<String> s = names.stream().filter(n -> n.startsWith("k"));
s.count();
s.count();                 // IllegalStateException: stream has already been operated upon or closed
```

### 4.2 대표 파이프라인

```java
record Order(String id, String userId, String status, long amount, LocalDate date) {}

// 1) 필터 + 변환 + 수집
List<String> paidIds = orders.stream()
        .filter(o -> o.status().equals("PAID"))
        .map(Order::id)
        .toList();

// 2) 집계
long revenue = orders.stream().mapToLong(Order::amount).sum();
LongSummaryStatistics stats = orders.stream().mapToLong(Order::amount).summaryStatistics();

// 3) 그룹핑
Map<String, Long> revenueByUser = orders.stream()
        .collect(Collectors.groupingBy(Order::userId, Collectors.summingLong(Order::amount)));

Map<LocalDate, List<String>> idsByDate = orders.stream()
        .collect(Collectors.groupingBy(Order::date, TreeMap::new,
                 Collectors.mapping(Order::id, Collectors.toList())));

// 4) 분할
Map<Boolean, List<Order>> bigOrNot = orders.stream()
        .collect(Collectors.partitioningBy(o -> o.amount() >= 100_000));

// 5) 키-값 맵 (중복 키 처리 필수)
Map<String, Order> latestByUser = orders.stream()
        .collect(Collectors.toMap(Order::userId, Function.identity(),
                 (a, b) -> a.date().isAfter(b.date()) ? a : b));

// 6) 평탄화
List<String> allTags = posts.stream().flatMap(p -> p.tags().stream()).distinct().toList();
```

### 4.3 중간 연산 분류

| 분류 | 연산 | 성질 |
|---|---|---|
| 상태 없음 | `filter`, `map`, `flatMap`, `peek`, `mapMulti` | 원소 하나씩 처리 |
| 상태 있음 | `sorted`, `distinct` | 전체(또는 상당 부분)를 봐야 함 → 무한 스트림에 위험 |
| 단락(short-circuit) | `limit`, `takeWhile` | 일찍 끝낼 수 있음 |

최종 연산: `forEach`, `collect`, `reduce`, `toList`, `count`, `min/max`, `anyMatch/allMatch/noneMatch`, `findFirst/findAny`.

---

## 5. Java 9 이후 Stream 의 변화

| 기능 | 버전 | 출처 |
|---|---|---|
| `takeWhile`, `dropWhile`, `iterate(seed, hasNext, next)`, `ofNullable` | 9 | [Stream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html) |
| `Collectors.filtering`, `flatMapping` | 9 | [Collectors](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html) |
| `Collectors.toUnmodifiableList/Set/Map` | 10 | 〃 |
| `Collectors.teeing` | 12 | 〃 |
| `Stream.toList()`, `mapMulti` | 16 | [Stream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html) |
| Sequenced Collections (`reversed`, `getFirst` …) | 21 | [JEP 431](https://openjdk.org/jeps/431) |
| Stream Gatherers (`Stream.gather`) | 24 | [JEP 485](https://openjdk.org/jeps/485) |

### 5.1 `takeWhile` / `dropWhile`

```java
// 정렬된 로그에서 특정 시각 이전까지만
List<Log> before = sortedLogs.stream()
        .takeWhile(l -> l.time().isBefore(cutoff))
        .toList();
```

**함정**: `filter` 와 달리 조건이 처음 거짓이 되는 순간 **멈춘다**. 정렬되지 않은 소스에 쓰면 결과가 틀린다.

### 5.2 `Stream.toList()` vs `Collectors.toList()`

| | `stream.toList()` (16) | `collect(Collectors.toList())` |
|---|---|---|
| 수정 가능성 | **수정 불가** — 변경 시 `UnsupportedOperationException` | 보장 없음 (현재 구현은 보통 `ArrayList`) |
| null 요소 | 허용 | 허용 |

Javadoc: `toList()` 의 결과는 "unmodifiable; calls to any mutator method will always cause `UnsupportedOperationException`". 반면 `Collectors.toList()` 는 "There are no guarantees on the type, mutability, serializability, or thread-safety of the `List` returned"([Collectors](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html)).

```java
List<String> a = stream.toList();
a.add("x");                          // UnsupportedOperationException

// 수정 가능한 리스트가 필요하면 명시한다
List<String> b = stream.collect(Collectors.toCollection(ArrayList::new));
```

**실무 함정**: `collect(Collectors.toList())` 를 일괄 치환으로 `.toList()` 로 바꿨다가, 뒤에서 `.add()`/`.sort()` 하던 코드가 운영에서 터지는 경우가 있다. 치환 전 사용처를 확인한다.

### 5.3 `Collectors.teeing` — 한 번 순회로 두 집계

```java
record MinMax(long min, long max) {}

MinMax mm = orders.stream().collect(Collectors.teeing(
        Collectors.minBy(Comparator.comparingLong(Order::amount)),
        Collectors.maxBy(Comparator.comparingLong(Order::amount)),
        (min, max) -> new MinMax(min.map(Order::amount).orElse(0L),
                                 max.map(Order::amount).orElse(0L))));
```

### 5.4 `mapMulti` — 0~N 개로 펼치되 중간 스트림을 만들지 않음

```java
// 주문 → 주문 라인들. 조건에 맞는 라인만 내보냄
List<Line> lines = orders.stream()
        .<Line>mapMulti((order, sink) -> {
            for (Line l : order.lines()) {
                if (l.qty() > 0) sink.accept(l);
            }
        })
        .toList();
```

`flatMap` 은 원소마다 `Stream` 객체를 만들어 반환해야 하지만, `mapMulti` 는 `Consumer` 로 바로 밀어 넣는다. 타입 추론이 잘 안 되므로 `<Line>` 처럼 타입 인자를 명시하는 경우가 많다.

### 5.5 Sequenced Collections (Java 21)

[JEP 431](https://openjdk.org/jeps/431) 은 순서가 정의된 컬렉션을 위한 `SequencedCollection`, `SequencedSet`, `SequencedMap` 인터페이스를 추가했다. `List`, `Deque`, `LinkedHashSet`, `LinkedHashMap`, `SortedMap` 등이 여기에 맞춰졌다.

```java
List<Order> recent = orderList.reversed();     // 역순 "뷰" — 복사 아님
Order first = orderList.getFirst();            // list.get(0) 대체
Order last  = orderList.getLast();             // list.get(list.size() - 1) 대체

LinkedHashMap<String, Integer> lru = new LinkedHashMap<>();
lru.putFirst("hot", 1);                        // SequencedMap
var oldest = lru.firstEntry();
```

**함정**: `reversed()` 는 **뷰**다. 원본이 바뀌면 같이 바뀐다. 그리고 `--release 17` 로 빌드하는 라이브러리에서는 쓸 수 없다([J1 §2.4](https://myoungsoo7.github.io/2026/10/12/java-essence-jvm-bytecode-compatibility/)).

### 5.6 Stream Gatherers (Java 24)

[JEP 485](https://openjdk.org/jeps/485) 는 JDK 22([JEP 461](https://openjdk.org/jeps/461)), 23([JEP 473](https://openjdk.org/jeps/473)) 의 프리뷰를 거쳐 JDK 24 에 정식화됐다. `collect` 가 최종 연산의 확장점이듯, `gather` 는 **중간 연산의 확장점**이다. 내장 Gatherer 는 `java.util.stream.Gatherers` 의 `fold`, `mapConcurrent`, `scan`, `windowFixed`, `windowSliding` 다섯 개다.

```java
// 고정 크기 배치: 1000건씩 끊어서 벌크 insert
orders.stream()
      .gather(Gatherers.windowFixed(1000))
      .forEach(batch -> repository.bulkInsert(batch));

// 슬라이딩 윈도우: 3일 이동 평균
List<Double> ma3 = dailyRevenue.stream()
        .gather(Gatherers.windowSliding(3))
        .map(w -> w.stream().mapToLong(Long::longValue).average().orElse(0))
        .toList();

// 누적 합(scan)
List<Long> running = amounts.stream()
        .gather(Gatherers.scan(() -> 0L, Long::sum))
        .toList();
```

**주의**: JDK 24 이상(LTS 기준으로는 25)에서만 쓸 수 있다. JDK 21 서비스라면 `windowFixed` 는 직접 구현하거나 리스트를 잘라 쓴다.

---

## 6. Stream 함정 모음

### 6.1 소스를 수정하지 않는다 (non-interference)

```java
List<String> names = new ArrayList<>(List.of("a", "b", "c"));
names.stream().forEach(n -> { if (n.equals("b")) names.remove(n); });  // 정의되지 않은 동작
names.removeIf(n -> n.equals("b"));                                     // 이렇게 한다
```

### 6.2 상태 있는 람다 금지

```java
// 나쁜 예: 외부 리스트에 add — 병렬이면 깨진다
List<String> out = new ArrayList<>();
items.parallelStream().map(this::convert).forEach(out::add);

// 좋은 예
List<String> out2 = items.parallelStream().map(this::convert).toList();
```

### 6.3 `peek` 는 디버깅용이다

Javadoc 의 설명대로 행위 파라미터의 부수효과는 "may not always be executed and should not be relied upon"([Stream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html)). 구현은 결과에 영향이 없다면 파이프라인 일부를 건너뛸 수 있다. `peek` 안에서 엔티티를 수정하거나 이벤트를 발행하지 않는다.

```java
// 나쁜 예
long n = orders.stream().peek(o -> o.markExported()).count();   // markExported 가 호출 안 될 수 있다
```

### 6.4 `toMap` 의 중복 키와 null 값

`Collectors.toMap` 은 중복 키를 만나면 `IllegalStateException` 을 던진다([Collectors](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html)). 운영 데이터에는 "절대 없을 거라던" 중복이 있다. 병합 함수를 항상 준다. 또 `toUnmodifiableMap` 은 null 키·값을 허용하지 않아 `NullPointerException` 을 던진다.

```java
Map<String, String> emailById = users.stream()
        .collect(Collectors.toMap(User::id, User::email, (a, b) -> a));   // 병합 함수
```

### 6.5 `groupingBy` 결과 타입을 가정하지 않는다

Javadoc: "There are no guarantees on the type, mutability, serializability, or thread-safety of the `Map` or `List` objects returned." 정렬이 필요하면 `TreeMap::new`, 수정이 필요하면 맵 팩토리를 명시한다(§4.2 의 3번 예).

### 6.6 I/O 스트림은 닫는다

`Files.lines` 는 열린 파일을 붙잡고 있다. Javadoc 의 API Note: "This method must be used within a try-with-resources statement or similar control structure to ensure that the stream's open file is closed promptly"([Files](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html)).

```java
try (Stream<String> lines = Files.lines(path)) {
    long errors = lines.filter(l -> l.contains("ERROR")).count();
}
```

스프링 데이터 JPA 의 `Stream<T>` 반환 쿼리도 마찬가지다. 레퍼런스는 "Streams must be closed after usage to avoid resource leaks" 라고 하고 try-with-resources 예제를 든다([Spring Data JPA Query Methods](https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html)). try-with-resources 는 [J5](https://myoungsoo7.github.io/2026/10/12/java-null-optional-exceptions/).

### 6.7 `parallelStream()` 을 기본으로 쓰지 않는다

- Stream API 에는 병렬 실행에 쓸 스레드 풀(Executor)을 넘기는 인자가 없다. 웹 서버에서 요청마다 병렬 스트림을 돌리면 그 실행 자원을 애플리케이션이 통제하기 어렵다.
- 원소 처리 안에 I/O(DB, HTTP)가 있으면 병렬 스트림이 아니라 동시성 도구(가상 스레드, `CompletableFuture`)의 영역이다 — [J7](https://myoungsoo7.github.io/2026/10/12/java-concurrency-thread-to-virtual-threads/).
- `forEach` 는 병렬에서 순서를 보장하지 않는다. 순서가 필요하면 `forEachOrdered`.

### 6.8 Stream 을 반환하거나 필드에 저장하지 않는다

일회용이므로 두 번 소비되는 순간 터진다. 메서드 간에는 `List`/`Collection` 을 넘긴다. 예외: 대용량을 지연 처리해야 하는 경우 — 그때는 "한 번만, 반드시 닫아서" 를 API 문서에 적는다.

### 6.9 루프가 더 나은 경우

- 중간에 `break`/`continue`/`return` 이 여러 번 필요한 로직
- checked 예외를 던지는 호출이 많은 로직
- 인덱스가 의미 있는 처리 (`i` 와 `i+1` 비교)

스트림은 "무엇을" 표현하는 데 강하고, 복잡한 제어 흐름에는 약하다. 가독성이 기준이다.

---

## 7. 자바 Stream vs 코틀린 컬렉션 — 짧은 비교

| | 자바 Stream | 코틀린 컬렉션 연산 / Sequence |
|---|---|---|
| 평가 | 항상 지연 | 컬렉션 연산은 즉시, `asSequence()` 는 지연 |
| 재사용 | 일회용 | `List` 는 재사용 가능 |
| null | 원소로 허용, 타입에 표현 안 됨 | `List<String?>` 처럼 타입에 표현 |
| 원시 특화 | `IntStream` 등 별도 타입 | `sumOf` 등 함수 단위 |
| checked 예외 | 함수형 인터페이스가 막음 | 코틀린엔 checked 예외 개념 없음 |
| 확장 | Collector / Gatherer 구현 | 확장 함수 |

코틀린 쪽 상세와 공식 문서 근거는 [K6](https://myoungsoo7.github.io/2026/10/12/kotlin-collections-and-sequences/) 에 있다.

---

## References

- JEP 126: Lambda Expressions & Virtual Extension Methods — https://openjdk.org/jeps/126
- JEP 323: Local-Variable Syntax for Lambda Parameters — https://openjdk.org/jeps/323
- JEP 431: Sequenced Collections — https://openjdk.org/jeps/431
- JEP 456: Unnamed Variables & Patterns — https://openjdk.org/jeps/456
- JEP 461 / 473 / 485: Stream Gatherers — https://openjdk.org/jeps/461 , https://openjdk.org/jeps/473 , https://openjdk.org/jeps/485
- JLS SE 21, Chapter 9 (§9.8 Functional Interfaces) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-9.html
- JLS SE 21, Chapter 15 (§15.13 Method Reference Expressions, §15.27 Lambda Expressions) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html
- `java.util.stream.Stream` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html
- `java.util.stream.Collectors` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html
- `java.util.function.Function` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/function/Function.html
- `java.lang.FunctionalInterface` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/FunctionalInterface.html
- `java.io.UncheckedIOException` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/UncheckedIOException.html
- `java.nio.file.Files` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html
- `java.util.function.Predicate` Javadoc (SE 21, `not` @since 11) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/function/Predicate.html
- Spring Data JPA Reference, Query Methods — https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/) ← 지금 글
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
