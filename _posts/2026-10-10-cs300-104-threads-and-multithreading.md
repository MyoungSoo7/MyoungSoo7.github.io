---
layout: post
title: "[CS300 #104] 스레드와 멀티스레딩 — 주소 공간을 함께 쓰는 실행 흐름"
date: 2026-10-10 19:44:00 +0900
categories: [cs]
tags: [cs300, operating-systems, thread, concurrency, gil]
---

컴퓨터공학 300 주제 시리즈의 104번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

스레드는 한 프로세스 안에서 주소 공간과 열린 파일을 공유하면서 각자의 레지스터와 스택만 따로 가지는 실행 흐름이며, 싸게 만들고 쉽게 데이터를 나누는 대신 동기화 책임을 프로그래머에게 넘긴다.

## 왜 필요한가

웹 서버가 요청 하나를 처리하는 동안 디스크를 기다린다고 해 보자. 프로세스가 하나뿐이면 그동안 다른 요청은 모두 줄을 선다. 요청마다 프로세스를 하나씩 만들면 해결되지만 비용이 크다. 주소 공간을 새로 만들고, 프로세스끼리 데이터를 나누려면 파이프나 공유 메모리 같은 별도 장치가 필요하다.

스레드는 이 중간 지점이다.

- **같은 메모리를 본다**: 전역 변수, 힙 객체를 그냥 함께 쓴다. 캐시나 연결 풀을 공유하기 쉽다.
- **생성과 전환이 상대적으로 싸다**: 주소 공간을 새로 만들지 않고, 같은 프로세스 안 스레드 간 전환은 페이지 테이블을 바꾸지 않는다.
- **멀티코어 활용**: 여러 스레드가 서로 다른 코어에서 동시에 실행될 수 있다.

대가는 분명하다. 같은 메모리를 동시에 건드리므로 경쟁 상태가 생긴다. 이 문제는 다음 글들(107~109)에서 다룬다.

## 핵심 개념

### 무엇을 공유하고 무엇을 따로 갖나

| 공유 (프로세스 단위) | 스레드마다 따로 |
|---|---|
| 코드, 전역 데이터, 힙 | 프로그램 카운터, 레지스터 |
| 열린 파일 디스크립터 | 스택(지역 변수, 호출 프레임) |
| 현재 디렉터리, 사용자 ID | 스레드 ID(TID) |
| 시그널 처리기 설정 | 시그널 마스크, errno |

```
 프로세스 (PID 100)
 +------------------------------------------------+
 |  코드 | 전역 데이터 | 힙 | 열린 파일 표          |
 |                                                |
 |  [스레드 A]       [스레드 B]       [스레드 C]   |
 |   PC, 레지스터     PC, 레지스터     PC, 레지스터 |
 |   스택 A          스택 B          스택 C        |
 +------------------------------------------------+
```

### 리눅스는 스레드를 어떻게 만드나

리눅스 커널은 프로세스와 스레드를 따로 구분하지 않고 모두 **task** 로 다룬다. 차이는 `clone()` 시스템 콜에 무엇을 공유할지 플래그로 알려 주는 것뿐이다. `CLONE_VM`(주소 공간), `CLONE_FILES`(파일 표), `CLONE_SIGHAND`(시그널 처리기), `CLONE_THREAD`(같은 스레드 그룹) 등을 켜면 스레드, 대부분 끄면 별도 프로세스가 된다.

그래서 리눅스에서 "PID" 라고 부르는 것은 사실 **스레드 그룹 ID(TGID)** 이고, 스레드마다 고유한 TID 가 따로 있다. `/proc/PID/task/` 아래에 TID 별 디렉터리가 있다. 사용자 공간의 POSIX 스레드(pthreads) 구현인 glibc 의 NPTL 은 스레드 하나를 커널 task 하나에 대응시키는 **1:1 모델**이다(`pthreads(7)` 참고).

### 스레딩 모델

