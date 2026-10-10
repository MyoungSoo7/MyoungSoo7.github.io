---
layout: post
title: "[CS300 #046] 해시 테이블과 충돌 해결 — 평균 O(1) 의 조건"
date: 2026-10-10 18:46:00 +0900
categories: [cs]
tags: [cs300, data-structures, hash-table, open-addressing, hashdos]
---

컴퓨터공학 300 주제 시리즈의 046번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

해시 테이블은 키를 해시 함수로 배열 인덱스로 바꿔 평균 O(1) 에 찾는 구조이고, 서로 다른 키가 같은 칸에 떨어지는 **충돌**을 체이닝이나 개방 주소법으로 처리하며, 적재율을 낮게 유지해야 그 O(1) 이 지켜진다.

## 왜 필요한가

배열은 인덱스를 알면 O(1) 이다. 그런데 우리가 실제로 들고 있는 것은 인덱스가 아니라 사용자 이름, URL, 파드 이름 같은 키다. 정렬된 배열이나 균형 트리로 찾으면 O(log n), 그냥 훑으면 O(n) 이다. 해시 테이블은 "키를 인덱스로 바꾸는 함수"를 하나 끼워 넣어 배열의 O(1) 을 키 검색에도 가져온다.

파이썬 `dict` 와 `set`, 자바 `HashMap`, 고의 `map`, 러스트 `HashMap` 이 모두 해시 테이블이다. 데이터베이스의 해시 조인, 캐시, 중복 제거, 카운팅, 라우팅 테이블까지 쓰지 않는 곳을 찾기가 더 어렵다. 그만큼 "평균 O(1)" 이 깨지는 조건을 알아야 한다. 그 조건을 공격자가 일부러 만들 수도 있기 때문이다.

## 핵심 개념

### 기본 구조

```
key ──hash()──▶ 정수 h ──(h mod m)──▶ 버킷 인덱스

  "apple"  → h=…3817 → 3817 mod 8 = 1
  "cherry" → h=…2209 → 2209 mod 8 = 1   ← 충돌!
```

좋은 해시 함수는 같은 키에 항상 같은 값을 주고(결정적), 서로 다른 키를 버킷에 고르게 흩뿌린다. 그리고 `a == b` 이면 반드시 `hash(a) == hash(b)` 여야 한다. 파이썬과 자바 모두 이 규칙을 언어 차원에서 요구한다. 거꾸로는 성립하지 않는다. 해시가 같아도 키는 다를 수 있다. 그래서 버킷에서 찾은 뒤에는 키를 다시 `==` 로 비교한다.

### 적재율(load factor)

**적재율 α = 원소 수 n / 버킷 수 m** 이다. α 가 커질수록 충돌이 많아진다. 그래서 모든 실용 구현은 α 가 기준을 넘으면 버킷 배열을 대략 2배로 키우고 모든 원소를 새 위치로 다시 넣는다(rehash). 동적 배열과 같은 분할 상환 논리로, 이 비용을 감안해도 삽입은 평균 O(1) 이다. 자바 `HashMap` 문서는 기본 적재율 0.75 가 시간과 공간 사이의 좋은 절충이며, 이를 넘으면 버킷 수를 약 두 배로 늘려 재해시한다고 적는다([Java SE 21 HashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html)).

### 충돌 해결 1: 체이닝(separate chaining)

각 버킷이 리스트를 들고, 같은 버킷에 떨어진 원소를 모두 거기 매단다.

```
버킷
 0 │ ∅
 1 │ ●→ ("apple",5) → ("cherry",6)
 2 │ ∅
 3 │ ●→ ("banana",6)
```

구현이 단순하고 α 가 1 을 넘어도 동작한다. 평균 체인 길이가 α 이므로 검색은 O(1 + α) 다. 단점은 노드 할당과 포인터 추적이다. 자바 `HashMap` 이 이 계열이다. 같은 해시를 가진 키가 몰리면 체인이 길어지는데, 자바 문서는 이를 완화하려고 키가 `Comparable` 이면 비교 순서를 써서 동률을 깨기도 한다고 적는다.

### 충돌 해결 2: 개방 주소법(open addressing)

모든 원소를 버킷 배열 자체에 넣는다. 칸이 차 있으면 정해진 규칙으로 다른 칸을 찾아간다(탐사, probing).

| 방식 | 다음 칸 | 특징 |
|---|---|---|
| 선형 탐사 | i, i+1, i+2, … | 캐시에 가장 유리. 원소가 뭉치는 1차 군집이 생긴다 |
| 이차 탐사 | i, i+1², i+2², … (또는 삼각수) | 1차 군집 완화 |
| 이중 해싱 | i, i+h₂, i+2h₂, … | 군집이 가장 적다. 해시를 두 번 계산 |

개방 주소법에서 삭제는 까다롭다. 칸을 그냥 비우면, 그 칸을 지나 더 뒤로 밀려났던 원소를 찾을 때 "빈칸을 만났으니 없다"고 잘못 끝난다. 그래서 **묘비(tombstone)** 표시를 남겨 "여기는 비었지만 탐색은 계속하라"고 알린다. 묘비가 쌓이면 성능이 떨어지므로 재해시 때 치운다.

