---
layout: post
title: "필터와 인터셉터의 차이는 정상 경로에서 안 보인다 — 예외·비동기·에러 디스패치에서 갈린다"
date: 2026-09-15 10:53:49 +0900
categories: [java, spring]
tags: [spring, filter, interceptor, servlet, dispatcher-servlet, async, exception-handling, spring-security, spring-boot]
---

"필터는 서블릿 표준이고 인터셉터는 스프링 것" — 여기까지는 다 안다. [지난 글]({% post_url 2026-05-29-spring-filter-vs-interceptor-network-perspective %})에서 패킷이 컨트롤러까지 가는 계층을 12단계로 그렸으니, 위치 이야기는 거기서 끝났다.

이번 글은 그 다음이다. **정상 경로에서는 둘 다 잘 돈다. 차이가 실제로 드러나는 건 예외가 나거나, 비동기로 빠지거나, 에러 페이지로 디스패치될 때다.** 로그가 비고, 인증이 우회되고, `afterCompletion` 이 안 불리는 자리들 — 전부 여기에 몰려 있다.

출처 원칙: 동작 규칙과 기본값은 Spring 레퍼런스·javadoc·Spring Boot 문서·Jakarta EE 문서로 확인한 것만 적는다. 문서로 확인되지 않은 것은 추론이라고 라벨을 붙인다.

---

## 0. 한 줄 요약부터

**필터는 `DispatcherServlet` 바깥에서 컨테이너가 부르고, 인터셉터는 `DispatcherServlet` 이 핸들러를 찾은 뒤에 부른다.** 아래 모든 차이가 이 한 문장에서 나온다.

```
클라이언트
  └ 서블릿 컨테이너
      └ FilterChain            ← 필터 (컨테이너의 계약)
          └ DispatcherServlet
              ├ HandlerMapping (어떤 핸들러인지 결정)
              ├ preHandle       ← 인터셉터 (스프링의 계약)
              ├ 컨트롤러 메서드
              ├ postHandle
              └ afterCompletion
```

서블릿 스펙상 하나의 요청을 처리하는 서블릿은 최대 하나지만 필터는 여럿일 수 있고, 필터는 다운스트림 필터·서블릿의 호출을 막거나 요청·응답 객체를 교체할 수 있다.[^sec-arch]

---

## 1. 예외가 서로 다른 곳으로 간다

스프링 레퍼런스는 범위를 정확히 못 박는다 — **"요청 매핑 중이거나 요청 핸들러에서 던져진" 예외**를 `DispatcherServlet` 이 `HandlerExceptionResolver` 체인에 위임한다.[^mvc-exc] `@ControllerAdvice` / `@ExceptionHandler` 는 그 체인의 한 구현(`ExceptionHandlerExceptionResolver`)이다.

즉 **필터에서 던진 예외는 이 체인에 애초에 들어가지 않는다.** `DispatcherServlet` 에 도달하기 전에 터졌거나, 이미 빠져나온 뒤에 터졌기 때문이다. 대신 컨테이너까지 올라가고, 컨테이너는 설정된 에러 페이지로 **ERROR 디스패치**를 만든다.[^mvc-exc] 스프링 부트라면 그 자리가 `/error`(`BasicErrorController`)다.

실무적으로 이게 왜 아픈가:

- 팀이 `@RestControllerAdvice` 로 응답 포맷(`{code, message, traceId}`)을 통일해 놨는데, **인증 필터가 던진 예외만 형식이 다르다.** 프론트는 그 하나 때문에 파싱 분기를 하나 더 갖는다.
- 그래서 필터 단계의 실패는 예외를 던지는 대신 **필터 안에서 직접 응답을 쓰는** 편이 낫다. Spring Security 가 `AuthenticationEntryPoint` / `AccessDeniedHandler` 같은 별도 진입점을 두는 구조가 정확히 그 이유다.
- 또는 `HandlerExceptionResolver` 빈을 필터에 주입해 예외를 스프링 쪽 처리로 넘길 수도 있다. 다만 이건 "필터가 스프링을 알아야 한다" 는 결합이 생긴다 — 공짜가 아니다. *(이 선택의 트레이드오프는 문서의 권고가 아니라 내 판단이다.)*

---

## 2. ERROR 디스패치에서 필터는 기본적으로 **안 돈다**

여기가 로그 실종의 단골 원인이다.

