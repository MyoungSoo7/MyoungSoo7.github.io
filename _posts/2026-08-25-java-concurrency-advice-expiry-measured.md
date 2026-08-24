---
layout: post
title: "자바 동시성 조언에는 유통기한이 있다 — 내가 이 블로그에 쓴 것부터 틀렸다"
date: 2026-08-25 04:08:24 +0900
categories: [java, concurrency, jvm]
tags: [java, concurrency, virtual-threads, jep491, jep444, jep505, structured-concurrency, jmm, 본질]
---

동시성 글은 오래 못 간다. 알고리즘 글은 10년 가도 맞는데, 동시성 조언은 JDK 한 번 올라가면
반이 죽는다. 조언이 **런타임 구현에 붙어 있기 때문**이다. 구현이 바뀌면 조언이 같이 바뀐다.

이 글은 그걸 남의 글로 확인하지 않고 내 글로 확인한다. 2026년 6월에 이 블로그에 쓴
[가상 스레드 pinning 글](/2026/06/13/java-virtual-threads-loom-deep-dive-pinning-spring-boot/)과
[carrier thread 글](/2026/06/19/virtual-thread-and-carrier-thread-relationship/)에서,
지금 기준으로 **틀렸거나 실행하면 JVM 이 안 뜨는 대목**을 세 군데 찾았다. 전부 손으로 재서
확인했고, 재현 코드와 출력을 그대로 싣는다.

측정 환경은 같은 맥의 JDK 두 개다 — `openjdk 21.0.1` 과 `openjdk 25.0.2`, 8코어.

---

## 1. `synchronized` 는 이제 캐리어를 붙잡지 않는다

가상 스레드의 대표 함정으로 6년째 인용되는 것이 pinning 이다. `synchronized` 블록 안에서
블로킹하면 가상 스레드가 캐리어(플랫폼 스레드)에서 내려오지 못해, 스레드 수십만 개를 쓸 수
있다는 이점이 통째로 사라진다는 얘기다. JEP 491 이 그 이유를 정확히 적어 뒀다 — JVM 이
모니터 소유자를 **가상 스레드가 아니라 캐리어 기준으로 기록**하기 때문이다.

> "When a virtual thread runs a `synchronized` instance method and acquires the monitor
> associated with the instance, the JVM records the virtual thread's carrier platform
> thread as holding the monitor — not the virtual thread itself."
> — [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491)

그래서 언마운트를 허용하면 상호배제가 깨진다. JVM 은 그걸 막으려고 언마운트 자체를 금지했다.
이게 JDK 21~23 의 이야기다. JEP 491 은 **JDK 24 에 들어갔다**(Status: Closed / Delivered,
Release 24).

재는 건 간단하다. 락은 스레드마다 따로 줘서 경합을 0으로 만들고, 순수하게 "언마운트가
되는가" 만 본다.

```java
public class PinDemo {
    public static void main(String[] args) throws Exception {
        int p = Runtime.getRuntime().availableProcessors();
        int n = p * 4;                       // 캐리어보다 4배 많은 가상 스레드
        CountDownLatch done = new CountDownLatch(n);
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) {
            final Object lock = new Object();   // 스레드마다 다른 락 = 경합 없음
            Thread.ofVirtual().start(() -> {
                synchronized (lock) {
                    try { Thread.sleep(1000); } catch (InterruptedException e) { }
                }
                done.countDown();
            });
        }
        done.await();
        System.out.printf("elapsed=%dms%n", (System.nanoTime() - t0) / 1_000_000);
    }
}
```

핀이 걸리면 캐리어 8개가 한 번에 8개씩만 자므로 4번에 나눠 자게 되어 4초가 걸린다.
핀이 없으면 32개가 동시에 자고 1초에 끝난다. 실제 출력:

```
java=21.0.1  processors=8  virtualThreads=32  sleepEach=1000ms  elapsed=4587ms
java=21.0.1  processors=8  virtualThreads=32  sleepEach=1000ms  elapsed=4597ms
java=25.0.2  processors=8  virtualThreads=32  sleepEach=1000ms  elapsed=1164ms
java=25.0.2  processors=8  virtualThreads=32  sleepEach=1000ms  elapsed=1157ms
```

