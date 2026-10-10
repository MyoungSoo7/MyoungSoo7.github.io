---
layout: post
title: "[CS300 #122] 프로세스 간 통신 — 파이프·공유 메모리·소켓"
date: 2026-10-10 20:02:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, ipc, shared-memory, socket, linux]
---

컴퓨터공학 300 주제 시리즈의 122번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

프로세스는 서로의 메모리를 볼 수 없다. 그래서 데이터를 주고받으려면 커널이 마련한 통로(IPC)를 써야 하고, 대표적인 통로가 파이프, 공유 메모리, 소켓이다. 셋은 복사 횟수, 동기화 책임, 기계 경계를 넘을 수 있는지가 다르다.

## 왜 필요한가

운영체제는 프로세스마다 독립된 가상 주소 공간을 준다. 한 프로세스가 잘못된 포인터를 써도 다른 프로세스는 멀쩡하다. 이 격리 덕분에 시스템이 안정적이다.

하지만 격리는 협력을 어렵게 만든다. 웹 서버는 워커 프로세스에 요청을 나눠 줘야 하고, 데이터베이스는 클라이언트와 대화해야 하고, 브라우저는 탭 프로세스와 GPU 프로세스가 화면을 주고받아야 한다. 여기서 어떤 IPC 를 고르느냐가 성능과 복잡도를 함께 결정한다.

그리고 소켓은 같은 기계 안의 IPC 이면서 동시에 다른 기계와의 통신 수단이다. "한 대에서 여러 대로" 가는 다리가 바로 여기다.

## 핵심 개념

### 두 가지 모델: 메시지 전달과 공유 메모리

| 모델 | 방식 | 장점 | 단점 |
|---|---|---|---|
| 메시지 전달 | 커널을 거쳐 바이트를 복사 | 동기화가 단순, 격리 유지 | 복사 비용, 시스템 콜 비용 |
| 공유 메모리 | 같은 물리 페이지를 양쪽 주소 공간에 매핑 | 복사 없음, 가장 빠름 | 동기화를 직접 해야 함 |

파이프와 소켓은 메시지 전달, 공유 메모리는 이름 그대로다.

### 파이프와 FIFO

익명 파이프(`pipe()`)는 단방향 바이트 스트림이다. 부모가 만들어 `fork` 로 자식에게 물려줘야 하므로 관련 있는 프로세스끼리만 쓴다. 이름 있는 파이프(FIFO, `mkfifo`)는 파일 시스템에 경로가 있어서 관련 없는 프로세스도 열 수 있다. 둘 다 같은 기계 안에서만 동작한다.

### 공유 메모리

POSIX 공유 메모리는 `shm_open()` 으로 이름 있는 객체를 만들고 `ftruncate()` 로 크기를 정한 뒤 `mmap()` 으로 주소 공간에 붙인다. Linux 에서는 이 객체가 `/dev/shm` 아래 tmpfs 파일로 보인다.

```
 프로세스 A 가상 주소       물리 메모리        프로세스 B 가상 주소
 0x7f..1000  ------------>  [ 페이지 ]  <------------ 0x7f..9000
```

같은 페이지를 두 프로세스가 서로 다른 주소로 본다. 한쪽이 쓰면 다른 쪽이 즉시 볼 수 있다. 대신 "언제 다 썼는지" 를 알릴 방법이 없다. 세마포어, 뮤텍스(프로세스 공유 속성), 혹은 다른 IPC 로 신호를 보내야 한다. 동기화 없이 쓰면 경쟁 상태가 생긴다.

### 소켓

소켓은 통신 끝점을 나타내는 fd 다. 주소 체계(domain)와 타입으로 종류가 갈린다.

| 조합 | 쓰임 |
|---|---|
| `AF_UNIX` + `SOCK_STREAM` | 같은 기계, 연결형 스트림. Docker·containerd·PostgreSQL 로컬 접속 |
| `AF_UNIX` + `SOCK_DGRAM` | 같은 기계, 메시지 경계 유지. syslog 계열 |
| `AF_INET`/`AF_INET6` + `SOCK_STREAM` | TCP. 다른 기계와 통신 |
| `AF_INET` + `SOCK_DGRAM` | UDP |

유닉스 도메인 소켓은 파일 시스템 경로를 주소로 쓰고, 네트워크 스택을 거치지 않아 같은 기계 안에서는 TCP 루프백보다 가볍다. 또 `SCM_RIGHTS` 로 열린 fd 자체를 다른 프로세스에 넘기거나, `SO_PEERCRED` 로 상대 프로세스의 PID·UID 를 확인할 수 있다. TCP 로는 할 수 없는 일이다.

프로그래밍 모델은 같다. `socket → bind → listen → accept` 와 `socket → connect`. 그래서 처음에 유닉스 소켓으로 짠 서비스를 나중에 TCP 로 바꾸는 일이 어렵지 않다.

### 그 밖의 IPC

