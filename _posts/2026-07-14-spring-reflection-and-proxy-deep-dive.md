---
layout: post
title: "Reflection과 Proxy 심화 — 스프링의 마법과 @Transactional이 조용히 안 먹는 이유"
date: 2026-07-14 10:20:00 +0900
categories: [backend, spring, java]
tags: [reflection, proxy, spring, aop, jdk-dynamic-proxy, cglib, transactional, self-invocation, dependency-injection]
---

`@Transactional` 한 줄 붙였는데 롤백이 안 된다. `@Async` 붙였는데 그냥 동기로 돈다. `@Cacheable`인데 캐시를 씹는다. 스프링을 좀 써 본 사람이면 한 번쯤 당하는 이 "조용한 실패"의 정체는 버그가 아니라 **스프링이 어떻게 만들어졌는지**를 모르는 데서 온다.

이 글은 스프링의 두 기둥 **Reflection(리플렉션)** 과 **Proxy(프록시)** 를 밑바닥부터 정리하고, 그 위에서 왜 어노테이션이 가끔 무력화되는지를 코드로 보여준다.

미리 결론 한 줄:

> 스프링의 어노테이션 기능은 대부분 **"대상 객체를 프록시로 감싸 호출을 가로채는 것"** 이다. 그래서 프록시를 안 거치는 호출(같은 클래스 내부 호출, private/final 메서드)에서는 마법이 조용히 사라진다.

---

## 1. Reflection — 런타임에 코드가 코드를 들여다본다

리플렉션은 **실행 중에** 클래스·메서드·필드를 이름으로 조회하고 조작하는 기능이다. 컴파일 시점에 타입을 몰라도 다룰 수 있다는 게 핵심이다.

```java
Class<?> clazz = Class.forName("com.sparta.User");
Object user = clazz.getDeclaredConstructor().newInstance();

Field field = clazz.getDeclaredField("name");
field.setAccessible(true);          // private 캡슐화를 강제로 연다
field.set(user, "MyoungSoo");

Method method = clazz.getDeclaredMethod("greet", String.class);
method.invoke(user, "hello");       // user.greet("hello") 를 이름으로 호출
```

`private` 필드에 값을 넣는 `field.setAccessible(true)`가 눈에 띌 것이다. **바로 이게 스프링이 생성자도 setter도 없이 `private` 필드에 의존성을 꽂아 넣는 방법이다.**

### 왜 필요한가, 그리고 왜 비싼가

프레임워크의 본질은 "내가 모르는 남의 클래스를 다뤄야 한다"는 것이다. 스프링은 당신이 만들 `UserService`를 컴파일 시점에 알 수 없다. 그래서 런타임에 클래스를 스캔하고 리플렉션으로 인스턴스를 만들고 필드를 채운다.

대신 대가가 있다:

- **느리다.** JIT 최적화·인라이닝을 우회하고 접근 검사를 매번 한다.
- **캡슐화를 깬다.** `setAccessible`로 `private`을 뚫는다.
- **타입 안전성이 사라진다.** 컴파일러가 못 잡고 런타임에 `NoSuchMethodException`으로 터진다.
- **Java 9+ 모듈 시스템**에서는 강한 캡슐화(`--illegal-access`)로 `setAccessible`이 막힐 수 있다.

그래서 잘 만든 프레임워크는 리플렉션을 **부팅 시점에 한 번** 수행해 결과(메서드 핸들·메타데이터)를 **캐싱**하고, 요청마다 반복하지 않는다.

---

## 2. 스프링은 리플렉션을 어디서 쓰나

- **컴포넌트 스캔**: 패키지를 훑어 `@Component`/`@Service`/`@Repository`가 붙은 클래스를 찾는다.
- **의존성 주입(DI)**: 생성자·필드·setter를 리플렉션으로 호출해 빈을 꽂는다. 필드 주입(`@Autowired` on field)은 `field.setAccessible(true); field.set(bean, dep)` 그 자체다.
- **어노테이션 메타데이터 해석**: `@Value("${...}")`, `@Transactional(readOnly=true)` 같은 속성을 읽는다.
- **`@Entity` 매핑, 직렬화(Jackson), 검증(Bean Validation)** 등 거의 모든 "어노테이션 기반" 동작.

