---
layout: post
title: "*네트워크 의 *본질* — *TCP 상태 기계*, *BBR vs CUBIC*, *QUIC*, *mTLS handshake*"
date: 2026-06-22 19:10:00 +0900
categories: [networking, fundamentals, infrastructure, security]
tags: [networking, tcp, bbr, cubic, quic, http3, tls, mtls, handshake, congestion-control, time-wait, keep-alive, fundamentals]
---

> *"왜 *이 API 요청* 이 *200 ms 걸리지?"* — *백엔드 의 *흔한 질문*. 답 의 *대부분 의 비용* 은 *애플리케이션 코드 가 아니라 *TCP 의 *3-way handshake*, *TLS 의 *4 round-trip*, *Slow Start 의 *cwnd 성장*, *Nagle 의 *지연* 같은 *네트워크 의 *물리적 본질*.
>
> *Service Mesh 의 *mTLS*, *gRPC 의 *HTTP/2 multiplexing*, *Cloudflare 의 *BBR*, *HTTP/3 의 *QUIC* — *모두 *지난 10 년 의 *네트워크 진화*. 그 진화 의 *밑* 에 *TCP 가 *여전히 도는* 것 도 사실, *그 위 에서 *새 layer 가 *재발명* 되는 것 도 사실.
>
> 이 글은 *기본기 시리즈 의 *네트워크 편* — *TCP 의 상태 기계 와 함정*, *Congestion Control (CUBIC vs BBR)*, *QUIC / HTTP/3*, *TLS / mTLS handshake*, *Service Mesh 의 implementation* — 을 *백엔드 엔지니어 가 알아야 할 깊이* 로 정리한다.

내 *기본기 시리즈* :
- [*Linux Kernel*](/2026/06/22/linux-kernel-internals-process-scheduler-namespaces-cgroups-bpf.html)
- [*분산 시스템*](/2026/06/22/distributed-systems-cap-base-saga-2pc-cdc-consistency.html)
- [*JVM 본질*](/2026/06/22/jvm-internals-jit-gc-memory-model-escape-analysis.html)
- [*DB 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)

---

## TL;DR — *한 줄 결론*

> 네트워크 의 *백엔드 본질* 은 *7 가지* : (1) **TCP 상태 기계** — 11 상태, *TIME_WAIT 의 *시한 폭탄*, (2) **3-way handshake + Slow Start** — *cold connection 의 *진짜 비용*, (3) **Congestion Control** — *CUBIC (default) → BBR (Google, 2016)* 의 *bufferbloat 우회*, (4) **HTTP/2 multiplexing + HoL blocking**, (5) **HTTP/3 over QUIC** — *UDP 기반 *0-RTT + connection migration*, (6) **TLS 1.3 handshake** — *1-RTT (또는 0-RTT)* + *modern cipher (AES-GCM, ChaCha20)*, (7) **mTLS** — *Service Mesh 의 *기본*. *Cloudflare / Google 의 *현대 적 인프라* 가 *모두 *이 7 가지 의 위에서 *돈다*. *p99 latency 의 *진짜 원인* 은 *대부분 의 경우 *네트워크 의 *어디서 *RTT 추가 됐는지* — *측정 의 능력* 이 *시야 의 *깊이*.

---

## 1. *OSI 7 계층 — *백엔드 가 *알아야 하는 것***

```
L7 Application : HTTP, gRPC, WebSocket, AMQP, MQTT
L6 Presentation: TLS, SSL                                    ← *encryption layer*
L5 Session     : (대부분 L7 안 으로 흡수)
L4 Transport   : TCP (reliable), UDP (best-effort), QUIC     ← *port, congestion control*
L3 Network     : IP, ICMP, BGP, OSPF                          ← *routing*
L2 Data Link   : Ethernet, ARP, MAC, VLAN
L1 Physical    : cables, NIC
```

→ *백엔드 엔지니어 의 *시야* 는 *대부분 *L4 ~ L7*. *L1-L2 는 *infrastructure / network 팀*. *그러나 *L4 의 trade-off* 와 *L7 의 protocol 선택* 이 *우리 시스템 의 *latency / throughput / cost 결정*.

