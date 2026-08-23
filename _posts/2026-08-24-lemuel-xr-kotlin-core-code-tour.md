---
layout: post
title: "lemuel-xr 백엔드의 핵심 코틀린 코드 여섯 조각"
date: 2026-08-24 04:31:05 +0900
categories: [backend, kotlin]
tags: [kotlin, spring-boot, hexagonal-architecture, sealed-interface, caching, safety-gate]
---

lemuel-xr 백엔드는 Kotlin 2.2.20 · Spring Boot 4.0.4 · JVM 툴체인 25 위에서 돈다(`backend/build.gradle.kts`). 2026-08-24 기준 `backend/src/main` 에 코틀린 파일 298 개, `backend/src/test` 에 129 개가 있고 **자바 파일은 0 개**다. 원래는 자바 프로젝트였고, 커밋 `f047f52`("헥사고날 SOLID + 디자인패턴 + 전체 Java→Kotlin 100% 전환", 2026-07-16)에서 474 개 파일이 한 번에 갈렸다.

리포가 어느 정도 모양을 갖춘 김에, 이 백엔드에서 *가장 많이 읽히는* 코드 여섯 조각을 골라 왜 그렇게 쓰였는지 적는다. 문법 소개가 아니라 **결정 기록**에 가깝다. 이 코드베이스의 특징이 그거라서 그렇다 — 주석 대부분이 "무엇을 하는지"가 아니라 "왜 이 모양이어야 했는지"를 적고 있고, 대개 그 뒤에 실제로 터졌던 사고가 하나씩 붙어 있다.

---

## ① 도메인은 프레임워크를 모른다

`game/domain/GameSession.kt` 는 게임 한 판을 표현하는 애그리게이트다. 파일 전체에 `jakarta` 도 `springframework` 도 임포트되지 않는다.

```kotlin
class GameSession private constructor() {

    var id: UUID? = null
        private set
    var character: String? = null
        private set
    // ...

    /** 진행한 Scene 카운트를 단조 증가(monotonic)로 갱신. */
    fun advanceSceneCount(sceneId: Int) {
        sceneCountCompleted = maxOf((sceneCountCompleted ?: 0).toInt(), sceneId).toShort()
    }

    /** emergency exit — abandoned_at + final_outcome='safe_exit:...'. */
    fun exit(reason: String?, atScene: Int?) {
        abandonedAt = LocalDateTime.now()
        finalOutcome = "safe_exit:" + (reason ?: "user_choice")
        if (atScene != null) sceneCountCompleted = atScene.toShort()
    }

    companion object {
        fun start(userId: UUID?, character: String?): GameSession { /* ... */ }
        fun reconstitute(/* 저장된 전 상태 */): GameSession { /* ... */ }
    }
}
```

코틀린 문법에서 얻는 게 두 개 있다.

**`var x = null; private set`** — 게터는 공개하고 세터만 닫는다. 자바로 같은 걸 하려면 필드 + 게터 메서드를 손으로 써야 했고, 실수로 세터를 하나 열어 두면 아무도 모른다. 여기서는 상태를 바꾸는 길이 `recordDecision`·`advanceSceneCount`·`complete`·`exit` **네 개뿐**이고, 그게 곧 이 애그리게이트의 불변식이다.

**`private constructor()` + 팩토리 두 개** — `start()` 는 새 세션, `reconstitute()` 는 DB 에서 읽은 값의 복원이다. 둘을 갈라 놓은 이유는 `start()` 가 `UUID.randomUUID()` 와 `LocalDateTime.now()` 를 부르기 때문이다. 어댑터가 저장된 행을 되살릴 때 같은 생성자를 쓰면 ID 와 시작 시각이 조용히 새것으로 바뀐다. 생성자를 하나로 두면 그 사고를 막을 방법이 없다.

영속화는 `GameSessionPersistenceAdapter` 가 `GameSessionJpaEntity` 와 매핑한다. 도메인은 JPA 를 모르고, 유스케이스도 모른다. Spring 팀도 코틀린 가이드에서 도메인 표현과 프레임워크 결합을 분리하는 쪽을 권한다[^1].

---

## ② enum 한 줄이 곧 사용자 노출이다

`game/domain/Character.kt` 는 열네 줄짜리 enum 이다.

