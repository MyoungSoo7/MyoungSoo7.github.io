---
layout: post
title: "[CS300 #126] 락 없는 자료구조와 CAS — 잠그지 않고 경쟁을 이기는 법"
date: 2026-10-10 20:06:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, lock-free, cas, atomic, concurrency]
---

컴퓨터공학 300 주제 시리즈의 126번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

CAS(compare-and-swap)는 "메모리 값이 내가 예상한 값과 같을 때만 새 값으로 바꾼다" 를 하드웨어가 한 번에(원자적으로) 해 주는 명령이다. 이 명령 위에 "읽고, 계산하고, CAS 로 바꾸고, 실패하면 다시" 라는 루프를 얹으면 락 없이도 여러 스레드가 안전하게 자료구조를 고칠 수 있다.

## 왜 필요한가

뮤텍스는 쉽고 안전하다. 하지만 비용이 있다.

- 락을 쥔 스레드가 선점당하거나 페이지 폴트로 멈추면, 그 락을 기다리는 스레드가 모두 같이 멈춘다.
- 경쟁이 심하면 스레드가 잠들고 깨어나는 비용(커널 진입, 문맥 교환)이 실제 일보다 커진다.
- 시그널 핸들러나 인터럽트 문맥처럼 락을 잡으면 안 되는 곳이 있다.
- 우선순위 역전, 교착 같은 락 고유의 문제가 따라온다.

카운터 하나 올리는 데 락을 잡는 것은 과하다. 큐에 하나 넣는 데 다른 모든 스레드를 세우는 것도 과하다. CAS 는 "충돌이 드물면 그냥 하고, 충돌하면 다시 한다" 는 낙관적 방식으로 이 비용을 줄인다. 이 낙관적 사고방식은 데이터베이스의 낙관적 잠금, HTTP 의 `If-Match`, 쿠버네티스의 `resourceVersion` 까지 그대로 이어진다.

## 핵심 개념

### CAS 의 의미

의사 코드로 쓰면 다음과 같다. 이 전체가 하나의 원자적 명령으로 실행된다는 것이 핵심이다.

```
CAS(addr, expected, new):
    if *addr == expected:
        *addr = new
        return true
    return false
```

x86 에서는 `LOCK CMPXCHG` 명령, ARM 에서는 LL/SC(load-linked/store-conditional) 쌍이나 최근 아키텍처의 CAS 명령으로 구현된다. 언어에서는 C++ `std::atomic::compare_exchange_strong/weak`, 자바 `AtomicInteger.compareAndSet`, Go `atomic.CompareAndSwapInt64` 로 쓴다.

### CAS 루프

원자적 증가를 CAS 로 만들면 이렇다.

```
loop:
    old = load(counter)
    new = old + 1
    if CAS(counter, old, new): break
    # 실패: 그 사이 누가 바꿨다. 다시 읽고 다시 계산한다.
```

락을 잡지 않으므로 어떤 스레드가 중간에 멈춰도 다른 스레드는 계속 진행한다. 누군가의 CAS 는 반드시 성공하기 때문이다.

### 진행 보장의 등급

| 등급 | 보장 |
|---|---|
| 블로킹 | 락 보유자가 멈추면 다른 스레드도 멈출 수 있다 |
| 장애물 없음(obstruction-free) | 혼자 돌면 유한 단계 안에 끝난다 |
| 락 없음(lock-free) | 시스템 전체로 보면 언제나 누군가는 진행한다 |
| 대기 없음(wait-free) | 모든 스레드가 각자 유한 단계 안에 끝난다 |

CAS 루프는 보통 lock-free 다. 운이 나쁜 스레드는 계속 실패할 수 있으니 wait-free 는 아니다. 허리히(Maurice Herlihy)는 1991년 논문 "Wait-Free Synchronization" 에서 원자적 연산의 능력을 합의 수(consensus number)로 분류하고, CAS 가 임의 개수 스레드의 합의를 풀 수 있는 보편적 연산임을 보였다. 읽기·쓰기 레지스터만으로는 두 스레드의 합의도 wait-free 로 풀 수 없다.

### 락 없는 스택 (Treiber 스택)

가장 단순한 락 없는 자료구조다.

```
push(x):
    node = new Node(x)
    loop:
        node.next = top
        if CAS(top, node.next, node): return

pop():
    loop:
        old = top
        if old == null: return empty
        if CAS(top, old, old.next): return old.value
```

### ABA 문제

스레드 1 이 `top == A` 를 읽고 멈춘다. 그 사이 스레드 2 가 A 를 꺼내고, B 를 꺼내고, A 를 다시 넣는다. 스레드 1 이 깨어나 `CAS(top, A, A.next)` 를 하면 성공한다. 값은 같지만 A.next 는 이미 사라진 B 를 가리킨다. 자료구조가 망가진다.

```
T1 읽음: top=A → B → C
T2: pop A, pop B, push A    →  top=A → C
T1: CAS(top, A, B) 성공!     →  top=B (이미 해제된 노드)
```

대책은 다음과 같다.

- **태그(버전) 붙이기**: 포인터와 카운터를 함께 CAS 한다(double-width CAS). 값이 같아도 버전이 다르면 실패한다.
- **안전한 메모리 회수**: 해저드 포인터, 에포크 기반 회수로 누가 보고 있는 노드는 재사용하지 않는다.
- **가비지 컬렉터**: 자바처럼 GC 가 있으면 참조가 남은 노드는 재사용되지 않아 포인터 ABA 의 상당 부분이 사라진다.

