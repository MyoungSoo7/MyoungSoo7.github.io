---
layout: post
title: "*Spring *AOP* — *@Aspect 와 *Pointcut* 을 *시니어가 *주니어에게 *''*카페에서 *예제로 *조곤조곤""* 설명하는 *글"
date: 2026-06-06 02:10:00 +0900
categories: [spring, aop, fundamentals]
tags: [spring, aop, aspect, pointcut, advice, cross-cutting-concerns, fundamentals, proxy, java]
---

> *''*@Aspect 가 *뭐예요?""*, *''*Pointcut 표현식이 *왜 *이렇게 *복잡 해요?""*, *''*Spring AOP 가 *@Transactional 의 *기반이라는데, *그래서 *내가 *직접 *AOP 를 *짤 일이 *있나요?""*. *주니어 *2 ~ 3 년 차쯤 *되면 *''*Aspect 가 *@Configuration 처럼 *클래스에 *붙이는 *뭔가""* 같다는 *어렴풋한 *느낌까지는 *오는데, *그 *너머는 *''*뭔가 *제어가 *안 *되는 *마법""* 처럼 *느껴진다.
>
> 이 글은 *''*5 년 *차 *시니어가 *후배에게 *카페에서 *2 시간 *동안 *예제 *5 개로 *설명해주는""* 톤으로, *Spring AOP 의 *3 핵심 *어휘 (Aspect / Pointcut / Advice) 를 *''*무엇 → 왜 → 어떻게 → 진짜 *코드 → 함정""* 의 *5 단계로 *풀어본다. *앞 글 [Spring *후처리기와 *ThreadLocal](/2026/06/06/post-processor-threadlocal-senior-explains-to-junior/) 을 *읽었으면 *''*아 *Aspect 도 *결국 *후처리기 *위에 *서 있구나""* 의 *그림이 *명확해질 것이다.

대상은 *''*@Transactional 은 *써봤는데 *AOP 를 *직접 *만들어 본 *적은 *없는""* 주니어, 그리고 *''*Pointcut 표현식이 *외워지지 *않는 *모든""* 사람.

---

## 1. *AOP 가 *뭔가 — *''*관점 *지향""* 의 *진짜 *의미*

### 1.1 *비유로 *시작 — *연극의 *무대 감독*

연극을 *상상해보자. *배우 (= 우리 *비즈니스 *코드) 는 *''*연기""* 에만 *집중 해야 한다. *그런데 *연극에는 *''*조명을 *켜고, *음악을 *틀고, *막을 *내리고, *관객의 *기침 소리를 *모니터링 하는""* 같은 *부수적인 *작업이 *수십 가지 *있다.

```
[배우 *없는 *연극이 *없듯, *AOP 없는 *Spring 도 *없다]

배우 (비즈니스 *로직)              무대 감독 (Aspect)
─────────────────                ─────────────────
이순신 *역, *대사 ''*나의 죽음을...''   배우가 *''*등장""* 하면 → 조명 *ON
                                  배우가 *''*대사""* 시작 → 음악 *볼륨 *내림
                                  배우가 *''*퇴장""* 하면 → 막 *내림
```

배우는 *''*조명이 *어디 *있는지""* 를 *몰라도 *된다. *무대 감독이 *알아서 *''*등장 *시점""* 을 *포착해서 *조명을 *켠다.

**AOP 의 *한 줄 *정의**:

> *''*비즈니스 *로직에서 *''*공통 *관심사 (cross-cutting concerns)""* 를 *분리해서, *별도의 *''*Aspect""* 클래스에 *모아두고, *Spring 이 *알아서 *원하는 *시점에 *끼워 *넣어주는 *프로그래밍 *기법.""*

### 1.2 *''*공통 *관심사""* 란*

*비즈니스 *로직 *여러 *곳에 *반복 등장 하는 *''*비기능적 *요구사항""*. *대표 예:

- **로깅** — 메서드 *진입 / 결과 / 예외 *기록
- **트랜잭션** — DB 트랜잭션 *시작 / 커밋 / 롤백
- **보안** — 권한 *체크
- **캐싱** — 결과 *캐시 *조회 / 저장
- **메트릭** — *호출 횟수, *지연 시간 측정
- **재시도** — 실패 시 *N 회 *반복

이런 *것을 *''*비즈니스 *로직 *클래스에 *섞어 *놓으면""*:

