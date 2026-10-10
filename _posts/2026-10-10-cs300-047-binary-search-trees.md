---
layout: post
title: "[CS300 #047] 이진 탐색 트리 — 정렬을 유지하며 넣고 빼기"
date: 2026-10-10 18:47:00 +0900
categories: [cs]
tags: [cs300, data-structures, binary-search-tree, tree, ordered-map]
---

컴퓨터공학 300 주제 시리즈의 047번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

이진 탐색 트리(BST)는 "왼쪽 서브트리는 모두 작고, 오른쪽은 모두 크다"는 규칙을 지키는 이진 트리로, 탐색·삽입·삭제가 트리 높이 h 에 비례하는 O(h) 이고, 중위 순회하면 키가 정렬된 순서로 나온다.

## 왜 필요한가

해시 테이블은 "정확히 이 키"를 찾는 데는 최고지만 순서를 모른다. "30 이상 50 미만인 키 전부", "42 바로 다음으로 큰 키", "가장 작은 키" 같은 질문에는 전체를 훑어야 답할 수 있다. 정렬된 배열은 이런 질문에 이진 탐색으로 O(log n) 에 답하지만, 삽입과 삭제가 O(n) 이다.

이진 탐색 트리는 이 둘의 장점을 합치려는 시도다. 정렬 순서를 유지하면서, 삽입과 삭제도 트리가 균형만 잡혀 있으면 O(log n) 에 한다. 자바 `TreeMap`, C++ `std::map`, 데이터베이스 인덱스가 모두 이 아이디어의 후손이다. 다음 세 편(AVL, 레드블랙, B-트리)은 전부 "BST 의 높이를 어떻게 낮게 유지하나"에 대한 답이다. 그러니 그 출발점인 기본 BST 와 그 약점을 먼저 정확히 알아야 한다.

## 핵심 개념

### BST 성질

모든 노드 x 에 대해, x 의 왼쪽 서브트리의 키는 모두 x.key 보다 작고, 오른쪽 서브트리의 키는 모두 x.key 보다 크다. 바로 아래 자식만이 아니라 **서브트리 전체**에 대한 조건이라는 점이 중요하다.

```
            50
          /    \
        30      70
       /  \    /  \
     20   40  60   80
         /
       35
```

### 탐색

루트에서 시작해 찾는 키가 작으면 왼쪽, 크면 오른쪽으로 내려간다. 한 단계마다 한쪽 서브트리를 통째로 버린다. 이진 탐색과 같은 원리다. 비용은 내려간 깊이, 즉 최대 높이 h 다.

### 삽입

탐색하듯 내려가다 `None` 을 만난 자리에 새 노드를 붙인다. 새 노드는 항상 잎(leaf)이 된다. O(h).

### 삭제: 세 가지 경우

| 경우 | 처리 |
|---|---|
| 자식이 없음 | 그냥 떼어 낸다 |
| 자식이 하나 | 그 자식을 자기 자리로 올린다 |
| 자식이 둘 | 오른쪽 서브트리의 최솟값(**중위 후계자**)을 가져와 자기 키를 바꾸고, 후계자를 대신 삭제한다 |

세 번째 경우가 핵심이다. 후계자는 "나보다 큰 것 중 가장 작은 것"이라 그 자리에 놓아도 BST 성질이 깨지지 않는다. 그리고 후계자는 오른쪽 서브트리의 가장 왼쪽 노드라 왼쪽 자식이 없으므로, 그것을 지우는 일은 앞의 쉬운 두 경우 중 하나로 끝난다. 위 그림에서 30 을 지우면 후계자 35 가 그 자리에 오른다.

### 순서 연산

BST 는 해시 테이블이 못 하는 질문에 O(h) 로 답한다.

| 연산 | 방법 |
|---|---|
| 최솟값·최댓값 | 왼쪽(오른쪽) 끝까지 내려간다 |
| 후계자·선행자 | 오른쪽 서브트리 최솟값, 또는 조상으로 거슬러 오른다 |
| floor / ceiling (x 이하 최대, x 이상 최소) | 탐색 경로에서 후보를 갱신 |
| 범위 질의 [lo, hi] | 범위 밖 서브트리는 건너뛰며 중위 순회. O(h + k), k 는 결과 수 |
| 정렬 출력 | 중위 순회(왼쪽 → 자신 → 오른쪽). O(n) |

