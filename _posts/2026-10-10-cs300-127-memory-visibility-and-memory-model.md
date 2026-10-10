---
layout: post
title: "[CS300 #127] 메모리 가시성과 메모리 모델 — 내가 쓴 값을 남이 언제 보는가"
date: 2026-10-10 20:07:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, memory-model, happens-before, atomic]
---

컴퓨터공학 300 주제 시리즈의 127번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

멀티스레드 프로그램에서 한 스레드가 메모리에 쓴 값을 다른 스레드가 "언제, 어떤 순서로" 볼 수 있는지는 저절로 정해지지 않는다. 그 규칙을 정한 계약이 메모리 모델이고, 개발자는 원자 변수·락·volatile 같은 동기화로 happens-before 관계를 만들어야만 순서와 가시성을 보장받는다.

## 왜 필요한가

다음 코드는 너무 당연해 보인다.

```
스레드 A:  data = 42;  ready = true;
스레드 B:  while (!ready) {}   print(data);
```

B 는 42 를 찍을 것 같다. 하지만 동기화 없이 쓰면 C·C++·자바·Go 어디에서도 보장되지 않는다. B 가 영원히 루프를 돌 수도 있고, `ready` 는 true 인데 `data` 는 0으로 보일 수도 있다.

이유는 세 겹이다.

1. **컴파일러**가 명령 순서를 바꾸거나, 루프 안의 `ready` 읽기를 루프 밖으로 빼 버린다(한 번만 읽어도 단일 스레드 의미는 같으니까).
2. **CPU** 가 쓰기를 스토어 버퍼에 잠시 담아 두고 뒤의 읽기를 먼저 실행한다. 비순차 실행도 한다.
3. **캐시**가 코어마다 따로 있어서, 코어 간에 값이 전파되는 시점과 순서가 프로그램 순서와 다를 수 있다.

이 최적화들은 단일 스레드 결과를 바꾸지 않는 범위에서 성능을 크게 올린다. 대가로, 여러 스레드가 함께 볼 때의 순서는 따로 약속해야 한다. 그 약속이 메모리 모델이다.

## 핵심 개념

### 순차 일관성 (Sequential Consistency)

램포트(Leslie Lamport)가 1979년 정의한 가장 직관적인 모델이다. "모든 스레드의 연산이 어떤 하나의 전체 순서로 섞여 실행된 것처럼 보이고, 그 순서 안에서 각 스레드의 연산은 프로그램 순서를 지킨다." 사람이 머릿속으로 상상하는 실행이 바로 이것이다.

문제는 하드웨어가 이것을 기본으로 주지 않는다는 점이다. x86 은 TSO(total store order)라는 조금 약한 모델로, 쓰기 뒤의 읽기가 앞당겨질 수 있다. ARM·POWER 는 훨씬 약해서 더 많은 재배치가 허용된다.

### 고전적 예: 스토어 버퍼링

```
초기값 x = y = 0
스레드 1: x = 1; r1 = y;
스레드 2: y = 1; r2 = x;
```

순차 일관성이라면 `r1 == 0 && r2 == 0` 은 불가능하다. 누군가는 먼저 썼을 테니까. 그런데 x86 에서도 이 결과가 나올 수 있다. 각 코어의 쓰기가 스토어 버퍼에 머무는 동안 읽기가 먼저 메모리에서 옛 값을 읽기 때문이다.

### 언어 수준 메모리 모델: DRF-SC

하드웨어마다 다른 규칙을 개발자가 다 외울 수는 없다. 그래서 자바(JSR-133, Java 5), C/C++11, Go 는 언어 수준에서 다음 계약을 둔다.

> 데이터 경쟁(data race)이 없는 프로그램은 순차 일관적으로 실행된 것처럼 보인다.

