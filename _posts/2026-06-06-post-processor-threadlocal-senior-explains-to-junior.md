---
layout: post
title: "*Spring *후처리기* 와 *ThreadLocal* — *시니어가 *주니어에게 *조곤조곤 *설명하는 *진짜 *원리*"
date: 2026-06-06 02:00:00 +0900
categories: [spring, java, fundamentals]
tags: [spring, bean-post-processor, threadlocal, beanfactorypostprocessor, thread-safety, virtual-thread, fundamentals]
---

> *''*'@Transactional 은 *어떻게 *동작 *해요?""*, *''*ThreadLocal 이 *왜 *메모리 *누수 *위험이 *있다고 *하나요?""*. *주니어 *3 년 차쯤 *되면 *''*어렴풋이 *알지만 *설명은 *못 하겠는""* 주제들이 *있는데, *그 *대표가 ***Spring 의 *후처리기**와 **ThreadLocal**이다. *이 둘은 *얼핏 *상관 *없어 *보이지만, *Spring 의 *''*마법""* 이 *어떻게 *작동하는지의 *밑바닥 *두 *기둥이고, *그 *밑바닥을 *이해하면 *''*아 *그래서 *@Transactional 이 *클래스 *내부 *호출 시 *안 *먹혔구나""* 같은 *온갖 *수수께끼가 *한 번에 *풀린다.
>
> 이 글은 *''*5 년 *차 *시니어가 *주니어 *후배에게 *카페에서 *한 시간 *동안 *설명해주는""* 톤으로, *후처리기와 *ThreadLocal 을 *''*무엇인가 → 왜 *필요한가 → 어떻게 *동작 하나 → 실제 *Spring 에서 *어떻게 *쓰이나 → 흔한 *함정""* 의 *5 단계 로 *풀어본다.

대상은 *Spring 을 *6 개월 ~ 3 년 *써본 *주니어 / 미들 백엔드 *개발자, 그리고 *''*ThreadLocal 이 *위험 하다는데 *왜?""* 가 *진지하게 *궁금한 *모든 사람.

---

## 0. *시작 전에 *— *왜 *이 두 개를 *같이*

처음에는 *두 주제가 *별개라고 *생각할 수 *있는데, *실제로는 *Spring 의 *''*프록시 *마법""* 의 *양 축이다.

```
[애플리케이션 시작 시]                    [요청 처리 중]
─────────────────                       ────────────────
*Bean 후처리기*                          *ThreadLocal*
가 동작 → 우리 *Bean을                    이 동작 → 한 요청의 *상태가
*프록시로 *감싸기 결정                    *같은 *스레드에서 공유
↓                                       ↓
@Transactional 어노테이션 검사            @Transactional 의 *진짜 *트랜잭션
@Async 어노테이션 검사                     커넥션을 *ThreadLocal 에 *보관
@Cacheable 어노테이션 검사                 SecurityContext 도 *ThreadLocal
```

이 둘이 *맞물려서 *''*Spring 이 *알아서 *해준다""* 의 *기적이 *일어난다. *그래서 *둘 다 *제대로 *이해하면 *''*Spring 의 *내부""* 가 *한 *층 *벗겨진다.

---

## Part 1. *후처리기 (Post-Processor) — *Spring 의 *''*확장 *지점""*

### 1.1 *후처리기란 *무엇인가*

후처리기의 *한 줄 *정의:

> *''*Spring 컨테이너가 *Bean 을 *만드는 *과정에 *끼어들어, *Bean 이 *완성되기 *전이나 *후에 *우리가 *원하는 *수정을 *할 수 있게 *해주는 *''*훅 (hook)""*.""*

쉽게 *비유하면:

```
*공장*                              *Bean 라이프사이클*
─────────                          ───────────────────
원자재 *입고                       Bean 인스턴스 *생성
↓                                  ↓
*조립                              의존성 *주입 (DI)
↓                                  ↓
*검수                              초기화 (@PostConstruct)
↓                                  ↓
*포장 ← *''*공장 *직원이 *추가 작업""*    ← *후처리기*가 *여기 *끼어듦
↓                                  ↓
*출하                              Bean 사용 가능
```

