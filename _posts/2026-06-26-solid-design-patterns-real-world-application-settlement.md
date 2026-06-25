---
layout: post
title: "*기본기 강화* — *SOLID* 와 *디자인 패턴* 을 *실무 코드* 에 *어떻게 적용 했는가* — *Settlement 의 *살아있는 사례***"
date: 2026-06-26 04:00:00 +0900
categories: [oop, design-pattern, solid, architecture, settlement]
tags: [solid, srp, ocp, lsp, isp, dip, design-pattern, strategy, observer, command, outbox, hexagonal, archunit, settlement]
---

![기본기 강화 — 객체지향 설계 원칙(SOLID)과 디자인 패턴을 실무 코드에 어떻게 적용했는지 설명할 수 있어야 합니다](/assets/images/solid-design-patterns-fundamentals.jpg)

> *위 문장 은 *시니어 개발자 의 *면접관 의 평가 기준*. 또는 *내가 *내 코드 를 *PR 으로 *제출 할 때 *동료 가 보는 시선*.
>
> *"SOLID 가 뭔가요?"* 의 *암기 식 답* 이 아니라 — *"당신 의 코드 의 *어디 에 *어떻게 적용 했나"* 의 *증명*. *그게 *기본기 의 *진짜 깊이*.

이 글은 *SOLID 5 원칙* 과 *주요 디자인 패턴 들 (Strategy / Observer / Command / Template Method / Repository / Specification / Outbox)* 을 *내 *settlement 시스템 의 *실제 코드 와 함께 *풀어 낸다*. *추상 적 설명* 이 아니라 *내가 *왜 그렇게 짰는지* 의 *증명*.

내 *[객체지향 의 *역할 · 책임 · 협력*](/2026/06/21/object-oriented-role-responsibility-collaboration-deep-dive.html)* 의 *바로 다음 글*. *역할 / 책임 / 협력* 이 *철학* 이면 *SOLID + 패턴* 이 *그 *철학 의 *코드 의 문법*.

---

## TL;DR — *한 줄 결론*

> *SOLID 의 5 원칙* 은 *변경 의 비용 을 *낮추는 *5 가지 의 방향*. *디자인 패턴* 은 *그 방향 의 *반복 적 정답 의 *카탈로그*. *둘 다 *외우는 게 아니라 *적용 한 사례 로 *체화* 해야 *기본기*. *내 *settlement 의 *SellerTier · PaymentProcessor · Outbox · Read-only Projection · Chunk-Reader* 가 *그 *각각 의 살아있는 사례*. *ArchUnit 으로 *컴파일러 처럼 강제* 까지 도 — *기본기 의 *완성 의 신호*.

---

# Part 1. *SOLID — *5 원칙 의 실무 적용***

## 1. *S — Single Responsibility Principle (SRP)*

### 1.1 *원칙*

*"한 클래스 는 *변경 의 이유 가 *오직 하나"*. *책임 의 분리*.

### 1.2 *내 settlement 의 *분리***

*[어제 의 글](/2026/06/21/object-oriented-role-responsibility-collaboration-deep-dive.html)* 에서 본 *Settlement / Payout / Ledger* 의 분리 :

```kotlin
// === SRP 위반 — *돈 의 모든 일* 을 한 클래스 ===
class MoneyManager {
    fun calculateSettlement() { ... }
    fun processPayout() { ... }
    fun postLedgerEntry() { ... }
    fun reconcilePG() { ... }
    fun generatePdfReport() { ... }
    fun handleChargeback() { ... }
}
// → 6,000 줄 의 *God Class*. *어디 만 *변경 해도 *나머지 영향*

// === SRP 준수 — *책임 별 분리* ===
class Settlement { fun calculate(); fun confirm(); fun cancel() }
class Payout { fun start(); fun markCompleted(); fun markFailed() }
class Ledger { fun post(entry); fun balance() }
class PgReconciliation { fun reconcile() }
class SettlementReport { fun generatePdf() }
class Chargeback { fun open(); fun accept(); fun reject() }
```

### 1.3 *증명 — *변경 의 영향 범위*

*"수수료 정책 변경"* — `Settlement.calculate` 만 수정. *Payout / Ledger / Chargeback 영향 0*. *그게 *SRP 의 *진짜 가치*.

---

## 2. *O — Open/Closed Principle (OCP)*

### 2.1 *원칙*

