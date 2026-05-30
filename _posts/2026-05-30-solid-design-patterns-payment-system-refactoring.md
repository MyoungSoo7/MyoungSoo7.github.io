---
layout: post
title: "SOLID 원칙 × 디자인 패턴 — *결제 처리 시스템* 으로 보는 *왜 그 패턴이 그 자리* 인지"
date: 2026-05-30 12:35:00 +0900
categories: [reflection, software-engineering, refactoring]
tags: [solid, design-patterns, strategy, factory, decorator, dip, ocp, srp, spring-boot, java, kotlin, ddd, hexagonal]
---

"SOLID 5원칙 외웠고 GoF 23개 패턴도 안다. 근데 *실전에서 어디에 써야 할지* 모르겠다." — 이게 *교과서로만 배운* 사람의 가장 흔한 막힘.

원칙과 패턴은 *자주 함께 등장* 하고, *서로를 보조* 한다. SOLID 는 *방향성* 이고 패턴은 *구체적 도구*. *왜 그 패턴이 그 자리에 와야 하는지* 는 결국 *어떤 SOLID 원칙을 지키기 위함이냐* 로 환원된다.

본 글은 *결제 처리 시스템* 한 가지 예제로 *Before / After* 코드를 보여주며, *각 단계마다 어떤 SOLID + 어떤 패턴이 왜 적용됐는지* 를 *추적 가능하게* 설명한다.

> 본 글은 *고찰* 이다. 코드는 *교육용 축약본*. 실 운영 코드와는 표현이 다를 수 있어요.

---

## TL;DR

| 단계 | 문제 | SOLID 원칙 | 적용 패턴 |
|---|---|---|---|
| 1 → 2 | 한 클래스에 *결제 분기 + DB + 외부 호출* 다 섞임 | **SRP** (Single Responsibility) | 책임 분리 |
| 2 → 3 | 새 결제수단 추가 시 *if-else 거대화* | **OCP** (Open-Closed) | **Strategy** |
| 3 → 4 | 외부 PG API 가 *Service 와 직접 결합* | **DIP** (Dependency Inversion) | **Port & Adapter** |
| 4 → 5 | Strategy 생성 로직이 *호출자에 노출* | (캡슐화) | **Factory** |
| 5 → 6 | 모든 결제에 *로깅·재시도* 박혀있음 | **OCP**, **SRP** | **Decorator** |

---

## 0. 예제 도메인 — *결제 처리* 한 줄 요약

```
사용자가 주문 결제 요청 → 결제수단별 처리 → DB 기록 → 알림 발송
```

도메인은 단순하지만, *결제수단의 다양성* (카드, 계좌이체, 토스페이, 네이버페이, 가상자산...), *외부 PG 변경*, *로깅·재시도·메트릭* 같은 *횡단 관심사* 가 *코드를 빨리 망친다*. SOLID + 패턴이 *왜 필요한지* 가 자연스럽게 드러나는 도메인.

---

## 1. *Before* — "동작은 하는" 코드

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentRepository repo;
    private final RestTemplate restTemplate;
    private final NotificationService notification;

    @Transactional
    public PaymentResult pay(PaymentRequest req) {
        // 1. 결제수단별 분기
        if (req.getMethod() == PaymentMethod.CARD) {
            // 카드사 API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                "https://api.kakaopay.com/pay",
                Map.of("orderId", req.getOrderId(), "amount", req.getAmount()),
                String.class
            );
            log.info("Card payment requested: {}", req.getOrderId());
            // 재시도 로직...
            if (response.getStatusCode() != HttpStatus.OK) {
                throw new PaymentFailedException("Card failed");
            }
            // 응답 파싱...
        } else if (req.getMethod() == PaymentMethod.TOSS) {
            ResponseEntity<String> response = restTemplate.postForEntity(
                "https://api.tosspayments.com/v1/payments",
                Map.of("orderId", req.getOrderId(), "amount", req.getAmount()),
                String.class
            );
            log.info("Toss payment requested: {}", req.getOrderId());
            // ...
        } else if (req.getMethod() == PaymentMethod.NAVER_PAY) {
            // 또 다른 분기
        } else {
            throw new UnsupportedPaymentMethodException(req.getMethod());
        }

        // 2. DB 저장
        Payment payment = new Payment(
            req.getOrderId(),
            req.getAmount(),
            req.getMethod(),
            PaymentStatus.SUCCESS
        );
        repo.save(payment);

        // 3. 알림
        notification.send(req.getUserId(), "결제 완료");

        return new PaymentResult(payment.getId());
    }
}
```

### 무엇이 문제인가
- 한 메서드에 *결제수단 분기 + 외부 API + 재시도 + DB + 알림* 다 섞임
- 새 결제수단 (페이코, 스마일페이) 추가 → *이 거대 메서드 또 수정*
- *카카오 API 응답 형식* 이 바뀌면 → *PaymentService 전체* 테스트 다시
- 단위 테스트하려면 *RestTemplate mock + DB mock + Notification mock* — 5분 만에 setup 만 100줄

이걸 *5단계에 걸쳐* 단계적으로 리팩토링하자. *각 단계마다 어떤 SOLID 원칙* 을 지키는지 명시.

---

## 2. SRP 적용 — *각자의 책임* 분리

**Single Responsibility Principle**: *한 클래스는 변경되는 *이유* 가 하나여야 한다.*

`PaymentService` 의 현재 변경 이유 = *5개* (결제수단 추가, API 변경, DB 스키마, 알림 방식, 비즈니스 규칙). 이걸 분리:

```java
// === Domain: 비즈니스 규칙만 ===
public class Payment {
    private final OrderId orderId;
    private final Money amount;
    private final PaymentMethod method;
    private PaymentStatus status;

