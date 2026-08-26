---
layout: post
title: "자바 · 파이썬 · 고 — 문법, 자료구조, 그리고 각자가 지불한 값"
date: 2026-08-27 02:29:41 +0900
categories: [engineering]
tags: [java, python, golang, data-structures, type-system, concurrency]
---

## 이 글의 방법

세 언어를 비교하는 글은 대개 "누가 빠른가"로 흐른다. 그 질문은 여기서 다루지 않는다.
중립 제3자가 수행한 세 언어 간 헤드투헤드 벤치마크로서 이 글이 인용할 만한 것을 찾지 못했고, 검증 불가능한 숫자를 옮겨 적는 것보다 없다고 말하는 편이 정확하다.

대신 이렇게 했다.

- **명세와 공식 문서만 인용한다.** 언어 스펙, PEP, JEP, 공식 API 문서. 블로그 요약본은 근거로 쓰지 않는다.
- **주장은 실행해서 확인한다.** 이 글의 코드와 출력은 전부 로컬에서 실제로 돌린 결과다 — OpenJDK 25.0.2, CPython 3.14.4, Go 1.26.2 (macOS).

> 이 블로그에는 [자바와 파이썬의 2자 비교](/2026/06/11/python-vs-java-data-structures-syntax-deep-comparison/)와
> [자바 · 코틀린 · 파이썬 · 고 입문 비교](/2026/07/01/nodejs-python-kotlin-golang-fundamentals/)가 이미 있다.
> 이 글은 거기서 다루지 않은 것 — **세 언어가 서로 다른 것을 포기해서 서로 다른 것을 얻었다는 구조** — 에 집중한다.

---

## 1. 같은 프로그램, 세 언어

먼저 비교할 대상을 고정한다. 세 프로그램이 하는 일은 동일하다.
불변 데이터 정의 → SKU별 수량 집계(정렬 출력) → 문자열을 수량으로 파싱(실패 처리 포함) → 동시 조회.

### Java

```java
import java.util.*;
import java.util.concurrent.*;

record Item(String sku, int qty) {}                  // 불변 데이터 — 컴파일러가 생성

public class Demo {
    sealed interface Result permits Ok, Err {}       // 합타입: 케이스가 닫혀 있다
    record Ok(int value) implements Result {}
    record Err(String reason) implements Result {}

    static Result parseQty(String raw) {
        try { return new Ok(Integer.parseInt(raw)); }
        catch (NumberFormatException e) { return new Err(raw + " 는 수량이 아니다"); }
    }

    public static void main(String[] args) throws Exception {
        List<Item> items = List.of(new Item("A-1", 2), new Item("B-2", 5), new Item("A-1", 3));

        Map<String, Integer> byS = new TreeMap<>();               // 키 정렬 유지
        for (Item it : items) byS.merge(it.sku(), it.qty(), Integer::sum);
        System.out.println("집계: " + byS);

        for (String raw : List.of("7", "일곱")) {
            String msg = switch (parseQty(raw)) {                 // 케이스 누락 시 컴파일 에러
                case Ok(int v)     -> "수량 " + v;
                case Err(String r) -> "실패: " + r;
            };
            System.out.println(msg);
        }

        try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {   // 가상 스레드
            var futures = new ArrayList<Future<String>>();
            for (String sku : byS.keySet()) futures.add(exec.submit(() -> sku + " 조회완료"));
            for (var f : futures) System.out.println(f.get());
        }
    }
}
```

### Python

```python
from dataclasses import dataclass
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

@dataclass(frozen=True)                # 불변 — 런타임에 강제된다(__setattr__ 차단)
class Item:
    sku: str
    qty: int

def parse_qty(raw: str) -> int | str:  # 애너테이션은 런타임에 검사되지 않는다
    try:
        return int(raw)
    except ValueError:
        return f"{raw} 는 수량이 아니다"

items = [Item("A-1", 2), Item("B-2", 5), Item("A-1", 3)]

agg = Counter()
for it in items:
    agg[it.sku] += it.qty
print("집계:", dict(sorted(agg.items())))

for raw in ("7", "일곱"):
    match parse_qty(raw):              # 구조적 패턴 매칭 (3.10+)
        case int() as v: print(f"수량 {v}")
        case str() as r: print(f"실패: {r}")

with ThreadPoolExecutor() as ex:       # GIL 빌드에서는 CPU 병렬이 아니다
    for r in ex.map(lambda s: f"{s} 조회완료", sorted(agg)):
        print(r)
```

