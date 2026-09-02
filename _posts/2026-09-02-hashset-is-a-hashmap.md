---
layout: post
title: "HashSet 은 자료구조가 아니라 HashMap 이다 — OpenJDK 소스로 확인한 6가지"
date: 2026-09-02 22:25:00 +0900
categories: [backend, java]
tags: [java, collections, hashmap, hashset, jdk, data-structures, performance]
---

`HashMap` 과 `HashSet` 은 자바에서 제일 먼저 배우고 제일 자주 쓰는 자료구조다. 그래서 대부분 **"O(1) 조회"** 라는 한 줄로 이해를 멈춘다.

문제는 그 한 줄이 성립하기 위한 조건들이 코드에 안 보인다는 것이다. 조건이 깨져도 예외가 나지 않는다. **성능이 조용히 나빠지거나, 넣은 값이 조용히 사라진다.**

이 글은 [OpenJDK 의 `HashMap.java`](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashMap.java) 와 [`HashSet.java`](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashSet.java) 실물을 열어 그 조건들을 확인한다. 인용한 상수와 코드는 전부 현재 JDK 메인라인 소스 그대로다. 벤치마크 수치는 넣지 않는다 — 소스로 설명되는 것만 다룬다.

---

## 1. HashSet 에는 집합 구현이 없다

`HashSet.java` 는 404줄인데, 해시 로직이 한 줄도 없다. 전부 `HashMap` 에 위임한다.

```java
static final Object PRESENT = new Object();

public HashSet() {
    map = new HashMap<>();
}

public boolean add(E e) {
    return map.put(e, PRESENT)==null;
}

public boolean contains(Object o) {
    return map.containsKey(o);
}
```

`PRESENT` 는 **아무 의미 없는 더미 객체 하나**다. 클래스당 하나만 만들어 모든 원소의 값 자리에 같은 참조를 넣는다.

여기서 바로 따라오는 사실 셋:

- **HashSet 의 성능 특성은 HashMap 의 성능 특성과 같다.** 따로 외울 게 없다. 아래 2~6번은 전부 둘 다에 적용된다.
- **메모리는 Map 만큼 든다.** 엔트리마다 `Node` 객체(hash, key, value, next 4필드)가 하나씩 생긴다. 값 자리가 낭비되지만 참조 하나이므로 큰 낭비는 아니다. 진짜 비용은 `Node` 객체 자체다. `int` 100만 개를 `HashSet<Integer>` 에 넣으면 `int[]` 와 비교가 안 된다.
- **`LinkedHashSet` 도 같은 트릭이다.** `HashSet` 에는 `dummy` 인자를 받는 패키지 전용 생성자가 있고, 주석에 목적이 적혀 있다 — `@param dummy ignored (distinguishes this...)`. 이 생성자만 `map = new LinkedHashMap<>(...)` 를 쓴다. `LinkedHashSet` 은 `HashSet` 을 상속하면서 이 생성자를 부르는 것이 전부다.

**"Set 을 쓸까 Map 을 쓸까" 는 성능 질문이 아니다.** 의미 표현의 질문이다. 값이 필요 없으면 Set 을 쓰고, 그게 내부적으로 Map 이라는 사실은 잊어도 된다 — 아래 다섯 가지만 빼고.

---

## 2. `hashCode()` 를 그대로 쓰지 않는다 — 상위 비트를 접어 넣는다

버킷 인덱스를 구하는 식은 `(n - 1) & hash` 다. `n` 은 항상 2의 거듭제곱이므로 이 연산은 **해시의 하위 비트만 본다.** 테이블 크기가 16이면 하위 4비트가 전부다.

그래서 상위 비트가 아무리 잘 흩어져 있어도 하위 비트가 뭉치면 전부 같은 버킷에 몰린다. JDK 의 대응은 이 한 줄이다.

