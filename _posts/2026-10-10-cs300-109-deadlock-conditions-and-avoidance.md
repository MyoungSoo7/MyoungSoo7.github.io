---
layout: post
title: "[CS300 #109] 교착 상태 — 조건과 회피"
date: 2026-10-10 19:49:00 +0900
categories: [cs]
tags: [cs300, operating-systems, deadlock, bankers-algorithm, lock-ordering]
---

컴퓨터공학 300 주제 시리즈의 109번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

교착 상태는 둘 이상의 실행 흐름이 서로가 가진 자원을 기다리며 아무도 진행하지 못하는 상태이고, 네 가지 필요조건 중 하나만 깨면 예방할 수 있으며, 그 밖에 회피(은행원 알고리즘)·탐지 후 회복·무시라는 전략이 있다.

## 왜 필요한가

락을 쓰기 시작하면 곧 만나는 문제다. 스레드 A 가 계좌 X 의 락을 잡고 Y 를 기다리는데, 스레드 B 가 Y 를 잡고 X 를 기다린다. 둘 다 영원히 멈춘다. CPU 사용률은 0 인데 요청은 하나도 처리되지 않는다. 로그도 남지 않는다.

교착 상태는 애플리케이션 락에만 있지 않다.

- 데이터베이스에서 두 트랜잭션이 행을 반대 순서로 갱신할 때
- 파이프 양쪽이 서로 상대가 읽어 주기를 기다리며 버퍼를 가득 채웠을 때
- 분산 시스템에서 서비스 A 가 B 를 동기 호출하고 B 가 다시 A 를 부르는데 양쪽 스레드 풀이 모두 찼을 때

원리를 알면 설계 단계에서 피할 수 있고, 장애 중에도 빨리 알아볼 수 있다.

## 핵심 개념

### 네 가지 필요조건 (Coffman 조건)

Coffman, Elphick, Shoshani 가 1971년 논문 "System Deadlocks" 에서 정리한 조건이다. 네 가지가 **모두** 성립해야 교착 상태가 생긴다.

| 조건 | 뜻 |
|---|---|
| 상호 배제 | 자원을 한 번에 하나만 쓸 수 있다 |
| 점유와 대기(hold and wait) | 자원을 쥔 채 다른 자원을 기다린다 |
| 비선점(no preemption) | 남이 쥔 자원을 강제로 빼앗을 수 없다 |
| 순환 대기(circular wait) | 대기 관계가 원을 이룬다 |

### 자원 할당 그래프

```
   P1 ----요청----> [R2]
    ^                 |
   할당              할당
    |                 v
  [R1] <----요청---- P2
```

프로세스(P)에서 자원(R)으로 가는 화살표는 요청, 자원에서 프로세스로 가는 화살표는 할당이다. 각 자원이 하나씩만 있다면 **그래프에 사이클이 있는 것이 곧 교착 상태**다. 자원이 여러 개(인스턴스)라면 사이클은 필요조건일 뿐 충분조건은 아니다.

### 대응 전략 네 가지

**1. 예방(prevention)**: 네 조건 중 하나를 구조적으로 불가능하게 만든다.

| 깨는 조건 | 방법 | 비용 |
|---|---|---|
| 상호 배제 | 공유 가능한 자원으로 바꾼다(읽기 전용, 락 없는 자료구조) | 적용 범위가 좁다 |
| 점유와 대기 | 필요한 자원을 한꺼번에 요청하거나, 다 못 얻으면 다 놓는다 | 자원 활용률 저하 |
| 비선점 | `trylock` 실패 시 가진 락을 모두 놓고 재시도 | 라이브락 위험 |
| 순환 대기 | **모든 락에 전역 순서를 정하고 그 순서로만 잡는다** | 설계 규율 필요 |

실무에서 가장 많이 쓰는 것은 마지막, **락 순서 정하기**다. 예를 들어 두 계좌 간 이체에서 항상 계좌 번호가 작은 쪽 락을 먼저 잡으면 순환이 생길 수 없다.

