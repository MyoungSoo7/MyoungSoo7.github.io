---
layout: post
title: "Spring Security 7 — 필터 체인 구조부터 Boot 4 에서 바뀐 설정까지"
date: 2026-10-21 23:08:22 +0900
categories: [spring, security]
tags: [spring-security, spring-boot-4, filter-chain, csrf, mfa, migration]
---

Spring Boot 4.0 은 Spring Security 7.0 을 함께 가져온다([Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)). 메이저 버전이라 6.x 에서 "deprecated" 경고만 띄우던 API 가 실제로 사라졌다. 이 글은 두 부분이다. 먼저 **요청 하나가 Spring Security 를 어떻게 통과하는지**(필터 체인 구조)를 정리하고, 그 위에서 **7.0 에서 무엇이 바뀌었고 어떻게 옮겨 가는지**를 공식 문서 기준으로 정리한다.

2026-10-21 기준 [공식 레퍼런스](https://docs.spring.io/spring-security/reference/whats-new.html)에 표시된 안정 버전은 **7.1.1, 7.0.7, 6.5.11** 이다.

## 1부. 필터 체인 구조

### 요청이 지나가는 길

[Servlet Architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html) 문서의 구성 요소를 요청 순서대로 놓으면 이렇다.

```
HTTP 요청
  └─ 서블릿 컨테이너의 Filter 체인
       └─ DelegatingFilterProxy            (컨테이너 ↔ Spring ApplicationContext 다리)
            └─ FilterChainProxy            (Spring Security 의 입구, Bean)
                 ├─ SecurityFilterChain 0  (/api/** 에 매칭되면 이것만)
                 ├─ SecurityFilterChain 1
                 └─ SecurityFilterChain n  (나머지)
                      └─ CsrfFilter → 인증 필터들 → ... → ExceptionTranslationFilter → AuthorizationFilter
  └─ DispatcherServlet → 컨트롤러
```

- **DelegatingFilterProxy**: 서블릿 컨테이너는 Spring Bean 을 모른다. 이 필터가 컨테이너에 등록되고, 실제 일은 ApplicationContext 의 Bean 에게 넘긴다. Bean 조회를 늦출 수 있다는 장점도 있다.
- **FilterChainProxy**: Spring Security 서블릿 지원 전체의 출발점이다. 공식 문서는 Spring Security 문제를 추적할 때 **여기에 디버그 포인트를 거는 것**이 좋은 출발점이라고 한다. 선택이 아닌 일도 여기서 한다. 메모리 누수를 막으려고 `SecurityContext` 를 비우고, `HttpFirewall` 로 특정 유형의 공격을 막는다.
- **SecurityFilterChain**: 이 요청에 어떤 보안 필터들을 적용할지 정한다. 서블릿 컨테이너 필터는 URL 로만 고르지만, FilterChainProxy 는 `RequestMatcher` 로 요청의 무엇이든 보고 고를 수 있다.

### "첫 번째로 매칭되는 체인 하나만" 실행된다

체인이 여러 개면 FilterChainProxy 는 **처음 매칭되는 SecurityFilterChain 하나만** 실행한다. 공식 문서의 예로, `/api/**` 체인이 앞에 있으면 `/api/messages/` 요청은 뒤의 체인에도 매칭되더라도 앞 체인만 탄다. 그래서 체인을 여러 개 둘 때는 **좁은 `securityMatcher` 를 가진 체인을 앞에** 두어야 한다.

```java
@Bean
@Order(1)
SecurityFilterChain api(HttpSecurity http) throws Exception {
    http
        .securityMatcher("/api/**")
        .authorizeHttpRequests((authorize) -> authorize.anyRequest().authenticated())
        .oauth2ResourceServer((rs) -> rs.jwt(Customizer.withDefaults()));
    return http.build();
}

@Bean
@Order(2)
SecurityFilterChain web(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests((authorize) -> authorize
            .requestMatchers("/", "/login").permitAll()
            .anyRequest().authenticated())
        .formLogin(Customizer.withDefaults());
    return http.build();
}
```

체인마다 필터 구성이 완전히 독립적이다. 필터가 하나도 없는 체인을 만들어 특정 요청을 Spring Security 가 무시하게 할 수도 있다.

### 필터 순서와 확인 방법

공식 문서 예시에서 `csrf`, `httpBasic`, `formLogin`, `authorizeHttpRequests` 를 켜면 핵심 순서는 이렇게 된다.

| 필터 | 추가하는 DSL |
|---|---|
| CsrfFilter | `HttpSecurity#csrf` |
| BasicAuthenticationFilter | `HttpSecurity#httpBasic` |
| UsernamePasswordAuthenticationFilter | `HttpSecurity#formLogin` |
| AuthorizationFilter | `HttpSecurity#authorizeHttpRequests` |

즉 **익스플로잇 방어 → 인증 → 인가** 순이다. 실제로는 이 밖에도 여러 필터가 끼어 있다. 애플리케이션 시작 시 DEBUG 로그에 체인별 필터 목록이 찍히므로, Boot 라면 `logging.level.org.springframework.security=DEBUG` 로 확인하는 것이 가장 빠르다. 공식 문서에 실린 기본 체인 로그는 다음 순서다.

```
DisableEncodeUrlFilter, WebAsyncManagerIntegrationFilter, SecurityContextHolderFilter,
HeaderWriterFilter, CsrfFilter, LogoutFilter, UsernamePasswordAuthenticationFilter,
DefaultLoginPageGeneratingFilter, DefaultLogoutPageGeneratingFilter, BasicAuthenticationFilter,
RequestCacheAwareFilter, SecurityContextHolderAwareRequestFilter, AnonymousAuthenticationFilter,
ExceptionTranslationFilter, AuthorizationFilter
```

정확한 순서의 원본은 `FilterOrderRegistration` 코드다.

### 401 과 403 은 ExceptionTranslationFilter 가 가른다

`ExceptionTranslationFilter` 는 뒤쪽(AuthorizationFilter 나 메서드 보안)에서 던진 예외를 HTTP 응답으로 바꾼다. 공식 문서의 의사 코드다.

```java
try {
    filterChain.doFilter(request, response);
} catch (AccessDeniedException | AuthenticationException ex) {
    if (!authenticated || ex instanceof AuthenticationException) {
        startAuthentication();   // SecurityContext 비움 → 원 요청 저장 → AuthenticationEntryPoint
    } else {
        accessDenied();          // AccessDeniedHandler
    }
}
```

- **인증이 안 된 사용자**이거나 `AuthenticationException` 이면 → `AuthenticationEntryPoint`(로그인 페이지로 리다이렉트, 또는 `WWW-Authenticate` 헤더). REST API 에서 흔히 401 이 되는 경로다.
- **인증은 됐지만 권한이 없으면** → `AccessDeniedHandler`. 흔히 403 이 되는 경로다.

이 필터가 `AuthorizationFilter` **앞**에 있기 때문에 인가 실패를 잡을 수 있다. 커스텀 필터를 이보다 뒤에 넣거나, 컨트롤러에서 직접 `AccessDeniedException` 을 잡아 버리면 이 흐름이 깨진다.

### 커스텀 필터: 어디에 넣고, Bean 으로 만들지 말 것

`HttpSecurity` 에는 `addFilterBefore`, `addFilterAfter`, `addFilterAt` 세 메서드가 있다. 위치는 필터가 **무엇이 이미 끝났기를 기대하는지**로 정한다. 공식 문서의 기준표다.

| 내 필터가 | 이 필터 뒤에 둔다 | 그 시점에 끝난 일 |
|---|---|---|
| 익스플로잇 방어 필터 | `SecurityContextHolderFilter` | SecurityContext 로드 |
| 인증 필터 | `LogoutFilter` | 위 + 익스플로잇 방어(헤더, CORS, CSRF) |
| 인가 필터 | `AnonymousAuthenticationFilter` | 위 + 인증 |

가장 흔한 함정은 **필터를 `@Component` 나 `@Bean` 으로 만드는 것**이다. 공식 문서에 따르면 Spring Boot 가 그 필터를 내장 컨테이너에도 자동 등록해서, **컨테이너에서 한 번, Spring Security 에서 한 번, 서로 다른 순서로 두 번** 실행될 수 있다. 의존성 주입 때문에 Bean 이어야 한다면 컨테이너 등록을 끈다.

```java
@Bean
FilterRegistrationBean<TenantFilter> tenantFilterRegistration(TenantFilter filter) {
    FilterRegistrationBean<TenantFilter> registration = new FilterRegistrationBean<>(filter);
    registration.setEnabled(false);   // 컨테이너에는 등록하지 않는다
    return registration;
}
```

요청당 한 번만 실행되게 하려면 `Filter` 대신 `OncePerRequestFilter` 를 상속하는 방법도 있다.

## 2부. Spring Security 7.0 에서 바뀐 것

[What's New in Spring Security 7.0](https://docs.spring.io/spring-security/reference/7.0/whats-new.html) 에서 실무 영향이 큰 것만 추렸다.

### 사라진 것 (컴파일이 깨진다)

| 사라진 것 | 대신 쓸 것 |
|---|---|
| `HttpSecurity` DSL 의 `and()` | **람다 DSL** |
| `authorizeRequests` | `authorizeHttpRequests` |
| `AntPathRequestMatcher`, `MvcRequestMatcher` | `PathPatternRequestMatcher` |
| `AuthorizationManager#check` | `AuthorizationManager#authorize` |
| OAuth 2.0 password grant 지원 | (사용 중단 — 다른 grant 로) |
| Access API(`AccessDecisionManager`, `AccessDecisionVoter` 등)의 기본 포함 | 새 모듈 `spring-security-access` 로 이동 |
| Open SAML 4 지원 | Open SAML 5 |
| Apache DS 기반 LDAP 테스트 지원 | UnboundID |

**람다 DSL 은 7.0 부터 필수다.** [6.5 의 7.0 준비 가이드](https://docs.spring.io/spring-security/reference/6.5/migration-7/configuration.html)는 이전 방식(`.and()` 체이닝)이 7.0 에서 유효하지 않다고 명시하고, 이유로 두 가지를 든다. 반환 타입을 모르면 무엇을 설정하는지 알기 어려웠고, 두 스타일이 섞여 잘못된 설정이 자주 나왔다는 것이다.

```java
// 6.x 이전 스타일 — 7.0 에서 컴파일되지 않는다
http
    .authorizeRequests()
        .antMatchers("/blog/**").permitAll()
        .anyRequest().authenticated()
        .and()
    .formLogin()
        .loginPage("/login").permitAll();

// 7.0 — 람다 DSL
http
    .authorizeHttpRequests((authorize) -> authorize
        .requestMatchers("/blog/**").permitAll()
        .anyRequest().authenticated())
    .formLogin((form) -> form
        .loginPage("/login").permitAll());
```

`requestMatchers("/blog/**")` 처럼 **문자열을 넘기는 코드는 그대로 동작**한다. 깨지는 것은 `new AntPathRequestMatcher(...)` 처럼 매처 클래스를 직접 만든 코드다. [Authorize HttpServletRequests](https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html) 문서의 방식으로 바꾼다.

```java
import static org.springframework.security.web.servlet.util.matcher.PathPatternRequestMatcher.withDefaults;

http.authorizeHttpRequests((authorize) -> authorize
    .requestMatchers(withDefaults().matcher("/api/user/**")).hasRole("USER")
    .anyRequest().authenticated());
```

### 새로 생긴 것

- **다중 인증(MFA) 지원**: 인증 메커니즘이 인증 시점에 `FactorGrantedAuthority` 를 `Authentication` 에 붙인다(예: 비밀번호 인증 → `PASSWORD_AUTHORITY`). `@EnableMultiFactorAuthentication` 으로 "비밀번호 + 일회용 토큰(OTT)" 처럼 여러 요소를 모든 인가 규칙에 요구할 수 있다([Multi-Factor Authentication](https://docs.spring.io/spring-security/reference/servlet/authentication/mfa.html)).

  ```java
  @EnableMultiFactorAuthentication(authorities = {
      FactorGrantedAuthority.PASSWORD_AUTHORITY,
      FactorGrantedAuthority.OTT_AUTHORITY })
  ```

- **SPA 용 CSRF 설정 한 줄**: `http.csrf((csrf) -> csrf.spa());`. 6.x 에서는 SPA 와 붙일 때 BREACH 보호(토큰 인코딩)와 지연 로딩된 토큰 때문에 요청 핸들러를 직접 짜야 했다. [CSRF 문서](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)는 이제 이 설정을 SPA 통합 방법으로 제시한다.
- **모듈 통합**: Spring Authorization Server 와 Spring Security Kerberos Extension 이 Spring Security 안으로 들어왔다. Authorization Server 는 PKCE 가 기본으로 켜졌다.
- **Password4j 기반 인코더**: Argon2·BCrypt·SCrypt·PBKDF2·Balloon Hashing 구현이 추가됐다.
- **`Authentication.Builder`**: `Authentication` 을 변경·병합하는 빌더.
- **OAuth2 와 HTTP Service Client 연동**, 타입 수준 `@ClientRegistrationId` 등.

### 동작이 바뀐 것 (컴파일은 되는데 결과가 다르다)

- **로그인 리다이렉트가 상대 URI 로**: 6.x 는 로그인 페이지로 보낼 때 `Location: https://myapp.example.org/my-login` 같은 절대 URI 를 썼다. 7.0 은 `Location: /my-login` 이다. 대부분은 차이를 못 느끼지만, 리버스 프록시 뒤에서 `Location` 헤더를 다시 쓰거나 테스트에서 절대 URL 을 단언하던 코드는 영향을 받는다. 되돌리려면 `LoginUrlAuthenticationEntryPoint#setFavorRelativeUris(false)` 를 쓴다([7.0 준비 가이드 — Web](https://docs.spring.io/spring-security/reference/6.5/migration-7/web.html)).
- **Jackson 3**: `SecurityJackson2Modules` 로 Jackson 2 `ObjectMapper` 를 설정하던 코드는 Jackson 3 `JsonMapper.Builder` 와 `SecurityJacksonModules` 로 바꾼다. 공식 문서는 Jackson 3 지원이 Jackson 2 와 호환되는 형식을 써서, Jackson 2 로 직렬화한 객체를 역직렬화할 수 있다고 설명한다. 세션 저장소(Spring Session 등)에 직렬화된 `SecurityContext` 가 남아 있는 서비스라면 꼭 확인할 부분이다([Migrating to 7](https://docs.spring.io/spring-security/reference/migration/index.html)).

## 3부. 옮겨 가는 순서

[Migrating to 7](https://docs.spring.io/spring-security/reference/migration/index.html) 이 권하는 순서를 그대로 따르는 것이 가장 안전하다.

1. **먼저 6.5 로 올린다.** 6.5 는 6.x 의 마지막 릴리스이고, 7.0 의 동작을 미리 켜 볼 수 있는 준비 단계([Preparing for 7.0](https://docs.spring.io/spring-security/reference/6.5/migration-7/index.html))를 제공한다. 문제가 생기면 이전 동작으로 되돌리는 옵트아웃도 들어 있다.
2. 6.5 에서 **deprecated 경고를 0개로** 만든다. `and()` 제거, `authorizeHttpRequests` 전환, 매처 교체가 여기서 끝나야 한다.
3. 메서드 보안 표현식에서 파라미터 이름(`#id`)을 쓴다면 **`-parameters` 컴파일 옵션**을 확인한다. Spring Framework 6.1 에서 `LocalVariableTableParameterNameDiscoverer` 가 제거됐기 때문이다([7.0 준비 가이드 — Authorization](https://docs.spring.io/spring-security/reference/6.5/migration-7/authorization.html)).
4. **Spring Boot 4.0 의 최신 패치**로 올리고, Spring Security 7 의 최신 패치를 쓴다.
5. Jackson 3 전환, 로그인 리다이렉트(상대 URI) 영향, Access API 사용 여부(`spring-security-access` 의존성 추가 필요)를 점검한다.

## 흔한 함정 정리

- **필터를 `@Component` 로 등록** → 두 번 실행. `FilterRegistrationBean#setEnabled(false)`.
- **체인 순서** → 넓은 매처 체인이 앞에 있으면 뒤 체인은 영영 안 탄다. 좁은 `securityMatcher` 를 앞에, `@Order` 로 명시.
- **401/403 이 기대와 다름** → `AuthenticationEntryPoint`(미인증)와 `AccessDeniedHandler`(권한 없음)를 구분해서 설정.
- **"requestMatchers 가 다 깨진다" 는 오해** → 문자열 인자는 그대로 된다. 직접 만든 `AntPathRequestMatcher` 만 바꾸면 된다.
- **디버깅** → `FilterChainProxy` 에 브레이크포인트, `logging.level.org.springframework.security=DEBUG` 로 체인별 필터 목록 확인.

## References

- Spring Security Reference, [Servlet Architecture](https://docs.spring.io/spring-security/reference/servlet/architecture.html)
- Spring Security Reference, [What's New in Spring Security 7.0](https://docs.spring.io/spring-security/reference/7.0/whats-new.html)
- Spring Security Reference, [What's New (최신 안정판)](https://docs.spring.io/spring-security/reference/whats-new.html)
- Spring Security Reference, [Migrating to 7](https://docs.spring.io/spring-security/reference/migration/index.html)
- Spring Security Reference 6.5, [Preparing for 7.0](https://docs.spring.io/spring-security/reference/6.5/migration-7/index.html) — [Configuration](https://docs.spring.io/spring-security/reference/6.5/migration-7/configuration.html), [Web](https://docs.spring.io/spring-security/reference/6.5/migration-7/web.html), [Authorization](https://docs.spring.io/spring-security/reference/6.5/migration-7/authorization.html)
- Spring Security Reference, [Authorize HttpServletRequests](https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html)
- Spring Security Reference, [Cross Site Request Forgery (CSRF)](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)
- Spring Security Reference, [Multi-Factor Authentication](https://docs.spring.io/spring-security/reference/servlet/authentication/mfa.html)
- Spring Boot Wiki, [Spring Boot 4.0 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes)
