---
layout: post
title: "*알고리즘 코딩테스트* 의 *중요도 *Tier S/A/B/C 분류* + *Java vs Python *언어별 *작성 시간 / 메모리 / 함정* 비교 + *3 개월 학습 로드맵* — *프로그래머스 / LeetCode / 백준 *모든 시험 대응* 의 *우선순위 가이드***"
date: 2026-06-12 14:00:00 +0900
categories: [algorithm, coding-test, java, python, interview]
tags: [algorithm, coding-test, leetcode, baekjoon, programmers, dfs, bfs, dp, two-pointer, sliding-window, binary-search, java, python, time-complexity]
---

이 글은 *코딩 테스트* 의 *방대한 토픽 리스트* 를 *중요도 순* (Tier S/A/B/C) 으로 *기계적으로 분류* 하고, *각 토픽 별 *Java vs Python* 작성 시간 / 메모리 / 함정* 을 *나란히 비교* 한다. 마지막에 *3 개월 학습 로드맵* 으로 *우선순위 명확히* 하는 *현실적 가이드*.

전 글 ([Python vs Java 자료구조](/2026/06/11/python-vs-java-data-structures-syntax-deep-comparison/)) 의 *후속편*. *내부 구현 비교* 는 *전 글에서 정리*, 이 글은 *코딩 테스트 의 *실전 무기* 정리.

읽고 가셔도 좋은 분:
1. *취준생 / 신입 1~2 년차* — *코딩 테스트 준비* 할 때 *어디부터 *시작할지* 막막한 사람
2. *경력 3-5 년차* — *코딩 테스트 다시 준비* 중. *시간이 *제한적* 이라 *우선순위 명확* 히 하고 싶은 사람
3. *Java + Python 둘 다 쓰는* 개발자 — *어느 언어로 *시험 보는 것 이 *유리* 한지 고민 중인 사람

---

## TL;DR

> *코딩 테스트 의 *80% 는 *Tier S 5 개 토픽* (자료구조 / DFS-BFS / 정렬 / 이분 탐색 / 해시) 에서 나옴. *남은 20% 에 *Tier A-C* 가 분포. *Python 이 *작성 시간 * 1.5-2× 빠름*, *Java 가 *메모리 / 실행 시간 *2-3× 우월*. *시간 제한 빡빡한 *백준 골드 이상* 은 *Java 권장*, *프로그래머스 / LeetCode 는 *Python 권장*. *3 개월 로드맵* 으로 *기계적 우선순위* 가능.

**한 표로**:

| Tier | 토픽 | 출제 빈도 | 학습 우선순위 |
|------|------|---------|-------------|
| **S** | 자료구조 / DFS-BFS / 정렬 / 이분 탐색 / 해시 | **80%** | **1-4 주차** |
| **A** | DP / 그리디 / 투포인터 / 슬라이딩 윈도우 / 백트래킹 | 15% | 5-8 주차 |
| **B** | 다익스트라 / 우선순위 큐 / 분할정복 / 비트마스킹 | 4% | 9-10 주차 |
| **C** | 세그먼트 트리 / MST / 위상정렬 / SCC | 1% | 11-12 주차 (선택) |

---

## 0. *왜 *중요도 순* 인가*

> *알고리즘 토픽이 *수십 개*. *3 개월 학습 시간* 에 *전부 마스터 불가능*. *출제 빈도 와 *난이도 곡선* 의 *현실적 *최적해* 가 *Tier 분류*. *시간 투자 1 시간 당 *통과율 증가* 가 *가장 큰 토픽 부터* 학습.

**현실**:
- *백준 골드 / 프로그래머스 Lv 3* 까지는 *Tier S 5 개 + Tier A 1-2 개* 면 충분
- *카카오 / 네이버 본선 / 삼성 SW 역량 / LG CNS* 는 *Tier B 까지*
- *현대차 / 토스 / 라인 후반부* 는 *Tier C 도 필요*

---

## 1. *Tier S — *필수 5 개 토픽***