**2. 회피(avoidance)**: 자원을 줄 때마다 "이걸 주고도 모두가 끝날 수 있는 순서가 존재하는가(안전 상태)"를 검사해, 안전할 때만 준다. 다익스트라의 **은행원 알고리즘**이 대표다. 각 프로세스가 최대로 필요한 양을 미리 알려야 한다는 제약이 있어 범용 OS 에서는 거의 쓰지 않는다.

**3. 탐지와 회복(detection & recovery)**: 일단 허용하고, 주기적으로 대기 그래프에서 사이클을 찾는다. 찾으면 희생자를 골라 중단(롤백)시킨다. 데이터베이스가 이 방식을 쓴다.

**4. 무시(ostrich)**: 드물다고 보고 아무것도 하지 않는다. 생기면 사람이 재시작한다. 범용 OS 커널이 사용자 프로그램의 락 교착에 대해 취하는 태도가 사실상 이것이다.

### 은행원 알고리즘의 안전성 검사

```
Need = Max - Allocation
Work = Available
반복: Need[i] <= Work 인 미완료 프로세스 i 를 찾는다
      있으면 Work += Allocation[i] (i 가 끝나고 반납한다고 가정), i 완료 표시
      없으면 멈춘다
모두 완료 표시되면 안전 상태
```

### 교착 상태가 아닌 비슷한 것들

- **라이브락(livelock)**: 다들 계속 움직이지만(양보하고 재시도) 아무도 진척이 없다. 좁은 복도에서 서로 비켜 주다 계속 마주치는 상황이다. 재시도에 무작위 대기(지터)를 넣어 깬다.
- **기아(starvation)**: 시스템 전체는 진행하지만 특정 작업만 계속 밀린다.

## 직접 해 보기

먼저 락을 반대 순서로 잡아 실제로 교착을 만들고, 이어서 은행원 알고리즘의 안전성 검사를 구현한다.

```python
import threading, time

# 1) 실제로 교착 상태 만들기: 두 스레드가 락을 반대 순서로 잡는다
a, b = threading.Lock(), threading.Lock()
def t1():
    with a:
        time.sleep(0.1)
        if not b.acquire(timeout=1):      # 타임아웃이 없으면 영원히 멈춘다
            print("t1: b 를 1초 안에 못 잡음 -> 교착 의심"); return
        b.release()
def t2():
    with b:
        time.sleep(0.1)
        if not a.acquire(timeout=1):
            print("t2: a 를 1초 안에 못 잡음 -> 교착 의심"); return
        a.release()
x, y = threading.Thread(target=t1), threading.Thread(target=t2)
x.start(); y.start(); x.join(); y.join()

# 2) 은행원 알고리즘의 안전성 검사
def is_safe(available, max_need, alloc):
    n = len(alloc)
    need = [[m - a for m, a in zip(max_need[i], alloc[i])] for i in range(n)]
    work, done, order = list(available), [False] * n, []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not done[i] and all(nd <= w for nd, w in zip(need[i], work)):
                work = [w + a for w, a in zip(work, alloc[i])]   # 끝나면 자원 반납
                done[i] = True; order.append(f"P{i}"); progress = True
    return all(done), order

# 자원 종류 A, B, C
alloc    = [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]]
max_need = [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]]
print("가용 [3,3,2] ->", is_safe([3,3,2], max_need, alloc))
print("가용 [1,1,0] ->", is_safe([1,1,0], max_need, alloc))
```

```
t1: b 를 1초 안에 못 잡음 -> 교착 의심
가용 [3,3,2] -> (True, ['P1', 'P3', 'P4', 'P0', 'P2'])
가용 [1,1,0] -> (False, [])
```

