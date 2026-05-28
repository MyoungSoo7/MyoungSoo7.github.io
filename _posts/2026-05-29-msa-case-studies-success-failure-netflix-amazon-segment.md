---
layout: post
title: "MSA 12 년 — *Netflix·Amazon 의 성공*, *Segment·Prime Video 의 회귀*, 그리고 *2026 년의 답*"
date: 2026-05-29 00:35:00 +0900
categories: [architecture, microservices, backend]
tags: [msa, microservices, netflix, amazon, uber, segment, prime-video, monolith, modular-monolith, conway-law]
---

> 2014 년 3 월 25 일, Martin Fowler 와 James Lewis 가 *''Microservices''* 라는 한 단어를 글의 제목으로 올렸다. 그 뒤 12 년 동안 *''MSA 로 가자''* 라는 결정은 *전 세계 백엔드 진영의 디폴트* 가 되었다. 하지만 같은 12 년 동안, *''MSA 로 갔다가 돌아왔다''* 는 사례들도 *놀랄 만큼 많이* 쌓였다.

이 글은 *''MSA 는 좋은가, 나쁜가''* 라는 질문에 답하지 않는다. 대신 **누가 성공했고, 누가 실패했고, 그 차이가 어디서 왔는가** 를 6 개 기업 사례를 통해 본다. 그리고 *2026 년의 합리적 답* — *Modular Monolith* 와 *DDD bounded context* 의 부상 — 으로 마무리한다.

---

## 1. MSA 의 출발 — *Netflix 가 길을 내고, Fowler 가 이름을 붙였다*

흔히 MSA 의 출발을 2014 년 Fowler/Lewis 의 글로 보지만, *실제 실험* 은 더 앞선다.

- **2008**: Netflix 의 DVD 사업 *DB corruption* 으로 *3 일* 멈춤. 모놀리식 *Oracle* 단일 장애점에 학을 뗌
- **2008~2011**: AWS 로 이주하면서 *수백 개의 마이크로서비스* 로 *조각조각* 분해
- **2012**: Netflix OSS 공개 — Eureka(서비스 디스커버리), Hystrix(circuit breaker), Ribbon(client LB), Zuul(API gateway)
- **2014**: Fowler/Lewis 의 *''Microservices''* 글 — *''Netflix 가 하는 것들에 이름을 붙여보자''*

즉 MSA 는 *이론이 먼저가 아니라*, **Netflix 의 *생존을 위한 발버둥* 이 *후행적으로 이론화* 된 것** 이다. 이 출발점을 *잊으면* MSA 가 *모든 조직에 적용되는 범용 해법* 처럼 보이게 된다.

---

## 2. 성공 사례 — *조직이 MSA 에 맞춰진* 경우

### 2.1 **Netflix** — *Chaos Engineering* 을 *문화* 로

Netflix 가 MSA 로 *살아남은* 결정적 요인은 *기술이 아니라 문화* 였다.

- **Chaos Monkey** (2011) — *프로덕션에서* 무작위로 인스턴스를 죽인다. *''장애가 나도 안 죽는 시스템''* 을 *강제* 함
- **You build it, you run it** — 개발자가 *자기 서비스의 oncall* 을 직접 짐
- **Freedom & Responsibility** — *''뭐든 해도 되지만 책임도 너의 몫''*

> *결과*: 700+ 개 마이크로서비스. *single failure* 가 *전체 다운* 으로 전이되지 않음. *2015 년 AWS US-EAST-1 장애* 때 *대부분의 회사가 멈춘 동안 Netflix 만 살아남음*.

*''Chaos Monkey 가 *기술 도구* 인 줄 알지만 *진짜는 조직 문화* 다''* — Netflix 엔지니어들이 자주 하는 말.

### 2.2 **Amazon** — *Two-Pizza Team* + *You build it, you run it*

2002 년 Jeff Bezos 의 *''API Mandate''* 메모는 MSA 의 *조직적 청사진* 으로 자주 인용된다.

> *''모든 팀은 *서비스 인터페이스* 로만 데이터를 주고받는다. *직접 DB 공유* 는 *해고 사유*.''*
>
> *''모든 인터페이스는 *처음부터 외부 공개 가능* 하게 설계한다.''*

이 *한 장의 메모* 가 2006 년의 *AWS 출시* 로 이어졌다. AWS 자체가 *''Amazon 내부의 마이크로서비스 인터페이스 일부를 외부에 판 것''* 이다.

> *결과*: Amazon 은 *2011 년 기준* 하루 *수만 번 배포*. 팀당 *서비스 1 개* 로 *독립적 배포 사이클*. AWS 매출이 *전체 영업이익의 60%+* 를 책임지는 *역사적 베팅의 성공*.