---

## 2. *TCP — *상태 기계*

### 2.1 *11 상태 + 전이*

```
                          ┌────────┐
                          │ CLOSED │
                          └────┬───┘
              passive open │   │ active open
                           ▼   ▼
                       ┌───────┐
                       │ LISTEN │
                       └───┬────┘
                  SYN 수신 │       SYN 송신
                           ▼
                      ┌─────────┐
                      │SYN-RCVD │       ←   SYN-SENT
                      └────┬────┘
                  ACK 수신 │   완료
                           ▼
                      ┌──────────┐
                      │ESTABLISHED│   ← 데이터 통신
                      └────┬─────┘
                     FIN 송 │      │ FIN 수신
                            ▼      ▼
                   ┌────────────┐ ┌────────────┐
                   │FIN-WAIT-1  │ │CLOSE-WAIT  │
                   └─────┬──────┘ └─────┬──────┘
                  ACK수신│              │ FIN 송
                         ▼              ▼
                   ┌────────────┐ ┌────────────┐
                   │FIN-WAIT-2  │ │LAST-ACK    │
                   └─────┬──────┘ └─────┬──────┘
                   FIN수신│              │ACK수신
                          ▼              ▼
                   ┌────────────┐    ┌────────┐
                   │TIME-WAIT   │    │ CLOSED │
                   └─────┬──────┘    └────────┘
                    2*MSL│
                         ▼
                   ┌────────┐
                   │ CLOSED │
                   └────────┘
```

### 2.2 *TIME-WAIT 의 *시한폭탄***

> 능동 종료 한 쪽 (보통 *client*) 이 *TIME-WAIT 에서 *2*MSL (~60-120 초)* 머무름.

**왜** : 
- 마지막 ACK 가 *유실 되면 *재전송 필요*
- *옛 segment 가 *새 연결 에 *섞이지 않게*

**문제** : *고빈도 short-lived connection* (예: 매 초 수천 API 호출) 에서 *TIME-WAIT 가 *수만 개 누적* → *port 고갈*, *메모리 부담*.

```bash
# TIME_WAIT 개수
ss -t state time-wait | wc -l

# 해결
sysctl net.ipv4.tcp_tw_reuse=1            # 안전 한 재사용 활성화
sysctl net.ipv4.ip_local_port_range="10000 65535"
```

→ *Connection pooling + Keep-Alive* 가 *근본 해결*. 매 요청 *새 connection* 만들지 말 것.

### 2.3 *CLOSE-WAIT 의 *bug 증후***

> *CLOSE-WAIT 가 *오래 쌓이면 *애플리케이션 의 *close() 안 부르는 bug*.

```bash
ss -t state close-wait
# 100 개 이상 면 *코드 검토 필수*
```

→ try-with-resources / finally 의 *close* 누락.

### 2.4 *Half-Open Connection*

> *한 쪽 이 *crash 했는데 *다른 쪽 이 *모름*. *상대 도 *영원히 ESTABLISHED 로 보임*.

해결: *TCP keep-alive*
```bash
sysctl net.ipv4.tcp_keepalive_time=600    # 600초 idle 후 probe
sysctl net.ipv4.tcp_keepalive_intvl=60     # probe 간격
sysctl net.ipv4.tcp_keepalive_probes=3     # 3회 실패 후 close
```

또는 *애플리케이션 level keep-alive* (HTTP/1.1 Keep-Alive header, HTTP/2 PING frame).

---

## 3. *Handshake — *3-way 의 RTT 비용***

### 3.1 *3-way handshake*

```
Client                            Server
  │                                  │
  │ ───SYN (seq=x)──→                 │
  │                                  │
  │ ←─SYN-ACK (seq=y, ack=x+1)──     │
  │                                  │
  │ ───ACK (ack=y+1)──→               │
  │                                  │
  │ ←─── data ──────→                │
```

→ *데이터 보내기 전 *1.5 RTT* (50ms ping 의 경우 75ms) *고정 비용*.

### 3.2 *TCP Fast Open (TFO) — *RFC 7413*