정리하면 **리플렉션 = 스프링이 당신의 클래스를 "발견하고 생성하고 채우는" 능력**이다. 그런데 발견·생성만으로는 `@Transactional` 같은 **부가기능**을 넣을 수 없다. 여기서 두 번째 기둥이 등장한다.

---

## 3. Proxy — 원본을 감싸 호출을 가로챈다

프록시는 대상 객체를 대신 받는 **대리자**다. 클라이언트는 프록시를 진짜 객체로 착각하고 호출하지만, 프록시는 원본 메서드 **앞뒤로 부가기능**(트랜잭션 시작/커밋, 로깅, 권한 체크)을 끼워 넣는다.

```
호출자 → [프록시] → (부가기능: 트랜잭션 begin)
                  → 원본 객체.메서드()  ← 진짜 비즈니스 로직
                  → (부가기능: commit / rollback)
```

핵심은 **원본 코드는 부가기능을 전혀 모른다**는 것. 비즈니스 로직과 횡단 관심사(cross-cutting concern)를 분리하는 이게 바로 **AOP**다.

---

## 4. 두 종류의 프록시 — JDK Dynamic Proxy vs CGLIB

스프링이 런타임에 프록시를 **만들어내는** 방법은 두 가지다.

### JDK Dynamic Proxy (인터페이스 기반)

`java.lang.reflect.Proxy`가 대상의 **인터페이스**를 구현한 가짜 객체를 만든다. 모든 호출은 `InvocationHandler.invoke()`로 모인다.

```java
Object proxy = Proxy.newProxyInstance(
    loader, new Class[]{ UserService.class },
    (p, method, args) -> {
        System.out.println("before");           // 부가기능
        Object result = method.invoke(target, args); // 원본 호출 (리플렉션!)
        System.out.println("after");
        return result;
    });
```

`method.invoke`가 보이는가? **프록시의 심장은 결국 리플렉션이다.** 두 기둥은 이렇게 만난다. 단점: **인터페이스가 반드시 있어야** 한다.

### CGLIB (클래스 상속 기반)

인터페이스가 없어도 된다. CGLIB은 대상 클래스를 **상속한 서브클래스**를 바이트코드로 생성하고, 메서드를 오버라이드해 가로챈다. 그래서 프록시의 실제 타입은 `UserService$$EnhancerBySpringCGLIB$$...`가 된다.

- **Spring Boot는 기본이 CGLIB**이다(`proxyTargetClass=true`). 인터페이스가 있어도 CGLIB을 쓴다.
- 상속 기반이라 **`final` 클래스·`final` 메서드는 오버라이드 불가 → 프록시 불가**.
- 생성자를 우회해 인스턴스를 만들려고 Objenesis를 쓴다.

| | JDK Dynamic Proxy | CGLIB |
|---|---|---|
| 방식 | 인터페이스 구현 | 클래스 상속 |
| 전제 | 인터페이스 필수 | 없어도 됨 |
| 한계 | 인터페이스에 선언된 메서드만 | `final`/`private` 불가 |
| Boot 기본 | — | ✅ |

---

## 5. Spring AOP는 전부 프록시다

`@Transactional`, `@Async`, `@Cacheable`, `@PreAuthorize`, `@Retryable`, 커스텀 `@Aspect` — 이 모든 게 **"빈을 프록시로 바꿔치기하고, 그 프록시가 어드바이스를 실행"** 하는 동일한 메커니즘이다.

