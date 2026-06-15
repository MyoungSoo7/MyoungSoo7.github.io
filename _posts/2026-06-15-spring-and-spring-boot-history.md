---
layout: post
title: "*Spring 과 Spring Boot* — *역사 / 버전 / 한국 시장 / 프레임 워크 의 *본질**"
date: 2026-06-15 15:15:00 +0900
categories: [backend, spring, history]
tags: [spring, spring-boot, history, framework, java, korea, ecosystem]
---

> *한국 백엔드 = Spring* 이라는 *암묵 적 *공식*.
> 그런데 *Spring 이 *어디서 시작했고 *어떻게 진화 했는지* 는 *모르는 *개발자 도 *많다*.
> 이 글은 *Spring 의 *23 년 *역사* + *버전 별 *전환점* + *한국 시장 의 *압도적 *점유* + *프레임 워크 로서 의 *본질 적 기능*.

---

## TL;DR

| 항목 | 요약 |
|------|------|
| **시작** | 2003 — Rod Johnson 의 책 *"Expert One-on-One J2EE Design"* |
| **철학** | EJB 의 *과한 복잡도* 에 반발 — IoC / DI / AOP / POJO |
| **주요 버전** | Spring 1 (2004) → 5 (2017) → 6 (2022) → 7 (2026) |
| **Spring Boot 등장** | 2014 — *Auto-configuration* 의 혁명 |
| **한국 시장 점유** | *약 *85~90%* (자바 백엔드 기준) — *세계 최고 수준* |
| **본질** | *IoC 컨테이너 + AOP + 추상 *모듈* + Boot 의 *opinionated 자동화* |

핵심 한 줄 :

> *Spring 은 *Java 의 *복잡 함 을 *간소화 하는 *움직 임*. *23 년 *진화 의 *결과 가 *지금 의 *모습*.*

---

## 1. **시작 — 2003 의 *반발*

### *EJB 의 *과한 복잡도*

2000 년 대 초 *Java 엔터프라이즈* = **EJB (Enterprise JavaBeans)** :

- *XML 디스크립터 *수십 페이지*
- *Container 의 *과한 *의존*
- *테스트 *어려움* — *컨테이너 *띄우 야 *함*
- *Remote interface, Home interface, Bean interface* 의 *3 단 강제*
- *간단 한 *클래스 가 *수십 줄 의 *보일러 플레이트*

이 *복잡 도 가 *Java 엔터프라이즈 의 *기둥 발목*.

### *Rod Johnson 의 *책*

2002 — Rod Johnson 의 *"Expert One-on-One J2EE Design and Development"* :

> *"EJB 없 이 *J2EE 의 *대부분 *기능* 을 *POJO + 간단 한 *DI 로 *구현 가능* 하다."*

이 책 의 *예제 코드* 가 *Spring 의 *시작*.

### *2003 ~ 2004 — Spring 의 *공식 출범*

- 2003 : Spring Framework *초기 *공개*
- 2004 : Spring 1.0 정식 *릴리즈*
- *전 세계 *자바 개발자 의 *대대적 *환영*

---

## 2. **Spring 버전 *연대기*

### Spring 1.0 (2004)

```
주요 기능 :
- IoC 컨테이너 (BeanFactory)
- AOP (proxy 기반)
- JDBC / ORM 추상화
- 트랜잭션 추상화
- XML 기반 설정
```

*핵심 *혁명* : *EJB 없이 *엔터프라이즈 * 기능* — *POJO 의 *철학*.

### Spring 2.0 (2006)

```
- XML namespace 추가 (간결 한 설정)
- AspectJ 통합
- Java 5 의 *어노테이션 지원 시작*
- Bean scope 추가 (request / session)
```

*XML 의 *비대화* 가 *시작*. *어노테이션 의 *예고편*.

### Spring 2.5 (2007) — *어노테이션 의 *시대*

