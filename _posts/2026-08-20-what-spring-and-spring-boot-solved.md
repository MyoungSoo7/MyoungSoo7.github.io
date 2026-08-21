---
layout: post
title: "EJB 2.1 의 3파일에서 java -jar 한 줄까지 — 스프링/스프링부트가 실제로 지운 것들"
date: 2026-08-20 14:20:00 +0900
categories: [engineering, java]
tags: [Spring, SpringBoot, EJB, JavaEE, POJO, DI, IoC, AutoConfiguration]
---

"스프링이 왜 나왔는지" 는 자바 백엔드 인터뷰의 단골이다. 그런데 답변은 대부분 **결과의 목록** 이지 **문제의 목록** 이 아니다. "DI, AOP, POJO…" 를 나열해도, 그것이 **없던 시절엔 무엇을 견뎌야 했는가** 를 설명하지 못하면 정확한 답이 아니다. 이 글은 그 순서를 뒤집는다 — 먼저 무엇이 아팠고, 무엇이 지워졌는지 를 정리한다.

미리 밝혀두면 **스프링 부트는 EJB의 자리를 이어받은 것도 아니고, 스프링 프레임워크의 상위 호환도 아니다.** 두 도구는 서로 다른 층위의 문제를 풀었다. 그걸 하나로 뭉개면 "스프링이 마법이다" 로 끝나는 설명이 된다.

---

## 1. 스프링 이전: EJB 2.x 는 왜 무거웠나

2003년 이전에 J2EE 앱을 만든다는 것은 실질적으로 **EJB(Enterprise JavaBeans)** 를 쓴다는 뜻이었다. EJB 2.x 는 트랜잭션·보안·리모팅·수명주기를 컨테이너에 위임하는 대신, **개발자가 지불해야 하는 규정 요금** 이 컸다.

간단한 Session Bean 하나를 위해 필요한 파일은 최소 세 개였다.[^ejb-history]

```java
// 1. Remote Interface — 원격 호출용 계약
public interface HelloRemote extends EJBObject {
    String sayHello(String name) throws RemoteException;
}

// 2. Home Interface — 컨테이너에게 인스턴스를 요청하는 팩토리
public interface HelloHome extends EJBHome {
    HelloRemote create() throws RemoteException, CreateException;
}

// 3. Bean 구현체 — 실제 로직 + EJB 수명주기 콜백
public class HelloBean implements SessionBean {
    public String sayHello(String name) { return "Hi " + name; }
    public void ejbCreate() {}
    public void ejbRemove() {}
    public void ejbActivate() {}
    public void ejbPassivate() {}
    public void setSessionContext(SessionContext ctx) {}
}
```

여기에 **XML deployment descriptor** (`ejb-jar.xml`, 벤더별 `weblogic-ejb-jar.xml`/`jboss.xml` 등) 가 추가로 필요했다. 클라이언트에서 이 빈을 부르려면:

```java
Context ctx = new InitialContext();
Object ref = ctx.lookup("java:comp/env/ejb/Hello");
HelloHome home = (HelloHome) PortableRemoteObject.narrow(ref, HelloHome.class);
HelloRemote hello = home.create();
String result = hello.sayHello("Rod");
```

여덟 줄 중 실제 비즈니스 로직은 한 줄이다. 나머지는 컨테이너를 붙잡고 인스턴스를 얻어오는 절차다.

이 방식의 **비용을 항목화** 하면 이렇다.

| 항목            | EJB 2.x 에서의 비용                                                            |
| --------------- | ------------------------------------------------------------------------------ |
| 인터페이스 개수 | Remote + Home + Bean 최소 3개                                                  |
| 배포            | 벤더별 XML descriptor 필수 (WebLogic/JBoss/WebSphere 마다 다름)                |
| 테스트          | **컨테이너 없이 못 돌림** — 단위 테스트가 사실상 통합 테스트                   |
| 결합            | 비즈니스 로직 클래스가 `SessionBean` 인터페이스 · JNDI · 벤더 API 에 직접 의존 |
| 이식성          | 벤더 락인. WebLogic 에서 JBoss 로 옮기려면 descriptor 재작성                   |

Rod Johnson 이 2002년에 낸 _Expert One-on-One J2EE Design and Development_ 는 이 점을 정면으로 겨눈 책이었다. 그가 부록으로 제공한 30,000줄 규모의 프레임워크 코드가 다음 해 오픈소스로 풀렸고, 이름은 **Spring** 이었다.[^spring-history]

