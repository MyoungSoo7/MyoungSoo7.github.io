---
layout: post
title: "*Python vs Java* — 같은 알고리즘 *다른 성능* 의 *7 가지 결정적 이유*"
date: 2026-06-11 10:30:00 +0900
categories: [algorithm, python, java, performance]
tags: [python, java, jvm, jit, gil, hashmap, hashset, timsort, recursion, garbage-collection, coding-test, big-o]
---

> 코딩테스트 사이트의 *같은 문제* 를 *Python* 으로 *2.3 초* 에 푼다. 같은 알고리즘을 *Java* 로 옮기면 *0.4 초* 에 끝난다. *알고리즘 복잡도* 는 *같은 O(n log n)*.
>
> *왜 *6 배* 차이가 나는가*?

그리고 그 반대 케이스 — *Java 로 짠 코드가 *Python 보다 *더 메모리* 를 쓰는* 케이스도 *존재* 한다. *어느 언어가 *어떤 알고리즘* 에 *유리한지* 가 *그렇게 단순하지 않다*.

이 글은 *같은 알고리즘 을 *두 언어 로 구현* 했을 때 *왜 성능이 달라지는가* 를 *7 가지 결정적 차원* 으로 풀어본다. 단순 syntax 비교가 아니라 *런타임 의 *구조적 차이* 가 *알고리즘 성능 에 *직접 반영* 되는 그림*.

---

## TL;DR

> *Python 과 Java 는 같은 알고리즘 을 다른 런타임 위에서 실행* 한다. *JIT 컴파일 / GC 모델 / 컬렉션 메모리 레이아웃 / 동시성 모델 / 재귀 한계* 의 *7 가지 차이* 가 *체감 성능* 에 *5~50 배* 까지 *영향*. *언어 선택* 은 *알고리즘 성격* 과 *제약 조건* 의 *함수*.

---

## 1. *Layer 1 — *반복문의 비용**

가장 *체감 차이가 큰* 부분.

### 1.1 *Python 의 *모든 줄이 *interpreter dispatch**

```python
total = 0
for i in range(1_000_000):
    total += i
```

- 매 `+=` 가 *bytecode 명령* 으로 *해석*
- `range`, `i`, `total` 모두 *PyObject* 로 *box 된 정수*
- 각 연산이 *함수 호출 + ref-count 증감 + GIL 확인*

CPython 의 *반복문 1 회 비용* : *수십 ns ~ 100 ns*.

### 1.2 *Java 의 *JIT-compiled 반복문**

```java
long total = 0;
for (int i = 0; i < 1_000_000; i++) {
    total += i;
}
```

- *primitive int* — 박싱 없음. *4 byte 의 스택 변수*
- *HotSpot C2 컴파일러* 가 *수십 번 호출 후 native code 로 컴파일*
- 컴파일 후 *반복문 1 회 = 1~2 ns* (CPU pipeline 가 *한 사이클 in*)

→ **Python : Java = 50 ~ 100 : 1** (단순 산술 반복문 기준).

### 1.3 *그래서 Python 의 *반복문은 *벡터화* 하라*

```python
# 느림
total = 0
for i in range(N):
    total += arr[i]

# 빠름 (C 구현 활용)
total = sum(arr)
total = np.sum(arr)  # 더 빠름 (SIMD)
```

`sum`, `numpy`, `pandas` 의 *C / Fortran 백엔드 호출* 은 *반복문 비용 우회*. Java 의 JIT 가 *자연스럽게 제공* 하는 것을 *Python 은 라이브러리로 의식적으로 호출* 해야 함.

---

## 2. *Layer 2 — *컬렉션의 *메모리 레이아웃**

### 2.1 *Python list — *PyObject 포인터 배열**

```python
arr = [1, 2, 3, 4]
```

내부 구조 :

```
arr  →  [length, allocated, ob_item ptr ─→  [PyObj*, PyObj*, PyObj*, PyObj*]]
                                              ↓        ↓        ↓        ↓
                                            int(1)  int(2)  int(3)  int(4)
```

