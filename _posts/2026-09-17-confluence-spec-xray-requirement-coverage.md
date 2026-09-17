---
layout: post
title: "사양서(Confluence)와 Xray 커버리지 — 두 도구는 왜 조용히 어긋나는가"
date: 2026-09-17 19:19:31 +0900
categories: [Engineering, QA]
tags: [Xray, Confluence, Jira, 테스트관리, 추적성, 요구사항커버리지]
---

사양서는 Confluence 에 있고, 테스트는 Jira 의 Xray 에 있다. 대시보드에는 초록색 커버리지 도넛이 떠 있다. 그런데 릴리스 직후 "이 기능 테스트 안 했어요?" 가 나온다.

문제는 도구가 고장 난 게 아니다. **두 도구가 애초에 같은 것을 추적하지 않는다.** Confluence 는 *문서*를 버전 관리하고, Xray 는 *이슈 링크*를 근거로 커버리지를 계산한다. 이 글은 그 접합면이 정확히 어디이고, 어디서 조용히 끊어지며, 무엇으로 막을 수 있는지를 공식 문서 기준으로 정리한다.

---

## 1. Xray 의 세계관: "요구사항" 은 이슈타입이 아니라 역할이다

가장 먼저 깨야 할 오해가 있다. Xray 공식 FAQ 는 이렇게 못박는다.

> There is no "Requirement" issue type installed by Xray. In fact, Xray does not install any requirement-related issue types.[^xrayfaq]

Xray 는 `Requirement` 라는 이슈타입을 만들지 않는다. 대신 **어떤 이슈타입을 요구사항으로 취급할지 관리자가 지정**한다. Story 든 Epic 든 사내에서 만든 `Spec` 이든 상관없다. 심지어 Bug 도 지정할 수 있다 — 공식 문서는 "결함이 재발하지 않음을 보증하기 위해" 결함 이슈타입을 요구사항으로 매핑하는 것을 명시적으로 지원한다고 적는다.[^xrayreqdef]

그래서 Test Coverage 패널이 안 보인다는 신고의 원인은 거의 항상 둘 중 하나다.

> You need to ensure that: your project is defined as a requirements project, and your issue type is configured to be a requirement issue type.[^xrayfaq]

**프로젝트 활성화**와 **이슈타입 매핑**이 둘 다 켜져야 한다. 하나만 켜면 패널 자체가 나타나지 않고, 나타나지 않으면 아무도 커버리지를 입력하지 않으며, 입력이 없으면 리포트는 조용히 비어 있다.

그리고 커버리지의 실체는 화려한 무엇이 아니라 **Jira 이슈 링크**다.

> In order to cover a requirement issue with Test cases, you need to create Jira issue links between the requirement and Test or Test Set issues.[^xraycoverage]

Xray 가 설치 시 자동으로 만드는 링크 타입은 `Tests` (outbound `tests` / inbound `tested by`) 와 `Defect` (outbound `created` / inbound `created by`) 다.[^xraycoverage] 요구사항에서 Test 를 만들면 Xray 는 언제나 `Tests` 링크 타입을 기본값으로 쓴다.

---

## 2. Confluence 쪽에서 건너오는 다리는 세 개뿐이다

Confluence 사양서와 Jira/Xray 를 잇는 공식 경로는 생각보다 좁다. 전제는 하나 — **Application Links 로 두 인스턴스가 연결돼 있어야 한다.** Atlassian 문서는 Jira Issues 매크로의 선행 조건으로 이것을 못박는다.[^confmacro]

그 위에서 쓸 수 있는 것이 세 가지다.[^conftogether]

