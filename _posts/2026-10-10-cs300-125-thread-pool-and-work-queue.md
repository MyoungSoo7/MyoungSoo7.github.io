---
layout: post
title: "[CS300 #125] 스레드 풀과 작업 큐 — 일꾼은 미리 뽑고 일은 줄 세운다"
date: 2026-10-10 20:05:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, thread-pool, queue, backpressure]
---

컴퓨터공학 300 주제 시리즈의 125번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

스레드 풀은 정해진 수의 작업자 스레드를 미리 만들어 두고, 작업 큐에 쌓인 일을 하나씩 꺼내 처리하게 하는 구조다. 스레드 생성 비용을 아끼고, 동시에 실행되는 일의 수에 상한을 걸어 시스템을 보호한다.

## 왜 필요한가

요청이 올 때마다 스레드를 하나씩 새로 만드는 서버를 생각해 보자. 평소에는 잘 돈다. 그런데 트래픽이 10배로 튀면 스레드도 10배가 된다. 스레드마다 스택 메모리가 잡히고, 스케줄러는 수천 개 스레드 사이를 오가느라 바빠지고, 데이터베이스 커넥션은 바닥난다. 결국 모든 요청이 느려지고 서버가 죽는다.

스레드 풀은 이 문제를 두 가지로 푼다.

1. **재사용.** 스레드를 만들고 없애는 비용을 한 번만 낸다.
2. **상한.** 동시에 일하는 스레드 수를 고정한다. 넘치는 일은 큐에서 기다린다. 큐도 상한을 두면, 감당할 수 없는 일은 빨리 거절할 수 있다.

두 번째가 더 중요하다. 과부하에서 무너지지 않고 "느려지거나 거절하는" 시스템을 만드는 것이 스레드 풀의 진짜 역할이다.

## 핵심 개념

### 구조

```
 제출자들 ──submit──►  [ 작업 큐 ]  ──take──►  워커1
                       t5 t4 t3 t2            워커2
                                              워커3   (고정 N 개)
                                    ◄──결과(Future)──
```

- **작업 큐**: 생산자-소비자 큐. 보통 스레드 안전한 블로킹 큐다.
- **워커**: 무한 루프로 큐에서 일을 꺼내 실행한다.
- **Future**: 제출한 일의 결과를 나중에 받을 수 있는 핸들. 완료 여부, 결과, 예외를 담는다.

### 풀 크기 정하기

정답 공식은 없지만 출발점은 있다.

- **CPU 바운드**: 코어 수 근처. 더 늘려도 문맥 교환만 늘어난다.
- **I/O 바운드**: 코어 수 × (1 + 대기 시간 / 계산 시간) 정도에서 시작해 측정으로 조정한다. 대기 비율이 높을수록 스레드를 더 둔다.
- **하류 자원**: 워커가 데이터베이스 커넥션을 하나씩 쓴다면, 커넥션 풀 크기보다 크게 잡아 봐야 대기만 늘어난다.

파이썬 `ThreadPoolExecutor` 의 기본 `max_workers` 는 3.8 부터 `min(32, os.cpu_count() + 4)` 다. I/O 바운드 용도를 가정한 값이다.

### 큐의 크기와 역압

큐 길이를 무한으로 두면 과부하 때 메모리가 끝없이 늘고, 큐 뒤쪽 일은 처리될 무렵이면 이미 클라이언트가 포기한 뒤다. 쓸모없는 일을 열심히 하는 상태가 된다.

유한 큐를 쓰면 가득 찼을 때 무엇을 할지 정해야 한다. 자바 `ThreadPoolExecutor` 는 이를 거부 정책(RejectedExecutionHandler)으로 명시한다.

| 정책 | 동작 | 효과 |
|---|---|---|
| Abort | 예외를 던진다 | 호출자가 즉시 실패를 안다 |
| CallerRuns | 제출한 스레드가 직접 실행 | 제출 속도가 자연히 느려진다(역압) |
| Discard | 조용히 버린다 | 위험. 유실을 아무도 모른다 |
| DiscardOldest | 가장 오래된 일을 버린다 | 최신 데이터가 중요할 때 |

파이썬 `ThreadPoolExecutor` 의 내부 큐는 무한이다. 상한이 필요하면 세마포어로 제출 수를 제한하거나 `queue.Queue(maxsize=N)` 로 직접 짠다.

### 함정

- **풀 안에서 풀을 기다리기.** 워커가 같은 풀에 하위 작업을 넣고 그 결과를 기다리면, 모든 워커가 기다리는 순간 교착이 된다. 의존 관계가 있는 작업은 풀을 나누거나 비동기로 연결한다.
- **예외 삼키기.** Future 의 결과를 꺼내지 않으면 워커에서 난 예외가 아무 데도 기록되지 않는다.
- **긴 작업과 짧은 작업 섞기.** 긴 작업이 워커를 다 차지하면 짧은 작업이 줄줄이 막힌다(head-of-line blocking). 성격별로 풀을 나누는 것을 벌크헤드(bulkhead) 패턴이라 한다.
- **종료.** 풀을 닫을 때 큐에 남은 일을 끝낼지 버릴지 정해야 한다. 앞 글의 `SIGTERM` 처리와 맞물린다.

