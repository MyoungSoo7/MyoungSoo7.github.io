---
layout: post
title: "*프로그램 *vs *프로세스 *vs *스레드* — *세 단어 의 *경계와 *관계*"
date: 2026-06-13 17:45:00 +0900
categories: [computer-science, os, fundamentals]
tags: [process, program, thread, os, concurrency, fundamentals, backend]
---

> *프로그램* 과 *프로세스* 와 *스레드* — *비슷한 듯 *다른* 세 단어.
> *백엔드 면접 의 *단골*. *실 무 의 *결정적 *순간 마다 *되돌아 오는 *기본*.
> *정의 만 외우면 *50%*, *왜 그렇게 *나뉘었는지* 알면 *100%*. 이 글은 *그 *왜* 를 *짚는다*.

---

## TL;DR

| 항목 | **Program** | **Process** | **Thread** |
|------|-------------|-------------|------------|
| **상태** | *정적 (파일)* | *동적 (실행 중)* | *Process 안 의 *경량 단위* |
| **저장 위치** | *디스크* | *RAM (메모리)* | *Process 의 *메모리 안* |
| **자원 소유** | *없음* | *RAM / CPU 시간 / File / 소켓* | *공유* (스택 + 레지스터 만 *별도) |
| **생성 비용** | *없음* | *큼* (fork / exec) | *작음* |
| **통신** | *없음* | *IPC* (어렵고 비싸다) | *공유 메모리* (쉽지만 위험) |
| **격리** | — | *완전 격리* | *없음* (같은 process 안) |

*핵심 한 줄* :

> ***프로그램은 *설계도*, 프로세스는 *건축물*, 스레드는 *건축물 안의 *일꾼*.***

---

## 1. **Program** — *정적 *설계도*

### 정의

> *디스크 에 *저장된 *명령어 의 *집합*.*

`/usr/bin/java`, `myapp.jar`, `chrome.exe` — 이것들 이 *프로그램*.

### *특징*

- *정적* — *그냥 *파일*. *실행 되지 않으면 *아무것도 안 함*.
- *수명* — *디스크 에 *영원히 *있을 수 있다*.
- *공유* — *같은 프로그램을 *여러 사람이 *실행 가능*.
- *자원 소유 *없음*.

### *프로그램 의 *구성*

```
실행 파일 (.exe / .jar / ELF):
  - 코드 영역 (instructions)
  - 데이터 영역 (전역 변수 의 초기 값)
  - 메타 데이터 (헤더, 심볼 테이블 등)
```

이 파일 이 *RAM 으로 *로드 되어야* *프로세스* 가 된다.

---

## 2. **Process** — *살아 있는 *프로그램*

### 정의

> *OS 가 *RAM 에 *로드 한 *프로그램 의 *실행 인스턴스*.*

같은 프로그램 (Chrome) 을 *3 번 클릭* 하면 *3 개의 프로세스* 가 생성. *각자 *독립*.

### *Process 의 *4 가지 *특성*

1. **PID (Process ID)** — *OS 가 부여한 *고유 식별자*
2. **자원 소유** — *RAM / CPU 시간 / 파일 디스크립터 / 소켓 / 환경변수*
3. **완전 격리** — *다른 process 의 *메모리 접근 *불가*
4. **상태** — *Running / Ready / Waiting / Stopped / Zombie*

### *Process 의 *메모리 구조*

```
┌─────────────────────┐
│ Stack ↓ (지역변수)   │  ← 함수 호출, 매개변수
├─────────────────────┤
│       ↕             │
│ (Heap 과 Stack 사이)│
│       ↕             │
├─────────────────────┤
│ Heap ↑ (동적 할당)  │  ← malloc / new
├─────────────────────┤
│ BSS / Data         │  ← 전역 변수, 정적 변수
├─────────────────────┤
│ Text / Code        │  ← 명령어
└─────────────────────┘
```

이 *5 영역* 의 *총합* 이 *프로세스 의 *메모리*. 다른 process 의 메모리 와 *완전 분리*.

