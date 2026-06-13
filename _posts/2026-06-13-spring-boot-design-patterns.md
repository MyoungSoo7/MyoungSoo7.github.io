---
layout: post
title: "*Spring Boot 안의 *디자인 패턴* — *프레임 워크 가 *패턴 *교과서* 인 *이유*"
date: 2026-06-13 22:30:00 +0900
categories: [backend, spring, design-patterns]
tags: [spring, spring-boot, design-patterns, gof, proxy, strategy, template, observer]
---

> *디자인 패턴* 을 *책으로 *외우는 *시대 는 *끝났다*.
> *Spring Boot 의 *코드 한 줄 한 줄 마다 — *GoF 패턴* 이 *살아 있다*.
> *@Transactional 의 *내부 가 Proxy*, *PasswordEncoder 의 *내부 가 Strategy*, *JdbcTemplate 가 *Template Method*.
> *Spring 을 *깊이 쓰면* — *패턴 이 *자연 익혀 진다*. 이 글은 그 *지도*.

---

## TL;DR

| 패턴 | Spring 의 *그것* |
|------|------------------|
| **Singleton** | Bean (default scope) |
| **Factory** | BeanFactory / ApplicationContext / @Bean |
| **Proxy** | @Transactional / @Async / AOP |
| **Strategy** | PasswordEncoder / AuthenticationProvider |
| **Observer** | ApplicationEventPublisher / @EventListener |
| **Template Method** | JdbcTemplate / RestTemplate / TransactionTemplate |
| **Decorator** | Filter chain / HandlerInterceptor |
| **Adapter** | HandlerAdapter / MessageConverter |
| **Chain of Responsibility** | Filter / Security Filter Chain |
| **Builder** | RestClient.Builder / WebClient.Builder |

핵심 한 줄 :

> *Spring 의 *모든 *주요 기능* 은 *하나 이상 의 패턴 의 *적용*. *Spring 사용 = *패턴 사용*.

---

## 1. *왜 *Spring 이 *패턴 *교과서* 인가*

### *발상 의 기원*

Spring 은 *2003 년 Rod Johnson 의 *"Expert One-on-One J2EE Design and Development"* 책 에서 시작. *EJB 의 *과한 복잡도* 에 *반발* 하며 *경량 컨테이너 + 의존성 주입* 의 *철학* 제안.

이 *철학* 의 *내부* :

- *IoC* — *제어 의 *역전* (Hollywood Principle)
- *DI* — *의존성 *주입*
- *AOP* — *횡 단 관 심사*
- *POJO* — *순수 *Java 객체*

→ *모두 *GoF 패턴 의 *적용* 또는 *변주*.

### *현 대* 의 *영향*

- *Java 백엔드 *대부분 *Spring + Spring Boot*
- *Kotlin / Reactive 의 *진화 도 *Spring 안에서*
- *MSA / Cloud 의 *Spring Cloud*

→ *Spring 의 *내부 를 *읽으면* — *Java 백엔드 의 *모든 기술 의 *근본* 이 *보인다*.

---

## 2. **Singleton** — *Bean 의 *기본*

### *Spring 의 *Bean Scope*

```java
@Component
@Scope("singleton")  // default
public class UserService { ... }
```

*default 가 *Singleton*. *전 Spring 컨테이너 에 *하나만* 존재.

### *왜 *Spring 의 *Singleton 이 *안전 한가*

GoF *Singleton* 의 *위험* — *Thread-safe 구현 의 *복잡*. *Spring 은 *컨테이너 시작 시 *한 번 만 생성 + ConcurrentHashMap 에 저장*. 호출 자는 *공유 인스턴스 사용*.

```
ApplicationContext :
  Map<String, Object> singletons
```

→ ***GoF 의 *Singleton 함정 의 *완전 회피***.

### *주의 — *상태 ↔ Singleton*

```java
@Service
public class CounterService {
    private int count = 0;  // ❌ 공유 상태
    
    public void increment() { count++; }  // *race condition*
}
```

*Singleton Bean 안 의 *변경 가능 상태* 는 *위험*. *동시성 = *Bean 의 *기본 가정 위배*.