---

## 2. Spring 1.x (2004): 컨테이너를 뒤집었다

2004년 3월에 나온 Spring 1.0 이 실제로 지운 것은 **"컨테이너가 내 코드에 관여할 권리"** 였다. 이걸 IoC (Inversion of Control) 또는 DI (Dependency Injection) 라 부른다.

같은 서비스가 이렇게 바뀐다.

```java
// EJB 인터페이스 상속 없음. 그냥 POJO.
public class HelloService {
    private final GreetingRepository repo;
    public HelloService(GreetingRepository repo) { this.repo = repo; }  // 생성자 주입
    public String sayHello(String name) { return repo.greeting(name); }
}
```

의존성은 XML 로 배선한다.

```xml
<bean id="repo" class="com.example.GreetingRepository" />
<bean id="hello" class="com.example.HelloService">
    <constructor-arg ref="repo" />
</bean>
```

**같은 문제를 셋으로 나눠서 풀렸다.**

1. 비즈니스 로직 클래스는 인터페이스 상속·JNDI 조회에서 해방됨 → **테스트 가능** (`new HelloService(mockRepo)`)
2. 트랜잭션·보안 은 AOP 로 데코레이션 → 로직 코드가 깨끗해짐
3. 벤더 종속 사라짐 → Tomcat 이든 Jetty 든 상관없이 동일

하지만 지워진 만큼 새로 생긴 것도 있었다. **XML config** 이다. 스프링 프로젝트의 `applicationContext.xml` 이 수천 줄로 부풀어 오르는 게 흔한 풍경이 됐다. Spring 2.5 (2007) 에서 `@Autowired` · `@Component` 어노테이션이 도입되면서 XML 은 조금씩 줄었지만, 여전히 **웹 서버(Tomcat/Jetty)를 별도로 설치하고, WAR 파일을 만들어 `webapps/` 에 넣고, 서버 라이프사이클과 앱 라이프사이클을 나눠 관리** 해야 했다.

Spring 3.x (2009) 는 어노테이션 기반 config (`@Configuration`, `@Bean`) 를 정착시켰고, Spring 4.x (2013) 는 자바 8 람다·`CompletableFuture` 를 흡수했다. 그럼에도 "새 프로젝트 하나 만드는 데 필요한 최소 설정" 은 여전히 부담이었다 — pom.xml 에 스프링 코어·MVC·Jackson·Hibernate·Log4j 의 **호환되는 버전 조합** 을 직접 매기고, `web.xml` 에 DispatcherServlet 을 등록하고, tomcat-users.xml 을 손봐야 했다.

---

## 3. Spring Boot (2014): 나머지 조립 비용을 지웠다

2014년 4월, **Spring Boot 1.0** 이 나왔다.[^boot-history] Boot 가 새로 도입한 개념은 실은 딱 세 가지다.

1. **Starter 의존성** — `spring-boot-starter-web` 하나가 spring-webmvc·jackson·tomcat 등의 **검증된 버전 조합** 을 끌어옴
2. **Auto-Configuration** — 클래스패스에 `HikariCP` 가 있으면 자동으로 `DataSource` 를 만들고, `H2` 가 있으면 자동으로 in-memory DB 를 붙임
3. **Embedded Server** — Tomcat/Jetty/Undertow 가 앱과 함께 fat JAR 로 패키징 → `java -jar app.jar` 한 줄로 실행

같은 서비스가 이렇게 축소된다.

```java
@SpringBootApplication
public class HelloApp {
    public static void main(String[] args) { SpringApplication.run(HelloApp.class, args); }
}

@RestController
class HelloController {
    private final HelloService svc;
    HelloController(HelloService svc) { this.svc = svc; }  // 생성자 주입
    @GetMapping("/hello/{name}")
    String hi(@PathVariable String name) { return svc.sayHello(name); }
}
```

`web.xml` 없음. `applicationContext.xml` 없음. Tomcat 설치 없음. `mvn spring-boot:run` 하면 바로 뜬다.