### 2.3 **Uber** — *DOMA* 로 *MSA 의 폭주를 길들이다*

Uber 는 *2014~2018* 사이 *2,200 개 마이크로서비스* 까지 *폭증* 했다. 결과는 *''누가 무엇을 책임지는지 모르는 카오스''*.

2020 년 Uber 는 **DOMA (Domain-Oriented Microservice Architecture)** 를 발표한다.

- *수천 개의 마이크로서비스* 를 *수십 개의 도메인* 으로 *그룹핑*
- 도메인 간 통신은 *Gateway* 통해서만 — *직접 호출 금지*
- 도메인 내부는 *자유롭게 마이크로서비스* — *외부에서는 도메인 하나로 보임*

> *결과*: *''개별 서비스 = 마이크로서비스''* 의 환상에서 벗어나, *''도메인 = 책임 단위''* 로 *조직과 코드를 정렬*. *Conway's Law 를 *역으로* 활용한 사례*.

> **인사이트**: *''마이크로서비스가 너무 많은 게 문제''* 라는 *반성* 에서 *MSA 를 버리지 않고 *상위 추상* 을 도입한* 모범 답안.

---

## 3. 회귀/실패 사례 — *''MSA 로 갔다가 돌아왔다''*

### 3.1 **Segment** (2018) — *''Goodbye Microservices''*

데이터 파이프라인 SaaS Segment 는 *2017 년 말 ~ 2018 년* 사이에 *모놀리식으로 돌아갔다*. Alexandra Noonan 의 글 **Goodbye Microservices: From 100s of problem children to 1 superstar** 은 *MSA 회의론의 고전* 이 되었다.

**상황**:
- 고객사마다 *서로 다른 destination* (Google Analytics, Mixpanel, etc) 로 데이터 전송
- *destination 당 1 마이크로서비스* 로 시작 → 140+ 마이크로서비스
- 각 서비스가 *조금씩 다른 의존성 버전* / *조금씩 다른 deploy pipeline*

**증상**:
- *공통 라이브러리 1 줄 수정* → *140 개 서비스 모두에 deploy 필요*
- *''내 서비스만 *살짝* 다르게 해도 되겠지''* → *snowflake 폭증*
- *oncall 이 *140 개 서비스의 모든 다른 동작* 을 외워야 함*

**결정**:
- 140 개 서비스 → *1 개 모놀리식 worker* 로 통합
- *destination 은 *플러그인* 으로 처리* (코드 분리, 배포 통합)

> *결과*: *배포 빈도 ↑, 인지 부하 ↓, 운영 비용 ↓*. 글의 한 줄 결론:
>
> *''MSA 가 *잘못된 도구* 였던 게 아니라 *우리 *문제 도메인* 이 *너무 단순* 했던 것''*

### 3.2 **Amazon Prime Video** (2023) — *MSA → Monolith 로 *비용 90% 절감*

2023 년 5 월, Amazon 의 *Prime Video* 팀이 *놀라운 글* 을 올렸다.

> *''Scaling up the Prime Video audio/video monitoring service and reducing costs by 90%''*

**상황**:
- 라이브 스트림 *비디오 / 오디오 품질* 을 *실시간 모니터링* 하는 서비스
- 원래 *MSA + AWS Lambda + Step Functions* 로 구현
- Step Functions 가 *상태 전이마다 호출* → *비용 폭증*
- *S3 에 frame 을 저장하고 다음 단계가 다시 읽는* 패턴 → *S3 비용 폭증*

**결정**:
- *Lambda + Step Functions* → *EC2 + ECS* 로 *하나의 프로세스 안* 에서 처리
- 프레임을 *메모리* 에 두고 *다음 단계로 함수 호출* — *S3 왕복 제거*

**결과**:
- *비용 90% 절감*
- *처리량 ↑*
- Amazon 내부에서 *''심지어 Amazon 도 MSA 가 항상 답은 아니다''* 의 *공식 인정*

> **인사이트**: *고빈도 데이터 흐름* (high-throughput data flow) 에서는 *''함수 호출이 네트워크 호출보다 1,000 배 싸다''* 는 *물리적 진실* 이 *아키텍처 선택을 압도*. *Distributed Computing 의 8 가지 오류* 중 *''대역폭이 무한하다''* 와 *''네트워크는 공짜다''* 가 다시 드러난 사례.

### 3.3 **Istio at Google** — *제어 평면 자체가 복잡도 폭탄*

Google 이 만든 service mesh **Istio** 는 *MSA 의 운영 복잡도* 를 *해결하려고 만든 도구* 였다. 그런데 *Istio 자체가 분산 시스템* 인 게 문제였다.