*"확장 에는 열려있고 *변경 에는 닫혀있다"*. *새 케이스 가 추가 되어도 *기존 코드 변경 없음*.

### 2.2 *내 settlement 의 *셀러 등급 별 수수료***

```kotlin
// === OCP 위반 — if/else 체인 ===
class Settlement {
    fun commissionRate(tier: String): BigDecimal {
        if (tier == "NORMAL") return "0.035".toBigDecimal()
        if (tier == "VIP") return "0.025".toBigDecimal()
        if (tier == "STRATEGIC") return "0.020".toBigDecimal()
        // *새 등급 추가 할 때마다 *이 메서드 수정*
        throw IllegalArgumentException()
    }
}

// === OCP 준수 — Strategy + Sealed Interface ===
sealed interface SellerTier {
    val commissionRate: BigDecimal
    val defaultCycle: Int
    val holdback: HoldbackPolicy
    
    fun discountFor(amount: Money): Money
}

object Normal : SellerTier {
    override val commissionRate = "0.035".toBigDecimal()
    override val defaultCycle = 7
    override val holdback = HoldbackPolicy(rate = 0.30, days = 30)
}

object Vip : SellerTier {
    override val commissionRate = "0.025".toBigDecimal()
    override val defaultCycle = 3
    override val holdback = HoldbackPolicy(rate = 0.10, days = 14)
}

object Strategic : SellerTier {
    override val commissionRate = "0.020".toBigDecimal()
    override val defaultCycle = 1
    override val holdback = HoldbackPolicy(rate = 0.0, days = 0)
}

// 새 등급 *Platinum* 추가 시 — *새 object 만 추가*. *기존 코드 변경 0*
```

### 2.3 *증명 — *PR 의 *변경 범위***

새 등급 *Platinum* 추가 PR:
- ✅ `Platinum.kt` 추가
- ✅ 등록 의 *enum 또는 factory 한 줄*
- ❌ *Settlement / Payout / Calculator 의 *코드 변경 0*

*30 줄 PR* 로 *기능 추가 완성*. *OCP 의 *체감*.

---

## 3. *L — Liskov Substitution Principle (LSP)*

### 3.1 *원칙*

*"자식 클래스 는 *부모 의 *모든 약속 을 *지켜야 한다"*. *부모 의 *약속 보다 *덜 보장 하면 *대체 불가*.

### 3.2 *내 settlement 의 *PaymentProcessor***

```kotlin
interface PaymentProcessor {
    /**
     * @return PaymentResult — *반드시 *PaymentId 보장*
     * @throws PaymentDeclinedException — *결제 거절*
     */
    fun process(payment: Payment): PaymentResult
}

// === LSP 준수 ===
class TossPaymentProcessor : PaymentProcessor {
    override fun process(payment: Payment): PaymentResult {
        return tossClient.charge(payment).toResult()  // *약속 지킴*
    }
}

class KakaoPaymentProcessor : PaymentProcessor {
    override fun process(payment: Payment): PaymentResult {
        return kakaoClient.charge(payment).toResult()  // *약속 지킴*
    }
}

// === LSP 위반 — *약속 보다 *덜 보장* ===
class MockPaymentProcessor : PaymentProcessor {
    override fun process(payment: Payment): PaymentResult {
        if (Math.random() < 0.5) return null!!  // ❌ null 반환 — 부모 약속 위반
        if (payment.amount > 100_000) throw RuntimeException()  // ❌ 예외 타입 다름
        return PaymentResult.success()
    }
}
```

### 3.3 *증명 — *호출 자 의 *기대 가 *유지 되는가**

`Order.pay(processor)` 가 *TossPaymentProcessor / KakaoPaymentProcessor* 어느 것 으로 호출 되어도 *동일 한 *오류 처리 / 결과 처리* 의 *코드*. *그게 *LSP 의 *증명*.

---

## 4. *I — Interface Segregation Principle (ISP)*

### 4.1 *원칙*

*"클라이언트 가 *사용 하지 않는 메서드 에 *의존 하지 않게"*. *큰 인터페이스 의 분할*.

### 4.2 *내 settlement 의 *분할***

