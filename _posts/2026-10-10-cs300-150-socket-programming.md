---
layout: post
title: "[CS300 #150] 소켓 프로그래밍 — 네트워크를 파일처럼 다루는 인터페이스"
date: 2026-10-10 20:30:00 +0900
categories: [cs]
tags: [cs300, networking, socket, epoll, python]
---

컴퓨터공학 300 주제 시리즈의 150번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

소켓은 운영체제가 응용 프로그램에 내주는 네트워크 통신의 끝점이다. `socket → bind → listen → accept`(서버)와 `socket → connect`(클라이언트) 순서로 열고, `send/recv` 로 바이트를 주고받는다.

## 왜 필요한가

HTTP 클라이언트, DB 드라이버, 메시지 큐 라이브러리는 모두 결국 소켓 API 를 부른다. 라이브러리가 감춰 주는 동안은 몰라도 되지만, 다음 순간에는 반드시 알아야 한다.

- `recv()` 가 보낸 데이터의 절반만 돌려줘서 JSON 파싱이 깨질 때.
- 서버를 재시작했더니 "Address already in use" 로 뜨지 않을 때.
- 동시 접속이 늘자 스레드가 수천 개가 되어 서버가 멈출 때.

이 세 문제는 각각 스트림 경계, 소켓 옵션, I/O 다중화라는 소켓의 기본 개념에서 나온다.

## 핵심 개념

### 버클리 소켓 API

소켓 API 는 1980년대 BSD 유닉스에서 나왔고 지금은 POSIX 표준이다. 리눅스에서는 소켓도 파일 디스크립터라, `read`/`write`/`close` 를 그대로 쓸 수 있다.

```
서버                                클라이언트
socket()                            socket()
bind(주소, 포트)
listen(backlog)
accept()  <---- 3-way 핸드셰이크 ----  connect(서버 주소)
  └ 새 소켓(연결 전용) 반환
recv()/send()  <---- 데이터 ---->    send()/recv()
close()                             close()
```

- `socket(AF_INET, SOCK_STREAM)` 은 IPv4 TCP, `SOCK_DGRAM` 은 UDP 다. `AF_INET6` 은 IPv6 다.
- `listen()` 한 소켓은 연결을 받기만 한다. `accept()` 는 연결마다 새 소켓을 돌려준다. 그래서 서버는 듣는 소켓 하나와 연결 소켓 여러 개를 갖는다.
- 연결 하나는 (프로토콜, 출발지 IP, 출발지 포트, 목적지 IP, 목적지 포트) 5-튜플로 구별된다. 서버 포트가 80 하나여도 클라이언트 쪽 값이 다르면 서로 다른 연결이다.

### 스트림에는 경계가 없다

TCP 는 바이트 스트림이다. `send(b"AB")` 와 `send(b"CD")` 를 했어도 받는 쪽은 `b"ABCD"` 를 한 번에, 혹은 `b"A"`, `b"BCD"` 로 나눠 받을 수 있다. 또 `send()` 는 요청한 바이트를 다 보내지 못하고 일부만 보냈다고 반환할 수 있다.

그래서 응용 프로토콜은 메시지 경계를 스스로 정해야 한다. 흔한 방법은 셋이다.

| 방법 | 예 |
|---|---|
| 구분자 | 줄바꿈으로 끝나는 텍스트 프로토콜(SMTP, Redis 의 일부) |
| 길이 접두사 | 앞 4바이트에 길이를 쓰고 그만큼 읽기(많은 바이너리 프로토콜) |
| 헤더에 길이 | HTTP/1.1 의 `Content-Length` |

### 블로킹과 다중화

기본 소켓은 블로킹이다. `recv()` 는 데이터가 올 때까지 멈춘다. 연결 하나에 스레드 하나를 붙이면 코드는 단순하지만, 연결이 수만 개가 되면 스레드 비용이 감당되지 않는다.

대안은 하나의 스레드가 여러 소켓을 감시하는 I/O 다중화다.

