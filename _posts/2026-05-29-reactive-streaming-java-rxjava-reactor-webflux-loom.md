---
layout: post
title: "Java 의 Reactive Streaming — *Netflix RxJava* 부터 *Spring WebFlux* 까지, 그리고 *Loom 가상스레드* 가 다시 그린 지형"
date: 2026-05-29 01:25:00 +0900
categories: [java, reactive, concurrency]
tags: [reactive-streams, rxjava, project-reactor, spring-webflux, backpressure, java-flow, akka, mutiny, virtual-threads, loom]
---

> *''비동기는 어렵다''* — 자바 진영이 *15 년 동안 그 문장을 *7 번 다시 쓰며 진화* 했다. *Future → CompletableFuture → RxJava → Reactor → Flow API → WebFlux → Virtual Threads*. 그리고 *Loom 의 가상 스레드* 가 등장한 *2023 년 이후* — *''Reactive 가 정말 필요한가''* 라는 *근본적 질문* 이 다시 던져졌다. 답은 *''필요하지만 *전보다 좁은 영역에서*''*.

이 글은 *Java Reactive Streaming 의 역사* 를 *''왜 매 단계마다 새 도구가 필요했나''* 라는 시선으로 정리한다. *RxJava 의 등장, Reactive Streams 표준화, Reactor 의 부상, Spring WebFlux 의 도박, 그리고 Loom 이 다시 그린 지형* — *''언제 reactive 를 쓰고 언제 *쓰지 말아야* 하는가''* 의 *2026 년 현재 답*.

---

## 1. *''왜 비동기가 어려운가''* — Callback Hell 의 시대

자바의 *concurrency 도구* 는 1.0 시절의 *Thread + synchronized* 로 시작했다. 그러나 *''스레드 하나 = OS 스레드 하나 = 1MB 스택''* 이라는 *비용* 이 *''만 명의 동시 사용자''* 시대를 못 받았다.

*비동기 콜백* 이 답으로 등장했다. *''결과가 나오면 이 함수를 불러줘''*. 자바 5 의 *Future*, NIO 의 *Channel/Selector*, Servlet 3 의 *AsyncContext* — 모두 *''스레드를 안 묶고 일 시키기''* 였다.

그러나 *''Callback Hell''* — *콜백 안의 콜백 안의 콜백* 은 *''에러 처리''* 와 *''취소''* 와 *''조합''* 을 *지옥으로* 만들었다. *''사용자 ID 로 user 받고, user 의 친구 목록 받고, 각 친구의 게시물 받기''* — 세 단계 비동기 호출이 *''50 줄 callback nest''* 가 되었다.

*''이걸 *함수형 합성* 으로 풀자''* 가 *Reactive 의 첫 번째 동기*.

## 2. *Reactive Manifesto* (2014) — *4 가지 약속*

2014 년 *Reactive Manifesto v2.0* 이 발표된다. 4 가지 *''반응형 시스템의 약속''*:

1. **Responsive** — *''항상 응답한다''*
2. **Resilient** — *''장애에도 살아남는다''*
3. **Elastic** — *''부하에 따라 확장한다''*
4. **Message-Driven** — *''비동기 메시지로 통신한다''*

이 *Manifesto* 가 *''Reactive 라는 단어를 *유행어* 로 만든''* 사건이었다. *Erlang/Akka 의 actor 모델* + *FRP (Functional Reactive Programming) 의 데이터 흐름* + *''non-blocking IO''* 의 결합이 *''Reactive''* 라는 우산 아래 묶인다.

## 3. *RxJava* — *Netflix 의 *첫 발걸음** (2013)

*Microsoft Rx (Reactive Extensions for .NET)* 가 2009 년에 먼저 있었다. *''Observable''* 이라는 *''비동기 이벤트 스트림''* 추상이 핵심이었다. **Netflix 의 Ben Christensen** 이 *''이걸 자바로 포팅하면 우리 마이크로서비스 문제가 풀린다''* 며 *2013 년 RxJava* 를 발표한다.

RxJava 의 *핵심 아이디어*:

- **Observable** — *비동기 이벤트 시퀀스*
- **Operators** — *map, filter, flatMap, zip, merge…* — *Stream API 와 비슷한 함수형 조합*
- **Schedulers** — *어느 스레드에서 실행할지* 명시
- **Subscription** — *언제 시작·취소할지*