1. **Jira Issues 매크로** — 단일 이슈, 필터 결과 목록, 또는 이슈 *개수*를 페이지에 표시. Jira URL 을 그냥 붙여넣으면 매크로로 자동 변환된다. `<jira>/browse/CONF-1234` 는 단일 이슈로, `<jira>/issues/?jql=project%20%3D%20CONF` 는 검색 결과 목록으로 바뀐다.
2. **하이라이트 → 이슈 생성** — 페이지에서 텍스트를 선택하면 뜨는 "Create Jira issue" 아이콘. 선택한 텍스트가 이슈 요약(summary)에 자동으로 들어간다. 표 안의 텍스트라면 같은 열에서 여러 개를 한 번에 만들 수 있다. Atlassian 문서 자신이 "Confluence 로 기획하고 요구사항을 모으는 경우 특히 유용하다" 고 쓴다.
3. **Jira Links 버튼** — Confluence 에서 Jira 이슈를 링크하거나 Jira 에서 Confluence 페이지를 링크하면 페이지 상단에 나타나는 양방향 점프 버튼.

Xray 도 이 위에 얹힌다. Xray 문서는 Confluence 페이지에서 **Xray 이슈(Test, Pre-Condition 등)를 직접 생성**할 수 있고, `Overall Requirement Coverage` 같은 **Xray 전용 가젯을 Confluence 페이지에 임베드**할 수 있다고 적는다. 다만 Confluence 에서 이슈를 만들 때 **Xray 커스텀 필드에는 제약이 있다**고 같은 문서가 스스로 경고한다.[^xrayconf]

### 함정: 다리가 한 방향만 놓이는 조합이 있다

여기서 조용히 어긋나는 첫 지점이 나온다. Confluence Cloud + Jira Data Center/Server 조합에 대해 Atlassian 은 이렇게 쓴다.

> Once you link the page, it will appear in your issue, but a reciprocal link won't be added to a page. You might know this feature from server as 'Jira links button', but it's not available in Confluence Cloud.[^confcloudjiradc]

같은 문서는 버그 때문에 **Confluence 페이지를 검색할 수 없고 URL 을 붙여넣는 것만 된다**고도 명시한다. 즉 이 조합에서는 "이슈 → 사양서" 는 보이지만 "사양서 → 이슈" 는 안 보인다. 사양서를 읽는 사람은 이 요구사항이 테스트되고 있는지 *페이지 위에서는 알 방법이 없다.* 추적성은 양방향일 때만 추적성이다.

---

## 3. 상관관계의 실체 — 상태는 어떻게 계산되는가

Xray 의 요구사항 상태는 다섯 개이고, 커스텀 상태는 만들 수 없다.[^xraycalc]

| 상태 | 의미 (공식 정의) |
| --- | --- |
| `OK` | 연결된 모든 Test 가 PASSED |
| `NOK` | 연결된 Test 중 하나 이상이 FAILED |
| `NOTRUN` | FAILED 는 없고, TODO 또는 ABORTED 가 하나 이상 |
| `UNKNOWN` | FAILED 는 없고, UNKNOWN 이 하나 이상 |
| `UNCOVERED` | 연결된 Test 가 하나도 없음 |

Test 상태는 여기에 이렇게 매핑된다.[^xraycalc]

| Test 상태 | Final? | 매핑되는 요구사항 상태 |
| --- | --- | --- |
| PASS | yes | OK |
| FAIL | yes | NOK |
| TODO | no | NOTRUN |
| **ABORTED** | **yes** | **NOTRUN** |
| EXECUTING | no | NOTRUN |

계산의 골격은 단순하다. 요구사항 $R$ 의 상태는 그 요구사항을 검증하는 Test 들의 상태를 **하나의 가상 Test 로 합친 뒤** 위 표로 매핑한 값이다. 공식 문서는 이를 "a joint calculation is done for a virtual Test case" 라고 표현한다.[^xraycalc]

$$\mathrm{status}(R,\,V,\,E)\;=\;\mathrm{map}\!\left(\bigoplus_{t\,\in\,T(R,\,V)}\mathrm{status}(t,\,V,\,E)\right)$$

