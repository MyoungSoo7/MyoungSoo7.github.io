---
layout: post
title: "[CS300 #112] 페이지 교체 알고리즘 — 메모리가 찼을 때 누구를 내보낼까"
date: 2026-10-10 19:52:00 +0900
categories: [cs]
tags: [cs300, operating-systems, page-replacement, lru, clock]
---

컴퓨터공학 300 주제 시리즈의 112번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

물리 메모리가 가득 찬 상태에서 새 페이지가 필요하면 기존 페이지 하나를 내보내야 하고, 앞으로 가장 늦게 쓰일 페이지를 고르는 OPT 를 이상으로 삼아 FIFO, LRU, 그리고 LRU 를 싸게 근사하는 CLOCK 같은 알고리즘이 쓰인다.

## 왜 필요한가

110번 글의 요구 페이징 덕분에 프로세스는 실제 메모리보다 큰 주소 공간을 쓸 수 있다. 대가는 메모리가 찼을 때 무엇인가를 디스크(스왑 또는 원래 파일)로 내보내야 한다는 것이다. 잘못 고르면 방금 내보낸 페이지를 곧바로 다시 읽어 와야 한다.

비용 차이가 크다. 메모리 접근은 나노초 단위, 디스크에서 페이지를 읽는 것은 SSD 라도 마이크로초 단위, HDD 라면 밀리초 단위다. 페이지 폴트 비율이 아주 조금만 올라가도 평균 메모리 접근 시간이 몇 배로 뛴다. 그래서 교체 정책은 운영체제 성능의 핵심이다.

같은 문제는 CPU 캐시, 데이터베이스 버퍼 풀, Redis, CDN 캐시에서도 똑같이 나온다. "한정된 빠른 공간에 무엇을 남길까"라는 질문의 운영체제 버전이다.

## 핵심 개념

### 평가 방법: 참조열과 페이지 폴트 수

알고리즘은 페이지 번호의 나열(참조열)과 프레임 수가 주어졌을 때 페이지 폴트가 몇 번 나는지로 비교한다. 폴트가 적을수록 좋다.

### OPT (Belady 의 최적 알고리즘)

**앞으로 가장 오랫동안 쓰이지 않을 페이지**를 내보낸다. 벨레이디(L. A. Belady)가 1966년 논문에서 다룬 이 정책은 폴트 수가 이론적 최소다. 하지만 미래를 알아야 하므로 실제로 구현할 수 없다. 다른 알고리즘이 얼마나 좋은지 재는 **기준선**으로 쓴다.

### FIFO

가장 먼저 들어온 페이지를 내보낸다. 큐 하나로 구현되어 단순하다. 그러나 오래 있었다는 것이 덜 중요하다는 뜻은 아니다. 자주 쓰는 페이지도 순서가 되면 쫓겨난다.

