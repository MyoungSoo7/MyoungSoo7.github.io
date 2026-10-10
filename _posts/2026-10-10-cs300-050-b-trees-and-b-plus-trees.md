---
layout: post
title: "[CS300 #050] B-트리와 B+트리 — 디스크 페이지에 맞춘 넓고 낮은 트리"
date: 2026-10-10 18:50:00 +0900
categories: [cs]
tags: [cs300, data-structures, b-tree, b-plus-tree, database-index]
---

컴퓨터공학 300 주제 시리즈의 050번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

B-트리는 노드 하나에 키를 수십~수백 개 담아 트리를 넓고 낮게 만든 균형 탐색 트리이고, B+트리는 실제 데이터를 잎에만 두고 잎끼리 연결해 범위 검색을 빠르게 한 변형으로, 거의 모든 관계형 데이터베이스 인덱스와 파일 시스템의 기본 구조다.

## 왜 필요한가

AVL 이나 레드블랙 트리는 메모리 안에서는 훌륭하다. 그런데 데이터가 디스크에 있으면 계산이 달라진다. 디스크(SSD 포함)는 바이트 하나를 읽든 수 KB 를 읽든 한 번 읽는 비용이 비슷하고, 그 한 번이 메모리 접근보다 훨씬 비싸다. 이진 트리로 백만 건을 찾으면 높이 약 20, 즉 디스크를 20번 읽는다. 노드마다 키 하나를 읽으려고 페이지 하나를 통째로 가져오는 셈이다.

