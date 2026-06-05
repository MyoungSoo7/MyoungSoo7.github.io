---
layout: post
title: "Datadog vs 무료 Observability Stack — 비용·시간 효율의 *손익분기점* 분석 (Prometheus·Grafana·Loki·Tempo·Alertmanager)"
date: 2026-06-05 17:20:00 +0900
categories: [observability, sre, economics]
tags: [datadog, prometheus, grafana, loki, tempo, alertmanager, monitoring, observability, cost-analysis, roi, break-even]
---

*Datadog 한 달 청구서 5,000 만원*. 스타트업 CTO 들이 *2026 년에도 자주 듣는* 충격. 그 5,000 만원의 *실제 가치* 는 얼마인가? *Prometheus + Grafana + Loki + Tempo 무료 stack* 으로 *같은 가시성* 을 얻는 데 *진짜 비용 (셋업 시간 + 운영 시간 + 클러스터 자원)* 은 얼마인가?

이 글은 **(1) Datadog 가격 구조 해부** + **(2) 무료 stack 매핑** + **(3) 손익분기점 계산** + **(4) 시나리오별 결정** 으로 정리한다. 이전 [IntelliJ vs Eclipse 손익분기점 글]({% post_url 2026-05-29-intellij-vs-eclipse-tool-vs-fundamentals-roi-break-even %}) 의 *observability 버전*.

---

## TL;DR — 손익분기점 한 줄

> **호스트 < 30 대 + 엔지니어 < 10 명 = 무료 stack 이 압도적 ROI**
> **호스트 > 300 대 + 엔지니어 > 50 명 = Datadog 이 압도적 ROI**
> **중간 구간 (30~300 호스트)** = *결정 변수가 *팀 시간 단가*** + *온콜 빈도*

| 측면 | Datadog | 무료 stack (Prometheus 외) |
|---|---|---|
| **초기 비용** | $0 (트라이얼) | $0 (오픈소스) |
| **월 운영 비용 (호스트당)** | $15~$70 (티어 + 통합 별) | 클러스터 자원 + *운영 시간* |
| **셋업 시간** | ~2~8 시간 (agent 설치) | ~3~10 일 (각 컴포넌트 + 통합) |
| **운영 시간 (월)** | ~5 시간 (대시보드 만들기) | ~10~30 시간 (튜닝, 패치, 장애) |
| **알람 룰 작성** | UI 클릭 | YAML / PromQL |
| **데이터 보존** | 기본 15 개월 (옵션) | 자체 관리 (Postgres / S3 / object) |
| **장애 대응** | 24/7 SaaS 가 책임 | 너 책임 (운영 중 깨지면 알람도 안 옴) |
| **벤더 lock-in** | 강함 | 없음 |

---

## 1. Datadog 의 가격 구조 — *각 product 별 독립 청구*

Datadog 은 *단일 제품 가격* 이 아닌 **9 개 product 의 모듈식 청구**:

### 1.1 핵심 라인

| Product | 단위 | 가격 (2026 기준) |
|---|---|---|
| **Infrastructure** | per host / 월 | $15 (Pro) / $23 (Enterprise) |
| **APM** (트레이싱) | per host / 월 | $31 / $36 |
| **Log Management — Ingest** | per GB | $0.10 |
| **Log Management — Retention** | per million events / 월 | $1.27 ~ $3.75 (보존 기간별) |
| **Synthetics — API** | per 10k tests / 월 | $5 |
| **Synthetics — Browser** | per 1k tests / 월 | $12 |
| **RUM (Real User Monitoring)** | per 1k sessions / 월 | $1.50 |
| **Security Monitoring** | per host / 월 | $19 |
| **Database Monitoring** | per database host / 월 | $70 |

### 1.2 *실제 청구 시나리오*

**스타트업 (호스트 20대, 엔지니어 15명):**
```
20 호스트 × $15 (Infra)         = $300
20 호스트 × $31 (APM)           = $620
1 TB 로그/월 × $100 (ingest)     = $100
+ retention 15일 = $50
+ Synthetics API 100k tests   = $50
─────────────────────────────────
월 청구: 약 $1,120 (~150 만원)
```

**중견 (호스트 100대, 엔지니어 80명):**
```
100 × $15 + 100 × $31           = $4,600
5 TB 로그/월                    = $500
DB monitoring × 10              = $700
Synthetics + RUM 등             = $300
─────────────────────────────────
월 청구: 약 $6,100 (~820 만원)
```