여기서 $V$ 는 버전(또는 Test Plan), $E$ 는 Test Environment, $T(R,V)$ 는 그 스코프에서 $R$ 을 커버한다고 간주되는 Test 집합, $\bigoplus$ 는 순위 규칙에 따른 결합이다. 중요한 건 **좌변에 $V$ 와 $E$ 가 들어 있다는 사실** 자체다. 공식 문서의 표현대로, 누가 "이 요구사항 상태가 뭐냐" 고 물으면 되물어야 한다 — **"어느 버전에서?"**[^xraycf]

하위 요구사항이 있으면 부모 상태는 자기 상태와 자식 상태의 논리곱으로 결정된다.[^xraycalc]

| 부모 \ 자식 | OK | NOK | NOT RUN | UNKNOWN | UNCOVERED |
| --- | --- | --- | --- | --- | --- |
| **OK** | OK | NOK | NOT RUN | UNKNOWN | **OK** |
| **NOK** | NOK | NOK | NOK | NOK | NOK |
| **NOT RUN** | NOT RUN | NOK | NOT RUN | UNKNOWN | NOT RUN |
| **UNKNOWN** | UNKNOWN | NOK | UNKNOWN | UNKNOWN | UNKNOWN |
| **UNCOVERED** | OK | NOK | NOT RUN | UNKNOWN | UNCOVERED |

$$\mathrm{status}(R_{\text{parent}})\;=\;\mathrm{status}(R)\;\wedge\;\bigwedge_{s\,\in\,\mathrm{sub}(R)}\mathrm{status}(s)$$

표의 **왼쪽 위 모서리**를 보라. 부모가 `OK` 이고 자식이 전부 `UNCOVERED` 여도 결과는 `OK` 다. 공식 문서가 직접 쓴 문장은 이렇다.

> Even if you have sub-requirements, when you have tests that are directly linked to the parent requirement, Xray assumes that you are validating the requirement directly. Thus, it's irrelevant if the sub-requirements are uncovered by tests.[^xraycalc]

---

## 4. 조용히 어긋나는 다섯 지점

### (1) 커버리지는 링크이지 텍스트가 아니다

Xray 의 커버리지는 이슈 링크의 존재 여부로 계산된다. **Confluence 사양서의 문단을 고쳐도 링크는 그대로다.** 요구사항의 내용이 바뀌었는데 커버리지 도넛은 여전히 초록이다. 사양 변경이 테스트를 무효화시켰다는 신호가 이 모델에는 구조적으로 존재하지 않는다. 이건 버그가 아니라 설계의 경계다 — 그리고 그 경계를 메우는 건 사람의 규율이다.

### (2) "어느 버전에서?" — 커스텀 필드는 버전을 고를 수 없다

`Requirement Status` 는 계산 필드이고, **어느 버전 기준으로 계산할지는 전역 설정이 정한다.** FAQ 는 이렇게 쓴다.

> Currently, it is not possible to specify explicitly the version that you want to calculate the coverage on.[^xrayfaq]

게다가 프로젝트를 넘나들면 조건이 하나 더 붙는다.

> You must have the same version name between projects. The Test Execution fix version must have the same value as the Requirement Issue fix version.[^xrayfaq]

버전 이름이 `v2.1` 과 `2.1` 로 갈리는 순간, 실행 결과는 존재하는데 커버리지는 `UNCOVERED` 로 보인다. 아무도 에러를 보지 못한다.

### (3) ABORTED 는 실패가 아니라 "안 돌린 것" 이다

위 매핑 표에서 `ABORTED` → `NOTRUN` 이다. 인프라 문제로 중단된 테스트 스위트는 화면에서 **빨간색이 아니라 회색**으로 보인다. "실패는 없네" 라는 판단이 여기서 나온다. `NOTRUN` 은 "아직 안 봤다" 라는 뜻이지 "괜찮다" 가 아니다.

