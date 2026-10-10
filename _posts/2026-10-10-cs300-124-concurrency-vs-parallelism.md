---
layout: post
title: "[CS300 #124] 동시성과 병렬성의 차이 — 구조와 실행은 다른 이야기다"
date: 2026-10-10 20:04:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, concurrency, parallelism, python]
---

컴퓨터공학 300 주제 시리즈의 124번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

동시성(concurrency)은 여러 일을 겹쳐서 다룰 수 있게 프로그램을 짜는 구조의 문제이고, 병렬성(parallelism)은 여러 일을 같은 순간에 실제로 실행하는 하드웨어 실행의 문제다. 동시성은 병렬성 없이도 성립하고, 병렬성은 동시적 구조가 있어야 쓸 수 있다.

## 왜 필요한가

"스레드를 늘렸는데 왜 안 빨라지나요?" 는 개발자가 가장 자주 던지는 질문 중 하나다. 답은 대개 이 둘을 섞어서 생각했기 때문이다.

웹 서버가 요청 1만 개를 받는 문제는 대부분 기다림의 문제다. 데이터베이스 응답, 네트워크 왕복을 기다리는 동안 다른 요청을 다루면 된다. 코어가 하나여도 된다. 이건 동시성이다.

이미지 1만 장의 크기를 줄이는 문제는 계산의 문제다. 코어가 8개면 8장을 같은 순간에 처리해야 빨라진다. 이건 병렬성이다.

문제의 성격을 잘못 읽으면 도구를 잘못 고른다. 계산 작업에 비동기 I/O 를 쓰면 하나도 안 빨라지고, I/O 작업에 프로세스를 수천 개 띄우면 메모리만 먹는다.

## 핵심 개념

### 그림으로 보는 차이

```
동시성 (코어 1개, 번갈아 실행)
코어0: A A B B A C C B A C ...      시간 →

병렬성 (코어 2개, 같은 순간 실행)
코어0: A A A A A ...
코어1: B B B B B ...

동시성 + 병렬성 (코어 2개, 작업 3개)
코어0: A A C C A A ...
코어1: B B B C B B ...
```

롭 파이크(Rob Pike)는 2012년 발표 "Concurrency is not Parallelism" 에서 이렇게 정리했다. 동시성은 한꺼번에 많은 일을 *다루는(dealing with)* 것이고, 병렬성은 한꺼번에 많은 일을 *하는(doing)* 것이다. 동시성은 구조, 병렬성은 실행이다.

### 작업의 성격: I/O 바운드와 CPU 바운드

| 성격 | 시간이 어디에 쓰이나 | 효과적인 도구 |
|---|---|---|
| I/O 바운드 | 네트워크·디스크 대기 | 스레드, 비동기(이벤트 루프) |
| CPU 바운드 | 계산 | 여러 코어에서 병렬 실행(프로세스, 네이티브 스레드) |

### 암달의 법칙

병렬화할 수 없는 부분이 전체의 비율 s 라면, 코어 N 개로 얻을 수 있는 속도 향상은 최대 1 / (s + (1-s)/N) 이다. N 이 무한대로 가도 1/s 를 넘지 못한다. 순차 부분이 10%면 코어를 아무리 늘려도 10배가 한계다. 병렬화 전에 순차 구간부터 찾아야 하는 이유다.

### 파이썬과 GIL

CPython 은 오랫동안 전역 인터프리터 락(GIL)이 있어서 한 순간에 한 스레드만 파이썬 바이트코드를 실행했다. 그래서 스레드는 I/O 바운드 작업(대기 중에 GIL 을 놓는다)에는 효과가 있지만 순수 파이썬 계산에는 병렬 효과가 없다. 계산 병렬화는 `multiprocessing` 이나 `ProcessPoolExecutor` 로 프로세스를 나눠야 했다. Python 3.13 부터는 GIL 을 끈 실험적 free-threaded 빌드가 따로 제공되지만, 기본 빌드는 여전히 GIL 이 있다.

### 동시성이 부르는 문제

여러 흐름이 같은 데이터를 건드리면 실행 순서에 따라 결과가 달라진다. 경쟁 상태(race condition), 교착 상태(deadlock), 기아(starvation)가 여기서 생긴다. 병렬성이 없어도(코어 1개여도) 문맥 교환 때문에 경쟁 상태는 생긴다. 반대로 공유 상태가 없으면 병렬 실행은 안전하다. 그래서 병렬 처리 설계의 첫 원칙은 "공유하지 마라" 다.

## 직접 해 보기

같은 도구(스레드·프로세스)를 두 종류 작업에 써 보고 시간을 잰다.

