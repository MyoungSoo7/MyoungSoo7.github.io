---
layout: post
title: "[CS300 #138] 멱등성과 재시도 — 두 번 보내도 한 번만 일어나게"
date: 2026-10-10 20:18:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, idempotency, retry, exponential-backoff]
---

컴퓨터공학 300 주제 시리즈의 138번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

멱등한 연산은 한 번 하든 여러 번 하든 결과가 같은 연산이다. 분산 시스템에서는 응답이 사라졌을 때 다시 보낼 수밖에 없으므로, 재시도를 안전하게 하려면 연산을 멱등하게 만들어야 하고, 재시도 자체는 지수 백오프와 지터로 간격을 벌려야 한다.

## 왜 필요한가

분산 시스템의 8가지 오해 글에서 본 그림을 다시 보자. 요청을 보냈는데 타임아웃이 났다. 요청이 사라졌을 수도, 서버가 처리했는데 응답만 사라졌을 수도 있다. 클라이언트는 구별할 수 없다.

선택지는 둘이다.

- **다시 보내지 않는다** → 요청이 사라진 경우 일이 안 된다(최대 한 번, at-most-once).
- **다시 보낸다** → 응답만 사라진 경우 일이 두 번 된다(최소 한 번, at-least-once).

결제라면 둘 다 곤란하다. 돈이 안 빠지거나, 두 번 빠지거나. "정확히 한 번(exactly-once)" 을 네트워크 수준에서 보장하는 방법은 없다. 대신 **최소 한 번 전달 + 멱등한 처리 = 효과상 정확히 한 번** 이라는 조합을 만든다. 이 글의 핵심은 이 등식이다.

## 핵심 개념

### 멱등성의 정의

수학에서 f(f(x)) = f(x) 인 함수를 멱등하다고 한다. 시스템에서는 "같은 요청을 여러 번 적용해도 한 번 적용한 것과 서버 상태가 같다" 는 뜻이다.

| 연산 | 멱등한가 |
|---|---|
| `x = 5` | 예 |
| `x = x + 1` | 아니오 |
| 파일 삭제 | 예(두 번째는 "없음" 이지만 상태는 같다) |
| "이메일 보내기" | 아니오 |
| `UPSERT ... ON CONFLICT DO NOTHING` | 예 |

응답까지 같을 필요는 없다. 두 번째 `DELETE` 는 404 를 줄 수 있지만 서버 상태는 같다.

### HTTP 메서드

HTTP 의미론 표준(RFC 9110)은 메서드의 성질을 정한다.

| 메서드 | 안전(상태 변경 없음) | 멱등 |
|---|---|---|
| GET, HEAD, OPTIONS, TRACE | 예 | 예 |
| PUT, DELETE | 아니오 | 예 |
| POST, PATCH | 아니오 | 보장 안 됨 |

표준은 멱등한 메서드의 요청은 응답을 받기 전에 연결이 끊기면 자동으로 재시도할 수 있다고 설명한다. 그래서 프록시나 클라이언트 라이브러리가 GET 은 알아서 재시도하지만 POST 는 하지 않는다.

### 멱등성 키 (Idempotency Key)

POST 처럼 본래 멱등하지 않은 연산은 **클라이언트가 만든 고유 키**로 멱등하게 만든다.

```
POST /payments
Idempotency-Key: 6f1c...e2         ← 결제 "의도" 하나에 키 하나
{ "amount": 10000 }
```

1. 서버는 키를 처음 보면 처리하고, 키와 결과를 함께 저장한다.
2. 같은 키가 다시 오면 처리하지 않고 저장된 결과를 돌려준다.
3. 같은 키로 다른 본문이 오면 오류로 거절한다.

주의할 점이 있다.

