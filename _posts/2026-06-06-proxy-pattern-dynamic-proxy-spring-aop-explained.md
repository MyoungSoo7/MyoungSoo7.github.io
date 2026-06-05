---
layout: post
title: "주니어를 위한 프록시 패턴 안내 — *왜* 정적 프록시가 부족했고 *어떻게* 동적 프록시로 진화했으며 *Spring 이* 그걸 어떻게 활용하는가"
date: 2026-06-06 01:50:00 +0900
categories: [java, spring, design-pattern]
tags: [proxy-pattern, dynamic-proxy, jdk-dynamic-proxy, cglib, spring-aop, transactional, design-patterns, junior-friendly]
---

*"왜 `@Transactional` 이 같은 클래스 안에서 호출하면 *안 먹어요*?"*

이 한 질문이 *주니어 → 시니어* 의 길고 긴 여정의 *첫 걸음*. 답은 *Spring 의 프록시* 에 있고, 프록시 의 답은 *디자인 패턴의 Proxy* 에 있고, 디자인 패턴의 답은 *컴퓨터 과학의 *간접 참조 (indirection)*** 에 있다.

오늘 *주니어에게 친절히 설명하는 톤* 으로 이 사슬을 *처음부터 끝까지* 따라가 본다. *책에는 안 나오는 *왜*** 중심으로.

---

## TL;DR — *주니어가 알아야 할 한 줄*

> **Spring 의 `@Transactional` / `@Async` / `@Cacheable` 같은 어노테이션은 *프록시 객체* 가 *실제 객체 앞에 끼어들어* 동작한다.**
> *같은 클래스 안 (this) 에서 호출하면 *프록시를 거치지 않아 어노테이션이 무시* 된다.*

이 한 줄을 *직관* 으로 이해하면 *시니어의 90%* 이해 완료. 나머지는 *디테일*.

---

## 1. *프록시* 가 뭐냐 — 일상의 비유부터

### 1.1 카페에서 *대신 주문* 해주는 친구

오늘 아침. 너는 일하느라 바빠. 친구가 *대신 카페* 가서 *너의 커피* 를 주문해 와줘. 너는 *카운터에 안 가도* 커피를 받음.

여기서:
- **너** = 실제 객체 (Real Subject)
- **친구** = 프록시 (Proxy)
- **카페** = 클라이언트 (호출자)

친구 (프록시) 가 *너 (실제 객체) 와 *같은 일* 을 함*. 클라이언트 (카페) 입장에선 *누가 진짜* 인지 구분 안 됨.

### 1.2 *왜* 친구를 끼우나? — 3 가지 이유

1. **너 보호** — 너에게 *전화 받지 마* 라고 친구가 차단 (보안 / 접근 제어)
2. **너 자원 절약** — 친구가 *이미 사놓은 커피* 있으면 *카페 안 감* (캐싱)
3. **너 모르게 *추가 일*** — 친구가 *영수증을 따로 기록* (로깅 / 감사)

이게 *프록시 패턴의 3 가지 핵심 동기*.

---

## 2. *정적 프록시* — 책의 첫 챕터

### 2.1 *GoF 정통* — Subject 인터페이스 + 두 구현체

```java
// 1) 공통 interface
public interface Coffee {
    void order();
}

// 2) 진짜 객체
public class RealCoffee implements Coffee {
    @Override
    public void order() {
        System.out.println("카페 가서 커피 주문");
    }
}

// 3) 프록시 (대리)
public class FriendProxy implements Coffee {
    private final Coffee real = new RealCoffee();

    @Override
    public void order() {
        System.out.println("[로그] 친구가 주문 시작");
        real.order();                  // 진짜 호출
        System.out.println("[로그] 친구가 주문 끝");
    }
}

// 4) 사용
Coffee c = new FriendProxy();
c.order();
// 출력:
// [로그] 친구가 주문 시작
// 카페 가서 커피 주문
// [로그] 친구가 주문 끝
```

여기서 *클라이언트 (`c`)* 는 `FriendProxy` 가 *프록시* 인지 *진짜* 인지 *모름*. 둘 다 `Coffee` interface 구현체.

