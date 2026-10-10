---
layout: post
title: "[CS300 #078] 위상 정렬 — 의존성을 지키는 실행 순서 만들기"
date: 2026-10-10 19:18:00 +0900
categories: [cs]
tags: [cs300, algorithms, graph, topological-sort, dag]
---

컴퓨터공학 300 주제 시리즈의 078번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

위상 정렬은 방향 그래프의 정점을 "모든 간선 u→v 에 대해 u 가 v 보다 앞" 이 되도록 일렬로 세운다. 사이클이 없는 방향 그래프(DAG)에서만 가능하다. 진입 차수가 0 인 정점부터 빼는 Kahn 방식과 DFS 종료 순서를 뒤집는 방식이 있고, 둘 다 Θ(V + E) 다.

## 왜 필요한가

빌드 도구는 라이브러리를 먼저 컴파일하고 그걸 쓰는 실행 파일을 나중에 컴파일해야 한다. 패키지 관리자는 의존 패키지를 먼저 설치한다. 데이터 파이프라인은 원천 테이블을 만든 뒤 집계 테이블을 만든다. 서비스 기동도 설정과 저장소가 먼저, 앱이 나중이다.

이 모든 것이 "선행 관계를 어기지 않는 순서" 를 요구한다. 그리고 순환 의존이 있으면 그런 순서는 존재하지 않으므로, 그 사실을 찾아 알려 주는 것도 같은 알고리즘의 몫이다.

## 핵심 개념

### DAG 와 위상 순서

```
config ──→ cache ──→ app ──→ ingress
   │                  ↑
   └──→ db ───────────┘
          ↑
volume ───┘
(config → app 간선도 있음)
```

간선 X → Y 는 "X 가 끝나야 Y 를 시작할 수 있다" 를 뜻한다. 가능한 위상 순서는 하나가 아니다. config, volume, cache, db, app, ingress 도 되고 volume, config, db, cache, app, ingress 도 된다. 선행 관계만 지키면 나머지 순서는 자유다.

사이클이 있으면 불가능하다. A → B → A 라면 A 는 B 보다 앞이면서 뒤여야 한다. 거꾸로, 사이클이 없으면 위상 순서가 반드시 존재한다(아래 Kahn 알고리즘이 구성적으로 보여 준다).

### Kahn 알고리즘 (1962)

```
각 정점의 진입 차수(들어오는 간선 수)를 센다
진입 차수 0 인 정점을 모두 큐에 넣는다
while 큐가 비지 않음:
    u 를 꺼내 결과에 붙인다
    u → v 간선마다 v 의 진입 차수를 1 줄이고, 0 이 되면 큐에 넣는다
결과에 모든 정점이 들어갔으면 성공, 아니면 사이클이 있다
```

진입 차수 0 은 "기다릴 게 없다" 는 뜻이다. 그런 정점을 처리하면 그 정점을 기다리던 정점들의 대기가 하나 준다. 사이클에 속한 정점들은 서로를 기다리므로 진입 차수가 영원히 0 이 되지 않고, 결과에서 빠진다. 그래서 사이클 탐지가 공짜로 따라온다.

각 정점이 큐에 한 번, 각 간선이 한 번 처리되므로 Θ(V + E).

### DFS 방식

DFS 로 정점을 방문하고, 정점의 모든 후손 방문이 끝나는(finish) 순간 기록한다. **종료 시각의 역순** 이 위상 순서다. u → v 간선이 있으면 v 가 u 보다 먼저 끝나기 때문이다(v 를 u 안에서 방문하든, 이미 끝난 상태든).

아래 예제처럼 간선 방향을 "선행 작업 쪽" 으로 저장했다면(X 의 목록에 X 가 기다리는 것들), 종료 순서를 뒤집지 않고 그대로 쓰면 된다. 표현 방향에 따라 뒤집을지 말지가 바뀌니 주의한다.

사이클 탐지는 정점을 세 색으로 칠해서 한다. 흰색(미방문), 회색(방문 중, 재귀 스택 위), 검은색(완료). 탐색 중 회색 정점을 다시 만나면 사이클이다.

### 병렬 실행 단계

Kahn 알고리즘에서 "현재 큐에 있는 것들" 은 서로 의존하지 않아 동시에 실행할 수 있다. 큐를 단계별로 통째로 비우면, 각 단계가 병렬로 돌릴 수 있는 작업 묶음이 된다. 단계 수는 DAG 의 가장 긴 경로 길이이고, 이것이 무한한 일꾼이 있을 때의 최소 완료 시간(임계 경로)이다.

Python 3.9 부터 표준 라이브러리 `graphlib.TopologicalSorter` 가 이 방식을 제공한다. `get_ready()` 로 지금 실행 가능한 노드를 받고, 끝나면 `done()` 으로 알린다.

## 직접 해 보기

서비스 기동 순서를 예로 Kahn, DFS, `graphlib` 세 방법을 비교하고, 사이클을 일부러 만든다. python3 로 실행해 확인했다.

