---
layout: post
title: "@Async 를 튜닝하다가 @Async 를 떠난 78분 — settlement 의 ThreadPoolTaskExecutor 이력"
date: 2026-09-01 03:46:39 +0900
categories: [backend, spring]
tags: [spring, async, threadpooltaskexecutor, outbox, java]
---

`ThreadPoolTaskExecutor` 를 설명하는 글은 대개 `corePoolSize` / `maxPoolSize` / `queueCapacity` 세 숫자를 어떻게 잡느냐로 끝난다. 그런데 내 settlement 리포에 남은 실제 이력은 그 방향이 아니었다. 숫자를 고치고, 풀을 쪼개고, 거부 정책을 바꾸고 — **78분 뒤에 그 작업 자체를 `@Async` 밖으로 들어냈다.**

이 글은 그 78분에 관한 것이다. 튜닝이 왜 문제를 못 풀었는지가 요지다.

---

## 1. 등장 이유 — 한 풀이 두 종류의 일을 처리하고 있었다

처음 형태는 흔한 모양이다. `@EnableAsync` 하나, 풀 하나.

```java
@Configuration
@EnableAsync
@EnableScheduling
public class AsyncConfig {

    @Bean(name = "taskExecutor")
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);           // 기본 스레드 수
        executor.setMaxPoolSize(5);            // 최대 스레드 수
        executor.setQueueCapacity(100);        // 대기 큐 크기
        executor.setThreadNamePrefix("settlement-index-");
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }
}
```

빈 이름이 `taskExecutor` 인 건 우연이 아니다. `@EnableAsync` 는 컨텍스트에서 유일한 `TaskExecutor` 빈을 찾고, 없으면 **`taskExecutor` 라는 이름의 `Executor` 빈**을 찾는다. 둘 다 없으면 `SimpleAsyncTaskExecutor` 로 떨어진다 — 즉 풀이 아니라 호출마다 새 스레드다.[^enableasync] 이름 하나가 "풀을 쓴다" 와 "안 쓴다" 를 가른다.

문제는 이 풀에 성격이 전혀 다른 두 가지가 실려 있었다는 것이다.

- **ES 인덱싱** — 정산 데이터를 Elasticsearch 에 넣는다. 실패해도 재색인하면 된다. 베스트에포트다.
- **원장 분개 생성** — 정산이 커밋된 *뒤에* 회계 분개를 만든다. `@TransactionalEventListener(phase = AFTER_COMMIT)` 로 걸려 있었다. 유실되면 돈이 안 맞는다.

여기에 `prefix` 가 `settlement-index-` 인 것만 봐도 이 풀이 원래 무엇을 위해 만들어졌는지 알 수 있다. 원장 작업은 나중에 얹혔다.

### 큐가 먼저 찬다

`ThreadPoolTaskExecutor` 는 JDK 의 `ThreadPoolExecutor` 를 빈 스타일로 감싼 것이다.[^tpte] 그래서 스레드가 언제 늘어나는지도 JDK 규칙 그대로다. 그리고 그 규칙은 직관과 다르다.

> If fewer than corePoolSize threads are running, the Executor always prefers adding a new thread rather than queuing. If corePoolSize or more threads are running, the Executor always prefers queuing a request rather than adding a new thread. If a request cannot be queued, a new thread is created unless this would exceed maximumPoolSize, in which case, the task will be rejected.[^tpe]

즉 core 2 / max 5 / queue 100 이라는 설정에서 3번째 스레드가 뜨는 시점은 "작업이 3개 들어왔을 때" 가 아니다. **큐 100칸이 다 찬 다음**이다. 평상시 이 풀은 사실상 2스레드 풀이고, `maxPoolSize=5` 는 큐가 포화된 뒤에만 의미를 갖는다.

그리고 큐 100 + 스레드 5 까지 다 찬 뒤에 들어온 작업은 거부된다. 거부 처리기를 지정하지 않았으므로 기본값 `AbortPolicy` 다 — `RejectedExecutionException` 을 던지고, 그 작업은 실행되지 않는다.

정리하면 이 상태의 실패 시나리오는 이렇다. **인덱싱 버스트가 큐 100칸을 채운다 → 그 뒤에 도착한 원장 분개 작업이 거부된다 → 정산은 이미 커밋됐는데 분개는 영구 유실된다.** 예외는 `AFTER_COMMIT` 리스너를 호출한 쪽으로 전파되지만 트랜잭션은 이미 끝났으므로 되돌릴 것도 없다.

## 2. 1차 처방 — 풀 격리 + CallerRunsPolicy

`bc903820` (2026-06-06 02:25). 커밋 메시지가 문제 인식을 그대로 적고 있다.

