---
layout: post
title: "락을 걸었는데 왜 옛날 값이 나오나 — synchronized · JPA 영속성 컨텍스트 · MyBatis 로컬 캐시, 낡음이 사는 세 개의 층"
date: 2026-09-02 22:12:49 +0900
categories: [Java, Backend]
tags: [java, synchronized, jpa, hibernate, mybatis, jmm, transactional, spring, locking, concurrency]
---

동시성 버그 리포트에서 가장 자주 보는 문장이 있다.

> "`synchronized` 걸었는데도 재고가 음수로 갑니다."

그리고 그다음에 거의 항상 이어지는 조치가 있다. 락 범위를 넓힌다. 그래도 안 되면 `synchronized`를 클래스 레벨로 올린다. 그래도 안 되면 DB를 의심한다.

문제는 락의 **크기**가 아니라 **층**이다. "옛날 값"이 만들어지는 지점은 자바 애플리케이션에 최소 세 군데 있고, `synchronized`가 손대는 곳은 그중 하나뿐이다. 나머지 둘은 JPA를 쓰느냐 MyBatis를 쓰느냐에 따라 모양이 다르다.

이 글은 그 세 층을 분리하고, 각 층에서 실제로 뭘 써야 하는지 정리한다.

- **층 1 — JVM 메모리**: CPU 캐시와 JIT 재배치. `synchronized` / `volatile` 의 영역
- **층 2 — 프레임워크 세션 캐시**: JPA 영속성 컨텍스트, MyBatis 로컬 캐시. `synchronized` 가 **전혀** 손대지 못하는 영역
- **층 3 — DB 트랜잭션**: 격리 수준과 행 잠금. 프로세스 밖까지 나가는 유일한 층

이 블로그에는 [JPA와 MyBatis가 JDBC의 무엇을 지웠는지](/2026/08/20/jpa-vs-mybatis-two-branches-from-jdbc/), [낙관적 락과 분산 락을 언제 쓰는지](/2026/06/05/optimistic-lock-vs-distributed-lock-when-which/) 다룬 글이 이미 있다. 이 글은 그 앞 단계 — **왜 `synchronized`로는 애초에 안 되는가**를 층 단위로 쪼갠다.

---

## 층 1 — `synchronized` 가 실제로 보장하는 것

먼저 `synchronized`가 무엇을 주는지 정확히 하고 시작하자. 자바 언어 명세(JLS) §17.4.5는 이렇게 적는다.

> "An unlock on a monitor *happens-before* every subsequent lock on that monitor."
> — [JLS SE21 §17.4.5 Happens-before Order](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)

그리고 happens-before가 뭘 뜻하는지도 같은 절에 있다.

> "If one action *happens-before* another, then the first is visible to and ordered before the second."

즉 스레드 A가 모니터를 풀면, 그 이후 같은 모니터를 잡는 스레드 B는 A가 그 전에 쓴 값을 **본다**. 이게 `synchronized`가 파는 물건 전부다. 원자성(한 번에 하나만)과 가시성(먼저 쓴 걸 본다), **같은 JVM의 같은 모니터에 한해서.**

같은 절에 이런 경고도 붙어 있다.

> "if two actions share a *happens-before* relationship, they do not necessarily have to appear to have happened in that order to any code with which they do not share a *happens-before* relationship."

happens-before를 공유하지 않는 코드에는 아무 보장이 없다는 뜻이다. **DB는 이 관계를 공유하지 않는다.** 다른 JVM도 마찬가지다. 층 1의 도구가 층 2·3에 아무 영향을 못 미치는 이유가 여기서 이미 나온다.

## 층 2 — 프레임워크가 들고 있는 낡은 사본

여기가 실무에서 사람을 잡는 층이다. DB에는 새 값이 커밋돼 있는데, 애플리케이션이 **자기 세션 안의 사본**을 보고 있는 상황이다. 두 프레임워크가 서로 다른 방식으로 이 사본을 만든다.

### JPA — 영속성 컨텍스트는 "설계상" 낡는다

Hibernate 사용자 가이드는 Session을 이렇게 설명한다.

> the Session "maintains a generally **'repeatable read' persistence context (first level cache)** of the application domain model."
> — [Hibernate ORM 6.6 User Guide, §2.1 Architecture Overview](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html)

