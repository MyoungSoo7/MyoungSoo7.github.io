---
layout: post
title: "[CS300 #108] 뮤텍스·세마포어·모니터 — 동기화 도구 세 가지"
date: 2026-10-10 19:48:00 +0900
categories: [cs]
tags: [cs300, operating-systems, mutex, semaphore, monitor]
---

컴퓨터공학 300 주제 시리즈의 108번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

뮤텍스는 "한 번에 하나만", 세마포어는 "한 번에 N 개까지"와 "신호 보내기", 모니터는 "락과 조건 변수를 객체에 묶어 실수하기 어렵게 만든 구조"로, 모두 임계 구역과 실행 순서를 통제하는 도구다.

## 왜 필요한가

107번 글에서 공유 자원을 보호하려면 임계 구역을 상호 배제해야 한다는 것을 보았다. 그런데 실제 동시성 문제는 상호 배제만으로 끝나지 않는다.

- 동시에 DB 연결을 10개까지만 쓰고 싶다. (개수 제한)
- 큐에 데이터가 들어올 때까지 소비자가 기다려야 한다. (순서·조건 대기)
- 락을 잡고 나오는 것을 깜빡하는 실수를 언어 차원에서 막고 싶다. (구조화)

이 요구들에 각각 대응하는 것이 뮤텍스, 세마포어, 모니터(조건 변수)다. 이름은 다르지만 모두 "기다려야 하면 잠들고, 조건이 되면 깨운다"는 같은 뼈대 위에 있다.

## 핵심 개념

### 뮤텍스(Mutex)

**MUTual EXclusion** 의 줄임말이다. 상태는 잠김/풀림 둘뿐이다.

- `lock()`: 풀려 있으면 잠그고 들어간다. 잠겨 있으면 풀릴 때까지 기다린다.
- `unlock()`: 풀어 준다. **잠근 스레드만 풀 수 있다**는 소유권 개념이 있다.

기다리는 방식에 따라 두 종류로 나뉜다.

| 방식 | 동작 | 적합한 경우 |
|---|---|---|
| 스핀락 | 풀릴 때까지 루프를 돌며 계속 확인한다 | 임계 구역이 매우 짧고 멀티코어일 때, 커널 내부 |
| 블로킹 락 | 잠들고, 해제될 때 커널이 깨워 준다 | 대기가 길 수 있을 때, 일반 애플리케이션 |

리눅스의 pthread 뮤텍스는 **futex(fast user-space mutex)** 위에 만들어진다. 경합이 없으면 사용자 공간의 원자 연산 한 번으로 끝나고, 경합이 있을 때만 `futex()` 시스템 콜로 커널에 들어가 잠든다. 그래서 경합 없는 락은 매우 싸다.

### 세마포어(Semaphore)

다익스트라가 제안한 정수 카운터 기반 도구다. 원래 연산 이름은 네덜란드어에서 온 **P**(대기)와 **V**(신호)다.

```
P(S):  S 가 0 보다 커질 때까지 기다린 뒤 S -= 1    (wait, acquire, down)
V(S):  S += 1, 기다리는 쪽이 있으면 하나를 깨운다   (signal, release, up)
```

| 종류 | 초기값 | 용도 |
|---|---|---|
| 이진 세마포어 | 1 | 상호 배제(뮤텍스처럼) |
| 계수 세마포어 | N | 자원 N 개 풀 관리 |
| 신호용 세마포어 | 0 | "이 일이 끝났다"를 다른 스레드에 알림 |

뮤텍스와의 결정적 차이는 **소유권이 없다**는 점이다. 한 스레드가 P 를 하고 다른 스레드가 V 를 해도 된다. 그래서 스레드 간 신호 전달에 쓸 수 있지만, 그만큼 잘못 짝을 맞추기도 쉽다.

### 모니터(Monitor)와 조건 변수

세마포어로 복잡한 동기화를 짜다 보면 P 와 V 의 순서를 하나만 바꿔도 교착 상태가 된다. 호어(C. A. R. Hoare)와 브린치 한센(Per Brinch Hansen)이 1970년대에 제안한 **모니터**는 이를 구조로 해결한다.

