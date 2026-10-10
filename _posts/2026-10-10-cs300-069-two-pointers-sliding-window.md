---
layout: post
title: "[CS300 #069] 투 포인터와 슬라이딩 윈도 — 이중 루프를 한 번의 훑기로"
date: 2026-10-10 19:09:00 +0900
categories: [cs]
tags: [cs300, algorithms, two-pointers, sliding-window, monotonic-deque]
---

컴퓨터공학 300 주제 시리즈의 069번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

두 인덱스가 각각 한 방향으로만 움직이면, 둘이 합쳐 최대 2n 걸음이라 전체가 Θ(n) 이다. 투 포인터와 슬라이딩 윈도는 "모든 쌍을 보는 Θ(n²)" 을 "다시 볼 필요 없는 후보를 버리며 한 번 훑는 Θ(n)" 으로 바꾸는 기법이다.

## 왜 필요한가

"합이 target 인 두 수", "길이 k 구간의 최대 합", "중복 없는 가장 긴 부분 문자열" 같은 문제는 모든 구간이나 모든 쌍을 보면 쉽게 풀린다. 그러나 구간은 n(n+1)/2 개다. n = 10만이면 50억 개다.

이 기법의 핵심 질문은 하나다. **포인터를 앞으로 움직였을 때, 버린 후보를 다시 볼 필요가 없다는 걸 증명할 수 있는가?** 증명이 되면 선형이 된다.

## 핵심 개념

### 유형 1. 양 끝에서 마주 보고 오기

정렬된 배열에서 합이 target 인 두 수를 찾는다.

```
a = [1, 2, 4, 7, 11, 15], target = 15
 i→                    ←j
 1 + 15 = 16 > 15  → j 를 왼쪽으로
 1 + 11 = 12 < 15  → i 를 오른쪽으로
 2 + 11 = 13 < 15  → i 를 오른쪽으로
 4 + 11 = 15       → 찾음
```

왜 맞는가. 합이 target 보다 크면 a[j] 와 짝지을 수 있는 가장 작은 수 a[i] 와 더해도 크다. 그러니 a[j] 는 어떤 남은 원소와도 답이 될 수 없어 버려도 된다. 작을 때는 대칭이다. 매 단계 후보 하나가 안전하게 사라지므로 최대 n−1 단계다.

### 유형 2. 같은 방향으로 가는 두 포인터

정렬된 배열의 중복 제거, 두 정렬 배열 병합, 연결 리스트에서 느린·빠른 포인터로 사이클 찾기(Floyd) 등이 여기에 든다. 병합 정렬의 결합 단계도 투 포인터다.

### 유형 3. 고정 길이 윈도

길이 k 구간의 합을 매번 새로 더하면 Θ(nk) 다. 윈도를 한 칸 옮길 때 들어온 값을 더하고 나간 값을 빼면 Θ(1) 이다.

```
[2 1 5] 1 3 2      합 8
 2 [1 5 1] 3 2     합 8 − 2 + 1 = 7
 2 1 [5 1 3] 2     합 7 − 1 + 3 = 9
```

### 유형 4. 가변 길이 윈도

"조건을 만족하는 가장 긴(짧은) 구간" 을 찾는다. 오른쪽 r 을 한 칸씩 늘리고, 조건이 깨지면 왼쪽 l 을 조건이 회복될 때까지 당긴다.

```
for r in range(n):
    윈도에 a[r] 추가
    while 윈도가 조건을 위반:
        윈도에서 a[l] 제거; l += 1
    답 갱신 (r - l + 1)
```

안쪽 while 이 있어도 Θ(n) 이다. l 은 전체 실행 동안 0 에서 n 까지 한 방향으로만 움직이므로 while 본문은 합쳐서 최대 n 번 실행된다. 이것이 분할 상환 분석의 전형적인 예다.

이 틀이 성립하려면 조건이 단조여야 한다. "구간이 조건을 위반하면 그 구간을 포함하는 더 큰 구간도 위반한다" 가 성립해야 l 을 되돌릴 필요가 없다. 음수가 섞인 배열에서 "합이 S 이상인 가장 짧은 구간" 은 이 성질이 깨져 단순 슬라이딩 윈도로 풀리지 않는다.

### 유형 5. 윈도 최댓값과 단조 덱

길이 k 윈도마다 최댓값을 구하려면 힙으로 O(n log k) 다. 덱에 "값이 감소하는 순서의 인덱스" 만 유지하면 O(n) 이다. 새 값 x 가 들어올 때 덱 뒤쪽에서 x 이하인 값들을 버린다. 그 값들은 x 보다 먼저 윈도를 떠나면서 x 보다 작으니, 앞으로 어떤 윈도에서도 최댓값이 될 수 없다. 각 인덱스는 덱에 한 번 들어가고 한 번 나오므로 총 Θ(n) 이다.

## 직접 해 보기

네 유형을 한 파일에 담았다. python3 로 실행해 확인했다.

