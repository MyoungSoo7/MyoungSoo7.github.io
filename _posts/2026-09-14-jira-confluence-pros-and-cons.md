---
layout: post
title: "Jira와 Confluence의 장점과 단점 — 도구의 비용은 라이선스 청구서 밖에 있다"
date: 2026-09-14 19:14:11 +0900
categories: [Engineering, Tools]
tags: [Jira, Confluence, Atlassian, 협업툴, 이슈트래커, 위키]
---

[지난 글]({% post_url 2026-09-11-teams-jira-confluence-redmine-compared %})에서는 Teams·Jira/Confluence·Redmine 을 **범주**로 갈랐다. 이번엔 그 가운데 칸, Jira 와 Confluence 자체를 뜯는다. 장점과 단점을 나열하되, 한 가지 축을 유지한다 — **이 도구들의 진짜 비용과 진짜 가치는 대부분 라이선스 청구서 밖에 있다**는 것.

출처 원칙: 기능·가격 등 사실 주장은 Atlassian 공식 문서로 확인한 것만 적는다. "느리다", "검색이 약하다" 같은 **사용 경험 평가는 중립적인 헤드투헤드 벤치마크가 존재하지 않으므로**, 사실이 아니라 널리 보고되는 불만으로 라벨을 나눠 적는다.

---

## 1. Jira — 이슈 추적기

### 장점

**① 워크플로우가 코드처럼 조립된다.** Jira 의 워크플로우는 상태(status)와 전이(transition)의 그래프이고, 관리자가 상태·전이·조건을 직접 추가·수정할 수 있다.[^workflow] "우리 팀은 코드리뷰 다음에 QA 검증이 따로 있다" 같은 프로세스를 도구가 아니라 팀이 정의한다. 대부분의 경쟁 도구가 open/closed + 몇 개의 고정 상태를 주는 것과 대비되는 지점이다.

**② JQL — 이슈를 질의한다.** Jira Query Language 로 이슈를 SQL 비슷하게 검색할 수 있다.[^jql] `project = SETTLE AND status changed to Done after -7d` 같은 질의가 되면, "지난주에 실제로 끝난 일" 대시보드는 사람이 집계하는 게 아니라 저장된 질의가 된다. 리포트·보드·자동화가 전부 이 위에 선다.

**③ 자동화가 내장이다.** 규칙 기반 자동화(트리거 → 조건 → 액션)가 별도 구매 없이 모든 Jira 플랜에 포함된다.[^automation-doc] "이슈가 Done 으로 가면 상위 에픽에 코멘트", "PR 이 머지되면 상태 전이" 같은 반복 작업을 규칙으로 치환한다.[^automation]

**④ 개발 도구와의 추적성.** GitHub·Bitbucket·GitLab 을 연결하면 브랜치·커밋·PR 이 이슈 키로 이슈에 연결된다.[^devtools] "이 버그 수정이 어느 커밋이고 어느 릴리스에 나갔나"가 이슈 화면에서 바로 보인다. 감사(audit)나 장애 회고가 있는 조직에서 이 추적성은 대체가 어렵다.

**⑤ 생태계.** Atlassian Marketplace 에 서드파티 앱 생태계가 형성돼 있어[^marketplace] 테스트 관리, 시간 추적, 다이어그램 등 본체에 없는 기능을 붙일 수 있다.

### 단점

**① 유연성이 그대로 관리 부채가 된다.** 커스텀 필드는 관리자가 자유롭게 만들 수 있고,[^customfield] 워크플로우도 마찬가지다. 문제는 이걸 막는 구조적 장치가 없다는 것 — 팀마다 필드를 만들다 보면 비슷한 필드가 여럿 생기고, 화면은 아무도 안 채우는 입력란으로 덮이고, 워크플로우는 처음 설계한 관리자 없이는 손댈 수 없는 상태가 된다. **도구의 결함이라기보다 유연성의 청구서**인데, 이 청구서는 도입 1년 뒤에 온다.

