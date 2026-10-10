---
layout: post
title: "[CS300 #054] 분리 집합 (Union-Find) — 같은 무리인가를 거의 상수 시간에"
date: 2026-10-10 18:54:00 +0900
categories: [cs]
tags: [cs300, data-structures, union-find, disjoint-set, kruskal]
---

컴퓨터공학 300 주제 시리즈의 054번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

분리 집합(Union-Find)은 원소들을 서로 겹치지 않는 무리로 나누어 관리하며 "두 원소가 같은 무리인가(find)"와 "두 무리를 합쳐라(union)" 두 연산만 제공하는 구조로, 경로 압축과 크기 기준 합치기를 함께 쓰면 연산당 비용이 사실상 상수가 된다.

## 왜 필요한가

네트워크에 케이블이 하나씩 연결될 때마다 "지금 A 와 B 가 통신 가능한가?"를 물어야 한다고 하자. 매번 BFS 를 돌리면 질문마다 O(V + E) 다. 연결은 계속 늘어나기만 하고, 알고 싶은 것은 경로가 아니라 "같은 덩어리인가" 뿐이다.

이렇게 **합치기만 하고 쪼개지 않는** 연결 관계에는 Union-Find 가 정확히 맞는다. 크루스칼의 최소 신장 트리, 이미지에서 연결된 픽셀 덩어리 찾기, 동치 관계 묶기(같은 사람의 여러 계정 합치기), 타입 추론의 단일화, 퍼콜레이션 시뮬레이션이 대표적인 쓰임이다. 코드는 스무 줄 남짓인데 분석은 알고리즘 이론에서 가장 놀라운 결과 중 하나로 이어진다.

## 핵심 개념

### 표현: 부모 포인터 숲

각 무리를 트리 하나로 나타내고, 트리의 **루트**를 그 무리의 대표로 삼는다. 저장하는 것은 원소마다 부모 하나뿐이다. 루트는 자기 자신을 부모로 가진다.

```
parent: [0, 0, 1, 3, 3, 5]

  무리 {0,1,2}     무리 {3,4}     무리 {5}
      0               3              5
      |               |
      1               4
      |
      2
```

- `find(x)`: 부모를 따라 루트까지 올라가 루트를 돌려준다.
- `union(a, b)`: 두 루트를 찾아, 한 루트의 부모를 다른 루트로 바꾼다.
- `a` 와 `b` 가 같은 무리인지는 `find(a) == find(b)` 로 안다.

### 그냥 하면 느리다

아무 생각 없이 합치면 트리가 한 줄로 길어질 수 있다. 0, 1, 2, … 를 차례로 합치며 매번 기존 무리의 루트를 새 원소 아래에 붙이면 높이 n 의 사슬이 된다. 그러면 `find` 가 O(n) 이다.

### 최적화 1: 크기(또는 랭크) 기준 합치기

합칠 때 **작은 트리를 큰 트리의 루트 아래에** 붙인다. 그러면 어떤 원소의 깊이가 1 늘어날 때마다 그 원소가 속한 트리의 크기는 적어도 2배가 된다. 크기는 n 을 넘을 수 없으니 깊이는 log₂ n 을 넘지 못한다. 이것만으로 `find` 가 O(log n) 이 된다. 크기 대신 높이의 상한인 **랭크**를 써도 같다.

### 최적화 2: 경로 압축

`find(x)` 로 루트를 찾았으면, 돌아오면서 지나온 모든 노드의 부모를 루트로 바꿔 둔다. 다음에 그 노드들을 찾을 때는 한 번에 루트로 간다.

```
find(2) 전          find(2) 후
    0                   0
    |                 / | \
    1                1  2  (2 도 0 에 직접)
    |
    2
```

변형으로, 지나가며 각 노드를 할아버지에 연결하는 **경로 반감(path halving)** 이 있다. 한 번의 순회로 끝나 구현이 간단하다. SciPy 의 `DisjointSet` 은 문서에 경로 반감과 크기 기준 합치기를 구현했다고 적는다([SciPy — DisjointSet](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.DisjointSet.html)).

