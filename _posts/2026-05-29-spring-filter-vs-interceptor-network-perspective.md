---
layout: post
title: "Spring Filter vs Interceptor — TCP 패킷이 Controller 에 도달하는 12 단계와 그 사이에 누가 끼어드는가"
date: 2026-05-29 01:45:00 +0900
categories: [java, spring, networking]
tags: [spring, filter, interceptor, servlet, tomcat, http, tcp, dispatcher-servlet, handler-interceptor, aop, mdc, network]
---

"Filter 랑 Interceptor 가 뭐가 달라요?" 라는 질문에 *"Filter 는 서블릿 표준이고 Interceptor 는 Spring 거예요"* 라고만 답하면 **반쪽**. 진짜 차이는 *네트워크 패킷이 Controller 메서드에 도달하기까지의 12 단계 중 어디에서 동작하느냐* 에 있다.

이 글은 *TCP 패킷이 도착한 순간부터 응답이 다시 TCP 로 나가기까지* 의 모든 layer 를 그리고, Filter 와 Interceptor 가 *어느 layer 에 끼어드는지* 를 정확히 보여준다.

---

## TL;DR — 12 단계 한눈에

```
[Client] ── HTTPS request ──→
   1. TCP 3-way handshake          (커널)
   2. TLS handshake                 (커널 → JSSE)
   3. HTTP 파싱                     (Tomcat Connector — NIO/APR)
   4. Thread pool 에서 worker 할당  (Tomcat Executor)
   5. ⭐ Servlet Filter chain       ← Filter 동작 위치
   6. DispatcherServlet.service()
   7. HandlerMapping resolution
   8. ⭐ HandlerInterceptor.preHandle()  ← Interceptor 동작 위치
   9. @ControllerAdvice → ArgumentResolver
  10. Controller method 실행
  11. ⭐ HandlerInterceptor.postHandle()
  12. View / Message Converter → Response body
       ⭐ HandlerInterceptor.afterCompletion()
       ⭐ Servlet Filter chain (reverse order)
       Response 직렬화 → Connector → TCP flush
[Client] ←─── HTTPS response ─
```

| 위치 | 진입 시점 | Spring Bean? | DispatcherServlet 우회 가능? |
|---|---|---|---|
| **Filter** | DispatcherServlet *밖* (5번) | 기본 X (등록 시 가능) | ✅ 모든 요청 (정적 파일 포함) |
| **Interceptor** | DispatcherServlet *안* (8번) | ✅ (당연) | ❌ Controller 매칭된 요청만 |

---

## 0. 왜 이 차이가 중요한가

같은 일을 둘 다 할 수 있어 보이는데 (예: 로깅, 인증), *어느 layer 에서 동작하느냐* 가 다음을 결정한다:

- 정적 파일 (`/css/app.css`) 도 가로채나?
- Spring `@Autowired` 빈을 쓸 수 있나?
- `@PathVariable` 값을 알 수 있나?
- Exception 이 던져졌을 때 받을 수 있나?
- Response body 가 만들어진 *후* 에 무언가 할 수 있나?

이 질문들의 답이 *Filter / Interceptor 선택의 결정 기준*.

---

## 1. 패킷이 도착한 순간 — TCP / TLS layer

```
[Network Card] ──→ [Kernel: TCP/IP stack] ──→ [Tomcat NIO Connector]
```

- **TCP 3-way handshake**: 커널 레벨. 자바 코드는 *전혀 모름*
- **TLS handshake**: JSSE (Java Secure Socket Extension) 가 처리. 인증서 검증, key exchange, cipher 협상
- **HTTP/1.1 vs HTTP/2 vs HTTP/3**: Connector 가 protocol 결정. HTTP/2 면 *멀티플렉싱*, HTTP/3 면 *QUIC* (UDP 기반)

이 단계는 *Filter 도 Interceptor 도 못 닿음*. *커널과 Tomcat Connector 의 세계*.

### Tomcat Connector 의 종류

| Connector | 특징 |
|---|---|
| **NIO** (Non-blocking IO, 기본값) | Selector 패턴, 적은 thread 로 많은 connection |
| **NIO2** | AIO (Async IO) 기반. Linux 에선 성능 차이 미미 |
| **APR** (Apache Portable Runtime) | C 라이브러리 호출. native, 가장 빠름 |
| HTTP/2 | NIO + ALPN extension |
| HTTP/3 | 별도 implementation (Nginx 같은 reverse proxy 흔함) |