자바 `TreeMap` 의 `floorKey`, `ceilingKey`, `subMap`, `headMap` 이 바로 이 연산들이다([Java SE 21 TreeMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html)).

### 약점: 높이가 모든 것을 정한다

모든 연산이 O(h) 다. 균형이 잘 잡히면 h ≈ log₂ n 이지만, 키가 이미 정렬된 순서로 들어오면 매번 오른쪽에만 붙어 트리가 한 줄로 늘어선다.

```
1, 2, 3, 4, 5 순서로 삽입

1
 \
  2
   \
    3
     \
      4
       \
        5      ← 사실상 연결 리스트, h = n
```

이 경우 탐색이 O(n) 이 된다. 정렬된 입력은 현실에서 아주 흔하다. 시간순 로그, 자동 증가 ID, 이미 정렬된 파일이 다 그렇다. 무작위 순서로 넣으면 기대 높이가 O(log n) 이라는 것이 알려져 있지만(CLRS 의 "무작위로 만든 BST" 분석), 입력 순서를 우리가 고를 수는 없다. 그래서 실무에서 쓰는 순서 맵은 예외 없이 **자가 균형(self-balancing)** 트리다. 회전으로 높이를 O(log n) 으로 묶어 두는 AVL 트리와 레드블랙 트리가 다음 두 편의 주제다.

### 이진 트리 용어 정리

- **깊이(depth)**: 루트에서 그 노드까지 간선 수
- **높이(height)**: 그 노드에서 가장 깊은 잎까지 간선 수 (책에 따라 노드 수로 세기도 한다. 이 글의 코드는 노드 수로 센다)
- **완전 이진 트리**: 마지막 층만 빼고 꽉 차 있고, 마지막 층은 왼쪽부터 채운 트리. 힙 편에서 다시 나온다
- 노드 n 개인 이진 트리의 높이(노드 수 기준)는 최소 ⌈log₂(n+1)⌉, 최대 n 이다

## 직접 해 보기

삽입·탐색·삭제를 구현하고, 정렬된 입력과 무작위 입력의 높이를 비교한다.

```python
import random, sys
sys.setrecursionlimit(10000)

class Node:
    __slots__ = ("key", "left", "right")
    def __init__(self, key):
        self.key, self.left, self.right = key, None, None

def insert(root, key):
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = insert(root.left, key)
    elif key > root.key:
        root.right = insert(root.right, key)
    return root                       # 같은 키는 무시

def search(root, key):
    while root and root.key != key:
        root = root.left if key < root.key else root.right
    return root

def delete(root, key):
    if root is None:
        return None
    if key < root.key:
        root.left = delete(root.left, key)
    elif key > root.key:
        root.right = delete(root.right, key)
    else:
        if root.left is None:  return root.right    # 자식 0~1개
        if root.right is None: return root.left
        succ = root.right                           # 자식 2개: 후계자
        while succ.left:
            succ = succ.left
        root.key = succ.key
        root.right = delete(root.right, succ.key)
    return root

def inorder(root):
    return inorder(root.left) + [root.key] + inorder(root.right) if root else []

def height(root):
    return 1 + max(height(root.left), height(root.right)) if root else 0

root = None
for k in [50, 30, 70, 20, 40, 60, 80, 35]:
    root = insert(root, k)
print("중위 순회:", inorder(root))
root = delete(root, 30)               # 자식이 둘인 노드 삭제
print("30 삭제 후:", inorder(root), " 루트의 왼쪽 =", root.left.key)
print("40 있나?", search(root, 40) is not None, " 45 있나?", search(root, 45) is not None)

N = 2000
keys = list(range(N))
r_sorted = None
for k in keys:
    r_sorted = insert(r_sorted, k)
random.seed(7); random.shuffle(keys)
r_rand = None
for k in keys:
    r_rand = insert(r_rand, k)
print(f"N={N}  정렬된 순서로 삽입 높이={height(r_sorted)}  무작위 순서 높이={height(r_rand)}")
```

