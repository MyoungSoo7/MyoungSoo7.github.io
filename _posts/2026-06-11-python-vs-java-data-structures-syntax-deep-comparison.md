---
layout: post
title: "*Python 과 Java 의 *자료구조 / 문법 *4 단 깊이 비교* — *list vs ArrayList / dict vs HashMap / 시간 복잡도 / GC / GIL vs JVM Thread* 까지 *실전 선택 기준* 7 가지*"
date: 2026-06-11 11:00:00 +0900
categories: [language, python, java, comparison, data-structures]
tags: [python, java, list, arraylist, dict, hashmap, set, tuple, mutability, complexity, gil, jvm, gc, lambda, stream, functional]
---

이 글은 *Python 과 Java* 의 *자료구조 / 문법 / 런타임 모델* 을 *4 단 깊이* 로 비교한다. *"list = ArrayList 같은 거" 의 *얄팍한 정리* 가 아니라, *내부 구현 / 시간 복잡도 / 메모리 / 동시성* 까지 *왜 다른지*. 마지막에 *실전 선택 기준 7 가지* 로 *어떤 상황에 어느 언어 가 *진짜 적합* 한지* 정리.

읽고 가셔도 좋은 분:
1. *Java 백엔드 개발자* — *Python 을 *추가 학습* 하려는데 *익숙한 자료구조의 *Python 등가물* 이 궁금한 사람
2. *Python 으로 시작* 했지만 *Java 백엔드 면접* 준비 중 — *컬렉션 차이가 *왜 면접 단골 질문* 인지 궁금한 사람
3. *AI / 데이터* 영역에서 *Python 으로 코드* 짜고 있지만 *생산 시스템 일부를 *Java 로 마이그레이션* 검토 중인 사람

---

## TL;DR

> *Python 과 Java* 는 *문법은 *비슷 해 보여도* — *list vs ArrayList* 의 *내부 메모리 layout*, *dict vs HashMap* 의 *충돌 처리*, *GIL vs JVM thread*, *Garbage Collector 의 *세대 모델* 이 *완전히 다르다*. *작은 차이가 *production 성능 *10× 격차* 로 변환. *7 가지 실전 기준* 으로 *상황별 *적합 언어* 가 *기계적으로* 결정.

**한 표로**:

| 영역 | Python | Java |
|------|--------|------|
| **list** | dynamic array, *모든 타입 혼합* | `ArrayList<T>` — 타입 강제, `Object[]` 백킹 |
| **dict** | open addressing + perturbation | `HashMap` — Separate Chaining + Treeify (>8) |
| **set** | dict 와 동일 구조 (key only) | `HashSet` = `HashMap` wrapper |
| **tuple** | *immutable* — 메모리 30% 절감 | *없음* (record class 가 비슷) |
| **GC** | reference counting + cycle detector | Generational (G1 / ZGC) |
| **동시성** | **GIL** — single-thread bytecode | JVM thread (preemptive) |
| **타입** | duck typing + type hint (선택) | static typing + generics |

---

## 0. *Why — 두 언어 *동시 익히는 이유*

> *2026 년 백엔드 / AI 시장* 에서 *Python 은 *AI / 데이터 의 *de-facto 표준*. *Java 는 *Spring 생태의 *production 백본*. *두 언어를 *오가는 능력* 이 *AI 백엔드 / MLOps* 영역의 *진짜 무기*.

내 *lemuel-quant-core* 가 *C++ 시장 데이터 + Python 분석 사이드카 + Java Spring Boot API* 의 *3 언어 동시 운영*. *언어 간 *경계 설정* 이 *시스템의 *진짜 영역 분리*.

---

## 1. *기본 자료형 — *비슷해 보이지만 *완전 다른 메모리***

### 1.1 *정수 (int) 의 *진짜 차이***

**Python**:
```python
x = 10
print(type(x))   # <class 'int'>
print(x.bit_length())  # 4
x = 10 ** 100    # 자동 *임의 정밀도 (BigInteger)*
print(x.bit_length())  # 333
```

> Python 의 `int` 는 *고정 크기 X*. *값 크기에 따라 *자동 확장*. C extension 으로 *항상 PyLongObject*. *오버플로 0*.

