---
layout: post
title: "[CS300 #130] CAP 정리와 PACELC — 분할이 오면 무엇을 포기할 것인가"
date: 2026-10-10 20:10:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, cap-theorem, pacelc, consistency, availability]
---

컴퓨터공학 300 주제 시리즈의 130번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

CAP 정리는 "네트워크 분할(P)이 일어나면, 복제된 데이터 시스템은 모든 요청에 응답하는 가용성(A)과 항상 최신 값을 주는 일관성(C) 중 하나를 포기해야 한다" 는 정리다. PACELC 는 여기에 "분할이 없을 때(Else)도 지연(L)과 일관성(C) 사이의 선택이 있다" 를 더한다.

## 왜 필요한가

데이터를 여러 기계에 복제하는 이유는 둘이다. 한 대가 죽어도 서비스하려고(가용성), 가까운 곳에서 빨리 읽으려고(지연). 그런데 복제본이 여러 개가 되면 "모든 복제본이 같은 값을 갖는가" 라는 질문이 생긴다.

앞 글에서 봤듯 네트워크는 믿을 수 없다. 복제본 사이 연결이 끊기는 순간이 반드시 온다. 그때 시스템은 결정해야 한다. 상대와 연락이 안 되는데 쓰기 요청이 왔다. 받을 것인가, 거절할 것인가. 받으면 두 복제본이 달라진다. 거절하면 사용자는 오류를 본다.

CAP 는 이 선택을 피할 방법이 없다는 것을 증명했다. 그래서 데이터베이스나 메시지 시스템을 고를 때 "분할 때 이 시스템은 어느 쪽을 택하는가" 를 먼저 물어야 한다.

## 핵심 개념

### 세 글자의 정확한 뜻

에릭 브루어(Eric Brewer)가 2000년 PODC 기조연설에서 추측으로 제시했고, 세스 길버트(Seth Gilbert)와 낸시 린치(Nancy Lynch)가 2002년에 정의를 엄밀히 하고 증명했다. 증명에서의 정의는 일상 용어보다 좁다.

| 글자 | 정리에서의 뜻 |
|---|---|
| C (Consistency) | 선형화 가능성(atomic consistency). 모든 읽기는 가장 최근 완료된 쓰기를 본다. 데이터베이스 ACID 의 C 와 다른 말이다 |
| A (Availability) | 장애가 나지 않은 모든 노드가 받은 모든 요청에 (결국) 오류 아닌 응답을 한다 |
| P (Partition tolerance) | 노드 사이 메시지가 임의로 유실되어도 시스템이 동작한다 |

### 왜 셋 다는 안 되는가

노드 A, B 두 개, 둘 사이 연결이 끊겼다고 하자.

```
 클라이언트1 ──write x=2──►  [A]   ✕ 분할 ✕   [B]  ◄──read x── 클라이언트2
```

- A 가 쓰기를 받고(A 를 지킴) B 가 읽기에 응답하면(A 를 지킴), B 는 x=2 를 모르므로 옛 값을 준다. C 가 깨진다.
- C 를 지키려면 A 가 쓰기를 거부하거나 B 가 읽기를 거부해야 한다. A 가 깨진다.

이게 증명의 핵심 직관이다. 메시지가 오가지 못하면 정보가 전달될 수 없다.

### "셋 중 둘을 고른다" 는 오해

CAP 는 흔히 "C, A, P 중 두 개를 고른다" 로 요약되지만 부정확하다. 분산 시스템에서 분할은 선택지가 아니라 자연재해다. 실제 선택은 "분할이 일어났을 때 C 와 A 중 무엇을 내주는가" 하나뿐이다. 브루어 자신도 2012년 글 "CAP Twelve Years Later" 에서 이 단순화가 오해를 낳았다고 정리했다. 분할은 드물고, 분할 중에도 연산마다 다른 선택을 할 수 있으며, 분할이 끝난 뒤 복구 절차가 중요하다는 것이다.

| 분류 | 분할 때의 행동 | 예 |
|---|---|---|
| CP | 소수 쪽은 요청을 거부한다 | etcd, ZooKeeper, 합의 기반 저장소 |
| AP | 양쪽 다 응답하고 나중에 화해한다 | Dynamo 계열, Cassandra(설정에 따라), DNS |

단, 같은 제품도 설정에 따라 다르다. Cassandra 는 읽기·쓰기 일관성 수준(`ONE`, `QUORUM`, `ALL`)으로 요청마다 성향을 바꾼다.

### PACELC: 평소의 비용까지

다니엘 아바디(Daniel Abadi)는 2012년 논문에서 CAP 가 분할 때만 이야기한다는 점을 지적했다. 실제로는 분할이 없는 평소에도 비용이 있다. 강한 일관성을 원하면 쓰기마다 다른 복제본의 확인을 기다려야 하므로 느리다.

```
if Partition:  Availability 와 Consistency 중 선택   (PA / PC)
Else:          Latency 와 Consistency 중 선택        (EL / EC)
```

| 분류 | 의미 | 예(논문의 분류) |
|---|---|---|
| PA/EL | 분할 땐 가용성, 평소엔 지연 우선 | Dynamo, Cassandra, Riak |
| PC/EC | 언제나 일관성 우선 | 완전한 ACID 분산 DB |
| PA/EC | 분할 땐 가용성, 평소엔 일관성 | MongoDB(논문 당시 기준) |

