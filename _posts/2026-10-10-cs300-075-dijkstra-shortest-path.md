---
layout: post
title: "[CS300 #075] 최단 경로 — 다익스트라, 가장 가까운 정점부터 확정하기"
date: 2026-10-10 19:15:00 +0900
categories: [cs]
tags: [cs300, algorithms, graph, dijkstra, shortest-path]
---

컴퓨터공학 300 주제 시리즈의 075번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

다익스트라 알고리즘은 시작점에서 가장 가까운 미확정 정점을 하나씩 확정하고, 그 정점에서 나가는 간선으로 이웃의 거리를 줄인다(relax). 간선 가중치가 모두 0 이상일 때만 옳고, 이진 힙을 쓰면 O((V + E) log V) 다.

## 왜 필요한가

BFS 는 간선 개수가 가장 적은 경로를 찾는다. 하지만 실제 네트워크와 지도에서는 간선마다 비용이 다르다. 고속도로 두 구간이 국도 한 구간보다 빠를 수 있고, 대역폭이 큰 링크 두 홉이 느린 링크 한 홉보다 나을 수 있다.

다익스트라는 1959년 Edsger W. Dijkstra 가 짧은 논문 "A Note on Two Problems in Connexion with Graphs" 에서 발표했다. 같은 논문에 최소 신장 트리 문제도 함께 다뤘다. 오늘날에도 링크 상태 라우팅 프로토콜 OSPF 가 라우팅 표를 계산할 때 이 알고리즘을 쓴다고 RFC 2328 에 명시되어 있다.

## 핵심 개념

### 완화(relaxation)

모든 최단 경로 알고리즘의 기본 연산이다.

```
relax(u, v, w):
    if dist[u] + w < dist[v]:
        dist[v] = dist[u] + w
        prev[v] = u
```

"u 를 거쳐 v 로 가는 게 지금까지 아는 것보다 짧으면 갱신한다." 다익스트라와 벨만포드는 **어떤 순서로 완화하는가** 만 다르다.

### 알고리즘

```
dist[s] = 0, 나머지 ∞
우선순위 큐에 (0, s)
while 큐가 비지 않음:
    (d, u) = 큐에서 dist 가 가장 작은 것 꺼내기
    if u 가 이미 확정됨: 건너뜀
    u 확정
    for (v, w) in u 의 간선:
        relax(u, v, w), 줄었으면 큐에 (dist[v], v) 넣기
```

예제 그래프에서 A 를 시작점으로 하면:

```
간선(방향, 가중치)
A→B 4   A→C 1   C→B 2   B→D 1   C→D 5   D→E 3

확정 순서와 거리
A(0) → C(1) → B(3: A→C→B) → D(4: A→C→B→D) → E(7)
A→B 직행(4)보다 A→C→B(1+2=3)가 짧다.
```

### 왜 맞는가: 음이 아닌 가중치

큐에서 꺼낸 정점 u 의 거리가 d 라고 하자. 아직 확정되지 않은 다른 모든 정점의 거리는 d 이상이다. 그런 정점을 거쳐 u 로 돌아오는 경로는, 간선이 음수가 아니므로 길이가 d 이상이다. 그러므로 d 보다 짧은 경로는 존재하지 않고, u 를 확정해도 된다.

이 논증의 핵심 가정이 "간선이 음수가 아니다" 다. 음수 간선이 있으면 멀리 돌아가는 경로가 오히려 짧아질 수 있어 확정이 틀린다. 아래 예제에서 실제로 확인한다. 음수 간선이 있으면 다음 글의 벨만포드를 쓴다.

### 복잡도

| 우선순위 큐 | 시간 |
|---|---|
| 정렬 안 된 배열 (원 논문 방식) | O(V²) |
| 이진 힙 | O((V + E) log V) |
| 피보나치 힙 | O(E + V log V) |

이진 힙에는 "키 감소(decrease-key)" 연산이 없는 경우가 많다(Python `heapq` 도 없다). 그래서 거리가 줄 때마다 새 항목을 넣고, 꺼냈을 때 이미 더 짧은 값으로 확정된 낡은 항목이면 무시한다(lazy deletion). 힙 크기가 최대 E 까지 늘지만 log E ≤ 2 log V 라 복잡도는 같다.

조밀한 그래프(E ≈ V²)에서는 단순 배열 O(V²) 가 이진 힙 O(V² log V) 보다 낫다. 그래프 모양에 따라 구현을 고른다.

### 단일 쌍 질의와 조기 종료

목표 정점 t 하나만 필요하면 t 가 큐에서 꺼내지는 순간 멈춰도 된다. 그 순간 t 의 거리가 확정되기 때문이다. 지도 서비스처럼 좌표 정보가 있으면 A* 탐색이 휴리스틱으로 탐색 범위를 더 줄인다.

## 직접 해 보기

`heapq` 로 다익스트라를 짜고, 경로를 복원하고, 음수 간선에서 틀리는 것을 확인한다. python3 로 실행해 확인했다.

