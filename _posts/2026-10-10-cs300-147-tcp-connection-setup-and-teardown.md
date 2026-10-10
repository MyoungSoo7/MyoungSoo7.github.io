---
layout: post
title: "[CS300 #147] TCP 연결 수립과 종료 — 3-way 핸드셰이크와 TIME-WAIT 의 이유"
date: 2026-10-10 20:27:00 +0900
categories: [cs]
tags: [cs300, networking, tcp, handshake, time-wait]
---

컴퓨터공학 300 주제 시리즈의 147번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

TCP 는 SYN, SYN-ACK, ACK 세 번의 교환으로 양쪽의 시작 순서 번호를 맞춘 뒤 데이터를 주고받고, FIN 을 양방향으로 한 번씩 주고받아 연결을 닫는다. 먼저 닫은 쪽은 TIME-WAIT 상태로 잠시 남는다.

## 왜 필요한가

"연결 타임아웃"과 "연결 거부(connection refused)"는 완전히 다른 증상이다. 앞의 것은 SYN 에 아무 응답이 없다는 뜻이고(방화벽 드롭, 경로 문제, 서버 과부하), 뒤의 것은 상대가 RST 로 즉시 거절했다는 뜻이다(그 포트에 듣는 프로세스가 없음). 핸드셰이크를 알면 에러 메시지 한 줄로 문제 위치를 절반으로 좁힐 수 있다.

TIME-WAIT 소켓 수천 개, CLOSE-WAIT 가 쌓이는 서버, SYN 플러드 공격도 모두 이 글의 상태 기계에서 나온다.

## 핵심 개념

### 순서 번호와 핸드셰이크

TCP 는 바이트마다 순서 번호(sequence number)를 붙인다. 연결마다 시작 번호(ISN)를 무작위에 가깝게 정한다. 예전 연결의 늦게 도착한 패킷과 섞이지 않게, 그리고 공격자가 번호를 추측하지 못하게 하기 위해서다. 현재 TCP 명세인 RFC 9293 이 이를 정리한다.

```
클라이언트                                        서버 (LISTEN)
 SYN-SENT   ---- SYN, seq=x ------------------->
            <--- SYN, ACK, seq=y, ack=x+1 ------  SYN-RECEIVED
 ESTABLISHED --- ACK, seq=x+1, ack=y+1 ------->   ESTABLISHED
```

- SYN 과 FIN 은 데이터가 없어도 순서 번호 하나를 차지한다. 그래서 ack 가 x+1 이다.
- 세 번인 이유: 양쪽 모두 "내 시작 번호를 보냈고, 상대가 그걸 받았다는 확인"이 필요하다. 두 번이면 서버는 자기 SYN 이 클라이언트에 닿았는지 모른다.
- 핸드셰이크 중 MSS, 윈도 스케일, SACK 허용 같은 옵션도 협상한다.

연결 하나를 시작하는 데 왕복 시간(RTT) 1번이 든다. TLS 를 올리면 그 위에 왕복이 더 붙는다(154번 글). 지연이 큰 구간에서 연결을 재사용하는 이유다.

### 연결 종료

TCP 는 양방향 스트림이 독립적이다. 한쪽이 "나는 더 보낼 게 없다"(FIN)를 보내도 반대쪽은 계속 보낼 수 있다. 이것을 반쪽 닫기(half-close)라 한다.

```
능동 종료 측                                     수동 종료 측
 FIN-WAIT-1  ---- FIN ---------------------->    CLOSE-WAIT  (앱에 EOF 전달)
 FIN-WAIT-2  <--- ACK -----------------------
                       (수동 측 앱이 남은 데이터 보내고 close() 호출)
             <--- FIN -----------------------    LAST-ACK
 TIME-WAIT   ---- ACK ---------------------->    CLOSED
 (2×MSL 대기)
 CLOSED
```

### 상태 이름 정리

