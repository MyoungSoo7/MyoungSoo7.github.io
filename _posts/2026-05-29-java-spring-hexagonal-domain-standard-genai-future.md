---
layout: post
title: "Java/Spring + 헥사고날 — *복잡한 도메인의 정합성·확장성* 을 책임지는 *구조 표준* 의 과거·현재·생성형 AI 시대의 미래"
date: 2026-05-29 03:50:00 +0900
categories: [java, spring, architecture, ddd, ai]
tags: [hexagonal, ports-and-adapters, ddd, spring-modulith, archunit, bounded-context, ubiquitous-language, gen-ai, agent-orchestration, backend]
---

> *''구조 (structure) 는 *기능 (feature) 보다 오래 산다*''* — 백엔드 시니어가 *''매일 하는 일''* 의 *진짜 무게* 는 *오늘의 기능* 이 아니라 *내일·내년·5 년 뒤에도 *팀이 일관되게 확장할 수 있는 *틀* 을 박는 일*. 그 틀이 곧 **구조 표준 (architectural standard)**. Java/Spring + 헥사고날 (Ports & Adapters) 은 *2005 년 Alistair Cockburn 의 한 문장* 에서 시작해 *2026 년 *생성형 AI 시대의 *agent 경계 contract*''* 까지 *진화* 중이다. 이 글은 *''어떻게 해왔고, 지금 어떻게 하며, *AI 시대에 어떻게 *재정의* 될지''* 를 정리한다.

---

## 1. *''복잡한 도메인''* 이란 무엇인가

*''복잡 (complex)''* 은 *''*어렵다 (hard)*''* 와 다르다. Cynefin framework 의 정의:

- **Simple** — *원인-결과 명확*, *''best practice''* 가 답
- **Complicated** — *원인-결과 분석 가능*, *''good practice + 전문가''*
- **Complex** — *원인-결과가 *retrospect 으로만 보임*, *''emergent practice''*
- **Chaotic** — *원인-결과 없음*

*도메인 (domain) 이 *complex 하다''* 는 곧 *''*규칙·예외·맥락이 *살아있는 사람의 결정* 에 기댄 채로 *코드 안에 들어와야 한다''*''*. 결제·정산·트레이딩·의료·물류·콘텐츠 — *''*법규 + 사용자 행동 + 외부 시스템 + 시간 흐름*''* 이 *교차* 하는 영역.

이 *''복잡함''* 을 *코드로 표현* 할 때 *''*아무 구조 없이* 짜면''* — *6 개월 만에 *수정 불가능''*. *''*어떤 구조* 를 *어떻게 정렬* 할지''* 가 *백엔드 시니어의 *진짜 책임*.

## 2. *DDD 의 *bounded context*** — *''복잡 도메인을 *자르는* 단위''*

Eric Evans 의 *Domain-Driven Design* (2003) — *''*하나의 거대한 모델* 로 *모든 걸 표현하지 마라''*. 도메인을 *''*경계 (bounded context) 단위로 *잘라* 각 안에서 *내부적으로 일관된 *모델 (model)*''*''*.

*같은 단어 *''주문 (Order)''*''* 이 *결제 컨텍스트* 와 *배송 컨텍스트* 에서 *''다른 모델''* 일 수 있다. *''같은 이름·다른 의미''* 가 *''*복잡함을 자르는 *최소 단위*''*.

**Ubiquitous Language** — 각 bounded context 안에서 *''팀-제품-코드 가 *같은 단어로 말한다''*''*. *''결제 API 의 *cancel*''* 과 *''배송 API 의 *cancel*''* 은 *다른 단어로 명명*. 이 *언어 정렬* 이 *''*도메인 정합성 (domain integrity)*''* 의 *기반*.

## 3. *헥사고날 (Ports & Adapters) 의 본질* — *2005 년 Cockburn 의 한 문장*

> *''Allow an application to equally be driven by users, programs, automated tests, or batch scripts, and to be developed and tested in isolation from its eventual run-time devices and databases.''*
> — Alistair Cockburn, *''Hexagonal Architecture''*, 2005

