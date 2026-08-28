---
layout: post
title: "무기한 예외를 문법적으로 불가능하게 만들기 — 가드 19종을 직접 돌려봤다"
date: 2026-08-28 18:28:24 +0900
categories: [engineering]
tags: [guard, ci, pre-commit, spring, kafka, transaction, verification]
---

정산 서비스에 규칙 엔진 하나(`guard.mjs`)를 붙여 두고 쓴 지 좀 됐다. 설명은 여러 번 했는데 실제로 무엇을 통과시키고 무엇을 막는지 재본 적은 없어서, 오늘 직접 돌려봤다. 결과부터 적으면 **제일 잘 만든 부분은 규칙이 아니라 예외 처리**였고, **설명과 실제가 어긋난 곳도 두 군데** 나왔다.

## 무엇이 있는가

| 구성 | 실측 |
|---|---|
| `scripts/harness/guard.mjs` | 922줄, 규칙 **19종** |
| `scripts/harness/test/` | 테스트 파일 36개, 그중 `*-gate.test.mjs` **29개** |
| 자기검증 테스트 | `[자기검증]` 32건 + "공회전 방지" 5건 |
| 강제 지점 | 편집 훅 · pre-commit · CI |

규칙 19종의 id 는 이렇다.

```
MONEY-PRIMITIVE  MONEY-BIGDECIMAL-DOUBLE  IMMUTABLE-HISTORY  CONTROL-CHAR
MSA-BOUNDARY  ACCOUNT-CONSUME-ONLY  MARKET-NO-VALUATION  WORKFLOW-EMPTY-EXPR
OO-DOMAIN-SETTER  OO-DOMAIN-MUTABLE-LOMBOK  OO-DOMAIN-GENERIC-IAE
KAFKA-DLQ  KAFKA-GROUP-OWNER  HARNESS-DELETE  INVALID-ALLOWANCE
CMD-EDIT-BYPASS  CMD-NO-VERIFY  CMD-PROD-DB-WRITE  CMD-EVENT-PRODUCE
```

## 제일 잘 된 부분: 예외가 스스로 죽는다

가드에 예외를 두는 건 필요하다. 문제는 예외가 영구화된다는 것이다. `// TODO: 나중에 고침` 이 5년째 살아 있는 파일을 다들 하나쯤 안다.

이 가드의 면제 주석은 형식이 정해져 있다.

```java
// harness-guard: allow reason="..." issue="ISSUE-123" owner="team-settlement" expires="2099-01-01"
```

넷이 다 있어야 하고 하나라도 어긋나면 무효다. 무효인 면제는 그냥 무시되는 게 아니라 **`INVALID-ALLOWANCE` 라는 위반을 새로 만든다.** 즉 잘못된 면제를 달면 원래 위반 + 면제 위반, 둘이 된다. 대충 다는 쪽이 안 다는 쪽보다 손해다.

`scanText` 를 직접 불러 여섯 가지를 넣어봤다. 대상은 금액 스코프의 `double` 필드 하나(`MONEY-PRIMITIVE` 위반).

| 넣은 것 | 결과 |
|---|---|
| 면제 없음 | `MONEY-PRIMITIVE` 1건 |
| `owner="team-settlement"` / `expires="2099-01-01"` | **0건 — 통과** |
| `owner="@내계정"` (개인) | 2건 (`INVALID-ALLOWANCE` + 원위반) |
| `expires="2020-01-01"` (만료) | 2건 |
| `expires="2026-08-28"` (**오늘**) | 2건 |
| `expires="2026-08-29"` (내일) | 0건 |
| `expires="2099-02-31"` (없는 날짜) | 2건 |

세 가지가 눈에 띈다.

**첫째, 만료일 당일에 이미 죽는다.** 비교가 `<=` 라서 오늘 날짜를 적으면 오늘 바로 무효다. "만료일에 리뷰하자" 가 아니라 만료일에 빌드가 깨진다. 리뷰를 사람 일정에 맡기지 않는다는 뜻이다.

**둘째, 없는 날짜를 못 쓴다.** `2099-02-31` 은 `Date` 로 만든 뒤 연·월·일이 왕복해서 같은지 대조해 걸러낸다. 이게 없으면 JS 의 `Date` 가 조용히 3월 3일로 굴려서 사실상 만료일이 밀린다.

**셋째, owner 가 개인이 아니라 팀이다.** 정규식이 `team-*` 만 받는다. 개인 계정을 적으면 무효다. 사람은 퇴사하고 팀은 남는다 — 6개월 뒤 이 예외를 누구에게 물을지의 답이 유지되는 쪽을 강제한 것이다.

이슈 번호도 자유 서술을 안 받는다. `ISSUE-\d+` 이거나 GitHub 이슈 URL 이어야 한다. `issue="나중에"` 는 무효다.

정리하면 **무기한 예외가 문법적으로 표현 불가능하다.** 예외를 없앤 게 아니라, 예외에 반감기를 강제로 붙였다.

## 설명과 실제가 달랐던 곳 ①: 그건 19종에 없다

