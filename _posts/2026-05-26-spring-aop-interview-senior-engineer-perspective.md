---
layout: post
title: "Spring AOP — 무대 감독의 시선으로: 면접에서 점수 따는 답변과, 시니어가 *현장에서 다친 흔적*"
date: 2026-05-26 20:30:00 +0900
categories: [spring, backend, interview]
tags: [spring, aop, proxy, cglib, jdk-dynamic-proxy, transactional, aspect, interview, senior]
---

> 연극 무대를 상상해보세요. 배우(핵심 로직)는 연기에만 집중해야 합니다. 만약 배우가 직접 조명을 켜고, 배경 음악을 틀고, 퇴장할 때 막을 내린다면 연극이 엉망이 될 것입니다. AOP 는 무대 감독(*Aspect*)처럼, 배우가 언제 등장하고 퇴장하는지(*Pointcut*)를 지켜보다가, 적절한 타이밍에 조명과 음향(*Advice*)을 틀어주는 역할을 합니다.

이 비유 하나로 AOP 의 *전체 구조* 가 잡힌다. 하지만 면접에서 이 비유만 외워서 답하면 *''아 이 친구 책 읽었네''* 로 끝난다. 시니어가 평가하는 건 *''그 다음에 뭐가 나오느냐''* 다.

이 글은 *''AOP 가 뭐예요?''* 라는 질문에 대해, **주니어 답변** → **미들 답변** → **시니어 답변** 의 *세 층위* 로 정리한다. 그리고 시니어 레벨에서 면접관이 정말 듣고 싶어하는 *''그래서 production 에서 어떻게 다쳤어요?''* 의 사례 3 개를 푼다.

---

## 1. 주니어 답변 — *비유 + 핵심 용어* 까지

면접관이 *''AOP 가 뭔지 설명해보세요''* 라고 물으면 주니어는 보통 이렇게 답한다:

> *''관점 지향 프로그래밍이에요. 로깅이나 트랜잭션 같은 *공통 관심사* 를 비즈니스 로직에서 분리하는 방법입니다. Aspect, Pointcut, Advice 같은 용어가 있어요.''*

이 답변은 **합격선**. *''cross-cutting concerns''* 라는 단어를 알고 있다는 증거. 하지만 *''그래서 그게 어떻게 동작하는데요?''* 가 바로 이어진다.

### 1.1 비유를 *현실 코드* 로 연결

연극 비유를 그대로 코드로 옮기면:

```java
// 배우 (핵심 로직)
@Service
public class PaymentService {
    public PaymentResult charge(PaymentCommand cmd) {
        return chargeProvider.process(cmd);   // ← 결제만 한다
    }
}

// 무대 감독 (Aspect)
@Aspect
@Component
public class PaymentMonitoringAspect {

    // Pointcut: PaymentService 의 모든 public 메서드를 지켜본다
    @Pointcut("execution(public * com.lemuel.payment.PaymentService.*(..))")
    public void anyPaymentMethod() {}

    // Advice: 입장 전(Before) — 조명을 켠다
    @Before("anyPaymentMethod()")
    public void turnOnLights(JoinPoint jp) {
        log.info("결제 시작: {}", jp.getArgs());
        meter.counter("payment.attempts").increment();
    }

    // Advice: 퇴장 후(AfterReturning) — 음악을 튼다
    @AfterReturning(pointcut = "anyPaymentMethod()", returning = "result")
    public void playMusic(PaymentResult result) {
        log.info("결제 완료: {}", result);
        meter.counter("payment.success").increment();
    }

    // Advice: 사고 시(AfterThrowing) — 막을 내린다
    @AfterThrowing(pointcut = "anyPaymentMethod()", throwing = "ex")
    public void closeCurtain(Throwable ex) {
        log.error("결제 실패: {}", ex.getMessage());
        meter.counter("payment.failure").increment();
    }
}
```

PaymentService 는 *결제* 만 한다. 로깅, 메트릭, 알람 — 모두 *Aspect 가 옆에서 도와준다*. 배우는 자신의 대사에만 집중.