**Java**:
```java
int x = 10;
System.out.println(Integer.SIZE);  // 32 bit 고정
x = Integer.MAX_VALUE;  // 2,147,483,647
x += 1;                 // -2,147,483,648  ← *오버플로!*

// 임의 정밀도가 필요하면
BigInteger big = new BigInteger("10").pow(100);
```

> Java 의 `int` 는 *32 bit 고정*. *오버플로 *조용히* 발생 (예외 없음). *큰 수는 *명시적 `BigInteger` 사용*.

| 항목 | Python `int` | Java `int` |
|------|-------------|------------|
| 크기 | 가변 (28+ bytes) | 4 bytes 고정 |
| 오버플로 | *불가능* | *조용히 발생* |
| 산술 비용 | 느림 (객체 할당) | 빠름 (CPU 명령 1) |
| `0` 캐싱 | 작은 정수는 캐시 | Integer.valueOf(0) 캐시 |

> **함정**: Java 의 *`int` 와 *`Integer` (boxing)* 가 *서로 다름*. *Python 은 모두 객체*.

### 1.2 *문자열 — *immutable + interning***

**공통점**: *둘 다 immutable*.

```python
# Python
s = "hello"
s[0] = 'H'    # TypeError — immutable
```

```java
// Java
String s = "hello";
s.charAt(0) = 'H';   // 컴파일 에러 — String 은 immutable
```

**차이 — interning**:

```python
# Python — 짧은 문자열 자동 intern (CPython 구현)
a = "hello"
b = "hello"
print(a is b)   # True (intern 됨)

# 동적 생성은 X
c = "hel" + "lo"
print(a is c)   # True (컴파일 최적화)
d = "".join(['h','e','l','l','o'])
print(a is d)   # False (런타임 생성)
```

```java
// Java — string pool
String a = "hello";
String b = "hello";
System.out.println(a == b);  // true (pool 에서 같은 ref)

String c = new String("hello");
System.out.println(a == c);          // false (new = heap)
System.out.println(a == c.intern()); // true (intern 으로 pool 가져옴)
```

> **함정**: *Python 의 `is` 와 *Java 의 `==` 가 *둘 다 *참조 비교*. *값 비교는 `==` (Python), `.equals()` (Java)*. *이 둘을 혼동하면 *치명적 버그*.

---

## 2. *컬렉션 4 종 *내부 비교***

### 2.1 *List (Python) vs ArrayList (Java)*

```python
# Python
nums = [1, 2, 3]
nums.append(4)
nums.insert(0, 0)
nums[2] = 99
mixed = [1, "hello", 3.14, [1,2]]   # *타입 혼합 자유*
```

```java
// Java
List<Integer> nums = new ArrayList<>(Arrays.asList(1, 2, 3));
nums.add(4);
nums.add(0, 0);
nums.set(2, 99);
// 타입 혼합? — Object 사용해야 함, 보통 안 함
List<Object> mixed = new ArrayList<>(List.of(1, "hello", 3.14));
```

**내부 구현**:

| 항목 | Python `list` | Java `ArrayList` |
|------|--------------|------------------|
| 백킹 | `PyObject **` (포인터 배열) | `Object[]` |
| 초기 크기 | 0 | 10 (`DEFAULT_CAPACITY`) |
| 확장 비율 | `~ 1.125×` | `1.5×` |
| element 타입 | 혼합 | 동일 (`<T>`) |
| 메모리 (1M ints) | ~28 MB (정수 객체) | ~16 MB (`Integer` boxed) |
| 메모리 (`int[]`) | N/A | ~4 MB ← *최고 효율* |

> *Java 의 *primitive 배열 (`int[]`)* 이 *Python `list` 보다 *7× 작음*. *고성능 영역에서 *Python *불리*.

**시간 복잡도**:

| 연산 | Python `list` | Java `ArrayList` |
|------|--------------|------------------|
| `lst[i]` | O(1) | O(1) |
| `append` | amortized O(1) | amortized O(1) |
| `insert(0, x)` | O(n) | O(n) |
| `del lst[i]` | O(n) | O(n) |
| `x in lst` | O(n) | O(n) |
| `lst.sort()` | O(n log n) — Timsort | O(n log n) — Timsort (Java 8+) |

> *두 언어 모두 *Timsort* 채택. *Tim Peters 가 *Python 위해 *2002 년에 발명* 한 알고리즘이 *Java 에 *역수입*.

### 2.2 *Dict (Python) vs HashMap (Java)*