후처리기는 *''*포장 *직원""* 같은 *역할 — *Bean 이 *조립은 *됐는데 *아직 *고객 (= 우리 *서비스 *코드) 에게 *주기 *전에, *추가 *작업을 *할 *수 있다.

### 1.2 *왜 *필요한가*

상상해보자. *내가 *직접 *서비스 클래스를 *짰는데, *Spring 이 *그 클래스를 *나도 *모르게 *''*프록시""* 라는 *다른 *클래스로 *몰래 *바꿔치기 한다.

```java
@Service
public class OrderService {
    @Transactional
    public void place(Order order) {
        orderRepository.save(order);
    }
}
```

내가 *짠 건 *위 *클래스 인데, *Spring 이 *''*이 *클래스에 *@Transactional 이 *있네? *그럼 *내가 *몰래 *트랜잭션 *시작/커밋 *코드를 *덧붙인 *서브클래스를 *대신 *넣어 *줄게""* 라고 *해주는 *주체가 *바로 *후처리기다.

```
실제 *주입되는 *것:
  ┌──────────────────────────────┐
  │  OrderService$$EnhancerByCGLIB ← 후처리기가 *만들어준 *프록시
  │  ├─ beginTransaction()
  │  ├─ super.place(order)         ← *진짜 코드 *호출
  │  └─ commitTransaction()
  └──────────────────────────────┘
```

이게 *''*Spring 의 *마법""* 의 *정체. *후처리기 없이는 *@Transactional, @Async, @Cacheable, @Validated 가 *전부 *동작 *안 한다.

### 1.3 *두 *종류의 *후처리기*

Spring 은 *후처리기를 *두 *층위로 *나눠 *둔다.

#### **(A) BeanFactoryPostProcessor — *''*설계도 *수정자""***

```java
public interface BeanFactoryPostProcessor {
    void postProcessBeanFactory(ConfigurableListableBeanFactory beanFactory);
}
```

이건 *Bean 이 *''*아직 *만들어지지 *않은""* 상태에서 *돈다. *''*설계도 (BeanDefinition) 자체를 *수정""* 한다. *''*이 *Bean 의 *클래스를 *바꿔라""*, *''*이 *프로퍼티 값을 *바꿔라""* 같은 *것을 *할 수 있다.

**대표적 *예: `PropertySourcesPlaceholderConfigurer`** — `${db.url}` 같은 *플레이스홀더를 *실제 *값으로 *치환.

#### **(B) BeanPostProcessor — *''*만든 *Bean 수정자""***

```java
public interface BeanPostProcessor {
    Object postProcessBeforeInitialization(Object bean, String beanName);
    Object postProcessAfterInitialization(Object bean, String beanName);
}
```

이건 *Bean 이 *''*이미 *만들어진""* 후에 *돈다. *''*이 *Bean 을 *프록시로 *감싸라""* 같은 *작업을 *한다.

**대표적 *예: `AnnotationAwareAspectJAutoProxyCreator`** — *@Transactional / @Async / @Aspect 가 *붙은 *Bean 을 *프록시로 *감쌈.

### 1.4 *실제 *Bean 라이프사이클 *순서*

```
1. BeanFactoryPostProcessor 가 *돔
   ├─ BeanDefinition 의 *변경 *(예: @Value 치환)
   └─ 이후 *''*BeanDefinition 은 *확정""*

2. 각 *Bean 마다:
   a. 인스턴스 *생성 (newInstance)
   b. 의존성 *주입 (@Autowired)
   c. ★ BeanPostProcessor.postProcessBeforeInitialization()
   d. 초기화 (@PostConstruct, InitializingBean.afterPropertiesSet())
   e. ★ BeanPostProcessor.postProcessAfterInitialization()  ← *프록시 *생성이 *여기*
   f. Bean *준비 *완료
   g. 다른 *Bean 에 *주입됨

3. 애플리케이션 *종료 시:
   a. @PreDestroy, DisposableBean.destroy()
```