해석:
- *''*도메인 코어 (core) 가 *외부 세계 (DB, HTTP, queue, file) 를 *모른다*''*''*
- *''외부 세계는 *adapter* 로 *교체 가능*''*
- *''*테스트는 *adapter 없이* 도메인만* 검증 가능''*

### 3.1. *세 단어로 줄인 헥사고날*

| 개념 | 뜻 |
|---|---|
| **Domain (core)** | 비즈니스 규칙. *외부 의존 0* |
| **Port** | 도메인이 *''외부와 대화하는 *인터페이스* 정의''* |
| **Adapter** | port 를 *''*실제 기술* 로 구현''* — JPA adapter, HTTP adapter, Kafka adapter |

### 3.2. *의존 방향* 의 *유일한 규칙*

```
adapter → port (interface) ← domain
                  ↑
              port 가 *domain 쪽에 정의됨* — 이것이 *반전 (inversion)*
```

*''*adapter 가 *domain 에 의존*''*'' (역방향 아님). *''*domain 은 *adapter 의 존재를 *모름*''*''*. 이 *한 줄* 이 모든 *''*레이어 위반 (layer leak)*''* 의 *판정 기준*.

### 3.3. *왜 *''*육각형*''* 모양일까*

Cockburn 자신이 *''*4각형은 *내부·외부 두 면* 만 보여 *''양극 대비''* 를 강조하지만, *''복수의 *port 가 있다''*''* 는 *시각화* 를 위해 *6각형* 으로 그렸다''* 라고 설명. *수학적 의미 없음*. *''port 가 *여럿* 이라는 *시각적 강조*''* 뿐.

## 4. *''왜 Java/Spring 에 헥사고날이 *자리잡았는가''*

### 4.1. *DI 컨테이너 = *반전의 *기반 인프라*''*

Spring 의 *''Dependency Injection''* 은 *''*외부 의존을 *밖에서 주입*''* 함으로써 *''*도메인이 *구현체를 직접 import 안 함*''* 을 *''*컨테이너 차원에서* 강제* 가능*. 헥사고날의 *''*adapter 를 *교체 가능*''* 이 *''Spring 의 @Bean 한 줄로 가능''*.

Python·Go 진영에선 *''DI 가 *언어 차원에서 미약*''* 해서 *''헥사고날을 *수동으로 구성*''* 해야. 자바가 *''*무게에 비례한 *질서 강제*''* 가 *''장점''* 인 분야.

### 4.2. *Spring Boot 3/4 + Java 17/21* 의 시너지

- **record** (Java 14) — *''*불변 데이터 객체* 1 줄''*. *''도메인 value object''* 표현 *대폭 단순화*
- **sealed class** (Java 17) — *''*가능한 하위 타입 *제한*''*. *''*도메인 상태 (state) 의 *닫힌 모델링*''*
- **pattern matching** (Java 21) — *''*switch 가 *exhaustive*''* — *''*상태 누락 *컴파일 타임 감지''*''*
- **virtual threads** (Java 21) — *''*adapter 가 *비동기 reactive 안 써도* 고동시성 가능''*

이 4 가지가 *''*헥사고날의 *도메인 표현이 *훨씬 정교* 해진''* 직접 원인.

### 4.3. *Spring Modulith* (2023+) — *''*모놀리스 안 *bounded context 의 *물리적 분리*''*

```
src/main/java/
  com.foo.order/           ← bounded context
    OrderService.java
    package-info.java       ← @ApplicationModule
  com.foo.payment/         ← bounded context
    PaymentService.java
    package-info.java
```

*''Modulith 가 *''패키지 간 *허용 의존''* 을 *''*컴파일 타임에 검증*''*''*. *''*JAR 분리 없이 *bounded context 분리 효과*''*. *''마이크로서비스로 *너무 일찍* 가는 *실수* 의 *대안*''*.

## 5. *''표준을 *팀에 *강제* 하는*'' 실전 도구*

*''*문서로 *''*이러이러하게 하라*''* 만 쓰면 *6 개월 뒤 *전부 위반*''* — *''*구조 표준은 *코드로 강제* 되어야* 한다*.

### 5.1. **ArchUnit** — *''*아키텍처 규칙을 *테스트로*''*

