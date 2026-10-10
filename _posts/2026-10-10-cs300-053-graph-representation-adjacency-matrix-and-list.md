---
layout: post
title: "[CS300 #053] 그래프 표현 — 인접 행렬과 인접 리스트"
date: 2026-10-10 18:53:00 +0900
categories: [cs]
tags: [cs300, data-structures, graph, adjacency-list, adjacency-matrix]
---

컴퓨터공학 300 주제 시리즈의 053번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

그래프는 V×V 표에 간선 유무를 적는 인접 행렬, 정점마다 이웃 목록을 두는 인접 리스트, 그리고 그 목록을 배열 두 개로 납작하게 편 CSR 로 표현하며, 간선이 적은 희소 그래프에는 리스트 계열이, 빽빽하거나 간선 존재를 자주 묻는 경우엔 행렬이 맞는다.

## 왜 필요한가

도로망, 소셜 관계, 웹 링크, 패키지 의존성, 마이크로서비스 호출 관계, 쿠버네티스 리소스의 소유 관계는 모두 그래프다. 그래프 알고리즘(BFS, DFS, 최단 경로, 위상 정렬)은 알고리즘 파트에서 자세히 다루지만, 그 알고리즘이 얼마나 빠른지는 **그래프를 어떻게 저장했느냐**에 먼저 달려 있다.

같은 BFS 라도 인접 행렬 위에서는 O(V²), 인접 리스트 위에서는 O(V + E) 다. 정점 백만 개짜리 소셜 그래프를 행렬로 잡으면 칸이 1조 개라 메모리에 올라가지도 않는다. 반대로 정점 수백 개에 간선이 빽빽한 그래프에서 "u 와 v 가 연결됐나?"를 수없이 물어야 한다면 행렬이 훨씬 빠르다. 표현을 고르는 것이 그래프 문제의 첫 결정이다.

## 핵심 개념

### 용어

- 정점(vertex) 수 V, 간선(edge) 수 E
- **방향 그래프**: 간선에 방향이 있다 (u → v). **무방향**: 없다
- **가중 그래프**: 간선에 비용·거리가 붙는다
- **희소(sparse)**: E 가 V² 보다 훨씬 작다. 현실 그래프 대부분이 그렇다. **조밀(dense)**: E 가 V² 에 가깝다
- 무방향 단순 그래프의 E 는 최대 V(V−1)/2 다

예시로 다음 무방향 그래프를 쓴다.

```
    0 ─── 1
     \   /
      \ /
       2 ─── 3 ─── 4
```

### 인접 행렬

V×V 표에서 `M[u][v] = 1` 이면 간선이 있다. 가중 그래프면 1 대신 가중치를, 간선 없음은 0 이나 무한대로 적는다. 무방향이면 대칭 행렬이다.

```
     0 1 2 3 4
  0 [0 1 1 0 0]
  1 [1 0 1 0 0]
  2 [1 1 0 1 0]
  3 [0 0 1 0 1]
  4 [0 0 0 1 0]
```

### 인접 리스트

정점마다 이웃을 담은 목록을 둔다. 저장하는 것은 실제로 있는 간선뿐이다.

```
0: [1, 2]
1: [0, 2]
2: [0, 1, 3]
3: [2, 4]
4: [3]
```