## 직접 해 보기

유한 큐와 고정 워커로 작은 스레드 풀을 직접 만든다.

```python
import queue, threading, time

class TinyPool:
    def __init__(self, workers, maxsize):
        self.q = queue.Queue(maxsize=maxsize)
        self.threads = [threading.Thread(target=self._run, daemon=True)
                        for _ in range(workers)]
        for t in self.threads: t.start()

    def _run(self):
        while True:
            fn, arg = self.q.get()
            if fn is None:                 # 종료 신호
                self.q.task_done(); return
            try: fn(arg)
            finally: self.q.task_done()

    def submit(self, fn, arg):
        self.q.put_nowait((fn, arg))       # 가득 차면 queue.Full -> 거절

    def shutdown(self):
        for _ in self.threads: self.q.put((None, None))
        for t in self.threads: t.join()

def job(i):
    time.sleep(0.1)

pool = TinyPool(workers=3, maxsize=5)
accepted = rejected = 0
for i in range(20):                        # 한꺼번에 20개를 몰아 넣는다
    try: pool.submit(job, i); accepted += 1
    except queue.Full: rejected += 1
pool.q.join(); pool.shutdown()
print("accepted", accepted, "rejected", rejected)
```

출력은 `accepted 5 rejected 15` 에서 `accepted 8 rejected 12` 사이다. 실제로 돌려 보면 제출 루프가 워커보다 빨라서 앞쪽이 자주 나온다. 워커가 아직 일을 꺼내 가지 못했으면 큐 크기 5개만 받고, 워커 3개가 하나씩 꺼내 갔다면 최대 8개까지 받는다. 그 이상은 즉시 거절된다. 무한 큐였다면 20개를 모두 받아 놓고 마지막 일은 0.6초 뒤에야 시작했을 것이다. 어느 쪽이 맞는지는 요구사항이 정하지만, 상한이 있어야 선택할 수 있다.

## 현업에서는

- **웹 서버.** Tomcat 같은 서블릿 컨테이너는 요청 처리 스레드 풀의 최대 크기와 대기 큐 길이를 설정으로 둔다. 둘 다 넘으면 연결을 거절한다. 이 값은 데이터베이스 커넥션 풀 크기와 함께 맞춰야 한다.
- **분산 작업 큐.** Celery, Sidekiq, 쿠버네티스 Job 등은 같은 구조를 기계 여러 대로 늘린 것이다. 큐가 Redis·RabbitMQ·Kafka 로 바뀌고 워커가 파드로 바뀔 뿐이다. 큐 길이를 지표로 워커 파드 수를 늘리는 오토스케일링(KEDA 등)도 흔하다.
- **관측.** 풀에서 볼 지표는 활성 워커 수, 큐 길이, 대기 시간, 거절 횟수다. 큐 길이가 계속 늘면 처리량이 유입량보다 적다는 뜻이고, 워커를 늘리거나 유입을 줄여야 한다.
- **Go 와 가상 스레드.** 고루틴이나 자바 21 의 가상 스레드처럼 아주 가벼운 실행 단위가 있으면 "생성 비용" 문제는 줄어든다. 그래도 하류 자원 보호를 위한 동시성 상한은 여전히 필요하다. 세마포어가 그 역할을 맡는다.

## 확인 문제

1. 스레드 풀이 주는 두 가지 이점은?
2. 작업 큐를 무한 길이로 두면 과부하에서 어떤 일이 생기는가?
3. CallerRuns 거부 정책이 역압을 만드는 원리는?
4. 워커 4개짜리 풀에서 각 워커가 같은 풀에 하위 작업을 제출하고 결과를 기다린다. 무엇이 문제인가?

### 풀이

1. 스레드 생성·소멸 비용의 재사용, 동시 실행 수의 상한(과부하 보호).
2. 메모리가 계속 늘고 대기 시간이 길어져, 처리할 즈음엔 이미 의미 없는 일을 하게 된다. 결국 메모리 부족으로 죽을 수 있다.
3. 큐가 차면 제출한 스레드가 직접 일을 하게 되어, 그동안 새 일을 제출하지 못한다. 생산 속도가 소비 속도에 맞춰진다.
4. 네 워커가 모두 결과를 기다리면 하위 작업을 실행할 워커가 없어 교착에 빠진다.

## 더 읽을거리 (References)

- [concurrent.futures — Python 공식 문서](https://docs.python.org/3/library/concurrent.futures.html)
- [queue — A synchronized queue class, Python 공식 문서](https://docs.python.org/3/library/queue.html)
- [ThreadPoolExecutor — Java SE 21 API 문서](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html)