- 각 원소가 *PyObject* (28 byte for int)
- list 본체 + 4 개의 PyObject = *약 150 byte* (32 byte list + 4×28 byte int)
- 정수 4 개에 *150 byte* — *Java 의 `int[4]` (16 byte) 의 *10 배**

### 2.2 *Java ArrayList<Integer> — *Boxed Integer 배열**

```java
List<Integer> arr = new ArrayList<>(List.of(1, 2, 3, 4));
```

- Java 의 `Integer` 는 *boxed int* (16 byte + header)
- ArrayList 내부 `Object[]` + 4 개 Integer = *약 80 byte*
- `int[]` 라면 *16 byte* (4 byte × 4 + 4 byte header padding)

### 2.3 *비교 표*

| 자료구조 | 4 개 정수 메모리 | 비고 |
|---|---|---|
| Python `list` | *~150 byte* | 모든 원소가 PyObject |
| Python `array.array("i", [...])` | *~80 byte* | primitive 배열 |
| Python `numpy.array([...], dtype=int32)` | *16 byte* | C buffer |
| Java `List<Integer>` (ArrayList) | *~80 byte* | Boxed Integer |
| Java `int[]` | *16 byte* | primitive 배열 |

*같은 논리적 자료구조가 언어 + 변형에 따라 10 배 메모리 차이*. *알고리즘의 공간 복잡도가 언어에 따라 재정의된다*.

---

## 3. *Layer 3 — *재귀와 스택*

### 3.1 *Python 의 *재귀 한계**

기본값 *1000*. 이걸 넘으면 `RecursionError`.

```python
import sys
sys.setrecursionlimit(10000)  # 늘릴 수 있지만 OS 스택 한계 따로
```

*DFS / 분할정복 / 동적계획법* 같은 깊은 재귀가 *Python 에서 치명적*. 보통 *반복 + 명시 스택* 으로 *재작성* 해야 한다.

### 3.2 *Java 의 *JVM 스택 크기**

JVM thread 당 *기본 1 MB stack* (Linux). `-Xss2m` 로 *늘릴 수 있다*. *재귀 깊이 수만 단계* 까지 *현실적*.

```java
java -Xss4m MyDFS  // 4 MB stack
```

### 3.3 *왜 Python 이 *재귀에 보수적* 인가*

Python 의 *함수 호출 1 회 비용* 이 *크다* (수 μs). *재귀 자체가 interpreter 입장에서 비싸다*. *반복문이 항상 우선* — *재귀 한계 작게 두는 게 의도된 디자인*.

Java 는 *JIT 이 tail call 도 일부 최적화* 하고 *함수 호출 비용이 작다* → 재귀 친화적. 다만 *공식 tail call optimization 은 없음* (Scala / Kotlin 같은 다른 JVM 언어는 일부 지원).

---

## 4. *Layer 4 — *해시 자료구조*

### 4.1 *Python dict — *Open addressing**

Python 3.7+ 의 dict 는 *insertion order* 유지 + *open addressing* 해시.

- *충돌 시* 다음 slot 으로 *probe*
- *load factor 2/3 넘으면* *resize*
- *해시 함수* 는 *secure (randomized seed)* — 같은 key 가 매번 다른 hash

### 4.2 *Java HashMap — *Chaining + Treeify**

Java 8+ 의 HashMap :

- *충돌 시* 같은 bucket 의 *linked list*
- *list 길이 8 넘으면* *red-black tree 로 변환* (worst-case O(log n) 보장)
- *해시 충돌 공격 (DoS)* 에 *내성*

### 4.3 *체감 성능 차이*

`dict.get(key)` 와 `map.get(key)` :

- Python : *수십 ns* (해시 + slot 접근)
- Java : *수 ns* (JIT 후)