핵심은 *repeatable read*다. 하나의 영속성 컨텍스트 안에서 같은 식별자로 두 번 조회하면 **같은 자바 인스턴스**가 나온다. 이건 버그가 아니라 사양이 약속한 동작이고, 엔티티 동일성(`==`)이 성립하는 근거다.

그런데 이 약속이 곧 "낡음의 보장"이기도 하다.

```java
// 스레드 B (긴 트랜잭션 안)
Item item = em.find(Item.class, 1L);   // stock = 10 을 읽어 컨텍스트에 적재
// ... 이 사이에 스레드 A 가 stock = 0 으로 UPDATE 하고 커밋 ...
Item again = em.find(Item.class, 1L);  // DB 를 다시 안 간다. 여전히 stock = 10
```

두 번째 `find`는 SELECT를 날리지 않는다. 컨텍스트에 있으니까. 여기에 `synchronized`를 아무리 둘러도 소용이 없다 — 스레드 B의 낡은 값은 **CPU 캐시가 아니라 힙 위의 엔티티 객체**에 들어 있고, `synchronized`는 힙 객체를 무효화하지 않는다. 층이 다르다.

해법도 층 2의 도구여야 한다. Hibernate 가이드가 두는 자리는 이렇다.

- **refresh** (§6.11 Refresh entity state) — 해당 엔티티만 DB에서 다시 읽어 덮어쓴다
- **clear / evict** (§6.14 Evicting entities) — 컨텍스트를 비운다
- **detach** (§6.12 Working with detached data) — 관리 대상에서 떼어낸다

`em.refresh(item)` 한 줄이 `synchronized` 블록 열 줄보다 정확한 처방인 경우가 실제로 많다.

### MyBatis — "SQL을 직접 쓰니까 항상 최신"이 아니다

MyBatis를 쓰는 팀에서 자주 나오는 오해가 "우리는 매퍼로 SQL을 직접 날리니 캐시 문제가 없다"는 것이다. 공식 설정 문서를 보면 그렇지 않다.

