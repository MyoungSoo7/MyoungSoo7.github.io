---
layout: post
title: "[CS300 #094] 캐시 일관성 — 코어마다 캐시가 있을 때 같은 값을 보게 하는 법"
date: 2026-10-10 19:34:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, cache-coherence, mesi, false-sharing]
---

컴퓨터공학 300 주제 시리즈의 094번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

멀티코어 CPU 는 코어마다 자기 캐시를 갖기 때문에 같은 주소의 복사본이 여러 개 생긴다. 캐시 일관성 프로토콜(대표적으로 MESI 계열)은 "한 코어가 쓰면 다른 코어의 낡은 복사본을 무효화한다" 는 규칙으로 모두가 하나의 메모리를 보는 것처럼 만든다. 이 규칙의 비용이 거짓 공유 같은 성능 함정으로 드러난다.

## 왜 필요한가

코어 0 이 변수 x 를 자기 L1 캐시에서 1 로 바꿨는데, 코어 1 의 L1 에는 아직 x = 0 이 남아 있다면? 두 스레드가 서로 다른 세상을 본다. 하드웨어가 이것을 막아 주지 않으면 멀티스레드 프로그램은 아예 쓸 수 없다.

하드웨어는 막아 준다. 대신 그 일에 비용이 든다. 이 글의 실험에서 두 스레드가 **서로 다른 변수**를 증가시키는데도, 두 변수가 같은 캐시 라인에 있다는 이유만으로 약 2~3배 느려진다. 코드만 봐서는 공유가 전혀 없는데 말이다. 일관성의 단위가 변수가 아니라 캐시 라인이기 때문이다.

## 핵심 개념

### 문제 상황

```
        코어 0                 코어 1
      ┌────────┐            ┌────────┐
      │ L1: x=1│            │ L1: x=0│   ← 낡은 복사본
      └───┬────┘            └───┬────┘
          └──────────┬──────────┘
                ┌────┴────┐
                │ 메모리 x=0│
                └─────────┘
```

일관성(coherence)은 **한 주소**에 대해 다음을 보장하는 성질이다.

1. 모든 코어가 그 주소에 대한 쓰기들을 같은 순서로 본다(쓰기 직렬화).
2. 한 코어의 쓰기는 결국 다른 코어의 읽기에 보인다(쓰기 전파).

### 무효화 기반 프로토콜: MESI

대부분의 CPU 는 쓰기 전에 다른 복사본을 무효화하는 방식을 쓴다. 각 캐시 라인은 네 상태 중 하나를 갖는다.

| 상태 | 뜻 | 다른 캐시에 복사본 | 메모리와 같은가 |
|---|---|---|---|
| M (Modified) | 내가 고쳤다 | 없음 | 다름(더티) |
| E (Exclusive) | 나만 갖고 있고 안 고쳤다 | 없음 | 같음 |
| S (Shared) | 여럿이 읽기용으로 갖고 있다 | 있을 수 있음 | 같음 |
| I (Invalid) | 쓸 수 없다 | - | - |

주요 전이는 다음과 같다.

```
읽기 미스, 다른 곳에 없음        → E
읽기 미스, 다른 곳에 있음        → S (M 이던 쪽은 값을 내려주고 S 로)
쓰기 (S 상태)                   → 다른 복사본 모두 I 로 무효화 요청 후 M
쓰기 (E 상태)                   → 조용히 M (아무에게도 알릴 필요 없음)
다른 코어가 쓰기 요청            → 내 복사본 I
```

E 상태의 존재 이유가 마지막에서 두 번째 줄이다. 혼자 가진 라인은 버스 트래픽 없이 바로 쓸 수 있다. 실제 제품은 여기에 상태를 더한 변형(MOESI, MESIF 등)을 쓴다.

### 스누핑과 디렉터리