**대기업 (호스트 1000대):**
```
호스트 × ($15 + $31)             = $46,000
로그 50 TB                      = $5,000
DB / Security / Synthetics      = $5,000
─────────────────────────────────
월 청구: 약 $56,000 (~7,500 만원)
연 청구: 약 9 억원
```

→ **호스트 수와 *선형적*** 으로 증가. *클라우드 비용보다 빠르게* 폭증 가능.

### 1.3 *숨은 비용*

- **Custom metrics**: 추가 $0.05 per metric / 월. *100 metrics = $5/host*. 대규모 환경에선 *큰 부담*
- **Indexed log retention**: *15 일 기본*, 그 이상 추가 청구
- **Trace 100% 보존 → $$$**. 보통 *sampling 1~5%*
- **Cardinality 폭발**: *user_id label 같은 high-cardinality* 가 청구 폭증

---

## 2. 무료 Stack — *어느 도구가 Datadog 의 어느 product 대체*

### 2.1 매핑 매트릭스

| Datadog Product | 무료 대안 | 비고 |
|---|---|---|
| **Infrastructure metrics** | Prometheus + node_exporter | Pull 기반, scrape interval 15s |
| **APM (트레이싱)** | Tempo (Grafana) + OTLP | Jaeger 도 가능 |
| **Log Management** | Loki (Grafana) | "Prometheus for logs" |
| **Dashboards** | Grafana | Datadog dashboard 보다 *덜 화려*, 충분 |
| **Alerts** | Alertmanager + PrometheusRule | YAML 정의, Git-managed |
| **Synthetics (uptime)** | Blackbox Exporter / k6 | 또는 *uptime-kuma* |
| **RUM** | Sentry / OpenTelemetry web SDK | RUM 은 *완전 대체 어려움* |
| **Database monitoring** | postgres_exporter / mysqld_exporter | Postgres 의 pg_stat 노출 |
| **Security monitoring** | Falco + Wazuh | 별도 학습 곡선 |
| **Real-time profiling** | async-profiler + Pyroscope | JVM 한정엔 충분 |

### 2.2 통합된 *Grafana LGTM* 스택

```
L — Loki (logs)
G — Grafana (UI)
T — Tempo (traces)
M — Mimir (metrics, Prometheus 호환)
```

Grafana Labs 가 *통합 stack* 으로 push. *Datadog 의 *Logs + Traces + Metrics* 통합 UX 와 거의 동등*.

### 2.3 *내가 운영 중인 무료 stack*

```
- Prometheus (kube-prometheus-stack helm chart) — metrics
- Grafana — UI
- Loki + Promtail / Fluent-bit — logs
- Tempo + OpenTelemetry Collector — traces
- Alertmanager — alerts → Telegram bot
- Blackbox Exporter — uptime
- postgres-exporter / kafka-exporter / nginx-exporter — DB / Queue 별
- uptime-kuma — *추가* 외부 가시성
```

**클러스터 자원:** ~3 CPU + 4 GB RAM + 100 GB 디스크 (prod 30+ 서비스 모니터링).

---

## 3. *진짜* 비용 계산 — 호스트 수별

### 3.1 호스트 비용 모델

**Datadog 청구식:**
```
월 청구 = hosts × ($15 + $31)        # infra + APM
        + log_TB × $100               # 로그 ingest
        + retention_GB × $X            # 보존
        + custom_metrics × $0.05/100   # 사용자 정의
```

**무료 stack 비용식:**
```
월 비용 = 클러스터 자원 (CPU/RAM/디스크)
        + 셋업 시간 × 엔지니어 시간단가  # 일회성, 첫 해만
        + 운영 시간/월 × 시간단가         # 반복
        + 장애 시간 × 비즈니스 비용       # 가끔
```

### 3.2 *예시 계산* — 호스트 20 대 환경

**Datadog:**
- 월 $1,120 (위 시나리오) = *연 $13,440* = *약 1,790 만원*