- 키 저장과 실제 처리는 **같은 트랜잭션**이어야 한다. 처리만 되고 키 저장 전에 죽으면 다음 재시도가 또 처리한다.
- 같은 키의 요청이 **동시에** 두 개 오면 하나만 처리되도록 잠금이나 유일 제약이 필요하다.
- 키는 재시도마다 새로 만드는 것이 아니라 **사용자 의도 하나에 하나**다. 사용자가 "결제" 버튼을 한 번 눌렀으면 그 클릭에 키 하나다.

Stripe 같은 결제 API 가 이 방식을 쓰고, IETF 에서 `Idempotency-Key` 헤더를 표준화하는 초안이 진행 중이다.

### 다른 멱등화 기법

- **자연 키 + 유일 제약**: 주문 번호에 유일 인덱스를 걸고 `INSERT ... ON CONFLICT DO NOTHING`.
- **조건부 쓰기**: 버전이 맞을 때만 갱신(CAS, `If-Match`).
- **상태 전이 검사**: "결제 대기 → 결제 완료" 만 허용하면 두 번째 완료 요청은 무시된다.
- **소비자 측 중복 제거**: 메시지 ID 를 처리 완료 테이블에 기록해 같은 ID 는 건너뛴다.

### 재시도: 언제, 얼마나, 어떤 간격으로

재시도는 공짜가 아니다. 서버가 과부하로 느려졌는데 모든 클라이언트가 즉시 재시도하면 부하가 몇 배가 되어 회복이 불가능해진다(재시도 폭풍).

- **재시도할 오류만 재시도한다.** 타임아웃, 503, 연결 실패는 재시도 대상이다. 400(잘못된 요청)은 몇 번 해도 같다.
- **지수 백오프**: 대기 시간을 base × 2^n 으로 늘리고 상한(cap)을 둔다.
- **지터(jitter)**: 대기 시간에 무작위를 섞는다. 모든 클라이언트가 같은 순간에 실패하면 같은 순간에 재시도해 다시 몰리기 때문이다. AWS Builders' Library 는 백오프에 지터를 더해 재시도 시각을 흩어 놓는 방법을 설명한다. 아래 예제는 0 과 백오프 값 사이에서 무작위로 고르는 가장 단순한 형태(흔히 full jitter 라 부른다)를 쓴다.
- **횟수와 전체 시간 제한**: 무한 재시도는 없다. 호출 체인의 각 층이 3번씩 재시도하면 맨 아래는 27배의 부하를 받는다. 재시도는 한 층에서만 하는 것이 원칙이다.
- **재시도 예산**: 전체 요청 대비 재시도 비율에 상한(예: 10%)을 둔다.

## 직접 해 보기

요청은 항상 서버에 도착하지만 응답의 30% 가 사라지는 결제 서버를 만든다. 클라이언트는 타임아웃이면 최대 5번 재시도한다. 멱등 키가 있을 때와 없을 때 실제 출금 횟수를 비교한다.

```python
import random, uuid
random.seed(5)

class PaymentServer:
    def __init__(self, use_keys):
        self.use_keys, self.charges, self.seen = use_keys, [], {}
    def charge(self, amount, key):
        if self.use_keys and key in self.seen:
            return self.seen[key]                 # 같은 키: 저장해 둔 결과를 그대로 돌려줌
        self.charges.append(amount)               # 실제 출금
        result = f"ok:{len(self.charges)}"
        if self.use_keys: self.seen[key] = result
        return result

def call(server, amount, key):
    """요청은 항상 도착하지만, 30% 확률로 응답이 사라진다(타임아웃)."""
    result = server.charge(amount, key)
    if random.random() < 0.3: raise TimeoutError
    return result

def backoff(attempt, base=0.1, cap=5.0):
    return random.uniform(0, min(cap, base * 2 ** attempt))   # full jitter

def pay(server, amount, max_attempts=5):
    key = str(uuid.uuid4())                       # 한 번의 '의도' 에 키 하나
    for attempt in range(max_attempts):
        try:
            return call(server, amount, key)
        except TimeoutError:
            _ = backoff(attempt)                  # 실제라면 time.sleep(_)
    return "포기"

for use_keys in (False, True):
    s = PaymentServer(use_keys)
    for _ in range(1000): pay(s, 10_000)
    print(f"멱등 키 {'사용' if use_keys else '없음'}: 결제 의도 1000건 → 실제 출금 {len(s.charges)}건")

random.seed(0)
print("백오프 예시(초):", [round(backoff(a), 2) for a in range(6)])
```

