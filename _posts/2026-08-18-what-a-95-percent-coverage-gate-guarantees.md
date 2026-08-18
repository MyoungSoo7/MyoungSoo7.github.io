---
layout: post
title: "커버리지 95%가 보증하는 것과 보증하지 않는 것 — 정산 프로젝트 18개 모듈 실측"
date: 2026-08-18 20:30:00 +0900
categories: [testing, quality]
tags: [jacoco, coverage, gradle, mutation-testing, pitest, archunit, ci]
---

정산 프로젝트의 모듈별 테스트 커버리지 표를 다시 들여다봤다. 두 개의 숫자가 나란히 있다.

![정산 프로젝트 모듈별 커버리지 — 게이트 기준과 전체 소스 기준](/assets/images/settlement-coverage-gate-vs-whole-source.jpg)

같은 모듈인데 왼쪽은 97%, 오른쪽은 88%다. 어느 쪽이 진짜냐는 질문은 틀렸다. **둘 다 진짜고, 둘 다 같은 리포트 한 벌에서 나온다.** 다른 것은 "무엇을 세느냐"뿐이다.

이 글은 저 표가 무엇을 **보증**하고 무엇을 **보증하지 않는지**를, 추측이 아니라 실제 CI 산출물을 다시 계산해서 정리한 기록이다. 결론부터 말하면 — 보증하는 범위는 생각보다 좁고, 그 좁은 범위 안에서조차 두 개 모듈은 **아무것도 측정하지 않고 있었다.**

