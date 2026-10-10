---
layout: post
title: "[CS300 #009] 그래프 이론 기초 — 용어와 표현"
date: 2026-10-10 18:09:00 +0900
categories: [cs]
tags: [cs300, math, graph-theory, adjacency-list, bfs]
---

컴퓨터공학 300 주제 시리즈의 009번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

그래프는 정점(대상)과 간선(대상 사이의 연결)으로 이루어진 구조다. 네트워크, 의존성, 지도, 소셜 관계처럼 "무엇이 무엇과 이어져 있는가" 를 다루는 문제는 거의 모두 그래프 문제이고, 그 출발점은 정확한 용어와 적절한 메모리 표현이다.

## 왜 필요한가

라우터와 링크, 마이크로서비스 호출 관계, 패키지 의존성, 웹 페이지 링크, 지하철 노선, 쿠버네티스 오브젝트의 소유 관계가 모두 그래프다. 문제를 그래프로 옮기는 순간 수십 년 동안 다듬어진 알고리즘(최단 경로, 위상 정렬, 연결 요소, 최소 신장 트리)을 그대로 쓸 수 있다.

반대로 용어가 흐리면 문제를 잘못 옮긴다. "경로" 와 "산책(walk)" 을 구분하지 않거나, 유향과 무향을 섞으면 알고리즘이 엉뚱한 답을 낸다. 표현을 잘못 고르면 같은 알고리즘이 수백 배 느려진다.

## 핵심 개념

### 정의

그래프 G = (V, E) 는 정점 집합 V 와 간선 집합 E 로 이루어진다. 정점 수를 n = n(V), 간선 수를 m = n(E) 로 쓴다.

- **무향 그래프**: 간선이 순서 없는 쌍 {u, v}. 친구 관계, 양방향 도로.
- **유향 그래프(digraph)**: 간선이 순서쌍 (u, v), u → v. 팔로우, 함수 호출, 의존성.
- **가중 그래프**: 간선마다 값(거리, 비용, 지연)이 붙음.
- **단순 그래프**: 자기 루프(u–u)와 중복 간선이 없는 그래프. 별말이 없으면 단순 그래프를 가정한다.

### 기본 용어

| 용어 | 뜻 |
|---|---|
| 인접(adjacent) | u 와 v 사이에 간선이 있음 |
| 차수(degree) | 정점에 붙은 간선 수. 유향이면 진입 차수·진출 차수로 나눔 |
| 산책(walk) | 간선으로 이어진 정점의 나열. 정점 반복 허용 |
| 경로(path) | 정점이 반복되지 않는 산책 |
| 사이클(cycle) | 시작과 끝이 같고, 그 외에는 정점이 반복되지 않는 닫힌 산책(길이 3 이상, 무향 기준) |
| 연결(connected) | 모든 정점 쌍 사이에 경로가 있음(무향) |
| 연결 요소 | 서로 연결된 정점들의 최대 묶음 |
| 강하게 연결 | 유향 그래프에서 모든 u, v 에 대해 u→v, v→u 경로가 모두 있음 |
| DAG | 유향 비순환 그래프. 의존성 그래프의 기본형 |
| 부분 그래프 | 정점과 간선의 일부만 고른 그래프 |
| 완전 그래프 Kₙ | 모든 정점 쌍이 인접. 간선 수 n(n−1)/2 |
| 이분 그래프 | 정점을 두 묶음으로 나눠 간선이 묶음 사이에만 있게 할 수 있음 |

연결 요소는 006번 글의 동치 관계로 정의된다. "u 에서 v 로 가는 경로가 있다" 는 무향 그래프에서 반사·대칭·추이를 만족하므로, 그 동치류가 연결 요소다.

### 악수 정리

**정리.** 무향 그래프에서 모든 정점의 차수 합은 간선 수의 두 배다. Σ deg(v) = 2m.

