---
layout: post
title: "[CS300 #091] 해저드와 분기 예측 — 파이프라인이 멈추는 세 가지 이유"
date: 2026-10-10 19:31:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, pipeline-hazard, branch-prediction, forwarding]
---

컴퓨터공학 300 주제 시리즈의 091번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

해저드는 파이프라인에서 다음 명령어를 다음 사이클에 진행시킬 수 없는 상황이다. 부품 충돌(구조), 앞 결과 의존(데이터), 분기 방향 미정(제어) 세 종류가 있고, 각각 자원 분리, 포워딩, 분기 예측으로 대응한다. 분기 예측이 틀리면 투기적으로 실행한 일을 버려야 하므로, 예측하기 어려운 분기는 실제로 측정 가능한 만큼 느리다.

## 왜 필요한가

앞 글(#090)의 이상적인 파이프라인은 매 사이클 명령어 하나를 끝냈다. 실제 프로그램은 앞 명령어의 결과를 바로 쓰고, `if` 와 반복문으로 가득하다. 이 의존성이 파이프라인을 멈춘다.

이 글의 "직접 해 보기" 에서 C 프로그램 하나를 돌려 본다. 같은 데이터, 같은 코드인데 데이터를 정렬해 두기만 해도 반복문이 몇 배 빨라진다. 이유는 분기 예측이다. 하드웨어 동작을 모르면 이 현상은 설명할 수 없다.

## 핵심 개념

### 1. 구조 해저드

두 명령어가 같은 사이클에 같은 하드웨어 자원을 쓰려 할 때 생긴다. 예를 들어 메모리가 하나뿐이면 IF 단계(명령어 읽기)와 MEM 단계(데이터 읽기)가 충돌한다. 해결은 자원을 늘리는 것이다. 명령어 캐시와 데이터 캐시를 나누는 이유 중 하나다(#086 수정 하버드 구조). 현대 설계에서는 대부분 설계 단계에서 없앤다.

### 2. 데이터 해저드

뒤 명령어가 앞 명령어의 결과를 필요로 하는데 그 결과가 아직 레지스터에 쓰이지 않았을 때 생긴다.

```
add  x1, x2, x3     # x1 은 WB(5사이클째)에 쓰인다
sub  x4, x1, x5     # 그런데 ID(3사이클째)에서 x1 을 읽으려 한다
```

대응 방법은 다음과 같다.

| 방법 | 내용 |
|---|---|
| 스톨(버블) | 결과가 준비될 때까지 뒤 명령어를 멈춘다. 가장 단순, 가장 느림 |
| 포워딩(바이패싱) | EX 단계가 끝나자마자 ALU 결과를 다음 명령어의 EX 입력으로 바로 넘긴다. 레지스터 파일을 거치지 않음 |
| 명령어 재배치 | 컴파일러나 하드웨어(비순차 실행)가 의존 없는 명령어를 사이에 끼워 넣는다 |

포워딩으로도 못 막는 경우가 있다. **적재-사용 해저드**다.

```
lw   x1, 0(x2)      # x1 은 MEM 단계 끝에야 나온다
add  x4, x1, x5     # 바로 다음 EX 에서 필요 → 1사이클 스톨 불가피
```

메모리에서 오는 값은 ALU 결과보다 한 단계 늦게 나오기 때문이다. 캐시 미스라면 수십~수백 사이클을 기다린다.

### 3. 제어 해저드

분기 명령어는 EX 단계쯤에서야 조건과 목적지가 확정된다. 그 사이 IF 는 다음에 무엇을 가져와야 할지 모른다.

- 기다리기: 분기마다 몇 사이클을 버린다. 분기는 흔하므로 손해가 크다.
- **예측하기**: 방향과 목적지를 추측해 그 길로 계속 가져와 실행한다(투기적 실행). 맞으면 손실 없음, 틀리면 그동안 실행한 명령어를 버리고(flush) 올바른 경로로 다시 시작한다.

깊고 넓은 현대 파이프라인에서 예측 실패 한 번은 수십 개 명령어 슬롯을 버리는 것과 같다. 정확한 손실 사이클은 마이크로아키텍처마다 다르다.

### 분기 예측기

| 방식 | 원리 | 특징 |
|---|---|---|
| 정적 예측 | "뒤로 가는 분기는 taken, 앞으로 가는 분기는 not taken" 같은 고정 규칙 | 반복문에 잘 맞음 |
| 1비트 | 직전 결과를 그대로 따라 예측 | 반복문 끝에서 두 번 틀림 |
| 2비트 포화 카운터 | 0~3 카운터. 두 번 연속 틀려야 예측이 바뀜 | 반복문 끝에서 한 번만 틀림 |
| 상관·전역 이력 | 최근 여러 분기의 결과 패턴을 함께 보고 예측 | 번갈아 나오는 패턴도 학습 |
| BTB | 분기 명령어 주소 → 목적지 주소 캐시 | 방향뿐 아니라 "어디로" 도 미리 앎 |

현대 CPU 의 예측기는 이보다 훨씬 정교하지만, 기본 원리는 "과거 패턴이 반복될 것" 이라는 가정이다. 그래서 **무작위 데이터에 의존하는 분기**는 어떤 예측기도 잘 맞히지 못한다.

### 분기를 없애기

예측이 어려운 분기는 아예 없애는 방법이 있다. 조건부 이동(`cmov`)처럼 두 값을 다 계산해 두고 조건으로 고르는 명령어를 쓰면 분기 자체가 사라진다. 컴파일러는 이 변환(if-conversion)을 자동으로 하기도 한다.

### 투기적 실행의 그림자: Spectre

예측이 틀려 버린 명령어도 캐시 상태 같은 흔적을 남긴다. 2018년 공개된 Spectre 계열 취약점은 이 흔적을 측정해 접근 권한이 없는 메모리 내용을 유추할 수 있음을 보였다. 리눅스 커널은 이에 대한 여러 완화책을 갖고 있으며, 일부는 성능 비용을 동반한다. 성능 최적화 기법이 보안 문제로 이어진 대표 사례다.

## 직접 해 보기

### 1. 예측기 흉내

python3 로 실행해 확인했다.

```python
import random

def one_bit(seq):
    state, hit = 1, 0                      # 1 = taken 으로 예측
    for t in seq:
        hit += (state == t)
        state = t                          # 직전 결과를 그대로 따라감
    return hit / len(seq)

def two_bit(seq):
    c, hit = 2, 0                          # 0,1 = not taken / 2,3 = taken
    for t in seq:
        hit += ((c >= 2) == t)
        c = min(c + 1, 3) if t else max(c - 1, 0)   # 포화 카운터
    return hit / len(seq)

random.seed(0)
loop = ([1] * 9 + [0]) * 1000                   # 10번 도는 반복문의 분기
alt = [1, 0] * 5000                             # 번갈아
rnd = [random.randint(0, 1) for _ in range(10000)]
srt = sorted(rnd)                               # 정렬된 데이터의 if 분기

for name, s in [("loop", loop), ("alternate", alt), ("random", rnd), ("sorted", srt)]:
    print(f"{name:10s} 1-bit {one_bit(s):.3f}  2-bit {two_bit(s):.3f}")
```

출력:

```
loop       1-bit 0.800  2-bit 0.900
alternate  1-bit 0.000  2-bit 0.500
random     1-bit 0.503  2-bit 0.501
sorted     1-bit 1.000  2-bit 1.000
```

반복문 분기는 2비트가 1비트보다 낫다. 번갈아 나오는 패턴은 단순 카운터로는 못 잡고 이력 기반 예측기가 필요하다. 무작위는 무엇으로도 50% 다. 정렬하면 거의 100% 가 된다.

### 2. 실제 CPU 에서 측정

같은 반복문을 정렬 전후로 돌린다.

```c
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#define N 1000000
static int cmp(const void *a, const void *b) { return *(int*)a - *(int*)b; }
static double run(const int *d) {
    struct timespec t0, t1;
    long long sum = 0;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int r = 0; r < 100; r++)
        for (int i = 0; i < N; i++)
            if (d[i] >= 128) sum += d[i];      /* 데이터에 따라 갈리는 분기 */
    clock_gettime(CLOCK_MONOTONIC, &t1);
    printf("  sum=%lld ", sum);
    return (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
}
int main(void) {
    int *d = malloc(N * sizeof *d);
    srand(1);
    for (int i = 0; i < N; i++) d[i] = rand() % 256;
    printf("unsorted: %.3f s\n", run(d));
    qsort(d, N, sizeof *d, cmp);
    printf("sorted:   %.3f s\n", run(d));
    return 0;
}
```

```bash
gcc -O1 -fno-if-conversion -fno-if-conversion2 br.c -o br && ./br
```

x86-64 리눅스 노드(gcc 13.3)에서 한 번 돌린 결과다.

```
  sum=9588797900 unsorted: 0.633 s
  sum=9588797900 sorted:   0.126 s
```

합계는 같은데 정렬된 쪽이 약 5배 빨랐다. 다른 작업이 함께 돌던 노드라 반복할 때마다 수치가 흔들렸지만 정렬 쪽이 몇 배 빠르다는 경향은 매번 같았다. 정확한 배율은 CPU 와 부하에 따라 다르다.

흥미로운 점이 있다. if-conversion 끄는 옵션 없이 `-O1` 로만 컴파일하면 gcc 가 이 분기를 `cmovg`(조건부 이동)로 바꿔 버려 두 경우의 시간 차이가 사라졌다. 분기가 없으면 예측할 것도 없다.

## 현업에서는

- **데이터 의존 분기를 의심한다**: 핫 루프의 `if` 가 무작위 데이터에 따라 갈리면 예측 실패가 성능을 갉아먹는다. 리눅스 `perf stat` 의 `branch-misses` 비율로 확인할 수 있다. 데이터를 정렬하거나, 분기 없는 산술로 바꾸거나, 조건별로 데이터를 미리 나눈다.
- **likely/unlikely 힌트**: 리눅스 커널 코드의 `likely()`, `unlikely()` 매크로는 컴파일러에 분기 방향 힌트를 줘서 자주 가는 경로를 일직선 코드로 배치하게 한다.
- **보안 패치와 성능**: Spectre·Meltdown 완화책 적용 후 시스템 콜이 잦은 워크로드의 성능이 떨어졌다는 보고가 많았다. 노드의 완화 상태는 `/sys/devices/system/cpu/vulnerabilities/` 아래 파일로 확인할 수 있다. 홈랩 클러스터에서 노드 간 성능 차이를 비교할 때 이 값도 같이 본다.

## 확인 문제

1. 해저드의 세 종류와 각각의 대표 해결책을 적어라.
2. 포워딩으로 해결할 수 없는 데이터 해저드는 무엇이고 왜 그런가.
3. 10번 도는 반복문의 분기에서 1비트 예측기와 2비트 예측기의 정확도는 각각 얼마인가(반복문이 계속 재실행된다고 가정).
4. 정렬된 배열에서 `if (x >= 128)` 반복문이 빨라지는 이유는.

### 풀이

1. 구조 해저드(자원 분리), 데이터 해저드(포워딩·스톨·재배치), 제어 해저드(분기 예측·투기적 실행).
2. 적재-사용 해저드. 적재 값은 MEM 단계가 끝나야 나오므로 바로 다음 명령어의 EX 단계에 넘겨 줄 수 없어 최소 1사이클 스톨이 필요하다.
3. 1비트는 반복문의 마지막과 다음 실행의 첫 번째에서 두 번 틀려 80%, 2비트는 마지막에서 한 번만 틀려 90%.
4. 분기 결과가 앞부분은 계속 not taken, 뒷부분은 계속 taken 이 되어 예측기가 거의 항상 맞히기 때문이다.

## 더 읽을거리 (References)

- Paul Kocher 외, [Spectre Attacks: Exploiting Speculative Execution](https://spectreattack.com/spectre.pdf), IEEE S&P 2019
- Linux Kernel Documentation, [Spectre Side Channels](https://docs.kernel.org/admin-guide/hw-vuln/spectre.html)
- GCC 공식 문서, [Options That Control Optimization](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) (`-fif-conversion`)
- Agner Fog, [The microarchitecture of Intel, AMD and VIA CPUs](https://www.agner.org/optimize/microarchitecture.pdf) (분기 예측 실측 정리)
