---
layout: post
title: "[CS300 #059] LRU 캐시 구현 — 해시 맵과 이중 연결 리스트의 조합"
date: 2026-10-10 18:59:00 +0900
categories: [cs]
tags: [cs300, data-structures, lru-cache, cache-eviction, linked-hash-map]
---

컴퓨터공학 300 주제 시리즈의 059번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

LRU(Least Recently Used) 캐시는 용량이 차면 가장 오래 안 쓴 항목을 버리는 캐시로, 키 → 노드를 찾는 해시 맵과 사용 순서를 유지하는 이중 연결 리스트를 함께 써서 조회·삽입·퇴출을 모두 O(1) 에 한다.

## 왜 필요한가

캐시는 비싼 결과(디스크 읽기, DB 질의, 원격 호출, 무거운 계산)를 가까운 곳에 저장해 두는 장치다. 그런데 캐시 공간은 유한하다. 꽉 차면 무언가를 버려야 하고, **무엇을 버리느냐**가 적중률을 정한다.

LRU 는 "최근에 쓴 것은 곧 다시 쓸 가능성이 높다"는 시간 지역성에 기대는 정책이다. 단순하고 대부분의 작업 부하에서 잘 동작해서 CPU 캐시, 운영체제 페이지 캐시, 데이터베이스 버퍼 풀, 웹 캐시, 애플리케이션 메모리 캐시까지 가장 널리 쓰이는 기본값이다.

자료구조 관점에서 LRU 캐시는 이 파트의 종합 문제다. 해시 테이블(046편)만으로는 순서를 모르고, 연결 리스트(042편)만으로는 찾는 데 O(n) 이다. 둘을 엮어야 모든 연산이 O(1) 이 된다. 그래서 면접에서도 단골이다.

## 핵심 개념

### 필요한 연산

| 연산 | 동작 |
|---|---|
| `get(key)` | 있으면 값을 돌려주고, 그 항목을 "가장 최근 사용"으로 표시 |
| `put(key, val)` | 넣거나 갱신하고 "가장 최근 사용"으로 표시. 용량 초과면 가장 오래 안 쓴 항목 퇴출 |

세 가지가 모두 O(1) 이어야 한다. ① 키로 항목 찾기, ② 항목을 순서의 맨 앞으로 옮기기, ③ 순서의 맨 뒤 항목 빼기.

### 구조: 해시 맵 + 이중 연결 리스트

```
 해시 맵                    이중 연결 리스트 (사용 순서)
┌──────┬─────┐
│ "D"  │  ●──┼───┐      head ⇄ [D] ⇄ [A] ⇄ [C] ⇄ (head)
│ "A"  │  ●──┼───┼──┐          최근 ◀────────────▶ 오래됨
│ "C"  │  ●──┼───┼──┼──┐               ▲ 퇴출 대상은 맨 뒤
└──────┴─────┘   ▼  ▼  ▼
               노드를 직접 가리킴
```

- ① 해시 맵이 키로 **노드를 바로** 찾는다. 평균 O(1).
- ② 이중 연결 리스트라서 노드를 손에 쥐고 있으면 그 자리에서 떼어 내(O(1)) 맨 앞에 붙일(O(1)) 수 있다. 단일 연결 리스트면 앞 노드를 찾느라 O(n) 이 된다.
- ③ 맨 뒤 노드가 가장 오래 안 쓴 항목이다. 떼어 내고, 노드에 저장해 둔 **키**로 해시 맵에서도 지운다. 노드에 키를 함께 넣는 이유가 이것이다.

042편에서 본 센티널 노드를 쓰면 빈 리스트, 첫 노드, 마지막 노드의 특수 처리가 사라진다.

### 표준 라이브러리에는 이미 있다