스프링은 컨테이너 초기화 때 `BeanPostProcessor`로 대상 빈을 감지해, 원본 대신 **프록시를 컨테이너에 등록**한다. 이후 `@Autowired`로 주입받는 건 전부 프록시다. 그래서 트랜잭션이 붙는다.

---

## 6. 실전 함정 — 여기서 어노테이션이 조용히 죽는다

### ① Self-invocation (자기 호출) — 압도적 1위 사고

같은 클래스 안에서 `this.otherMethod()`로 호출하면 **프록시를 거치지 않는다.** 프록시는 "바깥에서 들어오는 호출"만 가로채기 때문이다.

```java
@Service
public class OrderService {

    public void place() {
        // ❌ this.save() — 프록시를 안 거침 → @Transactional 무효!
        save();
    }

    @Transactional
    public void save() { /* 롤백 안 됨 */ }
}
```

`place()`는 프록시를 통해 들어왔지만, 그 안의 `save()`는 **원본 객체의 this**로 직접 호출된다. 프록시가 개입할 틈이 없다. `@Async`, `@Cacheable`도 똑같이 무력화된다. **"트랜잭션이 안 걸려요"의 90%가 이것.**

### ② private / final 메서드

- `@Transactional`을 **`private`** 메서드에 붙이면 무시된다. JDK 프록시는 인터페이스의 public만, CGLIB은 서브클래스가 `private`을 오버라이드 못 한다.
- `final` 메서드·클래스는 CGLIB이 오버라이드할 수 없어 어드바이스가 안 걸린다(설정에 따라 부팅 에러).

### ③ 프록시라서 생기는 것들

- `bean.getClass()`가 `...$$EnhancerBySpringCGLIB$$...`로 나온다.
- 필드에 직접 접근하면 프록시의 빈 필드를 보게 될 수 있다 → **반드시 getter/메서드로 접근**.
- 자기 자신을 주입하면 순환참조가 될 수 있어 `@Lazy`가 필요.

---

## 7. Self-invocation, 어떻게 푸나

**해결책 1 — 다른 빈으로 분리 (가장 깔끔)**

부가기능이 필요한 메서드를 별도 빈으로 빼면, 호출이 프록시를 정상적으로 통과한다.

```java
@Service
public class OrderService {
    private final OrderPersister persister;   // 다른 빈 = 프록시 경유
    public void place() { persister.save(); } // ✅ @Transactional 적용됨
}
```

**해결책 2 — 자기 자신을 주입**

```java
@Service
public class OrderService {
    @Autowired @Lazy private OrderService self; // 프록시가 주입됨
    public void place() { self.save(); }        // ✅ 프록시 경유
}
```

**해결책 3 — `AopContext.currentProxy()`** (`@EnableAspectJAutoProxy(exposeProxy = true)` 필요)

```java
((OrderService) AopContext.currentProxy()).save(); // ✅
```

실무 권장은 **1번(책임 분리)** 이다. 2·3번은 프록시 의존이 코드에 드러나 냄새가 난다.

---

## 마무리 — 두 기둥이 곧 스프링이다

- **Reflection** = 스프링이 당신의 클래스를 **발견·생성·주입**하는 능력. `private` 필드에 값이 꽂히는 것도, 컴포넌트 스캔도 전부 이것.
- **Proxy** = 원본을 감싸 **부가기능을 가로채 삽입**하는 능력. `@Transactional`·`@Async`·AOP가 전부 이것. 그리고 프록시의 심장은 다시 리플렉션(`method.invoke`)이다.

그래서 다음 한 문장이 스프링 심화의 핵심이다:

> **어노테이션은 "프록시가 바깥에서 들어온 호출을 가로챌 때만" 동작한다.** 내부 호출·private·final은 프록시를 우회하므로 마법이 조용히 사라진다.

`@Transactional`이 안 먹으면 로직을 의심하기 전에 먼저 물어보자. **"이 호출이 프록시를 거치는가?"** 답이 "아니오"라면, 버그는 스프링이 아니라 호출 경로에 있다.
