---
layout: post
title: "스프링 AOP 포인트컷, 실무에서는 3개만 쓴다: 금융 정산과 쇼핑몰 도메인의 실제 사례"
date: 2026-08-11 02:10:00 +0900
categories: [spring, backend, architecture]
tags:
  [
    Spring AOP,
    포인트컷,
    execution,
    annotation,
    bean,
    CGLIB,
    김영한,
    인프런,
    정산,
    커머스,
  ]
---

![스프링 핵심 원리 고급편 - 섹션 12. 스프링 AOP 포인트컷 커리큘럼 (13강 1시간 52분)](/assets/images/spring-aop-pointcut-curriculum.jpg)

김영한 강사의 **[스프링 핵심 원리 - 고급편][course]** 섹션 12 는 포인트컷만 13강, 1시간 52분을 쓴다. 지시자(PCD)를 하나씩 다 훑는다 — `execution`, `within`, `args`, `@target`, `@within`, `@annotation`, `@args`, `bean`, `this`, `target`.

다 배우고 나면 드는 생각이 있다. **"이걸 다 쓸 일이 있나?"**

없다. 실무 코드베이스에서 실제로 쓰는 건 사실상 세 개다. 그리고 나머지는 *쓰기 위해서*가 아니라 **터졌을 때 원인을 알기 위해** 배운다. 이 글은 금융 정산과 쇼핑몰 두 도메인에서 포인트컷이 실제로 어떻게 쓰이는지, 그리고 나머지 지시자들이 어떤 사고로 나타나는지에 대한 정리다.

---

## 0. 전제: 스프링 AOP 가 잡을 수 있는 것은 메서드 실행뿐

먼저 범위를 못 박아야 한다. 공식 문서의 첫 문장이 그 일을 한다.

> Pointcuts determine join points of interest and thus enable us to control when advice runs. **Spring AOP only supports method execution join points for Spring beans**, so you can think of a pointcut as matching the execution of methods on Spring beans.
>
> — [Spring Framework Reference, Declaring a Pointcut][spring-pointcut]

필드 접근(`get`/`set`), 생성자, 예외 핸들러 같은 AspectJ 의 다른 조인 포인트는 스프링 AOP 에서 **`IllegalArgumentException`** 을 던진다. 스프링이 지원하는 PCD 는 다음 10개뿐이다 (같은 문서).

| PCD           | 매칭 기준                                | 판정 시점   |
| ------------- | ---------------------------------------- | ----------- |
| `execution`   | 메서드 시그니처                          | 정적        |
| `within`      | 특정 타입 내부의 조인 포인트             | 정적        |
| `this`        | **프록시 객체**가 주어진 타입의 인스턴스 | 정적/런타임 |
| `target`      | **대상 객체**가 주어진 타입의 인스턴스   | 정적/런타임 |
| `args`        | 전달된 인수가 주어진 타입의 인스턴스     | **런타임**  |
| `@target`     | 실행 객체의 클래스에 해당 애노테이션     | **런타임**  |
| `@within`     | 해당 애노테이션이 붙은 타입 내부         | 정적        |
| `@annotation` | 실행되는 메서드에 해당 애노테이션        | 정적        |
| `@args`       | 인수의 **런타임 타입**에 해당 애노테이션 | **런타임**  |
| `bean`        | 스프링 빈 이름 (스프링 전용 확장)        | 정적        |

`bean` 은 AspectJ 표준이 아니라 스프링이 더한 것이다. 문서가 명시한다.

> The `bean` PCD is supported **only in Spring AOP and not in native AspectJ weaving**. It is a Spring-specific extension (…) The `bean` PCD operates at the instance level (building on the Spring bean name concept) rather than at the type level only.

### 실무 사용 빈도

내 경험상의 등급이다. 뒤에서 각각 근거를 붙인다.