10 배 차이. 다만 *Python dict 의 최적화가 매년 좋아짐*. Python 3.12 의 *PEP 659 (Specializing Adaptive Interpreter)* 가 *반복 접근 패턴을 학습* 해 *bytecode 를 전문화* — JIT 없이도 *수 배 빠르다*.

### 4.4 *Set 비교*

| 연산 | Python set | Java HashSet |
|---|---|---|
| add / contains | *O(1) avg* | *O(1) avg* |
| 충돌 시 worst | *O(n) — open addressing* | *O(log n) — treeify* |
| 메모리 (n=100만 정수) | *약 50 MB* | *약 60 MB (boxed)* |

*Java 의 primitive HashSet 은 표준 라이브러리에 없음* — *Eclipse Collections* 또는 *fastutil* 같은 external 라이브러리가 *primitive HashSet* 을 제공.

---

## 5. *Layer 5 — *정렬 알고리즘*

### 5.1 *둘 다 *Timsort 를 *기본**

흥미로운 *수렴* — *Python `list.sort()` 의 Timsort 가 2002 년 Tim Peters 작*. Java 가 *그걸 채택* 해 *Java 7+ 의 `Arrays.sort(Object[])` 의 기본*.

Timsort 의 특징 :

- *Merge sort 변형*
- *이미 정렬된 부분 (run)* 을 *감지해 최적화*
- *Worst-case O(n log n)*, *best-case O(n)* (정렬된 입력)

### 5.2 *Java 의 *Dual-Pivot Quicksort* (primitive 배열)*

`Arrays.sort(int[])` 는 *Dual-Pivot Quicksort* (Vladimir Yaroslavskiy, 2009).

- *Pivot 2 개로 3 분할*
- *quicksort 의 cache locality* + *primitive 의 cache line 최적화*
- *Timsort 보다 primitive 에선 더 빠름*

### 5.3 *실측 비교 (1 백만 랜덤 정수)*

| 구현 | 시간 |
|---|---|
| Python `sorted()` (Timsort) | *~150 ms* |
| Java `Arrays.sort(int[])` (Dual-Pivot) | *~70 ms* |
| Java `Collections.sort(List<Integer>)` (Timsort) | *~200 ms* (박싱 비용) |
| numpy `np.sort()` | *~30 ms* (SIMD + C) |

*Python 의 sorted 가 Java 의 primitive sort 보다 2 배 느림*. *Java 의 Boxed sort 가 primitive sort 보다 3 배 느림*. *numpy 가 전부 합쳐 가장 빠름*.

→ *Java 가 primitive 정렬에서 압도적*. *Python 은 numpy 우회가 유일한 근접 옵션*.

---

## 6. *Layer 6 — *문자열 다루기*

### 6.1 *둘 다 *불변 (immutable)*

`s = s + "x"` 는 *새 문자열 생성*. 매 반복마다 *O(len(s)) 비용*. 결과 : *O(n²)* — 흔한 *느린 코드*.

### 6.2 *해결 — 내장 *string builder 패턴**

```python
# Python — list + join
parts = []
for w in words:
    parts.append(w)
result = "".join(parts)  # O(n)
```

```java
// Java — StringBuilder
StringBuilder sb = new StringBuilder();
for (String w : words) {
    sb.append(w);
}
String result = sb.toString();  // O(n)
```

### 6.3 *String interning*

- *Python : 짧은 string (60 자 이하) + 식별자 패턴 자동 intern*
- *Java : String literal 은 자동 intern + `String.intern()` 명시 가능*

*같은 string 비교 시* `is` (Python) / `==` (Java) 는 *interned 면 O(1)*, *아니면 동작 다름*.

### 6.4 *String 비교 비용*

| 연산 | Python | Java |
|---|---|---|
| `==` / `equals` | *length 다르면 즉시 false, 같으면 byte 비교* | *동일* |
| hash | *PEP 456 — SipHash* | *javahash (간단)* |
| substring | *O(k) copy* | *Java 7 이후 *O(k) copy* (이전엔 O(1) view)* |

