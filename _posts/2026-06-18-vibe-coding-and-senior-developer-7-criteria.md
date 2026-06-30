---
layout: post
title: "*바이브 코딩* 과 *AI 시대 시니어 개발자* 의 *7 가지 기준* — *위임 못하는 영역* 의 명세"
date: 2026-06-18 03:30:00 +0900
categories: [ai, software-engineering, senior-engineer, architecture]
tags: [vibe-coding, ai-coding, senior-engineer, code-review, domain-driven-design, hexagonal, llm, claude-code, copilot]
---

> 친구가 메시지를 보냈다 :
>
> *7 가지를 적었다*. *도메인 경계 / AI 지시 / 코드 리뷰 / 장애·보안·성능 / 테스트 전략 / 운영 구조 / 비즈니스 번역*. *"이게 AI 시대 의 *남는 역할 이지 않나*"*.
>
> 이 7 가지를 보다가 *놀랐다*. *모두 *바이브 코딩 의 *정확한 반대편* 에 있었다*.

이 글은 *바이브 코딩* 이라는 *현상* 과 *위 7 가지 기준* 이 *어떻게 *서로의 거울* 인지*, 그리고 *AI 시대의 *시니어 개발자의 *가치 가 *어디에 *남는지** 를 *내 18 시간 사고 추적 경험* 과 함께 분석한다.

내 *6 월 15 일 글* [*AI 가 할 수 있는 것 / 못 하는 것 + 5 가지 기준*](/2026/06/15/ai-coding-limits-and-anti-spaghetti-criteria.html) 의 *후속 자매편*. *5 가지 기준 (시스템 맥락 / 미래의 자신 / 다른 사람 이해 / 사고 학습 / 비즈니스 목적)* 이 *PR 시점의 self-check 리스트* 였다면, *이 7 가지* 는 *시니어 개발자의 *직무 정의 그 자체*.

---

## TL;DR — *한 줄 결론*

> *바이브 코딩* 은 *junior 의 함정*. *7 가지 기준* 은 *senior 의 정의*. *AI 가 *junior 수준 코드 생산* 을 *자동화* 했으니 *senior 의 시야가 *상대적으로 더 비싸 졌다*. *완벽 코드 작성* 이 *senior 의 일* 이 아니라 *위 7 가지 의 시야 + 책임* 이 *AI 시대 senior 의 *진짜 차별화*.

---

## 1. *바이브 코딩 의 정의*

*Vibe Coding* — 2025 년 초 *Andrej Karpathy* 가 명명한 코딩 패턴.

> *"AI 에게 *자연어로 분위기 가는 대로* 코드를 시키고 *읽지도 검토하지도 않고* 그대로 받아들이는 흐름."*

특징 :

- *AI 가 *국지적 정답* 을 *놀랍게 잘* 만든다. 이게 핵심 동력
- *개발자는 *시간 절약 + 빠른 prototyping* 의 *환상* 에 빠진다
- *코드 의 *전체 맥락 / 책임 / 시야* 는 *비워진다*
- *수십 PR 의 *자잘한 정답들* 이 *모이면* *한 덩어리의 *진흙* 이 된다*

내 [9 일 묻힌 frontend 사고](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug.html) 가 *전형적 사례*. *코드 자체는 *AI 가 만든 *정확한 패턴*. 다만 *Layer 0 (CI/CD pipeline) 의 *race* 까지 *AI 가 못 봤고*, *나도 *바이브 모드 로 만들어 *9 일 묻혔다*.

*바이브 코딩 이 *나쁜 것* 이 아니다. *프로토타이핑 / 실험 / 학습 단계* 에선 *합리적*. 다만 *시니어 의 *책임 영역* 에선 *함정* 이다.

---

## 2. *바이브 코딩 의 *3 가지 *구조적 위험***

### 2.1 *국지적 최적화 의 *축적**

10 개의 *국지적 정답* 이 *시스템 차원* 에선 *모순* 가능. 예 :

- *서비스 A* 가 *eventual consistency* 가정으로 코드
- *서비스 B* 가 *immediate consistency* 가정으로 코드
- *둘이 만나는 *순간* 에 *조용한 데이터 손실*

AI 는 *각 서비스 코드* 를 *완벽* 하게 만들지만 *서로의 가정* 을 *공유* 하지 못한다.