서블릿 필터는 디스패처 타입(`REQUEST`, `FORWARD`, `INCLUDE`, `ERROR`, `ASYNC`)별로 적용 여부가 정해지고, **아무것도 지정하지 않으면 기본은 `REQUEST` 뿐이다.**[^jakarta-dispatch]

스프링의 `OncePerRequestFilter` 는 여기에 자기 기본값을 더한다:

- `shouldNotFilterErrorDispatch()` 기본값 **`true`** — 에러 디스패치에서는 이 필터를 호출하지 않는다[^once]
- `shouldNotFilterAsyncDispatch()` 기본값 **`true`** — 이후 비동기 디스패치에서도 호출하지 않는다[^once]

그래서 이런 일이 벌어진다:

```
정상 응답  →  TraceIdFilter 가 MDC 채움  →  로그에 traceId 있음
500 응답   →  ERROR 디스패치로 /error 재진입
           →  필터는 기본적으로 안 돌음
           →  정작 traceId 가 제일 필요한 로그에 traceId 가 없음
```

`OncePerRequestFilter` javadoc 은 ERROR 디스패치가 REQUEST 디스패치가 끝난 *뒤에* 일어나며 **필터 체인이 처음부터 다시 시작된다**고 적는다.[^once] 그리고 컨테이너마다 디스패처 타입 기본값을 다르게 잡는 경우가 있어서, 이 플래그는 "필터의 설계 의도를 강제하는" 장치라고 설명한다.[^once] 컨테이너를 바꾸면 동작이 달라질 수 있다는 뜻이기도 하다 — [JBoss·톰캣 병행 운영 글]({% post_url 2026-09-15-jboss-tomcat-side-by-side-pitfalls %})에서 다룬 것과 같은 종류의 함정이다.

**대응.** 트레이스 ID·MDC 처럼 에러 응답에서도 반드시 살아 있어야 하는 필터는 `shouldNotFilterErrorDispatch()` 를 `false` 로 오버라이드하거나, 등록 시 디스패처 타입에 `ERROR` 를 포함시킨다. 반대로 요청 래핑처럼 **한 번만** 해야 하는 필터는 기본값 그대로 두는 게 맞다.

인터셉터 쪽은? `/error` 도 결국 `DispatcherServlet` 을 다시 타므로 **인터셉터는 에러 디스패치에서도 돈다.** 경로 패턴이 `/**` 라면 `/error` 까지 포함된다는 뜻이라, 인터셉터에 카운터를 달아뒀다면 에러 응답 하나가 두 번 세어질 수 있다. *(이건 위 인용들에서 따라 나오는 추론이다. 실제로는 인터셉터에서 `request.getDispatcherType()` 을 찍어 확인하는 게 맞다.)*

---

## 3. 비동기에서 생명주기가 갈라진다

스프링 문서는 비동기 처리의 핵심 효과를 이렇게 적는다 — `request.startAsync()` 를 호출하면 **"서블릿(그리고 모든 필터)이 빠져나갈 수 있지만 응답은 열린 채로 남는다."**[^mvc-async]

이 한 문장이 필터 쪽 전제를 깨뜨린다:

```java
// 동기라면 맞지만, 비동기 컨트롤러에서는 틀린 코드
long start = System.nanoTime();
chain.doFilter(request, response);
log.info("소요 {}ms", (System.nanoTime() - start) / 1_000_000);   // ← 실제 처리 전에 찍힘
```

`chain.doFilter()` 가 리턴하는 시점은 **응답이 끝난 시점이 아니라 스레드가 풀려난 시점**이다. `finally` 에서 `MDC.clear()` 를 하는 필터라면, 정작 비동기 작업이 도는 동안엔 MDC 가 이미 비어 있다.

인터셉터 쪽은 스프링이 이 상황을 위해 별도 콜백을 만들어 뒀다. `AsyncHandlerInterceptor` javadoc:[^async-ic]

- 핸들러가 비동기를 시작하면 `DispatcherServlet` 은 **`postHandle` 과 `afterCompletion` 을 부르지 않고** 빠져나간다. 결과(ModelAndView)가 아직 준비되지 않았기 때문이다.
- 대신 `afterConcurrentHandlingStarted` 가 호출된다. **전형적인 용도가 스레드 로컬 정리**라고 문서가 직접 적는다.
- 비동기 처리가 끝나면 컨테이너로 다시 디스패치되고, 그때 `preHandle` → `postHandle` → `afterCompletion` 이 (다시) 호출된다.
- 최초 요청인지 비동기 완료 후 디스패치인지는 `DispatcherType` 이 `REQUEST` 인지 `ASYNC` 인지로 구분한다.

