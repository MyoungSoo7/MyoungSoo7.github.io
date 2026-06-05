---
layout: post
title: "모니터링 5대 도구 비교 — Datadog · Grafana · Prometheus · 제니퍼 · Netdata *언제 어느 것*"
date: 2026-06-05 17:00:00 +0900
categories: [reflection, devops, observability]
tags: [monitoring, datadog, grafana, prometheus, jennifer, netdata, apm, observability, sre]
---

*"모니터링 뭐 써요?"* 의 답이 *"우리는 X 써요"* 한 단어로 끝나면 *위험 신호*. 실은 *5~10 개 도구가 *서로 다른 층* 에서 굴러가야* 한다. 그리고 *어느 도구가 어느 층에 맞는지* 결정이 *비용·운영 부담·SLA 의 80%* 를 좌우한다.

본 글은 *5 대 모니터링 도구* — **Datadog**, **Grafana**, **Prometheus**, **제니퍼 (Jennifer)**, **Netdata** — 를 *동일한 잣대* 로 분해하고, *언제 어느 것을 써야 하는지* 를 정리한다.

> 본 글은 *2026 년 시점, 한국 백엔드 엔지니어 관점*. 가격은 시점에 따라 변동.

---

## TL;DR

| 도구 | 주 영역 | 라이선스 | 적합 규모 | 한국 특화 |
|---|---|---|---|---|
| **Datadog** | All-in-one SaaS APM + Metrics + Logs + Traces | 상용 (호스트당 ~$15+/월) | 중대형 클라우드 네이티브 | △ (한국 사례 적음) |
| **Grafana** | 시각화 / 알람 / Unified UI | 오픈소스 (Cloud 유료) | 모든 규모 | △ |
| **Prometheus** | 메트릭 시계열 DB + 알람 룰 | 오픈소스 | 모든 규모 (K8s 표준) | △ |
| **제니퍼** | Java APM (트랜잭션 추적) | 상용 (라이선스) | 한국 엔터프라이즈, Java/WAS 중심 | ⭐ 강함 |
| **Netdata** | 호스트 실시간 메트릭 (per-second) | 오픈소스 + Cloud | 소~중규모, 홈랩 | △ |

| 차원 | Datadog | Grafana | Prometheus | 제니퍼 | Netdata |
|---|---|---|---|---|---|
| **메트릭** | ⭐⭐⭐ | △ (data source) | ⭐⭐⭐ | △ (자체 메트릭) | ⭐⭐⭐ (host 위주) |
| **로그** | ⭐⭐⭐ | △ (Loki 등 통합) | ❌ | △ | ❌ |
| **트레이스** | ⭐⭐⭐ | △ (Tempo 통합) | △ (OpenMetrics 변환) | ⭐⭐⭐ (Java 강점) | ❌ |
| **APM** | ⭐⭐⭐ | ❌ | ❌ | ⭐⭐⭐ (Java) | ❌ |
| **알람** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ (Alertmanager) | ⭐⭐ | ⭐⭐ |
| **설치/운영** | 쉬움 (SaaS) | 중간 | 중간 | 중간 (라이선스) | *매우 쉬움* |
| **비용** | 💰💰💰 | 💰 (self-host) | 💰 (self-host) | 💰💰 | 💰 |

---

## 0. *5 도구의 *근본 포지션*

먼저 *각 도구가 *어느 층* 의 도구인지* 명확히:

```
┌─────────────────────────────────────────────────────────┐
│                  사용자 시각 — 비즈니스 KPI               │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ Visualization / Alert    [ Grafana ]    [ Datadog UI ]   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ APM (애플리케이션 분석)  [ Datadog APM ]  [ 제니퍼 ]      │
│ - 트랜잭션 추적                                          │
│ - 메서드 단위 프로파일                                   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ 데이터 수집 / 저장                                        │
│   메트릭: [ Prometheus ] [ Datadog ] [ Netdata ]         │
│   로그:   [ Datadog ] (Loki / ELK 별도)                  │
│   트레이스: [ Datadog ] [ 제니퍼 ] (Tempo 별도)           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ 시스템 / 호스트 메트릭                                    │
│   [ Netdata ]  [ node-exporter→Prometheus ]              │
│   [ Datadog Agent ]                                      │
└──────────────────────────────────────────────────────────┘
```

