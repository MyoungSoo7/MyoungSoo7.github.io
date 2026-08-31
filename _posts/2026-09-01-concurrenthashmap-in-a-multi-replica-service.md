---
layout: post
title: "레플리카가 3개인데 ConcurrentHashMap 을 믿었다 — settlement 의 7개 사용처를 전수 조사했다"
date: 2026-09-01 03:45:10 +0900
categories: [backend, java]
tags: [concurrency, java, spring-boot, kubernetes, rate-limiting, idempotency]
---

`ConcurrentHashMap`(이하 CHM)은 "동시성 걱정 없이 쓰는 Map" 으로 배운다. 그 문장은 절반만 맞다.
CHM 이 보장하는 것은 **한 프로세스 안에서, 한 번의 메서드 호출이** 원자적이라는 것뿐이다.
프로세스가 늘어나면 보장은 프로세스 수만큼 쪼개지고, 호출이 두 번이 되면 그 사이는 아무도 지켜주지 않는다.

내 정산 시스템 [settlement](https://github.com/MyoungSoo7/settlement) 에서 CHM 을 쓰는 모든 곳을 세어 봤다.
main 소스 5곳, testFixtures 1곳, 테스트 1곳 — 모두 7개다 (`49c131b5` 기준).

```
shared-common/.../ratelimit/RateLimitRegistry.java              레지스트리
operation-service/.../dedupe/InMemoryTtlDedupeStore.java         TTL 중복 제거
operation-service/.../web/NotificationStreamController.java      동시 접속 집합
external-data-service/.../web/SyncStatusTracker.java             키별 상태 슬롯
settlement-service/.../mockbank/MockBankServer.java              멱등 원장 (테스트 더블)
shared-common/src/testFixtures/.../EventContractValidator.java   스키마 메모 캐시
order-service/src/test/.../IdempotentOrderConcurrencyIT.java     동시성 IT
```

용도별로 갈라 놓으니 CHM 을 쓰는 이유가 네 가지로 정리됐고,
그중 **두 곳이 실제로 틀려 있었다.** 하나는 배포 형상 때문에, 하나는 코드 자체 때문에.

---

## 1. 첫 번째 오류: "단일 노드 가정" 이라고 적어 놓고 3개를 띄웠다

`RateLimitRegistry` 는 Bucket4j 버킷을 키별로 들고 있는 전형적인 레지스트리다.

```java
private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

public Bucket resolve(RateLimitPolicy policy, String key) {
    String composite = policy.name() + "|" + key;
    return buckets.computeIfAbsent(composite, k -> buildBucket(policy));
}
```

코드는 흠잡을 데가 없다. javadoc 도 정직하다 — **"단일 노드 가정"** 이라고 적혀 있다.
문제는 그 가정이 배포 형상과 어긋나 있다는 것이다.

```
$ kubectl get deploy -n settlement-prod
NAME                  READY
settlement-app        3/3      ← 여기
settlement-frontend   3/3
settlement-operation  1/1
...
```

`shared-common` 이 클래스패스에 있는 한 `RateLimitFilter` 는 `FilterRegistrationBean` 으로 `/*` 에 붙는다.
즉 이 레지스트리는 **레플리카마다 하나씩, 서로 모르는 채로** 산다.
Kubernetes Service 는 요청을 백엔드 Pod 들에 분산하므로([Service 문서](https://kubernetes.io/docs/concepts/services-networking/service/)),
같은 IP 에서 온 로그인 시도는 3개의 서로 다른 버킷에 나뉘어 들어간다.

정책에 적힌 값이 분당 5회라면, 실제 천장은

$$
\text{유효 한도} = N_{\text{replica}} \times \text{정책값} = 3 \times 5 = 15\ \text{회/분}
$$

이다. 코드를 아무리 읽어도 안 보이고, 테스트도 통과하고, 로그에도 안 남는다.
**단위 테스트는 언제나 레플리카 1개짜리 세계에서 돌기 때문이다.**

여기서 진짜 교훈은 "분산 환경에선 Redis 를 써라" 같은 뻔한 문장이 아니다.
javadoc 에 가정을 적는 것까지는 잘했는데, **그 가정이 깨졌는지 검사하는 장치가 없었다**는 것이다.
주석은 배포 매니페스트를 읽지 못한다.

## 2. 두 번째 오류: CHM 을 썼는데 정작 원자적이지 않은 코드

`InMemoryTtlDedupeStore` 는 알림 중복 발송을 막는 TTL 기반 중복 제거기다.
"처음 보는 ID 인가?" 에 답한다.

```java
Instant prior = seen.putIfAbsent(id, now.plus(ttl));
if (prior != null && prior.isAfter(now)) return false;   // 아직 유효 → 중복
if (prior != null) { seen.put(id, now.plus(ttl)); }      // 만료됨 → 갱신
return true;                                              // 처음 봤다
```

`putIfAbsent` 는 원자적이다. `put` 도 원자적이다.
그런데 **둘 사이는 원자적이 아니다.**

두 스레드가 같은 만료된 항목을 동시에 만나면, 둘 다 `prior != null && prior.isAfter(now)` 를
거짓으로 읽고, 둘 다 `put` 하고, **둘 다 `true` 를 반환한다.**
"처음 봤다" 가 두 번 나온다 — 중복 제거기가 중복을 만든다.

전형적인 check-then-act 다. CHM 을 쓴다고 사라지지 않는다.
`ConcurrentMap` 이 이걸 위해 조건부 교체를 제공한다:

```java
if (prior != null && !seen.replace(id, prior, now.plus(ttl))) return false;
```

[`ConcurrentMap#replace(K,V,V)`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentMap.html#replace(K,V,V))
는 "값이 아직 `prior` 일 때만 바꾼다" 를 원자적으로 수행하고, 진 쪽에는 `false` 를 돌려준다.
`compute`/`merge` 로 감싸는 방법도 있다.

같은 클래스의 `evictExpired` 는 `seen.size()` 로 스윕 시점을 판단한다.
CHM 의 `size()` 는 동시 갱신 중에는 정확한 값이 아니다 —
[클래스 javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html)
이 집계성 메서드는 맵이 동시에 갱신되지 않을 때에나 유용하다고 명시한다.
스윕 임계값 판단에는 오차가 허용되므로 이건 버그가 아니지만,
**같은 숫자를 과금이나 한도 판정에 쓰면 그때부터는 버그다.**

## 3. 제대로 쓴 곳: `computeIfAbsent` 의 "키당 한 번" 을 설계에 활용

`SyncStatusTracker` 는 외부 데이터 수집원별 상태를 들고 있다.

```java
private final Map<String, Slot> slots = new ConcurrentHashMap<>();
// ...
slots.computeIfAbsent(source, this::createSlot);
```

`createSlot` 안에서 Micrometer `Gauge` 와 `Counter` 를 등록한다.
이게 안전한 이유는 딱 하나다 —
[`computeIfAbsent` 의 계산 함수는 키당 최대 한 번만 호출된다](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html#computeIfAbsent(K,java.util.function.Function)).
CHM 은 계산 중 해당 버킷을 잠그므로 두 스레드가 같은 소스로 동시에 들어와도 미터는 하나만 만들어진다.
`get()` 후 `null` 이면 `put` 하는 흔한 관용구로 짰다면 미터가 중복 등록된다.

바꿔 말하면 `computeIfAbsent` 는 "없으면 넣기" 의 축약형이 아니라
**부수효과가 있는 초기화를 키별로 한 번만 돌리는 도구**다. 이 차이가 실제로 결과를 가른다.

다만 CHM 은 여기까지만 해준다. 상태 전이 자체(예: `IDLE → RUNNING`)는
맵의 원자성으로 못 막는다. 조회와 갱신이 별개의 연산이기 때문이다.
그래서 이 클래스는 슬롯 **값 안에** `AtomicReference` 를 두고 `compareAndSet` 으로 전이한다.
CHM 이 지키는 것은 "슬롯을 찾는 일" 이고, "슬롯 안에서 벌어지는 일" 은 다른 도구가 지킨다.

이 클래스에는 설계 기록도 남아 있다. 4개 서비스를 한 프로세스로 합칠 때
상태를 `source` 로 키잉하지 않았다면, financial 수집이 도는 동안 market 수집이 409 로 거절됐을 것이다.
javadoc 의 표현을 빌리면 **"프로세스를 합친 것이 도메인 간 배타 락으로 새는 셈"** 이다.
맵의 키를 무엇으로 잡느냐가 곧 동시성 단위를 정한다.

## 4. 부수적으로: 집합이 필요하면 `newKeySet()`

SSE 접속을 들고 있는 `NotificationStreamController` 는 Map 이 필요 없다.

```java
private final Set<Connection> connections = ConcurrentHashMap.newKeySet();
```

`Collections.synchronizedSet` 은 모든 연산을 단일 락으로 직렬화하지만,
[`newKeySet()`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html#newKeySet())
은 CHM 의 분할 잠금을 그대로 물려받는다.
여기서 더 중요한 건 자료구조가 아니라 **제거 경로를 하나도 빠뜨리지 않는 것**이다.
이 컨트롤러는 `onCompletion`, `onTimeout`, `onError` 를 전부 같은 `close()` 로 보낸다.
셋 중 하나만 빠져도 죽은 연결이 집합에 영원히 남는다 — 스레드 안전한 메모리 누수다.

## 5. 모든 인메모리 맵은 캐시가 아니라 누수 후보다

`RateLimitRegistry` 로 돌아가면, 키는 `정책이름|IP` 다.
서로 다른 IP 가 들어올 때마다 항목이 하나씩 늘고, **이 맵은 아무것도 지우지 않는다.**

javadoc 은 "장시간 미사용 버킷 GC 는 Bucket4j 가 refill 기반으로 관리" 라고 적어 놨는데,
이건 사실과 다르다. Bucket4j 가 관리하는 건 버킷 **안의 토큰 리필**이고,
[Bucket4j 문서](https://bucket4j.com/) 어디에도 내가 만든 `HashMap` 에서 항목을 빼 준다는 말은 없다.
버킷 객체를 잡고 있는 건 CHM 이고, CHM 을 비우는 건 나다.

비교해 보면 차이가 분명하다. `InMemoryTtlDedupeStore` 는 `SWEEP_THRESHOLD = 1024`
스윕과 TTL 이 있어서 항목이 사라진다. `EventContractValidator` 의 `SCHEMA_CACHE` 는
키 집합이 스키마 파일 수로 유한하니 무한정 자라지 않는다.
**`RateLimitRegistry` 만 상한이 없다.** 그리고 그 키는 외부 입력에서 온다.

## 정리 — 코드가 아니라 경계를 본다

7개를 다 읽고 나서 남은 건 CHM 사용법이 아니라 **경계를 어디에 긋느냐** 였다.

| 물어볼 것 | settlement 에서 걸린 것 |
|---|---|
| 프로세스가 몇 개인가? | 레플리카 3개 × 분당 5회 = 실질 15회 |
| 한 번의 호출로 끝나는가? | `putIfAbsent` 후 `put` 은 원자적이지 않다 |
| 계산 함수에 부수효과가 있는가? | 있어도 된다 — 키당 한 번이 보장되므로 |
| 무엇이 항목을 지우는가? | 아무것도 안 지운다면 그건 캐시가 아니다 |
| 키가 곧 동시성 단위인가? | 키를 잘못 잡으면 도메인 간 배타 락이 된다 |

CHM 은 훌륭한 자료구조지만, 정확히 자기가 약속한 것만 지킨다.
**한 프로세스, 한 호출.** 그 밖은 전부 설계자의 몫이다.
그리고 그 경계는 코드가 아니라 배포 매니페스트와 호출 순서에 적혀 있어서,
코드 리뷰만으로는 잘 안 보인다.

---

## References

- Oracle, [`ConcurrentHashMap` (Java SE 21 API)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html) — 집계성 메서드의 근사값 성격, `computeIfAbsent` 의 키당 1회 호출, `newKeySet()`
- Oracle, [`ConcurrentMap#replace(K,V,V)` (Java SE 21 API)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentMap.html#replace(K,V,V)) — 조건부 원자적 교체
- Kubernetes, [Service](https://kubernetes.io/docs/concepts/services-networking/service/) — 백엔드 Pod 간 요청 분산
- [Bucket4j 공식 문서](https://bucket4j.com/) — 토큰 리필의 범위
- 소스: [MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement) `49c131b5`. 레플리카 수는 `kubectl get deploy -n settlement-prod` 실측값이다.