### 2.2 *왜* 이게 좋아?

- *진짜 객체* 의 코드 변경 *0*
- *로깅 추가* 했지만 `RealCoffee.order()` 안 건드림
- *Open/Closed Principle* — Open for extension (FriendProxy), Closed for modification (RealCoffee)

### 2.3 *한계* — 명백한 함정

문제 1: **클래스가 *10 개*** 면 *10 개 프록시* 모두 손으로 만들어야 함

```java
class UserProxy implements User { ... }
class OrderProxy implements Order { ... }
class PaymentProxy implements Payment { ... }
// ... 10 개 ...
```

→ *boilerplate 폭증*.

문제 2: **공통 로직 (예: 로깅)** 이 *10 개 프록시에 반복*. *변경 시 10 곳 수정*. DRY 위반.

문제 3: **새 클래스 추가** 때마다 *새 프록시* 작성. 자동화 불가.

→ *정적 프록시 = 1990 년대 GoF 책 시대* 의 한계. 대규모 시스템엔 *과부하*.

---

## 3. *동적 프록시* — 진화의 한 걸음

### 3.1 *아이디어* — 런타임에 *자동으로* 프록시 생성

*프록시 클래스를 손으로 작성하지 말고*, *JVM 이 런타임에 만들어 주면 어떨까?*

**Java 1.3 (2000) 부터** `java.lang.reflect.Proxy` 가 *바로 이걸* 해줌.

### 3.2 JDK 동적 프록시 — *Interface 기반*

```java
import java.lang.reflect.*;

// 1) InvocationHandler — *어떻게 처리할지* 만 정의
public class LoggingHandler implements InvocationHandler {
    private final Object target;

    public LoggingHandler(Object target) { this.target = target; }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        System.out.println("[로그] " + method.getName() + " 시작");
        Object result = method.invoke(target, args);   // 진짜 호출
        System.out.println("[로그] " + method.getName() + " 끝");
        return result;
    }
}

// 2) 사용 — Coffee 인터페이스 의 *프록시 자동 생성*
Coffee real = new RealCoffee();
Coffee proxy = (Coffee) Proxy.newProxyInstance(
    Coffee.class.getClassLoader(),
    new Class<?>[]{Coffee.class},
    new LoggingHandler(real)
);
proxy.order();
// 출력:
// [로그] order 시작
// 카페 가서 커피 주문
// [로그] order 끝
```

**무엇이 다른가?**
- `FriendProxy` 클래스 *0 개* 작성 (자동 생성)
- `LoggingHandler` *1 개* 작성 → *모든 interface* 에 재사용
- *런타임* 에 JVM 이 *바이트코드 합성* 으로 `$Proxy0` 같은 클래스 생성

### 3.3 *JDK 동적 프록시의 *치명적 한계***

```java
// ❌ JDK 동적 프록시 는 *Interface 없으면 못 만듦*
public class CoffeeService {              // ← Interface 안 implements
    public void order() { ... }
}

// 이건 안 됨:
Proxy.newProxyInstance(... new Class[]{CoffeeService.class} ...);  // 에러!
```

JDK Proxy 는 *Interface* 만 지원. *concrete class* (Interface 없는 클래스) 는 *못 감*.

### 3.4 CGLIB — *Class 도 프록시 가능*

**CGLIB** (Code Generation Library) 가 *그 문제* 해결.

```java
import org.springframework.cglib.proxy.*;

// concrete class (Interface 없음!)
public class CoffeeService {
    public void order() {
        System.out.println("카페 주문");
    }
}

// CGLIB 가 *Subclass 만들어* 메서드 *override*
Enhancer enhancer = new Enhancer();
enhancer.setSuperclass(CoffeeService.class);    // 부모로 박음
enhancer.setCallback((MethodInterceptor) (obj, method, args, methodProxy) -> {
    System.out.println("[로그] " + method.getName() + " 시작");
    Object result = methodProxy.invokeSuper(obj, args);   // 부모 메서드 호출
    System.out.println("[로그] " + method.getName() + " 끝");
    return result;
});

CoffeeService proxy = (CoffeeService) enhancer.create();
proxy.order();
```

