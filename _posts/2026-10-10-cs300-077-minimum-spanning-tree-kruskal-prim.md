---
layout: post
title: "[CS300 #077] 최소 신장 트리 — 크루스칼과 프림"
date: 2026-10-10 19:17:00 +0900
categories: [cs]
tags: [cs300, algorithms, graph, minimum-spanning-tree, union-find]
---

컴퓨터공학 300 주제 시리즈의 077번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

최소 신장 트리(MST)는 연결된 무향 가중 그래프의 모든 정점을 잇는 간선 V−1 개짜리 트리 중 가중치 합이 가장 작은 것이다. 크루스칼은 가벼운 간선부터 사이클이 안 생기면 고르고, 프림은 한 정점에서 출발해 트리에 붙은 가장 가벼운 간선을 계속 붙인다. 둘 다 "절단 속성" 이 보장하는 탐욕 알고리즘이다.

## 왜 필요한가

건물 여섯 동을 광케이블로 연결해야 한다. 동 사이마다 공사 비용이 다르다. 모든 동이 (직접이든 다른 동을 거쳐서든) 연결되기만 하면 되고, 비용은 최소로 하고 싶다. 사이클이 있으면 간선 하나를 빼도 여전히 연결되므로 낭비다. 그러니 답은 트리이고, 그중 비용 최소인 것이 MST 다.

전력망·통신망 설계가 원래 동기였다. Borůvka 가 1926년에 전력망 문제로 처음 다뤘고, Kruskal(1956)과 Prim(1957)이 오늘날 교과서의 두 방법을 발표했다. 앞서 본 다익스트라의 1959년 논문도 같은 문제를 다룬다.

## 핵심 개념

### 절단 속성(cut property)

정점들을 두 무리 S 와 V−S 로 나누는 것을 절단이라고 한다. 두 무리를 잇는 간선 중 가중치가 가장 작은 간선은 어떤 MST 에 반드시 포함된다(가중치가 모두 다르면 유일한 MST 에 포함된다).

교환 논증으로 증명한다. 그 가장 가벼운 간선 e 를 포함하지 않는 MST T 가 있다고 하자. T 에 e 를 더하면 사이클이 생기고, 그 사이클은 절단을 한 번 더 건너는 다른 간선 f 를 포함한다. f 를 빼면 다시 신장 트리가 되고, e 가 f 보다 가볍거나 같으므로 총합이 늘지 않는다. 그러므로 e 를 포함하는 MST 가 있다.

크루스칼과 프림은 절단을 고르는 방식만 다르다.

### 크루스칼

```
간선을 가중치 오름차순으로 정렬
각 정점을 자기 혼자인 덩어리로 시작
for (u, v, w) in 정렬된 간선:
    if u 와 v 가 다른 덩어리:      ← 사이클이 안 생김
        간선 채택, 두 덩어리 합치기
```

간선 (u, v) 를 고르는 순간, "u 가 속한 덩어리" 와 "나머지" 를 절단으로 보면 이 간선이 그 절단을 건너는 가장 가벼운 간선이다(더 가벼운 간선은 이미 다 처리했으니까). 절단 속성에 따라 안전하다.

"같은 덩어리인가" 를 빠르게 판정하는 자료구조가 **유니온 파인드**(서로소 집합)다. 경로 압축과 랭크에 의한 합치기를 함께 쓰면 연산 하나가 분할 상환으로 사실상 상수 시간이다(정확히는 역 아커만 함수 α(n)). 그래서 전체 시간은 정렬이 지배해 O(E log E) = O(E log V) 다.

### 프림

```
시작 정점 하나를 트리에 넣는다
트리와 바깥을 잇는 간선들을 최소 힙에 넣는다
while 트리에 안 들어온 정점이 있음:
    힙에서 가장 가벼운 간선 (u, v) 를 꺼낸다
    v 가 이미 트리에 있으면 버린다
    v 를 트리에 넣고, v 에서 바깥으로 가는 간선들을 힙에 넣는다
```

절단은 "현재 트리" 와 "나머지" 다. 매번 그 절단을 건너는 가장 가벼운 간선을 고르니 안전하다. 다익스트라와 모양이 거의 같다. 차이는 힙의 키가 "시작점에서의 누적 거리" 가 아니라 "트리까지의 간선 하나의 가중치" 라는 점이다.

이진 힙으로 O(E log V).

### 어느 쪽을 쓰나

| | 크루스칼 | 프림 |
|---|---|---|
| 핵심 자료구조 | 정렬 + 유니온 파인드 | 우선순위 큐 |
| 시간 | O(E log V) | O(E log V) (이진 힙) |
| 잘 맞는 그래프 | 희소, 간선 목록으로 주어진 경우 | 조밀, 인접 리스트·행렬로 주어진 경우 |
| 중간 상태 | 여러 조각(숲)이 점점 합쳐짐 | 하나의 트리가 점점 자람 |

조밀한 그래프(E ≈ V²)에서는 힙 없이 배열로 최솟값을 찾는 프림이 O(V²) 로 가장 좋다.

## 직접 해 보기

같은 그래프에 크루스칼과 프림을 돌려 가중치 합을 비교한다. python3 로 실행해 확인했다.

