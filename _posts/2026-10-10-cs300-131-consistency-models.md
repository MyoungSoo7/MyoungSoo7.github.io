---
layout: post
title: "[CS300 #131] 일관성 모델 — 강한 일관성과 최종 일관성"
date: 2026-10-10 20:11:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, consistency, linearizability, eventual-consistency]
---

컴퓨터공학 300 주제 시리즈의 131번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

일관성 모델은 "복제된 데이터를 읽을 때 어떤 값이 나올 수 있는가" 에 대한 계약이다. 가장 강한 쪽은 선형화 가능성(모든 연산이 한 순간에 일어난 것처럼 보임)이고, 가장 약한 쪽은 최종 일관성(쓰기가 멈추면 언젠가 모든 복제본이 같아짐)이다. 그 사이에 사용자 경험을 지켜 주는 세션 보장들이 있다.

## 왜 필요한가

사용자가 프로필 사진을 바꾸고 새로고침했더니 옛 사진이 나온다. 다시 새로고침하면 새 사진, 또 하면 옛 사진. 버그 신고가 들어온다. 그런데 데이터베이스는 "고장" 난 게 아니다. 읽기를 비동기 복제본에서 했을 뿐이다.

복제본이 여러 개면 쓰기가 모든 복제본에 도달하는 데 시간이 걸린다. 그 사이 읽기가 어디로 가느냐에 따라 다른 값이 보인다. 이것을 허용할지, 어디까지 허용할지를 정하는 것이 일관성 모델이다. 강할수록 프로그래밍은 쉽지만 느리고 가용성이 떨어진다(앞 글의 CAP·PACELC). 약할수록 빠르지만 애플리케이션이 이상한 상태를 견뎌야 한다.

## 핵심 개념

### 스펙트럼

```
강함 ◄────────────────────────────────────────────────► 약함
선형화 가능성 ─ 순차 일관성 ─ 인과 일관성 ─ 세션 보장들 ─ 최종 일관성
(느림, 분할 때 가용성 낮음)                    (빠름, 분할에도 응답)
```

### 선형화 가능성 (Linearizability)

허리히(Herlihy)와 윙(Wing)이 1990년 정의했다. 각 연산은 호출과 응답 사이의 어느 한 순간에 원자적으로 일어난 것처럼 보이고, 그 순서는 실제 시간 순서를 존중한다. 쉽게 말해 "복제본이 하나뿐인 것처럼" 동작한다.

```
클라이언트 A: |--- write x=1 ---|
클라이언트 B:                       |-- read x --|   → 반드시 1
클라이언트 C:        |-- read x --|                  → 0 또는 1 (겹치므로)
```

쓰기가 끝난 뒤 시작한 읽기는 반드시 그 값을 본다. 분산 락, 리더 선출, 유일성 제약(아이디 중복 방지)처럼 "단 하나" 가 중요한 곳에 필요하다. etcd, ZooKeeper(쓰기), Spanner 등이 제공한다. 대가는 합의나 동기 복제에 드는 지연이다.

### 순차 일관성

모든 연산이 어떤 하나의 전체 순서로 보이고, 각 클라이언트의 연산은 자기 순서를 지킨다. 선형화 가능성과의 차이는 실제 시간을 존중하지 않아도 된다는 것이다. 쓰기가 끝났는데도 다른 클라이언트가 잠시 옛 값을 볼 수 있다. 메모리 모델 글의 순차 일관성과 같은 개념이다.

### 인과 일관성

원인과 결과의 순서만 지킨다. "질문" 글을 본 뒤 단 "답변" 은, 누구에게나 질문보다 나중에 보여야 한다. 서로 관련 없는 쓰기는 복제본마다 다른 순서로 보여도 된다. 인과 관계는 다음 글의 벡터 시계로 추적한다. 분할 중에도 가용성을 유지하면서 얻을 수 있는 강한 축에 속하는 모델로 알려져 있다.

