---
layout: post
title: "프로그램 · 프로세스 · 스레드 — *OS 의 *3 층 추상* 과 *C → Java → Node* 의 *동시성 진화사*"
date: 2026-05-29 02:15:00 +0900
categories: [os, concurrency, language]
tags: [process, thread, c, java, nodejs, event-loop, virtual-thread, project-loom, libuv, pthread, jvm]
---

> *''프로그램은 *디스크* 에 있고, 프로세스는 *메모리* 에 있고, 스레드는 *CPU 에* 있다''*. *50 년 된 OS 교과서의 한 줄* 이지만, *그 한 줄을 *진짜 이해* 하면 *''*왜 Node.js 가 *싱글 스레드인데도 빠른가''*, *''*왜 Java 가 *Virtual Thread* 를 21 년 만에 도입했는가''*, *''*왜 Go 가 *고루틴* 으로 *모든 걸 바꿨는가''*'' 같은 *현대 프로그래밍의 *주요 질문들이 *한 줄기로 연결된다*.
>
> 이 글은 *프로그램 / 프로세스 / 스레드* 의 *기초* 부터, *OS 가 그것들을 *어떻게 무대 위에 올리는지*, 그리고 *C (1972) → Java (1995) → Node.js (2009)* 의 *3 언어가 *동시성에 *서로 다른 방식으로 응답한 *진화의 역사* 까지 *한 흐름* 으로 본다.

대상은 *''*동시성''* 이 *''*그냥 *Thread 만들면 되는 거 아니야?''* 라고 생각해 본 적 있는 *모든 백엔드 개발자*.

---

## 1. *3 층 추상* — *디스크 → 메모리 → CPU*

### 1.1 **프로그램** = *''디스크에 있는 *불활성 *지시문''***

```bash
$ ls -la /usr/bin/python3
-rwxr-xr-x  1 root  root  5,432,768  May 29 02:00 python3
```

이 파일은 *''*5 MB 짜리 *바이너리*''*. ELF (Linux) / Mach-O (macOS) / PE (Windows) *포맷*. *지시문 + 데이터*. *동작 안 함*. *디스크에 *조용히 누워 있음*.

프로그램은 *''*레시피 책''* 이다. *책 자체는 *요리하지 않는다*.

### 1.2 **프로세스** = *''*레시피를 *읽으며 요리하는* *주방'***

```bash
$ ./python3 -c "import time; time.sleep(60)" &
[1] 12345
```

이 순간 *OS 가 *4 가지 일* 을 한다*:

1. *Process ID (PID) 할당* — 12345
2. *Virtual Memory Space* 할당 — *4 KB ~ TB 단위의 *가상 주소 공간*
3. *프로그램 파일을 *메모리에 *로드*
4. *PCB (Process Control Block)* 생성 — *''*이 프로세스의 *상태''* 를 OS 가 관리

```
[Virtual Memory Layout of a Process]

  높은 주소
  ┌────────────────────┐
  │      Stack         │  ← *함수 호출 / 지역 변수* (자라난다 ↓)
  ├────────────────────┤
  │                    │
  │   (mmap / shared)  │
  │                    │
  ├────────────────────┤
  │      Heap          │  ← *동적 할당* (자라난다 ↑)
  ├────────────────────┤
  │      BSS           │  ← *0 으로 초기화된 *전역 변수*
  ├────────────────────┤
  │      Data          │  ← *초기값 있는 *전역 변수*
  ├────────────────────┤
  │      Text          │  ← *프로그램 *기계어* (read-only)
  └────────────────────┘
  낮은 주소
```

> **핵심**: *''프로세스 = *프로그램 + 자기만의 *메모리 + 자기만의 *상태*''*. *''*같은 프로그램 *2 개 띄우면* *서로 *완전히 격리된 *프로세스 *2 개*''*.

### 1.3 **스레드** = *''*하나의 *프로세스 안에서 *동시에 *흐르는 *실행 *흐름*'''