```python
import heapq

edges = [  # (가중치, u, v) 무향
    (7, "A", "B"), (5, "A", "D"), (8, "B", "C"), (9, "B", "D"), (7, "B", "E"),
    (5, "C", "E"), (15, "D", "E"), (6, "D", "F"), (8, "E", "F"), (9, "E", "G"), (11, "F", "G"),
]
nodes = sorted({x for _, u, v in edges for x in (u, v)})

class DSU:
    def __init__(self, items):
        self.p = {x: x for x in items}; self.r = {x: 0 for x in items}
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]       # 경로 절반 압축
            x = self.p[x]
        return x
    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False                        # 이미 같은 덩어리 → 사이클
        if self.r[a] < self.r[b]:
            a, b = b, a
        self.p[b] = a
        if self.r[a] == self.r[b]:
            self.r[a] += 1
        return True

def kruskal():
    dsu, mst = DSU(nodes), []
    for w, u, v in sorted(edges):
        if dsu.union(u, v):
            mst.append((u, v, w))
    return mst

def prim(start="A"):
    adj = {x: [] for x in nodes}
    for w, u, v in edges:
        adj[u].append((w, v)); adj[v].append((w, u))
    seen, mst = {start}, []
    pq = [(w, start, v) for w, v in adj[start]]
    heapq.heapify(pq)
    while pq and len(seen) < len(nodes):
        w, u, v = heapq.heappop(pq)
        if v in seen:
            continue
        seen.add(v); mst.append((u, v, w))
        for w2, x in adj[v]:
            if x not in seen:
                heapq.heappush(pq, (w2, v, x))
    return mst

k, p = kruskal(), prim()
print("크루스칼:", k, "합:", sum(w for *_, w in k))
print("프림    :", p, "합:", sum(w for *_, w in p))
```

출력:

```
크루스칼: [('A', 'D', 5), ('C', 'E', 5), ('D', 'F', 6), ('A', 'B', 7), ('B', 'E', 7), ('E', 'G', 9)] 합: 39
프림    : [('A', 'D', 5), ('D', 'F', 6), ('A', 'B', 7), ('B', 'E', 7), ('E', 'C', 5), ('E', 'G', 9)] 합: 39
```

정점 7개에 간선 6개, 합 39 로 같은 트리가 나왔다. 고르는 순서만 다르다. 크루스칼은 가중치 순(5, 5, 6, 7, 7, 9)으로 여기저기서 조각을 붙였고, 프림은 A 에서 출발해 트리를 키워 가다 E 에 닿은 뒤에야 C–E(5) 를 붙였다. 크루스칼에서 B–D(9) 와 E–F(8) 는 이미 같은 덩어리 사이 간선이라 버려졌다.

## 현업에서는

- **네트워크·배선 설계.** 최소 비용으로 모든 지점을 연결하는 문제의 출발점이다. 실제 설계에서는 장애 대비 이중화가 필요해 MST 에 간선을 더하지만, 기본 골격의 비용 하한을 MST 가 알려 준다.
- **클러스터링.** 데이터 점들의 MST 를 만든 뒤 가장 무거운 간선 k−1 개를 끊으면 k 개 군집이 된다. 단일 연결(single-linkage) 계층 군집화와 같은 결과다. 로그 패턴이나 장애 알림을 비슷한 것끼리 묶는 데 응용할 수 있다.
- **유니온 파인드 단독 활용.** 크루스칼의 부품인 유니온 파인드는 그 자체로 쓸모가 많다. "이 두 노드가 같은 네트워크 분할에 속하나", "이 두 계정이 같은 사람인가(식별자 병합)" 같은 동치 관계 질의를 거의 상수 시간에 처리한다.
- **근사 알고리즘의 부품.** 외판원 문제(TSP)의 2-근사 알고리즘은 MST 를 만들고 그 트리를 순회한다. NP-어려운 문제에 대한 실용적 해법의 재료가 된다.

## 확인 문제

1. 신장 트리의 간선 수가 V−1 인 이유는?
2. 크루스칼에서 유니온 파인드 대신 매번 BFS 로 "u 와 v 가 이미 연결되었나" 를 확인하면 복잡도는?
3. 모든 간선 가중치에 같은 상수를 더하면 MST 는 바뀌는가? 최단 경로는?
4. 가중치가 음수인 간선이 있어도 크루스칼은 올바른가?

### 풀이

1. V 개 정점을 사이클 없이 모두 연결하는 그래프가 트리이고, 트리의 간선 수는 항상 V−1 이다.
2. 간선마다 O(V) 의 BFS(현재 트리 간선 수가 V−1 이하)를 하므로 O(EV). 유니온 파인드를 쓰면 정렬 O(E log E) 가 지배한다.
3. MST 는 바뀌지 않는다. 모든 신장 트리가 간선 V−1 개라 똑같이 (V−1)·c 가 더해지기 때문이다. 최단 경로는 간선 수가 다른 경로끼리 비교하므로 바뀔 수 있다.
4. 올바르다. 절단 속성 논증은 가중치의 부호와 무관하다. 다익스트라와 다른 점이다.

## 더 읽을거리 (References)

- Joseph B. Kruskal, "On the Shortest Spanning Subtree of a Graph and the Traveling Salesman Problem", *Proceedings of the American Mathematical Society* 7(1), 1956.
- R. C. Prim, "Shortest Connection Networks and Some Generalizations", *Bell System Technical Journal* 36(6), 1957.
- NIST Dictionary of Algorithms and Data Structures, [Kruskal's algorithm](https://xlinux.nist.gov/dads/HTML/kruskalsalgo.html), [Prim-Jarnik algorithm](https://xlinux.nist.gov/dads/HTML/primJarnik.html)
- E. W. Dijkstra, [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390), *Numerische Mathematik* 1, 1959
