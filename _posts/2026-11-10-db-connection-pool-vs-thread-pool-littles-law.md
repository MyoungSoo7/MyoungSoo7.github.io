---
layout: post
title: "DB 커넥션 풀 × 스레드 풀 — 줄은 어디에 서는가 (리틀의 법칙으로 보는 Tomcat·HikariCP·가상 스레드)"
date: 2026-11-10 23:37:39 +0900
categories: [backend, performance]
tags: [hikaricp, tomcat, thread-pool, connection-pool, virtual-threads, littles-law, spring-boot]
---

> **검증 범위.** 기본값·동작 설명은 전부 1차 문서에서 확인했다 — HikariCP README·위키, Apache Tomcat 10.1 HTTP Connector 문서, Spring Boot 공식 프로퍼티 부록, OpenJDK JEP 444/491, PostgreSQL 공식 문서. 본문의 처리량 계산(예: "500 tx/s")은 **설명용 가정값을 공식에 넣은 산술**이지 측정값이 아니다. 내 환경에서 부하 테스트로 재현한 수치는 이 글에 없다.

HikariCP 설정 하나하나의 의미, 시간 설정의 사슬, Hibernate 가 커넥션을 빌리고 돌려주는 시점은 이미 따로 정리했다([HikariCP 딥다이브]({% post_url 2026-06-10-spring-boot-db-connection-pool-hikaricp-deep-dive %}), [Hibernate × HikariCP 경계]({% post_url 2026-09-15-hibernate-hikaricp-boundary %})). 이 글은 각 풀 하나가 아니라 **두 풀이 맞물리는 방식**을 본다. 질문은 하나다.

> 요청이 몰리면, **줄은 어디에 서는가?**

## 1. 요청 하나가 통과하는 줄들

Spring Boot + 내장 Tomcat + HikariCP 의 기본 구성에서, 요청 하나는 아래 관문을 순서대로 지난다. 괄호 안은 **공식 기본값**이다.

```
클라이언트
  │
  ▼  ① OS 의 연결 대기열     server.tomcat.accept-count      (100)
  ▼  ② Tomcat 이 받은 연결   server.tomcat.max-connections   (8192)
  ▼  ③ 워커 스레드           server.tomcat.threads.max       (200)
  ▼  ④ 커넥션 풀            maximumPoolSize                 (10)   ← 대기 상한 connectionTimeout 30s
  ▼  ⑤ DB 서버              PostgreSQL max_connections       (보통 100)
```