| 모델 | 설명 | 예 |
|---|---|---|
| 1:1 | 사용자 스레드 하나 = 커널 스레드 하나 | Linux NPTL, Java 플랫폼 스레드 |
| N:1 | 여러 사용자 스레드를 커널 스레드 하나에 | 초기 그린 스레드 |
| M:N | M 개 사용자 스레드를 N 개 커널 스레드에 다중화 | Go 고루틴, Java 21 가상 스레드 |

M:N 모델은 런타임이 자체 스케줄러를 가지고 블로킹 지점에서 다른 작업으로 갈아탄다. 수십만 개의 동시 작업을 적은 커널 스레드로 처리할 수 있다.

### 파이썬의 특수 사정: GIL

CPython 은 오랫동안 **GIL(Global Interpreter Lock)** 을 가졌다. 한 시점에 한 스레드만 파이썬 바이트코드를 실행한다. 따라서

- I/O 대기(`sleep`, 소켓, 파일)는 GIL 을 놓으므로 스레드로 잘 겹쳐진다.
- 순수 파이썬 계산은 스레드를 늘려도 빨라지지 않는다. 멀티코어를 쓰려면 `multiprocessing` 이나 GIL 을 놓는 C 확장(NumPy 등)을 써야 한다.

PEP 703 에 따라 CPython 3.13 부터 GIL 없는 빌드(free-threaded build)가 실험적으로 제공된다. 일반 배포판 빌드는 여전히 GIL 이 켜져 있다.

### 동시성과 병렬성

- **동시성(concurrency)**: 여러 작업이 진행 중인 상태. 코어 하나에서 번갈아 실행해도 된다.
- **병렬성(parallelism)**: 여러 작업이 물리적으로 같은 순간에 실행된다. 코어가 여럿 필요하다.

GIL 아래의 파이썬 스레드는 동시성은 있지만 계산 병렬성은 없다.

## 직접 해 보기

스레드가 메모리를 공유하고 각자 TID 를 가지는 것, 그리고 GIL 의 영향을 함께 확인한다.

```python
import os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

shared = []
def worker(i):
    shared.append((i, threading.get_native_id()))   # 같은 리스트를 함께 본다
    time.sleep(0.5)

ts = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
for t in ts: t.start()
time.sleep(0.1)
print("PID:", os.getpid(), " /proc/self/task:", sorted(os.listdir("/proc/self/task")))
for t in ts: t.join()
print("공유 리스트:", shared)

def cpu(n=4_000_000):
    s = 0
    for i in range(n): s += i
    return s
def io(_=None):
    time.sleep(0.5)

def timeit(label, pool_cls, fn, k=4):
    t = time.perf_counter()
    with pool_cls(max_workers=k) as ex:
        list(ex.map(fn, [None]*k if fn is io else [4_000_000]*k))
    print(f"{label:24s} {time.perf_counter()-t:5.2f}s")

if __name__ == "__main__":
    print("GIL 활성:", getattr(sys, "_is_gil_enabled", lambda: True)())
    t = time.perf_counter(); cpu(); print(f"{'CPU 작업 1개(기준)':24s} {time.perf_counter()-t:5.2f}s")
    timeit("CPU x4, 스레드 4개", ThreadPoolExecutor, cpu)
    timeit("CPU x4, 프로세스 4개", ProcessPoolExecutor, cpu)
    timeit("I/O x4, 스레드 4개", ThreadPoolExecutor, io)
```

4코어 리눅스, Python 3.12 에서의 결과다.

```
PID: 1168199  /proc/self/task: ['1168199', '1168200', '1168201', '1168202']
공유 리스트: [(0, 1168200), (1, 1168201), (2, 1168202)]
GIL 활성: True
CPU 작업 1개(기준)             0.55s
CPU x4, 스레드 4개            2.08s
CPU x4, 프로세스 4개           1.07s
I/O x4, 스레드 4개            0.50s
```

읽는 법은 이렇다.