### 1.1 *기본 자료구조 (배열 / 리스트 / 해시 / 스택 / 큐)*

**왜 Tier S**: *모든 문제의 *기본 인프라*. *데이터 입출력 / 빈도 카운트 / 순회* 등 *반드시 사용*.

#### Python
```python
# 빈도 카운트 — 한 줄
from collections import Counter
freq = Counter([1, 2, 2, 3, 3, 3])
# Counter({3: 3, 2: 2, 1: 1})

# Stack
stack = []
stack.append(1)
stack.append(2)
top = stack.pop()      # 2

# Queue (BFS 용)
from collections import deque
q = deque([1, 2, 3])
q.popleft()            # 1, O(1)
q.append(4)
```

#### Java
```java
// 빈도 카운트
Map<Integer, Integer> freq = new HashMap<>();
for (int n : nums) {
    freq.merge(n, 1, Integer::sum);   // ★ merge 패턴
}

// Stack — Deque 권장 (Stack class 는 deprecated)
Deque<Integer> stack = new ArrayDeque<>();
stack.push(1);
stack.push(2);
int top = stack.pop();   // 2

// Queue
Deque<Integer> queue = new ArrayDeque<>();
queue.offer(1);
queue.poll();   // 1
```

**작성 시간 비교**:

| 작업 | Python | Java |
|------|--------|------|
| 빈도 카운트 | 1 줄 | 3 줄 |
| Stack | 1 줄 (list) | 1 줄 (ArrayDeque) |
| Queue (FIFO) | 1 줄 (deque) | 1 줄 (ArrayDeque) |
| Sort + reverse | `sorted(nums, reverse=True)` | `Arrays.sort()` + `Collections.reverse()` 2 줄 |

→ *Python 의 *컬렉션 라이브러리* 가 *코딩 테스트 *압도적 우위*.

**함정**:
- *Java 의 `Stack` class 는 `Vector` 상속 — *synchronized — 느림*. `ArrayDeque` 권장.
- *Python 의 `list.pop(0)` 은 O(n)*. *반드시 `collections.deque`*.
- *Python 의 `set.add()` 가 *해시 가능 타입만 — list/dict 는 X*. `frozenset` 또는 `tuple` 변환.

### 1.2 *DFS / BFS*

**왜 Tier S**: *그래프 / 트리 / 격자 탐색* 의 *기본 도구*. *모든 코딩 테스트의 *30%+ 등장*.

#### DFS — Python (재귀)
```python
def dfs(graph, start, visited):
    visited.add(start)
    for neighbor in graph[start]:
        if neighbor not in visited:
            dfs(graph, neighbor, visited)

# Python 의 *재귀 limit 기본 1000* — 큰 그래프는
import sys
sys.setrecursionlimit(10**6)
```

#### DFS — Java
```java
void dfs(Map<Integer, List<Integer>> graph, int start, Set<Integer> visited) {
    visited.add(start);
    for (int neighbor : graph.getOrDefault(start, List.of())) {
        if (!visited.contains(neighbor)) {
            dfs(graph, neighbor, visited);
        }
    }
}

// Java JVM stack default = ~512KB
// 깊이 큰 재귀 시 -Xss 옵션으로 늘림
// java -Xss10m Solution
```

#### BFS — Python
```python
from collections import deque

def bfs(graph, start):
    visited = {start}
    q = deque([start])
    while q:
        node = q.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                q.append(neighbor)
    return visited
```

#### BFS — Java
```java
Set<Integer> bfs(Map<Integer, List<Integer>> graph, int start) {
    Set<Integer> visited = new HashSet<>();
    Deque<Integer> q = new ArrayDeque<>();
    q.offer(start);
    visited.add(start);
    while (!q.isEmpty()) {
        int node = q.poll();
        for (int neighbor : graph.getOrDefault(node, List.of())) {
            if (visited.add(neighbor)) {   // ★ add 의 반환값으로 한 줄
                q.offer(neighbor);
            }
        }
    }
    return visited;
}
```