- 초기 Istio 는 *4 개의 마이크로서비스 컴포넌트* (Pilot, Mixer, Citadel, Galley)
- *Mixer* 가 모든 요청의 hot path 에서 정책 검증 → *대규모에서 병목*
- *''mesh 를 운영하기 위한 mesh''* 라는 농담이 돌 정도

**결정 (2020, Istio 1.5)**:
- 4 개 컴포넌트를 *하나의 바이너리* `istiod` 로 *통합*
- *Mixer 자체를 제거* — Envoy 로 정책 이동

> **인사이트**: *''마이크로서비스를 만든 사람들이 *제어 평면을 모놀리스로 되돌렸다*''*. *컴포넌트 경계를 너무 잘게 나눈 게 *운영 비용* 으로 직격* 한 사례. *MSA 가 모놀리스 회귀의 *원인* 이 된 보기 드문 케이스*.

---

## 4. *왜* 어떤 조직은 성공하고 어떤 조직은 실패했나

3 + 3 사례를 한 줄로 정리해보면:

| 조직 | 결과 | 핵심 차이 |
|---|---|---|
| Netflix | 성공 | *Chaos Engineering 문화*, *oncall 책임 분산* |
| Amazon | 성공 | *Two-pizza team*, *''you build it, you run it''* |
| Uber | 성공 (회복) | *DOMA 로 *도메인 추상화* 도입* |
| Segment | 실패 (회귀) | *도메인이 *단순* 한데 *서비스를 나눔* |
| Prime Video | 실패 (회귀) | *고빈도 데이터 흐름* 에 *네트워크 분리* |
| Istio | 실패 (회귀) | *제어 평면을 *너무 잘게* 분리* |

### 4.1 *공통 패턴* — *조직 vs 코드 의 정렬*