**무료 stack:**
- 클러스터 자원: 3 CPU + 4GB + 100GB ≈ *연 $200* (AWS 기준) 또는 *0 원* (홈랩)
- 셋업 시간: 5 일 × 8 시간 = 40 시간 × 시간단가 $30 = *$1,200 일회성*
- 운영 시간 (월): 15 시간 × $30 = *월 $450* = *연 $5,400*
- *합산 첫 해: $200 + $1,200 + $5,400 = $6,800 (~ 900 만원)*
- *이후 매년: $200 + $5,400 = $5,600 (~ 750 만원)*

**연간 절약: $13,440 - $6,800 = $6,640 (~890 만원)**

호스트 20 대 환경에서 *무료 stack 이 우세*.

### 3.3 *예시 계산* — 호스트 1,000 대 환경

**Datadog:**
- 월 $56,000 = *연 $672,000* = *약 9 억원*

**무료 stack:**
- 클러스터 자원: 더 큼. 10 CPU + 32GB + 5TB ≈ *연 $5,000*
- 셋업: *50 일* 작업 (대규모는 *전담 SRE 팀* 필요)
- 운영 (월): 80 시간 = $2,400 → *연 $28,800*
- 첫 해 = $5,000 + $12,000 + $28,800 = *$45,800 (6,100 만원)*
- 이후 = $33,800/년 *(4,500 만원)*

**연간 절약: $672,000 - $45,800 = $626,200 (~84,000 만원 = *8 억원*)**

호스트 1,000 대 환경에서도 *무료 stack 이 절약은 큼*. 단:
- *Datadog 의 *24/7 SaaS 보장*, *즉각적 새 feature 추가* 는 무료 stack 이 *못 줌*
- *운영 인력의 *전문성*** 이 *진짜* 비용

---

## 4. *시간 효율* — 진짜 ROI 의 판단

### 4.1 Datadog 의 *시간 절감 영역*

✅ **알람 룰 빠른 설정** — UI 클릭으로 *5 분*. 무료 stack 은 YAML *30 분~수 시간*

✅ **대시보드** — *기본 템플릿* 풍부. AWS/Postgres/Redis 등 *자동 감지 + 대시보드*

✅ **APM 자동 instrumentation** — Java agent 하나로 *모든 메서드 trace*. 무료 stack 은 OpenTelemetry 직접 통합

✅ **장애 자동 분석** — Watchdog 이 *anomaly 자동 감지* + *root cause 추측*

✅ **upgrade 부담 0** — SaaS 가 알아서 패치

### 4.2 무료 stack 의 *시간 비용 영역*

⚠️ **셋업** — 5~10 일 (각 컴포넌트 + Helm chart + 통합)

⚠️ **튜닝** — Prometheus retention, Loki chunk size 등 *직접 조정*

⚠️ **알람 룰 작성** — PromQL 학습 필요

⚠️ **패치** — Prometheus 새 버전, Grafana 업그레이드 *직접*

⚠️ ***monitoring 의 monitoring*** — Prometheus 자체가 죽으면 알람도 안 옴. *meta-monitoring* 필요

⚠️ **장애 시 모든 책임 너**

### 4.3 *손익분기 시간*

```
Datadog 의 *연 비용 차액* (vs 무료) = $7,000 (호스트 20대 기준)
무료 stack 의 *추가 운영 시간 / 년* = 100 시간 (위 계산)

→ 시간단가 $70 미만 면 *무료 stack 이 ROI 양수*
→ 시간단가 $70 초과 면 *Datadog 이 ROI 양수*
```

**한국 백엔드 / SRE 시간단가 추정:**
- 주니어 (3년 미만): ~$15/h
- 미드 (3-7년): ~$30/h
- 시니어 (7년+): ~$50/h
- 외국 stake 회사: ~$100+/h

→ **국내 대다수 환경에선 무료 stack 이 ROI 양수**. 단 *시니어 SRE 가 *비싸진 시간* 을 *Datadog 으로 절약* 할 수 있다면* Datadog 도 합리.

---

## 5. *경영학적* 분석 — 결정 변수

### 5.1 호스트 수 비례 비용 — Datadog 의 *치명적 패턴*

```
호스트 수 증가 → Datadog 청구 *선형* 증가
무료 stack → 자원만 *완만하게* 증가

cross-over point (손익분기):
  ~30-50 호스트 부근
```

**소규모 (< 30 호스트)** → *무료 stack 압도*
**중간 (30-300)** → *결정 변수* (시간단가, 운영 능력)
**대규모 (> 300)** → *진영 분리*:
  - Datadog 의 *24/7 보장* 가치 큼
  - 그러나 비용도 *매월 1000 만원+* — *전담 SRE 팀* 가능 비용