```java
public class OrderService {
    public void place(Order order) {
        log.info("place 시작 {}", order);          // *로깅
        Timer.Sample sample = Timer.start();         // *메트릭
        try {
            // *권한 *체크
            if (!securityChecker.canPlace(currentUser)) {
                throw new ForbiddenException();
            }
            // *트랜잭션 *시작
            txManager.begin();
            try {
                // *진짜 *비즈니스 *로직 (3 줄)
                inventory.reserve(order);
                payment.charge(order);
                repository.save(order);
                txManager.commit();
            } catch (Exception ex) {
                txManager.rollback();
                throw ex;
            }
        } finally {
            sample.stop();                            // 메트릭
            log.info("place 완료");                    // 로깅
        }
    }
}
```

진짜 *비즈니스는 *3 줄, 부수적 *코드가 *20 줄. *''*Big Ball of Mud""* 의 *시작이다.

### 1.3 *AOP 가 *바꿔주는 *모습*

```java
@Service
public class OrderService {
    @Transactional
    @PreAuthorize("@securityChecker.canPlace(authentication)")
    @Timed("order.place")
    @Logged
    public void place(Order order) {
        inventory.reserve(order);
        payment.charge(order);
        repository.save(order);
    }
}
```

비즈니스 *로직만 *5 줄. *나머지는 *''*어노테이션 *4 개""* 로 *압축. *그리고 *각 *어노테이션 *뒤에는 *Aspect 가 *서 있다.

**이게 *AOP 의 *진짜 *효용**: *비즈니스 *코드의 *''*신호 *대 *잡음 *비율""* 을 *극단적으로 *올린다.

---

## 2. *3 핵심 *어휘 — *Aspect / Pointcut / Advice*

AOP 를 *처음 *배울 때 *외워야 *할 *건 *딱 *5 개. *그 *중에서도 *3 개가 *제일 *중요.

### 2.1 *Aspect (관점)*

*''*Pointcut + Advice 의 *묶음""*. *클래스 *하나에 *@Aspect 를 *붙이면 *그게 *Aspect.

```java
@Aspect
@Component
public class LoggingAspect {
    // 여기에 *Pointcut 과 *Advice 가 *함께 산다
}
```

### 2.2 *Pointcut (지점 *지정)*

*''*어디 (which method) 에 *Advice 를 *적용 할 것인가""* 의 *명세.

```java
@Pointcut("execution(public * com.lemuel.order..*Service.*(..))")
public void anyOrderServiceMethod() {}
```

이건 *''*com.lemuel.order *패키지 *하위의 *모든 *Service 클래스의 *모든 *public 메서드""* 를 *가리키는 *Pointcut.

### 2.3 *Advice (조언 / 실제 *하는 *일)*

*''*Pointcut 이 *''*어디""* 라면, *Advice 는 *''*무엇을""*. *5 종류가 *있다:

| Advice | 의미 |
|---|---|
| **@Before** | 메서드 *호출 *전 |
| **@AfterReturning** | 메서드가 *정상 *리턴 후 |
| **@AfterThrowing** | 메서드가 *예외 *던진 후 |
| **@After** | 정상이든 *예외든 *끝나면 (= try-finally 의 *finally) |
| **@Around** | 전과 *후 *모두 *제어 (가장 *강력) |

### 2.4 *Join Point (실행 *지점)*

*''*Advice 가 *실행될 *수 *있는 *모든 *시점""*. Spring AOP 에서는 *''*메서드 *실행""* 이 *유일한 *Join Point. (AspectJ 는 *필드 *접근 *등 더 *많은 *Join Point 를 *지원하지만 *Spring 은 *메서드만)*

### 2.5 *Weaving (직조)*

*''*Aspect 를 *실제 *코드에 *끼워 넣는 *과정""*. Spring AOP 는 *런타임에 *프록시 *생성으로 *weaving. (AspectJ 는 *컴파일 타임 / 클래스 *로드 타임 *weaving 도 *지원)*

> **앞 글의 *후처리기를 *기억하는가?** *바로 *그 *후처리기 (`AnnotationAwareAspectJAutoProxyCreator`) 가 *''*@Aspect 클래스를 *찾아서 *해당 *Pointcut 에 *매칭 되는 *Bean 을 *프록시로 *감싸는""* 일을 *한다. *AOP 의 *''*마법""* 은 *후처리기 *위에서 *돈다.