**격자 (2D) — *전형 패턴***:

```python
# Python — 4방향 탐색
def grid_bfs(grid):
    n, m = len(grid), len(grid[0])
    visited = [[False] * m for _ in range(n)]
    dr = [-1, 1, 0, 0]
    dc = [0, 0, -1, 1]
    
    def bfs(r, c):
        q = deque([(r, c)])
        visited[r][c] = True
        while q:
            cr, cc = q.popleft()
            for i in range(4):
                nr, nc = cr + dr[i], cc + dc[i]
                if 0 <= nr < n and 0 <= nc < m and not visited[nr][nc]:
                    visited[nr][nc] = True
                    q.append((nr, nc))
```

**함정**:
- *Python 의 *재귀가 *Java 보다 *느림* — 작은 그래프 외엔 *BFS 권장*
- *Java 의 *재귀 stack 이 *작음 — 깊이 1만+ 면 *StackOverflow*

### 1.3 *정렬 (Sort)*

**왜 Tier S**: *모든 문제의 *전처리*. *Two pointer / 그리디 / 이분 탐색* 의 *전제 조건*.

#### Python
```python
nums = [3, 1, 4, 1, 5]
nums.sort()                      # in-place
sorted_nums = sorted(nums)       # new list

# 커스텀 정렬 — 튜플로 multiple key
people = [("alice", 30), ("bob", 25)]
people.sort(key=lambda x: (x[1], x[0]))     # 나이 → 이름

# 내림차순
nums.sort(reverse=True)
```

#### Java
```java
int[] nums = {3, 1, 4, 1, 5};
Arrays.sort(nums);   // 기본 오름차순

// 객체 정렬 — Comparator
people.sort(Comparator.comparingInt(Person::getAge)
                       .thenComparing(Person::getName));

// 내림차순 — primitive 는 안 됨 (Integer[] 로 변환)
Integer[] nums2 = {3, 1, 4, 1, 5};
Arrays.sort(nums2, Comparator.reverseOrder());
```

**함정**:
- *Python 의 `sort()` 는 *in-place*, `sorted()` 는 *new list*. *return 값을 *변수에 할당 *주의*.
- *Java 의 *primitive 배열 내림차순* 안 됨. `Integer[]` 박싱 후 `Comparator.reverseOrder()`.
- *Python 은 *Timsort O(n log n)* (안정). *Java 도 동일*.

### 1.4 *이분 탐색 (Binary Search)*

**왜 Tier S**: *O(log n)* 가 *O(n)* 의 *유일한 탈출구*. *"최소값을 찾는데 *어떤 값" 패턴 의 *표준*.

#### Python
```python
from bisect import bisect_left, bisect_right

nums = [1, 3, 5, 7, 9]
i = bisect_left(nums, 5)    # 2 (첫 등장 위치)
j = bisect_right(nums, 5)   # 3 (마지막 등장 + 1)

# 직접 구현
def binary_search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target: return mid
        elif nums[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
```

#### Java
```java
// 내장 — 정렬된 배열에서
int idx = Arrays.binarySearch(nums, 5);
// Returns: target 의 인덱스, 없으면 -(insertion point) - 1

// 직접 구현
int binarySearch(int[] nums, int target) {
    int lo = 0, hi = nums.length - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;   // ★ overflow 방지
        if (nums[mid] == target) return mid;
        else if (nums[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
```

**파라메트릭 서치 (Parametric Search)** — *고급 패턴*:

