---
layout: post
title: "지라의 AI '로보(Rovo)' — 무료와 유료는 무엇이 다른가, 그리고 Rovo CLI·Rovo MCP 서버 정리"
date: 2026-10-17 17:40:00 +0900
categories: [ai]
tags: [atlassian, jira, rovo, mcp, cli, ai-agent, pricing]
---

지라(Jira)를 쓰다 보면 화면 곳곳에 **Rovo** 버튼이 보인다. 아틀라시안이 만든 AI 다.
"이거 공짜야?", "터미널에서 쓰는 CLI 도 있다던데?", "Claude 나 Cursor 에서 지라를 부르는 MCP 서버는?" 이 세 질문을
아틀라시안 공식 문서만 가지고 정리했다. 2026-10-17 에 확인한 내용이고, 가격 정책이 자주 바뀌는 영역이라 날짜를 꼭 같이 봐야 한다.

## 1. Rovo 가 무엇인가

공식 설명으로는 Rovo 는 *Jira, Confluence 같은 아틀라시안 앱에 내장된 팀 업무용 AI* 다.
바탕에는 **Teamwork Graph** 라는 맥락 계층이 있다. 아틀라시안 앱과 외부 도구의 업무·문서·사람·시스템을 연결한 그래프이고,
Rovo 는 이걸 이용해 흩어진 정보를 답과 에이전트로 바꾼다([Rovo 라이선스 FAQ](https://www.atlassian.com/software/rovo/pricing)).

사용자가 만나는 기능은 크게 넷이다.

| 기능 | 하는 일 |
|---|---|
| Rovo Search | 지라·컨플루언스와 연결된 외부 앱을 가로질러 검색 |
| Rovo Chat | 자연어로 묻고 답하기 (`chat.rovo.com` 에서도 접속) |
| Agents | 정해진 일을 맡는 AI 에이전트 (기본 제공 + 직접 만들기) |
| Studio | 에이전트와 자동화를 만드는 작업 공간 |

## 2. 무료와 유료 — 핵심은 "플랜"과 "크레딧" 두 축이다

### 축 1. 어떤 플랜이어야 Rovo 를 다 쓰나

공식 FAQ 는 이렇게 적는다. Search, Chat, Studio, 에이전트를 포함한 Rovo 는 **Jira·Confluence·Jira Service Management 의 Standard, Premium, Enterprise 클라우드 플랜**(또는 Service·Teamwork Collection) 고객에게 제공되고,
이런 유료 클라우드 플랜이 하나라도 있으면 **별도 구매 없이 자동으로 추가**된다.
그리고 "Rovo 의 AI 기능을 온전히 쓰려면 Standard 이상의 클라우드 플랜이 필요하다"고 못 박는다([Rovo 라이선스 FAQ](https://www.atlassian.com/software/rovo/pricing)).

즉 "Rovo 따로 결제"가 아니라 **지라·컨플루언스 유료 플랜에 딸려 오는 것**이 기본 구조다.
체험도 같은 방식이다. Rovo 만 따로 체험하는 게 아니라 Jira·Confluence·JSM 의 Standard 이상 플랜 체험으로 써 본다.

### 축 2. 크레딧 — 플랜마다 매달 주는 AI 사용량

유료 플랜에는 매달 **Rovo 크레딧**이 들어 있다. 공식 표를 옮기면 이렇다.

| 플랜 | Standard | Premium | Enterprise |
|---|---|---|---|
| Jira, Confluence | 사용자당 월 25 | 사용자당 월 70 | 사용자당 월 150 |
| Teamwork / Service Collection | 사용자당 월 250 | 사용자당 월 700 | 사용자당 월 1,500 |

- 크레딧은 사람마다 따로가 아니라 **조직 전체 공용 풀**이다. 많이 쓰는 사람과 적게 쓰는 사람이 서로 메워 준다.
- 앱을 여러 개 쓰면 **합산**된다. 공식 예시로 Jira·Confluence 둘 다 Premium 사용자 100명이면 7,000 + 7,000 = 월 14,000 크레딧이다.
- 매달 사용량 청구일에 초기화된다.

### 크레딧은 어디에 얼마나 드나

| 구분 | 소모량 | 예 |
|---|---|---|
| 기본 AI 상호작용 | 건당 10 크레딧 | Rovo Chat 의 빠른 답변 모드, 기본 에이전트 |
| 프리미엄 AI 상호작용 | 건마다 다름 | Rovo Chat 의 Work 모드, **Rovo CLI**, 고급 에이전트, Jira Coding Agent, 컨플루언스 슬라이드 |
| Teamwork Graph API·도구 호출 | 대부분 호출당 1~10 | 여러 시스템의 맥락을 모아 주는 호출. 보통 프롬프트 하나에 10~25 |

공식 FAQ 는 "어디서 눌렀는지가 아니라 **어떤 기능이냐**로 크레딧이 정해진다"고 강조한다.
지라에서 묻든, 컨플루언스에서 묻든, 슬랙에서 묻든 같은 질문이면 같은 크레딧이다.

### 크레딧을 다 쓰면 — 여기가 무료/유료의 실제 경계다

- **초과 사용(extra usage)이 켜져 있으면(기본값)**: 관리자가 정한 지출 한도까지 **추가 요금이 붙으면서** 계속 쓴다.
- **꺼져 있으면**: 크레딧을 쓰는 새 AI 요청이 다음 달 초기화까지 멈춘다. 이미 진행 중인 채팅·에이전트 작업은 끝까지 간다.
- **크레딧과 무관하게 계속되는 것**: 앱 안의 Rovo Search, 요약, 차트 인사이트, 용어 정의 같은 **무료 AI 기능**.
- 관리자는 사용량 80%, 100% 에서 알림을 받는다.

초과 사용이 **기본으로 켜져 있다**는 점은 꼭 기억해 두자. 쓰는 줄도 모르고 청구서에서 처음 만나는 비용은 대개 이런 "기본값 켜짐"에서 나온다.
(우리도 최근 백업 저장소 사용량이 무료 한도를 넘어 매달 소액이 나가고 있었다는 걸 카드 문자로 처음 알았다.)

### Rovo Free 와 Rovo Standard

조직 단위로 보면 **Rovo Free** 와 **Rovo Standard** 라는 구분도 있다.
Rovo Standard 는 지라·컨플루언스 유료 좌석이 없는 사람에게도 Rovo(Chat, Search, Studio 등)를 단독 앱처럼 열어 주는 플랜이다.
공식 문서 기준으로 지금은 **베타라서 요금을 받지 않고**, 베타가 끝나면 직접 유료 Standard 를 선택하지 않는 한 Rovo Free 로 돌아가며, 결정할 시간이 최소 90일 주어진다([What is Rovo Standard?](https://support.atlassian.com/rovo/docs/what-is-rovo-standard/)).

### 정리 — 무료로 쓰는 것과 돈이 드는 것

| | 돈이 안 드는 것 | 돈이 드는 것 |
|---|---|---|
| 플랜 | — | Rovo 전체 기능은 Jira/Confluence/JSM **Standard 이상** 유료 플랜에 포함 |
| 사용량 | 플랜에 포함된 월 크레딧 범위, 앱 안의 Search·요약·차트 인사이트·정의 | 크레딧 초과분(초과 사용 켜짐일 때), 선불 크레딧 팩 |
| 별도 도구 | MCP 서버·Teamwork Graph CLI **설치와 연결** | 그 도구로 하는 맥락 조회 호출의 크레딧, 독립형 Rovo Dev 구독 |

참고로 공식 크레딧 표에는 Standard·Premium·Enterprise 만 있다. Jira **Free 플랜**에 대해서는 이 FAQ 에 별도 할당이 적혀 있지 않으니,
Free 플랜 사이트라면 실제 관리 화면(Atlassian Administration → Insights → Platform usage → Rovo credits)에서 확인하는 게 정확하다.

## 3. Rovo CLI — 터미널의 Rovo

### 지금 쓰는 이름: Rovo Dev CLI

현재 문서상 정식 이름은 **Rovo Dev CLI** 다. 리포지토리의 코드를 이해하고, 지라 작업 항목을 처리하거나 컨플루언스 문서를 만드는 터미널 에이전트다.
설치는 아틀라시안 CLI(ACLI)의 확장으로 들어간다([설치 문서](https://support.atlassian.com/rovo/docs/install-and-run-rovo-dev-cli-on-your-device/)).

```bash
# 1) ACLI 설치(또는 최신으로 업데이트) — OS 별 안내는 ACLI 문서
# 2) 범위가 지정된 API 토큰 생성 (Rovo Dev 용)
acli rovodev auth login   # 계정 인증
acli rovodev run          # 대화형 모드로 실행
```

공식 문서 목차를 보면 기능 범위가 대략 보인다. 세션 관리, 메모리, 저장해 두고 다시 쓰는 프롬프트, 도구, **서브에이전트**, **MCP 서버 연결**,
서버 모드, **워크트리 모드**, Agent Skills 확장, 대형 언어 모델 전환이다([Use Rovo Dev CLI](https://support.atlassian.com/rovo/docs/use-rovo-dev-cli/)).
Claude Code 나 Codex CLI 를 써 본 사람이라면 익숙한 구성이다. 차이는 지라·컨플루언스·비트버킷 맥락이 기본으로 붙는다는 점이다.

### 비용 — 지금은 별도 구독, 곧 바뀐다

- **현재**: 사이트에 Rovo Dev 가 활성화돼 있어야 하고, **Rovo Dev 크레딧**이 필요하다. Rovo Dev 크레딧은 위의 Rovo 크레딧과 **별개 체계**다.
  Rovo Dev Standard 는 개발자당 월 20달러, 개발자당 월 2,000 Rovo Dev 크레딧 포함, 초과분은 크레딧당 0.01달러다([Rovo Dev 가격](https://www.atlassian.com/software/rovo-dev/pricing)).
- **체험판에선 CLI 가 안 된다.** 공식 문서에 "Rovo Dev Standard 체험 기간에는 CLI 를 쓸 수 없고 유료 구독이 필요하다"고 적혀 있다.
- **바뀌는 것**: Rovo Dev 는 독립 제품으로서 **단종(end of life)** 될 예정이고, 그 기능은 Jira·Teamwork Collection 구독 안으로 들어간다.
  Rovo Dev CLI 는 **통합 "Atlassian Rovo CLI"** 로 바뀌어 사용량 기반 요금제로 운영될 예정이다. 아틀라시안은 최소 60일 전에 알리고 이전 문서와 전환 기간을 주겠다고 밝혔다([Rovo Dev 전환 안내](https://www.atlassian.com/licensing/rovo-dev)).

앞의 크레딧 표에 **"Rovo CLI" 가 프리미엄 AI 상호작용**으로 이미 들어가 있는 것도 이 전환의 일부로 보인다.
정리하면, 앞으로 CLI 는 별도 구독이 아니라 **Rovo 크레딧을 쓰는 프리미엄 기능**이 될 가능성이 높다. 단가는 "건마다 다름"이라 아직 숫자로 말할 수 없다.

### 비슷한 이름 하나 더: Teamwork Graph CLI

개발자 문서에는 **Teamwork Graph CLI** 도 있다. 이건 AI 에이전트가 아니라, 에이전트가 지라·컨플루언스·비트버킷·JSM·Assets·Loom·Trello 등을 다룰 수 있게 해 주는 **도구 모음 CLI** 다([TWG CLI](https://developer.atlassian.com/platform/teamwork-graph/twg-cli/)).
설치와 연결은 무료이고, 맥락을 모아 주는 "enriched" 호출만 Rovo 크레딧을 쓴다.

## 4. Rovo MCP 서버 — Claude·Cursor·Codex 에서 지라를 부르기

### 무엇인가

아틀라시안 공식 MCP 서버는 **클라우드에서 도는 원격 서버**다. 설치할 프로그램 없이 주소 하나로 붙는다.
Jira, Confluence, JSM, Bitbucket, Compass, Loom, 그리고 Goals·Projects·Teams 같은 플랫폼 데이터와 Teamwork Graph 를 MCP 클라이언트에 연결한다([공식 리포](https://github.com/atlassian/atlassian-mcp-server)).

- 권장 주소: `https://mcp.atlassian.com/v2/mcp`
- 인증: **OAuth 2.1** 또는 **API 토큰**(헤드리스·자동화용)
- 옛 SSE 엔드포인트(`/v1/sse`)는 **2026-06-30 이후 지원 종료**. 커스텀 클라이언트는 `/mcp` 로 옮겨야 한다.

### 연결 예

공식 README 의 표를 그대로 옮긴다.

```bash
# Claude Code
claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp
# 세션 안에서 /mcp 로 인증

# Codex
codex mcp add atlassian --url https://mcp.atlassian.com/v2/mcp
```

Cursor 와 Claude Desktop 은 마켓플레이스·확장 메뉴에서 버튼으로 붙인다.

### 알아 두면 좋은 설계 세 가지

1. **권한은 사용자 그대로다.** 서버는 사용자가 원래 볼 수 있는 데이터에만 접근하고, 프로젝트·스페이스 권한을 그대로 따른다.
2. **위험한 도구는 기본으로 꺼져 있다.** 지라의 `delete_jira`, `manage_jira` 권한 그룹은 관리자가 켜야 쓸 수 있다.
   JSM 도구는 API 토큰 인증으로만 되고, API 토큰 인증 자체도 관리자가 켜야 한다(Atlassian Administration → Rovo → Rovo MCP server → Authentication).
3. **도구를 한꺼번에 내보내지 않는다.** 자주 쓰는 도구만 먼저 보여 주고 나머지는 필요할 때 찾게 한다. 클라이언트의 컨텍스트를 도구 설명으로 채우지 않기 위해서다.
   MCP 게이트웨이처럼 전부 필요하면 `?tools=all` 을 붙인다.

보안 문서는 접속 허용 도메인 설정, 조직 IP 허용 목록, 인증 방식이 **모두** 통과해야 도구 호출이 성공한다고 설명한다([MCP 서버 보안 문서](https://support.atlassian.com/security-and-access-policies/docs/understand-atlassian-rovo-mcp-server/)).

### 비용

- **설치와 연결은 무료**다.
- 하지만 Teamwork Graph 의 맥락을 모아 주는 호출(공식 문서가 예로 든 `getTeamworkGraphContext`, `searchAtlassian`, `search` 등)은 **Rovo 크레딧을 쓴다.**
  외부 에이전트 작업 하나가 여러 번 호출할 수 있어서, 프롬프트 하나에 10 크레딧을 넘을 수 있다고 FAQ 가 경고한다.
- 단순히 지라 이슈 하나를 읽고 쓰는 호출과, 여러 시스템을 엮어 맥락을 모으는 호출은 비용이 다르다는 뜻이다.

## 5. 고르는 법

| 하고 싶은 일 | 쓸 것 | 비용 감각 |
|---|---|---|
| 지라·컨플루언스 안에서 묻고 찾기 | Rovo Chat·Search | Standard 이상 플랜에 포함. 검색·요약은 크레딧 무관 |
| 터미널에서 코드 + 지라 작업 | Rovo Dev CLI → (전환 후) Rovo CLI | 지금은 개발자당 월 20달러 구독. 전환 후엔 크레딧(프리미엄) |
| 이미 쓰는 Claude Code·Cursor·Codex 에 지라를 붙이기 | Rovo MCP 서버 | 연결 무료, 맥락 조회 호출만 크레딧 |
| 에이전트에게 아틀라시안 도구 모음 주기 | Teamwork Graph CLI | 연결 무료, enriched 호출만 크레딧 |

이미 다른 코딩 에이전트를 쓰고 있다면, CLI 를 새로 들이기보다 **MCP 서버로 지라를 붙이는 쪽**이 진입 비용이 가장 낮다.
그리고 어떤 경로를 택하든, 관리자 화면에서 **초과 사용 한도부터 정해 두는 것**을 권한다. 기본값이 "켜짐"이다.

## References

- Atlassian, *Rovo licensing & FAQ (pricing)* — <https://www.atlassian.com/software/rovo/pricing>
- Atlassian Support, *What is Rovo Standard?* — <https://support.atlassian.com/rovo/docs/what-is-rovo-standard/>
- Atlassian Support, *Use Rovo Dev CLI* — <https://support.atlassian.com/rovo/docs/use-rovo-dev-cli/>
- Atlassian Support, *Install and run Rovo Dev CLI on your device* — <https://support.atlassian.com/rovo/docs/install-and-run-rovo-dev-cli-on-your-device/>
- Atlassian, *Rovo Dev pricing* — <https://www.atlassian.com/software/rovo-dev/pricing>
- Atlassian, *Rovo Dev is transitioning: What you need to know* — <https://www.atlassian.com/licensing/rovo-dev>
- Atlassian Developer, *Teamwork Graph CLI* — <https://developer.atlassian.com/platform/teamwork-graph/twg-cli/>
- Atlassian, *atlassian-mcp-server* (공식 GitHub) — <https://github.com/atlassian/atlassian-mcp-server>
- Atlassian Support, *Understand Atlassian Rovo MCP server* — <https://support.atlassian.com/security-and-access-policies/docs/understand-atlassian-rovo-mcp-server/>