```java
@Test
void domain_must_not_depend_on_spring() {
    noClasses()
        .that().resideInAPackage("..domain..")
        .should().dependOnClassesThat().resideInAPackage("org.springframework..")
        .check(classes);
}

@Test
void application_must_not_use_jpa_directly() {
    noClasses()
        .that().resideInAPackage("..application..")
        .should().dependOnClassesThat().resideInAPackage("jakarta.persistence..")
        .check(classes);
}
```

*''ArchUnit 이 *CI gate 에 박혀있으면 *위반 PR 이 *''merge 자체* 가 안 됨*''*. *''*문서 vs 강제* 의 *근본 차이*''*.

### 5.2. **Outbox Pattern** — *''*트랜잭션 + 메시징 정합성*''*

*''DB 커밋 + Kafka publish''* 가 *''*같은 트랜잭션 안에 못 들어감* (서로 다른 시스템)''* 라는 *근본 문제*. 해법:

```
@Transactional
void placeOrder(...) {
    orderRepository.save(order);              // ← DB
    outboxEventRepository.save(event);        // ← *같은 DB, 같은 트랜잭션*
    // Kafka publish 는 *''별도 *poller 가 outbox 읽고 발행*''*
}
```

*''Triple Idempotency''* (L1 outbox event_id unique → L2 processed_events PK → L3 DB unique 제약) 같은 *''*at-least-once + idempotent 수신*''* 패턴이 *''*복잡 도메인의 *정합성 기본 인프라*''*.

### 5.3. **JPA Leak 방지** — *''*ORM 이 도메인을 *오염시키지 않게''*''*

*''@Entity 가 *도메인 객체''* 인 *흔한 패턴* — *''편하지만 *위험*''*. *''*ORM lifecycle (detached, managed) 이 *도메인 의미와 충돌*''*. *''*lazy 로딩이 *비기능 요구사항에 *조용한 영향*''*.

대안:
- *''@Entity 는 *adapter 안*''*. *''*도메인은 *plain class*''*
- *''*adapter 에서 *@Entity ↔ Domain 객체 *명시적 변환*''*

이게 *''*초보에게 *부담* 같지만, *''*복잡 도메인 *6 개월 후* 에 *''*살아남는 코드베이스의 *공통점*''*.

### 5.4. **Spring Modulith Events** — *''*같은 모듈 안 *비동기 이벤트*''*

*''Order 가 끝나면 Notification 이 *알아서 반응*''* — *''메소드 직접 호출 (강결합)''* vs *''*이벤트 발행 (느슨한 결합)''*. *Modulith Events* 가 *''*같은 JVM 안* 이벤트 모델을 *Outbox + transaction 통합* 으로 제공*.

## 6. 기업 사례 — *''*복잡 도메인의 *구조 표준* 어떻게 박았나''*

### 6.1. **Netflix** — *''*Domain Graph Service (DGS) + *Backend-for-Frontend*''*

Netflix 는 *''마이크로서비스 *수 백 개''*''*. *''각 서비스가 *독립 bounded context*''*. *''*Federation 패턴* 으로 *클라이언트가 *한 GraphQL 로 보지만 *내부적으론 *서비스 별 *domain *분리''*''*. *''DGS framework''* 가 *Spring + Netflix-internal* 표준.

### 6.2. **Stripe** — *''*Idempotency Key + Event sourcing*''*

*''*결제 API 의 *모든 호출* 이 *Idempotency-Key 헤더''* 를 받음*. *''*재시도가 *부수효과 없음*''* 이 *''API 표준 그 자체''*. *''*복잡 결제 도메인의 *정합성을 *언어 차원에서 박았다''*''*.

### 6.3. **Amazon** — *''*2-pizza team + *Service ownership*''*

*''*한 팀이 *한 서비스의 *life cycle 전부 책임 (You build it, you run it)''*''*. *''*서비스 경계 = bounded context = 팀 경계''* 의 *''*3 중 정렬*''*. *''Werner Vogels 의 *''Architecting for the Cloud''*''* 가 그 *''*공식 문서*''*.

### 6.4. **GitHub** — *''*12-factor + Monolith first (Rails)*''*