```
멱등 키 없음: 결제 의도 1000건 → 실제 출금 1446건
멱등 키 사용: 결제 의도 1000건 → 실제 출금 1000건
백오프 예시(초): [0.08, 0.15, 0.17, 0.21, 0.82, 1.3]
```

키가 없으면 응답이 사라질 때마다 재시도가 새 출금이 되어 1000건 의도에 1446건이 빠져나간다. 키를 쓰면 정확히 1000건이다. 재시도와 네트워크 손실은 그대로인데 결과만 "정확히 한 번" 처럼 된다. 백오프 값은 시도마다 상한이 두 배로 커지면서 그 안에서 무작위로 뽑힌다.

## 현업에서는

- **메시지 큐 소비자.** Kafka, SQS, RabbitMQ 의 기본 전달 보장은 최소 한 번이다. 소비자가 처리 후 오프셋 커밋 전에 죽으면 같은 메시지를 다시 받는다. 소비자 로직을 멱등하게 짜는 것이 기본 전제다.
- **쿠버네티스의 선언적 API.** `kubectl apply` 는 "원하는 상태" 를 선언하므로 몇 번을 실행해도 결과가 같다. 컨트롤러의 조정 루프도 멱등하게 설계되어, 같은 이벤트를 여러 번 받거나 중간에 재시작해도 안전하다. 쿠버네티스가 장애에 강한 이유 중 큰 부분이 이 멱등성이다.
- **배포 스크립트와 마이그레이션.** `CREATE TABLE IF NOT EXISTS`, `mkdir -p` 처럼 멱등하게 작성한 스크립트는 중간에 실패해도 다시 돌리면 된다. 멱등하지 않은 스크립트는 실패 지점을 사람이 찾아 손으로 이어야 한다.
- **결제·주문 API.** 프런트엔드가 버튼 클릭마다 키를 만들어 보내고, 서버는 키 테이블에 유일 제약을 건다. 사용자가 버튼을 두 번 누르거나 모바일 네트워크가 끊겨 앱이 재시도해도 이중 결제가 나지 않는다.

## 확인 문제

1. at-most-once, at-least-once 의 차이와 각각의 위험은?
2. HTTP 에서 PUT 은 멱등하고 POST 는 그렇지 않은 이유를 예로 설명하라.
3. 멱등성 키를 재시도할 때마다 새로 생성하면 어떻게 되는가?
4. 지터 없이 지수 백오프만 쓰면 어떤 문제가 남는가?
5. 3계층 호출 체인에서 각 층이 실패 시 3번씩 시도하면 최하층은 최대 몇 배의 요청을 받는가?

### 풀이

1. at-most-once 는 다시 보내지 않아 유실 위험, at-least-once 는 다시 보내 중복 위험이 있다.
2. PUT 은 "이 자원을 이 상태로" 를 지정하므로 여러 번 해도 같은 상태다. POST 는 흔히 "새로 하나 만들어라" 라서 여러 번 하면 여러 개가 생긴다.
3. 서버는 매번 다른 요청으로 보고 처리하므로 멱등성 키가 아무 효과가 없다.
4. 동시에 실패한 클라이언트들이 같은 시각에 재시도해 부하가 다시 한꺼번에 몰린다.
5. 3 × 3 × 3 = 27배.

## 더 읽을거리 (References)

- [RFC 9110 — HTTP Semantics, 9.2.2 Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)
- [The Idempotency-Key HTTP Header Field (IETF Internet-Draft)](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)
- [AWS Builders' Library — Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Stripe API — Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