```
First connection:
  SYN → SYN-ACK + cookie
  ACK + cookie 저장

Subsequent connection:
  SYN + cookie + data → SYN-ACK + response
  ↑ *데이터 가 *첫 RTT 안 에 *함께 *전송*
```

→ *0-RTT data*. *replay 보안* 으로 idempotent operation 만 안전.

```bash
sysctl net.ipv4.tcp_fastopen=3   # client + server
```

### 3.3 *Slow Start — *cwnd 의 *기하 증가***

> *TCP 의 *congestion window (cwnd)* — *동시에 보낼 수 있는 데이터 양*.

```
Round 1: cwnd = 10 segments (~14KB)
Round 2: cwnd = 20             ← 2 배
Round 3: cwnd = 40
...
```

→ *대용량 다운로드 시 *Slow Start 의 *처음 수 RTT* 가 *throughput 의 *상한*. *큰 file 의 *처음 1초 가 *느림*.

→ *연결 재사용 의 *장점 의 *진짜 이유* — Slow Start 통과 한 connection 의 *큰 cwnd 보존*.

---

## 4. *Congestion Control — *CUBIC vs BBR***

### 4.1 *CUBIC — *Linux 기본 (2008~)***

> *Loss-based*. *Packet drop = 혼잡 신호*. *drop 시 cwnd 절반*.

```
cwnd 시간 추이 (sawtooth):
   /\   /\   /\
  /  \ /  \ /  \
 ↑     ↑     ↑
drop, drop, drop ─→ cwnd 매번 절반
```

**문제 — *bufferbloat***:
- 현대 라우터 의 *큰 buffer* 가 *packet 안 떨어뜨림*. 대신 *latency 증가*.
- CUBIC 은 *latency 증가 인지 못함* → *cwnd 계속 증가* → *큰 buffer 가득 채움*.

### 4.2 *BBR (Bottleneck Bandwidth and RTT) — *Google 2016***

> *Latency-based*. *RTT 변화 = 혼잡 신호*. *bandwidth × RTT 를 *추정*.

```
모델:
   bottleneck bandwidth = packet 수 / 시간
   RTprop (RTT propagation) = 최소 RTT 측정

목표:
   cwnd = BDP (bandwidth × RTT)
   ↑ 정확히 *통로 꽉 차게* — *buffer 안 채움*
```

**효과** :
- *YouTube* — *4% throughput ↑, 33% latency ↓*
- *Cloudflare* — *2x throughput 그라운드*
- *대부분 의 modern 인프라 가 *BBR 채택*

```bash
sysctl net.ipv4.tcp_congestion_control=bbr
```

### 4.3 *Nagle Algorithm — *작은 packet 묶기***

> *작은 send 를 *모아서 *큰 packet 으로 *전송*. *RFC 896* (1984).

```
Client send 1 byte → Nagle 이 buffer 에 보관
Client send 1 byte → 또 buffer
... (40ms timeout)
40ms 후 함께 send
```

**문제** : *interactive workload* (SSH, gRPC) 에선 *40ms latency 추가*. *고전적 함정*.

```c
// Nagle 비활성화
int flag = 1;
setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));
```

→ *대부분 의 *gRPC / HTTP/2 / WebSocket 라이브러리* 가 *TCP_NODELAY 기본*.

### 4.4 *Delayed ACK — *Nagle 의 짝***

> *수신 측 이 *ACK 를 *최대 200ms 지연* — *다른 ACK 와 묶기 또는 응답 데이터 와 묶기*.

→ *Nagle + Delayed ACK* 조합 시 *수백 ms latency 가능*. *호환 안 좋음*.

---

## 5. *HTTP — *진화*

### 5.1 *HTTP/1.1 (1997)*

```
GET /a HTTP/1.1
Connection: keep-alive

HTTP/1.1 200 OK
... (응답 1)

GET /b HTTP/1.1
... (요청 2)

HTTP/1.1 200 OK
... (응답 2)
```

**한계** : *Head-of-Line blocking* — 한 요청 의 응답 늦으면 *뒷 요청 도 대기*. *Pipelining* 시도 했지만 *대부분 비활성*.