### *Process 생성 — *fork() 의 *세계*

Unix 에서 :

```c
pid_t pid = fork();
if (pid == 0) {
    // 자식 프로세스
} else if (pid > 0) {
    // 부모 프로세스 (pid = 자식 의 PID)
}
```

`fork()` — *부모 의 *모든 *메모리 복사* 후 자식 생성. *비용 *크다* (수 MB 메모리 복사). 현대 OS 는 *Copy-on-Write* 로 *최적화*.

---

## 3. **Thread** — *프로세스 안의 *경량 일꾼*

### 정의

> *Process 의 *메모리 를 공유 하면서 *독립 적 으로 *실행 되는 *경량 단위*.*

### *왜 *Thread 가 *필요* 한가*

*Process 만 있다면* :

- *작업 분담* = *여러 process 생성* — *비용 비쌈*
- *process 간 *데이터 공유* = *IPC 어렵 고 *느림*
- *멀티 코어 CPU 활용* = *어려움*

*Thread 의 *등장* 이 *이 문제 *해결* :

- *생성 비용 *작음* (Process 의 *1/100 정도*)
- *같은 process 의 *메모리 *직접 공유* — *통신 *빠름*
- *멀티 코어 활용 *직 접*

### *Thread 의 *4 가지 *특성*

1. **TID (Thread ID)** — process 안 *고유 식별자*
2. **공유** — *Heap / Code / Data / 열린 파일 등 *공유*
3. **독립** — *Stack / Program Counter / Registers / Local* — *별도*
4. **수명** — *부모 process 가 *끝나면 함께 *끝남*

### *Thread 의 *메모리 구조*

```
Process 메모리 :
┌─────────────────────┐
│ Thread 1 Stack      │  ← 각 thread *별도*
├─────────────────────┤
│ Thread 2 Stack      │
├─────────────────────┤
│ Thread 3 Stack      │
├─────────────────────┤
│   ↕   (공간 부족 시 *Stack overflow*)
├─────────────────────┤
│ Heap (공유)         │  ← 모든 thread 가 *공유*
├─────────────────────┤
│ BSS / Data (공유)   │
├─────────────────────┤
│ Text / Code (공유)   │
└─────────────────────┘
```

→ *각 thread 가 *Stack 만 별도*, 나머지는 *공유*. *그래서 *공유 메모리 가 *위험* 의 *원천*.

---

## 4. *Process 와 Thread 의 *상세 비교*

### *생성 비용*

```
Process 생성  : 1 ~ 10 ms  (fork + 메모리 할당)
Thread 생성   :   10 ~ 100 µs  (Stack 만 할당)
```

→ *Thread 가 *10 ~ 100 배 빠름*.

### *Context Switch 비용*

```
Process Switch : 5 ~ 20 µs  (메모리 mapping 변경 포함)
Thread Switch  : 1 ~  5 µs  (같은 process 안)
```

### *통신 방식*

| 방식 | Process 간 | Thread 간 |
|------|-----------|------------|
| **Shared memory** | *IPC 필요 (mmap, shm)* | *바로 공유* |
| **Message** | Socket / Pipe / Queue | Queue + Lock |
| **Signal** | Signal / Event | 콜백 |

### *격리 / 안전*

```
Process : *한 process 죽어도 *다른 process *영향 없음*
Thread  : *한 thread 의 *치명적 *오류 가 *전 process *다운*
```

→ *안정성* 은 *Process > Thread*. 그래서 *Chrome 의 *Multi-process 아키텍처* — 탭 *별로 *process* 분리.

---

## 5. **Multi-Process vs Multi-Thread** — *어느 때*

### *Multi-Process 권장*

- *안정성 *결정 적* — 한 인스턴스 다운 *다른 *영향 없음*
- *각자 *독립 자원* (RAM 분리)
- *언어 가 *fork 모델 친화* (Python multiprocessing, PHP-FPM)
- *보안 격리* 필요 (Chrome 탭)