---

## 3. *직접 *만들어보기 — *''*Hello AOP""**

코드로 *보는 게 *가장 빠르다. *주문 *메서드의 *실행 시간을 *재는 *간단한 *Aspect 를 *만들어 보자.

### 3.1 *준비 — *의존성 + @EnableAspectJAutoProxy*

```kotlin
// build.gradle.kts
implementation("org.springframework.boot:spring-boot-starter-aop")
```

Spring Boot 는 *spring-boot-starter-aop 만 *있으면 *@EnableAspectJAutoProxy 가 *자동 활성화. *명시 *필요 X.

### 3.2 *대상 *서비스*

```java
@Service
public class OrderService {
    public Order place(OrderCommand cmd) {
        // *비즈니스 *로직
        try { Thread.sleep(100); } catch (Exception ignored) {}
        return new Order(cmd.id());
    }
}
```

### 3.3 *Aspect *작성*

```java
@Slf4j
@Aspect
@Component
public class TimingAspect {

    // (1) Pointcut — *어디에 *적용 할까?
    @Pointcut("execution(* com.lemuel.shop.order..*Service.*(..))")
    public void anyOrderService() {}

    // (2) Advice — *무엇을 *할까? (@Around 가 *가장 *강력)
    @Around("anyOrderService()")
    public Object measureTime(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.nanoTime();
        try {
            return pjp.proceed();  // ← *진짜 *메서드 *호출
        } finally {
            long elapsedMs = (System.nanoTime() - start) / 1_000_000;
            String methodName = pjp.getSignature().toShortString();
            log.info("[METRIC] {} took {}ms", methodName, elapsedMs);
        }
    }
}
```

이 *코드만 *추가하면 *`OrderService.place()` 가 *호출될 *때마다 *콘솔에 *''*[METRIC] OrderService.place() took 102ms""* 같은 *로그가 *찍힌다. **`OrderService` 코드는 *0 줄 *수정**.

### 3.4 *''*아, 이게 *AOP 구나""* 의 *순간*

처음 *AOP 코드를 *돌려보면 *반드시 *드는 *생각이 *있다:

> *''*어? *내가 *`OrderService.place()` 를 *호출 했는데, *왜 *`TimingAspect.measureTime()` 이 *대신 *실행 되는 *거지?""*

이 *''*어?""* 의 *답이 *바로 *프록시. *Spring 이 *내가 *주입받는 *OrderService 를 *''*프록시로 *감싼""* 다음 *그것을 *주입했고, *그 *프록시 안에서 *`measureTime()` 이 *먼저 *돌고 *그 *안에서 *`pjp.proceed()` 가 *진짜 *`place()` 를 *호출 한 *것이다.

---

## 4. *Pointcut *표현식 — *''*무서워 *보이지만 *6 요소로 *분해 *가능""*

Pointcut 표현식이 *처음 *보면 *외계어 같다.

```java
"execution(public * com.lemuel.order.application..*Service.*(..))"
```

이걸 *6 요소로 *분해 *해보면 *쉽다.

```
execution(  public  *  com.lemuel.order.application..*Service  .  *  (..)  )
   ↑         ↑     ↑                ↑                      ↑   ↑
 지정자    제어자  반환형          타입(클래스)            메서드  파라미터
```

### 4.1 *각 *요소 *분해*

#### **(1) 지정자 — `execution`**
*''*어떤 *조인 포인트 *유형""* 인가. *Spring AOP 는 *대부분 *`execution` 만 *씀.

#### **(2) 제어자 — `public`, `protected`, `private`**
*생략 가능. *Spring 은 *어차피 *public 만 *프록시 *대상.

#### **(3) 반환형 — `*`, `void`, `String`, `Order`**
*`*` 는 *모든 *반환형. *특정 *타입 *지정도 *가능.

#### **(4) 타입 (클래스)** — `com.lemuel.order.application..*Service`

이게 *제일 *복잡 *보이는 *부분. 분해 하면:

- `com.lemuel.order.application` — *패키지 시작점
- `..` — *''*해당 *패키지 *및 *그 *하위 *모든 *패키지""* (재귀)
- `*Service` — *''*이름이 *Service 로 *끝나는 *모든 *클래스""*

#### **(5) 메서드명** — `*`, `place`, `find*`, `get*`
*와일드카드 *지원.