성공 사례의 공통점:
1. **조직 단위 = 서비스 단위** (Conway's Law 적극 활용)
2. **개발자가 *자기 서비스의 운영* 까지 책임 진다**
3. **장애가 *전파되지 않는* 구조** — circuit breaker, bulkhead, timeout

실패 사례의 공통점:
1. **서비스를 나눴는데 *조직은 그대로*** → *모든 변경이 *cross-team coordination*
2. **도메인이 *고도로 결합* 인데 *물리적으로 분리***
3. ***''마이크로서비스가 *멋있어 보여서*''*** 라는 *기술 주도* 결정

### 4.2 *Conway's Law* 를 *모르면 MSA 는 실패한다*

> *''시스템을 설계하는 조직은 *자기 조직의 의사소통 구조* 를 닮은 시스템을 만든다''* — Melvin Conway, 1967

MSA 는 이 법칙을 *역으로* 활용하는 *조직 패턴* 이다. *''서비스를 나누면 조직도 나뉜다''* 가 아니라, *''조직이 나뉘어야 서비스도 의미 있게 나뉜다''*.

*Segment 가 실패한 이유* — *데이터 파이프라인 *한 팀* 이 140 개 서비스를 운영*. *Conway's Law 와 정반대* 의 배치였다.

*Netflix 가 성공한 이유* — *서비스 하나당 *작은 팀 하나*. 의사소통 비용이 *팀 내부* 로 *국한*.

---

## 5. *2026 년의 답* — *Modular Monolith* 와 *DDD bounded context*

2020 년 이후 진영의 *합리적 합의* 가 모이고 있다.

> **Modular Monolith 부터 시작하고, 명확한 *bounded context* 가 *조직적으로* 분리될 때만 마이크로서비스로 쪼갠다**

### 5.1 *Modular Monolith* — *한 프로세스, 분리된 모듈*

- *하나의 배포 단위* — 운영 복잡도 ↓
- *모듈 간 경계가 *컴파일 타임* 에 강제* (ArchUnit, sealed packages, Spring Modulith)
- *DB 는 분리된 스키마* — *논리적* 으로는 마이크로서비스
- *준비되면 *모듈 → 서비스* 로 *추출* 가능*

**대표 사례 — Shopify**:
- 매출 *수십 조* 규모인데 *여전히 *모놀리식 Rails 앱***
- *''Sorbet''* 으로 *타입 강제*, *''Packwerk''* 로 *모듈 경계 강제*
- *왜 안 쪼개나?* — *''쪼개도 *더 나을 게 없으니까*''*

### 5.2 *Spring Modulith* (2022) — Spring 진영의 *공식 답*

Spring 진영도 2022 년 *Spring Modulith* 를 발표했다.

```java
// src/main/java/com/lemuel/order/
@ApplicationModule(
    allowedDependencies = { "payment" }  // ← payment 모듈만 의존 가능
)
package com.lemuel.order;

// src/main/java/com/lemuel/payment/
@ApplicationModule
package com.lemuel.payment;

// order 가 inventory 를 *직접 호출* 하면 *테스트가 깨짐*
```

- *컴파일 타임 + 테스트 타임* 에 *모듈 경계 검증*
- 모듈 간 통신은 *Spring Application Event* 통해 *비동기적으로*
- *나중에 *서비스 추출* 시 *이벤트 → Kafka 메시지* 로 *교체만 하면 됨*

> *2026 년의 권장 출발점* = **Spring Boot + Spring Modulith + 명확한 bounded context**. *조직이 *팀 단위* 로 커지면 그때 *서비스로 추출*.

---

## 6. *MSA 도입 결정 *3 단계 체크리스트*

실제로 *''MSA 로 가야 할까?''* 라고 고민할 때 다음 3 가지를 *순서대로* 점검하라.

### Q1. *조직이 분리되어 있는가?*

- 팀이 *하나* 인데 *서비스 30 개* 짜내고 있으면 → *실패 예약*
- *''팀이 *독립적으로 배포* 할 수 있는가''* 가 *MSA 의 진짜 척도*

### Q2. *운영 성숙도가 충분한가?*

체크리스트:
- [ ] *Centralized logging* (ELK, Loki) — 분산 로그 추적 가능
- [ ] *Distributed tracing* (OpenTelemetry, Jaeger) — *''내 요청이 어디서 죽었나''* 추적
- [ ] *Centralized metrics* (Prometheus + Grafana)
- [ ] *Service mesh* 또는 *최소한의 service discovery*
- [ ] *CI/CD 가 *모든 서비스에* 자동화*
- [ ] *On-call rotation* 이 *각 서비스마다* 명확

이 중 *3 개 이상 안 되면* 모놀리식으로 *남아라*. *MSA 는 운영 도구를 *갖춘 조직만* 의 사치품*.

### Q3. *분리가 *도메인* 적으로 자연스러운가?*

- *''성능* 때문에 나눠야지''* → *수직 확장 / 캐시* 먼저 시도
- *''*나중에* 분리할 수 있게 미리 나눠두자''* → *YAGNI 위반*. *Modular Monolith* 가 답
- *''*팀 간 충돌* 이 잦아서 *코드를 물리적으로 분리해야* 한다''* → *MSA 적정 시점*

---

## 7. 정리 — *MSA 는 도구이지 목표가 아니다*

12 년의 사례가 가르쳐주는 한 줄:

> **MSA 의 성공은 *기술 선택* 이 아니라 *조직 정렬* 의 문제다.**

Netflix 와 Amazon 이 성공한 건 *Eureka 와 Hystrix* 때문이 아니라 *Chaos Monkey 와 You-build-it-you-run-it* 때문이었다. Segment 와 Prime Video 가 회귀한 건 *MSA 가 나빠서* 가 아니라 *그 도메인에 *과한 선택* 이었기* 때문이다.

*''우리도 Netflix 처럼 가자''* 라는 한 문장이 *지난 12 년 가장 비싼 의사결정* 이었던 회사가 많다. *남이 *입은 옷* 을 *내 몸* 에 맞춘다고 *맞을 리* 없다.

> **2026 년의 합리적 출발점**:
>
> 1. *Modular Monolith* 로 시작
> 2. 모듈 경계는 *DDD bounded context* 로
> 3. *팀이 진짜로 *독립* 할 수 있는 시점* 에만 *서비스로 추출*
> 4. 추출 후엔 *Netflix 의 *문화* 까지 *복제*

기술은 *가져올 수 있다*. 문화는 *복제 불가능* 하다. 이게 MSA 12 년의 *진짜 교훈* 이다.

---

## 더 읽으면 좋은 글·자료

- Martin Fowler·James Lewis, **Microservices** (2014) — *시작점*
- Sam Newman, **Building Microservices** (2 판, 2021) — *실무 교과서*
- Alexandra Noonan, **Goodbye Microservices** (Segment, 2018) — *회귀 사례의 고전*
- Prime Video Tech blog, **Scaling up the Prime Video audio/video monitoring service and reducing costs by 90%** (2023)
- Uber Engineering, **Microservice Architecture at Uber** + **DOMA** 발표
- Vlad Khononov, **Learning Domain-Driven Design** (2021) — *bounded context 의 현대적 정리*
- Spring Modulith 공식 문서 — *모놀리식과 마이크로서비스 사이의 *공식 답*
- Shopify Engineering, **Deconstructing the Monolith** + **Sorbet/Packwerk** 시리즈