**핵심 *포인트**: *프록시는 *e 단계 (`postProcessAfterInitialization`) 에서 *만들어진다. *즉 *진짜 *Bean 이 *완성된 *뒤에, *그것을 *감싸는 *프록시 객체가 *반환되고, *이후 *DI 는 *이 *프록시를 *받는다.

### 1.5 *직접 *만들어보기 — *''*Hello""* 후처리기*

```java
@Component
public class HelloBeanPostProcessor implements BeanPostProcessor {

    @Override
    public Object postProcessBeforeInitialization(Object bean, String beanName) {
        if (beanName.equals("orderService")) {
            System.out.println("[Before init] orderService 가 *초기화 *되기 *직전!");
        }
        return bean;
    }

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        if (beanName.equals("orderService")) {
            System.out.println("[After init] orderService 가 *초기화 *완료!");
            // 여기서 *원하면 *bean 을 *완전히 *다른 *것으로 *교체 가능
            // return new ProxiedOrderService(bean);
        }
        return bean;
    }
}
```

이 *코드만 *추가해도 *서비스 *실행 시 *콘솔에 *메시지가 *찍힌다. *내가 *''*Spring 의 *내부""* 에 *끼어든 *것이다.

### 1.6 *실제 *Spring 이 *후처리기로 *제공하는 *것들*

흔히 *모르는 *사실 — *우리가 *매일 *쓰는 *Spring 의 *기능 중 *많은 것이 *후처리기로 *구현되어 있다:

| 후처리기 | 역할 |
|---|---|
| `AutowiredAnnotationBeanPostProcessor` | @Autowired 처리 |
| `CommonAnnotationBeanPostProcessor` | @PostConstruct, @PreDestroy, @Resource 처리 |
| `AnnotationAwareAspectJAutoProxyCreator` | @Transactional, @Async 의 *프록시 생성 |
| `ConfigurationClassPostProcessor` | @Configuration 클래스 처리 |
| `PersistenceAnnotationBeanPostProcessor` | @PersistenceContext (JPA EntityManager) 주입 |
| `RequiredAnnotationBeanPostProcessor` | (구) @Required 어노테이션 |

> 즉 *''*Spring 의 *Spring 다움""* 의 *대부분이 *후처리기 위에서 *돈다.

### 1.7 *흔한 *함정 *3 가지*

#### *함정 1 — *프록시가 *''*같은 클래스 *내부 *호출""* 시 *동작 *X*

```java
@Service
public class OrderService {

    @Transactional
    public void place(Order order) {
        process(order);  // ← *같은 *클래스 *내부 *호출
    }

    @Transactional  // ← 이 *트랜잭션이 *''*무시""* 됨
    public void process(Order order) {
        repository.save(order);
    }
}
```

**왜?** *프록시는 *Spring 이 *주입한 *''*겉껍질""*. `place()` 가 *호출되면 *프록시가 *돌다가 *진짜 *`OrderService` 의 *`place()` 를 *호출. *그 *안에서 *`process()` 를 *부르면 *''*프록시를 *거치지 *않고 *진짜 *클래스의 *`process()` 를 *직접 *호출""*. *어노테이션 *처리 *X.

**해법**:
- 같은 *클래스 *내부 *호출 *피하기 (가장 *권장)
- *self-injection* (덜 *권장)
- *AopContext.currentProxy()* (가장 *비권장)

#### *함정 2 — *@Async / @Transactional 이 *private 메서드에 *안 *먹힘*

프록시는 *public 메서드만 *오버라이드 *가능. *private 은 *오버라이드 *X → 어노테이션 *처리 *불가.

#### *함정 3 — *@Configuration 클래스 *내부 *메서드 *호출의 *함정*

```java
@Configuration
public class AppConfig {
    @Bean
    public DataSource dataSource() { return new HikariDataSource(); }

    @Bean
    public JdbcTemplate jdbcTemplate() {
        return new JdbcTemplate(dataSource());  // ← *같은 *Bean *반환?
    }
}
```

