---
layout: post
title: "코루틴이 가상 스레드보다 가볍다는 말이 뒤집히는 지점 — 자바 25 에서 직접 재봤다"
date: 2026-09-02 22:39:17 +0900
categories: [Java, Kotlin]
tags: [java25, virtual-threads, kotlin-coroutines, loom, jep444, jep491, benchmark]
---

이 블로그엔 가상 스레드와 코루틴을 비교한 글이 이미 두 편 있다. 둘 다 *개념* 비교였다. 이번 글은
다르다. 같은 기계, 같은 JDK 25 에서 같은 모양의 일을 양쪽으로 돌려 **숫자를 재고**, 그 숫자가
통념과 어긋나는 한 지점을 찾아 바이트코드까지 열어본 기록이다.

찾은 것은 이거다. 코루틴이 메모리를 덜 쓰는 건 맞는데, **항상은 아니다.** 중단 지점을 넘어
살아남아야 하는 상태가 많아지면 코루틴 쪽이 가상 스레드보다 **1.85 배 더** 썼다. 그리고 그 경계는
"스레드냐 상태 머신이냐" 가 아니라 컴파일러가 상태 머신을 **만들어야 하느냐 마느냐** 에 있었다.

---

## 1. 두 진영이 서로에 대해 남긴 공식 기록

이 비교가 재미있는 건 양쪽 1차 문서가 서로를 명시적으로 언급하기 때문이다.

가상 스레드를 확정한 **JEP 444** 는 "Alternatives" 절에서 async/await 식 문법적 코루틴을
자바에 넣지 않은 이유를 적으면서 코틀린을 이름으로 지목한다.

> Most languages that have adopted syntactic coroutines have done so due to an inability to
> implement user-mode threads (e.g., Kotlin), legacy semantic guarantees (e.g., the inherently
> single-threaded JavaScript), or language-specific technical constraints (e.g., C++). These
> limitations do not apply to Java.[^jep444-alt]

요약하면 "너희는 못 해서 그렇게 한 거고, 우리는 할 수 있다" 다.

반대편, 코틀린 공식 문서의 "Comparing coroutines and JVM threads" 절은 코루틴이 왜 가벼운지를
숫자로 설명한다.

> For 50,000 threads, that can be up to 100 GB, compared to roughly 500 MB for the same number
> of coroutines.[^kotlin-compare]

100 GB 대 500 MB. 200 배다. 그런데 이 문단이 비교 대상으로 쓰는 코드는 `kotlin.concurrent.thread`,
즉 **플랫폼 스레드**다. 같은 절 어디에도 virtual thread 라는 단어는 없다(2026 년 7 월 27 일자
기준). 그 200 배는 JDK 21 이 바꿔놓은 전제 위에서 나온 숫자다.

그래서 세 번째 줄이 필요하다. 같은 일을 **가상 스레드로** 돌리면 어디에 서는가.

---

## 2. 재는 방법

코틀린 문서의 예제 모양을 그대로 옮겼다. N 개를 띄우고 각자 5 초 쉬고 끝난다.

```java
// Sleep.java — 같은 코드로 mode 만 바꿔 플랫폼/가상 스레드 둘 다 돌린다
ThreadFactory factory = "virtual".equals(mode)
        ? Thread.ofVirtual().factory()
        : Thread.ofPlatform().factory();

CountDownLatch latch = new CountDownLatch(n);
for (int i = 0; i < n; i++) {
    factory.newThread(() -> {
        try { Thread.sleep(Duration.ofSeconds(5)); } catch (InterruptedException ignored) {}
        latch.countDown();
    }).start();
}
latch.await();
```

```kotlin
// sleep.kt — 코틀린 문서 예제와 같은 구조
runBlocking {
    withContext(Dispatchers.Default) {
        repeat(n) { launch { delay(5000L) } }
    }
}
```

측정 환경은 macOS x86_64 8 코어, **OpenJDK 25.0.2** (Homebrew), `kotlinx-coroutines-core` 1.11.0,
`kotlinc` 2.4.10 이다. 코틀린 쪽은 `-jvm-target 25` 로 컴파일해 클래스 파일 major version 을 69 로
맞췄다. 메모리는 `/usr/bin/time -l` 의 maximum resident set size, 각 구성 3 회.