```python
# Python
d = {"name": "유라", "age": 30}
d["email"] = "ura@example.com"
print(d.get("phone", "없음"))
```

```java
// Java
Map<String, Object> d = new HashMap<>();
d.put("name", "유라");
d.put("age", 30);
d.put("email", "ura@example.com");
System.out.println(d.getOrDefault("phone", "없음"));
```

**내부 충돌 처리 — *완전 다름***:

| 항목 | Python `dict` | Java `HashMap` |
|------|--------------|----------------|
| 해시 충돌 | **Open Addressing** + perturbation | **Separate Chaining** (linked list) |
| 충돌 8 개 초과 시 | resize | **Treeify** (Red-Black Tree, O(log n)) |
| load factor | 2/3 (~ 0.667) | 0.75 |
| 삽입 순서 보존 | **유지** (3.7+) | *유지 안 함* (LinkedHashMap 사용) |
| null 키 | *허용* | *허용 (1 개만)* |
| 메모리 (1M entries) | ~ 80 MB | ~ 64 MB |

**Open Addressing vs Separate Chaining 의 *차이***:

```
Python (Open Addressing):
  hash 충돌 시 *다음 빈 슬롯* 으로 이동
  → 캐시 친화적 (연속 메모리)
  → 삭제가 *복잡* (tombstone 필요)

Java (Separate Chaining):
  hash 충돌 시 *연결리스트* 에 append
  → 삭제 단순
  → 너무 많이 모이면 *Tree 화* (Java 8+)
```

**Treeify — Java 의 *공격 방어***:

```java
// HashMap.TREEIFY_THRESHOLD = 8
// 한 bucket 에 8 개 이상 충돌 시 → Red-Black Tree 변환
// 이유: *Hash collision DoS 공격* 방어
//
// 예: 공격자가 *해시가 같은 100 개 키* 보내면
//     Separate Chaining 만 → O(100) lookup 매번
//     Treeify 후 → O(log 100) ≈ O(7)
```

> *Python 의 *Open Addressing* 은 *hash 의 *randomization* 으로 같은 공격 방어. *접근 방법은 다르지만 *목표는 같음*.

### 2.3 *Set (Python) vs HashSet (Java)*

**Python**: `set` 은 *dict 의 *key only* 버전. 같은 hash 알고리즘.

**Java**: `HashSet` 은 *내부적으로 `HashMap` wrapper*. 값은 모두 `PRESENT` 라는 dummy object.

```java
// Java HashSet 실제 구현 — 한 줄 요약
public class HashSet<E> {
    private static final Object PRESENT = new Object();
    private HashMap<E, Object> map = new HashMap<>();
    
    public boolean add(E e) {
        return map.put(e, PRESENT) == null;
    }
}
```

> *Java 의 `HashSet` 은 *HashMap 의 메모리 *60% wasted*. *Python 의 `set` 은 *내부 최적화*.

### 2.4 *Tuple — *Python 만 있는 *immutable 컬렉션***

```python
# Python — 불변 + 메모리 효율
point = (3, 4)
# point[0] = 5  # TypeError

# Tuple 의 *진짜 가치*: dict key 가능
locations = {(35.6, 139.7): "Tokyo", (37.6, 127.0): "Seoul"}
```

**메모리 비교**:
```python
import sys
sys.getsizeof((1,2,3))      # 64 bytes
sys.getsizeof([1,2,3])      # 88 bytes  ← list 30% 더 많음
```

**Java 등가물**: 
- *없음*. 가장 가까운 건 *`record` class (Java 14+)*:

```java
public record Point(int x, int y) {}

Point p = new Point(3, 4);
// p.x() = 5;  // ❌ — record 는 immutable
```

> *Java record 는 *Python tuple 의 *상위 호환*. *이름 있는 필드 + immutable*. *2020 년 이후 *현대 Java 의 *큰 진화*.

### 2.5 *Linked List vs Deque*

| Python | Java |
|--------|------|
| `collections.deque` | `LinkedList<T>` (deque) 또는 `ArrayDeque<T>` (faster) |
| O(1) head/tail | 동일 |

> 둘 다 *queue / stack* 의 *현실적 선택*. *Java 는 `ArrayDeque` 가 `LinkedList` 보다 *2-3× 빠름* — *cache locality*.

---

## 3. *문법 — *익숙해도 *조심 해야 할 *함정 5 가지***