```python
import heapq

def dijkstra(g, s):
    dist, prev, pq, pops = {s: 0}, {}, [(0, s)], 0
    while pq:
        d, u = heapq.heappop(pq)
        pops += 1
        if d > dist[u]:
            continue                      # 이미 더 짧은 값으로 확정된 낡은 항목
        for v, w in g[u]:
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd; prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev, pops

def path(prev, s, t):
    p = [t]
    while p[-1] != s:
        p.append(prev[p[-1]])
    return p[::-1]

g = {"A": [("B", 4), ("C", 1)], "B": [("D", 1)], "C": [("B", 2), ("D", 5)],
     "D": [("E", 3)], "E": []}
dist, prev, pops = dijkstra(g, "A")
print("거리:", dist)
print("A→E 경로:", path(prev, "A", "E"), "| 힙에서 꺼낸 횟수:", pops)

# 음수 간선이 있으면 틀린다
neg = {"S": [("A", 1), ("B", 5)], "A": [("T", 1)], "B": [("A", -10)], "T": []}
def dijkstra_strict(g, s):        # 교과서형: 한 번 꺼낸 정점은 다시 보지 않음
    dist, done, pq = {s: 0}, set(), [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        for v, w in g[u]:
            if v not in done and d + w < dist.get(v, float("inf")):
                dist[v] = d + w; heapq.heappush(pq, (dist[v], v))
    return dist
print("음수 간선에서 다익스트라:", dijkstra_strict(neg, "S"))
```

출력:

```
거리: {'A': 0, 'B': 3, 'C': 1, 'D': 4, 'E': 7}
A→E 경로: ['A', 'C', 'B', 'D', 'E'] | 힙에서 꺼낸 횟수: 7
음수 간선에서 다익스트라: {'S': 0, 'A': 1, 'B': 5, 'T': 2}
```

정점은 5개인데 힙에서 7번 꺼냈다. B 와 D 의 거리가 한 번씩 줄면서 낡은 항목이 남았고, `d > dist[u]` 검사로 건너뛰었다.

음수 간선 그래프의 실제 최단 거리는 A = 5 − 10 = −5, T = −4 다. 다익스트라는 A 를 거리 1 로 먼저 확정해 버려서, 나중에 B 를 거쳐 더 짧은 길을 발견해도 반영하지 못했다. 정당성 논증의 가정이 깨지면 결과가 조용히 틀린다. 오류도 경고도 없다는 점이 무섭다.

## 현업에서는

- **OSPF·IS-IS 라우팅.** 링크 상태 프로토콜에서 각 라우터는 전체 토폴로지를 알고, 자신을 뿌리로 다익스트라를 돌려 최단 경로 트리를 만든다. RFC 2328 16.1절이 OSPF 의 이 계산을 기술한다. 링크 비용(cost)은 음수가 아니므로 가정이 성립한다.
- **지도·내비게이션.** 기본 골격은 다익스트라이고, 실제 서비스는 A* 와 사전 계산 기법을 더해 대륙 규모 도로망에서 빠르게 답한다.
- **서비스 메시와 지연 기반 라우팅.** 지연 시간을 가중치로 두면 "가장 빠른 경로" 문제다. 측정값이 계속 바뀌므로 주기적으로 다시 계산한다.
- **게임과 로봇.** 격자 위 이동 비용이 지형마다 다를 때 다익스트라나 A* 로 경로를 찾는다.

## 확인 문제

1. 가중치가 모두 1 인 그래프에서 다익스트라와 BFS 의 결과는 같은가? 어느 쪽이 더 효율적인가?
2. lazy deletion 방식에서 `if d > dist[u]: continue` 를 빼면 결과가 틀리는가?
3. 모든 간선에 같은 큰 상수를 더해 음수를 없애면 다익스트라로 원래 최단 경로를 구할 수 있는가?
4. 조밀한 그래프에서 배열 기반 O(V²) 구현이 이진 힙보다 나은 이유는?

### 풀이

1. 거리는 같다. BFS 는 Θ(V + E) 로 힙의 log 비용이 없어 더 효율적이다.
2. 결과는 맞다. 다만 낡은 항목으로도 이웃을 다시 훑어 불필요한 작업이 늘어난다. 완화 조건이 엄격한 부등호라 잘못된 값으로 갱신되지는 않는다.
3. 아니다. 간선 수가 많은 경로가 더 크게 불이익을 받아 최단 경로가 바뀔 수 있다. 음수 간선이 있으면 벨만포드를 쓰거나, 존슨 알고리즘처럼 경로 순서를 보존하는 재가중치를 쓴다.
4. E ≈ V² 이면 힙 버전은 O(V² log V) 이고 배열 버전은 O(V²) 다. 매번 최솟값을 V 칸에서 찾는 비용이 간선 처리 비용에 묻힌다.

## 더 읽을거리 (References)

- E. W. Dijkstra, [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390), *Numerische Mathematik* 1, 1959
- IETF, [RFC 2328 — OSPF Version 2](https://www.rfc-editor.org/rfc/rfc2328), 16.1절
- Python 공식 문서, [heapq — Heap queue algorithm](https://docs.python.org/3/library/heapq.html)
- NIST Dictionary of Algorithms and Data Structures, [Dijkstra's algorithm](https://xlinux.nist.gov/dads/HTML/dijkstraalgo.html)