```python
from collections import deque
from graphlib import TopologicalSorter, CycleError

# "X: [Y, ...]" = X 를 하려면 Y 가 먼저 끝나야 한다 (선행 작업)
deps = {
    "app":     ["db", "cache", "config"],
    "db":      ["volume", "config"],
    "cache":   ["config"],
    "ingress": ["app"],
    "volume":  [],
    "config":  [],
}

def kahn(deps):
    nodes = set(deps) | {d for ds in deps.values() for d in ds}
    indeg = {n: 0 for n in nodes}
    out = {n: [] for n in nodes}
    for x, ds in deps.items():
        for d in ds:
            out[d].append(x); indeg[x] += 1     # 간선 d → x
    q = deque(sorted(n for n in nodes if indeg[n] == 0))
    order = []
    while q:
        u = q.popleft(); order.append(u)
        for v in sorted(out[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(nodes):
        raise ValueError("사이클 있음: " + str(sorted(n for n in nodes if indeg[n] > 0)))
    return order

def dfs_topo(deps):
    WHITE, GRAY, BLACK = 0, 1, 2
    nodes = set(deps) | {d for ds in deps.values() for d in ds}
    color = {n: WHITE for n in nodes}; order = []
    def visit(u):
        color[u] = GRAY
        for d in sorted(deps.get(u, [])):       # 선행 작업부터 끝낸다
            if color[d] == GRAY:
                raise ValueError(f"사이클: {u} → {d}")
            if color[d] == WHITE:
                visit(d)
        color[u] = BLACK
        order.append(u)                          # 끝나는 순간 기록
    for n in sorted(nodes):
        if color[n] == WHITE:
            visit(n)
    return order

print("Kahn    :", kahn(deps))
print("DFS     :", dfs_topo(deps))

ts = TopologicalSorter(deps)
ts.prepare()
stage = 0
while ts.is_active():
    ready = sorted(ts.get_ready())               # 지금 동시에 시작해도 되는 것들
    print(f"단계 {stage}: {ready}")
    ts.done(*ready); stage += 1

bad = dict(deps, config=["app"])                 # config 가 app 을 기다리게 → 사이클
try:
    list(TopologicalSorter(bad).static_order())
except CycleError as e:
    print("CycleError:", e.args[1])
```

출력:

```
Kahn    : ['config', 'volume', 'cache', 'db', 'app', 'ingress']
DFS     : ['config', 'cache', 'volume', 'db', 'app', 'ingress']
단계 0: ['config', 'volume']
단계 1: ['cache', 'db']
단계 2: ['app']
단계 3: ['ingress']
CycleError: ['app', 'config', 'app']
```

Kahn 과 DFS 의 순서가 다르지만 둘 다 올바르다. 위상 순서는 유일하지 않다. `graphlib` 의 단계 출력은 config 와 volume 을 동시에, 그다음 cache 와 db 를 동시에 띄울 수 있다고 알려 준다. 4단계가 이 의존 그래프의 최소 기동 단계 수다. 사이클을 넣자 `CycleError` 가 사이클 경로 자체(app → config → app)를 보여 줬다.

## 현업에서는

- **워크플로 엔진.** Airflow 같은 도구는 작업 흐름을 DAG 로 정의한다. 스케줄러는 선행 작업이 모두 끝난 작업만 실행 가능 상태로 올린다. 위의 `get_ready()`/`done()` 루프와 같은 구조다.
- **빌드와 패키지.** Make, Bazel 같은 빌드 도구와 apt, pip 같은 패키지 관리자는 의존 그래프를 위상 순서로 처리하고, 순환 의존이 있으면 오류를 낸다.
- **서비스 기동 순서.** systemd 는 유닛 사이의 `After=`, `Before=` 같은 순서 관계로 기동 순서를 정하고, 순환이 생기면 일부 유닛을 빼서 끊는다. 쿠버네티스는 반대로 파드 사이 기동 순서를 보장하지 않는다. 그래서 init container 나 readiness probe 로 "의존 대상이 준비될 때까지 기다리기" 를 각 파드가 스스로 해야 한다. 홈랩에서 DB 보다 앱이 먼저 떠 재시작을 반복하는 장면이 이 차이에서 나온다.
- **스프레드시트.** 셀 수식이 다른 셀을 참조하는 관계도 DAG 이고, 재계산은 위상 순서로 한다. 순환 참조 경고가 곧 사이클 탐지다.

## 확인 문제

1. 위상 정렬 결과가 유일한 조건은?
2. Kahn 알고리즘이 끝났을 때 결과 길이가 V 보다 작으면 무엇을 뜻하는가?
3. DFS 위상 정렬에서 회색 정점을 다시 만나는 것이 왜 사이클인가?
4. 작업마다 걸리는 시간이 다를 때, 일꾼이 무한하면 전체 완료 시간은 어떻게 구하는가?

### 풀이

1. 위상 순서에서 연속한 모든 두 정점 사이에 간선이 있을 때, 즉 DAG 에 모든 정점을 지나는 경로(해밀턴 경로)가 있을 때다. Kahn 에서는 매 단계 큐에 정점이 정확히 하나만 있을 때다.
2. 진입 차수가 0 이 되지 못한 정점들이 남았다는 뜻이고, 그 정점들 사이에 사이클이 있다.
3. 회색은 현재 재귀 스택 위에 있는, 즉 지금 탐색 중인 경로의 조상이다. 후손에서 조상으로 가는 간선이 있으면 조상 → … → 후손 → 조상의 사이클이 된다.
4. DAG 에서 작업 시간을 가중치로 한 가장 긴 경로(임계 경로)를 구한다. 위상 순서대로 "시작 가능 시각 = 선행 작업 완료 시각의 최댓값" 을 계산하면 Θ(V + E) 에 나온다.

## 더 읽을거리 (References)

- A. B. Kahn, "Topological Sorting of Large Networks", *Communications of the ACM* 5(11), 1962.
- Python 공식 문서, [graphlib — Functionality to operate with graph-like structures](https://docs.python.org/3/library/graphlib.html)
- Apache Airflow 공식 문서, [DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html)
- NIST Dictionary of Algorithms and Data Structures, [topological sort](https://xlinux.nist.gov/dads/HTML/topologicalSort.html)