스레드는 *프로세스의 *자원을 *공유* 하면서 *각자 *CPU 에서 *실행 됨*:

```
[Process — 공유 자원]
  ├─ Text (코드)        ← *모든 스레드 공유*
  ├─ Heap (동적 할당)    ← *모든 스레드 공유* (동시 접근 위험)
  ├─ Data / BSS          ← *공유*
  └─ File descriptors    ← *공유*

[Thread — 각자 자기 것]
  ├─ Stack               ← *각 스레드마다 *독립적*
  ├─ Registers           ← *각 스레드마다 *독립적*
  └─ Thread ID
```

> **격언**: *''*프로세스 *분리는 *안전*, *공유는 *어려움*. *스레드 *공유는 *쉬움*, *동기화는 *어려움*''*.

이 한 줄이 *동시성 프로그래밍 *수십 년의 *고통의 *원천이자 *진보의 *동력*.

### 1.4 *Process *vs* Thread — *물리적 차이*

| | **Process** | **Thread** |
|---|---|---|
| 메모리 공간 | *독립* | *공유* |
| 생성 비용 | *비쌈* (fork: *수 ms*) | *쌈* (~ μs) |
| Context switch | *비쌈* (TLB flush 등) | *상대적으로 *쌈* |
| 통신 | *IPC* (파이프, 소켓, 공유 메모리) | *공유 메모리 (변수)* |
| 장애 격리 | *완벽* | *깨짐 — *하나 죽으면 *전부* 죽음* |
| 동기화 | *덜 필요* | *반드시 필요* (mutex, semaphore) |

---

## 2. *OS 는 *어떻게 무대를 운영* 하는가*

### 2.1 *Scheduler — *''*수십 개의 *프로세스/스레드가 *4 코어 CPU 에 *돌아간다''*

```
[CPU Core 0]  ─▶ T1 (10ms) ─▶ T2 (10ms) ─▶ T1 (10ms) ─▶ T3 (10ms) ─▶ ...
[CPU Core 1]  ─▶ T4         ─▶ T5         ─▶ T4         ─▶ T6         ─▶ ...

매 *time slice (~10ms) 마다 *context switch*
```

OS Scheduler 의 일:
- *어느 스레드를 *어느 코어에 *언제 *놓을지*'' 결정
- **Linux 의 *CFS (Completely Fair Scheduler)*** — *''*공평하게 *각자 *받을 만큼만 *받는다''*
- **Windows 의 *priority-based*** — *우선순위 + time slice*

### 2.2 *Context Switch — *''*수만 CPU 사이클의 *세금''***

스레드 A → 스레드 B 전환 시:

1. *A 의 레지스터 *모두 *저장* (PCB 또는 TCB 에)
2. *B 의 레지스터 *모두 *복원*
3. *Cache / TLB 가 *''*차가워짐*''* — *cache miss 폭증*
4. *Memory 페이지 테이블 *교체* (프로세스 전환 시)

> **현실 비용**:
> - *Thread context switch* — *~ 1 μs*
> - *Process context switch* — *~ 3 ~ 10 μs* + *cache 영향 *훨씬 큼*

이 *비용* 이 *''*많은 스레드 = *반드시 *빠름'은 *아니다''* 의 *물리적 근거*.

### 2.3 *Blocking I/O 의 *진짜 비용*

```c
ssize_t n = read(fd, buf, 1024);   // ← *디스크 읽기 *완료될 때까지 *블록*
```

이 한 줄에서 *OS 가 *4 단계* 를 한다*:

1. *현재 스레드 *상태 = SLEEPING* 으로 표시
2. *Scheduler 에 *''*다른 스레드 *돌려달라*''*
3. *Disk I/O 완료* 시 *interrupt 발생*
4. *스레드 *상태 = RUNNABLE* 로 복원 → 다음 *time slice 에 실행*

