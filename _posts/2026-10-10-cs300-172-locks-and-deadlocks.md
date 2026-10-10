---
layout: post
title: "[CS300 #172] 락과 교착 상태 — 서로의 손을 잡고 멈춘 트랜잭션"
date: 2026-10-10 20:52:00 +0900
categories: [cs]
tags: [cs300, database, locking, deadlock, two-phase-locking]
---

컴퓨터공학 300 주제 시리즈의 172번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

락은 트랜잭션이 데이터에 대한 접근 권한을 독점하거나 공유하게 하는 장치이고, 교착 상태는 둘 이상의 트랜잭션이 서로가 쥔 락을 기다리며 영원히 멈춘 상태다. DB 는 이를 탐지해 한쪽을 강제로 롤백한다.

## 왜 필요한가

MVCC 덕분에 읽기와 쓰기는 서로 막지 않는다. 하지만 같은 행을 두 트랜잭션이 동시에 고치는 것은 여전히 막아야 한다. 또 "잔액을 확인하고 출금"처럼 읽은 값을 근거로 쓰는 로직은 그 행을 미리 잠가야 안전하다. 이 모든 것이 락이다.

락을 쓰면 교착 상태가 따라온다. 운영 중인 서비스 로그에 `deadlock detected` 가 찍히는 것은 드문 일이 아니다. 원인을 이해하면 대부분은 코드 순서를 바꾸는 것만으로 사라진다.

## 핵심 개념

### 공유 락과 배타 락

가장 기본적인 두 종류다.

| | 공유(S) 보유 중 | 배타(X) 보유 중 |
|---|---|---|
| 공유(S) 요청 | 허용 | 대기 |
| 배타(X) 요청 | 대기 | 대기 |

읽기는 여럿이 동시에 해도 되니 S 끼리는 공존한다. 쓰기는 혼자 해야 하니 X 는 어떤 락과도 공존하지 않는다. 이 표를 **호환성 행렬**이라 한다. 실제 DB 는 더 많은 모드를 둔다. PostgreSQL 은 테이블 수준 락 모드를 8가지 정의하고, 문서에 충돌 표를 싣고 있다.

### 락의 단위

- **행 락**: 동시성이 가장 높다. `UPDATE`, `DELETE`, `SELECT ... FOR UPDATE` 가 잡는다.
- **테이블 락**: `ALTER TABLE`, `LOCK TABLE` 등이 잡는다. 일반 DML 도 약한 테이블 락을 잡아 "스키마 변경과의 충돌"을 막는다.
- **범위·간격 락**: 존재하지 않는 행의 "자리"를 잠근다. MySQL InnoDB 의 넥스트키 락이 대표적이며, 팬텀을 막는 데 쓰인다.
- **권고 락(advisory lock)**: 데이터와 무관하게 애플리케이션이 이름 붙여 잡는 락. 배치 작업의 중복 실행 방지 등에 쓴다.

### 2단계 락킹(2PL)

락만 잡는다고 직렬 가능성이 생기지는 않는다. 읽고 바로 풀고, 다시 잡으면 그 틈에 다른 트랜잭션이 끼어든다. **2단계 락킹**은 규칙 하나로 이를 해결한다.

```
락 개수
  ▲        확장 단계        │  축소 단계
  │      ┌──┐              │
  │   ┌──┘  └──┐           │      ← 한 번이라도 락을 풀면
  │ ┌─┘        └───────────┼──┐     그 뒤로는 새 락을 잡지 않는다
  └─┴──────────────────────┴──┴──▶ 시간
```

트랜잭션은 락을 얻기만 하는 단계와 풀기만 하는 단계로 나뉘어야 한다. 이를 지키면 결과가 직렬 가능함이 증명되어 있다. 실무 DB 는 대개 **엄격한 2PL** 을 쓴다. 쓰기 락을 커밋·롤백 시점까지 쥐고 있다가 한꺼번에 푼다. 그래야 다른 트랜잭션이 커밋되지 않은 값을 읽는 일(그리고 연쇄 롤백)이 없다.

### 교착 상태

```
T1: LOCK A ──────────────── LOCK B (대기…)
T2:        LOCK B ─────────────────────── LOCK A (대기…)

대기 그래프:  T1 ──기다림──▶ T2
              ▲               │
              └───기다림──────┘     사이클 = 교착
```

