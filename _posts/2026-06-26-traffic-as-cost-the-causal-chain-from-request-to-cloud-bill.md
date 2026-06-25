---
layout: post
title: "*트래픽 의 비용 화* — *요청 한 건* 이 *얼마 의 클라우드 청구서* 가 되는지 의 *인과 사슬* 과 *백엔드 개발자 의 비용 책임***"
date: 2026-06-26 02:30:00 +0900
categories: [backend, infrastructure, cost, finops, sre]
tags: [traffic, cost, finops, egress, cdn, cache, autoscaling, observability-cost, k3s, lightsail, repatriation, idle-cost, p99]
---

> *어느 날 의 *AWS 청구서* — *전 월 대비 *2.7 배*. *팀 의 *공포*. *원인 추적 — *프론트 의 *한 이미지* 가 *CloudFront 캐싱 헤더 가 *잘못 되어 *모든 요청 마다 *S3 에서 *원본 read*. *trafffic 의 *수십 GB egress* + *S3 의 read 요청 수* + *함께 묻어 가는 Lambda invocation 수* — *3 가지 의 *연쇄 폭발*.
>
> *문제 의 *원인 — 코드 의 *6 줄*. *Cache-Control 헤더 의 *한 줄*. *그게 *2 천 만원 의 *월 청구서 의 *증가 의 *씨앗*.
>
> *백엔드 개발자 의 *9 년 의 *경험 의 *조용한 진실* — *모든 트래픽 은 *돈 의 *흔적 을 남긴다*. *그 흔적 을 *코드 의 *어느 한 줄 이 *결정 한다*. *그 한 줄 을 *볼 줄 아는 사람 이 *비용 의 *책임자*.

이 글은 *트래픽 의 *물리 적 흐름* 이 *어떻게 *클라우드 청구서 의 *수치 로 *번역 되는지* 의 *인과 사슬*, *그 사슬 의 *7 가지 *증폭 점*, *그것 의 *7 가지 *축소 도구*, *그리고 *내 *Lightsail → K3s 홈랩 *이주 의 *실측 적 *비용 분해* 까지 *밀도 있게* 정리한다.

함께 보면 좋은 *자매편* :
- *[Lightsail 에서 K3s 온프렘 으로 — *cloud 탈출 의 9 일*](/2026/05/12/lightsail-to-k3s-onprem-repatriation.html)*
- *[Infrastructure 비용 절감 + Cloud Exit + FinOps](/2026/05/30/infrastructure-cost-reduction-cloud-exit-finops.html)*
- *[K3s 홈랩 의 *트래픽 폭주 시나리오 + 예방*](/2026/05/30/k3s-homelab-traffic-surge-scenarios-prevention.html)*
- *[Cache Hit Ratio — *working set / policy / stampede*](/2026/06/10/cache-hit-ratio-deep-dive-working-set-policies-stampede.html)*
- *[CDN 효율 — *CloudFront / Akamai / Cloudflare*](/2026/06/10/cdn-efficiency-cloudfront-akamai-cloudflare.html)*
- *[Datadog vs 무료 관측 — *비용 / 시간 분석*](/2026/06/05/datadog-vs-free-observability-cost-time-analysis.html)*

이 글은 *그 위에 *트래픽 의 *돈 으로 의 *번역 의 *연쇄 의 *통합 시각* 을 *덧 댄다*.

---

## TL;DR — *한 줄 결론*

> *트래픽 의 *각 요청 은 *6 가지 의 *비용 항목* (compute / egress / storage I/O / DB I/O / observability / 부하 가 만든 미래 의 scale-out) 으로 *번역* 된다*. *이 *6 가지 의 *각각 이 *코드 의 *한 두 결정 으로 *수십 배 의 *증폭 또는 *축소* 의 *지렛대 점*. *백엔드 개발자 가 *그 *각 지렛대 점 의 *위치 와 *효과 의 *수치 를 *알아야 한다*. *7 가지 *증폭 점 의 *반대편* 이 *7 가지 *축소 도구*. *그 모든 것 의 *위에 *경우 에 따라 *cloud 탈출 (repatriation) 의 *수십 배 의 *수익*. *내 *Lightsail → K3s 의 *실측 — *월 $180 → $0 (전기 만 +$8)*.

---

## 1. *요청 한 건 의 *비용 의 *해부**

*전형 적 인 *Spring Boot REST API* 의 *한 요청 (HTTP GET)*. *그 요청 이 *클라우드 의 *어느 청구 항목 에 *얼마 의 *흔적* 을 남기는가*.

