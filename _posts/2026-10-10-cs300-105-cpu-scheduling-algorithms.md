---
layout: post
title: "[CS300 #105] CPU 스케줄링 알고리즘 — 다음에 누구를 돌릴 것인가"
date: 2026-10-10 19:45:00 +0900
categories: [cs]
tags: [cs300, operating-systems, scheduling, round-robin, eevdf]
---

컴퓨터공학 300 주제 시리즈의 105번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

CPU 스케줄러는 실행 대기 중인 작업 가운데 다음에 CPU 를 줄 대상을 고르는 정책이며, 반환 시간·응답 시간·공정성 가운데 무엇을 우선하느냐에 따라 FCFS, SJF, RR, MLFQ, 비례 배분(CFS·EEVDF) 같은 알고리즘이 갈린다.

## 왜 필요한가

실행 가능한 작업은 늘 코어 수보다 많다. 4코어 서버에서 `R` 상태 작업이 20개라면, 매 순간 16개는 기다려야 한다. 누구를 먼저 돌리느냐에 따라 같은 하드웨어에서도 체감 성능이 크게 달라진다.

- 터미널에서 키를 눌렀는데 0.5초 뒤에 글자가 찍히면 사용자는 느리다고 느낀다(응답 시간).
- 야간 배치는 언제 시작하든 전체가 빨리 끝나는 것이 중요하다(반환 시간).
- 여러 사용자가 같은 서버를 쓰면 한 사람이 CPU 를 독차지하면 안 된다(공정성).

이 목표들은 서로 충돌한다. 스케줄링 알고리즘은 그 사이에서 하나를 고르는 방법이다.

## 핵심 개념

### 측정 지표

| 지표 | 정의 |
|---|---|
| 반환 시간(turnaround) | 완료 시각 − 도착 시각 |
| 대기 시간(waiting) | 준비 큐에서 기다린 시간의 합 = 반환 시간 − 실행 시간 |
| 응답 시간(response) | 처음 CPU 를 받은 시각 − 도착 시각 |
| 처리량(throughput) | 단위 시간당 완료한 작업 수 |

### 고전 알고리즘

**FCFS(First-Come, First-Served)**: 도착 순서대로 끝까지 실행한다. 단순하지만 긴 작업 뒤에 짧은 작업이 줄을 서면 모두가 오래 기다린다. 이것을 **호위 효과(convoy effect)** 라고 부른다.

**SJF(Shortest Job First)**: 남은 실행 시간이 가장 짧은 작업부터 돌린다. 모든 작업이 동시에 도착하고 실행 시간을 미리 안다면 평균 대기 시간을 최소화한다는 것이 증명되어 있다. 선점형 버전은 **SRTF(Shortest Remaining Time First)** 라 한다. 문제는 실행 시간을 미리 알 수 없다는 것과, 긴 작업이 계속 밀려 **기아(starvation)** 에 빠질 수 있다는 것이다.

**RR(Round Robin)**: 작업마다 시간 조각(time quantum)을 주고, 다 쓰면 큐 맨 뒤로 보낸다. 응답 시간이 좋지만 반환 시간은 나빠질 수 있다. 시간 조각이 너무 작으면 컨텍스트 스위칭 비용이 커지고, 너무 크면 FCFS 와 같아진다.

**우선순위 스케줄링**: 우선순위가 높은 작업부터 돌린다. 낮은 우선순위의 기아를 막기 위해 오래 기다린 작업의 우선순위를 올려 주는 **에이징(aging)** 을 함께 쓴다.

### MLFQ — 미래를 모를 때 과거로 추측한다

**MLFQ(Multi-Level Feedback Queue)** 는 우선순위가 다른 큐 여러 개를 두고, 작업의 행동을 보고 큐를 옮긴다.

```
 Q2 (높음, 짧은 조각)  [대화형 작업들]
 Q1 (중간)             [  ...  ]
 Q0 (낮음, 긴 조각)    [CPU 를 오래 쓰는 작업들]
```

- 새 작업은 가장 높은 큐에서 시작한다.
- 시간 조각을 다 쓰면 한 단계 내려간다(CPU 집약으로 추정).
- 일정 주기마다 모든 작업을 맨 위로 올린다(기아 방지).

