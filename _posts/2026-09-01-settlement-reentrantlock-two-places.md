---
layout: post
title: "핀이 사라진 뒤에도 ReentrantLock 이 남은 두 자리 — settlement 실측"
date: 2026-09-01 03:45:36 +0900
categories: [backend, concurrency]
tags: [java, reentrantlock, virtual-threads, jep491, distributed-lock, idempotency, sse]
---

Java 21 이 가상 스레드를 내놓았을 때 딸려 온 숙제가 하나 있었다. `synchronized` 안에서 블로킹하면 가상 스레드가 캐리어 플랫폼 스레드에 **핀(pinned)** 되어 못 내려온다는 것. JEP 444 는 아예 이렇게 적어 뒀다.

> "avoid frequent and long-lived pinning by revising `synchronized` blocks or methods that run frequently and guard potentially long I/O operations to use `java.util.concurrent.locks.ReentrantLock` instead"[^jep444]

그래서 한동안 "가상 스레드를 켰으면 `synchronized` 를 `ReentrantLock` 으로 바꿔라"가 사실상의 마이그레이션 지침이었다. 그리고 JDK 24 에서 JEP 491 이 그 이유를 없앴다.[^jep491] 모니터 소유권을 캐리어가 아니라 가상 스레드 단위로 추적하도록 JVM 을 고쳐서, `synchronized` 에서 블로킹해도 언마운트된다.

내 정산 서비스(`settlement`)는 Java 25 · Spring Boot 4.0.7 에 `spring.threads.virtual.enabled: true` 로 돌고 있다. 그러면 질문은 이렇게 된다. **핀이 사라졌는데 여기 남아 있는 `ReentrantLock` 은 관성인가, 이유가 있나.**

세어 보니 `src/main/java` 아래 자바 파일 3,113개 중 `ReentrantLock` 을 쓰는 건 **2개**였다. `synchronized` 는 3개 파일 4곳. 두 자리를 다 읽어 봤고, 결론부터 적으면 **둘 다 핀과는 상관없는 이유로 남아 있었다.**

## 자리 ① — 스트라이프 256개, 그리고 "3초만 기다린다"

`order-service` 의 중복 주문 방지 경로다. 같은 `Idempotency-Key` 로 두 번 들어온 요청을 직렬화한다.

```java
private static final int STRIPES = 256;
private final ReentrantLock[] stripes = new ReentrantLock[STRIPES];

private ReentrantLock lockFor(String key) {
    int idx = (key.hashCode() & 0x7fffffff) % STRIPES;
    return stripes[idx];
}

@Override
public <T> T executeWithLock(String key, Duration waitTime, Duration leaseTime, Supplier<T> action) {
    ReentrantLock lock = lockFor(key);
    boolean acquired = false;
    try {
        acquired = lock.tryLock(waitTime.toMillis(), TimeUnit.MILLISECONDS);
        if (!acquired) {
            throw new LockAcquisitionException("락 획득 시간 초과(in-memory): key=" + key);
        }
        return action.get();
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new LockAcquisitionException("락 대기 중 인터럽트: key=" + key, e);
    } finally {
        if (acquired) lock.unlock();
    }
}
```

배열로 쪼갠 이유는 고전적인 락 스트라이핑이다. Guava 의 `Striped` javadoc 이 그 절충을 정확히 설명한다 — 키마다 락을 하나씩 두는 `Map<K, Lock>` 은 동시성이 최대지만 메모리 사용량도 최대이고, 스트라이프 수가 적을수록 서로 다른 키가 같은 락에 매핑될 확률이 올라간다.[^striped] 여기 코드 주석도 같은 말을 한다 — "서로 다른 키가 같은 스트라이프를 공유하면 드물게 추가 직렬화가 생기나 무해".

정작 `synchronized` 로는 **못 쓰는 것**은 배열이 아니라 그다음 줄이다. `tryLock(3초)`. `synchronized` 에는 "3초 기다려 보고 안 되면 포기한다"가 없다. 들어가거나, 무한히 기다리거나 둘 중 하나다. JEP 491 도 핀을 없앤 뒤에 남는 선택 기준을 이렇게 정리한다.

> "Other APIs in the package provide greater power and finer control for advanced cases that require fairness, concurrent access to shared data with read-write locks, **timed or interruptible lock acquisition**, or optimistic reading."[^jep491]

즉 이 자리는 핀 때문이 아니라 **기능** 때문에 `ReentrantLock` 이다. JEP 491 이 아무것도 바꾸지 않는 자리다.