- `select`/`poll`: 감시할 소켓 목록을 매번 커널에 넘긴다. 소켓 수에 비례해 느려진다.
- `epoll`(리눅스), `kqueue`(BSD 계열): 관심 목록을 커널에 등록해 두고 "준비된 것"만 받는다. 대규모 서버의 기반이다.

파이썬의 `selectors` 모듈은 플랫폼에 맞는 최선의 방식을 고르고, `asyncio` 는 그 위에 이벤트 루프를 얹는다. Node.js, nginx, Go 런타임도 같은 원리로 동작한다.

### 자주 쓰는 소켓 옵션

| 옵션 | 효과 |
|---|---|
| `SO_REUSEADDR` | TIME-WAIT 연결이 남아 있어도 같은 포트에 다시 bind 할 수 있게 한다. 서버 재시작 때 필요 |
| `SO_KEEPALIVE` | 오래 조용한 연결에 TCP keepalive 탐침을 보낸다 |
| `TCP_NODELAY` | 작은 패킷을 모아 보내는 Nagle 알고리즘을 끈다. 지연에 민감한 요청-응답에 쓴다 |
| `SO_RCVBUF`/`SO_SNDBUF` | 소켓 버퍼 크기. 고대역·장거리 전송에서 중요 |
| 타임아웃 | 파이썬은 `settimeout()`. 연결·읽기 타임아웃을 안 걸면 한없이 기다린다 |

## 직접 해 보기

길이 접두사로 메시지를 구분하는 에코 서버를 `selectors` 로 만든다. 클라이언트는 일부러 메시지를 잘게 쪼개 보내, 서버가 경계를 제대로 복원하는지 본다.

```python
import selectors, socket, struct, threading, time

sel = selectors.DefaultSelector()
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0)); srv.listen(); srv.setblocking(False)
sel.register(srv, selectors.EVENT_READ, data=None)
PORT = srv.getsockname()[1]
bufs = {}

def serve(stop_after):
    handled = 0
    while handled < stop_after:
        for key, _ in sel.select(timeout=1):
            if key.data is None:                       # 새 연결
                conn, _ = key.fileobj.accept(); conn.setblocking(False)
                sel.register(conn, selectors.EVENT_READ, data="conn"); bufs[conn] = b""
                continue
            conn = key.fileobj
            chunk = conn.recv(4096)
            if not chunk:                              # 상대가 닫음
                sel.unregister(conn); conn.close(); continue
            bufs[conn] += chunk
            while len(bufs[conn]) >= 4:                # 길이 접두사로 메시지 꺼내기
                n = struct.unpack("!I", bufs[conn][:4])[0]
                if len(bufs[conn]) < 4 + n: break
                msg = bufs[conn][4:4+n]; bufs[conn] = bufs[conn][4+n:]
                conn.sendall(struct.pack("!I", len(msg)) + msg.upper())
                handled += 1

def recv_exact(s, n):
    out = b""
    while len(out) < n:
        part = s.recv(n - len(out))
        if not part: raise ConnectionError("closed early")
        out += part
    return out

def client(name, msgs):
    with socket.create_connection(("127.0.0.1", PORT), timeout=3) as c:
        wire = b"".join(struct.pack("!I", len(m)) + m for m in msgs)
        for i in range(0, len(wire), 3):               # 3바이트씩 쪼개서 전송
            c.sendall(wire[i:i+3]); time.sleep(0.001)
        for _ in msgs:
            n = struct.unpack("!I", recv_exact(c, 4))[0]
            print(name, "<-", recv_exact(c, n))

t = threading.Thread(target=serve, args=(4,)); t.start()
c1 = threading.Thread(target=client, args=("A", [b"hello", b"socket"]))
c2 = threading.Thread(target=client, args=("B", [b"length-prefix", b"ok"]))
c1.start(); c2.start(); c1.join(); c2.join(); t.join()
sel.close(); srv.close()
```