### 둘을 함께 쓰면: 역 아커만 함수

두 최적화를 함께 쓰면 연산 m 개의 총비용이 O(m · α(n)) 이다. 여기서 α 는 **역 아커만 함수**로, 아커만 함수가 상상할 수 없이 빨리 자라는 만큼 상상할 수 없이 느리게 자란다. 실제 컴퓨터가 다룰 수 있는 어떤 n 에서도 α(n) 은 4 를 넘지 않는다. 그래서 "사실상 상수"라고 말한다. 이 상한은 Tarjan 이 1975년 논문에서 증명했고, 이 계열 알고리즘으로는 더 나아질 수 없다는 하한도 그 뒤 연구들로 정리되었다.

| 방식 | find 최악 | m 개 연산 총비용 |
|---|---|---|
| 최적화 없음 | O(n) | O(m · n) |
| 크기 기준 합치기만 | O(log n) | O(m log n) |
| 경로 압축만 | 분할 상환 O(log n) | O(m log n) 수준 |
| 둘 다 | 분할 상환 O(α(n)) | O(m · α(n)) |

### 못 하는 것

Union-Find 는 **쪼개기를 지원하지 않는다.** 연결이 끊어지는 상황(간선 삭제)에는 쓸 수 없고, 동적 연결성 문제는 훨씬 복잡한 구조가 필요하다. 또 "어떤 경로로 연결되었나"도 모른다. 오직 같은 무리인지만 안다. 이 단순함이 속도의 원천이다.

## 직접 해 보기

경로 압축과 크기 기준 합치기를 켜고 끌 수 있는 Union-Find 를 만들고, 크루스칼 알고리즘에 써 본 뒤, 일부러 만든 최악의 사슬에서 최적화 효과를 잰다.

```python
class DSU:
    def __init__(self, n, smart=True):
        self.parent = list(range(n))
        self.size = [1] * n
        self.smart = smart
        self.steps = 0                     # 부모 포인터를 따라간 횟수

    def find(self, x):
        root = x
        while self.parent[root] != root:
            root = self.parent[root]; self.steps += 1
        if self.smart:                     # 경로 압축: 지나온 노드를 루트에 직접 연결
            while self.parent[x] != root:
                self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.smart and self.size[ra] < self.size[rb]:
            ra, rb = rb, ra                # 크기 기준 합치기: 작은 쪽을 큰 쪽 아래로
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True

# 1) 크루스칼 최소 신장 트리
edges = [(7, "A", "B"), (5, "A", "D"), (8, "B", "C"), (9, "B", "D"), (7, "B", "E"),
         (5, "C", "E"), (15, "D", "E"), (6, "D", "F"), (8, "E", "F"), (9, "E", "G"), (11, "F", "G")]
names = sorted({v for _, a, b in edges for v in (a, b)})
idx = {v: i for i, v in enumerate(names)}
d = DSU(len(names))
mst = [(w, a, b) for w, a, b in sorted(edges) if d.union(idx[a], idx[b])]
print("MST:", mst, " 총 가중치:", sum(w for w, _, _ in mst))

# 2) 최적화 유무 비교: 일부러 긴 사슬을 만든 뒤 find 를 반복
N = 4_000
for smart in (False, True):
    d = DSU(N, smart)
    for i in range(1, N):
        d.union(i, i - 1)                  # 최적화가 없으면 길이 N 의 사슬이 된다
    d.steps = 0
    for i in range(N):
        d.find(i)
    print(f"{'최적화 O' if smart else '최적화 X'}: find {N:,}번에 포인터 이동 {d.steps:,}회")
```

```
MST: [(5, 'A', 'D'), (5, 'C', 'E'), (6, 'D', 'F'), (7, 'A', 'B'), (7, 'B', 'E'), (9, 'E', 'G')]  총 가중치: 39
최적화 X: find 4,000번에 포인터 이동 7,998,000회
최적화 O: find 4,000번에 포인터 이동 3,999회
```