→ *각 도구가 *경쟁* 하는 듯 보이지만 실제론 *서로 다른 층*. 그래서 *조합* 이 흔하다 (예: Prometheus + Grafana + Datadog APM).

---

## 1. Datadog — *All-in-One SaaS 의 정점*

### 본질
*돈으로 시간을 사는* 도구. 메트릭·로그·트레이스·APM·RUM·security 까지 *한 UI* 에 다 있음. *설치 = Agent 1 줄 + 토큰*.

### 강점
- **올인원** — 하나의 도구로 *시각화·알람·로그·트레이스* 다 가능
- **자동 계측** — Java/Python/Go/Node 등 *AutoInstrumentation* 이 강력. 코드 수정 없이 APM 동작
- **풍부한 integrations** — AWS / GCP / K8s / DB / 200+ 시스템과 *클릭 한 번* 연결
- **머신러닝 알람** — *baseline 자동 학습* + 이상 감지
- **운영 부담 0** — SaaS, *우리가 관리 안 함*

### 약점
- **비쌈** — 호스트당 $15~30/월 (Pro tier 기준). *로그 / 트레이스 별도 과금*. 중견기업도 *월 천만원 단위*
- **벤더 락인** — Datadog 메트릭 형식·태그 시스템에 *코드와 운영이 종속*
- **데이터 외부 송출** — *민감 데이터* 가 Datadog 클라우드로. *내부망 격리 요구* 환경에선 부적합
- **한국 사례 적음** — 영문 문서 위주, 한국 커뮤니티 약함

### 적합 / 부적합
- 적합: *클라우드 네이티브 중대형 회사*, 글로벌 분산, *운영 인력 부족*
- 부적합: *비용 민감 스타트업*, *온프레미스 폐쇄망*, *데이터 외부 송출 금지*

### 가격 감각 (2026 기준)
- Infra Monitoring Pro: 호스트당 $15/월
- APM Pro: 호스트당 $31/월
- Logs (ingest + retain): $0.10 ~ /GB
- 100 호스트 + 적당한 로그 = *월 ~$5,000~10,000*

---

## 2. Grafana — *시각화·알람의 표준 UI*

### 본질
**데이터 *시각화* 도구**. *자체 데이터 저장 안 함*. Prometheus / Elasticsearch / Tempo / Datadog / MySQL / etc 의 *수십 개 data source* 를 *한 대시보드* 에 모음.

### 강점
- **Data source agnostic** — *어느 백엔드든* 그릴 수 있음
- **PromQL / LogQL / TraceQL** 다 지원 — 통합 쿼리 UI
- **알람 (Grafana Alerting)** — 시각화에서 *바로 알람 정의*
- **오픈소스 + Grafana Cloud** — 자체 호스트 무료, 관리형 유료
- **풍부한 플러그인** — 수백 개 visualization, 비즈니스 KPI 패널도 가능
- **K8s 친화** — Prometheus / Loki / Tempo 와 *자연스러운 조합*

### 약점
- **저장 안 함** — *반드시 다른 백엔드 (Prometheus/ES 등) 가 있어야 함*
- **알람 운영 복잡** — Alertmanager 와 *어느 쪽을 쓸지* 혼란
- **대시보드 폭발** — 누구나 만들 수 있어서 *수십 개 중복 대시보드* 자주 발생

### 적합 / 부적합
- 적합: *Prometheus 또는 ELK 이미 사용 중*, *대시보드·알람 통합 UI* 필요
- 부적합: *데이터 저장 솔루션도 없음* → Grafana 만으론 부족

### 권장 패턴
**Grafana + Prometheus + Loki + Tempo** = *오픈소스로 Datadog 흉내내기* 의 정석. 운영 부담은 *높지만* 비용은 *Datadog 의 1/10*.

---

## 3. Prometheus — *K8s 시대의 메트릭 표준*

### 본질
**시계열 메트릭 DB + Pull-based 수집 + 알람 룰 엔진**. K8s 가 사실상 표준으로 채택. *오픈소스 의 De facto*.

