---
layout: post
title: "[CS300 #103] 프로세스와 프로세스 상태 — 실행 중인 프로그램의 일생"
date: 2026-10-10 19:43:00 +0900
categories: [cs]
tags: [cs300, operating-systems, process, fork, zombie]
---

컴퓨터공학 300 주제 시리즈의 103번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

프로세스는 "실행 중인 프로그램"이며, 커널은 각 프로세스를 PCB 라는 자료구조로 관리하면서 생성 → 준비 → 실행 → 대기 → 종료의 상태 사이를 옮겨 다니게 한다.

## 왜 필요한가

디스크 위의 `/usr/bin/python3` 는 그냥 바이트 덩어리다. 그것을 실행하면 비로소 메모리, 열린 파일, CPU 레지스터 값, 현재 위치를 가진 **살아 있는 실체**가 된다. 같은 프로그램을 세 번 실행하면 프로세스는 셋이다.

운영체제가 프로세스라는 추상화를 만든 이유는 두 가지다.

- **격리**: 각 프로세스는 자기만의 주소 공간을 가진다. 한 프로세스의 버그가 다른 프로세스의 메모리를 망가뜨리지 못한다.
- **다중화**: CPU 가 하나여도 여러 프로세스가 번갈아 실행되며 모두 동시에 도는 것처럼 보인다.

장애 대응에서도 프로세스 상태는 첫 번째 단서다. `ps` 의 STAT 열에 `D` 가 쌓이면 I/O 가 막혔고, `Z` 가 쌓이면 부모가 자식을 거두지 않고 있다.

## 핵심 개념

### 프로세스가 가진 것

| 구성 요소 | 내용 |
|---|---|
| 주소 공간 | 코드(text), 데이터, 힙, 스택, 매핑된 라이브러리 |
| CPU 문맥 | 프로그램 카운터, 스택 포인터, 범용 레지스터 |
| 커널 자원 | 열린 파일 디스크립터 표, 현재 디렉터리, 시그널 처리 방식 |
| 신원 | PID, 부모 PID, 사용자·그룹 ID, cgroup·네임스페이스 소속 |

커널은 이 정보를 **PCB(Process Control Block)** 에 담는다. 리눅스에서 PCB 에 해당하는 것은 `struct task_struct` 다. 리눅스는 스레드도 task 하나로 표현하므로 엄밀히는 "스케줄링 단위 하나당 task_struct 하나"다.

메모리 배치는 대략 다음과 같다(주소가 위로 갈수록 커진다).

```
높은 주소  +-------------------+
           |  스택 (아래로 자람) |  지역 변수, 함수 호출 프레임
           |        |          |
           |        v          |
           |  mmap 영역         |  공유 라이브러리, 파일 매핑
           |        ^          |
           |        |          |
           |  힙 (위로 자람)    |  malloc / new
           +-------------------+
           |  데이터 / BSS      |  전역 변수
           |  코드 (text)       |  기계어, 읽기 전용
낮은 주소  +-------------------+
```

### 상태 전이 — 교과서 모델

```
          admit            dispatch
  [New] ---------> [Ready] --------> [Running] -----> [Terminated]
                     ^  ^   preempt     |      exit
                     |  +---------------+
                     |                  | I/O 요청, sleep
                     |   I/O 완료       v
                     +------------- [Waiting]
```

- **Ready**: 실행할 준비가 되었고 CPU 만 기다린다.
- **Running**: 지금 CPU 위에서 명령어를 실행하고 있다.
- **Waiting(Blocked)**: 디스크, 네트워크, 타이머 같은 사건을 기다린다. 사건이 오기 전에는 CPU 를 줘도 할 일이 없다.
- 실행 중인 프로세스가 시간 할당량을 다 쓰면 **선점(preempt)** 되어 Ready 로 돌아간다.

### 리눅스의 실제 상태 코드

`ps` 의 STAT 열과 `/proc/PID/stat` 의 3번째 필드에서 보이는 문자다.

| 코드 | 이름 | 의미 |
|---|---|---|
| `R` | Running/Runnable | 실행 중이거나 실행 대기열에 있다(Ready 와 Running 을 구분하지 않는다) |
| `S` | Interruptible sleep | 사건을 기다린다. 시그널로 깨울 수 있다 |
| `D` | Uninterruptible sleep | 주로 디스크·NFS I/O 대기. 시그널로 깨울 수 없다 |
| `T` | Stopped | `SIGSTOP` 이나 디버거에 의해 멈췄다 |
| `Z` | Zombie | 종료했지만 부모가 아직 종료 상태를 회수하지 않았다 |

교과서의 Ready·Running 이 리눅스에서는 둘 다 `R` 이라는 점을 기억해 두자. load average 가 `R` 과 `D` 상태 개수를 함께 센다는 것도 리눅스의 특징이다(`proc(5)` 의 `/proc/loadavg` 설명 참고).

### 생성과 종료: fork, exec, wait

유닉스 계열에서 새 프로그램을 띄우는 방식은 두 단계다.

1. `fork()` 가 현재 프로세스를 복제한다. 자식은 부모와 같은 코드 위치에서 깨어나되, `fork` 반환값이 부모에게는 자식 PID, 자식에게는 0 이다. 메모리는 복사하는 척만 하고 실제로는 **쓰기 시 복사(Copy-on-Write)** 로 공유한다.
2. 자식이 `execve()` 로 자기 주소 공간을 새 프로그램으로 갈아 끼운다. PID 는 그대로다.
3. 부모는 `wait()` 계열 호출로 자식의 종료 코드를 회수한다.