#### **(6) 파라미터** — `(..)`, `(String, ..)`, `()`

- `(..)` — *모든 *파라미터 (0 개 *이상)
- `()` — *파라미터 *없음
- `(String)` — *String 1 개
- `(String, ..)` — *첫 *번째 *String, *나머지 *상관 X

### 4.2 *자주 *쓰는 *7 가지 *패턴*

```java
// 1. 모든 *public 메서드
"execution(public * *(..))"

// 2. 특정 *패키지 *전체
"execution(* com.lemuel.shop..*(..))"

// 3. 특정 *클래스의 *모든 *메서드
"execution(* com.lemuel.shop.OrderService.*(..))"

// 4. 메서드명 *패턴 (find 로 시작하는 *모든 *메서드)
"execution(* com.lemuel.shop..*Service.find*(..))"

// 5. *특정 *반환형
"execution(Order com.lemuel.shop..*(..))"

// 6. *특정 *파라미터
"execution(* com.lemuel.shop..*(String, ..))"

// 7. 특정 *어노테이션 *붙은 *메서드
"@annotation(org.springframework.transaction.annotation.Transactional)"
```

### 4.3 *execution *외의 *지정자 — *''*상황별 *유용""*

#### **`@annotation()`** — 특정 *어노테이션 *붙은 *메서드*

```java
@Around("@annotation(com.lemuel.audit.AuditLog)")
public Object audit(ProceedingJoinPoint pjp) { ... }
```

*''*@AuditLog 가 *붙은 *모든 *메서드""*. *내가 *만든 *커스텀 *어노테이션 *처리할 때 *매우 *유용.

#### **`@within()`** — 특정 *어노테이션 *붙은 *클래스 내의 *모든 *메서드*

```java
@Around("@within(org.springframework.stereotype.Service)")
public Object onAnyService(ProceedingJoinPoint pjp) { ... }
```

#### **`within()`** — 특정 *클래스/패키지 *내의 *모든 *조인 포인트*

```java
@Pointcut("within(com.lemuel.shop.order..*)")
public void orderModule() {}
```

#### **`@args()`** — 파라미터에 *특정 *어노테이션 *붙은 *경우*

```java
@Before("@args(com.lemuel.validation.Validated)")
public void validate(...) { ... }
```

### 4.4 *조합 — *AND / OR / NOT*

Pointcut 도 *논리식으로 *조합 *가능.

```java
// AND
@Pointcut("execution(* *..*Service.*(..)) && @annotation(MyAnnotation)")
public void serviceMethodWithMyAnnotation() {}

// OR
@Pointcut("execution(* *..*Service.*(..)) || execution(* *..*Repository.*(..))")
public void serviceOrRepository() {}

// NOT
@Pointcut("execution(* *..*Service.*(..)) && !execution(* *..ReadOnlyService.*(..))")
public void serviceExceptReadOnly() {}
```

### 4.5 *Named Pointcut 으로 *재사용*

같은 *Pointcut 을 *여러 *Advice 가 *공유 *가능.

```java
@Aspect
@Component
public class OrderAspect {

    @Pointcut("execution(* com.lemuel.shop.order..*Service.*(..))")
    public void anyOrderService() {}  // ← 이 *이름을 *재사용

    @Before("anyOrderService()")
    public void logBefore(JoinPoint jp) { ... }

    @AfterReturning("anyOrderService()")
    public void logAfter(JoinPoint jp) { ... }
}
```

---

## 5. *실전 *예시 *3 가지*

### 5.1 *예시 1 — *감사 *로그 (Audit Log)*

요구사항: *''*@AuditLog 가 *붙은 *메서드의 *호출자, *파라미터, *결과를 *별도 *테이블에 *기록 하라""*.

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface AuditLog {
    String action() default "";
}

@Aspect
@Component
@RequiredArgsConstructor
public class AuditLogAspect {

    private final AuditLogRepository auditRepo;
    private final ObjectMapper objectMapper;

    @Around("@annotation(auditLog)")
    public Object audit(ProceedingJoinPoint pjp, AuditLog auditLog) throws Throwable {
        var actor = SecurityContextHolder.getContext().getAuthentication().getName();
        var args = objectMapper.writeValueAsString(pjp.getArgs());

        try {
            Object result = pjp.proceed();
            auditRepo.save(new AuditEntry(actor, auditLog.action(), args,
                "SUCCESS", objectMapper.writeValueAsString(result)));
            return result;
        } catch (Exception ex) {
            auditRepo.save(new AuditEntry(actor, auditLog.action(), args,
                "FAIL", ex.getMessage()));
            throw ex;
        }
    }
}

