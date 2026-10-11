---
layout: post
title: "[SE100 #085] 관측 가능성 — 로그·메트릭·트레이스"
date: 2026-10-11 17:08:53 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, observability, opentelemetry, cardinality, telemetry]
---

소프트웨어 공학 100 주제 시리즈의 85번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

모니터링이 "미리 알고 있는 질문" 에 답하는 장치라면, 관측 가능성은 **미리 예상하지 못한 질문**을 코드 수정·재배포 없이 던질 수 있는 시스템의 성질이다. 로그·메트릭·트레이스는 그 재료이고, 실제 가치는 셋을 **같은 식별자로 엮는 설계**와 **비용(카디널리티) 통제**에서 나온다.

## 왜 필요한가

장애 대응에서 가장 비싼 시간은 "무엇이 이상한지는 아는데 왜인지 모르는" 구간이다. 이 구간이 길어지는 전형적인 원인은 다음과 같다.

- 메트릭 대시보드에서 오류율 상승은 보이지만, 어떤 사용자·어떤 경로·어떤 버전에서인지 나눠 볼 차원이 없다.
- 로그는 많지만 서비스마다 형식이 달라 한 요청의 흔적을 이어 붙일 수 없다.
- 트레이스는 1% 만 샘플링돼서 정작 실패한 요청의 트레이스가 없다.
- 차원을 늘리려고 메트릭에 `user_id` 라벨을 붙였다가 모니터링 시스템이 먼저 쓰러진다.

기본 도구는 CS300 [모니터링 — Prometheus·Grafana]({% post_url 2026-10-10-cs300-232-monitoring-prometheus-grafana %}), [로그 수집과 분석]({% post_url 2026-10-10-cs300-233-log-collection-and-analysis %}), [분산 추적]({% post_url 2026-10-10-cs300-234-distributed-tracing %}) 에서 다뤘다. 이 글은 그 도구들을 **하나의 설계**로 묶는 판단을 다룬다.

## 핵심 개념

### 모니터링과 관측 가능성

[OpenTelemetry 의 Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) 는 관측 가능성을 "내부 동작을 몰라도 시스템에 질문을 던져 바깥에서 이해할 수 있게 하는 것" 으로 설명하고, 그 목적을 새로운 문제, 즉 "알지 못하는 미지(unknown unknowns)" 를 다루고 "왜 이런 일이 일어나는가" 에 답하는 데 둔다. 그리고 애플리케이션이 **적절히 계측되었다**는 것을 "문제를 해결하려고 계측을 더 추가할 필요가 없는 상태" 로 정의한다.

| 구분 | 모니터링 | 관측 가능성 |
|---|---|---|
| 질문 | 사전에 정한 질문 ("오류율이 1% 를 넘었나?") | 사후에 떠오른 질문 ("이 오류는 왜 iOS 17 + 쿠폰 사용 주문에만?") |
| 산출물 | 대시보드, 경보 | 임의 차원으로 자르고 이어 붙일 수 있는 원시 신호 |
| 실패 모드 | 몰랐던 고장은 안 보임 | 데이터는 있지만 비용 폭증 |