평소에 일어나는 일(지연)이 분할(드묾)보다 훨씬 자주 사용자에게 체감된다. 그래서 PACELC 는 실무 판단에 더 가깝다.

## 직접 해 보기

복제본 두 개짜리 저장소를 CP 모드와 AP 모드로 만들고, 분할 중에 쓰고 읽어 본다.

```python
class Replica:
    def __init__(self, name): self.name, self.data = name, {}

class Cluster:
    def __init__(self, mode):
        self.mode = mode                      # "CP" 또는 "AP"
        self.a, self.b = Replica("A"), Replica("B")
        self.partitioned = False

    def write(self, node, key, value):
        other = self.b if node is self.a else self.a
        if not self.partitioned:
            node.data[key] = value; other.data[key] = value   # 동기 복제
            return "ok"
        if self.mode == "CP":
            return "error: 복제 불가, 쓰기 거부"              # 일관성을 위해 가용성 포기
        node.data[key] = value                                 # 가용성을 위해 일관성 포기
        return "ok (로컬만)"

    def read(self, node, key):
        if self.partitioned and self.mode == "CP":
            return "error: 최신 보장 불가"
        return node.data.get(key)

for mode in ("CP", "AP"):
    c = Cluster(mode)
    c.write(c.a, "x", 1)
    c.partitioned = True                      # 네트워크 분할 발생
    w = c.write(c.a, "x", 2)
    r = c.read(c.b, "x")
    print(f"{mode}: 분할 중 A에 x=2 쓰기 -> {w!r:28} B에서 읽기 -> {r!r}")
```

```
CP: 분할 중 A에 x=2 쓰기 -> 'error: 복제 불가, 쓰기 거부'        B에서 읽기 -> 'error: 최신 보장 불가'
AP: 분할 중 A에 x=2 쓰기 -> 'ok (로컬만)'                   B에서 읽기 -> 1
```

CP 는 오류를 내서 틀린 값을 주지 않는다. AP 는 항상 답하지만 B 는 옛 값 1 을 준다. 어느 쪽도 "틀린" 설계가 아니다. 장바구니라면 AP 가, 계좌 잔액이라면 CP 가 맞을 수 있다. 실제 CP 시스템은 노드가 세 개 이상이고, 과반을 확보한 쪽은 계속 서비스한다. 그 이야기는 Raft 글에서 이어진다.

## 현업에서는

- **쿠버네티스의 etcd.** 쿠버네티스의 모든 상태는 etcd 에 있고, etcd 는 Raft 기반 CP 저장소다. 3노드 중 2노드가 살아 있으면 계속 쓰지만, 과반이 무너지면 쓰기를 거부한다. 그래서 컨트롤 플레인 노드는 홀수(3, 5)로 두고, 서로 다른 장애 영역에 나눠 놓는다.
- **DNS.** DNS 는 대표적인 AP 시스템이다. 권한 서버가 바뀌어도 캐시는 TTL 동안 옛 값을 준다. 대신 언제나 답한다.
- **설계 질문.** 새 저장소를 고를 때 "분할 때 소수 쪽은 쓰기를 받는가?", "평소 쓰기는 몇 개 복제본의 확인을 기다리는가?" 를 문서에서 찾아본다. 이 두 질문이 PACELC 의 PA/PC, EL/EC 에 해당한다.
- **"CA 시스템" 이라는 말.** 한 기계짜리 RDBMS 를 CA 라고 부르기도 하는데, 분할이 생길 여지가 없으니 CAP 의 대상이 아니라고 보는 것이 정확하다.

## 확인 문제

1. CAP 의 C 와 ACID 의 C 는 어떻게 다른가?
2. "CAP 중 둘을 고른다" 가 부정확한 이유는?
3. 3노드 etcd 클러스터가 1:2 로 분할되었다. 각 쪽은 쓰기를 받는가?
4. PACELC 가 CAP 에 더한 관점은 무엇이고, 왜 실무에서 중요한가?

### 풀이

1. CAP 의 C 는 선형화 가능성(최신 쓰기를 읽음)이고, ACID 의 C 는 트랜잭션이 제약 조건을 깨지 않는다는 뜻이다.
2. 분산 시스템에서 분할은 피할 수 없으므로 P 는 선택지가 아니다. 실제 선택은 분할 때 C 와 A 중 무엇을 포기하느냐다.
3. 2노드 쪽은 과반이라 계속 쓰기를 받고, 1노드 쪽은 거부한다.
4. 분할이 없는 평소에도 일관성을 높이면 지연이 늘어난다는 관점이다. 평소 지연은 분할보다 훨씬 자주 사용자에게 영향을 준다.

## 더 읽을거리 (References)

- [Seth Gilbert, Nancy Lynch, "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services", ACM SIGACT News, 2002 (PDF)](https://users.ece.cmu.edu/~adrian/731-sp04/readings/GL-cap.pdf)
- [Eric Brewer, "CAP Twelve Years Later: How the Rules Have Changed" (InfoQ 재게재, 원문 IEEE Computer 2012)](https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/)
- [Daniel Abadi, "Consistency Tradeoffs in Modern Distributed Database System Design", IEEE Computer, 2012 (저자 공개본)](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