> **먼저 밟은 함정 하나.** 처음엔 `JAVA_HOME=$(/usr/libexec/java_home -v 25)` 로 잡았다. 이게
> **JDK 26.0.2.1 을 돌려준다.** macOS 의 `java_home -v` 는 정확 일치가 아니라 *그 이상* 을
> 매칭하고, 이 기계엔 26 이 링크돼 있었다. `-v 25.0.2` 로 적어도 26 이 나온다. 에러도 경고도 없다.
> 25 를 재려면 keg 경로를 직접 박아야 했다. 처음 낸 수치는 전부 26 의 것이었고 버렸다.

---

## 3. 1 라운드 — 코틀린 문서 예제 그대로, 50,000 개

| 구성 | spawn | total | max RSS |
|---|---|---|---|
| 플랫폼 스레드 | — | **4,068 개에서 OOM** | 180–188 MiB |
| 가상 스레드 | 0.17 s | 5.29 s | 133–140 MiB |
| 코루틴 | 0.22 s | 5.55 s | 76–83 MiB |

(3 회 중앙값. RSS 는 범위.)

플랫폼 스레드는 50,000 근처도 못 간다. 3 회 모두 **정확히 4,068 개**에서 같은 자리에 멈췄다.

```
FAILED after 4068 threads: java.lang.OutOfMemoryError: unable to create native thread:
possibly out of memory or process/resource limits reached
[warning][os,thread] Failed to start thread - pthread_create failed (EAGAIN)
```

이 4,068 은 이 기계의 숫자다(`ulimit -u` 가 2784). 다른 기계에선 다른 값이 나온다. 코틀린 문서도
"may throw an out-of-memory error or slow down thread creation" 이라고 적어두었고, 실제로 그렇게
됐다.

여기까지는 코틀린 문서가 맞다. 다만 **세 번째 줄이 추가되면 그림이 달라진다.** 가상 스레드도
5.29 초에 멀쩡히 끝냈고, 메모리는 코루틴의 1.7 배였다. 200 배가 아니라 1.7 배다.

## 4. 2 라운드 — 100 만 개

| 구성 | spawn | total | max RSS |
|---|---|---|---|
| 가상 스레드 | 1.31 s | 17.76 s | 930–1046 MiB |
| 코루틴 | 1.31 s | 10.40 s | 484–570 MiB |

100 만 개에서도 둘 다 끝난다. 코루틴이 시간은 1.7 배, 메모리는 1.8 배쯤 유리하다. 의미 있는
차이지만 자릿수 차이는 아니다.

가상 스레드 쪽 메모리가 어디서 오는지는 JEP 444 가 직접 적어둔다.

> The stacks of virtual threads are stored in Java's garbage-collected heap as stack chunk
> objects. The stacks grow and shrink as the application runs (…).[^jep444-mem]

힙에 들어간 스택 조각이다. 코루틴 쪽의 대응물은 컴파일러가 만든 continuation 객체다. **둘 다
"중단된 실행을 힙에 적어둔 것"** 이라는 점에서 같은 물건이다. 그러면 크기 차이는 어디서 나는가.

## 5. 3 라운드 — 스택을 깊게 만들면 뒤집힌다

앞의 두 워크로드는 호출 깊이가 사실상 0 이다. 중단 시점에 적어둘 게 별로 없다. 그래서 깊이를
100 으로 만들고 200,000 개를 돌렸다.

```java
// Deep.java
static void down(int d) {
    if (d == 0) { Thread.sleep(Duration.ofSeconds(5)); return; }
    down(d - 1);
}
```

```kotlin
// deep.kt — 재귀 호출이 꼬리 위치에 있다
suspend fun down(d: Int) {
    if (d == 0) { delay(5000L); return }
    down(d - 1)
}
```

| 구성 | spawn | total | max RSS |
|---|---|---|---|
| 가상 스레드 | 0.68 s | 9.37 s | 756–758 MiB |
| 코루틴 (위 코드) | 0.50 s | 6.78 s | 149–155 MiB |

5 배 차이. 코루틴의 압승처럼 보인다. **그런데 이 숫자는 틀린 것을 재고 있었다.**

`deep.kt` 의 `down` 은 재귀 호출이 **꼬리 위치**에 있다. 호출하고 나면 할 일이 없다. 코틀린 코루틴
설계 문서(KEEP-0164)가 이 경우를 따로 규정한다.

