---
layout: post
title: "[CS300 #093] 캐시 — 사상 방식과 교체 정책, 주소 하나가 캐시 칸을 찾는 법"
date: 2026-10-10 19:33:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, cpu-cache, set-associative, lru]
---

컴퓨터공학 300 주제 시리즈의 093번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

캐시는 메모리 주소를 태그·인덱스·오프셋으로 쪼개 어느 칸에 담을지 정한다(사상 방식). 한 주소가 갈 수 있는 칸이 하나면 직접 사상, 몇 개 중 하나면 집합 연관, 아무 데나면 완전 연관이다. 칸이 다 찼을 때 누구를 내보낼지가 교체 정책이고, 쓰기를 언제 아래로 내려보낼지가 쓰기 정책이다.

## 왜 필요한가

앞 글(#092)에서 캐시 적중이냐 미스냐에 따라 접근 시간이 수십 배 달라지는 것을 봤다. 그런데 미스에도 종류가 있다. 캐시가 작아서 생기는 미스, 처음 보는 데이터라 생기는 미스, 그리고 **자리는 남는데 하필 같은 칸을 두고 다투느라** 생기는 미스. 마지막 것은 캐시 구조를 알아야만 보인다.

2의 거듭제곱 크기 행렬에서 열 방향 순회가 유독 느리거나, 특정 배열 크기에서만 성능이 꺼지는 현상이 이 충돌 미스에서 나온다. 그리고 LRU, FIFO 같은 교체 정책은 CPU 캐시뿐 아니라 레디스, CDN, 페이지 캐시, 애플리케이션 캐시 설계에 그대로 쓰이는 개념이다.

## 핵심 개념

### 주소 쪼개기

캐시는 라인(블록) 단위로 데이터를 담는다. 라인 크기 B 바이트, 집합 수 S 일 때 주소는 이렇게 나뉜다.

```
 ┌──────────────────────┬────────────────┬──────────────┐
 │         태그          │     인덱스      │    오프셋     │
 └──────────────────────┴────────────────┴──────────────┘
   나머지 상위 비트          log2(S) 비트      log2(B) 비트
   "집합 안의 누구인가"      "어느 집합인가"    "라인 안 몇 번째 바이트"
```

예: 라인 64B, 집합 64개면 오프셋 6비트, 인덱스 6비트, 나머지가 태그다. 각 캐시 라인은 데이터와 함께 태그, 유효 비트, (쓰기 백이면) 더티 비트를 저장한다. 적중 판정은 "인덱스로 집합을 고르고, 그 집합의 태그들과 주소의 태그를 비교" 하는 것이다.

### 세 가지 사상 방식

| 방식 | 한 주소가 갈 수 있는 칸 | 장점 | 단점 |
|---|---|---|---|
| 직접 사상 | 정확히 1개 | 비교기 1개, 빠르고 단순 | 충돌 미스가 많다 |
| N-웨이 집합 연관 | 집합 하나 안의 N개 중 아무 데나 | 충돌 감소, 현실적 비용 | 비교기 N개 |
| 완전 연관 | 전체 아무 데나 | 충돌 미스 없음 | 모든 태그를 동시에 비교해야 해 크게 만들기 어려움 |

직접 사상은 1-웨이 집합 연관이고, 완전 연관은 집합이 하나인 집합 연관이다. 실제 CPU 의 L1·L2·L3 는 대부분 집합 연관이며, 작은 TLB 같은 구조는 완전 연관에 가깝게 만들기도 한다. 구체적인 웨이 수는 CPU 마다 다르다.

### 미스의 세 종류 (3C)

| 종류 | 원인 | 줄이는 법 |
|---|---|---|
| 강제(Compulsory) | 처음 접근하는 데이터 | 더 큰 라인, 프리페치 |
| 용량(Capacity) | 작업 집합이 캐시보다 큼 | 더 큰 캐시, 작업 집합 줄이기(블로킹) |
| 충돌(Conflict) | 같은 집합에 몰림 | 연관도 높이기, 데이터 배치 바꾸기 |

멀티코어에서는 네 번째로 일관성 미스(#094)가 추가된다.

### 교체 정책

집합이 가득 찼는데 새 라인이 들어와야 하면 하나를 내보낸다.

| 정책 | 내보낼 대상 | 특징 |
|---|---|---|
| LRU | 가장 오래 사용되지 않은 것 | 시간 지역성에 잘 맞음. 웨이가 많으면 정확한 구현이 비쌈 |
| 의사 LRU(PLRU) | LRU 를 트리 비트 등으로 근사 | 하드웨어에서 흔히 쓰는 절충 |
| FIFO | 가장 먼저 들어온 것 | 단순하지만 자주 쓰는 데이터도 내보냄 |
| 무작위 | 아무거나 | 단순, 병적인 패턴에 강함 |
| 최적(Belady's MIN) | 앞으로 가장 늦게 쓰일 것 | 미래를 알아야 해 구현 불가. 비교 기준용 |

LRU 에도 약점이 있다. 캐시 용량보다 딱 한 줄 큰 데이터를 순환 접근하면, 항상 다음에 쓸 라인을 내보내므로 적중률이 0 이 된다. 아래 실험에서 확인한다.

### 쓰기 정책

| 상황 | 정책 | 동작 |
|---|---|---|
| 쓰기 적중 | Write-through | 캐시와 아래 층에 동시에 씀. 단순, 트래픽 많음 |
| | Write-back | 캐시에만 쓰고 더티 표시. 쫓겨날 때 아래로 씀. 트래픽 적음 |
| 쓰기 미스 | Write-allocate | 라인을 캐시로 가져온 뒤 씀(write-back 과 짝) |
| | No-write-allocate | 아래 층에 바로 씀(write-through 와 짝) |

현대 CPU 의 데이터 캐시는 보통 write-back + write-allocate 다.

## 직접 해 보기

### 1. 캐시 시뮬레이터

8라인짜리 장난감 캐시로 사상 방식과 교체 정책을 비교한다. python3 로 실행해 확인했다.

```python
from collections import OrderedDict

class Cache:
    """총 lines 개 라인, ways 웨이 집합 연관 캐시. 라인 크기 64B."""
    def __init__(self, lines, ways, policy="LRU", line=64):
        self.sets = lines // ways
        self.ways, self.policy, self.line = ways, policy, line
        self.data = [OrderedDict() for _ in range(self.sets)]
        self.hits = self.misses = 0

    def access(self, addr):
        block = addr // self.line             # 오프셋 떼기
        idx = block % self.sets               # 인덱스 -> 어느 집합
        tag = block // self.sets              # 태그 -> 집합 안에서 누구인지
        s = self.data[idx]
        if tag in s:
            self.hits += 1
            if self.policy == "LRU":
                s.move_to_end(tag)            # 최근 사용으로 갱신
            return
        self.misses += 1
        if len(s) >= self.ways:
            s.popitem(last=False)             # LRU: 가장 오래 안 쓴 것 / FIFO: 가장 먼저 들어온 것
        s[tag] = True

    def rate(self):
        return self.hits / (self.hits + self.misses)

LINES = 8                                     # 8 라인 x 64B = 512B 장난감 캐시
trace_conflict = [0, 512] * 50                # 같은 인덱스로 가는 두 주소를 번갈아
trace_cycle = [i * 64 for i in range(9)] * 20 # 용량보다 1줄 많은 순환
trace_hot = []                                # 자주 쓰는 3줄 + 가끔 오는 줄들
for i in range(200):
    trace_hot += [0, 64, 128, 64 * (3 + i % 12)]

for name, tr in [("conflict", trace_conflict), ("cycle9", trace_cycle), ("hot", trace_hot)]:
    row = []
    for ways, pol in [(1, "LRU"), (2, "LRU"), (8, "LRU"), (8, "FIFO")]:
        c = Cache(LINES, ways, pol)
        for a in tr:
            c.access(a)
        row.append(f"{ways}-way {pol}: {c.rate():.2f}")
    print(f"{name:9s}", " | ".join(row))
```

출력:

```
conflict  1-way LRU: 0.00 | 2-way LRU: 0.98 | 8-way LRU: 0.98 | 8-way FIFO: 0.98
cycle9    1-way LRU: 0.74 | 2-way LRU: 0.63 | 8-way LRU: 0.00 | 8-way FIFO: 0.00
hot       1-way LRU: 0.70 | 2-way LRU: 0.75 | 8-way LRU: 0.75 | 8-way FIFO: 0.62
```

세 가지가 보인다.

- **conflict**: 캐시는 거의 비어 있는데 직접 사상에서는 두 주소가 같은 칸을 두고 서로를 쫓아내 적중률 0 이다. 2-웨이만 돼도 해결된다. 전형적인 충돌 미스다.
- **cycle9**: 완전 연관 LRU 가 오히려 0 이다. 용량보다 한 줄 많은 순환에서 LRU 는 항상 곧 쓸 라인을 내보낸다. 직접 사상은 충돌이 한 집합에만 몰려 나머지는 적중한다. "더 좋은 정책" 은 접근 패턴에 달려 있다.
- **hot**: 자주 쓰는 라인이 있는 패턴에서는 LRU 가 FIFO 보다 낫다. FIFO 는 자주 쓰는 라인도 순서가 되면 내보낸다.

### 2. 실제 CPU: 행 순회 vs 열 순회

C 의 2차원 배열은 행 우선으로 저장된다. 같은 64MB 배열을 두 방향으로 더한다.

```c
#include <stdio.h>
#include <time.h>
#define N 4096
static int a[N][N];                       /* 64MB, 행 우선 저장 */
static double now(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}
int main(void) {
    long s = 0; double t;
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) a[i][j] = i ^ j;
    t = now();
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) s += a[i][j];  /* 행 순회 */
    printf("row-major:    %.3f s\n", now() - t);
    t = now();
    for (int j = 0; j < N; j++) for (int i = 0; i < N; i++) s += a[i][j];  /* 열 순회 */
    printf("column-major: %.3f s  (s=%ld)\n", now() - t, s);
    return 0;
}
```

x86-64 노트북급 CPU, `gcc -O1` 에서 한 번 측정한 결과다.

```
row-major:    0.034 s
column-major: 0.277 s  (s=68702699520)
```

행 순회는 한 번 가져온 64바이트 라인의 int 16개를 다 쓰고 넘어간다. 열 순회는 한 칸 갈 때마다 16KB(4096 × 4바이트)씩 건너뛰므로 라인마다 int 하나만 쓰고 버린다. 게다가 간격이 2의 거듭제곱이라 같은 집합에 몰리는 충돌 미스까지 겹친다. 연산 수는 같은데 8배 가까이 차이 났다.

## 현업에서는

- **배열 순회 방향**: 행렬, 이미지, 넘파이 배열은 저장 순서(C 순서·포트란 순서)대로 순회한다. 큰 행렬 곱은 블록 단위로 쪼개(타일링) 작업 집합을 캐시에 맞춘다.
- **소프트웨어 캐시의 교체 정책**: 레디스는 `maxmemory-policy` 로 LRU·LFU 근사 정책을 고르게 해 준다. 파이썬은 `functools.lru_cache` 를 제공한다. 순차 스캔 한 번에 캐시가 통째로 밀려나는 현상(cache pollution)은 CPU 캐시와 DB 버퍼 풀 모두에서 나타나며, 그래서 많은 시스템이 순수 LRU 대신 변형을 쓴다.
- **2의 거듭제곱 크기 주의**: 구조체 배열의 크기나 스트라이드가 큰 2의 거듭제곱이면 충돌 미스로 성능이 갑자기 떨어질 수 있다. 패딩을 조금 넣어 해결되는 경우가 있다.

## 확인 문제

1. 라인 64B, 집합 128개인 캐시에서 주소의 오프셋·인덱스 비트 수는.
2. 직접 사상 캐시에서 캐시가 거의 비어 있는데도 미스가 반복될 수 있는 이유는.
3. 용량이 4줄인 완전 연관 LRU 캐시에 A B C D E A B C D E ... 를 반복 접근하면 적중률은.
4. Write-back 캐시에서 더티 비트가 필요한 이유는.

### 풀이

1. 오프셋 6비트(2^6=64), 인덱스 7비트(2^7=128).
2. 서로 다른 주소가 같은 인덱스로 사상되면 한 칸을 두고 서로를 쫓아내기 때문이다(충돌 미스).
3. 0. 매번 다음에 쓸 라인이 가장 오래전에 쓴 라인이라 쫓겨난다.
4. 쫓겨날 때 아래 층에 다시 써야 하는 수정된 라인인지 구별하기 위해서다. 깨끗한 라인은 그냥 버리면 된다.

## 더 읽을거리 (References)

- Ulrich Drepper, [What Every Programmer Should Know About Memory](https://akkadia.org/drepper/cpumemory.pdf), 2007 (3장 CPU Caches)
- [Computer Systems: A Programmer's Perspective — 저자 공식 사이트](https://csapp.cs.cmu.edu/) (6장)
- Python 공식 문서, [functools — lru_cache](https://docs.python.org/3/library/functools.html)
- L. A. Belady, "A study of replacement algorithms for a virtual-storage computer", *IBM Systems Journal* 5(2), 1966.