```java
Observable.from(userIds)
    .flatMap(id -> userService.findById(id))
    .filter(user -> user.isActive())
    .map(User::getName)
    .subscribe(System.out::println);
```

이 *한 흐름* 으로 *''사용자 ID 들 → 활성 사용자 이름 출력''* 이 *''아무 callback 도 없이''* 표현된다. *''Callback Hell''* 이 *''Stream Pipeline''* 으로 바뀐 *결정적 순간*.

### 3.1. RxJava 가 *흥한 이유*

- **함수형 합성** — *각 operator 가 독립* 적이라 *조합 자유*
- **에러 처리** — *try/catch* 대신 *onError* 가 *''스트림의 일부''*
- **취소 가능** — *Subscription.unsubscribe()*. *''결과가 더 이상 필요 없을 때''* 명시적 중단
- **스케줄러 분리** — *''IO 는 Schedulers.io(), CPU 는 Schedulers.computation()''* — *''어디서 도는지''* 가 선언적

### 3.2. RxJava 의 *함정*

- **Memory leak** — *subscription 안 해제* 하면 *''Observable 이 계속 살아있음''*
- **Operator 60+** — *학습 곡선 엄청남*
- **Debugging 지옥** — *''스택 트레이스가 *내부 RxJava 프레임* 으로 가득''* — *원래 어디서 났는지 모름*
- **Backpressure 미흡** — RxJava 1 은 *''생산자가 빨라 소비자가 못 따라가는 상황''* 대응이 약했음

이 *''Backpressure 문제''* 가 *''표준이 필요하다''* 라는 *다음 단계의 동기*.

## 4. *Reactive Streams 표준* (2015) — *4 개의 인터페이스*

2013~2015 년 *Netflix, Pivotal, Lightbend (Akka), Red Hat* 등이 모여 *Reactive Streams* 라는 *''최소 공통 표준''* 을 만든다. 핵심은 *4 개의 인터페이스*:

```java
public interface Publisher<T> {
    void subscribe(Subscriber<? super T> subscriber);
}

public interface Subscriber<T> {
    void onSubscribe(Subscription s);
    void onNext(T t);
    void onError(Throwable t);
    void onComplete();
}

public interface Subscription {
    void request(long n);  // ← 핵심: backpressure
    void cancel();
}

public interface Processor<T,R> extends Subscriber<T>, Publisher<R> {}
```

*''request(n)''* 한 줄이 *''Reactive Streams 의 핵심 발명''* 이었다. *''소비자가 *''N 개만 보내라''* 라고 요구* 하고, *생산자는 그 이상 보내지 않는다*. 이게 **backpressure** 다 — *생산자가 빠를 때 *consumer 가 흐름을 통제* 한다*. *''호스 끝을 잡고 물을 조절''* 하는 모델.

이 표준 위에 *RxJava 2/3, Project Reactor, Akka Streams, Mutiny* 가 모두 *상호운용 가능* 한 구현으로 산다.

## 5. *Project Reactor* — *Spring 의 *선택** (2016)

**Pivotal (현 VMware)** 의 *Stéphane Maldini* 가 주도한 **Project Reactor** 가 2016 년 등장한다. *Reactive Streams 표준의 Spring 진영 구현*. *RxJava 와 거의 같은 패러다임* 이지만 *Spring 과 잘 통합* 되도록 설계됨.

**Reactor 의 두 가지 타입**:

| 타입 | 의미 | 예 |
|---|---|---|
| **Mono\<T\>** | *0 또는 1 개* 의 결과 | *DB 에서 user 한 명 조회* |
| **Flux\<T\>** | *0~N 개* 의 결과 | *DB 에서 user 목록 조회* |

```java
Mono<User> userMono = userRepository.findById(id);
Flux<Post> postsFlux = postRepository.findByUserId(id);

Mono<UserProfile> profile = userMono
    .zipWith(postsFlux.collectList(),
             (user, posts) -> new UserProfile(user, posts));
```

*RxJava 의 Observable 이 둘로 갈라진 것* — *''결과가 *하나* 인지 *여러 개* 인지를 타입으로 표현''*. 이게 *''API 가 더 명확해진다''* 는 게 Reactor 의 차별점.