`dataSource()` 호출 시 *진짜 *new 객체 *2 개가 *생길 *것 *같은데, *실제로는 *@Configuration 클래스도 *후처리기로 *프록시화되어 *같은 *싱글톤 *반환. *마법이 *맞고, *이 *마법도 *후처리기 덕분.

---

## Part 2. *ThreadLocal — *''*스레드 *별 *비밀 상자""*

### 2.1 *ThreadLocal 이란 *무엇인가*

ThreadLocal 의 *한 줄 *정의:

> *''*같은 *변수 이름인데, *스레드마다 *다른 *값을 *가질 수 있게 *해주는 *Java 의 *클래스.""*

비유:

```
*보통의 *static 변수*               *ThreadLocal*
────────────────                  ──────────────
모든 *스레드가 *공유                각 *스레드의 *''*개인 사물함""*
(== 회사 *공용 *프린터)              (== 개인 *책상 서랍)
```

### 2.2 *왜 *필요한가*

웹 서버는 *''*한 *요청 = 한 *스레드""* 가 *기본 모델 (전통적). *그런데 *그 요청을 *처리하는 *동안 *여러 *클래스가 *''*현재 *로그인 *사용자가 *누구지?""*, *''*지금 *어떤 *트랜잭션 *안이지?""* 같은 *정보를 *공유 *필요.

**선택지 1 — *메서드 *파라미터로 *전달**
```java
service1.doStuff(currentUser, transaction, ...);
service2.doStuff(currentUser, transaction, ...);
service3.doStuff(currentUser, transaction, ...);
```
*모든 메서드 *시그니처가 *지저분.

**선택지 2 — *static 변수**
```java
public class CurrentUserHolder {
    public static User current;  // ← 절대 X
}
```
*A 요청이 *값을 *설정하면 *B 요청도 *그 값을 *봄. *데이터 *유출.

**선택지 3 — *ThreadLocal**
```java
public class CurrentUserHolder {
    private static final ThreadLocal<User> CURRENT = new ThreadLocal<>();

    public static void set(User u)  { CURRENT.set(u); }
    public static User  get()       { return CURRENT.get(); }
    public static void clear()      { CURRENT.remove(); }
}
```
*같은 *변수인데 *스레드마다 *다른 *값. *완벽.

### 2.3 *기본 *사용법*

```java
ThreadLocal<String> threadName = new ThreadLocal<>();

// 스레드 *A 에서:
threadName.set("Worker-A");
System.out.println(threadName.get());  // "Worker-A"

// 스레드 *B 에서 (동시 *실행):
threadName.set("Worker-B");
System.out.println(threadName.get());  // "Worker-B"  ← 서로 *영향 X
```

### 2.4 *Spring 이 *ThreadLocal 을 *쓰는 *대표적 *곳*

#### **(A) Spring Security 의 *SecurityContextHolder**
```java
SecurityContextHolder.getContext().getAuthentication()
```
*어디서든 *''*지금 *로그인 *유저는?""* 를 *물을 수 있는 *이유 = *ThreadLocal 에 *담겨 *있어서.

#### **(B) @Transactional 의 *트랜잭션 *동기화**
```java
TransactionSynchronizationManager.getResource(dataSource)
```
*현재 *트랜잭션의 *DB 커넥션이 *ThreadLocal 에 *저장. *같은 *요청에서 *여러 *Repository 호출 시 *같은 *커넥션을 *공유.

#### **(C) Logback / SLF4J 의 *MDC**
```java
MDC.put("requestId", UUID.randomUUID().toString());
log.info("Hello");  // ← *requestId 가 *자동 *로그에 *포함
```
*요청 *별 *로그 *추적의 *핵심.

#### **(D) Spring 의 *LocaleContextHolder**
```java
LocaleContextHolder.getLocale()  // 현재 *요청의 *언어
```

---

### 2.5 *ThreadLocal 의 *진짜 *위험 — *''*메모리 *누수""*

이게 *주니어가 *제일 *많이 *놓치는 *부분이다. *''*ThreadLocal 위험""* 의 *진짜 *이유.

#### *왜 *위험한가*

웹 *서버의 *스레드 *풀 *동작:

```
요청 1: [Tomcat 스레드 #5] → handle() → set ThreadLocal 값 X → 응답 → *스레드 *반환됨
요청 2: [Tomcat 스레드 #5] → handle() → ThreadLocal.get() → *값 X 가 *나옴!
```

*스레드는 *재사용*. *내가 *set 했는데 *remove 안 *하면, *같은 *스레드를 *받은 *다음 *요청이 *내 *값을 *그대로 *본다. *데이터 *유출 *+ 메모리 *누수.

#### *해결책 — *반드시 *finally 에서 *remove*

```java
try {
    CurrentUserHolder.set(user);
    doStuff();
} finally {
    CurrentUserHolder.clear();  // ← *필수
}
```

Spring 의 *경우 *대부분 *''*Interceptor / Filter""* 에서 *자동으로 *clear 해주지만, *내가 *직접 *ThreadLocal 을 *쓴다면 *반드시 *finally 패턴.

#### *왜 *''*GC 가 *안 *해주나""**

ThreadLocal 의 *내부 *구조:

```
Thread
  └─ ThreadLocalMap (내부 *필드)
       └─ Entry[]
            ├─ Entry { key: ThreadLocal (weak ref), value: 우리 *값 (strong ref) }
            └─ ...
```

키는 *weak reference 라 *ThreadLocal 객체가 *GC 되면 *키는 *null 이 되지만, **값은 *strong reference**라 *Thread 가 *살아있는 *한 *값도 *살아있다. *Tomcat 의 *스레드 *풀은 *수십 분 *수시간 *살아있으므로 *값이 *그동안 *''*떠다님""*.

### 2.6 *Virtual Thread (Java 21) 시대의 *변화*

Project Loom 의 *Virtual Thread 가 *나오면서 *ThreadLocal 의 *위치가 *살짝 *바뀌었다.

- **Virtual Thread 는 *재사용되지 *않음** (작업 *끝나면 *증발). *그래서 *''*다음 *요청에 *값 *유출""* 위험은 *낮음.
- **하지만 *Virtual Thread 가 *수십만 *개 *동시에 *살면 *ThreadLocal 메모리 *수십만 *배 *증가 *위험.**

이를 위해 *Java 21 에서 *`ScopedValue` 라는 *대안이 *나옴 (Preview).

```java
private static final ScopedValue<User> CURRENT = ScopedValue.newInstance();

ScopedValue.where(CURRENT, user).run(() -> {
    System.out.println(CURRENT.get());  // *스코프 *안에서만 *유효
});
// 스코프 *벗어나면 *자동으로 *값 *증발 — GC X
```

> *''*ThreadLocal 은 *''*명시적 *remove""* 가 *필요한데, *ScopedValue 는 *''*자동 *정리""*. *Virtual Thread 시대의 *권장 패턴.""*

### 2.7 *흔한 *함정 *3 가지*

#### *함정 1 — *clear 안 함 → 메모리 *누수 + 데이터 *유출*

이미 *위에서 *설명. *finally 에서 *remove 가 *필수.

#### *함정 2 — *@Async / 자식 *스레드에 *값이 *전달 *안 됨*

```java
@Async
public void doAsync() {
    User u = CurrentUserHolder.get();  // ← null!
}
```

@Async 메서드는 *다른 *스레드에서 *실행. *원래 *스레드의 *ThreadLocal 값이 *전달 안 *됨.

**해법**:
- `InheritableThreadLocal` (단점: *스레드 *풀에서는 *재사용 시 *문제)
- Spring 의 *`DelegatingSecurityContextExecutor`
- 명시적 *파라미터 *전달

#### *함정 3 — *ReactiveStream 에서 *ThreadLocal 안 *통함*

WebFlux 의 *경우 *''*한 *요청 = 한 *스레드""* 가 *아님. *비동기 *체인에서 *스레드가 *왔다 갔다. *ThreadLocal 무효.

**해법**:
- Reactor 의 *`Context`
- 또는 *Java 21 의 *`ScopedValue` (Loom 의 *권장 패턴)

---

## Part 3. *둘이 *어떻게 *맞물리는가 — *@Transactional 의 *진짜 *동작*