```kotlin
enum class Character(val dbValue: String) {
    JOB("job"), ELIJAH("elijah"), MOSES("moses"), DAVID("david"),
    JOSEPH("joseph"), JESUS("jesus"), SOLOMON("solomon"), RUTH("ruth"),
    PETER("peter"), DANIEL("daniel"), ESTHER("esther"),
    ABRAHAM("abraham"), JACOB("jacob"), RAHAB("rahab");

    companion object {
        fun from(value: String?): Character {
            if (value == null) throw AppException(ErrorCode.E_CHARACTER_UNKNOWN)
            for (c in entries) {
                if (c.dbValue.equals(value, ignoreCase = true) ||
                    c.name.equals(value, ignoreCase = true)) return c
            }
            throw AppException(ErrorCode.E_CHARACTER_UNKNOWN, "Unknown character: $value")
        }
    }
}
```

코드는 시시한데 이 파일의 **주석이 79 줄**이다. 본문보다 길다. 이유는 이 enum 이 시나리오 로더의 순회 대상이기 때문이다 — `ScenarioYamlLoader.loadAll()` 은 디렉터리를 훑는 게 아니라 `entries` 를 돈다. 그래서 콘텐츠가 다 완성돼 있어도 **여기 한 줄이 없으면 사용자에게 안 보인다.** 실제로 룻·베드로·다니엘·에스더·아브라함·야곱은 저작이 끝난 채로 몇 주씩 닫혀 있었고, 여는 순간이 곧 배포다.

그래서 각 인물 줄마다 "무슨 근거로 열었는지 / 무엇이 아직 없는지"가 주석에 붙어 있다. 예를 들어 다니엘 항목에는 *"인간 안전검토자 사인오프는 없다 — 해제하지 않고 대장에 미해소 부채로 등재한 채 연다"* 고 적혀 있다. 라합 항목에는 낭독 트랙이라 선택지가 하나도 없고 그 대가로 *"동의 카드와 상시 이탈이 유일한 통제"* 가 된다는 사실이 적혀 있다.

그리고 값을 늘렸는데 yml 을 안 만들면? 로더는 warn 로그만 남기고 조용히 넘어간다. 그 구멍은 `ScenarioYamlLoaderTest` 의 `모든 Character 에 시나리오 yml 이 존재하고 로드된다` 가 막는다. 코틀린에서 enum 상수 목록을 `entries` 로 그냥 순회할 수 있다는 점[^2]이, 이 경우엔 편의가 아니라 **테스트가 전수 검사를 걸 수 있는 지점**이다.

---

## ③ 등급은 사용자의 위중도가 아니라 키워드의 정밀도다

`safety/application/CrisisKeywordScanner.kt` 는 사용자가 쓴 글에서 위기 신호를 찾는다. 등급 체계에 대한 이 클래스의 입장이 명시돼 있다.

> **등급은 사용자의 위중도가 아니라 키워드의 정밀도를 잰다.** `자살` 은 다른 뜻으로 쓰일 여지가 거의 없어 critical 이고, `마지막` 은 일상어와 구분이 안 돼 medium 이다. 등급을 내리는 것은 "덜 위험한 사람" 이라는 판단이 아니라 "이 문자열만으로는 확신할 수 없다" 는 고백이다.

이 정의가 코드 모양을 정한다. 첫 매칭에서 멈출 수 없다는 뜻이기 때문이다.

```kotlin
private fun mostSevereMatch(text: String): Match? {
    val m = pattern.matcher(text)
    var best: Match? = null
    while (m.find()) {
        val p = classify(m)
        val rank = rankOf(severityOf(p))
        if (rank > (best?.rank ?: 0)) {
            best = Match(p, rank, m.start(), m.end())
            if (rank == MAX_RANK) break   // critical — 더 올라갈 등급이 없다
        }
    }
    return best
}
```

주석에 실제 문장이 예시로 박혀 있다. *"마지막으로 정리하고 있어요. 자살할 생각입니다"* — medium 토큰(`마지막`)이 먼저 나오므로 첫 매칭만 보면 `자살` 이 있는데도 조용한 카드로 끝난다. 등급이 전부 같았던 시절에는 드러나지 않던 구멍이다.

fallback 방향도 뒤집혀 있다. 매핑에 없는 분류는 `high` 가 아니라 **`critical`** 로 본다. 3단 등급 도입 전에는 *어떤* 매칭이든 LLM 호출을 건너뛰고 위기 화면을 강제했으니, 이름 없는 override 정규식을 쓰는 운영자가 등급 도입만으로 조용히 보호를 잃지 않으려면 fallback 이 옛 동작이어야 한다.

