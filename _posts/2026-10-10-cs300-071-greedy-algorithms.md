---
layout: post
title: "[CS300 #071] 탐욕 알고리즘 — 지금 가장 좋아 보이는 선택이 정답일 때"
date: 2026-10-10 19:11:00 +0900
categories: [cs]
tags: [cs300, algorithms, greedy, huffman-coding, interval-scheduling]
---

컴퓨터공학 300 주제 시리즈의 071번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

탐욕 알고리즘은 매 단계에서 지금 가장 좋아 보이는 선택을 하고 되돌아보지 않는다. 빠르고 단순하지만 항상 옳지는 않다. 옳다는 것을 "교환 논증" 으로 증명할 수 있을 때만 쓴다.

## 왜 필요한가

탐욕은 사람이 가장 먼저 떠올리는 전략이다. 거스름돈을 줄 때 큰 동전부터 쓰고, 일정이 겹치면 빨리 끝나는 일부터 잡는다. 이런 직관이 맞는 문제에서는 탐욕이 가장 빠르고 코드도 짧다. 크루스칼·프림 최소 신장 트리, 다익스트라 최단 경로, 허프만 부호가 모두 탐욕이다.

문제는 직관이 틀리는 경우도 많다는 점이다. 동전 단위가 조금만 바뀌어도 "큰 것부터" 는 최적이 아니다. 그래서 탐욕을 쓸 때는 "왜 이 선택이 안전한가" 를 설명할 수 있어야 한다.

## 핵심 개념

### 탐욕이 통하는 두 조건

1. **탐욕 선택 속성(greedy-choice property)**: 지금의 탐욕 선택을 포함하는 최적해가 반드시 존재한다.
2. **최적 부분 구조(optimal substructure)**: 그 선택을 하고 남은 문제의 최적해를 합치면 전체 최적해가 된다.

2번은 동적 계획법과 공유하는 성질이다. 차이는 1번에 있다. 동적 계획법은 여러 선택지를 다 따져 보고, 탐욕은 하나만 고른다.

### 교환 논증(exchange argument)

탐욕 선택 속성을 증명하는 표준 기법이다. "어떤 최적해가 탐욕 선택을 안 했다면, 그 일부를 탐욕 선택으로 바꿔도 손해가 없다" 를 보인다.

**활동 선택 문제**로 해 보자. 회의 시간들이 주어지고, 겹치지 않게 최대한 많이 잡고 싶다. 탐욕 규칙: "끝나는 시각이 가장 이른 회의부터 고른다."

증명: 끝이 가장 이른 회의를 g 라 하자. 임의의 최적해 OPT 에서 가장 먼저 끝나는 회의를 o 라 하자. g 는 o 보다 늦게 끝나지 않는다. OPT 에서 o 를 g 로 바꾸면, g 가 o 보다 빨리(또는 같이) 끝나므로 나머지 회의와 겹치지 않는다. 개수는 그대로다. 그러므로 g 를 포함하는 최적해가 있다. 남은 문제는 "g 가 끝난 뒤 시작하는 회의들" 이고, 같은 논리를 반복하면 된다.

반대로 "가장 짧은 회의부터", "가장 먼저 시작하는 회의부터" 는 반례가 있다. 규칙 선택이 중요하다.

### 탐욕이 틀리는 예

동전 단위가 {4, 3, 1} 이고 6원을 거슬러 준다.

- 탐욕: 4 + 1 + 1 → 3개
- 최적: 3 + 3 → 2개

처음 4를 고른 순간 최적해에서 벗어났고, 되돌아가지 않으니 회복할 수 없다. 이런 문제는 동적 계획법으로 푼다. 한국 원화나 미국 달러처럼 실제 화폐 단위들은 탐욕이 최적이 되도록 설계되어 있다(이런 단위 체계를 canonical 하다고 한다).

**0/1 배낭 문제**도 탐욕이 틀린다. 무게당 가치가 높은 물건부터 넣으면 자투리 공간이 낭비될 수 있다. 다만 물건을 쪼갤 수 있는 **분할 배낭 문제**에서는 무게당 가치 순 탐욕이 최적이다.

### 허프만 부호

문자별 빈도가 주어질 때 평균 비트 수가 최소인 접두 부호(어떤 부호도 다른 부호의 접두사가 아님)를 만든다. 허프만이 1952년에 발표했다.

```
반복: 빈도가 가장 작은 두 노드를 꺼내 하나로 합치고(빈도 = 합) 다시 넣는다.
      노드가 하나 남으면 그것이 트리의 뿌리다.
왼쪽 가지 0, 오른쪽 가지 1 → 잎까지의 경로가 부호.
```

가장 드문 두 문자를 트리 가장 깊은 곳의 형제로 둬도 손해가 없다는 교환 논증이 정당성의 핵심이다. 최소 힙을 쓰면 문자 종류 수 k 에 대해 O(k log k) 다.

## 직접 해 보기

활동 선택, 동전 거스름돈(탐욕 vs 최적), 허프만 부호를 차례로 돌린다. python3 로 실행해 확인했다.

