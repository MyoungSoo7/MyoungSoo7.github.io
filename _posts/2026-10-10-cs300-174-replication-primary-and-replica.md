---
layout: post
title: "[CS300 #174] 복제 — 프라이머리와 레플리카"
date: 2026-10-10 20:54:00 +0900
categories: [cs]
tags: [cs300, database, replication, high-availability, failover]
---

컴퓨터공학 300 주제 시리즈의 174번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

복제는 한 서버(프라이머리)의 변경 기록을 다른 서버(레플리카)로 보내 같은 데이터를 유지하는 것이며, 그 목적은 장애 대비와 읽기 분산이고, 핵심 선택은 "커밋 응답 전에 레플리카를 기다릴 것인가"다.

## 왜 필요한가

DB 서버가 한 대면 그 서버의 디스크 고장, 커널 패닉, 노드 재부팅이 곧 서비스 중단이다. 백업이 있어도 복원에는 시간이 걸리고, 마지막 백업 이후의 데이터는 잃는다. 또 읽기 요청이 늘어나면 한 대로는 감당이 안 된다.

복제는 두 문제를 동시에 겨냥한다. 데이터 사본을 여러 서버에 실시간에 가깝게 유지해, 하나가 죽으면 다른 하나를 승격하고(고가용성), 평소에는 읽기를 나눠 받는다(읽기 확장). 대신 "사본들이 언제 같아지는가"라는 새로운 문제가 생긴다.

## 핵심 개념

### 구조: 단일 리더

가장 흔한 구조는 쓰기를 한 곳(프라이머리, 리더, 마스터)만 받는 것이다.

```
           쓰기·읽기
 앱 ───────────────▶ [Primary] ──WAL 스트림──▶ [Replica 1]  ◀── 읽기
                         │                      
                         └─────WAL 스트림──▶ [Replica 2]  ◀── 읽기
```

쓰기 지점이 하나라 충돌이 없다. 여러 곳에서 쓰기를 받는 다중 리더나, 리더 없이 정족수로 읽고 쓰는 방식(Dynamo 계열)도 있지만, 관계형 DB 의 기본은 단일 리더다.

### 무엇을 보내는가

| 방식 | 보내는 것 | 예 | 특징 |
|---|---|---|---|
| 물리(스트리밍) 복제 | WAL 레코드 그대로(페이지 수준 변경) | PostgreSQL 스트리밍 복제 | 바이트 단위로 같은 사본, 같은 메이저 버전 필요 |
| 논리 복제 | 행 단위 변경(INSERT/UPDATE/DELETE) | PostgreSQL 논리 복제, MySQL 행 기반 binlog | 일부 테이블만, 다른 버전 간 가능 |
| 문장 기반 복제 | SQL 문장 | MySQL 문장 기반 binlog | `NOW()`, `RAND()` 같은 비결정 함수에 취약 |

물리 복제는 "WAL 과 복구" 글에서 본 장치를 그대로 쓴다. 레플리카는 끝나지 않는 복구를 하고 있는 서버다. 프라이머리의 WAL 을 받아 계속 재생한다. PostgreSQL 은 이 상태에서도 읽기 쿼리를 받을 수 있다(hot standby).

### 동기 대 비동기

복제의 가장 중요한 손잡이다.

```
비동기:  앱 → Primary 커밋(로컬 WAL fsync) → "OK" 응답
                       └──── 나중에 ────▶ Replica

동기:    앱 → Primary 커밋 ──▶ Replica 수신/기록 확인 ──▶ "OK" 응답
```

| | 비동기 | 동기 |
|---|---|---|
| 커밋 지연 | 짧음 | 레플리카 왕복만큼 늘어남 |
| 프라이머리 사망 시 | 전송 안 된 최근 커밋 손실 가능 | 커밋된 것은 레플리카에 있음 |
| 레플리카 사망 시 | 영향 없음 | 대체 레플리카가 없으면 쓰기가 멈춤 |

PostgreSQL 은 `synchronous_standby_names` 로 동기 레플리카를 지정하고, `synchronous_commit` 으로 기다리는 수준을 고른다. `remote_write`(레플리카 OS 에 넘김), `on`(레플리카 디스크에 플러시), `remote_apply`(레플리카에서 재생까지 끝남, 그래야 레플리카에서 바로 읽힘)처럼 단계가 나뉜다. 여러 레플리카 중 "아무 하나" 혹은 "N 개 중 K 개"만 기다리게 해서, 레플리카 하나가 죽어도 쓰기가 멈추지 않게 하는 것이 흔한 절충이다.