### 최종 일관성 (Eventual Consistency)

새 쓰기가 멈추면 결국 모든 복제본이 같은 값으로 수렴한다. 그 "결국" 이 언제인지, 그 전에 무엇이 보이는지는 약속하지 않는다. 아마존의 베르너 보겔스(Werner Vogels)가 2008년 글 "Eventually Consistent" 에서 대규모 서비스 관점으로 정리했다. 동시에 들어온 충돌 쓰기를 어떻게 합칠지(마지막 쓰기 승리, 벡터 시계 비교, CRDT)도 따로 정해야 한다.

### 세션 보장: 사용자가 느끼는 일관성

더글러스 테리(Douglas Terry) 등이 1994년 제시한 네 가지 보장은 최종 일관성 위에서 한 사용자의 경험을 지켜 준다.

| 보장 | 의미 | 깨지면 |
|---|---|---|
| 내 쓰기 읽기 (Read Your Writes) | 내가 쓴 것은 나에게 보인다 | 글을 썼는데 목록에 없다 |
| 단조 읽기 (Monotonic Reads) | 한 번 본 것보다 과거로 돌아가지 않는다 | 새로고침하면 댓글이 사라졌다 나타났다 |
| 단조 쓰기 (Monotonic Writes) | 내 쓰기들은 순서대로 적용된다 | 비밀번호 변경 두 번의 순서가 뒤집힌다 |
| 읽은 뒤 쓰기 (Writes Follow Reads) | 내가 본 것 이후에 내 쓰기가 적용된다 | 답글이 원글보다 먼저 보인다 |

구현 방법은 단순한 편이다. 세션을 한 복제본에 고정(sticky)하거나, 클라이언트가 "내가 마지막으로 본 버전" 을 들고 다니며 그보다 오래된 복제본은 피한다.

## 직접 해 보기

리더 하나와 비동기 팔로워 둘을 흉내 내고, 매 단계 쓰기 직후 읽기를 어디서 하느냐에 따라 세션 보장 위반을 센다.

```python
import random
random.seed(3)

class Store:
    """리더 1 + 팔로워 2. 쓰기는 리더에만, 팔로워에는 비동기로 늦게 전달."""
    def __init__(self):
        self.leader = {}; self.followers = [{}, {}]; self.log = []; self.applied = [0, 0]
    def write(self, k, v):
        self.leader[k] = v; self.log.append((k, v))
    def tick(self):                                  # 복제 지연: 팔로워마다 30% 확률로 따라잡음
        for i in range(2):
            if random.random() < 0.3:
                for k, v in self.log[self.applied[i]:]:
                    self.followers[i][k] = v
                self.applied[i] = len(self.log)
    def read(self, replica, k):
        return (self.leader if replica == "L" else self.followers[replica]).get(k)

def run(policy):
    s = Store(); ryw = mono = 0; last_seen = 0
    for step in range(1, 2001):
        s.write("x", step)                           # 사용자가 x 를 step 으로 갱신
        s.tick()
        replica = policy(s)
        v = s.read(replica, "x") or 0
        if v != step: ryw += 1                       # 방금 쓴 값을 못 읽음
        if v < last_seen: mono += 1                  # 전에 본 것보다 옛 값을 읽음
        last_seen = max(last_seen, v)
    return ryw, mono

print("아무 팔로워 읽기   RYW 위반 %4d  단조 읽기 위반 %4d" % run(lambda s: random.choice([0, 1])))
print("팔로워 0 고정      RYW 위반 %4d  단조 읽기 위반 %4d" % run(lambda s: 0))
print("리더에서 읽기      RYW 위반 %4d  단조 읽기 위반 %4d" % run(lambda s: "L"))
```

```
아무 팔로워 읽기   RYW 위반 1394  단조 읽기 위반  463
팔로워 0 고정      RYW 위반 1393  단조 읽기 위반    0
리더에서 읽기      RYW 위반    0  단조 읽기 위반    0
```

