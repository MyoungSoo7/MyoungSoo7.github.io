---
layout: post
title: "자바와 코틀린의 동시성 차이 — 스레드는 둘 다 싸졌는데, 취소는 왜 아직 다른가"
date: 2026-09-02 22:43:46 +0900
categories: [Java, Kotlin]
tags: [java, kotlin, coroutines, virtual-threads, cancellation, structured-concurrency, jep-505, jep-491, scoped-values, interrupt]
---

이 블로그에는 가상 스레드와 코루틴을 비교한 글이 이미 여러 개 있다. 거기서 든 근거의 상당수는 "코루틴이 훨씬 가볍다", "자바는 `synchronized` 에서 핀이 걸린다" 였다. **그 근거들은 지금 대부분 유효하지 않다.**

핀은 JDK 24 에서 없어졌고[^jep491], `ScopedValue` 는 JDK 25 에서 정식이 됐다[^jep506]. 그러면 차이가 사라졌나. 아니다. 차이는 **다른 자리로 옮겨갔다.** 남은 자리는 무게가 아니라 **취소(cancellation)** 다.

이 글은 그 한 축만 판다.

---

## 1. 2026년 9월 기준 좌표

| 기능 | 자바 | 코틀린 |
|---|---|---|
| 경량 실행 단위 | Virtual Threads — **정식**, JDK 21[^jep444] | Coroutines — **정식**, 1.3 / 2018-10[^kt13] |
| `synchronized` 핀 | **해소**, JDK 24[^jep491] | 해당 없음 |
| 스코프(구조적 동시성) | **아직 프리뷰**, JDK 27 기준 7차[^jep533] | 정식, 언어 관용구 |
| 컨텍스트 전파 | `ScopedValue` — 정식, JDK 25[^jep506] | `CoroutineContext` — 정식 |
| 취소 메커니즘 | `Thread.interrupt()` — 1996년의 그것 | `Job` 트리 + `CancellationException` |

읽을 곳은 3행과 5행이다.

---

## 2. 이미 좁혀진 차이 — 무게와 핀

JEP 491 의 요약은 이렇게 적혀 있다.

> "This will eliminate nearly all cases of virtual threads being pinned to platform threads, which severely restricts the number of virtual threads available to handle an application's workload."[^jep491]
> (가상 스레드가 플랫폼 스레드에 고정되는 거의 모든 경우를 제거한다.)

`nearly all` 이지 `all` 이 아니라는 점은 짚어둘 만하지만, "코틀린을 써야 하는 이유가 핀" 이라는 논거는 JDK 24 이상에서는 성립하지 않는다. 무게 역시 마찬가지다. 둘 다 힙에 연속체(continuation)를 얹는 같은 계열의 물건이다.

그래서 여기서 비교를 멈추면 "이제 거의 같다" 는 결론이 나온다. 틀린 결론이다.

---

## 3. 남은 차이의 진짜 자리 — 취소 상태가 어디에 사는가

두 언어의 취소는 **저장되는 위치가 다르다.**

자바의 취소 상태는 **스레드에 달린 불리언 플래그** 하나다. `Thread.interrupt()` 의 명세는 여러 경우를 나열한 뒤 이렇게 끝난다.

> "If none of the previous conditions hold then this thread's interrupt status will be set."[^thread]
> (앞의 어느 조건에도 해당하지 않으면, 이 스레드의 인터럽트 상태가 설정된다.)

즉 기본 동작은 **플래그를 켜는 것뿐**이다. 그리고 그 플래그는 읽으면 지워진다.

> "The *interrupted status* of the thread is cleared by this method."[^thread]
> (이 메서드는 스레드의 인터럽트 상태를 지운다. — `Thread.interrupted()`)

플래그가 스레드에 있고, 누군가 읽으면 사라진다. `catch (InterruptedException e) { log.warn(...); }` 한 줄이 취소를 통째로 삼키는 고전적 사고가 여기서 나온다.