> *주니어 합격 포인트*: Aspect/Pointcut/Advice 의 *3 단어* 를 *코드로* 보여주기. 그 이상 깊이 들어가지 않아도 *''AOP 안다''* 는 인상.

---

## 2. 미들 답변 — *''내부적으로 어떻게 동작해요?''*

여기부터가 *진짜 면접*. 답이 *''proxy 가 감싸요''* 에서 끝나면 미들. *''어떤 proxy 인지, 언제 어느 게 쓰이는지, 한계가 뭔지''* 까지 가야 시니어.

### 2.1 Spring AOP = *Proxy 기반*

Spring AOP 는 *''Aspect 가 마법처럼 동작''* 하는 게 아니라 **proxy 객체** 를 만든다. PaymentService 를 직접 호출하는 것처럼 보이지만, 실제로는 *PaymentService 를 감싼 프록시 객체* 가 먼저 호출되고, 그 프록시가 *advice* 를 실행한 후 *진짜 PaymentService* 의 메서드를 위임 호출한다.

```
caller
   ↓ paymentService.charge(cmd)
[PaymentService$$ProxyByCGLIB]
   ├── Before advice (조명 켜기)
   ├── 실제 PaymentService.charge(cmd) 호출
   ├── AfterReturning advice (음악)
   └── (예외 시) AfterThrowing advice (막)
   ↓
caller (return)
```

### 2.2 *JDK Dynamic Proxy* vs *CGLIB* — *언제 어느 게 쓰이나*

Spring 의 기본 동작:

| 타겟 | 사용 Proxy | 조건 |
|---|---|---|
| 인터페이스 구현체 | **JDK Dynamic Proxy** | 타겟 클래스가 인터페이스를 구현 + Spring 5 까지 기본 |
| 인터페이스 없는 클래스 | **CGLIB** | 클래스 자체를 *상속* 해서 proxy 생성 |
| Spring Boot 2.x+ | **CGLIB 가 기본** | `proxy-target-class: true` 로 변경됨 |

> *미들 합격 포인트*: *''Spring Boot 는 CGLIB 가 기본''* 임을 아는 것. 옛 책들이 *''인터페이스가 있으면 JDK Dynamic Proxy''* 라고 가르치지만 Boot 2.x 부터는 그렇지 않다.

#### 두 방식의 *진짜 차이* — 면접에서 깊이 점수

```java
// JDK Dynamic Proxy 의 한계
public interface PaymentApi {
    PaymentResult charge(PaymentCommand cmd);
}

@Service
public class PaymentService implements PaymentApi {
    public PaymentResult charge(PaymentCommand cmd) { ... }

    // ❌ 인터페이스에 없는 메서드는 proxy 가 *못 감싼다*
    public void internalAdminMethod() { ... }
}
```

JDK Dynamic Proxy 는 *인터페이스의 메서드만* 가로챈다. 인터페이스에 없는 메서드는 *advice 가 적용되지 않는다*. 디버깅하기 정말 까다로운 함정.

CGLIB 는 *상속* 으로 동작하므로 *클래스의 모든 메서드* 를 가로챌 수 있다. 단 — `final` 메서드, `private` 메서드, `static` 메서드는 *상속이 불가능* 하므로 여전히 못 감싼다.

```java
@Service
public class PaymentService {
    
    // ✅ proxy 가 감쌈
    public PaymentResult charge(PaymentCommand cmd) { ... }
    
    // ❌ final → CGLIB 가 못 감쌈 (런타임 에러 또는 silent skip)
    public final PaymentResult chargeFinal(PaymentCommand cmd) { ... }
    
    // ❌ private → proxy 가 가로챌 수 없음
    private PaymentResult chargeInternal(PaymentCommand cmd) { ... }
}
```

### 2.3 Weaving — *언제 짜이는가*

| 방식 | 시점 | 도구 |
|---|---|---|
| Compile-time | 컴파일 단계 | AspectJ Compiler (`ajc`) |
| Load-time | 클래스 로딩 시 | AspectJ LTW + Java agent |
| **Runtime** | 빈 생성 시 (Spring 의 기본) | Spring AOP (Proxy 생성) |