- **시그널**: 데이터 없이 사건만 알린다. 다음 글에서 다룬다.
- **메시지 큐**(POSIX `mq_open`): 커널이 메시지 경계와 우선순위를 유지한다.
- **eventfd**, **파일 잠금**, **mmap 한 일반 파일** 등도 있다.

### 고르는 기준

1. 다른 기계와 통신해야 하나? 그렇다면 소켓 말고는 답이 없다.
2. 데이터가 크고 빈번하며 지연에 민감한가? 공유 메모리를 고려한다. 동기화 비용을 감수할 수 있을 때만.
3. 부모-자식 간 단순 스트림인가? 파이프가 가장 간단하다.
4. 같은 기계의 서비스 간 요청-응답인가? 유닉스 도메인 소켓이 무난하다.

## 직접 해 보기

파이썬 표준 라이브러리로 세 가지를 한 번에 써 본다.

```python
import os, socket
from multiprocessing import Process, shared_memory

# 1) 파이프
r, w = os.pipe()
if os.fork() == 0:
    os.close(r); os.write(w, b"hello via pipe"); os._exit(0)
os.close(w); print(os.read(r, 100)); os.wait()

# 2) 공유 메모리
def writer(name):
    shm = shared_memory.SharedMemory(name=name)
    shm.buf[:5] = b"HELLO"
    shm.close()

shm = shared_memory.SharedMemory(create=True, size=16)
p = Process(target=writer, args=(shm.name,)); p.start(); p.join()
print(bytes(shm.buf[:5]))      # join 이 '다 썼다' 는 동기화 역할
shm.close(); shm.unlink()

# 3) 유닉스 도메인 소켓 쌍
a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
if os.fork() == 0:
    a.close(); b.sendall(b"hello via unix socket"); os._exit(0)
b.close(); print(a.recv(100)); os.wait()
```

출력은 세 줄이다.

```
b'hello via pipe'
b'HELLO'
b'hello via unix socket'
```

공유 메모리 예제에서 `p.join()` 을 빼면 부모가 아직 쓰이지 않은 0 바이트를 읽을 수 있다. 공유 메모리는 동기화를 대신해 주지 않는다는 것을 직접 확인할 수 있다.

## 현업에서는

- **컨테이너 런타임.** `kubelet` 은 containerd 와 유닉스 도메인 소켓 위의 gRPC(CRI)로 대화한다. `docker` CLI 도 기본적으로 `/var/run/docker.sock` 으로 데몬에 접속한다. 이 소켓 파일의 권한이 곧 루트 권한이라는 점이 보안 점검 단골 항목이다.
- **데이터베이스.** PostgreSQL 은 같은 기계 접속에 유닉스 소켓을 쓸 수 있고, 백엔드 프로세스들은 공유 버퍼를 공유 메모리로 나눠 쓴다. 컨테이너에서 `/dev/shm` 이 작게 잡혀 PostgreSQL 이나 크롬이 실패하는 사례가 자주 보고된다.
- **사이드카.** 같은 파드 안의 컨테이너들은 네트워크 네임스페이스를 공유하므로 `localhost` TCP 나 공유 볼륨 위의 유닉스 소켓으로 대화한다.
- **데이터 과학.** 파이썬 멀티프로세싱에서 큰 배열을 피클로 넘기면 복사 비용이 크다. `shared_memory` 나 메모리 매핑 파일로 바꾸면 수 배 빨라지는 경우가 많다.

## 확인 문제

1. 공유 메모리가 파이프보다 빠른 근본 이유와, 그 대가는 무엇인가?
2. 익명 파이프와 FIFO 의 차이는?
3. 유닉스 도메인 소켓만 할 수 있고 TCP 소켓은 할 수 없는 일 두 가지를 들어라.
4. 서로 다른 두 서버의 프로세스가 통신하려면 어떤 IPC 를 써야 하는가?

### 풀이

1. 커널을 거친 복사 없이 같은 물리 페이지를 공유하기 때문이다. 대가는 동기화를 프로그램이 직접 책임져야 한다는 것이다.
2. 익명 파이프는 이름이 없어 fd 를 물려받은 관련 프로세스끼리만 쓰고, FIFO 는 파일 시스템 경로가 있어 관련 없는 프로세스도 열 수 있다.
3. `SCM_RIGHTS` 로 fd 넘기기, `SO_PEERCRED` 로 상대 자격 증명 확인. 파일 권한으로 접근 제어하는 것도 있다.
4. 네트워크 소켓(TCP/UDP)이다. 파이프와 공유 메모리는 기계 경계를 넘지 못한다.

## 더 읽을거리 (References)

- [multiprocessing.shared_memory — Python 공식 문서](https://docs.python.org/3/library/multiprocessing.shared_memory.html)
- [socket — Python 공식 문서](https://docs.python.org/3/library/socket.html)
- [shm_overview(7) — Linux man-pages (man.archlinux.org)](https://man.archlinux.org/man/shm_overview.7)
- [unix(7) — Linux man-pages (man.archlinux.org)](https://man.archlinux.org/man/unix.7)
