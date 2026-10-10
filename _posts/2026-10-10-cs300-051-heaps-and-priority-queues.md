---
layout: post
title: "[CS300 #051] 힙과 우선순위 큐 — 가장 급한 것 하나만 빨리"
date: 2026-10-10 18:51:00 +0900
categories: [cs]
tags: [cs300, data-structures, heap, priority-queue, heapq]
---

컴퓨터공학 300 주제 시리즈의 051번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

이진 힙은 "부모가 자식보다 작거나 같다"는 규칙만 지키는 완전 이진 트리를 배열에 담은 것으로, 최솟값 보기 O(1), 넣기·꺼내기 O(log n), 한꺼번에 만들기 O(n) 을 제공하며 우선순위 큐의 표준 구현이다.

## 왜 필요한가

일이 들어오는 순서와 처리해야 하는 순서가 다를 때가 있다. 응급실은 도착 순서가 아니라 위급한 순서로 환자를 본다. 타이머는 등록 순서가 아니라 만료 시각 순서로 깨어나야 한다. 다익스트라 알고리즘은 지금까지 가장 가까운 정점부터 확정한다. 이런 "다음에 처리할 것은 가장 우선순위 높은 것" 구조가 **우선순위 큐**다.

정렬된 배열로 만들면 꺼내기는 O(1) 이지만 넣기가 O(n) 이다. 정렬 안 된 배열이면 넣기는 O(1) 이지만 꺼내기가 O(n) 이다. 균형 BST 를 쓰면 둘 다 O(log n) 이지만 무겁다. 힙은 "전체 정렬은 필요 없고 맨 앞 하나만 알면 된다"는 점을 이용해, 배열 하나로 둘 다 O(log n) 에 해낸다. 포인터도, 추가 메모리도 없다.

## 핵심 개념

### 힙 성질과 배열 표현

**최소 힙(min-heap)** 은 모든 노드가 자기 자식보다 작거나 같은 완전 이진 트리다. 형제끼리는 순서가 없다. 그래서 정렬보다 훨씬 약한 조건이고, 그만큼 유지가 싸다. 루트가 항상 최솟값이다. 최대 힙은 부등호만 반대다.

완전 이진 트리는 위층부터, 각 층은 왼쪽부터 빈틈없이 채우므로 배열에 그대로 펼칠 수 있다. 0번부터 세면

```
부모(i) = (i − 1) // 2      왼쪽 자식(i) = 2i + 1      오른쪽 자식(i) = 2i + 2

                5                       idx: 0  1  2  3  4  5  6  7  8  9
             /     \                   val: 5 33 53 38 49 65 62 51 97 61
           33       53
          /  \     /  \
        38    49  65   62
       / \    /
     51  97  61
```