## 6. *Java 9 Flow API* (2017) — *표준의 표준*

*Doug Lea* (java.util.concurrent 의 저자) 가 주도해 *Reactive Streams 표준을 *JDK 자체* 로 흡수*. *java.util.concurrent.Flow* 안에 *4 개 인터페이스가 그대로* 들어왔다.

*그러나 *''Flow API 만''* 으로 직접 코딩하는 사람은 거의 없다*. 너무 *저수준*. *''표준이 JDK 안에 있다''* 는 *''호환성 약속''* 만 의미 있을 뿐, 실제 코드는 여전히 *Reactor, RxJava, Mutiny* 를 쓴다.

## 7. *Spring WebFlux* (2017) — *Servlet 을 버린 도박*

2017 년 *Spring Framework 5* 가 **Spring WebFlux** 를 발표한다. *''Servlet API 와 *완전히 별개의* 웹 스택''*. 기반은 *Netty (non-blocking IO)*, 컨트롤러 반환 타입은 *Mono / Flux*.

```java
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public Mono<User> findUser(@PathVariable String id) {
        return userService.findById(id);  // ← 논블로킹
    }
}
```

**WebFlux 가 *제시한 약속***:

- *수 천~수 만 동시 연결* 을 *적은 스레드* 로 처리
- *I/O 대기 동안 스레드를 *''묶지 않음''* — *resource 효율*
- *backpressure 전파* — 클라이언트 느리면 *DB 쿼리도 늦춘다*

**그러나 *현실의 함정***:

1. **모든 게 reactive 여야 한다** — JDBC 가 *블로킹* 이라 *못 씀*. *R2DBC* 로 가야 함. *그런데 R2DBC 가 mature 한 게 PostgreSQL, MySQL, MSSQL 등 일부*
2. **디버깅 어렵다** — *스택 트레이스* 가 *Reactor 내부 프레임* 으로 가득
3. **학습 비용 큼** — 팀이 *''Mono/Flux 사고법''* 에 익숙해지는 데 *수 개월*
4. **3rd-party 라이브러리** — *대부분 *blocking API*. *Schedulers.boundedElastic()* 로 우회

*결과* — WebFlux 는 *''고동시성·진짜 IO 바운드''* 일 때만 *값어치 함*. *일반 CRUD* 에 쓰면 *''복잡도만 늘고 성능은 똑같음''*.

## 8. *다른 진영의 답* — *Akka Streams, Mutiny*

- **Akka Streams** — *Lightbend (Scala 진영) 의 *full reactive stack**. *backpressure 가 그래프 단위로 *''엔진 안에서''* 처리됨*. *Scala 진영 표준*. 자바에서도 쓸 수 있지만 *''Scala 같은 코드 작성 비용''*. 2022 년 *Akka 가 BSL 라이선스로 전환* 되면서 *Pekko* (Apache fork) 가 자라남
- **Mutiny** — *Quarkus 의 *reactive 라이브러리**. *Reactor 보다 *''직관적인 API''* 를 *추구*. *Uni\<T\> = Reactor 의 Mono*, *Multi\<T\> = Reactor 의 Flux*. *''await().atMost(Duration)''* 같은 *명시적 blocking 변환* 이 매력
- **RxJava 3** — 여전히 *Android 진영의 표준*. 서버 자바에선 *Reactor* 에 자리 내줌

## 9. *Backpressure* — Reactive 의 *진짜 가치*

*''왜 그냥 Thread Pool 로 안 되는가''* 라는 질문에 *Reactive 가 *진짜 다른 답을 주는* 곳* — *backpressure*.

*전통적 큐 기반 시스템* 의 문제:
- *생산자가 빠르면 *큐가 무한히 자람*. *OOM*
- *큐를 *''bounded''* 로 만들면 *생산자가 *block* 되어야* 함. *blocking*
- 또는 *''drop''* 해야 함. *데이터 손실*

*Reactive Streams* 는 *''소비자가 *N 개만 받는다* 라고 *상류에 전파*''* 한다. *''DB 가 100 개 row 를 보내려는데 *클라이언트가 10 개만* 요청''* → *DB 가 *''10 개만 조회''*. *''비어있지 않을 때만 다음 요청''*. *''pull-based push''*.