### (4) Final statuses precedence — 새로 잡은 실행이 상태를 못 바꾼다

기본값으로 켜져 있는 설정이다.

> If you have a Test currently in some final status (e.g. PASS, FAIL) and you schedule a new Test Run for it, then this Test Run won't affect the calculation of the status of the Test.[^xraycalc]

의도된 동작이다 — 끝난 작업만 보겠다는 것. 하지만 "재실행 걸었는데 상태가 안 변한다" 는 혼란의 정확한 출처이기도 하다. 이 플래그가 켜져 있으면 최신 Test Run 은 `finished on` 기준으로, 꺼져 있으면 `created` 기준으로 뽑힌다.[^xraycalc] 판정 기준 자체가 바뀐다.

### (5) Separation of Concerns — 하나의 실패가 모든 요구사항을 물들인다

Xray 설정의 `Separation of Concerns` 는 기본적으로 **하나의 Test 결과가 연결된 모든 요구사항에 동일하게 반영되도록** 한다. 하나의 Test 가 여러 요구사항을 서로 다른 방식으로 검증한다면 이 옵션을 꺼야 하고, 그러면 실행 화면에서 요구사항별 상태를 수동으로 지정할 수 있다.[^xraysettings] 끄지 않은 채 Test 하나에 요구사항 다섯 개를 묶으면, 한 스텝의 실패가 다섯 개를 전부 `NOK` 로 만든다.

---

## 5. 관리법 — 대시보드가 아니라 게이트로

### 5.1 추적 단위를 문단이 아니라 이슈로 내린다

Confluence 페이지 하나에 이슈 하나를 걸면 커버리지의 해상도는 페이지 단위가 된다. 실질적으로 아무것도 추적하지 못한다. **사양서의 검증 가능한 진술마다 이슈를 만든다.** 하이라이트 → Create Jira issue 가 바로 이 용도이고, 표 형태로 사양을 쓰면 한 열에서 여러 이슈를 한 번에 만들 수 있다.[^conftogether]

### 5.2 링크는 나중에 손으로 맞추지 않는다

Test Coverage 패널에서 **요구사항으로부터 Test 를 생성**하면 링크가 자동으로 걸린다.[^xraycoverage] 반대로 이미 만들어 둔 Test 를 나중에 사람이 찾아 붙이는 방식은 반드시 누락된다. 링크는 생성 시점에 부수효과로 생겨야 한다.

### 5.3 커버리지는 JQL 게이트로 건다

차트는 쳐다보지 않으면 그만이다. 릴리스 조건으로 걸어야 한다. Xray 공식 튜토리얼이 제시하는 질의가 그대로 쓸 만하다.[^xrayjql]

```
project = COM AND issue in requirements('uncovered')
```

버전·환경까지 좁히려면 `requirements()` 함수의 인자를 채운다. 시그니처는 `requirements(상태목록, 프로젝트, 버전, 테스트환경, flat, toDate, savedFilter)` 이고, 공식 문서는 **프로젝트 인자를 반드시 채우라**고 강하게 권고한다 — 비워 두면 Jira 전체 프로젝트의 요구사항을 처리한다.[^xrayjqlfn]

```
issue in requirements('NOK', 'Calculator', 'v2.0', 'chrome', 'false')
```

`flat` 인자를 눈여겨보자. 기본값이 `false` 라서 **부모 요구사항만 조회된다.** 4절 (3)의 표에서 본 대로 부모는 자식이 `UNCOVERED` 여도 `OK` 로 보일 수 있으니, 실제 구멍을 찾으려면 `flat = 'true'` 로 바닥까지 내려가야 한다.

역방향도 함수가 있다. `requirementTests('DEMO-10')` 은 요구사항을 검증하는 Test 목록을, `testRequirements('DEMO-1')` 은 어떤 Test 가 검증하는 요구사항 목록을, `testPlanRequirements('DEMO-20')` 은 Test Plan 에 (간접적으로라도) 엮인 요구사항 전부를 돌려준다.[^xrayjqlfn]