```python
# 문제: 배열 nums 를 K 개 그룹으로 나눌 때 *최소화 할 *최대 합*
def parametric_search(nums, k):
    def can_split(max_sum):
        # max_sum 이하로 K 개 그룹 만들 수 있나?
        groups = 1
        cur = 0
        for n in nums:
            if cur + n > max_sum:
                groups += 1
                cur = n
            else:
                cur += n
        return groups <= k
    
    lo, hi = max(nums), sum(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if can_split(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

**함정**:
- *(lo + hi) // 2* Python 은 *오버플로 X*. *Java 는 *2^31 - 1 초과 시* 음수 — `lo + (hi - lo) / 2` 필수.

### 1.5 *해시 (HashMap / HashSet)*

**왜 Tier S**: *시간 복잡도의 *마법사*. *"X 가 있는가" 의 *O(1)*. *Two Sum 류 의 *기본 도구*.

#### Python
```python
# Two Sum 의 한 줄 풀이
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
```

#### Java
```java
public int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        Integer prev = seen.get(target - nums[i]);
        if (prev != null) return new int[]{prev, i};
        seen.put(nums[i], i);
    }
    return new int[]{};
}
```

**함정**:
- *Python 의 *`dict.get(k, default)` 가 *Java `getOrDefault` 보다 *간결*
- *Java 의 *autoboxing* — `Map<Integer, Integer>` 가 *primitive 보다 *느림*. *대량 데이터는 *`int[]` 활용*.

---

## 2. *Tier A — *자주 출제 5 개***

### 2.1 *동적 계획법 (DP)*

**왜 Tier A**: *프로그래머스 Lv 3 / LeetCode Medium 의 *주력*. *점화식 만들기* 가 *진짜 *어려움*.

#### Python
```python
# 최장 증가 부분수열 (LIS) — O(n log n)
from bisect import bisect_left

def lis(nums):
    tails = []
    for n in nums:
        i = bisect_left(tails, n)
        if i == len(tails):
            tails.append(n)
        else:
            tails[i] = n
    return len(tails)

# 배낭 문제 (0/1 Knapsack)
def knapsack(items, capacity):
    dp = [0] * (capacity + 1)
    for weight, value in items:
        for c in range(capacity, weight - 1, -1):
            dp[c] = max(dp[c], dp[c - weight] + value)
    return dp[capacity]
```

#### Java
```java
public int lis(int[] nums) {
    List<Integer> tails = new ArrayList<>();
    for (int n : nums) {
        int i = Collections.binarySearch(tails, n);
        if (i < 0) i = -i - 1;
        if (i == tails.size()) tails.add(n);
        else tails.set(i, n);
    }
    return tails.size();
}
```

**함정**:
- *Python 의 *재귀 + memoization* 이 *Java 보다 *짧지만*, *재귀 limit + GIL* 로 *느림*. *Bottom-up DP* 권장.
- *Java 는 *2D DP 배열 *메모리 효율* 우위.

### 2.2 *그리디 (Greedy)*

```python
# 활동 선택 — 끝나는 시각으로 정렬 후 그리디
def activity_selection(activities):
    activities.sort(key=lambda x: x[1])
    count, last_end = 0, 0
    for start, end in activities:
        if start >= last_end:
            count += 1
            last_end = end
    return count
```

```java
public int activitySelection(int[][] activities) {
    Arrays.sort(activities, (a, b) -> a[1] - b[1]);
    int count = 0, lastEnd = 0;
    for (int[] a : activities) {
        if (a[0] >= lastEnd) {
            count++;
            lastEnd = a[1];
        }
    }
    return count;
}
```

### 2.3 *투포인터 (Two Pointer)*

```python
def two_sum_sorted(nums, target):
    l, r = 0, len(nums) - 1
    while l < r:
        s = nums[l] + nums[r]
        if s == target: return [l, r]
        elif s < target: l += 1
        else: r -= 1
```

```java
int[] twoSumSorted(int[] nums, int target) {
    int l = 0, r = nums.length - 1;
    while (l < r) {
        int s = nums[l] + nums[r];
        if (s == target) return new int[]{l, r};
        else if (s < target) l++;
        else r--;
    }
    return new int[]{};
}
```

### 2.4 *슬라이딩 윈도우 (Sliding Window)*

```python
# 길이 K 의 최대 합
def max_subarray_k(nums, k):
    window = sum(nums[:k])
    best = window
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        best = max(best, window)
    return best