```
- @Autowired, @Component, @Service, @Controller
- *XML 의 *대안 *처음 *공식 등장*
- *Annotation-driven 의 *시작*
```

이 *버전 부터 *Spring 의 *얼굴* 이 *바뀌었다*. *XML 줄임 → 어노테이션 *.

### Spring 3.0 (2009)

```
- Java 5+ 의무
- Java Config (@Configuration, @Bean)
- REST 지원 (@RestController 전신)
- Expression Language (SpEL)
- Spring MVC 의 *현대 적 *완성*
```

*Java Config 의 *등장 — *XML 의 *대안 *완전*. *현대 Spring 의 *얼굴* 확립.

### Spring 4.0 (2013)

```
- Java 8 지원 (Lambda + Stream)
- WebSocket / SockJS / STOMP
- Groovy 통합
- @Conditional (Spring Boot 의 *기반*)
```

*Java 8 의 *함수형 *흡수*. *Spring Boot 의 *준비 완료*.

### **Spring Boot 1.0 (2014)** — *혁명*

> *"Spring 의 *복잡 한 *설정* 을 *0* 으로."*

```
- Auto-configuration
- Starter 의존성 (spring-boot-starter-*)
- 내장 톰캣 (embedded server)
- Actuator (운영 endpoint)
- application.properties / yml
- @SpringBootApplication
```

*Java 백엔드 의 *최대 의 *전환점*. *XML 0 줄, *설정 *최소화*, *바로 동작*.

### Spring 5.0 (2017)

```
- Reactive Programming (WebFlux + Reactor)
- Kotlin 공식 지원
- Java 8 의무
- HTTP/2 지원
- 함수형 endpoint
```

*Reactive 의 *공식 흡수*. *모던 자바 의 *방향 제시*.

### Spring Boot 2.0 (2018)

- Spring 5 기반
- Reactive 지원 (`spring-boot-starter-webflux`)
- Micrometer 통합
- HikariCP 기본
- Java 8 의무

### Spring 6.0 / Spring Boot 3.0 (2022)

```
- *Java 17 의무 (LTS)*
- *Jakarta EE 9 전환* (javax.* → jakarta.*)
- GraalVM Native Image 정식 지원
- HTTP Interface (RestClient + WebClient + RestTemplate 통일 시도)
- AOT processing
- Observation API (Micrometer 통합)
```

*Java 17 + Jakarta 의 *대전환*. *2026 년 *까지 의 *주력*.

### Spring 6.1 / Spring Boot 3.2 (2023)

- *RestClient* (RestTemplate + WebClient 통합)
- Virtual Thread 지원 (Java 21)
- *Spring AI* 의 *공식 *출현*

### **Spring 7 / Spring Boot 4.0 (2026)**

```
- *Java 25 의무 (현재 LTS)*
- *Project Loom 의 *완전 통합*
- *Spring AI 의 *공식 *주류*
- *Reactive 의 *진화 + Coroutine 친화*
- *Cloud Native 의 *기본*
```

*현재 시점 의 *주력*.

---

## 3. **한국 시장 의 *Spring 점유*

### *대략적 *수치 (2026 기준)*

```
Java 백엔드 채용 공고 의 *기술 스택* :
  - Spring Boot      : ~85%
  - Spring Framework : ~5%   (legacy)
  - 기타 (Quarkus / Micronaut / Helidon) : ~10%
```

*세계 최고 수준 의 *집중*. 미국 / 유럽 *대비* 도 *압도적*.

### *왜 *한국 이 *Spring 압도 적 인가*

1. ***전자정부 표준 프레임 워크* (eGovFrame)** — 정부 의 *표준 채택* 으로 *공공 영역 의 *Spring 강제*
2. ***금융 / 통신 / 공공 의 *Java 강세*** — *기존 코드 자산* 의 *연속 성*
3. ***대학 의 *Spring 교육*** — *주요 학교 의 *Java + Spring* 의무 교육
4. ***커뮤니티 의 *성장*** — KSUG, 인프런, 강의 영상 의 *압도적 *생태계*
5. ***한국 인 *주요 기여자*** (Toby 이일민, 향로, 김영한 등) — *번역 / 강의 / 책 *의 *대중 화*