이제 *둘을 *합쳐서 *@Transactional 의 *전체 *동작을 *추적 해보자.

```
1. 애플리케이션 시작
   ↓
2. *BeanPostProcessor* (AnnotationAwareAspectJAutoProxyCreator) 가 *동작
   ↓
3. OrderService 빈 *완성 후
   ''*이 클래스에 *@Transactional 있네?""* → 프록시 *생성
   ↓
4. 우리 *서비스 코드는 *프록시를 *주입받음
   ↓
5. *요청 *들어옴 (Tomcat *스레드 #5)
   ↓
6. controller.place() → proxy.place()
   ↓
7. 프록시가 *트랜잭션 *시작
   ├─ Connection 얻기 (DataSource)
   ├─ AutoCommit = false
   └─ *ThreadLocal* (TransactionSynchronizationManager) 에 *커넥션 *저장
   ↓
8. proxy → super.place() → repository.save()
   ↓
9. repository 가 *''*현재 *트랜잭션이 *있나?""* 물음
   └─ *ThreadLocal* 에서 *커넥션 *발견 → 같은 *커넥션 *재사용
   ↓
10. 정상 종료 시 *프록시가 *commit()
    └─ *ThreadLocal* 에서 *커넥션 *제거 + 반납
   ↓
11. 응답 *반환, 스레드 #5 *반환됨
```

**핵심**:
- 7 번 (트랜잭션 시작) 과 *9 번 (Repository 가 *커넥션 *찾기) 사이의 *연결을 *ThreadLocal 이 *맡고
- *프록시를 *만들어서 *''*트랜잭션 *시작/커밋""* 코드를 *우리 *코드 *주위에 *덧붙인 *것은 *후처리기가 *맡는다.

> *''*후처리기가 *''*판""* 을 *깔고, *ThreadLocal 이 *''*값을 *공유""* 한다. *둘이 *없으면 *@Transactional 이 *동작 *X.""*

---

## Part 4. *함께 *기억할 *5 가지*

### 1. *후처리기는 *''*Bean 라이프사이클의 *끼어드는 *지점""*
- BeanFactoryPostProcessor — *설계도 *수정 (BeanDefinition)
- BeanPostProcessor — *완성된 *Bean 수정 (대부분 *프록시 *생성)

### 2. *프록시는 *''*같은 클래스 *내부 *호출""* 시 *동작 *X
- @Transactional, @Async, @Cacheable 모두 *해당
- 외부 *진입점이 *프록시를 *거치는 *호출일 때만 *동작

### 3. *ThreadLocal 은 *''*스레드별 *비밀 상자""*
- 같은 *변수, 스레드마다 *다른 값
- SecurityContext, @Transactional, MDC 등이 *모두 *사용

### 4. *ThreadLocal 은 *반드시 *finally 에서 *remove
- 안 *그러면 *메모리 *누수 + 다음 *요청에 *값 *유출
- 키는 *weak ref, 값은 *strong ref → GC 가 *못 *건져감

### 5. *Virtual Thread 시대 — *ScopedValue 가 *후계자
- *Virtual Thread 가 *재사용 X 이므로 *''*다음 요청 유출""* 은 *덜 *위험
- 그러나 *수십만 *VT 의 *ThreadLocal 메모리는 *위험
- ScopedValue 가 *''*스코프 끝나면 *자동 *정리""* 의 *대안

---

## Part 5. *마지막 *— *''*그래서 *이걸 *언제 *써야 *해요?""**

후배가 *자주 *묻는 *현실적 *질문에 *답하자면:

### *후처리기를 *내가 *직접 *만들 일이 *있나?*

**거의 *없다**. *Spring 이 *제공하는 *후처리기 *(@Transactional 등) 가 *95% 의 *경우 *충분. *내가 *후처리기를 *만들 *상황은:
- *커스텀 *어노테이션 *처리 (예: @AuditLog)
- *특정 *Bean 의 *자동 *주입 *로직 (예: 모든 *Service 에 *공통 *Logger *주입)
- *프레임워크 *수준의 *확장

