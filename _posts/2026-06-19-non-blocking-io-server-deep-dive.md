---
layout: post
title: "*논블로킹 I/O 서버* — *C10K* 부터 *Reactor 패턴*, *epoll / io_uring*, *Netty / Node.js / Nginx* 까지"
date: 2026-06-19 10:00:00 +0900
categories: [networking, system, performance, backend]
tags: [non-blocking-io, nio, epoll, io-uring, reactor-pattern, netty, nodejs, nginx, c10k, event-loop, libuv, backpressure]
---

> *"왜 *Node.js 는 *싱글 스레드* 인데 *동시 접속 10 만* 을 처리 하는가?"* — 이 질문 의 *답* 은 *Node.js 가 아니라* *그 아래 의 *epoll* 에 있다.
>
> *블로킹 I/O 서버* 는 *"1 connection = 1 thread"* 라는 *직관적 모델* 위에서 만들어졌다. *2000 년대 초* 까지 그것 으로 *충분* 했다. *그런데 *C10K (concurrent 10,000 connections)* 가 *현실* 이 되자 *그 모델 은 *벽 에 부딪쳤다*. *스레드 1 만 개* 의 *컨텍스트 스위치* 와 *스택 메모리* 가 *서버 를 *죽였다*.
>
> *논블로킹 I/O 서버* 는 *완전히 다른 철학* 으로 답했다. *"스레드 가 *I/O 를 기다리지 않게 한다"* — *event loop* 하나 가 *수만 connection* 을 *돌아가며 *상태 확인*, *준비 된 것만 처리*. *Nginx 의 *4 worker 가 *10 만 동시 접속* 을 처리하는 *물리적 근거*.
>
> 이 글은 *C10K 문제 → select/poll/epoll/kqueue/io_uring 진화 → Reactor 패턴 → Netty/Node.js/Nginx 구현 → 백프레셔 → Virtual Thread 와 의 비교* 까지 *논블로킹 I/O 서버 의 *모든 층* 을 *분해* 한다.