### 5.2 *HTTP/2 (2015) — *Multiplexing*

```
[Stream 1]: GET /a  → response stream 1
[Stream 2]: GET /b  → response stream 2
[Stream 3]: GET /c  → response stream 3

→ 한 TCP connection 위 *여러 stream 동시 진행*
```

**Frame 기반**:
- HEADERS frame — 헤더
- DATA frame — body
- HEADERS + DATA 가 *interleave*

**HPACK** — 헤더 압축 (이전 헤더 dictionary).

**한계 — *TCP HoL blocking*** :
- *한 stream 의 *packet 손실* → *모든 stream block* (TCP layer 의 ordered delivery 보장)
- Multiplexing 은 *application layer 에서* 만 — *TCP layer 는 모름*

### 5.3 *HTTP/3 (2022) over QUIC*

> *QUIC* = *UDP 위 의 *reliable + secure + multiplexed*.

**왜 *TCP 대신 *UDP***:
- *TCP HoL blocking 해결* — *각 stream 의 *독립적 packet ordering*
- *0-RTT* — 처음 부터 데이터 송신 가능
- *Connection migration* — *Wi-Fi → 4G 전환* 시 *connection 유지*
- *TLS 1.3 통합* — TCP+TLS 의 *별개 handshake* 안 함

**누가 채택**:
- Google (Chrome, YouTube)
- Cloudflare (전 세계 CDN)
- Facebook
- Apple iCloud

```bash
# Nginx 의 HTTP/3 활성화 (1.25+)
listen 443 quic reuseport;
listen 443 ssl;
http2 on;
http3 on;
add_header Alt-Svc 'h3=":443"; ma=86400';
```

---

## 6. *TLS / mTLS — *암호화 의 *handshake***

### 6.1 *TLS 1.3 (2018, RFC 8446)*

**1-RTT handshake**:
```
Client                                        Server
  │                                              │
  │ ──ClientHello (cipher list, key share)────→ │
  │                                              │
  │ ←─ServerHello (cipher 선택, key share)─    │
  │ ←─{EncryptedExtensions, Certificate, ...}── │
  │                                              │
  │ ──Finished (encrypted)────────────────────→ │
  │ ──Application Data (encrypted)─────────────→│
```

**0-RTT** (이전 connection 의 PSK 재사용):
```
ClientHello + early_data + Application Data
```

→ *0-RTT* 는 *replay attack 가능* — *idempotent operation 만 안전*. POST / 결제 같은 *side-effect* 은 *반드시 1-RTT*.

### 6.2 *TLS 1.2 → 1.3 의 *개선***

| | TLS 1.2 | TLS 1.3 |
|---|---|---|
| Handshake | 2-RTT | **1-RTT (or 0-RTT)** |
| Cipher | 옵션 많음 (CBC, RC4 등 안전 X) | *AES-GCM, ChaCha20 만* |
| Key exchange | RSA, DHE, ECDHE | *ECDHE 만 (PFS 강제)* |
| Algorithm negotiation | Hello 안 plain | *encrypted* |

→ *TLS 1.2 = legacy*. *TLS 1.3 = 2026 의 표준*. *1.0/1.1 은 PCI-DSS 위반*.

### 6.3 *mTLS — *Service Mesh 의 *기본***

> *Mutual TLS* — 클라이언트 도 *certificate 제출*. 서버 가 *그 cert 검증*.

```
Client                                Server
  │                                     │
  │ ──ClientHello──────────────────→   │
  │ ←─ServerHello + Server Cert + Cert Request──
  │ ──Client Cert + Finished────────→  │
  │ ←─Finished────────────────────────│
  │ ──Application Data───────────────→ │
```

**Service Mesh (Istio, Linkerd) 의 mTLS**:
- *각 Pod 의 sidecar (Envoy)* 가 *client/server cert 모두 보유*
- *Pod 간 통신* 이 *자동 mTLS*
- *Cert 자동 발급 / 갱신* (SPIFFE / SPIRE)

→ *Zero Trust 의 *실현* — *내부 통신 도 *암호화 + 신원 검증*.

### 6.4 *Cipher 의 *현실***