그리고 가장 위험한 한 줄 — **비동기 요청이 타임아웃되거나 네트워크 오류로 끝나면 컨테이너가 디스패치를 하지 않으므로 `postHandle` 과 `afterCompletion` 이 호출되지 않는다.**[^async-ic] 여기에 리소스 해제를 걸어뒀다면 그 경로에서만 조용히 샌다. 그래서 문서는 타임아웃 같은 이벤트까지 다루려면 `CallableProcessingInterceptor` / `DeferredResultProcessingInterceptor` 를 등록하라고 안내한다.[^mvc-async2]

**정리하면 — 비동기를 쓰는 순간 "요청 하나 = 콜백 한 세트" 가 깨진다.** 필터는 한 요청에 대해 여러 스레드에서 여러 번 불릴 수 있고,[^once] 인터셉터는 콜백 조합 자체가 달라진다.

---

## 4. `postHandle` 은 REST API 에서 사실상 죽은 훅이다

스프링 레퍼런스가 직접 경고한다 — **`@ResponseBody` 와 `ResponseEntity` 컨트롤러 메서드는 응답이 `HandlerAdapter` 안에서 이미 쓰이고 커밋되며, 그건 `postHandle` 이 호출되기 전이다. 그래서 헤더 추가 같은 응답 변경을 하기엔 너무 늦다.**[^mvc-ic] 문서는 대신 `ResponseBodyAdvice` 를 쓰라고 안내한다.

즉 요즘 대부분인 REST 컨트롤러에서 `postHandle` 로 할 수 있는 일은 "읽기와 기록" 뿐이다. 응답을 **고치는** 일은 세 자리 중 하나로 간다:

| 하고 싶은 일 | 맞는 자리 |
| --- | --- |
| 응답 바디 형태를 바꾸기 (공통 래핑 등) | `ResponseBodyAdvice` |
| 응답 헤더 추가 | 필터(커밋 전) 또는 컨트롤러 |
| 응답 바디를 읽어서 로깅·압축 | 필터 + `HttpServletResponseWrapper` |

마지막 줄이 필터의 고유 능력이다. 필터는 응답 객체 자체를 래퍼로 **교체**해서 다운스트림에 넘길 수 있다.[^sec-arch] 인터셉터에는 이에 해당하는 수단이 없다 — 인터셉터가 받는 건 이미 정해진 `HttpServletResponse` 다.

---

## 5. 인터셉터만 아는 것 — 어떤 핸들러가 걸렸는가

반대 방향의 고유 능력도 있다. 인터셉터 콜백은 `handler` 파라미터를 받고, 이건 대개 `HandlerMethod` 다 — javadoc 이 "the handler (or HandlerMethod) ... for type and/or instance examination" 이라고 명시한다.[^async-ic]

그래서 **"이 컨트롤러 메서드에 붙은 어노테이션을 보고 분기" 하는 일은 인터셉터만 할 수 있다.** 필터는 그 시점에 어떤 컨트롤러가 선택될지 모른다 — 핸들러 매핑이 아직 안 일어났기 때문이다.

```java
public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) {
    if (handler instanceof HandlerMethod hm && hm.hasMethodAnnotation(RateLimited.class)) {
        // 어노테이션 기반 처리 — 필터에서는 불가능
    }
    return true;
}
```

경로 패턴도 인터셉터 쪽이 더 편하다. `addPathPatterns` / `excludePathPatterns` 로 등록 시점에 선언한다.[^mvc-config]

---

## 6. 그런데 인증·인가는 인터셉터로 하면 안 된다

이 글에서 가장 반직관적인 항목이고, 추측이 아니라 **스프링 공식 문서의 명시적 권고**다:

> Interceptors are not ideally suited as a security layer due to the potential for a mismatch with annotated controller path matching. Generally, we recommend using Spring Security, or alternatively a similar approach integrated with the Servlet filter chain, and applied as early as possible.[^mvc-ic][^mvc-config]

이유가 중요하다 — **인터셉터의 경로 매칭과 컨트롤러 어노테이션의 경로 매칭이 어긋날 수 있기 때문이다.** 보안에서 이 어긋남은 곧 우회다. 인터셉터가 `/admin/**` 을 막는다고 믿었는데 컨트롤러 매핑이 그 패턴 밖의 형태로도 같은 메서드에 도달하면, 그 경로는 검사 없이 통과한다.