짧고 대화형인 작업은 자연스럽게 위에 남고, 긴 계산 작업은 아래로 내려간다. 실행 시간을 몰라도 SJF 와 비슷한 효과를 낸다. 고전 유닉스, Solaris, Windows 계열 스케줄러가 이 아이디어를 바탕으로 한다.

### 비례 배분: 리눅스 CFS 와 EEVDF

리눅스의 일반 작업 스케줄러는 오랫동안 **CFS(Completely Fair Scheduler)** 였다. CFS 는 각 작업이 받은 CPU 시간을 가중치로 나눈 **가상 실행 시간(vruntime)** 을 기록하고, vruntime 이 가장 작은 작업을 다음에 실행한다. 작업들은 vruntime 기준 레드-블랙 트리에 정렬된다. nice 값이 낮을수록(우선순위가 높을수록) 가중치가 커서 vruntime 이 천천히 증가하므로 CPU 를 더 많이 받는다.

리눅스 커널 문서에 따르면 커널은 6.6 버전부터 CFS 를 **EEVDF(Earliest Eligible Virtual Deadline First)** 로 옮기기 시작했다. EEVDF 도 CPU 시간을 가중치에 따라 공정하게 나누는 것이 목표지만, 각 작업에 "받을 자격이 있는가(eligible)"와 "가상 마감 시각(virtual deadline)"을 계산해 마감이 가장 이른 자격 있는 작업을 고른다. 지연에 민감한 작업이 더 짧은 시간 조각을 요청할 수 있다는 점이 특징이다.

### 스케줄링 클래스

리눅스는 정책별 클래스를 우선순위 순으로 둔다(`sched(7)`).

| 정책 | 용도 |
|---|---|
| `SCHED_DEADLINE` | 주기·실행 시간·마감을 명시하는 실시간 작업 |
| `SCHED_FIFO`, `SCHED_RR` | 고정 우선순위 실시간 작업 |
| `SCHED_OTHER`(`SCHED_NORMAL`), `SCHED_BATCH`, `SCHED_IDLE` | 일반 작업 (CFS/EEVDF) |

실시간 클래스 작업이 실행 가능하면 일반 작업보다 항상 먼저 실행된다.

## 직접 해 보기

네 작업을 FCFS, SJF(비선점), RR 로 돌리는 작은 시뮬레이터다.

```python
from collections import deque

# (이름, 도착 시각, 필요한 CPU 시간)
JOBS = [("A", 0, 8), ("B", 1, 4), ("C", 2, 9), ("D", 3, 5)]

def report(name, finish, first_run):
    tat = [finish[n] - a for n, a, _ in JOBS]           # 반환 시간
    wait = [finish[n] - a - b for n, a, b in JOBS]      # 대기 시간
    resp = [first_run[n] - a for n, a, _ in JOBS]       # 응답 시간
    avg = lambda xs: sum(xs) / len(xs)
    print(f"{name:10s} 평균 반환 {avg(tat):5.2f}  평균 대기 {avg(wait):5.2f}  평균 응답 {avg(resp):5.2f}")

def fcfs():
    t, fin, first = 0, {}, {}
    for n, a, b in sorted(JOBS, key=lambda j: j[1]):
        t = max(t, a); first[n] = t; t += b; fin[n] = t
    return fin, first

def sjf():   # 비선점: 도착한 것 중 가장 짧은 것
    t, fin, first, left = 0, {}, {}, list(JOBS)
    while left:
        ready = [j for j in left if j[1] <= t] or [min(left, key=lambda j: j[1])]
        n, a, b = min(ready, key=lambda j: j[2])
        t = max(t, a); first[n] = t; t += b; fin[n] = t; left.remove((n, a, b))
    return fin, first

def rr(q):
    t, fin, first = 0, {}, {}
    rem = {n: b for n, _, b in JOBS}
    pending = deque(sorted(JOBS, key=lambda j: j[1])); queue = deque()
    while pending or queue:
        while pending and pending[0][1] <= t: queue.append(pending.popleft()[0])
        if not queue: t = pending[0][1]; continue
        n = queue.popleft(); first.setdefault(n, t)
        run = min(q, rem[n]); t += run; rem[n] -= run
        while pending and pending[0][1] <= t: queue.append(pending.popleft()[0])
        if rem[n]: queue.append(n)
        else: fin[n] = t
    return fin, first

report("FCFS", *fcfs())
report("SJF", *sjf())
report("RR(q=1)", *rr(1))
report("RR(q=4)", *rr(4))
report("RR(q=100)", *rr(100))
```