이를 DRF-SC(data-race-free → sequentially consistent)라 부른다. 데이터 경쟁이란 두 스레드가 같은 메모리에 동시에 접근하고, 적어도 하나가 쓰기이며, 둘 사이에 동기화가 없는 경우다. C/C++ 에서는 데이터 경쟁 자체가 정의되지 않은 동작(UB)이다.

즉 개발자의 일은 "모든 공유 변수 접근을 동기화로 엮는 것" 하나다. 그러면 하드웨어가 무엇을 재배치하든 컴파일러가 필요한 펜스를 넣어 준다.

### happens-before

동기화가 만드는 순서 관계를 happens-before 라 한다. A happens-before B 이면 A 의 효과(그리고 A 이전의 모든 쓰기)가 B 에서 보인다.

| 동기화 | 만들어지는 관계 |
|---|---|
| 락 | unlock 이 같은 락의 다음 lock 보다 앞선다 |
| 자바 `volatile` | volatile 쓰기가 같은 변수의 이후 읽기보다 앞선다 |
| C++ atomic release/acquire | release 쓰기가 그 값을 읽은 acquire 읽기보다 앞선다 |
| 스레드 시작·조인 | `start()` 이전 → 새 스레드, 스레드 끝 → `join()` 이후 |
| Go 채널 | 송신이 그 값의 수신 완료보다 앞선다 |

앞의 예에서 `ready` 를 원자 변수로 바꾸고 release 로 쓰고 acquire 로 읽으면, `data = 42` 가 release 이전에 있으므로 acquire 이후의 `print(data)` 에서 반드시 42 가 보인다. 이것이 "게시(publication)" 패턴이다.

### 메모리 순서 단계 (C++ 기준)

| 순서 | 보장 | 용도 |
|---|---|---|
| `relaxed` | 그 변수 자체의 원자성만 | 통계 카운터 |
| `acquire` / `release` | 짝을 이룬 쌍 사이의 순서 | 게시, 락 구현 |
| `seq_cst` | 모든 seq_cst 연산의 단일 전체 순서 | 기본값, 가장 안전 |

모르면 기본값 `seq_cst` 를 쓴다. 약한 순서는 측정으로 필요가 확인된 곳에서만 쓴다.

### 흔한 오해

- **"volatile 이면 스레드 안전하다"** — C/C++ 의 `volatile` 은 하드웨어 레지스터용이지 스레드 동기화가 아니다. 자바의 `volatile` 은 가시성과 순서를 주지만 `count++` 같은 복합 연산을 원자적으로 만들지는 않는다.
- **"x86 은 강하니까 괜찮다"** — 컴파일러 재배치는 하드웨어와 무관하게 일어난다. 아래 실험이 그 예다.
- **"파이썬은 GIL 이 있으니 상관없다"** — GIL 은 바이트코드 하나의 원자성을 줄 뿐, 여러 단계 연산의 원자성은 주지 않는다. 그리고 free-threaded 빌드에서는 GIL 자체가 없다.

## 직접 해 보기

파이썬으로는 이 현상을 재현하기 어려워 C 로 본다. 첫 예제와 같은 구조를 일반 변수와 원자 변수로 각각 컴파일한다.

```c
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <unistd.h>

int data = 0;
#ifdef USE_ATOMIC
atomic_bool ready = 0;
#define PUBLISH() atomic_store_explicit(&ready, 1, memory_order_release)
#define WAIT()    while (!atomic_load_explicit(&ready, memory_order_acquire)) ;
#else
int ready = 0;                       /* 일반 변수: 데이터 경쟁 */
#define PUBLISH() (ready = 1)
#define WAIT()    while (!ready) ;
#endif

void *reader(void *arg) {
    WAIT();
    printf("reader saw data = %d\n", data);
    return NULL;
}

int main(void) {
    pthread_t t;
    pthread_create(&t, NULL, reader, NULL);
    sleep(1);
    data = 42;
    PUBLISH();
    pthread_join(t, NULL);
    return 0;
}
```