Spring 이 채택한 *Runtime weaving* 의 장점은 *컴파일 도구 없이 동작* 하는 것. 단점은 *proxy 의 한계 그대로* — final/private/self-invocation 못 잡는다. *진짜 AspectJ* 가 필요하면 LTW 가야 한다. (실무에서는 *95% 가 Spring AOP 로 충분* 함)

---

## 3. 시니어 답변 — *''production 에서 어떻게 다쳤어요?''*

여기가 *''대화''* 가 시작되는 지점. *''AOP 잘못 써서 새벽에 일어났던 적 있어요?''* 같은 질문이 나오면, 답할 *흉터* 가 있어야 한다.

### 3.1 흉터 #1 — *self-invocation 의 함정* (가장 유명한 실수)

```java
@Service
public class OrderService {

    @Transactional
    public Order placeOrder(OrderCommand cmd) {
        validate(cmd);
        Order order = createOrder(cmd);
        sendNotification(order);   // ← 같은 클래스의 메서드 호출
        return order;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(Order order) {
        notificationLog.save(...);   // ← 새 트랜잭션 안에서 저장하길 기대
    }
}
```

*기대*: `sendNotification` 이 `REQUIRES_NEW` 라서 *별도 트랜잭션* 으로 동작.
*실제*: `sendNotification` 의 `@Transactional` 이 **무시된다**. notificationLog 가 *바깥 트랜잭션* 안에서 같이 저장되거나 같이 롤백된다.

#### 왜?

`placeOrder` 안에서 `this.sendNotification(...)` 을 호출하면 — 그건 *proxy 가 아닌 진짜 OrderService 인스턴스의 직접 호출*. proxy 는 *바깥에서 들어오는 호출만* 가로챈다. `this.` 는 그 proxy 를 우회한다.

#### 시니어가 보이는 답변

> *''이 케이스는 self-invocation 이라고 부르고요, proxy AOP 의 가장 큰 함정입니다. 해결은 세 가지가 있어요.''*

```java
// 해결 1 — 다른 빈으로 분리
@Service
public class NotificationService {
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void send(Order order) { ... }
}

@Service
public class OrderService {
    private final NotificationService notification;

    @Transactional
    public Order placeOrder(OrderCommand cmd) {
        ...
        notification.send(order);   // ← 빈 경계를 넘어가니 proxy 가 감쌈
    }
}

// 해결 2 — self-injection (덜 권장, 가독성 ↓)
@Service
public class OrderService {
    @Autowired @Lazy
    private OrderService self;

    @Transactional
    public Order placeOrder(OrderCommand cmd) {
        ...
        self.sendNotification(order);   // ← proxy 를 통한 호출
    }
}

// 해결 3 — AopContext 로 proxy 명시 가져오기 (가장 비권장)
@Service
@EnableAspectJAutoProxy(exposeProxy = true)
public class OrderService {
    @Transactional
    public Order placeOrder(OrderCommand cmd) {
        ...
        ((OrderService) AopContext.currentProxy()).sendNotification(order);
    }
}
```

> *시니어 합격 포인트*: 3 가지 옵션을 *모두 알고*, *왜 해결 1 이 권장인지* 의견을 갖는 것. *''관심사 분리 측면에서도 자연스러워서''*.

### 3.2 흉터 #2 — *Order 가 잘못된 Aspect 두 개* (조용한 버그)

```java
@Aspect
@Component
public class TransactionMonitoringAspect {
    @Around("@annotation(Transactional)")
    public Object measureTx(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.nanoTime();
        try {
            return pjp.proceed();
        } finally {
            meter.timer("tx.duration").record(System.nanoTime() - start);
        }
    }
}
```

문제: `@Transactional` 의 advice 와 `TransactionMonitoringAspect` 의 advice 가 *동일한 메서드* 에 모두 적용된다. **Order 가 안 정해지면** 어느 게 먼저 실행될지 *비결정적*.

특히 *내가 측정하려는 게 ''트랜잭션 시작부터 끝까지''* 인지 *''메서드 본체만''* 인지에 따라 순서가 중요. Spring 의 `@Transactional` 의 기본 order 는 `Ordered.LOWEST_PRECEDENCE` — *가장 안쪽* 에서 동작. 그 위를 감싸려면 *내 aspect 의 order 가 더 낮은 숫자* 여야 한다.

