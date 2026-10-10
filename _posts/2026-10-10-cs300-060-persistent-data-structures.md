---
layout: post
title: "[CS300 #060] 영속 자료구조 — 고치지 않고 새 버전을 만든다"
date: 2026-10-10 19:00:00 +0900
categories: [cs]
tags: [cs300, data-structures, persistent-data-structure, immutability, structural-sharing]
---

컴퓨터공학 300 주제 시리즈의 060번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

영속 자료구조(persistent data structure)는 갱신할 때 기존 것을 고치지 않고 새 버전을 돌려주며 옛 버전도 그대로 쓸 수 있게 남기는 구조로, 바뀐 경로만 복사하고 나머지는 옛 버전과 공유(구조 공유)해서 버전마다 통째로 복사하는 비용 없이 모든 이력을 들고 다닌다.

## 왜 필요한가

지금까지 이 파트에서 본 자료구조는 모두 **제자리에서** 바뀌었다. 배열에 쓰면 옛 값은 사라지고, 트리를 회전하면 옛 모양은 남지 않는다. 이것을 영속의 반대말로 **일시적(ephemeral)** 자료구조라고 부른다.

그런데 옛 버전이 필요한 경우가 생각보다 많다.

- **실행 취소·이력.** 편집기, 설계 도구, 게임의 되감기는 이전 상태를 들고 있어야 한다.
- **동시성.** 한 스레드가 읽는 도중 다른 스레드가 고치면 깨진 중간 상태를 볼 수 있다. 데이터가 절대 바뀌지 않는다면 락 없이 누구나 안전하게 읽는다.
- **스냅숏과 버전 관리.** 데이터베이스의 다중 버전 동시성 제어(MVCC), 깃의 커밋, 파일 시스템의 스냅숏은 "특정 시점의 전체 상태"를 싸게 보존해야 한다.
- **UI 상태 관리.** "바뀌었나?"를 내용 비교 대신 참조 비교(`===`) 한 번으로 판단할 수 있다.

매번 통째로 복사하면 버전마다 O(n) 이 든다. 영속 자료구조는 이것을 O(log n) 이나 O(1) 로 줄인다. 함수형 언어(클로저, 하스켈, 스칼라)에서는 기본 컬렉션이 이 방식이다.

## 핵심 개념

### 영속성의 단계

