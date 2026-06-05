---
layout: post
title: "Scouter · Pinpoint · New Relic · Datadog — 실시간 *TPS (Transactions Per Second)* 확인 방법과 4 도구 비교 (한국 시장 관점)"
date: 2026-06-05 19:30:00 +0900
categories: [observability, apm, monitoring]
tags: [apm, tps, scouter, pinpoint, newrelic, datadog, monitoring, performance, korea]
---

*"우리 서비스 지금 *몇 TPS*?"* 는 *백엔드 운영의 가장 기본 질문* 이다. **TPS (Transactions Per Second)** = *초당 처리 요청 수*. 이 한 숫자가 시스템의 *현재 부하 + 한계 + SLO 기준* 을 모두 담는다.

한국 환경에서 *TPS 를 측정하는 APM 도구* 는 크게 4 가지로 압축된다:

- **Scouter** — 한국 LG CNS / Saltlux 개발 오픈소스, 한국 SI 시장 점유
- **Pinpoint** — Naver 개발 오픈소스, 한국 + 글로벌
- **New Relic** — 미국 상용 SaaS
- **Datadog** — 미국 상용 SaaS (어제 글의 그 Datadog)

이 글은 *각자 TPS 확인 흐름* + *4 도구 직접 비교* + *2026 한국 시장 결정 가이드* 로 정리한다.

---

## TL;DR

| 도구 | TPS 확인 위치 | 라이센스 | 한국 점유율 | 적합 환경 |
|---|---|---|---|---|
| **Scouter** | XLog 화면 좌상단 *"TPS"* 라이브 차트 | 오픈소스 (Apache 2.0) | 금융권 / 공공기관 | 한국 SI / 보안 강한 환경 |
| **Pinpoint** | Inspector 의 *"Transactions"* 그래프 | 오픈소스 (Apache 2.0) | 네이버 계열 / 대기업 | MSA + 분산 트랜잭션 시각화 |
| **New Relic** | One UI → APM → Throughput (rpm 단위, 60 으로 나누면 TPS) | 유료 SaaS (Free tier 100GB/월) | 외국계 / 글로벌 | 무인 운영 가능한 SaaS 우선 |
| **Datadog** | Dashboard 의 *Service Overview* → Requests/sec | 유료 SaaS | 외국계 / 스타트업 | 통합 observability 필요 |

**한 줄 결론:** *Scouter = 무료 + 한국 패턴*, *Pinpoint = 무료 + MSA 시각화*, *New Relic = 유료 + 글로벌 표준*, *Datadog = 유료 + 통합성*.

---

## 1. TPS 의 정의 — *측정의 함정*

### 1.1 단순 정의

```
TPS = 초당 완료된 transaction 수
```

*transaction* 의 정의가 *도구마다 다름*:

- **Scouter / Pinpoint:** *Java agent 가 *Servlet 진입~응답 완료* 를 1 트랜잭션* (HTTP 요청 단위)
- **New Relic / Datadog:** *Web request* 또는 *background job* 단위 (커스텀 instrumentation 가능)

### 1.2 *유사 지표 혼동 주의*

| 지표 | 의미 | TPS 와 차이 |
|---|---|---|
| **RPS** (Requests/sec) | 들어온 요청 수 | TPS = *완료된* 요청, RPS = *들어온* 요청. 보통 같지만 *큐 대기* 시 RPS > TPS |
| **QPS** (Queries/sec) | DB query 수 | 1 transaction = N queries. TPS × N = QPS |
| **rpm** | *분당* 요청 (New Relic 의 기본 단위) | rpm / 60 = TPS |
| **Concurrent** | *동시* 요청 | TPS × avg_latency_sec = 평균 concurrent |

→ *Datadog 의 "1,000 rps"* 와 *New Relic 의 "60,000 rpm"* 은 *같은 의미*.

### 1.3 *왜 TPS 가 중요한가*

