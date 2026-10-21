---
layout: post
title: "자바 Stream Gatherers 직접 만들기 — 중간 연산 확장점의 계약과 함정 (JDK 25 실측)"
date: 2026-10-21 23:00:00 +0900
categories: [java]
tags: [java, stream, gatherers, jep-485, mapConcurrent, virtual-threads, jdk25]
---

[J4 람다·Stream 글 §5.6](https://myoungsoo7.github.io/2026/10/12/java-lambda-functional-interface-stream/) 에서는 내장 Gatherer 다섯 개(`windowFixed`, `windowSliding`, `scan`, `fold`, `mapConcurrent`)의 사용 예만 짧게 봤다. 이번 글은 그다음 단계다. **Gatherer 를 직접 만드는 법**과, 그때 지켜야 하는 계약을 다룬다.

글의 코드는 모두 Eclipse Temurin `25.0.4.1+1-LTS` 에서 단일 파일(`java Demo.java`)로 실행했다. 출력은 실제 실행 결과를 그대로 옮겼다.

---

## 1. 왜 Gatherer 가 필요했나

Stream 은 최종 연산 쪽으로는 처음부터 확장할 수 있었다. `Collector` 를 직접 구현하면 `collect` 로 어떤 집계든 만들 수 있다. 반면 **중간 연산**은 `map`, `filter`, `flatMap`, `distinct`, `sorted`, `limit` 처럼 JDK 가 준 고정 목록뿐이었다.

[JEP 485](https://openjdk.org/jeps/485) 는 이 빈자리를 `Stream::gather(Gatherer)` 로 메웠다. JDK 22([JEP 461](https://openjdk.org/jeps/461))와 23([JEP 473](https://openjdk.org/jeps/473))에서 프리뷰를 거쳤고, **JDK 24 에서 API 변경 없이 정식화**됐다. 그러니 JDK 25 LTS 에서는 플래그 없이 쓸 수 있다.

JEP 본문이 동기로 드는 예가 `distinctBy` 다. "길이 기준으로 중복을 제거하라" 같은 요구는 `distinct()` 로 표현할 수 없다. JEP 는 원소를 래퍼 레코드로 감싸 `equals` 를 바꾸는 우회로를 보여 주고, 그게 얼마나 어색한지를 근거로 든다.

## 2. Gatherer 의 네 함수

[`Gatherer<T, A, R>`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.html) 는 함수 네 개로 이루어진다. T 는 입력, A 는 상태, R 은 출력 타입이다.

| 함수 | 필수 | 역할 |
|---|---|---|
| `initializer()` | 선택 | 상태 객체 `A` 를 만든다 |
| `integrator()` | **필수** | 원소 하나를 받아 상태를 갱신하고, 필요하면 `Downstream` 으로 내보낸다. `boolean` 을 반환한다 |
| `combiner()` | 선택 | 병렬 분할된 두 상태를 합친다. **이게 있어야 병렬 평가가 가능하다** |
| `finisher()` | 선택 | 입력이 끝났을 때 상태를 보고 마지막 원소를 내보낸다 |

Javadoc 이 제시하는 순차 평가 모델은 다음과 같다.

```java
A state = gatherer.initializer().get();
for (T t : data) {
    gatherer.integrator().integrate(state, t, downstream);
}
gatherer.finisher().accept(state, downstream);
```

`Collector` 의 supplier / accumulator / combiner / finisher 와 거의 같은 꼴이다. 차이는 두 가지다.

1. integrator 가 **`Downstream` 을 받아서 원소를 몇 개든 흘려보낼 수 있다.** 1:1(map), 1:0(filter), 1:N(flatMap), N:1(window) 을 모두 표현할 수 있다.
2. integrator 가 **`false` 를 반환하면 단락**(short-circuit)된다. Javadoc 의 표현으로는 "더 이상 원소가 없는 것처럼 해석"된다.

### 2.1 팩토리 일곱 개 — `of` 와 `ofSequential`

직접 클래스를 만들 필요는 없다. 정적 팩토리가 있다.

| 팩토리 | 상태 | 병렬 |
|---|---|---|
| `of(integrator)` | 없음 | 가능 |
| `of(integrator, finisher)` | 없음 | 가능 |
| `of(initializer, integrator, combiner, finisher)` | 있음 | 가능 |
| `ofSequential(integrator)` | 없음 | 순차 |
| `ofSequential(integrator, finisher)` | 없음 | 순차 |
| `ofSequential(initializer, integrator)` | 있음 | 순차 |
| `ofSequential(initializer, integrator, finisher)` | 있음 | 순차 |

`ofSequential` 이 만든 Gatherer 는 combiner 가 [`defaultCombiner()`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.html#defaultCombiner()) 다. Javadoc 은 이것을 "소유 Gatherer 가 **순차로만 평가되어야 함**을 나타낸다"고 정의한다. 상태가 있는 Gatherer 의 대부분은 이쪽으로 만들게 된다.

### 2.2 `Integrator.of` vs `Integrator.ofGreedy`

integrator 를 감싸는 팩토리도 두 가지다.

- [`Integrator.ofGreedy`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.Integrator.html): "입력을 전부 소비하며, 다운스트림이 더 원하지 않는다는 사실만 전달할 수 있다." 스스로 단락하지 않는다는 표시다. Gatherer Javadoc 은 이런 integrator 의 반환값을 "검사할 필요가 없다"고 적는다. 즉 라이브러리 쪽 최적화 힌트다.
- `Integrator.of`: 스스로 단락할 수 있는 integrator.

## 3. 직접 만들어 보기

### 3.1 `distinctBy` — 순차, 상태 있음, greedy

```java
static <T, K> Gatherer<T, ?, T> distinctBy(Function<? super T, ? extends K> key) {
    return Gatherer.ofSequential(
        HashSet<K>::new,
        Gatherer.Integrator.ofGreedy((seen, t, down) ->
            !seen.add(key.apply(t)) || down.push(t)));
}
```

반환값을 `!seen.add(...) || down.push(t)` 로 쓴 데는 이유가 있다. 이미 본 키면 내보내지 않고 `true`(계속)를 반환한다. 처음 본 키면 `push` 의 결과를 **그대로 반환한다.** 이 이유는 §4 에서 다룬다.

```java
record Order(String id, String customer, long bytes) {}
// o1 kim 400, o2 lee 300, o3 kim 500, o4 park 700, o5 lee 100
orders.stream().gather(distinctBy(Order::customer)).map(Order::id).toList();
```
```
[o1, o2, o4]
```

### 3.2 `takeWhileInclusive` — 스스로 단락하는 Gatherer

`takeWhile` 은 조건이 깨진 원소를 **버린다.** "조건을 깨뜨린 그 원소까지 포함해서" 멈추고 싶을 때가 있다. 예를 들면 페이지네이션에서 `hasNext=false` 인 마지막 페이지까지 받는 경우다.

```java
static <T> Gatherer<T, ?, T> takeWhileInclusive(Predicate<? super T> p) {
    return Gatherer.ofSequential(
        Gatherer.Integrator.of((Void unused, T t, Gatherer.Downstream<? super T> down) ->
            down.push(t) && p.test(t)));
}
```

무한 스트림에 걸고, 업스트림에서 실제로 몇 개를 당겼는지 `peek` 로 셌다.

```java
Stream.iterate(1, i -> i + 1).peek(i -> seen.incrementAndGet())
      .gather(takeWhileInclusive(i -> i < 5)).toList();
Stream.iterate(1, i -> i + 1).takeWhile(i -> i < 5).toList();
```
```
takeWhileInclusive = [1, 2, 3, 4, 5] (upstream pulled 5)
takeWhile          = [1, 2, 3, 4]
```

`false` 를 반환한 순간 업스트림 당김이 멈춘다. 무한 스트림에서도 끝난다. 이것은 `ofGreedy` 로는 만들 수 없는 Gatherer 다.

### 3.3 `batchByWeight` — finisher 와 `isRejecting`

`windowFixed(n)` 은 **개수** 기준이다. 실무에서는 "Kafka 메시지 크기 합이 1MB 를 넘지 않게", "벌크 insert 바이트가 한도를 넘지 않게"처럼 **무게** 기준으로 묶어야 할 때가 더 많다.

```java
static <T> Gatherer<T, ?, List<T>> batchByWeight(long limit, ToLongFunction<? super T> w) {
    class State { List<T> buf = new ArrayList<>(); long sum; }
    return Gatherer.ofSequential(
        State::new,
        Gatherer.Integrator.ofGreedy((s, t, down) -> {
            long wt = w.applyAsLong(t);
            boolean more = true;
            if (!s.buf.isEmpty() && s.sum + wt > limit) {
                more = down.push(List.copyOf(s.buf));
                s.buf.clear(); s.sum = 0;
            }
            s.buf.add(t); s.sum += wt;
            return more;
        }),
        (s, down) -> {
            if (!s.buf.isEmpty() && !down.isRejecting()) down.push(List.copyOf(s.buf));
        });
}
```
```
batchByWeight(1000)            = [[o1, o2], [o3], [o4, o5]]
batchByWeight(1000) + limit(1) = [[o1, o2]]
```

세 가지를 짚어 둔다.

- **finisher 가 없으면 마지막 배치가 사라진다.** 입력이 끝났을 때 버퍼에 남은 `[o4, o5]` 를 내보낼 기회는 finisher 뿐이다. 이 버그는 테스트 데이터가 우연히 한도에 딱 맞으면 드러나지 않는다.
- **`isRejecting()`** 은 finisher 에서 다운스트림이 이미 닫혔는지 확인하는 용도다. [Javadoc](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.Downstream.html) 은 이것이 **best-effort** 라고 명시한다. 한 번 `true` 가 되면 다시 `false` 로 돌아가지는 않는다. JEP 485 의 `fixedWindow` 예제도 같은 방식으로 finisher 를 막는다.
- **`List.copyOf` 로 복사해서 내보낸다.** 내보낸 뒤 `buf.clear()` 를 하므로 같은 리스트를 넘기면 다운스트림이 받은 배치가 비어 버린다. 내장 `windowFixed` 도 [Javadoc](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherers.html#windowFixed(int)) 에서 각 윈도를 수정 불가 `List` 로 준다고 명시한다.

### 3.4 `mapNotNull` — 병렬 가능한 무상태 Gatherer

상태가 없으면 `Gatherer.of(integrator)` 만으로 병렬 평가가 가능하다.

```java
static <T, R> Gatherer<T, ?, R> mapNotNull(Function<? super T, ? extends R> f) {
    return Gatherer.of(Gatherer.Integrator.ofGreedy(
        (Void unused, T t, Gatherer.Downstream<? super R> down) -> {
            R r = f.apply(t);
            return r == null || down.push(r);
        }));
}

IntStream.rangeClosed(1, 20).boxed().parallel()
         .gather(mapNotNull(i -> i % 3 == 0 ? "x" + i : null)).toList();
```
```
[x3, x6, x9, x12, x15, x18]
```

`parallel()` 에서도 encounter order 대로 나왔다. 람다 파라미터 타입을 `(Void unused, T t, ...)` 로 다 적어야 하는 점은 다소 번거롭다. 무상태 integrator 는 상태 타입이 `Void` 라서 컴파일러가 추론하지 못하는 경우가 있다.

### 3.5 `andThen` 으로 합성

```java
orders.stream()
      .gather(distinctBy(Order::customer).andThen(batchByWeight(1000, Order::bytes)))
      .toList();
```
```
[[o1, o2], [o4]]
```

JEP 485 는 `source.gather(a).gather(b).gather(c)` 와 `source.gather(a.andThen(b).andThen(c))` 가 **의미상 동등**하다고 적는다. 합성해 둔 Gatherer 하나를 상수로 공유할 수 있다는 점이 실용적인 이득이다.

## 4. 함정 1 — `push` 의 반환값을 버리면

[`Downstream.push`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.Downstream.html) 는 "더 보낼 수 있으면 `true`, 아니면 `false`" 를 반환한다. 한 번 `false` 를 반환하면 그 뒤의 `push` 는 계속 `false` 다.

이 값을 무시하면 어떻게 되는지 쟀다. 원소 하나를 100만 번 반복해서 내보내는 Gatherer 두 개를 만들고, 뒤에 `limit(3)` 을 걸었다.

```java
// 무시
for (int i = 0; i < n; i++) { calls.incrementAndGet(); down.push(t); }
return true;

// 존중
for (int i = 0; i < n; i++) { calls.incrementAndGet(); if (!down.push(t)) return false; }
return true;
```
```
push ignored: loop iterations=1000000, respected: 3
```

**결과는 똑같이 3개인데, 무시한 쪽은 루프를 100만 번 다 돌았다.** 결과가 맞으니 테스트로는 잡히지 않는다. 반복할 때마다 HTTP 호출이나 DB 조회를 하는 Gatherer 였다면 그 비용이 그대로 낭비된다.

규칙은 간단하다. **1:N 으로 내보내는 integrator 는 매 `push` 결과를 확인하고, `false` 면 즉시 `false` 를 반환한다.** 1:1 integrator 는 `return down.push(x);` 로 끝내면 된다.

## 5. 함정 2 — 순차 Gatherer 를 `parallel()` 에 넣으면

```java
IntStream.rangeClosed(1, 12).boxed().parallel()
         .gather(Gatherers.windowFixed(5)).toList();
```
```
[[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12]]
```

결과는 맞다. 오류가 나지도 않는다. 하지만 이 단계는 병렬로 돌지 않았다. JEP 485 는 combiner 가 없는 Gatherer 가 병렬 파이프라인에 들어가면 `parallel().forEachOrdered()` 와 비슷하게 평가된다고 설명한다. 앞뒤 단계는 병렬일 수 있지만, Gatherer 자체는 encounter order 대로 하나씩 처리한다.

그러니 "parallel 을 붙였으니 빨라지겠지"는 성립하지 않는다. **상태가 있는 Gatherer 를 병렬로 돌리려면 combiner 를 직접 설계해야 한다.** 분할된 두 상태를 합칠 수 있는 연산(합계, 최댓값, 집합 합집합 등)이 아니면 애초에 병렬화할 수 없다. JEP 485 의 `selectOne` 예제가 combiner 를 단 예다. `Math::max` 처럼 결합법칙이 성립하는 selector 로 두 부분 결과 중 하나를 고른다.

Javadoc 의 계약도 함께 지켜야 한다. 상태 객체와 `Downstream` 참조는 그것이 전달된 메서드 호출 기간보다 오래 **캡처·보관하거나 다른 스레드에 노출하면 안 된다.** combiner 나 finisher 로 넘어간 상태는 integrator 로 다시 넘어오지 않는다.

## 6. `mapConcurrent` — 가상 스레드 + 순서 보존

내장 Gatherer 중 가장 실무적인 것이 [`mapConcurrent(maxConcurrency, mapper)`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherers.html#mapConcurrent(int,java.util.function.Function)) 다. Javadoc 이 보장하는 것은 세 가지다.

- **가상 스레드**로 실행한다.
- **스트림 순서를 보존**한다.
- 다운스트림이 더 원하지 않으면 진행 중인 작업을 best-effort 로 취소한다.

뒤 원소일수록 빨리 끝나도록 일부러 대기 시간을 거꾸로 줬다. 원소 `i` 는 `(21-i)×10ms` 동안 잔다.

```java
IntStream.rangeClosed(1, 20).boxed()
    .gather(Gatherers.mapConcurrent(4, i -> {
        if (Thread.currentThread().isVirtual()) virt.incrementAndGet();
        int now = inFlight.incrementAndGet(); peak.accumulateAndGet(now, Math::max);
        sleep((21 - i) * 10L);
        inFlight.decrementAndGet();
        return i;
    })).toList();
```
```
mapConcurrent(4) = [1, 2, ..., 20] virtual=20/20 peak=4 610ms
sequential sleep sum = 2100ms
```

- 20개 모두 가상 스레드에서 실행됐다.
- 동시 실행 수 최대치는 정확히 4 였다. `maxConcurrency` 가 상한으로 지켜졌다.
- 늦게 끝나는 앞 원소를 기다려서 **결과는 입력 순서 그대로** 나왔다.
- 순차로 돌렸다면 대기 시간 합이 2100ms 였을 것을 610ms 에 끝냈다. 이것은 내 환경에서 한 번 잰 값이다. 비율보다는 "동시에 돈다"는 사실만 보면 된다.

**순서 보존의 대가는 head-of-line blocking 이다.** 1번이 200ms 걸리면 그동안 이미 끝난 2~4번도 다운스트림으로 나가지 못한다. 순서가 필요 없고 처리량이 중요하면 `ExecutorService` 와 `CompletionService` 처럼 완료 순서대로 받는 도구가 맞다.

예외는 이렇게 나왔다.

```java
Stream.of(1, 2, 3).gather(Gatherers.mapConcurrent(2, i -> {
    if (i == 2) throw new IllegalStateException("boom");
    return i;
})).toList();
```
```
exception = java.lang.IllegalStateException / cause=null
```

Javadoc 은 mapper 가 예외로 끝나면 그 결과가 다운스트림으로 나갈 차례에 `RuntimeException` 으로 다시 던지고, 남은 작업을 취소한다고 적고 있다. Temurin 25.0.4 에서는 원래의 `IllegalStateException` 이 감싸이지 않고 그대로 올라왔다. 다른 버전에서 래핑 방식이 다를 수 있으니 **예외 타입에 의존하는 로직이라면 쓰는 JDK 에서 직접 확인하길 권한다.**

## 7. 정리 — 언제 직접 만드나

| 상황 | 선택 |
|---|---|
| map / filter / flatMap 으로 표현된다 | 기존 연산. Gatherer 를 만들 이유가 없다 |
| 키 기준 중복 제거, 연속 중복 제거, 무게 기준 배치, 포함형 takeWhile | `ofSequential` 로 직접 만든다 |
| I/O 바운드 변환을 동시 실행 수를 제한해 돌리고 순서는 유지 | `Gatherers.mapConcurrent` |
| 상태가 있는데 병렬로 돌려야 한다 | combiner 를 설계할 수 있을 때만 `Gatherer.of(…, combiner, …)` |

직접 만들 때의 체크리스트는 다음과 같다.

1. 스스로 멈출 일이 없으면 `Integrator.ofGreedy`, 멈출 수 있으면 `Integrator.of`.
2. `push` 의 반환값을 버리지 않는다. 1:N 이면 루프 안에서 확인한다.
3. 버퍼링하는 Gatherer 는 **finisher 에서 잔여분을 내보내고**, 그 전에 `isRejecting()` 을 본다.
4. 내보낸 객체를 나중에 수정하지 않는다. 복사하거나 불변으로 넘긴다.
5. 상태·`Downstream` 참조를 메서드 밖으로 새어 나가게 하지 않는다.
6. `parallel()` 을 붙였다고 Gatherer 가 병렬로 도는 게 아니다. combiner 가 있어야 한다.

---

## References

- [JEP 485: Stream Gatherers](https://openjdk.org/jeps/485) — 정식화 (JDK 24)
- [JEP 461: Stream Gatherers (Preview)](https://openjdk.org/jeps/461) — JDK 22
- [JEP 473: Stream Gatherers (Second Preview)](https://openjdk.org/jeps/473) — JDK 23
- [`java.util.stream.Gatherer` — Java SE 25 API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.html)
- [`Gatherer.Integrator` — Java SE 25 API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.Integrator.html)
- [`Gatherer.Downstream` — Java SE 25 API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherer.Downstream.html)
- [`java.util.stream.Gatherers` — Java SE 25 API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Gatherers.html)
- 실행 환경: Eclipse Temurin `25.0.4.1+1-LTS` (Docker 이미지 `eclipse-temurin:25-jdk`), 단일 파일 실행
