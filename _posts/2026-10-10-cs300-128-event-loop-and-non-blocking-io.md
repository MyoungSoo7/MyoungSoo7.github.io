---
layout: post
title: "[CS300 #128] 이벤트 루프와 논블로킹 I/O — 스레드 하나로 만 개의 연결을 다루는 법"
date: 2026-10-10 20:08:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, event-loop, epoll, asyncio, non-blocking-io]
---

컴퓨터공학 300 주제 시리즈의 128번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

논블로킹 I/O 는 "지금 당장 할 수 없으면 기다리지 말고 바로 돌아와라" 는 방식이고, 이벤트 루프는 커널에 "준비된 fd 를 알려 달라" 고 묻고(epoll·kqueue), 준비된 것만 처리하기를 반복하는 단일 스레드 루프다. 대기를 스레드가 아니라 루프가 관리하므로 적은 자원으로 아주 많은 연결을 다룬다.

## 왜 필요한가

연결 하나에 스레드 하나를 붙이는 서버는 이해하기 쉽다. `read` 가 블록되면 그 스레드만 잠든다. 그런데 연결이 1만 개가 되면 스레드도 1만 개다. 스레드마다 스택 메모리가 있고, 대부분은 아무 일도 하지 않고 데이터를 기다리며 잠들어 있다. 흔히 "C10K 문제" 로 불린 이 한계가 이벤트 기반 서버를 대중화했다.

관찰은 단순하다. 연결 대부분은 대부분의 시간 동안 놀고 있다. 그렇다면 "지금 읽을 데이터가 있는 연결" 만 골라서 처리하면 스레드 하나로도 충분하다. nginx, Redis, Node.js, 파이썬 asyncio 가 모두 이 구조다.

## 핵심 개념

### 블로킹과 논블로킹

| 모드 | `read()` 를 불렀는데 데이터가 없으면 |
|---|---|
| 블로킹(기본) | 데이터가 올 때까지 스레드가 잠든다 |
| 논블로킹(`O_NONBLOCK`) | 즉시 -1 을 반환하고 `errno = EAGAIN` |

논블로킹만으로는 부족하다. 계속 `read` 를 시도하며 바쁘게 돌면 CPU 만 탄다. 필요한 것은 "어느 fd 가 준비됐는지" 를 한꺼번에 기다리는 방법이다.

### I/O 다중화: select → poll → epoll

- `select`: fd 집합을 넘기고 준비된 것을 받는다. 매번 전체 집합을 넘기고 전부 훑는다. fd 수 상한(`FD_SETSIZE`)이 있다.
- `poll`: 상한은 없앴지만 여전히 매번 전체를 넘기고 훑는다. 연결 수에 비례하는 비용.
- `epoll`(Linux): 관심 목록을 커널에 한 번 등록해 두고, `epoll_wait` 는 준비된 fd 만 돌려준다. 준비된 수에 비례하는 비용이라 연결이 많아도 효율적이다. BSD·macOS 의 `kqueue` 가 같은 역할이다.

epoll 에는 두 가지 통지 방식이 있다.

| 방식 | 의미 | 주의 |
|---|---|---|
| 레벨 트리거(기본) | 읽을 데이터가 남아 있는 동안 계속 알린다 | 단순하고 안전 |
| 엣지 트리거(`EPOLLET`) | 상태가 바뀌는 순간 한 번 알린다 | `EAGAIN` 이 날 때까지 다 읽어야 한다. 안 그러면 남은 데이터를 영영 못 받는다 |

### 이벤트 루프의 뼈대

```
등록: 리슨 소켓 → "읽기 가능하면 accept 콜백"
loop:
    timeout = 가장 가까운 타이머까지 남은 시간
    events = epoll_wait(timeout)
    for fd, ev in events:
        콜백 실행 (accept / read / write)   ← 절대 블록하면 안 된다
    만료된 타이머 콜백 실행
```

콜백이 블록하지 않고 짧게 끝나는 한, 루프는 빠르게 다음 이벤트로 넘어간다. 이 계약이 이벤트 루프의 전부다.

### 콜백에서 코루틴으로

콜백만으로 짜면 "읽고 → 데이터베이스 조회하고 → 쓰기" 같은 흐름이 콜백 안의 콜백으로 쪼개진다. 그래서 언어들이 `async/await` 를 도입했다. 코루틴은 `await` 지점에서 실행을 멈추고 루프에 제어를 넘겼다가, 기다리던 이벤트가 오면 그 자리부터 다시 이어진다. 겉보기에는 순차 코드인데 실제로는 이벤트 루프 위에서 돈다.

### 가장 중요한 규칙: 루프를 막지 마라

이벤트 루프는 스레드 하나다. 한 콜백이 0.1초 블록하면 그동안 모든 연결이 멈춘다. 흔한 범인은 다음과 같다.

- 블로킹 라이브러리 호출(동기 HTTP 클라이언트, 동기 DB 드라이버, `time.sleep`)
- 무거운 계산(JSON 대용량 파싱, 암호화, 이미지 처리)
- 동기 파일 I/O(대부분의 OS 에서 일반 파일은 epoll 로 기다릴 수 없다)

대책은 이런 일을 스레드 풀이나 프로세스 풀로 보내는 것이다. 파이썬은 `asyncio.to_thread` 나 `loop.run_in_executor`, Node.js 는 내부적으로 libuv 스레드 풀이 파일 I/O 등을 맡는다.

### 장단점

| 장점 | 단점 |
|---|---|
| 연결 수 대비 메모리·문맥 교환이 적다 | 한 곳의 블로킹이 전체를 멈춘다 |
| 공유 상태 접근이 단일 스레드라 락이 거의 필요 없다 | 기본적으로 코어 하나만 쓴다 |
| 대기 위주 작업에 매우 효율적 | CPU 바운드에는 이득이 없다 |