- *Capacity planning* — *이 호스트는 1,000 TPS 까지 OK* 같은 *upper bound*
- *SLO* — *p99 latency < 200ms at 500 TPS* 같은 *조건부 보장*
- *비용 (Datadog 등)* — *고객사 청구 = 호스트 수 × TPS 영향*
- *오토스케일링 트리거* — TPS 70% 임계 시 자동 확장

---

## 2. Scouter — *한국에서 가장 흔한 무료 APM*

### 2.1 정체

- **2014, LG CNS** 가 공개 (LGCNS Open Source). 현재 *Saltlux + 커뮤니티* 가 유지보수
- *국방·금융·공공* 에 *압도적* 점유. *외부 SaaS 금지* 환경의 *기본 옵션*
- 구조: Java agent → Scouter Collector → Scouter Viewer (Java Swing 또는 web)

### 2.2 설치 (3 단계)

```bash
# 1. Collector 서버
wget https://github.com/scouter-project/scouter/releases/download/v2.20.0/scouter-min-2.20.0.tar.gz
tar -xzf scouter-min-2.20.0.tar.gz
cd scouter/server
./startup.sh

# 2. 애플리케이션 (Spring Boot) 에 agent 부착
java -javaagent:./scouter/agent.java/scouter.agent.jar \
     -Dscouter.config=./scouter/agent.java/conf/scouter.conf \
     -jar app.jar

# 3. Viewer 다운로드 (별도)
# Scouter Viewer 는 *Java Swing UI* (legacy) 또는 *Scouter Paper* (web)
```

### 2.3 *TPS 확인 — Scouter Viewer*

**XLog** 화면을 열면:

```
┌─ XLog (트랜잭션 분포) ─────────────────────────┐
│  ↑ y축: 응답시간 (ms)                          │
│  ●●●●●  ← 각 점 = 1 트랜잭션                 │
│  ●●  ●●●                                      │
│  →  시간                                       │
└────────────────────────────────────────────────┘

좌상단 *대시보드*:
   TPS: 142.5         ← 실시간 (5초 평균)
   Active: 8          ← 현재 처리 중
   GC: 0.02s          ← GC 상태
   HeapUsed: 65%
```

XLog 의 *각 점이 1 transaction*. *밀도* 가 *TPS 의 직관*.

**메뉴:** Object → 좌측 Server → Service → XLog

### 2.4 *고급 — Counter 화면*

XLog 외에 *Counter* (메트릭 시계열) 도 있음:
- TPS / TPS_NORMAL / TPS_SLOW / TPS_ERROR 별 *분리* 가시화
- *Tag* 별 (URL, Service, Method) 그룹화 가능

**메뉴:** Object → Counter → tps_*

### 2.5 *장단점*

✅ 완전 무료, 한국어 문서, *XLog 가 한국 운영자들에게 *직관*
⚠️ UI 가 *Java Swing legacy* — 모던 SaaS 대비 *불편*
⚠️ 분산 트랜잭션 추적은 *제한적* (Pinpoint 가 강함)

---

## 3. Pinpoint — *네이버 발 분산 트랜잭션 시각화*

### 3.1 정체

- **2015, Naver** 가 GitHub 공개 (Apache 2.0)
- 분산 트랜잭션 추적 (Java Agent + HBase + Web UI)
- 모던 web UI (React 기반)
- *Naver / 카카오 / 라인* 등 *국내 대기업* 활용

### 3.2 *Pinpoint Web UI 의 TPS*

**Inspector** 메뉴 (애플리케이션 선택 후):

```
┌─ Server Map (분산 트랜잭션 시각화) ──────────────┐
│  [Client] → [Spring App] → [Redis]              │
│             ↘ [Postgres] ↗                       │
│                                                  │
└──────────────────────────────────────────────────┘

Inspector 패널:
  Transactions per Sec  ← *TPS 그래프*
   200 ┤  ╱╲
   100 ┤╱  ╲╱╲
     0 └───────────────
        14:00  14:30
```

**메뉴:** Application 선택 → Inspector → *Throughput (Transactions per Second)* 그래프

### 3.3 *Real-time / Heatmap*

Pinpoint 의 강점:

- **Real-time** 모드 — *지난 5 분* 실시간 갱신
- **Heatmap** — 트랜잭션 분포 (응답 시간 vs 시간) 색상 시각화

### 3.4 ServerMap — *MSA TPS 시각화의 정점*

```
[Browser] ────120 tps──→ [api-gateway] ──80 tps──→ [user-service]
                                       └─40 tps──→ [order-service]
                                                    └─40 tps──→ [postgres]
```

각 *서비스 간 화살표* 에 *TPS* 표시. *진짜 분산 시스템* 의 *트래픽 흐름* 한 눈에.

### 3.5 *장단점*

✅ ServerMap 의 *분산 트랜잭션 시각화* 압도적
✅ 무료 + 모던 React UI
⚠️ *HBase 운영 부담* (Pinpoint 가 HBase 의존)
⚠️ Agent 설정 비교적 복잡

---

## 4. New Relic — *SaaS APM 의 글로벌 표준*

### 4.1 정체

- **1999, San Francisco**. 가장 오래된 APM SaaS (정통)
- Java / Python / Node.js / Ruby / Go 모든 언어 agent
- 2020 부터 *New Relic One* 통합 플랫폼 (APM + Infra + Logs + Synthetics)
- *Free tier 100 GB/월 + 1 user free* (2026 기준)

### 4.2 *TPS 확인 — APM Throughput*

```
1. one.newrelic.com 로그인
2. APM & services → 너 application 선택
3. Summary 페이지 상단 차트:
   "Throughput (rpm)" — 분당 요청 수
   현재: 45,000 rpm = 750 TPS
4. Time picker — *Real-time* (Live) 또는 1m / 5m / ...
```

### 4.3 *NRQL — 커스텀 TPS 쿼리*

New Relic 의 *NRQL* (New Relic Query Language) 로 정확한 TPS:

```sql
SELECT rate(count(*), 1 second) FROM Transaction
WHERE appName = 'my-app'
SINCE 5 minutes ago
TIMESERIES
```

→ *진짜* TPS (초당 transaction count).

### 4.4 *Service Map + Distributed Tracing*

Pinpoint 의 ServerMap 과 비슷한 *Service Map*. 단 *Distributed Tracing* 이 더 깊음 (OpenTelemetry 호환).

### 4.5 *장단점*

✅ *24/7 SaaS 안정성* (1999~)
✅ NRQL 의 *유연한 query*
✅ 모든 언어 지원 (Java, Kotlin, Python, Node, Go, Ruby, .NET)
⚠️ 비용 (이전 글 참고 — *Per-host 대비 *Per-GB 인입 모델***)
⚠️ Free tier 100 GB/월 = 일 3 GB. *prod 한 서비스* 라도 *금방 초과*

---

## 5. Datadog — *어제 글의 그 도구* (TPS 측면)

### 5.1 TPS 확인 — Service Overview

```
1. app.datadoghq.com → APM → Services
2. 너 service 선택
3. Service Overview 페이지:
   "Requests" 차트 — req/s 단위
   - 평균: 320 req/s
   - p95: 380 req/s
4. Time picker — Past 5min / 15min / Live
```

### 5.2 *Watchdog* — 자동 anomaly 감지

Datadog 만의 강점: **Watchdog AI** 가 *평소 대비 TPS 급증/급감* 을 *자동 알림*.

```
"Throughput on service order-service dropped by 60%
 from 120 req/s to 48 req/s in the last 10 minutes"
```

평소 *baseline 학습 + outlier 알림*. 다른 도구는 *고정 임계* 만.

### 5.3 *DDQL 또는 Dashboard*

```
sum:trace.servlet.request.hits{service:order-service}.as_rate()
```

→ 커스텀 dashboard 에 위젯으로 추가.

---

## 6. 4 도구 *직접 비교* 매트릭스

