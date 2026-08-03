---
layout: post
title: "0건을 막으면서 초록으로 보이는 게이트 — lemuel-xr 안전 규칙을 실행 파일로 옮긴 기록"
date: 2026-08-04 06:30:00 +0900
categories: [software-engineering, safety, testing, lemuel-xr]
tags:
  [
    vacuous-green,
    mutation-testing,
    test-oracle,
    korean-nlp,
    content-safety,
    spring-boot,
    kotlin,
  ]
---

> **한 줄 요약.** 안전 규칙을 YAML 에 `id` 로 선언해 두면 리포트는 초록으로 뜬다. 그런데 그 `id` 를 읽는 코드가 없으면 그 게이트는 **0건을 막는다.** lemuel-xr 의 신규 인물 5명(아브라함·다니엘·에스더·야곱·베드로) 작업에서 이 상태를 걷어내고, 게이트를 산문에서 실행 파일로 옮긴 기록이다. 마지막에 **아직 살아 있는 과차단 1건**을 실측 그대로 남긴다.

## 1. 증거 경계 — 무엇을 실측했고 무엇은 못 했나

먼저 이 글이 어디까지 주장하는지 못 박는다. 안전에 관한 글에서 이 문단을 생략하면 나머지 전부가 마케팅이 된다.

| 항목                      | 상태                                                                                                                   |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 게이트 러너 5인물 판정    | 실행함 — 전원 `PASS 19 / FAIL 0 / BLOCKED 8`                                                                           |
| 게이트 러너 자신의 테스트 | 실행함 — `49/49` (게이트 27개 · RED 픽스처 27 · GREEN 6)                                                               |
| 백엔드 테스트 443건       | **로컬 343건만 통과 확인.** 99건은 Testcontainers 기반이라 로컬에 Docker 가 없어 미실행(1건 skip). 이 99건은 CI 몫이다 |
| 런타임 토큰 543종 매칭    | `ForbiddenTokenScanner.kt` 의 정규화 규칙을 그대로 옮긴 파이썬 미러로 확인                                             |
| "R2/R3 위반이 없다"       | **주장하지 않는다.** 게이트가 보증하는 것은 _선언된 문자열의 정확한 표층형이 대상에 없다_ 까지다                       |

마지막 줄이 이 글의 전제다. 이건 러너가 매 실행마다 스스로 출력하는 문구이기도 하다.

## 2. lemuel-xr 과 R2/R3 가 뭔가

lemuel-xr 은 성경 인물 서사를 VR/AR 로 체험하는 예방 영적 교육 프로젝트다. **치료 도구가 아니다.** 그래서 사용자에게 노출되는 모든 텍스트에 정신건강 안전선이 걸려 있고, 그중 두 축이 이 글의 대상이다.

- **R2 — 고난의 의미부여 금지.** "이 고난에는 뜻이 있다", "당신을 겸손하게 하시려고 실패를 주셨다" 류. 절망 상태의 사용자에게 **책임을 전가**한다.
- **R3 — 회복 압박 금지.** "빨리 회복해서 다시 일어나라", "포기하지 않으면 결국 받는다" 류. 회복을 **성과로 만든다.**

금지 이유가 신학이 아니라 정신건강이라는 점이 중요하다. 신학 논쟁은 `disputed_points` 로 따로 기록하고, 이 두 축은 맥락과 무관하게 막는다.

집행 수단은 저작 YAML(`content/{인물}/scene*.yml`)의 `lint_forbidden_tokens` 다. 각 Scene 이 자기가 막을 문자열을 들고 있다.

## 3. vacuous green — 이 저장소의 재발 사고 유형

문제는 이렇게 생긴 노드다.

```yaml
- id: R3_no_reorientation_pressure
  description: "회복 압박 어휘 0건"
```