코틀린의 취소 상태는 **작업 트리의 노드**에 산다.

> "According to this principle, coroutines form a tree hierarchy of parent and child tasks with linked lifecycles."[^ktsc]
> "If the parent coroutine fails or gets canceled, all its child coroutines are recursively canceled too."[^ktsc]
> (부모가 실패하거나 취소되면 모든 자식 코루틴이 재귀적으로 함께 취소된다.)

그래서 코틀린에서 취소를 삼키는 것은 **한 줄로는 안 된다.** 문서가 따로 경고할 만큼 의도적이어야 한다.

> "Catching `CancellationException` can break the cancellation propagation. If you must catch it, rethrow it."[^ktcancel]

한쪽은 실수로 삼켜지고, 한쪽은 삼키려면 작정해야 한다. 이게 남은 차이의 핵심이다.

---

## 4. 흔한 오해 하나 — "코틀린은 취소가 자동이다"

아니다. **둘 다 협조적(cooperative)이다.**

> "In Kotlin, coroutine cancellation is cooperative. Coroutines react to cancellation only when they cooperate by suspending or checking for cancellation explicitly."[^ktcancel]

서스펜션 포인트가 없는 계산 루프는 코틀린에서도 취소를 무시한다.

```kotlin
val sum = async(Dispatchers.Default) {
    var acc = 0L
    for (i in 0 until 50_000_000_000L) acc += i   // 서스펜션 포인트 없음 → cancel() 무시
    acc
}
```

```java
Subtask<Long> sum = scope.fork(() -> {
    long acc = 0;
    for (long i = 0; i < 50_000_000_000L; i++) acc += i;  // 인터럽트 확인 없음 → 무시
    return acc;
});
```

둘 다 뚫린다. 고치는 법도 대칭이다 — 코틀린은 `ensureActive()` 나 `yield()`, 자바는 `Thread.interrupted()` 확인.

**그럼 뭐가 다른가.** 체크포인트가 생기는 조건이 다르다.

| | 체크포인트가 되는 것 | 안 되는 것 |
|---|---|---|
| 코틀린 | 모든 `suspend` 호출 | 순수 계산 루프 |
| 자바 | **인터럽트 가능한** 블로킹 호출만 | 계산 루프 + **인터럽트 불가능한 블로킹 호출** |

자바 쪽 마지막 칸이 문제다. JEP 505 가 직접 인정한다.

> "Subtasks that do not respond to interrupts because, e.g., they block on methods that are not interruptible, may delay the closing of a scope indefinitely."[^jep505]
> (인터럽트 불가능한 메서드에서 블로킹되는 등의 이유로 인터럽트에 반응하지 않는 서브태스크는 스코프 닫기를 무한정 지연시킬 수 있다.)

코틀린에서 I/O 를 하려면 대개 `suspend` 함수를 통과한다 — 취소 체크포인트가 **덤으로** 생긴다. 자바에서 블로킹 I/O 는 그것이 인터럽트에 반응하도록 만들어졌을 때만 체크포인트가 된다. 그렇지 않으면 `scope.close()` 는 **기다린다.**

> "Execution cannot continue beyond the close method until the interrupted threads finish."[^jep505]

---

## 5. 자바가 "취소를 바꾸지 않겠다" 고 명시한 문장

구조적 동시성이 이 문제를 풀어줄 거라고 기대할 수 있다. JEP 505 의 Non-Goals 는 그 기대를 직접 닫는다.

> "It is not a goal to replace the existing thread interruption mechanism with a new thread cancellation mechanism. We might propose to do so in the future."[^jep505]
> (기존 스레드 인터럽트 메커니즘을 새로운 취소 메커니즘으로 대체하는 것은 목표가 아니다. 향후 제안할 수는 있다.)