**4.6초 → 1.16초.** 코드는 한 글자도 안 바뀌었고 JDK 만 바뀌었다.

## 2. 그래서 폐기된 조언 — "`synchronized` 를 `ReentrantLock` 으로 바꿔라"

내 6월 글은 이렇게 적었다. *"ReentrantLock / 가벼운 lock-free 구조가 VT 시대의 기본 동시성
도구가 되어야 한다."* 그때 기준으로는 맞는 말이었다. 지금은 아니다. 특이한 건 이 조언을
**JEP 문서가 직접 철회했다**는 점이다:

> "We previously recommended solving frequent and long-lived pinning problems by migrating
> code from using `synchronized` to using `ReentrantLock`. Once the `synchronized` keyword
> no longer pins virtual threads, such migration will no longer be necessary. You need not
> revert code that has been migrated to use `ReentrantLock` back to using `synchronized`."
> — JEP 491

그리고 새 코드에 대한 권고는 20년 전 책으로 돌아간다:

> "If you are writing new code, we agree with the recommendation in *Java Concurrency in
> Practice* §13.4: Use `synchronized` where practical, since it is more convenient and less
> error prone, and use `ReentrantLock` and the other APIs in `java.util.concurrent.locks`
> when more flexibility is required."
> — JEP 491

즉 한 바퀴 돌아 제자리다. 2023~2025년의 "j.u.c 락으로 갈아타라" 는 **런타임 결함을 우회하는
임시 조치**였고, 결함이 고쳐지자 조언도 원래대로 돌아왔다. 이미 갈아탄 코드를 되돌릴 필요는
없다는 문장이 같이 붙어 있는 것도 그래서다.

## 3. 진단 방법이 통째로 바뀌었다 (그리고 내 글은 없는 옵션을 적어 뒀다)

pinning 진단으로 오래 쓰인 건 `-Djdk.tracePinnedThreads` 다. JDK 21 에서는 잘 나온다:

```
$ java21 -Djdk.tracePinnedThreads=short PinDemo.java
Thread[#64,ForkJoinPool-1-worker-7,5,CarrierThreads]
    PinDemo.lambda$main$0(PinDemo.java:19) <== monitors:1
```

같은 명령을 JDK 25 에서 돌리면 **아무것도 안 나온다.** 에러도 경고도 없다. 조용히 무시된다.
JEP 491 이 이 시스템 프로퍼티를 제거했기 때문이다:

> "This system property will no longer be needed once the `synchronized` keyword no longer
> pins virtual threads. It has, in addition, proved to be problematic since the stack traces
> are printed while executing critical code. We will therefore remove this system property;
> setting it on the command line will have no effect."
> — JEP 491

여기까지는 "옛 방법이 조용히 죽었다" 정도다. 문제는 내 6월 글이 **대체 옵션이라고 적어둔 것**
이다:

```bash
# JDK 24+   ← 내 글에 이렇게 적혀 있다
-XX:+UnlockExperimentalVMOptions -XX:+TrackVirtualThreadPinning
```

이런 VM 옵션은 없다. 실행하면 프로그램이 안 도는 정도가 아니라 **JVM 이 아예 기동하지 않는다:**

```
$ java25 -XX:+UnlockExperimentalVMOptions -XX:+TrackVirtualThreadPinning -version
Unrecognized VM option 'TrackVirtualThreadPinning'
Error: Could not create the Java Virtual Machine.
```

이게 검증 없이 쓴 글의 실제 비용이다. 읽은 사람이 운영 JVM 옵션에 넣으면 그 프로세스는 안 뜬다.

남는 정식 수단은 JFR 이벤트 하나다. JEP 491 은 `synchronized` 용도로는 필요 없어졌지만
**다른 핀 상황을 위해 유지한다**고 명시했고, JDK 25 에서 실제로 존재한다:

```
$ java25 Ev.java        # FlightRecorder.getEventTypes() 에서 virtualthread 필터
jdk.VirtualThreadEnd
jdk.VirtualThreadPinned
jdk.VirtualThreadStart
jdk.VirtualThreadSubmitFailed
```

## 4. "핀이 사라졌다" 가 아니라 "`synchronized` 때문에 생기던 핀이 사라졌다"

이건 내 글이 틀린 건 아니지만 흔한 오해라 짚어 둔다. JEP 491 의 Future Work 는 남은 경우를
셋으로 못 박는다. 전부 `synchronized` 와 무관하다.