**② 학습 곡선.** JQL·워크플로우·스킴(scheme) 개념은 개발자에게도 진입장벽이 있고, 비개발 직군에게는 더 높다. 그 결과 Jira 가 "개발팀만 쓰는 도구"로 고립되고, 나머지 조직은 스프레드시트로 돌아가는 분리가 자주 일어난다. (이 문단은 공식 문서로 입증되는 사실이 아니라 널리 보고되는 조직적 패턴이다.)

**③ 성능 불만.** 화면 전환·검색이 느리다는 불만은 오래되고 광범위하다. 다만 이걸 뒷받침하는 **중립적인 성능 벤치마크는 찾지 못했다** — 규모·설정·네트워크에 따라 체감이 크게 갈리므로, 도입 전 실제 데이터 규모로 체험판을 돌려보는 것이 유일하게 정직한 검증이다.

**④ 비용 구조.** 좌석당 구독이고, 플랜별 가격은 공식 가격 페이지에 공개돼 있다.[^pricing-jira] 주의할 점은 표면 가격보다 **총비용의 구성** — 쓸만한 기능이 Marketplace 앱(별도 과금)에 있는 경우가 많고, 앱 가격도 대개 좌석 수에 비례한다. 인원이 늘면 본체와 앱이 같이 늘어난다.

**⑤ 프로세스 과잉을 유도한다.** 상태를 추가할 수 있으면 추가하게 된다. 필수 필드를 만들 수 있으면 만들게 된다. Jira 가 관료제를 만드는 게 아니라, **관료제를 만들고 싶은 조직의 마찰을 0으로 낮춰준다.** 도구 선택의 문제가 아니라 거버넌스의 문제지만, 도구가 그 방향으로 미끄러지기 쉽게 돼 있는 건 사실이다.

---

## 2. Confluence — 위키

### 장점

**① Jira 통합이 최대 무기다.** Jira 이슈를 페이지에 임베드하고, 페이지에서 이슈를 만들고, 요구사항 문서와 이슈를 양방향으로 연결하는 것이 공식 지원된다.[^jira-confluence] "기획서 따로, 이슈 따로"가 아니라 기획서가 이슈의 출처가 되는 구조 — 이 결합이 Confluence 를 단독 위키가 아니라 Jira 의 반쪽으로 만든다.

**② 구조화된 지식베이스.** 스페이스로 팀·프로젝트 단위를 가르고,[^spaces] 페이지 트리로 계층을 만들고, 템플릿으로 회의록·회고·기획서의 형식을 통일한다.[^templates] 버전 히스토리·인라인 코멘트·동시 편집 같은 협업 기본기도 갖춰져 있다.

**③ 진입장벽이 낮다.** Jira 와 달리 비개발 직군도 바로 쓸 수 있다. 전사 문서 허브가 되려면 이게 필수 조건인데, Confluence 는 그 조건을 충족한다.

### 단점

**① 검색과 발견성.** 문서가 수천 페이지로 쌓이면 "분명히 있는데 못 찾는" 문제가 생긴다는 불만이 오래됐다. 이것도 중립 벤치마크는 없으므로 불만으로 라벨한다. 다만 구조적으로 말할 수 있는 것은 — **위키는 정원이다.** 트리 정리, 죽은 문서 아카이브, 명명 규칙 유지에 지속적인 관리 비용이 들고, 이 비용을 안 내면 어떤 위키든 문서 무덤이 된다. Confluence 는 그 비용을 없애주지 않는다.

**② 개발자 문서와의 마찰.** 에디터가 마크다운 네이티브가 아니라서, 코드리뷰 흐름 안에서 문서를 관리하고 싶은 개발팀은 결국 리포지토리 안 docs(docs-as-code)로 간다. 그러면 문서가 Confluence 와 리포 두 곳으로 갈라지고, 어느 쪽이 진실인지가 새 문제가 된다. 이 분기는 도구 결함이라기보다 **개발 문서와 조직 문서의 요구사항이 원래 다르다**는 사실의 표출인데, Confluence 하나로 둘 다 덮으려 하면 마찰이 난다.