### Go

{% raw %}
```go
type Item struct {                     // 값 타입 — 대입하면 복사된다
	SKU string
	Qty int
}

// 에러는 값이다. 시그니처에 드러나고, 무시하면 눈에 띈다.
func parseQty(raw string) (int, error) {
	n, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("%s 는 수량이 아니다: %w", raw, err)
	}
	return n, nil
}

func main() {
	items := []Item{{"A-1", 2}, {"B-2", 5}, {"A-1", 3}}

	agg := map[string]int{}
	for _, it := range items {
		agg[it.SKU] += it.Qty          // 없는 키는 제로값 0 에서 시작
	}
	keys := make([]string, 0, len(agg))
	for k := range agg {               // 맵 순회 순서는 명세상 미정 — 정렬은 직접
		keys = append(keys, k)
	}
	sort.Strings(keys)
	// ... 출력 ...

	for _, raw := range []string{"7", "일곱"} {
		if n, err := parseQty(raw); err != nil {
			fmt.Println("실패:", err)
		} else {
			fmt.Println("수량", n)
		}
	}

	var wg sync.WaitGroup
	out := make([]string, len(keys))
	for i, k := range keys {           // goroutine — OS 스레드가 아니다
		wg.Add(1)
		go func() { defer wg.Done(); out[i] = k + " 조회완료" }()
	}
	wg.Wait()
}
```
{% endraw %}

세 프로그램의 실제 출력은 같다(맵 출력 표기만 다름).

```
집계: {A-1=5, B-2=5}      # Java   (Python: {'A-1': 5, 'B-2': 5} / Go: map[A-1:5 B-2:5])
수량 7
실패: 일곱 는 수량이 아니다
A-1 조회완료
B-2 조회완료
```

같은 일을 하는데 **코드가 다른 이유** 가 이 글의 본론이다.

---

## 2. 타입 시스템 — 세 갈래

### 실험

같은 실수를 세 언어에 넣고 언제 걸리는지 봤다.

```java
static int twice(int n) { return n * 2; }
twice("셋");
```
```python
def twice(n: int) -> int: return n * 2
twice("셋")
```
```go
func twice(n int) int { return n * 2 }
twice("셋")
```

**실측 결과:**

| | 언제 | 무엇이 |
|---|---|---|
| Java | 컴파일 | `error: method twice cannot be applied to given types; required: int` |
| Go | 컴파일 | `cannot use "셋" (untyped string constant) as int value` |
| Python | **안 걸림** | `셋셋` 이 출력된다 |

파이썬이 `셋셋` 을 출력하는 이유가 중요하다. 애러가 아니라 **성공** 했다.
`"셋" * 2` 는 파이썬에서 완벽히 유효한 문자열 반복 연산이고, `-> int` 라는 애너테이션은 그걸 막지 않는다.

이건 CPython 의 결함이 아니라 **명시된 설계** 다. PEP 484 는 이렇게 못 박는다 — 애너테이션은 `__annotations__` 로 런타임에 접근 가능하지만 **런타임 타입 검사는 일어나지 않으며**, 별도의 오프라인 타입 체커의 존재를 전제한다.[^1]
그 전제 위에서 `mypy` · `pyright` 같은 체커가 성립한다. 즉 파이썬의 타입 안전성은 **언어가 아니라 툴체인이 제공** 하며, 툴체인을 CI 에 안 걸면 존재하지 않는다.

### 자바: 제네릭은 컴파일 타임에만 산다

자바는 정적 타입이지만 제네릭에는 구멍이 있다. 실행해 보면 드러난다.

```java
List<String> s = new ArrayList<>(); List<Integer> i = new ArrayList<>();
System.out.println("런타임 타입이 같은가: " + (s.getClass() == i.getClass()));
List raw = s; raw.add(42);
System.out.println(s.get(0));
```