    public static Payment requested(OrderId orderId, Money amount, PaymentMethod method) {
        if (amount.isZeroOrNegative()) {
            throw new InvalidAmountException(amount);
        }
        return new Payment(orderId, amount, method, PaymentStatus.PENDING);
    }

    public void markSuccess() {
        if (this.status != PaymentStatus.PENDING) {
            throw new IllegalStateException("Cannot succeed from " + status);
        }
        this.status = PaymentStatus.SUCCESS;
    }
}

// === Service: 오케스트레이션만 ===
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentRepository repo;
    private final PaymentGateway gateway;       // ← 외부 호출은 별도
    private final NotificationService notification;

    @Transactional
    public PaymentId pay(PaymentRequest req) {
        var payment = Payment.requested(req.getOrderId(), req.getAmount(), req.getMethod());
        gateway.charge(payment);
        payment.markSuccess();
        repo.save(payment);
        notification.send(req.getUserId(), payment);
        return payment.getId();
    }
}
```

### 효과
- *비즈니스 규칙 (금액 검증, 상태 전이)* 은 `Payment` 도메인 — Spring 없이 *순수 단위 테스트* 가능
- `PaymentService` 는 *3줄 오케스트레이션* — 외부 의존성 4개로 줄어듦
- *결제수단 분기* 는 아직 `PaymentGateway` 안에 — 다음 단계에서 분리

여전히 `PaymentGateway` 가 *모든 결제수단을 알아야* 함. 다음 OCP + Strategy 차례.

---

## 3. OCP + Strategy 패턴 — *새 결제수단 추가에 닫혀있고, 확장에 열려있게*

**Open-Closed Principle**: *기존 코드는 닫혀있고 (수정 안 함), 새 기능 추가는 열려있어야 한다.*

`PaymentGateway` 내부의 `if (CARD) ... else if (TOSS) ...` 는 *새 결제수단 = 코드 수정*. 패턴으로 빼면:

```java
// === 전략 인터페이스 ===
public interface PaymentStrategy {
    PaymentMethod supports();
    PaymentResult charge(Payment payment);
}

// === 각 결제수단별 구현 ===
@Component
public class CardPaymentStrategy implements PaymentStrategy {
    private final CardApiClient cardApi;

    @Override public PaymentMethod supports() { return PaymentMethod.CARD; }

    @Override public PaymentResult charge(Payment payment) {
        var response = cardApi.charge(payment.getOrderId(), payment.getAmount());
        return PaymentResult.from(response);
    }
}

@Component
public class TossPaymentStrategy implements PaymentStrategy {
    private final TossApiClient tossApi;
    @Override public PaymentMethod supports() { return PaymentMethod.TOSS; }
    @Override public PaymentResult charge(Payment payment) {
        var response = tossApi.charge(payment.getOrderId(), payment.getAmount());
        return PaymentResult.from(response);
    }
}

// === Gateway: 적합한 Strategy 선택만 ===
@Component
public class PaymentGateway {
    private final Map<PaymentMethod, PaymentStrategy> strategies;

