---
layout: post
title: "Grafana 의 *3종 데이터소스* — Prometheus (메트릭) · Elasticsearch (로그) · Tempo (트레이스) 의 *제대로 된* 사용법"
date: 2026-05-29 04:10:00 +0900
categories: [reflection, devops, observability]
tags: [grafana, prometheus, elasticsearch, tempo, observability, metrics, logs, traces, correlation, sre]
---

홈랩 K3s 의 Grafana 에 *3종 데이터소스* 가 붙어있다. **Prometheus** (메트릭), **Elasticsearch** (로그), **Tempo** (트레이스). 셋 다 *3대 옵저버빌리티 기둥* 으로 유명한데, *Grafana 안에서 함께 쓸 때의 진짜 가치* 는 *각자가 답하는 질문* 이 다르고, *셋이 연결될 때* 1+1+1 > 5 가 된다는 거다.

이 글은 *어느 질문에 어느 데이터소스* 를 써야 하는지, *Grafana 의 Explore 와 대시보드를 어떻게 분업* 시키는지 정리한다.

> 본 글은 *Grafana 운영자 관점* 의 고찰. 각 도구의 *모든 기능* 이 아니라 *실제로 쓰는* 패턴 위주.

---

## TL;DR

| 데이터소스 | 답하는 질문 | Grafana 에서 주요 사용처 |
|---|---|---|
| **Prometheus** | "*무엇이* 이상한가?" — 수치·추세 | 대시보드 (Time series, Stat, Gauge) + Alerting |
| **Elasticsearch** | "*왜* 그런가?" — 사람이 읽는 메시지 | Explore (검색·필터) + Logs panel |
| **Tempo** | "*어떻게* 그렇게 됐나?" — 요청의 흐름 | Explore (Service Graph, Trace search) + Span Drill |

세 도구를 *각자 따로* 보면 *전체 그림* 안 보임 — *연결* 이 핵심.

---

## 0. 옵저버빌리티의 *3대 기둥* 빠르게

| 신호 | 단위 | 특징 |
|---|---|---|
| **Metrics** | 시간별 수치 (RPS, latency, CPU%) | *작고 빠름*, 시계열 DB 에 효율적 |
| **Logs** | 사람이 읽는 텍스트 메시지 | *크고 검색 가능*, 전문검색 엔진 필요 |
| **Traces** | 요청의 *시작-끝 흐름* (분산 systems 간) | *맥락이 풍부*, span 트리 구조 |

세 신호는 *독립적이 아니라 상호 보완*. 알람은 *메트릭* 으로 받고, 원인은 *로그* 에서 찾고, 흐름은 *트레이스* 로 확인한다.

---

## 1. Prometheus — 무엇이 *수치적* 으로 이상한가

### Grafana 에서의 역할: 대시보드 + Alerting

Prometheus 는 *Grafana 의 본진*. 거의 모든 대시보드의 *메인 데이터소스*. PromQL 한 줄로 시계열을 끌어와 그린다.

### *반드시* 만들어야 할 PromQL 표현 *4가지*

```promql
# 1. Request rate (Traffic)
sum by (service) (rate(http_requests_total[5m]))

# 2. Error rate (Errors)
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
  / sum by (service) (rate(http_requests_total[5m]))

# 3. p99 latency (Latency)
histogram_quantile(0.99,
  sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
)

# 4. Resource saturation (Saturation)
sum by (pod) (container_memory_working_set_bytes)
  / sum by (pod) (kube_pod_container_resource_limits{resource="memory"})
```

이 *4개 표현식* 이 SRE 의 *Golden Signals*. 서비스마다 이 4개만 깔끔하게 그려놓으면 *대시보드 1개* 로 모든 서비스 상태 파악.

### Grafana Alerting 의 진가

대시보드는 *사람이 봐야* 효과가 있다. Alerting 은 *사람이 안 봐도* 알람을 받게 한다. *진짜 가치* 는 alert 에 있음.

기본 alert rule 예시:
```yaml
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
    / sum(rate(http_requests_total[5m])) by (service)
    > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "{{ $labels.service }} error rate > 1% for 5min"
```

이걸 Slack/Telegram 으로 보내면 *대시보드 안 켜도* 장애 감지.

### 흔한 함정
- `rate()` 대신 `increase()` 사용 → 잘못된 추세
- *histogram_quantile* 의 `le` label sum 빼먹음 → 잘못된 percentile
- *cardinality 폭발* (label 너무 많이) → Prometheus 메모리 OOM

---