그래서 Spring Security 는 인터셉터가 아니라 **서블릿 필터**로 구현돼 있다. `FilterChainProxy` 하나가 `SecurityFilterChain` 을 통해 여러 시큐리티 필터에 위임하고, 이건 `DelegatingFilterProxy` 로 감싸져 컨테이너에 등록된다.[^sec-arch] 필터 체인에서 처리하면 **`DispatcherServlet` 에 도달하기 전에** 판정이 끝나므로 "어떤 컨트롤러로 매핑됐는가" 와 무관해진다.

**인터셉터에 어울리는 일은 따로 있다** — 로케일 변경, 감사 로그, 핸들러 어노테이션 기반 처리처럼 **우회되어도 보안 사고가 아닌 것들.** 스프링이 기본 제공하는 인터셉터가 `LocaleChangeInterceptor` 인 것도 이 성격을 보여준다.[^mvc-config]

---

## 7. 등록과 순서 — 부트에서 실제로 걸려 넘어지는 것들

필터 순서는 요청 처리 결과를 바꾼다. 필터는 다운스트림에만 영향을 주므로 **호출 순서가 대단히 중요하다**고 스프링 시큐리티 문서도 못 박는다.[^sec-arch] 스프링 부트 문서에서 실제로 사람을 잡는 항목들:[^boot-servlet]

- **`@Order` 를 `@Bean` 메서드에 붙이면 필터 순서에 반영되지 않는다.** `Filter` **클래스**에 `@Order` 를 붙이거나 `Ordered` 를 구현해야 하고, 클래스를 못 고치면 `FilterRegistrationBean` 을 만들어 `setOrder(int)` 를 써야 한다. — 가장 흔한 착각이다.
- **요청 본문을 읽는 필터를 `Ordered.HIGHEST_PRECEDENCE` 에 두지 말 것.** 애플리케이션의 문자 인코딩 설정보다 먼저 돌아 인코딩 설정을 무력화할 수 있다.
- **요청을 래핑하는 필터는 `OrderedFilter.REQUEST_WRAPPER_FILTER_MAX_ORDER` 이하**로 둘 것.
- 순서가 궁금하면 추측하지 말고 `logging.level.web=debug` 를 켠다 — 등록된 필터의 순서와 URL 패턴이 기동 시 로그에 찍힌다.
- 필터 빈은 **애플리케이션 생애주기에서 아주 이르게 초기화된다.** 다른 빈에 의존하는 필터라면 `DelegatingFilterProxyRegistrationBean` 을 쓰는 게 안전하다. (데이터소스·JPA 에 의존하는 필터를 만들었다가 기동이 꼬이는 사고가 여기서 나온다.)

인터셉터 쪽은 훨씬 단순하다. `WebMvcConfigurer#addInterceptors` 에 등록한 순서가 실행 순서이고, 경로 패턴을 같은 자리에서 선언한다.[^mvc-config] 다만 문서가 짚는 함정이 하나 있다 — **XML 설정은 인터셉터를 `MappedInterceptor` 빈으로 선언해 모든 `HandlerMapping` 이 감지하지만, 자바 설정은 자기가 관리하는 `HandlerMapping` 에만 넘긴다.**[^mvc-config] 다른 프레임워크의 핸들러 매핑까지 걸리길 원한다면 `MappedInterceptor` 빈으로 선언해야 한다.

---

## 8. 그래서 무엇을 언제 쓰나

| 요구 | 자리 | 이유 |
| --- | --- | --- |
| 인증·인가 | **필터** (Spring Security) | 경로 매칭 불일치로 우회될 수 있어 인터셉터는 공식 비권장[^mvc-ic] |
| 요청·응답 래핑, 바디 로깅, 압축 | **필터** | 요청·응답 객체 자체를 교체할 수 있는 건 필터뿐[^sec-arch] |
| 문자 인코딩, CORS 사전 처리 | **필터** | `DispatcherServlet` 진입 전에 끝나야 함 |
| 트레이스 ID / MDC | **필터** (단 `ERROR` 디스패치 포함 여부를 결정할 것) | 에러 응답 로그에서 사라지는 게 이 결정에 달림[^once] |
| 핸들러 어노테이션 기반 처리 | **인터셉터** | `HandlerMethod` 를 아는 건 인터셉터뿐[^async-ic] |
| 로케일·테마 변경, 감사 로그 | **인터셉터** | 우회돼도 보안 사고가 아님[^mvc-config] |
| 응답 바디 형태 변경 | **둘 다 아님** — `ResponseBodyAdvice` | `postHandle` 은 이미 늦음[^mvc-ic] |