이 *''*I/O 대기 = *스레드 *놀고 있음''* 가 *동시성 진화의 *모든 출발점*. *놀고 있는 스레드 위에서 *다른 일을 할 수 없을까* 가 *Node.js / async/await / virtual thread 의 *공통 질문*.

---

## 3. *C 시대* (1972 ~) — *''*OS 와 *가깝게*, 모든 걸 *직접*''*

### 3.1 *fork () + exec () — *프로세스의 *기본 패턴**

Unix 의 *''*프로세스 생성 = 항상 *복제 후 변신*''*:

```c
pid_t pid = fork();              // 부모 프로세스 *복제*
if (pid == 0) {
    // *자식 프로세스 — 부모와 *완전히 같은 메모리 상태*
    execl("/bin/ls", "ls", "-la", NULL);   // *변신* — 다른 프로그램으로 *덮어쓰기*
} else {
    // *부모 프로세스
    int status;
    waitpid(pid, &status, 0);   // *자식 *종료 대기*
}
```

*''*fork ()'' 가 *부모 메모리를 *전부 복사*'' 하면 *비싸다*. 그래서 *현대 OS 는 *COW (Copy-on-Write)* — *''*복사한 척만 하고 *진짜 쓸 때만 복사''*.

### 3.2 *pthread — *POSIX 스레드의 *표준화** (1995)

C 에서 *''*공식 스레드''* 는 *POSIX Threads (pthread)*:

```c
#include <pthread.h>

void* worker(void* arg) {
    int id = *(int*)arg;
    printf("Hello from thread %d\n", id);
    return NULL;
}

int main() {
    pthread_t threads[4];
    int ids[4] = {1, 2, 3, 4};

    for (int i = 0; i < 4; i++) {
        pthread_create(&threads[i], NULL, worker, &ids[i]);
    }
    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], NULL);
    }
    return 0;
}
```

### 3.3 *C 의 *동시성 책임* — *''*전부 *직접 관리*''*

- *Mutex / condition variable / semaphore 직접 관리*
- *Race condition* — *compiler 가 *전혀 안 도와줌*
- *Deadlock* — *직접 *방지 / 감지*
- *Memory model* — *C11 부터 *명시적*, 그 이전엔 *플랫폼 의존*

```c
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
int counter = 0;

void increment() {
    pthread_mutex_lock(&mutex);
    counter++;
    pthread_mutex_unlock(&mutex);   // ← *잊으면 *영원히 잠김*
}
```

> **C 의 정신**: *''*OS 가 *해주는 것까지가 *언어가 *해주는 것*. *그 위는 *프로그래머 책임*''*.

### 3.4 *select () / poll () / epoll () — *''*하나의 스레드로 *여러 fd 다루기''**

```c
// 1980s — select ()
fd_set readfds;
FD_ZERO(&readfds);
FD_SET(sock1, &readfds);
FD_SET(sock2, &readfds);
select(maxfd+1, &readfds, NULL, NULL, NULL);

// 2002 — epoll () — Linux 의 *확장 가능 답*
int epfd = epoll_create1(0);
epoll_ctl(epfd, EPOLL_CTL_ADD, sock1, &ev);
struct epoll_event events[64];
int n = epoll_wait(epfd, events, 64, -1);
```

이 *epoll ()* 이 *나중에 *Node.js / nginx 의 *기반* 이 된다*. *''*한 스레드가 *수만 connection 동시 다루기''* 가 *epoll 으로 *물리적으로 가능* 해진 순간이 *2002 년*.

---

## 4. *Java 시대* (1995 ~) — *''*JVM 이 *중간에 *낀다''*

### 4.1 *Green Threads → Native Threads — *초기의 *우회*

Java 초창기 (1.0 ~ 1.2) 는 **Green Threads** — *JVM 이 *자체 스케줄링*. *OS 는 *Java 프로세스 *하나로만 봄*.

- *장점*: *플랫폼 일관성*, *생성 비용 ↓*
- *단점*: *멀티 코어 활용 불가*, *blocking I/O 가 *전체 JVM 블록*