| 등급         | PCD                                          | 쓰이는 곳                                         |
| ------------ | -------------------------------------------- | ------------------------------------------------- |
| ★★★ 매일     | `execution`                                  | 계층 전체를 대상으로 하는 횡단 관심사             |
| ★★★ 매일     | `@annotation`                                | 메서드 단위 옵트인 — 락, 감사, 재시도             |
| ★★ 가끔      | `bean`                                       | 이름 규약이 잡힌 코드베이스에서 빈 단위 지정      |
| ★ 드물게     | `within`, `@within`                          | 모듈/패키지 경계 한정, 보통 `execution` 으로 대체 |
| ☆ 거의 안 씀 | `args`, `@args`, `@target`, `this`, `target` | 매개변수 바인딩 보조. 단독 사용은 사고의 원인     |

---

## 1. 금융 정산 — 규제 대응 감사 로그는 `execution` 과 `@annotation` 을 **둘 다** 쓴다

정산 시스템에서 가장 먼저 AOP 로 뽑는 관심사는 감사 로그다. 누가·언제·어떤 금액을 움직였는지 전부 남겨야 한다.

여기서 초보와 실무의 갈림길이 있다. **어느 쪽 하나만 쓰면 반드시 구멍이 난다.**

### 1-1. `@annotation` 만 쓰면 — 빠뜨린 것을 아무도 모른다

```java
@Around("@annotation(auditable)")
public Object audit(ProceedingJoinPoint joinPoint, Auditable auditable) throws Throwable { ... }
```

깔끔하다. 개발자가 `@Auditable` 을 붙인 메서드만 정확히 잡는다. 문제는 **새 정산 서비스를 만든 개발자가 애노테이션을 안 붙이면 감사 로그가 그냥 없다는 것**이다. 컴파일도 되고 테스트도 통과한다. 규제 감사에서야 발견된다.

옵트인 방식의 구조적 약점이다. 누락이 **조용하다.**

### 1-2. `execution` 만 쓰면 — 계층 구조 리팩터링에 부러진다

```java
@Around("execution(* com.company.settlement.application..*Service.*(..))")
```

빠짐이 없다는 게 장점이다. 그런데 패키지를 `application` → `usecase` 로 옮기는 순간 조용히 아무것도 안 잡는다. **틀린 포인트컷은 에러를 내지 않는다. 그냥 0건을 매칭한다.** 이것이 포인트컷 디버깅이 어려운 근본 이유다.

### 1-3. 실무 해법 — 넓게 잡고, 명시적으로 뺀다

```java
@Aspect
@Component
public class SettlementAuditAspect {

    // 정산 유스케이스 계층 전체 — 기본은 "전부 남긴다"
    @Pointcut("execution(* com.company.settlement.application..*Service.*(..))")
    private void settlementUseCase() {}

    // 명시적으로 제외 표시한 것만 뺀다 (조회성 API 등)
    @Pointcut("@annotation(com.company.settlement.audit.NoAudit)")
    private void excluded() {}

    @Around("settlementUseCase() && !excluded()")
    public Object audit(ProceedingJoinPoint pjp) throws Throwable {
        AuditContext ctx = AuditContext.of(pjp);   // 메서드명, 파라미터 시그니처
        try {
            Object result = pjp.proceed();
            auditLogger.success(ctx);
            return result;
        } catch (Throwable e) {
            auditLogger.failure(ctx, e);   // 실패도 반드시 남긴다
            throw e;
        }
    }
}
```

기본값을 뒤집은 것이 전부다. **"붙인 것만 남긴다"에서 "뺀다고 명시한 것만 안 남긴다"로.** 누락이 조용하지 않게 된다 — 새 서비스를 추가하면 자동으로 감사 대상이 되고, 빼려면 `@NoAudit` 을 붙이며 리뷰어의 눈에 걸린다.

그리고 포인트컷 표현식을 **이름 있는 `@Pointcut` 으로 쪼갠 것**은 공식 권장이다.

> It is a **best practice to build more complex pointcut expressions out of smaller named pointcuts**, as shown above. (…) We recommend defining a dedicated class that captures commonly used named pointcut expressions for this purpose.
>
> — [Spring Framework Reference][spring-pointcut]

