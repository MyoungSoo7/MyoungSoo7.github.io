---
layout: post
title: "Xray 커버리지는 Jira 배관이 결정한다 — 이슈타입·링크·스킴·권한"
date: 2026-09-17 19:31:14 +0900
categories: [Engineering, QA]
tags: [Jira, Xray, 테스트관리, 이슈링크, 스킴, 추적성, JQL]
---

Xray 를 도입하면 "테스트 관리 도구를 하나 더 얻었다" 고 생각하기 쉽다. 실제로 얻은 것은 조금 더
건조하다. **Jira 이슈타입 몇 개와 이슈 링크 타입 하나, 그리고 계산되는 커스텀 필드 몇 개다.**

이게 왜 중요한가. Xray 가 별도 데이터베이스에 테스트를 보관하는 게 아니라 Jira 이슈로 보관하기
때문에, **Jira 쪽 관리 설정이 그대로 테스트 관리의 진위를 결정한다.** 이슈 링크를 끄면 커버리지가
끊기고, 이슈타입 스킴을 잘못 건드리면 옆 프로젝트까지 딸려 들어오고, 권한 하나가 빠지면 테스트는
만들어지는데 요구사항에는 안 붙는다. 대시보드는 이 모든 경우에 조용히 초록색이다.

이 글은 그 **배관(plumbing)** 쪽 이야기다. 사양서(Confluence)에서 Jira 로 넘어오는 다리에 대해서는
[별도의 글]({% post_url 2026-09-17-confluence-spec-xray-requirement-coverage %})에서 다뤘고, 여기서는
다리가 닿는 쪽 — **Jira 자체의 구성** — 만 본다.

---

## 1. Xray 가 Jira 에 실제로 설치하는 것

