---
layout: post
title: "스프링이 자바를 쓰는 방식 — 리플렉션, 애노테이션, JDK 동적 프록시 vs CGLIB, DI·AOP 의 원리"
date: 2026-10-12 00:19:42 +0900
categories: [java]
tags: [java, spring, reflection, annotation, dynamic-proxy, cglib, aop, dependency-injection, transactional, bean-post-processor, aot, graalvm]
---

자바·코틀린 20편 시리즈의 **자바 9번째 글(J9)** 입니다. 스프링은 "마법" 처럼 보이지만, 실제로는 **자바 언어와 JDK 가 제공하는 몇 가지 기능**(리플렉션, 런타임 애노테이션, 동적 프록시, 바이트코드 생성)을 조합한 것입니다. 이 글은 그 조합을 자바 쪽에서 해부합니다. 각 메커니즘이 **무엇이고, 스프링이 어디에 쓰며, 어떤 함정을 만드는지** 를 순서대로 봅니다.

코틀린에서 같은 메커니즘이 왜 추가 플러그인(all-open, no-arg)을 필요로 하는지는 짝이 되는 [K9 — 코틀린 × 스프링](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) 에서 다룹니다. 프록시 패턴 자체를 처음부터 보고 싶다면 이전 글 [주니어를 위한 프록시 패턴 안내](https://myoungsoo7.github.io/2026/06/06/proxy-pattern-dynamic-proxy-spring-aop-explained/) 를 먼저 읽어도 좋습니다.

---

## 1. 큰 그림 — 스프링 컨테이너가 하는 일

애플리케이션이 뜰 때 스프링은 대략 다음을 합니다.

1. **스캔**: 클래스패스에서 `@Component` 계열 애노테이션이 붙은 클래스를 찾는다. → *애노테이션 + 리플렉션*
2. **빈 정의**: 각 클래스의 생성자·의존성·스코프를 해석한다. → *리플렉션, 파라미터 이름*
3. **인스턴스화 + 주입**: 생성자를 골라 호출하고 의존성을 넣는다. → *리플렉션(Constructor/Field/Method)*
4. **후처리**: `BeanPostProcessor` 가 빈을 감싸거나 바꾼다. 트랜잭션·비동기·AOP 는 여기서 **프록시**로 바뀐다. → *JDK 동적 프록시 / CGLIB*
5. **설정 클래스 강화**: `@Configuration` 클래스는 CGLIB 하위 클래스로 바뀐다. → *바이트코드 생성*

| 자바 기능 | 도입 | 스프링에서의 용도 |
|---|---|---|
| 리플렉션 (`java.lang.reflect.Method` 등) | JDK 1.1 ([Method Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Method.html)) | 빈 생성, 의존성 주입, 애노테이션 읽기 |
| JDK 동적 프록시 (`Proxy`) | JDK 1.3 ([Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html)) | 인터페이스 기반 AOP 프록시 |
| 애노테이션 (`java.lang.annotation`) | JDK 1.5 ([Annotation Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/annotation/Annotation.html)) | `@Component`, `@Transactional` 등 메타데이터 |
| 파라미터 이름 (`-parameters`, `java.lang.reflect.Parameter`) | JDK 8 ([JEP 118](https://openjdk.org/jeps/118)) | 생성자·핸들러 파라미터 바인딩 |
| 바이트코드 생성 (CGLIB, 스프링이 재패키징) | 외부 라이브러리 | 클래스 기반 프록시, `@Configuration` 강화 |

---

## 2. 애노테이션 — 메타데이터를 런타임까지 들고 가기

### 2.1 무엇인가

애노테이션은 코드에 붙이는 메타데이터입니다. 리플렉션으로 읽으려면 **`@Retention(RetentionPolicy.RUNTIME)`** 이어야 합니다. `RetentionPolicy` Javadoc 에 따르면:

- `SOURCE`: 컴파일러가 버린다.
- `CLASS`: 클래스 파일에는 기록되지만 런타임에 VM 이 유지할 필요는 없다. **이게 기본값이다.**
- `RUNTIME`: 클래스 파일에 기록되고 런타임에도 유지되어 **리플렉션으로 읽을 수 있다.**

([RetentionPolicy Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/annotation/RetentionPolicy.html))

### 2.2 코드 — 직접 만든 애노테이션 읽기

```java
import java.lang.annotation.*;
import java.lang.reflect.Method;

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
@interface Audited {
    String action();
}

class OrderService {
    @Audited(action = "ORDER_CANCEL")
    public void cancel(long orderId) { /* ... */ }
}

public class AnnotationDemo {
    public static void main(String[] args) throws Exception {
        Method m = OrderService.class.getMethod("cancel", long.class);
        Audited a = m.getAnnotation(Audited.class);
        System.out.println(a.action());   // ORDER_CANCEL
    }
}
```

### 2.3 스프링의 애노테이션 모델 — 메타 애노테이션과 합성

자바 애노테이션은 **상속을 지원하지 않습니다.** 그래서 스프링은 "애노테이션에 붙은 애노테이션(메타 애노테이션)" 을 따라가는 자체 검색 알고리즘을 갖고 있습니다 ([Spring Annotation Programming Model](https://github.com/spring-projects/spring-framework/wiki/Spring-Annotation-Programming-Model)).

- **메타 애노테이션**: 다른 애노테이션에 선언된 애노테이션.
- **스테레오타입**: 컴포넌트의 역할을 선언(`@Repository`, `@Service`, `@Controller`). 이들은 `@Component` 로 메타 애노테이션되어 있어 컴포넌트 스캔 대상이 됩니다.
- **합성 애노테이션(composed annotation)**: 여러 메타 애노테이션의 동작을 합친 것.
- **`@AliasFor`**(Spring 4.2+): 합성 애노테이션의 속성을 메타 애노테이션의 속성과 연결.

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Service
@Transactional(readOnly = true)
public @interface ReadOnlyService {
    @AliasFor(annotation = Service.class, attribute = "value")
    String value() default "";
}

@ReadOnlyService
public class ProductQueryService { /* 모든 public 메서드가 읽기 전용 트랜잭션 */ }
```

### 2.4 함정

1. **`@Retention` 을 빼먹으면 기본값 `CLASS`** 라 런타임에 보이지 않습니다. 직접 만든 애노테이션 기반 AOP 가 "아무 일도 안 한다" 면 가장 먼저 확인할 것.
2. **`java.lang.reflect` 로 직접 읽으면 메타 애노테이션을 못 찾습니다.** `m.getAnnotation(Transactional.class)` 는 `@ReadOnlyService` 를 통해 간접적으로 붙은 `@Transactional` 을 찾지 못합니다. 스프링의 `AnnotatedElementUtils`/`MergedAnnotations` 같은 유틸을 써야 스프링과 같은 규칙으로 찾습니다.
3. **인터페이스 메서드의 애노테이션은 구현 클래스로 상속되지 않습니다**(자바 언어 규칙). 스프링 팀이 `@Transactional` 을 인터페이스보다 **구체 클래스의 메서드**에 붙이라고 권하는 이유 중 하나입니다(5.4 참고).

---

## 3. 리플렉션 — 런타임에 클래스를 다루기

### 3.1 무엇인가

`Class`, `Constructor`, `Method`, `Field` 객체로 런타임에 타입 정보를 읽고, 생성자·메서드를 호출하고, 필드 값을 읽고 쓰는 기능입니다. 접근 제어(`private`)는 `setAccessible(true)` 로 우회할 수 있지만, **모듈 시스템 이후에는 제약**이 있습니다(3.4).

### 3.2 코드 — 미니 DI 컨테이너

스프링 DI 의 뼈대를 리플렉션만으로 흉내 내면 이렇습니다.

```java
import java.lang.reflect.Constructor;
import java.lang.reflect.Parameter;
import java.util.HashMap;
import java.util.Map;

public class MiniContainer {
    private final Map<Class<?>, Object> singletons = new HashMap<>();

    @SuppressWarnings("unchecked")
    public <T> T getBean(Class<T> type) {
        Object existing = singletons.get(type);
        if (existing != null) return (T) existing;

        try {
            Constructor<?>[] ctors = type.getDeclaredConstructors();
            if (ctors.length != 1) {
                throw new IllegalStateException(type + ": 생성자가 하나여야 합니다");
            }
            Constructor<?> ctor = ctors[0];
            Parameter[] params = ctor.getParameters();
            Object[] args = new Object[params.length];
            for (int i = 0; i < params.length; i++) {
                args[i] = getBean(params[i].getType());   // 재귀적으로 의존성 해결
            }
            ctor.setAccessible(true);
            T bean = (T) ctor.newInstance(args);
            singletons.put(type, bean);
            return bean;
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
    }
}
```

실제 스프링은 여기에 스코프, 한정자(`@Qualifier`), 순환 참조 감지, 후처리기, 이벤트 등 수많은 기능을 얹지만, **"생성자를 리플렉션으로 찾아 의존성을 재귀적으로 만들어 넣는다"** 는 핵심은 같습니다.

### 3.3 스프링의 DI 권장 — 생성자 주입

스프링 레퍼런스는 다음과 같이 권합니다 ([Spring Framework — Dependency Injection](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html)).

> 스프링 팀은 일반적으로 생성자 주입을 지지한다. 애플리케이션 컴포넌트를 불변 객체로 구현할 수 있고, 필수 의존성이 `null` 이 아님을 보장하기 때문이다. 또한 생성자 주입된 컴포넌트는 항상 완전히 초기화된 상태로 호출 코드에 반환된다.

세터 주입은 "합리적인 기본값을 줄 수 있는 선택적 의존성" 에만 쓰라고 합니다. 그리고 생성자가 하나뿐이면 `@Autowired` 를 붙일 필요가 없습니다 ([Spring Framework — Using @Autowired](https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html)).

```java
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentClient paymentClient;

    // 생성자 하나 → @Autowired 불필요
    public OrderService(OrderRepository orderRepository, PaymentClient paymentClient) {
        this.orderRepository = orderRepository;
        this.paymentClient = paymentClient;
    }
}
```

선택적 의존성은 `Optional<T>` 이나 `@Nullable` 로, 같은 타입 여러 개는 `List<T>`·`Map<String, T>` 로 주입받을 수 있습니다(같은 문서).

### 3.4 함정

1. **생성자 주입 순환 참조**: A 가 B 를, B 가 A 를 생성자로 요구하면 스프링은 `BeanCurrentlyInCreationException` 을 던집니다 ([같은 문서](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html)). 세터 주입으로 "해결" 하기보다 설계를 고치는 게 맞습니다. 순환은 대개 책임 분리가 잘못됐다는 신호입니다.
2. **파라미터 이름**: 스프링 6.0 부터 `-parameters` 컴파일 플래그 사용이 권장되고, 디버그 정보를 읽던 `LocalVariableTableParameterNameDiscoverer` 는 deprecated 되었습니다 ([Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)). 빌드에 `-parameters` 가 켜져 있지 않은 상태에서 `@PathVariable Long id`, `@RequestParam String name` 처럼 이름을 생략하면 바인딩이 실패할 수 있습니다. 이름을 명시(`@PathVariable("id")`)하거나 `-parameters` 를 켜세요.
3. **모듈 시스템과 `setAccessible`**: `AccessibleObject.setAccessible` 은 호출자와 선언 클래스가 다른 모듈이고 그 패키지가 호출자에게 열려(open) 있지 않으면 `private` 멤버 접근을 허용하지 않고 `InaccessibleObjectException` 을 던집니다 ([AccessibleObject Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/AccessibleObject.html)). JDK 17 의 [JEP 403](https://openjdk.org/jeps/403) 은 `--illegal-access` 를 제거해 JDK 내부의 강한 캡슐화를 영구화했습니다. 애플리케이션 코드는 대부분 클래스패스(이름 없는 모듈)에 있어 스프링이 접근할 수 있지만, **라이브러리가 JDK 내부 클래스를 리플렉션으로 건드리면** 17 이상에서 실패합니다.
4. **`final` 필드 변경**: `setAccessible` 로도 `static final`, record 의 `final` 필드 등은 쓰기가 허용되지 않습니다([AccessibleObject Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/AccessibleObject.html)). 더 나아가 JDK 26 의 [JEP 500](https://openjdk.org/jeps/500) 은 딥 리플렉션으로 일반 `final` 필드를 바꾸면 **기본으로 경고**를 내고(`--illegal-final-field-mutation` 기본값 `warn`), 이후 릴리스에서 `deny` 를 기본으로 만들 예정이라고 밝힙니다. **필드 주입(`@Autowired` 를 `final` 이 아닌 필드에)** 은 이 문제와 무관하지만, `final` 필드를 리플렉션으로 채우는 직렬화·테스트 유틸이 있다면 미리 점검해야 합니다. 생성자 주입이 여기서도 안전한 선택입니다.

---

## 4. 프록시 — 호출을 가로채는 두 가지 방법

스프링의 `@Transactional`, `@Async`, `@Cacheable`, 사용자 정의 `@Aspect` 는 모두 **프록시**로 동작합니다. 빈 대신 "빈을 감싼 객체" 가 주입되고, 그 객체가 호출 전후에 부가 기능을 실행합니다.

### 4.1 JDK 동적 프록시

`java.lang.reflect.Proxy` 는 JDK 1.3 부터 있었고, **인터페이스만** 프록시할 수 있습니다. 모든 메서드 호출은 `InvocationHandler.invoke(Object proxy, Method method, Object[] args)` 로 모입니다 ([Proxy Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html)).

```java
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;

interface PaymentGateway {
    String pay(long amount);
}

class RealGateway implements PaymentGateway {
    public String pay(long amount) { return "tx-" + amount; }
}

public class JdkProxyDemo {
    public static void main(String[] args) {
        PaymentGateway target = new RealGateway();

        InvocationHandler timing = (proxy, method, methodArgs) -> {
            long start = System.nanoTime();
            try {
                return method.invoke(target, methodArgs);     // 실제 대상 호출
            } finally {
                System.out.printf("%s took %d µs%n",
                        method.getName(), (System.nanoTime() - start) / 1_000);
            }
        };

        PaymentGateway proxy = (PaymentGateway) Proxy.newProxyInstance(
                PaymentGateway.class.getClassLoader(),
                new Class<?>[] { PaymentGateway.class },
                timing);

        System.out.println(proxy.pay(1000));
        System.out.println(proxy.getClass());            // $Proxy0 류의 런타임 생성 클래스
        System.out.println(proxy instanceof RealGateway); // false — 인터페이스만 구현
    }
}
```

**주의**: `method.invoke` 는 대상 메서드가 던진 예외를 `InvocationTargetException` 으로 감쌉니다. 실제 프레임워크는 이를 풀어서(`getCause()`) 다시 던집니다. 위 예제는 단순화를 위해 생략했습니다.

### 4.2 CGLIB — 하위 클래스 생성

CGLIB 은 런타임에 **대상 클래스의 하위 클래스**를 바이트코드로 만들어 메서드를 오버라이드합니다. 스프링은 CGLIB 을 `spring-core` 안에 재패키징해 포함하므로 별도 의존성이 필요 없습니다 ([Spring Framework — Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)).

### 4.3 스프링은 어느 쪽을 쓰나

스프링 프레임워크 문서의 규칙 ([Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)):

- 대상이 **인터페이스를 하나 이상 구현**하면 → JDK 동적 프록시 (구현한 모든 인터페이스를 프록시)
- 인터페이스가 **없으면** → CGLIB
- `@EnableAspectJAutoProxy(proxyTargetClass = true)`, `@EnableTransactionManagement(proxyTargetClass = true)` 등으로 CGLIB 을 강제할 수 있다.
- **스프링 프레임워크 7.0** 부터는 빈 단위로 `@Proxyable(INTERFACES)`, `@Proxyable(TARGET_CLASS)` 를 붙여 전역 기본값을 덮어쓸 수 있다.

그런데 **스프링 부트는 기본값이 다릅니다.** 부트 레퍼런스는 "기본적으로 스프링 부트의 자동 구성은 Spring AOP 가 CGLib 프록시를 쓰도록 구성한다. JDK 프록시를 쓰려면 `spring.aop.proxy-target-class` 를 `false` 로 설정하라" 고 명시합니다 ([Spring Boot — AOP](https://docs.spring.io/spring-boot/reference/features/aop.html)).

| | 순수 스프링 프레임워크 | 스프링 부트 기본 |
|---|---|---|
| 인터페이스 있는 빈 | JDK 동적 프록시 | **CGLIB** |
| 인터페이스 없는 빈 | CGLIB | CGLIB |
| 바꾸는 법 | `proxyTargetClass = true` | `spring.aop.proxy-target-class=false` |

### 4.4 CGLIB 프록시의 제약 — 자바 언어 규칙에서 나온다

하위 클래스를 만들어 오버라이드하는 방식이므로, **자바에서 오버라이드할 수 없는 것은 가로챌 수 없습니다** ([Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)).

- `final` **클래스**는 프록시할 수 없다(상속 불가).
- `final` **메서드**는 어드바이스를 적용할 수 없다(오버라이드 불가).
- `private` 메서드는 어드바이스를 적용할 수 없다.
- 다른 패키지의 상위 클래스에 있는 package-private 메서드도 사실상 `private` 이라 불가.
- 프록시 인스턴스는 Objenesis 로 만들어 생성자가 두 번 호출되지 않는다.
- 모듈 경로의 `java.lang` 패키지 클래스는 `--add-opens=java.base/java.lang=ALL-UNNAMED` 없이 CGLIB 프록시를 만들 수 없다.

**코틀린과의 연결**: 코틀린 클래스와 메서드는 **기본이 `final`** 입니다. 그래서 위 규칙에 그대로 걸리고, 이를 풀기 위해 `kotlin-spring`(all-open) 플러그인이 필요합니다. 자세한 내용은 [K9](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/).

---

## 5. 프록시가 만드는 대표 함정 — self-invocation

### 5.1 무엇이 문제인가

프록시는 **외부에서 프록시를 통해 들어온 호출만** 가로챕니다. 같은 객체 안에서 `this.method()` 로 부르면 프록시를 거치지 않습니다 ([Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)).

```java
@Service
public class CouponService {

    public void issueAll(List<Long> userIds) {
        for (Long id : userIds) {
            issue(id);   // this.issue(id) — 프록시를 거치지 않는다!
        }
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void issue(Long userId) {
        // 사용자별 독립 트랜잭션을 기대했지만, 실제로는 트랜잭션이 적용되지 않는다
    }
}
```

트랜잭션 문서도 같은 내용을 명시합니다. 프록시 모드(기본값)에서는 프록시를 통한 외부 호출만 가로채므로, **자기 호출은 `@Transactional` 이 붙어 있어도 실제 트랜잭션으로 이어지지 않습니다** ([Spring Framework — Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)). `@Async` 도 마찬가지입니다. 같은 클래스 안의 로컬 호출은 가로챌 수 없습니다 ([Spring Framework — Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)).

### 5.2 해결책 (공식 문서가 제시하는 순서)

1. **자기 호출을 없애도록 리팩터링(권장)** — 트랜잭션 경계가 필요한 메서드를 다른 빈으로 분리.

   ```java
   @Service
   public class CouponBatchService {
       private final CouponIssuer issuer;
       public CouponBatchService(CouponIssuer issuer) { this.issuer = issuer; }

       public void issueAll(List<Long> userIds) {
           userIds.forEach(issuer::issue);   // 다른 빈 → 프록시 경유
       }
   }

   @Service
   public class CouponIssuer {
       @Transactional(propagation = Propagation.REQUIRES_NEW)
       public void issue(Long userId) { /* 사용자별 독립 트랜잭션 */ }
   }
   ```

2. **자기 자신 주입(self injection)** — 프록시를 통해 호출. `@Autowired` 는 자기 참조를 fallback 으로만 고려합니다 ([Using @Autowired](https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html)).
3. **`AopContext.currentProxy()`** — `exposeProxy` 설정이 필요하고 코드가 스프링 AOP 에 강하게 묶이므로 **강하게 비권장**.
4. **AspectJ 위빙** — 컴파일 타임/로드 타임 위빙은 프록시가 아니라 바이트코드에 직접 어드바이스를 넣으므로 자기 호출 문제가 없습니다.

### 5.3 메서드 가시성

스프링 6.0 부터 **클래스 기반 프록시에서는 `protected`·package-private 메서드도** 기본으로 트랜잭션이 적용될 수 있습니다. 단 인터페이스 기반 프록시에서는 트랜잭션 메서드가 반드시 `public` 이고 인터페이스에 정의되어 있어야 합니다 ([Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)). `private` 메서드는 어떤 경우에도 프록시로 가로챌 수 없습니다(4.4).

### 5.4 인터페이스에 붙인 애노테이션

스프링 팀은 `@Transactional` 을 인터페이스 메서드보다 **구체 클래스의 메서드**에 붙이라고 권합니다. 5.0 이후 인터페이스 기반·클래스 기반 프록시 모두에서 동작은 하지만, 자바 애노테이션은 인터페이스에서 상속되지 않으므로 AspectJ 모드에서는 인식되지 않기 때문입니다 ([Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)).

---

## 6. `BeanPostProcessor` — 프록시가 끼어드는 지점

### 6.1 무엇인가

`BeanPostProcessor` 는 빈이 만들어진 직후 그 빈을 검사하거나 **다른 객체로 바꿔치기**할 수 있는 확장 지점입니다. 스프링 문서는 "일부 Spring AOP 인프라 클래스는 프록시로 감싸는 로직을 제공하기 위해 빈 후처리기로 구현되어 있다" 고 설명합니다 ([Spring Framework — Container Extension Points](https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html)).

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
@interface LogSlowCalls {}

@Component
public class SlowCallLoggingPostProcessor implements BeanPostProcessor {

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        Class<?>[] interfaces = bean.getClass().getInterfaces();
        if (!bean.getClass().isAnnotationPresent(LogSlowCalls.class) || interfaces.length == 0) {
            return bean;
        }
        return Proxy.newProxyInstance(
                bean.getClass().getClassLoader(),
                interfaces,
                (proxy, method, args) -> {
                    long start = System.nanoTime();
                    try {
                        return method.invoke(bean, args);
                    } finally {
                        long ms = (System.nanoTime() - start) / 1_000_000;
                        if (ms > 500) {
                            System.out.println(beanName + "." + method.getName() + " " + ms + "ms");
                        }
                    }
                });
    }
}
```

(교육용 예제입니다. 실무에서는 `@Aspect` 나 Micrometer 관측 API 를 쓰는 편이 낫습니다.)

### 6.2 함정 — 일찍 만들어진 빈은 프록시가 안 된다

AOP 자동 프록시도 `BeanPostProcessor` 이므로, **`BeanPostProcessor` 자신과 그것이 직접 참조하는 빈은 자동 프록시 대상이 아닙니다.** 이런 경우 "Bean 'someBean' ... is not eligible for getting processed by all BeanPostProcessors (for example: not eligible for auto-proxying)" 로그가 남습니다. 문서는 `BeanPostProcessor` 를 의존성 없는 `static @Bean` 메서드로 선언하라고 권합니다 ([Container Extension Points](https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html)).

실무에서 "`@Transactional` 이 특정 서비스에서만 안 먹는다" 의 원인이, 그 서비스가 커스텀 `BeanPostProcessor` 에 주입되어 있던 경우가 이것입니다. 위 로그 문구로 검색해 보세요.

---

## 7. `@Configuration` 과 CGLIB

### 7.1 무엇인가

`@Configuration` 클래스는 시작 시점에 **CGLIB 으로 하위 클래스가 만들어집니다.** 하위 클래스의 `@Bean` 메서드는 부모 메서드를 호출하기 전에 컨테이너에 캐시된 빈이 있는지 먼저 확인합니다 ([Spring Framework — Using the @Configuration annotation](https://docs.spring.io/spring-framework/reference/core/beans/java/configuration-annotation.html)).

```java
@Configuration
public class AppConfig {
    @Bean
    public ClientService clientService1() {
        ClientServiceImpl s = new ClientServiceImpl();
        s.setClientDao(clientDao());   // 두 번 호출되지만
        return s;
    }

    @Bean
    public ClientService clientService2() {
        ClientServiceImpl s = new ClientServiceImpl();
        s.setClientDao(clientDao());   // 같은 싱글톤이 반환된다
        return s;
    }

    @Bean
    public ClientDao clientDao() {
        return new ClientDaoImpl();
    }
}
```

### 7.2 lite 모드: `proxyBeanMethods = false`

```java
@Configuration(proxyBeanMethods = false)
public class WebClientConfig {
    @Bean
    WebClient webClient(WebClient.Builder builder) {   // 메서드 파라미터로 의존성 주입
        return builder.baseUrl("https://api.example.com").build();
    }
}
```

`proxyBeanMethods = false` 면 CGLIB 하위 클래스를 만들지 않습니다. 대신 `@Bean` 메서드 간 호출이 가로채지지 않으므로, 의존성은 **메서드 파라미터나 생성자로 주입**받아야 합니다(같은 문서).

### 7.3 함정

- `@Configuration` 클래스는 `final` 이면 안 됩니다(같은 문서). 코틀린에서 all-open 플러그인이 `@Configuration` 을 여는 이유입니다.
- lite 모드에서 `clientDao()` 를 직접 호출하면 **매번 새 인스턴스**가 생깁니다. 싱글톤을 기대한 코드가 조용히 깨집니다.

---

## 8. AOT 와 네이티브 이미지 — 리플렉션 없는 스프링

### 8.1 무엇이 다른가

GraalVM 네이티브 이미지는 빌드 시점에 `main` 에서 도달 가능한 코드를 정적 분석하고, **닫힌 세계(closed-world) 가정** 아래 동작합니다. 스프링 부트 문서 기준 핵심 차이는 다음과 같습니다 ([Spring Boot — Introducing GraalVM Native Images](https://docs.spring.io/spring-boot/reference/packaging/native-image/introducing-graalvm-native-images.html)).

- 클래스패스가 빌드 시점에 고정된다.
- 빈 정의가 런타임에 바뀔 수 없다(`@Profile`, `@ConditionalOnProperty` 등에 제약).
- **리플렉션, 리소스, 직렬화, 동적 프록시, JNI** 는 GraalVM 이 알 수 있도록 힌트로 알려 줘야 한다.

### 8.2 스프링의 해법 — AOT 처리

스프링은 빌드 시점에 **AOT 처리**를 해서, 런타임 리플렉션 대신 직접 호출하는 자바 소스(빈 정의 코드), 프록시용 바이트코드, 그리고 `reflect-config.json`·`proxy-config.json` 같은 힌트 파일을 생성합니다(같은 문서). 앞서 본 "리플렉션으로 생성자를 찾아 호출" 하던 부분이 **빌드 시점에 생성된 평범한 자바 코드**로 바뀌는 셈입니다.

이 지원은 스프링 프레임워크 6.0 에서 AOT 처리와 GraalVM 네이티브 이미지 1급 지원으로 들어왔습니다 ([Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)). 부트 버전별 GraalVM 요구 버전은 [J10](https://myoungsoo7.github.io/2026/10/12/spring-boot-java-version-compatibility/) 에서 정리합니다.

### 8.3 함정

- 직접 `Class.forName(name)` 이나 `Method.invoke` 로 동적으로 호출하는 코드는 네이티브 이미지에서 힌트 없이 실패합니다.
- 프로퍼티 값에 따라 빈이 생기고 안 생기는 설계(`.enabled` 류)는 네이티브 이미지에서 빌드 시점 값으로 고정됩니다.

---

## 9. 정리 — 자바 기능과 스프링 기능의 대응표

| 스프링 기능 | 자바 메커니즘 | 대표 함정 |
|---|---|---|
| 컴포넌트 스캔 | 런타임 애노테이션 + 리플렉션 | `@Retention` 누락, 메타 애노테이션은 스프링 유틸로 읽기 |
| 생성자 주입 | `Constructor` 리플렉션 + 파라미터 이름 | 순환 참조, `-parameters` 누락 |
| `@Transactional`/`@Async`/`@Cacheable` | JDK 동적 프록시 / CGLIB | self-invocation, `final`/`private` 메서드 |
| `@Configuration` 싱글톤 보장 | CGLIB 하위 클래스 | `final` 클래스, lite 모드에서 직접 호출 |
| AOP 자동 프록시 | `BeanPostProcessor` | 후처리기에 주입된 빈은 프록시 안 됨 |
| 네이티브 이미지 | AOT 코드 생성 + 힌트 | 동적 리플렉션, 런타임 조건부 빈 |

스프링을 "마법" 이 아니라 **리플렉션 + 프록시 + 바이트코드 생성의 조합**으로 이해하면, 함정의 대부분이 "자바 언어 규칙(오버라이드 불가, 애노테이션 비상속, 모듈 캡슐화)" 에서 나온다는 것이 보입니다. 같은 규칙이 코틀린에서 어떻게 드러나는지는 [K9](https://myoungsoo7.github.io/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/) 에서 이어집니다. AOP 자체의 개념(Aspect, Pointcut, Advice)은 이전 글 [Spring AOP — Aspect·Pointcut](https://myoungsoo7.github.io/2026/06/06/spring-aop-aspect-pointcut-senior-explains-with-examples/) 을 참고하세요.

---

## References

- [java.lang.reflect.Proxy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html) — Oracle Javadoc (JDK 21)
- [java.lang.reflect.AccessibleObject](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/AccessibleObject.html) — Oracle Javadoc (JDK 21)
- [java.lang.reflect.Method](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Method.html), [java.lang.annotation.Annotation](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/annotation/Annotation.html) — Oracle Javadoc (JDK 21)
- [java.lang.annotation.RetentionPolicy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/annotation/RetentionPolicy.html) — Oracle Javadoc (JDK 21)
- [JEP 118: Access to Parameter Names at Runtime](https://openjdk.org/jeps/118) — OpenJDK
- [JEP 403: Strongly Encapsulate JDK Internals](https://openjdk.org/jeps/403) — OpenJDK
- [JEP 500: Prepare to Make Final Mean Final](https://openjdk.org/jeps/500) — OpenJDK
- [Spring Framework — Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html) — docs.spring.io
- [Spring Framework — Dependency Injection](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html) — docs.spring.io
- [Spring Framework — Using @Autowired](https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html) — docs.spring.io
- [Spring Framework — Using the @Configuration annotation](https://docs.spring.io/spring-framework/reference/core/beans/java/configuration-annotation.html) — docs.spring.io
- [Spring Framework — Container Extension Points](https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html) — docs.spring.io
- [Spring Framework — Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html) — docs.spring.io
- [Spring Framework — Task Execution and Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html) — docs.spring.io
- [Spring Annotation Programming Model](https://github.com/spring-projects/spring-framework/wiki/Spring-Annotation-Programming-Model) — spring-projects wiki
- [Spring Framework 6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes) — spring-projects wiki
- [Spring Boot — Aspect-Oriented Programming](https://docs.spring.io/spring-boot/reference/features/aop.html) — docs.spring.io
- [Spring Boot — Introducing GraalVM Native Images](https://docs.spring.io/spring-boot/reference/packaging/native-image/introducing-graalvm-native-images.html) — docs.spring.io

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/)
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/)
- J9. [스프링이 자바를 쓰는 방식 — 리플렉션·프록시·DI](/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) ← 지금 글
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/)

**코틀린**

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/)
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