| 상태 | 의미 |
|---|---|
| LISTEN | 서버가 연결 요청을 기다림 |
| SYN-SENT / SYN-RECEIVED | 핸드셰이크 진행 중 |
| ESTABLISHED | 데이터 송수신 가능 |
| FIN-WAIT-1 / FIN-WAIT-2 | 내가 FIN 을 보냈고 상대 FIN 을 기다림 |
| CLOSE-WAIT | 상대가 FIN 을 보냄. 내 앱이 close() 하기를 기다림 |
| LAST-ACK | 내 FIN 에 대한 마지막 ACK 를 기다림 |
| TIME-WAIT | 먼저 닫은 쪽이 잠시 대기 |

### TIME-WAIT 가 필요한 이유

먼저 닫은 쪽은 마지막 ACK 를 보낸 뒤 바로 사라지지 않고 MSL(Maximum Segment Lifetime)의 두 배 동안 기다린다. 이유는 두 가지다.

1. 마지막 ACK 가 유실되면 상대가 FIN 을 재전송한다. 그때 다시 ACK 해 줄 상태가 남아 있어야 한다.
2. 같은 (출발지 IP, 포트, 목적지 IP, 포트) 조합으로 새 연결을 바로 열면, 이전 연결의 늦게 도착한 세그먼트가 새 연결에 섞일 수 있다. 네트워크에서 그 세그먼트들이 사라질 시간을 번다.

RFC 9293 은 MSL 을 2분으로 잡는다. 실제 운영체제는 구현마다 더 짧은 값을 쓴다. 중요한 건 TIME-WAIT 가 버그가 아니라 정상 동작이라는 점이다. 짧은 연결을 대량으로 맺는 클라이언트에서 TIME-WAIT 가 많이 보이는 건 자연스럽고, 진짜 해결책은 연결 재사용(keep-alive, 커넥션 풀)이다.

### RST

RST 는 "이 연결은 없다, 즉시 끊는다"는 신호다.

- 닫힌 포트로 SYN 이 오면 RST 로 응답한다. 클라이언트에는 "Connection refused" 로 보인다.
- 앱이 읽지 않은 데이터를 남긴 채 소켓을 닫거나, SO_LINGER 를 0 으로 두고 닫으면 FIN 대신 RST 가 나간다.
- 방화벽은 RST 를 보내 거절(reject)하기도, 아무 응답 없이 버리기도(drop) 한다. 버리면 클라이언트는 SYN 재전송을 반복하다 타임아웃이 난다.

### SYN 플러드와 백로그

서버는 SYN 을 받으면 SYN-RECEIVED 상태를 잠시 기억한다. 공격자가 응답하지 않는 SYN 을 대량으로 보내면 이 대기열이 가득 차 정상 연결을 못 받는다. 리눅스는 SYN 쿠키(`tcp_syncookies`)로 대응한다. 상태를 저장하는 대신 그 정보를 서버의 ISN 안에 암호학적으로 담아 보내고, 마지막 ACK 가 오면 거기서 복원한다. 핸드셰이크가 끝난 연결은 `listen()` 의 backlog 크기만큼 accept 대기열에 쌓인다.

## 직접 해 보기

로컬호스트에서 세 가지 상황을 재현한다. 정상 연결과 반쪽 닫기, 그리고 듣는 프로세스가 없는 포트로 연결할 때의 RST 다.

```python
import socket, threading

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.bind(("127.0.0.1", 0)); srv.listen(8)
port = srv.getsockname()[1]

def server():
    conn, addr = srv.accept()              # 3-way 핸드셰이크가 끝나야 반환
    data = b""
    while chunk := conn.recv(1024):        # 빈 바이트 = 상대가 FIN 을 보냄
        data += chunk
    print("서버: 받은 데이터", data, "-> 상대 FIN 확인(EOF)")
    conn.sendall(b"reply after client FIN")  # 반쪽 닫기: 아직 보낼 수 있다
    conn.close()                           # 이제 서버도 FIN

t = threading.Thread(target=server); t.start()

c = socket.create_connection(("127.0.0.1", port))
c.sendall(b"hello")
c.shutdown(socket.SHUT_WR)                 # 클라이언트 FIN (쓰기만 닫음)
print("클라이언트: 받은 응답", c.recv(1024))
print("클라이언트: 다음 recv", c.recv(1024), "-> 서버 FIN")
c.close(); t.join(); srv.close()

# 듣는 프로세스가 없는 포트: 커널이 RST 로 거절한다
try:
    socket.create_connection(("127.0.0.1", port), timeout=2)
except ConnectionRefusedError as e:
    print("닫힌 포트:", type(e).__name__)
```