> `localCacheScope` — 기본값 **SESSION**.
> "By default (SESSION) all queries executed during a session are cached. If `localCacheScope=STATEMENT` local session will be used just for statement execution, no data will be shared between two different calls to the same SqlSession."
> — [MyBatis 3, Configuration](https://mybatis.org/mybatis-3/configuration.html)

즉 **같은 `SqlSession` 안에서 같은 쿼리를 두 번 날리면 두 번째는 DB로 안 나간다.** 문서는 이 캐시의 목적을 "to prevent circular references and speed up repeated nested queries"라고 밝히고 있다. 성능·순환참조 방지용이지 정합성 장치가 아니다.

Spring 환경에서 `SqlSession`은 보통 트랜잭션에 묶이므로, **트랜잭션이 긴 만큼 로컬 캐시도 길게 산다.** JPA 영속성 컨텍스트와 증상이 거의 같아진다. 차이가 있다면 JPA는 이 동작이 사양에 명시된 계약이고, MyBatis는 껐다 켤 수 있는 설정(`localCacheScope=STATEMENT`)이라는 점 정도다.

**요약하면 층 2에서 두 프레임워크의 차이는 "캐시가 있냐 없냐"가 아니라 "계약이냐 옵션이냐"다.** 둘 다 낡은 사본을 들고 있을 수 있고, 둘 다 `synchronized`로는 못 고친다.

## 층 3 — 유일하게 프로세스 밖까지 가는 층

세 층 중 다중 인스턴스 환경에서 살아남는 건 이 층뿐이다. JVM 모니터는 정의상 그 JVM 안에서만 유효하다(JLS §17.1: "Each object in Java is associated with a monitor"). 파드가 두 개면 모니터도 두 개고, 두 스레드는 서로 다른 락을 잡고 사이좋게 같은 행을 덮어쓴다.

층 3의 도구는 프레임워크에 따라 이렇게 갈린다.

| | JPA | MyBatis |
|---|---|---|
| 낙관적 | `@Version` (충돌 시 `OptimisticLockException`) | 버전 컬럼을 직접 관리 — `UPDATE ... WHERE id=? AND version=?` 후 영향 행 수 확인 |
| 비관적 | `LockModeType.PESSIMISTIC_WRITE` | `SELECT ... FOR UPDATE` 를 매퍼에 직접 |

Hibernate 가이드는 낙관적 락(§11.1 Optimistic)과 비관적 락 모드(§11.3 LockMode and LockModeType, `PESSIMISTIC_WRITE` 포함)를 각각 별도 절로 둔다. MyBatis에는 대응 추상화가 없으므로 SQL로 직접 쓴다 — 그게 MyBatis의 설계 의도이기도 하다.

여기서 중요한 건 도구 목록이 아니라 **경계**다. 층 3의 도구만이 "다른 JVM에서 온 요청"을 막는다.

---

## 그래서, `@Transactional` + `synchronized` 는 왜 단일 서버에서도 안 되는가

여기까지는 "분산 환경이라 안 된다"는 익숙한 결론으로 갈 수 있다. 그런데 **서버가 한 대여도 이 조합은 깨진다.** 이유가 층 문제와 별개로 하나 더 있다.

흔히 쓰는 코드는 이렇게 생겼다.

```java
@Transactional
public synchronized void decrease(Long id, int qty) {
    Item item = repository.findById(id).orElseThrow();
    item.decreaseStock(qty);
}   // ← 여기서 모니터가 풀린다
```

`synchronized`는 메서드의 진입과 반환에 걸린다. 그런데 **커밋은 메서드가 반환된 뒤에 일어난다.** Spring의 선언적 트랜잭션은 AOP 프록시로 동작하고, 문서는 `TransactionInterceptor`가 트랜잭션을 "메서드 호출 **주변에서**(around method invocations)" 구동한다고 설명한다. 실제 순서는 소스에 그대로 있다.

```java
// spring-tx 6.2.0, TransactionAspectSupport#invokeWithinTransaction (L374~416)
TransactionInfo txInfo = createTransactionIfNecessary(ptm, txAttr, joinpointIdentification);  // L374
Object retVal;
try {
    retVal = invocation.proceedWithInvocation();   // L380 ← 대상 메서드. synchronized 블록은 여기서 끝난다
}
catch (Throwable ex) {
    completeTransactionAfterThrowing(txInfo, ex);
    throw ex;
}
finally {
    cleanupTransactionInfo(txInfo);                // L388
}
// ...
commitTransactionAfterReturning(txInfo);           // L416 ← 커밋은 여기
return retVal;
```
— [spring-framework v6.2.0, `TransactionAspectSupport.java`](https://github.com/spring-projects/spring-framework/blob/v6.2.0/spring-tx/src/main/java/org/springframework/transaction/interceptor/TransactionAspectSupport.java#L374-L416)

L380이 반환되는 순간 모니터가 풀리고, 커밋은 L416에서 일어난다. **그 사이에 창이 열린다.**

```
스레드 A : [락 획득] find(stock=10) → 9로 변경 → [락 해제] ······· [커밋]
스레드 B :                                      [락 획득] find(...) ← 아직 10
```

스레드 B는 락을 정상적으로 획득했는데도 커밋되지 않은 상태를 보고 출발한다. 락은 제대로 동작했다. 락이 지키는 구간과 트랜잭션이 지키는 구간이 어긋났을 뿐이다.

같은 문서에는 이 조합을 더 미끄럽게 만드는 조항도 있다.

> "In proxy mode (which is the default), only external method calls coming in through the proxy are intercepted. This means that self-invocation ... does not lead to an actual transaction at runtime even if the invoked method is marked with `@Transactional`."
> — [Spring Framework Reference, Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)

같은 클래스 안에서 부르면 트랜잭션 자체가 안 붙는다. 락은 걸리고 트랜잭션은 없는 상태 — 증상이 더 헷갈린다.

이 어긋남을 `synchronized`로 고치려면 **락을 트랜잭션 바깥에 걸어야** 한다. 즉 `@Transactional` 메서드를 호출하는 쪽에서 락을 잡고, 커밋이 끝난 뒤 풀어야 한다. 가능은 하지만 그렇게 만들어봐야 층 1의 도구인 건 변하지 않는다 — 파드가 두 개가 되는 순간 다시 무효다.

---

## 층별 정리

| 낡음이 사는 곳 | 증상 | 맞는 도구 | `synchronized` 로 되나 |
|---|---|---|---|
| 층 1. JVM 메모리 (CPU 캐시 / 재배치) | 다른 스레드가 쓴 필드 값이 안 보임 | `synchronized`, `volatile`, `Atomic*` | **된다** (이 층 전용) |
| 층 2. JPA 영속성 컨텍스트 | `find` 두 번 해도 DB 안 감, 커밋된 값 안 보임 | `refresh` / `clear` / 트랜잭션 경계 축소 | 안 된다 |
| 층 2. MyBatis 로컬 캐시 | 같은 SqlSession 안 동일 쿼리 재사용 | `localCacheScope=STATEMENT`, 세션 분리 | 안 된다 |
| 층 3. DB 동시 수정 | lost update, 재고 음수 | `@Version` / `FOR UPDATE` / 분산 락 | 안 된다 (특히 다중 인스턴스) |

체크 순서를 하나 제안하면 이렇다.

1. **인스턴스가 2개 이상인가?** → 그렇다면 층 1 도구는 후보에서 제외하고 시작한다. 고민할 게 없다.
2. **낡은 값이 DB에서 온 건가, 세션 캐시에서 온 건가?** → 쿼리 로그를 켜서 그 시점에 SELECT가 실제로 나갔는지 본다. 안 나갔으면 층 2다. `synchronized`를 아무리 만져도 안 바뀐다.
3. **SELECT는 나갔는데 값이 겹쳐 쓰이는가?** → 층 3이다. 충돌 빈도가 낮으면 `@Version`, 높으면 `FOR UPDATE`. 판단 기준은 [낙관적 락 vs 분산 락 글](/2026/06/05/optimistic-lock-vs-distributed-lock-when-which/)에 정리해뒀다.
4. **락과 트랜잭션 경계가 어긋나 있지 않은가?** → 위의 L380/L416 문제. 락이 커밋을 포함하지 못하면 락이 있으나 없으나다.

---

## 정리

`synchronized`가 나쁜 도구라서 재고 문제를 못 푸는 게 아니다. **정확히 자기 층의 일만 하기 때문에** 못 푼다. JLS가 약속한 건 "같은 모니터를 잡는 같은 JVM의 스레드 사이 가시성"이고, 그 약속은 지켜진다. 지켜지지 않는 건 개발자가 기대한 다른 두 층이다.

- 층 2의 낡음은 프레임워크가 **의도적으로** 만든 것이다. Hibernate는 그걸 "repeatable read persistence context"라 부르고, MyBatis는 `localCacheScope` 기본값 SESSION으로 켜둔다. 성능을 위해 산 낡음이니, 정합성이 필요하면 그 층의 스위치를 꺼야 한다.
- 층 3의 낡음만이 진짜 동시 수정이고, 그건 DB가 중재해야 한다. JPA면 `@Version`/`PESSIMISTIC_WRITE`, MyBatis면 SQL로 직접.
- 그리고 어떤 층이든, **락이 커밋을 감싸지 못하면 락이 아니다.**

동시성 문제를 만나면 락부터 넓히지 말고 먼저 물어보는 게 낫다. *지금 이 낡은 값은 어느 층에서 왔나.*

---

## References

- Oracle, [The Java Language Specification, SE 21 — Chapter 17. Threads and Locks](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html) (§17.1 Synchronization, §17.4.4 Synchronization Order, §17.4.5 Happens-before Order)
- Hibernate, [Hibernate ORM 6.6 User Guide](https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html) (§2.1 Architecture, §6.11 Refresh, §6.12 Detached data, §6.14 Evicting entities, §11.1 Optimistic, §11.3 LockMode and LockModeType)
- MyBatis, [MyBatis 3 — Configuration](https://mybatis.org/mybatis-3/configuration.html) (`localCacheScope`)
- Spring, [Spring Framework Reference — Using `@Transactional`](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)
- Spring, [Spring Framework Reference — Understanding the Spring Framework's Declarative Transaction Implementation](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-decl-explained.html)
- spring-projects/spring-framework, [`TransactionAspectSupport.java` v6.2.0, L374–L416](https://github.com/spring-projects/spring-framework/blob/v6.2.0/spring-tx/src/main/java/org/springframework/transaction/interceptor/TransactionAspectSupport.java#L374-L416)