- 공유 데이터와 그것을 다루는 프로시저를 하나로 묶는다.
- 모니터 안에는 한 번에 한 스레드만 들어올 수 있다(진입 시 자동 락).
- 조건을 기다려야 하면 **조건 변수**에서 `wait()` 한다. 이때 락을 **원자적으로 놓고** 잠든다.
- 다른 스레드가 조건을 바꾼 뒤 `signal()`/`notify()` 로 깨운다.

자바의 `synchronized` + `wait/notify`, 파이썬의 `threading.Condition`, pthread 의 `pthread_mutex_t` + `pthread_cond_t` 조합이 모두 모니터 패턴이다.

### 조건 대기는 반드시 while 로

```python
with cond:
    while not 조건:      # if 가 아니다
        cond.wait()
    ...조건이 참인 상태에서 작업...
```

대부분의 실제 시스템은 **메사(Mesa) 의미론**을 따른다. `notify` 는 깨어날 기회를 줄 뿐, 깨어난 스레드가 락을 다시 잡았을 때 조건이 여전히 참이라는 보장은 없다. 그 사이 다른 스레드가 먼저 자원을 가져갈 수 있다. 또한 POSIX 는 아무도 신호하지 않았는데 깨어나는 **가짜 깨어남(spurious wakeup)** 을 허용한다. 그래서 깨어나면 조건을 다시 확인해야 한다.

### 한눈에 비교

| | 뮤텍스 | 세마포어 | 모니터(락+조건 변수) |
|---|---|---|---|
| 상태 | 잠김/풀림 | 정수 카운터 | 락 + 대기 큐 |
| 소유권 | 있음 | 없음 | 락에 있음 |
| 주 용도 | 상호 배제 | 개수 제한, 신호 | 임의 조건 대기 |
| 실수 위험 | 해제 누락 | P/V 짝 오류 | 낮음(구조화) |

## 직접 해 보기

고전 문제인 **유한 버퍼(생산자-소비자)** 를 세마포어 버전과 모니터 버전으로 각각 풀어 본다.

```python
import threading, time, random
from collections import deque

# 1) 세마포어 두 개 + 뮤텍스 하나로 만든 유한 버퍼 (생산자-소비자)
CAP = 3
buf = deque()
empty = threading.Semaphore(CAP)   # 빈 칸 수
full = threading.Semaphore(0)      # 찬 칸 수
mutex = threading.Lock()           # 버퍼 자체 보호
max_seen = 0

def producer(n):
    global max_seen
    for i in range(n):
        empty.acquire()                 # 빈 칸이 없으면 잠든다
        with mutex:
            buf.append(i); max_seen = max(max_seen, len(buf))
        full.release()                  # 소비자 하나를 깨운다

def consumer(n, out):
    for _ in range(n):
        full.acquire()                  # 찬 칸이 없으면 잠든다
        with mutex:
            out.append(buf.popleft())
        empty.release()
        time.sleep(random.random() / 1000)

got = []
ts = [threading.Thread(target=producer, args=(100,)),
      threading.Thread(target=consumer, args=(100, got))]
for t in ts: t.start()
for t in ts: t.join()
print("세마포어 버전: 받은 개수", len(got), "순서 유지", got == list(range(100)), "버퍼 최대 크기", max_seen)

# 2) 같은 문제를 모니터(락 + 조건 변수) 스타일로
class BoundedBuffer:
    def __init__(self, cap):
        self.cap, self.items = cap, deque()
        self.cond = threading.Condition()           # 락을 내장한 조건 변수
    def put(self, x):
        with self.cond:                             # 모니터 진입 = 락 획득
            while len(self.items) == self.cap:      # if 가 아니라 while
                self.cond.wait()                    # 락을 놓고 잠든다
            self.items.append(x)
            self.cond.notify_all()
    def get(self):
        with self.cond:
            while not self.items:
                self.cond.wait()
            x = self.items.popleft()
            self.cond.notify_all()
            return x

bb, out = BoundedBuffer(3), []
p = threading.Thread(target=lambda: [bb.put(i) for i in range(100)])
c = threading.Thread(target=lambda: [out.append(bb.get()) for _ in range(100)])
p.start(); c.start(); p.join(); c.join()
print("모니터 버전  : 받은 개수", len(out), "순서 유지", out == list(range(100)))
```