```java
@Aspect
@Component
@Order(1)   // ← @Transactional 보다 바깥 (1 이 더 우선)
public class TransactionMonitoringAspect { ... }
```

> *시니어 합격 포인트*: `@Order` 의 *''숫자가 작을수록 바깥''* 의미와, `@Transactional` 의 기본 order 를 *외우고 있는 것*. *''실제로 측정이 트랜잭션 끝나고 *commit 까지* 포함하는지 디버깅하다가 뒤집어진 적 있어요''* 같은 일화가 있으면 만점.

### 3.3 흉터 #3 — *@Async + @Transactional 이 같이 있으면* (조용한 데이터 손실)

```java
@Service
public class ReportService {

    @Transactional
    @Async
    public void generateReportAsync(Long userId) {
        var data = repo.findByUserId(userId);   // ← LazyInitializationException?
        ...
    }
}
```

기대: *비동기로 트랜잭션 안에서 동작*.
실제: *제대로 동작은 하지만*, `@Async` proxy 가 `@Transactional` proxy 를 *감쌌는지 그 반대인지* 에 따라 *트랜잭션 경계의 의미* 가 달라진다.

순서 분석:
- caller → `@Async` proxy → `@Transactional` proxy → 메서드 — *Async 가 별도 스레드에서 트랜잭션 시작*. 정상.
- caller → `@Transactional` proxy → `@Async` proxy → 메서드 — *호출자의 트랜잭션은 거기서 끝나고*, 새 스레드에서 *트랜잭션 없이* 실행. **bug**.

어느 쪽이 적용되는지는 *bean 등록 순서, proxy 종류, @Order* 에 따라 다르다.

#### 안전한 패턴

`@Async` 와 `@Transactional` 을 *같은 메서드* 에 붙이지 말고 *분리*:

```java
@Service
public class ReportService {
    private final ReportTransactionalService txService;

    @Async
    public void generateReportAsync(Long userId) {
        txService.generateReport(userId);   // ← 다른 빈, 새 스레드 안에서 트랜잭션 시작
    }
}

@Service
public class ReportTransactionalService {
    @Transactional
    public void generateReport(Long userId) { ... }
}
```

> *시니어 합격 포인트*: *''@Async + @Transactional 의 조합은 piggy 가 위험''* 이라는 *경험* 을 보이는 것. 그리고 *''저는 분리 패턴으로 갑니다''* 라는 *의견* 을 갖는 것.

---

## 4. 면접에서 *덜 다뤄지는* 시니어 시그널

### 4.1 *''AOP 를 안 써야 할 때''* 를 말할 수 있는가

좋은 시니어는 *''쓰는 법''* 보다 *''안 쓰는 법''* 을 안다. AOP 가 *over-engineering* 인 케이스:

- **단일 메서드에서만 필요한 cross-cutting** — Aspect 만들지 말고 그냥 메서드 안에서 처리. *''2 곳 이상에서 동일하게 필요''* 가 AOP 의 진입 조건.
- **타이트 루프 안의 메서드** — proxy 호출은 *직접 호출* 보다 *나노초 수준* 으로 느림. 100만 번 도는 루프 안의 메서드를 Aspect 로 감싸면 *측정 가능한* 오버헤드.
- **debugging 이 자주 필요한 메서드** — Aspect 가 끼면 stack trace 가 한 줄 더 길어지고, IDE 의 *''step into''* 가 *advice 안으로* 먼저 들어간다. 개발 경험 비용.

### 4.2 *''메타 어노테이션''* 으로 의도 표현

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Transactional
@Async
public @interface AuditedAsync {
}
```

이렇게 정의해두면 `@AuditedAsync` 한 줄로 *우리 팀의 비동기 + 트랜잭션 규약* 을 표현. 면접에서 *''메타 어노테이션을 어떻게 활용하셨어요?''* 라는 질문에 *''개인 어노테이션을 만들어서 팀의 표준 규약을 컴파일러 레벨로 강제했어요''* 같은 답이 *senior 시그널*.

### 4.3 *''AOP 의 디버깅 도구''*

면접관이 *''aspect 가 적용되는지 어떻게 확인하셨어요?''* 라고 물을 수 있다. 답할 거리:

```bash
# 1. 빈이 proxy 인지 확인
@Autowired
private OrderService orderService;