```kotlin
// === ISP 위반 — Repository 라는 이름 으로 *모든 것* ===
interface SettlementRepository {
    fun save(s: Settlement)
    fun findById(id: SettlementId): Settlement?
    fun findByPeriod(period: Period): List<Settlement>
    fun deleteAll()                          // *위험*. 사용자 가 *원하지 않음*
    fun generatePdf(id: SettlementId): ByteArray   // *책임 다른 일*
    fun reconcileAll()                       // *책임 다른 일*
}

// === ISP 준수 — *역할 별 분리* ===
interface SettlementWriter {
    fun save(s: Settlement)
}

interface SettlementReader {
    fun findById(id: SettlementId): Settlement?
    fun findByPeriod(period: Period): List<Settlement>
}

interface SettlementPdfGenerator {
    fun generate(s: Settlement): ByteArray
}

interface SettlementReconciler {
    fun reconcile()
}

// 클라이언트 는 *필요 한 것 만* 의존
class SettlementCreateService(
    private val writer: SettlementWriter,
    private val reader: SettlementReader,  // *PdfGenerator / Reconciler 안 봄*
) { ... }
```

### 4.3 *증명 — *Mock 의 *간결성**

*테스트 시* `SettlementCreateService` 의 mock — *writer + reader* 만 mocking. *PdfGenerator / Reconciler* 의 *불필요 한 stub* 없음.

---

## 5. *D — Dependency Inversion Principle (DIP)*

### 5.1 *원칙*

*"상위 모듈 은 *하위 모듈 에 의존 하지 않는다*. 둘 다 *추상* 에 의존*. "*

### 5.2 *내 settlement 의 *Hexagonal Port***

*[K8s Watch-Reconcile 글](/2026/06/20/kubernetes-control-loop-watch-reconcile-pattern-deep-dive.html)* 과 *[객체지향 글](/2026/06/21/object-oriented-role-responsibility-collaboration-deep-dive.html)* 의 *바로 그 *Port-Adapter 구조*.

```kotlin
// === DIP 위반 — 도메인 이 *JPA 에 직접 의존* ===
package github.lms.lemuel.settlement.domain

import org.springframework.data.jpa.repository.JpaRepository  // ❌ 도메인 → 인프라

class SettlementService {
    @Autowired lateinit var jpaRepo: JpaSettlementRepository
    fun create(...) { jpaRepo.save(...) }
}

// === DIP 준수 — 도메인 이 *Port 에 의존*, Adapter 가 *Port 구현* ===
// domain/application/port/out/
interface SettlementRepository {
    fun save(s: Settlement)
    fun findById(id: SettlementId): Settlement?
}

// adapter/out/persistence/
@Repository
class JpaSettlementRepositoryAdapter(
    private val jpaRepo: SpringDataSettlementRepository,
) : SettlementRepository {
    override fun save(s: Settlement) {
        jpaRepo.save(s.toEntity())
    }
    override fun findById(id: SettlementId): Settlement? =
        jpaRepo.findById(id.value).orElse(null)?.toDomain()
}
```

### 5.3 *증명 — *ArchUnit 으로 *컴파일러 처럼 강제**

내 *settlement* 의 `ArchitectureTest.kt` :

```kotlin
@Test
fun `domain 은 adapter 를 참조 하면 안 된다`() {
    noClasses()
        .that().resideInAPackage("..domain..")
        .should().dependOnClassesThat()
        .resideInAPackage("..adapter..")
        .check(classes)
}

@Test
fun `application 은 JPA 를 직접 import 하면 안 된다`() {
    noClasses()
        .that().resideInAPackage("..application..")
        .should().dependOnClassesThat()
        .resideInAPackage("javax.persistence..", "jakarta.persistence..", 
                          "org.springframework.data.jpa..")
        .check(classes)
}
```

*PR 마다 *CI 가 위 룰 검증*. *DIP 가 *문서 가 아니라 *컴파일러 의 검증*. *기본기 의 *완성 의 신호*.

---

# Part 2. *디자인 패턴 — *실무 적용***

## 6. *Strategy — *알고리즘 의 교체***

### 6.1 *위 의 *셀러 등급 이 그 자체***

*Section 2.2 의 SellerTier* 가 *Strategy 패턴 의 직접 예*. *Context (Settlement) 가 *Strategy (SellerTier) 의 선택* 으로 *런타임 행위 변경*.

### 6.2 *추가 사례 — *수수료 정책 변경***