**CGLIB 의 동작:**
- *컴파일 시점이 아닌 *런타임* 에* `CoffeeService` 의 *Subclass 바이트코드 합성*
- 모든 메서드 *override* → MethodInterceptor 호출
- *부모 (CoffeeService) 메서드* 는 `methodProxy.invokeSuper()` 로 호출

### 3.5 JDK Proxy vs CGLIB — *비교*

| 항목 | JDK Dynamic Proxy | CGLIB |
|---|---|---|
| **대상** | Interface 만 | Concrete class (Interface 도 OK) |
| **동작 방식** | Interface 의 모든 메서드 *동적 구현* | Class 의 *Subclass 합성* |
| **`final` class** | N/A | ❌ 불가 |
| **`final` method** | N/A | ❌ override 불가 |
| **`private` method** | 가능 (interface 에 없음) | ❌ override 불가 |
| **성능** | 첫 호출 *조금* 느림 | 빠름 (compiled bytecode) |
| **라이브러리 추가** | 필요 없음 (JDK 내장) | CGLIB 필요 |

→ *둘 다 한계가 있다.* 그러나 *합쳐 쓰면* 거의 모든 경우 커버.

---

## 4. Spring 의 프록시 — *AOP 의 정체*

### 4.1 *왜* Spring 이 프록시를 쓰나?

**Spring AOP (Aspect-Oriented Programming)** 의 한 줄 답:

> *비즈니스 로직 외부의 *횡단 관심사* (트랜잭션, 로깅, 보안, 캐시) 를 *Aspect 로 분리*. 그 Aspect 가 *프록시* 로 자동 끼어듦.*

```java
@Service
public class OrderService {

    @Transactional      // ← 이게 *프록시 의 신호*
    public Order create(...) {
        // 비즈니스 로직만
    }
}
```

`@Transactional` 어노테이션을 *컴파일러가* 처리하는 게 아님. *Spring 이 *런타임에 프록시* 만들어* `OrderService.create()` 앞뒤에 *트랜잭션 시작 / commit / rollback* 코드 끼움.

### 4.2 *Spring 의 프록시 결정 룰*

```
1. 클래스가 *Interface 를 구현* 하면 → JDK Dynamic Proxy
2. 클래스가 *Interface 안 구현* 하면 → CGLIB
3. 강제 `spring.aop.proxy-target-class=true` → 항상 CGLIB
```

Spring Boot 2.x 부터 *default 가 CGLIB* (`spring.aop.proxy-target-class=true` 기본).
이유: *Interface 가 있어도 CGLIB 으로 통일* — 옛 JDK Proxy 함정 회피.

### 4.3 *@Transactional 의 *진짜 흐름***

```java
// 너가 작성한 코드
@Service
public class OrderService {
    @Transactional
    public Order create() {
        orderRepository.save(...);
        paymentClient.charge(...);
        return order;
    }
}

// Spring 이 *런타임* 에 만든 코드 (개념적)
class OrderService$$EnhancerByCGLIB$$xxx extends OrderService {
    public Order create() {
        TransactionStatus tx = transactionManager.getTransaction(...);
        try {
            Order result = super.create();        // 진짜 메서드 호출
            transactionManager.commit(tx);
            return result;
        } catch (Exception e) {
            transactionManager.rollback(tx);
            throw e;
        }
    }
}
```

너의 `@Transactional` 의 *try/catch + commit/rollback* 은 *Spring 의 CGLIB Subclass* 가 *자동* 끼움. 너 코드엔 *없음*.

### 4.4 *Self-invocation 함정* — 그 *유명한 문제*

```java
@Service
public class OrderService {

    @Transactional
    public void outer() {
        this.inner();     // ❌ this 가 *진짜 객체*, 프록시 *아님*
    }

    @Transactional(propagation = REQUIRES_NEW)
    public void inner() {
        // ...
    }
}
```