Java 1.3 (2000) 부터 **Native Threads (1:1 mapping)** — *Java Thread = OS Thread 1 개*. *멀티 코어 활용 가능*, 하지만 *Thread 가 *비싸짐* (~ 1 MB stack).

### 4.2 *synchronized + volatile — *JVM 의 *동기화 추상**

```java
public class Counter {
    private int count = 0;

    public synchronized void increment() {   // ← *모니터 락*
        count++;
    }
}
```

- *synchronized* — *''*객체별 *내장 락*''* — *C 의 mutex 보다 *훨씬 단순*
- *volatile* — *''*메모리 가시성 보장''* — *cache 와 main memory 의 *동기*
- *Java Memory Model (JMM)* — *''*어떤 *재배치까지 허용되는가''* 를 *언어 차원 명시*

### 4.3 *java.util.concurrent (J2SE 5, 2004)* — *Doug Lea 의 *선물***

Doug Lea 의 *JSR 166* 으로 *동시성의 *교과서적 추상* 이 *표준 라이브러리* 에 들어옴:

```java
ExecutorService pool = Executors.newFixedThreadPool(10);

Future<Integer> result = pool.submit(() -> {
    return heavyComputation();
});

Integer value = result.get();   // *블록*
```

- *ExecutorService / Future / Callable*
- *ConcurrentHashMap, CopyOnWriteArrayList*
- *AtomicInteger, AtomicReference*
- *CountDownLatch, CyclicBarrier, Semaphore*

> **임팩트**: *''*직접 *Thread.start ()'' 가 *안티 패턴*'' 으로 자리. *Pool 추상* 이 *기본*.

### 4.4 *CompletableFuture (Java 8, 2014) — *비동기의 *구체화***

```java
CompletableFuture.supplyAsync(() -> fetchUser(id))
    .thenCompose(user -> fetchOrdersAsync(user.id()))
    .thenApply(orders -> summarize(orders))
    .thenAccept(System.out::println)
    .exceptionally(ex -> {
        log.error("fail", ex);
        return null;
    });
```

*''*콜백 지옥''* 을 *체이닝 형태로 *길들임*. *RxJava* 와 함께 *Java 의 *async 표현력*.

### 4.5 *Project Loom — *Virtual Thread (Java 21, 2023)*

*20 년 만에 *Java 의 *concurrency 가 *다시 *큰 변화*.

```java
// 기존 — *비싼 OS 스레드*
Thread t = new Thread(() -> handleRequest());

// Loom — *Virtual Thread*
Thread vt = Thread.startVirtualThread(() -> handleRequest());

// 또는
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i ->
        executor.submit(() -> handleRequest(i))
    );
}
```

#### Virtual Thread 의 *진짜 의미*

- **수십만 개의 *Virtual Thread* 동시 실행 가능** — *OS 스레드는 *적게* 사용*
- *Blocking I/O 가 *Virtual Thread 만 *놓치게 함* — *OS 스레드는 *놀지 않음*
- *''*기존 *동기 코드 그대로* + *성능은 *비동기*''* — *async / await 없이*

```
[전통적 Thread]
  Thread #1 → blocking read () → *OS 스레드 1 개 *잠*

[Virtual Thread]
  Virtual Thread #1 → blocking read () → *Carrier (OS) Thread 풀려나서 *다른 VT 처리*
                                          ← read 완료 시 *VT 재개*
```

> **임팩트**: *''*Node.js / Go 가 *해결한 문제를 *Java 도 *자기 방식으로 *해결''*. *''*ReactiveStream / WebFlux 의 *학습 비용 없이 *고성능''*.

### 4.6 *Spring Boot + Virtual Thread (Spring 6.1 / Boot 3.2, 2024)*

```yaml
spring:
  threads:
    virtual:
      enabled: true   # ← 한 줄
```