Xray 는 앱 설치 시 Jira 에 아래를 추가한다. Cloud 기준 이슈타입은 **Test, Precondition, Test Set,
Test Plan, Test Execution** 이고, Data Center 에는 **Sub Test Execution** 이 더 있다.
([Xray Cloud — Working with Test Issues](https://docs.getxray.app/spaces/XRAYCLOUD/pages/45250311/Working+with+Test+Issues),
[Xray DC — Testing Approaches](https://docs.getxray.app/spaces/XRAY/pages/62271070))

여기서 처음 걸리는 지점이 있다. **Test Run 은 Jira 이슈가 아니다.** Test 를 Test Execution 에
넣는 순간 Xray 내부에 생기는 엔티티이고, Jira 이슈 키가 없다. 마찬가지로 **Test Repository** 도
이슈타입이 아니라 프로젝트 안의 폴더 트리다. 그래서 "테스트 실행 이력을 JQL 로 뽑아 달라" 는
요청은 절반만 가능하다 — Test Execution 이슈는 JQL 로 잡히지만 개별 Run 은 Xray 쪽 기능
(JQL 함수·리포트·REST)을 거쳐야 한다.

조직 단위 두 개도 자주 헷갈린다.

| 이슈타입 | 쓰임 |
| --- | --- |
| **Test Set** | 테스트를 묶어 두는 **정적 목록**. 실행 계획이 아니다 |
| **Test Plan** | 특정 범위(릴리스·스프린트)의 **실행 계획과 통합 결과** |
| **Test Execution** | 실제로 한 번 돌린 **실행 단위** |

Test Set 에 100개를 넣어 놨다고 계획이 선 게 아니다. Test Plan 을 만들어야 "이 릴리스에서 무엇을
돌릴 것인가" 가 생긴다.

---

## 2. 요구사항과 테스트의 상관관계는 "이슈 링크 한 줄" 이다

Xray 에서 요구사항 커버리지는 요약 텍스트나 태그가 아니라 **Jira 이슈 링크**다. Xray 는 설치 시
링크 타입 두 개를 추가한다.

- **Tests** — outward `tests` / inward `tested by`
- **Defect** — outward `created` / inward `created by`

즉 `TEST-42 tests REQ-7` 이라는 링크가 있어야 커버리지가 성립한다. 링크가 없으면 그 요구사항은
UNCOVERED 다. 이 사실 하나가 아래 세 가지를 전부 **커버리지 장애 지점**으로 만든다.

### (1) 이슈 링크는 Jira 전역에서 꺼질 수 있다

Atlassian 공식 문서는 이슈 링크가 관리자가 **활성/비활성** 할 수 있는 기능이라고 명시한다.
비활성화하면 링크 기능 자체가 사라진다.
([Configuring issue linking](https://confluence.atlassian.com/spaces/ADMINJIRASERVER110/pages/1627461076/Configuring+issue+linking))

Xray 를 쓰는 인스턴스에서 링크를 끌 일이 있느냐고 물으면 보통 없다. 그런데 Jira 를 먼저 쓰던
조직이 "링크가 지저분하다" 는 이유로 정리하다가 **링크 타입을 삭제하거나 이름을 바꾸는** 경우는
있다. 같은 문서가 관리자는 링크 타입을 추가·수정·**삭제** 할 수 있다고 적고 있다. Xray 의
`Tests` 링크 타입이 여기 포함된다.

### (2) 링크에는 별도 권한이 필요하다

링크를 만들려면 **Link issues**(Cloud 표기 **Link Work Items**) 권한이 있어야 한다. 이게 커버리지
쪽에서 특히 고약하게 나타난다. Xray Cloud 권한 문서의 문장을 그대로 옮기면 이렇다.

> "To correctly create Tests from Coverable items, specifically, you also need 'Link Work Items'
> permission. Without it, the test item will be created but not automatically connected to the
> Coverable item."
> — [Xray Cloud, Xray and Permissions](https://docs.getxray.app/spaces/XRAYCLOUD/pages/1203503118/Xray+and+Permissions)

**테스트는 만들어진다. 링크만 안 붙는다.** 에러도 안 난다. QA 는 "테스트 만들었다" 고 하고
대시보드는 "커버 안 됨" 이라고 한다. 두 사람 다 맞는 말을 하고 있다.

### (3) 커버리지 대상은 프로젝트마다 따로 켠다

Xray 는 어떤 이슈타입을 "요구사항(Coverable Issue Type)" 으로 볼지 **전역 설정 + 프로젝트별
설정** 두 곳에서 정한다. 프로젝트 토글이 꺼져 있거나 그 프로젝트의 Story 가 매핑에 없으면,
링크를 아무리 걸어도 커버리지 필드가 안 산다. 반대로 **Xray 자신의 이슈타입을 요구사항으로
매핑하면 안 된다** — 테스트가 테스트를 커버하는 순환이 생긴다.
([Configuring a Jira project to be used as a Requirement project](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44566294))

---

## 3. 이슈타입 스킴은 프로젝트 하나짜리 설정이 아니다

Xray 이슈타입을 쓰려면 프로젝트의 **Issue Type Scheme** 에 그것들을 넣어야 한다. 여기서 실수가
잦은 이유는 스킴의 성질 때문이다.

- 프로젝트는 **이슈타입 스킴을 정확히 하나** 가진다.
- 스킴은 **여러 프로젝트가 공유**한다. 즉 스킴을 고치면 **그 스킴을 쓰는 모든 프로젝트**가 바뀐다.
- 이슈가 존재하는 이슈타입을 스킴에서 빼면 Jira 가 **Issue Type Migration Wizard** 를 띄워 이슈를
  다른 타입으로 옮기게 한다.

([Associating issue types with projects](https://confluence.atlassian.com/adminjiraserver100/associating-issue-types-with-projects-1442845277.html),
[Working with issue type schemes](https://confluence.atlassian.com/jirasoftwareserver0821/working-with-issue-type-schemes-1167696375.html))

그래서 "개발팀 프로젝트에만 Xray 를 켜자" 고 했는데 옆 프로젝트 이슈 생성 화면에 Test·Test Plan 이
같이 뜨는 일이 생긴다. 스킴을 공유하고 있었던 것이다. 켜기 전에 **그 스킴을 쓰는 프로젝트 목록을
먼저 확인**해야 한다.

### 스킴은 하나가 아니라 셋이다

이슈타입 스킴만 고치고 끝내면 절반만 된 상태가 된다. Xray 공식 가이드는 기존 프로젝트에 Xray 를
붙일 때 **Issue Type Scheme** 과 **Issue Type Screen Scheme** 을 **각각** 손봐야 한다고 안내한다.
추가로 프로젝트의 **필드 구성(field configuration)** 에 Xray 커스텀 필드가 들어 있어야 하며, 그렇지
않으면 "you'll most likely experience errors" 라고 적혀 있다.
([Configuring Xray with an existing project](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44566326))

증상으로 보면 이렇다.

| 빠뜨린 것 | 증상 |
| --- | --- |
| Issue Type Scheme | 이슈 생성 목록에 Test 가 아예 없음 |
| Issue Type **Screen** Scheme | Test 는 만들어지는데 **테스트 스텝·타입 필드가 안 보임** |
| Field configuration | 이슈 열 때/저장할 때 오류 |

두 번째가 제일 헷갈린다. 이슈타입은 분명히 생겼는데 Xray 화면이 없으니 "Xray 가 고장났다" 로
읽힌다. 고장이 아니라 스크린 스킴을 안 건드린 것이다.

같은 문서는 한 가지를 더 경고한다. 이슈타입 추가는 **되돌리기가 간단하지 않다.** 이미 그 타입으로
이슈가 생긴 뒤에는 마이그레이션을 거쳐야 한다. 실험은 샌드박스 프로젝트에서 한다.

### 팀 관리형 프로젝트에는 스킴이 없다

Atlassian 은 팀 관리형(team-managed) 프로젝트가 **스킴을 갖지 않고 공유 구성을 쓰지 않는다**고
명시한다. 이슈타입이 프로젝트 내부에만 존재한다는 뜻이다.
([Learn Atlassian — team-managed vs company-managed](https://www.atlassian.com/software/jira/guides/projects/overview))

테스트 자산을 여러 프로젝트에 걸쳐 재사용하고 전사 커버리지를 집계할 생각이라면, **테스트가 사는
프로젝트는 회사 관리형(company-managed)으로 두는 편**이 관리 비용이 훨씬 싸다. 이건 Xray 의 제약이
아니라 Jira 의 구조다.

---

## 4. 프로젝트 경계를 어디에 그을 것인가

Xray 는 요구사항·테스트·결함을 **같은 프로젝트에 둘 수도, 나눌 수도** 있다. 공식 문서는 대표적인
배치 다섯 가지를 제시하고 **"All in one"(요구사항·테스트·실행·결함을 한 프로젝트에)** 을 기본
권장안으로 든다.
([Project Organization](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44566397/Project+Organization))

나누는 쪽을 택할 때 반드시 알아야 할 함정이 문서에 하나 박혀 있다.

> "your Requirement's project version names must match the names of the Test Execution's project"
> — 같은 문서

요구사항 프로젝트와 테스트 실행 프로젝트를 분리해 놓고 버전(Fix Version) 이름을 서로 다르게 쓰면
— 예컨대 한쪽은 `2026.09`, 다른 쪽은 `Sprint 42` — **버전별 커버리지 분석이 매칭되지 않는다.**
링크는 멀쩡하고 실행도 멀쩡한데 "이번 릴리스 커버리지" 만 비어 보인다.

실무적으로 정리하면 이렇다.

- **분리를 택했다면 버전 명명 규칙을 두 프로젝트에 강제한다.** (릴리스 이름 생성 담당자를 한 명으로)
- 분리의 이유가 "권한" 이면 대개 프로젝트 분리 대신 **이슈 보안 수준·권한 스킴**으로 풀 수 있다.
- 분리의 이유가 "테스트가 백로그를 더럽힌다" 면 보드 필터(`issuetype not in (Test, "Test Execution", ...)`)
  로 충분한 경우가 많다.

---

## 5. 워크플로와 권한 — 테스트 이슈도 그냥 이슈다

Xray 이슈타입에는 **Jira 워크플로가 그대로 붙는다.** 승인 없이 테스트를 고치지 못하게 하고 싶다면
새 워크플로를 쓰면 된다. 다만 두 가지를 알고 해야 한다.

**(1) 읽기 전용 상태는 커버리지를 얼리지 못한다.** 워크플로 상태에 `jira.issue.editable = false` 를
주면 그 상태의 이슈는 편집이 막힌다. 그런데 Xray 문서는 이렇게 적는다.

> "Coverage status on read-only Requirements can still be affected by status changes in the related
> Test Runs."
> — [Xray and Permissions](https://docs.getxray.app/spaces/XRAYCLOUD/pages/1203503118/Xray+and+Permissions)

요구사항을 "확정" 상태로 잠가도 **커버리지 상태는 계속 움직인다.** 이건 버그가 아니라 설계다 —
커버리지는 이슈 필드가 아니라 연결된 Test Run 들로부터 **계산되는 값**이기 때문이다. 스냅샷이
필요하면 이슈를 잠글 게 아니라 **Test Plan 이나 버전으로 스코프를 고정**해서 읽어야 한다.

**(2) 실행 자체를 워크플로 상태로 막을 수 있다.** Xray 전역 설정의 Miscellaneous 에
**"Disallow executions of Tests with workflow statuses"** 가 있다. 예를 들어 `Draft`·`Deprecated`
상태의 Test 는 실행을 막을 수 있다. 검토 안 끝난 테스트의 결과가 커버리지에 섞여 들어오는 걸
막는 유일한 구조적 장치라서, 테스트 리뷰 프로세스를 도입한다면 이걸 같이 켜야 의미가 생긴다.

권한 쪽은 원칙이 단순하다. **Xray 는 별도 권한 체계를 만들지 않는다.** Browse / Create / Edit /
Delete / Link 같은 표준 Jira 권한이 그대로 적용되고, 여기에 Test Case Importer 같은 대량 작업은
**Make bulk changes** 를 요구한다. 그래서 권한 사고가 나면 Xray 설정이 아니라 **권한 스킴**을 본다.

---

## 6. 자동화가 만드는 것도 Jira 이슈다

CI 에서 JUnit XML 을 밀어 넣으면 Xray 는 그걸 **Jira 이슈로** 바꾼다. Test Execution 이슈가 생기고,
필요하면 Test 이슈까지 만든다. 여기서 Jira 쪽에 직접 영향을 주는 규칙이 하나 있다.

Xray 는 들어온 결과를 기존 Test 이슈에 매칭할 때 **이슈 키(`testKey`) → 요약(Manual/BDD) 또는
Generic Test Definition(Generic)** 순으로 찾고, 못 찾으면 **새 Test 이슈를 만든다.** JUnit 의 경우
`classname` 과 `name` 을 합친 문자열이 Generic Test Definition 이 된다.
([Import Execution Results — REST](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44569902/Import+Execution+Results+-+REST))

같은 문서의 이 문장이 핵심이다.

> "If the match field (summary or definition) is changed, Xray will search for another issue and
> will create a new test case."

무슨 뜻인가. **테스트 메서드 이름을 리팩터링하면 Xray 는 그걸 새 테스트로 본다.** 이전 Test 이슈에
걸어 둔 요구사항 링크·라벨·Test Plan 소속은 전부 옛 이슈에 남고, 새 이슈는 아무 데도 안 붙은 채
생긴다. 커버리지 숫자는 그 순간 조용히 떨어진다. 코드는 정상이고 테스트도 통과했는데 말이다.

방어책은 두 가지다.

- **`testKey` 로 고정한다.** 테스트 코드에 Jira 키를 애노테이션·태그로 박아 두면 이름을 바꿔도
  같은 이슈로 들어간다.
- **`requirementKeys` 로 코드에서 커버리지를 선언한다.** `testInfo` 에 이 필드를 넣으면 Xray 가
  그 Test 이슈와 요구사항 사이에 링크를 만들어 준다. 사람이 손으로 링크를 걸지 않아도 되므로
  2절의 "링크가 안 걸린 테스트" 문제를 구조적으로 줄인다.

반대로 **`info` 를 쓰면 매번 새 Test Execution 이슈가 생긴다.** 기존 실행에 결과를 덧붙이려면
`testExecutionKey` 를 줘야 한다. 이 차이를 모르면 프로젝트에 Test Execution 이슈가 빌드 수만큼
쌓인다 — 기능적으로는 정상이지만, 그 프로젝트의 이슈 검색과 보드는 못 쓰게 된다.

---

## 7. 관리법 — Jira 쪽에서 거는 게이트

지금까지가 "어디서 끊어지는가" 였다면, 아래는 **Jira 설정과 JQL 만으로 걸 수 있는 방어선**이다.
Xray 리포트는 사람이 봐야 하지만, JQL 은 자동화에 물릴 수 있다.

### 7.1 커버리지 구멍을 JQL 로 뽑는다

Xray 는 JQL 함수를 제공한다. 대표적인 것들:

```
issue in requirements('uncovered')
issue in requirements('OK', 'COM', '1.2')
issue in requirementTests('COM-1')
issue in testRequirements('COM-42')
issue in testExecutionTests('COM-100')
```

가장 값싼 게이트는 이 한 줄이다.

```
project = COM AND issuetype = Story AND fixVersion = "2026.09"
  AND issue not in requirements('OK', 'COM', '2026.09')
```

**"이번 릴리스 스토리 중 커버리지가 OK 가 아닌 것"** 을 필터로 저장해 두고, 결과가 0 이 아니면
릴리스를 막는다. 대시보드 가젯보다 이쪽이 낫다 — 숫자를 보는 게 아니라 **목록이 나오기 때문**에
누가 무엇을 해야 하는지가 바로 나온다.

### 7.2 링크 없는 테스트를 주기적으로 훑는다

2절의 "Link Work Items 없이 만들어진 테스트" 는 에러를 안 내므로 **찾아 나서야만** 보인다.

```
project = COM AND issuetype = Test AND issueLinkType is EMPTY
```

이 필터가 0 이 아니면 둘 중 하나다 — 권한이 빠졌거나, 링크를 걸 대상 없이 테스트부터 만들었거나.
어느 쪽이든 그 테스트의 결과는 커버리지에 반영되지 않는다.

### 7.3 스킴 변경은 영향 범위를 먼저 뽑는다

이슈타입 스킴·스크린 스킴을 건드리기 전에 **그 스킴을 공유하는 프로젝트 목록**을 확인한다.
(Jira 관리 → Issues → Issue type schemes 의 Projects 열). 이걸 안 보고 "우리 프로젝트만" 이라고
생각한 변경이 옆 팀 이슈 생성 화면을 바꾼다.

### 7.4 버전 이름을 규칙으로 강제한다

프로젝트를 분리했다면 4절의 함정이 상시로 열려 있다. 릴리스 이름은 **한 곳에서 만들고 복사**한다.
자동화가 있다면 Jira REST `/rest/api/3/project/{key}/versions` 로 두 프로젝트 버전 목록을 비교해
불일치를 알리는 게 가장 싸다.

### 7.5 테스트 이슈를 백로그에서 걷어낸다

Test·Test Execution 이슈가 스크럼 보드에 섞이면 팀이 Xray 를 싫어하게 되고, 싫어지면 링크를 안
건다. 보드 필터에서 빼는 한 줄이 도입 성패를 가르는 경우가 실제로 많다.

```
project = COM AND issuetype not in (Test, "Test Set", "Test Plan", "Test Execution", "Pre-Condition")
```

### 7.6 커스텀 필드를 게이트의 근거로 쓰지 않는다

"Requirement Status" 같은 Xray 커스텀 필드는 **계산 필드**다. 기본 스코프로 계산되고, JQL 로 정렬·
집계하기에 적합하지 않다. **버전이나 Test Plan 을 인자로 받는 JQL 함수**(`requirements(status, project, version)`,
`requirementsWithStatusByTestPlan`)를 게이트의 근거로 쓴다. 이유는 단순하다 — 게이트는 "언제
기준으로" 를 반드시 말할 수 있어야 하는데, 커스텀 필드는 그걸 말할 수 없다.

---

## 8. 요약

- Xray 의 테스트 자산은 **Jira 이슈**이고, 요구사항 커버리지는 **Jira 이슈 링크**(`tests` /
  `tested by`)다. 그래서 Jira 관리 설정이 곧 테스트 관리의 신뢰도다.
- 이슈 링크는 전역에서 꺼질 수 있고, 링크 타입은 삭제될 수 있으며, 링크 생성에는 **별도 권한**이
  필요하다. 권한이 없으면 **테스트는 생성되고 링크만 조용히 빠진다.**
- 이슈타입 스킴은 **프로젝트 간 공유**된다. 그리고 **스크린 스킴은 별도 작업**이다 — 이걸
  빠뜨리면 "이슈타입은 있는데 Xray 화면이 없는" 상태가 된다.
- 프로젝트를 분리했다면 **버전 이름이 프로젝트 간에 일치**해야 버전별 분석이 성립한다.
- 워크플로로 요구사항을 잠가도 **커버리지 상태는 계속 움직인다.** 스냅샷은 Test Plan·버전
  스코프로 읽는다.
- CI 결과 임포트에서 **매칭 필드(요약 / Generic Test Definition)가 바뀌면 새 Test 이슈가 생긴다.**
  `testKey` 고정과 `requirementKeys` 선언이 방어책이다.
- 관리는 대시보드가 아니라 **JQL 필터**로 건다. `requirements('uncovered')` 와
  `issueLinkType is EMPTY` 두 개만 걸어도 절반은 잡힌다.

---

## 9. 근거의 한계

- 이 글의 사실 진술은 **Atlassian 과 Xray(Xblend) 공식 문서**에 근거했다. 각 항목의 출처를
  본문에 인라인으로 달았다.
- Xray 는 **Cloud 와 Data Center 의 UI 명칭과 기능 범위가 다르다.** 예컨대 Sub Test Execution 은
  DC 에만 있고, 권한 명칭은 Cloud 가 "Link Work Items", DC/Server 계열 문서가 "Link Issues" 다.
  본문에서는 인용한 문서의 표기를 따랐으므로, 적용 전 **본인 인스턴스의 배포 형태에 맞는 문서**를
  다시 확인하기 바란다.
- 7절의 JQL 예시는 공식 문서의 함수 시그니처에 기반해 구성한 것으로, **프로젝트 키·버전명·
  이슈타입명은 각 인스턴스에 맞춰 바꿔야 한다.** 필자 환경에서 검증한 것은 문법 형태이지
  특정 조직의 결과값이 아니다.
- 6절의 CI 임포트 동작은 문서에 명시된 매칭 규칙을 근거로 했다. 실제 파이프라인에 적용하기 전
  **샌드박스 프로젝트에서 한 번 돌려 이슈가 몇 개 생기는지** 세어 보는 편이 안전하다.
- 도입 성패나 팀 반응에 대한 서술(7.5 등)은 **경험적 판단**이며 공식 문서의 주장이 아니다.

---

## References

**Atlassian 공식**

- [Configuring issue linking — Jira Administration](https://confluence.atlassian.com/spaces/ADMINJIRASERVER110/pages/1627461076/Configuring+issue+linking)
- [Associating issue types with projects](https://confluence.atlassian.com/adminjiraserver100/associating-issue-types-with-projects-1442845277.html)
- [Working with issue type schemes](https://confluence.atlassian.com/jirasoftwareserver0821/working-with-issue-type-schemes-1167696375.html)
- [Jira projects overview — team-managed vs company-managed](https://www.atlassian.com/software/jira/guides/projects/overview)

**Xray 공식 (Xblend / getxray.app)**

- [Working with Test Issues (Xray Cloud)](https://docs.getxray.app/spaces/XRAYCLOUD/pages/45250311/Working+with+Test+Issues)
- [Configuring Xray with an existing project](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44566326)
- [Configuring a Jira project to be used as a Requirement project](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44566294)
- [Project Organization](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44566397/Project+Organization)
- [Xray and Permissions](https://docs.getxray.app/spaces/XRAYCLOUD/pages/1203503118/Xray+and+Permissions)
- [Import Execution Results — REST](https://docs.getxray.app/spaces/XRAYCLOUD/pages/44569902/Import+Execution+Results+-+REST)
- [Testing Approaches (Xray DC)](https://docs.getxray.app/spaces/XRAY/pages/62271070)

**관련 글**

- [사양서(Confluence)와 Xray 커버리지 — 두 도구는 왜 조용히 어긋나는가]({% post_url 2026-09-17-confluence-spec-xray-requirement-coverage %})