`outer()` 안에서 `this.inner()` 호출 →
- `this` 는 *진짜 OrderService 객체* (CGLIB Subclass 가 아님)
- → `inner()` 의 `@Transactional` *무시*
- → 새 트랜잭션 *안 만들어짐*

**왜?**
- *프록시는 *외부 진입점에만* 끼어듦*. 객체 *내부 호출 (this.method)* 은 *프록시를 거치지 않음*.

이게 *주니어가 가장 많이 묻는 *그 질문***.

**해결책 3 가지:**

1. **메서드 분리** — `inner()` 를 *별도 service* 로
```java
@Service
public class OrderService {
    private final InnerService inner;

    @Transactional
    public void outer() {
        inner.inner();   // 다른 객체 → 프록시 거침 ✅
    }
}
```

2. **AspectJ** (compile-time weaving) — 컴파일 시점에 *코드에 직접 박음*. self-invocation 도 동작. 단 *설정 복잡*.

3. **`AopContext.currentProxy()`** — *주변 프록시* 명시 호출. *권장 안 함*.

---

## 5. *실전* — settlement / lemuel-xr 에서 본 사례

### 5.1 *내 환경의 *프록시 사용 위치****

```java
// settlement 의 OutboxPublisherScheduler
@Component
public class OutboxPublisherScheduler {

    @Scheduled(fixedDelayString = "...")        // ← 프록시
    @SchedulerLock(name = "outbox-publisher")    // ← 프록시
    @Transactional                               // ← 프록시
    public void publishPendingEvents() {
        // 비즈니스
    }
}
```

이 메서드 하나에 **3 개 어노테이션 = 3 개 *AOP advice*** 가 *프록시 안* 에 *체인* 되어 동작:

```
외부 호출
  ↓
프록시
  ├─ @Scheduled 의 trigger 시점 체크
  ├─ @SchedulerLock 의 분산 락 획득 (ShedLock advice)
  ├─ @Transactional 의 tx begin
  ↓
진짜 publishPendingEvents() 실행
  ↓
프록시 (역순)
  ├─ tx commit / rollback
  ├─ SchedulerLock release
  └─ 다음 trigger 대기
```

각 advice 가 *프록시 안의 *데코레이터 체인***. *Open-Closed Principle* 의 살아있는 예.

### 5.2 *디버깅 팁* — *내가 진짜 프록시* 인지 확인

```java
@Service
public class OrderService {
    @Transactional
    public Order create() {
        System.out.println(this.getClass().getName());
        // 출력:
        // OrderService$$SpringCGLIB$$0    ← CGLIB 으로 만든 Subclass!
        return ...;
    }
}
```

`getClass()` 이름에 `$$SpringCGLIB$$` 또는 `$Proxy` 가 *프록시 표시*. 디버깅 시 *정상 동작* 검증법.

### 5.3 *`final` 클래스 / 메서드 함정*

```java
@Service
public final class OrderService {     // ❌ final class!
    @Transactional
    public void create() { ... }
}

// Spring boot 시작:
// BeanInstantiationException: Failed to instantiate
// [OrderService$$SpringCGLIB$$0]: Subclass cannot be created.
```

CGLIB 는 *Subclass 합성* → `final` 이면 *불가*. **Spring 에서 `final` class 는 *피해야*.**

```java
@Service
public class OrderService {
    @Transactional
    public final void create() { ... }   // ❌ final method!
}
```

`final` 메서드도 *override 불가* → *프록시 못 끼움* → *@Transactional 무시*. *Silent fail* (예외 없음, 그저 트랜잭션 안 적용). **이게 *진짜 무서운* 함정**.

---

## 6. *동적 프록시 의 *내부 동작* — 한 발 더 깊이*

### 6.1 JDK Proxy 가 *런타임에 만드는 코드*

```java
// JDK 가 합성한 코드 (개념적)
public final class $Proxy0 extends Proxy implements Coffee {
    public $Proxy0(InvocationHandler h) { super(h); }

    public final void order() {
        try {
            super.h.invoke(this, m3, null);   // m3 = Coffee.class.getMethod("order")
        } catch (RuntimeException | Error e) { throw e; }
        catch (Throwable t) { throw new UndeclaredThrowableException(t); }
    }

    // ...
    private static Method m3;
    static {
        try { m3 = Class.forName("Coffee").getMethod("order"); }
        catch (Exception e) { throw new NoSuchMethodError(); }
    }
}
```