```

### 2.5 *백트래킹 (Backtracking)*

```python
# N-Queens
def solve_nqueens(n):
    result = []
    def backtrack(row, cols, diag1, diag2, path):
        if row == n:
            result.append(path[:])
            return
        for col in range(n):
            if col in cols or row - col in diag1 or row + col in diag2:
                continue
            cols.add(col)
            diag1.add(row - col)
            diag2.add(row + col)
            path.append(col)
            backtrack(row + 1, cols, diag1, diag2, path)
            cols.remove(col)
            diag1.remove(row - col)
            diag2.remove(row + col)
            path.pop()
    backtrack(0, set(), set(), set(), [])
    return result
```

---

## 3. *Tier B — *가끔 출제*

### 3.1 *다익스트라 (Dijkstra)*

```python
import heapq

def dijkstra(graph, start):
    dist = {n: float('inf') for n in graph}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, node = heapq.heappop(pq)
        if d > dist[node]: continue
        for neighbor, weight in graph[node]:
            nd = d + weight
            if nd < dist[neighbor]:
                dist[neighbor] = nd
                heapq.heappush(pq, (nd, neighbor))
    return dist
```

```java
public Map<Integer, Integer> dijkstra(Map<Integer, List<int[]>> graph, int start) {
    Map<Integer, Integer> dist = new HashMap<>();
    for (int n : graph.keySet()) dist.put(n, Integer.MAX_VALUE);
    dist.put(start, 0);
    PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> a[0] - b[0]);
    pq.offer(new int[]{0, start});
    while (!pq.isEmpty()) {
        int[] cur = pq.poll();
        int d = cur[0], node = cur[1];
        if (d > dist.get(node)) continue;
        for (int[] e : graph.getOrDefault(node, List.of())) {
            int nd = d + e[1];
            if (nd < dist.get(e[0])) {
                dist.put(e[0], nd);
                pq.offer(new int[]{nd, e[0]});
            }
        }
    }
    return dist;
}
```

### 3.2 *분할 정복 (Merge Sort, Quick Select)*

### 3.3 *비트마스킹 — *부분 집합 DP**

```python
# TSP — bitmask DP
def tsp(graph, n):
    INF = float('inf')
    dp = [[INF] * n for _ in range(1 << n)]
    dp[1][0] = 0
    for mask in range(1 << n):
        for u in range(n):
            if not (mask & (1 << u)) or dp[mask][u] == INF: continue
            for v in range(n):
                if mask & (1 << v): continue
                new_mask = mask | (1 << v)
                dp[new_mask][v] = min(dp[new_mask][v], dp[mask][u] + graph[u][v])
    return min(dp[(1<<n)-1][i] + graph[i][0] for i in range(1, n))