읽으면 게이트다. 리포트에도 게이트로 집계된다. 그런데 `lint_forbidden_tokens` 도 `enforcement: structural` 도 없다. **어떤 코드도 이 노드를 읽지 않는다.** 검사 대상 0건을 순회하고 0건 위반으로 초록이 된다.

이건 커버리지 지표의 고전적 실패와 정확히 같은 자리다. Petrovic·Ivanković·Fraser·Just 의 ICSE 2021 논문은 구글에서 6년간 축적한 약 1,500만 개 mutant 데이터를 분석하면서 이렇게 적는다.

> "Code coverage is also easily fooled, as it only determines whether code has been executed, regardless of how well its behavior has been checked."
> — [Petrovic et al., _Does mutation testing improve testing practices?_, ICSE 2021](https://homes.cs.washington.edu/~rjust/publ/mutation_testing_practices_icse_2021.pdf)

실행됐다는 사실과 **거동이 검사됐다는 사실**은 다르다. 선언된 게이트는 "실행됐다" 쪽에 해당하고, 집행 수단이 붙어야 "검사됐다" 가 된다.

Zhi 와 Garousi 는 이 간극을 테스트 코드 쪽에서 Inadequate-Assertion(IA) 문제로 정식화했다. 오픈소스 3개 프로젝트를 mutation 분석과 커버리지 분석으로 훑은 결과, **IA 문제는 흔했고 테스트 코드가 복잡할수록 발생률이 높았다**([Zhi & Garousi, ICSTW 2013](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/180440441/Junji_Zhi_Vahid_Garousi_REGRESSION_13_camera_ready.pdf)). 실행은 하되 확인은 안 하는 코드는 사람이 손으로 쓰는 곳 어디서나 자란다. 안전 게이트라고 예외가 아니다.

Papadakis 등의 survey 는 여기에 쓸 만한 어휘를 하나 더 준다. mutant 를 "약하게 죽인다(weak kill)" 는 것은 실행 직후 프로그램 상태가 달라졌다는 뜻이고, "강하게 죽인다(strong kill)" 는 그 차이가 **관측 가능한 출력까지 전파됐다**는 뜻이다. 둘 사이에는 failed error propagation 이 있어 형식적 포함관계가 성립하지 않는다([Papadakis et al., _Mutation Testing Advances: An Analysis and Survey_](https://mutationtesting.uni.lu/survey.pdf)). 같은 survey 가 정리한 표에서 Chekam 등(2017)은 **strong mutation 은 결함 발견과 강하게 연결되지만 statement·branch·weak mutation 은 약하게 연결된다**고 보고한다.

선언만 있는 게이트는 weak kill 이다. 상태는 바뀌었다(YAML 에 규칙이 생겼다). 출력까지는 전파되지 않는다(빌드가 절대 붉어지지 않는다).

## 4. 이번 작업의 종착 상태

신규 5인물의 R2/R3 노드를 전수 세면 이렇다.

| 인물     | R2/R3 게이트 | 집행 수단 보유 |
| -------- | ------------ | -------------- |
| 아브라함 | 9            | 9              |
| 다니엘   | 8            | 8              |
| 에스더   | 5            | 5              |
| 야곱     | 7            | 7              |
| 베드로   | 5            | 5              |
| **합계** | **34**       | **34**         |

집행 수단은 둘 중 하나다. `lint_forbidden_tokens: [...]` 로 막을 문자열을 명시하거나, `enforcement: structural` + `structural_check:` 로 구조 자체를 강제하거나. 어느 쪽도 없는 노드는 이제 없다.

## 5. 한국어 형태론 — 어간을 자르면 그 축의 위로가 함께 죽는다

토큰을 고를 때 부딪힌 것이 이거다. **한국어의 부정은 어간 뒤에 붙는다**(`-지 않/못`, `-가 아니`). 그래서 어간에서 자른 토큰은 그 축의 _정당한 부정형 위로_ 를 반드시 삼킨다.

`빨리 회복` 이라는 토큰을 예로 들면:

| 문장                            | 의도                             | 어간 토큰의 판정 |
| ------------------------------- | -------------------------------- | ---------------- |
| 빨리 회복하세요                 | R3 위반 — 회복 압박              | 차단 ✅          |
| 빨리 회복하셔야죠               | R3 위반 — 회복 압박              | 차단 ✅          |
| **빨리 회복하지 않아도 됩니다** | **R3 을 정면으로 해제하는 위로** | **차단 ❌**      |

세 번째 줄이 문제다. 이 문장은 막아야 할 대상이 아니라 **막는 이유 그 자체**다. 그런데 어간 토큰은 셋을 구분하지 못한다.

그래서 이번에 새로 넣은 토큰은 전부 **명령·당위 어미를 최소 한 음절 더 포함**하게 만들었다. `기다리` 가 아니라 `조금만 더 기다리`, `용서해` 가 아니라 `용서해야`. 검증은 mustBlock 만으로 부족하다 — 사전형과 높임 활용형 양쪽을 막는 케이스, 그리고 **같은 축의 부정형 위로가 통과하는지 확인하는 mustPass 케이스**를 짝으로 넣었다.

```kotlin
// mustBlock — 같은 위반을 높임 활용형으로 바꿔도 막힌다
"조금만 더 기다리시면 됩니다.",   // 아브라함
"관계는 회복되어야죠.",            // 야곱

// mustPass — 부정으로 꺼내는 위로는 열려 있어야 한다
"용서하지 않으셔도 됩니다. 아직 안 해도 됩니다.",  // 야곱
"물러서도 괜찮습니다. 그건 배신이 아닙니다.",       // 다니엘
```

mustPass 가 없으면 토큰을 넓힐수록 테스트가 더 초록이 된다. 그 방향으로 최적화하면 결국 아무 말도 못 하는 앱이 나온다.

## 6. 전역 목록이라는 제약 — 과차단은 안전이 아니라 손실

런타임 금지 토큰은 `application.yml` 한 곳에 있고 **전 인물 공통**이다. 이번에 저작 층과 동기화하면서 66종에서 **543종**으로 늘렸다.

```yaml
safety:
  forbidden-tokens:
    list: "가장 좋은 것으로,가족까지 잃게 될,감당할 만하니, 감사가 부족, ..."
```

전역이라는 사실이 설계 제약을 만든다. 아브라함 서사를 위해 넣은 토큰이 에스더 서사의 정당한 문장을 막는다. 그래서 토큰 하나를 넓히는 결정은 **다섯 서사 전부에 대한 결정**이다.

스캐너의 매칭 규칙도 여기 맞춰져 있다.

```kotlin
private fun normalize(s: String): String = s.trim().replace(WHITESPACE, " ")
```

토큰과 대상 **양쪽** 에 같은 정규화를 걸고 `indexOf` 한다. LLM 출력은 같은 표현도 공백 수가 들쭉날쭉해서, 정규화 없이 `contains` 만 하면 `믿음이  부족`(두 칸)을 놓친다. 실제로 543종 중 108종이 앞뒤 공백이 붙은 채 저장돼 있는데, `trim()` 덕분에 무해하다. 게이트 러너가 이 규칙을 **정확히 미러링**해야 하는 이유도 같다. 러너가 런타임보다 느슨하면 vacuous green 이고(더 나쁘다), 엄격하면 false red 다.

## 7. 게이트를 실행 파일로 — PASS / FAIL / **BLOCKED**

게이트 러너(`scripts/newchar_gates.py`)의 핵심 설계 결정은 판정이 **3값**이라는 것이다.

- `PASS` — 검사했고 위반이 없다
- `FAIL` — 검사했고 위반이 있다
- `BLOCKED` — **판정 불가.** 검사에 필요한 입력이 없다

`BLOCKED` 가 이 도구의 존재 이유다. 예를 들어 배제 목록(`exclusions`)이 정의되지 않은 상태에서 "배제 위반 0건" 은 아무 의미가 없다. 순회를 0회 돌고 0건을 보고한 것뿐이다. 이걸 `PASS` 로 찍는 순간 도구 자체가 vacuous green 을 생산한다.

그래서 러너는 `FAIL` 과 `BLOCKED` 모두에 대해 종료 코드를 0이 아닌 값으로 낸다. 그리고 매 실행마다 출력 하단에 이 문장을 박는다.

```
⚠️ BLOCKED 는 PASS 가 아니다 — 판정 불가 상태다. 통과로 보고하지 말 것.
⚠️ PASS 의 주장 범위: '선언된 토큰의 정확한 표층형이 대상에 없다' 까지다. 'R2/R3 위반이 없다' 가 아니다.
```

5인물 전원의 현재 판정이 `PASS 19 / FAIL 0 / BLOCKED 8` 인데, 이 BLOCKED 8건은 **고치지 않은 채로 두는 것이 정답**이다. seed 층 입력이 실제로 없기 때문이다. 설정 키를 지어내서 초록으로 만들면 그게 정확히 이 글이 걷어내려는 상태가 된다.

## 8. 게이트 자신의 테스트 — RED/GREEN 짝

게이트를 실행 파일로 만들면 게이트가 코드가 되고, 코드에는 버그가 있다.

실제로 이번에 하나 나왔다. 신학 검토자 주석(`theology_footer_refs`)은 **금지 표현을 인용하는 것이 임무**다. "이런 문장은 R2 가스라이팅이므로 막는다" 라고 쓰려면 그 문장을 적어야 한다. 그런데 러너가 이걸 사용자에게 렌더되는 leaf 로 세어 false red 를 냈다.

쉬운 수정이 두 개 있었고, 둘 다 버렸다.

- **키 이름 화이트리스트** — 검토자 주석에만 쓰이는 키 이름을 예외 처리. 같은 이름이 다른 곳에 생기는 순간 구멍이 된다.
- **Kotlin 정의 미러링** — 사용자 노출 키 목록을 복제. `wait_label`·`disclose_label` 같은 **실제 노출 라벨**이 함께 빠진다.

채택한 것은 `scalar_nodes()` 가 값과 함께 **조상 경로**를 내보내게 하고, 카브아웃을 서브트리 단위로 거는 방식이다. 키 이름이 아니라 _부위_ 로 좁힌다.

```python
def _in_nonuser_subtree(key, anc, subtrees):
    """조상 경로가 검토자 주석 서브트리에 들어 있고, 그 leaf 가 `*_ko` 가 아닌가."""
    if key.endswith("_ko"):
        return False
    return any(a in subtrees for a in anc)
```

`*_ko` leaf 를 계속 검사하는 게 핵심이다. 같은 서브트리 안에 `raw_text_ko`·`note_ko` 가 살고, 이것들은 실제로 렌더된다. 그리고 카브아웃과 함께 **GREEN/RED 짝** 을 넣었다. GREEN 은 검토자 주석에 금지 표현을 심고 통과를 기대하고, RED 는 같은 서브트리의 `note_ko` 에 심고 실패를 기대한다. 카브아웃이 너무 넓어지면 RED 케이스가 즉시 깨진다.

이렇게 게이트 자체 테스트가 47개에서 **49개**가 됐고, 전부 통과한다.

## 9. 아직 살아 있는 것

여기가 이 글에서 제일 중요한 절이다.

**§5 에서 예로 든 `빨리 회복` 은 지금도 런타임 목록에 그대로 있다.** 즉 lemuel-xr 은 현재 "빨리 회복하지 않아도 됩니다" 를 **차단한다.** 확인 방법은 간단하다. `application.yml` 의 543종에 스캐너와 같은 정규화를 걸고 그 문장을 넣어 보면 `빨리 회복` 에 걸린다.

이 토큰은 이번 작업에서 만든 게 아니라 엘리야 서사의 오래된 자산이고, 엘리야 문서는 이 토큰이 무엇을 막으려는지 여러 곳에 적어 뒀다. 그런데 **그 대가로 무엇이 함께 막히는지는 어디에도 적혀 있지 않다.** 고치려면 저작 층(`content/elijah/*.yml`)과 런타임을 함께 좁혀야 하고, 그건 이번 커밋 범위 밖이다.

같은 맥락에서, 이미 사람 승인을 받고 머지된 두 인물도 러너를 돌리면 붉다.

| 인물   | 판정                           |
| ------ | ------------------------------ |
| 엘리야 | `PASS 15 / FAIL 4 / BLOCKED 8` |
| 솔로몬 | `PASS 17 / FAIL 2 / BLOCKED 8` |

이건 이번 작업의 회귀가 아니라 **러너가 새로 보이게 만든 기존 부채**다. 도구를 만들면 도구가 먼저 하는 일은 좋은 소식을 주는 게 아니라 빚 명세서를 뽑는 것이다.

그리고 게이트 전체가 못 막는 것이 하나 더 있다. **유의어 재작성**이다. 문자열 매칭이므로 같은 뜻을 다른 표층형으로 쓰면 그대로 통과한다. 이건 결함이 아니라 방법의 한계이고, 저장소는 이걸 `knownBypass` 테스트로 **명시적으로 기록**한다. 막지 못하는 것을 막는다고 적지 않는 것이 여기서의 규율이다.

## 10. 남는 것

- 선언은 게이트가 아니다. 그 선언을 읽는 코드가 있어야 게이트다.
- 한국어에서 어간 절단 토큰은 **그 축의 위로를 함께 죽인다.** mustBlock 만 있는 테스트는 이 손실을 영영 못 본다.
- 판정은 2값이 아니라 3값이어야 한다. `BLOCKED` 를 `PASS` 로 접는 순간 도구가 사고의 공범이 된다.
- 게이트를 코드로 만들면 게이트에도 RED/GREEN 이 필요하다.
- 그리고 무엇을 못 막는지 적어 두는 것이, 무엇을 막는지 적는 것보다 대체로 더 유용하다.

---

## References

1. Goran Petrovic, Marko Ivanković, Gordon Fraser, René Just. **"Does mutation testing improve testing practices?"** _IEEE/ACM 43rd International Conference on Software Engineering (ICSE)_, 2021. <https://homes.cs.washington.edu/~rjust/publ/mutation_testing_practices_icse_2021.pdf>
2. Junji Zhi, Vahid Garousi. **"On Adequacy of Assertions in Automated Test Suites: An Empirical Investigation."** _IEEE 6th International Conference on Software Testing, Verification and Validation Workshops (ICSTW)_, 2013, pp. 382–391. DOI: [10.1109/ICSTW.2013.49](https://doi.org/10.1109/ICSTW.2013.49) · [post-print (QUB Research Portal)](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/180440441/Junji_Zhi_Vahid_Garousi_REGRESSION_13_camera_ready.pdf)
3. Mike Papadakis, Marinos Kintis, Jie Zhang, Yue Jia, Yves Le Traon, Mark Harman. **"Mutation Testing Advances: An Analysis and Survey."** _Advances in Computers_. <https://mutationtesting.uni.lu/survey.pdf> — weak/firm/strong mutation 구분 및 failed error propagation 논의는 §2, 커버리지 기준과 결함 발견의 관계를 정리한 표(Chekam et al. 2017 포함)는 §3.

_본문의 판정 수치는 모두 2026-08-04 시점 `MyoungSoo7/lemuel-xr` main 브랜치에서 실행한 결과다. Testcontainers 기반 99건은 로컬 미실행이라 이 글의 근거에서 제외했다._