핵심:
- 클래스 이름 `$Proxy0`, `$Proxy1`, ... (JVM 내부 자동)
- `super.h` = `InvocationHandler`
- 모든 인터페이스 메서드 → `h.invoke(this, method, args)` 호출

### 6.2 CGLIB 의 *FastClass + MethodProxy*

CGLIB 가 *reflection* 안 쓰는 비결:

```java
// CGLIB 합성 (개념적)
public class OrderService$$EnhancerByCGLIB$$xxx extends OrderService {
    private MethodInterceptor CGLIB$CALLBACK_0;
    private static final MethodProxy CGLIB$create$1$Proxy = ...;

    public Order create(...) {
        return (Order) CGLIB$CALLBACK_0.intercept(this, ..., CGLIB$create$1$Proxy);
    }
}

// FastClass — reflection 없이 *직접 호출* 위한 lookup table
public class OrderService$$FastClassByCGLIB$$ {
    public Object invoke(int index, Object obj, Object[] args) {
        switch (index) {
            case 0: return ((OrderService) obj).create();   // 직접 호출
            // ...
        }
    }
}
```

JDK Proxy 는 `method.invoke(...)` 의 *reflection 비용*. CGLIB 는 *직접 메서드 호출* + *switch dispatch*. **CGLIB 가 JDK Proxy 보다 ~2x 빠름**.

---

## 7. *주니어가 가장 많이 묻는 *5 질문***

### Q1. *@Transactional 안 먹는데요?*

**A:** self-invocation 점검:
1. `this.method()` 패턴? → 다른 service 로 분리
2. `final` 메서드? → 빼기
3. `private` 메서드? → public 으로
4. Spring container 가 *진짜 그 객체를 관리* 하는지? (@Autowired vs new)

### Q2. *Interface 만들어야 하나요?*

**A:** Spring Boot 2.x+ 는 *default CGLIB* 라 *Interface 없어도 OK*. 단:
- *Mocking* 위해 Interface 있는 게 좋음 (Mockito 가 *interface 더 쉬움*)
- *DI 컨테이너의 *유연성** — interface 사용 시 *구현체 swap* 쉬움

### Q3. *AOP 가 *어디서* 적용되는지 어떻게 알아?*

**A:** Spring Actuator 의 `/actuator/beans` 또는 *getClass().getName()* 출력. `$$SpringCGLIB$$` 또는 `$Proxy` 가 *프록시 흔적*.

### Q4. *프록시가 *체인* 인 이유는?*

**A:** *각 advice* 가 *별도 데코레이터*. `@Transactional + @Async + @Cacheable` 모두 있는 메서드는 *3 단 프록시 체인*. *Around advice* 의 *전후 처리* 가 *Russian Doll* 처럼 *겹침*.

### Q5. *AspectJ 와 Spring AOP 차이는?*

**A:**
| | Spring AOP | AspectJ |
|---|---|---|
| 동작 시점 | 런타임 (프록시) | 컴파일 시점 (weaving) |
| 적용 범위 | Spring Bean 만 | 모든 Java 객체 |
| Self-invocation 동작 | ❌ | ✅ |
| 설정 복잡도 | 단순 | 복잡 |

대부분 *Spring AOP* 로 충분. *AspectJ* 는 *특수 케이스*.

---

## 8. *흔한 함정 5 가지 — 시니어 가 자주 잡는 것*

### ❌ 함정 1: *self-invocation*

위에서 자세히. *프록시 패턴 학습의 첫 번째 깨달음*.

### ❌ 함정 2: *final 메서드 + @Transactional → silent fail*

예외도 안 던지고 *그저 작동 안 함*. **무서운 함정** — *발견까지 며칠*.

### ❌ 함정 3: *private 메서드 + @Transactional*