### *Multi-Thread 권장*

- *통신 *많음* — 공유 메모리 직접 활용
- *경량 동시성* — *수천 동시 *요청*
- *멀티 코어 활용*
- *Java, C++, Go 같은 *thread 친화 언어*

### *둘 다 *조합 — *현대 대형 시스템*

```
N 개 process × M 개 thread = N×M 동시 처리
```

- Chrome — 탭 *별 process* + 각 process 안 *여러 thread*
- Nginx — *worker process N 개*, 각 *event-driven 처리*
- Spring Boot — *단일 process + thread pool*
- PostgreSQL — *connection 별 *process* (Postgres 14+ 부터 일부 thread 화)

---

## 6. **Context Switch** — *동시성 의 *진짜 비용*

### *Switch 가 *발생 하는 *순간*

1. *Timer interrupt* — *OS scheduler 의 *정기 호출*
2. *I/O 대기* — *디스크 / 네트워크 / 락*
3. *Higher priority* — *우선순위 높은 task 등장*
4. *System call* — *syscall 의 *일부 가 *switch 유도*

### *비용*

- *수십 ~ 수백 µs*
- *CPU cache 무효화* (L1/L2 의 *내용 사라짐*)
- *TLB flush* (페이지 테이블 변환 캐시)
- *Pipeline flush*

### *과한 Switch 의 *증상*

```
1000 개 thread 가 *동시 active* → switch *초당 10000 회 +
→ CPU 의 *실제 일하는 시간 < *switch 비용*
→ throughput *떨어짐*
```

### *해결 — *적정 동시성*

```
Thread Pool 크기 ≈ CPU 코어 수 × 2 (CPU bound)
                  ≈ CPU 코어 수 × 10~100 (I/O bound)
```

이게 *대부분 백엔드 의 *적정 시작*.

---

## 7. **백엔드 의 *현실*

### *Java / Spring Boot*

- *단일 JVM process*
- *Tomcat 의 *thread pool* (기본 200)
- *각 요청 = 1 thread*
- *blocking I/O 가 *기본*

→ *동시 요청 200 이 *상한*. *그 이상 은 *큐 대기*.

*Project Loom (Java 21+) — Virtual Thread* 의 등장 :

- *경량 thread (수십만 개)*
- *OS thread *기반* 안 함*
- *I/O 대기 시 *yield + park*
- *기존 코드 거의 그대로*

→ *Java 의 *thread 모델 *혁명*. 2026 기준 *production *적용 확산*.

### *Node.js*

- *단일 process + 단일 main thread*
- *Event Loop + libuv* 의 *비동기 I/O*
- *Worker Threads* 로 *CPU bound 작업 분리*
- *Cluster 모듈* 로 *multi-process*

→ *CPU 코어 수 = process 수* 패턴.

### *Go*

- *Goroutine* — *경량 동시성 단위*
- *수십만 ~ 수백만 goroutine* 가능
- *OS thread 의 *수십 배 효율*
- *channel* 로 *통신*

→ *Java Loom 이 *영향 받은 모델*.

### *Python*

- *GIL (Global Interpreter Lock)*
- *단일 thread 가 *진짜 실행*
- *Multi-thread 가 *I/O 에만 효과*
- *CPU bound 는 *multiprocessing*

→ *Python 은 *Thread 보다 *Process 친화*.

---

## 8. **Concurrency 의 *실 무 위험*

### *Race Condition*

```java
// ❌ 2 thread 가 *동시 *increment
public class Counter {
    int count = 0;
    public void inc() { count++; }  // 비-atomic
}
```

`count++` 가 *3 단계* (read / add / write). 두 thread 동시 실행 시 *부정합*.

해결 :

```java
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();  // atomic
```

### *Deadlock*

```
Thread 1 : Lock A → wait for Lock B
Thread 2 : Lock B → wait for Lock A
→ 둘 다 *영원히 기다림*
```

해결 — *Lock 순서 *통일*, *timeout 적용*, *tryLock + 백오프*.

