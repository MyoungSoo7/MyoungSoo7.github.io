---
layout: post
title: "[CS300 #137] 분산 트랜잭션과 2PC·사가 — 여러 곳에 걸친 일을 하나처럼"
date: 2026-10-10 20:17:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, distributed-transaction, two-phase-commit, saga]
---

컴퓨터공학 300 주제 시리즈의 137번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

여러 데이터베이스나 서비스에 걸친 작업을 "전부 되거나 전부 안 되게" 하는 방법은 크게 둘이다. 2단계 커밋(2PC)은 모두에게 준비됐는지 묻고 한꺼번에 커밋해 원자성을 지키지만 코디네이터 장애에 약하다. 사가(Saga)는 각 단계를 바로 커밋하고, 실패하면 이미 한 단계를 보상 트랜잭션으로 되돌린다.

## 왜 필요한가

한 데이터베이스 안에서는 `BEGIN ... COMMIT` 으로 끝이다. 주문을 넣고 재고를 줄이는 일이 함께 성공하거나 함께 실패한다.

그런데 주문은 주문 서비스의 DB 에, 재고는 재고 서비스의 DB 에, 결제는 외부 결제사에 있다면? 주문은 들어갔는데 재고 차감이 실패하면 팔 수 없는 물건을 판 것이다. 결제는 됐는데 주문 저장이 실패하면 돈만 빠져나간 것이다. 앞 글의 샤딩도 같은 문제를 만든다. 계좌 A 는 샤드 1, 계좌 B 는 샤드 2 에 있으면 송금 하나가 두 기계에 걸친다.

각 참여자가 따로 실패할 수 있고(부분 실패), 메시지가 사라질 수 있는 환경에서 원자성을 어떻게 얻을 것인가가 이 글의 질문이다.

## 핵심 개념

### 2단계 커밋 (Two-Phase Commit)

코디네이터 하나와 참여자 여럿이 있다.

```
         1단계: 준비(prepare)              2단계: 결정
코디네이터 ── PREPARE ──► 참여자 A  ── YES ──►   ── COMMIT ──► A
          └─ PREPARE ──► 참여자 B  ── YES ──►   └─ COMMIT ──► B
                           (하나라도 NO 면 모두에게 ABORT)
```

1. **준비 단계**: 코디네이터가 모든 참여자에게 "커밋할 수 있나?" 를 묻는다. 참여자는 변경을 내구성 있게 기록하고 필요한 잠금을 잡은 뒤 YES 를 보낸다. YES 를 보낸 순간부터 참여자는 **스스로 결정할 권리를 잃는다.** 나중에 코디네이터가 커밋하라면 반드시 커밋할 수 있어야 한다.
2. **결정 단계**: 모두 YES 면 코디네이터는 COMMIT 결정을 자기 로그에 먼저 기록하고 모두에게 알린다. 하나라도 NO 거나 응답이 없으면 ABORT.

### 2PC 의 약점: 블로킹

참여자가 YES 를 보낸 뒤 코디네이터가 죽으면 어떻게 될까. 참여자는 커밋도 중단도 혼자 정할 수 없다. 다른 참여자가 NO 를 냈을 수도, 코디네이터가 이미 COMMIT 을 기록했을 수도 있기 때문이다. 코디네이터가 돌아올 때까지 잠금을 쥔 채 기다린다. 그동안 그 행을 건드리는 다른 트랜잭션도 막힌다. 이것을 **블로킹 프로토콜**이라 한다.

그 밖의 비용도 있다.

- 왕복이 최소 두 번이고, 각 단계마다 디스크 강제 기록이 필요해 느리다.
- 가장 느린 참여자가 전체 속도를 정한다.
- 참여자 모두가 2PC 를 지원해야 한다(외부 결제 API 는 대개 지원하지 않는다).

코디네이터 결정을 합의 알고리즘으로 복제하면 블로킹 문제를 줄일 수 있다. 그레이(Jim Gray)와 램포트의 "Consensus on Transaction Commit"(2006)이 Paxos 로 이 문제를 다룬다. Spanner 같은 분산 DB 는 2PC 의 참여자 각각을 합의 그룹으로 만들어 이 약점을 메운다.

### PostgreSQL 의 2PC

PostgreSQL 은 2PC 의 참여자 역할을 위한 명령을 제공한다.