// 사용
@Service
public class OrderService {
    @AuditLog(action = "주문 생성")
    public Order place(OrderCommand cmd) { ... }
}
```

비즈니스 *코드는 *0 줄 *수정. *어노테이션 하나만 *붙이면 *''*누가 *언제 *뭘 *했는지""* 자동 기록.

### 5.2 *예시 2 — *재시도 (Retry)*

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Retryable {
    int maxAttempts() default 3;
    long delayMs() default 100;
}

@Slf4j
@Aspect
@Component
public class RetryAspect {

    @Around("@annotation(retryable)")
    public Object retry(ProceedingJoinPoint pjp, Retryable retryable) throws Throwable {
        int attempt = 0;
        while (true) {
            attempt++;
            try {
                return pjp.proceed();
            } catch (Exception ex) {
                if (attempt >= retryable.maxAttempts()) {
                    log.warn("재시도 {}회 실패, 포기: {}", attempt, ex.toString());
                    throw ex;
                }
                log.info("재시도 {}/{}: {}", attempt, retryable.maxAttempts(), ex.toString());
                Thread.sleep(retryable.delayMs() * attempt);  // 지수 백오프
            }
        }
    }
}

// 사용
@Service
public class PaymentService {
    @Retryable(maxAttempts = 3, delayMs = 200)
    public PaymentResult charge(Payment p) {
        return stripeClient.charge(p);  // 일시적 *네트워크 *오류 *대비
    }
}
```

### 5.3 *예시 3 — *권한 *체크*

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RequireRole {
    String[] value();
}

@Aspect
@Component
public class AuthorizationAspect {

    @Before("@annotation(requireRole)")
    public void checkRole(JoinPoint jp, RequireRole requireRole) {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null) {
            throw new UnauthorizedException();
        }
        var userRoles = auth.getAuthorities().stream()
            .map(GrantedAuthority::getAuthority).toList();

        boolean ok = Arrays.stream(requireRole.value()).anyMatch(userRoles::contains);
        if (!ok) {
            throw new ForbiddenException("필요 권한: " + String.join(", ", requireRole.value()));
        }
    }
}

// 사용
@Service
public class AdminService {
    @RequireRole({"ADMIN", "SUPER_ADMIN"})
    public void deleteAll() { ... }
}
```

> **현실의 *권장**: 권한 *체크는 *Spring Security 의 *@PreAuthorize 가 *훨씬 *풍부함. *이 *예시는 *''*AOP 의 *기본 *원리 *학습용""*.

---

## 6. *흔한 *함정 *5 가지*

### 6.1 *함정 1 — *같은 *클래스 *내부 *호출 시 *Aspect 무시*

```java
@Service
public class OrderService {

    @Logged
    public void method1() {
        method2();  // ← *같은 *클래스 *내부 *호출
    }

    @Logged  // ← 이 *Aspect 가 *''*무시""* 됨
    public void method2() { ... }
}
```

**왜?** *@Logged Aspect 는 *프록시에 *적용됨. `method1()` 호출 시 *프록시가 *돌다가 *진짜 *클래스의 *`method1()` 호출. *그 *안에서 *`method2()` 부르면 *''*프록시를 *거치지 *않고 *진짜 *`this.method2()`""*. *Aspect 미적용.

**(앞 글의 *후처리기 *함정과 *완전히 *같은 *원리)**

**해결**:
- 외부 *진입점에 *Aspect (가장 *권장)
- self-injection
- *클래스 *분리

### 6.2 *함정 2 — *private 메서드는 *AOP 안 *먹힘*

Spring AOP 는 *프록시 *기반. *프록시는 *public 메서드만 *오버라이드 가능. *private 은 *대상 X.

### 6.3 *함정 3 — *JDK Dynamic Proxy vs CGLIB*

Spring 은 *두 *프록시 *방식 중 *하나를 *씀:

| 방식 | 조건 | 동작 |
|---|---|---|
| **JDK Dynamic Proxy** | 인터페이스 *있는 *클래스 | 인터페이스 *구현체 *생성 |
| **CGLIB** | 인터페이스 *없는 *클래스 | 서브클래스 *생성 |

**Spring Boot 의 *기본**: `spring.aop.proxy-target-class=true` → CGLIB *우선. *클래스 *기반 *프록시 (서브클래스).

**주의 — *final 클래스 / final 메서드는 *CGLIB *불가** (서브클래스 *못 만듦). *@Async 가 *final 메서드에서 *조용히 *안 *먹는 *현상의 *주범.

### 6.4 *함정 4 — *Aspect 의 *순서 (@Order)*

여러 *Aspect 가 *같은 *Pointcut 에 *걸리면 *''*어느 *것이 *먼저 *돌까?""*. *기본은 *''*비결정적""*.

```java
@Aspect
@Component
@Order(1)  // ← *낮은 *숫자가 *바깥
public class TransactionAspect { ... }