선형 탐사에서 균일 해싱을 가정한 평균 탐사 수는 Knuth 의 분석으로 잘 알려져 있다. 실패한 검색은 약 ½(1 + 1/(1−α)²) 칸이다. α = 0.5 면 2.5칸, α = 0.9 면 50칸을 넘는다. 아래 실습에서 직접 확인한다. 개방 주소법 구현들이 적재율을 0.5~0.9 사이에서 보수적으로 관리하는 이유다.

### 현대 구현: Swiss Table

최근 언어 런타임은 개방 주소법을 더 다듬은 **Swiss Table** 설계를 많이 쓴다. 각 칸의 해시 일부(7비트 정도)를 별도의 제어 바이트 배열에 두고, SIMD 나 비트 연산으로 여러 칸을 한 번에 비교한다. 고는 1.24 에서 내장 `map` 을 Swiss Table 기반으로 완전히 새로 구현했다고 공식 블로그에서 밝혔다([Go Blog — Faster Go maps with Swiss Tables](https://go.dev/blog/swisstable)). 러스트 `HashMap` 문서도 이차 탐사와 SIMD 조회로 구현되었다고 적는다([Rust HashMap](https://doc.rust-lang.org/std/collections/struct.HashMap.html)).

### HashDoS: 평균이 최악이 될 때

O(1) 은 키가 고르게 흩어진다는 가정 위의 **평균**이다. 공격자가 해시 함수를 알면 모두 같은 버킷에 떨어지는 키를 대량으로 만들어 보낼 수 있다. 그러면 삽입 하나가 O(n), n 개 삽입이 O(n²) 이 되어 서버 CPU 가 녹는다. 웹 프레임워크가 요청 파라미터를 해시 테이블에 담는다는 점을 노린 공격이 2011년 여러 언어에 걸쳐 보고되었다([oCERT-2011-003](https://ocert.org/advisories/ocert-2011-003.html)).

대응은 해시 함수에 프로세스마다 다른 **비밀 시드**를 섞는 것이다. 파이썬은 `str` 과 `bytes` 의 해시를 기본적으로 무작위화하며, 문서는 이것이 dict 삽입의 최악 성능 O(n²) 을 노린 서비스 거부를 막기 위한 것이라고 설명한다([Python — Command line and environment, PYTHONHASHSEED](https://docs.python.org/3/using/cmdline.html)). 러스트 `HashMap` 은 기본적으로 무작위 시드를 쓰는 HashDoS 저항 알고리즘을 쓰며, 현재 기본값은 SipHash 1-3 이라고 문서에 적혀 있다. 그래서 파이썬에서 `set` 의 순회 순서는 실행할 때마다 달라질 수 있다. 순서에 의존하는 테스트가 가끔 깨지는 이유다.

### 파이썬 dict 의 순서

파이썬 `dict` 는 3.7 부터 삽입 순서 유지가 언어 차원에서 보장된다. 문서는 3.6 에서는 CPython 구현 세부였다고 적는다([Python — Built-in Types, dict](https://docs.python.org/3/library/stdtypes.html)). 해시 테이블이라고 해서 항상 순서가 없다고 단정하면 안 되고, 반대로 다른 언어의 맵이 순서를 지킨다고 가정해서도 안 된다. 고의 언어 명세는 `map` 순회 순서가 정해져 있지 않고 순회할 때마다 같다는 보장도 없다고 적는다([The Go Programming Language Specification](https://go.dev/ref/spec)).

## 직접 해 보기

묘비를 쓰는 선형 탐사 해시 맵을 만들고, 적재율별 실패 검색 탐사 수를 이론값과 비교한다.

```python
import random

class LinearProbingMap:
    _DELETED = object()                       # 묘비(tombstone)

    def __init__(self, cap=8):
        self.keys = [None] * cap
        self.vals = [None] * cap
        self.n = 0
        self.probes = 0                       # 들여다본 칸 수(통계용)

    def _slot(self, key):
        cap = len(self.keys)
        i = hash(key) % cap
        first_tomb = None
        while True:
            self.probes += 1
            k = self.keys[i]
            if k is None:                     # 빈칸: 키가 없다
                return (first_tomb if first_tomb is not None else i), False
            if k is self._DELETED:
                if first_tomb is None:
                    first_tomb = i
            elif k == key:
                return i, True
            i = (i + 1) % cap                 # 선형 탐사: 다음 칸

    def put(self, key, val):
        if (self.n + 1) / len(self.keys) > 0.5:   # 적재율 0.5 넘으면 2배
            self._resize(len(self.keys) * 2)
        i, found = self._slot(key)
        if not found:
            self.n += 1
        self.keys[i], self.vals[i] = key, val

    def get(self, key, default=None):
        i, found = self._slot(key)
        return self.vals[i] if found else default

    def delete(self, key):
        i, found = self._slot(key)
        if found:
            self.keys[i], self.vals[i] = self._DELETED, None
            self.n -= 1

    def _resize(self, cap):
        old = [(k, v) for k, v in zip(self.keys, self.vals)
               if k is not None and k is not self._DELETED]
        self.keys, self.vals, self.n = [None] * cap, [None] * cap, 0
        for k, v in old:
            self.put(k, v)

m = LinearProbingMap()
for w in ["apple", "banana", "cherry", "durian", "elder"]:
    m.put(w, len(w))
m.delete("banana")
print(m.get("cherry"), m.get("banana"), m.get("elder"))

# 적재율에 따른 평균 탐사 수 (실패 탐색) vs 이론값 ½(1 + 1/(1-α)²)
random.seed(1)
CAP = 1 << 16
for alpha in (0.25, 0.5, 0.75, 0.9):
    t = LinearProbingMap(CAP)
    keys = random.sample(range(10**9), int(CAP * alpha))
    for k in keys:
        i, _ = t._slot(k); t.keys[i] = k   # 확장 없이 직접 채움
    t.probes = 0
    misses = random.sample(range(10**9, 2 * 10**9), 20000)
    for k in misses:
        t._slot(k)
    theory = 0.5 * (1 + 1 / (1 - alpha) ** 2)
    print(f"α={alpha:.2f}  실측 {t.probes/len(misses):6.2f}칸   이론 {theory:6.2f}칸")
```

```
6 None 5
α=0.25  실측   1.39칸   이론   1.39칸
α=0.50  실측   2.49칸   이론   2.50칸
α=0.75  실측   8.24칸   이론   8.50칸
α=0.90  실측  58.65칸   이론  50.50칸
```

`banana` 를 지운 뒤에도 그 뒤에 밀려 들어갔을 수 있는 `cherry`, `elder` 가 잘 찾아진다. 묘비 덕분이다. 그리고 적재율 0.5 까지는 2~3칸이면 끝나지만 0.9 에서는 수십 칸으로 뛴다. 이론식은 테이블이 매우 클 때의 근사라 높은 적재율에서는 실측과 차이가 커진다. 그래도 "1 에 가까워지면 폭발한다"는 모양은 정확히 맞는다.

## 현업에서는

- **해시 가능한 키.** 파이썬에서 리스트를 dict 키로 못 쓰는 이유는 변경 가능하기 때문이다. 넣은 뒤 내용이 바뀌면 해시가 바뀌어 다시는 못 찾는다. 자바에서 `equals` 만 재정의하고 `hashCode` 를 안 하면 `HashMap` 이 같은 키를 다른 키로 취급한다. 둘 다 리뷰 단골 버그다.
- **미리 크기 잡기.** 수백만 개를 넣을 맵은 처음부터 용량을 잡아 두면 재해시가 사라진다. 재해시 동안의 지연 스파이크와 메모리 순간 최대치도 함께 없어진다.
- **요청 파라미터와 JSON.** 외부 입력을 해시 테이블에 담는 서버는 HashDoS 를 의식해야 한다. 언어 기본 해시가 시드를 쓰는지 확인하고, 파라미터 개수 상한을 둔다.
- **순서 의존 버그.** 테스트에서 `set` 을 문자열로 찍어 기댓값과 비교하는 코드는 해시 무작위화 때문에 간헐적으로 깨진다. 정렬해서 비교하는 게 맞다.

## 확인 문제

1. 적재율이 0.75 인 체이닝 해시 테이블에서 평균 체인 길이는?
2. 개방 주소법에서 삭제할 때 칸을 그냥 비우면 어떤 문제가 생기는가?
3. `a == b` 인데 `hash(a) != hash(b)` 인 클래스를 dict 키로 쓰면 어떻게 되는가?
4. 해시 함수에 비밀 시드를 섞는 목적은?
5. 선형 탐사에서 적재율을 0.5 에서 0.9 로 올리면 실패 검색 탐사 수는 이론상 몇 배쯤 되는가?

### 풀이

1. 평균 0.75 개(α 와 같다).
2. 그 칸을 지나 더 뒤에 자리 잡은 키를 찾을 때 빈칸에서 탐색이 멈춰 "없다"고 잘못 판단한다. 묘비로 해결한다.
3. 같은 키를 넣어도 다른 버킷으로 가서 중복 저장되거나, 넣은 키를 찾지 못한다.
4. 공격자가 같은 버킷에 몰리는 키를 미리 계산하지 못하게 해 O(n²) 서비스 거부(HashDoS)를 막는다.
5. 2.5칸에서 50.5칸으로 약 20배.

## 더 읽을거리 (References)

- Oracle, [Java SE 21 API — HashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html)
- The Go Blog, [Faster Go maps with Swiss Tables](https://go.dev/blog/swisstable)
- Python Documentation, [Command line and environment — PYTHONHASHSEED](https://docs.python.org/3/using/cmdline.html)
- The Rust Standard Library, [HashMap](https://doc.rust-lang.org/std/collections/struct.HashMap.html)
- Donald E. Knuth, *The Art of Computer Programming, Vol. 3: Sorting and Searching*, 2nd ed., Addison-Wesley, 1998 — 6.4 Hashing