| 방식 | 원리 | 확장성 |
|---|---|---|
| 스누핑 | 모든 캐시가 공유 버스의 요청을 엿듣고 반응 | 코어가 적을 때 단순하고 빠름 |
| 디렉터리 | 라인별로 "누가 갖고 있는지" 를 기록한 디렉터리에 물어 해당 코어에만 메시지 | 코어가 많을 때 유리 |

코어 수가 많은 서버 CPU 와 여러 소켓 시스템은 디렉터리나 그와 비슷한 필터 구조를 쓴다.

### 거짓 공유 (False Sharing)

일관성은 캐시 라인 단위로 관리된다. 서로 다른 스레드가 **서로 다른 변수**를 쓰더라도 그 변수들이 같은 라인에 있으면, 한쪽이 쓸 때마다 다른 쪽의 라인이 무효화된다. 라인이 두 코어 사이를 탁구공처럼 오간다.

```
같은 64B 라인: [ counter_a | counter_b | ... ]
코어 0: counter_a++  → 라인 M, 코어 1 의 라인 I
코어 1: counter_b++  → 라인 가져와 M, 코어 0 의 라인 I
코어 0: counter_a++  → 다시 가져와 ...
```

해결은 간단하다. 자주 쓰는 변수들을 서로 다른 캐시 라인에 떨어뜨려 놓는다(패딩, 정렬).

### 일관성과 메모리 모델은 다르다

일관성은 **한 주소**에 관한 약속이다. 서로 **다른 주소**에 대한 쓰기들이 다른 코어에 어떤 순서로 보이는지는 메모리 일관성 모델(memory consistency model)의 영역이다. x86 은 비교적 강한 순서를, ARM 은 더 느슨한 순서를 허용한다. 그래서 캐시가 일관적이어도 락이나 원자 연산, 메모리 배리어 없이 짠 동시성 코드는 틀릴 수 있다. 언어 차원에서는 자바 메모리 모델, Go 메모리 모델, C11/C++11 원자 연산이 이 규칙을 정한다.

## 직접 해 보기

두 스레드를 서로 다른 물리 코어에 고정하고, 각자 자기 카운터를 원자적으로 5천만 번 증가시킨다. 두 카운터가 같은 라인에 있을 때와 떨어져 있을 때를 비교한다.

```c
/* fs.c — 거짓 공유(false sharing) 측정 */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <time.h>
#define ITERS 50000000L

struct { long a; long b; } same;                 /* 같은 64B 라인 */
struct { long a; char pad[64]; long b; } apart;  /* 다른 라인 */

struct arg { long *x; int cpu; };
static void *inc(void *p) {
    struct arg *a = p;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(a->cpu, &set);       /* 서로 다른 물리 코어에 고정 */
    pthread_setaffinity_np(pthread_self(), sizeof set, &set);
    long *x = a->x;
    for (long i = 0; i < ITERS; i++) __atomic_fetch_add(x, 1, __ATOMIC_RELAXED);
    return NULL;
}
static double run(long *x, long *y) {
    pthread_t t1, t2; struct timespec s, e;
    clock_gettime(CLOCK_MONOTONIC, &s);
    struct arg a1 = { x, 0 }, a2 = { y, 1 };
    pthread_create(&t1, NULL, inc, &a1);
    pthread_create(&t2, NULL, inc, &a2);
    pthread_join(t1, NULL); pthread_join(t2, NULL);
    clock_gettime(CLOCK_MONOTONIC, &e);
    return (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec) / 1e9;
}
int main(void) {
    printf("same line:  %.2f s\n", run(&same.a, &same.b));
    printf("apart:      %.2f s\n", run(&apart.a, &apart.b));
    return 0;
}
```

```bash
gcc -O2 -pthread fs.c -o fs && ./fs
```

2코어(코어당 하이퍼스레드 2개) x86-64 노트북급 CPU 에서 세 번 돌린 결과다. CPU 0 과 1 이 서로 다른 물리 코어인 것을 `/sys/devices/system/cpu/cpu0/topology/thread_siblings_list` 로 확인하고 고정했다.