```kotlin
interface CommissionPolicy {
    fun calculate(amount: Money, seller: Seller): Money
}

class FlatRatePolicy(val rate: BigDecimal) : CommissionPolicy { ... }
class TieredPolicy(val tiers: List<Tier>) : CommissionPolicy { ... }
class PromotionalPolicy(val basePolicy: CommissionPolicy, val discount: BigDecimal) : CommissionPolicy {
    override fun calculate(amount: Money, seller: Seller): Money =
        basePolicy.calculate(amount, seller) * (1 - discount)
}
```

*프로모션 적용 = *PromotionalPolicy 로 감싸기*. *기존 정책 코드 변경 0*. *OCP + Decorator 의 시너지*.

---

## 7. *Observer — *이벤트 의 *발행/구독***

### 7.1 *내 settlement 의 *Outbox 가 *그 자체***

*[Outbox 패턴 글](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)* 에서 자세히. *Observer 의 *분산 시스템 판*.

```kotlin
class Payment {
    fun capture() {
        this.status = CAPTURED
        // *Observer 의 *알림* — 이벤트 발행
        DomainEventPublisher.publish(PaymentCaptured(this.id, this.amount))
    }
}

// Subscribers (Listener) — 자기 책임 만
@Component
class SettlementEventListener {
    @EventListener
    fun on(event: PaymentCaptured) {
        settlementService.createFrom(event)
    }
}

@Component
class RewardEventListener {
    @EventListener
    fun on(event: PaymentCaptured) {
        rewardService.grantPointsFor(event.userId, event.amount)
    }
}
```

*Payment 는 *Settlement / Reward 의 존재 모름*. *느슨한 결합*. *Open/Closed 까지 만족*.

### 7.2 *Outbox 의 *Observer 의 확장*

*같은 패턴* 의 *분산 버전*:
- 도메인 이벤트 발행 → outbox_events 테이블 INSERT (동일 트랜잭션)
- Poller 가 *비동기 로 *Kafka 발행
- 다른 서비스 (settlement-service) 가 *Kafka 구독*

*프로세스 의 경계 를 넘어 도 *Observer*. *MSA 의 *기본 통신 패턴*.

---

## 8. *Command — *행위 의 *객체화***

### 8.1 *내 settlement 의 *사용***

```kotlin
// === Command 객체 ===
data class CreateSettlementCommand(
    val sellerId: SellerId,
    val period: Period,
    val payments: List<PaymentId>,
    val idempotencyKey: IdempotencyKey,
)

interface CreateSettlementUseCase {
    fun create(command: CreateSettlementCommand): SettlementId
}

// === 이점 ===
// 1. *재시도 가능* — Command 를 *큐* 에 넣었다 *다시 꺼냄*
// 2. *멱등성 보장* — idempotencyKey 가 *Command 의 일부*
// 3. *직렬화 가능* — JSON 변환 → Kafka 발행
// 4. *테스트 용이* — Command 객체 만 만들면 됨
```

### 8.2 *Outbox 의 *Command 의 직렬화*

*outbox_events 의 *각 row* 가 *직렬화 된 Command*. *poller 가 *deserialize → 재실행*. *failure 시 *재시도* 의 기반.

---

## 9. *Template Method — *불변 한 흐름 + 가변 한 step***

### 9.1 *내 settlement 의 *Spring Batch***

```kotlin
abstract class SettlementBatchStep<T> {
    fun execute() {
        // *불변 한 흐름*
        val items = read()
        val processed = items.map { process(it) }
        write(processed)
        log()
    }
    
    protected abstract fun read(): List<T>
    protected abstract fun process(item: T): T
    protected abstract fun write(items: List<T>)
}

// === 각 step 이 *가변 부분 만* 구현 ===
class MonthlySettlementStep : SettlementBatchStep<Payment>() {
    override fun read() = paymentRepository.findCapturedByMonth(month)
    override fun process(p: Payment) = settlementCalculator.from(p)
    override fun write(items: List<Settlement>) = settlementRepository.saveAll(items)
}
```

*공통 흐름 의 *중복 제거* + *각 step 의 *변동 부분 만 *명시*.

---

## 10. *Repository — *영속성 의 *추상화***

### 10.1 *DDD 의 *기본 패턴***