이게 *제대로 작동하는 곳* 은 *전체 흐름이 reactive 일 때*. *''중간에 blocking 한 단계''* 가 끼면 *backpressure 가 깨진다*. 그래서 *''reactive 는 전부 아니면 의미 없다''* 라는 *경구* 가 있는 것.

## 10. *Cold vs Hot* / *Multicast* 의 *함정*

| 종류 | 의미 | 예 |
|---|---|---|
| **Cold** | *각 subscriber 마다 *처음부터* 다시 emit* | DB 조회 |
| **Hot** | *현재 시점부터 emit, 이미 지난 건 *못 받음** | 마우스 이벤트, Kafka 토픽 |

*''Mono\<User\> userMono = userRepo.findById(id)''* 를 *두 번 subscribe* 하면 *DB 가 두 번 호출* 됨. *처음 보는 사람이 *제일 자주 다치는* 부분*. *.cache()* 또는 *.share()* 로 *hot 으로 전환*.

## 11. *Virtual Threads (Loom)* — *Reactive 의 *대체재* 인가*

2023 년 **JDK 21** 에 *Virtual Threads (Project Loom)* 가 *정식 출시* 된다. *''OS 스레드 한 개 위에 수 백만 개의 *경량 스레드*''*. *블로킹 코드를 *블로킹처럼* 써도 *non-blocking 처럼 도는*''*.

```java
// 전통 — 블로킹
@GetMapping("/users/{id}")
public User findUser(@PathVariable String id) {
    return userService.findById(id);  // ← 그냥 블로킹 호출
}

// Loom — 같은 코드. 단지 Tomcat 이 *''각 요청을 virtual thread 에서''* 처리
// 결과: WebFlux 와 비슷한 동시성, *그러나 코드는 단순*
```

**Loom 의 의미**:

1. *''Reactive 의 *복잡도* 없이 *동시성 이득*''* 을 얻을 수 있음
2. *blocking JDBC, blocking HTTP client* 등 *기존 자바 생태계 그대로* 쓸 수 있음
3. *디버깅·스택트레이스 평범*

*그래서 *Reactive 의 *대체재 인가*?* — *부분적으로 그렇다*. *''단순 동시성''* 이 목적이었다면 *Loom 으로 충분*. *''함수형 합성, backpressure, 스트림 변환''* 이 필요하면 *여전히 Reactor*.

**2026 년 현재의 가이드**:

| 케이스 | 추천 |
|---|---|
| *단순 REST API + JDBC* | **Loom (Virtual Threads)** — Reactive 안 씀 |
| *수십 만 동시 SSE/WebSocket* | **Reactor / WebFlux** — backpressure 가 가치 |
| *데이터 스트림 변환 (transform, merge, zip)* | **Reactor / RxJava** — 함수형 합성이 가치 |
| *Kafka 컨슈머 + 처리 파이프라인* | **Reactor + Kafka Reactor** 또는 **Akka Streams** |
| *Android* | **RxJava 3** 또는 **Kotlin Coroutines/Flow** |
| *Kotlin 서버* | **Coroutines + Flow** — 자바 reactive 안 씀 |

## 12. *Kotlin Coroutines 의 부상* — *''Reactive 를 안 쓰는 이유''*

*Kotlin* 의 *Coroutines + Flow* 가 *''Reactive 의 *가장 강한 경쟁자*''* 다. *suspend* 함수가 *''blocking 처럼 보이는 non-blocking 코드''* 를 *''Reactor 보다 훨씬 직관적으로''* 표현한다.

```kotlin
suspend fun findUserProfile(id: String): UserProfile {
    val user = userRepository.findById(id)       // ← suspend
    val posts = postRepository.findByUser(id)    // ← suspend
    return UserProfile(user, posts)
}
```

*''Mono/Flux 의 .flatMap 체인 없이 *''동기 코드처럼''*''*. Spring 도 *Kotlin Coroutines 를 *공식 지원*. *''Reactor 대신 suspend fun 반환''* 패턴이 *Kotlin 진영 표준*.

자바에 *''Loom 이 Kotlin 의 suspend 와 비슷한 자리''* 를 차지하기 시작했다. *''Reactive 가 비주류로 밀린다''* 의 *진짜 신호*.

## 13. *흔한 실수 — Reactive 를 *잘못* 쓰는 7 가지*