> - "When resolving a symbolic reference (JVMS §5.4.3) to a class or interface and the
>   virtual thread blocks while loading a class."
> - "When blocking inside a class initializer."
> - "When waiting for a class to be initialized by another thread (JVMS §5.5)."
> — JEP 491, Future Work

여기에 네이티브 경계가 하나 더 있다 — 네이티브 메서드나 FFM API 로 내려간 코드가 자바로
콜백해 블로킹하면 핀이 걸린다. JEP 491 이 `jdk.VirtualThreadPinned` 이벤트를 남겨둔 이유가
바로 이 부류다.

셋 다 클래스 로딩·초기화 시점이라 정상 서비스에서는 드물게 걸린다. 문서도
*"These cases should rarely cause issues"* 라고 적었다. 다만 **기동 직후 트래픽을 붓는 구조**
라면 클래스 로딩이 집중되는 구간과 겹친다는 점은 기억해 둘 만하다.

## 5. 구조적 동시성은 아직 정식이 아니다 — 6번째 프리뷰다

내 6월 글의 비교표에는 이렇게 적혀 있다. *"구조화 동시성 — Java 21 preview, 25 정식."*
틀렸다. JDK 25 의 JEP 505 는 제목부터 **Fifth Preview** 다.

```
$ java25 Sc.java
Sc.java:1: error: StructuredTaskScope is a preview API and is disabled by default.
import java.util.concurrent.StructuredTaskScope;
  (use --enable-preview to enable preview APIs)
```

`--enable-preview` 를 주면 돈다. 그러니까 **쓸 수는 있는데 정식이 아니다.** 그리고 이건
말장난이 아니라 실제로 API 가 라운드마다 바뀐다는 뜻이다. JEP 문서에 변경 이력이 그대로 남아 있다:

- **JDK 25 (JEP 505)** — `StructuredTaskScope` 의 **public 생성자를 없애고 정적 팩토리
  `open()` 으로 교체.** 정책은 `Joiner` 로 분리.
- **JDK 26 (JEP 525)** — `Joiner.onTimeout()` 추가, `allSuccessfulOrThrow()` 의 반환형을
  스트림에서 **리스트로 변경**, `anySuccessfulResultOrThrow()` 를 `anySuccessfulOrThrow()`
  로 **개명**, `open()` 의 인자를 `Function` 에서 `UnaryOperator` 로 변경.