### 5.4 분석 스코프를 팀 합의로 고정한다

Xray 의 커버리지는 **Version / Test Plan / Test Environment** 라는 스코프 위에서만 의미가 있다. 공식 문서는 같은 스토리가 "1.0 에서는 OK 인데 2.0 에서는 회귀 때문에 NOK 일 수 있다" 고 예를 든다.[^xraycovanalysis] 스코프를 정하지 않은 커버리지 숫자는 서로 다른 질문의 답을 한 칸에 적어 놓은 것이다. 무엇을 기준으로 볼지 — 버전인지 Test Plan 인지, 환경을 묶을지 나눌지 — 를 먼저 합의하고 리포트 기본값으로 박아 둔다.

### 5.5 커스텀 필드에 의존하지 않는다

`Requirement Status` 커스텀 필드에 대해 공식 문서가 스스로 내린 평가는 냉정하다.

> they're just used to have a quick glimpse of the status of each entity … therefore their usage is limited.[^xraycalc]

같은 문서는 요구사항을 상태로 검색할 거면 **커스텀 필드 대신 `requirements()` 함수를 쓰라**고 권고한다.[^xraycf] 대시보드 위젯은 필드로, 게이트는 함수로 나누는 게 안전하다.

### 5.6 사양서 위에 커버리지를 올려 둔다

Xray 의 `Overall Requirement Coverage` 가젯을 Confluence 페이지에 임베드할 수 있다.[^xrayconf] 4절 (1)에서 본 단방향 링크 문제의 현실적 완화책이다 — 사양서를 읽는 사람이 그 자리에서 커버리지를 본다. 다만 이건 가젯 프로비저닝과 인증이 얽혀 있어 잘 깨진다. Xray 트러블슈팅 문서가 점검 순서를 그대로 적어 뒀다: Application Links 양쪽 확인 → Confluence 관리자에서 외부 가젯 등록(개별 또는 피드 구독) → Confluence 에서 Jira 인증 완료 여부 → 가젯 XML URL 직접 참조로 격리.[^xrayconf]

### 5.7 릴리스 전엔 Traceability 리포트를 역방향으로 읽는다

`Requirement Traceability Report` 는 요구사항 → Test → Test Run → Defect 를 한 화면에 놓는다. 공식 설명은 "요구사항의 생애를 정방향·역방향 모두로" 본다고 쓴다.[^xraytrace] 커버리지 숫자가 아니라 **결함까지 이어진 사슬**을 보는 게 릴리스 판정에 훨씬 가깝다. 이 리포트를 쓰려면 프로젝트에 Requirement Coverage 가 켜져 있어야 한다는 전제도 같은 문서에 적혀 있다.

---

## 6. 요약

- Xray 에 `Requirement` 이슈타입은 없다. **역할을 매핑**하는 것이고, 프로젝트 활성화 + 이슈타입 매핑이 둘 다 필요하다.
- 커버리지의 물리적 실체는 **Jira 이슈 링크** (`tests` / `tested by`) 다. 사양서 텍스트 변경은 여기에 아무 영향도 주지 않는다.
- 요구사항 상태는 **버전·Test Plan·환경 스코프 위에서만** 정의된다. "어느 버전에서?" 를 빼먹은 커버리지 수치는 무의미하다.
- 부모 요구사항은 자식이 전부 `UNCOVERED` 여도 `OK` 로 보일 수 있다. `flat = 'true'` 로 내려가서 봐야 한다.
- `ABORTED` 는 `NOTRUN` 으로 매핑된다. 회색은 안전이 아니다.
- 대시보드가 아니라 `requirements('uncovered')` 같은 **JQL 게이트**로 릴리스를 막는다.