GitHub 의 *''*monolith first → 분리 *느리게*''* 전략. *''*Rails monolith 가 *15 년째 운영 중''*''*. *''*''*마이크로서비스가 *항상 답이 아니다*''*''* 의 *''*반례적 *증거*''*.

### 6.5. **한국 기업**

- **카카오** — *''*카카오 Tech Blog 의 *DDD 시리즈*''*. *''*카카오페이의 *결제 도메인 *bounded context 분리*''*
- **쿠팡** — *''*''*Java + Spring + 마이크로서비스* 표준화*''*. *''*Coupang Tech blog''* 가 *''서비스 표준 = 회사 자산*''* 입증
- **토스** — *''*''*Silo 단위 *bounded context*''*''*. *''*제품팀 자율 + *기술 기준 표준 (Toss Tech) 합의*''*
- **우아한형제들 (배민)** — *''*MSA + DDD 의 *공개적 *진화 사례*''*. *''*우아한 형제들 기술 블로그*''* 가 *''*업계 표준 학습 자원*''*
- **라인** — *''*''*Engineering Excellence''*''*. *''*Java/Kotlin 헥사고날 + Spring Modulith *조기 채택''*
- **컬리** — *''*''*복잡 물류 도메인 + 정합성*''*''*. *''*Outbox + idempotency 의 *모범 케이스*''*

### *공통점*

*''*기술 자체가 아니라 *''*경계 (bounded context) 와 의존 방향 (dependency direction) 의 *원칙* 을 *''*문서·코드·CI·온보딩''* 의 *4 가지 형태로 박았다''*''*. *''*외부에서 보면 *서비스 분리* 인데, 내부에서 보면 *언어 + 모듈 + 데이터 정합성* 의 *3 중 표준*''*.

## 7. *''표준을 *팀이 따르게* 만드는*'' 메커니즘*

### 7.1. *4 가지 강제 메커니즘*

| 메커니즘 | 도구 | 강제력 |
|---|---|---|
| **컴파일** | Spring Modulith package boundary | 컴파일 에러 |
| **CI gate** | ArchUnit, JQAssistant | merge 전 차단 |
| **리뷰 체크리스트** | PR template | 사람 판단 |
| **온보딩** | cookiecutter, archetype | 신입의 *''첫 commit''* 이 *표준대로* |

*''4 단계가 *모두 작동해야 *''*표준이 *진짜로 강제 됨*''*. *''*ArchUnit 만 있고 *PR template 없으면''* 신입이 *''*ArchUnit 통과만 하면 OK''* 라 *''*도메인 의미적 위반''* 을 *알아채지 못함*.

### 7.2. *''*시니어가 *직접 짜는 것* 보다 *''*표준을 *코드화*''* 하는 일''* 이 *''*시간 대비 *팀 영향* 이 *100 배''*''*

*''*시니어가 *''*직접 *복잡한 feature 를 *짜면''*''* — 그 feature 만 *''*잘 됨*''*. *''*시니어가 *''*ArchUnit 룰 +  cookiecutter template + PR template 을 *박으면*''*''* — *''*팀 *모든 신규 코드* 가 *''*올바른 모양''* 으로 *자동 생성됨*''*.

## 8. *생성형 AI 시대* — *헥사고날 + AI 의 *진짜 의미***

### 8.1. *''*AI 가 *코드 짜는 것* 보다 *''*경계 어기는*''* 게 *더 위험*''*

Cursor·Copilot·Claude Code 의 *''*1 차 출력''* 은 *''*잘 짜는 듯 보이지만 *''*레이어 위반 (예: 도메인에 @Autowired)''* 을 *''*조용히 도입''*''*. *''*인간 리뷰가 안 잡으면 *기술 부채 폭증''*''*.

*''*ArchUnit + Modulith 가 박혀있는 코드베이스에선 *''*AI 가 만든 위반 코드가 *''*CI 에서 즉시 fail*''*''* — *''*AI 시대에 *구조 강제가 *훨씬 더 중요*''* 해진* 이유*.

### 8.2. *''*AI 의 *context* 를 *''*헥사고날 layer 단위로 한정''*''* — *정확도 폭발*