```

---

## 4. *Tier C — *고급 (선택)*

| 토픽 | 출제 회사 |
|------|---------|
| 세그먼트 트리 / 펜윅 트리 | 카카오 본선, 토스 후반부 |
| MST (Kruskal / Prim) | 삼성 SW 역량 |
| 위상 정렬 | LG CNS, 네이버 |
| 강한 연결 요소 (SCC) | 거의 출제 X |
| 최대 유량 (Max Flow) | 대학원 입시 외 거의 X |

> *Tier C* 는 *시간이 *남으면* 학습. *공기업 / 외국계는 *Tier S + A* 만 으로 *통과*.

---

## 5. *Java vs Python — *코딩 테스트 *언어 선택***

### 5.1 *작성 시간 비교*

| 작업 | Python | Java | 비율 |
|------|--------|------|------|
| 입력 파싱 | `list(map(int, input().split()))` 1 줄 | `BufferedReader + split + parseInt` 5 줄 | 5× |
| 빈도 카운트 | `Counter(nums)` 1 줄 | `HashMap.merge` 3 줄 | 3× |
| 정렬 + key | `sorted(nums, key=...)` 1 줄 | `Comparator + sort` 3-4 줄 | 4× |
| 슬라이싱 | `nums[i:j]` 1 줄 | `Arrays.copyOfRange()` 1 줄 | 1× |
| 전체 평균 | 1× (baseline) | 1.5-2× | - |

→ *Python 이 *작성 속도 *압도*.

### 5.2 *실행 시간 / 메모리 비교*

| 항목 | Python | Java |
|------|--------|------|
| 실행 시간 | 1× (baseline) | 0.3-0.5× (Java가 빠름) |
| 메모리 | 1× (baseline) | 0.4-0.6× (Java가 적음) |
| 시간 제한 빡빡한 문제 (백준 골드+) | *불리* | *우월* |
| 시간 제한 여유 (프로그래머스, LeetCode) | OK | OK |

### 5.3 *시험별 *권장 언어**

| 시험 | 권장 |
|------|------|
| LeetCode | **Python** (작성 속도 + 시간 제한 여유) |
| 프로그래머스 (Lv 1-3) | **Python** |
| 프로그래머스 (Lv 4-5) | **Java** (시간 제한 빡빡) |
| 백준 실버-골드 | **Python** |
| 백준 플래티넘+ | **Java / C++** |
| 카카오 / 네이버 본선 | **Python (작성 속도) 또는 Java (확실성)** |
| 삼성 SW 역량 | **Java / C++** (PyPy 불가능 환경) |

### 5.4 *Python 의 *PyPy 활용*

> *백준에서 *PyPy3 선택 가능*. *순수 Python 대비 *3-5× 빠름*. *재귀 / 큰 입력* 문제에 *PyPy3 권장*.

```
# 백준 문제 풀 때:
# 1차: Python3 으로 풀이 (작성 빠름)
# TLE 시: PyPy3 로 *제출 만 변경* — 다시 풀이 필요 X
```

---

## 6. *3 개월 학습 로드맵*

### *1-2 주차 — *기본 자료구조 + 문법***

- 리스트 / 딕셔너리 / 셋 / 큐 / 스택 *완전 익히기*
- *입출력 처리* (백준의 `sys.stdin` / Java `BufferedReader`)
- *시간 복잡도 *감각*
- **목표**: 백준 *브론즈 → 실버 1*, 프로그래머스 Lv 1 *전부*

### *3-4 주차 — *DFS / BFS / 정렬 / 이분 탐색 / 해시***

- *그래프 / 트리 / 격자 탐색 *완성*
- *정렬 + 커스텀 비교*
- *이분 탐색 + 파라메트릭 서치*
- **목표**: 프로그래머스 Lv 2, 백준 실버 → 골드 4

### *5-6 주차 — *DP / 그리디 / 투포인터 / 슬라이딩***

- *점화식 만드는 *감각*
- *그리디 vs DP* 의 *경계*
- *투포인터 / 슬라이딩 *전형 패턴 5 개*
- **목표**: 프로그래머스 Lv 3 절반, 백준 골드 3

### *7-8 주차 — *백트래킹 + DP 심화 + 트리***

- *재귀 + 가지치기* 패턴
- *2D / 3D DP*
- *트리 순회 + 트리 DP*
- **목표**: 프로그래머스 Lv 3 *대부분*, 백준 골드 2-1

### *9-10 주차 — *다익스트라 + 우선순위 큐 + 비트마스킹***

- *그래프 최단 경로 *3 종* (다익스트라 / 플로이드 / 벨만포드)
- *비트마스킹 부분집합 DP*
- *수학 (조합론 / 모듈로)*
- **목표**: 백준 *플래티넘 5*

### *11-12 주차 — *모의 시험 + 약점 보강***

- *주 1 회 *프로그래머스 모의 시험*
- *오답 노트 *철저히*
- *알고리즘 별 *시간 측정*
- **목표**: 실제 시험 *합격 안정권*

---

## 7. *실전 시험 *공통 함정 5 가지*

### 7.1 *입력 처리 안 빠르게 — *TLE***

```python
# 느림 — input() 은 *매 호출 *parse + flush*
n = int(input())
for _ in range(n):
    nums.append(int(input()))

