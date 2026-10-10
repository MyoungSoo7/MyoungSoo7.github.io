---
layout: post
title: "[CS300 #044] 큐와 원형 큐 — 먼저 온 것을 먼저, 배열 끝을 앞에 잇기"
date: 2026-10-10 18:44:00 +0900
categories: [cs]
tags: [cs300, data-structures, queue, circular-buffer, fifo]
---

컴퓨터공학 300 주제 시리즈의 044번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

큐는 뒤로 넣고 앞에서 빼는 FIFO(First-In, First-Out) 구조이고, 원형 큐는 고정 크기 배열의 끝과 처음을 나머지 연산으로 이어 붙여 원소를 옮기지 않고 큐를 만드는 방법이다.

## 왜 필요한가

스택이 "가장 최근 것부터"라면 큐는 "먼저 온 것부터"다. 은행 창구, 프린터 대기열처럼 공정함이 필요한 곳은 다 큐다. 컴퓨터 안에서는 더 많다. 키보드 입력 버퍼, 네트워크 카드의 수신 링, 운영체제의 실행 대기열, 메시지 브로커, 너비 우선 탐색(BFS), 쿠버네티스 컨트롤러의 작업 큐가 모두 큐다.

큐를 배울 때 핵심은 개념보다 **구현**이다. 앞 글에서 본 것처럼 배열 앞에서 빼면 매번 O(n) 이 든다. 그렇다고 연결 리스트를 쓰면 원소마다 할당이 생긴다. 원형 큐는 이 둘을 다 피한다. 고정된 메모리 한 덩어리로, 할당도 이동도 없이 넣고 뺀다. 그래서 커널과 장치 드라이버, 오디오·네트워크 버퍼처럼 성능과 예측 가능성이 중요한 곳에서 표준처럼 쓰인다.

## 핵심 개념

### 연산

| 연산 | 의미 | 원형 큐 비용 |
|---|---|---|
| `enqueue(x)` | 뒤(tail)에 넣기 | O(1) |
| `dequeue()` | 앞(head)에서 꺼내기 | O(1) |
| `peek()` | 앞을 보기 | O(1) |
| `size()` / `is_empty()` / `is_full()` | 상태 확인 | O(1) |

### 단순 배열 큐의 문제

배열에 `head` 와 `tail` 두 인덱스를 두고, 넣을 땐 `tail` 을, 뺄 땐 `head` 를 하나씩 늘린다고 하자. 원소를 옮기지 않으니 둘 다 O(1) 이다. 그런데 계속 넣고 빼면 두 인덱스가 오른쪽으로만 흘러가서, 앞쪽은 비어 있는데 뒤쪽 끝에 닿아 "꽉 찼다"고 말하게 된다.

```
초기:     [1][2][3][4][ ]      head=0, tail=4
두 번 뺌: [ ][ ][3][4][ ]      head=2, tail=4
두 번 넣음: [ ][ ][3][4][5] + 6 은?  → 끝에 닿음, 앞 두 칸은 놀고 있음
```

### 원형 큐: 끝에서 처음으로 감기

해법은 인덱스를 용량으로 나눈 나머지로 계산하는 것이다. 마지막 칸 다음은 0번 칸이 된다.

```
          head
           ▼
   ┌───┬───┬───┬───┬───┐
   │ 6 │ 7 │ 3 │ 4 │ 5 │        (cap=5, head=2, size=5)
   └───┴───┴───┴───┴───┘
     ▲ 
     └─ 5 다음 칸은 (4+1) % 5 = 0

논리적 순서: 3 → 4 → 5 → 6 → 7
```

- 다음에 꺼낼 위치: `head`
- 다음에 넣을 위치: `(head + size) % cap`
- 꺼낸 뒤: `head = (head + 1) % cap`

### 가득 참과 비어 있음 구분

`head` 와 `tail` 두 인덱스만 들고 있으면, 비었을 때도 `head == tail`, 가득 찼을 때도 `head == tail` 이 되어 구분이 안 된다. 흔히 쓰는 해법은 세 가지다.