한 가지 더 — 해시 계산이 호출마다 새 객체를 만든다.

```kotlin
private fun sha256Hex(s: String): String =
    HexFormat.of().formatHex(
        MessageDigest.getInstance("SHA-256").digest(s.toByteArray(StandardCharsets.UTF_8)),
    )
```

이전 구현은 인스턴스 필드 하나를 재사용했다. 이 클래스는 싱글턴 `@Component` 이고 `scan` 은 요청 스레드에서 동시에 불린다. `MessageDigest` 는 `update` 로 데이터를 누적하다 `digest` 로 마감하고 초기 상태로 리셋되는 **상태 객체**이며, 자바독은 이 클래스에 대해 스레드 안전을 보장하지 않는다[^3]. 동시 호출이 서로의 버퍼를 덮으면 *엉뚱한 해시* 가 나온다. 이 프로젝트에서 해시는 평문을 저장하지 않고 사후 추적하는 유일한 수단이라, 틀린 해시는 감사 흔적의 소실이다.

---

## ④ 캐시 히트도 안전 게이트를 통과해야 한다

`ai/application/GenerateLlmResponseUseCase.kt` 는 LLM 응답을 캐시 우선으로 돌려주는 유스케이스다. 두 가지가 특징적이다.

**첫째, 캐시 히트를 무조건 믿지 않는다.**

```kotlin
val cached = cache.findByCacheKey(key)
if (cached.isPresent) {
    val hit = cached.get()
    // 게이트 도입 *이전* 에 캐시된 응답도 검사한다. 캐시를 통과시키면
    // 오염된 문장이 영구히 살아남아 게이트가 무력해진다.
    val cachedScan = forbiddenTokenScanner.scan(hit.response)
    if (cachedScan.matched) {
        recordGateBlock(cachedScan)
        return Result(forbiddenTokenFallback, "static", "safety-fallback", false)
    }
    // ...
}
```

캐시는 게이트보다 오래 산다. 게이트를 나중에 붙였는데 히트 경로를 열어 두면, 게이트 이전에 구워진 문장은 영원히 검사받지 않고 나간다. 같은 이유로 2026-08-23 에 고친 버그가 하나 더 있다 — `ai.generation.enabled=false` 인 경로에만 게이트가 없었다. 즉 **생성을 끄는 것이 안전 게이트를 함께 끄는 일**이었고, 생성을 끄는 이유가 대개 안전 우려라는 걸 생각하면 방향이 정확히 반대였다.

재시도는 딱 한 번이다. 같은 프롬프트라도 LLM 출력은 매번 다르므로 대개 1 회 재생성에서 풀리고, 두 번 연속 걸리면 프롬프트 자체가 문제일 가능성이 높아 더 시도하지 않는다. 그리고 걸린 응답은 캐시에 넣지 않는다.

계량 기준도 명시돼 있다. 게이트 블록 카운터는 "사용자가 대체 문구를 봤다"가 아니라 **"후보 문장 하나를 막았다"**를 센다 — 재시도로 풀린 경우도 한 번 센다. 그쪽을 빼면 *모델이 반복해서 금칙 문장을 만들고 있는데 재시도가 가려 주는 상태* 가 지표에서 사라진다.

**둘째, 트랜잭션 전파를 `REQUIRES_NEW` 로 격리한다.**

```kotlin
@Transactional(propagation = Propagation.REQUIRES_NEW)
fun execute(purpose: String, promptKey: String, variables: Map<String, Any?>): Result {
```

바깥 트랜잭션(예: `DecideSceneUseCase`)의 rollback 신호를 오염시키지 않기 위해서다. 사이드카가 5xx 를 뱉으면 *이 트랜잭션만* 롤백되고 바깥은 그 예외를 잡아 정적 fallback 으로 진행한다.

대신 대가가 있고, 코드 주석은 그걸 적어 뒀다 — `REQUIRES_NEW` 는 별도 커넥션을 잡으므로 풀 사이즈가 충분해야 한다. 이건 이 프로젝트만의 관찰이 아니라 Spring 레퍼런스가 명시적으로 경고하는 사항이다: 바깥 트랜잭션의 리소스는 그대로 묶여 있는 채 안쪽이 새 커넥션을 요구하므로, 풀이 동시 스레드 수를 최소 1 이상 초과하도록 잡지 않으면 커넥션 고갈과 교착에 이를 수 있다[^4].