해결 — *@Scope("prototype")*, *AtomicInteger*, *Redis 등 *외부 상태*.

---

## 3. **Factory** — *BeanFactory / @Bean / ApplicationContext*

### *Bean 생성의 *위임*

```java
@Configuration
public class AppConfig {
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate(...);
    }
}
```

`@Bean` 메서드 — *Factory Method 패턴*. 컨테이너 가 *호출 자가 *클래스 알 필요 없이 *객체 얻기*.

### *BeanFactory 의 *3 단계*

```
1. Bean 정의 등록 (BeanDefinition)
2. Bean 생성 위임 (FactoryBean / @Bean / @Component)
3. 의존성 주입 + 초기화
```

`ApplicationContext` 가 *BeanFactory 의 *확장*. *Factory + Singleton + Registry 의 *조합*.

### *FactoryBean*

```java
@Component
public class MyServiceFactory implements FactoryBean<MyService> {
    public MyService getObject() {
        return new MyService(...);
    }
    public Class<?> getObjectType() { return MyService.class; }
}
```

*복잡 생성 로직* 의 *명시적 *Factory 인터페이스*. *Spring 내부 의 *많은 Bean (예: SqlSessionFactoryBean)* 이 *이 형태*.

---

## 4. **Proxy** — *@Transactional 의 *비밀*

### *Spring 의 *Proxy 의 *모습*

```java
@Service
public class OrderService {
    @Transactional
    public void process() { ... }
}
```

*실 행 시 — *OrderService 가 *Proxy 객체* 로 wrap*. 메서드 호출 가 *Proxy 통과 → 트랜잭션 시작 → 실제 메서드 → 종료 시 commit/rollback*.

### *Proxy 의 *2 구현*

1. **JDK Dynamic Proxy** — *인터페이스 기반*. *대상 객체 가 *인터페이스 구현* 시.
2. **CGLIB** — *클래스 기반*. *바이트 코드 *조작* 으로 *서브 클래스 생성*.

Spring Boot 2.x+ 부터 *CGLIB 기본*. *인터페이스 없는 클래스 도 *Proxy 가능*.

### *Self-Invocation 의 *함정*

```java
@Service
public class OrderService {
    public void wrapper() {
        process();  // ❌ Proxy 안 거침 — @Transactional 무시
    }
    
    @Transactional
    public void process() { ... }
}
```

*같은 객체 안 의 *호출* 은 *Proxy 안 거침*. *별도 Bean 분리* 또는 *AopContext.currentProxy()* 우회.

→ *Proxy 패턴 의 *대표적 *실 무 함정*. *몰라서 *6개월 만에 *데이터 부정합 발견* 흔함.

---

## 5. **Strategy** — *PasswordEncoder / AuthenticationProvider*

### *Strategy 의 *전형*

```java
public interface PasswordEncoder {
    String encode(CharSequence rawPassword);
    boolean matches(CharSequence rawPassword, String encodedPassword);
}

// 구현 들
class BCryptPasswordEncoder implements PasswordEncoder { ... }
class Pbkdf2PasswordEncoder implements PasswordEncoder { ... }
class Argon2PasswordEncoder implements PasswordEncoder { ... }
```

*PasswordEncoder 인터페이스 + 구현 *교체 가능* = *Strategy 의 *교과서*.

### *주입 의 *유연성*

```java
@Bean
PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder();  // 또는 Argon2 등
}

@Autowired PasswordEncoder encoder;  // *구체 클래스 *모름*
```

→ *알고리즘 *교체* 가 *Bean 정의 *한 줄 수정*. *Strategy 의 *진짜 가치*.

### *DelegatingPasswordEncoder — 다중 Strategy*

```java
PasswordEncoder encoder = PasswordEncoderFactories
    .createDelegatingPasswordEncoder();
// → {bcrypt} / {pbkdf2} / {scrypt} 등 *접두사* 로 *자동 선택*
```

*Strategy 의 *동적 *디스패치* 도 *Spring 내장*.

---

## 6. **Observer** — *ApplicationEventPublisher*