B-트리는 "어차피 페이지 단위로 읽을 거라면 페이지 하나에 키를 가득 채우자"는 생각이다. 노드 하나에 키가 수백 개면 분기 수도 수백이 되고, 백만 건이라도 높이 3 정도에서 끝난다. Bayer 와 McCreight 가 1972년 대용량 순서 인덱스를 위해 발표했고([Bayer & McCreight, Acta Informatica, 1972](https://doi.org/10.1007/BF00288683)), 지금도 PostgreSQL 과 SQLite 를 비롯한 관계형 데이터베이스의 기본 인덱스가 이 계열이다. 메모리 안에서도 캐시 라인과 할당 비용 때문에 이점이 있어서 러스트 표준 라이브러리는 순서 맵을 레드블랙이 아니라 B-트리(`BTreeMap`)로 구현했다.

## 핵심 개념

### B-트리의 정의 (최소 차수 t)

CLRS 의 정의를 따르면 최소 차수 t ≥ 2 인 B-트리는 다음을 만족한다.

1. 루트가 아닌 모든 노드는 키를 t−1 개 이상 2t−1 개 이하 가진다. 루트는 1개 이상.
2. 키가 k 개인 내부 노드는 자식이 정확히 k+1 개다.
3. 노드 안의 키는 정렬되어 있고, 자식 i 의 키들은 키 i−1 과 키 i 사이에 있다.
4. **모든 잎이 같은 깊이에 있다.**

```
                    [ 30 | 60 ]
                  /      |      \
       [10|20]      [40|50]      [70|80|90]
       /  |  \      /  |  \      /  |  |  \
      …   …   …    …   …   …    …   …  …   …
```

4번이 균형을 보장한다. 레드블랙 트리 편에서 본 2-3-4 트리는 t = 2 인 B-트리다.

### 높이

모든 노드가 최소 t 개 자식을 가지므로, 키가 n 개인 B-트리의 높이 h 는 대략 log_t n 이하다. t 가 크면 밑이 커져 높이가 급격히 줄어든다.

| 분기 수(대략) | 백만 건 높이 | 10억 건 높이 |
|---|---|---|
| 2 (이진 트리) | 약 20 | 약 30 |
| 100 | 3 | 5 |
| 500 | 3 | 4 |

내부 노드는 자주 읽혀 대부분 메모리 버퍼에 상주하므로, 실제 디스크 읽기는 잎 하나 정도로 끝나는 경우가 많다.

### 삽입: 쪼개고 위로 올린다

1. 탐색하듯 내려가 키가 들어갈 잎을 찾는다.
2. 잎에 자리가 있으면 정렬 위치에 끼운다.
3. 잎이 꽉 차 있으면(2t−1 개) **쪼갠다**. 가운데 키는 부모로 올라가고, 양쪽 절반은 각자 노드가 된다.
4. 부모도 꽉 차 있으면 연쇄적으로 쪼갠다. 루트가 쪼개지면 새 루트가 생기며 높이가 1 늘어난다.

B-트리는 **위로 자란다.** 잎이 아래로 늘어나는 게 아니라 루트가 위로 생긴다. 그래서 모든 잎의 깊이가 항상 같다. CLRS 방식은 내려가는 길에 꽉 찬 노드를 미리 쪼개 두어, 다시 올라올 필요 없이 한 번에 끝낸다. 아래 실습 코드가 그 방식이다.

삭제는 반대로 키가 t−1 개 미만이 되는 노드를 형제에게서 **빌리거나**(재분배) 형제와 **합쳐서** 처리한다.

### B+트리: 데이터는 잎에만

실제 데이터베이스는 대부분 B+트리를 쓴다. 차이는 두 가지다.

| 항목 | B-트리 | B+트리 |
|---|---|---|
| 값(행 또는 행 포인터) 위치 | 모든 노드 | **잎에만** |
| 내부 노드 | 키 + 값 + 자식 포인터 | 키(구분자) + 자식 포인터만 |
| 잎 연결 | 없음 | 잎끼리 연결 리스트 |
| 범위 검색 | 트리를 오르내리며 중위 순회 | 시작 잎을 찾고 옆으로 훑기 |
| 분기 수 | 값 때문에 작아짐 | 내부 노드가 가벼워 더 큼 |

```
B+트리
                 [ 30 | 60 ]                 ← 내부: 길잡이 키만
               /      |      \
  [10 20 25] ⇄ [30 40 50] ⇄ [60 70 80]       ← 잎: 모든 키와 값, 옆으로 연결
```

`WHERE created_at BETWEEN …` 같은 범위 질의는 시작점 잎 하나를 찾은 뒤 연결을 따라 옆으로 읽기만 하면 된다. 내부 노드가 가벼우니 같은 페이지에 더 많은 키가 들어가 트리도 더 낮다.

SQLite 파일 형식 문서는 두 가지 B-트리를 쓴다고 적는다. 테이블 B-트리는 64비트 정수 키를 쓰고 **모든 데이터를 잎에 저장**하며 내부 노드는 키와 자식 포인터만 가진다. 인덱스 B-트리는 임의의 키를 쓰고 데이터를 담지 않는다([SQLite Database File Format](https://www.sqlite.org/fileformat2.html)). 앞의 것이 바로 B+트리 모양이다. PostgreSQL 문서는 B-트리 인덱스가 다단계 트리이고 **각 층을 페이지들의 이중 연결 리스트로 쓸 수 있으며**, 보통 전체 페이지의 99% 이상이 잎 페이지라고 설명한다([PostgreSQL — B-Tree Indexes](https://www.postgresql.org/docs/current/btree.html)).

## 직접 해 보기

CLRS 방식의 B-트리 삽입을 구현하고, 최소 차수 t 에 따라 높이와 탐색 시 읽는 노드 수가 어떻게 바뀌는지 본다. 노드 하나를 읽는 것을 디스크 페이지 한 번 읽기로 생각하면 된다.

```python
import bisect, random, math

class BNode:
    __slots__ = ("keys", "kids")
    def __init__(self, leaf=True):
        self.keys = []
        self.kids = None if leaf else []

class BTree:
    """CLRS 방식: 최소 차수 t, 노드당 키 t-1 ~ 2t-1 개. 내려가며 미리 쪼갠다."""
    def __init__(self, t):
        self.t, self.root = t, BNode()

    def search(self, key):
        node, visited = self.root, 0
        while True:
            visited += 1                                  # 노드 1개 = 디스크 페이지 1번 읽기
            i = bisect.bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                return True, visited
            if node.kids is None:
                return False, visited
            node = node.kids[i]

    def _split(self, parent, i):
        t, full = self.t, parent.kids[i]
        right = BNode(leaf=full.kids is None)
        mid = full.keys[t - 1]
        right.keys, full.keys = full.keys[t:], full.keys[:t - 1]
        if full.kids is not None:
            right.kids, full.kids = full.kids[t:], full.kids[:t]
        parent.keys.insert(i, mid)                        # 가운데 키가 위로 올라간다
        parent.kids.insert(i + 1, right)

    def insert(self, key):
        if len(self.root.keys) == 2 * self.t - 1:         # 루트가 꽉 차면 높이 +1
            old, self.root = self.root, BNode(leaf=False)
            self.root.kids.append(old)
            self._split(self.root, 0)
        node = self.root
        while node.kids is not None:
            i = bisect.bisect_left(node.keys, key)
            if len(node.kids[i].keys) == 2 * self.t - 1:
                self._split(node, i)
                if key > node.keys[i]:
                    i += 1
            node = node.kids[i]
        bisect.insort(node.keys, key)

    def height(self):
        h, n = 1, self.root
        while n.kids is not None:
            h, n = h + 1, n.kids[0]
        return h

N = 1_000_000
keys = random.Random(42).sample(range(10**9), N)
for t in (2, 16, 128):
    bt = BTree(t)
    for k in keys:
        bt.insert(k)
    found, visited = bt.search(keys[12345])
    print(f"t={t:>3} (노드당 최대 {2*t-1:>3}키)  높이={bt.height()}  "
          f"탐색 시 읽은 노드={visited}  found={found}")
print(f"참고: 완전 균형 이진 트리 높이 ≈ log2(N) = {math.log2(N):.1f}")
```

```
t=  2 (노드당 최대   3키)  높이=16  탐색 시 읽은 노드=14  found=True
t= 16 (노드당 최대  31키)  높이=5  탐색 시 읽은 노드=5  found=True
t=128 (노드당 최대 255키)  높이=3  탐색 시 읽은 노드=3  found=True
참고: 완전 균형 이진 트리 높이 ≈ log2(N) = 19.9
```

백만 건을 넣는 데 파이썬으로 수십 초가 걸린다. 같은 백만 건인데 노드당 255키면 높이 3 이다. 디스크로 치면 페이지 세 번이다. t = 2(2-3-4 트리)는 높이 16 으로 이진 트리 수준이다. 노드 안에서는 `bisect` 로 이진 탐색을 하므로 비교 횟수 자체는 크게 다르지 않다. 줄어드는 것은 **노드를 옮겨 다니는 횟수**, 즉 페이지 읽기와 캐시 미스다.

## 현업에서는

- **기본 인덱스.** PostgreSQL 에서 `CREATE INDEX` 를 옵션 없이 쓰면 B-트리 인덱스가 만들어진다([PostgreSQL — Index Types](https://www.postgresql.org/docs/current/indexes-types.html)). `=`, `<`, `BETWEEN`, `ORDER BY` 를 모두 처리할 수 있는 이유가 B+트리의 정렬 순서와 잎 연결이다.
- **복합 인덱스 순서.** `(a, b)` 인덱스는 (a, b) 사전순으로 정렬된 B+트리다. 그래서 `WHERE a = ?` 나 `WHERE a = ? AND b > ?` 는 빠르지만 `WHERE b = ?` 만으로는 인덱스 범위를 좁히지 못한다. 전화번호부가 성으로 먼저 정렬되어 이름만으로는 못 찾는 것과 같다.
- **무작위 키와 페이지 분할.** UUIDv4 처럼 무작위인 기본 키는 삽입이 잎 전체에 흩어져 페이지 분할과 캐시 미스가 늘어난다. 시간순으로 증가하는 키는 항상 오른쪽 끝 잎에 붙어 분할이 한쪽에서만 일어난다. 키 설계가 인덱스 크기와 쓰기 성능에 직접 영향을 주는 이유다.
- **메모리 안의 B-트리.** 러스트 `BTreeMap` 문서는 BST 가 원소마다 힙 할당을 하고 비교마다 캐시 미스 가능성이 있다는 점을 들어, 노드마다 원소 배열을 담는 B-트리가 캐시 효율과 탐색 작업량 사이의 근본적 절충이라고 설명한다([Rust BTreeMap](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html)).

## 확인 문제

1. 최소 차수 t = 3 인 B-트리에서 루트가 아닌 노드가 가질 수 있는 키 수의 범위는?
2. B-트리의 모든 잎이 같은 깊이에 있게 되는 이유를 삽입 동작으로 설명하라.
3. B+트리가 B-트리보다 범위 검색에 유리한 이유 두 가지는?
4. 분기 수가 약 200 인 B+트리에서 키 800만 개를 담으면 높이는 대략 얼마인가?
5. `(country, city)` 복합 인덱스로 `WHERE city = 'Seoul'` 만 걸면 인덱스 범위 탐색이 잘 안 되는 이유는?

### 풀이

1. t−1 = 2 개 이상, 2t−1 = 5 개 이하.
2. 새 키는 항상 잎에 들어가고, 넘치면 쪼개진 가운데 키가 위로 올라간다. 높이는 루트가 쪼개질 때만, 모든 경로에 똑같이 1 씩 늘어난다.
3. 모든 데이터가 잎에 있고 잎끼리 연결되어 있어 시작 잎만 찾으면 옆으로 훑으면 된다. 내부 노드에 값이 없어 분기 수가 커지고 트리가 더 낮다.
4. 200² = 4만, 200³ = 800만이므로 약 3.
5. 인덱스가 country 를 먼저 기준으로 정렬되어 있어서, city 만으로는 정렬 순서상 연속 구간이 생기지 않는다.

## 더 읽을거리 (References)

- R. Bayer, E. McCreight, ["Organization and maintenance of large ordered indexes"](https://doi.org/10.1007/BF00288683), *Acta Informatica* 1(3), 1972
- PostgreSQL Documentation, [B-Tree Indexes](https://www.postgresql.org/docs/current/btree.html)
- SQLite, [Database File Format](https://www.sqlite.org/fileformat2.html)
- The Rust Standard Library, [BTreeMap](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html)
- Douglas Comer, "The Ubiquitous B-Tree", *ACM Computing Surveys* 11(2), 1979
