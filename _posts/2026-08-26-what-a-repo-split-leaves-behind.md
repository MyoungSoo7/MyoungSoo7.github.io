---
layout: post
title: "리포를 쪼개면 코드는 따라오고 검사는 남는다"
date: 2026-08-26 15:26:22 +0900
categories: [engineering]
tags: [monorepo, repository-split, ci, gradle, github-actions, harness]
---

## 쪼갠 뒤에 남는 것

2026년 8월 25일, 커머스 절반을 떼어 [`MyoungSoo7/shop`](https://github.com/MyoungSoo7/shop) 이라는 별도 저장소로 옮겼다.
원래 저장소는 정산·여신·카드까지 한 덩어리로 들고 있었고, 거기서 주문·결제·포인트·기프트카드와 그걸 받아 처리하는 운영 서비스만 잘라 냈다.
남은 것은 `order-service` · `operation-service` · `gateway-service`, 그리고 Gradle composite build 로 물린 `shared-common` 이다.

코드를 옮기는 일은 어렵지 않았다. 컴파일러가 도와준다. 안 따라온 심볼은 빨간 줄로 나온다.

**안 따라온 것은 코드가 아니라 검사였다.** 그리고 검사는 안 따라와도 빨간 줄이 안 나온다.
정확히 말하면, *아무것도 검사하지 않게 된 검사* 는 초록불을 낸다. 통과했다고 말한다.

이 글은 쪼갠 뒤 사흘 동안 그 저장소에서 실제로 찾아낸 다섯 건의 기록이다.
새로운 이론은 없다. 다만 "리포 분리"의 비용이 어디에 청구되는지에 대한 실측치다.

---

## 1. 유령을 가리키는 명단

저장소 규율 게이트 중에 자바 컨트롤러·매핑 수를 세는 게 있다. 원본 저장소 시절에 만든 것이고, 스캔할 서비스 목록을 **손으로 적어** 두었다.

분리 후 그 목록에는 여덟 개 이름이 있었다. `settlement-service`, `finance-service`, `company-service`, `external-data-service`, `education-service`, `board-service` — **이 중 여섯 개는 새 저장소에 존재한 적이 없다.**

문제는 목록이 틀렸다는 게 아니다. 목록이 틀렸을 때 **무슨 일이 일어났는가** 다.
디렉터리를 훑는 함수는 없는 경로에 대해 예외를 던지지 않고 빈 배열을 돌려줬다. 게이트는 0개 파일을 스캔했고, 0개 파일에서 0건의 위반을 찾았고, 통과했다.

> 0건 위반과 0건 검사는 리포트에서 똑같이 생겼다.

고칠 때 이름 여섯 개를 지우는 것으로 끝내지 않았다. 명단을 손으로 적는 한 같은 일이 다시 일어나기 때문에, `settings.gradle.kts` 에서 파생시켰다 ([`c53a820`](https://github.com/MyoungSoo7/shop/commit/c53a820)).
빌드가 아는 모듈 목록이 곧 게이트가 스캔할 목록이다. 모듈을 추가하고 게이트에 안 적는 상태가 성립하지 않는다.

## 2. 정직하게 깨진 쪽 — 대조군

같은 분리에서 정반대로 동작한 사례가 하나 있다. 대조군으로서 중요하다.

이벤트 계약 픽스처 테스트는 배포 중인 토픽 목록을 `List.of(...)` 로 명시해 둔다. 분리하면서 스키마·샘플 리소스는 커머스 20종만 남기고 지웠는데, **목록에는 정산·대출·카드 토픽 31개가 그대로 남아 있었다.**

이건 조용히 통과하지 않았다. **23개 케이스가 "픽스처가 없다"로 즉시 깨졌다** ([`dfd30f8`](https://github.com/MyoungSoo7/shop/commit/dfd30f8)).

두 사례의 차이는 규율의 차이가 아니다. **구조의 차이다.**

| | 스캔하는 게이트 | 명시 목록 게이트 |
|---|---|---|
| 대상이 사라지면 | 빈 집합 → 통과 | 조회 실패 → 실패 |
| 대상이 추가되면 | 자동 포함 | 목록에 없으면 누락 |

어느 쪽도 그 자체로 우월하지 않다. 둘 다 있어야 한다 — **스캔 결과가 비면 실패시키고, 명시 목록과 실제 리소스를 서로 대조하면** 된다.
지금 그 테스트에는 `topicListCoversEveryShippedSchema()` 가 붙어 있다. 목록과 디스크를 맞춰 보고, 어느 한쪽만 바꾸면 깨진다.

## 3. 갈라진 게이트 — composite build 는 상속하지 않는다

커버리지 게이트의 제외 목록이 두 군데에 따로 적혀 있었다. 루트 `build.gradle.kts` 는 어댑터·config·util 등 22개 패턴을 제외했고, `shared-common/build.gradle.kts` 는 `**/common/pdf/**` 하나만 제외했다.

이게 그냥 중복이 아닌 이유는 `shared-common` 이 서브프로젝트가 아니라 `includeBuild("shared-common")` 로 물린 **독립 빌드**이기 때문이다.
Gradle 문서는 이 격리를 명시한다 — included build 는 루트 빌드나 다른 included build 와 **어떤 설정도 공유하지 않으며**, 각각 독립적으로 구성되고 실행된다.[^1]
즉 루트의 `subprojects { }` 블록은 여기 닿지 않는다. 한쪽을 고쳐도 다른 쪽은 그대로 남는다. 구조적으로 그렇게 되어 있다.

갈라진 결과는 "더 엄격"이 아니었다. `shared-common` 의 라인 커버리지는 **81%** 였고 선언된 문턱은 **90%** 였다. 넘지 못하는 게이트였다.

그런데 왜 빌드가 안 깨졌나. JaCoCo Gradle 플러그인 문서가 답을 준다 — `JacocoCoverageVerification` 태스크는 **기본적으로 `check` 의 의존이 아니다.**[^2] 이 저장소는 그걸 명시적으로 물려 두었지만(`tasks.named("check") { dependsOn(...) }`), `test` 는 여전히 그 태스크에 의존하지 않는다.
그래서 `:shared-common:test` 는 계속 초록불이었다. **문턱을 못 넘는 게이트는 아무도 안 켜게 되고, 안 켜진 게이트는 없는 게이트다.**

고친 방식은 제외 목록을 [`gradle/coverage-excludes.txt`](https://github.com/MyoungSoo7/shop/blob/main/gradle/coverage-excludes.txt) 하나로 모으고, 두 빌드가 **그 파일만** 읽게 한 것이다. `shared-common` 쪽은 자기 `rootDir` 이 저장소 루트가 아니므로 `rootDir.resolveSibling("gradle")` 로 올라간다.
그리고 빌드 스크립트에 패턴을 직접 적으면 깨지는 게이트를 하나 더 붙였다 ([`9ab8232`](https://github.com/MyoungSoo7/shop/commit/9ab8232)). 정본을 만들어 놓고 정본을 우회할 수 있게 두면 드리프트는 다시 시작된다.

## 4. 없는 파일을 부르는 단계

`verify.sh` — 커밋 전에 돌리는 전체 검증 스크립트 — 가 `harness-audit.mjs` 를 호출하고 있었다.
그 파일은 **이 저장소의 어느 커밋에도 존재한 적이 없다.** 원본 저장소에서 스크립트만 따라오고 대상은 안 따라온 것이다.

여기에 두 번째 층이 있었다. 그 단계가 실패해도 아무도 몰랐던 이유는, 그걸 강제하는 `pre-commit` 훅이 **한 번도 실행된 적이 없기** 때문이다.
`verify.sh` 와 `pre-commit` 둘 다 git 인덱스에 `100644` 로 들어가 있었다. git 문서는 이 경우의 동작을 한 줄로 적어 둔다 — 실행 비트가 없는 훅은 **무시된다**.[^3]
에러도, 경고도 없다. 그냥 안 돈다.

로컬 워킹트리에서 `chmod +x` 를 해도 인덱스 모드는 안 바뀐다. `git update-index --chmod=+x` 로 인덱스에 기록해야 다른 클론에서도 실행된다 ([`3e25214`](https://github.com/MyoungSoo7/shop/commit/3e25214)).

## 5. 게이트여야 할 것이 각주로 박제된 경우

토픽 카탈로그에는 21개가 등재돼 있는데 계약 스키마는 20개였다. `lemuel.education.course_published` 하나가 계약 없이 발행되고 있었다.

이 사실은 **모르고 있던 게 아니었다.** `SPEC.md` 와 시퀀스 다이어그램 문서 양쪽에 "카탈로그가 하나 더 많은 이유는…" 이라는 각주로 적혀 있었다. 심지어 `ls ... | wc -l` 로 세어 확인하라는 검증 절차까지 함께 적혀 있었다.

그 절차를 돌리는 것은 사람이다. 그리고 사람은 그걸 안 돌린다.

> 각주는 결함을 설명한다. 막지는 않는다.

하필 이 토픽은 소비자가 저장소 밖에 있어서, 필드가 바뀌어도 저장소 안에서는 아무것도 안 깨진다. **계약이 유일한 경보인 자리에서 계약이 빠져 있었다.**
스키마와 정본 샘플을 만들고, 카탈로그와 스키마가 1:1 인지 대조하는 게이트를 붙였다. 그 게이트는 문서 본문에 적힌 숫자까지 실제와 대조한다 — 각주를 기계가 읽게 만든 셈이다 ([`58f3411`](https://github.com/MyoungSoo7/shop/commit/58f3411)).

---

## 곁가지: CI 경로 필터도 같은 병이었다

분리 직후 CI 를 새로 짜면서 `github.event.before` 를 기준으로 변경 경로를 판정하게 했다. "직전 푸시 이후 바뀐 파일만 검사한다"는 뜻이다.

전제가 하나 깔려 있다 — **모든 푸시가 실행을 완주한다**는 것. GitHub Actions 의 concurrency 그룹은 기본값에서 그룹당 대기 실행을 하나만 허용하고, 새 실행이 큐에 들어오면 기존 대기 실행을 **취소하고 그 자리를 차지한다.**[^4]
빠르게 세 번 푸시하면 가운데 푸시의 실행이 취소되고, 그 구간의 diff 는 **누구도 평가하지 않은 채로 지나간다.**

고친 기준은 "직전 푸시"가 아니라 **"마지막으로 성공한 실행의 커밋"** 이다. 취소·실패한 구간은 다음 실행의 누적 diff 안에 그대로 남는다.
실측 로그에도 그렇게 찍힌다: `변경 감지 기준: 마지막 green 커밋 cae4741... (누적 diff)`.

---

## 하나의 문법

다섯 건은 서로 다른 층에서 났다. Gradle, git, GitHub Actions, 노드 스크립트, 마크다운 문서.
공통점은 기술이 아니라 **실패 모드의 모양**이다.

1. **빈 집합은 통과처럼 보인다.** 없는 디렉터리를 스캔한 결과와 위반 없는 결과는 구분되지 않는다.
2. **격리는 편의가 아니라 계약이다.** composite build 든 별도 워크플로든, 격리된 것은 고쳐도 같이 안 고쳐진다.
3. **비활성은 침묵한다.** 실행 비트 없는 훅, 못 넘는 문턱, 취소된 실행 — 셋 다 에러를 내지 않는다.
4. **문서는 게이트가 아니다.** 결함을 정확히 서술한 각주가 있어도 결함은 그대로 있다.

리포 분리에서 실제로 비싼 건 코드 이동이 아니다. **검사의 전제가 조용히 거짓이 되는 것**이다.
그리고 그 거짓은 빨간불이 아니라 초록불로 나타난다.

그래서 이번에 붙인 게이트들은 전부 **고치기 전 상태에서 빨갛게 뜨는지 먼저 확인**했다. 커버리지 정본 게이트는 이전 커밋의 파일로 되돌리면 7건 중 3건이 깨지고, 계약 정합 게이트는 스키마를 옮겨 두면 5건 중 2건이 깨진다.
통과만 확인한 게이트는 통과를 증명하지 않는다. 현재 이 저장소의 규율 게이트는 52개 스위트 379건이고, 전부 초록이다 — 다만 그 초록이 무엇을 봤는지 말할 수 있게 됐다는 게 이번 작업의 전부다.

## 아직 안 풀린 것

정직하게 남겨 둔다.

- **마이그레이션 이력은 통째로 따라왔다.** 주문 서비스에 156개, 운영 서비스에 20개. 이 중 원본 저장소 시절 스키마를 만드는 것이 얼마나 되는지, 그 테이블들이 지금도 쓰이는지 **검사하는 것이 아무것도 없다.** 위 다섯 건과 정확히 같은 모양의 구멍이고, 아직 안 막았다.
- 게이트 자체의 커버리지는 여전히 사람이 정한다. "무엇을 검사해야 하는가"를 기계가 알아내지는 못한다. 이 글의 다섯 건도 결국 사람이 뒤져서 찾았다.

---

## References

[^1]: Gradle, "Composite Builds (Included Builds)", *Gradle User Manual*. "Included builds do not share any configuration with the root build or other included builds." <https://docs.gradle.org/current/userguide/composite_builds.html>
[^2]: Gradle, "The JaCoCo Plugin", *Gradle User Manual*. "The `JacocoCoverageVerification` task is not a task dependency of the `check` task provided by the Java plugin." <https://docs.gradle.org/current/userguide/jacoco_plugin.html>
[^3]: Git, "githooks(5)", *Git Documentation*. 실행 비트가 설정되지 않은 훅은 무시된다. <https://git-scm.com/docs/githooks>
[^4]: GitHub, "Workflow syntax for GitHub Actions — `concurrency`", *GitHub Docs*. 기본값 `queue: single` 에서는 그룹당 하나의 `pending` 실행만 허용되며, 새 실행이 큐에 들어오면 기존 대기 실행은 취소된다. <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>

본문에 인용한 커밋·파일은 모두 공개 저장소 [`MyoungSoo7/shop`](https://github.com/MyoungSoo7/shop) 에서 직접 확인할 수 있다.
수치(커버리지 81%, 게이트 379건, 마이그레이션 156/20건)는 2026-08-26 기준 해당 저장소 `main` 에서 실측한 값이다.