출력 순서는 스레드 스케줄에 따라 바뀔 수 있지만 내용은 같다.

```
A <- b'HELLO'
B <- b'LENGTH-PREFIX'
A <- b'SOCKET'
B <- b'OK'
```

3바이트씩 쪼개 보냈는데도 메시지 네 개가 온전히 복원됐다. 서버 스레드는 하나뿐인데 두 클라이언트를 동시에 처리했다. 클라이언트의 `recv_exact` 처럼 "원하는 길이를 다 받을 때까지 반복"하는 함수는 소켓 코드의 기본 부품이다.

## 현업에서는

- 직접 소켓을 다루는 일은 드물지만, 라이브러리 설정의 이름이 모두 소켓 개념이다. `connect_timeout`, `read_timeout`, `tcp_nodelay`, `keepalive`, `backlog`, `so_reuseport` 를 보면 이 글의 어느 부분인지 연결할 수 있어야 한다.
- 타임아웃 없는 소켓 호출은 장애를 키운다. 상대가 응답을 멈추면 스레드가 영원히 묶이고, 풀 전체가 고갈된다. 모든 외부 호출에 연결 타임아웃과 읽기 타임아웃을 따로 건다.
- 쿠버네티스에서 컨테이너 앱이 `127.0.0.1` 에 bind 하면 같은 파드 밖에서는 접속이 안 된다. 서비스로 노출할 서버는 `0.0.0.0`(또는 `::`)에 bind 해야 한다. 홈랩에서도 자주 하는 실수다.
- `ss -ltnp` 로 어떤 프로세스가 어느 주소·포트에서 듣고 있는지 확인한다.

## 확인 문제

1. 서버가 `accept()` 를 호출할 때마다 새 소켓이 생기는 이유는?
2. 클라이언트가 `send(b"abc")`, `send(b"def")` 를 했을 때 서버의 첫 `recv(1024)` 가 돌려줄 수 있는 값을 두 가지 이상 들라.
3. 길이 접두사 프로토콜에서 `recv(n)` 을 한 번만 부르면 안 되는 이유는?
4. 서버를 재시작했더니 "Address already in use" 가 났다. 원인과 해결 옵션은?
5. 컨테이너 안 서버가 `127.0.0.1:8080` 에 bind 했을 때 Service 로 접속이 안 되는 이유는?

### 풀이

1. 듣는 소켓은 연결 요청을 받는 역할만 하고, 각 연결은 고유한 5-튜플을 가지므로 연결마다 별도 소켓(파일 디스크립터)이 필요하다.
2. `b"abc"`, `b"abcdef"`, `b"ab"` 등. TCP 는 경계를 보존하지 않는다.
3. `recv(n)` 은 최대 n 바이트를 돌려줄 뿐, n 바이트를 보장하지 않기 때문이다. 다 받을 때까지 반복해야 한다.
4. 이전 프로세스의 연결이 TIME-WAIT 로 남아 같은 주소·포트 bind 를 막는다. bind 전에 `SO_REUSEADDR` 를 켠다.
5. 루프백 주소는 파드 자신의 네트워크 네임스페이스 안에서만 닿는다. 파드 IP 로 들어온 트래픽을 받으려면 `0.0.0.0` 에 bind 해야 한다.

## 더 읽을거리 (References)

- Python `socket` 문서: <https://docs.python.org/3/library/socket.html>
- Python *Socket Programming HOWTO*: <https://docs.python.org/3/howto/sockets.html>
- Python `selectors` 문서: <https://docs.python.org/3/library/selectors.html>
- socket(7), epoll(7) 매뉴얼: <https://manpages.debian.org/bookworm/manpages/socket.7.en.html>, <https://manpages.debian.org/bookworm/manpages/epoll.7.en.html>
- W. Richard Stevens, Bill Fenner, Andrew M. Rudoff, *UNIX Network Programming, Volume 1*, 3rd ed., Addison-Wesley (서지 정보)