---

## ⑤ sealed interface 가 HTTP 상태를 도메인 쪽에서 정한다

`tts/application/SynthesizeTtsUseCase.kt` 의 반환 타입이다.

```kotlin
/** POST /api/tts/synthesize 의 결과. */
sealed interface Submission {
    /** 캐시 히트 — 바로 재생 가능. */
    data class Ready(val audioUrl: String?, val durationMs: Int?) : Submission
    /** 큐에 올라감 — [jobId] 로 폴링할 것. */
    data class Pending(val jobId: String) : Submission
    /** 큐 포화 — 429. */
    data class Rejected(val queueDepth: Int) : Submission
}

sealed interface JobView {
    data class Ready(val audioUrl: String?, val durationMs: Int?) : JobView
    data object Pending : JobView
    data object Failed : JobView
}
```

봉인 계층의 모든 직접 하위 타입은 컴파일 시점에 알려져 있고, `when` 과 함께 쓰면 컴파일러가 분기 누락을 잡아 준다[^5]. 상태가 없는 경우는 `data object` 로 둔다 — `data class` 와 달리 인스턴스가 하나고 `toString()` 이 클래스 이름으로 나온다[^6]. 컨트롤러는 이 세 갈래를 각각 200 / 202 / 429 로 옮기기만 하면 되고, 새 상태를 추가하면 컨트롤러의 `when` 이 **빨개진다**. 어댑터가 조용히 옛 상태만 처리하는 사태가 구조적으로 안 생긴다.

이 유스케이스에는 캐시 설계 이야기가 두 개 더 있다.

**jobId 를 곧 cacheKey 로 뒀다.** 같은 텍스트에 대한 동시 요청이 자연히 하나의 작업으로 합쳐지므로 별도 중복 제거 장치가 필요 없다.

**의도적으로 `@Transactional` 이 아니다.** 트랜잭션 안에서 큐에 넣으면 PENDING 행이 커밋되기 *전에* 워커가 시작될 수 있고, 워커가 먼저 READY 를 쓴 뒤 바깥 트랜잭션이 커밋되며 PENDING 으로 덮어쓴다. 그래서 "PENDING 커밋 → 그 다음 enqueue" 순서를 손으로 보장한다.

그리고 유령 작업 처리:

```kotlin
// PENDING 행만 보고 "진행 중" 이라 판단하면 안 된다. 큐와 워커는 JVM 안에
// 있어서 배포·OOM·강제종료로 프로세스가 갈리면 행만 PENDING 인 채 아무도
// 처리하지 않는 유령이 남는다.
e.status == TtsCache.PENDING && queue.isInFlight(key) -> return Submission.Pending(key)
```

마지막으로 이 파일에서 제일 마음에 드는 장치는 **캐시 세대 표식**이다.

```kotlin
private val AUDIO_GENERATION: Map<String, String> = mapOf("ko" to "gem2", "en" to "gem2")
```

텍스트가 같아도 *나는 소리가 달라지는* 변경(엔진 교체, 화자 변경, 인코딩 변경)을 하면 이 값을 올린다. 없으면 그런 변경은 **배포는 성공하는데 사용자에게는 아무것도 안 바뀐다** — 캐시는 텍스트 해시로 조회되고 히트하면 사이드카를 아예 부르지 않기 때문이다. 세대 값 하나하나에 그 세대를 만든 이유가 적혀 있는데, 그중 두 개(`g2p1`·`g2p2`)에는 *"둘 다 오진이었다"* 고 적혀 있다. 한국어 발음 전처리 문제라고 보고 두 세대를 태웠는데, 전처리를 아예 하지 않은 원문도 똑같이 잡음이 났고 결국 엔진 문제였다는 기록이다.

> 참고: 이 파일에 인용된 수치(XTTS 가 오디오 1 초당 CPU 4.1~4.6 초, 51.5 초 문장이 base64 로 WAV 3.30MB 대 MP3 0.41MB, Gemini TTS 로 80 자 왕복 14 초, 전 문장 프리웜 93 건 36 분)는 전부 **이 프로젝트 파드에서 잰 자체 실측**이고 코드 주석에 근거가 남아 있다. 벤더의 공개 벤치마크가 아니며 제 3 자 재현 결과도 아니다.

---

## ⑥ "정본"은 한쪽만 고치는 길이 없을 때만 뜻을 가진다