### *전형*

```java
// 1. 이벤트 정의
public class OrderCompletedEvent {
    private final Long orderId;
    public OrderCompletedEvent(Long id) { orderId = id; }
}

// 2. 발행
@Service
public class OrderService {
    @Autowired ApplicationEventPublisher publisher;
    
    public void complete(Long id) {
        publisher.publishEvent(new OrderCompletedEvent(id));
    }
}

// 3. 구독
@Component
public class EmailNotifier {
    @EventListener
    public void onOrderCompleted(OrderCompletedEvent event) {
        // 메일 발송
    }
}
```

### *Spring 의 *추가 기능*

- *@Async + @EventListener* — *비동기 처리*
- *@TransactionalEventListener* — *트랜잭션 *완료 후* 발행
- *Conditional* — `condition = "#event.orderId > 100"`

→ *GoF Observer 의 *기본 + 트랜잭션 통합* = *진짜 실 무 *원형*.

### *주의*

- *순서 보장 *없음* — *순서 중요 면 *@Order* 또는 *Workflow Engine*
- *예외 처리* — *Listener 의 *예외 가 *발행 자에 *영향 줄지* 명시
- *@TransactionalEventListener* 의 *주의* — *commit 후 발행*

---

## 7. **Template Method** — *JdbcTemplate*

### *전형*

```java
@Autowired JdbcTemplate jdbcTemplate;

List<User> users = jdbcTemplate.query(
    "SELECT * FROM users WHERE active = ?",
    new Object[]{ true },
    (rs, rowNum) -> new User(rs.getLong("id"), rs.getString("name"))
);
```

### *Template 의 *큰 흐름*

```
JdbcTemplate.query :
  1. 커넥션 획득 (DataSource)
  2. PreparedStatement 생성
  3. 파라미터 바인딩
  4. 실 행
  5. ResultSet 처리 ← *RowMapper 콜백*
  6. 자원 정리 (try-with-resources)
  7. 예외 변환 (SQLException → DataAccessException)
```

이 *큰 흐름* 이 *고정* + *사용자 가 *RowMapper 만 *제공* = *Template Method 의 *교과서*.

### *유사 *Template Method*

- *RestTemplate* — HTTP 호출 흐름 + ResponseExtractor 콜백
- *TransactionTemplate* — 트랜잭션 흐름 + TransactionCallback
- *RedisTemplate* — Redis 명령 흐름 + RedisCallback
- *KafkaTemplate* — Kafka publish 흐름 + ProducerCallback

→ *"~Template"* 이름 의 *Spring 클래스* 는 *대부분 *Template Method*.

---

## 8. **Decorator** — *Filter Chain / HandlerInterceptor*

### *Filter Chain 의 *형태*

```
Request → Filter1 → Filter2 → Filter3 → Servlet
                                ↓
Response ← Filter1 ← Filter2 ← Filter3 ← Servlet
```

각 Filter 가 *요청 / 응답 의 *추가 처리* — *Decorator 의 *체인 형식*.

```java
@Component
public class LoggingFilter implements Filter {
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
        log.info("incoming: " + req);
        chain.doFilter(req, res);  // 다음 으로
        log.info("done");
    }
}
```

### *Spring Security 의 *Filter Chain*

```
SecurityContextPersistenceFilter
  → CsrfFilter
  → BasicAuthenticationFilter
  → UsernamePasswordAuthenticationFilter
  → AuthorizationFilter
  → ...
  → Controller
```

*보안 의 *모든 책임* 이 *Filter 단위 분리*. *Decorator + Chain of Responsibility 의 *조합*.

### *HandlerInterceptor — Spring MVC 의 *Decorator*

```java
@Component
public class TimingInterceptor implements HandlerInterceptor {
    public boolean preHandle(...) { /* 시작 */ }
    public void postHandle(...) { /* 끝 */ }
}
```

*MVC 컨트롤러 호출 *앞 뒤* 의 *처리* — *AOP 대체 가능*.

---

## 9. **Adapter** — *HandlerAdapter / MessageConverter*