`StructuredTaskScope` 는 취소를 **더 잘 조직**한다. 부모가 인터럽트되면 자식이 자동으로 취소되고, `close()` 가 정리를 보장한다. 그건 진짜 개선이다. 하지만 그 아래에서 실제로 흐르는 신호는 여전히 1996년의 인터럽트 플래그다. **자바는 인터럽트 위에 구조를 얹었고, 코틀린은 구조 자체를 취소의 단위로 만들었다.**

---

## 6. 스코프의 성숙도 — 프리뷰 7차

이건 설계 취향이 아니라 날짜의 문제다. JEP 533 이 자기 이력을 이렇게 적는다 — 인큐베이터 JDK 19·20, 프리뷰 JDK 21·22·23·24·25·26, 그리고 JDK 27 에서 **7차 프리뷰**[^jep533].

| JDK | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 |
|---|---|---|---|---|---|---|---|---|---|
| 상태 | 인큐베이터 | 인큐베이터 | 프리뷰 | 프리뷰 | 프리뷰 | 프리뷰 | 프리뷰 | 프리뷰 | 프리뷰 |

JDK 25 에서는 공개 생성자가 정적 팩토리로 바뀌었고[^jep505], JDK 26 에서는 `Joiner` 에 `onTimeout()` 이 추가되고 `allSuccessfulOrThrow()` 의 반환 타입이 바뀌었다[^jep525]. **API 가 아직 움직이고 있다.**

코틀린의 같은 기능은 2018년 10월에 안정화됐다[^kt13]. 여덟 해 차이다. "쓸 수 있느냐" 가 아니라 "`--enable-preview` 없이 프로덕션에 넣을 수 있느냐" 를 묻는다면, 지금 답은 한쪽만 예다.

---

## 7. 컨텍스트 전파 — 왜 자바는 두 개고 코틀린은 하나인가

`ScopedValue` 는 JDK 25 에서 정식이 됐다.

> "Introduce scoped values, which enable a method to share immutable data both with its callees within a thread, and with child threads."[^jep506]

좋은 물건이다. `ThreadLocal` 보다 싸고 안전하다. 그런데 **데이터만 흐른다.**

코틀린의 `CoroutineContext` 는 디스패처와 이름뿐 아니라 **`Job` 자체**를 담는다. 그래서 컨텍스트를 상속한다는 말이 곧 취소 핸들을 상속한다는 말이다. 자바는 이걸 두 개의 메커니즘(`ScopedValue` + 인터럽트)으로 나눠 갖고 있고, 코틀린은 하나로 갖고 있다.

```kotlin
coroutineScope {                        // 컨텍스트 = 데이터 + 취소 핸들
    val user  = async { findUser(id) }
    val order = async { fetchOrder(id) }
    Response(user.await(), order.await())
}
```

```java
try (var scope = StructuredTaskScope.open()) {   // 취소는 여기
    Subtask<User>  user  = scope.fork(() -> findUser(id));
    Subtask<Order> order = scope.fork(() -> fetchOrder(id));
    scope.join();
    return new Response(user.get(), order.get());
}                                                 // 데이터는 ScopedValue 로 따로
```

모양은 놀랍도록 비슷하다. 나뉜 것은 밑이다.

---

## 8. 코틀린이 치르는 값 — 체크포인트는 공짜가 아니다

여기서 코틀린 편만 들면 정직하지 않다. 4장에서 "코틀린은 `suspend` 호출마다 체크포인트가 덤으로 생긴다" 고 썼다. **그 덤의 청구서가 함수 색깔(function coloring)이다.**

`suspend` 를 붙이면 그 함수를 부르는 함수도 `suspend` 여야 한다. 취소가 공짜로 촘촘해지는 이유는 컴파일러가 호출 지점마다 상태 기계를 끼워 넣기 때문이고, 그 대가로 호출 그래프 전체가 물든다. 자바에는 이 세금이 없다 — 대신 체크포인트도 없다.