```
서버: 받은 데이터 b'hello' -> 상대 FIN 확인(EOF)
클라이언트: 받은 응답 b'reply after client FIN'
클라이언트: 다음 recv b'' -> 서버 FIN
닫힌 포트: ConnectionRefusedError
```

`shutdown(SHUT_WR)` 뒤에도 클라이언트가 응답을 받았다는 점이 반쪽 닫기다. 마지막 예외가 `ConnectionRefusedError` 인 것은 RST 를 받았기 때문이다. 같은 코드를 방화벽이 SYN 을 버리는 주소로 돌리면 `TimeoutError` 가 난다. 그 차이가 장애 위치의 차이다.

## 현업에서는

- `ss -tan` 으로 상태별 소켓을 센다. `ss -tan state time-wait | wc -l` 처럼 특정 상태만 볼 수도 있다.
- CLOSE-WAIT 가 계속 늘어나면 거의 항상 우리 앱 버그다. 상대는 이미 FIN 을 보냈는데 우리 코드가 소켓을 close() 하지 않고 있다는 뜻이다. 커넥션 풀 반환 누락, 예외 경로의 close 누락을 찾는다.
- 클라이언트 쪽 TIME-WAIT 가 너무 많아 임시 포트가 고갈되면 새 연결이 실패한다. HTTP keep-alive, 커넥션 풀로 연결 수 자체를 줄이는 것이 정공법이다.
- 쿠버네티스에서 파드가 종료될 때 Service 엔드포인트에서 빠지기 전에 프로세스가 먼저 죽으면, 클라이언트는 RST 나 연결 실패를 본다. preStop 훅으로 잠깐 기다리게 하는 이유다.

## 확인 문제

1. "Connection refused" 와 "Connection timed out" 은 각각 패킷 수준에서 무슨 일이 일어난 것인가?
2. SYN 과 FIN 이 데이터가 없는데도 순서 번호를 하나 소비하는 이유는?
3. TIME-WAIT 상태는 능동 종료 측과 수동 종료 측 중 어디에 생기는가? 그 이유 두 가지는?
4. 서버에 CLOSE-WAIT 가 수천 개 쌓였다. 무엇을 의심해야 하는가?
5. SYN 쿠키가 SYN 플러드를 막는 원리를 한 문장으로 쓰라.

### 풀이

1. refused 는 SYN 에 RST 가 돌아온 것(듣는 프로세스 없음 또는 reject), timed out 은 SYN 에 아무 응답이 없어 재전송 끝에 포기한 것(드롭, 경로 문제, 과부하)이다.
2. 상대가 그 제어 신호를 받았다는 것을 ACK 번호로 확인할 수 있게 하기 위해서다.
3. 능동 종료 측에 생긴다. 마지막 ACK 유실 시 재전송된 FIN 에 응답하기 위해, 그리고 이전 연결의 지연 세그먼트가 같은 4-튜플의 새 연결에 섞이지 않게 하기 위해서다.
4. 상대가 연결을 닫았는데 우리 앱이 소켓을 close() 하지 않는 버그다. 커넥션 반환 누락이나 예외 처리 경로를 확인한다.
5. 반쯤 열린 연결 상태를 서버 메모리에 저장하지 않고 ISN 안에 인코딩해 보내, 정상 ACK 가 돌아올 때만 상태를 만든다.

## 더 읽을거리 (References)

- RFC 9293, *Transmission Control Protocol (TCP)*: <https://www.rfc-editor.org/rfc/rfc9293.html>
- tcp(7) 매뉴얼: <https://manpages.debian.org/bookworm/manpages/tcp.7.en.html>
- Linux 커널 문서, *IP Sysctl* (tcp_syncookies, tcp_tw_reuse 등): <https://docs.kernel.org/networking/ip-sysctl.html>
- ss(8) 매뉴얼: <https://manpages.debian.org/bookworm/iproute2/ss.8.en.html>