### 2.2 *Why 의 *증발**

AI 가 만든 코드의 *왜* 는 *prompt 안에* 만 있고 *코드 / commit / 문서 에는 *안 남는다*. 6 개월 후 *그 코드 를 *바꿔야* 할 때 *왜 그렇게 됐는지* 모른다*. *변경의 *비용 ↑*.

### 2.3 *책임 의 *위임 가능 한 환상**

*AI 가 만들었으니까 *내가 책임자가 아니라는* 무의식적 위임*. 실제론 *signoff 는 *사람 이 한다*. *바이브 모드 = 책임자가 *몰래 사라진 *코드*. 사고 시 *복구 의 시야 없음*.

---

## 3. *7 가지 기준 — *바이브 코딩 의 *반대편 거울***

친구가 적은 *7 가지 기준* 을 *바이브 코딩 의 *각각 다른 반대편* 으로 매핑.

### 3.1 *기준 1 — 도메인 경계를 나눌 수 있는 사람*

**바이브 코딩 한계** : ❌

AI 는 *주어진 함수 / 클래스 안* 의 정답만 만든다. *Bounded Context, Aggregate, Hexagonal Architecture* 의 *경계 결정* 은 *비즈니스 의미* 의 영역. *AI 가 *어디서 도메인이 끝나고 *어디서 다음 도메인이 시작 하는지* 를 *못 본다*.

**개발자 가치** : 🔥 *압도적으로 상승*

*경계가 망가지면 *수십 PR 의 자잘한 정답이 *한 덩어리의 *진흙* 이 된다*. 내 [settlement 의 ArchUnit 3 가지 핵심 룰](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) 이 *경계 강제 의 *컴파일러 수준 evidence*. *코드 가 *AI 가 만든 거여도 *경계 가 지켜지면 *바이브 모드 가 아닌 *시니어 모드*.

### 3.2 *기준 2 — AI 에게 정확히 작업 지시할 수 있는 사람*

**바이브 코딩 한계** : ❌

*그 자체가 *바이브 코딩 의 *정확한 반대편*. *"느낌으로 시키면" *바이브*, *명확한 context + constraint + acceptance criteria 로 시키면* *진짜 활용*.

**개발자 가치** : 🔥 *새로운 핵심 스킬*

*Prompt 엔지니어링 ≠ AI 지시*. 차이는 :

| 항목 | Prompt 엔지니어링 | AI 지시 (시니어) |
|---|---|---|
| 입력 | *자연어 한 줄* | *시스템 맥락 + 과거 사고 + layer contract + 비즈니스 의도* |
| 출력 검증 | *동작 확인* | *5 가지 기준 self-check (시스템 맥락 / 미래의 나 / 다른 사람 / 사고 학습 / 비즈니스)* |
| 책임 | *Prompt 가 정답* | *내가 signoff*, AI 가 도구 |

*AI 의 prompt context 를 *조직 의 *맥락* 으로 *구성* 하는 메타 작업* 이 *AI 시대 *새로 등장한 시니어 일*.

### 3.3 *기준 3 — 생성된 코드를 리뷰할 수 있는 사람*

**바이브 코딩 한계** : ❌

*읽지 않는* 게 바이브의 정의. *리뷰 = 바이브 코딩의 *정확한 반대*.

**개발자 가치** : 🔥 *진짜 시니어의 영역*

내 [9 일 묻힌 사고](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug.html) — *AI 가 만든 fix 코드는 *기술적으로 *정확*. 다만 *Layer 0 (CI/CD) 의 *race 가 *9 일 묻힌* 것* 은 *리뷰어 가 *시스템 맥락* 으로 *catch* 해야 했음. *내가 *바이브 모드 로 *그냥 머지* 한 결과 *9 일 묻혔다*.

리뷰 = *AI 의 *국지적 정답* 을 *전체 시스템 의 *맥락 에 *대조* 하는 작업*.

### 3.4 *기준 4 — 장애 / 보안 / 성능 리스크 를 잡는 사람*

**바이브 코딩 한계** : ❌

*국지적 패턴 은 OK*, *시스템 의 *교집합 리스크* 못 본다*. 예 :

