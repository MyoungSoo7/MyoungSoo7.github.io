---
layout: post
title: "[CS300 #134] 합의 알고리즘 — Raft, 이해하기 쉽게 설계된 합의"
date: 2026-10-10 20:14:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, raft, consensus, etcd, replicated-log]
---

컴퓨터공학 300 주제 시리즈의 134번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

Raft 는 여러 서버가 같은 명령 로그를 같은 순서로 갖게 만드는 합의 알고리즘이다. 과반의 표로 리더를 뽑고, 리더가 로그를 복제하며, 과반에 저장된 항목만 커밋한다. 그래서 2f+1 대 중 f 대가 죽어도 정확하게 동작한다.

## 왜 필요한가

앞 글에서 리더 선출은 "합의 저장소에 맡긴다" 고 했다. 그럼 그 합의 저장소는 어떻게 만드나? 여기가 바닥이다.

목표는 **복제된 상태 기계(replicated state machine)** 다. 서버 여러 대가 같은 초기 상태에서 출발해 같은 명령을 같은 순서로 적용하면 같은 상태가 된다. 그러니 "명령의 순서" 에만 합의하면 된다. 몇 대가 죽거나 네트워크가 끊겨도 이 순서가 갈라지면 안 된다.

이 문제의 고전 해법은 램포트의 Paxos 다. 하지만 Paxos 는 이해하기 어렵고 실제 시스템으로 옮기는 데 빈칸이 많기로 유명했다. 디에고 온가로(Diego Ongaro)와 존 아우스터하우트(John Ousterhout)는 2014년 논문 "In Search of an Understandable Consensus Algorithm" 에서 **이해하기 쉬움을 설계 목표로** 한 Raft 를 발표했다. 지금 etcd, Consul, CockroachDB, TiKV 등 많은 시스템이 Raft 를 쓴다. 쿠버네티스의 모든 상태도 Raft 위에 있다.

## 핵심 개념

Raft 는 문제를 세 조각으로 나눈다. 리더 선출, 로그 복제, 안전성.

### 역할과 임기(term)

```
           타임아웃                  과반 득표
 follower ─────────► candidate ─────────────► leader
    ▲                    │                       │
    └── 더 높은 term 발견 ┴───────────────────────┘
```

- 모든 서버는 follower 로 시작한다.
- 시간은 **임기(term)** 로 나뉜다. 단조 증가하는 정수다. 한 임기에 리더는 최대 하나다.
- 어떤 메시지든 자기보다 높은 term 을 보면 즉시 그 term 으로 올리고 follower 가 된다. 옛 리더는 이렇게 자동으로 물러난다.

### 리더 선출

1. follower 는 리더의 하트비트를 일정 시간 못 받으면(선거 타임아웃) term 을 1 올리고 candidate 가 된다.
2. 자기에게 투표하고 다른 서버에 `RequestVote` 를 보낸다.
3. 각 서버는 한 term 에 **한 표만** 준다. 먼저 온 요청에 준다. 단, 후보의 로그가 자기보다 뒤처졌으면 거절한다.
4. 과반을 얻으면 리더가 된다.

표가 갈리면 아무도 과반을 못 얻는다. Raft 는 선거 타임아웃을 **무작위**(논문 예시 150~300ms)로 둬서 대개 한 서버가 먼저 깨어나 이기게 한다. FLP 결과를 우회하는 현실적 장치다.

### 로그 복제

```
리더   [1:x=1][1:y=2][2:x=3]      ← (term:명령)
팔로워 [1:x=1][1:y=2][2:x=3]   ✓
팔로워 [1:x=1][1:y=2]          ✓ (따라오는 중)
팔로워 [1:x=1]                  
팔로워 (다운)
```

1. 클라이언트 요청은 리더만 받는다. 리더는 로그 끝에 항목을 붙인다.
2. `AppendEntries` 로 팔로워에 보낸다. 이때 "바로 앞 항목의 index 와 term" 을 함께 보낸다. 팔로워는 그 자리에 같은 항목이 없으면 거절하고, 리더는 한 칸씩 뒤로 가며 일치 지점을 찾아 덮어쓴다.
3. 항목이 **과반의 서버에 저장되면 커밋**된다. 리더는 커밋된 항목을 상태 기계에 적용하고 클라이언트에 응답한다.

이 일치 검사 덕분에 **로그 일치 속성**이 성립한다. 두 로그의 어떤 index 에서 term 이 같으면, 그 index 까지의 모든 항목이 같다.

### 안전성: 왜 커밋된 항목은 사라지지 않나