> **증명.** 간선 하나는 양 끝 두 정점의 차수에 각각 1 씩 더한다. 따라서 차수 합은 간선마다 정확히 2 씩 늘어난다. ∎

**따름정리.** 차수가 홀수인 정점의 수는 짝수다. (홀수 차수 합이 홀수면 전체 합이 짝수일 수 없다.)

같은 대상을 두 방식(정점 쪽에서, 간선 쪽에서)으로 세는 조합적 증명이다. 유향 그래프에서는 진입 차수 합 = 진출 차수 합 = m 이다.

### 메모리 표현

| 표현 | 공간 | 간선 (u,v) 존재 확인 | u 의 이웃 나열 | 잘 맞는 경우 |
|---|---|---|---|---|
| 인접 행렬 | Θ(n²) | Θ(1) | Θ(n) | 조밀한 그래프, 작은 n, 행렬 연산 |
| 인접 리스트 | Θ(n + m) | Θ(deg u) | Θ(deg u) | 희소한 그래프(대부분의 실제 그래프) |
| 간선 리스트 | Θ(m) | Θ(m) | Θ(m) | 간선을 정렬해 처리(크루스칼), 파일 저장 |

실제 그래프는 대개 **희소**하다. 정점이 백만 개인 소셜 그래프에서 한 사람의 친구는 많아야 수천 명이다. 인접 행렬은 10¹² 칸이 필요하지만 인접 리스트는 정점 수 + 간선 수에 비례한다. 반대로 정점이 수백 개 이하이고 간선이 많으면 행렬이 간단하고 빠르다.

```
정점 0..3, 간선 {0,1} {0,2} {1,2} {2,3}

인접 행렬            인접 리스트
   0 1 2 3          0: [1, 2]
0 [0 1 1 0]         1: [0, 2]
1 [1 0 1 0]         2: [0, 1, 3]
2 [1 1 0 1]         3: [2]
3 [0 0 1 0]
```

무향 그래프의 인접 행렬은 대칭 행렬이다. 행렬을 k 번 곱한 Aᵏ 의 (i, j) 원소는 i 에서 j 로 가는 길이 k 짜리 산책의 수다. 그래프와 선형대수가 만나는 지점이다(017·018번 글).

### 탐색: BFS 와 DFS

그래프 알고리즘의 대부분은 두 탐색 위에 서 있다.

- **너비 우선 탐색(BFS)**: 큐를 쓴다. 시작점에서 가까운 정점부터 방문한다. 가중치 없는 그래프에서 최단 경로(간선 수 기준)를 찾는다.
- **깊이 우선 탐색(DFS)**: 스택(또는 재귀)을 쓴다. 한 방향으로 끝까지 갔다가 되돌아온다. 사이클 탐지, 위상 정렬, 연결 요소에 쓴다.

인접 리스트에서 두 탐색 모두 Θ(n + m) 시간이 걸린다. 모든 정점을 한 번, 모든 간선을 (무향이면 양쪽에서) 한 번씩 본다.

## 직접 해 보기

인접 리스트를 만들고, 악수 정리를 확인하고, BFS 로 최단 거리와 연결 요소를 구한다. 큐는 `collections.deque` 를 쓴다.

```python
from collections import deque, defaultdict

edges = [(0, 1), (0, 2), (1, 2), (2, 3), (4, 5)]
n = 7                              # 정점 6 은 고립 정점
adj = defaultdict(list)
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)

deg = [len(adj[v]) for v in range(n)]
print("차수:", deg, "합:", sum(deg), "2m:", 2 * len(edges))

# 인접 행렬과 A^2 (길이 2 산책의 수)
A = [[1 if v in adj[u] else 0 for v in range(n)] for u in range(n)]
A2 = [[sum(A[i][k] * A[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
print("0 에서 3 으로 가는 길이 2 산책:", A2[0][3])

def bfs(start):
    dist = {start: 0}
    q = deque([start])
    while q:
        u = q.popleft()
        for w in adj[u]:
            if w not in dist:
                dist[w] = dist[u] + 1
                q.append(w)
    return dist

print("0 에서의 거리:", bfs(0))

seen, components = set(), []
for v in range(n):
    if v not in seen:
        comp = set(bfs(v))
        seen |= comp
        components.append(sorted(comp))
print("연결 요소:", components)
```