- `/proc/self/task` 에 메인 스레드(TID = PID)와 스레드 3개가 보인다. 각 스레드가 `shared` 리스트에 직접 쓴 결과가 그대로 남는다.
- CPU 작업 4개를 스레드로 돌리면 기준의 약 4배(2.08s)다. GIL 때문에 사실상 직렬이다.
- 프로세스 4개는 코어를 나눠 쓰므로 빨라진다. 4코어인데 정확히 0.55s 가 아닌 것은 프로세스 생성 비용과 다른 부하 때문이다.
- I/O 대기 4개는 스레드로 완벽히 겹쳐져 0.5초에 끝난다.

## 현업에서는

- **스레드 수 = 메모리**: 스레드마다 스택이 필요하다. 리눅스 glibc 의 기본 스택 크기는 보통 `ulimit -s` 값(흔히 8MB)을 따르며, 이는 가상 주소 예약이라 실제 사용량만큼만 물리 메모리를 쓴다. 그래도 스레드 수천 개는 커널 자료구조와 전환 비용을 키운다. 요청당 스레드 모델의 서버가 스레드 풀 크기를 제한하는 이유다.
- **쿠버네티스 CPU limit 과 스레드 수**: 컨테이너 CPU limit 이 1 코어인데 런타임이 노드 전체 코어 수만큼 스레드를 만들면 CFS 쿼터를 금방 소진해 스로틀링이 생긴다. JVM, Go 런타임 등은 cgroup 의 CPU 제한을 읽어 스레드 수를 맞추는 기능을 가지고 있으니 버전별 동작을 확인해야 한다.
- **스레드 덤프**: 자바의 `jstack`, 파이썬의 `py-spy dump` 는 스레드별 스택을 보여 준다. 응답이 멈춘 서비스에서 모든 스레드가 같은 락을 기다리고 있는지 확인하는 첫 단계다.
- **`top -H`**: 스레드 단위로 CPU 사용률을 볼 수 있다. 프로세스 CPU 가 100% 일 때 어느 스레드가 범인인지 찾는다.

## 확인 문제

1. 같은 프로세스의 두 스레드가 공유하지 않는 것 두 가지를 들어라.
2. 리눅스에서 스레드와 프로세스를 만드는 시스템 콜은 무엇이고, 둘의 차이는 무엇으로 결정되는가?
3. CPython(GIL 활성)에서 CPU 집약 작업을 스레드 8개로 나누면 빨라지는가? I/O 집약 작업은?
4. 동시성과 병렬성의 차이를 예를 들어 설명하라.

### 풀이

1. 스택, 레지스터(프로그램 카운터 포함). 그 밖에 TID, 시그널 마스크, errno 도 스레드별이다.
2. 둘 다 `clone()` 계열이다. 주소 공간·파일 표·시그널 처리기 등을 공유하는 플래그(`CLONE_VM`, `CLONE_THREAD` 등)를 켜면 스레드, 끄면 프로세스가 된다.
3. CPU 집약 작업은 GIL 때문에 빨라지지 않고 오히려 전환 비용으로 느려질 수 있다. I/O 대기는 GIL 을 놓으므로 겹쳐져 빨라진다.
4. 코어 하나에서 두 작업을 번갈아 실행하면 동시성은 있지만 병렬성은 없다. 코어 두 개에서 두 작업이 같은 순간 실행되면 병렬성이 있다.

## 더 읽을거리 (References)

- OSTEP, [Concurrency: An Introduction (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-intro.pdf)
- Linux man-pages, [pthreads(7)](https://manpages.debian.org/bookworm/manpages/pthreads.7.en.html), [clone(2)](https://manpages.debian.org/bookworm/manpages-dev/clone.2.en.html)
- Python 문서, [threading](https://docs.python.org/3/library/threading.html), [Python support for free threading](https://docs.python.org/3/howto/free-threading-python.html)
- [PEP 703 — Making the Global Interpreter Lock Optional in CPython](https://peps.python.org/pep-0703/)