둘은 대립하지 않는다. 경보는 여전히 모니터링(특히 SLO 기반, SE100 #084)이 담당하고, 관측 가능성은 경보 이후의 조사 시간을 줄인다.

### 신호들

[OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/) 문서는 현재 지원 신호로 트레이스, 메트릭, 로그, 배기지(baggage)를 들고, 이벤트와 프로파일을 개발·제안 단계로 둔다.

| 신호 | 본질 | 강점 | 약점 |
|---|---|---|---|
| 메트릭 | 시간 구간에 걸친 수치 집계 | 싸고 빠름, 경보·추세에 적합 | 집계 순간 개별 사건의 맥락이 사라짐 |
| 로그 | 타임스탬프가 붙은 개별 사건 기록 | 풍부한 맥락, 어디서나 존재 | 양이 많고 형식이 제각각 |
| 트레이스 | 한 요청이 여러 구성요소를 거친 경로(스팬의 트리) | 분산 시스템의 인과·지연 분해 | 계측 비용, 샘플링 필요 |
| 배기지 | 신호들 사이로 전달되는 문맥 키-값 | 하류 서비스에서도 테넌트·실험군 등 식별 | 모든 요청에 실려 전파되므로 크기·민감정보 주의 |

### 셋을 엮는 열쇠: 컨텍스트 전파

신호가 따로 놀면 "기둥 셋" 이 아니라 "사일로 셋" 이다. 엮는 장치는 표준화된 식별자다. [W3C Trace Context](https://www.w3.org/TR/trace-context/) 권고안은 `traceparent` 헤더 형식을 정한다.

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             │  │                                │                │
           버전  trace-id (16바이트)            parent-id (8바이트)  플래그(sampled)
```

[OpenTelemetry 로그 데이터 모델](https://opentelemetry.io/docs/concepts/signals/logs/)은 로그 레코드에 `TraceId`, `SpanId` 필드를 두어, 로그를 그 순간의 트레이스와 자동으로 연결한다. 메트릭 쪽에는 [exemplar](https://opentelemetry.io/docs/specs/otel/metrics/data-model/) 가 있다. OpenTelemetry 메트릭 데이터 모델은 exemplar 를 메트릭 이벤트에 `trace_id`·`span_id` 같은 문맥을 연결하는 기록값으로 정의하며, 트레이스와 메트릭을 잇는 것을 용도로 든다. 지연 히스토그램에서 "느린 요청 하나" 의 트레이스로 바로 뛰어갈 수 있다.

```
 경보(메트릭: p99 지연 상승) ──exemplar──▶ 트레이스(어느 스팬이 느린가)
                                              │ trace_id
                                              ▼
                                   로그(그 스팬에서 무슨 일이 있었나)
```

### 카디널리티: 관측 가능성의 비용 함수

메트릭에서 라벨 값의 조합 하나하나가 별도의 시계열이 된다. [Prometheus 명명 가이드](https://prometheus.io/docs/practices/naming/)는 사용자 ID, 이메일처럼 값의 종류가 무한한 차원을 라벨로 쓰지 말라고 경고한다. [계측 가이드](https://prometheus.io/docs/practices/instrumentation/)는 대부분의 메트릭은 라벨이 없어야 하고, 메트릭의 카디널리티를 10 미만으로 유지하며, 100 을 넘거나 그럴 가능성이 있으면 대안을 찾으라는 일반 지침을 준다. 같은 문서의 예로, node_exporter 의 파일시스템 메트릭은 노드 1만 대에서 약 10만 시계열로 감당할 만하지만, 여기에 사용자별 쿼터를 더해 사용자 1만 명이면 수천만 단위가 되어 감당할 수 없다.

해법은 차원을 **신호별로 나누는 것**이다.

| 차원 | 메트릭 라벨 | 트레이스 속성 / 구조화 로그 필드 |
|---|---|---|
| HTTP 메서드, 라우트 템플릿(`/orders/{id}`), 상태코드 클래스 | 예 | 예 |
| 서비스 버전, 리전 | 예 | 예 |
| 사용자 ID, 주문 ID, 실제 URL 경로 | **아니오** | 예 |
| 오류 메시지 원문 | 아니오 | 예 |

라우트를 템플릿으로 기록하는 이유도 같다. [HTTP 시맨틱 컨벤션](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/)의 `http.server.request.duration` 메트릭은 `http.request.method`, `http.response.status_code`, `http.route` 같은 속성을 쓴다. 이름을 표준에 맞추면 도구를 바꿔도 대시보드와 쿼리를 다시 짜지 않아도 된다.

### 집계 가능한 분포: 히스토그램과 서머리

[Prometheus 히스토그램 문서](https://prometheus.io/docs/practices/histograms/)는 서머리(summary)가 미리 계산한 분위수는 **집계할 수 없다**고 강조한다. 복제본 10개의 p90 을 평균해도 서비스 전체의 p90 이 아니다. 여러 인스턴스를 합쳐 분위수를 보려면 버킷 카운트를 내보내는 히스토그램을 쓴다.

### 샘플링

[OpenTelemetry 샘플링 문서](https://opentelemetry.io/docs/concepts/sampling/)는 두 방식을 구분한다. **헤드 샘플링**은 트레이스 시작 시점에 결정해 효율적이지만, 트레이스 전체를 보고 결정할 수 없어 "오류가 난 트레이스는 모두 남긴다" 를 보장할 수 없다. **테일 샘플링**은 트레이스의 스팬 대부분을 본 뒤 결정해 오류·고지연 트레이스를 골라 남길 수 있지만 구현과 운영이 어렵다.

### 무엇을 볼지 정하는 방법론

- [Google SRE 의 네 가지 황금 신호](https://sre.google/sre-book/monitoring-distributed-systems/): 사용자 대면 시스템에서 지표를 네 개만 고를 수 있다면 지연, 트래픽, 오류, 포화도.
- [Brendan Gregg 의 USE 방법](https://www.brendangregg.com/usemethod.html): 모든 **자원**에 대해 사용률(utilization), 포화도(saturation), 오류(errors)를 확인한다.

황금 신호는 서비스(요청) 관점, USE 는 자원 관점이다. 서비스 지표가 이상하면 USE 로 자원을 훑는 식으로 함께 쓴다.

## 실무 적용

### 구조화 로그에 트레이스 문맥 싣기

```python
import json, logging, time
from opentelemetry import trace

class JsonFormatter(logging.Formatter):
    def format(self, record):
        ctx = trace.get_current_span().get_span_context()
        doc = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "service.name": "checkout",
            "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else None,
            "span_id": format(ctx.span_id, "016x") if ctx.is_valid else None,
        }
        doc.update(getattr(record, "fields", {}))   # 고카디널리티 값은 여기로
        return json.dumps(doc, ensure_ascii=False)

log = logging.getLogger("checkout")
h = logging.StreamHandler(); h.setFormatter(JsonFormatter()); log.addHandler(h)
log.warning("쿠폰 적용 실패", extra={"fields": {"order_id": "o-123", "coupon": "FALL10"}})
```

`order_id` 같은 고카디널리티 값은 로그 필드(또는 스팬 속성)로 보내고, 메트릭에는 `route`, `status_class` 정도만 남긴다.

### 계측 설계 체크리스트

- [ ] 모든 서비스가 `traceparent` 를 받고 넘기는가 (메시지 큐 헤더 포함)
- [ ] 로그가 JSON 등 구조화 형식이며 `trace_id` 를 포함하는가
- [ ] 지연은 히스토그램으로, 라우트는 템플릿으로 기록하는가
- [ ] 메트릭 라벨에 사용자·주문 ID, 원본 URL 이 없는가 (CI 에서 검사)
- [ ] 오류·고지연 트레이스가 샘플링에서 살아남는가
- [ ] 배포 버전이 모든 신호에 리소스 속성으로 붙는가 (배포 전후 비교)
- [ ] 로그·스팬 속성에 비밀번호·토큰·개인정보가 들어가지 않는가

## 흔한 오해와 함정

- **"세 기둥을 다 모으면 관측 가능하다"** — 서로 연결되지 않은 세 저장소는 조사 시간을 줄이지 못한다. 핵심은 공통 식별자와 공통 속성 이름이다.
- **"많이 모을수록 좋다"** — 카디널리티와 보존 비용은 선형 이상으로 늘어난다. 질문이 없는 데이터는 비용이다.
- **평균 지연 대시보드** — 평균은 꼬리를 숨긴다. 분포(히스토그램)로 보고, 분위수는 집계 가능한 방식으로 계산한다.
- **헤드 샘플링만으로 충분하다는 가정** — 드문 오류일수록 샘플에서 빠진다.
- **로그에 민감정보** — 관측 데이터는 접근 범위가 넓어 유출 경로가 되기 쉽다. 수집 단계에서 마스킹한다.

## 확인 문제

1. OpenTelemetry 문서가 말하는 "적절히 계측된" 애플리케이션의 조건은?
2. 요청 지연 메트릭에 `user_id` 라벨을 붙이면 어떤 문제가 생기며, 그 정보는 어디에 두어야 하는가?
3. 인스턴스 5개의 서머리 p99 를 평균한 값이 서비스 p99 가 아닌 이유는?
4. "오류가 난 트레이스는 반드시 남긴다" 를 보장하려면 어떤 샘플링이 필요한가? 그 대가는?

### 풀이

1. 문제를 해결하기 위해 계측을 더 추가할 필요가 없을 만큼 필요한 정보가 이미 신호로 나오고 있는 상태.
2. 사용자 수만큼 시계열이 늘어나 저장·메모리·쿼리 비용이 폭증한다(카디널리티 폭발). 사용자 ID 는 스팬 속성이나 구조화 로그 필드에 둔다.
3. 분위수는 선형이 아니라 평균으로 합칠 수 없다. 인스턴스마다 트래픽 양과 분포가 다르기 때문이다. 버킷 카운트를 합산하는 히스토그램으로 계산해야 한다.
4. 트레이스 전체를 보고 결정하는 테일 샘플링. 스팬을 결정 시점까지 버퍼링해야 해서 구현·운영이 복잡하고 자원이 든다.

## 더 읽을거리 (References)

- OpenTelemetry, [Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/), [Signals](https://opentelemetry.io/docs/concepts/signals/), [Logs](https://opentelemetry.io/docs/concepts/signals/logs/), [Sampling](https://opentelemetry.io/docs/concepts/sampling/)
- OpenTelemetry, [Metrics data model (Exemplars)](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)
- OpenTelemetry, [Semantic conventions for HTTP metrics](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/)
- W3C, [Trace Context](https://www.w3.org/TR/trace-context/)
- Prometheus, [Metric and label naming](https://prometheus.io/docs/practices/naming/), [Instrumentation](https://prometheus.io/docs/practices/instrumentation/), [Histograms and summaries](https://prometheus.io/docs/practices/histograms/)
- Google, [Site Reliability Engineering, Chapter 6 — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- Brendan Gregg, [The USE Method](https://www.brendangregg.com/usemethod.html)