### 강점
- **Pull-based** — Prometheus 가 *각 pod 의 `/metrics` 엔드포인트 긁어옴*. *별도 agent 불필요*
- **Service Discovery** — K8s annotation 만 붙이면 *자동 발견*
- **PromQL** — 매우 강력한 쿼리 언어 (rate, histogram_quantile, sum by, ...)
- **Alertmanager** — 분리된 알람 라우팅 (Slack/Telegram/PagerDuty)
- **에코시스템** — node-exporter, kube-state-metrics, blackbox-exporter 등 *모든 곳에 exporter*

### 약점
- **장기 보관 약함** — 디폴트 *15일 retention*, 장기는 *Thanos / Mimir / VictoriaMetrics* 필요
- **HA 구성 복잡** — *클러스터링 안 됨*, *2 인스턴스 + 외부 storage* 패턴 필요
- **로그 / 트레이스 X** — 메트릭 전용
- **Cardinality 폭발 위험** — label 너무 많이 → 메모리 OOM

### 적합 / 부적합
- 적합: *K8s 클러스터 운영*, *오픈소스 우선*, *DIY 가능*
- 부적합: *로그·트레이스도 같은 UI 에서 보고 싶음* (→ Grafana + Loki + Tempo 묶음)

### 핵심 PromQL 4개
```promql
# Request rate
sum(rate(http_requests_total[5m])) by (service)

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
  / sum(rate(http_requests_total[5m])) by (service)

# p99 latency
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le))

# Memory saturation
sum(container_memory_working_set_bytes) by (pod)
  / sum(kube_pod_container_resource_limits{resource="memory"}) by (pod)
```

---

## 4. 제니퍼 (Jennifer) — *한국 Java APM 의 강자*

### 본질
**한국 토종 Java APM 도구**. 1990 년대 후반 ~ 2000 년대 초반 시작. *대기업 SI / 금융권 / 공공기관* 의 *Java WAS (WebLogic / JBoss / Tomcat)* 운영에 깊이 침투.

### 강점
- **트랜잭션 단위 추적** — 사용자 요청 *하나가 어떤 메서드 → 어떤 SQL → 어떤 외부 호출* 로 흘러갔는지 *세부 단위* 시각화
- **Java 깊이** — JVM 메트릭, GC 분석, 스레드 덤프 자동 수집
- **이상 트랜잭션 탐지** — 임계값 초과 자동 capture (heap dump 포함)
- **한국 기업 특화** — *한글 UI*, *한국 기업의 KPI 명세에 맞춤*, *한국 영업 / 기술지원 강력*
- **온프레미스** — *데이터가 외부로 안 나감* → 금융권 / 공공기관 핵심 요구사항

### 약점
- **상용 라이선스 비싸** — 인스턴스/CPU 당 과금. 중견 기업 *수천만원 단위*
- **Java 중심** — Python / Go / Node 지원은 *상대적으로 약함*
- **글로벌 추세에서 약함** — 클라우드 네이티브 / 컨테이너 / 분산 트레이싱 표준 (OpenTelemetry) 통합이 *상대적으로 느림*
- **K8s 친화도 낮음** — 본질이 *WAS 시대 도구*. K8s 환경에선 *agent 주입* 등 추가 작업

### 적합 / 부적합
- 적합: *한국 대기업/금융권/공공기관*, *Java/Spring/WAS 중심*, *외부 데이터 송출 금지*
- 부적합: *클라우드 네이티브 스타트업*, *다언어 환경*, *컨테이너 / K8s 위주*

### *세대* 의미
제니퍼는 *서버를 SSH 로 들어가서 관리* 하던 시대의 *대표 도구*. *컨테이너 / K8s* 시대엔 *기존 시스템의 *교체 비용이 너무 커서* 유지* 하는 경우가 많음. *새 시스템* 은 OpenTelemetry + Tempo + Datadog 등으로 *세대 전환* 진행 중.

---

## 5. Netdata — *실시간 호스트 모니터링의 끝판왕*