```sql
BEGIN;
UPDATE stock SET qty = qty - 1 WHERE id = 7;
PREPARE TRANSACTION 'order-1234';   -- 1단계: 디스크에 기록, 세션과 분리됨
-- (코디네이터가 모든 참여자의 준비를 확인한 뒤)
COMMIT PREPARED 'order-1234';       -- 2단계 (또는 ROLLBACK PREPARED)
```

`max_prepared_transactions` 의 기본값은 0이라 쓰려면 켜야 한다. 공식 문서는 준비된 트랜잭션을 오래 방치하면 잠금을 쥐고 VACUUM 을 막는다고 경고한다. 애플리케이션이 직접 쓰기보다 트랜잭션 관리자가 쓰라고 만든 기능이다.

### 사가 (Saga)

가르시아-몰리나(Hector Garcia-Molina)와 세일럼(Kenneth Salem)이 1987년 오래 걸리는 트랜잭션(LLT)을 위해 제안했다. 큰 트랜잭션을 지역 트랜잭션 T1, T2, ..., Tn 의 순서로 나누고, 각 Ti 마다 그 효과를 되돌리는 **보상 트랜잭션** Ci 를 준비한다.

```
정상:  T1 → T2 → T3 → 완료
실패:  T1 → T2 → T3(실패) → C2 → C1
```

각 Ti 는 바로 커밋되므로 긴 잠금이 없다. 대신 **격리성(ACID 의 I)이 없다.** T1 과 C1 사이에 다른 트랜잭션이 T1 의 결과를 볼 수 있다. 결제가 승인됐다가 취소되는 모습이 사용자에게 보일 수 있다.

### 사가의 설계 포인트

- **보상은 롤백이 아니다.** 이미 보낸 이메일은 못 거둬들인다. "취소 안내 메일 발송" 같은 의미적 보상을 설계해야 한다.
- **보상과 재시도는 멱등해야 한다.** 메시지는 중복 전달될 수 있다(다음 글).
- **오케스트레이션 vs 코레오그래피.** 중앙 오케스트레이터가 단계를 지시하거나(흐름이 한눈에 보인다), 각 서비스가 이벤트를 듣고 다음 일을 하거나(결합이 느슨하지만 흐름 추적이 어렵다).
- **로컬 DB 변경과 메시지 발행의 원자성.** "DB 에 저장하고 이벤트 발행" 사이에서 죽으면 둘이 어긋난다. 같은 DB 트랜잭션에 이벤트를 아웃박스 테이블로 함께 기록하고, 별도 프로세스가 발행하는 트랜잭셔널 아웃박스 패턴을 흔히 쓴다.

### 비교

| 항목 | 2PC | 사가 |
|---|---|---|
| 원자성 | 강함 | 보상으로 결국 맞춤 |
| 격리성 | 있음(잠금) | 없음 |
| 잠금 기간 | 전체 트랜잭션 동안 | 각 지역 트랜잭션 동안만 |
| 장애 시 | 코디네이터 장애에 블로킹 | 보상 로직이 복잡 |
| 적합 | 같은 조직 내 DB, 짧은 트랜잭션 | 마이크로서비스, 외부 API, 긴 업무 흐름 |

## 직접 해 보기

2PC 의 투표·결정과 사가의 역순 보상을 간단히 재현한다.

```python
# --- 2PC ---------------------------------------------------------------
class Participant:
    def __init__(self, name, will_fail=False):
        self.name, self.will_fail, self.state = name, will_fail, "init"
    def prepare(self):                     # 1단계: 할 수 있으면 잠그고 YES
        if self.will_fail: self.state = "aborted"; return False
        self.state = "prepared"; return True
    def commit(self): self.state = "committed"
    def abort(self):  self.state = "aborted"

def two_phase_commit(parts):
    votes = [p.prepare() for p in parts]
    decision = all(votes)                  # 코디네이터 결정(실제로는 로그에 먼저 기록)
    for p in parts: (p.commit if decision else p.abort)()
    return "COMMIT" if decision else "ABORT", {p.name: p.state for p in parts}

print("2PC 정상   :", two_phase_commit([Participant("주문DB"), Participant("재고DB")]))
print("2PC 재고X  :", two_phase_commit([Participant("주문DB"), Participant("재고DB", True)]))

# --- 사가 ---------------------------------------------------------------
log = []
def step(name, fail=False):
    def do():
        if fail: raise RuntimeError(f"{name} 실패")
        log.append(f"{name}")
    return do
def comp(name): return lambda: log.append(f"보상: {name} 취소")

def run_saga(steps):
    done = []
    for action, compensate in steps:
        try:
            action(); done.append(compensate)
        except RuntimeError as e:
            log.append(f"!! {e}")
            for c in reversed(done): c()   # 완료된 단계를 역순으로 보상
            return "보상 완료"
    return "성공"

saga = [(step("주문 생성"), comp("주문")),
        (step("결제 승인"), comp("결제")),
        (step("배송 예약", fail=True), comp("배송"))]
print("사가 결과  :", run_saga(saga))
for line in log: print("   ", line)
```