## 락은 정합성 수단이 아니다 — 그렇게 적혀 있다

이 포트의 javadoc 에 이런 문장이 있다.

> 락은 **가용성·중복작업 방지**를 위한 것이지 유일한 정합성 수단이 아니다 — 락이 비활성/만료돼도 호출부는 DB UNIQUE 제약 같은 영속 백스톱으로 최종 정합성을 보장해야 한다.

Martin Kleppmann 이 2016년에 Redlock 을 비판하며 세운 구분과 같은 이야기다. 락을 왜 쓰는지 물으면 답은 둘 중 하나인데 — **효율(efficiency)**: 락이 실패하면 같은 일을 두 번 해서 돈이 조금 더 나가거나 알림이 두 번 갈 뿐이다. **정합성(correctness)**: 락이 실패하면 데이터가 깨진다. 이 둘을 섞어 놓고 논의하면 안 된다는 게 그 글의 요지였다.[^kleppmann]

여기 락은 명시적으로 전자다. 후자는 마이그레이션에 박혀 있다.

```sql
-- V20260628100000__order_idempotency.sql
CREATE TABLE IF NOT EXISTS opslab.order_idempotency (
    idempotency_key VARCHAR(255) NOT NULL,
    ...
    CONSTRAINT pk_order_idempotency PRIMARY KEY (idempotency_key)
);
```

그리고 호출부는 락을 뚫고 들어온 동시 중복을 실제로 처리한다. `DataIntegrityViolationException` 을 잡아서 이긴 쪽 주문을 다시 읽어 돌려준다. 두 번째 요청은 실패가 아니라 **첫 주문의 멱등 응답**이 된다.

## 그래서 프로덕션에서 실제로 도는 건 어느 쪽인가

여기가 이 글을 쓰면서 새로 확인한 부분이다. 어댑터는 두 개다 — 방금 본 인메모리 스트라이프와, Redis `SET NX PX` + Lua CAS 해제를 쓰는 진짜 분산 락. 스위치는 이렇게 걸려 있다.

```java
// InMemory
@ConditionalOnProperty(name = "app.order.idempotency.distributed-lock",
                       havingValue = "false", matchIfMissing = true)
// Redis
@ConditionalOnProperty(name = "app.order.idempotency.distributed-lock", havingValue = "true")
```

`matchIfMissing = true` 니까 **설정하지 않으면 인메모리**다. 그래서 찾아봤다.

- settlement 리포 전체의 `.yml` / `.yaml` / `.properties` 에서 `app.order.idempotency.distributed-lock` 이 설정된 곳: **0건** (javadoc 과 애노테이션 4줄이 전부).
- helm-deploy 차트·values 전체에서 해당 키 또는 `DISTRIBUTED_LOCK` env: **0건**.
- 살아 있는 클러스터의 `settlement-prod/settlement-app` 디플로이먼트 env 13개 중 `LOCK`/`IDEMPOT` 을 포함하는 키: **없음**.

그리고 그 워크로드가 바로 `order-service` 다. CI 가 모듈→이미지 매핑을 주석으로 적어 두고 있고(`order-service → ghcr.io/myoungsoo7/settlement`), 차트의 `required-env.yaml` 도 이 앱을 order-service 로 지칭한다. 실행 중 레플리카는 **3개**다(차트 `replicaCount: 3`, 클러스터 실측 `.spec.replicas = 3`).

정리하면 프로덕션에서 도는 것은 Redis 분산 락이 아니라 **JVM 3개에 각각 따로 들어 있는 256개짜리 `ReentrantLock` 배열**이다. 파드 안에서는 직렬화가 되고, 파드 경계를 넘는 중복은 락이 전혀 못 본다. 그걸 잡는 건 `pk_order_idempotency` 하나다.

이건 고장이 아니다. 코드가 스스로 그렇게 적어 뒀고("멀티 인스턴스 환경의 최종 중복 차단은 호출부의 DB UNIQUE 백스톱이 보장한다"), 부팅 로그로도 남긴다. Kleppmann 의 구분대로 보면 오히려 정직한 배치다 — 효율 레이어는 싸고 근사하게, 정합성 레이어는 DB 제약으로. 어긋난 건 동작이 아니라 **이름**이다. `DistributedLockPort` 의 기본 구현이 분산이 아니다.

## 자리 ② — 재진입 락을 쓰면서 재진입을 금지한 곳