정산처럼 애스펙트가 여러 개(감사, 멱등성, 메트릭, 트랜잭션 경계 로깅) 붙는 도메인에서는 `CommonPointcuts` 클래스 하나에 표현식을 모아두는 게 특히 값어치가 있다. 패키지 구조가 바뀔 때 고칠 곳이 **한 군데**가 된다.

### 1-4. 매개변수 바인딩 — 여기서 `args` 가 유일하게 정당해진다

감사 로그에 "얼마를 움직였는지"를 남기려면 파라미터가 필요하다. 이때 `args` 를 쓴다. 단, **단독으로 쓰지 않는다.**

```java
@Around("settlementUseCase() && args(command, ..)")
public Object auditWithAmount(ProceedingJoinPoint pjp, SettleCommand command) throws Throwable {
    // command.amount() 는 남기고, command.accountNo() 는 마스킹해서 남긴다
    ...
}
```

`args` 는 **런타임 인수의 실제 타입**으로 매칭하며 부모 타입을 허용한다. 메서드 시그니처의 정적 정보만 보는 `execution` 과 대비되는 지점이다 (김영한, 「args」 강의). 즉 `execution(* *(Object))` 은 선언 타입이 정확히 `Object` 인 메서드만 잡지만, `args(Object)` 는 무엇이든 하나를 받는 모든 메서드를 잡는다.

> ⚠️ 금융 도메인 주의: AOP 로 감사 로그를 자동화하면 **파라미터 전체를 무심코 직렬화하기 쉽다.** 계좌번호·주민번호·카드번호가 평문으로 로그에 흘러들어가는 사고가 이 지점에서 난다. 바인딩한 파라미터는 화이트리스트 방식으로 필드를 골라 남겨야 한다.

---

## 2. 쇼핑몰 — `@annotation` 으로 분산락, `bean` 으로 관측

### 2-1. 재고·쿠폰 분산락: `@annotation` + 매개변수 바인딩

커머스에서 AOP 가 가장 잘 먹히는 자리는 분산락이다. 선착순 쿠폰과 재고 차감은 반드시 직렬화되어야 하는데, 이 로직을 서비스 메서드마다 손으로 쓰면 락 해제 누락이 반드시 생긴다.

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface DistributedLock {
    String key();                              // SpEL: "#couponId"
    long waitSeconds() default 3;
    long leaseSeconds() default 5;
}

@Aspect
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)   // 트랜잭션보다 바깥에서 돌아야 한다
public class DistributedLockAspect {