```
fix(async): 원장 전용 executor 분리 + CallerRunsPolicy 로 유실 방지

ES 인덱싱(베스트에포트)과 AFTER_COMMIT 원장 분개가 단일 풀을 공유해,
인덱싱 버스트 시 원장 작업이 밀리거나 기본 AbortPolicy 로 거부되면
정산 커밋 후 분개가 영구 유실될 수 있었다.
```

바뀐 건 세 파일, 두 가지다.

**(1) 풀을 쪼갰다.**

```java
@Bean(name = "ledgerTaskExecutor")
public Executor ledgerTaskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(2);
    executor.setMaxPoolSize(4);
    executor.setQueueCapacity(50);
    executor.setThreadNamePrefix("ledger-async-");
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
    ...
}
```

리스너 쪽은 딱 한 글자 단위의 변경이다.

```diff
-    @Async
+    @Async("ledgerTaskExecutor")
```

이 한 줄이 실은 중요하다. 풀이 두 개가 되는 순간 "유일한 `TaskExecutor` 빈" 규칙은 더 이상 적용되지 않고, 이름 없는 `@Async` 는 `taskExecutor` 라는 *이름* 덕분에 계속 인덱싱 풀로 간다. 한쪽만 한정자를 붙이면 나머지는 조용히 예전 풀에 남는다.

**(2) 두 풀 모두 `CallerRunsPolicy` 로 바꿨다.**

> A handler for rejected tasks that runs the rejected task directly in the calling thread of the `execute` method, unless the executor has been shut down, in which case the task is discarded.[^callerruns]

거부되면 호출한 스레드가 직접 실행한다. 작업이 사라지지 않고(무손실), 제출하던 스레드가 그 일을 하느라 멈추니 자연스럽게 유입 속도가 줄어든다(백프레셔). `AbortPolicy` 대비 명백한 개선이다.

여기서 끝났다면 이 글은 "풀은 용도별로 격리하고 거부 정책을 고르자" 는 평범한 글이 됐을 것이다.

## 3. 78분 뒤 — 격리한 풀을 지웠다

`bb4fcd48` (2026-06-06 03:43). 앞 커밋과의 간격이 **78분**이다.

이 커밋은 `ledgerTaskExecutor` 빈을 통째로 지운다. 그리고 `LedgerCreationEventListener` 와 `LedgerReverseEntryEventListener` — `@Async` + `@TransactionalEventListener(AFTER_COMMIT)` 조합 두 개 — 도 파일째 삭제한다. 대신 들어온 것이 아웃박스 테이블과 폴러다.

```java
@Scheduled(fixedDelayString = "${app.ledger-outbox.poll-delay-ms:5000}")
@SchedulerLock(name = "ledger-outbox-poller", lockAtMostFor = "PT5M")
public void poll() { ... }
```

원장 작업은 이제 정산 트랜잭션 *안에서* `ledger_outbox` 행으로 저장된다. 커밋되면 행이 남고, 롤백되면 행도 없다. 폴러가 그 행을 읽어 처리한다. ShedLock 이 다중 인스턴스에서 중복 실행을 막는다.

### 78분 사이에 무엇을 깨달았나

풀 격리도 `CallerRunsPolicy` 도 같은 전제 위에 있다. **작업이 JVM 힙 안의 큐에 있다는 전제.**

- 프로세스가 죽으면 큐에 있던 것은 같이 사라진다. `setWaitForTasksToCompleteOnShutdown(true)` 는 *정상* 종료 때 큐를 비워주는 것이고, `awaitTerminationSeconds(30)` 를 넘기면 그마저 끊긴다. `kill -9`, OOM, 노드 축출에는 해당 사항이 없다.
- `CallerRunsPolicy` 는 유실을 막는 게 아니라 **거부를 막는다.** 이 둘은 다르다. 거부되지 않은 작업도 실행 중에 프로세스가 죽으면 그냥 없어진다.
- 재시도할 근거가 어디에도 남지 않는다. 무엇이 실패했는지 아는 유일한 기록이 로그 한 줄이다.

"정산이 커밋됐으면 분개는 *반드시* 만들어져야 한다" 는 요구를 인메모리 큐로 만족시킬 방법은 없다. 튜닝의 문제가 아니라 저장 위치의 문제다. 그래서 큐를 힙에서 DB 로 옮겼다 — 그게 아웃박스다.

## 4. 그래서 지금 남아 있는 `@Async`

오늘 이 리포의 프로덕션 코드에서 `@Async` 는 **정확히 한 곳**이다.