Java 6 까지는 substring 이 *O(1) view* — 메모리 누수 위험으로 *Java 7 부터 *O(k) copy* 로 변경*. *역사적 trade-off*.

---

## 7. *Layer 7 — *동시성 / 병렬*

### 7.1 *Python 의 *GIL — 진정한 병렬이 못 됨**

CPython 의 *Global Interpreter Lock* — *한 시점에 한 thread 만 bytecode 실행*. *멀티코어 CPU 를 못 살린다*.

해결책 :
- *multiprocessing* — 별도 *프로세스*. 통신 비용 큼
- *asyncio* — 단일 thread *coroutine*. I/O bound 에 적합
- *numpy / pandas / scipy* — *C 백엔드는 GIL 해제 후 동작*

*Python 3.13+ 의 no-GIL 빌드* (PEP 703) — 실험적. 곧 *기본 옵션* 가능성.

### 7.2 *Java 의 *진정한 멀티스레드**

JVM thread 는 *OS thread 1:1 매핑* — *멀티코어 직접 활용*.

- *synchronized* — 모니터 락
- *java.util.concurrent* — ConcurrentHashMap, ExecutorService 등 풍부
- *Virtual Threads (Java 21+)* — 경량 thread, Project Loom

### 7.3 *알고리즘에 미치는 영향*

| 알고리즘 | Python | Java |
|---|---|---|
| Merge sort 병렬화 | *멀티프로세스 (overhead 큼)* | *ForkJoinPool 한 줄* |
| 그래프 BFS 병렬 | *어렵다 (GIL)* | *자연스럽다* |
| 행렬 곱셈 | *numpy 가 *내부에서 BLAS 호출* (GIL 해제)* | *JIT + SIMD* |

*CPU-bound 병렬 알고리즘은 Java 가 자연스럽고 Python 은 우회 필요*.

---

## 8. *Layer 8 — *Garbage Collection 의 *알고리즘 영향**

### 8.1 *Python — *Reference counting + Cycle detector**

- 객체마다 *참조 카운트*. 0 되면 *즉시 해제*
- *순환 참조* 는 *주기적 detector* 가 처리
- *예측 가능한 GC* — *큰 일시 멈춤 없음*

### 8.2 *Java — *Generational GC**

- *Young generation + Old generation*
- *G1GC* (기본) / *ZGC* (저지연) / *Shenandoah*
- *Stop-the-world pause* — *수 ms ~ 수 100 ms*

### 8.3 *알고리즘이 받는 영향*

*대량의 임시 객체* (예: 매 반복마다 `new ArrayList`) :

- Python : *즉시 해제* — 메모리 *천천히 증가*
- Java : *Young heap 에 쌓이다 GC* — Young GC 마다 *짧은 멈춤*

*p99 응답시간 민감한 서비스* 에선 *Java 의 GC pause* 가 *Python 의 예측가능성* 보다 *덜 friendly*. 다만 *Python 의 느린 throughput* 이 *대부분 더 큰 문제*.

---

## 9. *실전 — *어느 언어가 *어느 알고리즘* 에 *유리한가**

### 9.1 *Python 이 유리한 경우*

- *프로토타이핑 / EDA / 데이터 분석* — 코드 짧고 빠른 작성
- *Numpy / Pandas / SciPy* 가 적용 가능한 *수치 계산* — *C 백엔드*
- *기계학습 / 통계* — *생태계 압도적*
- *간단한 알고리즘 + I/O 위주* — JIT 없어도 충분
- *작은 N* (입력 < 10⁵) — 6배 차이 나도 *체감 작음*

### 9.2 *Java 가 유리한 경우*

- *큰 N* (입력 > 10⁶) — JIT + primitive 의 *5~50 배 차이*
- *CPU bound + 멀티스레드*
- *재귀 깊이 큰 알고리즘* (DFS 깊은 그래프, divide & conquer)
- *메모리 효율 중요* — primitive 배열의 *10 배 절약*
- *long-running 서비스* — JIT warm-up 후 *극대 성능*