    public PaymentGateway(List<PaymentStrategy> strategies) {
        this.strategies = strategies.stream()
            .collect(Collectors.toMap(PaymentStrategy::supports, s -> s));
    }

    public PaymentResult charge(Payment payment) {
        var strategy = strategies.get(payment.getMethod());
        if (strategy == null) {
            throw new UnsupportedPaymentMethodException(payment.getMethod());
        }
        return strategy.charge(payment);
    }
}
```

### 효과
- **새 결제수단 (페이코, 스마일페이) 추가** = `PayCoPaymentStrategy implements PaymentStrategy` *클래스 하나 추가*
- 기존 `PaymentGateway` / `CardPaymentStrategy` / `TossPaymentStrategy` *전혀 수정 안 함* ← OCP 충족
- Spring 이 *자동으로 List 주입* → 등록 코드도 필요 없음

### SOLID 원칙 동시 만족
- *OCP* — 확장 열림, 수정 닫힘
- *SRP* — 각 strategy 는 *한 결제수단만* 알면 됨
- *LSP* (Liskov) — 모든 Strategy 는 *substitutable*

---

## 4. DIP + Port/Adapter — *외부 API 와 도메인 분리*

**Dependency Inversion Principle**: *상위 모듈은 하위 모듈에 의존하지 말고, 둘 다 추상에 의존하라.*

지금 `CardPaymentStrategy` 가 `CardApiClient` (구체 구현) 에 직접 의존. *카카오페이 → 카드사 직접 통신* 으로 바뀌면 `CardPaymentStrategy` 수정 필요.

헥사고날 (Port & Adapter) 로 풀자:

```java
// === Port (인터페이스, 도메인 레이어) ===
public interface CardPaymentPort {
    PaymentResult charge(OrderId orderId, Money amount);
}

// === Adapter (외부 시스템별 구현, 인프라 레이어) ===
@Component
@RequiredArgsConstructor
public class KakaoPayCardAdapter implements CardPaymentPort {
    private final RestClient restClient;

    @Override
    public PaymentResult charge(OrderId orderId, Money amount) {
        var response = restClient.post()
            .uri("https://api.kakaopay.com/pay")
            .body(Map.of("orderId", orderId.value(), "amount", amount.toLong()))
            .retrieve()
            .body(KakaoPayResponse.class);
        return PaymentResult.success(response.getPaymentKey());
    }
}

// === Strategy: Port 에만 의존 ===
@Component
@RequiredArgsConstructor
public class CardPaymentStrategy implements PaymentStrategy {
    private final CardPaymentPort cardPort;       // ← 인터페이스
    @Override public PaymentMethod supports() { return PaymentMethod.CARD; }
    @Override public PaymentResult charge(Payment payment) {
        return cardPort.charge(payment.getOrderId(), payment.getAmount());
    }
}
```

### 효과
- *KakaoPay → 다른 PG (예: 나이스페이)* 로 바꾸려면 `NicePayCardAdapter implements CardPaymentPort` *새로 만들기만*
- `CardPaymentStrategy` 는 *전혀 수정 안 함*
- 테스트 시 `CardPaymentPort` 를 *fake 로 교체* → 외부 호출 없이 단위 테스트
- *settlement 도메인이 외부 PG 의 변경에 흔들리지 않음*

### SOLID 원칙
- *DIP* — Strategy 는 *구체적인 PG SDK* 가 아니라 *추상화 (Port)* 에 의존
- *OCP* — Adapter 추가는 *기존 Adapter / Strategy* 수정 안 함

---

## 5. Factory 패턴 — *Strategy 생성 복잡성 캡슐화*

지금 `PaymentGateway` 의 생성자에서 *모든 Strategy 를 List 로 받아* Map 으로 변환. 단순하지만 *Strategy 가 init 시 추가 설정 (예: 환경별 다른 PG)* 이 필요해지면 복잡해진다.

Factory 로 분리:

```java
@Component
@RequiredArgsConstructor
public class PaymentStrategyFactory {
    private final Map<PaymentMethod, PaymentStrategy> strategies;
    private final PaymentEnvironment env;       // dev, staging, prod

    public PaymentStrategyFactory(List<PaymentStrategy> all, PaymentEnvironment env) {
        this.strategies = all.stream()
            .collect(Collectors.toMap(PaymentStrategy::supports, s -> s));
        this.env = env;
    }