### 본질
**Per-second granularity 의 호스트 모니터링**. 설치 *1 줄 + 1 분* → *수백 개 메트릭 자동 수집*, *예쁜 UI 자동 생성*.

### 강점
- **설치가 압도적으로 쉬움** — `bash <(curl https://my-netdata.io/kickstart.sh)` 1 줄
- **즉시 동작** — *설정 0*, *기본 dashboard 자동*
- **1초 단위 granularity** — Prometheus 의 *기본 15초* 보다 *15배 세밀*
- **자원 사용 적음** — *agent 가 가벼움* (1-2% CPU)
- **모든 게 자동** — CPU/메모리/디스크/네트워크/프로세스/Docker 등 *디폴트로 다 수집*
- **머신러닝 이상 감지** — 무료 tier 에서도 작동

### 약점
- **호스트 중심** — *서비스 레벨 메트릭 (RPS, p99 latency)* 은 별도 통합 필요
- **장기 저장 약함** — 디폴트 *짧은 retention*, Netdata Cloud (유료) 또는 외부 백엔드 필요
- **분산 환경에서 산만함** — 100 호스트면 *100 개 대시보드*. 통합 뷰는 *Cloud 유료* 가야
- **알람은 기본만** — 본격적인 alerting 은 약함

### 적합 / 부적합
- 적합: *홈랩 / 소규모 서버*, *빠르게 시작*, *호스트 레벨 deep dive*
- 부적합: *대규모 분산 시스템*, *APM 필요*

### 홈랩에서의 위치
*Netdata = 각 호스트의 "X-ray"*. Prometheus 가 *서비스 메트릭* 을 본다면, Netdata 는 *그 아래 OS / 디스크 / 네트워크* 를 본다. *둘은 보완 관계*.

---

## 6. *시나리오별 추천*

### A. 스타트업 (5~30명, 클라우드)
```
Prometheus + Grafana + Loki (or ELK)  — *오픈소스 풀스택*
                +
Netdata  — *각 호스트 상세*
```
비용: *서버 비용만*. 운영 부담: *중*.
*Datadog 1년 비용 으로 *시니어 1명 채용* 가능*.

### B. 중견 기업 (30~200명, 클라우드)
```
Datadog (APM + Logs + Infra)   — 운영 인력 절감
                +
Prometheus + Grafana  — *코어 K8s 메트릭은 자체*
```
*하이브리드*. Datadog 의 비싼 부분만 자체로 빼서 *비용 50% 절감*.

### C. 대기업 / 금융권 / 공공기관 (Java 중심, 폐쇄망)
```
제니퍼 (Java APM)  — 기존 자산
                +
Grafana + Prometheus  — *새 시스템*
                +
ELK / Loki  — 로그
```
*세대 공존*. 신규 시스템은 *오픈소스로 전환*, 레거시는 *제니퍼 유지*.

### D. 글로벌 SaaS / 클라우드 네이티브
```
Datadog (전체)  또는
New Relic / Honeycomb
```
*돈으로 시간 사기*. 운영 인력을 *제품 개발* 에 투입.

### E. 홈랩 / 1인 개발자
```
Netdata (각 노드)
                +
Grafana + Prometheus (서비스 메트릭)
```
*무료 + 빠른 시작*. 본 글의 저자도 *이 구성*.

---

## 7. *결합* 패턴 — 실전에서 자주 보이는 조합

### 패턴 1: *Prometheus + Grafana + Loki + Tempo*
오픈소스 *완전 풀스택*. Grafana 가 *통합 UI* 역할.
- **Prometheus** — 메트릭
- **Loki** — 로그
- **Tempo** — 트레이스
- **Grafana** — 시각화 + 알람 통합

비용: 인프라만. 운영 부담: 높음.

### 패턴 2: *Prometheus + Grafana + Elasticsearch (ELK)*
Loki 보다 *전문 검색* 강력한 ES 를 *로그 백엔드* 로.
적합: *로그 검색이 핵심* 인 환경 (보안 분석, 감사)

### 패턴 3: *Datadog 단독*
*돈 있는 회사*. 모든 게 한 곳에. 운영 부담 최저.

