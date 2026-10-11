---
layout: post
title: "코틀린 코루틴과 Flow — suspend, 구조적 동시성, Dispatcher, 취소, 예외, 그리고 자바 가상 스레드와의 비교"
date: 2026-10-12 00:27:42 +0900
categories: [kotlin]
tags: [kotlin, coroutines, flow, structured-concurrency, dispatchers, cancellation, virtual-threads, kotlinx-coroutines]
---

자바·코틀린 20편 시리즈의 **코틀린 7번째 글(K7)** 이다. 코틀린 코루틴을 여섯 덩어리로 나눈다. (1) `suspend` 함수와 코루틴 빌더, (2) 구조적 동시성, (3) Dispatcher 와 컨텍스트, (4) 취소와 타임아웃, (5) 예외 전파와 Supervisor, (6) `Flow`. 마지막에 자바 가상 스레드와 무엇이 같고 무엇이 다른지 표로 정리한다.

자바 쪽 짝 글은 [J7 — 동시성: Thread → ExecutorService → CompletableFuture → 가상 스레드](https://myoungsoo7.github.io/2026/10/12/java-concurrency-thread-to-virtual-threads/) 다. 스프링에서 `suspend` 컨트롤러와 `Flow` 를 쓰는 법은 [K10 — 코틀린 × 스프링부트](https://myoungsoo7.github.io/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/) 에서 다룬다. 예전에 쓴 [Kotlin Coroutine 완전 가이드](https://myoungsoo7.github.io/2026/06/13/kotlin-coroutine-usage-suspend-flow-structured-concurrency/) 와 [자바와 코틀린의 동시성 차이 — 취소](https://myoungsoo7.github.io/2026/09/02/java-kotlin-cancellation-is-the-real-difference/) 도 함께 보면 좋다.

> 코루틴 API 는 언어 자체가 아니라 `kotlinx.coroutines` 라이브러리에 있다. 언어가 제공하는 것은 `suspend` 키워드이고, `launch`/`async`/`Flow` 는 라이브러리 함수다.

---

## 1. suspend 함수와 코루틴 빌더

### 1.1 무엇인가

공식 문서: "코루틴의 가장 기본 구성 요소는 **suspending function** 이다. 실행 중인 작업을 멈췄다가 나중에 재개할 수 있게 하며, 코드 구조에는 영향을 주지 않는다." 그리고 제약: "suspend 함수는 **다른 suspend 함수에서만** 호출할 수 있다." ([Coroutines basics](https://kotlinlang.org/docs/coroutines-basics.html))

코루틴은 빌더로 시작한다.

| 빌더 | 역할 (공식 문서 요지) | 반환 |
|---|---|---|
| `CoroutineScope.launch` | 결과가 필요 없거나 기다리지 않을 작업을 스코프 안에서 시작 | `Job` |
| `CoroutineScope.async` | 동시 계산을 시작, `await()` 로 결과를 기다림 | `Deferred<T>` |
| `coroutineScope { }` | 하위 트리의 루트를 만들고, 블록과 그 안에서 띄운 코루틴이 **모두 끝날 때까지** suspend | 블록 결과 |
| `runBlocking { }` | 스코프를 만들고 그 안의 코루틴이 끝날 때까지 **현재 스레드를 블록** | 블록 결과 |

### 1.2 코드

```kotlin
import kotlinx.coroutines.*

suspend fun fetchUser(id: Long): User {
    delay(100)                 // 스레드를 막지 않고 코루틴만 멈춘다
    return User(id, "user-$id")
}

data class User(val id: Long, val name: String)

fun main() = runBlocking {     // main 은 suspend 가 아니므로 다리 역할
    val user = fetchUser(1)
    println(user)
}
```

### 1.3 순차가 기본, 동시성은 명시적으로

공식 문서([Composing suspending functions](https://kotlinlang.org/docs/composing-suspending-functions.html)): "코루틴 안의 코드도 일반 코드처럼 **기본적으로 순차적**이다." 그리고 "코루틴의 동시성은 **항상 명시적**이다."

```kotlin
suspend fun loadProfile(id: Long): Profile = coroutineScope {
    val user = async { fetchUser(id) }          // 동시 시작
    val orders = async { fetchOrders(id) }      // 동시 시작
    Profile(user.await(), orders.await())
}
```

`async` 를 쓰지 않고 `fetchUser(id)` 다음 줄에 `fetchOrders(id)` 를 쓰면 순서대로 실행된다. 자바의 `CompletableFuture` 처럼 "호출하면 이미 비동기로 돈다" 가 아니다. 이 점이 코루틴 코드가 동기 코드처럼 읽히는 이유이자, 동시 실행을 원할 때 `async` 를 빠뜨리는 실수의 원인이기도 하다.

### 1.4 함정 — runBlocking

[`runBlocking` API 문서](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-blocking.html) 의 경고:

- 용도는 블로킹 코드와 suspend 라이브러리를 잇는 것 — `main` 함수, 테스트, suspend 함수를 불러야 하는 non-suspend 콜백.
- **suspend 함수 안에서 `runBlocking` 을 부르지 말 것.** 불필요할 뿐 아니라 스레드를 블록해 **스레드 기아(starvation)** 를 일으킬 수 있고, 현재 코루틴 컨텍스트도 무시된다.

```kotlin
// 나쁜 예
suspend fun loadConfiguration() {
    val data = runBlocking { fetchConfigurationData() }   // 하지 말 것
}

// 좋은 예
suspend fun loadConfiguration() {
    val data = fetchConfigurationData()
}
```

스프링 MVC 컨트롤러 안에서 `runBlocking` 으로 suspend 함수를 감싸는 코드가 실무에서 자주 보인다. 스프링은 컨트롤러 메서드를 직접 `suspend` 로 선언하는 것을 지원하므로(K10) 그쪽이 맞다.

---

## 2. 구조적 동시성 (Structured Concurrency)

### 2.1 무엇인가

공식 문서: "이 원칙에 따라 코루틴은 **수명이 연결된 부모-자식 트리**를 이룬다." 그리고 "부모가 실패하거나 취소되면 모든 자식이 재귀적으로 취소된다. 이렇게 연결해 두면 취소와 오류 처리가 예측 가능하고 안전해진다." 또한 "새 코루틴은 수명을 정의·관리하는 `CoroutineScope` 안에서만 띄울 수 있다." ([Coroutines basics](https://kotlinlang.org/docs/coroutines-basics.html))

[Coroutine context and dispatchers](https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html) 는 두 규칙을 더 적는다.

- 다른 코루틴의 스코프에서 띄운 코루틴은 컨텍스트를 상속하고, 그 `Job` 은 부모 `Job` 의 **자식**이 된다.
- "부모 코루틴은 항상 모든 자식의 완료를 기다린다. 부모가 자식을 직접 추적하거나 `join` 할 필요가 없다."

### 2.2 코드 — 실패 시 형제 취소

```kotlin
suspend fun concurrentSum(): Int = coroutineScope {
    val one = async { doSomethingUsefulOne() }
    val two = async { doSomethingUsefulTwo() }
    one.await() + two.await()
}
```

공식 문서: "`concurrentSum` 안에서 예외가 나면 그 스코프에서 띄운 **모든 코루틴이 취소된다**." `one` 이 실패하면 `two` 는 자동 취소되고, 예외는 `concurrentSum` 호출자에게 전파된다. 남은 작업이 백그라운드에서 계속 도는 일이 없다.

### 2.3 실무 사용사례 — 팬아웃 API 집계

```kotlin
suspend fun dashboard(userId: Long): Dashboard = coroutineScope {
    val profile = async { profileClient.get(userId) }
    val orders = async { orderClient.recent(userId) }
    val points = async { pointClient.balance(userId) }
    Dashboard(profile.await(), orders.await(), points.await())
}
```

세 호출이 동시에 나가고, 하나라도 실패하면 나머지는 취소된 뒤 예외가 올라간다. 요청이 취소되면(클라이언트 연결 종료 등으로 상위 코루틴이 취소되면) 세 호출 모두 함께 취소된다.

### 2.4 함정 — GlobalScope 와 "async 스타일 함수"

공식 문서는 `GlobalScope.async { }` 를 반환하는 `xxxAsync()` 함수 스타일을 **강하게 비권장**한다. `@OptIn(DelicateCoroutinesApi::class)` 가 필요할 정도다. 이유: `val one = somethingAsync()` 와 `one.await()` 사이에서 로직 오류로 예외가 나 호출한 쪽이 중단돼도, 그 작업은 **백그라운드에서 계속 돈다**. "구조적 동시성에서는 이 문제가 생기지 않는다."

규칙으로 정리하면:

- 함수가 동시 작업을 띄워야 하면 `suspend fun` + `coroutineScope { }` 로 만든다.
- 함수가 스코프를 벗어나 오래 사는 작업을 띄워야 하면, 그 수명을 소유한 객체(서비스 빈 등)가 `CoroutineScope` 를 들고 종료 시 `cancel()` 한다. `GlobalScope` 는 쓰지 않는다.

---

## 3. Dispatcher 와 CoroutineContext

### 3.1 무엇인가

공식 문서: "코루틴 디스패처는 코루틴이 실행에 쓰는 스레드 또는 스레드 풀을 정한다." "컨텍스트에 디스패처가 없으면 빌더는 `Dispatchers.Default` 를 쓴다." 그리고 "코루틴은 특정 스레드에 묶이지 않는다. 한 스레드에서 멈췄다가 다른 스레드에서 재개할 수 있다." ([Coroutines basics](https://kotlinlang.org/docs/coroutines-basics.html))

| Dispatcher | 용도와 특성 (공식 API 문서 기준) |
|---|---|
| `Dispatchers.Default` | 디스패처가 지정되지 않으면 쓰는 기본값. 공유 스레드 풀. 최대 스레드 수는 기본적으로 **CPU 코어 수, 최소 2** ([API](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-default.html)) |
| `Dispatchers.IO` | **블로킹 IO 작업을 떠넘기는** 공유 풀. 병렬 IO 스레드 수는 `kotlinx.coroutines.io.parallelism` 시스템 프로퍼티로 제한되며 기본값은 **64 와 코어 수 중 큰 값**. `Default` 와 스레드를 공유 ([API](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)) |
| `Dispatchers.Main` | UI 애플리케이션용 (`MainScope()` 가 기본으로 사용) |
| `Dispatchers.Unconfined` | 첫 suspend 지점까지만 호출 스레드에서 돌고, 이후엔 재개시킨 함수가 정한 스레드에서 재개. "일반 코드에서는 쓰지 말 것" |

### 3.2 코드 — withContext 로 블로킹 호출 격리

```kotlin
suspend fun readReport(path: Path): String =
    withContext(Dispatchers.IO) {
        Files.readString(path)          // 블로킹 API
    }
```

`withContext` 는 새 컨텍스트로 블록을 실행하고 끝나면 원래 디스패처로 돌아온다. 공식 문서는 디스패처가 다르면 "추가 디스패치가 필요하다" 고 적는다. 다만 `Dispatchers.IO` API 문서에 따르면 `Default` 에서 `IO` 로 `withContext` 할 때는 스레드를 공유하므로 **보통 실제 스레드 전환이 일어나지 않도록** best-effort 로 구현돼 있다.

### 3.3 실무 사용사례 — 리소스별 병렬도 제한

`Dispatchers.IO` 의 `limitedParallelism` 뷰는 IO 의 64 제한에 묶이지 않는 **탄력적(elastic)** 뷰다. 공식 문서 예제:

```kotlin
val mysqlDispatcher = Dispatchers.IO.limitedParallelism(100)
val mongoDispatcher = Dispatchers.IO.limitedParallelism(60)
```

최대 부하에서는 `64 + 100 + 60` 개 스레드까지 갈 수 있지만, 평상시에는 소수 스레드를 셋이 공유한다. JDBC 커넥션 풀 크기에 맞춘 디스패처를 따로 두면 "DB 커넥션은 10개인데 블로킹 호출 64개가 동시에 커넥션을 기다리는" 상황을 디스패처 수준에서 제한할 수 있다.

```kotlin
class ReportRepository(private val jdbc: JdbcTemplate) {
    private val dbDispatcher = Dispatchers.IO.limitedParallelism(10)  // 커넥션 풀 크기와 맞춤

    suspend fun findAll(): List<Report> = withContext(dbDispatcher) {
        jdbc.query("select id, title from report") { rs, _ ->
            Report(rs.getLong("id"), rs.getString("title"))
        }
    }
}

data class Report(val id: Long, val title: String)
```

### 3.4 자바 Executor 와 잇기

`kotlinx.coroutines` 는 `ExecutorService.asCoroutineDispatcher()`/`Executor.asCoroutineDispatcher()` 확장을 제공한다 ([API](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/as-coroutine-dispatcher.html)). 기존 자바 스레드 풀을 그대로 디스패처로 쓸 수 있다. 실행기가 거부(`RejectedExecutionException`)하면 해당 Job 은 취소되고 정리 작업은 `Dispatchers.IO` 로 넘어간다고 문서에 적혀 있다.

### 3.5 함정

1. **`Dispatchers.Default` 에서 블로킹 호출.** Default 는 코어 수만큼의 스레드뿐이다. JDBC·파일 IO 같은 블로킹 호출을 그대로 부르면 CPU 작업용 스레드가 모두 묶인다. 블로킹은 `withContext(Dispatchers.IO)` 로 감싼다.
2. **`newSingleThreadContext` 누수.** 공식 문서: "전용 스레드는 매우 비싼 자원이다. 필요 없어지면 `close` 로 해제하거나, 최상위 변수에 두고 재사용해야 한다."
3. **`Unconfined` 를 성능 트릭으로 쓰기.** 재개 스레드가 예측 불가능해진다. 문서가 일반 코드에서 쓰지 말라고 명시한다.

---

## 4. 취소와 타임아웃

### 4.1 무엇인가 — 취소는 협조적이다

공식 문서: "코틀린에서 코루틴 취소는 **협조적(cooperative)** 이다. 코루틴은 suspend 하거나 명시적으로 취소를 확인할 때만 취소에 반응한다." 취소된 코루틴은 다음 확인 지점에서 `CancellationException` 을 던지고, `delay()` 같은 `kotlinx.coroutines` 의 suspend 함수는 suspend 할 때 취소를 확인한다 ([Cancellation and timeouts](https://kotlinlang.org/docs/coroutines-cancellation.html)).

### 4.2 코드 — CPU 루프에서 취소 확인

```kotlin
suspend fun checksum(chunks: List<ByteArray>): Long = coroutineScope {
    var sum = 0L
    for (chunk in chunks) {
        ensureActive()                // 취소됐으면 CancellationException
        sum += chunk.sumOf { it.toLong() }
    }
    sum
}
```

공식 문서의 세 도구:

| 도구 | 동작 |
|---|---|
| `isActive` | 취소되면 `false` |
| `ensureActive()` | 취소되면 `CancellationException` 을 던짐 |
| `yield()` | 잠깐 suspend 하면서 취소를 확인하고, 스레드를 양보해 다른 코루틴이 돌 기회를 줌 |

### 4.3 타임아웃

```kotlin
val result: String? = withTimeoutOrNull(500) {   // 500ms
    slowRemoteCall()
}
if (result == null) log.warn("remote call timed out")
```

`withTimeoutOrNull` 은 시간 초과 시 `null` 을 반환한다. `withTimeout` 은 예외를 던진다.

### 4.4 정리 코드 — NonCancellable

```kotlin
try {
    processStream()
} finally {
    withContext(NonCancellable) {
        connection.closeGracefully()     // suspend 함수여도 끝까지 실행
    }
}
```

공식 문서: `NonCancellable` 은 suspend `close()` 같은 정리 작업을 취소와 무관하게 끝내야 할 때 쓴다. 단, "`launch`·`async` 같은 다른 빌더와 함께 쓰지 말 것 — 부모-자식 관계를 끊어 구조적 동시성을 깬다."

### 4.5 함정 — CancellationException 을 삼키기

공식 문서의 가장 중요한 경고: "**`CancellationException` 을 잡으면 취소 전파가 끊길 수 있다.** 꼭 잡아야 한다면 다시 던져라."

```kotlin
// 나쁜 예 — 모든 예외를 잡아 로그만 남김
suspend fun syncOnce() {
    try {
        remote.sync()
    } catch (e: Exception) {          // CancellationException 도 여기 걸린다
        log.error("sync failed", e)
    }
}

// 좋은 예
suspend fun syncOnceSafely() {
    try {
        remote.sync()
    } catch (e: CancellationException) {
        throw e                       // 취소는 그대로 올려 보낸다
    } catch (e: Exception) {
        log.error("sync failed", e)
    }
}
```

`runCatching { }` 도 같은 문제를 갖는다. 내부에서 모든 `Throwable` 을 잡기 때문에 suspend 코드에서 그대로 쓰면 취소를 실패로 오인한다.

---

## 5. 예외 전파와 Supervisor

### 5.1 무엇인가

공식 문서([Coroutine exceptions handling](https://kotlinlang.org/docs/exception-handling.html)):

| 빌더 | 예외 처리 |
|---|---|
| `launch` | 예외를 **자동 전파** (`Thread.uncaughtExceptionHandler` 와 비슷) |
| `async` | 예외를 사용자에게 **노출** — `await()` 에서 받는다 |

- 자식이 `CancellationException` 이 아닌 예외로 실패하면 **그 예외로 부모를 취소**한다. 부모는 나머지 자식을 취소하고, 모든 자식이 끝난 뒤 예외를 처리한다.
- 여러 자식이 실패하면 **첫 번째 예외가 이기고** 나머지는 suppressed 로 붙는다.

### 5.2 CoroutineExceptionHandler 의 한계

공식 문서가 적은 제약:

- 이미 끝난 코루틴이라 **복구는 불가능**하고, 잡히지 않은 예외에만 호출된다.
- 자식 코루틴은 처리를 부모에게 위임하므로 **자식에 단 핸들러는 무시**된다.
- `async` 는 모든 예외를 잡아 `Deferred` 에 담으므로 핸들러가 효과 없다.

즉, `CoroutineExceptionHandler` 는 "최상위 코루틴의 마지막 로깅 지점" 이지 `try/catch` 대체물이 아니다.

### 5.3 SupervisorJob / supervisorScope — 실패를 위로 올리지 않기

- `SupervisorJob`: 자식의 실패가 supervisor 와 형제에게 전파되지 **않는다**.
- `supervisorScope { }`: 취소는 **아래로만** 전파된다. 자식이 자기 예외를 직접 처리해야 하고, 이 스코프 안 자식은 루트 코루틴처럼 `CoroutineExceptionHandler` 를 **사용한다**.

```kotlin
suspend fun notifyAll(users: List<Long>) = supervisorScope {
    users.forEach { id ->
        launch {
            try {
                pushClient.send(id)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                log.warn("push failed for {}", id, e)   // 한 명 실패가 나머지를 취소하지 않는다
            }
        }
    }
}
```

### 5.4 사용사례 정리

| 상황 | 선택 |
|---|---|
| 결과를 모두 합쳐야 함, 하나 실패하면 전체 실패 | `coroutineScope` + `async` |
| 독립 작업 여러 개, 일부 실패 허용 | `supervisorScope` + `launch` (+ 각자 try/catch) |
| 오래 사는 컴포넌트가 백그라운드 작업 소유 | `CoroutineScope(SupervisorJob() + dispatcher)` 를 필드로, 종료 시 `cancel()` |

---

## 6. Flow — 비동기 스트림

### 6.1 무엇인가

공식 문서([Asynchronous Flow](https://kotlinlang.org/docs/coroutines-flow.html)):

- "Flow 는 **비동기로 생산될 수 있는 순차적 값 스트림**이다." 값은 emitter 에서 collector 로, 업스트림에서 다운스트림으로 흐른다.
- "Sequence 처럼 **cold flow 는 지연적**이다. cold flow 빌더 블록은 collector 가 수집하기 전까지 실행되지 않는다. **새 collector 마다 flow 가 새로 실행된다.**"
- `flow { }` 빌더 안에서 `emit()` 으로 값을 내보내고, `collect()` 로 수집한다.
- 중간 연산자(`map` 등)는 업스트림에 연산을 적용해 새 다운스트림 flow 를 반환하며, 이들 역시 cold 다.

### 6.2 코드

```kotlin
import kotlinx.coroutines.flow.*

fun pages(): Flow<String> = flow {
    for (page in 1..3) {
        println("Loading page $page...")
        emit("Page $page")
    }
}

suspend fun main() {
    val f = pages()                 // 아직 아무것도 실행되지 않음
    f.map { it.uppercase() }
        .take(2)                    // 2개 받으면 업스트림 취소
        .collect { println(it) }
}
```

### 6.3 컨텍스트 보존과 flowOn

공식 문서: "기본적으로 cold flow 는 **collector 와 같은 코루틴 컨텍스트**에서 실행된다." 다른 컨텍스트가 필요하면 `flowOn` 을 쓴다. `flowOn` 은 **업스트림의 컨텍스트만** 바꾸고 다운스트림은 호출자 컨텍스트에 둔다.

그리고 제약: "`flow()` 빌더는 자신이 실행되는 컨텍스트와 **같은 컨텍스트에서 emit 해야 한다**. 블록 안에서 다른 코루틴을 띄워 `emit()` 하거나 `withContext()` 로 컨텍스트를 바꿀 수 없다."

```kotlin
// 실패한다 — flow 블록 안에서 withContext 후 emit
val bad = flow {
    withContext(Dispatchers.IO) {
        emit(readLine())
    }
}

// 맞는 방법 — flowOn
val good = flow {
    emit(Files.readString(path))   // 블로킹 읽기
}.flowOn(Dispatchers.IO)           // 업스트림만 IO 에서 실행
```

동시에 여러 코루틴에서 값을 보내야 하면 `channelFlow { }` 를 쓴다. 공식 문서에 따르면 `channelFlow` 는 버퍼가 있는 채널을 쓰며 **기본 버퍼는 64개**이고, `.buffer(n)` 으로 바꾸거나 `.buffer(0)` 으로 없앨 수 있다.

### 6.4 예외 — catch 와 예외 투명성

```kotlin
flow {
    emit("a")
    throw UnsupportedOperationException("error")
}.catch { e ->
    println("Upstream completed with $e")
    emit("Fallback value")
}.collect { println("Got '$it'") }
```

공식 문서의 두 규칙:

1. "`.catch()` 연산자는 **collector 가 던진 예외는 처리하지 않는다.**" `collect { }` 람다는 `catch` 뒤에서 실행되기 때문이다. collect 블록 안 예외는 `collect` 호출부의 try/catch 가 잡아야 한다.
2. flow 빌더 안에서 collector 가 던진 예외를 잡았다면 **다시 던져야 한다**. 그래야 예외 투명성이 유지되고 `collect()` 호출자가 처리할 수 있다.

### 6.5 Hot flow — StateFlow / SharedFlow

`StateFlow` API 문서([StateFlow](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-state-flow/)):

- 하나의 갱신 가능한 값을 가진 **hot flow**. collector 와 독립적으로 존재하며 `value` 로 현재 값을 읽는다. collector 는 정상 완료되지 않는다.
- `Any.equals()` 기반으로 같은 값은 내보내지 않고(`distinctUntilChanged` 와 유사), 빠른 갱신은 **합쳐져(conflate)** 느린 collector 는 최신 값만 받는다.
- `replay = 1`, `onBufferOverflow = DROP_OLDEST` 인 `SharedFlow` 와 동등한 동작이며, 항상 초기값이 있다.

```kotlin
class CounterModel {
    private val _counter = MutableStateFlow(0)
    val counter: StateFlow<Int> = _counter.asStateFlow()

    fun inc() {
        _counter.update { it + 1 }     // 원자적, 동시 사용 안전
    }
}
```

**실무:** 서버에서는 "현재 설정값·피처 플래그·연결 상태" 같이 **최신 상태 하나**만 의미 있는 값을 여러 구독자에게 나눌 때 `StateFlow` 가 맞다. 모든 이벤트를 빠짐없이 전달해야 하는 경우(주문 이벤트 등)에는 conflation 때문에 맞지 않는다.

### 6.6 Flow 함정

1. **cold flow 를 두 번 collect 하면 두 번 실행된다.** DB 조회 flow 를 두 군데서 collect 하면 쿼리도 두 번 나간다.
2. **`flow { }` 안에서 `withContext` 후 emit.** 런타임 예외. `flowOn` 을 쓴다.
3. **`catch` 로 collect 블록 예외를 잡으려는 시도.** 잡히지 않는다.
4. **StateFlow 로 이벤트 버스 만들기.** 같은 값 연속 전송은 무시되고 빠른 갱신은 합쳐진다.

---

## 7. 자바 가상 스레드와의 비교

### 7.1 공통점 — "블로킹처럼 쓰고, 스레드는 싸게"

- 코루틴: 공식 문서는 스레드가 보통 수 MB 메모리를 쓰고 JVM 이 감당하는 스레드는 수천 개 수준인 반면, 코루틴은 특정 스레드에 묶이지 않고 스레드 풀을 공유하므로 **훨씬 가볍다** 고 설명한다 ([Coroutines basics](https://kotlinlang.org/docs/coroutines-basics.html)).
- 가상 스레드: [JEP 444](https://openjdk.org/jeps/444) 로 **JDK 21 에서 정식** 도입. "높은 처리량의 동시성 애플리케이션을 작성·유지·관찰하는 노력을 극적으로 줄이는 경량 스레드." 목표는 thread-per-request 스타일 서버가 하드웨어를 최적으로 쓰도록 하는 것, 기존 `java.lang.Thread` API 코드를 최소 변경으로 옮기는 것.

### 7.2 차이점 표

| 항목 | 코틀린 코루틴 | 자바 가상 스레드 |
|---|---|---|
| 제공 위치 | 언어(`suspend`) + 라이브러리(`kotlinx.coroutines`) | JDK 런타임 (`Thread` API) |
| 함수 색칠 | `suspend` 는 suspend 함수에서만 호출 가능 — 호출 체인 전체에 전파 | 없음. 일반 블로킹 메서드를 그대로 호출 |
| 기존 블로킹 라이브러리 | 그대로 부르면 스레드를 막음 → `Dispatchers.IO` 로 격리 | 그대로 부르면 JDK 가 가상 스레드를 언마운트 (아래 pinning 예외) |
| 구조적 동시성 | `coroutineScope`/`supervisorScope` 로 **라이브러리 차원에서 기본 제공** | 자바 측 구조적 동시성 API 상태는 J7 참고 |
| 취소 | 협조적, 스코프 트리를 따라 **자동 전파** | 인터럽트 기반. 스레드 트리 개념이 기본 API 엔 없음 |
| 풀링 | 디스패처(풀) 위에서 실행 | JEP 444: "가상 스레드는 싸고 많으므로 **절대 풀링하지 말 것**. 작업마다 새로 만든다." |
| 스트림 | `Flow` (cold), `StateFlow`/`SharedFlow` (hot) | 대응물 없음 (Reactor 등 별도 라이브러리) |
| 비자바 플랫폼 | Kotlin/JS·Native 등에서도 동작 | JVM 전용 |

### 7.3 pinning — 가상 스레드 쪽의 함정

JEP 444 시점(JDK 21)에는 가상 스레드가 블로킹 연산 중 캐리어 스레드에서 내려오지 못하는(pinned) 경우가 두 가지였다: `synchronized` 블록·메서드 안, 그리고 네이티브 메서드·외부 함수 실행 중. JEP 는 "pinning 은 애플리케이션을 틀리게 만들지는 않지만 확장성을 해칠 수 있다" 고 쓰고, 자주 쓰는 `synchronized` 를 `ReentrantLock` 으로 바꾸길 권했다.

이후 [JEP 491](https://openjdk.org/jeps/491) 이 **JDK 24** 에 들어가 `synchronized` 에서의 pinning 을 제거했다. 즉 JDK 21 LTS 에서 가상 스레드를 쓰는 서비스와 JDK 25 LTS 에서 쓰는 서비스는 `synchronized` 에 대한 주의 수준이 다르다.

코루틴에는 이 개념이 없다. 대신 "코루틴 안에서 블로킹 호출을 하면 그 디스패처 스레드가 막힌다" 는 더 단순하지만 **개발자가 직접 챙겨야 하는** 규칙이 있다.

### 7.4 어떻게 고를까 (판단 기준)

- **기존 자바 블로킹 코드베이스, 동기 스타일 유지가 목표** → 가상 스레드가 변경 비용이 작다.
- **취소·타임아웃·팬아웃이 많고, 그 전파를 코드 구조로 보장하고 싶다** → 코루틴의 구조적 동시성이 강점.
- **스트림 처리(Flow), 멀티플랫폼** → 코루틴.
- 둘은 배타적이지 않다. 가상 스레드 기반 `Executor` 를 `asCoroutineDispatcher()` 로 감싸 코루틴 디스패처로 쓰는 것도 API 상 가능하다(3.4). 성능 우열은 워크로드마다 다르므로 이 글에서는 수치를 제시하지 않는다.

---

## 8. 체크리스트

- [ ] suspend 함수 안에 `runBlocking` 이 없는가
- [ ] `GlobalScope` 대신 소유자가 명확한 스코프를 쓰는가
- [ ] 동시 작업은 `coroutineScope` 안의 `async` 로 묶여 실패 시 형제가 취소되는가
- [ ] 블로킹 호출은 `Dispatchers.IO`(또는 `limitedParallelism` 뷰)로 격리했는가
- [ ] `catch (e: Exception)`/`runCatching` 이 `CancellationException` 을 삼키지 않는가
- [ ] 긴 CPU 루프에 `ensureActive()`/`yield()` 가 있는가
- [ ] 정리용 suspend 호출은 `withContext(NonCancellable)` 로 감쌌는가
- [ ] flow 블록 안에서 `withContext` 대신 `flowOn` 을 쓰는가
- [ ] cold flow 를 여러 번 collect 해서 원치 않는 재실행이 생기지 않는가

---

## References

- Kotlin docs — [Coroutines basics](https://kotlinlang.org/docs/coroutines-basics.html)
- Kotlin docs — [Composing suspending functions](https://kotlinlang.org/docs/composing-suspending-functions.html)
- Kotlin docs — [Coroutine context and dispatchers](https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html)
- Kotlin docs — [Cancellation and timeouts](https://kotlinlang.org/docs/coroutines-cancellation.html)
- Kotlin docs — [Coroutine exceptions handling](https://kotlinlang.org/docs/exception-handling.html)
- Kotlin docs — [Asynchronous Flow](https://kotlinlang.org/docs/coroutines-flow.html)
- kotlinx.coroutines API — [Dispatchers.Default](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-default.html), [Dispatchers.IO](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html), [runBlocking](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-blocking.html), [asCoroutineDispatcher](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/as-coroutine-dispatcher.html), [StateFlow](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-state-flow/)
- OpenJDK — [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- OpenJDK — [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491)

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/)
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/)
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/)
- J9. [스프링이 자바를 쓰는 방식 — 리플렉션·프록시·DI](/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/)
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/)

**코틀린**

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/)
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/) ← 지금 글
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
