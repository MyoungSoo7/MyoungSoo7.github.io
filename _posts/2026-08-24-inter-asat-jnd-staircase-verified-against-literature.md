---
layout: post
title: "inter-asat 의 JND 계단법을 문헌과 대조하고, 두 구현을 맞물려 돌려봤다"
date: 2026-08-24 05:47:32 +0900
categories: [psychoacoustics, engineering]
tags: [jnd, staircase, psychophysics, levitt, 3afc, inter-asat, validation]
---

[inter-asat](https://github.com/MyoungSoo7/inter-asat) 은 이명(tinnitus) 청각 훈련 앱이다.
그 안에 **JND(Just Noticeable Difference, 최소 가지 차이) 측정**이 들어 있다.
"이 사람이 두 소리의 차이를 알아채는 최소 크기는 얼마인가" 를 재는 절차다.

JND 측정은 심리물리학에서 60년 넘게 다듬어진 주제라서, 구현을 설명하는 것만으로는 부족하다.
**어떤 계단법(staircase)과 어떤 수렴 규칙을 썼는지가 곧 측정의 타당성**이기 때문이다.
그래서 이 글은 두 가지를 한다.

1. 구현을 끝까지 읽고,
2. 그 구현을 **1차 문헌과 대조**하고,
3. 프론트/백엔드 두 구현을 **JS 로 다시 짜서 서로 맞물려 돌린다.**

3번을 한 이유가 있다. 이 저장소에는 "프론트가 계산한 JND 가 맞는지" 를 서버가 다시 재생해서
확인하는 **검증기(replay validator)** 가 있다. 그런데 그 검증기 자체는 아무도 검증하지 않았다.

> **이 글의 범위와 한계를 먼저 밝힌다.** 모든 코드 인용은 `origin/main` 의
> `e40f057` 커밋을 정적으로 읽은 것이다. 실행 수치는 **내가 그 두 코드 경로를
> JS 로 재구현해 돌린 결과**이고, 저장소의 Kotlin/Gradle 테스트 스위트나 실제 서버를
> 돌려서 얻은 것이 아니다. 실제 참가자 데이터도 보지 않았다. 아래에서 "측정했다" 는
> 전부 이 시뮬레이션을 뜻한다.

---

## 1. 무엇을 재는가 — 두 트랙, 3AFC

두 종류의 JND 를 잰다.

| 트랙 | 무엇을 다르게 하는가 | 단위 |
|---|---|---|
| **주파수 JND** | 기준 톤 대비 주파수를 얼마나 올려야 다른 소리로 들리나 | % |
| **공간 JND** | 소리의 좌우 방향을 얼마나 틀어야 다른 방향으로 들리나 | 도(°) |

과제 형식은 **3AFC(three-alternative forced choice)** 다. 세 개를 들려주고 그중 하나만 다르며,
참가자는 반드시 셋 중 하나를 고른다. 셋 중 하나이므로 **찍어도 1/3 은 맞는다.** 이 추측률이
뒤에 나오는 모든 숫자의 기준선이 된다.

주파수 트랙의 기준 톤은 참가자마다 다르다.

```ts
// frontend/src/app/(trainee)/training/v2/frequency-jnd/page.tsx
const ref = tinnitusHz / 2 < 125 ? tinnitusHz : tinnitusHz / 2;
```

이명 주파수의 **한 옥타브 아래**를 기준으로 삼는다(단, 125 Hz 미만이 되면 이명 주파수 그대로).
기본값 1400 Hz 이면 기준은 700 Hz 다. 이 "700" 이 뒤에서 아주 중요해진다.

---

## 2. 3-down 1-up 은 왜 하필 79.4% 인가

핵심 규칙은 `frontend/src/lib/staircaseV2.ts` 에 있다.
**세 번 연속 맞히면 어렵게, 한 번 틀리면 쉽게.** 이른바 3-down 1-up 이다.

```ts
if (opts.isCorrect) {
  state.consecutiveCorrect += 1;
  if (state.consecutiveCorrect >= 3) {
    const newIndex = Math.min(state.presetIndex + 1, lastIndex);
    if (state.direction === 1) {           // 쉬워지던 중이었다면 → 반전
      state.reversalCount += 1;
      state.reversals.push(state.presetIndex);
    }
    state.direction = -1; state.presetIndex = newIndex; state.consecutiveCorrect = 0;
  }
} else {
  const newIndex = Math.max(state.presetIndex - 1, 0);
  if (state.direction === -1) {            // 어려워지던 중이었다면 → 반전
    state.reversalCount += 1;
    state.reversals.push(state.presetIndex);
  }
  state.direction = 1; state.presetIndex = newIndex; state.consecutiveCorrect = 0;
}
```

이 규칙이 수렴하는 지점은 임의로 정한 값이 아니다. Levitt(1971)의 원문은 이렇게 말한다 —
변환 상하법은 **DOWN 반응열이 나올 확률과 UP 반응열이 나올 확률이 같아지는 자극 수준**,
즉 각각이 0.5 가 되는 지점으로 수렴한다.[^levitt]

3연속 정답이어야 내려가므로 DOWN 열의 확률은 $P^3$ 이고, 따라서

$$P^n = 0.5 \quad\Longrightarrow\quad P = 0.5^{1/n}$$

$n=3$ 이면 $P = 0.5^{1/3} = 0.7937$, 즉 **79.4% 정답률**이다.
($n=2$ 면 70.7%, $n=4$ 면 84.1%. Levitt 논문이 2-down 1-up 에 대해 직접
$[P(X)]^2 = 0.5,\ P(X)=0.707$ 이라고 적어 둔 그 계산이다.)

그런데 3AFC 에서 79.4% "정답률" 은 79.4% "탐지" 가 아니다. 추측 보정을 넣어야 한다.
정답률 $p_c$ 와 실제 탐지확률 $p_d$ 의 관계는

$$p_c = p_d + \frac{1 - p_d}{3} \quad\Longrightarrow\quad p_d = \frac{p_c - 1/3}{2/3}$$

$p_c = 0.7937$ 을 넣으면 $p_d = 0.6905$. **이 앱이 재는 값은 "약 69% 확률로 탐지되는 차이"** 다.
"JND" 라는 한 단어 뒤에 이 기준(criterion)이 숨어 있고, 다른 논문의 JND 와 비교할 때는
반드시 이 기준을 맞춰야 한다.

여기서 저장소 자체 문헌 리뷰와 어긋나는 곳이 하나 있다.
`docs/1month/1week/research/01-adaptive-staircase-methods.md` 는 "ASAT 는 2-down 1-up 규칙 채택
→ 70.7% 수렴점" 이라고 적고 과제도 2AFC 라고 적어 뒀는데, 실제 배포된 V2 는 **3-down 1-up + 3AFC** 다.
문서가 코드를 따라오지 못했다. 같은 문서 §3.1 의 수렴점 공식
$P^n / (P^n + Q^m)$ 도 $n=2, m=1$ 에서 0.618 을 주어 **바로 아래 자기 표(70.7 / 79.4 / 84.1)와 모순**된다.
표가 맞고 공식이 틀렸다. 다행히 **코드는 표를 따랐다.**

---

## 3. 사다리(preset ladder)라는 선택

프론트엔드는 연속적인 delta 를 다루지 않는다. 미리 정해 둔 값 목록의 **인덱스**를 오르내린다.

```ts
// frontend/src/lib/constants.ts
export const FREQUENCY_PRESET_PERCENT = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.5, 0.2] as const;
export const FREQUENCY_JND_INITIAL_INDEX = 7;   // 3%
export const SPATIAL_PRESET_DEGREES = [90,80,70,60,50,40,30,20,10, 9,8,7,6,5,4,3,2,1] as const;
```

인덱스가 클수록 어렵다. 장점은 명확하다 — 자극 값이 이산적이라 프리렌더/캐시가 쉽고,
재생 검증에서 값이 정확히 일치한다.

단점도 명확하다. **간격이 균일하지 않다.** 공간 사다리는 10° 까지는 한 칸이 10° 인데
그 아래로는 한 칸이 1° 다. 계단법의 스텝 크기는 추정치의 편향과 정밀도를 직접 좌우하는 값인데,
여기서는 "지금 어느 칸에 있느냐" 에 따라 실효 스텝이 10 배 달라진다.

백엔드는 다르게 짰다. `ThreeDownOneUpPolicy.kt` 는 연속 `BigDecimal` 로 움직이고,
반전이 일정 횟수 쌓이면 스텝을 줄인다.

```kotlin
if (reversalCount >= config.fineStepThreshold) { stepSize = config.smallStep }
```

이건 Levitt 이 직접 권한 것이다 — "테스트 도중 스텝 크기를 체계적으로 줄이면 추정 효율이 높아진다."[^levitt]
같은 파일에는 사다리로는 표현할 수 없는 안전장치도 있다.

```kotlin
val stepEffective = stepped && newDelta.compareTo(currentDelta) != 0
```

**클램프에 막혀 값이 실제로 안 움직였으면 반전으로 세지 않는다.** 주석도 정확하다 —
"반전은 실효 스텝 방향이 뒤집히고 **동시에** 클램프된 스텝이 실제로 delta 를 바꿨을 때만 기록된다."

그리고 상수가 어긋나는 곳이 있다. `AlgorithmConfigCatalog.kt` 의
`spatialJndV2()` 는 `initialDelta = 45°` 인데 **공간 사다리에 45 라는 칸이 없다.**
`constants.ts` 헤더 주석도 사양이 "45° 시작" 이라고 적어 놓고 실제로는 인덱스 5 = 40° 로 시작하며,
그 옆에 `"Q2 회신 대기. 잠정"` 이라고 솔직하게 적혀 있다. 같은 파일의
`frequencyJndV2(referenceFrequency)` 는 기준 주파수를 인자로 받으면서도
`initialDelta` 를 `BigDecimal("30.0000") // 3% of 1000Hz` 로 **하드코딩**한다.
30 Hz 는 500 Hz 에서 6%, 4000 Hz 에서 0.75% 다.

---

## 4. 추정치는 반전점의 평균 — 그런데 추정기가 셋이다

계단법의 표준 추정 방식은 마지막 몇 개 반전점의 평균이다. 이 저장소도 그렇게 한다.

```ts
// staircaseV2.ts — 마지막 6개 반전점 값의 산술평균
const tail = reversalIndices.slice(-window);
return tail.reduce((a, i) => a + presetValues[i], 0) / tail.length;
```

문제는 **같은 값을 계산하는 코드가 셋**이라는 것이다.

| 위치 | 방식 | 쓰이는 곳 |
|---|---|---|
| `staircaseV2.ts` | 마지막 6 반전점 **산술평균** | 화면에 뜨고 DB 에 저장되는 값 |
| `StaircaseValidationStrategy.kt` | 재생 후 **산술평균** | 그 값이 맞는지 판정 |
| `JndStatistics.kt` | **절사 기하평균** + SE + 95% CI + CV | 통계 컬럼(V21 마이그레이션) |

세 번째가 가장 정교하다. 최솟값·최댓값 하나씩 버리고 로그 스케일에서 평균을 낸 뒤
델타법으로 표준오차를 구하고 95% 신뢰구간을 붙인다. 주석은 그 근거로
"계단법의 반전점 값은 로그정규분포를 따르므로 García-Pérez(1998)에 따라 산술평균보다 기하평균이 낫다" 고 적는다.
연구용 앱에서 보기 드물게 제대로 된 코드다.

다만 **화면·검증에 쓰이는 값과 통계 컬럼에 저장되는 값이 서로 다른 방식으로 계산된다.**
크기 차이는 실제로는 작았다 — 내 시뮬레이션에서 마지막 6 반전점이
`1, 0.2, 1, 0.5, 1, 0.5` (%) 였고 산술평균 0.7000% vs 절사 기하평균 0.7071%, **차이 1.0%** 였다.
그러니 이건 "수치가 크게 틀린다" 는 문제가 아니라 **"보고되는 숫자가 어느 정의인지 불분명하다"** 는
일관성 문제다. 논문에 쓸 때는 이 구분이 필요하다.

---

## 5. 검증기를 검증해봤다

이제 본론이다. 백엔드에는 `StaircaseValidationStrategy` 가 있다.
프론트가 보낸 trial 목록을 서버가 **독립적으로 다시 재생**해서 JND 를 재계산하고,
프론트가 보고한 값과 비교한다.

```kotlin
val relDiff = Math.abs(frontJnd - backJnd) / backJnd
if (relDiff > jndDriftRelativeThreshold) { policyDrift = true; ... }   // 기본 0.10
```

판정은 OK / WARN / **DRIFT** 셋. `V2SessionValidator` 의 문서는 DRIFT 를 이렇게 정의한다 —
"JND 10% 이상 차이 … **데이터셋에서 제외 권장**". 즉 이 플래그가 켜지면 그 세션은 버려진다.

좋은 설계다. 클라이언트 계산을 서버가 독립적으로 재현해 대조하는 건 임상·연구 데이터에서 옳은 방향이다.
그래서 **그 검증기가 실제로 무엇을 판정하는지** 확인해보기로 했다.
`staircaseV2.ts` 와 `replayStaircase`, `JndStatistics.calculate` 를 JS 로 그대로 옮기고,
결정론적 LCG(seed 고정)와 3AFC 로지스틱 관찰자를 붙여, **프론트가 실제로 보내는 payload 를 그대로 백엔드에 먹였다.**

### 5-1. 주파수 트랙 — 100% 가 DRIFT 로 찍힌다

프론트가 저장할 때 보내는 payload 는 이렇다.

```ts
// frequency-jnd/page.tsx
const stimVal = referenceHz + referenceHz * (r.percentDelta / 100);   // Hz
...
saveV2Session({
  referenceFrequencyHz: referenceHz,
  jndValue: jnd,          // ← 퍼센트
  trials,                 // ← stimulusValue / referenceValue 는 Hz
});
```

**`jndValue` 는 퍼센트인데, `stimulusValue` 는 Hz 다.**
백엔드는 trial 의 Hz 값으로 재생하니까 당연히 Hz 로 된 JND 를 만들어 낸다.
그리고 퍼센트와 Hz 를 그대로 뺀다.

기본값(기준 700 Hz)으로 한 세션을 돌린 결과:

```
프론트 JND (staircaseV2, 산술평균)      : 0.7000   [단위: %]
백엔드 JND (replayStaircase, 산술평균)  : 4.9000   [단위: Hz]
relΔ = |front-back|/back = 85.7%   임계 10%  → DRIFT (데이터셋 제외 권장)
```

닫힌 형태로 정리하면 더 분명하다. 프론트 값을 $j$ (%) 라 하면 백엔드 값은 $j \cdot f_{ref}/100$ (Hz) 이므로

$$\mathrm{rel}\Delta = \frac{\left| j - j\cdot f_{ref}/100 \right|}{j \cdot f_{ref}/100} = \left| \frac{100}{f_{ref}} - 1 \right|$$

**참가자의 JND $j$ 가 통째로 약분된다.** 즉 이 값은 참가자가 누구든, 얼마나 잘하든 상관없이
기준 주파수만으로 정해지는 상수다. 모든 합법 기준 주파수에서:

```
  f_ref= 125 Hz → relΔ= 20.0%  DRIFT
  f_ref= 250 Hz → relΔ= 60.0%  DRIFT
  f_ref= 500 Hz → relΔ= 80.0%  DRIFT
  f_ref= 700 Hz → relΔ= 85.7%  DRIFT
  f_ref=1000 Hz → relΔ= 90.0%  DRIFT
  f_ref=2000 Hz → relΔ= 95.0%  DRIFT
  f_ref=4000 Hz → relΔ= 97.5%  DRIFT
  f_ref=8000 Hz → relΔ= 98.8%  DRIFT
```

입력 검증이 $f_{ref} \ge 125$ 를 보장하므로 $|100/f_{ref} - 1| \ge 0.2 > 0.10$ 이 항상 성립한다.
**모든 V2 주파수 JND 세션이 예외 없이 "데이터셋에서 제외 권장" 으로 찍힌다.**
$f_{ref} = 100\ \mathrm{Hz}$ 일 때만 우연히 0 이 되는데, 그 값은 사다리 범위 밖이다.

### 5-2. 그 경로를 덮는 유닛 테스트는 초록이다

이게 이 글에서 가장 하고 싶은 이야기다. 해당 경로에는 테스트가 있다.

```kotlin
// V2SessionValidatorTest.kt
// ref=1000, deltas: 1030 → 1020 → 1010 → ... jnd = |1015 - 1000| = 15
// 프론트가 보고한 값 = 14 (백엔드 15와 7% 차이 → OK)
val req = reqOf(SessionType.FREQUENCY_JND_MEASUREMENT, 0, 7, BigDecimal.valueOf(14), trials)
val r = validator.validate(req, AlgorithmConfigCatalog.frequencyJndV2())
assertThat(r.status).isEqualTo(AlgorithmValidationStatus.OK)
```

테스트는 `jndValue = 14` 를 **손으로 적었다.** 14 는 Hz 다.
프론트는 저 자리에 1.5 같은 퍼센트를 넣는다. 테스트가 프론트의 payload 를 쓰지 않고
**"백엔드가 기대하는 형태" 를 스스로 지어냈기** 때문에, 테스트는 통과하면서 동시에
틀린 가정을 공식화한다. 초록불이 오히려 방어막이 됐다.

이건 내가 다른 저장소에서도 몇 번 본 패턴이다 —
**경계를 넘는 계약은 양쪽 중 한쪽만 아는 값으로 테스트하면 안 된다.** 계약 테스트가 필요한 자리다.

### 5-3. 공간 트랙 — 검증기가 다른 것을 세고 있다

공간 트랙은 좌/우를 무작위로 섞는다. 좋은 설계다(응답 편향 제거).

```ts
const sign = Math.random() < 0.5 ? -1 : +1;
const signedDeg = sign * deg;
...
stimulusValue: r.signedDegrees,   // 예: -30, +30, -20, +20 ...
```

그런데 백엔드의 재생 로직은 **`stimulusValue` 가 오르내리는 방향이 바뀌는 지점**을 반전으로 센다.

```kotlin
val cmp = Math.sign(currStim - prevStim)
if (cmp == 0) continue
val currDirection = if (cmp > 0) 1 else -1
if (prevDirection != null && currDirection != prevDirection) reversals.add(prevStim)
```

부호가 매 trial 무작위로 뒤집히니, 이 코드는 **계단의 반전이 아니라 좌우 부호 뒤집힘을 센다.**
참 역치 2.0° 로 200 세션을 돌린 결과:

```
  seed#0: 프론트 반전 8 → JND 2.500°  |  백엔드 "반전" 27 → JND 2.333°  relΔ 7.1%  OK
  seed#1: 프론트 반전 8 → JND 3.500°  |  백엔드 "반전" 31 → JND 4.167°  relΔ 16.0%  DRIFT
  ...
  → OK 90 / DRIFT 110  (55.0% 가 DRIFT)
```

계단은 정확히 8 번 반전했는데 백엔드는 25~31 번을 찾았다.
그리고 **OK 로 통과한 45% 도 우연이다** — 두 평균 모두 어차피 역치 근처를 맴돌기 때문에
가끔 10% 안에 들어올 뿐, 검증기가 옳은 것을 확인해서 통과한 게 아니다.
합격이 불합격만큼이나 정보가 없다.

수정 자체는 어렵지 않아 보인다. `.abs()` 를 재생 시작 지점에서(마지막 평균이 아니라)
적용하면 부호가 사라져 계단 반전만 남는다. 다만 그건 이 저장소 소유자의 판단이라
여기서는 진단까지만 적는다.

### 5-4. 이 저장소는 이미 절반쯤 알고 있었다

`docs/PRD-역순.md` 를 읽다가 이 문장을 봤다.

> `algorithmValidation`(OK/WARN/DRIFT) … 이것은 **"프론트 계산이 서버 재생과 일치하는가"** 를 볼 뿐
> **"참가자가 과제를 제대로 수행했는가"** 는 보지 않는다.

정확한 지적이다. 같은 문서는 사다리 상수가 프론트/백엔드에 이중으로 존재해서
어긋나면 재생 검증이 **"거짓 DRIFT"** 를 뿜을 거라고도 적어 놨다.
내가 측정한 건 그 예측이 이미 현실이 되어 있었다는 것이다.

---

## 6. 세운 가설 중 하나는 틀렸다 — 그래서 기각했다

읽으면서 버그일 거라고 확신한 게 하나 있었다.
프론트는 반전을 셀 때 `direction` 만 보고, `Math.min`/`Math.max` 로 클램프돼서
**인덱스가 실제로 안 움직인 경우를 걸러내지 않는다.** 백엔드는 위에서 본 `stepEffective` 로 거른다.
그러니 사다리 끝에 붙어 있는 참가자는 "유령 반전" 을 쌓을 것 같았다.

시뮬레이션은 모든 조건에서 `클램프 0` 을 뱉었다. 다시 따져보니 도달 불가능하다 —
사다리 꼭대기(인덱스 11)에는 **DOWN 스텝으로만** 들어가므로 그때 `direction = -1` 이고,
거기서 또 맞히면 `direction === 1` 이 아니라 세지 않는다. 바닥(인덱스 0)도 대칭으로 같다.
**클램프 상태에서는 반전 계산 분기 자체가 실행되지 않는다.** 프론트는 여기서 맞다.

버그처럼 생겼지만 버그가 아니었다. 세우고, 돌려보고, 기각했다. 이건 적어 둘 가치가 있다.

---

## 7. 사다리 바닥에서 벌어지는 일

주파수 사다리의 마지막 칸은 0.2% 다. 그보다 잘 듣는 사람은 어떻게 될까.

```
  참역치 0.15% → 프론트 반전 12  JND 0.350%  종료위치 0.2% (바닥 고정)
  참역치 0.05% → 프론트 반전  0  JND null (측정 불가)  종료위치 0.2% (바닥 고정)
```

- 참 역치 0.15% 인 사람은 **0.350% 로 보고된다.** 실제보다 2.3 배 나쁘게 나온다(바닥 검열).
- 참 역치 0.05% 인 사람은 계속 맞히기만 해서 **반전이 한 번도 안 생기고 `jndValue = null`** 이 된다.

두 번째가 더 곤란하다. `computeJndFromReversals` 는 반전이 0 이면 `null` 을 돌려주는데,
**"너무 잘해서 못 쟀다" 와 "세션이 실패했다" 가 같은 `null` 로 저장된다.**
0.2% 는 700 Hz 에서 1.4 Hz 다 — 훈련된 청취자에게 도달 불가능한 값이 아니다.
Wier 등(1977)이 200~8000 Hz 에서 잰 주파수 변별 역치는 주파수와 감각수준에 따라 크게 달라지고,
저역·고감각수준 조건에서는 상당히 작은 값이 나온다.[^wier]

같은 논문이 사다리 자체에 대해서도 시사하는 바가 있다. `FREQUENCY_PRESET_PERCENT` 는
**퍼센트 고정 사다리**, 즉 Weber 분수가 주파수에 무관하게 일정하다고 가정한다.
Wier 등은 바로 그 주파수 의존성이 **유의했다**고 보고했다.[^wier]

---

## 8. 문헌이 짚어 주는 남은 두 가지

**(1) 79.4% 는 명목값이다.** García-Pérez(1998)는 고정 스텝 계단법을 광범위하게 시뮬레이션해서,
Wetherill·Levitt 의 변환 상하법 규칙들이 — 상승/하강 스텝 비 $\delta^-/\delta^+ = 1$ 을 전제하는데 —
**실제로는 명목 목표점에 도달하지 못한다**고 보고했다. 3-down/1-up 이 제대로 수렴하려면
$\delta^-/\delta^+ = 0.7393$ 이어야 하고, 그때 도달하는 지점은 79.4% 가 아니라 **83.15%** 다.
또한 반전 20회 이하의 짧은 고정스텝 계단법은 편향되고 정밀도가 낮다고 지적한다.[^garcia]

흥미로운 건 **이 저장소가 이미 García-Pérez 를 인용하고 있다는 것**이다 —
`JndStatistics.kt` 와 `V21__jnd_confidence_interval.sql` 이 기하평균의 근거로 인용한다.
같은 논문의 수렴점 경고는 아직 반영되지 않았다. 흠잡자는 게 아니라, **이미 읽은 논문 안에
다음 개선 항목이 들어 있다**는 이야기다. 공간 트랙은 반전 8회로 종료하는데, 이건 위 기준으로 짧다.

**(2) 3AFC 선택 자체는 문헌이 지지한다.** Schlauch & Rose(1990)는 2·3·4-구간 강제선택
계단법을 시뮬레이션과 소규모 실측으로 비교해서, 구간 수가 2 → 4 로 늘면 반복 측정의
변산성이 줄거나 유지되고 정확도는 대체로 개선된다고 보고했다. 결론 중 하나는
**"70.7% 를 겨냥한 2IFC 보다 3·4IFC 가, 추가 소요 시간을 감안해도 더 효율적"** 이라는 것이다.[^schlauch]
Leek(2001)의 리뷰도 같은 결과를 정리하면서, 2AFC + 71% 조합이 특히 나쁜 선택이라고 적는다.[^leek]

**즉 inter-asat 이 3AFC + 79.4% 를 고른 것은 문헌 기준으로 좋은 조합이다.**
문서에 남아 있는 "2AFC + 70.7%" 설명이 오히려 열등한 쪽이었고, 코드가 더 나은 쪽으로 갔다.

---

## 9. 정리

읽고 돌려본 결론은 이렇다.

**핵심 알고리즘은 교과서적으로 옳다.** 3-down 1-up, 79.4% 수렴, 반전점 평균 추정,
스텝 축소, 클램프된 반전을 세지 않는 백엔드의 세심함, 절사 기하평균과 95% 신뢰구간까지 —
개인 프로젝트에서 이 정도로 문헌을 따라간 구현은 드물다.

**깨진 건 알고리즘이 아니라 그 알고리즘을 인증하는 장치다.**

- 주파수: 퍼센트 ↔ Hz 단위 불일치로 **모든 세션이 DRIFT**. 참가자와 무관한 상수다.
- 공간: 부호가 실린 자극값 때문에 검증기가 계단 반전이 아니라 좌우 뒤집힘을 센다. **55% 가 DRIFT.**
- 그리고 그 경로의 유닛 테스트는 **초록이면서 틀린 가정을 굳히고 있다.**

교훈을 한 줄로 줄이면: **검증기도 검증 대상이다.**
"서버가 독립적으로 재계산한다" 는 문장은 그 자체로 신뢰의 근거가 되지 못한다.
독립적으로 재계산해서 **엉뚱한 걸 세고 있을 수도** 있고,
그때 나오는 라벨(DRIFT = 데이터셋 제외)은 좋은 데이터를 버리게 만든다.
조용히 실패하는 쪽이 시끄럽게 실패하는 쪽보다 늘 비싸다.

### 재현

내가 돌린 두 스크립트는 `staircaseV2.ts` · `StaircaseValidationStrategy.replayStaircase` ·
`JndStatistics.calculate` 를 JS 로 이식하고 seed 를 고정한 것이다.
읽은 코드는 아래 다섯 파일이면 충분하다.

```bash
git clone https://github.com/MyoungSoo7/inter-asat && cd inter-asat
git show e40f057:frontend/src/lib/staircaseV2.ts
git show e40f057:frontend/src/lib/constants.ts
git show e40f057:frontend/src/app/\(trainee\)/training/v2/frequency-jnd/page.tsx
git show e40f057:src/main/kotlin/.../validation/StaircaseValidationStrategy.kt
git show e40f057:src/main/kotlin/.../service/JndStatistics.kt
```

---

## References

[^levitt]: Levitt, H. (1971). *Transformed up-down methods in psychoacoustics.* **Journal of the Acoustical Society of America, 49**(2), 467–477. [doi:10.1121/1.1912375](https://doi.org/10.1121/1.1912375) (PMID 5541744). 수렴 조건 $P^n = 0.5$, 2-down 1-up 의 0.707, 스텝 크기 축소 권고의 1차 출처.

[^garcia]: García-Pérez, M. A. (1998). *Forced-choice staircases with fixed step sizes: asymptotic and small-sample properties.* **Vision Research, 38**(12), 1861–1881. [doi:10.1016/S0042-6989(97)00340-4](https://doi.org/10.1016/s0042-6989(97)00340-4) (PMID 9797963). $\delta^-/\delta^+ = 0.7393$ 과 83.15%, 짧은 고정스텝 계단법의 편향. 이 저장소가 기하평균 근거로 이미 인용 중인 논문.

[^schlauch]: Schlauch, R. S., & Rose, R. M. (1990). *Two-, three-, and four-interval forced-choice staircase procedures: Estimator bias and efficiency.* **Journal of the Acoustical Society of America, 88**(2), 732–740. [doi:10.1121/1.399776](https://doi.org/10.1121/1.399776) (PMID 2212297).

[^leek]: Leek, M. R. (2001). *Adaptive procedures in psychophysical research.* **Perception & Psychophysics, 63**(8), 1279–1292. [doi:10.3758/BF03194543](https://doi.org/10.3758/bf03194543). `AlgorithmConfigCatalog` 주석이 인용하는 리뷰.

[^wier]: Wier, C. C., Jesteadt, W., & Green, D. M. (1977). *Frequency discrimination as a function of frequency and sensation level.* **Journal of the Acoustical Society of America, 61**(1), 178–184. [doi:10.1121/1.381251](https://doi.org/10.1121/1.381251) (PMID 833369). 200–8000 Hz · 5–80 dB SL, 2구간 강제선택 적응 절차. 저장소의 `NORMATIVE_JND` 상수 출처 중 하나.

**코드 출처:** [MyoungSoo7/inter-asat](https://github.com/MyoungSoo7/inter-asat) `main` @ `e40f057` (public).
인용한 문장 중 `docs/PRD-역순.md` 의 두 문단은 저장소 자체 문서이며, 내 분석보다 앞선다.