```
런타임 타입이 같은가: true
s 의 클래스: java.util.ArrayList
Exception in thread "main" java.lang.ClassCastException:
        class java.lang.Integer cannot be cast to class java.lang.String
        at E.main(E.java:8)
```

`List<String>` 과 `List<Integer>` 는 런타임에 **같은 클래스** 다. 타입 인자는 지워진다.
그래서 raw type 으로 42 를 밀어넣는 게 (경고는 나지만) 통과하고, 폭발은 **전혀 관계없는 줄** 에서 일어난다. 컴파일러가 몰래 넣어 둔 캐스트가 터지는 것이다.

`List<T>` 를 `List<String>` 과 `List<Integer>` 로 오버로드할 수 없는 것도 같은 이유다. 자바 제네릭을 오래 쓰면 몸으로 아는 제약인데, 원인은 하나다.

### 고: 구조적 인터페이스 — 사용측이 정의한다

```go
type Speaker interface{ Speak() string }   // implements 선언이 없다

type Dog struct{}
func (Dog) Speak() string { return "멍" }

var s Speaker = Dog{}                      // 메서드 집합이 맞으면 그것으로 충족
```

`Dog` 는 자기가 `Speaker` 라고 말한 적이 없다. 그럴 필요가 없다 — 메서드 집합이 맞으면 충족이다.
결과적으로 **인터페이스를 구현체 옆이 아니라 소비자 옆에 정의** 하게 된다. 라이브러리가 콘크리트 타입을 반환해도, 내 패키지에서 내가 필요한 만큼만 인터페이스로 잘라 쓸 수 있다.

자바에서 같은 걸 하려면 어댑터를 쓰거나 원본을 고쳐야 한다. 대신 자바는 "이 클래스가 어떤 계약을 지키기로 했는가"가 선언부에 남는다. 정확히 맞바꾼 것이다.

| | 자바 | 파이썬 | 고 |
|---|---|---|---|
| 검사 시점 | 컴파일 | 런타임(사실상 미검사) + 외부 체커 | 컴파일 |
| 다형성 | 명목적 (`implements`) | 덕 타이핑 | 구조적 (암묵) |
| 제네릭 | 있음 / **타입 소거** | 애너테이션 뿐 (런타임 무효) | 있음 (1.18~)[^2] |
| 타입 안전의 소재지 | 언어 | **툴체인** | 언어 |

---

## 3. 자료구조 — 무엇이 내장이고 무엇이 진짜인가

### 각 언어가 기본으로 주는 것

| 개념 | Java | Python | Go |
|---|---|---|---|
| 가변 배열 | `ArrayList<E>` | `list` | `[]T` (슬라이스) |
| 고정 배열 | `T[]` | — (`array` 모듈) | `[N]T` |
| 해시 맵 | `HashMap<K,V>` | `dict` | `map[K]V` |
| 정렬 맵 | `TreeMap<K,V>` | — | — |
| 집합 | `HashSet<E>` | `set` | — (`map[T]struct{}`) |
| 불변 시퀀스 | `List.of(...)` | `tuple` | — |
| 큐/덱 | `ArrayDeque` | `collections.deque` | — (슬라이스로) |
| 힙 | `PriorityQueue` | `heapq` | `container/heap` |

**표에서 눈에 띄는 건 고의 빈칸이다.** 정렬 맵도, 집합도, 덱도 없다.
이건 누락이 아니라 방침이다. 고는 언어 차원의 자료구조를 슬라이스·맵·채널 셋으로 묶고, 나머지는 사용자가 만들거나 표준 라이브러리에서 가져오게 한다. 집합이 필요하면 `map[T]struct{}` 를 쓰는 관용구가 사실상의 표준이다.

작은 언어를 유지한 대가로 매번 손으로 쓰는 코드가 늘어난다. 위 예제에서 맵 키를 정렬하려고 슬라이스를 만들어 `sort.Strings` 를 부른 게 정확히 그 대가다 — 자바는 `TreeMap` 한 줄, 파이썬은 `sorted()` 한 번이면 끝난다.