마지막은 프로덕션 코드가 아니라 테스트다. `safety/application/CrisisKeywordDocContractTest.kt` 는 **문서와 런타임의 양방향 일치**를 강제한다.

정본은 `docs/EMOTION-CLASSIFIER.md` §3 의 키워드 사전이고, 런타임은 `application.yml` 의 정규식이다. 이 테스트가 없던 동안 두 곳은 오래 갈라져 있었다 — 문서에는 3 단 등급과 18 개 키워드가, 런타임에는 6 개 키워드가 전부 같은 등급으로 있었다.

검사는 두 방향이다.

1. **문서 → 런타임**: 문서 사전의 모든 키워드가 문서가 말한 등급으로 실제 판정되는가. 문자열 비교가 아니라 스캐너를 **돌려서** 확인한다. `죽고\s?싶` 하나가 `죽고 싶`·`죽고싶` 둘을 덮는 식으로 문법이 달라도 행동이 같으면 통과여야 하기 때문이다.
2. **런타임 → 문서**: 정규식의 리터럴 대안이 전부 문서에 적혀 있는가. 이 방향이 없으면 런타임에만 몰래 추가된 키워드가 "문서가 정본"이라는 말 아래에서 문서 밖에 산다.

그리고 vacuous green 방지 테스트가 따로 있다.

```kotlin
@Test
fun `문서 사전은 세 등급이 모두 비어 있지 않다`() {
    // 파싱이 조용히 한 등급만 읽어 오면 위 테스트가 vacuous green 이 된다.
```

문서를 긁어 오는 파서가 조용히 0 건을 읽으면 1 번 테스트는 "틀린 게 없다"며 초록이 된다. 검사 대상이 비어 있는 초록은 검사가 아니다. 그래서 사전이 비면 실패하고, 세 등급 중 하나라도 비면 실패한다.

---

## 공통점

여섯 조각을 관통하는 습관이 하나 있다. **주석이 코드의 동작이 아니라 결정과 그 대가를 적는다.**

- `REQUIRES_NEW` 옆에는 커넥션 풀 고갈 위험이 적혀 있다.
- 캐시 세대 표식 옆에는 그걸 안 올렸을 때 "배포는 되는데 아무것도 안 바뀌는" 실패 모드가 적혀 있다.
- enum 한 줄 옆에는 그 인물에게 아직 없는 검토가 적혀 있다.
- 등급 fallback 옆에는 그 값이 `high` 가 아니라 `critical` 이어야 하는 하위 호환 근거가 적혀 있다.

이 코드베이스에서 제일 비싼 자산은 코틀린 문법이 아니라 이 기록들이다. `private set` 도 `sealed interface` 도 결국 *잘못 쓰는 길을 없애는* 장치인데, 왜 없애야 했는지는 언어가 적어 주지 않는다.

---

## References

[^1]: Spring Framework Reference — *Kotlin support*. <https://docs.spring.io/spring-framework/reference/languages/kotlin.html>
[^2]: Kotlin Documentation — *Enum classes* (`entries`). <https://kotlinlang.org/docs/enum-classes.html>
[^3]: Java SE 25 API Specification — `java.security.MessageDigest`. "A `MessageDigest` object starts out initialized. The data is processed through it using the `update` methods... After `digest` has been called, the `MessageDigest` object is reset to its initialized state." 자바독은 이 클래스의 스레드 안전성을 보장하지 않는다. <https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/security/MessageDigest.html>
[^4]: Spring Framework Reference — *Transaction Propagation*, "Understanding PROPAGATION_REQUIRES_NEW": "Do not use `PROPAGATION_REQUIRES_NEW` unless your connection pool is appropriately sized, exceeding the number of concurrent threads by at least 1." <https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html>
[^5]: Kotlin Documentation — *Sealed classes and interfaces*. "All direct subclasses of a sealed class are known at compile time." <https://kotlinlang.org/docs/sealed-classes.html>
[^6]: Kotlin Documentation — *Object declarations and expressions* (data objects). <https://kotlinlang.org/docs/object-declarations.html>

코드 인용은 전부 `MyoungSoo7/lemuel-xr` 의 `main` 브랜치 커밋 `174d84e` 기준이며, 파일 경로는 본문에 적어 뒀다. 리포 통계(코틀린 298 / 테스트 129 / 자바 0, 전환 커밋 `f047f52` 474 파일)는 같은 커밋에서 `find` 와 `git show --stat` 으로 실측했다.
