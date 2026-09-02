---
layout: post
title: 자바 동시성 로직이 풀려던 문제, 그리고 그 전과 후
date: 2026-09-03 03:49:18 +0900
categories: [java]
tags: [concurrency, jvm, java-util-concurrent, virtual-threads]
---

자바 동시성 API는 어느 날 갑자기 완성된 형태로 나온 게 아니다. `synchronized` 하나로
버티던 시절의 구체적인 실패 사례들이 쌓여서 `java.util.concurrent`가 나왔고,
그 이후에도 "쓰레드 자체가 비싸다"는 다음 병목이 드러나면서 가상 쓰레드까지 이어졌다.
이 글은 각 단계에서 **정확히 어떤 문제를 풀었는지**를 1차 자료 기준으로 정리한다.

## 1. 동시성이 푸는 문제는 세 가지로 좁혀진다

자바 메모리 모델(JMM)을 정의하는 [JLS 17장](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)은
멀티쓰레드 프로그램이 겪는 문제를 크게 세 갈래로 다룬다.

- **가시성(visibility)** — 한 쓰레드가 쓴 값을 다른 쓰레드가 언제 보게 되는지가
  컴파일러·CPU 재정렬 때문에 보장되지 않는 문제. JLS 17.4는 이를 "happens-before"
  관계로 공식화한다.
- **원자성(atomicity)** — `count++`처럼 보기엔 한 줄이지만 실제로는 읽기·연산·쓰기
  세 단계로 나뉘는 연산이 중간에 끼어들어 값을 잃어버리는 문제(lost update).
- **상호배제와 진행(mutual exclusion & progress)** — 공유 자원에 대한 접근 순서를
  통제하지 못하면 경쟁 상태(race condition)뿐 아니라 교착 상태(deadlock), 기아
  상태(starvation)로 이어진다.

`synchronized`와 `volatile`은 이 세 가지를 다루기 위해 JDK 1.0부터 있던 도구였다.
문제는 도구가 너무 거칠었다는 데 있다.

## 2. java.util.concurrent 이전 — synchronized 하나로 버티던 시절

JDK 5 이전 자바에서 동시성 제어 수단은 사실상 `synchronized` 블록/메서드와
`Object.wait()/notify()`, 그리고 `volatile` 뿐이었다. 이 구조에는 실무에서
반복적으로 부딪히는 한계가 있었다.

- **락을 조건부로 얻거나 포기할 수 없다.** `synchronized`는 블록에 진입하면 락을
  얻을 때까지 무조건 기다린다. "1초만 기다려보고 안 되면 포기"하는 타임아웃이나,
  대기 중 인터럽트를 받아 취소하는 것이 불가능했다.
- **읽기와 쓰기를 구분할 수 없다.** 읽기 전용 접근이 압도적으로 많은 자료구조에서도
  읽기끼리 병렬로 허용하는 방법이 없어 불필요하게 직렬화됐다.
- **조건 변수가 하나뿐이다.** `wait/notify`는 객체당 모니터 하나, 대기 집합 하나였다.
  "버퍼가 가득 찼을 때"와 "버퍼가 비었을 때"처럼 조건이 여러 개인 생산자-소비자
  패턴을 표현하려면 `notifyAll`로 관련 없는 쓰레드까지 깨워야 했다.
- **원자적 증가 같은 단순 연산에도 락이 필요했다.** CPU에 CAS(compare-and-swap)
  명령이 있었지만 언어 차원에서 이를 쓸 방법이 없어, 카운터 하나 늘리는 데도
  모니터 진입/이탈 비용을 치렀다.
- **쓰레드 풀을 직접 짜야 했다.** `Runnable`을 `Thread`에 얹어 실행하는 것 외에
  표준화된 실행 프레임워크가 없어 프로젝트마다 자체 쓰레드 풀을 구현했다.