### *Memory Visibility*

```
Thread 1 : count = 10
Thread 2 : 읽으면 *옛 값 보일 수 있음*
```

해결 — `volatile`, `synchronized`, `Atomic*`, *memory barrier*.

---

## 9. **흔한 *오해*

### 9.1. *"Thread 가 *Process 보다 *항상 *빠르다*"*

→ *틀림*. *생성 비용은 *빠르지만 *contention / 동기화 비용*. *부적 절 한 설계 시 *오히려 *느림*.

### 9.2. *"Multi-Thread 면 *멀티 코어 *자동 활용"*

→ *틀림*. *Python GIL*, *비동기 단일 thread* 등 — *언어 의 *모델* 에 *의존*.

### 9.3. *"Thread 많이 만들면 *동시성 ↑*"*

→ *틀림*. *Context switch 비용* 으로 *오히려 ↓*. *적정 풀 크기* 가 *답*.

### 9.4. *"Process 격리 가 *항상 안전*"*

→ *대부분 맞음*. 그러나 *IPC / shared memory* 시 *동기화 문제 *동일 발생*.

---

## 10. **본인 *7 년 경험* 5 사례*

### 10.1. *Tomcat Thread Pool *부족*

*동시 요청 *250* — *50 개 대기*. *Pool 200 → 400 으로 늘림* → *해결*. *Memory 증가 무시 안 됨*.

### 10.2. *Java Project Loom *적용*

*Spring Boot 3.2 + Java 21 + Virtual Thread* — *동일 RAM 으로 *동시 처리 5 배 ↑*.

### 10.3. *Python multiprocessing 의 *함정*

*Process 간 *큰 객체 전달* — *pickle 직렬화 비용 폭증*. *공유 메모리 활용* 으로 해결.

### 10.4. *Node.js Cluster *우회*

*CPU bound 작업 이 *Event Loop 점유* — *전 서비스 *느려짐*. *Worker Thread 분리* 로 해결.

### 10.5. *Race Condition *3 개월 *디버깅*

*드물게 *재현* 되는 *부정합* — *동시 결제 *2 번 처리*. *Atomic + DB unique 제약* 으로 해결.

---

## 11. **결정 가이드**

```
□ *안정성 *최우선* — Process 분리
□ *경량 동시성 *대규모* — Thread (또는 Coroutine)
□ *CPU bound* — Thread Pool = CPU × 2
□ *I/O bound* — Thread Pool = CPU × 10~100, 또는 Virtual Thread / Coroutine
□ *상태 공유* 가 *과한 가* — Process 격리 검토
□ *Race Condition 위험* — Atomic / Lock / DB 제약 *복합 적*
□ *현대 언어 의 *경량 모델* — Loom / Goroutine / asyncio 적극 활용
```

---

## 12. *마치며*

> *프로그램 / 프로세스 / 스레드 의 *경계 를 *몸 에 *익히면* — *동시성 의 *모든 의사결정* 의 *근거가 *생긴다*.

3 줄 요약 :

1. ***프로그램 = 설계도, 프로세스 = 건축물, 스레드 = 일꾼*** — *역할 의 명확함*.
2. ***Multi-Thread 와 Multi-Process 는 *trade-off — *공유 vs 격리***.
3. ***적정 동시성 = CPU × 2 (CPU bound), CPU × 10~100 (I/O bound)*** — *과한 thread 는 *오히려 *느림*.

7년차 회고 :

> *"학부 시절 *OS 가 *지루* 했다. *7년 후 *Tomcat 의 *thread pool 튜닝* 의 *결정 적 *순간* 에 *그때 의 *기초가 *되돌아 온다*."*

다음 글 — *Java Virtual Thread 의 *깊이* — *Loom 의 *내부 동작* 과 *Spring Boot 통합*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 *운영 회고*. *OS 의 *원리* 는 *언어 / 프레임워크 무관*. *Linux 의 *task_struct, *Windows 의 *thread 객체* 등 *세부 구현* 은 *다를 수 있다*.