### *HandlerAdapter*

Spring MVC 의 *전형 흐름* :

```
DispatcherServlet
  → 어떤 Handler 인지 *결정 (HandlerMapping)*
  → 해당 HandlerAdapter 로 *위임* (Adapter)
  → 처리 + ModelAndView 반환
```

`@Controller` (전통), `@RestController`, `HttpRequestHandler`, `Servlet` 등 — *서로 다른 *인터페이스* 를 *공통 호출 형태* 로 *변환*.

```java
// 내부
HandlerAdapter adapter = getHandlerAdapter(handler);
ModelAndView mv = adapter.handle(request, response, handler);
```

→ *서로 다른 Handler 형태* 를 *DispatcherServlet 이 동일 하게 *호출 가능* — *Adapter 의 *교과서*.

### *MessageConverter*

```
HTTP body ↔ Java 객체 의 *변환*
- MappingJackson2HttpMessageConverter : JSON
- StringHttpMessageConverter : String
- ByteArrayHttpMessageConverter : byte[]
```

각 컨버터 가 *MediaType* 별 *Adapter*. *Content-Type 매칭 후 *위임*.

---

## 10. **Chain of Responsibility** — *Filter / Interceptor*

### *Filter Chain 의 *책임 *연쇄*

각 Filter 가 *처리 가능 여부 결정* + *다음 으로 위임*.

```java
public class AuthFilter implements Filter {
    public void doFilter(...) {
        if (publicEndpoint(req)) {
            chain.doFilter(...);  // *위임*
            return;
        }
        if (!authenticated(req)) {
            res.sendError(401);
            return;  // *체인 중단*
        }
        chain.doFilter(...);  // *위임*
    }
}
```

*각 단계 가 *자기 책임* 만 다루고 *다음 으로 위임*. *Chain of Responsibility 의 *전형*.

### *Spring Security 의 *완성 형태*

```
HttpSecurity
  .authorizeRequests()
      .antMatchers("/public/**").permitAll()
      .antMatchers("/admin/**").hasRole("ADMIN")
      .anyRequest().authenticated()
  .and()
  .addFilterBefore(myFilter, UsernamePasswordAuthenticationFilter.class)
```

*Filter 들 의 *체인 *세밀 *설정*. *책임 + 순서 의 *명시 적 제어*.

---

## 11. **Builder** — *WebClient / RestClient*

### *Reactive WebClient*

```java
WebClient client = WebClient.builder()
    .baseUrl("https://api.example.com")
    .defaultHeader(HttpHeaders.CONTENT_TYPE, "application/json")
    .filter(loggingFilter())
    .build();
```

*복잡 객체 의 *단계 적 구성* — *Builder 의 *교과서*.

### *Spring 6 의 *RestClient (2024+)*

```java
RestClient client = RestClient.builder()
    .baseUrl("...")
    .requestInterceptor(...)
    .build();
```

*Builder 패턴 의 *현대 적 *접근 — fluent + immutable*.

---

## 12. **현실 의 *복합 사용*

### *@Transactional 의 *내부* 분석*

한 *@Transactional* 어노테이션 안 에 *몇 개 패턴 이 *조합* 되어 있는가:

```
1. Singleton — Bean (TransactionInterceptor)
2. Proxy — TransactionInterceptor 가 Bean 을 wrap
3. Strategy — TransactionManager (JPA / JDBC / JTA / 등)
4. Template — TransactionTemplate (programmatic)
5. Chain — Multiple Interceptor 들 의 *연쇄*
6. Observer — TransactionalEventListener 와 통합
```

→ *간단 한 @Transactional 한 줄 의 *내부 가 *6 가지 패턴 의 *합주*. *프레임 워크 의 *깊이*.

### *Spring MVC 의 *Request 처리*

```
1. Filter (Decorator + Chain)
2. DispatcherServlet (Front Controller)
3. HandlerMapping (Strategy)
4. HandlerAdapter (Adapter)
5. HandlerInterceptor (Decorator)
6. @Controller (Bean = Singleton)
7. @Transactional (Proxy)
8. MessageConverter (Adapter)
9. ApplicationEventPublisher (Observer)
```