**③ 단독으로는 매력이 약하다.** Jira 없이 Confluence 만 쓴다면, 경쟁 제품(Notion 등[^notion]) 대비 차별점의 대부분 — Jira 임베드·연동 — 이 사라진다. Confluence 의 가격도 좌석당 구독이므로[^pricing-confluence] 단독 도입이라면 비교 대상을 넓게 잡는 게 맞다.

---

## 3. 그래서 언제 쓰나

- **프로세스·감사·추적성이 요구되는 조직** (규제 산업, 규모 있는 제품 조직): Jira + Confluence 조합은 여전히 표준에 가깝다. 추적성(커밋↔이슈↔릴리스)과 워크플로우 강제력은 이 조합의 대체가 드물다.
- **소규모 팀·스타트업**: 유연성의 관리 부채를 감당할 관리자가 없다면, 더 가벼운 조합(예: Linear[^linear] + Notion)이 총비용에서 유리할 수 있다. 다만 이것은 성능·기능의 우열 판정이 아니라 **관리 비용을 누가 내느냐**의 선택이다.
- **자체 호스팅이 필수인 조직**: Atlassian 의 배포 옵션 문제는 [지난 글]({% post_url 2026-09-11-teams-jira-confluence-redmine-compared %})에서 다뤘다 — 이 경우 비교 대상 자체가 달라진다.

한 줄 요약 — **Jira 는 프로세스가 있는 조직에겐 최강의 추적 도구, 없는 조직에겐 관료제 생성기다. Confluence 는 Jira 옆에서 가치가 극대화되는 지식베이스이고, 단독으로는 평범한 위키다.** 그리고 두 도구 모두, 진짜 비용은 라이선스가 아니라 그것을 계속 정리하는 사람의 시간이다.

---

## References

[^workflow]: Atlassian 공식 문서 — [Work with issue workflows](https://support.atlassian.com/jira-cloud-administration/docs/work-with-issue-workflows/)
[^jql]: Atlassian 공식 문서 — [What is advanced search in Jira Cloud?](https://support.atlassian.com/jira-software-cloud/docs/what-is-advanced-search-in-jira-cloud/)
[^automation-doc]: Atlassian 공식 문서 — [Jira Cloud automation](https://support.atlassian.com/cloud-automation/docs/jira-cloud-automation/)
[^automation]: Atlassian 공식 제품 페이지 — [Jira Automation](https://www.atlassian.com/software/jira/features/automation)
[^devtools]: Atlassian 공식 문서 — [Integrate with development tools](https://support.atlassian.com/jira-cloud-administration/docs/integrate-with-development-tools/)
[^marketplace]: [Atlassian Marketplace](https://marketplace.atlassian.com/)
[^customfield]: Atlassian 공식 문서 — [Create a custom field](https://support.atlassian.com/jira-cloud-administration/docs/create-a-custom-field/)
[^pricing-jira]: Atlassian 공식 가격 페이지 — [Jira Pricing](https://www.atlassian.com/software/jira/pricing)
[^jira-confluence]: Atlassian 공식 문서 — [Use Jira and Confluence together](https://support.atlassian.com/confluence-cloud/docs/use-jira-and-confluence-together/)
[^spaces]: Atlassian 공식 문서 — [Use spaces to organize your work](https://support.atlassian.com/confluence-cloud/docs/use-spaces-to-organize-your-work/)
[^templates]: Atlassian 공식 문서 — [Create a page from a template](https://support.atlassian.com/confluence-cloud/docs/create-a-page-from-a-template/)
[^notion]: [Notion Help Center](https://www.notion.com/help)
[^pricing-confluence]: Atlassian 공식 가격 페이지 — [Confluence Pricing](https://www.atlassian.com/software/confluence/pricing)
[^linear]: [Linear Docs](https://linear.app/docs)