1. **개수(size)를 따로 센다.** 이 글의 예제 방식이다. 가장 이해하기 쉽다.
2. **한 칸을 비워 둔다.** `(tail + 1) % cap == head` 를 가득 참으로 본다. 용량이 하나 줄지만 생산자와 소비자가 서로 다른 변수만 쓰게 되어, 락 없이 쓰는 단일 생산자·단일 소비자 링 버퍼에서 자주 쓴다.
3. **인덱스를 나머지 없이 계속 증가시키고, 쓸 때만 나머지를 취한다.** `tail - head` 가 곧 개수다. 용량을 2의 거듭제곱으로 잡으면 나머지 연산을 비트 AND(`& (cap - 1)`)로 바꿀 수 있다.

리눅스 커널 문서는 원형 버퍼 지원이 두 묶음으로 되어 있다고 설명한다. 2의 거듭제곱 크기 버퍼의 점유량을 계산하는 편의 함수, 그리고 생산자와 소비자가 락을 공유하지 않을 때 필요한 메모리 배리어다([Linux Kernel — Circular Buffers](https://docs.kernel.org/core-api/circular-buffers.html)). 같은 문서는 임의 크기 버퍼에서 점유량을 계산하려면 느린 나머지(나눗셈) 명령이 필요하다는 점을 2의 거듭제곱을 쓰는 이유로 든다.

### 꽉 찼을 때 정책

원형 큐는 크기가 고정이므로 꽉 찼을 때 무엇을 할지 정해야 한다.

| 정책 | 동작 | 쓰는 곳 |
|---|---|---|
| 거부 | 넣기 실패, 오류 반환 | 제한된 작업 큐, 백프레셔 |
| 대기 | 빈칸이 날 때까지 블록 | 스레드 간 생산자·소비자 |
| 덮어쓰기 | 가장 오래된 것을 버림 | 로그·메트릭 링 버퍼, 최근 N개 보관 |
| 확장 | 더 큰 배열로 이사 | 동적 큐(`ArrayDeque`, `collections.deque`) |

## 직접 해 보기

개수를 따로 세는 원형 큐를 만들고, 인덱스가 감기는 모습을 출력한다.

```python
class CircularQueue:
    def __init__(self, capacity):
        self.buf = [None] * capacity
        self.cap = capacity
        self.head = 0      # 다음에 꺼낼 위치
        self.size = 0

    def enqueue(self, x):
        if self.size == self.cap:
            raise OverflowError("queue full")
        tail = (self.head + self.size) % self.cap
        self.buf[tail] = x
        self.size += 1

    def dequeue(self):
        if self.size == 0:
            raise IndexError("queue empty")
        x = self.buf[self.head]
        self.buf[self.head] = None          # 참조 해제
        self.head = (self.head + 1) % self.cap
        self.size -= 1
        return x

    def __repr__(self):
        cells = ["." if v is None else str(v) for v in self.buf]
        return f"buf=[{' '.join(cells)}] head={self.head} size={self.size}"

q = CircularQueue(5)
for x in range(1, 5):
    q.enqueue(x)
print(q)
print("꺼냄:", q.dequeue(), q.dequeue())
print(q)
for x in (5, 6, 7):
    q.enqueue(x)          # 6, 7 은 배열 앞쪽으로 감겨 들어간다
print(q)
try:
    q.enqueue(8)
except OverflowError as e:
    print("오류:", e)
print("전부 꺼냄:", [q.dequeue() for _ in range(q.size)])
```

```
buf=[1 2 3 4 .] head=0 size=4
꺼냄: 1 2
buf=[. . 3 4 .] head=2 size=2
buf=[6 7 3 4 5] head=2 size=5
오류: queue full
전부 꺼냄: [3, 4, 5, 6, 7]
```

배열 안의 물리적 순서는 `6 7 3 4 5` 이지만, 꺼내는 순서는 넣은 순서 그대로 `3 4 5 6 7` 이다. `dequeue` 에서 꺼낸 칸을 `None` 으로 비우는 것도 중요하다. 그대로 두면 큐에서는 빠졌는데 배열이 참조를 계속 들고 있어 가비지 컬렉터가 그 객체를 회수하지 못한다.

파이썬에서 실제로 큐가 필요하면 직접 만들 필요 없이 `collections.deque` 를 쓴다. 스레드 사이에서 주고받을 때는 락을 대신 처리해 주는 `queue.Queue` 를 쓴다. `queue` 모듈 문서는 이것을 "다중 생산자, 다중 소비자 큐"라고 소개하고, 필요한 락 처리를 모두 구현한다고 적는다([Python queue](https://docs.python.org/3/library/queue.html)). `Queue(maxsize=n)` 으로 만들면 꽉 찼을 때 `put` 이 블록되어 위 표의 "대기" 정책이 된다.

## 현업에서는

- **네트워크와 장치 드라이버.** NIC 는 수신·송신 디스크립터를 링 형태로 둔다. 링이 꽉 차면 패킷이 버려진다. `ethtool -S` 같은 도구에서 보이는 드롭 카운터가 이 링이 넘쳤다는 신호인 경우가 많다.
- **쿠버네티스 컨트롤러.** client-go 의 `workqueue` 패키지는 컨트롤러가 처리할 객체 키를 담는 큐다. 문서는 이 큐의 성질을 "Fair: 넣은 순서대로 처리", "Stingy: 같은 항목을 동시에 여러 번 처리하지 않고, 처리 전에 여러 번 들어오면 한 번만 처리"라고 적는다([client-go workqueue](https://pkg.go.dev/k8s.io/client-go/util/workqueue)). 단순 FIFO 에 중복 제거와 재시도 지연을 얹은 형태다.
- **백프레셔.** 무한히 커지는 큐는 결국 메모리를 다 먹는다. 크기 제한이 있는 큐는 생산자에게 "천천히"를 알리는 장치가 된다. 장애 회고에서 "큐 길이 지표를 안 봤다"는 말이 자주 나오는 이유다.
- **최근 N개 로그.** 덮어쓰기 정책의 링 버퍼는 메모리 사용량이 고정이라 장시간 도는 데몬의 최근 이벤트 보관에 알맞다.

## 확인 문제

1. 용량 8 인 원형 큐에서 `head = 6`, `size = 4` 이면 다음에 넣을 인덱스는?
2. `head` 와 `tail` 만 쓰는 원형 큐에서 비었음과 가득 참이 구분되지 않는 이유와 해결책 두 가지는?
3. 용량을 2의 거듭제곱으로 잡으면 무엇이 좋은가?
4. `dequeue` 에서 꺼낸 칸을 비우지 않으면 어떤 문제가 생길 수 있는가?
5. BFS 에서 큐 대신 스택을 쓰면 탐색 순서는 무엇이 되는가?

### 풀이

1. (6 + 4) % 8 = 2.
2. 둘 다 `head == tail` 이기 때문이다. 개수를 따로 세거나, 한 칸을 비워 두어 `(tail+1) % cap == head` 를 가득 참으로 본다. (인덱스를 계속 증가시키는 방법도 있다.)
3. `i % cap` 을 `i & (cap - 1)` 로 바꿀 수 있어 나눗셈이 사라진다.
4. 큐에서 빠진 객체를 배열이 계속 참조해 가비지 컬렉션이 안 된다(메모리 누수처럼 보인다).
5. 깊이 우선 탐색(DFS) 순서가 된다.

## 더 읽을거리 (References)

- The Linux Kernel documentation, [Circular Buffers](https://docs.kernel.org/core-api/circular-buffers.html)
- Python Documentation, [queue — A synchronized queue class](https://docs.python.org/3/library/queue.html)
- Kubernetes client-go, [package workqueue](https://pkg.go.dev/k8s.io/client-go/util/workqueue)
- Robert Sedgewick, Kevin Wayne, *Algorithms*, 4th ed., Addison-Wesley, 2011 — 1.3 Bags, Queues, and Stacks