```
세마포어 버전: 받은 개수 100 순서 유지 True 버퍼 최대 크기 3
모니터 버전  : 받은 개수 100 순서 유지 True
```

세마포어 버전에서 `empty.acquire()` 와 `mutex` 획득 순서를 바꿔 보자. 버퍼가 가득 찬 상태에서 생산자가 뮤텍스를 잡은 채 `empty` 를 기다리면, 소비자는 뮤텍스를 못 잡아 영원히 꺼내지 못한다. 교착 상태다(109번 글). 순서 하나에 정확성이 걸려 있다는 것이 세마포어의 어려움이고, 모니터 버전은 그런 실수의 여지가 적다.

## 현업에서는

- **연결 풀과 동시성 제한**: DB 연결 풀, 외부 API 호출 동시 개수 제한은 계수 세마포어 그 자체다. 파이썬 `asyncio.Semaphore(10)` 으로 동시 요청 수를 10개로 묶는 코드가 흔하다.
- **락 범위는 짧게**: 락을 잡은 채 네트워크 호출이나 디스크 I/O 를 하면 다른 스레드가 모두 줄을 선다. 공유 상태 갱신만 락 안에 두고, 느린 작업은 밖으로 뺀다.
- **멈춘 서비스의 스택에서 futex 보기**: 응답이 없는 프로세스를 `strace -p` 로 보면 `futex(..., FUTEX_WAIT, ...)` 에서 멈춰 있는 경우가 많다. 락이나 조건 변수 대기 중이라는 뜻이다. 스레드 덤프와 함께 보면 누가 락을 쥐고 있는지 찾을 수 있다.
- **리눅스 커널 내부**: 커널은 짧은 구간에는 스핀락, 잠들 수 있는 구간에는 커널 뮤텍스·세마포어, 읽기가 압도적인 자료구조에는 RCU 를 쓴다. 커널 문서의 locking 항목이 각 도구를 언제 쓰는지 설명한다.

## 확인 문제

1. 뮤텍스와 이진 세마포어의 가장 큰 차이는 무엇인가?
2. 동시 다운로드 수를 5개로 제한하려면 어떤 도구를 어떤 초기값으로 쓰는가?
3. 조건 변수에서 `wait()` 할 때 락을 원자적으로 놓아야 하는 이유는?
4. 조건 대기를 `if` 가 아니라 `while` 로 감싸야 하는 이유 두 가지는?
5. futex 가 경합 없는 락을 싸게 만드는 원리는?

### 풀이

1. 뮤텍스는 소유권이 있어 잠근 스레드만 풀 수 있다. 세마포어는 소유권이 없어 다른 스레드가 V 를 할 수 있다.
2. 계수 세마포어를 초기값 5 로 만들고, 다운로드 전에 acquire, 끝나면 release 한다.
3. 락을 놓는 것과 잠드는 것 사이에 틈이 있으면, 그 틈에 다른 스레드가 조건을 바꾸고 notify 한 신호를 놓쳐 영원히 잠들 수 있다(lost wakeup).
4. 메사 의미론에서는 깨어난 뒤 다른 스레드가 먼저 조건을 바꿔 놓을 수 있고, 가짜 깨어남도 허용되기 때문이다.
5. 락 상태를 사용자 공간 메모리에 두고 원자 명령으로 바로 잡는다. 경합이 있을 때만 시스템 콜로 커널에 들어가 잠들기 때문에 대부분의 경우 커널 진입이 없다.

## 더 읽을거리 (References)

- OSTEP, [Locks (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-locks.pdf), [Condition Variables (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-cv.pdf), [Semaphores (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-sema.pdf)
- E. W. Dijkstra, [Cooperating sequential processes (EWD123)](https://www.cs.utexas.edu/~EWD/transcriptions/EWD01xx/EWD123.html) — P/V 연산의 원전
- C. A. R. Hoare, "Monitors: An Operating System Structuring Concept", *Communications of the ACM* 17(10), 1974.
- POSIX.1-2024, [pthread_cond_wait](https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_cond_wait.html) — 가짜 깨어남 규정; Linux man-pages, [futex(7)](https://manpages.debian.org/bookworm/manpages/futex.7.en.html)