```
2PC 정상   : ('COMMIT', {'주문DB': 'committed', '재고DB': 'committed'})
2PC 재고X  : ('ABORT', {'주문DB': 'aborted', '재고DB': 'aborted'})
사가 결과  : 보상 완료
    주문 생성
    결제 승인
    !! 배송 예약 실패
    보상: 결제 취소
    보상: 주문 취소
```

2PC 는 재고 DB 하나가 NO 를 내자 주문 DB 도 함께 중단한다. 아무도 커밋하지 않았으니 되돌릴 것도 없다. 사가는 주문과 결제를 이미 커밋한 뒤 배송에서 실패했으므로, 완료된 단계를 역순으로 보상한다. 그 사이 잠깐 "결제 완료" 상태가 외부에 보였을 수 있다는 점이 사가의 대가다. 실제 2PC 는 여기에 코디네이터 결정 로그와 타임아웃, 재전송이 더해진다.

## 현업에서는

- **마이크로서비스.** 서비스마다 DB 를 따로 갖는 구조에서는 2PC 보다 사가가 흔하다. Temporal 같은 워크플로 엔진은 단계와 보상, 재시도를 코드로 표현하고 실행 이력을 저장해 오케스트레이션 사가를 돕는다.
- **XA 트랜잭션.** 자바 EE 의 JTA 와 XA 는 여러 리소스(DB, 메시지 큐)를 2PC 로 묶는 표준이다. 운영 중 "in-doubt" 트랜잭션이 남아 잠금을 쥐고 있는 사고가 대표적인 운영 부담이다.
- **아웃박스 + CDC.** 주문 서비스가 주문 테이블과 아웃박스 테이블을 한 트랜잭션에 쓰고, CDC 도구가 아웃박스 변경을 Kafka 로 발행하는 구성이 널리 쓰인다. 발행은 최소 한 번이므로 소비자는 멱등해야 한다.
- **피할 수 있으면 피한다.** 가장 좋은 분산 트랜잭션은 필요 없게 만든 것이다. 함께 바뀌는 데이터를 같은 서비스·같은 샤드에 두도록 경계를 다시 그리는 것이 먼저다.

## 확인 문제

1. 2PC 에서 참여자가 YES 를 보낸 뒤에는 왜 혼자서 중단할 수 없는가?
2. 2PC 가 "블로킹 프로토콜" 이라 불리는 이유는?
3. 사가에 격리성이 없다는 것은 구체적으로 어떤 현상을 뜻하는가?
4. 이미 발송한 이메일 같은 단계는 어떻게 보상하는가?
5. "DB 저장 후 이벤트 발행" 이 원자적이지 않을 때 쓰는 패턴은?

### 풀이

1. 코디네이터가 이미 COMMIT 을 결정했을 수 있으므로, YES 를 보낸 참여자는 커밋 가능 상태를 유지하고 결정을 기다려야 한다.
2. 준비 후 코디네이터가 죽으면 참여자들이 잠금을 쥔 채 결정을 무기한 기다려야 하기 때문이다.
3. 중간 단계의 커밋 결과(예: 결제 승인)가 보상 전까지 다른 트랜잭션이나 사용자에게 보인다.
4. 되돌릴 수 없으므로 취소 안내 메일처럼 의미적으로 상쇄하는 보상 동작을 설계한다.
5. 트랜잭셔널 아웃박스 패턴. 같은 DB 트랜잭션에 이벤트를 기록하고 별도 프로세스가 발행한다.

## 더 읽을거리 (References)

- [PostgreSQL — PREPARE TRANSACTION](https://www.postgresql.org/docs/current/sql-prepare-transaction.html)
- [PostgreSQL — Two-Phase Transactions](https://www.postgresql.org/docs/current/two-phase.html)
- Hector Garcia-Molina, Kenneth Salem, "Sagas", ACM SIGMOD 1987.
- Jim Gray, Leslie Lamport, "Consensus on Transaction Commit", ACM Transactions on Database Systems 31(1), 2006.