내 *4 편 연작* 의 *후속편* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
- [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
- [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)

이전 *Virtual Thread 글* 이 *"async 코드 색칠 없이 *기존 동기 코드 의 *효율적 실행"* 의 *길* 을 보여줬다면, 이 글은 *"async 색칠을 *기꺼이 받아들여서 *극한 동시성을 *얻는"* *반대편 의 길* — *Reactor / Netty / Node.js* — 을 *해부* 한다.

---

## TL;DR — *한 줄 결론*

> *블로킹 I/O 서버* 는 *connection 당 thread* 모델 위에서 *컨텍스트 스위치 와 스택 메모리* 에 죽었다. *논블로킹 I/O 서버* 는 *event loop 하나 가 N connection 을 *상태 확인* 후 *준비 된 것만 처리* 하는 *Reactor 패턴* 으로 답했다. 그 *상태 확인 의 *심장* 이 *epoll (Linux) / kqueue (BSD) / IOCP (Windows) / io_uring (Linux 5.1+)*. *Nginx 의 *worker 4 개 가 *10 만 connection* 을 처리하는 이유. *대신 *async 색칠* 의 *복잡성 비용* 을 지불 — *JDK 21+ Virtual Thread 가 *그 비용 없이 *비슷한 효과* 를 노린다*. 둘 다 *내부적으로 *epoll 위에서 돈다* — *추상화 의 *높이* 만 다를 뿐.

---

## 1. *블로킹 I/O 의 *모델 과 한계*

### 1.1 *전통 모델 — *thread-per-connection*

```c
// 의사 코드 — 1990 년대 표준
int server = socket(AF_INET, SOCK_STREAM, 0);
bind(server, ...);
listen(server, 128);

while (1) {
    int client = accept(server, ...);    // 새 connection 받기
    pthread_create(&tid, NULL,
        handle_client, &client);          // 스레드 하나 띄워서 처리
}

void* handle_client(void* arg) {
    int fd = *(int*)arg;
    char buf[4096];
    while (1) {
        int n = read(fd, buf, sizeof(buf));   // ← *블로킹* — 데이터 올 때까지 대기
        if (n <= 0) break;
        write(fd, buf, n);                    // ← *블로킹* — 보낼 수 있을 때까지 대기
    }
    close(fd);
    return NULL;
}
```

> *직관적* 이고 *코드 가 *읽기 쉽다*. *각 connection 의 *상태 가 *스택 에 자연스럽게 *저장*. *동시성 = 스레드 수*.

### 1.2 *왜 *C10K 에서 깨졌나*

| 자원 | 1 connection = 1 thread 의 *비용* |
|---|---|
| 스택 메모리 (기본 1 MB) | *10K conn × 1 MB = 10 GB RAM* |
| 컨텍스트 스위치 | *N 스레드 가 라운드 로빈* → *cache 가 매 스위치 마다 무효화* → *throughput 급락* |
| 커널 메모리 (TCB, kernel stack) | 수십 KB × N |
| 스케줄러 부하 | *런큐 N 길이* — O(log N) 또는 O(N) 의 *스케줄링 결정* |

> *Dan Kegel* 이 *C10K 페이지 (1999)* 에서 *문제 정의* 한 그것 — *"한 서버가 *동시에 10,000 client 를 처리 할 수 있나?"* 가 *불가능 함 의 *증명*.

### 1.3 *Thread pool 의 *부분 해결*

```text
while accept:
    connection = accept()
    thread_pool.submit(connection)
```

→ *스레드 수* 를 *고정* (예: 200) → *메모리 안정*. *단* :
- *200 스레드 가 *모두 I/O 대기 중* 이면 *201 번째 connection 은 대기* — *limit 가 *낮아짐*.
- *Servlet 컨테이너 의 *전통 모델*. *Tomcat BIO connector* (deprecated).

→ *thread pool 은 *thread-per-connection 의 *완화 일 뿐*, *근본 해결 이 아님*. *connection 수 > pool 크기* 가 되는 순간 *대기 발생*.

---

## 2. *C10K 의 *해법 — *event-driven I/O*

### 2.1 *핵심 통찰*

> *대부분의 connection 은 *대부분의 시간 *I/O 를 기다린다*. 그 *대기 중인 connection* 마다 *스레드를 *할당하는 것 은 *낭비*. *모든 connection 을 *한 곳 에 등록* 해두고, *데이터 가 *실제로 도착한 connection 만* 처리 하면 되지 않나?*

이게 *event-driven I/O* 의 *철학*.

### 2.2 *3 단계 진화*

1. **select / poll** (1983) — *N 개 FD 를 *모니터링*, *준비된 것* 만 *돌려줌*. *O(N) 스캔* 의 한계.
2. **epoll (Linux 2.6, 2002) / kqueue (FreeBSD, 2000) / IOCP (Windows, 1995)** — *커널 이 *내부 자료구조 로 *FD 추적* → *준비된 것만 *O(1) 로 돌려줌*.
3. **io_uring (Linux 5.1, 2019)** — *system call 자체 를 *비동기화*. *epoll 보다 *시스템콜 횟수 ↓*, *zero-copy 친화*.

### 2.3 *select — 시작점*

```c
fd_set readfds;
struct timeval tv;

FD_ZERO(&readfds);
FD_SET(server_fd, &readfds);
FD_SET(client1_fd, &readfds);
FD_SET(client2_fd, &readfds);
// ... 최대 FD_SETSIZE (보통 1024) 개

tv.tv_sec = 5; tv.tv_usec = 0;
int n = select(maxfd + 1, &readfds, NULL, NULL, &tv);

if (n > 0) {
    if (FD_ISSET(server_fd, &readfds)) accept_new_connection();
    if (FD_ISSET(client1_fd, &readfds)) handle_client(client1_fd);
    // ...
}
```

**한계** :
- *FD_SETSIZE = 1024* — *컴파일 타임 상수*, 그 이상 모니터링 불가.
- *매 호출 마다 *전체 fd_set 을 *커널 ↔ 유저 공간 *복사*.
- *모든 FD 를 *O(N) 스캔* — *9,999 FD 중 *1 개만 ready* 라도 *N 회 검사*.

### 2.4 *poll — *FD_SETSIZE 제거*

```c
struct pollfd fds[10000];
fds[0].fd = server_fd; fds[0].events = POLLIN;
// ... 10,000 개

int n = poll(fds, 10000, -1);
for (int i = 0; i < 10000; i++) {
    if (fds[i].revents & POLLIN) handle(fds[i].fd);
}
```

**개선** :
- *FD 개수 제한 없음*.

**여전한 한계** :
- *매 호출 마다 *전체 배열 복사*.
- *준비 여부 확인 이 *O(N) 스캔*.

### 2.5 *epoll — *진짜 해결*

```c
int epfd = epoll_create1(0);

struct epoll_event ev;
ev.events = EPOLLIN;
ev.data.fd = server_fd;
epoll_ctl(epfd, EPOLL_CTL_ADD, server_fd, &ev);     // 한 번만 등록

struct epoll_event events[64];
while (1) {
    int n = epoll_wait(epfd, events, 64, -1);       // ★ 준비된 것만 돌아옴
    for (int i = 0; i < n; i++) {
        if (events[i].data.fd == server_fd) {
            int client = accept(server_fd, ...);
            ev.events = EPOLLIN | EPOLLET;          // edge-triggered
            ev.data.fd = client;
            epoll_ctl(epfd, EPOLL_CTL_ADD, client, &ev);
        } else {
            handle_data(events[i].data.fd);
        }
    }
}
```

**핵심 차이** :

| | select / poll | epoll |
|---|---|---|
| FD 등록 | 매 호출 마다 *전체 복사* | *한 번* 등록, *커널 이 기억* |
| 준비 확인 | *O(N) 스캔* | *O(준비된 개수)* |
| 최대 FD | 1024 (select) / 무제한 (poll) | *수십만* |
| 트리거 | level-triggered | level + *edge-triggered* 선택 가능 |

> *epoll 의 *진짜 혁신* 은 *준비된 것 만 *돌아오는 것*. *10,000 FD 중 *1 개 ready* 면 *그 1 개 만 돌아옴* — *O(N) → O(준비된 개수)*.

### 2.6 *Level-triggered vs Edge-triggered*

```text
LT (Level-Triggered) : 데이터 가 *남아 있는 동안* 계속 알림
ET (Edge-Triggered)  : 데이터 가 *새로 도착할 때만* 알림 (한 번)
```

**ET 의 장점** :
- *epoll_wait 호출 횟수 ↓*. 한 번 알림 받고 *완전히 비울 때까지* read.

**ET 의 함정** :
- *반드시 *EAGAIN 까지 *모두 read* 해야 함. 안 비우면 *다음 알림 안 옴* → *연결 멈춤*.
- *non-blocking FD 와 *함께 사용 필수*.

```c
while (1) {
    int n = read(fd, buf, sizeof(buf));
    if (n == -1 && errno == EAGAIN) break;     // 완전히 비움
    if (n == 0) { close(fd); break; }          // 상대방 종료
    process(buf, n);
}
```

→ *Nginx, Netty, Node.js 모두 *ET 사용* — *극한 성능* 을 위해.

### 2.7 *io_uring — *async 의 *진정한 미래*

epoll 도 *완전한 비동기 가 아니다* — `read()` 같은 *실제 I/O* 는 *여전히 syscall*. *모든 system call 자체를 *비동기화* 한 게 *io_uring*.

```text
[Submission Queue]    [Completion Queue]
  (user → kernel)       (kernel → user)

user 가 SQE (Submission Queue Entry) push:
  - read fd=10, buf=..., len=4096
  - write fd=11, buf=..., len=2048

kernel 이 처리 후 CQE (Completion Queue Entry) push:
  - read 완료, n=4096
  - write 완료, n=2048

user 는 polling 또는 wait 으로 CQE 수확
```

**장점** :
- *Syscall 횟수 ↓* — 여러 작업을 *한 번에 submit*.
- *Zero-copy 친화* — 버퍼 등록 후 *그대로 재사용*.
- *fixed file* / *fixed buffer* 로 *각 작업 마다 *FD lookup / 메모리 복사 제거*.
- *대부분 의 syscall* 을 *모두 지원* (`read`, `write`, `accept`, `connect`, `sendmsg`, `fsync`, ...) — *epoll 처럼 *socket 한정* 이 아님.

**한계** :
- *Linux 5.1+* — *상대적으로 신규*.
- *API 복잡도 ↑* — `liburing` 으로 일부 완화.
- *보안 우려* — *과거 kernel CVE 다수*. 일부 컨테이너 환경 (Google) 에서 *비활성화*.

**현재 채택** :
- *PostgreSQL 17* — async I/O 옵션.
- *Nginx (실험적)*.
- *Node.js / Bun* — *libuv 내부 에서 *조건부 활용*.
- *JVM* — *Netty io_uring transport*.

---

## 3. *Reactor 패턴 — *논블로킹 서버 의 *설계 패턴*

### 3.1 *기본 구조*

> *Reactor* = *event demultiplexer (epoll / kqueue / IOCP)* + *event handler*.

```text
                  ┌────────────────┐
                  │  Event Loop    │
                  │  (single       │
                  │   thread)      │
                  └───┬────────┬───┘
                      │        │
            epoll_wait│        │ dispatch
                      │        │
              ┌───────▼────┐   ▼
              │ FD events  │ ┌─────────┐
              │ ready list │ │ Handler │
              └────────────┘ │  - read │
                             │  - write│
                             │  - close│
                             └─────────┘
```

**Pseudo code** :
```python
while True:
    events = epoll_wait()
    for event in events:
        if event.is_new_connection():
            accept_and_register()
        elif event.is_readable():
            data = read_non_blocking(event.fd)
            process_data(data)
        elif event.is_writable():
            write_pending_data(event.fd)
```

→ *단일 스레드 가 *수만 FD 를 *처리*. 각 핸들러 는 *짧고 *논블로킹*.

### 3.2 *변종 — Multi-Reactor (Main + Sub)*

*Doug C. Schmidt* 의 *논문 (1995)* 에서 제안.

```text
        [Acceptor Reactor]
         (1 thread, listen)
                │
                │ accept new conn → 분배
                ▼
   [Sub Reactor 1]  [Sub Reactor 2]  [Sub Reactor N]
   (worker thread)   (worker thread)   (worker thread)
   epoll_wait          epoll_wait          epoll_wait
```

**왜 *2 단계*** :
- *Acceptor 의 *부하 (accept) 와 *worker 의 *부하 (I/O 처리) 분리*.
- *worker 가 *CPU core 수 만큼* — *각 코어 가 *독립 event loop*.
- *cache locality* — *한 connection 의 *모든 처리 가 *한 worker* 에서.

→ *Netty 의 *NioEventLoopGroup (boss + worker) 구조* 가 *바로 이것*.

### 3.3 *Proactor 와 의 차이*

| | Reactor | Proactor |
|---|---|---|
| *"준비됨" 알림 후* | user 가 *직접 read/write* | kernel 이 *read/write 후 결과 전달* |
| 모델 | *Sync 논블로킹* | *Async 논블로킹* |
| 구현 | epoll, kqueue | IOCP (Windows), io_uring (Linux) |
| 사용 라이브러리 | Netty NIO, Nginx, Node.js | Netty AIO/io_uring, ASIO |

> *Proactor 가 *더 추상화 가 높다* — kernel 이 *데이터 까지 *준비해서 *알림*. 대신 *kernel 이 *user 의 buffer 를 알아야 함* → *복잡한 인터페이스*.

---

## 4. *구현체 비교 — *Nginx / Node.js / Netty / Tomcat NIO*

### 4.1 *Nginx — *C, multi-process + epoll*

```text
[Master process]
   ├ fork ─→ [Worker 1] — epoll loop (수만 conn)
   ├ fork ─→ [Worker 2] — epoll loop
   ├ fork ─→ [Worker 3] — epoll loop
   └ fork ─→ [Worker 4] — epoll loop
                ↑
        (코어 수 만큼)
```

**특징** :
- *프로세스* 단위 (스레드 가 *아님*) — *shared-nothing*.
- *각 worker 가 *독립 epoll loop* — *수만 connection*.
- *configuration reload 가 *graceful* — old worker drain, new worker accept.
- *각 worker = 하나의 코어 *고정* (CPU affinity).

**왜 *압도적으로 빠른가* :
- C 코드 + *zero copy (`sendfile`, `splice`)*.
- *논블로킹 epoll ET*.
- *Memory pool* — 매 요청 마다 malloc 안 함.
- *Lua 모듈* (OpenResty) 로 *Lua 가 *C 와 같은 event loop 에서* 실행.

### 4.2 *Node.js — *V8 + libuv*

```text
[V8 JavaScript Engine]
        ↑↓
[libuv]
   ├ Event loop (single thread)
   ├ Thread pool (default 4 threads — for blocking ops)
   │   └ DNS lookup, file I/O (POSIX 의 *비동기 file API 부재*)
   └ epoll / kqueue / IOCP / io_uring (조건부)
```

**왜 *싱글 스레드 가 *10K + 처리 하나* :
- *JS 코드 자체 는 *event loop 1 스레드*.
- *I/O 는 *libuv 가 *epoll 위에서 *비동기 처리*.
- *CPU bound 작업 만 *thread pool* 사용.

**한계** :
- *CPU 집약 작업* (큰 JSON parse, crypto) 이 *event loop 막음* — *지연 spike*.
- *worker_threads* 모듈로 *별도 스레드* 가능 (cluster 와 함께).

**Bun / Deno** :
- *libuv 대신 *자체 비동기 런타임* — 일부 더 빠름, 일부 호환성 차이.

### 4.3 *Netty — *Java NIO + epoll native*

```java
EventLoopGroup bossGroup = new NioEventLoopGroup(1);          // accept 전담
EventLoopGroup workerGroup = new NioEventLoopGroup();         // 코어 수 만큼 (기본)

ServerBootstrap b = new ServerBootstrap()
    .group(bossGroup, workerGroup)
    .channel(NioServerSocketChannel.class)
    .childHandler(new ChannelInitializer<SocketChannel>() {
        @Override
        protected void initChannel(SocketChannel ch) {
            ch.pipeline()
                .addLast(new HttpServerCodec())
                .addLast(new MyBusinessHandler());
        }
    });
b.bind(8080).sync();
```

**구조** :
- *Boss event loop* — *accept 만*.
- *Worker event loop* — *CPU core 수* — 각자 *epoll loop*.
- *Channel pipeline* — *decoder → handler → encoder* 의 *작은 단계 의 체인*.

**고급 기능** :
- *EpollEventLoopGroup* (Linux native) — *순수 Java NioEventLoopGroup 보다 *빠름*. *epoll ET + native syscall*.
- *IOUringEventLoopGroup* — *io_uring 사용* (실험적이지만 *프로덕션 채택 사례* 증가).
- *ByteBuf* — *zero-copy / pooled buffer*. JDK ByteBuffer 보다 효율적.
- *Backpressure* — `channel.isWritable()` 로 *수신 측 처리 속도 *조절*.

**누가 쓰나** :
- *Spring WebFlux* (Reactor Netty).
- *gRPC Java*.
- *Akka HTTP*.
- *Apache Kafka client*.
- *Cassandra*.

### 4.4 *Tomcat NIO / NIO2 — *전통 적인 *반쯤 NIO**

Tomcat 의 *Connector* :
- *BIO (blocking)* — *deprecated*.
- *NIO* — *기본*. *accept + read header 가 *논블로킹 epoll*. 그 후 *handler 는 *thread pool* (전통적 스레드).
- *NIO2 (APR)* — *async I/O 까지*.
- *Spring Boot 3.2 + Virtual Thread* — *handler 가 *VT* 위에서 실행, *NIO accept layer + VT thread* 의 *하이브리드*.

> *Tomcat NIO* 는 *완전한 Reactor* 가 *아니다*. *수십만 connection* 의 *극한 동시성* 보다 *수천 connection + 친숙한 servlet API* 의 *균형*. *Spring MVC* 의 *현실적 선택*.

---

## 5. *Backpressure — *논블로킹의 *숨은 도전*

### 5.1 *왜 *backpressure 가 *필요한가*

```text
[빠른 producer] → [event loop] → [느린 consumer]
   1000 msg/s         ↓              100 msg/s
                  (큐에 쌓임)
                       ↓
                  (메모리 폭발)
```

*논블로킹 의 *치명적 함정* :
- *수신 측이 *늦다고 *senders 가 *멈추지 않음*.
- *큐 가 *무한히 쌓임* → *OOM*.

### 5.2 *처방 — 흐름 제어*

**1. *Bounded queue + drop / block***:
```java
// Netty 의 channel.isWritable() — 송신 버퍼가 *낮은 워터마크* 를 넘으면 false
if (ctx.channel().isWritable()) {
    ctx.writeAndFlush(msg);
} else {
    // 잠시 멈추거나 버림
}
```

**2. *TCP backpressure***:
- TCP 의 *receive window* 가 *자체 backpressure*.
- 수신 측 application 이 *read 가 늦으면* → kernel buffer 가 *참* → *window 줄어듦* → *송신 측 TCP 가 *멈춤*.
- *단* — *kernel buffer 가 *크면 *수십 MB 까지 쌓일 수 있음*. *application level 흐름 제어* 가 *더 명시적*.

**3. *Reactive Streams***:
- *Project Reactor / RxJava* 의 *Backpressure 모델*.
- *consumer 가 *"나는 N 개 더 받을 수 있다"* 라고 *request*. 그만큼만 emit.
- *push 모델 → pull 모델 의 *전환*.

```java
Flux.create(sink -> {
    sink.onRequest(n -> {
        for (long i = 0; i < n; i++) {
            sink.next(produce());      // 요청 받은 만큼만
        }
    });
}, FluxSink.OverflowStrategy.BUFFER);
```

**4. *Application-level rate limit***:
- *Resilience4j*, *Bucket4j* 같은 *RateLimiter*.

> *backpressure 는 *비동기 시스템 의 *가장 자주 잊혀지는 *설계 요소* — 작동 잘 하다가 *부하 spike 에서 *조용히 OOM* 으로 *죽는다*.

---

## 6. *Async 색칠 (Color of Functions) — *논블로킹 의 *비용*

### 6.1 *문제*

*Bob Nystrom 의 *2015 글* "What Color Is Your Function?" :

> *비동기 함수* 와 *동기 함수* 가 *서로 호환 안 됨*. *모든 callstack 이 *비동기로 색칠* 되어야 함.

```javascript
// Node.js — async/await 는 *전염* 됨
async function fetchUser(id) {
    return await db.query("SELECT ...");   // ← async 함수만 await 가능
}

// 어디서든 호출하려면 *호출자 도 async* 여야 함
async function handleRequest(req) {
    const user = await fetchUser(req.id);   // 호출자도 async
    return user;
}
```

```java
// Project Reactor — Mono / Flux 가 *전염*
public Mono<User> fetchUser(Long id) {
    return r2dbc.sql("SELECT ...").execute();
}

// 모든 상위 함수 가 Mono / Flux 반환
public Mono<Response> handleRequest(Request req) {
    return fetchUser(req.id).map(this::toResponse);
}
```

### 6.2 *비용*

- *Stack trace 가 *비대*해지고 *읽기 어려움*.
- *Debugger 가 *제대로 작동 안 함* (각 await / map 마다 *컨텍스트 분리*).
- *기존 sync 라이브러리* 와 *호환 어려움* (예: 기존 JDBC, blocking client).
- *학습 비용 ↑*.

### 6.3 *Virtual Thread 의 *반격*

[*Virtual Thread 글*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html) 에서 다룬 그것 :

> *VT 는 *async 색칠 없이 *기존 동기 코드 가 *효율적으로 도는 *철학*. *Continuation 으로 *마운트/언마운트* → *수십만 동시성*.

**비교** :

| | 논블로킹 (Reactor / Netty) | Virtual Thread |
|---|---|---|
| 코드 스타일 | *async/await*, *Mono/Flux* | *기존 동기 코드* 그대로 |
| 극한 성능 (cold) | *더 빠름* (no continuation overhead) | 약간 느림 |
| 코드 읽기 / 디버깅 | *어려움* | *쉬움* |
| 기존 lib 호환 | *limited* | *full* |
| Pinning 위험 | 없음 | `synchronized` + native frame |
| 학습 곡선 | *높음* | *낮음* |

> *극한 throughput* 이 *최우선* 이면 *Netty / Nginx* 가 *여전히 정답*. *대부분의 비즈니스 코드* 는 *Virtual Thread* 가 *코드 비용 적게 *비슷한 동시성* 을 *얻는 길*.

---

## 7. *실전 — *언제 *논블로킹 서버를 *선택* 하나*

### 7.1 *논블로킹 이 *압도적으로 *유리한 경우*

- *수만 ~ 수십만 동시 connection* (long polling, WebSocket, SSE, IoT, 게임).
- *대부분 connection 이 *대부분 시간 *idle* (예: 채팅 서버 — 메시지 가끔 도착).
- *극한 throughput* 필요 (CDN 노드, gateway, proxy).
- *낮은 latency* 가 *생명 (HFT, 실시간 비드 시스템)*.

### 7.2 *Virtual Thread 가 *충분한 경우*

- *수천 ~ 수만 동시 요청 의 *전통적 REST API*.
- *복잡한 비즈니스 로직* — *async 색칠 비용* 이 *부담*.
- *기존 sync 라이브러리* 의존 (JDBC, MyBatis, ...).
- *Spring Boot* 의 *생태계* 활용 (대부분의 라이브러리 가 *VT 친화*).

### 7.3 *하이브리드*

- *Edge layer* — *Nginx + 논블로킹 (TLS termination, 라우팅, rate limit)*.
- *Application layer* — *Spring Boot + VT (비즈니스 로직)*.
- *Internal layer* — *Netty / gRPC (서비스 간 통신)*.

→ *각 층 에 *맞는 도구*. *모든 곳 에 *Reactive* 는 *과잉*.

---

## 8. *성능 비교 — *숫자 의 *현실*

(*특정 워크로드 / 하드웨어 의 *예시*. 일반화 위험 — *반드시 *자기 워크로드 로 *측정*.)

```text
[64-byte echo, 4 vCPU, 10K concurrent clients]

Server                  RPS       p99 latency   Memory
─────────────────────────────────────────────────────────
Tomcat BIO              ~5K       80 ms         2.5 GB    (스레드 수 한계)
Tomcat NIO              ~25K      35 ms         500 MB
Spring Boot + VT (JDK21) ~28K     30 ms         500 MB
Netty (epoll native)    ~80K      8 ms          200 MB
Nginx (static, sendfile) ~250K    2 ms          50 MB
Node.js (libuv)         ~50K      15 ms         300 MB
```

> *Nginx 의 *압도적 성능* 은 *논블로킹 + zero-copy + C* 의 *3 박자*. *정적 파일 서빙* 에선 *어떤 application 서버도 *근접 못 함*.
>
> *Netty 와 *VT* 의 *gap* 은 *3 배 정도* — *극한 동시성* 워크로드 가 *아니면 *VT* 의 *코드 단순성* 이 *더 가치 있음*.

---

## 9. *디버깅 / 모니터링*

### 9.1 *논블로킹 서버 의 *어려움*

- *Stack trace 가 *단순한 동기 호출 의 *연속이 아님* — *Reactor 에선 *Mono.map() 의 lambda 가 *언제 실행됐는지* 추적 어려움.
- *Event loop 멈춤 (block)* — *한 핸들러 가 *blocking call* 을 했다면 *그 worker 의 *모든 connection 이 *멈춘다*.

### 9.2 *대처*

**1. *Event loop 차단 감지*** :
```bash
# Netty
-Dio.netty.leakDetection.level=PARANOID
-Dio.netty.eventLoopThreads=8

# Node.js
node --inspect app.js   # Chrome DevTools 로 event loop lag 시각화

# Spring WebFlux — BlockHound 라이브러리
BlockHound.install();   // event loop 안 *blocking 호출 감지 시 throw*
```

**2. *Distributed tracing***:
- *OpenTelemetry* — 비동기 컨텍스트 *전파* 자동.
- *Reactor 의 *Context API* / Netty 의 *AttributeMap*.

**3. *Heap dump + thread dump***:
- *event loop 가 *어디서 blocked* 되었는지 — thread dump 가 *답*.
- *JFR* — JVM 이면 *Java Flight Recorder* 가 *async 추적 까지 지원*.

---

## 10. *결론 — *epoll 위에서 *모두 가 *돈다*

> *Nginx, Node.js, Netty, libuv, Tomcat NIO, Virtual Thread (file I/O 영역)* — *결국 *모두 *epoll (또는 kqueue / IOCP / io_uring) 위에서 돈다*. *다른 점 은 *추상화 의 높이*.

**계층**:
```text
[ 비즈니스 코드 (개발자 가 쓰는 것) ]
       ↓
[ Virtual Thread / Reactor / async-await / callback ]  ← 추상화 다양
       ↓
[ JVM / libuv / V8 / 언어 런타임 ]
       ↓
[ epoll / kqueue / IOCP / io_uring ]            ← 모두 여기 위
       ↓
[ Linux / BSD / Windows kernel ]
       ↓
[ NIC (네트워크 카드 의 *DMA, ring buffer*) ]
```

> *논블로킹 I/O 서버 의 *진짜 본질* 은 *"스레드 가 *I/O 를 기다리지 않게 한다"*. 이 한 문장 이 *C10K 의 해법*, *Reactor 패턴*, *Netty 의 구조*, *epoll 의 API*, *Virtual Thread 의 마운트/언마운트* 까지 *모두 의 *공통 동기*.

*어떤 추상화 를 선택* 할지는 *워크로드 / 팀 의 숙련도 / 생태계* 의 *함수*. 그러나 *그 아래 에서 *epoll 이 *돌고 있다는 사실* 을 *모르면* — *알람이 울릴 때 *어디 를 *볼지 *모른다*.

*수만 connection 이 *우아하게 흐르게 하는* — *그게 *2026 년 *백엔드 서버 의 *기본기*.

---

## *참고*

- Dan Kegel, *The C10K Problem* (1999) — [kegel.com/c10k.html](http://www.kegel.com/c10k.html). *문제 정의 의 *원전*.
- Douglas C. Schmidt, *Reactor: An Object Behavioral Pattern for Demultiplexing and Dispatching Handlers for Synchronous Events* (1995).
- Jens Axboe, *Efficient IO with io_uring* — kernel.dk 문서.
- Norman Maurer, *Netty in Action* (Manning).
- *Linux man pages* : `epoll(7)`, `epoll_wait(2)`, `io_uring(7)`.
- Bob Nystrom, *What Color is Your Function?* (2015).
- 자매편 :
  - [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
  - [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
  - [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
  - [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