> In the simplest case, a suspending function invokes other suspending functions only at *tail
> positions* (…). They are compiled just like regular non-suspending functions (…).
>
> In a case when suspending invocations appear in non-tail positions, the compiler creates a
> state machine for the corresponding suspending function. An instance of the state machine
> object in created when suspending function is invoked (…).[^keep164]

즉 **꼬리 호출이면 상태 머신 자체가 안 만들어진다.** 100 단계를 내려가도 힙에 남는 건 맨 아래
`delay` 하나뿐이다. 반면 자바 쪽은 실제로 100 개 프레임을 쌓았다가 그걸 통째로 힙에 적어둔다.
같은 일을 잰 게 아니었다.

jar 를 열어 확인했다.

```
=== deep.jar (꼬리 호출) ===
   3213  DeepKt.class
   3487  DeepKt$main$total$1$1.class
   ...                                  ← down 의 상태 머신 클래스가 없다

=== deep2.jar (비꼬리) ===
   4175  Deep2Kt.class
   1338  Deep2Kt$down$1.class           ← 비꼬리에서만 생긴다
   3695  Deep2Kt$main$total$1$1.class
```

그래서 재귀 호출 뒤에 실제로 할 일을 남겨 꼬리 호출을 깼다.

```kotlin
// deep2.kt — 중단 지점 이후에 d 를 다시 쓴다. 컴파일러가 레벨마다 상태를 보존해야 한다.
suspend fun down(d: Int): Int {
    if (d == 0) { delay(5000L); return 0 }
    val r = down(d - 1)
    return r + d
}
```

| 구성 (200,000 개 × 깊이 100) | spawn | total | max RSS |
|---|---|---|---|
| 가상 스레드 | 0.68 s | 9.37 s | **756–758 MiB** |
| 코루틴 — 꼬리 호출 | 0.50 s | 6.78 s | 149–155 MiB |
| 코루틴 — **비꼬리** | 1.14 s | 6.59 s | **1353–1501 MiB** |

**뒤집혔다.** 같은 깊이, 같은 개수인데 코루틴이 가상 스레드의 **1.85 배**를 썼다. (반환값
`sink=5050` = 1+2+…+100 이 찍히는 걸로 재귀가 실제로 계산됐음을 확인했다. 컴파일러가 지워버린 게
아니다.)

## 6. 그래서 경계는 어디인가

정리하면 이렇다.

- 중단 지점을 넘어 **살아남아야 할 상태가 거의 없으면** — 코루틴이 확실히 싸다. 컴파일러가
  상태 머신을 아예 안 만들거나, 만들어도 필드 몇 개다.
- 살아남아야 할 상태가 **진짜로 많으면** — 양쪽 다 그걸 힙에 적어야 한다. 같은 정보량이다.
  이 실측에선 오히려 레벨마다 별도 객체를 만드는 코루틴 쪽이 컴팩트한 스택 조각보다 컸다.

코루틴의 이점은 "스레드가 아니라서" 가 아니라 **"필요 없는 상태를 컴파일 타임에 안 만들어서"**
다. 그 판정이 안 서는 코드에선 이점이 사라지고, 여기선 역전됐다.

JEP 444 도 스택 조각이 "more compact" 하다고 적고 있고, 플랫폼 스레드 스택과 달리 GC 루트가
아니라 stop-the-world 스캔에서 순회되지 않는다는 점도 함께 적어둔다.[^jep444-mem] 다만 같은 절에
경고도 있다 — G1 은 humongous stack chunk 를 지원하지 않아, 가상 스레드 스택이 리전 크기의
절반(작으면 512 KB)에 닿으면 `StackOverflowError` 가 날 수 있다.

---

## 7. 핀은 사라지지 않았다, 자리를 옮겼을 뿐이다

JDK 24 의 **JEP 491** 이 `synchronized` 핀을 없앴다.[^jep491] 21 시절 가상 스레드의 가장 큰 함정이
사라진 것이다. 문서는 이제 이렇게 안내한다.

> Once the `synchronized` keyword no longer pins virtual threads, you can choose between
> `synchronized` and the APIs in the `java.util.concurrent.locks` package based solely upon
> which best solves the problem at hand.[^jep491-choose]