### 5.2 *팀 규모 vs 도구 비용*

```
Datadog 비용 = 호스트 수 × $45 / 월
무료 stack 운영 = SRE 1 명 풀타임 (대규모 환경)

→ 호스트 500 대 = 월 $22,500 = *SRE 1 명 풀타임 비용*
```

대규모 환경에선:
- *Datadog 비용 = SRE 1 명 비용* 인 시점에 **선택지**
- *SRE 가 *없으면* Datadog*
- *SRE 가 *있으면 *Datadog 절약분으로 다른 사람 채용**

### 5.3 *위험 가중치*

| 위험 요인 | Datadog | 무료 stack |
|---|---|---|
| 도구 자체 다운 | SaaS 가 책임 | 너 책임 |
| 데이터 손실 | 거의 없음 (SaaS) | 자체 백업 필요 |
| 벤더 lock-in | 강함 (마이그레이션 어려움) | 0 |
| 가격 인상 | 가능 (2024 inflation 30%) | 0 |
| 보안 / 데이터 거버넌스 | 외부 SaaS | 자체 운영 |

*보안 민감 산업* (금융, 공공, 의료) 은 *Datadog 의 *외부 SaaS** 가 *허용 안 됨* — *무료 stack 만 가능*.

### 5.4 *Hidden ROI* — 가격에 안 보이는 가치

Datadog 의 *진짜 가치* (가격표 안 나옴):
- *Watchdog* 의 자동 anomaly detection
- *Service Map* 자동 생성
- *Notebooks* 협업
- *Incidents* workflow
- *SLO* dashboard
- *Audit log* (보안 / 컴플라이언스)

무료 stack 의 *Hidden 가치*:
- *벤더 lock-in 회피*
- *팀의 *PromQL / observability 깊이* 학습*
- *오픈소스 기여 가능*
- *자체 호스팅 = *데이터 주권**

---

## 6. *결정 가이드* — 시나리오별

### 시나리오 A: 1 인 개발자 / 사이드 프로젝트

**무료 stack 100%**. 호스트 1~5 대. Datadog 가격 부담. Prometheus + Grafana 가 충분.

### 시나리오 B: 시드 ~ 시리즈 A 스타트업 (호스트 5~30)

**무료 stack 우선** + *Datadog free tier 사용* (5 hosts 한정 무료):
- Datadog 의 *Watchdog / RUM* 만 무료 tier 로 *부분 사용*
- 본격 모니터링은 Prometheus + Grafana

### 시나리오 C: 시리즈 B/C (호스트 30~300)

**결정 변수:**
- SRE 시간단가 < $50/h → *무료 stack*
- SRE 시간단가 ≥ $50/h → *Datadog 검토* (특히 APM)
- *24/7 oncall 부담* → Datadog 의 *Watchdog 자동 분석* 가치

대다수 한국 스타트업은 *무료 stack* 이 합리.

### 시나리오 D: 대기업 / 글로벌 (호스트 300+)

**Datadog 이 *기본***, 단 *고비용* 통제:
- *비용 가시화* — DD Cost Insights 활용
- *high-cardinality 차단* — user_id 같은 label 회피
- *Sampling 비율 조정* (APM trace 1~5%)

또는 *하이브리드*:
- *Critical 시스템 (결제, 인증)* — Datadog
- *비핵심 (배치, 분석)* — 무료 stack

### 시나리오 E: 금융 / 공공 / 의료

**무료 stack 필수** — 데이터 외부 SaaS 금지.

---

## 7. *내 환경의 결정* — K3s 홈랩 + 30+ 서비스

내 환경:
- 호스트: 5 노드 (K3s) + 곧 R730xd 추가
- prod 서비스: 30+ namespace
- 트래픽: 작음 (대부분 *학습 + 작은 trial prod*)
- 비용 부담: *개인 비용*

**결정:** **무료 stack 100%**.

