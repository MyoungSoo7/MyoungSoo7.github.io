---
layout: post
title: "[CS300 #132] 논리 시계와 벡터 시계 — 시계 없이 순서를 정하는 법"
date: 2026-10-10 20:12:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, lamport-clock, vector-clock, causality]
---

컴퓨터공학 300 주제 시리즈의 132번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

분산 시스템에서는 기계마다 물리 시계가 조금씩 어긋나므로 타임스탬프로 사건의 순서를 정할 수 없다. 램포트 시계는 "원인이 결과보다 작은 번호를 갖는" 카운터를 주고, 벡터 시계는 한 걸음 더 나아가 두 사건이 인과 관계인지 동시(concurrent)인지까지 판별해 준다.

## 왜 필요한가

서버 A 의 로그에 `10:00:00.120 주문 생성`, 서버 B 의 로그에 `10:00:00.100 결제 승인` 이 찍혔다. 결제가 주문보다 먼저였나? 알 수 없다. 두 서버의 시계는 NTP 로 맞춰도 수 ms 씩 어긋날 수 있고, 가상 머신이 멈췄다 깨어나면 더 크게 틀어진다. 시계가 거꾸로 가는 일도 있다.

"마지막 쓰기 승리(last-write-wins)" 를 물리 시계로 하면, 시계가 빠른 서버의 옛 쓰기가 시계가 느린 서버의 새 쓰기를 이겨 버린다. 데이터가 조용히 사라진다.

레슬리 램포트는 1978년 논문 "Time, Clocks, and the Ordering of Events in a Distributed System" 에서 관점을 바꿨다. 정확한 시각이 아니라 **인과 관계**가 중요하다. 메시지를 보낸 사건은 받은 사건보다 앞선다. 이 관계만으로 일관된 순서를 만들 수 있다.

## 핵심 개념

### happens-before (→)

램포트가 정의한 관계다.

1. 같은 프로세스 안에서 a 가 b 보다 먼저 일어났으면 a → b.
2. a 가 메시지 송신이고 b 가 그 메시지의 수신이면 a → b.
3. a → b 이고 b → c 이면 a → c (추이성).

a → b 도 아니고 b → a 도 아니면 두 사건은 **동시(concurrent, a ∥ b)** 다. "같은 시각" 이라는 뜻이 아니라 "서로 영향을 줄 수 없었다" 는 뜻이다.

```
P0:  a ──── b(송신) ─────────────────── g
              \
P1:            c(수신) ── e(송신)
                             \
P2:  d ───────────────────── f(수신)
```

여기서 a → b → c → e → f 다. d 와 c 는 서로 오간 메시지 경로가 없으므로 동시다. g 와 f 도 동시다.

### 램포트 시계

각 프로세스가 정수 카운터 L 을 갖는다.

- 사건이 일어날 때마다 L = L + 1.
- 메시지를 보낼 때 L 을 실어 보낸다.
- 받으면 L = max(L, 받은 L) + 1.

이렇게 하면 **a → b 이면 L(a) < L(b)** 가 성립한다. 하지만 역은 성립하지 않는다. L(a) < L(b) 라고 해서 a → b 라는 보장은 없다. 동시 사건에도 크기 차이가 생기기 때문이다. 동점은 프로세스 번호로 깨서 모든 사건의 전체 순서를 만들 수 있다. 램포트는 이 전체 순서로 분산 상호 배제를 구현해 보였다.

### 벡터 시계

프로세스가 N 개면 각자 길이 N 의 벡터 V 를 갖는다. V[j] 는 "내가 아는 한 프로세스 j 가 몇 번째 사건까지 했는가" 다. 1988년 무렵 피지(Colin Fidge)와 마테른(Friedemann Mattern)이 각각 제안했다.

- 프로세스 i 의 사건마다 V[i] += 1.
- 보낼 때 V 전체를 싣는다.
- 받으면 원소별로 V = max(V, 받은 V) 한 뒤 V[i] += 1.

비교 규칙은 다음과 같다.

| 조건 | 판정 |
|---|---|
| 모든 원소에서 V(a) ≤ V(b) 이고 같지 않음 | a → b |
| 모든 원소에서 V(b) ≤ V(a) 이고 같지 않음 | b → a |
| 둘 다 아님 | a ∥ b (동시) |

이번에는 **a → b ⇔ V(a) < V(b)** 가 양방향으로 성립한다. 동시성을 정확히 잡아낸다.

### 대가와 변형

| 방식 | 크기 | 알려 주는 것 |
|---|---|---|
| 램포트 시계 | 정수 1개 | 인과와 모순 없는 전체 순서 |
| 벡터 시계 | 참여자 수만큼 | 인과 관계와 동시성의 정확한 판별 |
| 하이브리드 논리 시계(HLC) | 물리 시각 + 카운터 | 물리 시각에 가까우면서 인과를 지키는 타임스탬프 |

벡터 시계는 참여자가 많아지면 커진다. 그래서 실제 시스템은 복제본 수만큼만 두거나(버전 벡터), 오래된 항목을 잘라 낸다. CockroachDB 같은 시스템은 HLC 를 쓴다.

## 직접 해 보기

위 그림의 사건을 그대로 실행하며 두 시계를 함께 계산한다.