`application.yml`:
```yaml
server:
  tomcat:
    connection-timeout: 20s
    max-connections: 8192
    threads:
      max: 200       # worker thread pool
      min-spare: 10
```

`threads.max` 가 *동시 처리 가능 요청 수*. 이 수를 넘으면 *큐에 대기* → latency 폭증.

---

## 2. Servlet Filter chain — Spring 의 *밖*

HTTP 파싱이 끝나 *ServletRequest / ServletResponse* 객체가 만들어지면, Tomcat 은 *web.xml 또는 Spring Boot 의 FilterRegistrationBean 에 등록된 Filter chain* 을 호출한다.

```java
public interface Filter {
    default void init(FilterConfig filterConfig) throws ServletException {}
    void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException;
    default void destroy() {}
}
```

### Filter chain 실행 모델

```
Filter1.doFilter() {
    // 요청 가공 (pre)
    chain.doFilter(request, response);  ← 다음 filter / Servlet 으로 위임
    // 응답 가공 (post)
}
```

각 Filter 가 *체인의 다음을 직접 호출*. 이게 Filter 의 *전형적 컨트롤 패턴* — *Decorator 패턴의 살아있는 예시*.

### Spring Boot 에서 Filter 등록

```java
@Configuration
public class FilterConfig {

    @Bean
    public FilterRegistrationBean<TraceIdFilter> traceIdFilter() {
        var registration = new FilterRegistrationBean<>(new TraceIdFilter());
        registration.addUrlPatterns("/api/*");
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE);  // 가장 먼저 실행
        return registration;
    }
}

class TraceIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String traceId = req.getHeader("X-Trace-Id");
        if (traceId == null) traceId = UUID.randomUUID().toString();
        MDC.put("traceId", traceId);
        res.setHeader("X-Trace-Id", traceId);
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.clear();
        }
    }
}
```

### Filter 의 *진짜 강점*

Filter 는 *DispatcherServlet 밖* 에서 동작하므로:

1. **정적 파일도 가로챔** — `/static/app.css` 같은 정적 리소스에도 필터 적용
2. **DispatcherServlet 우회 가능** — 인증 실패 시 *Controller 까지 안 가고* 401 응답
3. **응답 전체를 가공 가능** — Gzip 압축, response body 수정 (단 `ContentCachingResponseWrapper` 같은 trick 필요)
4. **Spring 컨텍스트 부재여도 동작** — Spring 시작 전에 등록되는 시스템 필터도 있음 (e.g. CharacterEncodingFilter)

### Spring Security 가 Filter 인 이유

```
SecurityFilterChain:
  SecurityContextPersistenceFilter
    → LogoutFilter
      → UsernamePasswordAuthenticationFilter
        → BasicAuthenticationFilter
          → RequestCacheAwareFilter
            → SecurityContextHolderAwareRequestFilter
              → AnonymousAuthenticationFilter
                → SessionManagementFilter
                  → ExceptionTranslationFilter
                    → FilterSecurityInterceptor
                      → [DispatcherServlet]
```

Spring Security 의 *모든 인증/인가* 가 Filter 로 구현. 이유:
- *DispatcherServlet 들어가기 전에* 차단 (CPU 절약)
- *정적 리소스도 보호*
- *세션 / Authentication 정보를 Spring MVC 의 모든 곳에서 사용 가능* 하도록 ThreadLocal 세팅

---

## 3. DispatcherServlet — Spring MVC 의 입구

Filter chain 끝에 *DispatcherServlet.service()* 가 호출됨. 여기부터 *Spring 의 세계*.