    @Around("@annotation(lock)")
    public Object around(ProceedingJoinPoint pjp, DistributedLock lock) throws Throwable {
        String key = spelParser.parse(lock.key(), pjp);   // 파라미터 → 락 키
        RLock rLock = redissonClient.getLock("lock:" + key);
        if (!rLock.tryLock(lock.waitSeconds(), lock.leaseSeconds(), TimeUnit.SECONDS)) {
            throw new LockAcquisitionException(key);
        }
        try {
            return pjp.proceed();
        } finally {
            if (rLock.isHeldByCurrentThread()) rLock.unlock();
        }
    }
}
```

여기서 `@annotation` 이 정답인 이유는 명확하다. **락은 "이 메서드는 락이 필요하다"는 도메인 지식이 필요한 옵트인 결정**이기 때문이다. 감사 로그처럼 "전부 다"가 기본값이 될 수 없다. 계층 전체에 락을 걸면 성능이 무너진다.

그리고 `@Order(HIGHEST_PRECEDENCE)` 가 핵심이다. 락 해제가 트랜잭션 커밋보다 먼저 일어나면, 락을 놓은 직후 아직 커밋되지 않은 재고를 다음 요청이 읽는다. 포인트컷을 아무리 정확히 써도 **애스펙트 순서를 틀리면 락이 무의미해진다.**

### 2-2. `bean` — 이름 규약이 있으면 가장 읽기 쉬운 포인트컷

레포지토리 계층의 쿼리 시간을 재고 싶다고 하자. `execution` 으로 쓰면 이렇다.

```java
@Around("execution(* com.shop..repository..*Repository.*(..))")
```

`bean` 으로 쓰면 이렇다.

```java
@Around("bean(*Repository)")
```

빈 이름 규약이 잡혀 있다면 두 번째가 압도적으로 읽기 쉽고, 패키지 이동에 안 부러진다. 특정 빈만 골라내거나 제외하는 것도 자연스럽다.

```java
@Around("bean(*Repository) && !bean(auditLogRepository)")   // 감사 로그 자신은 제외
```

대신 **AspectJ 위빙으로 이전할 수 없다**는 제약을 안고 가는 것이다(위 공식 인용). 스프링 AOP 로 계속 갈 것이 확실할 때만 쓴다.

### 2-3. `within` — 어댑터 계층만 한정할 때

헥사고날 구조에서 "외부 API 호출 어댑터에만 서킷브레이커 메트릭을 붙인다" 같은 요구가 있다.

```java
@Pointcut("within(com.shop.adapter.out.external..*)")
private void externalAdapter() {}
```

`within` 은 **타입 내부의 조인 포인트**를 잡는다. `execution` 과 달리 부모 타입 지정이 안 되고 정확한 타입 매칭이라, 실무에서는 대개 `execution` 이 더 유연해서 그쪽을 쓴다 (김영한, 「within」 강의). 위처럼 **패키지 경계 자체가 의미인 경우**에만 `within` 이 더 명확하다.

---

## 3. 나머지 지시자는 "사고의 원인"으로 만난다

여기서부터가 강의 1시간 52분의 진짜 값어치다.

### 3-1. `@target` · `@args` 단독 사용 → 애플리케이션이 아예 안 뜬다

김영한 강사가 「@target, @within」 강의에서 강조하는 대목이다.

> `@ARGS`, `@Target` 과 같은 포인트컷 지시자는 **단독으로 사용하면 안 된다.** 이러한 지시자는 실제 객체 인스턴스가 생성되고 실행될 때 어드바이스 적용 여부를 판단할 수 있기 때문이다. 스프링 컨테이너는 애플리케이션 로딩 시점에 프록시를 생성하려고 시도하는데, 프록시가 없으면 실행 시점의 판단 자체가 불가능하다.
>
> — 김영한, [「@target, @within」][lec-target] (스프링 핵심 원리 - 고급편)

결과가 뭐냐면, 스프링이 **모든 빈에 프록시를 붙이려고 시도한다.** 그리고 스프링 내부의 `final` 클래스 빈에 CGLIB 프록시를 만들려다 실패한다. 강사의 표현 그대로 _"Cannot serve a class 파이널로 되어있는 서버 클래스 할 수 없다고 뜨죠."_

그래서 반드시 `execution` 같은 정적 지시자로 **대상을 먼저 좁힌 뒤** 조합한다.

```java
// ❌ 애플리케이션이 안 뜬다
@Around("@target(com.shop.TraceTarget)")