### 3.1 *for 루프 — *둘 다 *for-each*

```python
for x in nums:
    print(x)

for i, x in enumerate(nums):   # *index 동시*
    print(i, x)
```

```java
for (int x : nums) {
    System.out.println(x);
}

for (int i = 0; i < nums.size(); i++) {
    System.out.println(i + " " + nums.get(i));
}

// Java 8+ stream
IntStream.range(0, nums.size())
    .forEach(i -> System.out.println(i + " " + nums.get(i)));
```

### 3.2 *조건식 — *삼항 연산자*

```python
result = "양수" if x > 0 else "음수"
```

```java
String result = x > 0 ? "양수" : "음수";
```

### 3.3 *List Comprehension — *Python 만의 무기**

```python
# Python — 한 줄
squares = [x*x for x in range(10) if x % 2 == 0]
# [0, 4, 16, 36, 64]
```

```java
// Java 등가
List<Integer> squares = IntStream.range(0, 10)
    .filter(x -> x % 2 == 0)
    .map(x -> x * x)
    .boxed()
    .toList();
```

> *Python 의 *Comprehension* 이 *간결성 우위*. *Java 8 Stream* 이 *비슷한 표현력 따라잡았지만 *3-4× 보일러플레이트*.

### 3.4 *Try / Except — *예외 처리*

```python
try:
    result = risky_call()
except ValueError as e:
    log.error(f"값 오류: {e}")
except (TypeError, KeyError) as e:
    log.error(f"타입/키 오류: {e}")
else:
    log.info("성공")
finally:
    cleanup()
```

```java
try {
    Object result = riskyCall();
} catch (NumberFormatException e) {
    log.error("값 오류: {}", e.getMessage());
} catch (ClassCastException | NullPointerException e) {
    log.error("타입/Null 오류: {}", e.getMessage());
} finally {
    cleanup();
}
// Java 의 *checked exception* 은 강제 catch 또는 declare
```

> *Java 의 *checked exception* 이 *Python 에 없음*. *둘 다 장단점* — *Java 는 *컴파일 강제*, *Python 은 *유연*.

### 3.5 *함수 선언 — *first-class function*

```python
# Python — 함수가 *값*
def double(x): return x * 2

triple = lambda x: x * 3

list(map(double, [1,2,3]))   # [2, 4, 6]
```

```java
// Java — 함수형 인터페이스
Function<Integer, Integer> doubleFn = x -> x * 2;
Function<Integer, Integer> triple = x -> x * 3;

List.of(1,2,3).stream()
    .map(doubleFn::apply)
    .toList();
```

> *Python 의 함수가 *진짜 first-class*. *Java 의 lambda 는 *함수형 인터페이스의 *syntactic sugar*. *내부적으로는 *anonymous class 와 *유사*.

---

## 4. *클래스 — *상속 + 다형성 + 캡슐화*

### 4.1 *기본 클래스*

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def greet(self):
        return f"{self.name}, {self.age}살"

p = Person("유라", 30)
print(p.greet())
```

```java
public class Person {
    private String name;
    private int age;
    
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
    
    public String greet() {
        return String.format("%s, %d살", name, age);
    }
    
    public String getName() { return name; }
    public int getAge() { return age; }
}
```

> *Python: ~7 줄*. *Java: ~15 줄*. *getter/setter 의 *Java 의 *반복 부담* 이 *대표적 보일러플레이트*. *Lombok 의 `@Data`* 또는 *Java 16+ `record`* 가 해결.

### 4.2 *상속*

```python
class Employee(Person):
    def __init__(self, name, age, salary):
        super().__init__(name, age)
        self.salary = salary
    
    def greet(self):
        return f"{super().greet()} - 연봉 {self.salary}"
```

```java
public class Employee extends Person {
    private long salary;
    
    public Employee(String name, int age, long salary) {
        super(name, age);
        this.salary = salary;
    }
    
    @Override
    public String greet() {
        return super.greet() + " - 연봉 " + salary;
    }
}
```

### 4.3 *다중 상속 — *Python 만 *가능***

```python
# Python — *다중 상속* 가능 (MRO)
class Cook: ...
class Driver: ...
class Manager(Cook, Driver): ...