```java
// DispatcherServlet.doDispatch() 핵심 흐름 (단순화)
protected void doDispatch(HttpServletRequest request, HttpServletResponse response) {

    // 1. URL → Handler 매핑
    HandlerExecutionChain mappedHandler = getHandler(request);
    if (mappedHandler == null) return notFound();

    // 2. ⭐ Interceptor.preHandle()
    if (!mappedHandler.applyPreHandle(request, response)) return;

    // 3. ArgumentResolver → Controller 호출
    HandlerAdapter ha = getHandlerAdapter(mappedHandler.getHandler());
    ModelAndView mv = ha.handle(request, response, mappedHandler.getHandler());

    // 4. ⭐ Interceptor.postHandle()
    mappedHandler.applyPostHandle(request, response, mv);

    // 5. View 렌더링 (Message Converter 가 JSON 변환)
    render(mv, request, response);

    // 6. ⭐ Interceptor.afterCompletion()
    mappedHandler.triggerAfterCompletion(request, response, null);
}
```

Interceptor 의 3 메서드가 *각각 어디서 호출되는지* 가 코드에 그대로 드러난다.

---

## 4. HandlerInterceptor — Spring 의 *안*

```java
public interface HandlerInterceptor {

    // Controller 호출 *전*. false 반환 시 Controller 안 호출됨.
    default boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) {
        return true;
    }

    // Controller 호출 *후*, View 렌더링 *전*. ModelAndView 수정 가능.
    default void postHandle(HttpServletRequest req, HttpServletResponse res,
                            Object handler, ModelAndView mv) {}

    // View 렌더링 *후* (또는 예외 발생 시). 항상 호출됨 — 자원 정리 용도.
    default void afterCompletion(HttpServletRequest req, HttpServletResponse res,
                                  Object handler, Exception ex) {}
}
```

### 등록

```java
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Autowired
    private AuditInterceptor auditInterceptor;  // Spring Bean!

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(auditInterceptor)
            .addPathPatterns("/api/**")
            .excludePathPatterns("/api/health", "/api/metrics");
    }
}

@Component
public class AuditInterceptor implements HandlerInterceptor {

    @Autowired
    private UserRepository userRepo;  // ✅ DI 자유롭게

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) {
        if (handler instanceof HandlerMethod hm) {
            // ✅ 어떤 Controller 메서드인지 알 수 있음
            String method = hm.getMethod().getName();
            // @RequireAdmin 같은 커스텀 어노테이션 검사
            if (hm.hasMethodAnnotation(RequireAdmin.class)) {
                if (!isAdmin(req)) {
                    res.setStatus(403);
                    return false;
                }
            }
        }
        return true;
    }
}
```

### Interceptor 의 *진짜 강점*

1. **Spring Bean** — `@Autowired` 로 어떤 빈이든 주입 가능
2. **Handler 정보** — *어떤 Controller 메서드* 가 매칭됐는지 (`HandlerMethod`) 알 수 있음. 메서드의 어노테이션 검사 가능
3. **`@PathVariable` / `@RequestMapping` 정보 접근** — URL 패턴 매칭 결과 사용 가능
4. **`@ControllerAdvice` 와 조합** — 예외 처리 + 인터셉터 모두 Spring 컨텍스트에서

---

## 5. Filter vs Interceptor — 핵심 비교 매트릭스

| 항목 | Filter | Interceptor |
|---|---|---|
| 표준 | Java Servlet API | Spring MVC |
| 패키지 | `jakarta.servlet.Filter` | `org.springframework.web.servlet.HandlerInterceptor` |
| 위치 | DispatcherServlet *밖* | DispatcherServlet *안* |
| 정적 파일 적용 | ✅ | ❌ |
| DispatcherServlet 우회 | ✅ (Controller 안 거치고 응답 가능) | ❌ (이미 dispatch 됨) |
| Spring Bean 으로 등록 | △ (가능하지만 추가 등록 필요) | ✅ 기본 |
| `@Autowired` DI | △ (`@WebFilter` + `@Component` 또는 `DelegatingFilterProxy`) | ✅ |
| Handler 정보 (HandlerMethod) | ❌ | ✅ |
| Request/Response 가공 | ✅ (Wrapper 패턴) | △ (어렵)) |
| 응답 body 수정 | ✅ (ContentCachingResponseWrapper) | ❌ (이미 늦음) |
| Exception 받기 | △ (try/catch 직접) | ✅ (afterCompletion) |
| 실행 순서 제어 | `@Order`, FilterRegistration | `addInterceptor().order(0)` |
| 적용 패턴 | URL pattern | URL pattern + path variable |

---