### 구현이 무엇인지가 성능을 결정한다

내장 자료구조의 이름이 같아도 **구현이 다르면 다른 물건** 이다. 공식 문서가 직접 말하는 것들만 옮긴다.

- **`java.util.HashMap`** — 오라클 API 문서: 해시 함수가 원소를 버킷에 잘 분산시킨다는 가정 하에 `get` 과 `put` 에 **상수 시간 성능** 을 제공한다. 다만 컬렉션 뷰 순회는 **크기가 아니라 용량(버킷 수) + 크기** 에 비례하므로, 초기 용량을 과하게 잡으면 순회가 느려진다.[^3] 로드 팩터 기본값은 0.75.
- **CPython 의 `list`** — 파이썬 공식 FAQ: 리스트는 Lisp 식 연결 리스트가 아니라 **가변 길이 배열** 이며, 다른 객체를 가리키는 참조의 연속 배열이다. 그래서 `a[i]` 인덱싱 비용은 리스트 크기·인덱스 값과 무관하다.[^4] 리스트 앞쪽 삽입/삭제가 비싼 이유가 여기서 나온다.
- **`dict` 의 순서** — 3.7 부터 **삽입 순서 보존이 언어 명세의 공식 일부** 로 선언됐다.[^5] 3.6 에서는 구현 세부사항이었다. 이제는 기대도 된다.
- **고의 맵 순회 순서** — 반대다. 언어 명세가 **순서를 규정하지 않으며**, 공식 블로그는 한 번의 순회와 다음 순회가 같으리라는 보장도 없다고 명시한다. 안정적인 순서가 필요하면 별도 자료구조를 유지하라고 문서가 직접 말한다.[^6]

마지막 두 항목이 대비를 잘 보여 준다. **같은 "해시 맵"인데 한쪽은 순서를 계약으로 올렸고, 한쪽은 계약에서 내렸다.**
파이썬은 예측 가능성을 얻고 구현 자유를 잃었다. 고는 구현 자유를 얻고, 대신 순회 순서에 의존하는 코드가 조용히 깨지는 걸 **개발 중에 드러나게** 만들었다.

같은 맵을 같은 프로세스 안에서 네 번 순회한 실측 결과다.

```
$ go run r.go        $ go run r.go     # 다시 실행
cdeab                bcdea
abcde                deabc
eabcd                abcde
eabcd                abcde
```

한 프로세스 안에서도 매번 다르다. 순서에 기대는 코드는 테스트를 몇 번만 돌려도 깨진다 — 운영에 나가서 깨지는 대신에.

### 값이냐 참조냐

문법보다 사고방식을 더 많이 바꾸는 차이다.

고 명세는 값 표현을 명시한다 — 미리 선언된 타입, **배열**, 구조체의 값은 자기 완결적이며, 변수가 값 전체를 저장한다. 반면 포인터·함수·**슬라이스**·맵·채널 값은 공유될 수 있는 하부 데이터에 대한 참조를 담는다.[^7]

```go
type Item struct{ SKU string; Qty int }
a := Item{"A-1", 2}
b := a          // 복사다. b.Qty 를 바꿔도 a 는 안 바뀐다
arr := [3]int{1,2,3}
cp := arr       // 배열도 복사다
sl := []int{1,2,3}
al := sl        // 슬라이스는 하부 배열을 공유한다 — 여기서 사람들이 걸린다
```

자바와 파이썬에는 이 구분이 없다. 객체는 항상 참조로 다뤄지고, "복사"는 명시적으로 요청해야 한다(`clone()`, `copy.deepcopy()`, `List.copyOf()`).
고에서는 **기본이 복사** 이고 공유가 예외다. 동시성 코드에서 이 기본값의 방향이 갖는 의미가 크다 — 값 타입을 goroutine 에 넘기면 애초에 공유가 없다.

---

## 4. 동시성 — 셋이 가장 크게 갈라지는 곳

### 고: 언어에 내장된 동시성