거기에 **Actuator** 가 얹혔다 — `/actuator/health`, `/actuator/metrics`, `/actuator/prometheus` 같은 관측 엔드포인트가 라이브러리 한 줄로 붙는다. Kubernetes 의 liveness/readiness probe 와 자연스럽게 맞물린다. (내가 지난 이틀 [힙 예산][heap] 과 [GC 알고리즘 선택][gc] 을 팠던 그 파드도 정확히 이 Actuator 를 통해 숫자를 읽었다.)

---

## 4. 세 시대 나란히 놓기

| 항목             | Pre-Spring (EJB 2.x)                        | Spring 1~4                      | Spring Boot 1.0+                                      |
| ---------------- | ------------------------------------------- | ------------------------------- | ----------------------------------------------------- |
| 최소 파일 수     | Bean + Home + Remote + XML descriptor ≥ 4개 | POJO + applicationContext.xml   | POJO 하나 (`@SpringBootApplication`)                  |
| 의존성 배선      | JNDI lookup                                 | XML `<bean>` 또는 `@Autowired`  | Auto-config + starter                                 |
| 트랜잭션         | 컨테이너 관리 EJB, XML descriptor           | `@Transactional` (AOP)          | `@Transactional` + auto DataSource                    |
| 웹 서버          | JEE 앱 서버 설치 (WebLogic/JBoss)           | Tomcat 별도 설치, WAR 배포      | Embedded Tomcat, fat JAR (`java -jar`)                |
| 테스트           | 컨테이너 필수 → 사실상 통합 테스트          | POJO 단위 테스트 가능           | `@SpringBootTest` + Testcontainers                    |
| 새 프로젝트 시작 | 벤더 튜토리얼 하루                          | Spring Initializr 이전엔 반나절 | [start.spring.io](https://start.spring.io/) 에서 30초 |
| 관측성           | 벤더 콘솔                                   | 별도 배선 (JMX 등)              | Actuator (`/actuator/*`)                              |
| 벤더 종속        | 강함                                        | 약함                            | 없음                                                  |

**한 문장으로 요약하면**: EJB 는 "컨테이너가 코드에 개입" 을 요구했고, 스프링은 그걸 뒤집어 **코드가 컨테이너에 개입** 하게 만들었다. 스프링 부트는 그 개입조차 대부분 자동화해서 **개발자가 손을 대는 지점을 최소 라인** 으로 줄였다.

---

## 5. 그럼 스프링 부트는 완전한 해결인가

아니다. **지운 만큼 새로 생긴 문제** 가 있다. 그리고 그 문제들은 서로 무관한 잔가지가 아니라, **하나의 거래에서 파생된 것들** 이다.

### 5-1. 거래의 정체: 선언 비용 → 추론 비용

스타터는 비용을 없앤 게 아니라 **옮겼다.** XML 시절의 비용은 _쓰는 비용_ 이었다 — 무엇을 어떻게 배선할지 손으로 적어야 했다. 부트 시대의 비용은 _읽는 비용_ 이다 — 무엇이 이미 배선돼 있는지 역으로 알아내야 한다. 코드는 쓰는 일보다 읽고 고치는 일이 훨씬 많으므로, 이 교환이 항상 이득이라고 단정할 수 없다.

옮겨간 자리를 정확히 짚으면 이렇다. 스타터는 실은 두 가지다. ① 검증된 조합을 끌어오는 **의존성 묶음(BOM)**, ② `@ConditionalOnClass` · `@ConditionalOnMissingBean` 같은 조건으로 켜지고 꺼지는 **auto-configuration**. 결정적인 건 ②다. 이 순간부터 **설정은 "내가 쓴 문장" 이 아니라 "classpath 의 함수" 가 된다.**

그래서 XML 시절엔 없던 실패 모드가 생긴다.

- **빌드 파일 한 줄이 곧 설정 변경이다.** `spring-boot-starter-security` 를 추가하면 애플리케이션 코드를 한 줄도 고치지 않았는데 모든 엔드포인트가 인증을 요구하기 시작한다. 즉 `build.gradle` 의 diff 를 **설정 diff 로 읽어야** 한다.
- **부재(不在)가 원인이 된다.** `@ConditionalOnMissingBean` 때문에, 내가 빈을 _추가_ 하면 다른 배선이 _사라진다_. 범인이 "내가 쓴 코드" 가 아니라 "내 코드 때문에 사라진 코드" 라서, **grep 으로 잡히지 않는다.** 이게 다음 항목이 유독 어려운 진짜 이유다.
- **버전 결정권이 BOM 으로 넘어간다.** 내가 명시한 적조차 없는 라이브러리가 부트를 올릴 때 조용히 바뀐다.

### 5-2. 그래서 실제로 치르는 비용

- **마법의 리버스 엔지니어링 비용** — Auto-config 가 `HikariCP` 를 자동으로 잡아주는 건 편리하지만, 원하지 않는 자동 배선이 있을 때 그걸 **꺼내서 어디서 어떻게 등록됐는지 추적** 하는 일은 XML 을 읽던 시절보다 어렵다. XML 은 나빴지만 정직했다 — 파일을 열면 거기 다 있었다. 게다가 실무에서 답이 필요한 질문은 대개 "무엇이 켜졌나" 가 아니라 **"무엇이 왜 안 켜졌나"** 이고, 그 답은 report 의 _Negative matches_ 쪽에 있다. `--debug` 로 auto-configuration report 를 뽑거나 `spring-boot-actuator` 의 `/actuator/conditions` 를 봐야 한다.[^actuator-conditions]
- **버전 매트릭스는 여전** — Starter 가 조합을 잡아주지만, Spring Boot 3.x → 3.y 마이너 업그레이드에서도 Hibernate·Jackson·Netty 등의 호환성 이슈가 나온다. 메이저 경계에서는 더 깊은 일이 벌어진다. **Spring Boot 4.0 은 Jackson 3 을 기본 JSON 라이브러리로 삼았고, 자동 구성되는 빈의 _타입 자체_ 가 바뀌었다** — Jackson 3 이 classpath 에 있으면 `JsonMapper` 빈이 구성되고, Jackson 2 용 auto-config 는 deprecated 된 별도 모듈 `spring-boot-jackson2` 로 분리되어 그쪽이 `ObjectMapper` 를 구성한다.[^jackson3-json-doc] 패키지 좌표도 `com.fasterxml.jackson` 에서 `tools.jackson` 으로 옮겨갔다(`jackson-annotations` 만 예외).[^boot4-migration] 결과적으로, 손으로 만들어둔 Jackson 2 `ObjectMapper` 빈은 **더 이상 auto-config 와 같은 자리를 다투지 않는다.** `@ConditionalOnMissingBean` 으로 억제하던 관계가 타입이 달라지는 순간 성립하지 않기 때문이다. 스타터가 조합을 책임진다는 약속이 뒤집히는 지점이 바로 여기다.
- **관측 부담이 앱으로 옮겨옴** — Actuator 는 편리하지만, `/actuator/prometheus` 를 프로덕션에 열어두면 카디널리티 폭발이 실측 부담을 만든다. 이 블로그의 [지난 GC 글][gc] 이 예시다. 카디널리티보다 더 구조적인 문제는 **의존 역전** 이다. 진단 창구가 진단 대상 _안_ 에 들어가 있으므로, 앱이 뜨지 않으면 왜 안 뜨는지도 그 창구로는 볼 수 없다. JDK 도구(`jstat`, `jcmd`)가 빠진 JRE 베이스 이미지를 쓰는 컨테이너에서는 이 제약이 그대로 드러난다.
- **부팅 시간 · 메모리 발자국** — Boot 앱은 fat JAR 로 편의를 주지만, 시작 시간은 여전히 수 초 단위다. 그 수 초의 실체 중 상당 부분이 **조건 평가와 classpath 스캔** 이다. 즉 5-1 의 편의를 매 기동마다 다시 지불한다. 재기동이 잦은 쿠버네티스 환경에서는 일회성 비용이 아니라 반복 비용이 된다. GraalVM native image (Spring Boot 3.x, 2022+) 가 이 문제를 겨누고 있지만, 리플렉션·프록시가 많은 코드는 여전히 튜닝 대상이다.

### 5-3. 값을 치르는 법

문제 목록으로 끝내면 "그래서 쓰지 말라는 거냐" 가 된다. 그건 아니다. 이 비용들은 **지불 시점을 앞당기면 대부분 관리 가능** 하다.

- 프로덕션에 처음 올리기 전에 conditions report 를 **한 번은 눈으로** 볼 것. 특히 Negative matches.
- **starter 추가를 코드 리뷰 대상으로** 둘 것. 빌드 파일 한 줄이 런타임 동작을 바꾼다는 걸 팀의 기본 상식으로.
- 자동 배선을 덮어쓸 땐 **타입까지** 확인할 것. 부트 4 의 `JsonMapper` / `ObjectMapper` 가 그 교훈이다.
- 메이저 업그레이드는 릴리스 노트가 아니라 **마이그레이션 가이드** 를 읽을 것.

> 덧붙임 — 위 두 번째·세 번째 항목은 내가 직접 밟은 것이다. Boot 4 로 올린 프로젝트에서 손으로 만든 Jackson 2 매퍼가 부트의 모듈 등록을 받지 못해 런타임만 깨졌는데, 테스트는 다른 매퍼를 쓰고 있어서 **CI 는 끝까지 초록이었다.** 관측 쪽도 마찬가지로, JRE 이미지라 `jstat` 이 없어 결국 `/actuator/prometheus` 를 긁는 스크립트를 따로 만들어야 했다. 이 문단은 공식 문서가 아니라 개인 관측이다.

---

## 6. 요약

EJB 2.x 는 컨테이너에게 코드를 위임했고, 그 대가로 개발자가 절차 코드를 견뎠다. 스프링은 그 절차를 지우고 **코드를 다시 POJO로 되돌렸다** — 그 대신 XML 이 늘어났다. 스프링 부트는 그 XML 마저 자동화해서 **`java -jar` 한 줄** 로 실행되는 앱을 표준화했다.

이 세 층은 순차적으로 대체된 게 아니라 **누적되어 지워진** 것이다. 스프링 부트가 auto-config 를 하려면 Spring 프레임워크의 DI 컨테이너가 필요하고, 그 컨테이너의 존재 이유는 EJB 시대의 무게를 알아야 온전히 이해된다. 반대로 오늘 스프링 부트 프로젝트에서 헤매고 있다면, 그 답은 종종 **한 단계 아래 층** 에 있다.

[heap]: /2026/08/18/jvm-heap-budget-in-1gi-container/
[gc]: /2026/08/18/one-line-memory-limit-chose-the-gc/

[^ejb-history]: Sun Microsystems, _Enterprise JavaBeans Specification, Version 2.1_, 2003. Session Bean 의 Home/Remote/Bean 3-인터페이스 구조와 벤더별 deployment descriptor 요구사항은 이 스펙에 명시돼 있다.

[^spring-history]: Rod Johnson, _Expert One-on-One J2EE Design and Development_, Wrox, 2002. 이 책의 부록으로 배포된 프레임워크 코드가 SourceForge 에 `spring-framework` 로 공개되었고, 2004년 3월 Spring 1.0 이 릴리스됐다.

[^boot-history]: Spring Boot 1.0.0 릴리스: 2014년 4월 1일. Pivotal (당시 SpringSource) 의 Phil Webb / Dave Syer 주도. [공식 릴리스 노트 아카이브](https://github.com/spring-projects/spring-boot/releases/tag/v1.0.0.RELEASE) 참조.

[^actuator-conditions]: Spring Boot Actuator 의 `/actuator/conditions` 엔드포인트는 auto-configuration 이 각 조건 (`@ConditionalOnClass`, `@ConditionalOnMissingBean` 등) 을 어떻게 평가했는지를 보여준다. `--debug` 플래그도 시작 시 같은 보고서를 stdout 으로 덤프한다.

[^jackson3-json-doc]: Spring Boot Reference Documentation, [_JSON_](https://docs.spring.io/spring-boot/reference/features/json.html). "Jackson 3 is the preferred and default library" 및 Jackson 3 → `JsonMapper` 자동 구성 / `spring-boot-jackson2` 모듈 → `ObjectMapper` 자동 구성(deprecated), `spring.jackson2.*` 프로퍼티 분리가 명시돼 있다.

[^boot4-migration]: spring-projects/spring-boot Wiki, [_Spring Boot 4.0 Migration Guide_](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide) — "Upgrading Jackson" 절. 그룹 ID·패키지가 `com.fasterxml.jackson` 에서 `tools.jackson` 으로 이동(단 `jackson-annotations` 는 예외), 과도기용 `spring.jackson.use-jackson2-defaults` 프로퍼티와 deprecated `spring-boot-jackson2` 모듈 제공. 배경 설명은 Spring 팀 블로그 [_Introducing Jackson 3 support in Spring_](https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring) (2025-10-07) 참조.
