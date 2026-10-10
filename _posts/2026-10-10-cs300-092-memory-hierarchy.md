---
layout: post
title: "[CS300 #092] 메모리 계층 구조 — 빠르고 작은 것과 느리고 큰 것을 겹쳐 쌓는 이유"
date: 2026-10-10 19:32:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, memory-hierarchy, locality, latency]
---

컴퓨터공학 300 주제 시리즈의 092번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

메모리 계층 구조는 레지스터–캐시–주기억 장치–저장 장치처럼 빠르고 작고 비싼 층과 느리고 크고 싼 층을 겹쳐 쌓고, 프로그램의 지역성을 이용해 "거의 가장 빠른 층의 속도로, 가장 큰 층의 용량을" 쓰는 것처럼 보이게 하는 설계다.

## 왜 필요한가

CPU 는 1나노초 안에 여러 명령어를 처리하는데, 주기억 장치(DRAM)에서 값 하나를 가져오는 데는 수십~백 나노초 이상이 걸린다. 이 차이를 메우지 못하면 CPU 는 대부분의 시간을 기다리며 보낸다(#086 폰 노이만 병목).

이 글의 실험에서 같은 반복문이 데이터 크기만 바뀌었는데 접근당 시간이 2ns 에서 130ns 로 60배 넘게 늘어난다. 알고리즘의 빅오가 같아도 실제 시간이 크게 다른 이유, "배열이 연결 리스트보다 빠르다" 는 말의 근거가 여기 있다.

## 핵심 개념

### 계층 피라미드

```
            ┌────────┐   빠름, 작음, 비쌈
            │ 레지스터 │
           ┌┴────────┴┐
           │  L1 캐시  │   코어마다
          ┌┴──────────┴┐
          │   L2 캐시   │   코어마다(대개)
         ┌┴────────────┴┐
         │    L3 캐시    │   코어들이 공유(대개)
        ┌┴──────────────┴┐
        │  주기억(DRAM)   │
       ┌┴────────────────┴┐
       │ SSD / HDD / 네트워크│  느림, 큼, 쌈
       └──────────────────┘
```

각 층은 바로 아래 층의 일부를 복사해 두는 캐시 역할을 한다. 층 사이 데이터 이동 단위도 다르다. 캐시와 DRAM 사이는 캐시 라인(x86-64 에서 흔히 64바이트), DRAM 과 디스크 사이는 페이지(흔히 4KB)다.

### 대략적인 크기와 지연 감각

정확한 수치는 CPU 세대와 제품마다 크게 다르므로, 이 글은 자릿수 감각만 잡고 실제 값은 직접 측정한다.

| 층 | 용량 자릿수 | 접근 지연 자릿수 |
|---|---|---|
| 레지스터 | 수백 바이트 | 1사이클 이하 |
| L1 | 수십 KB | 수 사이클 |
| L2 | 수백 KB ~ 수 MB | 십여 사이클 |
| L3 | 수 MB ~ 수백 MB | 수십 사이클 |
| DRAM | 수 GB ~ 수 TB | 수십~백 ns 대 |
| NVMe SSD | 수백 GB ~ 수십 TB | 수십 μs 대 |
| HDD | 수 TB | 수 ms 대 |

층을 하나 내려갈 때마다 지연이 몇 배에서 수천 배씩 늘어난다.

### 지역성: 계층이 통하는 이유

계층 구조는 프로그램이 메모리를 무작위로 쓰지 않는다는 관찰 위에 서 있다.

- **시간 지역성**: 방금 쓴 데이터는 곧 다시 쓴다. 반복문 변수, 자주 호출하는 함수의 코드.
- **공간 지역성**: 방금 쓴 주소 근처를 곧 쓴다. 배열 순회, 순차 명령어 실행.

캐시는 시간 지역성을 위해 최근 데이터를 남겨 두고, 공간 지역성을 위해 한 바이트가 필요해도 주변 64바이트를 통째로 가져온다. 하드웨어 프리페처는 순차·일정 간격 접근 패턴을 감지해 다음 라인을 미리 가져온다.

### 평균 메모리 접근 시간 (AMAT)

```
AMAT = 적중 시간 + 미스율 × 미스 패널티
```

L1 적중 시간 1ns, 미스율 5%, 미스 패널티(아래 층에서 가져오는 시간) 100ns 면 AMAT = 1 + 0.05 × 100 = 6ns. 미스율이 1% 로 줄면 2ns 다. 미스율 몇 %p 가 평균 시간을 몇 배 바꾼다. 다층이면 미스 패널티 자리에 다음 층의 AMAT 를 재귀적으로 넣는다.

### 포함 관계와 쓰기

- 상위 층의 데이터가 하위 층에도 반드시 있는지(포함, inclusive) 아닌지(배타, exclusive)는 설계마다 다르다.
- 쓰기를 즉시 아래 층에 반영할지(write-through), 나중에 쫓겨날 때 반영할지(write-back)도 설계 선택이다. 다음 글(#093)에서 다룬다.

### 작업 집합

프로그램이 일정 시간 동안 실제로 만지는 데이터의 크기를 작업 집합이라 한다. 작업 집합이 어느 층에 들어가느냐가 성능을 좌우한다. 같은 알고리즘이라도 데이터가 L2 에 들어가는 동안은 빠르다가, L3 를 넘는 순간 DRAM 속도로 떨어진다.

## 직접 해 보기

작업 집합 크기를 바꿔 가며 접근당 시간을 잰다. 다음 주소가 이번에 읽은 값에 들어 있는 "포인터 추적" 방식이라 CPU 가 접근을 겹치거나 미리 가져올 수 없다. 순서를 무작위로 섞어 프리페처도 무력화했다.

```c
/* chase.c — 작업 집합 크기별 메모리 접근 지연(포인터 추적) */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
int main(void) {
    for (size_t kb = 16; kb <= 128 * 1024; kb *= 4) {
        size_t n = kb * 1024 / sizeof(size_t);
        size_t *next = malloc(n * sizeof *next), *perm = malloc(n * sizeof *perm);
        for (size_t i = 0; i < n; i++) perm[i] = i;
        srand(42);
        for (size_t i = n - 1; i > 0; i--) {          /* 무작위 순열: 프리페처 무력화 */
            size_t j = ((size_t)rand() * RAND_MAX + rand()) % (i + 1);
            size_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
        }
        for (size_t i = 0; i < n; i++) next[perm[i]] = perm[(i + 1) % n];
        size_t p = 0, steps = 20 * 1000 * 1000;
        struct timespec t0, t1;
        clock_gettime(CLOCK_MONOTONIC, &t0);
        for (size_t s = 0; s < steps; s++) p = next[p];   /* 앞 결과가 다음 주소 */
        clock_gettime(CLOCK_MONOTONIC, &t1);
        double ns = ((t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec)) / steps;
        printf("%8zu KB  %6.1f ns/access  (p=%zu)\n", kb, ns, p % 10);
        free(next); free(perm);
    }
    return 0;
}
```

```bash
gcc -O2 chase.c -o chase && ./chase
```

2코어 노트북급 x86-64 CPU(코어당 L1d 32KB, L2 256KB, 공유 L3 4MB)에서 한 번 측정한 결과다.

```
      16 KB     2.2 ns/access  (p=4)
      64 KB     4.0 ns/access  (p=6)
     256 KB     8.7 ns/access  (p=0)
    1024 KB    18.0 ns/access  (p=6)
    4096 KB    76.3 ns/access  (p=4)
   16384 KB   103.2 ns/access  (p=2)
   65536 KB   132.2 ns/access  (p=6)
```

16KB 는 L1 에 들어가 약 2ns 다. 64KB 부터 L1 을 넘고, 1MB 는 L3 에 머물러 18ns, L3(4MB)에 꽉 차는 4MB 부터 급격히 늘어 64MB 에서는 130ns 대다. 계단 모양이 캐시 층과 맞아떨어진다. 큰 크기에서는 캐시 미스뿐 아니라 TLB 미스(#095)도 함께 더해진다. 출력의 `p` 는 컴파일러가 반복문을 지우지 못하게 결과를 쓰는 용도다. 수치는 CPU 와 부하에 따라 달라진다.

## 현업에서는

- **자료구조 선택**: 연결 리스트와 트리 노드는 메모리 곳곳에 흩어져 포인터 추적이 된다. 같은 O(n) 순회라도 연속 배열이 몇 배 빠른 경우가 흔하다. 해시 테이블도 개방 주소법이 캐시에 더 친화적인 경우가 많다.
- **DB 와 캐시 계층**: 데이터베이스의 버퍼 풀, 레디스 같은 인메모리 캐시, CDN 은 모두 소프트웨어로 만든 메모리 계층이다. "핫 데이터가 메모리에 다 들어가는가" 가 지연 시간을 정한다. 디스크에 닿는 순간 자릿수가 바뀐다.
- **컨테이너 메모리 한도**: 쿠버네티스 파드의 메모리 limit 을 작업 집합보다 작게 잡으면 페이지 캐시가 밀려나고 디스크 I/O 가 늘어 느려지며, 더 줄이면 OOM 으로 죽는다. 홈랩 노드처럼 메모리가 넉넉하지 않은 환경에서는 작업 집합을 실측해 limit 을 잡는 것이 안전하다.

## 확인 문제

1. 시간 지역성과 공간 지역성의 예를 하나씩 들어라.
2. 적중 시간 2ns, 미스율 10%, 미스 패널티 80ns 인 캐시의 AMAT 는.
3. 캐시가 한 바이트가 필요해도 64바이트를 가져오는 이유는.
4. 위 실험에서 4MB 부근에서 지연이 급격히 늘어난 이유는.

### 풀이

1. 시간: 반복문의 카운터 변수를 매번 읽는다. 공간: 배열을 인덱스 순서대로 순회한다.
2. 2 + 0.1 × 80 = 10ns.
3. 공간 지역성 때문에 주변 데이터를 곧 쓸 가능성이 높고, 한 번에 크게 가져오는 편이 여러 번 가져오는 것보다 효율적이기 때문이다.
4. 작업 집합이 L3 캐시 용량(4MB)에 닿아 대부분의 접근이 DRAM 까지 내려가기 시작했기 때문이다.

## 더 읽을거리 (References)

- Ulrich Drepper, [What Every Programmer Should Know About Memory](https://akkadia.org/drepper/cpumemory.pdf), 2007
- [Computer Systems: A Programmer's Perspective — 저자 공식 사이트](https://csapp.cs.cmu.edu/) (6장 메모리 계층)
- Kubernetes Documentation, [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- John L. Hennessy, David A. Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed., Morgan Kaufmann. 2장.