### 패턴 4: *제니퍼 + 자체 메트릭*
한국 대기업의 *전형*. APM 은 제니퍼, 인프라 메트릭은 *Nagios / Zabbix / 자체 도구*.

### 패턴 5: *Netdata (per-host) + 다른 도구 (서비스)*
홈랩 / 소규모 운영의 *효율적 조합*. *호스트는 Netdata 가 알아서*, 서비스는 *Prometheus 가 따로*.

---

## 8. *흔한 함정* 5가지

### 8.1 *Datadog 비용이 *조용히 늘어남**
- 호스트 추가 / 로그 늘어남 / 새 integration → *청구서가 매달 ↑*
- 1년 후 *예산 초과* 발견 → 패닉
- 대응: *cost monitoring* 자체를 처음부터 설정

### 8.2 *Prometheus cardinality 폭발*
- label 에 *user_id / request_id* 같은 *고유값* 넣음
- 메모리 OOM → Prometheus 죽음
- 대응: *cardinality 알람* + *label 정책 문서화*

### 8.3 *Grafana 대시보드 100 개*
- 누구나 만듦 → *중복* / *고아* 대시보드 폭증
- 장애 시 *"어디 봐야 하지?"*
- 대응: *공식 대시보드만 *공개*, 개인 대시보드는 *private folder*

### 8.4 *제니퍼 라이선스를 *컨테이너 환경에서 잘못 산정**
- WAS 1 instance 가정으로 라이선스 산 후 K8s 로 가서 *pod 수만큼 늘어남*
- 라이선스 비용 폭증
- 대응: *컨테이너 환경 라이선스 모델 사전 확인*

### 8.5 *Netdata 를 *서비스 메트릭* 으로 잘못 씀*
- Netdata = 호스트, 아니라 *서비스* 가 아님
- *서비스 RPS / p99* 같은 건 Prometheus 가 본질
- 대응: *역할 분담 명확히*

---

## 9. 결론 — *6 가지 원칙*

### 1. *도구 = 층*
한 도구가 모든 층을 *완벽히* 못 한다. *각 층에 맞는 도구* 선택.

### 2. *비용 = 시간*
Datadog 의 비싼 비용 = *운영 인력 시간을 산 것*. 인력이 *부족하면* 합리적.

### 3. *오픈소스 풀스택 = 인력 + 시간 투자*
Prometheus + Grafana + Loki + Tempo = *Datadog 의 1/10 비용*, 단 *운영 인력 1~2명 필요*.

### 4. *알람이 없으면 모니터링이 아니다*
대시보드 100 개보다 *알람 룰 10 개* 가 더 중요. 사람이 *대시보드 안 켜고도* 장애 감지 가능해야.

### 5. *한국 환경의 특수성*
- 금융권 / 공공기관 → 제니퍼 + 폐쇄망 정책 → Datadog 불가
- 일반 IT → 오픈소스 + 부분 Datadog 의 *하이브리드*
- 스타트업 → 오픈소스 + Netdata

### 6. *측정 없이 결정하지 말 것*
도입 전 *현 환경의 메트릭/로그/트레이스 양* 을 측정. *그 양으로 각 도구의 *예상 비용* 계산*. *경험으로 결정 하지 말 것* — 견적이 *생각보다 10배* 비싼 경우 흔함.

---

## 마지막 — *내가 운영하는 홈랩 5노드 클러스터* 의 선택

```
오픈소스 풀스택:
  Prometheus + Grafana + Loki + Tempo
  Fluent-bit (로그 수집)
  Velero (백업)
  
도입 비용: 0 (인프라만)
운영 부담: 중간 (혼자 운영 가능)
```

같은 구성을 *Datadog* 으로 했으면 *연간 $20,000+*. 단, *그 돈으로 *시니어 1명 채용* 가능*.

*어느 쪽이 맞다* 가 아니라 — *우리 회사의 *제약 조건이 무엇이냐* 에 따라 결정*. *돈 vs 시간* 의 트레이드오프. 항상.

다음 글에선 *Prometheus + Grafana + Loki + Tempo *통합 풀스택* 의 *실전 셋업* — 각 컴포넌트의 *Helm values 와 자주 막히는 5가지* 를 정리할 예정.