### 1.1 *6 가지 비용 항목 의 *상세**

| 항목 | 한 요청 의 영향 | 비용 의 단위 |
|---|---|---|
| **Compute** | *EC2 / Fargate / Lambda 의 *CPU 시간* | *vCPU-시간 *. *AWS 의 *t3.medium = $0.0416/h* |
| **Egress (외부 송신)** | *응답 페이로드 의 *바이트* | *GB. *AWS = $0.09/GB (북미)*. *최대 비용 항목 의 *흔한 1 위* |
| **Storage I/O** | *S3 read / EBS IOPS / RDS IOPS* | *요청 수 + 바이트*. *S3 GET = $0.0004/1K req* |
| **DB I/O** | *RDS / Aurora 의 *I/O 요청 + 저장* | *I/O 횟수 + 저장 GB-월* |
| **Observability** | *로그 + metric + trace 의 *수집 / 저장 / 조회* | *GB. *Datadog/New Relic 의 *호스트 별 * 수십 ~ 수백 $/월* |
| **Future scale-out** | *부하 가 *오토스케일 의 *추가 인스턴스 를 *유발* | *간접 적*. *시간 차* 로 나타남 |

*한 요청 의 *직접 비용 = $0.000001 ~ $0.0001 *. *작아 보임*. *그러나 *수천만 요청 / 월* 의 *곱* 이 *수백 ~ 수천 만원*.

### 1.2 *Egress 가 *왜 *대부분 의 *지옥 의 *주인공* 인가**

*AWS 의 *비용 분포 의 *흔한 사실*:

- *Compute (EC2 / RDS / Lambda) = *30 ~ 50 %*.
- *Egress = *20 ~ 40 %*. *많은 회사 의 *예상치 못한 *1 위*.
- *Observability (CloudWatch / Datadog) = *5 ~ 20 %*.
- *Storage = *5 ~ 15 %*.

*Egress 의 *3 가지 의 *함정* :
1. *외부 응답* — *사용자 가 *받는 모든 바이트*. *직관 적 으로 가시 적*.
2. *Cross-AZ traffic* — *서비스 들 의 *AZ 간 통신*. *눈에 안 보이는 *주요 비용*.
3. *백업 / 복제 의 *외부 전송* — *S3 cross-region replication, *RDS 복제 의 *cross-AZ*.

*Egress 의 *진짜 위험* — *내가 *모르고 *발생* 시킨 것 의 *비율 이 *수십 %* 일 가능성.

---

## 2. *증폭 점 7 가지 — *코드 의 *어디 가 *비용 의 *지렛대 인가**

내 *9 년 의 *실제 사고* 의 *분류*.

### 2.1 *캐시 누락 — *Cache-Control 헤더 의 *한 줄**

```
GET /api/products/{id}    응답 헤더 :  Cache-Control: no-store
```

- *클라이언트, CDN, 중간 프록시 모두 *캐시 안 함*.
- *모든 요청 이 *오리진 까지 *왕복*.
- *수십 % 의 요청 이 *동일 한 데이터* 일 가능성 — *그러나 *모두 *재 계산*.

*해결*:
```
Cache-Control: public, max-age=3600, stale-while-revalidate=86400
```

- *CDN edge 캐시 1 시간*.
- *그 사이 의 요청 = *오리진 에 안 옴*.
- *백엔드 의 *compute + DB I/O + egress 가 *수십 배 절감*.

### 2.2 *N+1 쿼리 — *DB I/O 의 *수십 배 증폭**

```java
// ❌
List<Order> orders = orderRepo.findAll();   // 1 쿼리
for (Order o : orders) {
    Customer c = customerRepo.findById(o.customerId);   // N 쿼리
}
```

- *DB I/O 의 *직접 비용 = *RDS IOPS 의 *수백 배*.
- *RDS Provisioned IOPS 의 *추가 구매 강요* → *추가 비용*.
- *그 트래픽 으로 *추가 read replica 의 *autoscale 유발*.

*해결* — *fetch join / batch fetching / DataLoader 패턴*. *수십 배 의 I/O 감소*.

### 2.3 *로그 의 *과도 — *Observability 비용 의 *조용한 폭발**

```java
log.info("Processing request: {}", request);   // 매 요청 1KB
log.info("Loaded user: {}", user);              // 매 요청 2KB
log.info("Result: {}", result);                 // 매 요청 5KB
// 합계 — 매 요청 8KB. RPS 1000 = 8MB/초 = 700 GB/일.
```