goroutine 과 채널은 라이브러리가 아니라 **문법** 이다. `go f()` 는 키워드고, `chan T` 는 타입이며, 채널의 FIFO 보장과 버퍼 동작은 언어 명세에 적혀 있다.[^7]
동시성이 언어 설계의 1급 관심사였던 결과, 표준적인 동시 프로그램의 모양이 하나로 수렴한다.

위 예제에서 `for i, k := range keys` 안의 클로저가 `i` 와 `k` 를 그대로 캡처하는데도 올바르게 동작한다는 점을 짚어 둘 만하다. Go 1.22 부터 루프 변수가 **반복마다 새로 생성** 되기 때문이다. 그 전 버전에서 이 코드는 흔한 버그였다 — 언어가 자기 함정 하나를 명시적으로 없앤 사례다.

### 자바: 스레드를 싸게 만들어서 같은 곳에 도달했다

자바의 답은 다른 방향이었다. 스레드 모델을 바꾸는 대신 **스레드를 싸게** 만들었다.

JEP 444 는 가상 스레드를 JDK 21 에서 정식화하면서, 이것이 OS 가 아니라 JDK 가 제공하는 경량 스레드이며 **M:N 스케줄링** — 많은 수(M)의 가상 스레드를 적은 수(N)의 OS 스레드에 올리는 방식 — 이라고 설명한다. 그리고 이 접근이 다른 언어에서 성공했다는 근거로 **고의 goroutine 을 직접 지목** 한다.[^8]

중요한 단서도 같은 문서에 있다. 가상 스레드는 **더 빠른 스레드가 아니다.** 코드를 더 빨리 실행하지 않는다. 지연시간(latency)이 아니라 처리량(throughput), 즉 **규모** 를 위해 존재한다.[^8]
오라클 문서는 경험칙까지 준다 — 애플리케이션이 동시에 1만 개 이상의 가상 스레드를 갖는 일이 없다면, 가상 스레드로 이득을 볼 가능성이 낮다.

그래서 요청당 스레드(thread-per-request) 스타일을 버리지 않고도 확장이 가능해졌다. 리액티브로 갈아엎었던 코드를 다시 동기 스타일로 되돌릴 수 있게 된 것이 실무에서 가장 큰 변화다.

### 파이썬: GIL, 그리고 지금 진행 중인 일

CPython 의 GIL 은 여러 스레드가 동시에 파이썬 코드를 실행하지 못하게 한다. 그래서 위 예제의 `ThreadPoolExecutor` 는 I/O 대기에는 도움이 되지만 CPU 병렬은 아니다.

**여기가 지금 움직이고 있다.** 정확히 기록하면 이렇다.

- PEP 703 이 `--disable-gil` 빌드 구성을 도입했고, 3.13 에서 **명시적 실험 기능** 으로 들어갔다.[^9]
- PEP 779 가 다음 단계 진입 기준을 정했고, **Python 3.14 에서 free-threaded 빌드가 공식 지원(officially supported)** 상태가 됐다.[^10] 다만 여전히 **선택적 빌드** 이고 기본값이 아니다.
- 단일 스레드 성능 대가에 대해 3.14 릴리스 노트는 **플랫폼과 C 컴파일러에 따라 대략 5–10%** 라고 적는다.[^11] 이건 CPython 개발팀 자신의 측정치이므로 그렇게 읽어야 한다.
- 내 인터프리터가 어느 쪽인지는 직접 확인할 수 있다. 위 예제에 이 줄을 넣어 돌린 결과는 `False` 였다 — 일반 배포판은 여전히 GIL 빌드다.

```python
import sys; print(sys.version)          # "free-threading build" 문자열 포함 여부
print(sys._is_gil_enabled())            # 실행 중 GIL 활성 여부
```

| | 동시성 단위 | 언어 통합 | CPU 병렬 |
|---|---|---|---|
| Java | 플랫폼/가상 스레드 | 라이브러리 (`java.util.concurrent`) | 예 |
| Python | 스레드 / 프로세스 / async | 라이브러리 + `async`/`await` 문법 | GIL 빌드에선 아니오 · free-threaded 빌드는 3.14 부터 공식 지원 |
| Go | goroutine + 채널 | **문법** | 예 |

---

## 5. 에러 처리 — 세 가지 철학