- *Tomcat 의 *worker thread 가 *Virtual Thread* 로 *교체*
- *@Async 도 *Virtual Thread 로*
- *''*JDBC 호출이 *Virtual Thread 안에서 *블록 해도* OS 스레드는 *안 막힘*''*

---

## 5. *Node.js 시대* (2009 ~) — *''*싱글 스레드인데 *어떻게 그렇게 *빠른가''*

### 5.1 *출생 배경 — *''*Apache 의 *한계*''*

2009 년 Ryan Dahl 이 *''*Apache 가 *수만 동시 connection 에서 죽는다''* 라는 문제에 *직면*:

- Apache 의 *thread-per-connection* 모델: *10,000 connection = 10,000 thread = *수십 GB 메모리*
- *Context switch 비용 폭증*
- *대부분의 thread 가 *I/O 대기 *놀고 있음*

해법: *''*하나의 스레드가 *epoll 으로 *모든 I/O 를 *동시 다루자*'' = **Event Loop**.

### 5.2 *libuv — *Node.js 의 *심장**

```
[JavaScript 코드]
       │
       ▼
[V8 Engine]
       │
       ▼
[libuv]
       │
   ┌───┴───────────────┐
   │                   │
[Event Loop]    [Thread Pool (default 4)]
   │                   │
   ├─ Network I/O      ├─ File I/O (blocking)
   ├─ Timers           ├─ DNS lookup
   └─ epoll/kqueue/    └─ Crypto (heavy)
      IOCP
```

- **Event Loop** — *''*비동기 작업을 *큐에 넣고 *완료된 것부터 *콜백 실행''*
- **Thread Pool** — *''*진짜 *블로킹*'' 작업 (file I/O, DNS, crypto) 은 *별도 스레드*

### 5.3 *Event Loop 의 *6 단계**

```
┌──────────────────────────────────────────────┐
│  ┌──────────────┐                            │
│  │   timers     │  setTimeout / setInterval  │
│  └──────────────┘                            │
│  ┌──────────────┐                            │
│  │ pending callbacks │  TCP 에러 등          │
│  └──────────────┘                            │
│  ┌──────────────┐                            │
│  │   idle, prepare   │  내부 용              │
│  └──────────────┘                            │
│  ┌──────────────┐                            │
│  │     poll     │  *대부분의 I/O 콜백 *여기* │
│  └──────────────┘                            │
│  ┌──────────────┐                            │
│  │    check     │  setImmediate              │
│  └──────────────┘                            │
│  ┌──────────────┐                            │
│  │ close callbacks   │                       │
│  └──────────────┘                            │
└──────────────────────────────────────────────┘
   ↑          매 cycle 마이크로태스크 큐 *비움 (Promise 콜백)
   └──────────────────────────────────────────┘
```

### 5.4 *async / await — *콜백 지옥의 *문법적 종결**

```javascript
// 콜백 지옥 (2009 ~ 2015)
fetchUser(id, (err, user) => {
    if (err) return cb(err);
    fetchOrders(user.id, (err, orders) => {
        if (err) return cb(err);
        summarize(orders, (err, summary) => {
            if (err) return cb(err);
            cb(null, summary);
        });
    });
});

// async / await (2017 ~)
async function getSummary(id) {
    const user    = await fetchUser(id);
    const orders  = await fetchOrders(user.id);
    return await summarize(orders);
}
```

*형태는 *동기* 코드, *내부는 *비동기 event loop*. *Promise 의 *문법적 *해체* (syntactic sugar).

### 5.5 *Worker Threads (Node 10.5, 2018) — *''*싱글 스레드의 *예외**

CPU 집약적 작업은 *event loop 를 *막아버림*. 해법:

```javascript
const { Worker } = require('node:worker_threads');

const worker = new Worker('./heavy.js', {
    workerData: { input: 1000000 }
});

worker.on('message', result => console.log(result));
```

- *Worker = *독립적 V8 인스턴스 + 자체 event loop*
- *공유 메모리는 *SharedArrayBuffer 로만*
- *''*Node 는 더 이상 *순수 싱글 스레드가 *아니다*. *단지 *기본이 싱글*''*