### 복제 지연이 만드는 이상

비동기 레플리카는 프라이머리보다 늦다. 평소엔 밀리초지만, 대량 배치나 네트워크 문제로 수 초~수 분이 될 수 있다. 이때 생기는 현상:

- **자기 쓰기를 못 읽음**: 닉네임을 바꾸고 새로고침했는데 옛 닉네임이 보인다. 쓰기는 프라이머리로, 읽기는 레플리카로 갔기 때문이다.
- **시간 역행**: 두 번 새로고침했는데 첫 번째는 지연이 작은 레플리카, 두 번째는 지연이 큰 레플리카로 가서 방금 본 댓글이 사라진다.

대응은 "쓰기 후 읽기 일관성"을 주는 것이다. 방금 쓴 사용자의 읽기는 일정 시간 프라이머리로 보내거나, 클라이언트가 자기 쓰기의 LSN 을 기억했다가 그 LSN 까지 재생한 레플리카에서만 읽는다.

### 장애 조치(failover)

프라이머리가 죽으면 레플리카 하나를 승격한다. 어려운 점이 세 가지 있다.

1. **정말 죽었는가?** 네트워크만 끊긴 것이라면 옛 프라이머리가 살아서 계속 쓰기를 받을 수 있다. 두 프라이머리가 동시에 쓰기를 받는 상황을 **스플릿 브레인**이라 하며, 데이터가 갈라져 합치기 어렵다. 그래서 자동 장애 조치 도구는 합의(etcd, Raft 등)로 리더를 정하고, 옛 프라이머리를 확실히 격리(fencing)한다.
2. **누구를 승격하는가?** 가장 많이 재생한(LSN 이 큰) 레플리카를 고른다.
3. **잃은 데이터**: 비동기 복제라면 승격된 레플리카에 없는 커밋은 사라진다. 이것을 RPO(복구 시점 목표)로 미리 합의해 둔다.

## 직접 해 보기

WAL 스트림, 재생 지연, 쓰기 후 읽기, 장애 조치 손실을 작은 시뮬레이션으로 확인한다.

```python
from collections import deque

class Primary:
    def __init__(self):
        self.data, self.wal, self.lsn = {}, [], 0
    def write(self, k, v):
        self.lsn += 1
        self.data[k] = v
        self.wal.append((self.lsn, k, v))
        return self.lsn

class Replica:
    def __init__(self, name):
        self.name, self.data, self.applied = name, {}, 0
        self.inbox = deque()                     # 네트워크로 오는 중인 WAL
    def receive(self, records):
        self.inbox.extend(records)
    def apply(self, n=1):                        # 재생 속도는 프라이머리와 무관
        for _ in range(min(n, len(self.inbox))):
            lsn, k, v = self.inbox.popleft()
            self.data[k] = v; self.applied = lsn

p, r = Primary(), Replica("r1")
sent = 0
def ship():
    global sent
    r.receive(p.wal[sent:]); sent = len(p.wal)

# 비동기 복제: 커밋 응답은 프라이머리만 보고 즉시
lsn = p.write("nickname", "새이름"); ship()
print("방금 쓴 값을 레플리카에서 읽기:", r.data.get("nickname"), f"(지연 {lsn - r.applied} LSN)")
r.apply()
print("재생 후:", r.data.get("nickname"))

# 쓰기 후 읽기 일관성: 클라이언트가 자기 쓰기 LSN 을 기억했다가
def read_your_writes(key, my_lsn):
    if r.applied >= my_lsn:
        return r.data.get(key), r.name
    return p.data.get(key), "primary"
my = p.write("cart", 3); ship()
print("LSN 확인 읽기:", read_your_writes("cart", my))

# 장애 조치: 프라이머리가 죽을 때 아직 전송/재생 안 된 커밋은?
p.write("order:1", "결제완료")                    # 전송되기 전에 프라이머리 사망
r.apply(10)
print("승격된 레플리카의 order:1 =", r.data.get("order:1"), "← 비동기 복제의 데이터 손실")
```

