---
layout: post
title: "[CS300 #049] 레드블랙 트리 — 느슨한 균형으로 갱신을 싸게"
date: 2026-10-10 18:49:00 +0900
categories: [cs]
tags: [cs300, data-structures, red-black-tree, balanced-tree, 2-3-tree]
---

컴퓨터공학 300 주제 시리즈의 049번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

레드블랙 트리는 노드마다 빨강·검정 색 1비트를 달고 "빨강이 연달아 오지 않고, 루트에서 모든 잎까지 검은 노드 수가 같다"는 규칙을 지켜 높이를 2 log₂(n+1) 이하로 묶는 이진 탐색 트리로, AVL 보다 균형은 느슨하지만 갱신 때 회전이 적다.

## 왜 필요한가

AVL 트리는 높이를 아주 낮게 유지하지만, 그 대가로 삽입·삭제 때마다 균형을 엄격하게 따진다. 특히 삭제는 루트까지 회전이 이어질 수 있다. 갱신이 많은 범용 컨테이너나 운영체제 커널에서는 "조회가 조금 느려도 갱신이 싸고 예측 가능한" 쪽이 낫다.

레드블랙 트리가 그 답이다. 자바 `TreeMap` 문서 첫 줄은 "레드블랙 트리 기반의 `NavigableMap` 구현"이며 `containsKey`, `get`, `put`, `remove` 에 log(n) 시간을 보장한다고 적는다([Java SE 21 TreeMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html)). 리눅스 커널 문서는 삽입과 삭제에 각각 최대 두 번과 세 번의 회전만 필요하다는 점을 AVL 대비 장점으로 들고, 커널 곳곳에서 쓰이는 사례를 소개한다([Linux Kernel — Red-black Trees](https://docs.kernel.org/core-api/rbtree.html)). 실무에서 "균형 이진 트리"라고 하면 대개 이것이다.

## 핵심 개념

### 다섯 가지 규칙

CLRS 의 정의를 따르면 레드블랙 트리는 다음을 모두 만족하는 BST 다. 여기서 잎은 키가 없는 `NIL` 노드로 본다.

1. 모든 노드는 빨강 아니면 검정이다.
2. 루트는 검정이다.
3. 모든 잎(NIL)은 검정이다.
4. 빨강 노드의 자식은 모두 검정이다. (빨강이 연달아 오지 않는다)
5. 어떤 노드에서든 그 아래 모든 잎까지 가는 경로의 검은 노드 수가 같다. 이 수를 **검은 높이(black-height)** 라 한다.

### 높이 상한이 나오는 이유

규칙 5 때문에 루트에서 잎까지 모든 경로는 같은 수 b 의 검은 노드를 지난다. 규칙 4 때문에 빨강은 검정 사이에 하나씩만 끼어들 수 있다. 그러므로 가장 긴 경로도 가장 짧은 경로(검정만)의 2배를 넘지 못한다. 검은 높이가 b 인 트리에는 적어도 2^b − 1 개의 내부 노드가 있으므로 b ≤ log₂(n+1), 높이 h ≤ 2b ≤ 2 log₂(n+1) 이다. AVL 의 약 1.44 log₂ n 보다 느슨하지만 여전히 O(log n) 이다.

### 2-3-4 트리로 보면 쉬워진다

레드블랙 트리는 사실 **2-3-4 트리**(노드 하나에 키 1~3개)를 이진 트리로 표현한 것이다. 빨강 노드는 "부모와 같은 큰 노드에 묶여 있다"는 뜻이다.

```
2-3-4 트리의 3-노드 [10 | 20]      레드블랙 트리 표현

                                       20(B)
                                      /
                                   10(R)      ← 빨강 = 부모와 한 몸
```

이렇게 보면 규칙이 자연스럽다. 2-3-4 트리는 모든 잎이 같은 깊이에 있다. 빨강을 부모에 합치면 남는 것은 검정뿐이니 "검은 높이가 모두 같다"는 말이 곧 "2-3-4 트리의 잎이 모두 같은 깊이"라는 말이다. 이 관점은 Guibas 와 Sedgewick 의 1978년 논문에서 정리되었고, Sedgewick 은 2-3 트리에 대응시켜 규칙을 더 줄인 **좌편향 레드블랙 트리(LLRB)** 를 제안했다([Sedgewick, Left-leaning Red-Black Trees](https://www.cs.princeton.edu/~rs/talks/LLRB/LLRB.pdf)). 이 글의 실습은 LLRB 다.

### 삽입: 새 노드는 빨강

새 노드를 빨강으로 넣으면 규칙 5(검은 높이)는 절대 안 깨진다. 깨질 수 있는 것은 규칙 4(빨강 연속)뿐이다. 부모가 빨강이면 **삼촌**(부모의 형제) 색을 본다.

| 상황 | 처리 | 2-3-4 트리에서의 의미 |
|---|---|---|
| 삼촌이 빨강 | 부모·삼촌을 검정, 조부모를 빨강으로 바꾸고 조부모에서 다시 검사 | 꽉 찬 4-노드를 쪼개 가운데 키를 위로 올림 |
| 삼촌이 검정, 꺾인 모양 | 부모에서 회전해 일자 모양으로 만듦 | 노드 안 키 순서 정리 |
| 삼촌이 검정, 일자 모양 | 조부모에서 회전, 색 교환 | 3-노드를 4-노드로 키움 |

색 바꾸기는 위로 전파될 수 있지만 O(1) 이고, 회전은 삽입 한 번에 최대 2회다. 삭제는 경우가 더 많지만 회전은 최대 3회다. AVL 의 삭제가 O(log n) 회 회전할 수 있는 것과 대조된다.

### 좌편향 레드블랙 트리의 세 줄

LLRB 는 "빨강 링크는 왼쪽에만"이라는 규칙을 더해 경우를 확 줄인다. 재귀 삽입에서 내려갔다가 올라오며 세 줄만 검사한다.

```
if 오른쪽만 빨강:          왼쪽 회전      (빨강을 왼쪽으로 기울임)
if 왼쪽과 왼쪽-왼쪽이 빨강: 오른쪽 회전    (빨강 연속을 4-노드 모양으로)
if 양쪽 다 빨강:           색 뒤집기      (4-노드를 쪼개 위로 올림)
```

## 직접 해 보기

LLRB 삽입을 구현하고, 규칙 위반을 검사하는 함수로 10만 개 삽입 뒤 트리를 검증한다.

```python
import math, random
RED, BLACK = True, False

class Node:
    __slots__ = ("key", "left", "right", "color")
    def __init__(self, key):
        self.key, self.left, self.right, self.color = key, None, None, RED

def is_red(n): return n is not None and n.color == RED

def rot_left(h):
    x = h.right; h.right = x.left; x.left = h
    x.color, h.color = h.color, RED
    return x

def rot_right(h):
    x = h.left; h.left = x.right; x.right = h
    x.color, h.color = h.color, RED
    return x

def flip(h):                       # 4-노드 쪼개기
    h.color = not h.color
    h.left.color = not h.left.color
    h.right.color = not h.right.color

def _insert(h, key):
    if h is None:
        return Node(key)           # 새 노드는 항상 빨강
    if key < h.key:   h.left = _insert(h.left, key)
    elif key > h.key: h.right = _insert(h.right, key)
    if is_red(h.right) and not is_red(h.left):    h = rot_left(h)
    if is_red(h.left) and is_red(h.left.left):    h = rot_right(h)
    if is_red(h.left) and is_red(h.right):        flip(h)
    return h

def insert(root, key):
    root = _insert(root, key)
    root.color = BLACK             # 루트는 항상 검정
    return root

def check(n):
    """(검은 높이, 전체 높이) 반환. 규칙 위반이면 AssertionError"""
    if n is None:
        return 0, 0
    assert not (is_red(n) and (is_red(n.left) or is_red(n.right))), "빨강 연속"
    assert not is_red(n.right), "오른쪽 빨강 (LLRB 규칙)"
    bl, hl = check(n.left)
    br, hr = check(n.right)
    assert bl == br, "검은 높이 불일치"
    return bl + (0 if is_red(n) else 1), 1 + max(hl, hr)

for name, keys in [("정렬", list(range(100_000))),
                   ("무작위", random.Random(5).sample(range(10**6), 100_000))]:
    root = None
    for k in keys:
        root = insert(root, k)
    black, height = check(root)
    print(f"{name:4} 100,000개  검은 높이={black}  전체 높이={height}  "
          f"2*log2(n+1)={2*math.log2(len(keys)+1):.1f}")
```

```
정렬   100,000개  검은 높이=16  전체 높이=17  2*log2(n+1)=33.2
무작위  100,000개  검은 높이=14  전체 높이=23  2*log2(n+1)=33.2
```

두 경우 모두 검사를 통과했고, 높이는 상한 33.2 보다 한참 낮다. 앞 글의 AVL 실습(무작위 10만 개에서 높이 20)과 비교하면 레드블랙(23)이 조금 더 높다. "균형은 느슨하지만 O(log n)" 이라는 설명이 숫자로 보인다.

## 현업에서는

- **언어 표준 라이브러리.** 자바 `TreeMap`·`TreeSet` 이 레드블랙 트리다. 순서가 필요한 맵을 쓰면 이미 쓰고 있는 셈이다.
- **리눅스 커널.** 커널 rbtree 문서는 LWN 기사를 인용해 I/O 스케줄러의 요청 추적, 고해상도 타이머, ext3 디렉터리 항목, epoll 파일 디스크립터, 네트워크 HTB 스케줄러의 패킷 등을 레드블랙 트리 사용처로 든다. 다만 오래된 인용이라 지금은 바뀐 것도 있다. 예를 들어 가상 메모리 영역(VMA) 추적은 이후 B-트리 계열인 Maple Tree 로 옮겨 갔고, 커널 문서는 Maple Tree 의 가장 중요한 용도를 VMA 추적이라고 적는다([Linux Kernel — Maple Tree](https://docs.kernel.org/core-api/maple_tree.html)).
- **CPU 스케줄러.** 리눅스의 CFS 스케줄러 문서는 실행 대기 태스크를 가상 실행 시간 기준의 시간순 레드블랙 트리로 관리한다고 설명한다([Linux Kernel — CFS Scheduler](https://docs.kernel.org/scheduler/sched-design-CFS.html)). 가장 덜 실행된 태스크가 맨 왼쪽 노드가 된다. 커널은 6.6 부터 EEVDF 스케줄러로 옮겨 가기 시작했다고 문서에 적혀 있다([Linux Kernel — EEVDF Scheduler](https://docs.kernel.org/scheduler/sched-eevdf.html)).
- **직접 구현은 피한다.** 레드블랙 삭제는 경우가 많아 버그가 나기 쉽다. 필요하면 검증된 라이브러리를 쓰고, 꼭 짜야 한다면 위의 `check` 같은 불변식 검사를 무작위 테스트에 붙인다.

## 확인 문제

1. 새로 삽입하는 노드를 빨강으로 칠하는 이유는?
2. 검은 높이가 3 인 레드블랙 트리의 내부 노드 수의 최솟값은?
3. 레드블랙 트리의 빨강 노드는 2-3-4 트리에서 무엇을 뜻하는가?
4. 삽입 시 부모와 삼촌이 모두 빨강이면 어떻게 처리하며, 2-3-4 트리로는 무슨 일인가?
5. 같은 데이터에서 AVL 트리보다 레드블랙 트리가 더 높을 수 있는데도 범용 라이브러리가 레드블랙을 많이 택하는 이유는?

### 풀이

1. 검정으로 넣으면 그 경로의 검은 높이만 1 늘어 규칙 5 가 깨지는데, 이것은 고치기 어렵다. 빨강으로 넣으면 깨질 수 있는 것은 규칙 4 뿐이고 색 바꾸기와 회전으로 국소적으로 고칠 수 있다.
2. 2³ − 1 = 7개.
3. 부모와 같은 2-3-4 노드(3-노드나 4-노드)에 묶인 키다.
4. 부모·삼촌을 검정, 조부모를 빨강으로 바꾸고 조부모에서 다시 검사한다. 꽉 찬 4-노드를 쪼개 가운데 키를 부모 노드로 올리는 것에 해당한다.
5. 삽입·삭제의 회전 수가 상수(최대 2·3회)라 갱신 비용이 작고 예측 가능하며, 노드당 추가 정보도 1비트로 작기 때문이다.

## 더 읽을거리 (References)

- The Linux Kernel documentation, [Red-black Trees (rbtree) in Linux](https://docs.kernel.org/core-api/rbtree.html)
- Robert Sedgewick, [Left-leaning Red-Black Trees](https://www.cs.princeton.edu/~rs/talks/LLRB/LLRB.pdf)
- Robert Sedgewick, Kevin Wayne, [Algorithms, 4th ed. — 3.3 Balanced Search Trees](https://algs4.cs.princeton.edu/33balanced/)
- Leo J. Guibas, Robert Sedgewick, "A dichromatic framework for balanced trees", *19th Annual Symposium on Foundations of Computer Science (FOCS)*, 1978
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022 — Red-Black Trees 장