코어를 다 쓰려면 이벤트 루프를 코어 수만큼 띄운다. nginx 의 워커 프로세스가 그렇다.

## 직접 해 보기

asyncio 에서 논블로킹 대기와 블로킹 호출이 루프에 미치는 영향을 비교한다. 별도의 하트비트 태스크가 10ms 마다 깨어나며, 루프가 얼마나 오래 막혔는지 잰다.

```python
import asyncio, time

async def good(i):
    await asyncio.sleep(0.1)           # 기다리는 동안 루프에 제어를 돌려준다

async def bad(i):
    time.sleep(0.1)                    # 블로킹 호출: 루프 전체가 멈춘다

async def heartbeat(stop):
    gaps, last = [], time.perf_counter()
    while not stop.is_set():
        await asyncio.sleep(0.01)
        now = time.perf_counter(); gaps.append(now - last); last = now
    return max(gaps)

async def run(fn, n):
    stop = asyncio.Event()
    hb = asyncio.create_task(heartbeat(stop))
    t = time.perf_counter()
    await asyncio.gather(*(fn(i) for i in range(n)))
    elapsed = time.perf_counter() - t
    stop.set()
    return elapsed, await hb

for fn, n in ((good, 1000), (bad, 10)):
    elapsed, worst = asyncio.run(run(fn, n))
    print(f"{fn.__name__:4} x{n:<4} 전체 {elapsed:.2f}s, 하트비트 최대 간격 {worst*1000:.0f}ms")
```

Python 3.12 에서의 결과다.

```
good x1000 전체 0.12s, 하트비트 최대 간격 17ms
bad  x10   전체 1.01s, 하트비트 최대 간격 1012ms
```

0.1초 대기 1000개가 0.12초에 끝난다. 스레드는 하나뿐이다. 반면 `time.sleep` 을 쓴 10개는 차례로 실행되어 1초가 걸리고, 그동안 하트비트가 한 번도 돌지 못했다. 서버였다면 1초 동안 모든 클라이언트가 응답을 못 받은 것이다. `bad` 안의 `time.sleep(0.1)` 을 `await asyncio.to_thread(time.sleep, 0.1)` 로 바꾸면 이 기계에서 전체 0.21초, 하트비트 최대 간격 11ms 로 바뀐다. 블로킹 호출이 기본 스레드 풀(이 기계에서 워커 8개)로 넘어가 루프는 계속 돈다. 10개가 8개 워커를 두 번에 나눠 쓰므로 0.2초가 걸린다.

## 현업에서는

- **nginx, Redis.** nginx 는 워커 프로세스마다 이벤트 루프를 하나씩 돌린다. Redis 는 명령 실행을 기본적으로 한 스레드에서 처리하므로, `KEYS *` 같은 무거운 명령 하나가 그동안 모든 클라이언트를 세운다. 운영 문서가 대형 키 순회 명령을 경계하는 이유다.
- **Node.js 서비스의 지연 스파이크.** 큰 JSON 을 동기로 파싱하거나 동기 암호화 함수를 쓰면 이벤트 루프 지연(event loop lag)이 튄다. 이 지연을 지표로 수집해 대시보드에 두는 경우가 많다.
- **파이썬 비동기 서버.** FastAPI 같은 ASGI 프레임워크에서 `async def` 핸들러 안에 동기 DB 드라이버를 쓰면 위 실험의 `bad` 와 똑같아진다. 동기 코드는 `def` 핸들러(프레임워크가 스레드 풀로 보낸다)로 두거나 비동기 드라이버를 쓴다.
- **쿠버네티스 헬스체크.** 이벤트 루프가 막히면 liveness 프로브 응답도 늦어져, 일시적 부하가 재시작으로 번질 수 있다. 프로브 타임아웃을 너무 빡빡하게 잡지 않는 이유 중 하나다.

## 확인 문제

1. `select`/`poll` 대비 `epoll` 이 연결 수가 많을 때 유리한 이유는?
2. 엣지 트리거 모드에서 읽기 이벤트를 받았을 때 반드시 해야 하는 일은?
3. 이벤트 루프 서버에서 콜백 하나가 200ms 걸리는 계산을 하면 어떤 일이 생기는가? 대책은?
4. 이벤트 루프 하나로 8코어 서버의 CPU 를 다 쓸 수 있는가?

### 풀이

1. 관심 목록을 커널에 한 번만 등록하고, `epoll_wait` 는 준비된 fd 만 돌려주므로 비용이 전체 연결 수가 아니라 준비된 수에 비례한다.
2. `EAGAIN` 이 날 때까지 데이터를 끝까지 읽어야 한다. 그렇지 않으면 남은 데이터에 대한 알림이 다시 오지 않는다.
3. 그 200ms 동안 모든 연결의 처리가 멈춘다. 계산을 스레드 풀·프로세스 풀로 넘기거나 작게 쪼갠다.
4. 없다. 루프는 한 스레드에서 돌므로 코어 하나만 쓴다. 루프를 코어 수만큼(프로세스나 스레드로) 띄워야 한다.

## 더 읽을거리 (References)

- [Event Loop — Python asyncio 공식 문서](https://docs.python.org/3/library/asyncio-eventloop.html)
- [selectors — Python 공식 문서](https://docs.python.org/3/library/selectors.html)
- [The Node.js Event Loop — Node.js 공식 문서](https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick)
- [epoll(7) — Linux man-pages (man.archlinux.org)](https://man.archlinux.org/man/epoll.7)