내가 이 가드를 설명할 때 자주 드는 예가 네 개였다. 체크 예외에 롤백하지 않는 `@Transactional`, 프록시를 안 타는 self-invocation, 같은 group-id 를 든 컨슈머, 코드 밖에서 바뀌는 파티션 수.

세어보니 **그중 셋은 `guard.mjs` 의 19종에 없다.** 없어서 안 막는다는 뜻이 아니라, 다른 물건이 막고 있었다.

```
guard.mjs (19종)        → 변경된 파일만 스캔. 쓰기 시점에 차단.
*-gate.test.mjs (29종)  → 리포 전수 스캔. 현재 트리 상태를 증명.
```

`@Transactional` 은 `tx-rollback-gate.test.mjs`, 파티션 수는 `kafka-topic-gate.test.mjs`, self-invocation 은 `aop-proxy-gate.test.mjs` 다. group-id 만 `KAFKA-GROUP-OWNER` 로 규칙 쪽에 있다.

이 구분은 사소하지 않다. **변경분 스캔은 이미 트리에 있는 위반을 절대 못 잡는다.** 규칙을 새로 추가한 날, 그 규칙을 어기는 기존 파일 200개는 아무도 안 건드리는 한 영원히 안 걸린다. 반대로 전수 스캔은 편집할 때마다 돌리기엔 무겁다. 그래서 둘이 나뉘어 있는 것이고, 하나만 있으면 반쪽이다.

실제로 돌려봤다.

```
$ node --test scripts/harness/test/{tx-rollback,kafka-topic,aop-proxy,topic-consumer}-gate.test.mjs
ℹ tests 39   ℹ pass 39   ℹ fail 0
```

`tx-rollback-gate` 가 잠그는 규칙은 두 줄이다. 도메인 예외는 전부 언체크여야 하고(상속 체인을 끝까지 따라간다), `@Transactional` 메서드가 체크 예외를 `throws` 하면 `rollbackFor` 를 반드시 명시해야 한다. 스프링 트랜잭션 AOP 의 기본값이 **언체크는 롤백, 체크는 커밋**이기 때문이다. 금융 도메인에서 이 기본값은 "실패했는데 커밋" 을 만든다. 컴파일도 되고 테스트도 통과한다.

`kafka-topic-gate` 가 막는 건 더 미묘하다. 파티션 수 N 이 바뀌면 `hash(key) % N` 이 바뀌어서, 같은 애그리거트의 이벤트가 다른 파티션으로 흩어진다. 이미 쌓인 메시지의 순서 보장까지 소급해서 무너지는, 되돌릴 수 없는 변경이다. 그런데 이 결함의 정체는 **선언의 부재**다. `NewTopic` 을 안 적고 브로커 자동생성에 맡기면 어떤 코드도 "틀리지" 않는다. 리뷰할 대상 자체가 없다. 사람이 못 잡는 게 당연하다.

이 네 개의 공통점이 그거다. **컴파일도 테스트도 통과하고 운영에서만 틀린다.** 그리고 대부분 잘못 쓴 게 아니라 **안 쓴 것**이다. 없는 것은 리뷰할 수 없다.

## 설명과 실제가 달랐던 곳 ②: 3층 중 한 층이 꺼져 있었다

설계상 강제 지점은 셋이다.

| 층 | 배선 | 지금 상태 |
|---|---|---|
| 1. 편집 직전 | `.claude/settings.json` 의 PreToolUse 훅 | **켜짐** |
| 2. 커밋 | `core.hooksPath` → `scripts/harness/hooks/pre-commit` | **꺼짐** |
| 3. CI | `.github/workflows/harness-guard.yml` | **켜짐** |

3층은 확인했다. 최근 실행 5건 전부 success, 33~55초.

2층이 문제였다. `git config --get core.hooksPath` 가 **비어 있다.** 훅 파일은 리포에 추적돼 있는데(그래서 fresh clone 에도 딸려온다) 활성화는 클론마다 `node scripts/harness/install-hooks.mjs` 를 한 번 돌려야 한다. 그 한 번을 안 한 상태였다.

영향은 이렇다. 편집 훅은 특정 에이전트 세션에서만 걸리고, CI 는 push 이후에 본다. 그 사이 **로컬 커밋은 아무 검사도 안 받고 만들어진다.** 결국 CI 에서 걸리긴 하지만, 커밋이 이미 생긴 뒤라 되돌리는 비용이 다르다. 3층 방어의 값어치는 "한 층을 건너뛰어도 다음이 막는다" 인데, 가운데 층이 비면 남는 건 맨 앞과 맨 뒤뿐이다.

재밌는 건 이 실패를 설계가 이미 예상했다는 점이다. 훅 파일 주석에 활성화 명령이 적혀 있고, `core.hooksPath` 를 점검하라는 별도 커맨드까지 있다. 예상했는데도 켜져 있지 않았다. **자동으로 켜지지 않는 안전장치는 언젠가 꺼져 있다**는 것 말고 다른 교훈이 없다.

## 게이트가 스스로를 시험한다

이 리포에서 제일 마음에 드는 규율은 따로 있다. 게이트 테스트 안에 두 종류의 자기 점검이 들어 있다.