- **자바 `LinkedHashMap`**: 해시 테이블에 이중 연결 리스트를 얹은 구조다. 문서는 마지막 접근 순서로 순회하는 **접근 순서(access-order)** 생성자가 있으며 "LRU 캐시를 만들기에 적합하다"고 적고, `removeEldestEntry` 를 재정의하면 새 항목을 넣을 때 오래된 항목을 자동으로 지우는 정책을 줄 수 있다고 설명한다([Java SE 21 LinkedHashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedHashMap.html)).
- **파이썬 `OrderedDict`**: 문서는 `OrderedDict` 가 잦은 재정렬을 일반 `dict` 보다 잘 처리하며 이 덕분에 여러 종류의 LRU 캐시 구현에 알맞다고 하고, `move_to_end` 와 `popitem(last=False)` 를 제공한다([Python collections.OrderedDict](https://docs.python.org/3/library/collections.html)).
- **파이썬 `functools.lru_cache`**: 함수 결과를 인자 기준으로 캐시하는 데코레이터다. `cache_info()` 로 적중·실패 횟수와 크기를 볼 수 있어 `maxsize` 를 조정하는 데 쓴다고 문서에 적혀 있다([Python functools](https://docs.python.org/3/library/functools.html)).

### LRU 의 약점: 순차 스캔

LRU 는 "최근에 쓴 것 = 곧 또 쓸 것"이 틀리는 패턴에 약하다. 대표가 **순차 스캔**이다. 캐시보다 큰 데이터를 처음부터 끝까지 반복해서 읽으면, 각 항목이 다시 쓰이기 직전에 정확히 퇴출되어 적중률이 0 이 된다. 한 번만 읽는 대량 스캔(백업, 통계 배치)이 자주 쓰는 데이터를 캐시에서 다 밀어내는 **캐시 오염**도 같은 원리다.

그래서 실제 시스템은 LRU 를 변형한다.

| 변형 | 아이디어 |
|---|---|
| LRU-K / 2Q | 한 번 쓰인 것과 두 번 이상 쓰인 것을 분리해, 한 번 스캔된 항목이 자주 쓰는 항목을 밀어내지 못하게 |
| LFU | 최근성 대신 사용 빈도로 퇴출 |
| CLOCK | 원형 리스트와 참조 비트 하나로 LRU 를 근사. 접근마다 리스트를 고치지 않아 싸다 |
| 표본 근사 LRU | 몇 개를 무작위로 골라 그중 가장 오래된 것을 퇴출 |

### 동시성

`get` 도 리스트 순서를 바꾸는 **쓰기**다. 그래서 여러 스레드가 쓰는 LRU 캐시는 읽기에도 락이 필요하고, 그 락이 병목이 되기 쉽다. 캐시를 여러 조각(shard)으로 나누거나, 접근 기록을 버퍼에 모았다가 한꺼번에 반영하거나, CLOCK 처럼 순서 갱신이 싼 근사를 쓴다.

## 직접 해 보기

센티널 이중 연결 리스트와 dict 로 LRU 캐시를 만들고, 표준 라이브러리 판과 비교한 뒤, 접근 패턴별 적중률을 잰다.

```python
class _Node:
    __slots__ = ("key", "val", "prev", "next")
    def __init__(self, key=None, val=None):
        self.key, self.val, self.prev, self.next = key, val, None, None

class LRUCache:
    """해시 맵(키 → 노드) + 이중 연결 리스트(사용 순서). get/put 모두 O(1)."""
    def __init__(self, capacity):
        self.cap = capacity
        self.map = {}
        self.head = _Node()                       # 센티널: head.next = 가장 최근
        self.head.prev = self.head.next = self.head
        self.hits = self.misses = 0

    def _unlink(self, n):
        n.prev.next, n.next.prev = n.next, n.prev

    def _push_front(self, n):
        n.prev, n.next = self.head, self.head.next
        self.head.next.prev = n
        self.head.next = n

    def get(self, key):
        n = self.map.get(key)
        if n is None:
            self.misses += 1
            return None
        self.hits += 1
        self._unlink(n); self._push_front(n)       # 방금 썼으니 맨 앞으로
        return n.val

    def put(self, key, val):
        n = self.map.get(key)
        if n:
            n.val = val
            self._unlink(n); self._push_front(n)
            return
        if len(self.map) == self.cap:
            lru = self.head.prev                   # 맨 뒤 = 가장 오래 안 쓴 것
            self._unlink(lru)
            del self.map[lru.key]
        n = _Node(key, val)
        self.map[key] = n
        self._push_front(n)

    def order(self):
        out, n = [], self.head.next
        while n is not self.head:
            out.append(n.key); n = n.next
        return out

c = LRUCache(3)
for k in "ABC":
    c.put(k, k.lower())
c.get("A")                 # A 를 최근으로
c.put("D", "d")            # 꽉 참 → 가장 오래 안 쓴 B 퇴출
print("순서(최근→오래):", c.order(), " B:", c.get("B"))

# 표준 라이브러리 두 가지
from collections import OrderedDict
from functools import lru_cache

class OD_LRU(OrderedDict):
    def __init__(self, cap): super().__init__(); self.cap = cap
    def get_(self, k):
        if k not in self: return None
        self.move_to_end(k); return self[k]
    def put_(self, k, v):
        self[k] = v; self.move_to_end(k)
        if len(self) > self.cap: self.popitem(last=False)

o = OD_LRU(3)
for k in "ABC": o.put_(k, k.lower())
o.get_("A"); o.put_("D", "d")
print("OrderedDict 판:", list(o.keys()))

@lru_cache(maxsize=128)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)
print("fib(80) =", fib(80), fib.cache_info())

# 접근 패턴에 따른 적중률: 상위 20% 키가 요청의 80% 를 차지하는 경우 vs 순차 스캔
import random
rng = random.Random(0)
hot, cold = list(range(200)), list(range(200, 1000))
skewed = [rng.choice(hot) if rng.random() < 0.8 else rng.choice(cold) for _ in range(100_000)]
scan = [i % 1000 for i in range(100_000)]          # 1000개를 계속 돌며 순차 접근
for name, reqs in [("쏠린 접근", skewed), ("순차 스캔", scan)]:
    c = LRUCache(300)
    for k in reqs:
        if c.get(k) is None:
            c.put(k, True)
    print(f"{name}: 용량 300 / 키 1000  적중률 {c.hits / len(reqs):.1%}")
```

```
순서(최근→오래): ['D', 'A', 'C']  B: None
OrderedDict 판: ['C', 'A', 'D']
fib(80) = 23416728348467685 CacheInfo(hits=78, misses=81, maxsize=128, currsize=81)
쏠린 접근: 용량 300 / 키 1000  적중률 75.9%
순차 스캔: 용량 300 / 키 1000  적중률 0.0%
```

직접 만든 판과 `OrderedDict` 판이 같은 결과를 냈다(출력 방향만 반대다. 직접 만든 판은 최근→오래, `OrderedDict` 는 오래→최근). `lru_cache` 를 붙인 피보나치는 서로 다른 인자 81개를 한 번씩만 계산했고 나머지 78번은 캐시에서 가져왔다. 캐시 없이 재귀로 계산하면 fib(80) 은 사실상 끝나지 않는다.

마지막 실험이 LRU 의 성격을 보여 준다. 키 1000개 중 30%만 담을 수 있는 캐시인데, 요청이 인기 키 200개에 쏠린 경우에는 적중률이 76% 다. 반면 1000개를 순서대로 계속 도는 스캔에서는 0% 다. 같은 캐시, 같은 용량이라도 접근 패턴에 따라 결과가 극과 극이다.

## 현업에서는

- **Redis 의 근사 LRU.** Redis 는 `maxmemory` 에 닿으면 `allkeys-lru` 같은 정책으로 키를 퇴출한다. 문서는 Redis 의 LRU 가 정확한 구현이 아니라 근사이며, 소수의 키를 무작위로 표본 추출해 그중 마지막 접근이 가장 오래된 것을 퇴출한다고 설명한다([Redis — Key eviction](https://redis.io/docs/latest/develop/reference/eviction/)). 키마다 연결 리스트 포인터 두 개를 두지 않아 메모리를 아끼는 선택이다. 같은 문서는 일부 키가 나머지보다 훨씬 자주 접근될 때 `allkeys-lru` 가 좋은 기본값이라고 권한다.
- **운영체제 페이지 캐시.** 리눅스 커널 문서에는 메모리 압박 아래에서 페이지 회수를 최적화하는 대안 LRU 구현인 Multi-Gen LRU 가 설명되어 있다([Linux Kernel — Multi-Gen LRU](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)). 같은 문서는 페이지 회수가 커널의 캐싱 정책을 정한다고 적는다. 이름 그대로 페이지를 세대(generation)로 나눠 관리하는 방식이라, 접근마다 순서를 고치는 정확한 LRU 가 아니라 그 근사다.
- **스캔이 캐시를 망칠 때.** 야간 배치나 백업이 돈 다음 날 아침 서비스 지연이 튀는 현상은 캐시 오염을 의심할 만하다. 배치용 질의는 캐시를 우회하게 하거나, 스캔에 강한 정책(2Q 계열)을 쓰는 캐시를 고른다.
- **`lru_cache` 주의점.** 인자가 해시 가능해야 하고, 인스턴스 메서드에 붙이면 `self` 가 키에 들어가 인스턴스가 캐시에 붙잡혀 메모리가 해제되지 않을 수 있다. 크기 제한 없는 `cache` 는 장시간 도는 서버에서 메모리 누수처럼 보일 수 있다.

## 확인 문제

1. 용량 2 인 LRU 캐시에 put(1), put(2), get(1), put(3), get(2), get(3), get(1) 을 하면 각 get 의 결과(적중/실패)는?
2. LRU 캐시에 단일 연결 리스트를 쓰면 어떤 연산이 O(1) 이 아니게 되는가?
3. 리스트 노드에 값뿐 아니라 키도 저장하는 이유는?
4. 캐시 용량보다 큰 데이터를 순차적으로 반복해서 읽을 때 LRU 의 적중률이 0 에 가까워지는 이유는?
5. Redis 가 정확한 LRU 대신 표본 추출 근사를 쓰는 이유로 짐작할 수 있는 것은?

### 풀이

1. put(3) 때 가장 오래 안 쓴 2 가 퇴출된다. get(2) 실패, get(3) 적중, get(1) 적중. (첫 get(1) 도 적중)
2. 임의 노드를 떼어 내는 것. 앞 노드를 찾으려면 처음부터 따라가야 해서 O(n) 이 된다.
3. 맨 뒤 노드를 퇴출할 때 해시 맵에서도 그 항목을 지워야 하는데, 노드만 보고 키를 알아야 하기 때문이다.
4. 어떤 항목이 다시 요청될 때쯤이면 그 사이에 캐시 용량보다 많은 다른 항목이 들어와, 그 항목은 이미 가장 오래 안 쓴 것으로 퇴출된 뒤다.
5. 모든 키에 순서 리스트 포인터를 두는 메모리 비용과 접근마다 리스트를 고치는 비용을 피하면서, 표본 크기로 정확도를 조절할 수 있기 때문이다.

## 더 읽을거리 (References)

- Oracle, [Java SE 21 API — LinkedHashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/LinkedHashMap.html)
- Python Documentation, [functools — lru_cache](https://docs.python.org/3/library/functools.html), [collections — OrderedDict](https://docs.python.org/3/library/collections.html)
- Redis Documentation, [Key eviction](https://redis.io/docs/latest/develop/reference/eviction/)
- The Linux Kernel documentation, [Multi-Gen LRU](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)