### 5.6 *Cluster — *''*프로세스 수준 *멀티 코어 활용**

```javascript
const cluster = require('node:cluster');
const os = require('node:os');

if (cluster.isPrimary) {
    for (let i = 0; i < os.cpus().length; i++) {
        cluster.fork();   // *자식 프로세스로 *Node 인스턴스 *여러 개*
    }
} else {
    require('./app');
}
```

*''*싱글 스레드의 한계를 *프로세스 복제로*''* — *fork () 의 *현대적 활용*.

---

## 6. *3 언어 비교 — *동시성 모델의 *서로 다른 답**

```
[I/O 가 *오래 걸리는* 요청 *10,000 개를 *어떻게 처리하나*]

C (pthread)           — Thread *10,000 개*. *비현실적*
C (epoll)             — *수동 *event loop*. *고성능 *지만 *복잡*
Java 8 (Thread)       — *Thread Pool 200 개*. *나머지는 *큐 대기*
Java 8 (CompletableFuture) — *비동기 체이닝*. *코드 복잡*
Java 21 (Loom)        — *Virtual Thread 10,000 개*. *간단 + 고성능*
Node.js               — *Event Loop 1 개*. *async/await*
Go                    — *Goroutine 10,000 개*. *런타임이 알아서*
```

### 6.1 *각 모델의 *철학*

- **C 의 *철학*** = *''*OS 를 *그대로 노출*. 책임은 *프로그래머*''*
- **Java 의 *철학*** = *''*Thread 추상* + *언어 수준 동기화 + *Loom 으로 *언어가 *비동기를 *숨김*''*
- **Node 의 *철학*** = *''*Event Loop *위에 *언어를 *얹는다*. *비동기를 *언어가 *드러냄*''*

### 6.2 *발전 방향의 *수렴**

흥미롭게도 *3 언어가 *비슷한 곳* 으로 *수렴* 중:

| 시대 | C | Java | Node |
|---|---|---|---|
| 1990s | pthread | Green Thread | (없음) |
| 2000s | epoll | Native Thread + j.u.c | (없음) |
| 2010s | epoll (변함 없음) | CompletableFuture | Promise / async-await |
| 2020s | io_uring | **Virtual Thread (Loom)** | Worker Threads + cluster |

*''*동기처럼 보이지만 *내부는 비동기''* 가 *세 진영의 *공통 종착점*. *Loom 의 *Virtual Thread* 와 *async / await* 는 *서로 다른 방식의 *같은 해법*.

---

## 7. *현장 적용 — *어떤 모델을 *언제 *쓰나*

### 7.1 *워크로드 유형별 *권장*

| 워크로드 | 권장 모델 |
|---|---|
| *대량 동시 HTTP* (대부분 I/O 대기) | Node.js / Go / Java + Loom |
| *CPU 집약 *수치 계산* | C / Rust / Java native compile |
| *분산 작업 큐* | *프로세스 *여러 개* (Spring + multiple JVM, Node cluster) |
| *임베디드 / 실시간* | C / Rust + pthread |
| *복잡한 트랜잭션 + ORM* | Java + Spring (Loom 활용) |

### 7.2 *Spring Boot 의 *2026 권장 *설정*

```yaml
# 단순 API 서버 — *Loom 활성*
spring:
  threads:
    virtual:
      enabled: true

# *Tomcat 의 worker thread 가 Virtual Thread 로
# JDBC blocking 호출도 *OS 스레드 안 막음*
```

### 7.3 *Node.js 의 *2026 권장 *패턴*

- *대부분의 API* — *event loop 그대로*
- *CPU 작업 (이미지 처리, 암호화)* — *Worker Threads*
- *멀티 코어 활용* — *PM2 / cluster 모드*
- *''*ESM + top-level await*''* — *현대 표준*

---