첫 부분에서 메시지가 한 줄만 나온 이유가 흥미롭다. t1 이 타임아웃으로 포기하면서 `a` 를 놓자, 아직 기다리던 t2 가 `a` 를 잡고 정상 종료했다. 타임아웃이 "비선점" 조건을 깨는 회복 장치 노릇을 한 것이다. 둘째 부분은 가용 자원이 `[3,3,2]` 이면 P1→P3→P4→P0→P2 순서로 모두 끝낼 수 있어 안전하고, `[1,1,0]` 이면 어떤 프로세스의 남은 요구도 채울 수 없어 불안전하다는 결과다. 불안전 상태가 곧 교착 상태는 아니지만, 교착으로 갈 가능성을 배제할 수 없다.

## 현업에서는

- **데이터베이스 교착 탐지**: PostgreSQL 은 락을 `deadlock_timeout`(기본 1초)만큼 기다린 뒤 교착 검사를 하고, 사이클이 있으면 트랜잭션 하나를 `deadlock detected` 에러로 중단시킨다. 애플리케이션은 이 에러를 받으면 트랜잭션 전체를 재시도해야 한다. 근본 대책은 여러 행을 갱신할 때 항상 같은 순서(예: 기본 키 오름차순)로 접근하는 것이다.
- **리눅스 커널의 lockdep**: 커널은 개발·테스트 빌드에서 lockdep 이라는 검증기로 락 획득 순서를 기록하고, 순서가 뒤집힐 가능성이 보이면 실제로 교착이 일어나기 전에 경고한다. 락 순서 규율을 기계로 강제하는 사례다.
- **모든 대기에 타임아웃**: HTTP 클라이언트, DB 연결 획득, 분산 락에 타임아웃이 없으면 교착이 무기한 장애가 된다. 타임아웃은 교착을 "느린 실패"로 바꾸어 관측 가능하게 만든다.
- **분산 교착**: 서비스 간 동기 호출이 원을 이루면 스레드 풀 고갈로 서로를 기다린다. 호출 그래프에 사이클이 없도록 설계하고, 서킷 브레이커와 타임아웃을 둔다.

## 확인 문제

1. 교착 상태의 네 가지 필요조건을 쓰라.
2. 락 순서 정하기는 네 조건 중 무엇을 깨는가?
3. 자원 인스턴스가 여러 개인 시스템에서 자원 할당 그래프에 사이클이 있으면 반드시 교착인가?
4. 은행원 알고리즘이 범용 운영체제에서 잘 쓰이지 않는 이유는?
5. 라이브락과 교착 상태의 차이는?

### 풀이

1. 상호 배제, 점유와 대기, 비선점, 순환 대기.
2. 순환 대기다. 모두가 같은 순서로 잡으면 대기 관계가 원을 이룰 수 없다.
3. 아니다. 자원마다 인스턴스가 하나일 때만 사이클이 곧 교착이다. 여러 개일 때는 사이클이 있어도 다른 인스턴스가 풀려 진행할 수 있다.
4. 각 프로세스가 앞으로 필요한 최대 자원량을 미리 선언해야 하고, 매 할당마다 검사 비용이 들기 때문이다.
5. 교착 상태는 모두 멈춰 기다리고, 라이브락은 모두 계속 상태를 바꾸며 움직이지만 진척이 없다.

## 더 읽을거리 (References)

- OSTEP, [Common Concurrency Problems (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-bugs.pdf)
- E. G. Coffman, M. Elphick, A. Shoshani, "System Deadlocks", *ACM Computing Surveys* 3(2), 1971.
- E. W. Dijkstra, [The mathematics behind the Banker's Algorithm (EWD623)](https://www.cs.utexas.edu/~EWD/transcriptions/EWD06xx/EWD623.html)
- PostgreSQL 문서, [Explicit Locking — Deadlocks](https://www.postgresql.org/docs/current/explicit-locking.html); Linux kernel documentation, [Runtime locking correctness validator (lockdep)](https://docs.kernel.org/locking/lockdep-design.html)