@Aspect
@Component
@Order(2)
public class LoggingAspect { ... }
```

이러면:
```
[Logging Before]
  [Transaction Begin]
    실제 *메서드 *실행
  [Transaction Commit]
[Logging After]
```

*''*Aspect 순서는 *''*외곽이 *낮은 숫자""*'' 라는 *직관과 *반대로 *느껴질 수 있으니 *주의.

### 6.5 *함정 5 — *Pointcut 의 *성능*

너무 *광범위한 *Pointcut 은 *모든 *메서드 *호출마다 *''*이 *Pointcut 에 *해당 되나?""* 매칭 *비용을 *낸다.

**비효율**:
```java
@Pointcut("execution(* *(..))")  // *모든 *메서드 — *매칭 *비용 *극대화
```

**효율**:
```java
@Pointcut("execution(* com.lemuel.shop.order..*Service.*(..))")  // *대상 *좁힘
```

또는 *`within()` 으로 *먼저 *필터:
```java
@Pointcut("within(com.lemuel.shop..*) && @annotation(MyAnnotation)")
```

---

## 7. *Spring AOP vs *AspectJ — *''*무엇이 *다른가""*

이건 *주니어가 *헷갈리는 *부분.

| | Spring AOP | AspectJ |
|---|---|---|
| Weaving 시점 | 런타임 (프록시) | 컴파일 / 로드 타임 (바이트코드 *변경) |
| 적용 *대상 | Spring Bean 만 | *모든 *Java 클래스 |
| Join Point | 메서드 *실행만 | *필드 *접근, *생성자, *static 초기화 등 |
| 성능 | 프록시 *오버헤드 | 거의 *0 |
| 학습 *곡선 | 낮음 | 높음 |
| 설치 *복잡도 | 의존성 *추가 만 | 별도 *컴파일러 *필요 |

**현실 *95% 의 *Spring 프로젝트는 *Spring AOP 로 *충분**. *AspectJ 는 *''*Spring Bean 이 *아닌 *객체에도 *Aspect 적용""* 이 *필요할 *때만 *고려.

---

## 8. *''*그래서 *내가 *직접 *Aspect 만들 *일이 *있나?""**

후배가 *제일 *자주 *묻는 *질문.

**대부분의 *경우 — *없다**. *Spring 이 *이미 *제공:
- @Transactional → 트랜잭션 *처리
- @Async → 비동기 *실행
- @Cacheable → 캐시
- @Scheduled → 스케줄러
- @Retryable (Spring Retry) → 재시도
- @PreAuthorize (Spring Security) → 권한

**내가 *직접 *Aspect 만들 *상황**:
- *팀 *내부 *특수 *요구 (감사 *로그, *권한 *모델)
- *외부 *라이브러리에는 *없는 *어노테이션 *처리
- *프레임워크 *수준의 *공통 *기능

**하지만 *''*어떻게 *동작 하는지""* 는 *반드시 *알아야 한다**. 이유:
- @Transactional 이 *안 *먹는 *디버깅
- *프록시 *함정 (같은 클래스 *내부 *호출)
- *성능 *분석 (어떤 Aspect 가 *얼마나 *비용 *내는가)

---

## 9. *정리 — *''*5 가지 *기억할 *점""*

### 1. *AOP 의 *3 핵심 *어휘*
- **Aspect** — Pointcut + Advice 묶음
- **Pointcut** — 어디 (which method)
- **Advice** — 무엇 (@Before / @After / @AfterReturning / @AfterThrowing / @Around)

### 2. *@Around 가 *가장 *강력*
*pjp.proceed() 의 *전/후 모두 *제어. 다른 *Advice 는 *@Around 의 *특수 케이스.

### 3. *Pointcut 표현식의 *6 요소*
*execution(제어자 *반환형 *타입.메서드(파라미터)). *외우려 하지 *말고 *분해 해라.

### 4. *프록시의 *함정 — *''*내부 *호출 무시""**
*같은 *클래스 *내부 *호출 시 *Aspect 가 *동작 *안 함. *외부 *진입점이 *프록시 거치는 *경우만.

### 5. *Aspect 의 *진짜 *효용은 *''*신호 *대 *잡음""**
*비즈니스 *코드가 *''*뭘 *하는지""* 만 *남고 *''*어떻게 *부수적""* 인 *것은 *Aspect 로 *분리. *유지보수성의 *극단적 *향상.

---

## 10. *마지막 — *후처리기 + ThreadLocal + AOP 의 *연결*

[앞 글](/2026/06/06/post-processor-threadlocal-senior-explains-to-junior/)에서 *후처리기와 *ThreadLocal 을 *다뤘고, *이 *글에서 *AOP 를 *다뤘다. *세 *주제가 *어떻게 *연결되는가:

```
*Spring 의 *''*마법""*
        │
        ├─ *후처리기*
        │    └─ Bean 라이프사이클에 *끼어들어 *프록시 *생성
        │         └─ AnnotationAwareAspectJAutoProxyCreator
        │              └─ @Aspect 찾아 *Pointcut 매칭 *후 *프록시 감싸기
        │
        ├─ *AOP (Aspect / Pointcut / Advice)*
        │    └─ 위 *프록시 안에서 *우리 *Advice 실행
        │
        └─ *ThreadLocal*
             └─ Advice 가 *''*현재 *트랜잭션""*, *''*현재 *사용자""* 같은 *상태를 *공유