### *영향*

장점 :
- *코드 일관성*
- *인력 *교환 *쉬움*
- *생태계 *완성도*
- *커뮤니티 *지원*

단점 :
- *대안 *경험 부족* — Quarkus / Micronaut 의 *학습 *기회 줄어듦*
- *Java + Spring 외 의 *경험 적음* — *모노 컬처*
- *글로벌 변화 *느리게 *따라옴*

### *2026 년 의 *변화 *신호*

- *Kotlin + Spring 의 *증가*
- *Coroutine 의 *주류 화*
- *Spring AI 의 *대중 화*
- *Native Image 의 *프로덕션 채택 증가*
- *Quarkus / Micronaut 의 *조금씩 *시장 진입*

---

## 4. **Spring 의 *본질 — *7 가지 *핵심*

### 4.1. *IoC (Inversion of Control)*

> *"객체 의 *생성 과 *수명* 을 *컨테이너 가 *제어*."*

전통 적 — *개발자 가 *new 로 객체 생성*. Spring — *컨테이너 가 *대신*. 의존 *주입* 도 *컨테이너*.

```java
@Component
public class OrderService {
    private final UserRepository userRepository;
    
    public OrderService(UserRepository ur) {
        this.userRepository = ur;
    }
}
```

→ *new 가 *없다*. *Spring 컨테이너 가 *자동 주입*.

### 4.2. *DI (Dependency Injection)*

*IoC 의 *구체 화 *형태*. *생성자 / 세터 / 필드* 의 *3 가지 *주입* 방법.

```java
// 생성자 — 권장
public OrderService(UserRepository ur) { ... }

// 세터
@Autowired
public void setUserRepository(UserRepository ur) { ... }

// 필드 — 권장 안 함
@Autowired
private UserRepository userRepository;
```

### 4.3. *AOP (Aspect Oriented Programming)*

*횡 단 관심 사* (cross-cutting concerns) 의 *모듈 화* :

- 로깅
- 보안
- 트랜잭션
- 캐싱

```java
@Aspect
@Component
public class LoggingAspect {
    @Around("@annotation(MyAnnotation)")
    public Object log(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = pjp.proceed();
        log.info("took: {}", System.currentTimeMillis() - start);
        return result;
    }
}
```

*비즈니스 로직 과 *횡 단 관심 사 의 *분리*.

### 4.4. *POJO (Plain Old Java Object)*

> *"순수 한 *Java 객체* 만 으로 *프레임 워크 활용*."*

```java
// ❌ EJB 시대
public class OrderBean implements EntityBean {
    public void ejbCreate() { ... }
    public void ejbLoad() { ... }
    public void ejbStore() { ... }
    // 수 십 줄 의 *컨테이너 강제 코드*
}

// ✅ Spring 시대
public class Order {
    private Long id;
    private BigDecimal amount;
    // *순수 Java*
}
```

### 4.5. *Abstraction (추상화 모듈)*

*JDBC / ORM / Transaction / Cache / Messaging* 의 *추상화* :

- `JdbcTemplate`
- `JpaRepository`
- `@Transactional`
- `RedisTemplate`
- `KafkaTemplate`

*공통 인터페이스 *위 에 *구체 구현 교체* 가능.

### 4.6. *Annotation-driven*

*XML 의 *제거*. *어노테이션 으로 *의도 *명시*.

```java
@Service
@Transactional(readOnly = true)
public class UserService { ... }

@RestController
@RequestMapping("/api/users")
public class UserController { ... }
```

### 4.7. *Convention over Configuration* (Spring Boot 의 *핵심*)