도구 조합 전반의 손익은 [Jira와 Confluence의 장점과 단점]({% post_url 2026-09-14-jira-confluence-pros-and-cons %})에서, 이슈 키를 축으로 도구를 한 흐름으로 엮는 방법은 [이슈 키 하나로 세 도구 엮기]({% post_url 2026-09-14-jira-confluence-gitlab-intellij-one-flow %})에서 다뤘다. 사양 자체를 검증 가능한 단위로 쪼개는 문제는 [모호한 아이디어를 결정 가능한 설계로 바꾸는 법]({% post_url 2026-08-09-grill-me-requirements-discovery %})에 가깝다.

---

## 7. 근거의 한계

이 글의 모든 규칙·상태표·수식은 **Xray Server + Data Center 공식 문서**와 **Atlassian Confluence Data Center 공식 문서**를 근거로 한다. Xray Cloud 는 용어(예: coverable issues)와 설정 화면이 다를 수 있으므로, Cloud 사용자는 동일 항목을 Cloud 문서에서 다시 확인해야 한다. 성능 수치나 도입 효과에 대한 정량 주장은 이 글에 없다 — 중립 제3자의 재현 가능한 측정 자료를 확인하지 못했기 때문이다. 벤더 문서는 제품 동작의 1차 출처로는 신뢰할 수 있지만, 제품의 *효과*에 대한 주장으로는 1차 출처가 아니다.

---

## References

[^xrayfaq]: Xray Server + DC Documentation, "FAQ". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY/pages/301404190/FAQ>
[^xrayreqdef]: Xray Documentation, "Requirements and Defects". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY760/pages/48760721/Requirements+and+Defects>
[^xraycoverage]: Xray Server + DC Documentation, "Test Coverage". <https://docs.getxray.app/space/XRAY/301469960/Test%20Coverage>
[^xraycalc]: Xray Server + DC Documentation, "Understanding coverage and the calculation of Test and requirement statuses". <https://docs.getxray.app/space/XRAY/301669557/Understanding+coverage+and+the+calculation+of+Test+and+requirement+statuses>
[^xraycf]: Xray Server + DC Documentation, "Using custom fields". <https://docs.getxray.app/space/XRAY/301474590/Using%20custom%20fields>
[^xraysettings]: Xray Server + DC Documentation, "Coverage Settings". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY/pages/301504155/Coverage+Settings>
[^xraycovanalysis]: Xray Documentation, "Coverage Analysis". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY740/pages/48432017/Coverage+Analysis>
[^xraytrace]: Xray Server + DC Documentation, "Requirement Traceability Report". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY/pages/301699901/Requirement+Traceability+Report>
[^xrayjql]: Xray Server + DC Documentation, "Tutorial for querying with JQL". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY/pages/301669523/Tutorial+for+querying+with+JQL>
[^xrayjqlfn]: Xray Server + DC Documentation, "Enhanced querying with JQL". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY/pages/301501338/Enhanced+querying+with+JQL>
[^xrayconf]: Xray Documentation, "Integration with Confluence" 및 Xray Product KB, "[Xray Server] Troubleshooting Quick Tips for Confluence Integration". <https://getxraydocs.atlassian.net/wiki/spaces/XRAY720/pages/48268125/Integration+with+Confluence> · <https://docs.getxray.app/space/ProductKB/46269103/>
[^conftogether]: Atlassian Documentation, "Use Jira applications and Confluence together" (Confluence Data Center 10.2). <https://confluence.atlassian.com/doc/use-jira-and-confluence-together-427623543.html>
[^confmacro]: Atlassian Documentation, "Jira Issues Macro" (Confluence Data Center 10.2). <https://confluence.atlassian.com/doc/jira-issues-macro-139380.html>
[^confcloudjiradc]: Atlassian Documentation, "Integrate Confluence Cloud with Jira Data Center/Server". <https://confluence.atlassian.com/enterprise/integrate-confluence-cloud-with-jira-data-center-server-1101925671.html>