### 그래서 늘 락 없는 게 좋은가

아니다. 경쟁이 매우 심하면 CAS 실패와 재시도가 캐시 라인을 계속 흔들어(캐시 핑퐁) 오히려 느려질 수 있다. 구현과 검증은 훨씬 어렵다. 실무 원칙은 "검증된 라이브러리를 쓴다" 다. 자바의 `ConcurrentLinkedQueue` 는 Michael & Scott 의 락 없는 큐 알고리즘에 기반한다.

## 직접 해 보기

파이썬에는 하드웨어 CAS 가 노출되어 있지 않다. 그래서 CAS 를 락으로 흉내 낸 `AtomicInt` 를 만들고, 그 위에 CAS 루프를 올려 동작과 재시도를 관찰한다. 락은 "하드웨어가 한 명령으로 해 준다" 를 대신할 뿐, 증가 로직 자체는 락을 쥐지 않는다.

```python
import threading, time

class AtomicInt:
    def __init__(self, v=0):
        self._v = v; self._hw = threading.Lock()   # 하드웨어 원자성 흉내
    def load(self): return self._v
    def cas(self, expected, new):
        with self._hw:
            if self._v == expected:
                self._v = new; return True
            return False

counter = AtomicInt(); retries = [0]

def incr(n):
    for _ in range(n):
        while True:
            old = counter.load()
            time.sleep(0)                # 다른 스레드에 양보: 경쟁을 일부러 키운다
            if counter.cas(old, old + 1): break
            retries[0] += 1

ts = [threading.Thread(target=incr, args=(2000,)) for _ in range(4)]
for t in ts: t.start()
for t in ts: t.join()
print("counter", counter.load(), "retries", retries[0])

# 비교: 원자성 없는 증가
plain = [0]
def unsafe(n):
    for _ in range(n):
        v = plain[0]; time.sleep(0); plain[0] = v + 1
ts = [threading.Thread(target=unsafe, args=(2000,)) for _ in range(4)]
for t in ts: t.start()
for t in ts: t.join()
print("unsafe", plain[0])
```

실행하면 CAS 버전은 항상 `counter 8000` 이고 재시도 횟수가 수천에서 수만 번 찍힌다(한 실행에서 19807번). 원자성 없는 버전은 8000 보다 훨씬 작은 값이 나온다(같은 실행에서 2000). 읽기와 쓰기 사이에 다른 스레드가 끼어들어 갱신을 덮어쓴 것이다(lost update). CAS 는 이 덮어쓰기를 감지해 다시 하게 만든다.

## 현업에서는

- **원자 카운터.** 메트릭 라이브러리의 카운터, 참조 카운트(`std::shared_ptr`), 커넥션 풀의 남은 개수는 대부분 원자 연산으로 구현된다.
- **낙관적 동시성 제어.** 쿠버네티스 API 서버에 객체를 업데이트할 때 `metadata.resourceVersion` 이 다르면 409 Conflict 가 난다. 컨트롤러는 다시 읽고 다시 시도한다. 이것은 분산 버전의 CAS 루프다. etcd 의 트랜잭션(`compare` 후 `then`)도 같은 원리다.
- **데이터베이스.** `UPDATE t SET v = ?, version = version + 1 WHERE id = ? AND version = ?` 의 영향받은 행 수가 0이면 충돌로 보고 재시도한다. 행 잠금 없이 동시 수정을 감지하는 흔한 패턴이다.
- **HTTP.** `ETag` 와 `If-Match` 헤더로 "내가 본 버전일 때만 덮어써라" 를 표현한다. 조건이 맞지 않으면 412 Precondition Failed 다.

## 확인 문제

1. CAS 가 "원자적" 이어야 하는 이유를 읽기·비교·쓰기를 따로 할 때와 비교해 설명하라.
2. lock-free 와 wait-free 의 차이는?
3. ABA 문제란 무엇이고 대표적 대책 두 가지는?
4. 쿠버네티스에서 `resourceVersion` 충돌(409)이 났을 때 컨트롤러가 하는 일은 CAS 루프의 어느 단계에 해당하는가?

### 풀이

1. 따로 하면 비교와 쓰기 사이에 다른 스레드가 값을 바꿀 수 있어, 바뀐 값을 덮어쓰게 된다. 원자적이면 그 틈이 없다.
2. lock-free 는 시스템 전체로 누군가는 진행함을 보장하고, wait-free 는 모든 스레드 각각이 유한 단계 안에 끝남을 보장한다.
3. 값이 A→B→A 로 바뀌어 CAS 가 변화를 감지하지 못하는 문제다. 버전 태그를 함께 CAS 하기, 해저드 포인터·에포크 기반 회수로 노드 재사용 막기.
4. CAS 실패 후 "다시 읽고 다시 계산하는" 재시도 단계다.

## 더 읽을거리 (References)

- [Maurice Herlihy, "Wait-Free Synchronization", ACM TOPLAS 13(1), 1991 (저자 공개본)](https://cs.brown.edu/~mph/Herlihy91/p124-herlihy.pdf)
- [Michael & Scott, Non-Blocking Concurrent Queue Algorithm (University of Rochester)](https://www.cs.rochester.edu/research/synchronization/pseudocode/queues.html)
- [std::atomic::compare_exchange — cppreference](https://en.cppreference.com/w/cpp/atomic/atomic/compare_exchange)
- [java.util.concurrent.atomic — Java SE 21 API 문서](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/atomic/package-summary.html)
