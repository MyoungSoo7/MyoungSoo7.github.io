---
layout: post
title: "[CS300 #098] 멀티코어와 SIMD — 코어를 늘리는 병렬성과 데이터를 넓히는 병렬성"
date: 2026-10-10 19:38:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, multicore, simd, vectorization]
---

컴퓨터공학 300 주제 시리즈의 098번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

멀티코어는 독립적인 명령어 흐름을 여러 개 동시에 돌리는 병렬성(MIMD)이고, SIMD 는 명령어 하나로 여러 데이터 원소를 한꺼번에 처리하는 병렬성이다. 하나는 스레드·프로세스로, 다른 하나는 벡터 레지스터와 컴파일러 벡터화로 얻는다. 둘은 서로 다른 축이라 곱해서 쓸 수 있다.

## 왜 필요한가

2000년대 중반 이후 단일 코어의 클록 주파수는 전력과 발열 때문에 예전처럼 오르지 않게 됐다. 칩 제조사는 늘어난 트랜지스터를 코어 수와 벡터 폭에 썼다. 그 결과 "기다리면 공짜로 빨라지는" 시대가 끝났다. 소프트웨어가 병렬성을 직접 드러내야 새 하드웨어의 성능을 쓸 수 있다.

이 글의 실험에서 같은 C 반복문이 컴파일 옵션만으로 약 11배 빨라지고(SIMD), 같은 파이썬 작업이 프로세스 수를 늘려 약 2배 빨라진다(멀티코어). 그리고 "코어 4개면 4배" 가 왜 안 나오는지도 본다.

## 핵심 개념

### 플린의 분류

1966년 마이클 플린은 명령어 흐름과 데이터 흐름의 수로 컴퓨터를 나눴다.

| 분류 | 명령어 흐름 | 데이터 흐름 | 예 |
|---|---|---|---|
| SISD | 1 | 1 | 고전적 단일 코어 |
| SIMD | 1 | 여러 개 | CPU 벡터 명령, GPU 의 실행 방식 일부 |
| MISD | 여러 개 | 1 | 실용 사례 드묾 |
| MIMD | 여러 개 | 여러 개 | 멀티코어, 클러스터 |

현대 CPU 는 MIMD(코어 여러 개)이면서 각 코어가 SIMD 명령을 가진 혼합형이다.

### 멀티코어 구조

```
┌──────────────── CPU 패키지 ────────────────┐
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│
│ │ 코어 0  │ │ 코어 1  │ │ 코어 2  │ │ 코어 3  ││
│ │ L1  L2 │ │ L1  L2 │ │ L1  L2 │ │ L1  L2 ││
│ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘│
│     └──────────┴────┬─────┴──────────┘     │
│                ┌────┴────┐                 │
│                │ 공유 L3  │                 │
│                └────┬────┘                 │
└─────────────────────┼──────────────────────┘
                 메모리 컨트롤러 ─ DRAM
```

