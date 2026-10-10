---
layout: post
title: "[CS300 #106] 컨텍스트 스위칭 — CPU 가 작업을 갈아타는 비용"
date: 2026-10-10 19:46:00 +0900
categories: [cs]
tags: [cs300, operating-systems, context-switch, tlb, performance]
---

컴퓨터공학 300 주제 시리즈의 106번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

컨텍스트 스위칭은 커널이 현재 실행 중인 작업의 CPU 상태를 저장하고 다음 작업의 상태를 복원해 CPU 를 넘겨주는 과정이며, 직접 비용(레지스터 저장·복원)보다 캐시와 TLB 가 식는 간접 비용이 더 크게 작용하는 경우가 많다.

## 왜 필요한가

105번 글의 스케줄러는 "다음에 누구를 돌릴지"를 정한다. 실제로 CPU 를 넘겨주는 동작이 컨텍스트 스위칭이다. 선점형 멀티태스킹, 블로킹 I/O, 스레드 풀, 이벤트 루프가 모두 이 위에서 돈다.

공짜가 아니라는 점이 중요하다. 초당 수십만 번의 전환이 일어나는 서버는 일을 하는 시간보다 갈아타는 시간이 길어질 수 있다. 스레드를 무작정 늘렸는데 처리량이 오히려 떨어지는 현상, `vmstat` 의 `cs` 열이 비정상적으로 큰 상황을 이해하려면 이 비용을 알아야 한다.

## 핵심 개념

### 무엇을 저장하고 복원하나

| 항목 | 내용 |
|---|---|
| 범용 레지스터 | 계산 중간값 |
| 프로그램 카운터, 스택 포인터 | 어디까지 실행했는지, 스택이 어디인지 |
| 플래그 레지스터 | 비교 결과 등 |
| FPU/SIMD 레지스터 | 부동소수점·벡터 상태 (필요할 때 저장하는 최적화가 있다) |
| 주소 공간 | 다른 프로세스로 갈 때 페이지 테이블 루트(x86 의 CR3)를 교체 |
| 커널 스택 | 작업마다 별도의 커널 스택 |

리눅스에서 이 상태는 작업의 `task_struct` 와 커널 스택에 저장된다.

### 전환이 일어나는 순간

```
작업 A 실행 중 (사용자 모드)
   |
   | (1) 타이머 인터럽트, 시스템 콜, 예외
   v
커널 진입: A 의 사용자 레지스터를 A 의 커널 스택에 저장
   |
   | (2) 스케줄러: "다음은 B"
   v
switch_to(A, B): A 의 커널 레지스터 저장, B 의 것 복원
                 다른 프로세스라면 페이지 테이블 교체
   |
   | (3) B 의 커널 스택에서 복귀
   v
B 의 사용자 레지스터 복원 -> 사용자 모드로 복귀, B 실행 재개
```

전환의 계기는 둘로 나뉜다.

- **자발적 전환(voluntary)**: 작업이 스스로 CPU 를 내려놓는다. I/O 대기, `sleep`, 락 대기(`futex`), 파이프 읽기 등.
- **비자발적 전환(involuntary)**: 시간 조각을 다 썼거나 더 높은 우선순위 작업이 깨어나 커널이 선점한다.

리눅스는 이 두 횟수를 `/proc/PID/status` 의 `voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches` 로 보여 준다. 자발적 전환이 많으면 기다림이 많은 작업이고, 비자발적 전환이 많으면 CPU 경합이 심하다는 신호다.

### 직접 비용과 간접 비용

**직접 비용**은 레지스터 저장·복원, 스케줄러 코드 실행, 모드 전환이다. 현대 CPU 에서 마이크로초 수준이다.

**간접 비용**이 더 크다.

- **캐시 오염**: B 가 실행되는 동안 A 의 데이터가 L1/L2 캐시에서 밀려난다. A 가 돌아오면 캐시 미스를 다시 겪는다.
- **TLB 플러시**: 프로세스가 바뀌면 가상→물리 주소 변환 캐시(TLB)가 무효가 된다. x86 의 PCID, ARM 의 ASID 같은 태그 기능이 이 비용을 줄인다.
- **분기 예측기, 프리페처 상태** 도 식는다.

같은 프로세스의 스레드끼리 전환하면 주소 공간이 같으므로 페이지 테이블 교체와 TLB 플러시가 필요 없다. 스레드 전환이 프로세스 전환보다 싼 주된 이유다.

### 모드 전환과는 다르다

시스템 콜은 **모드 전환**(사용자 → 커널 → 사용자)이지 컨텍스트 스위칭이 아니다. 같은 작업이 커널에 잠깐 들어갔다 나올 뿐이다. 시스템 콜 안에서 작업이 잠들어야 할 때에야 컨텍스트 스위칭이 일어난다.

### 사용자 공간 전환

Go 고루틴, 코루틴, `asyncio` 태스크는 커널이 아니라 언어 런타임이 전환한다. 저장할 상태가 적고 커널 진입이 없어서 훨씬 싸다. 대신 런타임이 블로킹 시스템 콜을 피하거나 별도 스레드로 넘기는 장치를 갖춰야 한다.

## 직접 해 보기

두 프로세스가 파이프 두 개로 1바이트를 주고받는 "핑퐁"이다. 한쪽이 `read` 에서 잠들고 다른 쪽이 `write` 로 깨우므로 왕복마다 전환이 일어난다.