// ✅ 대상을 먼저 축소
@Around("execution(* com.shop..*(..)) && @target(com.shop.TraceTarget)")
```

### 3-2. `@target` vs `@within` — 부모 클래스 메서드가 잡히냐 마느냐

둘 다 "클래스에 붙은 애노테이션"으로 매칭해서 헷갈리는데, 차이는 상속에서 갈린다.

|                           | 자기 클래스의 메서드 | **부모 클래스에서 상속받은 메서드** |
| ------------------------- | -------------------- | ----------------------------------- |
| `@target` (인스턴스 기준) | ✅ 적용              | ✅ **적용**                         |
| `@within` (타입 기준)     | ✅ 적용              | ❌ 미적용                           |

강사의 요약이 가장 짧다. _"쉽게 얘기해서 타겟은 부모 클래스의 메소드까지 전부 다 어드바이스를 적용을 해줘요."_

추상 기반 클래스에 공통 메서드를 몰아넣는 커머스 서비스 구조에서 이 차이가 실제로 문제가 된다. `@within` 을 썼는데 상속받은 `findById` 에 로그가 안 남는다면 원인이 이것이다.

### 3-3. `this` vs `target` × JDK 동적 프록시 vs CGLIB

강의 110번(22분 40초, 섹션에서 가장 긴 강의)이 이 주제다. 그럴 만하다.

- `this` → 스프링 빈으로 등록된 **프록시 객체**
- `target` → 프록시가 감싸고 있는 **실제 대상 객체**

공식 문서가 왜 이런 구분이 생겼는지 설명한다.

> AspectJ itself has type-based semantics and, at an execution join point, both `this` and `target` refer to the same object (…) **Spring AOP is a proxy-based system and differentiates between the proxy object itself (which is bound to `this`) and the target object behind the proxy (which is bound to `target`).**
>
> — [Spring Framework Reference][spring-pointcut]

실제 동작은 프록시 생성 전략에 따라 갈린다 (김영한, [「this, target」][lec-this] 강의의 검증 결과).

| 프록시 전략     | 포인트컷 지정   | `this`        | `target` |
| --------------- | --------------- | ------------- | -------- |
| JDK 동적 프록시 | 인터페이스      | ✅            | ✅       |
| JDK 동적 프록시 | **구체 클래스** | ❌ **미적용** | ✅       |
| CGLIB           | 인터페이스      | ✅            | ✅       |
| CGLIB           | 구체 클래스     | ✅            | ✅       |

JDK 동적 프록시는 인터페이스만 구현하므로, 프록시 객체가 `MemberServiceImpl` 이라는 구체 타입을 **모른다.** 그래서 `this(MemberServiceImpl)` 이 매칭에 실패한다. `target` 은 항상 실제 객체를 보므로 이 제약이 없다.

실무에서 이걸 만날 확률은 낮다. 스프링 부트는 `spring.aop.proxy-target-class` 기본값이 `true` (CGLIB) 라서 위 표의 ❌ 칸으로 갈 일이 없기 때문이다. 다만 **레거시 설정으로 JDK 프록시를 강제한 프로젝트를 인수인계받았을 때** 정확히 이 칸에서 "왜 AOP 가 안 걸리지"가 발생한다.

### 3-4. 포인트컷 문제로 오인되는 1위 — 내부 호출

이건 포인트컷을 아무리 정교하게 써도 해결되지 않는다.

> Due to the proxy-based nature of Spring's AOP framework, **calls within the target object are, by definition, not intercepted.** For JDK proxies, only public interface method calls on the proxy can be intercepted.
>
> — [Spring Framework Reference][spring-pointcut]

```java
@Service
public class OrderService {

    public void placeOrder(Order order) {
        validate(order);
        decreaseStock(order);   // ⚠️ this.decreaseStock() — 프록시를 안 거친다
    }