*''*Claude 에 *''*''*전체 *프로젝트 코드 다 보여줘''*''*''* → *''*모델이 *어디서 답을 찾을지 *모름*''*. 그러나 *''*''*''*domain/order 하위 코드만 보여줘''*''*''* → *''*답이 *명확히 *경계 안''*''*.

= **bounded context 가 *AI prompt 의 *context window 절감 단위*''***. 코드베이스가 *''*잘 잘려있을수록''* AI 정확도가 *''*비례 *상승''*''*.

### 8.3. *''*Ubiquitous Language 가 *AI 의 *vocabulary*''***

*''*''*Order 가 *cancel 되었다*''*''* 가 *''*결제 컨텍스트''* 와 *''*배송 컨텍스트''* 에서 *''*''*다른 의미*''*''* — *''*AI 가 *''*어느 컨텍스트의 *cancel 인지* 알려면 *''*ubiquitous language *문서 (context map)''* 가 *''*''*prompt 의 일부* 가 되어야* 한다*''*.

= **DDD 의 *context map* 이 *AI 시대에 *''*문서가 아니라 *실행 데이터*''*''***.

### 8.4. *''*Port 인터페이스가 *agent tool 의 *contract*''*

*''*AI agent 가 *''*도메인을 호출''* 할 때 *''*직접 코드를 호출하지 않고 *''*port 인터페이스 (의도)* 만 호출* — *''*adapter 가 *agent 일 수도, 사람일 수도, 다른 서비스일 수도''*''*. *''*Port 가 *''*MCP (Model Context Protocol) tool definition*''* 으로 *직접 변환 가능*''*.

```java
// port (도메인 정의)
interface PlaceOrderUseCase {
    OrderResult execute(PlaceOrderCommand cmd);
}

// MCP tool — *같은 의도, 다른 표현*
{
  "name": "place_order",
  "description": "Place an order with idempotency key",
  "inputSchema": { "command": { ... } }
}
```

*''*Port 정의 = MCP tool 정의''* — *''*같은 *도메인 의도를 *두 형태로 동시 표현*''*. *''*AI 시대에 *port 가 *''*문서가 아니라 *agent 와 *사람이 *공유하는 contract*''*''*.

### 8.5. *''*Verifiable Boundary'' — *AI 결과의 *검증 단위*''*

*''*AI 가 *port 를 호출* 했을 때 *''*''*그 결과가 *''*올바른지 어떻게 알지*''*''* — *''*domain 의 *''*invariant (불변식)''* 이 *''*검증 함수''*''*. *''*Hexagonal 의 *''*domain core 에 *invariant 가 박혀있다면''*''* — *''*AI 출력이 *''*그 invariant 위반시 *자동 reject*''*''*.

= **invariant 가 *''*AI 시대의 *guardrail*''***.

## 9. *향후 5 년* 의 *방향 7 가지*

### 9.1. *''*Architecture-aware codegen*''*

agent 가 *''*ArchUnit 룰을 알고 *''*그 규칙 안에서만* 생성''*''*. *''*''*Cursor Rules / Claude Code AGENTS.md''* 가 *''*초기 모습''*. *향후 *''*''*룰을 *컴파일러처럼* 강제''*''*.

### 9.2. *''*ArchUnit-as-prompt*''*

*''*ArchUnit 룰이 *prompt 의 *시스템 메시지로 자동 주입*''*. *''*''*프로젝트의 *modular boundary 가 *agent 의 *first-class context*''*''*.

### 9.3. *''*Bounded context 가 *fine-tuning 데이터 단위*''*

*''*같은 context 안 코드들로 *''*전용 *embedding/fine-tune*''*''*. *''*다른 context 코드는 *''*다른 vector space 안''*''*. *''*''*''*context bleed*''* (다른 context 단어를 잘못 가져오는 문제) 자동 차단''*''*.

### 9.4. *''*Port 인터페이스가 *agent tool registry 의 *source of truth*''*

*''*개발자가 *port 를 정의하면''* — *''*자동으로 *''*MCP tool, OpenAPI, gRPC proto, Spring Cloud Function*''* 4 개로 *동시 생성''*''*. *''*''*도메인 의도가 *''*표현 형식을 *횡단''*''*''*.