```java
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

**해시를 16비트 오른쪽으로 밀어 자기 자신과 XOR** 한다. 상위 16비트의 정보를 하위 16비트에 섞어 넣는 것이다. 비용은 시프트 하나 XOR 하나.

읽을 점 두 가지.

- **이건 보정이지 구제가 아니다.** `hashCode()` 가 항상 같은 값을 돌려주면 XOR 을 해도 같은 값이다. 나쁜 `hashCode()` 는 여전히 나쁘다.
- **`key == null` 이면 해시가 0이다.** `HashMap` 은 null 키 하나를 허용하고 항상 0번 버킷에 넣는다. 반면 `Map.of(...)`, `Set.of(...)` 같은 불변 컬렉션은 null 을 `NullPointerException` 으로 거부한다. `HashMap` 을 쓰다 불변 팩토리로 바꿀 때 여기서 깨진다.

---

## 3. 트리화 임계값 8은 생각보다 훨씬 안 걸린다

"버킷 하나에 8개가 넘으면 링크드 리스트가 레드-블랙 트리로 바뀐다" 는 널리 알려진 사실이다. 상수도 실제로 있다.

```java
static final int TREEIFY_THRESHOLD = 8;
static final int UNTREEIFY_THRESHOLD = 6;
static final int MIN_TREEIFY_CAPACITY = 64;
```

그런데 `treeifyBin()` 의 첫 분기가 이렇다.

```java
final void treeifyBin(Node<K,V>[] tab, int hash) {
    int n, index; Node<K,V> e;
    if (tab == null || (n = tab.length) < MIN_TREEIFY_CAPACITY)
        resize();
    else if ((e = tab[index = (n - 1) & hash]) != null) {
        // ... 실제 트리화
```

**테이블 길이가 64 미만이면 트리화하지 않고 리사이즈부터 한다.** 작은 맵에서 충돌이 몰리는 건 대개 테이블이 작아서지 해시가 나빠서가 아니라는 판단이다. 즉 기본 용량 16으로 시작한 맵은 최소 두 번 리사이즈를 거쳐 64가 되기 전까지는 트리를 절대 만들지 않는다.

그리고 트리화의 실제 보장은 생각보다 약하다. 트리 노드끼리 순서를 정할 때 해시가 같으면 `Comparable` 을 쓰고, **그것도 없으면 이렇게 처리한다.**

```java
static int tieBreakOrder(Object a, Object b) {
    int d;
    if (a == null || b == null ||
        (d = a.getClass().getName().
         compareTo(b.getClass().getName())) == 0)
        d = (System.identityHashCode(a) <= System.identityHashCode(b) ?
             -1 : 1);
    return d;
}
```

클래스 이름으로 비교하고, 그것도 같으면 `identityHashCode` 로 임의 순서를 만든다. 이건 **일관된 전순서가 아니다** — 탐색이 트리를 타고 내려가되 정확히 찾으려면 결국 양쪽 가지를 뒤져야 하는 경우가 생긴다.

정리하면: **트리화는 최악 케이스를 O(log n) 으로 만들어주는 보장이 아니라, 악성 충돌의 피해를 줄이는 완충 장치다.** 키가 `Comparable` 이 아니면 완충 효과도 줄어든다. 트리화를 믿고 `hashCode()` 를 대충 짜는 건 순서가 거꾸로다.

참고로 언트리화 임계값은 6이지 8이 아니다. 7에서 왔다 갔다 할 때 트리↔리스트 변환이 반복되는 걸 막는 히스테리시스다.

---

## 4. 가변 객체를 키로 넣는 것은 "느려짐" 이 아니라 "미정의 동작" 이다

이게 실무에서 제일 자주, 제일 조용하게 터지는 사고다. `java.util.Set` 의 클래스 주석은 이렇게 못 박는다.

> Note: Great care must be exercised if mutable objects are used as set elements. The behavior of a set is not specified if the value of an object is changed in a manner that affects `equals` comparisons while the object is an element in the set.

`java.util.Map` 의 키에 대해서도 같은 문장이 있다. **"성능이 나빠진다" 가 아니라 "동작이 명세되지 않는다"** 는 표현을 쓴다.

무슨 일이 벌어지는지는 위의 1~2번을 알면 바로 나온다. `put` 시점의 해시로 버킷을 정해 넣었는데, 필드를 바꿔 해시가 달라지면 조회는 **다른 버킷**을 뒤진다. 그래서:

- `set.contains(x)` 가 `false` 인데 `set` 안에는 `x` 가 들어 있다
- `set.remove(x)` 가 실패하는데 `size()` 는 줄지 않는다
- 반복문으로 돌면 그 원소가 멀쩡히 나온다

예외가 없다. 로그도 없다. 그냥 없는 것처럼 행동한다.

현실에서 이 형태는 대개 JPA 엔티티에서 나온다. `@Id` 를 포함해 `equals`/`hashCode` 를 만들었는데, 영속화 전에는 `id` 가 `null` 이었다가 `flush` 후 값이 채워지는 경우다. **컬렉션에 넣은 뒤 해시가 바뀌는 전형이다.** 대응은 두 가지 중 하나다 — 키는 불변 필드(비즈니스 키나 UUID)로만 해시를 만들거나, 애초에 가변 엔티티를 해시 컬렉션의 키/원소로 쓰지 않거나.

---

## 5. 반복 순서는 삽입 순서가 아니고, 규모가 커지면 바뀐다

이건 알려져 있지만 **"언제 바뀌는가"** 를 아는 사람은 적다. 리사이즈 때다. `resize()` 의 핵심 분기는 이 한 줄이다.

```java
if ((e.hash & oldCap) == 0) {
```

테이블을 2배로 늘리면 인덱스는 `hash & (newCap - 1)` 로 다시 계산되는데, 새로 추가된 비트 하나(`oldCap`)만 보면 된다. 그 비트가 0이면 원래 자리에, 1이면 `원래 자리 + oldCap` 으로 간다. 그래서 한 버킷의 리스트가 **두 갈래로 쪼개진다.**

결과적으로 반복 순서는 원소 개수가 임계치를 넘는 순간 재배치된다. 임계치는 `용량 × 0.75` 다.

```java
static final int DEFAULT_INITIAL_CAPACITY = 1 << 4; // aka 16
static final float DEFAULT_LOAD_FACTOR = 0.75f;
```

기본값이면 13번째 원소를 넣을 때 처음 바뀐다. **이게 위험한 이유는 테스트가 통과하기 때문이다.** 원소 5개짜리 단위 테스트에서 순서를 기대하는 단언문을 쓰면 초록불이 켜진다. 운영에서 데이터가 수천 건이 되면 순서가 달라지고, 테스트는 여전히 초록불이다.

순서가 필요하면 `LinkedHashMap`/`LinkedHashSet`(삽입 순서) 이나 `TreeMap`/`TreeSet`(정렬 순서) 을 **명시적으로** 쓴다. `HashMap` 이 어쩌다 원하는 순서로 나오는 건 계약이 아니다.

같은 맥락에서 하나 더 — fail-fast 이터레이터도 계약이 아니다. `HashMap` 클래스 주석의 표현 그대로다.

> Fail-fast iterators throw `ConcurrentModificationException` on a best-effort basis. Therefore, it would be wrong to write a program that depended on this exception for its correctness: *the fail-fast behavior of iterators should be used only to detect bugs.*

`ConcurrentModificationException` 은 **버그 탐지기이지 동시성 방어 수단이 아니다.** 이걸 `catch` 해서 재시도하는 코드를 본 적 있다면, 그건 동기화가 빠진 자리를 가린 것이다.

---

## 6. `new HashMap<>(1000)` 은 1000개를 담을 준비가 아니다

제일 흔한 미신이다. 생성자 인자는 **초기 용량(버킷 개수)** 이지 예상 원소 수가 아니다. 리사이즈는 `용량 × 0.75` 에서 일어나므로 `new HashMap<>(1000)` 은 1024개 버킷으로 시작하지만 임계치는 768이라 **원소가 768개를 넘는 순간 리사이즈한다.** 미리 잡아준 의미가 없다.

JDK 19 부터 이 계산을 대신 해주는 팩토리가 들어왔다.

```java
static int calculateHashMapCapacity(int numMappings) {
    return (int) Math.ceil(numMappings / (double) DEFAULT_LOAD_FACTOR);
}

public static <K, V> HashMap<K, V> newHashMap(int numMappings) { ... }
```

`HashSet` 에도 `HashSet.newHashSet(int numElements)` 가 같은 방식으로 있다. **JDK 19 이상이면 예상 크기를 아는 순간 이 팩토리를 쓰는 게 맞다.**

```java
// 이전: 직접 나눠야 했다
Map<String, Order> m = new HashMap<>((int) (expected / 0.75f) + 1);

// JDK 19+
Map<String, Order> m = HashMap.newHashMap(expected);
Set<String> s = HashSet.newHashSet(expected);
```

재미있는 건 JDK 가 자기 코드에서도 이 실수를 하고 있었다는 점이다. 현재 `HashSet(Collection)` 생성자는 이렇게 고쳐져 있다.

```java
public HashSet(Collection<? extends E> c) {
    map = HashMap.newHashMap(Math.max(c.size(), 12));
    addAll(c);
}
```

즉 `new HashSet<>(list)` 는 이미 제대로 사이징된다. 반면 **직접 만들어 `addAll` 하는 코드는 그대로 리사이즈를 겪는다.**

---

## 정리 — 여섯 줄

1. **HashSet 은 값이 더미인 HashMap 이다.** 성능 특성을 따로 외울 필요가 없다.
2. **인덱스는 해시 하위 비트만 본다.** 그래서 JDK 가 `h ^ (h >>> 16)` 로 상위 비트를 섞어 넣는다. 나쁜 `hashCode()` 는 이걸로도 못 구한다.
3. **트리화는 테이블이 64 이상일 때만 일어나고, 보장이 아니라 완충이다.** 키가 `Comparable` 이 아니면 완충 효과도 줄어든다.
4. **가변 키는 미정의 동작이다.** 넣은 값이 예외 없이 사라진다. JPA 엔티티의 `id` 지연 할당이 대표 사례다.
5. **반복 순서는 리사이즈에서 바뀐다.** 작은 테스트는 통과하고 운영에서 달라진다. 순서가 필요하면 `Linked-`/`Tree-` 를 명시한다.
6. **생성자 인자는 용량이지 원소 수가 아니다.** JDK 19+ 라면 `newHashMap`/`newHashSet` 을 쓴다.

그리고 이 여섯 가지는 전부 **단일 프로세스 안의 이야기다.** 레플리카가 두 개 이상이면 이 중 무엇도 도움이 되지 않는다 — 그 이야기는 [ConcurrentHashMap 을 믿었던 전수 조사](/2026/09/01/concurrenthashmap-in-a-multi-replica-service/) 에 따로 적었다.

---

## References

- OpenJDK `java/util/HashMap.java` — <https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashMap.java> (본문의 상수·`hash()`·`treeifyBin()`·`tieBreakOrder()`·`calculateHashMapCapacity()` 인용 출처)
- OpenJDK `java/util/HashSet.java` — <https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashSet.java> (`PRESENT`, `dummy` 생성자, `HashSet(Collection)`, `newHashSet`)
- OpenJDK `java/util/Set.java` — <https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/Set.java> (가변 원소에 대한 미정의 동작 명시)
- `java.util.HashMap` API 문서 — <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html>
- `java.util.HashSet` API 문서 — <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashSet.html>
- JDK 19 릴리스 노트 (`newHashMap`/`newHashSet`/`newLinkedHashMap` 추가, JDK-8186958) — <https://bugs.openjdk.org/browse/JDK-8186958>