```python
from collections import deque, Counter

def pair_sum_sorted(a, target):
    i, j = 0, len(a) - 1
    while i < j:
        s = a[i] + a[j]
        if s == target:
            return i, j
        if s < target:
            i += 1          # 더 키워야 한다 → 작은 쪽을 올린다
        else:
            j -= 1          # 줄여야 한다 → 큰 쪽을 내린다
    return None

def max_window_sum(a, k):
    s = sum(a[:k]); best = s
    for r in range(k, len(a)):
        s += a[r] - a[r - k]          # 들어온 것 더하고 나간 것 빼기
        best = max(best, s)
    return best

def longest_unique(s):
    cnt = Counter(); l = 0; best = 0
    for r, ch in enumerate(s):
        cnt[ch] += 1
        while cnt[ch] > 1:            # 조건이 깨지면 왼쪽을 줄인다
            cnt[s[l]] -= 1; l += 1
        best = max(best, r - l + 1)
    return best

def sliding_max(a, k):
    dq, out = deque(), []
    for i, x in enumerate(a):
        while dq and a[dq[-1]] <= x:  # 나보다 작은 뒤쪽 후보는 영영 최대가 못 된다
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:            # 윈도 밖으로 나간 앞쪽 제거
            dq.popleft()
        if i >= k - 1:
            out.append(a[dq[0]])
    return out

print(pair_sum_sorted([1, 2, 4, 7, 11, 15], 15))
print(max_window_sum([2, 1, 5, 1, 3, 2], 3))
print(longest_unique("abcabcbb"), longest_unique("pwwkew"))
print(sliding_max([1, 3, -1, -3, 5, 3, 6, 7], 3))
```

출력:

```
(2, 4)
9
3 3
[3, 3, 5, 5, 6, 7]
```

`collections.deque` 는 양 끝 삽입·삭제가 O(1) 이라 단조 덱에 알맞다. 리스트의 `pop(0)` 은 O(n) 이므로 여기서 쓰면 선형이 깨진다.

## 현업에서는

- **TCP 슬라이딩 윈도.** TCP 송신자는 수신자가 알려 준 윈도 크기만큼만 확인응답(ACK) 없이 보낼 수 있다. ACK 가 오면 윈도의 왼쪽 끝이 앞으로 밀린다. 이름 그대로 슬라이딩 윈도다.
- **레이트 리미터.** "최근 60초 동안 요청 100회" 같은 제한은 시간 기준 슬라이딩 윈도다. 타임스탬프를 덱에 넣고 60초보다 오래된 것을 앞에서 빼면 된다.
- **이동 평균과 지표.** 모니터링의 "최근 5분 평균" 은 고정 윈도 합을 갱신하는 방식으로 계산할 수 있다. Prometheus 의 `rate()` 처럼 구간 단위로 계산하는 함수들도 개념적으로 같은 질문을 던진다.
- **오토스케일링 안정화.** 쿠버네티스 HPA 는 축소 결정을 내릴 때 일정 시간 창 안의 추천값을 함께 보는 안정화 창(stabilization window)을 쓴다. 순간 값에 흔들리지 않으려는 장치다.

## 확인 문제

1. 가변 윈도 코드에 while 문이 루프 안에 있는데도 Θ(n) 인 이유는?
2. 정렬되지 않은 배열에서 합이 target 인 두 수를 찾으려면 투 포인터 대신 무엇을 쓰는 게 좋은가?
3. 음수가 섞인 배열에서 "합이 S 이상인 가장 짧은 구간" 에 단순 슬라이딩 윈도가 안 되는 이유는?
4. 단조 덱에서 덱 뒤쪽을 버릴 때 조건을 `<` 로 할지 `<=` 로 할지는 결과에 영향을 주는가?

### 풀이

1. 왼쪽 포인터 l 은 감소하지 않고 최대 n 까지만 증가한다. while 본문의 실행 횟수 합이 n 이하이므로 전체는 Θ(n).
2. 해시 집합. 한 번 훑으며 target − x 가 이미 본 값에 있는지 확인하면 평균 Θ(n). 정렬 후 투 포인터는 Θ(n log n).
3. 왼쪽을 줄였을 때 합이 오히려 커질 수 있어(음수를 빼는 경우) "위반 구간을 포함하는 구간도 위반" 이라는 단조성이 깨진다. 이때는 누적합과 단조 덱을 조합하는 다른 방법을 쓴다.
4. 최댓값 값 자체는 같다. `<=` 면 같은 값 중 최신 인덱스만 남아 덱이 더 짧다. 최댓값의 위치까지 필요하면 어느 쪽을 원하는지에 맞춰 고른다.

## 더 읽을거리 (References)

- IETF, [RFC 9293 — Transmission Control Protocol (TCP)](https://www.rfc-editor.org/rfc/rfc9293), 3.8.6절 윈도 관리
- Python 공식 문서, [collections.deque](https://docs.python.org/3/library/collections.html)
- Kubernetes 공식 문서, [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022.