**하지만 *''*Spring 이 *후처리기로 *동작 한다""* 는 *사실은 *무조건 *알아야 함**. 디버깅 시 *''*왜 *내 *어노테이션이 *안 먹지?""* 의 *답이 *대부분 *여기.

### *ThreadLocal 을 *내가 *직접 *써야 *하나?*

**가능하면 *피해라**. *대부분 *Spring 이 *알아서 *해준다. *내가 *ThreadLocal 을 *직접 *써야 할 *상황은:
- *공통 *컨텍스트 *전파 (예: 요청 *ID, 사용자 *ID)
- *''*외부 *시스템 *호출 시 *항상 *덧붙일 *헤더""* 같은 *것

**ThreadLocal 을 *쓴다면 *반드시**:
- *Filter / Interceptor 에서 *try-finally 로 *clear 보장
- *Virtual Thread 환경이면 *ScopedValue 검토
- *비동기 / 반응형 코드에서는 *Reactor Context

---

## Part 6. *정리*

> *''*Spring 의 *''*마법""* 은 *두 *기둥 위에 *서 있다. 한 *기둥은 *후처리기 — *우리 *코드 *주위에 *프록시를 *덧붙여 *''*우리가 *몰래 *원하는 *동작""* 을 *추가 한다. 다른 한 *기둥은 *ThreadLocal — *같은 *요청의 *여러 *클래스가 *''*보이지 않는 *상태""* 를 *공유 한다. *둘이 *합쳐져서 *''*@Transactional 한 줄 *붙이면 *알아서 *동작""* 이라는 *놀라운 *추상화가 *완성 된다.*''*

이 *두 *기둥을 *제대로 *이해하면:
- *''*왜 *내 *@Transactional 이 *안 *먹지?""* — 같은 *클래스 *내부 *호출, *프록시 *함정
- *''*왜 *ThreadLocal 이 *위험 하다고?""* — 스레드 풀, finally 미사용
- *''*Virtual Thread 가 *뭐가 *다른가?""* — ScopedValue 의 *등장
- *''*ReactiveStream 에서 *왜 *MDC 가 *안 *통하지?""* — 비동기 *체인의 *스레드 *전환

이 *모든 *질문이 *한 *줄기로 *연결된다는 *것이 *''*시니어가 *주니어를 *제일 *부러워하지 *않는 *순간""* 의 *진짜 *내용이다. *처음엔 *어렵지만 *한 *번 *제대로 *이해하면 *Spring 의 *내부가 *훨씬 *덜 *무서워진다.

후배가 *카페에서 *''*그래서 *@Transactional 이 *어떻게 *동작 해요?""* 라고 *물으면, *오늘 *이 *글의 *내용을 *그대로 *전해 *주면 된다. *후처리기가 *''*판""* 을 *깔고, *ThreadLocal 이 *''*값""* 을 *공유 한다 — *이 한 줄을 *기둥으로 *세우고 *위에 *예제와 *함정을 *얹어 *주면, *그 후배도 *언젠가 *자기 *후배에게 *같은 *이야기를 *해줄 *것이다.

---

## 더 *읽으면 *좋은 *자료*

- *Joshua Bloch*, **Effective Java** (3 판) — Item 1 ~ 90 의 *기초가 *이 *글의 *전제
- *Brian Goetz*, **Java Concurrency in Practice** — *ThreadLocal *4.3 절
- *Spring Framework Reference* — *''*Bean Lifecycle""*, *''*Aspects with AspectJ""*
- *Project Loom JEP 444* (Virtual Threads), *JEP 446* (Scoped Values)
- *Spring 공식 *블로그* — *''*Virtual Threads in Spring Boot 3.2""*
- *우아한기술블로그* — *''*Spring 의 *프록시와 *@Transactional""* 시리즈
- 본 블로그의 [Spring AOP — *무대 *감독의 *시선](/2026/05/26/spring-aop-interview-senior-engineer-perspective/)
- 본 블로그의 [TDD 와 *Mockito 의 *역사](/2026/05/29/tdd-mockito-value-spring-history/)