*한 HTTP 요청 의 처리 = *9 패턴 의 *조합*.

---

## 13. *왜 *Spring 을 *읽으면 *패턴 이 *보이는가*

### *직접 체감*

- *@Transactional 의 *Self-Invocation 함정* — *Proxy 의 *본질 이해*
- *PasswordEncoder 교체* — *Strategy 의 *유연 함 체감*
- *@EventListener 의 *비동기* — *Observer 의 *현대 적 변주*
- *JdbcTemplate 의 *복잡 SQL 처리* — *Template Method 의 *위력*

이 모든 *순간* 이 *책 없 이 *실 무 에서 *패턴 익히기*.

### *추천 *순서*

1. *Spring 의 *기본 *기능 *사용*
2. *내부 가 *왜 *그렇게 *동작 하는지* 의 *호기심*
3. *해당 패턴 의 *GoF 책 *섹션* 만 *읽음*
4. *책 + 실 무 의 *상호 강화*

→ *책 으로 *처음 부터 *외우는 게 *아니라 *실 무 의 *순서* 가 *답*.

---

## 14. *흔한 *오해*

### 14.1. *"Spring 이 너무 *복잡 해서 *패턴 가린다*"*

→ *반대*. *Spring 의 *철학* 이 *패턴 의 *명시 적 구현*. *읽으면 *패턴 이 *드러 난다*.

### 14.2. *"@Transactional 만 알면 *Proxy 다 안다*"*

→ *부족*. *AOP / pointcut / advice / weaving* 까지 *이해 해야 *진짜 Proxy*.

### 14.3. *"Spring 의 *패턴 = GoF 와 *동일*"*

→ *기본 은 동일*. *Spring 의 *확장 + 통합* 이 *현대 적 변주*. *원전 + Spring 둘 다 보는 게 *정답*.

---

## 15. *내 *경험* — *Spring 을 *깊이 *읽어 본 *결과*

### *3 년차* — *@Transactional 의 *내부 *모름*

*Self-Invocation 함정* 으로 *6 개월 만 에 *데이터 부정합 발견*. *AOP + Proxy 의 *내부 분석* 후 *해결*.

### *5 년차* — *Spring Security 의 *Filter Chain 분석*

*100+ 페이지 분석 자료 작성*. *Decorator + Chain + Strategy + Adapter 의 *조합 이 *눈 에 보이기 시작*.

### *7 년차* — *Spring 의 *모든 핵심 기능 의 *패턴 적 *해석 가능*

*신규 서비스 설계 시 — *Spring 의 *어느 패턴 응용* 인지 *직 관*. *코드 작성 *속도 ↑* + *유지 보수 *부담 ↓*.

→ *Spring 의 *깊이 = *패턴 의 *깊이*. *둘이 *서로 보강*.

---

## 16. 마치며

> *Spring 의 *모든 *주요 기능* 의 *내부* — *GoF 패턴 의 *적용 또는 *변주*. *Spring 을 *깊이 쓰면* — *패턴 이 *자연 익혀 진다*.

3 줄 요약 :

1. ***@Transactional / @Bean / @EventListener 가 *각각 *어떤 패턴 의 적용 인지 *몸 으로 *알기***.
2. ***Filter / Interceptor / HandlerAdapter 의 *역할 분담 *을 *패턴 으로 *읽기***.
3. ***Spring 코드 안 의 *패턴 의 *조합 의 *직 관* 이 *시니어 의 *능력***.

7년차 회고 :

> *"학부 시절 *패턴 책 *외우려 했다*. *7년 후 *Spring 의 *코드 만 *읽 어도 *패턴 이 *드러 남* 을 *몸 으로 *느낀다*."*

다음 글 — *Spring AOP 의 *깊이* — Pointcut / Advice / Weaving / Aspect 의 *내부 동작*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 / Spring 운영 회고*. *Spring 5/6 기준*. *세부 구현 은 *버전* 마다 *변할 수 있음*. *원리 + 패턴 매핑* 은 *오래 가는 지식*.