- *@Transactional 안 외부 HTTP* → DB connection 점유 → cascading failure ([HikariCP 글](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html))
- *cgroup throttling* → consumer lag 누적 ([Velero 99.54% 사고](https://github.com/MyoungSoo7/helm-deploy/blob/master/docs/VELERO-RUNTIME-CONFIG.md))
- *N+1 query* → DB 폭주 ([응답시간 모니터링 글](/2026/06/10/backend-latency-and-monitoring-truth.html))
- *SQL injection* → 코드 단 *prepared statement* 인데 *동적 쿼리* 우회
- *Race condition* → idempotency 누락 ([Triple Idempotency 글](/2026/06/13/settlement-consistency-batch-kafka-outbox.html))

**개발자 가치** : 🔥 *경험치 의 영역*

*과거 사고 의 함정* 을 *AI 에게 *prompt 로 주입* 안 하면 *같은 사고 반복*. 본인 [9 일 묻힌 사고 + velero 좀비 잡 + etcd HDD] 박제 시리즈 가 *진짜 evidence*.

### 3.5 *기준 5 — 테스트 전략 을 세우는 사람*

**바이브 코딩 한계** : ❌

*주어진 함수의 unit test* 는 잘 만든다. *어디서 어디까지를 테스트할지 / E2E vs Integration vs Contract Test 의 트레이드오프* 는 *못 본다*.

**개발자 가치** : 🟡 *부분적으로 자동화 가능 + 전략은 사람*

- *Unit test 자동 작성* → AI 가 잘함
- *Test pyramid 의 *균형 결정* → 사람
- *Contract test (Pact / Spring Cloud Contract)* → AI 가 보조, 결정은 사람
- *Performance test 의 *시나리오 설계* → 사람
- *Synthetic monitoring 의 *외부 검증* → 사람 (서비스 의 *진짜 사용자 시점*)

*전략 = 비즈니스 가치 의 함수*. *AI 가 *전략 까지 짤 수 없다*.

### 3.6 *기준 6 — 운영 가능한 구조로 만드는 사람*

**바이브 코딩 한계** : ❌

*돌아가는 코드 와 *운영 가능한 코드* 는 다르다*. 운영 가능한 구조 의 요소 :

- *관측가능성* (Metric + Log + Trace 의 3 pillars)
- *DLQ + retry + circuit breaker*
- *Bulkhead* (thread pool 분리)
- *Idempotency* (Triple Idempotency 패턴)
- *Health probe + readiness 시점 조정*
- *Graceful shutdown*

*AI 는 *각 패턴 을 *알지만 *언제 어디서 *필요한지* 못 본다*.

**개발자 가치** : 🔥 *본인 강점*

내 시리즈 [Triple Idempotency / Transactional Outbox / 비동기 인프라 책임 행렬 / 응답시간 모니터링] 이 *이 영역의 *직접 증거*. *운영 가능한 구조의 *시야 가 *AI 시대 의 senior 의 *제 1 가치*.

### 3.7 *기준 7 — 비즈니스 요구를 기술 구조로 번역하는 사람*

**바이브 코딩 한계** : ❌

AI 는 *문제 를 받아 *기술 적으로 *완벽 한 답* 을 *내놓는다*. *문제 자체가 *진짜인지* 는 *모른다*.

예 :

- 비즈니스 : *"검색 응답시간을 500ms 로 낮춰라"*
- 기술 정답 : *인덱스 추가, 캐시, ElasticSearch 도입*
- 진짜 비즈니스 목적 : *이탈률 1% 감소 → 분기 매출 5% 증가*
- 진짜 솔루션 : *latency 보다 *검색 결과 의 *관련성* 이 더 중요* (lower CTR)

**개발자 가치** : 🔥 *시니어의 *진짜 일*

*AI 시대 에도 *기획 → 기술* 의 *번역 책임* 은 *사람 에게 남는다*. *비즈니스 사이드 + 기술 사이드 가 *대화* 하는 *통역사 의 역할*.

---

## 4. *7 가지 기준 의 *상호 연결**

7 가지가 *독립적 으로 *작동 하지 않는다*. *서로 *연쇄 의존* 관계가 있다.

```
[기준 7: 비즈니스 번역]
       ↓
[기준 1: 도메인 경계]
       ↓
[기준 6: 운영 구조] ← [기준 4: 리스크 catch]
       ↓                    ↓
[기준 5: 테스트 전략]   [기준 3: 코드 리뷰]
       ↓                    ↓
        [기준 2: AI 지시]
```

- *비즈니스 번역 (7)* 이 *도메인 경계 (1) 의 *근거*
- *도메인 경계* 가 *운영 구조 (6) 의 *제약*
- *운영 구조* 가 *테스트 전략 (5) + 리스크 catch (4) 의 *대상*
- *모두 합쳐서 *AI 지시 (2) 의 *context*

*7 가지 중 *어느 한 가지만 가진 사람* 은 *바이브 모드 의 *위장*. *전부 갖춘 사람만이 *진짜 시니어*.

---

## 5. *AI 시대 시니어 의 *가치 측정**

내 [6/15 글의 5 가지 기준](/2026/06/15/ai-coding-limits-and-anti-spaghetti-criteria.html) 과 *이번 7 가지 기준* 의 관계 :

| 5 가지 기준 (PR self-check) | 7 가지 기준 (직무 정의) |
|---|---|
| 시스템 맥락의 연결 | 도메인 경계 (1) + 운영 구조 (6) |
| 미래의 자기 자신 | (직무 정의 에 포함 안 됨 — 개인 책임) |
| 다른 사람 의 이해 가능성 | 도메인 경계 (1) + 코드 리뷰 (3) |
| 사고 학습 의 반영 | 리스크 catch (4) |
| 비즈니스 의 진짜 목적 | 비즈니스 번역 (7) |
| (PR self-check 에 없음) | AI 지시 (2) — 메타 작업 |
| (PR self-check 에 없음) | 테스트 전략 (5) |

5 가지는 *변경 시점의 self-check*, 7 가지는 *직무 의 *영역 정의*. *서로 보완*. 5 가지 self-check 가 *루틴* 이 되고, 7 가지 가 *영역의 *전체 그림* 이다.

---

## 6. *내 인프라 의 *7 가지 기준 evidence***

각 기준 별로 *내 작업의 *직접 증거*.

### 6.1 *기준 1 — 도메인 경계*

- [settlement 의 ArchUnit 3 핵심 룰](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) — Hexagonal 경계 *컴파일러 수준 강제*
- [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) — *추상화 layer 의 경계 시야*

### 6.2 *기준 2 — AI 지시*

- 이 블로그 글 *16 편* 자체가 *AI 와 협업 한 evidence*. *내가 *AI 에게 *어떻게 지시했는지* 의 *결과*. 메모리에 박힌 *사고 학습 박제 패턴* 이 *prompt context 의 *재료*.

### 6.3 *기준 3 — 코드 리뷰*

- [9 일 묻힌 사고 5 PR 시퀀스](https://github.com/MyoungSoo7/helm-deploy/pull/22) #20 → #22 → #24 → #28 → #29 — *국지적 정답이 *전체 시스템 에서 *9 일 묻혔던 이유* 를 *수직 추적*

### 6.4 *기준 4 — 리스크 catch*

- [Velero CPU throttling 99.54%](https://github.com/MyoungSoo7/helm-deploy/blob/master/docs/VELERO-RUNTIME-CONFIG.md) — Prometheus 메트릭 catch + cgroup limit 상향
- [etcd HDD fsync trap](/2026/06/06/etcd-fsync-hdd-trap-kube-api-error-budget-burn.html) — KubeAPIErrorBudgetBurn 알람에서 *디스크 마이그레이션 까지의 수직 진단*
- [LimitRange ratio 위반](https://github.com/MyoungSoo7/helm-deploy/pull/40) — academy-staging redis 한 달 묻혔던 ratio 8 vs 10 위반 catch

### 6.5 *기준 5 — 테스트 전략*

- *Synthetic monitoring* — chat.lemuel.co.kr 의 *외부 served bytes 검증* (9 일 묻힌 사고 진단의 *최후 보루*)
- *Playwright E2E + 배포 후 외부 도메인 가용성 검증*

### 6.6 *기준 6 — 운영 구조*

- [settlement 의 Triple Idempotency](/2026/06/13/settlement-consistency-batch-kafka-outbox.html)
- [Transactional Outbox 패턴 + Micrometer 4 종 메트릭](/2026/06/16/async-integration-and-infrastructure.html)
- [HikariCP 5 가지 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html)
- [이커머스 트래픽 제어 7 layer](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html)

### 6.7 *기준 7 — 비즈니스 번역*

- *Lemuel XR 의 Recovery 영성 동행 mission* — *치료 도구 가 아닌* *영성 동행* 으로 *기획 의 *정의* + *AI 기능 *비활성화 결정**. 기술 가능성 보다 *진짜 목적 의 *번역*
- *sparta-msa 의 *학습 + 실 운영* 균형* — *완벽 production 보다 *진정성 의 evidence* 의 가치 선택

---

## 7. *결론 — *바이브 코딩 이 늘어날수록 *시니어 가 비싸 진다***

> *"바이브 코딩 은 *junior 의 함정*. *7 가지 기준* 은 *senior 의 정의*. *AI 가 junior 수준 코드 생산* 을 *자동화* 했으니 *senior 의 시야가 *상대적으로 *더 비싸 졌다*. *완벽 코드 작성* 이 *senior 의 일* 이 아니라 *위 7 가지 의 시야 + 책임* 이 *AI 시대 senior 의 *진짜 차별화*."*

7 가지 모두 *바이브 코딩이 못 하는 영역*. *그게 우연 이 아니라 *바이브 코딩이 *위임 못하는 영역의 *명세** 다.

*AI 시대의 시니어 = *위임 못 하는 영역 의 *책임자**. 더 명확하게 :

- 도메인 경계의 *결정자*
- AI 지시의 *맥락 주입자*
- 코드 리뷰의 *시야 검증자*
- 리스크의 *학습 + 박제자*
- 테스트의 *전략 수립자*
- 운영 구조의 *디자이너*
- 비즈니스의 *번역자*

7 가지 모두 *signoff 책임* 의 다른 얼굴. *AI 가 *생성* 의 80% 를 가져가도 *senior 의 *signoff 영역* 은 *축소 되지 않는다*. *오히려 *signoff 의 가치 가 *더 크게 평가 된다*.

*다음에 *AI 한테 시키기 전에 — *내가 *7 가지 중 *몇 가지를 *책임지고 있는가* 를 *자문 해보자*. 그 답이 *내가 *바이브 모드 인지 senior 모드 인지* 의 *간단한 시계 다*.

---

*시리즈 :* [C++ 는 클러스터 *밖에* 있다](/2026/06/07/cpp-in-kubernetes-cluster-outside-the-cluster.html) · [Go 는 클러스터 *전체에* 있다](/2026/06/07/go-is-everywhere-in-my-k3s-cluster.html) · [R 은 클러스터에 *없다*](/2026/06/07/r-not-in-my-k3s-cluster-and-why.html) · [이커머스 SaaS 의 트래픽 제어](/2026/06/07/ecommerce-saas-traffic-control-defense-in-depth.html) · [Observer Pattern 의 7 layer stack dive](/2026/06/09/observer-pattern-down-to-cpu-stack-dive.html) · [HikariCP 의 5 시간 설정](/2026/06/10/spring-boot-hikaricp-connection-pool-wait-time.html) · [백엔드 응답시간 + 모니터링](/2026/06/10/backend-latency-and-monitoring-truth.html) · [Python vs Java 알고리즘](/2026/06/11/python-vs-java-algorithms-comparison.html) · [정산 정합성](/2026/06/13/settlement-consistency-batch-kafka-outbox.html) · [AI 가 할 수 있는 것 / 못 하는 것](/2026/06/15/ai-coding-limits-and-anti-spaghetti-criteria.html) · [비동기 배치 7 패턴](/2026/06/15/batch-as-async-integration-pattern.html) · [비동기 연동과 인프라](/2026/06/16/async-integration-and-infrastructure.html) · *바이브 코딩 vs 시니어 7 기준 (현재 글)*

*이 글은 sparta-msa-project + settlement + helm-deploy 의 *18 시간 9 일 묻힌 사고 추적 + Triple Idempotency + Observer 7 layer stack* 운영 경험과 [6/15 의 5 가지 기준 글](/2026/06/15/ai-coding-limits-and-anti-spaghetti-criteria.html) 의 *후속 자매편* 으로 작성.*