## 6. 언제 무엇을 쓰는가 — 결정 트리

```
┌─ 정적 파일 (CSS/JS) 도 가로채야 하나?
│   YES → Filter
│   NO  ↓
│
├─ Controller 진입 전에 차단해야 하나? (인증/CORS/CSRF)
│   YES → Filter (Spring Security 처럼)
│   NO  ↓
│
├─ 어떤 Controller 메서드인지 알아야 하나?
│   YES → Interceptor (@RequireAdmin 같은 커스텀 어노테이션 검사)
│   NO  ↓
│
├─ Response body 를 가공해야 하나? (gzip, 암호화)
│   YES → Filter (ContentCachingResponseWrapper)
│   NO  ↓
│
├─ 그냥 로깅/MDC/audit?
│   둘 다 OK. *DI 가 필요하면* Interceptor, *모든 요청 (정적 포함)* 이면 Filter
│
└─ 비즈니스 로직?
    AOP (@Around)  ← 메서드 레벨, HTTP 무관
```

---

## 7. AOP 와는 어떻게 다른가

| 영역 | Filter | Interceptor | AOP (@Around) |
|---|---|---|---|
| Layer | Servlet | Spring MVC | 메서드 호출 |
| 작동 단위 | HTTP request | HTTP request | 메서드 한 번 호출 |
| 대상 | 모든 요청 | Controller 매핑 요청 | 모든 Spring Bean 의 메서드 |
| 사용 사례 | CORS, 인증, gzip | audit, MDC | 트랜잭션, 캐시, 보안 (메서드 레벨) |

AOP 는 *HTTP 와 무관* — `service.process()` 같은 *서비스 레이어 메서드* 가 호출될 때 끼어듦. *Filter / Interceptor 가 HTTP 라면 AOP 는 메서드*.

```
요청
  ↓
Filter         (HTTP 레벨, Tomcat 안)
  ↓
Interceptor    (HTTP 레벨, Spring MVC 안)
  ↓
Controller
  ↓ controllerService.process()
AOP            (메서드 레벨, Spring AOP 의 proxy)
  ↓
실제 메서드
```

세 layer 가 *서로 다른 추상화 수준* 에서 횡단 관심사를 처리.

---

## 8. 실전 — 4가지 시나리오와 정답

### 시나리오 1: CORS 처리

```java
@Configuration
public class CorsConfig {
    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of("https://app.example.com"));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
        config.setAllowedHeaders(List.of("*"));
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
```

**정답: Filter**. 이유:
- Preflight (OPTIONS) 요청은 *Controller 와 무관*. DispatcherServlet 안에 안 들어가도 응답해야 함
- 정적 파일 요청에도 CORS 헤더 필요
- Spring 의 `CorsFilter` 자체가 Filter

### 시나리오 2: Trace ID (MDC)

**정답: Filter**. 이유:
- *모든 요청* (정적 포함) 에 traceId 부여
- 로그 첫 줄부터 traceId 가 있어야 (Interceptor 보다 *먼저* 실행)
- Spring 컨텍스트 의존성 없음 (OncePerRequestFilter 로 충분)

### 시나리오 3: API 호출 audit (사용자별 통계)

```java
@Component
public class AuditInterceptor implements HandlerInterceptor {
    @Autowired private AuditService auditService;

    @Override
    public void afterCompletion(HttpServletRequest req, HttpServletResponse res,
                                Object handler, Exception ex) {
        if (handler instanceof HandlerMethod hm) {
            auditService.record(new AuditEvent(
                getUserId(req),
                hm.getMethod().getName(),
                res.getStatus(),
                ex != null
            ));
        }
    }
}
```

**정답: Interceptor**. 이유:
- *어떤 Controller 메서드* 호출됐는지 알아야 함 (`HandlerMethod`)
- `AuditService` 빈 DI 필요
- 정적 파일은 audit 안 함
- 예외 발생 여부도 알아야 (`afterCompletion(... Exception ex)`)

### 시나리오 4: Response body Gzip 압축

```java
@Configuration
public class GzipConfig {
    @Bean
    public FilterRegistrationBean<GzipFilter> gzipFilter() {
        var reg = new FilterRegistrationBean<>(new GzipFilter());
        reg.addUrlPatterns("/*");
        return reg;
    }
}
```

