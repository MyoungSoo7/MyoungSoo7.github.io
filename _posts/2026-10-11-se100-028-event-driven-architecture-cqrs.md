---
layout: post
title: "[SE100 #028] 이벤트 기반 아키텍처와 CQRS·이벤트 소싱"
date: 2026-10-11 16:58:12 +0900
categories: [software-engineering]
tags: [se100, software-architecture, event-driven-architecture, cqrs, event-sourcing, transactional-outbox]
---

소프트웨어 공학 100 주제 시리즈의 28번째 글이다. (카테고리: 설계와 아키텍처)

## 한 줄 요약

"이벤트 기반" 이라는 말 아래에는 서로 다른 네 패턴 — **이벤트 알림, 이벤트 전달 상태 이전, 이벤트 소싱, CQRS** — 이 섞여 있다. 각각 푸는 문제와 치르는 비용이 다르므로, 무엇을 도입하는지 이름으로 구분하고 시작해야 한다.

## 왜 필요한가

Martin Fowler 는 2017년 글 [What do you mean by "Event-Driven"?](https://martinfowler.com/articles/201701-event-driven.html)에서, 사람들이 "이벤트 기반" 이라고 말할 때 실제로는 꽤 다른 것들을 가리킨다는 관찰에서 출발한다. 그가 소개한 사례에서 한 프로젝트 관리자는 이벤트 소싱이 재앙이었다고 했다. 변경 하나에 읽기 모델과 쓰기 모델을 모두 고쳐야 해서 일이 두 배였다는 것이다. Fowler 는 바로 그 문장에서 이벤트 소싱과 **CQRS** 의 혼동 가능성을 읽어 낸다. 읽기·쓰기 모델을 따로 고치는 부담은 CQRS 의 특징이기 때문이다. 그 프로젝트의 기술 리드는 비동기 통신 과다를 주범으로 꼽았는데, Fowler 는 비동기가 복잡도를 키우는 건 맞지만 어느 패턴의 필수 요소도 아니라고 짚는다. 패턴을 뭉뚱그리면 무엇이 원인인지조차 가릴 수 없다.

또 하나의 실무 문제는 **이중 쓰기(dual write)** 다. "DB 에 저장하고 이벤트를 발행한다" 는 두 작업은 원자적이지 않다. 저장 직후 프로세스가 죽으면 이벤트가 사라지고, 발행 후 커밋이 실패하면 존재하지 않는 주문의 이벤트가 나간다. 이벤트 기반으로 가는 순간 이 문제를 반드시 설계해야 한다.

## 핵심 개념

### 1. 이벤트 알림 (Event Notification)

시스템이 자기 도메인의 변화를 다른 시스템에 알리는 메시지를 보낸다. Fowler 의 설명에서 핵심은 **보내는 쪽이 응답에 크게 관심이 없다**는 것이다. 이벤트는 ID 와 조회 링크 정도만 담고, 수신자는 필요하면 원 시스템에 다시 물어본다.

| 장점 | 함정 |
|---|---|
| 결합이 낮고 구성이 단순 | 여러 알림을 가로지르는 논리 흐름이 **코드 어디에도 명시되지 않는다.** 운영 중 시스템을 관찰해야만 흐름이 보이고, 디버깅과 수정이 어렵다 |

Fowler 가 경고하는 함정이 하나 더 있다. **수동공격적 명령(passive-aggressive command)**. 보내는 쪽이 수신자가 특정 동작을 하길 기대하면서 명령 대신 이벤트 모양으로 보내는 경우다. 기대가 있다면 명령 메시지로 의도를 드러내야 한다.

```
이벤트(사실, 과거형):  OrderPlaced { orderId }        — 누가 듣든 상관없다
명령(의도, 명령형):    ReserveStock { orderId, sku }   — 특정 수신자의 처리를 기대
```

### 2. 이벤트 전달 상태 이전 (Event-Carried State Transfer)

이벤트에 변경된 데이터를 담아 보내, 수신자가 자기 사본을 갱신하고 **원 시스템에 다시 묻지 않게** 한다. Fowler 는 고객 주소 변경 이벤트를 예로 든다.

| 얻는 것 | 치르는 것 |
|---|---|
| 원 시스템이 죽어도 수신자는 동작(회복력) | 데이터가 많이 오가고 사본이 많아짐 |
| 원격 호출이 없어 지연 감소 | 수신자가 상태를 유지하는 복잡도 |
| 원 시스템의 조회 부하 감소 | 사본은 **결국 일관(eventually consistent)** |

### 3. 이벤트 소싱 (Event Sourcing)

Fowler 의 [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) 정의: **애플리케이션 상태의 모든 변경을 이벤트의 순서열로 저장한다.** 이벤트를 질의할 수 있을 뿐 아니라, 이벤트 로그로 과거 상태를 재구성하고 소급 변경에 맞춰 상태를 자동 조정하는 기반으로 쓴다. 이벤트 저장소가 진실의 원천이고 현재 상태는 거기서 파생된다. 그가 드는 가장 친숙한 예는 버전 관리 시스템이다. 커밋 로그가 이벤트 저장소이고 작업 트리가 상태다.

같은 글이 꼽는 능력은 세 가지다.

| 능력 | 뜻 |
|---|---|
| 완전 재구성(Complete Rebuild) | 상태를 버리고 이벤트를 처음부터 재생해 다시 만든다 |
| 시간 질의(Temporal Query) | 임의 시점의 상태를 구한다 |
| 이벤트 재생(Event Replay) | 과거 이벤트가 틀렸으면 고쳐서 이후 결과를 다시 계산한다 |

긴 이벤트 열을 매번 처음부터 재생하지 않도록 **스냅샷**을 두는 것도 같은 글에 나온다. 2017년 글에서 Fowler 는 흔한 오해 하나를 바로잡는다. 이벤트 소싱이 **반드시 비동기일 필요는 없다** — 로컬 git 저장소를 갱신하는 것처럼 동기로도 된다.

```kotlin
// 이벤트 소싱 집합체: 상태는 이벤트를 접어서(fold) 만든다
sealed interface AccountEvent
data class Deposited(val amount: Long) : AccountEvent
data class Withdrawn(val amount: Long) : AccountEvent

data class Account(val balance: Long = 0) {
    fun apply(e: AccountEvent) = when (e) {
        is Deposited -> copy(balance = balance + e.amount)
        is Withdrawn -> copy(balance = balance - e.amount)
    }
    fun withdraw(amount: Long): AccountEvent {
        require(amount <= balance) { "잔액 부족" }   // 결정은 현재 상태로
        return Withdrawn(amount)                       // 결과는 새 이벤트로
    }
    companion object {
        fun replay(events: List<AccountEvent>) = events.fold(Account()) { acc, e -> acc.apply(e) }
    }
}
```

### 4. CQRS

[CQRS](https://martinfowler.com/bliki/CQRS.html)(Command Query Responsibility Segregation)는 Fowler 가 Greg Young 에게서 처음 들었다고 밝힌 패턴으로, **갱신용 모델과 조회용 모델을 분리**한다. 뿌리는 Bertrand Meyer 가 *Object-Oriented Software Construction* 에서 만든 [명령-질의 분리(CQS)](https://martinfowler.com/bliki/CommandQuerySeparation.html) — 메서드는 상태를 바꾸는 명령이거나 값을 반환하는 질의 중 하나여야 한다 — 를 모델 수준으로 끌어올린 것이다. Greg Young 의 [CQRS Documents](https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf)가 초기 설명 자료다.

```
         명령(Command)                         질의(Query)
 클라이언트 ──▶ [쓰기 모델: 규칙·검증] ──저장──▶ 쓰기 저장소
                         │ 이벤트/변경 전파 (비동기면 지연 발생)
                         ▼
                [읽기 모델: 화면별 비정규화 뷰] ◀── 클라이언트 조회
```

Fowler 는 CQRS 에 대해 가장 강하게 경고한다. **대부분의 시스템에서 CQRS 는 위험한 복잡도를 더한다.** 그가 본 사례 다수는 좋지 않았고, CQRS 가 시스템을 심각한 어려움에 빠뜨리는 주요 원인으로 보였다고 쓴다. 적용한다면 시스템 전체가 아니라 특정 부분(DDD 의 바운디드 컨텍스트)에만 쓰라고 권한다. 2017년 글은 CQRS 가 **엄밀히는 이벤트와 무관하다** — 이벤트 없이도 쓸 수 있다 — 는 점도 짚는다.

Microsoft 의 [CQRS](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)·[Event Sourcing](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) 패턴 문서는 읽기 모델의 결과적 일관성, 이벤트 버전 관리 같은 고려 사항을 정리한다.

### 네 패턴 비교

| 패턴 | 푸는 문제 | 핵심 비용 | 독립 사용 |
|---|---|---|---|
| 이벤트 알림 | 시스템 간 결합 | 흐름이 코드에 안 보임 | 가능 |
| 상태 이전 | 원 시스템 의존·지연 | 사본 관리, 결과적 일관성 | 가능 |
| 이벤트 소싱 | 감사·이력·재구성 | 스키마 진화, 재생 비용, 학습 곡선 | 가능 |
| CQRS | 읽기·쓰기 모델의 상충 | 두 모델 유지, 동기화 | 가능(이벤트 없이도) |

### 이중 쓰기와 트랜잭셔널 아웃박스

Chris Richardson 의 [Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html) 패턴은 이중 쓰기 문제를 이렇게 푼다. 업무 데이터와 함께 **같은 DB 트랜잭션으로 outbox 테이블에 메시지를 기록**하고, 별도의 메시지 릴레이가 outbox 를 읽어 브로커에 발행한다. 같은 페이지는 릴레이가 **같은 메시지를 두 번 이상 발행할 수 있으므로 소비자는 멱등이어야 하며**, 처리한 메시지 ID 를 기록하는 방법을 제시한다. 브로커 자체도 중복 전달을 할 수 있으므로 소비자 멱등성은 어차피 필요하다는 점도 덧붙인다.

```sql
BEGIN;
INSERT INTO orders (id, customer_id, total) VALUES ('o-42', 'c-7', 39000);
INSERT INTO outbox (id, aggregate_id, type, payload, created_at)
VALUES ('e-901', 'o-42', 'OrderPlaced', '{"orderId":"o-42","total":39000}', now());
COMMIT;
-- 릴레이: SELECT ... FROM outbox WHERE published_at IS NULL ORDER BY created_at
--         → 브로커 발행 → published_at 갱신 (실패 시 재시도 → 중복 가능)
```

```python
# 소비자 멱등 처리: 같은 이벤트 ID 는 한 번만 반영
def handle(event, db):
    with db.transaction():
        inserted = db.execute(
            "INSERT INTO processed_events(id) VALUES (%s) ON CONFLICT DO NOTHING",
            (event["id"],)).rowcount
        if inserted == 0:
            return            # 이미 처리함
        db.execute("UPDATE stock SET qty = qty - %s WHERE sku = %s",
                   (event["qty"], event["sku"]))
```

이벤트의 공통 봉투 형식이 필요하면 CNCF 의 [CloudEvents](https://cloudevents.io)를 참고할 수 있다. [명세](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)는 `id`, `source`, `specversion`, `type` 을 필수 속성으로 정하고, 공식 사이트에 따르면 2024년 1월 CNCF 졸업(Graduated) 프로젝트가 됐다.

## 흔한 오해와 함정

- **"이벤트 기반 = 이벤트 소싱."** 이벤트 알림만 쓰는 시스템이 대부분이다. 이벤트 소싱은 상태 저장 방식에 관한 결정이고, 시스템 간 통신 방식과는 별개다.
- **"CQRS 는 이벤트 소싱과 한 세트."** 둘은 자주 같이 쓰이지만 독립적이다. Fowler 가 들은 "이벤트 소싱 재앙" 사례에서도 그는 CQRS 와의 혼동 가능성부터 의심했다.
- **"이벤트 소싱은 비동기여야 한다."** Fowler 가 직접 부정한 오해다.
- **"이벤트로 바꾸면 결합이 사라진다."** 이벤트 스키마가 새 계약이 된다. 필드 이름 하나 바꾸는 것이 API 변경과 같은 무게를 갖는다(SE100 #029).
- **"브로커가 정확히 한 번 전달을 보장하니 멱등성은 필요 없다."** 아웃박스 릴레이 단계에서도 중복이 생긴다. 소비자 멱등성은 기본 전제로 설계한다.
- **"읽기 모델은 즉시 반영된다."** 비동기 전파라면 쓰기 직후 조회에 옛 값이 보일 수 있다.

## 확인 문제

1. 이벤트 알림과 이벤트 전달 상태 이전의 차이를 수신자 행동 기준으로 설명하라.
2. "수동공격적 명령" 이란 무엇이며 어떻게 고치는가?
3. 이벤트 소싱이 제공하는 세 가지 능력은?
4. Fowler 가 CQRS 도입에 대해 권하는 범위는?
5. 트랜잭셔널 아웃박스를 써도 소비자 멱등성이 필요한 이유는?

### 풀이

1. 이벤트 알림의 수신자는 최소 정보만 받고 필요하면 원 시스템에 다시 조회한다. 상태 이전의 수신자는 이벤트에 담긴 데이터로 자기 사본을 갱신하므로 원 시스템에 묻지 않는다.
2. 보내는 쪽이 수신자의 특정 동작을 기대하면서 메시지를 이벤트 형태로 보내는 것. 기대가 있다면 명령 메시지로 의도를 명시한다.
3. 완전 재구성, 시간 질의(임의 시점 상태), 이벤트 재생(과거 이벤트 수정 후 재계산).
4. 시스템 전체가 아니라 특정 부분(바운디드 컨텍스트)에만 적용하라고 권하며, 대부분의 시스템에서는 위험한 복잡도를 더한다고 경고한다.
5. 메시지 릴레이가 발행 후 기록 전에 실패하면 같은 메시지를 다시 발행할 수 있고, 브로커도 중복 전달할 수 있기 때문이다.

## 더 읽을거리 (References)

- Martin Fowler, [What do you mean by "Event-Driven"?](https://martinfowler.com/articles/201701-event-driven.html), 2017
- Martin Fowler, [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html), [CQRS](https://martinfowler.com/bliki/CQRS.html), [CommandQuerySeparation](https://martinfowler.com/bliki/CommandQuerySeparation.html)
- Greg Young, [CQRS Documents](https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf), 2010
- Microsoft Azure Architecture Center, [CQRS pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs), [Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- Chris Richardson, [Pattern: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- CloudEvents, [cloudevents.io](https://cloudevents.io), [Specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)
- CS300: [마이크로서비스 vs 모놀리스]({% post_url 2026-10-10-cs300-199-microservices-vs-monolith %}), [분산 트랜잭션: 2PC 와 사가]({% post_url 2026-10-10-cs300-137-distributed-transactions-2pc-and-saga %})