이 문제들을 정리해 표준 해법으로 만든 것이 더그 리(Doug Lea)가 이끈
[JSR-166](https://jcp.org/en/jsr/detail?id=166)이고, 그 산출물이 2004년
Java 5(J2SE 5.0)에 `java.util.concurrent` 패키지로 들어갔다.

## 3. JDK 5 (2004) — java.util.concurrent 등장 이후

[java.util.concurrent 패키지 문서](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html)에
명시된 대로, 이 패키지는 위 문제들을 각각 구체적인 클래스로 대응시켰다.

| 이전 문제 | 이후 해법 |
|---|---|
| 조건부·인터럽트 가능 락 부재 | `Lock`/`ReentrantLock`의 `tryLock()`, `lockInterruptibly()` |
| 읽기/쓰기 구분 불가 | `ReadWriteLock`/`ReentrantReadWriteLock` |
| 조건 변수 하나뿐 | `Condition` — 락 하나에 여러 대기 큐를 둘 수 있음 |
| CAS 부재 | `AtomicInteger`, `AtomicLong` 등 — 락 없이 CAS로 원자적 갱신 |
| 자체 구현 쓰레드 풀 | `ExecutorService`, `ThreadPoolExecutor` — 표준 실행 프레임워크 |
| 스레드 안전 컬렉션 직접 구현 | `ConcurrentHashMap`, `CopyOnWriteArrayList` 등 |
| 수동 카운트다운/배리어 구현 | `CountDownLatch`, `CyclicBarrier`, `Semaphore` |

특히 `ConcurrentHashMap`은 `Hashtable`이나 `Collections.synchronizedMap`처럼
맵 전체를 하나의 락으로 잠그지 않고, 내부를 여러 구간으로 나눠 잠금 범위를
좁히는 방식으로 설계됐다는 점이 당시 문서에 명시돼 있다. 이는 "락은 필요하지만
그 범위는 최소화한다"는 이 시기 동시성 설계의 공통 방향을 보여준다.

## 4. JDK 7~9 — 실행 모델의 확장

`java.util.concurrent`가 자료구조와 저수준 동기화 도구를 표준화했다면, 그 다음
단계는 "작업을 어떻게 조합해서 실행할 것인가"의 문제였다.

- **JDK 7 (2011)** — `ForkJoinPool`이 추가돼 작업을 재귀적으로 쪼개 여러 코어에
  분산시키고 유휴 워커가 다른 워커의 큐에서 일을 훔쳐오는(work-stealing) 실행
  모델을 표준화했다.
- **JDK 8 (2014)** — `CompletableFuture`가 콜백 체이닝(`thenApply`, `thenCompose`
  등)을 표준 API로 제공하면서, 비동기 작업의 결과를 기다리며 블로킹하지 않고
  이어붙이는 방식이 가능해졌다.
- **JDK 9 (2017)** — `Flow` API가 리액티브 스트림의 표준 인터페이스(`Publisher`,
  `Subscriber`, `Subscription`, `Processor`)를 JDK에 편입시켰다.

## 5. JDK 21 (2023) — 가상 쓰레드, 다음 병목의 해소

`java.util.concurrent`가 락과 자료구조 문제를 풀고 나자 다음 병목이 드러났다.
**플랫폼 쓰레드 자체가 무겁다**는 점이다. 플랫폼 쓰레드는 OS 쓰레드에 1:1로
매핑되고, [JEP 444 (Virtual Threads)](https://openjdk.org/jeps/444)에 따르면
스택 크기 때문에 개수를 수천 단위로 늘리기 어렵고, 블로킹 I/O 중에는 OS 쓰레드를
점유한 채 아무 일도 하지 않는다. 요청 하나당 쓰레드 하나(thread-per-request)
모델은 동시 접속자가 늘수록 이 비용을 그대로 물려받았다.

JEP 444는 이를 "동기적으로 짜인 코드를 그대로 두고, 실행 단위만 가볍게 만든다"는
방향으로 풀었다. 가상 쓰레드는 JVM이 관리하는 경량 쓰레드로, 블로킹 연산을 만나면
그 순간에만 OS 쓰레드(carrier thread)를 반납하고 다른 가상 쓰레드가 그 자리를
쓴다. `ReentrantLock`, `ConcurrentHashMap` 같은 JDK 5의 도구들은 그대로 유지된
채, 그 위에서 도는 실행 단위가 바뀐 것이다. JDK 19~20의 프리뷰([JEP 425](https://openjdk.org/jeps/425),
[JEP 436](https://openjdk.org/jeps/436))를 거쳐 JDK 21에서 정식 기능이 됐다.

## 정리 — 문제와 해법의 연대기

| 시기 | 풀린 문제 | 남은 문제 |
|---|---|---|
| ~JDK 4 | (없음, 도구가 `synchronized`/`wait-notify` 뿐) | 세밀한 락 제어 불가, CAS 미지원, 표준 실행 프레임워크 부재 |
| JDK 5 (2004) | 조건부 락, 원자적 연산, 표준 컬렉션·실행자 | 비동기 작업 조합이 콜백 지옥으로 흐름 |
| JDK 7~9 | 작업 분할(Fork/Join), 비동기 체이닝, 리액티브 표준 | 플랫폼 쓰레드의 개수·비용 한계 |
| JDK 21 (2023) | 쓰레드 개수 제약 완화(가상 쓰레드) | — |

각 단계는 이전 단계가 풀지 못한 구체적 실패 사례에 대한 응답이었다. 동시성 API를
"쓰레드 안전하게 만드는 마법"으로 보기보다, 어떤 실패를 막기 위해 도입됐는지를
따라가면 언제 무엇을 써야 하는지가 더 분명해진다.

## References

- [JLS SE 21, Chapter 17: Threads and Locks](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)
- [JSR-166: Concurrency Utilities](https://jcp.org/en/jsr/detail?id=166)
- [java.util.concurrent package summary (JDK 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html)
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [JEP 425: Virtual Threads (Preview)](https://openjdk.org/jeps/425)
- [JEP 436: Virtual Threads (Second Preview)](https://openjdk.org/jeps/436)