그런데 **코루틴 쪽에도 구조적으로 같은 문제가 있고, 이건 런타임이 고쳐줄 수 없다.** 코루틴 안에서
`delay` 가 아니라 진짜 블로킹 호출을 하면 디스패처의 스레드가 통째로 묶인다. 재봤다.

```kotlin
// block.kt — delay 가 아니라 Thread.sleep 이다
withContext(dispatcher) { repeat(n) { launch { Thread.sleep(5000L) } } }
```

| 디스패처 | n=64 | n=512 |
|---|---|---|
| `Dispatchers.Default` (8 코어) | **41.23 s** | — |
| `Dispatchers.IO` (기본 상한 64) | 5.21 s | **41.25 s** |
| 가상 스레드 executor | 5.21 s | **5.22 s** |

`Dispatchers.Default` 는 코어 수만큼이라 64 개를 8 개씩 8 번에 나눠 처리한다. 5 초짜리가 41 초가
됐다. 블로킹엔 `Dispatchers.IO` 를 쓰라는 게 관례고 실제로 n=64 는 해결되지만, 그건 **상한이
8 에서 64 로 옮겨간 것뿐**이라 512 개에서 똑같이 41 초가 된다.

세 번째 줄이 답이다. 디스패처를 `Executors.newVirtualThreadPerTaskExecutor().asCoroutineDispatcher()`
로 바꾸면 상한이 없어진다.

```kotlin
val exec = Executors.newVirtualThreadPerTaskExecutor()
withContext(exec.asCoroutineDispatcher()) { /* 블로킹 호출도 안전 */ }
```

참고로 **같은 블로킹 `Thread.sleep` 을 자바 가상 스레드는 50,000 개 돌려 5.29 초**에 끝냈다(3 절).
코루틴이 8 개에서 막히던 그 호출이다. 둘은 경쟁 관계가 아니라 아래위로 겹치는 관계다.

그리고 JEP 491 이후에도 자바 쪽에 핀이 남은 자리가 있다 — 네이티브 메서드나 FFM API 를 거쳐
네이티브 코드가 자바로 되돌아와 블로킹하는 경우다. 이건 `jdk.VirtualThreadPinned` JFR 이벤트로
잡는다.[^jep491]

---

## 8. 숫자로 안 잡히는 차이

### 함수에 색이 있는가

`suspend` 는 전염된다. suspend 함수는 suspend 함수에서만 부를 수 있고, 그래서 호출 사슬을 따라
위로 번진다.[^kotlin-basics] 가상 스레드엔 이 표시가 없다 — 기존 `Thread` API 그대로다. JEP 444 가
문법적 코루틴을 거부한 이유가 정확히 이것이었다. 스레드용 API 와 코루틴용 API 로 "세상이 쪼개지는
것"(*split the world*)을 피하겠다는 것.[^jep444-alt]

뒤집으면, 색이 있어서 **중단 가능한 지점이 소스에 보인다.** 가상 스레드에선 어떤 호출이 언마운트를
일으키는지 코드만 봐선 모른다. 취향이 아니라 트레이드오프다.

### 취소

코루틴 쪽은 `Job` 핸들로 취소하고, 부모가 취소되면 자식으로 전파되며, 취소된 코루틴은 다음
검사 지점에서 `CancellationException` 을 던진다.[^kotlin-cancel] 협조적 취소이고, 구조적 동시성이
라이브러리 API 로 **2018 년 10 월 1.0** 부터 안정 상태다.[^coroutines-10]

자바 쪽 대응물인 **JEP 505 Structured Concurrency 는 JDK 25 에서도 여전히 프리뷰**다 — 그것도
다섯 번째 프리뷰.[^jep505] 25 를 쓰더라도 `--enable-preview` 가 필요하고 API 는 아직 움직인다.
2026 년 9 월 기준으로 이 항목은 코루틴 쪽이 명확히 앞서 있다.

### 컨텍스트 전달

코루틴은 `CoroutineContext` 로 디스패처·Job·기타 요소를 하나로 들고 다닌다.[^kotlin-ctx] 자바
쪽은 `ThreadLocal` 이 있었지만 가상 스레드가 수백만 개면 비용 구조가 달라진다. 그 답인 **JEP 506
Scoped Values 는 JDK 25 에서 정식 기능이 됐다.**[^jep506] 이쪽은 25 에서 격차가 메워진 항목이다.