```
$ gcc -O2 -pthread -o vis_plain vis.c
$ gcc -O2 -pthread -DUSE_ATOMIC -o vis_atomic vis.c
$ timeout 5 ./vis_plain; echo "exit=$?"
exit=124
$ timeout 5 ./vis_atomic; echo "exit=$?"
reader saw data = 42
exit=0
```

GCC 13.3, x86-64 에서 확인한 결과다. 일반 변수 버전은 5초 타임아웃(124)으로 끝난다. `-O2` 최적화가 `ready` 를 레지스터에 한 번만 읽어 두고 무한 루프로 바꿨기 때문이다. 데이터 경쟁이 있는 프로그램이므로 컴파일러는 그렇게 해도 된다. 원자 변수 버전은 매번 메모리에서 읽고, acquire-release 쌍 덕분에 `data` 의 42 도 보장된다. `-O0` 로 컴파일하면 일반 버전도 우연히 동작할 수 있다. 우연히 동작하는 코드가 가장 위험하다.

## 현업에서는

- **더블 체크 락킹.** 자바 싱글턴의 더블 체크 락킹은 필드에 `volatile` 이 없으면 생성이 끝나지 않은 객체를 다른 스레드가 볼 수 있다. Java 5 메모리 모델 개정 이후 `volatile` 을 붙이면 올바르게 동작한다.
- **경쟁 탐지기.** Go 의 `go test -race`, C/C++ 의 ThreadSanitizer(`-fsanitize=thread`)는 데이터 경쟁을 실행 중에 찾아 준다. CI 에 넣어 두면 드물게만 터지는 버그를 미리 잡는다.
- **분산 시스템과의 연결.** 메모리 모델의 질문 "쓴 값을 언제 누가 보는가" 는 복제된 데이터베이스에서 그대로 다시 나온다. 순차 일관성, 선형화 가능성, 최종 일관성 같은 용어가 이 글과 뒤의 일관성 모델 글에서 같은 뜻으로 쓰인다. 코어 사이의 캐시가 기계 사이의 복제본으로 바뀌었을 뿐이다.

## 확인 문제

1. 동기화 없는 `while (!ready) {}` 가 무한 루프가 될 수 있는 이유를 컴파일러 관점에서 설명하라.
2. DRF-SC 계약을 한 문장으로 말하라.
3. 스토어 버퍼링 예제에서 `r1 == 0 && r2 == 0` 이 x86 에서 가능한 이유는?
4. 자바 `volatile int count` 에 대해 여러 스레드가 `count++` 를 하면 안전한가?
5. release/acquire 쌍이 "게시" 를 안전하게 만드는 원리는?

### 풀이

1. 데이터 경쟁이 없다고 가정할 수 있으므로, 루프 안에서 `ready` 가 바뀌지 않는다고 보고 한 번만 읽어 레지스터에 두는 최적화를 할 수 있다.
2. 데이터 경쟁이 없는 프로그램은 순차 일관적으로 실행된 것처럼 보인다.
3. 각 코어의 쓰기가 스토어 버퍼에 머무는 동안 뒤의 읽기가 먼저 수행되어 상대의 쓰기 전 값을 읽을 수 있기 때문이다.
4. 안전하지 않다. `volatile` 은 가시성과 순서만 주고, 읽기-증가-쓰기의 원자성은 주지 않는다. `AtomicInteger` 를 써야 한다.
5. release 쓰기 이전의 모든 쓰기가, 그 값을 읽은 acquire 읽기 이후에 보이도록 happens-before 관계가 생기기 때문이다.

## 더 읽을거리 (References)

- [Leslie Lamport, "How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs", IEEE Trans. Computers, 1979](https://lamport.azurewebsites.net/pubs/multi.pdf)
- [The Java Language Specification, Chapter 17. Threads and Locks](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)
- [std::memory_order — cppreference](https://en.cppreference.com/w/cpp/atomic/memory_order)
- [The Go Memory Model](https://go.dev/ref/mem)