Tomcat 문서가 ①~③의 관계를 그대로 적어 두었다. 동시 요청이 워커 스레드보다 많으면 `maxThreads` 까지 스레드를 늘리고, 그래도 넘치면 `maxConnections` 까지 연결은 받아 두되 스레드가 빌 때까지 줄 세우며, 그것도 차면 OS 가 `acceptCount` 크기의 큐에 쌓고, 그 큐마저 차면 연결이 거절되거나 타임아웃된다([Tomcat HTTP Connector](https://tomcat.apache.org/tomcat-10.1-doc/config/http.html)).

④는 HikariCP 의 몫이다. 풀이 `maximumPoolSize` 에 도달했고 놀고 있는 커넥션이 없으면 `getConnection()` 은 `connectionTimeout` 동안 블록되고, 넘기면 `SQLException` 을 던진다([HikariCP README](https://github.com/brettwooldridge/HikariCP)).

기본값만 놓고 보면 눈에 띄는 숫자가 있다. **스레드 200 개가 커넥션 10 개를 나눠 쓴다.** 이게 잘못된 설정일까?

## 2. 리틀의 법칙 — 숫자 셋의 관계

대기열 이론의 리틀의 법칙(Little, 1961)은 안정 상태의 시스템에서 다음이 성립한다고 말한다.

$$
L = \lambda W
$$

$$L$$ 은 시스템 안에 동시에 머무는 작업 수, $$\lambda$$ 는 도착률(=안정 상태의 처리량), $$W$$ 는 작업 하나가 머무는 평균 시간이다. JEP 444 도 서버 확장성을 이 법칙으로 설명한다 — 지연이 같다면 처리량을 10배로 올리려면 동시 처리 수도 10배가 되어야 한다([JEP 444](https://openjdk.org/jeps/444)).

이걸 **두 풀에 따로** 적용하면 핵심이 보인다.

**커넥션 풀이 정하는 처리량 상한.** 커넥션 하나를 붙잡는 평균 시간을 $$W_{\text{hold}}$$ 라 하면

$$
\lambda_{\max} = \frac{N_{\text{conn}}}{W_{\text{hold}}}
$$

**스레드 풀에 필요한 크기.** 요청 하나가 스레드를 붙잡는 시간 $$W_{\text{req}}$$ 는 DB 시간뿐 아니라 직렬화·외부 API·커넥션 대기까지 포함한다.

$$
N_{\text{thread}} \ge \lambda \cdot W_{\text{req}}
$$

설명용 가정을 넣어 보자. 커넥션 10 개, 트랜잭션이 커넥션을 평균 20ms 쥐면 $$\lambda_{\max} = 10 / 0.02 = 500$$ tx/s 다. 같은 요청의 전체 처리 시간이 200ms(외부 API 호출 포함)라면, 500 req/s 를 받기 위해 필요한 스레드는 $$500 \times 0.2 = 100$$ 개다. **커넥션은 10 개로 충분한데 스레드는 100 개가 필요하다** — 두 풀의 크기가 다른 건 정상이다. 두 풀은 서로 다른 $$W$$ 를 세기 때문이다.

HikariCP 위키도 같은 방향이다. 위키의 공리는 **"작은 풀을, 커넥션을 기다리는 스레드로 포화시켜라"** 이고, 1만 명의 프런트엔드 사용자가 있어도 풀은 많아야 수십 개, 나머지 애플리케이션 스레드는 풀에서 커넥션을 기다리며 블록되는 게 맞다고 쓴다([About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)). 출발점 공식은 PostgreSQL 프로젝트에서 온 것으로 소개된다.

$$
N_{\text{conn}} \approx (\text{core\_count} \times 2) + \text{effective\_spindle\_count}
$$

(코어 수에 하이퍼스레드는 넣지 않고, 활성 데이터가 전부 캐시되면 spindle 은 0 이다. 위키 스스로 "출발점일 뿐, 부하 테스트로 주변 값을 시험하라"고 단서를 단다. 위키가 인용한 Oracle 데모의 "응답시간 ~100ms → ~2ms" 는 그 데모 환경의 결과로, 일반화할 수치가 아니다.)

그러니 "스레드 200 : 커넥션 10" 자체는 잘못이 아니다. 문제는 **190 개의 대기 스레드가 어디서, 얼마나 기다리느냐**다.

## 3. 맞물림이 어긋나는 세 가지 방식

### 3-1. 줄이 커넥션 풀 앞에 서는데, 대기 상한이 너무 길다

스레드가 커넥션보다 많으면 줄은 ③(Tomcat)이 아니라 ④(Hikari `getConnection()`) 앞에 선다. 이때 Hikari 의 기본 `connectionTimeout` 은 30초다. 앞단의 로드밸런서·게이트웨이·클라이언트 타임아웃이 그보다 짧으면, **클라이언트는 이미 포기했는데 서버 스레드는 아직 커넥션을 기다리고**, 커넥션을 얻으면 아무도 받지 않을 응답을 위해 DB 작업까지 수행한다. 그동안 그 스레드는 새 요청을 받지 못한다.

처방은 크기가 아니라 순서다 — **Hikari 의 대기 상한을 상위 타임아웃보다 짧게** 둬서, 포기할 요청은 커넥션을 쓰기 전에 빨리 실패시킨다.

### 3-2. $$W_{\text{hold}}$$ 가 DB 밖에서 부푼다

위 공식에서 처리량 상한을 좌우하는 건 풀 크기보다 $$W_{\text{hold}}$$ 다. 커넥션을 쥔 채로 DB 와 무관한 일을 하면 $$W_{\text{hold}}$$ 가 커지고 $$\lambda_{\max}$$ 가 같은 비율로 떨어진다.

- `@Transactional` 메서드 안에서 외부 HTTP 호출: 가정값으로 20ms 짜리 트랜잭션에 200ms 외부 호출이 끼면 $$W_{\text{hold}} = 220$$ms, $$\lambda_{\max} = 10/0.22 \approx 45$$ tx/s — 11분의 1이다.
- OSIV(Open Session In View)로 커넥션 반납이 뷰 렌더링 뒤까지 밀리는 경우 — [이전 글]({% post_url 2026-09-15-hibernate-hikaricp-boundary %})에서 다뤘다.

이때 풀을 키우는 건 증상 완화다. 위키의 결론대로 DB 가 실제로 동시에 처리할 수 있는 수는 대략 코어 수의 두 배 근처라서, 풀을 키우면 줄이 Hikari 앞에서 DB 내부(락·컨텍스트 스위칭)로 옮겨 갈 뿐이다. **외부 호출을 트랜잭션 밖으로 빼는 것**이 $$W_{\text{hold}}$$ 를 줄이는 정공법이다.

### 3-3. 한 스레드가 커넥션 두 개를 원하면 — 풀 교착

스레드 풀이 여럿(Tomcat 워커 + `@Async` 실행기 + 배치)이고 한 풀의 커넥션을 공유할 때, 한 작업이 커넥션을 쥔 채로 두 번째 커넥션(예: `REQUIRES_NEW`)을 요청하면 교착 가능성이 생긴다. 위키가 주는 교착 회피 최소 크기는

$$
N_{\text{pool}} = T_n \times (C_m - 1) + 1
$$

$$T_n$$ 은 최대 스레드 수, $$C_m$$ 은 한 스레드가 동시에 쥐는 최대 커넥션 수다. 위키 예시로 $$T_n = 8, C_m = 3$$ 이면 17 이다. 이 공식이 **스레드 풀 크기를 직접 변수로 갖는다**는 점이 이 글의 요지와 맞닿는다 — 스레드를 늘리면 교착 회피에 필요한 커넥션도 같이 늘어난다. 위키는 이것이 "최적 크기가 아니라 교착을 피하는 최소값"이며, 풀을 키우기 전에 애플리케이션에서 해결할 수 있는지부터 보라고 권한다. 원인 코드 패턴은 [Hibernate × HikariCP 경계]({% post_url 2026-09-15-hibernate-hikaricp-boundary %}) 4절에 정리했다.

## 4. 가상 스레드를 켜면 ③이 사라진다

Spring Boot 에서 `spring.threads.virtual.enabled=true`(Java 21+)를 켜면 공식 프로퍼티 문서가 명시하듯 `server.tomcat.threads.max` 와 `threads.min-spare` 는 **효과가 없어진다**([Spring Boot 프로퍼티 부록](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)). `@Async` 등에 쓰이는 자동 구성 실행기도 가상 스레드 기반 `SimpleAsyncTaskExecutor` 로 바뀐다([Task Execution](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html)).

그러면 위 그림에서 ③ 관문이 사실상 없어진다. 동시 요청 수를 묶던 "스레드 200 개"가 사라지니, **줄은 전부 ④ Hikari 앞으로 이동한다.** 커넥션 풀이 남은 유일한 동시성 상한이 된다.

JEP 444 가 이 상황에 직접 답한다.

- 가상 스레드는 싸고 많으므로 **풀링하지 말 것.** 작업마다 새로 만든다.
- 제한된 자원에 대한 동시 접근을 묶으려고 스레드 풀 크기를 쓰던 관용구를 가상 스레드로 옮기지 말고, **세마포어처럼 그 목적에 맞는 구성 요소를 쓸 것.**
- 비싼 자원(예: DB 커넥션)을 ThreadLocal 에 캐시하던 관용구는 가상 스레드마다 자원을 만들게 되어 성능을 크게 떨어뜨릴 수 있으니 주의할 것.
- 가상 스레드는 더 빠른 스레드가 아니다 — 지연이 아니라 **처리량(규모)** 을 위한 것이다.

([JEP 444](https://openjdk.org/jeps/444))

여기서부터는 위 문서들에서 끌어낸 **내 추론**이다. 가상 스레드에서 커넥션 풀은 사실상 JEP 444 가 말하는 "세마포어" 역할을 이미 하고 있다 — 동시에 DB 에 들어가는 수를 `maximumPoolSize` 로 묶는다. 그래서 커넥션 풀을 가상 스레드 수에 맞춰 키우면 안 된다. 바뀌는 건 **대기열의 크기에 상한이 없어진다는 점**이다. 플랫폼 스레드 시절엔 Tomcat 스레드 200 개가 Hikari 앞 대기자 수를 자연스럽게 묶었지만, 가상 스레드에선 몰려온 요청이 전부 `getConnection()` 앞에서 최대 `connectionTimeout` 동안 기다린다. 3-1 의 "짧은 대기 상한" 이 선택이 아니라 필수가 되는 이유다. 대기자 수 자체를 묶고 싶으면 DB 진입 앞에 세마포어나 벌크헤드를 둔다.

핀닝도 알아 둘 것. JDK 21 에서는 `synchronized` 블록 안에서 블로킹하면 가상 스레드가 캐리어 스레드에 고정(pinned)되어 확장성이 떨어진다([Oracle Virtual Threads 문서](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)). JDK 24 의 [JEP 491](https://openjdk.org/jeps/491)이 `synchronized` 로 인한 핀닝을 거의 모두 없앴다. JDK 21 에 머무른다면 JFR 의 `jdk.VirtualThreadPinned` 이벤트로 확인한다.

## 5. 설정 순서

바깥(DB)에서 안(스레드)으로 정한다. 반대로 하면 스레드 수에 맞춰 커넥션을 늘리는 실수를 한다.

1. **DB 한도부터.** PostgreSQL `max_connections` 는 보통 기본 100 이고 서버 시작 시에만 바꿀 수 있다([PostgreSQL 문서](https://www.postgresql.org/docs/current/runtime-config-connection.html)). 인스턴스 수 × 풀 크기 + 운영 여유가 이 안에 들어와야 한다(계산은 [딥다이브 3절]({% post_url 2026-06-10-spring-boot-db-connection-pool-hikaricp-deep-dive %})).
2. **풀 크기는 작게 시작.** 위키 공식을 출발점으로, 부하 테스트에서 처리량이 꺾이는 지점을 찾는다. Hikari 는 `minimumIdle` 을 두지 않는 고정 크기 풀을 권장한다(README).
3. **대기 상한을 상위 타임아웃보다 짧게.** `connectionTimeout` < 게이트웨이·클라이언트 타임아웃.
4. **$$W_{\text{hold}}$$ 를 줄인다.** 트랜잭션 안의 외부 호출 제거, OSIV 끄기 검토.
5. **스레드 수는 리틀의 법칙으로.** $$N_{\text{thread}} \ge \lambda \cdot W_{\text{req}}$$. 커넥션 대기 시간도 $$W_{\text{req}}$$ 에 들어간다는 것을 잊지 말 것. 가상 스레드라면 이 단계 대신 세마포어·벌크헤드로 대기자 수를 묶는다.
6. **줄이 어디 서는지 관측한다.** HikariCP 의 Micrometer 지표 `hikaricp.connections.pending`(커넥션 대기 스레드 수)과 `hikaricp.connections.acquire`(획득 시간)가 ④ 앞의 줄이다. 이 값이 꾸준히 0 이 아니면 줄이 Hikari 앞에 서 있는 것이고, 그때 볼 것은 풀 크기보다 2절의 $$W_{\text{hold}}$$ 다.

## 정리

- 스레드 풀과 커넥션 풀은 서로 다른 $$W$$ 를 센다. 크기가 다른 게 정상이다.
- 처리량 상한은 $$N_{\text{conn}} / W_{\text{hold}}$$ — 풀 크기보다 **커넥션을 쥔 시간**이 더 큰 손잡이다.
- 스레드가 커넥션보다 많으면 줄은 Hikari 앞에 선다. 그 줄의 대기 상한은 상위 타임아웃보다 짧아야 한다.
- 가상 스레드를 켜면 Tomcat 스레드라는 관문이 사라지고, 커넥션 풀이 유일한 동시성 상한이자 사실상의 세마포어가 된다. 풀을 키우지 말고 대기를 묶어라.

## References

1. John D. C. Little, "A Proof for the Queuing Formula: L = λW", *Operations Research* 9(3):383–387, 1961. [doi:10.1287/opre.9.3.383](https://doi.org/10.1287/opre.9.3.383)
2. Brett Wooldridge, *About Pool Sizing*, HikariCP Wiki. <https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing>
3. HikariCP README — Configuration (`maximumPoolSize`, `connectionTimeout`, `minimumIdle` 기본값). <https://github.com/brettwooldridge/HikariCP>
4. Apache Tomcat 10.1, *The HTTP Connector* (`maxThreads`, `maxConnections`, `acceptCount`). <https://tomcat.apache.org/tomcat-10.1-doc/config/http.html>
5. Spring Boot, *Common Application Properties* (`server.tomcat.*`, `spring.threads.virtual.enabled`). <https://docs.spring.io/spring-boot/appendix/application-properties/index.html>
6. Spring Boot, *Task Execution and Scheduling*. <https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html>
7. Ron Pressler & Alan Bateman, *JEP 444: Virtual Threads* (JDK 21). <https://openjdk.org/jeps/444>
8. *JEP 491: Synchronize Virtual Threads without Pinning* (JDK 24). <https://openjdk.org/jeps/491>
9. Oracle, *Java SE 21 Core Libraries — Virtual Threads*. <https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html>
10. PostgreSQL Documentation, *Connections and Authentication* (`max_connections`). <https://www.postgresql.org/docs/current/runtime-config-connection.html>