- *CloudWatch Logs = *$0.50/GB ingest + $0.03/GB-month 저장*.
- *700 GB/일 = *월 21 TB = *$10,500/월 ingest + $630/월 저장*.

*해결*:
- *log level 의 *체계 (INFO 만 default, DEBUG 는 명시 적)*.
- *구조 화 로그 의 *간결 한 키*.
- *민감 / 무의미 필드 의 *제외*.
- *샘플링 (대표 적 부분 만)*.
- *retention 의 *짧게 (30 일 → 7 일)*.

### 2.4 *오토스케일 의 *비대칭 — *올라 가고 *안 내려옴**

```
오전 9 시  : 트래픽 ↑ → 인스턴스 2 → 8
오전 11 시 : 트래픽 ↓ → 인스턴스 8 → 8 (그대로!!)
오후 5 시  : 트래픽 ↓↓ → 인스턴스 8 → 8 (그대로!!)
```

- *Scale-down policy 의 *너무 보수 적 / 비활성* — *흔한 사고*.
- *주간 평균 부하 의 *2~3 배 인스턴스* 가 *24 시간 돌아감*.

*해결*:
- *명시 적 scale-down 정책 의 *적극화*.
- *Karpenter / Cluster Autoscaler 의 *aggressive 모드*.
- *예약 인스턴스 (Reserved / Savings Plan) 의 *비율 조정*.

### 2.5 *Idle dev / staging — *주말 의 *조용한 청구**

```
production cluster   : 5 노드 × 24h × 365 = $30,000/년
staging cluster      : 5 노드 × 24h × 365 = $30,000/년 ← 80% 비어 있음
dev cluster          : 3 노드 × 24h × 365 = $18,000/년 ← 95% 비어 있음
```

- *staging / dev = production 의 *동일 규모 가 *흔한 함정*.
- *주말 + 야간 = *비활성 의 *60 % 시간*.

*해결*:
- *staging / dev 의 *축소 (production 의 *1/3 ~ 1/5)*.
- *야간 / 주말 의 *자동 종료* (KubeCost / Karpenter / cron).
- *임시 환경 의 *PR 별 *수명 한정*.

### 2.6 *불필요한 외부 호출 — *Egress 의 *조용한 누적**

```
@Service
class OrderService {
    public Order get(Long id) {
        // 매번 외부 의 *국가 코드 API 호출 (실제 거의 안 변함)
        String country = externalApi.getCountry(user.ip());
        ...
    }
}
```

- *외부 API 의 *바이트 가 *egress 비용*.
- *외부 API 자체 의 *호출 비용 (Stripe 의 GET 등 일부 는 무료, 대부분 의 *데이터 API 는 *유료)*.
- *지연 시간 의 *직접 추가*.

*해결*:
- *결과 의 *Caffeine / Redis 캐시*.
- *DB 의 *상수 화 (drift 가 작은 경우)*.
- *Bulk fetch + cache* — 1000 명 의 *국가 를 *한 번 의 *호출 로*.

### 2.7 *cross-AZ traffic — *눈에 안 보이는 *증폭**

```
AZ-A  : Application Pod
AZ-B  : Redis primary
AZ-C  : RDS primary
→ 한 요청 = AZ-A↔AZ-B + AZ-A↔AZ-C = 2 hops × egress 비용
```

- *AWS 의 *AZ 간 traffic = $0.01/GB* (양 방향).
- *MSA 13 개 의 *세분화 시 *수십 hops 가능*.
- *단일 요청 의 *AZ 간 합산 트래픽 = *수십 ~ 수백 KB*.
- *RPS 1000 = *월 *수 TB 의 *눈에 안 보이는 *AZ 간 egress*.

*해결*:
- *Topology-aware routing — Kubernetes 의 *topology spread + topologyAwareHints*.
- *Single-AZ 의 *복제 (가능 한 경우)*.
- *Cross-AZ 가 *필요 한 곳 의 *최소 화*.

---

## 3. *축소 도구 7 가지 — *증폭 점 의 *대 응*

각 증폭 점 의 *직접 적 대 응*. *9 년 의 *실측 적 *축소 비율 의 추정*.

| 도구 | 대 응 증폭 점 | 예상 절감 |
|---|---|---|
| **CDN + Cache 헤더** | 캐시 누락 | *Egress 40~80 % 감소* |
| **Fetch join / Batch / DataLoader** | N+1 | *DB I/O 90 % 감소* |
| **Log sampling + Level 정리** | 로그 과도 | *Observability 60~90 % 감소* |
| **Aggressive Autoscale + Karpenter** | 비대칭 스케일 | *Compute 20~40 % 감소* |
| **Dev/Staging 야간 종료** | Idle 비용 | *환경 별 50 % 감소* |
| **외부 API 의 *캐시 화*** | 불필요한 외부 호출 | *외부 비용 + 지연 동시 감소* |
| **Topology-aware Routing** | Cross-AZ 증폭 | *AZ Egress 30~60 % 감소* |