```java
try { return new Ok(Integer.parseInt(raw)); }
catch (NumberFormatException e) { return new Err(...); }
```
```python
try: return int(raw)
except ValueError: return f"..."
```
```go
n, err := strconv.Atoi(raw)
if err != nil { return 0, fmt.Errorf("...: %w", err) }
```

자바와 파이썬은 예외를 던진다. 제어 흐름에서 벗어나므로 **정상 경로가 깨끗** 하다. 대신 어떤 함수가 무엇을 던지는지 호출부에서 보이지 않는다(자바의 검사 예외는 부분적인 예외인데, 그것 때문에 욕을 먹는 기능이기도 하다).

고는 에러를 **평범한 반환값** 으로 만든다. 시그니처에 드러나고, `if err != nil` 이 코드의 상당 부분을 차지한다. 장황하다는 비판이 정당한 만큼, "이 함수가 실패할 수 있는가"를 시그니처만 보고 안다는 이점도 정당하다.

실무적 차이 하나: 위 고 코드의 `%w` 는 원인 에러를 감싸서 `errors.Is` / `errors.As` 로 나중에 풀어볼 수 있게 한다. 실제 출력이 이렇게 나온다.

```
실패: 일곱 는 수량이 아니다: strconv.Atoi: parsing "일곱": invalid syntax
```

내 문맥과 하위 계층의 원인이 한 줄에 남는다. 자바의 `initCause`, 파이썬의 `raise ... from ...` 이 같은 역할을 한다.

---

## 6. 그래서 어디에 쓰는가

기술적 특성에서 바로 도출되는 것만 적는다.

**자바**
- 강점: 성숙한 정적 타입 + 압도적인 엔터프라이즈 생태계 + JIT + 성숙한 관측 도구(JFR·힙덤프). 가상 스레드로 동기 스타일 확장성까지 회복했다. 리팩터링 도구가 언어 중 가장 강한 축이다.
- 약점: 장황함(레코드·패턴 매칭으로 많이 줄었다), 제네릭 소거, 기동 시간과 메모리 발자국.
- 자리: 오래 사는 서버, 팀이 크고 코드가 오래 가는 곳, 도메인이 복잡한 곳.

**파이썬**
- 강점: 최단 거리로 동작하는 코드. 데이터·과학·ML 생태계는 대체재가 없다. REPL 과 노트북이 탐색적 작업의 사이클을 압도적으로 줄인다.
- 약점: 타입 안전이 **언어 밖** 에 있어서 규율(체커를 CI 에 거는 일)에 의존한다. GIL 은 완화 중이지만 아직 기본값이 아니다. 배포 시 런타임·의존성을 같이 날라야 한다.
- 자리: 데이터·ML·자동화·글루 코드, 그리고 요구사항이 아직 흔들리는 초기 단계.

**고**
- 강점: 작은 언어(스펙을 한 번에 읽을 수 있다), 정적 단일 바이너리, 빠른 컴파일, 언어에 박힌 동시성, 표준 툴(`gofmt`·`go vet`·레이스 검출기)이 논쟁을 없앤다.
- 약점: 표현력을 의도적으로 제한했다 — 표의 빈칸들, `if err != nil` 의 반복, 제네릭은 늦게(1.18) 왔고 여전히 보수적이다.
- 자리: 네트워크 서비스, CLI·에이전트, 인프라 도구. 컨테이너 이미지가 작아야 하는 곳.

### 고르는 기준은 사실 언어가 아니다

정직하게 말하면, 위 목록으로 결정되는 경우는 많지 않다. 실제로 결정하는 것은 대개 이쪽이다.

1. **이미 있는 코드** — 남의 언어로 다시 쓰는 비용은 거의 항상 이득보다 크다.
2. **팀이 아는 것** — 잘 모르는 언어의 "우월한 특성"은 실현되지 않는다.
3. **생태계** — ML 은 파이썬, 쿠버네티스 주변은 고, 엔터프라이즈 통합은 자바. 언어가 아니라 그 언어에 있는 라이브러리를 고르는 것이다.
4. **운영 형태** — 배포 단위가 바이너리 하나여야 하는가, JVM 을 띄울 수 있는가, 런타임을 함께 날라도 되는가.