팔로워를 무작위로 고르면 두 보장이 모두 깨진다. 팔로워 하나에 고정(sticky)하면 여전히 방금 쓴 값은 못 보지만, 과거로 돌아가는 일은 사라진다. 한 복제본은 시간이 앞으로만 가기 때문이다. 리더에서 읽으면 둘 다 지켜진다. 대신 리더에 읽기 부하가 몰린다. 실무에서는 "쓰기 직후 몇 초간만 리더에서 읽기" 같은 절충을 쓴다.

## 현업에서는

- **읽기 복제본.** PostgreSQL·MySQL 의 읽기 전용 복제본으로 읽기를 분산하면 위 실험의 첫 줄이 그대로 재현된다. 프레임워크의 "쓰기 후 일정 시간 같은 요청 흐름은 primary 사용" 옵션이나, 복제 위치(LSN)를 비교해 충분히 따라온 복제본만 쓰는 방식으로 막는다.
- **쿠버네티스 API.** 클라이언트의 list/watch 는 API 서버 캐시에서 응답될 수 있다. `resourceVersion` 파라미터로 "이 버전 이후의 데이터" 를 요구하는 것이 일종의 단조 읽기 보장이다. 컨트롤러는 최종 일관성을 전제로 "원하는 상태와 현재 상태의 차이를 계속 줄이는" 방식으로 설계된다.
- **캐시.** CDN 이나 Redis 캐시 앞에 둔 데이터는 TTL 동안 옛 값을 줄 수 있다. 캐시 무효화를 언제 하느냐가 곧 일관성 모델의 선택이다.
- **테스트.** Jepsen 프로젝트는 실제 분산 데이터베이스가 문서에 적힌 일관성 수준을 지키는지 장애 주입으로 검증하고, 여러 제품에서 위반을 보고해 왔다. 문서의 일관성 주장도 검증 대상이다.

## 확인 문제

1. 선형화 가능성과 순차 일관성의 결정적 차이는?
2. 최종 일관성이 보장하는 것과 보장하지 않는 것은?
3. "새로고침할 때마다 댓글이 보였다 안 보였다 한다" 는 어떤 세션 보장의 위반인가?
4. 위 실험에서 팔로워 하나에 고정하면 왜 단조 읽기가 지켜지는가?
5. 아이디 중복 가입 방지에 최종 일관성 저장소만 쓰면 어떤 문제가 생기는가?

### 풀이

1. 선형화 가능성은 실제 시간 순서를 존중한다. 완료된 쓰기 이후 시작한 읽기는 반드시 그 값을 본다. 순차 일관성은 그렇지 않아도 된다.
2. 쓰기가 멈추면 결국 모든 복제본이 수렴한다는 것만 보장한다. 언제 수렴하는지, 그 전에 어떤 값을 읽는지는 보장하지 않는다.
3. 단조 읽기(Monotonic Reads) 위반이다.
4. 한 복제본에 적용되는 로그는 앞으로만 진행하므로, 같은 복제본에서 읽은 값은 과거로 돌아가지 않는다.
5. 분할이나 복제 지연 중에 두 복제본이 같은 아이디를 각각 받아들일 수 있다. 유일성은 선형화 가능한 연산(합의, 단일 리더의 제약 조건)이 필요하다.

## 더 읽을거리 (References)

- [Maurice Herlihy, Jeannette Wing, "Linearizability: A Correctness Condition for Concurrent Objects", ACM TOPLAS, 1990 (저자 공개본)](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf)
- [Werner Vogels, "Eventually Consistent" (2008)](https://www.allthingsdistributed.com/2008/12/eventually_consistent.html)
- [Jepsen, Consistency Models](https://jepsen.io/consistency)
- Douglas B. Terry et al., "Session Guarantees for Weakly Consistent Replicated Data", PDIS 1994.