- **JDK 27 (JEP 533)** — **Seventh Preview.** 이 글을 쓰는 시점에 JDK 27 은 Release
  Candidate 단계이고 기능이 동결됐다. [GA 예정일은 2026년 9월 15일](https://openjdk.org/projects/jdk/27/).

JDK 26 은 [2026년 3월 17일에 GA](https://openjdk.org/projects/jdk/26/) 됐다. 인큐베이팅이
2022년 JDK 19 였으니 4년째 프리뷰이고, **다음 달에 일곱 번째 프리뷰가 나온다.** 프로덕션 코드에 넣으면 **JDK 를 올릴 때마다 컴파일이
깨지는 걸 감수**해야 한다는 뜻이다. 이건 결함이 아니라 프리뷰의 정의 그대로다.

내가 왜 틀렸는지도 분명하다. 같은 시기 같은 Loom 계열이라 **ScopedValue 와 묶어서 기억**했는데,
그쪽은 진짜로 정식이 됐다 — JEP 506, JDK 25, 최종화. 둘은 운명이 갈렸는데 나는 한 칸에 적었다.

## 6. 안 변한 것 — 메모리 모델

여기까지가 전부 "구현이 바뀌어서 조언이 죽은" 사례다. 그럼 안 죽는 건 뭔가. **자바 메모리
모델이다.** 가상 스레드는 스케줄러를 바꿨을 뿐 `Thread` 의 의미를 바꾸지 않았다. JEP 444 가
Non-Goals 에 명시했다 — *"It is not a goal to change the basic concurrency model of Java."*

그래서 `java.util.concurrent` 패키지 문서의 happens-before 목록은 6월에도 지금도 그대로다:

> "Actions in a thread prior to the submission of a `Runnable` to an `Executor`
> happen-before its execution begins. (…) Actions taken by the asynchronous computation
> represented by a `Future` happen-before actions subsequent to the retrieval of the result
> via `Future.get()` in another thread."
> — [java.util.concurrent (Java SE 25 API)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/package-summary.html)

락을 `synchronized` 로 잡든 `ReentrantLock` 으로 잡든, 플랫폼 스레드에서 돌든 가상 스레드에서
돌든, 가시성 규칙은 [JLS 17장](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html)
하나에서 나온다. 공부 시간을 어디에 쓸지 정할 때 이게 기준이 된다 — **모델은 오래 가고 튜닝
팁은 한 릴리스짜리다.**

## 7. 그럼 지금 무엇이 맞나

2026년 8월 기준으로, 1차 문서에서 직접 확인되는 것만.

- **가상 스레드를 풀에 넣지 마라.** 동시 접근 제한이 목적이면 세마포어를 써라. JEP 444 가
  명시적으로 경고한다 — *"do not be tempted to pool virtual threads in order to limit
  concurrency. Instead use constructs specifically designed for that purpose, such as
  semaphores."*
- **스레드풀 + ThreadLocal 로 비싼 자원을 캐싱하던 코드를 그대로 옮기지 마라.** 스레드가
  100만 개면 캐시도 100만 개가 된다(JEP 444).
- **CPU 바운드에는 이득이 없다.** JEP 444 의 조건은 두 개다 — 동시 작업이 수천 개 이상이고,
  워크로드가 CPU 바운드가 아닐 것.
- **스케줄러 크기.** 기본 병렬도는 가용 프로세서 수이고 `jdk.virtualThreadScheduler.parallelism`
  로 조정한다(JEP 444). 스케줄러가 쓸 수 있는 플랫폼 스레드 수의 기본 상한은 256이다(JEP 491).
- **`synchronized` 를 피하려고 코드를 비틀지 마라.** JDK 24 이상이면 그럴 이유가 없다.
- **구조적 동시성은 프리뷰다.** 쓰려면 `--enable-preview` 와 릴리스마다의 수정 비용을 같이 받아라.

그리고 하나 더. 이 글도 유통기한이 있다. 다음 달 JDK 27 이 나오면 5절의 API 이름이 또 바뀐다.
**날짜와 JDK 버전을 안 적은 동시성 글은 믿을 게 못 된다** — 내가 방금 그 예를 두 편 남겼다.

---

## 재현

이 글의 모든 출력은 macOS(8코어)에서 `openjdk 21.0.1` 과 `openjdk 25.0.2` 로 직접 실행한
것이다. `PinDemo.java` 는 위에 전문이 있고, 나머지는 각 절의 명령 한 줄이 전부다.
JDK 24 이상이면 어디서 돌려도 같은 방향의 결과가 나온다(절대 시간은 코어 수에 따라 달라진다).

## References

- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444) — OpenJDK, Ron Pressler & Alan Bateman. JDK 21, Closed/Delivered.
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491) — OpenJDK, Patricio Chilano Mateo & Alan Bateman. JDK 24, Closed/Delivered.
- [JEP 505: Structured Concurrency (Fifth Preview)](https://openjdk.org/jeps/505) — OpenJDK. JDK 25.
- [JEP 525: Structured Concurrency (Sixth Preview)](https://openjdk.org/jeps/525) — OpenJDK. JDK 26.
- [JEP 533: Structured Concurrency (Seventh Preview)](https://openjdk.org/jeps/533) — OpenJDK. JDK 27.
- [JDK 27 Project page](https://openjdk.org/projects/jdk/27/) — Release Candidate, GA 2026/09/15 예정.
- [JEP 506: Scoped Values](https://openjdk.org/jeps/506) — OpenJDK, Andrew Haley & Andrew Dinn. JDK 25, 최종화.
- [JDK 26 Project page](https://openjdk.org/projects/jdk/26/) — GA 2026/03/17.
- [java.util.concurrent — Java SE 25 API Specification](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/package-summary.html) — Memory Consistency Properties.
- [The Java Language Specification, Java SE 25 Edition, Chapter 17: Threads and Locks](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html)
- Brian Goetz et al., *Java Concurrency in Practice*, §13.4 — JEP 491 이 새 코드 권고의 근거로 직접 인용한 대목.