**정답: Filter**. 이유:
- Response body 전체를 *buffer 후 압축* 해야 함
- Interceptor 의 `postHandle` 은 *이미 body 가 쓰이는 중*
- `ContentCachingResponseWrapper` 같은 *Filter 패턴* 으로 가능

(실제론 Spring Boot 의 `server.compression.enabled=true` 가 *Tomcat 레벨* 에서 처리하는 게 더 효율적. Tomcat Connector 가 직접 처리)

---

## 9. 네트워크 관점에서 보는 *각 layer 의 시간 비용*

각 단계가 *latency 의 어느 부분을 점유* 하는가:

```
TCP handshake          ~10ms (지역) / ~100ms (대륙간)
TLS handshake          ~30ms (TLS 1.3) / ~60ms (TLS 1.2)
HTTP 파싱              ~1ms
Filter chain (Spring Security 등 10개)  ~2-5ms
DispatcherServlet      ~1ms
Interceptor (3개)       ~1-2ms
Controller + Service    ~30-200ms ← 비즈니스 로직
Message Converter (JSON) ~3-10ms
Response flush         ~1ms

총 latency: ~80-400ms (대부분이 Controller + 외부 호출)
```

*Filter / Interceptor 는 latency 의 *작은 부분***. 그러나 *모든 요청에 적용* 되므로 *수만 RPS 환경에선 누적 비용 큼*.

성능 팁:
- Filter chain 길이 *최소화* (특히 Spring Security 의 *기본 13개 Filter*)
- Interceptor 에 *동기 IO 절대 금지* (Redis, DB 호출 등)
- Heavy 검증은 *async + 결과 캐시*

---

## 10. 내 환경의 Filter / Interceptor 매핑

### settlement (Spring Boot 3.x)

| 위치 | 용도 | 구현 |
|---|---|---|
| Filter | Trace ID + MDC | `TraceIdFilter extends OncePerRequestFilter` |
| Filter | Spring Security | 기본 13개 + JWT 검증 1개 |
| Filter | CORS | `CorsFilter` |
| Filter | Request/Response 로깅 | `CommonsRequestLoggingFilter` |
| Interceptor | Idempotency-Key 검사 | `IdempotencyInterceptor` (HandlerMethod 의 `@IdempotentOperation` 검사) |
| Interceptor | Rate limit | `RateLimitInterceptor` (Redis 기반) |
| Interceptor | Audit | `AuditInterceptor` (afterCompletion 에서 비동기 publish) |

### lemuel-xr

| 위치 | 용도 |
|---|---|
| Filter | Trace ID, CORS, Spring Security |
| Interceptor | Mental health safety pre-check, User opt-out 검사 |
| AOP | `@Cacheable`, `@Transactional`, embedding 호출 retry |

---

## 결론 — Layer 를 알면 *올바른 도구* 가 보인다

Filter 와 Interceptor 의 차이는 *기능* 이 아니다. *네트워크 패킷이 도착한 후의 12 단계 중 어디에서 동작하느냐* 다.

선택 기준 한 줄:
- **DispatcherServlet 들어가기 전** 에 뭔가 해야 → **Filter**
- **어떤 Controller 메서드** 인지 알아야 → **Interceptor**
- **메서드 호출 자체** 를 가로채야 → **AOP**

좋은 Spring 개발자는 *언제 어느 layer 에 끼어들지* 를 *네트워크 흐름* 으로 직관적으로 안다. 이걸 모르면 *Interceptor 에서 CORS 처리* 같은 *layer 오용* 이 발생해 production 디버깅 지옥행.

---

## 참고

- *Jakarta Servlet Specification 6.0*
- [Spring MVC — DispatcherServlet](https://docs.spring.io/spring-framework/docs/current/reference/html/web.html#mvc-servlet)
- [Spring Security FilterChain](https://docs.spring.io/spring-security/reference/servlet/architecture.html)
- [Tomcat Connector 비교](https://tomcat.apache.org/tomcat-10.1-doc/config/http.html)
- 관련 글: [Harness Engineering ② Test Harness]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %}), [DDD 와 MSA 의 상관관계]({% post_url 2026-05-29-ddd-msa-bounded-context-aggregate-event-storming %})