---

## 9. 정리

| | 가상 스레드 | 코루틴 |
|---|---|---|
| 상태 없는 대량 대기 | 잘 된다 | **메모리 1.7–1.8 배 유리** |
| 중단을 넘는 상태가 많음 | **메모리 1.85 배 유리** | 레벨마다 객체 |
| 블로킹 호출 | 그냥 된다 | 디스패처 상한에 막힘 (가상 스레드 executor 로 해결) |
| 함수 색깔 | 없음 | `suspend` 전염 |
| 구조적 동시성 | JEP 505, 25 에서도 **프리뷰** | 1.0 (2018) 이후 안정 |
| 스코프 값 | **JEP 506, 25 에서 정식** | `CoroutineContext` |

한 줄로 줄이면 — **"코루틴이 가볍다" 는 문장의 유효 범위는 생각보다 좁다.** 그 문장이 참인 건
살아남을 상태가 적을 때이고, 그 조건이 깨지면 실측에서 역전된다. 그리고 그 문장이 비교하던
상대(플랫폼 스레드)는 JDK 21 이후 자바가 더 이상 강요하지 않는 선택지다.

### 이 숫자의 한계

명시해 둔다. 기계 한 대, 구성당 3 회, 워크로드는 전부 **잠자기**다. 실제 I/O 도, 연산도, 경합도
없다. `max RSS` 는 GC 타이밍에 흔들리는 지표라 100 만 개 구간의 범위가 넓게 잡혔다(가상 스레드
930–1046 MiB). 처리량(throughput) 은 아예 재지 않았다. 중립적인 제 3 자 벤치마크로 검증한 것도
아니다.

그러니 "코루틴이 몇 배 빠르다/느리다" 로 읽지 말고, **역전이 일어나는 조건이 존재하며 그 조건이
무엇인지** 로 읽는 게 맞다. 그 부분은 바이트코드와 KEEP 문서로 뒷받침된다. 배수는 당신 워크로드에서
다시 재야 한다.

---

## References

[^jep444-alt]: JEP 444: Virtual Threads — "Alternatives" 절. <https://openjdk.org/jeps/444>
[^jep444-mem]: JEP 444: Virtual Threads — "Memory use and interaction with garbage collection" 절. <https://openjdk.org/jeps/444>
[^jep491]: JEP 491: Synchronize Virtual Threads without Pinning (JDK 24) — "Diagnosing remaining cases of pinning" 절. <https://openjdk.org/jeps/491>
[^jep491-choose]: JEP 491 — "Choosing between `synchronized` and `java.util.concurrent.locks`" 절. <https://openjdk.org/jeps/491>
[^jep505]: JEP 505: Structured Concurrency (Fifth Preview), Release 25. <https://openjdk.org/jeps/505>
[^jep506]: JEP 506: Scoped Values, Release 25. <https://openjdk.org/jeps/506>
[^keep164]: Kotlin KEEP-0164, "Compiling suspending functions" 절. <https://github.com/Kotlin/KEEP/blob/main/proposals/KEEP-0164-coroutines.md>
[^kotlin-compare]: Kotlin 공식 문서, Coroutines basics — "Comparing coroutines and JVM threads". <https://kotlinlang.org/docs/coroutines-basics.html>
[^kotlin-basics]: Kotlin 공식 문서, Coroutines basics — "Suspending functions". <https://kotlinlang.org/docs/coroutines-basics.html>
[^kotlin-cancel]: Kotlin 공식 문서, Cancellation and timeouts. <https://kotlinlang.org/docs/cancellation-and-timeouts.html>
[^kotlin-ctx]: Kotlin 공식 문서, Coroutine context and dispatchers. <https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html>
[^coroutines-10]: kotlinx.coroutines 1.0.0 릴리스, 2018-10-29. <https://github.com/Kotlin/kotlinx.coroutines/releases/tag/1.0.0>

측정 환경: macOS x86_64 8 코어 · OpenJDK 25.0.2 (Homebrew) · kotlinx-coroutines-core 1.11.0 ·
kotlinc 2.4.10 (`-jvm-target 25`) · `/usr/bin/time -l` · 구성당 3 회.