교착이 생기는 네 조건(Coffman 조건)은 상호 배제, 점유 대기, 비선점, 순환 대기다. 하나라도 깨면 교착은 생기지 않는다. DB 는 앞의 세 가지를 본질적으로 갖고 있으므로, 실질적인 대응은 순환 대기를 다루는 것이다.

### DB 의 대응: 탐지와 희생자 선택

대부분의 DB 는 **탐지** 방식을 쓴다. 대기 그래프에서 사이클을 찾으면 그중 하나를 희생자로 골라 롤백한다. 나머지는 진행된다.

PostgreSQL 은 락을 일정 시간 기다린 뒤에야 교착 검사를 한다. 검사 자체가 비싸서다. 이 시간이 `deadlock_timeout` 이고 기본값은 1초다. 교착이 확인되면 한 트랜잭션이 `deadlock detected` 오류(SQLSTATE `40P01`)로 실패한다.

교착과는 별개로, 락을 너무 오래 기다리지 않게 하는 상한도 있다. PostgreSQL 의 `lock_timeout` 은 락 대기 상한을, `statement_timeout` 은 문장 전체 실행 상한을 정한다.

### 애플리케이션의 예방책

1. **잠그는 순서를 통일한다.** 이체라면 계좌 ID 가 작은 쪽부터 잠근다. 모든 트랜잭션이 같은 순서를 따르면 사이클이 생길 수 없다.
2. **트랜잭션을 짧게 한다.** 락을 쥔 시간이 짧을수록 겹칠 확률이 낮다.
3. **필요한 락을 처음에 한 번에 잡는다.** `SELECT ... WHERE id IN (...) ORDER BY id FOR UPDATE`.
4. **기다리지 않는 선택지**: `FOR UPDATE NOWAIT`(즉시 실패), `FOR UPDATE SKIP LOCKED`(잠긴 행은 건너뜀). 작업 큐를 테이블로 구현할 때 `SKIP LOCKED` 가 특히 유용하다.
5. **재시도**: 교착은 완전히 없앨 수 없다고 보고, 희생자가 된 트랜잭션을 전체 재시도한다.

## 직접 해 보기

파이썬 스레드 락으로 두 트랜잭션의 교착을 재현하고, 순서 통일로 해결한다. DB 의 `lock_timeout` 처럼 1초 타임아웃을 두었다. 마지막에는 대기 그래프에서 사이클을 찾는 탐지기를 붙였다.

```python
import threading, time

row_lock = {"A": threading.Lock(), "B": threading.Lock()}

def transfer(name, first, second, results, ordered=False):
    if ordered:                      # 해결책: 항상 같은 순서로 잠근다
        first, second = sorted([first, second])
    with row_lock[first]:
        time.sleep(0.1)              # 두 트랜잭션이 첫 락을 잡을 시간을 준다
        got = row_lock[second].acquire(timeout=1.0)   # DB 의 lock_timeout 흉내
        if not got:
            results[name] = f"{second} 를 기다리다 타임아웃 → 롤백"
            return
        try:
            results[name] = "커밋"
        finally:
            row_lock[second].release()

for ordered in (False, True):
    results = {}
    t1 = threading.Thread(target=transfer, args=("T1", "A", "B", results, ordered))
    t2 = threading.Thread(target=transfer, args=("T2", "B", "A", results, ordered))
    t1.start(); t2.start(); t1.join(); t2.join()
    print("순서 통일" if ordered else "순서 제각각", dict(sorted(results.items())))

# 대기 그래프(wait-for graph)에서 사이클 찾기
def find_cycle(waits_for):
    def dfs(node, path):
        if node in path:
            return path[path.index(node):] + [node]
        for nxt in waits_for.get(node, []):
            cyc = dfs(nxt, path + [node])
            if cyc:
                return cyc
    for start in waits_for:
        cyc = dfs(start, [])
        if cyc:
            return cyc

print("교착:", find_cycle({"T1": ["T2"], "T2": ["T3"], "T3": ["T1"], "T4": ["T1"]}))
print("교착:", find_cycle({"T1": ["T2"], "T2": ["T3"]}))
```

한 번 실행한 결과:

```
순서 제각각 {'T1': 'B 를 기다리다 타임아웃 → 롤백', 'T2': '커밋'}
순서 통일 {'T1': '커밋', 'T2': '커밋'}
교착: ['T1', 'T2', 'T3', 'T1']
교착: None
```

순서가 제각각이면 T1 은 A 를, T2 는 B 를 쥔 채 상대를 기다린다. 한쪽이 타임아웃으로 물러나 자기 락을 풀자 다른 쪽이 진행했다. 어느 쪽이 희생될지는 실행마다 달라질 수 있다. 순서를 통일하면 둘 다 A 부터 잡으므로 한쪽은 처음부터 기다리기만 하고, 사이클이 생기지 않아 둘 다 커밋된다. 대기 그래프 예에서 T4 는 T1 을 기다리지만 사이클 밖에 있다. 사이클 안의 하나만 롤백하면 T4 도 결국 풀린다.

## 현업에서는

- **교착 로그를 읽는 습관**: PostgreSQL 은 교착이 나면 서버 로그에 관련 프로세스와 그들이 기다리던 락, 실행 중이던 문장을 남긴다. 두 문장의 잠금 순서를 비교하면 원인이 거의 바로 보인다.
- **외래 키도 락을 잡는다**: 자식 행을 삽입하면 부모 행에 공유 계열 락이 걸린다. 부모 행을 갱신하는 트랜잭션과 자식을 삽입하는 트랜잭션이 엇갈려 교착이 나는 경우가 있다. "나는 이 행을 건드리지도 않았다"는 착각의 원인이다.
- **배치와 온라인 트래픽의 충돌**: 수만 행을 한 트랜잭션으로 갱신하는 배치는 오래 락을 쥔다. 1,000행 단위로 쪼개 커밋하면 온라인 요청이 기다리는 시간이 짧아진다.
- **마이그레이션의 테이블 락**: `ALTER TABLE` 은 강한 테이블 락을 원한다. 긴 쿼리 하나가 테이블을 읽는 중이면 `ALTER` 가 대기하고, 그 뒤에 들어온 모든 일반 쿼리가 `ALTER` 뒤에 줄을 서서 서비스가 멈춘다. 마이그레이션 전에 `lock_timeout` 을 짧게 거는 이유다.

## 확인 문제

1. 공유 락끼리는 호환되고 배타 락은 어떤 락과도 호환되지 않는 이유는?
2. 엄격한 2PL 이 일반 2PL 보다 실무에서 선호되는 이유는?
3. 교착 상태의 네 조건 중 애플리케이션이 가장 쉽게 깰 수 있는 것은 무엇이고, 어떻게 깨는가?
4. PostgreSQL 이 락 대기를 시작하자마자 교착 검사를 하지 않는 이유는?
5. 작업 큐 테이블에서 여러 워커가 같은 작업을 집어 가지 않게 하려면 어떤 구문을 쓰는가?

### 풀이

1. 읽기끼리는 서로의 결과를 바꾸지 않지만, 쓰기는 다른 읽기·쓰기의 결과를 바꾸기 때문이다.
2. 쓰기 락을 커밋까지 유지해 커밋되지 않은 값이 다른 트랜잭션에 노출되지 않고, 연쇄 롤백이 생기지 않는다.
3. 순환 대기. 모든 트랜잭션이 자원을 같은 전역 순서(예: ID 오름차순)로 잠그게 한다.
4. 교착 검사는 비용이 크고 대부분의 락 대기는 곧 풀리므로, `deadlock_timeout`(기본 1초) 동안 기다린 뒤에만 검사한다.
5. `SELECT ... FOR UPDATE SKIP LOCKED` 로 이미 다른 워커가 잠근 행을 건너뛴다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html) — 락 모드, 충돌 표, 교착 상태
- PostgreSQL 공식 문서, [Lock Management](https://www.postgresql.org/docs/current/runtime-config-locks.html) — `deadlock_timeout`
- PostgreSQL 공식 문서, [SELECT](https://www.postgresql.org/docs/current/sql-select.html) — 잠금 절 `FOR UPDATE`, `NOWAIT`, `SKIP LOCKED`
- K. P. Eswaran, J. N. Gray, R. A. Lorie, I. L. Traiger, "The Notions of Consistency and Predicate Locks in a Database System", *Communications of the ACM*, 19(11), 1976.
