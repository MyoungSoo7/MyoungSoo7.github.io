---
layout: post
title: "Netty 는 NIO 를 예쁘게 감싼 게 아니다 — 나타나기 전과 후"
date: 2026-08-24 06:16:00 +0900
categories: [network, jvm]
tags: [netty, nio, java, c10k, loom, 본질]
---

Netty 를 "NIO 를 쓰기 편하게 감싼 라이브러리" 라고 설명하는 글이 많다. 틀린 말은 아닌데,
그 설명으로는 **왜 하필 Netty 여야 했는지**가 안 나온다. 편의성이 이유였다면 대체재가
수십 개 나왔어야 하는데 그러지 않았다.

이 글은 세 가지만 본다. 나타나기 전엔 뭐가 아팠나, 정확히 무엇을 겨냥해 나타났나,
나타난 뒤 무엇이 달라졌고 **무엇은 아직 안 풀렸나.**

---

## 1. 나타나기 전 — 커넥션 하나가 스레드 하나였다

`java.io` 시절 서버의 모양은 하나였다. 접속이 들어오면 스레드를 하나 붙이고, 그 스레드가
그 연결을 끝까지 책임진다. 읽을 게 없으면 `read()` 에서 블록된 채 기다린다.

이 구조가 왜 벽에 부딪히는지는 나중에 OpenJDK 가 JEP 444 에서 아주 간명하게 정리했다.
스레드-당-요청 방식의 확장성은 Little's Law 의 지배를 받는다 — 지연이 고정일 때
처리량을 10배 늘리려면 동시 처리 수도 10배가 되어야 하고, 요청 하나가 스레드 하나를
잡는다면 **스레드 수가 처리량에 비례해 늘어야 한다.** 그런데:

> "the number of available threads is limited because the JDK implements threads as
> wrappers around operating system (OS) threads. OS threads are costly, so we cannot
> have too many of them"
> — [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)

즉 CPU 도 네트워크도 남아도는데 **스레드가 먼저 바닥난다.** 풀링을 해도 소용없다.
풀링은 스레드 생성 비용을 줄일 뿐 총 개수를 늘려주지 않기 때문이다(같은 문서).

이게 업계에서 이름을 얻은 게 1999~2001년의 **C10K 문제**다. Dan Kegel 이 정리한
그 문서의 첫 문장은 지금 읽어도 도발적이다:

> "It's time for web servers to handle ten thousand clients simultaneously, don't you
> think?"
> — [The C10K problem](https://www.kegel.com/c10k.html)

Kegel 의 논지는 하드웨어가 이미 충분하다는 것이었다. 1만 클라이언트를 감당할 CPU·RAM·NIC
가격이 이미 내려왔는데 못 하고 있다면, 그건 **하드웨어 문제가 아니라 I/O 전략과 API 의
문제**라는 것.

### 자바의 공식 답변: JSR 51

자바 진영의 대응은 명시적이었다. 2000년 1월 제출되어 2002년 5월 최종 릴리스된
**JSR 51 — New I/O APIs for the Java Platform** 이다. 스펙 리드는 Mark Reinhold.
이 JSR 이 스스로 밝힌 목적 중 첫 번째가 이거다:

> "The scalable I/O API will make it easier to write production-quality web and
> application servers that scale well to thousands of open connections"
> — [JSR 51](https://jcp.org/en/jsr/detail?id=51)

그리고 이 JSR 의 Expert Group 명단에 누가 있었냐면 — **Dan Kegel** 과 **Doug Lea** 다.
C10K 를 쓴 사람이 그 문제를 풀 자바 API 를 같이 설계했다. 우연이 아니라 직접 연결된
계보다.

그렇게 `Selector`, `ByteBuffer`, `SocketChannel` 이 들어왔다. 스레드 하나가 수천 개
연결을 돌볼 수 있게 됐다. **문제가 풀린 것처럼 보였다.**

---

## 2. 그런데 왜 Netty 가 필요했나

NIO 가 준 것은 **메커니즘**이지 **프레임워크**가 아니었다. `Selector` 를 손에 쥔 개발자가
그 다음에 직접 써야 하는 목록은 대략 이렇다.

- 이벤트 루프 자체 (select → 키 순회 → 디스패치 → 다시 select)
- **프레이밍.** TCP 는 스트림이라 메시지 경계가 없다. 반쪽만 온 패킷을 모아 두고
  다음 조각을 기다리는 누산 버퍼를 직접 관리해야 한다
- 스레드 핸드오프 (I/O 스레드에서 비즈니스 로직을 어디로 넘길 것인가)
- 백프레셔 (쓰기가 밀릴 때 읽기를 멈출 것인가)
- SSL/TLS 핸드셰이크 상태 기계

이건 "조금 불편하다" 수준이 아니라 **매번 서버를 쓸 때마다 프로토콜 스택을 다시 짜는**
일이다. Netty 프로젝트가 스스로 밝힌 존재 이유가 정확히 여기에 있다:

> "The Netty project is an effort to provide an asynchronous event-driven network
> application framework and tooling for the rapid development of maintainable
> high-performance and high-scalability protocol servers and clients."
> — [Netty User guide for 4.x](https://netty.io/wiki/user-guide-for-4.x.html)

여기까지가 흔히 하는 설명이다. **그런데 이게 본질이 아니다.**

### 진짜 이유: 메커니즘 자체가 고장나 있었다

NIO 는 편의성만 부족했던 게 아니라 **버그가 있었다.** 가장 유명한 게 리눅스에서
`Selector.select(timeout)` 이 블록하지 않고 즉시 돌아와 버리는 문제다. 이벤트가 없는데도
루프가 계속 돌아 **CPU 를 100% 태운다.**

OpenJDK 버그 데이터베이스에 그대로 남아 있다 —
[JDK-6403933 "(se) Selector doesn't block on Selector.select(timeout) (lnx)"](https://bugs.openjdk.org/browse/JDK-6403933),
담당자 Alan Bateman, 영향 버전에 `1.4.2_13` 과 `6` 이 찍혀 있고 상태는 Fixed.

여기서 Netty 의 성격이 드러난다. Netty 는 이 버그를 **기다리지 않고 우회했다.** 지금도
`NioEventLoop` 소스 최상단에 이런 static 블록이 있다:

```java
// Workaround for JDK NIO bug.
//
// See:
// - https://bugs.openjdk.java.net/browse/JDK-6427854 for first few dev (unreleased) builds of JDK 7
// - https://bugs.openjdk.java.net/browse/JDK-6527572 for JDK prior to 5.0u15-rev and 6u10
// - https://github.com/netty/netty/issues/203
```

그리고 실제 방어 로직은 이렇다 (`io.netty.selectorAutoRebuildThreshold`, 기본값 **512**):

```java
if (SELECTOR_AUTO_REBUILD_THRESHOLD > 0 &&
        selectCnt >= SELECTOR_AUTO_REBUILD_THRESHOLD) {
    // The selector returned prematurely many times in a row.
    // Rebuild the selector to work around the problem.
    logger.warn("Selector.select() returned prematurely {} times in a row; rebuilding Selector {}.",
            selectCnt, selector);
    rebuildSelector();
    return true;
}
```

`select()` 가 연속 512번 헛돌면 **Selector 를 통째로 새로 만들어 갈아끼운다.** JDK 를
못 고치니 런타임에 갈아치우는 것이다. 같은 파일에 JDK 의 `HashSet` 기반 selected-key
집합을 배열 기반 `SelectedSelectionKeySet` 으로 **리플렉션으로 바꿔 끼우는** 코드도 있다
(`io.netty.noKeySetOptimization` 으로 끌 수 있다).
([NioEventLoop.java, 4.1 브랜치](https://github.com/netty/netty/blob/4.1/transport/src/main/java/io/netty/channel/nio/NioEventLoop.java))

**이게 본질이다.** Netty 가 대체 불가였던 이유는 API 가 예뻐서가 아니다.
_JDK 와 커널과 수많은 프로덕션 장애에서 나온 흉터를 대신 지고 있어서_ 다. 직접 NIO 로
서버를 짜면 저 512번 헛도는 Selector 를 **당신이 새벽에 발견하게 된다.**

참고로 Netty 는 JBoss 산하에서 시작했다. Maven Central 에 남은 최초 좌표가
`org.jboss.netty:netty:3.0.0.GA` 라는 데서 계보가 그대로 보인다. netty.io 는 저자가
2003년부터 유사한 프레임워크를 써 왔다고 밝히고 있다.

---

## 3. 나타난 후 — 무엇이 달라졌나

가장 크게 달라진 건 **"프로토콜 서버를 만든다" 가 "이벤트 루프를 짠다" 와 분리된 것**이다.

Netty 프로젝트가 관리하는 [Adopters 목록](https://netty.io/wiki/adopters.html)에는
gRPC, Elasticsearch, Apache Cassandra, Apache Spark, Apache Flink, Apache Pulsar,
Apache Druid, Hazelcast, Helidon 이 올라 있고, Facebook(Nifty)·Twitter(Finagle)·Apple
사례도 링크돼 있다. *(주의: 이건 프로젝트가 직접 관리하는 자기 목록이다. 중립 제3자
집계가 아니다.)*

더 흥미로운 건 **다른 프레임워크의 설계 근거로 인용되기 시작했다**는 점이다. Spring 이
WebFlux 를 왜 만들었는지 설명하는 공식 문서는 이렇게 적는다:

> "This was the motivation for a new common API to serve as a foundation across any
> non-blocking runtime. That is important because of servers (such as Netty) that are
> well-established in the async, non-blocking space."
> — [Spring Framework Reference, WebFlux Overview](https://docs.spring.io/spring-framework/reference/web/webflux/new-framework.html)

Netty 가 "잘 자리잡은 기반" 이라는 전제 위에서 상위 프레임워크가 설계된 것이다.
**바닥이 되면 사람들이 그 위에 집을 짓는다.** 그게 나타난 후의 가장 큰 변화다.

---

## 4. 그런데 아직 안 풀린 것 — 이 문단이 없으면 홍보문이다

### (1) 자바에 수동 메모리 관리가 돌아왔다

Netty 의 `ByteBuf` 는 GC 대상이 아니라 **참조 카운팅 객체**다. 공식 유저 가이드가 아주
직설적으로 적어 놨다:

> "ByteBuf is a reference-counted object which has to be released explicitly via the
> `release()` method. Please keep in mind that it is the handler's responsibility to
> release any reference-counted object passed to the handler."
> — [Netty User guide for 4.x](https://netty.io/wiki/user-guide-for-4.x.html)

GC 언어를 쓰면서 `release()` 를 손으로 부른다. 안 부르면 샌다. Netty 가 누수 탐지기를
기본 탑재하고 있다는 사실 자체가 **누수가 예외가 아니라 예상 상황**이라는 뜻이다.

### (2) 이벤트 루프를 막으면 전부 멈춘다

`NioEventLoop` 의 선언은 `public final class NioEventLoop extends SingleThreadEventLoop`
다. 이름 그대로 **단일 스레드**가 자기에게 등록된 모든 채널을 돌본다. 여기서 따라 나오는
결론은 코드를 읽으면 바로 보인다 — 핸들러 안에서 JDBC 호출 하나를 블로킹으로 하면,
그 EventLoop 에 매달린 **모든 연결이 같이 선다.** 성능 저하가 아니라 정지다.

이건 벤치마크가 필요한 주장이 아니라 클래스 선언에서 나오는 구조적 귀결이다. 그리고
이 함정은 15년째 그대로 있다.

### (3) 애초의 전제가 다시 열렸다

가장 근본적인 변화다. Netty 가 존재하는 이유는 **"연결마다 스레드를 줄 수 없다"** 였다.
JEP 444 가 JDK 21 에서 가상 스레드를 정식 기능으로 넣으면서 그 전제가 흔들렸다.

그리고 같은 JEP 가 비동기 스타일의 대가를 공식 문서에서 이례적으로 솔직하게 적었다:

> "In the asynchronous style, each stage of a request might execute on a different
> thread... Stack traces provide no usable context, debuggers cannot step through
> request-handling logic, and profilers cannot associate an operation's cost with its
> caller."
> — [JEP 444](https://openjdk.org/jeps/444)

Netty 로 서버를 짜 본 사람이면 이 세 줄이 뭘 말하는지 안다. 스택 트레이스가 쓸모없고,
디버거로 요청을 따라갈 수 없고, 프로파일러가 비용을 누구 탓으로 못 돌린다. **그건 Netty
의 결함이 아니라 비동기라는 선택 자체의 값이다.** 그리고 JEP 444 의 목표는 그 값을
치르지 않고도 확장하게 하는 것이다.

그렇다고 Netty 가 사라졌냐면 아니다. **한 층 아래로 내려갔다.** gRPC 도 Spring WebFlux
(Reactor Netty)도 여전히 그 위에 있다. 다만 *"이걸 안 쓰면 방법이 없다"* 는 시절은
끝났고, 이제는 **"이 층에서 무엇을 얻고 무엇을 잃는가"** 를 고르는 문제가 됐다.

---

## 정리

| | 내용 |
|---|---|
| **전** | 연결마다 스레드. OS 스레드가 비싸 CPU 남기고 스레드가 먼저 고갈 (C10K) |
| **왜** | NIO(JSR 51)가 메커니즘은 줬으나 프레이밍·백프레셔·TLS 는 매번 재구현. **게다가 Selector 가 리눅스에서 헛돌았다** |
| **후** | 프로토콜 서버 작성이 이벤트 루프 작성과 분리. 상위 프레임워크의 기반층이 됨 |
| **미해결** | `release()` 수동 호출 / EventLoop 블로킹 시 전면 정지 / JEP 444 로 전제 자체가 재개봉 |

한 줄로 줄이면 — **Netty 는 NIO 를 편하게 만든 게 아니라, NIO 가 깨져 있던 자리마다
흉터를 대신 지고 서 있었던 것이다.** 그 흉터가 코드에 주석으로 남아 있는 걸 직접 보면
이 프레임워크의 성격이 한 번에 이해된다.

---

### 근거의 한계

- 성능 우열(예: "Netty 가 X 보다 빠르다")은 이 글에서 **주장하지 않는다.** 재현 가능한
  중립 제3자 헤드투헤드 벤치마크를 확인하지 못했다.
- Adopters 목록은 Netty 프로젝트가 직접 관리하는 자기 목록이며 제3자 검증 집계가 아니다.
- `org.jboss.netty:netty:3.0.0.GA` 의 Maven Central 등록 시각은 확인했으나, 그것이 최초
  *릴리스* 시점과 같다고 단정하지 않는다(일괄 동기화된 흔적이 있다). 그래서 본문에는
  연도 대신 **group id 로 드러나는 계보**만 적었다.

---

## References

1. Dan Kegel, [*The C10K problem*](https://www.kegel.com/c10k.html)
2. JCP, [*JSR 51: New I/O APIs for the Java Platform*](https://jcp.org/en/jsr/detail?id=51) — Spec Lead: Mark Reinhold / EG: Dan Kegel, Doug Lea 외. Final Release 2002-05-09
3. OpenJDK, [*JEP 444: Virtual Threads*](https://openjdk.org/jeps/444) — JDK 21
4. OpenJDK Bug System, [*JDK-6403933 (se) Selector doesn't block on Selector.select(timeout) (lnx)*](https://bugs.openjdk.org/browse/JDK-6403933)
5. Netty, [*User guide for 4.x*](https://netty.io/wiki/user-guide-for-4.x.html)
6. Netty, [*NioEventLoop.java (4.1)*](https://github.com/netty/netty/blob/4.1/transport/src/main/java/io/netty/channel/nio/NioEventLoop.java)
7. Netty, [*Adopters*](https://netty.io/wiki/adopters.html) — 프로젝트 자체 관리 목록
8. Spring, [*Spring Framework Reference — WebFlux Overview*](https://docs.spring.io/spring-framework/reference/web/webflux/new-framework.html)
9. Maven Central, [`org.jboss.netty:netty`](https://repo1.maven.org/maven2/org/jboss/netty/netty/)