| 항목 | Scouter | Pinpoint | New Relic | Datadog |
|---|---|---|---|---|
| **라이센스** | Apache 2.0 (무료) | Apache 2.0 (무료) | 유료 (Free tier 있음) | 유료 (Free tier 있음) |
| **호스팅** | 자체 (Collector + Viewer) | 자체 (HBase + Web) | SaaS | SaaS |
| **UI 모더니티** | ⚠️ Swing legacy + Paper | ⭐ React (모던) | ⭐⭐ 최신 React | ⭐⭐ 최신 React |
| **TPS 가시화** | XLog (점), Counter (시계열) | Inspector + ServerMap | APM Summary + NRQL | Service Overview + Watchdog |
| **실시간 정확도** | ⭐ (5s 평균) | ⭐⭐ (5s + Real-time mode) | ⭐⭐ (Live picker) | ⭐⭐ (Live) |
| **분산 트레이싱** | ⚠️ 약함 | ⭐⭐⭐ ServerMap | ⭐⭐⭐ Service Map + OT | ⭐⭐⭐ Service Map |
| **Anomaly 자동 감지** | ❌ | ⚠️ 제한적 | ⭐⭐ Applied Intelligence | ⭐⭐⭐ Watchdog |
| **언어 지원** | Java + .NET | Java + Python + Node | 모든 주요 언어 | 모든 주요 언어 |
| **운영 부담** | 보통 (Collector + Viewer) | 큼 (HBase 운영) | 0 (SaaS) | 0 (SaaS) |
| **한국 점유율** | 압도적 (금융·공공) | 매우 높음 (네이버계) | 보통 (외국계) | 빠르게 ↑ (스타트업) |
| **데이터 주권** | ✅ 자체 호스팅 | ✅ 자체 호스팅 | ❌ 외부 SaaS | ❌ 외부 SaaS |

---

## 7. *실전 시나리오* — 어느 도구 선택할까

### 시나리오 A: *금융권 / 공공기관*

데이터 외부 반출 *금지* 환경.

**→ Scouter** 또는 **Pinpoint**.
- Scouter: 작은 팀 + 단순 운영 우선
- Pinpoint: MSA + 분산 트랜잭션 시각화 필요

### 시나리오 B: *네이버 / 카카오 계열*

이미 *Pinpoint 의 *원조*  환경*.

**→ Pinpoint**. 사내 표준 + 운영 경험 풍부.

### 시나리오 C: *외국계 또는 SaaS 우선*

운영 인력 부족 + 글로벌 표준.

**→ New Relic** 또는 **Datadog**.
- New Relic: APM 만 깊게 → NRQL 강력
- Datadog: APM + Infra + Logs + Synthetics 통합

### 시나리오 D: *한국 스타트업 / 시리즈 A-B*

비용 부담 + 운영 인력 1~3 명.

**→ Pinpoint** (무료) 또는 **Datadog Free tier**:
- Pinpoint: 큰 트래픽 + 분산 시스템
- Datadog: 자체 운영 부담 회피 + Watchdog 가치

### 시나리오 E: *홈랩 / 사이드 프로젝트*

**→ Prometheus + Grafana + Tempo** (어제 글 참고).
- TPS = `rate(http_server_requests_seconds_count[1m])` PromQL
- *APM 전용 도구 안 써도* 무료 stack 으로 가능

내 K3s 환경엔 *Tempo + OpenTelemetry* 사용 중. TPS 측정엔 *Micrometer 의 Prometheus metric* 으로 충분.

---

## 8. *한국 시장 특화* 고려사항

### 8.1 *전자정부 프레임워크*

전자정부 프레임워크 환경엔 *Scouter 가 *기본 가정**. *Pinpoint* 도 호환되지만 *Scouter 가 더 검증*.

### 8.2 *금융권 규제 — ISMS-P*

데이터 *외부 반출 금지*. → *SaaS (New Relic, Datadog) 사용 불가*.
→ *Scouter / Pinpoint / 자체 Prometheus + Tempo* 만 옵션.

### 8.3 *대기업 SI 프로젝트*

*"고객사 환경에 설치"* 가 일반. → *자체 호스팅 가능한 Scouter / Pinpoint*. SaaS 는 *외부 SaaS 사용 승인* 필요.

### 8.4 *클라우드 네이티브 스타트업*