System.out.println(AopUtils.isAopProxy(orderService));      // true → proxy 임
System.out.println(AopUtils.isCglibProxy(orderService));    // true → CGLIB
System.out.println(AopUtils.isJdkDynamicProxy(orderService)); // true → JDK

# 2. Pointcut 매칭 확인 (Spring Boot)
logging.level.org.springframework.aop.framework=DEBUG

# 3. 실행 trace
debug:
  pjp.getSignature().getName()       # 메서드명
  pjp.getTarget()                    # 원본 빈
  Arrays.toString(pjp.getArgs())     # 인자
```

이런 *''AopUtils 가 있어요''* 같은 *''아 그런 API 가 있구나''* 시그널이 시니어 점수.

---

## 5. *면접관 입장* 에서 평가 그리드

내가 다른 후보를 평가할 때 쓰는 *암묵적 그리드*:

| 항목 | 주니어 | 미들 | 시니어 |
|---|---|---|---|
| 비유로 설명 가능? | ✓ | ✓ | ✓ |
| Aspect/Pointcut/Advice 알고 있음? | ✓ | ✓ | ✓ |
| Proxy 기반인 걸 아는가? | △ | ✓ | ✓ |
| JDK Proxy vs CGLIB 의 *기본 동작 변화* (Boot 2.x+) | ✗ | ✓ | ✓ |
| self-invocation 함정 | ✗ | △ | ✓ |
| `@Order` 가 advice 순서 결정 | ✗ | △ | ✓ |
| `@Async` + `@Transactional` 의 위험 | ✗ | ✗ | ✓ |
| *''AOP 를 안 써야 할 때''* 의견 | ✗ | ✗ | ✓ |
| 자신만의 *흉터* 일화 | ✗ | ✗ | ✓ |

위에서 *시니어 칸* 의 5 개 중 *3 개 이상* 이 자연스럽게 나오면 *''이 사람 시니어가 맞네''* 의 인상.

---

## 6. 정리 — *3 줄 응답 템플릿*

면접 끝에 *''AOP 한 문장으로 정리해주세요''* 같은 요청에:

> *''AOP 는 cross-cutting concern 을 proxy 기반으로 분리하는 방법입니다. Spring 에서는 CGLIB proxy 가 기본이고, self-invocation·@Order·@Async/@Transactional 조합에서 자주 다칩니다. 저는 ''같은 패턴이 2 곳 이상에서 반복될 때만 Aspect 로 빼고, debugging 비용을 신중하게 평가합니다.''*

이 3 줄에 *시니어 시그널 5 개* 가 다 들어있다 — *proxy*, *CGLIB*, *self-invocation*, *order*, *cost-aware*.

---

## 마무리

처음의 비유로 돌아가자. 무대 감독은 배우보다 *보이지 않는다*. 좋은 AOP 도 그렇다 — *비즈니스 로직 안에 흔적이 없고*, *Aspect 만 보면 ''이 시스템의 cross-cutting 정책''* 이 한눈에 보인다.

하지만 무대 감독이 *무능하면* 조명이 늦게 켜지고, 음악이 어울리지 않게 울리고, 막이 잘못된 타이밍에 내려진다. AOP 도 *서툴게 쓰면* self-invocation 으로 트랜잭션이 풀리고, order 가 꼬여서 메트릭이 잘못되고, @Async 와 함께 써서 데이터가 사라진다.

*''어떻게 쓰느냐''* 보다 *''언제 안 쓰느냐''*, *''어디서 다치는가''* 를 아는 게 시니어. 면접관도 같은 질문을 던진다 — *어디서 다치셨어요?*

---

> 작성: 2026-05-26. Spring Boot 3.x / 4.x 기준. 실제 프로젝트(*lemuel-xr*, *settlement*, *asat*)에서 AOP 로 다친 사례 3 개 + 안 다친 패턴 1 개로 구성.