    @DistributedLock(key = "#order.productId")
    public void decreaseStock(Order order) { ... }   // 락이 걸리지 않는다
}
```

`decreaseStock` 을 컨트롤러에서 직접 부르면 락이 걸리고, `placeOrder` 를 거치면 안 걸린다. **같은 메서드가 호출 경로에 따라 다르게 동작한다.** 재고 오차 같은 재현 안 되는 버그의 단골 원인이다.

포인트컷 표현식을 고쳐서는 절대 해결되지 않는다. 해법은 셋 중 하나다.

1. **자기 자신 주입** — 순환 참조 회피 설정 필요, 권장하지 않음
2. **지연 조회** — `ApplicationContext` 나 `ObjectProvider` 로 프록시를 꺼내 호출
3. **구조 분리** — `StockService` 로 클래스를 분리해 진짜 외부 호출로 만든다 (권장)

3번이 정답인 이유는 AOP 우회가 아니라 **책임 분리가 원래 옳기 때문**이다. 락이 필요한 임계 구역이 다른 메서드 안에 숨어 있다는 것 자체가 설계 신호다.

---

## 4. 정리 — 실무 체크리스트

1. **`execution` 은 계층에, `@annotation` 은 메서드에.** "기본적으로 다 적용"은 `execution`, "명시적으로 선택"은 `@annotation`.
2. **누락이 조용한 쪽을 피한다.** 규제 대응처럼 빠짐이 치명적이면 옵트아웃(`execution && !@NoAudit`), 성능 영향이 크면 옵트인(`@annotation`).
3. **표현식은 이름 있는 `@Pointcut` 으로 쪼개고 한 클래스에 모은다.** 공식 권장이며, 패키지 리팩터링 시 고칠 곳이 한 군데가 된다.
4. **런타임 판정 지시자(`@target`, `@args`, `args`)는 단독 사용 금지.** 반드시 `execution`/`within` 으로 대상을 먼저 좁힌다.
5. **애스펙트 순서를 명시한다.** 락은 트랜잭션 바깥(`@Order(HIGHEST_PRECEDENCE)`)이어야 한다.
6. **AOP 가 안 걸리면 먼저 내부 호출을 의심한다.** 포인트컷 표현식은 그다음이다.
7. **바인딩한 파라미터를 통째로 로깅하지 않는다.** 금융 도메인에서 이건 사고다.

`within`, `this`, `target`, `@within`, `@args` 를 직접 쓸 일은 아마 없을 것이다. 그런데 이 다섯 개를 모르면 "왜 상속받은 메서드엔 안 걸리지", "왜 이 프로젝트만 AOP 가 안 먹지"에서 며칠을 태운다. 1시간 52분이 아깝지 않은 이유다.

---

## References

### 1차 · 공식

- Spring Framework Reference Documentation, _Declaring a Pointcut_ — 지원 PCD 목록, `bean` 확장, `this`/`target` 의 프록시 기반 구분, 내부 호출 미인터셉트, 포인트컷 분리 권장. <https://docs.spring.io/spring-framework/reference/core/aop/ataspectj/pointcuts.html>
- Spring Framework Reference Documentation, _AOP Concepts / Proxying Mechanisms_. <https://docs.spring.io/spring-framework/reference/core/aop.html>

### 강의

- 김영한, **[스프링 핵심 원리 - 고급편][course]** (인프런) — 섹션 12 「스프링 AOP - 포인트컷」
  - [「@target, @within」][lec-target] — 단독 사용 시 전체 빈 프록시 시도 및 `final` 클래스 오류
  - [「this, target」][lec-this] — JDK 동적 프록시 / CGLIB 별 매칭 검증
  - [「args」][lec-args] — 런타임 타입 매칭과 `execution` 의 정적 매칭 대비
  - [「within」][lec-within] — 정확한 타입 매칭, 부모 타입 미지원
  - [「bean」][lec-bean] — 스프링 전용 빈 이름 지시자

### 한계 명시

본문의 금융·커머스 코드는 특정 회사 코드가 아니라 두 도메인에서 반복적으로 나타나는 패턴을 재구성한 것이다. 성능 수치나 벤치마크는 제시하지 않았다 — 애스펙트 오버헤드는 어드바이스 내용과 프록시 전략에 전적으로 좌우되므로 일반화된 수치를 인용하는 것이 부정확하기 때문이다.

[spring-pointcut]: https://docs.spring.io/spring-framework/reference/core/aop/ataspectj/pointcuts.html
[course]: https://www.inflearn.com/courses/lecture?courseId=327901&unitId=94513
[lec-target]: https://www.inflearn.com/courses/lecture?courseId=327901&unitId=94525
[lec-this]: https://www.inflearn.com/courses/lecture?courseId=327901&unitId=94519
[lec-args]: https://www.inflearn.com/courses/lecture?courseId=327901&unitId=94518
[lec-within]: https://www.inflearn.com/courses/lecture?courseId=327901&unitId=94517
[lec-bean]: https://www.inflearn.com/courses/lecture?courseId=327901&unitId=94522