    public PaymentStrategy forMethod(PaymentMethod method) {
        var strategy = strategies.get(method);
        if (strategy == null) {
            throw new UnsupportedPaymentMethodException(method);
        }
        // 환경별 분기 / mock 주입 등 *생성 복잡성 여기 캡슐화*
        if (env.isDev() && method == PaymentMethod.CARD) {
            return new MockCardStrategy();  // dev 에선 mock
        }
        return strategy;
    }
}

// === Gateway 가 Factory 만 사용 ===
@Component
@RequiredArgsConstructor
public class PaymentGateway {
    private final PaymentStrategyFactory factory;

    public PaymentResult charge(Payment payment) {
        return factory.forMethod(payment.getMethod()).charge(payment);
    }
}
```

### 효과
- *환경별 다른 Strategy* (dev = mock, prod = 실제) 같은 *생성 복잡성* 이 Factory 안으로 캡슐화
- `PaymentGateway` 는 *생성을 모르고* 사용만 함

### 패턴의 본질
Factory 는 *"객체 생성 로직 자체가 비즈니스 로직" 일 때* 등장. *어떤 객체 종류 / 어떻게 초기화 / 언제 재사용* 같은 결정을 *호출자에서 분리*.

---

## 6. Decorator 패턴 — *로깅·재시도·메트릭* 횡단 관심사 분리

지금 각 Strategy 마다 *log.info("Card payment requested...")* 같은 코드가 들어있을 거다. 그리고 *재시도 / 메트릭 / circuit breaker* 도 필요. *모든 Strategy 에 같은 코드를 박는 건* SRP 위반 + OCP 위반.

Decorator 패턴으로 *바깥에서 감싸*:

```java
// === Decorator 기본 ===
@RequiredArgsConstructor
public class LoggingPaymentStrategyDecorator implements PaymentStrategy {
    private final PaymentStrategy delegate;
    private final MeterRegistry meters;

    @Override public PaymentMethod supports() { return delegate.supports(); }

    @Override public PaymentResult charge(Payment payment) {
        var start = System.nanoTime();
        log.info("Payment START: orderId={}, method={}, amount={}",
            payment.getOrderId(), payment.getMethod(), payment.getAmount());
        try {
            var result = delegate.charge(payment);
            log.info("Payment SUCCESS: orderId={}", payment.getOrderId());
            meters.timer("payment.duration", "method", payment.getMethod().name())
                .record(System.nanoTime() - start, TimeUnit.NANOSECONDS);
            return result;
        } catch (Exception e) {
            log.error("Payment FAILED: orderId={}, error={}",
                payment.getOrderId(), e.getMessage());
            meters.counter("payment.error", "method", payment.getMethod().name()).increment();
            throw e;
        }
    }
}

@RequiredArgsConstructor
public class RetryingPaymentStrategyDecorator implements PaymentStrategy {
    private final PaymentStrategy delegate;
    private static final int MAX_RETRIES = 3;

    @Override public PaymentMethod supports() { return delegate.supports(); }

    @Override public PaymentResult charge(Payment payment) {
        Exception lastError = null;
        for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                return delegate.charge(payment);
            } catch (TransientPaymentException e) {
                lastError = e;
                sleepWithBackoff(attempt);
            }
        }
        throw new PaymentExhaustedException(lastError);
    }
}

// === Factory 에서 Decorator 쌓기 ===
public PaymentStrategy forMethod(PaymentMethod method) {
    var base = strategies.get(method);
    if (base == null) throw new UnsupportedPaymentMethodException(method);
    
    // 안쪽부터: base → Retry → Logging
    return new LoggingPaymentStrategyDecorator(
        new RetryingPaymentStrategyDecorator(base),
        meters
    );
}
```

### 효과
- *각 Strategy 의 비즈니스 로직은 깨끗* — 로깅/재시도 코드 없음
- *새 횡단 관심사 (예: distributed tracing)* 추가 = *새 Decorator 클래스만* — 기존 코드 0 수정
- *Decorator 조합* 으로 *환경별 다른 동작* (dev = logging 만, prod = logging + retry + circuit breaker)

### SOLID 원칙
- *SRP* — 각 Decorator 는 *한 가지 횡단 관심사만*
- *OCP* — 새 횡단 관심사 = 새 Decorator
- *DIP* — Decorator 는 `PaymentStrategy` 추상화에 의존

---

## 7. *After* 전체 구조 — 한 화면 요약

```
PaymentService (도메인 오케스트레이션, 3줄)
  └─ PaymentGateway
       └─ PaymentStrategyFactory  ← 환경별 생성 결정
            └─ [LoggingDecorator(RetryDecorator(CardPaymentStrategy(CardPaymentPort)))]
                                                            ↑
                                          KakaoPayCardAdapter / NicePayCardAdapter
                                          (헥사고날 Port 의 구현체)