### 3.1 *추가 의 *비 *코드 적 *도구**

이 *7 가지 위 에 *조직 / 인프라 차원 의 *3 가지*:

1. **Reserved / Savings Plan / Spot** — *Compute 비용 의 *30~70 % 감소*. *예약 의 *수학*.
2. **Compression** — *gzip / brotli 의 *응답*. *Egress + 클라이언트 대역 절감*.
3. **Repatriation (cloud 탈출)** — *극단 적 *수익*. *내 경우 *Lightsail $180/월 → K3s 홈랩 $8/월 의 *95 % 감소*.

---

## 4. *내 *Lightsail → K3s 의 *실측 적 *비용 분해**

내 *2026 년 5 월 의 *실제 이주 의 *수치 적 검증*.

### 4.1 *Before — *Lightsail 4 인스턴스 + S3 + Route 53*

| 항목 | 월 비용 |
|---|---|
| Lightsail 인스턴스 (4 × $40) | *$160* |
| S3 + Egress | *$15* |
| Route 53 | *$5* |
| 총 | *$180* |

특징 — *고정 비용 의 *예측 가능성*. *그러나 *낮 부하 90 % 의 *유휴*.

### 4.2 *After — *5 노드 K3s 홈랩 + Cloudflare*

| 항목 | 월 비용 |
|---|---|
| 전기 (5 노드 평균 60 W × 24h × $0.12/kWh) | *+$8* |
| 인터넷 (기존 가정 회선) | *기존 비용 (+$0)* |
| 도메인 (yearly $12 / 12) | *$1* |
| Cloudflare (free tier) | *$0* |
| 총 | *$9* |

**95 % 절감**. 다만 *비용 외 의 *trade-off* :

| 측면 | Cloud | 홈랩 |
|---|---|---|
| 가용성 (SLA) | *99.95 %* | *내 가 보장* |
| 유지 보수 시간 | *0* | *주 1 ~ 2 시간* |
| 확장성 | *즉시* | *하드웨어 추가 필요* |
| 학습 가치 | *적음* | *극도 로 높음* |
| 사이드 사업 가능 | *제약* | *내 인프라* |

*내 의 *결론 — *개인 / 학습 / 사이드 사업 = K3s 홈랩 의 *압도 적 승리*. *기업 = *상황 따라*. *상세 한 *cloud 탈출 의 *판단 기준 의 *내 의 [Cloud Exit + FinOps 글](/2026/05/30/infrastructure-cost-reduction-cloud-exit-finops.html)*.

---

## 5. *트래픽 패턴 의 *3 가지 시나리오 와 *비용 의 *형태**

*트래픽 의 *모양 이 *비용 의 *모양 을 *결정*.

### 5.1 *Flat constant traffic — *예측 가능 한 *주력 서비스**

```
RPS  ────────────  (24h 일정한 1000)
```

*비용 형태* :
- *Reserved Instance / Savings Plan 의 *극대 효용*.
- *오토스케일 의 *유용 도 ↓* — *수요 가 안 바뀌므로*.
- *On-prem 의 *유리한 영역*.

*적합 전략* — *RI / Savings Plan 의 *60 % 이상 약정*.

### 5.2 *Diurnal traffic — *낮 부하 *밤 휴식**

```
RPS  ┌────┐       ┌────┐
     │    │       │    │
─────┘    └───────┘    └─────
     0    8h     16h    24h
```

*비용 형태* :
- *오토스케일 의 *주된 적용 영역*.
- *Spot / Preemptible 의 *유리한 영역*.
- *야간 의 *idle 의 *절감 의 *큰 영역*.

*적합 전략* — *Autoscale + 야간 dev/staging 종료 + Spot 비율 ↑*.

### 5.3 *Spiky burst — *세일 / 이벤트 / 바이럴**

```
RPS  ─────────────┐                ┌─────────
                  │   (peak 50x)   │
                  └────────────────┘
                  세일 시작        세일 끝
```

*비용 형태* :
- *예측 의 어려움*.
- *오토스케일 의 *반응 시간 의 *함정*. *수 분 의 *늦음 = 500 / 타임아웃 의 *손실*.
- *CDN + Queue 패턴 의 *핵심*.