# Java — *단일 상속 only*. 대신 *Interface 다중 implement*
```

> *Python 의 *다중 상속* 은 *diamond 문제* 가능 (MRO 로 해결). *Java 는 *처음부터 *불가능 하게 *언어 설계*.

---

## 5. *동시성 — *결정적 *언어 차이***

### 5.1 *Python 의 *GIL — 진짜 영향**

```python
import threading

def cpu_work():
    sum = 0
    for i in range(10**7):
        sum += i

# 4 thread 동시 실행
threads = [threading.Thread(target=cpu_work) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
```

**현실**:
- *CPython 의 *GIL (Global Interpreter Lock)* — *어떤 순간에도 *1 thread 만 bytecode 실행*
- *4 thread 가 *4 코어 사용* 못 함. *1 core 만 100%*
- *CPU bound 작업 = 4 thread *순차 실행*
- *해법*:
  - `multiprocessing` (별도 프로세스 → 통신 비용)
  - C extension (numpy, pandas 가 *GIL 해제*)
  - **PEP 703 — *No-GIL Python* (3.13+ 옵션, 2025 년)**

### 5.2 *Java JVM Thread*

```java
import java.util.concurrent.*;

ExecutorService executor = Executors.newFixedThreadPool(4);
for (int i = 0; i < 4; i++) {
    executor.submit(() -> {
        long sum = 0;
        for (int j = 0; j < 10_000_000; j++) sum += j;
    });
}
executor.shutdown();
```

- *진짜 OS thread*. *4 코어 *100% 활용*.
- *Java 21+ Virtual Thread (Project Loom)* — *수백만 *경량 thread* 가능.

**비교**:

| 항목 | Python (GIL) | Java JVM |
|------|-------------|----------|
| CPU 병렬 | *불가* | *완전 가능* |
| IO 병렬 | *가능* (GIL 해제) | *가능* |
| 권장 모델 | asyncio (단일 thread, event loop) | thread pool + Virtual Thread |
| 무거운 계산 | numpy / multiprocessing | 그냥 thread |

### 5.3 *AsyncIO vs Reactive*

```python
# Python asyncio
import asyncio

async def fetch(url):
    await asyncio.sleep(1)
    return f"data from {url}"

async def main():
    results = await asyncio.gather(
        fetch("a"), fetch("b"), fetch("c")
    )
    print(results)

asyncio.run(main())
```

```java
// Java — CompletableFuture
CompletableFuture<String> a = CompletableFuture.supplyAsync(() -> fetch("a"));
CompletableFuture<String> b = CompletableFuture.supplyAsync(() -> fetch("b"));
CompletableFuture<String> c = CompletableFuture.supplyAsync(() -> fetch("c"));

CompletableFuture.allOf(a, b, c)
    .thenAccept(v -> {
        System.out.println(List.of(a.join(), b.join(), c.join()));
    });
```

---

## 6. *Garbage Collector — *완전히 다른 모델***

### 6.1 *Python GC — *Reference Counting + Cycle Detector***

```python
import sys

x = [1, 2, 3]
print(sys.getrefcount(x))  # 2 (변수 + getrefcount 인자)

y = x
print(sys.getrefcount(x))  # 3

del y
print(sys.getrefcount(x))  # 2

# 순환 참조 — reference counting 만으론 X
a = []
b = []
a.append(b)
b.append(a)
del a
del b
# → GC 의 *cycle detector* 가 주기적 청소
```

> **장점**: *deterministic destruction* (객체 *즉시 소멸*). *RAII 가능*.
> **단점**: *모든 객체에 *refcount 필드* 8 bytes 추가 — *메모리 오버헤드*.

### 6.2 *Java GC — *Generational + Concurrent***

```
[Eden]  →  [S0] / [S1] (Young)   →  [Old]
   ↑                                    ↑
새 객체                            오래 살아남은 객체

Minor GC: Eden + Survivor — *millisec*
Major GC: Old generation — *수십 millisec ~ 수 초*

알고리즘:
  - Parallel GC      throughput 우선
  - G1 GC ★ default  대형 heap (~ 4GB+)
  - ZGC              very low latency (< 1ms pause)
  - Shenandoah       Red Hat 의 low-latency
```

**비교**:

| 항목 | Python | Java |
|------|--------|------|
| 모델 | RefCount + Cycle | Generational |
| Pause | 거의 없음 | minor: ~10ms, major: 0.5s+ |
| 메모리 | RefCount overhead | 더 큰 heap 필요 |
| Deterministic? | *yes* — destructor 즉시 | *no* — 정확한 GC 시점 모름 |

> **결론**: *Python 은 *작은 메모리 / 즉시 해제* 강점. *Java 는 *대용량 / 동시성 throughput* 강점.

---

## 7. *실전 선택 기준 7 가지*

### 기준 1 — *팀 / 생태계*

- *데이터 / AI 팀* → Python (numpy, pandas, scikit-learn, PyTorch)
- *백엔드 / 엔터프라이즈* → Java (Spring, JPA, Kafka client)

### 기준 2 — *CPU intensive 코드*

- *Python 으로 *순수 CPU 작업 X*. *반드시 *C extension* (numpy / Cython)
- *Java 는 *그냥 작성*. JIT 가 *최적화*

### 기준 3 — *마이크로 latency 요구*

- *p99 < 1ms 필요* → Java (ZGC)
- *p99 < 10ms 충분* → Python OK

### 기준 4 — *런타임 메모리*

- *< 100MB 필요* (Lambda 등) → Python
- *수 GB 가능* → Java

### 기준 5 — *동시성 패턴*

- *IO bound* → 둘 다 OK (asyncio / Loom)
- *CPU bound 멀티스레딩* → Java *압도*

### 기준 6 — *AI 모델 inference*

- *PyTorch / TensorFlow 모델* → Python *(직접)*
- *Java 에서는 *ONNX Runtime / DJL* — 가능하지만 *간접*

### 기준 7 — *MLOps / 배포 표준*

- *Docker 이미지 작음* → Python (`python:3.13-slim` ~ 50MB)
- *Spring Boot* → ~250MB

---

## 8. *마무리 — *두 언어의 *진짜 의미***

### 8.1 *동시에 *익히는 것의 가치*

> *2026 년 백엔드 / AI 시장* 에서 *한 언어만 *고집하는 *경력은 *천장이 빠르다*. *Python 으로 *데이터 + AI*, *Java 로 *production 백엔드* — *둘의 *경계 설정* 이 *시스템 설계의 *핵심 능력*.

### 8.2 *내부 구현 *왜 다른지* 이해의 가치*

> *list 와 ArrayList 의 *시간 복잡도가 *같다* 라고 *외워두는 것 vs *Timsort 가 *Python 에서 Java 로 *역수입* 됐다는 *이유와 함께* 외우는 것 — *이 차이가 *깊이 면접 답변* 의 *진짜 차이*.

### 8.3 *이력서 변환 hook*

> *"Python 과 Java 둘 다 사용 가능"* 한 줄에:
> - list vs ArrayList *내부 메모리 layout* 차이
> - dict vs HashMap *충돌 처리* 알고리즘 차이 (Open Addressing vs Separate Chaining + Treeify)
> - GIL vs JVM thread 의 *CPU 병렬 차이*
> - RefCount vs Generational GC 의 *deterministic destruction 차이*
> - 7 가지 *실전 선택 기준*
> 
> *4 단 깊이 면접 답변* 모두 준비.

---

## 부록 — *한 표로 정리한 *컬렉션 매핑***

| 기능 | Python | Java |
|------|--------|------|
| 동적 배열 | `list` | `ArrayList<T>` |
| 고정 배열 | (없음) | `int[]`, `T[]` |
| Linked List | `collections.deque` | `LinkedList<T>` |
| Stack | `list.append/pop` | `Deque<T>` (Stack class 비추) |
| Queue | `collections.deque` | `ArrayDeque<T>` |
| Priority Queue | `heapq` | `PriorityQueue<T>` |
| Hash Map | `dict` | `HashMap<K,V>` |
| Sorted Map | (없음 — `sorted(dict.items())`) | `TreeMap<K,V>` |
| Hash Set | `set` | `HashSet<T>` |
| Sorted Set | (없음 — `sortedcontainers`) | `TreeSet<T>` |
| Tuple (immutable) | `tuple` | `record` (Java 14+) |
| Counter | `collections.Counter` | (직접 구현 — `Map<K, Integer>`) |
| Default Dict | `collections.defaultdict` | `getOrDefault()` 패턴 |
| Frozen Set | `frozenset` | `Collections.unmodifiableSet()` |

---

*다음 글:* *Python 의 *typing / pyright / mypy* 와 *Java 의 *static 타입* 의 *진짜 차이* — *런타임 vs 컴파일 시점의 *검증 비용 비교*.