```python
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def io_task(_):
    time.sleep(0.2)                  # 네트워크 대기 흉내
def cpu_task(_):
    return sum(i * i for i in range(2_000_000))

def bench(executor_cls, fn, n=8):
    t = time.perf_counter()
    with executor_cls(max_workers=4) as ex:
        list(ex.map(fn, range(n)))
    return time.perf_counter() - t

if __name__ == "__main__":
    t = time.perf_counter(); [io_task(i) for i in range(8)]
    print(f"I/O  순차     {time.perf_counter()-t:.2f}s")
    print(f"I/O  스레드4  {bench(ThreadPoolExecutor, io_task):.2f}s")
    t = time.perf_counter(); [cpu_task(i) for i in range(8)]
    print(f"CPU  순차     {time.perf_counter()-t:.2f}s")
    print(f"CPU  스레드4  {bench(ThreadPoolExecutor, cpu_task):.2f}s")
    print(f"CPU  프로세스4 {bench(ProcessPoolExecutor, cpu_task):.2f}s")
```

논리 코어 4개(물리 2코어) 노트북 서버, Python 3.12 에서 돌린 결과다(숫자는 기계마다 다르다).

```
I/O  순차     1.60s
I/O  스레드4  0.41s
CPU  순차     3.39s
CPU  스레드4  4.01s
CPU  프로세스4 1.91s
```

I/O 작업은 스레드 4개로 4배 빨라진다. 기다림이 겹쳤을 뿐 계산은 거의 없다. CPU 작업은 스레드로는 전혀 안 빨라지고 오히려 조금 느려진다(GIL 과 문맥 교환 비용). 프로세스로 나눠야 빨라진다. 다만 물리 코어가 2개라 4프로세스를 써도 2배에 못 미친다. 하이퍼스레딩의 논리 코어는 물리 코어 하나만큼의 계산력을 주지 않는다.

## 현업에서는

- **웹 서버 구성.** 파이썬 웹 서비스는 흔히 "프로세스 여러 개 × 프로세스마다 스레드나 이벤트 루프" 로 띄운다. 프로세스는 코어를 채우는 병렬성, 그 안의 스레드·비동기는 대기를 겹치는 동시성 담당이다.
- **쿠버네티스 CPU 한도.** 컨테이너에 CPU limit 1 을 주고 워커를 8개 띄우면, 동시성은 8이지만 병렬성은 1코어어치다. CFS 쿼터에 걸려 지연이 튀는 현상(throttling)이 생긴다. 워커 수는 limit 과 작업 성격을 같이 보고 정한다.
- **배치 작업.** 수천 개 파일을 처리하는 작업은 먼저 I/O 와 CPU 비중을 재 본다. `time` 명령의 real·user·sys 를 비교하면 감이 온다. real 이 user+sys 보다 훨씬 길면 대기가 많은 작업이다.
- **분산으로 확장.** 한 기계의 코어를 다 쓰고도 부족하면 여러 기계로 나눈다. 이때도 같은 질문을 한다. 무엇을 나눌 수 있고, 무엇이 순차인가. 이 질문은 마지막 글인 MapReduce 까지 이어진다.

## 확인 문제

1. 코어가 하나뿐인 기계에서 동시성은 가능한가? 병렬성은?
2. 순차 부분이 25%인 프로그램을 코어 4개로 돌릴 때 암달의 법칙에 따른 최대 속도 향상은?
3. CPython 기본 빌드에서 CPU 바운드 작업을 스레드로 나누면 왜 빨라지지 않는가?
4. 공유 상태가 전혀 없는 병렬 작업에서도 경쟁 상태가 생길 수 있는가?

### 풀이

1. 동시성은 가능하다(시분할로 번갈아 실행). 병렬성은 불가능하다(같은 순간 하나만 실행).
2. 1 / (0.25 + 0.75/4) = 1 / 0.4375 ≈ 2.29배.
3. GIL 때문에 한 순간에 한 스레드만 바이트코드를 실행하므로 계산이 겹치지 않는다.
4. 메모리 공유가 없으면 그 데이터에 대해서는 생기지 않는다. 다만 파일·데이터베이스 같은 외부 자원을 함께 쓰면 그 자원에서 경쟁이 생길 수 있다.

## 더 읽을거리 (References)

- [Rob Pike, Concurrency is not Parallelism — The Go Blog](https://go.dev/blog/waza-talk)
- [concurrent.futures — Python 공식 문서](https://docs.python.org/3/library/concurrent.futures.html)
- [threading — Python 공식 문서 (GIL 관련 설명 포함)](https://docs.python.org/3/library/threading.html)
- Gene M. Amdahl, "Validity of the single processor approach to achieving large scale computing capabilities", AFIPS Spring Joint Computer Conference, 1967.