```
AEAD ciphers (Authenticated Encryption with Associated Data):
  AES-128-GCM     ← *기본 추천 (hardware AES-NI)*
  AES-256-GCM     ← 더 강
  ChaCha20-Poly1305 ← *ARM / 모바일* (AES-NI 없을 때)
```

→ *modern handshake 는 *cipher 선택 단순화*. 이전 의 *CBC + HMAC* 같은 *복잡한 조합* 없음.

---

## 7. *Connection Pooling — *latency 절감 의 *기본***

### 7.1 *Why*

```
Cold connection:
  DNS lookup        ~5ms
  TCP handshake     ~50ms (1 RTT)
  TLS handshake     ~100ms (2 RTT)
  HTTP request      ~50ms
  TOTAL             ~205ms

Warm connection (pool 재사용):
  HTTP request      ~50ms
  TOTAL             ~50ms   ← *4x faster*
```

### 7.2 *Spring WebClient 의 *기본 설정***

```java
@Bean
WebClient client() {
    ConnectionProvider provider = ConnectionProvider.builder("pool")
        .maxConnections(200)                        // *연결 풀 크기*
        .maxIdleTime(Duration.ofSeconds(60))        // 60초 idle 시 close
        .pendingAcquireTimeout(Duration.ofSeconds(5))
        .evictInBackground(Duration.ofSeconds(30))  // 주기적 정리
        .build();

    return WebClient.builder()
        .clientConnector(new ReactorClientHttpConnector(HttpClient.create(provider)))
        .build();
}
```

### 7.3 *HikariCP (DB connection pool) 의 *연관 원리***

→ 내 [*I/O 병목 글*](/2026/06/18/io-bottleneck-how-to-solve.html) 참조. *DB connection pool 의 *원리 가 *HTTP pool 과 *근본 동일*.

---

## 8. *Load Balancer — *L4 vs L7***

### 8.1 *L4 (Transport)*

- *TCP / UDP 패킷 수준* — 5-tuple 만 봄
- *예* : kube-proxy, MetalLB, AWS NLB
- *장점* : 빠름, 모든 프로토콜 지원
- *단점* : HTTP header / cookie 못 봄

### 8.2 *L7 (Application)*

- *HTTP method / path / header* 본 후 라우팅
- *예* : nginx-ingress, Traefik, AWS ALB, Cloudflare
- *장점* : 라우팅 유연, sticky session, rate limit, WAF
- *단점* : *연결 종료 (terminate) 필요* — TLS 도 종료

→ 내 [*K8s 로드밸런서 글*](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html) 참조.

---

## 9. *디버깅 / 측정 도구*

### 9.1 *tcpdump — *패킷 캡처***

```bash
# 80 포트 의 모든 패킷 capture
tcpdump -i any -nn 'tcp port 80' -w /tmp/dump.pcap

# Wireshark 로 분석
wireshark /tmp/dump.pcap
```

→ *application 의 *진짜 트래픽* 보는 *마지막 도구*. handshake / RTT / window size 등 *모든 metadata*.

### 9.2 *ss — *socket 상태***

```bash
ss -tan                    # 모든 TCP
ss -tan state established  # ESTABLISHED 만
ss -tnp                    # process 정보 포함
ss -s                       # summary
```

### 9.3 *curl -w — *각 단계 시간***

```bash
curl -w "DNS: %{time_namelookup}s, Connect: %{time_connect}s, TLS: %{time_appconnect}s, TTFB: %{time_starttransfer}s, Total: %{time_total}s\n" -o /dev/null -s https://example.com
```

→ *각 단계 의 *latency breakdown* — DNS / TCP / TLS / TTFB / Total.

### 9.4 *mtr — *traceroute + 통계*

```bash
mtr --report --report-cycles 100 google.com
# 각 hop 의 *loss / latency* 통계
```

### 9.5 *iperf3 — *bandwidth 측정***

```bash
# server
iperf3 -s

# client
iperf3 -c <server-ip>
```

→ *진짜 bandwidth* 측정. *NIC saturation* 검증.

---

## 10. *체크리스트 — *네트워크 본질 의 *실전***