### 9.3 *코딩테스트 관점 — *시간 제한**

같은 문제, 같은 알고리즘 :

| 채점 | Python 제한 | Java 제한 | 비율 |
|---|---|---|---|
| 백준 | *3 배 보너스* | *1 배 기준* | 3 : 1 |
| LeetCode | *동일 시간* | *동일 시간* | *Python 에 불리* |
| 프로그래머스 | *5 배 보너스* | *1 배 기준* | 5 : 1 |

*경쟁 프로그래밍의 현실적 시간 차이가 3~5 배 보너스로 역사적 보정*. *LeetCode 처럼 보너스 없는 경우* *Python 으로 시간 초과 흔함*.

---

## 10. *Big-O 가 *거짓말 하는 순간**

이론적 복잡도 *O(n log n)* 인 두 구현이 *50 배 차이* 가 나는 *이유* :

- *상수 항 차이* (Java 의 cache-friendly primitive 배열 vs Python 의 boxed object 포인터 추적)
- *Memory access pattern* — *연속 메모리 (Java int[]) 가 cache hit rate 압도*
- *분기 예측* — JIT 가 *반복문 패턴 학습 후 분기 예측 최적화*
- *SIMD 자동 벡터화* — JIT 가 *수동 같은 반복문을 4~8 배 가속*

*Big-O 는 추세만 말해줄 뿐 체감 성능은 상수 항이 결정한다*. *그 상수 항이 런타임의 모든 layer 의 합산*.

---

## 11. *내 sparta-msa-project 의 사례*

*코딩테스트 채점 시스템* 운영 사례 :

- *judge-engine 자체* 는 *C++* (seccomp + cgroup, 0 latency target)
- *Java 제출* — JIT warm-up 못 함 → *primitive 배열 + 명시 StringBuilder* 권장
- *Python 제출* — *sys.stdin / readline + for 대신 list comprehension* 권장

같은 문제 *(N=10⁶ 정렬 + 이진 탐색)* 의 평균 실행 시간 :

- C++ : *0.08 초*
- Java : *0.4 초*
- Python (vanilla) : *2.3 초*
- Python (numpy) : *0.6 초*

*C++ : Java : Python = 1 : 5 : 30* (대략). *Python + numpy 는 Java 와 비슷*.

[lemuel-quant-core 의 R 모듈](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) 도 *벡터화된 R 코드 = numpy 의 R 버전* — 같은 패턴.

---

## 12. *교훈 — *언어는 *알고리즘의 *상수 항* 을 결정한다***

> *"알고리즘은 Big-O 가 전부가 아니다. *언어 의 *런타임 모델* 이 *알고리즘 의 체감 성능* 을 결정한다. 같은 알고리즘이 어느 언어에서 빠른지를 알면 *문제와 도구의 짝지음* 이 가능해진다*."*

*Python 의 읽기 좋고 생태계 풍부*. *Java 의 primitive + JIT + 진정한 멀티스레드*. *둘 다 그 고유의 강점으로 알고리즘의 상수 항을 다르게 만든다*.

다음에 알고리즘 문제를 만났을 때 — *Big-O 만 보지 말고 런타임의 7 가지 차원도 함께 보자*. 그게 *언어를 진짜 선택하는 시야* 다.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [R 은 클러스터에 *없다*](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · [HikariCP 의 5 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) · [백엔드 응답시간 + 모니터링](/2026/06/10/backend-latency-and-monitoring-truth.html) · *Python vs Java 알고리즘 (현재 글)*

*이 글은 [sparta-msa-project 의 judge-engine 운영 경험](https://github.com/MyoungSoo7/sparta-msa-project) + Java HotSpot internals + CPython 3.12 implementation details + 일반적 알고리즘 벤치마크 (백준 / LeetCode / 프로그래머스) 데이터를 기반으로 작성.*