## 8. *''*함정''* — *각 모델의 *고유 위험*

### 8.1 *Thread (Java pre-Loom)*

- *Deadlock* — *두 락을 *서로 다른 순서로 잡으면 *영원히 멈춤*
- *Race condition* — *공유 변수 동기화 빠뜨리면 *비결정적 버그*
- *Thread pool 고갈* — *blocking 호출 누적 → *전체 마비*

### 8.2 *Node.js Event Loop*

- *CPU 작업 시 *event loop 막힘* — *모든 요청 *동시 *멈춤**
- *''*Unhandled promise rejection''* — *조용히 *프로세스 죽음*
- *''*이벤트 큐 지연''* — *bursty 요청 시 *latency 증가*

### 8.3 *Virtual Thread (Java Loom)*

- *Pinned thread* — *synchronized 안에서 blocking 호출 → *OS 스레드 *고정* → *VT 효과 *반감**
- *ThreadLocal* — *수십만 VT 마다 *복사본 → *메모리 폭주*
- *''*Loom 도 *모든 *blocking 을 *지원하지 않음*''* — *예: *legacy native 코드*

---

## 9. 정리 — *''*OS 의 *3 층 추상* 이 *50 년 끝* 에 도착한 곳''*

3 층 추상이 *50 년에 걸쳐 *수렴* 한 *3 가지 진실*:

> 1. ***''*프로세스는 *격리*, 스레드는 *공유*''*** — *수십 년 변함 없음*
> 2. ***''*I/O 대기 중 *놀고 있는 스레드는 *낭비*''*** — *동시성 발전의 *영원한 동력*
> 3. ***''*동기 처럼 *코드 쓰고 *비동기처럼 *동작 한다''*** — *2024 년의 *종착점* (Loom, async/await, goroutine)

각 언어의 *진화 한 줄로*:

- **C** — *''*OS 의 *얇은 wrapper*. *모든 것을 *직접*. *fork ()/pthread/epoll 의 *교과서*''*
- **Java** — *''*Green → Native → ExecutorService → CompletableFuture → *Virtual Thread*. *21 년의 *언어 차원 동시성 추상화 여정*''*
- **Node.js** — *''*Event Loop 하나로 *시작 → Worker Thread / Cluster 로 *확장*. *''*비동기를 *언어가 *드러낸다*''* 의 *대표주자*''*

> **2026 년의 *수렴점***:
>
> *''*개발자가 *동기처럼 코드 쓰고*, *런타임이 *비동기로 처리* 한다''*. *Java 의 Loom, Node 의 async/await, Go 의 goroutine, Rust 의 async — *서로 다른 길* 로 *같은 곳에 도착*.

*프로그램 → 프로세스 → 스레드* 의 *3 층 추상* 을 *''*OS 교과서의 *낡은 개념''* 으로 보지 말자. *그 3 층 위에서 *어떤 동시성 모델이 *왜 *생기고, 사라지고, 다시 부활했는지* 를 *알아야 *현대 백엔드의 *모든 성능 결정* 이 *말이 된다*.

---

## 더 읽으면 좋은 자료

- **Operating System Concepts** (Silberschatz) — *''공룡책''* — *프로세스/스레드의 *기본*
- **The Linux Programming Interface** (Michael Kerrisk) — *Linux 시스템 콜의 *교과서*
- **Java Concurrency in Practice** (Brian Goetz) — *Java 동시성의 *바이블*
- **Node.js Design Patterns** (Mario Casciaro) — *Event Loop 의 *내부 동작*
- **The Art of Multiprocessor Programming** (Maurice Herlihy)
- **Project Loom JEP 444** — *Virtual Thread 의 *공식 설계 문서*
- **libuv 공식 문서** — *Node.js 의 *심장*
- **''The C10K problem''** (Dan Kegel) — *epoll 등 *고동시성의 *역사적 출발점*
- **''Async/await: A Practical Guide''** — *Promise → async 의 *진화 정리*