AWS / GCP 클라우드 기반. *Datadog / New Relic* 자연.

### 8.5 *카카오 / 네이버 출신 엔지니어 이직*

*Pinpoint 사용 경험* 이 *spec 가산점*. *Pinpoint 운영* 은 *시장 가치 ↑*.

---

## 9. *내 환경의 선택*

K3s 홈랩 + 30+ prod 서비스:

- **Tempo + OpenTelemetry + Micrometer Prometheus** 사용 중
- TPS = Grafana 대시보드의 `rate(http_server_requests_seconds_count[1m])`
- APM 전용 도구 안 씀

이유:
- 무료 stack 으로 *충분히 TPS 가시화*
- *학습 가치* (PromQL / LogQL / TraceQL)
- *데이터 주권* (외부 SaaS 없음)

만약 *Datadog 으로 갈* 시점이 온다면:
- 호스트 > 100 + SRE 인력 부족 + *Watchdog AI* 의 자동 분석 가치 필요

---

## 10. *실전 — 4 도구 각자 TPS 확인 명령 / 클릭 흐름*

### Scouter
```
1. Scouter Viewer 실행 (collector 연결)
2. 좌측 Object 트리 → Server → Service (예: my-app)
3. 우클릭 → XLog 또는 Counter
4. 좌상단 *대시보드 패널* 의 "TPS" 라이브 값
```

### Pinpoint
```
1. https://pinpoint.example.com 접속
2. 좌측 *Application List* → 너 app
3. Inspector 메뉴
4. "Transactions per Second" 그래프
5. (선택) ServerMap 으로 서비스 간 TPS
```

### New Relic
```
1. one.newrelic.com → APM & services
2. application 선택
3. Summary 페이지 → "Throughput (rpm)" 차트
4. rpm / 60 = TPS
5. NRQL: SELECT rate(count(*), 1 second) FROM Transaction
```

### Datadog
```
1. app.datadoghq.com → APM → Services
2. service 선택
3. Service Overview → "Requests (req/s)" 차트
4. Live 토글로 실시간
5. (자동) Watchdog 가 anomaly 알림
```

---

## 11. 결론 — *TPS = 시스템의 심전도*

TPS 는 *"우리 시스템 *심장박동*"*. *p99 latency, error rate, queue depth* 와 함께 *4 가지 핵심 지표 (USE / RED 모델)* 의 *R (Rate)*.

| 결정 변수 | 추천 도구 |
|---|---|
| 무료 + 한국 + 단순 | **Scouter** |
| 무료 + 분산 + 모던 UI | **Pinpoint** |
| 유료 + SaaS + APM 전용 | **New Relic** |
| 유료 + SaaS + 통합 observability | **Datadog** |
| 무료 + DIY + 학습 가치 | **Prometheus + Tempo** |

**한 줄 결론:** *Scouter 와 Pinpoint 는 한국이 *세계에 기여한 두 무료 APM*. *데이터 주권* 이 중요한 환경엔 *여전히 최선*. SaaS 환경엔 New Relic / Datadog 이 *0 운영 부담* 으로 *글로벌 표준*. 결정은 *데이터 주권 + 운영 인력 + 비용* 의 함수.*

---

## 참고

- *Scouter GitHub* — https://github.com/scouter-project/scouter
- *Pinpoint GitHub* — https://github.com/pinpoint-apm/pinpoint
- *New Relic Docs* — https://docs.newrelic.com
- *Datadog APM Docs* — https://docs.datadoghq.com/tracing/
- *RED Method* — Tom Wilkie (Weaveworks)
- *USE Method* — Brendan Gregg
- 관련 글:
  - [Datadog vs 무료 Observability Stack 손익분기점]({% post_url 2026-06-05-datadog-vs-free-observability-cost-time-analysis %})
  - [Java 21 Virtual Threads 실전 사례]({% post_url 2026-06-05-virtual-threads-real-cases-vs-kotlin-coroutines %})
  - [서비스 안정성과 고도화]({% post_url 2026-06-05-service-reliability-and-evolution-real-incidents %})