FIFO 에는 **벨레이디의 모순(Belady's anomaly)** 이 있다. 프레임을 늘렸는데 폴트가 **늘어나는** 경우가 있다. 아래 실험에서 직접 확인한다.

### LRU (Least Recently Used)

**가장 오랫동안 쓰이지 않은 페이지**를 내보낸다. "최근에 안 쓴 것은 앞으로도 안 쓸 것"이라는 시간 지역성 가정이다. 대체로 OPT 에 가깝게 동작하고 벨레이디의 모순이 없다(스택 알고리즘이기 때문에 프레임 k 개일 때의 내용이 항상 k+1 개일 때의 부분집합이다).

문제는 비용이다. 정확한 LRU 는 **모든 메모리 접근마다** 순서를 갱신해야 한다. 하드웨어가 매 접근에 타임스탬프를 남기거나 리스트를 재정렬하는 것은 현실적이지 않다.

### CLOCK (Second Chance)

하드웨어가 이미 제공하는 **참조 비트(Accessed bit)** 만으로 LRU 를 근사한다.

```
         +---+
    +--> | A | ref=1        시계 바늘이 가리키는 페이지를 본다
    |    +---+              ref=1 이면 0 으로 지우고 다음으로 (두 번째 기회)
  +---+         +---+       ref=0 이면 그 페이지를 내보낸다
  | D |         | B |
  |ref0|        |ref1|
  +---+         +---+
    ^    +---+    |
    +--- | C | <--+
         +---+ ref=0
```

페이지에 접근할 때마다 하드웨어가 참조 비트를 1 로 켠다. 교체가 필요하면 바늘을 돌리며 1 은 0 으로 지우고, 처음 만나는 0 을 내보낸다. 최근에 쓴 페이지는 한 바퀴 동안 살아남는다. 여기에 **Dirty 비트**까지 보아 수정되지 않은 페이지(디스크에 다시 쓸 필요가 없는 페이지)를 우선 내보내는 변형도 있다.

### 리눅스는 실제로 무엇을 하나

리눅스는 페이지를 **익명 메모리**(힙, 스택)와 **파일 기반 페이지**(페이지 캐시)로 나누어 관리하고, 전통적으로 각각을 active/inactive 두 개의 LRU 리스트로 다뤘다. 한 번 쓰인 페이지는 inactive 에 들어가고, 다시 쓰이면 active 로 승격된다. 한 번 읽고 마는 대용량 스캔이 자주 쓰는 페이지를 몰아내지 못하게 하려는 구조다. 최근 커널에는 세대(generation) 단위로 더 세밀하게 나누는 **MGLRU(Multi-Gen LRU)** 가 들어왔고, 커널 문서에 설정 방법이 정리되어 있다. 어느 쪽이든 정확한 LRU 가 아니라 참조 비트를 이용한 근사다.

## 직접 해 보기

네 알고리즘을 같은 참조열로 비교하고, FIFO 의 벨레이디 모순을 재현한다.

```python
from collections import OrderedDict, deque

def fifo(refs, k):
    mem, q, faults = set(), deque(), 0
    for p in refs:
        if p in mem: continue
        faults += 1
        if len(mem) == k: mem.remove(q.popleft())
        mem.add(p); q.append(p)
    return faults

def lru(refs, k):
    mem, faults = OrderedDict(), 0
    for p in refs:
        if p in mem: mem.move_to_end(p); continue      # 최근 사용으로 갱신
        faults += 1
        if len(mem) == k: mem.popitem(last=False)      # 가장 오래 안 쓴 것
        mem[p] = True
    return faults

def opt(refs, k):
    mem, faults = set(), 0
    for i, p in enumerate(refs):
        if p in mem: continue
        faults += 1
        if len(mem) == k:
            future = refs[i + 1:]
            victim = max(mem, key=lambda x: future.index(x) if x in future else float("inf"))
            mem.remove(victim)
        mem.add(p)
    return faults

def clock(refs, k):
    frames, ref, hand, faults = [None] * k, [0] * k, 0, 0
    for p in refs:
        if p in frames: ref[frames.index(p)] = 1; continue
        faults += 1
        while ref[hand]:                    # 참조 비트가 1이면 기회를 한 번 더 준다
            ref[hand] = 0; hand = (hand + 1) % k
        frames[hand], ref[hand] = p, 1
        hand = (hand + 1) % k
    return faults

refs = [7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1]
print("참조열:", refs)
for k in (3, 4):
    print(f"프레임 {k}: OPT {opt(refs,k):2d}  LRU {lru(refs,k):2d}  CLOCK {clock(refs,k):2d}  FIFO {fifo(refs,k):2d}")

belady = [1,2,3,4,1,2,5,1,2,3,4,5]
print("벨레이디 참조열:", belady)
print("FIFO 프레임 3 ->", fifo(belady, 3), "회 /  프레임 4 ->", fifo(belady, 4), "회")
print("LRU  프레임 3 ->", lru(belady, 3), "회 /  프레임 4 ->", lru(belady, 4), "회")
```

```
참조열: [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
프레임 3: OPT  9  LRU 12  CLOCK 14  FIFO 15
프레임 4: OPT  8  LRU  8  CLOCK  9  FIFO 10
벨레이디 참조열: [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
FIFO 프레임 3 -> 9 회 /  프레임 4 -> 10 회
LRU  프레임 3 -> 10 회 /  프레임 4 -> 8 회
```

OPT ≤ LRU ≤ CLOCK ≤ FIFO 순서가 이 참조열에서 그대로 보인다. CLOCK 은 LRU 보다 조금 나쁘지만 구현 비용이 훨씬 싸다. 아래 두 줄이 벨레이디의 모순이다. FIFO 는 프레임을 3개에서 4개로 늘렸더니 폴트가 9회에서 10회로 늘었다. LRU 는 같은 참조열에서 10회에서 8회로 줄었다.

## 현업에서는

- **페이지 캐시가 "사용 중"인 메모리를 차지하는 이유**: 리눅스 `free` 의 `buff/cache` 는 파일 내용을 담아 둔 페이지다. 필요하면 교체 알고리즘이 먼저 이것을 내보내므로 대부분 "쓸 수 있는 메모리"다. 그래서 `free` 열보다 `available` 열을 본다.
- **스왑과 swappiness**: `vm.swappiness` 는 익명 페이지를 스왑으로 내보내는 것과 파일 페이지를 버리는 것 사이의 상대적 선호를 조정한다. 쿠버네티스 노드는 오랫동안 스왑 비활성화가 전제였고, 최근 버전에서 노드 스왑 지원이 단계적으로 추가되고 있으니 사용하는 버전의 문서를 확인한다.
- **대용량 백업이 캐시를 밀어낼 때**: 큰 파일을 한 번 읽는 백업 작업 뒤에 서비스가 느려지는 것은 자주 쓰던 페이지가 밀려났기 때문이다. `posix_fadvise(POSIX_FADV_DONTNEED)` 나 `O_DIRECT` 로 페이지 캐시를 우회하거나, cgroup 메모리 제한으로 백업 작업의 캐시 사용량을 묶는다.
- **애플리케이션 캐시**: Redis 의 `maxmemory-policy` 에 있는 `allkeys-lru` 같은 옵션도 정확한 LRU 가 아니라 표본을 뽑아 근사한다. 정확한 LRU 가 비싸다는 사정은 어느 층에서나 같다.

## 확인 문제

1. OPT 알고리즘을 실제로 구현할 수 없는 이유와, 그래도 쓸모 있는 이유는?
2. 벨레이디의 모순이란 무엇이며, 어떤 알고리즘에서 나타나는가?
3. 정확한 LRU 가 비싼 이유는?
4. CLOCK 알고리즘에서 참조 비트가 1 인 페이지를 만나면 어떻게 하는가?
5. 수정된(dirty) 페이지보다 깨끗한 페이지를 먼저 내보내는 것이 유리한 이유는?

### 풀이

1. 앞으로의 참조 순서를 알아야 하기 때문에 구현할 수 없다. 대신 같은 참조열에서 다른 알고리즘의 성능을 비교하는 이론적 하한(기준선)으로 쓴다.
2. 프레임 수를 늘렸는데 페이지 폴트가 오히려 늘어나는 현상이다. FIFO 에서 나타나고, LRU·OPT 같은 스택 알고리즘에서는 나타나지 않는다.
3. 모든 메모리 접근마다 사용 순서를 갱신해야 하기 때문이다. 하드웨어 지원 없이 소프트웨어로 하면 감당할 수 없다.
4. 참조 비트를 0 으로 지우고 바늘을 다음으로 옮긴다(두 번째 기회). 바늘이 한 바퀴 돌아 다시 올 때까지 또 참조되지 않으면 그때 내보낸다.
5. 깨끗한 페이지는 디스크에 같은 내용이 있으므로 그냥 버리면 되지만, dirty 페이지는 내보내기 전에 디스크에 써야 해서 I/O 가 추가로 든다.

## 더 읽을거리 (References)

- OSTEP, [Beyond Physical Memory: Policies (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf)
- L. A. Belady, "A study of replacement algorithms for a virtual-storage computer", *IBM Systems Journal* 5(2), 1966.
- Linux kernel documentation, [Multi-Gen LRU](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)
- Linux kernel documentation, [Documentation for /proc/sys/vm/](https://docs.kernel.org/admin-guide/sysctl/vm.html) — `swappiness` 등
