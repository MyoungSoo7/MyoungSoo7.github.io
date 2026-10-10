---
layout: post
title: "[CS300 #234] 분산 추적 — 요청 하나가 거쳐 간 길을 다시 그리기"
date: 2026-10-10 21:54:00 +0900
categories: [cs]
tags: [cs300, devops, tracing, opentelemetry, observability]
---

컴퓨터공학 300 주제 시리즈의 234번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

분산 추적은 요청 하나에 고유한 trace ID 를 붙여 서비스 경계를 넘을 때마다 전달하고, 각 구간(span)의 시작·끝·부모를 기록해, 나중에 그 요청의 전체 호출 트리와 시간 배분을 재구성하는 기법이다.

## 왜 필요한가

"주문 API 가 2초 걸린다." 메트릭은 여기까지 알려 준다. 그런데 주문 API 는 장바구니, 재고, 결제, 쿠폰 서비스를 부르고, 결제는 다시 외부 PG 와 DB 를 부른다. 2초 중 어디서 시간을 썼는가? 각 서비스의 로그를 시각으로 맞춰 가며 뒤지는 것은 서비스가 다섯 개만 넘어도 불가능에 가깝다. 동시에 수천 개 요청이 섞여 있기 때문이다.

분산 추적은 이 질문에 그림 한 장으로 답한다.

## 핵심 개념

### trace 와 span

- **span**: 하나의 작업 단위. 이름, 시작 시각, 종료 시각, 속성(attribute), 상태, 이벤트를 가진다. 예: "HTTP GET /orders", "SELECT orders", "call payment".
- **trace**: 같은 trace ID 를 공유하는 span 들의 트리. 요청 하나의 전체 여정이다.
- 각 span 은 자신의 span ID 와 **부모 span ID** 를 갖는다. 부모가 없는 span 이 루트다.

```
trace 4bf92f35...
[GET /orders/42 ......................................] 2000ms  (api-gateway)
  [auth.verify ..]                                       80ms  (auth)
  [orders.get ...........................................] 1880ms (orders)
     [SELECT orders ...]                                   150ms (postgres)
     [payment.status ..............................]       1500ms (payment)
        [HTTP POST pg.example/status ...........]          1400ms (외부)
```

이 그림(워터폴)만 보면 시간의 대부분이 외부 PG 호출에 있다는 것이 바로 보인다.

### 컨텍스트 전파

추적이 서비스 경계를 넘으려면 trace ID 와 현재 span ID 를 다음 호출에 실어 보내야 한다. HTTP 에서는 헤더로 보낸다. W3C Trace Context 권고안이 표준 헤더 형식을 정한다.

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             |  |                                |                |
             |  trace-id (16바이트, 32 hex)        parent-id(8바이트) trace-flags
             version                                               (01 = sampled)
```

- `trace-id` 는 전체 trace 를 식별한다. 모두 0 인 값은 무효다.
- `parent-id` 는 이 요청을 보낸 쪽의 span ID 다. 받는 쪽은 이것을 부모로 삼아 새 span 을 만든다.
- `trace-flags` 의 최하위 비트는 호출자가 이 trace 를 기록(sampled)했는지를 나타낸다.
- 벤더별 추가 정보는 `tracestate` 헤더에 담는다.

메시지 큐를 거칠 때도 같은 정보를 메시지 헤더(메타데이터)에 넣어 전파한다. 전파가 한 군데서 끊기면 trace 가 두 조각으로 갈라진다.

### 계측(instrumentation)

span 을 만드는 코드를 넣는 것을 계측이라 한다.

- **자동 계측**: HTTP 서버·클라이언트, DB 드라이버, 메시지 클라이언트 라이브러리에 붙는 에이전트나 플러그인이 span 생성과 헤더 전파를 대신한다.
- **수동 계측**: 비즈니스 로직의 중요한 구간에 직접 span 을 만든다.

OpenTelemetry 는 언어별 API·SDK, 자동 계측 라이브러리, 수집기(Collector), 전송 프로토콜(OTLP)을 제공하는 벤더 중립 표준이다. 앱은 OTLP 로 Collector 에 보내고, Collector 가 Jaeger, Tempo, Zipkin, 상용 백엔드 등으로 내보낸다. 백엔드를 바꿔도 앱 코드는 그대로다.

### 샘플링

모든 요청을 추적하면 데이터가 너무 많다. 그래서 일부만 기록한다.

| 방식 | 결정 시점 | 장단점 |
|---|---|---|
| Head-based | trace 시작 시 확률로 결정, 하위 서비스는 플래그를 따름 | 단순하고 싸다. 드문 에러 trace 를 놓칠 수 있다 |
| Tail-based | trace 가 끝난 뒤 전체를 보고 결정 | 에러·느린 trace 를 골라 남길 수 있다. Collector 가 trace 를 모아 둘 메모리가 필요하다 |

### 기원

이 구조는 Google 이 2010년 발표한 Dapper 논문에서 널리 알려졌다. 논문은 낮은 오버헤드, 애플리케이션 투명성(라이브러리 수준 계측), 샘플링을 핵심 설계 목표로 꼽았다. 이후 Zipkin, Jaeger, OpenTracing·OpenCensus 를 거쳐 OpenTelemetry 로 통합되었다.

## 직접 해 보기

`traceparent` 헤더를 만들고 파싱하는 것과, span 목록에서 트리를 재구성해 각 span 의 자기 시간(self time, 자식에게 쓰지 않은 시간)을 계산해 보자.

```python
import secrets, re