실행 결과다.

```
차수: [2, 2, 3, 1, 1, 1, 0] 합: 10 2m: 10
0 에서 3 으로 가는 길이 2 산책: 1
0 에서의 거리: {0: 0, 1: 1, 2: 1, 3: 2}
연결 요소: [[0, 1, 2, 3], [4, 5], [6]]
```

차수가 홀수인 정점(2, 3, 4, 5)이 4 개, 즉 짝수 개라는 따름정리도 확인된다.

## 현업에서는

- **쿠버네티스 소유 관계.** 디플로이먼트는 레플리카셋을, 레플리카셋은 파드를 소유한다. 각 오브젝트의 `ownerReferences` 가 유향 간선이고, 가비지 컬렉터는 이 그래프를 따라 주인이 사라진 오브젝트를 지운다([Kubernetes, Garbage Collection](https://kubernetes.io/docs/concepts/architecture/garbage-collection/)). 연쇄 삭제(cascading deletion)는 그래프 탐색이다.
- **의존성 그래프.** 패키지 매니저, 빌드 도구, 워크플로 엔진은 작업을 DAG 로 표현하고 위상 정렬로 실행 순서를 정한다. 파이썬 표준 라이브러리에도 `graphlib.TopologicalSorter` 가 있다([Python, graphlib](https://docs.python.org/3/library/graphlib.html)).
- **장애 영향 범위.** 서비스 호출 그래프에서 한 서비스가 죽었을 때 영향을 받는 서비스는 "그 정점으로 가는 경로가 있는 정점들" 이다. 간선을 뒤집은 그래프에서 BFS 한 번이면 구한다.
- **라이브러리.** 큰 그래프 분석은 NetworkX 같은 라이브러리로 시작하는 경우가 많다([NetworkX Reference](https://networkx.org/documentation/stable/reference/index.html)). 직접 짜든 라이브러리를 쓰든, 어떤 표현을 쓰는지 알아야 메모리와 시간을 예측할 수 있다.

## 확인 문제

1. 정점 10 개인 완전 그래프 K₁₀ 의 간선 수는?
2. 모든 정점의 차수가 3 인 정점 7 개짜리 단순 무향 그래프가 존재하는가?
3. 정점 10⁵ 개, 간선 10⁶ 개인 그래프를 인접 행렬과 인접 리스트로 저장할 때 칸 수를 비교하라.
4. 가중치 없는 그래프의 최단 경로에 DFS 가 아니라 BFS 를 쓰는 이유는?

### 풀이

1. 10 × 9 / 2 = 45.
2. 없다. 차수 합이 21 로 홀수가 되어 악수 정리(차수 합 = 2m)에 어긋난다.
3. 행렬은 10¹⁰ 칸, 리스트는 정점 10⁵ 개 + 간선 항목 2 × 10⁶ 개(무향)로 약 2.1 × 10⁶ 칸이다.
4. BFS 는 거리 0, 1, 2, … 순서로 정점을 처음 방문하므로 처음 방문할 때의 거리가 곧 최단 거리다. DFS 는 먼 길로 먼저 도착할 수 있다.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 10장 Directed graphs, 12장 Simple Graphs — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- Thomas H. Cormen 외, *Introduction to Algorithms*, 4판, MIT Press, 20장 Elementary Graph Algorithms
- [Kubernetes Documentation, Garbage Collection](https://kubernetes.io/docs/concepts/architecture/garbage-collection/)
- [Python Documentation, collections.deque](https://docs.python.org/3/library/collections.html#collections.deque)