- 커밋된 항목은 과반에 있다.
- 새 리더는 과반의 표를 받아야 한다.
- 두 과반은 반드시 겹친다. 그리고 투표자는 자기보다 로그가 뒤처진 후보를 거절한다.
- 따라서 새 리더는 반드시 모든 커밋된 항목을 가지고 있다(리더 완전성).

한 가지 미묘한 규칙이 있다. 리더는 **이전 term 의 항목을 복제 개수만 세서 커밋하지 않는다.** 자기 term 의 항목이 과반에 복제되면 그 앞의 항목이 함께 커밋된다. 논문 Figure 8 이 이 규칙 없이 커밋된 항목이 덮어써지는 시나리오를 보여 준다.

### 장애 허용

| 클러스터 크기 | 과반 | 견딜 수 있는 장애 |
|---|---|---|
| 1 | 1 | 0 |
| 3 | 2 | 1 |
| 4 | 3 | 1 |
| 5 | 3 | 2 |
| 7 | 4 | 3 |

노드를 늘리면 장애 허용은 늘지만, 쓰기마다 더 많은 확인을 기다려야 해 느려진다. 그래서 보통 3 또는 5 를 쓴다.

### 그 밖의 부분

실제 구현에는 로그 압축(스냅샷), 멤버십 변경(한 번에 한 서버씩 추가·제거), 읽기 처리(리더가 아직 리더인지 과반에 확인하는 ReadIndex, 또는 임대 기반 읽기)가 더 필요하다. 논문과 공식 사이트가 이 부분까지 다룬다.

## 직접 해 보기

5노드 Raft 의 선출과 커밋 규칙만 간추린 시뮬레이션이다. 실제 Raft 보다 크게 단순화했다(메시지가 즉시 도착하고, 팔로워는 리더 로그를 통째로 복사한다).

```python
import random
random.seed(42)

class Node:
    def __init__(self, i):
        self.id, self.term, self.voted_for, self.role = i, 0, None, "follower"
        self.log, self.alive = [], True              # log: [(term, cmd)]
        self.reset_timer()
    def reset_timer(self):
        self.timer = random.randint(150, 300)        # 무작위 선거 타임아웃(ms)

def last(n): return (n.log[-1][0] if n.log else 0, len(n.log))

def request_vote(cand, voter):
    if not voter.alive: return False
    if cand.term > voter.term:
        voter.term, voter.voted_for, voter.role = cand.term, None, "follower"
    up_to_date = last(cand) >= last(voter)           # 로그가 나보다 뒤처진 후보는 거절
    if cand.term == voter.term and voter.voted_for in (None, cand.id) and up_to_date:
        voter.voted_for = cand.id; voter.reset_timer(); return True
    return False

def append(leader, f):
    if not f.alive or leader.term < f.term: return False
    f.term, f.role = leader.term, "follower"; f.reset_timer()
    f.log = list(leader.log); return True            # 단순화: 리더 로그를 통째로 복사

nodes = [Node(i) for i in range(5)]
def leader(): return next((n for n in nodes if n.alive and n.role == "leader"), None)

def run(ms):
    for _ in range(ms // 10):
        for n in nodes:
            if not n.alive: continue
            if n.role == "leader":
                for f in nodes:
                    if f is not n: append(n, f)       # 하트비트 겸 복제
                continue
            n.timer -= 10
            if n.timer <= 0:                          # 타임아웃 → 후보
                n.role, n.term, n.voted_for = "candidate", n.term + 1, n.id
                n.reset_timer()
                votes = 1 + sum(request_vote(n, v) for v in nodes if v is not n)
                if votes > len(nodes) // 2:
                    n.role = "leader"
                    print(f"  node{n.id} 가 term {n.term} 리더 당선 (표 {votes}/5)")

def client_write(cmd):
    L = leader()
    L.log.append((L.term, cmd))
    acks = 1 + sum(append(L, f) for f in nodes if f is not L)
    status = "커밋" if acks > len(nodes) // 2 else "미커밋(과반 미달)"
    print(f"  '{cmd}' -> node{L.id}, 복제 {acks}/5 → {status}")

print("1) 시작"); run(400); client_write("x=1")
L = leader(); L.alive = False; print(f"2) 리더 node{L.id} 장애"); run(400); client_write("x=2")
for n in nodes:
    if n.alive and n is not leader(): n.alive = False; break
print("3) 한 대 더 장애 (3/5 생존)"); run(100); client_write("x=3")
for n in nodes:
    if n.alive and n is not leader(): n.alive = False; break
print("4) 한 대 더 장애 (2/5 생존)"); run(100); client_write("x=4")
```