## 2. Elasticsearch — 왜 그런지 *사람이 읽는 메시지*

### Grafana 에서의 역할: Explore 중심

Elasticsearch 는 *대시보드* 보다 **Explore** 에서 더 자주 씀. *시간 + 자유 검색* 으로 원하는 로그를 즉시 찾는 도구.

### Grafana Explore + Elasticsearch 쿼리 패턴

```
# Lucene/KQL 스타일
log.level: "ERROR" AND kubernetes.namespace_name: "settlement-prod"
log.level: "ERROR" AND NOT message: "Connection reset"
message: "OutOfMemoryError" AND @timestamp:[now-1h TO now]
```

Grafana Explore 에서:
- 좌측 datasource = Elasticsearch
- Query type = Lucene
- 시간 범위 = 우상단에서 조정 (Last 1 hour / Custom)
- Hits 가 시계열 그래프 + 로그 stream 으로 함께 보임

### Kibana vs Grafana Explore — 어느 쪽?

| 작업 | Kibana 우위 | Grafana Explore 우위 |
|---|---|---|
| 자유 검색 (KQL) | ✅ — KQL native, autocomplete 강함 | △ — Lucene 만 |
| 대시보드 (로그 통계) | ✅ — Visualization 풍부 | △ — 단순 |
| **메트릭 + 로그 함께 보기** | ❌ — 다른 도구 | ✅ — 한 화면에 |
| **트레이스 + 로그 함께 보기** | ❌ | ✅ |

→ **순수 로그 검색은 Kibana, 메트릭·트레이스 와 함께 볼 땐 Grafana Explore**.

이 *역할 분담* 이 정리되면 두 도구가 *겹치지 않고* 시너지.

### Logs panel 활용

대시보드에 *작은 Logs 패널* 을 한두 개 두면:
- 특정 서비스 / 특정 에러 패턴의 *실시간 로그 stream*
- p99 latency 그래프 옆에 *그 시간대 에러 로그* 동시 노출
- 시야 줄어들지 않음

### 흔한 함정
- *모든 INFO 로그* Elasticsearch 로 보냄 → 비용 폭발
- *JSON 아닌 plain text* 로 보냄 → 필드별 검색 불가
- *index pattern* 정리 안 함 → 검색 느림

---

## 3. Tempo — *요청이 어떻게* 흘렀나

### Grafana 에서의 역할: Explore 의 Service Graph + Trace 검색

Tempo 는 *분산 트레이싱* 백엔드. 요청 하나가 *서비스 A → B → DB → C* 로 흐르는 전체 *span 트리* 를 저장.

### 진짜 봐야 할 *두 화면*

#### 1. **Service Graph** (Grafana Explore → Tempo → Service Graph)
- 모든 서비스의 *호출 관계* 그래프
- 각 화살표 위에 *RPS + p50/p95 latency + error rate*
- *어디서 호출이 막혔는지* 한눈에

#### 2. **Trace 검색**
- TraceID 직접 입력 (로그에서 복사해서)
- 또는 service name + duration > X 같은 필터
- 결과: span 트리 — *어느 service 가 *얼마나* 걸렸는지* 정확히

### *진짜 가치* — TraceID 로 *로그/메트릭 점프*

좋은 옵저버빌리티 셋업의 *마법* 은 **TraceID correlation**:

```
Kibana 에서 ERROR 로그 발견 → traceID 복사
→ Grafana Tempo Explore 에 붙여넣기
→ 그 traceID 의 전체 span 트리 보임
→ 어느 서비스가 *진짜 느렸는지* 한 번에 확인
```

이게 *분산 시스템 디버깅* 의 *교과서 흐름*. 이거 한 번 해보면 *왜 Tempo 가 있어야 하는지* 즉시 이해.

### 흔한 함정
- **계측 (instrumentation) 안 함** — OpenTelemetry SDK 안 붙이면 trace *생성 자체 안 됨*. Tempo 깔아도 무용지물
- **TraceID 가 로그에 없음** — Spring Boot 의 MDC 에 *traceId* 자동 추가 안 시킴 → 로그/트레이스 *연결 불가*
- **Sampling 100%** — 비용 폭발. *production 에선 1~10%* 가 표준

---

## 4. *셋이 연결될 때* — 진짜 가치

### 실전 장애 흐름

