---
layout: post
title: "[CS300 #076] 최단 경로 — 벨만포드와 플로이드워셜"
date: 2026-10-10 19:16:00 +0900
categories: [cs]
tags: [cs300, algorithms, graph, bellman-ford, floyd-warshall]
---

컴퓨터공학 300 주제 시리즈의 076번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

벨만포드는 모든 간선을 V−1 번 완화해 음수 간선이 있어도 한 출발점의 최단 거리를 구하고, 한 번 더 줄어드는지 보아 음수 사이클을 찾는다. O(VE). 플로이드워셜은 "경유지로 쓸 수 있는 정점" 을 하나씩 늘리는 DP 로 모든 쌍의 최단 거리를 Θ(V³) 에 구한다.

## 왜 필요한가

앞 글의 다익스트라는 음수 간선 하나에 조용히 틀린 답을 냈다. 음수 가중치는 생각보다 자주 나온다. 환율 차익(로그를 취하면 곱이 합이 되고 부호가 뒤집힌다), 보상이 있는 경로, 제약 조건 시스템(차분 제약)이 그렇다.

또 "모든 지점 사이의 거리표" 가 필요할 때가 있다. 정점마다 다익스트라를 돌릴 수도 있지만, 정점 수가 수백 이하라면 세 줄짜리 3중 루프인 플로이드워셜이 더 단순하고 음수 간선도 처리한다.

## 핵심 개념

### 벨만포드: 왜 V−1 번인가

음수 사이클이 없으면 최단 경로는 같은 정점을 두 번 지나지 않는다(사이클을 빼도 길이가 늘지 않으니까). 그러므로 최단 경로의 간선 수는 최대 V−1 개다.

모든 간선을 한 바퀴 완화하는 것을 "라운드" 라고 하자. 귀납적으로, k 라운드가 끝나면 **간선 k 개 이하로 이루어진 경로 중 최단** 인 거리가 모든 정점에 확정된다. 그래서 V−1 라운드면 충분하다.

```
for i in 1 .. V-1:
    for (u, v, w) in 모든 간선:
        relax(u, v, w)
for (u, v, w) in 모든 간선:
    if dist[u] + w < dist[v]: 음수 사이클 존재
```

V 번째 라운드에서도 거리가 줄면, 간선 V 개 이상을 쓰는 경로가 더 짧다는 뜻이다. 그런 경로는 반드시 사이클을 포함하고, 그 사이클의 합이 음수라는 뜻이다. 음수 사이클이 있으면 그 사이클을 계속 돌수록 짧아지므로 "최단 거리" 가 정의되지 않는다.

복잡도는 O(VE). 다익스트라보다 느리지만 가정이 약하다. 한 라운드에서 아무것도 안 바뀌면 바로 끝낼 수 있어 실제로는 더 빨리 끝나는 경우가 많다.

### 거리 벡터 라우팅

벨만포드는 분산 환경에 잘 맞는다. 각 라우터는 이웃이 알려 준 거리표만 보고 자기 표를 갱신하면 된다(완화). 전체 토폴로지를 몰라도 된다. RIP 이 이 방식이고, RFC 2453 은 RIP 이 Bellman-Ford(거리 벡터) 계열 알고리즘에 기반한다고 밝힌다.

대신 고질병이 있다. 링크가 끊겼을 때 라우터들이 서로의 낡은 정보를 믿고 거리를 1씩 올려 가는 **무한대로 세기(count to infinity)** 문제다. RIP 은 메트릭 16 을 "무한대" 로 정해 이 과정을 끊는다. 그래서 RIP 네트워크의 경로는 최대 15홉으로 제한된다.

### 플로이드워셜: 경유지를 늘리는 DP

정점을 0..V−1 로 번호 붙인다.

**상태**: d_k[i][j] = 경유지로 0..k−1 번 정점만 쓸 수 있을 때 i 에서 j 로 가는 최단 거리.

**점화식**: 정점 k 를 경유지로 새로 허용하면, 최단 경로가 k 를 지나거나 안 지나거나 둘 중 하나다.