# 빠름
import sys
input = sys.stdin.readline
n = int(input())
```

```java
// 느림 — Scanner
Scanner sc = new Scanner(System.in);

// 빠름 — BufferedReader
BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
int n = Integer.parseInt(br.readLine());
```

### 7.2 *시간 복잡도 *암산 안 함**

```
n=10^5 → O(n log n) 까지 안전
n=10^4 → O(n^2) 까지 안전
n=10^3 → O(n^3) 까지 안전
n=20-25 → O(2^n) 가능 (백트래킹 + bitmask)
n>10^6 → O(n) 만 안전 (정렬도 위험)
```

> *문제 의 *N 범위 보고 *알고리즘 *기계적 선택*. *암산이 *습관* 이 되어야 함.

### 7.3 *재귀 한계*

```python
import sys
sys.setrecursionlimit(10**6)  # *반드시 필요 시 추가*
```

### 7.4 *Java 의 *primitive vs Wrapper 혼동***

```java
// 함정 — int[] 와 Integer[] 의 동작이 다름
int[] arr1 = {1, 2, 3};
Arrays.sort(arr1);   // 오름차순만

Integer[] arr2 = {1, 2, 3};
Arrays.sort(arr2, Comparator.reverseOrder());   // 내림차순 가능
```

### 7.5 *Python 의 *deepcopy / shallow copy***

```python
# 함정
matrix = [[0] * 3] * 3      # ❌ 같은 list 참조 3 개
matrix[0][0] = 1
print(matrix)               # [[1,0,0], [1,0,0], [1,0,0]]  ← *모두 변경*!

# 올바른 방법
matrix = [[0] * 3 for _ in range(3)]
```

---

## 8. *마무리 — *코딩 테스트 의 *진짜 의미***

### 8.1 *우선순위 가 *시간 효율의 핵심***

> *시간이 *제한적* 인 학습 — *Tier S 5 개 토픽을 *완벽히* 푸는 게 *Tier C 모든 토픽* 을 *얕게 푸는 것 보다 *합격에 *직결*.

### 8.2 *Java + Python *둘 다* 의 가치*

> *Python 으로 *빠르게 작성*, *Java 로 *시간 / 메모리 빡빡한 문제 대응*. *둘 다 익혀 두면 *모든 시험에 *유연한 대응*.

### 8.3 *이력서 변환 hook*

> *"코딩 테스트 합격 / 알고리즘 경험"* 한 줄에:
> - Tier S/A/B/C *분류 + 우선순위*
> - Java vs Python *작성 속도 / 실행 속도 / 메모리* 차이
> - 시험별 (LeetCode / 백준 / 프로그래머스) *권장 언어 + 근거*
> - *3 개월 로드맵 의 *주차별 목표*
> - 실전 함정 5 가지
> 
> *4 단 깊이 면접 답변 hook* 모두 준비.

---

## 부록 — *언어별 *템플릿 코드 (입력 처리)*

### Python — *백준 표준 템플릿*
```python
import sys
from collections import defaultdict, deque, Counter
from heapq import heappush, heappop
input = sys.stdin.readline
sys.setrecursionlimit(10**6)

def solve():
    n = int(input())
    nums = list(map(int, input().split()))
    # ...

if __name__ == "__main__":
    solve()
```

### Java — *백준 표준 템플릿*
```java
import java.util.*;
import java.io.*;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();
        
        int n = Integer.parseInt(br.readLine().trim());
        StringTokenizer st = new StringTokenizer(br.readLine());
        int[] nums = new int[n];
        for (int i = 0; i < n; i++) nums[i] = Integer.parseInt(st.nextToken());
        
        // ...
        
        System.out.print(sb);
    }
}
```

---

*다음 글:* *백준 / 프로그래머스 / LeetCode 의 *시험 환경 *5 가지 차이* — *부분 점수 / 시간 제한 / 메모리 제한 / 입출력 / 언어 버전*. 어디 *집중* 해야 하는지 정리.