### 9.5. *''*DDD ubiquitous language 가 *embedding 인덱스 단위*''*

*''*''*context map 의 *''*용어집''* 이 *''*RAG retrieval 의 *primary key*''*''*''*. *''*같은 *cancel* 도 *''*''*결제 cancel vs 배송 cancel*''* 이 *''*다른 인덱스 partition*''*''*.

### 9.6. *''*Hexagonal CI ↔ AI Review 통합*''*

CI 의 *''*ArchUnit + Modulith + Outbox 검증''* 결과가 *''*''*AI 가 *PR 리뷰할 때 *맥락 자동 주입*''*''*. *''*''*''*''*''*이 PR 이 *Outbox 패턴을 *어겼는지*''*''*''*''*''* 를 *''*human + AI 가 *같은 데이터로 판단*''*.

### 9.7. *''*Domain Event 가 *agent triggering 의 단위*''*

*''*''*OrderPlaced 이벤트가 발행되면 → notification agent 가 자동 실행*''*''*. *''*''*''*hexagonal 의 outbound port (이벤트 발행) 가 *''*agent loop 의 *event source*''*''*''*''*. *''*''*Spring Modulith Events + LangChain4j + Spring AI''* 가 *''*''**같은 추상의 *세 표현*''*''*.

## 10. *시니어 백엔드의 *실천 가이드** — 단계별 *4 분기 계획*

### Q1 — *''*기초 구조 박기''*

- 패키지 구조 *''*domain / application / adapter (in/out)''* 표준화
- *''*ArchUnit 4-5 룰 *''*(도메인 → Spring 의존 금지, application → JPA 직접 금지, adapter cross-domain 금지)*''*''*
- *''*Spring Modulith 도입 *''*(monolith 안 모듈 경계)''*''*
- *''*PR template + 리뷰 체크리스트''*

### Q2 — *''*도메인 정합성 인프라''*

- *''*Outbox pattern *''*(이벤트 발행)''*''*
- *''*Triple idempotency *''*(L1 outbox + L2 processed + L3 DB unique)''*''*
- *''*Domain event + Modulith events''*
- *''*Audit trail *''*(*''*who-what-when 의 *''*불변 기록*''*''*''*)*''*

### Q3 — *''*AI 시대 *프롬프트 친화 구조''*

- *''*AGENTS.md / Cursor Rules / Claude Code instructions''*
- *''*ArchUnit 룰을 *''*natural language description*''* 으로 별도 문서화 (AI 가 읽기 위함)
- *''*Port 인터페이스를 *''*OpenAPI + MCP tool''* 로 *''*자동 export*''*

### Q4 — *''*Agent 통합 + 측정''*

- *''*PR review agent *''*(헥사고날 위반 자동 지적)*''*''*
- *''*Test generation agent *''*(domain invariant 기반 property-based test)*''*''*
- *''*''*Architecture decision agent*''* — RFC 자동 분석
- *''*DORA + AI-mediated metric 측정''*

## 11. *''*기술 기준 (technical standard) 제시*''* — 시니어의 *''*4 가지 산출물*''*

### 11.1. **Architectural Decision Record (ADR)**

*''*''*결정의 이유* 가 *''*결정 자체*''* 보다 오래 산다*''*''* — *Michael Nygard 의 *원칙*. *''*''*ADR 0001 — Why Hexagonal*''*''*, *''*''*ADR 0042 — Why Outbox over Saga*''*''* 같은 *''*결정의 history*''*''*. *''*''*5 년 뒤 신입이 *''*같은 *틀린 결정* 을 다시 안 하기 위함*''*''*''*.

### 11.2. **Coding Standard + Lint + ArchUnit**

*''*''*문장이 아니라 *''*컴파일러로 *강제*''*''*''*''*. *''*신입이 *''*첫 commit 부터 *표준 위반 0*''*''*''*.

### 11.3. **Reference Application (cookiecutter / archetype)**