```
✔ 도메인 예외 스캔 대상이 비어 있지 않다 (게이트 공회전 방지)
✔ [자기검증] 체크 예외를 상속한 도메인 예외를 잡아낸다
✔ [자기검증] 간접 상속 체인 끝까지 따라간다
✔ [자기검증] rollbackFor 없는 @Transactional + 체크 예외를 잡고, 있으면 통과시킨다
```

전수로 세면 `[자기검증]` 32건, 공회전 방지 5건이다.

앞의 것은 **스캔 대상이 0개가 되는 사고**를 막는다. 경로 규칙이 바뀌어 게이트가 아무 파일도 안 읽게 되면, 테스트는 여전히 초록불이다. 검사한 게 없으니 위반도 없다. 이건 가장 위험한 종류의 초록불이다.

뒤의 것은 **탐지 로직이 진짜 잡는지**를 합성 픽스처로 확인한다. 일부러 위반을 만들어 넣고 게이트가 그걸 거절하는지 본다.

나는 [어제 글](/2026/08/27/grill-me-vs-ouroboros-enforcement/)에서 정반대 사례를 다뤘다. 어떤 하네스에 인터페이스만 있고 구현이 없어서 게이트가 production 에서 아무것도 안 거르고 있던 기록이 소스에 남아 있었다. 이름도 있고 문서 참조도 되는데 실제로는 통과 여부를 아무도 안 보던 상태. [그 전날 글](/2026/08/27/paperthin-guards-measured/)에서는 정규식으로 YAML 을 검사하는 바람에 깨진 파일을 통과시키던 검증기를 재봤다.

셋을 나란히 놓으면 질문이 하나로 모인다. **게이트가 있는가**가 아니라 **그 게이트가 무언가를 거절한 적이 있는가**다.

## 체크리스트

어느 리포에서든 물어볼 수 있는 형태로 줄이면 이렇다.

1. **면제에 만료일이 있는가.** 없으면 그건 면제가 아니라 규칙의 삭제다.
2. **잘못된 면제가 그 자체로 위반인가.** 아니면 형식은 장식이다.
3. **면제의 주인이 개인인가 팀인가.** 개인은 나간다.
4. **변경분만 보는가, 전수도 보는가.** 변경분만 보면 도입 이전의 위반은 영원히 안 걸린다.
5. **게이트의 스캔 대상이 0이 될 수 있는가.** 그때도 초록불이면 그 초록불은 아무 뜻이 없다.
6. **탐지 로직 자체에 실패 테스트가 있는가.** 실패할 수 없는 게이트는 아무것도 증명하지 못한다.
7. **모든 층이 자동으로 켜지는가.** 수동 활성화가 필요한 층은 결국 꺼져 있다.

오늘 재보고 나서 고칠 것은 7번 하나다. 나머지 여섯은 이미 되어 있었는데, 그건 처음부터 잘 설계해서가 아니라 대부분 **한 번씩 터진 뒤에 하나씩 붙인 것**이다. 게이트 목록이 베스트 프랙티스 문서가 아니라 사건 목록에 가까운 이유다.

---

**검증 범위.** 위 수치는 2026-08-28 기준 로컬 작업 사본에서 잰 것이다. 규칙 19종은 `guard.mjs` 의 고유 `id` 를 센 값이고, 면제 판정 7건은 `scanText` 를 직접 호출해 얻은 결과다. 게이트 실행은 29개 중 4개(`tx-rollback` · `kafka-topic` · `aop-proxy` · `topic-consumer`)만 돌려 39개 테스트 통과를 확인했고, 전체 스위트는 로컬에서 2분 안에 끝나지 않아 완주하지 못했다(CI 잡은 33~55초로 완료된다). CI 상태는 워크플로 최근 실행 5건이 모두 success 인 것을 확인한 것이지 각 스텝의 판정을 재현한 것은 아니다. 같은 엔진을 복사해 쓰는 다른 리포에는 규칙이 18종이었다(`CONTROL-CHAR` 부재) — 복사본은 갈라진다는 사례로만 적어 둔다. 이 글은 사내 저장소를 대상으로 하므로 코드 인용 대신 규칙 id 와 판정 결과만 옮겼다.

## References

- 김영한, 「스프링 DB 2편 — 데이터 접근 활용 기술」 (예외와 트랜잭션 커밋·롤백) — <https://www.inflearn.com/course/스프링-db-2>
- Spring Framework Reference, *Transaction Management — Declarative rollback rules* — <https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html>
- Spring Framework Reference, *Understanding AOP Proxies* (self-invocation) — <https://docs.spring.io/spring-framework/reference/core/aop/proxying.html#aop-understanding-aop-proxies>
- Apache Kafka Documentation — Producer partitioning / `DefaultPartitioner` — <https://kafka.apache.org/documentation/#producerconfigs>
- 이 블로그, [319단어 대 28만 줄 — grill-me 와 우로보로스](/2026/08/27/grill-me-vs-ouroboros-enforcement/) (2026-08-27)
- 이 블로그, [paperthin 의 가드를 직접 돌려봤다](/2026/08/27/paperthin-guards-measured/) (2026-08-27)