같은 트레이드오프의 양면이다. 어느 쪽이 이득인지는 코드베이스가 정한다.

`NonCancellable` 이 존재한다는 사실도 코틀린 모델이 완전하지 않다는 증거다. 정리 코드가 취소 후에도 끝까지 돌아야 하면 트리 밖으로 잠깐 빠져나와야 하고, 문서는 그걸 남용하면 "구조적 동시성을 깨뜨린다" 고 경고한다[^ktcancel].

---

## 9. 그래서 지금 고른다면

- **자바 25/26 에서 새로 시작한다** — 가상 스레드는 그냥 켠다. 구조적 동시성은 프리뷰라는 걸 알고 쓴다. 그리고 **인터럽트에 반응하지 않는 블로킹 호출이 코드에 몇 개나 있는지 세어 본다.** 그 개수가 이 글의 위험을 그대로 나타낸다.
- **취소·타임아웃·부분 실패가 도메인의 중심이다** — 코틀린 쪽이 여전히 앞선다. 스트리밍(`Flow`/`Channel`)까지 필요하면 더 그렇다.
- **이미 자바다** — 언어를 바꿀 이유는 이 글 어디에도 없다. 대신 취소 경로에 **명시적 체크포인트를 손으로 넣는다.** 코틀린이 컴파일러에게 시키는 일을 사람이 하는 것뿐이다.

---

## 정리

무게는 수렴했다. 핀은 사라졌다. 남은 차이는 한 문장이다.

**자바는 취소를 스레드의 플래그로 다루고, 코틀린은 작업 트리의 상태로 다룬다.** 그리고 자바는 그걸 바꾸지 않겠다고 JEP 에 적어 뒀다.

---

## 이 글의 한계

- 성능 수치를 넣지 않았다. 이 글의 주장은 벤치마크가 아니라 명세의 문장에 기대고 있다.
- JDK 26·27 항목은 JEP 문서 기준이며, 릴리스 시점의 최종 API 는 또 바뀔 수 있다. 프리뷰라는 게 그런 뜻이다.
- 안드로이드는 다루지 않았다. 거기선 애초에 선택지가 하나다.

---

## References

[^jep444]: JEP 444: Virtual Threads — Status: Closed/Delivered, Release 21. <https://openjdk.org/jeps/444>
[^jep491]: JEP 491: Synchronize Virtual Threads without Pinning — Status: Closed/Delivered, **Release 24**. "This will eliminate nearly all cases of virtual threads being pinned to platform threads…" <https://openjdk.org/jeps/491>
[^jep505]: JEP 505: Structured Concurrency (Fifth Preview) — Release 25. Non-Goals: "It is not a goal to replace the existing thread interruption mechanism with a new thread cancellation mechanism." <https://openjdk.org/jeps/505>
[^jep525]: JEP 525: Structured Concurrency (Sixth Preview) — Release 26. <https://openjdk.org/jeps/525>
[^jep533]: JEP 533: Structured Concurrency (Seventh Preview) — Release 27. 인큐베이터·프리뷰 이력 전체가 이 문서의 History 에 정리돼 있다. <https://openjdk.org/jeps/533>
[^jep506]: JEP 506: Scoped Values — Status: Closed/Delivered, Release 25. <https://openjdk.org/jeps/506>
[^thread]: `java.lang.Thread`, Java SE 25 API Specification — `interrupt()`, `interrupted()`. <https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html>
[^ktcancel]: Kotlin Documentation — Coroutine cancellation. <https://kotlinlang.org/docs/coroutines-cancellation.html>
[^ktsc]: Kotlin Documentation — Coroutine basics / structured concurrency. <https://kotlinlang.org/docs/coroutines-basics.html>
[^kt13]: JetBrains, "Kotlin 1.3 Released with Coroutines, Kotlin/Native Beta, and more", 2018-10. <https://blog.jetbrains.com/kotlin/2018/10/kotlin-1-3/>