```python
import os, time, resource

N = 50_000
p2c_r, p2c_w = os.pipe()     # 부모 -> 자식
c2p_r, c2p_w = os.pipe()     # 자식 -> 부모

pid = os.fork()
if pid == 0:
    for _ in range(N):
        os.read(p2c_r, 1)        # 부모가 보낼 때까지 잠든다
        os.write(c2p_w, b"y")    # 부모를 깨운다
    os._exit(0)

before = resource.getrusage(resource.RUSAGE_SELF)
t = time.perf_counter()
for _ in range(N):
    os.write(p2c_w, b"x")
    os.read(c2p_r, 1)
dt = time.perf_counter() - t
after = resource.getrusage(resource.RUSAGE_SELF)
os.waitpid(pid, 0)

print(f"왕복 {N}회: {dt:.2f}s, 왕복당 {dt / N * 1e6:.1f} us")
print("부모의 자발적 전환  :", after.ru_nvcsw - before.ru_nvcsw)
print("부모의 비자발적 전환:", after.ru_nivcsw - before.ru_nivcsw)
with open("/proc/self/status") as f:
    print("".join(l for l in f if "ctxt_switches" in l), end="")
```

4코어 리눅스 노트북의 결과다.

```
왕복 50000회: 1.08s, 왕복당 21.6 us
부모의 자발적 전환  : 47482
부모의 비자발적 전환: 1963
voluntary_ctxt_switches:	47482
nonvoluntary_ctxt_switches:	1990
```

왕복 5만 번에 부모의 자발적 전환이 약 4만 7천 번이다. 거의 매 왕복마다 부모가 `read` 에서 잠들었다는 뜻이다. 일부 왕복에서는 자식의 응답이 이미 와 있어 잠들 필요가 없었다. 왕복당 약 20µs 에는 파이썬 인터프리터 비용, 시스템 콜 네 번, 전환 두 번이 모두 들어 있다. 두 프로세스를 `taskset -c 0 python3 ...` 으로 한 코어에 묶으면 비자발적 전환 비율이 크게 늘어나는 것도 관찰할 수 있다. `resource.getrusage` 의 `ru_nvcsw`, `ru_nivcsw` 가 `/proc` 의 값과 일치한다는 것도 확인하자.

## 현업에서는

- **`vmstat 1` 의 `cs` 열**: 초당 전체 컨텍스트 스위치 수다. 평소 값을 알아 두어야 이상치를 판단할 수 있다. 갑자기 몇 배로 뛰면 락 경합, 과도한 스레드 수, 아주 작은 단위의 I/O 를 의심한다.
- **`pidstat -w`**: 프로세스별 초당 자발적(`cswch/s`)·비자발적(`nvcswch/s`) 전환을 보여 준다. 비자발적이 높으면 CPU 가 모자라거나 cgroup CPU 쿼터에 걸려 있다.
- **스레드 풀 크기**: CPU 집약 작업의 스레드 수를 코어 수보다 훨씬 크게 잡으면 비자발적 전환만 늘어난다. 보통 코어 수 근처에서 시작해 측정으로 조정한다.
- **이벤트 루프 모델**: nginx, Node.js, Redis 가 적은 수의 스레드로 많은 연결을 처리하는 이유 중 하나가 컨텍스트 스위칭 회피다. `epoll` 로 준비된 소켓만 골라 처리하므로 연결마다 스레드를 재우고 깨울 필요가 없다.

## 확인 문제

1. 시스템 콜 한 번과 컨텍스트 스위칭 한 번의 차이는 무엇인가?
2. 같은 프로세스의 스레드 간 전환이 다른 프로세스 간 전환보다 싼 이유는?
3. 자발적 전환과 비자발적 전환의 예를 하나씩 들어라.
4. 컨텍스트 스위칭의 간접 비용 두 가지를 설명하라.
5. 위 실험에서 부모의 자발적 전환 수가 왕복 수보다 약간 적은 이유는?

### 풀이

1. 시스템 콜은 같은 작업이 사용자 모드와 커널 모드를 오가는 모드 전환이다. 컨텍스트 스위칭은 CPU 가 실행하는 작업 자체를 바꾸는 것이다.
2. 주소 공간이 같아서 페이지 테이블 교체와 TLB 무효화가 필요 없고, 캐시 내용도 일부 공유되기 때문이다.
3. 자발적: 디스크 읽기를 기다리며 잠듦. 비자발적: 시간 조각을 다 써서 스케줄러가 선점함.
4. 캐시 오염(돌아왔을 때 캐시 미스 증가)과 TLB 무효화(주소 변환을 다시 채워야 함).
5. 부모가 `read` 를 호출한 시점에 자식의 응답이 이미 파이프에 도착해 있으면 잠들지 않고 바로 읽기 때문이다.

## 더 읽을거리 (References)

- OSTEP, [Mechanism: Limited Direct Execution (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-mechanisms.pdf) — 타이머 인터럽트와 문맥 저장
- Linux man-pages, [getrusage(2)](https://manpages.debian.org/bookworm/manpages-dev/getrusage.2.en.html) — `ru_nvcsw`, `ru_nivcsw`
- Linux man-pages, [proc(5)](https://manpages.debian.org/bookworm/manpages/proc.5.en.html) — `/proc/PID/status` 의 전환 횟수
- Linux man-pages, [vmstat(8)](https://manpages.debian.org/bookworm/procps/vmstat.8.en.html)