*[위 Part 1 의 *DIP 의 예시 * 가 *Repository 패턴 의 *Settlement 적용*. *도메인 이 *영속성 의 *세부 (JPA / MongoDB / Redis) 를 모름*.

### 10.2 *Read-only Projection — *읽기 모델 의 분리***

내 *settlement* 의 *고유 패턴*:

```kotlin
// settlement-service 가 order-service 의 코드 를 *import 하지 않고도*
// payments / orders 테이블 의 데이터 를 *읽음*

@Entity
@Immutable  // *읽기 전용*
@Table(name = "payments")
class SettlementPaymentReadModel {
    @Id val id: Long
    val sellerId: String
    val amount: BigDecimal
    val capturedAt: Instant
    // *order-service 의 *Payment Entity 와 *같은 테이블* 이지만 *독립 클래스*
}

interface SettlementPaymentReadModelRepository : Repository<SettlementPaymentReadModel, Long> {
    fun findBySellerIdAndCapturedAtBetween(sellerId: String, start: Instant, end: Instant): List<SettlementPaymentReadModel>
}
```

*CQRS 의 *간이 형*. *읽기 와 쓰기 의 *모델 분리*. *settlement 가 *order 에 *코드 의존 0*.

---

## 11. *Specification — *조건 의 *조합***

### 11.1 *복잡 한 쿼리 의 *조합***

```kotlin
interface SettlementSpec {
    fun matches(s: Settlement): Boolean
    fun and(other: SettlementSpec) = SettlementSpec { matches(it) && other.matches(it) }
    fun or(other: SettlementSpec) = SettlementSpec { matches(it) || other.matches(it) }
}

class HighValueSpec(val threshold: Money) : SettlementSpec {
    override fun matches(s: Settlement) = s.amount >= threshold
}

class VipTierSpec : SettlementSpec {
    override fun matches(s: Settlement) = s.seller.tier == Vip
}

class DateRangeSpec(val start: LocalDate, val end: LocalDate) : SettlementSpec { ... }

// 조합
val complex = HighValueSpec(Money.of(1_000_000))
    .and(VipTierSpec())
    .and(DateRangeSpec(start, end))

settlements.filter { complex.matches(it) }
```

*조건 의 *재사용 + 합성*.

---

## 12. *Outbox — *현대 MSA 의 핵심 패턴***

### 12.1 *Observer + Command + Repository 의 *합성***

*내 *[Outbox 패턴 글](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html)* 의 *전체 내용*. 핵심:

```kotlin
@Transactional
fun capture(payment: Payment) {
    payment.status = CAPTURED
    paymentRepository.save(payment)
    
    // *동일 트랜잭션* 에서 *outbox 에 *이벤트 저장*
    outboxRepository.save(OutboxEvent(
        eventId = UUID.randomUUID(),  // *멱등 키*
        topic = "payment.captured",
        payload = PaymentCaptured(payment.id, payment.amount).toJson()
    ))
}

// *Poller 가 *비동기 로 *Kafka 발행*
@Scheduled(fixedDelay = 2000)
fun publish() {
    val events = outboxRepository.claimPending(batchSize = 100)  // FOR UPDATE SKIP LOCKED
    events.forEach { kafkaTemplate.send(it.topic, it.payload) }
    outboxRepository.markPublished(events)
}
```

*패턴 의 합성* — *Observer (이벤트) + Command (직렬화) + Repository (저장) + Template Method (poll 흐름)*. *현대 백엔드 의 *교과서*.

---

# Part 3. *적용 의 *깊이 — *증명 의 *5 단계***

## 13. *기본기 의 *5 단계 의 *체득***

| 단계 | 의미 | 신호 |
|---|---|---|
| 1. *암기* | SOLID 의 *5 글자* 외움 | 면접 의 *짧은 답* |
| 2. *식별* | 코드 보고 *위반 여부* 판단 | 코드 리뷰 에서 *지적 가능* |
| 3. *적용* | 새 코드 작성 시 *원칙 의식* | PR 의 *구조 가 명확* |
| 4. *합성* | 여러 원칙 + 패턴 의 *조합 적 사용* | *Outbox 같은 *현대 패턴 자연 구사* |
| 5. *강제* | *ArchUnit / lint / CI 로 자동 검증* | *팀 전체 가 *기본기 의 *바닥 보장* |

내 *settlement* — *5 단계 까지 도달*. *ArchUnit 의 *3 가지 룰* 이 *모든 PR 의 컴파일러 검증*.

---

## 14. *면접 답변 의 *템플릿***

위 그림 의 *평가 기준* 에 대한 *내 답변 의 구조*:

```markdown
# 1. SOLID 의 *체득 단계*
*5 가지 다 외우 고 있고*, *settlement 에서 *5 가지 모두 적용*.

# 2. 구체 적 예
- SRP — Settlement / Payout / Ledger 의 분리
- OCP — SellerTier 의 sealed interface 로 *새 등급 추가 시 *기존 코드 변경 0*
- LSP — PaymentProcessor 의 *Toss / Kakao 의 *대체 가능*
- ISP — Reader / Writer 의 분리. *Mock 의 *간결성*
- DIP — Hexagonal 의 *Port-Adapter*. *ArchUnit 으로 *컴파일러 처럼 강제*

# 3. 디자인 패턴
- Strategy — SellerTier
- Observer + Command + Repository → *Outbox 의 *합성*
- Template Method — Spring Batch 의 *Chunk-oriented*
- Repository + CQRS Read Model — *settlement ↔ order 의 *코드 의존 0*

# 4. *강제 메커니즘*
ArchUnit 의 *3 가지 룰* 이 *팀 전체 의 *바닥 보장*.

# 5. *지속 적 개선*
*매 PR 마다 *기본기 의 *체크리스트*. *나의 *시야 가 *AI 로 일부 위임 되어도 *남는 영역*.
```

---

## 15. *맺음 *— *기본기 의 *진짜 의미***

*"SOLID 와 디자인 패턴 을 *실무 코드 에 *어떻게 적용 했는지* *설명 할 수 있어야 한다"* — *그림 의 *문장*.

*"설명 할 수 있어야 한다"* 의 *진짜 의미* :
- *암기 가 아니라 *내 코드 의 *구체 적 위치*
- *위반 의 *영향* 의 *체감*
- *원칙 의 *조합 적 사용*
- *팀 의 *바닥 보장 의 *강제 메커니즘*

*"SRP 는 단일 책임 원칙 입니다"* 의 답 — *암기 단계*. *"제 Settlement 의 *Payout 과 Ledger 의 분리 가 *SRP 의 예 이고*, *수수료 변경 시 *Payout 영향 0 의 의미 이고*, *그게 *ArchUnit 의 *...adapter.. → ..application.. 의존 차단 룰* 까지* — *5 단계 의 *체득*.

이 *차이* 가 *내 코드 의 *시니어 의 신호*. *그리고 *AI 시대 에 *살아남는 *시야 의 *기반*.

내일 *내 PR 의 *코드 한 줄 한 줄* 이 *위 5 가지 의 *어느 원칙 의 *어느 단계 의 적용 인가* — *내가 *설명 할 수 있다면*, *그게 *기본기*.

---

## 부록 — *오늘 *3 분 안 에 할 수 있는 *3 가지***

- [ ] *내 *최근 PR* 의 *코드 가 *SRP 위반 인지* 확인 (한 클래스 가 *변경 이유* 가 *몇 개* 인가)
- [ ] *내 *if/else 체인* 중 *Strategy 패턴 으로 *대체 가능 한 곳* 식별
- [ ] *내 프로젝트 의 *ArchUnit 룰 이 *존재 하는가*. *없다면 *3 가지 룰 부터 시작*

3 가지 중 *2 가지 가 *NO* 면 — *기본기 의 *2~3 단계* 에 머문 상태. *5 단계 로 가는 *오늘 의 *3 분*.

---

*관련 글*

- [*객체지향 의 *핵심 가치 — 역할 · 책임 · 협력*](/2026/06/21/object-oriented-role-responsibility-collaboration-deep-dive.html) — *SOLID 의 *철학 적 상위*
- [*Transactional Outbox 패턴 과 비동기 통합*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) — *Observer + Command + Repository 의 *합성 의 *현장*
- [*kubectl run 의 *Watch-Reconcile 패턴*](/2026/06/20/kubernetes-control-loop-watch-reconcile-pattern-deep-dive.html) — *DIP 의 *분산 시스템 판*
- [*DB 배치 처리 의 성능 향상 2 축*](/2026/06/21/db-batch-performance-covering-index-and-chunking.html) — *Template Method 의 *Spring Batch 실전*
- [*8 가지 체크리스트 로 settlement 자가 검수*](/2026/06/18/eight-checklist-self-audit-of-my-settlement-system.html) — *기본기 의 *5 단계 의 *체크 리스트*
- [*바이브 코딩 과 *시니어 의 *7 가지 기준*](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html) — *AI 시대 에 *남는 시야*
