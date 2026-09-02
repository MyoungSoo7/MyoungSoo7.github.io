---
layout: post
title: "자바 21과 자바 25의 가상 스레드 — 21에서 막혀 있던 것이 25에서 풀렸다"
date: 2026-09-02 22:05:02 +0900
categories: [java, concurrency]
tags: [virtual-threads, loom, jep-444, jep-491, pinning, synchronized, structured-concurrency, scoped-values, jdk25]
---

가상 스레드는 자바 21에서 정식 기능이 됐다. 그런데 21을 쓰던 사람들은 곧 같은 벽을 만났다. **`synchronized` 안에서 블로킹하면 가상 스레드가 캐리어에 못 박힌다(pinning).** 그래서 "가상 스레드를 쓰려면 라이브러리부터 `ReentrantLock` 으로 갈아엎어야 한다"는 말이 따라다녔다.

자바 25는 그 벽을 치웠다. 이 글은 기능 나열이 아니라 **21에서 실제로 무엇이 막혀 있었고, 25에서 그중 무엇이 풀렸으며, 아직 무엇이 남아 있는지**를 OpenJDK 1차 문서로만 따라간다.

먼저 정직하게 짚을 것이 하나 있다. 이 변화의 핵심인 [JEP 491](https://openjdk.org/jeps/491)은 **릴리스가 24다.** 25에서 새로 들어온 게 아니라 24에서 들어와 25 LTS에 실려 있는 것이다. 그러니 이 글의 "21 vs 25"는 엄밀히 말하면 *21과, 22–25에 걸쳐 쌓인 결과*의 비교다.

---

## 1. 21이 확정한 것

[JEP 444: Virtual Threads](https://openjdk.org/jeps/444)는 JDK 19의 JEP 425, JDK 20의 JEP 436 프리뷰를 거쳐 **21에서 정식(Closed/Delivered)** 이 됐다. 모델은 이렇다. 플랫폼 스레드는 OS 스레드라 OS 스케줄러가 코어에 배정하지만, 가상 스레드는 **JDK 자신의 스케줄러**가 플랫폼 스레드 위에 *마운트* 한다. 그 플랫폼 스레드가 그 순간의 **캐리어(carrier)** 다. I/O 같은 블로킹 연산을 만나면 가상 스레드는 *언마운트* 해서 캐리어를 스케줄러에 돌려주고, 준비되면 (다른 캐리어일 수도 있는) 플랫폼 스레드에 다시 마운트돼 이어 달린다.

프리뷰 대비 21에서 확정된 변경은 JEP 444에 두 가지가 적혀 있다.

- 가상 스레드는 **언제나 스레드 로컬 변수를 지원한다** — 프리뷰에 있던 "스레드 로컬을 끄는 선택지"가 사라졌다.
- `Thread.Builder` 로 만든 가상 스레드는 **생애 내내 모니터링되고**, 새 스레드 덤프에서 관찰된다.

그리고 JEP 444는 진단용으로 시스템 프로퍼티 `jdk.tracePinnedThreads` 를 함께 도입했다. 이름 그대로, 핀 되는 지점을 찾으라고 준 물건이다. **21 시절에 그런 도구가 필요했다는 것 자체가 이 글의 주제다.**

## 2. 21에서 실제로 막혀 있던 것 — 핀의 세 가지 상황

JEP 491의 Motivation 절이 원인을 아주 분명하게 적어 놨다. `synchronized` 는 모니터(monitor)로 정의되고, JVM 은 그 모니터를 **누가 들고 있는지 추적한다. 그런데 추적하는 대상이 가상 스레드가 아니라 그 캐리어인 플랫폼 스레드였다.**

만약 `synchronized` 안에서 가상 스레드가 언마운트해 버리면, 스케줄러는 그 빈 플랫폼 스레드에 곧 **다른** 가상 스레드를 마운트한다. 그러면 JVM 이 보기에 그 다른 가상 스레드가 모니터를 들고 있는 셈이 된다. 남의 임계 구역에 걸어 들어가거나 남의 락을 풀 수 있게 된다. **상호 배제가 깨진다.** 그래서 JVM 은 언마운트를 아예 막았다. 핀은 버그가 아니라 그 시점 구현의 *필연적 귀결*이었다.

JEP 491이 드는 정본 예시는 이것이다.

```java
synchronized byte[] getData() {
    byte[] buf = ...;
    int nread = socket.getInputStream().read(buf);    // 여기서 블로킹될 수 있다
    ...
}
```

읽을 바이트가 없으면 `read` 가 블로킹된다. 가상 스레드만 멈추면 될 일인데, `getData` 가 `synchronized` 라서 **캐리어 플랫폼 스레드, 나아가 그 밑의 OS 스레드까지 함께 멈춘다.**

핀이 걸리는 상황은 세 가지다(JEP 491).

1. `synchronized` 메서드·문 **안에서 실행 중일 때**
2. 이미 남이 쥔 모니터를 얻으려고 **블로킹할 때** — 캐리어가 모니터를 획득할 때까지 JVM 안에서 막힌다
3. `Object.wait()` 과 그 타임드 변형 — `Object.notify()` 로 깨어나 캐리어가 모니터를 다시 얻을 때까지 JVM 안에서 막힌다. 이 경우는 *`synchronized` 안이라서* 한 번, *캐리어가 JVM 에서 블로킹돼서* 또 한 번, **이중으로** 핀이다

`static synchronized` 메서드(클래스 객체의 모니터)와 `synchronized` 문에도 똑같이 적용된다.

### 왜 이게 그냥 느린 정도가 아니라 위험했나

JEP 491은 결과를 이렇게 적는다 — 잦고 오래가는 핀은 확장성을 해치고, **기아(starvation)나 심지어 데드락**으로 이어질 수 있다. 스케줄러가 쓸 수 있는 플랫폼 스레드가 전부 핀 됐거나 JVM 안에서 블로킹돼 버리면 어떤 가상 스레드도 못 돈다.

"그럼 캐리어를 더 늘리면 되지 않나"는 JEP 491의 Alternatives 절에서 이미 기각됐다. 스케줄러는 `Object.wait()` 에 대해서는 실제로 여분의 플랫폼 스레드를 확보하는 보상을 하지만, 그 방식은 **확장되지 않는다**. 스케줄러가 쓸 수 있는 플랫폼 스레드 수에는 상한이 있고 **기본 상한은 256**이다. 많은 가상 스레드가 동시에 `synchronized` 안에서 블로킹되면 어떤 병렬도 값으로도 해결되지 않는다.

### 21 시절의 우회책

그래서 무슨 일이 있었나. JEP 491의 표현대로, **많은 라이브러리 관리자들이 `synchronized` 를 `java.util.concurrent` 락으로 바꿨다.** 그 락들은 핀을 걸지 않기 때문이다. 애플리케이션 코드에서도 같은 패턴이 정석으로 통했다.

```java
// 21 시절의 정석 우회 — 락을 바꾸면 핀이 사라진다
private final ReentrantLock lock = new ReentrantLock();

byte[] getData() throws IOException {
    lock.lock();
    try {
        byte[] buf = new byte[8192];
        int nread = socket.getInputStream().read(buf);   // 이제 언마운트된다
        ...
    } finally {
        lock.unlock();
    }
}
```

이게 정확히 JEP 491이 없애려던 상황이다. 문서의 Goals 는 한 줄이다 — *기존 자바 라이브러리가 `synchronized` 를 쓰지 않도록 고치지 않고도 가상 스레드에서 잘 확장되게 한다.*

## 3. 25에서 풀린 것

JEP 491(릴리스 24)은 JVM 의 `synchronized` 구현을 바꿔서 **가상 스레드가 자기 캐리어와 독립적으로 모니터를 획득·보유·해제**하게 만들었다. 마운트/언마운트가 그에 필요한 장부를 관리한다.

- **모니터 획득 대기가 언마운트한다.** 블로킹하면 캐리어를 스케줄러에 돌려주고, 모니터가 풀려 JVM 이 그 가상 스레드를 고르면 (다른 캐리어일 수 있는 곳에) 다시 마운트해 재시도한다.
- **`Object.wait()` 와 타임드 변형도 언마운트한다.** 대기 중에도, 모니터를 다시 얻으려 블로킹하는 동안에도 캐리어를 잡고 있지 않는다.

즉 위의 `synchronized byte[] getData()` 를 **한 글자도 고치지 않은 채로** 25에서 돌리면, `read` 가 블로킹될 때 캐리어가 풀린다. 21에서 라이브러리를 통째로 갈아엎게 만들던 이유가 사라진 것이다.

### 진단 도구가 바뀌었다 — 이건 마이그레이션 함정이다

두 가지가 같이 움직였다.

- **`jdk.tracePinnedThreads` 는 제거됐다.** JEP 491에 명시돼 있다 — 커맨드라인에 넣어도 **아무 효과가 없다**. 21 시절 운영 스크립트나 JVM 옵션 템플릿에 이 플래그가 남아 있다면, 25에서는 조용히 무시된다. 에러도 안 난다.
- **JFR 이벤트 `jdk.VirtualThreadPinned` 는 남았다.** 다만 용도가 바뀌었다. `synchronized` 가 더는 핀을 걸지 않으므로 그 목적으로는 필요 없어졌고, 대신 **다른** 핀 상황을 위해 유지된다. 특히 가상 스레드가 `native` 메서드나 Foreign Function & Memory API 로 네이티브 코드를 호출하고, 그 네이티브 코드가 다시 자바로 콜백해 블로킹하는 경우다. 이벤트 자체도 **핀의 이유와 캐리어 스레드의 정체를 함께 담도록** 확장됐다.

### 권고가 뒤집혔다

JEP 491은 이전 권고를 스스로 철회한다. 요지는 세 가지다.

1. 핀 문제를 `synchronized` → `ReentrantLock` 마이그레이션으로 풀라던 **이전 권고는 더 이상 필요 없다.**
2. 그렇다고 **이미 옮긴 코드를 되돌릴 필요는 없다.**
3. 새 코드라면 *Java Concurrency in Practice* §13.4의 권고를 따르라 — **편하고 실수가 적으니 가능한 곳엔 `synchronized` 를 쓰고**, 공정성·읽기쓰기 락·타임드/인터럽터블 획득·낙관적 읽기처럼 더 많은 유연성이 필요할 때 `java.util.concurrent.locks` 를 쓰라. 어느 쪽이든 **락의 범위를 좁히고, 락을 쥔 채 I/O 같은 블로킹을 하지 말라.**

마지막 문장이 중요하다. 핀이 사라졌다고 "락 쥐고 I/O 해도 된다"가 되는 게 아니다. 상호 배제는 그대로 남아 있다 — 확장을 막던 것이 *캐리어 점유*에서 *경합* 으로 정직하게 좁혀졌을 뿐이다.

## 4. 25에서도 여전히 핀이 걸리는 곳

JEP 491의 Future Work 절이 남은 경우를 명시한다. `synchronized` 와 무관한 세 가지다.

- 클래스·인터페이스의 심볼릭 참조를 해석(JVMS §5.4.3)하다가 **클래스 로딩에서 블로킹**할 때 — 스택의 네이티브 프레임 때문에 캐리어가 핀 된다
- **클래스 초기화자 안에서 블로킹**할 때 — 역시 네이티브 프레임 때문
- 다른 스레드가 **클래스를 초기화하기를 기다릴 때**(JVMS §5.5) — 가상 스레드가 JVM 안에서 블로킹돼 캐리어를 핀 한다

JEP 는 이 경우들이 "문제를 일으키는 일이 드물 것"이라 보고, 문제가 되면 다시 보겠다고 적었다. 여기에 앞서 말한 **네이티브/FFM 콜백** 을 더하면 25에서 `jdk.VirtualThreadPinned` 를 켜 둘 이유가 그대로 남는다.

## 5. 25에서 함께 달라진 주변부

가상 스레드 엔진 자체는 아니지만, 가상 스레드로 코드를 쓰는 방식을 바꾸는 것들이 25에 들어왔다.

**Scoped Values 가 정식이 됐다** — [JEP 506](https://openjdk.org/jeps/506). JDK 20 인큐베이터(JEP 429), 21 프리뷰(446)부터 22·23·24를 거쳐 25에서 final 이다. 스레드 로컬보다 추론하기 쉽고 공간·시간 비용이 낮으며, JEP 스스로 **가상 스레드·구조적 동시성과 함께 쓸 때 특히 그렇다**고 말한다. 25에서의 유일한 API 변경은 `ScopedValue.orElse` 가 더는 `null` 을 받지 않는 것이다. 21에서 "가상 스레드는 스레드 로컬을 언제나 지원한다"로 확정했던 자리에, 25에 와서 **더 싼 대안**이 정식으로 놓인 셈이다.

**구조적 동시성은 아직 프리뷰다** — [JEP 505](https://openjdk.org/jeps/505), 다섯 번째 프리뷰. 19 인큐베이터(428), 21 첫 프리뷰(453, 여기서 `fork` 가 `Future` 대신 `Subtask` 를 반환하게 됐다)를 거쳐 25에 이르렀고, JEP 525(여섯 번째 프리뷰)로 이어진다. 25의 변경은 **`StructuredTaskScope` 를 public 생성자가 아니라 정적 팩터리 메서드로 연다**는 것이다. 인자 없는 `open()` 은 "모든 서브태스크 성공 또는 하나라도 실패" 를 기다리고, 다른 정책은 `Joiner` 로 준다.

```java
// JDK 25 프리뷰 — 정적 팩터리로 연다
try (var scope = StructuredTaskScope.open()) {
    Subtask<User>  user  = scope.fork(() -> findUser(id));
    Subtask<Order> order = scope.fork(() -> fetchOrder(id));
    scope.join();                       // 전부 성공 또는 하나라도 실패까지
    return new Response(user.get(), order.get());
}
```

**`ForkJoinPool` 과 `CompletableFuture` 도 움직였다**(JDK-8319447). `ForkJoinPool` 이 `ScheduledExecutorService` 를 구현하게 됐고, 타임아웃이 지나면 취소되는 `submitWithTimeout` 이 생겼다. 그리고 **명시적 `Executor` 없는 `CompletableFuture` 비동기 메서드가 이제 `ForkJoinPool` 공통 풀에서 실행된다** — 이전에는 공통 풀 병렬도가 2 미만으로 설정된 경우 비동기 태스크마다 새 스레드를 만들었다. 동작 변화이므로 25로 올릴 때 확인할 항목이다.

**스레드 덤프에 락 정보가 들어갔다**(JDK-8356870). `HotSpotDiagnosticMXBean.dumpThreads` 와 `jcmd Thread.dump_to_file` 이 만드는 덤프가 락 정보를 포함한다. 21에서 JEP 444가 "가상 스레드가 새 스레드 덤프에서 관찰된다"고 한 뒤, 25에서 **그 덤프에 락까지 실린 것**이다. `jdk.tracePinnedThreads` 를 잃은 자리를 메우는 쪽에 가깝다.

---

## 정리 — 21과 25를 한 줄씩

| | 자바 21 | 자바 25 |
|---|---|---|
| 가상 스레드 | 정식(JEP 444) | 동일 |
| `synchronized` 안 블로킹 | **캐리어까지 멈춤(핀)** | 언마운트, 캐리어 반납(JEP 491, 24에서) |
| 경합 모니터 획득 대기 | JVM 안에서 블로킹, 핀 | 언마운트 |
| `Object.wait()` | 이중 핀 | 언마운트 |
| 권장 우회 | `synchronized` → `j.u.c.locks` 마이그레이션 | 불필요. 문제에 맞게 고르면 됨 |
| `jdk.tracePinnedThreads` | JEP 444가 도입 | **제거 — 지정해도 무효** |
| `jdk.VirtualThreadPinned` (JFR) | `synchronized` 핀 탐지용 | 네이티브/FFM 콜백 핀용, 이유·캐리어 포함 |
| 남은 핀 | 위 전부 + 클래스 로딩·초기화 | 클래스 로딩·초기화, 네이티브 콜백 |
| Scoped Values | 프리뷰(JEP 446) | **정식(JEP 506)** |
| 구조적 동시성 | 첫 프리뷰(JEP 453) | 다섯 번째 프리뷰(JEP 505), 정적 팩터리 |

21에서 25로 올릴 때 실제로 할 일은 짧다. **① `jdk.tracePinnedThreads` 를 쓰던 자리를 `jdk.VirtualThreadPinned` JFR 이벤트로 옮긴다. ② 핀을 피하려고 `ReentrantLock` 으로 옮겼던 코드는 그대로 둔다 — 되돌릴 이유가 없다. ③ `CompletableFuture` 의 기본 실행자 변경을 확인한다.** 그리고 21에서 "가상 스레드는 우리 스택에서 안 통한다"고 접어 뒀던 라이브러리가 있다면, 그 판단의 근거가 `synchronized` 였는지 다시 볼 값어치가 있다.

성능 수치를 적지 않은 것은 의도적이다. 중립적인 21↔25 헤드투헤드 벤치마크를 1차 출처에서 확인하지 못했고, 확인 못 한 숫자는 쓰지 않는다. 위의 **256** 은 벤치마크가 아니라 JEP 491이 명시한 스케줄러 기본 상한값이다.

---

## References

- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444) — Ron Pressler, Alan Bateman. Release 21, Closed/Delivered. (스레드 로컬 상시 지원, `Thread.Builder` 생애 모니터링, `jdk.tracePinnedThreads` 도입)
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491) — Patricio Chilano Mateo, Alan Bateman. **Release 24**, Closed/Delivered, hotspot/runtime. (핀의 원인·세 상황, 기본 상한 256, `jdk.tracePinnedThreads` 제거, `jdk.VirtualThreadPinned` 확장, 남은 핀 사례)
- [JEP 506: Scoped Values](https://openjdk.org/jeps/506) — Release 25, final. (`orElse` 가 `null` 을 거부)
- [JEP 505: Structured Concurrency (Fifth Preview)](https://openjdk.org/jeps/505) — Release 25, preview. (`StructuredTaskScope` 정적 팩터리, `Joiner`)
- [JDK 25 Release Notes](https://www.oracle.com/java/technologies/javase/25-relnote-issues.html) — Oracle. (JDK-8319447 `ForkJoinPool`/`CompletableFuture`, JDK-8356870 스레드 덤프 락 정보)
- Brian Goetz et al., *Java Concurrency in Practice* §13.4 — JEP 491이 새 코드 권고의 근거로 직접 인용하는 문헌.