```
d_{k+1}[i][j] = min( d_k[i][j],  d_k[i][k] + d_k[k][j] )
```

k 를 바깥 루프로 두고 표 하나를 덮어쓰면 된다. 덮어써도 되는 이유는 k 행과 k 열의 값이 이번 라운드에서 바뀌지 않기 때문이다(d[k][k] ≥ 0 이면 d[i][k] + d[k][k] ≥ d[i][k]).

```
for k in range(V):
    for i in range(V):
        for j in range(V):
            d[i][j] = min(d[i][j], d[i][k] + d[k][j])
```

루프 순서가 핵심이다. k 가 가장 바깥이어야 한다. 순서를 바꾸면 DP 의 의미가 깨진다.

끝난 뒤 어떤 i 에 대해 d[i][i] < 0 이면 i 를 지나는 음수 사이클이 있다.

### 셋 비교

| | 다익스트라 | 벨만포드 | 플로이드워셜 |
|---|---|---|---|
| 문제 | 단일 출발 | 단일 출발 | 모든 쌍 |
| 음수 간선 | 불가 | 가능 | 가능 |
| 음수 사이클 탐지 | 불가 | 가능 | 가능 |
| 시간 | O((V+E) log V) | O(VE) | Θ(V³) |
| 공간 | O(V + E) | O(V + E) | Θ(V²) |

모든 쌍이 필요하고 그래프가 희소하며 음수 간선이 있다면, 벨만포드 한 번으로 재가중치를 한 뒤 다익스트라를 V 번 돌리는 존슨(Johnson) 알고리즘이 O(VE log V) 로 더 빠르다.

## 직접 해 보기

앞 글에서 다익스트라가 틀렸던 그래프를 벨만포드로 다시 풀고, 음수 사이클을 만들어 탐지하고, 플로이드워셜로 모든 쌍 거리와 경로를 구한다. python3 로 실행해 확인했다.

```python
INF = float("inf")

def bellman_ford(n, edges, s):
    dist = [INF] * n; dist[s] = 0
    for i in range(n - 1):                 # V-1 라운드
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w; changed = True
        if not changed:                    # 더 줄 게 없으면 조기 종료
            break
    for u, v, w in edges:                  # 한 번 더 줄면 음수 사이클
        if dist[u] + w < dist[v]:
            return dist, True
    return dist, False

# 0=S, 1=A, 2=B, 3=T (앞 글의 음수 간선 예제)
edges = [(0, 1, 1), (0, 2, 5), (1, 3, 1), (2, 1, -10)]
print("벨만포드:", bellman_ford(4, edges, 0))

cyc = edges + [(3, 2, 2)]                  # B→A→T→B 합 = -10 + 1 + 2 = -7
print("음수 사이클:", bellman_ford(4, cyc, 0))

def floyd_warshall(n, edges):
    d = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    nxt = [[None] * n for _ in range(n)]
    for u, v, w in edges:
        d[u][v] = w; nxt[u][v] = v
    for k in range(n):                     # k 를 경유지로 허용
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
                    nxt[i][j] = nxt[i][k]
    return d, nxt

def fw_path(nxt, i, j):
    if nxt[i][j] is None:
        return []
    p = [i]
    while i != j:
        i = nxt[i][j]; p.append(i)
    return p

E = [(0, 1, 3), (0, 2, 8), (1, 2, 2), (2, 3, 1), (3, 0, 4), (1, 3, 7)]
d, nxt = floyd_warshall(4, E)
for row in d:
    print(" ".join(f"{x:>3}" for x in row))
print("0→3 경로:", fw_path(nxt, 0, 3), "| 대각선에 음수 없음:", all(d[i][i] >= 0 for i in range(4)))
```

출력:

```
벨만포드: ([0, -5, 5, -4], False)
음수 사이클: ([0, -12, -3, -5], True)
  0   3   5   6
  7   0   2   3
  5   8   0   1
  4   7   9   0
0→3 경로: [0, 1, 2, 3] | 대각선에 음수 없음: True
```