```java
@Transactional
private void doWork() { ... }    // ❌
```
*private* 도 *override 불가* → *프록시 못 끼움* → *어노테이션 무시*.

### ❌ 함정 4: *new MyService() 로 직접 생성*

```java
@Service
public class OrderService {
    @Transactional
    public void create() { ... }
}

// 어디선가
OrderService s = new OrderService();   // ❌ 직접 생성
s.create();   // 프록시 안 거침 → @Transactional 무시
```

*Spring container 가 관리하는 객체* 만 *프록시*. *new* 하면 *생짜 객체*.

### ❌ 함정 5: *생성자 안에서 @Transactional 메서드 호출*

```java
@Service
public class OrderService {
    public OrderService() {
        create();   // ❌ 생성자 안의 this 는 *프록시 전*
    }
    @Transactional
    public void create() { ... }
}
```

*생성자 실행 시점엔 *프록시 객체 가 아직 안 만들어짐**. *@PostConstruct* 도 *동일 한계*.

---

## 9. *시니어 가 보는 *프록시 의 미래***

### 9.1 *Native Image* (GraalVM) 시대

*GraalVM Native Image* 는 *AOT (Ahead-Of-Time)* 컴파일. *런타임 바이트코드 합성* 어려움.

→ Spring AOT (3.0+) 가 *런타임 프록시* 를 *빌드 타임 클래스* 로 *미리 생성*. *CGLIB 없이* 동작 가능.

### 9.2 *Project Loom* 과 *프록시*

Virtual Threads 의 *continuation* 도 *바이트코드 수준* 변환. *AOP 와 다르지만 *기법* 은 비슷*.

### 9.3 *Code Generation 의 Renaissance*

*Annotation Processor* (Lombok, MapStruct), *Compile-time Weaving* (AspectJ), *AOT* (GraalVM)... *런타임 동적 프록시* 의 시대가 *조금씩 *컴파일 시점*** 으로 이동.

단 *Spring AOP 는 *압도적 표준* 으로 유지* 될 것. 학습 가치 큼.

---

## 10. *주니어 에게 *마지막 한 마디**

프록시 패턴은 *시니어 가 자주 잡는 *주니어 의 실수** 의 *진앙*. *self-invocation* 함정에 한 번 빠진 주니어는 *영원히 기억* 한다. *기억할 만한 가치 있는* 함정.

**기억할 3 줄:**

1. **Spring 의 어노테이션 마법은 *프록시*** — 마법 아닌 *코드 합성*
2. **외부 진입점 만 *프록시 거침*** — `this.method()` 는 *못 거침*
3. ***final / private 은 프록시 못 끼움*** — *silent fail* 무섭다

이 3 줄을 *진짜로 *몸에 박으면** 너는 *시니어 의 첫 검문* 통과. 그 다음은 *AOP 의 *Pointcut 표현식**, *@Order 의 *advice 우선순위**, *AspectJ weaving 모드* 같은 *디테일 의 세계*. 천천히 채우면 됨.

*이 글이 너의 첫 *aha 모먼트*** 가 되길.

---

## 참고

- *Design Patterns* — Gamma, Helm, Johnson, Vlissides (GoF, 1994) — Proxy 패턴 정통
- *Spring in Action 6th Ed* — Craig Walls (2022)
- *Spring Boot 3 in Practice* — Somnath Musib (2024)
- [JDK Dynamic Proxy 공식 문서](https://docs.oracle.com/javase/8/docs/technotes/guides/reflection/proxy.html)
- [Spring AOP Reference](https://docs.spring.io/spring-framework/reference/core/aop.html)
- 관련 글:
  - [JVM 구조와 Java 버전 변천사]({% post_url 2026-05-29-jvm-structure-java-version-evolution-production-impact %})
  - [Spring Filter vs Interceptor]({% post_url 2026-05-29-spring-filter-vs-interceptor-network-perspective %})
  - [ShedLock 으로 @Scheduled 분산 락]({% post_url 2026-06-04-kubernetes-scheduled-shedlock-distributed-lock %})
  - [Harness Engineering ② Test Harness]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %})