결과:

```
방금 쓴 값을 레플리카에서 읽기: None (지연 1 LSN)
재생 후: 새이름
LSN 확인 읽기: (3, 'primary')
승격된 레플리카의 order:1 = None ← 비동기 복제의 데이터 손실
```

첫 줄이 "자기 쓰기를 못 읽음"이다. 세 번째 줄은 레플리카가 아직 LSN 2 까지만 재생했으므로 LSN 2 를 요구하는 읽기를 프라이머리로 돌린 것이다. 마지막 줄은 프라이머리가 "결제완료"에 커밋 응답을 했지만 그 WAL 이 레플리카에 도착하기 전에 죽은 경우다. 사용자는 결제 완료 화면을 봤는데, 승격된 새 프라이머리에는 그 주문이 없다. 동기 복제가 막으려는 것이 바로 이 상황이다.

## 현업에서는

- **복제 지연을 지표로**: PostgreSQL 은 `pg_stat_replication` 에서 레플리카별 전송·기록·재생 LSN 과 지연 시간을 보여 준다. 이 값을 대시보드와 경보에 걸어 두는 것이 기본이다.
- **레플리카는 백업이 아니다**: `DROP TABLE` 을 실수로 실행하면 그 명령도 레플리카로 복제된다. 시점 복구용 WAL 아카이브와 백업은 별도로 필요하다.
- **쿠버네티스 위의 DB**: StatefulSet 으로 PostgreSQL 을 띄우고 오퍼레이터(Patroni 기반 등)가 리더 선출과 장애 조치를 맡는 구성이 흔하다. 리더 정보는 쿠버네티스 API 나 etcd 에 두고, 서비스 엔드포인트가 현재 프라이머리를 가리키게 한다. 홈랩의 작은 클러스터라도 노드 하나가 내려가는 일은 자주 있으니, 레플리카 하나와 자동 장애 조치만 있어도 체감 차이가 크다.
- **읽기 분산의 함정**: ORM 에서 "읽기 전용 트랜잭션은 레플리카로" 규칙을 일괄 적용했다가, 결제 직후 주문 상세 조회가 레플리카로 가서 "주문 없음"이 뜨는 일이 있다. 일관성이 필요한 읽기를 따로 표시해야 한다.

## 확인 문제

1. 물리 복제와 논리 복제의 차이를 "보내는 것" 기준으로 설명하라.
2. 동기 복제에서 유일한 동기 레플리카가 죽으면 무슨 일이 생기는가? 이를 피하는 설정 방향은?
3. "닉네임을 바꿨는데 옛 닉네임이 보인다"는 현상의 원인과 해결책 두 가지는?
4. 스플릿 브레인이란 무엇이고 왜 위험한가?
5. 레플리카가 있는데도 백업이 필요한 이유는?

### 풀이

1. 물리 복제는 WAL 레코드(페이지 수준 바이트 변경)를 그대로 보내 동일한 사본을 만든다. 논리 복제는 행 단위 변경을 보내 일부 테이블이나 다른 버전 간 복제가 가능하다.
2. 프라이머리가 동기 확인을 받지 못해 커밋이 멈춘다. 동기 후보를 여럿 두고 "그중 하나(또는 K 개)"만 기다리게 설정한다.
3. 쓰기는 프라이머리, 읽기는 지연된 레플리카로 갔기 때문이다. 쓴 직후 해당 사용자의 읽기를 프라이머리로 보내거나, 쓰기 LSN 까지 재생된 레플리카에서만 읽는다.
4. 두 노드가 동시에 자신을 프라이머리로 여기고 쓰기를 받는 상태다. 데이터가 두 갈래로 갈라져 자동으로 합칠 수 없다.
5. 실수나 버그로 인한 삭제·변경도 그대로 복제되기 때문이다. 과거 시점으로 돌아가려면 백업과 WAL 아카이브가 필요하다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/current/high-availability.html), [Log-Shipping Standby Servers](https://www.postgresql.org/docs/current/warm-standby.html)
- PostgreSQL 공식 문서, [Replication (서버 설정)](https://www.postgresql.org/docs/current/runtime-config-replication.html) — `synchronous_standby_names`, `synchronous_commit`
- PostgreSQL 공식 문서, [Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)
- Kubernetes 공식 문서, [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