*적합 전략* — *Cloudflare / CloudFront 의 *극단 적 활용*, *Spring Boot 의 *대기 실 큐 패턴 ([내 글](/2026/06/10/spring-boot-traffic-surge-waiting-room-queue-pattern.html))*, *사전 워밍업 의 *명시 화*.

---

## 6. *백엔드 개발자 의 *비용 책임 의 *5 가지 *체크리스트**

*9 년 의 *최종 정리 — *내 가 *PR 의 *마지막 *5 분* 에 *해야 하는 *5 가지 자가 점검*.

1. **Cache-Control / ETag 의 *공개 가능 응답 의 *모두 설정*** — *덜 의식 적 인 *기본 의 *조용한 비용*.
2. **N+1 의 *부재 확인*** — *fetch join / batch / DataLoader 의 *명시 적 사용 의 *확인*.
3. **로그 의 *과도 필드 의 *제거*** — *DEBUG 의 *prod 활성 의 *확인*. *민감 정보 의 *기본 제외*.
4. **외부 API 의 *캐시 의 *고려*** — *결과 가 *수 분 동안 *유효 한지 의 *질문 의 *습관*.
5. **AZ 간 통신 의 *최소화*** — *Pod 의 *근접 한 *서비스 와 *같은 AZ 의 *우선 의 *고려*.

이 *5 가지 의 *습관 적 적용 이 *팀 의 *월 비용 의 *수십 ~ 수백 % 의 *조용한 차이*.

---

## 7. *조직 차원 의 *FinOps 의 *3 가지 원칙**

*9 년 의 *조직 관점* 의 *정리*.

### 7.1 *Visibility — *모두 가 *볼 수 있어야**

- *팀 별 *클라우드 비용 의 *대시보드*.
- *서비스 별 *태깅 의 *철저 한 강제*.
- *주간 / 월간 의 *비용 의 *공유*.

*보이지 않는 비용 = *제어 안 되는 비용*.

### 7.2 *Ownership — *누가 *주인 인가**

- *각 비용 항목 의 *명확 한 *책임자*.
- *예산 의 *팀 단위 *위임*.
- *초과 시 의 *공식 적 *알람 + 회의*.

*주인 없는 비용 = *모두 의 책임 이 *결국 누구 의 책임 도 아님*.

### 7.3 *Optimization — *계속 *개선 의 *문화**

- *FinOps 의 *주간 회의*.
- *비용 의 *PR 리뷰 의 *공식 항목 (예: KubeCost 의 *PR 리뷰 의 *비용 영향 분석*).
- *연 *최저 가 갱신 의 *공식 목표*.

*개선 하지 않으면 *비용 은 *복리 적으로 증가*.

---

## 8. *결론 — *비용 의 *언어 의 *내면화**

*"트래픽 문제 와 인프라 비용 절감"* — *별개 의 두 주제 가 *아니다*. *하나 의 *인과 사슬 의 *양 끝점*.

- *트래픽 의 *패턴 이 *비용 의 *모양 을 *결정*.
- *비용 의 *형태 가 *트래픽 의 *지속 가능성 의 *경계 를 *결정*.
- *그 사이 의 *번역 의 *지렛대 가 *코드 의 *어느 한 줄 들*.

*9 년 의 *결론* — *백엔드 개발자 의 *9 년차 의 *진짜 차별화 의 *한 가지* 가 *이 *번역 의 *능력*. *내 코드 의 *한 줄 이 *팀 의 *월 청구서 의 *수십 % 의 *지렛대 임 을 *알고 *결정 하는 사람*.

> *"이 코드 는 *얼마 의 *클라우드 비용 을 *발생 시키는가" 의 *질문 을 *내 가 *매 PR 마다 *내게 *하는 것* — *그게 *AI 시대 의 *백엔드 의 *남는 자리 의 *한 형태*.*

---

## 다음 으로 *권 하는 읽기**

- *Cloud FinOps Foundation 의 *FinOps Framework* — *공식 적 프레임 워크*.
- *AWS Cost Explorer + Cost Anomaly Detection* — *기본 도구 의 *습관 적 활용*.
- *KubeCost* — *Kubernetes 의 *비용 의 *세부 분해 의 *최고 도구*.
- *내 자매편* — *위 의 *6 개 자매편 의 *통합 적 *읽기*.

*다음 글* — *KubeCost 의 *실제 적용 + 내 K3s 홈랩 의 *유틸리티 비교 + Cloudflare 의 *무료 의 *극한 활용 의 *3 부 시리즈* — *곧*.