**현재 운영:**
```
Prometheus (kube-prometheus-stack)
  ├─ node-exporter (모든 노드)
  ├─ kube-state-metrics
  └─ postgres-exporter / kafka-exporter

Grafana
  ├─ Kubernetes 클러스터 대시보드
  ├─ JVM 대시보드 (Micrometer Prometheus)
  ├─ Postgres 대시보드
  └─ 비즈니스 KPI (settlement / lemuel-xr)

Loki + Fluent-bit
  ├─ 모든 pod 로그 수집
  └─ Grafana Explore 에서 검색

Tempo + OpenTelemetry Collector
  └─ Spring Boot 의 traces (Micrometer tracing bridge)

Alertmanager
  └─ → Telegram bot (lemuel CPU 알람 등 실제 운영)
```

**연 비용 추정:**
- 인프라: $0 (홈랩)
- 시간: ~80 시간/년 (튜닝, 패치) × $0 (개인 시간) = $0
- 학습 가치: *높음* — 직접 PromQL / LogQL 등 학습

→ **무료 stack 의 ROI = 무한대** (홈랩 환경).

회사 환경이면 *호스트 30 대 미만 + 시간단가 < $50/h* 시 *무료 stack* 권장.

---

## 8. 흔한 함정 5 가지

### ❌ 함정 1: *Datadog 가 *알아서 다 해준다* 는 환상*

비용 *통제 안 하면* 매월 *예상의 3 배 청구*. *Custom metrics, high-cardinality, retention* 폭증.

### ❌ 함정 2: *무료 stack = *공짜* 라는 착각*

*시간 비용* 이 진짜 비용. 5 일 셋업 + 월 15 시간 운영 = *시니어 시간단가에 따라 큰 금액*.

### ❌ 함정 3: *monitoring 의 monitoring* 부재

Prometheus 자체가 죽으면 *알람도 안 옴*. *외부 uptime 도구 (Pingdom / uptime-kuma)* 로 *Prometheus 자체 모니터* 필요.

### ❌ 함정 4: *Cardinality 폭발*

```
http_requests_total{path="/api/users/12345"}
http_requests_total{path="/api/users/12346"}
...
```

*path 에 user_id 들어가면* metric 수 *폭증*. Datadog 청구 폭증 / Prometheus 메모리 폭증. **path label 은 *route pattern* 만**.

### ❌ 함정 5: *vendor lock-in 후 마이그레이션 비용*

Datadog → 무료 stack 마이그레이션 = *모든 대시보드 / 알람 / runbook 재작성*. *6 개월~1 년* 작업. *처음 선택* 이 *진짜 lock-in*.

---

## 9. 결론 — *경영 의사결정 변수 5 가지*

| 변수 | 무료 stack 유리 | Datadog 유리 |
|---|---|---|
| 호스트 수 | < 50 | > 300 |
| 엔지니어 시간단가 | < $50/h | ≥ $50/h |
| 산업 규제 (금융/공공) | ✅ | ❌ 금지 |
| 운영 인력 보유 | ✅ | 없으면 Datadog |
| 학습 가치 | 추구 | 결과 우선 |

**2026 년 5 월 추천:**
- **소규모 스타트업 / 사이드 프로젝트** → **무료 stack** (Prometheus + Grafana + Loki + Tempo)
- **중견 30~300 호스트** → *시간단가 기반 결정*. 둘 다 가능
- **대기업 300+ 호스트** → *Datadog* 또는 *전담 SRE + 무료 stack*
- **금융 / 공공 / 의료** → *무료 stack 만 가능*

**한 줄 결론:** *Datadog 의 5,000 만원 청구서는 *호스트 1000 대 + SRE 부재* 의 *합리적 가격* 이지만, *호스트 30 대 환경에선 *시간 단가 무시한 사치**. *경영의 핵심* 은 *호스트 수 × 시간단가* 의 *교차점* 을 *측정* 하고 결정하는 것.*

---

## 참고

- *Distributed Systems Observability* — Cindy Sridharan (2018)
- *Observability Engineering* — Charity Majors, Liz Fong-Jones, George Miranda (2022)
- [Datadog Pricing](https://www.datadoghq.com/pricing/)
- [Grafana LGTM Stack](https://grafana.com/oss/)
- *Prometheus: Up & Running* — Brian Brazil (2018)
- 관련 글:
  - [IntelliJ vs Eclipse 손익분기점]({% post_url 2026-05-29-intellij-vs-eclipse-tool-vs-fundamentals-roi-break-even %})
  - [Java vs Kotlin ROI]({% post_url 2026-05-29-java-vs-kotlin-roi-break-even-claude-code-ai-coding %})
  - [Harness Engineering ④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
