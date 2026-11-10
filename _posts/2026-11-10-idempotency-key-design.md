---
layout: post
title: "멱등성과 멱등키 — \"한 번만 일어나게\"를 어디서, 어떻게 보장할까"
date: 2026-11-10 23:39:13 +0900
categories: [architecture, msa]
tags: [idempotency, idempotency-key, retry, outbox, kafka, http, distributed-systems]
---

[앞 글(MSA · EDA · CDC · CQRS 비교)]({% post_url 2026-11-10-msa-eda-cdc-cqrs-comparison %})의 4장에서 "Outbox 릴레이는 같은 메시지를 두 번 보낼 수 있으므로 **소비자는 멱등해야 한다**"고 한 줄로 넘어갔다. 이 글은 그 한 줄을 펼친다. 분산 시스템에서 "정확히 한 번"은 네트워크가 주는 것이 아니라 **수신 쪽이 만들어 내는 것**이다. 그 도구가 멱등성이고, HTTP 경계에서는 그 손잡이가 멱등키(Idempotency-Key)다.

> 이 블로그의 [CS300 #138 멱등성과 재시도]({% post_url 2026-10-10-cs300-138-idempotency-and-retries %})가 개념과 재시도 간격(백오프)을 다뤘다면, 이 글은 **멱등키를 서버에 실제로 구현할 때 부딪히는 결정들**에 집중한다.

## 1. 왜 "그냥 다시 보내기"가 위험한가

클라이언트가 `POST /payments` 를 보냈는데 타임아웃이 났다. 가능한 상태는 세 가지다.

1. 요청이 서버에 닿지도 않았다.
2. 서버가 처리했지만 응답이 돌아오는 길에 끊겼다.
3. 서버가 **아직 처리 중**이다.

클라이언트는 이 셋을 구분할 수 없다. IETF 초안도 정확히 이 장면으로 시작한다 — 타임아웃이 나면 클라이언트는 리소스가 만들어졌는지, 서버가 처리를 끝냈는지조차 모르고, 따라서 안전하게 재시도할 수 있는지도 모른다([IETF draft §1][ietf]). 재시도하면 2번 상황에서 이중 결제가 나고, 재시도하지 않으면 1번 상황에서 결제가 누락된다.

AWS의 Malcolm Featonby는 이 딜레마의 대안 — 매번 "있는지 먼저 조회해 보는" 대사(reconciliation) — 이 드문 엣지 케이스를 위해 너무 많은 일을 시키며, 그래도 "그 리소스를 *내가* 만든 건지, 다른 프로세스가 만든 건지"는 여전히 모른다고 지적한다([AWS Builders' Library][aws]). 해법은 연산 자체를 **재시도해도 부작용이 추가로 생기지 않게**, 즉 멱등하게 만드는 것이다.

## 2. 두 종류의 멱등성을 구분하자

### 2-1. HTTP 메서드의 멱등성 (프로토콜 약속)

[RFC 9110 §9.2.2][rfc9110]는 "같은 요청을 여러 번 보냈을 때 서버에 대한 **의도된 효과**가 한 번 보낸 것과 같으면" 그 메서드를 멱등하다고 정의한다. `PUT`, `DELETE`, 그리고 안전한 메서드(`GET`, `HEAD`, `OPTIONS`, `TRACE`)가 여기 속하고, `POST`와 `PATCH`는 아니다.

중요한 단서가 두 가지 있다.

- RFC는 이 속성이 **사용자가 요청한 것**에만 적용되며, 서버가 요청마다 로그를 남기는 등 별도의 부작용을 갖는 것은 자유라고 명시한다. 멱등성은 "아무 일도 안 일어난다"가 아니라 "*요청된 효과*가 한 번분"이라는 뜻이다.
- 이건 **메서드 의미론에 대한 약속**이지 구현 보장이 아니다. `PUT /accounts/1/balance` 를 "현재 잔액 + 100" 으로 구현하면 메서드 이름과 상관없이 멱등하지 않다.

### 2-2. 비즈니스 연산의 멱등성 (애플리케이션 책임)

"주문 생성", "결제 승인", "포인트 적립"은 본질적으로 `POST`다. 여기서 멱등성은 프로토콜이 주지 않으므로 **애플리케이션이 중복을 식별하는 수단**을 따로 가져야 한다. 그 수단이 두 가지 축으로 나뉜다.

| 축 | 식별자 | 대표 위치 |
|---|---|---|
| 동기 요청 경계 | 클라이언트가 만든 **멱등키** | HTTP API (결제·주문 생성) |
| 비동기 메시지 경계 | 메시지/이벤트 **ID** | 이벤트 소비자 (Outbox 이후) |

둘은 같은 아이디어 — *"이 ID를 본 적이 있나?"* — 를 다른 경계에 적용한 것이다. 3~5장은 앞의 것, 6장은 뒤의 것이다.

## 3. 왜 "요청 내용 해시"가 아니라 "클라이언트가 만든 키"인가

중복 판별을 요청 파라미터 해시로 하면 클라이언트는 아무것도 안 해도 된다. 편해 보인다. AWS는 이 접근이 **모든 경우에 통하지는 않는다**고 경험적으로 말한다. 같은 호출자가 짧은 간격으로 똑같은 DynamoDB 테이블 생성 요청을 두 번 보냈다면 중복일 가능성이 높지만, 똑같은 EC2 인스턴스 기동 요청 두 번은 **정말로 인스턴스 두 대를 원한 것**일 수 있다([AWS][aws]).

즉 "같은 내용"과 "같은 의도"는 다르다. 의도를 아는 쪽은 클라이언트뿐이므로, **클라이언트가 고유 식별자로 의도를 표현**하게 하는 것이 AWS의 선호 방식이고(EC2에선 `ClientToken`), Stripe와 IETF 초안의 `Idempotency-Key`도 같은 발상이다. 덤으로 그 식별자가 로그(CloudTrail 등)에 남아 감사 추적이 쉬워진다([AWS][aws]).

## 4. Idempotency-Key 헤더 — 표준화 현황

IETF HTTPAPI 워킹그룹에서 `Idempotency-Key` 요청 헤더를 표준화하고 있다. 이 글을 쓰는 시점의 최신본은 [draft-ietf-httpapi-idempotency-key-header-08][ietf](2026-10-22 게시, Standards Track 지향)이다. **아직 RFC가 아닌 Internet-Draft**이므로 "작업 중인 문서"로 인용해야 하며, 세부는 바뀔 수 있다.

초안의 핵심 규칙을 요약하면:

- **문법**: Structured Field의 String. 예: `Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"`. UUID 같은 랜덤 식별자를 권장(RECOMMENDED).
- **유일성**: 키는 유일해야 하고, **다른 페이로드의 요청에 재사용해서는 안 된다**(MUST NOT).
- **만료**: 리소스는 시간 기반 만료를 둘 수 있고(MAY), 그 정책을 문서로 공개해야 한다(SHOULD).
- **지문(fingerprint)**: 키와 함께 페이로드 체크섬 등으로 만든 지문을 써서 요청 동일성을 판단할 수 있다(MAY).
- **오류 응답**

| 상황 | 상태 코드 | 클라이언트 행동 |
|---|---|---|
| 키가 필요한 연산인데 헤더 없음 | `400 Bad Request` | 고쳐서 재시도 |
| 같은 키, **다른 페이로드** | `422 Unprocessable Content` | 고쳐서 재시도 |
| 같은 키, **원 요청이 아직 처리 중** | `409 Conflict` | 그대로 재시도 가능 |
| 원 요청이 끝난 뒤 재시도 | 원 요청 결과와 **일관된 응답** | — |

초안의 구현 현황 절에는 Stripe, Adyen, Dwolla, WorldPay 등이 이미 `Idempotency-Key`라는 이름의 커스텀 헤더를 쓰고 있다고 기록돼 있다 — 표준이 관행을 뒤따라 정리하는 형태다.

## 5. 서버 구현에서 내려야 하는 다섯 가지 결정

### 결정 1. 키의 범위(scope) — "누구의" 키인가

키를 전역 유일로 다루면 서로 다른 고객의 키가 우연히(혹은 악의로) 겹칠 때 남의 응답을 돌려줄 수 있다. AWS는 멱등 "세션"을 **고객 식별자 + 클라이언트 요청 식별자** 조합으로 잡는다고 설명한다([AWS][aws]). 실무적으로는 `(tenant_or_account_id, endpoint, idempotency_key)`를 유니크 키로 두는 것이 안전하다.

### 결정 2. 같은 키, 다른 내용 — 거부한다

키는 같은데 파라미터가 다르면? AWS는 "고객이 다른 결과를 의도했다고 가정하는 것이 가장 안전하다"며 **파라미터 불일치 검증 오류**를 반환하고, 이를 위해 최초 요청의 파라미터를 키와 함께 저장한다([AWS][aws]). Stripe도 들어온 파라미터를 원 요청과 비교해 다르면 오류를 낸다([Stripe][stripe]). IETF 초안에서는 이게 `422`다. 그래서 저장 레코드에는 **요청 지문(해시)**이 들어가야 한다.

### 결정 3. 처리 중인 요청과 겹칠 때 — 409로 밀어낸다

첫 요청이 아직 끝나지 않았는데 같은 키의 재시도가 들어오는 경우가 가장 까다롭다. 두 요청이 동시에 "본 적 없음"을 확인하고 둘 다 처리하면 멱등키가 무력화된다. 그래서 **"키 선점"은 원자적이어야 한다** — 보통 유니크 제약이 걸린 행을 `INSERT`(또는 `INSERT … ON CONFLICT DO NOTHING`)하는 것으로 잡는다. 선점에 실패한 쪽은 기존 행의 상태를 보고, 아직 `IN_PROGRESS`면 `409 Conflict`(초안 §2.7)를 돌려준다. Stripe도 동시 실행 중인 요청과 충돌한 경우는 결과를 저장하지 않으므로 다시 시도할 수 있다고 문서화한다([Stripe][stripe]).

### 결정 4. 무엇을 되돌려 줄 것인가 — "같은 바이트" vs "같은 의미"

여기서 사업자마다 선택이 갈린다.

- **Stripe API v1**: 엔드포인트 실행이 시작된 뒤의 **상태 코드와 본문을 저장**하고, 같은 키의 재시도엔 그 저장된 응답을 그대로 준다. **`500` 오류까지 포함해서**다. 반면 API v2는 성공한 작업을 반복하지 않되, 실패하거나 부분 실패한 작업은 가능하면 완료까지 재시도한 뒤 갱신된 응답을 준다([Stripe][stripe]).
- **AWS (EC2 RunInstances)**: 바이트 동일이 아니라 **의미적으로 동등한(semantically equivalent)** 응답을 준다. 처음 응답이 `pending`이었다면 몇 분 뒤 같은 `ClientToken` 재시도엔 `running`이 나온다. 같은 인스턴스 ID를 가리키므로 의미는 같다([AWS][aws]).

AWS는 또 "이미 존재함(`ResourceAlreadyExists`)"을 돌려주는 방식을 비판한다. 서버 입장에선 부작용이 없으니 멱등하지만, **클라이언트 입장에선** 자신이 만든 건지 남이 만든 건지 모르게 되고 재시도 후 실행 흐름이 바뀌므로 "클라이언트 쪽 부작용"이 생긴다는 것이다([AWS][aws]). 재시도를 SDK 안에 숨기려면 첫 응답과 같은 의미의 응답이 필요하다.

### 결정 5. 키를 얼마나 보관할까 — TTL

영원히 보관할 수는 없다. 저장 비용 문제도 있지만, AWS는 아주 오래전 키와 새 키가 충돌하면 오히려 고객 경험을 해친다고 말한다. EC2는 **리소스 수명 + 늦게 도착하는 요청이 다 도착했거나 더는 유효하지 않다고 볼 만한 간격**으로 보관한다([AWS][aws]). Stripe v1은 최소 24시간이 지난 키를 자동 정리할 수 있고, 정리된 뒤 같은 키가 오면 **새 요청으로 처리**한다([Stripe][stripe]). 즉 TTL 밖에서는 멱등성이 보장되지 않으며, IETF 초안이 만료 정책을 **문서로 공개하라**고 요구하는 이유가 이것이다.

## 6. 키 기록과 비즈니스 변경은 한 트랜잭션에

AWS 글에서 가장 중요한 문장은 이것이다: 멱등 토큰을 기록하는 일과 요청을 처리하는 **모든 변경 연산을 하나의 ACID 연산으로** 묶어야 한다. 그렇지 않으면 "토큰은 기록됐는데 리소스는 안 만들어진" 상태나 그 반대가 생긴다([AWS][aws]).

같은 DB 안에서 끝나는 연산이면 간단하다.

```sql
-- 멱등키 테이블 (PostgreSQL 예시)
CREATE TABLE idempotency_keys (
  account_id      BIGINT       NOT NULL,
  idem_key        VARCHAR(255) NOT NULL,
  request_hash    CHAR(64)     NOT NULL,   -- 결정 2: 같은 키·다른 내용 감지
  status          VARCHAR(16)  NOT NULL,   -- IN_PROGRESS / COMPLETED
  response_code   INT,
  response_body   JSONB,                   -- 결정 4: 재생할 응답
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  PRIMARY KEY (account_id, idem_key)       -- 결정 1: 범위
);
```

```
BEGIN
  INSERT INTO idempotency_keys(account_id, idem_key, request_hash, status)
  VALUES (:acct, :key, :hash, 'IN_PROGRESS')
  ON CONFLICT DO NOTHING                     -- 결정 3: 원자적 선점
  → 0 행이면: 기존 행 조회
        hash 다름        → 422
        IN_PROGRESS      → 409
        COMPLETED        → 저장된 응답 재생
  → 1 행이면: 비즈니스 처리(주문 INSERT 등)
             + idempotency_keys 를 COMPLETED·응답으로 UPDATE
COMMIT
```

문제는 처리 도중 **외부 시스템**(PG사 결제 API, 메일 발송)을 부르는 경우다. 외부 호출은 내 DB 트랜잭션으로 롤백되지 않는다. Stripe 엔지니어 Brandur Leach는 이를 "외부 상태 변경(foreign state mutation)"이라 부르고, 요청을 **원자적 단계(atomic phase)와 복구 지점(recovery point)**으로 쪼개 키 레코드에 진행 단계를 기록한 뒤, 재시도 시 마지막 복구 지점부터 이어가는 설계를 제시한다([Leach 2017][brandur]). 그리고 같은 글에서, 로컬 ACID 저장소만 건드리는 엔드포인트라면 요청을 트랜잭션 하나에 매핑하는 훨씬 단순한 방법을 쓸 수 있으니 **가능하면 그쪽을 택하라**고 권한다. 외부 호출 자체도 가능하면 하위 시스템의 멱등키(예: PG사가 받는 키)를 다시 넘겨 연쇄적으로 멱등하게 만든다.

## 7. 메시지 소비자의 멱등성 — 앞 글로 돌아가서

Outbox + CDC/릴레이 구조에서 브로커는 보통 **at-least-once** 전달을 보장한다. microservices.io의 Idempotent Consumer 패턴은 그 대가를 이렇게 정리한다: 같은 메시지로 소비자가 여러 번 호출될 수 있으므로, 예컨대 `AccountDebited` 메시지를 받아 잔액에서 빼는 소비자가 멱등하지 않으면 잔액이 틀어진다([Richardson][mio]).

해법은 HTTP 멱등키와 같은 모양이다.

- 소비자는 트랜잭션 안에서 **처리한 메시지 ID**를 `PROCESSED_MESSAGES` 테이블에 `INSERT`한다. 기본키가 `(subscriberId, messageId)`이므로 이미 처리한 메시지면 `INSERT`가 실패하고, 트랜잭션을 롤백해 무시한다.
- 또는 별도 테이블 대신 **생성·갱신하는 비즈니스 엔티티 자체에** 메시지 ID를 저장할 수도 있다([Richardson][mio]).

여기서도 핵심은 6장과 같다 — **"처리했음" 기록과 비즈니스 변경이 같은 트랜잭션**이어야 한다. 기록만 먼저 커밋하고 처리에서 죽으면 메시지가 유실되고, 처리만 커밋하고 기록에서 죽으면 중복 처리된다.

### Kafka 멱등 프로듀서는 이걸 대신해 주지 않는다

Kafka의 `enable.idempotence=true`는 "프로듀서가 스트림에 각 메시지의 **정확히 한 사본**만 쓰도록 보장"하며, `false`면 **브로커 장애 등으로 인한 프로듀서 재시도**가 중복을 쓸 수 있다고 문서화돼 있다. 활성화 조건은 `acks=all`, `retries > 0`, `max.in.flight.requests.per.connection ≤ 5`이고, 충돌 설정이 없으면 기본으로 켜진다([Apache Kafka 4.1 Producer Configs][kafka]).

문서가 말하는 보장 범위는 **프로듀서 클라이언트 내부 재시도로 생기는 중복**이다. 다음은 이 보장 바깥이다.

- Outbox 릴레이가 발행 후 "발행 완료" 표시 전에 죽어서, 재기동 뒤 **애플리케이션이 같은 레코드를 새로 `send()`** 하는 경우.
- 소비자가 처리 후 오프셋 커밋 전에 죽어서 **같은 레코드를 다시 읽는** 경우.

그러므로 브로커 설정과 별개로 **소비자 측 멱등성(7장)은 여전히 필요**하다. 앞 글에서 "소비자는 멱등해야 한다"고 한 것은 이 때문이다.

## 8. 체크리스트

- [ ] `POST`/`PATCH` 중 "두 번 일어나면 안 되는" 엔드포인트에 멱등키를 **필수**로 받는가? (없으면 `400`)
- [ ] 키 유니크 범위에 **계정/테넌트**가 포함되는가?
- [ ] **요청 지문**을 저장해 같은 키·다른 내용을 `422`로 거부하는가?
- [ ] 키 선점이 **유니크 제약 기반의 원자적 연산**인가? 처리 중 재시도에 `409`를 주는가?
- [ ] 키 기록과 비즈니스 변경이 **같은 트랜잭션**인가? 외부 호출은 복구 지점으로 쪼갰는가?
- [ ] 재시도 응답 정책(저장된 응답 재생 vs 의미적 동등 응답)이 **정해져 있고 문서화**됐는가?
- [ ] **TTL**을 정하고 공개했는가? TTL 밖 재사용은 새 요청이라는 점이 명시됐는가?
- [ ] 이벤트 소비자가 **처리한 메시지 ID**를 비즈니스 변경과 같은 트랜잭션에 기록하는가?
- [ ] 키에 **개인정보**(이메일·주민번호 등)를 넣지 않는가? (Stripe도 민감정보를 키로 쓰지 말라고 안내한다 [Stripe][stripe])

## 마치며

멱등성은 "중복이 안 생기게 하는 기술"이 아니라 **"중복이 생겨도 결과가 같게 만드는 설계"**다. 네트워크는 at-least-once까지만 약속하고, exactly-once *효과*는 수신자가 ID를 기억하는 것으로 완성된다. HTTP 경계에선 멱등키로, 메시지 경계에선 처리된 메시지 ID로 — 둘 다 "이 ID를 봤는가"를 **트랜잭션 안에서** 묻는다는 한 가지 원리다.

> 근거의 한계: 멱등키 구현 방식(응답 재생 vs 의미적 동등, TTL 길이)의 우열을 중립적으로 비교한 실증 연구는 찾지 못했다. 이 글의 권고는 IETF 초안(작업 중 문서)과 AWS·Stripe의 **벤더 1차 문서에 기술된 설계 선택**을 정리한 것이며, 각 방식의 장단은 해당 문서가 스스로 밝힌 근거를 옮긴 것이다.

## References

1. J. Jena, S. Dalal, D. Tishkin, "[The Idempotency-Key HTTP Header Field][ietf]", IETF Internet-Draft draft-ietf-httpapi-idempotency-key-header-08, 2026-10-22 (work in progress).
2. R. Fielding, M. Nottingham, J. Reschke (Eds.), "[RFC 9110: HTTP Semantics][rfc9110]", §9.2.2 Idempotent Methods, IETF, 2022.
3. Malcolm Featonby, "[Making retries safe with idempotent APIs][aws]", Amazon Builders' Library.
4. Stripe, "[Idempotent requests][stripe]", Stripe API Reference.
5. Brandur Leach, "[Implementing Stripe-like Idempotency Keys in Postgres][brandur]", 2017-10-27.
6. Chris Richardson, "[Pattern: Idempotent Consumer][mio]", microservices.io.
7. Apache Kafka, "[Producer Configs — enable.idempotence][kafka]", Kafka 4.1 documentation.
8. 앞 글: [MSA · EDA · CDC · CQRS 비교 — 넷은 같은 층의 선택지가 아니다]({% post_url 2026-11-10-msa-eda-cdc-cqrs-comparison %})

[ietf]: https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header
[rfc9110]: https://www.rfc-editor.org/rfc/rfc9110#section-9.2.2
[aws]: https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
[stripe]: https://docs.stripe.com/api/idempotent_requests
[brandur]: https://brandur.org/idempotency-keys
[mio]: https://microservices.io/patterns/communication-style/idempotent-consumer.html
[kafka]: https://kafka.apache.org/41/configuration/producer-configs/