Driscoll, Sarnak, Sleator, Tarjan 의 1989년 논문 "Making Data Structures Persistent" 는 부분 영속과 완전 영속을 정의하고 이를 일반적으로 구현하는 기법을 제시했다([Driscoll et al., JCSS 1989](https://doi.org/10.1016/0022-0000%2889%2990034-2)). 두 버전을 합치는 합류 영속은 그 뒤의 연구에서 다뤄졌다.

| 단계 | 옛 버전 읽기 | 옛 버전 고치기 | 버전 구조 |
|---|---|---|---|
| 부분 영속 (partial) | 가능 | 최신 버전만 | 일직선 |
| 완전 영속 (full) | 가능 | 어느 버전이든 | 트리처럼 갈라짐 |
| 합류 영속 (confluent) | 가능 | 가능, 두 버전 합치기도 | DAG |

깃이 좋은 비유다. 어느 커밋이든 체크아웃해 볼 수 있고(읽기), 옛 커밋에서 브랜치를 따 고칠 수 있고(완전), 브랜치를 병합할 수 있다(합류).

### 가장 단순한 예: 불변 연결 리스트

단일 연결 리스트의 맨 앞에 붙이는 것은 기존 리스트를 전혀 건드리지 않는다.

```
xs = [2, 3]          xs:        2 → 3 → ∅
ys = cons(1, xs)     ys:   1 ─┘
zs = cons(9, xs)     zs:   9 ─┘   (2 → 3 은 셋이 공유)
```

`ys` 와 `zs` 는 서로 다른 리스트지만 꼬리를 공유한다. 누구도 고치지 않으니 공유해도 안전하다. 이것이 **구조 공유(structural sharing)** 의 핵심이다. 대신 맨 뒤에 붙이거나 중간을 고치려면 그 앞부분 전체를 복사해야 한다.

### 경로 복사(path copying)

트리에서 노드 하나를 바꾸려면 그 노드와, 루트에서 그 노드까지의 **경로 위 노드들만** 새로 만든다. 경로 밖의 서브트리는 옛 버전과 그대로 공유한다.

```
      v0                         v1 = insert(v0, 35)
      50                         50'
     /  \                       /   \
   30    70        →          30'    70   ← v0 의 70 서브트리를 그대로 가리킴
  /  \   / \                 /  \
 20  40 60  80             20    40'      ← 20 도 공유
                                 /
                               35 (새 노드)
```

균형 트리라면 경로 길이가 O(log n) 이므로, 갱신 한 번에 새 노드 O(log n) 개면 된다. 새 버전의 루트 `50'` 와 옛 버전의 루트 `50` 이 각각 완전한 트리를 이룬다.

### 더 효율적인 구조들

| 구조 | 아이디어 | 쓰는 곳 |
|---|---|---|
| 넓은 분기 트리 (32갈래) | 트리를 아주 얕게 해 경로 복사 비용을 줄임 | 클로저 벡터, 스칼라 벡터 |
| HAMT (해시 배열 매핑 트라이) | 해시값 비트를 5비트씩 끊어 32갈래 트라이로 | 클로저·스칼라의 해시 맵 |
| 핑거 트리 | 양 끝 접근을 분할 상환 O(1) 로 | 하스켈 `Data.Sequence` |
| 팻 노드 (fat node) | 노드 안에 필드 값의 버전 이력을 기록 | Driscoll 등의 부분 영속 기법 |

클로저 문서는 모든 컬렉션이 불변이고 영속적이며, 구조 공유를 이용해 "수정된" 버전을 효율적으로 만들고, 해시 맵은 log₃₂N 단계로 접근한다고 설명한다([Clojure — Data Structures](https://clojure.org/reference/data_structures)). 32갈래면 원소가 10억 개여도 깊이가 6 이다.

### 분할 상환 분석과의 충돌

영속성에는 함정이 하나 있다. 동적 배열처럼 "가끔 비싼 연산이 있지만 평균은 싸다"는 분할 상환 분석은, 같은 옛 버전에서 비싼 연산을 **반복해서** 실행할 수 있으면 깨진다. 비싼 순간 직전의 버전을 계속 꺼내 같은 연산을 하면 매번 비싸다. Okasaki 는 박사 논문에서 지연 평가(lazy evaluation)와 메모이제이션을 이용해 영속 환경에서도 분할 상환 상한을 지키는 기법을 정리했다([Okasaki, Purely Functional Data Structures, 1996](https://www.cs.cmu.edu/~rwh/students/okasaki.pdf)).

## 직접 해 보기

파이썬의 `NamedTuple` 로 바꿀 수 없는 노드를 만들고, 경로 복사로 영속 이진 탐색 트리를 구현한다.

```python
from typing import NamedTuple, Optional
import random

class Node(NamedTuple):                 # NamedTuple: 만든 뒤 바꿀 수 없다
    key: int
    left: Optional["Node"]
    right: Optional["Node"]

def insert(t, key):
    """경로 복사: 루트에서 삽입 위치까지의 노드만 새로 만들고 나머지는 공유."""
    if t is None:
        return Node(key, None, None)
    if key < t.key:
        return Node(t.key, insert(t.left, key), t.right)   # 오른쪽 서브트리는 그대로 공유
    if key > t.key:
        return Node(t.key, t.left, insert(t.right, key))
    return t

def keys(t):
    return keys(t.left) + [t.key] + keys(t.right) if t else []

def nodes(t, acc=None):
    acc = set() if acc is None else acc
    if t:
        acc.add(id(t)); nodes(t.left, acc); nodes(t.right, acc)
    return acc

v0 = None
for k in [50, 30, 70, 20, 40, 60, 80]:
    v0 = insert(v0, k)
v1 = insert(v0, 35)                     # 새 버전. v0 은 그대로 남는다
v2 = insert(v1, 65)

print("v0:", keys(v0))
print("v1:", keys(v1))
print("v2:", keys(v2))
n0, n1 = nodes(v0), nodes(v1)
print(f"v0 노드 {len(n0)}개, v1 노드 {len(n1)}개, 공유 {len(n0 & n1)}개, 새로 만든 것 {len(n1 - n0)}개")
print("v1 의 오른쪽 서브트리는 v0 것과 같은 객체인가?", v1.right is v0.right)

try:
    v0.key = 999
except AttributeError as e:
    print("변경 시도:", type(e).__name__)

# 1만 개짜리 트리에 1천 번 삽입하며 모든 버전을 보관할 때의 비용
rng = random.Random(0)
base = None
for k in rng.sample(range(10**6), 10_000):
    base = insert(base, k)
versions, t = [base], base
for k in rng.sample(range(10**6, 2 * 10**6), 1_000):
    t = insert(t, k); versions.append(t)
all_nodes = set()
for v in versions:
    all_nodes |= nodes(v)
print(f"버전 {len(versions):,}개 보관: 전체 노드 {len(all_nodes):,}개 "
      f"(통째 복사였다면 약 {sum(len(keys(v)) for v in versions):,}개)")
```

```
v0: [20, 30, 40, 50, 60, 70, 80]
v1: [20, 30, 35, 40, 50, 60, 70, 80]
v2: [20, 30, 35, 40, 50, 60, 65, 70, 80]
v0 노드 7개, v1 노드 8개, 공유 4개, 새로 만든 것 4개
v1 의 오른쪽 서브트리는 v0 것과 같은 객체인가? True
변경 시도: AttributeError
버전 1,001개 보관: 전체 노드 34,197개 (통째 복사였다면 약 10,510,500개)
```

35 를 넣은 v1 은 경로 위의 50, 30, 40 을 새로 만들고 새 노드 35 를 더해 4개만 만들었다. 20 과 오른쪽 서브트리(70, 60, 80)는 v0 의 객체를 그대로 가리킨다. v0, v1, v2 세 버전이 동시에 살아 있고 각자 올바른 내용을 보여 준다. 1만 개 트리의 1001개 버전을 모두 보관하는 데 노드 약 3만 4천 개면 충분했다. 버전마다 복사했다면 천만 개가 넘는다. 이 예제는 균형을 잡지 않는 BST 라 경로가 조금 길지만, 균형 트리를 쓰면 버전당 O(log n) 이 보장된다.

## 현업에서는

- **깃.** 깃의 커밋은 트리 객체를 가리키고, 트리 객체는 하위 트리와 블롭(파일 내용)을 해시로 가리킨다([Pro Git — Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)). 파일 하나를 고친 커밋은 그 파일의 블롭과 루트까지의 트리 객체만 새로 만들고 나머지는 이전 커밋과 공유한다. 이 글의 경로 복사와 같은 모양이다.
- **프런트엔드 상태 관리.** React 문서는 상태에 넣은 객체를 직접 고치지 말고 읽기 전용처럼 다루어 새 객체로 교체하라고 안내한다([React — Updating Objects in State](https://react.dev/learn/updating-objects-in-state)). 바뀐 부분만 새로 만들고 나머지는 이전 객체를 재사용하는 스프레드 문법이 곧 수동 경로 복사다. 그래서 참조 비교 한 번으로 바뀐 부분을 알아낼 수 있다.
- **데이터베이스와 저장소.** MVCC 를 쓰는 데이터베이스는 갱신 시 행의 새 버전을 만들어 진행 중인 트랜잭션이 옛 버전을 계속 보게 한다. 쓰기 시 복사(copy-on-write) B-트리를 쓰는 저장 엔진은 페이지를 제자리에서 고치지 않고 경로를 복사해 새 루트를 만든다. 스냅숏이 거의 공짜가 되는 이유다.
- **쿠버네티스 선언형 모델.** 쿠버네티스 객체는 `resourceVersion` 이 붙은 버전의 연속으로 다뤄지고, 컨트롤러는 "현재 상태를 고친다"기보다 "새 원하는 상태를 제출한다". 자료구조 수준의 영속성과는 다르지만, 버전을 값으로 다루는 같은 사고방식이다.
- **비용.** 불변 구조는 할당이 많고 포인터를 더 따라가서, 단일 스레드에서 제자리 갱신하는 코드보다 느릴 수 있다. 성능이 중요한 곳에서는 내부적으로만 잠깐 가변으로 고친 뒤 불변으로 굳히는 기법(클로저의 transient 등)을 쓴다.

## 확인 문제

1. 부분 영속과 완전 영속의 차이는?
2. 노드 n 개인 균형 이진 탐색 트리에 경로 복사로 삽입하면 새로 만드는 노드 수는 대략 몇 개인가?
3. 불변 단일 연결 리스트에서 맨 앞에 붙이기는 O(1) 인데 맨 뒤에 붙이기는 왜 O(n) 인가?
4. 영속 자료구조가 락 없이 여러 스레드에서 읽기에 안전한 이유는?
5. 동적 배열의 분할 상환 O(1) 이 영속 환경에서 깨질 수 있는 이유는?

### 풀이

1. 부분 영속은 옛 버전을 읽기만 할 수 있고 최신 버전만 고칠 수 있다. 완전 영속은 어느 버전이든 고쳐 새 가지를 만들 수 있다.
2. 루트에서 삽입 위치까지 경로의 노드 수, 즉 O(log n) 개(새 잎 포함).
3. 맨 뒤에 붙이면 마지막 노드의 `next` 를 바꿔야 하는데 고칠 수 없으니 그 노드를 복사해야 하고, 그 노드를 가리키는 앞 노드도 복사해야 해서 결국 리스트 전체를 복사한다.
4. 한 번 만들어진 노드는 절대 바뀌지 않으므로 읽는 도중 내용이 변하는 일이 없다.
5. 용량이 꽉 찬 직전 버전을 보관해 두었다가 거기서 추가를 반복하면, 매번 O(n) 복사가 일어난다. 비싼 연산을 "한 번만" 치른다는 전제가 무너진다.

## 더 읽을거리 (References)

- James R. Driscoll, Neil Sarnak, Daniel D. Sleator, Robert E. Tarjan, ["Making Data Structures Persistent"](https://doi.org/10.1016/0022-0000%2889%2990034-2), *Journal of Computer and System Sciences* 38(1), 1989
- Chris Okasaki, [*Purely Functional Data Structures*](https://www.cs.cmu.edu/~rwh/students/okasaki.pdf), PhD thesis, Carnegie Mellon University, 1996
- Clojure, [Data Structures](https://clojure.org/reference/data_structures)
- Scott Chacon, Ben Straub, [*Pro Git* — 10.2 Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