---

## 마무리

세 가지만 남긴다.

**① 필터는 컨테이너의 계약, 인터셉터는 스프링의 계약이다.** 그래서 컨테이너를 바꾸면(톰캣↔JBoss, 디스패처 타입 기본값) 필터 쪽 동작이 흔들릴 수 있고, 스프링 버전을 올리면 인터셉터 쪽 계약이 움직인다. 흔들리는 축이 서로 다르다.

**② 정상 경로만 테스트하면 이 글의 함정을 하나도 못 만난다.** 예외 응답·비동기·타임아웃을 테스트에 넣지 않으면 MDC 실종도, `afterCompletion` 미호출도 운영에서 처음 본다. 그리고 그때는 로그가 없어서 원인 추적이 어렵다 — **로그를 채우는 코드가 바로 그 경로에서 안 도는 것**이기 때문이다.

**③ "둘 다 되는데 뭘 쓰죠?" 라면 기준은 딱 하나 — 우회되면 사고인가.** 사고라면 필터(그리고 Spring Security). 아니면 인터셉터가 더 편하고 정보도 많다.

---

## References

[^mvc-ic]: Spring Framework 공식 레퍼런스 — [Web MVC: Interception](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-servlet/handlermapping-interceptor.html) (`preHandle`/`postHandle`/`afterCompletion`, `@ResponseBody`·`ResponseEntity` 에서 `postHandle` 이 늦다는 경고, 보안 계층 비권장)
[^mvc-config]: Spring Framework 공식 레퍼런스 — [MVC Config: Interceptors](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-config/interceptors.html) (등록·경로 패턴, `MappedInterceptor` 차이, 보안 계층 비권장)
[^mvc-exc]: Spring Framework 공식 레퍼런스 — [Web MVC: Exceptions](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-servlet/exceptionhandlers.html) (`HandlerExceptionResolver` 의 적용 범위, Container Error Page / ERROR 디스패치)
[^mvc-async]: Spring Framework 공식 레퍼런스 — [Web MVC: Asynchronous Requests](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-async.html) ("the Servlet (as well as any filters) can exit, but the response remains open")
[^mvc-async2]: Spring Framework 공식 레퍼런스 — [Web MVC: Asynchronous Requests](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-async.html) (`CallableProcessingInterceptor` / `DeferredResultProcessingInterceptor` 등록 안내)
[^async-ic]: Spring Framework javadoc — [`AsyncHandlerInterceptor`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/servlet/AsyncHandlerInterceptor.html) (`afterConcurrentHandlingStarted`, `REQUEST`/`ASYNC` 구분, 타임아웃·네트워크 오류 시 디스패치 없음)
[^once]: Spring Framework javadoc — [`OncePerRequestFilter`](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/filter/OncePerRequestFilter.html) (`shouldNotFilterErrorDispatch()`·`shouldNotFilterAsyncDispatch()` 기본 `true`, ERROR 디스패치에서 필터 체인이 처음부터 다시 시작)
[^sec-arch]: Spring Security 공식 레퍼런스 — [Servlet Architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html) (`FilterChain`, 요청·응답 교체, 순서의 중요성, `DelegatingFilterProxy`, `FilterChainProxy`, `SecurityFilterChain`)
[^boot-servlet]: Spring Boot 공식 레퍼런스 — [Servlet Web Applications](https://docs.spring.io/spring-boot/reference/web/servlet.html) (`FilterRegistrationBean`, `@Order` 를 `@Bean` 메서드에 붙이면 안 되는 이유, `REQUEST_WRAPPER_FILTER_MAX_ORDER`, `logging.level.web=debug`, `DelegatingFilterProxyRegistrationBean`)
[^jakarta-dispatch]: Jakarta EE 공식 튜토리얼 — [Jakarta Servlet](https://jakarta.ee/learn/jakartaee-tutorial/current/web/servlets/servlets.html) (디스패처 타입 `REQUEST`/`ASYNC`/`FORWARD`/`INCLUDE`/`ERROR`, "If no types are specified, the default option is REQUEST")