무방향 간선 하나는 양쪽 목록에 한 번씩, 모두 2E 개 항목이 된다. 목록을 리스트 대신 해시 집합으로 두면 간선 존재 검사도 평균 O(1) 이 된다. 파이썬 그래프 라이브러리 NetworkX 의 `Graph` 클래스 문서는 내부를 "dict-of-dict-of-dict" 구조로 설명한다. 바깥 사전은 정점별 인접 정보, 그 안의 사전은 이웃별 간선 데이터다([NetworkX — Graph](https://networkx.org/documentation/stable/reference/classes/graph.html)). 인접 리스트를 해시 맵으로 만든 형태다.

### CSR(Compressed Sparse Row)

인접 리스트를 정점마다 따로 할당하면 포인터와 할당 비용이 크다. CSR 은 모든 이웃을 배열 하나(`targets`)에 이어 붙이고, 정점 u 의 이웃이 어디서 시작하는지를 `offsets` 배열에 적는다.

```
offsets: [0, 2, 4, 7, 9, 10]
targets: [1, 2 | 0, 2 | 0, 1, 3 | 2, 4 | 3]
          └0의┘ └1의┘ └──2의──┘ └3의┘ └4┘

u 의 이웃 = targets[offsets[u] : offsets[u+1]]
```

메모리가 연속이라 캐시 효율이 좋고, 정수 배열 두 개뿐이라 작다. 대신 간선 추가·삭제가 비싸서, 한 번 만들고 여러 번 읽는 분석 작업에 맞는다. 희소 행렬 라이브러리의 CSR 형식과 같은 것이며, SciPy 의 `scipy.sparse.csgraph` 모듈도 그래프를 CSR 희소 행렬로 다룬다([SciPy — Compressed sparse graph routines](https://docs.scipy.org/doc/scipy/reference/sparse.csgraph.html)).

### 비교

| 항목 | 인접 행렬 | 인접 리스트 | CSR |
|---|---|---|---|
| 메모리 | O(V²) | O(V + E) | O(V + E), 가장 작음 |
| u–v 간선 있나 | **O(1)** | O(deg(u)) (해시 집합이면 평균 O(1)) | O(log deg(u)) (정렬 시) |
| u 의 이웃 전부 | O(V) | **O(deg(u))** | **O(deg(u))**, 캐시 친화적 |
| BFS·DFS 전체 | O(V²) | O(V + E) | O(V + E) |
| 간선 추가 | O(1) | O(1) | 재구성 필요 |
| 정점 추가 | O(V²) 재할당 | O(1) | 재구성 필요 |
| 어울리는 곳 | 작고 조밀, 플로이드-워셜, 행렬 연산 | 범용, 변경이 잦을 때 | 크고 정적인 그래프 분석 |

BFS 가 행렬에서 O(V²) 인 이유는 정점 하나의 이웃을 찾을 때마다 행 전체 V 칸을 훑어야 하기 때문이다. 간선이 몇 개 없어도 마찬가지다.

### 간선 리스트

`[(0,1), (0,2), …]` 처럼 간선만 나열한 형태도 있다. 저장과 전송에는 가장 단순하지만 이웃 찾기가 O(E) 다. 크루스칼 알고리즘처럼 "간선을 가중치 순으로 한 번 훑기"만 필요할 때 쓴다. 다음 글의 Union-Find 와 짝을 이룬다.

## 직접 해 보기

같은 그래프를 세 가지로 표현하고, 희소 그래프에서 메모리 차이를 계산한다.

```python
from collections import deque
from array import array
import random

# 무방향 그래프 예시: 0-1, 0-2, 1-2, 2-3, 3-4
V = 5
edges = [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4)]

# 1) 인접 행렬: V×V
M = [[0] * V for _ in range(V)]
for u, v in edges:
    M[u][v] = M[v][u] = 1

# 2) 인접 리스트: 정점마다 이웃 목록
adj = [[] for _ in range(V)]
for u, v in edges:
    adj[u].append(v); adj[v].append(u)

# 3) CSR: offsets[u] ~ offsets[u+1] 구간이 u 의 이웃
deg = [len(a) for a in adj]
offsets = [0]
for d in deg:
    offsets.append(offsets[-1] + d)
targets = [v for a in adj for v in a]

print("행렬:")
for row in M:
    print("  ", row)
print("리스트:", adj)
print("CSR offsets:", offsets, " targets:", targets)
print("2 의 이웃 (CSR):", targets[offsets[2]:offsets[3]])

def bfs(start, neighbors):
    dist = {start: 0}; q = deque([start])
    while q:
        u = q.popleft()
        for v in neighbors(u):
            if v not in dist:
                dist[v] = dist[u] + 1; q.append(v)
    return dist

print("BFS(행렬):", bfs(0, lambda u: [v for v in range(V) if M[u][v]]))
print("BFS(리스트):", bfs(0, lambda u: adj[u]))

# 희소 그래프에서 메모리 비교: 정점 2만, 간선 10만 (정점마다 이웃 10개라고 가정)
V2, E2 = 20_000, 100_000
rng = random.Random(1)
cells_matrix = V2 * V2                    # 비트 하나씩만 써도 이만큼 칸이 필요
csr_targets = array("i", (rng.randrange(V2) for _ in range(2 * E2)))
csr_offsets = array("i", range(0, 2 * E2 + 1, 10))
print(f"V={V2:,}, E={E2:,}")
print(f"  인접 행렬 칸 수 = {cells_matrix:,} (1비트씩이어도 {cells_matrix/8/2**20:.0f} MiB)")
print(f"  CSR 배열 크기   = {(len(csr_targets)+len(csr_offsets))*4/2**20:.2f} MiB (int32)")
```

```
행렬:
   [0, 1, 1, 0, 0]
   [1, 0, 1, 0, 0]
   [1, 1, 0, 1, 0]
   [0, 0, 1, 0, 1]
   [0, 0, 0, 1, 0]
리스트: [[1, 2], [0, 2], [0, 1, 3], [2, 4], [3]]
CSR offsets: [0, 2, 4, 7, 9, 10]  targets: [1, 2, 0, 2, 0, 1, 3, 2, 4, 3]
2 의 이웃 (CSR): [0, 1, 3]
BFS(행렬): {0: 0, 1: 1, 2: 1, 3: 2, 4: 3}
BFS(리스트): {0: 0, 1: 1, 2: 1, 3: 2, 4: 3}
V=20,000, E=100,000
  인접 행렬 칸 수 = 400,000,000 (1비트씩이어도 48 MiB)
  CSR 배열 크기   = 0.84 MiB (int32)
```

표현이 달라도 BFS 결과는 같다. 다른 것은 비용이다. 정점 2만, 간선 10만인 희소 그래프에서 인접 행렬은 칸이 4억 개라 한 칸을 1비트로 줄여도 48 MiB, 파이썬 리스트의 리스트로 만들면 기가바이트 단위가 된다. CSR 은 1 MiB 도 안 된다. 행렬의 칸 중 실제 간선은 20만 / 4억, 0.05% 다.

## 현업에서는

- **의존성 그래프.** 패키지 매니저, 빌드 시스템, 워크플로 엔진(예: 작업 DAG)은 의존성을 인접 리스트로 들고 위상 정렬로 실행 순서를 정한다. 파이썬 표준 라이브러리에도 `graphlib.TopologicalSorter` 가 있고, 노드와 그 선행 노드 목록을 받는 형태다([Python graphlib](https://docs.python.org/3/library/graphlib.html)).
- **쿠버네티스 리소스 관계.** 디플로이먼트 → 레플리카셋 → 파드는 `ownerReferences` 로 이어진 그래프다. 쿠버네티스 문서는 소유자 참조가 어떤 객체가 다른 객체에 종속되는지를 컨트롤 플레인에 알려 주고, 이를 이용해 관련 객체를 정리한다고 설명한다([Kubernetes — Garbage Collection](https://kubernetes.io/docs/concepts/architecture/garbage-collection/)). 각 객체가 자기 소유자 목록을 들고 있는, 역방향 인접 리스트라고 볼 수 있다.
- **서비스 맵과 트레이싱.** 분산 트레이싱 도구가 그리는 서비스 호출 그래프는 (호출자, 피호출자, 호출 수) 간선 리스트를 모아 만든다. 저장은 간선 리스트로, 분석은 인접 리스트로 바꿔 하는 것이 일반적이다.
- **선택 기준 한 줄.** 정점 수가 수천 이하이고 간선이 빽빽하거나 행렬 연산(전이 행렬, 플로이드-워셜)을 할 것이면 행렬, 그 밖에는 인접 리스트로 시작한다. 크고 바뀌지 않는 그래프를 반복 분석하면 CSR 로 굳힌다.

## 확인 문제

1. 정점 1000개, 간선 3000개인 무방향 그래프를 인접 행렬과 인접 리스트로 저장할 때 칸(항목) 수는 각각 대략 얼마인가?
2. 인접 행렬에서 BFS 가 O(V²) 인 이유는?
3. CSR 에서 정점 u 의 차수(degree)는 어떻게 O(1) 에 구하는가?
4. "u 와 v 사이에 간선이 있나?"를 매우 자주 묻고, 정점 수가 작다면 어떤 표현을 고르는가?
5. 무방향 그래프의 인접 리스트에서 모든 목록 길이의 합은 E 와 어떤 관계인가?

### 풀이

1. 행렬 1000² = 100만 칸, 리스트는 정점 목록 1000 + 항목 2 × 3000 = 6000.
2. 각 정점의 이웃을 찾을 때 행 전체 V 칸을 확인해야 하고, 이것을 V 개 정점에 대해 하기 때문이다.
3. `offsets[u+1] - offsets[u]`.
4. 인접 행렬. 간선 확인이 O(1) 이다. (리스트를 해시 집합으로 두는 것도 대안이다.)
5. 각 간선이 양 끝 목록에 한 번씩 들어가므로 합은 2E 다(차수 합 정리).

## 더 읽을거리 (References)

- Robert Sedgewick, Kevin Wayne, [Algorithms, 4th ed. — 4.1 Undirected Graphs](https://algs4.cs.princeton.edu/41graph/)
- NetworkX Documentation, [Graph — Undirected graphs with self loops](https://networkx.org/documentation/stable/reference/classes/graph.html)
- SciPy Documentation, [Compressed sparse graph routines (scipy.sparse.csgraph)](https://docs.scipy.org/doc/scipy/reference/sparse.csgraph.html)
- NIST Dictionary of Algorithms and Data Structures, [adjacency-list representation](https://xlinux.nist.gov/dads/HTML/adjacencyListRep.html), [adjacency-matrix representation](https://xlinux.nist.gov/dads/HTML/adjacencyMatrixRep.html)