파이썬 `heapq` 문서는 정확히 이 조건, 즉 모든 k 에 대해 `heap[k] <= heap[2*k+1]` 이고 `heap[k] <= heap[2*k+2]` 인 리스트를 힙으로 쓴다고 정의한다([Python heapq](https://docs.python.org/3/library/heapq.html)).

### 연산

| 연산 | 방법 | 비용 |
|---|---|---|
| `peek` | `a[0]` | O(1) |
| `push(x)` | 배열 끝에 넣고 부모보다 작으면 자리 바꾸며 올림(sift-up) | O(log n) |
| `pop()` | 루트와 마지막을 바꾸고 빼낸 뒤, 새 루트를 작은 자식과 바꾸며 내림(sift-down) | O(log n) |
| `heapify` | 마지막 내부 노드부터 루트까지 거꾸로 sift-down | **O(n)** |
| 임의 원소 찾기·삭제 | 순서가 없으니 훑어야 함 | O(n) |

### heapify 가 O(n) 인 이유

원소 n 개를 하나씩 `push` 하면 최악 O(n log n) 이다. 그런데 아래에서 위로 `sift-down` 을 하면 O(n) 이다. 트리 노드의 절반은 잎이라 내려갈 일이 없다. 4분의 1 은 한 층, 8분의 1 은 두 층만 내려간다. 총 이동량은

```
n/4 · 1 + n/8 · 2 + n/16 · 3 + …  =  n · Σ k/2^(k+1)  =  n
```

이 되어 선형이다. 높이가 큰 노드는 아주 적고, 많은 노드는 아주 낮다는 점이 핵심이다.

### 힙 정렬

heapify 한 뒤 n 번 pop 하면 정렬된 순서가 나온다. 최대 힙을 쓰고 꺼낸 값을 배열 뒤쪽 빈자리에 넣으면 추가 메모리 없이 제자리 정렬이 된다. 이것이 1964년 Williams 가 발표한 힙 정렬이고, 최악 O(n log n) 을 보장한다. 다만 메모리 접근이 흩어져 실전에서는 퀵 정렬 계열보다 느린 경우가 많다. 정렬 알고리즘은 다음 파트에서 따로 다룬다.

### 우선순위 큐 구현의 실전 문제

`heapq` 문서의 "우선순위 큐 구현 노트" 절은 실제로 부딪히는 문제를 정리해 둔다.

- **동률 처리.** 우선순위가 같으면 넣은 순서대로 나와야 할 때가 많다. 힙은 안정적이지 않다. `(우선순위, 순번, 작업)` 처럼 증가하는 순번을 끼워 넣는다. 순번 덕분에 작업 객체끼리 비교할 일도 없어져, 비교 불가능한 객체를 넣어도 오류가 나지 않는다.
- **우선순위 변경·삭제.** 힙에서 특정 원소를 찾는 것은 O(n) 이다. 흔한 해법은 지우지 않고 "취소됨" 표시만 해 두었다가 꺼낼 때 건너뛰는 **지연 삭제**다. 고의 `container/heap` 처럼 원소의 인덱스를 따로 추적해 `Fix(h, i)` 로 O(log n) 에 고치는 방법도 있다([Go container/heap](https://pkg.go.dev/container/heap)).

## 직접 해 보기

배열 기반 최소 힙을 직접 만들고, 비교 횟수로 heapify 와 반복 push 를 비교한다.

```python
import random, heapq, itertools

class MinHeap:
    def __init__(self, items=()):
        self.a = list(items)
        self.cmp = 0
        for i in range(len(self.a) // 2 - 1, -1, -1):   # 상향식 heapify: O(n)
            self._down(i)

    def _less(self, i, j):
        self.cmp += 1
        return self.a[i] < self.a[j]

    def _up(self, i):
        while i > 0:
            p = (i - 1) // 2
            if not self._less(i, p):
                break
            self.a[i], self.a[p] = self.a[p], self.a[i]
            i = p

    def _down(self, i):
        n = len(self.a)
        while True:
            l, r, m = 2 * i + 1, 2 * i + 2, i
            if l < n and self._less(l, m): m = l
            if r < n and self._less(r, m): m = r
            if m == i:
                return
            self.a[i], self.a[m] = self.a[m], self.a[i]
            i = m

    def push(self, x):
        self.a.append(x)
        self._up(len(self.a) - 1)

    def pop(self):
        a = self.a
        a[0], a[-1] = a[-1], a[0]
        x = a.pop()
        if a:
            self._down(0)
        return x

rng = random.Random(0)
data = [rng.randint(0, 99) for _ in range(10)]
h = MinHeap(data)
print("배열 상태:", h.a)
print("하나씩 pop:", [h.pop() for _ in range(len(data))])

N = 1 << 17
for name, data in [("무작위", [rng.random() for _ in range(N)]),
                   ("내림차순", list(range(N, 0, -1)))]:   # push 의 최악 입력
    h1 = MinHeap(data)                   # 한 번에 heapify
    h2 = MinHeap()
    for x in data:                       # 하나씩 push
        h2.push(x)
    print(f"{name:4} N={N}: heapify 비교 {h1.cmp:>9,}회  push N번 비교 {h2.cmp:>9,}회")

# 동률 처리: (우선순위, 순번, 작업) — 작업끼리는 비교하지 않게
pq, seq = [], itertools.count()
for prio, task in [(2, "백업"), (1, "알림"), (2, "리포트"), (0, "장애 대응")]:
    heapq.heappush(pq, (prio, next(seq), task))
print([heapq.heappop(pq)[2] for _ in range(len(pq))])
print("상위 3개:", heapq.nlargest(3, [5, 1, 9, 3, 7, 2]))
```

```
배열 상태: [5, 33, 53, 38, 49, 65, 62, 51, 97, 61]
하나씩 pop: [5, 33, 38, 49, 51, 53, 61, 62, 65, 97]
무작위  N=131072: heapify 비교   246,417회  push N번 비교   298,500회
내림차순 N=131072: heapify 비교   262,110회  push N번 비교 1,966,099회
['장애 대응', '알림', '백업', '리포트']
상위 3개: [9, 7, 5]
```

배열 상태는 위 그림의 트리와 같다. 정렬되어 있지 않지만 힙 성질은 만족한다. 비교 횟수를 보면 heapify 는 입력과 상관없이 2N 안쪽이다. 하나씩 push 하는 쪽은 무작위 입력에서는 새 원소가 대개 몇 층만 올라가서 생각보다 싸지만, 내림차순처럼 매번 루트까지 올라가야 하는 입력에서는 N log N 에 가까운 약 196만 회가 된다. "평균적으로 괜찮다"와 "최악에도 보장된다"는 다른 말이다. 우선순위가 같은 "백업"과 "리포트"는 순번 덕에 넣은 순서대로 나왔다.

## 현업에서는

- **타이머와 지연 작업.** 이벤트 루프와 스케줄러는 "다음에 만료될 타이머"를 힙 맨 앞에서 꺼낸다. 파이썬 `asyncio` 의 지연 콜백, 고의 런타임 타이머가 이 형태다.
- **쿠버네티스 스케줄러.** 스케줄링 프레임워크의 QueueSort 플러그인은 스케줄링 큐 안의 파드 순서를 정하는 `Less(Pod1, Pod2)` 함수를 제공한다고 문서에 적혀 있다([Kubernetes — Scheduling Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)). 기본 동작은 우선순위가 높은 파드를 먼저 꺼내는 것이다. 비교 함수 하나로 순서를 정하는 우선순위 큐의 전형이다.
- **상위 k 개.** 로그에서 가장 느린 요청 100개를 찾을 때 전체를 정렬(O(n log n))할 필요 없이 크기 k 짜리 최소 힙을 유지하면 O(n log k), 메모리 O(k) 다. 스트리밍 데이터에서 특히 유용하다.
- **자바.** `PriorityQueue` 문서는 `offer`·`poll` 이 O(log n), `remove(Object)`·`contains` 가 선형 시간, `peek` 가 상수 시간이라고 명시한다([Java SE 21 PriorityQueue](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/PriorityQueue.html)). 임의 원소 삭제가 선형이라는 점을 모르고 큰 큐에서 `remove(obj)` 를 반복하면 느려진다.

## 확인 문제

1. 0부터 세는 배열 힙에서 인덱스 9 의 부모와, 인덱스 4 의 두 자식 인덱스는?
2. 최소 힙 `[1, 3, 2, 7, 4]` 에서 pop 을 한 번 하면 배열은 어떻게 되는가?
3. heapify 가 O(n) 인 직관적 이유는?
4. 우선순위 큐에 `(priority, task)` 튜플을 넣었다가 같은 우선순위에서 `TypeError` 가 났다. 원인과 해결책은?
5. 스트림에서 가장 큰 값 k 개를 유지하려면 최소 힙과 최대 힙 중 무엇을 쓰는가?

### 풀이

1. 부모는 (9−1)//2 = 4. 인덱스 4 의 자식은 9 와 10.
2. 마지막 원소 4 를 루트로 옮겨 `[4, 3, 2, 7]`, 작은 자식 2 와 교환해 `[2, 3, 4, 7]`.
3. 노드 대부분이 잎 근처에 있어 조금만 내려가면 되고, 많이 내려가야 하는 위쪽 노드는 아주 적다. 합하면 n 에 비례한다.
4. 우선순위가 같으면 튜플 비교가 `task` 끼리 비교로 넘어가는데 task 가 비교 불가능한 객체라서다. `(priority, 순번, task)` 처럼 고유한 순번을 가운데 넣는다.
5. 크기 k 의 **최소** 힙. 맨 앞(현재 k 개 중 가장 작은 값)보다 큰 값이 오면 교체한다.

## 더 읽을거리 (References)

- Python Documentation, [heapq — Heap queue algorithm](https://docs.python.org/3/library/heapq.html) — 우선순위 큐 구현 노트 포함
- Oracle, [Java SE 21 API — PriorityQueue](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/PriorityQueue.html)
- Go Standard Library, [container/heap](https://pkg.go.dev/container/heap)
- J. W. J. Williams, "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), 1964