> *"기본 설정 이 *적정* — 필요 할 때 만 *명시*."*

```
spring-boot-starter-web 추가 만 으로 :
  - 톰캣 자동 시작
  - Jackson JSON 자동
  - DispatcherServlet 자동 설정
  - Actuator 활성 (옵션)
```

*몇 줄 의 *의존 추가* 가 *수십 줄 의 *설정 *대체*.

---

## 5. **Spring 생태계 의 *주요 *프로젝트*

### *Core*

- **Spring Framework** — IoC / AOP / MVC / Reactive
- **Spring Boot** — *자동 설정 + Starter*
- **Spring Data** — JPA / MongoDB / Redis / Elasticsearch
- **Spring Security** — *인증 / 권한*
- **Spring Cloud** — *마이크로 서비스 인프라*

### *통합*

- **Spring Integration** — *통신 패턴*
- **Spring Batch** — *대량 처리*
- **Spring AMQP** — *RabbitMQ*
- **Spring Kafka** — *Kafka*
- **Spring Session** — *세션 분산*

### *최근*

- **Spring AI** (2023+) — *AI / LLM 통합*
- **Spring Modulith** — *모듈러 모놀리식*
- **Spring HTTP Interface** — *Feign 의 *대안*
- **Spring Native** (deprecated → GraalVM 통합)

---

## 6. **Spring Boot 의 *Magic 의 *내부*

### *@SpringBootApplication 의 *3 합*

```java
@SpringBootApplication = 
  @Configuration +
  @ComponentScan +
  @EnableAutoConfiguration
```

- `@Configuration` — Bean 정의 가능
- `@ComponentScan` — `@Component` 들 자동 등록
- `@EnableAutoConfiguration` — *Magic 의 *핵심*

### *Auto-configuration 의 *동작*

```
1. classpath 의 의존 *분석*
2. spring-boot-autoconfigure 의 *@Configuration 들 *확인*
3. *조건 (@ConditionalOn*) 만족 시 *자동 적용*
```

예 — *HikariCP 가 classpath 에 있으면* DataSource 자동 설정.

### *Starter 의 *역할*

```
spring-boot-starter-web :
  - spring-web
  - spring-webmvc
  - tomcat-embed
  - jackson-databind
  - ...
```

*하나 의 *starter 가 *수십 의 *의존 통합*.

→ ***개발자 가 *적정 *조합 *고민 *안 해도 됨***. *Boot 의 *진짜 가치*.

---

## 7. **Spring 의 *진화 의 *교훈*

### *복잡도 의 *흡수*

- *2003* : *EJB 의 *복잡도* → Spring 이 *POJO 로 *간소화*
- *2014* : *Spring 자체 의 *복잡도* → Boot 가 *Auto-config 로 *간소화*
- *2026* : *MSA 의 *복잡도* → Spring Cloud + Modulith 가 *간소화*

*Spring 의 *역할* = *Java 의 *복잡도 를 *흡수 하는 *움직임*. 23 년 동안 *변하지 않은 정체성*.

### *변화 의 *수용*

- *2009* : Annotation 의 *수용*
- *2014* : Convention over Configuration 의 *수용*
- *2017* : Reactive 의 *수용*
- *2022* : Jakarta EE 9 + GraalVM 의 *수용*
- *2023+* : Spring AI 의 *수용*

→ *Spring 의 *역사 = *Java 변화 의 *역사*.

---

## 8. **2026 년 의 *Spring 사용자 의 *시야*

### *핵심 *질문*

> *"Spring 만 *알면 *충분 한가*?"*

답 :

- *현재* : *대부분 한국 기업 에서 *Yes*
- *5 년 후* : *불충분 *가능*

*권장 *준비*:

1. ***Spring 의 *깊이*** — *어노테이션 *외우 기 *말고* *내부 동작 이해*
2. ***Kotlin + Spring 의 *학습*** — *생산성 ↑*
3. ***Coroutine + Reactive 의 *친화*** — *Java Loom 적응*
4. ***Spring 외 *대안 *경험*** — Quarkus / Micronaut 한 번 *시도*
5. ***시스템 설계 의 *원리*** — *프레임 워크 무관 한 *깊이*

### *Spring 의 *현대 적 *학습 *순서*

```
1. Spring Boot 의 *기본 기능* 사용 (1 개월)
2. *Auto-config 의 *동작 *이해* (2 개월)
3. *AOP / @Transactional 의 *내부* (3 개월)
4. *Spring Security 의 *Filter Chain* (4 개월)
5. *Spring Data 의 *Repository 추상* (5 개월)
6. *Spring AI / Spring Cloud 의 *통합* (6 개월)
```

*반 년* 이면 *대부분 *영역* 커버.

---

## 9. *내 *7 년 의 *Spring 회고*

### *3 년 전* 까지 — *기능 *외우는* 단계*

- *어노테이션 의 *이름 *외우기*
- *Boot 의 *Magic 에 의지*
- *내부 동작 *모름*

### *5 년 차* — *내부 호기심*

- *@Transactional 의 *Proxy 패턴 분석*
- *Bean 의 *생성 순서 이해*
- *Auto-config 의 *조건 분석*

### *7 년 차* (현재) — *시스템 *시각*

- *Spring 의 *각 기능 의 *디자인 패턴 매핑*
- *Spring 의 *한계 *식별 가능*
- *프레임 워크 *교체 *판단 기준*
- *Java 의 *진화 + Spring 의 *진화 의 *동기 *예측 가능*

---

## 10. **흔한 *오해*

### 10.1. *"Spring = EJB 의 *대안 *일 뿐*"*

→ *옛 시각*. *현대 Spring 은 *Java 백엔드 의 *기둥*. *대안 의 *수준 *완전 *능가*.

### 10.2. *"Boot 가 *모든 걸 *알아서 *해줌*"*

→ *부분 적 *맞음*. *Auto-config 의 *조건 이해 가 *없으면 *디버깅 *지옥*.

### 10.3. *"한국 의 *Spring 편중 = *시장 의 *약점*"*

→ *부분 *맞음*. *글로벌 *경쟁력 의 *우려 도 *있지만* *국내 시장 의 *생산성 ↑*.

### 10.4. *"Spring 의 *깊이 = 어노테이션 *암기*"*

→ *틀림*. *내부 동작 + 디자인 패턴 + 시스템 직관* 의 *총합* 이 *깊이*.

---

## 11. *마치며*

> *Spring 은 *23 년 *진화* 의 *결과 — *Java 의 *복잡도 를 *흡수* 하는 *최대 의 *움직임*. *Spring 의 *내부 를 *깊이 이해 하면 *Java 백엔드 의 *대부분 *영역 *이 *명확 해 진다*.

3 줄 요약 :

1. **Spring = *2003 EJB 반발 → 2014 Boot 혁명 → 2022 Java 17/Jakarta → 2026 AI 통합*** — *변화 의 *연속*.
2. **한국 *85~90% 점유* — *국내 *생산성 ↑*, *글로벌 *적응 도 함께 *준비 필요***.
3. **본질 = *IoC + DI + AOP + POJO + 추상 + Annotation + Convention*** — *7 개 의 *기본 *원칙 의 *조합*.

7년차 회고 :

> *"Spring 의 *얼굴 은 *수많이 *변했지만* — *복잡도 흡수 의 *철학* 은 *23 년 *내내 *동일*. *그게 *프레임 워크 의 *진짜 가치*."*

다음 글 — *Spring AI 의 *깊이* — RAG / Function Calling / Embedding / ChatModel 의 *통합 사용*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 / Spring 운영 회고*. *역사 사실 은 *문헌 기반*. *시장 점유* 는 *2026 년 상반기 *추정 수치* — *공식 조사 와 *다를 수 있음*.