```
1) 시작
  node1 가 term 1 리더 당선 (표 5/5)
  'x=1' -> node1, 복제 5/5 → 커밋
2) 리더 node1 장애
  node4 가 term 2 리더 당선 (표 4/5)
  'x=2' -> node4, 복제 4/5 → 커밋
3) 한 대 더 장애 (3/5 생존)
  'x=3' -> node4, 복제 3/5 → 커밋
4) 한 대 더 장애 (2/5 생존)
  'x=4' -> node4, 복제 2/5 → 미커밋(과반 미달)
```

리더가 죽으면 선거 타임아웃 뒤 다른 노드가 term 2 로 당선된다. 5대 중 3대가 살아 있으면 계속 커밋된다. 2대만 남으면 리더가 있어도 커밋할 수 없다. 클러스터는 틀린 답을 주는 대신 멈춘다. 앞 글 CAP 의 CP 가 바로 이 동작이다. `random.seed` 를 바꿔 보면 당선되는 노드가 달라진다.

## 현업에서는

- **etcd 와 쿠버네티스.** etcd 는 Raft 로 복제된 키-값 저장소다. 기본 하트비트 간격은 100ms, 선거 타임아웃은 1000ms 이고, 공식 문서는 선거 타임아웃을 멤버 간 왕복 시간의 최소 10배로 잡으라고 권한다. 디스크 fsync 가 느리면 하트비트가 늦어져 불필요한 리더 교체가 생긴다. etcd 를 빠른 디스크에 두라는 운영 지침이 여기서 나온다.
- **리더 교체 지표.** etcd 의 리더 변경 횟수 지표가 자주 오르면 네트워크 지연, 디스크 지연, CPU 기아를 의심한다. 무선 링크나 혼잡한 노드가 섞인 소규모 클러스터에서 특히 잘 보인다.
- **쓰기 지연.** 커밋은 과반의 디스크 기록을 기다리므로, 쓰기 지연은 "가장 느린 과반" 의 디스크와 네트워크가 결정한다. 멤버를 지리적으로 멀리 흩으면 장애 허용은 좋아지지만 모든 쓰기가 느려진다.
- **멤버 교체.** 고장 난 멤버를 뺄 때는 먼저 제거하고 새 멤버를 추가한다. 3노드 중 1대가 죽은 상태에서 새 멤버를 먼저 추가하면 4노드가 되어 과반이 3이 되는데, 새 멤버가 따라잡기 전에는 살아 있는 2대만으로 과반을 못 채워 클러스터가 멈출 수 있다.

## 확인 문제

1. Raft 에서 한 term 에 리더가 둘 생기지 않는 이유는?
2. 선거 타임아웃을 무작위로 두는 이유는?
3. 항목이 "커밋" 되었다는 것은 무엇을 뜻하는가?
4. 새 리더가 커밋된 항목을 반드시 갖고 있는 이유를 설명하라.
5. 5노드 클러스터에서 2대가 죽었다. 쓰기가 가능한가? 3대가 죽으면?

### 풀이

1. 리더가 되려면 과반의 표가 필요하고, 각 서버는 한 term 에 한 표만 주며, 두 과반은 반드시 겹치기 때문이다.
2. 여러 후보가 동시에 나서 표가 갈리는 상황(split vote)이 반복되는 것을 막기 위해서다.
3. 그 항목이 과반의 서버 로그에 저장되어, 이후 어떤 리더가 되든 그 항목을 갖게 되었다는 뜻이다. 이후 상태 기계에 적용해도 안전하다.
4. 커밋 항목은 과반에 있고, 새 리더는 과반의 표를 얻어야 하며, 투표자는 자기보다 로그가 뒤처진 후보를 거절하므로, 겹치는 투표자 덕분에 새 리더 로그는 커밋 항목을 포함한다.
5. 2대 장애면 3대가 과반이라 가능하다. 3대 장애면 2대만 남아 과반이 안 되므로 쓰기가 불가능하다.

## 더 읽을거리 (References)

- [Diego Ongaro, John Ousterhout, "In Search of an Understandable Consensus Algorithm (Extended Version)" (PDF)](https://raft.github.io/raft.pdf)
- [The Raft Consensus Algorithm — 공식 사이트 (시각화·구현 목록)](https://raft.github.io/)
- [etcd Tuning — heartbeat interval, election timeout](https://etcd.io/docs/v3.5/tuning/)
- [Leslie Lamport, "Paxos Made Simple" (PDF)](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)