- 코어마다 파이프라인·레지스터·L1(대개 L2 도)을 따로 갖고, L3 와 메모리 대역폭은 나눠 쓴다.
- 캐시 일관성 프로토콜(#094)이 코어들의 캐시를 맞춘다.
- **동시 멀티스레딩(SMT, 인텔의 하이퍼스레딩)**: 물리 코어 하나가 하드웨어 스레드 2개(이상)를 번갈아·동시에 실행한다. 한 스레드가 메모리를 기다리는 동안 다른 스레드가 실행 자원을 쓴다. 논리 CPU 수는 늘지만 실행 자원은 그대로라 성능은 2배가 되지 않는다.
- **NUMA**: 소켓이 여러 개인 서버에서는 각 소켓에 붙은 메모리가 따로 있어서, 다른 소켓의 메모리에 접근하면 더 느리다.

### 멀티코어의 한계

- 일을 나눌 수 있어야 한다. 순차 부분은 그대로 남는다(암달의 법칙, #100).
- 공유 자원(메모리 대역폭, L3, 락)에서 경합한다.
- 스레드 생성, 데이터 분배, 결과 합치기 비용이 든다.
- 거짓 공유(#094) 같은 하드웨어 수준 충돌.

### SIMD: 레지스터를 넓힌다

SIMD 명령은 넓은 벡터 레지스터에 원소 여러 개를 담아 한 번에 연산한다.

```
스칼라:  a0*b0  →  c0          (명령어 1개 = 연산 1개)

SIMD(256비트, float 8개):
 ┌──┬──┬──┬──┬──┬──┬──┬──┐
 │a0│a1│a2│a3│a4│a5│a6│a7│
 └──┴──┴──┴──┴──┴──┴──┴──┘
            ×                  (명령어 1개 = 연산 8개)
 ┌──┬──┬──┬──┬──┬──┬──┬──┐
 │b0│b1│b2│b3│b4│b5│b6│b7│
 └──┴──┴──┴──┴──┴──┴──┴──┘
```

| ISA | 확장 | 레지스터 폭 | float32 개수 |
|---|---|---|---|
| x86-64 | SSE 계열 | 128비트 | 4 |
| x86-64 | AVX, AVX2 | 256비트 | 8 |
| x86-64 | AVX-512 | 512비트 | 16 |
| ARM | NEON | 128비트 | 4 |
| ARM | SVE/SVE2 | 구현에 따라 가변 | 가변 |
| RISC-V | V 확장 | 구현에 따라 가변 | 가변 |

SSE2 는 x86-64 의 기본 사양에 포함되므로, 특별한 옵션 없이 빌드한 x86-64 바이너리는 128비트 SIMD 까지 쓸 수 있다. AVX2 이상은 CPU 마다 지원 여부가 달라 명시적으로 켜야 한다.

### SIMD 를 쓰는 세 가지 길

1. **컴파일러 자동 벡터화**: 반복문을 분석해 자동으로 SIMD 명령을 만든다. 반복 사이 의존성, 포인터 별칭(aliasing), 분기가 있으면 실패한다.
2. **인트린직**: `_mm256_add_ps` 같은 C 함수 모양의 명령어를 직접 쓴다. 빠르지만 ISA 에 묶인다.
3. **라이브러리**: 넘파이, BLAS, 이미지·코덱 라이브러리는 내부에서 SIMD 를 쓴다. 넘파이는 실행 중에 CPU 기능을 감지해 맞는 구현을 고른다. 대부분의 개발자에게는 이 길이 가장 현실적이다.

## 직접 해 보기

### 1. SIMD: 같은 코드, 다른 컴파일 옵션

```c
#include <stdio.h>
#include <time.h>
#define N 4096
float a[N], b[N], c[N];
int main(void) {
    for (int i = 0; i < N; i++) { a[i] = i * 0.5f; b[i] = i * 0.25f; }
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int r = 0; r < 200000; r++) {
        for (int i = 0; i < N; i++)
            c[i] = a[i] * b[i] + c[i];         /* 같은 연산을 원소마다 */
        __asm__ volatile("" ::: "memory");      /* 반복이 합쳐지지 않게 */
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    printf("%.3f s  (c[100]=%g)\n",
           (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9, c[100]);
    return 0;
}
```

```bash
gcc -O2 -fno-tree-vectorize simd.c -o scalar
gcc -O2 -ftree-vectorize simd.c -o sse
gcc -O2 -ftree-vectorize -mavx2 -mfma simd.c -o avx2
```

AVX2 를 지원하는 x86-64 노트북급 CPU, gcc 13.3 에서 한 번 돌린 결과다.

```
scalar: 1.822 s  (c[100]=2.49654e+08)
sse:    0.306 s  (c[100]=2.49654e+08)
avx2:   0.157 s  (c[100]=2.49654e+08)
```

`objdump -d` 로 보면 scalar 는 원소 하나짜리 `mulss`, sse 는 4개짜리 `mulps`/`addps`, avx2 는 256비트 `ymm` 레지스터에서 곱셈과 덧셈을 한 번에 하는 `vfmadd132ps` 를 쓴다. 데이터 48KB 가 L1·L2 근처에 머물러 메모리 대역폭에 덜 묶였기 때문에 SIMD 효과가 크게 나왔다. 배열이 캐시보다 훨씬 크면 메모리 대역폭이 상한이 되어 차이가 줄어든다. FMA 는 반올림을 한 번만 하므로 일반적으로는 결과의 마지막 자리가 달라질 수 있다는 점도 기억해 둔다(#083).

### 2. 멀티코어: 프로세스 수 늘리기

```python
import os, time
from concurrent.futures import ProcessPoolExecutor

def work(n):                         # 순수 CPU 작업: 정수 연산 반복
    s = 0
    for i in range(n):
        s += i * i % 7
    return s

TASKS = [3_000_000] * 8
print("logical CPUs:", os.cpu_count())
base = None
for workers in (1, 2, 4):
    t = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        total = sum(ex.map(work, TASKS))
    dt = time.perf_counter() - t
    base = base or dt
    print(f"workers={workers}  {dt:.2f}s  speedup {base/dt:.2f}x  (total={total})")
```

출력(python3, 같은 노드):

```
logical CPUs: 4
workers=1  6.30s  speedup 1.00x  (total=47999992)
workers=2  3.47s  speedup 1.81x  (total=47999992)
workers=4  3.04s  speedup 2.07x  (total=47999992)
```

논리 CPU 는 4개인데 4배가 아니라 2배에서 멈췄다. 이 CPU 는 물리 코어 2개에 SMT 로 논리 CPU 4개를 만든 것이고, 다른 작업도 함께 돌던 노드였다. 물리 코어 수만큼은 거의 선형으로 늘었고, SMT 로 얻은 이득은 작았다. 파이썬은 GIL 때문에 CPU 작업을 스레드로 나눠도 동시에 돌지 않으므로 여기서는 프로세스를 썼다.

## 현업에서는

- **CPU 요청과 한도**: 쿠버네티스의 `cpu: 1` 은 논리 CPU 하나에 해당하는 CPU 시간이다. SMT 가 켜진 노드에서 논리 CPU 2개는 물리 코어 2개만큼의 성능이 아닐 수 있다. 성능 민감 파드는 CPU Manager `static` 정책으로 전용 코어를 받게 할 수 있다.
- **라이브러리를 믿어라**: 반복문을 파이썬으로 돌리지 말고 넘파이 벡터 연산으로 바꾸는 것만으로 SIMD 와 C 루프를 동시에 얻는다. 직접 인트린직을 쓰는 것은 측정으로 병목이 확인된 뒤에.
- **빌드 대상 주의**: `-mavx2`, `-march=native` 로 빌드한 이미지는 AVX2 가 없는 노드에서 `illegal instruction` 으로 죽는다. 세대가 섞인 클러스터에서는 기준 ISA 를 정하거나, 런타임에 기능을 감지해 분기하는 라이브러리를 쓴다.
- **스레드 수 설정**: BLAS·넘파이·PyTorch 등은 기본으로 보이는 CPU 수만큼 스레드를 띄우기도 한다. 컨테이너의 CPU limit 이 2 인데 노드 전체 코어 수만큼 스레드가 뜨면 스로틀링으로 오히려 느려진다. `OMP_NUM_THREADS` 같은 설정을 limit 에 맞춘다.

## 확인 문제

1. 플린 분류에서 멀티코어 CPU 와 SIMD 명령은 각각 무엇에 해당하는가.
2. 256비트 SIMD 레지스터에는 float32 가 몇 개, float64 가 몇 개 들어가는가.
3. 컴파일러 자동 벡터화가 실패하는 대표적 원인 두 가지는.
4. 논리 CPU 4개인 노드에서 CPU 작업이 4배 빨라지지 않을 수 있는 이유 두 가지는.

### 풀이

1. 멀티코어는 MIMD, SIMD 명령은 SIMD.
2. float32 8개, float64 4개.
3. 반복 사이의 데이터 의존성, 포인터 별칭 가능성(같은 메모리를 가리킬 수 있음), 반복문 안의 복잡한 분기 중 두 가지.
4. 논리 CPU 가 SMT 로 만들어져 물리 실행 자원을 공유하는 경우, 다른 작업과의 경합, 순차 부분·작업 분배 비용, 메모리 대역폭 같은 공유 자원 한계 중 두 가지.

## 더 읽을거리 (References)

- GCC, [Auto-vectorization in GCC](https://gcc.gnu.org/projects/tree-ssa/vectorization.html)
- LLVM, [Auto-Vectorization in LLVM](https://llvm.org/docs/Vectorizers.html)
- NumPy Documentation, [CPU/SIMD Optimizations](https://numpy.org/doc/stable/reference/simd/index.html)
- Kubernetes Documentation, [Control CPU Management Policies on the Node](https://kubernetes.io/docs/tasks/administer-cluster/cpu-management-policies/)