= @Transactional 한 줄이 *세 *기둥 *위에서 *동작
```

**3 개의 *글이 *한 *그림으로 *합쳐 진다**:

1. 후처리기가 *''*프록시 *언제 *만들지""* 결정
2. AOP 가 *''*프록시 안에서 *무엇 *할지""* 정의
3. ThreadLocal 이 *''*프록시 사이에서 *상태 어떻게 *공유""* 함

이 *3 가지를 *함께 *이해 한 *주니어는 *Spring 의 *''*마법""* 이 *더 *이상 *마법 처럼 *보이지 *않는다. *''*아 *이게 *결국 *프록시 + 후처리기 + ThreadLocal 의 *조합이구나""* 라는 *그림이 *생긴다. *그게 *''*시니어로 *한 *발 *들어선""* 순간이다.

> **마지막 *한 *문장**:
>
> *''*AOP 는 *''*마법""* 이 *아니라 *''*잘 *설계된 *프록시 *패턴""* 일 *뿐이다. *그 *프록시를 *''*누가 *만드는가 (후처리기)""* 와 *''*무엇을 *공유 하는가 (ThreadLocal)""* 까지 *함께 *이해 하면, *Spring 의 *모든 *@annotation 이 *''*아 *이건 *어디서 *어떤 *Advice 가 *돌고 *있겠구나""* 의 *그림으로 *읽힌다. *그게 *''*Spring 을 *진짜 *안다""* 는 *상태다.""*

---

## 더 *읽으면 *좋은 *자료*

- 본 블로그의 [Spring 후처리기 + ThreadLocal — 시니어가 *주니어에게 *설명](/2026/06/06/post-processor-threadlocal-senior-explains-to-junior/) — *이 *글의 *전제
- 본 블로그의 [Spring AOP — *무대 *감독의 *시선, 면접 시각](/2026/05/26/spring-aop-interview-senior-engineer-perspective/) — *면접 *관점
- *Spring Framework Reference* — *''*5. Aspect Oriented Programming with Spring""*
- *Eclipse AspectJ Documentation* — Pointcut 표현식 *완전 *명세
- *Joshua Bloch*, **Effective Java** (3 판) — Item 18 (인터페이스 *기반 *프록시의 *전제)
- *우아한기술블로그* — *''*Spring AOP 실전 *적용기""* 시리즈
- *Vaughn Vernon*, **Implementing Domain-Driven Design** — *Aspect 와 *Domain Event 의 *분리
