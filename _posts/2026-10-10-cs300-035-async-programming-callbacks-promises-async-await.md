---
layout: post
title: "[CS300 #035] 비동기 프로그래밍 — 콜백·프라미스·async/await"
date: 2026-10-10 18:35:00 +0900
categories: [cs]
tags: [cs300, programming, async, event-loop, promise]
---

컴퓨터공학 300 주제 시리즈의 035번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

비동기 프로그래밍은 I/O 를 기다리는 동안 스레드를 멈춰 세우지 않고 다른 일을 하게 하는 방식이며, 콜백 → 프라미스 → async/await 는 같은 아이디어를 점점 읽기 쉽게 표현해 온 역사다.

## 왜 필요한가

웹 서버가 하는 일의 대부분은 기다림이다. DB 응답을 기다리고, 외부 API 를 기다리고, 디스크를 기다린다. 요청 하나당 스레드 하나를 배정하고 그 스레드가 기다리는 동안 멈춰 있게 하면, 동시 요청 수만큼 스레드와 스택 메모리가 필요하다(#027). 1만 개 연결이면 1만 개 스레드다.

비동기 모델은 다른 길을 택한다. 기다려야 하는 지점에서 "끝나면 알려 달라"고 등록하고 즉시 다른 작업으로 넘어간다. 스레드 하나로도 수천 개의 연결을 동시에 다룰 수 있다. 브라우저의 JavaScript, Node.js, Python 의 asyncio 가 모두 이 모델이다.

## 핵심 개념

### 동기, 비동기, 동시, 병렬

용어부터 구분한다.

| 용어 | 뜻 |
|---|---|
| 동기(synchronous) | 호출하면 결과가 나올 때까지 호출자가 기다린다 |
| 비동기(asynchronous) | 호출은 즉시 돌아오고, 결과는 나중에 알림으로 받는다 |
| 동시성(concurrency) | 여러 작업이 겹치는 시간대에 진행된다(번갈아 실행해도 됨) |
| 병렬성(parallelism) | 여러 작업이 같은 순간에 실제로 동시에 실행된다(코어 여러 개) |

asyncio 나 Node.js 의 이벤트 루프는 **동시적이지만 병렬적이지 않다.** 한 스레드가 작업들을 번갈아 실행한다. 그래서 I/O 대기가 많은 일에 강하고, CPU 계산이 많은 일에는 이득이 없다.

### 이벤트 루프

비동기 런타임의 심장은 이벤트 루프다.

```
 ┌──────────────────────────────────────────┐
 │  1. 실행 가능한 작업(콜백/코루틴)을 하나 꺼내 실행 │
 │  2. 그 작업이 I/O 를 기다리면 등록하고 양보      │
 │  3. OS 에 "준비된 I/O 가 있나?" 묻기 (epoll 등) │
 │  4. 준비된 I/O 의 콜백을 실행 대기열에 넣기      │
 └──────────────── 반복 ─────────────────────┘
```

핵심 규칙: **한 작업이 양보하지 않으면 루프 전체가 멈춘다.** 비동기 함수 안에서 `time.sleep(1)` 이나 동기 DB 드라이버를 부르면, 그 1초 동안 다른 모든 요청이 멈춘다.

JavaScript 의 이벤트 루프에는 두 종류의 대기열이 있다. 프라미스 콜백 같은 **마이크로태스크**는 현재 작업이 끝나자마자 모두 처리되고, `setTimeout` 같은 **태스크(매크로태스크)** 는 그 다음이다. HTML 표준이 이 처리 모델을 정의한다([HTML Standard — Event loops](https://html.spec.whatwg.org/multipage/webappapis.html#event-loops)).

### 1단계: 콜백

가장 원시적인 방식은 "끝나면 이 함수를 불러 달라"고 함수를 넘기는 것이다.

```javascript
readFile("a.txt", (err, a) => {
  if (err) return handle(err);
  readFile("b.txt", (err, b) => {
    if (err) return handle(err);
    save(a + b, (err) => { /* ... */ });
  });
});
```

순차 작업이 늘수록 들여쓰기가 깊어지고(콜백 지옥), 오류 처리를 단계마다 반복해야 하며, 예외가 콜백 경계를 넘지 못한다.

### 2단계: 프라미스

프라미스(Promise)는 "아직 없지만 나중에 생길 값"을 나타내는 **객체**다. 상태는 대기(pending), 이행(fulfilled), 거부(rejected) 중 하나이고 한번 정해지면 바뀌지 않는다([Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise)).

콜백을 넘기는 대신 값을 돌려받으므로 조합할 수 있다. `.then()` 체인으로 순차 실행을, `Promise.all()` 로 병행 대기를, `.catch()` 하나로 체인 전체의 오류를 처리한다. Python 의 `asyncio.Future`, Java 의 `CompletableFuture` 가 같은 개념이다.

### 3단계: async/await

`async` 함수는 프라미스(Python 에서는 코루틴 객체)를 돌려주고, 그 안에서 `await` 는 "이 값이 준비될 때까지 이 함수를 일시 정지하고 루프에 양보하라"는 뜻이다. 비동기 코드를 동기 코드처럼 위에서 아래로 쓸 수 있고, 오류는 평범한 `try/catch` 로 잡는다. Python 은 PEP 492 로 `async def`/`await` 문법을 도입했다([PEP 492](https://peps.python.org/pep-0492/)).

중요한 함정 두 가지:
1. **`await` 를 줄줄이 쓰면 순차 실행이다.** 독립적인 작업은 `asyncio.gather` / `Promise.all` 로 묶어야 동시에 기다린다.
2. **async 는 전염된다.** `await` 는 `async` 함수 안에서만 쓸 수 있으므로, 깊은 곳 하나가 비동기가 되면 호출 경로 전체가 `async` 가 된다. 흔히 "함수 색깔 문제"라 부른다.

### 블로킹 작업 다루기

피할 수 없는 동기 I/O 나 CPU 작업은 루프 밖으로 보낸다. Python 은 `asyncio.to_thread()` 로 스레드 풀에 넘기고, CPU 작업은 프로세스 풀을 쓴다([Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)). 시간 제한은 `asyncio.timeout()`(Python 3.11+)으로 건다.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
import asyncio, time

async def fetch(name, delay):
    await asyncio.sleep(delay)          # I/O 대기를 흉내 낸다
    return f"{name} done after {delay}s"

async def main():
    t = time.perf_counter()
    r = [await fetch("a", 1), await fetch("b", 1), await fetch("c", 1)]
    print("sequential", round(time.perf_counter() - t, 1))   # 3.0

    t = time.perf_counter()
    r = await asyncio.gather(fetch("a", 1), fetch("b", 1), fetch("c", 1))
    print("gather    ", round(time.perf_counter() - t, 1))   # 1.0

    async def bad(n):
        time.sleep(1)                   # 블로킹! 루프를 멈춘다
        return n
    t = time.perf_counter()
    await asyncio.gather(bad(1), bad(2), bad(3))
    print("blocking  ", round(time.perf_counter() - t, 1))   # 3.0

    def work(n):
        time.sleep(1); return n
    t = time.perf_counter()
    r = await asyncio.gather(*(asyncio.to_thread(work, i) for i in range(3)))
    print("to_thread ", round(time.perf_counter() - t, 1), r) # 1.0 [0, 1, 2]

    try:
        async with asyncio.timeout(0.5):
            await fetch("slow", 2)
    except TimeoutError:
        print("timeout after 0.5s")

asyncio.run(main())
```

`gather` 로 묶은 세 작업은 1초, `await` 를 줄 세우면 3초, 블로킹 `time.sleep` 을 섞으면 `gather` 를 써도 3초다.

JavaScript 의 실행 순서(Node.js 22):

```javascript
console.log("1 sync start");
setTimeout(() => console.log("5 timeout (macrotask)"), 0);
Promise.resolve().then(() => console.log("3 promise (microtask)"));
queueMicrotask(() => console.log("4 queueMicrotask"));
console.log("2 sync end");
// 출력 순서: 1, 2, 3, 4, 5
```

지연 0 인 `setTimeout` 도 마이크로태스크보다 늦다.

## 현업에서는

- **비동기 서버의 블로킹 호출**: FastAPI 같은 비동기 프레임워크에서 `async def` 핸들러 안에 동기 DB 드라이버나 `requests` 를 쓰면, 부하가 올라갈 때 응답 지연이 계단식으로 늘어난다. 비동기 드라이버를 쓰거나 동기 핸들러(`def`)로 두어 스레드 풀에서 돌게 한다.
- **타임아웃은 필수**: 외부 호출에 시간 제한이 없으면 느린 의존성 하나가 모든 작업을 대기 상태로 묶는다. 쿠버네티스 readiness 프로브가 실패하고 트래픽이 빠지는 장애로 번진다.
- **처리되지 않은 거부**: `await` 하지 않은 프라미스가 거부되면 오류가 사라지거나 프로세스가 종료된다. Node.js 는 처리되지 않은 프라미스 거부에 대해 경고하거나 프로세스를 종료할 수 있다. 백그라운드 작업도 반드시 결과를 수거한다.
- **동시성 제한**: `gather` 에 1만 개 작업을 한꺼번에 넣으면 상대 서버나 커넥션 풀이 버티지 못한다. `asyncio.Semaphore` 로 동시 실행 수를 제한한다.

## 확인 문제

1. 동시성과 병렬성의 차이는? asyncio 는 어느 쪽인가?
2. `async` 함수 안에서 `time.sleep(1)` 을 호출하면 어떤 일이 생기는가?
3. 독립적인 HTTP 요청 세 개를 `await` 세 줄로 쓰면 왜 느린가?
4. JavaScript 에서 `setTimeout(f, 0)` 과 `Promise.resolve().then(g)` 중 어느 것이 먼저 실행되는가?
5. CPU 를 많이 쓰는 계산을 asyncio 프로그램에서 처리하는 방법은?

### 풀이

1. 동시성은 여러 작업의 진행 시간대가 겹치는 것, 병렬성은 같은 순간에 물리적으로 동시에 실행되는 것이다. asyncio 는 한 스레드에서 번갈아 실행하는 동시성이다.
2. 이벤트 루프 스레드가 1초 동안 멈춰 다른 모든 코루틴이 진행하지 못한다. `await asyncio.sleep(1)` 을 써야 한다.
3. 각 `await` 가 앞 요청이 끝날 때까지 다음 요청을 시작하지 않아 순차 실행이 되기 때문이다. `gather` 로 묶어야 한다.
4. `g`. 프라미스 콜백은 마이크로태스크로, 현재 작업이 끝나는 즉시 `setTimeout` 콜백보다 먼저 처리된다.
5. `loop.run_in_executor` 로 `ProcessPoolExecutor` 에 넘긴다. 스레드는 CPython 의 GIL 때문에 CPU 작업 병렬화에 한계가 있다(자유 스레드 빌드 제외).

## 더 읽을거리 (References)

- Python Docs, [asyncio](https://docs.python.org/3/library/asyncio.html), [Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)
- [PEP 492 — Coroutines with async and await syntax](https://peps.python.org/pep-0492/)
- MDN, [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise), [Using promises](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises), [async function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)
- WHATWG, [HTML Standard — Event loops](https://html.spec.whatwg.org/multipage/webappapis.html#event-loops)