```python
import heapq
from collections import Counter

# 1) 활동 선택: 끝나는 시각이 가장 이른 것부터
meetings = [(1, 4), (3, 5), (0, 6), (5, 7), (3, 9), (5, 9),
            (6, 10), (8, 11), (8, 12), (2, 14), (12, 16)]
chosen, end = [], float("-inf")
for s, e in sorted(meetings, key=lambda m: m[1]):
    if s >= end:
        chosen.append((s, e)); end = e
print("선택된 회의:", chosen)

# 2) 거스름돈: 탐욕이 맞을 때와 틀릴 때
def greedy_coins(amount, coins):
    used = []
    for c in sorted(coins, reverse=True):
        while amount >= c:
            amount -= c; used.append(c)
    return used

def optimal_coins(amount, coins):          # 비교용 동적 계획법
    best = [0] + [float("inf")] * amount
    for v in range(1, amount + 1):
        for c in coins:
            if c <= v:
                best[v] = min(best[v], best[v - c] + 1)
    return best[amount]

for coins, amt in (([500, 100, 50, 10], 1260), ([4, 3, 1], 6)):
    g = greedy_coins(amt, coins)
    print(coins, amt, "탐욕:", len(g), g, "| 최적:", optimal_coins(amt, coins))

# 3) 허프만 부호
text = "abracadabra"
heap = [(f, i, ch) for i, (ch, f) in enumerate(sorted(Counter(text).items()))]
heapq.heapify(heap)
uid = len(heap)                             # 빈도가 같을 때 비교용 일련번호
while len(heap) > 1:
    f1, _, a = heapq.heappop(heap)          # 가장 드문 둘을 합친다
    f2, _, b = heapq.heappop(heap)
    heapq.heappush(heap, (f1 + f2, uid, (a, b))); uid += 1
codes = {}
def walk(node, prefix):
    if isinstance(node, str):
        codes[node] = prefix or "0"; return
    walk(node[0], prefix + "0"); walk(node[1], prefix + "1")
walk(heap[0][2], "")
bits = sum(len(codes[ch]) for ch in text)
print("부호:", dict(sorted(codes.items())), "| 총 비트:", bits, "vs 고정 3비트:", 3 * len(text))
```

출력:

```
선택된 회의: [(1, 4), (5, 7), (8, 11), (12, 16)]
[500, 100, 50, 10] 1260 탐욕: 6 [500, 500, 100, 100, 50, 10] | 최적: 6
[4, 3, 1] 6 탐욕: 3 [4, 1, 1] | 최적: 2
부호: {'a': '0', 'b': '110', 'c': '100', 'd': '101', 'r': '111'} | 총 비트: 23 vs 고정 3비트: 33
```

가장 흔한 'a'(5번)가 1비트, 나머지가 3비트를 받았다. 문자 5종을 고정 길이로 표현하면 3비트씩 33비트인데 허프만은 23비트다. 힙에 `uid` 를 넣은 이유는 빈도가 같을 때 튜플 비교가 문자열과 튜플을 비교하다 오류가 나지 않게 하기 위해서다.

## 현업에서는

- **압축.** DEFLATE(zip, gzip, PNG 내부)는 LZ77 로 반복을 줄인 뒤 허프만 부호로 남은 기호를 부호화한다. 이 구조는 RFC 1951 에 정의되어 있다.
- **쿠버네티스 스케줄러.** kube-scheduler 는 파드 하나마다 조건을 통과한 노드들에 점수를 매기고 가장 높은 점수의 노드에 배치한다. 지금 이 파드에 가장 좋은 노드를 고르고 나중에 재배치하지 않는다는 점에서 탐욕적이다. 그래서 파드가 쌓이는 순서에 따라 전체 배치가 최적이 아닐 수 있고, 이를 보정하는 descheduler 같은 별도 도구가 생겼다.
- **캐시 교체.** 다음에 가장 늦게 쓰일 것을 버리는 Belady 의 최적 교체는 미래를 알아야 하는 탐욕이다. 실무 LRU 는 과거로 미래를 추정하는 근사다.
- **일정·자원 할당.** 회의실 배정, 배치 작업 슬롯 할당처럼 구간 문제는 끝나는 시각 순 탐욕이 출발점이 된다.

## 확인 문제

1. 활동 선택에서 "가장 짧은 회의부터" 규칙의 반례를 하나 만들어라.
2. 탐욕과 동적 계획법이 공유하는 성질과 다른 성질은 각각 무엇인가?
3. 분할 배낭 문제에서는 탐욕이 최적인데 0/1 배낭에서는 아닌 이유는?
4. 허프만 부호가 접두 부호여야 하는 이유는?

### 풀이

1. [0,10), [9,12), [11,20). 가장 짧은 [9,12) 를 고르면 나머지 둘과 다 겹쳐 1개. 최적은 [0,10), [11,20) 의 2개.
2. 공유: 최적 부분 구조. 다른 점: 탐욕은 탐욕 선택 속성이 있어 한 가지 선택만 따라가고, 동적 계획법은 모든 선택지의 하위 문제를 풀어 비교한다.
3. 쪼갤 수 있으면 남는 공간을 다음 물건의 일부로 꽉 채울 수 있어 무게당 가치 순서가 최적이다. 쪼갤 수 없으면 무게당 가치가 높은 물건이 공간을 애매하게 남겨 전체 가치가 떨어질 수 있다.
4. 구분자 없이 비트열을 이어 붙여도 앞에서부터 한 가지로만 해독되게 하려고. 어떤 부호가 다른 부호의 접두사면 어디서 끊을지 모호해진다.

## 더 읽을거리 (References)

- D. A. Huffman, "A Method for the Construction of Minimum-Redundancy Codes", *Proceedings of the IRE* 40(9), 1952.
- IETF, [RFC 1951 — DEFLATE Compressed Data Format Specification](https://www.rfc-editor.org/rfc/rfc1951)
- Kubernetes 공식 문서, [Kubernetes Scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/)
- NIST Dictionary of Algorithms and Data Structures, [greedy algorithm](https://xlinux.nist.gov/dads/HTML/greedyalgo.html)