1. **CRUD 에 WebFlux 도입** — *복잡도만 늘고 *성능은 똑같음*. *''고동시성 IO 바운드 아니면 쓰지 마라''*
2. **블로킹 호출을 *Mono 안에서 그냥* 호출** — *event loop 스레드를 *block** → *전체 시스템 멈춤*. *Schedulers.boundedElastic()* 필수
3. **subscribe() 안 함** — *Mono/Flux 는 *''cold''* 라 *subscribe 안 하면 *아무 일도 안 일어남*. *''결과가 안 나옵니다''* 의 가장 흔한 원인
4. **block() 남용** — *''reactive 코드 안에서 .block()''* 은 *''non-blocking 의 이유 자체를 망가뜨림''*
5. **체이닝 깊이 10 단계+** — *디버깅 불가능*. *''Reactor 가 *모든 호출을 합칠* 만큼 똑똑하지 *않다*''*
6. **에러 처리 안 함** — *.onErrorReturn, .onErrorResume* 안 쓰면 *''subscription 이 silent 하게 끊김''*
7. **테스트 .block(Duration.ofSeconds(5))** — *현실에선 *훨씬 큰 지연* 이 발생*. *StepVerifier* 로 *정밀 테스트* 필수

## 14. 정리 — *''Reactive 의 진짜 자리''*

15 년의 자바 비동기 진화는 *''스레드를 어떻게 *덜 묶을까''* 의 *역사* 다:

| 시대 | 도구 | 핵심 한계 | 다음 단계가 해결한 것 |
|---|---|---|---|
| 2004 | Future | get() 이 block | 비블로킹 콜백 |
| 2009 | CompletableFuture | 조합 어려움 | 함수형 합성 (Rx) |
| 2013 | RxJava | backpressure 미흡 | 표준화 (Reactive Streams) |
| 2015 | Reactor / RS 표준 | 학습 곡선 | (해결 안 됨) |
| 2017 | WebFlux | 전체가 reactive 여야 | (현재 진행형) |
| 2023 | Virtual Threads (Loom) | — | *''Reactive 가 *''대부분의 경우*''* 불필요해짐*''* |

*''Reactive 가 죽었다''* 는 *틀린 표현*. *''Reactive 의 *적용 범위가 좁아졌다*''* 가 *정확*. *backpressure, 스트림 변환, 함수형 합성* 이 *진짜 필요한 도메인* 에선 *여전히 Reactor 가 답*. *그러나 *단순 동시성* 이 목적이었다면 *Loom 또는 Kotlin Coroutines 가 *훨씬 단순한* 답*.

> *''Reactive 는 *모든 자바 개발자가 *마스터해야 하는 도구* 였던 적이 없다*. *''특정 문제''* 에 *''특별히 잘 맞는''* 도구일 뿐. 그리고 *''특정 문제''* 의 비중이 *Loom 이후 줄어든 것*''*.

자바 백엔드 개발자가 *2026 년에 *해야 하는* 학습 순서*:

1. *Virtual Threads + Tomcat* — *기본*
2. *함수형 API + Stream* — *데이터 변환 기본*
3. *Kotlin Coroutines* — *추가 적응 비용 낮음*
4. *Reactor* — *''고동시성·진짜 스트림''* 마주칠 때

*Reactive 를 *처음부터* 시작할 필요는 *없다*. *필요할 때 배워도 *충분히 늦지 않다*''*.

---

## 더 읽을 거리

- *Reactive Manifesto* — *https://www.reactivemanifesto.org/*
- *Reactive Streams Specification* — *https://github.com/reactive-streams/reactive-streams-jvm*
- *Project Reactor Reference Documentation* — *https://projectreactor.io/docs*
- *Doug Lea — Future plans for java.util.concurrent* (JavaOne 2017)
- *JEP 444: Virtual Threads* — *https://openjdk.org/jeps/444*
- *Notes on structured concurrency* — Nathaniel J. Smith (Reactive 와 Loom 의 *철학적 비교*)
- *Kotlin Coroutines vs Reactive: a real-world comparison* (JetBrains, 2023)

*다음 글 예고: Spring Boot 4 + Virtual Threads + JPA — 왜 *대부분의 자바 백엔드* 가 *2026 년에 Reactive 를 *내려놓고* 있는가*