두 번째는 `operation-service` 의 SSE 알림 허브(`InMemoryNotificationStream`)다. 락 **하나**가 시퀀스 번호·수신자별 보존 버퍼·구독자 인덱스를 함께 지킨다. 여기서 `ReentrantLock` 을 고른 이유는 타임아웃이 아니라 **범위를 손으로 자르기 위해서**다.

```java
public StreamEvent publish(Notification notification) {
    StreamEvent event; List<Subscriber> targets;
    lock.lock();
    try {
        event = new StreamEvent(++seq, notification, clock.get());
        retainLocked(event);
        targets = new ArrayList<>(byRecipient.getOrDefault(notification.recipient(), Set.of()));
        for (Subscriber target : targets) enqueueLocked(target, event);
    } finally {
        lock.unlock();
    }
    // 전달은 락 밖에서.
    targets.forEach(this::pump);
    return event;
}
```

리스너 호출(= SSE 소켓 쓰기)은 락 바깥이다. 안에서 했다면 멈춰 있는 브라우저 하나가 발행자 전체를 막는다. 락을 쥔 채 우리가 모르는 코드를 부르지 않는 것 — Goetz 등이 *Java Concurrency in Practice* 에서 "open call" 이라고 부른 그 규칙이다.[^jcip] `synchronized` 블록으로도 못 할 건 아니지만, 이렇게 획득과 해제가 메서드 안에서 비대칭으로 흩어지는 모양은 명시적 락이 훨씬 읽기 쉽다.

더 재미있는 건 그다음이다. `ReentrantLock` 은 이름 그대로 재진입 가능한데, 구독자별 드레인 플래그는 **일부러 비재진입**이다.

```java
private final AtomicBoolean draining = new AtomicBoolean(false);
...
if (!subscriber.draining.compareAndSet(false, true)) return;
```

전달받는 도중에 리스너가 다시 `publish` 를 하면(재진입), 그 새 이벤트가 중첩 전달돼 이미 흐르고 있는 이벤트를 앞지를 수 있다. 그래서 락의 재진입성에 기대지 않고 CAS 로 한 번 더 잘랐다. 먼저 플래그를 잡은 쪽만 메일박스를 비우고, 나머지는 넣기만 한다. 재진입 가능한 락을 쓰면서 재진입을 금지한 자리다.

같은 이유로 구독 등록과 재개 백로그 적재가 **한 락 안에** 들어 있다. 동시에 발행된 이벤트는 백로그 스냅샷에 들어가거나 그 뒤 메일박스에 들어가거나 둘 중 하나지, 양쪽에 들어가지도 양쪽에서 빠지지도 않는다. 이 성질들은 문서가 아니라 테스트가 잡고 있다 — "재생 중 발행된 이벤트는 백로그 뒤에 순서대로 전달된다", "동시 발행에도 시퀀스는 유일하다", "메일박스가 넘치면 가장 오래된 것을 버리고 계속 흐른다".

## 대조 — 바로 옆 파일의 `synchronized`

그런데 같은 패키지의 컨트롤러에는 이런 게 있다.

```java
// NotificationStreamController.java:224
private final Object writeLock = new Object();
...
synchronized (writeLock) {
    emitter.send(event);   // 블로킹 소켓 쓰기
}
```

**블로킹 I/O 를 모니터로 감싼 것**이다. JEP 444 가 "자주 실행되면서 긴 I/O 를 감싸는 `synchronized`" 라고 콕 집어 지목했던 바로 그 모양이다. JDK 23 이하였다면 SSE 쓰기가 지연되는 동안 캐리어 플랫폼 스레드가 통째로 붙잡혔을 것이다. JDK 25 라서 안 붙잡힌다. 이 리포의 `application.yml` 도 그 이유를 한 줄로 적어 두고 있다.

```yaml
  threads:
    virtual:
      enabled: true # Java 21+ 가상 스레드 (Tomcat 요청 처리 + @Scheduled). JEP 491(JDK24+)로 synchronized 핀 없음
```

이 대조가 앞의 결론을 뒷받침한다. 만약 이 코드베이스에서 `ReentrantLock` 이 "핀 회피" 때문에 쓰였다면, **가장 먼저 바뀌었어야 할 자리가 안 바뀐 채로 남아 있다.** 남은 두 곳은 각각 타임아웃 획득과 락 범위 제어라는, 핀과 무관한 이유로 골라진 것이다.

