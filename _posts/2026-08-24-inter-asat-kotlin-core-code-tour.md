---
layout: post
title: "inter-asat 핵심 코틀린 코드 투어 — 223개 .kt, 그리고 끝까지 남은 Java 1개"
date: 2026-08-24 05:40:39 +0900
categories: [kotlin, spring]
tags: [kotlin, spring-boot, jvm-record, sealed-interface, hexagonal, strategy-pattern]
---

[inter-asat](https://github.com/MyoungSoo7/inter-asat) 은 이명·청각재활 대상자의 **주파수 JND / 공간 JND** 를 적응형 계단법(adaptive staircase)으로 측정하는 연구용 소프트웨어다. 이 글은 그 계단법이 *심리음향학적으로* 무엇인지를 설명하는 글이 아니라, 그 규칙이 **코틀린 코드로 어떻게 굳어졌는지** 를 보는 글이다.

기준 커밋은 `e40f057` (origin/main). 그 시점의 코드베이스 실측은 이렇다.

```bash
$ find src/main/kotlin -name '*.kt' | wc -l
223
$ find src/test -name '*.kt' | wc -l
35
$ find src -name '*.java'
src/main/java/interweb/com/rd/infrastructure/export/CsvHeader.java
```

Java 파일은 **딱 하나** 남았다. 왜 그 하나가 안 없어졌는지는 맨 마지막 절에서 다룬다.

---

## 1. build.gradle.kts 가 먼저 말해주는 것

```kotlin
plugins {
    kotlin("jvm") version "2.2.20"
    kotlin("plugin.spring") version "2.2.20"   // all-open
    kotlin("plugin.jpa") version "2.2.20"      // no-arg + all-open
}

kotlin {
    jvmToolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_24
    }
}
```

여기서 눈에 걸리는 건 **툴체인은 25인데 jvmTarget 은 24** 라는 점이다. 오타처럼 보이지만 아니다. Kotlin 2.2.20 의 Gradle 플러그인이 제공하는 `JvmTarget` enum 자체가 24에서 끝난다 — 로컬 캐시의 플러그인 API jar 를 직접 열어보면 확인된다.

```bash
$ unzip -p ~/.gradle/caches/modules-2/files-2.1/org.jetbrains.kotlin/\
kotlin-gradle-plugin-api/2.2.20/*/kotlin-gradle-plugin-api-2.2.20.jar \
  org/jetbrains/kotlin/gradle/dsl/JvmTarget.class | strings | grep -oE 'JVM_[0-9]+' | sort -u
...
JVM_22
JVM_23
JVM_24
```

즉 JDK 25로 빌드하되 바이트코드는 24로 낸다. 이건 "최신 JDK를 쓰면서 코틀린 컴파일러가 아직 못 내는 클래스파일 버전을 요구하지 않는" 조합이고, 툴체인 버전을 올릴 때 가장 먼저 깨지는 지점이기도 하다.

`plugin.spring` / `plugin.jpa` 두 줄도 그냥 관례가 아니다. 코틀린 클래스는 기본이 `final` 이라 Spring 의 CGLIB 프록시나 Hibernate 의 지연 로딩 프록시가 상속을 못 한다. all-open 플러그인이 `@Component`·`@Transactional`·`@Configuration` 등이 붙은 클래스를 자동으로 `open` 으로 만들고, no-arg 플러그인이 `@Entity` 에 합성 기본 생성자를 넣어준다.[^allopen][^noarg] 이 두 줄이 없으면 아래 나오는 엔티티 코드는 전부 런타임에 터진다.

---

## 2. Strategy — 난이도 정책은 "순수 값 변환"이다

계단법의 한 스텝은 `DifficultyPolicy` 라는 인터페이스 하나로 표현된다.

```kotlin
interface DifficultyPolicy {
    fun key(): PolicyKey
    fun step(input: PolicyInput): PolicyStep

    @JvmRecord
    data class PolicyInput(
        val currentDelta: BigDecimal,
        val currentStepSize: BigDecimal,
        val direction: Short,
        val reversalCount: Short,
        val reversals: List<BigDecimal>,
        val isCorrect: Boolean,
        val config: AlgorithmConfig,
    )

    @JvmRecord
    data class PolicyStep(
        val newDelta: BigDecimal,
        val newStepSize: BigDecimal,
        val newDirection: Short,
        val newReversalCount: Short,
        val newReversals: List<BigDecimal>,
        val converged: Boolean,
    )
}
```

설계의 핵심은 시그니처가 아니라 **금지 사항** 이다. 구현체(`TwoDownOneUpPolicy`, `ThreeDownOneUpPolicy`, `FixedDifficultyPolicy`)는 `@Component` 지만 상태가 없고, 리포지토리·DB·Spring 컨텍스트를 건드리지 않는다. 입력 값 묶음을 받아 출력 값 묶음을 돌려주는 순수 함수다.

그래서 정책 테스트는 Spring 컨텍스트를 띄우지 않는다. `PolicyInput` 을 손으로 만들고 `step()` 을 호출해 `PolicyStep` 을 단언하면 끝이다. 계단법처럼 *경계 조건이 곧 버그* 인 로직에서 이 차이는 크다 — 반전(reversal) 카운트가 하나 어긋나면 JND 값이 통째로 틀리는데, 그걸 확인하는 데 컨테이너가 필요하면 아무도 촘촘히 안 짠다.

clamp(하한·상한 고정)도 호출자가 아니라 정책의 책임으로 못 박혀 있다.

```kotlin
companion object {
    @JvmStatic
    fun clamp(delta: BigDecimal, config: AlgorithmConfig): BigDecimal { /* min/max 고정 */ }
}
```

---

## 3. Registry — `List<T>` 주입과 두 번의 fail-fast

정책을 고르는 코드는 `when` 문이 아니다.

```kotlin
@Component
class DifficultyPolicyRegistry(policies: List<DifficultyPolicy>) {

    private val byKey: Map<PolicyKey, DifficultyPolicy>

    init {
        val map: MutableMap<PolicyKey, DifficultyPolicy> = EnumMap(PolicyKey::class.java)
        for (p in policies) {
            val existing = map.put(p.key(), p)
            if (existing != null) {
                throw IllegalStateException("Duplicate DifficultyPolicy for key " + p.key() + ...)
            }
        }
        this.byKey = java.util.Map.copyOf(map)
    }

    fun get(key: PolicyKey): DifficultyPolicy =
        byKey[key] ?: throw IllegalStateException(
            "No DifficultyPolicy registered for key $key. Known keys: ${byKey.keys}",
        )
}
```

Spring 은 생성자의 `List<DifficultyPolicy>` 자리에 해당 타입의 빈을 전부 모아 넣어준다.[^autowired] 레지스트리는 그걸 각 빈이 **스스로 신고한** `key()` 로 색인한다. 새 정책을 추가하는 비용은 "클래스 하나 만들고 `@Component` 붙이기"가 전부다.

중요한 건 실패 지점이 두 군데라는 것.

- **중복 키 → 생성 시점에 폭발.** 애플리케이션이 아예 안 뜬다. 설정 오류를 런타임 조건으로 미루지 않는다.
- **없는 키 → 조회 시점에 폭발.** 이게 더 결정적이다. 어떤 정책 빈이 삭제된 뒤, 그 정책으로 시작된 과거 세션이 *조용히 다른 규칙으로 굴러가는* 상황을 막는다. 연구 데이터에서 이건 예외보다 훨씬 나쁜 사고다.

거의 같은 모양의 `SessionValidationStrategyResolver` 가 따로 있는데, 주석이 이유를 명시한다 — 일부 키(`BLOCK_ACCURACY_LADDER`)는 검증 전략은 있지만 난이도 정책이 없다. 억지로 한 레지스트리로 합치면 그 비대칭이 뭉개진다. 그래서 "미러링하되 의도적으로 별개 메커니즘"으로 둔다. 여기서 `get()` 이 예외 대신 `null` 을 돌려주는 것도 원래 `when` 의 fall-through 의미를 보존하기 위해서다.

---

## 4. `direction: Short` — 겹치지 않는 세 가족

3-down 1-up 정책이 가장 재미있다. 영속 상태에는 `direction` 이 `Short` 하나로만 저장되는데, 이 한 필드가 **상태 머신** 이다. 주석이 인코딩을 그대로 문서화한다.

```
INITIAL family     0, 1, 2      — 아직 아무 스텝도 밟지 않음; 연속 정답 n회
POST_DOWN family  10, 11, 12    — 마지막 유효 스텝이 DOWN; 그 이후 연속 정답 n회
POST_UP   family  -1, -2, -3    — 마지막 유효 스텝이 UP;   그 이후 연속 정답 n회
```

세 가족이 각자 0~2의 연속 정답 카운터를 들고 있고, 3번째 정답은 항상 DOWN 스텝을 내고 POST_DOWN 가족의 0번 슬롯으로 돌아간다.

```kotlin
private fun consecutiveCorrects(dir: Short): Int {
    if (isInitialFamily(dir)) return dir.toInt()          // 0, 1, 2
    if (isPostDownFamily(dir)) return dir - POST_DOWN_0   // 10, 11, 12 → 0, 1, 2
    if (isPostUpFamily(dir)) return -(dir - POST_UP_0)    // -1, -2, -3 → 0, 1, 2
    return 0
}
```

왜 INITIAL 을 POST_DOWN 과 굳이 분리했나. 주석의 답이 정확하다: 그래야 **맨 처음 오답이 UP→DOWN 반전으로 잘못 기록되지 않는다.** 되돌릴 이전 DOWN 스텝이 애초에 없기 때문이다. 초기값을 "DOWN 직후"와 같은 값으로 뭉뚱그렸다면 모든 세션의 반전 카운트가 1씩 부풀고, 마지막 반전점 평균으로 뽑는 JND 가 통째로 틀어진다.

반전 기록 조건도 두 겹이다.

```kotlin
val stepped = steppedDown || steppedUp
val stepEffective = stepped && newDelta.compareTo(currentDelta) != 0

if (stepEffective) {
    val prevEffective = effectiveStepDirection(dir)
    if ((steppedDown && prevEffective.toInt() == 1) || (steppedUp && prevEffective.toInt() == -1)) {
        reversalCount++
        ...
    }
}
```

방향이 뒤집혔다는 것만으로는 부족하고, **clamp 를 거친 뒤에도 delta 가 실제로 변했어야** 반전으로 센다. 하한에 붙어서 아무리 두드려도 값이 안 움직이는 구간에서 반전이 무한히 쌓이는 걸 막는 조건이다.

> 참고: 2-down 1-up / 3-down 1-up 이라는 변환 계단법 자체는 Levitt (1971) 의 transformed up-down 절차다. 각각 심리측정 함수의 약 70.7% / 79.4% 지점으로 수렴한다.[^levitt] 이 코드가 하는 일은 그 규칙을 재현 가능한 형태로 못 박는 것이다.

---

## 5. 스냅샷 — 세션이 "어떤 규칙으로" 돌았는지를 저장한다

```kotlin
@Entity
@Table(name = "algorithm_config_snapshot")
@SQLRestriction("deleted_at IS NULL")
class AlgorithmConfigSnapshot : BaseEntity {

    @Column(name = "initial_delta", nullable = false, precision = 10, scale = 4)
    lateinit var initialDelta: BigDecimal
        private set

    /**
     * The [PolicyKey] that drove the staircase for this session.
     * Persisted so that historical sessions remain reproducible even after
     * the default policy of a given protocol changes in code.
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "policy_key", nullable = false, length = 32)
    var policyKey: PolicyKey = PolicyKey.TWO_DOWN_ONE_UP
        private set
```

세션이 시작될 때 알고리즘 파라미터 **전부** 를 세션별로 한 벌 복사해 둔다. 모든 프로퍼티가 `var ... private set` 이다 — JPA 는 쓰기가 가능해야 하지만 외부에서는 못 바꾼다. 코틀린에서 세터만 좁히는 이 관용구가 "프레임워크 요구"와 "불변에 가까운 도메인"을 동시에 만족시키는 가장 값싼 방법이다.

가장 중요한 필드는 `policyKey` 다. 코드에서 기본 정책이 바뀌어도 **과거 세션은 자기가 돌던 규칙을 기억한다.** 연구 소프트웨어에서 재현성은 옵션이 아니다.

리터럴에 근거가 주석으로 붙어 있는 것도 이 파일의 성격을 보여준다.

```kotlin
this.bonusThresholdMs = 200   // Woodworth 1954, Brebner 1980
this.toneDurationMs = 500
this.isiMs = 800              // 500→800ms 로 상향 (Hoare et al. 2012)
this.configVersion = "v4.0"
```

그리고 파라미터 드리프트를 사람이 읽을 수 있게 뽑아주는 메서드가 붙어 있다.

```kotlin
/**
 * 이전 스냅샷과 비교하여 변경된 파라미터 목록을 반환.
 * 빈 리스트 = 동일한 설정 (드리프트 없음).
 */
fun diffFrom(prev: AlgorithmConfigSnapshot): List<String>
```

`BigDecimal` 비교에 `!=` 가 아니라 `compareTo(...) != 0` 을 쓰는 것도 의도적이다. `BigDecimal` 의 `equals` 는 스케일까지 보기 때문에 `10.0` 과 `10.00` 이 다르다고 나온다. 드리프트 감지에서 이 차이는 곧 오탐이다.

엔티티들은 하드 딜리트 대신 Hibernate 의 `@SQLRestriction("deleted_at IS NULL")` 로 소프트 딜리트를 건다.[^sqlrestriction] 측정 데이터를 지우는 대신 감춘다.

---

## 6. `ReversalCodec` — 의존성 역전을 인터페이스 한 장으로

반전점 목록은 DB 에 JSON 배열 문자열로 저장된다. 그런데 그 직렬화를 애플리케이션 서비스가 직접 하면 유스케이스가 Jackson 에 묶인다.

```kotlin
package interweb.com.rd.domain.port

interface ReversalCodec {
    /** Serialize a reversal series to its JSON array form (e.g. `"[10, 8, 5]"`). */
    fun toJson(reversals: List<BigDecimal>): String

    /** 빈 문자열이나 `"[]"` 입력은 비어 있는 mutable 리스트를 돌려준다. */
    fun fromJson(json: String?): MutableList<BigDecimal>
}
```

패키지 이름(`domain.port`)이 곧 규칙이다. 포트는 도메인에, Jackson 구현체는 어댑터에 산다. 인터페이스 두 메서드짜리 작은 장치지만, 이게 없으면 "JSON 라이브러리를 바꾸는 일"이 도메인 테스트를 건드리는 일이 된다.

---

## 7. Chain of Responsibility — `fun interface` 로 쓴 등급 판정

세션의 신뢰도 등급(A/B/C/F)은 if-else 사다리가 아니라 규칙 리스트다.

```kotlin
/** 각 규칙은 조건 충족 시 GradeResult를 반환하고, 아니면 null로 다음 규칙에 위임 */
fun interface GradeRule {
    fun evaluate(input: GradeInput): GradeResult?
}
```

`fun interface`(SAM 인터페이스)라서 구현체를 람다로 바로 쓸 수 있다.[^funinterface] 체인은 F → C → A 순으로 평가되고, 아무 규칙에도 안 걸리면 폴백이 B다.

```kotlin
private val CHAIN: List<GradeRule> = listOf(
    // F: 데이터 무효 — reversal 0회
    GradeRule { input ->
        if (input.reversalCount == 0) GradeResult(ReliabilityGrade.F, "No reversals recorded") else null
    },
    // C: reversal 부족
    GradeRule { input ->
        if (input.reversalCount < MIN_REVERSALS_B)
            GradeResult(ReliabilityGrade.C, "Insufficient reversals: " + input.reversalCount) else null
    },
    ...
)

/** 체인 종단 — 어떤 규칙에도 해당하지 않으면 B등급 */
private val FALLBACK = GradeResult(ReliabilityGrade.B, "Partial criteria met")
```

두 가지가 눈에 띈다. 첫째, 모든 임계값이 이름 붙은 상수다(`ACCURACY_A_LOW = 60.0`, `MAX_ANTICIPATORY_A = 0.05`, `HP_TEST_PASS_THRESHOLD = 5` …). 둘째, `GradeResult` 가 등급뿐 아니라 **사유 문자열** 을 같이 들고 다닌다. 등급이 왜 C로 떨어졌는지가 값 안에 있어서, 나중에 데이터를 걸러낼 때 원인을 되짚을 수 있다.

체인 순서 자체도 도메인 규칙이다. 무효(F)를 먼저 걸러내고, 품질 미달(C)을 걸러낸 다음에야 A 를 판정한다. 순서를 바꾸면 "reversal 이 0인데 정확도가 좋아서 A"가 나올 수 있다.

---

## 8. sealed interface — 자극 생성 전략

```kotlin
sealed interface StimulusGeneratorStrategy {

    fun generate(state: AdaptiveAlgorithmState): AdaptiveAlgorithmService.StimulusInfo

    @JvmRecord
    data class TrialStimulus(val stimulusValue: BigDecimal, val referenceValue: BigDecimal)

    /**
     * 클라이언트가 이미 제시받은 trial 의 (stimulus, reference) 값을 모달리티별로 재구성한다.
     * generate() 와 달리 catch-trial/무작위화 없이 결정적으로 도출한다(trial 영속화용).
     */
    fun resolveTrialValues(
        state: AdaptiveAlgorithmState,
        stimulusInterval: Int,
        config: AlgorithmConfig,
    ): TrialStimulus
}
```

구현은 다섯 개 — `FrequencyStrategy`, `IldStrategy`, `ItdStrategy`, `CombinedStrategy`, `NoiseListeningStrategy` — 전부 `@JvmRecord data class` 다. `sealed` 라 계층이 컴파일 타임에 닫혀 있고, `when` 으로 분기할 때 컴파일러가 누락을 잡아준다.[^sealed] 앞의 `DifficultyPolicy` 는 런타임에 빈으로 열려 있어야 해서 sealed 가 아니고, 이쪽은 모달리티가 코드에 고정이라 sealed 다. 같은 "전략"이라도 확장 지점이 다르면 봉인 여부가 갈린다.

메서드가 두 개인 이유도 분명하다. `generate()` 는 catch-trial 과 무작위화를 포함하고, `resolveTrialValues()` 는 **결정적** 이다. 클라이언트가 이미 들은 자극을 나중에 DB 에 남길 때 난수를 다시 굴리면 저장된 값과 실제 들린 값이 어긋난다. 같은 개념의 두 얼굴을 한 메서드에 욱여넣지 않고 쪼개 놨다.

선택은 팩토리 하나로 끝난다.

```kotlin
@JvmStatic
fun forSession(
    session: TrainingSession,
    algorithmService: AdaptiveAlgorithmService,
    config: AlgorithmConfig,
): StimulusGeneratorStrategy {
    if (session.sessionType == SessionType.NOISE_LISTENING) return NoiseListeningStrategy(algorithmService)
    if (session.sessionType != SessionType.SPATIAL) return FrequencyStrategy(algorithmService, config)
    val mode = session.spatialMode
    if (mode == SpatialMode.ITD) return ItdStrategy(algorithmService)
    if (mode == SpatialMode.COMBINED) return CombinedStrategy(algorithmService)
    return IldStrategy(algorithmService)
}
```

---

## 9. 끝까지 남은 Java 파일 한 개

```java
package interweb.com.rd.infrastructure.export;

@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.RECORD_COMPONENT, ElementType.FIELD})
public @interface CsvHeader {
    String value();
}
```

12줄짜리 애너테이션이다. 이게 왜 코틀린으로 안 넘어갔나. 답은 `ElementType.RECORD_COMPONENT` 에 있다 — 코틀린에는 애너테이션 타깃으로 이에 대응하는 것이 없다. 그런데 쓰는 쪽은 코틀린이다.

```kotlin
@JvmRecord
data class SessionExportRow(
    @CsvHeader("세션ID") val sessionId: String,
    ...
)
```

`@JvmRecord` 를 붙인 `data class` 는 진짜 Java record 로 컴파일된다.[^jvmrecord] 그래서 익스포터가 리플렉션으로 record component 를 훑을 수 있다.

```kotlin
private fun getAnnotatedComponents(clazz: Class<*>): Array<RecordComponent> {
    return clazz.recordComponents
        .filter { c -> c.isAnnotationPresent(CsvHeader::class.java) }
        .toTypedArray()
}
```

`CsvExporter` 와 `ExcelExporter` 가 이 한 경로를 공유한다. DTO 에 헤더 이름을 선언해두면 CSV 열 순서와 엑셀 열 순서가 자동으로 같아지고, 필드를 추가할 때 익스포터 두 곳을 고칠 일이 없다. `@JvmRecord` 는 저장소 전체에서 30개 파일이 쓴다.

정리하면, 이 프로젝트에서 마지막 Java 파일이 살아남은 이유는 게을러서가 아니라 **Java 언어에만 있는 애너테이션 타깃을 코틀린 record 에 붙이기 위해서** 다. 순수 코틀린 비율을 맞추겠다고 이걸 지웠다면 익스포트 파이프라인 전체를 다른 방식(수동 헤더 매핑 등)으로 다시 짜야 했을 것이다. 100%라는 숫자보다 이 12줄이 싸다.

---

## 마치며

코드를 훑고 남는 인상은 하나다. **틀린 결과가 조용히 나오는 경로를 계속 막아 놨다.**

- 없는 정책 키 → 다른 규칙으로 대체되지 않고 예외
- INITIAL 가족 분리 → 첫 오답이 가짜 반전으로 안 세짐
- clamp 후 값 미변화 → 반전으로 안 세짐
- 세션별 `policyKey` 영속화 → 기본 정책이 바뀌어도 과거 세션은 재현됨
- `compareTo` 비교 → 스케일 차이로 인한 드리프트 오탐 방지

측정 소프트웨어에서 제일 나쁜 실패는 죽는 게 아니라 **그럴듯한 숫자를 내는 것** 이다. 위 다섯 개는 전부 그 실패를 예외나 명시적 상태로 바꾸는 장치다. 그리고 그걸 표현하는 데 쓰인 코틀린 기능들 — `private set`, `@JvmRecord`, `sealed interface`, `fun interface`, `EnumMap` 색인 — 은 하나같이 화려하지 않다. 그게 맞다고 본다.

---

## References

[^allopen]: JetBrains, "All-open compiler plugin," *Kotlin Documentation*. <https://kotlinlang.org/docs/all-open-plugin.html>
[^noarg]: JetBrains, "No-arg compiler plugin," *Kotlin Documentation*. <https://kotlinlang.org/docs/no-arg-plugin.html>
[^autowired]: VMware/Broadcom, "Using @Autowired — Arrays, Collections, Maps," *Spring Framework Reference Documentation*. <https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html>
[^levitt]: H. Levitt, "Transformed up-down methods in psychoacoustics," *Journal of the Acoustical Society of America*, vol. 49, no. 2B, pp. 467–477, 1971. DOI 10.1121/1.1912375 (PMID 5541744). 원문은 유료 구독이며, DOI 확인 요청이 봇 차단으로 반려되어 이 글에서는 서지 정보로만 인용한다.
[^sqlrestriction]: Hibernate ORM 6.6 API, `org.hibernate.annotations.SQLRestriction`. <https://docs.jboss.org/hibernate/orm/6.6/javadocs/org/hibernate/annotations/SQLRestriction.html>
[^funinterface]: JetBrains, "Functional (SAM) interfaces," *Kotlin Documentation*. <https://kotlinlang.org/docs/fun-interfaces.html>
[^sealed]: JetBrains, "Sealed classes and interfaces," *Kotlin Documentation*. <https://kotlinlang.org/docs/sealed-classes.html>
[^jvmrecord]: JetBrains, "Using Java records in Kotlin — Declaring records in Kotlin," *Kotlin Documentation*. <https://kotlinlang.org/docs/jvm-records.html>