```java
@Async
@EventListener
public void handleSettlementIndexEvent(SettlementIndexEvent event) {
    try {
        // ES 벌크/단건 인덱싱
    } catch (Exception e) {
        log.error("이벤트 처리 실패: type={}, error={}", event.getEventType(), e.getMessage(), e);
        // UseCase 내부에서 이미 재시도 큐에 추가되므로 추가 처리 불필요
    }
}
```

그리고 `AsyncConfig` 의 주석은 다음처럼 바뀌어 있다.

```java
// 큐(100) + maxPool(5)까지 가득 차면 기본 AbortPolicy 는 예외를 던져 작업을 버린다.
// ES 인덱싱은 베스트에포트지만, 거부 시 호출 스레드가 직접 실행하는 CallerRunsPolicy 로
// 무손실 + 백프레셔를 보장한다. (원장 작업은 더 이상 이 풀에 의존하지 않고 트랜잭셔널
// 아웃박스 + 로컬 폴러로 처리된다 — LedgerOutboxPoller 참고.)
```

`@Async` 를 없앤 게 아니다. **`@Async` 가 감당할 수 있는 일만 남긴 것**이다. 인덱싱은 유실돼도 재색인으로 복구되고, 이 리스너는 예외를 자기가 삼킨다. 참고로 반환형이 `void` 인 `@Async` 메서드는 예외를 호출자에게 전달할 수 없고, 기본적으로 로깅만 된다 — 필요하면 `AsyncConfigurer` 로 `AsyncUncaughtExceptionHandler` 를 등록하는 자리다.[^enableasync] 이 리포는 등록하지 않았고, 대신 리스너가 자체적으로 잡는다.

## 5. 덤으로 — 프록시 함정은 게이트로 막는다

`@Async` 에는 튜닝과 무관한 별도의 함정이 있다. Spring 공식 문서의 표현이 정확하다.

> proxy mode allows for interception of calls through the proxy only. Local calls within the same class cannot get intercepted that way; an `@Async` annotation on such a method within a local call will be ignored since Spring's interceptor does not even kick in for such a runtime scenario.[^enableasync]

같은 클래스 안에서 `this.method()` 로 부르면 프록시를 지나지 않으므로 `@Async` 는 **조용히 무시된다.** 컴파일도 되고 테스트도 통과한다. 비동기여야 할 것이 동기로 돌 뿐이다.

이 리포는 그걸 사람 눈으로 잡지 않고 소스 레벨 스캔 게이트(`scripts/harness/test/aop-proxy-gate.test.mjs`)로 막는다. 같은 함정이 `@Retry` · `@CircuitBreaker` · `@Cacheable` · `@PreAuthorize` 에 그대로 적용되기 때문이다. 마지막 것은 특히 나쁘다 — 권한 검사가 조용히 사라진다.

---

## 정리

세 숫자를 잡는 문제로 시작해서 저장 위치의 문제로 끝났다.

| | 처방 | 막는 것 | 못 막는 것 |
|---|---|---|---|
| 이전 | 단일 풀, `AbortPolicy` | — | 거부·유실 전부 |
| `bc903820` | 풀 격리 + `CallerRunsPolicy` | 이웃 작업의 큐 점유, 거부 | **프로세스 종료** |
| `bb4fcd48` | 트랜잭셔널 아웃박스 + 폴러 | 위 전부 + 프로세스 종료 | (재처리 비용은 든다) |

`@Async` 와 `ThreadPoolTaskExecutor` 는 **잃어도 되는 일**에 쓰는 도구다. 잃으면 안 되는 일에 쓰면, 풀을 쪼개고 거부 정책을 바꾸는 방향으로 78분쯤 걸어가다가 결국 같은 결론에 도달하게 된다. 저 세 숫자를 만지기 전에 물어볼 것은 하나다 — **이 작업, 프로세스가 지금 죽으면 없어져도 되나?**

---

## References

[^tpe]: [`ThreadPoolExecutor` (Java SE 21 API Specification)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html) — "Queuing" 절. core → 큐 → max 순서, 그리고 거부 조건.
[^callerruns]: [`ThreadPoolExecutor.CallerRunsPolicy` (Java SE 21 API Specification)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.CallerRunsPolicy.html)
[^tpte]: [`ThreadPoolTaskExecutor` (Spring Framework API)](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/concurrent/ThreadPoolTaskExecutor.html) · [Task Execution and Scheduling (Spring Framework Reference)](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)
[^enableasync]: [`@EnableAsync` (Spring Framework API)](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/annotation/EnableAsync.html) — 기본 executor 해석 순서, `void` 반환의 예외 처리, `AdviceMode.PROXY` 의 self-invocation 제약.

코드·커밋은 개인 리포 `settlement` 의 `develop` 브랜치 기준이며, 커밋 해시(`bc903820`, `bb4fcd48`)와 시각은 `git log` 실측값이다.