```
FCFS       평균 반환 15.25  평균 대기  8.75  평균 응답  8.75
SJF        평균 반환 14.25  평균 대기  7.75  평균 응답  7.75
RR(q=1)    평균 반환 19.00  평균 대기 12.50  평균 응답  0.75
RR(q=4)    평균 반환 18.25  평균 대기 11.75  평균 응답  4.50
RR(q=100)  평균 반환 15.25  평균 대기  8.75  평균 응답  8.75
```

FCFS 는 A(0–8) → B(8–12) → C(12–21) → D(21–26) 순서다. SJF 는 A 가 끝난 시점 8 에서 가장 짧은 B, 그다음 D, 마지막에 C 를 고르므로 반환·대기 시간이 가장 좋다. RR 은 시간 조각이 작을수록 응답 시간이 0 에 가까워지지만 반환 시간은 가장 나쁘다. 시간 조각을 아주 크게 잡은 RR(q=100)은 FCFS 와 똑같아진다. 이 시뮬레이터는 컨텍스트 스위칭 비용을 0 으로 두었다는 점에 주의하자. 실제로는 q 가 작을수록 그 비용이 더해진다.

## 현업에서는

- **nice 와 renice**: 백업이나 압축 같은 배치 작업은 `nice -n 19` 로 낮은 우선순위로 돌려 서비스 지연을 줄인다. 디스크 쪽은 `ionice` 로 비슷하게 조정한다.
- **실시간 정책의 위험**: `SCHED_FIFO` 작업이 무한 루프에 빠지면 같은 코어의 일반 작업이 굶는다. 리눅스는 기본적으로 실시간 작업이 쓸 수 있는 CPU 시간을 일정 비율로 제한하는 장치(`sched_rt_runtime_us`)를 둔다.
- **쿠버네티스 CPU 요청은 가중치다**: 파드의 CPU `requests` 는 cgroup 의 CPU 가중치로 변환되어, 경합이 있을 때 비례 배분 스케줄러가 CPU 를 나누는 비율이 된다. `limits` 는 별도의 쿼터 메커니즘으로 상한을 건다.
- **CPU 고정(pinning)**: 지연에 민감한 워크로드는 `taskset` 이나 쿠버네티스 `static` CPU 관리자 정책으로 특정 코어에 고정해 다른 작업과의 경합과 캐시 오염을 줄인다.

## 확인 문제

1. 응답 시간과 반환 시간의 차이를 정의로 설명하라.
2. SJF 가 이론상 좋은데도 범용 OS 가 그대로 쓰지 않는 이유 두 가지는?
3. RR 에서 시간 조각을 무한히 크게 하면 어떤 알고리즘과 같아지는가?
4. MLFQ 가 주기적으로 모든 작업을 최상위 큐로 올리는 이유는?
5. CFS 에서 nice 값이 낮은 작업이 CPU 를 더 많이 받는 원리는?

### 풀이

1. 응답 시간은 도착부터 처음 실행될 때까지, 반환 시간은 도착부터 완료될 때까지의 시간이다.
2. 실행 시간을 미리 알 수 없고, 긴 작업이 계속 밀리는 기아가 생길 수 있기 때문이다.
3. FCFS 다. 모든 작업이 한 번에 끝까지 실행된다.
4. 낮은 큐에 내려간 CPU 집약 작업의 기아를 막고, 성격이 바뀐(대화형이 된) 작업이 다시 높은 우선순위를 받을 기회를 주기 위해서다.
5. 가중치가 커서 같은 실제 실행 시간에 대해 vruntime 이 더 천천히 증가하므로, 가장 작은 vruntime 을 고르는 스케줄러에 더 자주 선택된다.

## 더 읽을거리 (References)

- OSTEP, [Scheduling: Introduction (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched.pdf)
- Linux kernel documentation, [CFS Scheduler](https://docs.kernel.org/scheduler/sched-design-CFS.html), [EEVDF Scheduler](https://docs.kernel.org/scheduler/sched-eevdf.html)
- Linux man-pages, [sched(7)](https://manpages.debian.org/bookworm/manpages/sched.7.en.html)
- Kubernetes 문서, [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
