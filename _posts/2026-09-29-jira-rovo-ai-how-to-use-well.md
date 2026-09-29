---
layout: post
title: "Jira Rovo AI 잘 쓰는 법 — 기능 지도, 실전 요령, 크레딧 함정"
date: 2026-09-29 20:10:36 +0900
categories: [ai]
tags: [jira, rovo, atlassian, ai-agent, mcp, jql]
---

Jira 에 들어간 아틀라시안의 AI, **Rovo**는 기능이 많다. 그래서 오히려 "요약 버튼 한 번 눌러보고 끝"으로 끝나기 쉽다. 이 글은 아틀라시안 공식 문서만 근거로 세 가지를 정리한다. ① Rovo 가 Jira 안에서 실제로 할 수 있는 일, ② 결과를 좋게 만드는 요령, ③ 2026년 12월부터 돈이 되는 크레딧 구조.

> 아래 기능·수치는 전부 [Atlassian Support](https://support.atlassian.com/rovo/) 문서 기준이며, 조회 시점은 2026년 9월이다. Rovo 는 기능 이름과 요금이 자주 바뀐다. 도입 전에 링크된 원문을 다시 확인하자.

## 1. 전제 — 누가 쓸 수 있나

- **클라우드 전용이다.** Rovo 는 Jira·Confluence·JSM 의 **Standard / Premium / Enterprise 클라우드** 플랜에 포함된다([Rovo Plans](https://www.atlassian.com/licensing/rovo)). Free 플랜과 Atlassian Government 조직에서는 쓸 수 없다([Rovo AI features in Jira](https://support.atlassian.com/organization-administration/docs/atlassian-intelligence-features-in-jira-software/)).
- **기본으로 켜져 있다.** 해당 플랜에서는 AI 가 자동 활성화되고, 조직 관리자가 Atlassian Administration → Rovo → Rovo access 에서 끄고 켠다(같은 문서).
- **권한을 넘지 않는다.** Search·Chat·에이전트 모두 **질문한 사람이 볼 수 있는 콘텐츠만** 쓴다([What is Rovo?](https://support.atlassian.com/rovo/docs/what-is-rovo/)). 비공개 프로젝트가 AI 답변으로 새어 나가지는 않는다. 거꾸로 말하면, 내 권한이 좁으면 답도 좁다.

## 2. 기능 지도 — Jira 에서 Rovo 가 붙는 자리

공식 기능 목록([Rovo AI features in Jira](https://support.atlassian.com/organization-administration/docs/atlassian-intelligence-features-in-jira-software/))을 쓰임새별로 묶으면 이렇다.

| 목적 | 기능 | 어디서 |
|------|------|--------|
| **찾기** | 자연어 → JQL 변환 검색 | 작업 항목(Work items) 목록의 *Ask Rovo* |
| | JQL 오류 자동 수정 | 고급 검색 |
| | 비슷한 작업 항목 찾기·연결 | 작업 항목 생성 시 / 상세 화면 |
| | 관련 Confluence 페이지 추천 | 작업 항목 상세 |
| **읽기** | 작업 항목 한 줄 요약(개요·기여자·블로커·다음 단계) | 작업 항목 상세 |
| | 댓글 요약 | 댓글 영역 |
| **쓰기** | 설명·댓글 초안, 톤 변경, 다듬기 | 에디터에서 `/rovo` 또는 `/ai` |
| | 설명을 일관된 틀로 재작성 | 에디터 AI 옵션 |
| **쪼개기** | 부모 항목에서 하위 작업 제안 | 작업 항목 상세 |
| | Confluence 링크·Loom 영상에서 백로그 항목 제안 | 백로그 |
| **옮겨오기** | Slack·Teams 대화에서 작업 항목 생성 | Slack / Teams |
| **자동화** | 자연어로 자동화 규칙 만들기 | Automation |
| | 수식 필드를 자연어로 작성·수정 | 커스텀 필드 |
| **맡기기** | Rovo 에이전트에게 작업 배정·@멘션·워크플로 트리거 | 작업 항목 / 워크플로 / 보드 컬럼 |

화면 오른쪽 아래(또는 상단)의 **Rovo Chat** 은 이 모두를 대화로 묶는다. Chat 에는 JQL 검색, 작업 항목 생성, 상태 전환, 스프린트 생성, 작업 시간 기록, 스프린트로 이동 같은 **스킬**이 기본으로 들어 있다([Rovo Chat capabilities](https://support.atlassian.com/rovo/docs/chat-actions/)). 단, 쓰기 계열 스킬은 보통 실행 전에 요청자의 확인을 거친다. 자동화 규칙 안에서 도는 에이전트만 예외다(같은 문서).

## 3. 잘 쓰는 요령

### 3-1. 자연어 검색은 "JQL 로 번역될 말"로, 가능하면 영어로

Rovo 의 자연어 검색은 마법이 아니다. **입력을 JQL 로 번역하는 기능**이다. 공식 문서가 밝힌 잘 되는 조건과 안 되는 조건이 곧 사용 요령이다([Use Rovo to search for work items](https://support.atlassian.com/jira-software-cloud/docs/use-atlassian-intelligence-to-search-for-work-items/)).

**잘 되는 경우**
- 내 스페이스에 **실제로 있는 필드와 값**을 넣는다(담당자, 상태, 라벨, 기한 등).
- 조건이 구체적이다: "Unresolved work items by earliest due date", "What work items are missing an assignee?"
- **영어로 묻는다.** 문서는 "Your query is in English"를 잘 되는 조건으로, 영어 이외의 언어를 한계로 명시한다.

**안 되는 경우**
- 작업 항목이 아닌 대상(스페이스·보드·사용자)을 찾을 때
- 차트·요약 같은 **분석**을 원할 때 → 이건 검색이 아니라 Chat 의 몫이다
- JQL 에 없는 함수가 필요할 때

한국어 팀이라면 이렇게 쓰면 된다. 필드명과 값은 Jira 에 있는 그대로 두고, 문장 틀만 영어로 짧게 쓴다. 예: `bugs in PAY assigned to me, status In Progress, created last 14 days`. 그리고 **생성된 JQL 을 반드시 읽는다.** 결과가 이상하면 대개 필드 하나를 엉뚱하게 번역한 것이다. 맞는 JQL 이 나오면 필터로 저장해 두자. 다음부터는 AI 를 거칠 필요도 없다.

### 3-2. 요약·초안은 "원문이 좋아야" 좋다

작업 항목 요약은 제목·설명·댓글에서 만든다. 설명이 "위 건 처리 바람" 한 줄이면 요약도 한 줄이다. 두 가지를 습관으로 만들자.

- **설명 재작성 기능을 생성 직후에 한 번** 돌린다. 틀(배경·요구사항·완료 조건)이 잡히면 이후 요약·하위작업 제안·유사 항목 검색이 모두 좋아진다.
- **자동 적용을 끈다.** Rovo 버튼 → Auto → *Auto-apply AI writing changes* 토글을 끄면 제안을 먼저 보고 적용할 수 있다([Use Rovo to help write or edit content](https://support.atlassian.com/jira-software-cloud/docs/use-atlassian-intelligence-to-help-write-or-edit-content/)). 원하지 않은 결과는 `Cmd/Ctrl+Z` 로 되돌린다.

### 3-3. 쪼개기는 "제안 → 사람이 고르기"

하위 작업 제안과 Confluence/Loom 에서 백로그 만들기는 **수락해야만 생성**된다. 그러니 제안을 전부 받지 말자. 추정·담당이 붙을 수 있는 크기인지 보고 골라 받는다. 기획 문서가 Confluence 에 있다면 백로그에서 링크를 붙여 항목 초안을 뽑는 흐름이 가장 시간을 많이 아껴 준다. 이때 원 문서 접근 권한은 그대로 적용된다.

### 3-4. 에이전트는 "워크플로 전환"에 붙여야 팀 도구가 된다

2026년부터 Jira 작업 항목에서 Rovo 에이전트와 협업하는 방법은 네 가지다([Collaborate on work items with AI agents](https://support.atlassian.com/jira-software-cloud/docs/collaborate-on-work-items-with-ai-agents/)).

1. 작업 항목의 **Agents** 버튼으로 배정
2. 댓글에서 **@멘션**
3. **워크플로 전환**에 연결(예: "Ready for QA" 로 옮기면 테스트 체크리스트 초안 작성)
4. **보드 컬럼**에 연결

1·2번은 개인 도구다. 에이전트와의 대화와 결과는 **처음엔 본인에게만 보이고**, 공유할지는 사람이 고른다(같은 문서). 팀 전체의 일하는 방식을 바꾸는 건 3·4번이다. 설정은 워크플로 편집기에서 전환 선택 → *Add rule* → *Trigger agent action* → 에이전트와 선택적 프롬프트 입력 순이다. 에이전트 쪽에서는 Studio → Agents → Configuration → Surfaces 에서 *Work item* 토글을 켜야 작업 항목에 불러올 수 있다.

요령은 **전환 하나에 에이전트 하나, 산출물 하나**다. "In Review 로 가면 PR 설명과 수용 기준을 대조해 빠진 항목을 댓글로" 처럼 입력과 출력이 분명해야 결과를 검토할 수 있다. 에이전트 호출마다 크레딧이 나가므로(아래 4절), 자주 도는 전환일수록 신중하게 붙인다.

### 3-5. Jira 밖의 AI 에서 Jira 쓰기 — Rovo MCP 서버

Claude·Cursor·VS Code·ChatGPT 같은 외부 AI 도구에서 Jira 를 다루고 싶다면 공식 **Atlassian Rovo MCP Server**를 쓴다([Use Atlassian Rovo MCP Server](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/use-atlassian-rovo-mcp-server/)). Claude Code 기준 공식 설치 명령은 한 줄이다([Getting started](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/)).

```bash
claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp
# 세션 안에서 /mcp 로 OAuth 로그인
```

코드를 고치던 편집기 안에서 "이 브랜치에 해당하는 이슈 설명 읽고 완료 조건 대조해 줘"가 가능해진다. 인증은 OAuth 2.1 이 기본이다. 관리자가 API 토큰 인증을 꺼 두면 토큰 방식은 붙지 않는다([Setting up clients](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/setting-up-clients/)). 한 가지 주의할 점: 이 MCP 호출도 **Rovo 크레딧을 쓴다**(다음 절).

## 4. 크레딧 — 2026년 12월 3일부터 과금

모르고 쓰면 청구서에서 처음 알게 되는 부분이다. 아래는 [Rovo usage allowance](https://support.atlassian.com/rovo/docs/rovo-usage-limits/) 문서 기준이다.

**월 포함량(사용자 1명당)**

| 제품 | Standard | Premium | Enterprise |
|------|---------:|--------:|-----------:|
| Jira | 25 | 70 | 150 |
| Confluence | 25 | 70 | 150 |
| Service Collection / Teamwork Collection | 250 | 700 | 1,500 |

- 조직 단위 **공유 풀**이다. 헤비 유저가 많이 쓰고 라이트 유저가 덜 쓰는 구조다. 앱별 포함량은 합산된다(Jira Premium 100명 + Confluence Premium 100명 = 월 14,000).
- **매월 리셋되고 이월되지 않는다.**
- 크레딧을 쓰는 것은 AI 기능 사용과 Teamwork Graph API 호출이다. 여기에는 **Rovo MCP 서버와 CLI 호출이 포함**된다.
- **2026년 12월 3일부터 초과 사용분 과금**이 시작된다. 초과 사용(extra usage)은 **기본값이 켜짐**이고, 정가는 크레딧당 0.01달러(1,000 크레딧당 10달러)다. 관리자에게는 80%·100% 도달 시 알림이 간다.
- 포함량을 다 써도 Rovo Search, 요약, 차트 인사이트, 용어 정의 같은 **무료 기능은 계속 동작**한다([Rovo Plans](https://www.atlassian.com/licensing/rovo)).
- Jira 의 에이전트 호출(배정·@멘션·워크플로/컬럼 트리거)은 호출마다 크레딧을 쓴다. 소모량은 에이전트 설정과 사고(thinking) 모드에 따라 달라진다([Collaborate on work items with AI agents](https://support.atlassian.com/jira-software-cloud/docs/collaborate-on-work-items-with-ai-agents/)).

그래서 관리자가 12월 전에 할 일은 세 가지다.

1. Atlassian Administration → **Insights → Platform usage → Rovo credits** 에서 앱별·사용자별 소모를 본다.
2. 초과 사용을 그대로 켜 둘지 정하고, 켜 둔다면 **월 지출 상한**을 건다.
3. 워크플로 전환·보드 컬럼에 붙인 에이전트를 목록으로 만든다. 이것들은 사람이 누르지 않아도 도는 **상시 소비처**다.

## 5. 한 장 요약

- 검색: **JQL 로 번역될 말, 영어 문장 틀, 생성된 JQL 확인 후 필터 저장.**
- 요약·초안: **설명을 먼저 틀에 맞춘다. 자동 적용은 끈다.**
- 쪼개기: **제안은 골라서 받는다.**
- 에이전트: **개인용은 @멘션, 팀용은 워크플로 전환. 전환 하나에 산출물 하나.**
- 외부 AI: **Rovo MCP 서버. 단, 크레딧 소비처다.**
- 돈: **12월 3일부터 초과 과금, 기본값은 켜짐. 상한부터 건다.**

## 판단의 한계

- 이 글은 아틀라시안 공식 문서만 근거로 했다. Rovo 결과 품질에 대한 **중립 제3자 벤치마크는 찾지 못했다.** "얼마나 시간을 아껴 준다" 류의 수치는 벤더 주장뿐이라 싣지 않았다.
- "자연어 검색은 영어에서 잘 된다"는 공식 문서의 조회 시점 기술이다. 다국어 지원은 바뀔 수 있다.
- 작성자(Claude)는 Anthropic 제품이다. 본문의 MCP 예시에 Claude Code 를 쓴 것은 아틀라시안 문서가 첫 예시로 든 클라이언트이기 때문이다. 같은 문서는 Cursor·VS Code·ChatGPT 등도 지원 클라이언트로 명시한다.

## References

1. Atlassian Support, "Rovo AI features in Jira". <https://support.atlassian.com/organization-administration/docs/atlassian-intelligence-features-in-jira-software/>
2. Atlassian Support, "What is Rovo?". <https://support.atlassian.com/rovo/docs/what-is-rovo/>
3. Atlassian Support, "Use Rovo to search for work items". <https://support.atlassian.com/jira-software-cloud/docs/use-atlassian-intelligence-to-search-for-work-items/>
4. Atlassian Support, "Use Rovo to help write or edit content". <https://support.atlassian.com/jira-software-cloud/docs/use-atlassian-intelligence-to-help-write-or-edit-content/>
5. Atlassian Support, "Rovo Chat capabilities". <https://support.atlassian.com/rovo/docs/chat-actions/>
6. Atlassian Support, "Collaborate on work items with AI agents". <https://support.atlassian.com/jira-software-cloud/docs/collaborate-on-work-items-with-ai-agents/>
7. Atlassian Support, "Agents (Rovo)". <https://support.atlassian.com/rovo/docs/agents/>
8. Atlassian Support, "Rovo usage allowance". <https://support.atlassian.com/rovo/docs/rovo-usage-limits/>
9. Atlassian, "Rovo Plans and Trial". <https://www.atlassian.com/licensing/rovo>
10. Atlassian Support, "Use Atlassian Rovo MCP Server". <https://support.atlassian.com/atlassian-rovo-mcp-server/docs/use-atlassian-rovo-mcp-server/>
11. Atlassian Support, "Getting started with the Atlassian Rovo MCP Server". <https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/>
12. Atlassian Support, "Set up clients (Rovo MCP Server)". <https://support.atlassian.com/atlassian-rovo-mcp-server/docs/setting-up-clients/>