측정 대상은 공개 저장소 [MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement)의 main 브랜치이며, 원자료는 CI 실행 [#31895475292](https://github.com/MyoungSoo7/settlement/actions/runs/31895475292)(2026-08-15, success)가 남긴 18개 `backend-reports-*` 아티팩트다. 아래 숫자는 전부 그 아티팩트의 `jacocoTestReport.xml`을 다시 집계한 값이다.

---

## 1. 두 숫자는 같은 XML에서 나온다

JaCoCo 리포트는 한 번만 생성된다. 숫자가 갈리는 지점은 리포트가 아니라 **집계에서 무엇을 빼느냐**다. 루트 [`build.gradle.kts`](https://github.com/MyoungSoo7/settlement/blob/main/build.gradle.kts)가 두 태스크에 서로 다른 필터를 건다.

```kotlin
tasks.named<JacocoReport>("jacocoTestReport") {
    // 리포트: QueryDSL 생성 클래스만 제외
    classDirectories.setFrom(classDirectories.files.map { dir ->
        fileTree(dir) { exclude("**/Q*.class") }
    })
}

tasks.named<JacocoCoverageVerification>("jacocoTestCoverageVerification") {
    // 게이트: adapter in/out · config · util · *Application 을 추가로 제외
    classDirectories.setFrom(classDirectories.files.map { dir ->
        fileTree(dir) { exclude(
            "**/adapter/out/persistence/**", "**/adapter/in/web/**", "**/adapter/in/kafka/**",
            "**/config/**", "**/util/**", "**/SettlementServiceApplication*", /* … */ ) }
    })
    violationRules {
        rule { limit { counter = "LINE"; minimum = "0.90".toBigDecimal() } }
    }
}
```

즉 왼쪽 열(**게이트 기준**)은 헥사고날 구조에서 도메인·애플리케이션 계층만 남긴 뒤의 LINE 커버리지이고, 오른쪽 열(**전체 소스 기준**)은 어댑터·설정·부트스트랩까지 전부 포함한 값이다. CI를 실제로 막는 건 왼쪽뿐이다.

18개 모듈 아티팩트를 합산하면 이렇다.

| 구분            | 대상 라인 | 대상 클래스 | LINE 커버리지 |
| --------------- | --------: | ----------: | ------------: |
| 게이트 대상     |    20,451 |       1,798 |    **95.26%** |
| 전체 소스       |    37,025 |       2,980 |    **90.50%** |
| 게이트 **바깥** |    16,574 |       1,182 |    **84.62%** |

전체 라인의 **44.8%가 게이트 바깥**에 있고, 그 구간은 84.62%로 커버되어 있다. 측정은 되지만 점수는 매겨지지 않는 구간이다.

모듈별로 다시 계산한 값(게이트 / 전체):

| 모듈                         |   게이트 LINE | 전체 소스 LINE |
| ---------------------------- | ------------: | -------------: |
| investment-service           |         99.44 |          93.67 |
| account-service              |         99.02 |          95.29 |
| ai-service                   |         97.60 |          89.60 |
| company-service              |         97.09 |          93.77 |
| common-data-service          |         96.73 |          89.48 |
| market-service               |         96.61 |          88.19 |
| loan-service                 |         96.36 |          90.67 |
| settlement-service           |         95.39 |          90.76 |
| organization-service         |         95.33 |          94.63 |
| financial-statements-service |         95.07 |          93.03 |
| order-service                |         94.67 |          89.56 |
| insurance-service            |         94.43 |          88.30 |
| economics-service            |         91.89 |          88.93 |
| card-service                 |         91.81 |          87.41 |
| operation-service            |         91.25 |          90.13 |
| gateway-service              |   (해당 없음) |          33.33 |
| deposit-service              | **측정 없음** |  **측정 없음** |
| board-service                | **측정 없음** |  **측정 없음** |

첫 화면의 표와 대체로 맞고, 몇 모듈에서 소수점 이하가 다르다(예: card 91.81 vs 92.04). 표가 다른 커밋/실행에서 뽑힌 것으로 보인다. 마지막 세 줄은 뒤에서 따로 다룬다.

---

## 2. 그래서 이 숫자가 보증하는 것

### 2.1 "실행되었다"는 사실 — 딱 그것만

JaCoCo 문서가 LINE 카운터를 정의하는 문장은 명확하다.

> A source line is considered executed when at least one instruction that is assigned to this line has been executed.
> — [JaCoCo, Coverage Counters](https://www.jacoco.org/jacoco/trunk/doc/counters.html)

한 라인에 배정된 **명령어 중 하나라도** 실행되면 그 라인은 covered다. 그러니 게이트 95.26%가 보증하는 것은 정확히 이것이다 — _게이트 대상 20,451줄 중 19,482줄은 최소 한 번은 테스트가 지나갔다._ 그 이상도 이하도 아니다.

### 2.2 회귀를 막는 브레이크

값 자체보다 쓸모 있는 건 **하한선이 빌드에 물려 있다**는 점이다.

```kotlin
tasks.named("check") { dependsOn(tasks.named("jacocoTestCoverageVerification")) }
```

`check`가 `build`에 물려 있고 CI는 `./gradlew clean :${module}:build`를 돌리므로, 게이트 대상 커버리지가 90% 아래로 떨어지면 **빌드가 실패한다.** 테스트 없는 코드를 도메인 계층에 밀어넣는 경로가 물리적으로 막힌다. 여기에 18개 도메인 패키지에는 INSTRUCTION 80% 규칙이 하나 더 걸려 있어, 모듈 평균으로 특정 패키지의 공백을 가리는 것도 어렵다.

이건 Google의 권고와도 어긋나지 않는다. 구글은 60%를 "acceptable", 75%를 "commendable", 90%를 "exemplary"로 제시하면서도 top-down 강제에는 선을 긋는다([Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html), Arguelles·Ivanković·Bender, 2020).

### 2.3 낮은 숫자는 확정적인 정보다

커버리지의 비대칭성이 여기 있다. 높은 숫자는 품질을 증명하지 못하지만, **낮은 숫자는 공백을 확정한다.** gateway-service의 33.33%는 논쟁의 여지가 없다 — 그 모듈에는 클래스 1개, 라인 3줄뿐이고 테스트가 거의 없다. 커버리지는 "좋음"을 증명하는 도구가 아니라 "여기 안 봤다"를 들추는 도구로 쓸 때 값이 나온다.

---

## 3. 보증하지 않는 것

### 3.1 실행 ≠ 검증 — 뮤테이션으로 재봤다

구글의 같은 글이 못 박은 문장이다.

> Code coverage does not guarantee that the covered lines or branches have been tested correctly, it just guarantees that they have been executed by a test.

그럼 정산 프로젝트의 테스트는 실제로 "검증"을 하고 있나. 말로 답하지 않고 [PIT(pitest)](https://pitest.org/)로 돌려봤다. 대상은 `settlement-service`의 `github.lms.lemuel.settlement.domain.*` — 이 프로젝트에서 유일하게 pitest가 설정된 모듈이다.

```
>> Line Coverage (for mutated classes only): 490/562 (87%)
>> Generated 332 mutations  Killed 273 (82%)
>> Mutations with no coverage 55.  Test strength 99%
>> Ran 615 tests (1.85 tests per mutation)
```

`mutations.xml`을 세어보면 KILLED 272 / SURVIVED 4 / TIMED_OUT 1 / NO_COVERAGE 55다. 읽는 법은 이렇다.

- **뮤테이션 스코어 82%** — 라인 커버리지 95%와 13%p 차이. 숫자가 서로 다른 걸 재고 있다는 증거.
- **테스트가 지나간 구간에서는 강하다.** 커버된 277개 중 273개를 죽였다(test strength 99%). 즉 82%와 100%의 격차는 "약한 단언"이 아니라 **테스트가 아예 안 지나간 55개 뮤턴트**에서 온다.
- 살아남은 4개 중 3개는 `ConditionalsBoundaryMutator` — 경계 조건(`<` → `<=`)이다. 라인은 실행됐지만 경계값이 단언되지 않은 전형적인 구멍.

다만 정직하게 덧붙일 것이 있다. 살아남은 하나(`AmountAllocator:85`)를 열어보면,

```java
BigDecimal remainder = target.subtract(assigned);
int units = remainder.abs().intValueExact();
BigDecimal step = remainder.signum() < 0 ? BigDecimal.ONE.negate() : BigDecimal.ONE;
for (int k = 0; k < units; k++) { … }
```

`remainder`가 0이면 `units`도 0이라 루프가 돌지 않고 `step`은 쓰이지 않는다. `< 0`을 `<= 0`으로 바꿔도 관측 가능한 동작이 같은 **등가 뮤턴트(equivalent mutant)**에 가깝다. 뮤테이션 스코어를 게이트로 쓸 거면 이 비용을 먼저 계산해야 한다는 뜻이다.

그리고 이 pitest는 **CI에서 한 번도 돌지 않는다.** `.github/workflows/`에서 `pitest`를 grep하면 0건이고, 빌드 스크립트에도 `mutationThreshold`가 없다. 위 숫자는 이 글을 쓰려고 로컬에서 돌려 얻은 것이지, 파이프라인이 지키는 값이 아니다.

### 3.2 같은 코드인데 LINE 95%, BRANCH 85%

게이트는 LINE 카운터만 본다. **똑같은 클래스 집합**에서 BRANCH를 세면 숫자가 이렇게 갈린다.

| 카운터 |            게이트 대상 |           전체 소스 |
| ------ | ---------------------: | ------------------: |
| LINE   |      95.26% (20,451줄) |   90.50% (37,025줄) |
| BRANCH | **85.09%** (7,632분기) | 79.80% (10,711분기) |

게이트를 통과한 코드 안에서만 **1,138개 분기가 한 번도 타지 않았다.** 한 줄에 배정된 명령어 하나만 실행돼도 covered가 되는 LINE의 정의(§2.1)가 그대로 드러나는 지점이다. 90% LINE 게이트는 분기 조합에 대해 아무것도 말하지 않는다.

### 3.3 점수가 안 매겨지는 44.8%

주석은 "adapter in/out은 Testcontainers 통합 테스트로 별도 검증"이라고 적혀 있다. 그 전제가 어디까지 사실인지 분류별로 세어봤다(전 모듈 합산, LINE).

| 제외 분류                    |   커버리지 |      라인 |    미커버 |
| ---------------------------- | ---------: | --------: | --------: |
| security                     |      0.00% |         6 |         6 |
| bootstrap(`*Application`)    |     12.20% |        82 |        72 |
| util                         |     73.68% |        57 |        15 |
| **persistence**              | **81.17%** | **6,844** | **1,289** |
| kafka                        |     83.80% |     1,185 |       192 |
| external(PG·LLM·mail·PDF 등) |     86.45% |     2,384 |       323 |
| web(controller·API·DTO)      |     87.48% |     4,120 |       516 |
| config                       |     91.70% |       916 |        76 |
| batch                        |     92.55% |       255 |        19 |
| event                        |     94.05% |       689 |        41 |
| monitoring                   |    100.00% |        36 |         0 |

대체로 "버려진 구간"은 아니다. 하지만 persistence 6,844줄에서 1,289줄이 미커버이고, 이 구간에는 **게이트가 없다.** 나빠져도 빌드가 안 깨진다.

전제 자체도 조건부다. Testcontainers 통합 테스트 81개 클래스(13개 모듈)가 이렇게 걸려 있다.

```java
@EnabledIf(value = "isDockerAvailable", disabledReason = "Docker is not available")
```

Docker가 없으면 **조용히 스킵되고 빌드는 초록색이다.** 더 분명한 건, 첫 화면 표에 있는 세 모듈은 Docker 기반 통합 테스트가 **0개**인데도 persistence를 게이트에서 빼고 있다는 점이다.

| 모듈                | Docker 통합 테스트 | 제외된 persistence 라인 | 그 구간 커버리지 |
| ------------------- | -----------------: | ----------------------: | ---------------: |
| economics-service   |                  0 |                     114 |           77.19% |
| market-service      |                  0 |                     130 |           81.54% |
| common-data-service |                  0 |                     153 |           83.01% |

"통합 테스트로 별도 검증한다"는 근거로 제외했는데 그 통합 테스트가 없는 구간이다.

### 3.4 아무도 호출하지 않는 코드도 100%가 될 수 있다

커버리지는 "이 코드가 필요한가"를 묻지 않는다. 테스트만 있으면 죽은 코드도 만점이다. 이건 이 저장소에서 실제로 잡힌 문제다. ArchUnit 기반 인바운드 포트 도달성 가드를 신설한 커밋 [`a4b254f`](https://github.com/MyoungSoo7/settlement/commit/a4b254f830528109b037f4b7b5b14eea60f75c8b)가 10개 서비스에서 찾아낸 3건:

- **loan** — 담보 재평가·강제집행 유스케이스(마진콜 140%·청산 120% 판정)가 어떤 인바운드 어댑터에서도 도달 불가
- **card** — 명세서 개시 유스케이스에 청구 사이클 입력 경로가 없음
- **order** — `UpdateUserUseCase`: 구현체도 호출자도 없는 죽은 인터페이스

전부 커버리지 게이트를 통과한 상태였다. 이걸 잡은 건 커버리지가 아니라 아키텍처 테스트다.

### 3.5 측정 자체가 비어 있을 수 있다 — deposit·board

가장 뼈아픈 항목이다. CI 실행 #31895475292의 `backend-reports-deposit-service`와 `backend-reports-board-service`를 열면 `jacocoTestReport.xml`에 **클래스가 0개**이고 HTML에는 이렇게 적혀 있다.

```
No class files specified
```

원인은 필터를 **두 번 겹쳐 적용**한 것이다. 루트가 이미 `classDirectories`를 필터링된 `FileTree`로 교체했는데, 두 모듈이 그 위에 같은 관용구를 한 번 더 얹는다.

```kotlin
// deposit-service/build.gradle.kts
classDirectories.setFrom(
    files(classDirectories.files.map {          // ← .files 가 여기서 즉시 평가된다
        fileTree(it) { exclude("github/lms/lemuel/deposit/adapter/**", …) }
    })
)
```

`classDirectories.files`는 **설정(configuration) 시점에 즉시 해석**된다. 클린 빌드에서는 그 순간 클래스 출력 디렉터리가 아직 없으므로 빈 집합이 스냅샷되고, 이후 컴파일된 클래스는 영영 리포트에 들어오지 않는다. 그리고 대상이 0개인 `JacocoCoverageVerification`은 **위반 없이 통과한다.**

추측이 아니라 재현했다. 게이트를 100%로 올리는 init 스크립트를 얹어 "게이트가 살아 있으면 반드시 실패"하는 조건을 만들었다.

```kotlin
// probe.init.gradle.kts
allprojects {
    tasks.withType<JacocoCoverageVerification>().configureEach {
        violationRules { rule { limit { counter = "LINE"; minimum = "1.00".toBigDecimal() } } }
    }
}
```

| 조건                                            | 결과                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------ |
| deposit, 빌드 산출물이 남아 있는 트리           | **BUILD FAILED** — `lines covered ratio is 0.93, but expected minimum is 1.00` |
| deposit, `clean` 후 단일 `build` (= CI 조건)    | **BUILD SUCCESSFUL**, 리포트 클래스 0개                                        |
| shared-common(같은 관용구 1회만 적용), clean 후 | **BUILD FAILED** (0.92 vs 1.00)                                                |

세 번째 줄이 대조군이다. 필터를 한 번만 얹은 모듈은 멀쩡하다. 즉 **deposit-service와 board-service의 커버리지 게이트는 CI에서 아무것도 측정하지 않는 상태로 초록불을 켜고 있었다.** 첫 화면 표의 deposit 행(97%대 / 88%대)은 CI가 만들어낸 값이 아니다.

로컬에서는 재현이 잘 안 된다는 점도 함정이다. 루트 `clean`은 `:clean`이라 모듈 산출물을 지우지 않으므로, 그냥 돌리면 클래스가 잡혀서 정상으로 보인다. `:deposit-service:clean` 후 별도 `build`로 실행해야 CI와 같은 조건이 된다.

### 3.6 PR은 바뀐 모듈만 잰다

`ci.yml`은 `dorny/paths-filter`로 변경 모듈을 뽑아 그 모듈만 매트릭스로 돌린다(`shared` 변경이나 감지 실패 시에만 전체). 합리적인 최적화지만, **PR에 붙는 커버리지는 전체 상태가 아니라 건드린 모듈의 상태**다. 위의 합산 수치는 전체가 도는 main 빌드에서만 나온다.

### 3.7 측정과 "보이는 것"은 다른 문제다

`build.gradle.kts`에는 2026-08-12 기록이 남아 있다 — SonarCloud coverage **0.0%**, new_coverage **0.0%**. 테스트가 없어서가 아니라 `sonar.coverage.jacoco.xmlReportPaths`가 연결되지 않아서였다. 그 전에는 sonarqube 플러그인 5.1.0.4882가 Gradle 9에서 `NoSuchMethodError`로 죽고 있었는데, `continue-on-error`가 그걸 삼켜서 CI는 계속 초록이었다. 없었던 건 커버리지가 아니라 **게이트**였다. 지금은 플러그인 7.4.0.8496으로 올리고 경로를 연결했다.

---

## 4. 그래서 표를 어떻게 읽어야 하나

두 열의 **차이 크기**가 정보다. 차이는 "게이트 바깥 구간이 게이트 안보다 얼마나 덜 커버되어 있는가"를 뜻한다.

- organization(95.33 / 94.63), operation(91.25 / 90.13) — 차이 1%p 남짓. 어댑터까지 고르게 테스트된 모듈.
- market(96.61 / 88.19), ai(97.60 / 89.60), common-data(96.73 / 89.48) — 차이 8%p 이상. 도메인은 촘촘한데 어댑터가 얇다. 왼쪽 숫자만 보면 이 격차가 안 보인다.

그리고 왼쪽 열이 아무리 높아도 그것은 §2.1의 문장 하나만 보증한다. 나머지는 전부 별도의 도구가 필요하다 — 분기는 BRANCH 카운터가, 단언의 강도는 뮤테이션 테스트가, 도달 가능성은 아키텍처 테스트가.

## 5. 다음에 할 일

우선순위대로.

1. **deposit·board의 이중 `classDirectories` 제거** (§3.5). 지금은 게이트가 없는 것과 같다. 다른 모듈이 같은 관용구를 복사해 갈 위험도 있으니 루트 필터 하나로 통일하는 편이 낫다.
2. **게이트가 0개 클래스를 대상으로 통과하는 것을 실패로 만들기.** 위 probe 방식(임계값을 올려 반드시 깨지는지 확인)을 CI 스모크로 넣으면 같은 사고가 조용히 재발하지 않는다.
3. **pitest를 CI에 연결하고 임계값 걸기** (§3.1). 현재 82%가 관측됐으니 60~70% 정도의 하한부터. 단, 등가 뮤턴트 처리 비용을 먼저 감안할 것.
4. **BRANCH 카운터 규칙 추가** (§3.2). LINE 90% 옆에 BRANCH 하한을 두면 1,138개 미실행 분기가 숫자로 드러난다.
5. **통합 테스트가 없는 모듈의 persistence 제외를 재검토** (§3.3). economics·market·common-data는 "별도 검증"의 근거가 실재하지 않는다.

## 6. 이 글의 한계

- 합산 수치는 main 브랜치의 **CI 실행 1회**(2026-08-15, #31895475292)에서 나온 값이다. 커밋이 달라지면 소수점은 움직인다.
- `shared-common`은 CI가 커버리지 아티팩트를 올리지 않아 이 합산에서 빠져 있다.
- 뮤테이션 스코어는 `settlement-service`의 도메인 패키지 하나에서만 잰 값이다. 다른 모듈로 일반화할 수 없다.
- 첫 화면 표와 재계산 값이 몇 모듈에서 소수점 이하로 다르다. 표를 뽑은 커밋을 특정하지 못했으므로 그 차이는 해소하지 않고 남겨둔다.

---

## References

- JaCoCo, [Coverage Counters](https://www.jacoco.org/jacoco/trunk/doc/counters.html) — LINE/BRANCH/INSTRUCTION 카운터 정의 (공식 문서)
- Carlos Arguelles, Marko Ivanković, Adam Bender, [Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html), Google Testing Blog, 2020-08-07
- Marko Ivanković, Goran Petrović, René Just, Gordon Fraser, [Code Coverage at Google](https://research.google/pubs/code-coverage-at-google/), ESEC/FSE 2019
- Brian Marick, [How to Misuse Code Coverage](http://www.exampler.com/testing-com/writings/coverage.pdf), International Conference on Testing Computer Software, 1997 — 배경 읽을거리 (저자 사이트가 https 를 제공하지 않아 http 링크)
- [PIT Mutation Testing](https://pitest.org/) — 뮤테이터·등가 뮤턴트 관련 공식 문서
- Gradle, [The JaCoCo Plugin](https://docs.gradle.org/current/userguide/jacoco_plugin.html) — `JacocoCoverageVerification`, `violationRules`
- 원자료: [MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement) / CI 실행 [#31895475292](https://github.com/MyoungSoo7/settlement/actions/runs/31895475292) / 커밋 [`a4b254f`](https://github.com/MyoungSoo7/settlement/commit/a4b254f830528109b037f4b7b5b14eea60f75c8b)

_집계·재현에 쓴 수치는 위 CI 아티팩트를 내려받아 다시 계산한 값이며, pitest 결과만 로컬 실행(2026-08-18)이다. 벤치마크 비교나 타 프로젝트와의 우열 주장은 하지 않는다 — 이 글의 모든 숫자는 이 저장소 한 곳의 관측이다._