## 남은 비용

정직하게 적어 둘 것들.

1. **해시 충돌은 공짜가 아니다.** 스트라이프 256개니까 서로 무관한 두 `Idempotency-Key` 가 같은 락에 매핑되면 한쪽이 최대 3초를 기다린다. Guava 문서가 말하는 그 확률이고, 정확성에는 영향이 없지만 지연에는 있다.
2. **이름과 실물의 간격.** `DistributedLockPort` 의 프로덕션 구현이 분산이 아니라는 사실은 코드를 세 군데(애노테이션 · 리포 설정 · 헬름 values) 열어 봐야 확인된다. 부팅 로그에 남기는 건 잘한 일이지만, 로그는 아무도 안 읽는다.
3. **Redis 어댑터의 해제 스크립트는 이제 한 줄로 줄일 수 있다.** 코드의 Lua CAS 는 redis.io 문서의 예제와 글자 그대로 같은데, 그 문서는 Redis 8.4 부터 같은 일을 `DELEX key IFEQ value` 로 할 수 있다고 안내한다.[^redis] 지금 안 도는 경로라 급하진 않다.
4. **JEP 491 이 모든 핀을 없앤 건 아니다.** 네이티브 메서드나 FFM 을 통해 들어간 뒤 콜백에서 블로킹하면 여전히 핀이고, JVM 은 이 경우 `jdk.VirtualThreadPinned` 이벤트를 낸다.[^jep491] 이 코드에는 해당 없지만, "이제 신경 안 써도 된다"는 아니다.

## 정리

JEP 491 이 없앤 것은 **`synchronized` 를 피할 이유**였지, `ReentrantLock` 을 쓸 이유가 아니다. 둘의 기본 의미가 같아진 지금은 JEP 491 의 표현대로 "손에 든 문제를 무엇이 더 잘 푸는지"만 보면 된다.

3,113개 파일에서 살아남은 두 자리는 그 기준을 통과한 것들이었다 — 하나는 `synchronized` 로는 문법 자체가 없는 **시간 제한 획득**, 다른 하나는 임계 구역을 발행과 전달로 **손으로 자르는 것**. 반대로 핀 회피가 진짜 이유였다면 진작 바뀌었을 자리(`synchronized (writeLock) { emitter.send(...) }`)는 그대로다.

같이 딸려 나온 건 코드가 아니라 사실 하나였다. 프로덕션 레플리카 3개가 "분산 락"이라는 이름의 **JVM 로컬 락**으로 돌고 있고, 진짜 중복 차단은 PK 제약 한 줄이 하고 있다는 것. 설계대로이긴 한데, 설계대로라는 걸 확인하는 데 세 군데를 열어 봐야 했다.

---

## References

[^jep444]: JEP 444: Virtual Threads — OpenJDK, JDK 21. <https://openjdk.org/jeps/444> — 인용문은 "Scheduling virtual threads" 절.
[^jep491]: JEP 491: Synchronize Virtual Threads without Pinning — OpenJDK, JDK 24, Closed/Delivered. <https://openjdk.org/jeps/491> — 인용문은 "Choosing between `synchronized` and `java.util.concurrent.locks`" 절, 네이티브 프레임 관련 서술은 "Diagnosing remaining cases of pinning" 절.
[^striped]: `com.google.common.util.concurrent.Striped` javadoc — Google Guava. <https://guava.dev/releases/snapshot-jre/api/docs/com/google/common/util/concurrent/Striped.html>
[^kleppmann]: Martin Kleppmann, "How to do distributed locking", 2016-02-08. <https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html>
[^redis]: "Distributed Locks with Redis" — Redis 공식 문서, *Correct Implementation with a Single Instance*. <https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/>
[^jcip]: Brian Goetz et al., *Java Concurrency in Practice*, Addison-Wesley, 2006 — 10장의 "open call"(락을 쥔 채 외부 메서드를 호출하지 않기).

> 이 글의 코드·수치는 `MyoungSoo7/settlement` 의 `develop` 기준 실측이다. 레플리카 수와 env 는 살아 있는 `settlement-prod` 네임스페이스에서 확인했다. 참고로 JEP 491 의 핀 제거는 JDK 24 릴리스 노트 기준의 사실이고, 그로 인한 **성능 차이는 여기서 측정하지 않았다** — 이 글의 주장은 "어느 쪽이 빠른가"가 아니라 "왜 이 자리에 이게 남았는가"다.