언어 특성은 1~4 가 비겼을 때 쓰는 타이브레이커에 가깝다.

---

## 7. 한 문장으로

세 언어의 차이는 **무엇을 잘하느냐** 가 아니라 **무엇을 포기했느냐** 에서 나온다.

- **파이썬은 컴파일 타임 보장을 포기하고 속도(개발 속도)를 샀다.** 그래서 타입 안전을 원하면 언어 밖에서 사 와야 한다.
- **고는 표현력을 포기하고 단순성과 예측 가능성을 샀다.** 그래서 표의 빈칸들과 `if err != nil` 을 감수한다.
- **자바는 단순성을 포기하고 성숙도와 하위 호환을 샀다.** 그래서 타입 소거 같은 20년 전의 절충안을 지금도 안고 간다.

셋 다 합리적인 거래였고, 셋 다 청구서가 있다. **어느 청구서를 낼 수 있는지가 선택이다.**

## 이 글이 말하지 않은 것

- **성능 순위.** 위에서 말했듯 인용할 만한 중립 헤드투헤드 벤치마크를 찾지 못했다. 인용한 유일한 성능 수치(free-threaded 빌드의 5–10% 단일 스레드 대가)는 CPython 팀 자신의 측정치이며 그렇게 표시했다.
- **메모리 관리의 세부.** 셋 다 GC 언어지만 GC 설계(자바의 세대별·리전 기반 수집기, CPython 의 참조 카운팅 + 순환 검출, 고의 동시 마크·스윕)는 각각 글 한 편짜리다.
- **빌드·의존성 생태계.** Maven/Gradle · pip/uv · go modules 의 차이는 실무 체감이 큰데 여기서는 다루지 않았다.

---

## References

[^1]: Python, "PEP 484 – Type Hints". "While these annotations are available at runtime through the usual `__annotations__` attribute, no type checking happens at runtime." <https://peps.python.org/pep-0484/>
[^2]: The Go Team, "Go 1.18 Release Notes" — 타입 파라미터(제네릭) 도입. <https://go.dev/doc/go1.18>
[^3]: Oracle, "HashMap (Java SE 26 & JDK 26)", *Java Platform API Specification*. <https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/util/HashMap.html>
[^4]: Python, "Design and History FAQ — How are lists implemented in CPython?". <https://docs.python.org/3/faq/design.html>
[^5]: Python, "What's New In Python 3.7" — "the insertion-order preservation nature of `dict` objects has been declared to be an official part of the Python language spec." <https://docs.python.org/3/whatsnew/3.7.html>
[^6]: The Go Team, "Go maps in action", *The Go Blog*. <https://go.dev/blog/maps>
[^7]: "The Go Programming Language Specification" — 맵/채널 타입, 값의 표현. <https://go.dev/ref/spec>
[^8]: Ron Pressler & Alan Bateman, "JEP 444: Virtual Threads", OpenJDK. <https://openjdk.org/jeps/444> · 보조: Oracle, "Virtual Threads", *Java SE 21 Core Libraries*. <https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html>
[^9]: Sam Gross, "PEP 703 – Making the Global Interpreter Lock Optional in CPython". <https://peps.python.org/pep-0703/> · 현행 문서: "Python support for free threading". <https://docs.python.org/3/howto/free-threading-python.html>
[^10]: Thomas Wouters, Matt Page, Sam Gross, "PEP 779 – Criteria for supported status for free-threaded Python" (Final, 2025-06-16 승인). <https://peps.python.org/pep-0779/>
[^11]: Python, "What's New In Python 3.14" — free-threaded 모드의 단일 스레드 성능 대가는 "roughly 5-10%, depending on the platform and C compiler used". CPython 개발팀 자체 측정치. <https://docs.python.org/3/whatsnew/3.14.html>

본문의 코드와 출력은 **OpenJDK 25.0.2 · CPython 3.14.4 · Go 1.26.2 (darwin/amd64)** 에서 2026-08-27 에 직접 실행해 얻은 것이다.