```
[ 1. Grafana 메인 대시보드 ]
   ↓ p99 latency 가 3초로 튐 (Prometheus)
   ↓ 알람 받음
   
[ 2. drill-down — 특정 endpoint /api/orders 만 느림 ]
   ↓ Prometheus 의 label 'route' 로 필터
   
[ 3. Grafana Explore — Elasticsearch ]
   ↓ kubernetes.pod_name: settlement-* AND message: "/api/orders"
   ↓ → "Slow query: findByUserId" 로그 발견
   ↓ → 로그에 traceID: abc1234 있음
   
[ 4. Grafana Explore — Tempo ]
   ↓ TraceID abc1234 입력
   ↓ → settlement → DB (2.8초 spent) → external API (0.1초)
   ↓ → 범인 = DB 쿼리
   
[ 5. 진단 ]
   ↓ N+1 쿼리 의심 → 코드 리뷰
   ↓ 새 commit + ArgoCD sync → 정상화
```

**총 소요 시간 5분.** 사용자는 *알아채지도 못함*. 세 도구가 *연결* 됐기 때문에 가능한 흐름.

### 연결을 만들어두는 *3가지 작업*

1. **로그에 traceID 자동 첨부** — Spring Boot: `logging.pattern.level=%5p [%X{traceId}]` 같은 MDC pattern
2. **Grafana datasource 의 "Derived field"** — Elasticsearch 데이터소스 설정에서 traceID 필드 → Tempo 데이터소스 링크 자동 생성
3. **Prometheus exemplar 활용** — 메트릭 그래프 위의 점 ⚫ 클릭 → 해당 시점의 trace 자동 점프

이 3개 설정만 해두면 *대시보드 → 로그 → 트레이스* 가 *클릭 두 번* 으로 연결.

---

## 5. *Explore vs 대시보드* — 분업 명확히

Grafana 의 두 모드:

| 모드 | 언제 | 데이터소스 주력 |
|---|---|---|
| **Dashboard** | *평소 모니터링·정기 회의* | Prometheus (메트릭 시계열) |
| **Explore** | *장애 대응·임시 검색* | Elasticsearch (로그), Tempo (트레이스) |

*대시보드만 만들고 Explore 안 씀* → 평소엔 잘 보이지만 *장애 때* 못 씀
*Explore 만 쓰고 대시보드 안 만듦* → *알람 못 받음*, 능동 감지 불가

둘 다 필요 — *Dashboard 는 능동 감지, Explore 는 수동 추적*.

---

## 6. 흔한 함정 *5종*

| 함정 | 결과 | 예방 |
|---|---|---|
| 세 데이터소스 *각자 따로 봄* | 연결 없음, 장애 대응 느림 | TraceID correlation 셋업 |
| Prometheus 만 잘 함 | "*어디서* 느린지" 안 보임 | Tempo + Elasticsearch 추가 |
| Elasticsearch 에 *모든 로그* 다 보냄 | 디스크 비용 폭발 | log level filtering + ILM |
| Tempo sampling 100% | 비용 폭발 | production 1~10% sampling |
| Alert rule *0 개* | 대시보드 있어도 *장애 모름* | Golden Signals 4개 alert *처음부터* |

---

## 7. 결론 — *세 데이터소스 = 세 질문*

### 한 줄 매핑
- **Prometheus** = "*무엇이* 이상한가?" → 알람·추세
- **Elasticsearch** = "*왜* 그런가?" → 메시지 검색
- **Tempo** = "*어떻게* 그렇게 됐나?" → 요청 흐름

### Grafana 설치 직후 *반드시 정해두기*

1. **Default datasource = Prometheus** — 대시보드 만들 때 자동 선택
2. **Explore 첫 화면 datasource = Elasticsearch** — 장애 대응 흐름 시작점
3. **TraceID correlation** — Elasticsearch derived field → Tempo 링크 자동 생성
4. **Alerting rule** — Golden Signals 4개 *처음부터*
5. **로그 sampling + 보관 정책** — 비용 한계 명확히

### 마지막 — *도구 = 질문이 명확한 사람의 답변기*

세 데이터소스가 다 있어도 *질문이 모호* 하면 *답 못 받음*. 운영자가 *"무엇이? 왜? 어떻게?"* 의 *3가지 질문* 을 명확히 가지고 들어가야 도구가 *답을 줌*.

질문 없이 대시보드만 켜는 건 *TV 켜놓고 잠드는 것* 과 같음. 도구는 *수동적* 이고, 운영자만 *능동적* 일 수 있다.

다음 글에선 *OpenTelemetry SDK + Spring Boot* 의 traceID correlation 셋업 — Spring Boot 의 MDC 와 OTel 의 propagator 가 어떻게 함께 동작하는지 정리할 예정.