자식이 끝났는데 부모가 `wait` 하지 않으면 자식은 **좀비**로 남는다. 메모리는 이미 반납했지만 PID 와 종료 코드를 담은 작은 항목이 프로세스 테이블에 남는다. 부모가 먼저 죽으면 자식은 **고아**가 되어 init(PID 1) 또는 지정된 subreaper 에게 입양되고, 그 프로세스가 대신 `wait` 해 준다.

## 직접 해 보기

자식 프로세스를 만들고, 잠들기·멈춤·좀비 상태를 `/proc` 에서 직접 읽어 본다. 리눅스에서만 동작한다.

```python
import os, time, signal

def state(pid):
    with open(f"/proc/{pid}/stat") as f:
        data = f.read()
    # 2번째 필드(comm)는 괄호 안에 공백이 있을 수 있으므로 마지막 ')' 뒤에서 자른다
    return data[data.rindex(")") + 2]

pid = os.fork()
if pid == 0:                      # 자식
    time.sleep(1)                 # 잠깐 잠들었다가
    os._exit(7)                   # 종료 코드 7 로 끝난다

print("부모 PID", os.getpid(), "자식 PID", pid)
time.sleep(0.2); print("자식 상태(잠자는 중):", state(pid))
os.kill(pid, signal.SIGSTOP); time.sleep(0.1)
print("SIGSTOP 후        :", state(pid))
os.kill(pid, signal.SIGCONT); time.sleep(1.2)
print("종료했지만 wait 전 :", state(pid))
_, status = os.waitpid(pid, 0)
print("wait 후 종료 코드  :", os.waitstatus_to_exitcode(status))
print("/proc 항목 남았나  :", os.path.exists(f"/proc/{pid}"))
```

실행 결과다.

```
부모 PID 1166281 자식 PID 1166282
자식 상태(잠자는 중): S
SIGSTOP 후        : T
종료했지만 wait 전 : Z
wait 후 종료 코드  : 7
/proc 항목 남았나  : False
```

종료한 자식이 `waitpid` 전까지 `Z` 로 남아 있다가, 회수되는 순간 `/proc` 에서 사라지는 것이 보인다. 자식에서 `sys.exit` 대신 `os._exit` 를 쓴 이유는 부모에게서 복제된 파이썬 정리 루틴(버퍼 flush 등)이 두 번 실행되지 않게 하려는 것이다.

## 현업에서는

- **컨테이너의 PID 1 문제**: 컨테이너 안에서 애플리케이션이 PID 1 이 되면, 그 안에서 생긴 고아 프로세스를 거둘 책임도 진다. 셸 스크립트나 일반 앱은 이를 하지 않으므로 좀비가 쌓일 수 있다. 그래서 `tini` 같은 작은 init 을 쓰거나, 쿠버네티스에서 `shareProcessNamespace` 로 pause 컨테이너가 PID 1 을 맡게 하기도 한다.
- **D 상태 누적**: NFS 서버가 응답하지 않거나 디스크가 망가지면 그 경로를 건드린 프로세스가 `D` 로 쌓이고 `kill -9` 도 듣지 않는다. CPU 는 놀고 있는데 load average 만 치솟는다면 `ps -eo pid,stat,wchan,cmd | grep ' D'` 로 D 상태부터 찾는다.
- **fork 와 메모리**: 큰 힙을 가진 프로세스(예: Redis 스냅샷)가 fork 하면 Copy-on-Write 덕에 즉시 복사되지는 않지만, 이후 부모가 쓰는 페이지마다 복사가 일어나 메모리가 점점 늘어난다.
- **종료 코드 읽기**: 쿠버네티스에서 컨테이너 종료 코드 137 은 128+9, 즉 SIGKILL 로 죽었다는 뜻이다(OOM killer 가 흔한 원인). 143 은 128+15, SIGTERM 이다.

## 확인 문제

1. 프로그램과 프로세스의 차이를 한 문장으로 설명하라.
2. 교과서의 Ready 와 Running 은 리눅스 `ps` 에서 각각 어떤 문자로 보이는가?
3. 좀비 프로세스는 메모리를 얼마나 쓰는가? 왜 그래도 문제가 되는가?
4. `fork()` 직후 부모와 자식은 무엇으로 자신이 어느 쪽인지 구분하는가?
5. `kill -9` 를 보내도 죽지 않는 프로세스는 주로 어떤 상태인가?

### 풀이

1. 프로그램은 디스크에 저장된 실행 파일이고, 프로세스는 그것이 메모리에 올라가 CPU 문맥과 커널 자원을 가지고 실행 중인 인스턴스다.
2. 둘 다 `R` 이다. 리눅스는 실행 중과 실행 대기를 같은 상태로 표시한다.
3. 사용자 메모리는 이미 반납했고 커널의 작은 항목만 남는다. 그러나 PID 를 계속 점유하므로 대량으로 쌓이면 PID 고갈로 새 프로세스를 만들지 못한다.
4. `fork()` 의 반환값이다. 부모는 자식의 PID(양수)를, 자식은 0 을 받는다.
5. `D`(uninterruptible sleep) 상태다. 커널 내부 I/O 를 기다리는 중이라 시그널이 전달되지 않는다.

## 더 읽을거리 (References)

- OSTEP, [The Abstraction: The Process (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-intro.pdf)
- OSTEP, [Interlude: Process API (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-api.pdf)
- Linux man-pages, [fork(2)](https://manpages.debian.org/bookworm/manpages-dev/fork.2.en.html), [wait(2)](https://manpages.debian.org/bookworm/manpages-dev/wait.2.en.html)
- Linux man-pages, [proc(5)](https://manpages.debian.org/bookworm/manpages/proc.5.en.html) — `/proc/PID/stat` 필드와 상태 문자