*''*''*신규 서비스 *''*명령 한 줄 (gradle init + 회사 archetype)*''*'' 으로 *''*''*표준 구조 + 표준 의존 + 표준 모니터링 *전부 박힘*''*''*''*. *''*신입의 *''*첫 1 주''*''* 가 *''*''*표준 학습 *제로''*''*''*.

### 11.4. **Onboarding Playbook + Pairing**

*''*''*문서 + 도구 + 사람''* 의 *''*''*3 중 정렬*''*''*. *''*''*시니어가 *''*신입과 *pair* 로 *''*''*첫 feature*''*''*''* 를 짜는 *''*''*1-day 의례*''*''*''* — *''*''*무엇을 잘못해도 *되는지*''*''* 의 *암묵 기준 전수*''*.

## 12. *결론* — *''*구조가 *기능* 의 *재현성* 을 만든다*''*

*''*''*복잡 도메인의 *정합성과 확장성*''*''* 은 *''*''*아무리 *천재가 한 명* 있어도 *''*그 한 명이 *떠나면 무너진다''*''*''*''*. 무너지지 않게 만드는 일 = *''*''*구조 표준''*''*. 구조 표준의 *''*''*4 가지 도구*''*''* — *''*''*ADR + ArchUnit + Reference + Onboarding*''*''*.

*''*Java/Spring + 헥사고날 + DDD''* 는 *''*''*그 *4 가지 도구를 *가장 잘 받쳐주는 *기술 스택*''*''*. *''*''*Spring 의 DI + Modulith 의 boundary + Java 21 의 sealed/record + ArchUnit 의 CI 강제''*''* 가 *''*''*''*완벽한 *반복 가능 구조 표준''*''*''*''* 의 *''*''*기반*''*''*.

*생성형 AI 시대* — *''*''*''*이 구조가 *깨지지 않는 게 *더 중요해진다*''*''*''*''*. AI 가 *''*''*1 차 코드 짜기는 잘하지만 *''*''*경계 어기는 건 잘 못 깨닫는다*''*''*''*''*. *''*''*ArchUnit + Modulith + Outbox + Domain Event 가 박혀있어야 *''*''*''*AI 생성 코드 자체가 *''*''*''*''*표준 안에서 안전*''*''*''*''*''*''*.

*시니어 백엔드의 *진짜 일* * = *''*''*''*기능을 *직접 짜는 일* 이 아니라 *''*''*''*기능을 *어떻게 안전하게 *반복 생성할 수 있는 *틀* 을 만드는 일*''*''*''*''*''*''*. 그리고 *''*''*''*그 틀이 *AI 와 사람 모두에게 *같은 contract 가 되는 시대''*''*''*''* 가 *''*''*''*2026 년 이후의 *백엔드 시니어 영역*''*''*''*''*.

> *''*''*''*''*''*''*''*Architecture is the *decisions you wish you could get right early in a project*. *''*''* — *Ralph Johnson*''*''*''*''*. *''*''*''*AI 시대에 그 *''*''*''*early decisions 이 *''*''*''*''*agent contract 가 된다*''*''*''*''*''*''*''*''*.

---

## 더 읽을 거리

- *Domain-Driven Design* — Eric Evans, 2003
- *Implementing Domain-Driven Design* — Vaughn Vernon, 2013
- *Hexagonal Architecture* — Alistair Cockburn, 2005 (블로그 글)
- *Clean Architecture* — Robert C. Martin, 2017
- *Patterns of Enterprise Application Architecture* — Martin Fowler, 2002
- *Spring Modulith Reference* — *https://docs.spring.io/spring-modulith/reference/*
- *ArchUnit User Guide* — *https://www.archunit.org/userguide/html/000_Index.html*
- *Microservices Patterns* — Chris Richardson, 2018 (Outbox, Saga 등)
- *Anthropic — Building effective agents* — 2024
- *Model Context Protocol Specification* — Anthropic, 2024
- *Cursor Rules / Claude Code AGENTS.md 문서* — agent-friendly 코드베이스 설계

*다음 글 예고: AGENTS.md + ArchUnit + Spring Modulith 를 *한 코드베이스에 *통합* 한 reference template — *''복잡 도메인을 *AI 시대에도 안전하게 확장하기 위한*''* 실전 셋업*