크루스칼은 간선을 가중치 순으로 보면서 "두 끝이 이미 같은 무리면 버리고, 아니면 채택하고 합친다"를 반복한다. 사이클 검사가 `union` 의 반환값 하나로 끝난다. 정점 7개에 간선 6개가 채택되어 신장 트리가 완성되었다.

최악의 사슬에서는 차이가 극적이다. 최적화가 없으면 0 + 1 + … + 3999 ≈ 800만 번 포인터를 따라간다. 최적화를 켜면 크기 기준 합치기 덕분에 애초에 사슬이 생기지 않아, 루트가 아닌 원소마다 한 번씩 3999회로 끝난다. n 을 10배 늘리면 앞쪽은 100배, 뒤쪽은 10배 늘어난다.

## 현업에서는

- **네트워크·클러스터 연결성.** 노드 사이 링크 목록이 주어졌을 때 "몇 개 조각으로 나뉘었나", "이 두 노드가 같은 조각인가"를 빠르게 답한다. 링크가 하나씩 추가되는 로그를 재생하면서 언제 전체가 하나로 연결되는지 찾는 데도 쓴다.
- **엔터티 해석(중복 합치기).** 이메일이 같으면 같은 사람, 전화번호가 같으면 같은 사람… 같은 규칙으로 계정을 묶을 때, 규칙 하나를 만족할 때마다 `union` 하면 최종 무리가 곧 동일인 그룹이다. 동치 관계의 추이적 폐포를 구하는 표준 방법이다.
- **이미지 처리.** 연결 요소 라벨링(같은 색으로 이어진 픽셀 덩어리 찾기)의 2단계 알고리즘이 Union-Find 로 라벨 동치를 정리한다.
- **컴파일러 타입 추론.** 힌들리-밀너 계열 타입 추론의 단일화(unification)는 "이 두 타입 변수는 같다"를 계속 합쳐 나가는 과정이라 Union-Find 로 구현하는 경우가 많다.

## 확인 문제

1. `parent = [0, 0, 1, 1, 4, 4]` 일 때 무리는 몇 개이고 각각 무엇인가?
2. 크기 기준 합치기만 써도 트리 높이가 log₂ n 을 넘지 않는 이유는?
3. 경로 압축은 `find` 결과를 바꾸는가?
4. 크루스칼 알고리즘에서 Union-Find 는 어떤 역할을 하는가?
5. 간선이 추가되기도 하고 삭제되기도 하는 그래프의 연결성 질의에 기본 Union-Find 를 쓸 수 없는 이유는?

### 풀이

1. 두 개. {0, 1, 2, 3} (루트 0), {4, 5} (루트 4).
2. 원소의 깊이가 1 늘어나는 것은 그 원소가 속한 작은 트리가 더 큰 트리 밑으로 들어갈 때뿐이고, 그때 무리 크기가 2배 이상이 된다. 2배를 log₂ n 번 넘게 할 수 없다.
3. 바꾸지 않는다. 대표(루트)는 그대로이고 트리 모양만 납작해진다.
4. 간선의 두 끝이 이미 같은 무리인지(사이클이 생기는지) 검사하고, 채택한 간선의 두 무리를 합친다.
5. Union-Find 는 합치기만 지원하고 무리를 쪼개는 연산이 없다. 간선 삭제로 무리가 나뉘는 것을 반영할 수 없다.

## 더 읽을거리 (References)

- Robert Sedgewick, Kevin Wayne, [Algorithms, 4th ed. — 1.5 Case Study: Union-Find](https://algs4.cs.princeton.edu/15uf/)
- SciPy Documentation, [scipy.cluster.hierarchy.DisjointSet](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.DisjointSet.html)
- Robert E. Tarjan, "Efficiency of a Good But Not Linear Set Union Algorithm", *Journal of the ACM* 22(2), 1975
- Robert E. Tarjan, Jan van Leeuwen, "Worst-case Analysis of Set Union Algorithms", *Journal of the ACM* 31(2), 1984