```python
N = 3

class Proc:
    def __init__(self, i):
        self.i, self.lamport, self.vc = i, 0, [0] * N
    def local(self, label):
        self.lamport += 1; self.vc[self.i] += 1
        return self.stamp(label)
    def send(self, label):
        return self.local(label)                       # 보내기도 하나의 사건
    def recv(self, msg, label):
        _, l, vc = msg
        self.lamport = max(self.lamport, l) + 1
        self.vc = [max(a, b) for a, b in zip(self.vc, vc)]
        self.vc[self.i] += 1
        return self.stamp(label)
    def stamp(self, label):
        return (label, self.lamport, list(self.vc))

def happened_before(a, b):
    return all(x <= y for x, y in zip(a, b)) and a != b

def relation(e1, e2):
    a, b = e1[2], e2[2]
    if happened_before(a, b): return "→"
    if happened_before(b, a): return "←"
    return "∥ (동시)"

P = [Proc(i) for i in range(N)]
a = P[0].local("a: P0 로컬")
m1 = P[0].send("b: P0→P1 송신")
c = P[1].recv(m1, "c: P1 수신")
d = P[2].local("d: P2 로컬")
m2 = P[1].send("e: P1→P2 송신")
f = P[2].recv(m2, "f: P2 수신")
g = P[0].local("g: P0 로컬")

for e in (a, m1, c, d, m2, f, g):
    print(f"{e[0]:16} Lamport={e[1]}  VC={e[2]}")
print()
for x, y in ((a, f), (d, c), (g, f), (d, f)):
    print(f"{x[0][:1]} vs {y[0][:1]}: Lamport {x[1]} vs {y[1]},  벡터 시계 판정 {x[0][:1]} {relation(x, y)} {y[0][:1]}")
```

```
a: P0 로컬         Lamport=1  VC=[1, 0, 0]
b: P0→P1 송신      Lamport=2  VC=[2, 0, 0]
c: P1 수신         Lamport=3  VC=[2, 1, 0]
d: P2 로컬         Lamport=1  VC=[0, 0, 1]
e: P1→P2 송신      Lamport=4  VC=[2, 2, 0]
f: P2 수신         Lamport=5  VC=[2, 2, 2]
g: P0 로컬         Lamport=3  VC=[3, 0, 0]

a vs f: Lamport 1 vs 5,  벡터 시계 판정 a → f
d vs c: Lamport 1 vs 3,  벡터 시계 판정 d ∥ (동시) c
g vs f: Lamport 3 vs 5,  벡터 시계 판정 g ∥ (동시) f
d vs f: Lamport 1 vs 5,  벡터 시계 판정 d → f
```

`d vs c` 를 보자. 램포트 값은 1 < 3 이지만 실제로는 동시다. 램포트 시계만 보면 d 가 c 의 원인이라고 착각할 수 있다. 벡터 시계 [0,0,1] 과 [2,1,0] 은 어느 쪽도 다른 쪽보다 작지 않아서 동시로 정확히 판정된다. `g vs f` 도 마찬가지다.

## 현업에서는

- **충돌 감지.** 아마존 Dynamo 논문은 같은 키에 대한 버전들을 벡터 시계로 비교한다. 한 버전이 다른 버전의 조상이면 옛것을 버리고, 동시면 둘 다 남겨 애플리케이션(예: 장바구니 합치기)이 화해시킨다. 물리 시각으로 하나를 고르는 last-write-wins 보다 데이터를 덜 잃는다.
- **합의 알고리즘의 번호.** Raft 의 term, Paxos 의 제안 번호는 램포트 시계와 같은 발상이다. 더 큰 번호를 본 노드는 자기 번호를 올린다. 이 단조 증가 번호가 "옛 리더의 명령" 을 걸러 낸다.
- **분산 추적.** 여러 서비스에 걸친 요청 추적에서 스팬의 부모-자식 관계는 인과 관계를 명시적으로 기록한 것이다. 서버 시계가 어긋나 자식 스팬이 부모보다 먼저 시작한 것처럼 그려지는 일이 실제로 흔하다. 시각보다 관계를 믿어야 하는 이유다.
- **로그 분석.** 여러 노드 로그를 시각으로 정렬해 장애를 재구성할 때는 시계 오차를 항상 염두에 둔다. 요청 ID 같은 인과 정보를 로그에 남겨 두면 시계에 덜 의존한다.

## 확인 문제

1. 물리 시계로 사건 순서를 정하기 어려운 이유 두 가지는?
2. 램포트 시계에서 L(a) < L(b) 이면 a → b 라고 할 수 있는가?
3. 벡터 시계 [2,1,0] 과 [1,2,0] 의 관계는?
4. 프로세스 P1 의 벡터 시계가 [3,1,0] 일 때 [2,5,1] 을 담은 메시지를 받았다. 수신 후 P1 의 벡터 시계는?
5. Dynamo 가 물리 시각 대신 벡터 시계를 쓰는 이점은?

### 풀이

1. 기계마다 시계가 어긋나고(NTP 로도 수 ms 오차), 시계가 거꾸로 가거나 멈출 수 있다.
2. 없다. 역은 성립하지 않는다. 동시 사건도 크기 차이가 날 수 있다.
3. 첫 원소는 앞이 크고 둘째 원소는 뒤가 크므로 동시(∥)다.
4. 원소별 최대 [3,5,1] 에 자기 칸(인덱스 1) +1 → [3,6,1].
5. 동시 쓰기를 감지해 둘 다 보존할 수 있다. 시계가 빠른 서버의 옛 쓰기가 새 쓰기를 덮는 유실을 피한다.

## 더 읽을거리 (References)

- [Leslie Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System", Communications of the ACM, 1978 (PDF)](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)
- [DeCandia et al., "Dynamo: Amazon's Highly Available Key-value Store", SOSP 2007 (PDF)](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Friedemann Mattern, "Virtual Time and Global States of Distributed Systems", Parallel and Distributed Algorithms, 1989.
- Colin J. Fidge, "Timestamps in Message-Passing Systems That Preserve the Partial Ordering", 11th Australian Computer Science Conference, 1988.