벨만포드는 A = −5, T = −4 를 정확히 찾았다. 다익스트라가 놓친 값이다. 음수 사이클을 넣으면 탐지 플래그가 True 가 되고, 그때의 거리 값은 몇 라운드를 돌았느냐에 따라 달라지는 무의미한 숫자다. 플로이드워셜에서 0→3 은 직행 간선이 없고, 1→3 직행(7)보다 1→2→3(2+1=3) 이 짧아 0→1→2→3 = 6 이 되었다.

## 현업에서는

- **RIP 과 거리 벡터.** 작은 사내망이나 실습 환경에서 아직 볼 수 있다. 홉 수 15 제한과 느린 수렴은 위의 알고리즘 성질에서 그대로 나온다. 규모가 커지면 링크 상태 방식(OSPF, 다익스트라)으로 간다.
- **차익 거래 탐지.** 환율 r 을 가중치 −log r 로 바꾸면 "곱이 1보다 큰 환전 사이클" 이 "합이 음수인 사이클" 이 된다. 벨만포드의 음수 사이클 탐지가 곧 차익 기회 탐지다.
- **거리표 미리 계산.** 데이터센터 랙 사이 지연, 사무실 지점 사이 이동 비용처럼 정점이 수백 개 이하인 고정 그래프는 플로이드워셜로 한 번 표를 만들어 두고 조회만 한다.
- **도달 가능성.** 가중치 대신 불리언 OR/AND 로 같은 3중 루프를 돌리면 "i 에서 j 로 갈 수 있는가" 의 표(추이 폐포)가 나온다. Warshall 의 1962년 논문이 이 형태다. 권한 상속, 역할 계층에서 "이 역할이 간접적으로 저 권한을 갖는가" 를 미리 계산할 때 쓸 수 있다.

## 확인 문제

1. 벨만포드에서 라운드 수가 V−1 이면 충분한 이유는?
2. 플로이드워셜에서 루프 순서를 i, j, k (k 가 가장 안쪽)로 바꾸면 왜 틀리는가?
3. 음수 사이클이 있는 그래프에서 "최단 경로" 가 정의되지 않는 이유는?
4. V = 1000, E = 5000 인 희소 그래프에서 모든 쌍 최단 거리가 필요하고 가중치가 모두 양수다. 플로이드워셜과 다익스트라 V번 중 무엇이 나은가?

### 풀이

1. 음수 사이클이 없으면 최단 경로는 단순 경로이고 간선이 최대 V−1 개다. k 라운드 후 간선 k 개 이하 경로의 최단값이 확정되므로 V−1 라운드면 모든 최단 경로가 확정된다.
2. d[i][j] 를 계산하는 시점에 d[i][k], d[k][j] 가 아직 다른 경유지를 고려하지 않은 값이라 "0..k 경유" 라는 상태 의미가 성립하지 않는다.
3. 사이클을 한 번 더 돌 때마다 경로 길이가 줄어 하한이 없다.
4. 다익스트라 V번이 O(V(V+E) log V) ≈ 1000 × 6000 × 10 = 6×10⁷ 수준이고, 플로이드워셜은 V³ = 10⁹ 이다. 다익스트라 V번이 낫다.

## 더 읽을거리 (References)

- IETF, [RFC 2453 — RIP Version 2](https://www.rfc-editor.org/rfc/rfc2453), 3.4절 거리 벡터 알고리즘과 무한대 16
- Richard Bellman, "On a Routing Problem", *Quarterly of Applied Mathematics* 16(1), 1958.
- Robert W. Floyd, "Algorithm 97: Shortest Path", *Communications of the ACM* 5(6), 1962. / Stephen Warshall, "A Theorem on Boolean Matrices", *Journal of the ACM* 9(1), 1962.
- NIST Dictionary of Algorithms and Data Structures, [Bellman-Ford algorithm](https://xlinux.nist.gov/dads/HTML/bellmanford.html), [Floyd-Warshall algorithm](https://xlinux.nist.gov/dads/HTML/floydWarshall.html)