```
중위 순회: [20, 30, 35, 40, 50, 60, 70, 80]
30 삭제 후: [20, 35, 40, 50, 60, 70, 80]  루트의 왼쪽 = 35
40 있나? True  45 있나? False
N=2000  정렬된 순서로 삽입 높이=2000  무작위 순서 높이=28
```

같은 2000개 키인데 넣는 순서만으로 높이가 2000 과 28 로 갈린다. log₂ 2000 은 약 11 이니 무작위도 이상적인 균형과는 거리가 있지만, 정렬 입력의 2000 과는 비교가 안 된다. 정렬 입력 쪽은 재귀 깊이도 2000 이라 `setrecursionlimit` 을 올려야 돌아갔다. 기본 BST 를 실무에 쓰면 안 되는 이유가 이 한 줄에 다 들어 있다.

## 현업에서는

- **순서 맵이 필요할 때.** 시간 구간 질의, 리더보드, 다음 예약 찾기처럼 "범위"나 "다음 것"이 필요하면 해시 맵이 아니라 `TreeMap`, `std::map`, 러스트 `BTreeMap` 을 고른다. 파이썬 표준 라이브러리에는 균형 BST 가 없어서, 정렬 리스트와 `bisect` 모듈로 대신하는 경우가 많다([Python bisect](https://docs.python.org/3/library/bisect.html)). 삽입이 O(n) 이지만 n 이 크지 않으면 메모리 이동이 빨라 충분히 실용적이다.
- **자동 증가 키의 함정.** 균형을 잡지 않는 트리 구조에 시간순 ID 를 넣으면 위 실습의 한 줄 트리가 그대로 재현된다. 직접 만든 트리 구조가 이상하게 느려졌다면 입력 순서부터 의심한다.
- **디버깅 도구로서의 중위 순회.** 트리를 직접 다루는 코드를 고쳤다면, 무작위 연산 뒤 중위 순회 결과가 정렬되어 있는지 확인하는 검사 하나로 대부분의 버그가 잡힌다.

## 확인 문제

1. 아래 트리는 BST 인가? 루트 10, 왼쪽 자식 5, 5 의 오른쪽 자식 12, 루트의 오른쪽 자식 15.
2. 위 실습 트리(50, 30, 70, 20, 40, 60, 80, 35)에서 50 을 삭제하면 루트에 어떤 키가 오는가?
3. 1부터 7까지를 넣어 높이(노드 수 기준) 3 인 완전 균형 BST 를 만들려면 어떤 순서로 넣으면 되는가? 한 가지만 쓰라.
4. 범위 질의 [lo, hi] 의 비용이 O(h + k) 인 이유는?
5. 해시 테이블 대신 BST 계열을 고를 이유 두 가지는?

### 풀이

1. 아니다. 12 는 루트 10 의 왼쪽 서브트리에 있는데 10 보다 크다. 직속 부모 5 와의 관계만 맞다.
2. 오른쪽 서브트리 최솟값인 60.
3. 4, 2, 6, 1, 3, 5, 7 (각 구간의 가운데를 먼저 넣는다).
4. 경계를 찾아 내려가는 데 O(h), 범위 안 노드 k 개를 방문하는 데 O(k) 가 든다. 범위 밖 서브트리는 통째로 건너뛴다.
5. 정렬 순서 순회, 범위 질의, floor/ceiling 같은 순서 연산이 필요할 때. 그리고 최악 시간 보장(균형 트리라면 O(log n))이 필요할 때.

## 더 읽을거리 (References)

- Robert Sedgewick, Kevin Wayne, [Algorithms, 4th ed. — 3.2 Binary Search Trees](https://algs4.cs.princeton.edu/32bst/)
- NIST Dictionary of Algorithms and Data Structures, [binary search tree](https://xlinux.nist.gov/dads/HTML/binarySearchTree.html)
- Oracle, [Java SE 21 API — TreeMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html)
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022 — Binary Search Trees 장