내가 *high-traffic 백엔드* 운영 시 *확인* 하는 *12 가지*:

**TCP**:
1. `tcp_congestion_control=bbr` 인가
2. `tcp_tw_reuse=1`
3. `net.core.somaxconn` ≥ 65535
4. `tcp_keepalive_*` 적절 한가 (애플리케이션 idle 짧으면)

**Connection**:
5. *모든 HTTP client* 가 *Connection Pooling + Keep-Alive*
6. *DB connection pool size × 인스턴스 수* ≤ DB max_connections * 0.8
7. *Long-lived connection (WebSocket, gRPC)* 의 *idle timeout* 적절

**TLS**:
8. *TLS 1.3* 활성화 + 1.2 호환
9. *AES-GCM, ChaCha20* 만 허용
10. *cert 만료* 모니터링 (cert-manager 자동 갱신)

**HTTP/2/3**:
11. *HTTP/2* 활성화 (gRPC / 대용량 fan-out)
12. *HTTP/3 (QUIC)* 검토 (CDN edge — 모바일 사용자 latency)

---

## 11. *결론 — *RTT 의 *경제학***

> 네트워크 의 *모든 latency* 의 *밑* 에 *RTT 의 누적* 이 있다. *handshake RTT, slow start RTT, TLS RTT, application RTT* — 모두 *서울-부산 의 *1.5ms* 같은 *물리 의 *제약 위에서 *돈다*.

오늘 정리한 *7 본질* :
1. **TCP 상태 기계** — 11 상태 + TIME-WAIT 의 함정
2. **3-way handshake + Slow Start** — cold connection 의 *진짜 비용*
3. **CUBIC vs BBR** — *bufferbloat 의 *우회*
4. **HTTP/2 multiplexing** — *application HoL 해결, TCP HoL 잔존*
5. **HTTP/3 / QUIC** — *UDP 기반 *0-RTT + connection migration*
6. **TLS 1.3** — *1-RTT handshake + modern cipher*
7. **mTLS** — *Service Mesh 의 *기본*

> *백엔드 의 *p99 latency* 의 *큰 부분* 이 *애플리케이션 코드 가 아니라 *네트워크 의 *어디 의 RTT 가 *추가 됐는지* — *그 식별 의 능력* 이 *시니어 의 *깊이*.

*Connection Pool 한 줄*, *Keep-Alive header 한 줄*, *BBR 활성화 한 줄* — *모두 *물리적 RTT 절감* 의 *큰 효과*. *그 한 줄 의 *근거* 가 *오늘 의 *7 본질* 의 *어디 깨졌는지* 의 *이해 위에서 *서야* 한다.

*2026 년 의 네트워크 는 *7 년 전 의 네트워크 가 아니다*. *HTTP/3, mTLS, eBPF (Cilium), BBR, QUIC* — *모두 *production 표준*. *그 흐름 의 *변화 를 *놓치지 않는 시야* 가 *시니어 인프라 의 *기본기*.

---

## *기본기 시리즈 — *5 편 완성**

1. [*DB 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
2. [*오브젝트 서평*](/2026/06/22/object-book-review-cho-younghoo-object-oriented-design.html)
3. [*JVM 본질*](/2026/06/22/jvm-internals-jit-gc-memory-model-escape-analysis.html)
4. [*분산 시스템*](/2026/06/22/distributed-systems-cap-base-saga-2pc-cdc-consistency.html)
5. [*Linux Kernel*](/2026/06/22/linux-kernel-internals-process-scheduler-namespaces-cgroups-bpf.html)
6. **네트워크** ← 본 글

---

## *참고*

- *TCP/IP Illustrated, Vol. 1* (Stevens / Fall, 2nd ed.).
- *High Performance Browser Networking* (Ilya Grigorik) — *free online*.
- *BBR: Congestion-Based Congestion Control* (Cardwell et al., ACM Queue 2016).
- *QUIC: A UDP-Based Multiplexed and Secure Transport* (RFC 9000).
- *TLS 1.3* (RFC 8446).
- 자매편:
  - [*K8s 로드밸런서*](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html)
  - [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