Payment (도메인 객체) — 순수 비즈니스 규칙
```

### 변경 시나리오별 영향
| 변경 | 수정해야 할 파일 |
|---|---|
| 새 결제수단 (페이코) 추가 | `PayCoPaymentStrategy` 1개 + `PayCoAdapter` 1개 |
| 카카오페이 → 나이스페이 교체 | `NicePayCardAdapter` 1개 (Strategy 무관) |
| 메트릭 항목 추가 | `LoggingDecorator` 1개 |
| 재시도 정책 변경 | `RetryingDecorator` 1개 |
| 환경별 mock 추가 | `PaymentStrategyFactory` 1개 |

*Before 의 한 메서드* 가 모든 변경에 흔들렸던 것과 대비. *변경의 파급 범위가 작아진 것* 이 SOLID + 패턴의 *진짜 ROI*.

---

## 8. 함정 — 이 모든 게 *언제* 과한가

위 구조는 *결제 도메인* 처럼 *변경이 잦고 규칙이 복잡한* 시스템에 적합. 만약 *3개월짜리 사이드 프로젝트* 또는 *결제수단 1개로 평생 안 늘어남* 이라면 *Before 코드도 OK*. 패턴은 *변경 가능성에 대한 보험* 이고, 보험은 *공짜가 아니다*.

### 적용 기준
- *변경 가능성이 *높음*? → 패턴 적용
- 외부 의존성이 *바뀔 가능성이 있음*? → DIP + Port/Adapter
- *같은 종류의 객체* 가 *여러 종류* 등장? → Strategy
- *횡단 관심사* (로깅, 메트릭, 재시도) 가 *많음*? → Decorator
- *생성 로직 자체가 비즈니스*? → Factory

YAGNI ("You Aren't Gonna Need It") 와 *적절한 추상화* 사이의 균형. *너무 일찍* 추상화하면 *과공학 (over-engineering)*, *너무 늦으면* 리팩토링 비용.

---

## 9. 결론 — *원칙 → 패턴* 의 일관된 길

### 5단계 리팩토링 한눈 정리

| 단계 | SOLID | 패턴 | 효과 |
|---|---|---|---|
| 1→2 | SRP | (책임 분리) | 비즈니스 규칙 단위 테스트 가능 |
| 2→3 | OCP | Strategy | 새 결제수단 추가 시 기존 코드 무수정 |
| 3→4 | DIP | Port & Adapter | 외부 PG 교체 비용 0 |
| 4→5 | (캡슐화) | Factory | 환경별 생성 복잡성 격리 |
| 5→6 | OCP, SRP | Decorator | 횡단 관심사 분리 |

### *왜 그 패턴이 그 자리* 인지 — 본질
- *변경의 단위* 가 무엇인지 식별 → 그 단위를 *분리할 수 있는 방향* 의 SOLID 원칙 선택 → 그 원칙을 *구체화하는 패턴* 적용

이게 *원칙 → 패턴* 의 일관된 길. 거꾸로 *"이 패턴 써볼까"* 부터 시작하면 *적합하지 않은 곳에* 패턴이 들어가서 *코드 복잡도만 증가*.

### *마지막* — 코드는 *3가지 차원* 에서 진화한다
1. *기능적 정확성* — 동작하는가?
2. *변경 용이성* — 6개월 뒤 추가가 쉬운가?
3. *의도 명확성* — 다른 사람이 읽고 이해할 수 있는가?

SOLID + 패턴은 *2번과 3번을 위한 도구*. *1번은 그 자체로는 보장 못 함*. 그래서 *테스트* 가 함께 가야 한다.

다음 글에선 *Decorator vs AOP* — Spring AOP 가 이미 있는데 *왜 명시적 Decorator* 가 더 좋을 때가 있는지를 정리할 예정.