def new_traceparent(trace_id=None, sampled=True):
    trace_id = trace_id or secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    return f"00-{trace_id}-{span_id}-{'01' if sampled else '00'}", span_id

def parse(header):
    m = re.fullmatch(r"([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})", header)
    if not m or m.group(2) == "0" * 32 or m.group(3) == "0" * 16:
        return None
    return {"trace_id": m.group(2), "parent_id": m.group(3),
            "sampled": int(m.group(4), 16) & 1 == 1}

h, _ = new_traceparent()
print("parsed valid  :", parse(h) is not None)
print("parsed example:", parse("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
print("all-zero id   :", parse("00-" + "0" * 32 + "-00f067aa0ba902b7-01"))

# (span_id, parent_id, name, start_ms, end_ms)
spans = [
    ("a", None, "GET /orders/42",   0, 2000),
    ("b", "a",  "auth.verify",     10,   90),
    ("c", "a",  "orders.get",     100, 1980),
    ("d", "c",  "SELECT orders",  110,  260),
    ("e", "c",  "payment.status", 270, 1770),
    ("f", "e",  "POST pg/status", 300, 1700),
]
children = {}
for s in spans:
    children.setdefault(s[1], []).append(s)

def show(span, depth=0):
    sid, _, name, start, end = span
    kids = children.get(sid, [])
    self_ms = (end - start) - sum(k[4] - k[3] for k in kids)
    print(f"{'  ' * depth}{name:<18} total={end - start:5}ms self={self_ms:5}ms")
    for k in kids:
        show(k, depth + 1)

show(children[None][0])
```

출력은 다음과 같다. 새로 만든 헤더의 ID 는 매번 무작위이므로 검증 결과만 출력했다.

```
parsed valid  : True
parsed example: {'trace_id': '4bf92f3577b34da6a3ce929d0e0e4736', 'parent_id': '00f067aa0ba902b7', 'sampled': True}
all-zero id   : None
GET /orders/42     total= 2000ms self=   40ms
  auth.verify        total=   80ms self=   80ms
  orders.get         total= 1880ms self=  230ms
    SELECT orders      total=  150ms self=  150ms
    payment.status     total= 1500ms self=  100ms
      POST pg/status     total= 1400ms self= 1400ms
```

자기 시간을 보면 범인이 명확하다. 2초 중 1.4초가 외부 PG 호출이다. 이 계산은 자식 span 들이 겹치지 않는다고 가정했다. 병렬 호출이 있으면 자식 구간의 합집합으로 계산해야 한다.

## 현업에서는

- **끊긴 trace.** 가장 흔한 문제는 전파 누락이다. 직접 만든 HTTP 클라이언트, 비동기 작업 큐, 스레드 풀 경계에서 컨텍스트가 넘어가지 않으면 trace 가 조각난다. 경계마다 전파 여부를 확인한다.
- **로그·메트릭과 연결.** 로그에 trace ID 를 넣고(233번), 히스토그램 메트릭에 예시 trace ID(exemplar)를 붙이면, 대시보드의 느린 점 하나를 눌러 그 요청의 trace 로, 다시 그 trace 의 로그로 이동할 수 있다.
- **비용과 샘플링.** 트래픽이 많은 서비스는 head 샘플링 비율을 낮추고, 에러·고지연 trace 는 tail 샘플링으로 남기는 조합을 많이 쓴다.
- **서비스 메시와의 관계.** 서비스 메시의 사이드카 프록시가 span 을 만들어 줄 수는 있다. 하지만 들어온 요청과 나가는 요청을 연결하려면 앱이 헤더를 전달해 줘야 한다. 메시만으로는 완전한 trace 가 되지 않는다(239번).
- **민감 정보.** span 속성에 SQL 파라미터, 요청 본문, 토큰을 넣지 않는다. 추적 데이터도 로그만큼 널리 공유된다.

## 확인 문제

1. trace 와 span 의 관계를 설명하라.
2. W3C `traceparent` 헤더의 네 필드는 무엇인가?
3. trace 가 중간에 두 조각으로 갈라져 보인다. 가장 흔한 원인은?
4. head-based 샘플링과 tail-based 샘플링의 차이와 각각의 약점은?
5. span 의 자기 시간(self time)이 중요한 이유는?

### 풀이

1. trace 는 같은 trace ID 를 공유하는 span 들의 트리이고, span 은 그 안의 개별 작업 단위다. span 은 부모 span ID 로 트리를 이룬다.
2. version, trace-id, parent-id, trace-flags.
3. 서비스 경계(HTTP 클라이언트, 메시지 큐, 비동기 작업)에서 컨텍스트 헤더 전파가 누락됐다.
4. head 는 시작 시 확률로 정해 싸지만 드문 에러 trace 를 놓칠 수 있다. tail 은 끝난 뒤 골라 에러·느린 trace 를 남기지만 trace 를 모아 둘 자원이 필요하다.
5. 전체 시간은 자식 시간을 포함하므로 상위 span 은 늘 길어 보인다. 자기 시간이 실제로 그 구간이 소비한 시간이라 병목을 정확히 가리킨다.

## 더 읽을거리 (References)

- W3C, [Trace Context](https://www.w3.org/TR/trace-context/), W3C Recommendation.
- OpenTelemetry, [Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- B. Sigelman et al., [Dapper, a Large-Scale Distributed Systems Tracing Infrastructure](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/), Google Technical Report, 2010.
- OpenTelemetry, [Tracing API specification](https://opentelemetry.io/docs/specs/otel/trace/api/)