```
same line:  1.87 s     apart: 0.51 s
same line:  1.57 s     apart: 0.75 s
same line:  1.61 s     apart: 0.55 s
```

코드상 두 스레드는 아무것도 공유하지 않는데, 같은 라인에 있다는 이유만으로 2~3배 느렸다. 다른 작업이 함께 돌던 노드라 수치는 흔들렸다. 참고로 원자 연산 대신 `volatile` 증가로 바꾸면 차이가 30% 안팎으로 줄었다. 저장 버퍼 등 마이크로아키텍처의 영향이라 정확한 배율은 CPU 마다 다르다. 같은 물리 코어의 두 하이퍼스레드(CPU 0 과 2)에 고정해 보니 0.88s 대 0.81s 로 차이가 거의 사라졌다. L1 을 공유하므로 라인이 오갈 일이 없기 때문이다. 대신 두 스레드가 한 코어의 실행 자원을 나눠 쓰므로 "apart" 쪽은 다른 코어에 둘 때보다 느렸다.

## 현업에서는

- **카운터와 통계**: 스레드별 통계를 배열 `counts[thread_id]` 에 모으면 거짓 공유가 생기기 쉽다. 원소마다 캐시 라인 크기로 패딩하거나 스레드 로컬로 모았다가 마지막에 합친다. 자바는 이 목적의 `@Contended` 를 JEP 142 로 도입했고(JDK 내부용, 사용하려면 JVM 옵션 필요), 리눅스 커널은 `____cacheline_aligned` 같은 매크로를 쓴다.
- **락 경합**: 스핀락 하나를 수십 개 코어가 두드리면 그 라인이 코어 사이를 계속 오간다. 락을 쪼개거나(샤딩) 코어별 자료구조로 바꾸는 것이 해결책이다.
- **CPU 고정과 NUMA**: 소켓이 여러 개인 서버에서는 다른 소켓의 캐시와 일관성을 맞추는 비용이 더 크다. 쿠버네티스의 CPU Manager `static` 정책과 Topology Manager 는 지연에 민감한 파드를 특정 코어·NUMA 노드에 묶어 이런 비용을 줄이려는 기능이다.

## 확인 문제

1. MESI 의 E 상태가 있으면 어떤 이점이 있는가.
2. 거짓 공유란 무엇이고 어떻게 해결하는가.
3. 캐시 일관성이 보장되면 락 없이 짠 동시성 코드도 안전한가.
4. 위 실험에서 두 스레드를 같은 물리 코어의 하이퍼스레드에 고정하면 차이가 줄어드는 이유는.

### 풀이

1. 다른 캐시에 복사본이 없다는 것을 알기 때문에 쓰기 시 무효화 메시지 없이 바로 M 으로 바꿀 수 있다.
2. 서로 다른 변수가 같은 캐시 라인에 있어 한쪽의 쓰기가 다른 쪽 라인을 무효화하는 현상이다. 패딩·정렬로 변수를 서로 다른 라인에 둔다.
3. 아니다. 일관성은 한 주소에 대한 약속일 뿐, 여러 주소 사이의 순서와 원자성은 메모리 모델과 동기화 도구가 다룬다.
4. 하이퍼스레드는 같은 물리 코어의 L1 캐시를 공유하므로 라인이 코어 사이를 오가지 않기 때문이다.

## 더 읽을거리 (References)

- Linux Kernel Documentation, [Linux Kernel Memory Barriers](https://docs.kernel.org/core-api/wrappers/memory-barriers.html)
- [The Java Language Specification, Java SE 21 — Chapter 17. Threads and Locks](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)
- OpenJDK, [JEP 142: Reduce Cache Contention on Specified Fields](https://openjdk.org/jeps/142)
- Mark S. Papamarcos, Janak H. Patel, "A Low-Overhead Coherence Solution for Multiprocessors with Private Cache Memories", *ISCA*, 1984.
